"""
ESG / Environmental Remediation Engine (IVS 2024 — ESG Considerations / RICS TIP 9).

Quantifies the net ESG impact on property value by aggregating environmental costs
(remediation, fines) against green benefits (energy savings, carbon credits,
green premium uplift).

Formulas:
    total_costs          = remediation_cost + environmental_fines
    total_benefits       = energy_savings + carbon_credit_value + green_premium
    net_esg_adjustment   = total_benefits − total_costs

    Positive adjustment → net green benefit (property value uplift)
    Negative adjustment → net remediation burden (property value reduction)

Safety:
    This engine is STANDALONE — net_esg_adjustment does NOT automatically
    modify market_value in any report or /api/valuation response.
    ESG inputs must be independently verified by qualified environmental consultants.
"""

from decimal import Decimal

from .base import (
    EngineResult, AuditEntry, ValidationIssue, ValuationEngine,
)

_ALL_OPTIONAL_KEYS = (
    "remediation_cost",
    "environmental_fines",
    "energy_savings",
    "carbon_credit_value",
    "green_premium",
)

_HIGH_COST_THRESHOLD: float = 0.50   # costs > 50% of total_benefits → warn


class ESGRemediationEngine(ValuationEngine):
    """
    ESG / Environmental Remediation engine — Phase 16.6 v1.

    All inputs are optional individually, but at least one must be supplied.

    Inputs (dict keys):
        remediation_cost      float  optional (≥ 0) — site clean-up / decontamination cost
        environmental_fines   float  optional (≥ 0) — regulatory penalties or levies
        energy_savings        float  optional (≥ 0) — annual energy efficiency savings (capitalised)
        carbon_credit_value   float  optional (≥ 0) — market value of carbon offsets / credits
        green_premium         float  optional (≥ 0) — green-certification value uplift

    Outputs (EngineResult):
        value      = net_esg_adjustment (Decimal, EGP; can be negative = net cost)
        confidence = high | medium | low | insufficient
        metadata   = {remediation_cost, environmental_fines,
                      energy_savings, carbon_credit_value, green_premium,
                      total_costs, total_benefits, net_esg_adjustment,
                      components_supplied}
    """

    name    = "esg_remediation"
    version = "1.0.0"

    def validate(self, inputs: dict) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        supplied = [k for k in _ALL_OPTIONAL_KEYS if inputs.get(k) is not None]
        if not supplied:
            issues.append(ValidationIssue(
                severity="error",
                code="NO_ESG_INPUTS",
                message=(
                    "At least one ESG component is required: "
                    "remediation_cost, environmental_fines, energy_savings, "
                    "carbon_credit_value, or green_premium"
                ),
            ))

        for key in _ALL_OPTIONAL_KEYS:
            val = inputs.get(key)
            if val is not None and float(val) < 0:
                issues.append(ValidationIssue(
                    severity="error",
                    code=f"INVALID_{key.upper()}",
                    message=f"{key} must be ≥ 0; got {val}",
                ))

        cost_keys    = ("remediation_cost", "environmental_fines")
        benefit_keys = ("energy_savings", "carbon_credit_value", "green_premium")

        has_costs    = any(inputs.get(k) is not None for k in cost_keys)
        has_benefits = any(inputs.get(k) is not None for k in benefit_keys)

        if not has_costs and has_benefits:
            issues.append(ValidationIssue(
                severity="info",
                code="NO_COST_COMPONENTS",
                message=(
                    "No cost components (remediation_cost, environmental_fines) supplied — "
                    "net_esg_adjustment will represent pure green benefit"
                ),
            ))
        if has_costs and not has_benefits:
            issues.append(ValidationIssue(
                severity="info",
                code="NO_BENEFIT_COMPONENTS",
                message=(
                    "No benefit components (energy_savings, carbon_credit_value, "
                    "green_premium) supplied — net_esg_adjustment will be negative (net cost)"
                ),
            ))

        return issues

    def calculate(self, inputs: dict) -> EngineResult:
        """Aggregate costs → aggregate benefits → net ESG adjustment → EngineResult."""
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

        rem   = float(inputs.get("remediation_cost")    or 0)
        fines = float(inputs.get("environmental_fines") or 0)
        esav  = float(inputs.get("energy_savings")      or 0)
        carb  = float(inputs.get("carbon_credit_value") or 0)
        gprem = float(inputs.get("green_premium")       or 0)

        audit_trail: list[AuditEntry] = []

        # ── Step 1: Total costs ───────────────────────────────────────
        total_costs = rem + fines
        audit_trail.append(AuditEntry(
            step_name="Aggregate ESG costs",
            inputs={
                "remediation_cost":    round(rem, 2),
                "environmental_fines": round(fines, 2),
            },
            outputs={"total_costs": round(total_costs, 2)},
            formula="total_costs = remediation_cost + environmental_fines",
            references=["RICS TIP 9: Environmental Liability in Valuation",
                        "IVS 2024: ESG Considerations in Valuation"],
        ))

        # ── Step 2: Total benefits ─────────────────────────────────────
        total_benefits = esav + carb + gprem
        if total_benefits > 0 and total_costs > 0:
            cost_ratio = total_costs / total_benefits
            if cost_ratio > _HIGH_COST_THRESHOLD:
                issues.append(ValidationIssue(
                    severity="warning",
                    code="HIGH_REMEDIATION_COST_RATIO",
                    message=(
                        f"Total costs {total_costs:,.0f} EGP represent "
                        f"{cost_ratio:.0%} of total benefits — "
                        "net ESG position may be negative; review remediation scope"
                    ),
                ))
        audit_trail.append(AuditEntry(
            step_name="Aggregate ESG benefits",
            inputs={
                "energy_savings":      round(esav, 2),
                "carbon_credit_value": round(carb, 2),
                "green_premium":       round(gprem, 2),
            },
            outputs={"total_benefits": round(total_benefits, 2)},
            formula="total_benefits = energy_savings + carbon_credit_value + green_premium",
            references=["RICS: Green Value Premium",
                        "Carbon Disclosure Project (CDP): Carbon Credit Valuation",
                        "CRREM: Energy Efficiency Savings"],
        ))

        # ── Step 3: Net ESG adjustment ────────────────────────────────
        net_esg_adjustment = total_benefits - total_costs
        esg_direction = "net benefit" if net_esg_adjustment >= 0 else "net cost"
        audit_trail.append(AuditEntry(
            step_name="Compute net ESG adjustment",
            inputs={
                "total_benefits": round(total_benefits, 2),
                "total_costs":    round(total_costs, 2),
            },
            outputs={
                "net_esg_adjustment": round(net_esg_adjustment, 2),
                "esg_direction":      esg_direction,
            },
            formula="net_esg_adjustment = total_benefits − total_costs",
            references=["IVS 2024 para. 50: ESG Net Impact",
                        "RICS TIP 9: Net Environmental Value Adjustment"],
        ))

        # ── Confidence ────────────────────────────────────────────────
        components_supplied = sum(
            1 for k in _ALL_OPTIONAL_KEYS if inputs.get(k) is not None
        )
        if components_supplied >= 3:
            confidence = "high"
        elif components_supplied == 2:
            confidence = "medium"
        else:
            confidence = "low"

        metadata: dict = {
            "remediation_cost":      round(rem, 2) if inputs.get("remediation_cost") is not None else None,
            "environmental_fines":   round(fines, 2) if inputs.get("environmental_fines") is not None else None,
            "energy_savings":        round(esav, 2) if inputs.get("energy_savings") is not None else None,
            "carbon_credit_value":   round(carb, 2) if inputs.get("carbon_credit_value") is not None else None,
            "green_premium":         round(gprem, 2) if inputs.get("green_premium") is not None else None,
            "total_costs":           round(total_costs, 2),
            "total_benefits":        round(total_benefits, 2),
            "net_esg_adjustment":    round(net_esg_adjustment, 2),
            "esg_direction":         esg_direction,
            "components_supplied":   components_supplied,
        }

        return EngineResult(
            engine_name=self.name,
            value=Decimal(str(round(net_esg_adjustment, 2))),
            confidence=confidence,
            audit_trail=audit_trail,
            issues=issues,
            metadata=metadata,
        )
