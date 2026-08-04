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

from request_limits import accepted_uploaded_files

_MAX_FILE_COUNT = 5

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


# ── Template / approval helpers ────────────────────────────────────────
# _get_template_name_safe moved to reporting_pdf_builders; re-exported here.
from reporting_pdf_builders import _get_template_name_safe  # noqa: E402


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


# ── PDF builders (moved to reporting_pdf_builders) ──────────────────────────────
# Compatibility re-exports — names unchanged; _srr.* access still works.
from reporting_pdf_builders import (  # noqa: E402
    _TMPL_DIR,
    _build_draft_pdf,
    _build_simple_valuation_html,
    _build_simple_valuation_pdf_bytes,
    _build_certified_report_pdf,
)


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


# ── Internal expert workbook (moved to reporting_workbook_builder) ─────────────────
from reporting_workbook_builder import _create_expert_review_workbook  # noqa: F811,E402


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

        # Process document uploads — enforce 5-file limit on doc_* keys (Wave 4B1)
        _accepted_docs = accepted_uploaded_files(files, prefix="doc_")
        if len(_accepted_docs) > _MAX_FILE_COUNT:
            return jsonify({"error": "too_many_files", "maximum": _MAX_FILE_COUNT}), 413

        doc_errors: list[str] = []
        docs_saved: list[dict] = []
        for f in _accepted_docs:
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

        # Enforce 5-file limit on all file keys (Wave 4B1)
        _accepted_uploads = accepted_uploaded_files(files)
        if len(_accepted_uploads) > _MAX_FILE_COUNT:
            return jsonify({"error": "too_many_files", "maximum": _MAX_FILE_COUNT}), 413

        doc_errors: list[str] = []
        docs_saved: list[dict] = []

        for f in _accepted_uploads:
            try:
                role = request.form.get(f"role_{f.name}", "supporting_documents")
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
