"""
input_validator.py — Input data validation for EXPERT_SMART report generation.

Validates raw inputs passed to generate_pdf() / the report pipeline before
any rendering takes place.  All 18 rules are display-only checks; no
valuation math is performed here.

Raises nothing — always returns a ValidationResult.
"""

from __future__ import annotations

from typing import Any, Mapping

from .result import Severity, ValidationIssue, ValidationResult
from .rules import (
    _parse_numeric,
    check_lte,
    check_nonneg,
    check_not_nan_inf,
    check_positive,
    check_range,
    check_weights_sum,
    require,
)

# ── Valid profile keys ────────────────────────────────────────────────────────

_VALID_PROFILES: frozenset[str] = frozenset({"legacy", "detailed", "professional_template"})


# ── Public API ────────────────────────────────────────────────────────────────

def validate_inputs(
    data: Mapping[str, Any],
    *,
    profile_key: str = "legacy",
) -> ValidationResult:
    """
    Validate the input DTO passed to the PDF/report pipeline.

    Args:
        data: Top-level report data dict.  Expected top-level keys:
              appraiser, property_info, comparables, cost_approach,
              income_approach, reconciliation.
        profile_key: 'legacy' / 'detailed' / 'professional_template'.

    Returns:
        ValidationResult — inspect .is_valid and .errors/.warnings/.infos.
        Never raises.
    """
    issues: list[Any] = []

    # ── 1. Profile key ────────────────────────────────────────────────────────
    if profile_key not in _VALID_PROFILES:
        issues.append(ValidationIssue(
            field="profile_key",
            severity=Severity.ERROR,
            code="PROFILE_UNKNOWN",
            message_ar=f"مفتاح الـ profile غير معروف: '{profile_key}'",
            message_en=f"Unknown profile_key: '{profile_key}'. "
                       f"Valid: {sorted(_VALID_PROFILES)}",
        ))

    # ── 2. Appraiser ──────────────────────────────────────────────────────────
    appraiser = data.get("appraiser") or {}
    issues.append(require(
        appraiser, "name",
        code="APPRAISER_NAME_MISSING",
        message_ar="اسم المُقيِّم مطلوب",
        message_en="Appraiser name is required",
        severity=Severity.ERROR,
    ))
    issues.append(require(
        appraiser, "license",
        code="APPRAISER_LICENSE_MISSING",
        message_ar="رقم ترخيص المُقيِّم مطلوب",
        message_en="Appraiser license number is required",
        severity=Severity.WARNING,
    ))
    issues.append(require(
        appraiser, "date",
        code="APPRAISER_DATE_MISSING",
        message_ar="تاريخ التقرير مطلوب",
        message_en="Report date is required",
        severity=Severity.WARNING,
    ))

    # ── 3. Property info ──────────────────────────────────────────────────────
    prop = data.get("property_info") or {}
    issues.append(require(
        prop, "area",
        code="PROPERTY_AREA_MISSING",
        message_ar="مساحة العقار مطلوبة",
        message_en="Property area is required",
        severity=Severity.ERROR,
    ))
    issues.append(check_positive(
        prop, "area",
        code="PROPERTY_AREA_POSITIVE",
        message_ar="مساحة العقار يجب أن تكون أكبر من صفر",
        message_en="Property area must be greater than zero",
        severity=Severity.ERROR,
    ))
    issues.append(require(
        prop, "type",
        code="PROPERTY_TYPE_MISSING",
        message_ar="نوع العقار غير محدد",
        message_en="Property type is not specified",
        severity=Severity.WARNING,
    ))

    # ── 4. Cost approach (skipped if absent) ──────────────────────────────────
    cost = data.get("cost_approach")
    if cost is not None:
        issues.append(check_positive(
            cost, "rcn",
            code="COST_RCN_POSITIVE",
            message_ar="تكلفة الإحلال الجديدة (RCN) يجب أن تكون أكبر من صفر",
            message_en="Replacement cost new (RCN) must be greater than zero",
            severity=Severity.ERROR,
        ))
        issues.append(check_lte(
            cost, "depreciation", "rcn",
            code="COST_DEPRECIATION_RANGE",
            message_ar="قيمة الإهلاك يجب ألا تتجاوز تكلفة الإحلال الجديدة (RCN)",
            message_en="Depreciation must not exceed the replacement cost new (RCN)",
            severity=Severity.WARNING,
        ))
        issues.append(check_positive(
            cost, "land_value",
            code="COST_LAND_VALUE_POSITIVE",
            message_ar="قيمة الأرض يجب أن تكون أكبر من صفر",
            message_en="Land value must be greater than zero",
            severity=Severity.ERROR,
        ))

    # ── 5. Income approach (skipped if absent) ────────────────────────────────
    income = data.get("income_approach")
    if income is not None:
        issues.append(check_positive(
            income, "gross_income",
            code="INCOME_GROSS_POSITIVE",
            message_ar="الدخل الإجمالي السنوي يجب أن يكون أكبر من صفر",
            message_en="Gross annual income must be greater than zero",
            severity=Severity.ERROR,
        ))
        issues.append(check_range(
            income, "vacancy_pct",
            min_val=0.0, max_val=100.0,
            code="INCOME_VACANCY_RANGE",
            message_ar="نسبة الشواغر يجب أن تكون بين 0% و 100%",
            message_en="Vacancy percentage must be between 0% and 100%",
            severity=Severity.WARNING,
        ))
        issues.append(check_nonneg(
            income, "opex",
            code="INCOME_OPEX_NONNEG",
            message_ar="المصروفات التشغيلية يجب ألا تكون سالبة",
            message_en="Operating expenses must not be negative",
            severity=Severity.WARNING,
        ))
        issues.append(check_range(
            income, "cap_rate",
            min_val=1.0, max_val=20.0,
            code="INCOME_CAP_RATE_RANGE",
            message_ar="معدل الرسملة غير مألوف — يُتوقع بين 1% و 20%",
            message_en="Cap rate is unusual — expected between 1% and 20%",
            severity=Severity.WARNING,
        ))
        if profile_key == "professional_template":
            issues.append(check_range(
                income, "discount_rate",
                min_val=1.0, max_val=30.0,
                code="INCOME_DISCOUNT_RATE_RANGE",
                message_ar="معدل الخصم غير مألوف — يُتوقع بين 1% و 30%",
                message_en="Discount rate is unusual — expected between 1% and 30%",
                severity=Severity.WARNING,
            ))

    # ── 6. Reconciliation weights (skipped if absent) ─────────────────────────
    recon = data.get("reconciliation")
    if recon is not None:
        weights = recon.get("weights") or {}
        for wkey, wval in weights.items():
            parsed = _parse_numeric(wval)
            if parsed is not None and parsed < 0:
                issues.append(ValidationIssue(
                    field=f"reconciliation.weights.{wkey}",
                    severity=Severity.ERROR,
                    code="WEIGHTS_NEGATIVE",
                    message_ar=f"وزن '{wkey}' سالب — يجب أن تكون الأوزان غير سالبة",
                    message_en=f"Weight '{wkey}' is negative — weights must be non-negative",
                ))

    # ── 7. Comparables ────────────────────────────────────────────────────────
    comparables = data.get("comparables") or []
    for i, comp in enumerate(comparables):
        if not isinstance(comp, dict):
            continue
        issues.append(check_positive(
            comp, "sale_price",
            code="COMPARABLE_SALE_PRICE_POSITIVE",
            message_ar=f"سعر البيع للمقارن [{i}] يجب أن يكون أكبر من صفر",
            message_en=f"Sale price for comparable [{i}] must be greater than zero",
            severity=Severity.ERROR,
        ))
        issues.append(check_positive(
            comp, "area",
            code="COMPARABLE_AREA_POSITIVE",
            message_ar=f"مساحة المقارن [{i}] يجب أن تكون أكبر من صفر",
            message_en=f"Area for comparable [{i}] must be greater than zero",
            severity=Severity.ERROR,
        ))

    return ValidationResult.from_iterable(issues)
