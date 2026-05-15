"""
scenario_builder.py — Phase 24 Scenario Builder
Builds Optimistic / Base-Case / Pessimistic / Custom valuation scenarios
by composing parameter-level delta adjustments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ScenarioType(str, Enum):
    OPTIMISTIC  = "optimistic"
    BASE_CASE   = "base_case"
    PESSIMISTIC = "pessimistic"
    STRESS_TEST = "stress_test"
    CUSTOM      = "custom"


@dataclass
class ScenarioParameter:
    """Single adjustable parameter for scenario analysis."""

    name:               str
    base_value:         float
    optimistic_delta:   float   # % change for optimistic scenario (+ve = upside)
    pessimistic_delta:  float   # % change for pessimistic scenario (-ve = downside)
    description:        str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":              self.name,
            "base_value":        self.base_value,
            "optimistic_delta":  self.optimistic_delta,
            "pessimistic_delta": self.pessimistic_delta,
            "description":       self.description,
        }


@dataclass
class ScenarioResult:
    """Result of one scenario evaluation."""

    scenario_type: ScenarioType
    name:          str
    value:         float
    base_value:    float
    delta_pct:     float
    parameters:    List[Dict[str, Any]]
    description:   str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_type": self.scenario_type.value,
            "name":          self.name,
            "value":         round(self.value, 2),
            "base_value":    round(self.base_value, 2),
            "delta_pct":     round(self.delta_pct, 4),
            "parameters":    self.parameters,
            "description":   self.description,
        }


class ScenarioBuilder:
    """
    Build Optimistic / Base-Case / Pessimistic scenarios from a set of
    adjustable parameters.

    Each parameter contributes a multiplicative adjustment to the base
    property value; adjustments compound across parameters.

    Usage::
        result = (
            ScenarioBuilder(base_value=3_000_000)
            .add_parameter("market_growth", base_value=0, optimistic_delta=+10, pessimistic_delta=-10)
            .add_parameter("cap_rate", base_value=0, optimistic_delta=+5,  pessimistic_delta=-5)
            .build_scenario(ScenarioType.OPTIMISTIC)
        )
    """

    def __init__(self, base_value: float) -> None:
        self.base_value = base_value
        self.parameters: List[ScenarioParameter] = []

    # -- Fluent API -----------------------------------------------------------

    def add_parameter(
        self,
        name: str,
        base_value: float,
        optimistic_delta: float,
        pessimistic_delta: float,
        description: str = "",
    ) -> "ScenarioBuilder":
        self.parameters.append(
            ScenarioParameter(
                name=name,
                base_value=base_value,
                optimistic_delta=optimistic_delta,
                pessimistic_delta=pessimistic_delta,
                description=description,
            )
        )
        return self

    # -- Build ----------------------------------------------------------------

    def build_scenario(
        self,
        scenario_type: ScenarioType,
        name: str = "",
        description: str = "",
    ) -> ScenarioResult:
        """
        Evaluate the base_value under the given scenario type.

        Optimistic/Pessimistic: compound each parameter's delta multiplicatively.
        Base-Case: return base_value unchanged.
        """
        scenario_name = name or scenario_type.value.replace("_", " ").title()

        if scenario_type == ScenarioType.BASE_CASE:
            value = self.base_value
        elif scenario_type == ScenarioType.OPTIMISTIC:
            value = self._apply_deltas("optimistic")
        elif scenario_type in (ScenarioType.PESSIMISTIC, ScenarioType.STRESS_TEST):
            value = self._apply_deltas("pessimistic")
        else:
            value = self.base_value

        delta_pct = ((value - self.base_value) / self.base_value) if self.base_value else 0.0

        return ScenarioResult(
            scenario_type=scenario_type,
            name=scenario_name,
            value=value,
            base_value=self.base_value,
            delta_pct=delta_pct,
            parameters=[p.to_dict() for p in self.parameters],
            description=description,
        )

    def build_all(self) -> List[ScenarioResult]:
        """Build Optimistic, Base-Case, and Pessimistic in one call."""
        return [
            self.build_scenario(ScenarioType.OPTIMISTIC),
            self.build_scenario(ScenarioType.BASE_CASE),
            self.build_scenario(ScenarioType.PESSIMISTIC),
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_value": self.base_value,
            "parameters": [p.to_dict() for p in self.parameters],
        }

    # -- Private --------------------------------------------------------------

    def _apply_deltas(self, direction: str) -> float:
        """Compound multiplicative adjustments for all parameters."""
        multiplier = 1.0
        for p in self.parameters:
            delta = p.optimistic_delta if direction == "optimistic" else p.pessimistic_delta
            multiplier *= (1.0 + delta / 100.0)
        return self.base_value * multiplier
