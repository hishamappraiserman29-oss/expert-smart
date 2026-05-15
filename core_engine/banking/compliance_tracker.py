"""
compliance_tracker.py — CBE Loan Compliance Tracker

Track regulatory compliance for each loan against CBE lending requirements.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CBERequirement(str, Enum):
    LTV_LIMIT              = "ltv_limit"               # LTV <= CBE threshold
    COLLATERAL_VALUATION   = "collateral_valuation"    # Fresh valuation exists
    APPRAISER_APPROVAL     = "appraiser_approval"      # CBE-approved appraiser
    DOCUMENTATION_COMPLETE = "documentation_complete"  # All docs on file
    RISK_CLASSIFICATION    = "risk_classification"     # Risk class assigned
    INSURANCE_COVERAGE     = "insurance_coverage"      # Property insured
    REVALUATION_SCHEDULE   = "revaluation_schedule"    # Revaluation not overdue


@dataclass
class LoanComplianceStatus:
    """Compliance status for a single loan."""

    loan_id: str
    bank_id: str
    checked_at: datetime
    requirements_met: List[CBERequirement]
    requirements_failed: List[CBERequirement]
    compliance_score: float   # 0-100
    is_compliant: bool
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "loan_id": self.loan_id,
            "bank_id": self.bank_id,
            "checked_at": self.checked_at.isoformat(),
            "requirements_met": [r.value for r in self.requirements_met],
            "requirements_failed": [r.value for r in self.requirements_failed],
            "compliance_score": round(self.compliance_score, 1),
            "is_compliant": self.is_compliant,
            "notes": self.notes,
        }


class CBEComplianceTracker:
    """Check and track CBE compliance for bank loan portfolios."""

    # Maximum LTV per collateral type (CBE guidelines)
    _MAX_LTV: Dict[str, float] = {
        "residential_property": 80.0,
        "commercial_property":  70.0,
        "industrial_property":  65.0,
        "agricultural_land":    60.0,
        "undeveloped_land":     55.0,
        "mixed_use":            70.0,
    }

    def __init__(self) -> None:
        self._records: Dict[str, LoanComplianceStatus] = {}
        self._lock = threading.Lock()

    def check_loan(
        self,
        loan_id: str,
        bank_id: str,
        ltv_ratio: float,
        collateral_type: str = "residential_property",
        has_valuation: bool = True,
        cbe_approved_appraiser: bool = True,
        documentation_complete: bool = True,
        risk_class_assigned: bool = True,
        property_insured: bool = True,
        revaluation_overdue: bool = False,
    ) -> LoanComplianceStatus:
        """Evaluate CBE compliance for a single loan.

        Args:
            loan_id: Loan identifier.
            bank_id: Bank identifier.
            ltv_ratio: Current LTV percentage.
            collateral_type: Property type string.
            has_valuation: Is a current valuation on file?
            cbe_approved_appraiser: Was a CBE-approved appraiser used?
            documentation_complete: Are all required documents complete?
            risk_class_assigned: Has risk classification been performed?
            property_insured: Is the collateral property insured?
            revaluation_overdue: Is the revaluation schedule overdue?

        Returns:
            LoanComplianceStatus.
        """
        max_ltv = self._MAX_LTV.get(collateral_type.lower(), 75.0)
        met: List[CBERequirement] = []
        failed: List[CBERequirement] = []
        notes: List[str] = []

        def _check(req: CBERequirement, condition: bool, msg: str) -> None:
            if condition:
                met.append(req)
            else:
                failed.append(req)
                notes.append(msg)

        _check(CBERequirement.LTV_LIMIT, ltv_ratio <= max_ltv,
               f"LTV {ltv_ratio:.1f}% exceeds CBE limit {max_ltv:.0f}% for {collateral_type}")
        _check(CBERequirement.COLLATERAL_VALUATION, has_valuation,
               "No current collateral valuation on file")
        _check(CBERequirement.APPRAISER_APPROVAL, cbe_approved_appraiser,
               "Appraiser does not hold CBE approval")
        _check(CBERequirement.DOCUMENTATION_COMPLETE, documentation_complete,
               "Loan documentation is incomplete")
        _check(CBERequirement.RISK_CLASSIFICATION, risk_class_assigned,
               "Risk class not assigned")
        _check(CBERequirement.INSURANCE_COVERAGE, property_insured,
               "Collateral property is not insured")
        _check(CBERequirement.REVALUATION_SCHEDULE, not revaluation_overdue,
               "Collateral revaluation is overdue")

        total = len(met) + len(failed)
        score = (len(met) / total * 100) if total else 0.0
        is_compliant = len(failed) == 0

        status = LoanComplianceStatus(
            loan_id=loan_id,
            bank_id=bank_id,
            checked_at=datetime.utcnow(),
            requirements_met=met,
            requirements_failed=failed,
            compliance_score=score,
            is_compliant=is_compliant,
            notes=notes,
        )
        with self._lock:
            self._records[loan_id] = status
        logger.info(
            "CBE compliance %s: %.1f%% (%s)",
            loan_id, score, "PASS" if is_compliant else "FAIL",
        )
        return status

    def get_bank_compliance_summary(self, bank_id: str) -> Dict[str, Any]:
        """Return a portfolio-level compliance summary for a bank."""
        with self._lock:
            loans = [s for s in self._records.values() if s.bank_id == bank_id]
        if not loans:
            return {"bank_id": bank_id, "total_loans": 0, "compliant": 0, "compliance_rate": 0.0}
        compliant = sum(1 for l in loans if l.is_compliant)
        return {
            "bank_id": bank_id,
            "total_loans": len(loans),
            "compliant": compliant,
            "non_compliant": len(loans) - compliant,
            "compliance_rate": round(compliant / len(loans) * 100, 1),
            "average_score": round(sum(l.compliance_score for l in loans) / len(loans), 1),
        }

    def count(self) -> int:
        with self._lock:
            return len(self._records)


cbe_compliance_tracker = CBEComplianceTracker()
