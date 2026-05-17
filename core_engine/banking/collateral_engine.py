"""
collateral_engine.py — Collateral Valuation Engine

Specialized property valuations for bank lending and mortgage collateral.
Produces appraised, conservative, and forced-sale values per CBE guidelines.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CollateralType(str, Enum):
    RESIDENTIAL_PROPERTY = "residential_property"
    COMMERCIAL_PROPERTY = "commercial_property"
    INDUSTRIAL_PROPERTY = "industrial_property"
    AGRICULTURAL_LAND = "agricultural_land"
    MIXED_USE = "mixed_use"
    UNDEVELOPED_LAND = "undeveloped_land"


class CollateralQuality(str, Enum):
    EXCELLENT = "excellent"    # Grade A — default risk 0-5%
    GOOD = "good"              # Grade B — default risk 5-10%
    ACCEPTABLE = "acceptable"  # Grade C — default risk 10-20%
    FAIR = "fair"              # Grade D — default risk 20-35%
    POOR = "poor"              # Grade E — default risk >35%


class LoanPurpose(str, Enum):
    RESIDENTIAL_MORTGAGE = "residential_mortgage"
    COMMERCIAL_MORTGAGE = "commercial_mortgage"
    CONSTRUCTION_LOAN = "construction_loan"
    BRIDGE_LOAN = "bridge_loan"
    REFINANCING = "refinancing"
    HOME_IMPROVEMENT = "home_improvement"
    BUSINESS_ACQUISITION = "business_acquisition"


@dataclass
class CollateralProperty:
    """Property offered as loan collateral."""

    collateral_id: str
    property_id: str
    owner_name: str
    owner_id: str
    property_type: CollateralType
    location: str
    city: str
    area_sqm: float
    year_built: int
    condition: str          # "excellent" | "good" | "fair" | "poor" | "very_poor"
    legal_status: str       # "free" | "mortgaged" | "liened"
    existing_liens: int = 0
    assessed_value: float = 0.0
    market_value: float = 0.0
    insurance_value: float = 0.0
    registered_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "collateral_id": self.collateral_id,
            "property_id": self.property_id,
            "owner_name": self.owner_name,
            "property_type": self.property_type.value,
            "location": self.location,
            "city": self.city,
            "area_sqm": self.area_sqm,
            "condition": self.condition,
            "legal_status": self.legal_status,
            "existing_liens": self.existing_liens,
            "assessed_value": self.assessed_value,
            "market_value": self.market_value,
            "insurance_value": self.insurance_value,
            "registered_at": self.registered_at.isoformat(),
        }


@dataclass
class CollateralValuationResult:
    """Output of a collateral valuation."""

    collateral_id: str
    appraised_value: float
    conservative_value: float   # ~13% quick-sale discount
    forced_sale_value: float    # ~35% distressed-sale discount
    quality_rating: CollateralQuality
    valuation_confidence: float  # 0-100
    valuation_date: datetime
    valuation_expiry: datetime
    comparable_properties: int
    methodology: str
    condition_adjustment: float  # % adjustment applied
    location_premium: float
    market_conditions: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "collateral_id": self.collateral_id,
            "appraised_value": self.appraised_value,
            "conservative_value": self.conservative_value,
            "forced_sale_value": self.forced_sale_value,
            "quality_rating": self.quality_rating.value,
            "valuation_confidence": self.valuation_confidence,
            "valuation_date": self.valuation_date.isoformat(),
            "valuation_expiry": self.valuation_expiry.isoformat(),
            "comparable_properties": self.comparable_properties,
            "methodology": self.methodology,
            "condition_adjustment": self.condition_adjustment,
            "location_premium": self.location_premium,
            "market_conditions": self.market_conditions,
            "days_valid": (self.valuation_expiry - self.valuation_date).days,
        }


class CollateralValuationEngine:
    """Produce bank-grade collateral valuations per CBE standards."""

    _CONDITION_FACTORS: Dict[str, float] = {
        "excellent": 1.05,
        "good":      1.00,
        "fair":      0.95,
        "poor":      0.85,
        "very_poor": 0.70,
    }

    _VALIDITY_DAYS: Dict[CollateralType, int] = {
        CollateralType.RESIDENTIAL_PROPERTY: 180,
        CollateralType.COMMERCIAL_PROPERTY:  180,
        CollateralType.INDUSTRIAL_PROPERTY:  180,
        CollateralType.MIXED_USE:            180,
        CollateralType.AGRICULTURAL_LAND:    365,
        CollateralType.UNDEVELOPED_LAND:     365,
    }

    def value_collateral(
        self,
        collateral: CollateralProperty,
        market_conditions: str = "Stable",
        comparable_count: int = 3,
    ) -> CollateralValuationResult:
        """Produce appraised, conservative, and forced-sale values.

        Args:
            collateral: Property offered as collateral.
            market_conditions: "Strong" | "Stable" | "Weak" | "Declining".
            comparable_count: Number of comparable properties analysed.

        Returns:
            CollateralValuationResult.
        """
        base = collateral.market_value or collateral.assessed_value
        if base <= 0:
            raise ValueError(
                "market_value or assessed_value must be positive for collateral valuation"
            )

        condition_key = collateral.condition.lower()
        condition_factor = self._CONDITION_FACTORS.get(condition_key, 1.0)
        appraised = base * condition_factor

        # NOTE: CBE collateral discount percentages (13% quick-sale, 35% distressed-sale)
        # are market approximations — pending verification by د. عبد الرؤوف against
        # current CBE Circular 5/2019 (collateral valuation guidelines).
        conservative = appraised * 0.87   # 13% quick-sale discount
        forced_sale  = appraised * 0.65   # 35% distressed-sale discount

        quality = self._determine_quality(collateral)
        confidence = min(95.0, 50.0 + comparable_count * 10.0)
        validity_days = self._VALIDITY_DAYS.get(collateral.property_type, 180)
        now = datetime.utcnow()

        result = CollateralValuationResult(
            collateral_id=collateral.collateral_id,
            appraised_value=appraised,
            conservative_value=conservative,
            forced_sale_value=forced_sale,
            quality_rating=quality,
            valuation_confidence=confidence,
            valuation_date=now,
            valuation_expiry=now + timedelta(days=validity_days),
            comparable_properties=comparable_count,
            methodology="Comparative Market Analysis",
            condition_adjustment=(condition_factor - 1.0) * 100,
            location_premium=0.0,
            market_conditions=market_conditions,
        )
        logger.info(
            "Collateral valued: %s → EGP %,.0f (confidence %.1f%%)",
            collateral.collateral_id, appraised, confidence,
        )
        return result

    def _determine_quality(self, collateral: CollateralProperty) -> CollateralQuality:
        """Score property collateral quality from multiple risk factors."""
        score = 0.0

        # Property type
        type_scores = {
            CollateralType.RESIDENTIAL_PROPERTY: 5.0,
            CollateralType.COMMERCIAL_PROPERTY:  10.0,
            CollateralType.MIXED_USE:            12.0,
            CollateralType.INDUSTRIAL_PROPERTY:  15.0,
            CollateralType.AGRICULTURAL_LAND:    18.0,
            CollateralType.UNDEVELOPED_LAND:     20.0,
        }
        score += type_scores.get(collateral.property_type, 15.0)

        # Condition
        condition_scores = {
            "excellent": 2.0, "good": 5.0, "fair": 10.0,
            "poor": 15.0, "very_poor": 25.0,
        }
        score += condition_scores.get(collateral.condition.lower(), 10.0)

        # Existing liens
        score += collateral.existing_liens * 5.0

        if score < 8:
            return CollateralQuality.EXCELLENT
        elif score < 15:
            return CollateralQuality.GOOD
        elif score < 25:
            return CollateralQuality.ACCEPTABLE
        elif score < 35:
            return CollateralQuality.FAIR
        else:
            return CollateralQuality.POOR

    def calculate_coverage_ratio(
        self,
        valuation: CollateralValuationResult,
        loan_amount: float,
        use_conservative: bool = False,
    ) -> float:
        """Coverage = collateral value / loan amount.  Target >= 1.25."""
        if loan_amount <= 0:
            return 0.0
        value = valuation.conservative_value if use_conservative else valuation.appraised_value
        return value / loan_amount


collateral_engine = CollateralValuationEngine()
