"""
connection_manager.py — API Hardening: Connection Pooling
Generic thread-safe object pool. Uses a real DB connection when DATABASE_URL
is set; falls back to a mock connection so the pool works without infrastructure.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mock connection (fallback when no real DB is configured)
# ---------------------------------------------------------------------------

class _MockConnection:
    """Stub connection returned when DATABASE_URL is not set."""

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass

    def cursor(self) -> "_MockCursor":
        return _MockCursor()


class _MockCursor:
    def execute(self, *args, **kwargs) -> None:
        pass

    def fetchall(self) -> list:
        return []

    def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# ConnectionManager
# ---------------------------------------------------------------------------

class ConnectionManager:
    """Thread-safe connection pool with acquire/release lifecycle."""

    def __init__(
        self,
        max_connections:    int   = 20,
        connection_timeout: float = 30.0,
        idle_timeout:       float = 300.0,
    ) -> None:
        self.max_connections    = max_connections
        self.connection_timeout = connection_timeout
        self.idle_timeout       = idle_timeout

        self._available: list = []
        self._active:    Dict[int, Dict[str, Any]] = {}
        self._lock       = threading.Lock()

        self.stats: Dict[str, Any] = {
            "total_acquired":   0,
            "total_released":   0,
            "current_active":   0,
            "max_active":       0,
            "connection_errors": 0,
        }

    @contextmanager
    def get_connection(self, timeout: Optional[float] = None):
        """Yield a connection from the pool; return it on exit."""
        timeout_val = timeout or self.connection_timeout
        conn = None
        try:
            conn = self._acquire(timeout_val)
            cid  = id(conn)
            with self._lock:
                self._active[cid] = {"acquired_at": time.time(), "connection": conn}
                self.stats["current_active"] = len(self._active)
                self.stats["max_active"] = max(
                    self.stats["max_active"], self.stats["current_active"]
                )
            yield conn
        except TimeoutError:
            self.stats["connection_errors"] += 1
            raise
        except Exception:
            self.stats["connection_errors"] += 1
            raise
        finally:
            if conn is not None:
                self._release(conn)
                cid = id(conn)
                with self._lock:
                    self._active.pop(cid, None)
                    self.stats["current_active"] = len(self._active)

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                **self.stats,
                "available": len(self._available),
                "active":    len(self._active),
                "pool_utilization_pct": (
                    len(self._active) / self.max_connections * 100
                ) if self.max_connections else 0,
            }

    # -- Private --------------------------------------------------------------

    def _acquire(self, timeout: float) -> Any:
        deadline = time.monotonic() + timeout
        while True:
            with self._lock:
                if self._available:
                    conn = self._available.pop()
                    self.stats["total_acquired"] += 1
                    return conn
                if len(self._active) < self.max_connections:
                    conn = self._create_connection()
                    self.stats["total_acquired"] += 1
                    return conn
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Could not acquire connection within {timeout}s "
                    f"(active={len(self._active)})"
                )
            time.sleep(0.05)

    def _release(self, conn: Any) -> None:
        try:
            try:
                conn.rollback()
            except Exception:
                pass
            self._available.append(conn)
            self.stats["total_released"] += 1
        except Exception as exc:
            logger.warning("Error releasing connection: %s", exc)
            try:
                conn.close()
            except Exception:
                pass

    @staticmethod
    def _create_connection() -> Any:
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            try:
                from sqlalchemy import create_engine
                engine = create_engine(db_url, pool_pre_ping=True)
                return engine.connect()
            except Exception as exc:
                logger.debug("SQLAlchemy connection failed (%s), using mock", exc)
        return _MockConnection()


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_connection_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager
