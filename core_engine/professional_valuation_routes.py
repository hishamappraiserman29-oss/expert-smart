"""
professional_valuation_routes.py — Professional Valuation Backoffice Phase B + C.

Public endpoint (no auth required):
  POST /api/professional-valuation/requests              — client intake / create

Protected endpoints (JWT required):
  GET  /api/professional-valuation/workflow              — status + transition map
  GET  /api/professional-valuation/schema                — field definitions
  GET  /api/professional-valuation/requests              — list (dashboard)
  GET  /api/professional-valuation/requests/<id>         — full detail
  POST /api/professional-valuation/requests/<id>/transition — lifecycle move

Storage (never exposed in API responses):
  core_engine/instance/professional_valuation/requests.jsonl
  core_engine/instance/professional_valuation/events.jsonl

Phase C: evidence and source routes in professional_valuation_evidence_routes.py.
Certified report generation → later phases.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path

# ── Storage ───────────────────────────────────────────────────────────────────

_BASE        = Path(__file__).parent / "instance" / "professional_valuation"
_REQ_FILE    = _BASE / "requests.jsonl"
_EVENTS_FILE = _BASE / "events.jsonl"
_BASE.mkdir(parents=True, exist_ok=True)

# ── Status / transition model ─────────────────────────────────────────────────

_ALL_STATUSES: list[str] = [
    "draft_request", "submitted", "intake_review", "needs_documents",
    "evidence_review", "data_entry", "method_analysis", "expert_review",
    "peer_review_required", "peer_review_in_progress", "changes_requested",
    "approved_pending_signature", "signed_pending_certification",
    "certified_report_generated", "rejected", "archived",
]

_TERMINAL_STATUSES: frozenset[str] = frozenset({"certified_report_generated", "archived"})

_ALLOWED_TRANSITIONS: dict[str, set] = {
    "draft_request":                {"submitted"},
    "submitted":                    {"intake_review"},
    "intake_review":                {"needs_documents", "evidence_review", "rejected"},
    "needs_documents":              {"submitted", "rejected"},
    "evidence_review":              {"data_entry", "needs_documents", "rejected"},
    "data_entry":                   {"method_analysis"},
    "method_analysis":              {"expert_review"},
    "expert_review":                {"changes_requested", "peer_review_required", "rejected"},
    "changes_requested":            {"data_entry", "method_analysis", "expert_review"},
    "peer_review_required":         {"peer_review_in_progress"},
    "peer_review_in_progress":      {"changes_requested", "approved_pending_signature"},
    "approved_pending_signature":   {"signed_pending_certification"},
    "signed_pending_certification": {"certified_report_generated"},
    "certified_report_generated":   {"archived"},
    "rejected":                     {"archived"},
    "archived":                     set(),
}

_PVR_ID_RE = re.compile(r"^PVR-\d{8}-[0-9A-F]{4}$")

# ── Certification gate ────────────────────────────────────────────────────────

def _empty_gate_summary() -> dict:
    """Phase B fallback — used only when evidence module is not available."""
    return {
        "certification_ready":          False,
        "qa_data_cleared":              False,
        "real_sources_ready":           False,
        "mandatory_documents_ready":    False,
        "legal_due_diligence_ready":    False,
        "hbu_completed":                False,
        "methods_completed":            False,
        "reconciliation_completed":     False,
        "peer_review_completed":        False,
        "expert_signature_ready":       False,
        "blockers":                     ["Phase B — gates not evaluated"],
        "advisory_only_reason": (
            "Phase B request workflow only — certification gates are not complete."
        ),
    }


def _get_gate_summary(request_id: str, valuation_purpose: str = "") -> dict:
    """Return computed gate summary from Phase C/D/E state.
    certification_ready is always False in Phase B/C/D/E.
    """
    try:
        from professional_valuation_evidence_routes import compute_gate_summary
        gate = compute_gate_summary(request_id, valuation_purpose)
    except ImportError:
        gate = _empty_gate_summary()

    # Phase D: merge comparable readiness
    try:
        from professional_valuation_comparables import evaluate_comparable_readiness
        cr = evaluate_comparable_readiness(request_id, valuation_purpose)
        gate["comparables_ready"] = cr.get("certification_comparable_ready", False)
        gate["certification_ready"] = False
        if not gate["comparables_ready"]:
            blocker = "لا توجد مقارنات إنتاجية معتمدة."
            if blocker not in gate.get("blockers", []):
                gate.setdefault("blockers", []).append(blocker)
    except ImportError:
        gate.setdefault("comparables_ready", False)

    # Phase E: merge method analysis and reconciliation readiness
    try:
        from professional_valuation_methods import (
            evaluate_method_readiness_for_request,
            get_reconciliation_for_request,
        )
        mr = evaluate_method_readiness_for_request(request_id)
        gate["methods_completed"] = mr.get("methods_completed", False)
        recon = get_reconciliation_for_request(request_id)
        gate["reconciliation_completed"] = bool(
            recon and recon.get("weighted_value") is not None
        )
        gate["certification_ready"] = False  # always False in Phase E
        if not gate["methods_completed"]:
            blocker = "لا توجد طرق تقييم مكتملة ببيانات كافية."
            if blocker not in gate.get("blockers", []):
                gate.setdefault("blockers", []).append(blocker)
    except ImportError:
        gate.setdefault("methods_completed", False)
        gate.setdefault("reconciliation_completed", False)

    # Phase E addendum: preliminary approval readiness
    try:
        from professional_valuation_methods import get_preliminary_approval_for_request
        prelim = get_preliminary_approval_for_request(request_id)
        gate["preliminary_approval_ready"] = bool(prelim and prelim.get("preliminary_approval_ready"))
        gate["preliminary_use_allowed"]    = bool(prelim and prelim.get("preliminary_use_allowed"))
        gate["certified_use_allowed"]      = False
    except ImportError:
        gate.setdefault("preliminary_approval_ready", False)
        gate.setdefault("preliminary_use_allowed",    False)
        gate.setdefault("certified_use_allowed",      False)

    return gate


# ── Permission summary placeholder ────────────────────────────────────────────

def _permissions_summary(user_id: str | None = None) -> dict:
    return {
        "current_user_role":        "valuation_analyst",
        "can_edit_intake":          True,
        "can_transition":           True,
        "can_upload_evidence":      False,
        "can_approve_sources":      False,
        "can_generate_preliminary": False,
        "can_generate_certified":   False,
        "can_download_workbook":    False,
        "can_view_internal_notes":  True,
    }


# ── ID generation ─────────────────────────────────────────────────────────────

def _new_pvr_id() -> str:
    date_str = datetime.utcnow().strftime("%Y%m%d")
    suffix   = uuid.uuid4().hex[:4].upper()
    return f"PVR-{date_str}-{suffix}"


# ── Persistence helpers ───────────────────────────────────────────────────────

def _persist_pvr(rec: dict) -> None:
    with open(_REQ_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _update_pvr(request_id: str, updates: dict) -> None:
    if not _REQ_FILE.exists():
        return
    lines: list[str] = []
    with open(_REQ_FILE, encoding="utf-8") as fh:
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
    with open(_REQ_FILE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def _read_pvr(request_id: str) -> dict | None:
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


def _read_all_pvr(limit: int = 100, offset: int = 0) -> list[dict]:
    if not _REQ_FILE.exists():
        return []
    rows: list[dict] = []
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


def _append_event(
    request_id: str,
    actor: str,
    action: str,
    from_status: str,
    to_status: str,
    note: str = "",
    metadata: dict | None = None,
) -> None:
    event: dict = {
        "event_id":    "EVT-" + uuid.uuid4().hex[:8].upper(),
        "request_id":  request_id,
        "timestamp":   datetime.utcnow().isoformat(),
        "actor":       actor,
        "action":      action,
        "from_status": from_status,
        "to_status":   to_status,
        "note":        note,
        "metadata":    metadata or {},
    }
    with open(_EVENTS_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


def _read_events(request_id: str) -> list[dict]:
    if not _EVENTS_FILE.exists():
        return []
    events: list[dict] = []
    with open(_EVENTS_FILE, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                evt = json.loads(raw)
                if evt.get("request_id") == request_id:
                    events.append(evt)
            except json.JSONDecodeError:
                continue
    return events


# ── Response builders ─────────────────────────────────────────────────────────

def _safe_summary(rec: dict) -> dict:
    """Dashboard list item — no internal paths."""
    return {
        "request_id":                    rec.get("request_id", ""),
        "request_number":                rec.get("request_number", ""),
        "created_at":                    rec.get("created_at", ""),
        "updated_at":                    rec.get("updated_at", ""),
        "client_name":                   rec.get("client_name", ""),
        "property_title":                rec.get("property_title", ""),
        "property_type":                 rec.get("property_type", ""),
        "district":                      rec.get("district", ""),
        "valuation_purpose":             rec.get("valuation_purpose", ""),
        "status":                        rec.get("status", ""),
        "assigned_expert":               rec.get("assigned_expert", ""),
        "assigned_peer_reviewer":        rec.get("assigned_peer_reviewer", ""),
        "priority":                      rec.get("priority", "normal"),
        "certification_ready":           False,
        "missing_required_items_count":  len(rec.get("missing_required_items", [])),
        "source_quality_status":         rec.get("source_quality_status", "not_started"),
        "document_completeness_status":  rec.get("document_completeness_status", "not_started"),
        "report_outputs_count":          len(rec.get("report_outputs", [])),
    }


def _safe_detail(rec: dict) -> dict:
    """Full backoffice detail — no internal paths."""
    available = sorted(
        _ALLOWED_TRANSITIONS.get(rec.get("status", ""), set())
        - {"certified_report_generated"}
    )
    return {
        "request_id":                   rec.get("request_id", ""),
        "request_number":               rec.get("request_number", ""),
        "created_at":                   rec.get("created_at", ""),
        "updated_at":                   rec.get("updated_at", ""),
        "created_by":                   rec.get("created_by", ""),
        "client_name":                  rec.get("client_name", ""),
        "client_email":                 rec.get("client_email", ""),
        "client_phone":                 rec.get("client_phone", ""),
        "property_title":               rec.get("property_title", ""),
        "property_type":                rec.get("property_type", ""),
        "property_subtype":             rec.get("property_subtype", ""),
        "property_address":             rec.get("property_address", ""),
        "governorate":                  rec.get("governorate", ""),
        "city":                         rec.get("city", ""),
        "district":                     rec.get("district", ""),
        "valuation_purpose":            rec.get("valuation_purpose", ""),
        "basis_of_value":               rec.get("basis_of_value", ""),
        "intended_use":                 rec.get("intended_use", ""),
        "intended_users":               rec.get("intended_users", ""),
        "property_interest_valued":     rec.get("property_interest_valued", ""),
        "valuation_date":               rec.get("valuation_date", ""),
        "inspection_date":              rec.get("inspection_date", ""),
        "report_language":              rec.get("report_language", "ar"),
        "currency":                     rec.get("currency", "EGP"),
        "status":                       rec.get("status", ""),
        "assigned_expert":              rec.get("assigned_expert", ""),
        "assigned_peer_reviewer":       rec.get("assigned_peer_reviewer", ""),
        "priority":                     rec.get("priority", "normal"),
        "missing_required_items":       rec.get("missing_required_items", []),
        "source_quality_status":        rec.get("source_quality_status", "not_started"),
        "document_completeness_status": rec.get("document_completeness_status", "not_started"),
        "report_outputs":               rec.get("report_outputs", []),
        "internal_notes_count":         rec.get("internal_notes_count", 0),
        "ordinary_visible_summary":     rec.get("ordinary_visible_summary", ""),
        "peer_review_completed":        rec.get("peer_review_completed", False),
        "available_transitions":        available,
    }


# ── Transition validator ──────────────────────────────────────────────────────

def _validate_transition(
    current_status: str,
    target_status: str,
    record: dict,
    body: dict,
) -> tuple[bool, str, str]:
    """Validate a lifecycle transition.

    Returns (ok, error_code, arabic_message).
    error_code: certified_blocked | invalid_target | not_allowed | gate_blocked
    """
    # certified_report_generated is always blocked from the generic transition route
    if target_status == "certified_report_generated":
        return False, "certified_blocked", (
            "لا يمكن الوصول إلى 'certified_report_generated' عبر نقطة الانتقال العامة. "
            "يُخصص هذا لنقطة إصدار التقرير المعتمد في مرحلة لاحقة."
        )

    if target_status not in _ALL_STATUSES:
        return False, "invalid_target", (
            f"الحالة المستهدفة '{target_status}' غير معرّفة."
        )

    allowed = _ALLOWED_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        allowed_str = ", ".join(sorted(allowed)) if allowed else "لا يوجد"
        return False, "not_allowed", (
            f"الانتقال من '{current_status}' إلى '{target_status}' غير مسموح. "
            f"الانتقالات المتاحة من '{current_status}': {allowed_str}"
        )

    # Gate: approved_pending_signature requires peer_review_completed on record
    if target_status == "approved_pending_signature":
        if not record.get("peer_review_completed"):
            return False, "gate_blocked", (
                "لا يمكن الانتقال إلى 'approved_pending_signature' بدون إتمام مراجعة النظراء. "
                "يجب تعيين peer_review_completed=true على السجل أولاً."
            )

    # Gate: signed_pending_certification requires signature_gate_cleared in request body
    if target_status == "signed_pending_certification":
        if not body.get("signature_gate_cleared"):
            return False, "gate_blocked", (
                "لا يمكن الانتقال إلى 'signed_pending_certification' بدون بوابة التوقيع. "
                "يجب تمرير signature_gate_cleared=true في جسم الطلب "
                "(ستُتاح هذه البوابة عبر نقطة التوقيع في مرحلة لاحقة)."
            )

    # Gate: method_analysis requires basic intake data
    if target_status == "method_analysis":
        if not (record.get("valuation_purpose") and record.get("property_type")):
            return False, "gate_blocked", (
                "لا يمكن الانتقال إلى 'method_analysis' قبل توفر بيانات نطاق العمل الأساسية. "
                "يجب توفر valuation_purpose وproperty_type على السجل."
            )

    return True, "", ""


# ── Workflow and schema definitions ───────────────────────────────────────────

_WORKFLOW_DEF: dict = {
    "statuses": _ALL_STATUSES,
    "terminal_statuses": sorted(_TERMINAL_STATUSES),
    "transitions": {k: sorted(v) for k, v in _ALLOWED_TRANSITIONS.items()},
    "gate_requirements": {
        "approved_pending_signature": ["peer_review_completed (on record)"],
        "signed_pending_certification": ["signature_gate_cleared (in transition body)"],
        "method_analysis": ["valuation_purpose (on record)", "property_type (on record)"],
        "certified_report_generated": ["BLOCKED — use dedicated report generation endpoint"],
    },
    "phase_b_note": (
        "Phase B: request lifecycle only — "
        "evidence, source approval, and report generation in later phases."
    ),
}

_SCHEMA_DEF: dict = {
    "required_fields": [
        {"field": "client_name",      "type": "string", "label": "اسم العميل"},
        {"field": "property_type",    "type": "string", "label": "نوع العقار"},
        {"field": "valuation_purpose", "type": "string", "label": "غرض التقييم"},
    ],
    "location_requirement": "property_address OR (city or district) — at least one required",
    "optional_fields": [
        {"field": "client_email",            "type": "string"},
        {"field": "client_phone",            "type": "string"},
        {"field": "property_title",          "type": "string"},
        {"field": "property_subtype",        "type": "string"},
        {"field": "property_address",        "type": "string"},
        {"field": "governorate",             "type": "string"},
        {"field": "city",                    "type": "string"},
        {"field": "district",                "type": "string"},
        {"field": "basis_of_value",          "type": "string"},
        {"field": "intended_use",            "type": "string"},
        {"field": "intended_users",          "type": "string"},
        {"field": "property_interest_valued", "type": "string"},
        {"field": "valuation_date",          "type": "string (ISO 8601 date)"},
        {"field": "inspection_date",         "type": "string (ISO 8601 date)"},
        {"field": "report_language",         "type": "string", "default": "ar"},
        {"field": "currency",                "type": "string", "default": "EGP"},
        {"field": "priority", "type": "string", "enum": ["low", "normal", "high", "urgent"]},
    ],
    "id_format": "PVR-YYYYMMDD-XXXX",
    "storage_note": "JSONL file — internal path not exposed via API",
    "phase_b_note": (
        "Phase B field schema only — "
        "evidence and source fields added in Phase C."
    ),
}


# ── Route registration ────────────────────────────────────────────────────────

def register(app, require_auth, limiter=None) -> None:
    """Register /api/professional-valuation/* routes on *app*."""
    from flask import g, jsonify, request as flask_request

    # ── POST /api/professional-valuation/requests — Create (public) ────────
    @app.route("/api/professional-valuation/requests", methods=["POST"])
    def pvr_create():
        body = flask_request.get_json(force=True, silent=True) or {}

        client_name       = (body.get("client_name") or "").strip()
        property_type     = (body.get("property_type") or "").strip()
        valuation_purpose = (body.get("valuation_purpose") or "").strip()

        if not client_name:
            return jsonify({"ok": False, "error": "client_name مطلوب"}), 400
        if not property_type:
            return jsonify({"ok": False, "error": "property_type مطلوب"}), 400
        if not valuation_purpose:
            return jsonify({"ok": False, "error": "valuation_purpose مطلوب"}), 400

        property_address = (body.get("property_address") or "").strip()
        city             = (body.get("city") or "").strip()
        district         = (body.get("district") or "").strip()
        if not property_address and not (city or district):
            return jsonify({
                "ok":   False,
                "error": "يجب توفير property_address أو city/district على الأقل",
            }), 400

        now        = datetime.utcnow().isoformat()
        request_id = _new_pvr_id()

        rec: dict = {
            "request_id":               request_id,
            "request_number":           request_id,
            "created_at":               now,
            "updated_at":               now,
            "created_by":               "client",
            "status":                   "submitted",
            "client_name":              client_name,
            "client_email":             (body.get("client_email") or "").strip(),
            "client_phone":             (body.get("client_phone") or "").strip(),
            "property_title":           (body.get("property_title") or "").strip(),
            "property_type":            property_type,
            "property_subtype":         (body.get("property_subtype") or "").strip(),
            "property_address":         property_address,
            "governorate":              (body.get("governorate") or "").strip(),
            "city":                     city,
            "district":                 district,
            "valuation_purpose":        valuation_purpose,
            "basis_of_value":           (body.get("basis_of_value") or "").strip(),
            "intended_use":             (body.get("intended_use") or "").strip(),
            "intended_users":           (body.get("intended_users") or "").strip(),
            "property_interest_valued": (body.get("property_interest_valued") or "").strip(),
            "valuation_date":           (body.get("valuation_date") or "").strip(),
            "inspection_date":          (body.get("inspection_date") or "").strip(),
            "report_language":          (body.get("report_language") or "ar").strip(),
            "currency":                 (body.get("currency") or "EGP").strip(),
            "priority":                 (body.get("priority") or "normal").strip(),
            "assigned_expert":          "",
            "assigned_peer_reviewer":   "",
            "certification_gate_summary": _empty_gate_summary(),
            "missing_required_items":   [],
            "source_quality_status":    "not_started",
            "document_completeness_status": "not_started",
            "report_outputs":           [],
            "internal_notes_count":     0,
            "peer_review_completed":    False,
            "ordinary_visible_summary": (
                f"طلب تقييم مهني للعقار ({property_type}) بغرض {valuation_purpose}. "
                f"رقم الطلب: {request_id}. الحالة: مُقدَّم."
            ),
        }

        _persist_pvr(rec)
        _append_event(
            request_id=request_id,
            actor="client",
            action="create",
            from_status="",
            to_status="submitted",
            note="طلب جديد من العميل",
        )

        return jsonify({
            "ok":                    True,
            "request_id":            request_id,
            "request_number":        request_id,
            "status":                "submitted",
            "message":               (
                f"تم تسجيل طلب التقييم المهني بنجاح. رقم الطلب: {request_id}."
            ),
            "ordinary_visible_summary": rec["ordinary_visible_summary"],
        }), 201

    # ── GET /api/professional-valuation/workflow ───────────────────────────
    @app.route("/api/professional-valuation/workflow", methods=["GET"])
    @require_auth
    def pvr_workflow():
        return jsonify({"ok": True, "workflow": _WORKFLOW_DEF}), 200

    # ── GET /api/professional-valuation/schema ─────────────────────────────
    @app.route("/api/professional-valuation/schema", methods=["GET"])
    @require_auth
    def pvr_schema():
        return jsonify({"ok": True, "schema": _SCHEMA_DEF}), 200

    # ── GET /api/professional-valuation/requests — List (dashboard) ────────
    @app.route("/api/professional-valuation/requests", methods=["GET"])
    @require_auth
    def pvr_list():
        limit  = min(int(flask_request.args.get("limit", 50)), 200)
        offset = int(flask_request.args.get("offset", 0))

        rows = _read_all_pvr(limit=10000, offset=0)  # read all for filtering

        status_filter  = (flask_request.args.get("status") or "").strip()
        purpose_filter = (flask_request.args.get("valuation_purpose") or "").strip()
        ptype_filter   = (flask_request.args.get("property_type") or "").strip()
        expert_filter  = (flask_request.args.get("assigned_expert") or "").strip()
        q_filter       = (flask_request.args.get("q") or "").strip().lower()

        if status_filter:
            rows = [r for r in rows if r.get("status") == status_filter]
        if purpose_filter:
            rows = [r for r in rows if r.get("valuation_purpose") == purpose_filter]
        if ptype_filter:
            rows = [r for r in rows if r.get("property_type") == ptype_filter]
        if expert_filter:
            rows = [r for r in rows if r.get("assigned_expert") == expert_filter]
        if q_filter:
            rows = [
                r for r in rows
                if q_filter in (r.get("client_name") or "").lower()
                or q_filter in (r.get("property_title") or "").lower()
                or q_filter in (r.get("request_id") or "").lower()
            ]

        total = len(rows)
        paged = rows[offset: offset + limit]
        items = [_safe_summary(r) for r in paged]

        return jsonify({
            "ok":         True,
            "total":      total,
            "requests":   items,
            "pagination": {"limit": limit, "offset": offset},
        }), 200

    # ── GET /api/professional-valuation/requests/<id> — Detail ────────────
    @app.route("/api/professional-valuation/requests/<request_id>", methods=["GET"])
    @require_auth
    def pvr_detail(request_id: str):
        if not _PVR_ID_RE.match(request_id):
            return jsonify({"ok": False, "error": "رقم الطلب غير صالح"}), 400
        rec = _read_pvr(request_id)
        if rec is None:
            return jsonify({"ok": False, "error": "الطلب غير موجود"}), 404

        user_id = getattr(g, "user_id", None)
        valuation_purpose = rec.get("valuation_purpose", "")

        return jsonify({
            "ok":      True,
            "request": _safe_detail(rec),
            "workflow": {
                "current_status": rec.get("status"),
                "available_transitions": sorted(
                    _ALLOWED_TRANSITIONS.get(rec.get("status", ""), set())
                    - {"certified_report_generated"}
                ),
                "is_terminal": rec.get("status") in _TERMINAL_STATUSES,
            },
            "certification_gate_summary": _get_gate_summary(request_id, valuation_purpose),
            "missing_required_items":    rec.get("missing_required_items", []),
            "event_log":                 _read_events(request_id),
            "permissions_summary":       _permissions_summary(user_id),
            "available_actions":         sorted(
                _ALLOWED_TRANSITIONS.get(rec.get("status", ""), set())
                - {"certified_report_generated"}
            ),
        }), 200

    # ── POST /api/professional-valuation/requests/<id>/transition ──────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/transition",
        methods=["POST"],
    )
    @require_auth
    def pvr_transition(request_id: str):
        if not _PVR_ID_RE.match(request_id):
            return jsonify({"ok": False, "error": "رقم الطلب غير صالح"}), 400

        rec = _read_pvr(request_id)
        if rec is None:
            return jsonify({"ok": False, "error": "الطلب غير موجود"}), 404

        body          = flask_request.get_json(force=True, silent=True) or {}
        target_status = (body.get("target_status") or "").strip()
        note          = (body.get("note") or "").strip()

        if not target_status:
            return jsonify({"ok": False, "error": "target_status مطلوب"}), 400

        current_status = rec.get("status", "draft_request")
        ok, error_code, message = _validate_transition(
            current_status, target_status, rec, body
        )
        if not ok:
            return jsonify({
                "ok":         False,
                "error_code": error_code,
                "error":      message,
            }), 422

        now     = datetime.utcnow().isoformat()
        user_id = getattr(g, "user_id", None) or "system"

        _update_pvr(request_id, {"status": target_status, "updated_at": now})
        _append_event(
            request_id=request_id,
            actor=user_id,
            action="transition",
            from_status=current_status,
            to_status=target_status,
            note=note,
        )

        return jsonify({
            "ok":          True,
            "request_id":  request_id,
            "from_status": current_status,
            "to_status":   target_status,
            "updated_at":  now,
            "message":     (
                f"تم الانتقال من '{current_status}' إلى '{target_status}' بنجاح."
            ),
        }), 200
