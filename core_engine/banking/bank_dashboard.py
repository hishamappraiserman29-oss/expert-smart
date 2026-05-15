"""
bank_dashboard.py — Bank Portfolio Dashboard

Analytics and monitoring for bank collateral portfolios.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class BankPortfolioMetrics:
    """Aggregated metrics for one bank's collateral portfolio."""

    bank_id: str
    total_collateral_value: float
    total_loan_amount: float
    portfolio_ltv: float
    number_of_loans: int
    average_loan_size: float
    prime_loans: int
    conventional_loans: int
    conforming_loans: int
    high_ltv_loans: int
    active_loans: int
    paid_off_loans: int
    in_default_loans: int
    default_rate: float
    last_updated: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bank_id": self.bank_id,
            "portfolio_size": self.total_loan_amount,
            "total_collateral": self.total_collateral_value,
            "portfolio_ltv": round(self.portfolio_ltv, 2),
            "number_of_loans": self.number_of_loans,
            "average_loan_size": round(self.average_loan_size, 2),
            "risk_distribution": {
                "prime":        self.prime_loans,
                "conventional": self.conventional_loans,
                "conforming":   self.conforming_loans,
                "high_ltv":     self.high_ltv_loans,
            },
            "performance": {
                "active":      self.active_loans,
                "paid_off":    self.paid_off_loans,
                "in_default":  self.in_default_loans,
                "default_rate": round(self.default_rate, 2),
            },
            "last_updated": self.last_updated.isoformat(),
        }


class BankDashboard:
    """Compute and cache portfolio metrics for bank dashboards."""

    def __init__(self) -> None:
        self._portfolios: Dict[str, BankPortfolioMetrics] = {}

    def calculate_portfolio_metrics(
        self,
        bank_id: str,
        entries: List[Dict[str, Any]],
    ) -> BankPortfolioMetrics:
        """Derive portfolio metrics from collateral registry entry dicts.

        Args:
            bank_id: Bank identifier.
            entries: List of CollateralRegistryEntry.to_dict() outputs.

        Returns:
            BankPortfolioMetrics dataclass (also cached internally).
        """
        if not entries:
            metrics = BankPortfolioMetrics(
                bank_id=bank_id,
                total_collateral_value=0, total_loan_amount=0, portfolio_ltv=0,
                number_of_loans=0, average_loan_size=0,
                prime_loans=0, conventional_loans=0, conforming_loans=0, high_ltv_loans=0,
                active_loans=0, paid_off_loans=0, in_default_loans=0,
                default_rate=0, last_updated=datetime.utcnow(),
            )
            self._portfolios[bank_id] = metrics
            return metrics

        total_cv  = sum(e.get("collateral_value", 0) for e in entries)
        total_loan = sum(e.get("loan_amount",      0) for e in entries)
        ltv_pct    = (total_loan / total_cv * 100) if total_cv > 0 else 0.0

        prime  = sum(1 for e in entries if e.get("ltv_ratio", 0) <= 70)
        conv   = sum(1 for e in entries if 70  < e.get("ltv_ratio", 0) <= 85)
        conf   = sum(1 for e in entries if 85  < e.get("ltv_ratio", 0) <= 95)
        hlv    = sum(1 for e in entries if e.get("ltv_ratio", 0) > 95)

        active  = sum(1 for e in entries if e.get("status") == "active")
        paid    = sum(1 for e in entries if e.get("status") == "paid_off")
        default = sum(1 for e in entries if e.get("status") == "in_default")
        dr      = (default / len(entries) * 100) if entries else 0.0

        metrics = BankPortfolioMetrics(
            bank_id=bank_id,
            total_collateral_value=total_cv,
            total_loan_amount=total_loan,
            portfolio_ltv=ltv_pct,
            number_of_loans=len(entries),
            average_loan_size=total_loan / len(entries),
            prime_loans=prime,
            conventional_loans=conv,
            conforming_loans=conf,
            high_ltv_loans=hlv,
            active_loans=active,
            paid_off_loans=paid,
            in_default_loans=default,
            default_rate=dr,
            last_updated=datetime.utcnow(),
        )
        self._portfolios[bank_id] = metrics
        logger.info(
            "Dashboard metrics for bank %s: %d loans, LTV %.1f%%, default rate %.2f%%",
            bank_id, len(entries), ltv_pct, dr,
        )
        return metrics

    def get_dashboard_summary(self, bank_id: str) -> Dict[str, Any]:
        """Return cached dashboard for a bank, or error dict."""
        metrics = self._portfolios.get(bank_id)
        if metrics is None:
            return {"error": f"No portfolio data for bank {bank_id}"}
        alerts = []
        if metrics.portfolio_ltv > 85:
            alerts.append(f"Portfolio LTV {metrics.portfolio_ltv:.1f}% — exceeds 85% threshold")
        if metrics.default_rate > 2:
            alerts.append(f"Default rate {metrics.default_rate:.2f}% — elevated")
        return {
            "bank_id": bank_id,
            "summary": metrics.to_dict(),
            "alerts": alerts,
        }


bank_dashboard = BankDashboard()
