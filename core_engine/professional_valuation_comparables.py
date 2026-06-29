"""
professional_valuation_comparables.py — Comparable Data Entry & Excel Import (Phase D).

Endpoints (all JWT-protected):
  GET  /api/professional-valuation/comparable/types
  POST /api/professional-valuation/requests/<id>/comparables
  GET  /api/professional-valuation/requests/<id>/comparables
  GET  /api/professional-valuation/requests/<id>/comparables/<comp_id>
  POST /api/professional-valuation/requests/<id>/comparables/<comp_id>/review
  POST /api/professional-valuation/requests/<id>/comparables/import
  GET  /api/professional-valuation/requests/<id>/comparables/import-jobs
  GET  /api/professional-valuation/requests/<id>/comparables/import-jobs/<job_id>
  POST /api/professional-valuation/requests/<id>/comparables/import-jobs/<job_id>/cancel

Storage (internal paths never exposed in API responses):
  core_engine/instance/professional_valuation/comparables/<request_id>.jsonl
  core_engine/instance/professional_valuation/import_jobs/<request_id>.jsonl
  core_engine/instance/professional_valuation/comparable_import_files/<request_id>/<job_id>_<safe>
  (source stubs written to existing sources/<request_id>.jsonl)

Phase D scope: comparable data entry, structured Excel/CSV import, comparable readiness gate.
  - No OCR, no Qdrant, no RAG, no external APIs, no automatic value extraction.
  - production_ready defaults to False.
  - included_in_analysis defaults to False.
  - certification_ready always False in Phase D.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── Storage paths ─────────────────────────────────────────────────────────────

_BASE               = Path(__file__).parent / "instance" / "professional_valuation"
_COMP_DIR           = _BASE / "comparables"
_IMPORT_JOBS_DIR    = _BASE / "import_jobs"
_IMPORT_FILES_DIR   = _BASE / "comparable_import_files"
# Source stubs share the Phase C sources directory
_SOURCES_DIR        = _BASE / "sources"

for _d in (_COMP_DIR, _IMPORT_JOBS_DIR, _IMPORT_FILES_DIR, _SOURCES_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── ID format validators ──────────────────────────────────────────────────────

_PVR_ID_RE  = re.compile(r"^PVR-\d{8}-[0-9A-F]{4}$")
_PVCO_ID_RE = re.compile(r"^PVCO-[0-9A-F]{8}$")   # comparable
_PVIJ_ID_RE = re.compile(r"^PVIJ-[0-9A-F]{8}$")   # import job
_PVS_ID_RE  = re.compile(r"^PVS-[0-9A-F]{8}$")    # source stub

# ── File safety ───────────────────────────────────────────────────────────────

_MAX_IMPORT_BYTES = 20 * 1024 * 1024   # 20 MB
_ALLOWED_IMPORT_EXTS: frozenset[str] = frozenset({".xlsx", ".csv", ".xls"})
_BLOCKED_EXTENSIONS: frozenset[str] = frozenset({
    ".exe", ".bat", ".cmd", ".ps1", ".js", ".html",
    ".php", ".sh", ".zip", ".tar", ".gz", ".7z", ".rar",
})

# ── Comparable type catalogue ─────────────────────────────────────────────────

PV_COMPARABLE_TYPES: dict[str, str] = {
    "sales_comparable":         "مقارن بيعي",
    "rental_comparable":        "مقارن إيجاري",
    "land_comparable":          "مقارن أرض",
    "cost_comparable":          "مقارن تكلفة",
    "cap_rate_comparable":      "مقارن معدل رسملة",
    "discount_rate_reference":  "مرجع معدل خصم",
    "mixed_comparable":         "مقارن مختلط",
}

# Required fields (at least one from each inner list) per comparable_type
_REQUIRED_FIELD_GROUPS: dict[str, list[list[str]]] = {
    "sales_comparable": [
        ["location", "district", "city", "governorate"],
        ["area_m2"],
        ["value_amount"],
        ["transaction_date", "source_reference"],
        ["property_type"],
        ["source_name", "related_source_id"],
    ],
    "rental_comparable": [
        ["location", "district", "city", "governorate"],
        ["area_m2"],
        ["monthly_rent", "annual_rent"],
        ["transaction_date", "source_reference"],
        ["property_type"],
        ["source_name", "related_source_id"],
    ],
    "land_comparable": [
        ["location", "district", "city", "governorate"],
        ["area_m2", "unit"],
        ["land_price", "value_amount"],
        ["source_name", "related_source_id"],
    ],
    "cost_comparable": [
        ["construction_cost", "value_amount"],
        ["property_type"],
        ["source_name", "related_source_id"],
    ],
    "cap_rate_comparable": [
        ["value_amount"],
        ["property_type"],
        ["source_name", "related_source_id"],
    ],
    "discount_rate_reference": [
        ["value_amount"],
        ["source_name", "related_source_id"],
    ],
    "mixed_comparable": [
        ["location", "district", "city", "governorate", "property_type"],
        ["source_name", "related_source_id"],
    ],
}

# ── Comparable status lifecycle ───────────────────────────────────────────────

_COMP_VALID_STATUSES: frozenset[str] = frozenset({
    "staged", "under_review", "approved_for_analysis",
    "approved_as_production_comparable", "rejected", "superseded",
})

_COMP_TRANSITIONS: dict[str, frozenset[str]] = {
    "staged":                           frozenset({"under_review", "approved_for_analysis", "rejected"}),
    "under_review":                     frozenset({"approved_for_analysis", "rejected"}),
    "approved_for_analysis":            frozenset({"approved_as_production_comparable", "rejected"}),
    "approved_as_production_comparable": frozenset({"superseded"}),
    "rejected":                         frozenset({"under_review"}),
    "superseded":                       frozenset(),
}

# ── Comparable readiness by valuation purpose ─────────────────────────────────

_PURPOSE_REQUIRED_COMP_TYPES: dict[str, list[str]] = {
    "سوقية":      ["sales_comparable"],
    "market":      ["sales_comparable"],
    "sales":       ["sales_comparable"],
    "بيع":         ["sales_comparable"],
    "إيجار":       ["rental_comparable"],
    "rental":      ["rental_comparable"],
    "income":      ["rental_comparable"],
    "financing":   ["sales_comparable"],
    "تمويل":       ["sales_comparable"],
    "court":       ["sales_comparable"],
    "محكم":        ["sales_comparable"],
    "investment":  ["rental_comparable", "cap_rate_comparable"],
    "استثمار":     ["rental_comparable", "cap_rate_comparable"],
    "cost":        ["cost_comparable"],
    "تكلف":        ["cost_comparable"],
    "land":        ["land_comparable"],
    "أرض":         ["land_comparable"],
}

# ── Excel header alias map ─────────────────────────────────────────────────────

_HEADER_ALIASES: dict[str, str] = {
    # comparable_id
    "comparable_id": "comparable_id", "كود المقارن": "comparable_id",
    "رقم المقارن": "comparable_id", "رقم": "comparable_id", "id": "comparable_id",
    # comparable_type
    "comparable_type": "comparable_type", "نوع المقارن": "comparable_type",
    # property_type
    "property_type": "property_type", "نوع العقار": "property_type", "نوع": "property_type",
    # property_subtype
    "property_subtype": "property_subtype", "النوع الفرعي": "property_subtype",
    # location
    "location": "location", "الموقع": "location",
    # governorate
    "governorate": "governorate", "المحافظة": "governorate", "محافظة": "governorate",
    # city
    "city": "city", "المدينة": "city", "مدينة": "city",
    # district
    "district": "district", "المنطقة": "district", "منطقة": "district",
    "الحي": "district", "حي": "district",
    # address_or_description
    "address_or_description": "address_or_description", "الوصف": "address_or_description",
    "العنوان": "address_or_description", "وصف": "address_or_description",
    # area_m2
    "area_m2": "area_m2", "المساحة": "area_m2", "مساحة": "area_m2",
    "area": "area_m2", "م2": "area_m2", "م²": "area_m2", "المساحة م2": "area_m2",
    # floor
    "floor": "floor", "الدور": "floor", "دور": "floor",
    # frontage_m
    "frontage_m": "frontage_m", "الواجهة": "frontage_m", "عرض الواجهة": "frontage_m",
    "واجهة": "frontage_m",
    # finishing_quality
    "finishing_quality": "finishing_quality", "التشطيب": "finishing_quality",
    "تشطيب": "finishing_quality",
    # condition
    "condition": "condition", "الحالة": "condition", "حالة": "condition",
    # transaction_date
    "transaction_date": "transaction_date", "تاريخ الصفقة": "transaction_date",
    "التاريخ": "transaction_date", "تاريخ": "transaction_date", "date": "transaction_date",
    # offer_or_transaction
    "offer_or_transaction": "offer_or_transaction", "عرض أم صفقة": "offer_or_transaction",
    # value_amount (sales / general)
    "value_amount": "value_amount", "القيمة": "value_amount",
    "سعر البيع": "value_amount", "إجمالي السعر": "value_amount", "price": "value_amount",
    "سعر": "value_amount",
    # monthly_rent
    "monthly_rent": "monthly_rent", "الإيجار الشهري": "monthly_rent",
    "إيجار شهري": "monthly_rent", "monthly": "monthly_rent",
    # annual_rent
    "annual_rent": "annual_rent", "الإيجار السنوي": "annual_rent",
    "إيجار سنوي": "annual_rent", "annual": "annual_rent",
    # land_price
    "land_price": "land_price", "سعر الأرض": "land_price",
    # construction_cost
    "construction_cost": "construction_cost", "تكلفة البناء": "construction_cost",
    # currency
    "currency": "currency", "العملة": "currency",
    # unit
    "unit": "unit", "الوحدة": "unit",
    # price_per_m2
    "price_per_m2": "price_per_m2", "سعر المتر": "price_per_m2",
    "قيمة المتر": "price_per_m2", "سعر/م": "price_per_m2", "price/m2": "price_per_m2",
    # rent_per_m2
    "rent_per_m2": "rent_per_m2", "إيجار المتر": "rent_per_m2",
    "إيجار/م": "rent_per_m2", "rent/m2": "rent_per_m2",
    # adjusted_price_per_m2
    "adjusted_price_per_m2": "adjusted_price_per_m2", "سعر المتر المعدل": "adjusted_price_per_m2",
    "adj_price/m2": "adjusted_price_per_m2",
    # adjusted_rent_per_m2
    "adjusted_rent_per_m2": "adjusted_rent_per_m2", "إيجار المتر المعدل": "adjusted_rent_per_m2",
    "adj_rent/m2": "adjusted_rent_per_m2",
    # land_price_per_m2
    "land_price_per_m2": "land_price_per_m2", "سعر متر الأرض": "land_price_per_m2",
    # cost_per_m2
    "cost_per_m2": "cost_per_m2", "تكلفة المتر": "cost_per_m2",
    # adjustment_percent
    "adjustment_percent": "adjustment_percent", "نسبة التعديل": "adjustment_percent",
    "تعديل%": "adjustment_percent", "adj%": "adjustment_percent",
    # adjustment_notes
    "adjustment_notes": "adjustment_notes", "ملاحظات التعديل": "adjustment_notes",
    # source_name
    "source_name": "source_name", "المصدر": "source_name", "مصدر": "source_name",
    "source": "source_name",
    # source_reference
    "source_reference": "source_reference", "مرجع المصدر": "source_reference",
    "reference": "source_reference",
}

# ── ID generation ──────────────────────────────────────────────────────────────

def _new_pvco_id() -> str:
    return "PVCO-" + uuid.uuid4().hex[:8].upper()


def _new_pvij_id() -> str:
    return "PVIJ-" + uuid.uuid4().hex[:8].upper()


def _new_pvs_id() -> str:
    return "PVS-" + uuid.uuid4().hex[:8].upper()


# ── Numeric parsing ───────────────────────────────────────────────────────────

def _parse_float(val) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        f = float(val)
        return f if (f == f and abs(f) < 1e15) else None
    s = str(val).strip().replace(",", "").replace(" ", "")
    if not s or s in ("-", "—", "N/A", "n/a"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _safe_float(val) -> Optional[float]:
    """Returns float only if positive (rejects negatives and zero for divisors)."""
    f = _parse_float(val)
    return f if (f is not None and f > 0) else None


# ── Comparable validation ─────────────────────────────────────────────────────

_NUMERIC_FIELDS = frozenset({
    "area_m2", "value_amount", "monthly_rent", "annual_rent",
    "land_price", "construction_cost", "price_per_m2", "rent_per_m2",
    "adjusted_price_per_m2", "adjusted_rent_per_m2", "land_price_per_m2",
    "cost_per_m2", "adjustment_percent",
})


def _validate_professional_comparable(payload: dict) -> dict:
    """Validate and normalize a comparable payload.

    Returns:
        {ok, normalized, validation_warnings, validation_errors}
    """
    warnings: list[str] = []
    errors:   list[str] = []
    norm:     dict      = {}

    comp_type = (payload.get("comparable_type") or "").strip()
    if comp_type not in PV_COMPARABLE_TYPES:
        errors.append(f"نوع المقارن غير صالح: '{comp_type}'. الأنواع المتاحة: {list(PV_COMPARABLE_TYPES)}")
        return {"ok": False, "normalized": {}, "validation_warnings": warnings, "validation_errors": errors}

    norm["comparable_type"] = comp_type

    # Copy and normalize string fields
    _str_fields = [
        "property_type", "property_subtype", "location", "governorate", "city",
        "district", "address_or_description", "floor", "frontage_m",
        "finishing_quality", "condition", "transaction_date", "offer_or_transaction",
        "currency", "unit", "adjustment_notes", "source_name", "source_reference",
        "related_source_id", "related_evidence_id",
    ]
    for field in _str_fields:
        val = payload.get(field)
        if val is not None:
            norm[field] = str(val).strip()

    # Normalize numeric fields — reject negatives
    for field in _NUMERIC_FIELDS:
        raw = payload.get(field)
        if raw is None:
            continue
        f = _parse_float(raw)
        if f is None:
            warnings.append(f"الحقل '{field}' ليس رقماً صالحاً — تم تجاهله.")
            continue
        if f < 0:
            errors.append(f"الحقل '{field}' لا يمكن أن يكون سالباً ({f}).")
            continue
        norm[field] = f

    # Validate required field groups
    req_groups = _REQUIRED_FIELD_GROUPS.get(comp_type, [])
    for group in req_groups:
        satisfied = any(
            norm.get(f) or payload.get(f)
            for f in group
        )
        if not satisfied:
            errors.append(
                "حقل مطلوب مفقود: " + (" أو ".join(group))
            )

    # Derive per-m2 fields if not explicitly provided
    area = _safe_float(norm.get("area_m2"))

    if area:
        # price_per_m2
        if "price_per_m2" not in norm:
            val_amt = _safe_float(norm.get("value_amount"))
            if val_amt:
                norm["price_per_m2"] = round(val_amt / area, 2)

        # rent_per_m2
        if "rent_per_m2" not in norm:
            monthly = _safe_float(norm.get("monthly_rent"))
            annual  = _safe_float(norm.get("annual_rent"))
            rent    = monthly or (annual / 12 if annual else None)
            if rent:
                norm["rent_per_m2"] = round(rent / area, 2)

        # land_price_per_m2
        if "land_price_per_m2" not in norm:
            lp = _safe_float(norm.get("land_price"))
            if lp:
                norm["land_price_per_m2"] = round(lp / area, 2)

        # cost_per_m2
        if "cost_per_m2" not in norm:
            cc = _safe_float(norm.get("construction_cost"))
            if cc:
                norm["cost_per_m2"] = round(cc / area, 2)

    # adjusted_price_per_m2 from adjustment_percent
    if "adjusted_price_per_m2" not in norm:
        ppm2 = _safe_float(norm.get("price_per_m2"))
        adj  = _parse_float(norm.get("adjustment_percent"))
        if ppm2 is not None and adj is not None:
            norm["adjusted_price_per_m2"] = round(ppm2 * (1 + adj / 100), 2)

    if "adjusted_rent_per_m2" not in norm:
        rpm2 = _safe_float(norm.get("rent_per_m2"))
        adj  = _parse_float(norm.get("adjustment_percent"))
        if rpm2 is not None and adj is not None:
            norm["adjusted_rent_per_m2"] = round(rpm2 * (1 + adj / 100), 2)

    # QA simulation flag
    norm["qa_simulation"] = bool(payload.get("qa_simulation", False))

    ok = len(errors) == 0
    return {
        "ok":                  ok,
        "normalized":          norm,
        "validation_warnings": warnings,
        "validation_errors":   errors,
    }


# ── Comparable readiness gate ─────────────────────────────────────────────────

def evaluate_comparable_readiness(request_id: str, valuation_purpose: str) -> dict:
    """Compute comparable readiness gate for the request."""
    comps = _load_comparables(request_id)

    total              = len(comps)
    staged_count       = sum(1 for c in comps if c.get("status") == "staged")
    under_review_count = sum(1 for c in comps if c.get("status") == "under_review")
    approved_count     = sum(1 for c in comps if c.get("status") in ("approved_for_analysis", "approved_as_production_comparable"))
    production_count   = sum(1 for c in comps if c.get("production_ready") and not c.get("qa_simulation"))
    qa_count           = sum(1 for c in comps if c.get("qa_simulation"))
    rejected_count     = sum(1 for c in comps if c.get("status") == "rejected")

    # Determine required comparable types by purpose
    purpose_lower = (valuation_purpose or "").lower()
    required_types: list[str] = []
    for keyword, types in _PURPOSE_REQUIRED_COMP_TYPES.items():
        if keyword.lower() in purpose_lower:
            for t in types:
                if t not in required_types:
                    required_types.append(t)

    # Check which required types are covered by approved comparables
    approved_types = {c.get("comparable_type") for c in comps
                      if c.get("status") in ("approved_for_analysis", "approved_as_production_comparable")
                      and not c.get("qa_simulation")}
    missing_types = [t for t in required_types if t not in approved_types]

    real_comparables_ready      = approved_count > 0 and qa_count == 0 or (
        approved_count > 0 and production_count > 0
    )
    certification_comparable_ready = production_count > 0 and len(missing_types) == 0

    required_actions: list[str] = []
    if total == 0:
        required_actions.append("لا توجد مقارنات — يرجى إضافة مقارنات أو استيراد ملف Excel.")
    if staged_count > 0:
        required_actions.append(f"{staged_count} مقارن في انتظار المراجعة.")
    if missing_types:
        labels = [PV_COMPARABLE_TYPES.get(t, t) for t in missing_types]
        required_actions.append("أنواع مقارنات مطلوبة مفقودة: " + "، ".join(labels))
    if qa_count > 0:
        required_actions.append(f"{qa_count} مقارن QA — لا يُحتسب للإنتاج.")
    if production_count == 0:
        required_actions.append("لا توجد مقارنات إنتاجية معتمدة.")

    if certification_comparable_ready:
        status = "ready"
    elif approved_count > 0:
        status = "partial"
    elif total > 0:
        status = "staged"
    else:
        status = "missing"

    return {
        "comparable_readiness_status":          status,
        "total_comparables":                    total,
        "staged_comparables":                   staged_count,
        "under_review_comparables":             under_review_count,
        "approved_for_analysis_comparables":    approved_count,
        "production_ready_comparables":         production_count,
        "qa_comparables":                       qa_count,
        "rejected_comparables":                 rejected_count,
        "required_comparable_types":            required_types,
        "missing_comparable_types":             missing_types,
        "real_comparables_ready":               real_comparables_ready,
        "certification_comparable_ready":       certification_comparable_ready,
        "advisory_only_reason": (
            "Phase D — comparables staged for expert review only. "
            "They do not update final valuation automatically."
        ),
        "required_actions": required_actions,
    }


# ── Persistence helpers ───────────────────────────────────────────────────────

def _comp_file(request_id: str) -> Path:
    return _COMP_DIR / f"{request_id}.jsonl"


def _jobs_file(request_id: str) -> Path:
    return _IMPORT_JOBS_DIR / f"{request_id}.jsonl"


def _persist_comp(request_id: str, rec: dict) -> None:
    with open(_comp_file(request_id), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _update_comp(request_id: str, comp_id: str, updates: dict) -> None:
    f = _comp_file(request_id)
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
                if rec.get("comparable_id") == comp_id:
                    rec.update(updates)
                lines.append(json.dumps(rec, ensure_ascii=False))
            except json.JSONDecodeError:
                lines.append(raw)
    with open(f, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def _read_comp(request_id: str, comp_id: str) -> Optional[dict]:
    f = _comp_file(request_id)
    if not f.exists():
        return None
    with open(f, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
                if rec.get("comparable_id") == comp_id:
                    return rec
            except json.JSONDecodeError:
                continue
    return None


def _load_comparables(request_id: str) -> list[dict]:
    f = _comp_file(request_id)
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


def _persist_job(request_id: str, rec: dict) -> None:
    with open(_jobs_file(request_id), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _update_job(request_id: str, job_id: str, updates: dict) -> None:
    f = _jobs_file(request_id)
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
                if rec.get("import_job_id") == job_id:
                    rec.update(updates)
                lines.append(json.dumps(rec, ensure_ascii=False))
            except json.JSONDecodeError:
                lines.append(raw)
    with open(f, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def _read_job(request_id: str, job_id: str) -> Optional[dict]:
    f = _jobs_file(request_id)
    if not f.exists():
        return None
    with open(f, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
                if rec.get("import_job_id") == job_id:
                    return rec
            except json.JSONDecodeError:
                continue
    return None


def _load_jobs(request_id: str) -> list[dict]:
    f = _jobs_file(request_id)
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


# Source stub persistence (shares Phase C sources JSONL)
def _persist_source_stub(request_id: str, rec: dict) -> None:
    f = _SOURCES_DIR / f"{request_id}.jsonl"
    with open(f, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ── Public-safe record builders ───────────────────────────────────────────────

def _comp_safe(rec: dict) -> dict:
    """Public-safe comparable metadata — never includes internal file paths."""
    return {
        "comparable_id":            rec.get("comparable_id"),
        "request_id":               rec.get("request_id"),
        "created_at":               rec.get("created_at"),
        "created_by":               rec.get("created_by"),
        "source_origin":            rec.get("source_origin"),
        "import_job_id":            rec.get("import_job_id"),
        "related_source_id":        rec.get("related_source_id"),
        "related_evidence_id":      rec.get("related_evidence_id"),
        "comparable_type":          rec.get("comparable_type"),
        "comparable_label_ar":      rec.get("comparable_label_ar"),
        "property_type":            rec.get("property_type"),
        "property_subtype":         rec.get("property_subtype"),
        "location":                 rec.get("location"),
        "governorate":              rec.get("governorate"),
        "city":                     rec.get("city"),
        "district":                 rec.get("district"),
        "address_or_description":   rec.get("address_or_description"),
        "area_m2":                  rec.get("area_m2"),
        "floor":                    rec.get("floor"),
        "frontage_m":               rec.get("frontage_m"),
        "finishing_quality":        rec.get("finishing_quality"),
        "condition":                rec.get("condition"),
        "transaction_date":         rec.get("transaction_date"),
        "offer_or_transaction":     rec.get("offer_or_transaction"),
        "value_amount":             rec.get("value_amount"),
        "monthly_rent":             rec.get("monthly_rent"),
        "annual_rent":              rec.get("annual_rent"),
        "land_price":               rec.get("land_price"),
        "construction_cost":        rec.get("construction_cost"),
        "currency":                 rec.get("currency"),
        "unit":                     rec.get("unit"),
        "price_per_m2":             rec.get("price_per_m2"),
        "rent_per_m2":              rec.get("rent_per_m2"),
        "land_price_per_m2":        rec.get("land_price_per_m2"),
        "cost_per_m2":              rec.get("cost_per_m2"),
        "adjusted_price_per_m2":    rec.get("adjusted_price_per_m2"),
        "adjusted_rent_per_m2":     rec.get("adjusted_rent_per_m2"),
        "adjustment_percent":       rec.get("adjustment_percent"),
        "adjustment_notes":         rec.get("adjustment_notes"),
        "source_name":              rec.get("source_name"),
        "source_reference":         rec.get("source_reference"),
        "status":                   rec.get("status"),
        "review_status":            rec.get("review_status"),
        "expert_review_notes":      rec.get("expert_review_notes"),
        "rejection_reason":         rec.get("rejection_reason"),
        "validation_status":        rec.get("validation_status"),
        "validation_warnings":      rec.get("validation_warnings", []),
        "validation_errors":        rec.get("validation_errors", []),
        "production_ready":         rec.get("production_ready", False),
        "qa_simulation":            rec.get("qa_simulation", False),
        "included_in_analysis":     rec.get("included_in_analysis", False),
        "external_api_used":        rec.get("external_api_used", False),
        "qdrant_used":              rec.get("qdrant_used", False),
        "rag_used":                 rec.get("rag_used", False),
    }


def _job_safe(rec: dict) -> dict:
    """Public-safe import job — never includes internal file paths."""
    return {
        "import_job_id":        rec.get("import_job_id"),
        "request_id":           rec.get("request_id"),
        "created_at":           rec.get("created_at"),
        "created_by":           rec.get("created_by"),
        "original_filename":    rec.get("original_filename"),
        "file_ext":             rec.get("file_ext"),
        "import_type":          rec.get("import_type"),
        "sheet_names":          rec.get("sheet_names", []),
        "selected_sheet":       rec.get("selected_sheet"),
        "detected_columns":     rec.get("detected_columns", []),
        "normalized_columns":   rec.get("normalized_columns", []),
        "unknown_columns":      rec.get("unknown_columns", []),
        "row_count":            rec.get("row_count", 0),
        "staged_rows_count":    rec.get("staged_rows_count", 0),
        "rejected_rows_count":  rec.get("rejected_rows_count", 0),
        "warnings":             rec.get("warnings", []),
        "errors":               rec.get("errors", []),
        "status":               rec.get("status"),
        "comparable_type_hint": rec.get("comparable_type_hint"),
        "qa_simulation":        rec.get("qa_simulation", False),
        "external_api_used":    rec.get("external_api_used", False),
        "qdrant_used":          rec.get("qdrant_used", False),
        "rag_used":             rec.get("rag_used", False),
    }


# ── File sanitization ─────────────────────────────────────────────────────────

def _sanitize_filename(name: str) -> str:
    name = os.path.basename(name)
    name = name.replace("..", "")
    safe = "".join(c for c in name if c.isalnum() or c in "._- ")
    return safe.strip() or "upload"


# ── Column normalization ──────────────────────────────────────────────────────

def _normalize_col(raw: str) -> Optional[str]:
    key = raw.strip().lower()
    if key in _HEADER_ALIASES:
        return _HEADER_ALIASES[key]
    key2 = " ".join(key.split())
    return _HEADER_ALIASES.get(key2)


def _normalize_headers(raw_headers: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Return (detected_originals, normalized_canonicals, unknown_originals)."""
    detected:   list[str] = []
    normalized: list[str] = []
    unknown:    list[str] = []
    seen: set[str] = set()
    for raw in raw_headers:
        canonical = _normalize_col(raw)
        if canonical and canonical not in seen:
            detected.append(raw)
            normalized.append(canonical)
            seen.add(canonical)
        else:
            unknown.append(raw)
    return detected, normalized, unknown


# ── Excel / CSV parsing ───────────────────────────────────────────────────────

def _parse_xlsx(file_bytes: bytes, selected_sheet: Optional[str] = None) -> tuple[list[str], list[dict], list[str]]:
    """Parse an xlsx file. Returns (raw_headers, dicts_of_rows, sheet_names)."""
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    sheet_names = wb.sheetnames
    ws = wb[selected_sheet] if (selected_sheet and selected_sheet in sheet_names) else wb.active
    rows_iter = list(ws.iter_rows(values_only=True))
    if not rows_iter:
        return [], [], sheet_names
    raw_headers = [str(h).strip() if h is not None else "" for h in rows_iter[0]]
    dicts: list[dict] = []
    for row in rows_iter[1:]:
        if all(c is None for c in row):
            continue
        d = {raw_headers[i]: (row[i] if i < len(row) else None) for i in range(len(raw_headers))}
        dicts.append(d)
    wb.close()
    return raw_headers, dicts, sheet_names


def _parse_csv(file_bytes: bytes) -> tuple[list[str], list[dict]]:
    """Parse a CSV file. Returns (raw_headers, dicts_of_rows)."""
    text = file_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    raw_headers = reader.fieldnames or []
    dicts = [dict(row) for row in reader]
    return list(raw_headers), dicts


def _row_to_comparable_payload(row: dict, normalized_cols: list[str],
                                raw_headers: list[str],
                                comp_type_hint: str) -> dict:
    """Map a normalized row dict to a comparable payload."""
    # Build reverse map: normalized_col -> raw_header
    col_map = {normalized_cols[i]: raw_headers[i] for i in range(len(normalized_cols))}

    payload: dict = {}
    for canonical, raw_hdr in col_map.items():
        val = row.get(raw_hdr)
        if val is not None and str(val).strip() not in ("", "None"):
            payload[canonical] = val

    # If comparable_type not in row, use hint
    if "comparable_type" not in payload and comp_type_hint:
        payload["comparable_type"] = comp_type_hint

    return payload


def _import_rows(
    raw_headers: list[str],
    raw_rows: list[dict],
    comp_type_hint: str,
    request_id: str,
    job_id: str,
    user_id: str,
    qa_simulation: bool,
    create_source_stubs: bool,
    now: str,
) -> tuple[list[dict], list[dict], list[str]]:
    """Stage valid rows as comparables. Returns (staged, rejected, job_warnings)."""
    detected, normalized, unknown = _normalize_headers(raw_headers)
    job_warnings: list[str] = []
    if unknown:
        job_warnings.append(f"أعمدة غير معروفة (تم تجاهلها): {', '.join(unknown[:10])}")

    staged:   list[dict] = []
    rejected: list[dict] = []

    for idx, raw_row in enumerate(raw_rows):
        payload = _row_to_comparable_payload(raw_row, normalized, detected, comp_type_hint)
        payload["qa_simulation"] = qa_simulation

        vr = _validate_professional_comparable(payload)
        norm = vr["normalized"]
        v_warnings = vr["validation_warnings"]
        v_errors   = vr["validation_errors"]

        if not vr["ok"]:
            rejected.append({
                "row_index":    idx + 2,  # 1-based + header row
                "raw_row":      {k: str(v)[:200] for k, v in raw_row.items()},
                "errors":       v_errors,
                "warnings":     v_warnings,
            })
            continue

        comp_id = _new_pvco_id()
        comp_type = norm.get("comparable_type", comp_type_hint)
        src_stub_id = None

        # Optionally create draft source stub
        if create_source_stubs and (norm.get("source_name") or norm.get("source_reference")):
            src_stub_id = _new_pvs_id()
            stub = {
                "source_id":          src_stub_id,
                "request_id":         request_id,
                "created_at":         now,
                "created_by":         user_id,
                "source_type":        _comp_type_to_source_type(comp_type),
                "source_category":    "comparable_import_stub",
                "source_name":        norm.get("source_name", ""),
                "source_description": norm.get("source_reference", ""),
                "related_evidence_id": None,
                "related_method":     None,
                "location":           norm.get("location") or norm.get("district"),
                "district":           norm.get("district"),
                "property_type":      norm.get("property_type"),
                "transaction_date":   norm.get("transaction_date"),
                "value_type":         _comp_type_to_value_type(comp_type),
                "value_amount":       norm.get("value_amount") or norm.get("monthly_rent"),
                "unit":               norm.get("unit", "EGP"),
                "area_m2":            norm.get("area_m2"),
                "value_per_m2":       norm.get("price_per_m2") or norm.get("rent_per_m2"),
                "source_status":      "draft",
                "expert_review_status": "pending",
                "production_ready":   False,
                "approved_by":        None,
                "approved_at":        None,
                "rejection_reason":   None,
                "limitations":        "مصدر مستورد تلقائياً — يحتاج مراجعة خبير.",
                "qa_simulation":      qa_simulation,
                "import_job_id":      job_id,
                "external_api_used":  False,
                "qdrant_used":        False,
                "rag_used":           False,
            }
            _persist_source_stub(request_id, stub)

        rec: dict = {
            "comparable_id":          comp_id,
            "request_id":             request_id,
            "created_at":             now,
            "created_by":             user_id,
            "source_origin":          "excel_import",
            "import_job_id":          job_id,
            "related_source_id":      src_stub_id,
            "related_evidence_id":    norm.get("related_evidence_id"),
            "comparable_type":        comp_type,
            "comparable_label_ar":    PV_COMPARABLE_TYPES.get(comp_type, comp_type),
            "property_type":          norm.get("property_type", ""),
            "property_subtype":       norm.get("property_subtype", ""),
            "location":               norm.get("location", ""),
            "governorate":            norm.get("governorate", ""),
            "city":                   norm.get("city", ""),
            "district":               norm.get("district", ""),
            "address_or_description": norm.get("address_or_description", ""),
            "area_m2":                norm.get("area_m2"),
            "floor":                  norm.get("floor"),
            "frontage_m":             norm.get("frontage_m"),
            "finishing_quality":      norm.get("finishing_quality", ""),
            "condition":              norm.get("condition", ""),
            "transaction_date":       norm.get("transaction_date", ""),
            "offer_or_transaction":   norm.get("offer_or_transaction", ""),
            "value_amount":           norm.get("value_amount"),
            "monthly_rent":           norm.get("monthly_rent"),
            "annual_rent":            norm.get("annual_rent"),
            "land_price":             norm.get("land_price"),
            "construction_cost":      norm.get("construction_cost"),
            "currency":               norm.get("currency", "EGP"),
            "unit":                   norm.get("unit", ""),
            "price_per_m2":           norm.get("price_per_m2"),
            "rent_per_m2":            norm.get("rent_per_m2"),
            "land_price_per_m2":      norm.get("land_price_per_m2"),
            "cost_per_m2":            norm.get("cost_per_m2"),
            "adjusted_price_per_m2":  norm.get("adjusted_price_per_m2"),
            "adjusted_rent_per_m2":   norm.get("adjusted_rent_per_m2"),
            "adjustment_percent":     norm.get("adjustment_percent"),
            "adjustment_notes":       norm.get("adjustment_notes", ""),
            "source_name":            norm.get("source_name", ""),
            "source_reference":       norm.get("source_reference", ""),
            "source_status":          "staged",
            "status":                 "staged",
            "review_status":          "pending",
            "expert_review_notes":    "",
            "rejection_reason":       None,
            "validation_status":      "ok" if not v_errors else "warnings",
            "validation_warnings":    v_warnings,
            "validation_errors":      [],
            "production_ready":       False,
            "qa_simulation":          qa_simulation,
            "included_in_analysis":   False,
            "external_api_used":      False,
            "qdrant_used":            False,
            "rag_used":               False,
            "metadata":               {"row_index": idx + 2},
        }
        _persist_comp(request_id, rec)
        staged.append(_comp_safe(rec))

    return staged, rejected, job_warnings


def _comp_type_to_source_type(comp_type: str) -> str:
    _map = {
        "sales_comparable":        "sales_comparable",
        "rental_comparable":       "rental_comparable",
        "land_comparable":         "land_price_reference",
        "cost_comparable":         "construction_cost_reference",
        "cap_rate_comparable":     "cap_rate_reference",
        "discount_rate_reference": "discount_rate_reference",
        "mixed_comparable":        "expert_manual_entry",
    }
    return _map.get(comp_type, "expert_manual_entry")


def _comp_type_to_value_type(comp_type: str) -> str:
    _map = {
        "sales_comparable":        "sale_price",
        "rental_comparable":       "rent",
        "land_comparable":         "land_price",
        "cost_comparable":         "construction_cost",
        "cap_rate_comparable":     "cap_rate",
        "discount_rate_reference": "discount_rate",
    }
    return _map.get(comp_type, "value")


# ── Route registration ────────────────────────────────────────────────────────

def register_pv_comparable_routes(app, require_auth, limiter=None) -> None:
    """Register all Phase D comparable routes on *app*."""
    from flask import g, jsonify, request as flask_request
    from professional_valuation_routes import (
        _read_pvr, _PVR_ID_RE as _PVR_RE, _append_event,
    )

    # ── GET /api/professional-valuation/comparable/types ───────────────────
    @app.route("/api/professional-valuation/comparable/types", methods=["GET"])
    @require_auth
    def pv_comparable_types():
        catalogue = []
        for key, label_ar in PV_COMPARABLE_TYPES.items():
            req_groups = _REQUIRED_FIELD_GROUPS.get(key, [])
            catalogue.append({
                "key":              key,
                "label_ar":         label_ar,
                "required_fields":  req_groups,
            })
        return jsonify({"ok": True, "comparable_types": catalogue}), 200

    # ── POST /api/professional-valuation/requests/<id>/comparables ─────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/comparables",
        methods=["POST"],
    )
    @require_auth
    def pv_create_comparable(request_id: str):
        if not _PVR_RE.match(request_id):
            return jsonify({"ok": False, "error": "رقم الطلب غير صالح"}), 400
        req_rec = _read_pvr(request_id)
        if req_rec is None:
            return jsonify({"ok": False, "error": "الطلب غير موجود"}), 404

        body = flask_request.get_json(force=True, silent=True) or {}
        vr   = _validate_professional_comparable(body)
        if not vr["ok"]:
            return jsonify({
                "ok":                False,
                "error":             "بيانات المقارن غير صالحة.",
                "validation_errors": vr["validation_errors"],
            }), 422

        norm    = vr["normalized"]
        now     = datetime.utcnow().isoformat()
        user_id = getattr(g, "user_id", None) or "system"
        comp_id = _new_pvco_id()
        comp_type = norm["comparable_type"]

        rec: dict = {
            "comparable_id":          comp_id,
            "request_id":             request_id,
            "created_at":             now,
            "created_by":             user_id,
            "source_origin":          "manual_entry",
            "import_job_id":          None,
            "related_source_id":      norm.get("related_source_id"),
            "related_evidence_id":    norm.get("related_evidence_id"),
            "comparable_type":        comp_type,
            "comparable_label_ar":    PV_COMPARABLE_TYPES.get(comp_type, comp_type),
            "property_type":          norm.get("property_type", ""),
            "property_subtype":       norm.get("property_subtype", ""),
            "location":               norm.get("location", ""),
            "governorate":            norm.get("governorate", ""),
            "city":                   norm.get("city", ""),
            "district":               norm.get("district", ""),
            "address_or_description": norm.get("address_or_description", ""),
            "area_m2":                norm.get("area_m2"),
            "floor":                  norm.get("floor"),
            "frontage_m":             norm.get("frontage_m"),
            "finishing_quality":      norm.get("finishing_quality", ""),
            "condition":              norm.get("condition", ""),
            "transaction_date":       norm.get("transaction_date", ""),
            "offer_or_transaction":   norm.get("offer_or_transaction", ""),
            "value_amount":           norm.get("value_amount"),
            "monthly_rent":           norm.get("monthly_rent"),
            "annual_rent":            norm.get("annual_rent"),
            "land_price":             norm.get("land_price"),
            "construction_cost":      norm.get("construction_cost"),
            "currency":               norm.get("currency", "EGP"),
            "unit":                   norm.get("unit", ""),
            "price_per_m2":           norm.get("price_per_m2"),
            "rent_per_m2":            norm.get("rent_per_m2"),
            "land_price_per_m2":      norm.get("land_price_per_m2"),
            "cost_per_m2":            norm.get("cost_per_m2"),
            "adjusted_price_per_m2":  norm.get("adjusted_price_per_m2"),
            "adjusted_rent_per_m2":   norm.get("adjusted_rent_per_m2"),
            "adjustment_percent":     norm.get("adjustment_percent"),
            "adjustment_notes":       norm.get("adjustment_notes", ""),
            "source_name":            norm.get("source_name", ""),
            "source_reference":       norm.get("source_reference", ""),
            "source_status":          "staged",
            "status":                 "staged",
            "review_status":          "pending",
            "expert_review_notes":    "",
            "rejection_reason":       None,
            "validation_status":      "ok",
            "validation_warnings":    vr["validation_warnings"],
            "validation_errors":      [],
            "production_ready":       False,
            "qa_simulation":          norm.get("qa_simulation", False),
            "included_in_analysis":   False,
            "external_api_used":      False,
            "qdrant_used":            False,
            "rag_used":               False,
            "metadata":               {},
        }
        _persist_comp(request_id, rec)

        _append_event(
            request_id=request_id, actor=user_id,
            action="comparable_create",
            from_status="", to_status="staged",
            note=f"comparable_id={comp_id} type={comp_type}",
            metadata={"comparable_id": comp_id},
        )

        valuation_purpose = req_rec.get("valuation_purpose", "")
        readiness = evaluate_comparable_readiness(request_id, valuation_purpose)

        return jsonify({
            "ok":                    True,
            "comparable":            _comp_safe(rec),
            "comparable_readiness":  readiness,
            "certification_gate_summary": _gate_summary_with_comparables(request_id, valuation_purpose),
        }), 201

    # ── GET /api/professional-valuation/requests/<id>/comparables ──────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/comparables",
        methods=["GET"],
    )
    @require_auth
    def pv_list_comparables(request_id: str):
        if not _PVR_RE.match(request_id):
            return jsonify({"ok": False, "error": "رقم الطلب غير صالح"}), 400
        req_rec = _read_pvr(request_id)
        if req_rec is None:
            return jsonify({"ok": False, "error": "الطلب غير موجود"}), 404

        all_comps = _load_comparables(request_id)

        # Optional filters
        args = flask_request.args
        ftype    = args.get("comparable_type")
        fstatus  = args.get("status")
        fprod    = args.get("production_ready")
        fqa      = args.get("qa_simulation")
        forigin  = args.get("source_origin")

        filtered = all_comps
        if ftype:
            filtered = [c for c in filtered if c.get("comparable_type") == ftype]
        if fstatus:
            filtered = [c for c in filtered if c.get("status") == fstatus]
        if fprod is not None:
            want = fprod.lower() == "true"
            filtered = [c for c in filtered if bool(c.get("production_ready")) == want]
        if fqa is not None:
            want = fqa.lower() == "true"
            filtered = [c for c in filtered if bool(c.get("qa_simulation")) == want]
        if forigin:
            filtered = [c for c in filtered if c.get("source_origin") == forigin]

        valuation_purpose = req_rec.get("valuation_purpose", "")
        readiness = evaluate_comparable_readiness(request_id, valuation_purpose)

        type_counts: dict[str, int] = {}
        for c in all_comps:
            t = c.get("comparable_type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        return jsonify({
            "ok":                   True,
            "comparables":          [_comp_safe(c) for c in filtered],
            "comparable_readiness": readiness,
            "counts": {
                "total":            len(all_comps),
                "by_type":          type_counts,
                "staged":           sum(1 for c in all_comps if c.get("status") == "staged"),
                "under_review":     sum(1 for c in all_comps if c.get("status") == "under_review"),
                "approved":         sum(1 for c in all_comps if c.get("status") in ("approved_for_analysis", "approved_as_production_comparable")),
                "production_ready": sum(1 for c in all_comps if c.get("production_ready")),
                "rejected":         sum(1 for c in all_comps if c.get("status") == "rejected"),
                "qa":               sum(1 for c in all_comps if c.get("qa_simulation")),
            },
        }), 200

    # ── GET /api/professional-valuation/requests/<id>/comparables/<comp_id> ──
    @app.route(
        "/api/professional-valuation/requests/<request_id>/comparables/<comp_id>",
        methods=["GET"],
    )
    @require_auth
    def pv_get_comparable(request_id: str, comp_id: str):
        if not _PVR_RE.match(request_id):
            return jsonify({"ok": False, "error": "رقم الطلب غير صالح"}), 400
        if not _PVCO_ID_RE.match(comp_id):
            return jsonify({"ok": False, "error": "معرّف المقارن غير صالح"}), 400
        req_rec = _read_pvr(request_id)
        if req_rec is None:
            return jsonify({"ok": False, "error": "الطلب غير موجود"}), 404
        rec = _read_comp(request_id, comp_id)
        if rec is None:
            return jsonify({"ok": False, "error": "المقارن غير موجود"}), 404
        return jsonify({"ok": True, "comparable": _comp_safe(rec)}), 200

    # ── POST /api/professional-valuation/requests/<id>/comparables/<comp_id>/review
    @app.route(
        "/api/professional-valuation/requests/<request_id>/comparables/<comp_id>/review",
        methods=["POST"],
    )
    @require_auth
    def pv_review_comparable(request_id: str, comp_id: str):
        if not _PVR_RE.match(request_id):
            return jsonify({"ok": False, "error": "رقم الطلب غير صالح"}), 400
        if not _PVCO_ID_RE.match(comp_id):
            return jsonify({"ok": False, "error": "معرّف المقارن غير صالح"}), 400
        req_rec = _read_pvr(request_id)
        if req_rec is None:
            return jsonify({"ok": False, "error": "الطلب غير موجود"}), 404
        rec = _read_comp(request_id, comp_id)
        if rec is None:
            return jsonify({"ok": False, "error": "المقارن غير موجود"}), 404

        body      = flask_request.get_json(force=True, silent=True) or {}
        new_status = (body.get("status") or "").strip()
        user_id   = getattr(g, "user_id", None) or "system"
        now       = datetime.utcnow().isoformat()

        if new_status not in _COMP_VALID_STATUSES:
            return jsonify({"ok": False, "error": f"الحالة غير صالحة: '{new_status}'"}), 400

        curr_status = rec.get("status", "staged")
        allowed     = _COMP_TRANSITIONS.get(curr_status, frozenset())
        if new_status not in allowed:
            return jsonify({
                "ok":    False,
                "error": f"الانتقال من '{curr_status}' إلى '{new_status}' غير مسموح به.",
            }), 422

        # Validation rules for specific transitions
        if new_status == "rejected":
            rejection_reason = (body.get("rejection_reason") or "").strip()
            if not rejection_reason:
                return jsonify({"ok": False, "error": "يجب تحديد rejection_reason عند الرفض."}), 400

        if new_status == "approved_as_production_comparable":
            if rec.get("qa_simulation"):
                return jsonify({
                    "ok":    False,
                    "error": "المقارنات QA لا يمكن أن تصبح approved_as_production_comparable.",
                }), 422
            if rec.get("validation_errors"):
                return jsonify({
                    "ok":    False,
                    "error": "المقارن يحتوي على أخطاء تحقق — يجب إصلاحها أولاً.",
                }), 422
            if not (rec.get("source_name") or rec.get("related_source_id")):
                return jsonify({
                    "ok":    False,
                    "error": "يجب تحديد source_name أو related_source_id قبل الاعتماد للإنتاج.",
                }), 422

        included_in_analysis = bool(body.get("included_in_analysis", rec.get("included_in_analysis", False)))
        if included_in_analysis and new_status not in ("approved_for_analysis", "approved_as_production_comparable"):
            return jsonify({
                "ok":    False,
                "error": "included_in_analysis يمكن أن يكون True فقط عند approved_for_analysis أو approved_as_production_comparable.",
            }), 422

        production_ready = (
            new_status == "approved_as_production_comparable"
            and not rec.get("qa_simulation")
        )

        updates = {
            "status":               new_status,
            "review_status":        new_status,
            "reviewed_at":          now,
            "reviewed_by":          user_id,
            "expert_review_notes":  (body.get("expert_review_notes") or rec.get("expert_review_notes", "")),
            "rejection_reason":     body.get("rejection_reason") or rec.get("rejection_reason"),
            "included_in_analysis": included_in_analysis,
            "production_ready":     production_ready,
        }
        _update_comp(request_id, comp_id, updates)
        updated = _read_comp(request_id, comp_id)

        _append_event(
            request_id=request_id, actor=user_id,
            action="comparable_review",
            from_status=curr_status, to_status=new_status,
            note=f"comparable_id={comp_id}",
            metadata={"comparable_id": comp_id, "production_ready": production_ready},
        )

        valuation_purpose = req_rec.get("valuation_purpose", "")
        readiness = evaluate_comparable_readiness(request_id, valuation_purpose)

        return jsonify({
            "ok":                    True,
            "comparable":            _comp_safe(updated),
            "comparable_readiness":  readiness,
            "certification_gate_summary": _gate_summary_with_comparables(request_id, valuation_purpose),
        }), 200

    # ── POST /api/professional-valuation/requests/<id>/comparables/import ──
    @app.route(
        "/api/professional-valuation/requests/<request_id>/comparables/import",
        methods=["POST"],
    )
    @require_auth
    def pv_import_comparables(request_id: str):
        if not _PVR_RE.match(request_id):
            return jsonify({"ok": False, "error": "رقم الطلب غير صالح"}), 400
        req_rec = _read_pvr(request_id)
        if req_rec is None:
            return jsonify({"ok": False, "error": "الطلب غير موجود"}), 404

        file_obj = flask_request.files.get("file") if flask_request.files else None
        if not file_obj or not file_obj.filename:
            return jsonify({"ok": False, "error": "لم يتم رفع ملف."}), 400

        orig_name = _sanitize_filename(file_obj.filename)
        ext       = Path(orig_name).suffix.lower()
        if ext in _BLOCKED_EXTENSIONS:
            return jsonify({"ok": False, "error": f"صيغة الملف محظورة: {ext}"}), 400
        if ext not in _ALLOWED_IMPORT_EXTS:
            return jsonify({
                "ok":    False,
                "error": f"صيغة غير مدعومة: {ext}. المدعومة: .xlsx, .csv",
            }), 400

        data = file_obj.read()
        if len(data) == 0:
            return jsonify({"ok": False, "error": "الملف فارغ."}), 400
        if len(data) > _MAX_IMPORT_BYTES:
            return jsonify({"ok": False, "error": "حجم الملف يتجاوز 20 ميجابايت."}), 400

        form            = flask_request.form
        comp_type_hint  = (form.get("comparable_type_hint") or "").strip()
        selected_sheet  = (form.get("selected_sheet") or "").strip() or None
        qa_simulation   = form.get("qa_simulation", "false").lower() == "true"
        create_stubs    = form.get("create_source_stubs", "false").lower() == "true"

        if comp_type_hint and comp_type_hint not in PV_COMPARABLE_TYPES:
            return jsonify({
                "ok":    False,
                "error": f"comparable_type_hint غير صالح: '{comp_type_hint}'",
            }), 400

        user_id = getattr(g, "user_id", None) or "system"
        now     = datetime.utcnow().isoformat()
        job_id  = _new_pvij_id()

        # Save file safely (no path in API response)
        dest_dir = _IMPORT_FILES_DIR / request_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        safe_stored = job_id + ext
        (dest_dir / safe_stored).write_bytes(data)

        # Parse
        parse_errors: list[str] = []
        sheet_names:  list[str] = []
        raw_headers:  list[str] = []
        raw_rows:     list[dict] = []

        try:
            if ext == ".xlsx":
                raw_headers, raw_rows, sheet_names = _parse_xlsx(data, selected_sheet)
                import_type = "xlsx"
            elif ext == ".xls":
                # Treat as binary xlsx fallback via openpyxl
                try:
                    raw_headers, raw_rows, sheet_names = _parse_xlsx(data, selected_sheet)
                    import_type = "xls_compat"
                except Exception:
                    parse_errors.append("ملف .xls قد لا يكون مدعوماً — استخدم .xlsx أو .csv.")
                    import_type = "xls"
            else:  # .csv
                raw_headers, raw_rows = _parse_csv(data)
                import_type = "csv"
        except Exception as exc:
            parse_errors.append(f"خطأ في تحليل الملف: {str(exc)[:200]}")

        if parse_errors:
            job_rec = {
                "import_job_id":     job_id,
                "request_id":        request_id,
                "created_at":        now,
                "created_by":        user_id,
                "original_filename": orig_name,
                "file_ext":          ext,
                "import_type":       import_type if 'import_type' in dir() else ext[1:],
                "sheet_names":       [],
                "selected_sheet":    selected_sheet,
                "detected_columns":  [],
                "normalized_columns": [],
                "unknown_columns":   [],
                "row_count":         0,
                "staged_rows_count": 0,
                "rejected_rows_count": 0,
                "warnings":          [],
                "errors":            parse_errors,
                "status":            "failed",
                "comparable_type_hint": comp_type_hint,
                "qa_simulation":     qa_simulation,
                "external_api_used": False,
                "qdrant_used":       False,
                "rag_used":          False,
            }
            _persist_job(request_id, job_rec)
            return jsonify({
                "ok":    False,
                "error": parse_errors[0],
                "import_job": _job_safe(job_rec),
            }), 422

        # Process rows
        staged, rejected, job_warnings = _import_rows(
            raw_headers=raw_headers,
            raw_rows=raw_rows,
            comp_type_hint=comp_type_hint,
            request_id=request_id,
            job_id=job_id,
            user_id=user_id,
            qa_simulation=qa_simulation,
            create_source_stubs=create_stubs,
            now=now,
        )
        detected, normalized, unknown = _normalize_headers(raw_headers)

        job_rec = {
            "import_job_id":     job_id,
            "request_id":        request_id,
            "created_at":        now,
            "created_by":        user_id,
            "original_filename": orig_name,
            "file_ext":          ext,
            "import_type":       import_type,
            "sheet_names":       sheet_names,
            "selected_sheet":    selected_sheet,
            "detected_columns":  detected,
            "normalized_columns": normalized,
            "unknown_columns":   unknown,
            "row_count":         len(raw_rows),
            "staged_rows_count": len(staged),
            "rejected_rows_count": len(rejected),
            "warnings":          job_warnings,
            "errors":            [],
            "status":            "staged",
            "comparable_type_hint": comp_type_hint,
            "qa_simulation":     qa_simulation,
            "external_api_used": False,
            "qdrant_used":       False,
            "rag_used":          False,
        }
        _persist_job(request_id, job_rec)

        _append_event(
            request_id=request_id, actor=user_id,
            action="comparable_import",
            from_status="", to_status="staged",
            note=f"import_job_id={job_id} staged={len(staged)} rejected={len(rejected)}",
            metadata={"import_job_id": job_id},
        )

        valuation_purpose = req_rec.get("valuation_purpose", "")
        readiness = evaluate_comparable_readiness(request_id, valuation_purpose)

        return jsonify({
            "ok":                    True,
            "import_job":            _job_safe(job_rec),
            "staged_comparables":    staged,
            "rejected_rows":         rejected,
            "comparable_readiness":  readiness,
            "certification_gate_summary": _gate_summary_with_comparables(request_id, valuation_purpose),
        }), 201

    # ── GET /api/professional-valuation/requests/<id>/comparables/import-jobs
    @app.route(
        "/api/professional-valuation/requests/<request_id>/comparables/import-jobs",
        methods=["GET"],
    )
    @require_auth
    def pv_list_import_jobs(request_id: str):
        if not _PVR_RE.match(request_id):
            return jsonify({"ok": False, "error": "رقم الطلب غير صالح"}), 400
        req_rec = _read_pvr(request_id)
        if req_rec is None:
            return jsonify({"ok": False, "error": "الطلب غير موجود"}), 404
        jobs = _load_jobs(request_id)
        return jsonify({"ok": True, "import_jobs": [_job_safe(j) for j in jobs]}), 200

    # ── GET /api/professional-valuation/requests/<id>/comparables/import-jobs/<job_id>
    @app.route(
        "/api/professional-valuation/requests/<request_id>/comparables/import-jobs/<job_id>",
        methods=["GET"],
    )
    @require_auth
    def pv_get_import_job(request_id: str, job_id: str):
        if not _PVR_RE.match(request_id):
            return jsonify({"ok": False, "error": "رقم الطلب غير صالح"}), 400
        if not _PVIJ_ID_RE.match(job_id):
            return jsonify({"ok": False, "error": "معرّف مهمة الاستيراد غير صالح"}), 400
        req_rec = _read_pvr(request_id)
        if req_rec is None:
            return jsonify({"ok": False, "error": "الطلب غير موجود"}), 404
        job = _read_job(request_id, job_id)
        if job is None:
            return jsonify({"ok": False, "error": "مهمة الاستيراد غير موجودة"}), 404
        return jsonify({"ok": True, "import_job": _job_safe(job)}), 200

    # ── POST /api/professional-valuation/requests/<id>/comparables/import-jobs/<job_id>/cancel
    @app.route(
        "/api/professional-valuation/requests/<request_id>/comparables/import-jobs/<job_id>/cancel",
        methods=["POST"],
    )
    @require_auth
    def pv_cancel_import_job(request_id: str, job_id: str):
        if not _PVR_RE.match(request_id):
            return jsonify({"ok": False, "error": "رقم الطلب غير صالح"}), 400
        if not _PVIJ_ID_RE.match(job_id):
            return jsonify({"ok": False, "error": "معرّف مهمة الاستيراد غير صالح"}), 400
        req_rec = _read_pvr(request_id)
        if req_rec is None:
            return jsonify({"ok": False, "error": "الطلب غير موجود"}), 404
        job = _read_job(request_id, job_id)
        if job is None:
            return jsonify({"ok": False, "error": "مهمة الاستيراد غير موجودة"}), 404
        curr_status = job.get("status", "")
        if curr_status in ("staged",):
            return jsonify({
                "ok":    False,
                "error": "لا يمكن إلغاء مهمة تم تنظيمها — المقارنات تم إنشاؤها بالفعل.",
            }), 422
        if curr_status == "cancelled":
            return jsonify({"ok": True, "import_job": _job_safe(job)}), 200

        _update_job(request_id, job_id, {"status": "cancelled"})
        updated = _read_job(request_id, job_id)
        return jsonify({"ok": True, "import_job": _job_safe(updated)}), 200


# ── Gate integration helper (called by routes module) ────────────────────────

def _gate_summary_with_comparables(request_id: str, valuation_purpose: str) -> dict:
    """Return Phase C gate summary merged with Phase D comparable readiness."""
    try:
        from professional_valuation_evidence_routes import compute_gate_summary
        gate = compute_gate_summary(request_id, valuation_purpose)
    except ImportError:
        gate = {
            "certification_ready": False,
            "qa_data_cleared": False,
            "real_sources_ready": False,
            "mandatory_documents_ready": False,
            "legal_due_diligence_ready": False,
            "hbu_completed": False,
            "methods_completed": False,
            "reconciliation_completed": False,
            "peer_review_completed": False,
            "expert_signature_ready": False,
            "blockers": [],
            "advisory_only_reason": "Phase D",
        }

    cr = evaluate_comparable_readiness(request_id, valuation_purpose)
    gate["comparables_ready"]  = cr["certification_comparable_ready"]
    gate["certification_ready"] = False  # always False in Phase D

    if not cr["certification_comparable_ready"]:
        blocker = "لا توجد مقارنات إنتاجية معتمدة."
        if blocker not in gate.get("blockers", []):
            gate.setdefault("blockers", []).append(blocker)

    gate["advisory_only_reason"] = (
        "Phase D — comparables staged for expert review only. "
        "Certified report generation is a later phase."
    )
    return gate
