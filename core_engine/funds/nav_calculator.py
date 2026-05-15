"""
nav_calculator.py — Net Asset Value Calculator

Computes NAV and NAV per share for real estate funds.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FundAsset:
    asset_id: str
    asset_type: str
    current_value: float
    original_cost: float
    acquisition_date: date
    last_valuation_date: date
    percentage_of_fund: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "asset_type": self.asset_type,
            "current_value": round(self.current_value, 2),
            "original_cost": round(self.original_cost, 2),
            "unrealised_gain": round(self.current_value - self.original_cost, 2),
            "acquisition_date": self.acquisition_date.isoformat(),
            "last_valuation_date": self.last_valuation_date.isoformat(),
            "percentage_of_fund": round(self.percentage_of_fund, 4),
        }


@dataclass
class FundLiability:
    liability_id: str
    liability_type: str
    amount: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "liability_id": self.liability_id,
            "liability_type": self.liability_type,
            "amount": round(self.amount, 2),
        }


@dataclass
class NAVCalculationResult:
    fund_id: str
    total_assets: float
    total_liabilities: float
    net_asset_value: float
    nav_per_share: float
    shares_outstanding: float
    nav_change_percentage: float
    previous_nav: Optional[float]
    calculation_date: date
    assets: List[FundAsset]
    liabilities: List[FundLiability]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fund_id": self.fund_id,
            "total_assets": round(self.total_assets, 2),
            "total_liabilities": round(self.total_liabilities, 2),
            "net_asset_value": round(self.net_asset_value, 2),
            "nav_per_share": round(self.nav_per_share, 4),
            "shares_outstanding": self.shares_outstanding,
            "nav_change_percentage": round(self.nav_change_percentage, 4),
            "previous_nav": self.previous_nav,
            "calculation_date": self.calculation_date.isoformat(),
            "assets": [a.to_dict() for a in self.assets],
            "liabilities": [l.to_dict() for l in self.liabilities],
        }


class NAVCalculator:
    """Calculate NAV and NAV per share for a fund."""

    def __init__(self) -> None:
        self._previous_navs: Dict[str, float] = {}

    def calculate_nav(
        self,
        fund_id: str,
        assets: List[FundAsset],
        liabilities: List[FundLiability],
        shares_outstanding: float,
        calculation_date: Optional[date] = None,
    ) -> NAVCalculationResult:
        if shares_outstanding <= 0:
            raise ValueError("shares_outstanding must be positive")

        calc_date = calculation_date or date.today()
        total_assets = sum(a.current_value for a in assets)
        total_liabilities = sum(l.amount for l in liabilities)
        net_asset_value = total_assets - total_liabilities
        nav_per_share = net_asset_value / shares_outstanding

        previous_nav = self._previous_navs.get(fund_id)
        if previous_nav and previous_nav > 0:
            nav_change_pct = (net_asset_value - previous_nav) / previous_nav * 100
        else:
            nav_change_pct = 0.0

        # Update percentage_of_fund for each asset
        for asset in assets:
            asset.percentage_of_fund = (
                asset.current_value / total_assets * 100 if total_assets > 0 else 0.0
            )

        self._previous_navs[fund_id] = net_asset_value

        result = NAVCalculationResult(
            fund_id=fund_id,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            net_asset_value=net_asset_value,
            nav_per_share=nav_per_share,
            shares_outstanding=shares_outstanding,
            nav_change_percentage=nav_change_pct,
            previous_nav=previous_nav,
            calculation_date=calc_date,
            assets=assets,
            liabilities=liabilities,
        )
        logger.info(
            "NAV calculated for fund %s: NAV=%.2f, NAV/share=%.4f",
            fund_id, net_asset_value, nav_per_share,
        )
        return result

    def generate_nav_report(self, result: NAVCalculationResult) -> str:
        lines = [
            "NAV Calculation Report",
            "=" * 40,
            f"Fund ID          : {result.fund_id}",
            f"Calculation Date : {result.calculation_date}",
            f"Total Assets     : EGP {result.total_assets:,.2f}",
            f"Total Liabilities: EGP {result.total_liabilities:,.2f}",
            f"Net Asset Value  : EGP {result.net_asset_value:,.2f}",
            f"Shares Outstanding: {result.shares_outstanding:,.0f}",
            f"NAV per Share    : EGP {result.nav_per_share:,.4f}",
            f"NAV Change       : {result.nav_change_percentage:+.2f}%",
            "",
            "Asset Breakdown:",
        ]
        for asset in result.assets:
            lines.append(
                f"  {asset.asset_id} ({asset.asset_type}): "
                f"EGP {asset.current_value:,.2f} ({asset.percentage_of_fund:.1f}%)"
            )
        if result.liabilities:
            lines.append("")
            lines.append("Liabilities:")
            for lib in result.liabilities:
                lines.append(f"  {lib.liability_id} ({lib.liability_type}): EGP {lib.amount:,.2f}")
        return "\n".join(lines)


nav_calculator = NAVCalculator()
