"""
audit_trail.py — Government Audit Trail

Immutable, append-only log of all government compliance actions.
Required by CBE, Tax Authority, and EGFSA for regulatory documentation.
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    COMPLIANCE_CHECK = "compliance_check"
    TAX_CALCULATION = "tax_calculation"
    FORM_GENERATED = "form_generated"
    PORTAL_ACCESS = "portal_access"
    STANDARD_VALIDATED = "standard_validated"
    CERTIFICATE_ISSUED = "certificate_issued"
    SIGNATURE_APPLIED = "signature_applied"
    DATA_EXPORT = "data_export"


@dataclass
class AuditEntry:
    """A single immutable audit log entry."""

    entry_id: str
    action: AuditAction
    entity_id: str          # property_id, agency_id, or form_id
    entity_type: str        # "property" | "agency" | "form" | "document"
    actor: str              # user or system identity
    details: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "action": self.action.value,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "actor": self.actor,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "error_message": self.error_message,
        }


class GovernmentAuditTrail:
    """Thread-safe, append-only audit trail for government compliance actions."""

    def __init__(self) -> None:
        self._entries: List[AuditEntry] = []
        self._lock = threading.Lock()

    def record(
        self,
        action: AuditAction,
        entity_id: str,
        entity_type: str,
        actor: str = "system",
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> AuditEntry:
        """Append a new audit entry and return it."""
        entry = AuditEntry(
            entry_id=str(uuid.uuid4()),
            action=action,
            entity_id=entity_id,
            entity_type=entity_type,
            actor=actor,
            details=details or {},
            success=success,
            error_message=error_message,
        )
        with self._lock:
            self._entries.append(entry)
        logger.info(
            "Audit [%s] %s on %s/%s by %s",
            action.value, "OK" if success else "FAIL",
            entity_type, entity_id, actor,
        )
        return entry

    def get_by_entity(self, entity_id: str) -> List[AuditEntry]:
        """Return all entries for a given entity."""
        with self._lock:
            return [e for e in self._entries if e.entity_id == entity_id]

    def get_by_action(self, action: AuditAction) -> List[AuditEntry]:
        """Return all entries for a given action type."""
        with self._lock:
            return [e for e in self._entries if e.action == action]

    def get_all(self) -> List[AuditEntry]:
        """Return all audit entries (newest last)."""
        with self._lock:
            return list(self._entries)

    def count(self) -> int:
        """Return total number of recorded entries."""
        with self._lock:
            return len(self._entries)

    def to_report(self) -> str:
        """Generate a plain-text audit report."""
        with self._lock:
            entries = list(self._entries)
        lines = [
            "GOVERNMENT AUDIT TRAIL REPORT",
            "=" * 64,
            f"Total entries: {len(entries)}",
            "",
        ]
        for e in entries:
            status = "OK" if e.success else "FAIL"
            lines.append(
                f"[{e.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] "
                f"{status} | {e.action.value} | {e.entity_type}/{e.entity_id} | {e.actor}"
            )
        lines.append("=" * 64)
        return "\n".join(lines)


government_audit_trail = GovernmentAuditTrail()
