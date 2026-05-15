"""
fair_value_calculator.py — IFRS 13 Fair Value Calculator

Three-level hierarchy for fair value measurement per IFRS 13.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ValuationLevel(str, Enum):
    LEVEL_1 = "level_1"
    LEVEL_2 = "level_2"
    LEVEL_3 = "level_3"


class ValuationApproach(str, Enum):
    MARKET_APPROACH = "market_approach"
    INCOME_APPROACH = "income_approach"
    COST_APPROACH = "cost_approach"
    HYBRID_APPROACH = "hybrid_approach"


class FairValueInput(str, Enum):
    QUOTED_PRICE = "quoted_price"
    COMPARABLE_PRICE = "comparable_price"
    MARKET_DATA = "market_data"
    MANAGEMENT_ESTIMATE = "management_estimate"
    APPRAISAL = "appraisal"


@dataclass
class ValuationInput:
    input_type: FairValueInput
    value: float
    date: date
    source: str
    observable: bool
    weight: float = 1.0
    confidence: float = 1.0
    market_condition: str = "normal"


@dataclass
class FairValueAssessment:
    asset_id: str
    asset_type: str
    valuation_level: ValuationLevel
    approach: ValuationApproach
    fair_value: float
    level_1_value: Optional[float]
    level_2_value: Optional[float]
    level_3_value: Optional[float]
    range_low: float
    range_mid: float
    range_high: float
    confidence: float
    liquidity_discount: float
    key_assumptions: List[str]
    valuation_date: date
    ifrs13_compliant: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "asset_type": self.asset_type,
            "valuation_level": self.valuation_level.value,
            "approach": self.approach.value,
            "fair_value": round(self.fair_value, 2),
            "level_values": {
                "level_1": self.level_1_value,
                "level_2": self.level_2_value,
                "level_3": self.level_3_value,
            },
            "range": {
                "low": round(self.range_low, 2),
                "mid": round(self.range_mid, 2),
                "high": round(self.range_high, 2),
            },
            "confidence": round(self.confidence, 4),
            "liquidity_discount_pct": round(self.liquidity_discount * 100, 2),
            "key_assumptions": self.key_assumptions,
            "valuation_date": self.valuation_date.isoformat(),
            "ifrs13_compliant": self.ifrs13_compliant,
        }


# Liquidity discounts by asset type
_LIQUIDITY_DISCOUNTS: Dict[str, float] = {
    "residential": 0.00,
    "commercial": 0.05,
    "industrial": 0.10,
    "agricultural": 0.15,
    "speciality": 0.20,
    "mixed_use": 0.08,
    "undeveloped": 0.12,
}


class FairValueCalculator:
    """IFRS 13 fair value calculator with three-level input hierarchy."""

    def assess_fair_value(
        self,
        asset_id: str,
        asset_type: str,
        inputs: List[ValuationInput],
        approach: ValuationApproach = ValuationApproach.MARKET_APPROACH,
        valuation_date: Optional[date] = None,
    ) -> FairValueAssessment:
        if not inputs:
            raise ValueError("At least one valuation input required")

        val_date = valuation_date or date.today()
        level = self._determine_valuation_level(inputs)
        liquidity_discount = _LIQUIDITY_DISCOUNTS.get(asset_type, 0.10)

        total_weight = sum(inp.weight for inp in inputs)
        if total_weight == 0:
            total_weight = 1.0

        weighted_value = (
            sum(inp.value * inp.weight * inp.confidence for inp in inputs) / total_weight
        )

        l1_inputs = [i for i in inputs if i.input_type == FairValueInput.QUOTED_PRICE and i.observable]
        l2_inputs = [i for i in inputs if i.input_type in (FairValueInput.COMPARABLE_PRICE, FairValueInput.MARKET_DATA)]
        l3_inputs = [i for i in inputs if i.input_type in (FairValueInput.MANAGEMENT_ESTIMATE, FairValueInput.APPRAISAL)]

        l1_val = self._weighted_avg(l1_inputs) if l1_inputs else None
        l2_val = self._weighted_avg(l2_inputs) if l2_inputs else None
        l3_val = self._weighted_avg(l3_inputs) if l3_inputs else None

        range_low = weighted_value * 0.92
        range_mid = weighted_value
        range_high = weighted_value * 1.08

        # Apply liquidity discount to mid for Level 3 assets
        if level == ValuationLevel.LEVEL_3:
            range_mid = weighted_value * (1 - liquidity_discount)
            fair_value = range_mid
        else:
            fair_value = weighted_value
            liquidity_discount = 0.0

        avg_confidence = sum(inp.confidence for inp in inputs) / len(inputs)

        assumptions = self._build_assumptions(level, asset_type, inputs)

        assessment = FairValueAssessment(
            asset_id=asset_id,
            asset_type=asset_type,
            valuation_level=level,
            approach=approach,
            fair_value=fair_value,
            level_1_value=l1_val,
            level_2_value=l2_val,
            level_3_value=l3_val,
            range_low=range_low,
            range_mid=range_mid,
            range_high=range_high,
            confidence=avg_confidence,
            liquidity_discount=liquidity_discount,
            key_assumptions=assumptions,
            valuation_date=val_date,
        )
        logger.info(
            "Fair value assessment: %s (%s) = %.2f [%s]",
            asset_id, asset_type, fair_value, level.value,
        )
        return assessment

    def _determine_valuation_level(self, inputs: List[ValuationInput]) -> ValuationLevel:
        if any(i.input_type == FairValueInput.QUOTED_PRICE and i.observable for i in inputs):
            return ValuationLevel.LEVEL_1
        if all(i.observable for i in inputs):
            return ValuationLevel.LEVEL_2
        return ValuationLevel.LEVEL_3

    def _weighted_avg(self, inputs: List[ValuationInput]) -> float:
        total_w = sum(i.weight for i in inputs) or 1.0
        return sum(i.value * i.weight for i in inputs) / total_w

    def _build_assumptions(
        self, level: ValuationLevel, asset_type: str, inputs: List[ValuationInput]
    ) -> List[str]:
        assumptions = []
        if level == ValuationLevel.LEVEL_1:
            assumptions.append("Quoted market price — highest reliability")
        elif level == ValuationLevel.LEVEL_2:
            assumptions.append("Observable market inputs — comparable transactions used")
        else:
            assumptions.append("Unobservable inputs — management estimates and appraisals")
            discount = _LIQUIDITY_DISCOUNTS.get(asset_type, 0.10)
            if discount > 0:
                assumptions.append(f"Liquidity discount applied: {discount*100:.0f}%")
        if any(i.market_condition == "distressed" for i in inputs):
            assumptions.append("Distressed market conditions noted — values may be understated")
        return assumptions

    def generate_ifrs13_disclosure(self, assessment: FairValueAssessment) -> str:
        lines = [
            "IFRS 13 Fair Value Disclosure",
            "=" * 40,
            f"Asset ID     : {assessment.asset_id}",
            f"Asset Type   : {assessment.asset_type}",
            f"Valuation Level: {assessment.valuation_level.value.upper()}",
            f"Approach     : {assessment.approach.value.replace('_', ' ').title()}",
            f"Fair Value   : EGP {assessment.fair_value:,.2f}",
            f"Range        : EGP {assessment.range_low:,.2f} – {assessment.range_high:,.2f}",
            f"Confidence   : {assessment.confidence:.1%}",
            f"Date         : {assessment.valuation_date}",
            "",
            "Key Assumptions:",
        ]
        for assumption in assessment.key_assumptions:
            lines.append(f"  • {assumption}")
        lines += [
            "",
            f"IFRS 13 Compliant: {'Yes' if assessment.ifrs13_compliant else 'No'}",
        ]
        return "\n".join(lines)


fair_value_calculator = FairValueCalculator()
