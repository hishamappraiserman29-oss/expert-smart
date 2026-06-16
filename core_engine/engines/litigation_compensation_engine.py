"""
Litigation Compensation Engine (RICS Guidance Note — Compulsory Purchase / Eminent Domain).

Computes property damage compensation using the Before-and-After method,
supporting cost-to-cure analysis and severance damage to remainder parcels.

Formulas:
    diminution_in_value  = before_damage_value − after_damage_value
    total_compensation   = diminution_in_value + severance_damage

    Cost-to-cure viability (advisory):
        economically viable if cost_to_cure ≤ diminution_in_value

Safety:
    This engine is STANDALONE — compensation output does NOT automatically
    replace market_value in any report or /api/valuation response.
    Seek legal counsel before using this output in court proceedings.
"""

from decimal import Decimal

from .base import (
    EngineResult, AuditEntry, ValidationIssue, ValuationEngine,
)

_CURE_RATIO_WARN: float = 0.90   # warn when cost_to_cure > 90% of diminution


class LitigationCompensationEngine(ValuationEngine):
    """
    Litigation Compensation engine — Phase 16.6 v1.

    Inputs (dict keys):
        before_damage_value  float  required (> 0)  — property value before damage event
        after_damage_value   float  required (≥ 0)  — property value after damage event
        cost_to_cure         float  optional (≥ 0)  — estimated repair / remediation cost
        severance_damage     float  optional (≥ 0)  — damage to remainder parcel (partial take)

    Outputs (EngineResult):
        value      = total_compensation (Decimal, EGP)
        confidence = high | medium | low | insufficient
        metadata   = {before_damage_value, after_damage_value,
                      diminution_in_value, cost_to_cure,
                      cost_to_cure_viable, severance_damage,
                      total_compensation}
    """

    name    = "litigation_compensation"
    version = "1.0.0"

    def validate(self, inputs: dict) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        bdv = inputs.get("before_damage_value")
        if bdv is None:
            issues.append(ValidationIssue(
                severity="error",
                code="MISSING_BEFORE_DAMAGE_VALUE",
                message="before_damage_value is required",
            ))
        elif float(bdv) <= 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_BEFORE_DAMAGE_VALUE",
                message=f"before_damage_value must be > 0; got {bdv}",
            ))

        adv = inputs.get("after_damage_value")
        if adv is None:
            issues.append(ValidationIssue(
                severity="error",
                code="MISSING_AFTER_DAMAGE_VALUE",
                message="after_damage_value is required (use 0 for total loss)",
            ))
        elif float(adv) < 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_AFTER_DAMAGE_VALUE",
                message=f"after_damage_value must be ≥ 0; got {adv}",
            ))

        if bdv is not None and adv is not None:
            if float(adv) > float(bdv):
                issues.append(ValidationIssue(
                    severity="error",
                    code="AFTER_EXCEEDS_BEFORE",
                    message=(
                        f"after_damage_value {adv} > before_damage_value {bdv} — "
                        "property cannot appreciate due to a damage event; verify inputs"
                    ),
                ))

        ctc = inputs.get("cost_to_cure")
        if ctc is not None and float(ctc) < 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_COST_TO_CURE",
                message=f"cost_to_cure must be ≥ 0; got {ctc}",
            ))

        sev = inputs.get("severance_damage")
        if sev is not None and float(sev) < 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_SEVERANCE_DAMAGE",
                message=f"severance_damage must be ≥ 0; got {sev}",
            ))

        if ctc is None and sev is None:
            issues.append(ValidationIssue(
                severity="warning",
                code="MISSING_OPTIONAL_COMPONENTS",
                message=(
                    "cost_to_cure and severance_damage not supplied — "
                    "compensation based on before/after diminution only; "
                    "consider cure cost and severance for complete assessment"
                ),
            ))

        return issues

    def calculate(self, inputs: dict) -> EngineResult:
        """Before/after → diminution → cost-to-cure → severance → total compensation."""
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

        bdv = float(inputs["before_damage_value"])
        adv = float(inputs["after_damage_value"])
        ctc = inputs.get("cost_to_cure")
        sev = inputs.get("severance_damage")

        audit_trail: list[AuditEntry] = []

        # ── Step 1: Diminution in value (Before-and-After) ───────────
        diminution = bdv - adv
        if diminution == 0:
            issues.append(ValidationIssue(
                severity="warning",
                code="ZERO_DIMINUTION",
                message=(
                    "before_damage_value equals after_damage_value — "
                    "no economic loss detected; verify inputs"
                ),
            ))
        audit_trail.append(AuditEntry(
            step_name="Compute diminution in value (Before-and-After method)",
            inputs={
                "before_damage_value": round(bdv, 2),
                "after_damage_value":  round(adv, 2),
            },
            outputs={"diminution_in_value": round(diminution, 2)},
            formula="diminution_in_value = before_damage_value − after_damage_value",
            references=["RICS GN 3: Before-and-After Method",
                        "Uniform Standards of Professional Appraisal Practice (USPAP)",
                        "IVS 105: Valuation Approaches and Methods"],
        ))

        # ── Step 2: Cost-to-cure analysis (conditional) ──────────────
        cost_to_cure_viable: bool | None = None
        if ctc is not None:
            ctc_f = float(ctc)
            cost_to_cure_viable = ctc_f <= diminution
            cure_pct = (ctc_f / diminution) if diminution > 0 else None
            if cure_pct is not None and cure_pct > _CURE_RATIO_WARN:
                issues.append(ValidationIssue(
                    severity="warning",
                    code="HIGH_CURE_COST_RATIO",
                    message=(
                        f"cost_to_cure {ctc_f:,.0f} EGP is {cure_pct:.0%} of diminution — "
                        "economically marginal to cure; consider as-damaged valuation"
                    ),
                ))
            audit_trail.append(AuditEntry(
                step_name="Cost-to-cure viability analysis",
                inputs={
                    "cost_to_cure":       round(ctc_f, 2),
                    "diminution_in_value": round(diminution, 2),
                },
                outputs={
                    "cost_to_cure_viable": cost_to_cure_viable,
                    "cure_pct_of_diminution": round(cure_pct, 4) if cure_pct is not None else None,
                },
                formula=(
                    "economically viable if cost_to_cure ≤ diminution_in_value"
                ),
                references=["RICS: Cost-to-Cure Approach",
                            "Eminent Domain: Lesser of Cure vs Diminution"],
            ))

        # ── Step 3: Severance damage (conditional) ───────────────────
        sev_f: float = float(sev) if sev is not None else 0.0
        if sev is not None:
            audit_trail.append(AuditEntry(
                step_name="Severance damage to remainder parcel",
                inputs={
                    "severance_damage":    round(sev_f, 2),
                    "diminution_in_value": round(diminution, 2),
                },
                outputs={"severance_included": True},
                formula=(
                    "total_compensation = diminution_in_value + severance_damage"
                ),
                references=["RICS: Severance Compensation",
                            "Compulsory Purchase Order (CPO): Severance and Injurious Affection"],
            ))

        # ── Step 4: Total compensation ────────────────────────────────
        total_compensation = diminution + sev_f
        audit_trail.append(AuditEntry(
            step_name="Compute total compensation",
            inputs={
                "diminution_in_value": round(diminution, 2),
                "severance_damage":    round(sev_f, 2),
            },
            outputs={"total_compensation": round(total_compensation, 2)},
            formula="total_compensation = diminution_in_value + severance_damage",
            references=["RICS GN 3: Total Compensation",
                        "IVS 104: Bases Other Than Market Value"],
        ))

        # ── Confidence ────────────────────────────────────────────────
        has_ctc = ctc is not None
        has_sev = sev is not None
        if has_ctc and has_sev:
            confidence = "high"
        elif has_ctc or has_sev:
            confidence = "medium"
        else:
            confidence = "low"

        metadata: dict = {
            "before_damage_value":   round(bdv, 2),
            "after_damage_value":    round(adv, 2),
            "diminution_in_value":   round(diminution, 2),
            "cost_to_cure":          round(float(ctc), 2) if ctc is not None else None,
            "cost_to_cure_viable":   cost_to_cure_viable,
            "severance_damage":      round(sev_f, 2) if sev is not None else None,
            "total_compensation":    round(total_compensation, 2),
        }

        return EngineResult(
            engine_name=self.name,
            value=Decimal(str(round(total_compensation, 2))),
            confidence=confidence,
            audit_trail=audit_trail,
            issues=issues,
            metadata=metadata,
        )
