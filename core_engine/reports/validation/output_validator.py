"""
output_validator.py — Output/result validation for EXPERT_SMART reports.

Validates pre-computed valuation results for logical consistency before
PDF/Excel rendering.  All 9 rules check that outputs are present, positive,
finite, and internally consistent.

Raises nothing — always returns a ValidationResult.
"""

from __future__ import annotations

from typing import Any, Mapping

from .result import Severity, ValidationResult
from .rules import (
    check_not_nan_inf,
    check_positive,
    check_weights_sum,
    require,
)


# ── Public API ────────────────────────────────────────────────────────────────

def validate_outputs(
    data: Mapping[str, Any],
    *,
    profile_key: str = "legacy",
) -> ValidationResult:
    """
    Validate pre-computed valuation outputs in *data*.

    Args:
        data: Top-level report data dict.  Reads from:
              valuation_results, cost_approach, income_approach, reconciliation.
        profile_key: Unused at this stage; reserved for future profile-specific
                     output rules.

    Returns:
        ValidationResult — inspect .is_valid and .errors/.warnings/.infos.
        Never raises.
    """
    issues: list[Any] = []

    # ── 1. Final market value ─────────────────────────────────────────────────
    vr = data.get("valuation_results") or {}
    issues.append(require(
        vr, "market_value",
        code="MARKET_VALUE_MISSING",
        message_ar="القيمة السوقية النهائية مطلوبة في نتائج التقييم",
        message_en="Final market value is required in valuation_results",
    ))
    issues.append(check_positive(
        vr, "market_value",
        code="MARKET_VALUE_POSITIVE",
        message_ar="القيمة السوقية النهائية يجب أن تكون أكبر من صفر",
        message_en="Final market value must be greater than zero",
    ))
    issues.append(check_not_nan_inf(
        vr, "market_value",
        code="MARKET_VALUE_NAN_INF",
        message_ar="القيمة السوقية النهائية تحتوي على قيمة غير صالحة (NaN أو ∞)",
        message_en="Final market value contains an invalid value (NaN or Infinity)",
    ))

    # ── 2. Price per sqm (optional — warning only) ────────────────────────────
    issues.append(check_positive(
        vr, "price_per_sqm",
        code="PRICE_PER_SQM_POSITIVE",
        message_ar="سعر المتر المربع يجب أن يكون أكبر من صفر",
        message_en="Price per sqm must be greater than zero",
        severity=Severity.WARNING,
    ))

    # ── 3. Cost approach indication (optional) ────────────────────────────────
    cost = data.get("cost_approach")
    if cost is not None:
        issues.append(check_positive(
            cost, "cost_value_indication",
            code="COST_VALUE_POSITIVE",
            message_ar="مؤشر القيمة بأسلوب التكلفة يجب أن يكون أكبر من صفر",
            message_en="Cost approach value indication must be greater than zero",
            severity=Severity.WARNING,
        ))

    # ── 4. Income approach indication (optional) ──────────────────────────────
    income = data.get("income_approach")
    if income is not None:
        issues.append(check_positive(
            income, "income_value_indication",
            code="INCOME_VALUE_POSITIVE",
            message_ar="مؤشر القيمة بأسلوب الدخل يجب أن يكون أكبر من صفر",
            message_en="Income approach value indication must be greater than zero",
            severity=Severity.WARNING,
        ))

    # ── 5. Reconciliation (optional) ─────────────────────────────────────────
    recon = data.get("reconciliation")
    if recon is not None:
        issues.append(check_positive(
            recon, "final_value",
            code="RECONCILIATION_FINAL_POSITIVE",
            message_ar="القيمة النهائية في التوفيق يجب أن تكون أكبر من صفر",
            message_en="Reconciliation final value must be greater than zero",
        ))
        issues.append(check_not_nan_inf(
            recon, "final_value",
            code="RECONCILIATION_FINAL_NAN_INF",
            message_ar="القيمة النهائية في التوفيق تحتوي على قيمة غير صالحة (NaN أو ∞)",
            message_en="Reconciliation final value contains an invalid value (NaN or Infinity)",
        ))
        weights = recon.get("weights") or {}
        if weights:
            issues.append(check_weights_sum(
                weights,
                field="reconciliation.weights",
                code="WEIGHTS_SUM_MISMATCH",
                message_ar="مجموع أوزان المناهج يجب أن يساوي 100%",
                message_en="Sum of reconciliation weights must equal 100%",
            ))

    return ValidationResult.from_iterable(issues)
