"""
Cost Approach Engine — Full Depreciation Breakdown (IVS 105 / EGVS 4).

Extends beyond CostEngine (cost.py, which uses cost_tables.json + straight-line
physical depreciation only) by accepting all three standard forms of depreciation
explicitly and supporting a pre-computed Replacement Cost New override.

Formula:
    RCN  = building_area_sqm × cost_per_m2   (or caller-supplied replacement_cost_new)
    total_dep_rate = min(physical + functional + external, 1.0)
                     (overridden by depreciation_rate if supplied)
    DRC  = RCN × (1 − total_dep_rate)
    final_cost_approach_value = DRC + land_value

Three depreciation forms (fractions in [0, 1]):
    physical_depreciation       — wear and tear / physical condition
    functional_obsolescence     — layout, design, or utility inadequacies
    external_obsolescence       — location, market, or economic factors

All three are additive and clamped to 1.0 in aggregate.
If depreciation_rate is supplied it overrides the three-way breakdown.
"""

from decimal import Decimal

from .base import (
    EngineResult, AuditEntry, ValidationIssue, ValuationEngine,
)

_DEP_RATE_CEILING: float = 1.0
_HIGH_DEP_THRESHOLD: float = 0.80   # ≥ 80% depreciation → medium confidence


class CostApproachEngine(ValuationEngine):
    """
    Cost Approach (Full Depreciation Breakdown) engine — Phase 16.2 v1.

    Distinct from CostEngine (cost.py):
    • No cost_tables.json dependency — caller supplies cost_per_m2 or RCN
    • Explicit physical / functional / external depreciation breakdown
    • depreciation_rate override for when total is already known

    Inputs (dict keys):
        building_area_sqm        float  required (> 0)
        cost_per_m2              float  required unless replacement_cost_new supplied
        replacement_cost_new     float  optional — overrides area × cost_per_m2
        land_value               float  required (≥ 0)
        physical_depreciation    float  optional, fraction [0, 1], default 0
        functional_obsolescence  float  optional, fraction [0, 1], default 0
        external_obsolescence    float  optional, fraction [0, 1], default 0
        depreciation_rate        float  optional override [0, 1] — takes precedence
                                        over the three-way breakdown

    Outputs (EngineResult):
        value      = final_cost_approach_value (Decimal, EGP)
        confidence = high | medium | low | insufficient
        metadata   = {replacement_cost_new, physical_depreciation,
                      functional_obsolescence, external_obsolescence,
                      total_depreciation_rate, depreciated_replacement_cost,
                      land_value, final_cost_approach_value,
                      depreciation_source, rcn_source}
    """

    name    = "cost_approach"
    version = "1.0.0"

    # ------------------------------------------------------------------
    # Abstract method implementations
    # ------------------------------------------------------------------

    def validate(self, inputs: dict) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        area = inputs.get("building_area_sqm", 0) or 0
        if float(area) <= 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_BUILDING_AREA",
                message=f"building_area_sqm must be > 0; got {area}",
            ))

        land = inputs.get("land_value")
        if land is None:
            issues.append(ValidationIssue(
                severity="error",
                code="MISSING_LAND_VALUE",
                message="land_value is required (use 0 for leased/unknown land)",
            ))
        elif float(land) < 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_LAND_VALUE",
                message=f"land_value must be ≥ 0; got {land}",
            ))
        elif float(land) == 0:
            issues.append(ValidationIssue(
                severity="warning",
                code="ZERO_LAND_VALUE",
                message="land_value = 0 — land contribution unknown; confidence will be low",
            ))

        rcn_input   = inputs.get("replacement_cost_new")
        cost_pm2    = inputs.get("cost_per_m2")
        if rcn_input is None and cost_pm2 is None:
            issues.append(ValidationIssue(
                severity="error",
                code="MISSING_COST_INPUT",
                message=(
                    "Either cost_per_m2 or replacement_cost_new must be supplied"
                ),
            ))
        elif cost_pm2 is not None and float(cost_pm2) <= 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_COST_PER_M2",
                message=f"cost_per_m2 must be > 0; got {cost_pm2}",
            ))
        elif rcn_input is not None and float(rcn_input) <= 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_RCN",
                message=f"replacement_cost_new must be > 0; got {rcn_input}",
            ))

        dep_override = inputs.get("depreciation_rate")
        if dep_override is not None:
            if not (0.0 <= float(dep_override) <= _DEP_RATE_CEILING):
                issues.append(ValidationIssue(
                    severity="error",
                    code="INVALID_DEPRECIATION_RATE",
                    message=(
                        f"depreciation_rate must be in [0, 1]; got {dep_override}"
                    ),
                ))
        else:
            for key in ("physical_depreciation", "functional_obsolescence", "external_obsolescence"):
                val = inputs.get(key)
                if val is not None and not (0.0 <= float(val) <= 1.0):
                    issues.append(ValidationIssue(
                        severity="error",
                        code=f"INVALID_{key.upper()}",
                        message=f"{key} must be in [0, 1]; got {val}",
                    ))

        # Warn when no depreciation is specified at all
        all_zero = (
            dep_override is None
            and all(
                (inputs.get(k) or 0) == 0
                for k in ("physical_depreciation", "functional_obsolescence", "external_obsolescence")
            )
        )
        if all_zero:
            issues.append(ValidationIssue(
                severity="warning",
                code="ZERO_DEPRECIATION",
                message="No depreciation applied — verify asset is new or depreciation is intentionally zero",
            ))

        return issues

    def calculate(self, inputs: dict) -> EngineResult:
        """Full cost approach: RCN − Accrued Depreciation + Land → EngineResult."""
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

        area        = float(inputs["building_area_sqm"])
        land_value  = float(inputs.get("land_value", 0) or 0)

        audit_trail: list[AuditEntry] = []

        # ── Step 1: Replacement Cost New (RCN) ───────────────────────
        rcn_input  = inputs.get("replacement_cost_new")
        cost_pm2   = inputs.get("cost_per_m2")
        if rcn_input is not None:
            rcn        = float(rcn_input)
            rcn_source = "caller-supplied replacement_cost_new"
        else:
            rcn        = float(cost_pm2) * area
            rcn_source = f"cost_per_m2 × building_area_sqm"
        audit_trail.append(AuditEntry(
            step_name="Establish Replacement Cost New (RCN)",
            inputs={"cost_per_m2": cost_pm2, "building_area_sqm": area,
                    "replacement_cost_new_override": rcn_input},
            outputs={"rcn": round(rcn, 2), "source": rcn_source},
            formula="RCN = cost_per_m2 × building_area_sqm  (or caller override)",
            references=["IVS 105: Cost Approach", "EGVS_4.1: Replacement Cost New"],
        ))

        # ── Step 2: Depreciation breakdown ───────────────────────────
        dep_override  = inputs.get("depreciation_rate")
        phys  = float(inputs.get("physical_depreciation", 0) or 0)
        func  = float(inputs.get("functional_obsolescence", 0) or 0)
        ext   = float(inputs.get("external_obsolescence", 0) or 0)

        if dep_override is not None:
            total_dep_rate = min(float(dep_override), _DEP_RATE_CEILING)
            dep_source = "caller-supplied depreciation_rate override"
        else:
            raw_sum        = phys + func + ext
            total_dep_rate = min(raw_sum, _DEP_RATE_CEILING)
            dep_source = "sum(physical + functional + external)"

        audit_trail.append(AuditEntry(
            step_name="Determine total accrued depreciation",
            inputs={
                "physical_depreciation":   phys,
                "functional_obsolescence": func,
                "external_obsolescence":   ext,
                "depreciation_rate_override": dep_override,
            },
            outputs={
                "total_depreciation_rate": round(total_dep_rate * 100, 4),
                "source": dep_source,
            },
            formula=(
                "total_dep = min(physical + functional + external, 1.0)  "
                "[or depreciation_rate if supplied]"
            ),
            references=["IVS 105: Accrued Depreciation", "EGVS_4.3: Three-Form Depreciation"],
        ))

        # ── Step 3: Depreciated Replacement Cost (DRC) ───────────────
        drc = rcn * (1.0 - total_dep_rate)
        audit_trail.append(AuditEntry(
            step_name="Calculate Depreciated Replacement Cost (DRC)",
            inputs={"rcn": round(rcn, 2), "total_dep_rate_pct": round(total_dep_rate * 100, 4)},
            outputs={"drc": round(drc, 2)},
            formula="DRC = RCN × (1 − total_depreciation_rate)",
            references=["EGVS_4.4: DRC", "IVS 105: Depreciated Replacement Cost"],
        ))

        # ── Step 4: Add land value ─────────────────────────────────────
        final_value = drc + land_value
        audit_trail.append(AuditEntry(
            step_name="Add land value — final cost approach value",
            inputs={"drc": round(drc, 2), "land_value": land_value},
            outputs={"final_cost_approach_value": round(final_value, 2)},
            formula="final_value = DRC + land_value",
            references=["EGVS_4.5: Land + Building", "IVS 105: Cost Approach Final Value"],
        ))

        # ── Confidence ────────────────────────────────────────────────
        if land_value <= 0:
            confidence = "low"
        elif total_dep_rate >= _HIGH_DEP_THRESHOLD:
            confidence = "medium"
        else:
            confidence = "high"

        metadata: dict = {
            "rcn_source":                   rcn_source,
            "replacement_cost_new":         round(rcn, 2),
            "physical_depreciation":        phys,
            "functional_obsolescence":      func,
            "external_obsolescence":        ext,
            "depreciation_source":          dep_source,
            "total_depreciation_rate":      round(total_dep_rate, 6),
            "depreciated_replacement_cost": round(drc, 2),
            "land_value":                   land_value,
            "final_cost_approach_value":    round(final_value, 2),
        }

        return EngineResult(
            engine_name=self.name,
            value=Decimal(str(round(final_value, 2))),
            confidence=confidence,
            audit_trail=audit_trail,
            issues=issues,
            metadata=metadata,
        )
