"""
audit_log.py — Enterprise Audit Trail (Phase 15.2)

Persists AuditEvent records for compliance and activity tracking.
Uses the same per-call connection pattern as batch_store.py and webhook_log.py.

Table: audit_events
    id            INTEGER PK AUTOINCREMENT
    event_id      TEXT  — uuid, unique per event
    tenant_id     TEXT
    user_id       TEXT
    action        TEXT  — AuditAction value
    resource_type TEXT  — tenant | user | valuation | batch | report
    resource_id   TEXT
    details_json  TEXT  — JSON blob of supplementary context
    ip_address    TEXT
    timestamp     TEXT  — ISO 8601
"""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


_DEFAULT_DB = os.environ.get(
    "EXPERT_SMART_BATCH_DB",
    os.path.join(tempfile.gettempdir(), "expert_smart_batches.db"),
)

_DDL = """
CREATE TABLE IF NOT EXISTS audit_events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id      TEXT    NOT NULL DEFAULT '',
    tenant_id     TEXT    NOT NULL DEFAULT '',
    user_id       TEXT    NOT NULL DEFAULT '',
    action        TEXT    NOT NULL DEFAULT '',
    resource_type TEXT    NOT NULL DEFAULT '',
    resource_id   TEXT    NOT NULL DEFAULT '',
    details_json  TEXT    NOT NULL DEFAULT '{}',
    ip_address    TEXT    NOT NULL DEFAULT '',
    timestamp     TEXT    NOT NULL DEFAULT ''
);
"""


# ── Action enum ───────────────────────────────────────────────────────────────

class AuditAction(str, Enum):
    """Auditable actions in the enterprise system."""

    TENANT_CREATED    = "TENANT_CREATED"
    USER_ADDED        = "USER_ADDED"
    USER_DEACTIVATED  = "USER_DEACTIVATED"
    VALUATION_CREATED = "VALUATION_CREATED"
    BATCH_SUBMITTED   = "BATCH_SUBMITTED"
    REPORT_GENERATED  = "REPORT_GENERATED"
    WEBHOOK_FIRED     = "WEBHOOK_FIRED"
    LICENSE_CHECKED   = "LICENSE_CHECKED"


# ── Audit event ───────────────────────────────────────────────────────────────

@dataclass
class AuditEvent:
    """One audit record representing a single auditable action."""

    tenant_id:     str
    action:        str                       # AuditAction value
    resource_type: str
    resource_id:   str

    user_id:    str       = ""
    details:    Dict      = field(default_factory=dict)
    ip_address: str       = ""
    event_id:   str       = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp:  str       = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "event_id":      self.event_id,
            "tenant_id":     self.tenant_id,
            "user_id":       self.user_id,
            "action":        self.action,
            "resource_type": self.resource_type,
            "resource_id":   self.resource_id,
            "details":       self.details,
            "ip_address":    self.ip_address,
            "timestamp":     self.timestamp,
        }


# ── AuditLog ──────────────────────────────────────────────────────────────────

class AuditLog:
    """Persist and query enterprise audit events."""

    def __init__(self, db_path: str = _DEFAULT_DB) -> None:
        self.db_path = db_path
        self._ensure_table()

    # ── Internal ──────────────────────────────────────────────────────────────

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
        try:
            d["details"] = json.loads(d.pop("details_json", "{}"))
        except Exception:
            d["details"] = {}
        return d

    # ── Write ─────────────────────────────────────────────────────────────────

    def record(self, event: AuditEvent) -> None:
        """Persist one audit event."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_events
                    (event_id, tenant_id, user_id, action,
                     resource_type, resource_id, details_json,
                     ip_address, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.tenant_id,
                    event.user_id,
                    event.action,
                    event.resource_type,
                    event.resource_id,
                    json.dumps(event.details),
                    event.ip_address,
                    event.timestamp,
                ),
            )
            conn.commit()

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_by_tenant(self, tenant_id: str, limit: int = 50) -> List[dict]:
        """Return events for a tenant, newest first."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM audit_events
                WHERE  tenant_id = ?
                ORDER  BY id DESC
                LIMIT  ?
                """,
                (tenant_id, limit),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_by_user(
        self, tenant_id: str, user_id: str, limit: int = 50
    ) -> List[dict]:
        """Return events for a specific user within a tenant, newest first."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM audit_events
                WHERE  tenant_id = ? AND user_id = ?
                ORDER  BY id DESC
                LIMIT  ?
                """,
                (tenant_id, user_id, limit),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def count_by_tenant(self, tenant_id: str) -> int:
        """Total events for a tenant."""
        with self._connect() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM audit_events WHERE tenant_id = ?",
                (tenant_id,),
            ).fetchone()[0]

    def count_by_action(self, tenant_id: str, action: str) -> int:
        """Events of a specific action type for a tenant."""
        with self._connect() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM audit_events WHERE tenant_id = ? AND action = ?",
                (tenant_id, action),
            ).fetchone()[0]
