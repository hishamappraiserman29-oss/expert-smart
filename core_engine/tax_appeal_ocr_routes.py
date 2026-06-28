# -*- coding: utf-8 -*-
"""
tax_appeal_ocr_routes.py — OCR Pilot endpoints for Tax Appeal Evidence.

Endpoints (all JWT-protected):
  POST /api/tax-appeal/expert-requests/<id>/evidence/<ev_id>/ocr
  GET  /api/tax-appeal/expert-requests/<id>/ocr-jobs
  GET  /api/tax-appeal/expert-requests/<id>/ocr-jobs/<ocr_job_id>
  POST /api/tax-appeal/expert-requests/<id>/ocr-jobs/<ocr_job_id>/create-extraction-draft
  POST /api/tax-appeal/expert-requests/<id>/ocr-jobs/<ocr_job_id>/reject

Storage:
  instance/tax_appeal_ocr_jobs/<request_id>/ocr_jobs.jsonl
  instance/tax_appeal_ocr_raw/<request_id>/<ocr_job_id>.txt    (raw text, expert-only, never in API)

Rules:
  - No internal file paths in API responses
  - production_ready = False for all OCR results
  - external_api_used = False always
  - qdrant_used = False always
  - rag_used = False always
  - OCR raw text is expert-only; ordinary users cannot access
  - Evidence must belong to the request and not be rejected/superseded
  - Extraction drafts from OCR are NOT confirmed and NOT production-ready
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── Storage ───────────────────────────────────────────────────────────────────

_OCR_JOB_BASE = Path(__file__).parent / "instance" / "tax_appeal_ocr_jobs"
_OCR_RAW_BASE = Path(__file__).parent / "instance" / "tax_appeal_ocr_raw"
_EX_BASE      = Path(__file__).parent / "instance" / "tax_appeal_extractions"

for _d in (_OCR_JOB_BASE, _OCR_RAW_BASE, _EX_BASE):
    _d.mkdir(parents=True, exist_ok=True)

# ── Regex validators ──────────────────────────────────────────────────────────

_ER_ID_RE  = re.compile(r"^(?:TAXER|QA)-[0-9A-F]{8}$")
_EV_ID_RE  = re.compile(r"^EV-[0-9A-F]{8}$")
_OCR_ID_RE = re.compile(r"^OCR-[0-9A-F]{8}$")
_EX_ID_RE  = re.compile(r"^EX-[0-9A-F]{8}$")

# ── Status constants ──────────────────────────────────────────────────────────

_OCR_STATUSES = {"queued", "running", "completed", "failed", "unsupported", "cancelled"}
_REVIEW_STATUSES = {"not_reviewed", "needs_human_review", "reviewed", "rejected"}
_EV_INACTIVE = {"rejected", "superseded"}

# ── Arabic display labels ─────────────────────────────────────────────────────

_FIELD_LABELS_AR: dict[str, str] = {
    "building_age":                 "عمر المبنى",
    "construction_year":            "سنة البناء",
    "area_m2":                      "المساحة (م²)",
    "annual_rental_value":          "القيمة الإيجارية السنوية",
    "government_rental_value":      "القيمة الإيجارية الحكومية",
    "government_tax_amount":        "الضريبة الحكومية",
    "tax_notice_number":            "رقم الإخطار الضريبي",
    "tax_period":                   "الفترة الضريبية",
    "property_type":                "نوع العقار",
    "city":                         "المدينة",
    "governorate":                  "المحافظة",
    "district":                     "الحي / المنطقة",
    "owner_name":                   "اسم المالك",
    "national_id":                  "الرقم القومي",
    "document_date":                "تاريخ المستند",
    "sale_price":                   "قيمة البيع",
    "license_number":               "رقم الترخيص",
    "license_date":                 "تاريخ الترخيص",
    "activity_type":                "نوع النشاط",
    "factory_area_m2":              "مساحة المصنع (م²)",
    "construction_cost_per_m2":     "تكلفة البناء لكل م²",
    "land_price_per_m2":            "سعر الأرض لكل م²",
    "reference_date":               "تاريخ المرجع",
    "reference_source":             "جهة المرجع",
}

_EVIDENCE_LABELS_AR: dict[str, str] = {
    "tax_notice_form3":                  "نموذج 3 إخطار ضريبي",
    "ownership_document":                "وثيقة تمليك",
    "activity_license":                  "ترخيص نشاط",
    "industrial_license":                "ترخيص صناعي",
    "factory_cost_guidance":             "جدول تكاليف المصانع",
    "ain_shams_factory_cost_reference":  "مرجع عين شمس لتكاليف المصانع",
    "nuca_land_price_reference":         "مرجع NUCA لأسعار الأراضي",
}

# ── ID generator ──────────────────────────────────────────────────────────────

def _new_ocr_id() -> str:
    return "OCR-" + uuid.uuid4().hex[:8].upper()

def _new_ex_id() -> str:
    return "EX-" + uuid.uuid4().hex[:8].upper()

# ── Storage helpers ───────────────────────────────────────────────────────────

def _ocr_dir(request_id: str) -> Path:
    d = _OCR_JOB_BASE / request_id
    d.mkdir(parents=True, exist_ok=True)
    return d

def _ocr_file(request_id: str) -> Path:
    return _ocr_dir(request_id) / "ocr_jobs.jsonl"

def _raw_dir(request_id: str) -> Path:
    d = _OCR_RAW_BASE / request_id
    d.mkdir(parents=True, exist_ok=True)
    return d

def _persist_ocr(request_id: str, rec: dict) -> None:
    with open(_ocr_file(request_id), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

def _update_ocr(request_id: str, ocr_job_id: str, updates: dict) -> None:
    f = _ocr_file(request_id)
    if not f.exists():
        return
    lines: list[str] = []
    with open(f, encoding="utf-8") as fh:
        for raw in fh:
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                lines.append(raw)
                continue
            if rec.get("ocr_job_id") == ocr_job_id:
                rec.update(updates)
            lines.append(json.dumps(rec, ensure_ascii=False))
    with open(f, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n" if lines else "")

def _read_ocr(request_id: str, ocr_job_id: str) -> Optional[dict]:
    f = _ocr_file(request_id)
    if not f.exists():
        return None
    with open(f, encoding="utf-8") as fh:
        for raw in fh:
            try:
                rec = json.loads(raw)
                if rec.get("ocr_job_id") == ocr_job_id:
                    return rec
            except json.JSONDecodeError:
                continue
    return None

def _list_ocr_jobs(request_id: str) -> list[dict]:
    f = _ocr_file(request_id)
    if not f.exists():
        return []
    jobs: list[dict] = []
    seen: set[str] = set()
    with open(f, encoding="utf-8") as fh:
        for raw in fh:
            try:
                rec = json.loads(raw)
                jid = rec.get("ocr_job_id", "")
                seen.discard(jid)
                seen.add(jid)
                jobs.append(rec)
            except json.JSONDecodeError:
                continue
    # Return latest record per job_id
    latest: dict[str, dict] = {}
    for j in jobs:
        latest[j.get("ocr_job_id", "")] = j
    return list(latest.values())

def _save_raw_text(request_id: str, ocr_job_id: str, text: str) -> str:
    """Save raw OCR text to expert-only storage. Returns storage key (not path)."""
    raw_file = _raw_dir(request_id) / f"{ocr_job_id}.txt"
    raw_file.write_text(text, encoding="utf-8")
    return f"ocr_raw/{request_id}/{ocr_job_id}.txt"   # opaque key, no real path

def _load_raw_text(request_id: str, ocr_job_id: str) -> str:
    raw_file = _raw_dir(request_id) / f"{ocr_job_id}.txt"
    if raw_file.exists():
        return raw_file.read_text(encoding="utf-8")
    return ""

# ── Extraction JSONL helpers (mirrors extraction_routes.py pattern) ──────────

def _ex_dir(request_id: str) -> Path:
    d = _EX_BASE / request_id
    d.mkdir(parents=True, exist_ok=True)
    return d

def _ex_file(request_id: str) -> Path:
    return _ex_dir(request_id) / "extractions.jsonl"

def _persist_ex(request_id: str, rec: dict) -> None:
    with open(_ex_file(request_id), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

# ── Safe serializers (strip internal paths) ───────────────────────────────────

def _ocr_safe(rec: dict) -> dict:
    """Return API-safe OCR job dict — never includes internal file paths."""
    return {
        "ocr_job_id":          rec.get("ocr_job_id"),
        "request_id":          rec.get("request_id"),
        "evidence_id":         rec.get("evidence_id"),
        "evidence_type":       rec.get("evidence_type"),
        "job_status":          rec.get("job_status"),
        "engine_name":         rec.get("engine_name"),
        "engine_available":    rec.get("engine_available"),
        "languages_requested": rec.get("languages_requested"),
        "languages_used":      rec.get("languages_used"),
        "page_count":          rec.get("page_count"),
        "text_length":         rec.get("text_length"),
        "confidence_overall":  rec.get("confidence_overall"),
        "raw_text_preview":    rec.get("raw_text_preview"),
        "warnings":            rec.get("warnings"),
        "errors":              rec.get("errors"),
        "created_at":          rec.get("created_at"),
        "completed_at":        rec.get("completed_at"),
        "created_by":          rec.get("created_by", "expert"),
        "review_status":       rec.get("review_status"),
        "production_ready":    False,   # always False
        "external_api_used":   False,   # always False
        "qdrant_used":         False,   # always False
        "rag_used":            False,   # always False
        "extraction_draft_id": rec.get("extraction_draft_id"),
        "candidates_count":    rec.get("candidates_count", 0),
    }


# ── Route registration ────────────────────────────────────────────────────────

def register_ocr_routes(app, require_auth) -> None:
    from flask import request, jsonify
    from tax_appeal_evidence_routes import load_evidence_records, _ev_safe   # type: ignore[import-not-found]
    from tax_appeal_ocr_engine import run_local_ocr, get_engine_info         # type: ignore[import-not-found]
    from tax_appeal_ocr_candidates import build_ocr_field_candidates         # type: ignore[import-not-found]

    # ── POST .../evidence/<ev_id>/ocr — run OCR job ───────────────────────
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/evidence/<evidence_id>/ocr",
        methods=["POST", "OPTIONS"],
    )
    @require_auth
    def tax_appeal_run_ocr(request_id: str, evidence_id: str):
        if request.method == "OPTIONS":
            return jsonify({}), 200
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400
        if not _EV_ID_RE.fullmatch(evidence_id):
            return jsonify({"status": "error", "message": "معرّف المستند غير صالح"}), 400

        # Load evidence record
        evs = load_evidence_records(request_id)
        ev = next((e for e in evs if e.get("evidence_id") == evidence_id), None)
        if ev is None:
            return jsonify({"status": "error", "message": "المستند غير موجود"}), 404
        if ev.get("status") in _EV_INACTIVE:
            return jsonify({
                "status": "error",
                "message": "لا يمكن تشغيل OCR على مستند مرفوض أو متجاوَز.",
            }), 400

        body = request.get_json(silent=True) or {}
        languages = body.get("languages", ["ara", "eng"])
        mode      = body.get("mode", "general")

        # Locate file path (internal — never returned in response)
        internal_path = ev.get("internal_file_path")
        if not internal_path:
            return jsonify({
                "status": "error",
                "message": "مسار ملف المستند غير متاح للـ OCR.",
            }), 400

        from pathlib import Path as _Path
        file_path = _Path(internal_path)
        if not file_path.exists():
            return jsonify({
                "status": "error",
                "message": "الملف المرتبط بالمستند غير موجود على الخادم.",
            }), 400

        mime_type = ev.get("mime_type", "application/octet-stream")
        now       = datetime.utcnow().isoformat()
        ocr_id    = _new_ocr_id()

        # Build initial job record
        job: dict = {
            "ocr_job_id":          ocr_id,
            "request_id":          request_id,
            "evidence_id":         evidence_id,
            "evidence_type":       ev.get("evidence_type"),
            "job_status":          "running",
            "engine_name":         None,
            "engine_available":    False,
            "languages_requested": languages,
            "languages_used":      [],
            "page_count":          0,
            "text_length":         0,
            "confidence_overall":  0.0,
            "raw_text_preview":    "",
            "raw_text_storage_key": None,
            "warnings":            [],
            "errors":              [],
            "created_at":          now,
            "completed_at":        None,
            "created_by":          "expert",
            "reviewed_by":         None,
            "review_status":       "needs_human_review",
            "production_ready":    False,
            "external_api_used":   False,
            "qdrant_used":         False,
            "rag_used":            False,
            "extraction_draft_id": None,
            "candidates_count":    0,
            "internal_file_path":  None,   # never stored/returned
            "audit_log":           [{"action": "created", "at": now, "by": "expert"}],
        }
        _persist_ocr(request_id, job)

        # Run OCR
        try:
            ocr_result = run_local_ocr(str(file_path), mime_type, languages, mode)
        except Exception as exc:
            ocr_result = {
                "engine_name": "error", "engine_available": False,
                "page_count": 0, "languages_used": [],
                "text": "", "confidence_overall": 0.0,
                "warnings": [], "errors": [str(exc)],
                "raw_text_preview": "",
            }

        raw_text = ocr_result.get("text", "")
        storage_key = None
        if raw_text.strip():
            storage_key = _save_raw_text(request_id, ocr_id, raw_text)

        # Build OCR candidates
        ev_type    = ev.get("evidence_type", "")
        candidates_result = build_ocr_field_candidates(raw_text, ev_type)
        cand_count = len(candidates_result.get("candidates", []))

        completed_at = datetime.utcnow().isoformat()
        has_errors   = bool(ocr_result.get("errors"))
        job_status   = "failed" if has_errors and not raw_text.strip() else "completed"
        if not ocr_result.get("engine_available") and not raw_text.strip():
            # Check if it's unsupported type
            if "غير مدعوم" in " ".join(ocr_result.get("errors", [])):
                job_status = "unsupported"
            else:
                job_status = "failed"

        updates: dict = {
            "job_status":          job_status,
            "engine_name":         ocr_result.get("engine_name"),
            "engine_available":    ocr_result.get("engine_available", False),
            "languages_used":      ocr_result.get("languages_used", []),
            "page_count":          ocr_result.get("page_count", 0),
            "text_length":         len(raw_text),
            "confidence_overall":  ocr_result.get("confidence_overall", 0.0),
            "raw_text_preview":    ocr_result.get("raw_text_preview", "")[:500],
            "raw_text_storage_key": storage_key,
            "warnings":            (ocr_result.get("warnings") or []) + (candidates_result.get("warnings") or []),
            "errors":              ocr_result.get("errors", []),
            "completed_at":        completed_at,
            "production_ready":    False,
            "external_api_used":   False,
            "qdrant_used":         False,
            "rag_used":            False,
            "candidates_count":    cand_count,
            "audit_log":           [
                {"action": "created",   "at": now,          "by": "expert"},
                {"action": "completed", "at": completed_at, "by": "system",
                 "note":  f"engine={ocr_result.get('engine_name')} status={job_status}"},
            ],
        }
        _update_ocr(request_id, ocr_id, updates)

        rec = _read_ocr(request_id, ocr_id) or {**job, **updates}
        return jsonify({"status": "ok", "ocr_job": _ocr_safe(rec)}), 201

    # ── GET .../ocr-jobs — list jobs for request ──────────────────────────
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/ocr-jobs",
        methods=["GET"],
    )
    @require_auth
    def tax_appeal_list_ocr_jobs(request_id: str):
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400
        jobs = _list_ocr_jobs(request_id)
        return jsonify({"status": "ok", "ocr_jobs": [_ocr_safe(j) for j in jobs]}), 200

    # ── GET .../ocr-jobs/<ocr_job_id> — get single job ───────────────────
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/ocr-jobs/<ocr_job_id>",
        methods=["GET"],
    )
    @require_auth
    def tax_appeal_get_ocr_job(request_id: str, ocr_job_id: str):
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400
        if not _OCR_ID_RE.fullmatch(ocr_job_id):
            return jsonify({"status": "error", "message": "معرّف مهمة OCR غير صالح"}), 400
        rec = _read_ocr(request_id, ocr_job_id)
        if rec is None:
            return jsonify({"status": "error", "message": "مهمة OCR غير موجودة"}), 404
        return jsonify({"status": "ok", "ocr_job": _ocr_safe(rec)}), 200

    # ── POST .../ocr-jobs/<ocr_job_id>/create-extraction-draft ────────────
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/ocr-jobs/<ocr_job_id>/create-extraction-draft",
        methods=["POST", "OPTIONS"],
    )
    @require_auth
    def tax_appeal_ocr_create_draft(request_id: str, ocr_job_id: str):
        if request.method == "OPTIONS":
            return jsonify({}), 200
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400
        if not _OCR_ID_RE.fullmatch(ocr_job_id):
            return jsonify({"status": "error", "message": "معرّف مهمة OCR غير صالح"}), 400

        job = _read_ocr(request_id, ocr_job_id)
        if job is None:
            return jsonify({"status": "error", "message": "مهمة OCR غير موجودة"}), 404
        if job.get("job_status") not in {"completed"}:
            return jsonify({
                "status": "error",
                "message": "يجب أن تكون مهمة OCR مكتملة قبل إنشاء مسودة الاستخراج.",
            }), 400
        if job.get("review_status") == "rejected":
            return jsonify({
                "status": "error",
                "message": "مهمة OCR مرفوضة — لا يمكن إنشاء مسودة استخراج.",
            }), 400

        # Load raw OCR text
        raw_text = _load_raw_text(request_id, ocr_job_id)

        # Build candidates
        ev_type = job.get("evidence_type", "")
        candidates_result = build_ocr_field_candidates(raw_text, ev_type)
        candidates = candidates_result.get("candidates", [])

        # Build extraction draft
        now   = datetime.utcnow().isoformat()
        ex_id = _new_ex_id()

        # Candidate fields become suggested values (not confirmed)
        suggested_values: dict = {
            c["field_key"]: {
                "candidate_value":     c["candidate_value"],
                "confidence":          c["confidence"],
                "needs_human_review":  True,
                "accepted_by_default": False,
                "extraction_method":   c.get("extraction_method"),
                "source_snippet":      c.get("source_snippet"),
            }
            for c in candidates
        }

        extraction_draft: dict = {
            "extraction_id":       ex_id,
            "request_id":          request_id,
            "evidence_id":         job.get("evidence_id"),
            "evidence_type":       ev_type,
            "template_id":         f"ocr_draft_{ev_type}",
            "extraction_status":   "draft",
            "extraction_mode":     "ocr_pilot",
            "ocr_active_now":      True,
            "qdrant_active_now":   False,
            "rag_active_now":      False,
            "external_api_used":   False,
            "production_ready":    False,
            "review_status":       "needs_human_review",
            "ocr_job_id":          ocr_job_id,
            "candidate_values":    suggested_values,
            "confirmed_values":    {},        # starts empty — expert must confirm
            "extracted_values":    suggested_values,   # alias for compatibility
            "created_at":          now,
            "created_by":          "ocr_pilot",
            "confirmed_by":        None,
            "confirmed_at":        None,
            "notes":               "مسودة OCR آلية — تتطلب مراجعة الخبير وتأكيد كل حقل قبل الاستخدام.",
            "no_automatic_value_extraction": False,   # OCR pilot active
        }
        _persist_ex(request_id, extraction_draft)

        # Link draft to OCR job
        _update_ocr(request_id, ocr_job_id, {
            "extraction_draft_id": ex_id,
            "review_status":       "needs_human_review",
        })

        return jsonify({
            "status": "ok",
            "extraction_draft": {
                "extraction_id":     ex_id,
                "extraction_status": "draft",
                "review_status":     "needs_human_review",
                "production_ready":  False,
                "ocr_job_id":        ocr_job_id,
                "candidates_count":  len(candidates),
                "confirmed_values":  {},
                "created_at":        now,
            },
        }), 201

    # ── POST .../ocr-jobs/<ocr_job_id>/reject ─────────────────────────────
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/ocr-jobs/<ocr_job_id>/reject",
        methods=["POST", "OPTIONS"],
    )
    @require_auth
    def tax_appeal_ocr_reject(request_id: str, ocr_job_id: str):
        if request.method == "OPTIONS":
            return jsonify({}), 200
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400
        if not _OCR_ID_RE.fullmatch(ocr_job_id):
            return jsonify({"status": "error", "message": "معرّف مهمة OCR غير صالح"}), 400

        job = _read_ocr(request_id, ocr_job_id)
        if job is None:
            return jsonify({"status": "error", "message": "مهمة OCR غير موجودة"}), 404

        body = request.get_json(silent=True) or {}
        reason = body.get("reason", "مرفوضة من قِبل الخبير")
        now    = datetime.utcnow().isoformat()

        _update_ocr(request_id, ocr_job_id, {
            "review_status": "rejected",
            "reviewed_by":   "expert",
            "audit_log":     (job.get("audit_log") or []) + [
                {"action": "rejected", "at": now, "by": "expert", "reason": reason}
            ],
        })

        return jsonify({
            "status": "ok",
            "ocr_job_id":    ocr_job_id,
            "review_status": "rejected",
        }), 200

    # ── GET .../ocr-engine-info — engine availability ─────────────────────
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/ocr-engine-info",
        methods=["GET"],
    )
    @require_auth
    def tax_appeal_ocr_engine_info(request_id: str):
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400
        info = get_engine_info()
        return jsonify({"status": "ok", "engine_info": info}), 200


# ── Public loader (used by context builder) ───────────────────────────────────

def load_ocr_jobs(request_id: str) -> list[dict]:
    """Load all OCR job records for a request. Safe to call even if no jobs exist."""
    return _list_ocr_jobs(request_id)


def load_ocr_extraction_drafts(request_id: str) -> list[dict]:
    """Load all OCR extraction drafts for a request. Safe to call even if none exist."""
    f = _ex_file(request_id)
    if not f.exists():
        return []
    drafts: dict[str, dict] = {}
    with open(f, encoding="utf-8") as fh:
        for raw in fh:
            try:
                rec = json.loads(raw)
                ex_id = rec.get("extraction_id", "")
                if ex_id and rec.get("extraction_mode") == "ocr_pilot":
                    drafts[ex_id] = rec
            except json.JSONDecodeError:
                continue
    return list(drafts.values())


def build_ocr_pilot_summary(ocr_jobs: list[dict]) -> dict:
    """Build the ocr_pilot_summary dict for context / PDF / Excel."""
    total     = len(ocr_jobs)
    completed = sum(1 for j in ocr_jobs if j.get("job_status") == "completed")
    failed    = sum(1 for j in ocr_jobs if j.get("job_status") == "failed")
    unsupp    = sum(1 for j in ocr_jobs if j.get("job_status") == "unsupported")
    drafts    = sum(1 for j in ocr_jobs if j.get("extraction_draft_id"))
    confirmed = 0   # not counted here; comes from extraction records

    any_engine = any(j.get("engine_available") for j in ocr_jobs)
    ocr_active = total > 0 and completed > 0

    warnings: list[str] = []
    if not any_engine and total > 0:
        warnings.append("محرك OCR المحلي غير متاح في هذه البيئة — الاستخراج يدوي فقط.")
    if completed > 0:
        warnings.append("نتائج OCR لا تعد مصدرًا معتمدًا إلا بعد مراجعة وتأكيد الخبير.")

    return {
        "ocr_active_now":                  ocr_active,
        "qdrant_active_now":               False,
        "rag_active_now":                  False,
        "external_api_used":               False,
        "total_ocr_jobs":                  total,
        "completed_ocr_jobs":              completed,
        "failed_ocr_jobs":                 failed,
        "unsupported_ocr_jobs":            unsupp,
        "extraction_drafts_created_from_ocr": drafts,
        "ocr_values_used_in_report":       0,   # always 0 until expert-confirmed & mapped
        "expert_confirmed_ocr_values":     confirmed,
        "production_ready_count":          0,   # always 0 for raw OCR
        "warnings":                        warnings,
    }


def build_ocr_suggested_fields(extraction_drafts: list[dict]) -> list[dict]:
    """
    Build a list of OCR-suggested field rows for display in preliminary/expert-draft reports.

    Rules enforced here:
    - Only draft (unconfirmed, unrejected) extraction records are included.
    - Every row: production_ready=False, needs_human_review=True, accepted_by_default=False.
    - Label is always "قراءة آلية مبدئية — غير معتمدة".
    - No internal paths, no raw_text_storage_key, no OCR raw text.
    """
    rows: list[dict] = []
    for draft in extraction_drafts:
        if draft.get("review_status") in {"reviewed", "rejected"}:
            continue
        if draft.get("extraction_status") != "draft":
            continue

        ev_type  = draft.get("evidence_type", "")
        ev_label = _EVIDENCE_LABELS_AR.get(ev_type, ev_type)
        ex_id    = draft.get("extraction_id", "")

        candidate_values: dict = (
            draft.get("candidate_values")
            or draft.get("extracted_values")
            or {}
        )

        for field_key, cv in candidate_values.items():
            if not isinstance(cv, dict):
                continue
            raw_value = cv.get("candidate_value") if cv.get("candidate_value") is not None else cv.get("value")
            if raw_value is None:
                continue

            confidence: float = float(cv.get("confidence", 0.5))
            if confidence >= 0.8:
                conf_label = "عالية"
            elif confidence >= 0.6:
                conf_label = "متوسطة"
            else:
                conf_label = "منخفضة"

            rows.append({
                "field_key":              field_key,
                "field_label_ar":         _FIELD_LABELS_AR.get(field_key, field_key),
                "ocr_value":              str(raw_value),
                "confidence":             confidence,
                "confidence_label_ar":    conf_label,
                "evidence_type":          ev_type,
                "evidence_type_label_ar": ev_label,
                "extraction_id":          ex_id,
                "is_preliminary":         True,
                "production_ready":       False,
                "needs_human_review":     True,
                "accepted_by_default":    False,
                "label_ar":               "قراءة آلية مبدئية — غير معتمدة",
            })
    return rows
