"""
portfolio.py — Portfolio Analysis Framework (Phase 11.0)

Multi-property aggregation, risk metrics, and diversification analysis.
Additive layer — no Phase 4-10 logic is modified.

Classes:
    PropertyInPortfolio  — Single property in portfolio context
    AggregateMetrics     — Portfolio-level statistics
    PortfolioBuilder     — Chainable builder + metric calculation
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional


# ── Per-property record ───────────────────────────────────────────────────────

@dataclass
class PropertyInPortfolio:
    """Single property in portfolio context."""

    property_id:   str
    property_name: str
    property_type: str            # residential | commercial | land

    valuation_value:      float   # Market value (EGP)
    valuation_confidence: str     # high | medium | low

    annual_noi:          float    # Net operating income
    annual_gross_income: float    # Gross potential income

    portfolio_weight:       float = 0.0
    contribution_to_return: float = 0.0

    def calculate_metrics(self, total_portfolio_value: float) -> None:
        """Calculate portfolio-relative metrics."""
        if total_portfolio_value > 0:
            self.portfolio_weight       = self.valuation_value / total_portfolio_value
            self.contribution_to_return = self.annual_noi

    def to_dict(self) -> Dict:
        return {
            "property_id":           self.property_id,
            "property_name":         self.property_name,
            "property_type":         self.property_type,
            "valuation_value":       round(self.valuation_value, 2),
            "valuation_confidence":  self.valuation_confidence,
            "annual_noi":            round(self.annual_noi, 2),
            "annual_gross_income":   round(self.annual_gross_income, 2),
            "portfolio_weight":      round(self.portfolio_weight, 4),
            "contribution_to_return": round(self.contribution_to_return, 2),
        }


# ── Aggregate metrics ─────────────────────────────────────────────────────────

@dataclass
class AggregateMetrics:
    """Portfolio-level aggregate statistics."""

    total_portfolio_value:   float = 0.0
    number_of_properties:    int   = 0

    total_annual_noi:          float = 0.0
    total_annual_gross_income: float = 0.0
    portfolio_noi_margin:      float = 0.0

    value_by_type:    Dict[str, float] = field(default_factory=dict)
    type_percentages: Dict[str, float] = field(default_factory=dict)

    concentration_ratio: float = 0.0
    herfindahl_index:    float = 0.0

    portfolio_cap_rate: float = 0.0

    high_confidence_count:  int   = 0
    medium_confidence_count: int  = 0
    low_confidence_count:   int   = 0
    high_confidence_value:  float = 0.0

    def to_dict(self) -> Dict:
        return {
            "total_portfolio_value":    round(self.total_portfolio_value, 2),
            "number_of_properties":     self.number_of_properties,
            "total_annual_noi":         round(self.total_annual_noi, 2),
            "total_annual_gross_income": round(self.total_annual_gross_income, 2),
            "portfolio_noi_margin":     round(self.portfolio_noi_margin, 4),
            "value_by_type":            {k: round(v, 2) for k, v in self.value_by_type.items()},
            "type_percentages":         {k: round(v, 4) for k, v in self.type_percentages.items()},
            "concentration_ratio":      round(self.concentration_ratio, 4),
            "herfindahl_index":         round(self.herfindahl_index, 4),
            "portfolio_cap_rate":       round(self.portfolio_cap_rate, 4),
            "high_confidence_count":    self.high_confidence_count,
            "medium_confidence_count":  self.medium_confidence_count,
            "low_confidence_count":     self.low_confidence_count,
            "high_confidence_value":    round(self.high_confidence_value, 2),
        }


# ── Portfolio builder ─────────────────────────────────────────────────────────

class PortfolioBuilder:
    """Build and analyse a property portfolio."""

    def __init__(self, portfolio_name: str = "Default Portfolio") -> None:
        self.portfolio_name = portfolio_name
        self.properties: List[PropertyInPortfolio] = []
        self.metrics: Optional[AggregateMetrics]   = None

    # ── Building ──────────────────────────────────────────────────────────────

    def add_property(
        self,
        property_id:          str,
        property_name:        str,
        property_type:        str,
        valuation_value:      float,
        valuation_confidence: str,
        annual_noi:           float,
        annual_gross_income:  float,
    ) -> "PortfolioBuilder":
        """Add a property and return self for chaining."""
        self.properties.append(PropertyInPortfolio(
            property_id=property_id,
            property_name=property_name,
            property_type=property_type,
            valuation_value=valuation_value,
            valuation_confidence=valuation_confidence,
            annual_noi=annual_noi,
            annual_gross_income=annual_gross_income,
        ))
        self.metrics = None   # invalidate cached metrics
        return self

    # ── Metric calculation ────────────────────────────────────────────────────

    def calculate_metrics(self) -> None:
        """Compute and cache all portfolio-level metrics."""
        if not self.properties:
            self.metrics = AggregateMetrics()
            return

        m = AggregateMetrics()

        # Totals
        m.total_portfolio_value   = sum(p.valuation_value      for p in self.properties)
        m.number_of_properties    = len(self.properties)
        m.total_annual_noi        = sum(p.annual_noi            for p in self.properties)
        m.total_annual_gross_income = sum(p.annual_gross_income for p in self.properties)

        # Margins
        if m.total_annual_gross_income > 0:
            m.portfolio_noi_margin = m.total_annual_noi / m.total_annual_gross_income
        if m.total_portfolio_value > 0:
            m.portfolio_cap_rate   = m.total_annual_noi / m.total_portfolio_value

        # Value by type + type percentages
        type_values: Dict[str, float] = {}
        for p in self.properties:
            type_values[p.property_type] = type_values.get(p.property_type, 0.0) + p.valuation_value
        m.value_by_type = type_values
        if m.total_portfolio_value > 0:
            m.type_percentages = {
                pt: v / m.total_portfolio_value for pt, v in type_values.items()
            }

        # Concentration ratio (largest single property / total)
        if m.total_portfolio_value > 0:
            max_val = max(p.valuation_value for p in self.properties)
            m.concentration_ratio = max_val / m.total_portfolio_value

        # Herfindahl-Hirschman index (sum of squared weights)
        if m.total_portfolio_value > 0:
            weights = [p.valuation_value / m.total_portfolio_value for p in self.properties]
            m.herfindahl_index = sum(w * w for w in weights)

        # Confidence distribution
        for p in self.properties:
            conf = p.valuation_confidence.lower()
            if conf == "high":
                m.high_confidence_count  += 1
                m.high_confidence_value  += p.valuation_value
            elif conf == "medium":
                m.medium_confidence_count += 1
            else:
                m.low_confidence_count    += 1

        # Propagate weights to each property
        for p in self.properties:
            p.calculate_metrics(m.total_portfolio_value)

        self.metrics = m

    # ── Reporting ─────────────────────────────────────────────────────────────

    def get_portfolio_summary(self) -> Dict:
        """Return complete portfolio summary (JSON-serialisable)."""
        if self.metrics is None:
            self.calculate_metrics()
        return {
            "portfolio_name": self.portfolio_name,
            "metrics":        self.metrics.to_dict(),
            "properties":     [p.to_dict() for p in self.properties],
        }

    def get_diversification_score(self) -> float:
        """Diversification score: 1 − Herfindahl index (0 = concentrated, 1 = diversified)."""
        if self.metrics is None:
            self.calculate_metrics()
        return 1.0 - self.metrics.herfindahl_index
