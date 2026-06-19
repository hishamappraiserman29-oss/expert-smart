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

import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path

# ── Storage directories ───────────────────────────────────────────────────────

_BASE     = Path(__file__).parent / "instance" / "requests"
_REQ_FILE = _BASE / "requests.jsonl"
_UPLOADS  = _BASE / "uploads"
_REPORTS  = _BASE / "reports"

for _d in (_BASE, _UPLOADS, _REPORTS):
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
    """Generate a non-certified draft PDF for any source page."""
    from fpdf import FPDF

    source_page = req.get("source_page", "")
    pdf_title   = _PDF_TITLES.get(source_page, "تقرير مبدئي استرشادي")

    pdf_dir  = _REPORTS / req["request_id"]
    pdf_dir.mkdir(parents=True, exist_ok=True)
    out_path = pdf_dir / "draft_report.pdf"

    # Resolve Cairo fonts (bundled with the project)
    _font_r = _font_b = None
    try:
        from reports.pdf.pdf_arabic import find_font
        _font_r = str(find_font("cairo-regular"))
        _font_b = str(find_font("cairo-bold"))
    except Exception:
        pass

    # Mutable container so inner class can read the final font name
    _fn = ["Arial"]

    class _DraftPDF(FPDF):
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

    pdf = _DraftPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)

    if _font_r:
        try:
            pdf.add_font("Cairo", style="",  fname=_font_r)
            pdf.add_font("Cairo", style="B", fname=_font_b or _font_r)
            _fn[0] = "Cairo"
        except Exception:
            pass

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
    pdf.cell(0, 11, _ar(pdf_title), align="C", new_x="LMARGIN", new_y="NEXT")
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

    # Request metadata
    _heading("بيانات الطلب")
    _row("رقم الطلب:",    req.get("request_id", ""))
    _row("تاريخ الإنشاء:", req.get("created_at", "")[:10] if req.get("created_at") else "")
    _row("المصدر:",        source_page)
    _row("نوع الطلب:",     req.get("request_kind", ""))
    _hr()

    # Contact
    _heading("بيانات التواصل")
    _row("الاسم:",         req.get("user_name", ""))
    _row("الهاتف:",        req.get("phone", ""))
    if req.get("email"):
        _row("البريد:",    req.get("email", ""))
    _hr()

    # Payload summary
    payload = req.get("payload_json") or {}
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            payload = {}

    if payload:
        _heading("ملخص البيانات")
        for k, v in list(payload.items())[:15]:
            if v:
                _row(str(k) + ":", str(v))
        _hr()

    # Summary / notes
    if req.get("summary"):
        _heading("ملاحظات المستخدم")
        pdf.set_font(fn, "", 10)
        pdf.multi_cell(0, 7, _ar(str(req["summary"])), align="R")
        _hr()

    # Attached documents
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

        _persist_request(req)

        return jsonify({
            "status":           "success",
            "request_id":       request_id,
            "source_page":      source_page,
            "request_kind":     request_kind,
            "message": (
                f"تم تسجيل الطلب بنجاح. رقم الطلب: {request_id}. سيتم التواصل معك قريبًا."
            ),
            "pdf_available":     pdf_available,
            "pdf_download_url":  pdf_download_url,
            "pdf_message":       pdf_message,
            "non_certified":     True,
            "documents_saved":   len(docs_saved),
            "document_errors":   doc_errors,
        }), 201

    # ── GET /api/expert-requests/<id> — Request details ───────────────────
    @app.route("/api/expert-requests/<request_id>", methods=["GET"])
    def expert_request_get(request_id: str):
        if not _REQUEST_ID_RE.match(request_id):
            return jsonify({"status": "error", "message": "رقم الطلب غير صالح"}), 400
        req = _read_request(request_id)
        if req is None:
            return jsonify({"status": "error", "message": "الطلب غير موجود"}), 404
        # Return safe subset (no internal paths)
        public = {k: v for k, v in req.items() if k != "draft_pdf_path"}
        return jsonify({"status": "ok", "request": public}), 200

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

        return send_file(
            str(pdf_path),
            mimetype="application/pdf",
            as_attachment=False,
            download_name=f"draft_report_{request_id}.pdf",
        )

    # ── GET /api/expert-requests — List requests (admin only) ─────────────
    @app.route("/api/expert-requests", methods=["GET"])
    @require_auth
    def expert_request_list():
        limit  = min(int(request.args.get("limit", 50)), 200)
        offset = int(request.args.get("offset", 0))
        rows   = _read_all_requests(limit=limit, offset=offset)
        # Strip internal paths from listing
        for r in rows:
            r.pop("draft_pdf_path", None)
        return jsonify({
            "status": "ok",
            "total":  len(rows),
            "requests": rows,
            "pagination": {"limit": limit, "offset": offset},
        }), 200
