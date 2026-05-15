"""
government_portal.py — Government Agency Portal Manager

Dashboard and management interface for government agency clients.
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class GovernmentAgencyPortal:
    """In-memory state for one government agency's portal."""

    agency_name: str
    agency_id: str
    contact_person: str
    contact_email: str
    authorized_users: int = 0
    valuations_processed: int = 0
    forms_generated: int = 0
    compliance_checks: int = 0
    tax_calculations: int = 0
    last_access: datetime = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.last_access is None:
            self.last_access = datetime.utcnow()

    def record_activity(self, activity_type: str) -> None:
        """Increment the relevant counter for an activity."""
        if activity_type == "valuation":
            self.valuations_processed += 1
        elif activity_type == "form":
            self.forms_generated += 1
        elif activity_type == "compliance":
            self.compliance_checks += 1
        elif activity_type == "tax":
            self.tax_calculations += 1
        self.last_access = datetime.utcnow()

    def get_dashboard_summary(self) -> Dict[str, Any]:
        return {
            "agency": self.agency_name,
            "agency_id": self.agency_id,
            "contact": self.contact_person,
            "email": self.contact_email,
            "statistics": {
                "authorized_users": self.authorized_users,
                "valuations_processed": self.valuations_processed,
                "forms_generated": self.forms_generated,
                "compliance_checks": self.compliance_checks,
                "tax_calculations": self.tax_calculations,
                "last_accessed": self.last_access.isoformat(),
            },
            "features_available": [
                "Compliance checking",
                "Tax calculation",
                "Form generation",
                "Audit trail review",
                "Digital signatures",
                "Report export",
            ],
        }


class GovernmentPortalManager:
    """Create and manage government agency portals."""

    def __init__(self) -> None:
        self._portals: Dict[str, GovernmentAgencyPortal] = {}
        self._lock = threading.Lock()

    def create_portal(
        self,
        agency_name: str,
        contact_person: str,
        contact_email: str,
    ) -> GovernmentAgencyPortal:
        """Create a new portal for a government agency."""
        agency_id = str(uuid.uuid4())
        portal = GovernmentAgencyPortal(
            agency_name=agency_name,
            agency_id=agency_id,
            contact_person=contact_person,
            contact_email=contact_email,
        )
        with self._lock:
            self._portals[agency_id] = portal
        logger.info("Government portal created: %s (%s)", agency_name, agency_id)
        return portal

    def get_portal(self, agency_id: str) -> Optional[GovernmentAgencyPortal]:
        """Return a portal by ID, or None."""
        with self._lock:
            return self._portals.get(agency_id)

    def get_portal_statistics(self, agency_id: str) -> Dict[str, Any]:
        """Return dashboard summary for an agency, or empty dict."""
        portal = self.get_portal(agency_id)
        return portal.get_dashboard_summary() if portal else {}

    def list_portals(self) -> List[Dict[str, Any]]:
        """Return a list of all portal summaries."""
        with self._lock:
            return [p.get_dashboard_summary() for p in self._portals.values()]

    def record_activity(self, agency_id: str, activity_type: str) -> bool:
        """Record an activity for an agency. Returns False if agency not found."""
        portal = self.get_portal(agency_id)
        if portal is None:
            return False
        portal.record_activity(activity_type)
        return True

    def count(self) -> int:
        """Return total number of registered agency portals."""
        with self._lock:
            return len(self._portals)


government_portal_manager = GovernmentPortalManager()
