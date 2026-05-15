"""
stress_test.py — Phase 24 Stress Test Suite
Pre-built Egyptian real estate market stress scenarios (COVID, CBE rate hike,
EGP devaluation, market crash, recovery) plus a custom scenario API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StressScenario:
    """Definition of a single stress scenario."""

    name:        str
    description: str
    shocks:      Dict[str, float]   # factor_name → % change
    severity:    str = "moderate"   # "mild" | "moderate" | "severe"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":        self.name,
            "description": self.description,
            "shocks":      self.shocks,
            "severity":    self.severity,
        }


@dataclass
class StressTestResult:
    """Outcome of applying one stress scenario to a base value."""

    scenario:        StressScenario
    base_value:      float
    stressed_value:  float
    impact_pct:      float      # (stressed - base) / base * 100
    severity:        str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario":       self.scenario.to_dict(),
            "base_value":     round(self.base_value, 2),
            "stressed_value": round(self.stressed_value, 2),
            "impact_pct":     round(self.impact_pct, 4),
            "severity":       self.severity,
        }


class StressTestSuite:
    """
    Run a battery of stress scenarios against a property base value.

    Five built-in Egyptian real estate market scenarios are pre-loaded.
    Custom scenarios can be appended with :meth:`add_scenario`.
    """

    _BUILT_IN: List[StressScenario] = [
        StressScenario(
            name="covid_shock",
            description="COVID-19 market disruption: severe drop in transactions and prices",
            shocks={"market_activity": -30.0, "price_level": -15.0},
            severity="severe",
        ),
        StressScenario(
            name="interest_rate_hike",
            description="CBE overnight rate +500 bps: higher financing cost reduces demand",
            shocks={"financing_cost": -20.0, "demand": -15.0},
            severity="moderate",
        ),
        StressScenario(
            name="currency_devaluation",
            description="EGP devaluation -30%: raises construction costs, USD-priced assets rise",
            shocks={"usd_prices": +20.0, "construction_cost": +25.0},
            severity="moderate",
        ),
        StressScenario(
            name="market_crash",
            description="Severe market downturn: deep price correction and liquidity crisis",
            shocks={"price_level": -40.0, "liquidity": -50.0},
            severity="severe",
        ),
        StressScenario(
            name="recovery_boom",
            description="Post-correction recovery: rising demand and capital inflows",
            shocks={"price_level": +25.0, "demand": +30.0},
            severity="mild",
        ),
    ]

    def __init__(self) -> None:
        self.scenarios: List[StressScenario] = list(self._BUILT_IN)

    # -- API ------------------------------------------------------------------

    def add_scenario(self, scenario: StressScenario) -> None:
        """Append a custom scenario to the suite."""
        self.scenarios.append(scenario)

    def get_scenario(self, name: str) -> Optional[StressScenario]:
        """Return scenario by name, or None if not found."""
        return next((s for s in self.scenarios if s.name == name), None)

    def run_scenario(self, scenario: StressScenario, base_value: float) -> StressTestResult:
        """
        Apply scenario shocks to *base_value*.

        Shocks compound multiplicatively:
        stressed = base × ∏(1 + shock_i / 100)
        """
        multiplier = 1.0
        for pct in scenario.shocks.values():
            multiplier *= (1.0 + pct / 100.0)

        stressed   = base_value * multiplier
        impact_pct = ((stressed - base_value) / base_value * 100.0) if base_value else 0.0

        return StressTestResult(
            scenario=scenario,
            base_value=base_value,
            stressed_value=stressed,
            impact_pct=impact_pct,
            severity=scenario.severity,
        )

    def run_all(self, base_value: float) -> List[StressTestResult]:
        """Run every scenario in the suite against *base_value*."""
        return [self.run_scenario(s, base_value) for s in self.scenarios]

    def worst_case(self, base_value: float) -> StressTestResult:
        """Return the scenario that produces the lowest stressed value."""
        results = self.run_all(base_value)
        return min(results, key=lambda r: r.stressed_value)

    def best_case(self, base_value: float) -> StressTestResult:
        """Return the scenario that produces the highest stressed value."""
        results = self.run_all(base_value)
        return max(results, key=lambda r: r.stressed_value)

    def summary(self, base_value: float) -> Dict[str, Any]:
        """Return a summary dict with all results plus worst/best case."""
        results = self.run_all(base_value)
        return {
            "base_value":  round(base_value, 2),
            "scenarios":   [r.to_dict() for r in results],
            "worst_case":  min(results, key=lambda r: r.stressed_value).to_dict(),
            "best_case":   max(results, key=lambda r: r.stressed_value).to_dict(),
            "total_scenarios": len(results),
        }
