"""
Insurance Reinstatement Cost Engine (IVS 105 / RICS Insurance Valuation Guidance).

Computes the insurance reinstatement value — the cost to fully rebuild a property
to its current specification — NOT the market value or depreciated value.

Formula (component method):
    building_cost          = building_area_sqm × (construction_cost_per_m2
                                                   + finishing_cost_per_m2)
    reinstatement_cost_new = building_cost + mep_cost + debris_removal_cost
                           + professional_fees
    insurance_value        = reinstatement_cost_new × (1 + construction_inflation_rate)

Override:
    If caller supplies `reinstatement_cost_new`, the component computation is skipped
    and only the inflation adjustment is applied.

Key distinction: No depreciation is applied. Insurance covers the full cost of
rebuilding, not the depreciated value of what exists.
"""

from decimal import Decimal

from .base import (
    EngineResult, AuditEntry, ValidationIssue, ValuationEngine,
)

_HIGH_INFLATION_WARN: float = 0.30   # > 30% construction inflation → unusual


class InsuranceEngine(ValuationEngine):
    """
    Insurance Reinstatement Cost engine — Phase 16.4 v1.

    Inputs (dict keys):
        building_area_sqm           float  required (unless reinstatement_cost_new supplied)
        construction_cost_per_m2    float  required (unless reinstatement_cost_new supplied)
        finishing_cost_per_m2       float  optional ≥ 0, default 0
        mep_cost                    float  optional ≥ 0 (M&E + Plumbing, absolute EGP)
        debris_removal_cost         float  optional ≥ 0 (absolute EGP)
        professional_fees           float  optional ≥ 0 (architects, engineers, absolute EGP)
        construction_inflation_rate float  optional ≥ 0 (e.g. 0.10 = 10%), default 0
        reinstatement_cost_new      float  optional override — skips component calculation

    Outputs (EngineResult):
        value      = insurance_value (Decimal, EGP)
        confidence = high | medium | low | insufficient
        metadata   = {reinstatement_cost_new, building_cost, mep_cost, debris_removal_cost,
                      professional_fees, construction_inflation_rate, insurance_value,
                      rcn_source}
    """

    name    = "insurance"
    version = "1.0.0"

    # ------------------------------------------------------------------
    # Abstract method implementations
    # ------------------------------------------------------------------

    def validate(self, inputs: dict) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        rcn_override = inputs.get("reinstatement_cost_new")
        if rcn_override is not None:
            if float(rcn_override) <= 0:
                issues.append(ValidationIssue(
                    severity="error",
                    code="INVALID_RCN",
                    message=f"reinstatement_cost_new must be > 0; got {rcn_override}",
                ))
        else:
            area = inputs.get("building_area_sqm", 0) or 0
            if float(area) <= 0:
                issues.append(ValidationIssue(
                    severity="error",
                    code="MISSING_BUILDING_AREA",
                    message=f"building_area_sqm must be > 0; got {area}",
                ))
            cost_pm2 = inputs.get("construction_cost_per_m2", 0) or 0
            if float(cost_pm2) <= 0:
                issues.append(ValidationIssue(
                    severity="error",
                    code="MISSING_CONSTRUCTION_COST",
                    message=f"construction_cost_per_m2 must be > 0; got {cost_pm2}",
                ))

        finishing = inputs.get("finishing_cost_per_m2")
        if finishing is None:
            issues.append(ValidationIssue(
                severity="warning",
                code="MISSING_FINISHING_COST",
                message="finishing_cost_per_m2 not supplied — assumed zero",
            ))
        elif float(finishing) < 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_FINISHING_COST",
                message=f"finishing_cost_per_m2 must be ≥ 0; got {finishing}",
            ))

        for field, code in (
            ("mep_cost",            "MISSING_MEP_COST"),
            ("debris_removal_cost", "MISSING_DEBRIS_REMOVAL_COST"),
            ("professional_fees",   "MISSING_PROFESSIONAL_FEES"),
        ):
            val = inputs.get(field)
            if val is None:
                issues.append(ValidationIssue(
                    severity="warning",
                    code=code,
                    message=f"{field} not supplied — assumed zero; may understate insurance value",
                ))
            elif float(val) < 0:
                issues.append(ValidationIssue(
                    severity="error",
                    code=f"INVALID_{field.upper()}",
                    message=f"{field} must be ≥ 0; got {val}",
                ))

        inflation = inputs.get("construction_inflation_rate")
        if inflation is None or float(inflation) == 0.0:
            issues.append(ValidationIssue(
                severity="warning",
                code="ZERO_INFLATION_RATE",
                message=(
                    "construction_inflation_rate is 0 or not supplied — "
                    "no future cost adjustment applied; consider current build cost inflation"
                ),
            ))
        elif float(inflation) < 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_INFLATION_RATE",
                message=f"construction_inflation_rate must be ≥ 0; got {inflation}",
            ))
        elif float(inflation) > _HIGH_INFLATION_WARN:
            issues.append(ValidationIssue(
                severity="warning",
                code="HIGH_INFLATION_RATE",
                message=(
                    f"construction_inflation_rate {float(inflation):.1%} exceeds "
                    f"{_HIGH_INFLATION_WARN:.0%} — verify source of construction cost escalation"
                ),
            ))

        return issues

    def calculate(self, inputs: dict) -> EngineResult:
        """Component costs → RCN → inflation adjustment → insurance_value → EngineResult."""
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

        audit_trail: list[AuditEntry] = []

        # ── Step 1: Establish Reinstatement Cost New (RCN) ───────────
        rcn_override  = inputs.get("reinstatement_cost_new")
        finishing     = float(inputs.get("finishing_cost_per_m2") or 0)
        mep           = float(inputs.get("mep_cost") or 0)
        debris        = float(inputs.get("debris_removal_cost") or 0)
        prof_fees     = float(inputs.get("professional_fees") or 0)

        if rcn_override is not None:
            rcn          = float(rcn_override)
            building_cost = 0.0
            rcn_source   = "caller-supplied reinstatement_cost_new override"
        else:
            area          = float(inputs["building_area_sqm"])
            const_pm2     = float(inputs["construction_cost_per_m2"])
            building_cost = area * (const_pm2 + finishing)
            rcn           = building_cost + mep + debris + prof_fees
            rcn_source    = "area × (construction_cost + finishing) + mep + debris + fees"

        audit_trail.append(AuditEntry(
            step_name="Establish Reinstatement Cost New (RCN)",
            inputs={
                "building_area_sqm":          inputs.get("building_area_sqm"),
                "construction_cost_per_m2":   inputs.get("construction_cost_per_m2"),
                "finishing_cost_per_m2":      finishing,
                "mep_cost":                   mep,
                "debris_removal_cost":        debris,
                "professional_fees":          prof_fees,
                "reinstatement_cost_new_override": rcn_override,
            },
            outputs={
                "building_cost":          round(building_cost, 2),
                "reinstatement_cost_new": round(rcn, 2),
                "source":                 rcn_source,
            },
            formula=(
                "RCN = area × (construction_cost + finishing) + mep + debris + fees  "
                "(or caller-supplied override)"
            ),
            references=["IVS 105: Insurance Reinstatement", "RICS: Insurance Valuation Guidance"],
        ))

        # ── Step 2: Apply construction inflation ─────────────────────
        inflation       = float(inputs.get("construction_inflation_rate") or 0)
        insurance_value = rcn * (1.0 + inflation)

        audit_trail.append(AuditEntry(
            step_name="Apply construction inflation adjustment",
            inputs={
                "reinstatement_cost_new":     round(rcn, 2),
                "construction_inflation_rate": inflation,
            },
            outputs={"insurance_value": round(insurance_value, 2)},
            formula="insurance_value = RCN × (1 + construction_inflation_rate)",
            references=["RICS: Insurance Cost Escalation", "EGVS_4.6: Future Cost Adjustment"],
        ))

        # ── Confidence ────────────────────────────────────────────────
        has_finishing = finishing > 0
        has_mep       = mep > 0
        has_debris    = debris > 0
        has_fees      = prof_fees > 0
        has_inflation = inflation > 0
        optional_count = sum([has_finishing, has_mep, has_debris, has_fees])

        if optional_count >= 3 and has_inflation:
            confidence = "high"
        elif optional_count >= 1 or has_inflation or rcn_override is not None:
            confidence = "medium"
        else:
            confidence = "low"

        metadata: dict = {
            "reinstatement_cost_new":     round(rcn, 2),
            "rcn_source":                 rcn_source,
            "building_cost":              round(building_cost, 2),
            "finishing_cost":             finishing,
            "mep_cost":                   mep,
            "debris_removal_cost":        debris,
            "professional_fees":          prof_fees,
            "construction_inflation_rate": inflation,
            "insurance_value":            round(insurance_value, 2),
        }

        return EngineResult(
            engine_name=self.name,
            value=Decimal(str(round(insurance_value, 2))),
            confidence=confidence,
            audit_trail=audit_trail,
            issues=issues,
            metadata=metadata,
        )
