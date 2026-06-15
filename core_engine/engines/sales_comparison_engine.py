"""
Sales Comparison Engine — Adjustment Grid Approach (IVS 230).

Each comparable sale receives three explicit percentage adjustments
supplied by the appraiser:
    location_adjustment          (e.g.  0.05 = +5%)
    physical_adjustment          (e.g. -0.10 = −10%)
    market_condition_adjustment  (e.g.  0.00 = no change)

Adjustments are applied multiplicatively per comparable:
    adjusted_ppm = price_per_m2 × (1+loc) × (1+phy) × (1+mkt)

Final value:
    avg_adjusted_ppm = mean(adjusted_ppm_i for all comparables)
    indicated_value  = avg_adjusted_ppm × subject_area_sqm

This engine is distinct from ComparativeEngine (which auto-computes
area/age/floor/finishing adjustments from raw comparable attributes).
SalesComparisonEngine is for appraisers who have already determined
adjustment percentages from market analysis.
"""

import statistics
from decimal import Decimal

from .base import (
    EngineResult, AuditEntry, ValidationIssue, ValuationEngine,
)

_MIN_COMPARABLES: int   = 3
_WARN_ADJUSTMENT: float = 0.30   # warn if any single adjustment exceeds ±30%
_CV_MEDIUM_THRESHOLD: float = 0.20  # CV > 20% → medium confidence
_CONF_ADJ_THRESHOLD: float  = 0.20  # any adj > 20% → medium confidence


class SalesComparisonEngine(ValuationEngine):
    """
    Sales Comparison Approach (Adjustment Grid) engine — Phase 16 v1.

    Inputs (dict keys):
        subject_area_sqm   float  required
        comparables        list   required — each element is a dict:
            price_per_m2               float  required (EGP/sqm)
            location_adjustment        float  optional (fraction; default 0)
            physical_adjustment        float  optional (fraction; default 0)
            market_condition_adjustment float optional (fraction; default 0)
            label                      str    optional (preserved in summary)

    Outputs (EngineResult):
        value      = indicated_value (Decimal, EGP)
        confidence = high | medium | low | insufficient
        metadata   = {comparable_count, average_price_per_m2,
                      avg_adjusted_price_per_m2, indicated_value,
                      coefficient_of_variation, adjustment_summary,
                      assumptions, warnings}
    """

    name    = "sales_comparison"
    version = "1.0.0"

    def __init__(self) -> None:
        self.min_comparables:       int   = _MIN_COMPARABLES
        self.warn_adjustment:       float = _WARN_ADJUSTMENT
        self.cv_medium_threshold:   float = _CV_MEDIUM_THRESHOLD
        self.conf_adj_threshold:    float = _CONF_ADJ_THRESHOLD

    # ------------------------------------------------------------------
    # Abstract method implementations
    # ------------------------------------------------------------------

    def validate(self, inputs: dict) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        subject_area = inputs.get("subject_area_sqm", 0) or 0
        if subject_area <= 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_SUBJECT_AREA",
                message=f"subject_area_sqm must be > 0; got {subject_area}",
            ))

        comparables = inputs.get("comparables") or []
        if not comparables:
            issues.append(ValidationIssue(
                severity="error",
                code="NO_COMPARABLES",
                message="comparables list is required and must not be empty",
            ))
            return issues  # nothing more to validate without comps

        if len(comparables) < self.min_comparables:
            issues.append(ValidationIssue(
                severity="warning",
                code="INSUFFICIENT_COMPARABLES",
                message=(
                    f"Only {len(comparables)} comparable(s) provided; "
                    f"minimum {self.min_comparables} recommended for reliable indication"
                ),
            ))

        for idx, comp in enumerate(comparables):
            ppm = comp.get("price_per_m2", 0) or 0
            if ppm <= 0:
                issues.append(ValidationIssue(
                    severity="error",
                    code=f"INVALID_COMP_PRICE_{idx}",
                    message=f"Comparable [{idx}] price_per_m2 must be > 0; got {ppm}",
                ))

            for adj_key in (
                "location_adjustment",
                "physical_adjustment",
                "market_condition_adjustment",
            ):
                adj_val = comp.get(adj_key, 0) or 0
                if abs(float(adj_val)) > self.warn_adjustment:
                    issues.append(ValidationIssue(
                        severity="warning",
                        code=f"LARGE_ADJUSTMENT_{adj_key.upper()}_{idx}",
                        message=(
                            f"Comparable [{idx}] {adj_key} = {adj_val:+.1%} "
                            f"exceeds ±{self.warn_adjustment:.0%} — "
                            "verify with independent market evidence"
                        ),
                    ))

        return issues

    def calculate(self, inputs: dict) -> EngineResult:
        """Adjustment grid → indicated value → EngineResult."""
        issues = self.validate(inputs)
        if any(i.severity == "error" for i in issues):
            return EngineResult(
                engine_name=self.name,
                value=None,
                confidence="insufficient",
                audit_trail=[],
                issues=issues,
                metadata={},
            )

        subject_area = float(inputs["subject_area_sqm"])
        comparables  = inputs["comparables"]

        audit_trail: list[AuditEntry] = []
        adjusted_prices: list[float]  = []
        raw_prices: list[float]        = []
        comp_summaries: list[dict]     = []

        # ── Step 1: Apply adjustments to each comparable ──────────────
        for idx, comp in enumerate(comparables):
            ppm     = float(comp.get("price_per_m2", 0))
            loc_adj = float(comp.get("location_adjustment", 0) or 0)
            phy_adj = float(comp.get("physical_adjustment", 0) or 0)
            mkt_adj = float(comp.get("market_condition_adjustment", 0) or 0)

            cumulative_factor = (1.0 + loc_adj) * (1.0 + phy_adj) * (1.0 + mkt_adj)
            adjusted_ppm      = ppm * cumulative_factor

            raw_prices.append(ppm)
            adjusted_prices.append(adjusted_ppm)

            summary: dict = {
                "index":                        idx,
                "price_per_m2":                 round(ppm, 2),
                "location_adjustment":          f"{loc_adj:+.1%}",
                "physical_adjustment":          f"{phy_adj:+.1%}",
                "market_condition_adjustment":  f"{mkt_adj:+.1%}",
                "cumulative_adjustment_pct":    round((cumulative_factor - 1.0) * 100, 2),
                "adjusted_price_per_m2":        round(adjusted_ppm, 2),
            }
            if "label" in comp:
                summary["label"] = comp["label"]
            comp_summaries.append(summary)

            audit_trail.append(AuditEntry(
                step_name=f"Apply adjustments — comparable [{idx}]",
                inputs={
                    "price_per_m2":                ppm,
                    "location_adjustment":         loc_adj,
                    "physical_adjustment":         phy_adj,
                    "market_condition_adjustment": mkt_adj,
                },
                outputs={
                    "cumulative_adj_factor":   round(cumulative_factor, 6),
                    "adjusted_price_per_m2":   round(adjusted_ppm, 2),
                },
                formula="adj_ppm = ppm × (1+loc) × (1+phy) × (1+mkt)",
                references=["EGVS_6.1: Sales Comparison Adjustments", "IVS 230: Market Approach"],
            ))

        # ── Step 2: Average adjusted price per m² ─────────────────────
        avg_adjusted_ppm = statistics.mean(adjusted_prices)
        audit_trail.append(AuditEntry(
            step_name="Average adjusted price per m²",
            inputs={"adjusted_prices": [round(p, 2) for p in adjusted_prices]},
            outputs={"avg_adjusted_price_per_m2": round(avg_adjusted_ppm, 2)},
            formula="avg_adjusted_ppm = mean(adjusted_ppm_i)",
            references=["EGVS_6.2: Reconciliation of Comparables"],
        ))

        # ── Step 3: Indicated value ───────────────────────────────────
        indicated_value = avg_adjusted_ppm * subject_area
        audit_trail.append(AuditEntry(
            step_name="Calculate indicated value",
            inputs={
                "avg_adjusted_price_per_m2": round(avg_adjusted_ppm, 2),
                "subject_area_sqm":          subject_area,
            },
            outputs={"indicated_value": round(indicated_value, 2)},
            formula="indicated_value = avg_adjusted_ppm × subject_area_sqm",
            references=["EGVS_6.3: Indicated Value", "IVS 230: Indicated Value Reconciliation"],
        ))

        # ── Confidence ────────────────────────────────────────────────
        n = len(adjusted_prices)
        cv: float
        if n >= 2:
            stdev = statistics.stdev(adjusted_prices)
            cv = (stdev / avg_adjusted_ppm) if avg_adjusted_ppm > 0 else 999.0
        else:
            cv = 999.0

        has_large_adj = any(
            abs(float(comp.get("location_adjustment", 0) or 0))          > self.conf_adj_threshold or
            abs(float(comp.get("physical_adjustment", 0) or 0))           > self.conf_adj_threshold or
            abs(float(comp.get("market_condition_adjustment", 0) or 0))   > self.conf_adj_threshold
            for comp in comparables
        )

        if n < self.min_comparables:
            confidence = "low"
        elif cv > self.cv_medium_threshold or has_large_adj:
            confidence = "medium"
        else:
            confidence = "high"

        avg_raw_ppm = statistics.mean(raw_prices)

        metadata: dict = {
            "comparable_count":          n,
            "average_price_per_m2":      round(avg_raw_ppm, 2),
            "avg_adjusted_price_per_m2": round(avg_adjusted_ppm, 2),
            "indicated_value":           round(indicated_value, 2),
            "coefficient_of_variation":  round(cv, 4) if cv != 999.0 else None,
            "adjustment_summary":        comp_summaries,
            "assumptions": [
                f"{n} comparable(s) used in adjustment grid",
                "Equal weight applied to all comparable sales",
                "Adjustments applied multiplicatively: (1+loc) × (1+phy) × (1+mkt)",
                "No additional time-of-sale adjustment beyond explicit market_condition_adjustment",
            ],
            "warnings": [i.message for i in issues if i.severity == "warning"],
        }

        return EngineResult(
            engine_name=self.name,
            value=Decimal(str(round(indicated_value, 2))),
            confidence=confidence,
            audit_trail=audit_trail,
            issues=issues,
            metadata=metadata,
        )
