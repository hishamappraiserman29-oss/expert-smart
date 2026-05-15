"""
dcf_model.py — Discounted Cash Flow Income Model (Phase 10.0)

Multi-year cash flow projections + NPV analysis for commercial properties
and investment valuations.  Additive layer — no Phase 4-9 logic is modified.

Classes:
    AnnualCashFlow   — Single-year cash flow projection
    TerminalValue    — Residual value at end of explicit forecast period
    DCFModel         — Full DCF valuation (NPV of cash flows + terminal value)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional


# ── Annual cash flow ──────────────────────────────────────────────────────────

@dataclass
class AnnualCashFlow:
    """Single year cash flow in DCF model."""

    year: int
    gross_potential_income: float
    vacancy_rate: float
    effective_rental_income: float
    operating_expenses: float
    net_operating_income: float
    debt_service: float
    cash_flow_to_investor: float

    expense_ratio: float = 0.0
    noi_margin: float = 0.0

    def calculate(self) -> None:
        """Calculate derived metrics."""
        if self.effective_rental_income > 0:
            self.expense_ratio = self.operating_expenses / self.effective_rental_income
            self.noi_margin    = self.net_operating_income / self.effective_rental_income

    def to_dict(self) -> Dict:
        return {
            "year":                    self.year,
            "gross_potential_income":  self.gross_potential_income,
            "vacancy_rate":            self.vacancy_rate,
            "effective_rental_income": self.effective_rental_income,
            "operating_expenses":      self.operating_expenses,
            "net_operating_income":    self.net_operating_income,
            "debt_service":            self.debt_service,
            "cash_flow_to_investor":   self.cash_flow_to_investor,
            "expense_ratio":           round(self.expense_ratio, 4),
            "noi_margin":              round(self.noi_margin, 4),
        }


# ── Terminal value ────────────────────────────────────────────────────────────

@dataclass
class TerminalValue:
    """Terminal value at end of DCF explicit period."""

    final_year_noi: float
    terminal_cap_rate: float
    terminal_noi_growth: float
    discount_rate: float
    holding_period: int

    method: str = "cap_rate"     # "cap_rate" | "gordon_growth"

    terminal_value: float    = 0.0
    pv_terminal_value: float = 0.0

    def calculate_cap_rate_method(self) -> None:
        """Terminal value = Final Year NOI / Terminal Cap Rate."""
        if self.terminal_cap_rate > 0:
            self.terminal_value = self.final_year_noi / self.terminal_cap_rate

    def calculate_gordon_growth_method(self) -> None:
        """Terminal value = Final Year NOI × (1 + g) / (d - g)."""
        spread = self.discount_rate - self.terminal_noi_growth
        if spread > 0:
            numerator = self.final_year_noi * (1 + self.terminal_noi_growth)
            self.terminal_value = numerator / spread

    def calculate_pv(self) -> None:
        """PV of terminal value = Terminal Value / (1 + d)^n."""
        if self.discount_rate > 0:
            discount_factor       = (1 + self.discount_rate) ** self.holding_period
            self.pv_terminal_value = self.terminal_value / discount_factor

    def calculate(self) -> None:
        """Calculate terminal value and its present value."""
        if self.method == "cap_rate":
            self.calculate_cap_rate_method()
        elif self.method == "gordon_growth":
            self.calculate_gordon_growth_method()
        self.calculate_pv()

    def to_dict(self) -> Dict:
        return {
            "method":              self.method,
            "final_year_noi":     self.final_year_noi,
            "terminal_cap_rate":  self.terminal_cap_rate,
            "terminal_noi_growth": self.terminal_noi_growth,
            "terminal_value":     round(self.terminal_value, 2),
            "pv_terminal_value":  round(self.pv_terminal_value, 2),
            "holding_period":     self.holding_period,
        }


# ── DCF model ─────────────────────────────────────────────────────────────────

class DCFModel:
    """Discounted Cash Flow valuation model."""

    def __init__(
        self,
        discount_rate: float,
        holding_period: int = 5,
        terminal_cap_rate: Optional[float] = None,
    ) -> None:
        self.discount_rate    = discount_rate
        self.holding_period   = holding_period
        self.terminal_cap_rate = terminal_cap_rate if terminal_cap_rate is not None \
                                 else discount_rate

        self.annual_cash_flows: List[AnnualCashFlow]   = []
        self.terminal_value:    Optional[TerminalValue] = None

        self.pv_cash_flows:   float = 0.0
        self.pv_terminal_value: float = 0.0
        self.property_value:  float = 0.0

    # ── Building the model ────────────────────────────────────────────────────

    def add_annual_cash_flow(
        self,
        year: int,
        gross_income: float,
        vacancy_rate: float,
        operating_expenses: float,
        debt_service: float = 0.0,
    ) -> AnnualCashFlow:
        """Add a single-year cash flow projection."""
        eri = gross_income * (1 - vacancy_rate)
        noi = eri - operating_expenses
        cf  = noi - debt_service

        acf = AnnualCashFlow(
            year=year,
            gross_potential_income=gross_income,
            vacancy_rate=vacancy_rate,
            effective_rental_income=eri,
            operating_expenses=operating_expenses,
            net_operating_income=noi,
            debt_service=debt_service,
            cash_flow_to_investor=cf,
        )
        acf.calculate()
        self.annual_cash_flows.append(acf)
        return acf

    def set_terminal_value(
        self,
        final_year_noi: float,
        method: str = "cap_rate",
        terminal_noi_growth: float = 0.02,
    ) -> TerminalValue:
        """Set terminal value calculation."""
        self.terminal_value = TerminalValue(
            final_year_noi=final_year_noi,
            terminal_cap_rate=self.terminal_cap_rate,
            terminal_noi_growth=terminal_noi_growth,
            discount_rate=self.discount_rate,
            holding_period=self.holding_period,
            method=method,
        )
        self.terminal_value.calculate()
        return self.terminal_value

    # ── Core calculation ──────────────────────────────────────────────────────

    def calculate_npv(self) -> float:
        """Calculate NPV of all cash flows. Returns property_value."""
        self.pv_cash_flows = 0.0

        for acf in self.annual_cash_flows:
            discount_factor     = (1 + self.discount_rate) ** acf.year
            self.pv_cash_flows += acf.cash_flow_to_investor / discount_factor

        self.pv_terminal_value = (
            self.terminal_value.pv_terminal_value
            if self.terminal_value else 0.0
        )

        self.property_value = self.pv_cash_flows + self.pv_terminal_value
        return self.property_value

    # ── Reporting ─────────────────────────────────────────────────────────────

    def get_cash_flow_summary(self) -> Dict:
        """Aggregate statistics across all projected years."""
        n = len(self.annual_cash_flows)
        if n == 0:
            return {
                "years_projected": 0,
                "total_gross_income": 0.0,
                "total_noi": 0.0,
                "total_cash_flow": 0.0,
                "average_vacancy_rate": 0.0,
                "average_noi_margin": 0.0,
                "discount_rate": self.discount_rate,
                "terminal_cap_rate": self.terminal_cap_rate,
            }

        total_gross   = sum(a.gross_potential_income for a in self.annual_cash_flows)
        total_noi     = sum(a.net_operating_income   for a in self.annual_cash_flows)
        total_cf      = sum(a.cash_flow_to_investor  for a in self.annual_cash_flows)
        avg_vacancy   = sum(a.vacancy_rate           for a in self.annual_cash_flows) / n
        avg_noi_margin = sum(a.noi_margin            for a in self.annual_cash_flows) / n

        return {
            "years_projected":     n,
            "total_gross_income":  total_gross,
            "total_noi":           total_noi,
            "total_cash_flow":     total_cf,
            "average_vacancy_rate": avg_vacancy,
            "average_noi_margin":  avg_noi_margin,
            "discount_rate":       self.discount_rate,
            "terminal_cap_rate":   self.terminal_cap_rate,
        }

    def get_valuation_summary(self) -> Dict:
        """Full DCF results, JSON-serializable."""
        return {
            "pv_cash_flows":     round(self.pv_cash_flows, 2),
            "pv_terminal_value": round(self.pv_terminal_value, 2),
            "property_value":    round(self.property_value, 2),
            "discount_rate":     self.discount_rate,
            "terminal_cap_rate": self.terminal_cap_rate,
            "holding_period":    self.holding_period,
            "annual_cash_flows": [a.to_dict() for a in self.annual_cash_flows],
            "terminal_value":    self.terminal_value.to_dict()
                                 if self.terminal_value else None,
        }
