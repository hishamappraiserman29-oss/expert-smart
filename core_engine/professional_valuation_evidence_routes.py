"""
professional_valuation_evidence_routes.py — Evidence Upload & Source Registry for
Professional Valuation Backoffice (Phase C).

Endpoints (all JWT-protected unless noted):
  GET  /api/professional-valuation/evidence/types                          — evidence type catalogue
  GET  /api/professional-valuation/source/types                            — source type catalogue
  POST /api/professional-valuation/requests/<id>/evidence                  — register evidence
  GET  /api/professional-valuation/requests/<id>/evidence                  — list evidence
  GET  /api/professional-valuation/requests/<id>/evidence/<ev_id>          — detail
  POST /api/professional-valuation/requests/<id>/evidence/<ev_id>/review   — review/status change
  POST /api/professional-valuation/requests/<id>/sources                   — add source
  GET  /api/professional-valuation/requests/<id>/sources                   — list sources
  GET  /api/professional-valuation/requests/<id>/sources/<src_id>          — detail
  POST /api/professional-valuation/requests/<id>/sources/<src_id>/review   — review/status change

Storage (internal paths never exposed in API responses):
  core_engine/instance/professional_valuation/evidence/<request_id>.jsonl
  core_engine/instance/professional_valuation/sources/<request_id>.jsonl
  core_engine/instance/professional_valuation/evidence_files/<request_id>/<ev_id>_<safe_name>

Phase C scope: evidence, source registry, document completeness gate, source quality gate.
  - No OCR, no Qdrant, no RAG, no external APIs, no automatic value extraction.
  - production_ready defaults to False.
  - certification_ready always False in Phase C.
"""
from __future__ import annotations

import json
import mimetypes
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── Storage paths ─────────────────────────────────────────────────────────────

_BASE          = Path(__file__).parent / "instance" / "professional_valuation"
_EVIDENCE_DIR  = _BASE / "evidence"
_SOURCES_DIR   = _BASE / "sources"
_FILES_DIR     = _BASE / "evidence_files"

for _d in (_EVIDENCE_DIR, _SOURCES_DIR, _FILES_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── ID format validators ──────────────────────────────────────────────────────

_PVR_ID_RE = re.compile(r"^PVR-\d{8}-[0-9A-F]{4,8}$")
_PVE_ID_RE = re.compile(r"^PVE-[0-9A-F]{8}$")
_PVS_ID_RE = re.compile(r"^PVS-[0-9A-F]{8}$")

# ── File safety ───────────────────────────────────────────────────────────────

_MAX_FILE_BYTES = 20 * 1024 * 1024   # 20 MB

_ALLOWED_EXTENSIONS: frozenset[str] = frozenset({
    ".pdf", ".xlsx", ".xls", ".csv",
    ".jpg", ".jpeg", ".png", ".webp",
    ".txt", ".docx",
})

_BLOCKED_EXTENSIONS: frozenset[str] = frozenset({
    ".exe", ".bat", ".cmd", ".ps1",
    ".js", ".html", ".php", ".sh",
    ".zip", ".tar", ".gz", ".7z", ".rar",
})

# ── Evidence type catalogue ───────────────────────────────────────────────────

PV_EVIDENCE_TYPES: dict[str, str] = {
    # Core property / legal
    "ownership_document":           "وثيقة الملكية",
    "area_statement":               "بيان المساحة",
    "building_permit":              "ترخيص البناء",
    "completion_certificate":       "شهادة الإنهاء",
    "occupancy_certificate":        "شهادة الإشغال",
    "inspection_photos":            "صور المعاينة",
    "location_map":                 "خريطة الموقع",
    "gps_coordinates_document":     "وثيقة إحداثيات GPS",
    "legal_due_diligence_note":     "ملاحظة الفحص القانوني",
    "lease_contract":               "عقد الإيجار",
    # Market / source evidence
    "sales_comparable_document":    "مستند مقارن بيعي",
    "rental_comparable_document":   "مستند مقارن إيجاري",
    "land_price_reference":         "مرجع سعر الأرض",
    "cap_rate_reference":           "مرجع معدل الرسملة",
    "discount_rate_reference":      "مرجع معدل الخصم",
    "market_research_note":         "ملاحظة بحث سوقي",
    "comparable_excel":             "ملف Excel للمقارنات",
    "cost_reference":               "مرجع التكلفة",
    "construction_cost_reference":  "مرجع تكاليف البناء",
    # Governance
    "expert_note":                  "ملاحظة خبير",
    "peer_review_note":             "ملاحظة مراجعة النظراء",
    "signature_document":           "مستند التوقيع",
    "company_stamp":                "ختم الشركة",
    "other":                        "أخرى",
}

# Source-eligible evidence types (can be promoted to approved_as_source)
_SOURCE_ELIGIBLE_TYPES: frozenset[str] = frozenset({
    "sales_comparable_document", "rental_comparable_document",
    "land_price_reference", "cap_rate_reference", "discount_rate_reference",
    "market_research_note", "comparable_excel", "cost_reference",
    "construction_cost_reference", "lease_contract",
})

# ── Evidence status lifecycle ─────────────────────────────────────────────────

_EV_VALID_STATUSES: frozenset[str] = frozenset({
    "uploaded", "under_review", "approved_for_report",
    "approved_as_source", "rejected", "superseded",
})

_EV_TRANSITIONS: dict[str, frozenset[str]] = {
    "uploaded":            frozenset({"under_review", "approved_for_report", "rejected"}),
    "under_review":        frozenset({"approved_for_report", "approved_as_source", "rejected"}),
    "approved_for_report": frozenset({"approved_as_source", "rejected"}),
    "approved_as_source":  frozenset({"superseded"}),
    "rejected":            frozenset({"under_review"}),
    "superseded":          frozenset(),
}

# ── Source type catalogue ─────────────────────────────────────────────────────

PV_SOURCE_TYPES: dict[str, str] = {
    "sales_comparable":           "مقارن بيعي",
    "rental_comparable":          "مقارن إيجاري",
    "land_price_reference":       "مرجع سعر الأرض",
    "cap_rate_reference":         "مرجع معدل الرسملة",
    "discount_rate_reference":    "مرجع معدل الخصم",
    "construction_cost_reference": "مرجع تكاليف البناء",
    "legal_reference":            "مرجع قانوني",
    "market_research":            "بحث سوقي",
    "expert_manual_entry":        "إدخال خبير يدوي",
    "uploaded_document_source":   "مصدر من مستند مرفق",
    "qa_simulation_source":       "مصدر محاكاة QA (لأغراض الاختبار فقط)",
}

# ── Source status lifecycle ───────────────────────────────────────────────────

_SRC_VALID_STATUSES: frozenset[str] = frozenset({
    "draft", "submitted", "under_review",
    "approved_for_analysis", "approved_as_production_source",
    "rejected", "superseded",
})

_SRC_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft":                       frozenset({"submitted"}),
    "submitted":                   frozenset({"under_review"}),
    "under_review":                frozenset({"approved_for_analysis", "rejected"}),
    "approved_for_analysis":       frozenset({"approved_as_production_source", "rejected"}),
    "approved_as_production_source": frozenset({"superseded"}),
    "rejected":                    frozenset({"under_review"}),
    "superseded":                  frozenset(),
}

# ── Document completeness evaluation ──────────────────────────────────────────

_COMMON_REQUIRED_DOCS: list[str] = [
    "ownership_document",
    "area_statement",
    "inspection_photos",
    "location_map",
]

# OR-groups: at least one from each inner list is required for the given purpose keyword
_PURPOSE_EXTRA_DOCS: dict[str, list[list[str]]] = {
    "income":     [["lease_contract", "rental_comparable_document"]],
    "rental":     [["lease_contract", "rental_comparable_document"]],
    "إيجار":      [["lease_contract", "rental_comparable_document"]],
    "market":     [["sales_comparable_document", "comparable_excel"]],
    "sales":      [["sales_comparable_document", "comparable_excel"]],
    "سوقي":       [["sales_comparable_document", "comparable_excel"]],
    "سوقية":      [["sales_comparable_document", "comparable_excel"]],
    "بيع":        [["sales_comparable_document", "comparable_excel"]],
    "cost":       [["building_permit", "completion_certificate"],
                   ["cost_reference", "construction_cost_reference"]],
    "تكلف":       [["building_permit", "completion_certificate"],
                   ["cost_reference", "construction_cost_reference"]],
    "financing":  [["legal_due_diligence_note"]],
    "court":      [["legal_due_diligence_note"]],
    "تمويل":      [["legal_due_diligence_note"]],
    "محكم":       [["legal_due_diligence_note"]],
}

_ACTIVE_EV_STATUSES: frozenset[str] = frozenset({
    "uploaded", "under_review", "approved_for_report", "approved_as_source",
})


def evaluate_document_completeness(request_id: str, valuation_purpose: str) -> dict:
    """Compute document completeness gate for the request."""
    evidence_list = _load_evidence(request_id)
    active_types: set[str] = {
        ev["evidence_type"]
        for ev in evidence_list
        if ev.get("status") in _ACTIVE_EV_STATUSES
    }
    approved_types: set[str] = {
        ev["evidence_type"]
        for ev in evidence_list
        if ev.get("status") in ("approved_for_report", "approved_as_source")
    }

    # Determine required documents for this purpose
    purpose_lower = (valuation_purpose or "").lower()
    required_groups: list[list[str]] = [
        [d] for d in _COMMON_REQUIRED_DOCS
    ]
    for keyword, groups in _PURPOSE_EXTRA_DOCS.items():
        if keyword.lower() in purpose_lower:
            required_groups.extend(groups)

    # Evaluate completeness
    missing_blocking: list[str] = []
    submitted_doc_types: list[str] = sorted(active_types)
    approved_doc_types: list[str] = sorted(approved_types)

    for group in required_groups:
        if not any(t in active_types for t in group):
            missing_blocking.append(" أو ".join(group))

    total_required = len(required_groups)
    total_satisfied = total_required - len(missing_blocking)

    score = int(round((total_satisfied / max(total_required, 1)) * 100))
    if score >= 100:
        completeness_level = "complete"
    elif score >= 60:
        completeness_level = "partial"
    elif score >= 30:
        completeness_level = "low"
    else:
        completeness_level = "missing"

    certification_document_ready = len(missing_blocking) == 0

    return {
        "score":                        score,
        "required_documents":           [g[0] if len(g) == 1 else g for g in required_groups],
        "submitted_documents":          submitted_doc_types,
        "approved_documents":           approved_doc_types,
        "missing_required_documents":   missing_blocking,
        "missing_supporting_documents": [],
        "blocking_missing_documents":   missing_blocking,
        "completeness_level":           completeness_level,
        "certification_document_ready": certification_document_ready,
        "advisory_only_reason": (
            "Phase C — certification requires expert signature, peer review, and source approval."
        ),
        "required_actions": (
            [f"أضف: {m}" for m in missing_blocking]
            if missing_blocking else
            ["تم تقديم المستندات الإلزامية — يلزم مراجعة الخبير"]
        ),
    }


# ── Source quality evaluation ─────────────────────────────────────────────────

_REQUIRED_SOURCE_CATEGORIES: dict[str, list[str]] = {
    "market":    ["sales_comparable", "land_price_reference"],
    "سوقي":      ["sales_comparable", "land_price_reference"],
    "سوقية":     ["sales_comparable", "land_price_reference"],
    "rental":    ["rental_comparable", "cap_rate_reference"],
    "income":    ["rental_comparable", "cap_rate_reference"],
    "إيجار":     ["rental_comparable", "cap_rate_reference"],
    "financing": ["sales_comparable", "legal_reference", "land_price_reference"],
    "تمويل":     ["sales_comparable", "legal_reference", "land_price_reference"],
    "investment": ["rental_comparable", "discount_rate_reference", "cap_rate_reference"],
    "court":     ["legal_reference", "sales_comparable"],
    "محكم":      ["legal_reference", "sales_comparable"],
}


def evaluate_source_quality(request_id: str, valuation_purpose: str) -> dict:
    """Compute source quality gate for the request."""
    source_list = _load_sources(request_id)

    total_sources = len(source_list)
    production_ready_sources = sum(
        1 for s in source_list if s.get("production_ready") is True
    )
    qa_sources = sum(
        1 for s in source_list if s.get("qa_simulation") is True
    )
    approved_for_analysis_sources = sum(
        1 for s in source_list
        if s.get("source_status") in ("approved_for_analysis", "approved_as_production_source")
    )

    # Determine required source categories for this purpose
    purpose_lower = (valuation_purpose or "").lower()
    required_cats: list[str] = []
    for keyword, cats in _REQUIRED_SOURCE_CATEGORIES.items():
        if keyword.lower() in purpose_lower:
            required_cats = cats
            break

    present_types: set[str] = {s.get("source_type", "") for s in source_list}
    missing_categories: list[str] = [
        cat for cat in required_cats if cat not in present_types
    ]

    # Certification source ready rules
    has_real_production = production_ready_sources > 0 and (
        total_sources - qa_sources > 0
    )
    all_qa = total_sources > 0 and qa_sources == total_sources
    certification_source_ready = (
        has_real_production
        and not all_qa
        and len(missing_categories) == 0
    )

    if certification_source_ready:
        source_quality_status = "ready"
    elif total_sources == 0:
        source_quality_status = "not_started"
    elif production_ready_sources == 0:
        source_quality_status = "no_production_sources"
    elif all_qa:
        source_quality_status = "qa_only"
    elif missing_categories:
        source_quality_status = "missing_categories"
    else:
        source_quality_status = "pending_approval"

    return {
        "source_quality_status":          source_quality_status,
        "total_sources":                  total_sources,
        "production_ready_sources":       production_ready_sources,
        "qa_sources":                     qa_sources,
        "approved_for_analysis_sources":  approved_for_analysis_sources,
        "missing_source_categories":      missing_categories,
        "required_source_categories":     required_cats,
        "real_sources_ready":             has_real_production and not all_qa,
        "certification_source_ready":     certification_source_ready,
        "advisory_only_reason": (
            "مصادر البيانات غير مكتملة أو غير معتمدة للإنتاج."
            if not certification_source_ready else
            "مصادر جاهزة — يلزم استكمال بوابات الاعتماد الأخرى."
        ),
        "required_actions": (
            [f"أضف مصدر: {c}" for c in missing_categories]
            + (["يلزم مصدر إنتاج واحد على الأقل معتمد"] if not has_real_production else [])
            + (["جميع المصادر محاكاة QA — لا تصلح للإنتاج"] if all_qa else [])
        ) or ["المصادر جاهزة — استكمل بوابات الاعتماد الأخرى"],
    }


# ── Certification gate (Phase C) ──────────────────────────────────────────────

def compute_gate_summary(request_id: str, valuation_purpose: str = "") -> dict:
    """Compute certification gate summary from current evidence + source state.
    Phase C: certification_ready always False.
    """
    doc_status   = evaluate_document_completeness(request_id, valuation_purpose)
    src_status   = evaluate_source_quality(request_id, valuation_purpose)

    mandatory_docs_ready = doc_status["certification_document_ready"]
    real_sources_ready   = src_status["real_sources_ready"]

    blockers: list[str] = []
    if doc_status["missing_required_documents"]:
        blockers.append(
            "مستندات إلزامية ناقصة: " + "، ".join(doc_status["missing_required_documents"])
        )
    if not real_sources_ready:
        blockers.append("لا توجد مصادر إنتاج معتمدة — " + src_status["advisory_only_reason"])
    if src_status["qa_sources"] > 0:
        blockers.append("مصادر QA نشطة — يجب استبدالها بمصادر سوق حقيقية")
    blockers.append("مراجعة النظراء — لم تُنفَّذ بعد (مرحلة لاحقة)")
    blockers.append("توقيع الخبير — لم يُنفَّذ بعد (مرحلة لاحقة)")
    blockers.append("إصدار التقرير المعتمد — محظور في المرحلة ج")

    return {
        "certification_ready":       False,
        "qa_data_cleared":           src_status["qa_sources"] == 0 and src_status["total_sources"] > 0,
        "real_sources_ready":        real_sources_ready,
        "mandatory_documents_ready": mandatory_docs_ready,
        "legal_due_diligence_ready": False,
        "hbu_completed":             False,
        "methods_completed":         False,
        "reconciliation_completed":  False,
        "peer_review_completed":     False,
        "expert_signature_ready":    False,
        "blockers":                  blockers,
        "advisory_only_reason": (
            "Phase C — evidence and source readiness only. "
            "Certified report generation is a later phase."
        ),
    }


# ── ID generators ─────────────────────────────────────────────────────────────

def _new_pve_id() -> str:
    return "PVE-" + uuid.uuid4().hex[:8].upper()


def _new_pvs_id() -> str:
    return "PVS-" + uuid.uuid4().hex[:8].upper()


# ── Evidence persistence helpers ──────────────────────────────────────────────

def _ev_file(request_id: str) -> Path:
    return _EVIDENCE_DIR / f"{request_id}.jsonl"


def _persist_ev(request_id: str, rec: dict) -> None:
    with open(_ev_file(request_id), "a", encoding="utf-8") as fh:
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


def _load_evidence(request_id: str) -> list[dict]:
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


def _ev_safe(rec: dict) -> dict:
    """Public-safe evidence metadata — never includes internal_file_path."""
    return {
        "evidence_id":                  rec.get("evidence_id"),
        "request_id":                   rec.get("request_id"),
        "uploaded_at":                  rec.get("uploaded_at"),
        "uploaded_by":                  rec.get("uploaded_by"),
        "original_filename":            rec.get("original_filename"),
        "file_ext":                     rec.get("file_ext"),
        "mime_type":                    rec.get("mime_type"),
        "file_size_bytes":              rec.get("file_size_bytes"),
        "evidence_type":                rec.get("evidence_type"),
        "evidence_label_ar":            rec.get("evidence_label_ar"),
        "document_category":            rec.get("document_category"),
        "related_method":               rec.get("related_method"),
        "status":                       rec.get("status"),
        "review_status":                rec.get("review_status"),
        "source_use_status":            rec.get("source_use_status"),
        "production_ready":             rec.get("production_ready", False),
        "ordinary_visible":             rec.get("ordinary_visible", False),
        "expert_only":                  rec.get("expert_only", False),
        "is_required_document":         rec.get("is_required_document", False),
        "satisfies_document_requirement": rec.get("satisfies_document_requirement", False),
        "linked_source_ids":            rec.get("linked_source_ids", []),
        "rejection_reason":             rec.get("rejection_reason"),
        "superseded_by":                rec.get("superseded_by"),
        "no_automatic_value_extraction": rec.get("no_automatic_value_extraction", True),
        "external_api_used":            rec.get("external_api_used", False),
        "qdrant_used":                  rec.get("qdrant_used", False),
        "rag_used":                     rec.get("rag_used", False),
        "has_file":                     rec.get("has_file", False),
    }


def _ev_safe_with_expert_notes(rec: dict) -> dict:
    """Evidence metadata including expert_notes — for backoffice use only."""
    d = _ev_safe(rec)
    d["expert_notes"] = rec.get("expert_notes")
    return d


# ── Source persistence helpers ────────────────────────────────────────────────

def _src_file(request_id: str) -> Path:
    return _SOURCES_DIR / f"{request_id}.jsonl"


def _persist_src(request_id: str, rec: dict) -> None:
    with open(_src_file(request_id), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _update_src(request_id: str, source_id: str, updates: dict) -> None:
    f = _src_file(request_id)
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
                if rec.get("source_id") == source_id:
                    rec.update(updates)
                lines.append(json.dumps(rec, ensure_ascii=False))
            except json.JSONDecodeError:
                lines.append(raw)
    with open(f, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def _read_src(request_id: str, source_id: str) -> Optional[dict]:
    f = _src_file(request_id)
    if not f.exists():
        return None
    with open(f, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
                if rec.get("source_id") == source_id:
                    return rec
            except json.JSONDecodeError:
                continue
    return None


def _load_sources(request_id: str) -> list[dict]:
    f = _src_file(request_id)
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


def _src_safe(rec: dict) -> dict:
    """Public-safe source metadata."""
    return {
        "source_id":             rec.get("source_id"),
        "request_id":            rec.get("request_id"),
        "created_at":            rec.get("created_at"),
        "created_by":            rec.get("created_by"),
        "source_type":           rec.get("source_type"),
        "source_category":       rec.get("source_category"),
        "source_name":           rec.get("source_name"),
        "source_description":    rec.get("source_description"),
        "related_evidence_id":   rec.get("related_evidence_id"),
        "related_method":        rec.get("related_method"),
        "location":              rec.get("location"),
        "district":              rec.get("district"),
        "property_type":         rec.get("property_type"),
        "transaction_date":      rec.get("transaction_date"),
        "value_type":            rec.get("value_type"),
        "value_amount":          rec.get("value_amount"),
        "unit":                  rec.get("unit"),
        "area_m2":               rec.get("area_m2"),
        "value_per_m2":          rec.get("value_per_m2"),
        "source_status":         rec.get("source_status"),
        "expert_review_status":  rec.get("expert_review_status"),
        "production_ready":      rec.get("production_ready", False),
        "approved_by":           rec.get("approved_by"),
        "approved_at":           rec.get("approved_at"),
        "rejection_reason":      rec.get("rejection_reason"),
        "limitations":           rec.get("limitations"),
        "qa_simulation":         rec.get("qa_simulation", False),
        "external_api_used":     rec.get("external_api_used", False),
        "qdrant_used":           rec.get("qdrant_used", False),
        "rag_used":              rec.get("rag_used", False),
    }


# ── File safety helpers ───────────────────────────────────────────────────────

def _sanitize_filename(name: str) -> str:
    name = os.path.basename(name)
    name = name.replace("..", "")
    safe = "".join(c for c in name if c.isalnum() or c in "._- ")
    return safe.strip() or "upload"


# ── Events (shared with main routes module) ───────────────────────────────────

def _append_ev_event(request_id: str, actor: str, action: str, metadata: dict) -> None:
    """Append an event to the shared events.jsonl using the same format as Phase B."""
    from professional_valuation_routes import _append_event as _pv_append_event
    _pv_append_event(
        request_id=request_id,
        actor=actor,
        action=action,
        from_status="",
        to_status="",
        note=metadata.get("note", ""),
        metadata={k: v for k, v in metadata.items() if k != "note"},
    )


# ── Route registration ────────────────────────────────────────────────────────

def register_pv_evidence_routes(app, require_auth, limiter=None) -> None:
    """Register all Phase C evidence + source routes on *app*."""
    from flask import g, jsonify, request as flask_request
    from professional_valuation_routes import _read_pvr, _update_pvr, _PVR_ID_RE as _PVR_RE

    # ── GET /api/professional-valuation/evidence/types ─────────────────────
    @app.route("/api/professional-valuation/evidence/types", methods=["GET"])
    @require_auth
    def pv_evidence_types():
        return jsonify({
            "ok":             True,
            "evidence_types": [
                {"key": k, "label_ar": v}
                for k, v in PV_EVIDENCE_TYPES.items()
            ],
            "source_eligible_types": sorted(_SOURCE_ELIGIBLE_TYPES),
        }), 200

    # ── GET /api/professional-valuation/source/types ───────────────────────
    @app.route("/api/professional-valuation/source/types", methods=["GET"])
    @require_auth
    def pv_source_types():
        return jsonify({
            "ok":          True,
            "source_types": [
                {"key": k, "label_ar": v}
                for k, v in PV_SOURCE_TYPES.items()
            ],
        }), 200

    # ── POST /api/professional-valuation/requests/<id>/evidence ───────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/evidence",
        methods=["POST"],
    )
    @require_auth
    def pv_create_evidence(request_id: str):
        if not _PVR_RE.match(request_id):
            return jsonify({"ok": False, "error": "رقم الطلب غير صالح"}), 400
        rec = _read_pvr(request_id)
        if rec is None:
            return jsonify({"ok": False, "error": "الطلب غير موجود"}), 404

        now     = datetime.utcnow().isoformat()
        user_id = getattr(g, "user_id", None) or "system"

        # Support both multipart file upload and JSON metadata-only
        file_obj = flask_request.files.get("file") if flask_request.files else None
        if file_obj and file_obj.filename:
            # Multipart file upload
            orig_name = _sanitize_filename(file_obj.filename)
            ext       = Path(orig_name).suffix.lower()
            if ext in _BLOCKED_EXTENSIONS:
                return jsonify({"ok": False, "error": f"صيغة الملف محظورة: {ext}"}), 400
            if ext not in _ALLOWED_EXTENSIONS:
                return jsonify({"ok": False, "error": f"صيغة الملف غير مدعومة: {ext}"}), 400
            data = file_obj.read()
            if len(data) == 0:
                return jsonify({"ok": False, "error": "الملف فارغ"}), 400
            if len(data) > _MAX_FILE_BYTES:
                return jsonify({"ok": False, "error": "حجم الملف يتجاوز 20 ميجابايت"}), 400
            mime       = mimetypes.guess_type(orig_name)[0] or "application/octet-stream"
            ev_id      = _new_pve_id()
            safe_name  = ev_id + ext
            dest_dir   = _FILES_DIR / request_id
            dest_dir.mkdir(parents=True, exist_ok=True)
            (dest_dir / safe_name).write_bytes(data)
            has_file        = True
            file_size_bytes = len(data)
            evidence_type   = flask_request.form.get("evidence_type", "other")
            doc_category    = flask_request.form.get("document_category", "")
            related_method  = flask_request.form.get("related_method", "")
            is_required     = flask_request.form.get("is_required_document", "false").lower() == "true"
            expert_only     = flask_request.form.get("expert_only", "false").lower() == "true"
            expert_notes    = flask_request.form.get("notes", "")
        else:
            # JSON metadata-only registration
            body           = flask_request.get_json(force=True, silent=True) or {}
            orig_name      = (body.get("original_filename") or "").strip() or "metadata-only"
            ext            = Path(orig_name).suffix.lower() if "." in orig_name else ""
            mime           = "application/octet-stream"
            ev_id          = _new_pve_id()
            safe_name      = ev_id + (ext or "")
            has_file       = False
            file_size_bytes = 0
            evidence_type   = (body.get("evidence_type") or "other").strip()
            doc_category    = (body.get("document_category") or "").strip()
            related_method  = (body.get("related_method") or "").strip()
            is_required     = bool(body.get("is_required_document", False))
            expert_only     = bool(body.get("expert_only", False))
            expert_notes    = (body.get("notes") or "").strip()

        if evidence_type not in PV_EVIDENCE_TYPES:
            evidence_type = "other"

        ev_rec: dict = {
            "evidence_id":                    ev_id,
            "request_id":                     request_id,
            "uploaded_at":                    now,
            "uploaded_by":                    user_id,
            "original_filename":              orig_name,
            "safe_filename":                  safe_name,
            "file_ext":                       ext,
            "mime_type":                      mime,
            "file_size_bytes":                file_size_bytes,
            "evidence_type":                  evidence_type,
            "evidence_label_ar":              PV_EVIDENCE_TYPES[evidence_type],
            "document_category":              doc_category,
            "related_method":                 related_method,
            "status":                         "uploaded",
            "review_status":                  "pending_review",
            "source_use_status":              "not_used_as_source",
            "production_ready":               False,
            "ordinary_visible":               False,
            "expert_only":                    expert_only,
            "is_required_document":           is_required,
            "satisfies_document_requirement": False,
            "linked_source_ids":              [],
            "expert_notes":                   expert_notes,
            "rejection_reason":               None,
            "superseded_by":                  None,
            "metadata":                       {},
            "has_file":                       has_file,
            "no_automatic_value_extraction":  True,
            "external_api_used":              False,
            "qdrant_used":                    False,
            "rag_used":                       False,
        }

        _persist_ev(request_id, ev_rec)
        _append_ev_event(request_id, user_id, "evidence_upload", {
            "evidence_id":   ev_id,
            "evidence_type": evidence_type,
            "has_file":      has_file,
        })

        valuation_purpose = rec.get("valuation_purpose", "")
        doc_completeness  = evaluate_document_completeness(request_id, valuation_purpose)
        gate_summary      = compute_gate_summary(request_id, valuation_purpose)

        _update_pvr(request_id, {
            "document_completeness_status": doc_completeness["completeness_level"],
            "missing_required_items":       doc_completeness["missing_required_documents"],
            "certification_gate_summary":   gate_summary,
        })

        return jsonify({
            "ok":                          True,
            "evidence":                    _ev_safe(ev_rec),
            "document_completeness_status": doc_completeness,
            "certification_gate_summary":  gate_summary,
        }), 201

    # ── GET /api/professional-valuation/requests/<id>/evidence ────────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/evidence",
        methods=["GET"],
    )
    @require_auth
    def pv_list_evidence(request_id: str):
        if not _PVR_RE.match(request_id):
            return jsonify({"ok": False, "error": "رقم الطلب غير صالح"}), 400
        if _read_pvr(request_id) is None:
            return jsonify({"ok": False, "error": "الطلب غير موجود"}), 404

        evidence_list = _load_evidence(request_id)
        valuation_purpose = (_read_pvr(request_id) or {}).get("valuation_purpose", "")
        doc_completeness  = evaluate_document_completeness(request_id, valuation_purpose)

        return jsonify({
            "ok":                          True,
            "request_id":                  request_id,
            "evidence_items":              [_ev_safe(e) for e in evidence_list],
            "count":                       len(evidence_list),
            "document_completeness_status": doc_completeness,
            "missing_required_documents":  doc_completeness["missing_required_documents"],
        }), 200

    # ── GET /api/professional-valuation/requests/<id>/evidence/<ev_id> ────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/evidence/<evidence_id>",
        methods=["GET"],
    )
    @require_auth
    def pv_get_evidence(request_id: str, evidence_id: str):
        if not _PVR_RE.match(request_id):
            return jsonify({"ok": False, "error": "رقم الطلب غير صالح"}), 400
        if not _PVE_ID_RE.match(evidence_id):
            return jsonify({"ok": False, "error": "معرّف المستند غير صالح"}), 400
        if _read_pvr(request_id) is None:
            return jsonify({"ok": False, "error": "الطلب غير موجود"}), 404
        ev = _read_ev(request_id, evidence_id)
        if ev is None:
            return jsonify({"ok": False, "error": "المستند غير موجود"}), 404
        return jsonify({"ok": True, "evidence": _ev_safe_with_expert_notes(ev)}), 200

    # ── POST /api/professional-valuation/requests/<id>/evidence/<ev_id>/review
    @app.route(
        "/api/professional-valuation/requests/<request_id>/evidence/<evidence_id>/review",
        methods=["POST"],
    )
    @require_auth
    def pv_review_evidence(request_id: str, evidence_id: str):
        if not _PVR_RE.match(request_id):
            return jsonify({"ok": False, "error": "رقم الطلب غير صالح"}), 400
        if not _PVE_ID_RE.match(evidence_id):
            return jsonify({"ok": False, "error": "معرّف المستند غير صالح"}), 400
        pvr = _read_pvr(request_id)
        if pvr is None:
            return jsonify({"ok": False, "error": "الطلب غير موجود"}), 404
        ev = _read_ev(request_id, evidence_id)
        if ev is None:
            return jsonify({"ok": False, "error": "المستند غير موجود"}), 404

        body       = flask_request.get_json(force=True, silent=True) or {}
        new_status = (body.get("status") or "").strip()
        user_id    = getattr(g, "user_id", None) or "system"

        if new_status and new_status not in _EV_VALID_STATUSES:
            return jsonify({"ok": False, "error": f"حالة غير معروفة: {new_status}"}), 400

        current = ev.get("status", "uploaded")
        if new_status and new_status != current:
            allowed = _EV_TRANSITIONS.get(current, frozenset())
            if new_status not in allowed:
                return jsonify({
                    "ok":    False,
                    "error": f"الانتقال من '{current}' إلى '{new_status}' غير مسموح",
                }), 422

        # approved_as_source requires source-eligible type
        if new_status == "approved_as_source":
            if ev.get("evidence_type") not in _SOURCE_ELIGIBLE_TYPES:
                return jsonify({
                    "ok":    False,
                    "error": "هذا النوع من المستندات غير مؤهل كمصدر معتمد",
                }), 422

        # rejected requires rejection_reason
        if new_status == "rejected":
            if not (body.get("rejection_reason") or ev.get("rejection_reason")):
                return jsonify({
                    "ok":    False,
                    "error": "rejection_reason مطلوب عند الرفض",
                }), 400

        now = datetime.utcnow().isoformat()
        effective = new_status or current

        updates: dict = {
            "updated_at":     now,
            "review_status":  "reviewed",
        }
        if new_status:
            updates["status"] = new_status
        if body.get("expert_notes") is not None:
            updates["expert_notes"] = body["expert_notes"]
        if body.get("rejection_reason") is not None:
            updates["rejection_reason"] = body["rejection_reason"]
        if body.get("ordinary_visible") is not None:
            updates["ordinary_visible"] = bool(body["ordinary_visible"])
        if body.get("source_use_status") is not None:
            updates["source_use_status"] = body["source_use_status"]

        if effective == "approved_as_source":
            updates["production_ready"]               = True
            updates["satisfies_document_requirement"] = True
            updates["source_use_status"]              = "approved_as_source"
        elif effective == "approved_for_report":
            updates["satisfies_document_requirement"] = True
            updates["source_use_status"]              = "approved_for_report"
        elif effective in ("rejected", "superseded"):
            updates["production_ready"]               = False
            updates["satisfies_document_requirement"] = False
            updates["source_use_status"]              = "not_used_as_source"

        _update_ev(request_id, evidence_id, updates)
        updated = _read_ev(request_id, evidence_id)

        valuation_purpose = pvr.get("valuation_purpose", "")
        doc_completeness  = evaluate_document_completeness(request_id, valuation_purpose)
        gate_summary      = compute_gate_summary(request_id, valuation_purpose)
        _update_pvr(request_id, {
            "document_completeness_status": doc_completeness["completeness_level"],
            "missing_required_items":       doc_completeness["missing_required_documents"],
            "certification_gate_summary":   gate_summary,
        })

        _append_ev_event(request_id, user_id, "evidence_review", {
            "evidence_id": evidence_id,
            "new_status":  effective,
        })

        return jsonify({
            "ok":      True,
            "evidence": _ev_safe_with_expert_notes(updated) if updated else None,
            "document_completeness_status": doc_completeness,
        }), 200

    # ── POST /api/professional-valuation/requests/<id>/sources ────────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/sources",
        methods=["POST"],
    )
    @require_auth
    def pv_create_source(request_id: str):
        if not _PVR_RE.match(request_id):
            return jsonify({"ok": False, "error": "رقم الطلب غير صالح"}), 400
        pvr = _read_pvr(request_id)
        if pvr is None:
            return jsonify({"ok": False, "error": "الطلب غير موجود"}), 404

        body    = flask_request.get_json(force=True, silent=True) or {}
        now     = datetime.utcnow().isoformat()
        user_id = getattr(g, "user_id", None) or "system"

        source_type = (body.get("source_type") or "").strip()
        if not source_type:
            return jsonify({"ok": False, "error": "source_type مطلوب"}), 400
        if source_type not in PV_SOURCE_TYPES:
            return jsonify({
                "ok":    False,
                "error": f"نوع المصدر '{source_type}' غير معرّف",
            }), 400

        related_evidence_id = (body.get("related_evidence_id") or "").strip() or None
        if related_evidence_id:
            if not _PVE_ID_RE.match(related_evidence_id):
                return jsonify({"ok": False, "error": "معرّف المستند المرتبط غير صالح"}), 400
            if not _read_ev(request_id, related_evidence_id):
                return jsonify({"ok": False, "error": "المستند المرتبط غير موجود"}), 404

        qa_simulation = bool(body.get("qa_simulation", False))
        src_id        = _new_pvs_id()

        src_rec: dict = {
            "source_id":           src_id,
            "request_id":          request_id,
            "created_at":          now,
            "created_by":          user_id,
            "source_type":         source_type,
            "source_category":     (body.get("source_category") or "").strip(),
            "source_name":         (body.get("source_name") or "").strip(),
            "source_description":  (body.get("source_description") or "").strip(),
            "related_evidence_id": related_evidence_id,
            "related_method":      (body.get("related_method") or "").strip(),
            "location":            (body.get("location") or "").strip(),
            "district":            (body.get("district") or "").strip(),
            "property_type":       (body.get("property_type") or "").strip(),
            "transaction_date":    (body.get("transaction_date") or "").strip(),
            "value_type":          (body.get("value_type") or "").strip(),
            "value_amount":        body.get("value_amount"),
            "unit":                (body.get("unit") or "EGP").strip(),
            "area_m2":             body.get("area_m2"),
            "value_per_m2":        body.get("value_per_m2"),
            "source_status":       "draft",
            "expert_review_status": "pending",
            "production_ready":    False,
            "approved_by":         None,
            "approved_at":         None,
            "rejection_reason":    None,
            "limitations":         (body.get("limitations") or "").strip(),
            "qa_simulation":       qa_simulation,
            "external_api_used":   False,
            "qdrant_used":         False,
            "rag_used":            False,
        }

        _persist_src(request_id, src_rec)
        _append_ev_event(request_id, user_id, "source_create", {
            "source_id":   src_id,
            "source_type": source_type,
            "qa_simulation": qa_simulation,
        })

        valuation_purpose = pvr.get("valuation_purpose", "")
        src_quality  = evaluate_source_quality(request_id, valuation_purpose)
        gate_summary = compute_gate_summary(request_id, valuation_purpose)
        _update_pvr(request_id, {
            "source_quality_status":      src_quality["source_quality_status"],
            "certification_gate_summary": gate_summary,
        })

        return jsonify({
            "ok":                  True,
            "source":              _src_safe(src_rec),
            "source_quality_summary": src_quality,
            "certification_gate_summary": gate_summary,
        }), 201

    # ── GET /api/professional-valuation/requests/<id>/sources ─────────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/sources",
        methods=["GET"],
    )
    @require_auth
    def pv_list_sources(request_id: str):
        if not _PVR_RE.match(request_id):
            return jsonify({"ok": False, "error": "رقم الطلب غير صالح"}), 400
        pvr = _read_pvr(request_id)
        if pvr is None:
            return jsonify({"ok": False, "error": "الطلب غير موجود"}), 404

        sources           = _load_sources(request_id)
        valuation_purpose = pvr.get("valuation_purpose", "")
        src_quality       = evaluate_source_quality(request_id, valuation_purpose)

        return jsonify({
            "ok":                  True,
            "request_id":          request_id,
            "sources":             [_src_safe(s) for s in sources],
            "count":               len(sources),
            "source_quality_summary": src_quality,
        }), 200

    # ── GET /api/professional-valuation/requests/<id>/sources/<src_id> ────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/sources/<source_id>",
        methods=["GET"],
    )
    @require_auth
    def pv_get_source(request_id: str, source_id: str):
        if not _PVR_RE.match(request_id):
            return jsonify({"ok": False, "error": "رقم الطلب غير صالح"}), 400
        if not _PVS_ID_RE.match(source_id):
            return jsonify({"ok": False, "error": "معرّف المصدر غير صالح"}), 400
        if _read_pvr(request_id) is None:
            return jsonify({"ok": False, "error": "الطلب غير موجود"}), 404
        src = _read_src(request_id, source_id)
        if src is None:
            return jsonify({"ok": False, "error": "المصدر غير موجود"}), 404
        return jsonify({"ok": True, "source": _src_safe(src)}), 200

    # ── POST /api/professional-valuation/requests/<id>/sources/<src_id>/review
    @app.route(
        "/api/professional-valuation/requests/<request_id>/sources/<source_id>/review",
        methods=["POST"],
    )
    @require_auth
    def pv_review_source(request_id: str, source_id: str):
        if not _PVR_RE.match(request_id):
            return jsonify({"ok": False, "error": "رقم الطلب غير صالح"}), 400
        if not _PVS_ID_RE.match(source_id):
            return jsonify({"ok": False, "error": "معرّف المصدر غير صالح"}), 400
        pvr = _read_pvr(request_id)
        if pvr is None:
            return jsonify({"ok": False, "error": "الطلب غير موجود"}), 404
        src = _read_src(request_id, source_id)
        if src is None:
            return jsonify({"ok": False, "error": "المصدر غير موجود"}), 404

        body       = flask_request.get_json(force=True, silent=True) or {}
        new_status = (body.get("source_status") or "").strip()
        user_id    = getattr(g, "user_id", None) or "system"

        if new_status and new_status not in _SRC_VALID_STATUSES:
            return jsonify({"ok": False, "error": f"حالة غير معروفة: {new_status}"}), 400

        current = src.get("source_status", "draft")
        if new_status and new_status != current:
            allowed = _SRC_TRANSITIONS.get(current, frozenset())
            if new_status not in allowed:
                return jsonify({
                    "ok":    False,
                    "error": f"الانتقال من '{current}' إلى '{new_status}' غير مسموح",
                }), 422

        # QA simulation sources cannot become production
        if new_status == "approved_as_production_source" and src.get("qa_simulation"):
            return jsonify({
                "ok":    False,
                "error": "مصادر محاكاة QA لا يمكن اعتمادها كمصادر إنتاج",
            }), 422

        # rejected requires rejection_reason
        if new_status == "rejected":
            if not (body.get("rejection_reason") or src.get("rejection_reason")):
                return jsonify({
                    "ok":    False,
                    "error": "rejection_reason مطلوب عند الرفض",
                }), 400

        now = datetime.utcnow().isoformat()

        updates: dict = {"updated_at": now}
        if new_status:
            updates["source_status"] = new_status
        if body.get("expert_notes") is not None:
            updates["expert_review_status"] = "reviewed"
        if body.get("rejection_reason") is not None:
            updates["rejection_reason"] = body["rejection_reason"]

        effective = new_status or current
        if effective == "approved_as_production_source":
            updates["production_ready"]     = True
            updates["expert_review_status"] = "approved"
            updates["approved_by"]          = user_id
            updates["approved_at"]          = now
        elif effective in ("rejected", "superseded"):
            updates["production_ready"]     = False
            updates["expert_review_status"] = "rejected" if effective == "rejected" else "superseded"

        _update_src(request_id, source_id, updates)
        updated = _read_src(request_id, source_id)

        valuation_purpose = pvr.get("valuation_purpose", "")
        src_quality  = evaluate_source_quality(request_id, valuation_purpose)
        gate_summary = compute_gate_summary(request_id, valuation_purpose)
        _update_pvr(request_id, {
            "source_quality_status":      src_quality["source_quality_status"],
            "certification_gate_summary": gate_summary,
        })

        _append_ev_event(request_id, user_id, "source_review", {
            "source_id": source_id,
            "new_status": effective,
        })

        return jsonify({
            "ok":                  True,
            "source":              _src_safe(updated) if updated else None,
            "source_quality_summary": src_quality,
            "certification_gate_summary": gate_summary,
        }), 200
