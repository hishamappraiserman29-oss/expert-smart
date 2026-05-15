"""
loan_servicing.py — Loan Servicing Manager

Lifecycle management for collateral-backed loans: origination, payment tracking,
covenant monitoring, and maturity handling.
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LoanStatus(str, Enum):
    PENDING      = "pending"
    ACTIVE       = "active"
    DELINQUENT   = "delinquent"   # 1-89 days past due
    IN_DEFAULT   = "in_default"   # >= 90 days past due
    PAID_OFF     = "paid_off"
    FORECLOSED   = "foreclosed"
    RESTRUCTURED = "restructured"


@dataclass
class PaymentRecord:
    """A single loan payment."""

    payment_id: str
    loan_id: str
    amount: float
    payment_date: datetime
    principal_portion: float
    interest_portion: float
    outstanding_after: float
    on_time: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "payment_id": self.payment_id,
            "loan_id": self.loan_id,
            "amount": self.amount,
            "payment_date": self.payment_date.isoformat(),
            "principal_portion": self.principal_portion,
            "interest_portion": self.interest_portion,
            "outstanding_after": self.outstanding_after,
            "on_time": self.on_time,
        }


@dataclass
class Loan:
    """A collateral-backed loan record."""

    loan_id: str
    bank_id: str
    borrower_id: str
    collateral_id: str
    principal: float
    interest_rate: float        # Annual percentage
    term_months: int
    origination_date: datetime
    maturity_date: datetime
    status: LoanStatus = LoanStatus.ACTIVE
    outstanding_balance: float = 0.0
    payment_history: List[PaymentRecord] = field(default_factory=list)
    days_past_due: int = 0

    def __post_init__(self) -> None:
        if self.outstanding_balance == 0.0:
            self.outstanding_balance = self.principal

    @property
    def monthly_payment(self) -> float:
        """Standard amortisation monthly payment (EGP)."""
        r = self.interest_rate / 100 / 12
        n = self.term_months
        if r == 0:
            return self.principal / n
        return self.principal * r * (1 + r) ** n / ((1 + r) ** n - 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "loan_id": self.loan_id,
            "bank_id": self.bank_id,
            "borrower_id": self.borrower_id,
            "collateral_id": self.collateral_id,
            "principal": self.principal,
            "interest_rate": self.interest_rate,
            "term_months": self.term_months,
            "origination_date": self.origination_date.isoformat(),
            "maturity_date": self.maturity_date.isoformat(),
            "status": self.status.value,
            "outstanding_balance": self.outstanding_balance,
            "monthly_payment": round(self.monthly_payment, 2),
            "days_past_due": self.days_past_due,
            "payment_count": len(self.payment_history),
        }


class LoanServicingManager:
    """Originate, track, and service collateral-backed loans."""

    def __init__(self) -> None:
        self._loans: Dict[str, Loan] = {}
        self._lock = threading.Lock()

    def originate(
        self,
        bank_id: str,
        borrower_id: str,
        collateral_id: str,
        principal: float,
        interest_rate: float,
        term_months: int,
        loan_id: Optional[str] = None,
    ) -> Loan:
        """Create a new loan record."""
        lid = loan_id or str(uuid.uuid4())
        now = datetime.utcnow()
        loan = Loan(
            loan_id=lid,
            bank_id=bank_id,
            borrower_id=borrower_id,
            collateral_id=collateral_id,
            principal=principal,
            interest_rate=interest_rate,
            term_months=term_months,
            origination_date=now,
            maturity_date=now + timedelta(days=term_months * 30),
        )
        with self._lock:
            self._loans[lid] = loan
        logger.info("Loan originated: %s (EGP %,.0f, %d months)", lid, principal, term_months)
        return loan

    def record_payment(
        self,
        loan_id: str,
        amount: float,
        on_time: bool = True,
    ) -> Optional[PaymentRecord]:
        """Record a payment against a loan."""
        with self._lock:
            loan = self._loans.get(loan_id)
            if loan is None:
                return None
            monthly_interest = loan.outstanding_balance * (loan.interest_rate / 100 / 12)
            principal_portion = max(0.0, amount - monthly_interest)
            interest_portion = min(amount, monthly_interest)
            loan.outstanding_balance = max(0.0, loan.outstanding_balance - principal_portion)
            if loan.outstanding_balance <= 0:
                loan.status = LoanStatus.PAID_OFF
            if on_time and loan.status not in (LoanStatus.PAID_OFF,):
                loan.days_past_due = 0
            payment = PaymentRecord(
                payment_id=str(uuid.uuid4()),
                loan_id=loan_id,
                amount=amount,
                payment_date=datetime.utcnow(),
                principal_portion=principal_portion,
                interest_portion=interest_portion,
                outstanding_after=loan.outstanding_balance,
                on_time=on_time,
            )
            loan.payment_history.append(payment)
        return payment

    def mark_delinquent(self, loan_id: str, days_past_due: int) -> bool:
        """Flag a loan as delinquent with DPD count."""
        with self._lock:
            loan = self._loans.get(loan_id)
            if loan is None:
                return False
            loan.days_past_due = days_past_due
            if days_past_due >= 90:
                loan.status = LoanStatus.IN_DEFAULT
            elif days_past_due > 0:
                loan.status = LoanStatus.DELINQUENT
        return True

    def get(self, loan_id: str) -> Optional[Loan]:
        with self._lock:
            return self._loans.get(loan_id)

    def get_bank_loans(self, bank_id: str) -> List[Loan]:
        with self._lock:
            return [l for l in self._loans.values() if l.bank_id == bank_id]

    def count(self) -> int:
        with self._lock:
            return len(self._loans)


loan_servicing_manager = LoanServicingManager()
