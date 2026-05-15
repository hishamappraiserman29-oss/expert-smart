"""
ReportRepository — CRUD operations over the `reports` table.

Operates on a caller-supplied, already-migrated sqlite3.Connection.
Connection lifecycle (open/close/migrate) is the responsibility of
db_engine.py (Wave 7c.3), not this module.

Round-trip fidelity: the `data` dict passed to save() is returned
byte-identical by get() — full JSON serialization round-trip.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from .models import ReportRecord
from .schema import VALID_STATUSES


def _utc_now_iso() -> str:
    """Current UTC time as ISO 8601 string (modification #4)."""
    return datetime.now(timezone.utc).isoformat()


def _serialize(data: dict[str, Any]) -> str:
    """Serialize the report DTO to JSON (modification #3).

    Raises a clear TypeError if data contains non-JSON types
    (datetime, Decimal, set, …) instead of a cryptic json error.
    ensure_ascii=False keeps Arabic readable in the stored blob.
    """
    try:
        return json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        raise TypeError(
            f"Report data is not JSON-serializable: {e}. "
            "All values must be str / int / float / bool / None / list / dict."
        ) from e


def _extract_index_fields(data: dict[str, Any]) -> tuple[str | None, float | None]:
    """Pull indexed convenience fields from the DTO — defensive.

    Returns (appraiser_name, market_value); either may be None if
    absent or of an unexpected type.
    """
    appraiser_name: str | None = None
    market_value: float | None = None

    appraiser = data.get("appraiser")
    if isinstance(appraiser, dict):
        name = appraiser.get("name")
        if isinstance(name, str):
            appraiser_name = name

    results = data.get("valuation_results")
    if isinstance(results, dict):
        mv = results.get("market_value")
        if isinstance(mv, (int, float)) and not isinstance(mv, bool):
            market_value = float(mv)

    return appraiser_name, market_value


def _row_to_record(row: tuple) -> ReportRecord:
    """Convert a DB row tuple into a ReportRecord (deserializing data_json)."""
    (report_id, profile_key, status, appraiser_name,
     market_value, created_at, updated_at, data_json) = row
    return ReportRecord(
        report_id=report_id,
        profile_key=profile_key,
        status=status,
        appraiser_name=appraiser_name,
        market_value=market_value,
        created_at=created_at,
        updated_at=updated_at,
        data=json.loads(data_json),
    )


_SELECT_COLUMNS = (
    "report_id, profile_key, status, appraiser_name, "
    "market_value, created_at, updated_at, data_json"
)


class ReportRepository:
    """CRUD repository for report records. Stateless apart from `conn`."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ── Create ──────────────────────────────────────────────────────

    def save(
        self,
        *,
        profile_key: str,
        data: dict[str, Any],
        status: str = "draft",
        report_id: str | None = None,
    ) -> str:
        """Insert a new report record. Returns the report_id.

        Args:
            profile_key: Report profile ('legacy' / 'detailed' / …).
            data: Full report DTO — must be JSON-serializable.
            status: One of VALID_STATUSES (default 'draft').
            report_id: Optional caller-provided id; a UUID4 is
                       generated when omitted.

        Raises:
            ValueError: status not in VALID_STATUSES.
            TypeError: data is not JSON-serializable.
            sqlite3.IntegrityError: report_id already exists.

        On save, created_at == updated_at (modification #4).
        """
        if status not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status {status!r}. Valid: {sorted(VALID_STATUSES)}"
            )
        rid = report_id or str(uuid.uuid4())
        data_json = _serialize(data)
        appraiser_name, market_value = _extract_index_fields(data)
        now = _utc_now_iso()

        self._conn.execute(
            "INSERT INTO reports "
            "(report_id, profile_key, status, appraiser_name, "
            " market_value, created_at, updated_at, data_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (rid, profile_key, status, appraiser_name,
             market_value, now, now, data_json),
        )
        self._conn.commit()
        return rid

    # ── Read ────────────────────────────────────────────────────────

    def get(self, report_id: str) -> ReportRecord | None:
        """Return the record for report_id, or None if not found."""
        cur = self._conn.execute(
            f"SELECT {_SELECT_COLUMNS} FROM reports WHERE report_id = ?",
            (report_id,),
        )
        row = cur.fetchone()
        return _row_to_record(row) if row is not None else None

    def list(
        self,
        *,
        profile_key: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ReportRecord]:
        """Return records filtered by profile_key and/or status.

        Ordered by created_at DESC (newest first). limit/offset paginate.
        """
        clauses: list[str] = []
        params: list[Any] = []
        if profile_key is not None:
            clauses.append("profile_key = ?")
            params.append(profile_key)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        params.extend([limit, offset])

        cur = self._conn.execute(
            f"SELECT {_SELECT_COLUMNS} FROM reports{where} "
            "ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params,
        )
        return [_row_to_record(r) for r in cur.fetchall()]

    def count(
        self,
        *,
        profile_key: str | None = None,
        status: str | None = None,
    ) -> int:
        """Return the number of records matching the filters."""
        clauses: list[str] = []
        params: list[Any] = []
        if profile_key is not None:
            clauses.append("profile_key = ?")
            params.append(profile_key)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        cur = self._conn.execute(
            f"SELECT COUNT(*) FROM reports{where}", params
        )
        return int(cur.fetchone()[0])

    # ── Update ──────────────────────────────────────────────────────

    def update(
        self,
        report_id: str,
        *,
        data: dict[str, Any] | None = None,
        status: str | None = None,
    ) -> bool:
        """Update data and/or status for an existing report.

        Returns True if a row was updated, False if report_id not found
        or nothing to update.
        created_at is preserved; only updated_at changes (modification #4).

        Raises:
            ValueError: status provided but not in VALID_STATUSES.
            TypeError: data provided but not JSON-serializable.
        """
        if data is None and status is None:
            return False
        if status is not None and status not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status {status!r}. Valid: {sorted(VALID_STATUSES)}"
            )

        sets: list[str] = []
        params: list[Any] = []
        if data is not None:
            data_json = _serialize(data)
            appraiser_name, market_value = _extract_index_fields(data)
            sets += ["data_json = ?", "appraiser_name = ?", "market_value = ?"]
            params += [data_json, appraiser_name, market_value]
        if status is not None:
            sets.append("status = ?")
            params.append(status)

        sets.append("updated_at = ?")
        params.append(_utc_now_iso())
        params.append(report_id)

        cur = self._conn.execute(
            f"UPDATE reports SET {', '.join(sets)} WHERE report_id = ?",
            params,
        )
        self._conn.commit()
        return cur.rowcount > 0

    # ── Delete ──────────────────────────────────────────────────────

    def delete(self, report_id: str) -> bool:
        """Delete a report. Returns True if deleted, False if not found."""
        cur = self._conn.execute(
            "DELETE FROM reports WHERE report_id = ?", (report_id,)
        )
        self._conn.commit()
        return cur.rowcount > 0
