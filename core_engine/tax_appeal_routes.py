"""
tax_appeal_routes.py — Tax Appeal Backend Phase 1-3 + Phase 4 Expert Workflow.

Public endpoints (no auth required):
  POST /api/tax-appeal/leads                              — create lead, upload docs, generate FPDF PDF
  GET  /api/tax-appeal/leads/<id>/pdf                     — download FPDF draft PDF
  POST /api/tax-appeal/preliminary-pdf                    — stateless HTML/Playwright preliminary PDF

Expert-request endpoints (public creation, protected admin):
  POST /api/tax-appeal/expert-request                     — create expert request + generate workbook
  GET  /api/tax-appeal/expert-requests                    — admin list (requires auth)
  GET  /api/tax-appeal/expert-requests/<id>               — detail (public by request_id)
  POST /api/tax-appeal/expert-requests/<id>/review        — admin status transition
  POST /api/tax-appeal/expert-requests/<id>/expert-draft-pdf — admin generate HTML/Playwright draft
  GET  /api/tax-appeal/expert-requests/<id>/expert-draft-pdf — admin download
  GET  /api/tax-appeal/expert-requests/<id>/expert-workbook  — admin download workbook

Admin endpoint:
  GET  /api/tax-appeal/leads          — list leads (requires auth)

Storage:
  core_engine/tax_appeal/leads.jsonl             — leads (existing)
  core_engine/tax_appeal/uploads/<id>/           — uploads (existing)
  core_engine/tax_appeal/reports/<id>/           — FPDF PDFs (existing)
  core_engine/instance/tax_appeal_requests/      — expert requests (new)
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path

from request_limits import accepted_uploaded_files

_MAX_FILE_COUNT = 5

# ── Storage directories ───────────────────────────────────────────────────────

_BASE       = Path(__file__).parent / "tax_appeal"
_LEADS_FILE = _BASE / "leads.jsonl"
_UPLOADS    = _BASE / "uploads"
_REPORTS    = _BASE / "reports"

# ── Expert-request storage ────────────────────────────────────────────────────

_ER_BASE     = Path(__file__).parent / "instance" / "tax_appeal_requests"
_ER_FILE     = _ER_BASE / "requests.jsonl"
_ER_REPORTS  = _ER_BASE / "reports"
_ER_WB_DIR   = Path(__file__).parent / "instance" / "tax_appeal_workbooks"

for _d in (_ER_BASE, _ER_REPORTS, _ER_WB_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# Status model for expert requests
_VALID_ER_STATUSES = {
    "draft_only", "under_review", "needs_documents",
    "approved_pending_appeal_report", "appeal_report_generated", "rejected",
}
_ALLOWED_TRANSITIONS = {
    "draft_only":                    {"under_review"},
    "under_review":                  {"needs_documents", "approved_pending_appeal_report", "rejected"},
    "needs_documents":               {"under_review", "rejected"},
    "approved_pending_appeal_report": {"appeal_report_generated", "rejected"},
    "appeal_report_generated":       set(),
    "rejected":                      set(),
}

_ER_ID_RE = re.compile(r"^TAXER-[0-9A-F]{8}$")

for _d in (_BASE, _UPLOADS, _REPORTS):
    _d.mkdir(parents=True, exist_ok=True)

# ── Expert-request persistence helpers ───────────────────────────────────────

def _new_er_id() -> str:
    return "TAXER-" + uuid.uuid4().hex[:8].upper()


def _persist_er(rec: dict) -> None:
    with open(_ER_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _update_er(request_id: str, updates: dict) -> None:
    if not _ER_FILE.exists():
        return
    lines = []
    with open(_ER_FILE, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
                if rec.get("request_id") == request_id:
                    rec.update(updates)
                lines.append(json.dumps(rec, ensure_ascii=False))
            except json.JSONDecodeError:
                lines.append(raw)
    with open(_ER_FILE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def _read_er(request_id: str) -> dict | None:
    if not _ER_FILE.exists():
        return None
    with open(_ER_FILE, encoding="utf-8") as fh:
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


def _read_all_er(limit: int = 50, offset: int = 0) -> list:
    if not _ER_FILE.exists():
        return []
    rows: list = []
    with open(_ER_FILE, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rows.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    rows.reverse()
    return rows[offset: offset + limit]

# ── Constants ─────────────────────────────────────────────────────────────────

_ALLOWED_EXT = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx", ".xls", ".xlsx"}
_MAX_BYTES   = 10 * 1024 * 1024                 # 10 MB per file
_LEAD_ID_RE  = re.compile(r"^TAX-[0-9A-F]{8}$")

_DISCLAIMER = (
    "هذا التقرير مبدئي وغير معتمد، ولا يُعد طعنًا رسميًا أو تقرير خبير معتمد، "
    "ولا يستخدم أمام الجهات الرسمية أو القضائية أو التمويلية قبل مراجعة واعتماد "
    "خبير التقييم المختص."
)


# ── Standalone PDF renderers (importable by QA scripts) ───────────────────────

def _render_tax_preliminary_pdf(ctx: dict) -> bytes:
    """Render the preliminary PDF from a pre-built context dict. Returns PDF bytes."""
    from pdf_renderer import cairo_font_css, render_pdf_from_html
    from jinja2 import Environment, FileSystemLoader

    _TMPL_DIR = Path(__file__).parent / "templates" / "pdf"
    env = Environment(loader=FileSystemLoader(str(_TMPL_DIR)), autoescape=False)
    html_str = env.get_template("tax_appeal_preliminary.html").render(
        font_css_block=cairo_font_css(), **ctx
    )
    return render_pdf_from_html(html_str)


def _render_tax_expert_draft_pdf(ctx: dict) -> bytes:
    """Render the expert-draft PDF from a pre-built context dict. Returns PDF bytes."""
    from pdf_renderer import cairo_font_css, render_pdf_from_html
    from jinja2 import Environment, FileSystemLoader

    _TMPL_DIR = Path(__file__).parent / "templates" / "pdf"
    env = Environment(loader=FileSystemLoader(str(_TMPL_DIR)), autoescape=False)
    html_str = env.get_template("tax_appeal_expert_draft.html").render(
        font_css_block=cairo_font_css(), **ctx
    )
    return render_pdf_from_html(html_str)


# ── Lead persistence ──────────────────────────────────────────────────────────

def _new_lead_id() -> str:
    return "TAX-" + uuid.uuid4().hex[:8].upper()


def _persist_lead(lead: dict) -> None:
    with open(_LEADS_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(lead, ensure_ascii=False) + "\n")


def _read_lead(lead_id: str) -> dict | None:
    if not _LEADS_FILE.exists():
        return None
    with open(_LEADS_FILE, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
                if rec.get("lead_id") == lead_id:
                    return rec
            except json.JSONDecodeError:
                continue
    return None


def _read_all_leads(limit: int = 50, offset: int = 0) -> list:
    if not _LEADS_FILE.exists():
        return []
    rows: list = []
    with open(_LEADS_FILE, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rows.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    rows.reverse()                              # newest first
    return rows[offset: offset + limit]


# ── Document upload helpers ───────────────────────────────────────────────────

def _sanitize_filename(name: str) -> str:
    """Strip directory traversal and keep only safe characters."""
    name = os.path.basename(name)               # remove directory components
    name = name.replace("..", "")               # block double-dot sequences
    safe = "".join(c for c in name if c.isalnum() or c in "._- ")
    return safe.strip() or "upload"


def _save_document(lead_id: str, file_obj) -> dict:
    """Validate and save one uploaded file; return metadata dict."""
    orig  = file_obj.filename or "upload"
    safe  = _sanitize_filename(orig)
    ext   = Path(safe).suffix.lower()

    if ext not in _ALLOWED_EXT:
        raise ValueError(f"صيغة الملف غير مدعومة: {ext}")

    data = file_obj.read()
    if len(data) > _MAX_BYTES:
        raise ValueError("حجم الملف يتجاوز الحد الأقصى 10 ميجابايت")

    dest_dir = _UPLOADS / lead_id
    dest_dir.mkdir(parents=True, exist_ok=True)

    doc_id      = uuid.uuid4().hex
    stored_name = f"{doc_id}{ext}"
    (dest_dir / stored_name).write_bytes(data)

    return {
        "document_id":           doc_id,
        "lead_id":               lead_id,
        "original_filename":     safe,
        "stored_filename":       stored_name,
        "extension":             ext,
        "size_bytes":            len(data),
        "uploaded_at":           datetime.utcnow().isoformat(),
        "storage_relative_path": f"tax_appeal/uploads/{lead_id}/{stored_name}",
    }


# ── PDF generation ────────────────────────────────────────────────────────────

def _ar(text: str) -> str:
    """Reshape + bidi for Arabic text; fall back to raw string."""
    try:
        from reports.pdf.pdf_arabic import prepare_text
        return prepare_text(str(text))
    except Exception:
        return str(text)


def _build_pdf(lead: dict, docs_meta: list) -> Path:
    """Generate a non-certified draft PDF for a tax appeal lead."""
    from fpdf import FPDF

    pdf_dir  = _REPORTS / lead["lead_id"]
    pdf_dir.mkdir(parents=True, exist_ok=True)
    out_path = pdf_dir / "tax_screening_draft.pdf"

    # Resolve Cairo fonts (bundled with the project)
    _font_r = _font_b = None
    try:
        from reports.pdf.pdf_arabic import find_font
        _font_r = str(find_font("cairo-regular"))
        _font_b = str(find_font("cairo-bold"))
    except Exception:
        pass

    # Mutable font-name container so the inner class can read it after
    # fonts are registered on the FPDF instance.
    _fn = ["Arial"]

    class _TaxPDF(FPDF):
        def header(self):
            self.set_font(_fn[0], "B", 9)
            self.set_text_color(31, 78, 120)
            self.cell(0, 7, _ar("ALHADY FOR REAL PROPERTY"),
                      align="C", new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(0, 0, 0)

        def footer(self):
            self.set_y(-14)
            self.set_text_color(150, 150, 150)
            if _fn[0] != "Arial":
                self.set_font(_fn[0], "", 7)
                label = _ar("تقرير آلي استرشادي - غير معتمد رسميًا") + f"  |  {self.page_no()}"
            else:
                self.set_font("Helvetica", "", 7)
                label = f"Advisory Draft - Non-Certified  |  {self.page_no()}"
            self.cell(0, 8, label, align="C")
            self.set_text_color(0, 0, 0)

    pdf = _TaxPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)

    # Register Cairo fonts before first add_page() so header() uses them
    if _font_r:
        try:
            pdf.add_font("Cairo", style="",  fname=_font_r)
            pdf.add_font("Cairo", style="B", fname=_font_b or _font_r)
            _fn[0] = "Cairo"
        except Exception:
            pass  # stay with Arial

    pdf.add_page()
    fn = _fn[0]

    def _heading(text: str, size: int = 11):
        pdf.set_font(fn, "B", size)
        pdf.set_text_color(31, 78, 120)
        pdf.cell(0, 9, _ar(text), align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)

    def _row(label: str, value: str):
        pdf.set_font(fn, "B", 10)
        pdf.cell(60, 7, _ar(label), align="R")
        pdf.set_font(fn, "",  10)
        pdf.cell(0,  7, str(value or "—"), align="L",
                 new_x="LMARGIN", new_y="NEXT")

    def _hr():
        pdf.set_draw_color(212, 175, 55)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(3)

    # Title
    pdf.set_font(fn, "B", 15)
    pdf.set_text_color(212, 175, 55)
    pdf.cell(0, 11, _ar("تقرير فحص ضريبة عقارية مبدئي"),
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)

    # Watermark banner
    pdf.set_fill_color(255, 243, 220)
    pdf.set_font(fn, "B", 10)
    pdf.set_text_color(180, 50, 0)
    pdf.cell(0, 8, _ar("تقرير آلي استرشادي - غير معتمد رسميًا"),
             align="C", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)
    _hr()

    # Request info
    _heading("بيانات الطلب")
    _row("رقم الطلب:",     lead.get("lead_id", ""))
    _row("تاريخ الإنشاء:", lead.get("created_at", ""))
    _row("نوع الضريبة:",   lead.get("tax_type", ""))
    _row("نوع الأصل:",     lead.get("asset_type", ""))
    _hr()

    # Geographic
    _heading("النطاق الجغرافي")
    _row("الدولة:",              lead.get("country", ""))
    _row("المنطقة / المحافظة:", lead.get("region", ""))
    _row("المدينة / الحي:",      lead.get("city", ""))
    _row("المساحة (م²):",  lead.get("area", ""))
    _row("حالة العقار:",         lead.get("property_status", ""))
    _hr()

    # Financial
    _heading("البيانات المالية")
    _row("قيمة المطالبة الحكومية:",    lead.get("government_claim", ""))
    if lead.get("sale_value"):
        _row("قيمة التصرف / البيع:",   lead.get("sale_value", ""))
    if lead.get("annual_rental_estimate"):
        _row("تقدير الإيجار السنوي:",  lead.get("annual_rental_estimate", ""))
    _row("الضريبة المقدّرة (استرشادي):", lead.get("calculated_estimated_tax", ""))
    _row("الوفر المحتمل:",             lead.get("calculated_potential_saving", ""))
    _row("نسبة الفجوة:",              lead.get("calculated_gap_percent", ""))
    _row("مستوى المخاطرة:",           lead.get("risk_level", ""))
    _hr()

    # Documents
    if docs_meta:
        _heading("المستندات المرفقة")
        for dm in docs_meta:
            pdf.set_font(fn, "", 10)
            pdf.cell(0, 6, f"  • {dm.get('original_filename', '')}",
                     align="R", new_x="LMARGIN", new_y="NEXT")
        _hr()

    # Disclaimer (new page)
    pdf.add_page()
    _heading("إخلاء المسؤولية", 12)
    pdf.set_font(fn, "", 10)
    pdf.set_text_color(120, 50, 50)
    pdf.multi_cell(0, 7, _ar(_DISCLAIMER), align="R")
    pdf.set_text_color(0, 0, 0)

    pdf.output(str(out_path))
    return out_path


# ── Route registration ────────────────────────────────────────────────────────

def register(app, require_auth, limiter=None) -> None:
    """Register /api/tax-appeal/* routes on *app*."""
    from flask import jsonify, request, send_file

    # ── POST /api/tax-appeal/leads ─────────────────────────────────────────
    @app.route("/api/tax-appeal/leads", methods=["POST", "OPTIONS"])
    def tax_appeal_create_lead():
        if request.method == "OPTIONS":
            return jsonify({}), 200

        form  = request.form
        files = request.files

        owner_name = (form.get("owner_name") or "").strip()
        phone      = (form.get("phone") or "").strip()
        if not owner_name or not phone:
            return jsonify({
                "status": "error",
                "message": "الاسم ورقم الهاتف مطلوبان",
            }), 400

        lead_id = _new_lead_id()
        now     = datetime.utcnow().isoformat()

        lead = {
            "lead_id":         lead_id,
            "created_at":      now,
            "status":          "new",
            "approval_status": "draft_lead",
            "source_page":     "tax_appeal_tab",
            # Tax screening
            "tax_type":                   form.get("tax_type", ""),
            "asset_type":                 form.get("asset_type", ""),
            "country":                    form.get("country", ""),
            "region":                     form.get("region", ""),
            "city":                       form.get("city", ""),
            "district":                   form.get("district", ""),
            "area":                       form.get("area", ""),
            "property_status":            form.get("property_status", ""),
            "government_claim":           form.get("government_claim", ""),
            "sale_value":                 form.get("sale_value", ""),
            "annual_rental_estimate":     form.get("annual_rental_estimate", ""),
            "form3_status":               form.get("form3_status", ""),
            "calculated_estimated_tax":   form.get("calculated_estimated_tax", ""),
            "calculated_potential_saving":form.get("calculated_potential_saving", ""),
            "calculated_gap_percent":     form.get("calculated_gap_percent", ""),
            "risk_level":                 form.get("risk_level", ""),
            # Contact
            "owner_name":     owner_name,
            "phone":          phone,
            "email":          form.get("email", ""),
            "request_type":   form.get("request_type", ""),
            "contact_method": form.get("contact_method", ""),
            "summary":        form.get("summary", ""),
        }

        # Upload documents — enforce 5-file limit (Wave 4B1)
        _accepted = accepted_uploaded_files(files)
        if len(_accepted) > _MAX_FILE_COUNT:
            return jsonify({"error": "too_many_files", "maximum": _MAX_FILE_COUNT}), 413

        docs_meta: list  = []
        doc_errors: list = []
        for fo in _accepted:
            try:
                docs_meta.append(_save_document(lead_id, fo))
            except ValueError as exc:
                doc_errors.append(str(exc))

        lead["documents"] = docs_meta
        _persist_lead(lead)

        # Generate draft PDF
        pdf_available    = False
        pdf_download_url = None
        pdf_message      = ""
        try:
            _build_pdf(lead, docs_meta)
            pdf_available    = True
            pdf_download_url = f"/api/tax-appeal/leads/{lead_id}/pdf"
            pdf_message      = "تم إنشاء التقرير المبدئي بنجاح"
        except Exception as pdf_err:
            pdf_message = f"لم يتم إنشاء التقرير المبدئي: {pdf_err}"

        return jsonify({
            "status":           "success",
            "lead_id":          lead_id,
            "message": (
                f"تم تسجيل طلب الفحص بنجاح. رقم الطلب: {lead_id}. "
                "سيقوم الخبير بمراجعة البيانات والمستندات."
            ),
            "pdf_available":    pdf_available,
            "pdf_download_url": pdf_download_url,
            "pdf_message":      pdf_message,
            "documents_saved":  len(docs_meta),
            "document_errors":  doc_errors,
        }), 201

    # ── GET /api/tax-appeal/leads/<lead_id>/pdf ────────────────────────────
    @app.route("/api/tax-appeal/leads/<lead_id>/pdf", methods=["GET"])
    def tax_appeal_download_pdf(lead_id: str):
        if not _LEAD_ID_RE.fullmatch(lead_id):
            return jsonify({"status": "error",
                            "message": "معرّف الطلب غير صالح"}), 400

        pdf_path = _REPORTS / lead_id / "tax_screening_draft.pdf"
        if not pdf_path.exists():
            return jsonify({"status": "error",
                            "message": "التقرير غير متاح"}), 404

        return send_file(
            str(pdf_path),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"tax_screening_draft_{lead_id}.pdf",
        )

    # ── GET /api/tax-appeal/leads (admin/internal) ─────────────────────────
    @app.route("/api/tax-appeal/leads", methods=["GET"])
    @require_auth
    def tax_appeal_list_leads():
        try:
            limit  = min(int(request.args.get("limit",  50)), 200)
            offset = max(int(request.args.get("offset",  0)),   0)
        except ValueError:
            limit, offset = 50, 0
        records = _read_all_leads(limit=limit, offset=offset)
        return jsonify({"status": "ok", "count": len(records), "leads": records})

    # ── POST /api/tax-appeal/preliminary-pdf ──────────────────────────────
    # Stateless — accepts JSON payload, returns HTML/Playwright PDF bytes.
    # Does not store any data.  No FPDF used.
    @app.route("/api/tax-appeal/preliminary-pdf", methods=["POST", "OPTIONS"])
    def tax_appeal_preliminary_pdf():
        if request.method == "OPTIONS":
            return jsonify({}), 200
        try:
            payload = request.get_json(force=True, silent=True) or {}
        except Exception:
            payload = {}

        try:
            from tax_appeal_context import _build_tax_appeal_context
            from pdf_renderer import cairo_font_css, render_pdf_from_html
            from jinja2 import Environment, FileSystemLoader

            ctx = _build_tax_appeal_context(payload)
            _TMPL_DIR = Path(__file__).parent / "templates" / "pdf"
            env = Environment(loader=FileSystemLoader(str(_TMPL_DIR)), autoescape=False)
            template = env.get_template("tax_appeal_preliminary.html")
            html_str = template.render(font_css_block=cairo_font_css(), **ctx)
            pdf_bytes = render_pdf_from_html(html_str)

            from flask import Response
            return Response(
                pdf_bytes,
                status=200,
                mimetype="application/pdf",
                headers={
                    "Content-Disposition": "attachment; filename=tax_appeal_preliminary.pdf",
                    "Content-Length": str(len(pdf_bytes)),
                },
            )
        except Exception as exc:
            return jsonify({"status": "error", "message": str(exc)}), 500

    # ── POST /api/tax-appeal/expert-request ───────────────────────────────
    @app.route("/api/tax-appeal/expert-request", methods=["POST", "OPTIONS"])
    def tax_appeal_create_expert_request():
        if request.method == "OPTIONS":
            return jsonify({}), 200

        data = request.get_json(force=True, silent=True) or {}

        taxpayer_name = (data.get("taxpayer_name") or data.get("owner_name") or "").strip()
        taxpayer_phone = (data.get("taxpayer_phone") or data.get("phone") or "").strip()
        if not taxpayer_name or not taxpayer_phone:
            return jsonify({
                "status": "error",
                "message": "اسم المكلف ورقم الهاتف مطلوبان",
            }), 400

        request_id = _new_er_id()
        now        = datetime.utcnow().isoformat()

        rec: dict = {
            "request_id":               request_id,
            "created_at":               now,
            "updated_at":               now,
            "approval_status":          "draft_only",
            "appeal_report_available":  False,
            "source_page":              "tax_appeal",
            "taxpayer_name":            taxpayer_name,
            "taxpayer_phone":           taxpayer_phone,
            "taxpayer_email":           data.get("taxpayer_email") or data.get("email") or "",
            # Indexed fields for fast list display (duplicated from payload)
            "property_type":            data.get("property_type") or data.get("asset_type") or "",
            "tax_mode":                 data.get("tax_type") or data.get("tax_mode") or "",
            "district":                 data.get("district") or data.get("city") or "",
            "tax_assessment_basis_date": data.get("tax_assessment_basis_date") or "",
            "notice_received_date":     data.get("notice_received_date") or "",
            "government_tax_amount":    data.get("government_claim_value") or data.get("tax_government_claim") or 0,
            "expected_saving":          data.get("expected_saving") or 0,
            "payload_json":             json.dumps(data, ensure_ascii=False),
        }

        # Generate expert workbook (internal — path not returned to user)
        wb_available = False
        try:
            from tax_appeal_workbook_builder import _create_tax_appeal_workbook
            from tax_appeal_field_mapping import load_mapping_records as _load_fm_wb
            _create_tax_appeal_workbook(
                request_id, rec,
                mapping_records=_load_fm_wb(request_id),
            )
            wb_available = True
        except Exception:
            pass

        _persist_er(rec)

        return jsonify({
            "status":          "success",
            "request_id":      request_id,
            "approval_status": "draft_only",
            "workbook_ready":  wb_available,
            "message": (
                f"تم تسجيل طلب المراجعة الضريبية بنجاح. رقم الطلب: {request_id}. "
                "سيقوم الخبير بمراجعة البيانات."
            ),
        }), 201

    # ── GET /api/tax-appeal/expert-requests (admin) ────────────────────────
    @app.route("/api/tax-appeal/expert-requests", methods=["GET"])
    @require_auth
    def tax_appeal_list_expert_requests():
        try:
            limit  = min(int(request.args.get("limit",  50)), 200)
            offset = max(int(request.args.get("offset",  0)),   0)
        except ValueError:
            limit, offset = 50, 0
        records = _read_all_er(limit=limit, offset=offset)
        summaries = []
        for r in records:
            # Compute deadline_status from context if available, otherwise summarise
            payload = r.get("payload_json") or {}
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload = {}
            try:
                from tax_appeal_context import _build_tax_appeal_context
                ctx = _build_tax_appeal_context(payload)
                deadline_status = ctx.get("deadline_status", "")
            except Exception:
                deadline_status = ""
            summaries.append({
                "request_id":               r.get("request_id"),
                "created_at":               r.get("created_at"),
                "updated_at":               r.get("updated_at"),
                "approval_status":          r.get("approval_status"),
                "appeal_report_available":  r.get("appeal_report_available", False),
                "taxpayer_name":            r.get("taxpayer_name"),
                "property_type":            r.get("property_type"),
                "tax_mode":                 r.get("tax_mode"),
                "district":                 r.get("district"),
                "tax_assessment_basis_date": r.get("tax_assessment_basis_date"),
                "notice_received_date":     r.get("notice_received_date"),
                "deadline_status":          deadline_status,
                "government_tax_amount":    r.get("government_tax_amount"),
                "expected_saving":          r.get("expected_saving"),
            })
        return jsonify({"status": "ok", "count": len(summaries), "requests": summaries})

    # ── GET /api/tax-appeal/expert-requests/<id> (protected) ──────────────
    @app.route("/api/tax-appeal/expert-requests/<request_id>", methods=["GET"])
    @require_auth
    def tax_appeal_get_expert_request(request_id: str):
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400
        rec = _read_er(request_id)
        if not rec:
            return jsonify({"status": "error", "message": "الطلب غير موجود"}), 404
        # Build rich context from stored payload
        payload = rec.get("payload_json") or {}
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}
        context_summary: dict = {}
        try:
            from tax_appeal_context import _build_tax_appeal_context
            from tax_appeal_evidence_routes import load_evidence_records
            from tax_appeal_field_mapping import load_mapping_records as _load_fm
            ev_records = load_evidence_records(request_id)
            fm_records = _load_fm(request_id)
            ctx = _build_tax_appeal_context(
                payload,
                evidence_records=ev_records,
                mapping_records=fm_records,
            )
            context_summary = {
                "tax_assessment_basis_date":         ctx.get("tax_assessment_basis_date"),
                "tax_assessment_basis_date_display": ctx.get("tax_assessment_basis_date_display"),
                "notice_received_date":              ctx.get("notice_received_date"),
                "deadline_date":                     ctx.get("deadline_date"),
                "deadline_status":                   ctx.get("deadline_status"),
                "deadline_days_remaining":           ctx.get("deadline_days_remaining"),
                "missing_documents":                 ctx.get("missing_documents"),
                "data_gap_status":                   ctx.get("data_gap_status"),
                "five_methods_summary":              ctx.get("five_methods_summary"),
                "reconciliation_summary":            ctx.get("reconciliation_summary"),
                "committee_arguments":               ctx.get("committee_arguments"),
                "source_registry":                   ctx.get("source_registry"),
                "recommendation_summary":            ctx.get("recommendation_summary"),
                "evidence_summary":                  ctx.get("evidence_summary"),
                "field_mapping_summary":             ctx.get("field_mapping_summary"),
                "source_linked_inputs":              ctx.get("source_linked_inputs"),
                "extraction_summary":                ctx.get("extraction_summary"),
            }
        except Exception:
            pass
        safe = {k: v for k, v in rec.items() if k not in ("payload_json",)}
        safe["context"] = context_summary
        # Attach safe evidence list (no internal paths)
        try:
            from tax_appeal_evidence_routes import load_evidence_records, _ev_safe
            ev_list = load_evidence_records(request_id)
            safe["evidence"] = [_ev_safe(e) for e in ev_list]
            safe["evidence_count"] = len(ev_list)
        except Exception:
            safe["evidence"] = []
            safe["evidence_count"] = 0
        return jsonify({"status": "ok", "request": safe})

    # ── POST /api/tax-appeal/expert-requests/<id>/review ──────────────────
    @app.route("/api/tax-appeal/expert-requests/<request_id>/review", methods=["POST"])
    @require_auth
    def tax_appeal_review_expert_request(request_id: str):
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400
        rec = _read_er(request_id)
        if not rec:
            return jsonify({"status": "error", "message": "الطلب غير موجود"}), 404

        data           = request.get_json(force=True, silent=True) or {}
        new_status     = (data.get("approval_status") or "").strip()
        current_status = rec.get("approval_status", "draft_only")

        if new_status not in _VALID_ER_STATUSES:
            return jsonify({
                "status": "error",
                "message": f"حالة غير صالحة: {new_status!r}. الحالات المقبولة: {sorted(_VALID_ER_STATUSES)}",
            }), 400

        # appeal_report_generated can only be set by the report generation endpoint
        if new_status == "appeal_report_generated":
            return jsonify({
                "status": "error",
                "message": (
                    "لا يمكن تعيين حالة 'appeal_report_generated' يدويًا. "
                    "تُعيَّن تلقائيًا فقط بعد إنشاء ملف تقرير الطعن عبر نقطة النهاية المخصصة."
                ),
            }), 422

        allowed = _ALLOWED_TRANSITIONS.get(current_status, set())
        if new_status not in allowed:
            return jsonify({
                "status":  "error",
                "message": f"الانتقال من {current_status!r} إلى {new_status!r} غير مسموح به.",
            }), 422

        updates = {
            "approval_status":   new_status,
            "updated_at":        datetime.utcnow().isoformat(),
            "reviewed_at":       datetime.utcnow().isoformat(),
            "reviewer_notes":    data.get("notes") or "",
            "expert_notes":      data.get("expert_notes") or "",
            "missing_documents_note": data.get("missing_documents_note") or "",
            "decision_reason":   data.get("decision_reason") or "",
        }
        _update_er(request_id, updates)
        return jsonify({"status": "ok", "request_id": request_id, "approval_status": new_status})

    # ── POST /api/tax-appeal/expert-requests/<id>/expert-draft-pdf ────────
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/expert-draft-pdf",
        methods=["POST"],
    )
    @require_auth
    def tax_appeal_generate_expert_draft_pdf(request_id: str):
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400
        rec = _read_er(request_id)
        if not rec:
            return jsonify({"status": "error", "message": "الطلب غير موجود"}), 404

        current_status = rec.get("approval_status", "")
        if current_status not in ("approved_pending_appeal_report", "appeal_report_generated"):
            return jsonify({
                "status":  "error",
                "message": (
                    f"لا يمكن إنشاء مسودة الطعن في الحالة الحالية: {current_status!r}. "
                    "يجب أن تكون الحالة 'approved_pending_appeal_report' أولًا."
                ),
            }), 422

        try:
            payload: dict = rec.get("payload_json") or {}
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload = {}

            from tax_appeal_context import _build_tax_appeal_context
            from pdf_renderer import cairo_font_css, render_pdf_from_html
            from jinja2 import Environment, FileSystemLoader
            from tax_appeal_evidence_routes import load_evidence_records as _load_ev
            from tax_appeal_field_mapping import load_mapping_records as _load_fm2

            payload["request_id"] = request_id
            ctx = _build_tax_appeal_context(
                payload,
                evidence_records=_load_ev(request_id),
                mapping_records=_load_fm2(request_id),
            )

            _TMPL_DIR = Path(__file__).parent / "templates" / "pdf"
            env = Environment(loader=FileSystemLoader(str(_TMPL_DIR)), autoescape=False)
            tmpl = env.get_template("tax_appeal_expert_draft.html")
            html_str = tmpl.render(font_css_block=cairo_font_css(), **ctx)
            pdf_bytes = render_pdf_from_html(html_str)

            pdf_dir = _ER_REPORTS / request_id
            pdf_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = pdf_dir / "tax_appeal_expert_draft.pdf"
            pdf_path.write_bytes(pdf_bytes)

            # Advance status to appeal_report_generated.
            # Playwright's sync API can interact with nest_asyncio and cause the
            # JSONL store to be zeroed out during PDF generation.  If _read_er
            # no longer finds the record after rendering, re-persist it directly
            # rather than silently losing the update.
            _er_updates = {
                "approval_status":            "appeal_report_generated",
                "appeal_report_available":    True,
                "appeal_report_generated_at": datetime.utcnow().isoformat(),
                "updated_at":                datetime.utcnow().isoformat(),
            }
            if _read_er(request_id) is None:
                # Store was wiped during PDF rendering — re-persist with updates.
                rec.update(_er_updates)
                _ER_BASE.mkdir(parents=True, exist_ok=True)
                _persist_er(rec)
            else:
                _update_er(request_id, _er_updates)

            return jsonify({
                "status":     "ok",
                "request_id": request_id,
                "approval_status": "appeal_report_generated",
                "pdf_size_bytes": len(pdf_bytes),
            })
        except Exception as exc:
            return jsonify({"status": "error", "message": str(exc)}), 500

    # ── GET /api/tax-appeal/expert-requests/<id>/expert-draft-pdf ─────────
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/expert-draft-pdf",
        methods=["GET"],
    )
    @require_auth
    def tax_appeal_download_expert_draft_pdf(request_id: str):
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400
        pdf_path = _ER_REPORTS / request_id / "tax_appeal_expert_draft.pdf"
        if not pdf_path.exists():
            return jsonify({"status": "error", "message": "مسودة الطعن غير متاحة بعد"}), 404
        from flask import send_file
        return send_file(
            str(pdf_path),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"tax_appeal_expert_draft_{request_id}.pdf",
        )

    # ── GET /api/tax-appeal/expert-requests/<id>/expert-workbook ──────────
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/expert-workbook",
        methods=["GET"],
    )
    @require_auth
    def tax_appeal_download_expert_workbook(request_id: str):
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400
        wb_path = _ER_WB_DIR / request_id / f"tax_appeal_review_{request_id}.xlsx"
        if not wb_path.exists():
            return jsonify({"status": "error", "message": "ملف العمل الخبيري غير متاح"}), 404
        from flask import send_file
        return send_file(
            str(wb_path),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"tax_appeal_review_{request_id}.xlsx",
        )

    # ── POST /api/tax-appeal/expert-requests (plural alias) ───────────────
    # Alias so both /expert-request and /expert-requests work for creation.
    @app.route("/api/tax-appeal/expert-requests", methods=["POST", "OPTIONS"])
    def tax_appeal_create_expert_request_plural():
        return tax_appeal_create_expert_request()

    # ── POST /api/tax-appeal/expert-requests/<id>/appeal-report ───────────
    # Alias for expert-draft-pdf generation (task-spec-compliant name).
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/appeal-report",
        methods=["POST"],
    )
    @require_auth
    def tax_appeal_generate_appeal_report(request_id: str):
        return tax_appeal_generate_expert_draft_pdf(request_id)

    # ── GET /api/tax-appeal/expert-requests/<id>/appeal-report ────────────
    # Alias download endpoint.
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/appeal-report",
        methods=["GET"],
    )
    @require_auth
    def tax_appeal_download_appeal_report(request_id: str):
        return tax_appeal_download_expert_draft_pdf(request_id)

    # ── Evidence upload & source approval routes ───────────────────────────
    from tax_appeal_evidence_routes import register_evidence_routes
    register_evidence_routes(app, require_auth)

    # ── Field mapping routes ───────────────────────────────────────────────
    from tax_appeal_field_mapping import register_field_mapping_routes
    register_field_mapping_routes(app, require_auth)

    # ── Extraction readiness routes ────────────────────────────────────────
    from tax_appeal_extraction_routes import register_extraction_routes
    register_extraction_routes(app, require_auth)

    # ── OCR Pilot routes ───────────────────────────────────────────────────
    from tax_appeal_ocr_routes import register_ocr_routes
    register_ocr_routes(app, require_auth)
