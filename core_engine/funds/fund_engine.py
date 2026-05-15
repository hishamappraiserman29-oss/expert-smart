"""
fund_engine.py — Fund Valuation Engine

Valuation and risk metrics for 6 real estate fund types.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FundType(str, Enum):
    OPEN_ENDED = "open_ended"
    CLOSED_ENDED = "closed_ended"
    REIT = "reit"
    MUTUAL_FUND = "mutual_fund"
    PRIVATE_EQUITY = "private_equity"
    SECURITIZATION = "securitization"


class FundStrategy(str, Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    MIXED = "mixed"
    DEVELOPMENT = "development"
    VALUE_ADD = "value_add"
    OPPORTUNISTIC = "opportunistic"


@dataclass
class FundValuationResult:
    fund_id: str
    fund_name: str
    fund_type: FundType
    strategy: FundStrategy
    aum: float
    nav: float
    nav_per_share: float
    shares_outstanding: float
    ytd_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    dividend_per_share: float
    dividend_yield: float
    fra_registered: bool
    valuation_date: date
    currency: str = "EGP"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fund_id": self.fund_id,
            "fund_name": self.fund_name,
            "fund_type": self.fund_type.value,
            "strategy": self.strategy.value,
            "aum": round(self.aum, 2),
            "nav": round(self.nav, 2),
            "nav_per_share": round(self.nav_per_share, 4),
            "shares_outstanding": self.shares_outstanding,
            "performance": {
                "ytd_return_pct": round(self.ytd_return * 100, 4),
                "volatility_pct": round(self.volatility * 100, 4),
                "sharpe_ratio": round(self.sharpe_ratio, 4),
                "max_drawdown_pct": round(self.max_drawdown * 100, 4),
            },
            "income": {
                "dividend_per_share": round(self.dividend_per_share, 4),
                "dividend_yield_pct": round(self.dividend_yield, 4),
            },
            "fra_registered": self.fra_registered,
            "valuation_date": self.valuation_date.isoformat(),
            "currency": self.currency,
        }


class FundValuationEngine:
    """Value real estate funds and compute risk metrics."""

    RISK_FREE_RATE = 0.08
    MARKET_RISK_PREMIUM = 0.07

    def value_fund(
        self,
        fund_id: str,
        fund_name: str,
        fund_type: FundType,
        strategy: FundStrategy,
        aum: float,
        nav: float,
        shares_outstanding: float,
        ytd_return: float,
        volatility: float,
        dividend_per_share: float = 0.0,
        fra_registered: bool = True,
        valuation_date: Optional[date] = None,
        currency: str = "EGP",
    ) -> FundValuationResult:
        if shares_outstanding <= 0:
            raise ValueError("shares_outstanding must be positive")
        if volatility < 0:
            raise ValueError("volatility cannot be negative")

        val_date = valuation_date or date.today()
        nav_per_share = nav / shares_outstanding

        sharpe = (
            (ytd_return - self.RISK_FREE_RATE) / volatility
            if volatility > 0
            else 0.0
        )
        max_drawdown = volatility * 2.5

        dividend_yield = (
            dividend_per_share / nav_per_share * 100
            if nav_per_share > 0 and dividend_per_share > 0
            else 0.0
        )

        result = FundValuationResult(
            fund_id=fund_id,
            fund_name=fund_name,
            fund_type=fund_type,
            strategy=strategy,
            aum=aum,
            nav=nav,
            nav_per_share=nav_per_share,
            shares_outstanding=shares_outstanding,
            ytd_return=ytd_return,
            volatility=volatility,
            sharpe_ratio=sharpe,
            max_drawdown=max_drawdown,
            dividend_per_share=dividend_per_share,
            dividend_yield=dividend_yield,
            fra_registered=fra_registered,
            valuation_date=val_date,
            currency=currency,
        )
        logger.info(
            "Fund valued: %s (%s) AUM=%.2f NAV=%.2f Sharpe=%.3f",
            fund_id, fund_type.value, aum, nav, sharpe,
        )
        return result

    def compare_funds(
        self, results: List[FundValuationResult]
    ) -> Dict[str, Any]:
        if not results:
            return {"error": "No fund results to compare"}
        best_sharpe = max(results, key=lambda r: r.sharpe_ratio)
        best_return = max(results, key=lambda r: r.ytd_return)
        lowest_dd = min(results, key=lambda r: r.max_drawdown)
        return {
            "fund_count": len(results),
            "best_sharpe": {"fund_id": best_sharpe.fund_id, "sharpe": round(best_sharpe.sharpe_ratio, 4)},
            "best_return": {"fund_id": best_return.fund_id, "ytd_return_pct": round(best_return.ytd_return * 100, 4)},
            "lowest_drawdown": {"fund_id": lowest_dd.fund_id, "max_drawdown_pct": round(lowest_dd.max_drawdown * 100, 4)},
            "avg_nav": round(sum(r.nav for r in results) / len(results), 2),
            "total_aum": round(sum(r.aum for r in results), 2),
        }


fund_engine = FundValuationEngine()
