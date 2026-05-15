"""
dcf_sensitivity.py — DCF Sensitivity Analysis (Phase 10.1)

Multi-scenario terminal value comparison and discount rate sensitivity
analysis.  Additive layer — no Phase 4-9 logic is modified.

Classes:
    TerminalValueStrategy    — Constants for the three supported TV methods
    TerminalValueScenario    — Single scenario assumptions + results
    DCFSensitivityAnalysis   — Multi-scenario builder + summary
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from adapters.dcf_model import DCFModel


# ── Terminal value strategy constants ─────────────────────────────────────────

class TerminalValueStrategy:
    """Supported terminal value strategies."""

    PERPETUITY_CAP_RATE = "perpetuity_cap_rate"
    GORDON_GROWTH       = "gordon_growth"
    EXIT_MULTIPLE       = "exit_multiple"

    @staticmethod
    def supported() -> List[str]:
        return [
            TerminalValueStrategy.PERPETUITY_CAP_RATE,
            TerminalValueStrategy.GORDON_GROWTH,
            TerminalValueStrategy.EXIT_MULTIPLE,
        ]


# ── Scenario dataclass ────────────────────────────────────────────────────────

@dataclass
class TerminalValueScenario:
    """Terminal value scenario assumptions and results."""

    strategy: str
    label: str

    terminal_cap_rate:   Optional[float] = None
    terminal_noi_growth: Optional[float] = None
    exit_multiple:       Optional[float] = None

    terminal_value:    float = 0.0
    pv_terminal_value: float = 0.0
    property_value:    float = 0.0
    irr:               float = 0.0

    def to_dict(self) -> Dict:
        return {
            "strategy":           self.strategy,
            "label":              self.label,
            "terminal_cap_rate":  self.terminal_cap_rate,
            "terminal_noi_growth": self.terminal_noi_growth,
            "exit_multiple":      self.exit_multiple,
            "terminal_value":     round(self.terminal_value, 2),
            "pv_terminal_value":  round(self.pv_terminal_value, 2),
            "property_value":     round(self.property_value, 2),
            "irr":                round(self.irr, 4),
        }


# ── Main analysis class ───────────────────────────────────────────────────────

class DCFSensitivityAnalysis:
    """Multi-scenario DCF sensitivity analysis."""

    def __init__(
        self,
        discount_rate: float,
        holding_period: int,
        base_terminal_cap_rate: float,
    ) -> None:
        self.discount_rate          = discount_rate
        self.holding_period         = holding_period
        self.base_terminal_cap_rate = base_terminal_cap_rate

        # year → (gross_income, vacancy_rate, operating_expenses, debt_service)
        self.annual_cash_flows: Dict[int, Tuple[float, float, float, float]] = {}
        self.scenarios: List[TerminalValueScenario] = []

    # ── Data input ────────────────────────────────────────────────────────────

    def add_year_projection(
        self,
        year: int,
        gross_income: float,
        vacancy_rate: float,
        operating_expenses: float,
        debt_service: float = 0.0,
    ) -> None:
        self.annual_cash_flows[year] = (gross_income, vacancy_rate,
                                        operating_expenses, debt_service)

    # ── Scenario factories ────────────────────────────────────────────────────

    def create_cap_rate_scenarios(
        self,
        conservative_cap: float,
        base_cap: float,
        optimistic_cap: float,
    ) -> None:
        """Conservative/Base/Optimistic cap-rate scenarios.

        Higher cap rate → lower terminal value → lower property value.
        """
        definitions = [
            ("Conservative", conservative_cap),
            ("Base",          base_cap),
            ("Optimistic",    optimistic_cap),
        ]
        for label, cap in definitions:
            scenario = TerminalValueScenario(
                strategy=TerminalValueStrategy.PERPETUITY_CAP_RATE,
                label=label,
                terminal_cap_rate=cap,
            )
            dcf = self._build_dcf_cap_rate(cap)
            dcf.calculate_npv()
            scenario.terminal_value    = dcf.terminal_value.terminal_value
            scenario.pv_terminal_value = dcf.terminal_value.pv_terminal_value
            scenario.property_value    = dcf.property_value
            self.scenarios.append(scenario)

    def create_discount_rate_scenarios(self, rates: List[float]) -> None:
        """One scenario per discount rate using the base terminal cap rate."""
        noi = self._final_year_noi()
        for rate in rates:
            scenario = TerminalValueScenario(
                strategy=TerminalValueStrategy.PERPETUITY_CAP_RATE,
                label=f"Discount {rate * 100:.0f}%",
                terminal_cap_rate=self.base_terminal_cap_rate,
            )
            dcf = DCFModel(
                discount_rate=rate,
                holding_period=self.holding_period,
                terminal_cap_rate=self.base_terminal_cap_rate,
            )
            self._populate_cash_flows(dcf)
            dcf.set_terminal_value(noi, method="cap_rate")
            dcf.calculate_npv()
            scenario.terminal_value    = dcf.terminal_value.terminal_value
            scenario.pv_terminal_value = dcf.terminal_value.pv_terminal_value
            scenario.property_value    = dcf.property_value
            self.scenarios.append(scenario)

    def create_noi_growth_scenarios(
        self,
        conservative_growth: float,
        base_growth: float,
        optimistic_growth: float,
    ) -> None:
        """Conservative/Base/Optimistic Gordon Growth scenarios.

        Higher perpetual growth → higher terminal value → higher property value.
        """
        definitions = [
            ("Conservative Growth", conservative_growth),
            ("Base Growth",          base_growth),
            ("Optimistic Growth",    optimistic_growth),
        ]
        for label, growth in definitions:
            scenario = TerminalValueScenario(
                strategy=TerminalValueStrategy.GORDON_GROWTH,
                label=label,
                terminal_noi_growth=growth,
            )
            dcf = self._build_dcf_gordon(growth)
            dcf.calculate_npv()
            scenario.terminal_value    = dcf.terminal_value.terminal_value
            scenario.pv_terminal_value = dcf.terminal_value.pv_terminal_value
            scenario.property_value    = dcf.property_value
            self.scenarios.append(scenario)

    # ── Reporting ─────────────────────────────────────────────────────────────

    def get_scenario_summary(self) -> Dict:
        """Aggregate statistics across all scenarios."""
        if not self.scenarios:
            return {}
        values = [s.property_value for s in self.scenarios]
        return {
            "base_discount_rate":     self.discount_rate,
            "base_terminal_cap_rate": self.base_terminal_cap_rate,
            "holding_period":         self.holding_period,
            "scenario_count":         len(self.scenarios),
            "min_value":              round(min(values), 2),
            "max_value":              round(max(values), 2),
            "average_value":          round(sum(values) / len(values), 2),
            "value_range":            round(max(values) - min(values), 2),
            "scenarios":              [s.to_dict() for s in self.scenarios],
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    def _final_year_noi(self) -> float:
        """Derive NOI for the last projected year."""
        final_year = max(self.annual_cash_flows)
        gross, vacancy, opex, _ = self.annual_cash_flows[final_year]
        eri = gross * (1 - vacancy)
        return eri - opex

    def _populate_cash_flows(self, dcf: DCFModel) -> None:
        """Add all stored year projections to a DCFModel."""
        for year, (gross, vacancy, opex, debt) in self.annual_cash_flows.items():
            dcf.add_annual_cash_flow(year, gross, vacancy, opex, debt)

    def _build_dcf_cap_rate(self, cap_rate: float) -> DCFModel:
        dcf = DCFModel(
            discount_rate=self.discount_rate,
            holding_period=self.holding_period,
            terminal_cap_rate=cap_rate,
        )
        self._populate_cash_flows(dcf)
        dcf.set_terminal_value(self._final_year_noi(), method="cap_rate")
        return dcf

    def _build_dcf_gordon(self, growth_rate: float) -> DCFModel:
        dcf = DCFModel(
            discount_rate=self.discount_rate,
            holding_period=self.holding_period,
            terminal_cap_rate=self.base_terminal_cap_rate,
        )
        self._populate_cash_flows(dcf)
        dcf.set_terminal_value(
            self._final_year_noi(),
            method="gordon_growth",
            terminal_noi_growth=growth_rate,
        )
        return dcf
