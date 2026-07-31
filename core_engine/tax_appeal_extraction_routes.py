# -*- coding: utf-8 -*-
"""
tax_appeal_extraction_routes.py — Human Extraction Queue for Tax Appeal Evidence.

Workflow:
  Expert approves evidence → selects extraction template → manually enters field values
  → submits for review → expert confirms → creates field mappings from extraction.

Endpoints (all JWT-protected):
  GET  /api/tax-appeal/expert-requests/<id>/extraction-templates
  GET  /api/tax-appeal/expert-requests/<id>/evidence/<ev_id>/extraction-template
  GET  /api/tax-appeal/expert-requests/<id>/extractions
  POST /api/tax-appeal/expert-requests/<id>/evidence/<ev_id>/extractions
  POST /api/tax-appeal/expert-requests/<id>/extractions/<ex_id>/submit
  POST /api/tax-appeal/expert-requests/<id>/extractions/<ex_id>/confirm
  POST /api/tax-appeal/expert-requests/<id>/extractions/<ex_id>/reject
  POST /api/tax-appeal/expert-requests/<id>/extractions/<ex_id>/create-mappings

Storage:
  instance/tax_appeal_extractions/<request_id>/extractions.jsonl

Rules:
  - No OCR, no Qdrant, no RAG, no automatic value extraction.
  - All field values are manually entered by the expert.
  - extraction_mode = human_manual_only by default.
  - production_ready = True only after expert_confirmed AND evidence approved_as_source.
  - Rejected/superseded extractions cannot create mappings.
  - internal_file_path never returned in API responses.
  - No extracted values auto-fill or mutate payload_json.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── Storage ───────────────────────────────────────────────────────────────────

_EX_BASE = Path(__file__).parent / "instance" / "tax_appeal_extractions"
_EX_BASE.mkdir(parents=True, exist_ok=True)

# ── Regex validators ──────────────────────────────────────────────────────────

_ER_ID_RE = re.compile(r"^TAXER-[0-9A-F]{8}$")
_EV_ID_RE = re.compile(r"^EV-[0-9A-F]{8}$")
_EX_ID_RE = re.compile(r"^EX-[0-9A-F]{8}$")

# ── Status constants ──────────────────────────────────────────────────────────

_EX_STATUSES = {
    "not_started", "draft", "submitted_for_review",
    "expert_confirmed", "rejected", "superseded",
}
_EX_TRANSITIONS: dict[str, set[str]] = {
    "not_started":         {"draft"},
    "draft":               {"submitted_for_review", "rejected"},
    "submitted_for_review": {"expert_confirmed", "rejected", "draft"},
    "expert_confirmed":    {"superseded"},
    "rejected":            {"draft"},
    "superseded":          set(),
}

_EV_ACTIVE_STATUSES = {"uploaded", "needs_review", "approved_for_report", "approved_as_source"}
_EV_INACTIVE_STATUSES = {"rejected", "superseded"}


# ── ID generators ─────────────────────────────────────────────────────────────

def _new_ex_id() -> str:
    return "EX-" + uuid.uuid4().hex[:8].upper()


# ── JSONL helpers ─────────────────────────────────────────────────────────────

def _ex_dir(request_id: str) -> Path:
    d = _EX_BASE / request_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _ex_file(request_id: str) -> Path:
    return _ex_dir(request_id) / "extractions.jsonl"


def _persist_ex(request_id: str, rec: dict) -> None:
    f = _ex_file(request_id)
    with open(f, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _update_ex(request_id: str, extraction_id: str, updates: dict) -> None:
    f = _ex_file(request_id)
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
                if rec.get("extraction_id") == extraction_id:
                    rec.update(updates)
                lines.append(json.dumps(rec, ensure_ascii=False))
            except json.JSONDecodeError:
                lines.append(raw)
    with open(f, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def _read_ex(request_id: str, extraction_id: str) -> Optional[dict]:
    f = _ex_file(request_id)
    if not f.exists():
        return None
    with open(f, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
                if rec.get("extraction_id") == extraction_id:
                    return rec
            except json.JSONDecodeError:
                continue
    return None


def load_extraction_records(request_id: str) -> list[dict]:
    """Load all extraction records for a request. Public — used by context/workbook builders."""
    f = _ex_file(request_id)
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


def _safe_ex(rec: dict) -> dict:
    """Strip internal_file_path from an extraction record before returning to caller."""
    return {k: v for k, v in rec.items() if k != "internal_file_path"}


# ── Extraction summary builder ────────────────────────────────────────────────

def build_extraction_summary(extraction_records: list[dict]) -> dict:
    """Return extraction_summary dict for context/PDF/Excel."""
    total       = len(extraction_records)
    draft       = sum(1 for e in extraction_records if e.get("extraction_status") == "draft")
    submitted   = sum(1 for e in extraction_records if e.get("extraction_status") == "submitted_for_review")
    confirmed   = sum(1 for e in extraction_records if e.get("extraction_status") == "expert_confirmed")
    rejected    = sum(1 for e in extraction_records if e.get("extraction_status") == "rejected")
    prod_ready  = sum(1 for e in extraction_records if e.get("production_ready", False))
    ocr_ready   = sum(1 for e in extraction_records if e.get("future_ocr_ready", False))
    qdrant_ready= sum(1 for e in extraction_records if e.get("future_qdrant_ready", False))
    expert_req  = sum(1 for e in extraction_records if e.get("extraction_status") == "submitted_for_review")
    return {
        "total_extractions":          total,
        "draft_extractions":          draft,
        "submitted_extractions":      submitted,
        "confirmed_extractions":      confirmed,
        "rejected_extractions":       rejected,
        "production_ready_extractions": prod_ready,
        "future_ocr_ready_count":     ocr_ready,
        "future_qdrant_ready_count":  qdrant_ready,
        "expert_actions_required":    expert_req,
        "ocr_active_now":             False,
        "qdrant_active_now":          False,
        "rag_active_now":             False,
        "no_automatic_value_extraction": True,
        "note": (
            "جميع القيم مدخلة يدويًا بواسطة الخبير. "
            "لا يتم استخراج أي قيمة تلقائيًا من محتوى الملفات في هذا الإصدار."
        ),
    }


# ── Route registration ────────────────────────────────────────────────────────

def register_extraction_routes(app, require_auth) -> None:
    """Register /api/tax-appeal/expert-requests/<id>/extraction* routes."""
    from flask import jsonify, request as flask_request

    from tax_appeal_extraction_templates import (
        _get_extraction_template_catalogue,
        _get_template_for_evidence_type,
    )
    from tax_appeal_evidence_routes import load_evidence_records, _read_ev

    # ── GET /api/tax-appeal/expert-requests/<rid>/extraction-templates ─────
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/extraction-templates",
        methods=["GET"],
    )
    @require_auth
    def tax_appeal_get_extraction_templates(request_id: str):
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400
        catalogue = _get_extraction_template_catalogue()
        return jsonify({"ok": True, "templates": catalogue, "count": len(catalogue)}), 200

    # ── GET /api/tax-appeal/expert-requests/<rid>/evidence/<ev_id>/extraction-template ─
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/evidence/<evidence_id>/extraction-template",
        methods=["GET"],
    )
    @require_auth
    def tax_appeal_get_evidence_extraction_template(request_id: str, evidence_id: str):
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400
        if not _EV_ID_RE.fullmatch(evidence_id):
            return jsonify({"status": "error", "message": "معرّف المستند غير صالح"}), 400
        ev = _read_ev(request_id, evidence_id)
        if not ev:
            return jsonify({"status": "error", "message": "المستند غير موجود"}), 404
        ev_type  = ev.get("evidence_type", "")
        template = _get_template_for_evidence_type(ev_type)
        return jsonify({
            "ok":             True,
            "evidence_id":    evidence_id,
            "evidence_type":  ev_type,
            "template":       template,
            "has_template":   template is not None,
        }), 200

    # ── GET /api/tax-appeal/expert-requests/<rid>/extractions ─────────────
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/extractions",
        methods=["GET"],
    )
    @require_auth
    def tax_appeal_list_extractions(request_id: str):
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400
        records = load_extraction_records(request_id)
        safe    = [_safe_ex(r) for r in records]
        summary = build_extraction_summary(records)
        return jsonify({
            "ok":         True,
            "extractions": safe,
            "count":      len(safe),
            "summary":    summary,
        }), 200

    # ── POST /api/tax-appeal/expert-requests/<rid>/evidence/<ev_id>/extractions ─
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/evidence/<evidence_id>/extractions",
        methods=["POST"],
    )
    @require_auth
    def tax_appeal_create_extraction(request_id: str, evidence_id: str):
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400
        if not _EV_ID_RE.fullmatch(evidence_id):
            return jsonify({"status": "error", "message": "معرّف المستند غير صالح"}), 400

        # Validate evidence exists and is active
        ev = _read_ev(request_id, evidence_id)
        if not ev:
            return jsonify({"status": "error", "message": "المستند غير موجود"}), 404
        ev_status = ev.get("status", "")
        if ev_status in _EV_INACTIVE_STATUSES:
            return jsonify({
                "status":  "error",
                "message": f"لا يمكن إنشاء استخراج لمستند بحالة: {ev_status}",
            }), 422

        body         = flask_request.get_json(silent=True) or {}
        template_id  = (body.get("template_id") or "").strip()
        ev_type      = ev.get("evidence_type", "")
        now          = datetime.utcnow().isoformat()
        extraction_id = _new_ex_id()

        # Resolve template
        from tax_appeal_extraction_templates import (
            EXTRACTION_TEMPLATES_BY_ID,
            _get_template_for_evidence_type,
        )
        if template_id and template_id in EXTRACTION_TEMPLATES_BY_ID:
            tmpl = EXTRACTION_TEMPLATES_BY_ID[template_id]
        else:
            tmpl = _get_template_for_evidence_type(ev_type)

        # Values — manually supplied only; no auto-extraction
        raw_values   = body.get("extracted_values") or {}
        if not isinstance(raw_values, dict):
            raw_values = {}
        # Validate: must be plain key→string/number/None; reject nested objects
        clean_values: dict = {}
        for k, v in raw_values.items():
            if isinstance(v, (str, int, float, bool)) or v is None:
                clean_values[str(k)] = v

        # Determine production_ready
        is_approved_as_source = ev_status == "approved_as_source"

        rec: dict = {
            "extraction_id":       extraction_id,
            "request_id":          request_id,
            "evidence_id":         evidence_id,
            "evidence_type":       ev_type,
            "template_id":         tmpl["template_id"] if tmpl else None,
            "extraction_status":   "draft",
            "extraction_mode":     "human_manual_only",
            "extracted_values":    clean_values,
            "extracted_by":        body.get("extracted_by") or "expert",
            "extracted_at":        now,
            "reviewed_by":         None,
            "reviewed_at":         None,
            "review_status":       "pending",
            "expert_notes":        body.get("expert_notes") or "",
            "validation_warnings": [],
            "linked_mapping_ids":  [],
            "source_registry_id":  ev.get("source_registry_id") or None,
            "production_ready":    False,
            "future_ocr_ready":    tmpl["future_ocr_ready"] if tmpl else False,
            "future_qdrant_ready": tmpl["future_qdrant_ready"] if tmpl else False,
            "ocr_active_now":      False,
            "qdrant_active_now":   False,
            "rag_active_now":      False,
            "audit_log": [
                {
                    "action":     "created",
                    "timestamp":  now,
                    "by":         body.get("extracted_by") or "expert",
                    "note":       "مسودة استخراج أُنشئت يدويًا",
                }
            ],
        }
        _persist_ex(request_id, rec)
        return jsonify({
            "ok":          True,
            "extraction":  _safe_ex(rec),
            "message":     "تم إنشاء مسودة الاستخراج. أدخل القيم وأرسلها للمراجعة.",
        }), 201

    # ── POST /api/tax-appeal/expert-requests/<rid>/extractions/<ex_id>/submit ─
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/extractions/<extraction_id>/submit",
        methods=["POST"],
    )
    @require_auth
    def tax_appeal_submit_extraction(request_id: str, extraction_id: str):
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400
        if not _EX_ID_RE.fullmatch(extraction_id):
            return jsonify({"status": "error", "message": "معرّف الاستخراج غير صالح"}), 400

        rec = _read_ex(request_id, extraction_id)
        if not rec:
            return jsonify({"status": "error", "message": "سجل الاستخراج غير موجود"}), 404
        if rec.get("extraction_status") not in ("draft", "submitted_for_review"):
            return jsonify({
                "status":  "error",
                "message": "يمكن الإرسال للمراجعة من حالة مسودة فقط",
            }), 422

        body = flask_request.get_json(silent=True) or {}
        now  = datetime.utcnow().isoformat()

        # Optionally update values on submit
        raw_values = body.get("extracted_values")
        if raw_values and isinstance(raw_values, dict):
            clean: dict = {}
            for k, v in raw_values.items():
                if isinstance(v, (str, int, float, bool)) or v is None:
                    clean[str(k)] = v
            rec["extracted_values"] = clean

        audit = rec.get("audit_log") or []
        audit.append({"action": "submitted", "timestamp": now, "by": "expert", "note": "أُرسل للمراجعة"})
        updates = {
            "extraction_status": "submitted_for_review",
            "review_status":     "awaiting_expert_review",
            "expert_notes":      body.get("expert_notes") or rec.get("expert_notes") or "",
            "audit_log":         audit,
            "extracted_values":  rec.get("extracted_values") or {},
        }
        _update_ex(request_id, extraction_id, updates)
        rec.update(updates)
        return jsonify({
            "ok":        True,
            "extraction": _safe_ex(rec),
            "message":   "تم إرسال الاستخراج للمراجعة.",
        }), 200

    # ── POST /api/tax-appeal/expert-requests/<rid>/extractions/<ex_id>/confirm ─
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/extractions/<extraction_id>/confirm",
        methods=["POST"],
    )
    @require_auth
    def tax_appeal_confirm_extraction(request_id: str, extraction_id: str):
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400
        if not _EX_ID_RE.fullmatch(extraction_id):
            return jsonify({"status": "error", "message": "معرّف الاستخراج غير صالح"}), 400

        rec = _read_ex(request_id, extraction_id)
        if not rec:
            return jsonify({"status": "error", "message": "سجل الاستخراج غير موجود"}), 404
        if rec.get("extraction_status") != "submitted_for_review":
            return jsonify({
                "status":  "error",
                "message": "يمكن تأكيد الاستخراج من حالة مُرسَل للمراجعة فقط",
            }), 422

        body = flask_request.get_json(silent=True) or {}
        now  = datetime.utcnow().isoformat()

        # Check evidence status for production_ready
        ev             = _read_ev(request_id, rec.get("evidence_id", ""))
        ev_status      = (ev or {}).get("status", "")
        production_ready = ev_status == "approved_as_source"

        audit = rec.get("audit_log") or []
        audit.append({
            "action": "confirmed", "timestamp": now, "by": "expert",
            "note": body.get("expert_notes") or "تأكيد الخبير",
        })
        updates = {
            "extraction_status": "expert_confirmed",
            "review_status":     "expert_confirmed",
            "reviewed_by":       "expert",
            "reviewed_at":       now,
            "expert_notes":      body.get("expert_notes") or rec.get("expert_notes") or "",
            "production_ready":  production_ready,
            "audit_log":         audit,
        }
        _update_ex(request_id, extraction_id, updates)
        rec.update(updates)
        return jsonify({
            "ok":              True,
            "extraction":      _safe_ex(rec),
            "production_ready": production_ready,
            "message": (
                "تم تأكيد الاستخراج — جاهز للربط بالحقول."
                if production_ready else
                "تم التأكيد — غير إنتاجي حتى يُعتمد المستند كمصدر (approved_as_source)."
            ),
        }), 200

    # ── POST /api/tax-appeal/expert-requests/<rid>/extractions/<ex_id>/reject ─
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/extractions/<extraction_id>/reject",
        methods=["POST"],
    )
    @require_auth
    def tax_appeal_reject_extraction(request_id: str, extraction_id: str):
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400
        if not _EX_ID_RE.fullmatch(extraction_id):
            return jsonify({"status": "error", "message": "معرّف الاستخراج غير صالح"}), 400

        rec = _read_ex(request_id, extraction_id)
        if not rec:
            return jsonify({"status": "error", "message": "سجل الاستخراج غير موجود"}), 404
        if rec.get("extraction_status") in ("rejected", "superseded", "expert_confirmed"):
            return jsonify({
                "status":  "error",
                "message": "لا يمكن رفض هذا الاستخراج بحالته الحالية",
            }), 422

        body = flask_request.get_json(silent=True) or {}
        rejection_notes = (body.get("rejection_notes") or body.get("expert_notes") or "").strip()
        if not rejection_notes:
            return jsonify({
                "status":  "error",
                "message": "سبب الرفض مطلوب (rejection_notes)",
            }), 400

        now   = datetime.utcnow().isoformat()
        audit = rec.get("audit_log") or []
        audit.append({
            "action": "rejected", "timestamp": now, "by": "expert",
            "note": rejection_notes,
        })
        updates = {
            "extraction_status": "rejected",
            "review_status":     "rejected",
            "reviewed_by":       "expert",
            "reviewed_at":       now,
            "expert_notes":      rejection_notes,
            "production_ready":  False,
            "audit_log":         audit,
        }
        _update_ex(request_id, extraction_id, updates)
        rec.update(updates)
        return jsonify({
            "ok":        True,
            "extraction": _safe_ex(rec),
            "message":   "تم رفض الاستخراج.",
        }), 200

    # ── POST /api/tax-appeal/expert-requests/<rid>/extractions/<ex_id>/create-mappings ─
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/extractions/<extraction_id>/create-mappings",
        methods=["POST"],
    )
    @require_auth
    def tax_appeal_create_mappings_from_extraction(request_id: str, extraction_id: str):
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400
        if not _EX_ID_RE.fullmatch(extraction_id):
            return jsonify({"status": "error", "message": "معرّف الاستخراج غير صالح"}), 400

        rec = _read_ex(request_id, extraction_id)
        if not rec:
            return jsonify({"status": "error", "message": "سجل الاستخراج غير موجود"}), 404

        ex_status = rec.get("extraction_status", "")
        if ex_status in ("rejected", "superseded"):
            return jsonify({
                "status":  "error",
                "message": "لا يمكن إنشاء روابط حقول من استخراج مرفوض أو مُستبدل",
            }), 422
        if ex_status != "expert_confirmed":
            return jsonify({
                "status":  "error",
                "message": "يجب تأكيد الاستخراج من الخبير قبل إنشاء روابط الحقول",
            }), 422

        extracted_values = rec.get("extracted_values") or {}
        if not extracted_values:
            return jsonify({
                "status":  "error",
                "message": "لا توجد قيم مستخرجة لإنشاء روابط حقول",
            }), 422

        evidence_id  = rec.get("evidence_id", "")
        ev           = _read_ev(request_id, evidence_id)
        evidence_type = rec.get("evidence_type", "")

        # Load template for label/type lookup
        from tax_appeal_extraction_templates import (
            EXTRACTION_TEMPLATES_BY_ID,
            _get_template_for_evidence_type,
        )
        tmpl_id = rec.get("template_id")
        tmpl    = (
            EXTRACTION_TEMPLATES_BY_ID.get(tmpl_id)
            if tmpl_id else
            _get_template_for_evidence_type(evidence_type)
        )
        field_meta: dict[str, dict] = {}
        if tmpl:
            for f in tmpl.get("fields", []):
                field_meta[f["field_key"]] = f

        # Build field group lookup from field catalogue
        try:
            from tax_appeal_field_mapping import FIELD_CATALOGUE as _FC
            _field_group_map: dict[str, str] = {
                f["field_key"]: f.get("group", "other") for f in _FC
            }
        except Exception:
            _field_group_map = {}

        # Delegate to field mapping module — create draft mappings
        try:
            from tax_appeal_field_mapping import _persist_fm, _new_fm_id, _detect_conflict
            from tax_appeal_routes import _read_er
        except ImportError as ie:
            return jsonify({
                "status":  "error",
                "message": f"خطأ داخلي في الاستيراد: {ie}",
            }), 500

        er = _read_er(request_id)
        if not er:
            return jsonify({"status": "error", "message": "طلب الخبير غير موجود"}), 404

        now            = datetime.utcnow().isoformat()
        created_ids:   list[str] = []
        skipped_fields: list[str] = []

        for fkey, fval in extracted_values.items():
            if fval is None or str(fval).strip() == "":
                skipped_fields.append(fkey)
                continue

            fm_id      = _new_fm_id()
            fm_meta    = field_meta.get(fkey, {})
            label_ar   = fm_meta.get("label_ar", fkey)
            value_type = fm_meta.get("value_type", "text")

            # Detect conflict with existing payload
            _pj = er.get("payload_json")
            payload = (json.loads(_pj) if _pj else None) or er
            cf = _detect_conflict(
                request_id         = request_id,
                mapping_id         = fm_id,
                field_key          = fkey,
                mapped_value       = str(fval),
                evidence_id        = evidence_id,
                source_registry_id = rec.get("source_registry_id") or "",
                payload            = payload,
            )

            fm_rec: dict = {
                "mapping_id":           fm_id,
                "request_id":           request_id,
                "evidence_id":          evidence_id,
                "evidence_type":        evidence_type,
                "extraction_id":        extraction_id,
                "mapped_field_key":     fkey,
                "mapped_field_label_ar": label_ar,
                "mapped_field_group":   _field_group_map.get(fkey, "other"),
                "mapped_value":         str(fval),
                "mapped_value_type":    value_type,
                "value_origin":         "approved_source_manual_mapping",
                "source_registry_id":   rec.get("source_registry_id") or "",
                "mapping_status":       "needs_review",
                "expert_confirmed":     False,
                "expert_reviewed_at":   None,
                "conflict_id":          cf.get("conflict_id") if cf else None,
                "conflict_status":      cf.get("conflict_status") if cf else "no_conflict",
                "report_usage_allowed": False,
                "production_ready":     False,
                "expert_notes":         "",
                "created_at":           now,
                "updated_at":           now,
            }
            _persist_fm(request_id, fm_rec)
            created_ids.append(fm_id)

        # Update extraction record with linked mapping IDs
        existing_ids = rec.get("linked_mapping_ids") or []
        all_ids      = list(existing_ids) + created_ids
        audit        = rec.get("audit_log") or []
        audit.append({
            "action":    "create_mappings",
            "timestamp": now,
            "by":        "expert",
            "note":      f"أُنشئ {len(created_ids)} ربط حقول من الاستخراج",
        })
        _update_ex(request_id, extraction_id, {
            "linked_mapping_ids": all_ids,
            "audit_log":          audit,
        })

        return jsonify({
            "ok":              True,
            "created_mapping_ids": created_ids,
            "skipped_fields":  skipped_fields,
            "count":           len(created_ids),
            "message": (
                f"تم إنشاء {len(created_ids)} ربط حقول من الاستخراج. "
                "جميع الروابط في حالة needs_review — يلزم تأكيد الخبير. "
                "لم يتم تطبيق أي قيمة تلقائيًا على السياق."
            ),
        }), 201
