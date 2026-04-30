"""
reit_nav_engine.py
===================
Portfolio-level NAV engine for Real Estate Investment Trusts (REITs)
محرك صافي قيمة الأصول للصناديق العقارية على مستوى المحفظة الكاملة

Standards:
    - IFRS 13 (Fair Value Measurement)
    - IVS 103 (Valuation Approaches)
    - IOSCO Principles for the Valuation of CIS Portfolios
    - Egyptian FRA (Financial Regulatory Authority) disclosure rules
    - Saudi CMA REIT Regulations (semi-annual valuation requirement)

Design notes:
    * This module is ADDITIVE only. It does not modify any existing engine.
    * It composes with `fund_valuation_engine.run_fund_valuation` for per-asset
      fair value computation when only operational inputs are supplied.
    * If the caller already has each asset's fair value, the per-asset DCF step
      is skipped and the value is consumed as-is (Level 2 / Level 3 input).

Public API:
    run_reit_nav(payload)               -> dict
    generate_reit_nav_excel(result, dir) -> str (path to .xlsx)

Payload schema (run_reit_nav):
    fund_name           str
    units_outstanding   int      عدد الوحدات المُصدَرة للصندوق
    valuation_date      str      "YYYY-MM-DD" (default: today)
    ifrs_level          int      1 / 2 / 3 (default: 3)
    cash_and_equiv      float    النقد وما في حكمه
    receivables         float    المدينون / إيجارات مستحقة
    other_assets        float    أصول أخرى (استثمارات قصيرة الأجل …)
    loans               float    إجمالي القروض البنكية
    accrued_expenses    float    مصروفات مستحقة
    distributions_payable float  توزيعات معتمدة لم تُدفع
    deferred_tax        float    ضريبة مؤجلة
    other_liabilities   float    التزامات أخرى
    properties          list[dict] قائمة العقارات بالمحفظة:
        each item supports:
            - either: fair_value (float)            ← يُستخدم مباشرة
            - or:     market_value, annual_rent,
                      vacancy_rate, operating_expenses, area,
                      property_type, location, ifrs_level
                      (تُمرَّر إلى run_fund_valuation لحساب FV)
            - asset_id   str (optional)
            - asset_name str (optional)
"""

from __future__ import annotations
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

# Compose with the existing per-asset engine — read-only import
try:
    from core_engine.fund_valuation_engine import run_fund_valuation  # type: ignore
except Exception:
    try:
        from fund_valuation_engine import run_fund_valuation  # type: ignore
    except Exception:
        run_fund_valuation = None  # graceful fallback when engine isn't on path

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_OUT_DIR = os.path.join(_BASE_DIR, "outputs", "reports")


# ════════════════════════════════════════════════════════════════════════════
#  PORTFOLIO-LEVEL NAV
# ════════════════════════════════════════════════════════════════════════════

def _coerce_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v) if v not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _per_asset_fair_value(asset: Dict[str, Any], default_ifrs_level: int) -> Dict[str, Any]:
    """
    Returns per-asset valuation dict with at minimum: fair_value, noi, cap_rate.
    If `fair_value` is supplied, it is trusted and basic metrics are echoed.
    Otherwise delegates to fund_valuation_engine.run_fund_valuation.
    """
    asset_id   = str(asset.get("asset_id", "") or asset.get("id", ""))
    asset_name = str(asset.get("asset_name", "") or asset.get("name", "") or asset_id)

    # Fast path: caller has pre-computed fair value (e.g. external appraiser)
    if "fair_value" in asset and asset["fair_value"] not in (None, ""):
        fv = _coerce_float(asset["fair_value"])
        return {
            "asset_id":      asset_id,
            "asset_name":    asset_name,
            "property_type": str(asset.get("property_type", "")),
            "location":      str(asset.get("location", "")),
            "area":          _coerce_float(asset.get("area")),
            "fair_value":    fv,
            "noi":           _coerce_float(asset.get("noi")),
            "cap_rate":      _coerce_float(asset.get("cap_rate")),
            "cap_rate_pct":  _coerce_float(asset.get("cap_rate")) * 100,
            "method":        "Pre-supplied fair value (Level 2/3 input)",
        }

    # Slow path: invoke per-asset engine
    if run_fund_valuation is None:
        raise RuntimeError(
            "fund_valuation_engine.run_fund_valuation غير متاح؛ "
            "يجب توفير fair_value لكل أصل في المحفظة."
        )

    sub_payload = {
        "property_type":      asset.get("property_type", ""),
        "location":           asset.get("location", "غير محدد"),
        "area":               _coerce_float(asset.get("area")),
        "market_value":       _coerce_float(asset.get("market_value")),
        "annual_rent":        _coerce_float(asset.get("annual_rent")),
        "vacancy_rate":       _coerce_float(asset.get("vacancy_rate")),
        "operating_expenses": _coerce_float(asset.get("operating_expenses")),
        "loan_amount":        0.0,                    # liabilities aggregated at fund level
        "total_units":        1,
        "ifrs_level":         int(asset.get("ifrs_level", default_ifrs_level)),
        "fund_name":          asset_name or "أصل ضمن المحفظة",
    }
    inner = run_fund_valuation(sub_payload)
    return {
        "asset_id":      asset_id,
        "asset_name":    asset_name,
        "property_type": inner.get("property_type", ""),
        "location":      inner.get("location", ""),
        "area":          inner.get("area", 0.0),
        "fair_value":    inner.get("fair_value", 0.0),
        "noi":           inner.get("noi", 0.0),
        "cap_rate":      inner.get("cap_rate", 0.0),
        "cap_rate_pct":  inner.get("cap_rate_pct", 0.0),
        "method":        inner.get("fair_value_method", ""),
    }


def run_reit_nav(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aggregates a REIT portfolio into Gross Asset Value, Net Asset Value,
    and NAV per Unit, with IFRS 13 disclosure metadata.

    Returns
    -------
    dict — all portfolio metrics + per-asset breakdown.
    """
    fund_name: str = str(payload.get("fund_name", "صندوق الاستثمار العقاري")).strip()
    units_outstanding: int = int(_coerce_float(payload.get("units_outstanding"), 0))
    if units_outstanding <= 0:
        raise ValueError("units_outstanding يجب أن يكون عدداً موجباً (عدد وحدات الصندوق).")

    ifrs_level: int = int(_coerce_float(payload.get("ifrs_level"), 3))
    if ifrs_level not in (1, 2, 3):
        raise ValueError("ifrs_level يجب أن يكون 1 أو 2 أو 3.")

    valuation_date: str = str(payload.get("valuation_date") or datetime.today().strftime("%Y-%m-%d"))

    # ── 1. Per-asset valuation ────────────────────────────────────────────────
    raw_props: List[Dict[str, Any]] = list(payload.get("properties") or [])
    if not raw_props:
        raise ValueError("properties فارغة — يجب توفير قائمة عقارات المحفظة.")

    assets: List[Dict[str, Any]] = [_per_asset_fair_value(a, ifrs_level) for a in raw_props]

    # ── 2. Asset side ─────────────────────────────────────────────────────────
    real_estate_fv: float = sum(a["fair_value"] for a in assets)
    cash:           float = _coerce_float(payload.get("cash_and_equiv"))
    receivables:    float = _coerce_float(payload.get("receivables"))
    other_assets:   float = _coerce_float(payload.get("other_assets"))
    gross_asset_value: float = real_estate_fv + cash + receivables + other_assets

    # ── 3. Liability side ─────────────────────────────────────────────────────
    loans:                 float = _coerce_float(payload.get("loans"))
    accrued_expenses:      float = _coerce_float(payload.get("accrued_expenses"))
    distributions_payable: float = _coerce_float(payload.get("distributions_payable"))
    deferred_tax:          float = _coerce_float(payload.get("deferred_tax"))
    other_liabilities:     float = _coerce_float(payload.get("other_liabilities"))
    total_liabilities: float = (
        loans + accrued_expenses + distributions_payable + deferred_tax + other_liabilities
    )

    # ── 4. NAV core ───────────────────────────────────────────────────────────
    nav: float = gross_asset_value - total_liabilities
    nav_per_unit: float = nav / units_outstanding

    # ── 5. Portfolio metrics ──────────────────────────────────────────────────
    total_noi: float = sum(_coerce_float(a.get("noi")) for a in assets)
    weighted_cap_rate: float = (total_noi / real_estate_fv) if real_estate_fv > 0 else 0.0
    weighted_cap_rate_pct: float = weighted_cap_rate * 100

    ltv: float = (loans / real_estate_fv) if real_estate_fv > 0 else 0.0
    ltv_pct: float = ltv * 100

    gearing_ratio: float = (total_liabilities / gross_asset_value) if gross_asset_value > 0 else 0.0
    gearing_ratio_pct: float = gearing_ratio * 100

    # ── 6. Health Rating ──────────────────────────────────────────────────────
    health_score: float = 100.0
    if ltv_pct > 50:                health_score -= 25       # CMA REIT cap is ~50%
    elif ltv_pct > 35:              health_score -= 10
    if weighted_cap_rate_pct < 5:   health_score -= 15
    if gearing_ratio_pct > 60:      health_score -= 15
    if len(assets) < 3:             health_score -= 10       # diversification penalty
    if cash <= 0:                   health_score -= 5
    health_score = max(0.0, min(100.0, health_score))

    if health_score >= 85:
        health_label = "ممتاز — مطابق لمتطلبات الإدراج المؤسسي"
    elif health_score >= 70:
        health_label = "جيد — مقبول لصناديق REITs"
    elif health_score >= 55:
        health_label = "متوسط — يحتاج مراجعة هيكل التمويل أو التنويع"
    else:
        health_label = "ضعيف — توصية بإعادة هيكلة المحفظة"

    # ── 7. IFRS 13 / regulatory disclosure ────────────────────────────────────
    ifrs_level_labels = {
        1: "Level 1 — أسعار معلنة في أسواق نشطة",
        2: "Level 2 — مدخلات قابلة للملاحظة (معاملات سوق مشابهة)",
        3: "Level 3 — مدخلات غير قابلة للملاحظة (نهج الدخل / DCF)",
    }
    ifrs_disclosure = (
        f"وفقاً لـ IFRS 13 §93، يُفصَح عن صافي قيمة الأصول للصندوق «{fund_name}» "
        f"بتاريخ {valuation_date} كقياس قيمة عادلة من {ifrs_level_labels[ifrs_level]}."
    )

    # ── 8. Result dict ────────────────────────────────────────────────────────
    return {
        "fund_name":              fund_name,
        "valuation_date":         valuation_date,
        "ifrs_level":             ifrs_level,
        "ifrs_level_label":       ifrs_level_labels[ifrs_level],
        "ifrs_disclosure":        ifrs_disclosure,
        # Asset side
        "asset_count":            len(assets),
        "real_estate_fair_value": real_estate_fv,
        "cash_and_equiv":         cash,
        "receivables":            receivables,
        "other_assets":           other_assets,
        "gross_asset_value":      gross_asset_value,
        # Liability side
        "loans":                  loans,
        "accrued_expenses":       accrued_expenses,
        "distributions_payable":  distributions_payable,
        "deferred_tax":           deferred_tax,
        "other_liabilities":      other_liabilities,
        "total_liabilities":      total_liabilities,
        # NAV
        "nav":                    nav,
        "units_outstanding":      units_outstanding,
        "nav_per_unit":           nav_per_unit,
        # Portfolio metrics
        "total_noi":              total_noi,
        "weighted_cap_rate":      weighted_cap_rate,
        "weighted_cap_rate_pct":  weighted_cap_rate_pct,
        "ltv":                    ltv,
        "ltv_pct":                ltv_pct,
        "gearing_ratio":          gearing_ratio,
        "gearing_ratio_pct":      gearing_ratio_pct,
        # Health
        "health_score":           health_score,
        "health_label":           health_label,
        # Per-asset breakdown
        "assets":                 assets,
    }


# ════════════════════════════════════════════════════════════════════════════
#  EXCEL REPORT (lightweight — does not depend on existing report templates)
# ════════════════════════════════════════════════════════════════════════════

def generate_reit_nav_excel(result: Dict[str, Any], output_dir: str = "") -> str:
    """
    Renders an RTL Arabic Excel report for the REIT NAV result.
    Returns the absolute path of the produced .xlsx file.
    """
    import xlsxwriter  # type: ignore

    out_dir = output_dir.strip() if output_dir.strip() else _OUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(out_dir, f"reit_nav_{timestamp}.xlsx")

    NAVY, GOLD, WHITE, LIGHT, GREEN, RED, GREY = (
        "#1F3864", "#C9A227", "#FFFFFF", "#EAF0FB", "#1E8449", "#C0392B", "#F2F2F2"
    )

    wb = xlsxwriter.Workbook(filepath)
    ws = wb.add_worksheet("REIT NAV — IFRS 13")
    ws.right_to_left()

    title_fmt   = wb.add_format({"bold": True, "font_size": 16, "bg_color": NAVY,
                                 "font_color": WHITE, "align": "center", "valign": "vcenter"})
    section_fmt = wb.add_format({"bold": True, "font_size": 12, "bg_color": GOLD,
                                 "font_color": NAVY, "align": "right"})
    label_fmt   = wb.add_format({"bold": True, "bg_color": LIGHT, "align": "right", "border": 1})
    val_fmt     = wb.add_format({"num_format": "#,##0.00", "align": "right", "border": 1})
    pct_fmt     = wb.add_format({"num_format": "0.00%", "align": "right", "border": 1})
    nav_fmt     = wb.add_format({"bold": True, "bg_color": GREEN, "font_color": WHITE,
                                 "num_format": "#,##0.00", "align": "right", "border": 1})
    head_fmt    = wb.add_format({"bold": True, "bg_color": NAVY, "font_color": WHITE,
                                 "align": "center", "border": 1})

    ws.set_column(0, 0, 32)
    ws.set_column(1, 1, 22)

    # Header
    ws.merge_range(0, 0, 0, 1, f"تقرير صافي قيمة الأصول — {result['fund_name']}", title_fmt)
    ws.set_row(0, 32)
    ws.write(1, 0, "تاريخ التقييم", label_fmt); ws.write(1, 1, result["valuation_date"], label_fmt)
    ws.write(2, 0, "مستوى IFRS 13", label_fmt); ws.write(2, 1, result["ifrs_level_label"], label_fmt)

    # Assets
    r = 4
    ws.merge_range(r, 0, r, 1, "جانب الأصول (Assets)", section_fmt); r += 1
    for label, key in [
        ("القيمة العادلة للعقارات", "real_estate_fair_value"),
        ("النقد وما في حكمه",        "cash_and_equiv"),
        ("المدينون والإيجارات المستحقة", "receivables"),
        ("أصول أخرى",                "other_assets"),
        ("إجمالي قيمة الأصول (GAV)", "gross_asset_value"),
    ]:
        ws.write(r, 0, label, label_fmt)
        ws.write_number(r, 1, float(result[key]), val_fmt)
        r += 1

    # Liabilities
    r += 1
    ws.merge_range(r, 0, r, 1, "جانب الالتزامات (Liabilities)", section_fmt); r += 1
    for label, key in [
        ("القروض البنكية",                "loans"),
        ("مصروفات مستحقة",                "accrued_expenses"),
        ("توزيعات مُعتمدة غير مدفوعة",   "distributions_payable"),
        ("ضريبة مؤجلة",                   "deferred_tax"),
        ("التزامات أخرى",                 "other_liabilities"),
        ("إجمالي الالتزامات",             "total_liabilities"),
    ]:
        ws.write(r, 0, label, label_fmt)
        ws.write_number(r, 1, float(result[key]), val_fmt)
        r += 1

    # NAV
    r += 1
    ws.merge_range(r, 0, r, 1, "صافي قيمة الأصول (NAV)", section_fmt); r += 1
    ws.write(r, 0, "NAV (إجمالي)", label_fmt);                  ws.write_number(r, 1, float(result["nav"]), nav_fmt); r += 1
    ws.write(r, 0, "عدد الوحدات",  label_fmt);                  ws.write_number(r, 1, float(result["units_outstanding"]), val_fmt); r += 1
    ws.write(r, 0, "NAV لكل وحدة (NAV per Unit)", label_fmt);   ws.write_number(r, 1, float(result["nav_per_unit"]), nav_fmt); r += 1

    # Portfolio metrics
    r += 1
    ws.merge_range(r, 0, r, 1, "مؤشرات المحفظة", section_fmt); r += 1
    ws.write(r, 0, "Cap Rate المرجح",     label_fmt); ws.write_number(r, 1, float(result["weighted_cap_rate"]), pct_fmt); r += 1
    ws.write(r, 0, "نسبة LTV",            label_fmt); ws.write_number(r, 1, float(result["ltv"]), pct_fmt); r += 1
    ws.write(r, 0, "Gearing Ratio",       label_fmt); ws.write_number(r, 1, float(result["gearing_ratio"]), pct_fmt); r += 1
    ws.write(r, 0, "تقييم الصحة المالية", label_fmt); ws.write(r, 1, f"{result['health_score']:.1f} — {result['health_label']}", val_fmt); r += 1

    # Per-asset breakdown
    r += 2
    ws.merge_range(r, 0, r, 5, "تفصيل الأصول داخل المحفظة", section_fmt); r += 1
    ws.set_column(2, 5, 18)
    headers = ["الموقع", "النوع", "المساحة (م²)", "Cap Rate %", "القيمة العادلة", "اسم الأصل"]
    for col, h in enumerate(headers):
        ws.write(r, col, h, head_fmt)
    r += 1
    for a in result.get("assets", []):
        ws.write(r, 0, a.get("location", ""), label_fmt)
        ws.write(r, 1, a.get("property_type", ""), label_fmt)
        ws.write_number(r, 2, float(a.get("area", 0)), val_fmt)
        ws.write_number(r, 3, float(a.get("cap_rate_pct", 0)) / 100.0, pct_fmt)
        ws.write_number(r, 4, float(a.get("fair_value", 0)), val_fmt)
        ws.write(r, 5, a.get("asset_name", ""), label_fmt)
        r += 1

    # IFRS disclosure footer
    r += 2
    discl_fmt = wb.add_format({"italic": True, "bg_color": GREY, "align": "right", "text_wrap": True, "border": 1})
    ws.merge_range(r, 0, r, 5, result["ifrs_disclosure"], discl_fmt)
    ws.set_row(r, 38)

    wb.close()
    return filepath
