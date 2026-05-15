"""
risk_analytics.py — Fund Risk Analytics

VaR, volatility, correlation analysis for real estate fund portfolios.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Z-scores for VaR confidence levels
_Z_SCORES: Dict[float, float] = {
    0.90: 1.282,
    0.95: 1.645,
    0.99: 2.326,
}


@dataclass
class VaRResult:
    fund_id: str
    confidence_level: float
    var_amount: float
    var_percentage: float
    nav: float
    time_horizon_days: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fund_id": self.fund_id,
            "confidence_level": self.confidence_level,
            "var_amount": round(self.var_amount, 2),
            "var_percentage": round(self.var_percentage, 4),
            "nav": round(self.nav, 2),
            "time_horizon_days": self.time_horizon_days,
        }


@dataclass
class RiskProfile:
    fund_id: str
    daily_volatility: float
    annualised_volatility: float
    var_95: float
    var_99: float
    beta: float
    correlation_to_market: float
    risk_category: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fund_id": self.fund_id,
            "daily_volatility_pct": round(self.daily_volatility * 100, 4),
            "annualised_volatility_pct": round(self.annualised_volatility * 100, 4),
            "var_95_pct": round(self.var_95, 4),
            "var_99_pct": round(self.var_99, 4),
            "beta": round(self.beta, 4),
            "correlation_to_market": round(self.correlation_to_market, 4),
            "risk_category": self.risk_category,
        }


class RiskAnalytics:
    """Compute VaR and risk profiles for fund portfolios."""

    TRADING_DAYS = 252

    def calculate_var(
        self,
        fund_id: str,
        nav: float,
        daily_volatility: float,
        confidence_level: float = 0.95,
        time_horizon_days: int = 1,
    ) -> VaRResult:
        if confidence_level not in _Z_SCORES:
            raise ValueError(f"Confidence level must be one of {list(_Z_SCORES.keys())}")
        if daily_volatility < 0:
            raise ValueError("Volatility cannot be negative")

        z = _Z_SCORES[confidence_level]
        horizon_vol = daily_volatility * math.sqrt(time_horizon_days)
        var_pct = z * horizon_vol
        var_amount = nav * var_pct

        return VaRResult(
            fund_id=fund_id,
            confidence_level=confidence_level,
            var_amount=var_amount,
            var_percentage=var_pct,
            nav=nav,
            time_horizon_days=time_horizon_days,
        )

    def build_risk_profile(
        self,
        fund_id: str,
        daily_volatility: float,
        nav: float,
        beta: float = 1.0,
        correlation_to_market: float = 0.6,
    ) -> RiskProfile:
        annualised_vol = daily_volatility * math.sqrt(self.TRADING_DAYS)
        var_95 = _Z_SCORES[0.95] * daily_volatility * 100
        var_99 = _Z_SCORES[0.99] * daily_volatility * 100

        if annualised_vol < 0.08:
            risk_cat = "low"
        elif annualised_vol < 0.15:
            risk_cat = "moderate"
        elif annualised_vol < 0.25:
            risk_cat = "elevated"
        else:
            risk_cat = "high"

        return RiskProfile(
            fund_id=fund_id,
            daily_volatility=daily_volatility,
            annualised_volatility=annualised_vol,
            var_95=var_95,
            var_99=var_99,
            beta=beta,
            correlation_to_market=correlation_to_market,
            risk_category=risk_cat,
        )

    def portfolio_var(
        self,
        var_results: List[VaRResult],
        correlation_matrix: Optional[List[List[float]]] = None,
    ) -> float:
        """Simple portfolio VaR using sum of individual VaRs (conservative)."""
        return sum(r.var_amount for r in var_results)

    def correlation_matrix(
        self, fund_ids: List[str], returns: List[List[float]]
    ) -> Dict[str, Any]:
        """Compute pairwise Pearson correlations from return series."""
        n = len(fund_ids)
        if n == 0 or len(returns) != n:
            return {"error": "Mismatched fund_ids and returns"}

        def mean(xs: List[float]) -> float:
            return sum(xs) / len(xs) if xs else 0.0

        def pearson(xs: List[float], ys: List[float]) -> float:
            if len(xs) != len(ys) or len(xs) < 2:
                return 0.0
            mx, my = mean(xs), mean(ys)
            num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
            dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
            dy = math.sqrt(sum((y - my) ** 2 for y in ys))
            return num / (dx * dy) if dx * dy > 0 else 0.0

        matrix: Dict[str, Dict[str, float]] = {}
        for i, fid_i in enumerate(fund_ids):
            matrix[fid_i] = {}
            for j, fid_j in enumerate(fund_ids):
                matrix[fid_i][fid_j] = round(pearson(returns[i], returns[j]), 4)

        return {"fund_ids": fund_ids, "correlation_matrix": matrix}


risk_analytics = RiskAnalytics()
