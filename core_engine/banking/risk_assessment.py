"""
risk_assessment.py — Property Risk Assessment

Multi-factor property risk analysis aligned with Basel III risk-weight categories.
Complements LTV-based credit risk with property-specific risk scoring.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class BaselRiskWeight(str, Enum):
    """Basel III / CBE risk weight categories for real estate exposures."""
    RW_35  = "35%"    # Prime residential mortgage (LTV <= 80%)
    RW_75  = "75%"    # Standard residential / retail
    RW_100 = "100%"   # Commercial real estate, speculative
    RW_150 = "150%"   # Non-performing or high LTV > 100%


@dataclass
class RiskFactor:
    """A single scored risk factor."""

    name: str
    score: float        # 0 (low risk) → 100 (high risk)
    weight: float       # Contribution weight (0-1, all weights sum to 1)
    description: str

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight


@dataclass
class PropertyRiskProfile:
    """Composite risk profile for a property used as collateral."""

    property_id: str
    overall_risk_score: float       # 0-100; lower = less risky
    basel_risk_weight: BaselRiskWeight
    risk_factors: List[RiskFactor]
    risk_summary: str
    assessed_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "property_id": self.property_id,
            "overall_risk_score": round(self.overall_risk_score, 2),
            "basel_risk_weight": self.basel_risk_weight.value,
            "risk_factors": [
                {
                    "name": f.name,
                    "score": f.score,
                    "weight": f.weight,
                    "weighted_score": round(f.weighted_score, 2),
                    "description": f.description,
                }
                for f in self.risk_factors
            ],
            "risk_summary": self.risk_summary,
            "assessed_at": self.assessed_at.isoformat(),
        }


class PropertyRiskAnalyzer:
    """Assess multi-factor property risk for collateral underwriting."""

    # Weights must sum to 1.0
    _FACTOR_WEIGHTS = {
        "property_type":   0.20,
        "location":        0.25,
        "condition":       0.20,
        "age":             0.10,
        "market":          0.15,
        "legal":           0.10,
    }

    # Property type base risk scores
    _TYPE_SCORES = {
        "residential_property": 20.0,
        "commercial_property":  45.0,
        "mixed_use":            40.0,
        "industrial_property":  55.0,
        "agricultural_land":    60.0,
        "undeveloped_land":     70.0,
    }

    _CONDITION_SCORES = {
        "excellent": 10.0,
        "good":      25.0,
        "fair":      50.0,
        "poor":      75.0,
        "very_poor": 90.0,
    }

    _MARKET_SCORES = {
        "Strong":    10.0,
        "Stable":    30.0,
        "Weak":      60.0,
        "Declining": 80.0,
    }

    def assess(
        self,
        property_id: str,
        property_type: str,
        condition: str,
        year_built: int,
        city: str,
        legal_status: str,
        ltv_ratio: float,
        market_conditions: str = "Stable",
    ) -> PropertyRiskProfile:
        """Compute a composite risk profile.

        Args:
            property_id: Property identifier.
            property_type: CollateralType value string.
            condition: "excellent" | "good" | "fair" | "poor" | "very_poor".
            year_built: Year of construction.
            city: City / location name.
            legal_status: "free" | "mortgaged" | "liened".
            ltv_ratio: Current LTV percentage.
            market_conditions: Market state string.

        Returns:
            PropertyRiskProfile.
        """
        factors: List[RiskFactor] = []

        # 1. Property type
        type_score = self._TYPE_SCORES.get(property_type.lower(), 50.0)
        factors.append(RiskFactor(
            "property_type", type_score, self._FACTOR_WEIGHTS["property_type"],
            f"Property type: {property_type}",
        ))

        # 2. Location (prime cities = lower risk)
        prime_cities = {"cairo", "giza", "alexandria", "new cairo", "6th october"}
        loc_score = 20.0 if city.lower() in prime_cities else 50.0
        factors.append(RiskFactor(
            "location", loc_score, self._FACTOR_WEIGHTS["location"],
            f"Location: {city}",
        ))

        # 3. Condition
        cond_score = self._CONDITION_SCORES.get(condition.lower(), 40.0)
        factors.append(RiskFactor(
            "condition", cond_score, self._FACTOR_WEIGHTS["condition"],
            f"Property condition: {condition}",
        ))

        # 4. Age
        age = max(0, datetime.utcnow().year - year_built)
        age_score = min(90.0, age * 1.5)
        factors.append(RiskFactor(
            "age", age_score, self._FACTOR_WEIGHTS["age"],
            f"Property age: {age} years",
        ))

        # 5. Market conditions
        mkt_score = self._MARKET_SCORES.get(market_conditions, 30.0)
        factors.append(RiskFactor(
            "market", mkt_score, self._FACTOR_WEIGHTS["market"],
            f"Market: {market_conditions}",
        ))

        # 6. Legal status
        legal_scores = {"free": 10.0, "mortgaged": 50.0, "liened": 70.0}
        leg_score = legal_scores.get(legal_status.lower(), 40.0)
        factors.append(RiskFactor(
            "legal", leg_score, self._FACTOR_WEIGHTS["legal"],
            f"Legal status: {legal_status}",
        ))

        overall = sum(f.weighted_score for f in factors)

        # NOTE: Basel III risk-weight tier thresholds below are simplified heuristics.
        # Standard Basel III (CBE Basel III circular) uses a more granular matrix
        # (property type × LTV × occupancy). RW_75 applied broadly to LTV<=100 is
        # an approximation — pending domain review by د. عبد الرؤوف.
        # Basel risk weight
        if ltv_ratio <= 80 and property_type == "residential_property":
            rw = BaselRiskWeight.RW_35
        elif ltv_ratio <= 100:
            rw = BaselRiskWeight.RW_75
        elif overall >= 70:
            rw = BaselRiskWeight.RW_150
        else:
            rw = BaselRiskWeight.RW_100

        summary = (
            f"Overall risk score: {overall:.1f}/100 | "
            f"Basel weight: {rw.value} | "
            f"Dominant factor: {max(factors, key=lambda f: f.weighted_score).name}"
        )

        return PropertyRiskProfile(
            property_id=property_id,
            overall_risk_score=overall,
            basel_risk_weight=rw,
            risk_factors=factors,
            risk_summary=summary,
        )


property_risk_analyzer = PropertyRiskAnalyzer()
