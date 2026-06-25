"""
shared_request_routes.py — Generic Request / Lead / Document / Draft-PDF backend.

Supports five source pages:
  chat, tax_appeal, simple_valuation, professional_valuation, composite_valuation

Public endpoints (no auth required):
  POST /api/expert-requests                         — create request + optional docs + draft PDF
  GET  /api/expert-requests/<request_id>            — read request details
  POST /api/expert-requests/<request_id>/documents  — upload additional documents
  POST /api/expert-requests/<request_id>/draft-pdf  — (re-)generate draft PDF
  GET  /api/expert-requests/<request_id>/draft-pdf  — download draft PDF

Admin endpoint (requires auth):
  GET  /api/expert-requests                         — list all requests

Storage (non-public, under core_engine/instance/requests/):
  requests.jsonl
  uploads/<request_id>/<doc_id><ext>
  reports/<request_id>/draft_report.pdf
"""
from __future__ import annotations

import io
import json
import os
import re
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

# ── Storage directories ───────────────────────────────────────────────────────

_BASE      = Path(__file__).parent / "instance" / "requests"
_REQ_FILE  = _BASE / "requests.jsonl"
_UPLOADS   = _BASE / "uploads"
_REPORTS   = _BASE / "reports"
_WORKBOOKS         = Path(__file__).parent / "instance" / "expert_workbooks"
_CERTIFIED_REPORTS = Path(__file__).parent / "instance" / "certified_reports"

for _d in (_BASE, _UPLOADS, _REPORTS, _WORKBOOKS, _CERTIFIED_REPORTS):
    _d.mkdir(parents=True, exist_ok=True)

# ── Constants ─────────────────────────────────────────────────────────────────

_ALLOWED_EXT   = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx", ".xls", ".xlsx"}
_MAX_BYTES     = 10 * 1024 * 1024   # 10 MB per file
_REQUEST_ID_RE = re.compile(r"^REQ-[0-9A-F]{8}$")

_VALID_SOURCE_PAGES = {
    "chat", "tax_appeal", "simple_valuation",
    "professional_valuation", "composite_valuation",
}
_VALID_REQUEST_KINDS = {
    "expert_contact", "certified_report_request", "tax_appeal_review",
    "draft_report_request", "professional_review", "composite_review",
    "general_advisory",
}

# ── Approval status model ─────────────────────────────────────────────────────

_APPROVAL_STATUSES = {
    "draft_only",
    "under_review",
    "needs_documents",
    "approved_pending_report",
    "rejected",
    "certified_report_generated",
}

# Valid status transitions: current_status → allowed_next_statuses
# certified_report_generated is a terminal state reserved for a future task.
_ALLOWED_TRANSITIONS: dict[str, set] = {
    "draft_only":               {"under_review"},
    "under_review":             {"needs_documents", "approved_pending_report", "rejected"},
    "needs_documents":          {"under_review"},
    "approved_pending_report":  {"certified_report_generated"},
    "rejected":                 set(),
    "certified_report_generated": set(),
}

_PDF_TITLES: dict[str, str] = {
    "tax_appeal":             "تقرير فحص ضريبة عقارية مبدئي",
    "simple_valuation":       "تقرير تقييم عقاري مبدئي",
    "chat":                   "ملخص استشارة عقارية مبدئية",
    "professional_valuation": "مسودة مراجعة تقييم احترافي",
    "composite_valuation":    "مسودة تقييم مجمع مبدئية",
}

_DISCLAIMER = (
    "هذا التقرير مبدئي وغير معتمد، ولا يُعد تقرير خبير معتمدًا أو مستندًا صالحًا "
    "للاستخدام أمام الجهات الرسمية أو القضائية أو التمويلية قبل مراجعة واعتماد "
    "خبير التقييم المختص."
)


# ── Persistence helpers ───────────────────────────────────────────────────────

def _new_request_id() -> str:
    return "REQ-" + uuid.uuid4().hex[:8].upper()


def _persist_request(req: dict) -> None:
    with open(_REQ_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(req, ensure_ascii=False) + "\n")


def _update_request(req: dict) -> None:
    """Rewrite the JSONL replacing the record with matching request_id."""
    rid = req["request_id"]
    if not _REQ_FILE.exists():
        _persist_request(req)
        return
    lines = _REQ_FILE.read_text(encoding="utf-8").splitlines()
    updated: list[str] = []
    replaced = False
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            updated.append(raw)
            continue
        if rec.get("request_id") == rid:
            updated.append(json.dumps(req, ensure_ascii=False))
            replaced = True
        else:
            updated.append(raw)
    if not replaced:
        updated.append(json.dumps(req, ensure_ascii=False))
    _REQ_FILE.write_text("\n".join(updated) + "\n", encoding="utf-8")


def _read_request(request_id: str) -> dict | None:
    if not _REQ_FILE.exists():
        return None
    with open(_REQ_FILE, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
                if rec.get("request_id") == request_id:
                    return rec
            except json.JSONDecodeError:
                continue
    return None


def _read_all_requests(limit: int = 50, offset: int = 0) -> list:
    if not _REQ_FILE.exists():
        return []
    rows: list = []
    with open(_REQ_FILE, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rows.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    rows.reverse()   # newest first
    return rows[offset: offset + limit]


# ── Template / approval helpers ──────────────────────────────────────────────

def _get_template_name_safe(template_id: str) -> str:
    """Return Arabic template name from registry; fall back gracefully."""
    try:
        from report_template_registry import get_template_name_ar
        return get_template_name_ar(template_id, default=template_id or "غير محدد")
    except Exception:
        return template_id or "غير محدد"


def _request_summary(req: dict) -> dict:
    """Build a safe summary dict for the admin list endpoint.

    Strips internal filesystem paths; adds computed fields.
    Never exposes expert_workbook_path or draft_pdf_path.
    """
    payload = req.get("payload_json") or {}
    if isinstance(payload, str):
        try:
            payload = __import__("json").loads(payload)
        except Exception:
            payload = {}

    loc_parts = filter(None, [
        payload.get("country", ""),
        payload.get("region", ""),
        payload.get("city", ""),
        payload.get("district", ""),
    ])
    location_summary = " | ".join(loc_parts) or ""

    tmpl_id      = req.get("report_template_id") or ""
    tmpl_name_ar = _get_template_name_safe(tmpl_id)

    return {
        "request_id":              req.get("request_id", ""),
        "created_at":              req.get("created_at", ""),
        "client_name":             req.get("user_name", ""),
        "phone":                   req.get("phone", ""),
        "email":                   req.get("email", ""),
        "source_page":             req.get("source_page", ""),
        "request_kind":            req.get("request_kind", ""),
        "property_type":           payload.get("property_type", ""),
        "location_summary":        location_summary,
        "report_template_id":      tmpl_id,
        "report_template_name_ar": tmpl_name_ar,
        "approval_status":         req.get("approval_status", "draft_only"),
        "expert_workbook_available": bool(req.get("expert_workbook_available")),
        "draft_pdf_available":     req.get("draft_pdf_status") == "generated",
        "certified_report_available": bool(req.get("certified_report_available")),
    }


def _request_detail(req: dict) -> dict:
    """Build safe detail dict for GET /api/expert-requests/<id>.

    Returns all useful fields; strips internal filesystem paths.
    """
    payload = req.get("payload_json") or {}
    if isinstance(payload, str):
        try:
            payload = __import__("json").loads(payload)
        except Exception:
            payload = {}

    tmpl_id      = req.get("report_template_id") or ""
    tmpl_name_ar = _get_template_name_safe(tmpl_id)

    return {
        "request_id":              req.get("request_id", ""),
        "created_at":              req.get("created_at", ""),
        "updated_at":              req.get("updated_at", ""),
        "approval_status":         req.get("approval_status", "draft_only"),
        "status":                  req.get("status", "new"),
        "source_page":             req.get("source_page", ""),
        "request_kind":            req.get("request_kind", ""),
        "user_name":               req.get("user_name", ""),
        "phone":                   req.get("phone", ""),
        "email":                   req.get("email", ""),
        "preferred_contact_method": req.get("preferred_contact_method", ""),
        "summary":                 req.get("summary", ""),
        "report_template_id":      tmpl_id,
        "report_template_name_ar": tmpl_name_ar,
        "payload_json":            payload,
        "document_count":          req.get("document_count", 0),
        "documents":               req.get("documents", []),
        "draft_pdf_available":     req.get("draft_pdf_status") == "generated",
        "draft_pdf_url":           (
            f"/api/expert-requests/{req.get('request_id', '')}/draft-pdf"
            if req.get("draft_pdf_status") == "generated" else None
        ),
        "expert_workbook_available": bool(req.get("expert_workbook_available")),
        "certified_report_available": bool(req.get("certified_report_available")),
        "certified_report_url": (
            f"/api/expert-requests/{req.get('request_id', '')}/certified-report"
            if req.get("certified_report_available") else None
        ),
        "expert_notes":            req.get("expert_notes", ""),
        "expert_recommended_value": req.get("expert_recommended_value", ""),
        "valuation_method_summary": req.get("valuation_method_summary", ""),
        "reconciliation_notes":    req.get("reconciliation_notes", ""),
        "decision_reason":         req.get("decision_reason", ""),
        "requested_documents":     req.get("requested_documents", ""),
        "review_updated_at":       req.get("review_updated_at", ""),
    }


# ── Document upload helpers ───────────────────────────────────────────────────

def _sanitize_filename(name: str) -> str:
    """Strip directory traversal and keep only safe characters."""
    name = os.path.basename(name)
    name = name.replace("..", "")
    safe = "".join(c for c in name if c.isalnum() or c in "._- ")
    return safe.strip() or "upload"


def _save_document(request_id: str, file_obj, document_role: str = "supporting_documents") -> dict:
    """Validate and save one uploaded file; return metadata dict."""
    orig = file_obj.filename or "upload"
    safe = _sanitize_filename(orig)
    ext  = Path(safe).suffix.lower()

    if ext not in _ALLOWED_EXT:
        raise ValueError(f"صيغة الملف غير مدعومة: {ext}")

    data = file_obj.read()
    if len(data) > _MAX_BYTES:
        raise ValueError("حجم الملف يتجاوز الحد الأقصى 10 ميجابايت")

    dest_dir = _UPLOADS / request_id
    dest_dir.mkdir(parents=True, exist_ok=True)

    doc_id      = uuid.uuid4().hex
    stored_name = f"{doc_id}{ext}"
    (dest_dir / stored_name).write_bytes(data)

    return {
        "document_id":           doc_id,
        "request_id":            request_id,
        "original_filename":     safe,
        "stored_filename":       stored_name,
        "extension":             ext,
        "size_bytes":            len(data),
        "uploaded_at":           datetime.utcnow().isoformat(),
        "storage_relative_path": f"instance/requests/uploads/{request_id}/{stored_name}",
        "document_role":         document_role,
    }


# ── Arabic text helper ────────────────────────────────────────────────────────

def _ar(text: str) -> str:
    """Reshape + bidi for Arabic text; fall back to raw string if libraries absent."""
    try:
        from reports.pdf.pdf_arabic import prepare_text
        return prepare_text(str(text))
    except Exception:
        return str(text)


# ── PDF generation ────────────────────────────────────────────────────────────

def _build_draft_pdf(req: dict, docs_meta: list) -> Path:
    """Generate a non-certified draft PDF for any source page.

    Uses Playwright/Chromium HTML-to-PDF via pdf_renderer.
    Chromium handles Arabic shaping, RTL, and bidi natively.
    Never uses FPDF for Arabic user-facing content.
    """
    import html as _html
    from jinja2 import Environment, FileSystemLoader
    from pdf_renderer import cairo_font_css, render_pdf_from_html

    def _e(v) -> str:
        return _html.escape(str(v)) if v is not None else ""

    source_page = req.get("source_page", "")

    # Parse payload_json
    payload = req.get("payload_json") or {}
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            payload = {}

    payload_items = [
        {"key": _e(str(k)), "value": _e(str(v))}
        for k, v in list(payload.items())[:15]
        if v
    ]
    doc_names = [_e(dm.get("original_filename", "")) for dm in (docs_meta or [])]

    env      = Environment(loader=FileSystemLoader(str(_TMPL_DIR)), autoescape=False)
    template = env.get_template("expert_request_receipt.html")
    html_str = template.render(
        font_css_block=cairo_font_css(),
        pdf_title=_e(_PDF_TITLES.get(source_page, "تقرير مبدئي استرشادي")),
        request_id=_e(req.get("request_id", "")),
        created_at=_e((req.get("created_at") or "")[:10]),
        source_page=_e(source_page),
        request_kind=_e(req.get("request_kind", "")),
        user_name=_e(req.get("user_name", "")),
        phone=_e(req.get("phone", "")),
        email=_e(req.get("email", "")),
        preferred_contact_method=_e(req.get("preferred_contact_method", "")),
        summary=_e(req.get("summary", "")),
        payload_items=payload_items,
        doc_names=doc_names,
        disclaimer=_e(_DISCLAIMER),
    )

    pdf_dir  = _REPORTS / req["request_id"]
    pdf_dir.mkdir(parents=True, exist_ok=True)
    out_path = pdf_dir / "draft_report.pdf"

    pdf_bytes = render_pdf_from_html(html_str)
    out_path.write_bytes(pdf_bytes)
    return out_path


# ── Simple valuation quick PDF (no stored request) ───────────────────────────

_TMPL_DIR = Path(__file__).parent / "templates" / "pdf"


# ── Valuation purpose + date-basis helpers (moved to reporting_method_context) ──
# Compatibility re-exports — names unchanged; _srr.* access still works.
from reporting_method_context import (          # noqa: E402
    _RENTAL_PURPOSE_LABELS,
    _detect_valuation_purpose,
    _detect_valuation_date_basis,
)


# ── Workbook validators (moved to reporting_workbook_builder) ────────────────────
# Compatibility re-exports — names unchanged; _srr.* access still works.
from reporting_workbook_builder import (          # noqa: E402
    _validate_workbook_formulas_and_no_silent_blanks,
    _validate_workbook_no_silent_blanks,
)


# ── Valuation method context builder (moved to reporting_method_context) ────────
from reporting_method_context import _build_method_context  # noqa: F811,E402


def _build_simple_valuation_html(payload: dict) -> str:
    """Build the RTL Arabic HTML for the simple valuation draft PDF.

    Renders the Jinja2 template at templates/pdf/simple_valuation_draft.html.
    All user-provided values are html.escape()'d before injection.
    The font CSS block is trusted internal data generated by pdf_renderer.
    """
    import html as _html
    from jinja2 import Environment, FileSystemLoader

    def _e(v) -> str:
        return _html.escape(str(v)) if v is not None else ""

    # Collect and escape payload values
    prop_type   = _e(payload.get("property_type") or "—")
    area_raw    = payload.get("area")
    area_str    = _e(f"{area_raw} م²") if area_raw else "—"
    purpose     = _e(payload.get("purpose") or "القيمة السوقية")
    val_date    = _e(payload.get("valuation_date") or "—")
    condition   = _e(payload.get("condition") or "—")
    finishing   = _e(payload.get("finishing_level") or "")
    description = _e((payload.get("description") or "")[:200])

    notes_parts: list = []
    if payload.get("notes"):
        notes_parts.append(_e(str(payload["notes"])))
    if payload.get("quick_context"):
        notes_parts.append("سؤال السياق: " + _e(str(payload["quick_context"])))
    notes_str = " | ".join(notes_parts)

    geo_parts = [
        _e(payload.get("country")  or ""),
        _e(payload.get("region")   or ""),
        _e(payload.get("city")     or ""),
        _e(payload.get("district") or ""),
    ]
    geo_str = " | ".join(p for p in geo_parts if p)

    mv      = payload.get("estimated_value")
    has_mv  = bool(mv and isinstance(mv, (int, float)) and mv > 0)
    mv_str  = f"{int(mv):,} ج.م" if has_mv else ""
    low_str = (
        f"{int(payload['price_range_low']):,} ج.م"
        if has_mv and payload.get("price_range_low") else ""
    )
    high_str = (
        f"{int(payload['price_range_high']):,} ج.م"
        if has_mv and payload.get("price_range_high") else ""
    )
    cond_mul = (
        f"×{float(payload['cond_multiplier']):.2f}"
        if has_mv and payload.get("cond_multiplier") else ""
    )
    fin_mul = (
        f"×{float(payload['fin_multiplier']):.2f}"
        if has_mv and payload.get("fin_multiplier") else ""
    )

    doc_names_raw = payload.get("doc_names") or []
    doc_names = (
        [_e(str(d)[:120]) for d in doc_names_raw[:10]]
        if isinstance(doc_names_raw, list) else []
    )

    ppsm = payload.get("price_per_sqm")
    price_per_sqm_str = (
        f"{int(ppsm):,} ج.م/م²"
        if ppsm and isinstance(ppsm, (int, float)) and ppsm > 0 else ""
    )

    tmp_ref = _e("TMP-" + uuid.uuid4().hex[:6].upper())

    # ── AVM and per-method context fields ────────────────────────────────────
    def _safe_int_str(v, suffix=" ج.م"):
        try:
            return f"{int(float(str(v))):,}{suffix}" if v else ""
        except (TypeError, ValueError):
            return str(v) if v else ""

    avm_v   = payload.get("avm_value")
    has_avm = bool(avm_v and isinstance(avm_v, (int, float)) and avm_v > 0)
    avm_str = _safe_int_str(avm_v) if has_avm else ""
    avm_low_str  = _safe_int_str(payload.get("avm_low_range"))
    avm_high_str = _safe_int_str(payload.get("avm_high_range"))

    base_ppsm_raw = payload.get("base_price_per_m2")
    base_ppsm_str = _safe_int_str(base_ppsm_raw, " ج.م/م²")
    avm_confidence = _e(str(payload.get("avm_confidence_score") or ""))
    avm_quality    = _e(str(payload.get("avm_data_quality_status") or ""))
    avm_notes_str  = _e(str(payload.get("avm_notes") or ""))
    loc_factor     = _e(str(payload.get("location_factor") or ""))
    cond_factor    = _e(str(payload.get("condition_factor") or ""))
    fin_factor     = _e(str(payload.get("finishing_factor") or ""))

    sales_v   = payload.get("sales_value") or (mv if has_mv else None)
    has_sales = bool(sales_v and isinstance(sales_v, (int, float)) and sales_v > 0)
    sales_str_tbl  = _safe_int_str(sales_v) if has_sales else ""
    sales_w        = _e(str(payload.get("sales_weight") or ""))

    income_v       = payload.get("income_value")
    has_income     = bool(income_v and isinstance(income_v, (int, float)) and income_v > 0)
    income_str_tbl = _safe_int_str(income_v) if has_income else ""
    income_w       = _e(str(payload.get("income_weight") or ""))

    cost_v_raw     = payload.get("cost_value")
    has_cost       = bool(cost_v_raw and isinstance(cost_v_raw, (int, float)) and cost_v_raw > 0)
    cost_str_tbl   = _safe_int_str(cost_v_raw) if has_cost else ""
    cost_w         = _e(str(payload.get("cost_weight") or ""))

    avm_w        = _e(str(payload.get("avm_weight") or ""))
    recon_notes  = _e(str(payload.get("reconciliation_notes") or ""))

    # ── Method context (comparable matrix, income, DCF, cost) ─────────────
    method_ctx = _build_method_context(payload)

    # Render Jinja2 template
    from pdf_renderer import cairo_font_css
    env      = Environment(loader=FileSystemLoader(str(_TMPL_DIR)), autoescape=False)
    template = env.get_template("simple_valuation_draft.html")
    return template.render(
        font_css_block=cairo_font_css(),
        val_date=val_date,
        purpose=purpose,
        geo_str=geo_str,
        prop_type=prop_type,
        area_str=area_str,
        condition=condition,
        finishing=finishing,
        description=description,
        has_mv=has_mv,
        mv_str=mv_str,
        low_str=low_str,
        high_str=high_str,
        cond_mul=cond_mul,
        fin_mul=fin_mul,
        notes_str=notes_str,
        doc_names=doc_names,
        price_per_sqm_str=price_per_sqm_str,
        tmp_ref=tmp_ref,
        # AVM fields
        has_avm=has_avm,
        avm_str=avm_str,
        avm_low_str=avm_low_str,
        avm_high_str=avm_high_str,
        avm_confidence=avm_confidence,
        avm_quality=avm_quality,
        avm_notes_str=avm_notes_str,
        base_ppsm_str=base_ppsm_str,
        loc_factor=loc_factor,
        cond_factor=cond_factor,
        fin_factor=fin_factor,
        # Per-method table fields
        has_sales=has_sales,
        sales_str_tbl=sales_str_tbl,
        sales_w=sales_w,
        has_income=has_income,
        income_str_tbl=income_str_tbl,
        income_w=income_w,
        has_cost=has_cost,
        cost_str_tbl=cost_str_tbl,
        cost_w=cost_w,
        avm_w=avm_w,
        recon_notes=recon_notes,
        # Comparable matrix + income/DCF/cost calculation tables
        comparables=method_ctx["comparables"],
        avg_adjusted_price=method_ctx.get("avg_adjusted_price", ""),
        has_comparables=method_ctx.get("has_comparables", False),
        sales_from_comps=method_ctx.get("sales_from_comps", ""),
        income_monthly_rent=method_ctx.get("income_monthly_rent", ""),
        income_annual_gross=method_ctx.get("income_annual_gross", ""),
        income_vacancy_rate=method_ctx.get("income_vacancy_rate", ""),
        income_vacancy_amt=method_ctx.get("income_vacancy_amt", ""),
        income_collection_loss_pct=method_ctx.get("income_collection_loss_pct", ""),
        income_collection_loss=method_ctx.get("income_collection_loss", ""),
        income_egi=method_ctx.get("income_egi", ""),
        income_expense_rate=method_ctx.get("income_expense_rate", ""),
        income_expenses=method_ctx.get("income_expenses", ""),
        income_reserve_pct=method_ctx.get("income_reserve_pct", ""),
        income_reserve=method_ctx.get("income_reserve", ""),
        income_noi=method_ctx.get("income_noi", ""),
        income_cap_rate_pct=method_ctx.get("income_cap_rate_pct", ""),
        income_value_calc=method_ctx.get("income_value_calc", ""),
        dcf_rows=method_ctx.get("dcf_rows", []),
        dcf_pv_cashflows=method_ctx.get("dcf_pv_cashflows", ""),
        dcf_terminal_noi=method_ctx.get("dcf_terminal_noi", ""),
        dcf_terminal_value=method_ctx.get("dcf_terminal_value", ""),
        dcf_net_terminal=method_ctx.get("dcf_net_terminal", ""),
        dcf_pv_terminal=method_ctx.get("dcf_pv_terminal", ""),
        dcf_value_calc=method_ctx.get("dcf_value_calc", ""),
        dcf_discount_rate_pct=method_ctx.get("dcf_discount_rate_pct", ""),
        dcf_growth_rate_pct=method_ctx.get("dcf_growth_rate_pct", ""),
        dcf_terminal_cap_pct=method_ctx.get("dcf_terminal_cap_pct", ""),
        discount_rate_methods=method_ctx.get("discount_rate_methods", []),
        dr_average=method_ctx.get("dr_average", ""),
        dr_expert_selected=method_ctx.get("dr_expert_selected", ""),
        dr_notes=method_ctx.get("dr_notes", ""),
        terminal_cap_methods=method_ctx.get("terminal_cap_methods", []),
        tc_average=method_ctx.get("tc_average", ""),
        tc_expert_selected=method_ctx.get("tc_expert_selected", ""),
        cost_land_value=method_ctx.get("cost_land_value", ""),
        cost_replacement_per_m2=method_ctx.get("cost_replacement_per_m2", ""),
        cost_replacement_total=method_ctx.get("cost_replacement_total", ""),
        cost_physical_depr_pct=method_ctx.get("cost_physical_depr_pct", ""),
        cost_functional_depr_pct=method_ctx.get("cost_functional_depr_pct", ""),
        cost_total_depr_pct=method_ctx.get("cost_total_depr_pct", ""),
        cost_total_depr_amt=method_ctx.get("cost_total_depr_amt", ""),
        cost_depreciated_imprv=method_ctx.get("cost_depreciated_imprv", ""),
        cost_value_calc=method_ctx.get("cost_value_calc", ""),
        cost_breakdown=method_ctx.get("cost_breakdown", []),
        cost_breakdown_total=method_ctx.get("cost_breakdown_total", ""),
        land_comps=method_ctx.get("land_comps", []),
        avg_land_price=method_ctx.get("avg_land_price", ""),
        land_value_by_sales=method_ctx.get("land_value_by_sales", ""),
        extr_improved_indication=method_ctx.get("extr_improved_indication", ""),
        extr_replacement_cost_new=method_ctx.get("extr_replacement_cost_new", ""),
        extr_depreciation_pct=method_ctx.get("extr_depreciation_pct", ""),
        extr_depr_amount=method_ctx.get("extr_depr_amount", ""),
        extr_depr_imprv_value=method_ctx.get("extr_depr_imprv_value", ""),
        extr_land_value=method_ctx.get("extr_land_value", ""),
        extr_land_per_m2=method_ctx.get("extr_land_per_m2", ""),
        extr_land_share_value=method_ctx.get("extr_land_share_value", ""),
        land_value_reconciled=method_ctx.get("land_value_reconciled", ""),
        land_value_expert_selected=method_ctx.get("land_value_expert_selected", ""),
        map_placeholder_text=method_ctx.get("map_placeholder_text", ""),
        aerial_placeholder_text=method_ctx.get("aerial_placeholder_text", ""),
        comps_map_placeholder_text=method_ctx.get("comps_map_placeholder_text", ""),
        subject_map_image_available=method_ctx.get("subject_map_image_available", False),
        subject_aerial_image_available=method_ctx.get("subject_aerial_image_available", False),
        comparables_map_image_available=method_ctx.get("comparables_map_image_available", False),
        avm_regression=method_ctx.get("avm_regression", []),
        avm_reg_base_value=method_ctx.get("avm_reg_base_value", ""),
        avm_reg_predicted=method_ctx.get("avm_reg_predicted", ""),
        avm_reg_residual=method_ctx.get("avm_reg_residual", ""),
        avm_reg_final=method_ctx.get("avm_reg_final", ""),
        avm_reg_confidence_band=method_ctx.get("avm_reg_confidence_band", ""),
        avm_reg_limitations=method_ctx.get("avm_reg_limitations", ""),
        # New data-binding fields
        price_source_data=method_ctx.get("price_source_data", []),
        mass_appraisal_bridge=method_ctx.get("mass_appraisal_bridge", {}),
        cap_rate_derivation=method_ctx.get("cap_rate_derivation", {}),
        cap_rate_methods=method_ctx.get("cap_rate_derivation", {}).get("methods", []),
        cap_rate_average=method_ctx.get("cap_rate_derivation", {}).get("average_cap_rate", ""),
        cap_rate_expert_selected=method_ctx.get("cap_rate_derivation", {}).get("expert_selected_cap_rate", ""),
        cap_rate_notes=method_ctx.get("cap_rate_derivation", {}).get("final_cap_rate_notes", ""),
        cap_rate_disclaimer=method_ctx.get("cap_rate_derivation", {}).get("disclaimer", ""),
        # Purpose / date-basis / rental
        purpose_info=method_ctx.get("purpose_info", {}),
        date_basis_info=method_ctx.get("date_basis_info", {}),
        is_rental_purpose=method_ctx.get("is_rental_purpose", False),
        rental_value_context=method_ctx.get("rental_value_context", {}),
        rental_comparables=method_ctx.get("rental_value_context", {}).get("rental_comparables", []),
    )


def _build_simple_valuation_pdf_bytes(payload: dict) -> bytes:
    """Build a non-certified advisory draft PDF using Playwright/Chromium.

    Delegates rendering to pdf_renderer.render_pdf_from_html().
    Chromium handles Arabic shaping and RTL natively.
    Never falls back to FPDF for Arabic text.
    """
    from pdf_renderer import render_pdf_from_html
    return render_pdf_from_html(_build_simple_valuation_html(payload))


# ── Internal expert workbook (moved to reporting_workbook_builder) ─────────────────
from reporting_workbook_builder import _create_expert_review_workbook  # noqa: F811,E402


# ── Certified report PDF generation ──────────────────────────────────────────

def _build_certified_report_pdf(req: dict) -> Path:
    """Generate a certified valuation report PDF using Playwright/Chromium HTML renderer.

    Only callable when approval_status == 'approved_pending_report'.
    Uses Jinja2 template at templates/pdf/certified_valuation_report.html.
    Saves to: core_engine/instance/certified_reports/<REQ-ID>/certified_report_<REQ-ID>.pdf
    Never falls back to FPDF — Chromium handles Arabic shaping and RTL natively.
    """
    import html as _html
    from jinja2 import Environment, FileSystemLoader
    from pdf_renderer import cairo_font_css, render_pdf_from_html

    def _e(v) -> str:
        return _html.escape(str(v)) if v is not None else ""

    payload = req.get("payload_json") or {}
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            payload = {}

    location = " | ".join(filter(None, [
        payload.get("country", ""),
        payload.get("region", ""),
        payload.get("city", ""),
        payload.get("district", ""),
    ]))

    area_raw = payload.get("area")
    area_str = f"{area_raw} م²" if area_raw else ""

    # Method context: comparable matrix, income, DCF, cost
    mctx = _build_method_context(payload)

    env      = Environment(loader=FileSystemLoader(str(_TMPL_DIR)), autoescape=False)
    template = env.get_template("certified_valuation_report.html")
    html_str = template.render(
        font_css_block=cairo_font_css(),
        request_id=_e(req.get("request_id", "")),
        report_template_id=req.get("report_template_id") or "",
        created_at=_e((req.get("created_at") or "")[:10]),
        report_date=_e(datetime.utcnow().strftime("%Y-%m-%d")),
        valuation_date=_e(payload.get("valuation_date", "")),
        client_name=_e(req.get("user_name", "")),
        phone=_e(req.get("phone", "")),
        email=_e(req.get("email", "")),
        preferred_contact=_e(req.get("preferred_contact_method", "")),
        report_template_name_ar=_e(_get_template_name_safe(req.get("report_template_id") or "")),
        property_type=_e(payload.get("property_type", "")),
        location=_e(location),
        area=_e(area_str),
        description=_e((payload.get("description") or "")[:300]),
        condition=_e(payload.get("condition", "")),
        finishing=_e(payload.get("finishing_level", "")),
        utilities=_e(payload.get("utilities", "")),
        ownership_type=_e(payload.get("ownership_type", "")),
        current_use=_e(payload.get("current_use", "")),
        notes=_e(payload.get("notes", "")),
        purpose=_e(payload.get("purpose") or "القيمة السوقية"),
        summary=_e(req.get("summary", "")),
        expert_recommended_value=_e(req.get("expert_recommended_value", "")),
        valuation_method_summary=_e(req.get("valuation_method_summary", "")),
        reconciliation_notes=_e(req.get("reconciliation_notes", "")),
        expert_notes=_e(req.get("expert_notes", "")),
        decision_reason=_e(req.get("decision_reason", "")),
        requested_documents=_e(req.get("requested_documents", "")),
        review_updated_at=_e((req.get("review_updated_at") or "")[:10]),
        # Per-method values from expert review fields
        sales_comparison_value=_e(req.get("sales_comparison_value", "")),
        sales_comparison_weight=_e(req.get("sales_comparison_weight", "")),
        weighted_sales=_e(req.get("weighted_sales", "")),
        income_value=_e(req.get("income_value", "")),
        income_weight=_e(req.get("income_weight", "")),
        weighted_income=_e(req.get("weighted_income", "")),
        cap_rate=_e(req.get("cap_rate", "")),
        noi=_e(req.get("noi", "")),
        cost_value=_e(req.get("cost_value", "")),
        cost_weight=_e(req.get("cost_weight", "")),
        weighted_cost=_e(req.get("weighted_cost", "")),
        land_value=_e(req.get("land_value", "")),
        replacement_cost=_e(req.get("replacement_cost", "")),
        total_depreciation=_e(req.get("total_depreciation", "")),
        dcf_value=_e(req.get("dcf_value", "")),
        dcf_weight=_e(req.get("dcf_weight", "")),
        weighted_dcf=_e(req.get("weighted_dcf", "")),
        discount_rate=_e(req.get("discount_rate", "")),
        dcf_period=_e(req.get("dcf_period", "")),
        sensitivity_low=_e(req.get("sensitivity_low", "")),
        sensitivity_high=_e(req.get("sensitivity_high", "")),
        expert_name=_e(req.get("expert_name", "")),
        expert_reg_number=_e(req.get("expert_reg_number", "")),
        # AVM context fields (from payload or expert review)
        avm_value=_e(str(payload.get("avm_value") or req.get("avm_value") or "")),
        avm_low_range=_e(str(payload.get("avm_low_range") or req.get("avm_low_range") or "")),
        avm_high_range=_e(str(payload.get("avm_high_range") or req.get("avm_high_range") or "")),
        avm_confidence_score=_e(str(payload.get("avm_confidence_score") or req.get("avm_confidence_score") or "")),
        avm_data_quality_status=_e(str(payload.get("avm_data_quality_status") or req.get("avm_data_quality_status") or "")),
        avm_notes=_e(str(payload.get("avm_notes") or req.get("avm_notes") or "")),
        base_price_per_m2=_e(str(payload.get("base_price_per_m2") or "")),
        location_factor=_e(str(payload.get("location_factor") or "")),
        condition_factor=_e(str(payload.get("condition_factor") or "")),
        finishing_factor=_e(str(payload.get("finishing_factor") or "")),
        expert_override_value=_e(str(req.get("expert_override_value") or "")),
        expert_override_reason=_e(str(req.get("expert_override_reason") or "")),
        avm_weight=_e(str(payload.get("avm_weight") or req.get("avm_weight") or "")),
        weighted_avm=_e(str(req.get("weighted_avm") or "")),
        # Comparable matrix + income/DCF/cost calculation tables
        comparables=mctx["comparables"],
        avg_adjusted_price=mctx.get("avg_adjusted_price", ""),
        has_comparables=mctx.get("has_comparables", False),
        sales_from_comps=mctx.get("sales_from_comps", ""),
        income_monthly_rent=mctx.get("income_monthly_rent", ""),
        income_annual_gross=mctx.get("income_annual_gross", ""),
        income_vacancy_rate=mctx.get("income_vacancy_rate", ""),
        income_vacancy_amt=mctx.get("income_vacancy_amt", ""),
        income_egi=mctx.get("income_egi", ""),
        income_expense_rate=mctx.get("income_expense_rate", ""),
        income_expenses=mctx.get("income_expenses", ""),
        income_noi=mctx.get("income_noi", ""),
        income_cap_rate_pct=mctx.get("income_cap_rate_pct", ""),
        income_value_calc=mctx.get("income_value_calc", ""),
        dcf_rows=mctx.get("dcf_rows", []),
        dcf_pv_cashflows=mctx.get("dcf_pv_cashflows", ""),
        dcf_terminal_value=mctx.get("dcf_terminal_value", ""),
        dcf_pv_terminal=mctx.get("dcf_pv_terminal", ""),
        dcf_value_calc=mctx.get("dcf_value_calc", ""),
        dcf_discount_rate_pct=mctx.get("dcf_discount_rate_pct", ""),
        dcf_growth_rate_pct=mctx.get("dcf_growth_rate_pct", ""),
        dcf_terminal_cap_pct=mctx.get("dcf_terminal_cap_pct", ""),
        cost_land_value=mctx.get("cost_land_value", ""),
        cost_replacement_per_m2=mctx.get("cost_replacement_per_m2", ""),
        cost_replacement_total=mctx.get("cost_replacement_total", ""),
        cost_physical_depr_pct=mctx.get("cost_physical_depr_pct", ""),
        cost_functional_depr_pct=mctx.get("cost_functional_depr_pct", ""),
        cost_total_depr_pct=mctx.get("cost_total_depr_pct", ""),
        cost_total_depr_amt=mctx.get("cost_total_depr_amt", ""),
        cost_depreciated_imprv=mctx.get("cost_depreciated_imprv", ""),
        cost_value_calc=mctx.get("cost_value_calc", ""),
        cost_breakdown=mctx.get("cost_breakdown", []),
        cost_breakdown_total=mctx.get("cost_breakdown_total", ""),
        land_comps=mctx.get("land_comps", []),
        avg_land_price=mctx.get("avg_land_price", ""),
        land_value_by_sales=mctx.get("land_value_by_sales", ""),
        extr_improved_indication=mctx.get("extr_improved_indication", ""),
        extr_replacement_cost_new=mctx.get("extr_replacement_cost_new", ""),
        extr_depreciation_pct=mctx.get("extr_depreciation_pct", ""),
        extr_depr_amount=mctx.get("extr_depr_amount", ""),
        extr_depr_imprv_value=mctx.get("extr_depr_imprv_value", ""),
        extr_land_value=mctx.get("extr_land_value", ""),
        extr_land_per_m2=mctx.get("extr_land_per_m2", ""),
        extr_land_share_value=mctx.get("extr_land_share_value", ""),
        land_value_reconciled=mctx.get("land_value_reconciled", ""),
        land_value_expert_selected=mctx.get("land_value_expert_selected", ""),
        map_placeholder_text=mctx.get("map_placeholder_text", ""),
        aerial_placeholder_text=mctx.get("aerial_placeholder_text", ""),
        comps_map_placeholder_text=mctx.get("comps_map_placeholder_text", ""),
        subject_map_image_available=mctx.get("subject_map_image_available", False),
        subject_aerial_image_available=mctx.get("subject_aerial_image_available", False),
        comparables_map_image_available=mctx.get("comparables_map_image_available", False),
        discount_rate_methods=mctx.get("discount_rate_methods", []),
        dr_average=mctx.get("dr_average", ""),
        dr_expert_selected=mctx.get("dr_expert_selected", ""),
        dr_notes=mctx.get("dr_notes", ""),
        terminal_cap_methods=mctx.get("terminal_cap_methods", []),
        tc_average=mctx.get("tc_average", ""),
        tc_expert_selected=mctx.get("tc_expert_selected", ""),
        tc_notes=mctx.get("tc_notes", ""),
        dcf_terminal_noi=mctx.get("dcf_terminal_noi", ""),
        dcf_selling_costs_pct=mctx.get("dcf_selling_costs_pct", ""),
        dcf_net_terminal=mctx.get("dcf_net_terminal", ""),
        income_collection_loss_pct=mctx.get("income_collection_loss_pct", ""),
        income_collection_loss=mctx.get("income_collection_loss", ""),
        income_reserve_pct=mctx.get("income_reserve_pct", ""),
        income_reserve=mctx.get("income_reserve", ""),
        avm_regression=mctx.get("avm_regression", []),
        avm_reg_base_value=mctx.get("avm_reg_base_value", ""),
        avm_reg_predicted=mctx.get("avm_reg_predicted", ""),
        avm_reg_residual=mctx.get("avm_reg_residual", ""),
        avm_reg_final=mctx.get("avm_reg_final", ""),
        avm_reg_confidence_band=mctx.get("avm_reg_confidence_band", ""),
        avm_reg_limitations=mctx.get("avm_reg_limitations", ""),
        # New data-binding fields
        price_source_data=mctx.get("price_source_data", []),
        mass_appraisal_bridge=mctx.get("mass_appraisal_bridge", {}),
        cap_rate_derivation=mctx.get("cap_rate_derivation", {}),
        cap_rate_methods=mctx.get("cap_rate_derivation", {}).get("methods", []),
        cap_rate_average=mctx.get("cap_rate_derivation", {}).get("average_cap_rate", ""),
        cap_rate_expert_selected=mctx.get("cap_rate_derivation", {}).get("expert_selected_cap_rate", ""),
        cap_rate_notes=mctx.get("cap_rate_derivation", {}).get("final_cap_rate_notes", ""),
        cap_rate_disclaimer=mctx.get("cap_rate_derivation", {}).get("disclaimer", ""),
        # Purpose / date-basis / rental
        purpose_info=mctx.get("purpose_info", {}),
        date_basis_info=mctx.get("date_basis_info", {}),
        is_rental_purpose=mctx.get("is_rental_purpose", False),
        rental_value_context=mctx.get("rental_value_context", {}),
        rental_comparables=mctx.get("rental_value_context", {}).get("rental_comparables", []),
    )

    pdf_dir  = _CERTIFIED_REPORTS / req["request_id"]
    pdf_dir.mkdir(parents=True, exist_ok=True)
    out_path = pdf_dir / f"certified_report_{req['request_id']}.pdf"

    pdf_bytes = render_pdf_from_html(html_str)
    out_path.write_bytes(pdf_bytes)
    return out_path


# ── Route registration ────────────────────────────────────────────────────────

def register(app, require_auth, limiter=None) -> None:
    """Register /api/expert-requests/* routes on *app*."""
    from flask import jsonify, request, send_file

    # ── POST /api/expert-requests — Create request ─────────────────────────
    @app.route("/api/expert-requests", methods=["POST", "OPTIONS"])
    def expert_request_create():
        if request.method == "OPTIONS":
            return jsonify({}), 200

        form  = request.form
        files = request.files

        # Validate source_page
        source_page = (form.get("source_page") or "").strip().lower()
        if not source_page or source_page not in _VALID_SOURCE_PAGES:
            return jsonify({
                "status":  "error",
                "message": f"source_page مطلوب. القيم المقبولة: {', '.join(sorted(_VALID_SOURCE_PAGES))}",
            }), 400

        # Validate required contact fields
        user_name = (form.get("user_name") or "").strip()
        phone     = (form.get("phone")     or "").strip()
        email     = (form.get("email")     or "").strip()
        if not user_name:
            return jsonify({"status": "error", "message": "user_name مطلوب"}), 400
        if not phone and not email:
            return jsonify({"status": "error", "message": "رقم الهاتف أو البريد الإلكتروني مطلوب"}), 400

        request_kind = (form.get("request_kind") or "").strip().lower()
        if not request_kind or request_kind not in _VALID_REQUEST_KINDS:
            request_kind = "general_advisory"

        report_template_id = (form.get("report_template_id") or "").strip()

        # Parse optional payload_json
        raw_payload = form.get("payload_json") or ""
        try:
            payload_obj = json.loads(raw_payload) if raw_payload else {}
        except Exception:
            payload_obj = {}

        request_id = _new_request_id()
        now        = datetime.utcnow().isoformat()

        req: dict = {
            "request_id":           request_id,
            "created_at":           now,
            "updated_at":           now,
            "source_page":          source_page,
            "request_kind":         request_kind,
            "status":               "new",
            "approval_status":      "draft_only",
            "user_name":            user_name,
            "phone":                phone,
            "email":                email,
            "preferred_contact_method": (form.get("preferred_contact_method") or "").strip(),
            "summary":              (form.get("summary") or "").strip(),
            "report_template_id":   report_template_id,
            "payload_json":         payload_obj,
            "calculation_json":     {},
            "document_count":       0,
            "documents":            [],
            "draft_pdf_status":     "not_generated",
            "draft_pdf_path":       None,
            "internal_notes":       "",
            "client_visible_message": "",
        }

        # Process document uploads
        doc_errors: list[str] = []
        docs_saved: list[dict] = []
        for key in sorted(files.keys()):
            if not key.startswith("doc_"):
                continue
            f = files[key]
            if not f or not f.filename:
                continue
            try:
                meta = _save_document(request_id, f)
                docs_saved.append(meta)
            except ValueError as exc:
                doc_errors.append(f"{f.filename}: {exc}")

        req["documents"]      = docs_saved
        req["document_count"] = len(docs_saved)

        # Generate draft PDF
        pdf_available   = False
        pdf_download_url = None
        pdf_message     = "لم يتم إنشاء التقرير المبدئي"

        try:
            pdf_path = _build_draft_pdf(req, docs_saved)
            req["draft_pdf_status"] = "generated"
            req["draft_pdf_path"]   = str(pdf_path.relative_to(Path(__file__).parent))
            pdf_available    = True
            pdf_download_url = f"/api/expert-requests/{request_id}/draft-pdf"
            pdf_message      = "تم إنشاء التقرير المبدئي بنجاح"
        except Exception as exc:
            req["draft_pdf_status"] = f"error: {exc}"

        # Generate internal expert workbook (never exposed to ordinary user)
        workbook_available = False
        try:
            wb_path = _create_expert_review_workbook(request_id, req, docs_saved)
            req["expert_workbook_path"]      = str(wb_path)
            req["expert_workbook_available"] = True
            workbook_available = True
        except Exception as _wb_exc:
            req["expert_workbook_available"] = False

        _persist_request(req)

        return jsonify({
            "status":           "success",
            "request_id":       request_id,
            "source_page":      source_page,
            "request_kind":     request_kind,
            "message": (
                f"تم تسجيل طلب مراجعة التقرير. رقم الطلب: {request_id}. "
                "هذا ليس تقريرًا معتمدًا. سيتم إصدار النسخة المعتمدة فقط بعد مراجعة الخبير. "
                + ("تم إنشاء ملف مراجعة داخلي للخبير." if workbook_available else "")
            ).strip(),
            "pdf_available":            pdf_available,
            "pdf_download_url":         pdf_download_url,
            "pdf_message":              pdf_message,
            "non_certified":            True,
            "expert_workbook_available": workbook_available,
            "documents_saved":          len(docs_saved),
            "document_errors":          doc_errors,
        }), 201

    # ── GET /api/expert-requests/<id> — Request details ───────────────────
    @app.route("/api/expert-requests/<request_id>", methods=["GET"])
    def expert_request_get(request_id: str):
        if not _REQUEST_ID_RE.match(request_id):
            return jsonify({"status": "error", "message": "رقم الطلب غير صالح"}), 400
        req = _read_request(request_id)
        if req is None:
            return jsonify({"status": "error", "message": "الطلب غير موجود"}), 404
        return jsonify({"status": "ok", "request": _request_detail(req)}), 200

    # ── POST /api/expert-requests/<id>/documents — Upload documents ────────
    @app.route("/api/expert-requests/<request_id>/documents", methods=["POST"])
    def expert_request_upload_documents(request_id: str):
        if not _REQUEST_ID_RE.match(request_id):
            return jsonify({"status": "error", "message": "رقم الطلب غير صالح"}), 400
        req = _read_request(request_id)
        if req is None:
            return jsonify({"status": "error", "message": "الطلب غير موجود"}), 404

        files      = request.files
        doc_errors: list[str] = []
        docs_saved: list[dict] = []

        for key in sorted(files.keys()):
            f = files[key]
            if not f or not f.filename:
                continue
            try:
                role = request.form.get(f"role_{key}", "supporting_documents")
                meta = _save_document(request_id, f, document_role=role)
                docs_saved.append(meta)
            except ValueError as exc:
                doc_errors.append(f"{f.filename}: {exc}")

        if docs_saved:
            existing = req.get("documents") or []
            existing.extend(docs_saved)
            req["documents"]      = existing
            req["document_count"] = len(existing)
            req["updated_at"]     = datetime.utcnow().isoformat()
            _update_request(req)

        return jsonify({
            "status":          "success",
            "request_id":      request_id,
            "documents_saved": len(docs_saved),
            "document_errors": doc_errors,
        }), 200 if not doc_errors else 207

    # ── POST /api/expert-requests/<id>/draft-pdf — Generate PDF ───────────
    @app.route("/api/expert-requests/<request_id>/draft-pdf", methods=["POST"])
    def expert_request_generate_pdf(request_id: str):
        if not _REQUEST_ID_RE.match(request_id):
            return jsonify({"status": "error", "message": "رقم الطلب غير صالح"}), 400
        req = _read_request(request_id)
        if req is None:
            return jsonify({"status": "error", "message": "الطلب غير موجود"}), 404

        try:
            pdf_path = _build_draft_pdf(req, req.get("documents") or [])
            req["draft_pdf_status"] = "generated"
            req["draft_pdf_path"]   = str(pdf_path.relative_to(Path(__file__).parent))
            req["updated_at"]       = datetime.utcnow().isoformat()
            _update_request(req)
            return jsonify({
                "status":          "success",
                "request_id":      request_id,
                "pdf_available":   True,
                "pdf_download_url": f"/api/expert-requests/{request_id}/draft-pdf",
                "non_certified":   True,
                "message":         "تم إنشاء التقرير المبدئي بنجاح",
            }), 200
        except Exception as exc:
            return jsonify({
                "status":  "error",
                "message": f"فشل إنشاء التقرير المبدئي: {exc}",
            }), 500

    # ── GET /api/expert-requests/<id>/draft-pdf — Download PDF ────────────
    @app.route("/api/expert-requests/<request_id>/draft-pdf", methods=["GET"])
    def expert_request_download_pdf(request_id: str):
        if not _REQUEST_ID_RE.match(request_id):
            return jsonify({"status": "error", "message": "رقم الطلب غير صالح"}), 400

        pdf_path = _REPORTS / request_id / "draft_report.pdf"
        if not pdf_path.exists():
            return jsonify({"status": "error", "message": "التقرير المبدئي غير موجود"}), 404

        resp = send_file(
            str(pdf_path),
            mimetype="application/pdf",
            as_attachment=False,
            download_name=f"draft_report_{request_id}.pdf",
        )
        resp.headers["X-PDF-Renderer"] = "html-playwright"
        return resp

    # ── GET /api/expert-requests/<id>/expert-workbook — Admin Excel download ─
    @app.route("/api/expert-requests/<request_id>/expert-workbook", methods=["GET"])
    @require_auth
    def expert_request_download_workbook(request_id: str):
        if not _REQUEST_ID_RE.match(request_id):
            return jsonify({"status": "error", "message": "رقم الطلب غير صالح"}), 400
        wb_path = _WORKBOOKS / request_id / f"expert_review_{request_id}.xlsx"
        if not wb_path.exists():
            return jsonify({"status": "error", "message": "ملف المراجعة غير موجود"}), 404
        return send_file(
            str(wb_path),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"expert_review_{request_id}.xlsx",
        )

    # ── POST /api/expert-requests/<id>/certified-report — Generate certified PDF ─
    @app.route("/api/expert-requests/<request_id>/certified-report", methods=["POST"])
    @require_auth
    def expert_request_generate_certified_report(request_id: str):
        """Generate a certified valuation report PDF for an approved request.

        Preconditions:
          - JWT/admin auth required.
          - approval_status must be 'approved_pending_report'.
          - expert_recommended_value must be set.

        On success:
          - Generates PDF using HTML/Playwright renderer.
          - Saves to internal path (never exposed).
          - Sets approval_status = 'certified_report_generated'.
          - Sets certified_report_available = True.
        """
        if not _REQUEST_ID_RE.match(request_id):
            return jsonify({"status": "error", "message": "رقم الطلب غير صالح"}), 400

        req = _read_request(request_id)
        if req is None:
            return jsonify({"status": "error", "message": "الطلب غير موجود"}), 404

        current_status = req.get("approval_status", "draft_only")
        if current_status != "approved_pending_report":
            return jsonify({
                "status":  "error",
                "message": (
                    f"لا يمكن إصدار التقرير المعتمد للطلب بحالة '{current_status}'. "
                    "يجب أن تكون الحالة 'approved_pending_report' لإصدار التقرير المعتمد."
                ),
            }), 400

        if not (req.get("expert_recommended_value") or "").strip():
            return jsonify({
                "status":  "error",
                "message": "يجب إدخال القيمة النهائية الموصى بها من الخبير قبل إصدار التقرير المعتمد.",
            }), 400

        try:
            _build_certified_report_pdf(req)
        except Exception as exc:
            return jsonify({
                "status":  "error",
                "message": f"فشل إنشاء التقرير المعتمد: {exc}",
            }), 500

        now = datetime.utcnow().isoformat()
        req["approval_status"]              = "certified_report_generated"
        req["certified_report_available"]   = True
        req["certified_report_generated_at"] = now
        req["updated_at"]                   = now
        _update_request(req)

        return jsonify({
            "status":                     "success",
            "request_id":                 request_id,
            "approval_status":            "certified_report_generated",
            "certified_report_available": True,
            "message":                    "تم إصدار التقرير المعتمد بعد مراجعة الخبير.",
        }), 200

    # ── GET /api/expert-requests/<id>/certified-report — Download certified PDF ─
    @app.route("/api/expert-requests/<request_id>/certified-report", methods=["GET"])
    @require_auth
    def expert_request_download_certified_report(request_id: str):
        """Download the generated certified report PDF.

        Requires JWT/admin auth.
        Only available when approval_status == 'certified_report_generated'.
        Returns application/pdf with X-PDF-Renderer header.
        Does not expose internal filesystem path.
        """
        if not _REQUEST_ID_RE.match(request_id):
            return jsonify({"status": "error", "message": "رقم الطلب غير صالح"}), 400

        req = _read_request(request_id)
        if req is None:
            return jsonify({"status": "error", "message": "الطلب غير موجود"}), 404

        if req.get("approval_status") != "certified_report_generated":
            return jsonify({
                "status":  "error",
                "message": "التقرير المعتمد غير متاح. يجب إصداره أولاً بعد اعتماد مراجعة الخبير.",
            }), 409

        pdf_path = _CERTIFIED_REPORTS / request_id / f"certified_report_{request_id}.pdf"
        if not pdf_path.exists():
            return jsonify({
                "status":  "error",
                "message": "ملف التقرير المعتمد غير موجود على الخادم.",
            }), 404

        resp = send_file(
            str(pdf_path),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"certified_report_{request_id}.pdf",
        )
        resp.headers["X-PDF-Renderer"] = "html-playwright"
        return resp

    # ── POST /api/simple-valuation/draft-pdf — Quick advisory PDF ─────────
    @app.route("/api/simple-valuation/draft-pdf", methods=["POST", "OPTIONS"])
    def simple_valuation_draft_pdf():
        """Generate a non-certified advisory draft PDF directly from valuation data.

        No expert request is stored.  No contact info required.
        Returns application/pdf bytes with watermark and disclaimer.
        """
        if request.method == "OPTIONS":
            return jsonify({}), 200

        try:
            payload = request.get_json(force=True, silent=True) or {}
        except Exception:
            payload = {}

        prop_type = (payload.get("property_type") or "").strip()
        area_val  = payload.get("area")
        if not prop_type and not area_val:
            return jsonify({
                "status":  "error",
                "message": "يجب توفير نوع العقار أو المساحة على الأقل لإنشاء التقرير المبدئي",
            }), 400

        try:
            pdf_bytes = _build_simple_valuation_pdf_bytes(payload)
            buf = io.BytesIO(pdf_bytes)
            buf.seek(0)
            resp = send_file(
                buf,
                mimetype="application/pdf",
                as_attachment=True,
                download_name="draft_valuation_report.pdf",
            )
            resp.headers["X-PDF-Renderer"] = "html-playwright"
            return resp
        except Exception as exc:
            return jsonify({
                "status":  "error",
                "message": f"فشل إنشاء التقرير المبدئي: {exc}",
            }), 500

    # ── GET /api/expert-requests — List requests (admin only) ─────────────
    @app.route("/api/expert-requests", methods=["GET"])
    @require_auth
    def expert_request_list():
        limit  = min(int(request.args.get("limit", 50)), 200)
        offset = int(request.args.get("offset", 0))
        rows   = _read_all_requests(limit=limit, offset=offset)
        summaries = [_request_summary(r) for r in rows]
        return jsonify({
            "status":   "ok",
            "total":    len(summaries),
            "requests": summaries,
            "pagination": {"limit": limit, "offset": offset},
        }), 200

    # ── POST /api/expert-requests/<id>/review — Update review status ───────
    @app.route("/api/expert-requests/<request_id>/review", methods=["POST"])
    @require_auth
    def expert_request_review(request_id: str):
        """Update expert review status and notes for a request.

        Enforces allowed status transitions.
        Does not generate certified reports — certified_report_generated
        is reserved for a future task and cannot be set here.
        """
        if not _REQUEST_ID_RE.match(request_id):
            return jsonify({"status": "error", "message": "رقم الطلب غير صالح"}), 400

        req = _read_request(request_id)
        if req is None:
            return jsonify({"status": "error", "message": "الطلب غير موجود"}), 404

        body = request.get_json(force=True, silent=True) or {}

        new_status = (body.get("approval_status") or "").strip()
        if new_status:
            if new_status not in _APPROVAL_STATUSES:
                return jsonify({
                    "status":  "error",
                    "message": f"حالة غير صالحة: {new_status!r}. "
                               f"القيم المقبولة: {', '.join(sorted(_APPROVAL_STATUSES))}",
                }), 400

            # Block certified_report_generated via review — must use POST /certified-report
            if new_status == "certified_report_generated":
                return jsonify({
                    "status":  "error",
                    "message": "لا يمكن تعيين حالة 'certified_report_generated' مباشرةً عبر نقطة المراجعة. "
                               "استخدم POST /api/expert-requests/<id>/certified-report لإصدار التقرير المعتمد.",
                }), 400

            current_status = req.get("approval_status", "draft_only")
            allowed = _ALLOWED_TRANSITIONS.get(current_status, set())
            if new_status not in allowed:
                return jsonify({
                    "status":  "error",
                    "message": (
                        f"الانتقال من '{current_status}' إلى '{new_status}' غير مسموح. "
                        f"الانتقالات المسموحة من '{current_status}': "
                        + (", ".join(sorted(allowed)) if allowed else "لا يوجد انتقال مسموح")
                    ),
                }), 400

            req["approval_status"] = new_status

        now = datetime.utcnow().isoformat()
        # Update optional review fields
        for field in (
            "expert_notes", "requested_documents", "expert_recommended_value",
            "valuation_method_summary", "reconciliation_notes", "decision_reason",
            "sales_comparison_value", "sales_comparison_weight", "weighted_sales",
            "income_value", "income_weight", "weighted_income", "cap_rate", "noi",
            "cost_value", "cost_weight", "weighted_cost",
            "land_value", "replacement_cost", "total_depreciation",
            "dcf_value", "dcf_weight", "weighted_dcf", "discount_rate", "dcf_period",
            "sensitivity_low", "sensitivity_high",
            "avm_value", "avm_low_range", "avm_high_range",
            "avm_confidence_score", "avm_data_quality_status", "avm_notes",
            "avm_weight", "weighted_avm",
            "expert_override_value", "expert_override_reason",
            "expert_name", "expert_reg_number",
        ):
            val = body.get(field)
            if val is not None:
                req[field] = str(val).strip()

        req["review_updated_at"] = now
        req["updated_at"] = now

        # Append review log entry to Excel workbook سجل المراجعة sheet (best-effort)
        try:
            wb_path = _WORKBOOKS / request_id / f"expert_review_{request_id}.xlsx"
            if wb_path.exists():
                import openpyxl
                wb = openpyxl.load_workbook(str(wb_path))
                ws_log = wb["سجل المراجعة"]
                next_row = ws_log.max_row + 1
                note = (req.get("expert_notes") or "")[:80]
                ws_log.cell(row=next_row, column=1, value=now[:19].replace("T", " "))
                ws_log.cell(row=next_row, column=2, value=f"تحديث الحالة → {req.get('approval_status', '')}")
                ws_log.cell(row=next_row, column=3, value="الخبير")
                ws_log.cell(row=next_row, column=4, value=note)
                # Update Dashboard حالة الطلب cell (row 3, col 5)
                ws_dash = wb["Dashboard"]
                for row in ws_dash.iter_rows():
                    for cell in row:
                        if cell.value and "حالة الطلب" in str(cell.value):
                            # The value cell is in the same row, 2 columns right
                            ws_dash.cell(
                                row=cell.row,
                                column=cell.column + 1,
                                value=req.get("approval_status", ""),
                            )
                            break
                wb.save(str(wb_path))
        except Exception:
            pass  # workbook update is best-effort; do not fail the review

        _update_request(req)

        return jsonify({
            "status":          "success",
            "request_id":      request_id,
            "approval_status": req.get("approval_status", ""),
            "review_updated_at": now,
            "message":         "تم تحديث مراجعة الخبير بنجاح. لم يتم إنشاء تقرير معتمد.",
            "non_certified":   True,
            "certified_report_available": False,
        }), 200
