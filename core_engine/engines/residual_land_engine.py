"""
Residual Land Value Engine — Development Appraisal (IVS 105 / RICS Guidance).

Computes land value by residual deduction from Gross Development Value (GDV).
All cost items (development cost, developer profit, finance cost, professional
fees) are deducted from GDV to arrive at the Residual Land Value (RLV).

Formula:
    total_costs        = total_development_cost + developer_profit
                       + finance_cost + professional_fees
    residual_land_value = GDV − total_costs

    sensitivity_high   = (GDV × 1.05) − total_costs   (+5% GDV)
    sensitivity_low    = (GDV × 0.95) − total_costs   (−5% GDV)

The engine is distinct from HABUEngine (habu_engine.py) which models
high-and-best-use buildable area from FAR; this engine operates on a
caller-supplied GDV and explicit cost line items — suitable for detailed
development appraisals and loan security assessments.
"""

from decimal import Decimal
from typing import Optional

from .base import (
    EngineResult, AuditEntry, ValidationIssue, ValuationEngine,
)

_GDV_SENSITIVITY_STEP: float = 0.05   # ±5% GDV stress test
_ZERO_PROFIT_WARN_THRESH: float = 0.0
_HIGH_COST_RATIO_WARN: float = 0.90   # costs ≥ 90% of GDV → warn


class ResidualLandEngine(ValuationEngine):
    """
    Residual Land Value (Development Appraisal) engine — Phase 16.3 v1.

    Distinct from HABUEngine (habu_engine.py):
    • Operates on a caller-supplied GDV (not derived from FAR/NOI)
    • Explicit cost line items: dev_cost, profit, finance, professional fees
    • Sensitivity analysis: ±5% GDV stress

    Inputs (dict keys):
        gross_development_value   float  required (> 0) — total realised value
        total_development_cost    float  required (≥ 0) — hard + soft construction costs
        developer_profit          float  optional (≥ 0, default 0)
        finance_cost              float  optional (≥ 0, default 0)
        professional_fees         float  optional (≥ 0, default 0)

    Outputs (EngineResult):
        value      = residual_land_value (Decimal, EGP); None if GDV ≤ total_costs
        confidence = high | medium | low | insufficient
        metadata   = {gross_development_value, total_development_cost,
                      developer_profit, finance_cost, professional_fees,
                      total_costs, cost_ratio,
                      residual_land_value, feasibility_status,
                      sensitivity_high, sensitivity_low}
    """

    name    = "residual_land"
    version = "1.0.0"

    # ------------------------------------------------------------------
    # Abstract method implementations
    # ------------------------------------------------------------------

    def validate(self, inputs: dict) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        gdv = inputs.get("gross_development_value")
        if gdv is None:
            issues.append(ValidationIssue(
                severity="error",
                code="MISSING_GDV",
                message="gross_development_value is required",
            ))
        elif float(gdv) <= 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_GDV",
                message=f"gross_development_value must be > 0; got {gdv}",
            ))

        tdc = inputs.get("total_development_cost")
        if tdc is None:
            issues.append(ValidationIssue(
                severity="error",
                code="MISSING_DEVELOPMENT_COST",
                message="total_development_cost is required",
            ))
        elif float(tdc) < 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_DEVELOPMENT_COST",
                message=f"total_development_cost must be ≥ 0; got {tdc}",
            ))

        for field, code in (
            ("developer_profit", "INVALID_DEVELOPER_PROFIT"),
            ("finance_cost",     "INVALID_FINANCE_COST"),
            ("professional_fees","INVALID_PROFESSIONAL_FEES"),
        ):
            val = inputs.get(field)
            if val is not None and float(val) < 0:
                issues.append(ValidationIssue(
                    severity="error",
                    code=code,
                    message=f"{field} must be ≥ 0; got {val}",
                ))

        # Advisory: zero developer profit
        profit = inputs.get("developer_profit", 0) or 0
        if float(profit) == _ZERO_PROFIT_WARN_THRESH:
            issues.append(ValidationIssue(
                severity="warning",
                code="ZERO_DEVELOPER_PROFIT",
                message=(
                    "developer_profit = 0 — verify whether profit is intentionally "
                    "excluded (e.g. self-development) or missing from the appraisal"
                ),
            ))

        return issues

    def calculate(self, inputs: dict) -> EngineResult:
        """GDV − costs → RLV + sensitivity → EngineResult."""
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

        gdv     = float(inputs["gross_development_value"])
        tdc     = float(inputs["total_development_cost"])
        profit  = float(inputs.get("developer_profit",  0) or 0)
        finance = float(inputs.get("finance_cost",       0) or 0)
        prof_fees = float(inputs.get("professional_fees", 0) or 0)

        audit_trail: list[AuditEntry] = []

        # ── Step 1: Aggregate total costs ─────────────────────────────
        total_costs = tdc + profit + finance + prof_fees
        cost_ratio  = total_costs / gdv if gdv > 0 else 0.0

        audit_trail.append(AuditEntry(
            step_name="Aggregate total development costs",
            inputs={
                "total_development_cost": round(tdc, 2),
                "developer_profit":       round(profit, 2),
                "finance_cost":           round(finance, 2),
                "professional_fees":      round(prof_fees, 2),
            },
            outputs={
                "total_costs": round(total_costs, 2),
                "cost_ratio":  round(cost_ratio, 4),
            },
            formula="total_costs = total_development_cost + developer_profit + finance_cost + professional_fees",
            references=["IVS 105: Development Appraisal", "RICS GN: Residual Method"],
        ))

        # High cost ratio warning
        if cost_ratio >= _HIGH_COST_RATIO_WARN:
            issues.append(ValidationIssue(
                severity="warning",
                code="HIGH_COST_RATIO",
                message=(
                    f"total_costs are {cost_ratio:.0%} of GDV — "
                    "residual land value will be thin or negative; "
                    "verify cost inputs carefully"
                ),
            ))

        # ── Step 2: Residual Land Value ───────────────────────────────
        rlv = gdv - total_costs
        feasibility_status = "feasible" if rlv > 0 else "not_feasible"

        audit_trail.append(AuditEntry(
            step_name="Calculate Residual Land Value (RLV)",
            inputs={
                "gross_development_value": round(gdv, 2),
                "total_costs":             round(total_costs, 2),
            },
            outputs={
                "residual_land_value": round(rlv, 2),
                "feasibility_status":  feasibility_status,
            },
            formula="residual_land_value = GDV − total_costs",
            references=["RICS GN: Residual Valuation", "EGVS_6.1: Land Residual"],
        ))

        # ── Step 3: Sensitivity analysis ±5% GDV ─────────────────────
        sensitivity_high = (gdv * (1.0 + _GDV_SENSITIVITY_STEP)) - total_costs
        sensitivity_low  = (gdv * (1.0 - _GDV_SENSITIVITY_STEP)) - total_costs

        audit_trail.append(AuditEntry(
            step_name="Sensitivity analysis — ±5% GDV stress",
            inputs={
                "gdv": round(gdv, 2),
                "total_costs": round(total_costs, 2),
                "sensitivity_step_pct": _GDV_SENSITIVITY_STEP * 100,
            },
            outputs={
                "sensitivity_high": round(sensitivity_high, 2),
                "sensitivity_low":  round(sensitivity_low,  2),
            },
            formula=(
                "sensitivity_high = (GDV × 1.05) − total_costs; "
                "sensitivity_low  = (GDV × 0.95) − total_costs"
            ),
            references=["RICS GN: Sensitivity Analysis", "EGVS_6.2: Stress Testing"],
        ))

        # ── Confidence ────────────────────────────────────────────────
        if rlv <= 0:
            confidence = "low"
        elif cost_ratio >= _HIGH_COST_RATIO_WARN:
            confidence = "medium"
        elif profit == 0.0:
            confidence = "medium"
        else:
            confidence = "high"

        # value = None when not feasible (land is non-valuable under this scheme)
        result_value: Optional[Decimal] = (
            Decimal(str(round(rlv, 2))) if rlv > 0 else None
        )

        metadata: dict = {
            "gross_development_value": round(gdv, 2),
            "total_development_cost":  round(tdc, 2),
            "developer_profit":        round(profit, 2),
            "finance_cost":            round(finance, 2),
            "professional_fees":       round(prof_fees, 2),
            "total_costs":             round(total_costs, 2),
            "cost_ratio":              round(cost_ratio, 4),
            "residual_land_value":     round(rlv, 2),
            "feasibility_status":      feasibility_status,
            "sensitivity_high":        round(sensitivity_high, 2),
            "sensitivity_low":         round(sensitivity_low,  2),
        }

        return EngineResult(
            engine_name=self.name,
            value=result_value,
            confidence=confidence,
            audit_trail=audit_trail,
            issues=issues,
            metadata=metadata,
        )
