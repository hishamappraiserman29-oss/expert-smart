# -*- coding: utf-8 -*-
"""
tax_appeal_ocr_candidates.py — Regex-based field candidate extraction from OCR text.

Rules (always enforced):
  - accepted_by_default   = False  (every candidate requires human review)
  - needs_human_review    = True   (every candidate)
  - production_ready      = False  (every candidate)
  - preliminary_visible   = True   (advisory display allowed)
  - expert_review_visible = True
  - certified_usage_allowed = False (until expert confirms, maps, checks conflicts, overlays)
  - confidence is advisory only — do not trust blindly
  - Candidate values must not enter report context until reviewed and confirmed
  - Do not fail if pattern does not match — return doc-level summary row
  - Image-only evidence: extract visible text only, no inferred measurements or legal facts
  - Structured evidence (Excel/CSV): produce placeholder only, no OCR
"""
from __future__ import annotations

import re
from typing import Optional


# ── Constants ─────────────────────────────────────────────────────────────────

_ADVISORY_LABEL = "قراءة آلية مبدئية — غير معتمدة"

# Image-only evidence types — OCR extracts visible text only
_IMAGE_ONLY_TYPES: frozenset[str] = frozenset({
    "property_photos", "floor_plan", "map_or_aerial_image",
})

# Structured data types — separate parser required, not OCR
_STRUCTURED_TYPES: frozenset[str] = frozenset({
    "market_comparables_excel", "rental_comparables_excel", "tax_comparables_excel",
})

_IMAGE_TEXT_WARNING = (
    "قراءة نصوص ظاهرة فقط — لا يتم استنتاج المساحات أو الحالة الفنية من الصورة تلقائيًا."
)
_STRUCTURED_WARNING = (
    "ملف منظم — يحتاج مسار استخلاص جدولي منفصل، ولا يعالج كـ OCR."
)


# ── Core helpers ──────────────────────────────────────────────────────────────

def _candidate(
    field_key: str,
    label_ar: str,
    value: str,
    confidence: float,
    snippet: str,
    method: str,
    value_type: str = "text",
    warning: str = "",
) -> dict:
    return {
        "field_key":               field_key,
        "label_ar":                label_ar,
        "candidate_value":         value,
        "value_type":              value_type,
        "confidence":              min(1.0, max(0.0, confidence)),
        "extraction_method":       method,
        "source_snippet":          snippet[:200],
        "needs_human_review":      True,
        "accepted_by_default":     False,
        "production_ready":        False,
        "preliminary_visible":     True,
        "expert_review_visible":   True,
        "certified_usage_allowed": False,
        "advisory_label_ar":       _ADVISORY_LABEL,
        "warning":                 warning,
    }


def _doc_level_summary(evidence_type: str, note: str, warning: str = "") -> dict:
    """Return a document-level advisory summary row when no field candidates found."""
    return _candidate(
        "doc_level_summary", "ملخص قراءة المستند",
        note, 0.0, "", "doc_level_fallback",
        warning=warning,
    )


def _first_match(
    pattern: str, text: str, group: int = 1, flags: int = re.MULTILINE,
) -> Optional[tuple[str, str]]:
    m = re.search(pattern, text, flags)
    if m:
        start = max(0, m.start() - 40)
        end   = min(len(text), m.end() + 40)
        return m.group(group).strip(), text[start:end].replace("\n", " ")
    return None


def _clean_number(raw: str) -> str:
    table = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    return raw.translate(table).replace(",", "").replace("،", "").strip()


def _clean_date(raw: str) -> str:
    return raw.strip().replace("\\", "/").replace("-", "/")


# ── Extractors — one per evidence type ───────────────────────────────────────

def _extract_tax_notice_form3(text: str) -> list[dict]:
    c: list[dict] = []

    m = _first_match(r"(?:رقم الإشعار|رقم النموذج|رقم المطالبة)[:\s]*([0-9٠-٩/\-]+)", text)
    if m:
        c.append(_candidate("tax_notice_number", "رقم إشعار الضريبة",
                            _clean_number(m[0]), 0.75, m[1], "regex_id", "id"))

    m = _first_match(
        r"(?:تاريخ الإشعار|تاريخ الإصدار|صادر في|تاريخ الإرسال)[:\s]*"
        r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|[٠-٩]{1,2}[/\-][٠-٩]{1,2}[/\-][٠-٩]{2,4})", text)
    if m:
        c.append(_candidate("notice_issue_date", "تاريخ إصدار الإشعار",
                            _clean_date(m[0]), 0.70, m[1], "regex_date", "date"))

    m = _first_match(
        r"(?:تاريخ الاستلام|استُلم في|تاريخ التسليم)[:\s]*"
        r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})", text)
    if m:
        c.append(_candidate("notice_received_date", "تاريخ الاستلام",
                            _clean_date(m[0]), 0.65, m[1], "regex_date", "date"))

    m = _first_match(
        r"(?:تاريخ الحصر|تاريخ الأساس|تاريخ التقييم الضريبي|آخر تاريخ حصر)[:\s]*"
        r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})", text)
    if m:
        c.append(_candidate("tax_assessment_basis_date", "تاريخ أساس التقييم الضريبي",
                            _clean_date(m[0]), 0.70, m[1], "regex_date", "date"))

    m = _first_match(r"(?:الدورة الضريبية|سنة الضريبة|العام الضريبي)[:\s]*([0-9٠-٩]{4})", text)
    if m:
        c.append(_candidate("tax_cycle_year", "سنة الدورة الضريبية",
                            _clean_number(m[0]), 0.80, m[1], "regex_year", "number"))

    m = _first_match(
        r"(?:مبلغ الضريبة|الضريبة المستحقة|إجمالي الضريبة)[:\s]*"
        r"([0-9٠-٩,،\.]+(?:\s*جنيه)?)", text)
    if m:
        c.append(_candidate("government_tax_amount", "مبلغ الضريبة الحكومي",
                            _clean_number(m[0]), 0.75, m[1], "regex_amount", "amount"))

    m = _first_match(
        r"(?:القيمة الإيجارية السنوية|الإيجار السنوي الحكومي|القيمة الإيجارية)[:\s]*"
        r"([0-9٠-٩,،\.]+)", text)
    if m:
        c.append(_candidate("government_annual_rental_value", "القيمة الإيجارية السنوية الحكومية",
                            _clean_number(m[0]), 0.70, m[1], "regex_amount", "amount"))

    m = _first_match(
        r"(?:القيمة التقديرية|قيمة العقار المقدَّرة|التقييم الحكومي)[:\s]*"
        r"([0-9٠-٩,،\.]+)", text)
    if m:
        c.append(_candidate("government_assessed_value", "القيمة التقديرية الحكومية",
                            _clean_number(m[0]), 0.70, m[1], "regex_amount", "amount"))

    m = _first_match(
        r"(?:مأمورية|إدارة الضرائب|مكتب الضرائب|جهة الضريبة)[:\s]*([^\n]{3,60})", text)
    if m:
        c.append(_candidate("tax_authority_office", "مأمورية الضرائب",
                            m[0].strip(), 0.65, m[1], "regex_text"))

    m = _first_match(
        r"(?:رقم الحساب الضريبي|حساب العقار|رقم الملف الضريبي)[:\s]*([0-9٠-٩/\-]+)", text)
    if m:
        c.append(_candidate("property_tax_account_number", "رقم الحساب الضريبي للعقار",
                            _clean_number(m[0]), 0.75, m[1], "regex_id", "id"))
    return c


def _extract_ownership_document(text: str) -> list[dict]:
    c: list[dict] = []

    m = _first_match(r"(?:اسم المالك|المالك|صاحب العقار)[:\s]*([^\n]{3,60})", text)
    if m:
        c.append(_candidate("owner_name", "اسم المالك", m[0].strip(), 0.65, m[1], "regex_text"))

    m = _first_match(r"(?:اسم المتقدم|اسم المستأجر|الممثل القانوني)[:\s]*([^\n]{3,60})", text)
    if m:
        c.append(_candidate("taxpayer_name", "اسم صاحب الطلب", m[0].strip(), 0.60, m[1], "regex_text"))

    m = _first_match(r"(?:العنوان|عنوان العقار|الموقع)[:\s]*([^\n]{5,100})", text)
    if m:
        c.append(_candidate("property_address", "عنوان العقار", m[0].strip(), 0.60, m[1], "regex_text"))

    m = _first_match(
        r"(?:المساحة الكلية|مساحة العقار|المساحة)[:\s]*"
        r"([0-9٠-٩,،\.]+(?:\s*(?:م2|م²|متر مربع))?)", text)
    if m:
        c.append(_candidate("property_area", "مساحة العقار",
                            _clean_number(m[0]), 0.70, m[1], "regex_area", "area"))

    m = _first_match(
        r"(?:مساحة الأرض|مساحة قطعة الأرض)[:\s]*([0-9٠-٩,،\.]+(?:\s*م2)?)", text)
    if m:
        c.append(_candidate("land_area", "مساحة الأرض",
                            _clean_number(m[0]), 0.68, m[1], "regex_area", "area"))

    m = _first_match(r"(?:رقم الوحدة|رقم الشقة)[:\s]*([0-9٠-٩/\-]+)", text)
    if m:
        c.append(_candidate("unit_number", "رقم الوحدة",
                            _clean_number(m[0]), 0.70, m[1], "regex_id", "id"))

    m = _first_match(r"(?:رقم المبنى|رقم العقار)[:\s]*([0-9٠-٩/\-]+)", text)
    if m:
        c.append(_candidate("building_number", "رقم المبنى",
                            _clean_number(m[0]), 0.70, m[1], "regex_id", "id"))

    m = _first_match(r"(?:نوع الملكية|شكل الملكية)[:\s]*([^\n]{3,60})", text)
    if m:
        c.append(_candidate("ownership_type", "نوع الملكية", m[0].strip(), 0.60, m[1], "regex_text"))

    m = _first_match(
        r"(?:رقم الوثيقة|رقم سند الملكية|رقم العقد)[:\s]*([0-9٠-٩/\-]+)", text)
    if m:
        c.append(_candidate("ownership_document_number", "رقم وثيقة الملكية",
                            _clean_number(m[0]), 0.75, m[1], "regex_id", "id"))

    m = _first_match(
        r"(?:تاريخ الوثيقة|تاريخ العقد|تاريخ التسجيل)[:\s]*"
        r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})", text)
    if m:
        c.append(_candidate("ownership_date", "تاريخ وثيقة الملكية",
                            _clean_date(m[0]), 0.70, m[1], "regex_date", "date"))

    m = _first_match(r"(?:نزاع قانوني|حالة النزاع|طعن قانوني)[:\s]*([^\n]{3,80})", text)
    if m:
        c.append(_candidate("legal_dispute_status", "حالة النزاع القانوني",
                            m[0].strip(), 0.55, m[1], "regex_text"))
    return c


def _extract_lease_contract(text: str) -> list[dict]:
    c: list[dict] = []

    m = _first_match(r"(?:اسم المستأجر|المستأجر)[:\s]*([^\n]{3,60})", text)
    if m:
        c.append(_candidate("tenant_name", "اسم المستأجر", m[0].strip(), 0.65, m[1], "regex_text"))

    m = _first_match(
        r"(?:تاريخ بداية الإيجار|تاريخ بدء العقد|بداية الإيجار)[:\s]*"
        r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})", text)
    if m:
        c.append(_candidate("lease_start_date", "تاريخ بداية الإيجار",
                            _clean_date(m[0]), 0.70, m[1], "regex_date", "date"))

    m = _first_match(
        r"(?:تاريخ نهاية الإيجار|تاريخ انتهاء العقد|نهاية الإيجار)[:\s]*"
        r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})", text)
    if m:
        c.append(_candidate("lease_end_date", "تاريخ نهاية الإيجار",
                            _clean_date(m[0]), 0.70, m[1], "regex_date", "date"))

    m = _first_match(
        r"(?:الإيجار الشهري|القسط الشهري|الإيجار شهريًا)[:\s]*"
        r"([0-9٠-٩,،\.]+(?:\s*جنيه)?)", text)
    if m:
        c.append(_candidate("monthly_rent", "الإيجار الشهري",
                            _clean_number(m[0]), 0.75, m[1], "regex_amount", "amount"))

    m = _first_match(
        r"(?:الإيجار السنوي|القيمة الإيجارية السنوية)[:\s]*"
        r"([0-9٠-٩,،\.]+(?:\s*جنيه)?)", text)
    if m:
        c.append(_candidate("annual_rent", "الإيجار السنوي",
                            _clean_number(m[0]), 0.75, m[1], "regex_amount", "amount"))

    m = _first_match(
        r"(?:مساحة المأجور|المساحة المؤجرة)[:\s]*([0-9٠-٩,،\.]+(?:\s*م2)?)", text)
    if m:
        c.append(_candidate("leased_area", "المساحة المؤجرة",
                            _clean_number(m[0]), 0.70, m[1], "regex_area", "area"))

    m = _first_match(r"(?:الغرض من الإيجار|نوع الاستخدام|الاستخدام)[:\s]*([^\n]{3,60})", text)
    if m:
        c.append(_candidate("use_type", "نوع الاستخدام", m[0].strip(), 0.60, m[1], "regex_text"))

    m = _first_match(r"(?:زيادة الإيجار|شرط الزيادة|تصعيد الإيجار)[:\s]*([^\n]{3,80})", text)
    if m:
        c.append(_candidate("rent_escalation_clause", "شرط تصعيد الإيجار",
                            m[0].strip(), 0.55, m[1], "regex_text"))
    return c


def _extract_activity_license(text: str) -> list[dict]:
    c: list[dict] = []

    m = _first_match(r"(?:النشاط المرخَّص|نوع النشاط|الاستخدام المرخص)[:\s]*([^\n]{3,80})", text)
    if m:
        c.append(_candidate("licensed_use", "الاستخدام المرخَّص", m[0].strip(), 0.65, m[1], "regex_text"))

    m = _first_match(r"(?:نوع النشاط|النشاط التجاري)[:\s]*([^\n]{3,80})", text)
    if m:
        c.append(_candidate("activity_type", "نوع النشاط", m[0].strip(), 0.65, m[1], "regex_text"))

    m = _first_match(r"(?:رقم الترخيص|رقم ترخيص النشاط)[:\s]*([0-9٠-٩/\-]+)", text)
    if m:
        c.append(_candidate("activity_license_number", "رقم ترخيص النشاط",
                            _clean_number(m[0]), 0.75, m[1], "regex_id", "id"))

    m = _first_match(
        r"(?:تاريخ الإصدار|صادر في|تاريخ الترخيص)[:\s]*"
        r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})", text)
    if m:
        c.append(_candidate("activity_license_date", "تاريخ إصدار الترخيص",
                            _clean_date(m[0]), 0.70, m[1], "regex_date", "date"))

    m = _first_match(r"(?:الجهة المصدرة|صادر من|الجهة)[:\s]*([^\n]{3,60})", text)
    if m:
        c.append(_candidate("issuer", "الجهة المصدرة", m[0].strip(), 0.60, m[1], "regex_text"))

    m = _first_match(
        r"(?:تاريخ الانتهاء|صالح حتى|ينتهي في)[:\s]*"
        r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})", text)
    if m:
        c.append(_candidate("expiry_date", "تاريخ انتهاء الترخيص",
                            _clean_date(m[0]), 0.68, m[1], "regex_date", "date"))
    return c


def _extract_commercial_register(text: str) -> list[dict]:
    c: list[dict] = []

    m = _first_match(r"(?:رقم السجل التجاري|السجل التجاري)[:\s]*([0-9٠-٩/\-]+)", text)
    if m:
        c.append(_candidate("commercial_register_number", "رقم السجل التجاري",
                            _clean_number(m[0]), 0.80, m[1], "regex_id", "id"))

    m = _first_match(r"(?:اسم الشركة|اسم المنشأة|المتقدم)[:\s]*([^\n]{3,80})", text)
    if m:
        c.append(_candidate("taxpayer_name", "اسم الشركة / المنشأة",
                            m[0].strip(), 0.65, m[1], "regex_text"))

    m = _first_match(r"(?:نوع النشاط|الغرض التجاري)[:\s]*([^\n]{3,80})", text)
    if m:
        c.append(_candidate("activity_type", "نوع النشاط", m[0].strip(), 0.65, m[1], "regex_text"))

    m = _first_match(
        r"(?:تاريخ التسجيل|تاريخ الإصدار)[:\s]*"
        r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})", text)
    if m:
        c.append(_candidate("issue_date", "تاريخ الإصدار",
                            _clean_date(m[0]), 0.70, m[1], "regex_date", "date"))

    m = _first_match(r"(?:الجهة المصدرة|مكتب السجل)[:\s]*([^\n]{3,60})", text)
    if m:
        c.append(_candidate("issuer", "الجهة المصدرة", m[0].strip(), 0.60, m[1], "regex_text"))
    return c


def _extract_industrial_license(text: str) -> list[dict]:
    c: list[dict] = []

    m = _first_match(r"(?:رقم الترخيص الصناعي|رقم الترخيص)[:\s]*([0-9٠-٩/\-]+)", text)
    if m:
        c.append(_candidate("industrial_license_number", "رقم الترخيص الصناعي",
                            _clean_number(m[0]), 0.75, m[1], "regex_id", "id"))

    m = _first_match(r"(?:النشاط الصناعي|نوع الصناعة|الصناعة)[:\s]*([^\n]{3,80})", text)
    if m:
        c.append(_candidate("factory_activity", "النشاط الصناعي",
                            m[0].strip(), 0.65, m[1], "regex_text"))

    m = _first_match(r"(?:الجهة المصدرة|صادر من)[:\s]*([^\n]{3,60})", text)
    if m:
        c.append(_candidate("issuer", "الجهة المصدرة", m[0].strip(), 0.60, m[1], "regex_text"))

    m = _first_match(
        r"(?:تاريخ الإصدار|صادر في)[:\s]*"
        r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})", text)
    if m:
        c.append(_candidate("issue_date", "تاريخ الإصدار",
                            _clean_date(m[0]), 0.70, m[1], "regex_date", "date"))

    m = _first_match(
        r"(?:تاريخ الانتهاء|صالح حتى)[:\s]*"
        r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})", text)
    if m:
        c.append(_candidate("expiry_date", "تاريخ انتهاء الترخيص",
                            _clean_date(m[0]), 0.68, m[1], "regex_date", "date"))

    m = _first_match(r"(?:المنطقة الصناعية|الموقع الصناعي)[:\s]*([^\n]{3,60})", text)
    if m:
        c.append(_candidate("industrial_zone", "المنطقة الصناعية",
                            m[0].strip(), 0.60, m[1], "regex_text"))

    m = _first_match(
        r"(?:المساحة المرخصة|مساحة المصنع)[:\s]*([0-9٠-٩,،\.]+(?:\s*م2)?)", text)
    if m:
        c.append(_candidate("licensed_area", "المساحة المرخَّصة",
                            _clean_number(m[0]), 0.70, m[1], "regex_area", "area"))
    return c


def _extract_land_allocation(text: str) -> list[dict]:
    c: list[dict] = []

    m = _first_match(r"(?:رقم قرار التخصيص|رقم التخصيص)[:\s]*([0-9٠-٩/\-]+)", text)
    if m:
        c.append(_candidate("land_allocation_number", "رقم قرار التخصيص",
                            _clean_number(m[0]), 0.75, m[1], "regex_id", "id"))

    m = _first_match(
        r"(?:مساحة الأرض|مساحة قطعة الأرض)[:\s]*([0-9٠-٩,،\.]+(?:\s*م2)?)", text)
    if m:
        c.append(_candidate("land_area", "مساحة الأرض",
                            _clean_number(m[0]), 0.70, m[1], "regex_area", "area"))

    m = _first_match(
        r"(?:سعر الأرض|ثمن الأرض|سعر المتر)[:\s]*"
        r"([0-9٠-٩,،\.]+(?:\s*(?:جنيه|جنيه/م))?)", text)
    if m:
        c.append(_candidate("land_price_per_m2", "سعر الأرض للمتر المربع",
                            _clean_number(m[0]), 0.68, m[1], "regex_amount", "amount"))

    m = _first_match(
        r"(?:تاريخ التخصيص|تاريخ القرار)[:\s]*"
        r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})", text)
    if m:
        c.append(_candidate("allocation_date", "تاريخ التخصيص",
                            _clean_date(m[0]), 0.70, m[1], "regex_date", "date"))

    m = _first_match(r"(?:جهة التخصيص|الجهة المصدرة|الهيئة)[:\s]*([^\n]{3,80})", text)
    if m:
        c.append(_candidate("issuing_authority", "جهة التخصيص",
                            m[0].strip(), 0.60, m[1], "regex_text"))

    m = _first_match(r"(?:المنطقة الصناعية|منطقة التخصيص)[:\s]*([^\n]{3,60})", text)
    if m:
        c.append(_candidate("industrial_zone", "المنطقة الصناعية",
                            m[0].strip(), 0.60, m[1], "regex_text"))

    m = _first_match(r"(?:قيود الاستخدام|الاشتراطات)[:\s]*([^\n]{3,100})", text)
    if m:
        c.append(_candidate("usage_restrictions", "قيود الاستخدام",
                            m[0].strip(), 0.55, m[1], "regex_text"))
    return c


def _extract_area_statement(text: str) -> list[dict]:
    c: list[dict] = []

    m = _first_match(
        r"(?:مساحة المبنى|مساحة المنشأة)[:\s]*([0-9٠-٩,،\.]+(?:\s*م2)?)", text)
    if m:
        c.append(_candidate("building_area", "مساحة المبنى",
                            _clean_number(m[0]), 0.70, m[1], "regex_area", "area"))

    m = _first_match(
        r"(?:مساحة الأرض|مساحة قطعة الأرض)[:\s]*([0-9٠-٩,،\.]+(?:\s*م2)?)", text)
    if m:
        c.append(_candidate("land_area", "مساحة الأرض",
                            _clean_number(m[0]), 0.70, m[1], "regex_area", "area"))

    m = _first_match(
        r"(?:مساحة الوحدة|مساحة الشقة)[:\s]*([0-9٠-٩,،\.]+(?:\s*م2)?)", text)
    if m:
        c.append(_candidate("unit_area", "مساحة الوحدة",
                            _clean_number(m[0]), 0.70, m[1], "regex_area", "area"))

    m = _first_match(
        r"(?:مساحة الدور|مساحة الطابق)[:\s]*([0-9٠-٩,،\.]+(?:\s*م2)?)", text)
    if m:
        c.append(_candidate("floor_area", "مساحة الطابق",
                            _clean_number(m[0]), 0.68, m[1], "regex_area", "area"))

    m = _first_match(
        r"(?:المساحة المقاسة|المساحة الفعلية)[:\s]*([0-9٠-٩,،\.]+(?:\s*م2)?)", text)
    if m:
        c.append(_candidate("measured_area", "المساحة المقاسة",
                            _clean_number(m[0]), 0.72, m[1], "regex_area", "area"))

    m = _first_match(r"(?:مصدر القياس|الجهة القائسة)[:\s]*([^\n]{3,80})", text)
    if m:
        c.append(_candidate("measurement_source", "مصدر القياس",
                            m[0].strip(), 0.60, m[1], "regex_text"))

    m = _first_match(
        r"(?:تاريخ القياس|تاريخ الرفع)[:\s]*"
        r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})", text)
    if m:
        c.append(_candidate("measurement_date", "تاريخ القياس",
                            _clean_date(m[0]), 0.68, m[1], "regex_date", "date"))
    return c


def _extract_building_permit(text: str) -> list[dict]:
    c: list[dict] = []

    m = _first_match(r"(?:رقم التصريح|رقم رخصة البناء|رقم الرخصة)[:\s]*([0-9٠-٩/\-]+)", text)
    if m:
        c.append(_candidate("permit_number", "رقم رخصة البناء",
                            _clean_number(m[0]), 0.78, m[1], "regex_id", "id"))

    m = _first_match(
        r"(?:تاريخ الترخيص|تاريخ الرخصة|تاريخ الإصدار)[:\s]*"
        r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})", text)
    if m:
        c.append(_candidate("permit_date", "تاريخ رخصة البناء",
                            _clean_date(m[0]), 0.72, m[1], "regex_date", "date"))

    m = _first_match(
        r"(?:مساحة البناء المرخَّص|مساحة البناء)[:\s]*([0-9٠-٩,،\.]+(?:\s*م2)?)", text)
    if m:
        c.append(_candidate("licensed_building_area", "مساحة البناء المرخَّصة",
                            _clean_number(m[0]), 0.70, m[1], "regex_area", "area"))

    m = _first_match(r"(?:عدد الأدوار|عدد الطوابق|الأدوار المرخَّصة)[:\s]*([0-9٠-٩]+)", text)
    if m:
        c.append(_candidate("number_of_floors", "عدد الأدوار المرخَّصة",
                            _clean_number(m[0]), 0.75, m[1], "regex_number", "number"))

    m = _first_match(r"(?:الاستخدام المرخَّص|الغرض المرخَّص)[:\s]*([^\n]{3,80})", text)
    if m:
        c.append(_candidate("permitted_use", "الاستخدام المرخَّص",
                            m[0].strip(), 0.65, m[1], "regex_text"))

    m = _first_match(r"(?:الجهة المصدرة|صادر من|الحي)[:\s]*([^\n]{3,60})", text)
    if m:
        c.append(_candidate("issuer", "الجهة المصدرة", m[0].strip(), 0.60, m[1], "regex_text"))
    return c


def _extract_occupancy_certificate(text: str) -> list[dict]:
    c: list[dict] = []

    m = _first_match(
        r"(?:رقم الشهادة|رقم الإفادة|رقم مستند الإشغال)[:\s]*([0-9٠-٩/\-]+)", text)
    if m:
        c.append(_candidate("certificate_number", "رقم الشهادة",
                            _clean_number(m[0]), 0.75, m[1], "regex_id", "id"))

    m = _first_match(
        r"(?:تاريخ إتمام البناء|تاريخ إتمام التشييد)[:\s]*"
        r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})", text)
    if m:
        c.append(_candidate("completion_date", "تاريخ إتمام البناء",
                            _clean_date(m[0]), 0.70, m[1], "regex_date", "date"))

    m = _first_match(
        r"(?:تاريخ الإشغال|بدء الإشغال)[:\s]*"
        r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})", text)
    if m:
        c.append(_candidate("occupancy_date", "تاريخ الإشغال",
                            _clean_date(m[0]), 0.70, m[1], "regex_date", "date"))

    m = _first_match(
        r"(?:مساحة المبنى|المساحة الإجمالية)[:\s]*([0-9٠-٩,،\.]+(?:\s*م2)?)", text)
    if m:
        c.append(_candidate("building_area", "مساحة المبنى",
                            _clean_number(m[0]), 0.68, m[1], "regex_area", "area"))

    m = _first_match(r"(?:الجهة المصدرة|صادر من)[:\s]*([^\n]{3,60})", text)
    if m:
        c.append(_candidate("issuer", "الجهة المصدرة", m[0].strip(), 0.60, m[1], "regex_text"))
    return c


def _extract_factory_cost_guidance(text: str) -> list[dict]:
    c: list[dict] = []
    _cost = r"([0-9٠-٩,،\.]+(?:\s*جنيه)?(?:/م2)?)"

    m = _first_match(r"(?:تكلفة مبنى الإنتاج|تكلفة الإنتاج)[:\s]*" + _cost, text)
    if m:
        c.append(_candidate("production_building_cost_per_m2", "تكلفة مبنى الإنتاج/م²",
                            _clean_number(m[0]), 0.70, m[1], "regex_amount", "amount"))

    m = _first_match(r"(?:تكلفة المستودعات?|تكلفة المخازن?)[:\s]*" + _cost, text)
    if m:
        c.append(_candidate("warehouse_cost_per_m2", "تكلفة المستودع/م²",
                            _clean_number(m[0]), 0.70, m[1], "regex_amount", "amount"))

    m = _first_match(r"(?:تكلفة المبنى الإداري|تكلفة الإدارة)[:\s]*" + _cost, text)
    if m:
        c.append(_candidate("admin_building_cost_per_m2", "تكلفة المبنى الإداري/م²",
                            _clean_number(m[0]), 0.70, m[1], "regex_amount", "amount"))

    m = _first_match(r"(?:أعمال خارجية|تكلفة الأعمال الخارجية)[:\s]*" + _cost, text)
    if m:
        c.append(_candidate("external_works_cost", "تكلفة الأعمال الخارجية",
                            _clean_number(m[0]), 0.65, m[1], "regex_amount", "amount"))

    m = _first_match(
        r"(?:العمر الافتراضي|العمر الإنتاجي)[:\s]*([0-9٠-٩]+(?:\s*(?:سنة|عام))?)", text)
    if m:
        c.append(_candidate("useful_life_years", "العمر الافتراضي بالسنوات",
                            _clean_number(m[0]), 0.75, m[1], "regex_number", "number"))

    m = _first_match(
        r"(?:معدل الاستهلاك السنوي|نسبة الاستهلاك)[:\s]*([0-9٠-٩,\.]+(?:\s*%)?)", text)
    if m:
        c.append(_candidate("annual_depreciation_rate", "معدل الاستهلاك السنوي",
                            _clean_number(m[0]), 0.70, m[1], "regex_percent", "number"))

    m = _first_match(r"(?:مصدر الدليل|الدليل|جهة الإصدار)[:\s]*([^\n]{3,80})", text)
    if m:
        c.append(_candidate("guidance_source_name", "اسم مصدر الدليل",
                            m[0].strip(), 0.60, m[1], "regex_text"))

    m = _first_match(
        r"(?:تاريخ الدليل|تاريخ الإصدار)[:\s]*"
        r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4})", text)
    if m:
        c.append(_candidate("guidance_date", "تاريخ الدليل",
                            _clean_date(m[0]), 0.65, m[1], "regex_date", "date"))
    return c


def _extract_ain_shams_factory_cost(text: str) -> list[dict]:
    c: list[dict] = []
    _cost = r"([0-9٠-٩,،\.]+(?:\s*جنيه)?(?:/م2)?)"

    m = _first_match(r"(?:عنوان المرجع|اسم الجدول)[:\s]*([^\n]{3,100})", text)
    if m:
        c.append(_candidate("reference_title", "عنوان المرجع", m[0].strip(), 0.65, m[1], "regex_text"))

    m = _first_match(r"(?:تكلفة مبنى الإنتاج|تكلفة الإنتاج)[:\s]*" + _cost, text)
    if m:
        c.append(_candidate("production_building_cost_per_m2", "تكلفة مبنى الإنتاج/م²",
                            _clean_number(m[0]), 0.70, m[1], "regex_amount", "amount"))

    m = _first_match(r"(?:تكلفة المستودعات?|تكلفة المخازن?)[:\s]*" + _cost, text)
    if m:
        c.append(_candidate("warehouse_cost_per_m2", "تكلفة المستودع/م²",
                            _clean_number(m[0]), 0.70, m[1], "regex_amount", "amount"))

    m = _first_match(r"(?:تكلفة المبنى الإداري|تكلفة الإدارة)[:\s]*" + _cost, text)
    if m:
        c.append(_candidate("admin_building_cost_per_m2", "تكلفة المبنى الإداري/م²",
                            _clean_number(m[0]), 0.70, m[1], "regex_amount", "amount"))

    m = _first_match(
        r"(?:العمر الافتراضي|العمر الإنتاجي)[:\s]*([0-9٠-٩]+(?:\s*(?:سنة|عام))?)", text)
    if m:
        c.append(_candidate("useful_life_years", "العمر الافتراضي",
                            _clean_number(m[0]), 0.75, m[1], "regex_number", "number"))

    m = _first_match(r"(?:طريقة الاستهلاك|أسلوب الاستهلاك)[:\s]*([^\n]{3,60})", text)
    if m:
        c.append(_candidate("depreciation_method", "طريقة الاستهلاك",
                            m[0].strip(), 0.60, m[1], "regex_text"))

    m = _first_match(
        r"(?:معدل الاستهلاك السنوي|نسبة الاستهلاك)[:\s]*([0-9٠-٩,\.]+(?:\s*%)?)", text)
    if m:
        c.append(_candidate("annual_depreciation_rate", "معدل الاستهلاك السنوي",
                            _clean_number(m[0]), 0.70, m[1], "regex_percent", "number"))

    m = _first_match(r"(?:نطاق التطبيق|ملاحظة التطبيق)[:\s]*([^\n]{3,100})", text)
    if m:
        c.append(_candidate("applicability_note", "ملاحظة التطبيق",
                            m[0].strip(), 0.55, m[1], "regex_text"))
    return c


def _extract_nuca_land_price(text: str) -> list[dict]:
    c: list[dict] = []

    m = _first_match(r"(?:المدينة|المنطقة|الحي)[:\s]*([^\n]{3,80})", text)
    if m:
        c.append(_candidate("district_or_city", "المدينة / المنطقة",
                            m[0].strip(), 0.65, m[1], "regex_text"))

    m = _first_match(r"(?:الاستخدام|نوع الأرض|نوع الاستخدام)[:\s]*([^\n]{3,60})", text)
    if m:
        c.append(_candidate("land_use", "نوع استخدام الأرض",
                            m[0].strip(), 0.60, m[1], "regex_text"))

    m = _first_match(
        r"(?:سعر الأرض|سعر المتر المربع|ثمن الأرض)[:\s]*"
        r"([0-9٠-٩,،\.]+(?:\s*(?:جنيه|جنيه/م))?)", text)
    if m:
        c.append(_candidate("land_price_per_m2", "سعر الأرض للمتر المربع",
                            _clean_number(m[0]), 0.68, m[1], "regex_amount", "amount"))

    m = _first_match(
        r"(?:تاريخ المرجع|تاريخ السعر)[:\s]*"
        r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4})", text)
    if m:
        c.append(_candidate("reference_date", "تاريخ المرجع",
                            _clean_date(m[0]), 0.68, m[1], "regex_date", "date"))

    m = _first_match(r"(?:جهة الإصدار|الهيئة المصدرة)[:\s]*([^\n]{3,80})", text)
    if m:
        c.append(_candidate("issuing_authority", "جهة الإصدار",
                            m[0].strip(), 0.60, m[1], "regex_text"))

    m = _first_match(r"(?:ملاحظة|تنبيه|تعليق)[:\s]*([^\n]{3,100})", text)
    if m:
        c.append(_candidate("source_note", "ملاحظة المصدر", m[0].strip(), 0.50, m[1], "regex_text"))
    return c


def _extract_general_note(text: str) -> list[dict]:
    """Generic extractor for expert_note, legal_note, other."""
    c: list[dict] = []

    m = _first_match(r"(?:الموضوع|العنوان|ملخص)[:\s]*([^\n]{5,150})", text)
    if m:
        c.append(_candidate("note_summary", "ملخص الملاحظة", m[0].strip(), 0.55, m[1], "regex_text"))

    m = _first_match(r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})", text)
    if m:
        c.append(_candidate("mentioned_dates", "تواريخ مذكورة",
                            _clean_date(m[0]), 0.50, m[1], "regex_date", "date"))

    m = _first_match(r"([0-9٠-٩,،\.]+(?:\s*(?:جنيه|EGP)))", text)
    if m:
        c.append(_candidate("mentioned_amounts", "مبالغ مذكورة",
                            _clean_number(m[0]), 0.50, m[1], "regex_amount", "amount"))

    m = _first_match(r"([0-9٠-٩,،\.]+(?:\s*(?:م2|م²|متر مربع)))", text)
    if m:
        c.append(_candidate("mentioned_area", "مساحات مذكورة",
                            _clean_number(m[0]), 0.50, m[1], "regex_area", "area"))

    m = _first_match(r"(?:مطلوب|يجب|ملاحظة هامة)[:\s]*([^\n]{5,150})", text)
    if m:
        c.append(_candidate("action_required", "إجراء مطلوب", m[0].strip(), 0.50, m[1], "regex_text"))
    return c


# ── Image-only helper ─────────────────────────────────────────────────────────

def _build_image_text_candidates(text: str, evidence_type: str) -> list[dict]:
    if not text or not text.strip():
        return [_doc_level_summary(evidence_type,
                                   "لم يُستخرج نص من هذه الصورة.",
                                   _IMAGE_TEXT_WARNING)]
    candidates: list[dict] = []
    m = _first_match(r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})", text)
    if m:
        candidates.append(_candidate("mentioned_dates", "تواريخ ظاهرة في الصورة",
                                     _clean_date(m[0]), 0.40, m[1], "image_text_only",
                                     warning=_IMAGE_TEXT_WARNING))
    m = _first_match(r"([0-9٠-٩,،\.]+(?:\s*(?:م2|م²|متر)))", text)
    if m:
        candidates.append(_candidate("mentioned_area", "مساحات ظاهرة في الصورة",
                                     _clean_number(m[0]), 0.35, m[1], "image_text_only",
                                     "area", _IMAGE_TEXT_WARNING))
    if not candidates:
        candidates.append(_doc_level_summary(
            evidence_type,
            f"نص ظاهر في الصورة: {text.strip()[:200]}",
            _IMAGE_TEXT_WARNING,
        ))
    return candidates


# ── Dispatcher ────────────────────────────────────────────────────────────────

_EXTRACTORS: dict = {
    "tax_notice_form3":                    _extract_tax_notice_form3,
    "ownership_document":                  _extract_ownership_document,
    "lease_contract":                      _extract_lease_contract,
    "activity_license":                    _extract_activity_license,
    "commercial_register":                 _extract_commercial_register,
    "industrial_license":                  _extract_industrial_license,
    "land_allocation_document":            _extract_land_allocation,
    "area_statement":                      _extract_area_statement,
    "building_permit":                     _extract_building_permit,
    "occupancy_or_completion_certificate": _extract_occupancy_certificate,
    "factory_cost_guidance":               _extract_factory_cost_guidance,
    "ain_shams_factory_cost_reference":    _extract_ain_shams_factory_cost,
    "nuca_land_price_reference":           _extract_nuca_land_price,
    "expert_note":                         _extract_general_note,
    "legal_note":                          _extract_general_note,
    "other":                               _extract_general_note,
}


def build_ocr_field_candidates(
    ocr_text: str,
    evidence_type: str,
    template_id: Optional[str] = None,
) -> dict:
    """
    Extract advisory field candidates from raw OCR text.

    All candidates enforce:
      accepted_by_default   = False
      needs_human_review    = True
      production_ready      = False
      preliminary_visible   = True
      expert_review_visible = True
      certified_usage_allowed = False

    Never raises; all errors go into warnings.
    """
    warnings_out: list[str] = []
    is_image_only = evidence_type in _IMAGE_ONLY_TYPES
    is_structured = evidence_type in _STRUCTURED_TYPES

    # ── Structured: placeholder only ─────────────────────────────────────
    if is_structured:
        warnings_out.append(_STRUCTURED_WARNING)
        placeholder = _candidate(
            "structured_parser_required", "مسار استخلاص جدولي مطلوب",
            _STRUCTURED_WARNING, 0.0, "", "structured_placeholder",
            warning=_STRUCTURED_WARNING,
        )
        return {
            "evidence_type":      evidence_type,
            "template_id":        template_id,
            "candidates":         [placeholder],
            "confidence_summary": {"overall": 0.0, "count": 0},
            "warnings":           warnings_out,
            "is_structured":      True,
            "is_image_only":      False,
        }

    # ── Empty text ────────────────────────────────────────────────────────
    if not ocr_text or not ocr_text.strip():
        warnings_out.append("النص الخام فارغ — لا يمكن استخراج مرشحين.")
        return {
            "evidence_type":      evidence_type,
            "template_id":        template_id,
            "candidates":         [],
            "confidence_summary": {"overall": 0.0, "count": 0},
            "warnings":           warnings_out,
            "is_structured":      False,
            "is_image_only":      is_image_only,
        }

    # ── Image-only: visible text only ────────────────────────────────────
    if is_image_only:
        warnings_out.append(_IMAGE_TEXT_WARNING)
        candidates = _build_image_text_candidates(ocr_text, evidence_type)
        return {
            "evidence_type":      evidence_type,
            "template_id":        template_id,
            "candidates":         candidates,
            "confidence_summary": {"overall": 0.0, "count": len(candidates)},
            "warnings":           warnings_out,
            "is_structured":      False,
            "is_image_only":      True,
        }

    # ── Regular extraction ────────────────────────────────────────────────
    candidates: list[dict] = []
    extractor = _EXTRACTORS.get(evidence_type)
    extractor_ran = False
    if extractor is None:
        warnings_out.append(
            f"نوع المستند '{evidence_type}' لا يحتوي على مستخرج مرشحين مُعرَّف. "
            "يُرجى الإدخال اليدوي."
        )
    else:
        extractor_ran = True
        try:
            candidates = extractor(ocr_text)
        except Exception as exc:
            warnings_out.append(f"خطأ في استخراج المرشحين: {exc}")

    # Enforce invariants on all candidates
    for candidate in candidates:
        candidate["accepted_by_default"]     = False
        candidate["needs_human_review"]      = True
        candidate["production_ready"]        = False
        candidate["preliminary_visible"]     = True
        candidate["expert_review_visible"]   = True
        candidate["certified_usage_allowed"] = False
        candidate["advisory_label_ar"]       = _ADVISORY_LABEL

    # Doc-level summary row only when a known extractor ran but produced nothing
    if extractor_ran and not candidates:
        candidates.append(_doc_level_summary(
            evidence_type,
            f"لم يُعثر على حقول مطابقة في '{evidence_type}' — يُرجى المراجعة اليدوية.",
        ))

    avg_conf = (
        sum(candidate["confidence"] for candidate in candidates) / len(candidates)
        if candidates else 0.0
    )

    return {
        "evidence_type":      evidence_type,
        "template_id":        template_id,
        "candidates":         candidates,
        "confidence_summary": {"overall": round(avg_conf, 3), "count": len(candidates)},
        "warnings":           warnings_out,
        "is_structured":      False,
        "is_image_only":      False,
    }
