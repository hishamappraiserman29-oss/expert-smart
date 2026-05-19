"""
webhook_log.py — SQLite Webhook Delivery Log (Phase 14.1)

Persists WebhookDelivery records so delivery history survives restarts.
Uses the same per-call connection pattern as batch_store.py.

Table: webhook_deliveries
    id           INTEGER PK AUTOINCREMENT
    batch_id     TEXT
    url          TEXT
    status       TEXT  (pending | delivered | failed)
    attempt_count INTEGER
    last_status  INTEGER
    last_error   TEXT
    created_at   TEXT
    delivered_at TEXT
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
from typing import Dict, List, Optional

from adapters.webhook_dispatcher import WebhookDelivery


_DEFAULT_DB = os.environ.get(
    "EXPERT_SMART_BATCH_DB",
    os.path.join(tempfile.gettempdir(), "expert_smart_batches.db"),
)

_DDL = """
CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id      TEXT    NOT NULL DEFAULT '',
    url           TEXT    NOT NULL DEFAULT '',
    status        TEXT    NOT NULL DEFAULT 'pending',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    last_status   INTEGER NOT NULL DEFAULT 0,
    last_error    TEXT    NOT NULL DEFAULT '',
    created_at    TEXT    NOT NULL DEFAULT '',
    delivered_at  TEXT
);
"""


class WebhookLog:
    """Persist and query webhook delivery records."""

    def __init__(self, db_path: str = _DEFAULT_DB) -> None:
        self.db_path = db_path
        self._ensure_table()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_table(self) -> None:
        with self._connect() as conn:
            conn.execute(_DDL)
            conn.commit()

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        return dict(row)

    # ── Write ─────────────────────────────────────────────────────────────────

    def record(self, delivery: WebhookDelivery) -> None:
        """Insert a delivery record (call after dispatch completes)."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO webhook_deliveries
                    (batch_id, url, status, attempt_count,
                     last_status, last_error, created_at, delivered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    delivery.batch_id,
                    delivery.url,
                    delivery.status,
                    delivery.attempt_count,
                    delivery.last_status,
                    delivery.last_error,
                    delivery.created_at,
                    delivery.delivered_at,
                ),
            )
            conn.commit()

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_by_batch(self, batch_id: str) -> List[dict]:
        """Return all delivery records for a given batch_id (newest first)."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM webhook_deliveries
                WHERE batch_id = ?
                ORDER BY id DESC
                """,
                (batch_id,),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def count(self) -> int:
        """Total number of delivery records."""
        with self._connect() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM webhook_deliveries"
            ).fetchone()[0]

    def count_by_status(self, status: str) -> int:
        """Number of records with a given status."""
        with self._connect() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM webhook_deliveries WHERE status = ?",
                (status,),
            ).fetchone()[0]
