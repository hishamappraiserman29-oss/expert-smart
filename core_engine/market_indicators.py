"""
market_indicators.py — Market Price Indicators Backend (Phase 41.0)

Read-only market indicators for Mass Appraisal charts.
Data source: static sample values representative of the Egyptian RE market.
TODO: Add controlled market data collector for live updates.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MarketIndicatorPoint:
    """Single time-series data point for all four indicators."""

    date: str           # YYYY-MM-DD
    stratification: float   # Market price variation index (%)
    rppi: float             # Residential Property Price Index (%)
    avm: float              # AVM performance index (%)
    cma: float              # Comparative Market Analysis effectiveness (%)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "stratification": self.stratification,
            "rppi": self.rppi,
            "avm": self.avm,
            "cma": self.cma,
        }


class MarketIndicatorsBackend:
    """
    Market indicators backend for Mass Appraisal charts.

    Provides:
    - Latest indicator snapshot
    - 12-month historical time series
    - Min/max/avg statistics per indicator

    Data source: static representative values for the Egyptian RE market.
    """

    def __init__(self) -> None:
        self._data: List[MarketIndicatorPoint] = self._build_sample_data()
        logger.info("MarketIndicatorsBackend initialized (%d points)", len(self._data))

    # ── data initialisation ────────────────────────────────────────────────────

    def _build_sample_data(self) -> List[MarketIndicatorPoint]:
        """
        Build 12 months of sample indicator data.

        Values are grounded in typical Egyptian RE market ranges:
        - Stratification 8–14 %
        - RPPI 10–18 %
        - AVM  9–13 %
        - CMA  8–12 %
        """
        data: List[MarketIndicatorPoint] = []
        base = datetime.utcnow()

        for months_back in range(12, 0, -1):
            date_str = (base - timedelta(days=30 * months_back)).strftime("%Y-%m-%d")
            offset = 12 - months_back  # 0 for oldest, 11 for most recent

            strat = round(min(14.0, max(8.0, 8.44 + offset * 0.27)), 2)
            rppi  = round(min(18.0, max(10.0, 10.79 + offset * 0.30)), 2)
            avm   = round(min(13.0, max(9.0, 9.17  + offset * 0.18)), 2)
            cma   = round(min(12.0, max(8.0, 8.62  + offset * 0.17)), 2)

            data.append(MarketIndicatorPoint(date=date_str, stratification=strat, rppi=rppi, avm=avm, cma=cma))

        return data

    # ── public API ─────────────────────────────────────────────────────────────

    def get_latest_indicators(self) -> Dict[str, Any]:
        if not self._data:
            return {"status": "error", "message": "No data available", "indicators": {}}
        latest = self._data[-1]
        return {
            "status": "success",
            "last_updated": datetime.utcnow().isoformat(),
            "source": "sample_data",
            "indicators": {
                "stratification": latest.stratification,
                "rppi": latest.rppi,
                "avm": latest.avm,
                "cma": latest.cma,
            },
        }

    def get_indicators_history(self, days_back: int = 365) -> Dict[str, Any]:
        if not self._data:
            return {"status": "error", "message": "No data available", "history": []}
        history = [p.to_dict() for p in self._data]
        return {
            "status": "success",
            "last_updated": datetime.utcnow().isoformat(),
            "source": "sample_data",
            "count": len(history),
            "history": history,
        }

    def get_indicator_by_date(self, date_str: str) -> Optional[MarketIndicatorPoint]:
        for point in self._data:
            if point.date == date_str:
                return point
        return None

    def get_statistics(self) -> Dict[str, Any]:
        if not self._data:
            return {}

        def _stats(values: List[float]) -> Dict[str, float]:
            return {
                "min": round(min(values), 2),
                "max": round(max(values), 2),
                "avg": round(sum(values) / len(values), 2),
            }

        return {
            "stratification": _stats([p.stratification for p in self._data]),
            "rppi":           _stats([p.rppi           for p in self._data]),
            "avm":            _stats([p.avm            for p in self._data]),
            "cma":            _stats([p.cma            for p in self._data]),
            "data_points": len(self._data),
            "latest_date": self._data[-1].date,
        }


market_indicators = MarketIndicatorsBackend()
