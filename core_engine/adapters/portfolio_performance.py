"""
portfolio_performance.py — Portfolio Performance Analysis + Scenario Modeling (Phase 11.2)

Stress-testing and scenario analysis for property portfolios.
Additive layer — portfolio.py is imported but not modified.

Classes:
    PortfolioScenario            — Named scenario with shock parameters
    ScenarioResult               — Computed metrics for one scenario run
    PortfolioPerformanceAnalyzer — Runs multiple scenarios against a PortfolioBuilder
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from adapters.portfolio import PortfolioBuilder


# ── Scenario definition ───────────────────────────────────────────────────────

@dataclass
class PortfolioScenario:
    """Named scenario with multiplicative / additive shock parameters."""

    label: str                     # "optimistic" | "base" | "pessimistic" | custom
    noi_shock: float = 1.0         # Multiplier on NOI   (0.80 = −20 %)
    value_shock: float = 1.0       # Multiplier on value (0.85 = −15 %)
    cap_rate_shift: float = 0.0    # Additive shift on cap rate (+0.01 = +100 bps)

    def to_dict(self) -> Dict:
        return {
            "label":          self.label,
            "noi_shock":      round(self.noi_shock, 4),
            "value_shock":    round(self.value_shock, 4),
            "cap_rate_shift": round(self.cap_rate_shift, 4),
        }


# ── Scenario result ───────────────────────────────────────────────────────────

@dataclass
class ScenarioResult:
    """Computed portfolio metrics under one scenario."""

    scenario_label:           str
    stressed_portfolio_value: float = 0.0
    stressed_total_noi:       float = 0.0
    stressed_cap_rate:        float = 0.0
    stressed_noi_margin:      float = 0.0
    value_change_pct:         float = 0.0   # relative to base
    noi_change_pct:           float = 0.0   # relative to base
    irr_estimate:             float = 0.0   # stressed cap rate + assumed growth
    diversification_score:    float = 0.0

    def to_dict(self) -> Dict:
        return {
            "scenario_label":           self.scenario_label,
            "stressed_portfolio_value": round(self.stressed_portfolio_value, 2),
            "stressed_total_noi":       round(self.stressed_total_noi, 2),
            "stressed_cap_rate":        round(self.stressed_cap_rate, 4),
            "stressed_noi_margin":      round(self.stressed_noi_margin, 4),
            "value_change_pct":         round(self.value_change_pct, 4),
            "noi_change_pct":           round(self.noi_change_pct, 4),
            "irr_estimate":             round(self.irr_estimate, 4),
            "diversification_score":    round(self.diversification_score, 4),
        }


# ── Analyzer ──────────────────────────────────────────────────────────────────

class PortfolioPerformanceAnalyzer:
    """Run stress scenarios against a PortfolioBuilder instance."""

    # Assumed long-run annual property appreciation used in IRR estimate
    _ASSUMED_GROWTH_RATE: float = 0.05

    def __init__(self, portfolio_builder: PortfolioBuilder) -> None:
        self.portfolio = portfolio_builder
        self.scenarios: List[PortfolioScenario] = []
        self._results: Optional[List[ScenarioResult]] = None

        if self.portfolio.metrics is None:
            self.portfolio.calculate_metrics()

    # ── Building ──────────────────────────────────────────────────────────────

    def add_scenario(self, scenario: PortfolioScenario) -> "PortfolioPerformanceAnalyzer":
        """Append a scenario; returns self for chaining."""
        self.scenarios.append(scenario)
        self._results = None
        return self

    def create_standard_scenarios(self) -> "PortfolioPerformanceAnalyzer":
        """Replace scenario list with pessimistic / base / optimistic presets."""
        self.scenarios = [
            PortfolioScenario(
                "pessimistic",
                noi_shock=0.80,
                value_shock=0.85,
                cap_rate_shift=0.01,
            ),
            PortfolioScenario(
                "base",
                noi_shock=1.00,
                value_shock=1.00,
                cap_rate_shift=0.00,
            ),
            PortfolioScenario(
                "optimistic",
                noi_shock=1.15,
                value_shock=1.10,
                cap_rate_shift=-0.005,
            ),
        ]
        self._results = None
        return self

    # ── Computation ───────────────────────────────────────────────────────────

    def run_scenarios(self) -> List[ScenarioResult]:
        """Compute a ScenarioResult for every scenario and cache the list."""
        if not self.scenarios:
            self._results = []
            return []

        m           = self.portfolio.metrics
        base_value  = m.total_portfolio_value
        base_noi    = m.total_annual_noi
        base_gross  = m.total_annual_gross_income
        div_score   = self.portfolio.get_diversification_score()

        results: List[ScenarioResult] = []

        for sc in self.scenarios:
            stressed_value = base_value * sc.value_shock
            stressed_noi   = base_noi   * sc.noi_shock

            # Cap rate: recomputed from stressed figures then shifted
            stressed_cap = (
                (stressed_noi / stressed_value + sc.cap_rate_shift)
                if stressed_value > 0
                else 0.0
            )

            stressed_gross  = base_gross * sc.noi_shock
            stressed_margin = (
                stressed_noi / stressed_gross
                if stressed_gross > 0
                else 0.0
            )

            value_chg = (stressed_value - base_value) / base_value if base_value > 0 else 0.0
            noi_chg   = (stressed_noi   - base_noi)   / base_noi   if base_noi   > 0 else 0.0
            irr       = stressed_cap + self._ASSUMED_GROWTH_RATE

            results.append(ScenarioResult(
                scenario_label=sc.label,
                stressed_portfolio_value=stressed_value,
                stressed_total_noi=stressed_noi,
                stressed_cap_rate=stressed_cap,
                stressed_noi_margin=stressed_margin,
                value_change_pct=value_chg,
                noi_change_pct=noi_chg,
                irr_estimate=irr,
                diversification_score=div_score,
            ))

        self._results = results
        return results

    # ── Reporting ─────────────────────────────────────────────────────────────

    def get_performance_summary(self) -> Dict:
        """Return full performance summary across all scenarios."""
        if self._results is None:
            self.run_scenarios()

        results = self._results or []
        m = self.portfolio.metrics

        summary: Dict = {
            "portfolio_name":        self.portfolio.portfolio_name,
            "scenario_count":        len(results),
            "base_portfolio_value":  round(m.total_portfolio_value, 2),
            "base_total_noi":        round(m.total_annual_noi, 2),
            "base_cap_rate":         round(m.portfolio_cap_rate, 4),
            "diversification_score": round(self.portfolio.get_diversification_score(), 4),
            "scenarios":             [r.to_dict() for r in results],
        }

        if results:
            stressed_values = [r.stressed_portfolio_value for r in results]
            stressed_nois   = [r.stressed_total_noi       for r in results]

            summary["min_stressed_value"] = round(min(stressed_values), 2)
            summary["max_stressed_value"] = round(max(stressed_values), 2)
            summary["min_stressed_noi"]   = round(min(stressed_nois), 2)
            summary["max_stressed_noi"]   = round(max(stressed_nois), 2)

            if m.total_portfolio_value > 0:
                summary["value_at_risk_pct"] = round(
                    (m.total_portfolio_value - min(stressed_values)) / m.total_portfolio_value,
                    4,
                )
            else:
                summary["value_at_risk_pct"] = 0.0

        return summary
