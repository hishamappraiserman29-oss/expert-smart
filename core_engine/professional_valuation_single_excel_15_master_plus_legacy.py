"""
professional_valuation_single_excel_15_master_plus_legacy.py

ملف Excel إداري واحد: 15 ورقة رئيسية مدمجة + أوراق أرشيف الإصدارات القديمة
+ 3 تقارير PDF عربية (تقليدي / تفصيلي / احترافي)

advisory_only=True | not_real_training=True | arabic_primary=True
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from professional_valuation_arabic_report_examples import (
    ADJUSTED_PRICES_PER_SQM, ADJUSTMENTS_AR, ADVISORY_NOTE_AR,
    AVM_AR, COMPARABLES_AR, COST_AR, DATA_INPUTS_AR,
    DCF_10YEAR_AR, DCF_5YEAR_AR, HBU_AR, INCOME_AR,
    INDICATED_MARKET_VALUE, INDICATED_MARKET_VALUE_PER_SQM,
    METHOD_SELECTION_AR, PROBABILITY_WEIGHTED_VALUE,
    RECONCILIATION_AR, RECONCILIATION_SCORECARD_AR,
    RISKS_AR, SCENARIOS_AR, SENSITIVITY_MATRIX_AR,
    STANDARDS_AR, SUBJECT_AR,
)

_CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
_NOW = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
_INVALID_SHEET_CHARS = re.compile(r"[\\/?*\[\]:]")

MASTER_SHEET_NAMES = [
    "Cover", "Data Quality", "Property", "HBU Analysis", "Comparables",
    "Income Approach", "Cost Approach", "AVM Reference", "Scenarios",
    "Sensitivity Matrix", "Reconciliation", "Risk Register",
    "Standards Matrix", "Source Registry", "Admin Notes",
]
MASTER_SHEET_ARABIC = {
    "Cover":            "صفحة الغلاف",
    "Data Quality":     "جودة البيانات واكتمالها",
    "Property":         "بيانات العقار الأساسية",
    "HBU Analysis":     "تحليل أعلى وأفضل استخدام",
    "Comparables":      "المقارنات السوقية ومصفوفة التسويات",
    "Income Approach":  "أسلوب الدخل والتدفقات النقدية",
    "Cost Approach":    "أسلوب التكلفة والإهلاك",
    "AVM Reference":    "مؤشر التقييم الآلي المساعد",
    "Scenarios":        "تحليل السيناريوهات",
    "Sensitivity Matrix":"مصفوفة الحساسية المتقدمة",
    "Reconciliation":   "التوفيق والترجيح النهائي",
    "Risk Register":    "سجل المخاطر",
    "Standards Matrix": "مصفوفة المعايير والإفصاحات",
    "Source Registry":  "سجل مصادر البيانات",
    "Admin Notes":      "ملاحظات الإدارة والاعتماد",
}

# ── openpyxl style helpers ────────────────────────────────────────────────────
_HDR_FONT   = Font(bold=True, color="FFFFFF", size=11, name="Arial")
_HDR_FILL   = PatternFill("solid", fgColor="1A3A5C")
_SUB_FONT   = Font(bold=True, color="1A3A5C", size=10, name="Arial")
_SUB_FILL   = PatternFill("solid", fgColor="D4E6F1")
_LBL_FONT   = Font(bold=True, size=10, name="Arial")
_LBL_FILL   = PatternFill("solid", fgColor="EBF5FB")
_WARN_FILL  = PatternFill("solid", fgColor="FFF3CD")
_WARN_FONT  = Font(bold=True, color="856404", size=10, name="Arial")
_OK_FONT    = Font(bold=True, color="1E7E34", size=10, name="Arial")
_NOK_FONT   = Font(bold=True, color="721C24", size=10, name="Arial")
_RTL        = Alignment(horizontal="right", vertical="center", wrap_text=True)
_CTR        = Alignment(horizontal="center", vertical="center", wrap_text=True)
_THIN       = Border(
    left=Side(style="thin", color="AAAAAA"), right=Side(style="thin", color="AAAAAA"),
    top=Side(style="thin", color="AAAAAA"),  bottom=Side(style="thin", color="AAAAAA"),
)


def _w(ws, row: int, col: int, value=None, *, bold=False, fill=None,
       fnt=None, align=None, bdr=None, fmt=None) -> openpyxl.cell.Cell:
    c = ws.cell(row=row, column=col)
    if value is not None:
        c.value = value
    c.font  = fnt  if fnt  else (Font(bold=bold, size=10, name="Arial"))
    if fill:   c.fill      = fill
    if align:  c.alignment = align
    if bdr:    c.border    = bdr
    if fmt:    c.number_format = fmt
    return c


def _hdr(ws, row: int, col: int, text: str) -> None:
    _w(ws, row, col, text, fnt=_HDR_FONT, fill=_HDR_FILL, align=_RTL, bdr=_THIN)


def _sub(ws, row: int, col: int, text: str) -> None:
    _w(ws, row, col, text, fnt=_SUB_FONT, fill=_SUB_FILL, align=_RTL, bdr=_THIN)


def _lbl(ws, row: int, col: int, text: str) -> None:
    _w(ws, row, col, text, fnt=_LBL_FONT, fill=_LBL_FILL, align=_RTL, bdr=_THIN)


def _val(ws, row: int, col: int, value, fmt: Optional[str] = None) -> None:
    _w(ws, row, col, value, align=_RTL, bdr=_THIN, fmt=fmt)


def _init_ws(ws, title_ar: str, *, cols: list[int] | None = None) -> None:
    ws.sheet_view.rightToLeft = True
    ws.sheet_properties.tabColor = "1A3A5C"
    ws.row_dimensions[1].height = 26
    # Title across first N columns
    n = len(cols) if cols else 4
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=n)
    _w(ws, 1, 1, title_ar, fnt=Font(bold=True, size=14, color="FFFFFF", name="Arial"),
       fill=_HDR_FILL, align=_CTR, bdr=_THIN)
    if cols:
        for i, w in enumerate(cols, 1):
            ws.column_dimensions[get_column_letter(i)].width = w


# ── Master sheet builders ─────────────────────────────────────────────────────

def _add_cover(ws: openpyxl.worksheet.worksheet.Worksheet) -> None:
    _init_ws(ws, "صفحة الغلاف — ملف Excel الإداري الرئيسي", cols=[35, 30, 20, 20])
    ws.row_dimensions[2].height = 14
    r = 3
    pairs = [
        ("اسم التقرير",            "تقرير التقييم المهني المتكامل"),
        ("نوع الأصل",              SUBJECT_AR["property_type"]),
        ("موقع الأصل",             SUBJECT_AR["property_address"]),
        ("تاريخ التقييم",          SUBJECT_AR["valuation_date"]),
        ("تاريخ التقرير",          _NOW[:10]),
        ("الغرض من التقييم",       SUBJECT_AR["purpose"]),
        ("المستخدم المقصود",       SUBJECT_AR["client"]),
        ("أساس القيمة",            SUBJECT_AR["basis_of_value"]),
        ("مستوى التقرير",          "تقليدي / تفصيلي / احترافي"),
        ("حالة التقرير",           "مسودة استرشادية — advisory_only=True"),
        ("العملة",                 SUBJECT_AR["currency"]),
        ("تاريخ الإنشاء (UTC)",   _NOW),
    ]
    for label, value in pairs:
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=2)
        _lbl(ws, r, 1, label)
        ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=4)
        _val(ws, r, 3, value)
        ws.row_dimensions[r].height = 18
        r += 1
    r += 1
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
    _w(ws, r, 1,
       "تنبيه: هذا الملف داخلي للخبير أو الإدارة ولا يُرسل للمستخدم. المستخدم يستلم تقارير PDF فقط.",
       fnt=_WARN_FONT, fill=_WARN_FILL, align=_RTL)
    r += 1
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
    _w(ws, r, 1,
       f"advisory_only=True | not_real_training=True | certification_ready=False | {ADVISORY_NOTE_AR}",
       fnt=Font(italic=True, size=9, color="666666", name="Arial"), align=_RTL)


def _add_data_quality(ws) -> None:
    _init_ws(ws, "جودة البيانات واكتمالها", cols=[40, 20, 30, 20])
    r = 3
    _sub(ws, r, 1, "مؤشر الاكتمال")
    _val(ws, r, 2, "نسبة الاكتمال %"); _val(ws, r, 3, 87.5)
    r += 1
    _sub(ws, r, 1, "البيانات الإلزامية المكتملة")
    _val(ws, r, 2, "عدد الحقول"); _val(ws, r, 3, 7)
    r += 1
    _sub(ws, r, 1, "البيانات الإلزامية الناقصة")
    _val(ws, r, 2, "عدد الحقول"); _val(ws, r, 3, 1)
    r += 1; r += 1
    for col, txt in enumerate(["الحقل", "الحالة", "ملاحظة"], 1):
        _hdr(ws, r, col, txt)
    r += 1
    for item in DATA_INPUTS_AR:
        _lbl(ws, r, 1, item["field"])
        status = item["status"]
        c = ws.cell(row=r, column=2)
        c.value = status
        c.font = _OK_FONT if "مكتمل" in status else _WARN_FONT
        c.alignment = _RTL; c.border = _THIN
        _val(ws, r, 3, "بيانات توضيحية")
        r += 1
    r += 1
    for col, txt in enumerate(["درجة جودة البيانات", "جاهزية التقرير", "إصدار مسودة؟", "استنتاج نهائي؟"], 1):
        _lbl(ws, r, col, txt)
    r += 1
    for col, val in enumerate(["B — جيدة", "جاهز للمراجعة", "نعم", "بعد مراجعة الخبير"], 1):
        _val(ws, r, col, val)


def _add_property(ws) -> None:
    _init_ws(ws, "بيانات العقار الأساسية", cols=[35, 30, 25, 15])
    r = 3
    fields = [
        ("رقم الطلب",              SUBJECT_AR["request_id"]),
        ("نوع الأصل",              SUBJECT_AR["property_type"]),
        ("الموقع الكامل",          SUBJECT_AR["property_address"]),
        ("رقم القطعة",             SUBJECT_AR["plot_number"]),
        ("الحي",                   SUBJECT_AR["district"]),
        ("المدينة",                SUBJECT_AR["city"]),
        ("المساحة الأرضية (م²)",   COST_AR["land_area_m2"]),
        ("المساحة البنائية (م²)",  SUBJECT_AR["gross_floor_area_m2"]),
        ("عدد الغرف",              SUBJECT_AR["bedrooms"]),
        ("عدد دورات المياه",       SUBJECT_AR["bathrooms"]),
        ("المواقف",                SUBJECT_AR["parking"]),
        ("الطابق",                 SUBJECT_AR["floor"]),
        ("عمر المبنى (سنة)",       SUBJECT_AR["age_years"]),
        ("الاستخدام الحالي",       "سكني — R-2"),
        ("حالة الإشغال",           "مشغول / سكني"),
        ("حالة الملكية",           SUBJECT_AR["tenure"]),
        ("حالة الترخيص",           SUBJECT_AR["zoning"]),
        ("الحالة الإنشائية",       "جيدة"),
        ("الإحداثيات",             SUBJECT_AR["coordinates"]),
        ("الغرض من التقييم",       SUBJECT_AR["purpose"]),
        ("أساس القيمة",            SUBJECT_AR["basis_of_value"]),
    ]
    for label, value in fields:
        _lbl(ws, r, 1, label); _val(ws, r, 2, value)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=4)
        ws.row_dimensions[r].height = 16
        r += 1
    r += 1
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
    _w(ws, r, 1, ADVISORY_NOTE_AR, fnt=Font(italic=True, size=9, color="666666", name="Arial"), align=_RTL)


def _add_hbu(ws) -> None:
    _init_ws(ws, "تحليل أعلى وأفضل استخدام — HBU Analysis", cols=[35, 35, 15, 15])
    r = 3
    for col, txt in enumerate(["اختبار HBU", "النتيجة", "الحالة"], 1):
        _hdr(ws, r, col, txt)
    r += 1
    tests = [
        ("الاختبار الفيزيائي / Physically Possible",    HBU_AR["physically_possible"],  "مطابق ✓"),
        ("الاختبار القانوني / Legally Permissible",      HBU_AR["legally_permissible"],  "مطابق ✓"),
        ("الاختبار المالي / Financially Feasible",       HBU_AR["financially_feasible"], "مطابق ✓"),
        ("أعلى إنتاجية / Maximally Productive",         HBU_AR["maximally_productive"], "مطابق ✓"),
    ]
    for test_name, result, status in tests:
        _lbl(ws, r, 1, test_name); _val(ws, r, 2, result)
        c = ws.cell(row=r, column=3); c.value = status
        c.font = _OK_FONT; c.alignment = _RTL; c.border = _THIN
        r += 1
    r += 1
    _sub(ws, r, 1, "المؤشرات الرقمية"); r += 1
    numeric = [
        ("تكلفة التطوير (توضيحي SAR)",     "غير قابل للتطبيق — مبنى قائم"),
        ("الإيراد المتوقع (SAR/سنة)",       INCOME_AR["gross_market_rent_annual"]),
        ("صافي الدخل التشغيلي (SAR/سنة)",   INCOME_AR["net_operating_income"]),
        ("نسبة العائد المطلوب %",            INCOME_AR["cap_rate_pct"]),
        ("درجة الجدوى (1-10)",              8),
        ("درجة المخاطرة (1-10)",            3),
        ("السيناريو المختار",               "استخدام سكني حالي"),
        ("خلاصة HBU",                      HBU_AR["conclusion"]),
    ]
    for label, value in numeric:
        _lbl(ws, r, 1, label)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=4)
        _val(ws, r, 2, value)
        r += 1


def _add_comparables(ws) -> None:
    _init_ws(ws, "المقارنات السوقية ومصفوفة التسويات", cols=[28, 20, 14, 14, 14, 14, 14, 14, 14, 14])
    r = 3
    comp_hdrs = ["المقارنة", "العنوان", "المساحة م²", "السعر SAR",
                 "SAR/م²", "العمر", "الطابق", "الموقف", "الحالة", "تاريخ البيع"]
    for c, h in enumerate(comp_hdrs, 1):
        _hdr(ws, r, c, h)
    r += 1
    for comp in COMPARABLES_AR:
        row_vals = [comp["id"], comp["address"], comp["area_m2"], comp["price_sar"],
                    comp["price_per_sqm"], comp["age_years"], comp["floor"],
                    comp["parking"], comp["condition"], comp["sale_date"]]
        for c, v in enumerate(row_vals, 1):
            _val(ws, r, c, v)
        r += 1
    r += 1
    _sub(ws, r, 1, "مصفوفة التسويات"); r += 1
    adj_hdrs = ["عنصر التسوية"] + [comp["id"] for comp in COMPARABLES_AR]
    for c, h in enumerate(adj_hdrs, 1):
        _hdr(ws, r, c, h)
    r += 1
    for key, adj in ADJUSTMENTS_AR.items():
        _lbl(ws, r, 1, adj["label"])
        for c, v in enumerate(adj["values"], 2):
            _val(ws, r, c, v, fmt="0.0%")
        r += 1
    _lbl(ws, r, 1, "السعر المعدل SAR/م²")
    for c, v in enumerate(ADJUSTED_PRICES_PER_SQM, 2):
        _val(ws, r, c, v)
    r += 1; r += 1
    _sub(ws, r, 1, "مؤشر القيمة السوقية"); r += 1
    _lbl(ws, r, 1, "متوسط السعر المعدل SAR/م²"); _val(ws, r, 2, INDICATED_MARKET_VALUE_PER_SQM)
    r += 1
    _lbl(ws, r, 1, "المساحة البنائية م²"); _val(ws, r, 2, SUBJECT_AR["gross_floor_area_m2"])
    r += 1
    _lbl(ws, r, 1, "مؤشر القيمة السوقية SAR"); _val(ws, r, 2, INDICATED_MARKET_VALUE, fmt="#,##0")


def _add_income(ws) -> None:
    _init_ws(ws, "أسلوب الدخل والتدفقات النقدية", cols=[38, 20, 16, 16, 16, 16, 16, 16, 16, 16, 16])
    r = 3
    _sub(ws, r, 1, "قسم 1: الدخل والرسملة المباشرة"); r += 1
    inc_rows = [
        ("الإيجار السوقي السنوي الإجمالي SAR",    INCOME_AR["gross_market_rent_annual"]),
        ("نسبة الشغور %",                          INCOME_AR["vacancy_rate_pct"]),
        ("خصم الشغور SAR",                         INCOME_AR["vacancy_deduction"]),
        ("الدخل الإجمالي الفعلي SAR",              INCOME_AR["effective_gross_income"]),
        ("رسوم الإدارة SAR",                       INCOME_AR["management_fee"]),
        ("الصيانة السنوية SAR",                    INCOME_AR["maintenance_annual"]),
        ("التأمين السنوي SAR",                     INCOME_AR["insurance_annual"]),
        ("إجمالي المصروفات التشغيلية SAR",          INCOME_AR["total_opex"]),
        ("صافي الدخل التشغيلي NOI SAR",            INCOME_AR["net_operating_income"]),
        ("معدل الرسملة %",                         INCOME_AR["cap_rate_pct"]),
        ("مؤشر القيمة بطريقة الدخل SAR",           INCOME_AR["indicated_value_income"]),
    ]
    for label, value in inc_rows:
        _lbl(ws, r, 1, label)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=4)
        _val(ws, r, 2, value, fmt="#,##0")
        r += 1
    r += 1
    _sub(ws, r, 1, "قسم 2: DCF — التدفقات النقدية المخصومة (5 سنوات)"); r += 1
    for col, h in enumerate(["البيان", "السنة 1", "السنة 2", "السنة 3", "السنة 4", "السنة 5"], 1):
        _hdr(ws, r, col, h)
    r += 1
    _lbl(ws, r, 1, "التدفق النقدي SAR")
    for c, v in enumerate(DCF_5YEAR_AR["year_cash_flows"], 2):
        _val(ws, r, c, v, fmt="#,##0")
    r += 1
    dcf5_rows = [
        ("معدل النمو السنوي %",     DCF_5YEAR_AR["growth_rate_pct"]),
        ("معدل الرسملة الطرفية %",  DCF_5YEAR_AR["terminal_cap_rate_pct"]),
        ("معدل الخصم %",            DCF_5YEAR_AR["discount_rate_pct"]),
        ("القيمة الطرفية SAR",      DCF_5YEAR_AR["terminal_value_year5"]),
        ("NPV / مؤشر DCF (5سنة) SAR", DCF_5YEAR_AR["dcf_indicated_value"]),
    ]
    for label, value in dcf5_rows:
        _lbl(ws, r, 1, label)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=6)
        _val(ws, r, 2, value, fmt="#,##0")
        r += 1
    r += 1
    _sub(ws, r, 1, "قسم 3: DCF — التدفقات النقدية المخصومة (10 سنوات)"); r += 1
    dcf10_rows = [
        ("فترة الاحتجاز (سنة)",          DCF_10YEAR_AR["hold_period_years"]),
        ("صافي الدخل الأولي SAR",         DCF_10YEAR_AR["initial_noi"]),
        ("معدل النمو %",                  DCF_10YEAR_AR["growth_rate_pct"]),
        ("معدل الرسملة الطرفية %",        DCF_10YEAR_AR["terminal_cap_rate_pct"]),
        ("معدل الخصم %",                  DCF_10YEAR_AR["discount_rate_pct"]),
        ("NPV / مؤشر DCF (10سنة) SAR",   DCF_10YEAR_AR["dcf_indicated_value"]),
    ]
    for label, value in dcf10_rows:
        _lbl(ws, r, 1, label)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=6)
        _val(ws, r, 2, value, fmt="#,##0")
        r += 1


def _add_cost(ws) -> None:
    _init_ws(ws, "أسلوب التكلفة والإهلاك", cols=[38, 22, 16, 16])
    r = 3
    cost_rows = [
        ("مساحة الأرض م²",                       COST_AR["land_area_m2"]),
        ("قيمة الأرض SAR/م²",                    COST_AR["land_value_per_sqm"]),
        ("قيمة الأرض الإجمالية SAR",              COST_AR["land_value"]),
        ("المساحة البنائية الإجمالية م²",          COST_AR["gross_floor_area_m2"]),
        ("تكلفة الإحلال الجديدة SAR/م²",          COST_AR["replacement_cost_new_per_sqm"]),
        ("تكلفة الإحلال الجديدة الإجمالية SAR",   COST_AR["replacement_cost_new"]),
        ("العمر الاقتصادي (سنة)",                 COST_AR["effective_life_years"]),
        ("العمر الفعلي (سنة)",                    COST_AR["age_years"]),
        ("الإهلاك المادي %",                      COST_AR["physical_depreciation_pct"]),
        ("الإهلاك المادي SAR",                    COST_AR["physical_depreciation"]),
        ("الإهلاك الوظيفي SAR",                   COST_AR["functional_obsolescence"]),
        ("الإهلاك الخارجي SAR",                   COST_AR["economic_obsolescence"]),
        ("إجمالي الإهلاك SAR",                    COST_AR["physical_depreciation"]),
        ("قيمة الإحلال المستهلكة SAR",             COST_AR["depreciated_improvement_value"]),
        ("مؤشر القيمة بأسلوب التكلفة SAR",        COST_AR["indicated_value_cost"]),
    ]
    for label, value in cost_rows:
        _lbl(ws, r, 1, label)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=4)
        _val(ws, r, 2, value, fmt="#,##0")
        r += 1
    r += 1
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
    _w(ws, r, 1, ADVISORY_NOTE_AR, fnt=Font(italic=True, size=9, color="666666", name="Arial"), align=_RTL)


def _add_avm(ws) -> None:
    _init_ws(ws, "مؤشر التقييم الآلي المساعد — AVM Reference", cols=[38, 30, 16, 16])
    r = 3
    avm_rows = [
        ("مزود AVM",              AVM_AR["avm_provider"]),
        ("مصدر البيانات",         "قاعدة بيانات معاملات السوق (توضيحي)"),
        ("عدد المقارنات",         AVM_AR["comparable_count"]),
        ("نطاق الثقة",            "± 8% من القيمة المؤشرة"),
        ("درجة الثقة",            AVM_AR["confidence_level"]),
        ("معامل الثقة (0-1)",     AVM_AR["confidence_score"]),
        ("حداثة البيانات",        AVM_AR["data_freshness"]),
        ("مؤشر القيمة الآلي SAR", AVM_AR["avm_indicated_value"]),
        ("حدود الاعتماد",         "مؤشر مساعد فقط — لا يُعتمد كنتيجة نهائية"),
        ("سبب القيد",             AVM_AR["note"]),
        ("ضرورة مراجعة الخبير",   "نعم — إلزامية قبل إصدار أي نتيجة نهائية"),
    ]
    for label, value in avm_rows:
        _lbl(ws, r, 1, label)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=4)
        _val(ws, r, 2, value)
        r += 1
    r += 1
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
    _w(ws, r, 1,
       "تحذير: مؤشر AVM لا يُعتمد كنتيجة نهائية ولا يُغني عن تقييم الخبير المعتمد.",
       fnt=_WARN_FONT, fill=_WARN_FILL, align=_RTL)


def _add_scenarios(ws) -> None:
    _init_ws(ws, "تحليل السيناريوهات", cols=[28, 18, 16, 18, 18, 16, 18])
    r = 3
    hdrs = ["السيناريو", "معدل النمو %", "معدل الرسملة %", "معدل الخصم %",
            "قيمة DCF SAR", "الاحتمال %", "القيمة المرجحة SAR"]
    for c, h in enumerate(hdrs, 1):
        _hdr(ws, r, c, h)
    r += 1
    probs = [0.20, 0.60, 0.20]
    for s, p in zip(SCENARIOS_AR, probs):
        weighted = int(s["dcf_value"] * p)
        vals = [s["scenario"], s["growth_rate"], s["cap_rate"],
                s["discount_rate"], s["dcf_value"], p * 100, weighted]
        for c, v in enumerate(vals, 1):
            _val(ws, r, c, v, fmt="#,##0" if c in (5, 7) else None)
        r += 1
    r += 1
    _lbl(ws, r, 1, "القيمة المرجحة بالاحتمالات SAR")
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=7)
    _val(ws, r, 2, PROBABILITY_WEIGHTED_VALUE, fmt="#,##0")
    r += 1
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=7)
    _w(ws, r, 1, ADVISORY_NOTE_AR, fnt=Font(italic=True, size=9, color="666666", name="Arial"), align=_RTL)


def _add_sensitivity(ws) -> None:
    _init_ws(ws, "مصفوفة الحساسية المتقدمة", cols=[32, 18, 18, 18, 18])
    r = 3
    _sub(ws, r, 1, "محور X: نسبة الإشغال — محور Y: معدل الرسملة"); r += 1
    sm = SENSITIVITY_MATRIX_AR
    _hdr(ws, r, 1, "معدل الرسملة / نسبة الإشغال")
    for c, col_h in enumerate(sm["cols"], 2):
        _hdr(ws, r, c, col_h)
    r += 1
    for i, row_label in enumerate(sm["rows"]):
        _lbl(ws, r, 1, row_label)
        for c, val in enumerate(sm["values"][i], 2):
            cell = ws.cell(row=r, column=c)
            cell.value = val
            cell.number_format = "#,##0"
            cell.alignment = _RTL
            cell.border = _THIN
            # Colour-code
            if val >= 1_300_000:
                cell.fill = PatternFill("solid", fgColor="D5E8D4")
            elif val >= 1_150_000:
                cell.fill = PatternFill("solid", fgColor="FFF2CC")
            else:
                cell.fill = PatternFill("solid", fgColor="F8CECC")
        r += 1
    r += 1
    _sub(ws, r, 1, "محور X: معدل النمو — محور Y: معدل الخصم"); r += 1
    growth_rates = [1.5, 2.0, 3.0, 4.5]
    disc_rates = [7.5, 8.0, 8.5, 9.5]
    _hdr(ws, r, 1, "معدل الخصم / معدل النمو")
    for c, g in enumerate(growth_rates, 2):
        _hdr(ws, r, c, f"نمو {g}%")
    r += 1
    base_noi = INCOME_AR["net_operating_income"]
    for dr in disc_rates:
        _lbl(ws, r, 1, f"خصم {dr}%")
        for c, gr in enumerate(growth_rates, 2):
            try:
                tv = base_noi * (1 + gr/100)**5 / (dr/100)
                pv = sum(base_noi * (1 + gr/100)**y / (1 + dr/100)**y for y in range(1, 6)) + tv / (1 + dr/100)**5
            except ZeroDivisionError:
                pv = 0
            cell = ws.cell(row=r, column=c)
            cell.value = round(pv)
            cell.number_format = "#,##0"
            cell.alignment = _RTL; cell.border = _THIN
        r += 1
    r += 1
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
    _w(ws, r, 1, "الخلايا الخضراء: قيمة مرتفعة | الخلايا الصفراء: متوسطة | الخلايا الحمراء: منخفضة",
       fnt=Font(italic=True, size=9, color="444444", name="Arial"), align=_RTL)


def _add_reconciliation(ws) -> None:
    _init_ws(ws, "التوفيق والترجيح النهائي", cols=[34, 18, 16, 16, 18, 18])
    r = 3
    _sub(ws, r, 1, "الأوزان حسب مستوى التقرير"); r += 1
    _hdr(ws, r, 1, "الأسلوب"); _hdr(ws, r, 2, "القيمة SAR")
    _hdr(ws, r, 3, "وزن تقليدي%"); _hdr(ws, r, 4, "وزن تفصيلي%")
    _hdr(ws, r, 5, "وزن احترافي%"); _hdr(ws, r, 6, "مبرر الوزن")
    r += 1
    weights = [
        ("أسلوب السوق", RECONCILIATION_AR["market_approach_value"],    60, 50, 45, "بيانات سوق كافية ومحدثة"),
        ("أسلوب الدخل", RECONCILIATION_AR["income_approach_value"],    30, 35, 40, "عقار مدر للدخل"),
        ("أسلوب التكلفة", RECONCILIATION_AR["cost_approach_value"],    10, 15, 15, "للتحقق والمقارنة"),
    ]
    val_row_start = r
    for i, (name, val, w_trad, w_det, w_pro, reason) in enumerate(weights):
        _lbl(ws, r, 1, name)
        for c, v in enumerate([val, w_trad, w_det, w_pro, reason], 2):
            _val(ws, r, c, v, fmt="#,##0" if c == 2 else None)
        r += 1
    r += 1
    _sub(ws, r, 1, "نتيجة التوفيق المرجحة"); r += 1
    _lbl(ws, r, 1, "القيمة المرجحة (تفصيلي) SAR")
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=6)
    _val(ws, r, 2, RECONCILIATION_AR["weighted_value"], fmt="#,##0")
    r += 1
    _lbl(ws, r, 1, "القيمة النهائية المدوَّرة (رأي المقيّم) SAR")
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=6)
    _val(ws, r, 2, RECONCILIATION_AR["final_opinion_rounded"], fmt="#,##0")
    r += 1
    _lbl(ws, r, 1, "العملة")
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=6)
    _val(ws, r, 2, RECONCILIATION_AR["currency"])
    r += 1
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
    _w(ws, r, 1,
       "نطاق عدم اليقين: ±5% من القيمة المرجحة | لا يصدر استنتاج نهائي إلا بعد مراجعة الخبير واعتماده.",
       fnt=_WARN_FONT, fill=_WARN_FILL, align=_RTL)
    r += 1
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
    _w(ws, r, 1, f"advisory_only=True | certification_ready=False | {ADVISORY_NOTE_AR}",
       fnt=Font(italic=True, size=9, color="666666", name="Arial"), align=_RTL)


def _add_risk_register(ws) -> None:
    _init_ws(ws, "سجل المخاطر", cols=[24, 32, 18, 16, 16, 18, 20, 24, 18])
    r = 3
    hdrs = ["نوع الخطر", "وصف الخطر", "الاحتمالية", "الأثر", "الدرجة",
            "تأثير على القيمة %", "القيمة المعدَّلة SAR", "إجراءات التخفيف", "الحالة"]
    for c, h in enumerate(hdrs, 1):
        _hdr(ws, r, c, h)
    r += 1
    risk_types = [
        ("سوقي",    "تقلب معدلات الرسملة وأسعار السوق",       "متوسطة", "متوسط", "متوسطة",  -3, "تنويع الأصول"),
        ("قانوني",  "نزاعات ملكية أو مطالبات غير موثقة",       "منخفضة", "مرتفع", "متوسطة",  -2, "التحقق القانوني الكامل"),
        ("مستندي",  "عدم اكتمال وثائق الملكية",               "منخفضة", "متوسط", "منخفضة",  -1, "طلب المستندات الكاملة"),
        ("تشغيلي",  "ارتفاع تكاليف الصيانة المستقبلية",        "متوسطة", "منخفض", "منخفضة",  -1, "التفتيش الدوري"),
        ("إنشائي",  "تدهور البناء على المدى البعيد",           "منخفضة", "متوسط", "منخفضة",  -2, "تقرير المعاينة"),
        ("تمويلي",  "تغير أسعار الفائدة وتكلفة الاقتراض",      "متوسطة", "متوسط", "متوسطة",  -2, "قفل سعر الفائدة"),
        ("تنظيمي",  "تغيير الاشتراطات التخطيطية والبناء",       "منخفضة", "منخفض", "منخفضة",  -1, "متابعة الأنظمة الجديدة"),
        ("سيولة",   "صعوبة التسييل السريع للأصل",              "متوسطة", "متوسط", "متوسطة",  -2, "تقييم السوق الثانوي"),
        ("بيانات",  "محدودية بيانات المقارنات المتاحة",         "منخفضة", "منخفض", "منخفضة",  -1, "تعزيز قاعدة البيانات"),
    ]
    base_val = RECONCILIATION_AR["final_opinion_rounded"]
    for rt in risk_types:
        rtype, desc, prob, impact, grade, pct, mitigation = rt
        adj_val = int(base_val * (1 + pct / 100))
        row_data = [rtype, desc, prob, impact, grade, f"{pct}%", adj_val, mitigation, "قيد المتابعة"]
        for c, v in enumerate(row_data, 1):
            cell = ws.cell(row=r, column=c)
            cell.value = v; cell.alignment = _RTL; cell.border = _THIN
            if c == 3:
                cell.font = _WARN_FONT if prob == "متوسطة" else _OK_FONT
        r += 1


def _add_standards(ws) -> None:
    _init_ws(ws, "مصفوفة المعايير والإفصاحات", cols=[18, 32, 18, 18, 20])
    r = 3
    for c, h in enumerate(["المعيار", "البند", "الحالة", "المرجع", "ملاحظة"], 1):
        _hdr(ws, r, c, h)
    r += 1
    entries = [
        ("IVS 101",  "نطاق العمل",                   "مكتمل",         "IVSC 2025"),
        ("IVS 102",  "التحقيقات والامتثال",            "مكتمل",         "IVSC 2025"),
        ("IVS 103",  "إعداد التقرير",                 "مكتمل",         "IVSC 2025"),
        ("IVS 104",  "أسس القيمة",                    "مكتمل",         "IVSC 2025"),
        ("IVS 105",  "مناهج وأساليب التقييم",         "مكتمل",         "IVSC 2025"),
        ("IVS 400",  "التقييم العقاري",               "مكتمل",         "IVSC 2025"),
        ("RICS",     "الكتاب الأحمر — Red Book",       "مكتمل جزئياً", "RICS 2024"),
        ("IFRS 13",  "قياس القيمة العادلة",            "مكتمل جزئياً", "IASB"),
        ("USPAP",    "معايير ممارسة التقييم الأمريكية", "غير منطبق",    "TAF"),
        ("FRA Egypt","هيئة الرقابة المالية",           "مكتمل جزئياً", "FRA 2024"),
        ("GCC",      "المعايير الخليجية",              "مكتمل جزئياً", "GCC Valuation"),
        ("Basel III","سياق ضمانات الائتمان LTV/RWA",  "مكتمل",         "BIS 2024"),
    ]
    for std, bnd, status, ref in entries:
        _lbl(ws, r, 1, std); _val(ws, r, 2, bnd)
        c = ws.cell(row=r, column=3)
        c.value = status; c.alignment = _RTL; c.border = _THIN
        c.font = _OK_FONT if status == "مكتمل" else (_WARN_FONT if "جزئياً" in status else _NOK_FONT)
        _val(ws, r, 4, ref); _val(ws, r, 5, "بيانات توضيحية — يستلزم مراجعة")
        r += 1
    r += 1
    _sub(ws, r, 1, "الإفصاحات الإلزامية"); r += 1
    disclosures = [
        "هذا التقرير استرشادي ولا يُستخدم في أي معاملة مالية أو قانونية دون مراجعة الخبير المعتمد.",
        "البيانات الواردة هي أمثلة توضيحية — not_real_training=True.",
        "لا تعتمد على هذا التقرير لأغراض الإقراض أو البيع دون الحصول على نتيجة نهائية معتمدة.",
        "التقييم خضع لقيود بيانات موضحة في ورقة جودة البيانات.",
    ]
    for d in disclosures:
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
        _w(ws, r, 1, f"• {d}", fnt=Font(italic=True, size=9, color="333333", name="Arial"), align=_RTL)
        r += 1


def _add_source_registry(ws) -> None:
    _init_ws(ws, "سجل مصادر البيانات", cols=[26, 26, 16, 16, 18, 18, 20])
    r = 3
    for c, h in enumerate(["نوع البيانات", "المصدر", "التاريخ", "درجة الثقة", "رابط/مرجع", "ملاحظات التحقق", "قابلية الاعتماد"], 1):
        _hdr(ws, r, c, h)
    r += 1
    sources = [
        ("سعر العقار",          "بيانات معاملات السوق",        "يونيو 2026", "عالية",     "قاعدة البيانات الداخلية",  "تم التحقق",     "عالية"),
        ("المساحة",             "مخططات المبنى الرسمية",        "2018",       "عالية",     "أرشيف الترخيص",          "تم التحقق",     "عالية"),
        ("الدخل والإيجار",      "بيانات السوق الإيجاري",        "يونيو 2026", "متوسطة",    "مسوحات ميدانية",         "تحتاج تأكيداً", "متوسطة"),
        ("تكلفة البناء",        "دليل أسعار المقاولين 2026",    "مارس 2026",  "عالية",     "اتحاد المقاولين",        "تم التحقق",     "عالية"),
        ("معدل الرسملة",        "بيانات الصفقات المقارنة",      "مايو 2026",  "متوسطة",    "تحليل داخلي",            "تقدير",         "متوسطة"),
        ("معدل الخصم",          "متطلبات السوق المالية",        "يونيو 2026", "متوسطة",    "بنوك تجارية",            "تقدير",         "متوسطة"),
        ("المقارنات السوقية",   "منصة صفقات العقار السعودي",    "يونيو 2026", "عالية",     "الوصول المباشر للمنصة",  "تم التحقق",     "عالية"),
        ("الاشتراطات التنظيمية","هيئة التخطيط والتطوير العمراني","2026",      "عالية",     "البوابة الرسمية",        "تم التحقق",     "عالية"),
    ]
    for row_data in sources:
        for c, v in enumerate(row_data, 1):
            cell = ws.cell(row=r, column=c)
            cell.value = v; cell.alignment = _RTL; cell.border = _THIN
            if c == 4:
                cell.font = _OK_FONT if v == "عالية" else _WARN_FONT
        r += 1


def _add_admin_notes(ws) -> None:
    _init_ws(ws, "ملاحظات الإدارة والاعتماد", cols=[36, 30, 16, 18])
    r = 3
    _sub(ws, r, 1, "قائمة مراجعة الخبير"); r += 1
    checklist = [
        "تحقق من بيانات الملكية والوثائق القانونية",
        "راجع تقرير المعاينة الفنية",
        "تحقق من صحة المقارنات السوقية",
        "راجع حسابات DCF ومعدلات الرسملة",
        "تحقق من الامتثال لمعايير IVS 2025",
        "راجع تحليل HBU وسجل المخاطر",
        "وقّع على التقرير وختمه بعد الموافقة",
    ]
    for item in checklist:
        _lbl(ws, r, 1, f"☐ {item}")
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
        r += 1
    r += 1
    _sub(ws, r, 1, "حالة الاعتماد"); r += 1
    approval_rows = [
        ("هل تم الاعتماد؟",            "لا — بانتظار مراجعة الخبير"),
        ("تاريخ الاعتماد",             "—"),
        ("رقم الاعتماد",               "—"),
        ("ملاحظات عدم الاعتماد",        "التقرير في مرحلة المراجعة الداخلية"),
        ("طريقة استلام التقرير المعتمد","البريد الإلكتروني / WhatsApp"),
    ]
    for label, value in approval_rows:
        _lbl(ws, r, 1, label)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=4)
        _val(ws, r, 2, value)
        r += 1
    r += 1
    _sub(ws, r, 1, "بيانات التواصل"); r += 1
    contact = [
        ("الاسم بالكامل",    "—"),
        ("البريد الإلكتروني","—"),
        ("رقم واتساب",       "—"),
        ("نوع التقرير المطلوب","تقليدي / تفصيلي / احترافي"),
    ]
    for label, value in contact:
        _lbl(ws, r, 1, label)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=4)
        _val(ws, r, 2, value)
        r += 1
    r += 1
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
    _w(ws, r, 1,
       "تنبيه: لا يتم إصدار تقرير معتمد إلا بعد مراجعة الخبير واعتماده. "
       "هذا الملف داخلي للخبير أو الإدارة ولا يُرسل للمستخدم.",
       fnt=_WARN_FONT, fill=_WARN_FILL, align=_RTL)


# ── Master sheet dispatcher ───────────────────────────────────────────────────

_SHEET_BUILDERS = {
    "Cover":           _add_cover,
    "Data Quality":    _add_data_quality,
    "Property":        _add_property,
    "HBU Analysis":    _add_hbu,
    "Comparables":     _add_comparables,
    "Income Approach": _add_income,
    "Cost Approach":   _add_cost,
    "AVM Reference":   _add_avm,
    "Scenarios":       _add_scenarios,
    "Sensitivity Matrix": _add_sensitivity,
    "Reconciliation":  _add_reconciliation,
    "Risk Register":   _add_risk_register,
    "Standards Matrix": _add_standards,
    "Source Registry": _add_source_registry,
    "Admin Notes":     _add_admin_notes,
}


# ── Legacy sheet copying ──────────────────────────────────────────────────────

def _safe_name(prefix: str, original: str, existing: set[str]) -> str:
    max_suffix = 31 - len(prefix)
    clean = _INVALID_SHEET_CHARS.sub("_", original)
    clean = clean[:max_suffix]
    candidate = prefix + clean
    base, i = candidate, 1
    while candidate in existing:
        suf = f"_{i}"
        candidate = (base[: 31 - len(suf)]) + suf
        i += 1
    existing.add(candidate)
    return candidate


def _copy_legacy_workbook(
    target_wb: Workbook,
    src_path: Path,
    prefix: str,
    existing_names: set[str],
) -> list[dict]:
    mapping: list[dict] = []
    if not src_path.exists():
        return [{"error": f"Source not found: {src_path}", "prefix": prefix}]
    try:
        src_wb = openpyxl.load_workbook(str(src_path), data_only=False)
    except Exception as exc:
        return [{"error": str(exc), "prefix": prefix}]

    for sheet_name in src_wb.sheetnames:
        safe = _safe_name(prefix, sheet_name, existing_names)
        src_ws = src_wb[sheet_name]
        dst_ws = target_wb.create_sheet(safe)
        dst_ws.sheet_view.rightToLeft = True

        max_r, max_c = 0, 0
        for row in src_ws.iter_rows():
            for cell in row:
                if cell.value is not None:
                    dst_ws.cell(row=cell.row, column=cell.column, value=cell.value)
                    max_r = max(max_r, cell.row)
                    max_c = max(max_c, cell.column)

        for col_letter, cdim in src_ws.column_dimensions.items():
            if cdim.width:
                dst_ws.column_dimensions[col_letter].width = cdim.width

        for row_num, rdim in src_ws.row_dimensions.items():
            if rdim.height:
                dst_ws.row_dimensions[row_num].height = rdim.height

        note_row = (src_ws.max_row or 1) + 2
        dst_ws.cell(row=note_row, column=1,
                    value=f"[أرشيف قديم — مصدر: {src_path.name} | الورقة الأصلية: {sheet_name}]")

        mapping.append({
            "safe_name": safe,
            "original_name": sheet_name,
            "prefix": prefix,
            "source_file": src_path.name,
            "rows_copied": max_r,
            "cols_copied": max_c,
            "name_truncated": safe != prefix + _INVALID_SHEET_CHARS.sub("_", sheet_name),
        })
    src_wb.close()
    return mapping


# ── Excel workbook generator ──────────────────────────────────────────────────

def generate_excel(
    xl_out: Path,
    gf_path: Path,
    ultra_path: Path,
) -> dict:
    xl_out.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    wb.remove(wb.active)  # remove default Sheet

    existing_names: set[str] = set()

    # 1) 15 master sheets
    for name in MASTER_SHEET_NAMES:
        ws = wb.create_sheet(name)
        existing_names.add(name)
        _SHEET_BUILDERS[name](ws)

    # 2) Legacy archive — GRAND_FINAL
    gf_mapping = _copy_legacy_workbook(wb, gf_path, "LEGACY_GF_", existing_names)
    # 3) Legacy archive — ULTRA
    ultra_mapping = _copy_legacy_workbook(wb, ultra_path, "LEGACY_ULTRA_", existing_names)

    wb.save(str(xl_out))

    total_sheets = len(wb.sheetnames)
    legacy_count = total_sheets - 15
    gf_ok = not any("error" in m for m in gf_mapping)
    ul_ok = not any("error" in m for m in ultra_mapping)

    return {
        "excel_file": xl_out.name,
        "total_sheet_count": total_sheets,
        "master_sheet_count": 15,
        "legacy_archive_sheet_count": legacy_count,
        "first_15_sheets_are_master": wb.sheetnames[:15] == MASTER_SHEET_NAMES,
        "master_sheet_names": MASTER_SHEET_NAMES,
        "grand_final_copy_ok": gf_ok,
        "ultra_copy_ok": ul_ok,
        "gf_sheet_mapping": gf_mapping,
        "ultra_sheet_mapping": ultra_mapping,
        "vba_blocker": "openpyxl cannot transfer VBA/macros across workbooks; legacy sheet values+formulas preserved, macros excluded",
    }


# ── PDF CSS ───────────────────────────────────────────────────────────────────

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Arial Unicode MS','Segoe UI',Arial,sans-serif;
  font-size: 10.5pt; color: #1a1a1a; line-height: 1.75;
  direction: rtl; text-align: right;
}
h1 { font-size: 18pt; color: #1a3a5c; text-align: center; margin-bottom: 8px; }
h2 { font-size: 12pt; color: #1a3a5c; border-bottom: 2px solid #1a3a5c;
     padding-bottom: 3px; margin: 20px 0 7px; }
h3 { font-size: 10.5pt; color: #2c5f8a; margin: 14px 0 4px;
     border-right: 3px solid #2c5f8a; padding-right: 7px; }
p { margin: 6px 0; }
ul { margin: 5px 0; padding-right: 20px; list-style-type: disc; }
li { margin: 3px 0; font-size: 10pt; }
table { width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 9.5pt; direction: rtl; }
th { background: #1a3a5c; color: #fff; padding: 6px 9px; text-align: right; }
td { padding: 5px 9px; border: 1px solid #c8d4e0; vertical-align: top; text-align: right; }
tr:nth-child(even) td { background: #f0f5fa; }
.kv td:first-child { font-weight: bold; background: #e4edf5; width: 40%; }
.advisory { background:#fff8e1;border:2px solid #e6a817;padding:10px 14px;margin:12px 0;border-radius:5px;font-size:9.5pt; }
.advisory strong { color:#8a5700; }
.cover { text-align:center;padding:30px 20px;border:3px solid #1a3a5c;margin-bottom:20px;border-radius:8px;background:#f5f9fd; }
.cover .badge { display:inline-block;background:#fff3cd;border:1px solid #e6a817;color:#8a5700;padding:3px 12px;border-radius:12px;font-size:9pt;font-weight:bold;margin:6px 0 14px; }
.val-box { background:#e4edf5;border-right:5px solid #1a3a5c;padding:10px 14px;margin:10px 0;font-size:11pt;font-weight:bold;color:#1a3a5c; }
.note { font-size:8.5pt;color:#666;font-style:italic;margin-top:3px; }
.ok   { color:#1e7e34;font-weight:bold; }
.warn { color:#856404;font-weight:bold; }
.hl   { background:#fffde7;padding:8px 12px;border-right:4px solid #f9a825;margin:8px 0;border-radius:4px; }
.footer { margin-top:24px;border-top:1px solid #bbb;padding-top:7px;font-size:8pt;color:#888;text-align:center; }
.pro-badge { background:#1a3a5c;color:#d4af37;padding:3px 10px;border-radius:8px;font-size:9pt;font-weight:bold; }
.excel-ref { font-size:8.5pt;color:#2c5f8a;font-style:italic; }
@page { size: A4; margin: 18mm 16mm; }
"""

def _html_wrap(title: str, body: str, badge: str) -> str:
    return f"""<!DOCTYPE html>
<html lang='ar' dir='rtl'>
<head><meta charset='utf-8'><title>{title}</title>
<style>{_CSS}</style></head>
<body>
<div class='cover'>
  <h1>{title}</h1>
  <div class='sub'>{SUBJECT_AR['property_address']}</div>
  <div class='badge'>{badge}</div>
  <p style='font-size:9pt;color:#444;'>
    تاريخ التقرير: {_NOW[:10]} | العملة: {SUBJECT_AR['currency']} |
    أساس القيمة: القيمة السوقية (IVS 2025)
  </p>
  <p style='font-size:9pt;color:#444;'>
    ملف Excel الإداري: professional_valuation_admin_master_workbook.xlsm
  </p>
</div>
<div class='advisory'>
  <strong>تنبيه استرشادي:</strong> {ADVISORY_NOTE_AR} |
  advisory_only=True | certification_ready=False | not_real_training=True
</div>
{body}
<div class='footer'>
  {title} — {_NOW} — مسودة استرشادية | لا تُعتمد دون مراجعة الخبير
</div>
</body></html>"""


def _kv_table(rows: list[tuple]) -> str:
    r = "<table class='kv'>"
    for label, value in rows:
        r += f"<tr><td>{label}</td><td>{value}</td></tr>"
    return r + "</table>"


def _build_traditional_html() -> str:
    s = SUBJECT_AR
    body = f"""
<h2>1. بيانات العقار الأساسية</h2>
{_kv_table([
    ("نوع الأصل", s["property_type"]),
    ("الموقع", s["property_address"]),
    ("المساحة البنائية", f"{s['gross_floor_area_m2']} م²"),
    ("عمر المبنى", f"{s['age_years']} سنوات"),
    ("حالة الملكية", s["tenure"]),
    ("الغرض", s["purpose"]),
])}

<h2>2. أسلوب السوق / Market Approach</h2>
<p>تم تحليل {len(COMPARABLES_AR)} مقارنات سوقية محدثة.</p>
<table>
<tr><th>المقارنة</th><th>المساحة م²</th><th>السعر SAR</th><th>SAR/م²</th><th>التاريخ</th></tr>
{"".join(f"<tr><td>{c['id']}</td><td>{c['area_m2']}</td><td>{c['price_sar']:,}</td><td>{c['price_per_sqm']:,}</td><td>{c['sale_date']}</td></tr>" for c in COMPARABLES_AR)}
</table>
<div class='val-box'>مؤشر القيمة السوقية: {INDICATED_MARKET_VALUE:,} SAR
  <span class='note'>({INDICATED_MARKET_VALUE_PER_SQM:,} SAR/م² × {s['gross_floor_area_m2']} م²)</span>
</div>

<h2>3. أسلوب الدخل / Income Approach</h2>
{_kv_table([
    ("الإيجار السنوي الإجمالي", f"{INCOME_AR['gross_market_rent_annual']:,} SAR"),
    ("نسبة الشغور", f"{INCOME_AR['vacancy_rate_pct']}%"),
    ("المصروفات التشغيلية", f"{INCOME_AR['total_opex']:,} SAR"),
    ("صافي الدخل التشغيلي (NOI)", f"{INCOME_AR['net_operating_income']:,} SAR"),
    ("معدل الرسملة", f"{INCOME_AR['cap_rate_pct']}%"),
    ("مؤشر القيمة بطريقة الدخل", f"{INCOME_AR['indicated_value_income']:,} SAR"),
])}

<h2>4. أسلوب التكلفة / Cost Approach</h2>
{_kv_table([
    ("قيمة الأرض", f"{COST_AR['land_value']:,} SAR"),
    ("تكلفة الإحلال الجديدة", f"{COST_AR['replacement_cost_new']:,} SAR"),
    ("الإهلاك المادي", f"{COST_AR['physical_depreciation_pct']}% ({COST_AR['physical_depreciation']:,} SAR)"),
    ("مؤشر القيمة بأسلوب التكلفة", f"{COST_AR['indicated_value_cost']:,} SAR"),
])}

<h2>5. مؤشر التقييم الآلي المساعد / AVM</h2>
{_kv_table([
    ("مؤشر AVM", f"{AVM_AR['avm_indicated_value']:,} SAR"),
    ("درجة الثقة", AVM_AR["confidence_level"]),
    ("قيد الاستخدام", AVM_AR["note"]),
])}

<h2>6. التوفيق والترجيح النهائي / Reconciliation</h2>
<table>
<tr><th>الأسلوب</th><th>القيمة SAR</th><th>الوزن %</th><th>القيمة المرجحة SAR</th></tr>
<tr><td>أسلوب السوق</td><td>{RECONCILIATION_AR['market_approach_value']:,}</td><td>60%</td><td>{int(RECONCILIATION_AR['market_approach_value']*0.60):,}</td></tr>
<tr><td>أسلوب الدخل</td><td>{RECONCILIATION_AR['income_approach_value']:,}</td><td>30%</td><td>{int(RECONCILIATION_AR['income_approach_value']*0.30):,}</td></tr>
<tr><td>أسلوب التكلفة</td><td>{RECONCILIATION_AR['cost_approach_value']:,}</td><td>10%</td><td>{int(RECONCILIATION_AR['cost_approach_value']*0.10):,}</td></tr>
</table>
<div class='val-box'>رأي المقيّم (تقليدي): {RECONCILIATION_AR['final_opinion_rounded']:,} SAR</div>
<p class='note excel-ref'>المرجع في ملف Excel: Cover | Comparables | Income Approach | Cost Approach | Reconciliation</p>
"""
    return _html_wrap("تقرير التقييم التقليدي", body, "تقرير تقليدي — مسودة استرشادية")


def _build_detailed_html() -> str:
    s = SUBJECT_AR
    body = f"""
<h2>1. بيانات العقار الأساسية</h2>
{_kv_table([
    ("نوع الأصل", s["property_type"]),
    ("الموقع", s["property_address"]),
    ("المساحة الأرضية", f"{COST_AR['land_area_m2']} م²"),
    ("المساحة البنائية", f"{s['gross_floor_area_m2']} م²"),
    ("عمر المبنى", f"{s['age_years']} سنوات"),
    ("حالة الملكية", s["tenure"]),
    ("الغرض", s["purpose"]),
    ("أساس القيمة", s["basis_of_value"]),
])}

<h2>2. جودة البيانات واكتمالها</h2>
<table>
<tr><th>الحقل</th><th>الحالة</th></tr>
{"".join(f"<tr><td>{d['field']}</td><td class='ok'>{d['status']}</td></tr>" for d in DATA_INPUTS_AR)}
</table>
<p class='excel-ref'>ورقة Excel: Data Quality</p>

<h2>3. تحليل أعلى وأفضل استخدام / HBU</h2>
<table>
<tr><th>الاختبار</th><th>النتيجة</th></tr>
<tr><td>فيزيائي / Physically Possible</td><td class='ok'>{HBU_AR['physically_possible']}</td></tr>
<tr><td>قانوني / Legally Permissible</td><td class='ok'>{HBU_AR['legally_permissible']}</td></tr>
<tr><td>مالي / Financially Feasible</td><td class='ok'>{HBU_AR['financially_feasible']}</td></tr>
<tr><td>أعلى إنتاجية / Maximally Productive</td><td class='ok'>{HBU_AR['maximally_productive']}</td></tr>
</table>
<div class='hl'>خلاصة HBU: {HBU_AR['conclusion']}</div>
<p class='excel-ref'>ورقة Excel: HBU Analysis</p>

<h2>4. أسلوب السوق / Market Approach</h2>
<table>
<tr><th>م</th><th>العنوان</th><th>المساحة م²</th><th>السعر SAR</th><th>SAR/م²</th><th>التسوية الإجمالية %</th><th>السعر المعدل SAR/م²</th></tr>
{"".join(f"<tr><td>{c['id']}</td><td>{c['address']}</td><td>{c['area_m2']}</td><td>{c['price_sar']:,}</td><td>{c['price_per_sqm']:,}</td><td>{'±3%'}</td><td>{ap:,}</td></tr>" for c, ap in zip(COMPARABLES_AR, ADJUSTED_PRICES_PER_SQM))}
</table>
<div class='val-box'>مؤشر القيمة السوقية: {INDICATED_MARKET_VALUE:,} SAR</div>

<h2>5. أسلوب الدخل والرسملة المباشرة / Income Approach</h2>
{_kv_table([
    ("الإيجار السنوي الإجمالي", f"{INCOME_AR['gross_market_rent_annual']:,} SAR"),
    ("نسبة الشغور", f"{INCOME_AR['vacancy_rate_pct']}%"),
    ("الدخل الإجمالي الفعلي", f"{INCOME_AR['effective_gross_income']:,} SAR"),
    ("إجمالي المصروفات التشغيلية", f"{INCOME_AR['total_opex']:,} SAR"),
    ("صافي الدخل التشغيلي (NOI)", f"{INCOME_AR['net_operating_income']:,} SAR"),
    ("معدل الرسملة", f"{INCOME_AR['cap_rate_pct']}%"),
    ("مؤشر القيمة بطريقة الدخل", f"{INCOME_AR['indicated_value_income']:,} SAR"),
])}

<h2>6. ملخص DCF — التدفقات النقدية المخصومة (5 سنوات)</h2>
<table>
<tr><th>السنة</th>{"".join(f"<th>{i+1}</th>" for i in range(5))}</tr>
<tr><td>التدفق النقدي SAR</td>{"".join(f"<td>{v:,}</td>" for v in DCF_5YEAR_AR['year_cash_flows'])}</tr>
</table>
{_kv_table([
    ("معدل النمو السنوي", f"{DCF_5YEAR_AR['growth_rate_pct']}%"),
    ("معدل الرسملة الطرفية", f"{DCF_5YEAR_AR['terminal_cap_rate_pct']}%"),
    ("معدل الخصم", f"{DCF_5YEAR_AR['discount_rate_pct']}%"),
    ("القيمة الطرفية", f"{DCF_5YEAR_AR['terminal_value_year5']:,} SAR"),
    ("مؤشر DCF (5 سنوات)", f"{DCF_5YEAR_AR['dcf_indicated_value']:,} SAR"),
])}
<p class='excel-ref'>ورقة Excel: Income Approach (قسم DCF)</p>

<h2>7. أسلوب التكلفة / Cost Approach</h2>
{_kv_table([
    ("قيمة الأرض", f"{COST_AR['land_value']:,} SAR"),
    ("تكلفة الإحلال الجديدة", f"{COST_AR['replacement_cost_new']:,} SAR"),
    ("الإهلاك المادي", f"{COST_AR['physical_depreciation_pct']}%"),
    ("قيمة الإحلال المستهلكة", f"{COST_AR['depreciated_improvement_value']:,} SAR"),
    ("مؤشر القيمة بأسلوب التكلفة", f"{COST_AR['indicated_value_cost']:,} SAR"),
])}

<h2>8. مصفوفة الحساسية / Sensitivity Matrix</h2>
<table>
<tr><th>معدل الرسملة / الإشغال</th>{"".join(f"<th>{col}</th>" for col in SENSITIVITY_MATRIX_AR['cols'])}</tr>
{"".join(f"<tr><td><strong>{row}</strong></td>{''.join(f'<td>{v:,}</td>' for v in vals)}</tr>" for row, vals in zip(SENSITIVITY_MATRIX_AR['rows'], SENSITIVITY_MATRIX_AR['values']))}
</table>
<p class='excel-ref'>ورقة Excel: Sensitivity Matrix</p>

<h2>9. ملاحظات المخاطر / Risk Notes</h2>
<ul>
{"".join(f"<li><strong>{r['risk']}</strong> ({r['severity']}): {r['impact']}</li>" for r in RISKS_AR)}
</ul>
<p class='excel-ref'>ورقة Excel: Risk Register</p>

<h2>10. مؤشر التقييم الآلي المساعد / AVM</h2>
{_kv_table([
    ("مؤشر AVM", f"{AVM_AR['avm_indicated_value']:,} SAR"),
    ("درجة الثقة", f"{AVM_AR['confidence_level']} ({AVM_AR['confidence_score']:.0%})"),
    ("قيد الاستخدام", AVM_AR["note"]),
])}

<h2>11. التوفيق والترجيح النهائي / Reconciliation</h2>
<table>
<tr><th>الأسلوب</th><th>القيمة SAR</th><th>الوزن %</th><th>القيمة المرجحة SAR</th></tr>
<tr><td>أسلوب السوق</td><td>{RECONCILIATION_AR['market_approach_value']:,}</td><td>50%</td><td>{int(RECONCILIATION_AR['market_approach_value']*0.50):,}</td></tr>
<tr><td>أسلوب الدخل</td><td>{RECONCILIATION_AR['income_approach_value']:,}</td><td>35%</td><td>{int(RECONCILIATION_AR['income_approach_value']*0.35):,}</td></tr>
<tr><td>أسلوب التكلفة</td><td>{RECONCILIATION_AR['cost_approach_value']:,}</td><td>15%</td><td>{int(RECONCILIATION_AR['cost_approach_value']*0.15):,}</td></tr>
</table>
<div class='val-box'>رأي المقيّم (تفصيلي): {RECONCILIATION_AR['final_opinion_rounded']:,} SAR</div>
<p class='excel-ref'>ورقة Excel: Reconciliation</p>

<h2>12. مصادر البيانات / Source Registry</h2>
<p>تم توثيق {8} مصدر بيانات في ورقة "Source Registry" من ملف Excel الإداري.</p>
<p class='excel-ref'>ورقة Excel: Source Registry</p>
"""
    return _html_wrap("تقرير التقييم التفصيلي", body, "تقرير تفصيلي — مسودة استرشادية")


def _build_professional_html() -> str:
    s = SUBJECT_AR
    prob_rows = ""
    probs = [0.20, 0.60, 0.20]
    for sc, p in zip(SCENARIOS_AR, probs):
        wv = int(sc["dcf_value"] * p)
        prob_rows += f"<tr><td>{sc['scenario']}</td><td>{sc['growth_rate']}%</td><td>{sc['cap_rate']}%</td><td>{sc['discount_rate']}%</td><td>{sc['dcf_value']:,}</td><td>{int(p*100)}%</td><td>{wv:,}</td></tr>"

    body = f"""
<h2>1. بيانات العقار الأساسية</h2>
{_kv_table([
    ("نوع الأصل", s["property_type"]),
    ("الموقع", s["property_address"]),
    ("المساحة الأرضية", f"{COST_AR['land_area_m2']} م²"),
    ("المساحة البنائية", f"{s['gross_floor_area_m2']} م²"),
    ("عمر المبنى", f"{s['age_years']} سنوات"),
    ("حالة الملكية", s["tenure"]),
    ("الغرض", s["purpose"]),
    ("أساس القيمة", s["basis_of_value"]),
    ("الإحداثيات", s["coordinates"]),
])}

<h2>2. جودة البيانات واكتمالها</h2>
<table>
<tr><th>الحقل</th><th>الحالة</th></tr>
{"".join(f"<tr><td>{d['field']}</td><td class='ok'>{d['status']}</td></tr>" for d in DATA_INPUTS_AR)}
</table>
<p class='excel-ref'>ورقة Excel: Data Quality</p>

<h2>3. منهجية الاختيار / Method Selection</h2>
<table>
<tr><th>الأسلوب</th><th>قابل للتطبيق</th><th>الوزن %</th><th>المبرر</th></tr>
{"".join(f"<tr><td>{m['method']}</td><td class='ok'>{m['applicable']}</td><td>{m['weight_pct'] or '—'}</td><td>{m['reason']}</td></tr>" for m in METHOD_SELECTION_AR)}
</table>

<h2>4. تحليل أعلى وأفضل استخدام / HBU Analysis</h2>
<table>
<tr><th>الاختبار</th><th>النتيجة</th><th>الحالة</th></tr>
<tr><td>فيزيائي / Physically Possible</td><td>{HBU_AR['physically_possible']}</td><td class='ok'>مطابق ✓</td></tr>
<tr><td>قانوني / Legally Permissible</td><td>{HBU_AR['legally_permissible']}</td><td class='ok'>مطابق ✓</td></tr>
<tr><td>مالي / Financially Feasible</td><td>{HBU_AR['financially_feasible']}</td><td class='ok'>مطابق ✓</td></tr>
<tr><td>أعلى إنتاجية / Maximally Productive</td><td>{HBU_AR['maximally_productive']}</td><td class='ok'>مطابق ✓</td></tr>
</table>
<div class='hl'><strong>خلاصة HBU:</strong> {HBU_AR['conclusion']}</div>
<p class='excel-ref'>ورقة Excel: HBU Analysis</p>

<h2>5. أسلوب السوق / Market Approach</h2>
<table>
<tr><th>م</th><th>العنوان</th><th>المساحة م²</th><th>السعر SAR</th><th>SAR/م²</th><th>السعر المعدل SAR/م²</th></tr>
{"".join(f"<tr><td>{c['id']}</td><td>{c['address']}</td><td>{c['area_m2']}</td><td>{c['price_sar']:,}</td><td>{c['price_per_sqm']:,}</td><td>{ap:,}</td></tr>" for c, ap in zip(COMPARABLES_AR, ADJUSTED_PRICES_PER_SQM))}
</table>
<div class='val-box'>مؤشر القيمة السوقية: {INDICATED_MARKET_VALUE:,} SAR</div>
<p class='excel-ref'>ورقة Excel: Comparables</p>

<h2>6. أسلوب الدخل / Income Approach</h2>
{_kv_table([
    ("الإيجار السنوي الإجمالي", f"{INCOME_AR['gross_market_rent_annual']:,} SAR"),
    ("نسبة الشغور", f"{INCOME_AR['vacancy_rate_pct']}%"),
    ("الدخل الإجمالي الفعلي", f"{INCOME_AR['effective_gross_income']:,} SAR"),
    ("إجمالي المصروفات التشغيلية", f"{INCOME_AR['total_opex']:,} SAR"),
    ("NOI — صافي الدخل التشغيلي", f"{INCOME_AR['net_operating_income']:,} SAR"),
    ("معدل الرسملة", f"{INCOME_AR['cap_rate_pct']}%"),
    ("مؤشر القيمة بطريقة الدخل", f"{INCOME_AR['indicated_value_income']:,} SAR"),
])}
<p class='excel-ref'>ورقة Excel: Income Approach (قسم 1)</p>

<h2>7. DCF — التدفقات النقدية (5 سنوات)</h2>
<table>
<tr><th>السنة</th>{"".join(f"<th>السنة {i+1}</th>" for i in range(5))}</tr>
<tr><td>التدفق النقدي SAR</td>{"".join(f"<td>{v:,}</td>" for v in DCF_5YEAR_AR['year_cash_flows'])}</tr>
</table>
{_kv_table([
    ("معدل النمو", f"{DCF_5YEAR_AR['growth_rate_pct']}%"),
    ("معدل الرسملة الطرفية", f"{DCF_5YEAR_AR['terminal_cap_rate_pct']}%"),
    ("معدل الخصم", f"{DCF_5YEAR_AR['discount_rate_pct']}%"),
    ("القيمة الطرفية", f"{DCF_5YEAR_AR['terminal_value_year5']:,} SAR"),
    ("NPV / مؤشر DCF (5 سنوات)", f"{DCF_5YEAR_AR['dcf_indicated_value']:,} SAR"),
])}

<h2>8. DCF — التدفقات النقدية (10 سنوات)</h2>
{_kv_table([
    ("فترة الاحتجاز", f"{DCF_10YEAR_AR['hold_period_years']} سنوات"),
    ("صافي الدخل الأولي", f"{DCF_10YEAR_AR['initial_noi']:,} SAR"),
    ("معدل النمو", f"{DCF_10YEAR_AR['growth_rate_pct']}%"),
    ("معدل الخصم", f"{DCF_10YEAR_AR['discount_rate_pct']}%"),
    ("NPV / مؤشر DCF (10 سنوات)", f"{DCF_10YEAR_AR['dcf_indicated_value']:,} SAR"),
])}
<p class='excel-ref'>ورقة Excel: Income Approach (قسم 3 — DCF 10 سنوات)</p>

<h2>9. أسلوب التكلفة / Cost Approach</h2>
{_kv_table([
    ("قيمة الأرض", f"{COST_AR['land_value']:,} SAR"),
    ("تكلفة الإحلال الجديدة", f"{COST_AR['replacement_cost_new']:,} SAR"),
    ("الإهلاك المادي", f"{COST_AR['physical_depreciation_pct']}% ({COST_AR['physical_depreciation']:,} SAR)"),
    ("قيمة الإحلال المستهلكة", f"{COST_AR['depreciated_improvement_value']:,} SAR"),
    ("مؤشر القيمة بأسلوب التكلفة", f"{COST_AR['indicated_value_cost']:,} SAR"),
])}
<p class='excel-ref'>ورقة Excel: Cost Approach</p>

<h2>10. تحليل السيناريوهات / Scenario Analysis</h2>
<table>
<tr><th>السيناريو</th><th>معدل النمو %</th><th>معدل الرسملة %</th><th>معدل الخصم %</th><th>قيمة DCF SAR</th><th>الاحتمال %</th><th>القيمة المرجحة SAR</th></tr>
{prob_rows}
</table>
<div class='val-box'>القيمة المرجحة بالاحتمالات: {PROBABILITY_WEIGHTED_VALUE:,} SAR</div>
<p class='excel-ref'>ورقة Excel: Scenarios</p>

<h2>11. مصفوفة الحساسية المتقدمة / Sensitivity Matrix</h2>
<table>
<tr><th>معدل الرسملة / الإشغال</th>{"".join(f"<th>{col}</th>" for col in SENSITIVITY_MATRIX_AR['cols'])}</tr>
{"".join(f"<tr><td><strong>{row}</strong></td>{''.join(f'<td>{v:,}</td>' for v in vals)}</tr>" for row, vals in zip(SENSITIVITY_MATRIX_AR['rows'], SENSITIVITY_MATRIX_AR['values']))}
</table>
<p>مصفوفة الحساسية (معدل الخصم × معدل النمو) — انظر ورقة Excel: Sensitivity Matrix</p>
<p class='excel-ref'>ورقة Excel: Sensitivity Matrix</p>

<h2>12. سجل المخاطر / Risk Register</h2>
<table>
<tr><th>نوع الخطر</th><th>الخطورة</th><th>التأثير</th><th>تأثير القيمة %</th></tr>
{"".join(f"<tr><td>{r['risk']}</td><td class='warn'>{r['severity']}</td><td>{r['impact']}</td><td>—</td></tr>" for r in RISKS_AR)}
</table>
<div class='hl'>القيمة المعدَّلة بالمخاطر: {int(RECONCILIATION_AR['final_opinion_rounded'] * 0.97):,} SAR (تقليص افتراضي 3% لمجمل المخاطر)</div>
<p class='excel-ref'>ورقة Excel: Risk Register</p>

<h2>13. موثوقية مؤشر التقييم الآلي / AVM Reliability</h2>
{_kv_table([
    ("مؤشر AVM", f"{AVM_AR['avm_indicated_value']:,} SAR"),
    ("معامل الثقة", f"{AVM_AR['confidence_score']:.0%}"),
    ("عدد المقارنات", str(AVM_AR['comparable_count'])),
    ("حدود الاعتماد", AVM_AR["note"]),
    ("موثوقية المؤشر", "متوسطة — يُستخدم كتحقق مساعد فقط"),
])}
<p class='excel-ref'>ورقة Excel: AVM Reference</p>

<h2>14. التوفيق والترجيح النهائي / Reconciliation</h2>
<table>
<tr><th>الأسلوب</th><th>القيمة SAR</th><th>الوزن %</th><th>القيمة المرجحة SAR</th><th>مبرر الوزن</th></tr>
{"".join(f"<tr><td>{sc['approach']}</td><td>{sc['value_sar']:,}</td><td>{sc['weight_pct']}%</td><td>{sc['weighted_sar']:,}</td><td>{'بيانات كافية ومحدثة' if 'سوق' in sc['approach'] else 'دخل إيجاري مستقر' if 'دخل' in sc['approach'] else 'للتحقق فقط'}</td></tr>" for sc in RECONCILIATION_SCORECARD_AR)}
</table>
<div class='val-box'>القيمة المرجحة النهائية: {RECONCILIATION_AR['weighted_value']:,} SAR</div>
<div class='val-box'>رأي المقيّم (احترافي): {RECONCILIATION_AR['final_opinion_rounded']:,} SAR ± 5%</div>
<p class='excel-ref'>ورقة Excel: Reconciliation</p>

<h2>15. مصفوفة المعايير والإفصاحات / Standards Matrix</h2>
<table>
<tr><th>المعيار</th><th>البند</th><th>الحالة</th></tr>
{"".join(f"<tr><td>{s['standard']}</td><td>{s['name']}</td><td class='ok'>{s['status']}</td></tr>" for s in STANDARDS_AR)}
<tr><td>RICS Red Book</td><td>الكتاب الأحمر</td><td class='warn'>مكتمل جزئياً</td></tr>
<tr><td>Basel III</td><td>سياق ضمانات الائتمان</td><td class='ok'>مطابق</td></tr>
</table>
<p class='excel-ref'>ورقة Excel: Standards Matrix</p>

<h2>16. سجل مصادر البيانات / Source Registry</h2>
<p>تم توثيق 8 مصادر بيانات في ورقة "Source Registry" من ملف Excel الإداري.</p>
<p class='excel-ref'>ورقة Excel: Source Registry</p>

<h2>17. مقارنة أساليب Excel القديم</h2>
<table>
<tr><th>الأسلوب</th><th>ورقة Excel الجديدة</th><th>الورقة القديمة (GRAND_FINAL)</th></tr>
<tr><td>أسلوب السوق</td><td>Comparables</td><td>LEGACY_GF_مقارنات البيوع</td></tr>
<tr><td>أسلوب الدخل</td><td>Income Approach</td><td>LEGACY_GF_رأسمالة الدخل</td></tr>
<tr><td>أسلوب التكلفة</td><td>Cost Approach</td><td>LEGACY_GF_طريقة التكلفة</td></tr>
<tr><td>DCF</td><td>Income Approach (DCF)</td><td>LEGACY_GF_DCF — التدفقات النقدية</td></tr>
<tr><td>تحليل الحساسية</td><td>Sensitivity Matrix</td><td>LEGACY_GF_📊 تحليل الحساسية</td></tr>
<tr><td>HBU</td><td>HBU Analysis</td><td>LEGACY_GF_أفضل وأعلى استخدام — HABU</td></tr>
<tr><td>التوفيق</td><td>Reconciliation</td><td>LEGACY_GF_توفيق النتائج</td></tr>
<tr><td>لوحة القيادة</td><td>Cover</td><td>LEGACY_GF_لوحة القيادة التنفيذية</td></tr>
</table>
<p class='excel-ref'>الأوراق القديمة محفوظة في الملف الإداري كأرشيف بادئة LEGACY_GF_ و LEGACY_ULTRA_</p>

<h2>18. بوابة مراجعة الخبير / Expert Review Gate</h2>
<div class='hl'>
<strong>حالة الاعتماد:</strong> لم يُعتمد بعد — بانتظار مراجعة الخبير.<br>
<strong>certification_ready:</strong> False<br>
<strong>fake_approval_created:</strong> False<br>
لا يتم إصدار تقرير معتمد إلا بعد مراجعة الخبير واعتماده عبر ورقة "Admin Notes" في الملف الإداري.
</div>
<p class='excel-ref'>ورقة Excel: Admin Notes</p>
"""
    return _html_wrap("تقرير التقييم الاحترافي", body, "تقرير احترافي — مسودة استرشادية")


# ── Chrome PDF renderer ───────────────────────────────────────────────────────

def _render_pdf(html_str: str, pdf_out: Path) -> bool:
    pdf_out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, encoding="utf-8", mode="w") as f:
        f.write(html_str)
        tmp = Path(f.name)
    cmd = [
        str(_CHROME), "--headless=new", "--no-sandbox",
        "--disable-gpu", "--disable-extensions",
        f"--print-to-pdf={pdf_out}", "--print-to-pdf-no-header",
        str(tmp),
    ]
    try:
        result = subprocess.run(cmd, timeout=60, capture_output=True)
        tmp.unlink(missing_ok=True)
        return pdf_out.exists() and pdf_out.stat().st_size > 5_000
    except Exception:
        tmp.unlink(missing_ok=True)
        return False


def generate_all_pdfs(pdf_out: Path, preview_out: Path) -> dict:
    pdf_out.mkdir(parents=True, exist_ok=True)
    preview_out.mkdir(parents=True, exist_ok=True)

    reports = {
        "traditional_report": (_build_traditional_html, "تقليدي"),
        "detailed_report":    (_build_detailed_html,    "تفصيلي"),
        "professional_report":(_build_professional_html, "احترافي"),
    }
    results = {}
    for key, (builder, level) in reports.items():
        html = builder()
        prev_path = preview_out / f"{key}_preview.html"
        prev_path.write_text(html, encoding="utf-8")
        ok = _render_pdf(html, pdf_out / f"{key}.pdf")
        size = (pdf_out / f"{key}.pdf").stat().st_size if ok else 0
        h2_count = html.count("<h2>")
        results[key] = {
            "rendered": ok, "size_bytes": size,
            "h2_sections": h2_count, "level": level,
        }
    return results
