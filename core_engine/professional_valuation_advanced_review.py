"""
professional_valuation_advanced_review.py — Advanced Expert Review Workspace (Phase F).

Endpoints (all JWT-protected):
  GET  /api/professional-valuation/advanced-review/schema
  GET  /api/professional-valuation/requests/<id>/advanced-review
  POST /api/professional-valuation/requests/<id>/advanced-review/hbu
  POST /api/professional-valuation/requests/<id>/advanced-review/legal
  POST /api/professional-valuation/requests/<id>/advanced-review/esg
  POST /api/professional-valuation/requests/<id>/advanced-review/swot
  POST /api/professional-valuation/requests/<id>/advanced-review/<section>/approve-preliminary
  POST /api/professional-valuation/requests/<id>/advanced-review/<section>/reject

Storage (internal paths never exposed in API responses):
  instance/professional_valuation/advanced_reviews/<request_id>.json
  instance/professional_valuation/advanced_review_events/<request_id>.jsonl

Phase F scope: HBU, Legal, ESG, SWOT expert review sections.
  - No OCR, no Qdrant, no RAG, no external APIs.
  - production_ready=false always in Phase F.
  - certification_ready=false always in Phase F.
  - certified_use_allowed=false always in Phase F.
  - approved_for_preliminary may become true after expert review.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── Storage ───────────────────────────────────────────────────────────────────

_BASE          = Path(__file__).parent / "instance" / "professional_valuation"
_ADV_DIR       = _BASE / "advanced_reviews"
_ADV_EVENTS_DIR = _BASE / "advanced_review_events"

for _d in (_ADV_DIR, _ADV_EVENTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── ID / regex helpers ────────────────────────────────────────────────────────

_PVR_ID_RE   = re.compile(r"^PVR-\d{8}-[0-9A-F]{4,8}$")
_VALID_SECTIONS: frozenset[str] = frozenset({"hbu", "legal", "esg", "swot"})

def _new_pvar_id() -> str:
    return "PVAR-" + uuid.uuid4().hex[:8].upper()


# ── Section defaults ──────────────────────────────────────────────────────────

_VALID_STATUSES: frozenset[str] = frozenset({
    "not_started", "draft", "under_review", "needs_evidence",
    "approved_for_preliminary", "approved_for_certification",
    "rejected", "superseded",
})

def _empty_section(section_key: str, section_label_ar: str) -> dict:
    return {
        "section_key":               section_key,
        "section_label_ar":          section_label_ar,
        "status":                    "not_started",
        "completed":                 False,
        "approved_for_preliminary":  False,
        "approved_for_certification": False,
        "production_ready":          False,
        "reviewed_by":               None,
        "reviewed_at":               None,
        "expert_notes":              "",
        "missing_items":             [],
        "blockers":                  [],
        "warnings":                  [],
        "source_ids_used":           [],
        "evidence_ids_used":         [],
        "requires_additional_evidence": False,
        "official_use_allowed":      False,
        "certified_use_allowed":     False,
    }


def _empty_hbu() -> dict:
    rec = _empty_section("hbu", "الاستخدام الأمثل والأعلى إنتاجية")
    rec.update({
        "current_use":                   "",
        "candidate_uses":                [],
        "legally_permissible_test":      "",
        "physically_possible_test":      "",
        "financially_feasible_test":     "",
        "maximally_productive_test":     "",
        "selected_hbu":                  "",
        "hbu_conclusion":                "",
        "conversion_cost_estimate":      None,
        "incremental_income_estimate":   None,
        "legal_constraints":             "",
        "market_constraints":            "",
    })
    return rec


def _empty_legal() -> dict:
    rec = _empty_section("legal", "العناية القانونية الواجبة")
    rec.update({
        "ownership_type":                    "",
        "ownership_document_reviewed":       False,
        "ownership_document_evidence_id":    "",
        "title_restrictions":                "",
        "mortgage_or_lien_status":           "",
        "legal_dispute_status":              "",
        "last_transfer_date":                "",
        "zoning_or_planning_restrictions":   "",
        "permits_reviewed":                  False,
        "missing_legal_documents":           [],
        "legal_scope_limitation":            (
            "لم يتم إجراء فحص قانوني كامل، ويعد ذلك قيداً على نطاق العمل "
            "ولا يمثل التقرير رأياً قانونياً في صحة الملكية."
        ),
        "legal_conclusion":                  "",
    })
    return rec


def _empty_esg() -> dict:
    rec = _empty_section("esg", "تقييم ESG والمخاطر المناخية")
    rec.update({
        "esg_data_available":              False,
        "esg_score":                       None,
        "esg_category":                    "",
        "energy_efficiency_notes":         "",
        "water_efficiency_notes":          "",
        "accessibility_notes":             "",
        "climate_risk_score":              None,
        "climate_risk_category":           "",
        "flood_heat_or_environmental_risks": "",
        "insurance_cost_impact":           "",
        "cap_rate_adjustment_basis":       "",
        "discount_rate_adjustment_basis":  "",
        "terminal_value_adjustment_basis": "",
        "esg_value_impact_commentary":     "غير مكتمل — لا يطبق أثر إنتاجي",
    })
    return rec


def _empty_swot() -> dict:
    rec = _empty_section("swot", "تحليل SWOT والمخاطر الاستراتيجية")
    rec.update({
        "strengths":               [],
        "weaknesses":              [],
        "opportunities":           [],
        "threats":                 [],
        "weighted_priority_matrix": [],
        "highest_risk":            "",
        "highest_opportunity":     "",
        "hbu_linkage":             "",
        "dcf_linkage":             "",
        "uncertainty_linkage":     "",
        "recommendation_linkage":  "",
        "risk_heatmap":            [],
    })
    return rec


def _empty_advanced_review(request_id: str) -> dict:
    return {
        "request_id":              request_id,
        "updated_at":              None,
        "updated_by":              None,
        "hbu_review":              _empty_hbu(),
        "legal_due_diligence_review": _empty_legal(),
        "esg_climate_review":      _empty_esg(),
        "swot_risk_review":        _empty_swot(),
        "advanced_review_summary": {
            "total_sections":                4,
            "completed_sections":            0,
            "preliminary_approved_sections": 0,
            "all_advanced_reviews_prelim_ready": False,
            "all_advanced_reviews_cert_ready":   False,
            "missing_sections":              ["hbu", "legal", "esg", "swot"],
            "blockers":                      [],
            "required_actions":              [],
            "advisory_only_reason":          (
                "Phase F — advanced expert reviews can be approved for preliminary/internal "
                "use only. Final certification remains blocked."
            ),
        },
        "certification_gate_fragment": {
            "hbu_completed":              False,
            "legal_due_diligence_ready":  False,
            "esg_reviewed":               False,
            "swot_completed":             False,
            "advanced_reviews_prelim_ready": False,
            "advanced_reviews_cert_ready":   False,
        },
    }


# ── Storage helpers ───────────────────────────────────────────────────────────

def _load_advanced_review(request_id: str) -> dict:
    path = _ADV_DIR / f"{request_id}.json"
    if not path.exists():
        return _empty_advanced_review(request_id)
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return _empty_advanced_review(request_id)


def _save_advanced_review(rec: dict) -> None:
    rid  = rec["request_id"]
    path = _ADV_DIR / f"{rid}.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=2)


def _append_event(request_id: str, action: str, section: str, detail: dict) -> None:
    path = _ADV_EVENTS_DIR / f"{request_id}.jsonl"
    event = {
        "event_id":   "PVARE-" + uuid.uuid4().hex[:8].upper(),
        "request_id": request_id,
        "action":     action,
        "section":    section,
        "detail":     detail,
        "ts":         datetime.utcnow().isoformat() + "Z",
    }
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


def read_advanced_review_events(request_id: str) -> list[dict]:
    """Public helper for test assertions."""
    path = _ADV_EVENTS_DIR / f"{request_id}.jsonl"
    if not path.exists():
        return []
    events = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return events


# ── SWOT item builder ─────────────────────────────────────────────────────────

def _build_swot_item(raw: dict) -> dict:
    impact      = max(1, min(5, int(raw.get("impact_score", 1) or 1)))
    probability = max(1, min(5, int(raw.get("probability_score", 1) or 1)))
    return {
        "category":              str(raw.get("category", "")),
        "title_ar":              str(raw.get("title_ar", ""))[:500],
        "description_ar":        str(raw.get("description_ar", ""))[:2000],
        "evidence_basis":        str(raw.get("evidence_basis", "")),
        "related_section":       str(raw.get("related_section", "")),
        "impact_score":          impact,
        "probability_score":     probability,
        "priority_score":        impact * probability,
        "value_impact_direction": str(raw.get("value_impact_direction", "neutral")),
        "action_required":       bool(raw.get("action_required", False)),
        "source_quality_status": str(raw.get("source_quality_status", "advisory")),
    }


# ── Summary / gate recomputation ──────────────────────────────────────────────

def _recompute_summary(rec: dict) -> dict:
    hbu   = rec["hbu_review"]
    legal = rec["legal_due_diligence_review"]
    esg   = rec["esg_climate_review"]
    swot  = rec["swot_risk_review"]

    hbu_done   = hbu.get("completed", False)
    legal_done = legal.get("completed", False)
    esg_done   = esg.get("completed", False)
    swot_done  = swot.get("completed", False)

    hbu_prelim   = hbu.get("approved_for_preliminary", False)
    legal_prelim = legal.get("approved_for_preliminary", False)
    esg_prelim   = esg.get("approved_for_preliminary", False)
    swot_prelim  = swot.get("approved_for_preliminary", False)

    completed_count  = sum([hbu_done, legal_done, esg_done, swot_done])
    prelim_count     = sum([hbu_prelim, legal_prelim, esg_prelim, swot_prelim])
    all_prelim_ready = (prelim_count == 4)

    missing: list[str] = []
    blockers: list[str] = []
    if not hbu_done:
        missing.append("hbu")
        blockers.append("HBU review incomplete — الاستخدام الأمثل غير مكتمل")
    if not legal_done:
        missing.append("legal")
        blockers.append("Legal due diligence incomplete — العناية القانونية غير مكتملة")
    if not esg_done:
        missing.append("esg")
        blockers.append("ESG/climate review incomplete — تقييم ESG غير مكتمل")
    if not swot_done:
        missing.append("swot")
        blockers.append("SWOT/risk review incomplete — تحليل SWOT غير مكتمل")

    summary = {
        "total_sections":                4,
        "completed_sections":            completed_count,
        "preliminary_approved_sections": prelim_count,
        "all_advanced_reviews_prelim_ready": all_prelim_ready,
        "all_advanced_reviews_cert_ready":   False,
        "missing_sections":              missing,
        "blockers":                      blockers,
        "required_actions":              [],
        "advisory_only_reason": (
            "Phase F — advanced expert reviews can be approved for preliminary/internal "
            "use only. Final certification remains blocked."
        ),
    }

    gate_fragment = {
        "hbu_completed":              hbu_done,
        "legal_due_diligence_ready":  legal_done,
        "esg_reviewed":               esg_done,
        "swot_completed":             swot_done,
        "advanced_reviews_prelim_ready": all_prelim_ready,
        "advanced_reviews_cert_ready":   False,
    }

    rec["advanced_review_summary"]      = summary
    rec["certification_gate_fragment"]  = gate_fragment
    return rec


# ── HBU validation ────────────────────────────────────────────────────────────

def _validate_hbu(hbu: dict) -> tuple[bool, list[str]]:
    """Returns (completed, blockers)."""
    blockers = []
    tests = [
        ("legally_permissible_test",  "اختبار المسموحية القانونية مطلوب"),
        ("physically_possible_test",  "اختبار الإمكانية الفيزيائية مطلوب"),
        ("financially_feasible_test", "اختبار الجدوى الاقتصادية مطلوب"),
        ("maximally_productive_test", "اختبار الأعلى إنتاجية مطلوب"),
    ]
    for key, msg in tests:
        if not str(hbu.get(key) or "").strip():
            blockers.append(msg)
    if not str(hbu.get("selected_hbu") or "").strip():
        blockers.append("الاستخدام الأمثل المختار (selected_hbu) مطلوب للاعتماد")
    completed = len(blockers) == 0
    return completed, blockers


# ── Legal validation ──────────────────────────────────────────────────────────

def _validate_legal(legal: dict) -> tuple[bool, list[str]]:
    blockers = []
    if not legal.get("ownership_document_reviewed", False):
        blockers.append("وثيقة الملكية لم يتم مراجعتها — لا يمكن إتمام الاعتماد النهائي")
    if not str(legal.get("legal_conclusion") or "").strip():
        blockers.append("خلاصة الفحص القانوني مطلوبة")
    completed = not any(b for b in blockers if "النهائي" not in b)
    # legal can be completed even without ownership doc (with limitation)
    completed = bool(str(legal.get("legal_conclusion") or "").strip())
    return completed, blockers


# ── ESG validation ────────────────────────────────────────────────────────────

def _validate_esg(esg: dict) -> tuple[bool, list[str]]:
    blockers = []
    if not esg.get("esg_data_available", False):
        esg["esg_value_impact_commentary"] = "غير مكتمل — لا يطبق أثر إنتاجي"
        blockers.append("بيانات ESG غير متوفرة — التقرير يبقى استشارياً")
    completed = bool(
        str(esg.get("esg_value_impact_commentary") or "").strip()
        or str(esg.get("expert_notes") or "").strip()
    )
    return completed, blockers


# ── SWOT validation ───────────────────────────────────────────────────────────

def _validate_swot(swot: dict) -> tuple[bool, list[str]]:
    blockers = []
    for cat in ("strengths", "weaknesses", "opportunities", "threats"):
        if not swot.get(cat):
            label_map = {
                "strengths": "نقاط القوة",
                "weaknesses": "نقاط الضعف",
                "opportunities": "الفرص",
                "threats": "التهديدات",
            }
            blockers.append(f"يجب إدخال عنصر واحد على الأقل لـ {label_map[cat]}")
    completed = len(blockers) == 0
    return completed, blockers


# ── Safe section strip (remove internal fields before API response) ────────────

def _safe_section(sec: dict) -> dict:
    """Strip expert_notes from sections returned in non-expert contexts.
    For Phase F all responses are expert-protected (JWT required), so we keep them.
    """
    return sec


# ── Public gate helper (used by routes.py) ───────────────────────────────────

def get_advanced_review_gate_fragment(request_id: str) -> dict:
    """Return advanced review gate fields for merging into certification gate."""
    rec = _load_advanced_review(request_id)
    return rec.get("certification_gate_fragment", {
        "hbu_completed":              False,
        "legal_due_diligence_ready":  False,
        "esg_reviewed":               False,
        "swot_completed":             False,
        "advanced_reviews_prelim_ready": False,
        "advanced_reviews_cert_ready":   False,
    })


# ── Schema ────────────────────────────────────────────────────────────────────

_SCHEMA = {
    "sections": [
        {
            "section_key":   "hbu",
            "section_label_ar": "الاستخدام الأمثل والأعلى إنتاجية",
            "hbu_tests": [
                {"key": "legally_permissible_test",  "label_ar": "قانوني مسموح"},
                {"key": "physically_possible_test",  "label_ar": "ممكن فيزيائياً"},
                {"key": "financially_feasible_test", "label_ar": "مجدي اقتصادياً"},
                {"key": "maximally_productive_test", "label_ar": "الأعلى ربحية"},
            ],
            "required_for_completion": [
                "legally_permissible_test", "physically_possible_test",
                "financially_feasible_test", "maximally_productive_test",
                "selected_hbu",
            ],
        },
        {
            "section_key":      "legal",
            "section_label_ar": "العناية القانونية الواجبة",
            "disclaimer": (
                "لم يتم إجراء فحص قانوني كامل، ويعد ذلك قيداً على نطاق العمل "
                "ولا يمثل التقرير رأياً قانونياً في صحة الملكية."
            ),
            "required_for_completion": ["legal_conclusion"],
        },
        {
            "section_key":      "esg",
            "section_label_ar": "تقييم ESG والمخاطر المناخية",
            "advisory_note":    "أي تعديل على معدل الرسملة/الخصم يبقى استشارياً ما لم يكن مدعوماً بمصدر.",
            "required_for_completion": [],
        },
        {
            "section_key":      "swot",
            "section_label_ar": "تحليل SWOT والمخاطر الاستراتيجية",
            "required_for_completion": [
                "at_least_one_strength", "at_least_one_weakness",
                "at_least_one_opportunity", "at_least_one_threat",
            ],
        },
    ],
    "statuses": list(_VALID_STATUSES),
    "swot_score_range": {"min": 1, "max": 5, "priority_formula": "impact_score × probability_score"},
    "phase_f_rules": {
        "certified_use_allowed":         False,
        "approved_for_certification":     False,
        "production_ready":               False,
        "certification_ready":            False,
        "preliminary_approval_allowed":   True,
        "no_ocr":                         True,
        "no_qdrant":                      True,
        "no_rag":                         True,
        "no_external_api":                True,
    },
    "warning": (
        "Phase F: advanced expert reviews can be approved for preliminary/internal use only. "
        "Final certification remains blocked."
    ),
}


# ── Route registration ────────────────────────────────────────────────────────

def register_pv_advanced_review_routes(app, require_auth) -> None:
    """Register all Phase F advanced review routes on the Flask app."""
    from flask import request as freq, jsonify

    # ── GET schema ────────────────────────────────────────────────────────────

    @app.route("/api/professional-valuation/advanced-review/schema", methods=["GET"])
    @require_auth
    def pv_advanced_review_schema():
        return jsonify({"ok": True, "schema": _SCHEMA}), 200

    # ── GET advanced review ───────────────────────────────────────────────────

    @app.route(
        "/api/professional-valuation/requests/<request_id>/advanced-review",
        methods=["GET"],
    )
    @require_auth
    def pv_get_advanced_review(request_id: str):
        if not _PVR_ID_RE.match(request_id):
            return jsonify({"ok": False, "error": "request_id غير صالح"}), 400
        rec = _load_advanced_review(request_id)
        _recompute_summary(rec)
        return jsonify({
            "ok":                      True,
            "request_id":              request_id,
            "hbu_review":              _safe_section(rec["hbu_review"]),
            "legal_due_diligence_review": _safe_section(rec["legal_due_diligence_review"]),
            "esg_climate_review":      _safe_section(rec["esg_climate_review"]),
            "swot_risk_review":        _safe_section(rec["swot_risk_review"]),
            "advanced_review_summary": rec["advanced_review_summary"],
            "certification_gate_fragment": rec["certification_gate_fragment"],
            "phase_f_warning": (
                "Phase F: advanced expert reviews approved for preliminary internal use only. "
                "Certified/final approval remains blocked."
            ),
        }), 200

    # ── POST HBU review ───────────────────────────────────────────────────────

    @app.route(
        "/api/professional-valuation/requests/<request_id>/advanced-review/hbu",
        methods=["POST"],
    )
    @require_auth
    def pv_save_hbu_review(request_id: str):
        if not _PVR_ID_RE.match(request_id):
            return jsonify({"ok": False, "error": "request_id غير صالح"}), 400
        body = freq.get_json(silent=True) or {}
        rec  = _load_advanced_review(request_id)
        hbu  = rec["hbu_review"]

        # Update fields from body (string fields capped at 5000 chars)
        _str_fields = [
            "current_use", "legally_permissible_test", "physically_possible_test",
            "financially_feasible_test", "maximally_productive_test",
            "selected_hbu", "hbu_conclusion", "legal_constraints",
            "market_constraints", "expert_notes",
        ]
        for f in _str_fields:
            if f in body:
                hbu[f] = str(body[f] or "")[:5000]

        if "candidate_uses" in body:
            hbu["candidate_uses"] = [str(u)[:500] for u in (body["candidate_uses"] or [])[:20]]
        if "evidence_ids_used" in body:
            hbu["evidence_ids_used"] = [str(i)[:100] for i in (body["evidence_ids_used"] or [])[:50]]
        if "source_ids_used" in body:
            hbu["source_ids_used"] = [str(i)[:100] for i in (body["source_ids_used"] or [])[:50]]
        if "conversion_cost_estimate" in body:
            try:
                hbu["conversion_cost_estimate"] = float(body["conversion_cost_estimate"])
            except (TypeError, ValueError):
                hbu["conversion_cost_estimate"] = None
        if "incremental_income_estimate" in body:
            try:
                hbu["incremental_income_estimate"] = float(body["incremental_income_estimate"])
            except (TypeError, ValueError):
                hbu["incremental_income_estimate"] = None

        if "status" in body and body["status"] in _VALID_STATUSES:
            hbu["status"] = body["status"]
        else:
            hbu["status"] = "draft"

        completed, blockers = _validate_hbu(hbu)
        hbu["completed"] = completed
        hbu["blockers"]  = blockers
        hbu["reviewed_at"] = datetime.utcnow().isoformat() + "Z"
        hbu["production_ready"]            = False
        hbu["approved_for_certification"]  = False
        hbu["certified_use_allowed"]       = False

        rec["updated_at"] = datetime.utcnow().isoformat() + "Z"
        _recompute_summary(rec)
        _save_advanced_review(rec)
        _append_event(request_id, "hbu_save", "hbu", {"completed": completed, "blockers": blockers})

        return jsonify({
            "ok":            True,
            "hbu_review":    _safe_section(hbu),
            "advanced_review_summary":      rec["advanced_review_summary"],
            "certification_gate_fragment":  rec["certification_gate_fragment"],
            "no_ocr_qdrant_rag":            True,
            "certified_use_allowed":        False,
            "certification_ready":          False,
        }), 200

    # ── POST Legal review ─────────────────────────────────────────────────────

    @app.route(
        "/api/professional-valuation/requests/<request_id>/advanced-review/legal",
        methods=["POST"],
    )
    @require_auth
    def pv_save_legal_review(request_id: str):
        if not _PVR_ID_RE.match(request_id):
            return jsonify({"ok": False, "error": "request_id غير صالح"}), 400
        body  = freq.get_json(silent=True) or {}
        rec   = _load_advanced_review(request_id)
        legal = rec["legal_due_diligence_review"]

        _str_fields = [
            "ownership_type", "ownership_document_evidence_id",
            "title_restrictions", "mortgage_or_lien_status",
            "legal_dispute_status", "last_transfer_date",
            "zoning_or_planning_restrictions", "legal_conclusion",
            "expert_notes", "legal_scope_limitation",
        ]
        for f in _str_fields:
            if f in body:
                legal[f] = str(body[f] or "")[:5000]

        if "ownership_document_reviewed" in body:
            legal["ownership_document_reviewed"] = bool(body["ownership_document_reviewed"])
        if "permits_reviewed" in body:
            legal["permits_reviewed"] = bool(body["permits_reviewed"])
        if "missing_legal_documents" in body:
            legal["missing_legal_documents"] = [str(d)[:500] for d in (body["missing_legal_documents"] or [])[:30]]
        if "evidence_ids_used" in body:
            legal["evidence_ids_used"] = [str(i)[:100] for i in (body["evidence_ids_used"] or [])[:50]]
        if "source_ids_used" in body:
            legal["source_ids_used"] = [str(i)[:100] for i in (body["source_ids_used"] or [])[:50]]

        if "status" in body and body["status"] in _VALID_STATUSES:
            legal["status"] = body["status"]
        else:
            legal["status"] = "draft"

        completed, blockers = _validate_legal(legal)
        legal["completed"] = completed
        legal["blockers"]  = blockers
        legal["reviewed_at"] = datetime.utcnow().isoformat() + "Z"
        legal["production_ready"]            = False
        legal["approved_for_certification"]  = False
        legal["certified_use_allowed"]       = False

        # Ensure limitation text is always present
        if not str(legal.get("legal_scope_limitation") or "").strip():
            legal["legal_scope_limitation"] = (
                "لم يتم إجراء فحص قانوني كامل، ويعد ذلك قيداً على نطاق العمل "
                "ولا يمثل التقرير رأياً قانونياً في صحة الملكية."
            )

        rec["updated_at"] = datetime.utcnow().isoformat() + "Z"
        _recompute_summary(rec)
        _save_advanced_review(rec)
        _append_event(request_id, "legal_save", "legal", {"completed": completed, "blockers": blockers})

        return jsonify({
            "ok":             True,
            "legal_due_diligence_review": _safe_section(legal),
            "advanced_review_summary":    rec["advanced_review_summary"],
            "certification_gate_fragment": rec["certification_gate_fragment"],
            "no_legal_opinion":           True,
            "certified_use_allowed":      False,
            "certification_ready":        False,
        }), 200

    # ── POST ESG review ───────────────────────────────────────────────────────

    @app.route(
        "/api/professional-valuation/requests/<request_id>/advanced-review/esg",
        methods=["POST"],
    )
    @require_auth
    def pv_save_esg_review(request_id: str):
        if not _PVR_ID_RE.match(request_id):
            return jsonify({"ok": False, "error": "request_id غير صالح"}), 400
        body = freq.get_json(silent=True) or {}
        rec  = _load_advanced_review(request_id)
        esg  = rec["esg_climate_review"]

        _str_fields = [
            "esg_category", "energy_efficiency_notes", "water_efficiency_notes",
            "accessibility_notes", "climate_risk_category",
            "flood_heat_or_environmental_risks", "insurance_cost_impact",
            "cap_rate_adjustment_basis", "discount_rate_adjustment_basis",
            "terminal_value_adjustment_basis", "esg_value_impact_commentary",
            "expert_notes",
        ]
        for f in _str_fields:
            if f in body:
                esg[f] = str(body[f] or "")[:5000]

        if "esg_data_available" in body:
            esg["esg_data_available"] = bool(body["esg_data_available"])
        for score_field in ("esg_score", "climate_risk_score"):
            if score_field in body:
                try:
                    esg[score_field] = float(body[score_field])
                except (TypeError, ValueError):
                    esg[score_field] = None
        if "evidence_ids_used" in body:
            esg["evidence_ids_used"] = [str(i)[:100] for i in (body["evidence_ids_used"] or [])[:50]]
        if "source_ids_used" in body:
            esg["source_ids_used"] = [str(i)[:100] for i in (body["source_ids_used"] or [])[:50]]

        if "status" in body and body["status"] in _VALID_STATUSES:
            esg["status"] = body["status"]
        else:
            esg["status"] = "draft"

        completed, blockers = _validate_esg(esg)
        esg["completed"] = completed
        esg["blockers"]  = blockers
        esg["reviewed_at"] = datetime.utcnow().isoformat() + "Z"
        esg["production_ready"]           = False
        esg["approved_for_certification"] = False
        esg["certified_use_allowed"]      = False
        # ESG value impact is never applied automatically
        esg["no_automatic_value_impact"]  = True

        rec["updated_at"] = datetime.utcnow().isoformat() + "Z"
        _recompute_summary(rec)
        _save_advanced_review(rec)
        _append_event(request_id, "esg_save", "esg", {"completed": completed, "blockers": blockers})

        return jsonify({
            "ok":                True,
            "esg_climate_review": _safe_section(esg),
            "advanced_review_summary":      rec["advanced_review_summary"],
            "certification_gate_fragment":  rec["certification_gate_fragment"],
            "no_automatic_value_impact":    True,
            "certified_use_allowed":        False,
            "certification_ready":          False,
        }), 200

    # ── POST SWOT review ──────────────────────────────────────────────────────

    @app.route(
        "/api/professional-valuation/requests/<request_id>/advanced-review/swot",
        methods=["POST"],
    )
    @require_auth
    def pv_save_swot_review(request_id: str):
        if not _PVR_ID_RE.match(request_id):
            return jsonify({"ok": False, "error": "request_id غير صالح"}), 400
        body = freq.get_json(silent=True) or {}
        rec  = _load_advanced_review(request_id)
        swot = rec["swot_risk_review"]

        for cat in ("strengths", "weaknesses", "opportunities", "threats"):
            if cat in body:
                items = body[cat] if isinstance(body[cat], list) else []
                swot[cat] = [_build_swot_item(it) for it in items[:50]]

        _str_fields = [
            "highest_risk", "highest_opportunity", "hbu_linkage",
            "dcf_linkage", "uncertainty_linkage", "recommendation_linkage",
            "expert_notes",
        ]
        for f in _str_fields:
            if f in body:
                swot[f] = str(body[f] or "")[:5000]

        if "evidence_ids_used" in body:
            swot["evidence_ids_used"] = [str(i)[:100] for i in (body["evidence_ids_used"] or [])[:50]]
        if "source_ids_used" in body:
            swot["source_ids_used"] = [str(i)[:100] for i in (body["source_ids_used"] or [])[:50]]

        if "status" in body and body["status"] in _VALID_STATUSES:
            swot["status"] = body["status"]
        else:
            swot["status"] = "draft"

        # Build weighted priority matrix
        all_items = (
            swot["strengths"] + swot["weaknesses"]
            + swot["opportunities"] + swot["threats"]
        )
        swot["weighted_priority_matrix"] = sorted(
            [{"category": it["category"], "title_ar": it["title_ar"], "priority_score": it["priority_score"]}
             for it in all_items],
            key=lambda x: -x["priority_score"],
        )

        completed, blockers = _validate_swot(swot)
        swot["completed"] = completed
        swot["blockers"]  = blockers
        swot["reviewed_at"] = datetime.utcnow().isoformat() + "Z"
        swot["production_ready"]           = False
        swot["approved_for_certification"] = False
        swot["certified_use_allowed"]      = False

        rec["updated_at"] = datetime.utcnow().isoformat() + "Z"
        _recompute_summary(rec)
        _save_advanced_review(rec)
        _append_event(request_id, "swot_save", "swot", {"completed": completed, "blockers": blockers})

        return jsonify({
            "ok":              True,
            "swot_risk_review": _safe_section(swot),
            "advanced_review_summary":      rec["advanced_review_summary"],
            "certification_gate_fragment":  rec["certification_gate_fragment"],
            "certified_use_allowed":        False,
            "certification_ready":          False,
        }), 200

    # ── POST approve-preliminary ──────────────────────────────────────────────

    @app.route(
        "/api/professional-valuation/requests/<request_id>/advanced-review/<section_key>/approve-preliminary",
        methods=["POST"],
    )
    @require_auth
    def pv_approve_advanced_section_preliminary(request_id: str, section_key: str):
        if not _PVR_ID_RE.match(request_id):
            return jsonify({"ok": False, "error": "request_id غير صالح"}), 400
        if section_key not in _VALID_SECTIONS:
            return jsonify({"ok": False, "error": f"section_key غير صالح: {section_key}"}), 400

        rec = _load_advanced_review(request_id)
        section_map = {
            "hbu":   "hbu_review",
            "legal": "legal_due_diligence_review",
            "esg":   "esg_climate_review",
            "swot":  "swot_risk_review",
        }
        section = rec[section_map[section_key]]

        if not section.get("completed", False):
            return jsonify({
                "ok":     False,
                "error":  "القسم غير مكتمل — استكمل المراجعة أولاً.",
                "blockers": section.get("blockers", []),
            }), 422

        now = datetime.utcnow().isoformat() + "Z"
        section["approved_for_preliminary"]  = True
        section["approved_for_certification"] = False
        section["certified_use_allowed"]      = False
        section["status"]                     = "approved_for_preliminary"
        section["reviewed_at"]                = now
        rec["updated_at"] = now

        _recompute_summary(rec)
        _save_advanced_review(rec)
        _append_event(request_id, f"{section_key}_approve_preliminary", section_key,
                      {"approved_for_preliminary": True, "approved_for_certification": False})

        return jsonify({
            "ok":                        True,
            "section_key":               section_key,
            "approved_for_preliminary":  True,
            "approved_for_certification": False,
            "certified_use_allowed":     False,
            "certification_ready":       False,
            "advanced_review_summary":   rec["advanced_review_summary"],
            "certification_gate_fragment": rec["certification_gate_fragment"],
            "warning_text": (
                "تم الاعتماد المبدئي الداخلي — "
                "غير صالح للاستخدام الرسمي أو الاعتماد النهائي في المرحلة الحالية."
            ),
        }), 200

    # ── POST reject ───────────────────────────────────────────────────────────

    @app.route(
        "/api/professional-valuation/requests/<request_id>/advanced-review/<section_key>/reject",
        methods=["POST"],
    )
    @require_auth
    def pv_reject_advanced_section(request_id: str, section_key: str):
        if not _PVR_ID_RE.match(request_id):
            return jsonify({"ok": False, "error": "request_id غير صالح"}), 400
        if section_key not in _VALID_SECTIONS:
            return jsonify({"ok": False, "error": f"section_key غير صالح: {section_key}"}), 400

        body = freq.get_json(silent=True) or {}
        rejection_reason = str(body.get("rejection_reason") or "").strip()
        if not rejection_reason:
            return jsonify({"ok": False, "error": "rejection_reason مطلوب"}), 422

        rec = _load_advanced_review(request_id)
        section_map = {
            "hbu":   "hbu_review",
            "legal": "legal_due_diligence_review",
            "esg":   "esg_climate_review",
            "swot":  "swot_risk_review",
        }
        section = rec[section_map[section_key]]
        section["status"]                    = "rejected"
        section["approved_for_preliminary"]  = False
        section["approved_for_certification"] = False
        section["certified_use_allowed"]     = False
        section["blockers"].append(f"مرفوض: {rejection_reason[:1000]}")
        rec["updated_at"] = datetime.utcnow().isoformat() + "Z"

        _recompute_summary(rec)
        _save_advanced_review(rec)
        _append_event(request_id, f"{section_key}_reject", section_key,
                      {"rejection_reason": rejection_reason})

        return jsonify({
            "ok":          True,
            "section_key": section_key,
            "status":      "rejected",
            "approved_for_preliminary":  False,
            "approved_for_certification": False,
            "advanced_review_summary":  rec["advanced_review_summary"],
        }), 200
