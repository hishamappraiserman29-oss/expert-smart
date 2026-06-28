"""
tax_appeal_evidence_routes.py — Evidence upload and source approval workflow.

Endpoints (all JWT-protected):
  POST   /api/tax-appeal/expert-requests/<id>/evidence                        — upload
  GET    /api/tax-appeal/expert-requests/<id>/evidence                        — list
  GET    /api/tax-appeal/expert-requests/<id>/evidence/<ev_id>/download       — download
  POST   /api/tax-appeal/expert-requests/<id>/evidence/<ev_id>/review         — review
  POST   /api/tax-appeal/expert-requests/<id>/evidence/<ev_id>/promote-source — promote
  POST   /api/tax-appeal/expert-requests/<id>/evidence/<ev_id>/supersede      — supersede

Storage:
  core_engine/instance/tax_appeal_evidence/<request_id>/evidence.jsonl
  core_engine/instance/tax_appeal_evidence/<request_id>/files/<safe_filename>
  core_engine/instance/tax_appeal_source_registry/<request_id>/sources.jsonl

Rules:
  - internal_file_path never returned in API responses
  - production_ready=True only when status=approved_as_source
  - Ordinary users cannot call these endpoints
  - No OCR, no Qdrant, no RAG, no automatic content parsing
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── Storage ───────────────────────────────────────────────────────────────────

_EVIDENCE_BASE = Path(__file__).parent / "instance" / "tax_appeal_evidence"
_SOURCE_REG_BASE = Path(__file__).parent / "instance" / "tax_appeal_source_registry"

for _d in (_EVIDENCE_BASE, _SOURCE_REG_BASE):
    _d.mkdir(parents=True, exist_ok=True)

# ── Regex validators ──────────────────────────────────────────────────────────

_EV_ID_RE = re.compile(r"^EV-[0-9A-F]{8}$")
_ER_ID_RE = re.compile(r"^TAXER-[0-9A-F]{8}$")

# ── File limits and allowed types ─────────────────────────────────────────────

_MAX_BYTES = 20 * 1024 * 1024   # 20 MB

_ALLOWED_EXTENSIONS: set[str] = {
    ".pdf", ".xlsx", ".xls", ".csv",
    ".jpg", ".jpeg", ".png", ".webp",
    ".txt", ".docx",
}

_BLOCKED_EXTENSIONS: set[str] = {
    ".exe", ".bat", ".cmd", ".ps1",
    ".js", ".html", ".php", ".sh",
    ".zip", ".tar", ".gz", ".7z", ".rar",
}

# ── Evidence type registry ────────────────────────────────────────────────────

EVIDENCE_TYPES: dict[str, str] = {
    "tax_notice_form3":                    "إشعار الضريبة — نموذج 3",
    "ownership_document":                  "وثيقة الملكية",
    "lease_contract":                      "عقد الإيجار",
    "building_permit":                     "ترخيص البناء",
    "occupancy_or_completion_certificate": "شهادة الإشغال أو الإنهاء",
    "activity_license":                    "ترخيص النشاط",
    "commercial_register":                 "السجل التجاري",
    "industrial_license":                  "الترخيص الصناعي",
    "land_allocation_document":            "وثيقة تخصيص الأرض",
    "area_statement":                      "بيان المساحة",
    "floor_plan":                          "مسقط الطابق",
    "property_photos":                     "صور العقار",
    "map_or_aerial_image":                 "خريطة أو صورة جوية",
    "market_comparables_excel":            "مقارنات السوق (Excel)",
    "rental_comparables_excel":            "مقارنات الإيجار (Excel)",
    "tax_comparables_excel":               "مقارنات الضريبة (Excel)",
    "factory_cost_guidance":               "مرشد تكلفة المصانع",
    "ain_shams_factory_cost_reference":    "مرجع تكلفة مصانع عين شمس",
    "nuca_land_price_reference":           "مرجع أسعار أراضي هيئة التعمير",
    "expert_note":                         "ملاحظة خبير",
    "legal_note":                          "ملاحظة قانونية",
    "other":                               "أخرى",
}

# ── Evidence status lifecycle ─────────────────────────────────────────────────

_EV_VALID_STATUSES: set[str] = {
    "uploaded", "needs_review", "approved_for_report",
    "approved_as_source", "rejected", "superseded",
}

_EV_TRANSITIONS: dict[str, set[str]] = {
    "uploaded":            {"needs_review", "rejected"},
    "needs_review":        {"approved_for_report", "approved_as_source", "rejected"},
    "approved_for_report": {"approved_as_source", "rejected", "superseded"},
    "approved_as_source":  {"rejected", "superseded"},
    "rejected":            {"needs_review"},
    "superseded":          set(),
}


# ── Storage helpers ───────────────────────────────────────────────────────────

def _ev_dir(request_id: str) -> Path:
    d = _EVIDENCE_BASE / request_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _ev_file(request_id: str) -> Path:
    return _ev_dir(request_id) / "evidence.jsonl"


def _ev_files_dir(request_id: str) -> Path:
    d = _ev_dir(request_id) / "files"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _new_ev_id() -> str:
    return "EV-" + uuid.uuid4().hex[:8].upper()


def _persist_ev(request_id: str, rec: dict) -> None:
    f = _ev_file(request_id)
    with open(f, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _update_ev(request_id: str, evidence_id: str, updates: dict) -> None:
    f = _ev_file(request_id)
    if not f.exists():
        return
    lines: list[str] = []
    with open(f, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
                if rec.get("evidence_id") == evidence_id:
                    rec.update(updates)
                lines.append(json.dumps(rec, ensure_ascii=False))
            except json.JSONDecodeError:
                lines.append(raw)
    with open(f, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def _read_ev(request_id: str, evidence_id: str) -> Optional[dict]:
    f = _ev_file(request_id)
    if not f.exists():
        return None
    with open(f, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
                if rec.get("evidence_id") == evidence_id:
                    return rec
            except json.JSONDecodeError:
                continue
    return None


def load_evidence_records(request_id: str) -> list[dict]:
    """Load all evidence records for a request. Public — used by context/workbook builders."""
    f = _ev_file(request_id)
    if not f.exists():
        return []
    rows: list[dict] = []
    with open(f, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rows.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    return rows


def load_source_registry_records(request_id: str) -> list[dict]:
    """Load promoted source registry records for a request."""
    f = _SOURCE_REG_BASE / request_id / "sources.jsonl"
    if not f.exists():
        return []
    rows: list[dict] = []
    with open(f, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rows.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    return rows


# ── Safe response builder ─────────────────────────────────────────────────────

def _ev_safe(rec: dict) -> dict:
    """Return public-safe evidence metadata — never includes internal_file_path."""
    return {
        "evidence_id":               rec.get("evidence_id"),
        "request_id":                rec.get("request_id"),
        "original_filename":         rec.get("original_filename"),
        "evidence_type":             rec.get("evidence_type"),
        "evidence_type_label_ar":    rec.get("evidence_type_label_ar"),
        "status":                    rec.get("status"),
        "source_status":             rec.get("source_status"),
        "production_ready":          rec.get("production_ready", False),
        "expert_review_required":    rec.get("expert_review_required", True),
        "approved_for_report":       rec.get("approved_for_report", False),
        "approved_as_source":        rec.get("approved_as_source", False),
        "source_registry_id":        rec.get("source_registry_id"),
        "uploaded_at":               rec.get("uploaded_at"),
        "uploaded_by_role":          rec.get("uploaded_by_role"),
        "file_size":                 rec.get("file_size"),
        "mime_type":                 rec.get("mime_type"),
        "document_date":             rec.get("document_date"),
        "document_issuer":           rec.get("document_issuer"),
        "document_reference_number": rec.get("document_reference_number"),
        "confidentiality_level":     rec.get("confidentiality_level"),
        "expert_reviewed_at":        rec.get("expert_reviewed_at"),
        "expert_review_notes":       rec.get("expert_review_notes"),
        "rejection_reason":          rec.get("rejection_reason"),
        "version":                   rec.get("version", 1),
        "supersedes_evidence_id":    rec.get("supersedes_evidence_id"),
        "metadata_notes":            rec.get("metadata_notes"),
    }


def _sanitize_ev_filename(name: str) -> str:
    name = os.path.basename(name)
    name = name.replace("..", "")
    safe = "".join(c for c in name if c.isalnum() or c in "._- ")
    return safe.strip() or "upload"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ── Route registration ────────────────────────────────────────────────────────

def register_evidence_routes(app, require_auth) -> None:
    """Register all /api/tax-appeal/expert-requests/<id>/evidence/* routes on *app*."""
    from flask import jsonify, request, send_file

    # ── POST .../evidence — upload ─────────────────────────────────────────
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/evidence",
        methods=["POST", "OPTIONS"],
    )
    @require_auth
    def tax_appeal_upload_evidence(request_id: str):
        if request.method == "OPTIONS":
            return jsonify({}), 200

        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400

        from tax_appeal_routes import _read_er
        if not _read_er(request_id):
            return jsonify({"status": "error", "message": "طلب الطعن غير موجود"}), 404

        file_obj = request.files.get("file")
        if not file_obj or not file_obj.filename:
            return jsonify({"status": "error", "message": "يجب رفع ملف"}), 400

        orig_name = _sanitize_ev_filename(file_obj.filename)
        ext = Path(orig_name).suffix.lower()

        if ext in _BLOCKED_EXTENSIONS:
            return jsonify({"status": "error", "message": f"صيغة الملف محظورة: {ext}"}), 400
        if ext not in _ALLOWED_EXTENSIONS:
            return jsonify({"status": "error", "message": f"صيغة الملف غير مدعومة: {ext}"}), 400

        data = file_obj.read()
        if len(data) == 0:
            return jsonify({"status": "error", "message": "الملف فارغ"}), 400
        if len(data) > _MAX_BYTES:
            return jsonify({"status": "error", "message": "حجم الملف يتجاوز 20 ميجابايت"}), 400

        mime = mimetypes.guess_type(orig_name)[0] or "application/octet-stream"
        sha256 = _sha256(data)

        ev_id = _new_ev_id()
        safe_name = ev_id + ext

        dest = _ev_files_dir(request_id) / safe_name
        dest.write_bytes(data)

        ev_type = request.form.get("evidence_type", "other")
        if ev_type not in EVIDENCE_TYPES:
            ev_type = "other"

        now = datetime.utcnow().isoformat()

        rec: dict = {
            "evidence_id":               ev_id,
            "request_id":                request_id,
            "original_filename":         orig_name,
            "safe_filename":             safe_name,
            "mime_type":                 mime,
            "file_size":                 len(data),
            "uploaded_at":               now,
            "uploaded_by_role":          "expert",
            "evidence_type":             ev_type,
            "evidence_type_label_ar":    EVIDENCE_TYPES[ev_type],
            "status":                    "needs_review",
            "source_status":             "مرفق قيد المراجعة — لا يستخدم كمصدر معتمد",
            "production_ready":          False,
            "expert_review_required":    True,
            "expert_reviewed_by":        None,
            "expert_reviewed_at":        None,
            "expert_review_notes":       None,
            "rejection_reason":          None,
            "approved_for_report":       False,
            "approved_as_source":        False,
            "source_registry_id":        None,
            "document_date":             request.form.get("document_date") or None,
            "document_issuer":           request.form.get("document_issuer") or None,
            "document_reference_number": request.form.get("document_reference_number") or None,
            "confidentiality_level":     "internal",
            "ordinary_user_visible":     False,
            "internal_file_path":        str(dest),
            "safe_download_available":   True,
            "sha256_hash":               sha256,
            "version":                   1,
            "supersedes_evidence_id":    None,
            "metadata_notes":            request.form.get("metadata_notes") or None,
        }

        _persist_ev(request_id, rec)

        return jsonify({"status": "ok", **_ev_safe(rec)}), 201

    # ── GET .../evidence — list ────────────────────────────────────────────
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/evidence",
        methods=["GET"],
    )
    @require_auth
    def tax_appeal_list_evidence(request_id: str):
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400

        from tax_appeal_routes import _read_er
        if not _read_er(request_id):
            return jsonify({"status": "error", "message": "طلب الطعن غير موجود"}), 404

        records = load_evidence_records(request_id)
        return jsonify({
            "status":     "ok",
            "request_id": request_id,
            "count":      len(records),
            "evidence":   [_ev_safe(r) for r in records],
        })

    # ── GET .../evidence/<ev_id>/download ─────────────────────────────────
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/evidence/<evidence_id>/download",
        methods=["GET"],
    )
    @require_auth
    def tax_appeal_download_evidence(request_id: str, evidence_id: str):
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400
        if not _EV_ID_RE.fullmatch(evidence_id):
            return jsonify({"status": "error", "message": "معرّف المستند غير صالح"}), 400

        rec = _read_ev(request_id, evidence_id)
        if not rec:
            return jsonify({"status": "error", "message": "المستند غير موجود"}), 404

        file_path = _ev_files_dir(request_id) / rec["safe_filename"]
        if not file_path.exists():
            return jsonify({"status": "error", "message": "الملف غير موجود على الخادم"}), 404

        return send_file(
            str(file_path),
            mimetype=rec.get("mime_type", "application/octet-stream"),
            as_attachment=True,
            download_name=rec.get("original_filename", rec["safe_filename"]),
        )

    # ── POST .../evidence/<ev_id>/review ──────────────────────────────────
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/evidence/<evidence_id>/review",
        methods=["POST"],
    )
    @require_auth
    def tax_appeal_review_evidence(request_id: str, evidence_id: str):
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400
        if not _EV_ID_RE.fullmatch(evidence_id):
            return jsonify({"status": "error", "message": "معرّف المستند غير صالح"}), 400

        rec = _read_ev(request_id, evidence_id)
        if not rec:
            return jsonify({"status": "error", "message": "المستند غير موجود"}), 404

        body = request.get_json(force=True, silent=True) or {}
        new_status = (body.get("status") or "").strip()

        if new_status and new_status not in _EV_VALID_STATUSES:
            return jsonify({"status": "error", "message": f"حالة غير معروفة: {new_status}"}), 400

        current = rec.get("status", "uploaded")

        if new_status and new_status != current:
            allowed = _EV_TRANSITIONS.get(current, set())
            if new_status not in allowed:
                return jsonify({
                    "status": "error",
                    "message": f"الانتقال من '{current}' إلى '{new_status}' غير مسموح",
                }), 422

        now = datetime.utcnow().isoformat()

        # Derive approval flags from new status
        approved_for_report = rec.get("approved_for_report", False)
        approved_as_source  = rec.get("approved_as_source", False)
        production_ready    = rec.get("production_ready", False)
        source_status       = rec.get("source_status", "")

        effective = new_status or current
        if effective == "approved_as_source":
            production_ready    = True
            approved_as_source  = True
            approved_for_report = True
            source_status = "مستند مرفق ومعتمد كمصدر بواسطة الخبير"
        elif effective == "approved_for_report":
            production_ready    = False
            approved_for_report = True
            source_status = "مستند مرفق ومراجع من الخبير — معتمد للتقرير"
        elif effective in ("rejected", "superseded"):
            production_ready    = False
            approved_for_report = False
            approved_as_source  = False
            source_status = "مستند مرفوض أو مُستبدل — غير مُستخدم"
        elif effective == "needs_review":
            source_status = "مرفق قيد المراجعة — لا يستخدم كمصدر معتمد"

        updates: dict = {
            "expert_reviewed_at":  now,
            "updated_at":          now,
            "expert_review_notes": body.get("expert_review_notes") or rec.get("expert_review_notes"),
            "rejection_reason":    body.get("rejection_reason")    or rec.get("rejection_reason"),
            "production_ready":    production_ready,
            "approved_for_report": approved_for_report,
            "approved_as_source":  approved_as_source,
            "source_status":       source_status,
        }
        if new_status:
            updates["status"] = new_status

        _update_ev(request_id, evidence_id, updates)
        updated = _read_ev(request_id, evidence_id)

        return jsonify({
            "status": "ok",
            **({"evidence": _ev_safe(updated)} if updated else {}),
        })

    # ── POST .../evidence/<ev_id>/promote-source ──────────────────────────
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/evidence/<evidence_id>/promote-source",
        methods=["POST"],
    )
    @require_auth
    def tax_appeal_promote_evidence_source(request_id: str, evidence_id: str):
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400
        if not _EV_ID_RE.fullmatch(evidence_id):
            return jsonify({"status": "error", "message": "معرّف المستند غير صالح"}), 400

        rec = _read_ev(request_id, evidence_id)
        if not rec:
            return jsonify({"status": "error", "message": "المستند غير موجود"}), 404

        if rec.get("status") != "approved_as_source":
            return jsonify({
                "status": "error",
                "message": "لا يمكن إدراجه كمصدر إلا إذا كان بحالة 'approved_as_source'",
            }), 422

        body = request.get_json(force=True, silent=True) or {}
        now = datetime.utcnow().isoformat()

        src_id = rec.get("source_registry_id") or ("SRC-" + uuid.uuid4().hex[:8].upper())

        source_rec: dict = {
            "source_registry_id":     src_id,
            "evidence_id":            evidence_id,
            "request_id":             request_id,
            "evidence_type":          rec.get("evidence_type"),
            "evidence_type_label_ar": rec.get("evidence_type_label_ar"),
            "source_status":          "مستند مرفق ومعتمد كمصدر بواسطة الخبير",
            "production_ready":       True,
            "expert_reviewed":        True,
            "source_quality_score":   body.get("source_quality_score"),
            "mapped_source_category": body.get("mapped_source_category", rec.get("evidence_type")),
            "used_in_methods":        body.get("used_in_methods", []),
            "source_document_type":   rec.get("evidence_type"),
            "source_limitations":     body.get("source_limitations", ""),
            "original_filename":      rec.get("original_filename"),
            "document_date":          rec.get("document_date"),
            "document_issuer":        rec.get("document_issuer"),
            "promoted_at":            now,
        }

        src_dir = _SOURCE_REG_BASE / request_id
        src_dir.mkdir(parents=True, exist_ok=True)
        src_file = src_dir / "sources.jsonl"
        with open(src_file, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(source_rec, ensure_ascii=False) + "\n")

        _update_ev(request_id, evidence_id, {
            "source_registry_id":   src_id,
            "promoted_to_source_at": now,
        })

        return jsonify({
            "status":           "ok",
            "source_registry_id": src_id,
            "evidence_id":      evidence_id,
            "source_status":    "مستند مرفق ومعتمد كمصدر بواسطة الخبير",
            "production_ready": True,
        })

    # ── POST .../evidence/<ev_id>/supersede ───────────────────────────────
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/evidence/<evidence_id>/supersede",
        methods=["POST"],
    )
    @require_auth
    def tax_appeal_supersede_evidence(request_id: str, evidence_id: str):
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400
        if not _EV_ID_RE.fullmatch(evidence_id):
            return jsonify({"status": "error", "message": "معرّف المستند غير صالح"}), 400

        rec = _read_ev(request_id, evidence_id)
        if not rec:
            return jsonify({"status": "error", "message": "المستند غير موجود"}), 404

        current = rec.get("status", "uploaded")
        if "superseded" not in _EV_TRANSITIONS.get(current, set()):
            return jsonify({
                "status": "error",
                "message": f"لا يمكن استبدال مستند بحالة '{current}'",
            }), 422

        body = request.get_json(force=True, silent=True) or {}
        now = datetime.utcnow().isoformat()

        _update_ev(request_id, evidence_id, {
            "status":              "superseded",
            "production_ready":    False,
            "approved_for_report": False,
            "approved_as_source":  False,
            "superseded_by":       body.get("superseded_by_evidence_id", ""),
            "expert_review_notes": body.get("expert_review_notes", ""),
            "updated_at":          now,
        })

        return jsonify({
            "status":        "ok",
            "evidence_id":   evidence_id,
            "new_status":    "superseded",
            "superseded_by": body.get("superseded_by_evidence_id", ""),
        })
