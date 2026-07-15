# -*- coding: utf-8 -*-
"""
professional_valuation_preliminary_outputs.py
Phase H Addendum: Preliminary Report, Expert Draft Report & Expert Workbook.

Output tiers:
  Tier 1 — Advisory/Preliminary (this module):
    preliminary_pdf    Preliminary Professional Valuation PDF
    expert_draft_pdf   Expert Draft PDF (internal review)
    expert_workbook    Expert Workbook (internal/advisory)

  Tier 2 — Certified (Phase H, unchanged):
    certified_pdf / final_workbook (require certification_ready=True)

Endpoints (all JWT-protected):
  POST /api/professional-valuation/requests/<id>/preliminary-report
  GET  /api/professional-valuation/requests/<id>/preliminary-report
  POST /api/professional-valuation/requests/<id>/expert-draft-report
  GET  /api/professional-valuation/requests/<id>/expert-draft-report
  POST /api/professional-valuation/requests/<id>/expert-workbook
  GET  /api/professional-valuation/requests/<id>/expert-workbook

Strict rules:
  - Preliminary outputs do NOT require certification_ready=True.
  - Preliminary outputs NEVER claim final certification.
  - official_use_allowed=False, certified_use_allowed=False always.
  - No FPDF. PDF via HTML/Playwright (pdf_renderer).
  - Workbook via openpyxl.
  - No internal paths in API responses.
  - No OCR, no Qdrant, no RAG, no external APIs.
  - No fabricated signatures, stamps, or legal references.
  - Phase H certified output gate behavior unchanged.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

# ── Import shared helpers from Phase H ────────────────────────────────────────
# Phase H is always registered before this addendum in bridge_api.py.
from professional_valuation_outputs import (
    _OUT_DIR, _REG_DIR, _EV_DIR, _GATE_DIR, _TMPL_DIR, _PVR_ID_RE,
    _new_pvout_id, _new_pvoutevent_id, _PRIVATE_KEYS, _safe_output,
    _append_registry, _read_output_by_id, _latest_active_of_type,
    _output_version_for, _append_output_event, read_output_events,
    _load_gate_snapshot,
)

# ── Preliminary output storage ─────────────────────────────────────────────────

_PRELIM_OUT_DIR = _OUT_DIR.parent / "preliminary_outputs"
_PRELIM_OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Output types / advisory label ──────────────────────────────────────────────

_PRELIM_OUTPUT_TYPES = frozenset({"preliminary_pdf", "expert_draft_pdf", "expert_workbook"})
_ADVISORY_LABEL      = (
    "تقرير مبدئي / مسودة خبير — غير صالح للاستخدام الرسمي أو الاعتماد النهائي"
)
_NA = "غير متاح"
_NA2 = "يحتاج استكمال"

# ── Preliminary output record ──────────────────────────────────────────────────

def _new_prelim_record(
    request_id: str,
    output_type: str,
    generated_by: str,
    output_version: int,
) -> dict:
    now = datetime.utcnow().isoformat()
    return {
        "output_id":                   _new_pvout_id(),
        "request_id":                  request_id,
        "generated_at":                now,
        "generated_by":                generated_by,
        "output_type":                 output_type,
        "output_status":               "generation_failed",
        "output_version":              output_version,
        "report_number":               None,
        "file_available":              False,
        "file_size_bytes":             None,
        "file_hash_sha256":            None,
        "safe_download_token":         _new_pvout_id(),
        "internal_file_path":          None,    # never exposed in API
        "official_use_allowed":        False,   # always False for preliminary
        "certified_use_allowed":       False,   # always False for preliminary
        "preliminary_use_allowed":     True,    # advisory use allowed
        "advisory_only":               True,
        "certification_ready_required": False,
        "generation_blockers":         [],
        "warnings":                    [],
        "external_api_used":           False,
        "qdrant_used":                 False,
        "rag_used":                    False,
    }


# ── Preliminary readiness gate ─────────────────────────────────────────────────

def _check_preliminary_readiness(request_id: str) -> tuple[bool, list[str]]:
    """Allow preliminary output if any method or preliminary approval exists."""
    gate = _load_gate_snapshot(request_id)
    methods_ok  = gate.get("methods_completed", False)
    recon_ok    = gate.get("reconciliation_completed", False)
    prelim_ok   = gate.get("preliminary_approval_ready", False)

    if methods_ok or recon_ok or prelim_ok:
        return True, []

    blockers = [
        "لم يتم إنجاز أي طريقة تقييم بعد — يلزم تشغيل طريقة واحدة على الأقل"
        " قبل إنشاء المخرجات المبدئية أو مسودات الخبير",
    ]
    return False, blockers


# ── Preliminary output context ─────────────────────────────────────────────────

def build_professional_valuation_preliminary_output_context(request_id: str) -> dict:
    """Assemble advisory/preliminary context from all Professional Valuation phases.

    Unlike the certified context:
    - QA data is included with advisory labels.
    - Certification blockers are included as a visible section.
    - Expert notes are included in expert_notes section (for use in expert draft).
    - No internal paths.
    - advisory_only=True always.
    """
    ctx: dict = {
        "request_id":         request_id,
        "assembled_at":       datetime.utcnow().isoformat(),
        "context_type":       "professional_valuation_preliminary_output",
        "advisory_only":      True,
        "advisory_label":     _ADVISORY_LABEL,
        "external_api_used":  False,
        "qdrant_used":        False,
        "rag_used":           False,
    }

    # ── Request summary ───────────────────────────────────────────────────────
    _REPORT_TYPE_LABELS: dict = {
        "traditional_report":  "تقرير تقليدي",
        "detailed_report":     "تقرير تفصيلي",
        "professional_report": "تقرير احترافي",
    }
    req_summary: dict = {
        "request_id":        request_id,
        "request_number":    _NA,
        "client_name":       _NA,
        "client_type":       _NA,
        "property_title":    _NA,
        "property_address":  _NA,
        "property_type":     _NA,
        "valuation_purpose": _NA,
        "basis_of_value":    _NA,
        "valuation_date":    _NA,
        "inspection_date":   _NA,
        "currency":          "SAR",
        "report_language":   "ar",
        "report_type":       "professional_report",
        "report_type_label": "تقرير احترافي",
    }
    try:
        from professional_valuation_routes import _read_pvr as _pvr_read
        pvr = _pvr_read(request_id)
        if pvr:
            rt = pvr.get("report_type") or "professional_report"
            req_summary.update({
                "request_number":    pvr.get("request_number") or request_id,
                "client_name":       pvr.get("client_name") or _NA,
                "client_type":       pvr.get("client_type") or _NA,
                "property_title":    pvr.get("property_title") or _NA,
                "property_address":  pvr.get("property_address") or _NA,
                "property_type":     pvr.get("property_type") or _NA,
                "valuation_purpose": pvr.get("valuation_purpose") or _NA,
                "basis_of_value":    pvr.get("basis_of_value") or _NA,
                "valuation_date":    pvr.get("valuation_date") or _NA,
                "inspection_date":   pvr.get("inspection_date") or _NA,
                "currency":          pvr.get("currency") or "SAR",
                "report_language":   pvr.get("report_language") or "ar",
                "report_type":       rt,
                "report_type_label": _REPORT_TYPE_LABELS.get(rt, rt),
            })
    except (ImportError, Exception):
        pass
    ctx["request_summary"] = req_summary

    # ── Certification gate (shown as blockers, not as pass/fail) ─────────────
    gate = _load_gate_snapshot(request_id)
    ctx["certification_gate"] = {
        "certification_ready":               gate.get("certification_ready", False),
        "methods_completed":                 gate.get("methods_completed", False),
        "reconciliation_completed":          gate.get("reconciliation_completed", False),
        "preliminary_approval_ready":        gate.get("preliminary_approval_ready", False),
        "blockers":                          gate.get("blockers", []),
        "evaluated_at":                      gate.get("evaluated_at", _NA),
        "certification_status":              gate.get("certification_status", "مبدئي"),
        "advisory_note": "هذه المخرجات مبدئية وغير معتمدة — لاستخدام الخبراء الداخلي فقط",
    }

    # ── Evidence/source readiness (QA data included with label) ──────────────
    evidence_summary: dict = {
        "mandatory_document_readiness": False,
        "approved_count":               0,
        "missing_categories":           [],
        "qa_data_present":              True,
        "advisory_note": "البيانات الواردة قد تشمل محاكاة QA — للاستخدام المبدئي فقط",
    }
    try:
        from professional_valuation_evidence_routes import compute_gate_summary as _cev_gate
        eg = _cev_gate(request_id, gate.get("valuation_purpose", ""))
        evidence_summary.update({
            "mandatory_document_readiness": bool(eg.get("mandatory_documents_ready")),
            "approved_count":               int(eg.get("approved_count", 0)),
            "missing_categories":           eg.get("missing_categories", []),
            "qa_data_present":              not bool(eg.get("qa_data_cleared")),
        })
    except (ImportError, Exception):
        pass
    ctx["evidence_summary"] = evidence_summary

    # ── Source summary ────────────────────────────────────────────────────────
    source_summary: dict = {
        "production_source_count": 0,
        "qa_sources_present":      True,
        "advisory_note": "مصادر البيانات قد تشمل بيانات QA — مراجعة الخبير مطلوبة",
    }
    try:
        from professional_valuation_evidence_routes import compute_gate_summary as _cev_gate2
        sg = _cev_gate2(request_id, gate.get("valuation_purpose", ""))
        source_summary.update({
            "production_source_count": int(sg.get("real_source_count", 0)),
            "qa_sources_present":      not bool(sg.get("qa_data_cleared")),
        })
    except (ImportError, Exception):
        pass
    ctx["source_summary"] = source_summary

    # ── Comparable summary ────────────────────────────────────────────────────
    comparable_summary: dict = {
        "total_count":            0,
        "production_ready_count": 0,
        "staged_count":           0,
        "advisory_note": "قد تشتمل المقارنات على بيانات مرحلة التهيئة — مراجعة الخبير مطلوبة",
    }
    try:
        from professional_valuation_comparables import (
            _read_comparables as _rc, _COMPARABLE_DIR as _CDIR,
        )
        all_comps = _rc(request_id)
        comparable_summary["total_count"] = len(all_comps)
        comparable_summary["production_ready_count"] = sum(
            1 for c in all_comps
            if c.get("readiness_status") == "production_ready"
            and c.get("approval_status") == "approved"
        )
        comparable_summary["staged_count"] = sum(
            1 for c in all_comps
            if c.get("readiness_status") in ("staged", "qa", "pending")
        )
    except (ImportError, Exception):
        pass
    ctx["comparable_summary"] = comparable_summary

    # ── Method analysis ───────────────────────────────────────────────────────
    method_summary: dict = {
        "methods_completed":        False,
        "reconciliation_completed": False,
        "methods":                  [],
        "reconciliation_value":     _NA,
        "advisory_note": "نتائج الطرق مبدئية وقابلة للمراجعة",
    }
    try:
        from professional_valuation_methods import (
            _read_method_runs as _rmr, _read_reconciliation as _rrec,
        )
        runs = _rmr(request_id)
        if runs:
            method_summary["methods_completed"] = True
            method_summary["methods"] = [
                {
                    "method_type":    r.get("method_type", _NA),
                    "indicated_value": r.get("indicated_value", _NA),
                    "run_id":         r.get("run_id", _NA),
                    "status":         r.get("status", _NA),
                }
                for r in runs
            ]
        rec_list = _rrec(request_id)
        if rec_list:
            last_rec = rec_list[-1]
            method_summary["reconciliation_completed"] = True
            method_summary["reconciliation_value"] = last_rec.get("reconciled_value", _NA)
    except (ImportError, Exception):
        pass
    ctx["method_summary"] = method_summary

    # ── Preliminary approval ──────────────────────────────────────────────────
    preliminary_approval: dict = {
        "preliminary_approval_ready": False,
        "preliminary_value":          _NA,
        "advisory_note": "الموافقة المبدئية تؤكد مرحلة الدراسة الأولية فقط",
    }
    try:
        from professional_valuation_methods import _read_preliminary_approval as _rpa
        pa_list = _rpa(request_id)
        if pa_list:
            last_pa = pa_list[-1]
            preliminary_approval["preliminary_approval_ready"] = (
                last_pa.get("status") == "approved"
            )
            preliminary_approval["preliminary_value"] = last_pa.get("preliminary_value", _NA)
    except (ImportError, Exception):
        pass
    ctx["preliminary_approval"] = preliminary_approval

    # ── Advanced reviews (HBU, legal, ESG, SWOT) ─────────────────────────────
    advanced_reviews: dict = {
        "hbu_completed":   False,
        "legal_completed": False,
        "esg_completed":   False,
        "swot_completed":  False,
        "advisory_note": "المراجعات المتقدمة مبدئية — تتطلب اعتماداً نهائياً",
    }
    try:
        from professional_valuation_advanced_review import _read_advanced_reviews as _rar
        ar_list = _rar(request_id)
        for ar in ar_list:
            rt = ar.get("review_type", "")
            done = ar.get("status") in ("completed", "approved", "advisory_complete")
            if rt == "hbu":
                advanced_reviews["hbu_completed"]   = done
            elif rt == "legal":
                advanced_reviews["legal_completed"] = done
            elif rt == "esg":
                advanced_reviews["esg_completed"]   = done
            elif rt == "swot":
                advanced_reviews["swot_completed"]  = done
    except (ImportError, Exception):
        pass
    ctx["advanced_reviews"] = advanced_reviews

    # ── Missing certification gates (for expert next actions) ─────────────────
    blockers = gate.get("blockers", [])
    ctx["missing_certification_gates"] = {
        "blockers":      blockers,
        "blocker_count": len(blockers),
        "advisory_note": "هذه الموانع تمنع إصدار تقرير معتمد — لا تمنع المخرجات المبدئية",
    }

    # ── Expert next actions ───────────────────────────────────────────────────
    next_actions = gate.get("next_required_actions", [])
    ctx["expert_next_actions"] = {
        "actions": next_actions if next_actions else ["مراجعة البيانات المبدئية وإكمال المتطلبات"],
        "priority": "عالية" if len(blockers) > 5 else "متوسطة",
    }

    # ── Output matrix context ─────────────────────────────────────────────────
    try:
        from professional_valuation_output_matrix import (
            get_output_matrix_context, get_output_warnings,
        )
        _rt = req_summary.get("report_type", "professional_report")
        _vp = req_summary.get("valuation_purpose", "")
        _pt = req_summary.get("property_type", "")
        if _vp == _NA:
            _vp = ""
        if _pt == _NA:
            _pt = ""
        ctx["output_matrix"]   = get_output_matrix_context(_rt, _vp, _pt)
        ctx["output_warnings"] = get_output_warnings(_rt, _vp, advisory_only=True)
        ctx["report_type"]     = _rt
    except Exception:
        ctx["output_matrix"]   = {}
        ctx["output_warnings"] = []

    return ctx


# ── PDF generation: Preliminary Report ────────────────────────────────────────

def _generate_preliminary_pdf(
    ctx: dict, request_id: str, output_id: str,
) -> tuple[bool, str, int, str]:
    """Generate preliminary PDF via Jinja2 + Playwright.

    Returns (success, error_msg, size_bytes, sha256_hex).
    Does NOT raise; returns (False, error, 0, '') on any failure.
    """
    req_dir = _PRELIM_OUT_DIR / request_id
    req_dir.mkdir(parents=True, exist_ok=True)
    out_path = req_dir / f"{output_id}_preliminary_report.pdf"

    try:
        import jinja2
        tmpl_path = _TMPL_DIR / "professional_valuation_preliminary_report.html"
        tmpl_text = tmpl_path.read_text(encoding="utf-8")
        tmpl = jinja2.Environment(
            loader=jinja2.BaseLoader(),
            autoescape=True,
        ).from_string(tmpl_text)

        try:
            font_css = (_TMPL_DIR / "fonts" / "cairo_font.css").read_text(encoding="utf-8")
        except Exception:
            font_css = ""

        generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        html = tmpl.render(ctx=ctx, generated_at=generated_at, font_css_block=font_css)

        from pdf_renderer import render_pdf_from_html
        pdf_bytes = render_pdf_from_html(html)
        out_path.write_bytes(pdf_bytes)

        sha256 = hashlib.sha256(pdf_bytes).hexdigest()
        return True, "", len(pdf_bytes), sha256

    except Exception as exc:
        return False, str(exc), 0, ""


# ── PDF generation: Expert Draft Report ───────────────────────────────────────

def _generate_expert_draft_pdf(
    ctx: dict, request_id: str, output_id: str,
) -> tuple[bool, str, int, str]:
    """Generate expert draft PDF via Jinja2 + Playwright."""
    req_dir = _PRELIM_OUT_DIR / request_id
    req_dir.mkdir(parents=True, exist_ok=True)
    out_path = req_dir / f"{output_id}_expert_draft_report.pdf"

    try:
        import jinja2
        tmpl_path = _TMPL_DIR / "professional_valuation_expert_draft.html"
        tmpl_text = tmpl_path.read_text(encoding="utf-8")
        tmpl = jinja2.Environment(
            loader=jinja2.BaseLoader(),
            autoescape=True,
        ).from_string(tmpl_text)

        try:
            font_css = (_TMPL_DIR / "fonts" / "cairo_font.css").read_text(encoding="utf-8")
        except Exception:
            font_css = ""

        generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        html = tmpl.render(ctx=ctx, generated_at=generated_at, font_css_block=font_css)

        from pdf_renderer import render_pdf_from_html
        pdf_bytes = render_pdf_from_html(html)
        out_path.write_bytes(pdf_bytes)

        sha256 = hashlib.sha256(pdf_bytes).hexdigest()
        return True, "", len(pdf_bytes), sha256

    except Exception as exc:
        return False, str(exc), 0, ""


# ── Workbook generation: Expert Workbook (15 sheets) ──────────────────────────

_EXPERT_WB_SHEETS = [
    # ── Core (original 15) ──────────────────────────────────────────────────
    "ملخص المسودة",
    "بيانات الطلب",
    "بيانات العقار",
    "المستندات والمصادر",
    "المقارنات",
    "تحليل الطرق",
    "التوفيق المبدئي",
    "HBU",
    "الفحص القانوني",
    "ESG",
    "SWOT",
    "بوابات الاعتماد",
    "مراجعة الخبير",
    "ملاحظات داخلية",
    "سجل المخرجات",
    # ── Parity sheets (ported from ordinary valuation, sheets 16–43) ────────
    "مقدمة ونطاق التقييم",
    "الافتراضات والقيود",
    "طريقة مقارنة البيوع",
    "طريقة الدخل",
    "التدفقات النقدية DCF",
    "طريقة التكلفة",
    "قيمة الأرض",
    "تفصيل الإهلاك",
    "القيمة الإيجارية",
    "مقارنات إيجارية",
    "توفيق القيمة الإيجارية",
    "تحليل مخاطر DCF",
    "سيناريوهات What-If",
    "شراء أم إيجار",
    "نطاق الثقة وعدم اليقين",
    "مصادر الأسعار",
    "دعم التعديلات",
    "تحليل الاستدامة ESG",
    "تقييم الأثر البيئي",
    "مؤشرات تكلفة البناء",
    "مصفوفة المخاطر",
    "بيان الامتثال",
    "الإفصاحات المهنية",
    "التوصية النهائية",
    "اختبار اتساق الطرق",
    "حوكمة مصادر البيانات",
    "خارطة طريق الاعتماد",
    "قائمة فحص الاعتماد",
]


def _generate_expert_workbook(
    ctx: dict, request_id: str, output_id: str,
) -> tuple[bool, str, int, str]:
    """Generate expert workbook via openpyxl — RTL Arabic.

    Sheet set is determined by the output matrix (report_type × valuation_purpose
    × property_type).  All sheets are generated first; sheets not in the active
    set are removed before save.

    Returns (success, error_msg, size_bytes, sha256_hex).
    Does NOT raise.
    """
    req_dir = _PRELIM_OUT_DIR / request_id
    req_dir.mkdir(parents=True, exist_ok=True)
    out_path = req_dir / f"{output_id}_expert_workbook.xlsx"

    # ── Determine active sheet set from output matrix ─────────────────────────
    try:
        from professional_valuation_output_matrix import get_expert_sheets
        _rt  = ctx.get("report_type") or ctx.get("request_summary", {}).get("report_type", "professional_report")
        _vp  = ctx.get("request_summary", {}).get("valuation_purpose", "")
        _pt  = ctx.get("request_summary", {}).get("property_type", "")
        _active_sheets = frozenset(get_expert_sheets(_rt, _vp, _pt))
    except Exception:
        _active_sheets = None  # fallback: generate all sheets

    try:
        import openpyxl
        from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
        from openpyxl.utils import get_column_letter

        wb = openpyxl.Workbook()
        if wb.active and wb.active.title == "Sheet":
            wb.remove(wb.active)

        # ── Style helpers ─────────────────────────────────────────────────────
        _HDR_FILL  = PatternFill("solid", fgColor="1A5276")
        _SEC_FILL  = PatternFill("solid", fgColor="2E86C1")
        _WARN_FILL = PatternFill("solid", fgColor="FFF3CD")
        _OK_FILL   = PatternFill("solid", fgColor="D4EDDA")
        _ALT_FILL  = PatternFill("solid", fgColor="EBF5FB")
        _NA_FILL   = PatternFill("solid", fgColor="F8F9FA")
        _EXP_FILL  = PatternFill("solid", fgColor="FEF9E7")   # Expert-only notes

        _HDR_FONT  = Font(bold=True, color="FFFFFF", name="Calibri")
        _BOLD      = Font(bold=True, name="Calibri")
        _REG       = Font(name="Calibri")
        _WARN_FONT = Font(bold=True, color="7D6608", name="Calibri")
        _RTL_ALIGN = Alignment(horizontal="right", vertical="center", wrap_text=True, readingOrder=2)
        _CTR_ALIGN = Alignment(horizontal="center", vertical="center")
        _THIN_SIDE = Side(border_style="thin", color="CCCCCC")
        _THIN_BDR  = Border(left=_THIN_SIDE, right=_THIN_SIDE, top=_THIN_SIDE, bottom=_THIN_SIDE)

        def _sv(v) -> str:
            """Safe cell value: replace None/empty with غير متاح."""
            if v is None or str(v).strip() in ("", "None", "null", "nan"):
                return _NA
            return str(v)

        def _hdr(ws, row: int, text: str, cols: int = 3) -> None:
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=cols)
            c = ws.cell(row=row, column=1, value=text)
            c.font = _HDR_FONT; c.fill = _HDR_FILL; c.alignment = _CTR_ALIGN

        def _kv(ws, row: int, key: str, value, warn: bool = False) -> None:
            v = _sv(value)
            ck = ws.cell(row=row, column=1, value=key)
            cv = ws.cell(row=row, column=2, value=v)
            ck.font = _BOLD; ck.alignment = _RTL_ALIGN; ck.border = _THIN_BDR
            cv.font = _WARN_FONT if warn else _REG
            cv.fill = _WARN_FILL if warn else (_NA_FILL if v == _NA else _ALT_FILL)
            cv.alignment = _RTL_ALIGN; cv.border = _THIN_BDR

        def _bool_cell(ws, row: int, col: int, val: bool) -> None:
            text = "نعم ✓" if val else "لا ✗"
            c = ws.cell(row=row, column=col, value=text)
            c.font = _BOLD; c.fill = _OK_FILL if val else _WARN_FILL
            c.alignment = _CTR_ALIGN; c.border = _THIN_BDR

        def _col_widths(ws, widths: list) -> None:
            for i, w in enumerate(widths, 1):
                ws.column_dimensions[get_column_letter(i)].width = w

        req     = ctx.get("request_summary", {})
        gate    = ctx.get("certification_gate", {})
        methods = ctx.get("method_summary", {})
        ev_sum  = ctx.get("evidence_summary", {})
        comp    = ctx.get("comparable_summary", {})
        adv     = ctx.get("advanced_reviews", {})
        prelim  = ctx.get("preliminary_approval", {})
        blockers = ctx.get("missing_certification_gates", {}).get("blockers", [])

        # ── 1. ملخص المسودة ──────────────────────────────────────────────────
        ws = wb.create_sheet("ملخص المسودة")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "ملخص مسودة تقرير التقييم المهني", 3)
        # Advisory warning banner
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=3)
        warn_cell = ws.cell(row=2, column=1, value=_ADVISORY_LABEL)
        warn_cell.fill = _WARN_FILL; warn_cell.font = _WARN_FONT
        warn_cell.alignment = _CTR_ALIGN; warn_cell.border = _THIN_BDR

        row = 4
        for k, v in [
            ("رقم المخرج", ctx.get("output_id", _NA)),
            ("نوع المخرج", ctx.get("output_type", _NA)),
            ("رقم التقرير المبدئي", ctx.get("report_number", _NA)),
            ("رقم الطلب", req.get("request_id", _NA)),
            ("نوع التقرير", req.get("report_type_label", "تقرير احترافي")),
            ("اسم العميل", req.get("client_name", _NA)),
            ("عنوان العقار", req.get("property_address", _NA)),
            ("نوع العقار", req.get("property_type", _NA)),
            ("غرض التقييم", req.get("valuation_purpose", _NA)),
            ("أساس القيمة", req.get("basis_of_value", _NA)),
            ("تاريخ الإنشاء", ctx.get("assembled_at", _NA)[:10] if ctx.get("assembled_at") else _NA),
            ("حالة الاعتماد النهائي", "غير معتمد — مبدئي فقط"),
            ("استخدام رسمي مسموح", "لا"),
            ("استخدام معتمد مسموح", "لا"),
        ]:
            _kv(ws, row, k, v, warn=(k in ("حالة الاعتماد النهائي", "استخدام رسمي مسموح", "استخدام معتمد مسموح")))
            row += 1
        _col_widths(ws, [30, 40, 20])

        # ── 2. بيانات الطلب ──────────────────────────────────────────────────
        ws = wb.create_sheet("بيانات الطلب")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "بيانات الطلب")
        row = 3
        for k, v in [
            ("رقم الطلب",       req.get("request_id", _NA)),
            ("رقم مرجع الطلب",  req.get("request_number", _NA)),
            ("نوع التقرير",     req.get("report_type_label", "تقرير احترافي")),
            ("اسم العميل",      req.get("client_name", _NA)),
            ("نوع العميل",      req.get("client_type", _NA)),
            ("غرض التقييم",     req.get("valuation_purpose", _NA)),
            ("أساس القيمة",     req.get("basis_of_value", _NA)),
            ("تاريخ التقييم",   req.get("valuation_date", _NA)),
            ("تاريخ المعاينة",  req.get("inspection_date", _NA)),
            ("العملة",          req.get("currency", "SAR")),
            ("لغة التقرير",     req.get("report_language", "ar")),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [30, 40, 20])

        # ── 3. بيانات العقار ─────────────────────────────────────────────────
        ws = wb.create_sheet("بيانات العقار")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "بيانات العقار")
        row = 3
        for k, v in [
            ("عنوان العقار",  req.get("property_address", _NA)),
            ("نوع العقار",    req.get("property_type", _NA)),
            ("عنوان الملكية", req.get("property_title", _NA)),
            ("لغة التقرير",  req.get("report_language", "ar")),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [30, 40, 20])

        # ── 4. المستندات والمصادر ─────────────────────────────────────────────
        ws = wb.create_sheet("المستندات والمصادر")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "المستندات والمصادر — بيانات مبدئية")
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=3)
        note_cell = ws.cell(row=2, column=1, value=ev_sum.get("advisory_note", ""))
        note_cell.fill = _WARN_FILL; note_cell.font = _WARN_FONT; note_cell.alignment = _CTR_ALIGN
        row = 4
        for k, v in [
            ("جاهزية المستندات الإلزامية", _sv(ev_sum.get("mandatory_document_readiness"))),
            ("عدد المستندات المعتمدة",     _sv(ev_sum.get("approved_count", 0))),
            ("الفئات المفقودة",            "; ".join(ev_sum.get("missing_categories", [])) or _NA),
            ("بيانات QA موجودة",           "نعم — مبدئي" if ev_sum.get("qa_data_present") else "لا"),
            ("عدد المصادر الإنتاجية",      _sv(ctx.get("source_summary", {}).get("production_source_count", 0))),
            ("مصادر QA موجودة",            "نعم — مبدئي" if ctx.get("source_summary", {}).get("qa_sources_present") else "لا"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [30, 40, 20])

        # ── 5. المقارنات ──────────────────────────────────────────────────────
        ws = wb.create_sheet("المقارنات")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "المقارنات — بيانات مبدئية")
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=3)
        note_cell = ws.cell(row=2, column=1, value=comp.get("advisory_note", ""))
        note_cell.fill = _WARN_FILL; note_cell.font = _WARN_FONT; note_cell.alignment = _CTR_ALIGN
        row = 4
        for k, v in [
            ("إجمالي المقارنات",     _sv(comp.get("total_count", 0))),
            ("مقارنات جاهزة إنتاجياً", _sv(comp.get("production_ready_count", 0))),
            ("مقارنات في مرحلة التهيئة", _sv(comp.get("staged_count", 0))),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [30, 40, 20])

        # ── 6. تحليل الطرق ───────────────────────────────────────────────────
        ws = wb.create_sheet("تحليل الطرق")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "تحليل طرق التقييم — مبدئي")
        row = 3
        ws.cell(row=row, column=1, value="الطريقة").font = _BOLD
        ws.cell(row=row, column=2, value="القيمة المؤشرة").font = _BOLD
        ws.cell(row=row, column=3, value="الحالة").font = _BOLD
        row += 1
        method_list = methods.get("methods", [])
        if method_list:
            for m in method_list:
                ws.cell(row=row, column=1, value=_sv(m.get("method_type"))).alignment = _RTL_ALIGN
                ws.cell(row=row, column=2, value=_sv(m.get("indicated_value"))).alignment = _RTL_ALIGN
                ws.cell(row=row, column=3, value=_sv(m.get("status"))).alignment = _RTL_ALIGN
                row += 1
        else:
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
            c = ws.cell(row=row, column=1, value=_NA2)
            c.fill = _WARN_FILL; c.font = _WARN_FONT; c.alignment = _CTR_ALIGN
        _col_widths(ws, [30, 30, 20])

        # ── 7. التوفيق المبدئي ───────────────────────────────────────────────
        ws = wb.create_sheet("التوفيق المبدئي")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "التوفيق المبدئي — غير نهائي")
        row = 3
        for k, v in [
            ("اكتملت الطرق",         methods.get("methods_completed", False)),
            ("اكتملت التسوية",        methods.get("reconciliation_completed", False)),
            ("القيمة المُسوَّاة المبدئية", methods.get("reconciliation_value", _NA)),
            ("جاهزية الموافقة المبدئية", prelim.get("preliminary_approval_ready", False)),
            ("القيمة المبدئية",       prelim.get("preliminary_value", _NA)),
        ]:
            if isinstance(v, bool):
                ws.cell(row=row, column=1, value=k).font = _BOLD
                _bool_cell(ws, row, 2, v)
            else:
                _kv(ws, row, k, v)
            row += 1
        _col_widths(ws, [30, 30, 20])

        # ── 8. HBU ────────────────────────────────────────────────────────────
        ws = wb.create_sheet("HBU")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "تحليل أعلى وأفضل استغلال — HBU")
        row = 3
        _kv(ws, row, "اكتمال مراجعة HBU", "نعم" if adv.get("hbu_completed") else _NA2)
        row += 1
        _kv(ws, row, "ملاحظة", adv.get("advisory_note", _NA))
        _col_widths(ws, [30, 40, 20])

        # ── 9. الفحص القانوني ────────────────────────────────────────────────
        ws = wb.create_sheet("الفحص القانوني")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "الفحص القانوني المبدئي")
        row = 3
        _kv(ws, row, "اكتمال الفحص القانوني", "نعم" if adv.get("legal_completed") else _NA2)
        row += 1
        _kv(ws, row, "ملاحظة استشارية", "هذا الفحص مبدئي ولا يمثل رأياً قانونياً نهائياً")
        _col_widths(ws, [30, 40, 20])

        # ── 10. ESG ───────────────────────────────────────────────────────────
        ws = wb.create_sheet("ESG")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "ESG والمخاطر المناخية — مبدئي")
        row = 3
        _kv(ws, row, "اكتمال مراجعة ESG", "نعم" if adv.get("esg_completed") else _NA2)
        row += 1
        _kv(ws, row, "ملاحظة", "نتائج ESG استشارية ولا تؤثر تلقائياً على القيمة المبدئية")
        _col_widths(ws, [30, 40, 20])

        # ── 11. SWOT ──────────────────────────────────────────────────────────
        ws = wb.create_sheet("SWOT")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "تحليل SWOT المبدئي")
        row = 3
        _kv(ws, row, "اكتمال تحليل SWOT", "نعم" if adv.get("swot_completed") else _NA2)
        row += 1
        _kv(ws, row, "ملاحظة", "تحليل SWOT مبدئي — يستلزم مراجعة إضافية")
        _col_widths(ws, [30, 40, 20])

        # ── 12. بوابات الاعتماد ───────────────────────────────────────────────
        ws = wb.create_sheet("بوابات الاعتماد")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "موانع الاعتماد النهائي المتبقية", 3)
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=3)
        note_cell = ws.cell(row=2, column=1,
            value="الموانع التالية تمنع الاعتماد النهائي — لا تمنع المخرجات المبدئية")
        note_cell.fill = _WARN_FILL; note_cell.font = _WARN_FONT; note_cell.alignment = _CTR_ALIGN
        row = 4
        if blockers:
            for blocker in blockers:
                ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
                c = ws.cell(row=row, column=1, value=str(blocker))
                c.fill = _WARN_FILL; c.font = _WARN_FONT; c.alignment = _RTL_ALIGN
                c.border = _THIN_BDR; row += 1
        else:
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
            c = ws.cell(row=row, column=1, value="لا توجد موانع — قد تكون البيانات غير مكتملة")
            c.fill = _OK_FILL; c.alignment = _CTR_ALIGN
        _col_widths(ws, [10, 40, 20])

        # ── 13. مراجعة الخبير ────────────────────────────────────────────────
        ws = wb.create_sheet("مراجعة الخبير")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "قائمة مراجعة الخبير الداخلية")
        row = 3
        checklist = [
            ("تحقق من مصادر البيانات",         gate.get("real_sources_ready", False)),
            ("تحقق من المقارنات الإنتاجية",     gate.get("comparables_ready", False)),
            ("تحقق من اكتمال المستندات",        gate.get("mandatory_documents_ready", False)),
            ("تحقق من إنجاز الطرق",             gate.get("methods_completed", False)),
            ("تحقق من التسوية",                  gate.get("reconciliation_completed", False)),
            ("تحقق من الموافقة المبدئية",        gate.get("preliminary_approval_ready", False)),
            ("تحقق من مراجعة HBU",               adv.get("hbu_completed", False)),
            ("تحقق من الفحص القانوني",           adv.get("legal_completed", False)),
            ("تحقق من مراجعة ESG",               adv.get("esg_completed", False)),
            ("تحقق من تحليل SWOT",               adv.get("swot_completed", False)),
        ]
        for label, val in checklist:
            ws.cell(row=row, column=1, value=label).font = _BOLD
            ws.cell(row=row, column=1).alignment = _RTL_ALIGN
            ws.cell(row=row, column=1).border = _THIN_BDR
            _bool_cell(ws, row, 2, bool(val))
            row += 1
        _col_widths(ws, [40, 15, 15])

        # ── 14. ملاحظات داخلية ───────────────────────────────────────────────
        ws = wb.create_sheet("ملاحظات داخلية")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "ملاحظات داخلية — للخبير فقط — سري")
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=3)
        exp_cell = ws.cell(row=2, column=1, value="هذه الورقة مخصصة للخبير فقط — لا تُشارك خارجياً")
        exp_cell.fill = _EXP_FILL; exp_cell.font = _WARN_FONT; exp_cell.alignment = _CTR_ALIGN
        row = 4
        next_actions = ctx.get("expert_next_actions", {})
        for i, action in enumerate(next_actions.get("actions", []), 1):
            ws.cell(row=row, column=1, value=f"الإجراء {i}").font = _BOLD
            ws.cell(row=row, column=2, value=str(action)).font = _REG
            ws.cell(row=row, column=2).fill = _EXP_FILL
            ws.cell(row=row, column=2).alignment = _RTL_ALIGN
            row += 1
        if not next_actions.get("actions"):
            _kv(ws, row, "الإجراءات المطلوبة", _NA)
        _col_widths(ws, [25, 50, 15])

        # ── 15. سجل المخرجات ─────────────────────────────────────────────────
        ws = wb.create_sheet("سجل المخرجات")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "سجل المخرجات المبدئية", 4)
        row = 3
        ws.cell(row=row, column=1, value="معرف المخرج").font = _BOLD
        ws.cell(row=row, column=2, value="النوع").font = _BOLD
        ws.cell(row=row, column=3, value="تاريخ الإنشاء").font = _BOLD
        ws.cell(row=row, column=4, value="الحالة").font = _BOLD
        row += 1
        try:
            from professional_valuation_outputs import _read_registry as _rreg
            all_records = _rreg(request_id)
            prelim_records = [
                r for r in all_records
                if r.get("output_type") in _PRELIM_OUTPUT_TYPES
            ]
            for r in prelim_records[-10:]:   # last 10
                ws.cell(row=row, column=1, value=_sv(r.get("output_id"))).font = _REG
                ws.cell(row=row, column=2, value=_sv(r.get("output_type"))).font = _REG
                ws.cell(row=row, column=3, value=_sv(r.get("generated_at", "")[:10])).font = _REG
                ws.cell(row=row, column=4, value=_sv(r.get("output_status"))).font = _REG
                row += 1
        except (ImportError, Exception):
            ws.cell(row=row, column=1, value=_NA)
        _col_widths(ws, [25, 20, 18, 18])

        # ════════════════════════════════════════════════════════════════════
        # Parity sheets 16–43 — ported from ordinary valuation workbook
        # ════════════════════════════════════════════════════════════════════
        _src_sum = ctx.get("source_summary", {})

        # ── 16. مقدمة ونطاق التقييم ──────────────────────────────────────────
        ws = wb.create_sheet("مقدمة ونطاق التقييم")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "مقدمة التقرير ونطاق التقييم")
        row = 3
        for k, v in [
            ("رقم الطلب",           req.get("request_id", _NA)),
            ("غرض التقييم",         req.get("valuation_purpose", _NA)),
            ("أساس القيمة",         req.get("basis_of_value", _NA)),
            ("تاريخ التقييم",       req.get("valuation_date", _NA)),
            ("تاريخ المعاينة",      req.get("inspection_date", _NA)),
            ("نطاق الطرق المطلوبة", "مقارنة البيوع — الدخل — التكلفة — DCF"),
            ("القيود العامة",        "بيانات مبدئية — تخضع للمراجعة"),
            ("حالة الاعتماد",       "غير معتمد — مرحلة مبدئية"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [30, 42, 18])

        # ── 17. الافتراضات والقيود ───────────────────────────────────────────
        ws = wb.create_sheet("الافتراضات والقيود")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "الافتراضات الخاصة والقيود")
        row = 3
        for k, v in [
            ("الافتراض 1", "تم التحقق من الملكية من خلال المستندات المقدمة فقط"),
            ("الافتراض 2", "بيانات المقارنات مبنية على معطيات السوق المتاحة"),
            ("الافتراض 3", "لا عوائق قانونية معلومة تؤثر على القيمة — يخضع للتحقق"),
            ("الافتراض 4", "الحالة البنائية مبنية على نتيجة المعاينة البصرية"),
            ("القيد 1",    "هذا التقرير مبدئي وغير صالح للاستخدام الرسمي"),
            ("القيد 2",    "النتائج تخضع لتحديث عند توافر مزيد من البيانات"),
            ("القيد 3",    "لم تُجرَ دراسة هندسية أو بيئية متخصصة"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [18, 54, 18])

        # ── 18. طريقة مقارنة البيوع ──────────────────────────────────────────
        ws = wb.create_sheet("طريقة مقارنة البيوع")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "طريقة مقارنة البيوع — مبدئي")
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=3)
        c = ws.cell(row=2, column=1,
            value="بيانات مبدئية — يحتاج استكمال من مقارنات إنتاجية معتمدة")
        c.fill = _WARN_FILL; c.font = _WARN_FONT; c.alignment = _CTR_ALIGN
        row = 4
        for k, v in [
            ("إجمالي المقارنات",             _sv(comp.get("total_count", 0))),
            ("مقارنات جاهزة إنتاجياً",       _sv(comp.get("production_ready_count", 0))),
            ("مقارنات في مرحلة التهيئة",      _sv(comp.get("staged_count", 0))),
            ("متوسط سعر المتر المعدل",        _NA2),
            ("القيمة المشتقة من المقارنات",   _NA2),
            ("ملاحظة الخبير",                "يتطلب إدخال معاملات التعديل — بيانات محاكاة داخلية"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [35, 38, 17])

        # ── 19. طريقة الدخل ──────────────────────────────────────────────────
        ws = wb.create_sheet("طريقة الدخل")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "طريقة الدخل — مبدئي")
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=3)
        c = ws.cell(row=2, column=1,
            value="بيانات مبدئية — يحتاج استكمال القيم الإيجارية وبيانات الدخل")
        c.fill = _WARN_FILL; c.font = _WARN_FONT; c.alignment = _CTR_ALIGN
        row = 4
        for k, v in [
            ("القيمة الإيجارية السنوية",      _NA2),
            ("معدل الشغور المقدر (%)",         _NA2),
            ("صافي الدخل التشغيلي (NOI)",      _NA2),
            ("معدل الرسملة (%)",               _NA2),
            ("القيمة المشتقة من الدخل",        _NA2),
            ("الإيجارات المرجعية المستخدمة",   _NA2),
            ("ملاحظة",                          "يتطلب بيانات سوق إيجارية معتمدة"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [35, 38, 17])

        # ── 20. التدفقات النقدية DCF ──────────────────────────────────────────
        ws = wb.create_sheet("التدفقات النقدية DCF")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "تحليل التدفقات النقدية المخصومة — DCF — مبدئي")
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=3)
        c = ws.cell(row=2, column=1,
            value="بيانات مبدئية — يحتاج استكمال بيانات التدفقات ومعدل الخصم")
        c.fill = _WARN_FILL; c.font = _WARN_FONT; c.alignment = _CTR_ALIGN
        row = 4
        for k, v in [
            ("فترة الاستثمار (سنوات)",           _NA2),
            ("معدل الخصم (%)",                    _NA2),
            ("معدل النمو الإيجاري المتوقع (%)",   _NA2),
            ("معدل الرسملة الطرفي (%)",           _NA2),
            ("القيمة الحالية الصافية — NPV",       _NA2),
            ("القيمة التقييمية بـ DCF",            _NA2),
            ("ملاحظة",                             "للمراجعة الداخلية — يتطلب توقعات مالية مفصلة"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [40, 38, 12])

        # ── 21. طريقة التكلفة ────────────────────────────────────────────────
        ws = wb.create_sheet("طريقة التكلفة")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "طريقة التكلفة — مبدئي")
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=3)
        c = ws.cell(row=2, column=1,
            value="بيانات مبدئية — يحتاج استكمال مؤشرات تكلفة البناء والإهلاك")
        c.fill = _WARN_FILL; c.font = _WARN_FONT; c.alignment = _CTR_ALIGN
        row = 4
        for k, v in [
            ("قيمة الأرض",                     _NA2),
            ("تكلفة الإنشاء للمتر (ريال/م²)",   _NA2),
            ("إجمالي تكلفة الإنشاء",             _NA2),
            ("نسبة الإهلاك (%)",                  _NA2),
            ("إهلاك مجمع",                        _NA2),
            ("القيمة المُستبدَلة المخفضة",         _NA2),
            ("القيمة الإجمالية بطريقة التكلفة",    _NA2),
            ("ملاحظة",                             "يتطلب مسح ميداني وبيانات تكلفة بناء محدثة"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [38, 38, 14])

        # ── 22. قيمة الأرض ───────────────────────────────────────────────────
        ws = wb.create_sheet("قيمة الأرض")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "تقدير قيمة الأرض — مبدئي")
        row = 3
        for k, v in [
            ("المنطقة",                          req.get("property_address", _NA)),
            ("نوع العقار",                        req.get("property_type", _NA)),
            ("سعر المتر الأرضي المقدر (ريال)",    _NA2),
            ("المساحة الإجمالية (م²)",             _NA2),
            ("القيمة الإجمالية المقدرة للأرض",    _NA2),
            ("المصدر",                             "مصادر سوقية مبدئية — يحتاج تأكيداً"),
            ("ملاحظة",                             "تقدير مبدئي — يستلزم مقارنات أرض معتمدة"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [35, 38, 17])

        # ── 23. تفصيل الإهلاك ────────────────────────────────────────────────
        ws = wb.create_sheet("تفصيل الإهلاك")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "تفصيل الإهلاك وعمر المبنى")
        row = 3
        for k, v in [
            ("العمر الفعلي للمبنى (سنة)",         _NA2),
            ("العمر الاقتصادي المتوقع (سنة)",     _NA2),
            ("العمر المتبقي (سنة)",                _NA2),
            ("نسبة الإهلاك المادي (%)",            _NA2),
            ("الإهلاك الوظيفي (%)",                _NA2),
            ("الإهلاك الخارجي (%)",                _NA2),
            ("إجمالي الإهلاك (%)",                 _NA2),
            ("المصدر",                              "معاينة ميدانية — يحتاج بيانات إضافية"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [35, 38, 17])

        # ── 24. القيمة الإيجارية ─────────────────────────────────────────────
        ws = wb.create_sheet("القيمة الإيجارية")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "تحليل القيمة الإيجارية السوقية — مبدئي")
        row = 3
        for k, v in [
            ("الإيجار السوقي للمتر (ريال/م²/سنة)", _NA2),
            ("المساحة المؤجرة المقدرة (م²)",          _NA2),
            ("الإيجار الإجمالي السنوي",               _NA2),
            ("معدل الشغور المقدر (%)",                 _NA2),
            ("صافي الإيجار الفعلي",                    _NA2),
            ("نوع الاستخدام الإيجاري",                 req.get("property_type", _NA)),
            ("المصدر",                                  "بيانات سوق مبدئية — يحتاج تحقق"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [40, 38, 12])

        # ── 25. مقارنات إيجارية ──────────────────────────────────────────────
        ws = wb.create_sheet("مقارنات إيجارية")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "مقارنات إيجارية — مبدئي")
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=3)
        c = ws.cell(row=2, column=1,
            value="بيانات مبدئية — يحتاج استكمال من مقارنات إيجارية معتمدة")
        c.fill = _WARN_FILL; c.font = _WARN_FONT; c.alignment = _CTR_ALIGN
        row = 4
        ws.cell(row=row, column=1, value="العقار").font = _BOLD
        ws.cell(row=row, column=2, value="الإيجار (ريال/م²/سنة)").font = _BOLD
        ws.cell(row=row, column=3, value="ملاحظة").font = _BOLD
        row += 1
        for i in range(1, 5):
            ws.cell(row=row, column=1,
                value=f"مقارن إيجاري {i}").alignment = _RTL_ALIGN
            ws.cell(row=row, column=2, value=_NA2).fill = _WARN_FILL
            ws.cell(row=row, column=3, value="يحتاج استكمال").fill = _WARN_FILL
            row += 1
        _col_widths(ws, [30, 28, 32])

        # ── 26. توفيق القيمة الإيجارية ────────────────────────────────────────
        ws = wb.create_sheet("توفيق القيمة الإيجارية")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "توفيق تقديرات القيمة الإيجارية — مبدئي")
        row = 3
        for k, v in [
            ("متوسط إيجار المقارنات",           _NA2),
            ("إيجار السوق المرجح",               _NA2),
            ("الإيجار المحدد للعقار",            _NA2),
            ("نسبة الانحراف عن السوق (%)",       _NA2),
            ("ملاحظة التوفيق",                   "يتطلب اكتمال بيانات المقارنات الإيجارية"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [35, 38, 17])

        # ── 27. تحليل مخاطر DCF ───────────────────────────────────────────────
        ws = wb.create_sheet("تحليل مخاطر DCF")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "تحليل مخاطر التدفقات النقدية — مبدئي")
        row = 3
        for k, v in [
            ("سيناريو متفائل — معدل الخصم (%)",   _NA2),
            ("سيناريو متفائل — القيمة",            _NA2),
            ("سيناريو محايد — معدل الخصم (%)",    _NA2),
            ("سيناريو محايد — القيمة",             _NA2),
            ("سيناريو متشائم — معدل الخصم (%)",   _NA2),
            ("سيناريو متشائم — القيمة",            _NA2),
            ("نطاق الحساسية",                       _NA2),
            ("ملاحظة",                               "يتطلب اكتمال تحليل DCF"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [40, 36, 14])

        # ── 28. سيناريوهات What-If ────────────────────────────────────────────
        ws = wb.create_sheet("سيناريوهات What-If")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "سيناريوهات What-If وتحليل الحساسية — مبدئي", 4)
        row = 3
        ws.cell(row=row, column=1, value="المتغير").font = _BOLD
        ws.cell(row=row, column=2, value="التغيير (-10%)").font = _BOLD
        ws.cell(row=row, column=3, value="القاعدة").font = _BOLD
        ws.cell(row=row, column=4, value="التغيير (+10%)").font = _BOLD
        row += 1
        for param in ["سعر المتر", "معدل الرسملة", "نسبة الشغور", "معدل الخصم"]:
            ws.cell(row=row, column=1, value=param).alignment = _RTL_ALIGN
            for col in [2, 3, 4]:
                ws.cell(row=row, column=col, value=_NA2).fill = _WARN_FILL
            row += 1
        _col_widths(ws, [26, 22, 22, 22])

        # ── 29. شراء أم إيجار ────────────────────────────────────────────────
        ws = wb.create_sheet("شراء أم إيجار")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "تحليل شراء أم إيجار — مبدئي")
        row = 3
        for k, v in [
            ("سعر الشراء المقدر",            _NA2),
            ("الدفعة الأولى المفترضة (%)",    _NA2),
            ("معدل التمويل (%)",               _NA2),
            ("القسط الشهري المقدر",            _NA2),
            ("إيجار مماثل شهرياً",             _NA2),
            ("نقطة التعادل (سنوات)",           _NA2),
            ("التوصية",                         "يتطلب اكتمال البيانات المالية"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [35, 38, 17])

        # ── 30. نطاق الثقة وعدم اليقين ───────────────────────────────────────
        ws = wb.create_sheet("نطاق الثقة وعدم اليقين")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "نطاق الثقة وعدم اليقين في التقدير")
        row = 3
        for k, v in [
            ("القيمة المركزية المقدرة",         methods.get("reconciliation_value", _NA)),
            ("الحد الأدنى للتقدير (-10%)",      _NA2),
            ("الحد الأعلى للتقدير (+10%)",      _NA2),
            ("مستوى الثقة",                      "متوسط — مبدئي"),
            ("مصادر عدم اليقين",                "مقارنات — معدل رسملة — بيانات سوق محلي"),
            ("ملاحظة",                            "نطاق الثقة يضيق عند اكتمال البيانات الإنتاجية"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [35, 38, 17])

        # ── 31. مصادر الأسعار ────────────────────────────────────────────────
        ws = wb.create_sheet("مصادر الأسعار")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "مصادر بيانات الأسعار — مبدئية")
        row = 3
        for k, v in [
            ("عدد المصادر الإنتاجية",    _sv(_src_sum.get("production_source_count", 0))),
            ("مصادر QA موجودة",           "نعم — مبدئي" if _src_sum.get("qa_sources_present") else "لا"),
            ("تصنيف المصادر",             "مصادر سوقية — بيانات حكومية — مقارنات ميدانية"),
            ("حالة المصادر",              "مبدئية — تخضع للتحقق والاعتماد"),
            ("ملاحظة",                    _sv(_src_sum.get("advisory_note", _NA))),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [35, 38, 17])

        # ── 32. دعم التعديلات ────────────────────────────────────────────────
        ws = wb.create_sheet("دعم التعديلات")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "تحليل وتوثيق التعديلات — مبدئي")
        row = 3
        ws.cell(row=row, column=1, value="عنصر التعديل").font = _BOLD
        ws.cell(row=row, column=2, value="المعامل المقترح").font = _BOLD
        ws.cell(row=row, column=3, value="مبرر التعديل").font = _BOLD
        row += 1
        for adj_item in ["الموقع", "المساحة", "العمر", "الحالة", "التشطيب", "الوقت"]:
            ws.cell(row=row, column=1, value=adj_item).alignment = _RTL_ALIGN
            ws.cell(row=row, column=2, value=_NA2).fill = _WARN_FILL
            ws.cell(row=row, column=3,
                value="يحتاج تأصيل من بيانات المقارنات").alignment = _RTL_ALIGN
            row += 1
        _col_widths(ws, [22, 22, 46])

        # ── 33. تحليل الاستدامة ESG ──────────────────────────────────────────
        ws = wb.create_sheet("تحليل الاستدامة ESG")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "تحليل الاستدامة والمخاطر المناخية — موسع")
        row = 3
        for k, v in [
            ("اكتمال مراجعة ESG",           "نعم" if adv.get("esg_completed") else _NA2),
            ("تأثير ESG على القيمة",         "استشاري — لا يؤثر تلقائياً"),
            ("تصنيف الاستدامة",              _NA2),
            ("خطر الفيضانات",                _NA2),
            ("كفاءة الطاقة",                 _NA2),
            ("شهادات الاستدامة",             _NA2),
            ("التأثير المقدر على القيمة (%)", _NA2),
            ("ملاحظة",                        "نتائج ESG استشارية — تتطلب تقرير بيئي متخصص"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [35, 38, 17])

        # ── 34. تقييم الأثر البيئي ───────────────────────────────────────────
        ws = wb.create_sheet("تقييم الأثر البيئي")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "تقييم الأثر البيئي — مبدئي")
        row = 3
        for k, v in [
            ("حالة التلوث البيئي",          _NA2),
            ("قرب المنشآت الخطرة",           _NA2),
            ("استخدامات المنطقة المحيطة",    req.get("property_address", _NA)),
            ("المخاطر البيئية الجيولوجية",   _NA2),
            ("التأثير على القيمة",            "لا أثر بيئي معلوم — يخضع للتحقق"),
            ("ملاحظة",                        "مبدئي — يتطلب تقرير بيئي متخصص للتأكيد"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [35, 38, 17])

        # ── 35. مؤشرات تكلفة البناء ──────────────────────────────────────────
        ws = wb.create_sheet("مؤشرات تكلفة البناء")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "مؤشرات تكلفة البناء السوقية — مبدئي")
        row = 3
        ws.cell(row=row, column=1, value="تصنيف البناء").font = _BOLD
        ws.cell(row=row, column=2, value="التكلفة (ريال/م²)").font = _BOLD
        ws.cell(row=row, column=3, value="المصدر").font = _BOLD
        row += 1
        for btype in ["اقتصادي", "متوسط", "فاخر", "فائق الجودة"]:
            ws.cell(row=row, column=1, value=btype).alignment = _RTL_ALIGN
            ws.cell(row=row, column=2, value=_NA2).fill = _WARN_FILL
            ws.cell(row=row, column=3,
                value="يحتاج بيانات سوق").alignment = _RTL_ALIGN
            row += 1
        _col_widths(ws, [25, 25, 40])

        # ── 36. مصفوفة المخاطر ───────────────────────────────────────────────
        ws = wb.create_sheet("مصفوفة المخاطر")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "مصفوفة تقييم مخاطر التقييم — مبدئي", 4)
        row = 3
        ws.cell(row=row, column=1, value="نوع المخاطرة").font = _BOLD
        ws.cell(row=row, column=2, value="الاحتمالية").font = _BOLD
        ws.cell(row=row, column=3, value="الأثر").font = _BOLD
        ws.cell(row=row, column=4, value="مستوى المخاطرة").font = _BOLD
        row += 1
        for risk, prob, impact, level in [
            ("مخاطر بيانات السوق",      "متوسط", "عالٍ",       "عالٍ"),
            ("مخاطر قانونية",           "منخفض", "عالٍ",       "متوسط"),
            ("مخاطر اقتصادية",          "متوسط", "عالٍ",       "عالٍ"),
            ("مخاطر بيئية",             "منخفض", "متوسط",      "منخفض"),
            ("مخاطر نزاعات ملكية",      "منخفض", "مرتفع جداً", "متوسط"),
        ]:
            ws.cell(row=row, column=1, value=risk).alignment = _RTL_ALIGN
            ws.cell(row=row, column=2, value=prob).alignment = _RTL_ALIGN
            ws.cell(row=row, column=3, value=impact).alignment = _RTL_ALIGN
            _lv = ws.cell(row=row, column=4, value=level)
            _lv.fill = _WARN_FILL if level == "عالٍ" else _OK_FILL
            row += 1
        _col_widths(ws, [30, 18, 18, 24])

        # ── 37. بيان الامتثال ────────────────────────────────────────────────
        ws = wb.create_sheet("بيان الامتثال")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "بيان الامتثال المهني — مبدئي")
        row = 3
        for k, v in [
            ("المعيار المهني المطبق",      "المعيار السعودي للتقييم العقاري"),
            ("إطار الامتثال",              "IVSC — المعايير الدولية للتقييم"),
            ("التقييم مستقل ومحايد",       "نعم — لا تضارب مصالح معلوم"),
            ("لا تعليمات تقييدية",         "نعم"),
            ("الاستخدام المقصود",          req.get("valuation_purpose", _NA)),
            ("المستخدم المقصود",           req.get("client_name", _NA)),
            ("حالة التوقيع",               "غير مكتمل — مبدئي"),
            ("ملاحظة",                     "هذا البيان مبدئي — يُستبدل بالنسخة المعتمدة"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [35, 38, 17])

        # ── 38. الإفصاحات المهنية ─────────────────────────────────────────────
        ws = wb.create_sheet("الإفصاحات المهنية")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "الإفصاحات المهنية — مبدئي")
        row = 3
        for k, v in [
            ("استقلالية المقيّم",          "نعم — لا علاقة مالية أو تجارية بالعقار"),
            ("مصادر البيانات",             "مصادر سوقية مراجعة — غير معتمدة نهائياً"),
            ("افتراضات البيانات",          "يُفترض صحة المستندات المقدمة"),
            ("تحفظات القيمة",              "النتائج مبدئية وقابلة للتعديل"),
            ("إفصاح QA",                   "قد تحتوي البيانات على محاكاة QA — داخلي فقط"),
            ("حدود الاستخدام",             "للاستخدام الداخلي فقط — لا يُقدم لجهات خارجية"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [35, 50])

        # ── 39. التوصية النهائية ──────────────────────────────────────────────
        ws = wb.create_sheet("التوصية النهائية")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "التوصية التقييمية — مبدئي")
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=3)
        c = ws.cell(row=2, column=1,
            value="توصية مبدئية — لا تُستخدم للأغراض الرسمية أو الائتمانية")
        c.fill = _WARN_FILL; c.font = _WARN_FONT; c.alignment = _CTR_ALIGN
        row = 4
        for k, v in [
            ("القيمة المشتقة من المقارنات",   _NA2),
            ("القيمة المشتقة من الدخل",        _NA2),
            ("القيمة المشتقة من التكلفة",      _NA2),
            ("القيمة المشتقة من DCF",           _NA2),
            ("القيمة المُوفَّقة المبدئية",      methods.get("reconciliation_value", _NA)),
            ("الموافقة المبدئية",               "نعم" if prelim.get("preliminary_approval_ready") else _NA2),
            ("القيمة الموصى بها",               prelim.get("preliminary_value", _NA2)),
            ("ثقة التوصية",                     "متوسطة — تتحسن باكتمال البيانات"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [35, 38, 17])

        # ── 40. اختبار اتساق الطرق ───────────────────────────────────────────
        ws = wb.create_sheet("اختبار اتساق الطرق")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "اختبار اتساق طرق التقييم — مبدئي", 4)
        row = 3
        ws.cell(row=row, column=1, value="الطريقة").font = _BOLD
        ws.cell(row=row, column=2, value="القيمة المؤشرة").font = _BOLD
        ws.cell(row=row, column=3, value="الانحراف عن المتوسط (%)").font = _BOLD
        ws.cell(row=row, column=4, value="الحالة").font = _BOLD
        row += 1
        _method_list = methods.get("methods", [])
        if _method_list:
            for m_row in _method_list:
                ws.cell(row=row, column=1,
                    value=_sv(m_row.get("method_type"))).alignment = _RTL_ALIGN
                ws.cell(row=row, column=2,
                    value=_sv(m_row.get("indicated_value"))).alignment = _RTL_ALIGN
                ws.cell(row=row, column=3, value=_NA2).fill = _WARN_FILL
                ws.cell(row=row, column=4,
                    value=_sv(m_row.get("status"))).alignment = _RTL_ALIGN
                row += 1
        else:
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
            _nc = ws.cell(row=row, column=1, value="لا طرق مُنجزة — يحتاج استكمال")
            _nc.fill = _WARN_FILL; _nc.font = _WARN_FONT; _nc.alignment = _CTR_ALIGN
        _col_widths(ws, [28, 25, 28, 18])

        # ── 41. حوكمة مصادر البيانات ─────────────────────────────────────────
        ws = wb.create_sheet("حوكمة مصادر البيانات")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "حوكمة وجودة مصادر البيانات")
        row = 3
        for k, v in [
            ("عدد المستندات المعتمدة",       _sv(ev_sum.get("approved_count", 0))),
            ("جاهزية المستندات الإلزامية",   "نعم" if ev_sum.get("mandatory_document_readiness") else "لا"),
            ("مصادر QA مستبعدة من الاعتماد", "نعم — مصادر QA لا تُعتمد في التقارير النهائية"),
            ("تصنيف المصادر",                "حكومية — سوقية — خبراء محليون"),
            ("حالة مراجعة المصادر",          "مبدئية — تخضع للتحقق"),
            ("آلية حوكمة البيانات",          "مراجعة الخبير + تقاطع مصادر متعددة"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [40, 42])

        # ── 42. خارطة طريق الاعتماد ──────────────────────────────────────────
        ws = wb.create_sheet("خارطة طريق الاعتماد")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "خارطة طريق الاعتماد — المتطلبات المتبقية", 3)
        row = 3
        ws.cell(row=row, column=1, value="المتطلب").font = _BOLD
        ws.cell(row=row, column=2, value="الحالة").font = _BOLD
        ws.cell(row=row, column=3, value="الأولوية").font = _BOLD
        row += 1
        _roadmap_items = (
            blockers[:15]
            if blockers
            else ["لا موانع معلومة — تحقق من اكتمال بيانات الطلب"]
        )
        for _blk in _roadmap_items:
            ws.cell(row=row, column=1, value=str(_blk)).alignment = _RTL_ALIGN
            ws.cell(row=row, column=1).fill = _WARN_FILL
            ws.cell(row=row, column=2, value="معلق").fill = _WARN_FILL
            ws.cell(row=row, column=3, value="عالية").fill = _WARN_FILL
            row += 1
        _col_widths(ws, [52, 18, 15])

        # ── 43. قائمة فحص الاعتماد ───────────────────────────────────────────
        ws = wb.create_sheet("قائمة فحص الاعتماد")
        ws.sheet_view.rightToLeft = True
        _hdr(ws, 1, "قائمة فحص بنود الاعتماد النهائي")
        row = 3
        ws.cell(row=row, column=1, value="بند الاعتماد").font = _BOLD
        ws.cell(row=row, column=2, value="الحالة").font = _BOLD
        row += 1
        _cert_items = [
            ("اكتمال الطرق",              gate.get("methods_completed", False)),
            ("اكتمال التسوية",             gate.get("reconciliation_completed", False)),
            ("جاهزية الموافقة المبدئية",   gate.get("preliminary_approval_ready", False)),
            ("جاهزية المستندات الإلزامية", ev_sum.get("mandatory_document_readiness", False)),
            ("جاهزية المصادر الإنتاجية",   gate.get("real_sources_ready", False)),
            ("جاهزية المقارنات",           gate.get("comparables_ready", False)),
            ("اكتمال HBU",                 adv.get("hbu_completed", False)),
            ("الفحص القانوني",             adv.get("legal_completed", False)),
            ("مراجعة ESG",                 adv.get("esg_completed", False)),
            ("تحليل SWOT",                 adv.get("swot_completed", False)),
        ]
        for _clabel, _cval in _cert_items:
            ws.cell(row=row, column=1, value=_clabel).font = _BOLD
            ws.cell(row=row, column=1).alignment = _RTL_ALIGN
            ws.cell(row=row, column=1).border = _THIN_BDR
            _bool_cell(ws, row, 2, bool(_cval))
            row += 1
        _col_widths(ws, [42, 20])

        # ── Apply output matrix: remove sheets not in active set ──────────────
        if _active_sheets is not None:
            for _sn in list(wb.sheetnames):
                if _sn not in _active_sheets:
                    del wb[_sn]

        wb.save(str(out_path))
        data   = out_path.read_bytes()
        sha256 = hashlib.sha256(data).hexdigest()
        return True, "", len(data), sha256

    except Exception as exc:
        return False, str(exc), 0, ""


# ── Route registration ─────────────────────────────────────────────────────────

def register_pv_preliminary_routes(app, require_auth) -> None:
    """Register all Phase H Addendum preliminary output routes on the Flask app."""
    from flask import g, jsonify, request as freq, send_file

    def _actor() -> str:
        return getattr(g, "user_id", None) or "system"

    def _check_id(request_id: str):
        if not _PVR_ID_RE.match(request_id):
            return jsonify({"ok": False, "error": "رقم الطلب غير صالح"}), 400
        return None

    def _prelim_gate(request_id: str):
        """Return (True, []) or (False, blockers_list)."""
        return _check_preliminary_readiness(request_id)

    # ── POST /preliminary-report ───────────────────────────────────────────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/preliminary-report",
        methods=["POST"],
    )
    @require_auth
    def pvp_generate_preliminary_report(request_id: str):
        err = _check_id(request_id)
        if err:
            return err

        allowed, blockers = _prelim_gate(request_id)
        if not allowed:
            return jsonify({
                "ok":        False,
                "error":     "بيانات التقييم غير كافية لإنشاء تقرير مبدئي",
                "blockers":  blockers,
                "advisory":  True,
            }), 422

        actor   = _actor()
        version = _output_version_for(request_id, "preliminary_pdf")
        rec     = _new_prelim_record(request_id, "preliminary_pdf", actor, version)
        rec["report_number"] = (
            f"PV-PRELIM-{datetime.utcnow().strftime('%Y%m%d')}-{rec['output_id'][-6:]}"
        )

        ctx = build_professional_valuation_preliminary_output_context(request_id)
        ctx["report_number"] = rec["report_number"]
        ctx["output_id"]     = rec["output_id"]
        ctx["output_type"]   = "preliminary_pdf"

        success, err_msg, size, sha = _generate_preliminary_pdf(ctx, request_id, rec["output_id"])

        if success:
            rec["output_status"]    = "generated"
            rec["file_available"]   = True
            rec["file_size_bytes"]  = size
            rec["file_hash_sha256"] = sha
            rec["internal_file_path"] = str(
                _PRELIM_OUT_DIR / request_id / f"{rec['output_id']}_preliminary_report.pdf"
            )
        else:
            rec["output_status"]       = "generation_failed"
            rec["generation_blockers"] = [f"PDF error: {err_msg[:300]}"]

        _append_registry(rec)
        _append_output_event(
            request_id, actor, "generate_preliminary_report",
            output_id=rec["output_id"],
            note=f"status={rec['output_status']} version={version}",
            metadata={"output_type": "preliminary_pdf", "success": success},
        )

        return jsonify({
            "ok":               True,
            "output":           _safe_output(rec),
            "generation_success": success,
            "generation_error":   err_msg if not success else None,
        }), 200

    # ── GET /preliminary-report ────────────────────────────────────────────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/preliminary-report",
        methods=["GET"],
    )
    @require_auth
    def pvp_download_preliminary_report(request_id: str):
        err = _check_id(request_id)
        if err:
            return err

        rec = _latest_active_of_type(request_id, "preliminary_pdf")
        if rec is None or not rec.get("file_available"):
            return jsonify({"ok": False, "error": "لا يوجد تقرير مبدئي متاح"}), 404

        fpath = Path(rec.get("internal_file_path", ""))
        if not fpath.exists():
            return jsonify({"ok": False, "error": "ملف التقرير المبدئي غير موجود"}), 404

        return send_file(
            str(fpath),
            as_attachment=True,
            download_name=f"preliminary_report_{request_id}.pdf",
            mimetype="application/pdf",
        )

    # ── POST /expert-draft-report ──────────────────────────────────────────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/expert-draft-report",
        methods=["POST"],
    )
    @require_auth
    def pvp_generate_expert_draft_report(request_id: str):
        err = _check_id(request_id)
        if err:
            return err

        allowed, blockers = _prelim_gate(request_id)
        if not allowed:
            return jsonify({
                "ok":        False,
                "error":     "بيانات التقييم غير كافية لإنشاء مسودة خبير",
                "blockers":  blockers,
                "advisory":  True,
            }), 422

        actor   = _actor()
        version = _output_version_for(request_id, "expert_draft_pdf")
        rec     = _new_prelim_record(request_id, "expert_draft_pdf", actor, version)
        rec["report_number"] = (
            f"PV-DRAFT-{datetime.utcnow().strftime('%Y%m%d')}-{rec['output_id'][-6:]}"
        )

        ctx = build_professional_valuation_preliminary_output_context(request_id)
        ctx["report_number"] = rec["report_number"]
        ctx["output_id"]     = rec["output_id"]
        ctx["output_type"]   = "expert_draft_pdf"

        success, err_msg, size, sha = _generate_expert_draft_pdf(ctx, request_id, rec["output_id"])

        if success:
            rec["output_status"]    = "generated"
            rec["file_available"]   = True
            rec["file_size_bytes"]  = size
            rec["file_hash_sha256"] = sha
            rec["internal_file_path"] = str(
                _PRELIM_OUT_DIR / request_id / f"{rec['output_id']}_expert_draft_report.pdf"
            )
        else:
            rec["output_status"]       = "generation_failed"
            rec["generation_blockers"] = [f"PDF error: {err_msg[:300]}"]

        _append_registry(rec)
        _append_output_event(
            request_id, actor, "generate_expert_draft_report",
            output_id=rec["output_id"],
            note=f"status={rec['output_status']} version={version}",
            metadata={"output_type": "expert_draft_pdf", "success": success},
        )

        return jsonify({
            "ok":               True,
            "output":           _safe_output(rec),
            "generation_success": success,
            "generation_error":   err_msg if not success else None,
        }), 200

    # ── GET /expert-draft-report ───────────────────────────────────────────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/expert-draft-report",
        methods=["GET"],
    )
    @require_auth
    def pvp_download_expert_draft_report(request_id: str):
        err = _check_id(request_id)
        if err:
            return err

        rec = _latest_active_of_type(request_id, "expert_draft_pdf")
        if rec is None or not rec.get("file_available"):
            return jsonify({"ok": False, "error": "لا توجد مسودة خبير متاحة"}), 404

        fpath = Path(rec.get("internal_file_path", ""))
        if not fpath.exists():
            return jsonify({"ok": False, "error": "ملف مسودة الخبير غير موجود"}), 404

        return send_file(
            str(fpath),
            as_attachment=True,
            download_name=f"expert_draft_report_{request_id}.pdf",
            mimetype="application/pdf",
        )

    # ── POST /expert-workbook ──────────────────────────────────────────────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/expert-workbook",
        methods=["POST"],
    )
    @require_auth
    def pvp_generate_expert_workbook(request_id: str):
        err = _check_id(request_id)
        if err:
            return err

        allowed, blockers = _prelim_gate(request_id)
        if not allowed:
            return jsonify({
                "ok":        False,
                "error":     "بيانات التقييم غير كافية لإنشاء ملف Excel الخبير",
                "blockers":  blockers,
                "advisory":  True,
            }), 422

        actor   = _actor()
        version = _output_version_for(request_id, "expert_workbook")
        rec     = _new_prelim_record(request_id, "expert_workbook", actor, version)
        rec["report_number"] = (
            f"PV-EWB-{datetime.utcnow().strftime('%Y%m%d')}-{rec['output_id'][-6:]}"
        )

        ctx = build_professional_valuation_preliminary_output_context(request_id)
        ctx["report_number"] = rec["report_number"]
        ctx["output_id"]     = rec["output_id"]
        ctx["output_type"]   = "expert_workbook"

        success, err_msg, size, sha = _generate_expert_workbook(ctx, request_id, rec["output_id"])

        if success:
            rec["output_status"]    = "generated"
            rec["file_available"]   = True
            rec["file_size_bytes"]  = size
            rec["file_hash_sha256"] = sha
            rec["internal_file_path"] = str(
                _PRELIM_OUT_DIR / request_id / f"{rec['output_id']}_expert_workbook.xlsx"
            )
        else:
            rec["output_status"]       = "generation_failed"
            rec["generation_blockers"] = [f"Workbook error: {err_msg[:300]}"]

        _append_registry(rec)
        _append_output_event(
            request_id, actor, "generate_expert_workbook",
            output_id=rec["output_id"],
            note=f"status={rec['output_status']} version={version}",
            metadata={"output_type": "expert_workbook", "success": success},
        )

        return jsonify({
            "ok":               True,
            "output":           _safe_output(rec),
            "generation_success": success,
            "generation_error":   err_msg if not success else None,
        }), 200

    # ── GET /expert-workbook ───────────────────────────────────────────────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/expert-workbook",
        methods=["GET"],
    )
    @require_auth
    def pvp_download_expert_workbook(request_id: str):
        err = _check_id(request_id)
        if err:
            return err

        rec = _latest_active_of_type(request_id, "expert_workbook")
        if rec is None or not rec.get("file_available"):
            return jsonify({"ok": False, "error": "لا يوجد ملف Excel الخبير متاح"}), 404

        fpath = Path(rec.get("internal_file_path", ""))
        if not fpath.exists():
            return jsonify({"ok": False, "error": "ملف Excel الخبير غير موجود"}), 404

        return send_file(
            str(fpath),
            as_attachment=True,
            download_name=f"expert_workbook_{request_id}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
