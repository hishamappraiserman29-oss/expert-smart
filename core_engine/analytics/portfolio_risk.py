"""
portfolio_risk.py — Portfolio Risk Analytics (Phase 36)

Portfolio-level risk assessment: concentration, market, liquidity, credit, VaR.

Note: Named portfolio_risk.py to avoid shadowing funds/risk_analytics.py (Phase 34).
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PortfolioRisk:
    portfolio_id: str
    tenant_id: str
    total_value: float
    number_of_assets: int
    overall_risk_level: RiskLevel
    concentration_risk: float
    market_risk: float
    liquidity_risk: float
    credit_risk: float
    operational_risk: float
    var_95: float
    var_99: float
    assessed_at: datetime = field(default_factory=datetime.utcnow)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_id": self.portfolio_id,
            "tenant_id": self.tenant_id,
            "total_value": round(self.total_value, 2),
            "number_of_assets": self.number_of_assets,
            "overall_risk_level": self.overall_risk_level.value,
            "risk_scores": {
                "concentration": round(self.concentration_risk, 2),
                "market": round(self.market_risk, 2),
                "liquidity": round(self.liquidity_risk, 2),
                "credit": round(self.credit_risk, 2),
                "operational": round(self.operational_risk, 2),
            },
            "var_95": round(self.var_95, 2),
            "var_99": round(self.var_99, 2),
            "recommendations": self.recommendations,
            "assessed_at": self.assessed_at.isoformat(),
        }


class PortfolioRiskAnalytics:
    """Assess portfolio-level risk across multiple dimensions."""

    def __init__(self) -> None:
        self.assessments: Dict[str, PortfolioRisk] = {}
        self._by_tenant: Dict[str, List[str]] = {}
        self._lock = threading.Lock()
        logger.info("Portfolio Risk Analytics initialized")

    def assess_portfolio_risk(
        self,
        portfolio_id: str,
        tenant_id: str,
        total_value: float,
        assets: List[Dict[str, Any]],
        credit_risk: float = 10.0,
        operational_risk: float = 5.0,
    ) -> PortfolioRisk:
        n = len(assets)
        if n == 0 or total_value <= 0:
            concentration_risk = 0.0
            market_risk = 0.0
            liquidity_risk = 0.0
        else:
            largest = max((a.get("value", 0) for a in assets), default=0)
            concentration_risk = largest / total_value * 100

            market_risk = min(100.0, concentration_risk * 0.5)

            illiquid = sum(1 for a in assets if a.get("liquidity", "high") == "low")
            liquidity_risk = illiquid / n * 100

        avg_risk = (market_risk + liquidity_risk + credit_risk + operational_risk) / 4

        if avg_risk < 20:
            level = RiskLevel.LOW
        elif avg_risk < 40:
            level = RiskLevel.MEDIUM
        elif avg_risk < 70:
            level = RiskLevel.HIGH
        else:
            level = RiskLevel.CRITICAL

        var_95 = total_value * (avg_risk / 100) * 1.645
        var_99 = total_value * (avg_risk / 100) * 2.326

        recs: List[str] = []
        if concentration_risk > 30:
            recs.append("High concentration risk: diversify portfolio")
        if liquidity_risk > 50:
            recs.append("High liquidity risk: increase liquid assets")
        if level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            recs.append("Overall risk elevated: review and rebalance")

        assessment = PortfolioRisk(
            portfolio_id=portfolio_id,
            tenant_id=tenant_id,
            total_value=total_value,
            number_of_assets=n,
            overall_risk_level=level,
            concentration_risk=concentration_risk,
            market_risk=market_risk,
            liquidity_risk=liquidity_risk,
            credit_risk=credit_risk,
            operational_risk=operational_risk,
            var_95=var_95,
            var_99=var_99,
            recommendations=recs,
        )
        with self._lock:
            self.assessments[portfolio_id] = assessment
            self._by_tenant.setdefault(tenant_id, []).append(portfolio_id)

        logger.info("Portfolio risk assessed: %s → %s", portfolio_id, level.value)
        return assessment

    def get_high_risk_portfolios(self) -> List[PortfolioRisk]:
        with self._lock:
            return [
                a for a in self.assessments.values()
                if a.overall_risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
            ]

    def get_tenant_portfolios(self, tenant_id: str) -> List[PortfolioRisk]:
        with self._lock:
            ids = list(self._by_tenant.get(tenant_id, []))
            return [self.assessments[pid] for pid in ids if pid in self.assessments]

    def get_risk_distribution(self) -> Dict[str, Any]:
        with self._lock:
            assessments = list(self.assessments.values())
        if not assessments:
            return {"total": 0}
        dist: Dict[str, int] = {level.value: 0 for level in RiskLevel}
        for a in assessments:
            dist[a.overall_risk_level.value] += 1
        dist["total"] = len(assessments)
        return dist

    def count(self) -> int:
        with self._lock:
            return len(self.assessments)


portfolio_risk_analytics = PortfolioRiskAnalytics()
