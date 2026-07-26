"""
hbu_enhanced_excel.py
Enhanced HBU Excel builder — 15 sheets + BarChart + LineChart
Uses openpyxl (no xlsxwriter). Admin-only artifact.

No local file paths in cell values.
Governance: advisory_only=True · non_certified=True
"""
from __future__ import annotations

import pathlib
from typing import Any, Dict, List, Optional

try:
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.chart import BarChart, Reference, LineChart
    from openpyxl.chart.series import DataPoint
    _HAS_OPENPYXL = True
except ImportError:
    _HAS_OPENPYXL = False


# ─── Color palette ─────────────────────────────────────────────────────────────
NAVY   = "1F3864"
GOLD   = "C9A227"
GREEN  = "1E8449"
RED    = "C0392B"
BLUE   = "2471A3"
WHITE  = "FFFFFF"
LIGHT  = "EAF0FB"
GREY   = "F2F2F2"
AMBER  = "E59866"
DARK   = "0F172A"


def _fill(hex_color: str) -> "PatternFill":
    return PatternFill("solid", fgColor=hex_color)


def _font(bold=False, color=WHITE, size=11) -> "Font":
    return Font(bold=bold, color=color, size=size, name="Calibri")


def _align(horizontal="right", vertical="center", wrap=False) -> "Alignment":
    return Alignment(horizontal=horizontal, vertical=vertical, wrap_text=wrap)


def _border() -> "Border":
    side = Side(border_style="thin", color="A0A0A0")
    return Border(left=side, right=side, top=side, bottom=side)


def _write_header(ws, row: int, col: int, text: str, merge_to: int = 0):
    cell = ws.cell(row=row, column=col, value=text)
    cell.fill    = _fill(NAVY)
    cell.font    = _font(bold=True, color=WHITE, size=11)
    cell.alignment = _align(horizontal="center", vertical="center")
    cell.border  = _border()
    if merge_to > col:
        ws.merge_cells(start_row=row, start_column=col,
                       end_row=row, end_column=merge_to)


def _write_title(ws, row: int, text: str, ncols: int):
    cell = ws.cell(row=row, column=1, value=text)
    cell.fill    = _fill(GOLD)
    cell.font    = Font(bold=True, color=NAVY, size=13, name="Calibri")
    cell.alignment = _align(horizontal="center", vertical="center")
    cell.border  = _border()
    if ncols > 1:
        ws.merge_cells(start_row=row, start_column=1,
                       end_row=row, end_column=ncols)
    ws.row_dimensions[row].height = 30


def _write_kv(ws, row: int, label: str, value: Any, fmt: Optional[str] = None):
    lc = ws.cell(row=row, column=1, value=label)
    lc.fill = _fill(LIGHT)
    lc.font = Font(bold=True, color=DARK, size=10, name="Calibri")
    lc.alignment = _align()
    lc.border = _border()

    vc = ws.cell(row=row, column=2, value=value)
    vc.font = Font(color=DARK, size=10, name="Calibri")
    vc.alignment = _align()
    vc.border = _border()
    if fmt:
        vc.number_format = fmt


def _apply_rtl(ws):
    ws.sheet_view.rightToLeft = True


# ─── Individual sheet builders ─────────────────────────────────────────────────

def _sheet_summary(wb, case_data, hbu_result, fd):
    ws = wb.create_sheet("ملخص_HBU")
    _apply_rtl(ws)
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 40

    _write_title(ws, 1, "تقرير تحليل أعلى وأفضل استخدام (HBU)", 2)
    _write_kv(ws, 2, "رمز المهمة", case_data.get("case_id", "—"))
    _write_kv(ws, 3, "تاريخ التقييم", case_data.get("valuation_date", "—"))
    _write_kv(ws, 4, "المدينة / الحي",
              f'{case_data.get("city_ar","—")} / {case_data.get("district_ar","—")}')
    _write_kv(ws, 5, "مساحة الأرض (م²)", case_data.get("land_area_m2", 0), "#,##0")
    _write_kv(ws, 6, "الاستخدام الحالي", case_data.get("current_use", "—"))
    _write_kv(ws, 7, "العملة", case_data.get("currency", "ريال"))
    _write_kv(ws, 8, "معدل الخصم", hbu_result.get("discount_rate", 0.10), "0.00%")

    ws.row_dimensions[9].height = 6
    _write_kv(ws, 10, "أعلى وأفضل استخدام", hbu_result.get("recommended_use", "—"))
    _write_kv(ws, 11, "صافي القيمة الحالية (NPV)", hbu_result.get("recommended_npv"), "#,##0")
    _write_kv(ws, 12, "القيمة الإجمالية للتطوير (GDV)", fd.get("gdv"), "#,##0")
    _write_kv(ws, 13, "إجمالي تكاليف التطوير (TDC)", fd.get("tdc"), "#,##0")
    _write_kv(ws, 14, "القيمة المتبقية للأرض (RLV)", fd.get("rlv"), "#,##0")
    _write_kv(ws, 15, "RLV / م²", fd.get("rlv_per_m2"), "#,##0.00")
    _write_kv(ws, 16, "فترة الاسترداد (سنوات)", fd.get("payback_years"), "0.00")
    _write_kv(ws, 17, "IRR المشروع %", fd.get("irr_project_pct"), "0.00%")
    _write_kv(ws, 18, "IRR المستثمر %", fd.get("irr_investor_pct"), "0.00%")
    _write_kv(ws, 19, "هامش المطوّر %", fd.get("dev_margin_pct"), "0.00%")

    ws.row_dimensions[20].height = 6
    note_cell = ws.cell(row=21, column=1,
                         value="advisory_only=True | non_certified=True | fake_signature_created=False")
    note_cell.fill = _fill(AMBER)
    note_cell.font = Font(bold=True, color=DARK, size=9, name="Calibri")
    note_cell.alignment = _align(horizontal="center")
    ws.merge_cells("A21:B21")


def _sheet_provenance(wb, provenance_table):
    ws = wb.create_sheet("مصدرية_المدخلات")
    _apply_rtl(ws)
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 28
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 12
    ws.column_dimensions["E"].width = 22
    ws.column_dimensions["F"].width = 16
    ws.column_dimensions["G"].width = 12
    ws.column_dimensions["H"].width = 16
    ws.column_dimensions["I"].width = 36

    _write_title(ws, 1, "جدول مصدرية المدخلات", 9)
    headers = ["المُعرِّف", "المدخل", "القيمة", "الوحدة", "المصدر", "الطبقة", "الثقة%", "الحالة", "ملاحظة التوفيق"]
    for c, h in enumerate(headers, 1):
        _write_header(ws, 2, c, h)

    tier_colors = {
        "Tier-1 محوكم": GREEN,
        "Tier-1 محوكم (مشتق)": GREEN,
        "Tier-2 Draft": AMBER,
        "N/A": "808080",
    }

    for r, p in enumerate(provenance_table, 3):
        tier  = p.get("source_tier", "N/A")
        tcolor = tier_colors.get(tier, "808080")
        val   = p.get("value_used")

        cells_data = [
            (p.get("input_id", ""), None),
            (p.get("label_ar", ""), None),
            (val, "#,##0.00" if val is not None else None),
            (p.get("unit", ""), None),
            (p.get("source_name", ""), None),
            (tier, None),
            (p.get("confidence_score", 0), "0"),
            (p.get("status", ""), None),
            (p.get("reconciliation_note", "")[:80], None),
        ]
        for c, (v, fmt) in enumerate(cells_data, 1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.font = Font(color=DARK, size=9, name="Calibri")
            cell.alignment = _align(wrap=(c == 9))
            cell.border = _border()
            if fmt and v is not None:
                cell.number_format = fmt
            if c == 6:
                cell.fill = _fill(tcolor)
                cell.font = Font(bold=True, color=WHITE, size=9, name="Calibri")
            elif r % 2 == 0:
                cell.fill = _fill(GREY)


def _sheet_site(wb, case_data, sourcing):
    ws = wb.create_sheet("بيانات_الموقع")
    _apply_rtl(ws)
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 36

    _write_title(ws, 1, "المحور A — دراسة الموقع", 2)
    mi = sourcing.get("market_inputs", {})
    rows = [
        ("المدينة", case_data.get("city_ar", "—")),
        ("الحي", case_data.get("district_ar", "—")),
        ("مساحة الأرض (م²)", case_data.get("land_area_m2", 0)),
        ("الواجهة (م)", case_data.get("frontage_m", 40)),
        ("العمق (م)", case_data.get("depth_m", 60)),
        ("عرض الشارع (م)", case_data.get("road_width_m", 30)),
        ("الاستخدام الحالي", case_data.get("current_use", "—")),
        ("مؤشر سعر المتر (نموذج مجمع)", mi.get("land_ppm_indicator")),
        ("القيمة السوقية التأشيرية", mi.get("market_value_indicator")),
        ("نقاط القوة", "موقع متميز — واجهة رئيسية — سهولة الوصول"),
        ("نقاط الضعف", "استخدام حالي منخفض الكثافة"),
        ("الفرص", "نمو سوق الرياض — رؤية 2030 — بنية تحتية"),
        ("التهديدات", "تذبذب أسعار مواد البناء — زيادة العرض"),
    ]
    for i, (lbl, val) in enumerate(rows, 2):
        _write_kv(ws, i, lbl, val, "#,##0" if isinstance(val, (int, float)) else None)


def _sheet_market(wb, case_data, sourcing):
    ws = wb.create_sheet("الذكاء_السوقي")
    _apply_rtl(ws)
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 22
    ws.column_dimensions["C"].width = 16

    _write_title(ws, 1, "المحور B — الذكاء السوقي", 3)
    mi = sourcing.get("market_inputs", {})
    _write_header(ws, 2, 1, "المؤشر")
    _write_header(ws, 2, 2, "القيمة")
    _write_header(ws, 2, 3, "المصدر")

    indicators = [
        ("مؤشر سعر المتر (نموذج مجمع)", mi.get("land_ppm_indicator"), "نموذج AVM-v1"),
        ("معدل الرسملة", mi.get("cap_rate"), "بحث/افتراض"),
        ("الإيجار السكني / م²", mi.get("market_rent_residential_pm2"), "Draft محوكم"),
        ("الإيجار التجاري / م²", mi.get("market_rent_commercial_pm2"), "Draft محوكم"),
        ("تكلفة البناء / م²", mi.get("construction_cost_pm2"), "نموذج AVM-v1 (مشتق)"),
        ("معدل الإشغال السكني", mi.get("occupancy_residential"), "Draft محوكم"),
        ("معدل الاستيعاب", mi.get("absorption_rate_pct"), "طبقة الإثراء"),
        ("معدل الشواغر السوقي", mi.get("market_vacancy_rate"), "Draft محوكم"),
        ("معدل الخصم", mi.get("discount_rate"), "افتراض/Draft"),
        ("معدل النمو السنوي", mi.get("annual_growth_rate"), "افتراض/Draft"),
    ]

    for r, (lbl, val, src) in enumerate(indicators, 3):
        ws.cell(row=r, column=1, value=lbl).font = Font(color=DARK, size=10, name="Calibri")
        ws.cell(row=r, column=1).alignment = _align()
        ws.cell(row=r, column=1).border = _border()
        ws.cell(row=r, column=1).fill = _fill(LIGHT)

        vc = ws.cell(row=r, column=2, value=val)
        vc.font = Font(color=DARK, size=10, name="Calibri")
        vc.alignment = _align()
        vc.border = _border()
        if isinstance(val, float) and val < 1:
            vc.number_format = "0.00%"
        elif isinstance(val, (int, float)):
            vc.number_format = "#,##0.00"

        ws.cell(row=r, column=3, value=src).font = Font(color="808080", size=9, name="Calibri")
        ws.cell(row=r, column=3).alignment = _align()
        ws.cell(row=r, column=3).border = _border()


def _sheet_concepts(wb, alternatives, hbu_result):
    ws = wb.create_sheet("المفاهيم_التطويرية")
    _apply_rtl(ws)
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 34
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 16
    ws.column_dimensions["E"].width = 16

    _write_title(ws, 1, "المحور C — المفاهيم التطويرية", 5)
    headers = ["المعرف", "الاستخدام البديل", "تكلفة البناء", "الإيراد السنوي", "هل HBU؟"]
    for c, h in enumerate(headers, 1):
        _write_header(ws, 2, c, h)

    rec = hbu_result.get("recommended_use", "")
    for r, alt in enumerate(alternatives, 3):
        is_hbu = (alt.get("use_name", "") == rec)
        bg = GREEN if is_hbu else (LIGHT if r % 2 == 0 else WHITE)
        txt_color = WHITE if is_hbu else DARK
        cells = [
            alt.get("alternative_id", f"ALT-{r-2:02d}"),
            alt.get("name_ar", alt.get("use_name", "—")),
            alt.get("construction_cost", 0),
            alt.get("annual_revenue", 0),
            "★ نعم" if is_hbu else "—",
        ]
        fmts = [None, None, "#,##0", "#,##0", None]
        for c, (v, fmt) in enumerate(zip(cells, fmts), 1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.fill = _fill(bg)
            cell.font = Font(bold=is_hbu, color=txt_color, size=10, name="Calibri")
            cell.alignment = _align()
            cell.border = _border()
            if fmt and isinstance(v, (int, float)):
                cell.number_format = fmt


def _sheet_four_tests(wb, hbu_result, sheet_prefix="اختبار", start_num=6):
    test_names = {
        "test_1": ("اختبار_قانوني", "Test 1 — ممكن قانونياً",
                   "is_legally_permissible", "legal_note"),
        "test_2": ("اختبار_مادي",   "Test 2 — ممكن مادياً",
                   "is_physically_possible", "physical_note"),
        "test_3": ("اختبار_مالي",   "Test 3 — مجدٍ مالياً",
                   "financially_feasible",   ""),
    }

    for test_id, (sheet_name, title, field, note_field) in test_names.items():
        ws = wb.create_sheet(sheet_name)
        _apply_rtl(ws)
        ws.column_dimensions["A"].width = 28
        ws.column_dimensions["B"].width = 20
        ws.column_dimensions["C"].width = 36

        _write_title(ws, 1, title, 3)
        _write_header(ws, 2, 1, "البديل")
        _write_header(ws, 2, 2, "النتيجة")
        _write_header(ws, 2, 3, "الملاحظة")

        for r, s in enumerate(hbu_result.get("scenarios_evaluated", []), 3):
            if test_id == "test_3":
                pass_v = s.get("test_3_financial", False)
            elif test_id == "test_2":
                pass_v = s.get("test_2_physical", False)
            else:
                pass_v = s.get("test_1_legal", False)

            note = s.get(note_field, "") if note_field else s.get("verdict_so_far", "")
            bg   = GREEN if pass_v else RED
            ws.cell(row=r, column=1, value=s["use_name"]).font = Font(color=DARK, size=10)
            ws.cell(row=r, column=1).border = _border()
            ws.cell(row=r, column=1).fill = _fill(LIGHT)

            res_cell = ws.cell(row=r, column=2, value="✔ يجتاز" if pass_v else "✗ لا يجتاز")
            res_cell.fill = _fill(bg)
            res_cell.font = Font(bold=True, color=WHITE, size=10)
            res_cell.alignment = _align(horizontal="center")
            res_cell.border = _border()

            ws.cell(row=r, column=3, value=note[:80]).font = Font(color="606060", size=9)
            ws.cell(row=r, column=3).border = _border()
            ws.cell(row=r, column=3).alignment = _align(wrap=True)


def _sheet_max_productive(wb, hbu_result):
    ws = wb.create_sheet("أعلى_إنتاجية")
    _apply_rtl(ws)
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 40

    _write_title(ws, 1, "Test 4 — أعلى إنتاجية (HBU الموصى به)", 2)
    _write_kv(ws, 2, "الاستخدام الموصى به", hbu_result.get("recommended_use", "—"))
    _write_kv(ws, 3, "NPV الموصى به", hbu_result.get("recommended_npv"), "#,##0")
    note_cell = ws.cell(row=4, column=1, value=hbu_result.get("recommendation_note", ""))
    note_cell.fill = _fill(LIGHT)
    note_cell.font = Font(color=DARK, size=10, name="Calibri")
    note_cell.alignment = _align(wrap=True)
    note_cell.border = _border()
    ws.merge_cells("A4:B4")
    ws.row_dimensions[4].height = 50


def _sheet_financial_depth(wb, fd, currency):
    ws = wb.create_sheet("العمق_المالي")
    _apply_rtl(ws)
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 22

    _write_title(ws, 1, "المحور D.3 — القيمة المتبقية للأرض (RLV) والمقاييس المالية", 2)
    rows = [
        ("القيمة الإجمالية للتطوير (GDV)", fd.get("gdv")),
        ("إجمالي تكاليف التطوير (TDC)", fd.get("tdc")),
        ("  — تكلفة البناء الأساسية", fd.get("land_cost")),
        ("  — رسوم تمويلية", fd.get("finance_cost")),
        ("  — رسوم مهنية (10%)", fd.get("professional_fees")),
        ("  — احتياطي طوارئ (5%)", fd.get("contingency")),
        ("هامش المطوّر المستهدف (15% GDV)", fd.get("dev_profit_target")),
        ("القيمة المتبقية للأرض (RLV)", fd.get("rlv")),
        ("RLV / م²", fd.get("rlv_per_m2")),
        ("تكلفة الأرض المُدفوعة", fd.get("land_cost")),
        ("تكلفة الأرض / م²", fd.get("land_cost_per_m2")),
        ("جدوى RLV", fd.get("rlv_viability")),
        ("فترة الاسترداد (سنوات)", fd.get("payback_years")),
        ("IRR المشروع %", fd.get("irr_project_pct")),
        ("IRR المستثمر %", fd.get("irr_investor_pct")),
        ("هامش المطوّر الفعلي %", fd.get("dev_margin_pct")),
    ]
    for r, (lbl, val) in enumerate(rows, 2):
        _write_kv(ws, r, lbl, val,
                  "#,##0" if isinstance(val, (int, float)) and abs(val) > 1 else
                  ("0.00%" if isinstance(val, (int, float)) and abs(val) <= 1 else None))

    real_opt_cell = ws.cell(row=len(rows) + 3, column=1,
                             value=fd.get("real_options_note", "—"))
    real_opt_cell.font = Font(italic=True, color="606060", size=9, name="Calibri")
    real_opt_cell.alignment = _align(wrap=True)
    ws.merge_cells(f"A{len(rows)+3}:B{len(rows)+3}")
    ws.row_dimensions[len(rows) + 3].height = 40


def _sheet_sensitivity(wb, fd, currency):
    ws = wb.create_sheet("حساسية_متعددة")
    _apply_rtl(ws)
    _write_title(ws, 1, "المحور D.4 — تحليل الحساسية متعدد المتغيرات", 5)

    sg = fd.get("sensitivity_grid", {})
    matrix    = sg.get("npv_matrix", [])
    rev_mults = sg.get("rev_mults", [0.85, 1.00, 1.15])
    cost_mults= sg.get("cost_mults", [0.85, 1.00, 1.15])

    ws.cell(row=2, column=1, value="الإيراد \\ التكلفة").font = _font(bold=True, color=DARK)
    ws.cell(row=2, column=1).fill = _fill(NAVY)
    ws.cell(row=2, column=1).font = Font(bold=True, color=WHITE, size=10)
    ws.cell(row=2, column=1).alignment = _align(horizontal="center")
    ws.cell(row=2, column=1).border = _border()

    for c, cm in enumerate(cost_mults, 2):
        lbl = f"تكلفة {int(cm*100)}%"
        ws.cell(row=2, column=c, value=lbl).fill = _fill(NAVY)
        ws.cell(row=2, column=c).font = Font(bold=True, color=WHITE, size=10)
        ws.cell(row=2, column=c).alignment = _align(horizontal="center")
        ws.cell(row=2, column=c).border = _border()

    all_vals = [v for row in matrix for v in row if v is not None]
    max_v = max(all_vals) if all_vals else 1
    min_v = min(all_vals) if all_vals else 0

    for r, (rm, row_vals) in enumerate(zip(rev_mults, matrix), 3):
        lbl = f"إيراد {int(rm*100)}%"
        ws.cell(row=r, column=1, value=lbl).fill = _fill(NAVY)
        ws.cell(row=r, column=1).font = Font(bold=True, color=WHITE, size=10)
        ws.cell(row=r, column=1).alignment = _align()
        ws.cell(row=r, column=1).border = _border()

        for c, v in enumerate(row_vals, 2):
            cell = ws.cell(row=r, column=c, value=v)
            cell.number_format = "#,##0"
            cell.alignment = _align(horizontal="center")
            cell.border = _border()
            if v is not None:
                ratio = (v - min_v) / max(max_v - min_v, 1)
                gr = int(180 * ratio)
                rd = int(200 * (1 - ratio))
                cell.fill = PatternFill("solid", fgColor=f"{rd:02X}{gr:02X}3C")
                cell.font = Font(color=WHITE, size=10, name="Calibri")

    # Discount rate sensitivity
    ws.row_dimensions[len(matrix) + 4].height = 10
    start_dr = len(matrix) + 5
    _write_title(ws, start_dr, "حساسية معدل الخصم", 4)
    headers_dr = ["معدل الخصم %", "NPV", "IRR %", "الجدوى"]
    for c, h in enumerate(headers_dr, 1):
        _write_header(ws, start_dr + 1, c, h)

    dr_sens = fd.get("discount_rate_sensitivity", [])
    for r, dr in enumerate(dr_sens, start_dr + 2):
        npv = dr.get("npv")
        irr = dr.get("irr_pct")
        rate= dr.get("discount_rate_pct", 0)
        viab = "مجدٍ" if (npv or 0) > 0 else "غير مجدٍ"
        bg   = GREEN if (npv or 0) > 0 else RED
        vals = [f"{rate:.0f}%", npv, irr, viab]
        for c, v in enumerate(vals, 1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.font = Font(bold=(c == 4), color=WHITE if c == 4 else DARK, size=10)
            cell.alignment = _align(horizontal="center")
            cell.border = _border()
            if c == 4:
                cell.fill = _fill(bg)
            elif r % 2 == 0:
                cell.fill = _fill(GREY)
            if c in (2, 3) and isinstance(v, (int, float)):
                cell.number_format = "#,##0" if c == 2 else "0.00%"

    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 12


def _sheet_comparison(wb, hbu_result):
    ws = wb.create_sheet("مقارنة_البدائل")
    _apply_rtl(ws)
    headers = ["البديل", "قانوني", "مادي", "مالي", "أعلى إنتاجية", "NPV", "IRR%",
               "فترة الاسترداد", "الحكم النهائي"]
    widths  = [30, 10, 10, 10, 16, 18, 10, 18, 36]
    _write_title(ws, 1, "جدول مقارنة البدائل — جميع الاختبارات", len(headers))
    for c, (h, w) in enumerate(zip(headers, widths), 1):
        _write_header(ws, 2, c, h)
        ws.column_dimensions[chr(64 + c)].width = w

    rec = hbu_result.get("recommended_use", "")
    for r, row in enumerate(hbu_result.get("comparison_table", []), 3):
        is_hbu = row.get("maximally_productive", False)
        bg     = GREEN if is_hbu else (LIGHT if r % 2 == 0 else WHITE)
        tc     = WHITE if is_hbu else DARK

        vals = [
            row["use_name"],
            "✔" if row["legally_permissible"]  else "✗",
            "✔" if row["physically_possible"]  else "✗",
            "✔" if row["financially_feasible"] else "✗",
            "★" if row["maximally_productive"] else "—",
            row["npv"],
            (row["irr_pct"] or 0) / 100 if row["irr_pct"] else None,
            row["payback_years"],
            row["verdict"],
        ]
        fmts = [None, None, None, None, None, "#,##0", "0.00%", "0.00", None]
        for c, (v, fmt) in enumerate(zip(vals, fmts), 1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.fill = _fill(bg)
            cell.font = Font(bold=is_hbu, color=tc, size=10, name="Calibri")
            cell.alignment = _align(wrap=(c == len(vals)))
            cell.border = _border()
            if fmt and v is not None:
                cell.number_format = fmt


def _sheet_cashflows(wb, hbu_result):
    ws = wb.create_sheet("التدفقات_النقدية")
    _apply_rtl(ws)
    scenarios = hbu_result.get("scenarios_evaluated", [])
    max_yrs = max((len(s["cashflows"]) for s in scenarios), default=0)

    _write_title(ws, 1, "التدفقات النقدية السنوية لكل بديل", max_yrs + 2)
    ws.cell(row=2, column=1, value="البديل").fill = _fill(NAVY)
    ws.cell(row=2, column=1).font = _font(bold=True)
    ws.cell(row=2, column=1).alignment = _align(horizontal="center")
    ws.cell(row=2, column=1).border = _border()
    ws.column_dimensions["A"].width = 28

    for y in range(max_yrs):
        c = y + 2
        ws.cell(row=2, column=c, value=f"سنة {y}").fill = _fill(NAVY)
        ws.cell(row=2, column=c).font = _font(bold=True)
        ws.cell(row=2, column=c).alignment = _align(horizontal="center")
        ws.cell(row=2, column=c).border = _border()
        ws.column_dimensions[ws.cell(row=2, column=c).column_letter].width = 16

    rec = hbu_result.get("recommended_use", "")
    for r, s in enumerate(scenarios, 3):
        is_hbu = (s["use_name"] == rec)
        bg     = GREEN if is_hbu else (LIGHT if r % 2 == 0 else WHITE)
        tc     = WHITE if is_hbu else DARK

        ws.cell(row=r, column=1, value=s["use_name"]).fill = _fill(bg)
        ws.cell(row=r, column=1).font = Font(bold=is_hbu, color=tc, size=10)
        ws.cell(row=r, column=1).border = _border()
        ws.cell(row=r, column=1).alignment = _align()

        for y, cf in enumerate(s["cashflows"]):
            cell = ws.cell(row=r, column=y + 2, value=cf)
            cell.number_format = "#,##0"
            cell.font = Font(color=(RED if cf < 0 else DARK), size=10)
            cell.alignment = _align(horizontal="center")
            cell.border = _border()
            if is_hbu:
                cell.fill = _fill(GREEN if cf >= 0 else RED)
                cell.font = Font(color=WHITE, size=10)


def _sheet_risks(wb, case_data):
    ws = wb.create_sheet("مخاطر_وقيود")
    _apply_rtl(ws)
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 36
    ws.column_dimensions["C"].width = 36

    _write_title(ws, 1, "المحور E — المخاطر وخطط التخفيف", 3)
    _write_header(ws, 2, 1, "نوع المخاطرة")
    _write_header(ws, 2, 2, "التأثير المحتمل")
    _write_header(ws, 2, 3, "إجراء التخفيف")

    risks = [
        ("مخاطر السوق",    "انخفاض الإيرادات > 15% يؤثر على RLV",    "دراسة تأجير مسبق"),
        ("مخاطر التكلفة",  "تقلبات أسعار مواد البناء",                 "عقود بسقف سعري ثابت"),
        ("مخاطر التنظيم",  "تغيير اشتراطات التخطيط",                   "الحصول على التصاريح مبكراً"),
        ("مخاطر التمويل",  "ارتفاع معدلات الإقراض",                    "تمويل بسعر ثابت"),
        ("مخاطر الإشغال",  "بطء الاستيعاب السوقي",                     "تسويق مبكر"),
    ]
    for r, (rtype, impact, mitigation) in enumerate(risks, 3):
        for c, v in enumerate([rtype, impact, mitigation], 1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.font = Font(color=DARK, size=10, name="Calibri")
            cell.alignment = _align(wrap=True)
            cell.border = _border()
            cell.fill = _fill(AMBER if c == 2 else (GREEN if c == 3 else LIGHT))


def _sheet_governance(wb, case_data):
    ws = wb.create_sheet("حوكمة_وإفصاحات")
    _apply_rtl(ws)
    ws.column_dimensions["A"].width = 36
    ws.column_dimensions["B"].width = 40

    _write_title(ws, 1, "الحوكمة والإفصاحات", 2)
    gov_flags = [
        ("advisory_only",                    "True"),
        ("certification_ready",              "False"),
        ("fake_reviewer_signature_created",  "False"),
        ("non_certified",                    "True"),
        ("not_real_training_data",           "True"),
        ("web_research_label",               "مسح مبدئي محوكم — Draft"),
        ("source_priority",                  "mass_appraisal > web_research > enrichment > default"),
    ]
    for r, (flag, val) in enumerate(gov_flags, 2):
        _write_kv(ws, r, flag, val)

    disclaimer_cell = ws.cell(
        row=len(gov_flags) + 3, column=1,
        value=(
            "هذا التحليل استرشادي وغير معتمد. "
            "لا يمثل رأياً مهنياً نهائياً أو شهادة تقييم أو قراراً تنظيمياً. "
            "يجب مراجعة الافتراضات بواسطة مختص معتمد قبل الاعتماد على النتائج."
        )
    )
    disclaimer_cell.fill = _fill(AMBER)
    disclaimer_cell.font = Font(bold=True, color=DARK, size=10, name="Calibri")
    disclaimer_cell.alignment = _align(wrap=True)
    disclaimer_cell.border = _border()
    ws.merge_cells(f"A{len(gov_flags)+3}:B{len(gov_flags)+3}")
    ws.row_dimensions[len(gov_flags) + 3].height = 60


def _sheet_source_log(wb, sourcing):
    ws = wb.create_sheet("سجل_المصادر")
    _apply_rtl(ws)
    for c, (h, w) in enumerate(
        [("ID", 16), ("النوع", 18), ("الاسم", 28), ("URI", 36), ("الثقة%", 10)], 1
    ):
        _write_header(ws, 1, c, h)
        ws.column_dimensions[ws.cell(row=1, column=c).column_letter].width = w

    for r, src in enumerate(sourcing.get("source_log", []), 2):
        uri = str(src.get("source_uri") or src.get("url") or "")
        for c, v in enumerate([
            src.get("source_id", ""),
            src.get("source_type", ""),
            src.get("source_name", ""),
            uri[:60],
            src.get("confidence_score", ""),
        ], 1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.font = Font(color=DARK, size=9, name="Calibri")
            cell.alignment = _align()
            cell.border = _border()
            if r % 2 == 0:
                cell.fill = _fill(GREY)


def _add_npv_chart(wb, hbu_result):
    """Add BarChart for NPV comparison in a dedicated chart sheet."""
    ws_data = wb.create_sheet("_chart_data_npv")
    ws_data.sheet_state = "hidden"

    scenarios = hbu_result.get("scenarios_evaluated", [])
    ws_data.cell(row=1, column=1, value="البديل")
    ws_data.cell(row=1, column=2, value="NPV")
    for r, s in enumerate(scenarios, 2):
        ws_data.cell(row=r, column=1, value=s["use_name"][:15])
        ws_data.cell(row=r, column=2, value=round(s["npv"]))

    ws_chart = wb.create_sheet("مخطط_NPV")
    chart = BarChart()
    chart.type = "col"
    chart.title = "NPV لكل بديل"
    chart.y_axis.title = "NPV (ريال)"
    chart.x_axis.title = "البديل"
    chart.style = 10
    chart.width = 20
    chart.height = 12

    n = len(scenarios)
    data_ref   = Reference(ws_data, min_col=2, min_row=1, max_row=n + 1)
    cats_ref   = Reference(ws_data, min_col=1, min_row=2, max_row=n + 1)
    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats_ref)
    ws_chart.add_chart(chart, "A1")


def _add_sensitivity_chart(wb, fd):
    """Add LineChart for discount rate sensitivity."""
    ws_data = wb.create_sheet("_chart_data_sens")
    ws_data.sheet_state = "hidden"

    dr_sens = fd.get("discount_rate_sensitivity", [])
    ws_data.cell(row=1, column=1, value="معدل الخصم%")
    ws_data.cell(row=1, column=2, value="NPV")
    for r, dr in enumerate(dr_sens, 2):
        ws_data.cell(row=r, column=1, value=dr.get("discount_rate_pct", 0))
        ws_data.cell(row=r, column=2, value=dr.get("npv"))

    ws_chart = wb.create_sheet("مخطط_الحساسية")
    chart = LineChart()
    chart.title = "حساسية NPV لمعدل الخصم"
    chart.y_axis.title = "NPV (ريال)"
    chart.x_axis.title = "معدل الخصم %"
    chart.style = 10
    chart.width = 18
    chart.height = 10

    n = len(dr_sens)
    data_ref = Reference(ws_data, min_col=2, min_row=1, max_row=n + 1)
    cats_ref = Reference(ws_data, min_col=1, min_row=2, max_row=n + 1)
    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats_ref)
    ws_chart.add_chart(chart, "A1")


# ─── Main builder ──────────────────────────────────────────────────────────────

def build_hbu_excel(
    case_data:    Dict[str, Any],
    hbu_result:   Dict[str, Any],
    fd:           Dict[str, Any],
    sourcing:     Dict[str, Any],
    alternatives: List[Dict[str, Any]],
    out_path:     str,
) -> str:
    """
    Build admin-only Excel with 15+ sheets + 2 charts.
    Returns path to the written .xlsx file.
    """
    if not _HAS_OPENPYXL:
        raise ImportError("openpyxl is required for Excel generation")

    wb = openpyxl.Workbook()
    # Remove default sheet
    if "Sheet" in wb.sheetnames:
        del wb["Sheet"]

    currency = case_data.get("currency", "ريال")
    prov     = sourcing.get("provenance_table", [])

    # Build all sheets
    _sheet_summary(wb, case_data, hbu_result, fd)
    _sheet_provenance(wb, prov)
    _sheet_site(wb, case_data, sourcing)
    _sheet_market(wb, case_data, sourcing)
    _sheet_concepts(wb, alternatives, hbu_result)
    _sheet_four_tests(wb, hbu_result)
    _sheet_max_productive(wb, hbu_result)
    _sheet_financial_depth(wb, fd, currency)
    _sheet_sensitivity(wb, fd, currency)
    _sheet_comparison(wb, hbu_result)
    _sheet_cashflows(wb, hbu_result)
    _sheet_risks(wb, case_data)
    _sheet_governance(wb, case_data)
    _sheet_source_log(wb, sourcing)
    # Charts (adds 4 more sheets: 2 hidden data + 2 visible chart)
    _add_npv_chart(wb, hbu_result)
    _add_sensitivity_chart(wb, fd)

    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    return out_path
