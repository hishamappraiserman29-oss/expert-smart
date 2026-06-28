# -*- coding: utf-8 -*-
"""
tax_appeal_workbook_builder.py — Expert Tax Appeal Excel Workbook Builder.

Public API:
    _create_tax_appeal_workbook(request_id, request_record) -> Path
    _validate_tax_workbook_formulas_and_no_silent_blanks(workbook_path) -> list[str]

Output path:
    core_engine/instance/tax_appeal_workbooks/<REQ-ID>/tax_appeal_review_<REQ-ID>.xlsx

Sheets (14 total, "مدخلات الطعن" MUST be first):
    1.  مدخلات الطعن
    2.  Dashboard
    3.  بيانات العقار
    4.  بيانات الإخطار الضريبي
    5.  حساب الضريبة العقارية
    6.  حساب ضريبة التصرفات
    7.  تحليل المغالاة الحكومية
    8.  المقارنات السوقية والإيجارية
    9.  مهلة الطعن 60 يومًا
    10. المستندات المطلوبة
    11. مصادر البيانات
    12. سجل المراجعة
    13. صياغة مذكرة الطعن
    14. جاهزية Qdrant-RAG المستقبلية

Rules:
    - No FPDF.
    - Do not expose internal paths to ordinary users.
    - Transfer tax rate = 2.5% (fixed).
    - Annual and transfer tax logic must be clearly separated in the workbook.
    - No silent blanks: use gap markers where data is missing.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

# ── Storage ───────────────────────────────────────────────────────────────────

_WB_DIR = Path(__file__).parent / "instance" / "tax_appeal_workbooks"
_WB_DIR.mkdir(parents=True, exist_ok=True)

# ── Gap markers ───────────────────────────────────────────────────────────────

_GAP      = "غير متاح ضمن بيانات الطلب"
_EXPERT   = "يحتاج استكمال بواسطة الخبير"
_NA       = "غير مطبق لهذا النوع من الضريبة"
_QDRANT   = "مرحلة مستقبلية — غير مفعل"

# ── Number / date formats ─────────────────────────────────────────────────────
_FMT_CURRENCY = '#,##0.00" ج.م."'
_FMT_INT      = '#,##0'
_FMT_PCT      = '0.0%'
_FMT_DATE     = 'DD/MM/YYYY'

# ── Extra fill helpers ────────────────────────────────────────────────────────

def _input_fill():
    """Light yellow — marks user-editable input cells."""
    from openpyxl.styles import PatternFill
    return PatternFill("solid", fgColor="FFFDE7")


def _formula_fill():
    """Light blue — marks formula / calculated cells."""
    from openpyxl.styles import PatternFill
    return PatternFill("solid", fgColor="E3F2FD")


def _alt_fill():
    """Very light gray — alternating even rows."""
    from openpyxl.styles import PatternFill
    return PatternFill("solid", fgColor="F1F4F8")


def _warn_fill():
    """Light red — missing data / warning cells."""
    from openpyxl.styles import PatternFill
    return PatternFill("solid", fgColor="FEE2E2")

_REQUIRED_SHEETS = [
    "مدخلات الطعن",
    "Dashboard",
    "بيانات العقار",
    "بيانات الإخطار الضريبي",
    "حساب الضريبة العقارية",
    "حساب ضريبة التصرفات",
    "تحليل المغالاة الحكومية",
    "المقارنات السوقية والإيجارية",
    "مهلة الطعن 60 يومًا",
    "المستندات المطلوبة",
    "مصادر البيانات",
    "سجل المراجعة",
    "صياغة مذكرة الطعن",
    "جاهزية Qdrant-RAG المستقبلية",
    # ── Five canonical method sheets ──────────────────────────
    "طريقة التكلفة",
    "طريقة المقارنة",
    "طريقة الرسملة",
    "طريقة المقارنة الضريبية",
    "طريقة الانحدار المتعدد",
    "توفيق الطرق الخمس",
    # ── Professional governance sheets ────────────────────────
    "تحليل HBU",
    "المعايير المهنية",
    "حوكمة البيانات",
    # ── Reference intelligence sheets ─────────────────────────
    "قاعدة المراجع",
    "نموذج الإهلاك",
    "حساسية الضريبة",
    "مخاطر الطعن",
    "تقارير سابقة مرتبطة",
    "إصدارات المراجع",
    # ── Compliance, disclosure, methodology & specialized sheets ─────────────
    "نطاق العمل",
    "بيان الامتثال",
    "DCF إن وجد",
    "مراجعة الجودة",
    "توقيع واعتماد الخبير",
    "ESG والمخاطر المناخية",
    "الفحص القانوني والمستندي",
    "مراجعة النظراء",
    "مصفوفة المستندات",
    "أساس الضريبة والقيمة السوقية",
    "الأصول المتخصصة",
    "الأصول تحت الأرض",
    "حوكمة USPAP",
    "التأصيل المرجعي",
    "الحجة الضريبية المقارنة",
    "خصومات وصيانة وشغور",
    "مصفوفة التوفيق",
    "اختبار المثل الضريبي",
    "فصل الأصول العقارية والتشغيلية",
    "ملخص الحجة أمام اللجنة",
    "جودة نص التقرير",
]


# ── Style helpers ─────────────────────────────────────────────────────────────

def _style_imports():
    from openpyxl.styles import (
        Alignment, Border, Font, PatternFill, Side,
    )
    return Alignment, Border, Font, PatternFill, Side


def _hdr_fill(color: str = "1F4E78"):
    from openpyxl.styles import PatternFill
    return PatternFill("solid", fgColor=color)


def _hdr_font(bold: bool = True, color: str = "FFFFFF", size: int = 10):
    from openpyxl.styles import Font
    return Font(name="Cairo", bold=bold, color=color, size=size)


def _data_font(bold: bool = False, color: str = "1A1A2E", size: int = 9):
    from openpyxl.styles import Font
    return Font(name="Cairo", bold=bold, color=color, size=size)


def _center_align(wrap: bool = True):
    from openpyxl.styles import Alignment
    return Alignment(horizontal="center", vertical="center", wrap_text=wrap)


def _right_align(wrap: bool = True):
    from openpyxl.styles import Alignment
    return Alignment(horizontal="right", vertical="center", wrap_text=wrap)


def _left_align():
    from openpyxl.styles import Alignment
    return Alignment(horizontal="left", vertical="center")


def _thin_border():
    from openpyxl.styles import Border, Side
    thin = Side(style="thin", color="CCCCCC")
    return Border(left=thin, right=thin, top=thin, bottom=thin)


def _apply_row(
    ws, row_num: int, label: str, value: Any,
    lbl_color: str = "1B2E4B",
    is_input: bool = False,
    is_formula: bool = False,
    number_format: str = "",
) -> None:
    """Write a label/value pair: col-1 label (light-gray bg), col-2 value.

    is_input=True  → light-yellow background (editable field)
    is_formula=True → light-blue background (calculated field)
    Odd/even alternating background applied when neither flag is set.
    """
    from openpyxl.styles import Font, PatternFill
    effective_value = value if value not in (None, "") else _GAP

    # Label cell — always light steel-blue-gray
    lbl_cell = ws.cell(row=row_num, column=1, value=label)
    lbl_cell.font      = Font(name="Cairo", bold=True, size=9, color=lbl_color)
    lbl_cell.fill      = PatternFill("solid", fgColor="EFF2F7")
    lbl_cell.alignment = _right_align(wrap=False)
    lbl_cell.border    = _thin_border()

    # Value cell
    val_cell = ws.cell(row=row_num, column=2, value=effective_value)
    val_cell.font      = _data_font()
    val_cell.alignment = _right_align()
    val_cell.border    = _thin_border()
    if is_formula:
        val_cell.fill = _formula_fill()
    elif is_input:
        val_cell.fill = _input_fill()
    elif row_num % 2 == 0:
        val_cell.fill = _alt_fill()
    else:
        val_cell.fill = PatternFill("solid", fgColor="FFFFFF")
    if number_format:
        val_cell.number_format = number_format


def _write_section_header(ws, row: int, text: str, ncols: int = 4, color: str = "1F4E78") -> None:
    """Merge + style a section header row."""
    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=ncols)
    cell = ws.cell(row=row, column=1, value=text)
    cell.fill      = PatternFill("solid", fgColor=color)
    cell.font      = Font(name="Cairo", bold=True, size=10, color="FFFFFF")
    cell.alignment = Alignment(horizontal="right", vertical="center")


def _g(d: dict, *keys, default=None):
    """Get first truthy value from multiple keys."""
    for k in keys:
        v = d.get(k)
        if v not in (None, "", _GAP, _NA, _EXPERT):
            return v
    return default or _GAP


# ── Sheet builders ────────────────────────────────────────────────────────────

def _sheet_inputs(ws, ctx: dict, tax_mode: str) -> None:
    """Sheet 1: مدخلات الطعن — main input dashboard with formulas."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 37
    ws.column_dimensions["B"].width = 32
    ws.column_dimensions["C"].width = 20
    ws.column_dimensions["D"].width = 25

    from openpyxl.styles import Font, PatternFill, Alignment
    # Title
    ws.merge_cells("A1:D1")
    c = ws["A1"]
    c.value     = "مدخلات الطعن الضريبي — Tax Appeal Inputs"
    c.fill      = PatternFill("solid", fgColor="1F4E78")
    c.font      = Font(name="Cairo", bold=True, size=13, color="FFD700")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    row = 3
    _write_section_header(ws, row, "بيانات المكلف والطلب", ncols=4, color="2D5A27")
    row += 1
    _apply_row(ws, row, "رقم الطلب", ctx.get("request_id")); row += 1
    _apply_row(ws, row, "اسم المكلف", ctx.get("taxpayer_name")); row += 1
    _apply_row(ws, row, "رقم الهاتف", ctx.get("taxpayer_phone")); row += 1
    _apply_row(ws, row, "البريد الإلكتروني", ctx.get("taxpayer_email") or _GAP); row += 1
    _apply_row(ws, row, "تاريخ التقرير", ctx.get("report_date")); row += 1

    row += 1
    _write_section_header(ws, row, "بيانات العقار والموقع", ncols=4, color="2D5A27")
    row += 1
    _apply_row(ws, row, "نوع العقار", ctx.get("property_type")); row += 1
    _apply_row(ws, row, "المحافظة", ctx.get("governorate")); row += 1
    _apply_row(ws, row, "المدينة", ctx.get("city")); row += 1
    _apply_row(ws, row, "الحي / المنطقة", ctx.get("district")); row += 1
    _apply_row(ws, row, "كود المنطقة", ctx.get("zone_id")); row += 1
    _apply_row(ws, row, "المساحة (م²)", ctx.get("area")); row += 1
    _apply_row(ws, row, "نوع الملكية", ctx.get("ownership_type")); row += 1

    row += 1
    _write_section_header(ws, row, "نوع الضريبة", ncols=4, color="7B2D00")
    row += 1
    _apply_row(ws, row, "وضع الضريبة", ctx.get("tax_mode_label_ar")); row += 1
    _apply_row(ws, row, "تاريخ الأساس الضريبي", ctx.get("assessment_date")); row += 1
    _apply_row(ws, row, "آخر تاريخ حصر الضريبة / تاريخ أساس التقييم الضريبي",
               ctx.get("tax_assessment_basis_date")); row += 1
    _apply_row(ws, row, "ملاحظة أساس التقييم",
               ctx.get("tax_assessment_basis_date_note")); row += 1
    _apply_row(ws, row, "ملاحظة التاريخ", ctx.get("date_basis_note")); row += 1

    row += 1
    _write_section_header(ws, row, "بيانات الإخطار والمهلة", ncols=4, color="7B2D00")
    row += 1
    notice_row = row
    _apply_row(ws, row, "تاريخ استلام الإخطار (YYYY-MM-DD)", ctx.get("notice_received_date_iso") or _GAP); row += 1
    deadline_row = row
    ws.cell(row=row, column=1, value="تاريخ انتهاء مهلة الطعن (60 يومًا)")
    ws.cell(row=row, column=1).font = _hdr_font(color="1F4E78", size=9)
    ws.cell(row=row, column=1).alignment = _right_align(wrap=False)
    ws.cell(row=row, column=1).border = _thin_border()
    # Formula: deadline = notice + 60
    deadline_formula_cell = ws.cell(row=row, column=2)
    deadline_formula_cell.value = f"=IF(B{notice_row}<>\"{_GAP}\",B{notice_row}+60,\"{_GAP}\")"
    deadline_formula_cell.font  = _data_font()
    deadline_formula_cell.border = _thin_border()
    row += 1
    days_row = row
    ws.cell(row=row, column=1, value="الأيام المتبقية حتى انتهاء المهلة")
    ws.cell(row=row, column=1).font = _hdr_font(color="1F4E78", size=9)
    ws.cell(row=row, column=1).alignment = _right_align(wrap=False)
    ws.cell(row=row, column=1).border = _thin_border()
    # Formula: days remaining = deadline - TODAY()
    ws.cell(row=row, column=2).value  = f"=IF(B{notice_row}<>\"{_GAP}\",B{deadline_row}-TODAY(),\"{_GAP}\")"
    ws.cell(row=row, column=2).font   = _data_font()
    ws.cell(row=row, column=2).border = _thin_border()
    row += 1
    _apply_row(ws, row, "حالة المهلة", ctx.get("deadline_status")); row += 1

    row += 1
    _write_section_header(ws, row, "البيانات المالية — ضريبة التصرفات العقارية", ncols=4, color="5C1A1A")
    row += 1
    sale_val_row = row
    _apply_row(ws, row, "قيمة التصرف المُعلنة (حكومي)", _g(ctx, "government_assessed_sale_value")); row += 1
    challenged_val_row = row
    _apply_row(ws, row, "قيمة التصرف المطعون فيها (خبير)", _g(ctx, "challenged_sale_value")); row += 1
    # Transfer tax formula cell (2.5%)
    ws.cell(row=row, column=1, value="ضريبة التصرفات الحكومية (= قيمة التصرف × 2.5%)")
    ws.cell(row=row, column=1).font = _hdr_font(color="1F4E78", size=9)
    ws.cell(row=row, column=1).alignment = _right_align(wrap=False)
    ws.cell(row=row, column=1).border = _thin_border()
    govt_transfer_tax_row = row
    ws.cell(row=row, column=2).value  = f"=IF(ISNUMBER(B{sale_val_row}),B{sale_val_row}*0.025,\"{_NA}\")"
    ws.cell(row=row, column=2).font   = _data_font()
    ws.cell(row=row, column=2).border = _thin_border()
    row += 1
    ws.cell(row=row, column=1, value="ضريبة التصرفات المصححة (= قيمة الخبير × 2.5%)")
    ws.cell(row=row, column=1).font = _hdr_font(color="1F4E78", size=9)
    ws.cell(row=row, column=1).alignment = _right_align(wrap=False)
    ws.cell(row=row, column=1).border = _thin_border()
    corrected_transfer_row = row
    ws.cell(row=row, column=2).value  = f"=IF(ISNUMBER(B{challenged_val_row}),B{challenged_val_row}*0.025,\"{_NA}\")"
    ws.cell(row=row, column=2).font   = _data_font()
    ws.cell(row=row, column=2).border = _thin_border()
    row += 1
    _apply_row(ws, row, "تاريخ التصرف (البيع)", ctx.get("sale_date") if ctx.get("tax_mode") == "transfer_tax" else _NA)
    row += 1
    from openpyxl.styles import Font
    ws.cell(row=row, column=1, value="⚠ تنبيه")
    ws.cell(row=row, column=1).font = Font(name="Cairo", bold=True, size=9, color="B43200")
    ws.cell(row=row, column=1).alignment = _right_align(wrap=False)
    ws.cell(row=row, column=2, value="حدود وإعفاءات الضريبة العقارية السنوية لا تطبق على ضريبة التصرفات العقارية.")
    ws.cell(row=row, column=2).font = Font(name="Cairo", italic=True, size=9, color="B43200")
    ws.cell(row=row, column=2).alignment = _right_align()
    row += 1

    row += 1
    _write_section_header(ws, row, "البيانات المالية — الضريبة العقارية السنوية", ncols=4, color="1A4D2E")
    row += 1
    _apply_row(ws, row, "الضريبة الحكومية السنوية", _g(ctx, "government_tax_amount")); row += 1
    rental_val_row = row
    _apply_row(ws, row, "تقدير القيمة الإيجارية السوقية", _g(ctx, "estimated_market_rental_value")); row += 1
    maint_row = row
    _apply_row(ws, row, "نسبة خصم الصيانة", ctx.get("maintenance_deduction_rate") if ctx.get("tax_mode") == "annual_real_estate_tax" else _NA); row += 1
    exempt_row = row
    _apply_row(ws, row, "الإعفاء السنوي", ctx.get("exemption_amount") if ctx.get("tax_mode") == "annual_real_estate_tax" else _NA); row += 1
    ws.cell(row=row, column=1, value="الضريبة الاسترشادية المصححة (=(إيجار×(1-صيانة)-إعفاء)×10%)")
    ws.cell(row=row, column=1).font = _hdr_font(color="1A4D2E", size=9)
    ws.cell(row=row, column=1).alignment = _right_align(wrap=True)
    ws.cell(row=row, column=1).border = _thin_border()
    corrected_annual_row = row
    ws.cell(row=row, column=2).value = (
        f"=IF(AND(ISNUMBER(B{rental_val_row}),ISNUMBER(B{maint_row})),"
        f"MAX(0,(B{rental_val_row}*(1-B{maint_row})-IF(ISNUMBER(B{exempt_row}),B{exempt_row},0)))*0.1,"
        f"\"{_EXPERT}\")"
    )
    ws.cell(row=row, column=2).font   = _data_font()
    ws.cell(row=row, column=2).border = _thin_border()
    row += 1
    _apply_row(ws, row, "دورة الفحص / سنة التقييم", _g(ctx, "inspection_cycle_year")); row += 1
    _apply_row(ws, row, "دورة التقييم التالية المتوقعة", _g(ctx, "next_reassessment_year")); row += 1

    row += 1
    _write_section_header(ws, row, "تحليل المغالاة والوفر", ncols=4, color="7B2D00")
    row += 1
    govt_tax_row = row
    ws.cell(row=row, column=1, value="الضريبة الحكومية الإجمالية")
    ws.cell(row=row, column=1).font = _hdr_font(color="7B2D00", size=9)
    ws.cell(row=row, column=1).alignment = _right_align(wrap=False)
    ws.cell(row=row, column=1).border = _thin_border()
    ws.cell(row=row, column=2).value = (
        _g(ctx, "government_tax_amount", "transfer_tax_government")
    )
    ws.cell(row=row, column=2).font   = _data_font()
    ws.cell(row=row, column=2).border = _thin_border()
    row += 1
    corrected_row = row
    ws.cell(row=row, column=1, value="الضريبة المصححة (خبير)")
    ws.cell(row=row, column=1).font = _hdr_font(color="2D5A27", size=9)
    ws.cell(row=row, column=1).alignment = _right_align(wrap=False)
    ws.cell(row=row, column=1).border = _thin_border()
    ws.cell(row=row, column=2).value = _g(ctx, "corrected_tax_amount")
    ws.cell(row=row, column=2).font   = _data_font()
    ws.cell(row=row, column=2).border = _thin_border()
    row += 1
    overcharge_row = row
    ws.cell(row=row, column=1, value="المغالاة = ضريبة حكومية − ضريبة مصححة")
    ws.cell(row=row, column=1).font = _hdr_font(color="7B2D00", size=9)
    ws.cell(row=row, column=1).alignment = _right_align(wrap=False)
    ws.cell(row=row, column=1).border = _thin_border()
    ws.cell(row=row, column=2).value  = f"=IF(AND(ISNUMBER(B{govt_tax_row}),ISNUMBER(B{corrected_row})),B{govt_tax_row}-B{corrected_row},\"{_EXPERT}\")"
    ws.cell(row=row, column=2).font   = _data_font()
    ws.cell(row=row, column=2).border = _thin_border()
    row += 1
    savings_pct_row = row
    ws.cell(row=row, column=1, value="نسبة الوفر = مغالاة / ضريبة حكومية")
    ws.cell(row=row, column=1).font = _hdr_font(color="7B2D00", size=9)
    ws.cell(row=row, column=1).alignment = _right_align(wrap=False)
    ws.cell(row=row, column=1).border = _thin_border()
    ws.cell(row=row, column=2).value  = f"=IF(AND(ISNUMBER(B{overcharge_row}),ISNUMBER(B{govt_tax_row}),B{govt_tax_row}>0),B{overcharge_row}/B{govt_tax_row},\"{_EXPERT}\")"
    ws.cell(row=row, column=2).font   = _data_font()
    ws.cell(row=row, column=2).border = _thin_border()
    row += 1

    row += 1
    _write_section_header(ws, row, "المستندات والبيانات الناقصة", ncols=4, color="3D3D3D")
    row += 1
    missing = ctx.get("missing_documents") or []
    if missing:
        for doc in missing:
            _apply_row(ws, row, "مطلوب", doc); row += 1
    else:
        _apply_row(ws, row, "جودة البيانات", "مكتملة"); row += 1

    row += 1
    _write_section_header(ws, row, "ملاحظات الخبير", ncols=4, color="3D3D3D")
    row += 1
    ws.cell(row=row, column=1, value="ملاحظات الخبير")
    ws.cell(row=row, column=1).font = _hdr_font(color="3D3D3D", size=9)
    ws.cell(row=row, column=2, value=_EXPERT)
    ws.row_dimensions[row].height = 40
    row += 1


def _sheet_dashboard(ws, ctx: dict) -> None:
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 26
    ws.column_dimensions["C"].width = 20
    ws.column_dimensions["D"].width = 26

    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    thin_side = Side(style="thin", color="D1D5DB")
    card_border = Border(
        left=thin_side, right=thin_side,
        top=thin_side, bottom=thin_side,
    )

    def _kpi_card(row, col, label, value, hdr_color="1B2E4B", val_color="1B2E4B"):
        """Render a 3-row KPI card: header + value + spacer, spanning 2 columns."""
        end_col = col + 1
        # Header row
        ws.merge_cells(start_row=row, start_column=col, end_row=row, end_column=end_col)
        hdr = ws.cell(row=row, column=col, value=label)
        hdr.font      = Font(name="Cairo", bold=True, size=8.5, color="FFFFFF")
        hdr.fill      = PatternFill("solid", fgColor=hdr_color)
        hdr.alignment = Alignment(horizontal="center", vertical="center")
        hdr.border    = card_border
        ws.row_dimensions[row].height = 18

        # Value row
        ws.merge_cells(start_row=row+1, start_column=col, end_row=row+1, end_column=end_col)
        val = ws.cell(row=row+1, column=col, value=value if value not in (None, "", _GAP) else "—")
        val.font      = Font(name="Cairo", bold=True, size=12, color=val_color)
        val.fill      = PatternFill("solid", fgColor="F8F9FA")
        val.alignment = Alignment(horizontal="center", vertical="center")
        val.border    = card_border
        ws.row_dimensions[row+1].height = 26

    # ── Title ──────────────────────────────────────────────────────────────────
    ws.merge_cells("A1:D1")
    title = ws["A1"]
    title.value     = "Dashboard — لوحة المؤشرات الرئيسية — الهادي للتقييم العقاري"
    title.fill      = PatternFill("solid", fgColor="1B2E4B")
    title.font      = Font(name="Cairo", bold=True, size=13, color="C9973A")
    title.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 32

    # Blank separator
    ws.merge_cells("A2:D2")
    ws.row_dimensions[2].height = 6

    # ── KPI Row 1 ──────────────────────────────────────────────────────────────
    _kpi_card(3, 1, "نوع الضريبة", ctx.get("tax_mode_label_ar"), "1B2E4B")
    _kpi_card(3, 3, "حالة المهلة", ctx.get("deadline_status"),
              "7F1D1D" if ctx.get("deadline_status_key") in ("urgent", "expired") else "1A5E30",
              "7F1D1D" if ctx.get("deadline_status_key") in ("urgent", "expired") else "1A5E30")

    # Spacer row
    ws.row_dimensions[5].height = 5

    # ── KPI Row 2 ──────────────────────────────────────────────────────────────
    _kpi_card(6, 1, "الضريبة الحكومية", ctx.get("government_tax_amount"), "7F1D1D", "7F1D1D")
    _kpi_card(6, 3, "التقدير الاسترشادي", ctx.get("corrected_tax_amount"), "1A5E30", "1A5E30")

    # Spacer row
    ws.row_dimensions[8].height = 5

    # ── KPI Row 3 ──────────────────────────────────────────────────────────────
    _kpi_card(9, 1, "الوفر المتوقع",
              ctx.get("expected_savings"),
              "1A5E30" if ctx.get("overcharge_detected") else "374151",
              "1A5E30")
    _kpi_card(9, 3, "نسبة المغالاة",
              f"{ctx.get('overcharge_percentage', 0)}%",
              "7F1D1D" if ctx.get("overcharge_detected") else "374151",
              "7F1D1D" if ctx.get("overcharge_detected") else "374151")

    # Spacer
    ws.row_dimensions[11].height = 5

    # ── Detail rows ────────────────────────────────────────────────────────────
    ws.merge_cells("A12:D12")
    sep = ws["A12"]
    sep.fill = PatternFill("solid", fgColor="1B2E4B")
    sep.value = "تفاصيل الطلب"
    sep.font  = Font(name="Cairo", bold=True, size=9, color="C9973A")
    sep.alignment = Alignment(horizontal="right", vertical="center")
    ws.row_dimensions[12].height = 20

    detail_rows = [
        ("رقم الطلب",              ctx.get("request_id")),
        ("اسم المكلف",             ctx.get("taxpayer_name")),
        ("حالة البيانات",           ctx.get("data_quality_status")),
        ("الأيام المتبقية",         ctx.get("days_remaining")),
        ("آخر تاريخ حصر الضريبة / تاريخ أساس التقييم الضريبي",
         ctx.get("tax_assessment_basis_date")),
        ("رصد مغالاة",              "نعم" if ctx.get("overcharge_detected") else "لا"),
        ("التوصية",                  ctx.get("recommended_action")),
        ("حالة Qdrant / RAG",       "غير مفعل — مرحلة مستقبلية"),
        ("الإجراء المطلوب من الخبير", _EXPERT),
    ]
    for i, (lbl, val) in enumerate(detail_rows, start=13):
        _apply_row(ws, i, lbl, val or _GAP)


def _sheet_property(ws, ctx: dict) -> None:
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 32
    rows = [
        ("نوع العقار", ctx.get("property_type")),
        ("الدولة",     ctx.get("country")),
        ("المحافظة",   ctx.get("governorate")),
        ("المدينة",    ctx.get("city")),
        ("الحي",       ctx.get("district")),
        ("كود المنطقة", ctx.get("zone_id")),
        ("المساحة م²", ctx.get("area")),
        ("نوع الملكية", ctx.get("ownership_type")),
        ("عنوان العقار", ctx.get("property_address")),
    ]
    _write_section_header(ws, 1, "بيانات العقار", ncols=2, color="2D5A27")
    for i, (lbl, val) in enumerate(rows, start=2):
        _apply_row(ws, i, lbl, val or _GAP)


def _sheet_notice(ws, ctx: dict) -> None:
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 35
    ws.column_dimensions["B"].width = 32
    rows = [
        ("تاريخ الإخطار",          ctx.get("notice_received_date")),
        ("المهلة القانونية (يوم)",   60),
        ("تاريخ انتهاء المهلة",     ctx.get("deadline_date")),
        ("الأيام المتبقية",         ctx.get("days_remaining")),
        ("حالة المهلة",             ctx.get("deadline_status")),
        ("المطالبة الحكومية",       ctx.get("government_claimed_value")),
        ("الضريبة الحكومية",        ctx.get("government_tax_amount")),
        ("تاريخ الأساس الضريبي",   ctx.get("assessment_date")),
        ("آخر تاريخ حصر الضريبة / تاريخ أساس التقييم الضريبي",
         ctx.get("tax_assessment_basis_date")),
        ("ملاحظة أساس التقييم",    ctx.get("tax_assessment_basis_date_note")),
        ("ملاحظة التاريخ",          ctx.get("date_basis_note")),
    ]
    _write_section_header(ws, 1, "بيانات الإخطار الضريبي", ncols=2, color="7B2D00")
    for i, (lbl, val) in enumerate(rows, start=2):
        _apply_row(ws, i, lbl, val or _GAP)


def _sheet_annual_tax(ws, ctx: dict) -> None:
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 30
    _write_section_header(ws, 1, "حساب الضريبة العقارية السنوية (استرشادي)", ncols=2, color="1A4D2E")
    rows = [
        ("دورة الفحص / التقييم",             ctx.get("inspection_cycle_year")),
        ("دورة التقييم التالية",              ctx.get("next_reassessment_year")),
        ("القيمة الإيجارية الحكومية",         ctx.get("government_assessed_annual_rental_value")),
        ("القيمة الإيجارية السوقية (خبير)",  ctx.get("estimated_market_rental_value")),
        ("نسبة خصم الصيانة",                ctx.get("maintenance_deduction_rate")),
        ("الإعفاء السنوي",                   ctx.get("exemption_amount")),
        ("الوعاء الخاضع للضريبة",           ctx.get("taxable_base")),
        ("معدل الضريبة الاسترشادي",         ctx.get("tax_rate_advisory")),
        ("الضريبة الحكومية السنوية",         ctx.get("government_tax_amount")),
        ("الضريبة المصححة الاسترشادية",     ctx.get("corrected_tax_amount")),
        ("الوفر المتوقع",                    ctx.get("expected_savings")),
        ("المغالاة المرصودة",               "نعم" if ctx.get("overcharge_detected") else "لا"),
        ("الملاحظة",                         ctx.get("calculation_label")),
    ]
    for i, (lbl, val) in enumerate(rows, start=2):
        _apply_row(ws, i, lbl, val or _GAP)
    # Add note about annual vs transfer separation
    r = len(rows) + 3
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=2)
    from openpyxl.styles import Font, Alignment
    c = ws.cell(row=r, column=1, value=ctx.get("annual_thresholds_note", ""))
    c.font      = Font(name="Cairo", italic=True, size=9, color="B43200")
    c.alignment = Alignment(horizontal="right", vertical="center", wrap_text=True)


def _sheet_transfer_tax(ws, ctx: dict) -> None:
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 30
    _write_section_header(ws, 1, "حساب ضريبة التصرفات العقارية (معدل 2.5% ثابت)", ncols=2, color="5C1A1A")
    rows = [
        ("معدل الضريبة",                   "2.5% — ثابت بموجب القانون"),
        ("تاريخ التصرف (البيع)",           ctx.get("sale_date")),
        ("قيمة التصرف المُعلنة (حكومي)",  ctx.get("government_assessed_sale_value")),
        ("قيمة التصرف المطعون فيها",       ctx.get("challenged_sale_value")),
        ("ضريبة التصرفات الحكومية",        ctx.get("transfer_tax_government")),
        ("ضريبة التصرفات المصححة",         ctx.get("transfer_tax_corrected")),
        ("الوفر المتوقع",                  ctx.get("expected_savings")),
        ("الملاحظة",                       ctx.get("date_basis_note")),
        ("ملاحظة حدود السنوية",            ctx.get("annual_thresholds_note")),
        ("تسمية الحساب",                   ctx.get("calculation_label")),
    ]
    for i, (lbl, val) in enumerate(rows, start=2):
        _apply_row(ws, i, lbl, val or _GAP)


def _sheet_overcharge(ws, ctx: dict) -> None:
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 35
    ws.column_dimensions["B"].width = 30
    _write_section_header(ws, 1, "تحليل المغالاة الحكومية", ncols=2, color="7B2D00")
    rows = [
        ("الضريبة الحكومية",            ctx.get("government_tax_amount")),
        ("الضريبة المصححة",             ctx.get("corrected_tax_amount")),
        ("مبلغ المغالاة",               ctx.get("overcharge_amount")),
        ("نسبة المغالاة %",             ctx.get("overcharge_percentage")),
        ("الوفر المتوقع",               ctx.get("expected_savings")),
        ("رصد مغالاة",                  "نعم" if ctx.get("overcharge_detected") else "لا"),
        ("التوصية",                     ctx.get("recommended_action")),
        ("تحليل الفجوة",                ctx.get("tax_gap_analysis")),
        ("تسمية الحساب",                ctx.get("calculation_label")),
    ]
    for i, (lbl, val) in enumerate(rows, start=2):
        _apply_row(ws, i, lbl, val or _GAP)


def _sheet_comparables(ws, ctx: dict) -> None:
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 25
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 22
    ws.column_dimensions["D"].width = 22
    _write_section_header(ws, 1, "المقارنات السوقية والإيجارية", ncols=4, color="1F4E78")
    headers = ["الحي / المنطقة", "نوع العقار", "سعر / م²", "المصدر"]
    for col, h in enumerate(headers, 1):
        c = ws.cell(row=2, column=col, value=h)
        c.font      = _hdr_font(color="1F4E78")
        c.fill      = _hdr_fill("D6E4F0")
        c.alignment = _right_align(wrap=False)
    # Placeholder rows
    for r in range(3, 8):
        for col in range(1, 5):
            c = ws.cell(row=r, column=col, value=_EXPERT)
            c.font      = _data_font()
            c.border    = _thin_border()
            c.alignment = _right_align()


def _sheet_deadline(ws, ctx: dict) -> None:
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 35
    ws.column_dimensions["B"].width = 30
    _write_section_header(ws, 1, "مهلة الطعن 60 يومًا", ncols=2, color="7B2D00")
    rows = [
        ("تاريخ استلام الإخطار",    ctx.get("notice_received_date")),
        ("المهلة القانونية",         "60 يوم"),
        ("تاريخ انتهاء المهلة",     ctx.get("deadline_date")),
        ("الأيام المتبقية",          ctx.get("days_remaining")),
        ("حالة المهلة",              ctx.get("deadline_status")),
        ("آخر تاريخ حصر الضريبة / تاريخ أساس التقييم الضريبي",
         ctx.get("tax_assessment_basis_date")),
        ("⚠ تنبيه — أساس المهلة",
         "المهلة تُحسب من تاريخ استلام الإخطار لا من تاريخ الحصر الضريبي"),
    ]
    for i, (lbl, val) in enumerate(rows, start=2):
        _apply_row(ws, i, lbl, val or _GAP)
    dls = ctx.get("deadline_legal_status", {})
    extra_rows = [
        ("خطر الرفض الشكلي",       "نعم — خطر مرتفع" if dls.get("formal_rejection_risk") else "منخفض"),
        ("الإجراء الموصى به",       dls.get("recommended_next_step") or _GAP),
        ("إجراء عاجل مطلوب",        "نعم" if dls.get("urgent_action_required") else "لا"),
        ("مراجعة قانونية مطلوبة",   "نعم" if dls.get("legal_review_required") else "لا"),
        ("إخلاء المسؤولية",         dls.get("disclaimer") or "إرشاد إجرائي عام — يحتاج مراجعة مختص"),
    ]
    if dls.get("post_deadline_guidance"):
        extra_rows.insert(1, ("توجيه ما بعد المهلة", dls.get("post_deadline_guidance")))
    for i, (lbl, val) in enumerate(extra_rows, start=len(rows)+2):
        _apply_row(ws, i, lbl, val or _GAP)
    from openpyxl.styles import Font, Alignment
    note_row = len(rows) + len(extra_rows) + 2
    ws.cell(row=note_row, column=1).value = "⚠ ملاحظة"
    ws.cell(row=note_row, column=1).font = Font(name="Cairo", bold=True, size=9, color="B43200")
    ws.cell(row=note_row, column=2).value = "يُرجى التحقق من المهلة القانونية الدقيقة مع المختص القانوني."
    ws.cell(row=note_row, column=2).font = Font(name="Cairo", italic=True, size=9, color="B43200")


def _sheet_documents(ws, ctx: dict) -> None:
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 40
    ws.column_dimensions["B"].width = 22
    _write_section_header(ws, 1, "المستندات المطلوبة للطعن", ncols=2, color="3D3D3D")
    from openpyxl.styles import Font, PatternFill, Alignment
    base_docs = [
        "صورة الهوية الوطنية للمالك",
        "إخطار / نموذج 3 ضرائب الحكومي",
        "مستند ملكية العقار",
        "تقرير تقييم معتمد من خبير مرخص",
    ]
    tax_mode = ctx.get("tax_mode", "")
    if "transfer" in tax_mode:
        base_docs.append("عقد البيع / التصرف العقاري")
        base_docs.append("إثبات قيمة الصفقة (فاتورة / إفادة بنكية)")
    else:
        base_docs.append("بيانات القيمة الإيجارية السوقية")
        base_docs.append("كشف تقييم ضريبي سابق (دورة الفحص)")

    # Column header row
    h1 = ws.cell(row=2, column=1, value="المستند المطلوب")
    h1.font = _hdr_font(color="1B2E4B")
    h1.fill = PatternFill("solid", fgColor="D6E4F0")
    h1.alignment = _right_align(wrap=False)
    h1.border = _thin_border()
    h2 = ws.cell(row=2, column=2, value="حالة التوفر")
    h2.font = _hdr_font(color="1B2E4B")
    h2.fill = PatternFill("solid", fgColor="D6E4F0")
    h2.alignment = _right_align(wrap=False)
    h2.border = _thin_border()

    missing_set = set(ctx.get("missing_documents") or [])
    all_docs = base_docs + [d for d in missing_set if d not in base_docs]
    for i, doc in enumerate(all_docs, start=3):
        is_missing = doc in missing_set
        doc_cell = ws.cell(row=i, column=1, value=doc)
        doc_cell.font = _data_font(bold=False, color="7F1D1D" if is_missing else "111827")
        doc_cell.border = _thin_border()
        doc_cell.alignment = _right_align()
        if i % 2 == 0:
            doc_cell.fill = _alt_fill()

        status_cell = ws.cell(row=i, column=2, value="ناقص — مطلوب" if is_missing else _EXPERT)
        status_cell.font = _data_font(color="7F1D1D" if is_missing else "374151")
        status_cell.border = _thin_border()
        status_cell.alignment = _right_align()
        if is_missing:
            status_cell.fill = _warn_fill()
        elif i % 2 == 0:
            status_cell.fill = _alt_fill()


def _sheet_sources(ws, ctx: dict) -> None:
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 28
    ws.column_dimensions["C"].width = 20
    ws.column_dimensions["D"].width = 20
    ws.column_dimensions["E"].width = 22
    _write_section_header(ws, 1, "مصادر البيانات — هيكل المصادر (Qdrant غير مفعل حاليًا)", ncols=5, color="1F4E78")
    headers = ["كود المصدر", "نوع المصدر", "تسمية المصدر", "حالة الاستخدام", "حالة Qdrant"]
    for col, h in enumerate(headers, 1):
        c = ws.cell(row=2, column=col, value=h)
        c.font      = _hdr_font()
        c.fill      = _hdr_fill()
        c.alignment = _right_align(wrap=False)
    for r, src in enumerate(ctx.get("source_registry", []), start=3):
        data = [
            src.get("source_id", _GAP),
            src.get("source_type", _GAP),
            src.get("source_label", _GAP),
            src.get("source_status", _GAP),
            src.get("qdrant_status", _QDRANT),
        ]
        for col, val in enumerate(data, 1):
            c = ws.cell(row=r, column=col, value=val)
            c.font      = _data_font()
            c.alignment = _right_align()
            c.border    = _thin_border()
    # Disclaimer
    disc_row = len(ctx.get("source_registry", [])) + 4
    from openpyxl.styles import Font, Alignment
    ws.merge_cells(start_row=disc_row, start_column=1, end_row=disc_row, end_column=5)
    c = ws.cell(row=disc_row, column=1)
    c.value = ctx.get("source_registry_disclaimer", "")
    c.font  = Font(name="Cairo", italic=True, size=9, color="B43200")
    c.alignment = Alignment(horizontal="right", vertical="center", wrap_text=True)


def _sheet_audit(ws, ctx: dict) -> None:
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 38
    _write_section_header(ws, 1, "سجل المراجعة", ncols=2, color="3D3D3D")
    rows = [
        ("رقم الطلب",          ctx.get("request_id")),
        ("تاريخ الإنشاء",      ctx.get("report_date")),
        ("حالة البيانات",      ctx.get("data_quality_status")),
        ("حالة Qdrant",        "غير مفعل"),
        ("حالة RAG",           "غير مفعل"),
        ("بحث الإنترنت",       "غير مفعل"),
        ("الخبير المراجع",     _EXPERT),
        ("ملاحظات المراجعة",   _EXPERT),
    ]
    for i, (lbl, val) in enumerate(rows, start=2):
        _apply_row(ws, i, lbl, val or _GAP)


def _sheet_memo(ws, ctx: dict) -> None:
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 58
    _write_section_header(ws, 1, "صياغة مذكرة الطعن — مساحة عمل الخبير", ncols=2, color="1B2E4B")

    from openpyxl.styles import Font, PatternFill, Alignment

    # Memo heading rows
    heading_rows = [
        ("إلى:", "السيد المختص / مصلحة الضرائب العقارية"),
        ("الموضوع:", f"اعتراض فني على تقدير ضريبي — {ctx.get('tax_mode_label_ar', '')} — {ctx.get('city', '')}"),
        ("المكلف:", ctx.get("taxpayer_name", "")),
        ("تاريخ التقرير:", ctx.get("report_date", "")),
    ]
    for i, (lbl, val) in enumerate(heading_rows, start=2):
        lbl_cell = ws.cell(row=i, column=1, value=lbl)
        lbl_cell.font = _hdr_font(color="1B2E4B", size=9)
        lbl_cell.fill = PatternFill("solid", fgColor="EFF2F7")
        lbl_cell.alignment = _right_align(wrap=False)
        lbl_cell.border = _thin_border()
        val_cell = ws.cell(row=i, column=2, value=val or _EXPERT)
        val_cell.font = _data_font(bold=False)
        val_cell.alignment = _right_align()
        val_cell.border = _thin_border()
        ws.row_dimensions[i].height = 18

    # Section headers for memo body
    sections = [
        ("أولاً:", "مقدمة — تاريخ الإيداع وجهة التقديم"),
        ("ثانياً:", "بيانات المكلف والعقار والضريبة"),
        ("ثالثاً:", "ملخص الاعتراض الفني"),
        ("رابعاً:", "الحساب البديل المقترح وفارق الضريبة"),
        ("خامساً:", "الأدلة والمستندات الداعمة"),
        ("سادساً:", "الطلب الختامي والتوصية"),
        ("سابعاً:", "توقيع الخبير المعتمد وختمه الرسمي"),
    ]
    start_row = len(heading_rows) + 3
    for i, (num, sec) in enumerate(sections):
        row = start_row + i
        num_cell = ws.cell(row=row, column=1, value=num)
        num_cell.font = _hdr_font(color="1B2E4B", size=9)
        num_cell.fill = PatternFill("solid", fgColor="D6E4F0")
        num_cell.alignment = _right_align(wrap=False)
        num_cell.border = _thin_border()
        sec_cell = ws.cell(row=row, column=2, value=sec)
        sec_cell.font = _data_font(bold=True)
        sec_cell.alignment = _right_align()
        sec_cell.border = _thin_border()
        if i % 2 == 0:
            sec_cell.fill = _alt_fill()
        ws.row_dimensions[row].height = 32

    r = start_row + len(sections) + 2
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=2)
    c = ws.cell(row=r, column=1)
    c.value = "تنبيه: مسودة فنية استرشادية — لا تُرفع للجهات الرسمية قبل مراجعة وتوقيع الخبير المعتمد."
    c.font  = Font(name="Cairo", italic=True, size=9, color="7F1D1D")
    c.fill  = PatternFill("solid", fgColor="FEE2E2")


def _sheet_qdrant(ws, ctx: dict) -> None:
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 35
    ws.column_dimensions["B"].width = 32
    _write_section_header(ws, 1, "جاهزية Qdrant-RAG المستقبلية (غير مفعل)", ncols=2, color="1B2E4B")
    qrs = ctx.get("qdrant_readiness_summary", {})
    rows = [
        ("جاهز هيكليًا",             "نعم" if qrs.get("qdrant_ready") else "لا"),
        ("Qdrant مفعل",              "لا" if not qrs.get("qdrant_enabled") else "نعم"),
        ("RAG مفعل",                 "لا" if not qrs.get("rag_enabled") else "نعم"),
        ("استيعاب من الإنترنت",      "لا" if not qrs.get("internet_ingestion_enabled") else "نعم"),
        ("حالة Qdrant",              qrs.get("qdrant_status", _QDRANT)),
        ("الحالة العامة",             qrs.get("status_ar", "")),
    ]
    for i, (lbl, val) in enumerate(rows, start=2):
        _apply_row(ws, i, lbl, val or _GAP)
    from openpyxl.styles import Font
    ws.merge_cells("A9:B9")
    c = ws.cell(row=9, column=1, value=ctx.get("source_registry_disclaimer", ""))
    c.font = Font(name="Cairo", italic=True, size=9, color="B43200")


# ── Class-specific sheet builders ─────────────────────────────────────────────

def _sheet_residential_tax_calc(ws, ctx: dict) -> None:
    """حساب الضريبة العقارية — residential cost/tax calculation sheet."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 30
    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells("A1:B1")
    c = ws["A1"]
    c.value     = "حساب الضريبة العقارية السكنية"
    c.fill      = PatternFill("solid", fgColor="1A4D2E")
    c.font      = Font(name="Cairo", bold=True, size=12, color="FFD700")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    row = 3
    _write_section_header(ws, row, "بيانات طريقة التكلفة", ncols=2, color="2D5A27"); row += 1
    _apply_row(ws, row, "تكلفة الإحلال (ج.م/م²) — مبنى", ctx.get("cost_per_sqm_building")); row += 1
    _apply_row(ws, row, "سعر الأرض (ج.م/م²)", ctx.get("cost_per_sqm_land")); row += 1
    _apply_row(ws, row, "المساحة الإجمالية (م²)", ctx.get("area")); row += 1
    _apply_row(ws, row, "سنة الإتمام", ctx.get("completion_year")); row += 1
    _apply_row(ws, row, "دليل إتمام البناء", ctx.get("construction_date_evidence")); row += 1

    row += 1
    _write_section_header(ws, row, "بيانات طريقة مقارنة البيوع", ncols=2, color="2D5A27"); row += 1
    _apply_row(ws, row, "مقارن بيع 1", ctx.get("sales_comparable_1")); row += 1
    _apply_row(ws, row, "مقارن بيع 2", ctx.get("sales_comparable_2")); row += 1
    _apply_row(ws, row, "مقارن بيع 3", ctx.get("sales_comparable_3")); row += 1

    row += 1
    _write_section_header(ws, row, "بيانات طريقة الرسملة", ncols=2, color="2D5A27"); row += 1
    _apply_row(ws, row, "قيمة إيجارية مقارنة 1", ctx.get("rental_comparable_1")); row += 1
    _apply_row(ws, row, "قيمة إيجارية مقارنة 2", ctx.get("rental_comparable_2")); row += 1
    _apply_row(ws, row, "معدل الرسملة", ctx.get("capitalization_rate")); row += 1


def _sheet_residential_overcharge(ws, ctx: dict) -> None:
    """تحليل المغالاة — residential overcharge analysis."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 30
    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells("A1:B1")
    c = ws["A1"]
    c.value     = "تحليل المغالاة الضريبية — سكني"
    c.fill      = PatternFill("solid", fgColor="7B2D00")
    c.font      = Font(name="Cairo", bold=True, size=12, color="FFFFFF")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    row = 3
    _write_section_header(ws, row, "نتائج تحليل المغالاة", ncols=2, color="7B2D00"); row += 1
    _apply_row(ws, row, "وضع الإشغال", ctx.get("occupancy_status")); row += 1
    _apply_row(ws, row, "حالة الإتمام", ctx.get("completion_status")); row += 1
    _apply_row(ws, row, "الضريبة الحكومية", ctx.get("government_tax_amount")); row += 1
    _apply_row(ws, row, "الضريبة المصححة", ctx.get("corrected_tax_amount")); row += 1
    _apply_row(ws, row, "مبلغ المغالاة", ctx.get("overcharge_amount")); row += 1
    _apply_row(ws, row, "نسبة المغالاة (%)", ctx.get("overcharge_percentage")); row += 1


def _sheet_residential_sales_cmp(ws, ctx: dict) -> None:
    """مقارنة بيوع سكنية — residential sales comparison sheet."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 24
    ws.column_dimensions["C"].width = 20
    ws.column_dimensions["D"].width = 20
    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells("A1:D1")
    c = ws["A1"]
    c.value     = "مقارنة بيوع سكنية"
    c.fill      = PatternFill("solid", fgColor="2D5A27")
    c.font      = Font(name="Cairo", bold=True, size=12, color="FFFFFF")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    # Header row
    for col, hdr in enumerate(["البيان", "مقارن 1", "مقارن 2", "مقارن 3"], start=1):
        hc = ws.cell(row=2, column=col, value=hdr)
        hc.fill      = PatternFill("solid", fgColor="1F4E78")
        hc.font      = Font(name="Cairo", bold=True, size=9, color="FFFFFF")
        hc.alignment = Alignment(horizontal="center", vertical="center")

    rows_data = [
        ("بيانات العقار المقارن", ctx.get("sales_comparable_1"), ctx.get("sales_comparable_2"), ctx.get("sales_comparable_3")),
        ("ملاحظة", _EXPERT, _EXPERT, _EXPERT),
    ]
    for i, (lbl, v1, v2, v3) in enumerate(rows_data, start=3):
        for col, val in enumerate([lbl, v1, v2, v3], start=1):
            cell = ws.cell(row=i, column=col, value=val or _EXPERT)
            cell.font      = _data_font()
            cell.alignment = _right_align()
            cell.border    = _thin_border()


def _sheet_residential_cost(ws, ctx: dict) -> None:
    """طريقة التكلفة السكنية — residential cost approach detail sheet."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 30
    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells("A1:B1")
    c = ws["A1"]
    c.value     = "طريقة التكلفة — العقار السكني"
    c.fill      = PatternFill("solid", fgColor="1A4D2E")
    c.font      = Font(name="Cairo", bold=True, size=12, color="FFFFFF")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    row = 3
    _write_section_header(ws, row, "عناصر التكلفة", ncols=2, color="1A4D2E"); row += 1
    _apply_row(ws, row, "تكلفة الأرض (ج.م/م²)", ctx.get("cost_per_sqm_land")); row += 1
    _apply_row(ws, row, "تكلفة المبنى (ج.م/م²)", ctx.get("cost_per_sqm_building")); row += 1
    _apply_row(ws, row, "المساحة (م²)", ctx.get("area")); row += 1
    _apply_row(ws, row, "القيمة الإجمالية الاسترشادية", _EXPERT, is_formula=True); row += 1
    _apply_row(ws, row, "ملاحظة", "يستلزم استكمال الخبير"); row += 1


def _sheet_residential_completion(ws, ctx: dict) -> None:
    """أدلة الإتمام والإشغال — completion and occupancy evidence sheet."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 30
    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells("A1:B1")
    c = ws["A1"]
    c.value     = "أدلة الإتمام والإشغال"
    c.fill      = PatternFill("solid", fgColor="374151")
    c.font      = Font(name="Cairo", bold=True, size=12, color="FFFFFF")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    row = 3
    _write_section_header(ws, row, "بيانات الإتمام والإشغال", ncols=2, color="374151"); row += 1
    _apply_row(ws, row, "سنة الإتمام الفعلي", ctx.get("completion_year")); row += 1
    _apply_row(ws, row, "دليل الإتمام", ctx.get("construction_date_evidence")); row += 1
    _apply_row(ws, row, "وضع الإشغال", ctx.get("occupancy_status")); row += 1
    _apply_row(ws, row, "حالة الإتمام", ctx.get("completion_status")); row += 1
    _apply_row(ws, row, "الدور / الطابق", ctx.get("floor_level")); row += 1
    _apply_row(ws, row, "عدد الطوابق الكلي", ctx.get("number_of_floors")); row += 1


# ── Non-residential class-specific sheets ─────────────────────────────────────

def _sheet_non_residential_sales_cmp(ws, ctx: dict) -> None:
    """مقارنة غير سكنية — non-residential comparables sheet."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 30
    ws.column_dimensions["C"].width = 28
    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells("A1:C1")
    c = ws["A1"]
    c.value     = "مقارنة بيوع وإيجارات — غير سكني"
    c.fill      = PatternFill("solid", fgColor="2D5A27")
    c.font      = Font(name="Cairo", bold=True, size=12, color="FFFFFF")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    row = 3
    _write_section_header(ws, row, "بيانات المقارنات", ncols=3, color="2D5A27"); row += 1
    _apply_row(ws, row, "نوع النشاط التجاري", ctx.get("commercial_activity")); row += 1
    _apply_row(ws, row, "نوع الدور (أرضي/أول/بدروم)", ctx.get("commercial_floor_type")); row += 1
    _apply_row(ws, row, "معامل تعديل الدور", ctx.get("floor_adjustment_factor")); row += 1
    _apply_row(ws, row, "عرض الواجهة (م)", ctx.get("frontage_width")); row += 1
    _apply_row(ws, row, "مقارن بيع 1", ctx.get("sales_comparable_1")); row += 1
    _apply_row(ws, row, "مقارن بيع 2", ctx.get("sales_comparable_2")); row += 1


def _sheet_non_residential_rental(ws, ctx: dict) -> None:
    """تحليل القيمة الإيجارية — rental value analysis for non-residential."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 30
    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells("A1:B1")
    c = ws["A1"]
    c.value     = "تحليل القيمة الإيجارية — غير سكني"
    c.fill      = PatternFill("solid", fgColor="1F4E78")
    c.font      = Font(name="Cairo", bold=True, size=12, color="FFFFFF")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    row = 3
    _write_section_header(ws, row, "مؤشرات القيمة الإيجارية", ncols=2, color="1F4E78"); row += 1
    _apply_row(ws, row, "مقارن إيجاري 1", ctx.get("rental_comparable_1")); row += 1
    _apply_row(ws, row, "معدل رأسمال الإيجار (%)", ctx.get("rental_yield_pct")); row += 1
    _apply_row(ws, row, "القيمة الإيجارية الاسترشادية", ctx.get("estimated_market_rental_value")); row += 1


def _sheet_non_residential_floor_factors(ws, ctx: dict) -> None:
    """عوامل الدور والواجهة — floor and frontage adjustment factors."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 30
    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells("A1:B1")
    c = ws["A1"]
    c.value     = "عوامل الدور والواجهة — غير سكني"
    c.fill      = PatternFill("solid", fgColor="92400E")
    c.font      = Font(name="Cairo", bold=True, size=12, color="FFFFFF")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    row = 3
    _write_section_header(ws, row, "معاملات التعديل", ncols=2, color="92400E"); row += 1
    _apply_row(ws, row, "نوع الدور", ctx.get("commercial_floor_type")); row += 1
    _apply_row(ws, row, "معامل الدور", ctx.get("floor_adjustment_factor")); row += 1
    _apply_row(ws, row, "عرض الواجهة (م)", ctx.get("frontage_width")); row += 1
    _apply_row(ws, row, "المساحة القابلة للاستخدام (م²)", ctx.get("usable_area", ctx.get("area"))); row += 1
    _apply_row(ws, row, "ملاحظة تأثير الدور", "الأرضي: أعلى قيمة — البدروم والعلوي: تخفيض قياسي"); row += 1


def _sheet_non_residential_cost(ws, ctx: dict) -> None:
    """طريقة التكلفة غير السكنية — non-residential cost approach."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 30
    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells("A1:B1")
    c = ws["A1"]
    c.value     = "طريقة التكلفة — عقار غير سكني"
    c.fill      = PatternFill("solid", fgColor="1A4D2E")
    c.font      = Font(name="Cairo", bold=True, size=12, color="FFFFFF")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    row = 3
    _write_section_header(ws, row, "تكلفة الإحلال", ncols=2, color="1A4D2E"); row += 1
    _apply_row(ws, row, "تكلفة المبنى (ج.م/م²)", ctx.get("cost_per_sqm_building")); row += 1
    _apply_row(ws, row, "سعر الأرض (ج.م/م²)", ctx.get("cost_per_sqm_land")); row += 1
    _apply_row(ws, row, "المساحة (م²)", ctx.get("area")); row += 1
    _apply_row(ws, row, "القيمة الإجمالية الاسترشادية", _EXPERT, is_formula=True); row += 1


# ── Special-purpose class-specific sheets ─────────────────────────────────────

def _sheet_sp_components(ws, ctx: dict) -> None:
    """مكونات المنشأة — industrial/special-purpose facility components."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 16
    ws.column_dimensions["C"].width = 20
    ws.column_dimensions["D"].width = 18
    ws.column_dimensions["E"].width = 20
    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells("A1:E1")
    c = ws["A1"]
    c.value     = "مكونات المنشأة — تفصيلي"
    c.fill      = PatternFill("solid", fgColor="1B2E4B")
    c.font      = Font(name="Cairo", bold=True, size=12, color="FFD700")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    for col, hdr in enumerate(["المكوّن", "المساحة (م²)", "سعر الوحدة (ج.م/م²)", "نسبة الإهلاك", "القيمة الصافية"], start=1):
        hc = ws.cell(row=2, column=col, value=hdr)
        hc.fill      = PatternFill("solid", fgColor="1F4E78")
        hc.font      = Font(name="Cairo", bold=True, size=9, color="FFFFFF")
        hc.alignment = Alignment(horizontal="center", vertical="center")
        hc.border    = _thin_border()

    components = ctx.get("industrial_components") or []
    if components:
        for i, comp in enumerate(components, start=3):
            for col, val in enumerate([
                comp.get("name", _EXPERT),
                comp.get("area", _EXPERT),
                comp.get("unit_cost", _EXPERT),
                comp.get("depreciation", _EXPERT),
                comp.get("net_value", _EXPERT),
            ], start=1):
                cell = ws.cell(row=i, column=col, value=val)
                cell.font      = _data_font()
                cell.alignment = _right_align()
                cell.border    = _thin_border()
    else:
        ws.merge_cells("A3:E3")
        nc = ws.cell(row=3, column=1, value=_EXPERT)
        nc.font      = Font(name="Cairo", italic=True, size=9, color="7F1D1D")
        nc.alignment = Alignment(horizontal="center", vertical="center")

    row = max(4, len(components) + 4)
    _write_section_header(ws, row, "بيانات المنشأة العامة", ncols=5, color="374151"); row += 1
    _apply_row(ws, row, "المنطقة الصناعية", ctx.get("industrial_zone")); row += 1
    _apply_row(ws, row, "سعر الأرض (ج.م/م²)", ctx.get("land_price_per_sqm")); row += 1
    _apply_row(ws, row, "مرجع سعر الأرض", ctx.get("land_price_reference")); row += 1


def _sheet_sp_replacement_cost(ws, ctx: dict) -> None:
    """تكلفة الإحلال — replacement cost computation sheet."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 30
    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells("A1:B1")
    c = ws["A1"]
    c.value     = "تكلفة الإحلال — المنشأة الصناعية"
    c.fill      = PatternFill("solid", fgColor="1A4D2E")
    c.font      = Font(name="Cairo", bold=True, size=12, color="FFFFFF")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    row = 3
    _write_section_header(ws, row, "عناصر تكلفة الإحلال", ncols=2, color="1A4D2E"); row += 1
    _apply_row(ws, row, "سعر وحدة المبنى (ج.م/م²)", ctx.get("building_unit_cost")); row += 1
    _apply_row(ws, row, "المساحة الكلية للمباني (م²)", ctx.get("area")); row += 1
    _apply_row(ws, row, "مرجع التسعير", "جامعة عين شمس — خرسانة: 1200 / حديد: 800 ج.م/م²"); row += 1
    _apply_row(ws, row, "تكلفة الإحلال الإجمالية", _EXPERT, is_formula=True); row += 1


def _sheet_sp_depreciation(ws, ctx: dict) -> None:
    """الإهلاك — depreciation schedule for special-purpose."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 30
    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells("A1:B1")
    c = ws["A1"]
    c.value     = "جدول الإهلاك — المنشأة الصناعية"
    c.fill      = PatternFill("solid", fgColor="7B2D00")
    c.font      = Font(name="Cairo", bold=True, size=12, color="FFFFFF")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    row = 3
    _write_section_header(ws, row, "بيانات الإهلاك", ncols=2, color="7B2D00"); row += 1
    _apply_row(ws, row, "معدل الإهلاك السنوي (%)", ctx.get("depreciation_rate")); row += 1
    _apply_row(ws, row, "عمر المنشأة (سنة)", ctx.get("age_years")); row += 1
    dep_rate = ctx.get("depreciation_rate")
    age = ctx.get("age_years")
    if dep_rate not in (_EXPERT, _NA, _GAP) and age not in (_EXPERT, _NA, _GAP):
        try:
            total_dep = min(float(str(dep_rate)) * int(str(age)), 1.0)
            _apply_row(ws, row, "إجمالي نسبة الإهلاك المتراكم (%)", f"{total_dep:.1%}", is_formula=True)
        except Exception:
            _apply_row(ws, row, "إجمالي نسبة الإهلاك المتراكم (%)", _EXPERT)
    else:
        _apply_row(ws, row, "إجمالي نسبة الإهلاك المتراكم (%)", _EXPERT)
    row += 1
    _apply_row(ws, row, "ملاحظة مرجعية", "معدل 1.4% سنويًا وفق الأسس الأكاديمية المعتمدة"); row += 1


def _sheet_sp_analysis(ws, ctx: dict) -> None:
    """تحليل المنشأة الخاصة — special-purpose facility analysis."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 30
    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells("A1:B1")
    c = ws["A1"]
    c.value     = "تحليل المنشأة ذات الأغراض الخاصة"
    c.fill      = PatternFill("solid", fgColor="1B2E4B")
    c.font      = Font(name="Cairo", bold=True, size=12, color="FFD700")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    row = 3
    _write_section_header(ws, row, "بيانات التحليل الفني", ncols=2, color="1B2E4B"); row += 1
    _apply_row(ws, row, "المنطقة الصناعية", ctx.get("industrial_zone")); row += 1
    _apply_row(ws, row, "مرجع سعر الأرض", ctx.get("land_price_reference")); row += 1
    _apply_row(ws, row, "طرق التقييم المنطبقة", "طريقة التكلفة فقط (صناعي)"); row += 1
    _apply_row(ws, row, "مجال العمل", ctx.get("scope_of_work_ar")); row += 1
    _apply_row(ws, row, "الافتراضات", ctx.get("assumptions_ar")); row += 1


def _sheet_sp_value_summary(ws, ctx: dict) -> None:
    """ملخص القيمة الضريبية — tax value summary for special-purpose."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 30
    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells("A1:B1")
    c = ws["A1"]
    c.value     = "ملخص القيمة الضريبية للمنشأة"
    c.fill      = PatternFill("solid", fgColor="1A5E30")
    c.font      = Font(name="Cairo", bold=True, size=12, color="FFFFFF")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    row = 3
    _write_section_header(ws, row, "ملخص التقييم الضريبي", ncols=2, color="1A5E30"); row += 1
    _apply_row(ws, row, "الضريبة الحكومية المطالب بها", ctx.get("government_tax_amount")); row += 1
    _apply_row(ws, row, "الضريبة الاسترشادية المصححة", ctx.get("corrected_tax_amount")); row += 1
    _apply_row(ws, row, "الفرق (مبلغ المغالاة)", ctx.get("overcharge_amount")); row += 1
    _apply_row(ws, row, "نسبة المغالاة (%)", ctx.get("overcharge_percentage")); row += 1
    _apply_row(ws, row, "الوفر المتوقع", ctx.get("expected_savings")); row += 1
    _apply_row(ws, row, "التوصية الفنية", ctx.get("recommended_action")); row += 1


def _sheet_sp_limitations(ws, ctx: dict) -> None:
    """محددات وافتراضات خاصة — scope / assumptions / limitations sheet."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 30
    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells("A1:B1")
    c = ws["A1"]
    c.value     = "محددات وافتراضات خاصة"
    c.fill      = PatternFill("solid", fgColor="374151")
    c.font      = Font(name="Cairo", bold=True, size=12, color="FFFFFF")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    row = 3
    _write_section_header(ws, row, "النصوص الافتراضية والمحددات", ncols=2, color="374151"); row += 1
    _apply_row(ws, row, "مجال العمل", ctx.get("scope_of_work_ar")); row += 1
    _apply_row(ws, row, "الافتراضات الرئيسية", ctx.get("assumptions_ar")); row += 1
    _apply_row(ws, row, "التعريفات", ctx.get("definitions_ar")); row += 1
    _apply_row(ws, row, "المحددات", ctx.get("limitations_ar")); row += 1

    row += 1
    _write_section_header(ws, row, "تنبيهات خاصة", ncols=2, color="7F1D1D"); row += 1
    for warn in ctx.get("special_warnings", []):
        _apply_row(ws, row, "تنبيه", warn); row += 1


# ── Five-method canonical sheet builders ─────────────────────────────────────

def _sheet_five_cost(ws, ctx: dict) -> None:
    """طريقة التكلفة — canonical cost approach sheet (all archetypes)."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 42
    ws.column_dimensions["B"].width = 32
    ws.column_dimensions["C"].width = 30

    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells("A1:C1")
    c = ws["A1"]
    c.value     = "طريقة التكلفة — Cost Approach"
    c.fill      = PatternFill("solid", fgColor="1A4D2E")
    c.font      = Font(name="Cairo", bold=True, size=12, color="FFD700")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    methods = ctx.get("tax_valuation_methods", [])
    cost_m = next((m for m in methods if m.get("method_key") == "cost_approach"), {})

    row = 3
    _write_section_header(ws, row, "حالة الطريقة", ncols=3, color="1A4D2E"); row += 1
    _apply_row(ws, row, "انطباقية الطريقة",    cost_m.get("method_applicability", _EXPERT)); row += 1
    _apply_row(ws, row, "حالة البيانات",        cost_m.get("data_availability_status", _EXPERT)); row += 1
    _apply_row(ws, row, "ملاحظات الخبير",       cost_m.get("expert_notes", _EXPERT)); row += 1
    _apply_row(ws, row, "الاستكمال المستقبلي", cost_m.get("future_enrichment_status", _EXPERT)); row += 1

    row += 1
    _write_section_header(ws, row, "صفوف الحساب", ncols=3, color="2D5A27"); row += 1

    # Header row
    for col, hdr in enumerate(["البيان", "القيمة", "الصيغة"], start=1):
        hc = ws.cell(row=row, column=col, value=hdr)
        hc.fill      = PatternFill("solid", fgColor="1F4E78")
        hc.font      = Font(name="Cairo", bold=True, size=9, color="FFFFFF")
        hc.alignment = Alignment(horizontal="center", vertical="center")
    row += 1

    for calc in cost_m.get("calculation_rows", []):
        lbl_cell = ws.cell(row=row, column=1, value=calc.get("label", ""))
        lbl_cell.font      = _hdr_font(color="1B2E4B", size=9)
        lbl_cell.fill      = PatternFill("solid", fgColor="EFF2F7")
        lbl_cell.alignment = _right_align(wrap=False)
        lbl_cell.border    = _thin_border()
        val = calc.get("value", _GAP)
        formula = calc.get("formula", "")
        is_formula_cell = isinstance(val, str) and val.startswith("=")
        val_cell = ws.cell(row=row, column=2, value=val if val not in (None, "") else _GAP)
        val_cell.font      = _data_font()
        val_cell.alignment = _right_align()
        val_cell.border    = _thin_border()
        if is_formula_cell:
            val_cell.fill = _formula_fill()
        elif row % 2 == 0:
            val_cell.fill = _alt_fill()
        f_cell = ws.cell(row=row, column=3, value=formula or "")
        f_cell.font      = _data_font(color="6B7280")
        f_cell.alignment = _right_align()
        f_cell.border    = _thin_border()
        row += 1

    # ── Component table for special_purpose / factory ─────────────────────────
    component_table = cost_m.get("component_table", [])
    if component_table:
        row += 1
        _write_section_header(ws, row, "جدول مكوِّنات التكلفة التفصيلية", ncols=3, color="7B2D00"); row += 1
        # Expand columns for detailed component view
        ws.column_dimensions["A"].width = 30
        ws.column_dimensions["B"].width = 18
        ws.column_dimensions["C"].width = 18
        ws.column_dimensions["D"].width = 18
        ws.column_dimensions["E"].width = 18
        ws.column_dimensions["F"].width = 18
        comp_headers = ["المكوِّن", "المساحة (م²)", "تكلفة/م²", "تكلفة إحلال", "إهلاك %", "القيمة الإهلاكية"]
        from openpyxl.styles import Font as _F, PatternFill as _PF, Alignment as _AL
        for ci, hdr in enumerate(comp_headers, start=1):
            hc = ws.cell(row=row, column=ci, value=hdr)
            hc.fill      = _PF("solid", fgColor="7B2D00")
            hc.font      = _F(name="Cairo", bold=True, size=8, color="FFFFFF")
            hc.alignment = _AL(horizontal="center", vertical="center")
        row += 1
        for comp in component_table:
            vals = [
                comp.get("component_name", ""),
                comp.get("area_m2", _GAP),
                comp.get("unit_cost", _GAP),
                comp.get("replacement_cost_new", _GAP),
                comp.get("total_dep_pct", "0%"),
                comp.get("depreciated_value", _GAP),
            ]
            for ci, v in enumerate(vals, start=1):
                c = ws.cell(row=row, column=ci, value=v if v not in (None, "") else _GAP)
                c.font      = _data_font()
                c.alignment = _right_align()
                c.border    = _thin_border()
                if row % 2 == 0:
                    c.fill = _alt_fill()
            row += 1
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
        note_c = ws.cell(row=row, column=1,
                         value="ملاحظة: الآلات والمعدات التشغيلية لا تدخل ضمن التقييم العقاري إلا إذا تم النص صراحة على خلاف ذلك.")
        note_c.font = _F(name="Cairo", italic=True, size=8, color="7F1D1D")
        note_c.alignment = _right_align()
        row += 2

    row += 1
    _write_section_header(ws, row, "الدلالة الإجمالية", ncols=3, color="1A4D2E"); row += 1
    _apply_row(ws, row, "الدلالة (ج.م)", cost_m.get("indicated_value", _EXPERT), is_formula=True); row += 1
    _apply_row(ws, row, "البيانات الناقصة", ", ".join(cost_m.get("required_missing_inputs", [])) or "—"); row += 1

    # ── Formulas used ─────────────────────────────────────────────────────────
    formulas = cost_m.get("formulas_used", [])
    if formulas:
        row += 1
        _write_section_header(ws, row, "الصيغ الحسابية المستخدمة", ncols=3, color="2D5A27"); row += 1
        for f in formulas:
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
            fc = ws.cell(row=row, column=1, value=f)
            fc.font      = _data_font(color="1A4D2E")
            fc.alignment = _right_align()
            row += 1


def _sheet_five_market(ws, ctx: dict) -> None:
    """طريقة المقارنة — canonical market comparison sheet."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 32
    ws.column_dimensions["C"].width = 28

    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells("A1:C1")
    c = ws["A1"]
    c.value     = "طريقة المقارنة السوقية — Market Comparison"
    c.fill      = PatternFill("solid", fgColor="2D5A27")
    c.font      = Font(name="Cairo", bold=True, size=12, color="FFFFFF")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    methods = ctx.get("tax_valuation_methods", [])
    m = next((x for x in methods if x.get("method_key") == "market_comparison_approach"), {})

    row = 3
    _write_section_header(ws, row, "حالة الطريقة", ncols=3, color="2D5A27"); row += 1
    _apply_row(ws, row, "انطباقية الطريقة",    m.get("method_applicability", _EXPERT)); row += 1
    _apply_row(ws, row, "حالة البيانات",        m.get("data_availability_status", _EXPERT)); row += 1
    _apply_row(ws, row, "ملاحظات الخبير",       m.get("expert_notes", _EXPERT)); row += 1
    _apply_row(ws, row, "الاستكمال المستقبلي", m.get("future_enrichment_status", _EXPERT)); row += 1

    row += 1
    _write_section_header(ws, row, "بيانات المقارنات", ncols=3, color="2D5A27"); row += 1

    for col, hdr in enumerate(["البيان", "القيمة", "الصيغة"], start=1):
        hc = ws.cell(row=row, column=col, value=hdr)
        hc.fill      = PatternFill("solid", fgColor="1F4E78")
        hc.font      = Font(name="Cairo", bold=True, size=9, color="FFFFFF")
        hc.alignment = Alignment(horizontal="center", vertical="center")
    row += 1

    for calc in m.get("calculation_rows", []):
        lc = ws.cell(row=row, column=1, value=calc.get("label", ""))
        lc.font = _hdr_font(color="1B2E4B", size=9)
        lc.fill = PatternFill("solid", fgColor="EFF2F7")
        lc.alignment = _right_align(wrap=False)
        lc.border = _thin_border()
        vc = ws.cell(row=row, column=2, value=calc.get("value", _GAP) or _GAP)
        vc.font = _data_font()
        vc.alignment = _right_align()
        vc.border = _thin_border()
        if row % 2 == 0:
            vc.fill = _alt_fill()
        fc = ws.cell(row=row, column=3, value=calc.get("formula", "") or "")
        fc.font = _data_font(color="6B7280")
        fc.alignment = _right_align()
        fc.border = _thin_border()
        row += 1

    # ── Detailed comparison matrix ────────────────────────────────────────────
    comp_matrix = m.get("comparison_matrix", [])
    if comp_matrix:
        row += 1
        _write_section_header(ws, row, "مصفوفة المقارنة التفصيلية", ncols=3, color="1A4D2E"); row += 1
        ws.column_dimensions["A"].width = 30
        ws.column_dimensions["B"].width = 16
        ws.column_dimensions["C"].width = 16
        ws.column_dimensions["D"].width = 16
        ws.column_dimensions["E"].width = 16
        ws.column_dimensions["F"].width = 18
        matrix_headers = ["المقارن", "المساحة (م²)", "السعر (ج.م)", "سعر/م²", "معامل تعديل كلي", "سعر معدَّل/م²"]
        from openpyxl.styles import Font as _F, PatternFill as _PF, Alignment as _AL
        for ci, hdr in enumerate(matrix_headers, start=1):
            hc = ws.cell(row=row, column=ci, value=hdr)
            hc.fill      = _PF("solid", fgColor="1A4D2E")
            hc.font      = _F(name="Cairo", bold=True, size=8, color="FFFFFF")
            hc.alignment = _AL(horizontal="center", vertical="center")
        row += 1
        for comp in comp_matrix:
            vals = [
                str(comp.get("location", ""))[:50] or comp.get("comparable_id", ""),
                comp.get("area", _GAP),
                comp.get("value", _GAP),
                comp.get("price_per_m2", _GAP),
                comp.get("total_adj_factor", "0%"),
                comp.get("adjusted_price_per_m2", _GAP),
            ]
            for ci, v in enumerate(vals, start=1):
                c = ws.cell(row=row, column=ci, value=v if v not in (None, "") else _GAP)
                c.font      = _data_font()
                c.alignment = _right_align()
                c.border    = _thin_border()
                if not comp.get("included", True):
                    c.font = _data_font(color="9CA3AF")
                elif row % 2 == 0:
                    c.fill = _alt_fill()
            row += 1

        # Adjustment detail header
        adj_headers = ["المقارن", "تعديل التاريخ", "تعديل الموقع", "تعديل الدور", "تعديل الحالة", "مُدرج؟"]
        row += 1
        for ci, hdr in enumerate(adj_headers, start=1):
            hc = ws.cell(row=row, column=ci, value=hdr)
            hc.fill      = _PF("solid", fgColor="2D5A27")
            hc.font      = _F(name="Cairo", bold=True, size=8, color="FFFFFF")
            hc.alignment = _AL(horizontal="center", vertical="center")
        row += 1
        for comp in comp_matrix:
            vals = [
                comp.get("comparable_id", ""),
                comp.get("adj_time", "0%"),
                comp.get("adj_location", "0%"),
                comp.get("adj_floor", "0%"),
                comp.get("adj_condition", "0%"),
                "نعم" if comp.get("included") else "لا — " + comp.get("exclusion_reason", ""),
            ]
            for ci, v in enumerate(vals, start=1):
                c = ws.cell(row=row, column=ci, value=v if v not in (None, "") else _GAP)
                c.font      = _data_font()
                c.alignment = _right_align()
                c.border    = _thin_border()
                if row % 2 == 0:
                    c.fill = _alt_fill()
            row += 1

    row += 1
    _write_section_header(ws, row, "الدلالة", ncols=3, color="2D5A27"); row += 1
    _apply_row(ws, row, "دلالة المقارنة (ج.م)", m.get("indicated_value", _EXPERT), is_formula=True); row += 1
    _apply_row(ws, row, "البيانات الناقصة", ", ".join(m.get("required_missing_inputs", [])) or "—"); row += 1
    _apply_row(ws, row, "ملاحظة Qdrant",
               "قاعدة بيانات Qdrant للمقارنات السوقية — غير مفعلة — مرحلة مستقبلية"); row += 1


def _sheet_five_income(ws, ctx: dict) -> None:
    """طريقة الرسملة — canonical income capitalization sheet."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 42
    ws.column_dimensions["B"].width = 30
    ws.column_dimensions["C"].width = 28

    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells("A1:C1")
    c = ws["A1"]
    c.value     = "طريقة الرسملة / الدخل — Income Capitalization"
    c.fill      = PatternFill("solid", fgColor="1F4E78")
    c.font      = Font(name="Cairo", bold=True, size=12, color="FFFFFF")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    methods = ctx.get("tax_valuation_methods", [])
    m = next((x for x in methods if x.get("method_key") == "income_capitalization_approach"), {})

    row = 3
    _write_section_header(ws, row, "حالة الطريقة", ncols=3, color="1F4E78"); row += 1
    _apply_row(ws, row, "انطباقية الطريقة",    m.get("method_applicability", _EXPERT)); row += 1
    _apply_row(ws, row, "حالة البيانات",        m.get("data_availability_status", _EXPERT)); row += 1
    _apply_row(ws, row, "ملاحظات الخبير",       m.get("expert_notes", _EXPERT)); row += 1

    row += 1
    _write_section_header(ws, row, "حساب الدخل", ncols=3, color="1F4E78"); row += 1

    # Income rows with Excel formulas where applicable
    for col, hdr in enumerate(["البيان", "القيمة", "الصيغة"], start=1):
        hc = ws.cell(row=row, column=col, value=hdr)
        hc.fill      = PatternFill("solid", fgColor="1F4E78")
        hc.font      = Font(name="Cairo", bold=True, size=9, color="FFFFFF")
        hc.alignment = Alignment(horizontal="center", vertical="center")
    row += 1

    income_val_row = None
    cap_rate_row = None
    egi_row = None
    for i, calc in enumerate(m.get("calculation_rows", [])):
        lc = ws.cell(row=row, column=1, value=calc.get("label", ""))
        lc.font = _hdr_font(color="1B2E4B", size=9)
        lc.fill = PatternFill("solid", fgColor="EFF2F7")
        lc.alignment = _right_align(wrap=False)
        lc.border = _thin_border()
        val = calc.get("value", _GAP)
        vc = ws.cell(row=row, column=2, value=val if val not in (None, "") else _GAP)
        vc.font = _data_font()
        vc.alignment = _right_align()
        vc.border = _thin_border()
        if row % 2 == 0:
            vc.fill = _alt_fill()
        fc = ws.cell(row=row, column=3, value=calc.get("formula", "") or "")
        fc.font = _data_font(color="6B7280")
        fc.alignment = _right_align()
        fc.border = _thin_border()
        # Track key rows for cross-references
        label = calc.get("label", "")
        if "سنوية" in label and "إجمالية" not in label and "فعلي" not in label:
            income_val_row = row
        if "رسملة" in label and "معدل" in label:
            cap_rate_row = row
        if "فعلي" in label:
            egi_row = row
        row += 1

    # NOI / income_value formula row (Excel-native)
    if income_val_row and cap_rate_row:
        row += 1
        _write_section_header(ws, row, "صيغة الدخل", ncols=3, color="1A4D2E"); row += 1
        ws.cell(row=row, column=1, value="دلالة طريقة الرسملة (ج.م)").font = _hdr_font(color="1A4D2E", size=9)
        ws.cell(row=row, column=1).alignment = _right_align(wrap=False)
        ws.cell(row=row, column=1).border = _thin_border()
        fml = (
            f"=IF(AND(ISNUMBER(B{income_val_row}),ISNUMBER(B{cap_rate_row}),B{cap_rate_row}>0),"
            f"B{income_val_row}*(1-0.05-0.02)*(1-0.15-0.03)/B{cap_rate_row},\"{_EXPERT}\")"
        )
        wc = ws.cell(row=row, column=2, value=fml)
        wc.font = _data_font()
        wc.fill = _formula_fill()
        wc.alignment = _right_align()
        wc.border = _thin_border()
        ws.cell(row=row, column=3, value="= NOI / معدل الرسملة").font = _data_font(color="6B7280")
        row += 1

    row += 1
    _apply_row(ws, row, "البيانات الناقصة", ", ".join(m.get("required_missing_inputs", [])) or "—"); row += 1


def _sheet_five_tax_comparison(ws, ctx: dict) -> None:
    """طريقة المقارنة الضريبية — canonical tax comparison sheet."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 42
    ws.column_dimensions["B"].width = 30
    ws.column_dimensions["C"].width = 26

    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells("A1:C1")
    c = ws["A1"]
    c.value     = "طريقة المقارنة الضريبية — Tax Comparison"
    c.fill      = PatternFill("solid", fgColor="7B2D00")
    c.font      = Font(name="Cairo", bold=True, size=12, color="FFFFFF")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    methods = ctx.get("tax_valuation_methods", [])
    m = next((x for x in methods if x.get("method_key") == "tax_comparison_approach"), {})

    row = 3
    _write_section_header(ws, row, "مقارنة الضريبة الحكومية بالتقدير الاسترشادي", ncols=3, color="7B2D00"); row += 1

    for col, hdr in enumerate(["البيان", "القيمة", "الصيغة / الملاحظة"], start=1):
        hc = ws.cell(row=row, column=col, value=hdr)
        hc.fill      = PatternFill("solid", fgColor="1F4E78")
        hc.font      = Font(name="Cairo", bold=True, size=9, color="FFFFFF")
        hc.alignment = Alignment(horizontal="center", vertical="center")
    row += 1

    # Key rows for formulas
    govt_tax_row = None
    corr_tax_row = None
    area_row = None

    for calc in m.get("calculation_rows", []):
        lc = ws.cell(row=row, column=1, value=calc.get("label", ""))
        lc.font = _hdr_font(color="1B2E4B", size=9)
        lc.fill = PatternFill("solid", fgColor="EFF2F7")
        lc.alignment = _right_align(wrap=False)
        lc.border = _thin_border()
        val = calc.get("value", _GAP)
        vc = ws.cell(row=row, column=2, value=val if val not in (None, "") else _GAP)
        vc.font = _data_font()
        vc.alignment = _right_align()
        vc.border = _thin_border()
        if row % 2 == 0:
            vc.fill = _alt_fill()
        fc = ws.cell(row=row, column=3, value=calc.get("formula", "") or "")
        fc.font = _data_font(color="6B7280")
        fc.alignment = _right_align()
        fc.border = _thin_border()

        label = calc.get("label", "")
        if "حكومية" in label and "ضريبة" in label:
            govt_tax_row = row
        if "استرشادي" in label and "ضريبة" in label:
            corr_tax_row = row
        if "م²" in label and "موضوع" in label:
            area_row = row
        row += 1

    # Excel formula row for overcharge
    if govt_tax_row and corr_tax_row:
        row += 1
        _write_section_header(ws, row, "صيغة المقارنة الضريبية", ncols=3, color="5C1A1A"); row += 1
        ws.cell(row=row, column=1, value="فارق المغالاة الحكومية (ج.م)").font = _hdr_font(color="5C1A1A", size=9)
        ws.cell(row=row, column=1).alignment = _right_align(wrap=False)
        ws.cell(row=row, column=1).border = _thin_border()
        fml_overcharge = f"=IF(AND(ISNUMBER(B{govt_tax_row}),ISNUMBER(B{corr_tax_row})),B{govt_tax_row}-B{corr_tax_row},\"{_EXPERT}\")"
        oc = ws.cell(row=row, column=2, value=fml_overcharge)
        oc.font = _data_font()
        oc.fill = _formula_fill()
        oc.alignment = _right_align()
        oc.border = _thin_border()
        ws.cell(row=row, column=3, value="= ضريبة حكومية − ضريبة استرشادية").font = _data_font(color="6B7280")
        row += 1

        ws.cell(row=row, column=1, value="نسبة المغالاة (%)").font = _hdr_font(color="5C1A1A", size=9)
        ws.cell(row=row, column=1).alignment = _right_align(wrap=False)
        ws.cell(row=row, column=1).border = _thin_border()
        fml_pct = f"=IF(AND(ISNUMBER(B{govt_tax_row}),B{govt_tax_row}>0),(B{govt_tax_row}-B{corr_tax_row})/B{govt_tax_row},\"{_EXPERT}\")"
        pc = ws.cell(row=row, column=2, value=fml_pct)
        pc.font = _data_font()
        pc.fill = _formula_fill()
        pc.alignment = _right_align()
        pc.border = _thin_border()
        ws.cell(row=row, column=3, value="= فارق / حكومي").font = _data_font(color="6B7280")
        row += 1

    # ── Table 1: Government Assessment ───────────────────────────────────────
    govt_tbl = m.get("government_assessment_table", {})
    if govt_tbl:
        row += 1
        _write_section_header(ws, row, "جدول تقييم الحكومة", ncols=3, color="7B2D00"); row += 1
        for key, val in govt_tbl.items():
            label_map = {
                "govt_assessed_rental_value": "القيمة الإيجارية الحكومية (ج.م)",
                "govt_tax_amount": "الضريبة الحكومية (ج.م)",
                "tax_year_or_cycle": "دورة الفحص / السنة",
                "notice_number": "رقم الإخطار",
                "notice_date": "تاريخ الإخطار",
                "basis_date": "تاريخ التقرير",
                "govt_tax_per_m2": "الضريبة الحكومية / م²",
            }
            _apply_row(ws, row, label_map.get(key, key), val); row += 1

    # ── Table 2: Expert Indication ────────────────────────────────────────────
    expert_tbl = m.get("expert_indication_table", {})
    if expert_tbl:
        row += 1
        _write_section_header(ws, row, "جدول تقدير الخبير", ncols=3, color="1A4D2E"); row += 1
        for key, val in expert_tbl.items():
            label_map = {
                "expert_indicated_rental_value": "القيمة الإيجارية الاسترشادية (ج.م)",
                "expert_indicated_rental_per_m2": "قيمة إيجارية / م² (ج.م)",
                "expert_indicated_tax_amount": "الضريبة الاسترشادية (ج.م)",
                "expert_tax_per_m2": "ضريبة استرشادية / م²",
                "calculation_basis": "أساس الحساب",
                "notes": "ملاحظات",
            }
            _apply_row(ws, row, label_map.get(key, key), val); row += 1

    # ── Table 3: Comparable Tax Cases ────────────────────────────────────────
    cases = m.get("comparable_tax_cases", [])
    if cases:
        row += 1
        _write_section_header(ws, row, "جدول الحالات الضريبية المقارنة", ncols=3, color="374151"); row += 1
        from openpyxl.styles import Font as _F, PatternFill as _PF, Alignment as _AL
        tc_headers = ["رقم الحالة", "الموقع", "المساحة (م²)", "الضريبة (ج.م)", "ض./م²", "ض. معدَّلة/م²", "مُدرجة؟"]
        for ci, hdr in enumerate(tc_headers, start=1):
            hc = ws.cell(row=row, column=ci, value=hdr)
            hc.fill = _PF("solid", fgColor="374151")
            hc.font = _F(name="Cairo", bold=True, size=8, color="FFFFFF")
            hc.alignment = _AL(horizontal="center", vertical="center")
        row += 1
        for case in cases:
            vals = [
                case.get("tax_case_id", ""),
                str(case.get("location", ""))[:40],
                case.get("area", _GAP),
                case.get("tax_amount", _GAP),
                case.get("tax_per_m2", _GAP),
                case.get("adjusted_tax_per_m2", _GAP),
                "نعم" if case.get("included") else "لا",
            ]
            for ci, v in enumerate(vals, start=1):
                c = ws.cell(row=row, column=ci, value=v if v not in (None, "") else _GAP)
                c.font = _data_font()
                c.alignment = _right_align()
                c.border = _thin_border()
                if row % 2 == 0:
                    c.fill = _alt_fill()
            row += 1
        # Source note
        note_txt = cases[0].get("source_note", "")
        if note_txt:
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=7)
            nc = ws.cell(row=row, column=1, value=note_txt)
            nc.font = _F(name="Cairo", italic=True, size=8, color="7F1D1D")
            nc.alignment = _right_align()
            row += 1

    # ── Table 4: Tax Gap ─────────────────────────────────────────────────────
    gap_tbl = m.get("tax_gap_table", {})
    if gap_tbl:
        row += 1
        _write_section_header(ws, row, "جدول فارق الضريبة والوفر المتوقع", ncols=3, color="5C1A1A"); row += 1
        for key, val in gap_tbl.items():
            if key.startswith("formula_"):
                continue
            label_map = {
                "government_tax": "الضريبة الحكومية (ج.م)",
                "indicated_tax":  "الضريبة الاسترشادية (ج.م)",
                "comparable_avg_tax": "متوسط الحالات المقارنة (ج.م)",
                "overcharge_amount": "فارق المغالاة (ج.م)",
                "overcharge_percentage": "نسبة المغالاة",
                "expected_saving": "الوفر المتوقع (ج.م)",
                "conclusion": "الخلاصة",
            }
            _apply_row(ws, row, label_map.get(key, key), val,
                       is_formula=key in ("overcharge_amount","expected_saving")); row += 1

    row += 1


def _sheet_five_regression(ws, ctx: dict) -> None:
    """طريقة الانحدار المتعدد — future-ready regression sheet."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 44
    ws.column_dimensions["B"].width = 28
    ws.column_dimensions["C"].width = 26

    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells("A1:C1")
    c = ws["A1"]
    c.value     = "طريقة الانحدار المتعدد — Multiple Regression (جاهزية مستقبلية)"
    c.fill      = PatternFill("solid", fgColor="374151")
    c.font      = Font(name="Cairo", bold=True, size=12, color="FFFFFF")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    methods = ctx.get("tax_valuation_methods", [])
    m = next((x for x in methods if x.get("method_key") == "multiple_regression_approach"), {})

    row = 3
    _write_section_header(ws, row, "حالة النموذج الإحصائي", ncols=3, color="374151"); row += 1
    _apply_row(ws, row, "حالة الطريقة",     m.get("data_availability_status", _GAP)); row += 1
    _apply_row(ws, row, "ملاحظة النموذج",  m.get("expert_notes", _GAP)); row += 1
    _apply_row(ws, row, "الاستكمال المستقبلي", m.get("future_enrichment_status", _GAP)); row += 1

    row += 1
    _write_section_header(ws, row, "متغيرات النموذج ومساهماتها", ncols=3, color="374151"); row += 1

    for col, hdr in enumerate(["المتغير", "القيمة / المساهمة", "الصيغة"], start=1):
        hc = ws.cell(row=row, column=col, value=hdr)
        hc.fill      = PatternFill("solid", fgColor="1F4E78")
        hc.font      = Font(name="Cairo", bold=True, size=9, color="FFFFFF")
        hc.alignment = Alignment(horizontal="center", vertical="center")
    row += 1

    predicted_row = None
    expert_row = None
    for calc in m.get("calculation_rows", []):
        lc = ws.cell(row=row, column=1, value=calc.get("label", ""))
        lc.font = _hdr_font(color="1B2E4B", size=9)
        lc.fill = PatternFill("solid", fgColor="EFF2F7")
        lc.alignment = _right_align(wrap=False)
        lc.border = _thin_border()
        val = calc.get("value", _GAP)
        vc = ws.cell(row=row, column=2, value=val if val not in (None, "") else _GAP)
        vc.font = _data_font()
        vc.alignment = _right_align()
        vc.border = _thin_border()
        if row % 2 == 0:
            vc.fill = _alt_fill()
        fc = ws.cell(row=row, column=3, value=calc.get("formula", "") or "")
        fc.font = _data_font(color="6B7280")
        fc.alignment = _right_align()
        fc.border = _thin_border()
        label = calc.get("label", "")
        if "متوقعة" in label:
            predicted_row = row
        if "خبير" in label:
            expert_row = row
        row += 1

    # Residual formula if both rows exist
    if predicted_row and expert_row:
        row += 1
        _write_section_header(ws, row, "الفارق (Residual)", ncols=3, color="374151"); row += 1
        ws.cell(row=row, column=1, value="الفارق = |متوقع − خبير|").font = _hdr_font(color="374151", size=9)
        ws.cell(row=row, column=1).alignment = _right_align(wrap=False)
        ws.cell(row=row, column=1).border = _thin_border()
        fml = f"=IF(AND(ISNUMBER(B{predicted_row}),ISNUMBER(B{expert_row})),ABS(B{predicted_row}-B{expert_row}),\"{_GAP}\")"
        rc = ws.cell(row=row, column=2, value=fml)
        rc.font = _data_font()
        rc.fill = _formula_fill()
        rc.alignment = _right_align()
        rc.border = _thin_border()
        row += 1

    # ── Detailed variable table (from task spec structure) ────────────────────
    var_table = m.get("variable_table", [])
    if var_table:
        row += 1
        _write_section_header(ws, row, "جدول المتغيرات والمعاملات التفصيلي", ncols=3, color="374151"); row += 1
        ws.column_dimensions["A"].width = 26
        ws.column_dimensions["B"].width = 16
        ws.column_dimensions["C"].width = 18
        ws.column_dimensions["D"].width = 18
        ws.column_dimensions["E"].width = 16
        ws.column_dimensions["F"].width = 22
        from openpyxl.styles import Font as _F2, PatternFill as _PF2, Alignment as _AL2
        vt_headers = ["المتغير", "القيمة", "المعامل", "المساهمة", "الحالة", "ملاحظات"]
        for ci, hdr in enumerate(vt_headers, start=1):
            hc = ws.cell(row=row, column=ci, value=hdr)
            hc.fill      = _PF2("solid", fgColor="374151")
            hc.font      = _F2(name="Cairo", bold=True, size=8, color="FFFFFF")
            hc.alignment = _AL2(horizontal="center", vertical="center")
        row += 1
        for vr in var_table:
            vals = [
                vr.get("variable_ar", ""),
                vr.get("value", _GAP),
                vr.get("coefficient", _GAP),
                vr.get("contribution", _GAP),
                vr.get("source_status", ""),
                vr.get("notes", ""),
            ]
            for ci, v in enumerate(vals, start=1):
                c = ws.cell(row=row, column=ci, value=v if v not in (None, "") else _GAP)
                c.font      = _data_font()
                c.alignment = _right_align()
                c.border    = _thin_border()
                if row % 2 == 0:
                    c.fill = _alt_fill()
            row += 1

    # ── Model metadata ────────────────────────────────────────────────────────
    meta = m.get("model_metadata", {})
    if meta:
        row += 1
        _write_section_header(ws, row, "معلومات النموذج", ncols=3, color="374151"); row += 1
        for key, val in meta.items():
            if key == "variables_count":
                continue
            label_map = {
                "r_squared": "معامل التحديد R²",
                "observations_needed": "عدد الملاحظات المطلوبة",
                "training_status": "حالة التدريب",
                "simulation_note": "ملاحظة المحاكاة",
            }
            _apply_row(ws, row, label_map.get(key, key), val); row += 1

    # ── Governance block (Part I) ─────────────────────────────────────────────
    row += 1
    _write_section_header(ws, row, "حوكمة طريقة الانحدار المتعدد — وضع التفعيل", ncols=3, color="374151"); row += 1
    from openpyxl.styles import Font as _Font, PatternFill as _PF3
    gov_badge_val = (
        "⚙ محاكاة QA فقط — " + m.get("regression_status", _GAP)
        if m.get("qa_simulation_only")
        else "⊘ غير مفعلة إنتاجيًا — " + m.get("regression_status", _GAP)
    )
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
    badge = ws.cell(row=row, column=1, value=gov_badge_val)
    badge.fill = _PF3("solid", fgColor="FEF3C7" if m.get("qa_simulation_only") else "F1F5F9")
    badge.font = _Font(name="Cairo", bold=True, size=9, color="92400E" if m.get("qa_simulation_only") else "374151")
    badge.alignment = _right_align()
    row += 1

    gov_rows = [
        ("قاعدة بيانات تدريب متاحة؟", "لا" if not m.get("training_dataset_available") else "نعم"),
        ("نموذج مُدرَّب؟",             "لا" if not m.get("model_trained")               else "نعم"),
        ("حالة التحقق",                m.get("model_validation_status", _GAP)),
        ("محاكاة QA فقط؟",             "نعم" if m.get("qa_simulation_only")              else "لا"),
        ("مسموح بوزن إنتاجي؟",         "لا" if not m.get("production_weight_allowed")    else "نعم"),
        ("سبب الاستبعاد من التوفيق",    m.get("reason_for_exclusion_from_reconciliation", _GAP)),
    ]
    for lbl, val in gov_rows:
        _apply_row(ws, row, lbl, val); row += 1

    row += 1
    _write_section_header(ws, row, "متطلبات التفعيل المستقبلي", ncols=3, color="374151"); row += 1
    for req in m.get("future_activation_requirements", []):
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
        rc = ws.cell(row=row, column=1, value=f"• {req}")
        rc.font      = _data_font()
        rc.alignment = _right_align(wrap=True)
        rc.fill      = _alt_fill()
        row += 1

    row += 1
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    nc = ws.cell(row=row, column=1,
                 value="محاكاة QA — ليست نموذجًا إحصائيًا حقيقيًا. "
                       "يُفعَّل الانحدار الحقيقي عند توفر قاعدة بيانات كافية ومراجعة النموذج.")
    nc.font = _Font(name="Cairo", italic=True, size=9, color="7F1D1D")
    nc.alignment = _right_align()


def _sheet_assumptions(ws, ctx: dict) -> None:
    """الافتراضات والإفصاحات — Assumptions disclosure sheet (Part C)."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    for col, width in zip("ABCDEFGHIJ", (12, 14, 50, 24, 14, 14, 28, 36, 14, 28)):
        ws.column_dimensions[col].width = width
    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells("A1:J1")
    c = ws["A1"]
    c.value     = "الافتراضات العامة والافتراضات الخاصة ومحددات الاستخدام — Assumptions & Limiting Conditions"
    c.fill      = PatternFill("solid", fgColor="1B4332")
    c.font      = Font(name="Cairo", bold=True, size=12, color="FFFFFF")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    disc = ctx.get("assumptions_disclosure", {})

    row = 3
    # Separator note
    sep = disc.get("extraordinary_separator_note", "")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=10)
    sep_c = ws.cell(row=row, column=1, value=sep)
    sep_c.fill      = PatternFill("solid", fgColor="D1FAE5")
    sep_c.font      = Font(name="Cairo", bold=True, size=9, color="065F46")
    sep_c.alignment = _right_align(wrap=True)
    ws.row_dimensions[row].height = 30
    row += 2

    headers = [
        "المعرف", "نوع الافتراض", "نص الافتراض", "ينطبق على",
        "يؤثر على القيمة؟", "يؤثر على الضريبة؟",
        "حالة التحقق", "إجراء الخبير المطلوب", "جاهز للإنتاج؟", "ملاحظات"
    ]
    _write_section_header(ws, row, "جدول الافتراضات الكامل", ncols=10, color="1B4332"); row += 1
    for i, hdr in enumerate(headers, start=1):
        hc = ws.cell(row=row, column=i, value=hdr)
        hc.fill      = PatternFill("solid", fgColor="2D6A4F")
        hc.font      = Font(name="Cairo", bold=True, size=8, color="FFFFFF")
        hc.alignment = _center_align()
        hc.border    = _thin_border()
    row += 1

    all_rows = disc.get("all_assumption_rows", [])
    for i, r in enumerate(all_rows):
        is_extra = r.get("assumption_type", "") in ("خاص / استثنائي",)
        row_fill = PatternFill("solid", fgColor="FEF3C7") if is_extra else (
            _alt_fill() if i % 2 == 0 else PatternFill("solid", fgColor="FFFFFF")
        )
        for j, val in enumerate([
            r.get("assumption_id", ""),
            r.get("assumption_type", ""),
            r.get("assumption_text", ""),
            r.get("applies_to_method", ""),
            "نعم" if r.get("affects_value") else "لا",
            "نعم" if r.get("affects_tax")   else "لا",
            r.get("verification_status", ""),
            r.get("expert_action_required", "") or _EXPERT,
            "لا" if not r.get("production_ready") else "نعم",
            r.get("notes", "") or "",
        ], start=1):
            dc = ws.cell(row=row, column=j, value=val)
            dc.font      = _data_font()
            dc.alignment = _right_align(wrap=(j == 3))
            dc.border    = _thin_border()
            dc.fill      = row_fill
        row += 1

    row += 1
    # Summary section
    _write_section_header(ws, row, "ملخص الإفصاح", ncols=10, color="1B4332"); row += 1
    for label, key in [
        ("أثر الافتراضات على القيمة", "assumptions_impact_on_value"),
        ("أثر الافتراضات على الضريبة", "assumptions_impact_on_tax"),
        ("حالة الإفصاح", "disclosure_status"),
        ("يحتاج تأكيد خبير؟", "expert_confirmation_required"),
    ]:
        val = disc.get(key, _GAP)
        _apply_row(ws, row, label, "نعم" if val is True else ("لا" if val is False else str(val))); row += 1

    row += 1
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=10)
    adv = ws.cell(row=row, column=1, value=disc.get("disclosure_advisory", ""))
    adv.fill      = PatternFill("solid", fgColor="D1FAE5")
    adv.font      = Font(name="Cairo", italic=True, size=8, color="065F46")
    adv.alignment = _right_align()


def _sheet_sensitivity(ws, ctx: dict) -> None:
    """تحليل الحساسية — Sensitivity analysis sheet (Part F)."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    for col, width in zip("AB", (42, 28)):
        ws.column_dimensions[col].width = width
    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells("A1:B1")
    c = ws["A1"]
    c.value     = "تحليل الحساسية ونطاق النتيجة الاسترشادي — Sensitivity Analysis"
    c.fill      = PatternFill("solid", fgColor="1E40AF")
    c.font      = Font(name="Cairo", bold=True, size=12, color="FFFFFF")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    sa = ctx.get("sensitivity_analysis", {})
    rec = ctx.get("five_method_reconciliation", {})
    fct = rec.get("final_conclusion_table", {})

    row = 3
    _write_section_header(ws, row, "جدول تحليل الحساسية", ncols=2, color="1E40AF"); row += 1

    base_tax_val = sa.get("base_indicated_tax", 0.0)
    pct_val      = sa.get("sensitivity_pct", 0.0)

    # Input cells (yellow)
    ws.cell(row=row, column=1, value="الضريبة الاسترشادية الأساسية (ج.م)").font = _hdr_font(color="1B2E4B")
    ws.cell(row=row, column=1).alignment = _right_align()
    ws.cell(row=row, column=1).border    = _thin_border()
    ic = ws.cell(row=row, column=2, value=base_tax_val if base_tax_val else 0.0)
    ic.fill      = _input_fill()
    ic.number_format = _FMT_CURRENCY
    ic.border    = _thin_border()
    ic.font      = _data_font()
    base_row = row; row += 1

    ws.cell(row=row, column=1, value="نسبة الحساسية الاسترشادية").font = _hdr_font(color="1B2E4B")
    ws.cell(row=row, column=1).alignment = _right_align()
    ws.cell(row=row, column=1).border    = _thin_border()
    pc = ws.cell(row=row, column=2, value=pct_val if pct_val else 0.0)
    pc.fill        = _input_fill()
    pc.number_format = _FMT_PCT
    pc.border      = _thin_border()
    pc.font        = _data_font()
    pct_row = row; row += 1

    # Calculated cells (blue formulas)
    def _fcell(r, label, formula, fmt=_FMT_CURRENCY):
        ws.cell(row=r, column=1, value=label).font = _hdr_font(color="1B2E4B")
        ws.cell(row=r, column=1).alignment = _right_align()
        ws.cell(row=r, column=1).border    = _thin_border()
        fc = ws.cell(row=r, column=2, value=formula)
        fc.fill        = _formula_fill()
        fc.number_format = fmt
        fc.border      = _thin_border()
        fc.font        = _data_font(color="1E40AF")

    _fcell(row, "الحد المنخفض للضريبة (= أساس × (1 − حساسية))",
           f"=B{base_row}*(1-B{pct_row})"); row += 1
    low_row = row - 1

    _fcell(row, "الحد المرتفع للضريبة (= أساس × (1 + حساسية))",
           f"=B{base_row}*(1+B{pct_row})"); row += 1
    high_row = row - 1

    # Government tax (another input)
    gov_tax_val = ctx.get("government_tax_amount") or 0.0
    try:
        gov_tax_val = float(str(gov_tax_val).replace(",", ""))
    except Exception:
        gov_tax_val = 0.0
    ws.cell(row=row, column=1, value="الضريبة الحكومية (ج.م)").font = _hdr_font(color="1B2E4B")
    ws.cell(row=row, column=1).alignment = _right_align()
    ws.cell(row=row, column=1).border    = _thin_border()
    gc = ws.cell(row=row, column=2, value=gov_tax_val)
    gc.fill = _input_fill()
    gc.number_format = _FMT_CURRENCY
    gc.border = _thin_border()
    gc.font   = _data_font()
    gov_row = row; row += 1

    _fcell(row, "الوفر المتوقع — أدنى (= حكومي − حد مرتفع)",
           f"=B{gov_row}-B{high_row}"); row += 1
    _fcell(row, "الوفر المتوقع — الأساس (= حكومي − أساس)",
           f"=B{gov_row}-B{base_row}"); row += 1
    _fcell(row, "الوفر المتوقع — أعلى (= حكومي − حد منخفض)",
           f"=B{gov_row}-B{low_row}"); row += 1

    row += 1
    _write_section_header(ws, row, "محركات الحساسية الرئيسية", ncols=2, color="1E40AF"); row += 1
    for d in sa.get("key_sensitivity_drivers", []):
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
        dc = ws.cell(row=row, column=1, value=f"• {d}")
        dc.font      = _data_font()
        dc.alignment = _right_align(wrap=True)
        dc.fill      = _alt_fill()
        row += 1

    row += 1
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
    note_c = ws.cell(row=row, column=1,
                     value=sa.get("no_statistical_certainty_note", ""))
    note_c.fill      = PatternFill("solid", fgColor="DBEAFE")
    note_c.font      = Font(name="Cairo", italic=True, size=8, color="1E3A8A")
    note_c.alignment = _right_align(wrap=True)
    ws.row_dimensions[row].height = 36


def _sheet_five_reconciliation(ws, ctx: dict) -> None:
    """توفيق الطرق الخمس — five-method reconciliation sheet."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 22
    ws.column_dimensions["C"].width = 20
    ws.column_dimensions["D"].width = 18
    ws.column_dimensions["E"].width = 22
    ws.column_dimensions["F"].width = 24

    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells("A1:F1")
    c = ws["A1"]
    c.value     = "توفيق نتائج الطرق الخمس — Five-Method Reconciliation"
    c.fill      = PatternFill("solid", fgColor="1B2E4B")
    c.font      = Font(name="Cairo", bold=True, size=12, color="C9973A")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    rec = ctx.get("five_method_reconciliation", {})

    # Table header
    headers = ["الطريقة", "حالة البيانات", "الدلالة (ج.م)", "الوزن", "النتيجة المرجحة", "ملاحظات الخبير"]
    for col, hdr in enumerate(headers, start=1):
        hc = ws.cell(row=2, column=col, value=hdr)
        hc.fill      = PatternFill("solid", fgColor="1F4E78")
        hc.font      = Font(name="Cairo", bold=True, size=9, color="FFFFFF")
        hc.alignment = Alignment(horizontal="center", vertical="center")
        hc.border    = _thin_border()
    ws.row_dimensions[2].height = 18

    # ── Applicability table (from new applicability_table field) ─────────────
    row = 3
    app_table = rec.get("applicability_table", [])
    if app_table:
        _write_section_header(ws, row, "جدول الانطباقية والأوزان", ncols=6, color="C9973A"); row += 1
        app_headers = ["الطريقة", "الانطباقية", "حالة البيانات", "الدلالة (ج.م)", "الوزن", "مُدرجة؟"]
        for ci, hdr in enumerate(app_headers, start=1):
            hc = ws.cell(row=row, column=ci, value=hdr)
            hc.fill      = PatternFill("solid", fgColor="1F4E78")
            hc.font      = Font(name="Cairo", bold=True, size=9, color="FFFFFF")
            hc.alignment = Alignment(horizontal="center", vertical="center")
            hc.border    = _thin_border()
        row += 1
        for entry in app_table:
            for ci, val in enumerate([
                entry.get("method", _GAP),
                entry.get("applicability", _GAP),
                entry.get("data_status", _GAP),
                entry.get("indicated_value", _GAP),
                entry.get("weight", _GAP),
                "نعم" if entry.get("included") else "لا — مساند",
            ], start=1):
                cell = ws.cell(row=row, column=ci, value=val if val not in (None, "") else _GAP)
                cell.font      = _data_font()
                cell.alignment = _right_align()
                cell.border    = _thin_border()
                if row % 2 == 0:
                    cell.fill = _alt_fill()
            row += 1

    # ── Weighting table (method_weight entries) ───────────────────────────────
    row += 1
    _write_section_header(ws, row, "جدول الأوزان والنتائج المرجحة", ncols=6, color="1B2E4B"); row += 1
    headers = ["الطريقة", "حالة البيانات", "الدلالة (ج.م)", "الوزن", "النتيجة المرجحة", "ملاحظات"]
    for col, hdr in enumerate(headers, start=1):
        hc = ws.cell(row=row, column=col, value=hdr)
        hc.fill      = PatternFill("solid", fgColor="1F4E78")
        hc.font      = Font(name="Cairo", bold=True, size=9, color="FFFFFF")
        hc.alignment = Alignment(horizontal="center", vertical="center")
        hc.border    = _thin_border()
    ws.row_dimensions[row].height = 18
    row += 1

    for entry in rec.get("method_weight", []):
        for col, val in enumerate([
            entry.get("method", _GAP),
            entry.get("note", "—") or "—",
            entry.get("value", _GAP),
            entry.get("weight", _GAP),
            entry.get("weighted", _GAP),
            "—",
        ], start=1):
            cell = ws.cell(row=row, column=col, value=val if val not in (None, "") else _GAP)
            cell.font      = _data_font()
            cell.alignment = _right_align()
            cell.border    = _thin_border()
            if row % 2 == 0:
                cell.fill = _alt_fill()
        row += 1

    # ── Final conclusion table ────────────────────────────────────────────────
    fcl = rec.get("final_conclusion_table", {})
    row += 1
    _write_section_header(ws, row, "الخلاصة والقيمة المختارة من الخبير", ncols=6, color="1B2E4B"); row += 1

    summary_rows = [
        ("النتيجة المرجحة الإجمالية (ج.م)",      fcl.get("weighted_result") or rec.get("weighted_result", _GAP)),
        ("القيمة المختارة من الخبير (ج.م)",       fcl.get("expert_selected_value") or rec.get("expert_selected_value", _GAP)),
        ("الضريبة المختارة من الخبير (ج.م)",      fcl.get("expert_selected_tax") or rec.get("expert_selected_tax_amount", _GAP)),
        ("الضريبة الحكومية (ج.م)",                fcl.get("government_tax") or _GAP),
        ("فارق المغالاة (ج.م)",                   fcl.get("overcharge_amount") or _GAP),
        ("الوفر المتوقع (ج.م)",                   fcl.get("expected_savings") or rec.get("expected_savings", _GAP)),
        ("الطرق المستخدمة",                       ", ".join(fcl.get("methods_used", [])) or _GAP),
        ("الخلاصة",                               fcl.get("conclusion_ar") or rec.get("reconciliation_notes", _GAP)),
    ]
    for lbl, val in summary_rows:
        lc = ws.cell(row=row, column=1, value=lbl)
        lc.font = _hdr_font(color="1B2E4B", size=9)
        lc.fill = PatternFill("solid", fgColor="EFF2F7")
        lc.alignment = _right_align(wrap=False)
        lc.border = _thin_border()
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=6)
        vc = ws.cell(row=row, column=2, value=val if val not in (None, "") else _GAP)
        vc.font = _data_font(bold=True)
        vc.alignment = _right_align()
        vc.border = _thin_border()
        if row % 2 == 0:
            vc.fill = _alt_fill()
        row += 1

    row += 1
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    nc = ws.cell(row=row, column=1,
                 value=ctx.get("five_method_future_enrichment_note", ""))
    nc.font = Font(name="Cairo", italic=True, size=9, color="B43200")
    nc.alignment = _right_align()


# ── Professional governance sheet builders ────────────────────────────────────

def _sheet_hbu_analysis(ws, ctx: dict) -> None:
    """تحليل HBU — Highest and Best Use analysis sheet."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 36
    ws.column_dimensions["B"].width = 54
    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells("A1:B1")
    c = ws["A1"]
    c.value     = "تحليل أعلى وأفضل استغلال — HBU Analysis"
    c.fill      = PatternFill("solid", fgColor="1F3A5F")
    c.font      = Font(name="Cairo", bold=True, size=12, color="FFFFFF")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    hbu = ctx.get("hbu_analysis", {})
    row = 3
    _write_section_header(ws, row, "مكوّنات تحليل HBU", ncols=2, color="1F3A5F"); row += 1
    _apply_row(ws, row, "الاستخدام الحالي",            hbu.get("current_use")); row += 1
    _apply_row(ws, row, "الاستخدام المرخص",            hbu.get("licensed_use")); row += 1
    _apply_row(ws, row, "الاستخدامات الممكنة ماديًا",  hbu.get("physically_possible_uses")); row += 1
    _apply_row(ws, row, "الاستخدامات المسموح بها قانونًا", hbu.get("legally_permissible_uses")); row += 1
    _apply_row(ws, row, "الاستخدامات المجدية ماليًا",  hbu.get("financially_feasible_uses")); row += 1
    _apply_row(ws, row, "الاستخدام الأعلى إنتاجية",   hbu.get("maximally_productive_use")); row += 1

    row += 1
    _write_section_header(ws, row, "خلاصة HBU وأثره", ncols=2, color="2D6A4F"); row += 1
    _apply_row(ws, row, "خلاصة HBU",                  hbu.get("hbu_conclusion")); row += 1
    _apply_row(ws, row, "أثر HBU على القيمة الإيجارية", hbu.get("hbu_effect_on_rental_value")); row += 1
    _apply_row(ws, row, "أثر HBU على الوعاء الضريبي", hbu.get("hbu_effect_on_tax_basis")); row += 1
    _apply_row(ws, row, "أثر HBU على أوزان الطرق",    hbu.get("hbu_effect_on_method_weighting")); row += 1

    row += 1
    _write_section_header(ws, row, "متطلبات الاستكمال وملاحظات الخبير", ncols=2, color="7B2D00"); row += 1
    missing = hbu.get("hbu_required_missing_inputs", [])
    _apply_row(ws, row, "المستندات المطلوبة", " | ".join(missing) if missing else _GAP); row += 1
    _apply_row(ws, row, "ملاحظات الخبير",    hbu.get("hbu_expert_notes")); row += 1
    _apply_row(ws, row, "حالة البيانات",      hbu.get("hbu_data_status")); row += 1

    row += 1
    advisory = hbu.get("hbu_advisory_note", "")
    note_cell = ws.cell(row=row, column=1, value=advisory)
    note_cell.font      = Font(name="Cairo", italic=True, size=8, color="92400E")
    note_cell.alignment = _right_align()
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)


def _sheet_standards_mapping(ws, ctx: dict) -> None:
    """المعايير المهنية — Professional standards mapping sheet."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    for col, width in zip("ABCDEF", (28, 36, 28, 32, 30, 30)):
        ws.column_dimensions[col].width = width
    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells("A1:F1")
    c = ws["A1"]
    c.value     = "ربط الطرق بالمعايير المهنية — Professional Standards Mapping"
    c.fill      = PatternFill("solid", fgColor="3B1F6B")
    c.font      = Font(name="Cairo", bold=True, size=12, color="FFFFFF")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    std = ctx.get("standards_mapping", {})
    rows_data = std.get("standards_mapping_rows", [])

    # Header row
    headers = ["الطريقة", "المبدأ المهني", "العائلة المعيارية", "حالة المرجع / التوثيق", "ملاحظة الاستخدام", "القيود"]
    row = 3
    _write_section_header(ws, row, "جدول ربط الطرق بالمعايير", ncols=6, color="3B1F6B"); row += 1

    for i, hdr in enumerate(headers, start=1):
        hc = ws.cell(row=row, column=i, value=hdr)
        hc.fill      = PatternFill("solid", fgColor="5B3FA0")
        hc.font      = Font(name="Cairo", bold=True, size=9, color="FFFFFF")
        hc.alignment = _center_align()
        hc.border    = _thin_border()
    row += 1

    for i, r in enumerate(rows_data):
        fill = _alt_fill() if i % 2 == 0 else PatternFill("solid", fgColor="FFFFFF")
        for j, val in enumerate([
            r.get("method_name", ""),
            r.get("valuation_principle", ""),
            r.get("standard_family", ""),
            r.get("standard_reference_status", ""),
            r.get("professional_use_note", ""),
            r.get("limitations_note", ""),
        ], start=1):
            dc = ws.cell(row=row, column=j, value=val)
            dc.font      = _data_font()
            dc.alignment = _right_align()
            dc.border    = _thin_border()
            dc.fill      = fill
        row += 1

    row += 1
    # Advisory note
    note_text = std.get("standards_advisory_note", "")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    nc = ws.cell(row=row, column=1, value=note_text)
    nc.fill      = PatternFill("solid", fgColor="EDE9FE")
    nc.font      = Font(name="Cairo", italic=True, size=8, color="4C1D95")
    nc.alignment = _right_align()
    row += 1

    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    vc = ws.cell(row=row, column=1,
                 value=f"حالة التحقق: {std.get('standards_verification_status', _EXPERT)}")
    vc.fill      = PatternFill("solid", fgColor="FEF3C7")
    vc.font      = Font(name="Cairo", bold=True, size=9, color="92400E")
    vc.alignment = _right_align()


def _sheet_data_governance(ws, ctx: dict) -> None:
    """حوكمة البيانات — Data provenance governance sheet."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    for col, width in zip("ABCDEFGHIJ", (24, 30, 22, 20, 20, 14, 14, 28, 26, 20)):
        ws.column_dimensions[col].width = width
    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells("A1:J1")
    c = ws["A1"]
    c.value     = "حوكمة البيانات ومصادرها — Data Provenance Governance"
    c.fill      = PatternFill("solid", fgColor="1A2E4A")
    c.font      = Font(name="Cairo", bold=True, size=12, color="FFFFFF")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    gov = ctx.get("data_governance", {})
    rows_data = gov.get("data_governance_rows", [])
    summary   = gov.get("data_governance_summary", {})

    # Header row
    headers = ["الطريقة", "عنصر البيانات", "القيمة", "نوع المصدر",
               "حالة المصدر", "محاكاة QA؟", "جاهز للإنتاج؟",
               "الدليل المطلوب", "إجراء الخبير", "ملاحظات"]
    row = 3
    _write_section_header(ws, row, "جدول حوكمة البيانات", ncols=10, color="1A2E4A"); row += 1

    for i, hdr in enumerate(headers, start=1):
        hc = ws.cell(row=row, column=i, value=hdr)
        hc.fill      = PatternFill("solid", fgColor="2E4A6A")
        hc.font      = Font(name="Cairo", bold=True, size=9, color="FFFFFF")
        hc.alignment = _center_align()
        hc.border    = _thin_border()
    row += 1

    for i, r in enumerate(rows_data):
        is_qa_row  = r.get("is_qa_simulation", False)
        is_prod    = r.get("production_ready", False)
        row_fill   = _warn_fill() if is_qa_row and not is_prod else (_alt_fill() if i % 2 == 0 else PatternFill("solid", fgColor="FFFFFF"))
        for j, val in enumerate([
            r.get("method", ""),
            r.get("data_item", ""),
            r.get("value", ""),
            r.get("source_type", ""),
            r.get("source_status", ""),
            "نعم" if is_qa_row else "لا",
            "نعم" if is_prod   else "لا",
            r.get("required_evidence", ""),
            r.get("expert_action", ""),
            r.get("notes", ""),
        ], start=1):
            dc = ws.cell(row=row, column=j, value=val)
            dc.font      = _data_font()
            dc.alignment = _right_align()
            dc.border    = _thin_border()
            dc.fill      = row_fill
        row += 1

    row += 1
    # Summary section
    _write_section_header(ws, row, "ملخص حوكمة البيانات", ncols=10, color="374151"); row += 1
    for label, key in [
        ("محاكاة QA نشطة؟", "qa_simulation_active"),
        ("عدد الطرق الجاهزة للإنتاج", "production_ready_count"),
        ("عدد الطرق QA فقط", "qa_only_count"),
        ("الانحدار جاهز للإنتاج؟", "regression_production_ready"),
    ]:
        val = summary.get(key, _GAP)
        _apply_row(ws, row, label, "نعم" if val is True else ("لا" if val is False else str(val))); row += 1

    row += 1
    for note_key in ("validation_note", "no_live_data_note"):
        note = summary.get(note_key, "")
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=10)
        nc = ws.cell(row=row, column=1, value=note)
        nc.fill      = PatternFill("solid", fgColor="FEF3C7")
        nc.font      = Font(name="Cairo", italic=True, size=8, color="92400E")
        nc.alignment = _right_align()
        row += 1

    # Tax assessment basis date governance row
    row += 1
    _write_section_header(ws, row, "حوكمة تاريخ الحصر الضريبي", ncols=10, color="7B2D00"); row += 1
    basis_date_val = ctx.get("tax_assessment_basis_date", _GAP)
    basis_date_gap = bool(
        not ctx.get("tax_assessment_basis_date_raw")
        and ctx.get("tax_mode") != "transfer_tax"
    )
    basis_note = (
        "آخر تاريخ حصر الضريبة غير مدخل — يؤثر على فهم أساس الضريبة وتاريخ الوعاء محل الطعن."
        if basis_date_gap else ctx.get("tax_assessment_basis_date_note", "")
    )
    gov_row_data = [
        "تاريخ الحصر الضريبي",
        "آخر تاريخ حصر الضريبة / تاريخ أساس التقييم الضريبي",
        basis_date_val,
        "مُدخل يدويًا",
        "مطلوب" if basis_date_gap else "متاح",
        "نعم",
        "لا" if basis_date_gap else "نعم",
        "تاريخ صادر عن مصلحة الضرائب العقارية",
        "إدخال التاريخ" if basis_date_gap else "مراجعة الخبير",
        basis_note,
    ]
    for j, val in enumerate(gov_row_data, start=1):
        dc = ws.cell(row=row, column=j, value=val)
        dc.font      = _data_font()
        dc.alignment = _right_align()
        dc.border    = _thin_border()
        dc.fill      = _warn_fill() if basis_date_gap else _alt_fill()
    row += 1


# ── Property-class gaps sheet ─────────────────────────────────────────────────

def _sheet_property_class_review(ws, ctx: dict) -> None:
    """فجوات البيانات — property-class technical gap analysis sheet."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    cols = (6, 24, 30, 18, 18, 12, 24, 28, 24, 12)
    for col, width in zip("ABCDEFGHIJ", cols):
        ws.column_dimensions[col].width = width
    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells("A1:J1")
    c = ws["A1"]
    c.value     = "فجوات البيانات المطلوبة لاستكمال الاعتماد — Property-Class Technical Review"
    c.fill      = PatternFill("solid", fgColor="7F1D1D")
    c.font      = Font(name="Cairo", bold=True, size=12, color="FFFFFF")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    pcr = ctx.get("property_class_technical_review", {})
    gaps = pcr.get("detected_gaps", [])

    SEVERITY_COLOR = {
        "critical": "FEE2E2",
        "high":     "FEF3C7",
        "medium":   "FEF9C3",
        "low":      "F0FDF4",
    }
    SEVERITY_FONT = {
        "critical": "991B1B",
        "high":     "92400E",
        "medium":   "713F12",
        "low":      "14532D",
    }

    headers = ["م", "عنوان الفجوة", "الوصف", "الطريقة المتأثرة", "المخرج المتأثر",
               "الخطورة", "القيمة الحالية", "الإجراء المطلوب", "حالة المصدر", "جاهز؟"]
    row = 3
    _write_section_header(ws, row, "جدول الفجوات التقنية المُكتشفة", ncols=10, color="7F1D1D"); row += 1
    for i, hdr in enumerate(headers, start=1):
        hc = ws.cell(row=row, column=i, value=hdr)
        hc.fill      = PatternFill("solid", fgColor="991B1B")
        hc.font      = Font(name="Cairo", bold=True, size=9, color="FFFFFF")
        hc.alignment = _center_align()
        hc.border    = _thin_border()
    row += 1

    for gap in gaps:
        sev = gap.get("severity", "medium")
        bg  = SEVERITY_COLOR.get(sev, "FFFFFF")
        fg  = SEVERITY_FONT.get(sev, "374151")
        for j, val in enumerate([
            gap.get("issue_id", ""),
            gap.get("issue_title", ""),
            gap.get("issue_description", ""),
            gap.get("affected_method", ""),
            gap.get("affected_output", ""),
            sev,
            str(gap.get("current_value", "")),
            gap.get("corrected_value_or_required_action", ""),
            gap.get("data_source_status", ""),
            "لا" if not gap.get("production_ready") else "نعم",
        ], start=1):
            dc = ws.cell(row=row, column=j, value=val)
            dc.font      = Font(name="Cairo", size=8, color=fg)
            dc.alignment = _right_align()
            dc.border    = _thin_border()
            dc.fill      = PatternFill("solid", fgColor=bg)
        row += 1

    row += 1
    _write_section_header(ws, row, "الأدلة المطلوبة", ncols=10, color="374151"); row += 1
    for ev in pcr.get("required_evidence", []):
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=10)
        ec = ws.cell(row=row, column=1, value=f"• {ev}")
        ec.font      = _data_font()
        ec.alignment = _right_align()
        ec.fill      = _alt_fill()
        row += 1

    row += 1
    _write_section_header(ws, row, "إجراءات الخبير المطلوبة", ncols=10, color="374151"); row += 1
    for act in pcr.get("expert_required_actions", []):
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=10)
        ac = ws.cell(row=row, column=1, value=f"• {act}")
        ac.font      = _data_font()
        ac.alignment = _right_align()
        ac.fill      = _warn_fill()
        row += 1

    row += 1
    # Source readiness by method
    sr = pcr.get("source_readiness_by_method", {})
    if sr:
        _write_section_header(ws, row, "جاهزية مصادر البيانات لكل طريقة", ncols=10, color="1B2E4B"); row += 1
        sr_headers = ["الطريقة", "نوع المصدر المطلوب", "الحالة الحالية",
                      "Qdrant", "إنترنت", "OCR", "مفعل الآن"]
        for i, hdr in enumerate(sr_headers, start=1):
            hc = ws.cell(row=row, column=i, value=hdr)
            hc.fill      = PatternFill("solid", fgColor="1B2E4B")
            hc.font      = Font(name="Cairo", bold=True, size=8, color="FFFFFF")
            hc.alignment = _center_align()
            hc.border    = _thin_border()
        row += 1

        METHOD_LABELS = {
            "cost_approach":         "طريقة التكلفة",
            "market_comparison":     "طريقة المقارنة السوقية",
            "income_capitalization": "طريقة الرسملة / الدخل",
            "tax_comparison":        "طريقة المقارنة الضريبية",
            "multiple_regression":   "طريقة الانحدار المتعدد",
        }
        for mkey, mdata in sr.items():
            for j, val in enumerate([
                METHOD_LABELS.get(mkey, mkey),
                mdata.get("required_source_type", ""),
                mdata.get("current_source_status", ""),
                "نعم" if mdata.get("qdrant_ready") else "لا",
                "لا",
                "لا",
                "نعم" if mdata.get("active_now") else "لا",
            ], start=1):
                dc = ws.cell(row=row, column=j, value=val)
                dc.font      = _data_font()
                dc.alignment = _center_align() if j >= 4 else _right_align()
                dc.border    = _thin_border()
                dc.fill      = _alt_fill() if row % 2 == 0 else PatternFill("solid", fgColor="FFFFFF")
            row += 1

    row += 1
    # Production readiness note
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=10)
    nc = ws.cell(row=row, column=1,
                 value=f"حالة الجاهزية الإجمالية: {pcr.get('production_readiness_status', _EXPERT)}")
    nc.fill      = PatternFill("solid", fgColor="FEE2E2")
    nc.font      = Font(name="Cairo", bold=True, size=9, color="991B1B")
    nc.alignment = _right_align()


def _sheet_factory_cost_guidance(ws, ctx: dict) -> None:
    """مرجع تكلفة مباني المصانع — Ain Shams industrial cost reference sheet."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    for col, width in zip("ABCDEFGHIJ", (22, 20, 20, 14, 14, 14, 14, 20, 28, 24)):
        ws.column_dimensions[col].width = width
    from openpyxl.styles import Font, PatternFill, Alignment
    ws.merge_cells("A1:J1")
    c = ws["A1"]
    c.value     = "مرجع تكلفة مباني المصانع — Ain Shams Industrial Cost Reference"
    c.fill      = PatternFill("solid", fgColor="1A2E4A")
    c.font      = Font(name="Cairo", bold=True, size=12, color="FFFFFF")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    pcr = ctx.get("property_class_technical_review", {})
    fcg = pcr.get("factory_cost_guidance") or {}
    if not fcg:
        # Try direct from class-specific
        pass

    row = 3
    # Source header
    _write_section_header(ws, row, "معلومات المرجع", ncols=10, color="1A2E4A"); row += 1
    for label, key in [
        ("اسم المرجع",     "guidance_source_name"),
        ("نوع المرجع",     "guidance_source_type"),
        ("حالة المرجع",    "guidance_source_status"),
        ("فحص النظام",     "reviewed_by_system"),
        ("جاهز للإنتاج؟", "production_ready"),
    ]:
        val = fcg.get(key, _GAP)
        if isinstance(val, bool):
            val = "نعم" if val else "لا"
        _apply_row(ws, row, label, str(val)); row += 1

    row += 1
    # Source endorsement note
    note = fcg.get("guidance_official_endorsement", "")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=10)
    nc = ws.cell(row=row, column=1, value=note)
    nc.fill      = PatternFill("solid", fgColor="FEF3C7")
    nc.font      = Font(name="Cairo", italic=True, size=8, color="92400E")
    nc.alignment = _right_align()
    row += 2

    # Ain Shams cost table
    _write_section_header(ws, row, "جدول تكاليف البناء الصناعي — دراسة مبدئية", ncols=10, color="1F3A5F"); row += 1
    headers = ["البند الإنشائي", "تكلفة الهيكل/م²", "معامل التشطيب", "تكلفة التشطيب/م²",
               "الإجمالي/م²", "بعد معامل 85%", "التطبيق", "ملاحظة"]
    for i, hdr in enumerate(headers, start=1):
        hc = ws.cell(row=row, column=i, value=hdr)
        hc.fill      = PatternFill("solid", fgColor="1F3A5F")
        hc.font      = Font(name="Cairo", bold=True, size=9, color="FFFFFF")
        hc.alignment = _center_align()
        hc.border    = _thin_border()
    row += 1

    cost_cats = fcg.get("key_cost_categories", [])
    for i, cat in enumerate(cost_cats):
        fill = _alt_fill() if i % 2 == 0 else PatternFill("solid", fgColor="FFFFFF")
        for j, val in enumerate([
            cat.get("building_type_ar", ""),
            cat.get("base_cost_per_m2", ""),
            cat.get("finishing_factor", ""),
            cat.get("finishing_cost_per_m2", ""),
            cat.get("total_per_m2", ""),
            cat.get("after_85pct_safety", ""),
            cat.get("applicable_to", ""),
            "مرفق مبدئي — يحتاج مراجعة الخبير",
        ], start=1):
            dc = ws.cell(row=row, column=j, value=val)
            dc.font      = _data_font()
            dc.alignment = _center_align() if j in (2, 3, 4, 5, 6) else _right_align()
            dc.border    = _thin_border()
            dc.fill      = fill
        row += 1

    row += 1
    # Data gaps from Ain Shams doc
    _write_section_header(ws, row, "بيانات غير متوفرة في الدراسة المبدئية", ncols=10, color="991B1B"); row += 1
    for gap_item in fcg.get("recommended_depreciation_fields", []):
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=10)
        gc = ws.cell(row=row, column=1, value=f"⚠ {gap_item}")
        gc.fill      = PatternFill("solid", fgColor="FEE2E2")
        gc.font      = Font(name="Cairo", size=8, color="991B1B")
        gc.alignment = _right_align()
        row += 1

    row += 1
    # Machinery exclusion
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=10)
    mc = ws.cell(row=row, column=1, value=fcg.get("machinery_exclusion_note", ""))
    mc.fill      = PatternFill("solid", fgColor="DBEAFE")
    mc.font      = Font(name="Cairo", bold=True, size=9, color="1E3A8A")
    mc.alignment = _right_align()
    row += 1

    # Component cost map
    comp_map = fcg.get("component_cost_map", [])
    if comp_map:
        row += 1
        _write_section_header(ws, row, "مقارنة مكونات المنشأة بجدول الدراسة المبدئية", ncols=10, color="374151"); row += 1
        hdr2 = ["المكوَّن", "المساحة (م²)", "التكلفة المستخدمة", "المرجع من الدراسة", "ملاحظة الخبير"]
        for i, hdr in enumerate(hdr2, start=1):
            hc = ws.cell(row=row, column=i, value=hdr)
            hc.fill      = PatternFill("solid", fgColor="374151")
            hc.font      = Font(name="Cairo", bold=True, size=9, color="FFFFFF")
            hc.alignment = _center_align()
            hc.border    = _thin_border()
        row += 1
        for i2, comp in enumerate(comp_map):
            fill = _alt_fill() if i2 % 2 == 0 else PatternFill("solid", fgColor="FFFFFF")
            for j, val in enumerate([
                comp.get("component_name", ""),
                comp.get("component_area", ""),
                comp.get("used_unit_cost", ""),
                comp.get("ain_shams_reference", ""),
                comp.get("expert_review_note", ""),
            ], start=1):
                dc = ws.cell(row=row, column=j, value=val)
                dc.font      = _data_font()
                dc.alignment = _right_align()
                dc.border    = _thin_border()
                dc.fill      = fill
            row += 1

    row += 1
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=10)
    cc = ws.cell(row=row, column=1,
                 value=f"الاستشهاد: {fcg.get('source_citation', _GAP)}")
    cc.fill      = PatternFill("solid", fgColor="EDE9FE")
    cc.font      = Font(name="Cairo", italic=True, size=8, color="4C1D95")
    cc.alignment = _right_align()


# ── Reference intelligence sheets (Part J) ────────────────────────────────────

def _sheet_reference_registry(ws, ctx: dict) -> None:
    """Sheet: قاعدة المراجع — Internal reference database."""
    from openpyxl.styles import Font, PatternFill
    Alignment, Border, Font2, PatternFill2, Side = _style_imports()

    ws.sheet_view.rightToLeft = True
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 18
    ws.column_dimensions["E"].width = 14
    ws.column_dimensions["F"].width = 14
    ws.column_dimensions["G"].width = 22
    ws.column_dimensions["H"].width = 16

    reg = ctx.get("tax_reference_registry") or {}
    conf = reg.get("source_confidence_summary") or {}

    # Header
    ws.merge_cells("A1:H1")
    h = ws.cell(row=1, column=1, value="قاعدة المراجع الداخلية — مرجع استرشادي")
    h.font      = _hdr_font(size=12)
    h.fill      = _hdr_fill("1B2E4B")
    h.alignment = _center_align()

    row = 2
    _apply_row(ws, row, "إجمالي المراجع", conf.get("total_references", 0)); row += 1
    _apply_row(ws, row, "محاكاة QA", conf.get("qa_simulation_count", 0)); row += 1
    _apply_row(ws, row, "جاهز للإنتاج", conf.get("production_ready_count", 0)); row += 1
    _apply_row(ws, row, "مطلوب استكمال", conf.get("missing_count", 0)); row += 1
    _apply_row(ws, row, "حالة الثقة الإجمالية", conf.get("overall_confidence", _GAP)); row += 1
    _apply_row(ws, row, "Qdrant مفعل؟", "لا — مرحلة مستقبلية"); row += 1
    _apply_row(ws, row, "الإنترنت مفعل؟", "لا"); row += 1
    _apply_row(ws, row, "OCR مفعل؟", "لا"); row += 1
    row += 1

    # Helper to write a reference table
    def _write_ref_table(title: str, refs: list, cols: list[tuple]) -> None:
        nonlocal row
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=len(cols))
        th = ws.cell(row=row, column=1, value=title)
        th.font  = _hdr_font(size=10)
        th.fill  = _hdr_fill("1F4E78")
        th.alignment = _center_align()
        row += 1
        for ci, (hdr, _) in enumerate(cols, 1):
            c = ws.cell(row=row, column=ci, value=hdr)
            c.font = _hdr_font(size=9, color="FFFFFF")
            c.fill = _hdr_fill("374151")
            c.alignment = _center_align()
        row += 1
        if not refs:
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=len(cols))
            nc = ws.cell(row=row, column=1, value=_EXPERT)
            nc.font = Font(name="Cairo", italic=True, size=8, color="6B7280")
            nc.alignment = _center_align()
            row += 1
        else:
            for ri, ref in enumerate(refs):
                fill = _alt_fill() if ri % 2 == 0 else PatternFill("solid", fgColor="FFFFFF")
                for ci, (_, key) in enumerate(cols, 1):
                    val = ref.get(key)
                    if isinstance(val, list):
                        val = ", ".join(str(v) for v in val) if val else _GAP
                    if val is None:
                        val = _GAP
                    c = ws.cell(row=row, column=ci, value=val)
                    c.fill = fill
                    c.font = _data_font(size=8)
                    c.alignment = _right_align()
                    if isinstance(val, float) and key in ("value", "monthly_rent", "annual_rent", "land_price_per_m2"):
                        c.number_format = _FMT_CURRENCY
                    if isinstance(val, float) and key == "confidence_score":
                        c.number_format = _FMT_PCT
                row += 1
        row += 1

    rent_cols = [
        ("رقم المرجع", "reference_id"), ("التصنيف", "reference_type"),
        ("المنطقة", "district"), ("الفئة", "property_class"),
        ("الإيجار الشهري", "monthly_rent"), ("الإيجار السنوي", "annual_rent"),
        ("الثقة", "confidence_score"), ("الحالة", "source_status"),
    ]
    txn_cols = [
        ("رقم المرجع", "reference_id"), ("التصنيف", "reference_type"),
        ("المنطقة", "district"), ("المساحة م²", "area"),
        ("القيمة", "value"), ("السعر/م²", "price_per_m2"),
        ("الثقة", "confidence_score"), ("الحالة", "source_status"),
    ]
    land_cols = [
        ("رقم المرجع", "reference_id"), ("المنطقة", "district"),
        ("سعر الأرض/م²", "land_price_per_m2"), ("الفئة", "property_class"),
        ("الثقة", "confidence_score"), ("الحالة", "source_status"),
        ("ملاحظات", "notes"),
    ]
    adj_cols = [
        ("رقم المرجع", "reference_id"), ("نوع المعامل", "adjustment_factor_type"),
        ("قيمة المعامل", "adjustment_factor_value"), ("المنهجية", "used_in_methods"),
        ("الثقة", "confidence_score"), ("الحالة", "source_status"),
    ]

    _write_ref_table("أ. مراجع القيم الإيجارية", reg.get("rental_references", []), rent_cols)
    _write_ref_table("ب. مراجع المعاملات السوقية", reg.get("transaction_references", []), txn_cols)
    _write_ref_table("ج. مراجع أسعار الأراضي", reg.get("land_price_references", []), land_cols)
    _write_ref_table("د. مراجع معاملات التعديل", reg.get("adjustment_factor_references", []), adj_cols)

    # Disclaimer
    row += 1
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=8)
    dc = ws.cell(row=row, column=1, value="لا تصلح بيانات محاكاة QA كدليل رسمي — يحتاج استبدالها بمراجع موثقة قبل التقديم")
    dc.font = Font(name="Cairo", italic=True, size=8, color="7F1D1D")
    dc.alignment = _center_align()


def _sheet_depreciation_model(ws, ctx: dict) -> None:
    """Sheet: نموذج الإهلاك — Unified depreciation model."""
    from openpyxl.styles import Font, PatternFill
    ws.sheet_view.rightToLeft = True
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 22
    ws.column_dimensions["C"].width = 14
    ws.column_dimensions["D"].width = 14
    ws.column_dimensions["E"].width = 14
    ws.column_dimensions["F"].width = 14
    ws.column_dimensions["G"].width = 24

    udm = ctx.get("unified_depreciation_model") or {}

    ws.merge_cells("A1:G1")
    h = ws.cell(row=1, column=1, value="نموذج الإهلاك الموحد — استرشادي")
    h.font = _hdr_font(size=12); h.fill = _hdr_fill("1A4D2E"); h.alignment = _center_align()

    row = 2
    _apply_row(ws, row, "فئة العقار", udm.get("class_label_ar", _GAP)); row += 1
    _apply_row(ws, row, "نوع العقار الفرعي", udm.get("property_subtype", _GAP)); row += 1
    _apply_row(ws, row, "مفتاح الإهلاك", udm.get("depreciation_key", _GAP)); row += 1

    age_val = udm.get("effective_age_years")
    age_disp = str(age_val) + " سنة" if age_val is not None else _GAP
    _apply_row(ws, row, "العمر الفعلي", age_disp); row += 1

    if udm.get("effective_age_missing"):
        ws.cell(row=row - 1, column=2).fill = _warn_fill()

    eco_life = udm.get("economic_life_years")
    _apply_row(ws, row, "العمر الاقتصادي (سنة)", f"={eco_life}" if eco_life else _GAP, is_formula=bool(eco_life)); row += 1

    ann_rate = udm.get("annual_depreciation_rate")
    _apply_row(ws, row, "معدل الإهلاك السنوي", ann_rate, number_format=_FMT_PCT); row += 1

    acc_rate = udm.get("accumulated_depreciation_rate")
    acc_disp = acc_rate if acc_rate is not None else "يحتاج تحديد العمر الفعلي"
    _apply_row(ws, row, "معدل الإهلاك المتراكم", acc_disp, number_format=_FMT_PCT if isinstance(acc_disp, float) else ""); row += 1

    _apply_row(ws, row, "الحد الأقصى للإهلاك", udm.get("max_allowed_accumulated", 0.80), number_format=_FMT_PCT); row += 1
    _apply_row(ws, row, "المنهجية", udm.get("depreciation_method", _GAP)); row += 1
    _apply_row(ws, row, "حالة المصدر", udm.get("depreciation_source_status", _GAP)); row += 1
    _apply_row(ws, row, "تجاوز الخبير مسموح؟", "نعم"); row += 1
    _apply_row(ws, row, "تجاوز الخبير مُطبَّق؟", "نعم" if udm.get("expert_override_applied") else "لا"); row += 1
    if udm.get("expert_override_reason"):
        _apply_row(ws, row, "سبب التجاوز", udm.get("expert_override_reason")); row += 1
    if udm.get("ain_shams_guidance_note"):
        _apply_row(ws, row, "ملاحظة عين شمس", udm.get("ain_shams_guidance_note")); row += 1

    row += 1
    # Reference table: all classes
    headers = ["فئة العقار", "العمر الاقتصادي", "المعدل السنوي", "الحد الأقصى", "المنهجية", "المصدر"]
    for ci, hdr in enumerate(headers, 1):
        c = ws.cell(row=row, column=ci, value=hdr)
        c.font = _hdr_font(size=9); c.fill = _hdr_fill("374151"); c.alignment = _center_align()
    row += 1

    dep_table = [
        ("عقار سكني", 60, "1/60 ≈ 1.667%", "80%", "خط مستقيم", "ممارسة مهنية"),
        ("عقار غير سكني", 50, "2.00%", "80%", "خط مستقيم", "ممارسة مهنية"),
        ("منشأة صناعية / مصنع", 30, "1/30 ≈ 3.333%", "85%", "خط مستقيم", "ممارسة مهنية — يحتاج مراجعة"),
        ("مخزن / بدروم", 50, "2.00%", "80%", "خط مستقيم", "ممارسة مهنية"),
    ]
    for ri, (cls, eco, rate, mx, mth, src) in enumerate(dep_table):
        fill = _alt_fill() if ri % 2 == 0 else PatternFill("solid", fgColor="FFFFFF")
        for ci, val in enumerate([cls, eco, rate, mx, mth, src], 1):
            c = ws.cell(row=row, column=ci, value=val)
            c.fill = fill; c.font = _data_font(size=8); c.alignment = _center_align()
        row += 1

    if udm.get("effective_age_missing"):
        row += 1
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
        wc = ws.cell(row=row, column=1, value="⚠ " + udm.get("effective_age_gap_note", "العمر الفعلي غير مُقدَّم"))
        wc.fill = _warn_fill()
        wc.font = Font(name="Cairo", bold=True, size=9, color="7F1D1D")
        wc.alignment = _center_align()


def _sheet_tax_sensitivity(ws, ctx: dict) -> None:
    """Sheet: حساسية الضريبة — Detailed tax sensitivity analysis."""
    from openpyxl.styles import Font, PatternFill
    ws.sheet_view.rightToLeft = True
    ws.column_dimensions["A"].width = 24
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 18
    ws.column_dimensions["E"].width = 18
    ws.column_dimensions["F"].width = 24

    tsd = ctx.get("tax_sensitivity_detailed") or {}

    ws.merge_cells("A1:F1")
    h = ws.cell(row=1, column=1, value="تحليل الحساسية للضريبة — استرشادي")
    h.font = _hdr_font(size=12); h.fill = _hdr_fill("1E40AF"); h.alignment = _center_align()

    row = 2
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    disc = ws.cell(row=row, column=1, value=tsd.get("sensitivity_disclaimer", ""))
    disc.font = Font(name="Cairo", italic=True, size=8, color="7F1D1D"); disc.alignment = _center_align()
    row += 2

    # Rental sensitivity table
    rent_rows = tsd.get("rental_value_sensitivity") or []
    if rent_rows:
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
        th = ws.cell(row=row, column=1, value="أ. حساسية القيمة الإيجارية السنوية")
        th.font = _hdr_font(size=10); th.fill = _hdr_fill("1F4E78"); th.alignment = _center_align()
        row += 1
        hdrs = ["السيناريو", "الإيجار السنوي", "الوعاء الخاضع", "الضريبة الاسترشادية", "التوفير المتوقع", "ملاحظات"]
        for ci, hdr in enumerate(hdrs, 1):
            c = ws.cell(row=row, column=ci, value=hdr)
            c.font = _hdr_font(size=9); c.fill = _hdr_fill("374151"); c.alignment = _center_align()
        row += 1
        for ri, r in enumerate(rent_rows):
            fill = _alt_fill() if ri % 2 == 0 else PatternFill("solid", fgColor="FFFFFF")
            for ci, (key, fmt) in enumerate([
                ("scenario", ""), ("annual_rental_value", _FMT_CURRENCY),
                ("taxable_basis", _FMT_CURRENCY), ("indicative_tax", _FMT_CURRENCY),
                ("expected_saving", _FMT_CURRENCY), ("notes", ""),
            ], 1):
                val = r.get(key)
                if val is None: val = _GAP
                c = ws.cell(row=row, column=ci, value=val)
                c.fill = fill; c.font = _data_font(size=8); c.alignment = _center_align()
                if fmt and isinstance(val, (int, float)): c.number_format = fmt
            row += 1
        row += 1

    # Cap rate sensitivity
    cap_rows = tsd.get("cap_rate_sensitivity") or []
    if cap_rows:
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        th2 = ws.cell(row=row, column=1, value="ب. حساسية معدل الرسملة")
        th2.font = _hdr_font(size=10); th2.fill = _hdr_fill("1F4E78"); th2.alignment = _center_align()
        row += 1
        for ci, hdr in enumerate(["معدل الرسملة", "القيمة الاسترشادية", "", "ملاحظات"], 1):
            c = ws.cell(row=row, column=ci, value=hdr)
            c.font = _hdr_font(size=9); c.fill = _hdr_fill("374151"); c.alignment = _center_align()
        row += 1
        for ri, r in enumerate(cap_rows):
            fill = _alt_fill() if ri % 2 == 0 else PatternFill("solid", fgColor="FFFFFF")
            for ci, (key, fmt) in enumerate([("cap_rate", _FMT_PCT), ("indicated_value", _FMT_CURRENCY), ("", ""), ("notes", "")], 1):
                val = r.get(key) if key else ""
                if val is None: val = _GAP
                c = ws.cell(row=row, column=ci, value=val)
                c.fill = fill; c.font = _data_font(size=8); c.alignment = _center_align()
                if fmt and isinstance(val, (int, float)): c.number_format = fmt
            row += 1
        row += 1

    # Depreciation sensitivity
    dep_rows = tsd.get("depreciation_sensitivity") or []
    if dep_rows:
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        th3 = ws.cell(row=row, column=1, value="ج. حساسية معدل الإهلاك")
        th3.font = _hdr_font(size=10); th3.fill = _hdr_fill("1F4E78"); th3.alignment = _center_align()
        row += 1
        for ci, hdr in enumerate(["معدل الإهلاك", "الإهلاك المتراكم", "صافي قيمة المبنى", "ملاحظات"], 1):
            c = ws.cell(row=row, column=ci, value=hdr)
            c.font = _hdr_font(size=9); c.fill = _hdr_fill("374151"); c.alignment = _center_align()
        row += 1
        for ri, r in enumerate(dep_rows):
            fill = _alt_fill() if ri % 2 == 0 else PatternFill("solid", fgColor="FFFFFF")
            for ci, (key, fmt) in enumerate([
                ("depreciation_rate", _FMT_PCT), ("accumulated_dep", _FMT_PCT),
                ("net_building_value", _FMT_CURRENCY), ("notes", ""),
            ], 1):
                val = r.get(key)
                if val is None: val = _GAP
                c = ws.cell(row=row, column=ci, value=val)
                c.fill = fill; c.font = _data_font(size=8); c.alignment = _center_align()
                if fmt and isinstance(val, (int, float)): c.number_format = fmt
            row += 1


def _sheet_appeal_risk(ws, ctx: dict) -> None:
    """Sheet: مخاطر الطعن — Appeal risk assessment."""
    from openpyxl.styles import Font, PatternFill
    ws.sheet_view.rightToLeft = True
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 40

    ara = ctx.get("appeal_risk_assessment") or {}

    ws.merge_cells("A1:C1")
    h = ws.cell(row=1, column=1, value="تقييم مخاطر الطعن — مؤشر فني استرشادي")
    h.font = _hdr_font(size=12); h.fill = _hdr_fill("7F1D1D"); h.alignment = _center_align()

    risk_level = ara.get("overall_risk_level", _GAP)
    risk_colors = {"منخفض": "1A4D2E", "متوسط": "92400E", "مرتفع": "7F1D1D"}
    risk_color = risk_colors.get(risk_level, "374151")

    row = 2
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
    rc = ws.cell(row=row, column=1, value=f"مستوى المخاطرة: {risk_level}")
    rc.font = Font(name="Cairo", bold=True, size=14, color="FFFFFF")
    rc.fill = PatternFill("solid", fgColor=risk_color)
    rc.alignment = _center_align()
    row += 1

    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
    pl = ws.cell(row=row, column=1, value=ara.get("acceptance_probability_label", ""))
    pl.font = Font(name="Cairo", italic=True, size=9, color="1A1A2E"); pl.alignment = _center_align()
    row += 2

    # Score breakdown
    scores = [
        ("قوة الأدلة", "evidence_strength_score"),
        ("جودة المقارنات", "comparable_quality_score"),
        ("دعم الإهلاك", "depreciation_support_score"),
        ("موثوقية المصادر", "source_reliability_score"),
        ("اكتمال المستندات", "document_completeness_score"),
        ("خطر المهلة", "deadline_risk_score"),
        ("المجموع الموزون", "overall_risk_score"),
    ]
    ws.cell(row=row, column=1, value="مكون التقييم").font = _hdr_font(size=9)
    ws.cell(row=row, column=1).fill = _hdr_fill("374151")
    ws.cell(row=row, column=2, value="الدرجة (0-100)").font = _hdr_font(size=9)
    ws.cell(row=row, column=2).fill = _hdr_fill("374151")
    row += 1
    for ri, (label, key) in enumerate(scores):
        val = ara.get(key, 0)
        fill = _alt_fill() if ri % 2 == 0 else PatternFill("solid", fgColor="FFFFFF")
        c1 = ws.cell(row=row, column=1, value=label)
        c2 = ws.cell(row=row, column=2, value=val)
        c1.fill = c2.fill = fill
        c1.font = _data_font(bold=(key == "overall_risk_score"))
        c2.font = _data_font(bold=(key == "overall_risk_score"))
        c1.alignment = _right_align(); c2.alignment = _center_align()
        row += 1
    row += 1

    # Key risks
    risks = ara.get("key_risks") or []
    if risks:
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
        ws.cell(row=row, column=1, value="مخاطر رئيسية مُحددة").font = _hdr_font(size=10)
        ws.cell(row=row, column=1).fill = _hdr_fill("7F1D1D")
        ws.cell(row=row, column=1).alignment = _center_align()
        row += 1
        for r_text in risks:
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
            rc2 = ws.cell(row=row, column=1, value="• " + r_text)
            rc2.fill = _warn_fill(); rc2.font = _data_font(size=8, color="7F1D1D"); rc2.alignment = _right_align()
            row += 1
        row += 1

    # Recommended actions
    actions = ara.get("recommended_actions") or []
    if actions:
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
        ws.cell(row=row, column=1, value="الإجراءات الموصى بها").font = _hdr_font(size=10)
        ws.cell(row=row, column=1).fill = _hdr_fill("1A4D2E")
        ws.cell(row=row, column=1).alignment = _center_align()
        row += 1
        for act in actions:
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
            ac = ws.cell(row=row, column=1, value="✓ " + act)
            ac.fill = PatternFill("solid", fgColor="F0FDF4")
            ac.font = _data_font(size=8, color="1A4D2E"); ac.alignment = _right_align()
            row += 1
        row += 1

    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
    disc = ws.cell(row=row, column=1, value=ara.get("risk_disclaimer", ""))
    disc.font = Font(name="Cairo", italic=True, size=8, color="6B7280"); disc.alignment = _center_align()


def _sheet_prior_reports(ws, ctx: dict) -> None:
    """Sheet: تقارير سابقة مرتبطة — Prior valuation report links."""
    from openpyxl.styles import Font, PatternFill
    ws.sheet_view.rightToLeft = True
    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 14
    ws.column_dimensions["D"].width = 14
    ws.column_dimensions["E"].width = 16
    ws.column_dimensions["F"].width = 16
    ws.column_dimensions["G"].width = 30
    ws.column_dimensions["H"].width = 16

    links = ctx.get("prior_report_links") or []

    ws.merge_cells("A1:H1")
    h = ws.cell(row=1, column=1, value="التقارير السابقة المرتبطة — مرجع داعم")
    h.font = _hdr_font(size=12); h.fill = _hdr_fill("3B1F6B"); h.alignment = _center_align()

    row = 2
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=8)
    note = ws.cell(row=row, column=1, value=(
        "التقارير السابقة تُستخدم كمراجع داعمة فقط — ليست بديلًا عن تقييم ضريبي رسمي"
    ))
    note.font = Font(name="Cairo", italic=True, size=8, color="7F1D1D"); note.alignment = _center_align()
    row += 2

    hdrs = ["رقم التقرير", "نوع التقرير", "تاريخ التقرير", "المنطقة",
            "القيمة/الإيجار", "السعر/م²", "القيود", "مراجعة الخبير"]
    for ci, hdr in enumerate(hdrs, 1):
        c = ws.cell(row=row, column=ci, value=hdr)
        c.font = _hdr_font(size=9); c.fill = _hdr_fill("3B1F6B"); c.alignment = _center_align()
    row += 1

    if not links:
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=8)
        nc = ws.cell(row=row, column=1, value="لا توجد تقارير سابقة مُرتبطة — يمكن إضافتها عند الاستكمال")
        nc.font = Font(name="Cairo", italic=True, size=8, color="6B7280"); nc.alignment = _center_align()
    else:
        for ri, link in enumerate(links):
            fill = _alt_fill() if ri % 2 == 0 else PatternFill("solid", fgColor="FFFFFF")
            val_disp = link.get("indicated_market_value") or link.get("indicated_rental_value") or _GAP
            cols = [
                link.get("linked_report_id", _GAP),
                link.get("report_type", _GAP),
                link.get("report_date", _GAP),
                link.get("district", _GAP),
                val_disp,
                link.get("value_per_m2") or link.get("rent_per_m2") or _GAP,
                link.get("limitations", _GAP),
                "مطلوب" if link.get("expert_review_required") else "لا",
            ]
            for ci, val in enumerate(cols, 1):
                c = ws.cell(row=row, column=ci, value=val)
                c.fill = fill; c.font = _data_font(size=8); c.alignment = _right_align()
                if isinstance(val, float) and ci in (5, 6): c.number_format = _FMT_CURRENCY
            row += 1


def _sheet_reference_versioning(ws, ctx: dict) -> None:
    """Sheet: إصدارات المراجع — Reference versioning and confidence tracking."""
    from openpyxl.styles import Font
    ws.sheet_view.rightToLeft = True
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 28

    reg = ctx.get("tax_reference_registry") or {}
    ver = reg.get("reference_versioning") or {}

    ws.merge_cells("A1:B1")
    h = ws.cell(row=1, column=1, value="إصدارات المراجع وتتبع الثقة")
    h.font = _hdr_font(size=12); h.fill = _hdr_fill("1A2E4A"); h.alignment = _center_align()

    row = 2
    fields = [
        ("رقم إصدار المرجع",    "reference_version_id"),
        ("تاريخ الإنشاء",       "created_at"),
        ("تاريخ آخر تحديث",     "updated_at"),
        ("تاريخ لقطة المصدر",   "source_snapshot_date"),
        ("الفترة المنطبقة",     "applicable_period"),
        ("الإصدار",             "reference_version"),
        ("درجة الثقة",          "confidence_score"),
        ("جودة الأدلة",         "evidence_quality"),
        ("حالة المراجعة",       "review_status"),
        ("ملاحظات",             "notes"),
    ]
    for label, key in fields:
        val = ver.get(key, _GAP)
        _apply_row(ws, row, label, val,
                   number_format=_FMT_PCT if key == "confidence_score" and isinstance(val, float) else "")
        row += 1

    row += 1
    # Registry status
    rs = reg.get("registry_status") or {}
    _apply_row(ws, row, "Qdrant مُعد؟", "نعم" if rs.get("qdrant_ready") else "لا"); row += 1
    _apply_row(ws, row, "Qdrant مفعل؟", "لا — مرحلة مستقبلية"); row += 1
    _apply_row(ws, row, "الإنترنت مفعل؟", "لا"); row += 1
    _apply_row(ws, row, "OCR مفعل؟", "لا"); row += 1
    _apply_row(ws, row, "حالة السجل", rs.get("status_ar", _GAP)); row += 1
    _apply_row(ws, row, "إصدار السجل", rs.get("version", _GAP)); row += 1

    row += 1
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
    disc = ws.cell(row=row, column=1,
                   value="يتتبع هذا السجل تغييرات قيم المراجع الداخلية عبر الزمن لضمان الاتساق وإمكانية التدقيق")
    disc.font = Font(name="Cairo", italic=True, size=8, color="6B7280"); disc.alignment = _center_align()


# ── ws33–ws45: Compliance, disclosure, methodology & specialized sheets ───────

def _sheet_scope_of_work(ws, ctx: dict) -> None:
    """ws33: نطاق العمل — scope of work declaration."""
    ws.sheet_view.rightToLeft = True
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 35
    data = (ctx.get("five_method_tax_context") or {}).get("scope_of_work") or {}

    ws.merge_cells("A1:B1")
    h = ws.cell(row=1, column=1, value="نطاق العمل")
    h.font = _hdr_font(size=12); h.fill = _hdr_fill("1F4E78"); h.alignment = _center_align()

    row = 2
    fields = [
        ("الاستخدام المقصود",           "intended_use"),
        ("المستخدمون المقصودون",         "intended_users"),
        ("حصة الملكية",                  "property_interest"),
        ("تاريخ السريان",                "effective_date"),
        ("تاريخ المعاينة",               "inspection_date"),
        ("طرق التقييم",                  "valuation_methods"),
        ("المستندات المراجعة",           "documents_reviewed"),
        ("حالة النطاق",                  "scope_status"),
    ]
    for label, key in fields:
        raw = data.get(key, _GAP)
        if isinstance(raw, list):
            raw = " | ".join(str(x) for x in raw) if raw else _GAP
        _apply_row(ws, row, label, raw)
        row += 1
    # Add assessment basis date from root context
    _apply_row(ws, row, "آخر تاريخ حصر الضريبة / تاريخ أساس التقييم الضريبي",
               ctx.get("tax_assessment_basis_date")); row += 1


def _sheet_compliance_readiness(ws, ctx: dict) -> None:
    """ws34: بيان الامتثال — professional compliance readiness."""
    ws.sheet_view.rightToLeft = True
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 35
    data = (ctx.get("five_method_tax_context") or {}).get("professional_compliance_readiness") or {}

    ws.merge_cells("A1:B1")
    h = ws.cell(row=1, column=1, value="بيان الامتثال المهني")
    h.font = _hdr_font(size=12); h.fill = _hdr_fill("3B1F6B"); h.alignment = _center_align()

    row = 2
    standards = [
        ("IVS 2025",            "ivs_2025"),
        ("USPAP",               "uspap"),
        ("RICS Red Book 2025",  "rics_red_book_2025"),
        ("FRA / المعايير المصرية", "fra_egyptian"),
        ("IFRS 13",             "ifrs_13"),
    ]
    for std_label, std_key in standards:
        std_data = data.get(std_key) or {}
        _write_section_header(ws, row, f"المعيار: {std_label}", ncols=2, color="3B1F6B")
        row += 1
        for field_label, field_key in [
            ("حالة الجاهزية",      "readiness_status"),
            ("ادعاء الامتثال",     "compliance_claim"),
        ]:
            _apply_row(ws, row, field_label, std_data.get(field_key, _GAP))
            row += 1
        # Emit remaining keys (skip those already shown)
        skip_keys = {"readiness_status", "compliance_claim"}
        for k, v in std_data.items():
            if k in skip_keys:
                continue
            if isinstance(v, (dict, list)):
                continue
            _apply_row(ws, row, k, v if v not in (None, "") else _GAP)
            row += 1
        row += 1


def _sheet_dcf(ws, ctx: dict) -> None:
    """ws35: DCF إن وجد — discounted cash-flow (if applicable)."""
    ws.sheet_view.rightToLeft = True
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 35
    five = ctx.get("five_method_tax_context") or {}
    income = five.get("income_capitalization") or five.get("income_approach") or {}

    ws.merge_cells("A1:B1")
    h = ws.cell(row=1, column=1, value="DCF إن وجد — نهج الدخل")
    h.font = _hdr_font(size=12); h.fill = _hdr_fill("1F4E78"); h.alignment = _center_align()

    row = 2
    dcf_applicable = income.get("dcf_applicable", False)
    _apply_row(ws, row, "نوع طريقة الدخل",    income.get("income_method_type", _GAP)); row += 1
    _apply_row(ws, row, "DCF قابل للتطبيق؟",  "نعم" if dcf_applicable else "غير مطبق"); row += 1

    if not dcf_applicable:
        _apply_row(ws, row, "ملاحظة", "التحليل بالتدفق النقدي المخصوم غير مطبق لهذا العقار"); row += 1
    else:
        # DCF table
        dcf_table = income.get("dcf_table") or {}
        if dcf_table:
            _write_section_header(ws, row, "جدول DCF", ncols=2, color="1F4E78"); row += 1
            for k, v in dcf_table.items():
                if isinstance(v, (dict, list)):
                    continue
                _apply_row(ws, row, k, v if v not in (None, "") else _GAP); row += 1

    # Direct capitalisation table
    dc_table = income.get("direct_capitalization_table") or {}
    if dc_table:
        _write_section_header(ws, row, "الرسملة المباشرة", ncols=2, color="1F4E78"); row += 1
        for k, v in dc_table.items():
            if isinstance(v, (dict, list)):
                continue
            _apply_row(ws, row, k, v if v not in (None, "") else _GAP); row += 1


def _sheet_quality_control(ws, ctx: dict) -> None:
    """ws36: مراجعة الجودة — quality control checklist."""
    ws.sheet_view.rightToLeft = True
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 35
    data = (ctx.get("five_method_tax_context") or {}).get("quality_control_checklist") or {}

    ws.merge_cells("A1:B1")
    h = ws.cell(row=1, column=1, value="مراجعة الجودة")
    h.font = _hdr_font(size=12); h.fill = _hdr_fill("1B4332"); h.alignment = _center_align()

    row = 2
    _apply_row(ws, row, "الحالة الإجمالية", data.get("overall_status", _GAP)); row += 1

    checklist = data.get("checklist") or []
    if checklist:
        _write_section_header(ws, row, "قائمة التحقق", ncols=2, color="1B4332"); row += 1
        for item in checklist:
            if isinstance(item, dict):
                label  = item.get("label", _GAP)
                status = item.get("status", _GAP)
            else:
                label  = str(item)
                status = _GAP
            _apply_row(ws, row, label, status); row += 1


def _sheet_expert_signature(ws, ctx: dict) -> None:
    """ws37: توقيع واعتماد الخبير — expert certification & signature."""
    ws.sheet_view.rightToLeft = True
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 35
    data = ((ctx.get("five_method_tax_context") or {})
            .get("professional_compliance_readiness") or {}).get("uspap") or {}

    ws.merge_cells("A1:B1")
    h = ws.cell(row=1, column=1, value="توقيع واعتماد الخبير")
    h.font = _hdr_font(size=12); h.fill = _hdr_fill("1A2E4A"); h.alignment = _center_align()

    row = 2
    fields = [
        ("اسم المقيّم",                      "appraiser_name"),
        ("المؤهل / الاعتماد",                "credential"),
        ("تاريخ التوقيع",                    "signature_date"),
        ("الإفصاح عن المساعدة الجوهرية",    "significant_assistance_disclosure"),
        ("تحذير الاستخدام المقيّد",          "restricted_use_warning"),
    ]
    for label, key in fields:
        _apply_row(ws, row, label, data.get(key, _GAP)); row += 1

    row += 1
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
    from openpyxl.styles import Font
    note = ws.cell(row=row, column=1, value="مخصص لتوقيع الخبير المعتمد واعتماد التقرير رسمياً")
    note.font = Font(name="Cairo", italic=True, size=8, color="6B7280")
    note.alignment = _center_align()


def _sheet_esg_climate(ws, ctx: dict) -> None:
    """ws38: ESG والمخاطر المناخية — ESG and climate risk assessment."""
    ws.sheet_view.rightToLeft = True
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 35
    data = (ctx.get("five_method_tax_context") or {}).get("esg_climate_risk_assessment") or {}

    ws.merge_cells("A1:B1")
    h = ws.cell(row=1, column=1, value="ESG والمخاطر المناخية")
    h.font = _hdr_font(size=12); h.fill = _hdr_fill("1A4D2E"); h.alignment = _center_align()

    row = 2
    _apply_row(ws, row, "ملاحظة التقييم",    data.get("assessment_note", _GAP)); row += 1
    _apply_row(ws, row, "جاهز للإنتاج؟",    "نعم" if data.get("production_ready") else "لا"); row += 1

    risk = data.get("risk_factors") or {}
    if risk:
        _write_section_header(ws, row, "عوامل المخاطر", ncols=2, color="1A4D2E"); row += 1
        risk_fields = [
            ("خطر الفيضانات",                 "flood_risk"),
            ("خطر موجات الحرارة",              "heat_stress_risk"),
            ("تأثير التأمين",                  "insurance_impact"),
            ("امتثال المبنى الأخضر",           "green_building_compliance_status"),
            ("مصدر درجة ESG",                  "esg_score_source"),
        ]
        for label, key in risk_fields:
            _apply_row(ws, row, label, risk.get(key, _GAP)); row += 1


def _sheet_legal_due_diligence(ws, ctx: dict) -> None:
    """ws39: الفحص القانوني والمستندي — legal and document due diligence."""
    ws.sheet_view.rightToLeft = True
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 35
    data = (ctx.get("five_method_tax_context") or {}).get("legal_due_diligence_readiness") or {}

    ws.merge_cells("A1:B1")
    h = ws.cell(row=1, column=1, value="الفحص القانوني والمستندي")
    h.font = _hdr_font(size=12); h.fill = _hdr_fill("7F1D1D"); h.alignment = _center_align()

    row = 2
    _apply_row(ws, row, "الحالة الإجمالية", data.get("overall_status", _GAP)); row += 1
    _apply_row(ws, row, "إخلاء مسؤولية",   data.get("disclaimer", _GAP)); row += 1

    checklist = data.get("checklist") or []
    if checklist:
        _write_section_header(ws, row, "قائمة التحقق القانوني", ncols=2, color="7F1D1D"); row += 1
        for item in checklist:
            if isinstance(item, dict):
                label  = item.get("label", _GAP)
                status = item.get("status", _GAP)
            else:
                label  = str(item)
                status = _GAP
            _apply_row(ws, row, label, status); row += 1


def _sheet_peer_review(ws, ctx: dict) -> None:
    """ws40: مراجعة النظراء — peer review readiness."""
    ws.sheet_view.rightToLeft = True
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 35
    data = (ctx.get("five_method_tax_context") or {}).get("peer_review_readiness") or {}

    ws.merge_cells("A1:B1")
    h = ws.cell(row=1, column=1, value="مراجعة النظراء")
    h.font = _hdr_font(size=12); h.fill = _hdr_fill("3B1F6B"); h.alignment = _center_align()

    row = 2
    _apply_row(ws, row, "مراجعة النظراء مكتملة؟",
               "نعم" if data.get("peer_review_completed") else "لا"); row += 1

    # USPAP appraisal review sub-section
    uspap_rev = data.get("uspap_appraisal_review") or {}
    if uspap_rev:
        _write_section_header(ws, row, "مراجعة USPAP", ncols=2, color="3B1F6B"); row += 1
        for k, v in uspap_rev.items():
            if not isinstance(v, (dict, list)):
                _apply_row(ws, row, k, v if v not in (None, "") else _GAP); row += 1

    # RICS review sub-section
    rics_rev = data.get("rics_review") or {}
    if rics_rev:
        _write_section_header(ws, row, "مراجعة RICS", ncols=2, color="3B1F6B"); row += 1
        for k, v in rics_rev.items():
            if not isinstance(v, (dict, list)):
                _apply_row(ws, row, k, v if v not in (None, "") else _GAP); row += 1

    _apply_row(ws, row, "مخصص توقيع المراجع",
               data.get("reviewer_signature_placeholder", _GAP)); row += 1


def _sheet_document_matrix(ws, ctx: dict) -> None:
    """ws41: مصفوفة المستندات — document requirements matrix."""
    ws.sheet_view.rightToLeft = True
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 35
    data = (ctx.get("five_method_tax_context") or {}).get("document_requirements_matrix") or {}

    ws.merge_cells("A1:B1")
    h = ws.cell(row=1, column=1, value="مصفوفة متطلبات المستندات")
    h.font = _hdr_font(size=12); h.fill = _hdr_fill("374151"); h.alignment = _center_align()

    row = 2
    _apply_row(ws, row, "ملاحظة المصفوفة", data.get("matrix_note", _GAP)); row += 1

    items = data.get("items") or []
    if items:
        _write_section_header(ws, row, "قائمة المستندات", ncols=2, color="374151"); row += 1
        for item in items:
            if not isinstance(item, dict):
                continue
            label = item.get("label", _GAP)
            level = item.get("level", _GAP)
            affects_sub = "نعم" if item.get("affects_submission") else "لا"
            affects_val = "نعم" if item.get("affects_valuation") else "لا"
            affects_ddl = "نعم" if item.get("affects_deadline") else "لا"
            _apply_row(ws, row, label,
                       f"المستوى: {level} | التقديم: {affects_sub} | التقييم: {affects_val} | الموعد: {affects_ddl}")
            row += 1


def _sheet_tax_basis_vs_value(ws, ctx: dict) -> None:
    """ws42: أساس الضريبة والقيمة السوقية — tax basis vs market value explanation."""
    ws.sheet_view.rightToLeft = True
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 35
    data = (ctx.get("five_method_tax_context") or {}).get("tax_basis_explanation") or {}

    ws.merge_cells("A1:B1")
    h = ws.cell(row=1, column=1, value="أساس الضريبة والقيمة السوقية")
    h.font = _hdr_font(size=12); h.fill = _hdr_fill("7B2D00"); h.alignment = _center_align()

    row = 2
    _apply_row(ws, row, "ملاحظة التمييز", data.get("distinction_note", _GAP)); row += 1
    _apply_row(ws, row, "آخر تاريخ حصر الضريبة / تاريخ أساس التقييم الضريبي",
               ctx.get("tax_assessment_basis_date")); row += 1
    _apply_row(ws, row, "ملاحظة أساس التقييم",
               ctx.get("tax_assessment_basis_date_note")); row += 1
    row += 1

    # Annual tax section
    annual = data.get("annual_tax") or {}
    if annual:
        _write_section_header(ws, row, "الضريبة العقارية السنوية", ncols=2, color="7B2D00"); row += 1
        for label, key in [
            ("أساس القيمة الإيجارية",  "rental_value_basis"),
            ("الإيجار الفعلي",          "effective_rental"),
            ("الخصم",                   "deduction"),
            ("الدخل الخاضع للضريبة",   "taxable_income"),
            ("السعر السنوي",            "annual_rate"),
            ("المعادلة",               "formula"),
        ]:
            _apply_row(ws, row, label, annual.get(key, _GAP)); row += 1
    row += 1

    # Transfer tax section
    transfer = data.get("transfer_tax") or {}
    if transfer:
        _write_section_header(ws, row, "ضريبة التصرفات العقارية", ncols=2, color="7B2D00"); row += 1
        for label, key in [
            ("أساس نقل الملكية",    "transfer_basis"),
            ("سعر نقل الملكية",     "transfer_rate"),
            ("ملاحظة المعادلة",    "formula_note"),
        ]:
            _apply_row(ws, row, label, transfer.get(key, _GAP)); row += 1


def _sheet_specialized_assets(ws, ctx: dict) -> None:
    """ws43: الأصول المتخصصة — specialized asset governance."""
    ws.sheet_view.rightToLeft = True
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 35
    data = (ctx.get("five_method_tax_context") or {}).get("specialized_asset_governance") or {}

    ws.merge_cells("A1:B1")
    h = ws.cell(row=1, column=1, value="الأصول المتخصصة")
    h.font = _hdr_font(size=12); h.fill = _hdr_fill("7B2D00"); h.alignment = _center_align()

    row = 2
    _apply_row(ws, row, "قابل للتطبيق؟",   "نعم" if data.get("applicable") else "لا"); row += 1
    _apply_row(ws, row, "ملاحظة",           data.get("note", _GAP)); row += 1
    _apply_row(ws, row, "استبعاد الآلات مؤكد؟",
               "نعم" if data.get("machinery_exclusion_confirmed") else "لا"); row += 1
    _apply_row(ws, row, "تقسيم الأرض/المبنى",
               data.get("land_building_split", _GAP)); row += 1
    _apply_row(ws, row, "حالة مصدر الأرض الصناعية",
               data.get("industrial_land_source_status", _GAP)); row += 1

    component_table = data.get("component_cost_table") or []
    if component_table:
        _write_section_header(ws, row, "جدول تكلفة المكونات", ncols=2, color="7B2D00"); row += 1
        for item in component_table:
            if not isinstance(item, dict):
                continue
            label = item.get("component") or item.get("label") or str(item)
            value = item.get("cost") or item.get("value") or _GAP
            _apply_row(ws, row, label, value); row += 1


def _sheet_underground_assets(ws, ctx: dict) -> None:
    """ws44: الأصول تحت الأرض — underground asset governance."""
    ws.sheet_view.rightToLeft = True
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 35
    data = (ctx.get("five_method_tax_context") or {}).get("underground_asset_governance") or {}

    ws.merge_cells("A1:B1")
    h = ws.cell(row=1, column=1, value="الأصول تحت الأرض")
    h.font = _hdr_font(size=12); h.fill = _hdr_fill("1A2E4A"); h.alignment = _center_align()

    row = 2
    fields = [
        ("قابل للتطبيق؟",                   None,   "applicable",                         True),
        ("ملاحظة",                           None,   "note",                               False),
        ("حصة الأرض صفر تتطلب تبريراً؟",    None,   "land_share_zero_requires_justification", True),
        ("تبرير معامل الطابق السفلي",        None,   "basement_factor_justification",      False),
        ("خطر الوصول",                       None,   "access_risk",                        False),
        ("خطر التهوية",                      None,   "ventilation_risk",                   False),
        ("ارتفاع خطر الفيضان؟",             None,   "flood_risk_heightened",              True),
        ("نوع الملكية",                      None,   "ownership_type",                     False),
    ]
    for label, _, key, is_bool in fields:
        val = data.get(key, _GAP)
        if is_bool and isinstance(val, bool):
            val = "نعم" if val else "لا"
        _apply_row(ws, row, label, val if val not in (None, "") else _GAP); row += 1


def _sheet_uspap_governance(ws, ctx: dict) -> None:
    """ws45: حوكمة USPAP — USPAP governance and readiness."""
    ws.sheet_view.rightToLeft = True
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 35
    data = ((ctx.get("five_method_tax_context") or {})
            .get("professional_compliance_readiness") or {}).get("uspap") or {}

    ws.merge_cells("A1:B1")
    h = ws.cell(row=1, column=1, value="حوكمة USPAP")
    h.font = _hdr_font(size=12); h.fill = _hdr_fill("3B1F6B"); h.alignment = _center_align()

    row = 2
    fields = [
        ("حالة الجاهزية",                    "readiness_status"),
        ("ملخص نطاق العمل",                  "scope_of_work_summary"),
        ("الاستخدام المقصود",                "intended_use"),
        ("المستخدم المقصود",                 "intended_user"),
        ("حصة الملكية",                      "property_interest"),
        ("افتراضات استثنائية",               "extraordinary_assumptions"),
        ("شروط افتراضية",                    "hypothetical_conditions"),
        ("الإفصاح عن المساعدة الجوهرية",    "significant_assistance_disclosure"),
        ("تحذير الاستخدام المقيّد",          "restricted_use_warning"),
        ("مخصص توقيع المقيّم",              "appraiser_signature_placeholder"),
        ("ملاحظة USPAP",                     "uspap_note"),
    ]
    for label, key in fields:
        _apply_row(ws, row, label, data.get(key, _GAP)); row += 1


# ── ws46–ws53: New enhanced sheets ───────────────────────────────────────────

def _sheet_reference_grounding(ws, ctx: dict) -> None:
    """ws46: التأصيل المرجعي — Reference Grounding."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 40
    ws.column_dimensions["B"].width = 35
    ws.column_dimensions["C"].width = 25
    rg = ctx.get("reference_grounding", {})

    ws.merge_cells("A1:C1")
    h = ws.cell(row=1, column=1, value="التأصيل المرجعي للمدخلات الفنية — Reference Grounding")
    h.font = _hdr_font(size=12); h.fill = _hdr_fill("1F4E78"); h.alignment = _center_align()

    row = 2
    rows = [
        ("معايير التقييم المصرية",          rg.get("egyptian_valuation_standards_status", _EXPERT)),
        ("مرجع FRA المصري",                 rg.get("fra_reference_status", _EXPERT)),
        ("توجيهات تكلفة جامعة عين شمس",    rg.get("ain_shams_cost_guidance_status", _EXPERT)),
        ("مرجع أسعار أراضي المجتمعات العمرانية", rg.get("nuca_land_price_reference_status", _EXPERT)),
        ("مرجع مصلحة الضرائب العقارية",    rg.get("tax_authority_reference_status", _EXPERT)),
        ("حالة مرجع التكلفة",               rg.get("cost_reference_status", _EXPERT)),
        ("حالة مرجع الإهلاك",               rg.get("depreciation_reference_status", _EXPERT)),
        ("حالة مرجع سعر الأرض",             rg.get("land_price_reference_status", _EXPERT)),
        ("حالة مرجع خصومات الدخل",          rg.get("income_deduction_reference_status", _EXPERT)),
        ("مستندات مرفقة",                   str(rg.get("source_documents_attached") or "لا يوجد")),
        ("مستندات مطلوبة",                  ", ".join(rg.get("source_documents_missing") or ["لا بيانات"])),
        ("تأكيد الخبير مطلوب",              "نعم" if rg.get("expert_confirmation_required") else "لا"),
        ("محدودية المراجع",                  rg.get("reference_limitations", _EXPERT)),
        ("تصنيف QA",                        rg.get("qa_label") or "إنتاج"),
        ("جاهزية الإنتاج",                   "لا" if not rg.get("production_readiness") else "نعم"),
    ]
    for lbl, val in rows:
        _apply_row(ws, row, lbl, val); row += 1

    row += 1
    _write_section_header(ws, row, "المراجع حسب الطريقة", ncols=3, color="1F4E78"); row += 1
    from openpyxl.styles import Font, PatternFill
    for col, hdr in enumerate(["الطريقة", "نوع المرجع", "حالة المرجع"], start=1):
        c = ws.cell(row=row, column=col, value=hdr)
        c.font = _hdr_font(color="1B2E4B"); c.fill = PatternFill("solid", fgColor="D6E4F0")
        c.alignment = _right_align(wrap=False); c.border = _thin_border()
    row += 1
    for method, ref_info in (rg.get("per_method_reference") or {}).items():
        ws.cell(row=row, column=1, value=method).border = _thin_border()
        ws.cell(row=row, column=2, value=ref_info.get("reference_type", _EXPERT) if isinstance(ref_info, dict) else str(ref_info)).border = _thin_border()
        ws.cell(row=row, column=3, value=ref_info.get("status", _EXPERT) if isinstance(ref_info, dict) else _EXPERT).border = _thin_border()
        row += 1

    row += 1
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
    warn = ws.cell(row=row, column=1, value="لا يتم اعتبار أي مدخل موسوم بأنه محاكاة QA أو مصدر مستقبلي كدليل رسمي قبل إرفاق المستند أو مراجعة الخبير.")
    warn.font = Font(name="Cairo", italic=True, size=8, color="7F1D1D"); warn.fill = _warn_fill()
    warn.alignment = _right_align()


def _sheet_comparative_tax_argument(ws, ctx: dict) -> None:
    """ws47: الحجة الضريبية المقارنة — Comparative Tax Argument."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 35
    ws.column_dimensions["B"].width = 25
    ws.column_dimensions["C"].width = 25
    ws.column_dimensions["D"].width = 22
    cta = ctx.get("comparative_tax_argument", {})

    ws.merge_cells("A1:D1")
    h = ws.cell(row=1, column=1, value="تحليل المقارنة الضريبية ونسبة المغالاة")
    h.font = _hdr_font(size=12); h.fill = _hdr_fill("7B2D00"); h.alignment = _center_align()

    row = 2
    _write_section_header(ws, row, "مقارنة حكومية / خبير", ncols=4, color="7B2D00"); row += 1
    gov_expert_rows = [
        ("ضريبة حكومية إجمالية",        cta.get("government_tax_amount", _EXPERT)),
        ("ضريبة حكومية / م²",           cta.get("government_tax_per_m2", _EXPERT)),
        ("ضريبة الخبير المقترحة إجمالي", cta.get("expert_indicated_tax_amount", _EXPERT)),
        ("ضريبة الخبير / م²",           cta.get("expert_indicated_tax_per_m2", _EXPERT)),
        ("فجوة الضريبة / م²",           cta.get("tax_per_m2_gap", _EXPERT)),
        ("مبلغ المغالاة",               cta.get("overcharge_amount", _EXPERT)),
        ("نسبة المغالاة",               cta.get("overcharge_percentage", _EXPERT)),
    ]
    for lbl, val in gov_expert_rows:
        _apply_row(ws, row, lbl, val); row += 1

    row += 1
    _write_section_header(ws, row, "حالات ضريبية مقارنة", ncols=4, color="7B2D00"); row += 1
    from openpyxl.styles import Font, PatternFill
    for col, hdr in enumerate(["رقم الحالة", "الحي", "ضريبة/م²", "مُدرجة"], start=1):
        c = ws.cell(row=row, column=col, value=hdr)
        c.font = _hdr_font(color="1B2E4B"); c.fill = PatternFill("solid", fgColor="D6E4F0")
        c.alignment = _right_align(wrap=False); c.border = _thin_border()
    row += 1
    for case in (cta.get("comparable_tax_cases") or []):
        ws.cell(row=row, column=1, value=case.get("case_id", _EXPERT)).border = _thin_border()
        ws.cell(row=row, column=2, value=case.get("district", _EXPERT)).border = _thin_border()
        ws.cell(row=row, column=3, value=case.get("tax_per_m2", _EXPERT)).border = _thin_border()
        ws.cell(row=row, column=4, value="نعم" if case.get("included") else "لا").border = _thin_border()
        row += 1

    row += 1
    _write_section_header(ws, row, "ملخص الحجة", ncols=4, color="7B2D00"); row += 1
    summary_rows = [
        ("متوسط ضريبة المقارنات / م²",  cta.get("average_comparable_tax_per_m2", _EXPERT)),
        ("نسبة الموضوع للمقارنات",       cta.get("subject_vs_comparable_ratio", _EXPERT)),
        ("قوة الحجة",                    cta.get("argument_strength", _EXPERT)),
        ("حالة المصدر",                  cta.get("source_status", _EXPERT)),
    ]
    for lbl, val in summary_rows:
        _apply_row(ws, row, lbl, val); row += 1

    row += 1
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
    disc = ws.cell(row=row, column=1, value=cta.get("disclaimer", ""))
    disc.font = Font(name="Cairo", italic=True, size=8, color="374151"); disc.alignment = _right_align()


def _sheet_deductible_expenses(ws, ctx: dict) -> None:
    """ws48: خصومات وصيانة وشغور — Deductible Expenses."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 40
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 20
    ws.column_dimensions["D"].width = 20
    ws.column_dimensions["E"].width = 20
    dea = ctx.get("deductible_expense_analysis", {})

    ws.merge_cells("A1:E1")
    h = ws.cell(row=1, column=1, value="الخصومات والاستقطاعات المؤثرة على الوعاء الضريبي")
    h.font = _hdr_font(size=12); h.fill = _hdr_fill("2D5A27"); h.alignment = _center_align()

    row = 2
    maint_rate = dea.get("maintenance_deduction_rate", 0) or 0
    rows = [
        ("فئة العقار",                              dea.get("property_class", _EXPERT)),
        ("إجمالي القيمة الإيجارية السنوية",         dea.get("gross_annual_rental_value", _EXPERT)),
        ("نسبة خصم الصيانة والإدارة",               f"{float(maint_rate)*100:.0f}%"),
        ("مبلغ الخصم",                              dea.get("maintenance_deduction_amount", _EXPERT)),
        ("الوعاء الضريبي الصافي",                   dea.get("net_taxable_rental_basis", _EXPERT)),
        ("أساس النسبة (قانوني/افتراضي)",             dea.get("statutory_or_assumption_basis", _EXPERT)),
        ("حالة المصدر",                              dea.get("source_status", _EXPERT)),
        ("تأكيد الخبير مطلوب",                      "نعم" if dea.get("expert_confirmation_required") else "لا"),
        ("هل تنطبق على ضريبة التصرفات؟",            "لا — ضريبة التصرفات لا تخضع لهذه الخصومات"),
        ("ملاحظة",                                   dea.get("notes", _EXPERT)),
    ]
    for lbl, val in rows:
        is_editable = "نسبة" in lbl
        _apply_row(ws, row, lbl, val, is_input=is_editable)
        if is_editable:
            from openpyxl.styles import Font
            note_cell = ws.cell(row=row, column=3, value="النسبة قابلة للتعديل")
            note_cell.font = Font(name="Cairo", italic=True, size=8, color="2D5A27")
        row += 1


def _sheet_committee_reconciliation(ws, ctx: dict) -> None:
    """ws49: مصفوفة التوفيق — Committee Reconciliation Matrix."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 20
    ws.column_dimensions["D"].width = 15
    ws.column_dimensions["E"].width = 20
    ws.column_dimensions["F"].width = 20
    crm = ctx.get("committee_reconciliation_matrix", {})

    ws.merge_cells("A1:F1")
    h = ws.cell(row=1, column=1, value="مصفوفة توفيق نتائج الطرق الخمس — Committee Reconciliation Matrix")
    h.font = _hdr_font(size=12); h.fill = _hdr_fill("C9973A"); h.alignment = _center_align()

    def _list_to_str(v):
        if isinstance(v, list):
            return ", ".join(str(x) for x in v) if v else _GAP
        return v if v is not None else _GAP

    row = 2
    summary_rows = [
        ("الطرق المدروسة",           crm.get("methods_considered", _EXPERT)),
        ("الطرق المُستخدمة",         _list_to_str(crm.get("methods_used"))),
        ("الطرق المستبعدة",          _list_to_str(crm.get("methods_excluded"))),
        ("نتيجة القيمة الموزونة",    crm.get("weighted_value_result", _EXPERT)),
        ("نتيجة الضريبة الموزونة",   crm.get("weighted_tax_result", _EXPERT)),
        ("الضريبة المقترحة النهائية", crm.get("final_indicated_tax", _EXPERT)),
        ("الوفر المتوقع",            crm.get("expected_saving", _EXPERT)),
        ("مجموع الأوزان",            crm.get("total_weight", _EXPERT)),
        ("التحقق من الأوزان",        crm.get("weight_validation", _EXPERT)),
        ("ملاحظة IVS",               crm.get("ivs_readiness_note", _EXPERT)),
    ]
    for lbl, val in summary_rows:
        _apply_row(ws, row, lbl, val); row += 1

    row += 1
    _write_section_header(ws, row, "جدول الطرق والأوزان", ncols=6, color="C9973A"); row += 1
    from openpyxl.styles import Font, PatternFill
    for col, hdr in enumerate(["الطريقة", "الضريبة المقترحة", "جودة البيانات", "الوزن", "الناتج الموزون", "مُدرجة"], start=1):
        c = ws.cell(row=row, column=col, value=hdr)
        c.font = _hdr_font(color="1B2E4B"); c.fill = PatternFill("solid", fgColor="FFF3CD")
        c.alignment = _right_align(wrap=False); c.border = _thin_border()
    row += 1
    for entry in (crm.get("method_entries") or []):
        ws.cell(row=row, column=1, value=entry.get("method_name", _EXPERT)).border = _thin_border()
        ws.cell(row=row, column=2, value=entry.get("indicated_tax", _EXPERT)).border = _thin_border()
        ws.cell(row=row, column=3, value=entry.get("data_quality_status") or entry.get("data_quality", _EXPERT)).border = _thin_border()
        ws.cell(row=row, column=4, value=entry.get("weight", _EXPERT)).border = _thin_border()
        ws.cell(row=row, column=5, value=entry.get("weighted_result", _EXPERT)).border = _thin_border()
        ws.cell(row=row, column=6, value="نعم" if entry.get("included") else "لا").border = _thin_border()
        row += 1

    total_weight = crm.get("total_weight", 0)
    row += 1
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    wt = ws.cell(row=row, column=1, value=f"مجموع الأوزان المُدرجة = {total_weight}% — يجب أن يساوي 100%")
    wt.font = Font(name="Cairo", bold=True, size=9, color="7F1D1D" if total_weight != 100 else "2D5A27")
    wt.alignment = _right_align(); row += 1

    row += 1
    _apply_row(ws, row, "ملخص أمام اللجنة", crm.get("committee_facing_summary", _EXPERT)); row += 1
    _apply_row(ws, row, "مبررات التوفيق",    crm.get("reconciliation_reasoning", _EXPERT))


def _sheet_geographic_tax_check(ws, ctx: dict) -> None:
    """ws50: اختبار المثل الضريبي — Geographic Tax Reasonableness Check."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 20
    ws.column_dimensions["D"].width = 20
    ws.column_dimensions["E"].width = 20
    gtc = ctx.get("geographic_tax_reasonableness_check", {})

    ws.merge_cells("A1:E1")
    h = ws.cell(row=1, column=1, value="اختبار المثل الجغرافي — Geographic Tax Reasonableness Check")
    h.font = _hdr_font(size=12); h.fill = _hdr_fill("1A4D2E"); h.alignment = _center_align()

    row = 2
    summary_rows = [
        ("الحي",                          gtc.get("subject_district", _EXPERT)),
        ("كود المنطقة",                   gtc.get("subject_zone_id", _EXPERT)),
        ("فئة العقار",                    gtc.get("subject_property_class", _EXPERT)),
        ("ضريبة الموضوع / م²",            gtc.get("subject_tax_per_m2", _EXPERT)),
        ("متوسط ضريبة المقارنات / م²",    gtc.get("average_comparable_tax_per_m2", _EXPERT)),
        ("فجوة الحكومة مقابل المنطقة",    gtc.get("government_vs_area_average_gap", _EXPERT)),
        ("نسبة الحكومة مقابل المنطقة",    gtc.get("government_vs_area_average_ratio", _EXPERT)),
        ("مؤشر التقدير المبالغ فيه",      gtc.get("overassessment_indicator", _EXPERT)),
        ("حالة مصدر البيانات",             gtc.get("data_source_status", _EXPERT)),
        ("جاهز للإنتاج",                  "نعم" if gtc.get("production_ready") else "لا"),
    ]
    for lbl, val in summary_rows:
        _apply_row(ws, row, lbl, val); row += 1

    row += 1
    _write_section_header(ws, row, "حالات مقارنة جغرافية", ncols=5, color="1A4D2E"); row += 1
    from openpyxl.styles import Font, PatternFill
    for col, hdr in enumerate(["رقم المقارنة", "الحي", "ضريبة/م²", "حالة التطابق", "مُدرجة"], start=1):
        c = ws.cell(row=row, column=col, value=hdr)
        c.font = _hdr_font(color="1B2E4B"); c.fill = PatternFill("solid", fgColor="D6F5D6")
        c.alignment = _right_align(wrap=False); c.border = _thin_border()
    row += 1
    for case in (gtc.get("comparable_tax_rows") or []):
        ws.cell(row=row, column=1, value=case.get("tax_comparable_id", _EXPERT)).border = _thin_border()
        ws.cell(row=row, column=2, value=case.get("district", _EXPERT)).border = _thin_border()
        ws.cell(row=row, column=3, value=case.get("tax_per_m2", _EXPERT)).border = _thin_border()
        ws.cell(row=row, column=4, value=case.get("geo_match_status", _EXPERT)).border = _thin_border()
        ws.cell(row=row, column=5, value="نعم" if case.get("included") else "لا").border = _thin_border()
        row += 1

    row += 1
    _apply_row(ws, row, "ملاحظات الخبير", gtc.get("expert_notes", _EXPERT))


def _sheet_industrial_asset_separation(ws, ctx: dict) -> None:
    """ws51: فصل الأصول العقارية والتشغيلية — Industrial Asset Separation."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 40
    ws.column_dimensions["B"].width = 20
    ias = ctx.get("industrial_asset_separation", {})

    ws.merge_cells("A1:B1")
    h = ws.cell(row=1, column=1, value="الفصل بين الأصول العقارية والأصول التشغيلية")
    h.font = _hdr_font(size=12); h.fill = _hdr_fill("374151"); h.alignment = _center_align()

    if ias.get("applicable") is False:
        ws.cell(row=2, column=1).value = "هذا القسم مخصص للمصانع والمنشآت الصناعية — غير مطبق على هذا النوع"
        ws.cell(row=2, column=1).font = _data_font()
        ws.cell(row=2, column=1).alignment = _right_align()
        return

    row = 2
    mach = ias.get("machinery_equipment_exclusion") or {}
    prod = ias.get("production_lines_exclusion") or {}
    biz  = ias.get("business_income_exclusion") or {}
    rows = [
        ("مكونات الأصول العقارية الخاضعة للضريبة", ", ".join(ias.get("taxable_real_estate_components") or [])),
        ("الأصول المستبعدة (تشغيلية)",               ", ".join(ias.get("excluded_operating_assets") or [])),
        ("الآلات والمعدات",                           "مستبعدة — " + (mach.get("reason") or _EXPERT)),
        ("خطوط الإنتاج",                             "مستبعدة — " + (prod.get("reason") or _EXPERT)),
        ("أرباح النشاط التجاري",                     "مستبعدة — " + (biz.get("reason") or _EXPERT)),
        ("نطاق التقييم",                              ias.get("valuation_scope_note", _EXPERT)),
        ("تأكيد الخبير مطلوب",                       "نعم"),
    ]
    for lbl, val in rows:
        _apply_row(ws, row, lbl, val or _EXPERT); row += 1


def _sheet_committee_argument_summary(ws, ctx: dict) -> None:
    """ws52: ملخص الحجة أمام اللجنة — Committee Argument Summary."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 40
    ws.column_dimensions["B"].width = 50
    cas = ctx.get("committee_argument_summary", {})

    ws.merge_cells("A1:B1")
    h = ws.cell(row=1, column=1, value="ملخص الحجة الفنية الموجهة للجنة الطعن")
    h.font = _hdr_font(size=12); h.fill = _hdr_fill("1B2E4B"); h.alignment = _center_align()

    row = 2
    rows = [
        ("موقف الممول",                 cas.get("taxpayer_position_summary", _EXPERT)),
        ("ملخص التقدير الحكومي",        cas.get("government_assessment_summary", _EXPERT)),
        ("حجة المغالاة",                cas.get("overcharge_argument", _EXPERT)),
        ("حجة ضريبة المتر",             cas.get("tax_per_m2_argument", _EXPERT)),
        ("نتيجة توفيق الطرق",           cas.get("method_reconciliation_argument", _EXPERT)),
        ("حالة المهلة",                 cas.get("deadline_position_summary", _EXPERT)),
        ("المستندات المطلوبة",          cas.get("documents_needed_summary", _EXPERT)),
        ("توصية الخبير",                cas.get("expert_recommendation", _EXPERT)),
        ("صياغة الحجة أمام اللجنة",    cas.get("committee_facing_wording", _EXPERT)),
        ("إخلاء المسؤولية",             cas.get("formal_disclaimer", _EXPERT)),
    ]
    for lbl, val in rows:
        _apply_row(ws, row, lbl, val); row += 1


def _sheet_visible_text_quality(ws, ctx: dict) -> None:
    """ws53: جودة نص التقرير — Visible Text Quality Check."""
    ws.sheet_view.rightToLeft = True
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 35
    ws.column_dimensions["B"].width = 25
    vtq = ctx.get("visible_text_quality_check", {})

    ws.merge_cells("A1:B1")
    h = ws.cell(row=1, column=1, value="فحص جودة النص المرئي")
    h.font = _hdr_font(size=12); h.fill = _hdr_fill("6B7280"); h.alignment = _center_align()

    row = 2
    rows = [
        ("رموز مكسورة مرصودة",              "لا" if not vtq.get("corrupted_tokens_found") else "نعم — يحتاج مراجعة"),
        ("قيم فارغة مؤشرة بشكل صحيح",      "نعم" if vtq.get("missing_value_placeholders_ok") else "يحتاج مراجعة"),
        ("تنسيق العملة صحيح",               "نعم" if vtq.get("currency_format_ok") else "يحتاج مراجعة"),
        ("حالة النص العربي",                 vtq.get("arabic_wording_status", _EXPERT)),
        ("الحالة النهائية",                  vtq.get("final_status", _EXPERT)),
    ]
    for lbl, val in rows:
        _apply_row(ws, row, lbl, val); row += 1


# ── Field mapping sheets ──────────────────────────────────────────────────────

def _sheet_field_mappings(ws, mapping_records: list, ctx: dict) -> None:
    """Populate the ربط الحقول بالمصادر sheet with field mapping data."""
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    hdr_fill = _hdr_fill("1E40AF")
    hdr_font = _hdr_font()
    ctr      = _center_align()
    ok_fill  = PatternFill("solid", fgColor="D1FAE5")
    warn_fill= PatternFill("solid", fgColor="FEF3C7")
    err_fill = PatternFill("solid", fgColor="FEE2E2")

    ws.cell(row=1, column=1, value="ربط الحقول بالمصادر — Field Mapping").font = \
        Font(name="Cairo", bold=True, size=11, color="1E40AF")

    headers = [
        "mapping_id", "mapped_field_key", "التسمية العربية", "المجموعة",
        "القيمة", "نوع القيمة", "evidence_id", "نوع المستند",
        "source_registry_id", "حالة الربط", "إنتاجي", "مؤكد من الخبير",
        "تاريخ التأكيد", "تعارض", "مستخدم في التقرير", "ملاحظات الخبير",
    ]
    hr = 2
    for ci, h in enumerate(headers, 1):
        cell = ws.cell(row=hr, column=ci, value=h)
        cell.font      = hdr_font
        cell.fill      = hdr_fill
        cell.alignment = ctr

    if not mapping_records:
        ws.cell(row=hr + 1, column=1, value="لا توجد روابط حقول مسجلة بعد.").font = \
            Font(name="Cairo", size=9, color="374151")
        return

    status_label = {
        "draft":        "مسودة",
        "needs_review": "بانتظار المراجعة",
        "confirmed":    "مؤكد",
        "rejected":     "مرفوض",
        "superseded":   "مُستبدل",
    }

    sli = ctx.get("source_linked_inputs", {})

    for i, m in enumerate(mapping_records, 1):
        row    = hr + i
        status = m.get("mapping_status", "")
        prod   = m.get("production_ready", False)
        conf   = m.get("expert_confirmed", False)
        cf_st  = m.get("conflict_status", "no_conflict")
        fkey   = m.get("mapped_field_key", "")

        # Exclude rejected/superseded expert notes
        public_notes = "" if status in ("rejected", "superseded") else (m.get("expert_notes") or "")

        vals = [
            m.get("mapping_id", ""),
            fkey,
            m.get("mapped_field_label_ar", ""),
            m.get("mapped_field_group", ""),
            m.get("mapped_value", ""),
            m.get("mapped_value_type", ""),
            m.get("evidence_id", ""),
            m.get("evidence_type", ""),
            m.get("source_registry_id") or "—",
            status_label.get(status, status),
            "نعم" if prod else "لا",
            "نعم" if conf else "لا",
            (m.get("expert_reviewed_at") or "")[:10],
            cf_st,
            "نعم" if m.get("report_usage_allowed") else "لا",
            public_notes,
        ]
        for ci, v in enumerate(vals, 1):
            c = ws.cell(row=row, column=ci, value=v)
            c.font = _data_font()
            if ci == 10:
                if status == "confirmed":
                    c.fill = ok_fill
                elif status in ("rejected", "superseded"):
                    c.fill = err_fill
            if ci == 14 and cf_st != "no_conflict":
                c.fill = warn_fill

    ws.column_dimensions[get_column_letter(3)].width  = 28
    ws.column_dimensions[get_column_letter(5)].width  = 20
    ws.column_dimensions[get_column_letter(16)].width = 32


def _sheet_field_mapping_conflicts(ws, ctx: dict) -> None:
    """Populate the تعارضات البيانات sheet from context field_mapping_summary."""
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    hdr_fill  = _hdr_fill("B91C1C")
    hdr_font  = _hdr_font()
    ctr       = _center_align()
    warn_fill = PatternFill("solid", fgColor="FEE2E2")

    ws.cell(row=1, column=1, value="تعارضات البيانات — Field Mapping Conflicts").font = \
        Font(name="Cairo", bold=True, size=11, color="B91C1C")

    headers = [
        "conflict_id", "mapping_id", "field_key", "القيمة الأصلية",
        "القيمة المرتبطة بالمستند", "evidence_id", "source_registry_id",
        "الخطورة", "حالة التعارض", "قرار الخبير", "سبب التجاوز",
    ]
    hr = 2
    for ci, h in enumerate(headers, 1):
        cell = ws.cell(row=hr, column=ci, value=h)
        cell.font      = hdr_font
        cell.fill      = hdr_fill
        cell.alignment = ctr

    fm_sum = ctx.get("field_mapping_summary", {})
    if not fm_sum.get("conflicts_count"):
        ws.cell(row=hr + 1, column=1, value="لا توجد تعارضات بيانات مسجلة.").font = \
            Font(name="Cairo", size=9, color="374151")
        return

    # Load from storage
    request_id = ctx.get("request_id", "")
    conflict_records: list = []
    if request_id and not request_id.startswith("QA-"):
        try:
            from tax_appeal_field_mapping import load_conflict_records
            conflict_records = load_conflict_records(request_id)
        except Exception:
            pass

    if not conflict_records:
        ws.cell(row=hr + 1, column=1, value=f"عدد التعارضات: {fm_sum.get('conflicts_count', 0)} — البيانات التفصيلية غير متاحة.").font = \
            Font(name="Cairo", size=9, color="374151")
        return

    for i, c in enumerate(conflict_records, 1):
        row = hr + i
        vals = [
            c.get("conflict_id", ""),
            c.get("mapping_id", ""),
            c.get("field_key", ""),
            c.get("existing_payload_value", ""),
            c.get("mapped_value", ""),
            c.get("evidence_id", ""),
            c.get("source_registry_id") or "—",
            c.get("severity", ""),
            c.get("conflict_status", ""),
            c.get("resolution") or "—",
            c.get("override_reason") or "—",
        ]
        for ci, v in enumerate(vals, 1):
            cell = ws.cell(row=row, column=ci, value=v)
            cell.font = _data_font()
            if c.get("conflict_status") == "needs_expert_decision":
                cell.fill = warn_fill

    ws.column_dimensions[get_column_letter(4)].width  = 22
    ws.column_dimensions[get_column_letter(5)].width  = 22
    ws.column_dimensions[get_column_letter(11)].width = 32


# ── Main workbook builder ─────────────────────────────────────────────────────

def _sheet_evidence(ws, evidence_records: list) -> None:
    """Populate the المستندات والمرفقات sheet with uploaded evidence data."""
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    hdr_fill = _hdr_fill("374151")
    hdr_font = _hdr_font()
    ctr      = _center_align()
    ok_fill  = PatternFill("solid", fgColor="D1FAE5")
    err_fill = PatternFill("solid", fgColor="FEE2E2")
    lbl_font = Font(name="Cairo", size=9, color="374151")

    headers = [
        "evidence_id", "نوع المستند", "اسم الملف", "الحالة",
        "جاهز للتقرير", "جاهز كمصدر", "إنتاجي", "source_registry_id",
        "تاريخ الرفع", "ملاحظات الخبير", "الإجراء المطلوب",
    ]
    hr = 1
    ws.cell(row=hr, column=1, value="المستندات والمرفقات — Evidence & Attachments").font = \
        Font(name="Cairo", bold=True, size=11, color="1F4E78")
    hr = 2
    for ci, h in enumerate(headers, 1):
        cell = ws.cell(row=hr, column=ci, value=h)
        cell.font      = hdr_font
        cell.fill      = hdr_fill
        cell.alignment = ctr

    if not evidence_records:
        row = hr + 1
        ws.cell(row=row, column=1, value="لم يتم رفع أي مستندات مرفقة حتى الآن.").font = lbl_font
        return

    status_label = {
        "uploaded":            "مرفوع",
        "needs_review":        "بانتظار المراجعة",
        "approved_for_report": "معتمد للتقرير",
        "approved_as_source":  "معتمد كمصدر",
        "rejected":            "مرفوض",
        "superseded":          "مُستبدل",
    }

    for i, ev in enumerate(evidence_records, 1):
        row = hr + i
        status              = ev.get("status", "")
        production_ready    = ev.get("production_ready", False)
        approved_for_report = ev.get("approved_for_report", False)
        approved_as_source  = ev.get("approved_as_source", False)

        action = ""
        if status == "needs_review":
            action = "يلزم مراجعة الخبير"
        elif status == "rejected":
            action = "مستبعد — لا يُستخدم"
        elif status == "approved_as_source" and not ev.get("source_registry_id"):
            action = "يمكن إدراجه في سجل المصادر"
        elif status == "approved_for_report":
            action = "معتمد للتقرير — ليس مصدرًا إنتاجيًا"
        elif status == "approved_as_source":
            action = "مصدر إنتاجي — لا يحتاج إجراء"

        vals = [
            ev.get("evidence_id", ""),
            ev.get("evidence_type_label_ar", ev.get("evidence_type", "")),
            ev.get("original_filename", ""),
            status_label.get(status, status),
            "نعم" if approved_for_report else "لا",
            "نعم" if approved_as_source else "لا",
            "نعم" if production_ready else "لا",
            ev.get("source_registry_id") or "—",
            (ev.get("uploaded_at") or "")[:10],
            ev.get("expert_review_notes") or "",
            action,
        ]
        for ci, v in enumerate(vals, 1):
            c = ws.cell(row=row, column=ci, value=v)
            c.font = _data_font()
            if ci == 5 and approved_for_report:
                c.fill = ok_fill
            elif ci == 6 and approved_as_source:
                c.fill = ok_fill
            elif ci in (5, 6) and status == "rejected":
                c.fill = err_fill

    ws.column_dimensions[get_column_letter(3)].width = 30
    ws.column_dimensions[get_column_letter(2)].width = 24
    ws.column_dimensions[get_column_letter(11)].width = 32


def _create_tax_appeal_workbook(
    request_id: str,
    request_record: dict,
    evidence_records: list = None,
    mapping_records: list = None,
) -> Path:
    """Build and persist the tax appeal expert workbook.

    Returns the Path to the saved .xlsx file.
    Internal path never exposed to ordinary users.
    evidence_records: optional list of evidence dicts; pass [] or None if unavailable.
    mapping_records: optional list of field-mapping dicts; pass [] or None if unavailable.
    """
    import openpyxl

    evidence_records = list(evidence_records or [])
    mapping_records  = list(mapping_records  or [])

    # Parse payload
    payload: dict = request_record.get("payload_json") or {}
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            payload = {}

    # Merge record fields into payload for context
    for key in ("request_id", "taxpayer_name", "owner_name", "phone", "email"):
        if request_record.get(key) and not payload.get(key):
            payload[key] = request_record[key]
    payload.setdefault("request_id", request_id)

    # Build tax context (pass evidence + mappings so summaries appear in ctx)
    from tax_appeal_context import _build_tax_appeal_context
    ctx = _build_tax_appeal_context(
        payload,
        evidence_records=evidence_records,
        mapping_records=mapping_records,
    )
    tax_mode = ctx.get("tax_mode", "annual_real_estate_tax")

    # Create workbook
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # remove default Sheet

    # Sheet order: "مدخلات الطعن" MUST be first
    ws1  = wb.create_sheet("مدخلات الطعن")
    ws2  = wb.create_sheet("Dashboard")
    ws3  = wb.create_sheet("بيانات العقار")
    ws4  = wb.create_sheet("بيانات الإخطار الضريبي")
    ws5  = wb.create_sheet("حساب الضريبة العقارية")
    ws6  = wb.create_sheet("حساب ضريبة التصرفات")
    ws7  = wb.create_sheet("تحليل المغالاة الحكومية")
    ws8  = wb.create_sheet("المقارنات السوقية والإيجارية")
    ws9  = wb.create_sheet("مهلة الطعن 60 يومًا")
    ws10 = wb.create_sheet("المستندات المطلوبة")
    ws11 = wb.create_sheet("مصادر البيانات")
    ws12 = wb.create_sheet("سجل المراجعة")
    ws13 = wb.create_sheet("صياغة مذكرة الطعن")
    ws14 = wb.create_sheet("جاهزية Qdrant-RAG المستقبلية")
    # ── Five canonical method sheets ──────────────────────────────────────────
    ws15 = wb.create_sheet("طريقة التكلفة")
    ws16 = wb.create_sheet("طريقة المقارنة")
    ws17 = wb.create_sheet("طريقة الرسملة")
    ws18 = wb.create_sheet("طريقة المقارنة الضريبية")
    ws19 = wb.create_sheet("طريقة الانحدار المتعدد")
    ws20 = wb.create_sheet("توفيق الطرق الخمس")
    # ── Professional governance sheets ────────────────────────────────────────
    ws21 = wb.create_sheet("تحليل HBU")
    ws22 = wb.create_sheet("المعايير المهنية")
    ws23 = wb.create_sheet("حوكمة البيانات")
    ws24 = wb.create_sheet("الافتراضات والإفصاحات")
    ws25 = wb.create_sheet("تحليل الحساسية")
    ws26 = wb.create_sheet("فجوات البيانات")
    # ── Reference intelligence sheets ─────────────────────────────────────────
    ws27 = wb.create_sheet("قاعدة المراجع")
    ws28 = wb.create_sheet("نموذج الإهلاك")
    ws29 = wb.create_sheet("حساسية الضريبة")
    ws30 = wb.create_sheet("مخاطر الطعن")
    ws31 = wb.create_sheet("تقارير سابقة مرتبطة")
    ws32 = wb.create_sheet("إصدارات المراجع")
    # ── Compliance, disclosure, methodology & specialized sheets ──────────────
    ws33 = wb.create_sheet("نطاق العمل")
    ws34 = wb.create_sheet("بيان الامتثال")
    ws35 = wb.create_sheet("DCF إن وجد")
    ws36 = wb.create_sheet("مراجعة الجودة")
    ws37 = wb.create_sheet("توقيع واعتماد الخبير")
    ws38 = wb.create_sheet("ESG والمخاطر المناخية")
    ws39 = wb.create_sheet("الفحص القانوني والمستندي")
    ws40 = wb.create_sheet("مراجعة النظراء")
    ws41 = wb.create_sheet("مصفوفة المستندات")
    ws42 = wb.create_sheet("أساس الضريبة والقيمة السوقية")
    ws43 = wb.create_sheet("الأصول المتخصصة")
    ws44 = wb.create_sheet("الأصول تحت الأرض")
    ws45 = wb.create_sheet("حوكمة USPAP")

    # Calculation mode — automatic so formulas evaluate
    wb.calculation.calcMode = "auto"

    # Populate sheets
    _sheet_inputs(ws1, ctx, tax_mode)
    _sheet_dashboard(ws2, ctx)
    _sheet_property(ws3, ctx)
    _sheet_notice(ws4, ctx)
    _sheet_annual_tax(ws5, ctx)
    _sheet_transfer_tax(ws6, ctx)
    _sheet_overcharge(ws7, ctx)
    _sheet_comparables(ws8, ctx)
    _sheet_deadline(ws9, ctx)
    _sheet_documents(ws10, ctx)
    _sheet_sources(ws11, ctx)
    _sheet_audit(ws12, ctx)
    _sheet_memo(ws13, ctx)
    _sheet_qdrant(ws14, ctx)
    _sheet_five_cost(ws15, ctx)
    _sheet_five_market(ws16, ctx)
    _sheet_five_income(ws17, ctx)
    _sheet_five_tax_comparison(ws18, ctx)
    _sheet_five_regression(ws19, ctx)
    _sheet_five_reconciliation(ws20, ctx)
    _sheet_hbu_analysis(ws21, ctx)
    _sheet_standards_mapping(ws22, ctx)
    _sheet_data_governance(ws23, ctx)
    _sheet_assumptions(ws24, ctx)
    _sheet_sensitivity(ws25, ctx)
    _sheet_property_class_review(ws26, ctx)
    _sheet_reference_registry(ws27, ctx)
    _sheet_depreciation_model(ws28, ctx)
    _sheet_tax_sensitivity(ws29, ctx)
    _sheet_appeal_risk(ws30, ctx)
    _sheet_prior_reports(ws31, ctx)
    _sheet_reference_versioning(ws32, ctx)
    _sheet_scope_of_work(ws33, ctx)
    _sheet_compliance_readiness(ws34, ctx)
    _sheet_dcf(ws35, ctx)
    _sheet_quality_control(ws36, ctx)
    _sheet_expert_signature(ws37, ctx)
    _sheet_esg_climate(ws38, ctx)
    _sheet_legal_due_diligence(ws39, ctx)
    _sheet_peer_review(ws40, ctx)
    _sheet_document_matrix(ws41, ctx)
    _sheet_tax_basis_vs_value(ws42, ctx)
    _sheet_specialized_assets(ws43, ctx)
    _sheet_underground_assets(ws44, ctx)
    _sheet_uspap_governance(ws45, ctx)

    ws46 = wb.create_sheet("التأصيل المرجعي")
    ws47 = wb.create_sheet("الحجة الضريبية المقارنة")
    ws48 = wb.create_sheet("خصومات وصيانة وشغور")
    ws49 = wb.create_sheet("مصفوفة التوفيق")
    ws50 = wb.create_sheet("اختبار المثل الضريبي")
    ws51 = wb.create_sheet("فصل الأصول العقارية والتشغيلية")
    ws52 = wb.create_sheet("ملخص الحجة أمام اللجنة")
    ws53 = wb.create_sheet("جودة نص التقرير")

    _sheet_reference_grounding(ws46, ctx)
    _sheet_comparative_tax_argument(ws47, ctx)
    _sheet_deductible_expenses(ws48, ctx)
    _sheet_committee_reconciliation(ws49, ctx)
    _sheet_geographic_tax_check(ws50, ctx)
    _sheet_industrial_asset_separation(ws51, ctx)
    _sheet_committee_argument_summary(ws52, ctx)
    _sheet_visible_text_quality(ws53, ctx)

    # ── Evidence sheet (Part H) ───────────────────────────────────────────────
    ws_ev = wb.create_sheet("المستندات والمرفقات")
    _sheet_evidence(ws_ev, evidence_records)
    ws_ev.sheet_properties.tabColor = "374151"  # gray — documents category

    # Tab colors — group by category
    ws1.sheet_properties.tabColor  = "1B2E4B"  # inputs — dark navy
    ws2.sheet_properties.tabColor  = "C9973A"  # dashboard — gold
    ws3.sheet_properties.tabColor  = "2D5A27"  # property — green
    ws4.sheet_properties.tabColor  = "7B2D00"  # notice — amber
    ws5.sheet_properties.tabColor  = "1A4D2E"  # annual tax — dark green
    ws6.sheet_properties.tabColor  = "5C1A1A"  # transfer tax — dark red
    ws7.sheet_properties.tabColor  = "7B2D00"  # overcharge — amber
    ws8.sheet_properties.tabColor  = "2D5A27"  # comparables — green
    ws9.sheet_properties.tabColor  = "7F1D1D"  # deadline — red
    ws10.sheet_properties.tabColor = "374151"  # documents — gray
    ws11.sheet_properties.tabColor = "374151"  # sources — gray
    ws12.sheet_properties.tabColor = "374151"  # audit — gray
    ws13.sheet_properties.tabColor = "1B2E4B"  # memo — dark navy
    ws14.sheet_properties.tabColor = "6B7280"  # qdrant-future — muted gray
    ws15.sheet_properties.tabColor = "1A4D2E"  # cost — dark green
    ws16.sheet_properties.tabColor = "2D5A27"  # market — green
    ws17.sheet_properties.tabColor = "1F4E78"  # income — dark blue
    ws18.sheet_properties.tabColor = "7B2D00"  # tax comparison — amber
    ws19.sheet_properties.tabColor = "374151"  # regression — gray
    ws20.sheet_properties.tabColor = "C9973A"  # reconciliation — gold
    ws21.sheet_properties.tabColor = "1F3A5F"  # HBU — dark blue
    ws22.sheet_properties.tabColor = "3B1F6B"  # standards — purple
    ws23.sheet_properties.tabColor = "1A2E4A"  # governance — dark navy
    ws24.sheet_properties.tabColor = "1B4332"  # assumptions — dark green
    ws25.sheet_properties.tabColor = "1E40AF"  # sensitivity — dark blue
    ws26.sheet_properties.tabColor = "7F1D1D"  # data gaps — dark red
    ws27.sheet_properties.tabColor = "1B2E4B"  # reference registry — dark navy
    ws28.sheet_properties.tabColor = "1A4D2E"  # depreciation model — dark green
    ws29.sheet_properties.tabColor = "1E40AF"  # tax sensitivity — dark blue
    ws30.sheet_properties.tabColor = "7F1D1D"  # appeal risk — dark red
    ws31.sheet_properties.tabColor = "3B1F6B"  # prior reports — purple
    ws32.sheet_properties.tabColor = "1A2E4A"  # versioning — dark navy
    ws33.sheet_properties.tabColor = "1F4E78"  # scope of work — dark blue
    ws34.sheet_properties.tabColor = "3B1F6B"  # compliance — purple
    ws35.sheet_properties.tabColor = "1F4E78"  # DCF — dark blue
    ws36.sheet_properties.tabColor = "1B4332"  # quality control — dark green
    ws37.sheet_properties.tabColor = "1A2E4A"  # expert signature — dark navy
    ws38.sheet_properties.tabColor = "1A4D2E"  # ESG climate — dark green
    ws39.sheet_properties.tabColor = "7F1D1D"  # legal due diligence — dark red
    ws40.sheet_properties.tabColor = "3B1F6B"  # peer review — purple
    ws41.sheet_properties.tabColor = "374151"  # document matrix — gray
    ws42.sheet_properties.tabColor = "7B2D00"  # tax basis — amber
    ws43.sheet_properties.tabColor = "7B2D00"  # specialized assets — amber
    ws44.sheet_properties.tabColor = "1A2E4A"  # underground assets — dark navy
    ws45.sheet_properties.tabColor = "3B1F6B"  # USPAP governance — purple
    ws46.sheet_properties.tabColor = "1F4E78"  # reference grounding — blue
    ws47.sheet_properties.tabColor = "7B2D00"  # comparative tax argument — amber-red
    ws48.sheet_properties.tabColor = "2D5A27"  # deductible expenses — green
    ws49.sheet_properties.tabColor = "C9973A"  # committee reconciliation — gold
    ws50.sheet_properties.tabColor = "1A4D2E"  # geographic tax check — dark green
    ws51.sheet_properties.tabColor = "374151"  # industrial asset separation — gray
    ws52.sheet_properties.tabColor = "1B2E4B"  # committee argument summary — dark navy
    ws53.sheet_properties.tabColor = "6B7280"  # visible text quality — muted gray

    # ── Class-specific sheets (Part F) ────────────────────────────────────────
    archetype = ctx.get("report_archetype", "residential_tax_appeal_summary")

    if archetype == "residential_tax_appeal_summary":
        wsr1 = wb.create_sheet("حساب الضريبة العقارية")
        wsr2 = wb.create_sheet("تحليل المغالاة")
        wsr3 = wb.create_sheet("مقارنة بيوع سكنية")
        wsr4 = wb.create_sheet("طريقة التكلفة السكنية")
        wsr5 = wb.create_sheet("أدلة الإتمام والإشغال")
        _sheet_residential_tax_calc(wsr1, ctx)
        _sheet_residential_overcharge(wsr2, ctx)
        _sheet_residential_sales_cmp(wsr3, ctx)
        _sheet_residential_cost(wsr4, ctx)
        _sheet_residential_completion(wsr5, ctx)
        for ws_r in (wsr1, wsr2, wsr3, wsr4, wsr5):
            ws_r.sheet_properties.tabColor = "1A4D2E"  # residential — dark green

    elif archetype == "non_residential_tax_appeal_summary":
        wsnr1 = wb.create_sheet("مقارنة غير سكنية")
        wsnr2 = wb.create_sheet("تحليل القيمة الإيجارية")
        wsnr3 = wb.create_sheet("عوامل الدور والواجهة")
        wsnr4 = wb.create_sheet("طريقة التكلفة غير السكنية")
        _sheet_non_residential_sales_cmp(wsnr1, ctx)
        _sheet_non_residential_rental(wsnr2, ctx)
        _sheet_non_residential_floor_factors(wsnr3, ctx)
        _sheet_non_residential_cost(wsnr4, ctx)
        for ws_nr in (wsnr1, wsnr2, wsnr3, wsnr4):
            ws_nr.sheet_properties.tabColor = "92400E"  # non-residential — amber

    elif archetype == "special_purpose_tax_appeal_narrative":
        wssp1 = wb.create_sheet("مكونات المنشأة")
        wssp2 = wb.create_sheet("تكلفة الإحلال")
        wssp3 = wb.create_sheet("الإهلاك")
        wssp4 = wb.create_sheet("تحليل المنشأة الخاصة")
        wssp5 = wb.create_sheet("ملخص القيمة الضريبية")
        wssp6 = wb.create_sheet("محددات وافتراضات خاصة")
        wssp7 = wb.create_sheet("مرجع تكلفة المصانع")
        _sheet_sp_components(wssp1, ctx)
        _sheet_sp_replacement_cost(wssp2, ctx)
        _sheet_sp_depreciation(wssp3, ctx)
        _sheet_sp_analysis(wssp4, ctx)
        _sheet_sp_value_summary(wssp5, ctx)
        _sheet_sp_limitations(wssp6, ctx)
        _sheet_factory_cost_guidance(wssp7, ctx)
        for ws_sp in (wssp1, wssp2, wssp3, wssp4, wssp5, wssp6):
            ws_sp.sheet_properties.tabColor = "1B2E4B"  # special-purpose — dark navy
        wssp7.sheet_properties.tabColor = "1A2E4A"  # factory cost ref — dark navy

    # ── Field mapping sheets ──────────────────────────────────────────────────
    ws_fm  = wb.create_sheet("ربط الحقول بالمصادر")
    ws_fmc = wb.create_sheet("تعارضات البيانات")
    _sheet_field_mappings(ws_fm, mapping_records, ctx)
    _sheet_field_mapping_conflicts(ws_fmc, ctx)
    ws_fm.sheet_properties.tabColor  = "1E40AF"  # field mapping — dark blue
    ws_fmc.sheet_properties.tabColor = "B91C1C"  # conflicts — dark red

    # Persist
    out_dir = _WB_DIR / request_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"tax_appeal_review_{request_id}.xlsx"
    wb.save(str(out_path))
    return out_path


# ── Workbook validator ────────────────────────────────────────────────────────

def _validate_tax_workbook_formulas_and_no_silent_blanks(workbook_path) -> list[str]:
    """Validate tax appeal workbook structure, formulas, and no-silent-blanks rule.

    Returns a list of error strings. Empty list = all checks pass.
    """
    import openpyxl
    errors: list[str] = []
    path = str(workbook_path)

    try:
        wb = openpyxl.load_workbook(path, data_only=False)
    except Exception as e:
        return [f"WORKBOOK_LOAD_FAIL: {e}"]

    # Check 1: first sheet is "مدخلات الطعن"
    if not wb.sheetnames or wb.sheetnames[0] != "مدخلات الطعن":
        errors.append(f"FIRST_SHEET_WRONG: expected 'مدخلات الطعن', got {wb.sheetnames[0] if wb.sheetnames else 'none'!r}")

    # Check 2: all required sheets exist
    for required in _REQUIRED_SHEETS:
        if required not in wb.sheetnames:
            errors.append(f"MISSING_SHEET: {required!r}")

    # Check 3: formula cells exist in "مدخلات الطعن" (cells starting with "=")
    if "مدخلات الطعن" in wb.sheetnames:
        ws = wb["مدخلات الطعن"]
        formula_cells = [
            c for row in ws.iter_rows() for c in row
            if isinstance(c.value, str) and c.value.startswith("=")
        ]
        if not formula_cells:
            errors.append("NO_FORMULA_CELLS: مدخلات الطعن has no formula cells (no '=...' cells)")

        # Check 4: deadline formula (+60) exists
        deadline_formulas = [c for c in formula_cells if "+60" in str(c.value) or "60" in str(c.value)]
        if not deadline_formulas:
            errors.append("MISSING_DEADLINE_FORMULA: no 60-day deadline formula found in مدخلات الطعن")

        # Check 5: transfer tax formula (0.025 or 2.5%)
        transfer_tax_formulas = [c for c in formula_cells if "0.025" in str(c.value)]
        if not transfer_tax_formulas:
            errors.append("MISSING_TRANSFER_TAX_FORMULA: no 0.025 (2.5%) formula found in مدخلات الطعن")

        # Check 6: overcharge formula (subtraction)
        overcharge_formulas = [c for c in formula_cells if "-B" in str(c.value) or "−" in str(c.value)]
        if not overcharge_formulas:
            errors.append("MISSING_OVERCHARGE_FORMULA: no subtraction formula found for overcharge")

        # Check 7: no silent blanks — a label cell exists but its value partner
        # (col 2) is None.  Two excluded categories:
        #   • MergedCell objects (non-primary half of a section-header merge)
        #   • Spacer rows where col-1 is also None (openpyxl creates Cell objects
        #     for every position inside the sheet bounding box, even unwritten rows)
        from openpyxl.cell.cell import MergedCell as _MergedCell
        blank_cells = []
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                if (
                    cell.column == 2
                    and cell.value is None
                    and not isinstance(cell, _MergedCell)
                    and ws.cell(row=cell.row, column=1).value is not None
                ):
                    blank_cells.append(cell.coordinate)
        if len(blank_cells) > 5:  # allow some empty formula result cells
            errors.append(f"SILENT_BLANKS: {len(blank_cells)} blank value cells in مدخلات الطعن (max 5 allowed)")

    # Check 8: annual and transfer sheets exist and are separate
    if "حساب الضريبة العقارية" not in wb.sheetnames:
        errors.append("MISSING_ANNUAL_SHEET: حساب الضريبة العقارية missing")
    if "حساب ضريبة التصرفات" not in wb.sheetnames:
        errors.append("MISSING_TRANSFER_SHEET: حساب ضريبة التصرفات missing")

    return errors
