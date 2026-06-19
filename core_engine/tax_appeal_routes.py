"""
tax_appeal_routes.py — Tax Appeal Backend Phase 1-3.

Public endpoints (no auth required — public contact form):
  POST /api/tax-appeal/leads          — create lead, upload docs, generate PDF
  GET  /api/tax-appeal/leads/<id>/pdf — download draft PDF (non-certified)

Admin endpoint:
  GET  /api/tax-appeal/leads          — list leads (requires auth)

Storage (non-public, under core_engine/tax_appeal/):
  leads.jsonl
  uploads/<lead_id>/<doc_id><ext>
  reports/<lead_id>/tax_screening_draft.pdf
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path

# ── Storage directories ───────────────────────────────────────────────────────

_BASE       = Path(__file__).parent / "tax_appeal"
_LEADS_FILE = _BASE / "leads.jsonl"
_UPLOADS    = _BASE / "uploads"
_REPORTS    = _BASE / "reports"

for _d in (_BASE, _UPLOADS, _REPORTS):
    _d.mkdir(parents=True, exist_ok=True)

# ── Constants ─────────────────────────────────────────────────────────────────

_ALLOWED_EXT = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx", ".xls", ".xlsx"}
_MAX_BYTES   = 10 * 1024 * 1024                 # 10 MB per file
_LEAD_ID_RE  = re.compile(r"^TAX-[0-9A-F]{8}$")

_DISCLAIMER = (
    "هذا التقرير مبدئي وغير معتمد، ولا يُعد طعنًا رسميًا أو تقرير خبير معتمد، "
    "ولا يستخدم أمام الجهات الرسمية أو القضائية أو التمويلية قبل مراجعة واعتماد "
    "خبير التقييم المختص."
)


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

        # Upload documents
        docs_meta: list  = []
        doc_errors: list = []
        for key in files:
            fo = files[key]
            if not fo or not fo.filename:
                continue
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
