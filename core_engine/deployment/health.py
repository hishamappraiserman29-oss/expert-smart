"""
health.py — PH.5 Component Health-Check System

Provides a structured health-check registry:
  - Register named checks (callables that return ComponentHealth)
  - Run all checks (with timeout protection)
  - Aggregate to an overall status: HEALTHY / DEGRADED / UNHEALTHY
  - Output JSON-serialisable dict for the /api/advisor/health endpoint

Classes:
    HealthStatus     — HEALTHY | DEGRADED | UNHEALTHY
    ComponentHealth  — result of one check
    HealthChecker    — registry + runner + aggregator
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# HealthStatus
# ---------------------------------------------------------------------------

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


# Status precedence: UNHEALTHY > DEGRADED > HEALTHY
_PRIORITY: Dict[str, int] = {
    HealthStatus.HEALTHY: 0,
    HealthStatus.DEGRADED: 1,
    HealthStatus.UNHEALTHY: 2,
}


# ---------------------------------------------------------------------------
# ComponentHealth
# ---------------------------------------------------------------------------

@dataclass
class ComponentHealth:
    """Result of a single health check."""

    name: str
    status: str         # HealthStatus value
    latency_ms: float = 0.0
    detail: str = ""
    error: Optional[str] = None

    @classmethod
    def healthy(cls, name: str, latency_ms: float = 0.0, detail: str = "") -> "ComponentHealth":
        return cls(name=name, status=HealthStatus.HEALTHY, latency_ms=latency_ms, detail=detail)

    @classmethod
    def degraded(cls, name: str, latency_ms: float = 0.0, detail: str = "", error: str = "") -> "ComponentHealth":
        return cls(name=name, status=HealthStatus.DEGRADED,
                   latency_ms=latency_ms, detail=detail, error=error or None)

    @classmethod
    def unhealthy(cls, name: str, error: str, latency_ms: float = 0.0) -> "ComponentHealth":
        return cls(name=name, status=HealthStatus.UNHEALTHY, latency_ms=latency_ms, error=error)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "latency_ms": round(self.latency_ms, 2),
            "detail": self.detail,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# HealthChecker
# ---------------------------------------------------------------------------

class HealthChecker:
    """
    Registry and runner for named health checks.

    Usage
    -----
    checker = HealthChecker()

    @checker.register("database")
    def check_db() -> ComponentHealth:
        # ...
        return ComponentHealth.healthy("database", latency_ms=3.2)

    result = checker.run_all()
    # result["status"] in {"healthy", "degraded", "unhealthy"}
    """

    def __init__(self, timeout_seconds: float = 5.0) -> None:
        self._checks: Dict[str, Callable[[], ComponentHealth]] = {}
        self._timeout = timeout_seconds
        self._lock = threading.Lock()

    # -- Registration ---------------------------------------------------------

    def register(self, name: str) -> Callable:
        """Decorator: register a zero-argument function as a named health check."""
        def decorator(fn: Callable[[], ComponentHealth]) -> Callable[[], ComponentHealth]:
            with self._lock:
                self._checks[name] = fn
            return fn
        return decorator

    def register_fn(self, name: str, fn: Callable[[], ComponentHealth]) -> None:
        """Register a check function directly (non-decorator form)."""
        with self._lock:
            self._checks[name] = fn

    def unregister(self, name: str) -> bool:
        with self._lock:
            return self._checks.pop(name, None) is not None

    def registered_names(self) -> List[str]:
        with self._lock:
            return list(self._checks.keys())

    # -- Execution ------------------------------------------------------------

    def run_check(self, name: str) -> ComponentHealth:
        """Run a single named check. Returns UNHEALTHY on exception or timeout."""
        with self._lock:
            fn = self._checks.get(name)
        if fn is None:
            return ComponentHealth.unhealthy(name, error=f"Check '{name}' not registered")

        result_holder: List[Optional[ComponentHealth]] = [None]
        exc_holder: List[Optional[str]] = [None]

        def _run() -> None:
            t0 = time.perf_counter()
            try:
                r = fn()
                r.latency_ms = (time.perf_counter() - t0) * 1000
                result_holder[0] = r
            except Exception as exc:
                elapsed = (time.perf_counter() - t0) * 1000
                result_holder[0] = ComponentHealth.unhealthy(
                    name, error=str(exc), latency_ms=elapsed
                )

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join(timeout=self._timeout)

        if t.is_alive():
            # Timed out
            return ComponentHealth.unhealthy(
                name,
                error=f"Timed out after {self._timeout}s",
            )

        return result_holder[0] or ComponentHealth.unhealthy(name, error="No result returned")

    def run_all(self) -> Dict[str, Any]:
        """
        Run all registered checks and return an aggregated status dict.

        Returns
        -------
        {
            "status": "healthy" | "degraded" | "unhealthy",
            "checks": { name: ComponentHealth.to_dict(), ... },
            "summary": { "total": N, "healthy": N, "degraded": N, "unhealthy": N },
            "elapsed_ms": float,
        }
        """
        with self._lock:
            names = list(self._checks.keys())

        t0 = time.perf_counter()
        components: Dict[str, ComponentHealth] = {}
        for name in names:
            components[name] = self.run_check(name)

        elapsed_ms = (time.perf_counter() - t0) * 1000

        # Aggregate
        overall_priority = 0
        summary = {HealthStatus.HEALTHY: 0, HealthStatus.DEGRADED: 0, HealthStatus.UNHEALTHY: 0}
        for comp in components.values():
            summary[comp.status] = summary.get(comp.status, 0) + 1
            p = _PRIORITY.get(comp.status, 0)
            if p > overall_priority:
                overall_priority = p

        overall = {0: HealthStatus.HEALTHY, 1: HealthStatus.DEGRADED, 2: HealthStatus.UNHEALTHY}[overall_priority]

        return {
            "status": overall,
            "checks": {name: comp.to_dict() for name, comp in components.items()},
            "summary": {
                "total": len(components),
                "healthy": summary.get(HealthStatus.HEALTHY, 0),
                "degraded": summary.get(HealthStatus.DEGRADED, 0),
                "unhealthy": summary.get(HealthStatus.UNHEALTHY, 0),
            },
            "elapsed_ms": round(elapsed_ms, 2),
        }


# ---------------------------------------------------------------------------
# Built-in check factories
# ---------------------------------------------------------------------------

def disk_space_check(path: str = ".", warn_pct: float = 80.0, crit_pct: float = 95.0) -> Callable[[], ComponentHealth]:
    """Factory: check available disk space at *path*."""
    def _check() -> ComponentHealth:
        import shutil
        usage = shutil.disk_usage(path)
        used_pct = usage.used / usage.total * 100
        detail = f"{used_pct:.1f}% used ({usage.free // (1024**3):.1f} GB free)"
        if used_pct >= crit_pct:
            return ComponentHealth.unhealthy("disk_space", error=f"Critical: {detail}")
        if used_pct >= warn_pct:
            return ComponentHealth.degraded("disk_space", detail=detail)
        return ComponentHealth.healthy("disk_space", detail=detail)
    return _check


def directory_writable_check(path: str, name: str = "dir_writable") -> Callable[[], ComponentHealth]:
    """Factory: verify that *path* exists and is writable."""
    def _check() -> ComponentHealth:
        import os
        from pathlib import Path
        p = Path(path)
        if not p.exists():
            return ComponentHealth.unhealthy(name, error=f"Directory does not exist: {path}")
        if not p.is_dir():
            return ComponentHealth.unhealthy(name, error=f"Not a directory: {path}")
        if not os.access(str(p), os.W_OK):
            return ComponentHealth.unhealthy(name, error=f"Directory not writable: {path}")
        return ComponentHealth.healthy(name, detail=f"OK: {path}")
    return _check


def import_check(module_name: str) -> Callable[[], ComponentHealth]:
    """Factory: verify that *module_name* can be imported."""
    def _check() -> ComponentHealth:
        import importlib
        t0 = time.perf_counter()
        try:
            importlib.import_module(module_name)
            ms = (time.perf_counter() - t0) * 1000
            return ComponentHealth.healthy(f"import:{module_name}", latency_ms=ms)
        except ImportError as exc:
            return ComponentHealth.unhealthy(f"import:{module_name}", error=str(exc))
    return _check
