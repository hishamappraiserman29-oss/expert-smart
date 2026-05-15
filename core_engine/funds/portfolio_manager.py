"""
portfolio_manager.py — Multi-Fund Portfolio Manager

Tracks allocation targets, drift, and rebalancing for fund portfolios.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AllocationTarget:
    fund_id: str
    target_weight: float
    min_weight: float
    max_weight: float


@dataclass
class PortfolioHolding:
    fund_id: str
    nav: float
    current_weight: float
    target_weight: float
    drift: float
    rebalance_needed: bool


@dataclass
class PortfolioSnapshot:
    portfolio_id: str
    total_nav: float
    holdings: List[PortfolioHolding]
    snapshot_date: date
    overall_drift: float
    rebalance_required: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_id": self.portfolio_id,
            "total_nav": round(self.total_nav, 2),
            "snapshot_date": self.snapshot_date.isoformat(),
            "overall_drift": round(self.overall_drift, 4),
            "rebalance_required": self.rebalance_required,
            "holdings": [
                {
                    "fund_id": h.fund_id,
                    "nav": round(h.nav, 2),
                    "current_weight": round(h.current_weight, 4),
                    "target_weight": round(h.target_weight, 4),
                    "drift": round(h.drift, 4),
                    "rebalance_needed": h.rebalance_needed,
                }
                for h in self.holdings
            ],
        }


class PortfolioManager:
    """Manage multi-fund portfolios with target weights and drift monitoring."""

    DRIFT_THRESHOLD = 0.05

    def __init__(self) -> None:
        self._portfolios: Dict[str, List[AllocationTarget]] = {}
        self._lock = threading.Lock()

    def create_portfolio(
        self, portfolio_id: str, targets: List[AllocationTarget]
    ) -> None:
        total = sum(t.target_weight for t in targets)
        if not (0.999 < total < 1.001):
            raise ValueError(f"Target weights must sum to 1.0, got {total:.4f}")
        with self._lock:
            self._portfolios[portfolio_id] = targets

    def get_snapshot(
        self,
        portfolio_id: str,
        fund_navs: Dict[str, float],
        snapshot_date: Optional[date] = None,
    ) -> PortfolioSnapshot:
        with self._lock:
            targets = self._portfolios.get(portfolio_id)
        if targets is None:
            raise ValueError(f"Portfolio {portfolio_id!r} not found")

        snap_date = snapshot_date or date.today()
        total_nav = sum(fund_navs.get(t.fund_id, 0.0) for t in targets)
        holdings: List[PortfolioHolding] = []
        max_drift = 0.0

        for tgt in targets:
            nav = fund_navs.get(tgt.fund_id, 0.0)
            current_w = nav / total_nav if total_nav > 0 else 0.0
            drift = abs(current_w - tgt.target_weight)
            max_drift = max(max_drift, drift)
            holdings.append(
                PortfolioHolding(
                    fund_id=tgt.fund_id,
                    nav=nav,
                    current_weight=current_w,
                    target_weight=tgt.target_weight,
                    drift=drift,
                    rebalance_needed=drift > self.DRIFT_THRESHOLD,
                )
            )

        return PortfolioSnapshot(
            portfolio_id=portfolio_id,
            total_nav=total_nav,
            holdings=holdings,
            snapshot_date=snap_date,
            overall_drift=max_drift,
            rebalance_required=max_drift > self.DRIFT_THRESHOLD,
        )

    def list_portfolios(self) -> List[str]:
        with self._lock:
            return list(self._portfolios.keys())

    def count(self) -> int:
        with self._lock:
            return len(self._portfolios)


portfolio_manager = PortfolioManager()
