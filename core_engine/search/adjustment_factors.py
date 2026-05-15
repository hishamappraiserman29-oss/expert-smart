"""
adjustment_factors.py — Price Adjustment Factors (Phase 37)

Automated comparable price adjustments across 7 categories.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AdjustmentCategory(str, Enum):
    TIME = "time"
    LOCATION = "location"
    CONDITION = "condition"
    FEATURES = "features"
    SIZE = "size"
    RIGHTS = "rights"
    MARKET = "market"


@dataclass
class PriceAdjustment:
    adjustment_id: str
    category: AdjustmentCategory
    description: str
    adjustment_percentage: float
    adjustment_amount: Optional[float] = None
    justification: str = ""
    data_source: str = "market_analysis"
    is_standard: bool = False
    reliability: float = 0.8

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "description": self.description,
            "adjustment_percentage": self.adjustment_percentage,
            "adjustment_amount": self.adjustment_amount,
            "reliability": self.reliability,
        }


@dataclass
class AdjustedComparable:
    comparable_id: str
    original_price: float
    adjustments: List[PriceAdjustment] = field(default_factory=list)
    adjusted_price: float = 0.0
    total_adjustment_percentage: float = 0.0
    total_adjustment_amount: float = 0.0
    adjustment_confidence: float = 0.8

    def to_dict(self) -> Dict[str, Any]:
        return {
            "comparable_id": self.comparable_id,
            "original_price": self.original_price,
            "adjusted_price": round(self.adjusted_price, 2),
            "total_adjustment_percentage": round(self.total_adjustment_percentage, 4),
            "total_adjustment_amount": round(self.total_adjustment_amount, 2),
            "adjustment_count": len(self.adjustments),
            "adjustment_confidence": round(self.adjustment_confidence, 4),
        }


class AdjustmentFactorEngine:
    """Calculate and apply price adjustments for comparable properties."""

    _STANDARD_ADJUSTMENTS: Dict[str, float] = {
        "time_0_3_months": 0.0,
        "time_3_6_months": -1.0,
        "time_6_12_months": -2.5,
        "time_12_24_months": -5.0,
        "location_premium_cairo_downtown": 15.0,
        "location_premium_cairo_nasr_city": 10.0,
        "location_discount_far_suburbs": -15.0,
        "condition_excellent": 10.0,
        "condition_good": 0.0,
        "condition_fair": -5.0,
        "condition_poor": -15.0,
        "features_parking": 5.0,
        "features_garden": 8.0,
        "features_pool": 12.0,
        "market_strong": 5.0,
        "market_stable": 0.0,
        "market_weak": -5.0,
    }

    _CONDITION_ADJUSTMENTS: Dict[str, float] = {
        "excellent": 10.0,
        "good": 0.0,
        "fair": -5.0,
        "poor": -15.0,
    }

    def __init__(self) -> None:
        self.standard_adjustments = dict(self._STANDARD_ADJUSTMENTS)
        logger.info("Adjustment Factor Engine initialized")

    def apply_adjustments(
        self,
        comparable_id: str,
        original_price: float,
        adjustments: List[PriceAdjustment],
    ) -> AdjustedComparable:
        result = AdjustedComparable(
            comparable_id=comparable_id,
            original_price=original_price,
            adjustments=adjustments,
        )

        if not adjustments:
            result.adjusted_price = original_price
            return result

        adjusted_price = original_price
        total_pct = 0.0

        for adj in adjustments:
            amount = original_price * (adj.adjustment_percentage / 100.0)
            adjusted_price += amount
            total_pct += adj.adjustment_percentage

        result.adjusted_price = adjusted_price
        result.total_adjustment_percentage = total_pct
        result.total_adjustment_amount = adjusted_price - original_price
        result.adjustment_confidence = sum(a.reliability for a in adjustments) / len(adjustments)

        logger.info("Adjustments applied: %s (%+.1f%%)", comparable_id, total_pct)
        return result

    def get_standard_adjustment(self, adjustment_key: str) -> Optional[float]:
        return self.standard_adjustments.get(adjustment_key)

    def create_time_adjustment(self, days_since_sale: int) -> PriceAdjustment:
        months = days_since_sale / 30.0
        if months <= 3:
            pct, desc = 0.0, "Recent sale (0-3 months)"
        elif months <= 6:
            pct, desc = -1.0, "Sale 3-6 months ago"
        elif months <= 12:
            pct, desc = -2.5, "Sale 6-12 months ago"
        else:
            pct, desc = -5.0, "Sale 12-24 months ago"

        return PriceAdjustment(
            adjustment_id=f"TIME_{int(days_since_sale)}",
            category=AdjustmentCategory.TIME,
            description=desc,
            adjustment_percentage=pct,
            is_standard=True,
        )

    def create_condition_adjustment(self, condition: str) -> PriceAdjustment:
        pct = self._CONDITION_ADJUSTMENTS.get(condition.lower(), 0.0)
        return PriceAdjustment(
            adjustment_id=f"COND_{condition}",
            category=AdjustmentCategory.CONDITION,
            description=f"Condition: {condition}",
            adjustment_percentage=pct,
            is_standard=True,
        )

    def create_location_adjustment(
        self, subject_location: str, comparable_location: str
    ) -> Optional[PriceAdjustment]:
        if subject_location.lower() == comparable_location.lower():
            return None

        premium = ["cairo downtown", "cairo nasr city", "cairo new cairo"]
        subject_premium = any(loc in subject_location.lower() for loc in premium)
        comp_premium = any(loc in comparable_location.lower() for loc in premium)

        if subject_premium and not comp_premium:
            pct, desc = -10.0, "Comparable in less premium location"
        elif not subject_premium and comp_premium:
            pct, desc = 10.0, "Comparable in more premium location"
        else:
            pct, desc = -2.5, "Location difference adjustment"

        return PriceAdjustment(
            adjustment_id=f"LOC_{comparable_location}",
            category=AdjustmentCategory.LOCATION,
            description=desc,
            adjustment_percentage=pct,
            is_standard=False,
        )


adjustment_engine = AdjustmentFactorEngine()
