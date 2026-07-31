"""
professional_valuation_arabic_excel_legacy_generator.py
يولد ملفات Excel إدارية تعتمد على النموذج القديم (Legacy Template).
النموذج المرجعي الأول:  Report_ES_GRAND_FINAL_v4.xlsm (44 ورقة)
النموذج المرجعي الثاني: Report_ES_ULTRA.xlsm         (26 ورقة)

المنهجية:
 1. نسخ الملف القديم إلى موقع الإخراج (shutil.copy2)
 2. فتحه بـ openpyxl (keep_vba=True للحفاظ على الماكرو حيثما أمكن)
 3. إضافة أوراق ملخص عربية جديدة فقط
 4. حفظ بامتداد .xlsm

arabic_visible_labels=True | uses_legacy_template=True | admin_excel_internal_only=True
advisory_only=True | not_real_training=True
"""
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from professional_valuation_arabic_report_examples import (
    SUBJECT_AR, INCOME_AR, COST_AR, AVM_AR, RECONCILIATION_AR,
    INDICATED_MARKET_VALUE, DATA_INPUTS_AR, METHOD_SELECTION_AR,
    ADVISORY_NOTE_AR, RECONCILIATION_SCORECARD_AR, RISKS_AR, SCENARIOS_AR,
)

try:
    from openpyxl import load_workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    _OPENPYXL_OK = True
except ImportError:
    _OPENPYXL_OK = False

_GENERATED_AT = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

# ── Paths to legacy reference files ──────────────────────────────────────────
_LEGACY_ROOT = (
    Path(__file__).parent
    / "instance" / "manual_review_outputs"
    / "professional_valuation_full_page_uat_legacy_excel_visual_review"
    / "legacy_references"
)
LEGACY_GRAND_FINAL = _LEGACY_ROOT / "Report_ES_GRAND_FINAL_v4.xlsm"
LEGACY_ULTRA       = _LEGACY_ROOT / "Report_ES_ULTRA.xlsm"

# Fallback path
_LEGACY_ROOT2 = (
    Path(__file__).parent
    / "instance" / "manual_review_outputs"
    / "professional_valuation_legacy_report_output_rebuild"
    / "legacy_references"
)
LEGACY_GRAND_FINAL2 = _LEGACY_ROOT2 / "Report_ES_GRAND_FINAL_v4.xlsm"
LEGACY_ULTRA2       = _LEGACY_ROOT2 / "Report_ES_ULTRA.xlsm"

_NAVY  = "1A3A5C"
_GOLD  = "D4AF37"
_LIGHT = "E4EDF5"
_WARN  = "FFF3CD"
_GREEN = "D4EDDA"
_WHITE = "FFFFFF"


def _resolve_legacy() -> Path:
    for p in [LEGACY_GRAND_FINAL, LEGACY_GRAND_FINAL2]:
        if p.exists():
            return p
    raise FileNotFoundError(
        "لم يُعثر على ملف Report_ES_GRAND_FINAL_v4.xlsm في المسارات المتوقعة.\n"
        f"  {LEGACY_GRAND_FINAL}\n  {LEGACY_GRAND_FINAL2}"
    )


def _hdr(ws, row: int, col: int, value: str, bold: bool = True,
         bg: str = _NAVY, fg: str = _WHITE, size: int = 10) -> None:
    cell = ws.cell(row=row, column=col, value=value)
    cell.font  = Font(name="Calibri", bold=bold, color=fg, size=size)
    cell.fill  = PatternFill("solid", fgColor=bg)
    cell.alignment = Alignment(horizontal="right", vertical="center", wrap_text=True)


def _cell(ws, row: int, col: int, value, bold: bool = False,
          italic: bool = False, bg: str = None, size: int = 10) -> None:
    cell = ws.cell(row=row, column=col, value=value)
    cell.font = Font(name="Calibri", bold=bold, italic=italic, size=size)
    if bg:
        cell.fill = PatternFill("solid", fgColor=bg)
    cell.alignment = Alignment(horizontal="right", vertical="center", wrap_text=True)


def _kv_block(ws, start_row: int, pairs: list[tuple], label_bg: str = _LIGHT) -> int:
    row = start_row
    for k, v in pairs:
        _cell(ws, row, 1, k, bold=True, bg=label_bg)
        _cell(ws, row, 2, str(v) if v is not None else "")
        row += 1
    return row


def _table(ws, start_row: int, headers: list[str], rows: list[list]) -> int:
    r = start_row
    for c, h in enumerate(headers, 1):
        _hdr(ws, r, c, h)
    r += 1
    for data_row in rows:
        bg = _LIGHT if (r - start_row - 1) % 2 == 0 else None
        for c, val in enumerate(data_row, 1):
            _cell(ws, r, c, str(val) if val is not None else "", bg=bg)
        r += 1
    return r + 1


def _add_arabic_summary_sheet(wb, report_label: str, report_key: str, rec: dict) -> None:
    """أضف ورقة ملخص عربية جديدة (لا تحذف الأوراق القديمة)."""
    sheet_name = f"ملخص التقرير — {report_label}"[:31]
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]
    ws = wb.create_sheet(title=sheet_name)
    ws.column_dimensions["A"].width = 35
    ws.column_dimensions["B"].width = 50
    ws.sheet_view.rightToLeft = True

    _hdr(ws, 1, 1, f"ملخص التقرير — {report_label}", bg=_NAVY, fg=_GOLD, size=13)
    ws.merge_cells("A1:B1")
    ws.row_dimensions[1].height = 28

    _hdr(ws, 2, 1, "مسودة استشارية — للإدارة والخبير فقط — لا تُرسل للمستخدم",
         bg=_WARN, fg="8A5700", size=9)
    ws.merge_cells("A2:B2")

    r = _kv_block(ws, 4, [
        ("نوع التقرير",            report_label),
        ("مفتاح التقرير",          report_key),
        ("رقم الطلب",              SUBJECT_AR["request_id"]),
        ("العقار",                 SUBJECT_AR["property_address"]),
        ("نوع العقار",             SUBJECT_AR["property_type"]),
        ("المساحة الإجمالية",      f'{SUBJECT_AR["gross_floor_area_m2"]} م²'),
        ("الغرض",                  SUBJECT_AR["purpose"]),
        ("أساس القيمة",            SUBJECT_AR["basis_of_value"]),
        ("تاريخ التقييم",          SUBJECT_AR["valuation_date"]),
        ("العميل",                 SUBJECT_AR["client"]),
        ("العملة",                 SUBJECT_AR["currency"]),
        ("تاريخ الإصدار",          _GENERATED_AT),
        ("النموذج المرجعي",        "Report_ES_GRAND_FINAL_v4.xlsm"),
        ("advisory_only",          "True"),
        ("fake_approval_created",  "False"),
        ("certification_ready",    "False"),
        ("admin_excel_internal_only", "True"),
    ])

    r += 1
    _hdr(ws, r, 1, "نتائج التوفيق", bg=_NAVY, fg=_WHITE)
    _hdr(ws, r, 2, "القيمة", bg=_NAVY, fg=_WHITE)
    r += 1
    reconciliation_rows = [
        ("مؤشر أسلوب السوق / Market Approach",
         f'{rec["market_approach_value"]:,} SAR (وزن {rec["market_approach_weight_pct"]}%)'),
        ("مؤشر أسلوب الدخل / Income Approach",
         f'{rec["income_approach_value"]:,} SAR (وزن {rec["income_approach_weight_pct"]}%)'),
        ("مؤشر أسلوب التكلفة / Cost Approach",
         f'{rec["cost_approach_value"]:,} SAR (وزن {rec["cost_approach_weight_pct"]}%)'),
        ("القيمة الموزونة",  f'{rec["weighted_value"]:,} SAR'),
        ("رأي القيمة النهائي", f'{rec["final_opinion_rounded"]:,} {rec["currency"]}'),
    ]
    r = _kv_block(ws, r, reconciliation_rows, label_bg=_LIGHT)

    r += 1
    _cell(ws, r, 1, ADVISORY_NOTE_AR, italic=True, bg=_WARN)
    ws.merge_cells(f"A{r}:B{r}")
    ws.row_dimensions[r].height = 40


def _add_data_quality_sheet(wb) -> None:
    sheet_name = "جودة البيانات"
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]
    ws = wb.create_sheet(title=sheet_name)
    ws.column_dimensions["A"].width = 35
    ws.column_dimensions["B"].width = 30
    ws.sheet_view.rightToLeft = True

    _hdr(ws, 1, 1, "جودة البيانات واكتمال المتطلبات", bg=_NAVY, fg=_GOLD, size=12)
    ws.merge_cells("A1:B1")

    _table(ws, 3, ["البيان", "الحالة"],
           [[d["field"], d["status"]] for d in DATA_INPUTS_AR])


def _add_method_coverage_sheet(wb, report_label: str, methods: list[tuple]) -> None:
    sheet_name = f"تغطية الأساليب — {report_label}"[:31]
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]
    ws = wb.create_sheet(title=sheet_name)
    ws.column_dimensions["A"].width = 45
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 30
    ws.sheet_view.rightToLeft = True

    _hdr(ws, 1, 1, f"تغطية أساليب التقييم — {report_label}", bg=_NAVY, fg=_GOLD, size=12)
    ws.merge_cells("A1:C1")

    _table(ws, 3, ["أسلوب التقييم", "مُطبَّق", "ملاحظة"],
           [[m[0], m[1], m[2]] for m in methods])


def _add_expert_notes_sheet(wb, report_label: str) -> None:
    sheet_name = "ملاحظات الخبير"
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]
    ws = wb.create_sheet(title=sheet_name)
    ws.column_dimensions["A"].width = 50
    ws.column_dimensions["B"].width = 40
    ws.sheet_view.rightToLeft = True

    _hdr(ws, 1, 1, "ملاحظات الخبير والإدارة", bg=_NAVY, fg=_GOLD, size=12)
    ws.merge_cells("A1:B1")

    _kv_block(ws, 3, [
        ("نوع التقرير",                        report_label),
        ("حالة المراجعة",                     "معلقة — تستلزم مراجعة الخبير"),
        ("الخبير المسؤول",                    "— (يُحدَّد لاحقاً)"),
        ("تاريخ المراجعة",                    "— (يُحدَّد لاحقاً)"),
        ("ملاحظات المراجعة",                  "—"),
        ("الإجراء التالي",                    "مراجعة البيانات والمستندات وإصدار التقرير المعتمد"),
        ("admin_excel_internal_only",         "True — لا يُرسل للمستخدم"),
        ("certification_ready",               "False — يستلزم قرار الخبير"),
    ])


def _generate_workbook(
    legacy_path: Path,
    out_path: Path,
    report_label: str,
    report_key: str,
    methods: list[tuple],
) -> dict:
    if not _OPENPYXL_OK:
        return {"status": "FAILED", "error": "openpyxl not installed", "size_bytes": 0}
    if not legacy_path.exists():
        return {"status": "FAILED", "error": f"Legacy file not found: {legacy_path}", "size_bytes": 0}

    try:
        # Step 1: copy legacy file
        shutil.copy2(str(legacy_path), str(out_path))

        # Step 2: open with keep_vba=True to preserve macros/VBA where possible
        wb = load_workbook(str(out_path), keep_vba=True)
        legacy_sheet_count = len(wb.sheetnames)
        legacy_sheets_preserved = list(wb.sheetnames)  # record before adding

        # Step 3: add new Arabic sheets
        _add_arabic_summary_sheet(wb, report_label, report_key, RECONCILIATION_AR)
        _add_data_quality_sheet(wb)
        _add_method_coverage_sheet(wb, report_label, methods)
        _add_expert_notes_sheet(wb, report_label)

        # Step 4: save as .xlsm (keep_vba=True allows this)
        wb.save(str(out_path))

        size = out_path.stat().st_size
        new_sheet_count = len(wb.sheetnames)
        new_sheets_added = [s for s in wb.sheetnames if s not in legacy_sheets_preserved]

        return {
            "status": "OK",
            "file": str(out_path),
            "size_bytes": size,
            "legacy_file_used": str(legacy_path),
            "legacy_sheet_count": legacy_sheet_count,
            "legacy_sheets_preserved": legacy_sheets_preserved,
            "deleted_legacy_sheets": [],
            "new_sheets_added": new_sheets_added,
            "total_sheet_count": new_sheet_count,
            "uses_legacy_template": True,
            "arabic_visible_labels": True,
            "not_tiny_placeholder": size > 1_000_000,
            "macros_note": "keep_vba=True used — macro preservation attempted; verify in Excel",
        }
    except Exception as e:
        return {"status": "FAILED", "error": str(e), "size_bytes": 0}


def generate_all_excel(excel_out: Path) -> dict[str, dict]:
    excel_out.mkdir(parents=True, exist_ok=True)
    legacy_path = _resolve_legacy()

    configs = {
        "traditional_report_admin_workbook": {
            "label": "تقرير تقليدي",
            "key": "traditional_report",
            "methods": [
                ("أسلوب السوق / Market Approach",   "نعم", "وزن 50%"),
                ("أسلوب الدخل / Income Approach",   "نعم", "وزن 35%"),
                ("أسلوب التكلفة / Cost Approach",   "نعم", "وزن 15%"),
                ("AVM / نموذج التقييم الآلي",       "نعم", "مؤشر مساعد فقط"),
            ],
        },
        "detailed_report_admin_workbook": {
            "label": "تقرير تفصيلي",
            "key": "detailed_report",
            "methods": [
                ("أسلوب السوق / Market Approach",       "نعم", "وزن 50%"),
                ("أسلوب الدخل / Income Approach",       "نعم", "وزن 35%"),
                ("أسلوب التكلفة / Cost Approach",       "نعم", "وزن 15%"),
                ("التدفقات النقدية / DCF",              "نعم", "ملخص"),
                ("تحليل الحساسية / Sensitivity",        "نعم", "لقطة"),
                ("ملاحظات المخاطر / Risk Notes",        "نعم", "ملخص"),
                ("AVM / نموذج التقييم الآلي",           "نعم", "مؤشر مساعد"),
            ],
        },
        "professional_report_admin_workbook": {
            "label": "تقرير احترافي",
            "key": "professional_report",
            "methods": [
                ("أسلوب السوق / Market Approach",          "نعم", "وزن 50%"),
                ("أسلوب الدخل / Income Approach",          "نعم", "وزن 35%"),
                ("أسلوب التكلفة / Cost Approach",          "نعم", "وزن 15%"),
                ("التدفقات النقدية / DCF",                 "نعم", "5 و10 سنوات"),
                ("أعلى وأفضل استخدام / HBU",              "نعم", "ملخص"),
                ("تحليل السيناريوهات / Scenario Analysis", "نعم", "3 سيناريوهات"),
                ("تحليل الحساسية / Sensitivity",           "نعم", "مصفوفة كاملة"),
                ("مخاطر / Risk-Adjusted",                  "نعم", "مصفوفة مخاطر"),
                ("AVM / نموذج التقييم الآلي",              "نعم", "مناقشة موثوقية"),
                ("التوفيق والترجيح / Reconciliation",      "نعم", "بطاقة ترجيح"),
                ("مصفوفة المعايير / Standards",            "نعم", "IVS 2025"),
            ],
        },
    }

    results = {}
    for file_key, cfg in configs.items():
        out_path = excel_out / f"{file_key}.xlsm"
        result = _generate_workbook(
            legacy_path=legacy_path,
            out_path=out_path,
            report_label=cfg["label"],
            report_key=cfg["key"],
            methods=cfg["methods"],
        )
        result["report_label"] = cfg["label"]
        results[file_key] = result
    return results
