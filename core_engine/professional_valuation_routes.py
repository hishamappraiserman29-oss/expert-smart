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

_PVR_ID_RE = re.compile(r"^PVR-\d{8}-[0-9A-F]{4,8}$")

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

    # Phase F: advanced review gate fragment
    try:
        from professional_valuation_advanced_review import get_advanced_review_gate_fragment
        adv = get_advanced_review_gate_fragment(request_id)
        gate["hbu_completed"]               = adv.get("hbu_completed", False)
        gate["legal_due_diligence_ready"]   = adv.get("legal_due_diligence_ready", False)
        gate["esg_reviewed"]                = adv.get("esg_reviewed", False)
        gate["swot_completed"]              = adv.get("swot_completed", False)
        gate["advanced_reviews_prelim_ready"] = adv.get("advanced_reviews_prelim_ready", False)
        gate["advanced_reviews_cert_ready"] = False  # overridden by Phase G if all gates pass
        if not adv.get("hbu_completed", False):
            blocker = "HBU review incomplete — الاستخدام الأمثل غير مكتمل"
            if blocker not in gate.get("blockers", []):
                gate.setdefault("blockers", []).append(blocker)
        if not adv.get("legal_due_diligence_ready", False):
            blocker = "Legal due diligence incomplete — العناية القانونية غير مكتملة"
            if blocker not in gate.get("blockers", []):
                gate.setdefault("blockers", []).append(blocker)
        if not adv.get("esg_reviewed", False):
            blocker = "ESG/climate review incomplete — تقييم ESG غير مكتمل"
            if blocker not in gate.get("blockers", []):
                gate.setdefault("blockers", []).append(blocker)
        if not adv.get("swot_completed", False):
            blocker = "SWOT/risk review incomplete — تحليل SWOT غير مكتمل"
            if blocker not in gate.get("blockers", []):
                gate.setdefault("blockers", []).append(blocker)
    except ImportError:
        gate.setdefault("hbu_completed",               False)
        gate.setdefault("legal_due_diligence_ready",   False)
        gate.setdefault("esg_reviewed",                False)
        gate.setdefault("swot_completed",              False)
        gate.setdefault("advanced_reviews_prelim_ready", False)
        gate.setdefault("advanced_reviews_cert_ready", False)

    # Phase G: peer review and signature gate fragment
    try:
        from professional_valuation_certification import (
            compute_final_certification_gate as _final_gate,
        )
        final = _final_gate(request_id, valuation_purpose)
        gate["peer_review_completed"]   = final.get("peer_review_completed", False)
        gate["expert_signature_ready"]  = final.get("expert_signature_ready", False)
        gate["phase_g_peer_review_ready"] = final.get("phase_g_peer_review_ready", False)
        gate["phase_g_signature_ready"] = final.get("phase_g_signature_ready", False)
        gate["phase_g_license_ready"]   = final.get("phase_g_license_ready", False)
        gate["phase_g_stamp_ready"]     = final.get("phase_g_stamp_ready", False)
        gate["certification_ready"]     = final.get("certification_ready", False)
        gate["official_use_allowed"]    = final.get("official_use_allowed", False)
        gate["certified_use_allowed"]   = final.get("certified_use_allowed", False)
        gate["final_report_generation_allowed"]   = final.get("final_report_generation_allowed", False)
        gate["final_workbook_generation_allowed"] = final.get("final_workbook_generation_allowed", False)
        gate["certification_status"]    = final.get("certification_status", "not_ready")
        gate["blockers"]                = final.get("blockers", gate.get("blockers", []))
        gate["next_required_actions"]   = final.get("next_required_actions", [])
        if not final.get("peer_review_completed"):
            blocker = "Peer review not approved — مراجعة النظراء غير مكتملة أو غير معتمدة"
            if blocker not in gate.get("blockers", []):
                gate.setdefault("blockers", []).append(blocker)
        if not final.get("expert_signature_ready"):
            blocker = "Expert signature/license not completed — التوقيع والترخيص غير مكتملين"
            if blocker not in gate.get("blockers", []):
                gate.setdefault("blockers", []).append(blocker)
    except ImportError:
        gate.setdefault("peer_review_completed",  False)
        gate.setdefault("expert_signature_ready", False)
        gate["certification_ready"] = False  # always False without Phase G

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
    suffix   = uuid.uuid4().hex[:8].upper()
    return f"PVR-{date_str}-{suffix}"


# ── Persistence helpers ───────────────────────────────────────────────────────

def _persist_pvr(rec: dict) -> None:
    with open(_REQ_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _update_pvr(request_id: str, updates: dict) -> None:
    if not _REQ_FILE.exists():
        return
    lines: list[str] = []
    with open(_REQ_FILE, encoding="utf-8", errors="replace") as fh:
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


# Alias used by PVACR routes (chat-output/pdf, expert-review-request)
_find_pvr = _read_pvr

# ── PVUAFR: In-memory store for special asset requirement values ───────────
# Keyed by request_id; not persisted across restarts (advisory/draft only)
_SPECIAL_ASSET_REQ_VALUES: dict = {}


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
        "report_type":                   rec.get("report_type", "professional_report"),
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
        "report_type":                  rec.get("report_type", "professional_report"),
        # Canonical Axis 1 — Asset Classification
        "asset_family":                 rec.get("asset_family", ""),
        "asset_type":                   rec.get("asset_type", ""),
        "asset_subtype":                rec.get("asset_subtype", ""),
        "asset_condition_path":         rec.get("asset_condition_path", ""),
        # Canonical Axis 2 — Assignment Purpose
        "assignment_purpose":           rec.get("assignment_purpose", ""),
        "intended_user_category":       rec.get("intended_user_category", ""),
        "professional_context_path":    rec.get("professional_context_path", ""),
        "purpose_logic_path":           rec.get("purpose_logic_path", ""),
        # Step 2 UX purpose route fields
        "purpose_route":                rec.get("purpose_route", ""),
        "purpose_subroute":             rec.get("purpose_subroute", ""),
        "professional_purpose_path":    rec.get("professional_purpose_path", ""),
        # Canonical Axis 3 — Basis of Value
        "value_premise":                rec.get("value_premise", ""),
        "value_output_type":            rec.get("value_output_type", ""),
        # Three-Cards Taxonomy Summary (Part F)
        "taxonomy_cards_summary":       rec.get("taxonomy_cards_summary", {}),
        # Derived — Step 2 purpose routes summary
        "valuation_purpose_routes_summary": rec.get("valuation_purpose_routes_summary", {}),
        "legacy_purpose_aliases":       rec.get("legacy_purpose_aliases", []),
        "moved_purpose_options":        rec.get("moved_purpose_options", []),
        # Derived
        "canonical_taxonomy":           rec.get("canonical_taxonomy", {}),
        "derived_method_route":         rec.get("derived_method_route", {}),
        "asset_specific_requirements":  rec.get("asset_specific_requirements", {}),
        "asset_type_selection_context": rec.get("asset_type_selection_context", {}),
        # PVPTS Section 3 Three-Step contexts
        "valuation_purpose_context":    rec.get("valuation_purpose_context", {}),
        "purpose_registry_context":     rec.get("purpose_registry_context", {}),
        "basis_registry_context":       rec.get("basis_registry_context", {}),
        "intended_user_registry_context": rec.get("intended_user_registry_context", {}),
        "routing_matrix_registry_context": rec.get("routing_matrix_registry_context", {}),
        "purpose_taxonomy_v2_registries": rec.get("purpose_taxonomy_v2_registries", {}),
        "engine_governance_audit_context": rec.get("engine_governance_audit_context", {}),
        "main_page_sections_context":      rec.get("main_page_sections_context", {}),
        "advanced_controls_context":       rec.get("advanced_controls_context", {}),
        "professional_valuation_feature_capabilities": rec.get(
            "professional_valuation_feature_capabilities", {}
        ),
        "control_activation_roadmap":   rec.get("control_activation_roadmap", []),
        "report_reflection_matrix":     rec.get("report_reflection_matrix", {}),
        # PVDSR — Special asset requirements contexts
        "special_asset_requirements_context":     rec.get("special_asset_requirements_context", {}),
        "asset_methodology_guidance":             rec.get("asset_methodology_guidance", {}),
        "asset_report_workbook_context":          rec.get("asset_report_workbook_context", {}),
        "future_integrations":                    rec.get("future_integrations", {}),
        "special_asset_taxonomy_v2_registries":   rec.get("special_asset_taxonomy_v2_registries", {}),
        # PVACR — Chat output final restructure contexts
        "chat_output_context":                        rec.get("chat_output_context", {}),
        "report_output_registry_context":             rec.get("report_output_registry_context", {}),
        "output_format_visibility_policy_context":    rec.get("output_format_visibility_policy_context", {}),
        "deprecated_visible_controls_context":        rec.get("deprecated_visible_controls_context", {}),
        # PVS3 purpose context (original)
        "section3_purpose_context":                      rec.get("section3_purpose_context", {}),
        # PVS3 Section 3 Merge — purpose flow + professional targeting
        "section3_1_purpose_context":                    rec.get("section3_1_purpose_context", {}),
        "professional_targeting_context":                rec.get("professional_targeting_context", {}),
        "section3_cleanup_context":                      rec.get("section3_cleanup_context", {}),
        "purpose_flow_registry_summary":                 rec.get("purpose_flow_registry_summary", {}),
        "professional_targeting_registry_summary":       rec.get("professional_targeting_registry_summary", {}),
        "section3_1_legacy_mapping":                     rec.get("section3_1_legacy_mapping", {}),
        "professional_targeting_legacy_mapping":         rec.get("professional_targeting_legacy_mapping", {}),
        "pvs3_no_deletion_audit":                        rec.get("pvs3_no_deletion_audit", {}),
        # State
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

    # Gate: peer_review_required → peer_review_in_progress requires assigned peer review
    if target_status == "peer_review_in_progress":
        try:
            from professional_valuation_certification import get_peer_review_gate_fragment
            pr_frag = get_peer_review_gate_fragment(record.get("request_id", ""))
            if pr_frag.get("peer_review_status", "not_assigned") == "not_assigned":
                return False, "gate_blocked", (
                    "لا يمكن البدء في مراجعة النظراء قبل تعيين مراجع النظراء. "
                    "استخدم نقطة /peer-review/assign لتعيين المراجع أولاً."
                )
        except ImportError:
            pass  # Phase G not loaded — allow for backward compat

    # Gate: approved_pending_signature requires peer_review_completed on record
    if target_status == "approved_pending_signature":
        if not record.get("peer_review_completed"):
            return False, "gate_blocked", (
                "لا يمكن الانتقال إلى 'approved_pending_signature' بدون إتمام مراجعة النظراء. "
                "يجب تعيين peer_review_completed=true على السجل أولاً."
            )

    # Gate: signed_pending_certification requires signature gate (body flag OR Phase G record)
    if target_status == "signed_pending_certification":
        sig_gate_cleared = bool(body.get("signature_gate_cleared"))
        if not sig_gate_cleared:
            try:
                from professional_valuation_certification import get_signature_gate_fragment
                sig_frag = get_signature_gate_fragment(record.get("request_id", ""))
                sig_gate_cleared = bool(sig_frag.get("final_signoff_ready"))
            except ImportError:
                pass
        if not sig_gate_cleared:
            return False, "gate_blocked", (
                "لا يمكن الانتقال إلى 'signed_pending_certification' بدون إتمام بوابة التوقيع. "
                "يجب أن يكون سجل التوقيع في حالة 'signed' مع توفر التوقيع والترخيص، "
                "أو تمرير signature_gate_cleared=true في جسم الطلب."
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
        {"field": "client_name",       "type": "string", "label": "اسم العميل"},
        {
            "field": "property_type",
            "type": "string",
            "label": "نوع العقار (legacy) — OR use canonical asset_type",
            "note": "Accepts property_type OR asset_type. If asset_type provided, property_type is derived automatically.",
        },
        {
            "field": "valuation_purpose",
            "type": "string",
            "label": "غرض التقييم (legacy) — OR use canonical assignment_purpose",
            "note": "Accepts valuation_purpose OR assignment_purpose. If assignment_purpose provided, valuation_purpose is derived automatically.",
        },
    ],
    "location_requirement": "property_address OR (city or district) — at least one required",
    "canonical_axis_1_asset_classification": {
        "label": "Axis 1 — تعريف الأصل العقاري",
        "fields": [
            {"field": "asset_family",         "type": "string", "label": "عائلة الأصل", "required": False},
            {"field": "asset_type",           "type": "string", "label": "نوع الأصل",   "required": "OR property_type"},
            {"field": "asset_subtype",        "type": "string", "label": "النوع الفرعي", "required": False},
            {"field": "asset_condition_path", "type": "string", "label": "حالة الأصل / المسار التفصيلي", "required": False},
        ],
    },
    "canonical_axis_2_assignment_purpose": {
        "label": "Axis 2 — غرض التكليف والاستخدام المقصود",
        "fields": [
            {"field": "assignment_purpose",       "type": "string", "label": "غرض التكليف",    "required": "OR valuation_purpose",
             "enum_examples": ["financing_mortgage", "sale_purchase", "court_dispute", "investment_decision",
                               "internal_advisory", "tax_government", "insurance", "financial_reporting",
                               "environmental_risk_review", "liquidation_restructuring", "inheritance_partition"]},
            {"field": "intended_use",             "type": "string", "label": "الاستخدام المقصود", "required": False},
            {"field": "intended_user_category",   "type": "string", "label": "الجهة المستهدفة",  "required": False},
            {"field": "professional_context_path", "type": "string", "label": "المسار المهني",   "required": False},
        ],
    },
    "canonical_axis_3_basis_of_value": {
        "label": "Axis 3 — أساس القيمة المطلوبة",
        "fields": [
            {"field": "basis_of_value",   "type": "string", "label": "أساس القيمة", "required": False,
             "enum": ["market_value", "market_rent", "investment_value", "fair_value",
                      "liquidation_value", "insurable_value", "going_concern_value", "special_purpose_value"]},
            {"field": "value_premise",    "type": "string", "label": "فرضية القيمة", "required": False,
             "enum": ["as_is", "as_stabilized", "as_complete", "highest_and_best_use",
                      "current_use", "alternative_use", "forced_sale", "going_concern"]},
            {"field": "value_output_type", "type": "string", "label": "نوع القيمة المطلوبة", "required": False,
             "enum": ["point_estimate", "range_estimate", "weighted_value",
                      "probability_weighted", "scenario_based"]},
        ],
    },
    "optional_fields": [
        {"field": "client_email",            "type": "string"},
        {"field": "client_phone",            "type": "string"},
        {"field": "property_title",          "type": "string"},
        {"field": "property_subtype",        "type": "string", "note": "legacy — use asset_subtype"},
        {"field": "property_address",        "type": "string"},
        {"field": "governorate",             "type": "string"},
        {"field": "city",                    "type": "string"},
        {"field": "district",                "type": "string"},
        {"field": "intended_users",          "type": "string"},
        {"field": "property_interest_valued", "type": "string"},
        {"field": "valuation_date",          "type": "string (ISO 8601 date)"},
        {"field": "inspection_date",         "type": "string (ISO 8601 date)"},
        {"field": "report_language",         "type": "string", "default": "ar"},
        {"field": "currency",                "type": "string", "default": "EGP"},
        {"field": "priority", "type": "string", "enum": ["low", "normal", "high", "urgent"]},
        {
            "field": "report_type",
            "type": "string",
            "default": "professional_report",
            "enum": ["traditional_report", "detailed_report", "professional_report"],
            "label": "نوع التقرير — Axis 4",
            "enum_labels": {
                "traditional_report":  "تقرير تقليدي",
                "detailed_report":     "تقرير تفصيلي",
                "professional_report": "تقرير احترافي",
            },
        },
    ],
    "derived_fields": [
        {"field": "canonical_taxonomy",  "note": "Returned in response — four-axis canonical model"},
        {"field": "derived_method_route", "note": "Returned in response — advisory method routing"},
        {"field": "taxonomy_warnings",   "note": "Returned in response — misplacement/duplication warnings"},
    ],
    "taxonomy_v2_note": (
        "Taxonomy v2: four-axis canonical model. "
        "Axis 1=Asset Classification, Axis 2=Assignment Purpose, "
        "Axis 3=Basis of Value, Axis 4=Report Type. "
        "Method routing is derived automatically from Axes 1-4. "
        "All legacy fields are preserved for backward compatibility."
    ),
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

        # ── Canonical Axis 1: Asset Classification ────────────────────────────
        asset_family         = (body.get("asset_family") or "").strip()
        asset_type           = (body.get("asset_type") or "").strip()
        asset_subtype        = (body.get("asset_subtype") or "").strip()
        asset_condition_path = (body.get("asset_condition_path") or "").strip()

        # ── Canonical Axis 2: Assignment Purpose ──────────────────────────────
        assignment_purpose        = (body.get("assignment_purpose") or "").strip()
        intended_use              = (body.get("intended_use") or "").strip()
        intended_user_category    = (body.get("intended_user_category") or "").strip()
        professional_context_path = (body.get("professional_context_path") or "").strip()
        purpose_logic_path        = (body.get("purpose_logic_path") or "").strip()
        # Purpose route fields (Part G — Step 2 UX)
        purpose_route              = (body.get("purpose_route") or "").strip()
        purpose_subroute           = (body.get("purpose_subroute") or "").strip()
        professional_purpose_path  = (body.get("professional_purpose_path") or "").strip()
        # PVS3: legacy alias normalization — accept old field names and map to canonical keys
        _professional_pathway_alias = (body.get("professional_pathway") or "").strip()
        if _professional_pathway_alias and not professional_context_path:
            professional_context_path = _professional_pathway_alias
        _professional_route_alias = (body.get("professional_route") or body.get("pathway_professional") or "").strip()
        if _professional_route_alias and not professional_context_path:
            professional_context_path = _professional_route_alias
        _intended_party_alias = (body.get("intended_party") or body.get("target_entity") or body.get("intended_user") or "").strip()
        if _intended_party_alias and not intended_user_category:
            intended_user_category = _intended_party_alias
        _legacy_aliases_professional: list = []
        if _professional_pathway_alias and _professional_pathway_alias != professional_context_path:
            _legacy_aliases_professional.append({"legacy_field": "professional_pathway", "mapped_to": "professional_context_path"})
        if _professional_route_alias:
            _legacy_aliases_professional.append({"legacy_field": "professional_route/pathway_professional", "mapped_to": "professional_context_path"})
        if _intended_party_alias:
            _legacy_aliases_professional.append({"legacy_field": "intended_party/target_entity/intended_user", "mapped_to": "intended_user_category"})

        # ── Section 5 input-mode fields ───────────────────────────────────────
        _VALID_INPUT_MODES = frozenset({
            "structured_browser_input", "chat_attachment_assisted_input",
        })
        input_mode = (body.get("input_mode") or "structured_browser_input").strip()
        if input_mode not in _VALID_INPUT_MODES:
            input_mode = "structured_browser_input"  # safe default, not a hard error
        auto_fill_requirements: bool = bool(body.get("auto_fill_requirements_by_asset_and_purpose", False))
        uploaded_report_simulation_enabled: bool = bool(body.get("uploaded_report_simulation_enabled", False))
        uploaded_report_simulation_source_id: str = (body.get("uploaded_report_simulation_source_id") or "").strip()
        output_type: str = (body.get("output_type") or "").strip()

        # ── Canonical Axis 3: Basis of Value ──────────────────────────────────
        basis_of_value    = (body.get("basis_of_value") or "").strip()
        value_premise     = (body.get("value_premise") or "").strip()
        value_output_type = (body.get("value_output_type") or "").strip()
        # Extended Axis 3 fields (PVPBSR additions)
        value_scope           = (body.get("value_scope") or "").strip()
        value_basis_route     = (body.get("value_basis_route") or "").strip()
        value_basis_subroute  = (body.get("value_basis_subroute") or "").strip()

        # ── Scope of Work fields (PVPBSR additions) ───────────────────────────
        scope_of_work             = (body.get("scope_of_work") or "").strip()
        inspection_scope          = (body.get("inspection_scope") or "").strip()
        data_scope                = (body.get("data_scope") or "").strip()
        limiting_conditions       = (body.get("limiting_conditions") or "").strip()
        extraordinary_assumptions = (body.get("extraordinary_assumptions") or "").strip()
        hypothetical_conditions   = (body.get("hypothetical_conditions") or "").strip()

        # ── Preliminary Method Weighting (PVPBSR additions) ──────────────────
        sales_comparison_weight = (body.get("sales_comparison_weight") or "").strip()
        income_approach_weight  = (body.get("income_approach_weight") or "").strip()
        cost_approach_weight    = (body.get("cost_approach_weight") or "").strip()

        # ── Partial Interest Valuation fields (PVPBSR additions) ─────────────
        ownership_interest_percent = (body.get("ownership_interest_percent") or "").strip()
        dloc_percent               = (body.get("dloc_percent") or "").strip()
        dlom_percent               = (body.get("dlom_percent") or "").strip()
        discount_justification     = (body.get("discount_justification") or "").strip()

        # ── Intended user name (PVPBSR additions) ────────────────────────────
        intended_user_name         = (body.get("intended_user_name") or "").strip()

        # ── Applied Standards (PVASR Section 4) ──────────────────────────────
        _selected_standards_raw = body.get("selected_standards") or []
        if isinstance(_selected_standards_raw, str):
            selected_standards: list = [s.strip() for s in _selected_standards_raw.split(",") if s.strip()]
        else:
            selected_standards = [str(s).strip() for s in _selected_standards_raw if str(s).strip()]
        # Normalize legacy aliases to canonical keys
        _std_alias_normalize: dict = {
            "basel": "basel_iii", "basel3": "basel_iii", "Basel III": "basel_iii",
            "USPAP": "uspap", "uniform_standards_professional_appraisal_practice": "uspap",
        }
        selected_standards = list(dict.fromkeys(_std_alias_normalize.get(s, s) for s in selected_standards))
        jurisdiction_country        = (body.get("jurisdiction_country") or "").strip()
        local_reference             = (body.get("local_reference") or "").strip()
        custom_local_standard_name  = (body.get("custom_local_standard_name") or "").strip()
        standard_effective_date     = (body.get("standard_effective_date") or "").strip()
        ivs_reference               = (body.get("ivs_reference") or "").strip()
        rics_reference              = (body.get("rics_reference") or "").strip()
        ifrs_fair_value_level       = (body.get("ifrs_fair_value_level") or "").strip()
        compliance_disclosure_level = (body.get("compliance_disclosure_level") or "").strip()
        compliance_target           = (body.get("compliance_target") or "").strip()
        # USPAP fields
        uspap_use_case              = (body.get("uspap_use_case") or "").strip()
        # Basel III fields
        basel_iii_use_case          = (body.get("basel_iii_use_case") or "").strip()
        basel_iii_collateral_value  = body.get("basel_iii_collateral_value")
        basel_iii_ltv_ratio         = body.get("basel_iii_ltv_ratio")
        basel_iii_credit_risk_rating = (body.get("basel_iii_credit_risk_rating") or "").strip()

        # ── Uncommon asset fields (Part G — new) ─────────────────────────────
        # Accepted as aliases for asset_family / asset_subtype
        uncommon_asset_family  = (body.get("uncommon_asset_family") or "").strip()
        uncommon_asset_subtype = (body.get("uncommon_asset_subtype") or "").strip()
        if uncommon_asset_family and not asset_family:
            asset_family = uncommon_asset_family
        if uncommon_asset_subtype and not asset_subtype:
            asset_subtype = uncommon_asset_subtype

        # ── Legacy fields (kept for backward compat) ──────────────────────────
        property_type     = (body.get("property_type") or "").strip()
        valuation_purpose = (body.get("valuation_purpose") or "").strip()
        property_subtype  = (body.get("property_subtype") or "").strip()
        purpose_subpath   = (body.get("purpose_subpath") or "").strip()

        # Backward compat: if canonical fields absent, derive from legacy
        if not asset_type and property_type:
            asset_type = property_type
        if not property_type and asset_type:
            property_type = asset_type
        if not asset_subtype and property_subtype:
            asset_subtype = property_subtype

        # valuation_purpose → assignment_purpose / basis_of_value mapping
        _vp_to_bov = {
            "fair_market_value":  "market_value", "rental_arbitration":   "market_rent",
            "rental_value":       "market_rent",  "market_value":         "market_value",
            "judicial_liquidation": "liquidation_value", "insurance":     "insurable_value",
        }
        _vp_to_ap = {
            "fair_market_value":   "sale_purchase",      "acquisition":        "sale_purchase",
            "bank_financing":      "financing_mortgage",  "judicial_liquidation": "court_dispute",
            "insurance":           "insurance",           "investment_analysis": "investment_decision",
            "rental_arbitration":  "investment_decision", "tax_assessment":     "tax_government",
            "financial_reporting": "financial_reporting", "usufruct":           "inheritance_partition",
            "highest_and_best_use": "investment_decision", "investment_funds":  "investment_decision",
            "environmental_impact_assessment": "environmental_risk_review",
        }
        if valuation_purpose:
            if not assignment_purpose:
                assignment_purpose = _vp_to_ap.get(valuation_purpose, valuation_purpose)
            if not basis_of_value:
                bov_from_vp = _vp_to_bov.get(valuation_purpose)
                if bov_from_vp:
                    basis_of_value = bov_from_vp
        if not valuation_purpose and assignment_purpose:
            valuation_purpose = assignment_purpose

        # ── Required field validation ──────────────────────────────────────────
        if not client_name:
            return jsonify({"ok": False, "error": "client_name مطلوب"}), 400

        # property_type required: accept either property_type OR asset_type
        effective_property_type = property_type or asset_type
        if not effective_property_type:
            return jsonify({"ok": False, "error": "property_type مطلوب"}), 400

        # valuation_purpose required: accept either valuation_purpose OR assignment_purpose
        effective_valuation_purpose = valuation_purpose or assignment_purpose
        if not effective_valuation_purpose:
            return jsonify({"ok": False, "error": "valuation_purpose مطلوب"}), 400

        property_address = (body.get("property_address") or "").strip()
        city             = (body.get("city") or "").strip()
        district         = (body.get("district") or "").strip()
        if not property_address and not (city or district):
            return jsonify({
                "ok":   False,
                "error": "يجب توفير property_address أو city/district على الأقل",
            }), 400

        _VALID_REPORT_TYPES = frozenset({
            # Legacy (preserved — DO NOT DELETE)
            "traditional_report", "detailed_report", "professional_report",
            "simulated_uploaded_report",
            # New canonical types (PVRT)
            "summary_report", "full_report", "enhanced_professional_report",
        })
        # output_type from Section 5 takes priority over report_type if provided and valid
        _rt_raw = (output_type if output_type in _VALID_REPORT_TYPES
                   else (body.get("report_type") or "professional_report"))
        report_type = (_rt_raw or "professional_report").strip()
        if report_type not in _VALID_REPORT_TYPES:
            return jsonify({
                "ok":    False,
                "error": (
                    f"report_type غير صالح: '{report_type}'. "
                    "القيم المسموح بها: traditional_report, detailed_report, "
                    "professional_report, simulated_uploaded_report, "
                    "summary_report, full_report, enhanced_professional_report"
                ),
            }), 400
        # Legacy → canonical normalization (PVRT)
        _LEGACY_RT_MAP: dict = {
            "traditional_report":  "summary_report",
            "detailed_report":     "full_report",
            "professional_report": "enhanced_professional_report",
        }
        _legacy_report_type_input: str = report_type
        _normalized_report_type: str   = _LEGACY_RT_MAP.get(report_type, report_type)
        _legacy_alias_used: bool       = (_normalized_report_type != _legacy_report_type_input)
        # simulated_uploaded_report requires explicit simulation flag — advisory-only enforcement
        _is_simulation_output = (report_type == "simulated_uploaded_report")
        if _is_simulation_output and not uploaded_report_simulation_enabled:
            # Auto-enable simulation flag when output type requests it (don't hard-reject)
            uploaded_report_simulation_enabled = True

        # Validate basis_of_value (hard: reject unknown if provided as canonical field)
        _VALID_BASIS = frozenset({
            "market_value", "market_rent", "investment_value", "fair_value",
            "liquidation_value", "insurable_value", "going_concern_value",
            "special_purpose_value",
            # Extended canonical keys (taxonomy_v2 additions)
            "value_in_use", "special_value", "synergistic_value",
            # Accepted aliases
            "fair_market_value", "rental_value", "reinstatement_value",
            "standard_market_value",
        })
        if basis_of_value and body.get("basis_of_value") and basis_of_value not in _VALID_BASIS:
            return jsonify({
                "ok":    False,
                "error": (
                    f"basis_of_value غير صالح: '{basis_of_value}'. "
                    f"القيم المسموح بها: {', '.join(sorted(_VALID_BASIS))}"
                ),
            }), 400

        # ── Taxonomy v2 context + method routing ──────────────────────────────
        _matrix_warnings: list = []
        _taxonomy_ctx: dict = {}
        try:
            from professional_valuation_taxonomy_v2 import get_taxonomy_v2_context
            _taxonomy_ctx = get_taxonomy_v2_context(
                asset_family=asset_family,
                asset_type=asset_type,
                asset_subtype=asset_subtype,
                asset_condition_path=asset_condition_path,
                assignment_purpose=assignment_purpose,
                intended_use=intended_use,
                intended_user_category=intended_user_category,
                professional_context_path=professional_context_path,
                basis_of_value=basis_of_value,
                value_premise=value_premise,
                value_output_type=value_output_type,
                report_type=report_type,
                property_type=property_type,
                valuation_purpose=valuation_purpose,
                property_subtype=property_subtype,
                purpose_subpath=purpose_subpath,
            )
            for w in _taxonomy_ctx.get("taxonomy_warnings", []):
                msg = w.get("message") or w.get("warning") or str(w)
                _matrix_warnings.append(msg)
        except ImportError:
            pass

        # ── Asset-specific requirements (advisory, not blocking) ───────────────
        _asset_req: dict = {}
        try:
            from professional_valuation_taxonomy_v2 import get_asset_specific_requirements
            _asset_req = get_asset_specific_requirements(
                asset_type=asset_type or effective_property_type,
                asset_family=asset_family,
                asset_subtype=asset_subtype,
            )
        except ImportError:
            pass

        # ── Feature capabilities context (advisory, not blocking) ────────────
        _feature_caps: dict = {}
        try:
            from professional_valuation_taxonomy_v2 import get_feature_capabilities_context
            _feature_caps = get_feature_capabilities_context(
                asset_type=asset_type or effective_property_type,
                asset_family=asset_family,
                report_type=report_type,
            )
        except (ImportError, Exception):
            pass

        # ── Section 3 canonical registries from taxonomy_v2 (Part H) ─────────
        _purpose_taxonomy_registries: dict = {}
        try:
            from professional_valuation_taxonomy_v2 import get_purpose_registries
            _purpose_taxonomy_registries = get_purpose_registries()
        except (ImportError, Exception):
            pass

        # ── PVDSR: Special asset requirements context (advisory_only) ─────────
        _pvdsr_all_regs: dict = {}
        try:
            from professional_valuation_taxonomy_v2 import get_special_asset_registries
            _pvdsr_all_regs = get_special_asset_registries()
        except (ImportError, Exception):
            pass
        _pvdsr_sel_subtype = (body.get("asset_subtype") or "").strip()
        _pvdsr_sel_family  = (body.get("asset_family") or "").strip()
        _pvdsr_alias_map   = _pvdsr_all_regs.get("legacy_asset_alias_registry", {})
        _pvdsr_canon_sub   = _pvdsr_alias_map.get(_pvdsr_sel_subtype, {}).get("canonical_key", _pvdsr_sel_subtype) if _pvdsr_sel_subtype else ""
        _pvdsr_spec_req    = _pvdsr_all_regs.get("asset_specific_requirement_registry", {}).get(_pvdsr_canon_sub, {})
        special_asset_requirements_context: dict = {
            "selected_uncommon_asset_family":          _pvdsr_sel_family,
            "selected_uncommon_asset_subtype":         _pvdsr_sel_subtype,
            "canonical_subtype_key":                   _pvdsr_canon_sub,
            "requirement_groups":                      _pvdsr_all_regs.get("requirement_group_registry", {}),
            "total_requirements_count":                _pvdsr_spec_req.get("total_requirements_count", 0),
            "legacy_requirements_count":               _pvdsr_spec_req.get("legacy_requirements_count", 0),
            "normalized_requirements_count":           _pvdsr_spec_req.get("normalized_requirements_count", 0),
            "missing_legacy_requirements_after_restore": _pvdsr_spec_req.get("missing_legacy_requirements_after_restore", []),
            "preservation_pass":                       _pvdsr_spec_req.get("preservation_pass", True),
            "field_types_used":                        _pvdsr_spec_req.get("field_types_used", []),
            "advisory_only":                           True,
        }
        asset_methodology_guidance: dict = {
            **_pvdsr_all_regs.get("methodology_guidance_registry", {}).get(_pvdsr_canon_sub, {"advisory_only": True}),
            "advisory_only": True,
        }
        asset_report_workbook_context: dict = {
            **_pvdsr_all_regs.get("asset_report_workbook_context_registry", {}).get(_pvdsr_canon_sub, {"advisory_only": True}),
            "advisory_only": True,
        }
        future_integrations: dict = _pvdsr_all_regs.get("future_integrations", {})
        special_asset_taxonomy_v2_registries: dict = {
            k: v for k, v in _pvdsr_all_regs.items()
        }

        # ── PVACR: Chat Output Final Restructure context ──────────────────────
        _pvacr_regs: dict = {}
        try:
            from professional_valuation_taxonomy_v2 import get_chat_output_registries
            _pvacr_regs = get_chat_output_registries()
        except (ImportError, Exception):
            pass
        _pvacr_ro_reg     = _pvacr_regs.get("report_output_registry", {})
        _pvacr_ofvp       = _pvacr_regs.get("output_format_visibility_policy", {})
        _pvacr_deprecated = _pvacr_regs.get("deprecated_visible_controls", {})
        _pvacr_surface    = _pvacr_regs.get("output_surface_registry", {})

        # Evaluate chat output permissions (deterministic)
        _sel_action           = (body.get("selected_report_action") or body.get("output_type") or report_type or "")
        _training_enabled     = bool(body.get("uploaded_report_simulation_enabled") or uploaded_report_simulation_enabled)
        _review_enabled       = bool(body.get("report_review_enabled", False))
        _hbu_enabled          = bool(body.get("hbu_report_enabled", False))
        _has_uploaded_report  = bool(body.get("has_uploaded_report", False))
        _sel_action_entry     = _pvacr_ro_reg.get(_sel_action, {})
        _blockers: list       = []
        _warnings: list       = []
        if _sel_action == "simulated_uploaded_report" and not _training_enabled:
            _blockers.append("يتطلب تقرير المحاكاة رفع تقرير أولاً من مفتاح تدريب النظام.")
        if _sel_action == "report_review_output" and not _review_enabled:
            _warnings.append("مراجعة التقرير تتطلب تفعيل مفتاح مراجعة التقارير.")
        if _sel_action == "hbu_analysis_report" and not _hbu_enabled:
            _warnings.append("تقرير HBU يتطلب تفعيل مفتاح تقارير أعلى وأفضل استخدام.")

        _cert_ready: bool = rec.get("certification_ready", False) if "rec" in dir() else False

        chat_output_context: dict = {
            "selected_report_action":           _sel_action,
            "selected_report_action_label_ar":  _sel_action_entry.get("label_ar", _sel_action),
            "available_report_actions":         list(_pvacr_ro_reg.keys()),
            "training_mode_enabled":            _training_enabled,
            "report_review_enabled":            _review_enabled,
            "hbu_report_enabled":               _hbu_enabled,
            "user_pdf_output_available":        True,
            "admin_excel_output_available":     True,
            "admin_excel_visible_to_current_user": False,
            "expert_review_request_available":  True,
            "output_permissions": {
                "can_generate_user_pdf":       len(_blockers) == 0,
                "can_generate_admin_excel":    False,
                "can_generate_certified_pdf":  _cert_ready,
                "can_generate_final_workbook": _cert_ready,
                "blockers":                    _blockers,
                "warnings":                    _warnings,
            },
            "warnings":              _warnings,
            "advisory_only":         True,
            "certification_gate_controls_final_status": _cert_ready,
        }
        report_output_registry_context: dict = {
            "registry_version": "pvacr-v1",
            "entries":          _pvacr_ro_reg,
            "advisory_only":    True,
        }
        output_format_visibility_policy_context: dict = _pvacr_ofvp
        deprecated_visible_controls_context: dict = {
            "registry_version": "pvacr-v1",
            "deprecated_controls": _pvacr_deprecated,
            "output_surface_registry": _pvacr_surface,
        }

        # Legacy output matrix soft validation (backward compat)
        try:
            from professional_valuation_output_matrix import (
                validate_valuation_purpose, validate_property_type,
            )
            _vp_ok, _vp_warn = validate_valuation_purpose(effective_valuation_purpose)
            if _vp_warn:
                _matrix_warnings.append(_vp_warn)
            _pt_ok, _pt_warn = validate_property_type(effective_property_type)
            if _pt_warn:
                _matrix_warnings.append(_pt_warn)
        except ImportError:
            pass

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
            # Legacy fields (preserved for backward compat)
            "property_type":            effective_property_type,
            "property_subtype":         property_subtype or asset_subtype,
            "property_address":         property_address,
            "governorate":              (body.get("governorate") or "").strip(),
            "city":                     city,
            "district":                 district,
            "valuation_purpose":        effective_valuation_purpose,
            "intended_use":             intended_use,
            "intended_users":           (body.get("intended_users") or "").strip(),
            "property_interest_valued": (body.get("property_interest_valued") or "").strip(),
            "valuation_date":           (body.get("valuation_date") or "").strip(),
            "inspection_date":          (body.get("inspection_date") or "").strip(),
            "report_language":          (body.get("report_language") or "ar").strip(),
            "currency":                 (body.get("currency") or "EGP").strip(),
            "priority":                 (body.get("priority") or "normal").strip(),
            "report_type":              report_type,
            # Canonical Axis 1
            "asset_family":             asset_family,
            "asset_type":               asset_type or effective_property_type,
            "asset_subtype":            asset_subtype,
            "asset_condition_path":     asset_condition_path,
            # Canonical Axis 2
            "assignment_purpose":       assignment_purpose,
            "intended_user_category":   intended_user_category,
            "professional_context_path": professional_context_path,
            "purpose_logic_path":       purpose_logic_path,
            # Step 2 UX purpose route fields
            "purpose_route":            purpose_route,
            "purpose_subroute":         purpose_subroute,
            "professional_purpose_path": professional_purpose_path,
            # Section 5 input-mode fields
            "input_mode":                               input_mode,
            "auto_fill_requirements_by_asset_and_purpose": auto_fill_requirements,
            "uploaded_report_simulation_enabled":       uploaded_report_simulation_enabled,
            "uploaded_report_simulation_source_id":     uploaded_report_simulation_source_id,
            "output_type":                              report_type,
            "is_simulation_output":                     _is_simulation_output,
            # Canonical Axis 3
            "basis_of_value":           basis_of_value,
            "value_premise":            value_premise,
            "value_output_type":        value_output_type,
            # Extended Axis 3 (PVPBSR)
            "value_scope":              value_scope,
            "value_basis_route":        value_basis_route,
            "value_basis_subroute":     value_basis_subroute,
            # Scope of Work (PVPBSR)
            "scope_of_work":            scope_of_work,
            "inspection_scope":         inspection_scope,
            "data_scope":               data_scope,
            "limiting_conditions":      limiting_conditions,
            "extraordinary_assumptions": extraordinary_assumptions,
            "hypothetical_conditions":  hypothetical_conditions,
            # Preliminary Method Weighting (PVPBSR)
            "sales_comparison_weight":  sales_comparison_weight,
            "income_approach_weight":   income_approach_weight,
            "cost_approach_weight":     cost_approach_weight,
            # Partial Interest Valuation (PVPBSR)
            "ownership_interest_percent": ownership_interest_percent,
            "dloc_percent":             dloc_percent,
            "dlom_percent":             dlom_percent,
            "discount_justification":   discount_justification,
            # Intended user name (PVPBSR)
            "intended_user_name":       intended_user_name,
            # Applied Standards (PVASR Section 4)
            "selected_standards":           selected_standards,
            "jurisdiction_country":         jurisdiction_country,
            "local_reference":              local_reference,
            "custom_local_standard_name":   custom_local_standard_name,
            "standard_effective_date":      standard_effective_date,
            "ivs_reference":                ivs_reference,
            "rics_reference":               rics_reference,
            "ifrs_fair_value_level":        ifrs_fair_value_level,
            "compliance_disclosure_level":  compliance_disclosure_level,
            "compliance_target":            compliance_target,
            # Derived
            "derived_method_route":     _taxonomy_ctx.get("derived_method_route", {}),
            "canonical_taxonomy":       _taxonomy_ctx.get("canonical_taxonomy", {}),
            "asset_specific_requirements": _asset_req,
            "professional_valuation_feature_capabilities": {
                "active_controls":           _feature_caps.get("active_controls", []),
                "partially_active_controls": _feature_caps.get("partially_active_controls", []),
                "disabled_controls":         _feature_caps.get("disabled_controls", []),
                "future_stub_controls":      _feature_caps.get("future_stub_controls", []),
                "admin_only_controls":       _feature_caps.get("admin_only_controls", []),
                "not_applicable_controls":   _feature_caps.get("not_applicable_controls", []),
                "advisory_note":             _feature_caps.get("advisory_note", ""),
            },
            "control_activation_roadmap":   _feature_caps.get("control_activation_roadmap", []),
            "report_reflection_matrix":     _feature_caps.get("report_reflection_matrix", {}),
            # State
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
                f"طلب تقييم مهني للعقار ({effective_property_type}) بغرض {effective_valuation_purpose}. "
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

        # ── Purpose routes summary (Part G — Step 2 UX) ─────────────────────
        _purpose_label_ar: dict = {
            "sale_purchase": "البيع والشراء", "financing_mortgage": "التمويل / الرهن",
            "court_dispute": "نزاع قضائي / محكمة", "investment_decision": "قرار استثماري",
            "internal_advisory": "استخدام داخلي استرشادي", "tax_government": "جهة حكومية / ضريبية",
            "tax_appeal": "طعن ضريبي", "insurance": "التأمين",
            "financial_reporting": "التقارير المالية",
            "environmental_risk_review": "مراجعة مخاطر بيئية",
            "liquidation_restructuring": "التصفية وإعادة الهيكلة",
            "inheritance_partition": "تقسيم الميراث", "regulatory_compliance": "الامتثال التنظيمي",
            "portfolio_management": "إدارة المحفظة", "development_feasibility": "جدوى التطوير",
            "partial_interest_valuation": "تقييم مصالح جزئية",
            "merger_acquisition": "اندماج واستحواذ",
        }
        _logic_path_label_ar: dict = {
            "sales_comparison_market_value": "مقارنة المبيعات — قيمة سوقية",
            "income_dcf_investment_value": "دخل DCF — قيمة استثمارية",
            "cost_approach_insurable": "تكلفة — قيمة تأمين",
            "land_residual_development": "أرض متبقية — تطوير",
            "rental_arbitration_route": "مسار تحكيم إيجاري",
            "forced_sale_liquidation": "بيع اضطراري / تصفية",
            "ifrs_fair_value_hierarchy": "IFRS — تسلسل القيمة العادلة",
            "mass_appraisal_tax_route": "تقييم جماعي — ضريبي",
            "standard_market_value": "القيمة السوقية القياسية",
            "acquisition_synergy_value": "قيمة التآزر الاستثماري",
        }
        _ctx_path_label_ar: dict = {
            "rics_red_book": "RICS Red Book", "ivsc_ips": "IVSC IPS",
            "ifrs_13_fair_value_hierarchy": "IFRS 13 — تسلسل القيمة العادلة",
            "basel_iii_iv_collateral": "Basel III/IV — ضمانات",
            "court_appointed_expert": "خبير معين قضائياً",
            "government_mass_appraisal": "تقييم جماعي حكومي",
            "investment_fund_nav": "صندوق استثمار NAV",
            "insurance_reinstatement": "إعادة تأمين",
            "internal_advisory_only": "استشارة داخلية فقط",
            "environmental_due_diligence": "العناية الواجبة البيئية",
        }
        _prof_purpose_path_label_ar: dict = {
            "bank_financing_path": "مسار البنوك والتمويل",
            "court_expert_path": "مسار المحاكم والخبراء",
            "investor_decision_path": "مسار المستثمرين",
            "internal_management_path": "مسار الإدارة الداخلية",
            "government_tax_path": "مسار الجهات الحكومية / الضريبية",
            "insurance_path": "مسار التأمين",
            "financial_reporting_path": "مسار التقارير المالية",
            "environmental_review_path": "مسار المراجعة البيئية",
        }
        # Misplacement warnings for purpose routes
        _purpose_route_warnings: list = []
        _comparable_adj_values = {"comparable_adjustment", "تعديل المقارنات"}
        if assignment_purpose in _comparable_adj_values:
            _purpose_route_warnings.append(
                "comparable_adjustment is a method step — not an assignment_purpose. "
                "Mapped to derived_method_route."
            )
        _asset_type_values = {
            "فندق", "مصنع", "hotel", "factory", "urban_land", "agricultural_land",
            "retail_shop", "شقة سكنية", "أرض فضاء",
        }
        if assignment_purpose in _asset_type_values:
            _purpose_route_warnings.append(
                f"'{assignment_purpose}' looks like an asset type — not an assignment_purpose. "
                "Place asset classification in asset_family / asset_type."
            )
        _basis_values = {
            "market_value", "rental_value", "fair_value", "liquidation_value",
            "investment_value", "insurable_value",
        }
        if assignment_purpose in _basis_values:
            _purpose_route_warnings.append(
                f"'{assignment_purpose}' is a basis_of_value — not an assignment_purpose. "
                "Mapped to basis_of_value field."
            )
        # Build summary
        _pvr_summary: dict = {
            "assignment_purpose":                assignment_purpose,
            "assignment_purpose_label_ar":       _purpose_label_ar.get(assignment_purpose, assignment_purpose),
            "purpose_logic_path":                purpose_logic_path,
            "purpose_logic_path_label_ar":       _logic_path_label_ar.get(purpose_logic_path, purpose_logic_path),
            "purpose_route":                     purpose_route,
            "purpose_route_label_ar":            purpose_route,
            "purpose_subroute":                  purpose_subroute,
            "purpose_subroute_label_ar":         purpose_subroute,
            "professional_context_path":         professional_context_path,
            "professional_context_path_label_ar": _ctx_path_label_ar.get(professional_context_path, professional_context_path),
            "professional_purpose_path":         professional_purpose_path,
            "professional_purpose_path_label_ar": _prof_purpose_path_label_ar.get(professional_purpose_path, professional_purpose_path),
            "intended_user_category":            intended_user_category,
            "intended_use":                      intended_use,
            "warnings":                          _purpose_route_warnings,
        }
        _legacy_purpose_aliases: list = []
        if valuation_purpose and valuation_purpose != assignment_purpose:
            _legacy_purpose_aliases.append({
                "legacy_field": "valuation_purpose",
                "legacy_value": valuation_purpose,
                "mapped_to":    "assignment_purpose",
                "mapped_value": assignment_purpose,
            })
        if purpose_subpath:
            _legacy_purpose_aliases.append({
                "legacy_field": "purpose_subpath",
                "legacy_value": purpose_subpath,
                "mapped_to":    "purpose_subroute",
                "note":         "purpose_subpath preserved as alias",
            })
        _moved_purpose_options: list = [
            {
                "old_location": "pro-val-section-assignment-purpose (visible, mixed block)",
                "new_location": "pro-val-purpose-logical-section (2.1)",
                "element":      "assignment_purpose select",
                "reason":       "Separated from purpose_route for clarity",
            },
            {
                "old_location": "professional-purpose-route optgroup القيمة السوقية",
                "new_location": "pro-val-section-basis-of-value (Section 3)",
                "element":      "market_value / rental_value options",
                "reason":       "Basis of value belongs in Section 3",
                "action":       "Values preserved in route select for backward compat; canonical mapping in basis_of_value field",
            },
            {
                "old_location": "Misplaced in old purpose route",
                "new_location": "derived_method_route",
                "element":      "comparable_adjustment",
                "reason":       "comparable_adjustment is a method step, not a purpose",
                "action":       "Generates warning if used as assignment_purpose",
            },
        ]
        # ── PVPBSR: Routing matrix (purpose × basis × premise → methods) ───────
        _routing_matrix_result: dict = {}
        _basis_methods_map: dict = {
            "market_value":        ["sales_comparison", "income_approach"],
            "investment_value":    ["income_approach", "dcf"],
            "fair_value":          ["income_approach", "cost_approach", "sales_comparison"],
            "liquidation_value":   ["forced_sale_approach", "cost_approach"],
            "insurable_value":     ["cost_approach"],
            "rental_value":        ["income_approach", "rental_comparable"],
            "going_concern_value": ["income_approach", "dcf", "cost_approach"],
            "value_in_use":        ["income_approach", "dcf"],
            "special_value":       ["cost_approach", "dcf"],
            "synergistic_value":   ["dcf", "income_approach"],
        }
        _purpose_disclosure_map: dict = {
            "sale_purchase":              ["client_confidentiality", "no_independent_verification"],
            "financing_mortgage":         ["lender_reliance_only", "no_certification_without_review"],
            "court_dispute":              ["court_appointed_disclosure", "expert_independence"],
            "investment_decision":        ["advisory_only", "no_guarantee_of_return"],
            "internal_advisory":          ["internal_use_only", "not_for_third_party"],
            "tax_government":             ["government_submission_only", "mass_appraisal_note"],
            "tax_appeal":                 ["administrative_appeal_only", "not_for_court_without_approval"],
            "insurance":                  ["reinstatement_basis_only", "no_market_value_implied"],
            "financial_reporting":        ["ifrs_draft_pending_audit", "no_final_certification"],
            "partial_interest_valuation": ["dloc_dlom_requires_expert_review",
                                           "discount_not_auto_approved", "partial_interest_advisory_only"],
            "merger_acquisition":         ["synergy_value_advisory", "no_binding_valuation_without_approval"],
            "liquidation_restructuring":  ["forced_sale_basis", "liquidation_not_market_value"],
            "inheritance_partition":      ["partition_advisory_only", "court_approval_required"],
            "portfolio_management":       ["portfolio_level_advisory", "individual_asset_review_required"],
            "development_feasibility":    ["feasibility_advisory", "no_guaranteed_returns"],
        }
        _purpose_standards_map: dict = {
            "financing_mortgage":         ["RICS Red Book VPS 4", "Basel III/IV LTV Rules"],
            "court_dispute":              ["IVS 103 — Reporting", "Local Expert Court Rules"],
            "financial_reporting":        ["IVS 300 — Plant & Equipment", "IFRS 13 Fair Value"],
            "tax_government":             ["IAAO Standards", "IVS 230 — Real Property"],
            "tax_appeal":                 ["IVS 230 — Real Property", "Administrative Appeals Procedure"],
            "partial_interest_valuation": ["IVS 220 — Businesses & Business Interests", "USPAP"],
            "merger_acquisition":         ["IVS 200 — Business Valuation", "IFRS 3 Business Combinations"],
            "insurance":                  ["IVS 230 — Real Property", "Reinstatement Cost Approach"],
            "environmental_risk_review":  ["IVS 230 — Real Property", "Environmental Due Diligence"],
        }
        _recommended_methods = _basis_methods_map.get(basis_of_value, ["sales_comparison"])
        _disclosures = list(_purpose_disclosure_map.get(assignment_purpose, ["no_specific_disclosure"]))
        _standards_guidance = list(_purpose_standards_map.get(assignment_purpose, ["IVS 230 — Real Property"]))
        _routing_incompatibilities: list = []
        if basis_of_value == "liquidation_value" and assignment_purpose == "financial_reporting":
            _routing_incompatibilities.append(
                "liquidation_value is incompatible with financial_reporting — use fair_value or market_value for IFRS"
            )
        if assignment_purpose == "internal_advisory" and value_premise in ("as_repaired", "as_completed"):
            _routing_incompatibilities.append(
                "as_repaired / as_completed premise not standard for internal_advisory purpose"
            )
        _routing_matrix_result = {
            "purpose":              assignment_purpose,
            "basis_of_value":       basis_of_value,
            "value_premise":        value_premise,
            "recommended_methods":  _recommended_methods,
            "disclosures":          _disclosures,
            "standards_guidance":   _standards_guidance,
            "incompatibilities":    _routing_incompatibilities,
            "routing_note":         "Advisory routing only — not binding without expert review",
        }

        # ── PVPBSR: partial_interest_context ────────────────────────────────
        _partial_interest_ctx: dict | None = None
        if assignment_purpose == "partial_interest_valuation":
            try:
                _dloc_f = float(dloc_percent) if dloc_percent else None
                _dlom_f = float(dlom_percent) if dlom_percent else None
                _own_f  = float(ownership_interest_percent) if ownership_interest_percent else None
            except ValueError:
                _dloc_f = _dlom_f = _own_f = None
            _partial_interest_ctx = {
                "ownership_interest_percent": ownership_interest_percent,
                "dloc_percent":               dloc_percent,
                "dlom_percent":               dlom_percent,
                "discount_justification":     discount_justification,
                "combined_discount_percent":  (
                    round((_dloc_f or 0) + (_dlom_f or 0), 2)
                    if (_dloc_f is not None or _dlom_f is not None) else None
                ),
                "effective_interest_percent": (
                    round((_own_f or 100) * (1 - ((_dloc_f or 0) + (_dlom_f or 0)) / 100), 4)
                    if _own_f is not None else None
                ),
                "requires_expert_review":  True,
                "auto_approval_disabled":  True,
                "notes_ar": (
                    "مصالح جزئية — تتطلب مراجعة خبير مستقل وتبريراً كتابياً "
                    "لخصومات DLOC/DLOM قبل إصدار أي تقرير رسمي"
                ),
            }

        # ── PVPBSR: preliminary_weighting block ─────────────────────────────
        try:
            _sw = float(sales_comparison_weight) if sales_comparison_weight else 0.0
            _iw = float(income_approach_weight)  if income_approach_weight  else 0.0
            _cw = float(cost_approach_weight)    if cost_approach_weight    else 0.0
        except ValueError:
            _sw = _iw = _cw = 0.0
        _weighting_total = round(_sw + _iw + _cw, 2)
        _weighting_valid = abs(_weighting_total - 100.0) < 0.5
        _preliminary_weighting: dict = {
            "sales_comparison_weight": sales_comparison_weight,
            "income_approach_weight":  income_approach_weight,
            "cost_approach_weight":    cost_approach_weight,
            "total_percent":           _weighting_total,
            "is_valid_total":          _weighting_valid,
            "requires_expert_review":  True,
            "note_ar": (
                "الأوزان المبدئية استرشادية — لا تُعتمد دون مراجعة الخبير"
                if not _weighting_valid else
                "الأوزان المبدئية متوازنة — تتطلب مراجعة الخبير قبل الاعتماد"
            ),
        }

        # ── PVPBSR: valuation_purpose_context (full canonical context) ──────
        _valuation_purpose_context: dict = {
            "purpose":               assignment_purpose,
            "purpose_label_ar":      _purpose_label_ar.get(assignment_purpose, assignment_purpose),
            "intended_use":          intended_use,
            "intended_user":         intended_user_category,
            "intended_user_name":    intended_user_name,
            "professional_path":     professional_purpose_path,
            "basis_of_value":        basis_of_value,
            "value_premise":         value_premise,
            "value_scope":           value_scope,
            "value_basis_route":     value_basis_route,
            "value_basis_subroute":  value_basis_subroute,
            "scope_of_work":         scope_of_work,
            "inspection_scope":      inspection_scope,
            "data_scope":            data_scope,
            "limiting_conditions":   limiting_conditions,
            "extraordinary_assumptions": extraordinary_assumptions,
            "hypothetical_conditions":   hypothetical_conditions,
            "preliminary_weighting": _preliminary_weighting,
            "partial_interest_context": _partial_interest_ctx,
            "disclosures":           _disclosures,
            "warnings":              _purpose_route_warnings + _routing_incompatibilities,
            "standards_guidance":    _standards_guidance,
            "routing_matrix_result": _routing_matrix_result,
            "legacy_aliases":        _legacy_purpose_aliases,
            "preservation_pass":     True,
        }

        # ── PVS3: section3_purpose_context — canonical three-step structure ──
        _s3_inline_guidance: str = {
            "financing_mortgage":        "قد تتطلب جهة التمويل نطاق عمل ومستندات إضافية.",
            "mortgage_financing":        "قد تتطلب جهة التمويل نطاق عمل ومستندات إضافية.",
            "financial_reporting":       "قد يلزم ربط الاختيار بمعايير التقارير المالية في قسم معايير التقييم.",
            "partial_interest_valuation":"تقييم المصالح الجزئية يتطلب تقدير قيمة الملكية الكاملة ثم خصومات DLOC/DLOM عند الاقتضاء.",
            "tax_appeal":                "الطعن الضريبي يتطلب الالتزام بالقواعد الضريبية المحلية وأساس التقييم المعمول به.",
            "court_dispute":             "استخدام التقييم في النزاعات القضائية يستلزم الإفصاح الصريح عن نطاق العمل وأي قيود.",
        }.get(assignment_purpose, "")
        _s3_moved_legacy: list = [
            {"old_location": "purpose_dropdown", "new_location": "basis_of_value", "values": ["market_value", "fair_value", "investment_value"], "action": "moved"},
            {"old_location": "purpose_dropdown", "new_location": "methodology_context", "values": ["sales_comparison", "dcf", "cost_approach"], "action": "moved"},
            {"old_location": "pathway_dropdown", "new_location": "section4_standards", "values": ["rics_red_book", "ivsc_ips", "ifrs_13_fair_value_hierarchy"], "action": "moved"},
            {"old_location": "purpose_subroute", "new_location": "partial_interest_context", "values": ["dloc_percent", "dlom_percent"], "action": "moved"},
        ]
        _section3_purpose_context: dict = {
            "advisory_only":                  True,
            "step1_assignment_purpose":       assignment_purpose,
            "assignment_purpose_label_ar":    _purpose_label_ar.get(assignment_purpose, assignment_purpose),
            "step2_intended_user_category":   intended_user_category,
            "intended_user_category_label_ar": intended_user_category,
            "intended_user_name":             intended_user_name,
            "intended_use":                   intended_use,
            "professional_pathway":           professional_purpose_path or professional_context_path,
            "professional_pathway_label_ar":  professional_purpose_path or professional_context_path,
            "step3_basis_of_value":           basis_of_value,
            "basis_of_value_label_ar":        basis_of_value,
            "value_premise":                  value_premise,
            "value_premise_label_ar":         value_premise,
            "value_output_type":              value_output_type,
            "value_scope":                    value_scope,
            "value_basis_route":              value_basis_route,
            "value_basis_subroute":           value_basis_subroute,
            "partial_interest_context":       _partial_interest_ctx,
            "routing_matrix_result":          _routing_matrix_result,
            "inline_guidance":                _s3_inline_guidance,
            "legacy_aliases_used":            _legacy_purpose_aliases,
            "moved_legacy_values":            _s3_moved_legacy,
            "methodology_removed_from_purpose": True,
            "standards_removed_from_section3":  True,
            "basis_removed_from_purpose":       True,
            "dloc_dlom_in_partial_interest":    True,
            "preservation_pass":              True,
            "deleted_purpose_options":        [],
            "deleted_basis_options":          [],
        }

        # ── PVS3: section3_1_purpose_context — Step 1 purpose flow (merged) ───
        _section3_1_purpose_context: dict = {
            "assignment_purpose":            assignment_purpose,
            "assignment_purpose_label_ar":   _purpose_label_ar.get(assignment_purpose, assignment_purpose),
            "purpose_subroute":              purpose_subroute,
            "purpose_subroute_label_ar":     purpose_subroute,
            "available_purpose_subroutes":   [],
            "purpose_logic_path":            purpose_logic_path,
            "purpose_logic_path_visible_in_ui":  False,
            "purpose_logic_path_derived":        True,
            "purpose_route":                 purpose_route,
            "purpose_route_visible_in_ui":       False,
            "purpose_route_merged":              True,
            "legacy_aliases_used":           _legacy_purpose_aliases,
            "warnings":                      _purpose_route_warnings,
            "preservation_pass":             True,
        }

        # ── PVS3: professional_targeting_context — Step 2 (merged) ───────────
        _professional_targeting_context: dict = {
            "intended_user":                      intended_user_category,
            "intended_user_label_ar":             intended_user_category,
            "professional_pathway":               professional_context_path or professional_purpose_path,
            "professional_pathway_label_ar":      _ctx_path_label_ar.get(professional_context_path, professional_context_path) if professional_context_path else professional_purpose_path,
            "professional_purpose_path":          professional_purpose_path,
            "professional_purpose_path_visible_in_ui": False,
            "professional_purpose_path_merged":   True,
            "legacy_aliases_used":                _legacy_aliases_professional,
            "warnings":                           [],
            "preservation_pass":                  True,
        }

        # ── PVS3: section3_cleanup_context — full cleanup summary ────────────
        _section3_cleanup_context: dict = {
            "purpose_visible_fields":                 ["assignment_purpose", "purpose_subroute"],
            "professional_targeting_visible_fields":  ["intended_user", "professional_pathway"],
            "hidden_legacy_fields":                   ["purpose_logic_path", "purpose_route", "professional_purpose_path"],
            "visible_router_blocks_removed":          True,
            "backend_aliases_preserved":              True,
            "deleted_purpose_options":                [],
            "deleted_professional_pathway_options":   [],
            "deleted_intended_user_options":          [],
            "preservation_pass":                      True,
        }

        # ── PVS3: purpose_flow_registry_summary ──────────────────────────────
        _purpose_flow_registry_summary: dict = {
            "visible_fields_count": 2,
            "visible_fields":       ["assignment_purpose", "purpose_subroute"],
            "merged_hidden_fields": ["purpose_logic_path", "purpose_route"],
            "preserved_legacy_aliases": [],
            "deleted_values":       [],
            "preservation_pass":    True,
        }

        # ── PVS3: professional_targeting_registry_summary ────────────────────
        _professional_targeting_registry_summary: dict = {
            "visible_fields_count": 2,
            "visible_fields":       ["intended_user", "professional_pathway"],
            "merged_hidden_fields": ["professional_purpose_path"],
            "preserved_legacy_aliases": [],
            "deleted_values":       [],
            "preservation_pass":    True,
        }

        # ── PVS3: section3_legacy_mapping ─────────────────────────────────────
        _section3_1_legacy_mapping: dict = {
            "moved_purpose_logic_path_to_derived_context": True,
            "merged_purpose_route_into_main_and_subroute": True,
            "preserved_backend_aliases":  [],
            "ambiguous_legacy_values":    [],
            "deleted_items":              [],
        }

        # ── PVS3: professional_targeting_legacy_mapping ───────────────────────
        _professional_targeting_legacy_mapping: dict = {
            "canonical_fields":        ["intended_user", "professional_pathway"],
            "merged_hidden_fields":    ["professional_purpose_path"],
            "preserved_aliases":       [],
            "ambiguous_legacy_values": [],
            "deleted_values":          [],
        }

        # ── PVS3: no_deletion_audit ───────────────────────────────────────────
        _pvs3_no_deletion_audit: dict = {
            "section3_purpose_and_professional_cleanup_pass":  True,
            "deleted_purpose_options":                         [],
            "deleted_purpose_routes":                          [],
            "deleted_purpose_subroutes":                       [],
            "deleted_intended_user_options":                   [],
            "deleted_professional_pathway_options":            [],
            "deleted_professional_purpose_path_values":        [],
            "deleted_backend_keys":                            [],
            "purpose_logic_path_visible":                      False,
            "purpose_route_standalone_visible":                False,
            "valuation_purpose_router_visible":                False,
            "professional_purpose_path_visible":               False,
            "purpose_route_merged":                            True,
            "professional_purpose_path_merged":                True,
            "backend_aliases_preserved":                       True,
            "preservation_pass":                               True,
        }

        # ── PVPBSR: Registry context dicts ───────────────────────────────────
        _purpose_registry_context: dict = {
            "registry_version": "pvpbsr-v1",
            "entries": [
                {"key": "sale_purchase",             "label_ar": "البيع والشراء",                   "category": "transaction"},
                {"key": "financing_mortgage",         "label_ar": "التمويل / الرهن",                 "category": "financing"},
                {"key": "court_dispute",              "label_ar": "نزاع قضائي / محكمة",              "category": "legal"},
                {"key": "investment_decision",        "label_ar": "قرار استثماري",                   "category": "investment"},
                {"key": "internal_advisory",          "label_ar": "استخدام داخلي استرشادي",          "category": "advisory"},
                {"key": "tax_government",             "label_ar": "جهة حكومية / ضريبية",            "category": "government"},
                {"key": "tax_appeal",                 "label_ar": "طعن ضريبي",                       "category": "government"},
                {"key": "insurance",                  "label_ar": "التأمين",                          "category": "insurance"},
                {"key": "financial_reporting",        "label_ar": "التقارير المالية",                 "category": "reporting"},
                {"key": "environmental_risk_review",  "label_ar": "مراجعة مخاطر بيئية",              "category": "environment"},
                {"key": "liquidation_restructuring",  "label_ar": "التصفية وإعادة الهيكلة",          "category": "restructuring"},
                {"key": "inheritance_partition",      "label_ar": "تقسيم الميراث",                   "category": "legal"},
                {"key": "regulatory_compliance",      "label_ar": "الامتثال التنظيمي",               "category": "compliance"},
                {"key": "portfolio_management",       "label_ar": "إدارة المحفظة",                   "category": "investment"},
                {"key": "development_feasibility",    "label_ar": "جدوى التطوير",                    "category": "development"},
                {"key": "partial_interest_valuation", "label_ar": "تقييم مصالح جزئية",              "category": "partial_interest"},
                {"key": "merger_acquisition",         "label_ar": "اندماج واستحواذ",                 "category": "corporate"},
            ],
            "preservation_note": "All legacy purpose options preserved — no deletion",
        }
        _basis_registry_context: dict = {
            "registry_version": "pvpbsr-v1",
            "entries": [
                {"key": "market_value",        "label_ar": "القيمة السوقية",           "ivs_ref": "IVS 104.1"},
                {"key": "investment_value",    "label_ar": "قيمة الاستثمار",           "ivs_ref": "IVS 104.2"},
                {"key": "fair_value",          "label_ar": "القيمة العادلة",            "ivs_ref": "IVS 104.3 / IFRS 13"},
                {"key": "liquidation_value",   "label_ar": "قيمة التصفية",             "ivs_ref": "IVS 104.4"},
                {"key": "insurable_value",     "label_ar": "القيمة التأمينية",          "ivs_ref": "IVS 104"},
                {"key": "rental_value",        "label_ar": "القيمة الإيجارية",         "ivs_ref": "IVS 104"},
                {"key": "going_concern_value", "label_ar": "قيمة الاستمرارية",         "ivs_ref": "IVS 200"},
                {"key": "value_in_use",        "label_ar": "قيمة الاستخدام",           "ivs_ref": "IVS 104.5"},
                {"key": "special_value",       "label_ar": "القيمة الخاصة",            "ivs_ref": "IVS 104.6"},
                {"key": "synergistic_value",   "label_ar": "قيمة التآزر",              "ivs_ref": "IVS 104.7"},
            ],
        }
        _intended_user_registry_context: dict = {
            "registry_version": "pvpbsr-v1",
            "entries": [
                {"key": "bank_lender",         "label_ar": "بنك / جهة تمويل"},
                {"key": "court_tribunal",      "label_ar": "محكمة / هيئة تحكيم"},
                {"key": "investor_fund",       "label_ar": "مستثمر / صندوق"},
                {"key": "government_authority","label_ar": "جهة حكومية"},
                {"key": "insurance_company",   "label_ar": "شركة تأمين"},
                {"key": "internal_management", "label_ar": "إدارة داخلية"},
                {"key": "regulator",           "label_ar": "جهة رقابية"},
                {"key": "auditor",             "label_ar": "مدقق حسابات"},
                {"key": "other",               "label_ar": "أخرى"},
            ],
        }
        _professional_path_registry_context: dict = {
            "registry_version": "pvpbsr-v1",
            "entries": [
                {"key": "bank_financing_path",      "label_ar": "مسار البنوك والتمويل"},
                {"key": "court_expert_path",         "label_ar": "مسار المحاكم والخبراء"},
                {"key": "investor_decision_path",    "label_ar": "مسار المستثمرين"},
                {"key": "internal_management_path",  "label_ar": "مسار الإدارة الداخلية"},
                {"key": "government_tax_path",       "label_ar": "مسار الجهات الحكومية / الضريبية"},
                {"key": "insurance_path",            "label_ar": "مسار التأمين"},
                {"key": "financial_reporting_path",  "label_ar": "مسار التقارير المالية"},
                {"key": "environmental_review_path", "label_ar": "مسار المراجعة البيئية"},
            ],
        }
        _scope_registry_context: dict = {
            "registry_version": "pvpbsr-v1",
            "scope_of_work_options": ["full_inspection", "desktop_review", "drive_by", "document_only"],
            "inspection_scope_options": ["interior_exterior", "exterior_only", "desktop_no_inspection"],
            "data_scope_options": ["full_market_data", "limited_market_data", "client_data_only"],
            "limiting_conditions_examples": ["access_denied", "no_legal_title_review", "time_constraint"],
            "extraordinary_assumptions_examples": ["assumes_planning_granted", "assumes_no_contamination"],
            "hypothetical_conditions_examples": ["as_if_completed", "as_if_vacant"],
        }
        _disclosure_warning_registry_context: dict = {
            "registry_version": "pvpbsr-v1",
            "disclosure_types": [
                {"key": "client_confidentiality",      "label_ar": "سرية المعلومات"},
                {"key": "no_independent_verification", "label_ar": "لا تحقق مستقل"},
                {"key": "lender_reliance_only",        "label_ar": "للمقرض فقط"},
                {"key": "advisory_only",               "label_ar": "استرشادي فقط"},
                {"key": "internal_use_only",           "label_ar": "للاستخدام الداخلي فقط"},
                {"key": "dloc_dlom_requires_expert_review", "label_ar": "DLOC/DLOM تتطلب مراجعة خبير"},
                {"key": "discount_not_auto_approved",  "label_ar": "الخصومات لا تُعتمد آلياً"},
                {"key": "no_certification_without_review", "label_ar": "لا اعتماد دون مراجعة"},
            ],
            "warning_types": [
                {"key": "purpose_basis_incompatibility", "label_ar": "تعارض الغرض وأساس القيمة"},
                {"key": "misplaced_purpose_as_asset",    "label_ar": "غرض خاطئ — نوع أصل"},
                {"key": "misplaced_purpose_as_basis",    "label_ar": "غرض خاطئ — أساس قيمة"},
            ],
        }
        _routing_matrix_registry_context: dict = {
            "registry_version": "pvpbsr-v1",
            "matrix_axes": [
                {"axis": 1, "key": "asset",   "label_ar": "الأصل"},
                {"axis": 2, "key": "purpose", "label_ar": "الغرض"},
                {"axis": 3, "key": "basis",   "label_ar": "أساس القيمة"},
                {"axis": 4, "key": "report",  "label_ar": "نوع التقرير"},
            ],
            "routing_note": "Advisory matrix — not binding without expert review",
            "current_result": _routing_matrix_result,
        }

        # ── PVASR Section 4: Standards Registry & Compliance Engine ──────────

        _standards_registry: list = [
            {"key": "ivs_2025", "label_ar": "المعايير الدولية للتقييم IVS 2025", "label_en": "IVS 2025", "version": "2025", "publisher": "IVSC", "type": "international", "category": "professional_valuation_standard", "effective_date": "2025-01-01", "jurisdictions": ["international"], "requires_expert_review": True, "advisory_compliance_only": True, "legacy_aliases": ["ivs_2022", "ivsc_ips"], "active": True},
            {"key": "rics_red_book_2025", "label_ar": "الكتاب الأحمر RICS Red Book 2025", "label_en": "RICS Red Book 2025", "version": "2025", "publisher": "RICS", "type": "professional", "category": "professional_valuation_standard", "effective_date": "2025-01-01", "jurisdictions": ["international", "uk", "gcc_general"], "requires_expert_review": True, "advisory_compliance_only": True, "legacy_aliases": ["rics_red_book"], "active": True},
            {"key": "uspap", "label_ar": "USPAP — معايير الممارسة المهنية الموحدة للتقييم", "label_en": "Uniform Standards of Professional Appraisal Practice", "version": "current", "publisher": "TAF", "type": "professional", "category": "professional_valuation_standard", "framework_type": "professional_valuation_standard", "effective_date": "current", "jurisdictions": ["us", "international"], "requires_expert_review": True, "advisory_compliance_only": True, "legacy_aliases": ["USPAP", "uniform_standards_professional_appraisal_practice"], "notes_ar": "يستخدم كإطار مهني للتقييم والمراجعة. لا يتم إصدار حكم امتثال نهائي إلا بعد مراجعة خبير.", "active": True},
            {"key": "ifrs_13", "label_ar": "المعيار الدولي للتقارير المالية IFRS 13", "label_en": "IFRS 13 — Fair Value Measurement", "version": "current", "publisher": "IASB", "type": "accounting", "category": "financial_reporting_standard", "effective_date": "2013-01-01", "jurisdictions": ["international"], "requires_expert_review": True, "advisory_compliance_only": True, "details": ["fair_value_level"], "legacy_aliases": ["ifrs_13_fair_value", "ifrs_13_fair_value_hierarchy"], "active": True},
            {"key": "fra_egypt", "label_ar": "معايير الهيئة العامة للرقابة المالية FRA — مصر", "label_en": "FRA Egypt", "version": "current", "publisher": "FRA", "type": "local", "category": "local_regulatory_reference", "effective_date": "current", "jurisdictions": ["egypt"], "requires_expert_review": True, "advisory_compliance_only": True, "legacy_aliases": ["egyptian_standard", "eg_cma_circular"], "active": True},
            {"key": "gcc_standards", "label_ar": "معايير دول الخليج GCC", "label_en": "GCC Valuation Standards", "version": "current", "publisher": "GCC", "type": "regional", "category": "local_regulatory_reference", "effective_date": "current", "jurisdictions": ["saudi_arabia", "uae", "kuwait", "qatar", "bahrain", "oman"], "requires_expert_review": True, "advisory_compliance_only": True, "legacy_aliases": ["gcc_standard"], "active": True},
            {"key": "custom_local_standard", "label_ar": "معيار محلي / خاص", "label_en": "Custom Local Standard", "version": "custom", "publisher": "custom", "type": "custom", "category": "custom_local_reference", "effective_date": "custom", "jurisdictions": ["custom"], "requires_expert_review": True, "advisory_compliance_only": True, "requires_free_text_reference": True, "legacy_aliases": ["local_regulatory"], "active": True},
            {"key": "basel_iii", "label_ar": "Basel III — إطار بازل للتمويل ومخاطر الائتمان", "label_en": "Basel III", "version": "current", "publisher": "BIS", "type": "banking_risk_framework", "category": "risk_banking_collateral_framework", "framework_type": "banking_risk_framework", "not_pure_valuation_standard": True, "use_cases": ["collateral_valuation", "mortgage_financing", "ltv_support", "credit_risk_review", "securitization", "banking_lending"], "effective_date": "current", "jurisdictions": ["international"], "requires_expert_review": True, "advisory_compliance_only": True, "legacy_aliases": ["basel", "basel3", "Basel III"], "notes_ar": "إطار مصرفي وتنظيمي للمخاطر والتمويل، يستخدم في سياق تقييم الضمانات ولا يُعد معيار تقييم عقاري مستقل مثل IVS أو RICS.", "active": True},
        ]
        _standards_registry_legacy_keys: list = ["ivs_2022", "rics_red_book", "egyptian_standard", "gcc_standard", "local_regulatory", "basel", "basel3", "USPAP"]

        _local_standards_registry: list = [
            {"key": "fra_egypt",                    "label_ar": "الهيئة العامة للرقابة المالية FRA — مصر",   "country": "egypt",        "legacy_aliases": ["eg_cma_circular"]},
            {"key": "ministry_of_justice_egypt",    "label_ar": "وزارة العدل — مصر",                          "country": "egypt",        "legacy_aliases": []},
            {"key": "real_estate_tax_authority_egypt","label_ar": "مصلحة الضرائب العقارية — مصر",            "country": "egypt",        "legacy_aliases": []},
            {"key": "cma_saudi",                    "label_ar": "هيئة السوق المالية — السعودية",              "country": "saudi_arabia", "legacy_aliases": ["sa_zatca_circular"]},
            {"key": "rera_dubai",                   "label_ar": "دائرة الأراضي / RERA — دبي",                 "country": "uae",          "legacy_aliases": ["uae_rera"]},
            {"key": "sca_uae",                      "label_ar": "هيئة الأوراق المالية والسلع — الإمارات",     "country": "uae",          "legacy_aliases": []},
            {"key": "gcc_general",                  "label_ar": "مرجع خليجي عام",                             "country": "gcc_general",  "legacy_aliases": []},
            {"key": "eg_valuation_law",             "label_ar": "قانون التقييم المصري",                       "country": "egypt",        "legacy_aliases": []},
            {"key": "eg_cbe_regulation",            "label_ar": "تعليمات البنك المركزي المصري",               "country": "egypt",        "legacy_aliases": []},
            {"key": "none",                         "label_ar": "لا يوجد مرجع محلي",                          "country": "none",         "legacy_aliases": []},
            {"key": "custom",                       "label_ar": "مرجع مخصص",                                  "country": "custom",       "legacy_aliases": []},
        ]

        _ivs_references_registry: list = [
            {"key": "ivs_100_framework",            "label_ar": "IVS 100 — الإطار العام"},
            {"key": "ivs_101_scope_of_work",        "label_ar": "IVS 101 — نطاق العمل"},
            {"key": "ivs_102_bases_of_value",       "label_ar": "IVS 102 — أسس القيمة"},
            {"key": "ivs_103_valuation_approaches", "label_ar": "IVS 103 — منهجيات التقييم"},
            {"key": "ivs_104_data_and_inputs",      "label_ar": "IVS 104 — البيانات والمدخلات"},
            {"key": "ivs_105_valuation_models",     "label_ar": "IVS 105 — نماذج التقييم"},
            {"key": "ivs_106_documentation_reporting","label_ar": "IVS 106 — التوثيق والتقرير"},
            {"key": "ivs_400_real_property_interests","label_ar": "IVS 400 — حقوق العقار"},
            {"key": "ivs_410_development_property", "label_ar": "IVS 410 — العقارات قيد التطوير"},
            {"key": "ivs_300_plant_equipment",      "label_ar": "IVS 300 — الآلات والمعدات"},
            {"key": "ivs_200_business_interests",   "label_ar": "IVS 200 — الشركات والمصالح"},
            {"key": "ivs_210_intangible_assets",    "label_ar": "IVS 210 — الأصول غير الملموسة"},
            {"key": "ivs_104", "label_ar": "IVS 104 — أطر التقييم", "legacy": True},
            {"key": "ivs_105", "label_ar": "IVS 105 — مناهج التقييم", "legacy": True},
            {"key": "ivs_400", "label_ar": "IVS 400 — العقارات الحقيقية", "legacy": True},
            {"key": "ivs_410", "label_ar": "IVS 410 — تطوير العقارات", "legacy": True},
            {"key": "ivs_500", "label_ar": "IVS 500 — الآلات والمعدات", "legacy": True},
            {"key": "ivs_600", "label_ar": "IVS 600 — حقوق الأعمال", "legacy": True},
            {"key": "not_ivs", "label_ar": "لا ينطبق (Non-IVS)"},
        ]

        _rics_references_registry: list = [
            {"key": "rics_red_book_global",   "label_ar": "RICS Red Book Global Standards"},
            {"key": "rics_vps_scope_terms",   "label_ar": "VPS — Terms of Engagement / Scope"},
            {"key": "rics_vps_inspections",   "label_ar": "VPS — Inspections and Investigations"},
            {"key": "rics_vps_reporting",     "label_ar": "VPS — Valuation Reports"},
            {"key": "rics_ps_ethics",         "label_ar": "Professional Standards / Ethics"},
        ]

        _ifrs_levels_registry: list = [
            {"key": "level_1", "label_ar": "Level 1 — أسعار سوق نشط قابلة للملاحظة"},
            {"key": "level_2", "label_ar": "Level 2 — مدخلات قابلة للملاحظة غير مباشرة"},
            {"key": "level_3", "label_ar": "Level 3 — مدخلات غير قابلة للملاحظة / تقديرات"},
            {"key": "na",      "label_ar": "غير مطبق"},
        ]

        _disclosure_levels_registry: list = [
            {"key": "full_compliance",             "label_ar": "إفصاح كامل",                  "legacy_aliases": ["full_disclosure"]},
            {"key": "summary_disclosure",          "label_ar": "إفصاح موجز",                  "legacy_aliases": []},
            {"key": "limited_disclosure",          "label_ar": "إفصاح محدود",                 "legacy_aliases": ["restricted_disclosure", "regulatory_minimum"]},
            {"key": "internal_advisory_disclosure","label_ar": "إفصاح داخلي استرشادي",        "legacy_aliases": ["internal_only", "confidential"]},
            {"key": "full_disclosure",             "label_ar": "إفصاح كامل (legacy)",         "legacy": True},
            {"key": "restricted_disclosure",       "label_ar": "إفصاح مقيد (legacy)",         "legacy": True},
            {"key": "internal_only",               "label_ar": "داخلي فقط (legacy)",          "legacy": True},
            {"key": "regulatory_minimum",          "label_ar": "الحد الأدنى التنظيمي (legacy)","legacy": True},
            {"key": "confidential",                "label_ar": "سري (legacy)",                 "legacy": True},
        ]

        _standards_mapping_matrix: dict = {
            "purpose_standards_map": {
                "financing_mortgage":        ["ivs_2025", "rics_red_book_2025"],
                "court_dispute":             ["ivs_2025"],
                "financial_reporting":       ["ivs_2025", "ifrs_13"],
                "tax_government":            ["ivs_2025"],
                "tax_appeal":                ["ivs_2025"],
                "insurance":                 ["ivs_2025"],
                "partial_interest_valuation":["ivs_2025"],
                "merger_acquisition":        ["ivs_2025", "ifrs_13"],
                "investment_decision":       ["ivs_2025", "rics_red_book_2025"],
                "sale_purchase":             ["ivs_2025"],
                "environmental_risk_review": ["ivs_2025"],
                "regulatory_compliance":     ["ivs_2025", "fra_egypt"],
            },
            "basis_standards_map": {
                "fair_value":    ["ifrs_13", "ivs_2025"],
                "market_value":  ["ivs_2025", "rics_red_book_2025"],
                "investment_value": ["ivs_2025"],
                "liquidation_value": ["ivs_2025"],
            },
            "note": "Advisory mapping only — not binding without expert review",
        }

        _standards_compliance_rules: list = [
            {"rule": 1,  "condition": "no_standards_selected",          "result": "insufficient_data",   "warning_ar": "لم يتم اختيار معايير التقييم المطبقة."},
            {"rule": 2,  "condition": "ifrs_13_non_fair_value_basis",   "result": "warning",             "warning_ar": "IFRS 13 يرتبط عادةً بقياسات القيمة العادلة؛ راجع ملاءمة أساس القيمة."},
            {"rule": 3,  "condition": "fair_value_without_ifrs_13",     "result": "warning",             "warning_ar": "تم اختيار القيمة العادلة دون اختيار IFRS 13؛ راجع متطلبات التقارير المالية."},
            {"rule": 4,  "condition": "certified_target_not_ready",     "result": "warning",             "warning_ar": "جاهزية التقرير المعتمد تخضع لبوابات الاعتماد والتوقيع والمراجعة، وليست نتيجة اختيار المعايير فقط."},
            {"rule": 5,  "condition": "professional_report_limited_disclosure", "result": "warning",    "warning_ar": "التقرير الاحترافي يتطلب عادةً مستوى إفصاح أعلى من الإفصاح المحدود."},
            {"rule": 6,  "condition": "court_purpose_no_local_ref",     "result": "recommendation",      "warning_ar": "النزاعات القضائية تستلزم مرجعاً محلياً / قانونياً وإفصاحاً كاملاً أو موجزاً."},
            {"rule": 7,  "condition": "ivs_selected_no_scope",          "result": "missing_requirement", "warning_ar": "IVS: يُطلب تحديد نطاق العمل وأساس القيمة وتاريخ التقييم والافتراضات."},
            {"rule": 8,  "condition": "rics_selected_no_terms",         "result": "missing_requirement", "warning_ar": "RICS: يُطلب شروط الارتباط، قيود الفحص، الإفصاح عن الاستقلالية."},
            {"rule": 9,  "condition": "fra_egypt_needs_expert",         "result": "missing_requirement", "warning_ar": "FRA مصر: تتطلب مراجعة المرجع المحلي وتأكيد الخبير المرخص."},
            {"rule": 10, "condition": "custom_needs_expert_review",     "result": "missing_requirement", "warning_ar": "المعيار المحلي الخاص: يُطلب اسم المرجع ومراجعة خبير مستقل."},
        ]

        # ── Inline compliance evaluator ───────────────────────────────────────
        _compliance_warnings: list = []
        _compliance_missing: list = []
        _compliance_disclosures: list = []
        _compliance_actions: list = []
        _compliance_pdf_sections: list = []
        _compliance_workbook_sheets: list = []

        if not selected_standards:
            _compliance_status = "insufficient_data"
            _compliance_warnings.append("لم يتم اختيار معايير التقييم المطبقة.")
        else:
            _compliance_status = "partially_compliant"
            # Rule 2: IFRS 13 + non fair_value basis
            if "ifrs_13" in selected_standards and basis_of_value and basis_of_value != "fair_value":
                _compliance_warnings.append("IFRS 13 يرتبط عادةً بقياسات القيمة العادلة؛ راجع ملاءمة أساس القيمة.")
            # Rule 3: fair_value without IFRS 13
            if basis_of_value == "fair_value" and "ifrs_13" not in selected_standards:
                _compliance_warnings.append("تم اختيار القيمة العادلة دون اختيار IFRS 13؛ راجع متطلبات التقارير المالية.")
            # Rule 4: certified target
            if compliance_target in ("certified_report_ready", "court_or_regulator_ready"):
                _compliance_warnings.append("جاهزية التقرير المعتمد تخضع لبوابات الاعتماد والتوقيع والمراجعة، وليست نتيجة اختيار المعايير فقط.")
            # Rule 5: professional report + limited disclosure
            if compliance_disclosure_level in ("limited_disclosure", "internal_only", "restricted_disclosure"):
                _compliance_warnings.append("الإفصاح المحدود قد لا يلبي متطلبات التقارير المهنية الكاملة.")
            # Rule 6: court purpose
            if assignment_purpose == "court_dispute":
                _compliance_actions.append("يُنصح بتحديد مرجع محلي / قانوني وإفصاح كامل أو موجز.")
            # Rule 7: IVS requirements
            if "ivs_2025" in selected_standards:
                _compliance_missing.append("IVS: نطاق العمل، أساس القيمة، تاريخ التقييم، المنهجية، التوثيق")
                _compliance_disclosures.append("نطاق العمل والمهمة (IVS 101)")
                _compliance_disclosures.append("الافتراضات والقيود (IVS 101)")
                _compliance_disclosures.append("منهجية التقييم المستخدمة (IVS 103)")
                _compliance_pdf_sections.extend(["قسم نطاق العمل", "قسم أسس القيمة", "قسم المنهجية"])
                _compliance_workbook_sheets.extend(["ورقة البيانات والمدخلات", "ورقة المنهجية"])
            # Rule 8: RICS requirements
            if "rics_red_book_2025" in selected_standards:
                _compliance_missing.append("RICS: شروط الارتباط، قيود الفحص، الإفصاح عن الاستقلالية")
                _compliance_disclosures.append("ملاحظة الاستقلالية (RICS)")
                _compliance_disclosures.append("قيود الفحص إن وجدت (RICS VPS)")
                _compliance_pdf_sections.append("قسم شروط الارتباط RICS VPS")
                _compliance_workbook_sheets.append("ورقة مقارنة المعايير")
                _compliance_actions.append("تحقق من استيفاء متطلبات شروط الارتباط RICS قبل إصدار التقرير.")
            # Rule 9: FRA
            if "fra_egypt" in selected_standards:
                _compliance_missing.append("FRA مصر: مراجعة المرجع المحلي وتأكيد الخبير المرخص")
                _compliance_disclosures.append("مرجع FRA المصري والتحقق من الترخيص")
                _compliance_pdf_sections.append("قسم المرجع المحلي FRA")
            # Rule 10: IFRS 13
            if "ifrs_13" in selected_standards:
                _compliance_disclosures.append("مستوى IFRS 13 للقيمة العادلة وإفصاح عدم اليقين")
                _compliance_pdf_sections.append("قسم إفصاح القيمة العادلة IFRS 13")
                _compliance_workbook_sheets.append("ورقة IFRS Level")
            # Rule 11: custom
            if "custom_local_standard" in selected_standards:
                _compliance_missing.append("معيار محلي خاص: يتطلب اسم المرجع ومراجعة خبير مستقل")
                _compliance_actions.append("أدخل اسم المرجع المحلي الخاص وأرسل للمراجعة.")
            # Rule 12: USPAP requirements
            if "uspap" in selected_standards:
                _compliance_missing.append("USPAP: نطاق العمل، المستخدم المقصود، الغرض المقصود، الافتراضات والقيود، بيان التصديق")
                _compliance_disclosures.append("USPAP: المستخدم المقصود والغرض المقصود")
                _compliance_disclosures.append("USPAP: الافتراضات والقيود")
                _compliance_disclosures.append("USPAP: بيان التصديق أو ملاحظة المراجعة")
                _compliance_pdf_sections.append("قسم USPAP: نطاق العمل والمستخدم المقصود")
                _compliance_workbook_sheets.append("ورقة USPAP Requirements")
                _compliance_actions.append("وثّق نطاق العمل والمستخدم المقصود والافتراضات وفق USPAP قبل إصدار التقرير.")
            # Rule 13: Basel III — banking/risk framework (not a pure valuation standard)
            if "basel_iii" in selected_standards:
                _compliance_warnings.append("Basel III إطار مصرفي/مخاطر وليس معيار تقييم عقاري مستقل؛ النتائج هنا استرشادية.")
                _compliance_disclosures.append("Basel III: قيمة الضمان وسياق الائتمان (استرشادية)")
                _compliance_disclosures.append("Basel III: إطار مصرفي — لا يُعد موافقة ائتمانية أو تنظيمية")
                _compliance_pdf_sections.append("ملحق Basel III: سياق الضمان والتمويل")
                _compliance_workbook_sheets.append("ورقة Basel III Collateral Context")
                _compliance_actions.append("وثّق قيمة الضمان ونسبة LTV وسياق مخاطر الائتمان للتقارير المصرفية.")
            if not _compliance_warnings:
                _compliance_status = "compliant_advisory"

        _compliance_status_label_ar_map: dict = {
            "compliant_advisory":   "متوافق استرشادياً",
            "partially_compliant":  "امتثال جزئي",
            "non_compliant":        "غير متوافق",
            "insufficient_data":    "بيانات غير كافية",
            "pending_expert_review":"بانتظار مراجعة الخبير",
        }
        _compliance_status_label_ar = _compliance_status_label_ar_map.get(_compliance_status, "استرشادي")

        _report_disclosure_guidance: list = []
        _standards_summary_for_report = ""
        if selected_standards:
            _labels = {"ivs_2025": "IVS 2025", "rics_red_book_2025": "RICS Red Book 2025", "uspap": "USPAP", "ifrs_13": "IFRS 13", "fra_egypt": "FRA مصر", "gcc_standards": "GCC", "custom_local_standard": "معيار محلي خاص", "basel_iii": "Basel III (إطار مصرفي)"}
            _standards_summary_for_report = "معايير مختارة: " + " + ".join(_labels.get(s, s) for s in selected_standards) + " — استرشادي"
            if "ivs_2025" in selected_standards:
                _report_disclosure_guidance.append("إفصاح IVS: نطاق العمل، الافتراضات، المنهجية (استرشادي)")
            if "rics_red_book_2025" in selected_standards:
                _report_disclosure_guidance.append("إفصاح RICS: شروط الارتباط، الاستقلالية (استرشادي)")
            if "uspap" in selected_standards:
                _report_disclosure_guidance.append("إفصاح USPAP: المستخدم المقصود، الغرض، الافتراضات، بيان التصديق (استرشادي)")
            if "ifrs_13" in selected_standards:
                _report_disclosure_guidance.append("إفصاح IFRS 13: مستوى التسلسل الهرمي وعدم اليقين (استرشادي)")
            if "basel_iii" in selected_standards:
                _report_disclosure_guidance.append("Basel III (إطار مصرفي): قيمة الضمان، LTV، مخاطر الائتمان — استرشادي، لا موافقة ائتمانية")

        _uspap_context: dict = {
            "selected":          "uspap" in selected_standards,
            "use_case":          uspap_use_case or None,
            "required_disclosures": ["intended_user", "intended_use", "scope_of_work", "basis_of_value_or_value_definition", "assumptions_and_limiting_conditions", "data_sources", "methodology_rationale", "certification_or_expert_review_note"],
            "missing_requirements": ["USPAP: نطاق العمل، المستخدم المقصود، الغرض المقصود، بيان التصديق"] if "uspap" in selected_standards else [],
            "advisory_only":     True,
            "final_compliance_claim": False,
        }

        _basel_iii_context: dict = {
            "selected":              "basel_iii" in selected_standards,
            "framework_type":        "banking_risk_framework",
            "not_pure_valuation_standard": True,
            "use_case":              basel_iii_use_case or None,
            "collateral_value":      basel_iii_collateral_value,
            "ltv_ratio":             basel_iii_ltv_ratio,
            "credit_risk_rating":    basel_iii_credit_risk_rating or None,
            "required_inputs":       ["collateral_value", "ltv_ratio", "credit_risk_context", "collateral_quality_notes", "banking_lending_purpose"],
            "missing_requirements":  ["Basel III: قيمة الضمان، نسبة LTV، سياق مخاطر الائتمان"] if "basel_iii" in selected_standards else [],
            "advisory_only":         True,
            "credit_approval":       False,
            "regulatory_capital_calculation": False,
            "final_compliance_claim": False,
        }

        _standards_legacy_alias_mapping: dict = {
            "uspap":     ["USPAP", "uniform_standards_professional_appraisal_practice"],
            "basel_iii": ["basel", "basel3", "Basel III"],
            "deleted_standard_options": [],
            "preservation_pass": True,
        }

        _applied_standards_context: dict = {
            "selected_standards":           selected_standards,
            "available_standards":          [s["key"] for s in _standards_registry],
            "standards_by_category": {
                "professional_valuation_standard": [s["key"] for s in _standards_registry if s.get("category") == "professional_valuation_standard"],
                "financial_reporting_standard":    [s["key"] for s in _standards_registry if s.get("category") == "financial_reporting_standard"],
                "local_regulatory_reference":      [s["key"] for s in _standards_registry if s.get("category") == "local_regulatory_reference"],
                "custom_local_reference":          [s["key"] for s in _standards_registry if s.get("category") == "custom_local_reference"],
                "risk_banking_collateral_framework":[s["key"] for s in _standards_registry if s.get("category") == "risk_banking_collateral_framework"],
            },
            "uspap_context":                _uspap_context,
            "basel_iii_context":            _basel_iii_context,
            "jurisdiction_country":         jurisdiction_country,
            "local_reference":              local_reference,
            "custom_local_standard_name":   custom_local_standard_name,
            "standard_effective_date":      standard_effective_date,
            "ivs_reference":                ivs_reference,
            "rics_reference":               rics_reference,
            "ifrs_fair_value_level":        ifrs_fair_value_level,
            "compliance_disclosure_level":  compliance_disclosure_level,
            "compliance_target":            compliance_target,
            "compliance_status":            _compliance_status,
            "compliance_status_label_ar":   _compliance_status_label_ar,
            "missing_requirements":         _compliance_missing,
            "required_disclosures":         _compliance_disclosures,
            "standards_warnings":           _compliance_warnings,
            "recommended_actions":          _compliance_actions,
            "report_disclosure_guidance":   _report_disclosure_guidance,
            "required_pdf_sections":        _compliance_pdf_sections,
            "required_workbook_sheets":     _compliance_workbook_sheets,
            "compliance_summary": {
                "status":               _compliance_status,
                "final_compliance_claim": False,
                "requires_expert_review": True,
                "missing_requirements": _compliance_missing,
            },
            "registry_version":             "pvasr-v2",
            "advisory_only":                True,
            "expert_review_required":       True,
            "certification_gate_controls_final_status": True,
            "standards_summary_for_report": _standards_summary_for_report,
            "standards_limitations_for_report": "الامتثال في هذه المرحلة استرشادي — يتطلب مراجعة الخبير وبوابات الاعتماد.",
            "advisory_compliance_warning":  "لا تُعدّ هذه النتائج امتثالاً رسمياً أو اعتماداً نهائياً دون استيفاء بوابات التوقيع والمراجعة.",
            "legacy_aliases": {
                "standard_options":  _standards_registry_legacy_keys,
                "disclosure_levels": ["full_disclosure", "restricted_disclosure", "internal_only", "regulatory_minimum", "confidential"],
                "ivs_refs":          ["ivs_104", "ivs_105", "ivs_400", "ivs_410", "ivs_500", "ivs_600"],
                "local_refs":        ["eg_valuation_law", "eg_cma_circular", "eg_cbe_regulation", "sa_zatca_circular", "uae_rera"],
                "standards_legacy_alias_mapping": _standards_legacy_alias_mapping,
            },
            "preservation_pass": True,
        }

        _standards_registry_context: dict = {
            "registry_version": "pvasr-v1",
            "standards": _standards_registry,
            "local_standards": _local_standards_registry,
            "ivs_references": _ivs_references_registry,
            "rics_references": _rics_references_registry,
            "ifrs_levels": _ifrs_levels_registry,
            "disclosure_levels": _disclosure_levels_registry,
            "preservation_pass": True,
        }

        _standards_mapping_matrix_context: dict = {
            "registry_version": "pvasr-v1",
            "mapping_matrix": _standards_mapping_matrix,
            "compliance_rules": _standards_compliance_rules,
            "note": "Advisory mapping — not binding without expert review",
        }

        _standards_compliance_rules_context: dict = {
            "registry_version":      "pvasr-v1",
            "compliance_rules":      _standards_compliance_rules,
            "evaluated_status":      _compliance_status,
            "evaluated_status_ar":   _compliance_status_label_ar,
            "warnings_count":        len(_compliance_warnings),
            "missing_count":         len(_compliance_missing),
            "advisory_only":         True,
        }

        # ── PVRT: Report Type Registry + Context ─────────────────────────────
        _report_type_registry: list = [
            {
                "key": "summary_report",
                "label_ar": "تقرير موجز",
                "label_en": "Summary Report",
                "description_ar": "تقرير مختصر للاستخدام السريع أو العرض الأولي.",
                "legacy_aliases": ["traditional_report", "تقرير تقليدي"],
                "pdf_sections": ["cover_page","executive_summary","asset_summary","purpose_basis_summary","method_summary","value_conclusion","key_assumptions","advisory_warning_or_signature_block"],
                "workbook_sheets": ["cover_inputs","value_summary","method_summary","source_evidence_summary"],
                "approximate_page_range": "3-8",
                "minimum_methods_required": 1,
                "minimum_comparables_required": 0,
                "hbu_requirement": "not_required",
                "sensitivity_requirement": "not_required",
                "swot_requirement": "not_required",
                "uncertainty_requirement": "not_required",
                "esg_requirement": "not_required",
                "peer_review_requirement": "not_required",
                "signature_requirement": "not_required",
                "recommended_for": {"purposes": ["internal_advisory","quick_review"], "asset_types": ["residential_apartment","residential_villa"]},
                "advisory_only_until_certified": True,
            },
            {
                "key": "full_report",
                "label_ar": "تقرير كامل",
                "label_en": "Full Report",
                "description_ar": "تقرير تفصيلي يغطي جميع طرق التقييم والملاحق الأساسية.",
                "legacy_aliases": ["detailed_report", "تقرير تفصيلي"],
                "pdf_sections": ["cover_page","executive_summary","scope_of_work","property_details","market_overview","sales_comparison","income_approach","cost_approach","dcf_if_applicable","reconciliation","assumptions_and_limiting_conditions","comparables_appendix","income_tables_appendix","cost_tables_appendix","evidence_summary","advisory_warning_or_signature_block"],
                "workbook_sheets": ["cover_inputs","value_summary","method_summary","source_evidence_summary","property_details","comparables_sales","comparables_rent","adjustment_grid","income_approach","cost_approach","dcf","reconciliation","assumptions","evidence_registry"],
                "approximate_page_range": "15-25",
                "minimum_methods_required": 2,
                "minimum_comparables_required": 3,
                "hbu_requirement": "optional",
                "sensitivity_requirement": "optional",
                "swot_requirement": "not_required",
                "uncertainty_requirement": "optional",
                "esg_requirement": "not_required",
                "peer_review_requirement": "optional",
                "signature_requirement": "optional",
                "recommended_for": {"purposes": ["financing_mortgage","court_legal","market_value","investment_decision"], "asset_types": []},
                "advisory_only_until_certified": True,
            },
            {
                "key": "enhanced_professional_report",
                "label_ar": "تقرير شامل",
                "label_en": "Enhanced Professional Report",
                "description_ar": "تقرير كامل موسع يتضمن تحليلات متقدمة: HBU، الحساسية، SWOT، ESG، الحوكمة، سجل التدقيق.",
                "legacy_aliases": ["professional_report", "تقرير احترافي"],
                "pdf_sections": ["cover_page","executive_summary","scope_of_work","property_details","market_overview","sales_comparison","income_approach","cost_approach","dcf_if_applicable","reconciliation","assumptions_and_limiting_conditions","comparables_appendix","income_tables_appendix","cost_tables_appendix","evidence_summary","hbu_analysis","sensitivity_analysis","swot_analysis","uncertainty_range","esg_climate_review","legal_due_diligence_summary","risk_matrix","standards_compliance_summary","peer_review_summary","signature_license_metadata","certification_gate_snapshot","output_hash_version","audit_trail"],
                "workbook_sheets": ["cover_inputs","value_summary","method_summary","source_evidence_summary","property_details","comparables_sales","comparables_rent","adjustment_grid","income_approach","cost_approach","dcf","reconciliation","assumptions","evidence_registry","hbu","sensitivity","swot","uncertainty_range","esg","legal_review","risk_matrix","standards_compliance","peer_review","signature_gate","output_registry","audit_trail"],
                "approximate_page_range": "30-60+",
                "minimum_methods_required": 3,
                "minimum_comparables_required": 5,
                "hbu_requirement": "required",
                "sensitivity_requirement": "required",
                "swot_requirement": "required",
                "uncertainty_requirement": "required",
                "esg_requirement": "required",
                "peer_review_requirement": "required",
                "signature_requirement": "required",
                "recommended_for": {"purposes": ["financial_reporting","court_legal","certified_report_ready"], "asset_types": ["hotel","resort","cinema","hospital","school","factory","data_center","petrol_station"]},
                "advisory_only_until_certified": True,
            },
        ]

        _report_type_difference_matrix: list = [
            {"report_type": "summary_report",              "label_ar": "تقرير موجز",   "approximate_page_range": "3-8",   "minimum_methods_required": 1, "minimum_comparables_required": 0, "sales_comparison": True, "income_approach": False, "cost_approach": False, "dcf": False, "hbu": False, "sensitivity": False, "swot": False, "uncertainty_range": False, "esg": False, "legal_review": False, "standards_compliance": False, "peer_review": False, "signature_metadata": False, "output_registry": False, "audit_trail": False, "pdf_sections_count": 8,  "workbook_sheets_count": 4},
            {"report_type": "full_report",                 "label_ar": "تقرير كامل",   "approximate_page_range": "15-25", "minimum_methods_required": 2, "minimum_comparables_required": 3, "sales_comparison": True, "income_approach": True, "cost_approach": True, "dcf": True, "hbu": "optional", "sensitivity": "optional", "swot": False, "uncertainty_range": "optional", "esg": False, "legal_review": False, "standards_compliance": False, "peer_review": "optional", "signature_metadata": "optional", "output_registry": False, "audit_trail": False, "pdf_sections_count": 16, "workbook_sheets_count": 14},
            {"report_type": "enhanced_professional_report","label_ar": "تقرير شامل",   "approximate_page_range": "30-60+","minimum_methods_required": 3, "minimum_comparables_required": 5, "sales_comparison": True, "income_approach": True, "cost_approach": True, "dcf": True, "hbu": True, "sensitivity": True, "swot": True, "uncertainty_range": True, "esg": True, "legal_review": True, "standards_compliance": True, "peer_review": True, "signature_metadata": True, "output_registry": True, "audit_trail": True, "pdf_sections_count": 28, "workbook_sheets_count": 26},
        ]

        _pdf_output_config: dict = {
            "summary_report":               [r["pdf_sections"]  for r in _report_type_registry if r["key"] == "summary_report"][0],
            "full_report":                  [r["pdf_sections"]  for r in _report_type_registry if r["key"] == "full_report"][0],
            "enhanced_professional_report": [r["pdf_sections"]  for r in _report_type_registry if r["key"] == "enhanced_professional_report"][0],
        }

        _workbook_sheet_config: dict = {
            "summary_report":               [r["workbook_sheets"] for r in _report_type_registry if r["key"] == "summary_report"][0],
            "full_report":                  [r["workbook_sheets"] for r in _report_type_registry if r["key"] == "full_report"][0],
            "enhanced_professional_report": [r["workbook_sheets"] for r in _report_type_registry if r["key"] == "enhanced_professional_report"][0],
            "preserved_legacy_sheets":      list({
                "ملخص المسودة","بيانات الطلب","بيانات العقار","المستندات والمصادر","تحليل الطرق",
                "التوفيق المبدئي","بوابات الاعتماد","سجل المخرجات","مقدمة ونطاق التقييم","الافتراضات والقيود",
                "مصادر الأسعار","التوصية النهائية","بيان الامتثال","الإفصاحات المهنية","المقارنات",
                "طريقة مقارنة البيوع","طريقة الدخل","التدفقات النقدية DCF","طريقة التكلفة","قيمة الأرض",
                "تفصيل الإهلاك","القيمة الإيجارية","مقارنات إيجارية","توفيق القيمة الإيجارية",
                "تحليل مخاطر DCF","سيناريوهات What-If","شراء أم إيجار","نطاق الثقة وعدم اليقين",
                "دعم التعديلات","تحليل الاستدامة ESG","تقييم الأثر البيئي","مؤشرات تكلفة البناء",
                "مصفوفة المخاطر","اختبار اتساق الطرق","حوكمة مصادر البيانات","خارطة طريق الاعتماد",
                "قائمة فحص الاعتماد","HBU","الفحص القانوني","ESG","SWOT","مراجعة الخبير","ملاحظات داخلية",
            }),
        }

        # ── Inline recommendation engine ──────────────────────────────────────
        _specialized_assets_pvrt = {"hotel","resort","cinema","heritage","hospital","school","factory","data_center","petrol_station","warehouse_logistics","religious","sports_venue","museum","prison","airport"}
        _effective_asset_for_rec = asset_type or effective_property_type or ""
        _rec_report_type = "enhanced_professional_report"
        _rec_reasons: list = []
        _rec_warnings: list = []

        if assignment_purpose == "internal_advisory":
            _rec_report_type = "summary_report"
            _rec_reasons.append("الغرض: استشارة داخلية — تقرير موجز كافٍ")
        elif assignment_purpose == "financing_mortgage":
            _rec_report_type = "full_report"
            _rec_reasons.append("الغرض: تمويل/رهن — يُوصى بتقرير كامل")
        elif assignment_purpose in ("court_legal", "court_dispute", "regulatory_compliance"):
            _rec_report_type = "full_report"
            _rec_reasons.append("الغرض القضائي/الرقابي: الحد الأدنى — تقرير كامل")
        elif assignment_purpose == "financial_reporting" or basis_of_value == "fair_value":
            _rec_report_type = "enhanced_professional_report"
            _rec_reasons.append("قياس القيمة العادلة / التقارير المالية: يُوصى بتقرير شامل")
        elif any(a in _effective_asset_for_rec for a in _specialized_assets_pvrt):
            _rec_report_type = "enhanced_professional_report"
            _rec_reasons.append("الأصل متخصص: يُوصى بتقرير شامل")
        elif len(selected_standards) >= 2 or compliance_target == "certified_report_ready":
            _rec_report_type = "enhanced_professional_report"
            _rec_reasons.append("معايير متعددة أو هدف اعتماد: يُوصى بتقرير شامل")
        else:
            _rec_report_type = "enhanced_professional_report"
            _rec_reasons.append("الافتراضي للتقارير المهنية: تقرير شامل")

        # Override warning if user selected lower level
        _rt_level_pvrt = {"summary_report": 0, "full_report": 1, "enhanced_professional_report": 2}
        _rec_level = _rt_level_pvrt.get(_rec_report_type, 2)
        _user_level = _rt_level_pvrt.get(_normalized_report_type, 2)
        if _user_level < _rec_level:
            _rec_warnings.append(
                f"التقرير المختار ({_normalized_report_type}) أقل عمقاً من التوصية ({_rec_report_type})."
            )

        # ── report_type_context ───────────────────────────────────────────────
        _rt_entry = next((r for r in _report_type_registry if r["key"] == _normalized_report_type), _report_type_registry[2])
        _rt_label_map = {"summary_report": "تقرير موجز", "full_report": "تقرير كامل", "enhanced_professional_report": "تقرير شامل"}
        _certification_ready: bool = bool(rec.get("certification_ready", False))

        _report_type_context: dict = {
            "report_type":              _normalized_report_type,
            "report_type_label_ar":     _rt_label_map.get(_normalized_report_type, _normalized_report_type),
            "legacy_report_type_input": _legacy_report_type_input,
            "normalized_report_type":   _normalized_report_type,
            "legacy_alias_used":        _legacy_alias_used,
            "description_ar":           _rt_entry.get("description_ar", ""),
            "pdf_sections":             _rt_entry.get("pdf_sections", []),
            "workbook_sheets":          _rt_entry.get("workbook_sheets", []),
            "pdf_output_depth":         _rt_entry.get("approximate_page_range", ""),
            "workbook_output_depth":    f"{len(_rt_entry.get('workbook_sheets', []))} ورقة",
            "minimum_methods_required": _rt_entry.get("minimum_methods_required", 1),
            "minimum_comparables_required": _rt_entry.get("minimum_comparables_required", 0),
            "advanced_analysis_requirements": {
                "hbu":            _rt_entry.get("hbu_requirement", "not_required"),
                "sensitivity":    _rt_entry.get("sensitivity_requirement", "not_required"),
                "swot":           _rt_entry.get("swot_requirement", "not_required"),
                "uncertainty_range": _rt_entry.get("uncertainty_requirement", "not_required"),
                "esg":            _rt_entry.get("esg_requirement", "not_required"),
                "legal_review":   "required" if _normalized_report_type == "enhanced_professional_report" else "not_required",
                "peer_review":    _rt_entry.get("peer_review_requirement", "not_required"),
                "signature":      _rt_entry.get("signature_requirement", "not_required"),
            },
            "recommended_report_type":  _rec_report_type,
            "recommendation_reasons":   _rec_reasons,
            "warnings":                 _rec_warnings,
            "output_permissions": {
                "preliminary_pdf_allowed":   True,
                "expert_draft_pdf_allowed":  True,
                "expert_workbook_allowed":   True,
                "certified_pdf_allowed":     _certification_ready,
                "final_workbook_allowed":    _certification_ready,
            },
            "legacy_aliases": {
                "traditional_report":  "summary_report",
                "detailed_report":     "full_report",
                "professional_report": "enhanced_professional_report",
            },
            "advisory_only":                         True,
            "certification_gate_controls_final_status": True,
            "registry_version":                      "pvrt-v1",
            "preservation_pass":                     True,
        }

        _report_type_registry_context: dict = {
            "registry_version":         "pvrt-v1",
            "report_types":             _report_type_registry,
            "legacy_aliases":           {"traditional_report": "summary_report", "detailed_report": "full_report", "professional_report": "enhanced_professional_report"},
            "preservation_pass":        True,
        }

        _report_type_difference_matrix_context: dict = {
            "registry_version":     "pvrt-v1",
            "difference_matrix":    _report_type_difference_matrix,
            "note":                 "مصفوفة الفروق — استرشادية لمساعدة الخبير في اختيار نوع التقرير",
        }

        _report_output_configuration_context: dict = {
            "registry_version":                "pvrt-v1",
            "pdf_output_configuration":        _pdf_output_config,
            "workbook_sheet_configuration":    _workbook_sheet_config,
            "note":                            "تكوين مرجعي — المخرجات الفعلية تعتمد على البيانات المتاحة والاعتماد",
            "advisory_only":                   True,
            "certified_pdf_requires_gate":     True,
            "final_workbook_requires_gate":    True,
        }

        # ── Three-Cards Taxonomy Summary (Part F) ────────────────────────────
        _taxonomy_cards_summary: dict = {
            "card_1_asset_definition": {
                "asset_family":        asset_family,
                "asset_type":          asset_type or effective_property_type,
                "asset_subtype":       asset_subtype,
                "asset_condition_path": asset_condition_path,
            },
            "card_2_purpose_routes": {
                "assignment_purpose":          assignment_purpose,
                "purpose_logic_path":          purpose_logic_path,
                "purpose_route":               purpose_route,
                "purpose_subroute":            purpose_subroute,
                "professional_context_path":   professional_context_path,
                "professional_purpose_path":   professional_purpose_path,
                "intended_user_category":      intended_user_category,
                "intended_use":                intended_use,
            },
            "card_3_basis_of_value": {
                "basis_of_value":   basis_of_value,
                "value_premise":    value_premise,
                "value_output_type": value_output_type,
            },
            "warnings": _purpose_route_warnings,
        }

        # ── Engine Governance Audit Context (Part D — moved out of basis_of_value section) ──
        _engine_governance_ctx: dict = {
            "human_approval_required":              True,
            "ifrs_preliminary_level":               "Level 2",
            "draft_status":                         "draft_pending_human_review",
            "active_purpose":                       assignment_purpose,
            "data_readiness":                       "partial_data",
            "active_asset_type":                    asset_type or effective_property_type or "",
            "active_asset_family":                  asset_family or "",
            "report_status":                        "draft_not_certified",
            "active_route":                         purpose_route or "",
            "final_report_without_approval_allowed": False,
            "processing_pipeline_steps": [
                {"step": 1, "key": "interface_fields",   "label_ar": "حقول الواجهة",     "status": "active"},
                {"step": 2, "key": "database_mapping",   "label_ar": "قاعدة البيانات",   "status": "active"},
                {"step": 3, "key": "engine_inputs",      "label_ar": "مدخلات المحرك",    "status": "active"},
                {"step": 4, "key": "market_comparables", "label_ar": "مقارنات السوق",    "status": "pending_rag"},
                {"step": 5, "key": "auto_enrichment",    "label_ar": "الإثراء الآلي",    "status": "pending_rag"},
                {"step": 6, "key": "validation_rules",   "label_ar": "قواعد التحقق",     "status": "active"},
                {"step": 7, "key": "human_approval",     "label_ar": "الموافقة البشرية", "status": "required"},
                {"step": 8, "key": "report_disclosure",  "label_ar": "إفصاح التقرير",    "status": "active"},
                {"step": 9, "key": "output_contract",    "label_ar": "عقد المخرجات",     "status": "active"},
            ],
        }

        # ── Main Page Sections Context (Part E — 6-section restructure) ──────
        _main_page_sections_ctx: dict = {
            "section_count": 6,
            "page_version": "six_sections_v1",
            "sections": [
                {"id": "pro-val-section-basic-valuation-data",        "num": 1, "label_ar": "البيانات الأساسية للتقييم",     "status": "visible"},
                {"id": "pro-val-section-asset-type-selection",        "num": 2, "label_ar": "اختيار نوع الأصل العقاري",      "status": "visible"},
                {"id": "pro-val-section-valuation-purpose",           "num": 3, "label_ar": "الغرض من التقييم وأساس القيمة", "status": "visible"},
                {"id": "pro-val-section-applied-valuation-standards", "num": 4, "label_ar": "معايير التقييم المطبقة",        "status": "visible"},
                {"id": "pro-val-section-report-type",                 "num": 5, "label_ar": "نوع التقرير",                   "status": "visible"},
                {"id": "pro-val-section-chat-box",                    "num": 6, "label_ar": "صندوق الشات والمخرجات",         "status": "visible"},
            ],
            "governance_panel_visible": True,
            "advanced_controls_panel_visible": True,
        }

        # ── Advanced Controls Context (Part E — classification panel) ────────
        _advanced_controls_ctx: dict = {
            "active_controls": [
                {"id": "digital-verification", "label_ar": "المحقق الرقمي",         "location": "chat_box_section", "activation": "active"},
                {"id": "reference-library",    "label_ar": "المكتبة المرجعية",       "location": "chat_box_section", "activation": "active"},
                {"id": "output-registry",      "label_ar": "سجل التقارير المحفوظة",  "location": "output_panel",     "activation": "active"},
                {"id": "weighted-engine",      "label_ar": "محرك الترجيح المبدئي",   "location": "section_3b",       "activation": "active_non_certified"},
                {"id": "geo-risk",             "label_ar": "المخاطر الجيوتقنية",     "location": "chat_box_section", "activation": "conditional"},
            ],
            "inactive_controls": [
                {"id": "super-intelligence", "label_ar": "الاستخبارات الفائقة",    "reason": "pending_rag_qdrant",           "activation": "future_stub"},
                {"id": "asset-portfolio",    "label_ar": "محفظة الأصول",           "reason": "pending_asset_manager_backend","activation": "future_stub"},
                {"id": "migration-radar",    "label_ar": "رادار الهجرة العقارية",  "reason": "pending_demographics_api",     "activation": "future_stub"},
                {"id": "admin-dashboard",    "label_ar": "لوحة التحكم الإدارية",  "reason": "admin_only",                   "activation": "admin_only"},
            ],
            "activation_roadmap": [
                {"phase": 1, "status": "active",  "label": "6 Sections + Advanced Panel + Engine Governance"},
                {"phase": 2, "status": "pending", "label": "RAG + Qdrant → Super Intelligence Suite"},
                {"phase": 3, "status": "pending", "label": "Asset Manager Backend → Portfolio"},
                {"phase": 4, "status": "pending", "label": "Demographics API → Migration Radar"},
                {"phase": 5, "status": "pending", "label": "Admin Gate → Admin Dashboard"},
            ],
            "report_reflection_matrix": {
                "traditional_report":  {"pages": "3-5",   "methods": 1, "certification": False},
                "detailed_report":     {"pages": "15-20", "methods": 3, "certification": False},
                "professional_report": {"pages": "30+",   "methods": 3, "certification": True, "standards": "IVS/RICS"},
                "simulated_report":    {"pages": None,    "methods": 0, "certification": False, "advisory_only": True},
            },
        }

        # ── Asset Type Selection Context (Parts C+D+E cleanup) ──────────────
        _ASSET_FAMILY_LABELS_AR: dict = {
            # Common families (hidden from visible UI, preserved as backend aliases)
            "residential_housing":        "الوحدات السكنية والإسكان",
            "land_plots":                 "الأراضي والقطع الأرضية",
            "commercial_retail":          "التجاري والتجزئة",
            "office_administrative":      "الإداري والمكتبي",
            "industrial_logistics":       "الصناعي واللوجستي",
            "hospitality_leisure":        "الضيافة والترفيه",
            "healthcare_education":       "الطبي والتعليمي",
            # Uncommon/specialized families (visible in UI)
            "special_purpose":            "الأغراض الخاصة",
            "agri_environmental":         "الزراعي والبيئي",
            "infrastructure":             "البنية التحتية",
            "mixed_use":                  "متعدد الاستخدام",
            # New uncommon families (Part D)
            "heritage_assets":            "الأصول التراثية",
            "cultural_heritage_assets":   "الأصول الثقافية والتراثية",
            "special_purpose_assets":     "الأصول المتخصصة",
            "infrastructure_assets":      "أصول البنية التحتية",
            "healthcare_assets":          "الأصول الصحية",
            "education_assets":           "الأصول التعليمية",
            "religious_assets":           "الأصول الدينية",
            "sports_recreation_assets":   "الأصول الرياضية والترفيهية",
            "hospitality_special_assets": "أصول ضيافة متخصصة",
            "energy_utility_assets":      "أصول الطاقة والمرافق",
            "transport_assets":           "أصول النقل والمواقف",
            "marine_assets":              "الأصول البحرية",
            "agricultural_special_assets":"أصول زراعية متخصصة",
            "industrial_special_assets":  "أصول صناعية متخصصة",
            "tourism_special_assets":     "أصول سياحية متخصصة",
            "entertainment_assets":       "أصول الترفيه",
            # Legacy families (preserved, not deleted)
            "hospitality_entertainment":  "ضيافة وترفيه (موروث)",
            "sports_event_venues":        "رياضة وفعاليات",
            "advanced_industrial_logistics": "صناعة ولوجستيات متقدمة",
            "tech_energy_infrastructure": "تقنية وطاقة وبنية تحتية",
            "specialized_medical_science":"طبي وعلمي متخصص",
            "agri_environmental_assets":  "زراعي وبيئي (موروث)",
            "underground_special_assets": "تحت الأرض وخاص",
            "cemetery_memorial_assets":   "مقابر وتذكارية",
            "heritage_cultural_assets":   "تراث وثقافة",
        }
        _DUPLICATE_OPTIONS_REMOVED: list = [
            {"option": "hotel", "removed_from": "asset_subtype when asset_type=hotel",
             "reason": "duplicate — same value as parent asset_type",
             "canonical_subtype": "business_hotel / boutique_hotel / resort_hotel (choose specific)",
             "legacy_alias_preserved": True},
            {"option": "vacant_land", "removed_from": "asset_subtype when asset_type=أرض فضاء",
             "reason": "duplicate — same value as parent asset_type",
             "canonical_subtype": "residential_development_land / commercial_development_land / etc.",
             "legacy_alias_preserved": True},
            {"option": "residential_unit", "removed_from": "asset_subtype when asset_type=شقة سكنية",
             "reason": "duplicate — same value as parent asset_type",
             "canonical_subtype": "studio / one_bedroom / two_bedroom / penthouse / duplex / etc.",
             "legacy_alias_preserved": True},
        ]
        _UNCOMMON_FAMILY_KEYS: set = {
            "heritage_assets", "cultural_heritage_assets", "special_purpose_assets",
            "infrastructure_assets", "healthcare_assets", "education_assets", "religious_assets",
            "sports_recreation_assets", "hospitality_special_assets", "energy_utility_assets",
            "transport_assets", "marine_assets", "agricultural_special_assets",
            "industrial_special_assets", "tourism_special_assets", "entertainment_assets",
            "special_purpose", "agri_environmental", "infrastructure", "mixed_use",
            "hospitality_entertainment", "sports_event_venues", "advanced_industrial_logistics",
            "tech_energy_infrastructure", "specialized_medical_science", "agri_environmental_assets",
            "underground_special_assets", "cemetery_memorial_assets", "heritage_cultural_assets",
        }
        _COMMON_ASSET_TYPE_KEYS: list = [
            "شقة سكنية", "residential_apartment", "residential_villa", "عمارة سكنية",
            "أرض فضاء", "vacant_land", "urban_land", "أرض زراعية", "agricultural_land",
            "تجاري", "مبنى قائم", "administrative_office", "retail_shop", "shopping_mall",
            "mixed_use_asset", "فندق", "hotel", "resort", "مصنع", "industrial_factory",
            "warehouse", "محل تجاري", "retail_shop_detailed", "مستشفى", "مدرسة",
            "مناجم", "water_well", "hotel_resort_detailed", "serviced_apartments",
            "floating_hotel", "airport", "seaport", "marina", "data_center", "cold_storage",
            "prefabricated_factory", "industrial_logistics_facility_detailed",
            "healthcare_facility", "wellness_resort", "educational_asset",
            "heritage_property_detailed", "architectural_cultural_heritage_detailed",
            "timberland", "zoo_safari", "littoral_rights", "riparian_rights",
            "waterway_easement", "أصول معنوية", "ملكيات جزئية",
            "استثمارات تحت الإنشاء", "historical", "heritage",
        ]
        _PROF_FAMILY_SUBTYPES_BACKEND: dict = {
            "entertainment_assets":       ["cinema","theater","event_hall","amusement_center","cultural_center"],
            "heritage_assets":            ["distinguished_architectural_heritage","listed_heritage_building","adaptive_reuse_heritage_property","protected_historic_property","heritage_commercial_property"],
            "cultural_heritage_assets":   ["cultural_landmark","archaeological_site","heritage_museum","adaptive_reuse_heritage"],
            "special_purpose_assets":     ["petrol_station","cinema","theater","sports_club","cemetery","religious_facility","data_center_special","cold_storage_special"],
            "infrastructure_assets":      ["parking_structure","utility_station","transport_terminal","logistics_hub_special"],
            "healthcare_assets":          ["general_hospital","clinic_complex","medical_center","specialized_medical_facility"],
            "education_assets":           ["school_campus","university_campus","training_center","nursery_education_property"],
            "religious_assets":           ["mosque","religious_facility","community_worship_center"],
            "sports_recreation_assets":   ["stadium","indoor_arena","golf_course","sports_club","padel_tennis_courts","padel_tennis_court"],
            "hospitality_special_assets": ["wellness_resort","floating_hotel","boutique_hotel","heritage_hotel"],
            "energy_utility_assets":      ["solar_farm","utility_plant","telecom_tower","wind_farm"],
            "transport_assets":           ["parking_structure","transport_terminal","airport","seaport"],
            "marine_assets":              ["marina","floating_hotel","seaport"],
            "agricultural_special_assets":["agtech_hydroponic","greenhouse","smart_farm","fish_farm"],
            "industrial_special_assets":  ["industrial","prefabricated_factory","self_storage","container_yard"],
            "tourism_special_assets":     ["wellness_resort","zoo_safari","theme_park","heritage_tourism_property"],
            "special_purpose":            ["petrol_station","cinema","theater","sports_club","cemetery","religious_facility"],
            "agri_environmental":         ["agtech_hydroponic","greenhouse","smart_farm","timberland"],
            "infrastructure":             ["parking_structure","utility_station","road_asset","bridge"],
            "mixed_use":                  ["mixed_use_development","transit_oriented_development"],
            "hospitality_entertainment":  ["hotel","cinema","theater","opera_house","theme_park","indoor_ski_slope","casino"],
            "sports_event_venues":        ["stadium","indoor_arena","padel_tennis_courts","padel_tennis_court","squash_courts","racecourse","motorsport_circuit","golf_course"],
            "advanced_industrial_logistics": ["industrial","prefabricated_factory","self_storage","container_yard","parking_structure"],
            "tech_energy_infrastructure": ["telecom_tower","solar_farm"],
            "specialized_medical_science":["hospital","school","life_sciences_lab","bio_bank"],
            "agri_environmental_assets":  ["agtech_hydroponic","greenhouse","smart_farm"],
            "underground_special_assets": ["repurposed_cave","underground_bunker"],
            "cemetery_memorial_assets":   ["cemetery","memorial_park"],
            "heritage_cultural_assets":   ["heritage_property","architectural_heritage","cultural_landmark","adaptive_reuse_heritage"],
        }
        _is_uncommon_family = asset_family in _UNCOMMON_FAMILY_KEYS
        _selected_asset_source = (
            "uncommon_subtype" if (asset_subtype or property_subtype) and _is_uncommon_family
            else "uncommon_family" if _is_uncommon_family
            else "common_asset_type"
        )
        _asset_type_selection_ctx: dict = {
            "asset_type":                   asset_type or effective_property_type,
            "asset_type_label_ar":          _ASSET_FAMILY_LABELS_AR.get(asset_family, ""),
            "asset_family":                 asset_family,
            "asset_family_label_ar":        _ASSET_FAMILY_LABELS_AR.get(asset_family, ""),
            "uncommon_asset_family":        asset_family if _is_uncommon_family else "",
            "uncommon_asset_family_label_ar": _ASSET_FAMILY_LABELS_AR.get(asset_family, "") if _is_uncommon_family else "",
            "uncommon_asset_subtype":       (asset_subtype or property_subtype) if _is_uncommon_family else "",
            "uncommon_asset_subtype_label_ar": (asset_subtype or property_subtype) if _is_uncommon_family else "",
            "selected_asset_source":        _selected_asset_source,
            "asset_condition_path":         asset_condition_path,
            "asset_condition_path_label_ar": {
                "operating_existing":        "تشغيل قائم",
                "new_construction":          "مبنى جديد (تحت الإنشاء)",
                "as_is":                     "الحالة الراهنة",
                "as_repaired":              "بعد الإصلاح",
                "as_completed":             "عند اكتمال المشروع",
                "as_stabilized":            "بعد الاستقرار التشغيلي",
                "under_construction":       "قيد الإنشاء",
                "development_ready":        "جاهز للتطوير",
                "brownfield_redevelopment": "إعادة تطوير أرض صناعية",
                "heritage_listed":          "مدرج في قوائم التراث",
                "partially_let":            "مؤجر جزئياً",
                "investment_let":           "مؤجر استثمارياً",
                "shell_and_core":           "هيكل خام",
                "operating_existing_hotel": "فندق تشغيل قائم",
                "vacant_hotel":             "فندق شاغر",
                "hotel_under_renovation":   "فندق تحت التجديد",
                "raw_undeveloped_land":     "أرض خام غير مطورة",
                "serviced_land":            "أرض مخدومة",
                "land_under_development":   "أرض قيد التطوير",
            }.get(asset_condition_path, asset_condition_path),
            "asset_subtype":                asset_subtype or property_subtype,
            "asset_subtype_label_ar":       asset_subtype or property_subtype,
            "available_common_asset_types":   _COMMON_ASSET_TYPE_KEYS,
            "available_uncommon_asset_families": [k for k in _ASSET_FAMILY_LABELS_AR if k in _UNCOMMON_FAMILY_KEYS],
            "available_uncommon_asset_subtypes": _PROF_FAMILY_SUBTYPES_BACKEND.get(asset_family, []),
            "available_uncommon_asset_subtypes_by_family": _PROF_FAMILY_SUBTYPES_BACKEND,
            "available_asset_families": list(_ASSET_FAMILY_LABELS_AR.keys()),
            "available_asset_types": _COMMON_ASSET_TYPE_KEYS,
            "available_asset_subtypes_for_type": _asset_req.get("asset_type_resolved", ""),
            "duplicate_options_removed_from_visible_ui": _DUPLICATE_OPTIONS_REMOVED + [
                {"option": "residential_housing", "removed_from": "visible uncommon family dropdown",
                 "reason": "common asset type — covered by asset_type select", "legacy_alias_preserved": True},
                {"option": "land_plots", "removed_from": "visible uncommon family dropdown",
                 "reason": "common asset type — covered by asset_type select", "legacy_alias_preserved": True},
                {"option": "commercial_retail", "removed_from": "visible uncommon family dropdown",
                 "reason": "common asset type — covered by asset_type select", "legacy_alias_preserved": True},
                {"option": "office_administrative", "removed_from": "visible uncommon family dropdown",
                 "reason": "common asset type — covered by asset_type select", "legacy_alias_preserved": True},
                {"option": "industrial_logistics", "removed_from": "visible uncommon family dropdown",
                 "reason": "common asset type — covered by asset_type select", "legacy_alias_preserved": True},
                {"option": "hospitality_leisure", "removed_from": "visible uncommon family dropdown",
                 "reason": "common asset type — covered by asset_type select", "legacy_alias_preserved": True},
                {"option": "healthcare_education", "removed_from": "visible uncommon family dropdown",
                 "reason": "common asset type — covered by asset_type select", "legacy_alias_preserved": True},
            ],
            "duplicate_options_preserved_as_aliases": [
                "residential_housing", "land_plots", "commercial_retail", "office_administrative",
                "industrial_logistics", "hospitality_leisure", "healthcare_education",
            ],
            "legacy_aliases": [
                "hotel → business_hotel / boutique_hotel / resort_hotel (not shown as subtype when asset_type=hotel)",
                "vacant_land / أرض فضاء → residential_development_land / commercial_development_land / etc.",
                "residential_unit / شقة سكنية → studio / one_bedroom / two_bedroom / penthouse / duplex",
                "asset_family → uncommon_asset_family (alias maintained for backward compatibility)",
                "asset_subtype → uncommon_asset_subtype (alias maintained for backward compatibility)",
            ],
            "visible_ui_changes": {
                "family_label_changed_from": "عائلة الأصل",
                "family_label_changed_to":   "عائلة الأصل غير الشائعة",
                "subtype_label_changed_from": "النوع الفرعي / التصنيف التفصيلي",
                "subtype_label_changed_to":   "النوع الفرعي للأصل غير الشائع",
                "new_testid_family": "pro-val-uncommon-asset-family-select",
                "new_testid_subtype": "pro-val-uncommon-asset-subtype-select",
                "common_families_hidden_from_visible_ui": 7,
                "new_uncommon_families_added": 15,
                "family_expanded_from": 20,
                "family_expanded_to": len(_ASSET_FAMILY_LABELS_AR),
                "subtype_now_also_triggers_requirements_panel": True,
                "requirements_panel": "shown when asset_type OR uncommon_subtype selected — full requirements + legacy count",
            },
            "warnings": [],
        }

        # PVCC: Chat Command Center registries
        _pvcc_feature_toggles_registry: dict = {
            "super_intelligence": {
                "label_ar": "استخبارات فائقة",
                "state": "advisory_only",
                "description_ar": "تحليل استرشادي موسع — لا يتصل بنماذج خارجية.",
                "required_inputs": [],
                "effect_on_user_pdf": ["قد يُضاف قسم تحليل استرشادي موسع"],
                "effect_on_admin_excel": [],
                "blocked_reason_if_inactive": "",
                "external_api_required": False,
                "advisory_only": True,
            },
            "digital_inspector": {
                "label_ar": "المُحقق الرقمي",
                "state": "advisory_only",
                "description_ar": "فحص أولي للتناسق والشذوذ في بيانات التقييم.",
                "required_inputs": ["price_per_meter", "location"],
                "effect_on_user_pdf": ["قد يُضاف قسم ملاحظات جودة البيانات"],
                "effect_on_admin_excel": ["قد تُضاف ورقة Data Quality / Inconsistencies"],
                "blocked_reason_if_inactive": "",
                "external_api_required": False,
                "advisory_only": True,
            },
            "geotechnical_risk": {
                "label_ar": "المخاطر الجيوتقنية",
                "state": "future_stub",
                "description_ar": "تحليل التربة والسيول — يتطلب بيانات موقع جيوتقنية.",
                "required_inputs": ["location", "geotechnical_data"],
                "effect_on_user_pdf": ["قد يُضاف قسم المخاطر الجيوتقنية إذا توفرت البيانات"],
                "effect_on_admin_excel": ["قد تُضاف ورقة Geotechnical Risk Inputs"],
                "blocked_reason_if_inactive": "يحتاج بيانات موقع وجيوتقنية غير متوفرة حالياً.",
                "external_api_required": False,
                "advisory_only": True,
            },
            "migration_radar": {
                "label_ar": "رادار الهجرة",
                "state": "future_stub",
                "description_ar": "تحليل اتجاهات الطلب والهجرة — يتطلب بيانات سوق.",
                "required_inputs": ["location", "investment_horizon"],
                "effect_on_user_pdf": ["قد يُضاف قسم تحليل اتجاهات الطلب والهجرة"],
                "effect_on_admin_excel": ["قد تُضاف ورقة Demand & Migration Trend Inputs"],
                "blocked_reason_if_inactive": "يحتاج بيانات اتجاهات سوق غير متوفرة حالياً.",
                "external_api_required": False,
                "advisory_only": True,
            },
            "asset_portfolio": {
                "label_ar": "محفظة الأصول",
                "state": "future_stub",
                "description_ar": "تحليل ضمن محفظة أصول — يتطلب بيانات المحفظة.",
                "required_inputs": ["portfolio_data"],
                "effect_on_user_pdf": ["قد يُضاف قسم تحليل ضمن محفظة الأصول"],
                "effect_on_admin_excel": ["قد تُضاف ورقة Portfolio Context"],
                "blocked_reason_if_inactive": "يحتاج بيانات محفظة غير متوفرة حالياً.",
                "external_api_required": False,
                "advisory_only": True,
            },
            "reference_library": {
                "label_ar": "المكتبة المرجعية",
                "state": "advisory_only",
                "description_ar": "فتح المكتبة المرجعية للمقارنة المزدوجة — استرشادي.",
                "required_inputs": [],
                "effect_on_user_pdf": ["قد يُضاف قسم المراجع والمقارنات المرجعية"],
                "effect_on_admin_excel": ["قد تُضاف ورقة Reference Library Links"],
                "blocked_reason_if_inactive": "",
                "external_api_required": False,
                "advisory_only": True,
            },
            "report_review": {
                "label_ar": "مراجعة التقارير",
                "state": "advisory_only",
                "description_ar": "مراجعة التقرير وفق المعايير الدولية — استرشادي.",
                "required_inputs": [],
                "effect_on_user_pdf": ["قد يُضاف قسم ملاحظات المراجعة"],
                "effect_on_admin_excel": [],
                "blocked_reason_if_inactive": "",
                "external_api_required": False,
                "advisory_only": True,
            },
            "hbu_report": {
                "label_ar": "تقارير أعلى وأفضل استخدام",
                "state": "advisory_only",
                "description_ar": "تقرير أعلى وأفضل استغلال — يتطلب بيانات HBU.",
                "required_inputs": ["hbu_scenarios"],
                "effect_on_user_pdf": ["قد يُضاف قسم تحليل أعلى وأفضل استغلال"],
                "effect_on_admin_excel": ["قد تُضاف ورقة HBU Analysis"],
                "blocked_reason_if_inactive": "يحتاج سيناريوهات أعلى وأفضل استغلال.",
                "external_api_required": False,
                "advisory_only": True,
            },
        }

        _pvcc_output_registry: dict = {
            "traditional_report": {
                "label_ar": "تقرير تقليدي",
                "user_pdf_allowed": True, "admin_excel_allowed": True,
                "certified_gate_required_for_final": True, "advisory_allowed": True,
            },
            "detailed_report": {
                "label_ar": "تقرير تفصيلي",
                "user_pdf_allowed": True, "admin_excel_allowed": True,
                "certified_gate_required_for_final": True, "advisory_allowed": True,
            },
            "professional_report": {
                "label_ar": "تقرير احترافي",
                "user_pdf_allowed": True, "admin_excel_allowed": True,
                "certified_gate_required_for_final": True, "advisory_allowed": True,
            },
            "simulated_uploaded_report": {
                "label_ar": "محاكاة تقرير مرفوع",
                "requires_uploaded_report": True, "requires_training_upload": True,
                "simulation_only": True, "user_pdf_allowed": True,
                "admin_excel_allowed": True, "advisory_allowed": True,
            },
            "report_review_output": {
                "label_ar": "مراجعة تقرير",
                "requires_report_review_toggle": True, "review_only": True,
                "user_pdf_allowed": True, "admin_excel_allowed": True, "advisory_allowed": True,
            },
            "hbu_analysis_report": {
                "label_ar": "تقرير تحليل أعلى وأفضل استخدام",
                "requires_hbu_report_toggle": True,
                "user_pdf_allowed": True, "admin_excel_allowed": True, "advisory_allowed": True,
            },
            "standards_compliance_report": {
                "label_ar": "تقرير امتثال المعايير",
                "requires_standards_context": True,
                "user_pdf_allowed": True, "admin_excel_allowed": True, "advisory_allowed": True,
            },
        }

        _pvcc_toggle_impact_matrix: dict = {
            "digital_inspector": {
                "state": "advisory_only",
                "user_pdf_effect":   "قد يُضاف قسم ملاحظات جودة البيانات",
                "admin_excel_effect": "قد تُضاف ورقة Data Quality / Inconsistencies",
                "advisory_warning":  "استرشادي — لا يعتمد على مصادر خارجية.",
            },
            "geotechnical_risk": {
                "state": "future_stub",
                "user_pdf_effect":   "قد يُضاف قسم المخاطر الجيوتقنية إذا توفرت البيانات",
                "admin_excel_effect": "قد تُضاف ورقة Geotechnical Risk Inputs",
                "blockers_if_missing_inputs": "يحتاج بيانات موقع/مخاطر",
                "advisory_warning":  "غير متاح — يتطلب بيانات جيوتقنية.",
            },
            "migration_radar": {
                "state": "future_stub",
                "user_pdf_effect":   "قد يُضاف قسم تحليل اتجاهات الطلب والهجرة",
                "admin_excel_effect": "قد تُضاف ورقة Demand & Migration Trend Inputs",
                "blockers_if_missing_inputs": "يحتاج بيانات اتجاهات سوق",
                "advisory_warning":  "غير متاح — يتطلب بيانات اتجاهات سوق.",
            },
            "asset_portfolio": {
                "state": "future_stub",
                "user_pdf_effect":   "قد يُضاف قسم تحليل ضمن محفظة الأصول",
                "admin_excel_effect": "قد تُضاف ورقة Portfolio Context",
                "blockers_if_missing_inputs": "يحتاج بيانات محفظة",
                "advisory_warning":  "غير متاح — يتطلب بيانات محفظة.",
            },
            "reference_library": {
                "state": "advisory_only",
                "user_pdf_effect":   "قد يُضاف قسم المراجع والمقارنات المرجعية",
                "admin_excel_effect": "قد تُضاف ورقة Reference Library Links",
                "advisory_warning":  "استرشادي — المراجع ليست مصادر رسمية.",
            },
            "super_intelligence": {
                "state": "advisory_only",
                "user_pdf_effect":   "تحليل استرشادي موسع",
                "admin_excel_effect": "",
                "advisory_warning":  "استرشادي — لا ادعاء بذكاء حقيقي. تحليل استرشادي موسع فقط.",
            },
        }

        _pvcc_upload_policy: dict = {
            "property_docs": {
                "label_ar": "وثائق العقار",
                "allowed_file_types": ["pdf", "jpg", "jpeg", "png", "xlsx", "xls", "docx"],
                "purpose": "source_evidence",
                "safe_metadata_only_in_response": True,
            },
            "report_simulation_sample": {
                "label_ar": "محاكاة تقرير مرفوع",
                "allowed_file_types": ["pdf", "docx", "xlsx"],
                "purpose": "style_structure_simulation",
                "not_real_training": True,
                "safe_metadata_only_in_response": True,
            },
        }

        _cert_ready: bool = rec.get("certification_ready", False)
        _pvcc_chat_command_center_context: dict = {
            # Unified Chat Toolbar (PVS6 updates)
            "single_chat_box":                     True,
            "compact_property_docs_clip":          True,
            "microphone_restored":                 True,
            "simulation_report_clip_available":    True,
            "review_report_clip_available":        True,
            "upper_duplicate_report_selector_visible": False,
            "lower_report_selector_preserved":     True,
            "visible_report_selectors_count":      1,
            # Legacy fields preserved
            "chat_input_available":                True,
            "property_docs_clip_available":        True,
            "training_report_clip_available":      True,   # backward compat alias
            "smart_mentions_available":            True,
            "available_uploaded_files":            [],
            "selected_report_action":              report_type or "traditional_report",
            "available_report_actions": [
                "traditional_report", "detailed_report", "professional_report",
                "simulated_uploaded_report", "report_review_output",
                "hbu_analysis_report", "standards_compliance_report",
            ],
            "active_feature_toggles":  [],
            "feature_toggle_states":   {k: v["state"] for k, v in _pvcc_feature_toggles_registry.items()},
            "user_pdf_output_available":               True,
            "admin_excel_output_available":            True,
            "admin_excel_visible_to_current_user":     False,
            "unified_output_controls": {
                "user_pdf":       True,
                "admin_excel":    False,
                "selected_output": True,
            },
            "upload_purpose_registry": {
                "property_docs": {
                    "label_ar": "وثائق العقار",
                    "source_type": "property_evidence",
                    "safe_metadata_only": True,
                },
                "report_simulation_sample": {
                    "label_ar": "رفع تقرير للمحاكاة",
                    "source_type": "simulation_sample",
                    "not_real_training": True,
                    "safe_metadata_only": True,
                },
                "report_review_source": {
                    "label_ar": "رفع تقرير للمراجعة",
                    "source_type": "standards_review_source",
                    "review_against": ["ivs", "ivsc_context", "uspap", "selected_section4_standards"],
                    "advisory_review_only": True,
                    "safe_metadata_only": True,
                },
            },
            "output_permissions": {
                "can_generate_user_pdf":       True,
                "can_generate_admin_excel":    False,
                "can_generate_certified_pdf":  _cert_ready,
                "can_generate_final_workbook": _cert_ready,
                "blockers":  [],
                "warnings":  ["جميع المخرجات استرشادية غير معتمدة ما لم تكتمل بوابة الاعتماد."],
                "advisory_only": True,
            },
            "warnings":   ["جميع المخرجات استرشادية غير معتمدة ما لم تكتمل بوابة الاعتماد."],
            "advisory_only":                       True,
            "certification_gate_controls_final_status": True,
            "certification_gates_preserved":       True,
            "external_apis_active":                False,
            "real_ml_training_claimed":            False,
            "debug_tokens_visible":                False,
            "duplicate_upper_chat_removed":        True,
            "real_lower_chat_preserved":           True,
        }

        # Unified professional valuation page context (server-side scaffold)
        _unified_pv_page_context: dict = {
            "request_id":                     request_id,
            "section2_asset_context": {
                "common_asset_type":      rec.get("property_type"),
                "asset_kind":             "common" if rec.get("property_type") else "unknown",
            },
            "asset_requirement_values_context": {
                "source":    "asset_requirement_tables",
                "available": bool(rec.get("asset_requirements")),
            },
            "section3_purpose_scope_context": {
                "assignment_purpose":  rec.get("valuation_purpose"),
                "basis_of_value":      rec.get("basis_of_value"),
                "intended_user":       rec.get("intended_user"),
            },
            "section4_standards_context": {
                "selected_standards":  rec.get("selected_standards", []),
            },
            "hbu_context":              {"available": False},
            "data_quality_context":     {"available": False, "completion_percent": 0},
            "expert_review_context":    {"available": False},
            "chat_instruction_context": {"available": False, "source": "chat_box"},
            "property_docs_context":    {"source": "property_docs_clip",      "files": [], "safe_metadata_only": True},
            "simulation_report_context":{"source": "simulation_report_clip",  "files": [], "not_real_training": True},
            "review_report_context":    {
                "source": "review_report_clip", "files": [], "advisory_review_only": True,
                "review_against": ["ivs", "ivsc_context", "uspap", "selected_section4_standards"],
            },
            "certification_gate_context": {
                "certification_ready":    _cert_ready,
                "final_outputs_allowed":  _cert_ready,
            },
            "warnings":     ["جميع المخرجات استرشادية حتى اكتمال بوابة الاعتماد."],
            "advisory_only": True,
        }

        # DCUB: Duplicate Chat Box cleanup context
        _dcub_context: dict = {
            "upper_duplicate_chat_box_removed": True,
            "real_lower_chat_box_preserved":    True,
            "backend_output_context_preserved": True,
            "certification_gates_preserved":    True,
            "debug_tokens_visible":             False,
            "compat_testids_in_dom":            True,
            "cleanup_advisory":                 (
                "الصندوق المكرر العلوي (5. صندوق الشات والمخرجات) تمت إزالته. "
                "صندوق الشات الحقيقي (ai-section) محفوظ ومرئي."
            ),
        }

        # Store purpose routes summary back into the persisted record
        _update_pvr(request_id, {
            "valuation_purpose_routes_summary": _pvr_summary,
            "legacy_purpose_aliases":           _legacy_purpose_aliases,
            "moved_purpose_options":            _moved_purpose_options,
            "taxonomy_cards_summary":           _taxonomy_cards_summary,
            "engine_governance_audit_context":  _engine_governance_ctx,
            "main_page_sections_context":       _main_page_sections_ctx,
            "advanced_controls_context":        _advanced_controls_ctx,
            "asset_type_selection_context":     _asset_type_selection_ctx,
            # PVS3 additions — Section 3 three-step clean flow
            "section3_purpose_context":              _section3_purpose_context,
            # PVS3 Section 3 merge additions
            "section3_1_purpose_context":            _section3_1_purpose_context,
            "professional_targeting_context":        _professional_targeting_context,
            "section3_cleanup_context":              _section3_cleanup_context,
            "purpose_flow_registry_summary":         _purpose_flow_registry_summary,
            "professional_targeting_registry_summary": _professional_targeting_registry_summary,
            "section3_1_legacy_mapping":             _section3_1_legacy_mapping,
            "professional_targeting_legacy_mapping": _professional_targeting_legacy_mapping,
            "pvs3_no_deletion_audit":                _pvs3_no_deletion_audit,
            # PVPBSR additions
            "valuation_purpose_context":             _valuation_purpose_context,
            "purpose_registry_context":              _purpose_registry_context,
            "basis_registry_context":                _basis_registry_context,
            "intended_user_registry_context":        _intended_user_registry_context,
            "professional_path_registry_context":    _professional_path_registry_context,
            "scope_registry_context":                _scope_registry_context,
            "disclosure_warning_registry_context":   _disclosure_warning_registry_context,
            "routing_matrix_registry_context":       _routing_matrix_registry_context,
            # Section 3 canonical taxonomy v2 registries (Part H)
            "purpose_taxonomy_v2_registries":        _purpose_taxonomy_registries,
            # PVASR additions
            "applied_standards_context":             _applied_standards_context,
            "standards_registry_context":            _standards_registry_context,
            "standards_mapping_matrix_context":      _standards_mapping_matrix_context,
            "standards_compliance_rules_context":    _standards_compliance_rules_context,
            # PVDSR additions
            "special_asset_requirements_context":    special_asset_requirements_context,
            "asset_methodology_guidance":            asset_methodology_guidance,
            "asset_report_workbook_context":         asset_report_workbook_context,
            "future_integrations":                   future_integrations,
            "special_asset_taxonomy_v2_registries":  special_asset_taxonomy_v2_registries,
            # PVACR additions
            "chat_output_context":                        chat_output_context,
            "report_output_registry_context":             report_output_registry_context,
            "output_format_visibility_policy_context":    output_format_visibility_policy_context,
            "deprecated_visible_controls_context":        deprecated_visible_controls_context,
            # DCUB additions
            "duplicate_chat_box_cleanup_context":         _dcub_context,
            # PVCC additions
            "chat_command_center_context":                _pvcc_chat_command_center_context,
            "chat_feature_toggles_registry_context":     _pvcc_feature_toggles_registry,
            "chat_output_registry_context":              _pvcc_output_registry,
            "chat_toggle_impact_matrix_context":         _pvcc_toggle_impact_matrix,
            "chat_upload_policy_context":                _pvcc_upload_policy,
            # PVS6 unified page context
            "unified_professional_valuation_page_context": _unified_pv_page_context,
        })
        rec["valuation_purpose_routes_summary"] = _pvr_summary
        rec["legacy_purpose_aliases"]           = _legacy_purpose_aliases
        rec["moved_purpose_options"]            = _moved_purpose_options
        rec["taxonomy_cards_summary"]           = _taxonomy_cards_summary
        rec["engine_governance_audit_context"]  = _engine_governance_ctx
        rec["main_page_sections_context"]       = _main_page_sections_ctx
        rec["advanced_controls_context"]        = _advanced_controls_ctx
        rec["asset_type_selection_context"]     = _asset_type_selection_ctx
        # PVS3 additions
        rec["section3_purpose_context"]                    = _section3_purpose_context
        # PVS3 Section 3 merge additions
        rec["section3_1_purpose_context"]                  = _section3_1_purpose_context
        rec["professional_targeting_context"]              = _professional_targeting_context
        rec["section3_cleanup_context"]                    = _section3_cleanup_context
        rec["purpose_flow_registry_summary"]               = _purpose_flow_registry_summary
        rec["professional_targeting_registry_summary"]     = _professional_targeting_registry_summary
        rec["section3_1_legacy_mapping"]                   = _section3_1_legacy_mapping
        rec["professional_targeting_legacy_mapping"]       = _professional_targeting_legacy_mapping
        rec["pvs3_no_deletion_audit"]                      = _pvs3_no_deletion_audit
        # PVPBSR additions
        rec["valuation_purpose_context"]                   = _valuation_purpose_context
        rec["purpose_registry_context"]            = _purpose_registry_context
        rec["basis_registry_context"]              = _basis_registry_context
        rec["intended_user_registry_context"]      = _intended_user_registry_context
        rec["professional_path_registry_context"]  = _professional_path_registry_context
        rec["scope_registry_context"]              = _scope_registry_context
        rec["disclosure_warning_registry_context"] = _disclosure_warning_registry_context
        rec["routing_matrix_registry_context"]     = _routing_matrix_registry_context
        # Section 3 canonical taxonomy v2 registries
        rec["purpose_taxonomy_v2_registries"]      = _purpose_taxonomy_registries
        # PVASR additions
        rec["applied_standards_context"]          = _applied_standards_context
        rec["standards_registry_context"]         = _standards_registry_context
        rec["standards_mapping_matrix_context"]   = _standards_mapping_matrix_context
        rec["standards_compliance_rules_context"] = _standards_compliance_rules_context
        # PVRT additions
        rec["report_type_context"]                    = _report_type_context
        rec["report_type_registry_context"]           = _report_type_registry_context
        rec["report_type_difference_matrix_context"]  = _report_type_difference_matrix_context
        rec["report_output_configuration_context"]    = _report_output_configuration_context
        # PVDSR additions
        rec["special_asset_requirements_context"]   = special_asset_requirements_context
        rec["asset_methodology_guidance"]            = asset_methodology_guidance
        rec["asset_report_workbook_context"]         = asset_report_workbook_context
        rec["future_integrations"]                   = future_integrations
        rec["special_asset_taxonomy_v2_registries"]  = special_asset_taxonomy_v2_registries
        # PVACR additions
        rec["chat_output_context"]                     = chat_output_context
        rec["report_output_registry_context"]          = report_output_registry_context
        rec["output_format_visibility_policy_context"] = output_format_visibility_policy_context
        rec["deprecated_visible_controls_context"]     = deprecated_visible_controls_context
        # DCUB additions
        rec["duplicate_chat_box_cleanup_context"]      = _dcub_context
        # PVCC additions
        rec["chat_command_center_context"]             = _pvcc_chat_command_center_context
        rec["chat_feature_toggles_registry_context"]  = _pvcc_feature_toggles_registry
        rec["chat_output_registry_context"]            = _pvcc_output_registry
        rec["chat_toggle_impact_matrix_context"]       = _pvcc_toggle_impact_matrix
        rec["chat_upload_policy_context"]              = _pvcc_upload_policy
        # PVS6 unified page context
        rec["unified_professional_valuation_page_context"] = _unified_pv_page_context

        resp_body: dict = {
            "ok":                    True,
            "request_id":            request_id,
            "request_number":        request_id,
            "status":                "submitted",
            "message":               (
                f"تم تسجيل طلب التقييم المهني بنجاح. رقم الطلب: {request_id}."
            ),
            "ordinary_visible_summary": rec["ordinary_visible_summary"],
            "taxonomy_cards_summary":  _taxonomy_cards_summary,
            "valuation_purpose_routes_summary": _pvr_summary,
            "legacy_purpose_aliases":  _legacy_purpose_aliases,
            "moved_purpose_options":   _moved_purpose_options,
            "taxonomy_warnings":       _taxonomy_ctx.get("taxonomy_warnings", []),
            "canonical_taxonomy":    rec["canonical_taxonomy"],
            "derived_method_route":  rec["derived_method_route"],
            "asset_specific_requirements": {
                "requirements_panel_title_ar": _asset_req.get("requirements_panel_title_ar", ""),
                "asset_label_ar":      _asset_req.get("asset_label_ar", ""),
                "required_inputs":    _asset_req.get("required_inputs", []),
                "normalized_requirement_keys": _asset_req.get("normalized_requirement_keys", []),
                "normalized_requirements_count": _asset_req.get("normalized_requirements_count", 0),
                "required_evidence":  _asset_req.get("required_evidence", []),
                "recommended_methods": _asset_req.get("recommended_methods", []),
                "recommended_workbook_sheets": _asset_req.get("recommended_workbook_sheets", []),
                "recommended_pdf_sections": _asset_req.get("recommended_pdf_sections", []),
                "warnings":           _asset_req.get("warnings", []),
                "legacy_requirement_keys": _asset_req.get("legacy_requirement_keys", []),
                "legacy_requirements_count": _asset_req.get("legacy_requirements_count", 0),
                "total_requirements_count": _asset_req.get("total_requirements_count", 0),
                "requirement_groups":  _asset_req.get("requirement_groups", []),
                "preservation_pass":   _asset_req.get("preservation_pass", True),
                "missing_from_current_after_restore": _asset_req.get("missing_from_current_after_restore", []),
                "deleted_requirements": _asset_req.get("deleted_requirements", []),
                "asset_type_resolved": _asset_req.get("asset_type_resolved", ""),
                "is_generic_fallback": _asset_req.get("is_generic_fallback", True),
            },
            "professional_valuation_feature_capabilities": rec.get(
                "professional_valuation_feature_capabilities", {}
            ),
            "control_activation_roadmap": rec.get("control_activation_roadmap", []),
            "report_reflection_matrix":   rec.get("report_reflection_matrix", {}),
            # Section 5 context returned to frontend
            "selected_configuration_summary": {
                "input_mode":             input_mode,
                "auto_fill_requirements": auto_fill_requirements,
                "output_type":            report_type,
                "is_simulation_output":   _is_simulation_output,
                "purpose_logic_path":     purpose_logic_path or None,
            },
            "engine_governance_audit_context":  _engine_governance_ctx,
            "main_page_sections_context":      _main_page_sections_ctx,
            "advanced_controls_context":       _advanced_controls_ctx,
            "asset_type_selection_context":    _asset_type_selection_ctx,
            # PVS3 context additions
            "section3_purpose_context":                  _section3_purpose_context,
            # PVS3 Section 3 merge additions
            "section3_1_purpose_context":                _section3_1_purpose_context,
            "professional_targeting_context":            _professional_targeting_context,
            "section3_cleanup_context":                  _section3_cleanup_context,
            "purpose_flow_registry_summary":             _purpose_flow_registry_summary,
            "professional_targeting_registry_summary":   _professional_targeting_registry_summary,
            "section3_1_legacy_mapping":                 _section3_1_legacy_mapping,
            "professional_targeting_legacy_mapping":     _professional_targeting_legacy_mapping,
            "pvs3_no_deletion_audit":                    _pvs3_no_deletion_audit,
            # PVPBSR context additions
            "valuation_purpose_context":                 _valuation_purpose_context,
            "purpose_registry_context":            _purpose_registry_context,
            "basis_registry_context":              _basis_registry_context,
            "intended_user_registry_context":      _intended_user_registry_context,
            "professional_path_registry_context":  _professional_path_registry_context,
            "scope_registry_context":              _scope_registry_context,
            "disclosure_warning_registry_context": _disclosure_warning_registry_context,
            "routing_matrix_registry_context":     _routing_matrix_registry_context,
            # Section 3 canonical taxonomy v2 registries (Part H)
            "purpose_taxonomy_v2_registries":      _purpose_taxonomy_registries,
            # PVASR additions
            "applied_standards_context":           _applied_standards_context,
            "standards_registry_context":          _standards_registry_context,
            "standards_mapping_matrix_context":    _standards_mapping_matrix_context,
            "standards_compliance_rules_context":  _standards_compliance_rules_context,
            # PVRT additions
            "report_type_context":                   _report_type_context,
            "report_type_registry_context":          _report_type_registry_context,
            "report_type_difference_matrix_context": _report_type_difference_matrix_context,
            "report_output_configuration_context":   _report_output_configuration_context,
            # PVDSR additions
            "special_asset_requirements_context":    special_asset_requirements_context,
            "asset_methodology_guidance":            asset_methodology_guidance,
            "asset_report_workbook_context":         asset_report_workbook_context,
            "future_integrations":                   future_integrations,
            "special_asset_taxonomy_v2_registries":  special_asset_taxonomy_v2_registries,
            # PVACR additions
            "chat_output_context":                       chat_output_context,
            "report_output_registry_context":            report_output_registry_context,
            "output_format_visibility_policy_context":   output_format_visibility_policy_context,
            "deprecated_visible_controls_context":       deprecated_visible_controls_context,
            "chat_attachment_draft_summary": (
                {
                    "advisory_only": True,
                    "draft_note_ar": "المدخلات عبر الشات والمشابك مسودة استرشادية — تتطلب مراجعة الخبير.",
                }
                if input_mode == "chat_attachment_assisted_input" else None
            ),
            "uploaded_report_simulation_summary": (
                {
                    "advisory_only":         True,
                    "certified_output":      False,
                    "simulation_note_ar":    (
                        "محاكاة تقرير مرفوع — لمراجعة هيكل التقرير فقط. "
                        "لا تُعتمد البيانات أو التوقيعات أو الأختام."
                    ),
                }
                if uploaded_report_simulation_enabled else None
            ),
            # DCUB additions
            "duplicate_chat_box_cleanup_context": _dcub_context,
            # PVCC additions
            "chat_command_center_context":            _pvcc_chat_command_center_context,
            "chat_feature_toggles_registry_context": _pvcc_feature_toggles_registry,
            "chat_output_registry_context":          _pvcc_output_registry,
            "chat_toggle_impact_matrix_context":     _pvcc_toggle_impact_matrix,
            "chat_upload_policy_context":            _pvcc_upload_policy,
            # PVS6 unified page context
            "unified_professional_valuation_page_context": _unified_pv_page_context,
            # PVS3-REMOVE-35-DW: removed visible advisory sections context
            "removed_visible_advisory_sections_context": {
                "preliminary_method_weighting": {
                    "visible_in_ui": False,
                    "backend_data_preserved": True,
                    "note_ar": "الأوزان المبدئية مخفية من الواجهة — البيانات محفوظة في الخلفية",
                },
                "dynamic_inline_disclosures": {
                    "visible_in_ui": False,
                    "backend_data_preserved": True,
                    "note_ar": "الإفصاحات الديناميكية مخفية من الواجهة — محفوظة في الخلفية",
                },
                "certification_gates_preserved": True,
                "removal_scope": "visible_advisory_sections_only",
                "backend_integrity": "unaffected",
            },
        }
        if _matrix_warnings:
            resp_body["matrix_warnings"] = _matrix_warnings
            resp_body["taxonomy_warnings"] = _taxonomy_ctx.get("taxonomy_warnings", [])
        return jsonify(resp_body), 201

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

    # ── GET /api/professional-valuation/standards/catalogue ──────────────
    @app.route("/api/professional-valuation/standards/catalogue", methods=["GET"])
    @require_auth
    def pvr_standards_catalogue():
        _ivs_refs_cat = [
            {"key": "ivs_100_framework",            "label_ar": "IVS 100 — الإطار العام"},
            {"key": "ivs_101_scope_of_work",        "label_ar": "IVS 101 — نطاق العمل"},
            {"key": "ivs_102_bases_of_value",       "label_ar": "IVS 102 — أسس القيمة"},
            {"key": "ivs_103_valuation_approaches", "label_ar": "IVS 103 — منهجيات التقييم"},
            {"key": "ivs_104_data_and_inputs",      "label_ar": "IVS 104 — البيانات والمدخلات"},
            {"key": "ivs_105_valuation_models",     "label_ar": "IVS 105 — نماذج التقييم"},
            {"key": "ivs_106_documentation_reporting","label_ar": "IVS 106 — التوثيق والتقرير"},
            {"key": "ivs_400_real_property_interests","label_ar": "IVS 400 — حقوق العقار"},
            {"key": "ivs_410_development_property", "label_ar": "IVS 410 — العقارات قيد التطوير"},
            {"key": "ivs_300_plant_equipment",      "label_ar": "IVS 300 — الآلات والمعدات"},
            {"key": "ivs_200_business_interests",   "label_ar": "IVS 200 — الشركات والمصالح"},
            {"key": "ivs_210_intangible_assets",    "label_ar": "IVS 210 — الأصول غير الملموسة"},
            {"key": "ivs_104", "label_ar": "IVS 104 — أطر التقييم", "legacy": True},
            {"key": "ivs_105", "label_ar": "IVS 105 — مناهج التقييم", "legacy": True},
            {"key": "ivs_400", "label_ar": "IVS 400 — العقارات الحقيقية", "legacy": True},
            {"key": "ivs_410", "label_ar": "IVS 410 — تطوير العقارات", "legacy": True},
            {"key": "ivs_500", "label_ar": "IVS 500 — الآلات والمعدات", "legacy": True},
            {"key": "ivs_600", "label_ar": "IVS 600 — حقوق الأعمال", "legacy": True},
            {"key": "not_ivs", "label_ar": "لا ينطبق (Non-IVS)"},
        ]
        _rics_refs_cat = [
            {"key": "rics_red_book_global",   "label_ar": "RICS Red Book Global Standards"},
            {"key": "rics_vps_scope_terms",   "label_ar": "VPS — Terms of Engagement / Scope"},
            {"key": "rics_vps_inspections",   "label_ar": "VPS — Inspections and Investigations"},
            {"key": "rics_vps_reporting",     "label_ar": "VPS — Valuation Reports"},
            {"key": "rics_ps_ethics",         "label_ar": "Professional Standards / Ethics"},
        ]
        _ifrs_levels_cat = [
            {"key": "level_1", "label_ar": "Level 1 — أسعار سوق نشط قابلة للملاحظة"},
            {"key": "level_2", "label_ar": "Level 2 — مدخلات قابلة للملاحظة غير مباشرة"},
            {"key": "level_3", "label_ar": "Level 3 — مدخلات غير قابلة للملاحظة / تقديرات"},
            {"key": "na",      "label_ar": "غير مطبق"},
        ]
        _standards_cat = [
            {"key": "ivs_2025",             "label_ar": "IVS 2025",              "legacy_aliases": ["ivs_2022"]},
            {"key": "rics_red_book_2025",   "label_ar": "RICS Red Book 2025",    "legacy_aliases": ["rics_red_book"]},
            {"key": "ifrs_13",              "label_ar": "IFRS 13",               "legacy_aliases": []},
            {"key": "fra_egypt",            "label_ar": "FRA مصر",               "legacy_aliases": ["egyptian_standard", "eg_cma_circular"]},
            {"key": "gcc_standards",        "label_ar": "GCC معايير الخليج",     "legacy_aliases": ["gcc_standard"]},
            {"key": "custom_local_standard","label_ar": "معيار محلي / خاص",     "legacy_aliases": ["local_regulatory"]},
        ]
        _disclosure_cat = [
            {"key": "full_compliance",             "label_ar": "إفصاح كامل",              "legacy_aliases": ["full_disclosure"]},
            {"key": "summary_disclosure",          "label_ar": "إفصاح موجز",              "legacy_aliases": []},
            {"key": "limited_disclosure",          "label_ar": "إفصاح محدود",             "legacy_aliases": ["restricted_disclosure", "regulatory_minimum"]},
            {"key": "internal_advisory_disclosure","label_ar": "إفصاح داخلي استرشادي",    "legacy_aliases": ["internal_only", "confidential"]},
        ]
        return jsonify({
            "ok":                True,
            "registry_version":  "pvasr-v1",
            "standards_registry":       _standards_cat,
            "local_standards_registry": [
                {"key": "fra_egypt",                     "label_ar": "FRA — مصر"},
                {"key": "ministry_of_justice_egypt",     "label_ar": "وزارة العدل — مصر"},
                {"key": "real_estate_tax_authority_egypt","label_ar": "مصلحة الضرائب العقارية — مصر"},
                {"key": "cma_saudi",                     "label_ar": "هيئة السوق المالية — السعودية"},
                {"key": "rera_dubai",                    "label_ar": "دائرة الأراضي / RERA — دبي"},
                {"key": "sca_uae",                       "label_ar": "هيئة الأوراق المالية والسلع — الإمارات"},
                {"key": "gcc_general",                   "label_ar": "مرجع خليجي عام"},
                {"key": "eg_valuation_law",              "label_ar": "قانون التقييم المصري"},
                {"key": "eg_cma_circular",               "label_ar": "تعميم هيئة الرقابة المالية"},
                {"key": "eg_cbe_regulation",             "label_ar": "تعليمات البنك المركزي المصري"},
                {"key": "sa_zatca_circular",             "label_ar": "هيئة الزكاة والضريبة والجمارك (SA)"},
                {"key": "uae_rera",                      "label_ar": "هيئة تنظيم العقارات (دبي RERA)"},
                {"key": "none",                          "label_ar": "لا يوجد مرجع محلي"},
                {"key": "custom",                        "label_ar": "مرجع مخصص"},
            ],
            "ivs_references":    _ivs_refs_cat,
            "rics_references":   _rics_refs_cat,
            "ifrs_levels":       _ifrs_levels_cat,
            "disclosure_levels": _disclosure_cat,
            "advisory_only":     True,
        }), 200

    # ── GET /api/professional-valuation/report-types/catalogue ─────────────
    @app.route("/api/professional-valuation/report-types/catalogue", methods=["GET"])
    @require_auth
    def pvr_report_types_catalogue():
        _rt_cat = [
            {"key": "summary_report",               "label_ar": "تقرير موجز",  "label_en": "Summary Report",               "legacy_aliases": ["traditional_report", "تقرير تقليدي"], "pdf_sections_count": 8,  "workbook_sheets_count": 4,  "approximate_page_range": "3-8"},
            {"key": "full_report",                  "label_ar": "تقرير كامل",  "label_en": "Full Report",                  "legacy_aliases": ["detailed_report",     "تقرير تفصيلي"], "pdf_sections_count": 16, "workbook_sheets_count": 14, "approximate_page_range": "15-25"},
            {"key": "enhanced_professional_report", "label_ar": "تقرير شامل",  "label_en": "Enhanced Professional Report", "legacy_aliases": ["professional_report", "تقرير احترافي"],"pdf_sections_count": 28, "workbook_sheets_count": 26, "approximate_page_range": "30-60+"},
        ]
        return jsonify({
            "ok":                   True,
            "registry_version":     "pvrt-v1",
            "report_types":         _rt_cat,
            "legacy_aliases": {
                "traditional_report":  "summary_report",
                "detailed_report":     "full_report",
                "professional_report": "enhanced_professional_report",
            },
            "advisory_only":        True,
            "certified_requires_gate": True,
        }), 200

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
            "special_asset_requirements_context": rec.get("special_asset_requirements_context", {}),
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

    # ── PVACR: POST /api/professional-valuation/requests/<id>/chat-output/pdf
    @app.route(
        "/api/professional-valuation/requests/<string:request_id>/chat-output/pdf",
        methods=["POST"],
    )
    @require_auth
    def pvr_chat_output_pdf(request_id: str):
        body       = flask_request.get_json(force=True, silent=True) or {}
        action     = (body.get("report_action") or body.get("selected_report_action") or "").strip()
        rec        = _find_pvr(request_id)
        if rec is None:
            return jsonify({"ok": False, "error": "طلب غير موجود"}), 404
        _pvacr_r: dict = {}
        try:
            from professional_valuation_taxonomy_v2 import get_chat_output_registries
            _pvacr_r = get_chat_output_registries().get("report_output_registry", {})
        except (ImportError, Exception):
            pass
        entry = _pvacr_r.get(action, {})
        if action and not entry:
            return jsonify({"ok": False, "error": f"report_action غير معروف: '{action}'"}), 400
        return jsonify({
            "ok":              True,
            "request_id":      request_id,
            "report_action":   action or "advisory_draft",
            "output_type":     "user_pdf",
            "label_ar":        entry.get("label_ar", action),
            "advisory_only":   True,
            "certified_output": False,
            "message_ar":      "مسودة PDF استرشادية — غير معتمدة. تتطلب بوابة الاعتماد للإصدار النهائي.",
        }), 200

    # ── PVACR: POST /api/professional-valuation/requests/<id>/chat-output/admin-excel
    @app.route(
        "/api/professional-valuation/requests/<string:request_id>/chat-output/admin-excel",
        methods=["POST"],
    )
    @require_auth
    def pvr_chat_output_admin_excel(request_id: str):
        body   = flask_request.get_json(force=True, silent=True) or {}
        action = (body.get("report_action") or "").strip()
        rec    = _find_pvr(request_id)
        if rec is None:
            return jsonify({"ok": False, "error": "طلب غير موجود"}), 404
        # Admin-only: in absence of auth context, return access-denied advisory
        return jsonify({
            "ok":              False,
            "error":           "إصدار شيتات Excel محصور بدور الأدمن فقط.",
            "advisory_note":   "admin_only — admin_excel_visible_to_user: false",
            "report_action":   action or "",
            "output_type":     "admin_excel",
        }), 403

    # ── PVACR: POST /api/professional-valuation/requests/<id>/expert-review-request
    @app.route(
        "/api/professional-valuation/requests/<string:request_id>/expert-review-request",
        methods=["POST"],
    )
    @require_auth
    def pvr_expert_review_request(request_id: str):
        body   = flask_request.get_json(force=True, silent=True) or {}
        note   = (body.get("review_note") or body.get("note") or "").strip()
        rec    = _find_pvr(request_id)
        if rec is None:
            return jsonify({"ok": False, "error": "طلب غير موجود"}), 404
        now    = datetime.utcnow().isoformat()
        _update_pvr(request_id, {
            "expert_review_requested_at": now,
            "expert_review_note":         note,
            "expert_review_status":       "pending_expert_review",
        })
        return jsonify({
            "ok":                    True,
            "request_id":            request_id,
            "expert_review_status":  "pending_expert_review",
            "requested_at":          now,
            "review_note":           note,
            "advisory_only":         True,
            "message_ar":            (
                "تم تسجيل طلب مراجعة الخبير. لا يُعتمد التقرير تلقائياً — "
                "يتطلب مراجعة الخبير وموافقته عبر بوابة الاعتماد."
            ),
        }), 200


    # ── PVUAFR: GET /api/professional-valuation/requests/<id>/special-asset-requirements
    @app.route(
        "/api/professional-valuation/requests/<string:request_id>/special-asset-requirements",
        methods=["GET"],
    )
    @require_auth
    def pvr_get_special_asset_requirements(request_id: str):
        rec = _find_pvr(request_id)
        if rec is None:
            return jsonify({"ok": False, "error": "طلب غير موجود"}), 404
        asset_key   = flask_request.args.get("asset_key", "").strip()
        saved       = _SPECIAL_ASSET_REQ_VALUES.get(request_id, {})
        saved_values = saved.get("values", []) if (not asset_key or saved.get("selected_asset_key") == asset_key) else []
        completion  = saved.get("completion_summary", {
            "total_requirements_count":  0,
            "filled_requirements_count": 0,
            "missing_requirements_count": 0,
            "completion_percent":        0,
            "required_missing_keys":     [],
        })
        return jsonify({
            "ok":                True,
            "request_id":        request_id,
            "selected_asset_key": asset_key or saved.get("selected_asset_key", ""),
            "values":            saved_values,
            "completion_summary": completion,
            "advisory_only":     True,
        }), 200

    # ── PVUAFR: POST /api/professional-valuation/requests/<id>/special-asset-requirements
    @app.route(
        "/api/professional-valuation/requests/<string:request_id>/special-asset-requirements",
        methods=["POST"],
    )
    @require_auth
    def pvr_save_special_asset_requirements(request_id: str):
        rec = _find_pvr(request_id)
        if rec is None:
            return jsonify({"ok": False, "error": "طلب غير موجود"}), 404
        body       = flask_request.get_json(force=True, silent=True) or {}
        asset_key  = (body.get("selected_asset_key") or "").strip()
        values     = body.get("values") or []
        if not isinstance(values, list):
            return jsonify({"ok": False, "error": "values يجب أن يكون قائمة"}), 400
        # Compute completion summary
        total   = len(values)
        filled  = sum(1 for v in values if v.get("value") and str(v["value"]).strip())
        missing = total - filled
        pct     = round(filled / total * 100) if total > 0 else 0
        req_missing = [v.get("requirement_key", "") for v in values if not (v.get("value") and str(v["value"]).strip())]
        completion = {
            "total_requirements_count":   total,
            "filled_requirements_count":  filled,
            "missing_requirements_count": missing,
            "completion_percent":         pct,
            "required_missing_keys":      req_missing[:20],
        }
        _SPECIAL_ASSET_REQ_VALUES[request_id] = {
            "selected_asset_key": asset_key,
            "values":             values,
            "completion_summary": completion,
            "advisory_only":      True,
        }
        return jsonify({
            "ok":                True,
            "request_id":        request_id,
            "selected_asset_key": asset_key,
            "saved_count":       total,
            "completion_summary": completion,
            "advisory_only":     True,
            "message_ar":        "تم الحفظ المؤقت — استرشادي فقط. يتطلب مراجعة الخبير للاعتماد.",
        }), 200
