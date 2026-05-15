"""
ltv_calculator.py — LTV Calculator and Credit Risk Scoring

Loan-to-Value ratio calculation, tier classification, and credit risk assessment
per CBE lending standards.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LTVTier(str, Enum):
    PRIME        = "prime"          # LTV <= 70%
    CONVENTIONAL = "conventional"   # LTV 70-85%
    CONFORMING   = "conforming"     # LTV 85-95%
    HIGH_LTV     = "high_ltv"       # LTV > 95%


class CreditRiskRating(str, Enum):
    AAA = "aaa"   # < 0.5% default probability
    AA  = "aa"    # 0.5-2%
    A   = "a"     # 2-5%
    BBB = "bbb"   # 5-10%
    BB  = "bb"    # 10-20%
    B   = "b"     # 20-35%
    CCC = "ccc"   # > 35%


@dataclass
class LTVCalculationResult:
    """Output of an LTV calculation."""

    loan_id: str
    loan_amount: float
    collateral_value: float
    ltv_ratio: float         # percentage
    ltv_tier: LTVTier
    coverage_multiple: float  # collateral / loan
    calculated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "loan_id": self.loan_id,
            "loan_amount": self.loan_amount,
            "collateral_value": self.collateral_value,
            "ltv_ratio": round(self.ltv_ratio, 2),
            "ltv_tier": self.ltv_tier.value,
            "coverage_multiple": round(self.coverage_multiple, 4),
            "is_over_leveraged": self.ltv_ratio > 95,
            "calculated_at": self.calculated_at.isoformat(),
        }


@dataclass
class CreditRiskAssessment:
    """Credit risk assessment for a loan application."""

    loan_id: str
    borrower_credit_score: Optional[int]
    ltv_ratio: float
    property_quality: str
    loan_purpose: str
    market_conditions: str
    risk_rating: CreditRiskRating
    default_probability: float   # percentage
    loss_given_default: float    # percentage
    expected_loss: float         # percentage of loan
    risk_mitigation_factors: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    assessed_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "loan_id": self.loan_id,
            "risk_rating": self.risk_rating.value,
            "default_probability": round(self.default_probability, 2),
            "loss_given_default": round(self.loss_given_default, 2),
            "expected_loss": round(self.expected_loss, 4),
            "risk_mitigation_factors": self.risk_mitigation_factors,
            "recommendations": self.recommendations,
            "assessed_at": self.assessed_at.isoformat(),
        }


class LTVCalculator:
    """Calculate LTV ratios, tiers, and credit risk ratings."""

    def calculate_ltv(
        self,
        loan_id: str,
        loan_amount: float,
        collateral_value: float,
    ) -> LTVCalculationResult:
        """Compute Loan-to-Value ratio and classify into tier.

        Args:
            loan_id: Unique loan identifier.
            loan_amount: Loan principal in EGP.
            collateral_value: Appraised collateral value in EGP.

        Returns:
            LTVCalculationResult.
        """
        if collateral_value <= 0:
            raise ValueError("collateral_value must be positive")

        ltv = (loan_amount / collateral_value) * 100.0
        tier = self._tier(ltv)
        coverage = collateral_value / loan_amount if loan_amount > 0 else 0.0

        result = LTVCalculationResult(
            loan_id=loan_id,
            loan_amount=loan_amount,
            collateral_value=collateral_value,
            ltv_ratio=ltv,
            ltv_tier=tier,
            coverage_multiple=coverage,
            calculated_at=datetime.utcnow(),
        )
        logger.info("LTV %s: %.1f%% (%s)", loan_id, ltv, tier.value)
        return result

    def _tier(self, ltv: float) -> LTVTier:
        if ltv <= 70:
            return LTVTier.PRIME
        elif ltv <= 85:
            return LTVTier.CONVENTIONAL
        elif ltv <= 95:
            return LTVTier.CONFORMING
        else:
            return LTVTier.HIGH_LTV

    def assess_credit_risk(
        self,
        loan_id: str,
        borrower_credit_score: Optional[int],
        ltv_ratio: float,
        property_quality: str,
        loan_purpose: str,
        market_conditions: str = "Stable",
    ) -> CreditRiskAssessment:
        """Assess credit risk from borrower, collateral, and market inputs.

        Returns:
            CreditRiskAssessment.
        """
        # Base default probability
        dp = 5.0

        # Credit score adjustment
        if borrower_credit_score is not None:
            if borrower_credit_score >= 750:
                dp -= 3.0
            elif borrower_credit_score >= 650:
                dp -= 1.0
            elif borrower_credit_score < 550:
                dp += 5.0
            if borrower_credit_score < 450:
                dp += 5.0  # extra penalty for very poor scores

        # LTV adjustment
        if ltv_ratio > 95:
            dp += 5.0
        elif ltv_ratio > 85:
            dp += 2.0

        # Property quality adjustment
        quality_adj = {"excellent": -2.0, "good": 0.0, "fair": 2.0, "poor": 5.0}
        dp += quality_adj.get(property_quality.lower(), 0.0)

        # Market conditions adjustment
        market_adj = {"Strong": -2.0, "Stable": 0.0, "Weak": 2.0, "Declining": 5.0}
        dp += market_adj.get(market_conditions, 0.0)

        dp = max(0.5, min(99.0, dp))

        # Loss Given Default: approximate shortfall if collateral < loan
        lgd = max(0.0, ltv_ratio - 100.0) if ltv_ratio > 100 else max(0.0, ltv_ratio * 0.2)
        if ltv_ratio > 90:
            lgd = max(lgd, 20.0)

        el = (dp / 100.0) * (lgd / 100.0) * 100.0  # as % of loan
        rating = self._rating(dp)

        recs: List[str] = []
        if ltv_ratio > 90:
            recs.append("Mortgage insurance recommended")
        if borrower_credit_score is not None and borrower_credit_score < 550:
            recs.append("Higher interest rate recommended")
        if market_conditions == "Declining":
            recs.append("Monitor collateral value quarterly")

        mitigation: List[str] = []
        if borrower_credit_score is not None and borrower_credit_score >= 750:
            mitigation.append("Strong credit profile")
        if ltv_ratio <= 70:
            mitigation.append("Conservative LTV ratio")
        if property_quality in ("excellent", "good"):
            mitigation.append("High-quality collateral")

        return CreditRiskAssessment(
            loan_id=loan_id,
            borrower_credit_score=borrower_credit_score,
            ltv_ratio=ltv_ratio,
            property_quality=property_quality,
            loan_purpose=loan_purpose,
            market_conditions=market_conditions,
            risk_rating=rating,
            default_probability=dp,
            loss_given_default=lgd,
            expected_loss=el,
            risk_mitigation_factors=mitigation,
            recommendations=recs,
        )

    def _rating(self, dp: float) -> CreditRiskRating:
        if dp < 0.5:
            return CreditRiskRating.AAA
        elif dp < 2:
            return CreditRiskRating.AA
        elif dp < 5:
            return CreditRiskRating.A
        elif dp < 10:
            return CreditRiskRating.BBB
        elif dp < 20:
            return CreditRiskRating.BB
        elif dp < 35:
            return CreditRiskRating.B
        else:
            return CreditRiskRating.CCC


ltv_calculator = LTVCalculator()
