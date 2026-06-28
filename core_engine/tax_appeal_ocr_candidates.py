# -*- coding: utf-8 -*-
"""
tax_appeal_ocr_candidates.py — Regex-based field candidate extraction from OCR text.

Rules (always enforced):
  - accepted_by_default = False  (every candidate requires human review)
  - needs_human_review  = True   (every candidate)
  - confidence is advisory only — do not trust blindly
  - Candidate values must not enter report context until reviewed and confirmed
  - Do not fail if pattern does not match — return empty candidate list
"""
from __future__ import annotations

import re
from typing import Optional


# ── Helpers ───────────────────────────────────────────────────────────────────

def _candidate(field_key: str, label_ar: str, value: str,
                confidence: float, snippet: str, method: str) -> dict:
    return {
        "field_key":           field_key,
        "label_ar":            label_ar,
        "candidate_value":     value,
        "confidence":          min(1.0, max(0.0, confidence)),
        "extraction_method":   method,
        "source_snippet":      snippet[:200],
        "needs_human_review":  True,
        "accepted_by_default": False,
    }


def _first_match(pattern: str, text: str,
                 group: int = 1, flags: int = re.MULTILINE) -> Optional[tuple[str, str]]:
    """Return (matched_value, surrounding_snippet) or None."""
    m = re.search(pattern, text, flags)
    if m:
        start = max(0, m.start() - 40)
        end   = min(len(text), m.end() + 40)
        return m.group(group).strip(), text[start:end].replace("\n", " ")
    return None


def _clean_number(raw: str) -> str:
    """Normalise Arabic/Eastern digits to Western and strip whitespace."""
    table = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    return raw.translate(table).replace(",", "").replace("،", "").strip()


def _clean_date(raw: str) -> str:
    """Return cleaned date string (DD/MM/YYYY or similar)."""
    return raw.strip().replace("\\", "/").replace("-", "/")


# ── Template-specific extractors ──────────────────────────────────────────────

def _extract_tax_notice_form3(text: str) -> list[dict]:
    candidates: list[dict] = []

    # tax_notice_number
    m = _first_match(r"(?:رقم الإشعار|رقم النموذج|رقم المطالبة)[:\s]*([0-9٠-٩/\-]+)", text)
    if m:
        candidates.append(_candidate(
            "tax_notice_number", "رقم إشعار الضريبة",
            _clean_number(m[0]), 0.75, m[1], "regex_tax_notice_number"))

    # notice_issue_date
    m = _first_match(
        r"(?:تاريخ الإشعار|تاريخ الإصدار|صادر في|تاريخ الإرسال)[:\s]*"
        r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|[٠-٩]{1,2}[/\-][٠-٩]{1,2}[/\-][٠-٩]{2,4})",
        text)
    if m:
        candidates.append(_candidate(
            "notice_issue_date", "تاريخ إصدار الإشعار",
            _clean_date(m[0]), 0.70, m[1], "regex_date"))

    # notice_received_date
    m = _first_match(
        r"(?:تاريخ الاستلام|استُلم في|تاريخ التسليم)[:\s]*"
        r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
        text)
    if m:
        candidates.append(_candidate(
            "notice_received_date", "تاريخ الاستلام",
            _clean_date(m[0]), 0.65, m[1], "regex_date"))

    # tax_assessment_basis_date
    m = _first_match(
        r"(?:تاريخ الحصر|تاريخ الأساس|تاريخ التقييم الضريبي|آخر تاريخ حصر)[:\s]*"
        r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
        text)
    if m:
        candidates.append(_candidate(
            "tax_assessment_basis_date", "تاريخ أساس التقييم الضريبي",
            _clean_date(m[0]), 0.70, m[1], "regex_date"))

    # tax_cycle_year
    m = _first_match(r"(?:الدورة الضريبية|سنة الضريبة|العام الضريبي)[:\s]*([0-9٠-٩]{4})", text)
    if m:
        candidates.append(_candidate(
            "tax_cycle_year", "سنة الدورة الضريبية",
            _clean_number(m[0]), 0.80, m[1], "regex_year"))

    # government_tax_amount
    m = _first_match(
        r"(?:مبلغ الضريبة|الضريبة المستحقة|إجمالي الضريبة)[:\s]*"
        r"([0-9٠-٩,،\.]+(?:\s*جنيه)?)",
        text)
    if m:
        candidates.append(_candidate(
            "government_tax_amount", "مبلغ الضريبة الحكومي",
            _clean_number(m[0]), 0.75, m[1], "regex_amount"))

    # government_annual_rental_value
    m = _first_match(
        r"(?:القيمة الإيجارية السنوية|الإيجار السنوي الحكومي|القيمة الإيجارية)[:\s]*"
        r"([0-9٠-٩,،\.]+)",
        text)
    if m:
        candidates.append(_candidate(
            "government_annual_rental_value", "القيمة الإيجارية السنوية الحكومية",
            _clean_number(m[0]), 0.70, m[1], "regex_amount"))

    # government_assessed_value
    m = _first_match(
        r"(?:القيمة التقديرية|قيمة العقار المقدَّرة|التقييم الحكومي)[:\s]*"
        r"([0-9٠-٩,،\.]+)",
        text)
    if m:
        candidates.append(_candidate(
            "government_assessed_value", "القيمة التقديرية الحكومية",
            _clean_number(m[0]), 0.70, m[1], "regex_amount"))

    # tax_authority_office
    m = _first_match(
        r"(?:مأمورية|إدارة الضرائب|مكتب الضرائب|جهة الضريبة)[:\s]*([^\n]{3,60})", text)
    if m:
        candidates.append(_candidate(
            "tax_authority_office", "مأمورية الضرائب",
            m[0].strip(), 0.65, m[1], "regex_text"))

    # property_tax_account_number
    m = _first_match(
        r"(?:رقم الحساب الضريبي|حساب العقار|رقم الملف الضريبي)[:\s]*([0-9٠-٩/\-]+)", text)
    if m:
        candidates.append(_candidate(
            "property_tax_account_number", "رقم الحساب الضريبي للعقار",
            _clean_number(m[0]), 0.75, m[1], "regex_account"))

    return candidates


def _extract_ownership_document(text: str) -> list[dict]:
    candidates: list[dict] = []

    m = _first_match(r"(?:اسم المالك|المالك|صاحب العقار)[:\s]*([^\n]{3,60})", text)
    if m:
        candidates.append(_candidate(
            "owner_name", "اسم المالك",
            m[0].strip(), 0.65, m[1], "regex_text"))

    m = _first_match(r"(?:العنوان|عنوان العقار|الموقع)[:\s]*([^\n]{5,100})", text)
    if m:
        candidates.append(_candidate(
            "property_address", "عنوان العقار",
            m[0].strip(), 0.60, m[1], "regex_text"))

    m = _first_match(
        r"(?:المساحة|مساحة العقار)[:\s]*([0-9٠-٩,،\.]+(?:\s*(?:م2|م²|متر مربع))?)", text)
    if m:
        candidates.append(_candidate(
            "property_area", "مساحة العقار",
            _clean_number(m[0]), 0.70, m[1], "regex_area"))

    m = _first_match(
        r"(?:رقم الوثيقة|رقم سند الملكية|رقم العقد)[:\s]*([0-9٠-٩/\-]+)", text)
    if m:
        candidates.append(_candidate(
            "ownership_document_number", "رقم وثيقة الملكية",
            _clean_number(m[0]), 0.75, m[1], "regex_id"))

    m = _first_match(
        r"(?:تاريخ الوثيقة|تاريخ العقد|تاريخ التسجيل)[:\s]*"
        r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
        text)
    if m:
        candidates.append(_candidate(
            "ownership_date", "تاريخ وثيقة الملكية",
            _clean_date(m[0]), 0.70, m[1], "regex_date"))

    return candidates


def _extract_activity_license(text: str) -> list[dict]:
    candidates: list[dict] = []

    m = _first_match(r"(?:النشاط المرخَّص|نوع النشاط|الاستخدام المرخص)[:\s]*([^\n]{3,80})", text)
    if m:
        candidates.append(_candidate(
            "licensed_use", "الاستخدام المرخَّص",
            m[0].strip(), 0.65, m[1], "regex_text"))

    m = _first_match(
        r"(?:رقم الترخيص|رقم ترخيص النشاط)[:\s]*([0-9٠-٩/\-]+)", text)
    if m:
        candidates.append(_candidate(
            "activity_license_number", "رقم ترخيص النشاط",
            _clean_number(m[0]), 0.75, m[1], "regex_id"))

    m = _first_match(
        r"(?:تاريخ الإصدار|صادر في|تاريخ الترخيص)[:\s]*"
        r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
        text)
    if m:
        candidates.append(_candidate(
            "issue_date", "تاريخ الإصدار",
            _clean_date(m[0]), 0.70, m[1], "regex_date"))

    m = _first_match(r"(?:الجهة المصدرة|صادر من|الجهة)[:\s]*([^\n]{3,60})", text)
    if m:
        candidates.append(_candidate(
            "issuer", "الجهة المصدرة",
            m[0].strip(), 0.60, m[1], "regex_text"))

    return candidates


def _extract_industrial_license(text: str) -> list[dict]:
    candidates: list[dict] = []

    m = _first_match(
        r"(?:رقم الترخيص الصناعي|رقم الترخيص)[:\s]*([0-9٠-٩/\-]+)", text)
    if m:
        candidates.append(_candidate(
            "industrial_license_number", "رقم الترخيص الصناعي",
            _clean_number(m[0]), 0.75, m[1], "regex_id"))

    m = _first_match(r"(?:النشاط الصناعي|نوع الصناعة|الصناعة)[:\s]*([^\n]{3,80})", text)
    if m:
        candidates.append(_candidate(
            "factory_activity", "النشاط الصناعي",
            m[0].strip(), 0.65, m[1], "regex_text"))

    m = _first_match(r"(?:المنطقة الصناعية|الموقع الصناعي)[:\s]*([^\n]{3,60})", text)
    if m:
        candidates.append(_candidate(
            "industrial_zone", "المنطقة الصناعية",
            m[0].strip(), 0.60, m[1], "regex_text"))

    m = _first_match(
        r"(?:المساحة المرخصة|مساحة المصنع)[:\s]*([0-9٠-٩,،\.]+(?:\s*م2)?)", text)
    if m:
        candidates.append(_candidate(
            "licensed_area", "المساحة المرخَّصة",
            _clean_number(m[0]), 0.70, m[1], "regex_area"))

    return candidates


def _extract_factory_cost(text: str) -> list[dict]:
    candidates: list[dict] = []
    _cost_pattern = r"([0-9٠-٩,،\.]+(?:\s*جنيه)?(?:/م2)?)"

    m = _first_match(
        r"(?:تكلفة مبنى الإنتاج|تكلفة الإنتاج)[:\s]*" + _cost_pattern, text)
    if m:
        candidates.append(_candidate(
            "production_building_cost_per_m2", "تكلفة مبنى الإنتاج للمتر المربع",
            _clean_number(m[0]), 0.70, m[1], "regex_amount"))

    m = _first_match(
        r"(?:تكلفة المستودعات?|تكلفة المخازن?)[:\s]*" + _cost_pattern, text)
    if m:
        candidates.append(_candidate(
            "warehouse_cost_per_m2", "تكلفة المستودع للمتر المربع",
            _clean_number(m[0]), 0.70, m[1], "regex_amount"))

    m = _first_match(
        r"(?:تكلفة المبنى الإداري|تكلفة الإدارة)[:\s]*" + _cost_pattern, text)
    if m:
        candidates.append(_candidate(
            "admin_building_cost_per_m2", "تكلفة المبنى الإداري للمتر المربع",
            _clean_number(m[0]), 0.70, m[1], "regex_amount"))

    m = _first_match(r"(?:العمر الافتراضي|العمر الإنتاجي)[:\s]*([0-9٠-٩]+(?:\s*(?:سنة|عام))?)", text)
    if m:
        candidates.append(_candidate(
            "useful_life_years", "العمر الافتراضي بالسنوات",
            _clean_number(m[0]), 0.75, m[1], "regex_number"))

    m = _first_match(
        r"(?:معدل الاستهلاك السنوي|نسبة الاستهلاك)[:\s]*([0-9٠-٩,\.]+(?:\s*%)?)", text)
    if m:
        candidates.append(_candidate(
            "annual_depreciation_rate", "معدل الاستهلاك السنوي",
            _clean_number(m[0]), 0.70, m[1], "regex_percent"))

    m = _first_match(r"(?:مصدر الدليل|الدليل|جهة الإصدار)[:\s]*([^\n]{3,80})", text)
    if m:
        candidates.append(_candidate(
            "guidance_source_name", "اسم مصدر الدليل",
            m[0].strip(), 0.60, m[1], "regex_text"))

    return candidates


# ── Dispatcher ────────────────────────────────────────────────────────────────

_EXTRACTORS = {
    "tax_notice_form3":               _extract_tax_notice_form3,
    "ownership_document":             _extract_ownership_document,
    "activity_license":               _extract_activity_license,
    "industrial_license":             _extract_industrial_license,
    "factory_cost_guidance":          _extract_factory_cost,
    "ain_shams_factory_cost_reference": _extract_factory_cost,
    "nuca_land_price_reference":      _extract_factory_cost,   # same cost-like fields
}


def build_ocr_field_candidates(
    ocr_text: str,
    evidence_type: str,
    template_id: Optional[str] = None,
) -> dict:
    """
    Extract advisory field candidates from raw OCR text.

    All candidates have:
      accepted_by_default = False
      needs_human_review  = True

    Returns safe empty dict on any failure.
    """
    candidates: list[dict] = []
    warnings: list[str]    = []

    if not ocr_text or not ocr_text.strip():
        warnings.append("النص الخام فارغ — لا يمكن استخراج مرشحين.")
        return {
            "evidence_type":      evidence_type,
            "template_id":        template_id,
            "candidates":         [],
            "confidence_summary": {"overall": 0.0, "count": 0},
            "warnings":           warnings,
        }

    extractor = _EXTRACTORS.get(evidence_type)
    if extractor is None:
        warnings.append(
            f"نوع المستند '{evidence_type}' لا يحتوي على مستخرج مرشحين مُعرَّف. "
            "يُرجى الإدخال اليدوي."
        )
    else:
        try:
            candidates = extractor(ocr_text)
        except Exception as exc:
            warnings.append(f"خطأ في استخراج المرشحين: {exc}")

    # Enforce invariants
    for c in candidates:
        c["accepted_by_default"] = False
        c["needs_human_review"]  = True

    avg_conf = (
        sum(c["confidence"] for c in candidates) / len(candidates)
        if candidates else 0.0
    )

    return {
        "evidence_type":      evidence_type,
        "template_id":        template_id,
        "candidates":         candidates,
        "confidence_summary": {
            "overall": round(avg_conf, 3),
            "count":   len(candidates),
        },
        "warnings": warnings,
    }
