# -*- coding: utf-8 -*-
"""
reporting_workbook_builder.py — Expert Excel workbook builder and validators.

Extracted from shared_request_routes.py (refactor Step 2).
Contains workbook validation helpers and the expert review workbook builder.

No Flask, no request/response logic, no PDF rendering, no endpoint handlers.
"""
from __future__ import annotations

import json
from pathlib import Path

from reporting_method_context import _build_method_context  # noqa: F401

# Storage path — mirrors shared_request_routes.py; both files live in core_engine/
_WORKBOOKS = Path(__file__).parent / "instance" / "expert_workbooks"


# ── Workbook blank-cell validator ─────────────────────────────────────────────

def _validate_workbook_formulas_and_no_silent_blanks(workbook_path) -> list:
    """Inspect key workbook sheets for formula presence and no silent blanks.

    Returns list of issue strings (empty list = all checks pass).
    Checks:
    1. 'مدخلات التقرير' exists and is the first sheet.
    2. Required method sheets exist.
    3. Required sheets have sufficient non-blank rows.
    4. Key method sheets contain at least one formula cell (starting with '=').
    """
    import openpyxl as _opxl
    wb = _opxl.load_workbook(str(workbook_path), data_only=False)
    issues: list = []

    # 1. Check 'مدخلات التقرير' is first sheet
    if not wb.sheetnames:
        issues.append("WORKBOOK_EMPTY: no sheets found")
        return issues
    if wb.sheetnames[0] != "مدخلات التقرير":
        issues.append(
            f"INPUTS_SHEET_NOT_FIRST: first sheet is {wb.sheetnames[0]!r}, "
            "expected 'مدخلات التقرير'"
        )

    # 2 + 3. Required sheets exist and have content
    _REQUIRED = [
        "مدخلات التقرير", "Dashboard", "غلاف وملخص", "بيانات العقار",
        "مقارنة البيوع", "طريقة الدخل", "DCF", "طريقة التكلفة",
        "AVM", "توفيق النتائج", "مصادر الأسعار", "ربط التقييم الجماعي",
        "الخلاصة والصياغة النهائية", "القيمة الإيجارية",
        "مقارنات إيجارية", "توفيق القيمة الإيجارية",
        # Sheets from prior phases
        "سجل المراجعة", "قيمة الأرض", "خرائط وصور",
        # New strategic sheets
        "سيناريوهات What-If", "شراء أم إيجار", "ESG والاستدامة", "مؤشرات تكلفة البناء",
    ]
    for sname in _REQUIRED:
        if sname not in wb.sheetnames:
            issues.append(f"MISSING_SHEET: {sname!r}")
            continue
        ws = wb[sname]
        non_blank_rows = sum(
            1 for row in ws.iter_rows(min_row=2, max_row=40, values_only=True)
            if any(c is not None and str(c).strip() for c in row)
        )
        if non_blank_rows < 3:
            issues.append(
                f"NEAR_EMPTY: sheet {sname!r} has only {non_blank_rows} "
                "non-blank rows in rows 2–40"
            )

    # 4a. Audit trail check: سجل المراجعة must have ≥ 3 lifecycle rows
    if "سجل المراجعة" in wb.sheetnames:
        ws_audit = wb["سجل المراجعة"]
        audit_data_rows = sum(
            1 for row in ws_audit.iter_rows(min_row=2, max_row=20, values_only=True)
            if any(c is not None and str(c).strip() for c in row)
        )
        if audit_data_rows < 3:
            issues.append(
                f"AUDIT_TRAIL_SPARSE: 'سجل المراجعة' has only {audit_data_rows} "
                "lifecycle rows — expected ≥ 3"
            )

    # 4b. Land share check: قيمة الأرض must mention land_share_ratio
    if "قيمة الأرض" in wb.sheetnames:
        ws_land = wb["قيمة الأرض"]
        _land_cells = [
            str(cell or "")
            for row in ws_land.iter_rows(values_only=True)
            for cell in row if cell is not None
        ]
        _land_text = " ".join(_land_cells)
        if "نصيب" not in _land_text and "Ratio" not in _land_text and "ratio" not in _land_text:
            issues.append("LAND_SHARE_MISSING: 'قيمة الأرض' sheet has no land_share_ratio section")

    # 4c. What-If sheet has G-column formula cells (=value_impact)
    if "سيناريوهات What-If" in wb.sheetnames:
        ws_wi_v = wb["سيناريوهات What-If"]
        _wi_formula_found = any(
            cell.value and isinstance(cell.value, str) and cell.value.startswith("=")
            for row in ws_wi_v.iter_rows(min_row=3, max_row=20)
            for cell in row
        )
        if not _wi_formula_found:
            issues.append("WHAT_IF_NO_FORMULAS: 'سيناريوهات What-If' has no formula cells")

    # 4d. Buy vs Rent has price-to-rent formula
    if "شراء أم إيجار" in wb.sheetnames:
        ws_bvr_v = wb["شراء أم إيجار"]
        _bvr_formula_found = any(
            cell.value and isinstance(cell.value, str) and cell.value.startswith("=")
            for row in ws_bvr_v.iter_rows(min_row=2, max_row=30)
            for cell in row
        )
        if not _bvr_formula_found:
            issues.append("BUY_RENT_NO_FORMULAS: 'شراء أم إيجار' has no formula cells")

    # 4e. ESG sheet has SUM formula
    if "ESG والاستدامة" in wb.sheetnames:
        ws_esg_v = wb["ESG والاستدامة"]
        _esg_formula_found = any(
            cell.value and isinstance(cell.value, str) and "SUM" in cell.value.upper()
            for row in ws_esg_v.iter_rows(min_row=2, max_row=30)
            for cell in row
        )
        if not _esg_formula_found:
            issues.append("ESG_NO_SUM_FORMULA: 'ESG والاستدامة' has no SUM formula for scoring")

    # 4. Formula checks: key method sheets must have at least one '=' formula cell
    _FORMULA_SHEETS = [
        "مقارنة البيوع", "طريقة الدخل", "DCF",
        "طريقة التكلفة", "توفيق النتائج", "مقارنات إيجارية",
    ]
    for sname in _FORMULA_SHEETS:
        if sname not in wb.sheetnames:
            continue  # already flagged above
        ws = wb[sname]
        found_formula = False
        for row in ws.iter_rows(min_row=1, max_row=ws.max_row):
            for cell in row:
                if cell.value and isinstance(cell.value, str) and cell.value.startswith("="):
                    found_formula = True
                    break
            if found_formula:
                break
        if not found_formula:
            issues.append(f"NO_FORMULAS: sheet {sname!r} has no formula cells starting with '='")

    return issues


def _validate_workbook_no_silent_blanks(workbook_path) -> list:
    """Backward-compatible alias → delegates to _validate_workbook_formulas_and_no_silent_blanks."""
    return _validate_workbook_formulas_and_no_silent_blanks(workbook_path)


# ── Internal expert workbook ──────────────────────────────────────────

def _create_expert_review_workbook(request_id: str, req: dict, docs_meta: list) -> Path:
    """Create internal expert review Excel workbook (9 sheets: Dashboard + traditional).

    Never exposed to ordinary users.
    Saves to: core_engine/instance/expert_workbooks/<REQ-ID>/expert_review_<REQ-ID>.xlsx
    Returns the Path to the saved file.
    """
    # Resolve report template name (Arabic) from the registry — internal use only
    try:
        from report_template_registry import get_template_name_ar
        _tmpl_id      = req.get("report_template_id") or ""
        _tmpl_name_ar = get_template_name_ar(_tmpl_id, default=_tmpl_id or "غير محدد")
    except Exception:
        _tmpl_id      = req.get("report_template_id") or ""
        _tmpl_name_ar = _tmpl_id or "غير محدد"
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    # ── Colour palette ──────────────────────────────────────────────────────
    C_BLUE_D  = "1F4E78"
    C_BLUE_M  = "2D6A9F"
    C_BLUE_L  = "EBF3FB"
    C_GOLD    = "D4AF37"
    C_GOLD_BG = "FFF9E6"
    C_GRAY    = "F5F5F5"
    C_GREEN   = "F0FFF6"
    C_RED     = "FFF5F5"
    C_WHITE   = "FFFFFF"

    F_TITLE = Font(bold=True, color=C_WHITE, name="Arial", size=12)
    F_SEC   = Font(bold=True, color=C_WHITE, name="Arial", size=10)
    F_HDR   = Font(bold=True, color=C_WHITE, name="Arial", size=10)
    F_LBL   = Font(bold=True, color=C_BLUE_D, name="Arial", size=9)
    F_VAL   = Font(color="1A1A2E",           name="Arial", size=9)
    F_GOLD  = Font(bold=True, color="7A5800", name="Arial", size=10)

    AL_RT   = Alignment(horizontal="right",  vertical="center", wrap_text=True)
    AL_CTR  = Alignment(horizontal="center", vertical="center", wrap_text=True)
    AL_TOP  = Alignment(horizontal="right",  vertical="top",    wrap_text=True)

    def _fill(c):
        return PatternFill("solid", fgColor=c)

    def _rtl(ws):
        try:
            ws.sheet_view.rightToLeft = True
        except Exception:
            pass

    def _hdr(ws, headers):
        """Standard column-header row (row 1, freeze row 2)."""
        for col, title in enumerate(headers, 1):
            c = ws.cell(row=1, column=col, value=title)
            c.font  = F_HDR
            c.fill  = _fill(C_BLUE_D)
            c.alignment = AL_CTR
        ws.freeze_panes = ws.cell(row=2, column=1)
        _rtl(ws)

    def _row(ws, rownum, *vals):
        for col, v in enumerate(vals, 1):
            c = ws.cell(row=rownum, column=col)
            c.value     = str(v) if v is not None else ""
            c.alignment = AL_RT

    def _widths(ws, widths):
        for col, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(col)].width = w

    def _sec_hdr(ws, row, col1, col2, title, bg=C_BLUE_M, fg=C_WHITE):
        """Merged section-header row."""
        cr = f"{get_column_letter(col1)}{row}:{get_column_letter(col2)}{row}"
        ws.merge_cells(cr)
        c = ws.cell(row=row, column=col1, value=title)
        c.font      = Font(bold=True, color=fg, name="Arial", size=10)
        c.fill      = _fill(bg)
        c.alignment = AL_CTR
        ws.row_dimensions[row].height = 18

    def _kv(ws, row, label, value,
            lc=1, vs=2, ve=3, lbg=C_BLUE_L, vbg=C_WHITE):
        """Label / value pair with optional merged value cells."""
        cl = ws.cell(row=row, column=lc, value=label)
        cl.font      = F_LBL
        cl.fill      = _fill(lbg)
        cl.alignment = AL_RT
        if ve > vs:
            ws.merge_cells(
                f"{get_column_letter(vs)}{row}:{get_column_letter(ve)}{row}"
            )
        cv = ws.cell(row=row, column=vs, value=str(value) if value else "")
        cv.font      = F_VAL
        cv.fill      = _fill(vbg)
        cv.alignment = AL_RT

    # ── Parse payload ────────────────────────────────────────────────────────
    payload = req.get("payload_json") or {}
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            payload = {}

    mv      = payload.get("estimated_value")
    has_mv  = bool(mv and isinstance(mv, (int, float)) and mv > 0)
    mv_str  = f"{int(mv):,}" if has_mv else ""
    low_v   = payload.get("price_range_low")
    high_v  = payload.get("price_range_high")
    low_s   = f"{int(low_v):,}"  if has_mv and low_v  else ""
    high_s  = f"{int(high_v):,}" if has_mv and high_v else ""
    rng_s   = f"{low_s} — {high_s}" if low_s and high_s else ""
    location = " | ".join(filter(None, [
        payload.get("country", ""), payload.get("region", ""),
        payload.get("city", ""),    payload.get("district", ""),
    ]))
    data_status  = "مكتملة مبدئيًا" if has_mv else "ناقصة — تحتاج سعر متر"
    docs_status  = "مستندات مرفقة للمراجعة" if docs_meta else "لم تُرفع بعد"
    doc_names_s  = ", ".join(
        dm.get("original_filename", "") for dm in (docs_meta or [])
    )
    area_s = (f"{payload.get('area')} م²" if payload.get("area") else "")

    # ── Method context for numeric simulation ────────────────────────────────
    mctx = _build_method_context(payload)
    wb_comparables   = mctx.get("comparables", [])
    wb_has_comps     = mctx.get("has_comparables", False)
    wb_avg_adj       = mctx.get("avg_adjusted_price", "")
    wb_income_noi    = mctx.get("income_noi", "")
    wb_income_value  = mctx.get("income_value_calc", "")
    wb_cap_rate      = mctx.get("income_cap_rate_pct", "")
    wb_dcf_rows      = mctx.get("dcf_rows", [])
    wb_dcf_value     = mctx.get("dcf_value_calc", "")
    wb_cost_value    = mctx.get("cost_value_calc", "")
    wb_cost_land     = mctx.get("cost_land_value", "")
    wb_cost_repl     = mctx.get("cost_replacement_total", "")
    wb_cost_depr     = mctx.get("cost_total_depr_amt", "")

    # AVM numbers from payload
    _avm_val  = payload.get("avm_value")
    _avm_low  = payload.get("avm_low_range")
    _avm_high = payload.get("avm_high_range")
    def _n(v): return f"{int(float(str(v))):,}" if v else ""

    # Extended method context fields
    wb_land_comps         = mctx.get("land_comps", [])
    wb_avg_land_price     = mctx.get("avg_land_price", "")
    wb_land_value_sales   = mctx.get("land_value_by_sales", "")
    wb_land_value_recon   = mctx.get("land_value_reconciled", "")
    wb_cost_breakdown     = mctx.get("cost_breakdown", [])
    wb_cost_breakdown_tot = mctx.get("cost_breakdown_total", "")
    wb_dr_methods         = mctx.get("discount_rate_methods", [])
    wb_tc_methods         = mctx.get("terminal_cap_methods", [])
    wb_avm_reg            = mctx.get("avm_regression", [])
    wb_avm_reg_final      = mctx.get("avm_reg_final", "")
    wb_avm_reg_band       = mctx.get("avm_reg_confidence_band", "")
    wb_avm_reg_limitations= mctx.get("avm_reg_limitations", "")
    wb_extr               = {k: mctx.get(k, "") for k in [
        "extr_improved_indication", "extr_replacement_cost_new",
        "extr_depreciation_pct", "extr_depr_amount", "extr_depr_imprv_value",
        "extr_land_value", "extr_land_per_m2", "extr_land_share_value",
    ]}

    # New data-binding structures
    _dg               = mctx.get("_data_gap_label",    "غير متاح ضمن بيانات الطلب")
    _ef               = mctx.get("_expert_fill_label", "يحتاج استكمال بواسطة الخبير")
    _na               = mctx.get("_na_purpose_label",  "غير مطبق لهذا الغرض")
    wb_price_sources  = mctx.get("price_source_data", [])
    wb_mass_bridge    = mctx.get("mass_appraisal_bridge", {})
    wb_cap_rate_deriv = mctx.get("cap_rate_derivation", {})
    wb_cr_methods     = wb_cap_rate_deriv.get("methods", [])
    wb_cr_avg         = wb_cap_rate_deriv.get("average_cap_rate", _dg)
    wb_cr_expert      = wb_cap_rate_deriv.get("expert_selected_cap_rate", _ef)
    wb_cr_notes       = wb_cap_rate_deriv.get("final_cap_rate_notes", _ef)
    wb_cr_disclaimer  = wb_cap_rate_deriv.get("disclaimer", "")
    # Purpose / date-basis / rental
    wb_purpose_info   = mctx.get("purpose_info", {})
    wb_date_basis     = mctx.get("date_basis_info", {})
    wb_is_rental      = mctx.get("is_rental_purpose", False)
    wb_rental_ctx     = mctx.get("rental_value_context", {})
    wb_rental_comps   = wb_rental_ctx.get("rental_comparables", [])

    def _dg_val(v):
        """Return value or data-gap label when blank."""
        return v if (v and str(v).strip()) else _dg

    wb = openpyxl.Workbook()
    wb.calculation.calcMode    = "auto"
    wb.calculation.fullCalcOnLoad = True

    # ════════════════════════════════════════════════════════════════════════
    # Sheet 1: Dashboard (12-sheet edition)
    # ════════════════════════════════════════════════════════════════════════
    ws_d = wb.active
    ws_d.title = "Dashboard"
    _rtl(ws_d)
    _widths(ws_d, [30, 28, 28, 30, 28, 28])

    ws_d.merge_cells("A1:F1")
    ws_d["A1"].value     = "لوحة معلومات المراجعة الداخلية — Expert Smart (26 ورقة)"
    ws_d["A1"].font      = F_TITLE
    ws_d["A1"].fill      = _fill(C_BLUE_D)
    ws_d["A1"].alignment = AL_CTR
    ws_d.row_dimensions[1].height = 28

    _sec_hdr(ws_d, 2, 1, 6, "بيانات الطلب")
    _kv(ws_d, 3, "رقم الطلب",              request_id,                               1, 2, 3)
    _kv(ws_d, 3, "حالة الطلب",             req.get("approval_status", "قيد المراجعة"), 4, 5, 6)
    _kv(ws_d, 4, "تاريخ الإنشاء",          (req.get("created_at") or "")[:10],        1, 2, 3)
    _kv(ws_d, 4, "نوع الطلب",              req.get("request_kind", ""),               4, 5, 6)
    _kv(ws_d, 5, "اسم العميل",             req.get("user_name", ""),                  1, 2, 3)
    _kv(ws_d, 5, "الهاتف",                 req.get("phone", ""),                      4, 5, 6)
    _kv(ws_d, 6, "نموذج التقرير المطلوب",  _tmpl_name_ar,                             1, 2, 3,
        vbg=C_GOLD_BG if _tmpl_name_ar and _tmpl_name_ar != "غير محدد" else C_GRAY)
    _kv(ws_d, 6, "معرّف النموذج (ID)",      _tmpl_id or "—",                          4, 5, 6)
    ws_d.row_dimensions[7].height = 8

    _sec_hdr(ws_d, 8, 1, 6, "بيانات العقار")
    _kv(ws_d, 9,  "نوع العقار",    payload.get("property_type", ""),         1, 2, 3)
    _kv(ws_d, 9,  "الغرض",         payload.get("purpose", "القيمة السوقية"), 4, 5, 6)
    _kv(ws_d, 10, "الموقع",        location,                                  1, 2, 3)
    _kv(ws_d, 10, "المساحة",       area_s,                                    4, 5, 6)
    _kv(ws_d, 11, "تاريخ التقييم", payload.get("valuation_date", ""),         1, 2, 3)
    _kv(ws_d, 11, "حالة البيانات", data_status,                               4, 5, 6,
        vbg=C_GREEN if has_mv else C_RED)
    _kv(ws_d, 12, "أساس تاريخ التقييم",
        wb_date_basis.get("date_basis_label_ar", _dg),                         1, 2, 3,
        vbg="EBF3FB")
    _kv(ws_d, 12, "الغرض (مُصنَّف)",
        wb_purpose_info.get("purpose_label_ar", _dg),                          4, 5, 6,
        vbg="EBF3FB")
    ws_d.row_dimensions[13].height = 8

    _sec_hdr(ws_d, 14, 1, 6, "حالة طرق التقييم وقيمها")
    _kv(ws_d, 15, "مقارنة البيوع",  wb_avg_adj if wb_has_comps else ("متاحة" if has_mv else "تحتاج مقارنات"), 1, 2, 3,
        vbg=C_GREEN if (wb_has_comps or has_mv) else C_RED)
    _kv(ws_d, 15, "طريقة الدخل",   wb_income_value if wb_income_value else "تحتاج بيانات دخل", 4, 5, 6,
        vbg=C_GREEN if wb_income_value else C_RED)
    _kv(ws_d, 16, "طريقة التكلفة", wb_cost_value if wb_cost_value else "تحتاج بيانات تكلفة", 1, 2, 3,
        vbg=C_GREEN if wb_cost_value else C_RED)
    _kv(ws_d, 16, "DCF / AVM",     wb_dcf_value if wb_dcf_value else "راجع شيتات DCF و AVM", 4, 5, 6,
        vbg=C_GREEN if wb_dcf_value else C_RED)
    _kv(ws_d, 17, "التوفيق",        "قيد المراجعة — راجع شيت توفيق النتائج",   1, 2, 3, vbg=C_GOLD_BG)
    _kv(ws_d, 17, "حالة المستندات", docs_status,                               4, 5, 6,
        vbg=C_GREEN if docs_meta else C_RED)
    ws_d.row_dimensions[18].height = 8

    _sec_hdr(ws_d, 19, 1, 6, "القيمة المبدئية وAVM")
    _kv(ws_d, 20, "القيمة المبدئية", mv_str if mv_str else "غير متاحة",       1, 2, 3,
        vbg=C_GREEN if has_mv else C_RED)
    _kv(ws_d, 20, "قيمة AVM",        _n(_avm_val) if _avm_val else "—",       4, 5, 6,
        vbg=C_GOLD_BG if _avm_val else C_GRAY)
    ws_d.row_dimensions[21].height = 8

    _sec_hdr(ws_d, 22, 1, 6, "قرار الخبير", C_GOLD, "7A5800")
    ws_d.merge_cells("A23:F23")
    cq = ws_d["A23"]
    cq.value     = "قيد المراجعة — يُعبأ بواسطة الخبير"
    cq.font      = F_GOLD
    cq.fill      = _fill(C_GOLD_BG)
    cq.alignment = AL_CTR
    ws_d.row_dimensions[23].height = 22
    ws_d.row_dimensions[24].height = 8

    _sec_hdr(ws_d, 25, 1, 6, "ملاحظات الخبير الرئيسية")
    ws_d.merge_cells("A26:F29")
    cn = ws_d["A26"]
    cn.value     = ""
    cn.fill      = _fill(C_WHITE)
    cn.alignment = AL_TOP
    for r in range(26, 30):
        ws_d.row_dimensions[r].height = 20
    ws_d.freeze_panes = ws_d["A3"]

    # ════════════════════════════════════════════════════════════════════════
    # Sheet 1 (inserted at index 0): مدخلات التقرير — Central Input Hub
    # Inserted AFTER Dashboard so it becomes index 0, Dashboard becomes index 1
    # ════════════════════════════════════════════════════════════════════════
    ws_inp = wb.create_sheet("مدخلات التقرير", 0)
    _rtl(ws_inp)
    _widths(ws_inp, [44, 54, 28])
    ws_inp.merge_cells("A1:C1")
    ws_inp["A1"].value     = "مدخلات التقرير — مركز بيانات الإدخال للتقييم الداخلي"
    ws_inp["A1"].font      = F_TITLE
    ws_inp["A1"].fill      = _fill(C_BLUE_D)
    ws_inp["A1"].alignment = AL_CTR
    ws_inp.row_dimensions[1].height = 28
    _ri = 2

    # ── Section 1: بيانات التكليف ─────────────────────────────────────────
    _sec_hdr(ws_inp, _ri, 1, 3, "١. بيانات التكليف"); _ri += 1
    for _lbl_inp, _v_inp in [
        ("رقم الطلب",                  request_id),
        ("اسم العميل",                 req.get("user_name", _dg)),
        ("الهاتف",                     req.get("phone", _dg)),
        ("البريد الإلكتروني",          req.get("email", _dg)),
        ("معرّف نموذج التقرير",        _tmpl_id or _dg),
        ("اسم نموذج التقرير",          _tmpl_name_ar),
        ("مفتاح الغرض (purpose_key)",  wb_purpose_info.get("purpose_key", _dg)),
        ("الغرض من التقييم",           wb_purpose_info.get("purpose_label_ar", _dg)),
        ("تاريخ التقييم",              payload.get("valuation_date", _dg)),
        ("تاريخ التقرير",              payload.get("report_date", _dg)),
        ("مفتاح أساس التاريخ",         wb_date_basis.get("date_basis_key", _dg)),
        ("أساس تاريخ التقييم",         wb_date_basis.get("date_basis_label_ar", _dg)),
        ("ملاحظات أساس التاريخ",       wb_date_basis.get("date_basis_notes", _dg)),
    ]:
        _kv(ws_inp, _ri, _lbl_inp, _dg_val(_v_inp), 1, 2, 3,
            vbg=C_GOLD_BG if _lbl_inp in ("الغرض من التقييم", "تاريخ التقييم", "أساس تاريخ التقييم") else C_WHITE)
        _ri += 1
    ws_inp.row_dimensions[_ri].height = 6; _ri += 1

    # ── Section 2: بيانات العقار ──────────────────────────────────────────
    _sec_hdr(ws_inp, _ri, 1, 3, "٢. بيانات العقار"); _ri += 1
    for _lbl_inp, _v_inp in [
        ("نوع العقار",               payload.get("property_type", _dg)),
        ("فئة الأصل",                payload.get("asset_family", _dg)),
        ("النوع الفرعي",             payload.get("asset_subtype", _dg)),
        ("الدولة",                   payload.get("country", _dg)),
        ("المحافظة/المنطقة",         payload.get("region", _dg)),
        ("المدينة",                  payload.get("city", _dg)),
        ("الحي/المنطقة",             payload.get("district", _dg)),
        ("العنوان التفصيلي",         payload.get("address", _dg)),
        ("المساحة الإجمالية (م²)",   payload.get("area", _dg)),
        ("مساحة المبنى (م²)",        payload.get("building_area", _dg)),
        ("نصيب الأرض (م²)",          payload.get("land_share_area", _dg)),
        ("حالة العقار",              payload.get("condition", _dg)),
        ("مستوى التشطيب",           payload.get("finishing_level", _dg)),
        ("رقم الطابق",               payload.get("floor", _dg)),
        ("الواجهة (م)",              str(payload.get("frontage") or _dg)),
        ("عرض الشارع (م)",           str(payload.get("street_width") or _dg)),
        ("الإحداثيات",               payload.get("coordinates", _dg)),
        ("وصف العقار",               (payload.get("description") or _dg)[:200]),
        ("ملاحظات",                  payload.get("notes", _dg)),
    ]:
        _kv(ws_inp, _ri, _lbl_inp, _dg_val(_v_inp), 1, 2, 3,
            vbg=C_GOLD_BG if _lbl_inp in ("المساحة الإجمالية (م²)", "نصيب الأرض (م²)") else C_WHITE)
        _ri += 1
    ws_inp.row_dimensions[_ri].height = 6; _ri += 1

    # ── Section 3: مدخلات مصادر الأسعار ──────────────────────────────────
    _sec_hdr(ws_inp, _ri, 1, 3, "٣. مدخلات مصادر الأسعار"); _ri += 1
    if wb_price_sources:
        _ps0 = wb_price_sources[0]
        for _lbl_inp, _v_inp in [
            ("كود المصدر (عينة أولى)",  _ps0.get("source_registry_id", _dg)),
            ("نوع المصدر",              _ps0.get("source_type", _dg)),
            ("المنطقة / Zone",           _ps0.get("district", _dg)),
            ("سعر/م²",                  _ps0.get("price_per_m2", _dg)),
            ("تاريخ المصدر",            _ps0.get("source_date", _dg)),
            ("مستوى الثقة",             _ps0.get("source_confidence", _dg)),
            ("مستخدم في",              _ps0.get("used_in_methods", _dg)),
            ("عدد المصادر الكلي",       str(len(wb_price_sources))),
        ]:
            _kv(ws_inp, _ri, _lbl_inp, _dg_val(_v_inp), 1, 2, 3); _ri += 1
    else:
        _kv(ws_inp, _ri, "حالة المصادر", _dg, 1, 2, 3); _ri += 1
    ws_inp.row_dimensions[_ri].height = 6; _ri += 1

    # ── Section 4: مدخلات التقييم الجماعي ───────────────────────────────
    _sec_hdr(ws_inp, _ri, 1, 3, "٤. مدخلات التقييم الجماعي"); _ri += 1
    for _lbl_inp, _k_inp in [
        ("معرف تشغيل التقييم الجماعي",   "mass_run_id"),
        ("معرف المنطقة",                   "mass_zone_id"),
        ("متوسط سعر المتر في المنطقة",     "mass_average_price_per_m2"),
        ("نموذج القيمة الجماعية",          "mass_model_value"),
        ("نطاق الثقة",                      "mass_confidence_range"),
        ("درجة جودة البيانات",             "mass_data_quality_score"),
        ("تغطية مصادر البيانات",           "mass_source_coverage"),
        ("حالة التقييم الجماعي",           "mass_appraisal_status"),
    ]:
        _kv(ws_inp, _ri, _lbl_inp, _dg_val(wb_mass_bridge.get(_k_inp, _dg)), 1, 2, 3); _ri += 1
    ws_inp.row_dimensions[_ri].height = 6; _ri += 1

    # ── Section 5: مدخلات AVM ────────────────────────────────────────────
    _sec_hdr(ws_inp, _ri, 1, 3, "٥. مدخلات AVM"); _ri += 1
    for _lbl_inp, _v_inp in [
        ("سعر المتر الأساسي base_price_per_m2",  str(payload.get("base_price_per_m2") or _dg)),
        ("معامل الموقع location_factor",           str(payload.get("location_factor") or _dg)),
        ("معامل المساحة area_adjustment",          str(payload.get("area_adjustment") or _dg)),
        ("معامل الحالة condition_factor",          str(payload.get("condition_factor") or _dg)),
        ("معامل التشطيب finishing_factor",         str(payload.get("finishing_factor") or _dg)),
        ("معامل الطابق floor_view_factor",         str(payload.get("floor_view_factor") or _dg)),
        ("عامل الإهلاك العمري",                    str(payload.get("age_depreciation_factor") or _dg)),
        ("معامل الواجهة frontage_factor",          str(payload.get("frontage_factor") or _dg)),
        ("درجة الثقة avm_confidence_score",        str(payload.get("avm_confidence_score") or _dg)),
        ("حالة جودة البيانات",                    str(payload.get("avm_data_quality_status") or _dg)),
        ("قيمة تدخل الخبير",                      str(payload.get("expert_override_value") or _dg)),
        ("سبب تدخل الخبير",                       str(payload.get("expert_override_reason") or _dg)),
    ]:
        _kv(ws_inp, _ri, _lbl_inp, _dg_val(_v_inp), 1, 2, 3); _ri += 1
    ws_inp.row_dimensions[_ri].height = 6; _ri += 1

    # ── Section 6: مدخلات المقارنات البيعية ─────────────────────────────
    _sec_hdr(ws_inp, _ri, 1, 3, "٦. مدخلات المقارنات البيعية (4 مقارنات)"); _ri += 1
    if wb_comparables:
        for _ci_inp, _c_inp in enumerate(wb_comparables[:4], 1):
            _kv(ws_inp, _ri, f"مقارن {_ci_inp} — الموقع",        _dg_val(_c_inp.get("location", "")),       1, 2, 3); _ri += 1
            _kv(ws_inp, _ri, f"مقارن {_ci_inp} — المساحة",        str(_c_inp.get("area", _dg)),              1, 2, 3); _ri += 1
            _kv(ws_inp, _ri, f"مقارن {_ci_inp} — سعر البيع",      _dg_val(_c_inp.get("sale_price", "")),     1, 2, 3); _ri += 1
            _kv(ws_inp, _ri, f"مقارن {_ci_inp} — سعر المتر",      _dg_val(_c_inp.get("price_per_m2", "")),   1, 2, 3); _ri += 1
            _kv(ws_inp, _ri, f"مقارن {_ci_inp} — معامل الموقع",   str(_c_inp.get("location_factor", _dg)),  1, 2, 3); _ri += 1
            _kv(ws_inp, _ri, f"مقارن {_ci_inp} — حالة التضمين",   _dg_val(_c_inp.get("status", "")),         1, 2, 3); _ri += 1
    else:
        _kv(ws_inp, _ri, "مقارنات البيوع", _dg, 1, 2, 3); _ri += 1
    ws_inp.row_dimensions[_ri].height = 6; _ri += 1

    # ── Section 7: مدخلات المقارنات الإيجارية ───────────────────────────
    _sec_hdr(ws_inp, _ri, 1, 3, "٧. مدخلات المقارنات الإيجارية (4 مقارنات)"); _ri += 1
    if wb_rental_comps:
        for _ci_inp, _rc_inp in enumerate(wb_rental_comps[:4], 1):
            _kv(ws_inp, _ri, f"إيجاري {_ci_inp} — الموقع",        _dg_val(_rc_inp.get("location", "")),        1, 2, 3); _ri += 1
            _kv(ws_inp, _ri, f"إيجاري {_ci_inp} — المساحة",        str(_rc_inp.get("area", _dg)),               1, 2, 3); _ri += 1
            _kv(ws_inp, _ri, f"إيجاري {_ci_inp} — الإيجار الشهري", _dg_val(_rc_inp.get("monthly_rent_disp", "")), 1, 2, 3); _ri += 1
            _kv(ws_inp, _ri, f"إيجاري {_ci_inp} — معامل الموقع",   str(_rc_inp.get("location_factor", _dg)),   1, 2, 3); _ri += 1
    else:
        _kv(ws_inp, _ri, "مقارنات إيجارية", _na if not wb_is_rental else _dg, 1, 2, 3); _ri += 1
    ws_inp.row_dimensions[_ri].height = 6; _ri += 1

    # ── Section 8: مدخلات قيمة الأرض ────────────────────────────────────
    _sec_hdr(ws_inp, _ri, 1, 3, "٨. مدخلات قيمة الأرض"); _ri += 1
    for _lbl_inp, _v_inp in [
        ("مساحة نصيب الأرض (م²)",             str(payload.get("land_share_area", _dg))),
        ("متوسط سعر المتر (أرض)",              _dg_val(mctx.get("avg_land_price", ""))),
        ("قيمة الأرض بالمقارنة البيعية",      _dg_val(mctx.get("land_value_by_sales", ""))),
        ("قيمة الأرض بالاستخلاص",             _dg_val(wb_extr.get("extr_land_share_value", ""))),
        ("تكلفة الإنشاء كجديد (استخلاص)",     _dg_val(mctx.get("cost_replacement_total", ""))),
        ("الإهلاك الكلي",                      _dg_val(mctx.get("cost_total_depr_amt", ""))),
        ("قيمة المباني المستهلكة",             _dg_val(mctx.get("cost_depreciated_imprv", ""))),
    ]:
        _kv(ws_inp, _ri, _lbl_inp, _dg_val(_v_inp), 1, 2, 3); _ri += 1
    ws_inp.row_dimensions[_ri].height = 6; _ri += 1

    # ── Section 9: مدخلات طريقة التكلفة ─────────────────────────────────
    _sec_hdr(ws_inp, _ri, 1, 3, "٩. مدخلات طريقة التكلفة"); _ri += 1
    for _lbl_inp, _v_inp in [
        ("سعر متر الإنشاء كجديد",              _dg_val(mctx.get("cost_replacement_per_m2", ""))),
        ("تكلفة الإنشاء كجديد الإجمالية",      _dg_val(mctx.get("cost_replacement_total", ""))),
        ("نسبة الإهلاك الجسدي (%)",             _dg_val(mctx.get("cost_physical_depr_pct", ""))),
        ("نسبة الإهلاك الوظيفي (%)",            _dg_val(mctx.get("cost_functional_depr_pct", ""))),
        ("نسبة الإهلاك الاقتصادي (%)",          _dg_val(mctx.get("cost_external_depr_pct", ""))),
        ("إجمالي الإهلاك (%)",                  _dg_val(mctx.get("cost_total_depr_pct", ""))),
        ("إجمالي الإهلاك (ج.م)",                _dg_val(mctx.get("cost_total_depr_amt", ""))),
        ("قيمة المباني بعد الإهلاك",            _dg_val(mctx.get("cost_depreciated_imprv", ""))),
        ("قيمة نصيب الأرض",                    _dg_val(mctx.get("cost_land_value", ""))),
        ("القيمة بطريقة التكلفة",               _dg_val(mctx.get("cost_value_calc", ""))),
    ]:
        _kv(ws_inp, _ri, _lbl_inp, _dg_val(_v_inp), 1, 2, 3); _ri += 1
    ws_inp.row_dimensions[_ri].height = 6; _ri += 1

    # ── Section 10: مدخلات طريقة الدخل ──────────────────────────────────
    _sec_hdr(ws_inp, _ri, 1, 3, "١٠. مدخلات طريقة الدخل"); _ri += 1
    for _lbl_inp, _v_inp in [
        ("الإيجار الشهري",                     _dg_val(mctx.get("income_monthly_rent", ""))),
        ("الدخل السنوي الإجمالي",              _dg_val(mctx.get("income_annual_gross", ""))),
        ("نسبة الشواغر (%)",                   _dg_val(mctx.get("income_vacancy_rate", ""))),
        ("نسبة فقدان التحصيل (%)",             _dg),
        ("نسبة المصاريف التشغيلية (%)",        _dg_val(mctx.get("income_expense_rate", ""))),
        ("نسبة الاحتياطيات (%)",               _dg),
        ("معدل الرسملة النهائي (%)",           _dg_val(mctx.get("income_cap_rate_pct", ""))),
        ("صافي الدخل التشغيلي NOI",            _dg_val(mctx.get("income_noi", ""))),
        ("القيمة بطريقة الدخل",                _dg_val(mctx.get("income_value_calc", ""))),
    ]:
        _kv(ws_inp, _ri, _lbl_inp, _dg_val(_v_inp), 1, 2, 3,
            vbg=C_GOLD_BG if "نهائي" in _lbl_inp or "الدخل التشغيلي" in _lbl_inp else C_WHITE)
        _ri += 1
    ws_inp.row_dimensions[_ri].height = 6; _ri += 1

    # ── Section 11: مدخلات DCF ───────────────────────────────────────────
    _sec_hdr(ws_inp, _ri, 1, 3, "١١. مدخلات التدفقات النقدية المخصومة DCF"); _ri += 1
    for _lbl_inp, _v_inp in [
        ("فترة التحليل (سنوات)",                "5"),
        ("NOI السنة الأولى",                    _dg_val(mctx.get("income_noi", ""))),
        ("معدل نمو الإيجارات (%)",              _dg_val(mctx.get("dcf_growth_rate_pct", ""))),
        ("معدل نمو المصاريف (%)",               _dg),
        ("معدل الخصم WACC (%)",                 _dg_val(mctx.get("dcf_discount_rate_pct", ""))),
        ("معدل الرسملة النهائي Terminal (%)",    _dg_val(mctx.get("dcf_terminal_cap_pct", ""))),
        ("نسبة تكاليف البيع (%)",               _dg),
        ("احتياطي CapEx (%)",                    _dg),
        ("قيمة DCF الكلية",                     _dg_val(mctx.get("dcf_value_calc", ""))),
    ]:
        _kv(ws_inp, _ri, _lbl_inp, _dg_val(_v_inp), 1, 2, 3); _ri += 1
    ws_inp.row_dimensions[_ri].height = 6; _ri += 1

    # ── Section 12: مدخلات معدل الخصم (4 طرق) ───────────────────────────
    _sec_hdr(ws_inp, _ri, 1, 3, "١٢. مدخلات معدل الخصم (4 طرق)"); _ri += 1
    if wb_dr_methods:
        for _dm_inp in wb_dr_methods:
            _kv(ws_inp, _ri, _dm_inp.get("method", _dg), _dg_val(_dm_inp.get("indicated_rate", "")), 1, 2, 3); _ri += 1
    else:
        for _lbl_dr in ["Build-up Rate", "CAPM Proxy", "Market Yield Extraction", "Band of Investment"]:
            _kv(ws_inp, _ri, _lbl_dr, _dg, 1, 2, 3); _ri += 1
    _kv(ws_inp, _ri, "معدل الخصم المختار", _dg_val(mctx.get("dr_expert_selected", "")), 1, 2, 3, vbg=C_GOLD_BG); _ri += 1
    ws_inp.row_dimensions[_ri].height = 6; _ri += 1

    # ── Section 13: مدخلات معدل الرسملة النهائي (4 طرق) ─────────────────
    _sec_hdr(ws_inp, _ri, 1, 3, "١٣. مدخلات معدل الرسملة النهائي (4 طرق)"); _ri += 1
    if wb_cr_methods:
        for _cm_inp in wb_cr_methods:
            _kv(ws_inp, _ri, _cm_inp.get("method_name", _dg), _dg_val(_cm_inp.get("indicated_cap_rate", "")), 1, 2, 3); _ri += 1
    else:
        for _lbl_cr in ["Direct Market Extraction", "Band of Investment", "Discount Rate minus Growth", "Built-up Cap Rate"]:
            _kv(ws_inp, _ri, _lbl_cr, _dg, 1, 2, 3); _ri += 1
    _kv(ws_inp, _ri, "معدل الرسملة النهائي المختار", _dg_val(wb_cr_expert), 1, 2, 3, vbg=C_GOLD_BG); _ri += 1
    ws_inp.row_dimensions[_ri].height = 6; _ri += 1

    # ── Section 14: مدخلات التوفيق ────────────────────────────────────────
    _sec_hdr(ws_inp, _ri, 1, 3, "١٤. مدخلات التوفيق"); _ri += 1
    for _lbl_inp, _v_inp in [
        ("وزن مقارنة البيوع (%)",    _dg_val(req.get("sales_comparison_weight", ""))),
        ("وزن طريقة الدخل (%)",      _dg_val(req.get("income_weight", ""))),
        ("وزن طريقة التكلفة (%)",    _dg_val(req.get("cost_weight", ""))),
        ("وزن DCF (%)",               _dg_val(req.get("dcf_weight", ""))),
        ("وزن AVM (%)",               _dg_val(req.get("avm_weight", ""))),
        ("القيمة المختارة من الخبير", _dg_val(req.get("expert_recommended_value", ""))),
        ("ملاحظات الخبير",            _dg_val(req.get("expert_notes", ""))),
        ("ملاحظات التوفيق",           _dg_val(req.get("reconciliation_notes", ""))),
        ("سبب القرار",               _dg_val(req.get("decision_reason", ""))),
    ]:
        _kv(ws_inp, _ri, _lbl_inp, _v_inp, 1, 2, 3,
            vbg=C_GOLD_BG if "مختارة" in _lbl_inp else C_WHITE); _ri += 1

    ws_inp.row_dimensions[_ri].height = 6; _ri += 1

    # ── Section 15: مدخلات سيناريوهات What-If ────────────────────────────
    _sec_hdr(ws_inp, _ri, 1, 3, "١٥. مدخلات سيناريوهات What-If"); _ri += 1
    _wi_qa = mctx.get("is_qa", bool(payload.get("_qa_simulation")))
    for _lbl_inp, _v_inp in [
        ("سيناريو 1 — تغيير مستوى التشطيب",      "ترقية: عادي → فاخر" if _wi_qa else _ef),
        ("سيناريو 2 — تغيير حالة العقار",         "تحسين: متوسط → جيد" if _wi_qa else _ef),
        ("سيناريو 3 — تغيير الاستخدام",           "تحويل: سكني → تجاري" if _wi_qa else _ef),
        ("سيناريو 4 — تغيير معدل نمو الإيجار (%)", "3.0" if _wi_qa else _ef),
        ("سيناريو 5 — تغيير معدل الرسملة (%)",    "4.5" if _wi_qa else _ef),
        ("سيناريو 6 — تغيير معدل الخصم (%)",      "14.0" if _wi_qa else _ef),
        ("سيناريو 7 — تغيير نسبة الشواغر (%)",    "10.0" if _wi_qa else _ef),
        ("ملاحظات What-If",  "سيناريوهات افتراضية — تفاصيل في ورقة 'سيناريوهات What-If'" if _wi_qa else _ef),
    ]:
        _kv(ws_inp, _ri, _lbl_inp, _dg_val(_v_inp), 1, 2, 3); _ri += 1
    ws_inp.row_dimensions[_ri].height = 6; _ri += 1

    # ── Section 16: مدخلات تحليل الشراء مقابل الإيجار ───────────────────
    _sec_hdr(ws_inp, _ri, 1, 3, "١٦. مدخلات تحليل الشراء مقابل الإيجار"); _ri += 1
    _mv_num_inp = float(str(payload.get("estimated_value") or 0)) if payload.get("estimated_value") else 0
    _mr_num_inp = float(str(payload.get("income_monthly_rent") or (10_000 if _wi_qa else 0)))
    for _lbl_inp, _v_inp in [
        ("القيمة السوقية (ج.م)",              f"{int(_mv_num_inp):,}" if _mv_num_inp else _ef),
        ("الإيجار الشهري (ج.م)",             f"{int(_mr_num_inp):,}" if _mr_num_inp else _ef),
        ("الإيجار السنوي (ج.م)",             f"{int(_mr_num_inp * 12):,}" if _mr_num_inp else _ef),
        ("فترة الاحتفاظ (سنوات)",            "5" if _wi_qa else _ef),
        ("معدل نمو الإيجار السنوي (%)",      "3.0" if _wi_qa else _ef),
        ("العائد البديل على رأس المال (%)",  "12.0" if _wi_qa else _ef),
        ("تكاليف الشراء والتسجيل (%)",       "3.0" if _wi_qa else _ef),
        ("تكاليف الصيانة والامتلاك (%)",     "1.0" if _wi_qa else _ef),
        ("معدل التقدير الرأسمالي السنوي (%)", "5.0" if _wi_qa else _ef),
        ("ملاحظات تحليل ش/إ",  "تفاصيل في ورقة 'شراء أم إيجار'" if _wi_qa else _ef),
    ]:
        _kv(ws_inp, _ri, _lbl_inp, _dg_val(_v_inp), 1, 2, 3); _ri += 1
    ws_inp.row_dimensions[_ri].height = 6; _ri += 1

    # ── Section 17: مدخلات ESG والاستدامة ───────────────────────────────
    _sec_hdr(ws_inp, _ri, 1, 3, "١٧. مدخلات ESG والاستدامة"); _ri += 1
    for _lbl_inp, _v_inp in [
        ("الطاقة الشمسية (0–5)",           "3" if _wi_qa else _ef),
        ("العزل الحراري (0–5)",             "2" if _wi_qa else _ef),
        ("كفاءة المياه (0–5)",              "2" if _wi_qa else _ef),
        ("قرب وسائل النقل العام (0–5)",     "4" if _wi_qa else _ef),
        ("مواد صديقة للبيئة (0–5)",         "2" if _wi_qa else _ef),
        ("كفاءة تكاليف التشغيل (0–5)",      "3" if _wi_qa else _ef),
        ("جودة إدارة المبنى (0–5)",          "3" if _wi_qa else _ef),
        ("المخاطر البيئية (0–5)",           "4" if _wi_qa else _ef),
        ("إجمالي درجة ESG (=SUM أعلاه)",   "=SUM(B{start}:B{end})".format(start=_ri-8, end=_ri-1) if _wi_qa else _ef),
        ("تعديل معدل الرسملة بسبب ESG",    "يحسب في ورقة ESG والاستدامة" if _wi_qa else _ef),
    ]:
        _kv(ws_inp, _ri, _lbl_inp, _dg_val(_v_inp), 1, 2, 3); _ri += 1
    ws_inp.row_dimensions[_ri].height = 6; _ri += 1

    # ── Section 18: مدخلات الحوكمة وجاهزية الربط بمصادر البيانات ────────
    _sec_hdr(ws_inp, _ri, 1, 3, "١٨. الحوكمة وجاهزية الربط بمصادر البيانات"); _ri += 1
    _wb_approval = req.get("approval_status", "draft_only")
    for _lbl_inp, _v_inp in [
        ("حالة اعتماد التقرير",             _wb_approval),
        ("تاريخ الإنشاء",                   (req.get("created_at") or _dg)[:19].replace("T", " ")),
        ("تاريخ آخر تحديث",                 (req.get("updated_at") or _dg)[:19].replace("T", " ")),
        ("جاهزية Source Registry",          "مرحلة مستقبلية — لم تُفعَّل بعد"),
        ("جاهزية Qdrant",                  "مرحلة مستقبلية — لم تُفعَّل بعد"),
        ("جاهزية RAG",                      "مرحلة مستقبلية — لم تُفعَّل بعد"),
        ("جاهزية روابط APIs خارجية",        "مرحلة مستقبلية — لم تُفعَّل بعد"),
        ("الحالة الراهنة",                  "يعمل بمدخلات داخلية ومحاكاة QA — لا استرجاع حي"),
    ]:
        _kv(ws_inp, _ri, _lbl_inp, _v_inp, 1, 2, 3); _ri += 1
    ws_inp.row_dimensions[_ri].height = 6; _ri += 1

    # ── Section 19: ملاحظات الخبير ────────────────────────────────────────
    _sec_hdr(ws_inp, _ri, 1, 3, "١٩. ملاحظات الخبير"); _ri += 1
    for _lbl_inp, _v_inp in [
        ("ملاحظات الخبير العامة",  _dg_val(req.get("expert_notes", ""))),
        ("ملاحظات المراجعة",       _dg_val(req.get("reconciliation_notes", ""))),
        ("ملاحظات إضافية",         _ef),
    ]:
        _kv(ws_inp, _ri, _lbl_inp, _v_inp, 1, 2, 3); _ri += 1

    ws_inp.freeze_panes = ws_inp["A3"]

    # ════════════════════════════════════════════════════════════════════════
    # Sheet 2 (was Sheet 2): غلاف وملخص
    # ════════════════════════════════════════════════════════════════════════
    ws2 = wb.create_sheet("غلاف وملخص")
    _hdr(ws2, ["الحقل", "القيمة"])
    rows2 = [
        ("رقم الطلب",                  request_id),
        ("تاريخ الإنشاء",              (req.get("created_at") or "")[:10]),
        ("اسم العميل",                  req.get("user_name", "")),
        ("الهاتف",                      req.get("phone", "")),
        ("البريد الإلكتروني",           req.get("email", "")),
        ("نوع الطلب",                   req.get("request_kind", "")),
        ("نموذج التقرير المطلوب",       _tmpl_name_ar),
        ("معرّف نموذج التقرير",         _tmpl_id or "—"),
        ("حالة الاعتماد",               req.get("approval_status", "draft_only")),
        ("طريقة الاستلام المطلوبة",     req.get("preferred_contact_method", "")),
        ("الغرض من التقييم",            payload.get("purpose", "القيمة السوقية")),
        ("تاريخ التقييم",               payload.get("valuation_date", "")),
        ("نوع العقار",                  payload.get("property_type", "")),
        ("الموقع",                      location),
        ("المساحة",                     area_s),
        ("وصف مختصر",                   (payload.get("description") or "")[:200]),
        ("حالة التقرير",                "قيد المراجعة"),
        ("تنبيه",                       "هذا ملف داخلي للخبير والإدارة فقط — لا يُشارك مع العميل"),
    ]
    for i, (k, v) in enumerate(rows2, 2):
        _row(ws2, i, k, v)
    _widths(ws2, [36, 54])

    # ════════════════════════════════════════════════════════════════════════
    # Sheet 3: مقدمة التقرير والافتراضات  (NEW — 5 forms)
    # ════════════════════════════════════════════════════════════════════════
    ws3 = wb.create_sheet("مقدمة التقرير والافتراضات")
    _rtl(ws3)
    _widths(ws3, [38, 52, 38])

    ws3.merge_cells("A1:C1")
    ws3["A1"].value     = "مقدمة التقرير والافتراضات — نماذج A–E"
    ws3["A1"].font      = F_TITLE
    ws3["A1"].fill      = _fill(C_BLUE_D)
    ws3["A1"].alignment = AL_CTR
    ws3.row_dimensions[1].height = 24

    r3 = 2
    # نموذج A — مختصر
    _sec_hdr(ws3, r3, 1, 3, "نموذج A — مقدمة مختصرة"); r3 += 1
    _kv(ws3, r3, "رقم الطلب",          request_id,                              1, 2, 3); r3 += 1
    _kv(ws3, r3, "تاريخ التقرير",       "",                                      1, 2, 3); r3 += 1
    _kv(ws3, r3, "اسم العميل",          req.get("user_name", ""),                1, 2, 3); r3 += 1
    _kv(ws3, r3, "الغرض من التقييم",   payload.get("purpose", "القيمة السوقية"), 1, 2, 3); r3 += 1
    _kv(ws3, r3, "نطاق العمل المختصر", "مراجعة البيانات والتقييم بالطرق المعتمدة", 1, 2, 3); r3 += 1
    ws3.row_dimensions[r3].height = 6; r3 += 1

    # نموذج B — كامل
    _sec_hdr(ws3, r3, 1, 3, "نموذج B — مقدمة كاملة"); r3 += 1
    _kv(ws3, r3, "جهة التكليف",        req.get("user_name", ""),    1, 2, 3); r3 += 1
    _kv(ws3, r3, "العقار محل التقييم", location,                     1, 2, 3); r3 += 1
    _kv(ws3, r3, "الغرض من التقييم",   payload.get("purpose", ""),  1, 2, 3); r3 += 1
    _kv(ws3, r3, "تاريخ التقييم الفعلي", payload.get("valuation_date", ""), 1, 2, 3); r3 += 1
    _kv(ws3, r3, "نطاق العمل التفصيلي", "يشمل: مراجعة المستندات، زيارة العقار، تطبيق طرق التقييم المعتمدة.", 1, 2, 3); r3 += 1
    _kv(ws3, r3, "المعيار المُطبَّق",  "معايير التقييم الدولية (IVSC) — المعايير المصرية للتقييم", 1, 2, 3); r3 += 1
    ws3.row_dimensions[r3].height = 6; r3 += 1

    # نموذج C — افتراضات
    _sec_hdr(ws3, r3, 1, 3, "نموذج C — الافتراضات الأساسية"); r3 += 1
    for assumption in [
        "يُفترض صحة البيانات المقدمة من العميل وسلامتها.",
        "العقار خالٍ من النزاعات والأعباء الخفية غير المُفصَّح عنها.",
        "القيمة صالحة في تاريخ التقييم المذكور فقط.",
        "بيانات المساحة صحيحة وفق ما أُفيد — لم يُجرَ فحص هندسي مستقل.",
        "لا يتضمن هذا التقرير تثبتًا قانونيًا للملكية إلا إذا نُصَّ على ذلك.",
    ]:
        _kv(ws3, r3, "افتراض", assumption, 1, 2, 3); r3 += 1
    ws3.row_dimensions[r3].height = 6; r3 += 1

    # نموذج D — نطاق العمل
    _sec_hdr(ws3, r3, 1, 3, "نموذج D — نطاق العمل والقيود"); r3 += 1
    for scope_item in [
        "البيانات المستخدمة: بيانات الطلب المقدمة من العميل والمستندات المرفقة.",
        "مدى الفحص: مراجعة مكتبية + زيارة ميدانية (إن وُردت تفاصيلها).",
        "القيود: لا يشمل التقرير الفحص الهندسي التفصيلي ما لم يُنصَّ عليه.",
        "الاستخدام المقصود: الغرض المُصرَّح به فقط — لا يُستخدم لأغراض أخرى.",
    ]:
        _kv(ws3, r3, "بند", scope_item, 1, 2, 3); r3 += 1
    ws3.row_dimensions[r3].height = 6; r3 += 1

    # نموذج E — المستندات المطلوبة
    _sec_hdr(ws3, r3, 1, 3, "نموذج E — المستندات المطلوبة للمراجعة"); r3 += 1
    for doc_req in [
        "سند الملكية / عقد البيع",
        "رسم كروكي أو مساحي للعقار",
        "صور فوتوغرافية للعقار",
        "شهادة الضرائب العقارية",
        "أي مستندات تمويلية أو إيجارية ذات صلة",
    ]:
        _kv(ws3, r3, "مستند مطلوب", doc_req, 1, 2, 3); r3 += 1

    # ════════════════════════════════════════════════════════════════════════
    # Sheet 4: بيانات العقار
    # ════════════════════════════════════════════════════════════════════════
    ws4 = wb.create_sheet("بيانات العقار")
    _hdr(ws4, ["الحقل", "القيمة"])
    rows4 = [
        ("نوع العقار",           payload.get("property_type", "")),
        ("وصف العقار",           (payload.get("description") or "")[:200]),
        ("العنوان الكامل",        location),
        ("الدولة",               payload.get("country", "")),
        ("المحافظة / المنطقة",   payload.get("region", "")),
        ("المدينة",              payload.get("city", "")),
        ("الحي / المنطقة",       payload.get("district", "")),
        ("المساحة الإجمالية (م²)", payload.get("area", "")),
        ("حالة العقار",          payload.get("condition", "")),
        ("مستوى التشطيب",        payload.get("finishing_level", "")),
        ("المرافق والخدمات",      payload.get("utilities", "")),
        ("حقوق الملكية / السند",  payload.get("ownership_type", "")),
        ("الاستخدام الحالي",      payload.get("current_use", "")),
        ("سهولة الوصول",         ""),
        ("عدد الأدوار",           ""),
        ("عمر المبنى (سنة)",     ""),
        ("الملاحظات",            (payload.get("notes") or "")),
        ("المستندات المرفقة",    doc_names_s),
    ]
    for i, (k, v) in enumerate(rows4, 2):
        _row(ws4, i, k, v)
    _widths(ws4, [32, 54])

    # ════════════════════════════════════════════════════════════════════════
    # Sheet 5: مقارنة البيوع  (multi-form A–D)
    # ════════════════════════════════════════════════════════════════════════
    ws5 = wb.create_sheet("مقارنة البيوع")
    _rtl(ws5)

    ws5.merge_cells("A1:O1")
    ws5["A1"].value     = "مقارنة البيوع — نماذج A–D"
    ws5["A1"].font      = F_TITLE
    ws5["A1"].fill      = _fill(C_BLUE_D)
    ws5["A1"].alignment = AL_CTR
    ws5.row_dimensions[1].height = 22

    r5 = 2
    # Subject area reference cell (used in adjusted-value formulas below)
    ws5["P1"].value     = float(payload.get("area") or 120)
    ws5["P1"].font      = F_LBL
    ws5["P1"].alignment = AL_CTR

    # ── جدول مقارنات سكني — مصفوفة المقارنات التفصيلية ──────────────────────
    _sec_hdr(ws5, r5, 1, 15, "جدول مقارنات سكني — مصفوفة المقارنات التفصيلية — بيانات محاكاة داخلية"); r5 += 1
    hdr_comps = [
        "رقم المقارن", "الموقع", "المساحة (م²)",
        "سعر البيع الإجمالي", "سعر المتر (=D/C)",
        "معامل الموقع", "معامل المساحة", "معامل الحالة", "معامل التشطيب", "معامل التاريخ",
        "سعر المتر المعدل (=E×PRODUCT(F:J))", "القيمة المعدلة (=K×مساحة_موضوع)",
        "الحالة", "ملاحظات الخبير",
    ]
    for ci, h in enumerate(hdr_comps, 1):
        c = ws5.cell(r5, ci, value=h)
        c.font = F_HDR; c.fill = _fill(C_BLUE_D); c.alignment = AL_CTR
    r5 += 1

    def _pn5(v, default=0):
        """Parse numeric value from formatted string."""
        try:
            if isinstance(v, (int, float)): return float(v)
            return float(str(v).replace(",", "").replace(" ج.م", "").replace("ج.م/م²", "").strip() or default)
        except (TypeError, ValueError):
            return default

    for comp in wb_comparables:
        _rn5 = r5
        _area5   = _pn5(comp.get("area"), 0)
        _price5  = _pn5(comp.get("sale_price"), 0)
        _loc5    = _pn5(comp.get("location_factor"), 1)
        _ar5     = _pn5(comp.get("area_factor"), 1)
        _cond5   = _pn5(comp.get("condition_factor"), 1)
        _fin5    = _pn5(comp.get("finishing_factor"), 1)
        _time5   = _pn5(comp.get("time_factor"), 1)
        # Write raw data cells
        ws5.cell(_rn5, 1).value  = comp.get("num", "")
        ws5.cell(_rn5, 2).value  = str(comp.get("location", ""))
        ws5.cell(_rn5, 3).value  = _area5 if _area5 else str(comp.get("area", ""))   # C
        ws5.cell(_rn5, 4).value  = _price5 if _price5 else str(comp.get("sale_price", ""))  # D
        # Formula: price/m² = sale_price / area
        ws5.cell(_rn5, 5).value  = f"=D{_rn5}/C{_rn5}" if (_area5 and _price5) else str(comp.get("price_per_m2", ""))  # E
        # Adjustment factor cells (raw numeric)
        ws5.cell(_rn5, 6).value  = _loc5   # F location_factor
        ws5.cell(_rn5, 7).value  = _ar5    # G area_factor
        ws5.cell(_rn5, 8).value  = _cond5  # H condition_factor
        ws5.cell(_rn5, 9).value  = _fin5   # I finishing_factor
        ws5.cell(_rn5, 10).value = _time5  # J time_factor
        # Formula: adj price/m² = price/m² × PRODUCT(all factors)
        ws5.cell(_rn5, 11).value = f"=E{_rn5}*PRODUCT(F{_rn5}:J{_rn5})"  # K
        # Formula: adj value = adj_price/m² × subject_area ($P$1)
        ws5.cell(_rn5, 12).value = f"=K{_rn5}*$P$1"                        # L
        ws5.cell(_rn5, 13).value = str(comp.get("status", ""))
        ws5.cell(_rn5, 14).value = str(comp.get("notes", ""))
        for ci5 in range(1, 15): ws5.cell(_rn5, ci5).alignment = AL_RT
        r5 += 1

    # Summary / AVERAGE row
    if wb_comparables:
        _comp_first = r5 - len(wb_comparables)
        _comp_last  = r5 - 1
        ws5.cell(r5, 2).value  = "متوسط / AVERAGE"; ws5.cell(r5, 2).font = F_GOLD; ws5.cell(r5, 2).fill = _fill("D4AF37")
        ws5.cell(r5, 11).value = f"=AVERAGE(K{_comp_first}:K{_comp_last})"  # avg adj price/m²
        ws5.cell(r5, 12).value = f"=AVERAGE(L{_comp_first}:L{_comp_last})"  # avg adj value
        ws5.cell(r5, 11).fill  = _fill("D4AF37"); ws5.cell(r5, 11).font = F_GOLD
        ws5.cell(r5, 12).fill  = _fill("D4AF37"); ws5.cell(r5, 12).font = F_GOLD
        for ci5 in range(1, 15): ws5.cell(r5, ci5).alignment = AL_RT
        r5 += 1

    # Summary row
    _sec_hdr(ws5, r5, 1, 15, f"ملخص: متوسط سعر المتر المعدل = {wb_avg_adj}", C_GOLD, "7A5800"); r5 += 1
    ws5.row_dimensions[r5].height = 6; r5 += 1

    # نموذج A — مقارنة مختصرة (للإشارة السريعة)
    _sec_hdr(ws5, r5, 1, 8, "نموذج A — مقارنة البيوع المختصر (للإشارة السريعة)"); r5 += 1
    for ci, h in enumerate(["العقار", "الموقع", "المساحة", "سعر البيع", "سعر المتر", "التاريخ", "التعديل", "ملاحظة"], 1):
        ws5.cell(r5, ci).value = h; ws5.cell(r5, ci).font = F_HDR
        ws5.cell(r5, ci).fill = _fill(C_BLUE_M); ws5.cell(r5, ci).alignment = AL_CTR
    r5 += 1
    for comp in wb_comparables[:4]:
        ws5.cell(r5, 1).value = f"مقارن {comp.get('num', '')}"
        ws5.cell(r5, 2).value = str(comp.get("location", ""))
        ws5.cell(r5, 3).value = str(comp.get("area", ""))
        ws5.cell(r5, 4).value = str(comp.get("sale_price", ""))
        ws5.cell(r5, 5).value = str(comp.get("price_per_m2", ""))
        ws5.cell(r5, 7).value = str(comp.get("adjusted_price_per_m2", ""))
        ws5.cell(r5, 8).value = str(comp.get("notes", ""))
        for ci in range(1, 9): ws5.cell(r5, ci).alignment = AL_RT
        r5 += 1
    ws5.row_dimensions[r5].height = 6; r5 += 1

    # نموذج B — تسويات المقارنات
    _sec_hdr(ws5, r5, 1, 6, "نموذج B — ورقة تسويات المقارنات"); r5 += 1
    for ci, h in enumerate(["بند التسوية", "مقارن 1", "مقارن 2", "مقارن 3", "مقارن 4", "ملاحظة"], 1):
        c = ws5.cell(r5, ci, value=h)
        c.font = F_HDR; c.fill = _fill(C_BLUE_M); c.alignment = AL_CTR
    r5 += 1
    adj_items = [
        ("معامل الموقع",    "location_factor"),
        ("معامل المساحة",   "area_factor"),
        ("معامل الحالة",    "condition_factor"),
        ("معامل التشطيب",   "finishing_factor"),
        ("معامل التاريخ",   "time_factor"),
        ("سعر المتر المعدل", "adjusted_price_per_m2"),
        ("القيمة المعدلة",  "adjusted_value"),
    ]
    for lbl, key in adj_items:
        ws5.cell(r5, 1).value = lbl; ws5.cell(r5, 1).alignment = AL_RT
        for ci, comp in enumerate(wb_comparables[:4], 2):
            ws5.cell(r5, ci).value = str(comp.get(key, "")); ws5.cell(r5, ci).alignment = AL_RT
        r5 += 1
    ws5.row_dimensions[r5].height = 6; r5 += 1

    # نموذج C — نتيجة طريقة المقارنة
    _sec_hdr(ws5, r5, 1, 4, "نموذج C — ملخص نتيجة طريقة المقارنة"); r5 += 1
    _ws5_sales_row = None  # will be set to the row of "القيمة المشتقة من المقارنات"
    for lbl, val in [
        ("متوسط سعر المتر المعدل", wb_avg_adj),
        ("مساحة العقار محل التقييم (م²)", payload.get("area", "")),
        ("القيمة المشتقة من المقارنات", mctx.get("sales_from_comps", "")),
        ("ملاحظات الخبير", "تحتاج مراجعة ميدانية — بيانات محاكاة داخلية لأغراض اختبار الشكل"),
    ]:
        if lbl == "القيمة المشتقة من المقارنات":
            _ws5_sales_row = r5
        _kv(ws5, r5, lbl, val, 1, 2, 4, vbg=C_GOLD_BG if val else C_WHITE); r5 += 1

    _widths(ws5, [14, 24, 10, 18, 16, 12, 12, 12, 12, 12, 18, 18, 14, 28])

    # ════════════════════════════════════════════════════════════════════════
    # Sheet 6: طريقة الدخل  (multi-form A–E)
    # ════════════════════════════════════════════════════════════════════════
    ws6 = wb.create_sheet("طريقة الدخل")
    _rtl(ws6)
    _widths(ws6, [40, 28, 50])

    ws6.merge_cells("A1:C1")
    ws6["A1"].value     = "طريقة الدخل — نماذج A–E"
    ws6["A1"].font      = F_TITLE
    ws6["A1"].fill      = _fill(C_BLUE_D)
    ws6["A1"].alignment = AL_CTR
    ws6.row_dimensions[1].height = 22

    r6 = 2
    # ── نموذج A — رسملة الدخل المختصر (بيانات محاكاة) ─────────────────────
    _sec_hdr(ws6, r6, 1, 3, "نموذج A — رسملة الدخل المختصر — بيانات محاكاة داخلية"); r6 += 1
    _kv(ws6, r6, "الإيجار الشهري",           mctx.get("income_monthly_rent", ""),  1, 2, 3, vbg=C_GOLD_BG if wb_income_noi else C_WHITE); r6 += 1
    _kv(ws6, r6, "الدخل السنوي الإجمالي",    mctx.get("income_annual_gross", ""),  1, 2, 3); r6 += 1
    _kv(ws6, r6, "نسبة الشواغر",             mctx.get("income_vacancy_rate", ""),  1, 2, 3); r6 += 1
    _kv(ws6, r6, "خصم الشواغر",             mctx.get("income_vacancy_amt", ""),   1, 2, 3); r6 += 1
    _kv(ws6, r6, "الدخل الفعلي EGI",         mctx.get("income_egi", ""),           1, 2, 3); r6 += 1
    _kv(ws6, r6, "نسبة المصاريف التشغيلية",  mctx.get("income_expense_rate", ""), 1, 2, 3); r6 += 1
    _kv(ws6, r6, "المصاريف التشغيلية",        mctx.get("income_expenses", ""),     1, 2, 3); r6 += 1
    _kv(ws6, r6, "صافي الدخل التشغيلي NOI",  wb_income_noi,                        1, 2, 3, vbg=C_GREEN if wb_income_noi else C_RED); r6 += 1
    _kv(ws6, r6, "معدل الرسملة المُطبَّق",   wb_cap_rate,                          1, 2, 3); r6 += 1
    _kv(ws6, r6, "القيمة بطريقة الدخل",      wb_income_value,                      1, 2, 3, vbg=C_GREEN if wb_income_value else C_RED); r6 += 1
    ws6.row_dimensions[r6].height = 6; r6 += 1

    # نموذج B — نموذج رسملة الدخل التقليدي (قابل للتحرير)
    _sec_hdr(ws6, r6, 1, 3, "نموذج B — نموذج رسملة الدخل التقليدي (قابل للتعديل)"); r6 += 1
    for field, val in [
        ("نوع الاستخدام",              payload.get("property_type", "")),
        ("المساحة المؤجرة (م²)",       str(payload.get("area", ""))),
        ("الإيجار الشهري",             mctx.get("income_monthly_rent", "")),
        ("الدخل السنوي الإجمالي",      mctx.get("income_annual_gross", "")),
        ("نسبة الشواغر (%)",           mctx.get("income_vacancy_rate", "")),
        ("خصم الشواغر",               mctx.get("income_vacancy_amt", "")),
        ("الدخل الفعلي EGI",           mctx.get("income_egi", "")),
        ("نسبة المصاريف التشغيلية",    mctx.get("income_expense_rate", "")),
        ("إجمالي المصاريف التشغيلية",  mctx.get("income_expenses", "")),
        ("صافي الدخل التشغيلي NOI",    wb_income_noi),
        ("معدل الرسملة المُطبَّق (%)", wb_cap_rate),
        ("القيمة بطريقة الدخل",        wb_income_value),
        ("ملاحظات الخبير",             "بيانات محاكاة داخلية — تحتاج تحقق ميداني"),
    ]:
        _kv(ws6, r6, field, val, 1, 2, 3); r6 += 1
    ws6.row_dimensions[r6].height = 6; r6 += 1

    # نموذج C — جداول إضافية
    _sec_hdr(ws6, r6, 1, 3, "نموذج C — جداول إضافية (Excel placeholder للخبير)"); r6 += 1
    ws6.cell(r6, 1).value = "يمكن للخبير إضافة جداول إيجارية إضافية في هذا القسم."
    ws6.cell(r6, 1).alignment = AL_RT; r6 += 1
    ws6.row_dimensions[r6].height = 6; r6 += 1

    # نموذج D — NOI تفصيلي
    _sec_hdr(ws6, r6, 1, 3, "نموذج D — تحليل صافي الدخل التشغيلي NOI (تفصيلي)"); r6 += 1
    for field, val in [
        ("إجمالي الإيجارات المحصلة",       mctx.get("income_annual_gross", "")),
        ("إيرادات أخرى",                  _dg),
        ("إجمالي الدخل الفعلي EGI",        mctx.get("income_egi", "")),
        ("مصاريف الإدارة والصيانة",        mctx.get("income_expenses", "")),
        ("الضرائب والتأمين",               _dg),
        ("الاستهلاك والاحتياطيات",          _dg),
        ("إجمالي المصاريف التشغيلية",      mctx.get("income_expenses", "")),
        ("صافي الدخل التشغيلي NOI",        wb_income_noi),
    ]:
        _kv(ws6, r6, field, val, 1, 2, 3); r6 += 1

    # نموذج E — تحقق بالمعادلات (Formula Verification Model)
    ws6.row_dimensions[r6].height = 6; r6 += 1
    _sec_hdr(ws6, r6, 1, 3, "نموذج E — نموذج رسملة الدخل بالمعادلات (Formula Verification)"); r6 += 1
    def _pn6(v, default=0):
        try:
            if isinstance(v, (int, float)): return float(v)
            return float(str(v).replace(",", "").replace(" ج.م", "").replace("%", "").strip() or default)
        except (TypeError, ValueError): return default
    _inc6_monthly_row = r6
    ws6.cell(r6, 1).value = "الإيجار الشهري (مدخل)"; ws6.cell(r6, 1).alignment = AL_RT
    _m6v = _pn6(mctx.get("income_monthly_rent", "0"))
    ws6.cell(r6, 2).value = _m6v; ws6.cell(r6, 2).alignment = AL_RT; r6 += 1
    _inc6_ann_row = r6
    ws6.cell(r6, 1).value = "الدخل السنوي الإجمالي (=شهري×12)"; ws6.cell(r6, 1).alignment = AL_RT
    ws6.cell(r6, 2).value = f"=B{_inc6_monthly_row}*12"; ws6.cell(r6, 2).alignment = AL_RT; r6 += 1
    _inc6_vr_row = r6
    ws6.cell(r6, 1).value = "نسبة الشواغر (مدخل)"; ws6.cell(r6, 1).alignment = AL_RT
    _vr6 = _pn6(mctx.get("income_vacancy_rate", "5%"), 5) / 100.0 if "%" in str(mctx.get("income_vacancy_rate","")) else _pn6(mctx.get("income_vacancy_rate","0"), 0.05)
    ws6.cell(r6, 2).value = _vr6; ws6.cell(r6, 2).alignment = AL_RT; r6 += 1
    _inc6_va_row = r6
    ws6.cell(r6, 1).value = "خصم الشواغر (=سنوي×نسبة)"; ws6.cell(r6, 1).alignment = AL_RT
    ws6.cell(r6, 2).value = f"=B{_inc6_ann_row}*B{_inc6_vr_row}"; ws6.cell(r6, 2).alignment = AL_RT; r6 += 1
    _inc6_egi_row = r6
    ws6.cell(r6, 1).value = "الدخل الفعلي EGI (=سنوي-شواغر)"; ws6.cell(r6, 1).alignment = AL_RT
    ws6.cell(r6, 2).value = f"=B{_inc6_ann_row}-B{_inc6_va_row}"; ws6.cell(r6, 2).alignment = AL_RT; r6 += 1
    _inc6_er_row = r6
    ws6.cell(r6, 1).value = "نسبة المصاريف التشغيلية (مدخل)"; ws6.cell(r6, 1).alignment = AL_RT
    _er6 = _pn6(mctx.get("income_expense_rate", "25%"), 25) / 100.0 if "%" in str(mctx.get("income_expense_rate","")) else _pn6(mctx.get("income_expense_rate","0"), 0.25)
    ws6.cell(r6, 2).value = _er6; ws6.cell(r6, 2).alignment = AL_RT; r6 += 1
    _inc6_exp_row = r6
    ws6.cell(r6, 1).value = "المصاريف التشغيلية (=EGI×نسبة)"; ws6.cell(r6, 1).alignment = AL_RT
    ws6.cell(r6, 2).value = f"=B{_inc6_egi_row}*B{_inc6_er_row}"; ws6.cell(r6, 2).alignment = AL_RT; r6 += 1
    _inc6_noi_row = r6
    ws6.cell(r6, 1).value = "NOI (=EGI-مصاريف)"; ws6.cell(r6, 1).alignment = AL_RT
    ws6.cell(r6, 2).value = f"=B{_inc6_egi_row}-B{_inc6_exp_row}"; ws6.cell(r6, 2).fill = _fill(C_GREEN); ws6.cell(r6, 2).alignment = AL_RT; r6 += 1
    _inc6_cr_row = r6
    ws6.cell(r6, 1).value = "معدل الرسملة (مدخل)"; ws6.cell(r6, 1).alignment = AL_RT
    _cr6 = _pn6(wb_cap_rate.replace("%","") if isinstance(wb_cap_rate,str) else str(wb_cap_rate), 8) / 100.0
    ws6.cell(r6, 2).value = _cr6 if _cr6 > 0 else 0.08; ws6.cell(r6, 2).alignment = AL_RT; r6 += 1
    ws6.cell(r6, 1).value = "القيمة بطريقة الدخل (=NOI÷معدل)"; ws6.cell(r6, 1).alignment = AL_RT
    ws6.cell(r6, 2).value = f"=B{_inc6_noi_row}/B{_inc6_cr_row}"; ws6.cell(r6, 2).fill = _fill(C_GOLD_BG); ws6.cell(r6, 2).font = F_GOLD; ws6.cell(r6, 2).alignment = AL_RT; r6 += 1

    # ════════════════════════════════════════════════════════════════════════
    # Sheet 7: DCF  (NEW — 4 forms A–D)
    # ════════════════════════════════════════════════════════════════════════
    ws7 = wb.create_sheet("DCF")
    _rtl(ws7)
    _widths(ws7, [38, 26, 26, 26, 26, 26])

    ws7.merge_cells("A1:F1")
    ws7["A1"].value     = "طريقة التدفقات النقدية المخصومة DCF — نماذج A–D"
    ws7["A1"].font      = F_TITLE
    ws7["A1"].fill      = _fill(C_BLUE_D)
    ws7["A1"].alignment = AL_CTR
    ws7.row_dimensions[1].height = 22

    r7 = 2
    # ── نموذج A — افتراضات DCF وملخص ────────────────────────────────────
    _sec_hdr(ws7, r7, 1, 4, "نموذج A — DCF مختصر — افتراضات وملخص النتائج — بيانات محاكاة"); r7 += 1
    for field, val in [
        ("فترة التحليل (سنوات)", "5"),
        ("معدل الخصم WACC (%)",   mctx.get("dcf_discount_rate_pct", "")),
        ("معدل نمو الإيجارات (%)", mctx.get("dcf_growth_rate_pct", "")),
        ("معدل الرسملة النهائي Terminal Cap Rate (%)", mctx.get("dcf_terminal_cap_pct", "")),
        ("القيمة النهائية Terminal Value",             mctx.get("dcf_terminal_value", "")),
        ("القيمة الحالية للقيمة النهائية",             mctx.get("dcf_pv_terminal", "")),
        ("إجمالي القيمة الحالية للتدفقات",            mctx.get("dcf_pv_cashflows", "")),
        ("قيمة DCF الإجمالية",                        wb_dcf_value),
        ("ملاحظات", "محاكاة داخلية — لا تُستخدم كدليل سوقي"),
    ]:
        _kv(ws7, r7, field, val, 1, 2, 4, vbg=C_GREEN if val and field.startswith("قيمة DCF") else C_WHITE); r7 += 1
    ws7.row_dimensions[r7].height = 6; r7 += 1

    # نموذج B — جدول DCF الاحترافي (5 سنوات)
    _sec_hdr(ws7, r7, 1, 6, "نموذج B — جدول DCF الاحترافي (5 سنوات) — بيانات محاكاة"); r7 += 1
    for ci, h in enumerate(["السنة", "NOI", "معامل الخصم", "القيمة الحالية", "", ""], 1):
        c = ws7.cell(r7, ci, value=h)
        c.font = F_HDR; c.fill = _fill(C_BLUE_D); c.alignment = AL_CTR
    r7 += 1
    for row_data in wb_dcf_rows:
        ws7.cell(r7, 1).value = row_data.get("year", "")
        ws7.cell(r7, 2).value = row_data.get("noi", "")
        ws7.cell(r7, 3).value = row_data.get("discount_factor", "")
        ws7.cell(r7, 4).value = row_data.get("pv", "")
        for ci in range(1, 5): ws7.cell(r7, ci).alignment = AL_RT
        r7 += 1
    # Terminal value row
    ws7.cell(r7, 1).value = "القيمة النهائية Terminal Value"
    ws7.cell(r7, 2).value = mctx.get("dcf_terminal_value", "")
    ws7.cell(r7, 4).value = mctx.get("dcf_pv_terminal", "")
    ws7.cell(r7, 1).font = F_LBL; ws7.cell(r7, 1).alignment = AL_RT; r7 += 1
    # Total row
    ws7.cell(r7, 1).value = "إجمالي القيمة الحالية (DCF)"; ws7.cell(r7, 1).font = F_LBL
    ws7.cell(r7, 4).value = wb_dcf_value
    ws7.cell(r7, 4).fill  = _fill(C_GREEN)
    for ci in range(1, 5): ws7.cell(r7, ci).alignment = AL_RT
    r7 += 1
    ws7.row_dimensions[r7].height = 6; r7 += 1

    # نموذج C — افتراضات DCF التفصيلية
    _sec_hdr(ws7, r7, 1, 4, "نموذج C — افتراضات DCF التفصيلية (قابل للتحرير)"); r7 += 1
    for field, val in [
        ("معدل الخصم WACC (%)",           mctx.get("dcf_discount_rate_pct", "")),
        ("معدل نمو الإيجارات (%)",        mctx.get("dcf_growth_rate_pct", "")),
        ("معدل الشواغر (%)",              mctx.get("income_vacancy_rate", "")),
        ("معدل الرسملة النهائي (%)",      mctx.get("dcf_terminal_cap_pct", "")),
        ("قيمة إعادة البيع Terminal Value", mctx.get("dcf_terminal_value", "")),
        ("مبررات معدل الخصم",             "معدل السوق + علاوة مخاطر — محاكاة داخلية"),
        ("مصدر بيانات الدخل",             "بيانات الطلب — تحتاج تحقق ميداني"),
    ]:
        _kv(ws7, r7, field, val, 1, 2, 4); r7 += 1
    ws7.row_dimensions[r7].height = 6; r7 += 1

    # نموذج D — معدل الخصم / Terminal (4-method derivation)
    _sec_hdr(ws7, r7, 1, 4, "نموذج D — اشتقاق معدل الخصم (4 طرق)"); r7 += 1
    if wb_dr_methods:
        for dm in wb_dr_methods:
            _kv(ws7, r7, dm.get("method", ""), "", 1, 2, 4, lbg="2D6A9F"); r7 += 1
            ws7.cell(r7 - 1, 2).font = Font(bold=True, color="FFFFFF", name="Arial", size=9)
            for comp_lbl, comp_val in dm.get("components", []):
                _kv(ws7, r7, f"  {comp_lbl}", comp_val, 1, 2, 4); r7 += 1
            _kv(ws7, r7, "معدل مشار (Indicated Rate)", dm.get("indicated_rate", _dg),
                1, 2, 4, vbg="EBF3FB"); r7 += 1
            ws7.row_dimensions[r7].height = 4; r7 += 1
        _kv(ws7, r7, "متوسط معدل الخصم", mctx.get("dr_average", _dg), 1, 2, 4, vbg="D4AF37"); r7 += 1
        _kv(ws7, r7, "معدل الخصم المختار", mctx.get("dr_expert_selected", _dg), 1, 2, 4, vbg="D4AF37"); r7 += 1
        _kv(ws7, r7, "ملاحظات", mctx.get("dr_notes", _dg), 1, 2, 4); r7 += 1
    else:
        for field in ["معدل الفائدة الخالي من المخاطر (%)", "علاوة مخاطر السوق العقاري (%)",
                      "علاوة المخاطر الخاصة بالأصل (%)", "معدل الخصم الإجمالي WACC (%)",
                      "منهجية حساب القيمة النهائية", "القيمة النهائية المحسوبة"]:
            _kv(ws7, r7, field, _dg, 1, 2, 4); r7 += 1
    ws7.row_dimensions[r7].height = 6; r7 += 1

    # نموذج E — معدل الرسملة النهائي (4 طرق)
    _sec_hdr(ws7, r7, 1, 4, "نموذج E — معدل الرسملة النهائي (4 طرق) — غير معدل الخصم"); r7 += 1
    if wb_cr_methods:
        for cm in wb_cr_methods:
            _kv(ws7, r7, cm.get("method_name", ""), "", 1, 2, 4, lbg="4A3000"); r7 += 1
            ws7.cell(r7 - 1, 2).font = Font(bold=True, color="FFFFFF", name="Arial", size=9)
            inputs = cm.get("inputs") or {}
            for k, v in inputs.items():
                lbl_map = {
                    "debt_ratio":           "نسبة الدين",
                    "mortgage_constant":    "ثابت الرهن",
                    "equity_ratio":         "نسبة حقوق الملكية",
                    "equity_dividend_rate": "عائد حقوق الملكية",
                    "yield_rate":           "معدل العائد",
                    "growth_rate":          "معدل النمو طويل الأمد",
                    "risk_free_rate":       "معدل الخلو من المخاطر",
                    "property_risk":        "علاوة مخاطر العقار",
                    "liquidity_premium":    "علاوة السيولة",
                    "management_risk":      "علاوة الإدارة",
                    "growth_deduction":     "خصم النمو",
                }
                _kv(ws7, r7, f"  {lbl_map.get(k, k)}", v, 1, 2, 4); r7 += 1
            if cm.get("comparables"):
                for cmp in cm["comparables"]:
                    _kv(ws7, r7,
                        f"  مقارن {cmp.get('num','')} — {cmp.get('location','')}",
                        f"NOI: {cmp.get('noi','')} | قيمة: {cmp.get('value','')} | معدل: {cmp.get('cap_rate','')}",
                        1, 2, 4); r7 += 1
            if cm.get("formula"):
                _kv(ws7, r7, "  المعادلة", cm["formula"], 1, 2, 4); r7 += 1
            _kv(ws7, r7, "معدل رسملة مشار", cm.get("indicated_cap_rate", _dg),
                1, 2, 4, vbg="FFF9E6"); r7 += 1
            ws7.row_dimensions[r7].height = 4; r7 += 1
        _kv(ws7, r7, "متوسط معدل الرسملة النهائي (4 طرق)", wb_cr_avg, 1, 2, 4, vbg="D4AF37"); r7 += 1
        _kv(ws7, r7, "معدل الرسملة النهائي المختار",        wb_cr_expert, 1, 2, 4, vbg="D4AF37"); r7 += 1
        _kv(ws7, r7, "ملاحظات الخبير",                      wb_cr_notes, 1, 2, 4); r7 += 1
        if wb_cr_disclaimer:
            ws7.cell(r7, 1).value = wb_cr_disclaimer
            ws7.cell(r7, 1).font  = Font(color="B43200", name="Arial", size=8, italic=True)
            ws7.merge_cells(f"A{r7}:F{r7}"); r7 += 1
    else:
        for field in ["معدل الرسملة — الاستخلاص المباشر", "معدل الرسملة — حزمة الاستثمار",
                      "معدل الرسملة — معدل الخصم ناقص النمو", "معدل الرسملة — البناء التراكمي",
                      "متوسط معدل الرسملة", "معدل الرسملة المختار"]:
            _kv(ws7, r7, field, _dg, 1, 2, 4); r7 += 1

    # نموذج F — DCF بالمعادلات (Formula Verification)
    ws7.row_dimensions[r7].height = 6; r7 += 1
    _sec_hdr(ws7, r7, 1, 5, "نموذج F — تحقق DCF بالمعادلات — 5 سنوات + قيمة نهائية"); r7 += 1
    for _ci7f, _h7f in enumerate(["السنة", "NOI", "معدل النمو", "معامل الخصم (1/(1+r)^n)", "القيمة الحالية (=B×D)"], 1):
        _c7f = ws7.cell(r7, _ci7f, value=_h7f)
        _c7f.font = F_HDR; _c7f.fill = _fill(C_BLUE_M); _c7f.alignment = AL_CTR
    r7 += 1
    def _pn7(v, default=0):
        try:
            if isinstance(v, (int, float)): return float(v)
            return float(str(v).replace(",", "").replace(" ج.م", "").replace("%", "").strip() or default)
        except (TypeError, ValueError): return default
    try:
        _dcf7_noi1 = _pn7(wb_income_noi.replace(",","").replace(" ج.م","") if isinstance(wb_income_noi,str) else str(wb_income_noi), 0)
    except: _dcf7_noi1 = 0
    try:
        _dcf7_gr   = _pn7(mctx.get("dcf_growth_rate_pct","3%").replace("%","") if isinstance(mctx.get("dcf_growth_rate_pct",""),str) else str(mctx.get("dcf_growth_rate_pct",3)), 3) / 100.0
    except: _dcf7_gr = 0.03
    try:
        _dcf7_dr   = _pn7(mctx.get("dcf_discount_rate_pct","10%").replace("%","") if isinstance(mctx.get("dcf_discount_rate_pct",""),str) else str(mctx.get("dcf_discount_rate_pct",10)), 10) / 100.0
    except: _dcf7_dr = 0.10
    try:
        _dcf7_tc   = _pn7(mctx.get("dcf_terminal_cap_pct","8%").replace("%","") if isinstance(mctx.get("dcf_terminal_cap_pct",""),str) else str(mctx.get("dcf_terminal_cap_pct",8)), 8) / 100.0
    except: _dcf7_tc = 0.08
    _dcf7_start = r7
    for _yr7 in range(1, 6):
        ws7.cell(r7, 1).value = _yr7
        if _yr7 == 1:
            ws7.cell(r7, 2).value = _dcf7_noi1
        else:
            ws7.cell(r7, 2).value = f"=B{r7-1}*(1+C{r7})"
        ws7.cell(r7, 3).value = _dcf7_gr
        ws7.cell(r7, 4).value = f"=1/(1+{round(_dcf7_dr,4)})^A{r7}"
        ws7.cell(r7, 5).value = f"=B{r7}*D{r7}"
        for _ci7 in range(1, 6): ws7.cell(r7, _ci7).alignment = AL_RT
        r7 += 1
    _dcf7_tv_row = r7
    ws7.cell(r7, 1).value = "القيمة النهائية Terminal Value"; ws7.cell(r7, 1).font = F_LBL
    ws7.cell(r7, 2).value = f"=B{r7-1}/{round(_dcf7_tc,4)}" if _dcf7_tc else _dg
    ws7.cell(r7, 4).value = f"=1/(1+{round(_dcf7_dr,4)})^5"
    ws7.cell(r7, 5).value = f"=B{r7}*D{r7}"
    for _ci7 in range(1, 6): ws7.cell(r7, _ci7).alignment = AL_RT; r7 += 1
    ws7.cell(r7, 1).value = "قيمة DCF الإجمالية"; ws7.cell(r7, 1).font = F_GOLD
    ws7.cell(r7, 5).value = f"=SUM(E{_dcf7_start}:E{r7-1})"
    ws7.cell(r7, 5).fill  = _fill(C_GOLD_BG); ws7.cell(r7, 5).font = F_GOLD; ws7.cell(r7, 5).alignment = AL_RT; r7 += 1

    # ════════════════════════════════════════════════════════════════════════
    # Sheet 8: طريقة التكلفة  (multi-form A–E)
    # ════════════════════════════════════════════════════════════════════════
    ws8 = wb.create_sheet("طريقة التكلفة")
    _rtl(ws8)
    _widths(ws8, [40, 28, 50])

    ws8.merge_cells("A1:C1")
    ws8["A1"].value     = "طريقة التكلفة — نماذج A–E"
    ws8["A1"].font      = F_TITLE
    ws8["A1"].fill      = _fill(C_BLUE_D)
    ws8["A1"].alignment = AL_CTR
    ws8.row_dimensions[1].height = 22

    r8 = 2
    # ── نموذج A — طريقة التكلفة المختصر (بيانات محاكاة) ──────────────────
    _sec_hdr(ws8, r8, 1, 3, "نموذج A — طريقة التكلفة المختصر — بيانات محاكاة داخلية"); r8 += 1
    for field, val in [
        ("قيمة نصيب الأرض",             wb_cost_land),
        ("تكلفة الإنشاء كجديد",         wb_cost_repl),
        ("إجمالي الإهلاك",              wb_cost_depr),
        ("القيمة الاستبدالية الصافية",   mctx.get("cost_depreciated_imprv", "")),
        ("القيمة بطريقة التكلفة",        wb_cost_value),
    ]:
        _kv(ws8, r8, field, val, 1, 2, 3, vbg=C_GREEN if (val and field.startswith("القيمة بطريقة")) else C_WHITE); r8 += 1
    ws8.row_dimensions[r8].height = 6; r8 += 1

    # نموذج B — تفصيلي (قابل للتعديل)
    _sec_hdr(ws8, r8, 1, 3, "نموذج B — طريقة التكلفة التفصيلي (قابل للتعديل)"); r8 += 1
    for field, val in [
        ("مسطح الجزء محل التقييم (م²)",         str(payload.get("area", ""))),
        ("سعر متر الإنشاء كجديد",               mctx.get("cost_replacement_per_m2", "")),
        ("تكلفة الإنشاء كجديد (م² × سعر المتر)", wb_cost_repl),
        ("قيمة نصيب الأرض",                     wb_cost_land),
        ("نسبة الإهلاك الجسدي (%)",              mctx.get("cost_physical_depr_pct", "")),
        ("نسبة الإهلاك الوظيفي (%)",             mctx.get("cost_functional_depr_pct", "")),
        ("إجمالي الإهلاك (%)",                   mctx.get("cost_total_depr_pct", "")),
        ("إجمالي الإهلاك (ج.م)",                 wb_cost_depr),
        ("قيمة المباني بعد الإهلاك",             mctx.get("cost_depreciated_imprv", "")),
        ("القيمة بطريقة التكلفة (أرض + مباني)", wb_cost_value),
        ("ملاحظات الخبير", "بيانات محاكاة داخلية — تحتاج تحقق فني"),
    ]:
        _kv(ws8, r8, field, val, 1, 2, 3); r8 += 1
    ws8.row_dimensions[r8].height = 6; r8 += 1

    # نموذج C — نصيب الأرض (uses land value context)
    _sec_hdr(ws8, r8, 1, 3, "نموذج C — تحليل نصيب الأرض"); r8 += 1
    _lv_recon = mctx.get("land_value_reconciled", "")
    for field, val in [
        ("مساحة نصيب الأرض (م²)",             str(payload.get("land_share_area", "")) or _dg),
        ("سعر المتر المتوسط (أرض)",            _dg_val(mctx.get("avg_land_price", ""))),
        ("قيمة نصيب الأرض بالمقارنة البيعية", _dg_val(mctx.get("land_value_by_sales", ""))),
        ("قيمة نصيب الأرض بالاستخلاص",       _dg_val(wb_extr.get("extr_land_share_value", ""))),
        ("قيمة الأرض المتوفقة (Reconciled)",  _dg_val(_lv_recon)),
        ("القيمة المختارة لنصيب الأرض",       _dg_val(mctx.get("land_value_expert_selected", ""))),
    ]:
        _kv(ws8, r8, field, val, 1, 2, 3,
            vbg="D4AF37" if field.startswith("القيمة المختارة") and val != _dg else "FFFFFF"); r8 += 1
    ws8.row_dimensions[r8].height = 6; r8 += 1

    # نموذج D — جدول الإهلاك التفصيلي
    _sec_hdr(ws8, r8, 1, 3, "نموذج D — جدول الإهلاك"); r8 += 1
    for field, val in [
        ("الإهلاك الجسدي القابل للإصلاح",       _dg),
        ("الإهلاك الجسدي غير القابل للإصلاح",   _dg),
        ("الإهلاك الوظيفي / التقني (%)",         _dg_val(mctx.get("cost_functional_depr_pct", ""))),
        ("الإهلاك الاقتصادي / الخارجي (%)",      _dg_val(mctx.get("cost_external_depr_pct", ""))),
        ("إجمالي الإهلاك (%)",                   _dg_val(mctx.get("cost_total_depr_pct", ""))),
        ("إجمالي الإهلاك (ج.م)",                 _dg_val(mctx.get("cost_total_depr_amt", ""))),
        ("القيمة الاستبدالية بعد الإهلاك",       _dg_val(mctx.get("cost_depreciated_imprv", ""))),
    ]:
        _kv(ws8, r8, field, val, 1, 2, 3); r8 += 1
    ws8.row_dimensions[r8].height = 6; r8 += 1

    # نموذج E — Excel placeholder
    _sec_hdr(ws8, r8, 1, 3, "نموذج E — جداول تكلفة إضافية (Excel placeholder)"); r8 += 1
    ws8.cell(r8, 1).value = "يمكن للخبير إضافة جداول تكلفة تفصيلية إضافية في هذا القسم."
    ws8.cell(r8, 1).alignment = AL_RT; r8 += 1

    # نموذج F — تحقق طريقة التكلفة بالمعادلات (Formula Verification)
    ws8.row_dimensions[r8].height = 6; r8 += 1
    _sec_hdr(ws8, r8, 1, 3, "نموذج F — تحقق طريقة التكلفة بالمعادلات"); r8 += 1
    def _pn8(v, default=0):
        try:
            if isinstance(v, (int, float)): return float(v)
            return float(str(v).replace(",", "").replace(" ج.م", "").replace("ج.م/م²", "").replace("%", "").strip() or default)
        except (TypeError, ValueError): return default
    _cost8_area_row = r8
    ws8.cell(r8, 1).value = "المساحة الإجمالية (م²) — مدخل"; ws8.cell(r8, 1).alignment = AL_RT
    ws8.cell(r8, 2).value = float(payload.get("area") or 120); ws8.cell(r8, 2).alignment = AL_RT; r8 += 1
    _cost8_rate_row = r8
    ws8.cell(r8, 1).value = "سعر متر الإنشاء كجديد (ج.م/م²) — مدخل"; ws8.cell(r8, 1).alignment = AL_RT
    ws8.cell(r8, 2).value = _pn8(mctx.get("cost_replacement_per_m2", "0")); ws8.cell(r8, 2).alignment = AL_RT; r8 += 1
    _cost8_repl_row = r8
    ws8.cell(r8, 1).value = "تكلفة الإنشاء كجديد (=مساحة×سعر_المتر)"; ws8.cell(r8, 1).alignment = AL_RT
    ws8.cell(r8, 2).value = f"=B{_cost8_area_row}*B{_cost8_rate_row}"; ws8.cell(r8, 2).alignment = AL_RT; r8 += 1
    _cost8_pdr_row = r8
    ws8.cell(r8, 1).value = "نسبة الإهلاك الجسدي (%) — مدخل"; ws8.cell(r8, 1).alignment = AL_RT
    _pd8 = _pn8(mctx.get("cost_physical_depr_pct","10%"), 10) / 100.0
    ws8.cell(r8, 2).value = _pd8; ws8.cell(r8, 2).alignment = AL_RT; r8 += 1
    _cost8_pda_row = r8
    ws8.cell(r8, 1).value = "الإهلاك الجسدي (=تكلفة×نسبة)"; ws8.cell(r8, 1).alignment = AL_RT
    ws8.cell(r8, 2).value = f"=B{_cost8_repl_row}*B{_cost8_pdr_row}"; ws8.cell(r8, 2).alignment = AL_RT; r8 += 1
    _cost8_fdr_row = r8
    ws8.cell(r8, 1).value = "نسبة الإهلاك الوظيفي (%) — مدخل"; ws8.cell(r8, 1).alignment = AL_RT
    _fd8 = _pn8(mctx.get("cost_functional_depr_pct","5%"), 5) / 100.0
    ws8.cell(r8, 2).value = _fd8; ws8.cell(r8, 2).alignment = AL_RT; r8 += 1
    _cost8_fda_row = r8
    ws8.cell(r8, 1).value = "الإهلاك الوظيفي (=تكلفة×نسبة)"; ws8.cell(r8, 1).alignment = AL_RT
    ws8.cell(r8, 2).value = f"=B{_cost8_repl_row}*B{_cost8_fdr_row}"; ws8.cell(r8, 2).alignment = AL_RT; r8 += 1
    # Part D: External / economic obsolescence
    _cost8_edr_row = r8
    ws8.cell(r8, 1).value = "نسبة الإهلاك الاقتصادي / الخارجي (%) — مدخل"; ws8.cell(r8, 1).alignment = AL_RT
    _ed8 = _pn8(mctx.get("cost_external_depr_pct", "0%"), 0) / 100.0
    ws8.cell(r8, 2).value = _ed8; ws8.cell(r8, 2).alignment = AL_RT; r8 += 1
    _cost8_eda_row = r8
    ws8.cell(r8, 1).value = "الإهلاك الاقتصادي / الخارجي (=تكلفة×نسبة)"; ws8.cell(r8, 1).alignment = AL_RT
    ws8.cell(r8, 2).value = f"=B{_cost8_repl_row}*B{_cost8_edr_row}"; ws8.cell(r8, 2).alignment = AL_RT; r8 += 1
    _cost8_tda_row = r8
    ws8.cell(r8, 1).value = "إجمالي الإهلاك (=SUM)"; ws8.cell(r8, 1).alignment = AL_RT
    ws8.cell(r8, 2).value = f"=SUM(B{_cost8_pda_row}:B{r8-1})"; ws8.cell(r8, 2).alignment = AL_RT; r8 += 1
    _cost8_db_row = r8
    ws8.cell(r8, 1).value = "قيمة المباني بعد الإهلاك (=تكلفة-إهلاك)"; ws8.cell(r8, 1).alignment = AL_RT
    ws8.cell(r8, 2).value = f"=B{_cost8_repl_row}-B{_cost8_tda_row}"; ws8.cell(r8, 2).alignment = AL_RT; r8 += 1
    _cost8_land_row = r8
    ws8.cell(r8, 1).value = "قيمة نصيب الأرض — مدخل"; ws8.cell(r8, 1).alignment = AL_RT
    ws8.cell(r8, 2).value = _pn8(wb_cost_land); ws8.cell(r8, 2).alignment = AL_RT; r8 += 1
    ws8.cell(r8, 1).value = "القيمة بطريقة التكلفة (=أرض+مباني)"; ws8.cell(r8, 1).alignment = AL_RT
    ws8.cell(r8, 2).value = f"=B{_cost8_land_row}+B{_cost8_db_row}"
    ws8.cell(r8, 2).fill  = _fill(C_GOLD_BG); ws8.cell(r8, 2).font = F_GOLD; ws8.cell(r8, 2).alignment = AL_RT; r8 += 1

    # ════════════════════════════════════════════════════════════════════════
    # Sheet AVM: AVM — التقييم الآلي المبدئي (نماذج A–H)
    # ════════════════════════════════════════════════════════════════════════
    ws_avm = wb.create_sheet("AVM")
    _rtl(ws_avm)
    _widths(ws_avm, [42, 28, 50])

    ws_avm.merge_cells("A1:C1")
    ws_avm["A1"].value     = "نموذج AVM — التقييم الآلي المبدئي — نماذج A–H"
    ws_avm["A1"].font      = F_TITLE
    ws_avm["A1"].fill      = _fill(C_BLUE_D)
    ws_avm["A1"].alignment = AL_CTR
    ws_avm.row_dimensions[1].height = 22

    ra = 2
    # نموذج A — AVM مختصر (بيانات من الطلب)
    _avm_base = payload.get("base_price_per_m2", "")
    _avm_loc  = payload.get("location_factor", "")
    _avm_cond = payload.get("condition_factor", "")
    _avm_fin  = payload.get("finishing_factor", "")
    _avm_area = payload.get("area", "")
    _sec_hdr(ws_avm, ra, 1, 3, "نموذج A — AVM مختصر — بيانات من الطلب"); ra += 1
    for field, val in [
        ("نوع العقار",               payload.get("property_type", "")),
        ("الموقع / المنطقة",         location),
        ("المساحة (م²)",             str(_avm_area) if _avm_area else ""),
        ("القيمة الآلية المبدئية",   _n(_avm_val) if _avm_val else ""),
        ("الحد الأدنى للنطاق",       _n(_avm_low) if _avm_low else ""),
        ("الحد الأعلى للنطاق",       _n(_avm_high) if _avm_high else ""),
        ("درجة الثقة",               str(payload.get("avm_confidence_score", ""))),
        ("حالة جودة البيانات",        str(payload.get("avm_data_quality_status", ""))),
        ("ملاحظات AVM",              str(payload.get("avm_notes", ""))),
    ]:
        _kv(ws_avm, ra, field, val, 1, 2, 3, vbg=C_GOLD_BG if field.startswith("القيمة") and val else C_WHITE); ra += 1
    ws_avm.row_dimensions[ra].height = 6; ra += 1

    # نموذج B — حساب AVM: سعر المتر × المساحة × معاملات
    _sec_hdr(ws_avm, ra, 1, 3, "نموذج B — حساب AVM: سعر المتر × المساحة × معاملات التعديل"); ra += 1
    try:
        _base_v = float(str(_avm_base)) if _avm_base else 0
        _area_v = float(str(_avm_area)) if _avm_area else 0
        _basic_val = _base_v * _area_v
        _after_loc = _basic_val * float(str(_avm_loc)) if _avm_loc else _basic_val
        _after_cond = _after_loc * float(str(_avm_cond)) if _avm_cond else _after_loc
        _after_fin = _after_cond * float(str(_avm_fin)) if _avm_fin else _after_cond
    except (TypeError, ValueError):
        _basic_val = _after_loc = _after_cond = _after_fin = 0
    for field, val in [
        ("سعر المتر الأساسي  base_price_per_m2",   f"{int(_avm_base):,} ج.م/م²" if _avm_base else ""),
        ("المساحة (م²)",                           str(_avm_area) if _avm_area else ""),
        ("القيمة الأساسية  =  سعر × مساحة",        f"{int(_basic_val):,} ج.م" if _basic_val else ""),
        ("معامل الموقع  location_factor",           str(_avm_loc) if _avm_loc else ""),
        ("القيمة بعد تعديل الموقع",                 f"{int(_after_loc):,} ج.م" if _after_loc else ""),
        ("معامل الحالة  condition_factor",           str(_avm_cond) if _avm_cond else ""),
        ("القيمة بعد تعديل الحالة",                 f"{int(_after_cond):,} ج.م" if _after_cond else ""),
        ("معامل التشطيب  finishing_factor",          str(_avm_fin) if _avm_fin else ""),
        ("القيمة الآلية المبدئية المحسوبة",         f"{int(_after_fin):,} ج.م" if _after_fin else ""),
    ]:
        _kv(ws_avm, ra, field, val, 1, 2, 3, vbg=C_GREEN if field.startswith("القيمة الآلية المبدئية") and val else C_WHITE); ra += 1
    ws_avm.row_dimensions[ra].height = 6; ra += 1

    # نموذج C — نطاق الثقة / Confidence Range
    _sec_hdr(ws_avm, ra, 1, 3, "نموذج C — نطاق الثقة / Confidence Range"); ra += 1
    for field, val in [
        ("القيمة الآلية المبدئية",   _n(_avm_val) if _avm_val else ""),
        ("الحد الأدنى للنطاق",       _n(_avm_low) if _avm_low else ""),
        ("الحد الأعلى للنطاق",       _n(_avm_high) if _avm_high else ""),
        ("درجة الثقة",               str(payload.get("avm_confidence_score", ""))),
        ("تفسير نطاق الثقة",         "نطاق ±10% من القيمة المبدئية — مبدئي / استرشادي"),
    ]:
        _kv(ws_avm, ra, field, val, 1, 2, 3); ra += 1
    ws_avm.row_dimensions[ra].height = 6; ra += 1

    # نموذج D — معامل الموقع
    _sec_hdr(ws_avm, ra, 1, 3, "نموذج D — معامل المنطقة / Location Factor"); ra += 1
    for field, val in [
        ("المنطقة / zone",           location),
        ("معامل الموقع",              str(_avm_loc) if _avm_loc else ""),
        ("مصدر معامل الموقع",        "مدخلات الطلب — يحتاج تحقق ميداني"),
    ]:
        _kv(ws_avm, ra, field, val, 1, 2, 3); ra += 1
    ws_avm.row_dimensions[ra].height = 6; ra += 1

    # نموذج E — معامل الحالة والتشطيب
    _sec_hdr(ws_avm, ra, 1, 3, "نموذج E — معامل الحالة والتشطيب"); ra += 1
    for field, val in [
        ("حالة العقار",              payload.get("condition", "")),
        ("معامل الحالة",             str(_avm_cond) if _avm_cond else ""),
        ("مستوى التشطيب",           payload.get("finishing_level", "")),
        ("معامل التشطيب",            str(_avm_fin) if _avm_fin else ""),
    ]:
        _kv(ws_avm, ra, field, val, 1, 2, 3); ra += 1
    ws_avm.row_dimensions[ra].height = 6; ra += 1

    # نموذج F — جودة البيانات
    _sec_hdr(ws_avm, ra, 1, 3, "نموذج F — جودة البيانات / Data Quality Score"); ra += 1
    for field, val in [
        ("حالة جودة البيانات",        str(payload.get("avm_data_quality_status", ""))),
        ("مصادر البيانات المستخدمة",  "بيانات الطلب — لا يشمل Qdrant أو الإنترنت"),
        ("مدى توافر المقارنات",        "متاح من محاكاة داخلية" if wb_has_comps else "يحتاج تحقق ميداني"),
        ("توصية الخبير",              "راجع نتيجة AVM مع المقارنات الفعلية"),
    ]:
        _kv(ws_avm, ra, field, val, 1, 2, 3); ra += 1
    ws_avm.row_dimensions[ra].height = 6; ra += 1

    # نموذج G — AVM vs قيمة الخبير
    _sec_hdr(ws_avm, ra, 1, 3, "نموذج G — القيمة الآلية مقابل قيمة الخبير"); ra += 1
    for field, val in [
        ("القيمة الآلية AVM",         _n(_avm_val) if _avm_val else ""),
        ("قيمة الخبير النهائية",       ""),
        ("سبب تجاوز القيمة الآلية",   ""),
        ("ملاحظات الخبير على AVM",    ""),
    ]:
        _kv(ws_avm, ra, field, val, 1, 2, 3); ra += 1
    ws_avm.row_dimensions[ra].height = 6; ra += 1

    # نموذج H — تنبيه
    _sec_hdr(ws_avm, ra, 1, 3, "نموذج H — تنبيه الاستخدام الصحيح لـ AVM"); ra += 1
    ws_avm.cell(ra, 1).value = (
        "AVM في هذه النسخة أداة مساعدة ضمن ملف المراجعة، ولا تحل محل تقدير الخبير. "
        "لا يشمل هذا النموذج Qdrant أو الإنترنت. جميع البيانات من مدخلات الطلب."
    )
    ws_avm.cell(ra, 1).alignment = AL_RT; ws_avm.cell(ra, 1).font = Font(color="B43200", name="Arial", size=9)
    ws_avm.row_dimensions[ra].height = 8; ra += 1

    ws_avm.cell(ra, 1).value = (
        "تنبيه: AVM في هذه النسخة أداة مساعدة ضمن ملف المراجعة، ولا تحل محل تقدير الخبير أو "
        "مراجعة المقارنات والمستندات. لا يتضمن هذا النموذج استرجاعًا آليًا من الإنترنت أو Qdrant."
    )
    ws_avm.cell(ra, 1).alignment = AL_RT
    ws_avm.cell(ra, 1).font = Font(bold=False, color="B43200", name="Arial", size=9)
    ws_avm.row_dimensions[ra].height = 8; ra += 1

    # نموذج I — جدول انحدار AVM (AVM regression feature table)
    if wb_avm_reg:
        ws_avm.row_dimensions[ra].height = 6; ra += 1
        _widths(ws_avm, [42, 16, 20, 22, 38])
        _sec_hdr(ws_avm, ra, 1, 5, "نموذج I — جدول الانحدار / AVM Regression Feature Table"); ra += 1
        for ci, h in enumerate(["المتغير / Feature", "القيمة", "المعامل", "الأثر", "ملاحظات"], 1):
            c = ws_avm.cell(ra, ci, value=h)
            c.font = F_HDR; c.fill = _fill(C_BLUE_D); c.alignment = AL_CTR
        ra += 1
        for reg_row in wb_avm_reg:
            ws_avm.cell(ra, 1).value = reg_row.get("feature", "")
            ws_avm.cell(ra, 2).value = reg_row.get("value", "")
            ws_avm.cell(ra, 3).value = reg_row.get("coeff", "")
            ws_avm.cell(ra, 4).value = reg_row.get("effect", "")
            ws_avm.cell(ra, 5).value = reg_row.get("notes", "")
            for ci in range(1, 6): ws_avm.cell(ra, ci).alignment = AL_RT
            ra += 1
        for field, val in [
            ("القيمة الأساسية (Base Value)",   mctx.get("avm_reg_base_value", _dg)),
            ("مجموع المعاملات",                mctx.get("avm_reg_coeff_total", _dg)),
            ("القيمة المتوقعة (Predicted)",    mctx.get("avm_reg_predicted", _dg)),
            ("تعديل الخبير (Residual)",         mctx.get("avm_reg_residual", _dg)),
            ("القيمة النهائية لـ AVM",         mctx.get("avm_reg_final", _dg)),
            ("نطاق الثقة (Confidence Band)",   mctx.get("avm_reg_confidence_band", _dg)),
        ]:
            _kv(ws_avm, ra, field, val, 1, 2, 5,
                vbg="D4AF37" if "النهائية" in field and val != _dg else "FFFFFF"); ra += 1
        ws_avm.row_dimensions[ra].height = 4; ra += 1
        _disc2 = ws_avm.cell(ra, 1, mctx.get("avm_reg_limitations", ""))
        _disc2.font = Font(color="B43200", name="Arial", size=8, italic=True)
        ws_avm.merge_cells(f"A{ra}:E{ra}"); ra += 1

    # نموذج J — ربط مصادر الأسعار بـ AVM
    ws_avm.row_dimensions[ra].height = 6; ra += 1
    _avm_sources = [s for s in wb_price_sources if "AVM" in s.get("used_in_methods", "")]
    _sec_hdr(ws_avm, ra, 1, 5, "نموذج J — ربط مصادر الأسعار (Source Linkage)"); ra += 1
    for ci, h in enumerate(["كود المصدر", "نوع المصدر", "المنطقة", "سعر/م²", "الثقة"], 1):
        c = ws_avm.cell(ra, ci, value=h)
        c.font = F_HDR; c.fill = _fill("2D5A27"); c.alignment = AL_CTR
    ra += 1
    if _avm_sources:
        for src in _avm_sources:
            ws_avm.cell(ra, 1).value = src.get("source_registry_id", "")
            ws_avm.cell(ra, 2).value = src.get("source_type", "")
            ws_avm.cell(ra, 3).value = src.get("district", "")
            ws_avm.cell(ra, 4).value = src.get("price_per_m2", "")
            ws_avm.cell(ra, 5).value = src.get("source_confidence", "")
            for ci in range(1, 6): ws_avm.cell(ra, ci).alignment = AL_RT
            ra += 1
    else:
        ws_avm.cell(ra, 1).value = "لم تُربط مصادر أسعار بعد — يحتاج استكمال بواسطة الخبير"
        ws_avm.cell(ra, 1).font = Font(color="B43200", name="Arial", size=9)
        ws_avm.merge_cells(f"A{ra}:E{ra}"); ra += 1

    # ════════════════════════════════════════════════════════════════════════
    # Sheet 9: توفيق النتائج  (multi-form A–E)
    # ════════════════════════════════════════════════════════════════════════
    ws9 = wb.create_sheet("توفيق النتائج")
    _rtl(ws9)
    _widths(ws9, [40, 26, 50])

    ws9.merge_cells("A1:C1")
    ws9["A1"].value     = "توفيق النتائج — نماذج A–G"
    ws9["A1"].font      = F_TITLE
    ws9["A1"].fill      = _fill(C_BLUE_D)
    ws9["A1"].alignment = AL_CTR
    ws9.row_dimensions[1].height = 22

    # ── helper values for reconciliation ────────────────────────────────────
    def _parse_num(v):
        """Parse a numeric or pre-formatted value to float. Returns None on failure."""
        if v is None or v == "":
            return None
        try:
            if isinstance(v, (int, float)):
                return float(v)
            # Strip Arabic formatting: commas, currency suffix, units
            cleaned = (str(v).replace(",", "").replace(" ج.م", "")
                       .replace("ج.م/م²", "").replace("/م²", "").strip())
            return float(cleaned) if cleaned else None
        except (TypeError, ValueError):
            return None

    _rec_sales_raw  = _parse_num(
        payload.get("sales_comparison_value") or payload.get("sales_value")
        or mctx.get("sales_from_comps", "")
    )
    _rec_income_raw = _parse_num(payload.get("income_value") or mctx.get("income_value_calc", ""))
    _rec_cost_raw   = _parse_num(payload.get("cost_value") or mctx.get("cost_value_calc", ""))
    _rec_avm_raw    = _parse_num(payload.get("avm_value") or _avm_val)
    _rec_dcf_raw    = _parse_num(mctx.get("dcf_value_calc", ""))
    _rec_expert_raw = _parse_num(payload.get("expert_recommended_value", ""))
    _rec_notes      = payload.get("reconciliation_notes", "")

    _rec_sales  = f"{int(_rec_sales_raw):,} ج.م"  if _rec_sales_raw  is not None else ""
    _rec_income = f"{int(_rec_income_raw):,} ج.م" if _rec_income_raw is not None else ""
    _rec_cost   = f"{int(_rec_cost_raw):,} ج.م"   if _rec_cost_raw   is not None else ""
    _rec_avm    = f"{int(_rec_avm_raw):,} ج.م"    if _rec_avm_raw    is not None else ""
    _rec_dcf    = f"{int(_rec_dcf_raw):,} ج.م"    if _rec_dcf_raw    is not None else ""

    def _wval(s, i, c, w_s=0.40, w_i=0.40, w_c=0.20):
        sv, iv, cv = _parse_num(s), _parse_num(i), _parse_num(c)
        if sv is None or iv is None or cv is None:
            return ""
        return f"{int(sv*w_s + iv*w_i + cv*w_c):,} ج.م"

    def _wval4(s, i, c, a, w_s=0.35, w_i=0.25, w_c=0.20, w_a=0.20):
        sv, iv, cv, av = _parse_num(s), _parse_num(i), _parse_num(c), _parse_num(a)
        if any(v is None for v in [sv, iv, cv, av]):
            return ""
        return f"{int(sv*w_s + iv*w_i + cv*w_c + av*w_a):,} ج.م"

    def _wval5(s, i, c, a, d, w_s=0.30, w_i=0.20, w_c=0.15, w_a=0.20, w_d=0.15):
        sv, iv, cv, av, dv = _parse_num(s), _parse_num(i), _parse_num(c), _parse_num(a), _parse_num(d)
        if any(v is None for v in [sv, iv, cv, av, dv]):
            return ""
        return f"{int(sv*w_s + iv*w_i + cv*w_c + av*w_a + dv*w_d):,} ج.م"

    try:
        _rec_approved = f"{int(_rec_expert_raw):,} ج.م" if _rec_expert_raw is not None else ""
        _sens_low  = f"{int(_rec_expert_raw*0.90):,} ج.م" if _rec_expert_raw is not None else ""
        _sens_high = f"{int(_rec_expert_raw*1.10):,} ج.م" if _rec_expert_raw is not None else ""
    except (TypeError, ValueError):
        _rec_approved = _sens_low = _sens_high = ""

    r9 = 2
    # نموذج A — مختصر
    _sec_hdr(ws9, r9, 1, 3, "نموذج A — توفيق مختصر"); r9 += 1
    for field, val in [
        ("القيمة المعتمدة من الخبير", _rec_approved),
        ("أساس الاختيار",            _rec_notes or "قرار الخبير"),
        ("حد الحساسية (−10%)",        _sens_low),
        ("حد الحساسية (+10%)",        _sens_high),
        ("قرار الخبير",               ""),
    ]:
        _kv(ws9, r9, field, val, 1, 2, 3, vbg=C_GOLD_BG if field.startswith("القيمة") and val else C_WHITE); r9 += 1
    ws9.row_dimensions[r9].height = 6; r9 += 1

    # نموذج B — توفيق بالثلاث طرق
    _sec_hdr(ws9, r9, 1, 3, "نموذج B — توفيق بالثلاث طرق"); r9 += 1
    for field, val in [
        ("قيمة طريقة مقارنة البيوع",  _rec_sales),
        ("قيمة طريقة الدخل",          _rec_income),
        ("قيمة طريقة التكلفة",        _rec_cost),
        ("القيمة المرجحة 40/40/20",    _wval(_rec_sales, _rec_income, _rec_cost)),
        ("ملاحظات التوفيق",           _rec_notes),
    ]:
        _kv(ws9, r9, field, val, 1, 2, 3, vbg=C_GREEN if "المرجحة" in field and val else C_WHITE); r9 += 1
    ws9.row_dimensions[r9].height = 6; r9 += 1

    # نموذج C — توفيق بالأوزان 40/40/20
    _sec_hdr(ws9, r9, 1, 3, "نموذج C — توفيق بالأوزان 40/40/20"); r9 += 1
    for field, val in [
        ("قيمة مقارنة البيوع",         _rec_sales),
        ("وزن مقارنة البيوع %",        "40"),
        ("قيمة طريقة الدخل",           _rec_income),
        ("وزن طريقة الدخل %",          "40"),
        ("قيمة طريقة التكلفة",         _rec_cost),
        ("وزن طريقة التكلفة %",        "20"),
        ("القيمة المرجحة 40/40/20",    _wval(_rec_sales, _rec_income, _rec_cost)),
    ]:
        _kv(ws9, r9, field, val, 1, 2, 3, vbg=C_GREEN if "المرجحة" in field and val else C_WHITE); r9 += 1
    ws9.row_dimensions[r9].height = 6; r9 += 1

    # نموذج D — للخبير
    _sec_hdr(ws9, r9, 1, 3, "نموذج D — توفيق الخبير (قابل للتعديل)"); r9 += 1
    for field, val in [
        ("القيمة التي يوصي بها الخبير", _rec_approved),
        ("قرار الخبير",                 ""),
        ("مبررات التوفيق التفصيلية",    payload.get("decision_reason", "")),
        ("الطريقة الأقوى وسببها",        "مقارنة البيوع — لتوافر بيانات السوق"),
        ("تحفظات الخبير",               ""),
    ]:
        _kv(ws9, r9, field, val, 1, 2, 3, vbg=C_GOLD_BG if "يوصي" in field and val else C_WHITE); r9 += 1
    ws9.row_dimensions[r9].height = 6; r9 += 1

    # نموذج E — حساسية ±10%
    _sec_hdr(ws9, r9, 1, 3, "نموذج E — تحليل الحساسية ±10%"); r9 += 1
    for field, val in [
        ("القيمة المُعتمدة",      _rec_approved),
        ("الحد الأدنى (−10%)",    _sens_low),
        ("الحد الأعلى (+10%)",    _sens_high),
        ("نطاق الحساسية",         f"{_sens_low} — {_sens_high}" if _sens_low and _sens_high else ""),
        ("ملاحظات الحساسية",      "نطاق يعتمد على قيمة الخبير ± 10%"),
    ]:
        _kv(ws9, r9, field, val, 1, 2, 3); r9 += 1
    ws9.row_dimensions[r9].height = 6; r9 += 1

    # نموذج F — توفيق يشمل AVM (أربع طرق)
    _sec_hdr(ws9, r9, 1, 3, "نموذج F — توفيق يشمل AVM (أربع طرق)"); r9 += 1
    for field, val in [
        ("قيمة مقارنة البيوع",           _rec_sales),
        ("وزن مقارنة البيوع %",          "35"),
        ("قيمة طريقة الدخل",             _rec_income),
        ("وزن طريقة الدخل %",            "25"),
        ("قيمة طريقة التكلفة",           _rec_cost),
        ("وزن طريقة التكلفة %",          "20"),
        ("قيمة AVM",                      _rec_avm),
        ("وزن AVM %",                    "20"),
        ("القيمة المرجحة (أربع طرق)",    _wval4(_rec_sales, _rec_income, _rec_cost, _rec_avm)),
        ("ملاحظات",                       "AVM كطريقة مساعدة — الوزن قابل للتعديل بمعرفة الخبير"),
    ]:
        _kv(ws9, r9, field, val, 1, 2, 3, vbg=C_GREEN if "المرجحة" in field and val else C_WHITE); r9 += 1
    ws9.row_dimensions[r9].height = 6; r9 += 1

    # نموذج G — توفيق يشمل AVM + DCF (خمس طرق)
    _sec_hdr(ws9, r9, 1, 3, "نموذج G — توفيق يشمل AVM + DCF (خمس طرق)"); r9 += 1
    for field, val in [
        ("قيمة مقارنة البيوع",           _rec_sales),
        ("وزن مقارنة البيوع %",          "30"),
        ("قيمة طريقة الدخل",             _rec_income),
        ("وزن طريقة الدخل %",            "20"),
        ("قيمة طريقة التكلفة",           _rec_cost),
        ("وزن طريقة التكلفة %",          "15"),
        ("قيمة AVM",                      _rec_avm),
        ("وزن AVM %",                    "20"),
        ("قيمة DCF",                      _rec_dcf),
        ("وزن DCF %",                    "15"),
        ("القيمة المرجحة (خمس طرق)",     _wval5(_rec_sales, _rec_income, _rec_cost, _rec_avm, _rec_dcf)),
        ("ملاحظات الخبير",               _rec_notes),
    ]:
        _kv(ws9, r9, field, val, 1, 2, 3, vbg=C_GREEN if "المرجحة" in field and val else C_WHITE); r9 += 1

    # نموذج H — توفيق بالمعادلات (Formula Reconciliation)
    ws9.row_dimensions[r9].height = 6; r9 += 1
    _sec_hdr(ws9, r9, 1, 4, "نموذج H — توفيق بالمعادلات — القيمة المرجحة = Σ(قيمة × وزن)"); r9 += 1
    for _ci9h, _h9h in enumerate(["طريقة التقييم", "القيمة (ج.م)", "الوزن", "القيمة المرجحة (=B×C)"], 1):
        _c9h = ws9.cell(r9, _ci9h, value=_h9h)
        _c9h.font = F_HDR; _c9h.fill = _fill(C_BLUE_M); _c9h.alignment = AL_CTR
    r9 += 1
    # Use cross-sheet formula for sales value when the source row is known
    _sales_h_val = (
        f"='مقارنة البيوع'!B{_ws5_sales_row}"
        if _ws5_sales_row else (_rec_sales_raw or 0)
    )
    _rec9_methods9 = [
        ("مقارنة البيوع", _sales_h_val,         0.40),
        ("طريقة الدخل",   _rec_income_raw or 0, 0.40),
        ("طريقة التكلفة", _rec_cost_raw or 0,   0.20),
    ]
    _rec9_data_start = r9
    for _mn9, _mv9, _mw9 in _rec9_methods9:
        ws9.cell(r9, 1).value = _mn9; ws9.cell(r9, 1).alignment = AL_RT
        ws9.cell(r9, 2).value = _mv9; ws9.cell(r9, 2).alignment = AL_RT
        ws9.cell(r9, 3).value = _mw9; ws9.cell(r9, 3).alignment = AL_RT
        ws9.cell(r9, 4).value = f"=B{r9}*C{r9}"
        ws9.cell(r9, 4).fill  = _fill("EBF3FB"); ws9.cell(r9, 4).alignment = AL_RT; r9 += 1
    _rec9_total_row = r9
    ws9.cell(r9, 1).value = "إجمالي القيمة المرجحة"; ws9.cell(r9, 1).font = F_GOLD; ws9.cell(r9, 1).fill = _fill(C_GOLD_BG)
    ws9.cell(r9, 4).value = f"=SUM(D{_rec9_data_start}:D{r9-1})"
    ws9.cell(r9, 4).fill  = _fill(C_GOLD_BG); ws9.cell(r9, 4).font = F_GOLD; ws9.cell(r9, 4).alignment = AL_RT; r9 += 1
    ws9.cell(r9, 1).value = "حد الحساسية (−10%)"; ws9.cell(r9, 1).alignment = AL_RT
    ws9.cell(r9, 4).value = f"=D{_rec9_total_row}*0.9"; ws9.cell(r9, 4).alignment = AL_RT; r9 += 1
    ws9.cell(r9, 1).value = "حد الحساسية (+10%)"; ws9.cell(r9, 1).alignment = AL_RT
    ws9.cell(r9, 4).value = f"=D{_rec9_total_row}*1.1"; ws9.cell(r9, 4).alignment = AL_RT; r9 += 1

    # ════════════════════════════════════════════════════════════════════════
    # Sheet 10: الخلاصة والصياغة النهائية  (NEW — 5 forms A–E)
    # ════════════════════════════════════════════════════════════════════════
    ws10 = wb.create_sheet("الخلاصة والصياغة النهائية")
    _rtl(ws10)
    _widths(ws10, [38, 52, 36])

    ws10.merge_cells("A1:C1")
    ws10["A1"].value     = "الخلاصة والصياغة النهائية — نماذج A–E"
    ws10["A1"].font      = F_TITLE
    ws10["A1"].fill      = _fill(C_BLUE_D)
    ws10["A1"].alignment = AL_CTR
    ws10.row_dimensions[1].height = 22

    r10 = 2
    # نموذج A — خلاصة ملخص
    _sec_hdr(ws10, r10, 1, 3, "نموذج A — خلاصة تقرير ملخص"); r10 += 1
    for field in ["القيمة المُعتمدة", "غرض التقييم", "تاريخ التقييم",
                  "اسم الخبير", "رقم القيد / الترخيص", "تاريخ الإصدار"]:
        _kv(ws10, r10, field, "", 1, 2, 3); r10 += 1
    ws10.row_dimensions[r10].height = 6; r10 += 1

    # نموذج B — خلاصة كامل
    _sec_hdr(ws10, r10, 1, 3, "نموذج B — خلاصة تقرير كامل"); r10 += 1
    for field in ["القيمة السوقية النهائية المُوصى بها", "حساسية القيمة −10%", "حساسية القيمة +10%",
                  "الطريقة الأساسية للتقييم", "وزن مقارنة البيوع %", "وزن طريقة الدخل %",
                  "وزن طريقة التكلفة %", "ملاحظات الخبير النهائية", "شهادة الخبير"]:
        _kv(ws10, r10, field, "", 1, 2, 3); r10 += 1
    ws10.row_dimensions[r10].height = 6; r10 += 1

    # نموذج C — تمويل
    _sec_hdr(ws10, r10, 1, 3, "نموذج C — خلاصة التمويل البنكي"); r10 += 1
    for field in ["القيمة السوقية", "نسبة التمويل LTV (%)", "الحد الأعلى للتمويل",
                  "شروط الرهن", "توصية الخبير للبنك"]:
        _kv(ws10, r10, field, "", 1, 2, 3); r10 += 1
    ws10.row_dimensions[r10].height = 6; r10 += 1

    # نموذج D — محكمة
    _sec_hdr(ws10, r10, 1, 3, "نموذج D — خلاصة تقرير المحكمة"); r10 += 1
    for field in ["القيمة السوقية للنزاع", "تاريخ التقييم الرسمي", "المستندات الداعمة",
                  "شهادة الخبير للمحكمة", "ملاحظة قانونية"]:
        _kv(ws10, r10, field, "", 1, 2, 3); r10 += 1
    ws10.row_dimensions[r10].height = 6; r10 += 1

    # نموذج E — IFRS
    _sec_hdr(ws10, r10, 1, 3, "نموذج E — خلاصة IFRS / Fair Value"); r10 += 1
    for field in ["القيمة العادلة Fair Value", "تصنيف المدخلات (Level 1/2/3)",
                  "معيار التقييم (IFRS 13)", "طريقة التقييم المُطبَّقة",
                  "المدخلات الرئيسية وافتراضاتها", "تاريخ القيمة العادلة"]:
        _kv(ws10, r10, field, "", 1, 2, 3); r10 += 1

    # ════════════════════════════════════════════════════════════════════════
    # Sheet 11: المستندات
    # ════════════════════════════════════════════════════════════════════════
    ws11 = wb.create_sheet("المستندات")
    _hdr(ws11, ["اسم المستند", "نوع المستند", "حالة المراجعة", "ملاحظات الخبير"])
    for i, dm in enumerate(docs_meta or [], 2):
        _row(ws11, i,
             dm.get("original_filename", ""),
             dm.get("document_role", "supporting_documents"),
             "قيد المراجعة",
             "")
    _widths(ws11, [44, 24, 24, 44])

    # ════════════════════════════════════════════════════════════════════════
    # Sheet 12: سجل المراجعة
    # ════════════════════════════════════════════════════════════════════════
    ws12 = wb.create_sheet("سجل المراجعة")
    _hdr(ws12, ["التاريخ والوقت", "الإجراء / الحدث", "المستخدم / الدور", "الملاحظة"])
    _rtl(ws12)
    now_str   = (req.get("created_at") or "")[:19].replace("T", " ")
    upd_str   = (req.get("updated_at") or now_str)[:19].replace("T", " ")
    _status   = req.get("approval_status", "draft_only")
    _audit_row = 2
    # ── Lifecycle rows ────────────────────────────────────────────────────
    _lifecycle = [
        (now_str,  "استلام الطلب من العميل",         "العميل / النظام",
         f"إنشاء الطلب {request_id} — الحالة الأولية: draft_only"),
        (now_str,  "إصدار التقرير الأولي (PDF)",      "النظام",
         "تم إصدار نسخة المسودة الأولية (simple_valuation_draft.pdf) غير المعتمدة"),
        (now_str,  "إنشاء طلب خبير ومصنف المراجعة",  "النظام",
         f"تم إنشاء expert_review_{request_id}.xlsx وإرساله للخبير"),
    ]
    if _tmpl_id:
        _lifecycle.insert(1, (now_str, "تحديد نموذج التقرير", "العميل",
                               f"نموذج: {_tmpl_name_ar} ({_tmpl_id})"))
    if _status in ("under_review", "needs_documents", "approved_pending_report",
                   "rejected", "certified_report_generated"):
        _lifecycle.append((upd_str, "بدء المراجعة من قِبَل الخبير", "الخبير / المشرف",
                            "انتقل الطلب إلى مرحلة under_review"))
    if _status in ("needs_documents",):
        _lifecycle.append((upd_str, "طلب مستندات إضافية", "الخبير",
                            req.get("requested_documents") or "مستندات محددة بواسطة الخبير"))
    if _status in ("approved_pending_report", "certified_report_generated"):
        _lifecycle.append((upd_str, "الموافقة على التقرير — في انتظار الإصدار", "الخبير / المشرف",
                            req.get("expert_notes") or "تمت الموافقة"))
    if _status == "certified_report_generated":
        _lifecycle.append((upd_str, "إصدار التقرير المعتمد (Certified PDF)", "الخبير / المشرف",
                            "تم إصدار certified_valuation_report.pdf — النسخة النهائية المعتمدة"))
    if _status == "rejected":
        _lifecycle.append((upd_str, "رفض الطلب", "الخبير / المشرف",
                            req.get("decision_reason") or "تم الرفض"))
    for _ts, _act, _usr, _note in _lifecycle:
        _row(ws12, _audit_row, _ts, _act, _usr, _note)
        _audit_row += 1
    _widths(ws12, [25, 38, 30, 58])

    # ════════════════════════════════════════════════════════════════════════
    # Sheet 13: محاكاة التقييم المحترف (internal — never exposed to ordinary users)
    # ════════════════════════════════════════════════════════════════════════
    ws13 = wb.create_sheet("محاكاة التقييم المحترف")
    _rtl(ws13)
    _widths(ws13, [32, 26, 32, 26])
    r13  = 1
    _is_qa = bool(payload.get("_qa_simulation"))

    def _pv(val_from_payload, qa_fallback):
        return str(val_from_payload) if val_from_payload else (qa_fallback if _is_qa else "")

    def _wt_row(ws, rn, method_name, raw_val, wt_str):
        """Write one weighted-method row; return formatted weighted-value string."""
        try:
            v_n = float(str(raw_val).replace(",", "").replace(" ج.م", "").strip())
            w_n = float(str(wt_str).replace("%", "").strip()) / 100.0
            v_disp = f"{int(v_n):,} ج.م"
            wv_s   = f"{int(v_n * w_n):,} ج.م"
        except Exception:
            v_disp = str(raw_val) if raw_val else ""
            wv_s   = ""
        for col, v in enumerate([method_name, v_disp, wt_str, wv_s], 1):
            ch = ws.cell(row=rn, column=col, value=v)
            ch.font = F_VAL
            ch.alignment = AL_RT
        return wv_s

    # ── A: Asset Classification & Location ───────────────────────────────
    _sec_hdr(ws13, r13, 1, 4, "بيانات تصنيف الأصول والموقع — محاكاة التقييم المحترف"); r13 += 1
    for _lbl, _val in [
        ("نوع الأصول (الفئة)",    _pv(payload.get("asset_family"),  "عقار سكني")),
        ("النوع الفرعي للأصل",   _pv(payload.get("asset_subtype"), "شقة")),
        ("الموقع / المنطقة",      _pv(payload.get("location"),      location or "مدينة نصر - المنطقة الثامنة")),
        ("الإحداثيات الجغرافية", _pv(payload.get("coordinates"),   "30.0723, 31.3324")),
        ("عرض الشارع",            _pv(str(payload.get("street_width") or ""), "12 م")),
        ("الواجهة (م)",           _pv(str(payload.get("frontage") or ""),     "8 م")),
    ]:
        _kv(ws13, r13, _lbl, _val, 1, 2, 4); r13 += 1

    # ── B: Purpose Route & Governance ────────────────────────────────────
    _sec_hdr(ws13, r13, 1, 4, "مسار الغرض والحوكمة"); r13 += 1
    for _lbl, _val in [
        ("مسار الغرض الأساسي",   _pv(payload.get("purpose_route"),           "mortgage_valuation")),
        ("المسار الفرعي",         _pv(payload.get("purpose_subroute"),        "basel_iii_ltv")),
        ("مستوى IFRS",            _pv(payload.get("ifrs_level"),              "Level 2")),
        ("مسار الحوكمة النشط",  _pv(payload.get("active_route"),            "Basel III LTV — رهن عقاري")),
        ("الموافقة البشرية",      _pv(payload.get("human_approval_status"),  "مطلوب")),
        ("حالة التقرير",          _pv(payload.get("report_status"),          "مسودة — قيد المراجعة")),
    ]:
        _kv(ws13, r13, _lbl, _val, 1, 2, 4); r13 += 1

    # ── C: Technical Inputs ───────────────────────────────────────────────
    _sec_hdr(ws13, r13, 1, 4, "المدخلات التقنية للتقييم المحترف"); r13 += 1
    _ti13 = payload.get("technical_inputs") or {}
    if isinstance(_ti13, str):
        try:
            _ti13 = json.loads(_ti13)
        except Exception:
            _ti13 = {}
    def _ti13_get(key, qa_fallback):
        return _pv(_ti13.get(key) or payload.get(key), qa_fallback)
    for _lbl, _val in [
        ("معدل الاستهلاك",     _ti13_get("depreciation_factor", "25%")),
        ("العمر الفعلي",        _ti13_get("effective_age",       "8 سنوات")),
        ("العمر الاقتصادي",    _ti13_get("economic_life",       "50 سنة")),
        ("تكلفة الإنشاء/م²",  _ti13_get("construction_cost",   "6,000 ج.م/م²")),
        ("حالة التشغيل",        _ti13_get("operating_status",    "مشغول")),
        ("مستوى التشطيب",      _pv(payload.get("finishing") or payload.get("finishing_level"), "تشطيب متوسط")),
        ("الحالة",              _pv(payload.get("condition"),  "جيد")),
        ("رقم الطابق",          _ti13_get("floor",               "3")),
    ]:
        _kv(ws13, r13, _lbl, _val, 1, 2, 4); r13 += 1

    # ── D: Weighted Valuation Engine ──────────────────────────────────────
    _sec_hdr(ws13, r13, 1, 4, "محرك القيمة المرجح — بيانات محاكاة"); r13 += 1
    for col, h in enumerate(["طريقة التقييم", "القيمة ج.م", "الوزن %", "القيمة المرجحة ج.م"], 1):
        _ch = ws13.cell(row=r13, column=col, value=h)
        _ch.font = F_SEC; _ch.fill = _fill(C_BLUE_M); _ch.alignment = AL_CTR
    r13 += 1
    _vw13 = payload.get("valuation_weights") or {}
    if isinstance(_vw13, str):
        try:
            _vw13 = json.loads(_vw13)
        except Exception:
            _vw13 = {}
    _ps_val = payload.get("sales_value",  "") or (3000000  if _is_qa else "")
    _ps_wt  = _vw13.get("sales",  "") or payload.get("sales_weight",  "") or ("40%" if _is_qa else "")
    _pi_val = payload.get("income_value", "") or wb_income_value or (2415789 if _is_qa else "")
    _pi_wt  = _vw13.get("income", "") or payload.get("income_weight", "") or ("35%" if _is_qa else "")
    _pc_val = payload.get("cost_value",   "") or wb_cost_value   or (1410000 if _is_qa else "")
    _pc_wt  = _vw13.get("cost",   "") or payload.get("cost_weight",   "") or ("25%" if _is_qa else "")
    _wv13_s = _wt_row(ws13, r13, "مقارنة البيوع", _ps_val, _ps_wt); r13 += 1
    _wv13_i = _wt_row(ws13, r13, "طريقة الدخل",   _pi_val, _pi_wt); r13 += 1
    _wv13_c = _wt_row(ws13, r13, "طريقة التكلفة", _pc_val, _pc_wt); r13 += 1
    # Total weighted value row
    try:
        _total13 = sum(
            int(x.replace(",", "").replace(" ج.م", "").strip())
            for x in [_wv13_s, _wv13_i, _wv13_c] if x
        )
        _total13_s = f"{_total13:,} ج.م"
    except Exception:
        _total13_s = ""
    ws13.merge_cells(f"A{r13}:C{r13}")
    _tc_lbl = ws13.cell(row=r13, column=1, value="إجمالي القيمة المرجحة")
    _tc_lbl.font = F_GOLD; _tc_lbl.fill = _fill(C_GOLD_BG); _tc_lbl.alignment = AL_RT
    _tc_val = ws13.cell(row=r13, column=4, value=_total13_s)
    _tc_val.font = F_GOLD; _tc_val.fill = _fill(C_GOLD_BG); _tc_val.alignment = AL_RT
    r13 += 1
    # Sensitivity ±10%
    try:
        _tv13 = int(str(_total13_s).replace(",", "").replace(" ج.م", "").strip()) if _total13_s else 0
        _sens13_lo = f"{int(_tv13 * 0.90):,} ج.م"
        _sens13_hi = f"{int(_tv13 * 1.10):,} ج.م"
    except Exception:
        _sens13_lo = _sens13_hi = ""
    _kv(ws13, r13, "نطاق الحساسية (−10%)", _sens13_lo, 1, 2, 4); r13 += 1
    _kv(ws13, r13, "نطاق الحساسية (+10%)", _sens13_hi, 1, 2, 4); r13 += 1

    # ── E: AVM ────────────────────────────────────────────────────────────
    _sec_hdr(ws13, r13, 1, 4, "قيمة AVM الآلية — بيانات من الطلب"); r13 += 1
    _p13_avm_v    = (f"{_n(_avm_val)} ج.م"  if _avm_val  else ("3,055,500 ج.م" if _is_qa else ""))
    _p13_avm_low  = (f"{_n(_avm_low)} ج.م"  if _avm_low  else ("2,750,000 ج.م" if _is_qa else ""))
    _p13_avm_high = (f"{_n(_avm_high)} ج.م" if _avm_high else ("3,350,000 ج.م" if _is_qa else ""))
    _p13_avm_conf = payload.get("avm_confidence_score", "") or ("متوسط" if _is_qa else "")
    for _lbl, _val in [
        ("القيمة الآلية AVM", _p13_avm_v),
        ("النطاق المنخفض",   _p13_avm_low),
        ("النطاق المرتفع",   _p13_avm_high),
        ("درجة الثقة",       _p13_avm_conf),
    ]:
        _kv(ws13, r13, _lbl, _val, 1, 2, 4); r13 += 1

    # ── F: Expert Editable Fields ─────────────────────────────────────────
    _sec_hdr(ws13, r13, 1, 4, "حقول الخبير القابلة للتعديل"); r13 += 1
    for _lbl, _val in [
        ("القيمة الموصى بها من الخبير", str(payload.get("expert_recommended_value", "") or "")),
        ("ملاحظات الخبير",               str(payload.get("expert_notes",            "") or "")),
        ("ملاحظات التوفيق",               str(payload.get("reconciliation_notes",    "") or "")),
        ("سبب القرار",                   str(payload.get("decision_reason",          "") or "")),
    ]:
        _kv(ws13, r13, _lbl, _val, 1, 2, 4, vbg=C_GOLD_BG); r13 += 1

    r13 += 1
    _disc13 = ws13.cell(r13, 1,
        "محاكاة داخلية للمراجعة الاحترافية — لا تُكشف للمستخدمين العاديين. "
        "جميع القيم محاكاة داخلية أو مدخلات من الطلب.")
    _disc13.font = Font(color="B43200", name="Arial", size=8, italic=True)
    ws13.merge_cells(f"A{r13}:D{r13}")

    # ════════════════════════════════════════════════════════════════════════
    # Sheet 14: قيمة الأرض
    # ════════════════════════════════════════════════════════════════════════
    ws14 = wb.create_sheet("قيمة الأرض")
    _rtl(ws14)
    _widths(ws14, [28, 18, 18, 18, 18, 22, 22, 20, 36])
    r14 = 1

    ws14.merge_cells("A1:I1")
    _c = ws14.cell(1, 1, "قيمة الأرض — مقارنة البيوع والاستخلاص والتوفيق")
    _c.font      = F_TITLE
    _c.fill      = _fill(C_BLUE_D)
    _c.alignment = AL_CTR
    ws14.row_dimensions[1].height = 24
    r14 += 1

    # A: مقارنة بيوع الأراضي
    _sec_hdr(ws14, r14, 1, 9, "أ. مقارنة بيوع الأراضي"); r14 += 1
    land_hdr = ["رقم المقارن", "الموقع", "المساحة م²", "تاريخ العرض",
                "السعر الإجمالي", "سعر المتر", "سعر المتر المعدل",
                "حالة الموقع الجغرافي", "سبب الاستبعاد"]  # Part B: geo columns
    for col, h in enumerate(land_hdr, 1):
        _c = ws14.cell(r14, col, h)
        _c.font = F_HDR; _c.fill = _fill(C_BLUE_M); _c.alignment = AL_CTR
    r14 += 1
    for lc in (wb_land_comps or []):
        geo_status = lc.get("geo_match_status", "")
        geo_reason = lc.get("geo_exclusion_reason", "")
        _geo_fill  = _fill("FFDDDD") if geo_status == "خارج النطاق" else _fill("DDFFDD") if geo_status == "مطابق" else None
        for col, v in enumerate([
            str(lc.get("num", "")), lc.get("location", ""),
            str(lc.get("area_m2", "")), lc.get("offer_date", ""),
            lc.get("total_price_disp", ""), lc.get("price_per_m2_disp", ""),
            lc.get("adj_price_per_m2", ""),
            geo_status, geo_reason,
        ], 1):
            _c = ws14.cell(r14, col, v); _c.font = F_VAL; _c.alignment = AL_RT
            if col in (8, 9) and _geo_fill:
                _c.fill = _geo_fill
        r14 += 1
    if wb_avg_land_price:
        _sec_hdr(ws14, r14, 1, 5, f"متوسط سعر المتر المعدل: {wb_avg_land_price}", C_BLUE_L, C_BLUE_D)
        r14 += 1
    if wb_land_value_sales:
        _kv(ws14, r14, "قيمة نصيب الأرض (مقارنة بيوع)", wb_land_value_sales, 1, 2, 9, vbg=C_GREEN); r14 += 1
    r14 += 1

    # B: طريقة الاستخلاص
    _sec_hdr(ws14, r14, 1, 9, "ب. طريقة الاستخلاص"); r14 += 1
    for lbl, val in [
        ("القيمة الكلية للعقار المحسَّن (مؤشر)",  wb_extr.get("extr_improved_indication", "")),
        ("تكلفة الإنشاء كجديد",                     wb_extr.get("extr_replacement_cost_new", "")),
        ("نسبة الإهلاك",                            wb_extr.get("extr_depreciation_pct", "")),
        ("قيمة الإهلاك",                            wb_extr.get("extr_depr_amount", "")),
        ("قيمة الإنشاء المستهلكة",                   wb_extr.get("extr_depr_imprv_value", "")),
        ("قيمة الأرض المستخلصة (إجمالي)",           wb_extr.get("extr_land_value", "")),
        ("سعر متر الأرض المستخلص",                  wb_extr.get("extr_land_per_m2", "")),
        ("نصيب الأرض المستخلص",                     wb_extr.get("extr_land_share_value", "")),
    ]:
        _kv(ws14, r14, lbl, val, 1, 2, 9); r14 += 1
    r14 += 1

    # C: توفيق قيمة الأرض
    _sec_hdr(ws14, r14, 1, 9, "ج. توفيق قيمة الأرض", C_GOLD, "7A5800"); r14 += 1
    for lbl, val in [
        ("قيمة الأرض — طريقة المقارنة",   wb_land_value_sales),
        ("قيمة الأرض — طريقة الاستخلاص",  wb_extr.get("extr_land_share_value", "")),
        ("متوسط/قيمة الأرض المُوفَّقة",   wb_land_value_recon),
        ("قيمة الأرض المختارة من الخبير", wb_land_value_recon),
    ]:
        _kv(ws14, r14, lbl, val, 1, 2, 9, vbg=C_GOLD_BG if val == wb_land_value_recon else C_WHITE); r14 += 1
    r14 += 1
    _disc = ws14.cell(r14, 1,
        "ملاحظة: قيمة الأرض محاكاة داخلية للمراجعة — لا تستند إلى مصادر سوق رسمية.")
    _disc.font = Font(color="B43200", name="Arial", size=8, italic=True)
    ws14.merge_cells(f"A{r14}:I{r14}")
    r14 += 2

    # D: نصيب العقار من الأرض (Part C — shared land value)
    _sec_hdr(ws14, r14, 1, 9, "د. نصيب العقار المُقيَّم من قيمة الأرض", C_BLUE_D, "FFFFFF"); r14 += 1
    _EF14 = "يحتاج استكمال بواسطة الخبير"
    for lbl, val in [
        ("إجمالي المساحات القابلة للبيع في المبنى",  mctx.get("total_building_sellable_area", _EF14)),
        ("نسبة نصيب العقار (Land Share Ratio)",        mctx.get("land_share_ratio", _EF14)),
        ("مساحة نصيب العقار من الأرض (م²)",           mctx.get("subject_land_share_area", _EF14)),
        ("قيمة نصيب العقار المُوفَّقة",               mctx.get("reconciled_subject_land_share_value", _EF14)),
        ("قيمة نصيب العقار — اختيار الخبير",          mctx.get("expert_selected_subject_land_value", _EF14)),
        ("أساس الاحتساب",                              mctx.get("shared_land_basis_notes", "")),
    ]:
        _kv(ws14, r14, lbl, val, 1, 2, 9,
            vbg=C_GOLD_BG if "نصيب" in lbl and "اختيار" in lbl else C_WHITE); r14 += 1
    r14 += 1

    # ════════════════════════════════════════════════════════════════════════
    # Sheet 15: خرائط وصور
    # ════════════════════════════════════════════════════════════════════════
    ws15 = wb.create_sheet("خرائط وصور")
    _rtl(ws15)
    _widths(ws15, [36, 54])
    r15 = 1

    ws15.merge_cells("A1:B1")
    _c = ws15.cell(1, 1, "خرائط وصور — موقع العقار والمقارنات")
    _c.font      = F_TITLE
    _c.fill      = _fill(C_BLUE_D)
    _c.alignment = AL_CTR
    ws15.row_dimensions[1].height = 24
    r15 += 1

    # ── Coordinate display (Part F) ───────────────────────────────────────
    _sec_hdr(ws15, r15, 1, 2, "الإحداثيات الجغرافية للعقار"); r15 += 1
    _coords_raw15 = str(payload.get("coordinates") or "")
    _lat15, _lon15 = None, None
    if _coords_raw15 and "," in _coords_raw15:
        try:
            _cp15  = _coords_raw15.split(",", 1)
            _lat15 = float(_cp15[0].strip())
            _lon15 = float(_cp15[1].strip())
        except (ValueError, TypeError):
            pass
    _kv(ws15, r15, "خط العرض (Latitude)",  f"{_lat15:.6f}°N" if _lat15 is not None else "غير محدد — يُدخل الخبير", 1, 2, 2, vbg=C_BLUE_L); r15 += 1
    _kv(ws15, r15, "خط الطول (Longitude)", f"{_lon15:.6f}°E" if _lon15 is not None else "غير محدد — يُدخل الخبير", 1, 2, 2, vbg=C_BLUE_L); r15 += 1
    _kv(ws15, r15, "مصدر الإحداثيات",     payload.get("coordinate_source") or ("مدخل يدوي" if (_lat15 is not None) else "غير مُدخل"), 1, 2, 2); r15 += 1
    _kv(ws15, r15, "الحي / المنطقة",       payload.get("district") or "—", 1, 2, 2); r15 += 1
    _kv(ws15, r15, "المدينة",              payload.get("city") or "—", 1, 2, 2); r15 += 1
    r15 += 1

    # ── Formal image-type table ────────────────────────────────────────────
    _sec_hdr(ws15, r15, 1, 2, "جدول أنواع الصور والخرائط المطلوبة"); r15 += 1
    for _col15, _hval15 in enumerate(["نوع الصورة / الخريطة", "متوفر؟ — ملاحظات الخبير"], 1):
        _hc15 = ws15.cell(row=r15, column=_col15, value=_hval15)
        _hc15.font      = F_HDR
        _hc15.fill      = _fill(C_BLUE_D)
        _hc15.alignment = AL_CTR
    r15 += 1
    _img_types = [
        ("خريطة موقع العقار",     "لم تُرفق — يُضيفها الخبير يدوياً"),
        ("صورة جوية للعقار",      "لم تُرفق — يُضيفها الخبير يدوياً"),
        ("خريطة توزيع المقارنات", "لم تُرفق — يُضيفها الخبير يدوياً"),
        ("صور المقارن 1",         "لم تُرفق — يُضاف بواسطة الخبير"),
        ("صور المقارن 2",         "لم تُرفق — يُضاف بواسطة الخبير"),
        ("صور المقارن 3",         "لم تُرفق — يُضاف بواسطة الخبير"),
        ("صور المقارن 4",         "لم تُرفق — يُضاف بواسطة الخبير"),
        ("صور الواجهة الأمامية",  "لم تُرفق — يُضاف بواسطة الخبير"),
        ("صور الداخل",            "لم تُرفق — يُضاف بواسطة الخبير"),
    ]
    for _itype, _inote in _img_types:
        _row(ws15, r15, _itype, _inote)
        r15 += 1
    r15 += 1

    _sec_hdr(ws15, r15, 1, 2, "ملاحظات الخبير حول الصور والخرائط"); r15 += 1
    ws15.merge_cells(f"A{r15}:B{r15 + 3}")
    _c = ws15.cell(r15, 1, "")
    _c.fill      = _fill(C_WHITE)
    _c.alignment = AL_TOP
    for row_i in range(r15, r15 + 4):
        ws15.row_dimensions[row_i].height = 22
    r15 += 4
    r15 += 1
    _disc = ws15.cell(r15, 1,
        "لا تتضمن هذه النسخة جلب خرائط أو صور جوية من الإنترنت أو Google Maps أو OSM أو Mapbox. "
        "يُضيف الخبير الصور والخرائط يدوياً. لا يتم الكشف عن مسارات ملفات داخلية للمستخدم العادي.")
    _disc.font = Font(color="B43200", name="Arial", size=8, italic=True)
    ws15.merge_cells(f"A{r15}:B{r15}")

    # ════════════════════════════════════════════════════════════════════════
    # Sheet 16: مصادر الأسعار — Price Source Spine
    # ════════════════════════════════════════════════════════════════════════
    ws16 = wb.create_sheet("مصادر الأسعار")
    _rtl(ws16)
    _widths(ws16, [20, 22, 26, 20, 20, 22, 18, 16, 16, 26, 32, 20, 36])

    ws16.merge_cells("A1:M1")
    ws16["A1"].value     = "مصادر الأسعار — Price Source Spine (سجل داخلي)"
    ws16["A1"].font      = F_TITLE
    ws16["A1"].fill      = _fill("2D5A27")
    ws16["A1"].alignment = AL_CTR
    ws16.row_dimensions[1].height = 22

    _src_headers = [
        "كود المصدر", "نوع المصدر", "المنطقة / Zone",
        "نوع الأصل", "السعر / م²", "القيمة",
        "تاريخ المصدر", "مستوى الثقة", "الحالة",
        "مستخدم في", "ملاحظات الخبير",
        "حالة الموقع الجغرافي", "سبب الاستبعاد",  # Part B: geo columns
    ]
    _src_keys = [
        "source_registry_id", "source_type", "district",
        "property_class", "price_per_m2", "source_value",
        "source_date", "source_confidence", "source_status",
        "used_in_methods", "source_notes",
        "geo_match_status", "geo_exclusion_reason",
    ]
    r16 = 2
    for ci, h in enumerate(_src_headers, 1):
        c = ws16.cell(r16, ci, value=h)
        c.font = F_HDR; c.fill = _fill(C_BLUE_D); c.alignment = AL_CTR
    r16 += 1
    if wb_price_sources:
        for src in wb_price_sources:
            _src_geo  = src.get("geo_match_status", "")
            _src_gfill = _fill("FFDDDD") if _src_geo == "خارج النطاق" else _fill("DDFFDD") if _src_geo == "مطابق" else None
            for ci, key in enumerate(_src_keys, 1):
                ws16.cell(r16, ci).value     = src.get(key, _dg)
                ws16.cell(r16, ci).alignment = AL_RT
                ws16.cell(r16, ci).font      = F_VAL
                if ci in (12, 13) and _src_gfill:
                    ws16.cell(r16, ci).fill = _src_gfill
            ws16.cell(r16, 9).fill = _fill("FFFBE6")  # status column highlight
            r16 += 1
    else:
        ws16.cell(r16, 1).value = "لا توجد مصادر أسعار مرتبطة بهذا الطلب — يحتاج استكمال بواسطة الخبير"
        ws16.cell(r16, 1).font  = Font(color="B43200", name="Arial", size=9)
        ws16.merge_cells(f"A{r16}:M{r16}"); r16 += 1
    ws16.row_dimensions[r16].height = 6; r16 += 1
    _src_disc = ws16.cell(r16, 1,
        "جميع المصادر المدرجة في هذا السجل محاكاة داخلية لأغراض QA. "
        "لا يتضمن هذا السجل استرجاعاً من Source Registry/Qdrant في المرحلة الحالية. "
        "سيتم الربط الفعلي عند تفعيل مكون Source Registry.")
    _src_disc.font = Font(color="B43200", name="Arial", size=8, italic=True)
    ws16.merge_cells(f"A{r16}:M{r16}")

    # ════════════════════════════════════════════════════════════════════════
    # Sheet 17: ربط التقييم الجماعي — Mass Appraisal Bridge
    # ════════════════════════════════════════════════════════════════════════
    ws17 = wb.create_sheet("ربط التقييم الجماعي")
    _rtl(ws17)
    _widths(ws17, [38, 52])

    ws17.merge_cells("A1:B1")
    ws17["A1"].value     = "ربط التقييم الجماعي — Mass Appraisal Bridge (سجل داخلي)"
    ws17["A1"].font      = F_TITLE
    ws17["A1"].fill      = _fill("1F4E78")
    ws17["A1"].alignment = AL_CTR
    ws17.row_dimensions[1].height = 22

    r17 = 2
    _mass_fields = [
        ("معرف تشغيل التقييم الجماعي (mass_run_id)",   "mass_run_id"),
        ("معرف المنطقة (zone_id)",                       "mass_zone_id"),
        ("متوسط سعر المتر في المنطقة",                   "mass_average_price_per_m2"),
        ("نموذج القيمة الجماعية (model_value)",          "mass_model_value"),
        ("نطاق الثقة",                                   "mass_confidence_range"),
        ("درجة جودة البيانات",                           "mass_data_quality_score"),
        ("تغطية مصادر البيانات",                         "mass_source_coverage"),
        ("حالة التقييم الجماعي",                         "mass_appraisal_status"),
        ("مرتبط بطرق التقرير",                           "linked_to_report_methods"),
    ]
    for lbl, key in _mass_fields:
        val = wb_mass_bridge.get(key, _dg)
        _kv(ws17, r17, lbl, val, 1, 2, 2,
            vbg="D4AF37" if key in ("mass_model_value", "mass_average_price_per_m2") and val != _dg
            else "FFFFFF"); r17 += 1
    ws17.row_dimensions[r17].height = 6; r17 += 1

    # Source linkage disclosure
    _mass_disc = ws17.cell(r17, 1,
        "هذا السجل يمثل الجسر بين تقرير التقييم الفردي ومكون التقييم الجماعي / Smart Core. "
        "في المرحلة الحالية البيانات محاكاة QA. سيتم الربط الفعلي عند تفعيل mass appraisal engine. "
        "لا يتضمن هذا التحليل استرجاعاً من الإنترنت أو Qdrant أو أي مصدر بيانات خارجي.")
    _mass_disc.font = Font(color="B43200", name="Arial", size=8, italic=True)
    ws17.merge_cells(f"A{r17}:B{r17}")
    ws17.row_dimensions[r17].height = 24; r17 += 1

    # Source rows used in each method
    r17 += 1
    _sec_hdr(ws17, r17, 1, 2, "مصادر الأسعار المرتبطة بكل طريقة تقييم"); r17 += 1
    for ci, h in enumerate(["الطريقة", "المصادر المرتبطة"], 1):
        c = ws17.cell(r17, ci, value=h)
        c.font = F_HDR; c.fill = _fill(C_BLUE_D); c.alignment = AL_CTR
    r17 += 1
    _method_source_map = {
        "AVM": [], "مقارنة البيوع": [], "قيمة الأرض": [],
        "طريقة الدخل": [], "DCF": [], "طريقة التكلفة": [], "توفيق النتائج": [],
    }
    for src in wb_price_sources:
        for method in _method_source_map:
            if method in src.get("used_in_methods", ""):
                _method_source_map[method].append(src.get("source_registry_id", ""))
    for method_name, src_ids in _method_source_map.items():
        ws17.cell(r17, 1).value     = method_name
        ws17.cell(r17, 2).value     = "، ".join(src_ids) if src_ids else _dg
        ws17.cell(r17, 1).alignment = AL_RT
        ws17.cell(r17, 2).alignment = AL_RT
        r17 += 1

    # ════════════════════════════════════════════════════════════════════════
    # Sheet 19: القيمة الإيجارية — Rental Value Summary
    # ════════════════════════════════════════════════════════════════════════
    ws19 = wb.create_sheet("القيمة الإيجارية")
    _rtl(ws19)
    _widths(ws19, [42, 30, 50])

    ws19.merge_cells("A1:C1")
    ws19["A1"].value     = "القيمة الإيجارية — ملخص نتائج تقييم الإيجار"
    ws19["A1"].font      = F_TITLE
    ws19["A1"].fill      = _fill("1F4E78")
    ws19["A1"].alignment = AL_CTR
    ws19.row_dimensions[1].height = 22

    _r19 = 2
    if wb_is_rental or wb_rental_comps:
        _sec_hdr(ws19, _r19, 1, 3, "نموذج A — ملخص القيمة الإيجارية (بيانات محاكاة QA)"); _r19 += 1
        _rv = wb_rental_ctx
        for _lbl, _key in [
            ("متوسط إيجار المتر المعدل (ج.م/م²/شهر)", "avg_adj_rent_per_m2_monthly"),
            ("وسيط إيجار المتر المعدل (ج.م/م²/شهر)",  "median_adj_rent_per_m2_monthly"),
            ("المساحة (م²)",                             ""),
            ("الإيجار الشهري المشتق من المقارنات",      "indicated_monthly_rent"),
            ("الإيجار السنوي المشتق",                   "indicated_annual_rent"),
            ("نسبة الشواغر وفقدان التحصيل",             "vacancy_rate"),
            ("مبلغ الشواغر",                            "vacancy_amount"),
            ("مبلغ فقدان التحصيل",                      "collection_loss_amount"),
            ("صافي الدخل الإيجاري السنوي",               "net_rental_income"),
            ("العائد الإيجاري الضمني",                   "implied_yield"),
            ("الإيجار الشهري النهائي المختار",           "final_monthly_rental_value"),
            ("الإيجار السنوي النهائي المختار",           "final_annual_rental_value"),
            ("نطاق التقدير المنخفض",                    "rental_value_low_range"),
            ("نطاق التقدير المرتفع",                    "rental_value_high_range"),
            ("ملاحظات الخبير",                          "rental_value_notes"),
        ]:
            _val = (
                f"{float(payload.get('area') or 120):g} م²"
                if _key == "" else
                _rv.get(_key, _dg)
            )
            _kv(ws19, _r19, _lbl, _dg_val(_val), 1, 2, 3,
                vbg="D4AF37" if "نهائي" in _lbl else "FFFFFF"); _r19 += 1

        ws19.row_dimensions[_r19].height = 6; _r19 += 1

        # نموذج B — Excel formula section (formula cells reference row above)
        _sec_hdr(ws19, _r19, 1, 3, "نموذج B — معادلات إكسل للتحقق"); _r19 += 1
        # Find the row where final_monthly was written (it's _r19 - 6 from end of form A)
        # Write a static formula-check note instead for robustness
        _kv(ws19, _r19, "تحقق: الإيجار السنوي = الشهري × 12", _na, 1, 2, 3,
            vbg="EBF3FB"); _r19 += 1
        ws19.cell(_r19, 2).value = f"={_rv.get('final_monthly_rental_value', '0').replace(',','').replace(' ج.م','').strip() or '0'}*12"
        ws19.cell(_r19, 2).alignment = AL_RT; _r19 += 1

        ws19.row_dimensions[_r19].height = 6; _r19 += 1
        _sec_hdr(ws19, _r19, 1, 3, "نموذج C — توفيق القيمة الإيجارية المختصر"); _r19 += 1
        for _lbl2, _val2 in [
            ("إشارة طريقة المقارنة الإيجارية",         _rv.get("indicated_monthly_rent", _dg)),
            ("نطاق السوق الإيجاري",                     f"{_rv.get('rental_value_low_range', _dg)} — {_rv.get('rental_value_high_range', _dg)}"),
            ("القيمة الإيجارية الشهرية النهائية المختارة", _rv.get("final_monthly_rental_value", _ef)),
            ("القيمة الإيجارية السنوية النهائية المختارة",  _rv.get("final_annual_rental_value", _ef)),
            ("أساس تاريخ التقييم",                       wb_date_basis.get("date_basis_label_ar", _dg)),
            ("ملاحظة أساس التاريخ",                     wb_date_basis.get("date_basis_notes", _dg)),
        ]:
            _kv(ws19, _r19, _lbl2, _dg_val(_val2), 1, 2, 3,
                vbg="D4AF37" if "نهائية" in _lbl2 else "FFFFFF"); _r19 += 1

        if _rv.get("rental_disclaimer"):
            ws19.merge_cells(f"A{_r19}:C{_r19}")
            _dc = ws19.cell(_r19, 1, _rv["rental_disclaimer"])
            _dc.font = Font(color="B43200", name="Arial", size=8, italic=True)
            _dc.alignment = AL_RT; _r19 += 1
    else:
        _sec_hdr(ws19, _r19, 1, 3, _na); _r19 += 1
        for _np_lbl in ["متوسط إيجار المتر", "الإيجار الشهري", "الإيجار السنوي",
                         "القيمة الإيجارية النهائية", "ملاحظات الخبير"]:
            _kv(ws19, _r19, _np_lbl, _na, 1, 2, 3, vbg="F5F5F5"); _r19 += 1
        ws19.cell(_r19, 1).value = "الغرض الحالي لهذا الطلب ليس تقييم إيجاري."
        ws19.cell(_r19, 1).alignment = AL_RT; _r19 += 1

    # ════════════════════════════════════════════════════════════════════════
    # Sheet 20: مقارنات إيجارية — Rental Comparison Matrix (with Excel formulas)
    # ════════════════════════════════════════════════════════════════════════
    ws20 = wb.create_sheet("مقارنات إيجارية")
    _rtl(ws20)
    _widths(ws20, [14, 26, 14, 14, 16, 16, 16, 12, 12, 12, 12, 12, 14, 16, 16, 14, 28, 20, 36])

    ws20.merge_cells("A1:S1")
    ws20["A1"].value     = "مصفوفة المقارنات الإيجارية — مع معادلات إكسل (بيانات محاكاة QA)"
    ws20["A1"].font      = F_TITLE
    ws20["A1"].fill      = _fill("1F4E78")
    ws20["A1"].alignment = AL_CTR
    ws20.row_dimensions[1].height = 22

    # Row 2: subject area reference cell (used in formulas =N4*$B$2 etc.)
    ws20.merge_cells("A2:B2")
    ws20["A2"].value     = "مساحة العقار محل التقييم (م²) — مرجع المعادلات"
    ws20["A2"].font      = F_LBL
    ws20["A2"].fill      = _fill("EBF3FB")
    ws20["A2"].alignment = AL_RT
    _subj_area_val = float(payload.get("area") or 120)
    ws20["C2"].value     = _subj_area_val        # numeric — referenced by formulas
    ws20["C2"].font      = Font(bold=True, color="1F4E78", name="Arial", size=10)
    ws20["C2"].alignment = AL_CTR

    # Row 3: Column headers
    _rent_hdrs = [
        "رقم المقارن", "الموقع", "نوع العقار", "المساحة (م²)",
        "الإيجار الشهري", "الإيجار السنوي (=E×12)", "إيجار م²/شهر (=E/D)",
        "معامل الموقع", "معامل المساحة", "معامل الحالة",
        "معامل التشطيب", "معامل التاريخ",
        "إجمالي المعاملات (=H×…×L)", "إيجار م² معدل (=G×M)",
        "إيجار العقار المعدل (=N×$C$2)", "حالة المقارن", "ملاحظات الخبير",
        "حالة الموقع الجغرافي", "سبب الاستبعاد",  # Part B: geo columns
    ]
    for _ci, _h in enumerate(_rent_hdrs, 1):
        _hc = ws20.cell(3, _ci, value=_h)
        _hc.font = F_HDR; _hc.fill = _fill(C_BLUE_D); _hc.alignment = AL_CTR
    ws20.freeze_panes = ws20["A4"]

    # Rows 4-7: 4 comparables with formula cells
    _data_row_start = 4
    if wb_rental_comps:
        for _ri, _rc in enumerate(wb_rental_comps[:4], _data_row_start):
            _row_n = _ri
            _geo_stat  = _rc.get("geo_match_status", "")
            _geo_rsn   = _rc.get("geo_exclusion_reason", "")
            _geo_fill20 = _fill("FFDDDD") if _geo_stat == "خارج النطاق" else _fill("DDFFDD") if _geo_stat == "مطابق" else None
            # Raw numeric values in data columns
            ws20.cell(_row_n, 1).value  = _rc.get("num", _ri - _data_row_start + 1)
            ws20.cell(_row_n, 2).value  = str(_rc.get("location", ""))
            ws20.cell(_row_n, 3).value  = str(_rc.get("property_type", "شقة سكنية"))
            ws20.cell(_row_n, 4).value  = float(_rc.get("area", 0))          # D
            ws20.cell(_row_n, 5).value  = float(_rc.get("monthly_rent", 0))  # E
            ws20.cell(_row_n, 6).value  = f"=E{_row_n}*12"                   # F annual
            ws20.cell(_row_n, 7).value  = f"=E{_row_n}/D{_row_n}"            # G rent/m²
            ws20.cell(_row_n, 8).value  = float(_rc.get("location_factor", 1))   # H
            ws20.cell(_row_n, 9).value  = float(_rc.get("area_factor", 1))       # I
            ws20.cell(_row_n, 10).value = float(_rc.get("condition_factor", 1))  # J
            ws20.cell(_row_n, 11).value = float(_rc.get("finishing_factor", 1))  # K
            ws20.cell(_row_n, 12).value = float(_rc.get("time_factor", 1))       # L
            ws20.cell(_row_n, 13).value = f"=H{_row_n}*I{_row_n}*J{_row_n}*K{_row_n}*L{_row_n}"  # M total_adj
            ws20.cell(_row_n, 14).value = f"=G{_row_n}*M{_row_n}"               # N adj rent/m²
            ws20.cell(_row_n, 15).value = f"=N{_row_n}*$C$2"                    # O adj monthly
            ws20.cell(_row_n, 16).value = str(_rc.get("status", ""))
            ws20.cell(_row_n, 17).value = str(_rc.get("notes", ""))
            ws20.cell(_row_n, 18).value = _geo_stat    # R geo_match_status
            ws20.cell(_row_n, 19).value = _geo_rsn     # S geo_exclusion_reason
            for _ci2 in range(1, 20):
                ws20.cell(_row_n, _ci2).alignment = AL_RT
                if _ci2 in (18, 19) and _geo_fill20:
                    ws20.cell(_row_n, _ci2).fill = _geo_fill20
    else:
        # Non-QA: write data-gap rows
        for _ri in range(_data_row_start, _data_row_start + 4):
            for _ci2 in range(1, 20):
                ws20.cell(_ri, _ci2).value     = _na if _ci2 == 2 else (_dg if _ci2 <= 12 else _ef)
                ws20.cell(_ri, _ci2).alignment = AL_RT

    # Row 8: Summary / average formulas
    _sumrow = _data_row_start + 4
    ws20.cell(_sumrow, 2).value = "متوسط / ملخص"
    ws20.cell(_sumrow, 2).font  = F_LBL
    ws20.cell(_sumrow, 7).value  = f"=AVERAGE(G{_data_row_start}:G{_sumrow-1})"   # avg rent/m²
    ws20.cell(_sumrow, 13).value = f"=AVERAGE(M{_data_row_start}:M{_sumrow-1})"  # avg total_adj
    ws20.cell(_sumrow, 14).value = f"=AVERAGE(N{_data_row_start}:N{_sumrow-1})"  # avg adj rent/m²
    ws20.cell(_sumrow, 15).value = f"=AVERAGE(O{_data_row_start}:O{_sumrow-1})"  # avg adj monthly
    ws20.cell(_sumrow, 2).fill  = _fill("D4AF37")
    for _ci2 in [7, 13, 14, 15]:
        ws20.cell(_sumrow, _ci2).fill      = _fill("D4AF37")
        ws20.cell(_sumrow, _ci2).font      = F_GOLD
        ws20.cell(_sumrow, _ci2).alignment = AL_CTR

    # Row 9: Expert selected
    _exprow = _sumrow + 1
    ws20.cell(_exprow, 2).value  = "الإيجار الشهري النهائي المختار"
    ws20.cell(_exprow, 2).font   = F_LBL
    ws20.cell(_exprow, 15).value = (
        str(wb_rental_ctx.get("final_monthly_rental_value", _ef)).replace(" ج.م", "").replace(",", "").strip()
        if wb_rental_ctx.get("final_monthly_rental_value") else _ef
    )
    ws20.cell(_exprow, 15).fill      = _fill("D4AF37")
    ws20.cell(_exprow, 15).font      = F_GOLD
    ws20.cell(_exprow, 15).alignment = AL_CTR

    if not wb_rental_comps and not wb_is_rental:
        _sec_hdr(ws20, _exprow + 2, 1, 17, _na)

    # ════════════════════════════════════════════════════════════════════════
    # Sheet 21: توفيق القيمة الإيجارية — Rental Value Reconciliation
    # ════════════════════════════════════════════════════════════════════════
    ws21 = wb.create_sheet("توفيق القيمة الإيجارية")
    _rtl(ws21)
    _widths(ws21, [42, 36, 50])

    ws21.merge_cells("A1:C1")
    ws21["A1"].value     = "توفيق القيمة الإيجارية — الخلاصة النهائية"
    ws21["A1"].font      = F_TITLE
    ws21["A1"].fill      = _fill("1F4E78")
    ws21["A1"].alignment = AL_CTR
    ws21.row_dimensions[1].height = 22

    _r21 = 2
    if wb_is_rental or wb_rental_comps:
        _rv21 = wb_rental_ctx
        _sec_hdr(ws21, _r21, 1, 3, "نموذج A — توفيق القيمة الإيجارية"); _r21 += 1
        for _lbl21, _val21 in [
            ("إشارة طريقة المقارنة الإيجارية",         _rv21.get("indicated_monthly_rent",     _dg)),
            ("متوسط إيجار المتر المعدل (ج.م/م²/شهر)", _rv21.get("avg_adj_rent_per_m2_monthly",_dg)),
            ("نطاق السوق الإيجاري",                     f"{_rv21.get('rental_value_low_range',_dg)} — {_rv21.get('rental_value_high_range',_dg)}"),
            ("القيمة الإيجارية الشهرية النهائية",       _rv21.get("final_monthly_rental_value", _ef)),
            ("القيمة الإيجارية السنوية النهائية",        _rv21.get("final_annual_rental_value",  _ef)),
            ("الإيجار السنوي (معادلة =شهري×12)",        _ef),
            ("أساس تاريخ التقييم",                       wb_date_basis.get("date_basis_label_ar", _dg)),
            ("ملاحظة أثر تاريخ التقييم",                wb_date_basis.get("date_basis_notes",    _dg)),
            ("الخلاصة النهائية",                        _rv21.get("rental_value_notes",          _ef)),
        ]:
            _kv(ws21, _r21, _lbl21, _dg_val(_val21), 1, 2, 3,
                vbg="D4AF37" if ("نهائية" in _lbl21 or "الخلاصة" in _lbl21) else "FFFFFF"); _r21 += 1

        # Excel formula for annual from monthly (cell B row for "السنوي (معادلة)")
        _annual_formula_row = _r21 - 4   # the "الإيجار السنوي (معادلة)" row
        _monthly_val_str = (
            str(_rv21.get("final_monthly_rental_value", "0"))
            .replace(",", "").replace(" ج.م", "").strip()
        )
        try:
            _monthly_num = float(_monthly_val_str)
        except (ValueError, TypeError):
            _monthly_num = 0
        ws21.cell(_annual_formula_row, 2).value     = f"={_monthly_num}*12" if _monthly_num else _ef
        ws21.cell(_annual_formula_row, 2).alignment = AL_RT

        ws21.row_dimensions[_r21].height = 6; _r21 += 1
        if _rv21.get("rental_disclaimer"):
            ws21.merge_cells(f"A{_r21}:C{_r21}")
            _dsc = ws21.cell(_r21, 1, _rv21["rental_disclaimer"])
            _dsc.font = Font(color="B43200", name="Arial", size=8, italic=True)
            _dsc.alignment = AL_RT; _r21 += 1
    else:
        _sec_hdr(ws21, _r21, 1, 3, _na); _r21 += 1
        for _np_lbl21 in ["إشارة المقارنة الإيجارية", "القيمة الإيجارية النهائية",
                           "الخلاصة", "أساس التاريخ", "ملاحظات الخبير"]:
            _kv(ws21, _r21, _np_lbl21, _na, 1, 2, 3, vbg="F5F5F5"); _r21 += 1
        ws21.cell(_r21, 1).value = "الغرض الحالي لهذا الطلب ليس تقييم إيجاري."
        ws21.cell(_r21, 1).alignment = AL_RT

    # ════════════════════════════════════════════════════════════════════════
    # Sheet 22: سيناريوهات What-If — Sensitivity Analysis
    # ════════════════════════════════════════════════════════════════════════
    ws_wi = wb.create_sheet("سيناريوهات What-If")
    _rtl(ws_wi)
    _widths(ws_wi, [34, 22, 22, 22, 22, 22, 22, 22, 22, 36])

    ws_wi.merge_cells("A1:J1")
    ws_wi["A1"].value     = "سيناريوهات What-If — تحليل الحساسية وتأثير المتغيرات على القيمة"
    ws_wi["A1"].font      = F_TITLE
    ws_wi["A1"].fill      = _fill("2D5A27")
    ws_wi["A1"].alignment = AL_CTR
    ws_wi.row_dimensions[1].height = 26

    _wi_hdrs = ["السيناريو", "القيمة الأساسية", "المتغير المُعدَّل",
                "القيمة القديمة", "القيمة الجديدة", "تكلفة التغيير",
                "أثر القيمة", "صافي الأثر", "العائد ROI", "ملاحظات الخبير"]
    _r_wi = 2
    for _ci_wi, _h_wi in enumerate(_wi_hdrs, 1):
        _c_wi = ws_wi.cell(_r_wi, _ci_wi, _h_wi)
        _c_wi.font = F_HDR; _c_wi.fill = _fill(C_BLUE_D); _c_wi.alignment = AL_CTR
    _r_wi += 1

    _wi_is_qa = bool(payload.get("_qa_simulation"))
    # Part G: Write a reference cell pulling the final reconciliation value dynamically
    _wi_ref_row = _r_wi
    ws_wi.cell(_wi_ref_row, 1).value = "مرجع: القيمة المرجحة من توفيق النتائج"
    ws_wi.cell(_wi_ref_row, 1).font  = Font(name="Arial", size=9, italic=True, color="555555")
    ws_wi.cell(_wi_ref_row, 1).alignment = AL_RT
    ws_wi.cell(_wi_ref_row, 2).value = f"='توفيق النتائج'!D{_rec9_total_row}"
    ws_wi.cell(_wi_ref_row, 2).font  = F_GOLD
    ws_wi.cell(_wi_ref_row, 2).fill  = _fill(C_GOLD_BG)
    ws_wi.cell(_wi_ref_row, 2).alignment = AL_RT
    _r_wi += 1

    _wi_base  = float(str(payload.get("estimated_value") or 0)) if payload.get("estimated_value") else 0
    # For rental payloads, derive implied capital value from monthly rent / cap rate
    if not _wi_base and _wi_is_qa:
        try:
            _wi_mr = float(payload.get("income_monthly_rent") or payload.get("final_monthly_rental_value") or 0)
            _wi_cr = float(payload.get("income_cap_rate") or 3.8) / 100
            _wi_base = round(_wi_mr * 12 / _wi_cr) if (_wi_mr and _wi_cr) else 1_000_000
        except (ValueError, TypeError):
            _wi_base = 1_000_000
    _wi_scenarios = []
    # Each scenario: (name, var_name, old_v, new_v, fixed_cost, impact_pct, note)
    # impact_pct: fraction of base value; negative = value reduction
    if _wi_is_qa:
        _wi_scenarios = [
            ("ترقية التشطيب: عادي → فاخر",      "مستوى التشطيب", "عادي",  "فاخر",  80_000,    0.08,  "تقدير أثر الترقية"),
            ("تحسين الحالة: متوسط → جيد",        "حالة العقار",   "متوسط", "جيد",   50_000,    0.05,  "تحسن الحالة"),
            ("تغيير الاستخدام: سكني → تجاري",    "الاستخدام",    "سكني",  "تجاري", 120_000,   0.15,  "يخضع لموافقة جهوية"),
            ("رفع معدل نمو الإيجار: 3% → 5%",    "نمو الإيجار%", "3.0",   "5.0",   0,         0.06,  "سيناريو متفائل"),
            ("تغيير معدل الرسملة: 3.8% → 4.5%",  "معدل رسملة%",  "3.8",   "4.5",   0,         -0.09, "زيادة المخاطر"),
            ("تغيير معدل الخصم: 14% → 16%",      "معدل خصم%",   "14.0",  "16.0",  0,         -0.07, "بيئة سعر فائدة أعلى"),
            ("رفع نسبة الشواغر: 5% → 10%",       "نسبة شواغر%", "5.0",   "10.0",  0,         -0.04, "تراجع الطلب"),
        ]
    else:
        _wi_scenarios = [(f"سيناريو {_i}", _ef, _ef, _ef, None, None, _ef) for _i in range(1, 8)]

    for _sc_wi in _wi_scenarios:
        _sc_name, _var_n, _old_v, _new_v, _cost_c, _imp_pct, _note = _sc_wi
        ws_wi.cell(_r_wi, 1).value = _sc_name; ws_wi.cell(_r_wi, 1).alignment = AL_RT
        # Part G: base value references the reconciliation reference row dynamically
        ws_wi.cell(_r_wi, 2).value = f"=B{_wi_ref_row}"
        ws_wi.cell(_r_wi, 2).alignment = AL_RT
        ws_wi.cell(_r_wi, 3).value = _var_n; ws_wi.cell(_r_wi, 3).alignment = AL_RT
        ws_wi.cell(_r_wi, 4).value = _old_v; ws_wi.cell(_r_wi, 4).alignment = AL_RT
        ws_wi.cell(_r_wi, 5).value = _new_v; ws_wi.cell(_r_wi, 5).alignment = AL_RT
        # cost of change
        ws_wi.cell(_r_wi, 6).value = (f"{int(_cost_c):,} ج.م" if isinstance(_cost_c, int) else _cost_c)
        ws_wi.cell(_r_wi, 6).alignment = AL_RT
        # Part G: value impact references base dynamically
        if _imp_pct is not None and isinstance(_cost_c, int):
            ws_wi.cell(_r_wi, 7).value = f"=B{_wi_ref_row}*{_imp_pct}"
            ws_wi.cell(_r_wi, 8).value = f"=G{_r_wi}-F{_r_wi}"
            ws_wi.cell(_r_wi, 9).value = f"=IF(F{_r_wi}=0,\"N/A\",H{_r_wi}/F{_r_wi})"
        else:
            ws_wi.cell(_r_wi, 7).value = _ef
            ws_wi.cell(_r_wi, 8).value = _ef
            ws_wi.cell(_r_wi, 9).value = _ef
        for _col_wi in [7, 8, 9]:
            ws_wi.cell(_r_wi, _col_wi).alignment = AL_RT
        ws_wi.cell(_r_wi, 10).value = _note; ws_wi.cell(_r_wi, 10).alignment = AL_RT
        _r_wi += 1

    ws_wi.row_dimensions[_r_wi].height = 6; _r_wi += 1
    _wi_disc = ws_wi.cell(_r_wi, 1,
        "هذا التحليل استرشادي يعتمد على افتراضات QA داخلية فقط. لا يمثل توصية استثمارية نهائية. "
        "يلزم الخبير مراجعة كل سيناريو بشكل مستقل وإدخال قيم فعلية قبل الاعتماد.")
    _wi_disc.font = Font(color="B43200", name="Arial", size=8, italic=True)
    ws_wi.merge_cells(f"A{_r_wi}:J{_r_wi}")
    ws_wi.freeze_panes = ws_wi["A3"]

    # ════════════════════════════════════════════════════════════════════════
    # Sheet 23: شراء أم إيجار — Buy vs Rent Decision Matrix
    # ════════════════════════════════════════════════════════════════════════
    ws_bvr = wb.create_sheet("شراء أم إيجار")
    _rtl(ws_bvr)
    _widths(ws_bvr, [46, 40, 20])

    ws_bvr.merge_cells("A1:C1")
    ws_bvr["A1"].value     = "تحليل الشراء مقابل الإيجار — Buy vs Rent Decision Matrix"
    ws_bvr["A1"].font      = F_TITLE
    ws_bvr["A1"].fill      = _fill("1F4E78")
    ws_bvr["A1"].alignment = AL_CTR
    ws_bvr.row_dimensions[1].height = 26

    _r_bvr = 2
    _bvr_mv  = float(str(payload.get("estimated_value") or 0)) if payload.get("estimated_value") else 0
    _bvr_mr  = float(str(payload.get("income_monthly_rent") or (10_000 if _wi_is_qa else 0)))
    _bvr_ar  = _bvr_mr * 12
    _bvr_yrs = 5
    _bvr_rg  = 3.0    # rent growth %
    _bvr_alt = 12.0   # alternative return %
    _bvr_tc  = 3.0    # transaction cost %
    _bvr_mc  = 1.0    # maintenance %
    _bvr_cap = 5.0    # capital appreciation %

    _sec_hdr(ws_bvr, _r_bvr, 1, 3, "أ. مدخلات التحليل"); _r_bvr += 1
    # Part G: market value row references reconciliation sheet dynamically
    _bvr_mv_row = _r_bvr
    _kv(ws_bvr, _r_bvr, "القيمة السوقية للعقار",
        f"='توفيق النتائج'!D{_rec9_total_row}", 1, 2, 2)
    ws_bvr.cell(_r_bvr, 2).fill = _fill(C_GOLD_BG); ws_bvr.cell(_r_bvr, 2).font = F_GOLD
    ws_bvr.cell(_r_bvr, 3).value = "ج.م"; _r_bvr += 1
    _bvr_mr_row = _r_bvr
    _kv(ws_bvr, _r_bvr, "الإيجار الشهري السوقي", f"={_bvr_mr}" if _bvr_mr else _ef, 1, 2, 2)
    ws_bvr.cell(_r_bvr, 3).value = "ج.م/شهر"; _r_bvr += 1
    _bvr_ar_row = _r_bvr
    _kv(ws_bvr, _r_bvr, "الإيجار السنوي (=شهري × 12)", f"=B{_bvr_mr_row}*12", 1, 2, 2)
    ws_bvr.cell(_r_bvr, 3).value = "ج.م/سنة"; _r_bvr += 1
    for _lbl_bvr, _v_bvr, _u_bvr in [
        ("فترة الاحتفاظ المفترضة",                   str(_bvr_yrs), "سنة"),
        ("معدل نمو الإيجار السنوي",                  str(_bvr_rg), "%"),
        ("العائد البديل على رأس المال",               str(_bvr_alt), "%"),
        ("تكاليف الشراء والتسجيل",                   str(_bvr_tc), "% من القيمة"),
        ("تكاليف الصيانة والامتلاك السنوية",         str(_bvr_mc), "% من القيمة"),
        ("معدل التقدير الرأسمالي السنوي المتوقع",    str(_bvr_cap), "%"),
    ]:
        _kv(ws_bvr, _r_bvr, _lbl_bvr, _v_bvr, 1, 2, 2); ws_bvr.cell(_r_bvr, 3).value = _u_bvr; _r_bvr += 1

    ws_bvr.row_dimensions[_r_bvr].height = 6; _r_bvr += 1
    _sec_hdr(ws_bvr, _r_bvr, 1, 3, "ب. مؤشرات القرار"); _r_bvr += 1

    # price-to-rent ratio — Part G: use cell references instead of hardcoded values
    _ptr_row = _r_bvr
    _ptr_val = f"=B{_bvr_mv_row}/B{_bvr_ar_row}"
    _kv(ws_bvr, _r_bvr, "نسبة السعر إلى الإيجار (Price-to-Rent Ratio)", _ptr_val, 1, 2, 2)
    ws_bvr.cell(_r_bvr, 3).value = "أقل من 15: شراء مُفضَّل / 16–20: محايد / أكثر من 21: إيجار مُفضَّل"; _r_bvr += 1

    # total rent paid
    _rent_total_formula = f"=B{_bvr_ar_row}*{_bvr_yrs}"
    _kv(ws_bvr, _r_bvr, "إجمالي الإيجار المدفوع خلال فترة الاحتفاظ", _rent_total_formula, 1, 2, 2)
    ws_bvr.cell(_r_bvr, 3).value = "ج.م"; _r_bvr += 1

    # ownership cost — Part G: references market value cell
    _own_cost_formula = f"=B{_bvr_mv_row}*{_bvr_mc/100}*{_bvr_yrs}"
    _kv(ws_bvr, _r_bvr, "تكلفة الامتلاك الكلية (صيانة × فترة)", _own_cost_formula, 1, 2, 2)
    ws_bvr.cell(_r_bvr, 3).value = "ج.م"; _r_bvr += 1

    # projected resale value — Part G: references market value cell
    _resale_formula = f"=B{_bvr_mv_row}*(1+{_bvr_cap/100})^{_bvr_yrs}"
    _kv(ws_bvr, _r_bvr, "القيمة التقديرية عند البيع بعد فترة الاحتفاظ", _resale_formula, 1, 2, 2)
    ws_bvr.cell(_r_bvr, 3).value = "ج.م (تقدير)"; _r_bvr += 1

    # decision flag — Python-level computed from _bvr_mv/_bvr_ar for label only
    _ptr_num = round(_bvr_mv / _bvr_ar, 1) if (_bvr_mv and _bvr_ar) else None
    if _ptr_num is not None:
        if _ptr_num < 15:
            _decision_flag = f"الشراء مُفضَّل — نسبة السعر/الإيجار: {_ptr_num:.1f} (أقل من 15)"
        elif _ptr_num <= 20:
            _decision_flag = f"محايد / يعتمد على التمويل — نسبة: {_ptr_num:.1f}"
        else:
            _decision_flag = f"الإيجار قد يكون أفضل مالياً — نسبة: {_ptr_num:.1f} (أكثر من 21)"
    else:
        _decision_flag = _ef

    ws_bvr.row_dimensions[_r_bvr].height = 6; _r_bvr += 1
    _sec_hdr(ws_bvr, _r_bvr, 1, 3, "ج. نتيجة التحليل وتوصية استرشادية", bg="D4AF37", fg="000000"); _r_bvr += 1
    _kv(ws_bvr, _r_bvr, "مؤشر القرار", _decision_flag, 1, 2, 3, vbg=C_GOLD_BG); _r_bvr += 1

    ws_bvr.row_dimensions[_r_bvr].height = 6; _r_bvr += 1
    _bvr_disc = ws_bvr.cell(_r_bvr, 1,
        "هذا التحليل استرشادي ولا يعد نصيحة استثمارية نهائية. "
        "يعتمد على مدخلات مبدئية ويجب مراجعته من قِبل خبير متخصص "
        "مع مراعاة ظروف التمويل والوضع الضريبي للعميل.")
    _bvr_disc.font = Font(color="B43200", name="Arial", size=8, italic=True)
    ws_bvr.merge_cells(f"A{_r_bvr}:C{_r_bvr}")

    # ════════════════════════════════════════════════════════════════════════
    # Sheet 24: ESG والاستدامة — Green Valuation Scoring
    # ════════════════════════════════════════════════════════════════════════
    ws_esg = wb.create_sheet("ESG والاستدامة")
    _rtl(ws_esg)
    _widths(ws_esg, [42, 18, 18, 30])

    ws_esg.merge_cells("A1:D1")
    ws_esg["A1"].value     = "ESG والاستدامة — مؤشر التقييم الأخضر Green Valuation Scoring"
    ws_esg["A1"].font      = F_TITLE
    ws_esg["A1"].fill      = _fill("1A5E20")
    ws_esg["A1"].alignment = AL_CTR
    ws_esg.row_dimensions[1].height = 26

    _r_esg = 2
    _esg_is_qa = bool(payload.get("_qa_simulation"))
    _esg_hdrs = ["معيار التقييم", "الدرجة (0–5)", "الوزن", "ملاحظات"]
    for _ci_esg, _h_esg in enumerate(_esg_hdrs, 1):
        _c_esg = ws_esg.cell(_r_esg, _ci_esg, _h_esg)
        _c_esg.font = F_HDR; _c_esg.fill = _fill(C_BLUE_D); _c_esg.alignment = AL_CTR
    _r_esg += 1

    _esg_items = [
        ("الطاقة الشمسية / مصادر الطاقة المتجددة",   3 if _esg_is_qa else 0, "20%", "ألواح شمسية / طاقة متجددة"),
        ("العزل الحراري / كفاءة الطاقة",              2 if _esg_is_qa else 0, "15%", "عزل جدران وأسقف"),
        ("كفاءة استهلاك المياه",                       2 if _esg_is_qa else 0, "10%", "تركيبات موفرة للمياه"),
        ("القرب من وسائل النقل العام",                 4 if _esg_is_qa else 0, "15%", "على بُعد < 500م من محطة"),
        ("مواد البناء الصديقة للبيئة",                 2 if _esg_is_qa else 0, "10%", "مواد معاد تدويرها / منخفضة الكربون"),
        ("كفاءة تكاليف التشغيل",                       3 if _esg_is_qa else 0, "15%", "تكاليف تشغيل أقل من المتوسط"),
        ("جودة إدارة المبنى / BEMS",                   3 if _esg_is_qa else 0, "10%", "نظام إدارة مبنى ذكي"),
        ("المخاطر البيئية والموقع",                     4 if _esg_is_qa else 0, "5%",  "بعيد عن مناطق الفيضانات/التلوث"),
    ]
    _esg_score_rows = []
    for _item_esg, _score_esg, _wt_esg, _note_esg in _esg_items:
        ws_esg.cell(_r_esg, 1).value     = _item_esg;  ws_esg.cell(_r_esg, 1).alignment = AL_RT
        ws_esg.cell(_r_esg, 2).value     = _score_esg if _esg_is_qa else _ef
        ws_esg.cell(_r_esg, 2).alignment = AL_CTR
        ws_esg.cell(_r_esg, 3).value     = _wt_esg;   ws_esg.cell(_r_esg, 3).alignment = AL_CTR
        ws_esg.cell(_r_esg, 4).value     = _note_esg; ws_esg.cell(_r_esg, 4).alignment = AL_RT
        _esg_score_rows.append(_r_esg)
        _r_esg += 1

    # Total ESG score with formula
    ws_esg.row_dimensions[_r_esg].height = 6; _r_esg += 1
    _sec_hdr(ws_esg, _r_esg, 1, 4, "مجموع درجة ESG والتعديلات", bg=C_BLUE_M); _r_esg += 1

    _score_range = f"B{_esg_score_rows[0]}:B{_esg_score_rows[-1]}"
    _total_score_row = _r_esg
    ws_esg.cell(_r_esg, 1).value = "إجمالي درجة ESG (=SUM)"
    ws_esg.cell(_r_esg, 1).font  = F_LBL; ws_esg.cell(_r_esg, 1).alignment = AL_RT
    ws_esg.cell(_r_esg, 2).value = f"=SUM({_score_range})"
    ws_esg.cell(_r_esg, 2).font  = F_VAL; ws_esg.cell(_r_esg, 2).alignment = AL_CTR
    ws_esg.cell(_r_esg, 3).value = "من 40 (8 معايير × 5)"; ws_esg.cell(_r_esg, 3).alignment = AL_CTR
    _r_esg += 1

    # ESG category based on score
    _total_esg_score = sum(s for _, s, _, _ in _esg_items if isinstance(s, int))
    if _esg_is_qa:
        if _total_esg_score >= 30:
            _esg_cat = "ممتاز (A) — تأثير إيجابي على القيمة"
        elif _total_esg_score >= 20:
            _esg_cat = "جيد (B) — تأثير إيجابي معتدل"
        elif _total_esg_score >= 10:
            _esg_cat = "متوسط (C) — تأثير محدود"
        else:
            _esg_cat = "منخفض (D) — مخاطر بيئية"
    else:
        _esg_cat = _ef

    ws_esg.cell(_r_esg, 1).value = "تصنيف ESG"
    ws_esg.cell(_r_esg, 1).font  = F_LBL; ws_esg.cell(_r_esg, 1).alignment = AL_RT
    ws_esg.cell(_r_esg, 2).value = _esg_cat
    ws_esg.cell(_r_esg, 2).fill  = _fill(C_GREEN if "ممتاز" in str(_esg_cat) or "جيد" in str(_esg_cat) else C_GRAY)
    ws_esg.merge_cells(f"B{_r_esg}:D{_r_esg}")
    ws_esg.cell(_r_esg, 2).alignment = AL_RT; _r_esg += 1

    # cap rate adjustment formula
    _cap_adj_row = _r_esg
    ws_esg.cell(_r_esg, 1).value = "تعديل معدل الرسملة بسبب ESG"
    ws_esg.cell(_r_esg, 1).font  = F_LBL; ws_esg.cell(_r_esg, 1).alignment = AL_RT
    # adjustment: -0.025% per ESG point above 20 (max -0.5%)
    if _esg_is_qa:
        _adj_formula = f"=MAX(-0.5%,-(B{_total_score_row}-20)*0.025%)"
    else:
        _adj_formula = _ef
    ws_esg.cell(_r_esg, 2).value = _adj_formula
    ws_esg.cell(_r_esg, 2).alignment = AL_CTR
    ws_esg.cell(_r_esg, 3).value = "%-نقاط من معدل الرسملة"
    ws_esg.cell(_r_esg, 3).alignment = AL_RT
    ws_esg.cell(_r_esg, 4).value = "تعديل سلبي يُحسِّن المعدل (يزيد القيمة)"
    ws_esg.cell(_r_esg, 4).alignment = AL_RT; _r_esg += 1

    # Part H: ESG discount rate adjustment (same direction as cap rate adjustment)
    _dr_adj_row = _r_esg
    ws_esg.cell(_r_esg, 1).value = "تعديل معدل الخصم بسبب ESG"
    ws_esg.cell(_r_esg, 1).font  = F_LBL; ws_esg.cell(_r_esg, 1).alignment = AL_RT
    if _esg_is_qa:
        _dr_adj_formula = f"=B{_cap_adj_row}"  # same symmetric adjustment as cap rate
    else:
        _dr_adj_formula = _ef
    ws_esg.cell(_r_esg, 2).value = _dr_adj_formula
    ws_esg.cell(_r_esg, 2).alignment = AL_CTR
    ws_esg.cell(_r_esg, 3).value = "%-نقاط من معدل الخصم"
    ws_esg.cell(_r_esg, 3).alignment = AL_RT
    ws_esg.cell(_r_esg, 4).value = "مرتبط بتعديل معدل الرسملة — مُخفِّض للمخاطر البيئية"
    ws_esg.cell(_r_esg, 4).alignment = AL_RT; _r_esg += 1

    # ESG-adjusted cap rate (informational)
    ws_esg.cell(_r_esg, 1).value = "معدل الرسملة المعدَّل بعد ESG"
    ws_esg.cell(_r_esg, 1).font  = F_LBL; ws_esg.cell(_r_esg, 1).alignment = AL_RT
    if _esg_is_qa:
        _mctx_cr_expert = mctx.get("expert_selected_cap_rate", "8.00%")
        try:
            _cr_base_num = float(str(_mctx_cr_expert).replace("%", "").strip()) / 100
            ws_esg.cell(_r_esg, 2).value = f"={_cr_base_num}+B{_cap_adj_row}"
        except (ValueError, TypeError):
            ws_esg.cell(_r_esg, 2).value = f"=B{_cap_adj_row}"
    else:
        ws_esg.cell(_r_esg, 2).value = _ef
    ws_esg.cell(_r_esg, 2).fill  = _fill(C_GOLD_BG)
    ws_esg.cell(_r_esg, 2).font  = F_GOLD
    ws_esg.cell(_r_esg, 2).alignment = AL_CTR
    ws_esg.cell(_r_esg, 3).value = "نتيجة استرشادية — يؤكدها الخبير"
    ws_esg.cell(_r_esg, 3).alignment = AL_RT; _r_esg += 1

    ws_esg.row_dimensions[_r_esg].height = 6; _r_esg += 1
    _esg_disc_txt = (
        "لم يتم إدخال بيانات كافية لتطبيق تحليل الاستدامة في هذه النسخة." if not _esg_is_qa
        else "درجات ESG مبنية على محاكاة QA داخلية فقط. "
             "التعديلات استرشادية تعتمد على خصائص العقار كما أُدخلت من المستخدم."
    )
    _esg_disc = ws_esg.cell(_r_esg, 1, _esg_disc_txt)
    _esg_disc.font = Font(color="B43200", name="Arial", size=8, italic=True)
    ws_esg.merge_cells(f"A{_r_esg}:D{_r_esg}")

    # ════════════════════════════════════════════════════════════════════════
    # Sheet 25: مؤشرات تكلفة البناء — Construction Cost Source Readiness
    # ════════════════════════════════════════════════════════════════════════
    ws_cc = wb.create_sheet("مؤشرات تكلفة البناء")
    _rtl(ws_cc)
    _widths(ws_cc, [30, 12, 14, 16, 28, 16, 18, 16, 20, 36])

    ws_cc.merge_cells("A1:J1")
    ws_cc["A1"].value     = "مؤشرات تكلفة البناء — أساس تكلفة الإحلال (سجل داخلي)"
    ws_cc["A1"].font      = F_TITLE
    ws_cc["A1"].fill      = _fill("4A235A")
    ws_cc["A1"].alignment = AL_CTR
    ws_cc.row_dimensions[1].height = 26

    _cc_hdrs = ["بند التكلفة", "الوحدة", "الكمية", "تكلفة الوحدة",
                "مصدر السعر", "تاريخ المصدر", "حالة المصدر",
                "درجة الثقة", "تجاوز الخبير", "ملاحظات"]
    _r_cc = 2
    for _ci_cc, _h_cc in enumerate(_cc_hdrs, 1):
        _c_cc = ws_cc.cell(_r_cc, _ci_cc, _h_cc)
        _c_cc.font = F_HDR; _c_cc.fill = _fill(C_BLUE_D); _c_cc.alignment = AL_CTR
    _r_cc += 1

    _cc_is_qa = bool(payload.get("_qa_simulation"))
    _cc_area  = float(str(payload.get("area") or 0)) if payload.get("area") else 0
    _cc_items = mctx.get("cost_breakdown", [])
    if _cc_items and _cc_is_qa:
        for _item_cc in _cc_items:
            _item_n  = _item_cc.get("item", _ef)
            _unit_n  = _item_cc.get("unit", "م²")
            _qty_n   = _item_cc.get("quantity", _cc_area)
            _ucp_n   = _item_cc.get("unit_cost", _ef)
            ws_cc.cell(_r_cc, 1).value = _item_n;  ws_cc.cell(_r_cc, 1).alignment = AL_RT
            ws_cc.cell(_r_cc, 2).value = _unit_n;  ws_cc.cell(_r_cc, 2).alignment = AL_CTR
            ws_cc.cell(_r_cc, 3).value = _qty_n;   ws_cc.cell(_r_cc, 3).alignment = AL_CTR
            ws_cc.cell(_r_cc, 4).value = f"={_ucp_n}" if isinstance(_ucp_n, (int, float)) else str(_ucp_n)
            ws_cc.cell(_r_cc, 4).alignment = AL_CTR
            ws_cc.cell(_r_cc, 5).value = "محاكاة QA داخلية"; ws_cc.cell(_r_cc, 5).alignment = AL_RT
            ws_cc.cell(_r_cc, 6).value = "2026-06-01";        ws_cc.cell(_r_cc, 6).alignment = AL_CTR
            ws_cc.cell(_r_cc, 7).value = "تقدير داخلي";      ws_cc.cell(_r_cc, 7).alignment = AL_RT
            ws_cc.cell(_r_cc, 8).value = "متوسط";             ws_cc.cell(_r_cc, 8).alignment = AL_CTR
            ws_cc.cell(_r_cc, 9).value = _ef;                 ws_cc.cell(_r_cc, 9).alignment = AL_RT
            ws_cc.cell(_r_cc, 10).value = "يلزم استكمال من مصدر رسمي"; ws_cc.cell(_r_cc, 10).alignment = AL_RT
            _r_cc += 1
    else:
        for _ph_cc in ["هيكل إنشائي", "تشطيب داخلي", "تمديدات كهربائية",
                       "سباكة ومياه", "تكييف وتهوية", "واجهات خارجية",
                       "تجهيز أرضيات", "بنود غير مباشرة", "هامش طوارئ"]:
            ws_cc.cell(_r_cc, 1).value = _ph_cc; ws_cc.cell(_r_cc, 1).alignment = AL_RT
            for _ci_p in range(2, 11):
                ws_cc.cell(_r_cc, _ci_p).value = _ef
                ws_cc.cell(_r_cc, _ci_p).alignment = AL_CTR
            _r_cc += 1

    ws_cc.row_dimensions[_r_cc].height = 6; _r_cc += 1
    _cc_disc = ws_cc.cell(_r_cc, 1,
        "لم يتم ربط هذه النسخة بمصدر أسعار مواد بناء حي. "
        "تم استخدام مدخلات داخلية/محاكاة QA أو مدخلات الخبير. "
        "سيتم الربط الفعلي بقاعدة بيانات أسعار مواد البناء في مرحلة مستقبلية.")
    _cc_disc.font = Font(color="B43200", name="Arial", size=8, italic=True)
    ws_cc.merge_cells(f"A{_r_cc}:J{_r_cc}")
    ws_cc.freeze_panes = ws_cc["A3"]

    # Save
    wb_dir  = _WORKBOOKS / request_id
    wb_dir.mkdir(parents=True, exist_ok=True)
    wb_path = wb_dir / f"expert_review_{request_id}.xlsx"
    wb.save(str(wb_path))
    return wb_path

