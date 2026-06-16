"""
Rights / Partial Interests Valuation Engine (IVS 105 / IVSC Guidance).

Handles minority interests, usufruct rights, and partial ownership positions
where control and marketability discounts reduce value below the pro-rata share.

Formulas:
    minority_interest_undiscounted = full_property_value × ownership_percentage

    Sequential discount application (NEVER additive):
        value_after_dloc   = minority_interest_undiscounted × (1 − DLOC)
        minority_interest_value = value_after_dloc × (1 − DLOM)

    Usufruct / income-based PV (if annual_noi + discount_rate + remaining_term_years):
        usufruct_value = annual_noi × [1 − (1 + r)^(−n)] / r

Safety:
    DLOC and DLOM are applied SEQUENTIALLY, NOT additively.
    Combined effective discount = 1 − (1−DLOC)×(1−DLOM), not DLOC+DLOM.
    Documented in calculation_notes within metadata.

    This engine is STANDALONE — partial-interest output does NOT automatically
    replace market_value in any report or /api/valuation response.
"""

from decimal import Decimal
from typing import Optional

from .base import (
    EngineResult, AuditEntry, ValidationIssue, ValuationEngine,
)

_MAX_OWNERSHIP:  float = 1.0
_MAX_DLOC:       float = 0.80   # DLOC > 80% uncommon — warn
_MAX_DLOM:       float = 0.50   # DLOM > 50% uncommon — warn
_MIN_TERM_YEARS: float = 0.0


class RightsEngine(ValuationEngine):
    """
    Rights / Partial Interests engine — Phase 16.6 v1.

    Inputs (dict keys):
        full_property_value   float  required (> 0)   — 100% fee-simple market value
        ownership_percentage  float  required (0–1]   — fractional interest (e.g. 0.25)
        dloc                  float  optional [0–1)   — Discount for Lack of Control
        dlom                  float  optional [0–1)   — Discount for Lack of Marketability
        remaining_term_years  float  optional (> 0)   — usufruct / lease term in years
        annual_noi            float  optional (> 0)   — annual income for usufruct PV
        discount_rate         float  optional (> 0)   — discount rate for usufruct PV

    Outputs (EngineResult):
        value      = minority_interest_value (Decimal, EGP) — post-DLOC/DLOM
        confidence = high | medium | low | insufficient
        metadata   = {full_property_value, ownership_percentage,
                      minority_interest_undiscounted, value_after_dloc,
                      minority_interest_value, dloc, dlom,
                      usufruct_value, calculation_notes}
    """

    name    = "rights"
    version = "1.0.0"

    def validate(self, inputs: dict) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        fpv = inputs.get("full_property_value")
        if fpv is None:
            issues.append(ValidationIssue(
                severity="error",
                code="MISSING_FULL_PROPERTY_VALUE",
                message="full_property_value is required",
            ))
        elif float(fpv) <= 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_FULL_PROPERTY_VALUE",
                message=f"full_property_value must be > 0; got {fpv}",
            ))

        op = inputs.get("ownership_percentage")
        if op is None:
            issues.append(ValidationIssue(
                severity="error",
                code="MISSING_OWNERSHIP_PERCENTAGE",
                message="ownership_percentage is required (e.g. 0.25 for 25%)",
            ))
        else:
            op_f = float(op)
            if not (0 < op_f <= _MAX_OWNERSHIP):
                issues.append(ValidationIssue(
                    severity="error",
                    code="INVALID_OWNERSHIP_PERCENTAGE",
                    message=(
                        f"ownership_percentage must be in (0, 1]; got {op} — "
                        "use 1.0 for 100% fee-simple interest"
                    ),
                ))

        dloc = inputs.get("dloc")
        if dloc is not None:
            d = float(dloc)
            if not (0 <= d < 1):
                issues.append(ValidationIssue(
                    severity="error",
                    code="INVALID_DLOC",
                    message=f"dloc must be in [0, 1); got {dloc}",
                ))
            elif d > _MAX_DLOC:
                issues.append(ValidationIssue(
                    severity="warning",
                    code="HIGH_DLOC",
                    message=(
                        f"dloc {d:.0%} exceeds typical maximum of {_MAX_DLOC:.0%} — "
                        "verify with market evidence"
                    ),
                ))

        dlom = inputs.get("dlom")
        if dlom is not None:
            m = float(dlom)
            if not (0 <= m < 1):
                issues.append(ValidationIssue(
                    severity="error",
                    code="INVALID_DLOM",
                    message=f"dlom must be in [0, 1); got {dlom}",
                ))
            elif m > _MAX_DLOM:
                issues.append(ValidationIssue(
                    severity="warning",
                    code="HIGH_DLOM",
                    message=(
                        f"dlom {m:.0%} exceeds typical maximum of {_MAX_DLOM:.0%} — "
                        "verify with restricted-stock studies"
                    ),
                ))

        rt = inputs.get("remaining_term_years")
        noi = inputs.get("annual_noi")
        dr  = inputs.get("discount_rate")

        if rt is not None and float(rt) <= _MIN_TERM_YEARS:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_REMAINING_TERM",
                message=f"remaining_term_years must be > 0; got {rt}",
            ))

        if noi is not None and float(noi) <= 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_ANNUAL_NOI",
                message=f"annual_noi must be > 0; got {noi}",
            ))

        if dr is not None and float(dr) <= 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_DISCOUNT_RATE",
                message=f"discount_rate must be > 0; got {dr}",
            ))

        usufruct_inputs_count = sum(1 for x in (rt, noi, dr) if x is not None)
        if 0 < usufruct_inputs_count < 3:
            issues.append(ValidationIssue(
                severity="warning",
                code="INCOMPLETE_USUFRUCT_INPUTS",
                message=(
                    "Usufruct PV requires all three: remaining_term_years, "
                    "annual_noi, and discount_rate — usufruct_value will not be computed"
                ),
            ))

        return issues

    def calculate(self, inputs: dict) -> EngineResult:
        """Pro-rata share → DLOC → DLOM (sequential) → usufruct PV → EngineResult."""
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

        fpv  = float(inputs["full_property_value"])
        op   = float(inputs["ownership_percentage"])
        dloc = inputs.get("dloc")
        dlom = inputs.get("dlom")
        rt   = inputs.get("remaining_term_years")
        noi  = inputs.get("annual_noi")
        dr   = inputs.get("discount_rate")

        audit_trail: list[AuditEntry] = []

        # ── Step 1: Pro-rata minority interest ────────────────────────
        mi_undiscounted = fpv * op
        audit_trail.append(AuditEntry(
            step_name="Compute pro-rata minority interest",
            inputs={"full_property_value": round(fpv, 2), "ownership_percentage": op},
            outputs={"minority_interest_undiscounted": round(mi_undiscounted, 2)},
            formula="minority_interest_undiscounted = full_property_value × ownership_percentage",
            references=["IVS 105 para. 50: Partial Interests",
                        "IVSC Guidance Note GN 2: Minority Interests"],
        ))

        # ── Step 2: Apply DLOC (Discount for Lack of Control) ─────────
        dloc_f: float = float(dloc) if dloc is not None else 0.0
        value_after_dloc: float = mi_undiscounted * (1.0 - dloc_f)
        if dloc is not None:
            audit_trail.append(AuditEntry(
                step_name="Apply DLOC — Discount for Lack of Control",
                inputs={
                    "minority_interest_undiscounted": round(mi_undiscounted, 2),
                    "dloc": dloc_f,
                },
                outputs={"value_after_dloc": round(value_after_dloc, 2)},
                formula="value_after_dloc = minority_interest_undiscounted × (1 − DLOC)",
                references=["IVS 105: Control Premium / Control Discount",
                            "BVR: Control Premium Studies"],
            ))
        else:
            value_after_dloc = mi_undiscounted

        # ── Step 3: Apply DLOM sequentially (Discount for Lack of Marketability) ──
        dlom_f: float = float(dlom) if dlom is not None else 0.0
        minority_interest_value: float = value_after_dloc * (1.0 - dlom_f)
        if dlom is not None:
            audit_trail.append(AuditEntry(
                step_name="Apply DLOM — Discount for Lack of Marketability (sequential)",
                inputs={
                    "value_after_dloc": round(value_after_dloc, 2),
                    "dlom": dlom_f,
                },
                outputs={"minority_interest_value": round(minority_interest_value, 2)},
                formula=(
                    "minority_interest_value = value_after_dloc × (1 − DLOM)\n"
                    "CRITICAL: DLOC and DLOM are applied SEQUENTIALLY, NOT additively.\n"
                    "Combined effective discount = 1 − (1−DLOC)×(1−DLOM)"
                ),
                references=["IVS 105: Marketability Discount",
                            "Pratt et al.: Restricted Stock Studies",
                            "Mandelbaum v. Commissioner: DLOM factors"],
            ))
        else:
            minority_interest_value = value_after_dloc

        # ── Step 4: Usufruct PV (conditional — all three inputs required) ──
        usufruct_value: Optional[float] = None
        if rt is not None and noi is not None and dr is not None:
            n   = float(rt)
            r   = float(dr)
            noi_f = float(noi)
            # PV of level annuity: NOI × [1 − (1+r)^(−n)] / r
            pv_factor   = (1.0 - (1.0 + r) ** (-n)) / r
            usufruct_value = noi_f * pv_factor
            audit_trail.append(AuditEntry(
                step_name="Usufruct value — PV of income stream",
                inputs={
                    "annual_noi":          round(noi_f, 2),
                    "discount_rate":       r,
                    "remaining_term_years": n,
                },
                outputs={
                    "pv_factor":      round(pv_factor, 6),
                    "usufruct_value": round(usufruct_value, 2),
                },
                formula=(
                    "usufruct_value = annual_noi × [1 − (1+r)^(−n)] / r\n"
                    "(present value of level annuity)"
                ),
                references=["IVS 230: Income Approach",
                            "RICS VIP 1: Leasehold Valuation"],
            ))

        # ── Confidence ────────────────────────────────────────────────
        has_dloc = dloc is not None
        has_dlom = dlom is not None
        if has_dloc and has_dlom:
            confidence = "high"
        elif has_dloc or has_dlom:
            confidence = "medium"
        else:
            confidence = "low"

        # Effective combined discount for disclosure
        effective_combined_discount = 1.0 - (1.0 - dloc_f) * (1.0 - dlom_f)
        calculation_notes = (
            f"DLOC={dloc_f:.2%} and DLOM={dlom_f:.2%} applied SEQUENTIALLY "
            f"(not additively). Combined effective discount = "
            f"{effective_combined_discount:.2%} "
            f"[= 1 − (1−{dloc_f:.2%})×(1−{dlom_f:.2%})]. "
            "Additive approach would overstate the combined discount."
        )

        metadata: dict = {
            "full_property_value":           round(fpv, 2),
            "ownership_percentage":          op,
            "minority_interest_undiscounted": round(mi_undiscounted, 2),
            "value_after_dloc":              round(value_after_dloc, 2),
            "minority_interest_value":       round(minority_interest_value, 2),
            "dloc":                          dloc_f,
            "dlom":                          dlom_f,
            "effective_combined_discount":   round(effective_combined_discount, 4),
            "usufruct_value":                round(usufruct_value, 2) if usufruct_value is not None else None,
            "remaining_term_years":          float(rt) if rt is not None else None,
            "annual_noi":                    float(noi) if noi is not None else None,
            "discount_rate":                 float(dr) if dr is not None else None,
            "calculation_notes":             calculation_notes,
        }

        return EngineResult(
            engine_name=self.name,
            value=Decimal(str(round(minority_interest_value, 2))),
            confidence=confidence,
            audit_trail=audit_trail,
            issues=issues,
            metadata=metadata,
        )
