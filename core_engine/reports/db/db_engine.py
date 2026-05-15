"""
DB Engine — top-level public API for report persistence.

Wraps ReportRepository with automatic connection management:
each public function opens a connection, ensures the schema is
migrated, performs the operation, and always closes the connection
(modification #5).

This is the only module bridge_api / callers should import from.
ReportRepository is the lower-level, connection-injected layer.

The existing project `database/` package is untouched and unrelated.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .migrations import migrate
from .models import ReportRecord
from .repository import ReportRepository

# Default DB lives in db/data/ — gitignored, never committed.
DEFAULT_DB_PATH: Path = Path(__file__).parent / "data" / "reports.db"


# ─────────────────────────────────────────────────────────────────────
# Connection management (modification #5)
# ─────────────────────────────────────────────────────────────────────

def _connect(db_path: Path | str) -> sqlite3.Connection:
    """Open a migrated SQLite connection, creating the parent dir if needed.

    Always runs migrate() (idempotent) so the schema is guaranteed
    current before any operation. Callers must close the connection
    (the public functions do so in a finally block).
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)
    return conn


# ─────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────

def save_report(
    data: dict[str, Any],
    *,
    profile_key: str,
    status: str = "draft",
    report_id: str | None = None,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> str:
    """Persist a report and return its report_id.

    Args:
        data: Full report DTO — must be JSON-serializable.
        profile_key: 'legacy' / 'detailed' / 'professional'.
        status: One of the valid statuses (default 'draft').
        report_id: Optional caller id; a UUID4 is generated if omitted.
        db_path: SQLite file path (default DEFAULT_DB_PATH).

    Raises:
        ValueError: invalid status.
        TypeError: data not JSON-serializable.
        sqlite3.IntegrityError: report_id already exists.
    """
    conn = _connect(db_path)
    try:
        return ReportRepository(conn).save(
            profile_key=profile_key, data=data,
            status=status, report_id=report_id,
        )
    finally:
        conn.close()


def get_report(
    report_id: str,
    *,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> ReportRecord | None:
    """Return the report with report_id, or None if not found."""
    conn = _connect(db_path)
    try:
        return ReportRepository(conn).get(report_id)
    finally:
        conn.close()


def list_reports(
    *,
    profile_key: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> list[ReportRecord]:
    """Return reports filtered by profile_key/status, newest first."""
    conn = _connect(db_path)
    try:
        return ReportRepository(conn).list(
            profile_key=profile_key, status=status,
            limit=limit, offset=offset,
        )
    finally:
        conn.close()


def update_report(
    report_id: str,
    *,
    data: dict[str, Any] | None = None,
    status: str | None = None,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> bool:
    """Update data and/or status. Returns True if a row changed,
    False if report_id not found.

    Raises:
        ValueError: invalid status.
        TypeError: data not JSON-serializable.
    """
    conn = _connect(db_path)
    try:
        return ReportRepository(conn).update(
            report_id, data=data, status=status,
        )
    finally:
        conn.close()


def delete_report(
    report_id: str,
    *,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> bool:
    """Delete a report. Returns True if deleted, False if not found."""
    conn = _connect(db_path)
    try:
        return ReportRepository(conn).delete(report_id)
    finally:
        conn.close()


def count_reports(
    *,
    profile_key: str | None = None,
    status: str | None = None,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> int:
    """Return the number of reports matching the filters."""
    conn = _connect(db_path)
    try:
        return ReportRepository(conn).count(
            profile_key=profile_key, status=status,
        )
    finally:
        conn.close()
