# -*- coding: utf-8 -*-
"""
professional_valuation_outputs.py — Phase H: Protected Certified PDF & Final Workbook.

Endpoints (all JWT-protected):
  POST /api/professional-valuation/requests/<id>/certified-report
  GET  /api/professional-valuation/requests/<id>/certified-report
  POST /api/professional-valuation/requests/<id>/final-workbook
  GET  /api/professional-valuation/requests/<id>/final-workbook
  GET  /api/professional-valuation/requests/<id>/outputs
  GET  /api/professional-valuation/requests/<id>/outputs/<output_id>
  POST /api/professional-valuation/requests/<id>/outputs/<output_id>/revoke

Storage (internal paths NEVER exposed in API responses):
  instance/professional_valuation/certified_outputs/<request_id>/<output_id>_certified_report.pdf
  instance/professional_valuation/certified_outputs/<request_id>/<output_id>_final_workbook.xlsx
  instance/professional_valuation/output_registry/<request_id>.jsonl
  instance/professional_valuation/output_events/<request_id>.jsonl

Strict rules:
  - No certified output generated unless certification_ready=True.
  - No FPDF. PDF via HTML/Playwright (pdf_renderer).
  - Workbook via openpyxl.
  - internal_file_path never returned in API responses.
  - No OCR, no Qdrant, no RAG, no external APIs.
  - No fabricated signatures, stamps, reviewers, data, or legal references.
  - QA simulation data excluded from certified outputs.
  - Phase H only — prior phase routes (B–G) unmodified.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime
from pathlib import Path

# ── Storage paths ──────────────────────────────────────────────────────────────

_BASE     = Path(__file__).parent / "instance" / "professional_valuation"
_OUT_DIR  = _BASE / "certified_outputs"
_REG_DIR  = _BASE / "output_registry"
_EV_DIR   = _BASE / "output_events"
_GATE_DIR = _BASE / "certification_gate"          # Phase G snapshot dir
_TMPL_DIR = Path(__file__).parent / "templates" / "pdf"

for _d in (_OUT_DIR, _REG_DIR, _EV_DIR, _GATE_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── ID helpers ─────────────────────────────────────────────────────────────────

_PVR_ID_RE = re.compile(r"^PVR-\d{8}-[0-9A-F]{4}$")


def _new_pvout_id() -> str:
    return "PVOUT-" + uuid.uuid4().hex[:8].upper()


def _new_pvoutevent_id() -> str:
    return "PVOUTEVENT-" + uuid.uuid4().hex[:8].upper()


# ── Output types / statuses ────────────────────────────────────────────────────

_OUTPUT_TYPES    = frozenset({"certified_pdf", "final_workbook"})
_OUTPUT_STATUSES = frozenset({"generated", "superseded", "revoked", "generation_failed"})

# ── Keys excluded from API responses ──────────────────────────────────────────

_PRIVATE_KEYS = frozenset({"internal_file_path"})


# ── Default output record ──────────────────────────────────────────────────────

def _new_output_record(
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
        "certification_gate_snapshot": {},
        "peer_review_snapshot":        {},
        "signature_snapshot":          {},
        "method_run_id":               None,
        "reconciliation_id":           None,
        "preliminary_approval_id":     None,
        "advanced_review_snapshot_id": None,
        "file_available":              False,
        "file_size_bytes":             None,
        "file_hash_sha256":            None,
        "safe_download_token":         uuid.uuid4().hex,
        "internal_file_path":          None,   # never exposed in API
        "public_metadata":             {},
        "official_use_allowed":        False,
        "certified_use_allowed":       False,
        "generation_blockers":         [],
        "warnings":                    [],
        "external_api_used":           False,
        "qdrant_used":                 False,
        "rag_used":                    False,
    }


def _safe_output(rec: dict) -> dict:
    """Return output record safe for API (excludes internal_file_path)."""
    return {k: v for k, v in rec.items() if k not in _PRIVATE_KEYS}


# ── Output registry (JSONL per request) ───────────────────────────────────────

def _append_registry(rec: dict) -> None:
    path = _REG_DIR / f"{rec['request_id']}.jsonl"
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _read_registry(request_id: str) -> list[dict]:
    path = _REG_DIR / f"{request_id}.jsonl"
    if not path.exists():
        return []
    records: list[dict] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if raw:
            try:
                records.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    return records


def _read_output_by_id(request_id: str, output_id: str) -> dict | None:
    for rec in _read_registry(request_id):
        if rec.get("output_id") == output_id:
            return rec
    return None


def _latest_active_of_type(request_id: str, output_type: str) -> dict | None:
    matches = [
        r for r in _read_registry(request_id)
        if r.get("output_type") == output_type
        and r.get("output_status") not in ("revoked", "superseded")
    ]
    return matches[-1] if matches else None


def _output_version_for(request_id: str, output_type: str) -> int:
    existing = [
        r for r in _read_registry(request_id)
        if r.get("output_type") == output_type
    ]
    return len(existing) + 1


# ── Output event log (JSONL per request) ──────────────────────────────────────

def _append_output_event(
    request_id: str,
    actor: str,
    action: str,
    output_id: str = "",
    note: str = "",
    metadata: dict | None = None,
) -> None:
    event = {
        "event_id":   _new_pvoutevent_id(),
        "request_id": request_id,
        "timestamp":  datetime.utcnow().isoformat(),
        "actor":      actor,
        "action":     action,
        "output_id":  output_id,
        "note":       note,
        "metadata":   metadata or {},
    }
    path = _EV_DIR / f"{request_id}.jsonl"
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


def read_output_events(request_id: str) -> list[dict]:
    """Public helper for test assertions."""
    path = _EV_DIR / f"{request_id}.jsonl"
    if not path.exists():
        return []
    events: list[dict] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if raw:
            try:
                events.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    return events


# ── Gate snapshot reader ───────────────────────────────────────────────────────

def _load_gate_snapshot(request_id: str) -> dict:
    """Read Phase G certification gate snapshot; recompute if absent."""
    snap_path = _GATE_DIR / f"{request_id}.json"
    if snap_path.exists():
        try:
            return json.loads(snap_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    try:
        from professional_valuation_certification import compute_final_certification_gate
        return compute_final_certification_gate(request_id)
    except ImportError:
        return {
            "certification_ready":               False,
            "official_use_allowed":              False,
            "certified_use_allowed":             False,
            "final_report_generation_allowed":   False,
            "final_workbook_generation_allowed": False,
            "blockers": ["وحدة بوابة الاعتماد غير متاحة"],
            "evaluated_at": datetime.utcnow().isoformat(),
        }


# ── Output context assembler ───────────────────────────────────────────────────

def build_professional_valuation_output_context(request_id: str) -> dict:
    """Assemble certified output context from all Professional Valuation phases.

    Imports each phase module via try/except to remain safe if any module is
    unavailable.  Internal file paths are never included.
    QA simulation data is excluded from certified context.
    """
    NA = "غير متاح"
    ctx: dict = {
        "request_id":     request_id,
        "assembled_at":   datetime.utcnow().isoformat(),
        "context_type":   "professional_valuation_certified_output",
        "external_api_used": False,
        "qdrant_used":       False,
        "rag_used":          False,
    }

    # ── Request summary ───────────────────────────────────────────────────────
    req_summary: dict = {
        "request_id":        request_id,
        "request_number":    NA,
        "client_name":       NA,
        "client_type":       NA,
        "property_title":    NA,
        "property_address":  NA,
        "property_type":     NA,
        "valuation_purpose": NA,
        "basis_of_value":    NA,
        "valuation_date":    NA,
        "inspection_date":   NA,
        "currency":          "SAR",
        "report_language":   "ar",
    }
    try:
        from professional_valuation_routes import _read_pvr as _pvr_read
        pvr = _pvr_read(request_id)
        if pvr:
            req_summary.update({
                "request_number":    pvr.get("request_number") or request_id,
                "client_name":       pvr.get("client_name") or NA,
                "client_type":       pvr.get("client_type") or NA,
                "property_title":    pvr.get("property_title") or NA,
                "property_address":  pvr.get("property_address") or NA,
                "property_type":     pvr.get("property_type") or NA,
                "valuation_purpose": pvr.get("valuation_purpose") or NA,
                "basis_of_value":    pvr.get("basis_of_value") or NA,
                "valuation_date":    pvr.get("valuation_date") or NA,
                "inspection_date":   pvr.get("inspection_date") or NA,
                "currency":          pvr.get("currency") or "SAR",
                "report_language":   pvr.get("report_language") or "ar",
            })
    except (ImportError, Exception):
        pass
    ctx["request_summary"] = req_summary

    # ── Certification gate ────────────────────────────────────────────────────
    gate = _load_gate_snapshot(request_id)
    ctx["certification_gate"] = {
        "certification_ready":               gate.get("certification_ready", False),
        "official_use_allowed":              gate.get("official_use_allowed", False),
        "certified_use_allowed":             gate.get("certified_use_allowed", False),
        "final_report_generation_allowed":   gate.get("final_report_generation_allowed", False),
        "final_workbook_generation_allowed": gate.get("final_workbook_generation_allowed", False),
        "blockers":                          gate.get("blockers", []),
        "evaluated_at":                      gate.get("evaluated_at", NA),
        "certification_status":              gate.get("certification_status", NA),
    }

    # ── Evidence summary (no internal paths) ──────────────────────────────────
    evidence_summary: dict = {
        "mandatory_document_readiness": False,
        "approved_count":               0,
        "missing_categories":           [],
        "qa_excluded":                  True,
        "note": "مستندات معتمدة فقط — لا مسارات ملفات داخلية — بيانات QA مستبعدة",
    }
    try:
        from professional_valuation_evidence_routes import compute_gate_summary as _cev_gate
        eg = _cev_gate(request_id, gate.get("valuation_purpose", ""))
        evidence_summary.update({
            "mandatory_document_readiness": bool(eg.get("mandatory_documents_ready")),
            "approved_count":               int(eg.get("approved_count", 0)),
            "missing_categories":           eg.get("missing_categories", []),
            "qa_cleared":                   bool(eg.get("qa_data_cleared")),
        })
    except (ImportError, Exception):
        pass
    ctx["evidence_summary"] = evidence_summary

    # ── Source summary ────────────────────────────────────────────────────────
    source_summary: dict = {
        "production_ready_count": 0,
        "qa_cleared":             False,
        "qa_sources_excluded":    True,
        "note": "مصادر إنتاجية معتمدة فقط — بيانات محاكاة QA مستبعدة",
    }
    try:
        from professional_valuation_evidence_routes import compute_gate_summary as _src_gate
        sg = _src_gate(request_id, "")
        source_summary.update({
            "production_ready_count": int(sg.get("production_source_count", 0)),
            "qa_cleared":             bool(sg.get("qa_data_cleared")),
        })
    except (ImportError, Exception):
        pass
    ctx["source_summary"] = source_summary

    # ── Comparable summary ────────────────────────────────────────────────────
    comparable_summary: dict = {
        "production_ready_count":         0,
        "certification_comparable_ready": False,
        "excluded_staged_rejected":       True,
        "excluded_qa":                    True,
        "note": "مقارنات إنتاجية معتمدة فقط — مقارنات مرفوضة/مؤقتة/QA مستبعدة",
    }
    try:
        from professional_valuation_comparables import evaluate_comparable_readiness
        cr = evaluate_comparable_readiness(request_id, "")
        comparable_summary.update({
            "production_ready_count":         int(cr.get("production_ready_count", 0)),
            "certification_comparable_ready": bool(cr.get("certification_comparable_ready")),
        })
    except (ImportError, Exception):
        pass
    ctx["comparable_summary"] = comparable_summary

    # ── Method analysis ───────────────────────────────────────────────────────
    method_summary: dict = {
        "methods_completed":  False,
        "readiness_status":   NA,
        "method_outputs":     {},
        "limitations":        [],
    }
    try:
        from professional_valuation_methods import evaluate_method_readiness_for_request
        mr = evaluate_method_readiness_for_request(request_id)
        method_summary.update({
            "methods_completed": bool(mr.get("methods_completed")),
            "readiness_status":  str(mr.get("readiness_status", NA)),
            "method_outputs":    {
                k: v for k, v in mr.items()
                if k not in ("methods_completed", "readiness_status")
            },
        })
    except (ImportError, Exception):
        pass
    ctx["method_summary"] = method_summary

    # ── Reconciliation ────────────────────────────────────────────────────────
    recon_summary: dict = {
        "weighted_value":       None,
        "selected_final_value": None,
        "rationale":            NA,
        "method_weights":       {},
        "divergence_warnings":  [],
    }
    try:
        from professional_valuation_methods import get_reconciliation_for_request
        recon = get_reconciliation_for_request(request_id)
        if recon:
            recon_summary.update({
                "weighted_value":       recon.get("weighted_value"),
                "selected_final_value": recon.get("final_value") or recon.get("weighted_value"),
                "rationale":            recon.get("rationale") or NA,
                "method_weights":       recon.get("method_weights") or {},
            })
    except (ImportError, Exception):
        pass
    ctx["reconciliation_summary"] = recon_summary

    # ── Preliminary approval ──────────────────────────────────────────────────
    prelim_summary: dict = {
        "preliminary_approval_ready": False,
        "preliminary_use_allowed":    False,
        "approved_at":                NA,
    }
    try:
        from professional_valuation_methods import get_preliminary_approval_for_request
        prelim = get_preliminary_approval_for_request(request_id)
        if prelim:
            prelim_summary.update({
                "preliminary_approval_ready": bool(prelim.get("preliminary_approval_ready")),
                "preliminary_use_allowed":    bool(prelim.get("preliminary_use_allowed")),
                "approved_at":                prelim.get("approved_at") or NA,
            })
    except (ImportError, Exception):
        pass
    ctx["preliminary_approval"] = prelim_summary

    # ── Advanced reviews (HBU / Legal / ESG / SWOT) ──────────────────────────
    adv_summary: dict = {
        "hbu":  {"completed": False, "approved_for_preliminary": False, "status": "not_started"},
        "legal":{"completed": False, "approved_for_preliminary": False, "status": "not_started"},
        "esg":  {"completed": False, "approved_for_preliminary": False, "status": "not_started"},
        "swot": {"completed": False, "approved_for_preliminary": False, "status": "not_started"},
        "all_prelim_ready":          False,
        "all_cert_ready":            False,
        "approved_for_certification": False,  # always False in Phases F–G
        "certification_limitation": (
            "مراجعات الخبراء (HBU/قانوني/ESG/SWOT) معتمدة للاستخدام المبدئي الداخلي — "
            "الاعتماد النهائي يتطلب اكتمال جميع بوابات الفازات C–G."
        ),
    }
    try:
        from professional_valuation_advanced_review import (
            _load_advanced_review as _load_adv_rec,
            get_advanced_review_gate_fragment,
        )
        adv_rec  = _load_adv_rec(request_id)
        adv_gate = get_advanced_review_gate_fragment(request_id)
        for _key, _sec in (
            ("hbu",   "hbu_review"),
            ("legal", "legal_review"),
            ("esg",   "esg_review"),
            ("swot",  "swot_review"),
        ):
            sec_data = adv_rec.get(_sec, {})
            adv_summary[_key] = {
                "completed":               bool(sec_data.get("completed")),
                "approved_for_preliminary": bool(sec_data.get("approved_for_preliminary")),
                "status":                  sec_data.get("status", "not_started"),
                "approved_for_certification": False,
            }
        adv_summary["all_prelim_ready"] = bool(adv_gate.get("advanced_reviews_prelim_ready"))
        adv_summary["all_cert_ready"]   = False
    except (ImportError, Exception):
        pass
    ctx["advanced_reviews"] = adv_summary

    # ── Peer review ───────────────────────────────────────────────────────────
    peer_summary: dict = {
        "reviewer_name":      NA,
        "reviewer_role":      NA,
        "reviewer_license":   NA,
        "review_decision":    NA,
        "review_date":        NA,
        "reviewed_sections":  [],
        "peer_review_ready":  False,
        "review_notes_summary": NA,
        # expert_only_notes intentionally excluded from output context
    }
    try:
        from professional_valuation_certification import (
            _load_peer_review as _lpeer,
            _compute_peer_review_readiness as _cpeerrf,
        )
        pr_rec = _lpeer(request_id)
        prf    = _cpeerrf(pr_rec)
        peer_summary.update({
            "reviewer_name":     pr_rec.get("assigned_reviewer_name") or NA,
            "reviewer_role":     pr_rec.get("assigned_reviewer_role") or NA,
            "reviewer_license":  pr_rec.get("assigned_reviewer_license") or NA,
            "review_decision":   pr_rec.get("review_decision") or NA,
            "review_date":       pr_rec.get("review_completed_at") or NA,
            "reviewed_sections": pr_rec.get("reviewed_sections") or [],
            "peer_review_ready": prf.get("peer_review_ready", False),
            "review_notes_summary": (
                (pr_rec.get("review_notes") or NA)[:500]
            ),
        })
    except (ImportError, Exception):
        pass
    ctx["peer_review_summary"] = peer_summary

    # ── Expert signature ──────────────────────────────────────────────────────
    sig_summary: dict = {
        "expert_name":         NA,
        "expert_role":         NA,
        "expert_license":      NA,
        "firm_name":           NA,
        "signed_at":           NA,
        "signature_available": False,
        "stamp_available":     False,
        "approval_statement":  NA,
        "final_signoff_ready": False,
        "note": "لا صورة توقيع أو ختم — بيانات وصفية فقط",
    }
    try:
        from professional_valuation_certification import (
            _load_signature as _lsig,
            _compute_signature_readiness as _csigrf,
        )
        sig_rec = _lsig(request_id)
        srf     = _csigrf(sig_rec)
        sig_summary.update({
            "expert_name":         sig_rec.get("expert_name") or NA,
            "expert_role":         sig_rec.get("expert_role") or NA,
            "expert_license":      sig_rec.get("expert_license_number") or NA,
            "firm_name":           sig_rec.get("firm_name") or NA,
            "signed_at":           sig_rec.get("signed_at") or NA,
            "signature_available": bool(sig_rec.get("signature_available")),
            "stamp_available":     bool(sig_rec.get("stamp_available")),
            "approval_statement":  sig_rec.get("approval_statement") or NA,
            "final_signoff_ready": srf.get("final_signoff_ready", False),
        })
    except (ImportError, Exception):
        pass
    ctx["signature_summary"] = sig_summary

    return ctx


# ── PDF generation ─────────────────────────────────────────────────────────────

def _generate_certified_pdf(ctx: dict, request_id: str, output_id: str) -> tuple[bool, str, int, str]:
    """Generate certified PDF from output context.

    Returns (success, error_message, file_size_bytes, sha256_hex).
    Does NOT raise; always returns a result tuple.
    Path is stored in output record internal_file_path — never in API response.
    """
    req_dir = _OUT_DIR / request_id
    req_dir.mkdir(parents=True, exist_ok=True)
    out_path = req_dir / f"{output_id}_certified_report.pdf"

    try:
        import html as _html
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        from pdf_renderer import cairo_font_css, render_pdf_from_html

        def _e(v) -> str:
            if v is None:
                return "غير متاح"
            s = str(v)
            return _html.escape(s) if s else "غير متاح"

        def _ev(v, fallback: str = "غير متاح") -> str:
            if v is None or str(v).strip() in ("", "None", "null"):
                return fallback
            return _html.escape(str(v))

        env = Environment(
            loader=FileSystemLoader(str(_TMPL_DIR)),
            autoescape=select_autoescape(["html"]),
        )
        env.globals["e"]  = _e
        env.globals["ev"] = _ev

        tmpl = env.get_template("professional_valuation_certified_report.html")
        html_str = tmpl.render(
            ctx=ctx,
            font_css_block=cairo_font_css(),
            generated_at=ctx.get("assembled_at", ""),
        )

        pdf_bytes = render_pdf_from_html(html_str)
        out_path.write_bytes(pdf_bytes)

        sha256 = hashlib.sha256(pdf_bytes).hexdigest()
        return True, "", len(pdf_bytes), sha256

    except Exception as exc:
        return False, str(exc), 0, ""


# ── Workbook generation ────────────────────────────────────────────────────────

_SHEETS = [
    "غلاف التقرير",
    "ملخص الاعتماد",
    "نطاق العمل",
    "بيانات العقار",
    "المستندات المعتمدة",
    "مصادر البيانات",
    "المقارنات المعتمدة",
    "تحليل الطرق",
    "التوفيق النهائي",
    "تحليل HBU",
    "الفحص القانوني",
    "ESG والمخاطر المناخية",
    "تحليل SWOT",
    "مراجعة النظراء",
    "توقيع واعتماد الخبير",
    "سجل التدقيق",
    "موانع الاعتماد السابقة",
    "المخرجات والنسخ",
]

_NA = "غير متاح"
_NA2 = "غير منطبق"


def _generate_final_workbook(ctx: dict, request_id: str, output_id: str) -> tuple[bool, str, int, str]:
    """Generate certified XLSX workbook from output context.

    Returns (success, error_message, file_size_bytes, sha256_hex).
    Does NOT raise; always returns a result tuple.
    """
    req_dir = _OUT_DIR / request_id
    req_dir.mkdir(parents=True, exist_ok=True)
    out_path = req_dir / f"{output_id}_final_workbook.xlsx"

    try:
        import openpyxl
        from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
        from openpyxl.utils import get_column_letter

        wb = openpyxl.Workbook()
        # Remove default sheet
        if wb.active and wb.active.title == "Sheet":
            wb.remove(wb.active)

        # ── Style helpers ─────────────────────────────────────────────────────
        _HDR_FILL  = PatternFill("solid", fgColor="1F4E78")
        _SEC_FILL  = PatternFill("solid", fgColor="2D6A9F")
        _ALT_FILL  = PatternFill("solid", fgColor="EBF3FB")
        _WARN_FILL = PatternFill("solid", fgColor="FFF3CD")
        _OK_FILL   = PatternFill("solid", fgColor="D4EDDA")
        _NA_FILL   = PatternFill("solid", fgColor="F8F9FA")

        _HDR_FONT  = Font(bold=True, color="FFFFFF", name="Calibri")
        _SEC_FONT  = Font(bold=True, color="FFFFFF", name="Calibri")
        _BOLD      = Font(bold=True, name="Calibri")
        _REG       = Font(name="Calibri")
        _RTL_ALIGN = Alignment(horizontal="right", vertical="center", wrap_text=True, readingOrder=2)
        _CTR_ALIGN = Alignment(horizontal="center", vertical="center")
        _THIN_SIDE = Side(border_style="thin", color="CCCCCC")
        _THIN_BDR  = Border(left=_THIN_SIDE, right=_THIN_SIDE, top=_THIN_SIDE, bottom=_THIN_SIDE)

        def _hdr_row(ws, row: int, text: str, cols: int = 4) -> None:
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=cols)
            cell = ws.cell(row=row, column=1, value=text)
            cell.font   = _HDR_FONT
            cell.fill   = _HDR_FILL
            cell.alignment = _CTR_ALIGN

        def _kv(ws, row: int, key: str, value) -> None:
            v = _NA if (value is None or str(value).strip() in ("", "None", "null", "غير متاح")) else str(value)
            ck = ws.cell(row=row, column=1, value=key)
            cv = ws.cell(row=row, column=2, value=v)
            ck.font  = _BOLD;  ck.alignment = _RTL_ALIGN; ck.border = _THIN_BDR
            cv.font  = _REG;   cv.alignment = _RTL_ALIGN; cv.border = _THIN_BDR
            if v == _NA:
                cv.fill = _NA_FILL

        def _bool_cell(ws, row: int, col: int, val: bool) -> None:
            text = "نعم ✓" if val else "لا ✗"
            cell = ws.cell(row=row, column=col, value=text)
            cell.font      = _BOLD
            cell.fill      = _OK_FILL if val else _WARN_FILL
            cell.alignment = _CTR_ALIGN
            cell.border    = _THIN_BDR

        def _col_widths(ws, widths: list[int]) -> None:
            for i, w in enumerate(widths, 1):
                ws.column_dimensions[get_column_letter(i)].width = w

        # ── 1. غلاف التقرير ──────────────────────────────────────────────────
        ws = wb.create_sheet("غلاف التقرير")
        ws.sheet_view.rightToLeft = True
        req = ctx.get("request_summary", {})
        gate = ctx.get("certification_gate", {})

        _hdr_row(ws, 1, "تقرير التقييم العقاري المهني المعتمد", 4)
        _hdr_row(ws, 2, "Professional Certified Valuation Report", 4)
        row = 4
        for k, v in [
            ("رقم التقرير", ctx.get("report_number", _NA)),
            ("رقم الطلب", req.get("request_id", _NA)),
            ("اسم العميل", req.get("client_name", _NA)),
            ("نوع العميل", req.get("client_type", _NA)),
            ("عنوان العقار", req.get("property_address", _NA)),
            ("نوع العقار", req.get("property_type", _NA)),
            ("غرض التقييم", req.get("valuation_purpose", _NA)),
            ("أساس القيمة", req.get("basis_of_value", _NA)),
            ("تاريخ التقييم", req.get("valuation_date", _NA)),
            ("تاريخ المعاينة", req.get("inspection_date", _NA)),
            ("العملة", req.get("currency", "SAR")),
            ("تاريخ إنشاء التقرير", ctx.get("assembled_at", _NA)[:10] if ctx.get("assembled_at") else _NA),
            ("حالة الاعتماد", "معتمد" if gate.get("certification_ready") else "غير معتمد"),
        ]:
            _kv(ws, row, k, v)
            row += 1
        _col_widths(ws, [28, 40, 20, 20])

        # ── 2. ملخص الاعتماد ─────────────────────────────────────────────────
        ws = wb.create_sheet("ملخص الاعتماد")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "ملخص بوابة الاعتماد النهائية", 4)
        row = 3
        ws.cell(row=row, column=1, value="بند الاعتماد").font = _BOLD
        ws.cell(row=row, column=2, value="الحالة").font       = _BOLD
        row += 1
        for k, v in [
            ("جاهزية الاعتماد",           gate.get("certification_ready", False)),
            ("مسموح بالاستخدام الرسمي",   gate.get("official_use_allowed", False)),
            ("مسموح بالاستخدام المعتمد",  gate.get("certified_use_allowed", False)),
            ("مسموح بتوليد التقرير",       gate.get("final_report_generation_allowed", False)),
            ("مسموح بتوليد الملف",         gate.get("final_workbook_generation_allowed", False)),
        ]:
            ws.cell(row=row, column=1, value=k).font = _BOLD
            _bool_cell(ws, row, 2, v)
            row += 1
        row += 1
        ws.cell(row=row, column=1, value="تاريخ تقييم البوابة").font = _BOLD
        ws.cell(row=row, column=2, value=gate.get("evaluated_at", _NA)[:19] if gate.get("evaluated_at") else _NA)
        row += 1
        blockers = gate.get("blockers", [])
        if blockers:
            ws.cell(row=row, column=1, value="الموانع المتبقية").font = _BOLD
            row += 1
            for b in blockers:
                ws.cell(row=row, column=1, value=b).fill = _WARN_FILL
                row += 1
        _col_widths(ws, [40, 20, 20, 20])

        # ── 3. نطاق العمل ────────────────────────────────────────────────────
        ws = wb.create_sheet("نطاق العمل")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "نطاق العمل والقيود", 4)
        row = 3
        sig = ctx.get("signature_summary", {})
        for k, v in [
            ("الغرض المقصود",       req.get("valuation_purpose", _NA)),
            ("المستخدمون المقصودون", req.get("client_type", _NA)),
            ("مصلحة العقار",        req.get("basis_of_value", _NA)),
            ("تاريخ المعاينة",      req.get("inspection_date", _NA)),
            ("نطاق التوقيع",        sig.get("approval_statement", _NA)),
            ("القيود",               sig.get("note", _NA2)),
        ]:
            _kv(ws, row, k, v)
            row += 1
        _col_widths(ws, [30, 50])

        # ── 4. بيانات العقار ─────────────────────────────────────────────────
        ws = wb.create_sheet("بيانات العقار")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "بيانات العقار", 4)
        row = 3
        for k, v in [
            ("عنوان العقار",  req.get("property_address", _NA)),
            ("نوع العقار",    req.get("property_type", _NA)),
            ("عنوان الطلب",  req.get("property_title", _NA)),
            ("لغة التقرير",   req.get("report_language", "ar")),
        ]:
            _kv(ws, row, k, v)
            row += 1
        _col_widths(ws, [30, 50])

        # ── 5. المستندات المعتمدة ─────────────────────────────────────────────
        ws = wb.create_sheet("المستندات المعتمدة")
        ws.sheet_view.rightToLeft = True
        ev = ctx.get("evidence_summary", {})
        _hdr_row(ws, 1, "المستندات المعتمدة", 4)
        row = 3
        for k, v in [
            ("جاهزية المستندات الإلزامية", "نعم" if ev.get("mandatory_document_readiness") else "لا"),
            ("عدد المستندات المعتمدة",      str(ev.get("approved_count", 0))),
            ("بيانات QA مستبعدة",           "نعم"),
        ]:
            _kv(ws, row, k, v)
            row += 1
        missing = ev.get("missing_categories", [])
        if missing:
            row += 1
            ws.cell(row=row, column=1, value="الفئات المفقودة").font = _BOLD
            row += 1
            for m in missing:
                ws.cell(row=row, column=1, value=str(m)).fill = _WARN_FILL
                row += 1
        else:
            row += 1
            ws.cell(row=row, column=1, value="لا توجد فئات مفقودة").fill = _OK_FILL
        _col_widths(ws, [35, 35])

        # ── 6. مصادر البيانات ────────────────────────────────────────────────
        ws = wb.create_sheet("مصادر البيانات")
        ws.sheet_view.rightToLeft = True
        src = ctx.get("source_summary", {})
        _hdr_row(ws, 1, "مصادر البيانات الإنتاجية", 4)
        row = 3
        for k, v in [
            ("عدد المصادر الإنتاجية",  str(src.get("production_ready_count", 0))),
            ("بيانات QA مُعالَجة",      "نعم" if src.get("qa_cleared") else "لا"),
            ("مصادر QA مستبعدة",        "نعم"),
        ]:
            _kv(ws, row, k, v)
            row += 1
        _col_widths(ws, [35, 35])

        # ── 7. المقارنات المعتمدة ─────────────────────────────────────────────
        ws = wb.create_sheet("المقارنات المعتمدة")
        ws.sheet_view.rightToLeft = True
        comp = ctx.get("comparable_summary", {})
        _hdr_row(ws, 1, "المقارنات الإنتاجية المعتمدة", 4)
        row = 3
        for k, v in [
            ("عدد المقارنات الإنتاجية",      str(comp.get("production_ready_count", 0))),
            ("جاهزية المقارنات للاعتماد",     "نعم" if comp.get("certification_comparable_ready") else "لا"),
            ("المقارنات المرفوضة/المؤقتة/QA", "مستبعدة"),
        ]:
            _kv(ws, row, k, v)
            row += 1
        row += 1
        ws.cell(row=row, column=1, value=comp.get("note", _NA2)).fill = _ALT_FILL
        _col_widths(ws, [40, 30])

        # ── 8. تحليل الطرق ───────────────────────────────────────────────────
        ws = wb.create_sheet("تحليل الطرق")
        ws.sheet_view.rightToLeft = True
        mth = ctx.get("method_summary", {})
        _hdr_row(ws, 1, "تحليل طرق التقييم", 4)
        row = 3
        for k, v in [
            ("اكتمال طرق التقييم", "نعم" if mth.get("methods_completed") else "لا"),
            ("حالة الجاهزية",       mth.get("readiness_status", _NA)),
        ]:
            _kv(ws, row, k, v)
            row += 1
        method_outputs = mth.get("method_outputs", {})
        if method_outputs:
            row += 1
            ws.cell(row=row, column=1, value="مخرجات الطرق").font = _BOLD
            row += 1
            for k, v in method_outputs.items():
                if not isinstance(v, dict):
                    _kv(ws, row, str(k), str(v))
                    row += 1
        _col_widths(ws, [35, 35])

        # ── 9. التوفيق النهائي ────────────────────────────────────────────────
        ws = wb.create_sheet("التوفيق النهائي")
        ws.sheet_view.rightToLeft = True
        recon = ctx.get("reconciliation_summary", {})
        _hdr_row(ws, 1, "التوفيق النهائي للقيمة", 4)
        row = 3
        weighted_val = recon.get("weighted_value")
        final_val    = recon.get("selected_final_value")
        ws.cell(row=row, column=1, value="القيمة الموزونة").font = _BOLD
        ws.cell(row=row, column=2, value=f"{weighted_val:,.0f}" if isinstance(weighted_val, (int, float)) else _NA)
        row += 1
        ws.cell(row=row, column=1, value="القيمة النهائية المختارة").font = _BOLD
        ws.cell(row=row, column=2, value=f"{final_val:,.0f}" if isinstance(final_val, (int, float)) else _NA)
        row += 1
        _kv(ws, row, "المبرر", recon.get("rationale", _NA)); row += 1
        weights = recon.get("method_weights", {})
        if weights:
            row += 1
            ws.cell(row=row, column=1, value="أوزان الطرق").font = _BOLD
            row += 1
            for m, w in weights.items():
                _kv(ws, row, str(m), str(w)); row += 1
        _col_widths(ws, [35, 35])

        # ── 10. تحليل HBU ────────────────────────────────────────────────────
        ws = wb.create_sheet("تحليل HBU")
        ws.sheet_view.rightToLeft = True
        adv = ctx.get("advanced_reviews", {})
        hbu = adv.get("hbu", {})
        _hdr_row(ws, 1, "تحليل الاستخدام الأمثل (HBU)", 4)
        row = 3
        for k, v in [
            ("اكتمال مراجعة HBU",            "نعم" if hbu.get("completed") else "لا"),
            ("معتمد للاستخدام المبدئي",       "نعم" if hbu.get("approved_for_preliminary") else "لا"),
            ("الحالة",                          hbu.get("status", _NA)),
            ("معتمد للاستخدام النهائي",        "لا — Phase G مطلوب"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [35, 35])

        # ── 11. الفحص القانوني ────────────────────────────────────────────────
        ws = wb.create_sheet("الفحص القانوني")
        ws.sheet_view.rightToLeft = True
        legal = adv.get("legal", {})
        _hdr_row(ws, 1, "الفحص القانوني للعقار", 4)
        row = 3
        for k, v in [
            ("اكتمال الفحص القانوني",      "نعم" if legal.get("completed") else "لا"),
            ("معتمد للاستخدام المبدئي",    "نعم" if legal.get("approved_for_preliminary") else "لا"),
            ("الحالة",                       legal.get("status", _NA)),
            ("ملاحظة هامة",
             "هذا الفحص ليس رأياً قانونياً ولا يُعد بديلاً عن استشارة قانونية متخصصة."),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [35, 50])

        # ── 12. ESG والمخاطر المناخية ─────────────────────────────────────────
        ws = wb.create_sheet("ESG والمخاطر المناخية")
        ws.sheet_view.rightToLeft = True
        esg = adv.get("esg", {})
        _hdr_row(ws, 1, "مراجعة ESG والمخاطر المناخية", 4)
        row = 3
        for k, v in [
            ("اكتمال مراجعة ESG",          "نعم" if esg.get("completed") else "لا"),
            ("معتمد للاستخدام المبدئي",    "نعم" if esg.get("approved_for_preliminary") else "لا"),
            ("الحالة",                       esg.get("status", _NA)),
            ("أثر تلقائي على القيمة",       "لا — ESG استشاري فقط"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [35, 40])

        # ── 13. تحليل SWOT ────────────────────────────────────────────────────
        ws = wb.create_sheet("تحليل SWOT")
        ws.sheet_view.rightToLeft = True
        swot = adv.get("swot", {})
        _hdr_row(ws, 1, "تحليل SWOT والمخاطر الاستراتيجية", 4)
        row = 3
        for k, v in [
            ("اكتمال تحليل SWOT",          "نعم" if swot.get("completed") else "لا"),
            ("معتمد للاستخدام المبدئي",    "نعم" if swot.get("approved_for_preliminary") else "لا"),
            ("الحالة",                       swot.get("status", _NA)),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [35, 35])

        # ── 14. مراجعة النظراء ────────────────────────────────────────────────
        ws = wb.create_sheet("مراجعة النظراء")
        ws.sheet_view.rightToLeft = True
        peer = ctx.get("peer_review_summary", {})
        _hdr_row(ws, 1, "مراجعة النظراء", 4)
        row = 3
        for k, v in [
            ("اسم المراجع",               peer.get("reviewer_name", _NA)),
            ("دور المراجع",               peer.get("reviewer_role", _NA)),
            ("رخصة المراجع",              peer.get("reviewer_license", _NA)),
            ("قرار المراجعة",             peer.get("review_decision", _NA)),
            ("تاريخ المراجعة",            peer.get("review_date", _NA)),
            ("الأقسام المراجَعة",         ", ".join(peer.get("reviewed_sections", [])) or _NA),
            ("جاهزية مراجعة النظراء",    "نعم" if peer.get("peer_review_ready") else "لا"),
            ("ملخص الملاحظات",            peer.get("review_notes_summary", _NA)),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [30, 50])

        # ── 15. توقيع واعتماد الخبير ─────────────────────────────────────────
        ws = wb.create_sheet("توقيع واعتماد الخبير")
        ws.sheet_view.rightToLeft = True
        sig = ctx.get("signature_summary", {})
        _hdr_row(ws, 1, "توقيع الخبير وبيانات الاعتماد", 4)
        row = 3
        for k, v in [
            ("اسم الخبير",               sig.get("expert_name", _NA)),
            ("دور الخبير",               sig.get("expert_role", _NA)),
            ("رخصة الخبير",              sig.get("expert_license", _NA)),
            ("اسم الشركة",               sig.get("firm_name", _NA)),
            ("تاريخ التوقيع",            sig.get("signed_at", _NA)),
            ("التوقيع متاح",             "نعم" if sig.get("signature_available") else "لا"),
            ("الختم متاح",               "نعم" if sig.get("stamp_available") else "لا"),
            ("بيان الاعتماد",            sig.get("approval_statement", _NA)),
            ("جاهزية التوقيع النهائي",   "نعم" if sig.get("final_signoff_ready") else "لا"),
            ("ملاحظة",                   sig.get("note", _NA)),
        ]:
            _kv(ws, row, k, v); row += 1
        row += 1
        ws.cell(row=row, column=1,
                value="ملاحظة: لا تحتوي هذه الخلية على صورة توقيع أو ختم — بيانات وصفية فقط."
               ).fill = _WARN_FILL
        _col_widths(ws, [30, 55])

        # ── 16. سجل التدقيق ──────────────────────────────────────────────────
        ws = wb.create_sheet("سجل التدقيق")
        ws.sheet_view.rightToLeft = True
        out_meta = ctx.get("output_metadata", {})
        _hdr_row(ws, 1, "سجل التدقيق والمخرجات", 4)
        row = 3
        for k, v in [
            ("معرف المخرجات",   out_meta.get("output_id", _NA)),
            ("نوع المخرجات",    out_meta.get("output_type", _NA)),
            ("نسخة المخرجات",   str(out_meta.get("output_version", _NA))),
            ("تاريخ الإنشاء",   out_meta.get("generated_at", _NA)),
            ("منشئ التقرير",    out_meta.get("generated_by", _NA)),
            ("رقم التقرير",     out_meta.get("report_number", _NA)),
            ("تجزئة SHA-256",   out_meta.get("file_hash_sha256", _NA)),
            ("حجم الملف (بايت)",str(out_meta.get("file_size_bytes", _NA))),
        ]:
            _kv(ws, row, k, v); row += 1
        row += 1
        ws.cell(row=row, column=1, value="تقييم بوابة الاعتماد").font = _BOLD
        row += 1
        ws.cell(row=row, column=1, value=gate.get("evaluated_at", _NA))
        row += 2
        ws.cell(row=row, column=1,
                value="لا مصادر خارجية — لا Qdrant — لا RAG — لا OCR."
               ).fill = _OK_FILL
        _col_widths(ws, [30, 55])

        # ── 17. موانع الاعتماد السابقة ────────────────────────────────────────
        ws = wb.create_sheet("موانع الاعتماد السابقة")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "موانع الاعتماد السابقة (تاريخي)", 4)
        row = 3
        current_blockers = gate.get("blockers", [])
        if current_blockers:
            for b in current_blockers:
                ws.cell(row=row, column=1, value=str(b)).fill = _WARN_FILL
                row += 1
        else:
            ws.cell(row=row, column=1,
                    value="لا توجد موانع — اجتازت جميع بوابات الاعتماد"
                   ).fill = _OK_FILL
        _col_widths(ws, [80])

        # ── 18. المخرجات والنسخ ───────────────────────────────────────────────
        ws = wb.create_sheet("المخرجات والنسخ")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "سجل المخرجات والنسخ", 6)
        row = 3
        headers = ["معرف المخرجات", "النوع", "النسخة", "الحالة", "تاريخ الإنشاء", "حجم الملف"]
        for col, h in enumerate(headers, 1):
            c = ws.cell(row=row, column=col, value=h)
            c.font = _BOLD; c.fill = _SEC_FILL; c.alignment = _RTL_ALIGN
        row += 1
        for rec in _read_registry(request_id):
            ws.cell(row=row, column=1, value=rec.get("output_id", _NA))
            ws.cell(row=row, column=2, value=rec.get("output_type", _NA))
            ws.cell(row=row, column=3, value=rec.get("output_version", _NA))
            ws.cell(row=row, column=4, value=rec.get("output_status", _NA))
            ws.cell(row=row, column=5, value=rec.get("generated_at", _NA))
            ws.cell(row=row, column=6, value=str(rec.get("file_size_bytes", _NA)))
            row += 1
        _col_widths(ws, [22, 18, 10, 18, 25, 18])

        wb.save(str(out_path))

        data = out_path.read_bytes()
        sha256 = hashlib.sha256(data).hexdigest()
        return True, "", len(data), sha256

    except Exception as exc:
        return False, str(exc), 0, ""


# ── Route registration ─────────────────────────────────────────────────────────

def register_pv_outputs_routes(app, require_auth) -> None:
    """Register all Phase H output routes on the Flask app."""
    from flask import g, jsonify, request as freq, send_file

    def _actor() -> str:
        return getattr(g, "user_id", None) or "system"

    def _check_id(request_id: str):
        if not _PVR_ID_RE.match(request_id):
            return jsonify({"ok": False, "error": "رقم الطلب غير صالح"}), 400
        return None

    def _gate_check(request_id: str, field: str):
        """Return (gate, None) if generation allowed; (None, error_response) if not."""
        gate = _load_gate_snapshot(request_id)
        if not gate.get(field):
            return None, jsonify({
                "ok":      False,
                "error":   "بوابة الاعتماد النهائية لم تجتز — لا يمكن توليد المخرجات المعتمدة",
                "blockers": gate.get("blockers", []),
                "certification_ready": gate.get("certification_ready", False),
                "gate_status": gate.get("certification_status", "not_ready"),
            }), 422
        return gate, None, None

    # ── POST /api/professional-valuation/requests/<id>/certified-report ────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/certified-report",
        methods=["POST"],
    )
    @require_auth
    def pvh_generate_certified_report(request_id: str):
        err = _check_id(request_id)
        if err:
            return err

        gate = _load_gate_snapshot(request_id)
        if not gate.get("final_report_generation_allowed"):
            return jsonify({
                "ok":                False,
                "error":             "التقرير المعتمد غير مسموح بتوليده — بوابة الاعتماد لم تجتز",
                "blockers":          gate.get("blockers", []),
                "certification_ready": gate.get("certification_ready", False),
            }), 422

        actor   = _actor()
        version = _output_version_for(request_id, "certified_pdf")
        rec     = _new_output_record(request_id, "certified_pdf", actor, version)
        rec["report_number"] = (
            f"PV-RPT-{datetime.utcnow().strftime('%Y%m%d')}-{rec['output_id'][-6:]}"
        )
        rec["certification_gate_snapshot"] = {
            k: v for k, v in gate.items()
            if k not in ("blockers", "warnings", "advisory_only_reason")
        }

        ctx = build_professional_valuation_output_context(request_id)
        ctx["report_number"] = rec["report_number"]
        ctx["output_metadata"] = {
            "output_id":      rec["output_id"],
            "output_type":    "certified_pdf",
            "output_version": version,
            "generated_at":   rec["generated_at"],
            "generated_by":   actor,
            "report_number":  rec["report_number"],
        }

        success, err_msg, size, sha = _generate_certified_pdf(ctx, request_id, rec["output_id"])

        if success:
            rec["output_status"]   = "generated"
            rec["file_available"]  = True
            rec["file_size_bytes"] = size
            rec["file_hash_sha256"] = sha
            rec["internal_file_path"] = str(
                _OUT_DIR / request_id / f"{rec['output_id']}_certified_report.pdf"
            )
            rec["certified_use_allowed"]  = True
            rec["official_use_allowed"]   = True
            rec["public_metadata"] = {
                "report_number":  rec["report_number"],
                "output_version": version,
                "output_type":    "certified_pdf",
                "certified":      True,
            }
        else:
            rec["output_status"]      = "generation_failed"
            rec["file_available"]     = False
            rec["generation_blockers"] = [f"PDF generation error: {err_msg[:300]}"]

        _append_registry(rec)
        _append_output_event(
            request_id, actor, "generate_certified_report",
            output_id=rec["output_id"],
            note=f"status={rec['output_status']} version={version}",
            metadata={"output_type": "certified_pdf", "success": success},
        )

        return jsonify({
            "ok":           True,
            "output":       _safe_output(rec),
            "generation_success": success,
            "generation_error":   err_msg if not success else None,
        }), 200

    # ── GET /api/professional-valuation/requests/<id>/certified-report ─────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/certified-report",
        methods=["GET"],
    )
    @require_auth
    def pvh_download_certified_report(request_id: str):
        err = _check_id(request_id)
        if err:
            return err

        rec = _latest_active_of_type(request_id, "certified_pdf")
        if not rec:
            return jsonify({"ok": False, "error": "لا يوجد تقرير معتمد مُولَّد لهذا الطلب"}), 404

        if not rec.get("file_available"):
            return jsonify({
                "ok":     False,
                "error":  "الملف غير متاح — توليد التقرير فشل أو لم يكتمل",
                "output": _safe_output(rec),
            }), 404

        fpath = Path(rec.get("internal_file_path", ""))
        if not fpath.exists():
            return jsonify({"ok": False, "error": "ملف التقرير غير موجود في النظام"}), 404

        return send_file(
            str(fpath),
            as_attachment=True,
            download_name=f"professional_valuation_certified_report_{rec['output_version']}.pdf",
            mimetype="application/pdf",
        )

    # ── POST /api/professional-valuation/requests/<id>/final-workbook ──────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/final-workbook",
        methods=["POST"],
    )
    @require_auth
    def pvh_generate_final_workbook(request_id: str):
        err = _check_id(request_id)
        if err:
            return err

        gate = _load_gate_snapshot(request_id)
        if not gate.get("final_workbook_generation_allowed"):
            return jsonify({
                "ok":                False,
                "error":             "ملف Excel النهائي غير مسموح بتوليده — بوابة الاعتماد لم تجتز",
                "blockers":          gate.get("blockers", []),
                "certification_ready": gate.get("certification_ready", False),
            }), 422

        actor   = _actor()
        version = _output_version_for(request_id, "final_workbook")
        rec     = _new_output_record(request_id, "final_workbook", actor, version)
        rec["report_number"] = (
            f"PV-WB-{datetime.utcnow().strftime('%Y%m%d')}-{rec['output_id'][-6:]}"
        )
        rec["certification_gate_snapshot"] = {
            k: v for k, v in gate.items()
            if k not in ("blockers", "warnings", "advisory_only_reason")
        }

        ctx = build_professional_valuation_output_context(request_id)
        ctx["report_number"] = rec["report_number"]
        ctx["output_metadata"] = {
            "output_id":       rec["output_id"],
            "output_type":     "final_workbook",
            "output_version":  version,
            "generated_at":    rec["generated_at"],
            "generated_by":    actor,
            "report_number":   rec["report_number"],
            "file_hash_sha256": None,
            "file_size_bytes":  None,
        }

        success, err_msg, size, sha = _generate_final_workbook(ctx, request_id, rec["output_id"])

        if success:
            rec["output_status"]   = "generated"
            rec["file_available"]  = True
            rec["file_size_bytes"] = size
            rec["file_hash_sha256"] = sha
            rec["internal_file_path"] = str(
                _OUT_DIR / request_id / f"{rec['output_id']}_final_workbook.xlsx"
            )
            rec["certified_use_allowed"] = True
            rec["official_use_allowed"]  = True
            rec["public_metadata"] = {
                "report_number":  rec["report_number"],
                "output_version": version,
                "output_type":    "final_workbook",
                "certified":      True,
            }
            ctx["output_metadata"]["file_hash_sha256"] = sha
            ctx["output_metadata"]["file_size_bytes"]  = size
        else:
            rec["output_status"]       = "generation_failed"
            rec["file_available"]      = False
            rec["generation_blockers"] = [f"Workbook generation error: {err_msg[:300]}"]

        _append_registry(rec)
        _append_output_event(
            request_id, actor, "generate_final_workbook",
            output_id=rec["output_id"],
            note=f"status={rec['output_status']} version={version}",
            metadata={"output_type": "final_workbook", "success": success},
        )

        return jsonify({
            "ok":             True,
            "output":         _safe_output(rec),
            "generation_success": success,
            "generation_error":   err_msg if not success else None,
        }), 200

    # ── GET /api/professional-valuation/requests/<id>/final-workbook ───────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/final-workbook",
        methods=["GET"],
    )
    @require_auth
    def pvh_download_final_workbook(request_id: str):
        err = _check_id(request_id)
        if err:
            return err

        rec = _latest_active_of_type(request_id, "final_workbook")
        if not rec:
            return jsonify({"ok": False, "error": "لا يوجد ملف Excel نهائي مُولَّد لهذا الطلب"}), 404

        if not rec.get("file_available"):
            return jsonify({
                "ok":     False,
                "error":  "الملف غير متاح",
                "output": _safe_output(rec),
            }), 404

        fpath = Path(rec.get("internal_file_path", ""))
        if not fpath.exists():
            return jsonify({"ok": False, "error": "ملف Excel غير موجود في النظام"}), 404

        return send_file(
            str(fpath),
            as_attachment=True,
            download_name=f"professional_valuation_final_workbook_{rec['output_version']}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # ── GET /api/professional-valuation/requests/<id>/outputs ──────────────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/outputs",
        methods=["GET"],
    )
    @require_auth
    def pvh_list_outputs(request_id: str):
        err = _check_id(request_id)
        if err:
            return err

        records = _read_registry(request_id)
        events  = read_output_events(request_id)
        gate    = _load_gate_snapshot(request_id)

        return jsonify({
            "ok":      True,
            "outputs": [_safe_output(r) for r in records],
            "total":   len(records),
            "gate_summary": {
                "certification_ready":               gate.get("certification_ready", False),
                "final_report_generation_allowed":   gate.get("final_report_generation_allowed", False),
                "final_workbook_generation_allowed": gate.get("final_workbook_generation_allowed", False),
                "blockers":                          gate.get("blockers", []),
            },
            "event_log": events,
        }), 200

    # ── GET /api/professional-valuation/requests/<id>/outputs/<output_id> ──────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/outputs/<output_id>",
        methods=["GET"],
    )
    @require_auth
    def pvh_get_output(request_id: str, output_id: str):
        err = _check_id(request_id)
        if err:
            return err

        rec = _read_output_by_id(request_id, output_id)
        if rec is None:
            return jsonify({"ok": False, "error": "المخرج غير موجود"}), 404

        return jsonify({"ok": True, "output": _safe_output(rec)}), 200

    # ── POST /api/professional-valuation/requests/<id>/outputs/<id>/revoke ─────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/outputs/<output_id>/revoke",
        methods=["POST"],
    )
    @require_auth
    def pvh_revoke_output(request_id: str, output_id: str):
        err = _check_id(request_id)
        if err:
            return err

        records = _read_registry(request_id)
        found   = None
        for r in records:
            if r.get("output_id") == output_id:
                found = r
                break

        if found is None:
            return jsonify({"ok": False, "error": "المخرج غير موجود"}), 404

        if found.get("output_status") == "revoked":
            return jsonify({"ok": False, "error": "المخرج محذوف بالفعل"}), 409

        # Mark revoked in registry (append a new record reflecting the revocation)
        found["output_status"] = "revoked"
        # Rewrite the entire registry file (simple append-based JSONL doesn't support in-place edits)
        reg_path = _REG_DIR / f"{request_id}.jsonl"
        with open(reg_path, "w", encoding="utf-8") as fh:
            for r in records:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")

        _append_output_event(
            request_id, _actor(), "revoke_output",
            output_id=output_id,
            note="Output revoked — file not deleted",
        )

        return jsonify({
            "ok":     True,
            "output": _safe_output(found),
            "note":   "تم إلغاء المخرج — الملف لا يزال موجوداً على القرص ولم يُحذف",
        }), 200
