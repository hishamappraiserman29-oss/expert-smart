"""
tax_calculator.py — Tax Valuation Calculator

Calculate property tax valuations per Egyptian Tax Authority standards.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class TaxClassification(str, Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    AGRICULTURAL = "agricultural"
    MIXED_USE = "mixed_use"
    VACANT_LAND = "vacant_land"


@dataclass
class TaxValuationResult:
    """Output of a single tax valuation calculation."""

    property_id: str
    tax_classification: TaxClassification
    assessed_value: float
    tax_rate: float
    annual_tax: float
    capital_gains_tax_applicable: bool
    estimated_capital_gains_tax: float
    property_tax_rate: float
    total_estimated_tax: float
    calculated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "property_id": self.property_id,
            "tax_classification": self.tax_classification.value,
            "assessed_value": self.assessed_value,
            "tax_rate": self.tax_rate,
            "annual_tax": self.annual_tax,
            "capital_gains_tax_applicable": self.capital_gains_tax_applicable,
            "estimated_capital_gains_tax": self.estimated_capital_gains_tax,
            "property_tax_rate": self.property_tax_rate,
            "total_estimated_tax": self.total_estimated_tax,
            "calculated_at": self.calculated_at.isoformat(),
        }


class TaxCalculator:
    """Calculate tax valuations per Egyptian Tax Authority standards."""

    # Annual property tax rates by classification
    _PROPERTY_TAX_RATES: Dict[TaxClassification, float] = {
        TaxClassification.RESIDENTIAL:  0.005,   # 0.5%
        TaxClassification.COMMERCIAL:   0.015,   # 1.5%
        TaxClassification.INDUSTRIAL:   0.010,   # 1.0%
        TaxClassification.AGRICULTURAL: 0.003,   # 0.3%
        TaxClassification.MIXED_USE:    0.010,   # 1.0%
        TaxClassification.VACANT_LAND:  0.008,   # 0.8%
    }

    # Transfer / transaction tax rates by classification
    _TRANSACTION_TAX_RATES: Dict[TaxClassification, float] = {
        TaxClassification.RESIDENTIAL:  0.00,    # exempt
        TaxClassification.COMMERCIAL:   0.10,    # 10%
        TaxClassification.INDUSTRIAL:   0.05,    # 5%
        TaxClassification.AGRICULTURAL: 0.02,    # 2%
        TaxClassification.MIXED_USE:    0.07,    # 7%
        TaxClassification.VACANT_LAND:  0.03,    # 3%
    }

    CAPITAL_GAINS_RATE = 0.25          # 25% of realised gain
    CAPITAL_GAINS_EXEMPT_YEARS = 5     # exempt if held >= 5 years

    def calculate_tax_valuation(
        self,
        property_id: str,
        assessed_value: float,
        classification: TaxClassification,
        purchase_price: Optional[float] = None,
        years_held: Optional[int] = None,
    ) -> TaxValuationResult:
        """Calculate all applicable taxes for a property.

        Args:
            property_id: Unique property identifier.
            assessed_value: Current assessed market value (EGP).
            classification: Tax classification enum value.
            purchase_price: Original acquisition cost (optional, for CGT).
            years_held: Number of full years since acquisition (optional, for CGT).

        Returns:
            TaxValuationResult dataclass.
        """
        property_tax_rate = self._PROPERTY_TAX_RATES.get(classification, 0.005)
        transaction_tax_rate = self._TRANSACTION_TAX_RATES.get(classification, 0.0)

        annual_tax = assessed_value * property_tax_rate

        # Capital gains tax
        cgt = 0.0
        cgt_applicable = False
        if purchase_price is not None and years_held is not None:
            if years_held < self.CAPITAL_GAINS_EXEMPT_YEARS:
                cgt_applicable = True
                gain = assessed_value - purchase_price
                if gain > 0:
                    cgt = gain * self.CAPITAL_GAINS_RATE

        total_tax = annual_tax + cgt

        result = TaxValuationResult(
            property_id=property_id,
            tax_classification=classification,
            assessed_value=assessed_value,
            tax_rate=transaction_tax_rate,
            annual_tax=annual_tax,
            capital_gains_tax_applicable=cgt_applicable,
            estimated_capital_gains_tax=cgt,
            property_tax_rate=property_tax_rate,
            total_estimated_tax=total_tax,
            calculated_at=datetime.utcnow(),
        )

        logger.info(
            "Tax valuation for %s (%s): EGP %,.0f total",
            property_id, classification.value, total_tax,
        )
        return result

    def get_tax_report(self, result: TaxValuationResult) -> str:
        """Generate a plain-text tax report."""
        return (
            f"TAX VALUATION REPORT — Egyptian Tax Authority\n"
            f"{'=' * 64}\n"
            f"Property ID:           {result.property_id}\n"
            f"Tax Classification:    {result.tax_classification.value.upper()}\n"
            f"Assessed Value:        EGP {result.assessed_value:,.0f}\n"
            f"Report Date:           {result.calculated_at.strftime('%Y-%m-%d')}\n"
            f"\nTAX BREAKDOWN:\n"
            f"  Property Tax Rate:   {result.property_tax_rate * 100:.2f}%\n"
            f"  Annual Property Tax: EGP {result.annual_tax:,.0f}\n"
            f"  CGT Applicable:      {'Yes' if result.capital_gains_tax_applicable else 'No'}\n"
            f"  Estimated CGT:       EGP {result.estimated_capital_gains_tax:,.0f}\n"
            f"\nTOTAL ESTIMATED TAX:   EGP {result.total_estimated_tax:,.0f}\n"
            f"\nNOTES:\n"
            f"  - Residential properties may qualify for exemptions.\n"
            f"  - Capital gains tax exempt if property held >= 5 years.\n"
            f"  - Actual liability determined by tax authority.\n"
            f"{'=' * 64}\n"
        )


tax_calculator = TaxCalculator()
