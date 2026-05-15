"""
fund_dashboard.py — Fund Portfolio Dashboard

Aggregates multi-fund metrics for manager and regulator dashboards.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional

from funds.fund_engine import FundValuationResult

logger = logging.getLogger(__name__)


@dataclass
class FundDashboardMetrics:
    manager_id: str
    total_aum: float
    total_nav: float
    fund_count: int
    fra_registered_count: int
    compliance_rate: float
    avg_sharpe_ratio: float
    avg_ytd_return: float
    avg_max_drawdown: float
    top_performer_id: Optional[str]
    bottom_performer_id: Optional[str]
    snapshot_date: date

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manager_id": self.manager_id,
            "total_aum": round(self.total_aum, 2),
            "total_nav": round(self.total_nav, 2),
            "fund_count": self.fund_count,
            "fra_registered_count": self.fra_registered_count,
            "compliance_rate": round(self.compliance_rate, 4),
            "avg_sharpe_ratio": round(self.avg_sharpe_ratio, 4),
            "avg_ytd_return_pct": round(self.avg_ytd_return * 100, 4),
            "avg_max_drawdown_pct": round(self.avg_max_drawdown * 100, 4),
            "top_performer_id": self.top_performer_id,
            "bottom_performer_id": self.bottom_performer_id,
            "snapshot_date": self.snapshot_date.isoformat(),
        }


class FundDashboard:
    """Compute and present aggregated metrics across managed funds."""

    def __init__(self) -> None:
        self._snapshots: Dict[str, FundDashboardMetrics] = {}

    def compute_metrics(
        self,
        manager_id: str,
        fund_results: List[FundValuationResult],
        snapshot_date: Optional[date] = None,
    ) -> FundDashboardMetrics:
        snap_date = snapshot_date or date.today()

        if not fund_results:
            metrics = FundDashboardMetrics(
                manager_id=manager_id,
                total_aum=0, total_nav=0, fund_count=0,
                fra_registered_count=0, compliance_rate=0.0,
                avg_sharpe_ratio=0.0, avg_ytd_return=0.0,
                avg_max_drawdown=0.0,
                top_performer_id=None, bottom_performer_id=None,
                snapshot_date=snap_date,
            )
            self._snapshots[manager_id] = metrics
            return metrics

        n = len(fund_results)
        total_aum = sum(r.aum for r in fund_results)
        total_nav = sum(r.nav for r in fund_results)
        fra_count = sum(1 for r in fund_results if r.fra_registered)
        avg_sharpe = sum(r.sharpe_ratio for r in fund_results) / n
        avg_return = sum(r.ytd_return for r in fund_results) / n
        avg_dd = sum(r.max_drawdown for r in fund_results) / n
        compliance_rate = fra_count / n

        top = max(fund_results, key=lambda r: r.ytd_return)
        bottom = min(fund_results, key=lambda r: r.ytd_return)

        metrics = FundDashboardMetrics(
            manager_id=manager_id,
            total_aum=total_aum,
            total_nav=total_nav,
            fund_count=n,
            fra_registered_count=fra_count,
            compliance_rate=compliance_rate,
            avg_sharpe_ratio=avg_sharpe,
            avg_ytd_return=avg_return,
            avg_max_drawdown=avg_dd,
            top_performer_id=top.fund_id,
            bottom_performer_id=bottom.fund_id,
            snapshot_date=snap_date,
        )
        self._snapshots[manager_id] = metrics
        logger.info(
            "Dashboard metrics for manager %s: %d funds, AUM=%.2f, avg Sharpe=%.3f",
            manager_id, n, total_aum, avg_sharpe,
        )
        return metrics

    def get_snapshot(self, manager_id: str) -> Optional[FundDashboardMetrics]:
        return self._snapshots.get(manager_id)

    def generate_summary_report(self, metrics: FundDashboardMetrics) -> str:
        lines = [
            "Fund Manager Dashboard Report",
            "=" * 40,
            f"Manager ID       : {metrics.manager_id}",
            f"Snapshot Date    : {metrics.snapshot_date}",
            f"Fund Count       : {metrics.fund_count}",
            f"Total AUM        : EGP {metrics.total_aum:,.2f}",
            f"Total NAV        : EGP {metrics.total_nav:,.2f}",
            f"FRA Registered   : {metrics.fra_registered_count}/{metrics.fund_count}",
            f"Compliance Rate  : {metrics.compliance_rate:.1%}",
            f"Avg Sharpe Ratio : {metrics.avg_sharpe_ratio:.4f}",
            f"Avg YTD Return   : {metrics.avg_ytd_return * 100:.2f}%",
            f"Avg Max Drawdown : {metrics.avg_max_drawdown * 100:.2f}%",
        ]
        if metrics.top_performer_id:
            lines.append(f"Top Performer    : {metrics.top_performer_id}")
        if metrics.bottom_performer_id:
            lines.append(f"Bottom Performer : {metrics.bottom_performer_id}")
        return "\n".join(lines)


fund_dashboard = FundDashboard()
