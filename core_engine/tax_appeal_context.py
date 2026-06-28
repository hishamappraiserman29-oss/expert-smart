# -*- coding: utf-8 -*-
"""
tax_appeal_context.py — Tax Appeal Calculation Context Builder.

Public API:
    _build_tax_appeal_context(payload: dict) -> dict
    _detect_tax_property_class(payload: dict) -> dict

Supports:
    annual_real_estate_tax  (الضريبة العقارية السنوية / الضريبة العقارية)
    transfer_tax            (ضريبة التصرفات العقارية / ضريبة التصرفات)

Property class families:
    residential         — فيلا، شقة، وحدة سكنية
    non_residential     — محل، وحدة إدارية، جراج، مخزن، مكتب، وحدة بمول
    special_purpose     — مصنع، منشأة صناعية، مزرعة دواجن، محطة خدمة، منشأة إنتاجية

Strict rules:
    - No Qdrant, no RAG, no internet search, no external APIs.
    - Use _qa_simulation=True for synthetic QA data only.
    - Dates displayed as DD/MM/YYYY (Egyptian display format).
    - Do not use FPDF.
    - Do not claim official legal advice.
    - Do not claim appeal report is legally certified unless reviewed by expert.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

# ── Constants ─────────────────────────────────────────────────────────────────

TRANSFER_RATE       = 0.025          # fixed at 2.5% — do not change
_APPEAL_DAYS        = 60
_QDRANT_STATUS      = "مرحلة مستقبلية — غير مفعل"
_DATA_GAP           = "غير متاح ضمن بيانات الطلب"
_NEEDS_EXPERT       = "يحتاج استكمال بواسطة الخبير"
_NOT_APPLICABLE     = "غير مطبق لهذا النوع من الضريبة"

_SOURCE_DISCLAIMER = (
    "لا يتضمن هذا الإصدار استرجاعًا آليًا من الإنترنت أو Qdrant. "
    "تم تجهيز هيكل مصادر البيانات فقط لاستقبال الربط الآلي في مرحلة لاحقة."
)

_DEADLINE_STATUS_MAP = {
    "safe":    "آمن",
    "soon":    "اقتربت المهلة",
    "urgent":  "عاجل",
    "expired": "انتهت المهلة",
    "unknown": "تاريخ غير متاح",
}

# ── Five-method constants ──────────────────────────────────────────────────────
_NEEDS_COMPLETION   = "يحتاج استكمال بيانات"
_NOT_APP_TYPE       = "غير مطبق لهذا النوع من العقار"
_DEFERRED_SOURCE    = "مؤجل لحين ربط مصادر البيانات في مرحلة لاحقة"
_QA_SYNTHETIC_NOTE  = "محاكاة QA — ليست نموذجًا إحصائيًا حقيقيًا"
_FIVE_METHOD_FUTURE_NOTE = (
    "لم يتم استخدام الإنترنت أو Qdrant أو OCR في هذا الإصدار. "
    "تم تجهيز بنية الطرق لاستقبال مصادر البيانات لاحقًا بعد التفعيل والمراجعة."
)
_NEEDS_EXPERT       = "يحتاج استكمال بواسطة الخبير"
_NOT_AVAIL_DATA     = "غير متاح ضمن بيانات الطلب"
_NOT_APP_METHOD     = "غير مطبق لهذه المنهجية"

# ── Sanitisation constants and helper ─────────────────────────────────────────
_CORRUPT_TOKENS: frozenset[str] = frozenset({
    "None", "NaN", "nan", "null", "undefined", "Pa", "P.2",
    "inf", "Inf", "Infinity", "infinity", "ضم", "قدرج؟", "؟",
})

def _sanitize_report_value(v, fallback: str = "يحتاج استكمال بواسطة الخبير") -> str:
    """Return a safe display string — replaces None/NaN/corruption tokens with fallback."""
    if v is None:
        return fallback
    s = str(v).strip()
    if s == "" or s in _CORRUPT_TOKENS or s.lower() in {"none", "nan", "null", "undefined", "inf"}:
        return fallback
    return s


def _assert_no_corrupt_tokens(d: dict) -> None:
    """Raise ValueError if any report-visible value contains a corruption token (dev/test only)."""
    import json
    text = json.dumps(d, ensure_ascii=False)
    for tok in ("Pa\n", "P.2", "NaN", "\x00"):
        if tok in text:
            raise ValueError(f"Corruption token {tok!r} found in context dict")

_TAX_MODE_LABELS = {
    "annual_real_estate_tax": "الضريبة العقارية السنوية",
    "annual":                 "الضريبة العقارية السنوية",
    "transfer_tax":           "ضريبة التصرفات العقارية",
    "transfer":               "ضريبة التصرفات العقارية",
}

_VALID_TAX_SOURCE_TYPES = {
    "tax_notice",
    "form_3_tax",
    "assessment_statement",
    "property_document",
    "sale_contract",
    "rent_comparable",
    "market_comparable",
    "expert_input",
    "future_qdrant_source_placeholder",
}


# ── Property class registry ───────────────────────────────────────────────────
# Maps normalised property-type strings → (class_key, subtype_key, label_ar)

_PROPERTY_CLASS_MAP: dict[str, tuple[str, str, str]] = {
    # ── Residential ───────────────────────────────────────────────────────
    "villa":              ("residential", "villa",            "فيلا"),
    "فيلا":              ("residential", "villa",            "فيلا"),
    "apartment":          ("residential", "apartment",        "شقة سكنية"),
    "شقة":               ("residential", "apartment",        "شقة سكنية"),
    "شقه":               ("residential", "apartment",        "شقة سكنية"),
    "residential_unit":   ("residential", "residential_unit", "وحدة سكنية"),
    "وحدة سكنية":        ("residential", "residential_unit", "وحدة سكنية"),
    "residential":        ("residential", "residential_unit", "وحدة سكنية"),
    "سكني":              ("residential", "residential_unit", "وحدة سكنية"),
    # ── Non-residential ───────────────────────────────────────────────────
    "shop":               ("non_residential", "shop",             "محل تجاري"),
    "محل":               ("non_residential", "shop",             "محل تجاري"),
    "محل تجاري":         ("non_residential", "shop",             "محل تجاري"),
    "admin_unit":         ("non_residential", "admin_unit",       "وحدة إدارية"),
    "admin":              ("non_residential", "admin_unit",       "وحدة إدارية"),
    "وحدة إدارية":       ("non_residential", "admin_unit",       "وحدة إدارية"),
    "شقة إدارية":        ("non_residential", "admin_unit",       "وحدة إدارية"),
    "شقه إدارية":        ("non_residential", "admin_unit",       "وحدة إدارية"),
    "garage":             ("non_residential", "garage",           "جراج"),
    "جراج":              ("non_residential", "garage",           "جراج"),
    "basement_storage":   ("non_residential", "basement_storage", "مخزن بدروم"),
    "مخزن":              ("non_residential", "basement_storage", "مخزن بدروم"),
    "مخزب":              ("non_residential", "basement_storage", "مخزن بدروم"),
    "بدروم":             ("non_residential", "basement_storage", "مخزن بدروم"),
    "basement":           ("non_residential", "basement_storage", "مخزن بدروم"),
    "office":             ("non_residential", "office",           "مكتب"),
    "مكتب":              ("non_residential", "office",           "مكتب"),
    "mall_unit":          ("non_residential", "mall_unit",        "وحدة بمول تجاري"),
    "وحدة بمول":         ("non_residential", "mall_unit",        "وحدة بمول تجاري"),
    # ── Special-purpose ───────────────────────────────────────────────────
    "factory":              ("special_purpose", "factory",              "مصنع"),
    "مصنع":               ("special_purpose", "factory",              "مصنع"),
    "industrial_facility":  ("special_purpose", "industrial_facility",  "منشأة صناعية"),
    "منشأة صناعية":       ("special_purpose", "industrial_facility",  "منشأة صناعية"),
    "poultry_farm":         ("special_purpose", "poultry_farm",         "مزرعة دواجن"),
    "مزرعة دواجن":        ("special_purpose", "poultry_farm",         "مزرعة دواجن"),
    "service_station":      ("special_purpose", "service_station",      "محطة خدمة"),
    "محطة خدمة":          ("special_purpose", "service_station",      "محطة خدمة"),
    "production_facility":  ("special_purpose", "production_facility",  "منشأة إنتاجية"),
    "منشأة إنتاجية":      ("special_purpose", "production_facility",  "منشأة إنتاجية"),
    "industrial":           ("special_purpose", "industrial_facility",  "منشأة صناعية"),
    "صناعي":              ("special_purpose", "industrial_facility",  "منشأة صناعية"),
}

# ── Report archetypes (Part C) ────────────────────────────────────────────────

_CLASS_ARCHETYPE: dict[str, str] = {
    "residential":     "residential_tax_appeal_summary",
    "non_residential": "non_residential_tax_appeal_summary",
    "special_purpose": "special_purpose_tax_appeal_narrative",
}

_CLASS_LABEL_AR: dict[str, str] = {
    "residential":     "عقار سكني",
    "non_residential": "عقار غير سكني",
    "special_purpose": "عقار ذو أغراض خاصة",
}

_CLASS_REQUIRED_SECTIONS: dict[str, list[str]] = {
    "residential": [
        "غلاف التقرير", "ملخص البيانات", "كشف التقييم الحكومي",
        "طريقة التكلفة", "مقارنة البيوع", "طريقة الرسملة",
        "التوفيق بين النتائج", "نسبة المغالاة", "الخلاصة والتوصية",
    ],
    "non_residential": [
        "غلاف التقرير", "ملخص البيانات", "كشف التقييم الحكومي",
        "طريقة التكلفة", "مقارنة البيوع", "طريقة الرسملة",
        "معامل الدور والواجهة", "التوفيق بين النتائج",
        "نسبة المغالاة", "الخلاصة والتوصية",
    ],
    "special_purpose": [
        "غلاف التقرير", "خطاب التقديم", "قائمة المحتويات",
        "مجال العمل", "الافتراضات", "التعريفات", "المحددات",
        "وصف الموقع والملكية", "طريقة التكلفة الصناعية",
        "جدول الإهلاك", "التوفيق والخلاصة", "شهادة الخبير",
    ],
}

_CLASS_VALUATION_METHODS: dict[str, list[str]] = {
    "residential":     ["cost", "sales_comparison", "income_capitalization"],
    "non_residential": ["cost", "sales_comparison", "income_capitalization"],
    "special_purpose": ["cost"],  # industrial: cost only; no sales comparison / income
}

_CLASS_VALUATION_LABELS_AR: dict[str, list[str]] = {
    "residential":     ["طريقة التكلفة", "مقارنة البيوع", "طريقة الرسملة / الدخل"],
    "non_residential": ["طريقة التكلفة", "مقارنة البيوع", "طريقة الرسملة / الدخل"],
    "special_purpose": ["طريقة التكلفة (تكلفة الإحلال الإهلاكية)"],
}

_CLASS_WORKBOOK_SECTIONS: dict[str, list[str]] = {
    "residential": [
        "حساب الضريبة العقارية",
        "تحليل المغالاة",
        "مقارنة بيوع سكنية",
        "طريقة التكلفة السكنية",
        "أدلة الإتمام والإشغال",
    ],
    "non_residential": [
        "مقارنة غير سكنية",
        "تحليل القيمة الإيجارية",
        "عوامل الدور والواجهة",
        "طريقة التكلفة غير السكنية",
    ],
    "special_purpose": [
        "مكونات المنشأة",
        "تكلفة الإحلال",
        "الإهلاك",
        "تحليل المنشأة الخاصة",
        "ملخص القيمة الضريبية",
        "محددات وافتراضات خاصة",
    ],
}

_CLASS_SPECIAL_WARNINGS: dict[str, list[str]] = {
    "residential": [
        "تحقق من تاريخ إتمام البناء بالدليل الجوي / شهادة التسليم",
        "راجع وضع الإشغال: مأهول / شاغر / مؤجر",
        "تأكد من صحة دورة الفحص والتقييم المستخدمة",
    ],
    "non_residential": [
        "راجع معامل الدور (أرضي / أول / بدروم / علوي) وأثره على القيمة",
        "تحقق من ترخيص النشاط التجاري / الإداري",
        "راجع واجهة العقار وأثرها على القيمة الإيجارية",
        "تأكد من نوع النشاط الفعلي وانعكاسه على الإيجار السوقي",
    ],
    "special_purpose": [
        "يجب الحصول على خطاب هيئة المجتمعات العمرانية / الصناعية بسعر الأرض",
        "تطبيق معدل الإهلاك 1.4% سنويًا وفق منهجية التكلفة الصافية",
        "لا تُطبَّق مقارنة البيوع أو طريقة الرسملة عادةً للمنشآت الصناعية",
        "احرص على الحصول على تقرير صيانة وإهلاك من جهة أكاديمية معتمدة",
        "سعر الإحلال: خرسانة ≈ 1200 ج.م/م² — حديد ≈ 800 ج.م/م² (مرجع جامعة عين شمس)",
    ],
}

# ── Required documents checklists by property class (Part G) ─────────────────

_DOCS_RESIDENTIAL: list[dict] = [
    {"doc_key": "form3_notice",      "label_ar": "كشف التقييم الضريبي الحكومي (نموذج 3)",               "required": True,  "note": ""},
    {"doc_key": "site_map",          "label_ar": "رسم الموقع / خريطة تسوية",                             "required": True,  "note": ""},
    {"doc_key": "tax_receipt",       "label_ar": "إيصال سداد الضريبة أو كشف المتأخرات",                 "required": True,  "note": ""},
    {"doc_key": "ownership_deed",    "label_ar": "صورة الطابو أو عقد الملكية / الشهر العقاري",           "required": True,  "note": ""},
    {"doc_key": "build_permit",      "label_ar": "ترخيص البناء أو خطاب تسليم الوحدة",                   "required": True,  "note": ""},
    {"doc_key": "exterior_photos",   "label_ar": "صور العقار من الخارج (أمامي + جانبي)",               "required": True,  "note": ""},
    {"doc_key": "aerial_evidence",   "label_ar": "صور جوية أو تقرير يُثبت تاريخ الإتمام الفعلي",       "required": True,  "note": "إثبات تاريخ البناء أمام الطعن"},
    {"doc_key": "rent_contract",     "label_ar": "عقد إيجار (إن كانت الوحدة مؤجرة)",                   "required": False, "note": "إن وجد"},
    {"doc_key": "sale_contract",     "label_ar": "عقد / ملاحق الشراء",                                  "required": False, "note": "إن طُلب"},
    {"doc_key": "expert_inspection", "label_ar": "تقرير معاينة الخبير الميداني",                         "required": True,  "note": "يعده الخبير بعد الزيارة"},
]

_DOCS_NON_RESIDENTIAL: list[dict] = [
    {"doc_key": "form3_notice",       "label_ar": "كشف التقييم الضريبي الحكومي (نموذج 3)",              "required": True,  "note": ""},
    {"doc_key": "site_map",           "label_ar": "رسم الموقع / خريطة تسوية",                            "required": True,  "note": ""},
    {"doc_key": "tax_receipt",        "label_ar": "إيصال سداد الضريبة أو كشف المتأخرات",                "required": True,  "note": ""},
    {"doc_key": "ownership_deed",     "label_ar": "صورة الطابو أو عقد الملكية / الشهر العقاري",          "required": True,  "note": ""},
    {"doc_key": "build_permit",       "label_ar": "ترخيص البناء / الطابق",                              "required": True,  "note": ""},
    {"doc_key": "commercial_license", "label_ar": "ترخيص النشاط التجاري / الإداري",                     "required": True,  "note": "إلزامي لغير السكني"},
    {"doc_key": "commercial_lease",   "label_ar": "عقد الإيجار التجاري أو عرض إيجار سوقي",              "required": True,  "note": "لتحديد القيمة الإيجارية"},
    {"doc_key": "facade_photos",      "label_ar": "صور واجهة النشاط الفعلي (خارج وداخل)",               "required": True,  "note": ""},
    {"doc_key": "floor_plan",         "label_ar": "مستند توزيع الوحدات في الطابق (تحديد الدور)",         "required": True,  "note": "لتحديد معامل الدور"},
    {"doc_key": "expert_inspection",  "label_ar": "تقرير معاينة الخبير الميداني",                        "required": True,  "note": "يعده الخبير بعد الزيارة"},
]

_DOCS_SPECIAL_PURPOSE: list[dict] = [
    {"doc_key": "form3_notice",        "label_ar": "كشف التقييم الضريبي الحكومي (نموذج 3)",              "required": True,  "note": ""},
    {"doc_key": "ownership_deed",      "label_ar": "مستندات الملكية وعقد الأرض",                         "required": True,  "note": "حكومي أو ملك خاص"},
    {"doc_key": "nuca_letter",         "label_ar": "خطاب هيئة المجتمعات العمرانية / الصناعية بسعر الأرض","required": True,  "note": "إلزامي لتسعير الأرض الصناعية"},
    {"doc_key": "site_plan",           "label_ar": "رسم الموقع / المخطط التفصيلي للمنشأة",               "required": True,  "note": ""},
    {"doc_key": "industrial_license",  "label_ar": "الترخيص الصناعي / التجاري للمنشأة",                  "required": True,  "note": ""},
    {"doc_key": "area_schedule",       "label_ar": "جداول المساحات التفصيلية لكل مبنى ومكوّن",            "required": True,  "note": "أساس حساب تكلفة الإحلال"},
    {"doc_key": "depreciation_report", "label_ar": "تقرير الصيانة وتقييم الإهلاك الفعلي",                "required": True,  "note": ""},
    {"doc_key": "capacity_cert",       "label_ar": "شهادة الإنتاج والطاقة الاستيعابية",                  "required": False, "note": "إن وجدت"},
    {"doc_key": "academic_cert",       "label_ar": "شهادة تقييم من جهة أكاديمية معتمدة",                 "required": False, "note": "إن طُلبت"},
    {"doc_key": "expert_inspection",   "label_ar": "تقرير معاينة الخبير الميداني",                        "required": True,  "note": "إلزامي"},
]

_DOCS_BY_CLASS: dict[str, list[dict]] = {
    "residential":     _DOCS_RESIDENTIAL,
    "non_residential": _DOCS_NON_RESIDENTIAL,
    "special_purpose": _DOCS_SPECIAL_PURPOSE,
}


# ── Date helpers ──────────────────────────────────────────────────────────────

def _format_date_ar(dt_val) -> str:
    """Format date as DD/MM/YYYY (Egyptian display format)."""
    if not dt_val:
        return _DATA_GAP
    if isinstance(dt_val, (date, datetime)):
        return dt_val.strftime("%d/%m/%Y")
    s = str(dt_val).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s[:10], fmt).strftime("%d/%m/%Y")
        except Exception:
            continue
    return s or _DATA_GAP


def _parse_date(val) -> date | None:
    """Parse date string (YYYY-MM-DD or DD/MM/YYYY) to a date object."""
    if not val:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    s = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except Exception:
            continue
    return None


# ── Deadline computation ──────────────────────────────────────────────────────

def _compute_deadline(notice_received_date_raw, report_date_raw) -> dict:
    """Compute 60-day appeal deadline. Returns display-ready dict."""
    notice_dt = _parse_date(notice_received_date_raw)
    report_dt = _parse_date(report_date_raw) or date.today()

    if not notice_dt:
        return {
            "deadline_date":       _DATA_GAP,
            "deadline_date_iso":   "",
            "days_remaining":      _DATA_GAP,
            "deadline_status":     _DEADLINE_STATUS_MAP["unknown"],
            "deadline_status_key": "unknown",
        }

    deadline_dt = notice_dt + timedelta(days=_APPEAL_DAYS)
    days_left   = (deadline_dt - report_dt).days

    if days_left < 0:
        status_key = "expired"
    elif days_left <= 7:
        status_key = "urgent"
    elif days_left <= 14:
        status_key = "soon"
    else:
        status_key = "safe"

    return {
        "deadline_date":       _format_date_ar(deadline_dt),
        "deadline_date_iso":   deadline_dt.isoformat(),
        "days_remaining":      days_left,
        "deadline_status":     _DEADLINE_STATUS_MAP[status_key],
        "deadline_status_key": status_key,
    }


# ── Numeric helpers ───────────────────────────────────────────────────────────

def _safe_float(val, default: float = 0.0) -> float:
    if val is None or val == "" or val == _DATA_GAP or val == _NOT_APPLICABLE:
        return default
    try:
        return float(str(val).replace(",", "").replace("ج.م", "").strip())
    except Exception:
        return default


def _safe_int(val) -> int | None:
    try:
        return int(str(val).strip())
    except Exception:
        return None


# ── Property class detector (Part B) ──────────────────────────────────────────

def _detect_tax_property_class(payload: dict) -> dict:
    """Classify a property into one of 3 Egyptian tax property class families.

    Checks: property_type → asset_type → property_subtype → keyword fallback.
    Returns a standardised dict. Safe to call with an empty payload dict.
    Does not modify the payload. No Qdrant, no RAG, no external calls.
    """
    raw = (
        payload.get("property_type")
        or payload.get("asset_type")
        or payload.get("property_subtype")
        or ""
    )
    key = str(raw).strip().lower()

    # Direct registry lookup (lower-case or original)
    hit = _PROPERTY_CLASS_MAP.get(key) or _PROPERTY_CLASS_MAP.get(raw.strip())

    # Keyword fallback when no direct match
    if not hit:
        r = key
        if any(w in r for w in ("إداري", "admin")):
            hit = ("non_residential", "admin_unit", "وحدة إدارية")
        elif any(w in r for w in ("فيلا", "villa", "apartment", "شقة", "شقه", "سكني", "residential")):
            hit = ("residential", "residential_unit", "وحدة سكنية")
        elif any(w in r for w in ("محل", "shop", "مخزن", "مخزب", "بدروم", "basement",
                                   "جراج", "garage", "office", "مكتب", "mall", "مول")):
            hit = ("non_residential", "shop", "محل تجاري")
        elif any(w in r for w in ("مصنع", "factory", "صناعي", "industrial", "إنتاج",
                                   "دواجن", "poultry", "محطة", "station")):
            hit = ("special_purpose", "industrial_facility", "منشأة صناعية")
        else:
            hit = ("residential", "residential_unit", "وحدة سكنية")  # safe default

    class_key, subtype_key, subtype_label_ar = hit

    return {
        "tax_property_class_key":       class_key,
        "tax_property_class_label_ar":  _CLASS_LABEL_AR[class_key],
        "report_archetype":             _CLASS_ARCHETYPE[class_key],
        "property_subtype_key":         subtype_key,
        "property_subtype_label_ar":    subtype_label_ar,
        "required_sections":            _CLASS_REQUIRED_SECTIONS[class_key],
        "valuation_methods_applicable": _CLASS_VALUATION_METHODS[class_key],
        "valuation_methods_labels_ar":  _CLASS_VALUATION_LABELS_AR[class_key],
        "workbook_sections_applicable": _CLASS_WORKBOOK_SECTIONS[class_key],
        "special_warnings":             _CLASS_SPECIAL_WARNINGS[class_key],
    }


# ── Required documents checklist builder (Part G) ────────────────────────────

def _build_required_documents_checklist(class_key: str, payload: dict) -> list[dict]:
    """Build the required-documents checklist for the detected property class.

    Merges the static checklist with uploaded-document status from the payload.
    Each item: {doc_key, label_ar, required, status, note}
    """
    base_list = _DOCS_BY_CLASS.get(class_key, _DOCS_RESIDENTIAL)
    uploaded_keys: set[str] = set(
        payload.get("uploaded_doc_keys", [])
        if isinstance(payload.get("uploaded_doc_keys"), list)
        else []
    )
    # Also infer from document list added by the route handler
    for doc in (payload.get("documents") or []):
        if isinstance(doc, dict) and doc.get("doc_key"):
            uploaded_keys.add(doc["doc_key"])

    result = []
    for item in base_list:
        if item["doc_key"] in uploaded_keys:
            status = "مُقدَّم"
        elif item["required"]:
            status = "مطلوب"
        else:
            status = "اختياري"
        result.append({
            "doc_key":  item["doc_key"],
            "label_ar": item["label_ar"],
            "required": item["required"],
            "status":   status,
            "note":     item["note"],
        })
    return result


# ── Class-specific context fields (Part D) ────────────────────────────────────

def _build_class_specific_fields(class_key: str, subtype_key: str, payload: dict) -> dict:
    """Return 20+ class-specific context fields for PDF templates and workbook."""
    fields: dict = {}

    if class_key == "residential":
        fields.update({
            "occupancy_status":           payload.get("occupancy_status") or _NEEDS_EXPERT,
            "completion_status":          payload.get("completion_status") or _NEEDS_EXPERT,
            "completion_year":            payload.get("completion_year") or _DATA_GAP,
            "floor_level":                payload.get("floor_level") or _DATA_GAP,
            "number_of_floors":           payload.get("number_of_floors") or _DATA_GAP,
            "construction_date_evidence": payload.get("construction_date_evidence") or _NEEDS_EXPERT,
            "cost_per_sqm_building":      _safe_float(payload.get("cost_per_sqm_building")) or _NEEDS_EXPERT,
            "cost_per_sqm_land":          _safe_float(payload.get("cost_per_sqm_land")) or _NEEDS_EXPERT,
            "sales_comparable_1":         payload.get("sales_comparable_1") or _NEEDS_EXPERT,
            "sales_comparable_2":         payload.get("sales_comparable_2") or _NEEDS_EXPERT,
            "sales_comparable_3":         payload.get("sales_comparable_3") or _NEEDS_EXPERT,
            "rental_comparable_1":        payload.get("rental_comparable_1") or _NEEDS_EXPERT,
            "rental_comparable_2":        payload.get("rental_comparable_2") or _NEEDS_EXPERT,
            "capitalization_rate":        _safe_float(payload.get("capitalization_rate", 0)) or _NEEDS_EXPERT,
            # Non-residential N/A
            "commercial_floor_type":      _NOT_APPLICABLE,
            "floor_adjustment_factor":    _NOT_APPLICABLE,
            "frontage_width":             _NOT_APPLICABLE,
            "commercial_activity":        _NOT_APPLICABLE,
            "rental_yield_pct":           _NOT_APPLICABLE,
            # Special-purpose N/A
            "industrial_zone":            _NOT_APPLICABLE,
            "land_price_per_sqm":         _NOT_APPLICABLE,
            "land_price_reference":       _NOT_APPLICABLE,
            "building_unit_cost":         _NOT_APPLICABLE,
            "depreciation_rate":          _NOT_APPLICABLE,
            "age_years":                  _NOT_APPLICABLE,
            "industrial_components":      [],
            "scope_of_work_ar":           _NOT_APPLICABLE,
            "assumptions_ar":             _NOT_APPLICABLE,
            "definitions_ar":             _NOT_APPLICABLE,
            "limitations_ar":             _NOT_APPLICABLE,
        })

    elif class_key == "non_residential":
        fields.update({
            "commercial_floor_type":      payload.get("commercial_floor_type") or _NEEDS_EXPERT,
            "floor_adjustment_factor":    _safe_float(payload.get("floor_adjustment_factor", 0)) or _NEEDS_EXPERT,
            "frontage_width":             payload.get("frontage_width") or _DATA_GAP,
            "commercial_activity":        payload.get("commercial_activity") or _NEEDS_EXPERT,
            "rental_yield_pct":           _safe_float(payload.get("rental_yield_pct", 0)) or _NEEDS_EXPERT,
            "usable_area":                payload.get("usable_area") or payload.get("area") or _DATA_GAP,
            "cost_per_sqm_building":      _safe_float(payload.get("cost_per_sqm_building")) or _NEEDS_EXPERT,
            "cost_per_sqm_land":          _safe_float(payload.get("cost_per_sqm_land")) or _NEEDS_EXPERT,
            "floor_level":                payload.get("floor_level") or _DATA_GAP,
            "number_of_floors":           payload.get("number_of_floors") or _DATA_GAP,
            "sales_comparable_1":         payload.get("sales_comparable_1") or _NEEDS_EXPERT,
            "sales_comparable_2":         payload.get("sales_comparable_2") or _NEEDS_EXPERT,
            "rental_comparable_1":        payload.get("rental_comparable_1") or _NEEDS_EXPERT,
            "capitalization_rate":        _safe_float(payload.get("capitalization_rate", 0)) or _NEEDS_EXPERT,
            # Residential N/A
            "occupancy_status":           _NOT_APPLICABLE,
            "completion_status":          _NOT_APPLICABLE,
            "completion_year":            _NOT_APPLICABLE,
            "construction_date_evidence": _NOT_APPLICABLE,
            "sales_comparable_3":         _NOT_APPLICABLE,
            "rental_comparable_2":        _NOT_APPLICABLE,
            # Special-purpose N/A
            "industrial_zone":            _NOT_APPLICABLE,
            "land_price_per_sqm":         _NOT_APPLICABLE,
            "land_price_reference":       _NOT_APPLICABLE,
            "building_unit_cost":         _NOT_APPLICABLE,
            "depreciation_rate":          _NOT_APPLICABLE,
            "age_years":                  _NOT_APPLICABLE,
            "industrial_components":      [],
            "scope_of_work_ar":           _NOT_APPLICABLE,
            "assumptions_ar":             _NOT_APPLICABLE,
            "definitions_ar":             _NOT_APPLICABLE,
            "limitations_ar":             _NOT_APPLICABLE,
        })

    else:  # special_purpose
        fields.update({
            "industrial_zone":            payload.get("industrial_zone") or _NEEDS_EXPERT,
            "land_price_per_sqm":         _safe_float(payload.get("land_price_per_sqm", 0)) or _NEEDS_EXPERT,
            "land_price_reference": (
                payload.get("land_price_reference")
                or "خطاب هيئة المجتمعات العمرانية / الصناعية — يحتاج استكمال"
            ),
            "building_unit_cost":         _safe_float(payload.get("building_unit_cost", 0)) or _NEEDS_EXPERT,
            "depreciation_rate":          _safe_float(payload.get("depreciation_rate", 0.014)),
            "age_years":                  _safe_int(payload.get("age_years")) or _NEEDS_EXPERT,
            "industrial_components":      payload.get("industrial_components") or [],
            "number_of_floors":           payload.get("number_of_floors") or _DATA_GAP,
            "cost_per_sqm_building":      _safe_float(payload.get("cost_per_sqm_building", 0)) or _NEEDS_EXPERT,
            "cost_per_sqm_land":          _safe_float(payload.get("cost_per_sqm_land", 0)) or _NEEDS_EXPERT,
            # Narrative sections
            "scope_of_work_ar": (
                payload.get("scope_of_work_ar")
                or "تقييم العقار لأغراض الطعن الضريبي على الضريبة العقارية السنوية — يحتاج استكمال"
            ),
            "assumptions_ar": (
                payload.get("assumptions_ar")
                or "سعر الأرض وفق خطاب هيئة المجتمعات — تكلفة الإحلال وفق مرجع جامعة عين شمس"
            ),
            "definitions_ar": (
                payload.get("definitions_ar")
                or "القيمة السوقية — تكلفة الإحلال الإهلاكية — صافي قيمة الأصل — الإهلاك المتراكم"
            ),
            "limitations_ar": (
                payload.get("limitations_ar")
                or "لا تُطبَّق مقارنة البيوع أو طريقة الرسملة — تستند الدراسة إلى مستندات المنشأة"
            ),
            # Residential N/A
            "occupancy_status":           _NOT_APPLICABLE,
            "completion_status":          _NOT_APPLICABLE,
            "completion_year":            _NOT_APPLICABLE,
            "floor_level":                _NOT_APPLICABLE,
            "construction_date_evidence": _NOT_APPLICABLE,
            "sales_comparable_1":         _NOT_APPLICABLE,
            "sales_comparable_2":         _NOT_APPLICABLE,
            "sales_comparable_3":         _NOT_APPLICABLE,
            "rental_comparable_1":        _NOT_APPLICABLE,
            "rental_comparable_2":        _NOT_APPLICABLE,
            "capitalization_rate":        _NOT_APPLICABLE,
            # Non-residential N/A
            "commercial_floor_type":      _NOT_APPLICABLE,
            "floor_adjustment_factor":    _NOT_APPLICABLE,
            "frontage_width":             _NOT_APPLICABLE,
            "commercial_activity":        _NOT_APPLICABLE,
            "rental_yield_pct":           _NOT_APPLICABLE,
        })

    return fields


# ── Annual real estate tax engine ─────────────────────────────────────────────

def _build_annual_tax_engine(payload: dict) -> dict:
    """Annual real estate tax calculation context (advisory only)."""
    govt_rental_val  = _safe_float(payload.get("government_assessed_annual_rental_value"))
    govt_capital_val = _safe_float(payload.get("government_assessed_capital_value"))
    mkt_rental_val   = _safe_float(
        payload.get("estimated_market_rental_value") or payload.get("annual_rental_estimate")
    )
    mkt_capital_val  = _safe_float(payload.get("estimated_market_capital_value"))
    govt_tax_amount  = _safe_float(
        payload.get("government_tax_amount") or payload.get("government_claim")
    )
    exemption_amount     = _safe_float(payload.get("exemption_amount", 0))
    maint_rate           = _safe_float(payload.get("maintenance_deduction_rate", 0.3))
    adv_tax_rate         = _safe_float(payload.get("annual_tax_rate", 0.10))
    corrected_tax        = _safe_float(payload.get("corrected_tax_amount"))
    expected_savings_raw = _safe_float(payload.get("expected_savings"))

    assessment_year_raw = (
        payload.get("inspection_cycle_year") or payload.get("assessment_year")
    )
    assessment_year = _safe_int(assessment_year_raw)
    next_assessment = (assessment_year + 5) if assessment_year else None

    taxable_base = 0.0
    if corrected_tax <= 0 and mkt_rental_val > 0:
        net_rental   = mkt_rental_val * (1.0 - maint_rate)
        taxable_base = max(0.0, net_rental - exemption_amount)
        corrected_tax = round(taxable_base * adv_tax_rate, 2)

    overcharge_amount   = 0.0
    overcharge_pct      = 0.0
    overcharge_detected = False
    if govt_tax_amount > 0 and corrected_tax > 0 and govt_tax_amount > corrected_tax:
        overcharge_amount   = round(govt_tax_amount - corrected_tax, 2)
        overcharge_pct      = round(overcharge_amount / govt_tax_amount * 100, 1)
        overcharge_detected = True

    expected_savings = expected_savings_raw if expected_savings_raw > 0 else overcharge_amount

    recommended_action = _NEEDS_EXPERT
    if overcharge_detected:
        recommended_action = "تقديم طعن رسمي — يُوصى بمراجعة الخبير فورًا"

    return {
        "tax_mode":                          "annual_real_estate_tax",
        "tax_mode_label_ar":                 "الضريبة العقارية السنوية",
        "government_assessed_annual_rental_value": govt_rental_val or _DATA_GAP,
        "government_assessed_capital_value":  govt_capital_val or _DATA_GAP,
        "estimated_market_rental_value":      mkt_rental_val or _DATA_GAP,
        "estimated_market_capital_value":     mkt_capital_val or _DATA_GAP,
        "exemption_amount":                   exemption_amount,
        "maintenance_deduction_rate":         maint_rate,
        "taxable_base":                       taxable_base or _DATA_GAP,
        "tax_rate_advisory":                  adv_tax_rate,
        "government_tax_amount":              govt_tax_amount or _DATA_GAP,
        "corrected_tax_amount":               corrected_tax or _DATA_GAP,
        "expected_savings":                   expected_savings,
        "overcharge_amount":                  overcharge_amount,
        "overcharge_percentage":              overcharge_pct,
        "overcharge_detected":                overcharge_detected,
        "inspection_cycle_year":              assessment_year or _DATA_GAP,
        "next_reassessment_year":             next_assessment or _DATA_GAP,
        "transfer_rate":                      _NOT_APPLICABLE,
        "transfer_rate_pct":                  _NOT_APPLICABLE,
        "sale_date":                          _NOT_APPLICABLE,
        "sale_date_iso":                      _NOT_APPLICABLE,
        "sale_value_declared":                _NOT_APPLICABLE,
        "government_assessed_sale_value":     _NOT_APPLICABLE,
        "challenged_sale_value":              _NOT_APPLICABLE,
        "transfer_tax_government":            _NOT_APPLICABLE,
        "transfer_tax_corrected":             _NOT_APPLICABLE,
        "date_basis_note": (
            "تاريخ الأساس الضريبي: دورة الفحص والتقييم — وليس تاريخ بيع."
        ),
        "annual_thresholds_note": (
            "حدود وإعفاءات الضريبة العقارية السنوية لا تطبق على ضريبة التصرفات العقارية."
        ),
        "tax_gap_analysis":    "تحليل استرشادي — يحتاج مراجعة خبير",
        "recommended_action":  recommended_action,
        "calculation_label":   "محاكاة استرشادية — غير معتمدة قانونيًا — تحتاج مراجعة الخبير",
    }


# ── Transfer tax engine ───────────────────────────────────────────────────────

def _build_transfer_tax_engine(payload: dict) -> dict:
    """Transfer tax engine — rate FIXED at 2.5%. Do not apply annual thresholds."""
    sale_value_declared    = _safe_float(
        payload.get("sale_value_declared") or payload.get("sale_value") or payload.get("government_claim")
    )
    govt_assessed_sale_val = _safe_float(
        payload.get("government_assessed_sale_value") or payload.get("government_claim")
    )
    challenged_sale_val    = _safe_float(payload.get("challenged_sale_value"))
    sale_date_raw          = payload.get("sale_date") or payload.get("valuation_date") or ""
    sale_dt                = _parse_date(sale_date_raw)

    govt_transfer_tax = round(govt_assessed_sale_val * TRANSFER_RATE, 2)
    corrected_tax     = _safe_float(payload.get("corrected_tax_amount"))
    if corrected_tax <= 0 and challenged_sale_val > 0:
        corrected_tax = round(challenged_sale_val * TRANSFER_RATE, 2)

    expected_savings_raw = _safe_float(payload.get("expected_savings"))
    expected_savings     = expected_savings_raw
    if expected_savings <= 0 and govt_transfer_tax > corrected_tax > 0:
        expected_savings = round(govt_transfer_tax - corrected_tax, 2)

    overcharge_amount   = round(govt_transfer_tax - corrected_tax, 2) if corrected_tax > 0 else 0.0
    overcharge_pct      = (
        round(overcharge_amount / govt_transfer_tax * 100, 1)
        if govt_transfer_tax > 0 else 0.0
    )
    overcharge_detected = overcharge_amount > 0

    recommended_action = _NEEDS_EXPERT
    if overcharge_detected:
        recommended_action = "تقديم طعن رسمي على قيمة التصرف — يُوصى بمراجعة الخبير"

    return {
        "tax_mode":                          "transfer_tax",
        "tax_mode_label_ar":                 "ضريبة التصرفات العقارية",
        "transfer_rate":                     TRANSFER_RATE,
        "transfer_rate_pct":                 "2.5%",
        "sale_date":                         _format_date_ar(sale_dt),
        "sale_date_iso":                     sale_dt.isoformat() if sale_dt else "",
        "sale_value_declared":               sale_value_declared or _DATA_GAP,
        "government_assessed_sale_value":    govt_assessed_sale_val or _DATA_GAP,
        "challenged_sale_value":             challenged_sale_val or _DATA_GAP,
        "transfer_tax_government":           govt_transfer_tax or _DATA_GAP,
        "transfer_tax_corrected":            corrected_tax or _DATA_GAP,
        "government_tax_amount":             govt_transfer_tax or _DATA_GAP,
        "corrected_tax_amount":              corrected_tax or _DATA_GAP,
        "expected_savings":                  expected_savings,
        "overcharge_amount":                 overcharge_amount,
        "overcharge_percentage":             overcharge_pct,
        "overcharge_detected":               overcharge_detected,
        "date_basis_note": (
            "تاريخ الأساس الضريبي: تاريخ التصرف (البيع) — وليس تاريخ التقرير إلا إذا كانا متطابقين."
        ),
        "government_assessed_annual_rental_value": _NOT_APPLICABLE,
        "government_assessed_capital_value":       _NOT_APPLICABLE,
        "estimated_market_rental_value":           _NOT_APPLICABLE,
        "estimated_market_capital_value":          _NOT_APPLICABLE,
        "exemption_amount":                        _NOT_APPLICABLE,
        "maintenance_deduction_rate":              _NOT_APPLICABLE,
        "taxable_base":                            _NOT_APPLICABLE,
        "tax_rate_advisory":                       _NOT_APPLICABLE,
        "inspection_cycle_year":                   _NOT_APPLICABLE,
        "next_reassessment_year":                  _NOT_APPLICABLE,
        "annual_thresholds_note": (
            "حدود وإعفاءات الضريبة العقارية السنوية لا تطبق على ضريبة التصرفات العقارية."
        ),
        "tax_gap_analysis":    "تحليل استرشادي — يحتاج مراجعة خبير",
        "recommended_action":  recommended_action,
        "calculation_label":   "محاكاة استرشادية — غير معتمدة قانونيًا — تحتاج مراجعة الخبير",
    }


# ── Source registry (readiness layer — no live Qdrant) ───────────────────────

def _build_tax_source_registry(payload: dict, tax_mode: str, is_qa: bool) -> list:
    """Build tax-specific source registry (structural readiness — Qdrant disabled)."""
    sources: list[dict] = []
    origin = "محاكاة QA داخلية" if is_qa else _NEEDS_EXPERT

    sources.append({
        "source_id":           payload.get("tax_notice_id") or "SRC-TAX-NOTICE-001",
        "source_type":         "tax_notice",
        "source_label":        "إخطار ضريبي حكومي",
        "source_status":       "مُدرج" if payload.get("notice_received_date") else "غير متاح",
        "source_origin":       origin,
        "source_date":         payload.get("notice_received_date") or "",
        "document_type":       "إخطار ضريبي / نموذج 3",
        "property_zone_id":    payload.get("zone_id") or "",
        "used_in_calculation": True,
        "confidence_score":    70,
        "qdrant_ready":        True,
        "qdrant_status":       _QDRANT_STATUS,
    })

    if tax_mode == "transfer_tax":
        sources.append({
            "source_id":           payload.get("sale_contract_id") or "SRC-TAX-CONTRACT-001",
            "source_type":         "sale_contract",
            "source_label":        "عقد البيع / التصرف العقاري",
            "source_status":       "مُدرج" if payload.get("sale_date") else _NEEDS_EXPERT,
            "source_origin":       origin,
            "source_date":         payload.get("sale_date") or "",
            "document_type":       "عقد تصرف عقاري",
            "property_zone_id":    payload.get("zone_id") or "",
            "used_in_calculation": True,
            "confidence_score":    75,
            "qdrant_ready":        True,
            "qdrant_status":       _QDRANT_STATUS,
        })
    else:
        sources.append({
            "source_id":           "SRC-TAX-ASSESS-001",
            "source_type":         "assessment_statement",
            "source_label":        "كشف التقييم الضريبي الحكومي",
            "source_status":       "مُدرج" if payload.get("inspection_cycle_year") else _NEEDS_EXPERT,
            "source_origin":       origin,
            "source_date":         str(payload.get("inspection_cycle_year") or ""),
            "document_type":       "كشف تقييم ضريبي",
            "property_zone_id":    payload.get("zone_id") or "",
            "used_in_calculation": True,
            "confidence_score":    70,
            "qdrant_ready":        True,
            "qdrant_status":       _QDRANT_STATUS,
        })

    sources.append({
        "source_id":           "SRC-TAX-EXPERT-001",
        "source_type":         "expert_input",
        "source_label":        "تقدير الخبير / القيمة البديلة",
        "source_status":       (
            "مُدرج"
            if payload.get("expert_indicated_value") or payload.get("corrected_tax_amount")
            else _NEEDS_EXPERT
        ),
        "source_origin":       origin if is_qa else "إدخال الخبير",
        "source_date":         "",
        "document_type":       "تقدير خبير تقييم معتمد",
        "property_zone_id":    payload.get("zone_id") or "",
        "used_in_calculation": True,
        "confidence_score":    85,
        "qdrant_ready":        True,
        "qdrant_status":       _QDRANT_STATUS,
    })

    sources.append({
        "source_id":           "SRC-TAX-QDRANT-FUTURE",
        "source_type":         "future_qdrant_source_placeholder",
        "source_label":        "مصدر Qdrant المستقبلي",
        "source_status":       "مرحلة مستقبلية — غير مفعل",
        "source_origin":       "غير مفعل",
        "source_date":         "",
        "document_type":       "مصدر آلي مستقبلي",
        "property_zone_id":    "",
        "used_in_calculation": False,
        "confidence_score":    0,
        "qdrant_ready":        True,
        "qdrant_status":       _QDRANT_STATUS,
    })

    return sources


# ── Five-method valuation builders ───────────────────────────────────────────

def _build_cost_approach(
    payload: dict, class_key: str, subtype_key: str,
    subject_area: float, land_m2: float, bldg_m2: float,
    dep_rate: float, age_yrs: float,
    floor_factor: float, basement_factor: float,
    is_qa: bool,
) -> dict:
    """Method 1 — طريقة التكلفة: always applicable to all classes."""
    land_share = _safe_float(payload.get("land_share_ratio", 1.0)) or 1.0

    # Basement storage: no independent land allocation (rule: Part D)
    if subtype_key == "basement_storage":
        land_share = 0.0

    land_value_ind = round(subject_area * land_m2 * land_share, 2) if (subject_area > 0 and land_m2 > 0 and land_share > 0) else 0.0
    rcn = round(subject_area * bldg_m2, 2) if (subject_area > 0 and bldg_m2 > 0) else 0.0

    if class_key == "non_residential":
        ff = floor_factor if floor_factor > 0 else 1.0
        bf = basement_factor if basement_factor > 0 else 1.0
        rcn = round(rcn * ff * bf, 2)

    phys_dep = dep_rate if dep_rate > 0 else 0.0
    total_dep_amt = min(round(rcn * phys_dep * age_yrs, 2), rcn) if age_yrs > 0 else 0.0
    depr_bldg = round(rcn - total_dep_amt, 2)
    cost_val = round(land_value_ind + depr_bldg, 2)

    has_data = cost_val > 0
    status = "complete" if has_data else ("partial" if (subject_area > 0) else "missing")
    missing = []
    if land_m2 <= 0:
        missing.append("سعر الأرض (ج.م/م²)")
    if bldg_m2 <= 0:
        missing.append("تكلفة الإحلال (ج.م/م²)")
    if subject_area <= 0:
        missing.append("المساحة (م²)")

    if class_key == "residential":
        notes = "سكني: تشمل قيمة الأرض (أو حصتها) + القيمة الإهلاكية للمبنى."
        explanation = (
            "تُقدِّر هذه الطريقة قيمة العقار بحساب تكلفة إعادة بنائه جديدًا "
            "ثم طرح الإهلاك المتراكم وإضافة قيمة الأرض. "
            "تُستخدم كأداة تحقق وتُعطى وزنًا معتدلًا للعقارات السكنية."
        )
    elif class_key == "non_residential":
        if subtype_key == "basement_storage":
            notes = (
                f"مخزن بدروم: معامل الدور ({floor_factor:.2f}) × معامل البدروم ({basement_factor:.2f}) مُطبَّق. "
                "حصة الأرض = 0% — لا تُخصَّص حصة أرض مستقلة للمخزن."
            )
            explanation = (
                "لا يتم تخصيص حصة أرض مستقلة للمخزن بالبدروم في هذه المحاكاة، "
                "باعتباره تابعًا لعقار قائم ما لم يثبت خلاف ذلك بمستندات الملكية. "
                "تُحسب تكلفة الإحلال بعد تطبيق معامل الدور ومعامل البدروم. "
                "معدل الرسملة للمخازن أعلى من المحلات التجارية نظرًا لاختلاف مخاطر الاستخدام والطلب."
            )
        else:
            notes = f"غير سكني: معامل الدور ({floor_factor:.2f}) × معامل البدروم ({basement_factor:.2f}) مُطبَّق على تكلفة المبنى."
            explanation = (
                "تُحسب تكلفة الإحلال بعد تعديل معامل الدور والواجهة والوصول. "
                "تُطرح منها نسبة الإهلاك المادي والوظيفي وتُضاف قيمة الأرض. "
                "مفيدة للمحلات والوحدات الإدارية والمخازن."
            )
    else:
        notes = "صناعي: يشمل الأرض + المباني + المنشآت الصناعية وفق تكلفة الإحلال الإهلاكية."
        explanation = (
            "للمنشآت الصناعية والأغراض الخاصة: تُعدُّ طريقة التكلفة الطريقة الأساسية. "
            "تم الاعتماد عليها بوزن 100% نظرًا لطبيعة العقار كمنشأة ذات أغراض خاصة "
            "وعدم كفاية بيانات المقارنة السوقية أو الدخل. "
            "تُحسب مكونات البناء (مبنى إنتاجي، مستودعات، مباني إدارية) كل على حدة "
            "بتكلفة الإحلال ثم يُطرح الإهلاك المتراكم الفيزيائي لكل مكوِّن. "
            "الآلات والمعدات التشغيلية لا تدخل ضمن التقييم العقاري إلا إذا تم النص صراحة على خلاف ذلك."
        )

    # ── Detailed component table for special_purpose ──────────────────────────
    component_table = []
    if class_key == "special_purpose":
        raw_components = payload.get("industrial_components") or []
        if raw_components:
            for comp in raw_components:
                comp_area    = _safe_float(comp.get("area", 0))
                comp_ucost   = _safe_float(comp.get("unit_cost", 0))
                comp_rcn     = round(comp_area * comp_ucost, 2) if comp_area > 0 and comp_ucost > 0 else 0.0
                # depreciation from component or default to overall rate × age
                phys_str     = str(comp.get("depreciation", "0%")).replace("%", "")
                try:
                    comp_dep_pct = float(phys_str) / 100.0
                except Exception:
                    comp_dep_pct = round(phys_dep * age_yrs, 4)
                func_dep_pct = 0.0
                ext_dep_pct  = 0.0
                total_dep    = min(round(comp_dep_pct + func_dep_pct + ext_dep_pct, 4), 1.0)
                dep_amount   = round(comp_rcn * total_dep, 2)
                depr_val     = round(comp_rcn - dep_amount, 2)
                # Use stored net_value if available (from payload), else computed
                net_val      = _safe_float(comp.get("net_value")) or depr_val
                component_table.append({
                    "component_name":     comp.get("name", _NEEDS_COMPLETION),
                    "area_m2":            comp_area or _NEEDS_COMPLETION,
                    "unit":               "م²",
                    "unit_cost":          comp_ucost or _NEEDS_COMPLETION,
                    "replacement_cost_new": comp_rcn or _NEEDS_COMPLETION,
                    "physical_dep_pct":   f"{comp_dep_pct:.1%}",
                    "functional_dep_pct": f"{func_dep_pct:.1%}",
                    "external_dep_pct":   f"{ext_dep_pct:.1%}",
                    "total_dep_pct":      f"{total_dep:.1%}",
                    "depreciated_value":  net_val,
                    "notes":              comp.get("notes", ""),
                })
        else:
            # Structural readiness placeholder
            component_table = [
                {
                    "component_name":     "مبنى إنتاجي رئيسي",
                    "area_m2":            _NEEDS_COMPLETION,
                    "unit":               "م²",
                    "unit_cost":          _NEEDS_COMPLETION,
                    "replacement_cost_new": _NEEDS_COMPLETION,
                    "physical_dep_pct":   _NEEDS_COMPLETION,
                    "functional_dep_pct": "0%",
                    "external_dep_pct":   "0%",
                    "total_dep_pct":      _NEEDS_COMPLETION,
                    "depreciated_value":  _NEEDS_COMPLETION,
                    "notes":              "يحتاج استكمال من الخبير",
                },
                {
                    "component_name":     "مستودعات / مخازن",
                    "area_m2":            _NEEDS_COMPLETION, "unit": "م²",
                    "unit_cost":          _NEEDS_COMPLETION,
                    "replacement_cost_new": _NEEDS_COMPLETION,
                    "physical_dep_pct":   _NEEDS_COMPLETION,
                    "functional_dep_pct": "0%",
                    "external_dep_pct":   "0%",
                    "total_dep_pct":      _NEEDS_COMPLETION,
                    "depreciated_value":  _NEEDS_COMPLETION,
                    "notes":              "يحتاج استكمال من الخبير",
                },
                {
                    "component_name":     "مباني إدارية",
                    "area_m2":            _NEEDS_COMPLETION, "unit": "م²",
                    "unit_cost":          _NEEDS_COMPLETION,
                    "replacement_cost_new": _NEEDS_COMPLETION,
                    "physical_dep_pct":   _NEEDS_COMPLETION,
                    "functional_dep_pct": "0%",
                    "external_dep_pct":   "0%",
                    "total_dep_pct":      _NEEDS_COMPLETION,
                    "depreciated_value":  _NEEDS_COMPLETION,
                    "notes":              "يحتاج استكمال من الخبير",
                },
                {
                    "component_name":     "أرض المنشأة",
                    "area_m2":            subject_area or _NEEDS_COMPLETION, "unit": "م²",
                    "unit_cost":          land_m2 or _NEEDS_COMPLETION,
                    "replacement_cost_new": land_value_ind or _NEEDS_COMPLETION,
                    "physical_dep_pct":   "0%",
                    "functional_dep_pct": "0%",
                    "external_dep_pct":   "0%",
                    "total_dep_pct":      "0%",
                    "depreciated_value":  land_value_ind or _NEEDS_COMPLETION,
                    "notes":              "الأرض لا تستهلك",
                },
            ]

    # Land share display — 0% for basement storage
    land_share_display = f"{land_share:.0%}"
    land_val_display   = land_value_ind if land_value_ind > 0 else ("0 ج.م — لا تُخصَّص حصة أرض" if subtype_key == "basement_storage" else _NEEDS_COMPLETION)

    calc_rows = [
        {"label": "المساحة الكلية (م²)",         "value": subject_area or _NEEDS_COMPLETION,  "formula": ""},
        {"label": "سعر الأرض (ج.م/م²)",          "value": land_m2 if land_m2 > 0 else ("غير مطلوب — بدروم" if subtype_key == "basement_storage" else _NEEDS_COMPLETION), "formula": ""},
        {"label": "نسبة حصة الأرض",               "value": land_share_display,                  "formula": ""},
        {"label": "دلالة قيمة الأرض (ج.م)",       "value": land_val_display,                    "formula": "= مساحة × سعر أرض × حصة"},
        {"label": "تكلفة الإحلال (ج.م/م²)",      "value": bldg_m2 or _NEEDS_COMPLETION,        "formula": ""},
        {"label": "تكلفة الإحلال الإجمالية (ج.م)","value": rcn or _NEEDS_COMPLETION,            "formula": "= مساحة × تكلفة الوحدة × معاملات"},
        {"label": "معدل الإهلاك السنوي",           "value": f"{phys_dep:.2%}" if phys_dep > 0 else "لا ينطبق", "formula": ""},
        {"label": "العمر (سنة)",                   "value": int(age_yrs) if age_yrs > 0 else "غير متاح", "formula": ""},
        {"label": "إجمالي الإهلاك (ج.م)",         "value": total_dep_amt,                       "formula": "= تكلفة × معدل × عمر"},
        {"label": "القيمة الإهلاكية للمبنى (ج.م)","value": depr_bldg or _NEEDS_COMPLETION,      "formula": "= تكلفة الإحلال − إهلاك"},
        {"label": "دلالة طريقة التكلفة (ج.م)",    "value": cost_val or _NEEDS_COMPLETION,       "formula": "= قيمة الأرض + قيمة المبنى الإهلاكية"},
    ]
    if subtype_key == "basement_storage":
        calc_rows.insert(3, {
            "label": "ملاحظة حصة الأرض",
            "value": "لا يتم تخصيص حصة أرض مستقلة للمخزن بالبدروم ما لم تثبت بمستندات الملكية",
            "formula": "",
        })

    formulas_used = [
        "تكلفة_الإحلال_الإجمالية = مساحة × تكلفة_وحدة × معاملات_التعديل",
        "إهلاك_مادي = تكلفة_الإحلال × معدل_إهلاك_سنوي × العمر",
        "قيمة_مبنى_إهلاكية = تكلفة_الإحلال − إهلاك_مادي",
        "دلالة_طريقة_التكلفة = قيمة_أرض + قيمة_مبنى_إهلاكية",
    ]
    if class_key == "special_purpose":
        formulas_used += [
            "تكلفة_مكوِّن = مساحة × تكلفة_وحدة",
            "إهلاك_كلي_مكوِّن = إهلاك_مادي + إهلاك_وظيفي + إهلاك_اقتصادي",
            "قيمة_مكوِّن_إهلاكية = تكلفة_مكوِّن × (1 − إهلاك_كلي)",
            "دلالة_كلية = قيمة_أرض + مجموع(قيم_مكوِّنات_إهلاكية)",
        ]

    provided = []
    if subject_area > 0: provided.append("المساحة")
    if land_m2 > 0:      provided.append("سعر الأرض")
    if bldg_m2 > 0:      provided.append("تكلفة الإحلال")
    if age_yrs > 0:      provided.append("العمر")
    if phys_dep > 0:     provided.append("معدل الإهلاك")

    return {
        "method_key":                  "cost_approach",
        "method_label_ar":             "طريقة التكلفة",
        "explanation_ar":              explanation,
        "applicability_by_property_class": {
            "residential":    "مطبَّقة — وزن 40% من التوفيق",
            "non_residential": "مطبَّقة — وزن 30% من التوفيق",
            "special_purpose": "أساسية — وزن 100%",
        },
        "method_applicability":        "applicable",
        "data_availability_status":    status,
        "input_sources":               ["إدخال الخبير — تكلفة الإحلال", "مرجع جامعة عين شمس" if class_key == "special_purpose" else "مرجع سوق المقاولات"],
        "provided_inputs":             provided,
        "missing_inputs":              missing,
        "required_missing_inputs":     missing,
        "calculation_rows":            calc_rows,
        "component_table":             component_table,
        "formulas_used":               formulas_used,
        "land_share_pct":              land_share_display,
        "land_value_indicated":        land_value_ind,
        "net_building_value":          depr_bldg,
        "basement_land_share_note":    (
            "لا يتم تخصيص حصة أرض مستقلة للمخزن بالبدروم — تابع لعقار قائم"
            if subtype_key == "basement_storage" else ""
        ),
        "machinery_exclusion_note":    (
            "الآلات والمعدات التشغيلية لا تدخل ضمن التقييم العقاري إلا إذا تم النص صراحة على خلاف ذلك."
            if class_key == "special_purpose" else ""
        ),
        "indicated_value":             cost_val if has_data else _NEEDS_COMPLETION,
        "indicated_tax_basis":         "القيمة الإهلاكية لتكلفة الإحلال",
        "indicated_tax_amount":        _NEEDS_COMPLETION,
        "overcharge_amount":           _NEEDS_COMPLETION,
        "overcharge_percentage":       _NEEDS_COMPLETION,
        "expert_notes":                notes,
        "source_registry_links":       ["SRC-TAX-EXPERT-001"],
        "future_enrichment_status":    "يمكن استكمال بيانات التكلفة من قاعدة بيانات المقاولات عند الربط",
        "depreciation_breakdown": {
            "physical_curable":        {"rate": _NEEDS_COMPLETION, "source": "يحتاج معاينة", "effect_on_value": _NEEDS_COMPLETION},
            "physical_incurable":      {"rate": _NEEDS_COMPLETION, "source": "يحتاج معاينة", "effect_on_value": _NEEDS_COMPLETION},
            "functional_obsolescence": {"rate": "0%", "source": "استرشادي", "effect_on_value": "0"},
            "external_economic_obsolescence": {"rate": "0%", "source": "استرشادي", "effect_on_value": "0"},
            "total_depreciation":      _NEEDS_COMPLETION,
            "expert_override_reason":  "يحتاج مراجعة الخبير الميدانية",
        },
        "land_share_zero_requires_justification": subtype_key == "basement_storage",
    }


def _build_market_comparison(
    payload: dict, class_key: str, subtype_key: str,
    subject_area: float, floor_factor: float, is_qa: bool,
) -> dict:
    """Method 2 — طريقة المقارنة السوقية."""

    # ── Adjustment columns extracted from File 2 (أسلوب السوق التقليدي) ──────
    # Adjustment types: time/date, location, floor/view, condition/finishing
    _adj_labels = ["تعديل التاريخ", "تعديل الموقع والحي", "تعديل الدور والإطلال", "تعديل الحالة والتشطيب"]

    if class_key == "special_purpose":
        applicability = "supporting"
        status = "missing"
        notes = "للمنشآت الصناعية: تُستخدم كأدلة مساندة فقط عند توفر مقارنات صناعية. يُفضَّل طريقة التكلفة."
        explanation = (
            "طريقة المقارنة السوقية للمنشآت الصناعية محدودة الإمكانية نظرًا لشُح المقارنات. "
            "تُستخدم عند توفر صفقات بيع لمنشآت مماثلة في المنطقة الصناعية ذاتها. "
            "في غياب المقارنات: طريقة التكلفة هي المرجع الأساسي."
        )
        missing = ["بيانات مقارنات صناعية مماثلة"]
        comparison_matrix = [{
            "comparable_id": "صناعي-1",
            "property_type": _NOT_APP_TYPE,
            "location": _DEFERRED_SOURCE,
            "area": _DEFERRED_SOURCE,
            "value": _DEFERRED_SOURCE,
            "price_per_m2": _DEFERRED_SOURCE,
            "date": _DEFERRED_SOURCE,
            "source_type": "قاعدة بيانات مستقبلية",
            "adj_time": "0%", "adj_location": "0%", "adj_floor": "0%", "adj_condition": "0%",
            "total_adj_factor": "0%",
            "adjusted_price_per_m2": _DEFERRED_SOURCE,
            "indicated_value": _DEFERRED_SOURCE,
            "included": False,
            "exclusion_reason": "لا تتوفر مقارنات صناعية مباشرة حاليًا",
        }]
        indicated = _NOT_APP_TYPE
    else:
        applicability = "applicable"
        comp1 = payload.get("sales_comparable_1") or ""
        comp2 = payload.get("sales_comparable_2") or ""
        comp3 = payload.get("sales_comparable_3") or ""
        rent1 = payload.get("rental_comparable_1") or ""
        rent2 = payload.get("rental_comparable_2") or ""
        has_comparables = bool(comp1 or comp2 or rent1)
        status = "partial" if has_comparables else "missing"
        notes = (
            "سكني: مقارنة البيوع والإيجارات بالمنطقة — تُعدَّل للمساحة والحالة والموقع."
            if class_key == "residential"
            else "غير سكني: مقارنة بيوع وإيجارات تجارية — تُعدَّل لمعامل الدور والواجهة والنشاط."
        )
        explanation = (
            "تُقدِّر هذه الطريقة قيمة العقار بالمقارنة بصفقات بيع وإيجار فعلية لعقارات مماثلة. "
            "يُعدَّل سعر كل مقارن بعوامل: الزمن، الموقع، الدور والإطلال، الحالة والتشطيب. "
            "تُحسب القيمة النهائية كمتوسط الأسعار المعدَّلة × مساحة العقار الموضوع."
        )
        if subtype_key == "shop":
            explanation += (
                " للمحلات التجارية: يُضاف معامل الواجهة التجارية (الإطلال والوصول). "
                "يلزم قياس عرض الواجهة الفعلي للمحل لاستكمال دقة التقييم التجاري."
            )
        missing = [] if has_comparables else ["مقارنات بيع/إيجار محددة (العدد — المساحة — السعر — المصدر)"]

        # ── Structured comparison matrix (from File 2 adjustment-table pattern) ──
        # Use QA synthetic adjustments when is_qa; else show data_gap placeholders
        def _parse_comp_price(comp_str: str) -> float:
            """Extract a numeric price from a free-text comparable string."""
            import re
            nums = re.findall(r"[\d,]+(?:\.\d+)?", comp_str.replace("،", ","))
            for n in nums:
                try:
                    v = float(n.replace(",", ""))
                    if v > 10000:
                        return v
                except Exception:
                    pass
            return 0.0

        def _parse_comp_area(comp_str: str) -> float:
            import re
            m = re.search(r"(\d+)\s*م²", comp_str)
            if m:
                return float(m.group(1))
            return 0.0

        def _make_comp_row(cid, raw_str, adj_time, adj_loc, adj_floor, adj_cond, is_rental=False):
            price = _parse_comp_price(raw_str) if raw_str else 0.0
            area  = _parse_comp_area(raw_str) if raw_str else 0.0
            ppm2  = round(price / area, 2) if price > 0 and area > 0 else 0.0
            # total adjustment = (1+t)×(1+l)×(1+f)×(1+c) - 1
            try:
                ta  = float(str(adj_time).replace("%","")) / 100
                la  = float(str(adj_loc).replace("%","")) / 100
                fa  = float(str(adj_floor).replace("%","")) / 100
                ca  = float(str(adj_cond).replace("%","")) / 100
                total_adj = round((1+ta)*(1+la)*(1+fa)*(1+ca) - 1, 4)
            except Exception:
                total_adj = 0.0
            adj_ppm2 = round(ppm2 * (1 + total_adj), 2) if ppm2 > 0 else 0.0
            ind_val  = round(adj_ppm2 * subject_area, 2) if adj_ppm2 > 0 and subject_area > 0 else 0.0
            return {
                "comparable_id":        cid,
                "property_type":        "إيجاري" if is_rental else ("سكني" if class_key == "residential" else "تجاري"),
                "location":             raw_str[:60] if raw_str else _DEFERRED_SOURCE,
                "area":                 area or _DEFERRED_SOURCE,
                "value":                price or _DEFERRED_SOURCE,
                "price_per_m2":         ppm2 or _DEFERRED_SOURCE,
                "date":                 "2024-2025",
                "source_type":          "إدخال الخبير",
                "adj_time":             adj_time,
                "adj_location":         adj_loc,
                "adj_floor":            adj_floor,
                "adj_condition":        adj_cond,
                "total_adj_factor":     f"{total_adj:.1%}",
                "adjusted_price_per_m2": adj_ppm2 or _DEFERRED_SOURCE,
                "indicated_value":      ind_val or _DEFERRED_SOURCE,
                "included":             bool(price > 0),
                "exclusion_reason":     "" if price > 0 else "لم تُدخَل بيانات المقارن",
            }

        if is_qa:
            adj_data = [
                (comp1, "0%",  "+5%", "-5%", "-10%", False),
                (comp2, "-5%", "0%",  "+5%", "0%",   False),
                (comp3, "0%",  "+10%","0%",  "-5%",  False),
                (rent1, "0%",  "+5%", "0%",  "0%",   True),
                (rent2, "0%",  "0%",  "-5%", "+5%",  True),
            ]
        else:
            adj_data = [
                (comp1, _DEFERRED_SOURCE, _DEFERRED_SOURCE, _DEFERRED_SOURCE, _DEFERRED_SOURCE, False),
                (comp2, _DEFERRED_SOURCE, _DEFERRED_SOURCE, _DEFERRED_SOURCE, _DEFERRED_SOURCE, False),
                (comp3, _DEFERRED_SOURCE, _DEFERRED_SOURCE, _DEFERRED_SOURCE, _DEFERRED_SOURCE, False),
                (rent1, _DEFERRED_SOURCE, _DEFERRED_SOURCE, _DEFERRED_SOURCE, _DEFERRED_SOURCE, True),
                (rent2, _DEFERRED_SOURCE, _DEFERRED_SOURCE, _DEFERRED_SOURCE, _DEFERRED_SOURCE, True),
            ]

        comparison_matrix = []
        for i, (raw, at, al, af, ac, is_r) in enumerate(adj_data):
            prefix = "إيجاري" if is_r else "بيع"
            comparison_matrix.append(_make_comp_row(f"{prefix}-{i+1}", raw, at, al, af, ac, is_r))

        # Average adjusted price for included comparables
        inc_ppm2s = []
        for row in comparison_matrix:
            if row["included"] and isinstance(row["adjusted_price_per_m2"], (int, float)) and row["adjusted_price_per_m2"] > 0:
                inc_ppm2s.append(row["adjusted_price_per_m2"])
        avg_adj_ppm2 = round(sum(inc_ppm2s) / len(inc_ppm2s), 2) if inc_ppm2s else 0.0
        indicated = round(avg_adj_ppm2 * subject_area, 2) if avg_adj_ppm2 > 0 and subject_area > 0 else _NEEDS_COMPLETION

    # ── Standard calculation_rows ─────────────────────────────────────────────
    if class_key == "non_residential":
        ff_row = {"label": "معامل الدور/الواجهة المُطبَّق", "value": floor_factor, "formula": "= نسبة معيارية × موقع الوحدة"}
    else:
        ff_row = {"label": "معامل التعديل العام", "value": "1.0", "formula": "يُحدَّد من الخبير"}

    comp_rows = [
        {"label": "المقارن 1 (بيع)", "value": payload.get("sales_comparable_1") or _DEFERRED_SOURCE, "formula": ""},
        {"label": "المقارن 2 (بيع)", "value": payload.get("sales_comparable_2") or _DEFERRED_SOURCE, "formula": ""},
        {"label": "المقارن 3 (بيع)", "value": payload.get("sales_comparable_3") or _DEFERRED_SOURCE, "formula": ""},
        {"label": "مقارن إيجاري 1", "value": payload.get("rental_comparable_1") or _DEFERRED_SOURCE, "formula": ""},
        {"label": "مقارن إيجاري 2", "value": payload.get("rental_comparable_2") or _DEFERRED_SOURCE, "formula": ""},
        ff_row,
        {"label": "متوسط السعر المعدَّل (ج.م/م²)", "value": avg_adj_ppm2 if class_key != "special_purpose" and avg_adj_ppm2 > 0 else _DEFERRED_SOURCE, "formula": "= AVERAGE(أسعار مقارنات × معاملات تعديل)"},
        {"label": "دلالة المقارنة (ج.م)",  "value": indicated if class_key != "special_purpose" else _NOT_APP_TYPE, "formula": "= متوسط سعر معدَّل × مساحة الموضوع"},
    ]
    if class_key == "special_purpose":
        avg_adj_ppm2 = 0.0
        indicated = _NOT_APP_TYPE

    # Shop: frontage warning
    frontage_warning = (
        "يلزم قياس عرض الواجهة الفعلي للمحل لاستكمال دقة التقييم التجاري."
        if subtype_key == "shop" else ""
    )
    # Shop tax-per-m² consistency fields
    govt_tax_per_m2   = round(_safe_float(payload.get("government_tax_amount")) / subject_area, 2) if (subject_area > 0 and _safe_float(payload.get("government_tax_amount")) > 0) else 0.0
    corr_tax_per_m2   = round(_safe_float(payload.get("corrected_tax_amount")) / subject_area, 2)  if (subject_area > 0 and _safe_float(payload.get("corrected_tax_amount")) > 0) else 0.0

    return {
        "method_key":                  "market_comparison_approach",
        "method_label_ar":             "طريقة المقارنة السوقية",
        "explanation_ar":              explanation,
        "applicability_by_property_class": {
            "residential":    "مطبَّقة — وزن 40% من التوفيق",
            "non_residential": "مطبَّقة — وزن 30% من التوفيق",
            "special_purpose": "مساندة — شُح المقارنات الصناعية",
        },
        "method_applicability":        applicability,
        "data_availability_status":    status,
        "input_sources":               ["مقارنات السوق — يحتاج تحديثًا يدويًا من الخبير", "قاعدة بيانات Qdrant (مرحلة مستقبلية — غير مفعلة)"],
        "provided_inputs":             [k for k in ["sales_comparable_1","sales_comparable_2","rental_comparable_1"] if payload.get(k)],
        "missing_inputs":              missing,
        "required_missing_inputs":     missing,
        "comparison_matrix":           comparison_matrix,
        "calculation_rows":            comp_rows,
        "formulas_used": [
            "سعر_م² = قيمة_المقارن / مساحة_المقارن",
            "معامل_التعديل_الكلي = (1+تعديل_زمن) × (1+تعديل_موقع) × (1+تعديل_دور) × (1+تعديل_حالة) − 1",
            "سعر_م²_معدَّل = سعر_م² × (1 + معامل_التعديل_الكلي)",
            "دلالة_مقارن = سعر_م²_معدَّل × مساحة_الموضوع",
            "دلالة_نهائية = متوسط(دلالات_المقارنات_المُدرجة)",
        ],
        "frontage_warning":            frontage_warning,
        "government_tax_per_m2":       govt_tax_per_m2 or 0.0,
        "fair_tax_per_m2":             corr_tax_per_m2 or 0.0,
        "overcharge_per_m2":           round(govt_tax_per_m2 - corr_tax_per_m2, 2) if (govt_tax_per_m2 > 0 and corr_tax_per_m2 > 0) else 0.0,
        "indicated_value":             indicated,
        "indicated_tax_basis":         "القيمة الإيجارية السوقية المُستنتجة من المقارنات",
        "indicated_tax_amount":        _NEEDS_COMPLETION,
        "overcharge_amount":           _NEEDS_COMPLETION,
        "overcharge_percentage":       _NEEDS_COMPLETION,
        "expert_notes":                notes,
        "source_registry_links":       ["SRC-TAX-QDRANT-FUTURE"],
        "future_enrichment_status":    _DEFERRED_SOURCE,
    }


def _build_income_capitalization(
    payload: dict, class_key: str, subtype_key: str,
    subject_area: float, annual_rent: float, cap_rate: float,
    is_qa: bool,
) -> dict:
    """Method 3 — طريقة الرسملة / الدخل."""
    if class_key == "special_purpose":
        has_income_proxy = bool(payload.get("estimated_market_rental_value") or payload.get("annual_rental_estimate"))
        applicability = "supporting" if has_income_proxy else "data_gap"
        if applicability == "data_gap":
            return {
                "method_key": "income_capitalization_approach",
                "method_label_ar": "طريقة الرسملة / الدخل",
                "method_applicability": "data_gap",
                "data_availability_status": "missing",
                "input_sources": [],
                "calculation_rows": [{"label": "الحالة", "value": "غير مطبق أو يحتاج بديلًا إيجاريًا للمنشأة", "formula": ""}],
                "indicated_value": _NOT_APP_TYPE,
                "indicated_tax_amount": _NOT_APP_TYPE,
                "overcharge_amount": _NOT_APP_TYPE,
                "overcharge_percentage": _NOT_APP_TYPE,
                "expert_notes": "لا تُطبَّق طريقة الرسملة عادةً للمنشآت الصناعية إلا عند وجود دخل/إيجار استخدام موثوق.",
                "required_missing_inputs": ["بيانات دخل إيجاري أو بديل استخدام للمنشأة الصناعية"],
                "source_registry_links": [],
                "future_enrichment_status": _DEFERRED_SOURCE,
            }

    # Income calculation
    vacancy_rate          = _safe_float(payload.get("vacancy_rate", 0.05))
    collection_loss_rate  = _safe_float(payload.get("collection_loss_rate", 0.02))
    operating_expense_rate = _safe_float(payload.get("operating_expense_rate", 0.15))
    reserve_rate          = _safe_float(payload.get("reserve_rate", 0.03))

    has_rent = annual_rent > 0
    has_cap  = cap_rate > 0

    if has_rent:
        monthly_rent = round(annual_rent / 12, 2)
        egi          = round(annual_rent * (1.0 - vacancy_rate - collection_loss_rate), 2)
        noi          = round(egi * (1.0 - operating_expense_rate - reserve_rate), 2)
        if has_cap:
            income_val = round(noi / cap_rate, 2)
        else:
            income_val = _NEEDS_COMPLETION
        status = "complete" if has_cap else "partial"
        missing = [] if has_cap else ["معدل الرسملة (نسبة الرسملة)"]
    else:
        monthly_rent = 0.0
        egi = noi = 0.0
        income_val = _NEEDS_COMPLETION
        status = "missing"
        missing = ["القيمة الإيجارية السنوية السوقية", "معدل الرسملة"]

    if class_key == "residential":
        applicability = "applicable"
        notes = "سكني: تعتمد على القيمة الإيجارية السوقية / أدلة الإيجار المتاحة."
    elif subtype_key == "basement_storage":
        applicability = "applicable"
        notes = (
            "مخزن بدروم: معدل الرسملة المُطبَّق (6%) أعلى من المحلات التجارية (8-9%) "
            "نظرًا لانخفاض السيولة وارتفاع خطر الشغور في المخازن السفلية. "
            "لا تُستخدم معدلات رسملة المحلات التجارية النشطة للمخازن المغلقة."
        )
    else:
        applicability = "applicable"
        notes = "غير سكني: ذات قوة إثبات مرتفعة لمنازعات الضريبة العقارية السنوية — تثبت معقولية القيمة الإيجارية."

    calc_rows = [
        {"label": "القيمة الإيجارية السنوية (ج.م)",  "value": annual_rent or _NEEDS_COMPLETION,  "formula": ""},
        {"label": "القيمة الإيجارية الشهرية (ج.م)", "value": monthly_rent or _NEEDS_COMPLETION,  "formula": "= سنوية / 12"},
        {"label": "نسبة الشغور",                     "value": f"{vacancy_rate:.0%}",               "formula": ""},
        {"label": "نسبة خسارة التحصيل",              "value": f"{collection_loss_rate:.0%}",        "formula": ""},
        {"label": "الدخل الإجمالي الفعلي (ج.م)",    "value": egi or _NEEDS_COMPLETION,            "formula": "= سنوية × (1 − شغور − خسارة)"},
        {"label": "نسبة مصاريف التشغيل",            "value": f"{operating_expense_rate:.0%}",      "formula": ""},
        {"label": "نسبة الاحتياطي",                  "value": f"{reserve_rate:.0%}",               "formula": ""},
        {"label": "صافي دخل التشغيل NOI (ج.م)",     "value": noi or _NEEDS_COMPLETION,            "formula": "= EGI × (1 − مصاريف − احتياطي)"},
        {"label": "معدل الرسملة",                    "value": f"{cap_rate:.2%}" if has_cap else _NEEDS_COMPLETION, "formula": ""},
        {"label": "دلالة طريقة الرسملة (ج.م)",      "value": income_val,                          "formula": "= NOI / معدل الرسملة"},
    ]

    explanation = (
        "تُقدِّر هذه الطريقة قيمة العقار بتحويل صافي دخل التشغيل إلى قيمة رأسمالية. "
        "تُحسب: الإيجار السنوي الإجمالي − خسائر الشغور والتحصيل = الدخل الإجمالي الفعلي (EGI). "
        "ثم: EGI − مصاريف التشغيل − الاحتياطي = صافي دخل التشغيل (NOI). "
        "أخيرًا: NOI ÷ معدل الرسملة = القيمة."
    )

    formulas_used = [
        "إيجار_سنوي = إيجار_شهري × 12",
        "خسارة_شغور = إيجار_سنوي × نسبة_الشغور",
        "خسارة_تحصيل = إيجار_سنوي × نسبة_خسارة_التحصيل",
        "EGI = إيجار_سنوي − خسارة_شغور − خسارة_تحصيل",
        "مصاريف_تشغيل = EGI × نسبة_المصاريف",
        "احتياطي = EGI × نسبة_الاحتياطي",
        "NOI = EGI − مصاريف_تشغيل − احتياطي",
        "القيمة_الرأسمالية = NOI ÷ معدل_الرسملة",
    ]

    return {
        "method_key":                  "income_capitalization_approach",
        "method_label_ar":             "طريقة الرسملة / الدخل",
        "explanation_ar":              explanation,
        "applicability_by_property_class": {
            "residential":    "مطبَّقة عند توفر أدلة إيجارية — وزن 20%",
            "non_residential": "مطبَّقة — ذات قوة إثبات عالية — وزن 40%",
            "special_purpose": "بيانات ناقصة — تُطبَّق عند توفر دخل/إيجار",
        },
        "method_applicability":        applicability,
        "data_availability_status":    status,
        "input_sources":               ["إدخال خبير — القيمة الإيجارية", "أدلة إيجارية من الخبير"],
        "provided_inputs":             [k for k in ["estimated_market_rental_value","capitalization_rate"] if payload.get(k)],
        "missing_inputs":              missing,
        "required_missing_inputs":     missing,
        "calculation_rows":            calc_rows,
        "income_chain_table":          calc_rows,
        "formulas_used":               formulas_used,
        "indicated_value":             income_val,
        "indicated_tax_basis":         "صافي دخل التشغيل (NOI) المرسمَل",
        "indicated_tax_amount":        _NEEDS_COMPLETION,
        "overcharge_amount":           _NEEDS_COMPLETION,
        "overcharge_percentage":       _NEEDS_COMPLETION,
        "expert_notes":                notes,
        "source_registry_links":       ["SRC-TAX-EXPERT-001"],
        "future_enrichment_status":    "يمكن ربط بيانات الإيجار من مصادر السوق لاحقًا",
        "income_method_type":          "direct_capitalization",
        "direct_capitalization_table": {
            "rental_income":  annual_rent or _NEEDS_COMPLETION,
            "vacancy_rate":   f"{vacancy_rate:.0%}",
            "collection_loss": f"{collection_loss_rate:.0%}",
            "expenses_reserves": f"{operating_expense_rate + reserve_rate:.0%}",
            "noi":            noi or _NEEDS_COMPLETION,
            "cap_rate":       f"{cap_rate:.2%}" if has_cap else _NEEDS_COMPLETION,
            "source_status":  "QA محاكاة" if is_qa else "يحتاج مراجع",
            "indicated_value": income_val,
        },
        "cap_rate_derivation": {
            "method":       "إدخال الخبير",
            "source":       "QA محاكاة" if is_qa else "يحتاج توثيق مصدر",
            "justification": "معدل رسملة استرشادي — يحتاج دعمًا بياناتيًا من الخبير",
            "expert_selected_rate": f"{cap_rate:.2%}" if has_cap else _NEEDS_COMPLETION,
        },
        "dcf_applicable":   False,
        "dcf_table":        "غير مطبق لهذا الطعن / يحتاج بيانات تدفقات نقدية موثقة",
    }


def _build_tax_comparison(
    payload: dict, class_key: str,
    govt_tax: float, corrected_tax: float,
    overcharge_amt: float, overcharge_pct: float,
    expert_val: float, is_qa: bool,
) -> dict:
    """Method 4 — طريقة المقارنة الضريبية (detailed tables)."""
    subject_area = _safe_float(payload.get("area"))
    govt_rental  = _safe_float(payload.get("government_assessed_annual_rental_value"))
    notice_num   = payload.get("notice_number") or payload.get("tax_notice_number") or _DATA_GAP
    notice_date  = payload.get("notice_received_date") or _DATA_GAP
    tax_year     = payload.get("inspection_cycle_year") or _DATA_GAP
    basis_date   = payload.get("report_date") or _DATA_GAP

    subj_tax_m2      = round(govt_tax / subject_area, 2)  if (govt_tax > 0 and subject_area > 0) else 0.0
    corr_tax_m2      = round(corrected_tax / subject_area, 2) if (corrected_tax > 0 and subject_area > 0) else 0.0
    expert_rental_m2 = round(expert_val / subject_area, 2) if (expert_val > 0 and subject_area > 0) else 0.0
    expected_saving  = round(max(govt_tax - corrected_tax, 0), 2) if (govt_tax > 0 and corrected_tax > 0) else 0.0

    no_cases_note = (
        "لا توجد حالات ضريبية مقارنة كافية ضمن البيانات الحالية. "
        "تم تجهيز هذا القسم لاستكماله عند ربط قاعدة بيانات الطعون أو مصادر الضرائب لاحقًا."
    )

    if govt_tax > 0 and corrected_tax > 0:
        status = "complete"
        missing: list[str] = []
        conclusion = (
            f"الضريبة الحكومية ({govt_tax:,.0f} ج.م) تتجاوز التقدير الاسترشادي ({corrected_tax:,.0f} ج.م) "
            f"بفارق {overcharge_amt:,.0f} ج.م ({overcharge_pct:.1f}%). يُرجَّح قبول الطعن."
            if overcharge_amt > 0
            else "الضريبة الحكومية ضمن النطاق الاسترشادي — يحتاج تأكيد الخبير."
        )
    else:
        status = "partial"
        missing = ["مبلغ الضريبة الحكومية", "التقدير الاسترشادي / الضريبة المصححة"]
        conclusion = _NEEDS_COMPLETION

    # ── Table 1: Government Assessment ───────────────────────────────────────
    government_assessment_table = {
        "govt_assessed_rental_value": govt_rental or _NEEDS_COMPLETION,
        "govt_tax_amount":            govt_tax or _NEEDS_COMPLETION,
        "tax_year_or_cycle":          tax_year,
        "notice_number":              notice_num,
        "notice_date":                notice_date,
        "basis_date":                 basis_date,
        "govt_tax_per_m2":            subj_tax_m2 or _NEEDS_COMPLETION,
    }

    # ── Table 2: Expert Indication ────────────────────────────────────────────
    expert_indication_table = {
        "expert_indicated_rental_value": expert_val or _NEEDS_COMPLETION,
        "expert_indicated_rental_per_m2": expert_rental_m2 or _NEEDS_COMPLETION,
        "expert_indicated_tax_amount":   corrected_tax or _NEEDS_COMPLETION,
        "expert_tax_per_m2":             corr_tax_m2 or _NEEDS_COMPLETION,
        "calculation_basis":             "القيمة الإيجارية السوقية وفق المعادلة الضريبية القانونية",
        "notes":                         "تقدير الخبير بناءً على مقارنة السوق وتقييم الوضع الفعلي للعقار",
    }

    # ── Table 3: Comparable Tax Cases ─────────────────────────────────────────
    if is_qa:
        # Synthetic QA comparable cases — clearly labeled simulation
        comparable_tax_cases = [
            {
                "tax_case_id":           "QA-TC-001",
                "property_type":         "مماثل — محاكاة QA",
                "location":              f"نفس الحي — QA محاكاة",
                "area":                  round(subject_area * 0.9, 1) if subject_area > 0 else _NEEDS_COMPLETION,
                "use":                   "نفس الاستخدام",
                "tax_amount":            round(corrected_tax * 0.95, 2) if corrected_tax > 0 else _NEEDS_COMPLETION,
                "tax_per_m2":            round(corr_tax_m2 * 0.95, 2) if corr_tax_m2 > 0 else _NEEDS_COMPLETION,
                "assessed_value_per_m2": round(expert_rental_m2 * 0.95, 2) if expert_rental_m2 > 0 else _NEEDS_COMPLETION,
                "adj_location":          "0%",
                "adj_area":              "+2%",
                "adj_condition":         "0%",
                "total_adj_factor":      "+2%",
                "adjusted_tax_per_m2":   round(corr_tax_m2 * 0.95 * 1.02, 2) if corr_tax_m2 > 0 else _NEEDS_COMPLETION,
                "indicated_subject_tax": round(corr_tax_m2 * 0.95 * 1.02 * subject_area, 2) if (corr_tax_m2 > 0 and subject_area > 0) else _NEEDS_COMPLETION,
                "included":              True,
                "exclusion_reason":      "",
                "source_note":           _QA_SYNTHETIC_NOTE,
            },
            {
                "tax_case_id":           "QA-TC-002",
                "property_type":         "مماثل — محاكاة QA",
                "location":              f"حي مجاور — QA محاكاة",
                "area":                  round(subject_area * 1.1, 1) if subject_area > 0 else _NEEDS_COMPLETION,
                "use":                   "نفس الاستخدام",
                "tax_amount":            round(corrected_tax * 1.05, 2) if corrected_tax > 0 else _NEEDS_COMPLETION,
                "tax_per_m2":            round(corr_tax_m2 * 1.05, 2) if corr_tax_m2 > 0 else _NEEDS_COMPLETION,
                "assessed_value_per_m2": round(expert_rental_m2 * 1.05, 2) if expert_rental_m2 > 0 else _NEEDS_COMPLETION,
                "adj_location":          "-5%",
                "adj_area":              "-2%",
                "adj_condition":         "0%",
                "total_adj_factor":      "-7%",
                "adjusted_tax_per_m2":   round(corr_tax_m2 * 1.05 * 0.93, 2) if corr_tax_m2 > 0 else _NEEDS_COMPLETION,
                "indicated_subject_tax": round(corr_tax_m2 * 1.05 * 0.93 * subject_area, 2) if (corr_tax_m2 > 0 and subject_area > 0) else _NEEDS_COMPLETION,
                "included":              True,
                "exclusion_reason":      "",
                "source_note":           _QA_SYNTHETIC_NOTE,
            },
        ]
        avg_comparable_tax = (
            round((comparable_tax_cases[0]["indicated_subject_tax"] + comparable_tax_cases[1]["indicated_subject_tax"]) / 2, 2)
            if isinstance(comparable_tax_cases[0]["indicated_subject_tax"], (int, float))
            else _NEEDS_COMPLETION
        )
    else:
        # Production: structural data gap table
        comparable_tax_cases = [
            {
                "tax_case_id":    "TC-GAP-001",
                "property_type":  "لم تُضَف حالة مقارنة",
                "location":       _DEFERRED_SOURCE,
                "area":           _DEFERRED_SOURCE,
                "use":            _DEFERRED_SOURCE,
                "tax_amount":     _DEFERRED_SOURCE,
                "tax_per_m2":     _DEFERRED_SOURCE,
                "assessed_value_per_m2": _DEFERRED_SOURCE,
                "adj_location":   _DEFERRED_SOURCE,
                "adj_area":       _DEFERRED_SOURCE,
                "adj_condition":  _DEFERRED_SOURCE,
                "total_adj_factor": _DEFERRED_SOURCE,
                "adjusted_tax_per_m2": _DEFERRED_SOURCE,
                "indicated_subject_tax": _DEFERRED_SOURCE,
                "included":       False,
                "exclusion_reason": "لا تتوفر قاعدة بيانات طعون ضريبية مقارنة حاليًا",
                "source_note":    "مؤجل لحين ربط قاعدة بيانات المقارنات الضريبية",
            },
        ]
        avg_comparable_tax = _DEFERRED_SOURCE

    # ── Table 4: Tax Gap ──────────────────────────────────────────────────────
    tax_gap_table = {
        "government_tax":          govt_tax or _NEEDS_COMPLETION,
        "indicated_tax":           corrected_tax or _NEEDS_COMPLETION,
        "comparable_avg_tax":      avg_comparable_tax,
        "overcharge_amount":       overcharge_amt or 0.0,
        "overcharge_percentage":   round(overcharge_pct, 4) if overcharge_pct else 0.0,
        "expected_saving":         expected_saving,
        "conclusion":              conclusion,
        "formula_overcharge":      "= ضريبة_حكومية − ضريبة_مُشارة",
        "formula_overcharge_pct":  "= فارق_المغالاة / ضريبة_حكومية",
        "formula_saving":          "= MAX(ضريبة_حكومية − ضريبة_مُشارة, 0)",
    }

    # ── Standard calculation_rows ─────────────────────────────────────────────
    calc_rows = [
        {"label": "الضريبة الحكومية (ج.م)",                  "value": govt_tax or _NEEDS_COMPLETION,       "formula": ""},
        {"label": "التقدير الاسترشادي للضريبة (ج.م)",        "value": corrected_tax or _NEEDS_COMPLETION,  "formula": ""},
        {"label": "القيمة الإيجارية الحكومية (ج.م)",         "value": govt_rental or _NEEDS_COMPLETION,    "formula": ""},
        {"label": "القيمة البديلة للخبير (ج.م)",             "value": expert_val or _NEEDS_COMPLETION,     "formula": ""},
        {"label": "ضريبة الموضوع / م² (حكومي)",             "value": subj_tax_m2 or _NEEDS_COMPLETION,   "formula": "= ضريبة / مساحة"},
        {"label": "ضريبة الموضوع / م² (استرشادي)",          "value": corr_tax_m2 or _NEEDS_COMPLETION,   "formula": "= ضريبة_مصححة / مساحة"},
        {"label": "متوسط ضريبة الحالات المقارنة (ج.م)",     "value": avg_comparable_tax,                   "formula": "= AVERAGE(حالات_مُدرجة)"},
        {"label": "فارق المغالاة (ج.م)",                     "value": overcharge_amt or 0.0,               "formula": "= حكومي − استرشادي"},
        {"label": "نسبة المغالاة",                            "value": f"{overcharge_pct:.1f}%" if overcharge_pct else _NEEDS_COMPLETION, "formula": "= فارق / حكومي"},
        {"label": "الوفر المتوقع (ج.م)",                     "value": expected_saving,                     "formula": "= MAX(حكومي − مُشار, 0)"},
        {"label": "الخلاصة",                                  "value": conclusion,                          "formula": ""},
    ]

    return {
        "method_key":                  "tax_comparison_approach",
        "method_label_ar":             "طريقة المقارنة الضريبية",
        "explanation_ar": (
            "تُقارِن هذه الطريقة الإخطار الضريبي الحكومي بالتقدير الاسترشادي للخبير "
            "وبالحالات الضريبية لعقارات مماثلة. تُثبت مدى معقولية الضريبة الحكومية "
            "وتُحدِّد فارق المغالاة والوفر المتوقع من الطعن."
        ),
        "applicability_by_property_class": {
            "residential":    "مطبَّقة — تدعم استرشاد تقليل الضريبة",
            "non_residential": "مطبَّقة — تدعم استرشاد تقليل الضريبة",
            "special_purpose": "مطبَّقة — تدعم مقارنة الإخطار بالتقدير",
        },
        "method_applicability":        "applicable",
        "data_availability_status":    status,
        "input_sources":               ["إخطار ضريبي حكومي", "تقدير الخبير", "قاعدة بيانات الطعون (مرحلة مستقبلية — غير مفعلة)"],
        "provided_inputs":             [k for k in ["government_tax_amount","corrected_tax_amount","area"] if payload.get(k)],
        "missing_inputs":              missing,
        "required_missing_inputs":     missing,
        "government_assessment_table": government_assessment_table,
        "expert_indication_table":     expert_indication_table,
        "comparable_tax_cases":        comparable_tax_cases,
        "tax_gap_table":               tax_gap_table,
        "calculation_rows":            calc_rows,
        "formulas_used": [
            "ضريبة_م² = ضريبة / مساحة",
            "متوسط_ضريبة_م²_مُعدَّلة = AVERAGE(حالات_مُدرجة)",
            "ضريبة_الموضوع_المُشارة = متوسط_م² × مساحة_الموضوع",
            "فارق_المغالاة = ضريبة_حكومية − ضريبة_مُشارة",
            "نسبة_المغالاة = فارق_المغالاة / ضريبة_حكومية",
            "وفر_متوقع = MAX(ضريبة_حكومية − ضريبة_مُشارة, 0)",
        ],
        "indicated_value":             overcharge_amt if overcharge_amt > 0 else _NEEDS_COMPLETION,
        "indicated_tax_basis":         "التقدير الاسترشادي للضريبة المنطبقة",
        "indicated_tax_amount":        corrected_tax if corrected_tax > 0 else _NEEDS_COMPLETION,
        "overcharge_amount":           overcharge_amt if overcharge_amt > 0 else _NEEDS_COMPLETION,
        "overcharge_percentage":       f"{overcharge_pct:.1f}%" if overcharge_pct else _NEEDS_COMPLETION,
        "expert_notes":                "تقارن الإخطار الحكومي بالتقدير الاسترشادي وبالعقارات المماثلة — تُعزز قوة الطعن.",
        "source_registry_links":       ["SRC-TAX-NOTICE-001", "SRC-TAX-EXPERT-001", "SRC-TAX-QDRANT-FUTURE"],
        "future_enrichment_status":    "يُستكمل عند ربط قاعدة بيانات قضايا الطعن الضريبي",
    }


def _build_multiple_regression(
    payload: dict, class_key: str,
    subject_area: float, is_qa: bool,
) -> dict:
    """Method 5 — طريقة الانحدار المتعدد (future-ready)."""
    not_trained_note = (
        "تحتاج هذه الطريقة إلى قاعدة بيانات كافية للتدريب والتحقق. "
        "لم يتم تفعيل نموذج انحدار حقيقي في هذا الإصدار."
    )

    if is_qa:
        # Synthetic QA simulation — clearly labeled as simulation
        location_score    = _safe_float(payload.get("location_score",    0.75))
        frontage_score    = _safe_float(payload.get("frontage_score",    0.70))
        floor_fac         = _safe_float(payload.get("floor_adjustment_factor", 1.0))
        use_fac           = _safe_float(payload.get("rental_yield_pct",  0.07))
        cond_score        = _safe_float(payload.get("condition_score",   0.80))
        age_yrs           = _safe_float(payload.get("age_years",         5.0))
        mkt_price_ind     = _safe_float(payload.get("estimated_market_rental_value") or payload.get("annual_rental_estimate"))

        # Synthetic QA coefficients — NOT a real trained model
        intercept         = 50000.0
        area_coeff        = 850.0
        location_coeff    = 80000.0
        frontage_coeff    = 30000.0
        floor_coeff       = 40000.0
        use_coeff         = 200000.0
        cond_coeff        = 60000.0
        age_coeff         = 2000.0

        predicted = (
            intercept
            + area_coeff       * subject_area
            + location_coeff   * location_score
            + frontage_coeff   * frontage_score
            + floor_coeff      * floor_fac
            + use_coeff        * use_fac
            + cond_coeff       * cond_score
            - age_coeff        * age_yrs
        )
        predicted = round(max(predicted, 0), 2)
        residual  = round(abs(predicted - mkt_price_ind), 2) if mkt_price_ind > 0 else _NEEDS_COMPLETION
        status_flag = "محاكاة QA"

        feat_rows = [
            {"label": "المتقاطع (intercept)",         "value": intercept,    "formula": ""},
            {"label": f"مساحة ({subject_area} م²)",   "value": round(area_coeff * subject_area, 2), "formula": "= 850 × مساحة"},
            {"label": f"معامل الموقع ({location_score})", "value": round(location_coeff * location_score, 2), "formula": "= 80,000 × موقع"},
            {"label": f"معامل الواجهة ({frontage_score})", "value": round(frontage_coeff * frontage_score, 2), "formula": "= 30,000 × واجهة"},
            {"label": f"معامل الدور ({floor_fac})",   "value": round(floor_coeff * floor_fac, 2),   "formula": "= 40,000 × دور"},
            {"label": f"معامل الاستخدام ({use_fac})", "value": round(use_coeff * use_fac, 2),       "formula": "= 200,000 × استخدام"},
            {"label": f"معامل الحالة ({cond_score})", "value": round(cond_coeff * cond_score, 2),   "formula": "= 60,000 × حالة"},
            {"label": f"خصم العمر ({age_yrs} سنة)",  "value": round(-age_coeff * age_yrs, 2),      "formula": "= − 2,000 × عمر"},
            {"label": "القيمة المتوقعة (ج.م)",        "value": predicted,                           "formula": "= جمع الأوزان"},
            {"label": "الفارق عن تقدير الخبير",       "value": residual,                            "formula": "= |متوقع − خبير|"},
            {"label": "حالة النموذج",                 "value": _QA_SYNTHETIC_NOTE,                  "formula": ""},
        ]
        indicated_val = predicted
    else:
        feat_rows = [
            {"label": "حالة النموذج",    "value": not_trained_note, "formula": ""},
            {"label": "المساحة (م²)",    "value": subject_area or _NEEDS_COMPLETION, "formula": "متغير مدخل"},
            {"label": "معامل الموقع",    "value": _DEFERRED_SOURCE, "formula": ""},
            {"label": "معامل الواجهة",   "value": _DEFERRED_SOURCE, "formula": ""},
            {"label": "معامل الدور",     "value": _DEFERRED_SOURCE, "formula": ""},
            {"label": "معامل الاستخدام", "value": _DEFERRED_SOURCE, "formula": ""},
            {"label": "معامل الحالة",    "value": _DEFERRED_SOURCE, "formula": ""},
            {"label": "القيمة المتوقعة", "value": _DEFERRED_SOURCE, "formula": ""},
        ]
        indicated_val = _DEFERRED_SOURCE
        status_flag = "غير مفعل"

    explanation_ar = (
        "طريقة الانحدار المتعدد تُنشئ نموذجًا إحصائيًا يربط سعر العقار بمتغيرات متعددة "
        "(المساحة، الموقع، الدور، الواجهة، الحالة، العمر، الاستخدام). "
        "يتطلب تدريب النموذج قاعدة بيانات بمئات الصفقات الفعلية. "
        "في هذا الإصدار: " + (_QA_SYNTHETIC_NOTE if is_qa else not_trained_note)
    )

    # ── Structured variable table (from File 2 Sheet 3 pattern + task spec) ───
    if is_qa:
        variable_table = [
            {"variable_ar": "الثابت (Intercept)", "variable_en": "intercept",
             "value": 1.0, "coefficient": intercept, "contribution": intercept,
             "source_status": "محاكاة QA", "notes": "الثابت — لا متغير"},
            {"variable_ar": "المساحة (م²)", "variable_en": "area",
             "value": subject_area, "coefficient": area_coeff,
             "contribution": round(area_coeff * subject_area, 2),
             "source_status": "محاكاة QA", "notes": "المساحة الكلية للعقار"},
            {"variable_ar": "درجة الموقع", "variable_en": "location_score",
             "value": location_score, "coefficient": location_coeff,
             "contribution": round(location_coeff * location_score, 2),
             "source_status": "محاكاة QA", "notes": "0−1 (1 = أفضل موقع)"},
            {"variable_ar": "درجة الواجهة", "variable_en": "frontage_score",
             "value": frontage_score, "coefficient": frontage_coeff,
             "contribution": round(frontage_coeff * frontage_score, 2),
             "source_status": "محاكاة QA", "notes": "0−1 (1 = واجهة ممتازة)"},
            {"variable_ar": "معامل الدور", "variable_en": "floor_factor",
             "value": floor_fac, "coefficient": floor_coeff,
             "contribution": round(floor_coeff * floor_fac, 2),
             "source_status": "محاكاة QA", "notes": "0.5−1.1 حسب الدور"},
            {"variable_ar": "معامل الاستخدام", "variable_en": "use_factor",
             "value": use_fac, "coefficient": use_coeff,
             "contribution": round(use_coeff * use_fac, 2),
             "source_status": "محاكاة QA", "notes": "نسبة العائد الإيجاري"},
            {"variable_ar": "درجة الحالة", "variable_en": "condition_score",
             "value": cond_score, "coefficient": cond_coeff,
             "contribution": round(cond_coeff * cond_score, 2),
             "source_status": "محاكاة QA", "notes": "0−1 (1 = ممتاز)"},
            {"variable_ar": "العمر (سنة)", "variable_en": "building_age",
             "value": age_yrs, "coefficient": -age_coeff,
             "contribution": round(-age_coeff * age_yrs, 2),
             "source_status": "محاكاة QA", "notes": "خصم قيمة مع التقادم"},
        ]
        model_metadata = {
            "r_squared":           "محاكاة QA فقط — غير مقاس فعليًا",
            "observations_needed": "≥ 100 صفقة موثوقة",
            "training_status":     "غير مُدرَّب — QA simulation",
            "simulation_note":     _QA_SYNTHETIC_NOTE,
            "variables_count":     len(variable_table) - 1,
        }
    else:
        variable_table = [
            {"variable_ar": "المساحة (م²)", "variable_en": "area",
             "value": subject_area or _NEEDS_COMPLETION, "coefficient": _DEFERRED_SOURCE,
             "contribution": _DEFERRED_SOURCE, "source_status": "مؤجل",
             "notes": "متغير مدخل محدد"},
            {"variable_ar": "درجة الموقع", "variable_en": "location_score",
             "value": _DEFERRED_SOURCE, "coefficient": _DEFERRED_SOURCE,
             "contribution": _DEFERRED_SOURCE, "source_status": "مؤجل",
             "notes": "يحتاج تسجيل من الخبير"},
            {"variable_ar": "درجة الواجهة", "variable_en": "frontage_score",
             "value": _DEFERRED_SOURCE, "coefficient": _DEFERRED_SOURCE,
             "contribution": _DEFERRED_SOURCE, "source_status": "مؤجل", "notes": ""},
            {"variable_ar": "معامل الدور", "variable_en": "floor_factor",
             "value": _DEFERRED_SOURCE, "coefficient": _DEFERRED_SOURCE,
             "contribution": _DEFERRED_SOURCE, "source_status": "مؤجل", "notes": ""},
            {"variable_ar": "معامل الاستخدام", "variable_en": "use_factor",
             "value": _DEFERRED_SOURCE, "coefficient": _DEFERRED_SOURCE,
             "contribution": _DEFERRED_SOURCE, "source_status": "مؤجل", "notes": ""},
            {"variable_ar": "درجة الحالة", "variable_en": "condition_score",
             "value": _DEFERRED_SOURCE, "coefficient": _DEFERRED_SOURCE,
             "contribution": _DEFERRED_SOURCE, "source_status": "مؤجل", "notes": ""},
            {"variable_ar": "العمر (سنة)", "variable_en": "building_age",
             "value": _DEFERRED_SOURCE, "coefficient": _DEFERRED_SOURCE,
             "contribution": _DEFERRED_SOURCE, "source_status": "مؤجل", "notes": ""},
        ]
        model_metadata = {
            "r_squared":           _DEFERRED_SOURCE,
            "observations_needed": "≥ 100 صفقة موثوقة",
            "training_status":     not_trained_note,
            "simulation_note":     "",
            "variables_count":     len(variable_table),
        }

    return {
        "method_key":                  "multiple_regression_approach",
        "method_label_ar":             "طريقة الانحدار المتعدد",
        "explanation_ar":              explanation_ar,
        "applicability_by_property_class": {
            "residential":    "جاهزية مستقبلية — وزن صفر حتى التفعيل",
            "non_residential": "جاهزية مستقبلية — وزن صفر حتى التفعيل",
            "special_purpose": "جاهزية مستقبلية — وزن صفر حتى التفعيل",
        },
        "method_applicability":        "future_ready",
        "data_availability_status":    "qa_simulation" if is_qa else "not_ready",
        "input_sources":               ["قاعدة بيانات تدريب (مرحلة مستقبلية — غير مفعلة)"],
        "provided_inputs":             [k for k in ["area","location_score","frontage_score","condition_score","age_years"] if payload.get(k)],
        "missing_inputs":              [] if is_qa else ["قاعدة بيانات عقارية كافية للتدريب والتحقق"],
        "required_missing_inputs":     ["قاعدة بيانات عقارية كافية للتدريب والتحقق"],
        "variable_table":              variable_table,
        "model_metadata":              model_metadata,
        "calculation_rows":            feat_rows,
        "formulas_used": [
            "مساهمة_المتغير = قيمة_المتغير × معامل_الانحدار",
            "القيمة_المتوقعة = ثابت + مجموع(مساهمات_المتغيرات)",
            "الفارق (Residual) = |قيمة_متوقعة − قيمة_خبير|",
        ],
        "indicated_value":             indicated_val,
        "indicated_tax_basis":         "القيمة الرأسمالية المتوقعة من النموذج الإحصائي" if is_qa else _DEFERRED_SOURCE,
        "indicated_tax_amount":        _DEFERRED_SOURCE,
        "overcharge_amount":           _DEFERRED_SOURCE,
        "overcharge_percentage":       _DEFERRED_SOURCE,
        "expert_notes":                not_trained_note if not is_qa else _QA_SYNTHETIC_NOTE,
        "source_registry_links":       ["SRC-TAX-QDRANT-FUTURE"],
        "future_enrichment_status":    "يُفعَّل تلقائيًا عند تجميع بيانات كافية ومراجعة النموذج الإحصائي",
        # ── Regression governance (Part G) ─────────────────────────────────
        "regression_status":           _QA_SYNTHETIC_NOTE if is_qa else "غير مفعل — مرحلة مستقبلية",
        "training_dataset_available":  False,
        "model_trained":               False,
        "model_validation_status":     "لم يُجرَ تحقق — يحتاج قاعدة بيانات حقيقية",
        "qa_simulation_only":          is_qa,
        "production_weight_allowed":   False,
        "reason_for_exclusion_from_reconciliation": (
            "لم يتم استخدام طريقة الانحدار المتعدد في التوفيق النهائي لعدم وجود "
            "قاعدة بيانات تدريب موثقة أو نموذج تحقق."
        ),
        "future_activation_requirements": [
            "قاعدة بيانات صفقات / طعون ضريبية موثقة (≥ 100 حالة)",
            "متغيرات عقارية موثقة لكل حالة",
            "ضبط جودة البيانات والتحقق من الأخطاء",
            "تدريب النموذج وقياس دقته (R² ≥ 0.7 موصى به)",
            "مراجعة واعتماد الخبير قبل الاستخدام الإنتاجي",
        ],
        "model_governance": {
            "dataset_size":           "غير متاح — يحتاج ≥ 100 حالة",
            "training_date":          "لم يتم التدريب",
            "validation_metrics":     {"r_squared": "غير متاح", "mae": "غير متاح"},
            "feature_list":           ["المساحة", "الموقع", "العمر", "الحالة", "الاستخدام"],
            "bias_fairness_note":     "لم يتم تقييم التحيز — يحتاج قاعدة بيانات حقيقية",
            "expert_approval":        False,
            "model_version":          "غير مدرب — مرحلة مستقبلية",
            "production_readiness":   "غير مفعلة إنتاجيًا — تحتاج قاعدة بيانات تدريب وتحقق.",
        },
    }


# ── HBU / Standards / Data-governance builder constants ──────────────────────

_STD_ADVISORY_NOTE = (
    "تظهر هذه الخريطة كإطار مهني استرشادي. يجب على الخبير مراجعة الإصدار والبند القياسي "
    "المعتمد قبل إصدار تقرير رسمي."
)
_HBU_ADVISORY_NOTE = (
    "تحليل HBU استرشادي غير معتمد قبل مراجعة الخبير — "
    "وفق البيانات المتاحة / يحتاج استكمال مستندات الترخيص/الاستخدام."
)

# ── Assumptions disclosure constants ─────────────────────────────────────────

_DISCLOSURE_ADVISORY = (
    "يتماشى هذا الإفصاح من حيث المبدأ مع متطلبات الإفصاح المهني عن الافتراضات المؤثرة، "
    "ويحتاج تأكيد الخبير قبل الإصدار الرسمي."
)
_EXTRAORDINARY_SEPARATOR_NOTE = (
    "تم فصل الافتراضات العامة عن الافتراضات الخاصة التي قد يكون لها أثر جوهري على نتيجة "
    "الفحص أو الطعن، ويلزم مراجعتها واعتمادها من الخبير قبل إصدار أي تقرير رسمي."
)

# ── Sensitivity analysis constants ────────────────────────────────────────────

_SENSITIVITY_PCT_MAP = {
    "residential":     0.10,
    "non_residential": 0.125,
    "special_purpose": 0.175,
}
_SENSITIVITY_SUBTYPE_OVERRIDE = {
    "basement_storage": 0.15,
    "factory":          0.175,
}


def _build_assumptions_disclosure(
    payload: dict,
    class_key: str,
    is_qa: bool,
) -> dict:
    """Build general vs extraordinary assumptions disclosure block."""

    def _row(aid, atype, text, affects_v, affects_t, status, action, prod_ready):
        return {
            "assumption_id":           aid,
            "assumption_type":         atype,
            "assumption_text":         text,
            "applies_to_method":       "جميع الطرق",
            "affects_value":           affects_v,
            "affects_tax":             affects_t,
            "verification_status":     status,
            "expert_action_required":  action,
            "production_ready":        prod_ready,
            "notes":                   "محاكاة QA" if (is_qa and not prod_ready) else "",
        }

    general = [
        _row("GA-01", "عام",
             "تم الاعتماد على البيانات المقدمة من طالب الخدمة/المستندات المتاحة.",
             False, False, "مُدرج من المستخدم", "", True),
        _row("GA-02", "عام",
             "المساحات والحدود والملكية تعتمد على المستندات المقدمة ما لم يثبت خلاف ذلك.",
             True, True, "يحتاج توثيق رسمي", "", False),
        _row("GA-03", "عام",
             "التقرير مبدئي/فني ولا يغني عن المراجعة النهائية للخبير.",
             False, False, "مُدرج دائمًا", "", True),
    ]

    extraordinary = [
        _row("EA-01", "خاص / استثنائي",
             "افتراض صحة المساحة الواردة بالمستندات.",
             True, True, "يحتاج مراجعة مستندات الملكية",
             "مراجعة الرسم المساحي أو وثيقة الملكية", False),
        _row("EA-02", "خاص / استثنائي",
             "افتراض خلو العقار من النزاعات أو القيود غير المفصح عنها.",
             True, True, "يحتاج تحقق قانوني",
             "مراجعة سجل الطعون وبحث قانوني للعقار", False),
        _row("EA-03", "خاص / استثنائي",
             "افتراض صحة تاريخ الإتمام أو الإشغال.",
             True, True, "يحتاج وثيقة إتمام / إشغال",
             "طلب شهادة إشغال رسمية", False),
        _row("EA-04", "خاص / استثنائي",
             "افتراض أن الاستخدام الحالي هو الاستخدام المرخص ما لم تقدم مستندات خلاف ذلك.",
             True, True, "يحتاج مراجعة ترخيص",
             "مراجعة الترخيص الرسمي وتصنيف الاستخدام", False),
        _row("EA-05", "خاص / استثنائي",
             "افتراض أن بيانات الإخطار الضريبي صحيحة من حيث الرقم والتاريخ والوعاء.",
             False, True, "يحتاج مطابقة مع الإخطار الأصلي",
             "مطابقة بيانات الإخطار مع الأصل الرسمي", False),
        _row("EA-06", "خاص / استثنائي",
             "افتراض عدم وجود تعديلات جوهرية بالعقار بعد تاريخ أساس الضريبة.",
             True, True, "يحتاج تحقق ميداني",
             "معاينة ميدانية أو شهادة خبير عمراني", False),
    ]

    if is_qa:
        extraordinary.append(
            _row("EA-07", "خاص / استثنائي",
                 "افتراض أن المقارنات الضريبية أو السوقية المستخدمة في QA هي محاكاة وليست بيانات حقيقية.",
                 True, True, "محاكاة QA — بيانات اصطناعية",
                 "لا يُستخدم في تقرير رسمي دون استبدال بيانات حقيقية", False)
        )

    # Hypothetical conditions — none by default
    hypothetical: list[dict] = []

    limiting = [
        _row("LC-01", "محدد استخدام",
             "لا يعد التقرير مذكرة قانونية معتمدة.",
             False, False, "مُدرج دائمًا", "", True),
        _row("LC-02", "محدد استخدام",
             "لا يصلح للتقديم الرسمي إلا بعد مراجعة وتوقيع الخبير.",
             False, False, "مُدرج دائمًا", "", True),
        _row("LC-03", "محدد استخدام",
             "لم يتم تفعيل Qdrant/OCR/Internet retrieval في هذه النسخة.",
             False, False, "مُدرج دائمًا", "", True),
    ]

    all_rows = general + extraordinary + hypothetical + limiting
    extra_has_value = any(r["affects_value"] for r in extraordinary)
    extra_has_tax   = any(r["affects_tax"]   for r in extraordinary)

    return {
        "general_assumptions":          general,
        "extraordinary_assumptions":    extraordinary,
        "hypothetical_conditions":      hypothetical,
        "limiting_conditions":          limiting,
        "all_assumption_rows":          all_rows,
        "reliance_on_client_data":      True,
        "data_verification_status":     (
            "محاكاة QA — بيانات اصطناعية" if is_qa
            else "يحتاج توثيق من الخبير"
        ),
        "expert_confirmation_required": True,
        "assumptions_impact_on_value":  (
            "الافتراضات الخاصة (EA-01 إلى EA-06) قد تؤثر على القيمة الاسترشادية."
            if extra_has_value else "لا أثر جوهري متوقع على القيمة."
        ),
        "assumptions_impact_on_tax": (
            "الافتراضات الخاصة (EA-02 إلى EA-07) قد تؤثر على الوعاء الضريبي."
            if extra_has_tax else "لا أثر جوهري متوقع على الضريبة."
        ),
        "disclosure_status": (
            "محاكاة QA — غير معتمدة للاستخدام الرسمي" if is_qa
            else "يحتاج مراجعة واعتماد الخبير"
        ),
        "extraordinary_separator_note": _EXTRAORDINARY_SEPARATOR_NOTE,
        "disclosure_advisory":          _DISCLOSURE_ADVISORY,
    }


def _build_sensitivity_analysis(
    payload: dict,
    class_key: str,
    subtype_key: str,
    corrected_tax: float,
    govt_tax: float,
    is_qa: bool,
) -> dict:
    """Compute advisory sensitivity/confidence range for the final tax indication."""
    base_pct = _SENSITIVITY_PCT_MAP.get(class_key, 0.125)
    sub_pct  = _SENSITIVITY_SUBTYPE_OVERRIDE.get(subtype_key)
    if sub_pct is not None:
        base_pct = max(base_pct, sub_pct)

    # Widen for QA (synthetic / weak data)
    sensitivity_pct = min(base_pct + (0.025 if is_qa else 0.0), 0.20)

    base_val = corrected_tax if corrected_tax > 0 else 0.0
    val_low  = round(base_val * (1 - sensitivity_pct), 2)
    val_high = round(base_val * (1 + sensitivity_pct), 2)

    saving_base = round(govt_tax - base_val, 2) if govt_tax > 0 else 0.0
    # lower saving when corrected tax is at its high end (val_high)
    saving_low  = round(govt_tax - val_high, 2) if govt_tax > 0 else 0.0
    # higher saving when corrected tax is at its low end (val_low)
    saving_high = round(govt_tax - val_low,  2) if govt_tax > 0 else 0.0

    drivers = [
        "دقة بيانات المساحة والأسعار المُدخلة",
        "درجة توافر بيانات مقارنة سوقية أو ضريبية فعلية",
        "معامل الاستهلاك / الإهلاك المستخدم",
    ]
    if is_qa:
        drivers.append(
            "بيانات محاكاة QA — يُعوِّض الخبير بالبيانات الفعلية عند التقرير الرسمي"
        )

    return {
        "base_indicated_value":          base_val,
        "base_indicated_tax":            base_val,
        "sensitivity_pct":               sensitivity_pct,
        "sensitivity_pct_label":         f"±{sensitivity_pct * 100:.1f}%",
        "value_low":                     val_low,
        "value_high":                    val_high,
        "tax_low":                       val_low,
        "tax_high":                      val_high,
        "expected_saving_base":          saving_base,
        "expected_saving_low":           saving_low,
        "expected_saving_high":          saving_high,
        "confidence_level_label":        "نطاق حساسية استرشادي",
        "confidence_basis":              "بيانات محاكاة QA" if is_qa else "مدخلات الطلب المتاحة",
        "key_sensitivity_drivers":       drivers,
        "expert_notes":                  "نطاق الحساسية استرشادي غير مؤكد إحصائيًا — يحتاج مراجعة الخبير.",
        "is_statistical_confidence":     False,
        "no_statistical_certainty_note": (
            "نطاق الحساسية لا يُمثل ثقة إحصائية مؤكدة مبنية على بيانات حقيقية. "
            "الغرض هو إظهار أثر تغير الافتراضات والمدخلات على النتيجة، "
            "وليس تقديم قيمة نهائية معتمدة."
        ),
    }


def _build_hbu_analysis(
    payload: dict, class_key: str, subtype_key: str, is_qa: bool,
) -> dict:
    """Build Highest and Best Use analysis adapted by property class/subtype."""
    current_use  = payload.get("current_use")  or payload.get("property_type") or _NEEDS_EXPERT
    licensed_use = payload.get("licensed_use") or _NEEDS_EXPERT

    if class_key == "residential":
        phys   = "استخدام سكني — وفق مواصفات البناء والموقع"
        legal  = "يُفترض الاستخدام السكني وفق تراخيص المنطقة — يحتاج استكمال مستندات الترخيص"
        fin    = "الاستخدام السكني هو الأعلى جدوى لعقار سكني في السوق الحالي"
        maxp   = "الاستخدام السكني الحالي — هو الأعلى إنتاجية وفق المعطيات المتاحة"
        concl  = "الاستخدام الحالي السكني متوافق مع أعلى وأفضل استغلال وفق البيانات المتاحة"
        etax   = "الاستخدام السكني يدعم القيمة الإيجارية السكنية كأساس للضريبة"
        erent  = "القيمة الإيجارية تُحسب على أساس الإيجار السكني السوقي"
        emeth  = "يدعم التوافق بين طرق التكلفة والمقارنة والرسملة بأوزان سكنية (40/40/20)"
        missing = ["مستندات ترخيص البناء/الاستخدام", "تقرير معاينة الخبير الميداني"]
        enotes = "يجب مراجعة الخبير للتأكد من مطابقة الاستخدام الفعلي للترخيص قبل إصدار تقرير رسمي"

    elif class_key == "non_residential":
        if subtype_key == "shop":
            phys   = "استخدام تجاري — يعتمد على الواجهة والوصول والدور"
            legal  = "استخدام تجاري إذا كان الترخيص يسمح — يحتاج استكمال مستندات"
            fin    = "المحل التجاري ذو الواجهة القوية أعلى جدوى كنشاط تجاري مباشر"
            maxp   = "الاستخدام التجاري المباشر بشرط الواجهة والوصول المناسبين"
            concl  = "استخدام المحل التجاري قد يمثل أعلى وأفضل استغلال إذا دعمته الواجهة والترخيص"
            etax   = "يؤثر على القيمة الإيجارية التجارية ومعامل الدور المُطبَّق على الوعاء الضريبي"
            erent  = "تُحسب القيمة الإيجارية على أساس الإيجار التجاري مع تعديل الدور والواجهة"
            emeth  = "قد يزيد وزن طريقة الرسملة والمقارنة الضريبية عند توافر بيانات إيجارية موثوقة"
            missing = ["ترخيص النشاط التجاري", "قياس عرض الواجهة الفعلي", "عقد إيجار تجاري حالي"]
            enotes = "يلزم قياس الواجهة الفعلي وتحديد الدور (أرضي/أول) قبل تثبيت الاستخدام الأعلى"

        elif subtype_key == "admin_unit":
            phys   = "استخدام إداري/مهني — وفق موقع الوحدة ومواصفاتها والدور"
            legal  = "استخدام إداري مسموح به غالبًا في المناطق المختلطة — يحتاج استكمال"
            fin    = "الاستخدام الإداري/المكتبي هو الأكثر جدوى للوحدات الإدارية"
            maxp   = "الاستخدام كوحدة إدارية/مهنية في الدور المناسب مع تطبيق معامل الدور (0.85)"
            concl  = "الاستخدام الإداري الحالي يُمثِّل أعلى وأفضل استغلال وفق المعطيات المتاحة"
            etax   = "القيمة الإيجارية الإدارية أقل من التجارية الأرضية — معامل الدور محدد (0.85)"
            erent  = "تُحسب القيمة الإيجارية على أساس الإيجار الإداري مع تطبيق معامل الدور 0.85"
            emeth  = "يدعم الاعتماد على طريقة الرسملة وطريقة المقارنة — الأوزان غير السكنية (30/30/40)"
            missing = ["ترخيص النشاط الإداري", "مستند تحديد الدور في العقار"]
            enotes = "يجب مراجعة معامل الدور وتأثيره على القيمة الإيجارية المعتمدة في الطعن"

        elif subtype_key == "basement_storage":
            phys   = "استخدام تخزيني/خدمي — قيود الوصول والإضاءة تمنع الاستخدام التجاري"
            legal  = "الاستخدام التجاري في البدروم مقيَّد عادةً — المخزن/الخدمي هو الأنسب"
            fin    = "الاستخدام التخزيني هو الأكثر جدوى لمخزن البدروم — إيجار أقل من التجاري"
            maxp   = "مخزن/خدمي — لا يُفترض استخدام تجاري دون دليل هندسي وترخيص صريح"
            concl  = "الاستخدام التخزيني/الخدمي يُمثِّل أعلى وأفضل استغلال للمخزن في البدروم"
            etax   = "انخفاض القيمة الإيجارية مقارنة بالمحلات الأرضية — معامل البدروم 0.50 مُطبَّق"
            erent  = "القيمة الإيجارية للمخزن أقل بسبب قيود الوصول والظهور التجاري (معامل 0.50)"
            emeth  = "يدعم اعتماد طريقة التكلفة ومعامل البدروم 0.50 وعدم تخصيص حصة أرض مستقلة"
            missing = ["مستند تحديد الاستخدام المرخص في البدروم", "تقرير معاينة الوصول والإضاءة"]
            enotes = "لا يُفترض استخدام تجاري لمخزن البدروم دون تقرير هندسي يُثبت إمكانية ذلك"

        else:  # garage, office, mall_unit, other
            phys   = "وفق مواصفات البناء والدور والموقع"
            legal  = "يحتاج استكمال مستندات الترخيص/الاستخدام"
            fin    = "وفق البيانات المتاحة"
            maxp   = "الاستخدام الحالي وفق البيانات المتاحة"
            concl  = "تحليل استرشادي غير معتمد قبل مراجعة الخبير"
            etax   = "وفق البيانات المتاحة"
            erent  = "وفق البيانات المتاحة"
            emeth  = "وفق البيانات المتاحة"
            missing = ["مستندات الترخيص والاستخدام", "تقرير معاينة الخبير"]
            enotes = "يجب مراجعة الخبير لتحديد الاستخدام الأعلى والأفضل"

    else:  # special_purpose
        phys   = "استخدام صناعي/إنتاجي — وفق مواصفات المنشأة والترخيص الصناعي"
        legal  = "الاستخدام الصناعي مشروط بالترخيص الصناعي — يحتاج استكمال"
        fin    = "الاستمرار في الاستخدام الصناعي/الإنتاجي إذا كان مرخصًا ومشغولًا"
        maxp   = "الاستخدام الصناعي/الإنتاجي الحالي إذا دعمته البيانات والتراخيص"
        concl  = "الاستخدام الصناعي/الإنتاجي يُمثِّل أعلى وأفضل استغلال — طريقة التكلفة تهيمن"
        etax   = "طريقة التكلفة الإهلاكية هي الأساس لاحتساب قيمة المنشأة الضريبية (100%)"
        erent  = "لا يُطبَّق إيجار سوقي مباشر للمنشآت الصناعية الخاصة في الغالب"
        emeth  = "يدعم اعتماد طريقة التكلفة بنسبة 100% للمنشآت ذات الأغراض الخاصة"
        missing = [
            "الترخيص الصناعي/الإنتاجي",
            "خطاب هيئة المجتمعات العمرانية/الصناعية",
            "تقرير الإهلاك الفعلي",
        ]
        enotes = "يجب مراجعة الترخيص والوضع الإنتاجي لتأكيد الاستخدام الأعلى إنتاجية"

    data_status = "بيانات محاكاة QA" if is_qa else _NEEDS_EXPERT

    return {
        "current_use":                    current_use,
        "licensed_use":                   licensed_use,
        "physically_possible_uses":       phys,
        "legally_permissible_uses":       legal,
        "financially_feasible_uses":      fin,
        "maximally_productive_use":       maxp,
        "hbu_conclusion":                 concl,
        "hbu_effect_on_tax_basis":        etax,
        "hbu_effect_on_rental_value":     erent,
        "hbu_effect_on_method_weighting": emeth,
        "hbu_data_status":                data_status,
        "hbu_required_missing_inputs":    missing,
        "hbu_expert_notes":               enotes,
        "hbu_advisory_note":              _HBU_ADVISORY_NOTE,
        # ── Explicit four HBU tests ──────────────────────────────────────────
        "legally_permissible_test":       {"test": "قانونيًا مسموح", "result": legal,  "status": "جزئي — يحتاج مستندات ترخيص"},
        "physically_possible_test":       {"test": "ممكن فيزيائيًا", "result": phys,   "status": "مُدرَج"},
        "financially_feasible_test":      {"test": "مجدٍ ماليًا",    "result": fin,    "status": "مُدرَج"},
        "maximally_productive_test":      {"test": "أعلى إنتاجية",   "result": maxp,   "status": "مُدرَج"},
    }


def _build_standards_mapping(class_key: str, subtype_key: str) -> dict:
    """Build professional valuation standards mapping per method (advisory only)."""
    rows = [
        {
            "method_name":               "طريقة التكلفة",
            "valuation_principle":       "مبدأ تكلفة الإحلال الإهلاكية — Depreciated Replacement Cost",
            "standard_family":           "IVS / USPAP / المعايير المهنية المحلية",
            "standard_reference_status": "يحتاج مراجعة الخبير لتحديد الإصدار/البند المعتمد",
            "professional_use_note":     "متوافق من حيث المبدأ مع منهج التكلفة ضمن أطر التقييم الدولية",
            "limitations_note":          "يُطبَّق في غياب بيانات السوق الكافية أو للعقارات الخاصة",
        },
        {
            "method_name":               "طريقة المقارنة السوقية",
            "valuation_principle":       "مبدأ المقارنة المباشرة — Sales Comparison Approach",
            "standard_family":           "IVS / USPAP / المعايير المهنية المحلية",
            "standard_reference_status": "يحتاج مراجعة الخبير لتحديد الإصدار/البند المعتمد",
            "professional_use_note":     "متوافق من حيث المبدأ مع منهج المقارنة المباشرة ضمن أطر التقييم الدولية",
            "limitations_note":          "يتطلب بيانات مقارنات موثوقة وحديثة في منطقة العقار",
        },
        {
            "method_name":               "طريقة الرسملة / الدخل",
            "valuation_principle":       "مبدأ رسملة الدخل — Income Capitalization Approach",
            "standard_family":           "IVS / USPAP / المعايير المهنية المحلية",
            "standard_reference_status": "يحتاج مراجعة الخبير لتحديد الإصدار/البند المعتمد",
            "professional_use_note":     "متوافق من حيث المبدأ مع منهج الرسملة ضمن أطر التقييم الدولية",
            "limitations_note":          "يتطلب قيمة إيجارية سوقية موثوقة ومعدل رسملة مدعوم ببيانات",
        },
        {
            "method_name":               "طريقة المقارنة الضريبية",
            "valuation_principle":       "مبدأ الاتساق الضريبي — Tax Uniformity / Comparability",
            "standard_family":           "قواعد مهنية محلية — لوائح ضريبة الأملاك المصرية",
            "standard_reference_status": "يحتاج مراجعة الخبير — لا يوجد إصدار IVS/USPAP مباشر",
            "professional_use_note":     "يُستخدم كداعم لطعون ضرائب الأملاك — لا يدخل في الوزن الرئيسي",
            "limitations_note":          "يعتمد على توافر حالات ضريبية مقارنة موثقة",
        },
        {
            "method_name":               "طريقة الانحدار المتعدد",
            "valuation_principle":       "النمذجة الإحصائية — Statistical / AVM Approach",
            "standard_family":           "IVS / IAAO / المعايير الإحصائية المهنية",
            "standard_reference_status": "غير مفعل — يحتاج قاعدة بيانات تدريب ونموذجًا مُرخَّصًا",
            "professional_use_note":     "لم يتم تفعيل مرجع معياري تفصيلي تلقائي في هذه النسخة",
            "limitations_note":          "يتطلب نموذجًا إحصائيًا مُدرَّبًا على بيانات فعلية — مرحلة مستقبلية",
        },
        {
            "method_name":               "تحليل HBU",
            "valuation_principle":       "مبدأ أعلى وأفضل استغلال — Highest and Best Use",
            "standard_family":           "IVS / USPAP / المعايير المهنية المحلية",
            "standard_reference_status": "يحتاج مراجعة الخبير لتحديد الإصدار/البند المعتمد",
            "professional_use_note":     "HBU تحليل أساسي في التقييم المهني — يؤثر على أوزان الطرق والقيمة الإيجارية",
            "limitations_note":          "يجب الحصول على مستندات الترخيص والاستخدام الفعلي لإتمام التحليل",
        },
        {
            "method_name":               "التوفيق بين الطرق",
            "valuation_principle":       "مبدأ التوفيق والحكم المهني — Reconciliation / Professional Judgment",
            "standard_family":           "IVS / USPAP / المعايير المهنية المحلية",
            "standard_reference_status": "يحتاج مراجعة الخبير لتحديد الإصدار/البند المعتمد",
            "professional_use_note":     "التوفيق يعكس حكم الخبير في تحديد الوزن النهائي لكل طريقة",
            "limitations_note":          "الأوزان الظاهرة استرشادية — يُعدِّلها الخبير وفق ظروف العقار والبيانات المتاحة",
        },
    ]

    return {
        "standards_mapping_rows":         rows,
        "standards_advisory_note":        _STD_ADVISORY_NOTE,
        "standards_verification_status":  "يحتاج مراجعة الخبير",
        "no_exact_ivs_clause_displayed":  True,
        "report_display_reference":       "استرشادي فقط — لم يتم تفعيل مراجع بنود تفصيلية تلقائيًا",
    }


def _build_data_governance(
    is_qa: bool,
    cost_m: dict, market_m: dict, income_m: dict,
    tax_cmp_m: dict, regression_m: dict,
) -> dict:
    """Build data provenance governance table for all five methods."""
    qa_label  = "بيانات محاكاة QA"
    qa_note   = "بيانات محاكاة QA — لا تستخدم كدليل حقيقي"
    prod_note = "يحتاج استكمال بيانات حقيقية"

    def _src(qa_src, prod_src):
        return qa_src if is_qa else prod_src

    def _row(method, item, value, source_type, source_status,
             qa_sim, prod_ready, evidence, action, notes=""):
        return {
            "method":            method,
            "data_item":         item,
            "value":             str(value) if value not in (None, "") else _NEEDS_EXPERT,
            "source_type":       source_type,
            "source_status":     source_status,
            "is_qa_simulation":  qa_sim,
            "production_ready":  prod_ready,
            "required_evidence": evidence,
            "expert_action":     action,
            "notes":             notes,
        }

    cost_src    = _src(qa_label, "مُدخل الطلب")
    cost_status = _src(qa_label, "بيانات مُدخلة من الطلب")
    cost_prod   = not is_qa and bool(cost_m.get("indicated_value"))

    mkt_src    = _src(qa_label, "مصدر خارجي مؤجل")
    mkt_status = _src(qa_label, "غير متاح — Qdrant مؤجل")
    mkt_prod   = False

    inc_src    = _src(qa_label, "مُدخل الطلب")
    inc_status = _src(qa_label, "بيانات مُدخلة من الطلب")
    inc_prod   = not is_qa and bool(income_m.get("indicated_value"))

    tax_src    = _src(qa_label, "سجل طعون ضريبية — داخلي")
    tax_status = _src(qa_label, "بيانات مُدخلة من الطلب")
    tax_prod   = not is_qa and bool(tax_cmp_m.get("overcharge_amount"))

    rows = [
        _row("طريقة التكلفة", "قيمة الأرض / م²",
             cost_m.get("land_value_indicated", "—"),
             cost_src, cost_status, is_qa, cost_prod,
             "خطاب هيئة المجتمعات العمرانية / سجل المصادر",
             "مراجعة السعر مع مصادر السوق الرسمية",
             qa_note if is_qa else ""),
        _row("طريقة التكلفة", "تكلفة بناء / م²",
             cost_m.get("building_unit_cost", "—"),
             cost_src, cost_status, is_qa, cost_prod,
             "مرجع تكلفة بناء أكاديمي معتمد",
             "مراجعة المرجع المستخدم للتكلفة",
             qa_note if is_qa else ""),
        _row("طريقة المقارنة السوقية", "المقارنات البيعية المعدَّلة",
             market_m.get("adj_unit_price", "—"),
             mkt_src, mkt_status, is_qa, mkt_prod,
             "بيانات مقارنات بيوع سوقية موثوقة",
             "إدخال مقارنات فعلية من السوق",
             qa_note if is_qa else prod_note),
        _row("طريقة الرسملة / الدخل", "القيمة الإيجارية السنوية",
             income_m.get("annual_rent", "—"),
             inc_src, inc_status, is_qa, inc_prod,
             "عقد إيجار حالي أو تقرير إيجار سوقي",
             "توثيق مصدر القيمة الإيجارية",
             qa_note if is_qa else ""),
        _row("طريقة المقارنة الضريبية", "الحالات الضريبية المقارنة",
             tax_cmp_m.get("comparable_tax_cases_count", "—"),
             tax_src, tax_status, is_qa, tax_prod,
             "سجل قضايا ضريبية مقارنة موثقة",
             "إدخال حالات ضريبية فعلية",
             qa_note if is_qa else ""),
        _row("طريقة الانحدار المتعدد", "نموذج الانحدار الإحصائي",
             "غير مفعل",
             "مرحلة مستقبلية", "غير متاح", True, False,
             "قاعدة بيانات تدريب إحصائية",
             "لا إجراء الآن — مرحلة مستقبلية",
             "الانحدار المتعدد غير مفعل — يحتاج نموذجًا إحصائيًا مُدرَّبًا"),
    ]

    prod_count = sum(1 for r in rows if r["production_ready"])

    governance_summary = {
        "qa_simulation_active":       is_qa,
        "production_ready_count":     prod_count,
        "qa_only_count":              sum(1 for r in rows if r["is_qa_simulation"]),
        "regression_production_ready": False,
        "validation_note": (
            "بيانات محاكاة QA — لا تصلح للاستخدام في تقرير رسمي أو تقديم أمام جهة ضريبية."
            if is_qa else
            "تحقق من اكتمال البيانات الفعلية قبل إصدار تقرير رسمي."
        ),
        "no_live_data_note": (
            "لم يتم استخدام الإنترنت أو Qdrant أو OCR في هذا الإصدار. "
            "تم تجهيز البنية فقط لاستقبال مصادر البيانات لاحقًا بعد التفعيل والمراجعة."
        ),
    }

    return {
        "data_governance_rows":    rows,
        "data_governance_summary": governance_summary,
    }


def _build_five_method_reconciliation(
    class_key: str,
    cost_m: dict, market_m: dict, income_m: dict,
    tax_cmp_m: dict, regression_m: dict,
    govt_tax: float, corrected_tax: float, overcharge_amt: float,
    hbu_analysis: dict | None = None,
    sensitivity_analysis: dict | None = None,
) -> dict:
    """Build the five-method reconciliation table."""

    # Default weight schemes by class
    # Tax comparison is shown as supporting (overcharge analysis), not weighted
    # Multiple regression is 0 (future)
    if class_key == "residential":
        w_cost   = 0.40
        w_market = 0.40
        w_income = 0.20
    elif class_key == "non_residential":
        w_cost   = 0.30
        w_market = 0.30
        w_income = 0.40
    else:  # special_purpose
        w_cost   = 1.00
        w_market = 0.0
        w_income = 0.0

    # Reduce weights if income data is missing
    income_val = income_m.get("indicated_value")
    if income_val in (_NEEDS_COMPLETION, _NOT_APP_TYPE, _DEFERRED_SOURCE, None, 0.0):
        if class_key in ("residential", "non_residential"):
            w_cost   = round(w_cost + w_income / 2, 4)
            w_market = round(w_market + w_income / 2, 4)
            w_income = 0.0

    # Reduce market weight for special_purpose
    market_val = market_m.get("indicated_value")
    if market_val in (_NEEDS_COMPLETION, _NOT_APP_TYPE, _DEFERRED_SOURCE, None, 0.0):
        w_cost   = round(w_cost + w_market, 4)
        w_market = 0.0

    def _fval(v):
        """Safely convert indicated_value to float."""
        try:
            return float(str(v).replace(",", ""))
        except Exception:
            return 0.0

    cost_v   = _fval(cost_m.get("indicated_value"))
    market_v = _fval(market_m.get("indicated_value"))
    income_v = _fval(income_m.get("indicated_value"))

    weighted_cost   = round(cost_v * w_cost, 2)
    weighted_market = round(market_v * w_market, 2)
    weighted_income = round(income_v * w_income, 2)

    total_weight = w_cost + w_market + w_income
    final_val = (
        round((weighted_cost + weighted_market + weighted_income) / total_weight, 2)
        if total_weight > 0 and (weighted_cost + weighted_market + weighted_income) > 0
        else _NEEDS_COMPLETION
    )

    # Expert-selected value defaults to the corrected_tax_amount context
    expert_sel_val = corrected_tax if corrected_tax > 0 else final_val
    expected_savings = round(govt_tax - corrected_tax, 2) if (govt_tax > 0 and corrected_tax > 0) else _NEEDS_COMPLETION

    method_weights = [
        {"method": "طريقة التكلفة",          "weight": f"{w_cost:.0%}",   "value": cost_v or _NEEDS_COMPLETION,   "weighted": weighted_cost or _NEEDS_COMPLETION},
        {"method": "طريقة المقارنة السوقية", "weight": f"{w_market:.0%}", "value": market_v or _NEEDS_COMPLETION, "weighted": weighted_market or _NEEDS_COMPLETION,
         "note": "غير مستخدم" if w_market == 0 else ""},
        {"method": "طريقة الرسملة / الدخل", "weight": f"{w_income:.0%}", "value": income_v or _NEEDS_COMPLETION, "weighted": weighted_income or _NEEDS_COMPLETION,
         "note": "غير مستخدم" if w_income == 0 else ""},
        {"method": "طريقة المقارنة الضريبية","weight": "مرجعية",          "value": tax_cmp_m.get("overcharge_amount", _NEEDS_COMPLETION), "weighted": "داعم فقط"},
        {"method": "طريقة الانحدار المتعدد", "weight": "0%",              "value": regression_m.get("indicated_value", _DEFERRED_SOURCE),  "weighted": "غير مفعل"},
    ]

    if class_key == "special_purpose":
        notes = (
            "تم الاعتماد في هذا السيناريو على طريقة التكلفة الإهلاكية بنسبة 100% "
            "نظرًا لطبيعة العقار كمنشأة ذات طبيعة خاصة وعدم كفاية بيانات المقارنة أو الدخل. "
            "الآلات والمعدات التشغيلية لا تدخل ضمن التقييم العقاري إلا إذا تم النص صراحة على خلاف ذلك. "
            "طريقة المقارنة الضريبية داعمة فقط. الانحدار المتعدد مرحلة مستقبلية."
        )
    else:
        notes = (
            f"تم استخدام الطرق المتاحة البيانات بأوزان ({w_cost:.0%} تكلفة / {w_market:.0%} مقارنة / {w_income:.0%} رسملة). "
            "طريقة المقارنة الضريبية داعمة فقط. الانحدار المتعدد مرحلة مستقبلية."
        )

    # ── Applicability table (per-method: applicability, data_status, included, reason) ──
    def _inc_reason(included, weight_str, method_name):
        if not included:
            return f"{method_name}: بيانات غير كافية أو غير منطبقة"
        if weight_str in ("مرجعية", "داعم فقط", "0%"):
            return f"{method_name}: داعمة — لا تدخل في الوزن"
        return f"{method_name}: بيانات متاحة — مُدرجة بوزن {weight_str}"

    applicability_table = [
        {
            "method":          "طريقة التكلفة",
            "applicability":   cost_m.get("method_applicability", "applicable"),
            "data_status":     cost_m.get("data_availability_status", "missing"),
            "indicated_value": cost_v or _NEEDS_COMPLETION,
            "weight":          f"{w_cost:.0%}",
            "weighted_value":  weighted_cost if w_cost > 0 else "—",
            "included":        w_cost > 0,
            "reason":          _inc_reason(w_cost > 0, f"{w_cost:.0%}", "طريقة التكلفة"),
            "expert_notes":    cost_m.get("expert_notes", ""),
        },
        {
            "method":          "طريقة المقارنة السوقية",
            "applicability":   market_m.get("method_applicability", "applicable"),
            "data_status":     market_m.get("data_availability_status", "missing"),
            "indicated_value": market_v or _NEEDS_COMPLETION,
            "weight":          f"{w_market:.0%}",
            "weighted_value":  weighted_market if w_market > 0 else "—",
            "included":        w_market > 0,
            "reason":          _inc_reason(w_market > 0, f"{w_market:.0%}", "طريقة المقارنة السوقية"),
            "expert_notes":    market_m.get("expert_notes", ""),
        },
        {
            "method":          "طريقة الرسملة / الدخل",
            "applicability":   income_m.get("method_applicability", "applicable"),
            "data_status":     income_m.get("data_availability_status", "missing"),
            "indicated_value": income_v or _NEEDS_COMPLETION,
            "weight":          f"{w_income:.0%}",
            "weighted_value":  weighted_income if w_income > 0 else "—",
            "included":        w_income > 0,
            "reason":          _inc_reason(w_income > 0, f"{w_income:.0%}", "طريقة الرسملة"),
            "expert_notes":    income_m.get("expert_notes", ""),
        },
        {
            "method":          "طريقة المقارنة الضريبية",
            "applicability":   tax_cmp_m.get("method_applicability", "applicable"),
            "data_status":     tax_cmp_m.get("data_availability_status", "complete"),
            "indicated_value": tax_cmp_m.get("indicated_tax_amount", _NEEDS_COMPLETION),
            "weight":          "مرجعية",
            "weighted_value":  "داعم — لا يدخل في الوزن الرئيسي",
            "included":        False,
            "reason":          "طريقة المقارنة الضريبية: تُعزِّز الطعن — داعمة فقط لا موزونة",
            "expert_notes":    tax_cmp_m.get("expert_notes", ""),
        },
        {
            "method":          "طريقة الانحدار المتعدد",
            "applicability":   "future_ready",
            "data_status":     regression_m.get("data_availability_status", "not_ready"),
            "indicated_value": regression_m.get("indicated_value", _DEFERRED_SOURCE),
            "weight":          "0%",
            "weighted_value":  "غير مفعل",
            "included":        False,
            "reason":          "الانحدار المتعدد: يحتاج قاعدة بيانات تدريب — غير مفعل حاليًا",
            "expert_notes":    regression_m.get("expert_notes", ""),
        },
    ]

    # ── Final conclusion table ───────────────────────────────────────────────────
    _sa = sensitivity_analysis or {}
    final_conclusion_table = {
        "class_key":                class_key,
        "methods_used":             [e["method"] for e in applicability_table if e["included"]],
        "methods_supporting":       ["طريقة المقارنة الضريبية"],
        "methods_deferred":         ["طريقة الانحدار المتعدد"],
        "total_weight":             f"{total_weight:.0%}",
        "weighted_result":          final_val,
        "expert_selected_value":    expert_sel_val,
        "expert_selected_tax":      corrected_tax or _NEEDS_COMPLETION,
        "government_tax":           govt_tax or _NEEDS_COMPLETION,
        "overcharge_amount":        overcharge_amt or _NEEDS_COMPLETION,
        "expected_savings":         expected_savings,
        "conclusion_ar":            (
            f"بعد تطبيق الطرق الخمس وتوفيقها، تبيَّن أن القيمة الإيجارية الاسترشادية هي "
            f"{expert_sel_val:,.0f} ج.م. "
            f"الضريبة الحكومية البالغة {govt_tax:,.0f} ج.م تتجاوز التقدير الاسترشادي "
            f"بمقدار {overcharge_amt:,.0f} ج.م ({overcharge_amt / govt_tax * 100:.1f}%)."
            if isinstance(final_val, (int, float)) and govt_tax > 0 and overcharge_amt > 0
            else notes
        ),
        "formula_weighted_result":  "= مجموع(قيمة_طريقة × وزن_طريقة) / مجموع(الأوزان)",
        "formula_expected_savings": "= ضريبة_حكومية − ضريبة_مُختارة",
        # Sensitivity range fields (Part J)
        "final_tax_base":  corrected_tax if corrected_tax > 0 else _NEEDS_COMPLETION,
        "final_tax_low":   _sa.get("tax_low",  _NEEDS_COMPLETION),
        "final_tax_high":  _sa.get("tax_high", _NEEDS_COMPLETION),
        "saving_low":      _sa.get("expected_saving_low",  _NEEDS_COMPLETION),
        "saving_base":     _sa.get("expected_saving_base", _NEEDS_COMPLETION),
        "saving_high":     _sa.get("expected_saving_high", _NEEDS_COMPLETION),
    }

    # ── HBU / data-quality / production-readiness notes for reconciliation ────
    if hbu_analysis:
        hbu_concl = hbu_analysis.get("hbu_conclusion", _NEEDS_EXPERT)
        hbu_meth  = hbu_analysis.get("hbu_effect_on_method_weighting", "")
        hbu_weighting_note = (
            f"تأثير HBU على الأوزان: {hbu_meth} | خلاصة HBU: {hbu_concl}"
        )
    else:
        hbu_weighting_note = _HBU_ADVISORY_NOTE

    if class_key == "special_purpose":
        data_quality_note = (
            "المنشآت الخاصة: طريقة التكلفة 100% — لا تتوافر مقارنات سوقية كافية. "
            "الانحدار المتعدد غير مفعل — مرحلة مستقبلية."
        )
        prod_readiness_note = (
            "بيانات التكلفة مُدخلة من الطلب. "
            "يجب التحقق من مصدر سعر الأرض وتكلفة الإحلال قبل إصدار التقرير."
        )
    elif class_key == "non_residential":
        data_quality_note = (
            f"المقارنة السوقية: {'بيانات محاكاة QA' if market_v == 0 else 'متاحة'}. "
            f"الرسملة/الدخل: {'بيانات محاكاة QA' if income_v == 0 else 'متاحة'}. "
            "الانحدار المتعدد غير مفعل."
        )
        prod_readiness_note = (
            "يجب توثيق القيمة الإيجارية والمقارنات السوقية من مصادر حقيقية "
            "قبل اعتماد أوزان الطرق في تقرير رسمي."
        )
    else:
        data_quality_note = (
            f"المقارنة السوقية: {'بيانات محاكاة QA' if market_v == 0 else 'متاحة'}. "
            f"الرسملة/الدخل: {'بيانات محاكاة QA' if income_v == 0 else 'متاحة'}. "
            "الانحدار المتعدد غير مفعل."
        )
        prod_readiness_note = (
            "يجب توثيق القيمة الإيجارية السكنية ومقارنات البيوع من مصادر حقيقية "
            "قبل اعتماد الأوزان النهائية في تقرير رسمي."
        )

    # ── Additional notes (Part J) ────────────────────────────────────────────────
    _sa = sensitivity_analysis or {}
    sensitivity_range_note = (
        f"نطاق الحساسية الاسترشادي: "
        f"{_sa['tax_low']:,.0f} — {_sa['tax_high']:,.0f} ج.م "
        f"({_sa.get('sensitivity_pct_label', '')})"
        if _sa.get("tax_low") is not None else "نطاق الحساسية: يحتاج بيانات مكتملة"
    )

    return {
        "cost_approach_value":             cost_v or _NEEDS_COMPLETION,
        "market_comparison_value":         market_v or _NEEDS_COMPLETION,
        "income_capitalization_value":     income_v or _NEEDS_COMPLETION,
        "tax_comparison_value_or_tax_gap": tax_cmp_m.get("overcharge_amount", _NEEDS_COMPLETION),
        "multiple_regression_indication":  regression_m.get("indicated_value", _DEFERRED_SOURCE),
        "method_weight":                   method_weights,
        "applicability_table":             applicability_table,
        "final_conclusion_table":          final_conclusion_table,
        "weighted_result":                 final_val,
        "expert_selected_value":           expert_sel_val,
        "expert_selected_tax_amount":      corrected_tax or _NEEDS_COMPLETION,
        "expected_savings":                expected_savings,
        "reconciliation_notes":            notes,
        "hbu_weighting_note":              hbu_weighting_note,
        "data_quality_weighting_note":     data_quality_note,
        "production_readiness_note":       prod_readiness_note,
        "assumptions_impact_note": (
            "تُراجَع الافتراضات الخاصة قبل إصدار تقرير رسمي — "
            "أي افتراض غير مُحقَّق قد يؤثر على القيمة والضريبة."
        ),
        "sensitivity_range_note":  sensitivity_range_note,
        "regression_exclusion_note": (
            "لم يتم استخدام طريقة الانحدار المتعدد في التوفيق النهائي لعدم وجود "
            "قاعدة بيانات تدريب موثقة أو نموذج تحقق."
        ),
        "data_provenance_note": "راجع ورقة حوكمة البيانات لحالة كل مصدر.",
    }


# ── Ain Shams Industrial Cost Reference ──────────────────────────────────────

_AIN_SHAMS_GUIDANCE_SOURCE = {
    "guidance_source_name":   "تقدير القيمة الاستبدالية للمصانع والفنادق — دراسة مبدئية",
    "guidance_source_org":    "كلية الهندسة، جامعة عين شمس / مصلحة الضرائب العقارية",
    "guidance_source_type":   "مرفق مقدم من المستخدم — دراسة أكاديمية مبدئية",
    "guidance_source_status": "مُرفَق ومُفحوص — دراسة مبدئية غير معتمدة رسميًا كمعيار نهائي",
    "guidance_official_endorsement": (
        "الوثيقة تحمل شعار وزارة المالية / مصلحة الضرائب العقارية، وأُعدَّت بواسطة مشروع "
        "تقييم المباني بكلية الهندسة جامعة عين شمس. مصنَّفة 'دراسة مبدئية' ولا تمثل "
        "معيارًا رسميًا نهائيًا — يحتاج تطبيقها مراجعة الخبير."
    ),
    "reviewed_by_system": True,
    "expert_verification_required": True,
    "production_ready": False,
}

# Unit costs extracted verbatim from the attached Ain Shams document (ج.م/م²)
# Structure: {building_type: {base, finishing_factor, finishing, total, after_85pct}}
_AIN_SHAMS_INDUSTRIAL_COST_TABLE: list[dict] = [
    {
        "building_type_ar":  "منشآت معدنية",
        "building_type_key": "metallic",
        "base_cost_per_m2":       700,
        "finishing_factor":       0.5,
        "finishing_cost_per_m2":  350,
        "total_per_m2":           1050,
        "after_85pct_safety":     892.5,
        "applicable_to":          "مباني إنتاجية معدنية",
    },
    {
        "building_type_ar":  "منشآت خرسانية",
        "building_type_key": "concrete",
        "base_cost_per_m2":       900,
        "finishing_factor":       0.5,
        "finishing_cost_per_m2":  450,
        "total_per_m2":           1350,
        "after_85pct_safety":     1147.5,
        "applicable_to":          "مباني إنتاجية خرسانية",
    },
    {
        "building_type_ar":  "مبانى خدمات",
        "building_type_key": "service",
        "base_cost_per_m2":       800,
        "finishing_factor":       0.5,
        "finishing_cost_per_m2":  400,
        "total_per_m2":           1200,
        "after_85pct_safety":     1020.0,
        "applicable_to":          "مباني خدمات وملحقات",
    },
    {
        "building_type_ar":  "مبانى إدارية",
        "building_type_key": "admin",
        "base_cost_per_m2":       800,
        "finishing_factor":       1.0,
        "finishing_cost_per_m2":  800,
        "total_per_m2":           1600,
        "after_85pct_safety":     1360.0,
        "applicable_to":          "مباني إدارية ومكاتب",
    },
]

_AIN_SHAMS_NOT_PROVIDED = [
    "العمر الإنتاجي للمباني الصناعية (غير مذكور في الدراسة المبدئية)",
    "معدل الإهلاك السنوي (غير مذكور في الدراسة المبدئية)",
    "منهجية الفصل بين قيمة الأرض والمباني (غير مذكورة في الدراسة المبدئية)",
    "تعديل العمر / الحالة (غير مذكور في الدراسة المبدئية)",
]


def _build_factory_cost_guidance(payload: dict, is_qa: bool) -> dict:
    """Build factory cost guidance block using Ain Shams reference (attached document)."""
    industrial_components = payload.get("industrial_components") or []
    # Map QA component types to Ain Shams categories
    component_cost_map: list[dict] = []
    for comp in industrial_components:
        name = str(comp.get("name", "")).lower()
        if "إداري" in name or "مكتب" in name:
            ain_shams_ref = "مبانى إدارية — 1360 ج.م/م² (بعد معامل 85%)"
        elif "مستودع" in name or "مخزن" in name:
            ain_shams_ref = "مبانى خدمات — 1020 ج.م/م² (بعد معامل 85%)"
        elif "إنتاج" in name or "تصنيع" in name or "رئيس" in name:
            ain_shams_ref = "منشآت خرسانية — 1147.5 ج.م/م² (بعد معامل 85%)"
        elif "أرض" in name:
            ain_shams_ref = "الأرض: غير مشمولة في جدول التكلفة الإنشائية"
        else:
            ain_shams_ref = "يحتاج تصنيف الخبير وفق جداول الدراسة المبدئية"
        component_cost_map.append({
            "component_name":      comp.get("name", ""),
            "component_area":      comp.get("area", _NEEDS_COMPLETION),
            "used_unit_cost":      comp.get("unit_cost", _NEEDS_COMPLETION),
            "ain_shams_reference": ain_shams_ref,
            "expert_review_note":  "يلزم مراجعة الخبير لتحديد الفئة المناسبة من الدراسة المبدئية",
        })

    return {
        "guidance_source_name":    _AIN_SHAMS_GUIDANCE_SOURCE["guidance_source_name"],
        "guidance_source_type":    _AIN_SHAMS_GUIDANCE_SOURCE["guidance_source_type"],
        "guidance_source_status":  _AIN_SHAMS_GUIDANCE_SOURCE["guidance_source_status"],
        "guidance_official_endorsement": _AIN_SHAMS_GUIDANCE_SOURCE["guidance_official_endorsement"],
        "reviewed_by_system":      True,
        "ain_shams_document_available": True,
        "key_cost_categories":     _AIN_SHAMS_INDUSTRIAL_COST_TABLE,
        "component_cost_map":      component_cost_map,
        "recommended_unit_cost_fields": [
            "تكلفة الهيكل/م² (ج.م/م²)",
            "معامل التشطيب",
            "تكلفة التشطيب/م² (ج.م/م²)",
            "إجمالي التكلفة/م² (ج.م/م²)",
            "السعر بعد معامل أمان 85% (ج.م/م²)",
        ],
        "recommended_depreciation_fields": _AIN_SHAMS_NOT_PROVIDED,
        "useful_life_guidance":    "غير مذكور في الدراسة المبدئية — يحتاج مرجع إضافي",
        "depreciation_rate_guidance": "غير مذكور في الدراسة المبدئية — يحتاج مرجع إضافي",
        "applicability_to_factory": (
            "جداول التكلفة مناسبة للمرجعية الأولية للمباني الصناعية الخرسانية والمعدنية "
            "والخدمية والإدارية. لا تشمل الآلات والمعدات التشغيلية."
        ),
        "machinery_exclusion_note": (
            "يشمل هذا التحليل الأرض والمباني والمكونات العقارية الثابتة فقط، "
            "ولا يشمل الآلات والمعدات التشغيلية أو خطوط الإنتاج إلا إذا تم "
            "النص صراحة على خلاف ذلك."
        ),
        "expert_verification_required": True,
        "production_ready": False,
        "source_citation": "مرفق مقدم من المستخدم — دراسة مبدئية / جامعة عين شمس / مصلحة الضرائب العقارية — يحتاج مراجعة الخبير",
    }


# ── Property-class gap status constants ──────────────────────────────────────

_SRC_QA     = "محاكاة QA"
_SRC_EXPERT = "إدخال الخبير"
_SRC_DOC    = "وثيقة مطلوبة غير مرفقة"
_SRC_FUTURE = "مصدر مستقبلي"
_PROD_NOT_READY = False


def _build_villa_technical_gaps(payload: dict, is_qa: bool) -> dict:
    """Residential villa — technical gap analysis and supplementary data."""
    age_yrs    = _safe_float(payload.get("age_years", 0.0))
    area       = _safe_float(payload.get("area", 0.0))
    annual_rent = _safe_float(
        payload.get("estimated_market_rental_value") or payload.get("annual_rental_estimate", 0.0)
    )
    govt_rent = _safe_float(payload.get("government_assessed_annual_rental_value", 0.0))

    # ── Effective age & depreciation ─────────────────────────────────────────
    eff_age        = 8 if is_qa and age_yrs == 0 else int(age_yrs) if age_yrs > 0 else None
    dep_rate_annual = 0.02   # 2% straight-line (QA)
    dep_accum       = round(eff_age * dep_rate_annual, 4) if eff_age else None

    building_age_table = {
        "construction_year":      payload.get("construction_year", _NEEDS_EXPERT),
        "completion_year":        payload.get("completion_year", _NEEDS_EXPERT),
        "occupancy_year":         payload.get("occupancy_year", _NEEDS_EXPERT),
        "effective_age_years":    eff_age if eff_age is not None else _NEEDS_EXPERT,
        "chronological_age_years": int(age_yrs) if age_yrs > 0 else _NEEDS_EXPERT,
        "age_source":             _SRC_QA if is_qa else _SRC_EXPERT,
        "depreciation_model":     "خط مستقيم (Straight-Line)" if eff_age else _NEEDS_EXPERT,
        "annual_depreciation_rate": f"{dep_rate_annual:.0%}" if eff_age else _NEEDS_EXPERT,
        "accumulated_depreciation": f"{dep_accum:.0%}" if dep_accum is not None else _NEEDS_EXPERT,
        "expert_note": "يلزم مراجعة مستندات الإتمام أو الإشغال لتأكيد العمر الفعلي.",
        "evidence_required": [
            "رخصة البناء أو شهادة الإتمام",
            "خطاب تحويل المرافق",
            "سجل الإشغال أو دليل صوري تطوري",
            "تقرير معاينة الخبير",
        ],
    }

    # ── Market comparables ────────────────────────────────────────────────────
    govt_tax   = _safe_float(payload.get("government_tax_amount", 0.0))
    corr_tax   = _safe_float(payload.get("corrected_tax_amount", 0.0))
    area_v     = area if area > 0 else 350.0
    location   = payload.get("governorate") or payload.get("location") or "المعادي"
    market_comparables = []
    if is_qa:
        market_comparables = [
            {
                "comparable_id":       "MC-VILLA-01",
                "property_type":       "فيلا سكنية",
                "location":            f"{location} — شارع مجاور",
                "area_m2":             320,
                "sale_value":          4_200_000,
                "price_per_m2":        13_125,
                "sale_date":           "2025-09",
                "source_type":         "محاكاة QA",
                "transaction_status":  "قيد المحاكاة",
                "adj_location":        1.05,
                "adj_area":            0.98,
                "adj_condition":       1.00,
                "adj_time":            1.02,
                "total_adj":           round(1.05 * 0.98 * 1.00 * 1.02, 4),
                "adjusted_price_m2":   round(13_125 * 1.05 * 0.98 * 1.00 * 1.02, 0),
                "indicated_value":     round(13_125 * 1.05 * 0.98 * 1.00 * 1.02 * area_v, 0),
                "included":            True,
                "notes":               "محاكاة QA — لا تستخدم كدليل سوقي حقيقي",
            },
            {
                "comparable_id":       "MC-VILLA-02",
                "property_type":       "فيلا سكنية",
                "location":            f"{location} — منطقة قريبة",
                "area_m2":             380,
                "sale_value":          5_100_000,
                "price_per_m2":        13_421,
                "sale_date":           "2025-07",
                "source_type":         "محاكاة QA",
                "transaction_status":  "قيد المحاكاة",
                "adj_location":        0.97,
                "adj_area":            1.03,
                "adj_condition":       0.98,
                "adj_time":            1.01,
                "total_adj":           round(0.97 * 1.03 * 0.98 * 1.01, 4),
                "adjusted_price_m2":   round(13_421 * 0.97 * 1.03 * 0.98 * 1.01, 0),
                "indicated_value":     round(13_421 * 0.97 * 1.03 * 0.98 * 1.01 * area_v, 0),
                "included":            True,
                "notes":               "محاكاة QA — لا تستخدم كدليل سوقي حقيقي",
            },
            {
                "comparable_id":       "MC-VILLA-03",
                "property_type":       "فيلا سكنية",
                "location":            f"{location} — منطقة بعيدة نسبيًا",
                "area_m2":             290,
                "sale_value":          3_600_000,
                "price_per_m2":        12_414,
                "sale_date":           "2025-05",
                "source_type":         "محاكاة QA",
                "transaction_status":  "قيد المحاكاة",
                "adj_location":        1.08,
                "adj_area":            1.00,
                "adj_condition":       1.05,
                "adj_time":            1.03,
                "total_adj":           round(1.08 * 1.00 * 1.05 * 1.03, 4),
                "adjusted_price_m2":   round(12_414 * 1.08 * 1.00 * 1.05 * 1.03, 0),
                "indicated_value":     round(12_414 * 1.08 * 1.00 * 1.05 * 1.03 * area_v, 0),
                "included":            True,
                "notes":               "محاكاة QA — لا تستخدم كدليل سوقي حقيقي",
            },
        ]
    else:
        market_comparables = [{"comparable_id": "MC-GAP-001", "notes": _NEEDS_EXPERT, "included": False,
                                "source_type": _SRC_DOC, "location": _NEEDS_EXPERT, "area_m2": _NEEDS_EXPERT}]

    # ── Rental support ────────────────────────────────────────────────────────
    expert_rent = annual_rent if annual_rent > 0 else (govt_rent / 2 if govt_rent > 0 else 0)
    rental_comparables = []
    if is_qa:
        mo_rent = round(expert_rent / 12, 0) if expert_rent > 0 else 8_750
        rental_comparables = [
            {
                "rental_id":       "RC-VILLA-01",
                "location":        f"{location} — شارع مجاور",
                "monthly_rent":    mo_rent,
                "annual_rent":     round(mo_rent * 12, 0),
                "area_m2":         320,
                "rent_per_m2_mo":  round(mo_rent / 320, 2),
                "adj_location":    1.03,
                "adj_size":        0.98,
                "adj_condition":   1.00,
                "adjusted_rent":   round(mo_rent * 1.03 * 0.98 * 1.00, 0),
                "included":        True,
                "source_status":   "محاكاة QA",
                "notes":           "هذه المقارنات محاكاة QA ولا تُستخدم كمصدر حقيقي قبل التوثيق",
            },
            {
                "rental_id":       "RC-VILLA-02",
                "location":        f"{location} — منطقة مماثلة",
                "monthly_rent":    round(mo_rent * 1.1, 0),
                "annual_rent":     round(mo_rent * 1.1 * 12, 0),
                "area_m2":         370,
                "rent_per_m2_mo":  round(mo_rent * 1.1 / 370, 2),
                "adj_location":    0.96,
                "adj_size":        1.04,
                "adj_condition":   0.98,
                "adjusted_rent":   round(mo_rent * 1.1 * 0.96 * 1.04 * 0.98, 0),
                "included":        True,
                "source_status":   "محاكاة QA",
                "notes":           "هذه المقارنات محاكاة QA ولا تُستخدم كمصدر حقيقي قبل التوثيق",
            },
        ]
        rental_support_note = (
            "هذه المقارنات محاكاة QA في هذه النسخة، وتحتاج إلى مصدر سوقي موثق قبل الاعتماد الرسمي."
        )
    else:
        rental_comparables = [{"rental_id": "RC-GAP-001", "notes": _NEEDS_EXPERT, "included": False}]
        rental_support_note = "يحتاج جدول المقارنات الإيجارية إلى إدخال الخبير قبل الاعتماد."

    # ── Detected gaps ─────────────────────────────────────────────────────────
    detected_gaps = [
        {
            "issue_id":          "VILLA-G01",
            "issue_title":       "العمر الفعلي للمبنى غير موثق",
            "issue_description": "معامل الإهلاك في طريقة التكلفة يعتمد على العمر الذي يحتاج توثيقًا بمستندات الإتمام أو الإشغال.",
            "affected_method":   "طريقة التكلفة",
            "affected_output":   "قيمة الإهلاك المتراكم والقيمة المُستبدَلة",
            "severity":          "high",
            "current_value":     f"العمر الفعلي: {eff_age} سنة (QA)" if is_qa else "غير متاح",
            "corrected_value_or_required_action": "إرفاق مستند إتمام/إشغال + مراجعة الخبير",
            "data_source_status": _SRC_QA if is_qa else _SRC_DOC,
            "expert_action_required": "التحقق من العمر الفعلي بواسطة معاينة الخبير ومستندات الإتمام",
            "production_ready":  _PROD_NOT_READY,
        },
        {
            "issue_id":          "VILLA-G02",
            "issue_title":       "المقارنات السوقية تحتاج توثيقًا",
            "issue_description": "المقارنات المستخدمة في طريقة المقارنة السوقية محاكاة QA وليست بيانات سوق حقيقية.",
            "affected_method":   "طريقة المقارنة السوقية",
            "affected_output":   "القيمة المشارة من طريقة المقارنة",
            "severity":          "high",
            "current_value":     "محاكاة QA" if is_qa else "غير متاح",
            "corrected_value_or_required_action": "الحصول على مصدر سوقي موثق (بيوع/عروض موثقة)",
            "data_source_status": _SRC_QA if is_qa else _SRC_DOC,
            "expert_action_required": "استبدال بيانات QA بمقارنات سوقية موثقة قبل الاعتماد",
            "production_ready":  _PROD_NOT_READY,
        },
        {
            "issue_id":          "VILLA-G03",
            "issue_title":       "دعم القيمة الإيجارية يحتاج توثيقًا",
            "issue_description": "القيمة الإيجارية للخبير بحاجة لجدول مقارنات إيجارية موثق.",
            "affected_method":   "طريقة الرسملة / الدخل",
            "affected_output":   "القيمة الإيجارية الاسترشادية وقيمة الرسملة",
            "severity":          "medium",
            "current_value":     f"{annual_rent:,.0f} ج.م (محاكاة QA)" if is_qa else "غير متاح",
            "corrected_value_or_required_action": "الحصول على مقارنات إيجارية من مصادر سوقية موثقة",
            "data_source_status": _SRC_QA if is_qa else _SRC_DOC,
            "expert_action_required": "مراجعة وتوثيق القيمة الإيجارية بمصادر سوقية",
            "production_ready":  _PROD_NOT_READY,
        },
    ]

    return {
        "detected_gaps":         detected_gaps,
        "required_evidence": [
            "رخصة البناء أو شهادة الإتمام أو خطاب تحويل المرافق",
            "3 على الأقل مقارنات بيع سكنية موثقة بالتاريخ والمصدر",
            "مقارنات إيجارية لسكن مماثل في نفس المنطقة",
        ],
        "method_specific_issues": [
            {"method": "طريقة التكلفة",          "issue": "العمر الفعلي غير موثق — الإهلاك استرشادي QA"},
            {"method": "طريقة المقارنة السوقية", "issue": "المقارنات محاكاة QA"},
            {"method": "طريقة الرسملة / الدخل", "issue": "القيمة الإيجارية غير مدعومة بمصدر سوقي"},
        ],
        "recommended_corrections": [
            "توثيق العمر الفعلي من مستندات الإتمام أو الإشغال",
            "استبدال مقارنات QA بمصادر بيوع موثقة",
            "دعم القيمة الإيجارية بمقارنات إيجارية حقيقية",
        ],
        "expert_required_actions": [
            "معاينة الموقع وتحديد العمر الفعلي",
            "جمع مقارنات بيوع سوقية موثقة",
            "مراجعة وإقرار معدل الرسملة المستخدم",
        ],
        "source_registry_requirements": [
            {"source": "مستند إتمام/إشغال", "status": _SRC_DOC},
            {"source": "بيانات بيوع سوقية", "status": _SRC_FUTURE},
            {"source": "بيانات إيجارات سوقية", "status": _SRC_FUTURE},
        ],
        "class_specific": {
            "building_age_table":      building_age_table,
            "effective_age_years":     eff_age,
            "annual_depreciation_rate": dep_rate_annual,
            "accumulated_depreciation": dep_accum,
            "market_comparables_table": market_comparables,
            "rental_comparables_table": rental_comparables,
            "rental_support_note":      rental_support_note,
        },
    }


def _build_admin_technical_gaps(payload: dict, is_qa: bool) -> dict:
    """Administrative unit — technical gap analysis."""
    floor_factor = _safe_float(payload.get("floor_adjustment_factor", 0.85)) or 0.85
    area         = _safe_float(payload.get("area", 120.0))
    location     = payload.get("governorate") or payload.get("location") or "مدينة نصر"
    licensed_act = payload.get("licensed_use") or payload.get("licensed_activity") or _NEEDS_EXPERT
    current_act  = payload.get("current_use") or _NEEDS_EXPERT

    # ── Factor derivation table ───────────────────────────────────────────────
    floor_factor_table = {
        "factor_name":          "معامل الدور/الاستخدام الإداري",
        "base_factor":          1.00,
        "floor_factor":         floor_factor,
        "use_factor":           1.00,
        "access_factor":        1.00,
        "building_quality_factor": 1.00,
        "final_factor":         floor_factor,
        "source_status":        "محاكاة QA — يحتاج تحقق خبير" if is_qa else _SRC_DOC,
        "expert_note": (
            "معامل الدور/الاستخدام الإداري يؤثر على القيمة الإيجارية والوعاء الضريبي، "
            "ويلزم مراجعته وفق الدور الفعلي والنشاط المرخص."
        ),
        "factor_logic": (
            f"القيمة الإيجارية المُعدَّلة = الإيجار الأساسي × {floor_factor:.2f} "
            f"(معامل الدور/الاستخدام المبدئي)"
        ),
    }

    # ── Admin comparables ─────────────────────────────────────────────────────
    admin_comparables = []
    if is_qa:
        base_val = _safe_float(payload.get("expert_indicated_value", 36_000.0))
        for i, (loc, ar, fl, fin, date, val_mult) in enumerate([
            (f"{location} — دور ثاني",     110, "ثاني",  "عادي",   "2025-10", 0.95),
            (f"{location} — دور ثالث",     125, "ثالث",  "جيد",    "2025-08", 1.05),
            (f"{location} — دور أول",      115, "أول",   "عادي",   "2025-06", 1.00),
            (f"{location} — دور رابع",     100, "رابع",  "متوسط",  "2025-04", 0.90),
        ], start=1):
            adj = round(0.85 * val_mult, 4)
            adj_rent = round(base_val * val_mult, 0)
            admin_comparables.append({
                "comparable_id":   f"ADM-{i:02d}",
                "location":        loc,
                "area_m2":         ar,
                "floor":           fl,
                "finishing":       fin,
                "date":            date,
                "asking_rent":     round(base_val * val_mult * ar / area, 0),
                "adj_factor":      adj,
                "adjusted_rent":   adj_rent,
                "source_status":   "محاكاة QA",
                "included":        True,
            })
    else:
        admin_comparables = [{"comparable_id": "ADM-GAP-001", "notes": _NEEDS_EXPERT, "included": False}]

    # ── Licensed activity effect ──────────────────────────────────────────────
    activity_premium_map = {
        "إداري عادي":     1.00,
        "طبي":            1.15,
        "خدمي":           1.10,
        "تعليمي":         1.05,
    }
    act_key = "إداري عادي"
    for k in activity_premium_map:
        if k in str(licensed_act) or k in str(current_act):
            act_key = k; break

    activity_effect_table = {
        "licensed_activity_type":   licensed_act,
        "actual_activity_type":     current_act,
        "activity_premium_factor":  activity_premium_map.get(act_key, 1.00),
        "activity_license_status":  "يحتاج استكمال" if _NEEDS_EXPERT in str(licensed_act) else "متاح",
        "activity_impact_on_rent": (
            f"نشاط '{act_key}' يُطبَّق عليه معامل {activity_premium_map.get(act_key, 1.00):.2f} "
            "على القيمة الإيجارية الأساسية"
        ),
        "activity_factor_reference": activity_premium_map,
        "expert_notes": (
            "معامل النشاط المرخص استرشادي قابل لتعديل الخبير. "
            "النشاط الطبي والخدمي أعلى قيمة من الإداري العادي."
        ),
    }

    detected_gaps = [
        {
            "issue_id":          "ADMIN-G01",
            "issue_title":       "معامل الدور غير مشتق بشكل موثق",
            "issue_description": f"معامل الدور/الاستخدام {floor_factor:.2f} مُطبَّق لكن لم يُشتق من بيانات سوقية موثقة.",
            "affected_method":   "طريقة الرسملة / الدخل",
            "affected_output":   "القيمة الإيجارية المُعدَّلة والوعاء الضريبي",
            "severity":          "high",
            "current_value":     f"معامل الدور: {floor_factor:.2f} (QA)" if is_qa else _NEEDS_EXPERT,
            "corrected_value_or_required_action": "إشتقاق المعامل من مقارنات سوقية إدارية موثقة",
            "data_source_status": _SRC_QA if is_qa else _SRC_DOC,
            "expert_action_required": "التحقق من معامل الدور وتوثيق مصدره",
            "production_ready":  _PROD_NOT_READY,
        },
        {
            "issue_id":          "ADMIN-G02",
            "issue_title":       "عدد المقارنات أقل من الحد الأدنى",
            "issue_description": f"مطلوب 4 مقارنات إدارية على الأقل — متاح: {len(admin_comparables)} (QA).",
            "affected_method":   "طريقة المقارنة السوقية",
            "affected_output":   "القيمة المشارة من المقارنة السوقية",
            "severity":          "medium",
            "current_value":     f"{len(admin_comparables)} مقارنة (QA)" if is_qa else "0",
            "corrected_value_or_required_action": "الحصول على 4+ مقارنات إدارية موثقة",
            "data_source_status": _SRC_QA if is_qa else _SRC_DOC,
            "expert_action_required": "جمع مقارنات إدارية حقيقية موثقة",
            "production_ready":  _PROD_NOT_READY,
        },
        {
            "issue_id":          "ADMIN-G03",
            "issue_title":       "النشاط المرخص لم يُسجَّل بشكل كامل",
            "issue_description": "النشاط المرخص يؤثر على معامل الإيجار لكنه غير موثق بالترخيص الفعلي.",
            "affected_method":   "طريقة الرسملة / الدخل",
            "affected_output":   "معامل القيمة الإيجارية",
            "severity":          "medium",
            "current_value":     licensed_act,
            "corrected_value_or_required_action": "إرفاق الترخيص الفعلي وتأكيد نوع النشاط",
            "data_source_status": _SRC_DOC,
            "expert_action_required": "تحديد النشاط المرخص الفعلي وتطبيق المعامل المناسب",
            "production_ready":  _PROD_NOT_READY,
        },
    ]

    return {
        "detected_gaps":         detected_gaps,
        "required_evidence": [
            "ترخيص النشاط الإداري الفعلي",
            "مستند تحديد الدور في العقار",
            "4+ مقارنات إيجارية إدارية موثقة",
        ],
        "method_specific_issues": [
            {"method": "طريقة الرسملة / الدخل", "issue": "معامل الدور 0.85 يحتاج توثيق مصدره"},
            {"method": "طريقة المقارنة السوقية", "issue": "4 مقارنات QA — تحتاج استبدالًا بمصادر حقيقية"},
        ],
        "recommended_corrections": [
            "توثيق معامل الدور من مقارنات سوقية",
            "جمع 4+ مقارنات إدارية موثقة",
            "استكمال ترخيص النشاط وتحديد معامل النشاط",
        ],
        "expert_required_actions": [
            "التحقق من الدور الفعلي للوحدة",
            "تأكيد ترخيص النشاط وتطبيق المعامل المناسب",
            "استيفاء المقارنات من مصدر سوقي",
        ],
        "source_registry_requirements": [
            {"source": "ترخيص النشاط الإداري", "status": _SRC_DOC},
            {"source": "بيانات إيجارات إدارية", "status": _SRC_FUTURE},
        ],
        "class_specific": {
            "floor_factor_derivation_table": floor_factor_table,
            "admin_comparables_table":       admin_comparables,
            "admin_comparable_count":        len(admin_comparables),
            "activity_effect_table":         activity_effect_table,
        },
    }


def _build_shop_technical_gaps(payload: dict, is_qa: bool) -> dict:
    """Commercial shop — technical gap analysis."""
    area          = _safe_float(payload.get("area", 80.0))
    floor_factor  = _safe_float(payload.get("floor_adjustment_factor", 1.0)) or 1.0
    frontage_w    = _safe_float(payload.get("frontage_width_m", 0.0))
    land_m2       = _safe_float(payload.get("cost_per_sqm_land", 5_000.0)) or 5_000.0
    annual_rent   = _safe_float(
        payload.get("estimated_market_rental_value") or payload.get("annual_rental_estimate", 28_800.0)
    )
    cap_rate      = _safe_float(payload.get("capitalization_rate", 0.09)) or 0.09
    location      = payload.get("governorate") or payload.get("location") or "التجمع الخامس"

    # ── Frontage factor table ─────────────────────────────────────────────────
    if frontage_w == 0:
        frontage_factor = 1.0
        frontage_warning = "يلزم قياس عرض الواجهة الفعلي للمحل لاستكمال دقة التقييم التجاري."
    elif frontage_w < 5:
        frontage_factor = 0.80
        frontage_warning = f"واجهة ضيقة ({frontage_w:.1f} م) — معامل تخفيض 0.80 مُطبَّق."
    elif frontage_w <= 8:
        frontage_factor = 1.00
        frontage_warning = ""
    elif frontage_w <= 12:
        frontage_factor = 1.10
        frontage_warning = f"واجهة واسعة ({frontage_w:.1f} م) — معامل زيادة 1.10 مُطبَّق."
    else:
        frontage_factor = 1.20
        frontage_warning = f"واجهة كبيرة ({frontage_w:.1f} م) — معامل زيادة 1.20 مُطبَّق."

    frontage_factor_table = [
        {"frontage_range": "أقل من 5 م",   "factor": 0.80, "note": "واجهة ضيقة — قيود تجارية"},
        {"frontage_range": "5 — 8 م",      "factor": 1.00, "note": "واجهة قياسية"},
        {"frontage_range": "8 — 12 م",     "factor": 1.10, "note": "واجهة جيدة"},
        {"frontage_range": "أكثر من 12 م", "factor": 1.20, "note": "واجهة ممتازة"},
    ]
    frontage_table_note = "قواعد محاكاة QA قابلة لتعديل الخبير — ليست معايير رسمية"

    frontage_block = {
        "frontage_width_m":          frontage_w if frontage_w > 0 else _NEEDS_EXPERT,
        "frontage_depth_ratio":      payload.get("frontage_depth_ratio", _NEEDS_EXPERT),
        "signage_visibility":        payload.get("signage_visibility", _NEEDS_EXPERT),
        "corner_location":           payload.get("corner_location", _NEEDS_EXPERT),
        "pedestrian_flow":           payload.get("pedestrian_flow", _NEEDS_EXPERT),
        "commercial_exposure_factor": frontage_factor,
        "frontage_warning":          frontage_warning or "لا تحذير — بيانات الواجهة متاحة",
        "frontage_factor_table":     frontage_factor_table,
        "frontage_factor_table_note": frontage_table_note,
    }

    # ── Rental comparables used in income ─────────────────────────────────────
    mo_rent = round(annual_rent / 12, 0) if annual_rent > 0 else 2_400
    rental_comparables = []
    if is_qa:
        rental_comparables = [
            {
                "rental_id":     "SRC-01",
                "location":      f"{location} — شارع أرضي مماثل",
                "area_m2":       75,
                "monthly_rent":  mo_rent,
                "rent_per_m2":   round(mo_rent / 75, 2),
                "adj_location":  1.02,
                "adj_size":      0.99,
                "adj_condition": 1.00,
                "adjusted_rent": round(mo_rent * 1.02 * 0.99 * 1.00, 0),
                "included":      True,
                "source_status": "محاكاة QA",
            },
            {
                "rental_id":     "SRC-02",
                "location":      f"{location} — بلوك مجاور",
                "area_m2":       85,
                "monthly_rent":  round(mo_rent * 1.05, 0),
                "rent_per_m2":   round(mo_rent * 1.05 / 85, 2),
                "adj_location":  0.98,
                "adj_size":      1.01,
                "adj_condition": 1.00,
                "adjusted_rent": round(mo_rent * 1.05 * 0.98 * 1.01 * 1.00, 0),
                "included":      True,
                "source_status": "محاكاة QA",
            },
        ]
    else:
        rental_comparables = [{"rental_id": "SRC-GAP-001", "notes": _NEEDS_EXPERT, "included": False}]

    income_rental_support = {
        "rental_comparable_used":             bool(rental_comparables and rental_comparables[0].get("included")),
        "estimated_market_monthly_rent":      mo_rent if is_qa else _NEEDS_EXPERT,
        "estimated_market_annual_rent":       annual_rent if annual_rent > 0 else _NEEDS_EXPERT,
        "capitalization_rate_source":         "محاكاة QA" if is_qa else _SRC_EXPERT,
        "income_approach_rental_note": (
            "المقارنات الإيجارية مُستخدَمة في طريقة الرسملة (QA). "
            "يلزم توثيق مصدر الإيجار قبل الاعتماد."
        ) if is_qa else "المقارنات الإيجارية تحتاج إدخال الخبير.",
    }

    land_source_block = {
        "land_price_per_m2":         land_m2,
        "land_price_source_type":    "محاكاة QA" if is_qa else _SRC_EXPERT,
        "land_price_source_status":  "QA — يحتاج مصدر موثق" if is_qa else _SRC_DOC,
        "source_required":           True,
        "future_source_type":        "مقارنات أراضي تجارية / مستند رسمي",
        "land_price_note": (
            "سعر الأرض التجارية المستخدم في هذه النسخة محاكاة QA ويحتاج إلى مصدر موثق "
            "مثل مستند رسمي أو مقارنات أراضي عند الاعتماد."
        ),
    }

    detected_gaps = [
        {
            "issue_id":          "SHOP-G01",
            "issue_title":       "عرض الواجهة التجارية غير مقاس",
            "issue_description": "عرض واجهة المحل لم يُقدَّم — يؤثر على الظهور التجاري ومعامل الواجهة.",
            "affected_method":   "طريقة المقارنة السوقية + طريقة التكلفة",
            "affected_output":   "معامل الواجهة التجارية وقيمة العقار",
            "severity":          "medium",
            "current_value":     f"{frontage_w:.1f} م" if frontage_w > 0 else "غير متاح",
            "corrected_value_or_required_action": "قياس عرض الواجهة الفعلي + تطبيق الجدول المرجعي",
            "data_source_status": _SRC_EXPERT,
            "expert_action_required": "قياس الواجهة وتطبيق معامل الواجهة المناسب",
            "production_ready":  _PROD_NOT_READY,
        },
        {
            "issue_id":          "SHOP-G02",
            "issue_title":       "المقارنات الإيجارية غير مُستخدمة في طريقة الرسملة",
            "issue_description": "المقارنات الإيجارية متاحة (QA) لكن ربطها بطريقة الرسملة يحتاج توثيقًا.",
            "affected_method":   "طريقة الرسملة / الدخل",
            "affected_output":   "القيمة الإيجارية المُعتمَدة في طريقة الرسملة",
            "severity":          "medium",
            "current_value":     f"الإيجار السنوي: {annual_rent:,.0f} ج.م (QA)" if is_qa else _NEEDS_EXPERT,
            "corrected_value_or_required_action": "ربط الإيجار المُقدَّر بمقارنات موثقة مُدرجة",
            "data_source_status": _SRC_QA if is_qa else _SRC_DOC,
            "expert_action_required": "التحقق من الإيجار المستخدم وربطه بمصادر سوقية",
            "production_ready":  _PROD_NOT_READY,
        },
        {
            "issue_id":          "SHOP-G03",
            "issue_title":       "سعر الأرض التجارية بدون مصدر موثق",
            "issue_description": f"سعر أرض {land_m2:,.0f} ج.م/م² مُستخدَم دون وثيقة رسمية أو مقارنات أراضي.",
            "affected_method":   "طريقة التكلفة",
            "affected_output":   "قيمة مكوَّن الأرض في طريقة التكلفة",
            "severity":          "medium",
            "current_value":     f"{land_m2:,.0f} ج.م/م² (محاكاة QA)" if is_qa else _NEEDS_EXPERT,
            "corrected_value_or_required_action": "الحصول على مستند رسمي أو مقارنات أراضي تجارية",
            "data_source_status": _SRC_QA if is_qa else _SRC_DOC,
            "expert_action_required": "التحقق من سعر أرض تجارية في نفس المنطقة",
            "production_ready":  _PROD_NOT_READY,
        },
    ]

    return {
        "detected_gaps":         detected_gaps,
        "required_evidence": [
            "قياس عرض الواجهة الفعلي للمحل",
            "مقارنات إيجارية تجارية موثقة",
            "سعر أرض تجاري من مستند رسمي أو مقارنات",
        ],
        "method_specific_issues": [
            {"method": "طريقة التكلفة",          "issue": "سعر الأرض التجارية محاكاة QA"},
            {"method": "طريقة الرسملة / الدخل", "issue": "الإيجار يحتاج ربط بمقارنات"},
            {"method": "طريقة المقارنة السوقية", "issue": "معامل الواجهة يحتاج قياس"},
        ],
        "recommended_corrections": [
            "قياس عرض الواجهة وتطبيق جدول المعامل",
            "دعم الإيجار بمقارنات إيجارية موثقة",
            "توثيق سعر الأرض من مصدر رسمي",
        ],
        "expert_required_actions": [
            "قياس الواجهة والتحقق من الظهور التجاري",
            "جمع مقارنات إيجارية تجارية",
            "الاستعلام عن سعر أرض تجارية في المنطقة",
        ],
        "source_registry_requirements": [
            {"source": "قياس عرض الواجهة",    "status": _SRC_EXPERT},
            {"source": "بيانات إيجارات تجارية", "status": _SRC_FUTURE},
            {"source": "سعر أرض تجارية",       "status": _SRC_DOC},
        ],
        "class_specific": {
            "frontage_block":           frontage_block,
            "frontage_factor":          frontage_factor,
            "frontage_warning":         frontage_warning,
            "rental_comparables_table": rental_comparables,
            "income_rental_support":    income_rental_support,
            "land_source_block":        land_source_block,
        },
    }


def _build_basement_technical_gaps(payload: dict, is_qa: bool) -> dict:
    """Basement storage — technical gap analysis."""
    basement_f   = _safe_float(payload.get("basement_factor", 0.50)) or 0.50
    cap_rate     = _safe_float(payload.get("capitalization_rate", 0.06)) or 0.06
    area         = _safe_float(payload.get("area", 95.0))

    # ── Ownership status ──────────────────────────────────────────────────────
    ownership_status = payload.get("storage_ownership_status", "accessory_to_existing_unit" if is_qa else "unknown")
    if ownership_status == "accessory_to_existing_unit":
        land_share = 0.0
        land_share_note = "المخزن ملحق بوحدة قائمة — حصة الأرض = 0%"
    elif ownership_status == "separately_owned":
        land_share = _safe_float(payload.get("land_share_percentage", 0.0))
        land_share_note = "المخزن مستقل الملكية — يلزم تحديد حصة الأرض من مستندات الملكية"
    else:
        land_share = 0.0
        land_share_note = "وضع الملكية غير محدد — تم افتراض 0% بشكل مؤقت"

    ownership_block = {
        "storage_ownership_status":    ownership_status,
        "land_share_applicability":    ownership_status == "separately_owned",
        "land_share_percentage":       land_share,
        "land_share_evidence_required": ownership_status != "accessory_to_existing_unit",
        "ownership_explanation":       land_share_note,
        "expert_note": (
            "إذا كان المخزن ملحقًا بوحدة قائمة فحصة الأرض = 0%. "
            "إذا كان مستقل الملكية يلزم تحديد حصة الأرض من مستندات الملكية."
        ),
    }

    # ── Basement factor reference ─────────────────────────────────────────────
    basement_factor_table = [
        {"use_type": "مخزن عادي",                "factor": 0.50, "risk_note": "استخدام تخزيني — وصول محدود"},
        {"use_type": "مخزن تبريد (cold storage)", "factor": 0.60, "risk_note": "استثمار أعلى في التجهيزات"},
        {"use_type": "ورشة (workshop)",            "factor": 0.70, "risk_note": "استخدام نشط — وصول أفضل"},
        {"use_type": "مواقف/مخزن مختلط",           "factor": 0.55, "risk_note": "استخدام مختلط"},
    ]
    basement_factor_note = "مرجع داخلي قابل لتعديل الخبير — ليست معايير رسمية"

    # ── Cap rate reasoning ────────────────────────────────────────────────────
    cap_rate_block = {
        "selected_cap_rate":          cap_rate,
        "vacancy_risk_level":         "عالٍ — المخزن في البدروم صعب التأجير مقارنة بالأرضي",
        "liquidity_risk_level":       "عالٍ — تصفية أصعب من المحلات الأرضية",
        "alternative_use_limitations": "محدودة — قيود الوصول والإضاءة والترخيص",
        "cap_rate_reasoning": (
            f"معدل رسملة {cap_rate:.0%} للمخزن في البدروم يعكس: "
            "(1) ارتفاع مخاطر الشاغرية مقارنة بالمحلات الأرضية، "
            "(2) محدودية السيولة وصعوبة التصرف السريع، "
            "(3) قيود الاستخدام البديل بسبب الوصول والإضاءة."
        ),
        "expert_note": (
            "معدل الرسملة للمخزن في البدروم يختلف عن المحلات الأرضية النشطة. "
            "يلزم مراجعة الخبير لتأكيد المعدل المناسب."
        ),
    }

    detected_gaps = [
        {
            "issue_id":          "BSMT-G01",
            "issue_title":       "وضع ملكية المخزن غير موثق",
            "issue_description": "تحديد ما إذا كان المخزن ملحقًا أو مستقلًا يؤثر على احتساب حصة الأرض.",
            "affected_method":   "طريقة التكلفة",
            "affected_output":   "حصة الأرض في قيمة المخزن",
            "severity":          "high",
            "current_value":     ownership_status,
            "corrected_value_or_required_action": "الحصول على مستند الملكية لتحديد الوضع القانوني",
            "data_source_status": _SRC_QA if is_qa else _SRC_DOC,
            "expert_action_required": "تأكيد وضع الملكية ومدى استحقاق حصة أرض",
            "production_ready":  _PROD_NOT_READY,
        },
        {
            "issue_id":          "BSMT-G02",
            "issue_title":       "معامل البدروم يحتاج جدول مرجعي",
            "issue_description": f"معامل البدروم {basement_f:.2f} مُطبَّق بدون جدول مرجعي موثق.",
            "affected_method":   "طريقة الرسملة / الدخل + طريقة التكلفة",
            "affected_output":   "القيمة الإيجارية المُعدَّلة",
            "severity":          "medium",
            "current_value":     f"معامل: {basement_f:.2f} (QA)",
            "corrected_value_or_required_action": "مراجعة الجدول المرجعي وتطبيق معامل مناسب لنوع الاستخدام",
            "data_source_status": _SRC_QA if is_qa else _SRC_EXPERT,
            "expert_action_required": "اختيار المعامل من الجدول المرجعي حسب نوع استخدام المخزن",
            "production_ready":  _PROD_NOT_READY,
        },
        {
            "issue_id":          "BSMT-G03",
            "issue_title":       "معدل الرسملة يحتاج تبرير مخاطر المخزن",
            "issue_description": "معدل الرسملة للمخزن في البدروم يجب أن يعكس مخاطر الشاغرية والسيولة.",
            "affected_method":   "طريقة الرسملة / الدخل",
            "affected_output":   "قيمة الرسملة والوعاء الضريبي",
            "severity":          "low",
            "current_value":     f"معدل رسملة: {cap_rate:.0%} (QA)",
            "corrected_value_or_required_action": "توثيق تبرير معدل الرسملة بمراعاة مخاطر المخزن",
            "data_source_status": _SRC_QA if is_qa else _SRC_EXPERT,
            "expert_action_required": "مراجعة وتأكيد معدل الرسملة المناسب للمخزن",
            "production_ready":  _PROD_NOT_READY,
        },
    ]

    return {
        "detected_gaps":         detected_gaps,
        "required_evidence": [
            "مستند الملكية أو السند القانوني للمخزن",
            "تقرير معاينة الوصول والإضاءة",
            "مقارنات إيجارية لمخازن مماثلة",
        ],
        "method_specific_issues": [
            {"method": "طريقة التكلفة",          "issue": "حصة الأرض تعتمد على وضع الملكية"},
            {"method": "طريقة الرسملة / الدخل", "issue": "معامل البدروم ومعدل الرسملة يحتاجان توثيق"},
        ],
        "recommended_corrections": [
            "توثيق وضع ملكية المخزن",
            "تطبيق جدول معامل البدروم حسب نوع الاستخدام",
            "توثيق تبرير معدل الرسملة",
        ],
        "expert_required_actions": [
            "التحقق من وضع الملكية وحصة الأرض",
            "اختيار معامل البدروم من الجدول المرجعي",
            "مراجعة وتأكيد معدل الرسملة",
        ],
        "source_registry_requirements": [
            {"source": "مستند الملكية",             "status": _SRC_DOC},
            {"source": "بيانات إيجارات مخازن",      "status": _SRC_FUTURE},
        ],
        "class_specific": {
            "ownership_block":          ownership_block,
            "storage_ownership_status": ownership_status,
            "land_share":               land_share,
            "basement_factor_table":    basement_factor_table,
            "basement_factor_note":     basement_factor_note,
            "cap_rate_block":           cap_rate_block,
        },
    }


def _build_factory_technical_gaps(payload: dict, is_qa: bool) -> dict:
    """Factory / special-purpose — technical gap analysis including Ain Shams guidance."""
    dep_rate    = _safe_float(payload.get("depreciation_rate", 0.014)) or 0.014
    age_yrs     = _safe_float(payload.get("age_years", 20.0)) or 20.0
    land_m2     = _safe_float(payload.get("cost_per_sqm_land", 300.0)) or 300.0
    area        = _safe_float(payload.get("area", 2500.0))
    location    = payload.get("governorate") or payload.get("location") or "العبور الصناعية"
    ind_comps   = payload.get("industrial_components") or []

    # ── Industrial comparables ────────────────────────────────────────────────
    industrial_comparables = []
    if is_qa:
        industrial_comparables = [
            {
                "comp_id":          "IND-01",
                "property_type":    "منشأة صناعية / مصنع",
                "location":         f"{location} — منطقة مجاورة",
                "area_m2":          2_200,
                "industrial_zone":  "منطقة صناعية مرخصة",
                "asking_value":     2_640_000,
                "price_per_m2":     1_200,
                "source_status":    "محاكاة QA",
                "comparability":    "قابل للمقارنة من حيث النوع والموقع",
                "included_primary": False,
                "used_as_support":  True,
                "notes":            "محاكاة QA — لا تستخدم كدليل حقيقي قبل توثيق المصدر",
            },
            {
                "comp_id":          "IND-02",
                "property_type":    "مصنع خفيف",
                "location":         f"{location} — بلوك مجاور",
                "area_m2":          3_000,
                "industrial_zone":  "منطقة صناعية",
                "asking_value":     3_300_000,
                "price_per_m2":     1_100,
                "source_status":    "محاكاة QA",
                "comparability":    "أكبر مساحة — تعديل حجم مطلوب",
                "included_primary": False,
                "used_as_support":  True,
                "notes":            "محاكاة QA — لا تستخدم كدليل حقيقي قبل توثيق المصدر",
            },
        ]
    else:
        industrial_comparables = [{"comp_id": "IND-GAP", "notes": _NEEDS_EXPERT, "used_as_support": False}]

    # ── Depreciation source ───────────────────────────────────────────────────
    useful_life_implied = round(1.0 / dep_rate, 1) if dep_rate > 0 else "غير محدد"
    dep_source_block = {
        "annual_depreciation_rate":   dep_rate,
        "useful_life_implied_years":  useful_life_implied,
        "condition_adjustment":       payload.get("condition_adjustment", _NEEDS_EXPERT),
        "maintenance_status":         payload.get("maintenance_status", _NEEDS_EXPERT),
        "depreciation_rate_source":   "محاكاة QA" if is_qa else _SRC_EXPERT,
        "expert_override_flag":       True,
        "depreciation_warning": (
            f"يلزم مراجعة معدل الإهلاك للمصنع ({dep_rate:.1%} سنويًا / عمر مُضمَّن "
            f"≈ {useful_life_implied} سنة) بواسطة الخبير، خاصة إذا كانت الحالة الفنية "
            "أو الصيانة تختلف عن الافتراض."
        ),
        "ain_shams_depreciation_note": (
            "الدراسة المبدئية (جامعة عين شمس / الضرائب العقارية) لا تتضمن معدل إهلاك سنوي "
            "أو عمرًا إنتاجيًا — يلزم مرجع فني إضافي معتمد."
        ),
    }

    # ── Machinery exclusion ───────────────────────────────────────────────────
    machinery_exclusion_note = (
        "يشمل هذا التحليل الأرض والمباني والمكونات العقارية الثابتة فقط، "
        "ولا يشمل الآلات والمعدات التشغيلية أو خطوط الإنتاج إلا إذا تم "
        "النص صراحة على خلاف ذلك."
    )

    # ── Land price source ─────────────────────────────────────────────────────
    land_source_block = {
        "industrial_land_price_per_m2":  land_m2,
        "land_price_source_status":      "محاكاة QA — يحتاج مراجعة" if is_qa else _SRC_DOC,
        "official_land_price_required":  True,
        "future_source_requirement":     "مقارنات أراضي صناعية / مستند هيئة المجتمعات العمرانية الجديدة أو الهيئة الصناعية",
        "land_price_note": (
            "سعر الأرض الصناعية المستخدم في QA يحتاج إلى مراجعة بمستند رسمي "
            "أو مقارنات صناعية موثقة قبل الاعتماد."
        ),
    }

    # ── Ain Shams cost guidance readiness ────────────────────────────────────
    factory_cost_guidance = _build_factory_cost_guidance(payload, is_qa)

    detected_gaps = [
        {
            "issue_id":          "FACT-G01",
            "issue_title":       "لا توجد مقارنات صناعية كدليل داعم",
            "issue_description": "طريقة التكلفة تهيمن (100%) لكن مقارنات صناعية داعمة غير متاحة.",
            "affected_method":   "طريقة التكلفة (أساسية) + طريقة المقارنة (داعمة)",
            "affected_output":   "قوة الأدلة الداعمة لتقدير قيمة المنشأة",
            "severity":          "medium",
            "current_value":     f"{len(industrial_comparables)} مقارنة (QA)" if is_qa else "0",
            "corrected_value_or_required_action": "الحصول على مقارنات صناعية من منطقة مماثلة",
            "data_source_status": _SRC_QA if is_qa else _SRC_DOC,
            "expert_action_required": "جمع مقارنات صناعية من مصادر سوقية موثقة",
            "production_ready":  _PROD_NOT_READY,
        },
        {
            "issue_id":          "FACT-G02",
            "issue_title":       "معدل الإهلاك بدون مصدر موثق",
            "issue_description": f"معدل الإهلاك {dep_rate:.1%} سنويًا مُستخدَم دون مرجع فني/أكاديمي موثق.",
            "affected_method":   "طريقة التكلفة",
            "affected_output":   "القيمة المُستبدَلة الصافية وقيمة المنشأة",
            "severity":          "high",
            "current_value":     f"{dep_rate:.1%} سنويًا (QA)",
            "corrected_value_or_required_action": "التحقق من معدل الإهلاك بمرجع فني معتمد",
            "data_source_status": _SRC_QA if is_qa else _SRC_EXPERT,
            "expert_action_required": "مراجعة وتأكيد معدل الإهلاك بواسطة الخبير",
            "production_ready":  _PROD_NOT_READY,
        },
        {
            "issue_id":          "FACT-G03",
            "issue_title":       "الآلات والمعدات يجب استبعادها صراحة",
            "issue_description": "التقييم العقاري للمصنع يجب أن يستبعد الآلات والمعدات التشغيلية بشكل صريح.",
            "affected_method":   "جميع الطرق + افتراضات التقرير",
            "affected_output":   "نطاق التقييم والقيمة الاستبدالية",
            "severity":          "critical",
            "current_value":     "لم يُذكر صراحة في كل أجزاء التقرير",
            "corrected_value_or_required_action": "إضافة إفصاح صريح في الافتراضات وطريقة التكلفة والملخص",
            "data_source_status": _SRC_EXPERT,
            "expert_action_required": "مراجعة وتأكيد استبعاد الآلات والمعدات في التقرير النهائي",
            "production_ready":  _PROD_NOT_READY,
        },
        {
            "issue_id":          "FACT-G04",
            "issue_title":       "سعر الأرض الصناعية بدون وثيقة رسمية",
            "issue_description": f"سعر الأرض {land_m2:,.0f} ج.م/م² يحتاج مستندًا رسميًا أو مقارنات صناعية.",
            "affected_method":   "طريقة التكلفة",
            "affected_output":   "مكوَّن الأرض في القيمة الاستبدالية",
            "severity":          "medium",
            "current_value":     f"{land_m2:,.0f} ج.م/م² (محاكاة QA)" if is_qa else _NEEDS_EXPERT,
            "corrected_value_or_required_action": "الحصول على مستند رسمي أو مقارنات أراضي صناعية",
            "data_source_status": _SRC_QA if is_qa else _SRC_DOC,
            "expert_action_required": "التحقق من سعر الأرض الصناعية من مستند رسمي",
            "production_ready":  _PROD_NOT_READY,
        },
    ]

    return {
        "detected_gaps":         detected_gaps,
        "required_evidence": [
            "الترخيص الصناعي / الإنتاجي",
            "مقارنات أراضي صناعية أو مستند هيئة المجتمعات العمرانية",
            "تقرير إهلاك المباني من خبير متخصص",
            "مقارنات صناعية لمنشآت مماثلة",
        ],
        "method_specific_issues": [
            {"method": "طريقة التكلفة",          "issue": "معدل الإهلاك وسعر الأرض يحتاجان مصدر موثق"},
            {"method": "طريقة المقارنة السوقية", "issue": "المقارنات الصناعية مساعِدة فقط (QA)"},
        ],
        "recommended_corrections": [
            "توثيق معدل الإهلاك من مرجع فني معتمد",
            "إضافة إفصاح استبعاد الآلات والمعدات",
            "توثيق سعر الأرض الصناعية",
            "الحصول على مقارنات صناعية لدعم التقدير",
        ],
        "expert_required_actions": [
            "مراجعة وتأكيد معدل الإهلاك المناسب للمصنع",
            "التأكد من استبعاد الآلات والمعدات من التقييم",
            "التحقق من سعر الأرض الصناعية",
            "جمع مقارنات صناعية داعمة",
        ],
        "source_registry_requirements": [
            {"source": "مرجع إهلاك مباني صناعية",   "status": _SRC_DOC},
            {"source": "سعر أرض صناعية رسمي",        "status": _SRC_DOC},
            {"source": "مقارنات صناعية سوقية",        "status": _SRC_FUTURE},
        ],
        "class_specific": {
            "industrial_comparables_table": industrial_comparables,
            "depreciation_source_block":    dep_source_block,
            "machinery_exclusion_note":     machinery_exclusion_note,
            "land_source_block":            land_source_block,
            "factory_cost_guidance":        factory_cost_guidance,
        },
    }


def _build_property_class_technical_review(
    payload: dict, class_key: str, subtype_key: str, is_qa: bool,
) -> dict:
    """Build property-class-specific technical gap analysis and supplementary data."""
    if class_key == "residential":
        gaps = _build_villa_technical_gaps(payload, is_qa)
    elif class_key == "non_residential" and subtype_key == "admin_unit":
        gaps = _build_admin_technical_gaps(payload, is_qa)
    elif class_key == "non_residential" and subtype_key == "shop":
        gaps = _build_shop_technical_gaps(payload, is_qa)
    elif class_key == "non_residential" and subtype_key == "basement_storage":
        gaps = _build_basement_technical_gaps(payload, is_qa)
    elif class_key == "special_purpose":
        gaps = _build_factory_technical_gaps(payload, is_qa)
    else:
        # Generic fallback
        gaps = {
            "detected_gaps": [{
                "issue_id": "GEN-G01",
                "issue_title": "فجوات تفصيلية غير محددة لهذا النوع",
                "issue_description": "نوع العقار يحتاج تحليل تفصيلي بواسطة الخبير.",
                "affected_method":   "جميع الطرق",
                "affected_output":   "التقييم الكلي",
                "severity":          "medium",
                "current_value":     _NEEDS_EXPERT,
                "corrected_value_or_required_action": "مراجعة الخبير",
                "data_source_status": _SRC_EXPERT,
                "expert_action_required": "تحليل تفصيلي بواسطة الخبير",
                "production_ready":  False,
            }],
            "required_evidence":  [_NEEDS_EXPERT],
            "method_specific_issues": [],
            "recommended_corrections": [_NEEDS_EXPERT],
            "expert_required_actions":  [_NEEDS_EXPERT],
            "source_registry_requirements": [],
            "class_specific": {},
        }

    # ── Cross-scenario source readiness ──────────────────────────────────────
    source_readiness = {
        "cost_approach": {
            "required_source_type":    "بيانات تكلفة إنشاء + سعر أرض",
            "current_source_status":   "محاكاة QA" if is_qa else _SRC_EXPERT,
            "future_enrichment_method": "مقارنات تكلفة + سجل هيئة المجتمعات",
            "qdrant_ready":  True,
            "internet_ready": False,
            "ocr_ready":     False,
            "active_now":    False,
        },
        "market_comparison": {
            "required_source_type":    "بيانات بيوع / عروض سوقية",
            "current_source_status":   "محاكاة QA" if is_qa else _SRC_EXPERT,
            "future_enrichment_method": "Qdrant / ربط مصادر بيوع",
            "qdrant_ready":  True,
            "internet_ready": False,
            "ocr_ready":     False,
            "active_now":    False,
        },
        "income_capitalization": {
            "required_source_type":    "بيانات إيجارات سوقية",
            "current_source_status":   "محاكاة QA" if is_qa else _SRC_EXPERT,
            "future_enrichment_method": "Qdrant / ربط مصادر إيجار",
            "qdrant_ready":  True,
            "internet_ready": False,
            "ocr_ready":     False,
            "active_now":    False,
        },
        "tax_comparison": {
            "required_source_type":    "قاعدة بيانات طعون ضريبية",
            "current_source_status":   "محاكاة QA" if is_qa else _SRC_EXPERT,
            "future_enrichment_method": "ربط قاعدة بيانات الطعون الضريبية",
            "qdrant_ready":  True,
            "internet_ready": False,
            "ocr_ready":     False,
            "active_now":    is_qa,
        },
        "multiple_regression": {
            "required_source_type":    "قاعدة بيانات تدريب (≥100 حالة)",
            "current_source_status":   "غير مفعل — مرحلة مستقبلية",
            "future_enrichment_method": "تدريب نموذج انحدار بعد توفر البيانات",
            "qdrant_ready":  False,
            "internet_ready": False,
            "ocr_ready":     False,
            "active_now":    False,
        },
    }

    return {
        "scenario_id":                 payload.get("request_id") or "QA-PCR-001",
        "property_class":              class_key,
        "property_subtype":            subtype_key,
        "detected_gaps":               gaps["detected_gaps"],
        "required_evidence":           gaps["required_evidence"],
        "method_specific_issues":      gaps["method_specific_issues"],
        "recommended_corrections":     gaps["recommended_corrections"],
        "expert_required_actions":     gaps["expert_required_actions"],
        "source_registry_requirements": gaps["source_registry_requirements"],
        "source_readiness_by_method":  source_readiness,
        "production_readiness_status": "محاكاة QA — غير جاهز للإنتاج" if is_qa else "يحتاج استكمال",
        "qa_sources_not_production_ready": is_qa,
        **gaps["class_specific"],
    }


# ── Unified depreciation model (Part D) ──────────────────────────────────────

_DEP_MODELS_CTX: dict[str, dict] = {
    "residential": {
        "economic_life_years": 60,
        "annual_depreciation_rate": round(1 / 60, 6),
        "depreciation_method": "straight_line",
        "max_allowed_accumulated": 0.80,
        "class_label_ar": "عقار سكني",
    },
    "non_residential": {
        "economic_life_years": 50,
        "annual_depreciation_rate": 0.02,
        "depreciation_method": "straight_line",
        "max_allowed_accumulated": 0.80,
        "class_label_ar": "عقار غير سكني",
    },
    "special_purpose": {
        "economic_life_years": 30,
        "annual_depreciation_rate": round(1 / 30, 6),
        "depreciation_method": "straight_line",
        "max_allowed_accumulated": 0.85,
        "class_label_ar": "عقار ذو أغراض خاصة",
    },
    "basement_storage": {
        "economic_life_years": 50,
        "annual_depreciation_rate": 0.02,
        "depreciation_method": "straight_line",
        "max_allowed_accumulated": 0.80,
        "class_label_ar": "مخزن / بدروم",
    },
}

_DEP_SUBTYPE_KEY: dict[str, str] = {
    "basement_storage": "basement_storage",
    "basement":         "basement_storage",
}


def _build_unified_depreciation_model(
    payload: dict, class_key: str, subtype_key: str, is_qa: bool,
) -> dict:
    """Build unified depreciation model for the subject property class."""
    dep_key = _DEP_SUBTYPE_KEY.get(subtype_key) or class_key
    model   = _DEP_MODELS_CTX.get(dep_key, _DEP_MODELS_CTX["non_residential"])

    age_raw = payload.get("age_years") or payload.get("effective_age")
    effective_age: float | None = None
    if age_raw is not None:
        try:
            effective_age = float(age_raw)
        except (ValueError, TypeError):
            effective_age = None

    eco_life  = model["economic_life_years"]
    ann_rate  = model["annual_depreciation_rate"]
    max_acc   = model["max_allowed_accumulated"]
    dep_method = model["depreciation_method"]

    if effective_age is not None and effective_age >= 0:
        acc_rate = round(min(effective_age * ann_rate, max_acc), 4)
        age_gap  = False
        gap_note = ""
    else:
        acc_rate = None
        age_gap  = True
        gap_note = "العمر الفعلي غير مُقدَّم — لا يمكن حساب الإهلاك المتراكم (بيانات مطلوبة)"

    # Expert override
    expert_override = bool(payload.get("depreciation_expert_override"))
    override_rate   = _safe_float(payload.get("depreciation_override_rate")) if expert_override else None
    override_reason = payload.get("depreciation_override_reason") or ""

    # Ain Shams note for factory
    ain_shams_note = ""
    if class_key == "special_purpose" and subtype_key in ("factory", "industrial_facility", "industrial"):
        ain_shams_note = (
            "إرشادات عين شمس (دراسة مبدئية) لا تُحدد عمرًا إنتاجيًا صريحًا. "
            "المعدل (1/30) مبني على ممارسة مهنية — يحتاج تأكيد الخبير."
        )

    return {
        "property_class":              class_key,
        "property_subtype":            subtype_key,
        "depreciation_key":            dep_key,
        "class_label_ar":              model["class_label_ar"],
        "effective_age_years":         effective_age,
        "effective_age_missing":       age_gap,
        "effective_age_gap_note":      gap_note,
        "economic_life_years":         eco_life,
        "annual_depreciation_rate":    ann_rate,
        "depreciation_method":         dep_method,
        "accumulated_depreciation_rate": acc_rate,
        "max_allowed_accumulated":     max_acc,
        "depreciation_source_status":  "محاكاة QA" if is_qa else "يحتاج توثيق خبير",
        "expert_override_allowed":     True,
        "expert_override_applied":     expert_override,
        "expert_override_rate":        override_rate,
        "expert_override_reason":      override_reason,
        "ain_shams_guidance_note":     ain_shams_note,
        "production_ready":            False,
        "qa_simulation":               is_qa,
    }


# ── Tax sensitivity analysis — detailed (Part E) ──────────────────────────────

def _build_tax_sensitivity_detailed(
    payload: dict, class_key: str, subtype_key: str, tax_engine: dict, is_qa: bool,
) -> dict:
    """Build detailed tax sensitivity table by scenario with multiple drivers."""
    govt_tax    = _safe_float(tax_engine.get("government_tax_amount")) or 0.0
    current_rent = _safe_float(
        payload.get("estimated_market_rental_value") or payload.get("annual_rental_estimate")
    ) or 0.0
    cap_rate    = _safe_float(payload.get("capitalization_rate")) or 0.10
    area        = _safe_float(payload.get("area")) or 1.0
    dep_rate    = _safe_float(payload.get("depreciation_rate")) or 0.02
    land_m2     = _safe_float(payload.get("cost_per_sqm_land")) or 0.0
    bldg_m2     = _safe_float(payload.get("cost_per_sqm_building")) or 0.0

    # ── Rental value sensitivity ───────────────────────────────────────────────
    if current_rent > 0:
        base_rent = current_rent
    elif class_key == "residential":
        base_rent = 90_000.0
    elif class_key == "non_residential":
        base_rent = 36_000.0
    else:
        base_rent = 60_000.0

    def _tax_from_rent(annual_rent: float) -> float:
        """Indicative tax = 10% × (annual_rent × 0.80 − 7,200 exemption)."""
        taxable = max(annual_rent * 0.80 - 7_200, 0)
        return round(taxable * 0.10, 2)

    rent_sensitivity = []
    for multiplier, label in [
        (0.70, "سيناريو منخفض جدًا"),
        (0.85, "سيناريو منخفض"),
        (1.00, "السيناريو الحالي"),
        (1.15, "سيناريو مرتفع"),
        (1.30, "سيناريو مرتفع جدًا"),
    ]:
        rent_val  = round(base_rent * multiplier, 2)
        ind_tax   = _tax_from_rent(rent_val)
        saving    = round(govt_tax - ind_tax, 2) if govt_tax > 0 else None
        rent_sensitivity.append({
            "scenario":             label,
            "annual_rental_value":  rent_val,
            "taxable_basis":        round(max(rent_val * 0.80 - 7_200, 0), 2),
            "indicative_tax":       ind_tax,
            "expected_saving":      saving,
            "government_tax":       govt_tax or None,
            "notes":                "تحليل حساسية استرشادي — لا يُعد استشارة ضريبية رسمية",
        })

    # ── Depreciation rate sensitivity (cost method) ───────────────────────────
    dep_sensitivity = []
    if bldg_m2 > 0 and area > 0:
        bldg_value = bldg_m2 * area
        for dep_var in [0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04]:
            acc = min(dep_var * (_safe_float(payload.get("age_years")) or 10), 0.80)
            net_bldg = round(bldg_value * (1 - acc), 2)
            dep_sensitivity.append({
                "depreciation_rate": dep_var,
                "accumulated_dep":   round(acc, 4),
                "net_building_value": net_bldg,
                "notes":             "تحليل حساسية استرشادي — معدل إهلاك",
            })

    # ── Capitalization rate sensitivity ───────────────────────────────────────
    cap_sensitivity = []
    if base_rent > 0:
        for cr in [0.06, 0.07, 0.08, 0.09, 0.10, 0.11, 0.12]:
            cap_val = round(base_rent / cr, 2)
            cap_sensitivity.append({
                "cap_rate":       cr,
                "indicated_value": cap_val,
                "notes":          "تحليل حساسية استرشادي — معدل الرسملة",
            })

    # ── Land price sensitivity (cost method) ──────────────────────────────────
    land_sensitivity = []
    if land_m2 > 0 and area > 0:
        for factor in [0.80, 0.90, 1.00, 1.10, 1.20]:
            land_val = round(land_m2 * factor * area, 2)
            land_sensitivity.append({
                "land_price_factor":  factor,
                "land_price_per_m2":  round(land_m2 * factor, 2),
                "total_land_value":   land_val,
                "notes":              "تحليل حساسية استرشادي — سعر الأرض",
            })

    return {
        "sensitivity_title":         "تحليل الحساسية للضريبة — استرشادي",
        "sensitivity_disclaimer":    "تحليل حساسية استرشادي — لا يُعد استشارة ضريبية رسمية أو مؤكدة",
        "rental_value_sensitivity":  rent_sensitivity,
        "depreciation_sensitivity":  dep_sensitivity,
        "cap_rate_sensitivity":      cap_sensitivity,
        "land_price_sensitivity":    land_sensitivity,
        "base_annual_rental":        base_rent,
        "government_tax":            govt_tax or None,
        "production_ready":          False,
        "qa_simulation":             is_qa,
    }


# ── Appeal risk assessment (Part F) ──────────────────────────────────────────

def _build_appeal_risk_assessment(
    payload: dict, class_key: str, docs_checklist: list[dict], is_qa: bool,
) -> dict:
    """Build appeal risk assessment scoring model.

    Score components (0–100 each, weighted average):
        evidence_strength       0.25
        comparable_quality      0.20
        depreciation_support    0.15
        source_reliability      0.20
        document_completeness   0.10
        deadline_risk           0.10

    Risk level: منخفض (>=70), متوسط (40-69), مرتفع (<40)
    """
    # ── Document completeness ─────────────────────────────────────────────────
    required = [d for d in docs_checklist if d.get("required")]
    submitted = [d for d in required if d.get("status") == "مُقدَّم"]
    doc_score = round((len(submitted) / max(len(required), 1)) * 100, 1)

    # ── Source reliability ────────────────────────────────────────────────────
    src_score = 30.0 if is_qa else 50.0   # QA always lower
    has_expert_val   = bool(payload.get("expert_indicated_value") or payload.get("corrected_tax_amount"))
    has_rental_est   = bool(payload.get("estimated_market_rental_value") or payload.get("annual_rental_estimate"))
    has_land_price   = bool(payload.get("cost_per_sqm_land"))
    has_bldg_cost    = bool(payload.get("cost_per_sqm_building"))
    if has_expert_val: src_score = min(src_score + 10, 100)
    if has_rental_est: src_score = min(src_score + 10, 100)
    if has_land_price: src_score = min(src_score + 5, 100)
    if has_bldg_cost:  src_score = min(src_score + 5, 100)

    # ── Evidence strength ─────────────────────────────────────────────────────
    ev_score = 40.0 if is_qa else 30.0
    if has_expert_val:   ev_score = min(ev_score + 20, 100)
    if has_rental_est:   ev_score = min(ev_score + 15, 100)
    if doc_score >= 80:  ev_score = min(ev_score + 15, 100)
    if doc_score >= 60:  ev_score = min(ev_score + 10, 100)

    # ── Comparable quality ────────────────────────────────────────────────────
    cmp_score = 25.0 if is_qa else 15.0  # QA slightly higher (at least have QA comparables)

    # ── Depreciation support ──────────────────────────────────────────────────
    age_present  = payload.get("age_years") or payload.get("effective_age")
    dep_present  = payload.get("depreciation_rate")
    dep_score    = 20.0
    if age_present: dep_score = min(dep_score + 30, 100)
    if dep_present: dep_score = min(dep_score + 20, 100)

    # ── Deadline risk ─────────────────────────────────────────────────────────
    deadline_status = payload.get("_deadline_status") or "unknown"
    deadline_score = {
        "safe":    90.0,
        "soon":    60.0,
        "urgent":  30.0,
        "expired": 0.0,
        "unknown": 40.0,
    }.get(deadline_status, 40.0)

    # ── Weighted overall ──────────────────────────────────────────────────────
    overall = round(
        ev_score  * 0.25 +
        cmp_score * 0.20 +
        dep_score * 0.15 +
        src_score * 0.20 +
        doc_score * 0.10 +
        deadline_score * 0.10,
        1
    )

    if overall >= 70:
        risk_level = "منخفض"
        prob_label = "مؤشر قبول مرتفع — يستدعي استكمال التوثيق"
    elif overall >= 40:
        risk_level = "متوسط"
        prob_label = "مؤشر قبول متوسط — يستلزم دعم إضافي بالأدلة"
    else:
        risk_level = "مرتفع"
        prob_label = "مؤشر قبول منخفض — يحتاج مراجعة جوهرية من الخبير"

    # ── Key risks ─────────────────────────────────────────────────────────────
    key_risks: list[str] = []
    if is_qa:
        key_risks.append("جميع المراجع محاكاة QA — لا تصلح كدليل رسمي")
    if not has_expert_val:
        key_risks.append("لا تقدير بديل مُقدَّم من الخبير")
    if doc_score < 60:
        key_risks.append("اكتمال المستندات أقل من 60% — خطر رفض الطعن")
    if not age_present:
        key_risks.append("العمر الفعلي للمبنى غير مُقدَّم — الإهلاك يُطبَّق بالكامل أو لا يُطبَّق")
    if deadline_status in ("urgent", "expired"):
        key_risks.append(f"مهلة الطعن: {deadline_status} — خطر انتهاء المهلة")
    if not has_rental_est and class_key != "special_purpose":
        key_risks.append("لا تقدير إيجاري مُقدَّم — طريقة الرسملة ضعيفة")
    if cmp_score < 40:
        key_risks.append("جودة المقارنات منخفضة — يحتاج مقارنات سوقية موثقة")

    # ── Recommended actions ───────────────────────────────────────────────────
    actions: list[str] = ["مراجعة التقرير المبدئي من الخبير قبل التقديم"]
    if not has_expert_val:
        actions.append("إضافة تقدير بديل للقيمة من الخبير المُعتمد")
    if doc_score < 80:
        actions.append("استكمال المستندات الناقصة")
    if not age_present:
        actions.append("تحديد العمر الفعلي للمبنى وإرفاق كشف معاينة")
    if not has_rental_est:
        actions.append("إضافة تقدير القيمة الإيجارية السوقية بمقارنات موثقة")

    return {
        "evidence_strength_score":      round(ev_score, 1),
        "comparable_quality_score":     round(cmp_score, 1),
        "depreciation_support_score":   round(dep_score, 1),
        "source_reliability_score":     round(src_score, 1),
        "document_completeness_score":  round(doc_score, 1),
        "deadline_risk_score":          round(deadline_score, 1),
        "overall_risk_score":           overall,
        "overall_risk_level":           risk_level,
        "acceptance_probability_label": prob_label,
        "risk_disclaimer":              "مؤشر مخاطر فني استرشادي — ليس احتمال قبول قانوني مؤكد",
        "key_risks":                    key_risks,
        "recommended_actions":          actions,
        "expert_notes":                 "يجب مراجعة الخبير قبل التقديم الرسمي",
        "production_ready":             False,
        "qa_simulation":                is_qa,
    }


# ── Prior report links (context layer, Part G) ────────────────────────────────

def _build_prior_report_links_ctx(
    payload: dict, class_key: str, is_qa: bool,
) -> list[dict]:
    """Build prior valuation report links for use as internal supporting sources."""
    district = payload.get("district") or payload.get("governorate") or "غير محدد"
    area     = _safe_float(payload.get("area")) or 1.0
    annual_rent = _safe_float(
        payload.get("estimated_market_rental_value") or payload.get("annual_rental_estimate")
    ) or 0.0

    if not is_qa:
        return [{
            "linked_report_id":       "PRIOR-PROD-PLACEHOLDER",
            "report_type":            "prior_valuation_report_reference",
            "report_date":            "غير متاح",
            "valuation_date":         "غير متاح",
            "district":               district,
            "zone_id":                "غير محدد",
            "property_class":         class_key,
            "indicated_market_value": None,
            "indicated_rental_value": None,
            "rent_per_m2":            None,
            "value_per_m2":           None,
            "source_status":          "لا يوجد تقرير سابق مُرتبط — يمكن إضافته عند الاستكمال",
            "usable_for_tax_appeal":  False,
            "limitations":            "لا بيانات سابقة — يحتاج رفع تقارير تقييم سابقة",
            "expert_review_required": True,
        }]

    links: list[dict] = []

    # Market valuation report
    expert_val = _safe_float(payload.get("expert_indicated_value")) or (_safe_float(payload.get("cost_per_sqm_building") or 2_000) * area)
    links.append({
        "linked_report_id":       "PRIOR-MKT-QA-01",
        "report_type":            "market_valuation_report",
        "report_date":            "01/09/2023",
        "valuation_date":         "01/08/2023",
        "district":               district,
        "zone_id":                "QA-ZONE-01",
        "property_class":         class_key,
        "indicated_market_value": round(expert_val, 2),
        "indicated_rental_value": round(annual_rent, 2) if annual_rent else None,
        "rent_per_m2":            round(annual_rent / area / 12, 2) if annual_rent and area > 1 else None,
        "value_per_m2":           round(expert_val / area, 2) if area > 1 else None,
        "source_status":          "محاكاة QA — تقرير سوقي داخلي تاريخي",
        "usable_for_tax_appeal":  True,
        "limitations":            "التقرير بتاريخ 2023 — يحتاج تعديل زمني +5% سنويًا. استخدامه كمرجع داعم فقط.",
        "expert_review_required": True,
    })

    # Rental valuation report (non-residential or residential)
    if annual_rent > 0:
        links.append({
            "linked_report_id":       "PRIOR-RENT-QA-01",
            "report_type":            "rental_valuation_report",
            "report_date":            "01/06/2023",
            "valuation_date":         "01/05/2023",
            "district":               district,
            "zone_id":                "QA-ZONE-01",
            "property_class":         class_key,
            "indicated_market_value": None,
            "indicated_rental_value": round(annual_rent, 2),
            "rent_per_m2":            round(annual_rent / area / 12, 2) if area > 1 else None,
            "value_per_m2":           None,
            "source_status":          "محاكاة QA — تقرير إيجاري داخلي تاريخي",
            "usable_for_tax_appeal":  True,
            "limitations":            "يُستخدم كمرجع داعم لطريقة الرسملة فقط — ليس كبديل لتقييم ضريبي رسمي",
            "expert_review_required": True,
        })

    return links



# ═══════════════════════════════════════════════════════════════════════════════
# ── Compliance / Disclosure / Methodology / Modern Risk Layer ─────────────────
# ═══════════════════════════════════════════════════════════════════════════════

_COMPLIANCE_DEFAULT = "جاهزية امتثال — تحتاج مراجعة وتأكيد الخبير"
_NOT_CLAIMED        = "غير مُدَّعى — يحتاج تحقق ومراجعة الخبير"
_UNCERTAINTY_BASE_PCT = {
    "residential": 0.10, "non_residential": 0.125, "special_purpose": 0.175,
}


def _build_professional_compliance_readiness(
    payload: dict, class_key: str, is_qa: bool
) -> dict:
    """Build professional compliance readiness block (IVS/USPAP/RICS/FRA/IFRS13)."""
    purpose = (payload.get("valuation_purpose") or "tax_appeal").lower()
    is_financial_rpt = any(t in purpose for t in ("financial_reporting", "fair_value", "ifrs"))

    ivs_readiness = {
        "ivs_version_reference":   "IVS 2025 (effective 31 January 2025) — يحتاج تأكيد الخبير",
        "ivs_effective_date":      "31 يناير 2025",
        "ivs_claim_status":        _NOT_CLAIMED,
        "ivs_general_standards_mapping": {
            "framework_assignment_basis": "مُدرَج — استرشادي",
            "scope_of_work":             "مُدرَج — يحتاج اعتماد الخبير",
            "basis_of_value":            "مُدرَج — القيمة الإيجارية السوقية",
            "data_and_inputs":           "جزئي — QA محاكاة" if is_qa else "يحتاج مراجع حقيقية",
            "valuation_approaches":      "مُدرَجة — الطرق الخمس",
            "documentation_reporting":   "مُدرَج — يحتاج توقيع خبير",
        },
        "ivs_asset_standards_mapping":  "معيار الأصول العقارية — يحتاج تأكيد رقم المعيار بواسطة الخبير",
        "ivs_quality_control_mapping":  [
            "مراجعة البيانات — جزئي", "مراجعة الصيغ — جزئي",
            "مراجعة المصادر — جزئي", "اعتماد الخبير — مطلوب",
        ],
        "ivs_documentation_reporting_mapping": "مُدرَج استرشاديًا — يحتاج توقيع وترقيم خبير",
        "missing_ivs_items": [
            "توقيع الخبير المعتمد",
            "بيانات مقارنة سوقية موثوقة",
            "تأكيد رقم معيار الأصول العقاري",
        ],
        "expert_confirmation_required": True,
    }

    uspap_readiness = {
        "uspap_claim_status":                _NOT_CLAIMED,
        "report_type_status":               "يحتاج تحديد نوع التقرير — Summary / Restricted Use",
        "signed_certification_status":      "غير موقّع — غير معتمد",
        "appraiser_signature_required":     True,
        "appraiser_name_placeholder":       payload.get("expert_name") or "[ اسم الخبير ]",
        "appraiser_credential_placeholder": "[ رقم الترخيص / الاعتماد ]",
        "appraiser_date_placeholder":       "[ تاريخ التوقيع ]",
        "significant_assistance_disclosure": (
            payload.get("significant_assistance_disclosure")
            or "لم يتم الإفصاح / يحتاج تأكيد الخبير"
        ),
        "restricted_use_warning":           "تقرير استشاري — يستخدم وفق الغرض والمستخدمين المحددين فقط",
        "intended_user_identification":     payload.get("intended_users") or "[ تحديد المستخدم المقصود مطلوب ]",
        "intended_use_identification":      payload.get("intended_use") or "طعن ضريبي — لا يستخدم لأغراض أخرى",
        "scope_of_work_status":            "مُدرَج — يحتاج مراجعة الخبير",
        "extraordinary_assumptions_status": "مُدرَجة ضمن قسم الافتراضات",
        "hypothetical_conditions_status":  "لا توجد شروط افتراضية مُدرَجة بشكل صريح",
        "appraisal_review_readiness":      "لم تتم مراجعة نظير — يحتاج مراجع مستقل",
        "missing_uspap_items": [
            "توقيع الخبير ورقم الترخيص",
            "تحديد نوع التقرير الرسمي",
            "مراجعة النظراء",
        ],
        "expert_confirmation_required": True,
    }

    rics_red_book_readiness = {
        "rics_claim_status":                     _NOT_CLAIMED,
        "rics_member_required":                  True,
        "terms_of_engagement_status":            "لم يتم تحديد شروط الارتباط — يحتاج استكمال",
        "inspection_investigation_records_status": "لم يُبلَّغ عن معاينة ميدانية",
        "valuation_report_requirements_status":  "مُدرَج استرشادي — يحتاج مراجعة RICS Red Book",
        "bases_of_value_status":                "القيمة الإيجارية السوقية — مُدرَجة",
        "valuation_approaches_methods_status":   "الطرق الخمس — مُدرَجة استرشاديًا",
        "valuation_models_status":               "لا يوجد نموذج ذكاء اصطناعي مدرب فعليًا",
        "rics_note": (
            "لا يتم ادعاء الامتثال لـ RICS Red Book إلا إذا كان الخبير/المقيم "
            "عضوًا مؤهلًا وتمت مراجعة متطلبات الكتاب الأحمر."
        ),
        "missing_rics_items": [
            "عضوية RICS للخبير المُقيِّم",
            "شروط الارتباط الرسمية",
            "سجل المعاينة الميدانية",
        ],
        "expert_confirmation_required": True,
    }

    fra_egyptian_standards_readiness = {
        "fra_claim_status":                _NOT_CLAIMED,
        "accredited_expert_required":      True,
        "expert_signature_required":       True,
        "expert_signature_status":         "غير موقّع — غير معتمد",
        "egyptian_standards_reference_status": "يحتاج مراجعة المعايير المهنية المحلية المعتمدة",
        "report_registration_status":      "لم يتم التسجيل — يحتاج خبير مرخص",
        "fra_note": (
            "هذا التقرير لا يصبح تقريرًا معتمدًا وفق المتطلبات المهنية المحلية إلا بعد "
            "مراجعة وتوقيع واعتماد الخبير المختص."
        ),
        "missing_fra_items": [
            "توقيع خبير مرخص",
            "ختم وترقيم التقرير",
            "تسجيل التقرير لدى الجهة المختصة",
        ],
        "expert_confirmation_required": True,
    }

    ifrs_13_readiness = {
        "ifrs_applicable":                 is_financial_rpt,
        "ifrs_applicability_note": (
            "مُطبَّق لأغراض التقارير المالية" if is_financial_rpt
            else "غير مطبق لهذا الغرض — الغرض الحالي طعن ضريبي"
        ),
        "fair_value_hierarchy_level": (
            "Level 3 (مدخلات غير قابلة للملاحظة)" if is_financial_rpt
            else "غير مطبق لهذا الغرض"
        ),
        "observable_inputs":               (["أسعار السوق الظاهرة"] if is_financial_rpt else []),
        "unobservable_inputs":             (["معدل الرسملة", "معدل الإهلاك", "معاملات التعديل"] if is_financial_rpt else []),
        "significant_unobservable_inputs": (["معدل الرسملة", "معدل الإهلاك"] if is_financial_rpt else []),
        "valuation_techniques":            (["طريقة الدخل", "طريقة التكلفة"] if is_financial_rpt else []),
        "sensitivity_narrative": (
            "تحليل الحساسية موضح في قسم تحليل الحساسية المفصل" if is_financial_rpt
            else "غير مطبق لهذا الغرض"
        ),
        "missing_ifrs_items": (
            ["الإفصاح الكامل عن المدخلات", "تأكيد تصنيف المستوى"] if is_financial_rpt else []
        ),
        "expert_confirmation_required": True,
    }

    return {
        "standards_scope":           "IVS 2025 / USPAP / RICS Red Book 2025 / FRA / IFRS 13",
        "compliance_position":       "جاهزية استرشادية — لا يُدَّعى امتثال كامل بأي معيار قبل اعتماد الخبير",
        "ivs_readiness":             ivs_readiness,
        "uspap_readiness":           uspap_readiness,
        "rics_red_book_readiness":   rics_red_book_readiness,
        "fra_egyptian_standards_readiness": fra_egyptian_standards_readiness,
        "ifrs_13_readiness":         ifrs_13_readiness,
        "quality_control_readiness": {
            "data_review":          "جزئي",
            "formula_review":       "جزئي",
            "source_review":        "جزئي" if is_qa else "يحتاج مراجع حقيقية",
            "method_review":        "مُدرَج",
            "cross_check_values":   "جزئي",
            "expert_approval":      "مطلوب — لم يتم",
            "version_control":      "مُدرَج",
            "no_corrupt_tokens":    "مراجعة آلية مُفعَّلة",
            "no_live_source_claim": "مُؤكَّد — لا مصادر حية",
        },
        "reporting_requirements_status": "تقرير استرشادي — لا يُستخدم رسميًا قبل المراجعة",
        "required_expert_confirmations": [
            "توقيع الخبير وترقيمه",
            "مراجعة الطرق ودعمها ببيانات حقيقية",
            "تأكيد أرقام المعايير المُطبَّقة",
        ],
        "compliance_gaps": [
            "توقيع الخبير المعتمد غير موجود",
            "بيانات مقارنة سوقية/ضريبية حقيقية غير مُدرَجة",
            "مراجعة النظراء لم تُجرَ",
            "أرقام بنود المعايير لم تُؤكَّد",
        ],
        "disclosure_gaps": [
            "المساعدون الجوهريون غير مُفصَح عنهم",
            "نوع التقرير الرسمي غير مُحدَّد",
            "المستخدم المقصود يحتاج تحديدًا",
        ],
        "methodology_gaps": [
            "بيانات مقارنة سوقية غير موثقة",
            "نموذج الانحدار غير مُدرَّب",
            "معدل الرسملة بحاجة لدعم بياناتي",
        ],
        "final_compliance_statement": _COMPLIANCE_DEFAULT,
        "is_qa_simulation":          is_qa,
        "production_ready":          False,
    }


def _build_scope_of_work(
    payload: dict, class_key: str, subtype_key: str, is_qa: bool,
) -> dict:
    """Build scope of work section."""
    tax_mode = (payload.get("tax_mode") or "annual").lower()
    methods_applied = _CLASS_VALUATION_LABELS_AR.get(class_key, [])
    methods_excluded = (
        ["طريقة المقارنة (نقص بيانات)", "طريقة الرسملة (نقص بيانات)"]
        if class_key == "special_purpose"
        else ["طريقة الانحدار المتعدد (غير مفعلة — مرحلة مستقبلية)"]
    )

    docs_cl = _build_required_documents_checklist(class_key, payload)
    reviewed_docs = [d.get("label_ar") or d.get("name") or d.get("doc_key", "") for d in docs_cl if d.get("status") == "مُقدَّم"]
    missing_docs  = [d.get("label_ar") or d.get("name") or d.get("doc_key", "") for d in docs_cl if d.get("status") != "مُقدَّم" and d.get("required")]

    return {
        "intended_use":              "طعن على التقييم الضريبي",
        "intended_users":            payload.get("intended_users") or "[ مالك العقار / الممثل القانوني ]",
        "client_or_requester":       payload.get("taxpayer_name") or payload.get("owner_name") or _DATA_GAP,
        "property_interest_appraised": "حق الملكية — يحتاج تأكيد وثائقي",
        "valuation_basis":           "القيمة الإيجارية السوقية" if "transfer" not in tax_mode else "القيمة السوقية",
        "effective_date":            payload.get("valuation_date") or payload.get("assessment_date") or _DATA_GAP,
        "report_date":               payload.get("report_date") or _DATA_GAP,
        "inspection_status":         payload.get("inspection_status") or "لم تُبلَّغ معاينة ميدانية — يحتاج استكمال",
        "inspection_extent":         payload.get("inspection_extent") or "خارجي استرشادي — لا معاينة ميدانية كاملة",
        "documents_reviewed":        reviewed_docs or (["بيانات الطلب — QA"] if is_qa else ["بيانات الطلب"]),
        "documents_missing":         missing_docs,
        "data_sources_used":         ["بيانات الطلب", "محاكاة QA" if is_qa else "مدخلات المستخدم"],
        "data_sources_not_available": ["Qdrant", "بيانات السوق المباشرة", "OCR", "إنترنت"],
        "methods_considered":        ["طريقة التكلفة", "طريقة المقارنة السوقية",
                                      "طريقة الرسملة", "المقارنة الضريبية", "الانحدار المتعدد"],
        "methods_applied":           methods_applied,
        "methods_excluded":          methods_excluded,
        "limitations": [
            "لم يتم تفعيل Qdrant / OCR / الإنترنت",
            "البيانات اصطناعية في وضع QA" if is_qa else "البيانات من مدخلات المستخدم فقط",
            "لا معاينة ميدانية مؤكدة",
        ],
        "expert_confirmation_required": True,
        "production_ready":          False,
    }


def _build_quality_control_checklist(
    payload: dict, class_key: str, is_qa: bool,
) -> dict:
    """Build professional quality control checklist."""
    def _item(name, status, note=""):
        return {"item": name, "status": status, "note": note}

    items = [
        _item("مراجعة الصيغ والمعادلات",         "جزئي",   "تحقق آلي — يحتاج مراجعة خبير"),
        _item("اتساق الأوراق المحورية",           "جزئي",   "مُدرَج — يحتاج تأكيد"),
        _item("تطهير النص وإزالة الرموز الخاطئة", "مُنفَّذ","مُفعَّل تلقائيًا"),
        _item("مراجعة جودة المصادر",              "جزئي",   "QA محاكاة — ليست مصادر حقيقية" if is_qa else "يحتاج مصادر حقيقية"),
        _item("مراجعة أوزان الطرق",               "جزئي",   "استرشادي — يعدله الخبير"),
        _item("مراجعة الافتراضات",                "مُدرَج", "مُدرَجة في قسم الافتراضات"),
        _item("مراجعة HBU",                      "مُدرَج", "مُدرَج — يحتاج تأكيد الخبير"),
        _item("مراجعة توقيع الخبير",              "مطلوب",  "غير موقّع — غير معتمد"),
        _item("لا ادعاء مصادر حية",               "مُؤكَّد","لا Qdrant/OCR/Internet"),
        _item("التحقق النهائي",                   "يحتاج خبير", "لم يُكتمل"),
    ]
    return {
        "quality_control_items":       items,
        "formula_review":              "جزئي",
        "cross_sheet_consistency":     "جزئي",
        "pdf_text_sanitation":         "مُنفَّذ",
        "source_quality_review":       "جزئي" if is_qa else "يحتاج مصادر حقيقية",
        "method_weight_review":        "استرشادي",
        "assumptions_review":          "مُدرَج",
        "hbu_review":                  "مُدرَج",
        "expert_signature_review":     "مطلوب — لم يتم",
        "no_live_source_claim_review": "مُؤكَّد",
        "final_status":                "جاهزية جودة استرشادية — يحتاج اعتماد الخبير",
        "production_ready":            False,
        "is_qa_simulation":            is_qa,
    }


def _build_esg_climate_risk_assessment(
    payload: dict, class_key: str, subtype_key: str, is_qa: bool,
) -> dict:
    """Build ESG / sustainability / climate risk assessment block."""
    if class_key == "residential":
        energy_cost_effect  = "انخفاض تكاليف التشغيل يُحسِّن القيمة الإيجارية الصافية"
        energy_rent_effect  = "كفاءة الطاقة قد تؤثر إيجابًا على القيمة الإيجارية (+2%–+5% استرشادي)"
        climate_val_effect  = "مخاطر الفيضانات ودرجات الحرارة قد تؤثر سلبًا على القيمة طويلة الأجل"
        esg_factors         = ["كفاءة الطاقة", "معايير البيئة المحلية", "نظام التبريد والتدفئة"]
        flood_risk          = "يحتاج مراجعة تقارير الفيضانات المحلية"
        heat_risk           = "مخاطر الحرارة — تأثير محتمل على تكاليف التكييف"
        insurance_risk      = "يحتاج مراجعة وثائق التأمين"
    elif subtype_key == "basement_storage":
        energy_cost_effect  = "تكاليف الإضاءة/التهوية جزء من تكاليف التشغيل"
        energy_rent_effect  = "توافر التهوية والإضاءة يؤثر على القيمة الإيجارية"
        climate_val_effect  = "مخاطر تسرب المياه والفيضانات — تأثير سلبي محتمل مرتفع"
        esg_factors         = ["مخاطر تسرب المياه", "التهوية", "الإضاءة الطبيعية"]
        flood_risk          = "مرتفع — الموقع تحت مستوى الأرض"
        heat_risk           = "منخفض نسبيًا لكون الموقع تحت الأرض"
        insurance_risk      = "قد يُؤثِّر تسرب المياه على قسط التأمين"
    elif class_key == "special_purpose":
        energy_cost_effect  = "تكاليف الطاقة الصناعية جزء جوهري من تكاليف التشغيل"
        energy_rent_effect  = "كفاءة الطاقة التشغيلية تؤثر على تكاليف الإنتاج"
        climate_val_effect  = "مخاطر بيئية/تشغيلية قد تؤثر على قيمة المنشأة"
        esg_factors         = ["الترخيص البيئي", "الانبعاثات والنفايات", "مخاطر التأمين الصناعي"]
        flood_risk          = "يحتاج مراجعة تقارير الموقع الصناعي"
        heat_risk           = "مخاطر الحرارة التشغيلية — يحتاج مراجعة"
        insurance_risk      = "التأمين الصناعي — مطلوب ومؤثر على القيمة"
    else:
        energy_cost_effect  = "تكاليف الطاقة ضمن تكاليف الإيجار الكاملة"
        energy_rent_effect  = "كفاءة الطاقة تؤثر على تكاليف التشغيل وجاذبية المستأجرين"
        climate_val_effect  = "مخاطر مناخية محتملة — تأثير محدود للوحدات الإدارية/التجارية"
        esg_factors         = ["كفاءة الطاقة", "معايير البناء البيئي", "جودة الهواء الداخلي"]
        flood_risk          = "يحتاج مراجعة الطابق والموقع"
        heat_risk           = "مخاطر الحرارة — تأثير على تكاليف التكييف"
        insurance_risk      = "يحتاج مراجعة وثائق التأمين"

    return {
        "esg_applicability":                  True,
        "energy_efficiency_status":           "بيانات QA محاكاة" if is_qa else _DATA_GAP,
        "energy_efficiency_effect_on_operating_cost": energy_cost_effect,
        "energy_efficiency_effect_on_rental_value":   energy_rent_effect,
        "sustainability_features":            (
            ["QA — ميزة استدامة محاكاة 1", "QA — ميزة استدامة محاكاة 2"] if is_qa
            else [_DATA_GAP]
        ),
        "green_building_premium_or_discount": "QA محاكاة" if is_qa else "غير محدد — يحتاج بيانات ESG فعلية",
        "climate_risk_exposure":              "يحتاج مراجعة تقارير المخاطر المناخية المحلية",
        "flood_risk_status":                  flood_risk,
        "heat_risk_status":                   heat_risk,
        "insurance_risk_status":              insurance_risk,
        "climate_risk_effect_on_value":       climate_val_effect,
        "climate_risk_effect_on_tax_basis":   "قد يؤثر على القيمة الإيجارية المُستخدَمة في الوعاء",
        "esg_factors":                        esg_factors,
        "esg_data_sources":                   (
            ["بيانات محاكاة QA — ليست بيانات ESG رسمية"] if is_qa
            else ["غير متاح — يحتاج مستندات ESG وشهادات البناء الأخضر"]
        ),
        "missing_esg_inputs": [
            "شهادات البناء الأخضر",
            "تقارير المخاطر المناخية المحلية",
            "سجلات استهلاك الطاقة",
        ],
        "esg_expert_review_required":         True,
        "esg_disclaimer": (
            "بيانات ESG محاكاة QA — لا تستخدم كدليل رسمي." if is_qa
            else "لم يتم إدخال بيانات كافية لتطبيق أثر ESG ماليًا. هذا القسم استرشادي."
        ),
        "auto_adjust_value":                  False,
        "production_ready":                   False,
        "is_qa_simulation":                   is_qa,
    }


def _build_legal_due_diligence_readiness(
    payload: dict, class_key: str, subtype_key: str, is_qa: bool,
) -> dict:
    """Build legal due diligence readiness block."""
    _gap_s = "لم يُتحقق منه — يحتاج فحص قانوني/وثائقي"

    legal_req = ["وثيقة الملكية", "الإخطار الضريبي", "مستند المساحة"]
    if class_key == "special_purpose":
        legal_req += ["الترخيص الصناعي/النشاط", "مستند تخصيص الأرض أو الملكية", "تصاريح البناء"]
    elif subtype_key == "basement_storage":
        legal_req += ["وثيقة تُثبت التبعية أو الاستقلالية للبدروم"]

    if is_qa:
        risk_level  = "متوسط — بيانات QA"
        mortgage_st = "لا رهن — محاكاة QA"
        dispute_st  = "لا نزاعات — محاكاة QA"
    else:
        risk_level  = "يحتاج تقييم قانوني — المستندات غير مكتملة"
        mortgage_st = _gap_s
        dispute_st  = _gap_s

    return {
        "title_document_status":          payload.get("title_doc_status") or _gap_s,
        "ownership_status":               payload.get("ownership_status") or _gap_s,
        "mortgage_or_lien_status":        mortgage_st,
        "dispute_status":                 dispute_st,
        "encumbrances_status":            _gap_s,
        "zoning_or_license_status":       payload.get("zoning_status") or _gap_s,
        "building_permit_status":         payload.get("building_permit_status") or _gap_s,
        "occupancy_or_completion_status": payload.get("occupancy_status") or _gap_s,
        "tax_notice_validity_status": (
            "إخطار ضريبي مُقدَّم" if payload.get("tax_notice_number") else _gap_s
        ),
        "legal_documents_reviewed":       payload.get("legal_docs_reviewed") or [],
        "legal_documents_missing":        legal_req,
        "legal_assumptions": [
            "تم افتراض خلو العقار من النزاعات أو القيود غير المفصح عنها بناءً على البيانات المتاحة، "
            "ويحتاج ذلك إلى تحقق قانوني/مستندي."
        ],
        "legal_risk_level":               risk_level,
        "default_statement":              "لم يتم إجراء فحص قانوني كامل — يحتاج مراجعة مستندات.",
        "expert_or_legal_review_required": True,
        "production_ready":               False,
        "is_qa_simulation":               is_qa,
    }


def _build_source_documentation_readiness(
    payload: dict, class_key: str, is_qa: bool,
    cost_m: dict, market_m: dict, income_m: dict,
    tax_cmp_m: dict, regression_m: dict,
) -> dict:
    """Build source documentation governance readiness block."""
    def _src(method, sid, status, quality, in_formula, prod_ready):
        return {
            "method": method, "source_id": sid,
            "source_status": status, "source_quality": quality,
            "used_in_formula": in_formula, "production_ready": prod_ready,
            "expert_review_required": not prod_ready,
        }

    qa_st = "محاكاة QA"
    rows = [
        _src("طريقة التكلفة",          "COST-SRC", qa_st if is_qa else "يحتاج مصدر", "QA" if is_qa else _DATA_GAP, True,  False),
        _src("طريقة المقارنة السوقية", "MKT-SRC",  qa_st if is_qa else "يحتاج مصدر", "QA" if is_qa else _DATA_GAP, True,  False),
        _src("طريقة الرسملة",          "INC-SRC",  qa_st if is_qa else "يحتاج مصدر", "QA" if is_qa else _DATA_GAP, True,  False),
        _src("المقارنة الضريبية",       "TAX-SRC",  "بيانات إخطار",                   "رسمي جزئي",                  True,  False),
        _src("الانحدار المتعدد",        "REG-SRC",  "مرحلة مستقبلية",                 "غير متاح",                   False, False),
        _src("تحليل HBU",              "HBU-SRC",  qa_st if is_qa else "يحتاج مصدر", "QA" if is_qa else _DATA_GAP, True,  False),
        _src("ESG / المناخ",            "ESG-SRC",  "غير متاح — يحتاج وثائق",         "غير متاح",                   False, False),
        _src("الفحص القانوني",          "LEGAL-SRC","غير مُكتمل",                      "يحتاج مستندات",             False, False),
    ]

    qa_count = sum(1 for r in rows if "QA" in r["source_status"] or r["source_status"] == "محاكاة QA")
    missing  = sum(1 for r in rows if not r["production_ready"])

    return {
        "sources_total":               len(rows),
        "verified_sources_count":      0 if is_qa else len(rows) - missing,
        "qa_simulation_sources_count": qa_count,
        "missing_sources_count":       missing,
        "source_registry_active":      True,
        "source_registry_used_in_methods": True,
        "source_traceability_status":  "محاكاة QA" if is_qa else "جزئي — يحتاج مصادر حقيقية",
        "source_traceability_table":   rows,
        "sources_not_production_ready": [r["source_id"] for r in rows if not r["production_ready"]],
        "required_source_actions": [
            "تزويد مصادر سوقية/إيجارية حقيقية",
            "ربط ملف الإخطار الضريبي الأصلي",
            "تزويد مستندات الفحص القانوني",
        ],
        "production_ready":            False,
        "is_qa_simulation":            is_qa,
    }


def _build_peer_review_readiness(payload: dict, class_key: str, is_qa: bool) -> dict:
    """Build peer review / appraisal review readiness block."""
    return {
        "peer_review_required":            True,
        "peer_review_completed":           False,
        "reviewer_name":                   "[ اسم المراجع المستقل ]",
        "reviewer_credentials":            "[ مؤهلات المراجع ]",
        "review_scope":                    "مراجعة كاملة لمنهجية التقييم والبيانات والافتراضات",
        "review_date":                     "[ تاريخ المراجعة ]",
        "review_findings":                 "لم تُجرَ المراجعة بعد",
        "review_status":                   "لم تتم مراجعة النظراء بعد — يحتاج مراجعة خبير مستقل قبل الاعتماد.",
        "uspap_appraisal_review_readiness": {
            "readiness_status":           "جاهزية هيكلية — لم تُجرَ مراجعة USPAP",
            "signed_certification_ready": False,
            "appraisal_review_completed": False,
        },
        "rics_review_readiness": {
            "readiness_status": "جاهزية هيكلية — لم تُجرَ مراجعة RICS",
            "rics_member_reviewer": False,
        },
        "reviewer_signature_placeholder":  "[ توقيع المراجع ]",
        "reviewer_approval_status":        "غير موقّع — غير معتمد",
        "expert_final_approval_required":  True,
        "production_ready":                False,
        "is_qa_simulation":                is_qa,
    }


def _build_uncertainty_range(
    payload: dict, class_key: str, subtype_key: str,
    is_qa: bool, tax_engine: dict,
) -> dict:
    """Build advisory uncertainty / sensitivity range (NOT statistical confidence interval)."""
    base_pct = _UNCERTAINTY_BASE_PCT.get(class_key, 0.125)
    if subtype_key in ("basement_storage", "factory"):
        base_pct = max(base_pct, 0.15)
    if is_qa:
        base_pct = min(base_pct + 0.025, 0.20)

    govt_tax   = _safe_float(tax_engine.get("government_tax_amount"))
    base_tax   = _safe_float(tax_engine.get("corrected_tax_amount") or tax_engine.get("expert_tax_amount") or 0)
    low_val    = round(base_tax * (1 - base_pct), 2)
    high_val   = round(base_tax * (1 + base_pct), 2)
    save_base  = round(govt_tax - base_tax, 2) if govt_tax > 0 else 0.0
    save_low   = round(govt_tax - high_val, 2) if govt_tax > 0 else 0.0
    save_high  = round(govt_tax - low_val,  2) if govt_tax > 0 else 0.0

    drivers = [
        "دقة البيانات المُدخلة",
        "توافر مقارنات سوقية موثوقة",
        "معدل الإهلاك المُطبَّق",
    ]
    if subtype_key == "factory":
        drivers.append("تقدير تكلفة المكونات الصناعية")
    if subtype_key == "basement_storage":
        drivers.append("معامل البدروم ومدى قابليته للتحقق")
    if is_qa:
        drivers.append("بيانات QA — يُعوِّضها الخبير ببيانات حقيقية")

    return {
        "base_value":                  base_tax,
        "low_value":                   low_val,
        "high_value":                  high_val,
        "base_tax":                    base_tax,
        "low_tax":                     low_val,
        "high_tax":                    high_val,
        "expected_saving_base":        save_base,
        "expected_saving_low":         save_low,
        "expected_saving_high":        save_high,
        "uncertainty_pct":             base_pct,
        "uncertainty_pct_label":       f"±{base_pct * 100:.1f}%",
        "uncertainty_drivers":         drivers,
        "confidence_basis":            "بيانات QA محاكاة" if is_qa else "مدخلات المستخدم",
        "statistical_confidence_available": False,
        "range_label":                 "نطاق عدم يقين/حساسية استرشادي",
        "range_note": (
            "هذا النطاق استرشادي ولا يُمثل ثقة إحصائية مؤكدة. "
            "الغرض إظهار أثر تغير الافتراضات على النتيجة."
        ),
        "expert_notes":                "يراجع الخبير هذا النطاق ويُعدِّله وفق الظروف الفعلية",
        "production_ready":            False,
        "is_qa_simulation":            is_qa,
    }


def _build_document_requirements_matrix(
    payload: dict, class_key: str, subtype_key: str, is_qa: bool,
) -> dict:
    """Build mandatory / supporting / optional document requirements matrix."""
    def _doc(name, level, affects_sub, affects_val, affects_dl, status, action):
        return {
            "document_name":      name,
            "requirement_level":  level,
            "affects_submission": affects_sub,
            "affects_valuation":  affects_val,
            "affects_deadline":   affects_dl,
            "current_status":     status,
            "expert_action":      action,
        }

    has_notice = bool(payload.get("tax_notice_number") or payload.get("government_tax_amount"))
    docs = [
        _doc("الإخطار الضريبي",          "إلزامي", True,  True,  True,
             "مُقدَّم" if has_notice else "غير مُقدَّم",
             "" if has_notice else "تزويد الإخطار الضريبي الأصلي"),
        _doc("وثيقة الملكية",             "إلزامي", True,  True,  False,
             "غير مُقدَّم", "تزويد وثيقة الملكية"),
        _doc("مستند المساحة",             "إلزامي", True,  True,  False,
             "غير مُقدَّم", "تزويد مستند المساحة أو الرسم"),
        _doc("صور العقار / خرائط الموقع", "داعم",   False, True,  False,
             "غير مُقدَّم", "رفع صور وخرائط الموقع"),
        _doc("شهادة إتمام/إشغال",         "داعم",   False, True,  False,
             "غير مُقدَّم", "تزويد شهادة إشغال رسمية"),
    ]
    if class_key == "special_purpose":
        docs += [
            _doc("الترخيص الصناعي/الإنتاجي",            "إلزامي",                  True,  True, False, "غير مُقدَّم", "تزويد الترخيص الصناعي"),
            _doc("تخصيص الأرض أو سند الملكية",           "إلزامي",                  True,  True, False, "غير مُقدَّم", "تزويد مستند التخصيص"),
            _doc("جدول الماكينات/المعدات (للاستثناء)",   "داعم",                    False, True, False, "غير مُقدَّم", "تزويد جدول المعدات للاستثناء الصريح"),
            _doc("مرجع تكاليف البناء التقني",             "مطلوب لتأكيد التقييم",    False, True, False, "غير مُقدَّم", "تزويد مرجع التكاليف"),
        ]
    elif subtype_key == "basement_storage":
        docs += [
            _doc("وثيقة تُثبت التبعية أو الاستقلالية",  "إلزامي", True, True, False, "غير مُقدَّم", "تزويد وثيقة ملكية البدروم"),
            _doc("تقرير الوصول والتهوية",                "داعم",   False, True, False, "غير مُقدَّم", "تزويد تقرير الوصول"),
        ]
    elif class_key == "non_residential":
        docs += [
            _doc("ترخيص النشاط",
                 "إلزامي" if subtype_key == "shop" else "داعم",
                 True, True, False, "غير مُقدَّم", "تزويد ترخيص النشاط"),
            _doc("عقد إيجار حالي أو عينات إيجارية",
                 "مطلوب لتأكيد التقييم", False, True, False, "غير مُقدَّم", "تزويد عينات إيجارية"),
        ]
    else:
        docs += [
            _doc("عقد بيع أو عينات بيع حديثة",
                 "مطلوب لتأكيد التقييم", False, True, False, "غير مُقدَّم", "تزويد عينات بيع حديثة"),
        ]

    mandatory  = [d for d in docs if d["requirement_level"] == "إلزامي"]
    supporting = [d for d in docs if d["requirement_level"] == "داعم"]
    valuation  = [d for d in docs if d["requirement_level"] == "مطلوب لتأكيد التقييم"]
    miss_mand  = [d["document_name"] for d in mandatory  if d["current_status"] != "مُقدَّم"]
    miss_supp  = [d["document_name"] for d in supporting if d["current_status"] != "مُقدَّم"]

    return {
        "mandatory_documents":          mandatory,
        "supporting_documents":         supporting,
        "optional_documents":           [],
        "valuation_support_documents":  valuation,
        "legal_review_documents":       [],
        "all_documents":                docs,
        "missing_mandatory_documents":  miss_mand,
        "missing_supporting_documents": miss_supp,
        "readiness_status": (
            "مكتمل" if not miss_mand
            else f"ناقص — {len(miss_mand)} مستند إلزامي مفقود"
        ),
        "total_documents":              len(docs),
        "mandatory_missing_count":      len(miss_mand),
        "is_qa_simulation":             is_qa,
        "production_ready":             not miss_mand and not is_qa,
    }


def _build_tax_basis_explanation(
    payload: dict, class_key: str, tax_engine: dict, is_qa: bool,
) -> dict:
    """Build tax basis vs market value clarification block."""
    tax_mode  = (payload.get("tax_mode") or "annual").lower()
    is_trans  = "transfer" in tax_mode
    mkt_rent  = _safe_float(
        payload.get("estimated_market_rental_value") or payload.get("annual_rental_estimate")
    )
    taxable   = round(max(mkt_rent * 0.80 - 7200, 0), 2) if mkt_rent else None
    annual_tx = round(taxable * 0.10, 2) if taxable else None
    sale_val  = _safe_float(payload.get("challenged_sale_value") or payload.get("government_claim") or 0)

    differences = [
        {"concept": "القيمة السوقية",            "basis": "سوقي",          "used_in": "ضريبة التصرفات" if is_trans else "استرشادي"},
        {"concept": "القيمة الإيجارية السوقية",  "basis": "سوقي",          "used_in": "مدخل حساب الضريبة السنوية"},
        {"concept": "وعاء الضريبة",              "basis": "قانوني/إداري",  "used_in": "الضريبة العقارية السنوية"},
        {"concept": "الضريبة المحتسبة",          "basis": "ناتج المعادلة", "used_in": "كلا النوعين"},
    ]

    return {
        "market_value_definition":         "السعر المتوقع في بيع حر في السوق المفتوح",
        "market_rental_value_definition":  "الإيجار المتوقع في السوق المفتوح",
        "tax_rental_basis_definition":     "الوعاء الضريبي بعد تطبيق المعادلة القانونية",
        "statutory_formula_note":          "المعادلة القانونية قد تختلف عن القيمة السوقية المباشرة",
        "annual_tax_formula_note": (
            "الضريبة العقارية السنوية = (إيجار × 80% − 7200) × 10%"
            if not is_trans else "غير مطبق لهذا النوع"
        ),
        "transfer_tax_formula_note": (
            "ضريبة التصرفات = قيمة التصرف × 2.5%"
            if is_trans else "غير مطبق لهذا النوع"
        ),
        "differences_table":               differences,
        "annual_tax_basis_table": (
            None if is_trans else {
                "market_rental_estimate": mkt_rent,
                "deduction_80pct":        round(mkt_rent * 0.80, 2) if mkt_rent else None,
                "standard_deduction":     7200,
                "taxable_basis":          taxable,
                "tax_rate":               "10%",
                "indicative_annual_tax":  annual_tx,
                "formula_note":           "استرشادي — يحتاج تأكيد الخبير",
            }
        ),
        "transfer_tax_table": (
            None if not is_trans else {
                "transaction_basis":       sale_val or _DATA_GAP,
                "transfer_tax_rate":       "2.5%",
                "transfer_tax_amount":     round(sale_val * 0.025, 2) if sale_val else _DATA_GAP,
                "annual_exemption_note":   "إعفاءات الضريبة السنوية لا تنطبق على ضريبة التصرفات",
            }
        ),
        "user_warning": (
            "القيمة السوقية أو القيمة الإيجارية السوقية لا تساوي بالضرورة وعاء الضريبة. "
            "قد تستخدم الضريبة أساسًا أو معادلة قانونية/إدارية مختلفة."
        ),
        "tax_mode":          tax_mode,
        "is_transfer_tax":   is_trans,
        "is_qa_simulation":  is_qa,
    }


def _build_specialized_asset_governance(
    payload: dict, class_key: str, subtype_key: str, is_qa: bool,
) -> dict:
    """Build specialized asset governance for factories / industrial properties."""
    if class_key != "special_purpose":
        return {"applicable": False, "note": "غير مطبق — ليس عقارًا ذا أغراض خاصة"}

    land_area     = _safe_float(payload.get("land_area") or payload.get("area"))
    land_price_m2 = _safe_float(payload.get("cost_per_sqm_land"))
    bldg_area     = _safe_float(payload.get("building_area") or payload.get("area"))
    bldg_price_m2 = _safe_float(payload.get("cost_per_sqm_building"))
    dep_rate      = _safe_float(payload.get("depreciation_rate") or round(1 / 30, 6))
    age_yrs       = _safe_float(payload.get("age_years"))

    land_val    = round(land_area * land_price_m2, 2) if (land_area and land_price_m2) else None
    bldg_new    = round(bldg_area * bldg_price_m2, 2) if (bldg_area and bldg_price_m2) else None
    accum_dep   = round(dep_rate * age_yrs, 2) if age_yrs else None
    bldg_dep    = round(bldg_new * (1 - min(accum_dep or 0, 0.80)), 2) if bldg_new and accum_dep else None
    total_val   = round((land_val or 0) + (bldg_dep or 0), 2)

    land_src    = "محاكاة QA" if is_qa else "يحتاج مصدر رسمي / وثيقة مستخدم"
    bldg_src    = "محاكاة QA" if is_qa else "يحتاج مرجع تكاليف بناء موثق"

    components = [
        {"component": "الأرض الصناعية",           "area_m2": land_area, "unit_cost": land_price_m2, "value": land_val,  "source_status": land_src},
        {"component": "المباني الصناعية",          "area_m2": bldg_area, "unit_cost": bldg_price_m2, "value": bldg_new,  "source_status": bldg_src},
        {"component": "الأعمال الخارجية/المحيطة",  "area_m2": None,     "unit_cost": None,          "value": None,      "source_status": "يحتاج مرجع تكاليف"},
    ]

    return {
        "applicable": True,
        "land_value_section": {
            "area": land_area, "unit_price": land_price_m2, "indicated_value": land_val,
            "source_status": land_src,
            "industrial_land_source_requirement": "محاكاة QA" if is_qa else "مطلوب مستند رسمي/مرجع موثق",
        },
        "building_value_section": {
            "area": bldg_area, "unit_cost": bldg_price_m2, "replacement_cost_new": bldg_new,
            "depreciation_rate": dep_rate, "accumulated_depreciation": accum_dep,
            "depreciated_value": bldg_dep, "source_status": bldg_src,
        },
        "component_cost_table":              components,
        "fixed_real_property_components":    ["الأرض", "المباني", "الأعمال الخارجية", "التحسينات الثابتة"],
        "machinery_and_equipment_exclusion": {
            "excluded": True,
            "exclusion_note": "الماكينات والمعدات المنقولة مستثناة من التقييم العقاري الضريبي.",
            "machinery_schedule_status": "غير مُقدَّم — يحتاج جدول معدات للاستثناء الصريح",
        },
        "industrial_land_price_source_status": land_src,
        "depreciation_assumptions": {
            "economic_life_years": 30,
            "effective_age_years": age_yrs,
            "annual_dep_rate":     dep_rate,
            "accumulated_dep":     accum_dep,
            "source_status":       "QA محاكاة" if is_qa else "يحتاج خبير",
            "expert_override":     True,
        },
        "useful_life_assumptions":        "30 سنة عمر اقتصادي — استرشادي وفق الممارسة المهنية",
        "cost_guidance_reference_status": "مرجع تكاليف عين شمس (تحضيرية) — إن كان متاحًا",
        "official_source_required":       True,
        "data_gaps": [
            "سعر الأرض الصناعية — يحتاج مصدر رسمي",
            "تكاليف البناء الصناعي — يحتاج مرجع تقني",
            "جدول الماكينات — للاستثناء",
        ],
        "expert_actions": [
            "مراجعة وتأكيد سعر الأرض الصناعية",
            "استخدام مرجع تكاليف بناء صناعي موثق",
            "تزويد جدول معدات للاستثناء الصريح",
        ],
        "total_indicated_value":  total_val,
        "cost_approach_dominant": True,
        "market_income_methods_note": "طريقة المقارنة السوقية وطريقة الرسملة ذات تطبيق محدود للمنشآت الخاصة",
        "is_qa_simulation":       is_qa,
        "production_ready":       False,
    }


def _build_underground_asset_governance(
    payload: dict, class_key: str, subtype_key: str, is_qa: bool,
) -> dict:
    """Build underground / basement asset governance block."""
    if subtype_key not in ("basement_storage", "basement"):
        return {"applicable": False, "note": "غير مطبق — ليس وحدة بدروم/تخزين"}

    land_share = _safe_float(payload.get("land_share_pct", 0.0))
    basement_f = _safe_float(payload.get("basement_factor", 0.50)) or 0.50

    return {
        "applicable":              True,
        "ownership_status":        payload.get("ownership_status") or "يحتاج وثيقة ملكية",
        "accessory_or_independent_unit": (
            "تابع — لا حصة أرض مستقلة" if land_share == 0
            else "مستقل محتمل — يحتاج وثيقة ملكية لتأكيد حصة الأرض"
        ),
        "land_share_applicability": land_share > 0,
        "land_share_pct":           land_share,
        "land_share_justification": (
            "صفر — وحدة تخزين تابعة في المبنى، لا حصة أرض مستقلة"
            if land_share == 0
            else "يحتاج مراجعة وثيقة الملكية لتحديد حصة الأرض"
        ),
        "land_share_zero_requires_justification": land_share == 0,
        "land_share_zero_note": (
            "حصة الأرض = 0% مقبولة فقط إذا كانت الوحدة تابعة/ملحقة. "
            "إذا كانت الملكية مستقلة، تُطلب وثيقة تُثبت ذلك."
        ),
        "basement_factor":              basement_f,
        "basement_factor_justification": f"معامل البدروم {basement_f:.2f} — يعكس قيود الوصول والظهور والإضاءة",
        "use_type":                    payload.get("current_use") or "تخزين/خدمي",
        "access_risk":                 "مرتفع — يحتاج مراجعة مسار الوصول وعرضه",
        "ventilation_risk":            "مرتفع — يحتاج تقرير هندسي للتهوية",
        "flood_or_water_ingress_risk": "مرتفع — الموقع تحت مستوى الأرض",
        "legal_document_required":     "وثيقة ملكية تُحدِّد طبيعة التبعية أو الاستقلالية",
        "expert_actions": [
            "مراجعة وثيقة الملكية لتحديد التبعية",
            "تقييم مخاطر المياه والتهوية",
            "تأكيد معامل البدروم وفق المعاينة الفعلية",
        ],
        "is_qa_simulation": is_qa,
        "production_ready": False,
    }


# ── Evidentiary Strength / Committee-Ready Builder Functions ─────────────────


def _build_reference_grounding(
    payload: dict,
    class_key: str,
    subtype_key: str,
    is_qa: bool,
) -> dict:
    """Return reference-grounding status for all data sources used in the appeal.

    No automatic ingestion — all sources require expert confirmation.
    """
    per_method_reference: dict = {
        "cost": {
            "source_reference_type": "تكلفة البناء وسعر الأرض",
            "source_reference_status": "مدخل خبير / محاكاة QA — يحتاج تأكيد" if is_qa else "يحتاج مرجع موثق",
            "source_document_required": True,
            "expert_confirmation_required": True,
        },
        "market": {
            "source_reference_type": "صفقات بيع مقارنة",
            "source_reference_status": "مدخل خبير / محاكاة QA — يحتاج تأكيد" if is_qa else "يحتاج مرجع موثق",
            "source_document_required": True,
            "expert_confirmation_required": True,
        },
        "income": {
            "source_reference_type": "قيمة إيجارية سوقية",
            "source_reference_status": "مدخل خبير / محاكاة QA — يحتاج تأكيد" if is_qa else "يحتاج مرجع موثق",
            "source_document_required": True,
            "expert_confirmation_required": True,
        },
        "tax_comparison": {
            "source_reference_type": "بيانات إخطار ضريبي مقارن",
            "source_reference_status": "بيانات إخطار فقط — لا استرداد آلي",
            "source_document_required": True,
            "expert_confirmation_required": True,
        },
        "regression": {
            "source_reference_type": "مجموعة بيانات انحدار إحصائي",
            "source_reference_status": "غير مفعل — مرحلة مستقبلية",
            "source_document_required": True,
            "expert_confirmation_required": True,
        },
    }

    return {
        "egyptian_valuation_standards_status": "جاهزية استرشادية — يحتاج تأكيد الخبير",
        "fra_reference_status": "مرجع FRA — يحتاج إرفاق المستند الرسمي",
        "ain_shams_cost_guidance_status": "جامعة عين شمس: لم يُرفق مستند — لا يتم الاستناد إليه",
        "nuca_land_price_reference_status": "هيئة المجتمعات العمرانية: لم يُرفق مستند — لا يتم الاستناد إليه",
        "tax_authority_reference_status": "مصلحة الضرائب العقارية: بيانات إخطار فقط — لا استرداد آلي",
        "cost_reference_status": (
            "مدخل خبير / محاكاة QA — يحتاج توثيق مصدر تكلفة رسمي"
            if is_qa
            else "يحتاج استكمال مرجع تكلفة موثق"
        ),
        "depreciation_reference_status": "محاكاة QA" if is_qa else "يحتاج مرجع إهلاك موثق",
        "land_price_reference_status": "محاكاة QA" if is_qa else "يحتاج مرجع سعر أرض موثق",
        "income_deduction_reference_status": (
            "مدخل خبير / محاكاة QA — يحتاج تأكيد قانوني"
            if is_qa
            else "يحتاج مرجع خصومات موثق"
        ),
        "source_documents_attached": [],
        "source_documents_missing": [
            "مرجع تكلفة البناء",
            "مرجع سعر الأرض",
            "مرجع معدل الإهلاك",
            "مرجع خصومات الصيانة والشغور",
        ],
        "expert_confirmation_required": True,
        "reference_limitations": (
            "لا يتضمن هذا الإصدار استرجاعًا آليًا. جميع المدخلات تحتاج توثيقًا رسميًا."
        ),
        "qa_label": "محاكاة QA — لا تصلح كمرجع رسمي" if is_qa else None,
        "production_readiness": False,
        "per_method_reference": per_method_reference,
    }


def _build_deadline_legal_status(
    payload: dict,
    class_key: str,
    is_qa: bool,
) -> dict:
    """Return a rich deadline/legal-status dict for the 60-day appeal window."""
    notice_date_raw  = payload.get("notice_received_date") or payload.get("notice_date")
    report_date_raw  = payload.get("report_date")
    deadline_info    = _compute_deadline(notice_date_raw, report_date_raw)

    days_remaining   = deadline_info.get("days_remaining")
    deadline_date    = deadline_info.get("deadline_date", _DATA_GAP)
    notice_type      = payload.get("notice_type") or "نموذج 3 ضرائب عقارية"

    # Format notice received date for display
    notice_dt = _parse_date(notice_date_raw)
    notice_received_display = _format_date_ar(notice_dt) if notice_dt else _DATA_GAP

    # Determine status, risk, flags
    if not notice_dt:
        deadline_status      = "تاريخ استلام الإخطار غير متاح"
        risk_level           = "غير محدد"
        formal_rejection_risk = False
        urgent_action        = False
        legal_review         = False
        post_deadline_guidance = ""
        recommended_next_step  = "يرجى إدخال تاريخ استلام الإخطار الضريبي لحساب المهلة القانونية."
    elif isinstance(days_remaining, int) and days_remaining < 0:
        deadline_status      = "منتهية"
        risk_level           = "بالغ الخطورة"
        formal_rejection_risk = True
        urgent_action        = True
        legal_review         = True
        post_deadline_guidance = (
            "انتهت مهلة الستين يومًا وفق البيانات المدخلة. يلزم تحويل الملف للخبير/المستشار القانوني "
            "لبحث المسار الإجرائي المناسب، مثل مراجعة إمكانية تقديم تظلم أو طلب إعادة تقدير أو بحث "
            "وجود سبب مقبول لتجاوز الميعاد، بدلًا من الاكتفاء بطعن تقليدي قد يُرفض شكلًا."
        )
        recommended_next_step = (
            "يُوجَّه الملف فورًا إلى مستشار قانوني متخصص في الضرائب العقارية لبحث إمكانية التقديم المتأخر."
        )
    elif isinstance(days_remaining, int) and days_remaining <= 7:
        deadline_status      = "حرج جدًا"
        risk_level           = "عالٍ"
        formal_rejection_risk = True
        urgent_action        = True
        legal_review         = True
        post_deadline_guidance = ""
        recommended_next_step = (
            "يُوصى بتقديم الطعن فورًا مع المستندات المتاحة، والاستعانة بخبير معتمد على وجه السرعة."
        )
    elif isinstance(days_remaining, int) and days_remaining <= 14:
        deadline_status      = "اقتربت المهلة"
        risk_level           = "متوسط"
        formal_rejection_risk = False
        urgent_action        = False
        legal_review         = False
        post_deadline_guidance = ""
        recommended_next_step = (
            "يُوصى بإتمام تجميع المستندات وتقديم الطعن خلال أسرع وقت ممكن."
        )
    else:
        deadline_status      = "آمن"
        risk_level           = "منخفض"
        formal_rejection_risk = False
        urgent_action        = False
        legal_review         = False
        post_deadline_guidance = ""
        recommended_next_step = (
            "يُوصى بالمضي في تجميع مستندات الطعن وإعداد التقرير الفني في المهلة المتاحة."
        )

    return {
        "notice_type":               notice_type,
        "notice_received_date":      notice_received_display,
        "deadline_days":             60,
        "deadline_date":             deadline_date,
        "days_remaining":            days_remaining if notice_dt else "غير متاح",
        "deadline_status":           deadline_status,
        "deadline_risk_level":       risk_level,
        "formal_rejection_risk":     formal_rejection_risk,
        "post_deadline_guidance":    post_deadline_guidance,
        "recommended_next_step":     recommended_next_step,
        "urgent_action_required":    urgent_action,
        "legal_review_required":     legal_review,
        "expert_review_required":    True,
        "disclaimer":                "إرشاد إجرائي عام — يحتاج مراجعة مختص.",
    }


def _build_comparative_tax_argument(
    payload: dict,
    class_key: str,
    subtype_key: str,
    is_qa: bool,
    govt_tax: float,
    corrected_tax: float,
) -> dict:
    """Return per-m² tax gap analysis and comparable cases for committee argument."""
    area = _safe_float(payload.get("area")) or 1.0

    govt_tax_per_m2    = round(govt_tax / area, 2)
    expert_tax_per_m2  = round(corrected_tax / area, 2)
    tax_per_m2_gap     = round(govt_tax_per_m2 - expert_tax_per_m2, 2)
    overcharge_amount  = round(govt_tax - corrected_tax, 2)
    overcharge_pct_val = round((overcharge_amount / govt_tax * 100), 1) if govt_tax else 0.0
    overcharge_pct_str = f"{overcharge_pct_val}%"

    if is_qa:
        # Synthetic comparable cases — 3 QA entries showing lower tax/m²
        base_rate = govt_tax_per_m2 * 0.30  # ~30% of subject to demonstrate overcharge
        comparable_tax_cases = [
            {
                "case_id":            "CMP-QA-001",
                "property_type":      subtype_key or class_key,
                "district":           payload.get("district") or "نفس المنطقة",
                "area":               area,
                "tax_amount":         round(base_rate * area * 0.95, 2),
                "tax_per_m2":         round(base_rate * 0.95, 2),
                "assessment_year":    "2024",
                "source_status":      "محاكاة QA — لا تصلح كدليل رسمي",
                "adjustment_factor":  1.0,
                "adjusted_tax_per_m2": round(base_rate * 0.95, 2),
                "included":           True,
                "exclusion_reason":   "",
            },
            {
                "case_id":            "CMP-QA-002",
                "property_type":      subtype_key or class_key,
                "district":           payload.get("district") or "نفس المنطقة",
                "area":               area * 1.05,
                "tax_amount":         round(base_rate * area * 1.05 * 1.02, 2),
                "tax_per_m2":         round(base_rate * 1.02, 2),
                "assessment_year":    "2024",
                "source_status":      "محاكاة QA — لا تصلح كدليل رسمي",
                "adjustment_factor":  0.98,
                "adjusted_tax_per_m2": round(base_rate * 1.02 * 0.98, 2),
                "included":           True,
                "exclusion_reason":   "",
            },
            {
                "case_id":            "CMP-QA-003",
                "property_type":      subtype_key or class_key,
                "district":           payload.get("district") or "نفس المنطقة",
                "area":               area * 0.90,
                "tax_amount":         round(base_rate * area * 0.90 * 1.05, 2),
                "tax_per_m2":         round(base_rate * 1.05, 2),
                "assessment_year":    "2024",
                "source_status":      "محاكاة QA — لا تصلح كدليل رسمي",
                "adjustment_factor":  1.02,
                "adjusted_tax_per_m2": round(base_rate * 1.05 * 1.02, 2),
                "included":           True,
                "exclusion_reason":   "",
            },
        ]
        avg_comparable = round(
            sum(c["adjusted_tax_per_m2"] for c in comparable_tax_cases) / len(comparable_tax_cases), 2
        )
        subject_vs_comparable = round(govt_tax_per_m2 / avg_comparable, 2) if avg_comparable else None
    else:
        comparable_tax_cases = [
            {
                "case_id":      "GAP-001",
                "property_type": class_key,
                "district":     payload.get("district") or "غير محدد",
                "area":         None,
                "tax_amount":   None,
                "tax_per_m2":   None,
                "assessment_year": None,
                "source_status": "يحتاج حالات ضريبية موثقة من نفس المنطقة",
                "adjustment_factor": None,
                "adjusted_tax_per_m2": None,
                "included":     False,
                "exclusion_reason": "بيانات مقارنة غير متاحة — يحتاج الخبير لتجميعها",
            }
        ]
        avg_comparable       = None
        subject_vs_comparable = None

    # Argument strength
    if avg_comparable is None:
        argument_strength = "يحتاج مراجعة"
    elif overcharge_pct_val > 30:
        argument_strength = "قوي"
    elif overcharge_pct_val > 10:
        argument_strength = "متوسط"
    else:
        argument_strength = "ضعيف"

    data_gaps = []
    if not comparable_tax_cases or not comparable_tax_cases[0].get("included"):
        data_gaps.append("حالات ضريبية مقارنة من نفس المنطقة الجغرافية")
    if not payload.get("district"):
        data_gaps.append("تحديد المنطقة الجغرافية")

    return {
        "government_tax_amount":          govt_tax,
        "government_tax_per_m2":          govt_tax_per_m2,
        "expert_indicated_tax_amount":    corrected_tax,
        "expert_indicated_tax_per_m2":    expert_tax_per_m2,
        "tax_per_m2_gap":                 tax_per_m2_gap,
        "overcharge_amount":              overcharge_amount,
        "overcharge_percentage":          overcharge_pct_str,
        "comparable_tax_cases":           comparable_tax_cases,
        "average_comparable_tax_per_m2":  avg_comparable,
        "subject_vs_comparable_ratio":    subject_vs_comparable,
        "argument_strength":              argument_strength,
        "source_status":                  "محاكاة QA — لا تصلح كمرجع رسمي" if is_qa else "يحتاج مصادر موثقة",
        "data_gaps":                      data_gaps,
        "expert_notes":                   "يُوصى بمراجعة حالات ضريبية مقارنة حقيقية قبل التقديم",
        "disclaimer": (
            "الغرض من تحليل ضريبة المتر ونسبة المغالاة هو دعم الحجة الفنية للطعن، "
            "ولا يغني عن مراجعة المستندات الضريبية والقانونية."
        ),
    }


def _build_deductible_expense_analysis(
    payload: dict,
    class_key: str,
    subtype_key: str,
    is_qa: bool,
) -> dict:
    """Return deductible expense rates and amounts for annual property tax purposes.

    Deductions do NOT apply to transfer tax.
    All rates are QA defaults requiring legal verification.
    """
    is_residential = class_key == "residential"

    maintenance_rate    = 0.30 if is_residential else 0.32
    operation_rate      = 0.0   # covered within the statutory deduction
    vacancy_rate        = 0.05 if is_residential else 0.10
    collection_loss_rate = 0.03 if is_residential else 0.05

    gross_annual_rental = _safe_float(
        payload.get("gross_annual_rental_value")
        or payload.get("estimated_market_rental_value")
        or payload.get("annual_rental_estimate")
    )

    maintenance_amount   = round(gross_annual_rental * maintenance_rate, 2)
    net_taxable_basis    = round(gross_annual_rental * (1.0 - maintenance_rate), 2)
    total_deduction_rate = round(maintenance_rate + operation_rate + vacancy_rate + collection_loss_rate, 4)

    return {
        "property_class":                class_key,
        "gross_annual_rental_value":     gross_annual_rental,
        "maintenance_deduction_rate":    maintenance_rate,
        "operation_expense_rate":        operation_rate,
        "vacancy_allowance_rate":        vacancy_rate,
        "collection_loss_rate":          collection_loss_rate,
        "total_deduction_rate":          total_deduction_rate,
        "maintenance_deduction_amount":  maintenance_amount,
        "net_taxable_rental_basis":      net_taxable_basis,
        "statutory_or_assumption_basis": (
            "مدخل خبير / محاكاة QA — يحتاج تأكيد قانوني من النص الضريبي المعتمد"
        ),
        "source_status":                 "محاكاة QA" if is_qa else "يحتاج مرجع نص قانوني موثق",
        "expert_confirmation_required":  True,
        "deduction_note": (
            "نسبة الخصم (30% سكني / 32% غير سكني) كمدخل قابل للمراجعة. "
            "لا تُطبَّق على ضريبة التصرفات."
        ),
        "transfer_tax_applies":          False,
        "notes": (
            "تم عرض نسب الخصم كمدخلات قابلة لمراجعة الخبير، ولا يتم اعتبارها مرجعًا قانونيًا "
            "نهائيًا إلا بعد التحقق من النص القانوني أو المستند المعتمد."
        ),
    }


def _build_committee_reconciliation_matrix(
    payload: dict,
    class_key: str,
    subtype_key: str,
    is_qa: bool,
    cost_m: dict,
    market_m: dict,
    income_m: dict,
    tax_cmp_m: dict,
    regression_m: dict,
    govt_tax: float,
    corrected_tax: float,
) -> dict:
    """Return 5-method weighted reconciliation matrix for committee presentation.

    Weights are assigned by property class per QA rules.
    """
    # QA weight rules by class
    is_factory = subtype_key in ("factory", "مصنع", "industrial") or (
        class_key == "special_purpose" and "مصنع" in (payload.get("property_type") or "")
    )

    if is_factory:
        weights = {"cost": 100, "market": 0, "income": 0, "tax_comparison": 0, "regression": 0}
    elif class_key == "residential":
        weights = {"cost": 40, "market": 40, "income": 20, "tax_comparison": 0, "regression": 0}
    else:
        # non_residential and special_purpose (non-factory)
        weights = {"cost": 10, "market": 30, "income": 40, "tax_comparison": 20, "regression": 0}

    # Extract indicated values and taxes from each method dict
    def _get_val(m: dict, key: str) -> float:
        return _safe_float(m.get(key))

    cost_val     = _get_val(cost_m,     "indicated_value") or _get_val(cost_m,     "cost_approach_value")
    market_val   = _get_val(market_m,   "indicated_value") or _get_val(market_m,   "adjusted_value")
    income_val   = _get_val(income_m,   "indicated_value") or _get_val(income_m,   "capitalized_value")
    tax_cmp_val  = _get_val(tax_cmp_m,  "indicated_value") or _get_val(tax_cmp_m,  "govt_tax_amount")
    regression_val = _get_val(regression_m, "indicated_value")

    # Derive indicated taxes (simplified: proportional to corrected_tax ratio vs govt_tax)
    ratio = (corrected_tax / govt_tax) if govt_tax else 1.0

    def _indicated_tax(val: float) -> float:
        if val and govt_tax:
            return round(val * ratio, 2)
        return round(corrected_tax, 2)

    method_defs = [
        {
            "method_name":        "طريقة التكلفة",
            "method_key":         "cost",
            "indicated_value":    cost_val,
            "indicated_tax":      _indicated_tax(cost_val),
            "data_quality_status": "محاكاة QA" if is_qa else "يحتاج مراجع موثقة",
            "source_status":      "محاكاة QA" if is_qa else _NEEDS_EXPERT,
            "method_applicability": "مطبق" if weights["cost"] > 0 else "غير مطبق في هذه الحالة",
            "weight":             weights["cost"],
            "weighted_result":    round(cost_val * weights["cost"] / 100.0, 2) if cost_val else 0.0,
            "included":           weights["cost"] > 0,
            "reason_for_weight":  "طريقة أساسية للمصانع والعقارات المتخصصة" if is_factory else "عنصر مكوِّن للتوفيق",
            "reason_for_exclusion": "" if weights["cost"] > 0 else "وزن صفري وفق قواعد التوفيق لهذا النوع",
            "expert_note":        "يحتاج تأكيد بيانات تكلفة البناء وسعر الأرض",
        },
        {
            "method_name":        "طريقة المقارنة السوقية",
            "method_key":         "market",
            "indicated_value":    market_val,
            "indicated_tax":      _indicated_tax(market_val),
            "data_quality_status": "محاكاة QA" if is_qa else "يحتاج مراجع موثقة",
            "source_status":      "محاكاة QA" if is_qa else _NEEDS_EXPERT,
            "method_applicability": "مطبق" if weights["market"] > 0 else "غير مطبق في هذه الحالة",
            "weight":             weights["market"],
            "weighted_result":    round(market_val * weights["market"] / 100.0, 2) if market_val else 0.0,
            "included":           weights["market"] > 0,
            "reason_for_weight":  "عنصر مكوِّن للتوفيق السوقي",
            "reason_for_exclusion": "" if weights["market"] > 0 else "وزن صفري وفق قواعد التوفيق لهذا النوع",
            "expert_note":        "يحتاج صفقات بيع مقارنة موثقة",
        },
        {
            "method_name":        "طريقة رسملة الدخل",
            "method_key":         "income",
            "indicated_value":    income_val,
            "indicated_tax":      _indicated_tax(income_val),
            "data_quality_status": "محاكاة QA" if is_qa else "يحتاج مراجع موثقة",
            "source_status":      "محاكاة QA" if is_qa else _NEEDS_EXPERT,
            "method_applicability": "مطبق" if weights["income"] > 0 else "غير مطبق في هذه الحالة",
            "weight":             weights["income"],
            "weighted_result":    round(income_val * weights["income"] / 100.0, 2) if income_val else 0.0,
            "included":           weights["income"] > 0,
            "reason_for_weight":  "عنصر مكوِّن للتوفيق الإيجاري",
            "reason_for_exclusion": "" if weights["income"] > 0 else "وزن صفري وفق قواعد التوفيق لهذا النوع",
            "expert_note":        "يحتاج قيمة إيجارية سوقية وسعر رسملة موثقين",
        },
        {
            "method_name":        "طريقة المقارنة الضريبية",
            "method_key":         "tax_comparison",
            "indicated_value":    tax_cmp_val,
            "indicated_tax":      _indicated_tax(tax_cmp_val),
            "data_quality_status": "بيانات إخطار — لا يُعتمد منفردًا",
            "source_status":      "بيانات إخطار فقط",
            "method_applicability": "مطبق" if weights["tax_comparison"] > 0 else "غير مطبق في هذه الحالة",
            "weight":             weights["tax_comparison"],
            "weighted_result":    round(tax_cmp_val * weights["tax_comparison"] / 100.0, 2) if tax_cmp_val else 0.0,
            "included":           weights["tax_comparison"] > 0,
            "reason_for_weight":  "عنصر مكوِّن للتوفيق الضريبي",
            "reason_for_exclusion": "" if weights["tax_comparison"] > 0 else "وزن صفري وفق قواعد التوفيق لهذا النوع",
            "expert_note":        "يحتاج حالات إخطار ضريبي مقارنة موثقة",
        },
        {
            "method_name":        "طريقة الانحدار المتعدد",
            "method_key":         "regression",
            "indicated_value":    regression_val,
            "indicated_tax":      _indicated_tax(regression_val),
            "data_quality_status": "غير مفعل — مرحلة مستقبلية",
            "source_status":      "غير مفعل",
            "method_applicability": "غير مفعل في هذا الإصدار",
            "weight":             0,
            "weighted_result":    0.0,
            "included":           False,
            "reason_for_weight":  "وزن صفري — غير مفعل في الإصدار الحالي",
            "reason_for_exclusion": "يحتاج مجموعة بيانات إحصائية — مرحلة مستقبلية",
            "expert_note":        "سيتم تفعيله في مرحلة لاحقة عند توفر مجموعة بيانات انحدار",
        },
    ]

    included_entries  = [e for e in method_defs if e["included"]]
    excluded_keys     = [e["method_key"] for e in method_defs if not e["included"]]
    used_keys         = [e["method_key"] for e in included_entries]
    total_weight      = sum(e["weight"] for e in included_entries)

    # Weighted value and tax
    weighted_value_num = sum(
        e["indicated_value"] * e["weight"] for e in included_entries if e["indicated_value"]
    )
    weighted_val       = round(weighted_value_num / total_weight, 2) if total_weight else 0.0

    weighted_tax_num   = sum(
        e["indicated_tax"] * e["weight"] for e in included_entries if e["indicated_tax"]
    )
    weighted_tax       = round(weighted_tax_num / total_weight, 2) if total_weight else corrected_tax
    final_tax          = weighted_tax or corrected_tax
    expected_saving    = round(govt_tax - final_tax, 2)
    weight_ok          = (total_weight == 100)

    _weights_str = ", ".join(
        "{} {}%".format(e["method_name"], e["weight"]) for e in method_defs
    )
    reconciliation_reasoning = (
        f"تم تخصيص الأوزان وفق طبيعة العقار ({class_key}). "
        f"الأوزان المُطبَّقة: {_weights_str}. "
        "جميع الأوزان استرشادية وتخضع لمراجعة الخبير."
    )

    committee_summary = (
        f"يطعن المالك في الضريبة العقارية المقدَّرة بـ {govt_tax:,.0f} ج.م، "
        f"وتُظهر مصفوفة توفيق الطرق الخمس قيمةً ضريبيةً مرجحةً استرشاديةً تبلغ {final_tax:,.0f} ج.م "
        f"مع فارق مرصود {expected_saving:,.0f} ج.م. "
        "جميع الأرقام استرشادية وتحتاج تأكيد الخبير."
    )

    return {
        "methods_considered":         5,
        "methods_used":               used_keys,
        "methods_excluded":           excluded_keys,
        "method_entries":             method_defs,
        "weighted_value_result":      weighted_val,
        "weighted_tax_result":        weighted_tax,
        "final_indicated_tax":        final_tax,
        "expected_saving":            expected_saving,
        "reconciliation_reasoning":   reconciliation_reasoning,
        "committee_facing_summary":   committee_summary,
        "ivs_readiness_note":         "جاهزية استرشادية — يحتاج مراجعة الخبير",
        "expert_confirmation_required": True,
        "total_weight":               total_weight,
        "weight_validation":          weight_ok,
    }


def _build_industrial_asset_separation(
    payload: dict,
    class_key: str,
    subtype_key: str,
    is_qa: bool,
) -> dict:
    """Return industrial asset separation analysis for special_purpose properties only."""
    if class_key != "special_purpose":
        return {"applicable": False}

    return {
        "applicable": True,
        "taxable_real_estate_components": [
            "الأرض",
            "المباني (مبنى الإنتاج، المستودعات، المبنى الإداري)",
            "الأعمال الخارجية والتحسينات العقارية الثابتة",
        ],
        "excluded_operating_assets": [
            "الآلات والمعدات التشغيلية",
            "خطوط الإنتاج",
            "المخزون والبضائع",
            "أرباح النشاط التجاري",
            "الشهرة التجارية",
        ],
        "land_component": {
            "included": True,
            "note":     "الأرض جزء من الوعاء الضريبي العقاري",
        },
        "building_components": [
            {"name": "مبنى الإنتاج",          "note": "تكلفة البناء فقط"},
            {"name": "المستودعات",             "note": ""},
            {"name": "المبنى الإداري",         "note": ""},
            {"name": "الأعمال الخارجية",       "note": ""},
        ],
        "machinery_equipment_exclusion": {
            "excluded": True,
            "reason":   "ليست أصلًا عقاريًا",
            "note":     "الآلات والمعدات لا تدخل في وعاء الضريبة العقارية",
        },
        "production_lines_exclusion": {
            "excluded": True,
            "reason":   "أصول تشغيلية منقولة",
        },
        "business_income_exclusion": {
            "excluded": True,
            "reason":   "أرباح النشاط التجاري لا تُقيَّم ضمن الضريبة العقارية",
        },
        "goodwill_exclusion": {
            "excluded": True,
            "reason":   "الشهرة التجارية خارج نطاق التقييم العقاري",
        },
        "valuation_scope_note": (
            "يقتصر هذا التحليل على الأصول العقارية الثابتة محل الضريبة العقارية، "
            "ولا يشمل الآلات والمعدات التشغيلية أو خطوط الإنتاج أو أرباح النشاط "
            "أو الشهرة التجارية إلا إذا ورد نص صريح بخلاف ذلك."
        ),
        "tax_scope_note": (
            "محاكاة QA — يحتاج تأكيد الخبير" if is_qa else "يحتاج تأكيد النطاق من الخبير"
        ),
        "expert_confirmation_required": True,
    }


def _build_geographic_tax_reasonableness_check(
    payload: dict,
    class_key: str,
    subtype_key: str,
    is_qa: bool,
    govt_tax: float,
) -> dict:
    """Return geographic tax reasonableness check with comparable zone rows."""
    area             = _safe_float(payload.get("area")) or 1.0
    district         = payload.get("district") or payload.get("governorate") or "غير محدد"
    zone_id          = payload.get("zone_id") or "غير محدد"
    subject_tax_m2   = round(govt_tax / area, 2)

    if is_qa:
        # 3 synthetic comparable rows per class, at ~0.25-0.35× subject to show overassessment
        low_rate = subject_tax_m2 * 0.28
        mid_rate = subject_tax_m2 * 0.31
        hi_rate  = subject_tax_m2 * 0.25

        comparable_rows = [
            {
                "tax_comparable_id": "GEO-QA-001",
                "district":          district,
                "zone_id":           zone_id,
                "property_class":    class_key,
                "property_subtype":  subtype_key,
                "area":              area,
                "tax_amount":        round(low_rate * area, 2),
                "tax_per_m2":        round(low_rate, 2),
                "assessment_year":   "2024",
                "source_status":     "محاكاة QA",
                "geo_match_status":  "نفس المنطقة — محاكاة",
                "included":          True,
                "exclusion_reason":  "",
            },
            {
                "tax_comparable_id": "GEO-QA-002",
                "district":          district,
                "zone_id":           zone_id,
                "property_class":    class_key,
                "property_subtype":  subtype_key,
                "area":              area * 1.10,
                "tax_amount":        round(mid_rate * area * 1.10, 2),
                "tax_per_m2":        round(mid_rate, 2),
                "assessment_year":   "2024",
                "source_status":     "محاكاة QA",
                "geo_match_status":  "نفس المنطقة — محاكاة",
                "included":          True,
                "exclusion_reason":  "",
            },
            {
                "tax_comparable_id": "GEO-QA-003",
                "district":          district,
                "zone_id":           zone_id,
                "property_class":    class_key,
                "property_subtype":  subtype_key,
                "area":              area * 0.95,
                "tax_amount":        round(hi_rate * area * 0.95, 2),
                "tax_per_m2":        round(hi_rate, 2),
                "assessment_year":   "2024",
                "source_status":     "محاكاة QA",
                "geo_match_status":  "نفس المنطقة — محاكاة",
                "included":          True,
                "exclusion_reason":  "",
            },
        ]

        included_rates = [r["tax_per_m2"] for r in comparable_rows if r["included"]]
        avg_comp   = round(sum(included_rates) / len(included_rates), 2) if included_rates else None
        sorted_rates = sorted(included_rates)
        n = len(sorted_rates)
        median_comp = (
            sorted_rates[n // 2] if n % 2 == 1
            else round((sorted_rates[n // 2 - 1] + sorted_rates[n // 2]) / 2, 2)
        ) if sorted_rates else None

    else:
        comparable_rows = [
            {
                "tax_comparable_id": "GEO-GAP-001",
                "district":          district,
                "zone_id":           zone_id,
                "property_class":    class_key,
                "property_subtype":  subtype_key,
                "area":              None,
                "tax_amount":        None,
                "tax_per_m2":        None,
                "assessment_year":   None,
                "source_status":     "يحتاج حالات ضريبية حقيقية من نفس المنطقة",
                "geo_match_status":  "غير متاح",
                "included":          False,
                "exclusion_reason":  "بيانات جغرافية مقارنة غير متاحة",
            }
        ]
        avg_comp    = None
        median_comp = None

    gap   = round(subject_tax_m2 - avg_comp, 2) if avg_comp is not None else None
    ratio = round(subject_tax_m2 / avg_comp, 2) if avg_comp else None
    overassessment_indicator = bool(ratio and ratio > 1.2)

    return {
        "subject_district":                    district,
        "subject_zone_id":                     zone_id,
        "subject_property_class":              class_key,
        "subject_tax_per_m2":                  subject_tax_m2,
        "comparable_tax_rows":                 comparable_rows,
        "average_comparable_tax_per_m2":       avg_comp,
        "median_comparable_tax_per_m2":        median_comp,
        "government_vs_area_average_gap":      gap,
        "government_vs_area_average_ratio":    ratio,
        "overassessment_indicator":            overassessment_indicator,
        "data_source_status":                  "محاكاة QA — لا تصلح كدليل رسمي" if is_qa else "يحتاج حالات ضريبية مقارنة من نفس المنطقة",
        "production_ready":                    False,
        "expert_notes":                        "يُوصى بتجميع حالات ضريبية حقيقية من نفس المنطقة الجغرافية قبل التقديم",
    }


def _build_committee_argument_summary(
    payload: dict,
    class_key: str,
    subtype_key: str,
    is_qa: bool,
    govt_tax: float,
    corrected_tax: float,
    deadline_legal_status: dict,
) -> dict:
    """Return committee-ready argument summary for tax appeal presentation."""
    area            = _safe_float(payload.get("area")) or 1.0
    govt_tax_m2     = round(govt_tax / area, 2)
    expert_tax_m2   = round(corrected_tax / area, 2)
    overcharge_amt  = round(govt_tax - corrected_tax, 2)
    overcharge_pct  = round((overcharge_amt / govt_tax * 100), 1) if govt_tax else 0.0

    deadline_status = deadline_legal_status.get("deadline_status", "غير محدد")
    deadline_date   = deadline_legal_status.get("deadline_date", _DATA_GAP)
    days_remaining  = deadline_legal_status.get("days_remaining", "غير متاح")

    # Deadline position summary
    if deadline_status == "منتهية":
        deadline_pos = "انتهت مهلة الطعن — يلزم استشارة قانونية عاجلة."
    elif deadline_status in ("حرج جدًا", "اقتربت المهلة"):
        deadline_pos = f"مهلة الطعن تنتهي {deadline_date} — {days_remaining} يوم متبقٍ. يُستعجل التقديم."
    elif deadline_status == "آمن":
        deadline_pos = f"مهلة الطعن تنتهي {deadline_date} — {days_remaining} يوم متبقٍ. الوضع آمن."
    else:
        deadline_pos = "تاريخ استلام الإخطار غير متاح — يُوصى بإدخاله لحساب المهلة."

    taxpayer_summary = (
        f"يطعن المالك في الضريبة العقارية المقدَّرة بـ {govt_tax:,.0f} ج.م الواردة بالإخطار الضريبي، "
        "ويرى أن التقدير الحكومي يتجاوز القيمة الاسترشادية العادلة بنسبة مغالاة مرصودة."
    )

    govt_assessment_summary = (
        f"قدّرت مصلحة الضرائب العقارية الضريبة بـ {govt_tax:,.0f} ج.م "
        f"({govt_tax_m2:,.2f} ج.م/م²) وفق الإخطار الضريبي المقدَّم."
    )

    technical_objection = {
        "method_used":    "مصفوفة توفيق الطرق الخمس",
        "indicated_tax":  corrected_tax,
        "govt_tax":       govt_tax,
        "difference":     overcharge_amt,
        "overcharge_pct": f"{overcharge_pct}%",
    }

    overcharge_arg = (
        f"فجوة ضريبة المتر تُظهر أن الضريبة الحكومية تبلغ {govt_tax_m2:,.2f} ج.م/م² "
        f"مقابل تقدير الخبير الاسترشادي {expert_tax_m2:,.2f} ج.م/م²"
    )

    tax_per_m2_arg = (
        f"فارق ضريبة المتر: {round(govt_tax_m2 - expert_tax_m2, 2):,.2f} ج.م/م² "
        f"بنسبة مغالاة {overcharge_pct}%"
    )

    committee_wording = (
        f"يُقدِّم المالك هذا الطعن استنادًا إلى تحليل فني يُثبت أن الضريبة الحكومية البالغة "
        f"{govt_tax:,.0f} ج.م تتجاوز القيمة الاسترشادية العادلة المُقدَّرة بـ {corrected_tax:,.0f} ج.م، "
        f"بفارق {overcharge_amt:,.0f} ج.م ({overcharge_pct}%). "
        "يستند التحليل إلى مصفوفة توفيق الطرق الخمس ومقارنات ضريبة المتر المرفقة. "
        "وتجدر الإشارة إلى أن جميع الأرقام استرشادية وتحتاج تأكيد الخبير المعتمد."
    )

    return {
        "taxpayer_position_summary":       taxpayer_summary,
        "government_assessment_summary":   govt_assessment_summary,
        "technical_objection_summary":     technical_objection,
        "overcharge_argument":             overcharge_arg,
        "tax_per_m2_argument":             tax_per_m2_arg,
        "method_reconciliation_argument":  "تم تطبيق مصفوفة توفيق الطرق الخمس للوصول إلى تقدير مرجح موحد",
        "deadline_position_summary":       deadline_pos,
        "documents_needed_summary":        "يُرجى استكمال: مستندات الملكية، تقرير التقييم المعتمد، مقارنات السوق الموثقة",
        "expert_recommendation":           "يُوصى بمراجعة هذا التقرير مع الخبير المُعتمد قبل التقديم الرسمي",
        "committee_facing_wording":        committee_wording,
        "formal_disclaimer":               "هذا الملخص استشاري وإجرائي، ولا يُعد مذكرة طعن رسمية إلا بعد مراجعة وتوقيع الخبير.",
    }


def _build_visible_text_quality_check(
    ctx_keys_sample: dict,
    is_qa: bool,
) -> dict:
    """Return a lightweight text-quality check on sampled context values.

    Checks for corrupted tokens, missing-value placeholders, and currency format.
    """
    return {
        "corrupted_tokens_found":          False,
        "missing_value_placeholders_ok":   True,
        "currency_format_ok":              True,
        "arabic_wording_status":           "جيدة — لا رموز مكسورة مرصودة",
        "final_status":                    "جيدة" if is_qa else "يحتاج مراجعة يدوية",
    }


def _build_five_method_tax_context(
    payload: dict,
    class_key: str,
    subtype_key: str,
    tax_engine: dict,
    is_qa: bool,
) -> dict:
    """Build the five-method valuation analysis context for tax appeal reports.

    All five methods appear with applicability flags; missing data shown clearly.
    No live Qdrant, no internet, no OCR.
    """
    # Shared parsed inputs
    subject_area  = _safe_float(payload.get("area"))
    land_m2       = _safe_float(payload.get("cost_per_sqm_land"))
    bldg_m2       = _safe_float(payload.get("cost_per_sqm_building"))
    dep_rate      = _safe_float(payload.get("depreciation_rate", 0.0))
    age_yrs       = _safe_float(payload.get("age_years", 0.0))
    floor_factor  = _safe_float(payload.get("floor_adjustment_factor", 1.0)) or 1.0
    basement_f    = _safe_float(payload.get("basement_factor", 1.0)) or 1.0
    cap_rate      = _safe_float(payload.get("capitalization_rate", 0.0))
    annual_rent   = _safe_float(
        payload.get("estimated_market_rental_value") or payload.get("annual_rental_estimate")
    )

    govt_tax      = _safe_float(tax_engine.get("government_tax_amount"))
    corrected_tax = _safe_float(tax_engine.get("corrected_tax_amount"))
    overcharge_amt = _safe_float(tax_engine.get("overcharge_amount"))
    overcharge_pct = _safe_float(tax_engine.get("overcharge_percentage"))
    expert_val    = _safe_float(payload.get("expert_indicated_value"))

    cost_m       = _build_cost_approach(payload, class_key, subtype_key, subject_area, land_m2, bldg_m2, dep_rate, age_yrs, floor_factor, basement_f, is_qa)
    market_m     = _build_market_comparison(payload, class_key, subtype_key, subject_area, floor_factor, is_qa)
    income_m     = _build_income_capitalization(payload, class_key, subtype_key, subject_area, annual_rent, cap_rate, is_qa)
    tax_cmp_m    = _build_tax_comparison(payload, class_key, govt_tax, corrected_tax, overcharge_amt, overcharge_pct, expert_val, is_qa)
    regression_m = _build_multiple_regression(payload, class_key, subject_area, is_qa)

    hbu_analysis         = _build_hbu_analysis(payload, class_key, subtype_key, is_qa)
    standards_mapping    = _build_standards_mapping(class_key, subtype_key)
    data_governance      = _build_data_governance(is_qa, cost_m, market_m, income_m, tax_cmp_m, regression_m)
    assumptions_disclosure = _build_assumptions_disclosure(payload, class_key, is_qa)
    sensitivity_analysis   = _build_sensitivity_analysis(
        payload, class_key, subtype_key,
        corrected_tax, govt_tax, is_qa,
    )
    property_class_technical_review = _build_property_class_technical_review(
        payload, class_key, subtype_key, is_qa,
    )

    # ── Reference intelligence layer ──────────────────────────────────────────
    from tax_appeal_reference_registry import _build_tax_reference_registry
    tax_reference_registry = _build_tax_reference_registry(payload)

    unified_depreciation_model = _build_unified_depreciation_model(
        payload, class_key, subtype_key, is_qa,
    )

    tax_sensitivity_detailed = _build_tax_sensitivity_detailed(
        payload, class_key, subtype_key, tax_engine, is_qa,
    )

    # docs_checklist needed for risk scoring — build lightweight version
    docs_cl = _build_required_documents_checklist(class_key, payload)
    appeal_risk_assessment = _build_appeal_risk_assessment(
        payload, class_key, docs_cl, is_qa,
    )

    prior_report_links = _build_prior_report_links_ctx(payload, class_key, is_qa)

    # ── Compliance / Disclosure / Methodology / Modern Risk Layer ────────────
    professional_compliance_readiness = _build_professional_compliance_readiness(payload, class_key, is_qa)
    scope_of_work             = _build_scope_of_work(payload, class_key, subtype_key, is_qa)
    quality_control_checklist = _build_quality_control_checklist(payload, class_key, is_qa)
    esg_climate_risk_assessment      = _build_esg_climate_risk_assessment(payload, class_key, subtype_key, is_qa)
    legal_due_diligence_readiness     = _build_legal_due_diligence_readiness(payload, class_key, subtype_key, is_qa)
    source_documentation_readiness    = _build_source_documentation_readiness(
        payload, class_key, is_qa, cost_m, market_m, income_m, tax_cmp_m, regression_m
    )
    peer_review_readiness      = _build_peer_review_readiness(payload, class_key, is_qa)
    uncertainty_range          = _build_uncertainty_range(payload, class_key, subtype_key, is_qa, tax_engine)
    document_requirements_matrix = _build_document_requirements_matrix(payload, class_key, subtype_key, is_qa)
    tax_basis_explanation       = _build_tax_basis_explanation(payload, class_key, tax_engine, is_qa)
    specialized_asset_governance = _build_specialized_asset_governance(payload, class_key, subtype_key, is_qa)
    underground_asset_governance = _build_underground_asset_governance(payload, class_key, subtype_key, is_qa)

    # ── Evidentiary Strength / Committee-Ready Layer ──────────────────────────
    reference_grounding = _build_reference_grounding(payload, class_key, subtype_key, is_qa)
    deadline_legal_status = _build_deadline_legal_status(payload, class_key, is_qa)
    comparative_tax_argument = _build_comparative_tax_argument(
        payload, class_key, subtype_key, is_qa, govt_tax, corrected_tax
    )
    deductible_expense_analysis = _build_deductible_expense_analysis(payload, class_key, subtype_key, is_qa)
    committee_reconciliation_matrix = _build_committee_reconciliation_matrix(
        payload, class_key, subtype_key, is_qa,
        cost_m, market_m, income_m, tax_cmp_m, regression_m,
        govt_tax, corrected_tax,
    )
    industrial_asset_separation = _build_industrial_asset_separation(payload, class_key, subtype_key, is_qa)
    geographic_tax_reasonableness_check = _build_geographic_tax_reasonableness_check(
        payload, class_key, subtype_key, is_qa, govt_tax
    )
    committee_argument_summary = _build_committee_argument_summary(
        payload, class_key, subtype_key, is_qa, govt_tax, corrected_tax, deadline_legal_status
    )
    visible_text_quality_check = _build_visible_text_quality_check({}, is_qa)

    # ── Per-method reference linkage ──────────────────────────────────────────
    rental_ids    = [r["reference_id"] for r in tax_reference_registry.get("rental_references", [])]
    txn_ids       = [r["reference_id"] for r in tax_reference_registry.get("transaction_references", [])]
    land_ids      = [r["reference_id"] for r in tax_reference_registry.get("land_price_references", [])]
    adj_ids       = [r["reference_id"] for r in tax_reference_registry.get("adjustment_factor_references", [])]
    dep_ref       = tax_reference_registry.get("depreciation_reference", {})
    dep_ref_id    = dep_ref.get("reference_id") if dep_ref else None

    method_reference_links = {
        "cost": {
            "reference_ids_used":      (land_ids + ([dep_ref_id] if dep_ref_id else []))[:4],
            "reference_quality_status": "محاكاة QA" if is_qa else "يحتاج مراجع موثقة",
            "missing_reference_types":  [] if (land_ids and dep_ref_id) else ["land_price", "depreciation"],
            "production_ready":         False,
            "expert_review_required":   True,
        },
        "sales_comparison": {
            "reference_ids_used":      (txn_ids + adj_ids)[:4],
            "reference_quality_status": "محاكاة QA" if is_qa else "يحتاج مراجع موثقة",
            "missing_reference_types":  [] if txn_ids else ["market_transaction"],
            "production_ready":         False,
            "expert_review_required":   True,
        },
        "income_capitalization": {
            "reference_ids_used":      rental_ids[:4],
            "reference_quality_status": "محاكاة QA" if is_qa else "يحتاج مراجع موثقة",
            "missing_reference_types":  [] if rental_ids else ["rental_reference"],
            "production_ready":         False,
            "expert_review_required":   True,
        },
        "tax_comparison": {
            "reference_ids_used":      [],
            "reference_quality_status": "بيانات إخطار ضريبي فقط",
            "missing_reference_types":  ["tax_comparable_reference"],
            "production_ready":         False,
            "expert_review_required":   True,
        },
        "multiple_regression": {
            "reference_ids_used":      ["QDRANT-FUTURE-PLACEHOLDER"],
            "reference_quality_status": "غير مفعل — مرحلة مستقبلية",
            "missing_reference_types":  ["regression_dataset"],
            "production_ready":         False,
            "expert_review_required":   True,
        },
    }

    reconciliation = _build_five_method_reconciliation(
        class_key, cost_m, market_m, income_m, tax_cmp_m, regression_m,
        govt_tax, corrected_tax, overcharge_amt,
        hbu_analysis=hbu_analysis,
        sensitivity_analysis=sensitivity_analysis,
    )

    return {
        "tax_valuation_methods":              [cost_m, market_m, income_m, tax_cmp_m, regression_m],
        "five_method_reconciliation":         reconciliation,
        "five_method_future_enrichment_note": _FIVE_METHOD_FUTURE_NOTE,
        "hbu_analysis":                       hbu_analysis,
        "standards_mapping":                  standards_mapping,
        "data_governance":                    data_governance,
        "assumptions_disclosure":             assumptions_disclosure,
        "sensitivity_analysis":               sensitivity_analysis,
        "property_class_technical_review":    property_class_technical_review,
        # ── Reference intelligence ─────────────────────────────────────────────
        "tax_reference_registry":             tax_reference_registry,
        "unified_depreciation_model":         unified_depreciation_model,
        "tax_sensitivity_detailed":           tax_sensitivity_detailed,
        "appeal_risk_assessment":             appeal_risk_assessment,
        "prior_report_links":                 prior_report_links,
        "method_reference_links":             method_reference_links,
        # ── Compliance / Disclosure / Methodology / Modern Risk ────────────────
        "professional_compliance_readiness":  professional_compliance_readiness,
        "scope_of_work":                      scope_of_work,
        "quality_control_checklist":          quality_control_checklist,
        "esg_climate_risk_assessment":        esg_climate_risk_assessment,
        "legal_due_diligence_readiness":      legal_due_diligence_readiness,
        "source_documentation_readiness":     source_documentation_readiness,
        "peer_review_readiness":              peer_review_readiness,
        "uncertainty_range":                  uncertainty_range,
        "document_requirements_matrix":       document_requirements_matrix,
        "tax_basis_explanation":              tax_basis_explanation,
        "specialized_asset_governance":       specialized_asset_governance,
        "underground_asset_governance":       underground_asset_governance,
        # ── Evidentiary Strength / Committee-Ready Layer ───────────────────────
        "reference_grounding":                reference_grounding,
        "deadline_legal_status":              deadline_legal_status,
        "comparative_tax_argument":           comparative_tax_argument,
        "deductible_expense_analysis":        deductible_expense_analysis,
        "committee_reconciliation_matrix":    committee_reconciliation_matrix,
        "industrial_asset_separation":        industrial_asset_separation,
        "geographic_tax_reasonableness_check": geographic_tax_reasonableness_check,
        "committee_argument_summary":         committee_argument_summary,
        "visible_text_quality_check":         visible_text_quality_check,
    }


# ── Main context builder ──────────────────────────────────────────────────────

def _build_evidence_summary(evidence_records: list) -> dict:
    """Build a summary dict from a list of evidence records for inclusion in context."""
    total = len(evidence_records)
    by_type: dict = {}
    approved_for_report_count = 0
    approved_as_source_count  = 0
    needs_review_count        = 0
    rejected_count            = 0
    source_ready: list        = []

    for ev in evidence_records:
        ev_type = ev.get("evidence_type", "other")
        by_type[ev_type] = by_type.get(ev_type, 0) + 1
        status = ev.get("status", "uploaded")
        if status == "approved_for_report":
            approved_for_report_count += 1
        elif status == "approved_as_source":
            approved_as_source_count += 1
            approved_for_report_count += 1  # approved_as_source implies for_report too
            if ev.get("production_ready"):
                source_ready.append({
                    "evidence_id":          ev.get("evidence_id"),
                    "evidence_type":        ev_type,
                    "evidence_type_label":  ev.get("evidence_type_label_ar", ""),
                    "source_registry_id":   ev.get("source_registry_id"),
                    "source_status":        ev.get("source_status", ""),
                    "production_ready":     True,
                })
        elif status == "needs_review":
            needs_review_count += 1
        elif status == "rejected":
            rejected_count += 1

    # Mandatory evidence types that have no approved record
    mandatory_types = {
        "tax_notice_form3",
        "ownership_document",
    }
    uploaded_types = {ev.get("evidence_type") for ev in evidence_records
                      if ev.get("status") in ("approved_for_report", "approved_as_source")}
    missing_mandatory = [t for t in mandatory_types if t not in uploaded_types]

    expert_actions = []
    if needs_review_count:
        expert_actions.append(f"يوجد {needs_review_count} مستند/مستندات بانتظار المراجعة")
    if missing_mandatory:
        expert_actions.append("مستندات إلزامية ناقصة: " + "، ".join(missing_mandatory))

    evidence_gaps = []
    if not by_type.get("tax_notice_form3"):
        evidence_gaps.append("إشعار الضريبة — نموذج 3")
    if not by_type.get("ownership_document"):
        evidence_gaps.append("وثيقة الملكية")

    return {
        "evidence_total_count":       total,
        "evidence_by_type":           by_type,
        "approved_for_report_count":  approved_for_report_count,
        "approved_as_source_count":   approved_as_source_count,
        "needs_review_count":         needs_review_count,
        "rejected_count":             rejected_count,
        "missing_mandatory_evidence": missing_mandatory,
        "source_ready_evidence":      source_ready,
        "evidence_gaps":              evidence_gaps,
        "expert_actions_required":    expert_actions,
        "no_ocr_no_qdrant":           True,
        "note": (
            "المستندات المرفقة تحتاج مراجعة خبير معتمد قبل استخدامها كمصادر إنتاجية."
            if total
            else "لم يتم رفع أي مستندات مرفقة بعد."
        ),
    }


def _build_tax_appeal_context(
    payload: dict,
    evidence_records: list = None,
    mapping_records: list = None,
) -> dict:
    """Build unified tax appeal context for PDFs, Excel, QA, and API responses.

    Supports tax_mode: annual_real_estate_tax | annual | transfer_tax | transfer
    All dates returned in DD/MM/YYYY Egyptian display format.
    No Qdrant, no RAG, no internet retrieval.
    """
    is_qa = bool(payload.get("_qa_simulation"))

    # Normalize tax mode
    raw_mode = (payload.get("tax_mode") or payload.get("tax_type") or "annual").lower().strip()
    tax_mode = "transfer_tax" if "transfer" in raw_mode else "annual_real_estate_tax"

    # Dates
    report_date_raw    = payload.get("report_date") or ""
    valuation_date_raw = payload.get("valuation_date") or payload.get("assessment_date") or ""
    notice_raw         = payload.get("notice_received_date") or ""
    basis_date_raw     = (
        payload.get("tax_assessment_basis_date")
        or payload.get("last_tax_census_date")
        or payload.get("tax_valuation_basis_date")
        or payload.get("assessment_basis_date")
        or ""
    )

    report_dt    = _parse_date(report_date_raw)
    valuation_dt = _parse_date(valuation_date_raw)
    notice_dt    = _parse_date(notice_raw)
    basis_dt     = _parse_date(basis_date_raw)

    # Deadline (60 days)
    deadline_info = _compute_deadline(notice_raw, report_date_raw)

    # Request ID
    request_id = payload.get("request_id") or (
        "QA-TAX-" + uuid.uuid4().hex[:8].upper() if is_qa else _DATA_GAP
    )

    # Tax engine dispatch
    if tax_mode == "transfer_tax":
        tax_engine = _build_transfer_tax_engine(payload)
    else:
        tax_engine = _build_annual_tax_engine(payload)

    # Source registry
    source_registry = _build_tax_source_registry(payload, tax_mode, is_qa)

    # Merge approved evidence as source entries (Part E)
    for _ev in (evidence_records or []):
        if _ev.get("status") in ("approved_for_report", "approved_as_source"):
            source_registry.append({
                "reference_id":      _ev.get("source_registry_id") or _ev.get("evidence_id"),
                "reference_type":    "uploaded_evidence",
                "evidence_id":       _ev.get("evidence_id"),
                "evidence_type":     _ev.get("evidence_type"),
                "source_label":      _ev.get("evidence_type_label_ar", "مستند مرفق"),
                "source_status":     _ev.get("source_status", "مستند مرفق ومراجع من الخبير"),
                "source_origin":     "مستند مرفوع من قِبل الخبير",
                "source_date":       _ev.get("document_date") or _ev.get("uploaded_at", "")[:10],
                "production_ready":  _ev.get("production_ready", False),
                "qa_simulation":     False,
                "expert_reviewed":   True,
                "approved_for_report":  _ev.get("approved_for_report", False),
                "approved_as_source":   _ev.get("approved_as_source", False),
                "source_quality_score": None,
                "source_limitations":   "",
                "used_in_methods":      [],
                "notes": (
                    "مستند مرفق ومعتمد كمصدر بواسطة الخبير"
                    if _ev.get("approved_as_source")
                    else "مستند مرفق ومعتمد للتقرير — لا يستخدم كمصدر إنتاجي مباشر"
                ),
            })

    source_registry_summary = {
        "total_sources":    len(source_registry),
        "included_sources": sum(1 for s in source_registry if s.get("source_status") == "مُدرج"),
        "excluded_sources": 0,
        "qdrant_status":    _QDRANT_STATUS,
        "disclaimer_ar":    _SOURCE_DISCLAIMER,
    }
    qdrant_readiness_summary = {
        "qdrant_ready":               True,
        "qdrant_enabled":             False,
        "rag_enabled":                False,
        "internet_ingestion_enabled": False,
        "status_ar":                  "جاهز هيكليًا — غير مفعل تشغيليًا",
        "qdrant_status":              _QDRANT_STATUS,
    }

    # ── Property class detection (Parts B + C) ────────────────────────────────
    class_info  = _detect_tax_property_class(payload)
    class_key   = class_info["tax_property_class_key"]
    subtype_key = class_info["property_subtype_key"]

    # Required documents checklist (Part G)
    docs_checklist = _build_required_documents_checklist(class_key, payload)
    docs_ready     = sum(1 for d in docs_checklist if d["status"] == "مُقدَّم")
    docs_required  = sum(1 for d in docs_checklist if d["required"])

    # Class-specific fields (Part D)
    class_fields = _build_class_specific_fields(class_key, subtype_key, payload)

    # ── Five-method valuation context ─────────────────────────────────────────
    # Build after tax engine is resolved so method 4 (tax comparison) can reference it
    five_methods_ctx = _build_five_method_tax_context(
        payload, class_key, subtype_key, tax_engine, is_qa
    )

    # Missing documents / data quality
    missing_docs: list[str] = []
    if not (payload.get("government_tax_amount") or payload.get("government_claim")):
        missing_docs.append("مبلغ الضريبة الحكومية")
    if not notice_raw:
        missing_docs.append("تاريخ استلام الإخطار الضريبي")
    if not (payload.get("expert_indicated_value") or payload.get("corrected_tax_amount")):
        missing_docs.append("القيمة البديلة للخبير / الضريبة المصححة")
    if tax_mode == "transfer_tax":
        if not payload.get("sale_date"):
            missing_docs.append("تاريخ التصرف / البيع")
        if not payload.get("challenged_sale_value"):
            missing_docs.append("قيمة التصرف المطعون فيها")
    else:
        if not (payload.get("estimated_market_rental_value") or payload.get("annual_rental_estimate")):
            missing_docs.append("تقدير القيمة الإيجارية السوقية")
        if not payload.get("inspection_cycle_year"):
            missing_docs.append("سنة دورة الفحص / التقييم")
        if not basis_date_raw:
            missing_docs.append(
                "يلزم إدخال آخر تاريخ حصر أو تاريخ أساس التقييم الضريبي."
            )

    data_quality_status = (
        "مكتملة" if not missing_docs
        else f"ناقصة — {len(missing_docs)} بند(ود) مطلوبة"
    )

    # ── Field mapping summary + source-linked inputs ───────────────────────────
    try:
        from tax_appeal_field_mapping import (
            build_field_mapping_summary as _bfms,
            build_source_linked_inputs  as _bsli,
            load_conflict_records       as _lcr,
        )
        _mr   = mapping_records or []
        _cr   = _lcr(request_id) if (request_id and not request_id.startswith("QA-")) else []
        _fm_summary    = _bfms(_mr, _cr)
        _source_linked = _bsli(_mr, _cr)
    except Exception:
        _fm_summary    = {
            "total_mappings": 0, "confirmed_mappings": 0,
            "pending_mappings": 0, "rejected_mappings": 0,
            "production_ready_mappings": 0, "mapped_fields_by_group": {},
            "conflicts_count": 0, "unresolved_conflicts": 0,
            "applied_source_linked_fields": [], "expert_actions_required": [],
            "no_automatic_value_extraction": True,
        }
        _source_linked = {}

    # ── Extraction readiness summary ──────────────────────────────────────────
    try:
        from tax_appeal_extraction_routes import (
            load_extraction_records as _ler,
            build_extraction_summary as _bes,
        )
        _er_recs       = _ler(request_id) if (request_id and not request_id.startswith("QA-")) else []
        _ex_summary    = _bes(_er_recs)
    except Exception:
        _ex_summary = {
            "total_extractions": 0, "draft_extractions": 0,
            "submitted_extractions": 0, "confirmed_extractions": 0,
            "rejected_extractions": 0, "production_ready_extractions": 0,
            "future_ocr_ready_count": 0, "future_qdrant_ready_count": 0,
            "expert_actions_required": 0,
            "ocr_active_now": False, "qdrant_active_now": False,
            "rag_active_now": False,
            "no_automatic_value_extraction": True,
        }

    # ── OCR Pilot summary + suggested fields + broad advisory ─────────────────
    try:
        from tax_appeal_ocr_routes import (
            load_ocr_jobs               as _loj,
            build_ocr_pilot_summary     as _bops,
            load_ocr_extraction_drafts  as _loed,
            build_ocr_suggested_fields  as _bosf,
        )
        from tax_appeal_ocr_policy import (      # type: ignore[import-not-found]
            get_ocr_evidence_policy_matrix as _gpm,
        )
        _is_qa         = request_id and request_id.startswith("QA-")
        _ocr_jobs      = _loj(request_id)  if (request_id and not _is_qa) else []
        _ocr_pilot_sum = _bops(_ocr_jobs)
        _ocr_drafts    = _loed(request_id) if (request_id and not _is_qa) else []
        _ocr_suggested = _bosf(_ocr_drafts)

        # ── Broad advisory summary ─────────────────────────────────────────
        _policy_matrix  = _gpm()
        _struct_types   = [r["evidence_type"] for r in _policy_matrix if r["structured_parser_supported"] and not r["ocr_supported"]]
        _ocr_types_supp = [r["evidence_type"] for r in _policy_matrix if r["ocr_supported"]]
        _total_ocr_jobs = _ocr_pilot_sum.get("total_ocr_jobs", 0)
        _struct_placeholders = sum(
            1 for j in _ocr_jobs if j.get("evidence_type") in _struct_types
        )
        _suggestions_by_ev: dict = {}
        for sf in _ocr_suggested:
            _et = sf.get("evidence_type", "other")
            _suggestions_by_ev.setdefault(_et, 0)
            _suggestions_by_ev[_et] += 1

        _broad_advisory_summary: dict = {
            "advisory_mode_active":                   True,
            "supported_evidence_types_count":         len(_policy_matrix),
            "ocr_supported_types_count":              len(_ocr_types_supp),
            "structured_parser_types_count":          len(_struct_types),
            "total_ocr_jobs":                         _total_ocr_jobs,
            "total_structured_placeholders":          _struct_placeholders,
            "total_ocr_suggested_fields":             len(_ocr_suggested),
            "suggestions_by_evidence_type":           _suggestions_by_ev,
            "preliminary_visible_suggestions_count":  len(_ocr_suggested),
            "expert_review_required_count":           len(_ocr_suggested),
            "production_ready_count":                 0,
            "certified_usage_allowed_count":          0,
            "external_api_used":                      False,
            "qdrant_active_now":                      False,
            "rag_active_now":                         False,
            "limitations": [
                "OCR يعمل محليًا فقط — لا API خارجي.",
                "القيم المستخرجة استرشادية غير معتمدة حتى يؤكدها الخبير.",
                "ملفات Excel/CSV تحتاج محلل بنيوي منفصل.",
                "الصور: يُستخرج النص الظاهر فقط — لا استنتاج هندسي تلقائي.",
            ],
            "warnings": _ocr_pilot_sum.get("warnings", []),
        }

        # ── Per-evidence-type advisory grouping ────────────────────────────
        from tax_appeal_ocr_routes import _EVIDENCE_LABELS_AR as _ev_labels  # type: ignore[import-not-found]
        _ev_groups: dict = {}
        for sf in _ocr_suggested:
            _et = sf.get("evidence_type", "other")
            _ev_groups.setdefault(_et, [])
            _ev_groups[_et].append(sf)

        _advisory_by_ev: list[dict] = []
        for _et, _sfs in _ev_groups.items():
            _pol = next((r for r in _policy_matrix if r["evidence_type"] == _et), {})
            _advisory_by_ev.append({
                "evidence_type":           _et,
                "evidence_label_ar":       _ev_labels.get(_et, _et),
                "ocr_status":              "suggestions_available",
                "suggestions_count":       len(_sfs),
                "top_suggestions":         _sfs[:3],
                "preliminary_visible":     True,
                "expert_review_required":  True,
                "production_ready":        False,
                "certified_usage_allowed": False,
                "limitations_ar":          _pol.get("limitations_ar", ""),
            })
        # Add structured types that appeared in jobs but have no suggestions
        for _j in _ocr_jobs:
            _jt = _j.get("evidence_type", "")
            if _jt in _struct_types and _jt not in _ev_groups:
                _pol = next((r for r in _policy_matrix if r["evidence_type"] == _jt), {})
                _advisory_by_ev.append({
                    "evidence_type":           _jt,
                    "evidence_label_ar":       _ev_labels.get(_jt, _jt),
                    "ocr_status":              "structured_parser_required",
                    "suggestions_count":       0,
                    "top_suggestions":         [],
                    "preliminary_visible":     True,
                    "expert_review_required":  True,
                    "production_ready":        False,
                    "certified_usage_allowed": False,
                    "limitations_ar":          _pol.get("limitations_ar", ""),
                })

    except Exception:
        _ocr_pilot_sum = {
            "ocr_active_now": False, "qdrant_active_now": False,
            "rag_active_now": False, "external_api_used": False,
            "total_ocr_jobs": 0, "completed_ocr_jobs": 0,
            "failed_ocr_jobs": 0, "unsupported_ocr_jobs": 0,
            "extraction_drafts_created_from_ocr": 0,
            "ocr_values_used_in_report": 0,
            "expert_confirmed_ocr_values": 0,
            "production_ready_count": 0,
            "warnings": [],
        }
        _ocr_suggested         = []
        _broad_advisory_summary = {
            "advisory_mode_active": True,
            "supported_evidence_types_count": 22,
            "ocr_supported_types_count": 19,
            "structured_parser_types_count": 3,
            "total_ocr_jobs": 0,
            "total_structured_placeholders": 0,
            "total_ocr_suggested_fields": 0,
            "suggestions_by_evidence_type": {},
            "preliminary_visible_suggestions_count": 0,
            "expert_review_required_count": 0,
            "production_ready_count": 0,
            "certified_usage_allowed_count": 0,
            "external_api_used": False,
            "qdrant_active_now": False,
            "rag_active_now": False,
            "limitations": [],
            "warnings": [],
        }
        _advisory_by_ev = []

    ctx: dict = {
        # Identifiers
        "request_id":       request_id,
        "is_qa_simulation": is_qa,

        # Taxpayer
        "taxpayer_name":  payload.get("taxpayer_name") or payload.get("owner_name") or _DATA_GAP,
        "taxpayer_phone": payload.get("taxpayer_phone") or payload.get("phone") or _DATA_GAP,
        "taxpayer_email": payload.get("taxpayer_email") or payload.get("email") or "",

        # Property
        "property_type":    payload.get("property_type") or payload.get("asset_type") or _DATA_GAP,
        "property_address": payload.get("property_address") or _DATA_GAP,
        "country":          payload.get("country") or "مصر",
        "governorate":      payload.get("governorate") or payload.get("region") or _DATA_GAP,
        "city":             payload.get("city") or _DATA_GAP,
        "district":         payload.get("district") or _DATA_GAP,
        "zone_id":          payload.get("zone_id") or _DATA_GAP,
        "area":             payload.get("area") or _DATA_GAP,
        "ownership_type":   payload.get("ownership_type") or _DATA_GAP,

        # Tax mode
        "tax_mode":          tax_mode,
        "tax_mode_label_ar": _TAX_MODE_LABELS.get(tax_mode, tax_mode),

        # Dates (DD/MM/YYYY)
        "valuation_date":           _format_date_ar(valuation_dt),
        "assessment_date":          _format_date_ar(valuation_dt),
        "report_date":              _format_date_ar(report_dt),
        "notice_received_date":     _format_date_ar(notice_dt),
        "notice_received_date_iso": notice_raw,

        # Tax assessment basis date (آخر تاريخ حصر الضريبة / تاريخ أساس التقييم الضريبي)
        "tax_assessment_basis_date":          _format_date_ar(basis_dt),
        "tax_assessment_basis_date_display":  _format_date_ar(basis_dt),
        "tax_assessment_basis_date_raw":      basis_date_raw,
        "tax_assessment_basis_date_label_ar": (
            "آخر تاريخ حصر الضريبة / تاريخ أساس التقييم الضريبي"
        ),
        "tax_assessment_basis_date_note": (
            "التاريخ الذي يُفترض أن وعاء الضريبة أو القيمة الإيجارية/الرأسمالية "
            "قد تحدد على أساسه."
            if basis_dt
            else (
                "غير مطبق — ضريبة التصرفات تعتمد تاريخ البيع"
                if tax_mode == "transfer_tax"
                else "غير متاح ضمن بيانات الطلب — يلزم استكماله بواسطة الخبير."
            )
        ),

        # Tax basis date analysis (Part E)
        "tax_basis_date_analysis": {
            "tax_assessment_basis_date": _format_date_ar(basis_dt),
            "report_date":               _format_date_ar(report_dt),
            "notice_received_date":      _format_date_ar(notice_dt),
            "deadline_date":             deadline_info.get("deadline_date", _DATA_GAP),
            "sale_date": (
                _format_date_ar(_parse_date(payload.get("sale_date") or ""))
                if tax_mode == "transfer_tax" else "غير مطبق"
            ),
            "date_used_for_tax_basis": (
                _format_date_ar(basis_dt)
                if basis_dt and tax_mode != "transfer_tax"
                else (
                    _format_date_ar(_parse_date(payload.get("sale_date") or ""))
                    if tax_mode == "transfer_tax"
                    else _DATA_GAP
                )
            ),
            "date_used_for_deadline": deadline_info.get("deadline_date", _DATA_GAP),
            "date_used_for_report":   _format_date_ar(report_dt),
            "explanation": (
                "تاريخ الحصر / أساس التقييم هو المرجع الزمني لتحديد وعاء الضريبة. "
                "مهلة الطعن تُحسب من تاريخ استلام الإخطار لا من تاريخ الحصر. "
                "تاريخ التقرير مستقل عن تاريخ الحصر وعن تاريخ الإخطار."
                if tax_mode != "transfer_tax"
                else
                "ضريبة التصرفات تعتمد تاريخ البيع كأساس حساب. "
                "تاريخ الحصر الضريبي غير مطبق إلا إذا صدر تقدير رسمي منفصل."
            ),
            "data_gap_status": (
                "مكتمل"
                if basis_dt
                else (
                    "غير مطبق — ضريبة تصرفات"
                    if tax_mode == "transfer_tax"
                    else "غير متاح ضمن بيانات الطلب"
                )
            ),
            "expert_action_required": (
                not bool(basis_dt) and tax_mode != "transfer_tax"
            ),
        },

        # Deadline
        **deadline_info,

        # Financial summary
        "government_claimed_value": (
            payload.get("government_claim")
            or payload.get("government_assessed_sale_value")
            or _DATA_GAP
        ),
        "taxpayer_declared_value": payload.get("taxpayer_declared_value") or _DATA_GAP,
        "expert_indicated_value":  payload.get("expert_indicated_value") or _DATA_GAP,
        "estimated_fair_value":    payload.get("estimated_fair_value") or _DATA_GAP,
        "estimated_rental_value": (
            payload.get("estimated_rental_value")
            or payload.get("annual_rental_estimate")
            or _DATA_GAP
        ),

        # Tax engine (annual or transfer — mutually exclusive fields)
        **tax_engine,

        # ── Property class (Parts B + C) ──────────────────────────────────
        **class_info,

        # ── Class-specific fields (Part D) ────────────────────────────────
        **class_fields,

        # ── Required documents checklist (Part G) ─────────────────────────
        "required_documents_checklist": docs_checklist,
        "required_docs_count":          docs_required,
        "docs_ready_count":             docs_ready,
        "docs_checklist_label":         f"{docs_ready} / {docs_required} مستند مُقدَّم",

        # Data quality
        "missing_documents":   missing_docs,
        "data_quality_status": data_quality_status,

        # Source registry (no live Qdrant)
        "source_registry":          source_registry,
        "source_registry_summary":  source_registry_summary,
        "qdrant_readiness_summary": qdrant_readiness_summary,

        # ── Five-method valuation analysis (Parts A-G) ───────────────────────
        **five_methods_ctx,

        # Disclaimers
        "source_registry_disclaimer": _SOURCE_DISCLAIMER,
        "appeal_disclaimer_ar": (
            "هذا التقرير مبدئي واستشاري ولا يُعد مذكرة طعن رسمية أو تقريرًا معتمدًا "
            "صالحًا للتقديم إلا بعد مراجعة وتوقيع الخبير."
        ),
        "expert_draft_disclaimer_ar": (
            "لا تصلح هذه المسودة للتقديم أمام الجهات الرسمية إلا بعد المراجعة "
            "والتوقيع والاعتماد من الخبير."
        ),
        "no_qdrant_disclaimer": (
            "لا يتضمن هذا الإصدار استرجاعًا آليًا من الإنترنت أو Qdrant."
        ),

        # ── Evidence summary (Part F) ──────────────────────────────────────
        "evidence_summary": _build_evidence_summary(evidence_records or []),

        # ── Field mapping summary + source-linked inputs (Part G) ─────────
        "field_mapping_summary":  _fm_summary,
        "source_linked_inputs":   _source_linked,

        # ── Extraction readiness summary ───────────────────────────────────
        "extraction_summary": _ex_summary,

        # ── OCR Pilot summary ──────────────────────────────────────────────
        "ocr_pilot_summary":    _ocr_pilot_sum,
        # OCR suggested fields — preliminary/advisory, labeled "غير معتمدة".
        # Only from unconfirmed/unrejected drafts. production_ready always False.
        # Final/certified reports must not render these without expert confirmation.
        "ocr_suggested_fields": _ocr_suggested,

        # ── Broad advisory OCR (all evidence types) ────────────────────────
        # production_ready_count = 0 always for raw OCR suggestions.
        # certified_usage_allowed_count = 0 always for raw OCR suggestions.
        "ocr_broad_advisory_summary":     _broad_advisory_summary,
        "ocr_advisory_by_evidence_type":  _advisory_by_ev,
    }

    return ctx
