from decimal import Decimal
from typing import Optional

from .base import (
    EngineResult, AuditEntry, ValidationIssue, ValuationEngine,
)


class IncomeEngine(ValuationEngine):
    """
    Income Approach (Direct Capitalization) engine — Phase 4 v1.

    Formula:
        EGI  = Gross_Income × (1 − Vacancy_Rate)
        NOI  = EGI × (1 − OpEx_Ratio)
        Value = NOI / Cap_Rate
    """

    name    = "income"
    version = "1.0.0"

    def __init__(self):
        self.cap_rate_warning_min = 0.04   # 4%  — Egyptian market lower bound
        self.cap_rate_warning_max = 0.20   # 20% — Egyptian market upper bound
        self.default_vacancy_rate = 0.15
        self.default_opex_ratio   = 0.35

    # ──────────────────────────────────────────────────────────────────
    # Abstract method implementations
    # ──────────────────────────────────────────────────────────────────

    def validate(self, inputs: dict) -> list[ValidationIssue]:
        """Check inputs before calculation. Returns list of issues (empty = OK)."""
        issues: list[ValidationIssue] = []

        gross = inputs.get("gross_income_annual_egp", 0) or 0
        if gross <= 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_GROSS_INCOME",
                message=f"gross_income_annual_egp must be > 0; got {gross}",
            ))

        vacancy = inputs.get("vacancy_rate")
        if vacancy is not None:
            if vacancy < 0.0 or vacancy > 0.5:
                issues.append(ValidationIssue(
                    severity="error",
                    code="INVALID_VACANCY_RATE",
                    message=f"vacancy_rate must be in [0.0, 0.5]; got {vacancy}",
                ))

        opex = inputs.get("operating_expenses_ratio")
        if opex is not None:
            if opex < 0.0 or opex >= 1.0:
                issues.append(ValidationIssue(
                    severity="error",
                    code="INVALID_OPEX_RATIO",
                    message=f"operating_expenses_ratio must be in [0.0, 1.0); got {opex}",
                ))
            elif opex > 0.7:
                # High but not impossible — flag as warning, calculation continues
                issues.append(ValidationIssue(
                    severity="warning",
                    code="HIGH_OPEX_RATIO",
                    message=f"operating_expenses_ratio {opex:.0%} exceeds typical 70% ceiling",
                ))

        cap_rate = inputs.get("cap_rate")
        if cap_rate is None or cap_rate <= 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_CAP_RATE",
                message=f"cap_rate must be > 0; got {cap_rate}",
            ))
        elif not (self.cap_rate_warning_min <= cap_rate <= self.cap_rate_warning_max):
            issues.append(ValidationIssue(
                severity="warning",
                code="CAP_RATE_OUT_OF_RANGE",
                message=(
                    f"Cap rate {cap_rate:.1%} outside typical Egyptian range "
                    f"{self.cap_rate_warning_min:.0%}–{self.cap_rate_warning_max:.0%}"
                ),
            ))

        source    = inputs.get("cap_rate_source")
        reference = inputs.get("cap_rate_source_reference")
        if source == "expert" and not reference:
            issues.append(ValidationIssue(
                severity="warning",
                code="EXPERT_CAP_RATE_NO_SOURCE",
                message="Expert-judgment cap rate should have a documented reference",
            ))

        return issues

    def calculate(self, inputs: dict) -> EngineResult:
        """EGI → OpEx → NOI → Capitalise → EngineResult."""
        issues = self.validate(inputs)
        errors = [i for i in issues if i.severity == "error"]

        if errors:
            return EngineResult(
                engine_name=self.name,
                value=None,
                confidence="insufficient",
                audit_trail=[],
                issues=issues,
                metadata={},
            )

        gross    = float(inputs["gross_income_annual_egp"])
        vacancy  = float(inputs.get("vacancy_rate",              self.default_vacancy_rate))
        opex_r   = float(inputs.get("operating_expenses_ratio",  self.default_opex_ratio))
        cap_rate = float(inputs["cap_rate"])
        source   = inputs.get("cap_rate_source", "")
        reference = inputs.get("cap_rate_source_reference", "")

        audit_trail: list[AuditEntry] = []

        # ── Step 1: Extract parameters ────────────────────────────────
        audit_trail.append(AuditEntry(
            step_name="Extract income parameters",
            inputs={
                "gross_income_annual_egp": gross,
                "vacancy_rate": vacancy,
                "operating_expenses_ratio": opex_r,
                "cap_rate": cap_rate,
                "cap_rate_source": source,
            },
            outputs={},
            formula="—",
            references=["EGVS_5.1: Income Approach", "Phase 4 Income Engine v1.0"],
        ))

        # ── Step 2: EGI (Effective Gross Income) ─────────────────────
        egi, opex, noi = self._calculate_noi(gross, vacancy, opex_r)
        vacancy_loss = gross - egi

        audit_trail.append(AuditEntry(
            step_name="Calculate effective gross income (EGI)",
            inputs={"gross_income": gross, "vacancy_rate": vacancy},
            outputs={"vacancy_loss": round(vacancy_loss, 2), "egi": round(egi, 2)},
            formula="EGI = gross_income × (1 − vacancy_rate)",
            references=["EGVS_5.2: Effective Gross Income"],
        ))

        # ── Step 3: Operating Expenses ────────────────────────────────
        audit_trail.append(AuditEntry(
            step_name="Calculate operating expenses",
            inputs={"egi": round(egi, 2), "opex_ratio": opex_r},
            outputs={"operating_expenses": round(opex, 2)},
            formula="OpEx = EGI × operating_expenses_ratio",
            references=["EGVS_5.3: Operating Expenses"],
        ))

        # ── Step 4: NOI ───────────────────────────────────────────────
        audit_trail.append(AuditEntry(
            step_name="Calculate NOI (Net Operating Income)",
            inputs={"egi": round(egi, 2), "operating_expenses": round(opex, 2)},
            outputs={"noi": round(noi, 2)},
            formula="NOI = EGI − OpEx",
            references=["EGVS_5.4: Net Operating Income"],
        ))

        # ── Step 5: Capitalise ────────────────────────────────────────
        if noi <= 0:
            # Unprofitable — return result with no value
            audit_trail.append(AuditEntry(
                step_name="Apply capitalization rate",
                inputs={"noi": round(noi, 2), "cap_rate": cap_rate},
                outputs={"value": None},
                formula="Value = NOI / cap_rate",
                references=["EGVS_5.5: Direct Capitalization"],
            ))
            return EngineResult(
                engine_name=self.name,
                value=None,
                confidence="insufficient",
                audit_trail=audit_trail,
                issues=issues + [ValidationIssue(
                    severity="error",
                    code="NON_POSITIVE_NOI",
                    message=f"NOI = {noi:.2f} EGP — property unprofitable; income approach not applicable",
                )],
                metadata={
                    "gross_income": gross, "vacancy_loss": round(vacancy_loss, 2),
                    "effective_gross_income": round(egi, 2),
                    "operating_expenses": round(opex, 2), "noi": round(noi, 2),
                    "cap_rate": cap_rate, "cap_rate_source": source,
                    "cap_rate_source_reference": reference,
                },
            )

        value = noi / cap_rate
        audit_trail.append(AuditEntry(
            step_name="Apply capitalization rate",
            inputs={"noi": round(noi, 2), "cap_rate": cap_rate, "cap_rate_source": source},
            outputs={"value": round(value, 2)},
            formula="Value = NOI / cap_rate",
            references=["EGVS_5.5: Direct Capitalization", "Phase 4 Income Engine v1.0"],
        ))

        # ── Step 6: Confidence ────────────────────────────────────────
        cap_in_range = self.cap_rate_warning_min <= cap_rate <= self.cap_rate_warning_max

        if vacancy > 0.3:
            confidence = "low"
        elif cap_in_range:
            confidence = "high"
        elif source == "expert":
            confidence = "medium"
        elif source in ("published", "market"):
            confidence = "high"
        else:
            confidence = "medium"

        metadata = {
            "gross_income":              gross,
            "vacancy_loss":              round(vacancy_loss, 2),
            "effective_gross_income":    round(egi, 2),
            "operating_expenses":        round(opex, 2),
            "noi":                       round(noi, 2),
            "cap_rate":                  cap_rate,
            "cap_rate_source":           source,
            "cap_rate_source_reference": reference,
        }

        return EngineResult(
            engine_name=self.name,
            value=Decimal(str(round(value, 2))),
            confidence=confidence,
            audit_trail=audit_trail,
            issues=issues,
            metadata=metadata,
        )

    # ──────────────────────────────────────────────────────────────────
    # Helper
    # ──────────────────────────────────────────────────────────────────

    def _calculate_noi(
        self,
        gross_income: float,
        vacancy_rate: float,
        opex_ratio: float,
    ) -> tuple[float, float, float]:
        """Return (EGI, OpEx, NOI)."""
        egi  = gross_income * (1.0 - vacancy_rate)
        opex = egi * opex_ratio
        noi  = egi - opex
        return egi, opex, noi
