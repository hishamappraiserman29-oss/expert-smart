"""
professional_valuation_certification.py — Peer Review, Signature & Final Certification Gate (Phase G).

Endpoints (all JWT-protected):
  GET  /api/professional-valuation/requests/<id>/peer-review
  POST /api/professional-valuation/requests/<id>/peer-review/assign
  POST /api/professional-valuation/requests/<id>/peer-review/start
  POST /api/professional-valuation/requests/<id>/peer-review/submit
  GET  /api/professional-valuation/requests/<id>/signature
  POST /api/professional-valuation/requests/<id>/signature
  GET  /api/professional-valuation/requests/<id>/certification-gate
  POST /api/professional-valuation/requests/<id>/certification-gate/evaluate
  POST /api/professional-valuation/requests/<id>/certification-gate/mark-ready

Storage (internal paths never exposed in API responses):
  instance/professional_valuation/peer_reviews/<request_id>.json
  instance/professional_valuation/peer_review_events/<request_id>.jsonl
  instance/professional_valuation/signatures/<request_id>.json
  instance/professional_valuation/certification_gate/<request_id>.json
  instance/professional_valuation/certification_events/<request_id>.jsonl

Phase G scope: peer review assignment + sign-off, expert signature/license/stamp, final certification gate.
  - certification_ready can become True ONLY when all Phase C/D/E/F/G gates pass.
  - No OCR, no Qdrant, no RAG, no external APIs.
  - No fabricated peer reviewer identity, signature, license, or stamp.
  - No final certified PDF or workbook generated here — Phase H.
  - production_ready defaults to False on peer review and signature records.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path

# ── Storage paths ─────────────────────────────────────────────────────────────

_BASE             = Path(__file__).parent / "instance" / "professional_valuation"
_PEER_DIR         = _BASE / "peer_reviews"
_PEER_EVENTS_DIR  = _BASE / "peer_review_events"
_SIG_DIR          = _BASE / "signatures"
_GATE_DIR         = _BASE / "certification_gate"
_CERT_EVENTS_DIR  = _BASE / "certification_events"

for _d in (_PEER_DIR, _PEER_EVENTS_DIR, _SIG_DIR, _GATE_DIR, _CERT_EVENTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── ID / regex helpers ─────────────────────────────────────────────────────────

_PVR_ID_RE = re.compile(r"^PVR-\d{8}-[0-9A-F]{4}$")


def _new_pvpr_id() -> str:
    return "PVPR-" + uuid.uuid4().hex[:8].upper()


def _new_pvsg_id() -> str:
    return "PVSG-" + uuid.uuid4().hex[:8].upper()


# ── Peer review statuses ───────────────────────────────────────────────────────

_PR_STATUSES: frozenset[str] = frozenset({
    "not_assigned", "assigned", "in_review",
    "changes_requested", "approved", "rejected", "superseded",
})

# ── Signature approval statuses ───────────────────────────────────────────────

_SIG_STATUSES: frozenset[str] = frozenset({
    "not_started", "draft", "pending_signature",
    "signed", "rejected", "superseded",
})

# ── Required peer review sections for final approval ─────────────────────────

_REQUIRED_SECTIONS: frozenset[str] = frozenset({
    "methods", "reconciliation", "hbu", "legal", "esg", "swot"
})

_REQUIRED_REVIEW_FLAGS: frozenset[str] = frozenset({
    "methodology_review_complete",
    "source_review_complete",
    "document_review_complete",
    "hbu_review_complete",
    "legal_review_complete",
    "esg_review_complete",
    "swot_review_complete",
    "reconciliation_review_complete",
})


# ── Default records ───────────────────────────────────────────────────────────

def _default_peer_review(request_id: str) -> dict:
    now = datetime.utcnow().isoformat()
    return {
        "peer_review_id":                 _new_pvpr_id(),
        "request_id":                     request_id,
        "assigned_at":                    None,
        "assigned_by":                    None,
        "assigned_reviewer_name":         None,
        "assigned_reviewer_role":         None,
        "assigned_reviewer_license":      None,
        "assigned_reviewer_email":        None,
        "status":                         "not_assigned",
        "review_started_at":              None,
        "review_completed_at":            None,
        "review_decision":                None,
        "review_notes":                   None,
        "required_changes":               None,
        "reviewed_sections":              [],
        "methodology_review_complete":    False,
        "source_review_complete":         False,
        "document_review_complete":       False,
        "hbu_review_complete":            False,
        "legal_review_complete":          False,
        "esg_review_complete":            False,
        "swot_review_complete":           False,
        "reconciliation_review_complete": False,
        "peer_review_signature_available": False,
        "peer_review_signature_label":    None,
        "peer_review_ready":              False,
        "production_ready":               False,
        "official_use_allowed":           False,
        "certified_use_allowed":          False,
        "expert_only_notes":              None,
        "qdrant_used":                    False,
        "rag_used":                       False,
        "no_automatic_value_extraction":  True,
        "created_at":                     now,
        "updated_at":                     now,
    }


def _default_signature(request_id: str) -> dict:
    now = datetime.utcnow().isoformat()
    return {
        "signature_id":                _new_pvsg_id(),
        "request_id":                  request_id,
        "updated_at":                  None,
        "updated_by":                  None,
        "expert_name":                 None,
        "expert_role":                 None,
        "expert_license_number":       None,
        "expert_email":                None,
        "firm_name":                   None,
        "company_registration_number": None,
        "signature_available":         False,
        "signature_label":             None,
        "signature_file_uploaded":     False,
        "stamp_available":             False,
        "stamp_label":                 None,
        "stamp_file_uploaded":         False,
        "signed_at":                   None,
        "approval_statement":          None,
        "approval_scope":              None,
        "approval_status":             "not_started",
        "signature_ready":             False,
        "license_ready":               False,
        "stamp_ready":                 False,
        "final_signoff_ready":         False,
        "production_ready":            False,
        "official_use_allowed":        False,
        "certified_use_allowed":       False,
        "limitations":                 None,
        "qdrant_used":                 False,
        "rag_used":                    False,
        "no_automatic_value_extraction": True,
        "created_at":                  now,
    }


# ── Storage helpers — peer review ─────────────────────────────────────────────

def _load_peer_review(request_id: str) -> dict:
    path = _PEER_DIR / f"{request_id}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return _default_peer_review(request_id)


def _save_peer_review(rec: dict) -> None:
    path = _PEER_DIR / f"{rec['request_id']}.json"
    path.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_peer_event(
    request_id: str, actor: str, action: str,
    note: str = "", metadata: dict | None = None,
) -> None:
    event = {
        "event_id":   "PVPRE-" + uuid.uuid4().hex[:8].upper(),
        "request_id": request_id,
        "timestamp":  datetime.utcnow().isoformat(),
        "actor":      actor,
        "action":     action,
        "note":       note,
        "metadata":   metadata or {},
    }
    path = _PEER_EVENTS_DIR / f"{request_id}.jsonl"
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


def _read_peer_events(request_id: str) -> list[dict]:
    path = _PEER_EVENTS_DIR / f"{request_id}.jsonl"
    if not path.exists():
        return []
    events: list[dict] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if raw:
            try:
                events.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    return events


# ── Storage helpers — signature ───────────────────────────────────────────────

def _load_signature(request_id: str) -> dict:
    path = _SIG_DIR / f"{request_id}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return _default_signature(request_id)


def _save_signature(rec: dict) -> None:
    path = _SIG_DIR / f"{rec['request_id']}.json"
    path.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_cert_event(
    request_id: str, actor: str, action: str,
    note: str = "", metadata: dict | None = None,
) -> None:
    event = {
        "event_id":   "PVCE-" + uuid.uuid4().hex[:8].upper(),
        "request_id": request_id,
        "timestamp":  datetime.utcnow().isoformat(),
        "actor":      actor,
        "action":     action,
        "note":       note,
        "metadata":   metadata or {},
    }
    path = _CERT_EVENTS_DIR / f"{request_id}.jsonl"
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


def _read_cert_events(request_id: str) -> list[dict]:
    path = _CERT_EVENTS_DIR / f"{request_id}.jsonl"
    if not path.exists():
        return []
    events: list[dict] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if raw:
            try:
                events.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    return events


# ── Safe response builders ────────────────────────────────────────────────────

def _safe_peer_review(rec: dict) -> dict:
    """Return peer review dict with no internal file paths."""
    return {k: v for k, v in rec.items()}


def _safe_signature(rec: dict) -> dict:
    """Return signature dict with no internal file paths."""
    blocked = frozenset({
        "signature_file_path", "stamp_file_path",
        "_internal", "_file_path",
    })
    return {k: v for k, v in rec.items() if k not in blocked}


# ── Peer review readiness ─────────────────────────────────────────────────────

def _compute_peer_review_readiness(rec: dict) -> dict:
    status           = rec.get("status", "not_assigned")
    review_decision  = rec.get("review_decision")
    review_notes     = (rec.get("review_notes") or "").strip()
    reviewed_sections = rec.get("reviewed_sections") or []

    all_flags_set = all(rec.get(f) for f in _REQUIRED_REVIEW_FLAGS)
    all_sections  = all(s in reviewed_sections for s in _REQUIRED_SECTIONS)

    peer_review_ready = (
        status == "approved"
        and review_decision == "approved"
        and bool(review_notes)
        and all_sections
        and all_flags_set
    )

    return {
        "peer_review_ready":     peer_review_ready,
        "peer_review_status":    status,
        "certified_use_allowed": False,
        "official_use_allowed":  False,
    }


# ── Signature readiness ───────────────────────────────────────────────────────

def _compute_signature_readiness(rec: dict) -> dict:
    expert_name     = (rec.get("expert_name") or "").strip()
    expert_license  = (rec.get("expert_license_number") or "").strip()
    signed_at       = (rec.get("signed_at") or "").strip()
    sig_available   = bool(rec.get("signature_available"))
    approval_stmt   = (rec.get("approval_statement") or "").strip()
    approval_status = rec.get("approval_status", "not_started")

    signature_ready = bool(
        expert_name and expert_license
        and signed_at and sig_available and approval_stmt
    )
    license_ready = bool(expert_name and expert_license)
    stamp_ready   = bool(rec.get("stamp_available"))

    final_signoff_ready = (
        signature_ready
        and license_ready
        and approval_status == "signed"
    )

    return {
        "signature_ready":       signature_ready,
        "license_ready":         license_ready,
        "stamp_ready":           stamp_ready,
        "final_signoff_ready":   final_signoff_ready,
        "approval_status":       approval_status,
        "certified_use_allowed": False,
        "official_use_allowed":  False,
    }


# ── Gate fragments for external import ────────────────────────────────────────

def get_peer_review_gate_fragment(request_id: str) -> dict:
    """Return peer review gate fields for merging into certification gate."""
    rec = _load_peer_review(request_id)
    rf  = _compute_peer_review_readiness(rec)
    return {
        "peer_review_status":        rf["peer_review_status"],
        "peer_review_ready":         rf["peer_review_ready"],
        "phase_g_peer_review_ready": rf["peer_review_ready"],
    }


def get_signature_gate_fragment(request_id: str) -> dict:
    """Return signature gate fields for merging into certification gate."""
    rec = _load_signature(request_id)
    sf  = _compute_signature_readiness(rec)
    return {
        "signature_ready":         sf["signature_ready"],
        "license_ready":           sf["license_ready"],
        "stamp_ready":             sf["stamp_ready"],
        "final_signoff_ready":     sf["final_signoff_ready"],
        "phase_g_signature_ready": sf["signature_ready"],
        "phase_g_license_ready":   sf["license_ready"],
        "phase_g_stamp_ready":     sf["stamp_ready"],
    }


# ── Final certification gate evaluator ────────────────────────────────────────

def compute_final_certification_gate(
    request_id: str, valuation_purpose: str = ""
) -> dict:
    """Evaluate all Phase C–G gates and return the final certification gate.

    certification_ready becomes True only when every required gate is satisfied.
    In Phase G this CAN become True under a controlled fixture scenario.
    """
    gate: dict = {
        "request_id":   request_id,
        "evaluated_at": datetime.utcnow().isoformat(),
        # Phase C
        "phase_c_documents_ready":               False,
        "phase_c_sources_ready":                 False,
        # Phase D
        "phase_d_comparables_ready":             False,
        # Phase E
        "phase_e_methods_completed":             False,
        "phase_e_reconciliation_completed":      False,
        "phase_e_preliminary_approval_ready":    False,
        # Phase F
        "phase_f_hbu_completed":                 False,
        "phase_f_legal_due_diligence_ready":     False,
        "phase_f_esg_reviewed":                  False,
        "phase_f_swot_completed":                False,
        "phase_f_advanced_reviews_prelim_ready": False,
        # Phase G
        "phase_g_peer_review_ready":             False,
        "phase_g_signature_ready":               False,
        "phase_g_license_ready":                 False,
        "phase_g_stamp_ready":                   False,
        # Combined summary fields
        "qa_data_cleared":           False,
        "real_sources_ready":        False,
        "mandatory_documents_ready": False,
        "comparables_ready":         False,
        "methods_completed":         False,
        "reconciliation_completed":  False,
        "preliminary_approval_ready": False,
        "hbu_completed":             False,
        "legal_due_diligence_ready": False,
        "esg_reviewed":              False,
        "swot_completed":            False,
        "advanced_reviews_prelim_ready": False,
        "peer_review_completed":     False,
        "expert_signature_ready":    False,
        # Output
        "certification_ready":               False,
        "official_use_allowed":              False,
        "certified_use_allowed":             False,
        "final_report_generation_allowed":   False,
        "final_workbook_generation_allowed": False,
        "blockers":              [],
        "warnings":              [],
        "advisory_only_reason":  (
            "Phase G — peer review and signature gates evaluated. "
            "All upstream phases (C, D, E, F) must be complete before certification."
        ),
        "certification_status":    "not_ready",
        "next_required_actions":   [],
        # Governance flags always enforced
        "qdrant_used":                   False,
        "rag_used":                      False,
        "no_automatic_value_extraction": True,
    }

    blockers: list[str] = []
    next_actions: list[str] = []

    # ── Phase C — evidence / source gate ─────────────────────────────────────
    try:
        from professional_valuation_evidence_routes import compute_gate_summary
        c_gate = compute_gate_summary(request_id, valuation_purpose)
        gate["phase_c_documents_ready"]   = bool(c_gate.get("mandatory_documents_ready"))
        gate["phase_c_sources_ready"]     = bool(c_gate.get("real_sources_ready"))
        gate["qa_data_cleared"]           = bool(c_gate.get("qa_data_cleared", False))
        gate["mandatory_documents_ready"] = gate["phase_c_documents_ready"]
        gate["real_sources_ready"]        = gate["phase_c_sources_ready"]
    except ImportError:
        pass

    if not gate["qa_data_cleared"]:
        blockers.append("QA simulation data remains — يجب استبدالها بمصادر سوقية حقيقية")
    if not gate["mandatory_documents_ready"]:
        blockers.append("Mandatory documents incomplete — اكتمال المستندات الإلزامية مطلوب")
        next_actions.append("upload_mandatory_documents")
    if not gate["real_sources_ready"]:
        blockers.append("No approved production sources — لا توجد مصادر إنتاجية معتمدة")
        next_actions.append("approve_market_sources")

    # ── Phase D — comparable gate ─────────────────────────────────────────────
    try:
        from professional_valuation_comparables import evaluate_comparable_readiness
        d_gate = evaluate_comparable_readiness(request_id, valuation_purpose)
        gate["phase_d_comparables_ready"] = bool(d_gate.get("certification_comparable_ready"))
        gate["comparables_ready"]         = gate["phase_d_comparables_ready"]
    except ImportError:
        pass

    if not gate["comparables_ready"]:
        blockers.append("No production-ready comparables — مقارنات إنتاجية غير متوفرة")
        next_actions.append("submit_comparables")

    # ── Phase E — methods / reconciliation / preliminary approval ─────────────
    try:
        from professional_valuation_methods import (
            evaluate_method_readiness_for_request,
            get_reconciliation_for_request,
            get_preliminary_approval_for_request,
        )
        mr = evaluate_method_readiness_for_request(request_id)
        gate["phase_e_methods_completed"]          = bool(mr.get("methods_completed"))
        gate["methods_completed"]                  = gate["phase_e_methods_completed"]

        recon = get_reconciliation_for_request(request_id)
        gate["phase_e_reconciliation_completed"]   = bool(
            recon and recon.get("weighted_value") is not None
        )
        gate["reconciliation_completed"]           = gate["phase_e_reconciliation_completed"]

        prelim = get_preliminary_approval_for_request(request_id)
        gate["phase_e_preliminary_approval_ready"] = bool(
            prelim and prelim.get("preliminary_approval_ready")
        )
        gate["preliminary_approval_ready"]         = gate["phase_e_preliminary_approval_ready"]
    except ImportError:
        pass

    if not gate["methods_completed"]:
        blockers.append("Valuation methods incomplete — طرق التقييم غير مكتملة")
        next_actions.append("run_valuation_methods")
    if not gate["reconciliation_completed"]:
        blockers.append("Reconciliation not completed — التسوية غير مكتملة")
        next_actions.append("complete_reconciliation")
    if not gate["preliminary_approval_ready"]:
        blockers.append("Preliminary approval not issued — الموافقة المبدئية غير صادرة")
        next_actions.append("issue_preliminary_approval")

    # ── Phase F — advanced reviews ────────────────────────────────────────────
    try:
        from professional_valuation_advanced_review import get_advanced_review_gate_fragment
        adv = get_advanced_review_gate_fragment(request_id)
        gate["phase_f_hbu_completed"]                = bool(adv.get("hbu_completed"))
        gate["phase_f_legal_due_diligence_ready"]    = bool(adv.get("legal_due_diligence_ready"))
        gate["phase_f_esg_reviewed"]                 = bool(adv.get("esg_reviewed"))
        gate["phase_f_swot_completed"]               = bool(adv.get("swot_completed"))
        gate["phase_f_advanced_reviews_prelim_ready"] = bool(adv.get("advanced_reviews_prelim_ready"))
        gate["hbu_completed"]                        = gate["phase_f_hbu_completed"]
        gate["legal_due_diligence_ready"]            = gate["phase_f_legal_due_diligence_ready"]
        gate["esg_reviewed"]                         = gate["phase_f_esg_reviewed"]
        gate["swot_completed"]                       = gate["phase_f_swot_completed"]
        gate["advanced_reviews_prelim_ready"]        = gate["phase_f_advanced_reviews_prelim_ready"]
    except ImportError:
        pass

    if not gate["hbu_completed"]:
        blockers.append("HBU review incomplete — مراجعة الاستخدام الأمثل غير مكتملة")
        next_actions.append("complete_hbu_review")
    if not gate["legal_due_diligence_ready"]:
        blockers.append("Legal due diligence incomplete — العناية القانونية غير مكتملة")
        next_actions.append("complete_legal_review")
    if not gate["esg_reviewed"]:
        blockers.append("ESG/climate review incomplete — مراجعة ESG غير مكتملة")
        next_actions.append("complete_esg_review")
    if not gate["swot_completed"]:
        blockers.append("SWOT/risk review incomplete — تحليل SWOT غير مكتمل")
        next_actions.append("complete_swot_review")

    # ── Phase G — peer review ─────────────────────────────────────────────────
    pr_rec = _load_peer_review(request_id)
    pr_rf  = _compute_peer_review_readiness(pr_rec)
    gate["phase_g_peer_review_ready"] = pr_rf["peer_review_ready"]
    gate["peer_review_completed"]     = gate["phase_g_peer_review_ready"]

    if not gate["peer_review_completed"]:
        blockers.append("Peer review not approved — مراجعة النظراء غير مكتملة أو غير معتمدة")
        pr_status = pr_rec.get("status", "not_assigned")
        if pr_status == "not_assigned":
            next_actions.append("assign_peer_reviewer")
        elif pr_status in ("assigned", "in_review"):
            next_actions.append("await_peer_review_completion")
        elif pr_status == "changes_requested":
            next_actions.append("address_peer_review_changes")

    # ── Phase G — signature / license ─────────────────────────────────────────
    sig_rec = _load_signature(request_id)
    sig_rf  = _compute_signature_readiness(sig_rec)
    gate["phase_g_signature_ready"] = sig_rf["signature_ready"]
    gate["phase_g_license_ready"]   = sig_rf["license_ready"]
    gate["phase_g_stamp_ready"]     = sig_rf["stamp_ready"]
    gate["expert_signature_ready"]  = sig_rf["final_signoff_ready"]

    if not gate["expert_signature_ready"]:
        blockers.append("Expert signature/license not completed — التوقيع والترخيص غير مكتملين")
        next_actions.append("complete_expert_signature")

    # ── Final computation ─────────────────────────────────────────────────────
    gate["blockers"] = blockers

    all_required = (
        gate["qa_data_cleared"]
        and gate["mandatory_documents_ready"]
        and gate["real_sources_ready"]
        and gate["comparables_ready"]
        and gate["methods_completed"]
        and gate["reconciliation_completed"]
        and gate["preliminary_approval_ready"]
        and gate["hbu_completed"]
        and gate["legal_due_diligence_ready"]
        and gate["esg_reviewed"]
        and gate["swot_completed"]
        and gate["peer_review_completed"]
        and gate["expert_signature_ready"]
    )

    gate["certification_ready"]               = all_required and len(blockers) == 0
    gate["official_use_allowed"]              = gate["certification_ready"]
    gate["certified_use_allowed"]             = gate["certification_ready"]
    gate["final_report_generation_allowed"]   = gate["certification_ready"]
    gate["final_workbook_generation_allowed"] = gate["certification_ready"]

    if gate["certification_ready"]:
        gate["certification_status"]   = "ready_for_certified_outputs"
        gate["advisory_only_reason"]   = ""
        gate["next_required_actions"]  = ["generate_certified_outputs"]
    else:
        pr_status = pr_rec.get("status", "not_assigned")
        if pr_status == "approved" and sig_rf["final_signoff_ready"]:
            gate["certification_status"] = "signed_pending_final_gate"
        elif pr_status == "approved":
            gate["certification_status"] = "ready_for_signature"
        elif pr_status in ("in_review", "assigned"):
            gate["certification_status"] = "peer_review_in_progress"
        elif pr_status == "changes_requested":
            gate["certification_status"] = "changes_requested"
        else:
            gate["certification_status"] = "not_ready"
        # Deduplicate preserving order
        seen: set[str] = set()
        gate["next_required_actions"] = [
            a for a in next_actions if not (a in seen or seen.add(a))  # type: ignore[func-returns-value]
        ]

    # Save snapshot (best-effort)
    try:
        snap_path = _GATE_DIR / f"{request_id}.json"
        snap_path.write_text(json.dumps(gate, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass

    return gate


# ── Route registration ────────────────────────────────────────────────────────

def register_pv_certification_routes(app, require_auth) -> None:
    """Register all Phase G certification routes on the Flask app."""
    from flask import g, jsonify, request as flask_request

    def _actor() -> str:
        return getattr(g, "user_id", None) or "system"

    def _check_pvr_id(request_id: str):
        if not _PVR_ID_RE.match(request_id):
            return jsonify({"ok": False, "error": "رقم الطلب غير صالح"}), 400
        return None

    # ── GET /api/professional-valuation/requests/<id>/peer-review ─────────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/peer-review",
        methods=["GET"],
    )
    @require_auth
    def pvg_get_peer_review(request_id: str):
        err = _check_pvr_id(request_id)
        if err:
            return err
        rec    = _load_peer_review(request_id)
        events = _read_peer_events(request_id)
        rf     = _compute_peer_review_readiness(rec)
        return jsonify({
            "ok":          True,
            "peer_review": _safe_peer_review(rec),
            "readiness":   rf,
            "event_log":   events,
        }), 200

    # ── POST /api/professional-valuation/requests/<id>/peer-review/assign ─────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/peer-review/assign",
        methods=["POST"],
    )
    @require_auth
    def pvg_assign_peer_review(request_id: str):
        err = _check_pvr_id(request_id)
        if err:
            return err
        body = flask_request.get_json(force=True, silent=True) or {}

        reviewer_name = (body.get("reviewer_name") or "").strip()
        reviewer_role = (body.get("reviewer_role") or "").strip()

        if not reviewer_name:
            return jsonify({"ok": False, "error": "reviewer_name مطلوب"}), 422
        if not reviewer_role:
            return jsonify({"ok": False, "error": "reviewer_role مطلوب"}), 422

        now = datetime.utcnow().isoformat()
        rec = _load_peer_review(request_id)
        rec.update({
            "assigned_at":               now,
            "assigned_by":               _actor(),
            "assigned_reviewer_name":    reviewer_name,
            "assigned_reviewer_role":    reviewer_role,
            "assigned_reviewer_license": (body.get("reviewer_license") or "").strip() or None,
            "assigned_reviewer_email":   (body.get("reviewer_email") or "").strip() or None,
            "status":                    "assigned",
            "peer_review_ready":         False,
            "updated_at":                now,
        })
        _save_peer_review(rec)
        _append_peer_event(
            request_id, _actor(), "assign",
            note=(body.get("assignment_note") or f"Assigned to {reviewer_name}"),
            metadata={"reviewer_name": reviewer_name, "reviewer_role": reviewer_role},
        )

        gate = compute_final_certification_gate(request_id)
        return jsonify({
            "ok":                        True,
            "peer_review":               _safe_peer_review(rec),
            "certification_gate_summary": gate,
        }), 200

    # ── POST /api/professional-valuation/requests/<id>/peer-review/start ──────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/peer-review/start",
        methods=["POST"],
    )
    @require_auth
    def pvg_start_peer_review(request_id: str):
        err = _check_pvr_id(request_id)
        if err:
            return err
        rec = _load_peer_review(request_id)

        if rec.get("status") not in ("assigned", "changes_requested"):
            return jsonify({
                "ok":             False,
                "error":          (
                    "يجب أن تكون مراجعة النظراء في حالة 'assigned' أو 'changes_requested' للبدء."
                ),
                "current_status": rec.get("status"),
            }), 422

        now = datetime.utcnow().isoformat()
        rec.update({
            "status":             "in_review",
            "review_started_at":  now,
            "updated_at":         now,
        })
        _save_peer_review(rec)
        _append_peer_event(request_id, _actor(), "start_review", note="Review started")

        return jsonify({
            "ok":          True,
            "peer_review": _safe_peer_review(rec),
        }), 200

    # ── POST /api/professional-valuation/requests/<id>/peer-review/submit ─────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/peer-review/submit",
        methods=["POST"],
    )
    @require_auth
    def pvg_submit_peer_review(request_id: str):
        err = _check_pvr_id(request_id)
        if err:
            return err
        rec  = _load_peer_review(request_id)
        body = flask_request.get_json(force=True, silent=True) or {}

        review_decision   = (body.get("review_decision") or "").strip()
        review_notes      = (body.get("review_notes") or "").strip()
        required_changes  = (body.get("required_changes") or "").strip()
        reviewed_sections = body.get("reviewed_sections") or []

        if review_decision not in ("approved", "changes_requested", "rejected"):
            return jsonify({
                "ok":    False,
                "error": "review_decision يجب أن يكون: approved أو changes_requested أو rejected",
            }), 422

        if not review_notes:
            return jsonify({"ok": False, "error": "review_notes مطلوب"}), 422

        if review_decision == "changes_requested" and not required_changes:
            return jsonify({"ok": False, "error": "required_changes مطلوب عند طلب تعديلات"}), 422

        if review_decision == "approved":
            missing_sections = sorted(
                s for s in _REQUIRED_SECTIONS if s not in reviewed_sections
            )
            if missing_sections:
                return jsonify({
                    "ok":              False,
                    "error":           f"reviewed_sections يجب أن تشمل: {', '.join(sorted(_REQUIRED_SECTIONS))}",
                    "missing_sections": missing_sections,
                }), 422

            missing_flags = [f for f in _REQUIRED_REVIEW_FLAGS if not body.get(f)]
            if missing_flags:
                return jsonify({
                    "ok":           False,
                    "error":        f"جميع أعلام المراجعة مطلوبة للموافقة: {missing_flags}",
                    "missing_flags": missing_flags,
                }), 422

            if not body.get("peer_review_signature_available"):
                return jsonify({
                    "ok":    False,
                    "error": "peer_review_signature_available مطلوب للموافقة",
                }), 422

        now = datetime.utcnow().isoformat()
        rec.update({
            "status":               review_decision,
            "review_decision":      review_decision,
            "review_notes":         review_notes,
            "required_changes":     required_changes or None,
            "reviewed_sections":    reviewed_sections,
            "review_completed_at":  now,
            "updated_at":           now,
        })
        for flag in _REQUIRED_REVIEW_FLAGS:
            rec[flag] = bool(body.get(flag))
        rec["peer_review_signature_available"] = bool(body.get("peer_review_signature_available"))
        rec["peer_review_signature_label"]     = body.get("peer_review_signature_label") or None
        rec["expert_only_notes"]               = body.get("expert_only_notes") or None

        rf = _compute_peer_review_readiness(rec)
        rec["peer_review_ready"]      = rf["peer_review_ready"]
        rec["certified_use_allowed"]  = False  # full gate still needed

        _save_peer_review(rec)
        _append_peer_event(
            request_id, _actor(), "submit_review",
            note=f"decision={review_decision}",
            metadata={"review_decision": review_decision},
        )

        gate = compute_final_certification_gate(request_id)
        return jsonify({
            "ok":                        True,
            "peer_review":               _safe_peer_review(rec),
            "peer_review_ready":         rec["peer_review_ready"],
            "certification_gate_summary": gate,
        }), 200

    # ── GET /api/professional-valuation/requests/<id>/signature ───────────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/signature",
        methods=["GET"],
    )
    @require_auth
    def pvg_get_signature(request_id: str):
        err = _check_pvr_id(request_id)
        if err:
            return err
        rec = _load_signature(request_id)
        sf  = _compute_signature_readiness(rec)
        return jsonify({
            "ok":        True,
            "signature": _safe_signature(rec),
            "readiness": sf,
        }), 200

    # ── POST /api/professional-valuation/requests/<id>/signature ──────────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/signature",
        methods=["POST"],
    )
    @require_auth
    def pvg_save_signature(request_id: str):
        err = _check_pvr_id(request_id)
        if err:
            return err
        body = flask_request.get_json(force=True, silent=True) or {}

        approval_status = (body.get("approval_status") or "draft").strip()
        if approval_status not in _SIG_STATUSES:
            approval_status = "draft"

        if approval_status == "signed":
            expert_name    = (body.get("expert_name") or "").strip()
            expert_license = (body.get("expert_license_number") or "").strip()
            signed_at      = (body.get("signed_at") or "").strip()
            sig_available  = bool(body.get("signature_available"))
            approval_stmt  = (body.get("approval_statement") or "").strip()

            if not expert_name:
                return jsonify({"ok": False, "error": "expert_name مطلوب لحالة 'signed'"}), 422
            if not expert_license:
                return jsonify({"ok": False, "error": "expert_license_number مطلوب لحالة 'signed'"}), 422
            if not signed_at:
                return jsonify({"ok": False, "error": "signed_at مطلوب لحالة 'signed'"}), 422
            if not sig_available:
                return jsonify({
                    "ok":    False,
                    "error": "signature_available يجب أن يكون true لحالة 'signed'",
                }), 422
            if not approval_stmt:
                return jsonify({"ok": False, "error": "approval_statement مطلوب لحالة 'signed'"}), 422

        now = datetime.utcnow().isoformat()
        rec = _load_signature(request_id)

        def _pick(key: str, default=None):
            val = (body.get(key) or "")
            if isinstance(val, str):
                val = val.strip()
            return val if val else (rec.get(key) or default)

        rec.update({
            "updated_at":                  now,
            "updated_by":                  _actor(),
            "expert_name":                 _pick("expert_name"),
            "expert_role":                 _pick("expert_role"),
            "expert_license_number":       _pick("expert_license_number"),
            "expert_email":                _pick("expert_email"),
            "firm_name":                   _pick("firm_name"),
            "company_registration_number": _pick("company_registration_number"),
            "signature_available":         bool(body.get("signature_available",
                                                          rec.get("signature_available"))),
            "signature_label":             body.get("signature_label") or rec.get("signature_label"),
            "stamp_available":             bool(body.get("stamp_available",
                                                         rec.get("stamp_available"))),
            "stamp_label":                 body.get("stamp_label") or rec.get("stamp_label"),
            "signed_at":                   _pick("signed_at"),
            "approval_statement":          _pick("approval_statement"),
            "approval_scope":              _pick("approval_scope"),
            "approval_status":             approval_status,
            "limitations":                 body.get("limitations") or rec.get("limitations"),
        })

        sf = _compute_signature_readiness(rec)
        rec.update({
            "signature_ready":    sf["signature_ready"],
            "license_ready":      sf["license_ready"],
            "stamp_ready":        sf["stamp_ready"],
            "final_signoff_ready": sf["final_signoff_ready"],
            "certified_use_allowed": False,
            "official_use_allowed":  False,
        })

        _save_signature(rec)
        _append_cert_event(
            request_id, _actor(), "signature_update",
            note=f"approval_status={approval_status}",
            metadata={"approval_status": approval_status},
        )

        gate = compute_final_certification_gate(request_id)
        return jsonify({
            "ok":                        True,
            "signature":                 _safe_signature(rec),
            "final_signoff_ready":       rec["final_signoff_ready"],
            "certification_gate_summary": gate,
        }), 200

    # ── GET /api/professional-valuation/requests/<id>/certification-gate ──────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/certification-gate",
        methods=["GET"],
    )
    @require_auth
    def pvg_get_certification_gate(request_id: str):
        err = _check_pvr_id(request_id)
        if err:
            return err
        snap_path = _GATE_DIR / f"{request_id}.json"
        if snap_path.exists():
            try:
                gate = json.loads(snap_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                gate = compute_final_certification_gate(request_id)
        else:
            gate = compute_final_certification_gate(request_id)

        events = _read_cert_events(request_id)
        return jsonify({
            "ok":        True,
            "gate":      gate,
            "event_log": events,
        }), 200

    # ── POST /api/professional-valuation/requests/<id>/certification-gate/evaluate
    @app.route(
        "/api/professional-valuation/requests/<request_id>/certification-gate/evaluate",
        methods=["POST"],
    )
    @require_auth
    def pvg_evaluate_certification_gate(request_id: str):
        err = _check_pvr_id(request_id)
        if err:
            return err

        valuation_purpose = ""
        try:
            from professional_valuation_routes import _read_pvr as _pvr_read
            pvr = _pvr_read(request_id)
            if pvr:
                valuation_purpose = pvr.get("valuation_purpose", "")
        except ImportError:
            pass

        gate = compute_final_certification_gate(request_id, valuation_purpose)
        _append_cert_event(
            request_id, _actor(), "gate_evaluate",
            note=f"certification_ready={gate.get('certification_ready')}",
            metadata={"certification_status": gate.get("certification_status")},
        )

        return jsonify({"ok": True, "gate": gate}), 200

    # ── POST /api/professional-valuation/requests/<id>/certification-gate/mark-ready
    @app.route(
        "/api/professional-valuation/requests/<request_id>/certification-gate/mark-ready",
        methods=["POST"],
    )
    @require_auth
    def pvg_mark_certification_ready(request_id: str):
        err = _check_pvr_id(request_id)
        if err:
            return err

        valuation_purpose = ""
        try:
            from professional_valuation_routes import _read_pvr as _pvr_read
            pvr = _pvr_read(request_id)
            if pvr:
                valuation_purpose = pvr.get("valuation_purpose", "")
        except ImportError:
            pass

        gate = compute_final_certification_gate(request_id, valuation_purpose)

        if not gate.get("certification_ready"):
            return jsonify({
                "ok":      False,
                "error":   "بوابة الاعتماد النهائية لم تتجاوز — يوجد موانع",
                "blockers": gate.get("blockers", []),
                "gate":    gate,
            }), 422

        _append_cert_event(
            request_id, _actor(), "mark_ready",
            note="All gates passed — ready for certified output generation",
            metadata={"certification_status": "ready_for_certified_outputs"},
        )

        return jsonify({
            "ok":     True,
            "gate":   gate,
            "message": (
                "جميع بوابات الاعتماد اكتملت. "
                "يمكن الآن إنشاء التقرير المعتمد في المرحلة التالية (Phase H)."
            ),
        }), 200
