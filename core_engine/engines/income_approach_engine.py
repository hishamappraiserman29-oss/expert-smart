"""
Income Approach Engine — Absolute Expense Input (IVS 105 / EGVS 5).

Extends beyond IncomeEngine (income.py, which takes an opex_ratio fraction) by
accepting operating_expenses as an absolute EGP amount and computing expense_ratio
as a derived output.  Also supports expense derivation from operating_expense_ratio
when the absolute amount is not known.

Formula:
    EGI            = gross_income × (1 − vacancy_rate)
    operating_exp  = (caller-supplied absolute)  OR  EGI × operating_expense_ratio
    NOI            = EGI − operating_expenses
    income_value   = NOI / cap_rate
    expense_ratio  = operating_expenses / EGI     (derived output)

Cap rate = 0 is explicitly caught as an error — no division by zero.
"""

from decimal import Decimal

from .base import (
    EngineResult, AuditEntry, ValidationIssue, ValuationEngine,
)

_CAP_RATE_MIN: float = 0.04   # 4%  — Egyptian market lower bound
_CAP_RATE_MAX: float = 0.20   # 20% — Egyptian market upper bound
_HIGH_VACANCY_WARN: float = 0.50   # > 50% vacancy warrants explicit review


class IncomeApproachEngine(ValuationEngine):
    """
    Income Approach (Absolute Expense) engine — Phase 16.2 v1.

    Distinct from IncomeEngine (income.py):
    • Accepts operating_expenses as absolute EGP (not a ratio)
    • Derives expense_ratio as an output metric
    • Supports operating_expense_ratio as a fallback derivation path
    • Explicit cap_rate = 0 guard (no ZeroDivisionError)

    Inputs (dict keys):
        gross_income                float  required (annual EGP, > 0)
        vacancy_rate                float  optional, fraction [0, 1], default 0
        operating_expenses          float  optional — absolute EGP amount (≥ 0)
        operating_expense_ratio     float  optional — fraction of EGI; used to derive
                                           operating_expenses when not supplied directly
        cap_rate                    float  required (> 0)

    Outputs (EngineResult):
        value      = income_value (Decimal, EGP)
        confidence = high | medium | low | insufficient
        metadata   = {gross_income, vacancy_rate, effective_gross_income,
                      operating_expenses, expense_ratio, noi,
                      cap_rate, income_value, expense_source}
    """

    name    = "income_approach"
    version = "1.0.0"

    def __init__(self) -> None:
        self.cap_rate_min: float = _CAP_RATE_MIN
        self.cap_rate_max: float = _CAP_RATE_MAX

    # ------------------------------------------------------------------
    # Abstract method implementations
    # ------------------------------------------------------------------

    def validate(self, inputs: dict) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        gross = inputs.get("gross_income", 0) or 0
        if float(gross) <= 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_GROSS_INCOME",
                message=f"gross_income must be > 0; got {gross}",
            ))

        vacancy = inputs.get("vacancy_rate", 0) or 0
        if not (0.0 <= float(vacancy) <= 1.0):
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_VACANCY_RATE",
                message=f"vacancy_rate must be in [0, 1]; got {vacancy}",
            ))
        elif float(vacancy) > _HIGH_VACANCY_WARN:
            issues.append(ValidationIssue(
                severity="warning",
                code="HIGH_VACANCY_RATE",
                message=(
                    f"vacancy_rate {float(vacancy):.0%} exceeds {_HIGH_VACANCY_WARN:.0%} "
                    "— income approach reliability is reduced"
                ),
            ))

        cap_rate = inputs.get("cap_rate")
        if cap_rate is None:
            issues.append(ValidationIssue(
                severity="error",
                code="MISSING_CAP_RATE",
                message="cap_rate is required; income_value = NOI / cap_rate",
            ))
        elif float(cap_rate) <= 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_CAP_RATE_ZERO",
                message=(
                    f"cap_rate must be > 0 to avoid division by zero; got {cap_rate}"
                ),
            ))
        elif not (self.cap_rate_min <= float(cap_rate) <= self.cap_rate_max):
            issues.append(ValidationIssue(
                severity="warning",
                code="CAP_RATE_OUT_OF_RANGE",
                message=(
                    f"cap_rate {float(cap_rate):.1%} outside typical Egyptian market range "
                    f"{self.cap_rate_min:.0%}–{self.cap_rate_max:.0%}"
                ),
            ))

        op_exp       = inputs.get("operating_expenses")
        exp_ratio    = inputs.get("operating_expense_ratio")
        if op_exp is None and exp_ratio is None:
            issues.append(ValidationIssue(
                severity="warning",
                code="MISSING_OPERATING_EXPENSES",
                message=(
                    "Neither operating_expenses nor operating_expense_ratio supplied — "
                    "NOI will equal EGI (zero expenses assumed)"
                ),
            ))
        if op_exp is not None and float(op_exp) < 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_OPERATING_EXPENSES",
                message=f"operating_expenses must be ≥ 0; got {op_exp}",
            ))
        if exp_ratio is not None:
            if not (0.0 <= float(exp_ratio) < 1.0):
                issues.append(ValidationIssue(
                    severity="error",
                    code="INVALID_EXPENSE_RATIO",
                    message=f"operating_expense_ratio must be in [0, 1); got {exp_ratio}",
                ))

        return issues

    def calculate(self, inputs: dict) -> EngineResult:
        """EGI → expenses → NOI → capitalise → EngineResult."""
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

        gross    = float(inputs["gross_income"])
        vacancy  = float(inputs.get("vacancy_rate", 0) or 0)
        cap_rate = float(inputs["cap_rate"])

        audit_trail: list[AuditEntry] = []

        # ── Step 1: Effective Gross Income (EGI) ─────────────────────
        egi          = gross * (1.0 - vacancy)
        vacancy_loss = gross - egi
        audit_trail.append(AuditEntry(
            step_name="Calculate Effective Gross Income (EGI)",
            inputs={"gross_income": gross, "vacancy_rate": vacancy},
            outputs={"vacancy_loss": round(vacancy_loss, 2), "egi": round(egi, 2)},
            formula="EGI = gross_income × (1 − vacancy_rate)",
            references=["EGVS_5.1: Effective Gross Income", "IVS 105: Income Approach"],
        ))

        # ── Step 2: Operating expenses ────────────────────────────────
        op_exp_input  = inputs.get("operating_expenses")
        exp_ratio_in  = inputs.get("operating_expense_ratio")
        if op_exp_input is not None:
            op_exp       = float(op_exp_input)
            exp_source   = "caller-supplied operating_expenses"
        elif exp_ratio_in is not None:
            op_exp       = egi * float(exp_ratio_in)
            exp_source   = f"EGI × operating_expense_ratio ({float(exp_ratio_in):.2%})"
        else:
            op_exp       = 0.0
            exp_source   = "zero (no expenses supplied)"

        expense_ratio = (op_exp / egi) if egi > 0 else 0.0

        audit_trail.append(AuditEntry(
            step_name="Determine operating expenses",
            inputs={
                "operating_expenses_input":     op_exp_input,
                "operating_expense_ratio_input": exp_ratio_in,
                "egi": round(egi, 2),
            },
            outputs={
                "operating_expenses": round(op_exp, 2),
                "expense_ratio":      round(expense_ratio, 4),
                "source": exp_source,
            },
            formula="op_exp = (absolute input) OR (EGI × expense_ratio)",
            references=["EGVS_5.2: Operating Expenses", "IVS 105: NOI Derivation"],
        ))

        # ── Step 3: Net Operating Income (NOI) ───────────────────────
        noi = egi - op_exp
        audit_trail.append(AuditEntry(
            step_name="Calculate Net Operating Income (NOI)",
            inputs={"egi": round(egi, 2), "operating_expenses": round(op_exp, 2)},
            outputs={"noi": round(noi, 2)},
            formula="NOI = EGI − operating_expenses",
            references=["EGVS_5.3: Net Operating Income"],
        ))

        # Guard: non-positive NOI
        if noi <= 0:
            audit_trail.append(AuditEntry(
                step_name="Apply capitalization rate",
                inputs={"noi": round(noi, 2), "cap_rate": cap_rate},
                outputs={"income_value": None},
                formula="income_value = NOI / cap_rate",
                references=["EGVS_5.4: Direct Capitalization"],
            ))
            return EngineResult(
                engine_name=self.name,
                value=None,
                confidence="insufficient",
                audit_trail=audit_trail,
                issues=issues + [ValidationIssue(
                    severity="error",
                    code="NON_POSITIVE_NOI",
                    message=(
                        f"NOI = {noi:.2f} EGP ≤ 0 — income approach not applicable"
                    ),
                )],
                metadata={
                    "gross_income":            gross,
                    "vacancy_rate":            vacancy,
                    "effective_gross_income":  round(egi, 2),
                    "operating_expenses":      round(op_exp, 2),
                    "expense_ratio":           round(expense_ratio, 4),
                    "expense_source":          exp_source,
                    "noi":                     round(noi, 2),
                    "cap_rate":                cap_rate,
                    "income_value":            None,
                },
            )

        # ── Step 4: Capitalise NOI ────────────────────────────────────
        income_value = noi / cap_rate   # cap_rate > 0 guaranteed by validate()
        audit_trail.append(AuditEntry(
            step_name="Apply capitalization rate — income value",
            inputs={"noi": round(noi, 2), "cap_rate": cap_rate},
            outputs={"income_value": round(income_value, 2)},
            formula="income_value = NOI / cap_rate",
            references=["EGVS_5.4: Direct Capitalization", "IVS 105: Income Approach Final Value"],
        ))

        # ── Confidence ────────────────────────────────────────────────
        cap_in_range = self.cap_rate_min <= cap_rate <= self.cap_rate_max
        if cap_in_range and vacancy <= 0.30:
            confidence = "high"
        elif cap_in_range:
            confidence = "medium"
        else:
            confidence = "low"

        metadata: dict = {
            "gross_income":            gross,
            "vacancy_rate":            vacancy,
            "vacancy_loss":            round(vacancy_loss, 2),
            "effective_gross_income":  round(egi, 2),
            "operating_expenses":      round(op_exp, 2),
            "expense_ratio":           round(expense_ratio, 4),
            "expense_source":          exp_source,
            "noi":                     round(noi, 2),
            "cap_rate":                cap_rate,
            "income_value":            round(income_value, 2),
        }

        return EngineResult(
            engine_name=self.name,
            value=Decimal(str(round(income_value, 2))),
            confidence=confidence,
            audit_trail=audit_trail,
            issues=issues,
            metadata=metadata,
        )
