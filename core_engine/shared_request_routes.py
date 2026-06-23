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
    )


def _build_simple_valuation_pdf_bytes(payload: dict) -> bytes:
    """Build a non-certified advisory draft PDF using Playwright/Chromium.

    Delegates rendering to pdf_renderer.render_pdf_from_html().
    Chromium handles Arabic shaping and RTL natively.
    Never falls back to FPDF for Arabic text.
    """
    from pdf_renderer import render_pdf_from_html
    return render_pdf_from_html(_build_simple_valuation_html(payload))


# ── Internal expert workbook ──────────────────────────────────────────────────

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
    area_s  = (f"{payload.get('area')} م²" if payload.get("area") else "")

    wb = openpyxl.Workbook()

    # ── Sheet 1: Dashboard ────────────────────────────────────────────────────
    ws_d = wb.active
    ws_d.title = "Dashboard"
    _rtl(ws_d)
    _widths(ws_d, [30, 28, 28, 30, 28, 28])

    # Title
    ws_d.merge_cells("A1:F1")
    ws_d["A1"].value     = "لوحة معلومات المراجعة الداخلية — Expert Smart"
    ws_d["A1"].font      = F_TITLE
    ws_d["A1"].fill      = _fill(C_BLUE_D)
    ws_d["A1"].alignment = AL_CTR
    ws_d.row_dimensions[1].height = 28

    # Section: بيانات الطلب
    _sec_hdr(ws_d, 2, 1, 6, "بيانات الطلب")
    _kv(ws_d, 3, "رقم الطلب",     request_id,                                  1, 2, 3)
    _kv(ws_d, 3, "حالة الطلب",    req.get("approval_status", "قيد المراجعة"),  4, 5, 6)
    _kv(ws_d, 4, "تاريخ الإنشاء", (req.get("created_at") or "")[:10],          1, 2, 3)
    _kv(ws_d, 4, "نوع الطلب",     req.get("request_kind", ""),                 4, 5, 6)
    _kv(ws_d, 5, "اسم العميل",    req.get("user_name", ""),                    1, 2, 3)
    _kv(ws_d, 5, "الهاتف",        req.get("phone", ""),                        4, 5, 6)
    _kv(ws_d, 6, "نموذج التقرير المطلوب", _tmpl_name_ar,                       1, 2, 3,
        vbg=C_GOLD_BG if _tmpl_name_ar and _tmpl_name_ar != "غير محدد" else C_GRAY)
    _kv(ws_d, 6, "معرّف النموذج (ID)",   _tmpl_id or "—",                     4, 5, 6)
    ws_d.row_dimensions[7].height = 8

    # Section: بيانات العقار
    _sec_hdr(ws_d, 8, 1, 6, "بيانات العقار")
    _kv(ws_d, 9,  "نوع العقار",      payload.get("property_type", ""),          1, 2, 3)
    _kv(ws_d, 9,  "الغرض",           payload.get("purpose", "القيمة السوقية"),  4, 5, 6)
    _kv(ws_d, 10, "الموقع",          location,                                  1, 2, 3)
    _kv(ws_d, 10, "المساحة",         area_s,                                    4, 5, 6)
    _kv(ws_d, 11, "تاريخ التقييم",   payload.get("valuation_date", ""),         1, 2, 3)
    _kv(ws_d, 11, "حالة البيانات",   data_status,                               4, 5, 6,
        vbg=C_GREEN if has_mv else C_RED)
    ws_d.row_dimensions[12].height = 8

    # Section: حالة طرق التقييم
    _sec_hdr(ws_d, 13, 1, 6, "حالة طرق التقييم")
    _kv(ws_d, 14, "مقارنة البيوع",  "متاحة" if has_mv else "تحتاج مقارنات",  1, 2, 3,
        vbg=C_GREEN if has_mv else C_RED)
    _kv(ws_d, 14, "طريقة الدخل",   "تحتاج بيانات دخل",                        4, 5, 6, vbg=C_RED)
    _kv(ws_d, 15, "طريقة التكلفة", "تحتاج بيانات تكلفة",                       1, 2, 3, vbg=C_RED)
    _kv(ws_d, 15, "التوفيق",        "قيد المراجعة",                            4, 5, 6, vbg=C_GOLD_BG)
    _kv(ws_d, 16, "حالة المستندات", docs_status,                               1, 2, 3,
        vbg=C_GREEN if docs_meta else C_RED)
    _kv(ws_d, 16, "حالة التوثيق",  "لم تراجع بعد",                             4, 5, 6, vbg=C_RED)
    ws_d.row_dimensions[17].height = 8

    # Section: القيمة المبدئية
    _sec_hdr(ws_d, 18, 1, 6, "القيمة المبدئية")
    _kv(ws_d, 19, "القيمة المبدئية", mv_str if mv_str else "غير متاحة",        1, 2, 3,
        vbg=C_GREEN if has_mv else C_RED)
    _kv(ws_d, 19, "النطاق السعري",   rng_s if rng_s else "—",                  4, 5, 6,
        vbg=C_GOLD_BG if rng_s else C_GRAY)
    ws_d.row_dimensions[20].height = 8

    # Section: قرار الخبير (gold)
    _sec_hdr(ws_d, 21, 1, 6, "قرار الخبير", C_GOLD, "7A5800")
    ws_d.merge_cells("A22:F22")
    cq = ws_d["A22"]
    cq.value     = "قيد المراجعة — يُعبأ بواسطة الخبير"
    cq.font      = F_GOLD
    cq.fill      = _fill(C_GOLD_BG)
    cq.alignment = AL_CTR
    ws_d.row_dimensions[22].height = 22
    ws_d.row_dimensions[23].height = 8

    # Section: ملاحظات الخبير
    _sec_hdr(ws_d, 24, 1, 6, "ملاحظات الخبير الرئيسية")
    ws_d.merge_cells("A25:F28")
    cn = ws_d["A25"]
    cn.value     = ""
    cn.fill      = _fill(C_WHITE)
    cn.alignment = AL_TOP
    for r in range(25, 29):
        ws_d.row_dimensions[r].height = 20

    ws_d.freeze_panes = ws_d["A3"]

    # ── Sheet 2: غلاف وملخص ──────────────────────────────────────────────────
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

    # ── Sheet 3: بيانات العقار ────────────────────────────────────────────────
    ws3 = wb.create_sheet("بيانات العقار")
    _hdr(ws3, ["الحقل", "القيمة"])
    rows3 = [
        ("نوع العقار",           payload.get("property_type", "")),
        ("وصف العقار",           (payload.get("description") or "")[:200]),
        ("العنوان الكامل",        location),
        ("الدولة",               payload.get("country", "")),
        ("المحافظة / المنطقة",   payload.get("region", "")),
        ("المدينة",              payload.get("city", "")),
        ("الحي / المنطقة",       payload.get("district", "")),
        ("المساحة (م²)",         payload.get("area", "")),
        ("حالة العقار",          payload.get("condition", "")),
        ("مستوى التشطيب",        payload.get("finishing_level", "")),
        ("المرافق والخدمات",      ""),
        ("حقوق الملكية",         ""),
        ("سهولة الوصول",         ""),
        ("الملاحظات",            (payload.get("notes") or "")),
        ("المستندات المرفقة",    doc_names_s),
    ]
    for i, (k, v) in enumerate(rows3, 2):
        _row(ws3, i, k, v)
    _widths(ws3, [32, 54])

    # ── Sheet 4: مقارنة البيوع ────────────────────────────────────────────────
    ws4 = wb.create_sheet("مقارنة البيوع")
    _hdr(ws4, [
        "رقم المقارن", "نوع العقار", "الموقع", "المساحة",
        "تاريخ البيع / العرض", "قيمة البيع", "سعر المتر",
        "التشطيب", "الإطلالة / المزايا",
        "معامل الموقع", "معامل المساحة", "معامل الحالة", "معامل التاريخ",
        "السعر المعدل", "ملاحظات الخبير",
    ])
    for n in range(1, 4):
        _row(ws4, n + 1, f"مقارن {n}", "", "", "", "", "", "", "", "",
             "", "", "", "", "")
    _widths(ws4, [14, 16, 22, 12, 18, 16, 14, 12, 18, 14, 14, 14, 14, 16, 30])

    # ── Sheet 5: طريقة الدخل ──────────────────────────────────────────────────
    ws5 = wb.create_sheet("طريقة الدخل")
    _hdr(ws5, ["الحقل", "القيمة", "ملاحظات الخبير"])
    income_rows = [
        "نوع الاستخدام",
        "المساحة المؤجرة (م²)",
        "الإيجار الشهري",
        "الدخل السنوي الإجمالي",
        "نسبة الشواغر (%)",
        "المصاريف الدورية",
        "صافي الدخل التشغيلي NOI",
        "معدل الرسملة (%)",
        "القيمة بطريقة الدخل",
        "ملاحظات الخبير",
    ]
    for i, field in enumerate(income_rows, 2):
        _row(ws5, i, field, "", "")
    _widths(ws5, [38, 26, 50])

    # ── Sheet 6: طريقة التكلفة ────────────────────────────────────────────────
    ws6 = wb.create_sheet("طريقة التكلفة")
    _hdr(ws6, ["الحقل", "القيمة", "ملاحظات الخبير"])
    cost_rows = [
        "إجمالي مسطح الأرض (م²)",
        "إجمالي مسطح المباني (م²)",
        "مسطح الجزء محل التقييم (م²)",
        "نصيب الجزء من الأرض (م²)",
        "سعر متر الأرض",
        "قيمة نصيب الأرض",
        "تكلفة إنشاء المتر كجديد",
        "تكلفة إنشاء الجزء محل التقييم",
        "العمر الفعال (سنة)",
        "العمر الاقتصادي (سنة)",
        "الإهلاك القابل للإصلاح",
        "الإهلاك غير القابل للإصلاح",
        "إجمالي الإهلاك",
        "القيمة بطريقة التكلفة",
        "ملاحظات الخبير",
    ]
    for i, field in enumerate(cost_rows, 2):
        _row(ws6, i, field, "", "")
    _widths(ws6, [40, 26, 50])

    # ── Sheet 7: توفيق النتائج ────────────────────────────────────────────────
    ws7 = wb.create_sheet("توفيق النتائج")
    _hdr(ws7, ["الحقل", "القيمة", "ملاحظات الخبير"])
    recon_rows = [
        ("قيمة طريقة مقارنة البيوع",              "",   ""),
        ("وزن طريقة مقارنة البيوع %",             "40", "وزن افتراضي إرشادي — قابل للتعديل بواسطة الخبير"),
        ("قيمة طريقة الدخل",                      "",   ""),
        ("وزن طريقة الدخل %",                     "40", "وزن افتراضي إرشادي — قابل للتعديل بواسطة الخبير"),
        ("قيمة طريقة التكلفة",                    "",   ""),
        ("وزن طريقة التكلفة %",                   "20", "وزن افتراضي إرشادي — قابل للتعديل بواسطة الخبير"),
        ("القيمة المرجحة النهائية",                "",   ""),
        ("حساسية التقييم ±10%",                   "",   ""),
        ("القيمة الدنيا",                          "",   ""),
        ("القيمة العليا",                          "",   ""),
        ("القيمة التي يوصي بها الخبير",           "",   ""),
        ("قرار الخبير",                            "قيد المراجعة", ""),
        ("ملاحظات التوفيق",                       "",   ""),
    ]
    for i, (k, v, note) in enumerate(recon_rows, 2):
        _row(ws7, i, k, v, note)
    _widths(ws7, [40, 26, 54])

    # ── Sheet 8: المستندات ────────────────────────────────────────────────────
    ws8 = wb.create_sheet("المستندات")
    _hdr(ws8, ["اسم المستند", "نوع المستند", "حالة المراجعة", "ملاحظات الخبير"])
    for i, dm in enumerate(docs_meta or [], 2):
        _row(ws8, i,
             dm.get("original_filename", ""),
             dm.get("document_role", "supporting_documents"),
             "قيد المراجعة",
             "")
    _widths(ws8, [44, 24, 24, 44])

    # ── Sheet 9: سجل المراجعة ────────────────────────────────────────────────
    ws9 = wb.create_sheet("سجل المراجعة")
    _hdr(ws9, ["التاريخ والوقت", "الإجراء", "المستخدم / الدور", "الملاحظة"])
    now_str = (req.get("created_at") or "")[:19].replace("T", " ")
    _row(ws9, 2, now_str, "إنشاء الطلب", "النظام", f"إنشاء الطلب {request_id} تلقائيًا")
    if _tmpl_id:
        _row(ws9, 3, now_str, "نموذج التقرير المطلوب", "العميل",
             f"نموذج: {_tmpl_name_ar} ({_tmpl_id})")
    _widths(ws9, [25, 32, 28, 54])

    # Save
    wb_dir  = _WORKBOOKS / request_id
    wb_dir.mkdir(parents=True, exist_ok=True)
    wb_path = wb_dir / f"expert_review_{request_id}.xlsx"
    wb.save(str(wb_path))
    return wb_path


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

    env      = Environment(loader=FileSystemLoader(str(_TMPL_DIR)), autoescape=False)
    template = env.get_template("certified_valuation_report.html")
    html_str = template.render(
        font_css_block=cairo_font_css(),
        request_id=_e(req.get("request_id", "")),
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
