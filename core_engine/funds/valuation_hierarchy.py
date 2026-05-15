"""
valuation_hierarchy.py — IFRS 13 Valuation Hierarchy Manager

Tracks asset-level hierarchy assignments and monitors Level 3 concentration.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .fair_value_calculator import ValuationLevel

logger = logging.getLogger(__name__)

LEVEL_3_CONCENTRATION_LIMIT = 0.30


@dataclass
class HierarchyEntry:
    asset_id: str
    fund_id: str
    asset_type: str
    valuation_level: ValuationLevel
    fair_value: float
    last_review_date: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "fund_id": self.fund_id,
            "asset_type": self.asset_type,
            "valuation_level": self.valuation_level.value,
            "fair_value": round(self.fair_value, 2),
            "last_review_date": self.last_review_date,
        }


@dataclass
class HierarchySummary:
    fund_id: str
    total_fair_value: float
    level_1_value: float
    level_2_value: float
    level_3_value: float
    level_3_concentration: float
    concentration_breach: bool
    asset_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fund_id": self.fund_id,
            "total_fair_value": round(self.total_fair_value, 2),
            "level_1_value": round(self.level_1_value, 2),
            "level_2_value": round(self.level_2_value, 2),
            "level_3_value": round(self.level_3_value, 2),
            "level_3_concentration": round(self.level_3_concentration, 4),
            "concentration_breach": self.concentration_breach,
            "asset_count": self.asset_count,
        }


class ValuationHierarchyManager:
    """Manage IFRS 13 hierarchy assignments for fund assets."""

    def __init__(self) -> None:
        self._entries: Dict[str, HierarchyEntry] = {}
        self._lock = threading.Lock()

    def register_asset(
        self,
        asset_id: str,
        fund_id: str,
        asset_type: str,
        valuation_level: ValuationLevel,
        fair_value: float,
        review_date: str,
    ) -> HierarchyEntry:
        entry = HierarchyEntry(
            asset_id=asset_id,
            fund_id=fund_id,
            asset_type=asset_type,
            valuation_level=valuation_level,
            fair_value=fair_value,
            last_review_date=review_date,
        )
        with self._lock:
            self._entries[asset_id] = entry
        logger.info("Hierarchy: %s registered at %s for fund %s", asset_id, valuation_level.value, fund_id)
        return entry

    def get_fund_summary(self, fund_id: str) -> HierarchySummary:
        with self._lock:
            fund_entries = [e for e in self._entries.values() if e.fund_id == fund_id]

        l1 = sum(e.fair_value for e in fund_entries if e.valuation_level == ValuationLevel.LEVEL_1)
        l2 = sum(e.fair_value for e in fund_entries if e.valuation_level == ValuationLevel.LEVEL_2)
        l3 = sum(e.fair_value for e in fund_entries if e.valuation_level == ValuationLevel.LEVEL_3)
        total = l1 + l2 + l3
        concentration = l3 / total if total > 0 else 0.0

        return HierarchySummary(
            fund_id=fund_id,
            total_fair_value=total,
            level_1_value=l1,
            level_2_value=l2,
            level_3_value=l3,
            level_3_concentration=concentration,
            concentration_breach=concentration > LEVEL_3_CONCENTRATION_LIMIT,
            asset_count=len(fund_entries),
        )

    def get_asset(self, asset_id: str) -> Optional[HierarchyEntry]:
        with self._lock:
            return self._entries.get(asset_id)

    def update_level(
        self, asset_id: str, new_level: ValuationLevel, new_fair_value: float, review_date: str
    ) -> bool:
        with self._lock:
            entry = self._entries.get(asset_id)
            if entry is None:
                return False
            entry.valuation_level = new_level
            entry.fair_value = new_fair_value
            entry.last_review_date = review_date
        return True

    def count(self) -> int:
        with self._lock:
            return len(self._entries)


valuation_hierarchy = ValuationHierarchyManager()
