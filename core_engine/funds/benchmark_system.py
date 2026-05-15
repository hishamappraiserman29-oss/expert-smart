"""
benchmark_system.py — Fund Benchmark System

Tracks benchmark indices and computes fund performance vs benchmark.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkIndex:
    index_id: str
    name: str
    ytd_return: float
    one_year_return: float
    three_year_return: float
    asset_class: str
    region: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index_id": self.index_id,
            "name": self.name,
            "ytd_return_pct": round(self.ytd_return * 100, 4),
            "one_year_return_pct": round(self.one_year_return * 100, 4),
            "three_year_return_pct": round(self.three_year_return * 100, 4),
            "asset_class": self.asset_class,
            "region": self.region,
        }


@dataclass
class BenchmarkComparison:
    fund_id: str
    index_id: str
    fund_ytd_return: float
    benchmark_ytd_return: float
    alpha: float
    tracking_error: float
    information_ratio: float
    outperforming: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fund_id": self.fund_id,
            "index_id": self.index_id,
            "fund_ytd_return_pct": round(self.fund_ytd_return * 100, 4),
            "benchmark_ytd_return_pct": round(self.benchmark_ytd_return * 100, 4),
            "alpha_pct": round(self.alpha * 100, 4),
            "tracking_error_pct": round(self.tracking_error * 100, 4),
            "information_ratio": round(self.information_ratio, 4),
            "outperforming": self.outperforming,
        }


class BenchmarkSystem:
    """Register benchmark indices and compare fund performance against them."""

    def __init__(self) -> None:
        self._indices: Dict[str, BenchmarkIndex] = {}
        self._lock = threading.Lock()

    def register_index(self, index: BenchmarkIndex) -> None:
        with self._lock:
            self._indices[index.index_id] = index
        logger.info("Benchmark index registered: %s", index.index_id)

    def get_index(self, index_id: str) -> Optional[BenchmarkIndex]:
        with self._lock:
            return self._indices.get(index_id)

    def compare_fund(
        self,
        fund_id: str,
        fund_ytd_return: float,
        fund_volatility: float,
        index_id: str,
    ) -> BenchmarkComparison:
        index = self.get_index(index_id)
        if index is None:
            raise ValueError(f"Benchmark index {index_id!r} not found")

        alpha = fund_ytd_return - index.ytd_return
        # Tracking error approximation: std dev of return differential
        tracking_error = abs(fund_volatility - 0.02)
        information_ratio = alpha / tracking_error if tracking_error > 0 else 0.0

        return BenchmarkComparison(
            fund_id=fund_id,
            index_id=index_id,
            fund_ytd_return=fund_ytd_return,
            benchmark_ytd_return=index.ytd_return,
            alpha=alpha,
            tracking_error=tracking_error,
            information_ratio=information_ratio,
            outperforming=alpha > 0,
        )

    def list_indices(self) -> List[str]:
        with self._lock:
            return list(self._indices.keys())

    def count(self) -> int:
        with self._lock:
            return len(self._indices)


benchmark_system = BenchmarkSystem()
