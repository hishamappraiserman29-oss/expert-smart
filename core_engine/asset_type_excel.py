"""
asset_type_excel.py
====================
Supplementary single-workbook Excel writer for specialized asset valuators.

Adds one stand-alone .xlsx per specialized asset type (intangible / partial /
under-construction / quarry) without touching the main template that
write_to_excel_template uses.

Public API:
    write_asset_type_excel(asset_result, output_dir) -> Optional[str]
"""

from __future__ import annotations
import os
from datetime import datetime
from typing import Any, Dict, Optional


_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DEF_OUT = os.path.join(_BASE_DIR, "outputs", "reports")


def _ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def _build_workbook(filepath: str, title: str,
                    rows: list, footnote: str = "") -> str:
    import xlsxwriter  # type: ignore
    wb = xlsxwriter.Workbook(filepath)
    ws = wb.add_worksheet(title[:31])
    ws.right_to_left()

    NAVY, GOLD, WHITE, LIGHT, GREEN, GREY = (
        "#1F3864", "#C9A227", "#FFFFFF", "#EAF0FB", "#1E8449", "#F2F2F2"
    )

    title_fmt   = wb.add_format({"bold": True, "font_size": 16, "bg_color": NAVY,
                                 "font_color": WHITE, "align": "center", "valign": "vcenter"})
    label_fmt   = wb.add_format({"bold": True, "bg_color": LIGHT, "align": "right", "border": 1})
    val_fmt     = wb.add_format({"align": "right", "border": 1})
    num_fmt     = wb.add_format({"num_format": "#,##0.00", "align": "right", "border": 1})
    pct_fmt     = wb.add_format({"num_format": "0.00%", "align": "right", "border": 1})
    final_fmt   = wb.add_format({"bold": True, "bg_color": GREEN, "font_color": WHITE,
                                 "num_format": "#,##0.00", "align": "right", "border": 1})
    note_fmt    = wb.add_format({"italic": True, "bg_color": GREY, "align": "right",
                                 "text_wrap": True, "border": 1})

    ws.set_column(0, 0, 40)
    ws.set_column(1, 1, 24)

    ws.merge_range(0, 0, 0, 1, title, title_fmt)
    ws.set_row(0, 32)

    r = 2
    for label, value, kind in rows:
        ws.write(r, 0, label, label_fmt)
        if value is None:
            ws.write(r, 1, "—", val_fmt)
        elif kind == "money":
            ws.write_number(r, 1, float(value), final_fmt if "المعتمدة" in label or "النهائية" in label else num_fmt)
        elif kind == "pct":
            ws.write_number(r, 1, float(value), pct_fmt)
        elif kind == "num":
            ws.write_number(r, 1, float(value), num_fmt)
        else:
            ws.write(r, 1, str(value), val_fmt)
        r += 1

    if footnote:
        r += 1
        ws.merge_range(r, 0, r, 1, footnote, note_fmt)
        ws.set_row(r, 38)

    wb.close()
    return filepath


def _rows_intangible(r: Dict[str, Any]) -> list:
    return [
        ("نوع التقييم",                              "أصل معنوي — MPEEM",                                 "text"),
        ("المعيار المُطبَّق",                        r.get("standards", "IFRS 13 / IVS 210"),             "text"),
        ("الإيراد السنوي (ج.م)",                     r.get("annual_revenue"),                              "money"),
        ("نسبة العائد المنسوبة للأصل المعنوي",      r.get("intangible_attribution_pct"),                  "pct"),
        ("Contributory Asset Charge",                r.get("contributory_asset_charge_pct"),               "pct"),
        ("العائد الإضافي السنوي (ج.م)",              r.get("annual_excess_earnings"),                      "money"),
        ("عمر الحق المعنوي (سنوات)",                r.get("license_term_years"),                          "num"),
        ("معدل الخصم",                                r.get("discount_rate"),                               "pct"),
        ("القيمة الحالية للعائدات (ج.م)",            r.get("pv_excess_earnings"),                          "money"),
        ("ميزة الإطفاء الضريبي (TAB)",              r.get("tax_amortization_benefit_pct"),                "pct"),
        ("القيمة المعتمدة للأصل المعنوي (ج.م)",      r.get("reconciled_value"),                            "money"),
    ]


def _rows_partial(r: Dict[str, Any]) -> list:
    return [
        ("نوع التقييم",                              "ملكية جزئية — Pro-rata × DLOC × DLOM",              "text"),
        ("المعيار المُطبَّق",                        r.get("standards", "IVS 200 / Egyptian Civil Code"),  "text"),
        ("القيمة السوقية للملكية الكاملة (ج.م)",     r.get("total_property_value"),                        "money"),
        ("نسبة الملكية الجزئية",                     r.get("ownership_pct"),                               "pct"),
        ("صفة الحصة",                                "حصة مسيطرة" if r.get("is_controlling") else "حصة أقلية", "text"),
        ("القيمة النسبية (Pro-rata) (ج.م)",          r.get("pro_rata_value"),                              "money"),
        ("DLOC — خصم عدم السيطرة",                  r.get("dloc_pct"),                                    "pct"),
        ("قيمة بعد DLOC (ج.م)",                      r.get("value_after_dloc"),                            "money"),
        ("DLOM — خصم عدم القابلية للتسويق",         r.get("dlom_pct"),                                    "pct"),
        ("القيمة المعتمدة للحصة الجزئية (ج.م)",      r.get("reconciled_value"),                            "money"),
        ("النسبة الفعلية من القيمة الكاملة",         r.get("implied_per_unit_pct"),                        "pct"),
    ]


def _rows_under_construction(r: Dict[str, Any]) -> list:
    rows = [
        ("نوع التقييم",                              "استثمار تحت الإنشاء — Cost-to-date + Risk",         "text"),
        ("المعيار المُطبَّق",                        r.get("standards", "IAS 16 / IFRS 13 / IVS 230"),     "text"),
        ("التكلفة الكاملة المخططة (ج.م)",            r.get("planned_total_cost"),                          "money"),
        ("نسبة الإنجاز",                              r.get("completion_pct"),                              "pct"),
        ("التكلفة المنفقة حتى الآن (ج.م)",          r.get("cost_incurred"),                               "money"),
        ("نسبة مخاطرة الإنشاء",                      r.get("construction_risk_pct"),                       "pct"),
        ("قيمة المخاطرة (ج.م)",                      r.get("construction_risk_amount"),                    "money"),
        ("Method A — قيمة (ج.م)",                    r.get("value_method_a"),                              "money"),
    ]
    if r.get("value_method_b") is not None:
        rows.extend([
            ("القيمة السوقية المخططة بعد الاكتمال (ج.م)", r.get("planned_market_value"),                     "money"),
            ("تكلفة الإكمال المتبقية (ج.م)",          r.get("remaining_cost_to_complete"),                  "money"),
            ("هامش ربح المطور",                       r.get("developer_profit_pct"),                        "pct"),
            ("قيمة هامش الربح (ج.م)",                r.get("developer_profit_amount"),                     "money"),
            ("الأشهر المتبقية للاكتمال",              r.get("months_to_completion"),                        "num"),
            ("معدل الخصم",                             r.get("discount_rate"),                               "pct"),
            ("معامل القيمة الحالية",                  r.get("pv_factor"),                                   "num"),
            ("Method B — قيمة (ج.م)",                 r.get("value_method_b"),                              "money"),
        ])
    rows.extend([
        ("التوفيق المرجح",                            r.get("weighting"),                                   "text"),
        ("القيمة المعتمدة لاستثمار تحت الإنشاء (ج.م)", r.get("reconciled_value"),                          "money"),
    ])
    return rows


def _rows_quarry(r: Dict[str, Any]) -> list:
    return [
        ("نوع التقييم",                          "منجم — DCF على الاحتياطي المؤكد",            "text"),
        ("المعيار المُطبَّق",                    r.get("standards", "IVS 220 / SAMREC / JORC"),  "text"),
        ("الاحتياطي المؤكد (طن)",                r.get("reserve_tons"),                          "num"),
        ("الاستخراج السنوي (طن)",                r.get("annual_extraction"),                     "num"),
        ("سعر الطن الصافي (ج.م)",                r.get("price_per_ton"),                         "money"),
        ("العمر الإنتاجي المتوقع (سنة)",         r.get("life_years"),                            "num"),
        ("الإيراد السنوي (ج.م)",                 r.get("annual_revenue"),                        "money"),
        ("صافي التدفق النقدي السنوي (ج.م)",     r.get("annual_ncf"),                            "money"),
        ("القيمة الحالية للتدفقات (ج.م)",        r.get("pv_cash_flows"),                         "money"),
        ("القيمة الحالية لإعادة التأهيل (ج.م)",  r.get("pv_rehab_cost"),                         "money"),
        ("القيمة الحالية للأرض المتبقية (ج.م)",  r.get("pv_land_residual"),                      "money"),
        ("معدل الخصم",                            r.get("discount_rate"),                         "pct"),
        ("قيمة المنجم المعتمدة (ج.م)",          r.get("reconciled_value"),                      "money"),
        ("القيمة لكل طن احتياطي (ج.م)",          r.get("value_per_ton_reserve"),                 "money"),
    ]


_DISPATCH = {
    "intangible":         ("تقرير تقييم أصل معنوي — MPEEM",                _rows_intangible,
                           "وفق IFRS 13 / IVS 210. يخضع لاختبار الهبوط الدوري وفق IAS 36."),
    "partial_interest":   ("تقرير تقييم ملكية جزئية — IVS 200",            _rows_partial,
                           "وفق IVS 200 والقانون المدني المصري (م.825–م.850 الشيوع). الخصومات تعكس عدم السيطرة وضعف القابلية للتسويق."),
    "under_construction": ("تقرير تقييم استثمار تحت الإنشاء",              _rows_under_construction,
                           "وفق IAS 16 §22 / IFRS 13 / IVS 230. نسبة المخاطرة تعكس مخاطر التأخير وتجاوز الكلفة."),
    "quarry":             ("تقرير تقييم منجم — IVS 220",                   _rows_quarry,
                           "وفق IVS 220 ومعايير SAMREC / JORC. تكلفة إعادة التأهيل البيئي إلزامية وفق قانون البيئة المصري 4/1994."),
}


def write_asset_type_excel(asset_result: Dict[str, Any], output_dir: str = "") -> Optional[str]:
    """يُولِّد ملف Excel مكمِّل لنوع الأصل المتخصص. يُرجع المسار أو None."""
    if not isinstance(asset_result, dict):
        return None
    at = (asset_result.get("asset_type") or "").strip().lower()
    if at not in _DISPATCH:
        return None
    title, rows_fn, footnote = _DISPATCH[at]

    out_dir = _ensure_dir(output_dir or _DEF_OUT)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(out_dir, f"asset_{at}_{timestamp}.xlsx")
    return _build_workbook(filepath, title, rows_fn(asset_result), footnote)
