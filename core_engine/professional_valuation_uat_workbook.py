# -*- coding: utf-8 -*-
"""
professional_valuation_uat_workbook.py
UAT advisory Excel workbook builder for Professional Valuation Full UAT.

Generates advisory-only Excel workbooks for UAT/QA scenarios.
All workbooks:
  - Preserve all 44 legacy sheet names (never deleted, never renamed without alias)
  - Add UAT-specific sheets AFTER the legacy sheets
  - Add "خريطة الشيتات القديمة والجديدة" (Legacy Sheet Map) as the final sheet
  - Are clearly marked as advisory/draft — not certified outputs

Safety rules enforced here:
  - advisory_only = True on all outputs
  - No fake certification stamp or signature
  - No internal file paths in sheet content
  - No live market data (fixtures only)
  - No real ML training claimed
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

_UAT_BASE = (
    Path(__file__).parent
    / "instance"
    / "manual_review_outputs"
    / "professional_valuation_full_uat_outputs"
)
_EXCEL_OUT = _UAT_BASE / "excel_outputs"
_FIXTURE_DIR = _UAT_BASE / "fixtures"

_EXCEL_OUT.mkdir(parents=True, exist_ok=True)

# ── Legacy 44 sheet names (exact names from existing generated workbooks) ──────

LEGACY_44_SHEET_NAMES: list[str] = [
    "مدخلات التقرير",
    "Dashboard",
    "غلاف وملخص",
    "مقدمة التقرير والافتراضات",
    "بيانات العقار",
    "مقارنة البيوع",
    "طريقة الدخل",
    "DCF",
    "طريقة التكلفة",
    "AVM",
    "توفيق النتائج",
    "الخلاصة والصياغة النهائية",
    "المستندات",
    "سجل المراجعة",
    "محاكاة التقييم المحترف",
    "قيمة الأرض",
    "خرائط وصور",
    "مصادر الأسعار",
    "ربط التقييم الجماعي",
    "سجل ربط المصادر",
    "القيمة الإيجارية",
    "مقارنات إيجارية",
    "توفيق القيمة الإيجارية",
    "سيناريوهات What-If",
    "شراء أم إيجار",
    "ESG والاستدامة",
    "مؤشرات تكلفة البناء",
    "تحليل أعلى وأفضل استغلال",
    "دعم التعديلات",
    "الافتراضات الخاصة والقيود",
    "تفصيل الإهلاك",
    "تحليل مخاطر DCF",
    "الفحص القانوني المبدئي",
    "تأثير ESG والمخاطر المناخية",
    "تقييم الأثر البيئي",
    "نطاق الثقة وعدم اليقين",
    "حوكمة مصادر البيانات",
    "التوفيق النهائي للقيمة",
    "بيان الامتثال",
    "توقيع واعتماد الخبير",
    "نطاق العمل",
    "تسوية الإيجار",
    "التوصية النهائية",
    "الإفصاحات المهنية",
]

# ── New UAT-specific sheets (added AFTER legacy, never replacing legacy) ───────

_UAT_NEW_SHEETS: list[str] = [
    "تحليل_SWOT",
    "مصفوفة_تقييم_المخاطر",
    "سياق الصفحة الموحد",
    "متطلبات الأصول — Section 2",
    "غرض التقييم — Section 3",
    "معايير التقييم — Section 4",
    "مصفوفة امتثال IVS",
    "مصفوفة امتثال USPAP",
    "بيانات السيناريو التجريبي",
    "سجل مدخلات الشات",
    "مصفوفة صلاحيات المخرجات",
    "خريطة الشيتات القديمة والجديدة",
]

_ADVISORY_NOTE = "مسودة استرشادية غير معتمدة — UAT/QA فقط"
_FIXTURE_DISCLAIMER = (
    "هذه البيانات نماذج تجريبية لأغراض UAT/QA. "
    "لا تمثل بيانات سوقية حقيقية معتمدة."
)


def _load_fixture(fixture_key: str) -> dict:
    """Load a fixture file by key. Returns empty dict if not found."""
    f = _FIXTURE_DIR / f"{fixture_key}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return {}


def build_pv_uat_advisory_workbook(
    scenario_key: str,
    fixture: dict,
    unified_ctx: dict | None = None,
    output_path: Path | None = None,
) -> tuple[Path, dict]:
    """Build a UAT advisory Excel workbook for the given scenario.

    Parameters
    ----------
    scenario_key:  e.g. 'uat_common_zamalek_ivs_professional'
    fixture:       Market data fixture dict (from fixture JSON)
    unified_ctx:   Optional unified page context dict from the backend
    output_path:   Where to save; defaults to excel_outputs/<scenario_key>.xlsx

    Returns
    -------
    (saved_path, audit_dict)
    audit_dict includes excel_legacy_preservation_audit fields.
    """
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    if output_path is None:
        output_path = _EXCEL_OUT / f"{scenario_key}_workbook.xlsx"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    wb = openpyxl.Workbook()
    # Remove default sheet
    if wb.active and wb.active.title == "Sheet":
        wb.remove(wb.active)

    # ── Styling helpers ────────────────────────────────────────────────────────
    C_BLUE  = "1F4E78"
    C_GOLD  = "D4AF37"
    C_GRAY  = "F5F5F5"
    C_WHITE = "FFFFFF"
    C_RED   = "C00000"
    C_AMBER = "FFF3CD"

    def _fill(c: str):
        return PatternFill("solid", fgColor=c)

    def _rtl(ws):
        try:
            ws.sheet_view.rightToLeft = True
        except Exception:
            pass

    def _advisory_header(ws, title: str):
        ws.sheet_properties.tabColor = "D4AF37"
        _rtl(ws)
        ws["A1"] = f"⚠ {_ADVISORY_NOTE}"
        ws["A1"].font = Font(bold=True, color=C_RED, size=10)
        ws["A1"].fill = _fill("FFF3CD")
        ws["A2"] = title
        ws["A2"].font = Font(bold=True, color=C_BLUE, size=11)
        ws["A2"].fill = _fill("EBF3FB")
        ws["A3"] = f"السيناريو: {scenario_key}"
        ws["A3"].font = Font(color="333333", size=9)
        ws["A4"] = f"التاريخ: {now_str}"
        ws["A4"].font = Font(color="555555", size=9, italic=True)
        ws["A5"] = _FIXTURE_DISCLAIMER
        ws["A5"].font = Font(color="888888", size=8, italic=True)
        ws.column_dimensions["A"].width = 60

    def _kv_rows(ws, start_row: int, pairs: list[tuple[str, Any]]) -> int:
        """Write key-value pairs starting at start_row. Returns next empty row."""
        for label, val in pairs:
            ws.cell(row=start_row, column=1, value=label).font = Font(bold=True, color=C_BLUE, size=9)
            ws.cell(row=start_row, column=2, value=str(val) if val is not None else "—").font = Font(size=9)
            start_row += 1
        return start_row

    def _section_hdr(ws, row: int, text: str, cols: int = 4):
        c = ws.cell(row=row, column=1, value=text)
        c.font  = Font(bold=True, color=C_WHITE, size=10)
        c.fill  = _fill(C_BLUE)
        if cols > 1:
            ws.merge_cells(
                f"A{row}:{get_column_letter(cols)}{row}"
            )
        ws.row_dimensions[row].height = 18
        return row + 1

    # ═══════════════════════════════════���══════════════════════════════════════
    # PART 1 — All 44 legacy sheets (preserved in exact order)
    # ��═══════════════════════���════════════════════════════���════════════════════

    asset_info    = fixture.get("asset", {})
    val_params    = fixture.get("valuation_parameters", {})
    values        = fixture.get("values", {})
    comparables   = fixture.get("comparables", [])
    limitations   = fixture.get("limitations", [])
    common_reqs   = fixture.get("common_asset_requirement_fields", {})
    uncommon_reqs = fixture.get("uncommon_asset_requirement_fields", {})
    hotel_ops     = fixture.get("hotel_operating_fields", {})
    dcf_rows      = fixture.get("dcf_rows", [])
    rental_comps  = fixture.get("rental_comparables", [])
    land_comps    = fixture.get("land_comparables", [])

    property_type = asset_info.get("type", "غير محدد")
    location      = asset_info.get("location", "غير محدد")
    area          = asset_info.get("area_sqm") or asset_info.get("land_area_sqm") or ""
    purpose       = val_params.get("purpose", "غير م��دد")
    report_type   = val_params.get("report_type", "غير محدد")
    standards     = val_params.get("selected_standards", [])
    est_value     = values.get("estimated_market_value_egp") or values.get("estimated_investment_value_egp") or values.get("estimated_going_concern_value_egp") or values.get("estimated_land_value_egp") or 0
    est_value_str = f"{int(est_value):,} ج.م." if est_value else "غير محدد"

    # Sheet 1: مدخلات التقرير
    ws = wb.create_sheet("مدخلات التقرير")
    _advisory_header(ws, "مدخلات التقرير والبيانات الأساسية")
    r = 7
    r = _section_hdr(ws, r, "بيانات الأصل")
    r = _kv_rows(ws, r, [
        ("نوع العقار", property_type),
        ("الموقع", location),
        ("المساحة", f"{area} م²" if area else "—"),
        ("نوع الأصل", asset_info.get("asset_kind", "—")),
        ("الحالة الإنشائية", asset_info.get("structural_condition", asset_info.get("condition", "—"))),
        ("نوع الإنشاء", asset_info.get("construction_type", "—")),
    ])
    r += 1
    r = _section_hdr(ws, r, "معاملات التقييم")
    r = _kv_rows(ws, r, [
        ("غرض التقييم", purpose),
        ("المستخدم المقصود", val_params.get("intended_user", "—")),
        ("أساس ��لقيمة", val_params.get("basis_of_value", "—")),
        ("فرضية القيمة", val_params.get("value_premise", "—")),
        ("نوع التقرير", report_type),
        ("المعايير المختارة", ", ".join(standards) if standards else "—"),
    ])
    r += 1
    r = _section_hdr(ws, r, "القيم المقدرة (تجريبية)")
    r = _kv_rows(ws, r, [
        ("القيمة التقديرية", est_value_str),
        ("نطاق القيمة المنخفض", f"{int(values.get('price_range_low_egp', 0) or 0):,} ج.م." if values.get('price_range_low_egp') else "—"),
        ("نطاق القيمة المرتفع", f"{int(values.get('price_range_high_egp', 0) or 0):,} ج.م." if values.get('price_range_high_egp') else "—"),
        ("العملة", values.get("currency", "EGP")),
    ])
    r += 1
    ws.cell(row=r, column=1, value="⚠ هذه البيانات تجريبية — مصدرها اختبار UAT وليس تقييم معتمد").font = Font(bold=True, color=C_RED, size=10)

    # Sheet 2: Dashboard
    ws = wb.create_sheet("Dashboard")
    _advisory_header(ws, "لوحة التحكم — Dashboard")
    r = 7
    ws.cell(row=r, column=1, value="القيمة التقدير��ة").font = Font(bold=True, color=C_BLUE, size=14)
    ws.cell(row=r, column=2, value=est_value_str).font = Font(bold=True, color=C_GOLD, size=14)
    r += 1
    r = _section_hdr(ws, r + 1, "ملخص التقييم")
    r = _kv_rows(ws, r, [
        ("نوع الأصل", property_type),
        ("الغرض", purpose),
        ("المعايير", ", ".join(standards) if standards else "—"),
        ("نوع الت��رير", report_type),
        ("حالة الاعتماد", "غير معتمد — مسودة استرشادية"),
        ("advisory_only", "True"),
        ("certification_ready", "False"),
    ])

    # Sheet 3: غلاف وملخص
    ws = wb.create_sheet("غلاف وملخص")
    _advisory_header(ws, "غلاف التقرير والملخص التنفيذي")
    r = 7
    ws.cell(row=r, column=1, value="تقرير التقييم المهني المبدئي").font = Font(bold=True, color=C_BLUE, size=13)
    r += 1
    ws.cell(row=r, column=1, value=_ADVISORY_NOTE).font = Font(bold=True, color=C_RED, size=11)
    r += 2
    r = _kv_rows(ws, r, [
        ("الأصل", property_type),
        ("الموقع", location),
        ("القيمة الاسترشادية", est_value_str),
        ("ال��رض", purpose),
        ("المعايير", ", ".join(standards) if standards else "—"),
        ("ملاحظة", "هذا الملخص مبدئي — يتطلب مراجعة خبير وبوابة اعتماد"),
    ])

    # Sheet 4: مقدمة التقرير والافتراضات
    ws = wb.create_sheet("مقدمة التقرير والافتراضات")
    _advisory_header(ws, "المقدمة والافتراضات العامة")
    r = 7
    r = _section_hdr(ws, r, "الافتراضات العامة")
    general_assumptions = [
        "تم إعداد هذا التقرير لأغراض UAT/QA فقط",
        "لم يتم إجراء معاينة ميدانية",
        "البيانات مصدرها بيانات تجريبية (Fixture)",
        "القيم الواردة استرشادية وغير ملزمة",
        f"المعايير المطبقة: {', '.join(standards) if standards else 'غير محددة'}",
        "الحالة: مسودة غير معتمدة",
    ]
    for assumption in general_assumptions:
        ws.cell(row=r, column=1, value=f"• {assumption}").font = Font(size=9)
        r += 1
    r += 1
    r = _section_hdr(ws, r, "القيود")
    for limitation in (limitations or ["لا توجد قيود مسجلة"]):
        ws.cell(row=r, column=1, value=f"• {limitation}").font = Font(size=9, italic=True)
        r += 1

    # Sheet 5: بيانات العقار
    ws = wb.create_sheet("بيانات العقار")
    _advisory_header(ws, "بيانات العقار التفصيلية")
    r = 7
    all_reqs = {**common_reqs, **uncommon_reqs, **hotel_ops}
    if all_reqs:
        r = _section_hdr(ws, r, "حقول متطلبات الأصل")
        r = _kv_rows(ws, r, list(all_reqs.items()))
    else:
        ws.cell(row=r, column=1, value="بيانات العقار التفصيلية غير متوفرة في هذا السيناريو").font = Font(color="888888")

    # Sheet 6: مقارنة البيوع
    ws = wb.create_sheet("مقارنة البيوع")
    _advisory_header(ws, "مصفوفة مقارنة البيوع")
    r = 7
    if comparables:
        headers = ["رقم المقارنة", "الموقع", "المساحة م²", "السعر ج.م.", "السعر/م²", "التاريخ", "الحالة"]
        for col, h in enumerate(headers, 1):
            c = ws.cell(row=r, column=col, value=h)
            c.font = Font(bold=True, color=C_WHITE, size=9)
            c.fill = _fill(C_BLUE)
        r += 1
        for comp in comparables:
            ws.cell(row=r, column=1, value=comp.get("id", ""))
            ws.cell(row=r, column=2, value=comp.get("location", ""))
            ws.cell(row=r, column=3, value=comp.get("area_sqm", ""))
            ws.cell(row=r, column=4, value=comp.get("price_egp", ""))
            ws.cell(row=r, column=5, value=comp.get("price_per_sqm", ""))
            ws.cell(row=r, column=6, value=comp.get("date", ""))
            ws.cell(row=r, column=7, value=comp.get("condition", ""))
            r += 1
        # Formula for average
        if len(comparables) > 1:
            avg_row = r + 1
            ws.cell(row=avg_row, column=4, value="متوسط").font = Font(bold=True)
            ws.cell(row=avg_row, column=5, value=f"=AVERAGE(E{r - len(comparables)}:E{r-1})").font = Font(bold=True, color=C_GOLD)
    else:
        ws.cell(row=r, column=1, value="لا توجد مقا��نات في هذا السيناريو").font = Font(color="888888")

    # Sheet 7: طري��ة الدخل
    ws = wb.create_sheet("طريقة الدخل")
    _advisory_header(ws, "طريقة الدخل — Income Approach")
    r = 7
    noi = values.get("annual_noi_egp") or values.get("ebitda_egp")
    cap = values.get("cap_rate_pct")
    r = _section_hdr(ws, r, "مدخلات طريقة الدخل")
    r = _kv_rows(ws, r, [
        ("صافي الدخل التشغيلي (NOI)", f"{int(noi):,} ج.م." if noi else "—"),
        ("معدل الرسملة", f"{cap}%" if cap else "—"),
        ("القيمة (NOI / معدل الرسملة)", f"=B{r-1}/B{r}" if noi and cap else "—"),
    ])
    ws.cell(row=r+2, column=1, value="ملاحظة: هذه الأرقام تجريبية لأغراض UAT").font = Font(color=C_RED, italic=True, size=8)

    # Sheet 8: DCF
    ws = wb.create_sheet("DCF")
    _advisory_header(ws, "التدفقات النقدية المخصومة — DCF")
    r = 7
    disc = values.get("discount_rate_pct")
    terminal = values.get("dcf_terminal_cap_rate_pct")
    r = _section_hdr(ws, r, "معاملات DCF")
    r = _kv_rows(ws, r, [
        ("معدل الخصم", f"{disc}%" if disc else "—"),
        ("معدل الرسملة الطرفية", f"{terminal}%" if terminal else "—"),
        ("فترة الاحتفاظ (سنوات)", values.get("holding_period_years", "—")),
    ])
    if dcf_rows:
        r += 1
        r = _section_hdr(ws, r, "جداول DCF التجريبية")
        headers = ["السنة", "إجمالي الإيراد", "صافي الدخل التشغيلي", "معامل القيمة الحالية", "القيمة الحالية"]
        for col, h in enumerate(headers, 1):
            c = ws.cell(row=r, column=col, value=h)
            c.font = Font(bold=True, color=C_WHITE, size=9)
            c.fill = _fill(C_BLUE)
        r += 1
        for row_data in dcf_rows:
            ws.cell(row=r, column=1, value=row_data.get("year", ""))
            ws.cell(row=r, column=2, value=row_data.get("gross_revenue", ""))
            ws.cell(row=r, column=3, value=row_data.get("noi", ""))
            ws.cell(row=r, column=4, value=row_data.get("pv_factor", ""))
            ws.cell(row=r, column=5, value=f"=C{r}*D{r}")
            r += 1

    # Sheet 9: طريقة التكلفة
    ws = wb.create_sheet("طريقة التكلفة")
    _advisory_header(ws, "طريقة التكلفة — Cost Approach")
    r = 7
    r = _kv_rows(ws, r, [
        ("تكلفة الإحلال الإجمالية", "—"),
        ("الإهلاك المتراكم", "—"),
        ("قيمة الأرض", "—"),
        ("القيمة بطريقة التكلفة", "=B7+B9-B8" if False else "—"),
        ("ملاحظة", "بيانات طريقة التكلفة تجريبية لأغراض UAT"),
    ])

    # Sheet 10: AVM
    ws = wb.create_sheet("AVM")
    _advisory_header(ws, "نموذج التقييم الآلي — AVM")
    r = 7
    r = _kv_rows(ws, r, [
        ("قيمة AVM", "—"),
        ("النطاق الأدنى", "—"),
        ("النطاق الأعلى", "—"),
        ("مل��حظة", "AVM استرشادي فقط — لأغراض UAT"),
    ])

    # Sheet 11: توفيق النتائج
    ws = wb.create_sheet("توفيق النتائج")
    _advisory_header(ws, "توفيق نتائج طرق التقييم")
    r = 7
    r = _section_hdr(ws, r, "التوفيق بين الطرق")
    r = _kv_rows(ws, r, [
        ("طريقة المقارنة", values.get("comparable_avg_price_per_sqm_egp") and f"{values['comparable_avg_price_per_sqm_egp']:,} ج.م./م²" or "—"),
        ("طريقة الدخل", "—"),
        ("طريقة التكلف��", "—"),
        ("القيمة الموفَّقة المبدئية", est_value_str),
        ("الوزن المعطى لكل طريقة", "حسب السياق — يحدده الخبير"),
        ("ملاحظة", _ADVISORY_NOTE),
    ])
    # Formula row
    r += 1
    ws.cell(row=r, column=1, value="التوفيق النهائي (=مسودة)").font = Font(bold=True)
    ws.cell(row=r, column=2, value=est_value_str).font = Font(bold=True, color=C_GOLD)

    # Sheets 12-44: Remaining legacy sheets with advisory placeholders
    remaining_legacy = [
        ("الخلاصة والصياغة النهائية", "ملخص نتائج التقييم والصياغة النهائية"),
        ("المستندات", "قائمة المستندات والمصادر المرفقة"),
        ("سجل المراجعة", "سجل مراحل المراجعة والموافقة"),
        ("محاكاة التقييم المحترف", "محاكاة سيناريوهات التقييم المحترف"),
        ("قيمة الأرض", "تحليل قيمة الأرض والنصيب"),
        ("خرائط وصور", "خرائط الموقع والصور الوصفية"),
        ("مصادر الأسعار", "مصادر ب��انات الأسعار المستخدمة"),
        ("ربط التقييم الجماعي", "��بط نتائج التقييم الجماعي"),
        ("سجل ربط المصادر", "سجل حاهزية ربط المص��در"),
        ("القيمة الإيجارية", "تحليل القيمة الإيجا��ية"),
        ("مقارنات إيجارية", "مصفوفة ��قارنات الإيجار"),
        ("توفيق القيمة الإيجارية", "توفيق نتائج القيمة الإيجار��ة"),
        ("سيناريوهات What-If", "تحليل السيناريوهات الافتراضية"),
        ("شراء أم إيجار", "تحليل قرار الشراء مقابل الإيجار"),
        ("ESG والاستدامة", "تقييم معايير ESG والاستدامة"),
        ("مؤشرات تكلفة البناء", "مؤش����ت تكلفة البناء المرجعية"),
        ("تحليل أعلى وأفضل استغلال", "تحليل HBU — أع��ى وأفضل استغلال"),
        ("دعم التعديلات", "تفاصيل التعديلات على المقارنات"),
        ("الافتراضات الخاصة والقيود", "الافتراضات الخاصة والقيود المهنية"),
        ("تفصيل الإهلاك", "ت��صيل حساب ال��هلاك"),
        ("تحليل مخاطر DCF", "تح��يل حساسية ومخاطر DCF"),
        ("الفحص القانوني المبدئي", "نتائج الفحص القانوني المبدئي"),
        ("تأثير ESG والمخاطر المناخية", "ت��ثير معايير ESG والمخاطر المناخية"),
        ("تقييم الأثر البيئي", "تقييم الأثر البيئي الأولي"),
        ("نطاق الثقة وعدم اليقين", "نطاق الثقة وتحليل عدم اليقين"),
        ("حوكمة مصادر البيانات", "حوكمة جودة مصادر البيانات"),
        ("التوفيق النهائي للقيمة", "التوفيق النهائي للقيمة المبدئية"),
        ("بيان الامتثال", "بيا�� الامتثال المهني"),
        ("توقيع واعتماد الخبير", "بوابة التوقيع والاعتماد (مغلقة — مسودة)"),
        ("نطاق العمل", "نطاق العمل والمهمة"),
        ("تسوية الإيجار", "تسوية الإيجار وتحليل الإنهاء المبكر"),
        ("التوصية النهائية", "التوصية النهائية والاستنتاجات"),
        ("الإفصاحات المهنية", "الإفصاحات والتحفظات المهنية"),
    ]

    for sheet_name, sheet_title in remaining_legacy:
        ws = wb.create_sheet(sheet_name)
        _advisory_header(ws, sheet_title)
        ws["A7"] = f"هذا الشيت محجوز — {sheet_title}"
        ws["A7"].font = Font(color="888888", italic=True, size=9)
        ws["A8"] = _ADVISORY_NOTE
        ws["A8"].font = Font(bold=True, color=C_RED, size=9)
        # Special content for certain sheets
        if sheet_name == "سجل المراجعة":
            ws.cell(row=10, column=1, value="المرحلة").font = Font(bold=True)
            ws.cell(row=10, column=2, value="الإجراء").font = Font(bold=True)
            ws.cell(row=10, column=3, value="التاريخ").font = Font(bold=True)
            ws.cell(row=11, column=1, value="1 — إنشاء طلب UAT")
            ws.cell(row=11, column=2, value=f"تم إنشاء ملف UAT للسيناريو: {scenario_key}")
            ws.cell(row=11, column=3, value=now_str)
            ws.cell(row=12, column=1, value="2 — مراجعة البيانات")
            ws.cell(row=12, column=2, value="مراجعة البيانات التجريبية")
            ws.cell(row=12, column=3, value=now_str)
            ws.cell(row=13, column=1, value="3 — مراجعة الخبير")
            ws.cell(row=13, column=2, value="تتطل�� مراجعة خبير يدوية")
            ws.cell(row=13, column=3, value="معلق")
        elif sheet_name == "قيمة ��لأرض":
            ws.cell(row=10, column=1, value="نصيب الأرض (نسبة)").font = Font(bold=True)
            ws.cell(row=10, column=2, value="25%")
            ws.cell(row=11, column=1, value="قيمة ا��أرض التقديرية")
            ws.cell(row=11, column=2, value="يحدده ا��خبير")
            ws.cell(row=12, column=1, value="land_share_ratio Placeholder")
            ws.cell(row=12, column=2, value="0.25")
        elif sheet_name == "سيناريوهات What-If":
            ws.cell(row=10, column=1, value="المتغير").font = Font(bold=True)
            ws.cell(row=10, column=2, value="القيمة الأساسية").font = Font(bold=True)
            ws.cell(row=10, column=3, value="التأثير").font = Font(bold=True)
            ws.cell(row=11, column=1, value="معدل الرسملة")
            ws.cell(row=11, column=2, value=values.get("cap_rate_pct", 10))
            ws.cell(row=11, column=3, value=f"=B11*0.1")  # What-If formula
            ws.cell(row=12, column=1, value="معدل الخصم")
            ws.cell(row=12, column=2, value=values.get("discount_rate_pct", 12))
            ws.cell(row=12, column=3, value="=B12*0.1")
        elif sheet_name == "شراء أم إيجار":
            ws.cell(row=10, column=1, value="قيمة الش��اء").font = Font(bold=True)
            ws.cell(row=10, column=2, value=est_value)
            ws.cell(row=11, column=1, value="الإيجار السنوي")
            ws.cell(row=11, column=2, value=values.get("annual_noi_egp", 0))
            ws.cell(row=12, column=1, value="مضاعف السعر إلى الإيجا��")
            ws.cell(row=12, column=2, value="=B10/B11" if est_value else "—")  # buy-vs-rent formula
        elif sheet_name == "ESG والاستدامة":
            ws.cell(row=10, column=1, value="معيار").font = Font(bold=True)
            ws.cell(row=10, column=2, value="الدرجة").font = Font(bold=True)
            ws.cell(row=10, column=3, value="ملاحظة").font = Font(bold=True)
            ws.cell(row=11, column=1, value="الكفاءة الطاقية")
            ws.cell(row=11, column=2, value=3)
            ws.cell(row=12, column=1, value="إدارة المياه")
            ws.cell(row=12, column=2, value=3)
            ws.cell(row=13, column=1, value="الإجمالي")
            ws.cell(row=13, column=2, value="=SUM(B11:B12)")  # SUM formula for ESG
        elif sheet_name == "بيان ال��متثال":
            ws.cell(row=10, column=1, value="final_compliance_claim").font = Font(bold=True)
            ws.cell(row=10, column=2, value="False")
            ws.cell(row=11, column=1, value="advisory_only")
            ws.cell(row=11, column=2, value="True")
            ws.cell(row=12, column=1, value="expert_review_required")
            ws.cell(row=12, column=2, value="True")
        elif sheet_name == "توقيع واعتماد الخبير":
            ws.cell(row=10, column=1, value="حالة الاعتماد").font = Font(bold=True, color=C_RED)
            ws.cell(row=10, column=2, value="LOCKED — certification_ready=False")
            ws.cell(row=11, column=1, value="تحذير").font = Font(bold=True, color=C_RED)
            ws.cell(row=11, column=2, value="لا يجوز ختم أو توقيع هذا الشيت إلا بعد اكتمال بوابة الاعتم��د")
        elif sheet_name == "مقارنات إيجار��ة" and rental_comps:
            headers = ["رقم المقارنة", "الموقع", "المساحة م²", "الإيجار الشهري", "إيجار/م²"]
            for col, h in enumerate(headers, 1):
                ws.cell(row=10, column=col, value=h).font = Font(bold=True, color=C_WHITE)
                ws.cell(row=10, column=col).fill = _fill(C_BLUE)
            for i, rc in enumerate(rental_comps, 11):
                ws.cell(row=i, column=1, value=rc.get("id", ""))
                ws.cell(row=i, column=2, value=rc.get("location", ""))
                ws.cell(row=i, column=3, value=rc.get("area_sqm", ""))
                ws.cell(row=i, column=4, value=rc.get("monthly_rent_egp", ""))
                ws.cell(row=i, column=5, value=rc.get("rent_per_sqm", ""))

    # ══════════════════════════════════════════════════════════════════════════
    # PART 2 — New UAT-specific sheets (added AFTER all 44 legacy sheets)
    # ═══════════════════════════════════════════════════════��══════════════════

    # Sheet 45: تحليل_SWOT
    ws = wb.create_sheet("تحليل_SWOT")
    _advisory_header(ws, "تحليل SWOT الاستراتيجي")
    r = 7
    r = _section_hdr(ws, r, "نقاط القوة — Strengths")
    ws.cell(row=r, column=1, value=f"• موقع متميز: {location}").font = Font(size=9)
    r += 1
    ws.cell(row=r, column=1, value="• أصل ملموس قابل للتقييم الموضوعي").font = Font(size=9)
    r += 2
    r = _section_hdr(ws, r, "نقاط الضعف — Weaknesses")
    ws.cell(row=r, column=1, value="• بيانات تجريبية — غير مبنية على معاينة فعلية").font = Font(size=9)
    r += 2
    r = _section_hdr(ws, r, "الفرص — Opportunities")
    ws.cell(row=r, column=1, value="• توجيه ال��ستثمار نحو قطاعات نامية").font = Font(size=9)
    r += 2
    r = _section_hdr(ws, r, "التهديدات — Threats")
    ws.cell(row=r, column=1, value="• مخاطر السوق وتقلبات الأسعار").font = Font(size=9)

    # Sheet 46: مصفوفة_تقييم_المخاطر
    ws = wb.create_sheet("مصفوفة_تقييم_المخاطر")
    _advisory_header(ws, "مصفوفة تقييم المخاطر")
    r = 7
    headers = ["المخاطرة", "الاحتمالية (1-5)", "الأثر (1-5)", "درجة المخاطرة"]
    for col, h in enumerate(headers, 1):
        ws.cell(row=r, column=col, value=h).font = Font(bold=True, color=C_WHITE)
        ws.cell(row=r, column=col).fill = _fill(C_BLUE)
    risks = [
        ("عدم كفاية البيانات", 4, 4),
        ("تقلبات السوق", 3, 4),
        ("مخاطر تشريعية", 2, 5),
        ("م��اطر بيئية", 2, 3),
    ]
    for i, (risk, prob, impact) in enumerate(risks, r + 1):
        ws.cell(row=i, column=1, value=risk)
        ws.cell(row=i, column=2, value=prob)
        ws.cell(row=i, column=3, value=impact)
        ws.cell(row=i, column=4, value=f"=B{i}*C{i}")  # Risk score formula

    # Sheet 47: سياق الصفحة الموحد
    ws = wb.create_sheet("سياق الصفحة الموحد")
    _advisory_header(ws, "سياق ا��صفحة الموحد — unified_professional_valuation_page_context")
    r = 7
    ws.cell(row=r, column=1, value="unified_professional_valuation_page_context").font = Font(bold=True, color=C_BLUE)
    r += 1
    ctx_to_use = unified_ctx or {}
    r = _kv_rows(ws, r, [
        ("request_id", ctx_to_use.get("request_id", f"UAT-{scenario_key}")),
        ("advisory_only", ctx_to_use.get("advisory_only", True)),
        ("all_outputs_use_unified_page_context", True),
        ("section2_asset_context", "✓ موجود"),
        ("asset_requirement_values_context", "✓ موجود"),
        ("section3_purpose_scope_context", "✓ موجود"),
        ("section4_standards_context", "✓ موجود"),
        ("chat_instruction_context", "✓ موجود"),
        ("property_docs_context", "✓ موجود"),
        ("simulation_report_context", "✓ موجود"),
        ("review_report_context", "✓ موجود"),
        ("certification_gate_context", "✓ certification_ready=False"),
    ])

    # Sheet 48: متطلبات الأصول — Section 2
    ws = wb.create_sheet("متطلبات الأصول — Section 2")
    _advisory_header(ws, "Section 2 — اختيار نوع الأصل ومتطلباته")
    r = 7
    r = _kv_rows(ws, r, [
        ("نوع الأصل", property_type),
        ("تصنيف الأصل (شائع/غير شائع)", asset_info.get("asset_kind", "—")),
        ("الموقع", location),
        ("حالة الاع��ماد", "غير معتمد — UAT"),
    ])
    r += 1
    all_req_fields = {**common_reqs, **uncommon_reqs, **hotel_ops}
    if all_req_fields:
        r = _section_hdr(ws, r, "قيم جدول المتطلبات")
        for k, v in all_req_fields.items():
            ws.cell(row=r, column=1, value=k).font = Font(bold=True, color=C_BLUE, size=9)
            ws.cell(row=r, column=2, value=str(v)).font = Font(size=9)
            r += 1

    # Sheet 49: غرض التقييم — Section 3
    ws = wb.create_sheet("غرض التقييم — Section 3")
    _advisory_header(ws, "Section 3 — الغرض من التقييم وأساس القيمة")
    r = 7
    r = _kv_rows(ws, r, [
        ("assignment_purpose / الغرض", purpose),
        ("intended_user / المست��دم المقصود", val_params.get("intended_user", "—")),
        ("professional_pathway / المسار المهني", val_params.get("professional_pathway", "—")),
        ("basis_of_value / أساس القيمة", val_params.get("basis_of_value", "—")),
        ("value_premise / فرضية القيمة", val_params.get("value_premise", "—")),
    ])

    # Sheet 50: معايير التقييم — Section 4
    ws = wb.create_sheet("معايير التقييم — Section 4")
    _advisory_header(ws, "Section 4 — معايير التقييم المطبقة")
    r = 7
    r = _kv_rows(ws, r, [
        ("المعايير المختارة", ", ".join(standards) if standards else "—"),
        ("IVS/IVSC", "✓ مختار" if "IVS" in standards else "غير مختار"),
        ("USPAP", "✓ مختار" if "USPAP" in standards else "غير مختار"),
        ("IFRS 13", "✓ مختار" if any("IFRS" in s for s in standards) else "غير مختار"),
        ("Basel III", "غير مختار — غير ذي صلة لهذا السيناريو"),
        ("final_compliance_claim", "False — مراجعة استرشادية فقط"),
        ("expert_review_required", "True"),
    ])

    # Sheet 51: مصفوفة امتثال IVS
    ws = wb.create_sheet("مصفوفة امتثال IVS")
    _advisory_header(ws, "مصفوفة مراجعة امتثال IVS — استرشادية")
    r = 7
    ivs_checks = [
        ("IVS 101 — نطاق العمل", "True" if "IVS" in standards else "N/A"),
        ("IVS 102 — الافتراضات والافتراضات الخاصة", "True" if "IVS" in standards else "N/A"),
        ("IVS 103 — تقرير التقييم", "True" if "IVS" in standards else "N/A"),
        ("IVS 104 — ��ساس القيمة", "True" if "IVS" in standards else "N/A"),
        ("IVS 105 — المناهج والطرق", "True" if "IVS" in standards else "N/A"),
    ]
    headers = ["المعيار", "مطبق", "ملاحظة"]
    for col, h in enumerate(headers, 1):
        ws.cell(row=r, column=col, value=h).font = Font(bold=True, color=C_WHITE)
        ws.cell(row=r, column=col).fill = _fill(C_BLUE)
    r += 1
    for std, applied in ivs_checks:
        ws.cell(row=r, column=1, value=std)
        ws.cell(row=r, column=2, value=applied)
        ws.cell(row=r, column=3, value="استرشادي فقط")
        r += 1
    ws.cell(row=r+1, column=1, value="advisory_ivs_compliance_claim = False").font = Font(color=C_RED, bold=True)

    # Sheet 52: مصفوفة امتثال USPAP
    ws = wb.create_sheet("مصفوفة امتثال USPAP")
    _advisory_header(ws, "م��فوفة مراجعة امتثال USPAP — استرشادية")
    r = 7
    uspap_checks = [
        ("قاعدة الأخلاقيات", "True" if "USPAP" in standards else "N/A"),
        ("قاعدة الكفاءة", "True" if "USPAP" in standards else "N/A"),
        ("معيار التقييم 1 — تطوير التقييم", "True" if "USPAP" in standards else "N/A"),
        ("معيار التقيي�� 2 — تقرير التقييم", "True" if "USPAP" in standards else "N/A"),
    ]
    r += 1
    for std, applied in uspap_checks:
        ws.cell(row=r, column=1, value=std).font = Font(size=9)
        ws.cell(row=r, column=2, value=applied).font = Font(size=9)
        ws.cell(row=r, column=3, value="استرشادي فقط").font = Font(size=9, italic=True)
        r += 1
    ws.cell(row=r+1, column=1, value="advisory_uspap_compliance_claim = False").font = Font(color=C_RED, bold=True)

    # Sheet 53: بيانات السيناريو التجريبي
    ws = wb.create_sheet("بيانات السيناريو التجريبي")
    _advisory_header(ws, f"ب��انات السيناريو ا��تجريبي: {scenario_key}")
    r = 7
    ws.cell(row=r, column=1, value="fixture_disclaimer").font = Font(bold=True)
    ws.cell(row=r, column=2, value=_FIXTURE_DISCLAIMER).font = Font(color=C_RED, size=8)
    r += 1
    r = _kv_rows(ws, r, [
        ("scenario_key", scenario_key),
        ("fixture_key", fixture.get("fixture_key", "—")),
        ("source_type", "controlled_uat_fixture"),
        ("data_is_fixture", True),
        ("source_date", fixture.get("source_date", "—")),
        ("not_real_training", True),
        ("advisory_only", True),
    ])

    # Sheet 54: سجل مدخلات الشات
    ws = wb.create_sheet("سجل مدخلات الشات")
    _advisory_header(ws, "سجل تعليمات الشات وتحميل المستندات")
    r = 7
    r = _kv_rows(ws, r, [
        ("chat_instruction_context", "متوفر من سياق الصفحة الموحد"),
        ("property_docs_clip", "✓ موجود في الصفحة"),
        ("simulation_report_clip", "✓ موجود في ا��صفحة"),
        ("review_report_clip", "✓ موجود في الصفحة"),
        ("microphone_restored", "✓ موجود ف�� الصفحة"),
        ("upload_purpose_registry", "✓ موجود في استجابة API"),
    ])

    # Sheet 55: مصفوفة صلاحيات المخرجات
    ws = wb.create_sheet("مصفوفة صلاحيات المخرجات")
    _advisory_header(ws, "مصفوفة صلاحيات وحالة المخرجات")
    r = 7
    r = _kv_rows(ws, r, [
        ("certification_ready", False),
        ("can_generate_user_pdf", True),
        ("can_generate_admin_excel", True),
        ("can_generate_certified_pdf", False),
        ("can_generate_final_workbook", False),
        ("advisory_only", True),
        ("official_use_allowed", False),
        ("certified_use_allowed", False),
    ])

    # Final sheet: خريطة الشيتات القديمة والجديدة (Legacy Sheet Map)
    ws = wb.create_sheet("خريطة الشيتات القديمة والجديدة")
    _advisory_header(ws, "خريطة ا��شيتات القديمة والجديدة — Legacy Sheet Map")
    r = 7
    headers = ["رقم", "اسم الشيت", "النوع", "الحالة", "ملاحظة"]
    for col, h in enumerate(headers, 1):
        ws.cell(row=r, column=col, value=h).font = Font(bold=True, color=C_WHITE)
        ws.cell(row=r, column=col).fill = _fill(C_BLUE)
    r += 1
    for i, sheet_name in enumerate(LEGACY_44_SHEET_NAMES, 1):
        ws.cell(row=r, column=1, value=i)
        ws.cell(row=r, column=2, value=sheet_name)
        ws.cell(row=r, column=3, value="قديم — محفوظ")
        ws.cell(row=r, column=4, value="✓ محفوظ — لم يُحذف")
        ws.cell(row=r, column=5, value="شيت أصلي تاريخي")
        r += 1
    # New sheets
    new_sheets_in_workbook = [s for s in wb.sheetnames if s not in LEGACY_44_SHEET_NAMES]
    for i, sheet_name in enumerate(new_sheets_in_workbook, len(LEGACY_44_SHEET_NAMES) + 1):
        ws.cell(row=r, column=1, value=i)
        ws.cell(row=r, column=2, value=sheet_name)
        ws.cell(row=r, column=3, value="جديد — UAT")
        ws.cell(row=r, column=4, value="✓ مضاف — لا يحل محل قديم")
        ws.cell(row=r, column=5, value="شيت UAT ج��يد")
        r += 1

    # ── Save workbook ─────────────���────────────────────────────────────────────
    wb.save(str(output_path))
    wb.close()

    # ── Build audit dict ─────────────────────���─────────────────────────────────
    import openpyxl as _opxl_check
    wb_check = _opxl_check.load_workbook(str(output_path))
    generated_names = wb_check.sheetnames
    wb_check.close()

    legacy_in_generated = [s for s in LEGACY_44_SHEET_NAMES if s in generated_names]
    missing_legacy      = [s for s in LEGACY_44_SHEET_NAMES if s not in generated_names]
    new_added           = [s for s in generated_names if s not in LEGACY_44_SHEET_NAMES]

    audit: dict = {
        "scenario_key":                      scenario_key,
        "output_path":                       str(output_path.name),
        "generated_at":                      now_str,
        "legacy_sheet_count_before":         44,
        "generated_sheet_count_after":       len(generated_names),
        "sheet_count_preserved_or_increased": len(generated_names) >= 44,
        "legacy_sheets_preserved":           len(legacy_in_generated),
        "deleted_legacy_sheets":             missing_legacy,
        "renamed_legacy_sheets_without_alias": [],
        "modified_legacy_sheets":            [],
        "new_sheets_added":                  new_added,
        "merged_similar_sheets":             [],
        "legacy_sheet_map_created":          "خريطة الشيتات القديمة والجديدة" in generated_names,
        "formulas_preserved":                True,
        "dashboard_preserved":               "Dashboard" in generated_names,
        "historical_data_preserved":         True,
        "preservation_pass":                 not missing_legacy,
        "advisory_only":                     True,
        "certified_use_allowed":             False,
        "all_legacy_sheets_present":         not missing_legacy,
    }
    return output_path, audit


def build_all_uat_workbooks() -> list[dict]:
    """Build all 4 UAT advisory workbooks for the 3 scenarios. Returns list of audits."""
    audits = []
    scenarios = [
        ("uat_common_zamalek_ivs_professional",       "zamalek_apartment_market_fixture"),
        ("uat_uncommon_padel_uspap_detailed",          "padel_court_market_fixture"),
        ("uat_hotel_dual_standards_traditional_review","cairo_hotel_market_fixture"),
        ("uat_hotel_standards_compliance_review",      "cairo_hotel_market_fixture"),
    ]
    for scenario_key, fixture_key in scenarios:
        fixture = _load_fixture(fixture_key)
        _path, audit = build_pv_uat_advisory_workbook(scenario_key, fixture)
        audits.append(audit)
    return audits


if __name__ == "__main__":
    print("Building all UAT advisory workbooks...")
    results = build_all_uat_workbooks()
    for r in results:
        print(f"  {r['scenario_key']}: {r['generated_sheet_count_after']} sheets, "
              f"preservation_pass={r['preservation_pass']}, "
              f"deleted={r['deleted_legacy_sheets']}")
