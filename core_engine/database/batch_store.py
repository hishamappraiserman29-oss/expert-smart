"""
batch_store.py — SQLite-Backed Batch Job Persistence (Phase 13.0)

Replaces the in-memory BatchRegistry with a durable SQLite store so completed
batch reports survive server restarts.

Design decisions:
- One new connection per public method call (SQLite is cheap to open; avoids
  cross-thread connection sharing which sqlite3 disallows by default).
- Schema in one CREATE TABLE IF NOT EXISTS — no migration needed for new installs.
- summary_json / report_json store the full dicts as JSON text so the caller
  always gets back the same shape that get_completion_report() produced.
- Default DB path: tempfile.gettempdir()/expert_smart_batches.db
  Override via BatchStore(db_path="...") or EXPERT_SMART_BATCH_DB env var.

Public API:
    store = BatchStore()
    store.save(completion_report)          # INSERT OR REPLACE
    store.get(batch_id) -> Optional[dict]  # None if not found
    store.list_recent(limit=20) -> list    # newest first
    store.count() -> int
    store.delete(batch_id)                 # test cleanup
"""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from datetime import datetime
from typing import Dict, List, Optional


_DEFAULT_DB = os.environ.get(
    "EXPERT_SMART_BATCH_DB",
    os.path.join(tempfile.gettempdir(), "expert_smart_batches.db"),
)

_DDL = """
CREATE TABLE IF NOT EXISTS batch_jobs (
    batch_id              TEXT PRIMARY KEY,
    batch_name            TEXT NOT NULL DEFAULT '',
    status                TEXT NOT NULL DEFAULT 'completed',
    total_submitted       INTEGER NOT NULL DEFAULT 0,
    completed             INTEGER NOT NULL DEFAULT 0,
    failed                INTEGER NOT NULL DEFAULT 0,
    skipped               INTEGER NOT NULL DEFAULT 0,
    total_valuation_value REAL    NOT NULL DEFAULT 0.0,
    average_valuation     REAL    NOT NULL DEFAULT 0.0,
    summary_json          TEXT    NOT NULL DEFAULT '{}',
    report_json           TEXT    NOT NULL DEFAULT '{}',
    completed_at          TEXT,
    registered_at         TEXT    NOT NULL
);
"""


class BatchStore:
    """Persistent SQLite store for batch completion reports."""

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
        d = dict(row)
        d["summary"] = json.loads(d.pop("summary_json", "{}"))
        # Merge full report fields back (completed/failed/skipped property lists)
        full = json.loads(d.pop("report_json", "{}"))
        d["completed_properties"] = full.get("completed_properties", [])
        d["failed_properties"]    = full.get("failed_properties",    [])
        d["skipped_properties"]   = full.get("skipped_properties",   [])
        return d

    # ── Write ─────────────────────────────────────────────────────────────────

    def save(self, completion_report: dict) -> None:
        """Persist a completion report (INSERT OR REPLACE by batch_id)."""
        summary = completion_report.get("summary", {})
        now     = datetime.now().isoformat()

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO batch_jobs (
                    batch_id, batch_name, status,
                    total_submitted, completed, failed, skipped,
                    total_valuation_value, average_valuation,
                    summary_json, report_json,
                    completed_at, registered_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    completion_report.get("batch_id", ""),
                    completion_report.get("batch_name", ""),
                    completion_report.get("status", "completed"),
                    summary.get("total_submitted",       0),
                    summary.get("completed",             0),
                    summary.get("failed",                0),
                    summary.get("skipped",               0),
                    summary.get("total_valuation_value", 0.0),
                    summary.get("average_valuation",     0.0),
                    json.dumps(summary),
                    json.dumps(completion_report),
                    completion_report.get("completed_at"),
                    now,
                ),
            )
            conn.commit()

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(self, batch_id: str) -> Optional[dict]:
        """Return stored report for batch_id, or None if not found."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM batch_jobs WHERE batch_id = ?", (batch_id,)
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def list_recent(self, limit: int = 20) -> List[dict]:
        """Return up to `limit` most recent reports (newest registered_at first)."""
        limit = max(1, min(limit, 1000))
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM batch_jobs ORDER BY registered_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def count(self) -> int:
        """Return total number of stored batch jobs."""
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM batch_jobs").fetchone()[0]

    # ── Maintenance ───────────────────────────────────────────────────────────

    def delete(self, batch_id: str) -> None:
        """Remove one batch record — intended for tests and admin use."""
        with self._connect() as conn:
            conn.execute("DELETE FROM batch_jobs WHERE batch_id = ?", (batch_id,))
            conn.commit()

    def clear_all(self) -> None:
        """Delete all records — intended for tests only."""
        with self._connect() as conn:
            conn.execute("DELETE FROM batch_jobs")
            conn.commit()
