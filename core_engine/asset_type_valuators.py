"""
asset_type_valuators.py
========================
Specialized valuation functions for asset types not covered by special_assets.py.
This module is ADDITIVE — it does not modify the existing valuation pipeline.

Implements:
    1. value_intangible_asset    — MPEEM (IFRS 13 / IVS 210)
    2. value_partial_interest    — Pro-rata × DLOC × DLOM (IVS 200)
    3. value_under_construction  — Partial cost + completion ratio + risk premium (IFRS 16 / IAS 11)
    4. value_quarry_extended     — Wraps special_assets.value_quarry with reporting metadata

Standards referenced:
    - IFRS 13     Fair Value Measurement
    - IVS 210     Intangible Assets
    - IVS 200     Businesses & Business Interests (partial interests)
    - IAS 16/40   Property, Plant & Equipment / Investment Property
    - Egyptian Engineering Syndicate Real Estate Valuation Standard
"""

from __future__ import annotations
from typing import Any, Dict, Optional


# ════════════════════════════════════════════════════════════════════════════
#  1. INTANGIBLE ASSETS — MPEEM (Multi-Period Excess Earnings Method)
# ════════════════════════════════════════════════════════════════════════════

def value_intangible_asset(
    annual_revenue: float,
    contributory_asset_charge_pct: float = 0.10,   # نسبة مخصومة لمساهمة الأصول الأخرى
    intangible_attribution_pct: float = 0.35,      # نسبة العائد المنسوبة للأصل المعنوي
    license_term_years: int = 10,                  # عمر الحق المعنوي
    discount_rate: float = 0.15,                   # معدل الخصم (أعلى لمخاطر العائد)
    tax_amortization_benefit_pct: float = 0.18,    # TAB (Tax Amortization Benefit)
    region: str = "EG",
) -> Dict[str, Any]:
    """
    Multi-Period Excess Earnings Method (MPEEM) per IFRS 13 / IVS 210.

    Used for: حقوق التطوير، حقوق الامتياز، حقوق التسويق، علامات تجارية مرتبطة
              بالعقار، حقوق الانتفاع من امتيازات حكومية.

    Formula:
        Excess Earnings_t = annual_revenue × intangible_attribution × (1 − contributory_charge)
        PV               = Σ_{t=1}^{n} Excess Earnings_t / (1+r)^t
        Value            = PV × (1 + TAB)
    """
    if annual_revenue <= 0:
        raise ValueError("annual_revenue يجب أن يكون موجباً.")
    if not 0 < intangible_attribution_pct <= 1:
        raise ValueError("intangible_attribution_pct يجب أن يكون بين 0 و 1.")
    if not 0 <= contributory_asset_charge_pct < 1:
        raise ValueError("contributory_asset_charge_pct يجب أن يكون بين 0 وأقل من 1.")

    region_mult = 2.5 if region.upper() == "SA" else 1.0
    revenue_loc = annual_revenue * region_mult

    excess_earnings = revenue_loc * intangible_attribution_pct * (1 - contributory_asset_charge_pct)

    # PV of excess earnings stream
    pv_stream = sum(
        excess_earnings / ((1 + discount_rate) ** t)
        for t in range(1, license_term_years + 1)
    )

    # Tax Amortization Benefit (TAB) — common in IVS 210 for income-method intangibles
    intangible_value = pv_stream * (1 + tax_amortization_benefit_pct)

    return {
        "asset_type":                       "intangible",
        "method":                           "MPEEM (Multi-Period Excess Earnings Method)",
        "standards":                        "IFRS 13 / IVS 210",
        "annual_revenue":                   round(revenue_loc, 0),
        "intangible_attribution_pct":       intangible_attribution_pct,
        "contributory_asset_charge_pct":    contributory_asset_charge_pct,
        "annual_excess_earnings":           round(excess_earnings, 0),
        "license_term_years":               license_term_years,
        "discount_rate":                    discount_rate,
        "pv_excess_earnings":               round(pv_stream, 0),
        "tax_amortization_benefit_pct":     tax_amortization_benefit_pct,
        "reconciled_value":                 round(max(intangible_value, 0), 0),
    }


# ════════════════════════════════════════════════════════════════════════════
#  2. PARTIAL INTERESTS — Pro-rata × DLOC × DLOM
# ════════════════════════════════════════════════════════════════════════════

def value_partial_interest(
    total_property_value: float,        # القيمة السوقية للملكية الكاملة
    ownership_pct: float,               # نسبة الملكية الجزئية (0 < pct ≤ 1)
    is_controlling: bool = False,       # هل الحصة تكفي للسيطرة؟
    dloc_pct: float = 0.20,             # Discount for Lack of Control (10–25%)
    dlom_pct: float = 0.20,             # Discount for Lack of Marketability (15–30%)
    region: str = "EG",
) -> Dict[str, Any]:
    """
    Partial-interest valuation per IVS 200 / Egyptian Civil Code (شيوع).

    Pro-rata × ownership × (1 − DLOC if minority) × (1 − DLOM)

    DLOC = خصم عدم السيطرة     (للحصص الأقلية فقط)
    DLOM = خصم عدم القابلية للتسويق (يطبق دائماً للحصص الجزئية)
    """
    if total_property_value <= 0:
        raise ValueError("total_property_value يجب أن يكون موجباً.")
    if not 0 < ownership_pct <= 1:
        raise ValueError("ownership_pct يجب أن يكون بين 0 و 1 (مثلاً 0.30 لـ 30%).")
    if not 0 <= dloc_pct < 1:
        raise ValueError("dloc_pct يجب أن يكون بين 0 وأقل من 1.")
    if not 0 <= dlom_pct < 1:
        raise ValueError("dlom_pct يجب أن يكون بين 0 وأقل من 1.")

    region_mult = 2.5 if region.upper() == "SA" else 1.0
    full_value = total_property_value * region_mult

    pro_rata_value = full_value * ownership_pct
    effective_dloc = 0.0 if is_controlling else dloc_pct
    after_control_discount = pro_rata_value * (1 - effective_dloc)
    final_value = after_control_discount * (1 - dlom_pct)

    return {
        "asset_type":             "partial_interest",
        "method":                 "Pro-rata × DLOC × DLOM (IVS 200)",
        "standards":              "IVS 200 / Egyptian Civil Code (شيوع)",
        "total_property_value":   round(full_value, 0),
        "ownership_pct":          ownership_pct,
        "ownership_pct_label":    f"{ownership_pct * 100:.2f}%",
        "is_controlling":         is_controlling,
        "pro_rata_value":         round(pro_rata_value, 0),
        "dloc_pct":               effective_dloc,
        "dloc_amount":            round(pro_rata_value * effective_dloc, 0),
        "value_after_dloc":       round(after_control_discount, 0),
        "dlom_pct":               dlom_pct,
        "dlom_amount":            round(after_control_discount * dlom_pct, 0),
        "reconciled_value":       round(max(final_value, 0), 0),
        "implied_per_unit_pct":   round(final_value / max(full_value, 1), 4),
    }


# ════════════════════════════════════════════════════════════════════════════
#  3. UNDER-CONSTRUCTION — Cost-to-date + Risk Premium
# ════════════════════════════════════════════════════════════════════════════

def value_under_construction(
    planned_total_cost: float,                # التكلفة الكاملة المخططة (أرض + بناء)
    completion_pct: float,                    # نسبة الإنجاز الحالية (0–1)
    planned_market_value: Optional[float] = None,  # القيمة السوقية بعد الاكتمال
    remaining_cost_to_complete: Optional[float] = None,  # تكلفة الإكمال المتبقية
    construction_risk_pct: float = 0.10,      # نسبة المخاطرة (تأخير، تجاوز كلفة)
    months_to_completion: int = 12,           # المدة المتبقية للاكتمال
    discount_rate: float = 0.12,              # معدل الخصم لمخاطر التطوير
    developer_profit_pct: float = 0.15,       # هامش ربح المطور
    region: str = "EG",
) -> Dict[str, Any]:
    """
    Under-construction valuation — صيغة المستخدم:
        قيمة جزئية = التكلفة المنفقة × نسبة الإنجاز − نسبة المخاطرة
    مع تكامل منهجين:
        Method A (Cost-to-date):
            value_a = planned_total_cost × completion_pct × (1 − risk_pct)
        Method B (Discounted Residual):
            value_b = (planned_market_value − remaining_cost_to_complete
                      − developer_profit) / (1 + r)^(months/12)
        النتيجة النهائية = متوسط مرجح (60% A + 40% B عند توفر B).

    Standards: IAS 16 (PPE under construction), IFRS 13 (fair value), IVS 230 (Real Property Interests).
    """
    if planned_total_cost <= 0:
        raise ValueError("planned_total_cost يجب أن يكون موجباً.")
    if not 0 <= completion_pct <= 1:
        raise ValueError("completion_pct يجب أن يكون بين 0 و 1.")
    if not 0 <= construction_risk_pct < 1:
        raise ValueError("construction_risk_pct يجب أن يكون بين 0 وأقل من 1.")

    region_mult = 2.5 if region.upper() == "SA" else 1.0
    planned_total_cost_loc = planned_total_cost * region_mult

    # ── Method A: Cost-to-date with risk discount (formula الخاصة بالمستخدم) ──
    cost_incurred = planned_total_cost_loc * completion_pct
    value_a = cost_incurred * (1 - construction_risk_pct)

    # ── Method B: Discounted Residual (only if market value supplied) ────────
    value_b: Optional[float] = None
    pv_factor = 1.0
    developer_profit_amount = 0.0
    if planned_market_value is not None and planned_market_value > 0:
        planned_mv_loc = planned_market_value * region_mult
        if remaining_cost_to_complete is None:
            remaining_cost_to_complete = planned_total_cost_loc * (1 - completion_pct)
        else:
            remaining_cost_to_complete = remaining_cost_to_complete * region_mult
        developer_profit_amount = planned_mv_loc * developer_profit_pct
        gross_residual = planned_mv_loc - remaining_cost_to_complete - developer_profit_amount
        years_to_completion = max(months_to_completion, 0) / 12.0
        pv_factor = 1.0 / ((1 + discount_rate) ** years_to_completion) if years_to_completion > 0 else 1.0
        value_b = gross_residual * pv_factor

    # ── Reconciliation ───────────────────────────────────────────────────────
    if value_b is not None:
        reconciled = value_a * 0.60 + value_b * 0.40
        weights = "60% Cost-to-date + 40% Discounted Residual"
    else:
        reconciled = value_a
        weights = "100% Cost-to-date (لا توجد قيمة سوقية مخططة)"

    return {
        "asset_type":                 "under_construction",
        "method":                     "Cost-to-date + Risk + (optional) Discounted Residual",
        "standards":                  "IAS 16 / IFRS 13 / IVS 230",
        "planned_total_cost":         round(planned_total_cost_loc, 0),
        "completion_pct":             completion_pct,
        "completion_pct_label":       f"{completion_pct * 100:.2f}%",
        "cost_incurred":              round(cost_incurred, 0),
        "construction_risk_pct":      construction_risk_pct,
        "construction_risk_amount":   round(cost_incurred * construction_risk_pct, 0),
        "value_method_a":             round(value_a, 0),
        "planned_market_value":       round(planned_market_value * region_mult, 0) if planned_market_value else None,
        "remaining_cost_to_complete": round(remaining_cost_to_complete, 0) if remaining_cost_to_complete else None,
        "developer_profit_pct":       developer_profit_pct,
        "developer_profit_amount":    round(developer_profit_amount, 0) if developer_profit_amount else None,
        "discount_rate":              discount_rate,
        "months_to_completion":       months_to_completion,
        "pv_factor":                  round(pv_factor, 4),
        "value_method_b":             round(value_b, 0) if value_b is not None else None,
        "weighting":                  weights,
        "reconciled_value":           round(max(reconciled, 0), 0),
    }


# ════════════════════════════════════════════════════════════════════════════
#  4. QUARRY — wrapper that calls special_assets.value_quarry and adds metadata
#     for the reporting layer (Excel / Word). Pure pass-through if special_assets
#     is unavailable.
# ════════════════════════════════════════════════════════════════════════════

def value_quarry_extended(**kwargs) -> Dict[str, Any]:
    """
    Wraps special_assets.value_quarry to ensure the reporting layer can find
    the result under a stable key set. Adds methodology + standards + IVS reference.
    """
    try:
        from special_assets import value_quarry
    except Exception:
        from core_engine.special_assets import value_quarry  # type: ignore

    res = value_quarry(**kwargs)
    res.setdefault("method",    "Discounted Cash Flow on Proven Reserves (Depletion)")
    res.setdefault("standards", "IVS 220 / SAMREC / JORC code")
    res.setdefault("asset_type", "quarry")
    return res


# ════════════════════════════════════════════════════════════════════════════
#  PUBLIC DISPATCH — pick a valuator from a property_type label (best-effort)
# ════════════════════════════════════════════════════════════════════════════

# Mapping from Arabic labels (as in frontend dropdown) → valuator key
_TYPE_TO_VALUATOR = {
    "أصول معنوية":          "intangible",
    "ملكيات جزئية":         "partial_interest",
    "استثمارات تحت الإنشاء":"under_construction",
    "مناجم":                "quarry",
}


def has_specialized_valuator(property_type: str) -> bool:
    return (property_type or "").strip() in _TYPE_TO_VALUATOR


def run_specialized_valuator(property_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    يستدعي الدالة المتخصصة المناسبة للنوع. يُرجع dict موحَّد يحوي
    على الأقل: reconciled_value + asset_type + method + standards.

    payload : كل حقول الطلب (يستخرج كل valuator ما يحتاجه فقط).
    """
    key = _TYPE_TO_VALUATOR.get((property_type or "").strip())
    if not key:
        raise ValueError(f"لا يوجد valuator متخصص للنوع: {property_type}")

    p = payload  # alias
    region = (p.get("region") or "EG")

    if key == "intangible":
        return value_intangible_asset(
            annual_revenue                = float(p.get("annual_revenue", 0) or 0),
            contributory_asset_charge_pct = float(p.get("contributory_asset_charge_pct", 0.10)),
            intangible_attribution_pct    = float(p.get("intangible_attribution_pct", 0.35)),
            license_term_years            = int(p.get("license_term_years", 10)),
            discount_rate                 = float(p.get("discount_rate", 0.15)),
            tax_amortization_benefit_pct  = float(p.get("tax_amortization_benefit_pct", 0.18)),
            region                        = region,
        )

    if key == "partial_interest":
        return value_partial_interest(
            total_property_value = float(p.get("total_property_value") or
                                         (float(p.get("area", 0) or 0) *
                                          float(p.get("price_per_meter", 0) or 0))),
            ownership_pct        = float(p.get("ownership_pct", 0.50)),
            is_controlling       = bool(p.get("is_controlling", False)),
            dloc_pct             = float(p.get("dloc_pct", 0.20)),
            dlom_pct             = float(p.get("dlom_pct", 0.20)),
            region               = region,
        )

    if key == "under_construction":
        return value_under_construction(
            planned_total_cost          = float(p.get("planned_total_cost", 0) or 0),
            completion_pct              = float(p.get("completion_pct", 0.50)),
            planned_market_value        = (float(p["planned_market_value"])
                                           if p.get("planned_market_value") else None),
            remaining_cost_to_complete  = (float(p["remaining_cost_to_complete"])
                                           if p.get("remaining_cost_to_complete") else None),
            construction_risk_pct       = float(p.get("construction_risk_pct", 0.10)),
            months_to_completion        = int(p.get("months_to_completion", 12)),
            discount_rate               = float(p.get("discount_rate", 0.12)),
            developer_profit_pct        = float(p.get("developer_profit_pct", 0.15)),
            region                      = region,
        )

    if key == "quarry":
        return value_quarry_extended(
            reserve_tons             = float(p.get("reserve_tons", 0) or 0),
            annual_extraction_tons   = float(p.get("annual_extraction_tons", 0) or 0),
            price_per_ton            = float(p.get("price_per_ton", 120)),
            operating_cost_pct       = float(p.get("operating_cost_pct", 0.55)),
            discount_rate            = float(p.get("discount_rate", 0.12)),
            rehabilitation_cost      = float(p.get("rehabilitation_cost", 0)),
            land_area_m2             = float(p.get("land_area_m2", p.get("area", 0) or 0)),
            land_ppm                 = float(p.get("land_ppm", p.get("price_per_meter", 150) or 150)),
            region                   = region,
        )

    raise ValueError(f"unhandled valuator key: {key}")
