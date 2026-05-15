"""
collateral_registry.py — Collateral Registry

Central registry for tracking collateral across all loans and banks.
Thread-safe in-memory store with property, loan, and bank indexes.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CollateralRegistryEntry:
    """One record in the collateral registry."""

    collateral_id: str
    property_id: str
    owner_id: str
    loan_id: str
    bank_id: str
    collateral_value: float
    loan_amount: float
    ltv_ratio: float
    status: str                   # "active" | "paid_off" | "in_default" | "foreclosed"
    loan_origination_date: datetime
    loan_maturity_date: datetime
    last_valuation_date: datetime
    next_valuation_due: datetime
    registration_date: datetime = field(default_factory=datetime.utcnow)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "collateral_id": self.collateral_id,
            "property_id": self.property_id,
            "owner_id": self.owner_id,
            "loan_id": self.loan_id,
            "bank_id": self.bank_id,
            "collateral_value": self.collateral_value,
            "loan_amount": self.loan_amount,
            "ltv_ratio": self.ltv_ratio,
            "status": self.status,
            "loan_origination_date": self.loan_origination_date.isoformat(),
            "loan_maturity_date": self.loan_maturity_date.isoformat(),
            "last_valuation_date": self.last_valuation_date.isoformat(),
            "next_valuation_due": self.next_valuation_due.isoformat(),
            "registration_date": self.registration_date.isoformat(),
            "notes": self.notes,
        }


class CollateralRegistry:
    """Central, thread-safe collateral registry."""

    def __init__(self) -> None:
        self._entries: Dict[str, CollateralRegistryEntry] = {}
        self._by_property: Dict[str, List[str]] = {}
        self._by_loan:     Dict[str, List[str]] = {}
        self._by_bank:     Dict[str, List[str]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def register_collateral(
        self,
        collateral_id: str,
        property_id: str,
        owner_id: str,
        loan_id: str,
        bank_id: str,
        collateral_value: float,
        loan_amount: float,
        ltv_ratio: float,
        loan_maturity_date: datetime,
        valuation_validity_days: int = 180,
        notes: str = "",
    ) -> CollateralRegistryEntry:
        """Register a new collateral entry."""
        now = datetime.utcnow()
        entry = CollateralRegistryEntry(
            collateral_id=collateral_id,
            property_id=property_id,
            owner_id=owner_id,
            loan_id=loan_id,
            bank_id=bank_id,
            collateral_value=collateral_value,
            loan_amount=loan_amount,
            ltv_ratio=ltv_ratio,
            status="active",
            loan_origination_date=now,
            loan_maturity_date=loan_maturity_date,
            last_valuation_date=now,
            next_valuation_due=now + timedelta(days=valuation_validity_days),
            notes=notes,
        )
        with self._lock:
            self._entries[collateral_id] = entry
            self._by_property.setdefault(property_id, []).append(collateral_id)
            self._by_loan.setdefault(loan_id, []).append(collateral_id)
            self._by_bank.setdefault(bank_id, []).append(collateral_id)
        logger.info("Registered collateral %s → loan %s (bank %s)", collateral_id, loan_id, bank_id)
        return entry

    def update_status(self, collateral_id: str, new_status: str) -> bool:
        """Update a single entry's status. Returns False if not found."""
        with self._lock:
            if collateral_id not in self._entries:
                return False
            self._entries[collateral_id].status = new_status
        logger.info("Collateral %s status → %s", collateral_id, new_status)
        return True

    def update_loan_status(self, loan_id: str, new_status: str) -> int:
        """Update status of every collateral entry for a loan. Returns count updated."""
        updated = 0
        with self._lock:
            for cid in self._by_loan.get(loan_id, []):
                if cid in self._entries:
                    self._entries[cid].status = new_status
                    updated += 1
        logger.info("Updated %d collateral entries for loan %s → %s", updated, loan_id, new_status)
        return updated

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, collateral_id: str) -> Optional[CollateralRegistryEntry]:
        with self._lock:
            return self._entries.get(collateral_id)

    def get_by_loan(self, loan_id: str) -> List[CollateralRegistryEntry]:
        with self._lock:
            return [self._entries[c] for c in self._by_loan.get(loan_id, []) if c in self._entries]

    def get_by_property(self, property_id: str) -> List[CollateralRegistryEntry]:
        with self._lock:
            return [self._entries[c] for c in self._by_property.get(property_id, []) if c in self._entries]

    def get_bank_portfolio(self, bank_id: str) -> Dict[str, Any]:
        """Summary of all collateral registered for a bank."""
        with self._lock:
            entries = [self._entries[c] for c in self._by_bank.get(bank_id, []) if c in self._entries]

        total_cv = sum(e.collateral_value for e in entries)
        total_loan = sum(e.loan_amount for e in entries)
        active = sum(1 for e in entries if e.status == "active")

        return {
            "bank_id": bank_id,
            "total_collateral_value": total_cv,
            "total_loan_amount": total_loan,
            "portfolio_ltv": (total_loan / total_cv * 100) if total_cv > 0 else 0.0,
            "total_entries": len(entries),
            "active_loans": active,
            "entries": [e.to_dict() for e in entries],
        }

    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    def overdue_revaluations(self) -> List[CollateralRegistryEntry]:
        """Return entries whose next_valuation_due has passed."""
        now = datetime.utcnow()
        with self._lock:
            return [e for e in self._entries.values() if e.next_valuation_due < now]


collateral_registry = CollateralRegistry()
