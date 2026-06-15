"""
HABU Engine — Highest and Best Use Analysis (IVS 105).

Applies the Residual Method to determine the land value implied by
a proposed highest-and-best use, and flags whether that use is
financially feasible.

Formula chain:
    buildable_area        = total_land_area_sqm × max_far_allowed
    expected_habu_noi     = buildable_area × expected_noi_per_sqm_annual
    gross_development_value (GDV) = expected_habu_noi / cap_rate
    development_cost      = buildable_area × development_cost_per_m2
    developer_profit      = GDV × developer_profit_rate   (default 15%)
    residual_land_value   = GDV − development_cost − developer_profit
    feasibility_status    → "feasible" | "not_feasible"

The engine.value is the residual_land_value in EGP.
"""

from decimal import Decimal

from .base import (
    EngineResult, AuditEntry, ValidationIssue, ValuationEngine,
)

_DEFAULT_DEVELOPER_PROFIT_RATE: float = 0.15   # 15% of GDV — typical Egyptian market


class HABUEngine(ValuationEngine):
    """
    Highest and Best Use (HABU) — Residual Land Value engine — Phase 16 v1.

    Inputs (dict keys):
        total_land_area_sqm          float  required
        max_far_allowed              float  required (floor area ratio)
        expected_noi_per_sqm_annual  float  required (EGP/sqm/year)
        development_cost_per_m2      float  required (EGP/sqm of buildable area)
        cap_rate                     float  required (e.g. 0.08 for 8%)
        developer_profit_rate        float  optional (default 0.15)
        existing_building_value      float  optional (triggers medium confidence)
        proposed_habu_use            str    optional (warning if absent)
        current_use                  str    optional (warning if absent)

    Outputs (EngineResult):
        value       = residual_land_value (Decimal, EGP)
        confidence  = high | medium | low | insufficient
        metadata    = {buildable_area_sqm, expected_habu_noi,
                       gross_development_value, development_cost,
                       developer_profit, residual_land_value,
                       land_value_per_sqm, feasibility_status,
                       cap_rate, developer_profit_rate,
                       existing_building_value, assumptions}
    """

    name    = "habu"
    version = "1.0.0"

    def __init__(self) -> None:
        self.default_developer_profit_rate: float = _DEFAULT_DEVELOPER_PROFIT_RATE

    # ------------------------------------------------------------------
    # Abstract method implementations
    # ------------------------------------------------------------------

    def validate(self, inputs: dict) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        land_area = inputs.get("total_land_area_sqm", 0) or 0
        if land_area <= 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_LAND_AREA",
                message=f"total_land_area_sqm must be > 0; got {land_area}",
            ))

        far = inputs.get("max_far_allowed", 0) or 0
        if far <= 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_FAR",
                message=f"max_far_allowed must be > 0; got {far}",
            ))

        noi_ppm = inputs.get("expected_noi_per_sqm_annual")
        if noi_ppm is None:
            issues.append(ValidationIssue(
                severity="error",
                code="MISSING_NOI_PER_SQM",
                message="expected_noi_per_sqm_annual is required for HABU residual calculation",
            ))
        elif float(noi_ppm) <= 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_NOI_PER_SQM",
                message=f"expected_noi_per_sqm_annual must be > 0; got {noi_ppm}",
            ))

        dev_cost = inputs.get("development_cost_per_m2")
        if dev_cost is None:
            issues.append(ValidationIssue(
                severity="error",
                code="MISSING_DEV_COST",
                message="development_cost_per_m2 is required for HABU residual calculation",
            ))
        elif float(dev_cost) <= 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_DEV_COST",
                message=f"development_cost_per_m2 must be > 0; got {dev_cost}",
            ))

        cap_rate = inputs.get("cap_rate")
        if cap_rate is None:
            issues.append(ValidationIssue(
                severity="error",
                code="MISSING_CAP_RATE",
                message="cap_rate is required for GDV calculation",
            ))
        elif not (0 < float(cap_rate) < 1.0):
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_CAP_RATE",
                message=f"cap_rate must be in (0, 1); got {cap_rate}",
            ))

        dev_profit = inputs.get("developer_profit_rate")
        if dev_profit is not None:
            if not (0.0 <= float(dev_profit) < 1.0):
                issues.append(ValidationIssue(
                    severity="error",
                    code="INVALID_DEVELOPER_PROFIT_RATE",
                    message=f"developer_profit_rate must be in [0, 1); got {dev_profit}",
                ))

        # Warnings — contextual, do not block calculation
        if not inputs.get("proposed_habu_use"):
            issues.append(ValidationIssue(
                severity="warning",
                code="MISSING_PROPOSED_USE",
                message="proposed_habu_use not provided — HABU analysis lacks narrative context",
            ))

        if not inputs.get("current_use"):
            issues.append(ValidationIssue(
                severity="warning",
                code="MISSING_CURRENT_USE",
                message="current_use not provided — cannot assess change-of-use impact",
            ))

        return issues

    def calculate(self, inputs: dict) -> EngineResult:
        """HABU Residual Method → residual_land_value → EngineResult."""
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

        land_area        = float(inputs["total_land_area_sqm"])
        far              = float(inputs["max_far_allowed"])
        noi_ppm          = float(inputs["expected_noi_per_sqm_annual"])
        dev_cost_pm2     = float(inputs["development_cost_per_m2"])
        cap_rate         = float(inputs["cap_rate"])
        dev_profit_rate  = float(
            inputs["developer_profit_rate"]
            if inputs.get("developer_profit_rate") is not None
            else self.default_developer_profit_rate
        )
        current_use     = inputs.get("current_use", "")
        proposed_use    = inputs.get("proposed_habu_use", "")
        existing_bldg   = float(inputs.get("existing_building_value", 0) or 0)

        audit_trail: list[AuditEntry] = []

        # ── Step 1: Buildable area ────────────────────────────────────
        buildable_area = land_area * far
        audit_trail.append(AuditEntry(
            step_name="Calculate buildable area",
            inputs={"total_land_area_sqm": land_area, "max_far_allowed": far},
            outputs={"buildable_area_sqm": round(buildable_area, 2)},
            formula="buildable_area = total_land_area × max_far_allowed",
            references=["IVS 105: Highest and Best Use", "EGVS_3.1: Land Analysis"],
        ))

        # ── Step 2: Expected annual HABU NOI ─────────────────────────
        expected_habu_noi = buildable_area * noi_ppm
        audit_trail.append(AuditEntry(
            step_name="Calculate expected HABU NOI",
            inputs={"buildable_area_sqm": round(buildable_area, 2), "noi_per_sqm_annual": noi_ppm},
            outputs={"expected_habu_noi": round(expected_habu_noi, 2)},
            formula="expected_habu_noi = buildable_area × noi_per_sqm_annual",
            references=["IVS 105: HABU Income Projection", "EGVS_5.1"],
        ))

        # ── Step 3: Gross Development Value (GDV) ────────────────────
        gdv = expected_habu_noi / cap_rate
        audit_trail.append(AuditEntry(
            step_name="Calculate Gross Development Value (GDV)",
            inputs={"expected_habu_noi": round(expected_habu_noi, 2), "cap_rate": cap_rate},
            outputs={"gdv": round(gdv, 2)},
            formula="GDV = expected_habu_noi / cap_rate",
            references=["IVS 105: Residual Method", "EGVS_3.2: GDV"],
        ))

        # ── Step 4: Total development cost ───────────────────────────
        development_cost = buildable_area * dev_cost_pm2
        audit_trail.append(AuditEntry(
            step_name="Calculate total development cost",
            inputs={"buildable_area_sqm": round(buildable_area, 2), "dev_cost_per_m2": dev_cost_pm2},
            outputs={"development_cost": round(development_cost, 2)},
            formula="development_cost = buildable_area × development_cost_per_m2",
            references=["IVS 105: Cost Estimation", "EGVS_4.1"],
        ))

        # ── Step 5: Developer profit allowance ───────────────────────
        developer_profit = gdv * dev_profit_rate
        audit_trail.append(AuditEntry(
            step_name="Calculate developer profit allowance",
            inputs={"gdv": round(gdv, 2), "developer_profit_rate": dev_profit_rate},
            outputs={"developer_profit": round(developer_profit, 2)},
            formula="developer_profit = GDV × developer_profit_rate",
            references=["IVS 105: Developer Profit", "RICS Red Book GN1"],
        ))

        # ── Step 6: Residual land value ───────────────────────────────
        residual_land_value = gdv - development_cost - developer_profit
        audit_trail.append(AuditEntry(
            step_name="Calculate residual land value",
            inputs={
                "gdv": round(gdv, 2),
                "development_cost": round(development_cost, 2),
                "developer_profit": round(developer_profit, 2),
            },
            outputs={"residual_land_value": round(residual_land_value, 2)},
            formula="residual_land_value = GDV − development_cost − developer_profit",
            references=["IVS 105: Residual Land Value", "EGVS_3.3"],
        ))

        # ── Step 7: Feasibility test ──────────────────────────────────
        feasibility_status = "feasible" if residual_land_value > 0 else "not_feasible"
        audit_trail.append(AuditEntry(
            step_name="Determine feasibility status",
            inputs={"residual_land_value": round(residual_land_value, 2)},
            outputs={"feasibility_status": feasibility_status},
            formula="feasible if residual_land_value > 0",
            references=["IVS 105: Financial Feasibility Test"],
        ))

        # ── Confidence ────────────────────────────────────────────────
        if not proposed_use or not current_use:
            confidence = "low"
        elif residual_land_value <= 0:
            confidence = "low"
        elif existing_bldg > 0:
            confidence = "medium"
        else:
            confidence = "high"

        land_value_per_sqm = residual_land_value / land_area if land_area > 0 else 0.0

        metadata: dict = {
            "current_use":               current_use,
            "proposed_habu_use":         proposed_use,
            "buildable_area_sqm":        round(buildable_area, 2),
            "expected_habu_noi":         round(expected_habu_noi, 2),
            "gross_development_value":   round(gdv, 2),
            "development_cost":          round(development_cost, 2),
            "developer_profit":          round(developer_profit, 2),
            "residual_land_value":       round(residual_land_value, 2),
            "land_value_per_sqm":        round(land_value_per_sqm, 2),
            "feasibility_status":        feasibility_status,
            "cap_rate":                  cap_rate,
            "developer_profit_rate":     dev_profit_rate,
            "existing_building_value":   existing_bldg,
            "assumptions": [
                f"Proposed use: {proposed_use}" if proposed_use else "No proposed use specified",
                f"Current use: {current_use}" if current_use else "No current use specified",
                f"FAR {far} × {land_area:.0f} sqm = {buildable_area:.0f} sqm buildable area",
                f"Developer profit: {dev_profit_rate:.0%} of GDV",
                "Straight-line NOI projection — no phasing or lease-up period assumed",
            ],
        }

        return EngineResult(
            engine_name=self.name,
            value=Decimal(str(round(residual_land_value, 2))),
            confidence=confidence,
            audit_trail=audit_trail,
            issues=issues,
            metadata=metadata,
        )
