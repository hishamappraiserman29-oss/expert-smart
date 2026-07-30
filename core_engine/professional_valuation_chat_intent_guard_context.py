# professional_valuation_chat_intent_guard_context.py
# advisory_only=True | not_real_training=True | no_internal_paths=True
# Chat Intent Guard + Data Quality Score for Professional Valuation Chat Box

from __future__ import annotations
from typing import Dict, Any, List, Tuple

# ── Keyword Lists ─────────────────────────────────────────────────────────────

_VALUATION_KEYWORDS: List[str] = [
    # Property types (Arabic)
    "عقار", "أرض", "مبنى", "شقة", "فيلا", "محل", "مكتب", "مستودع",
    "فندق", "شاليه", "منزل", "بيت", "سكن", "تجاري", "صناعي", "سكني",
    "زراعي", "عقارات", "منشأة", "مشروع", "مجمع",
    # Location/area (note: "حي" omitted — too short, false-matches "بحكي" etc.)
    "موقع", "منطقة", "في حي", "شارع", "مدينة", "محافظة", "مساحة", "متر",
    "م٢", "طابق", "واجهة", "ارتداد", "عمق",
    # Valuation terms
    "تقييم", "مقيّم", "مقيم", "خبير", "استشاري", "قيمة", "سعر",
    "ثمن", "تثمين", "تقدير", "تسعير",
    # Financial
    "إيجار", "أجرة", "دخل", "عائد", "مصروف", "نفقة", "إشغال",
    "ربح", "استثمار", "عوائد", "تمويل", "رهن",
    # Legal/docs
    "ملكية", "سند", "صك", "رخصة", "تصريح", "وثيقة", "مستند", "عقد",
    # Reports
    "تقرير", "نسخة", "احترافي", "تفصيلي", "تقليدي", "إصدار تقرير",
    # Standards/special
    "هبيو", "امتثال", "معيار", "مراجعة", "محاكاة", "ايفاس",
    # Purpose
    "غرض", "هدف", "نطاق", "طريقة", "منهج", "بيع", "شراء",
    # Market
    "سوق", "مقارنة", "صفقة", "مبيعات",
    # Property details
    "غرفة", "حمام", "صالة", "مطبخ", "مرآب", "حديقة",
    # English terms
    "property", "land", "valuation", "appraisal", "report", "comparable",
    "income", "rent", "hbu", "compliance", "standards", "pdf", "excel",
]

_IRRELEVANT_KEYWORDS: List[str] = [
    "كورة", "كرة قدم", "ملعب", "مباراة", "بطولة", "دوري", "هداف", "مدرب كرة",
    "وصفة طبخ", "حلويات", "وجبة", "مطعم بعيد", "أكلة لذيذة",
    "فيلم سينما", "مسلسل", "أغنية", "مطرب", "حفلة موسيقية",
    "سياسة", "انتخابات", "حزب سياسي", "رئيس جمهورية",
    "رحلة سياحية", "توريزم", "سفر مع العيلة",
    "نكتة", "مزحة", "عبارات عشوائية",
    "مشكلة شخصية", "مشاكل عيلة",
]

# Minimum required fields for a professional valuation report
_MIN_REQUIRED_FIELDS: List[Dict[str, Any]] = [
    {"key": "asset_type",        "label": "نوع الأصل",
     "keywords": ["عقار", "فندق", "أرض", "شقة", "فيلا", "مكتب", "تجاري", "سكني",
                  "مبنى", "محل", "مستودع", "صناعي", "منشأة", "property", "hotel",
                  "apartment", "land", "office", "commercial", "residential"]},
    {"key": "asset_location",    "label": "موقع الأصل",
     "keywords": ["موقع", "منطقة", "في حي", "شارع", "مدينة", "محافظة", "يقع", "واقع",
                  "القاهرة", "الرياض", "جدة", "مكة", "الدمام", "الخبر", "أبوظبي", "دبي",
                  "location", "city", "district"]},
    {"key": "asset_area",        "label": "مساحة الأصل",
     "keywords": ["مساحة", "متر", "م٢", "م2", "مترمربع", "فدان", "هكتار", "قيراط",
                  "ألف متر", "مئة متر", "area", "sqm", "square"]},
    {"key": "ownership_status",  "label": "سند الملكية",
     "keywords": ["ملكية", "سند", "صك", "مالك", "ملاك", "تسجيل",
                  "ownership", "title", "deed"]},
    {"key": "valuation_purpose", "label": "الغرض من التقييم",
     "keywords": ["الغرض", "هدف", "بيع", "شراء", "رهن", "تمويل", "قسمة", "ميراث",
                  "إرث", "ضريبة", "تأمين", "منازعة", "لأغراض",
                  "purpose", "mortgage", "sale", "finance"]},
    {"key": "asset_condition",   "label": "حالة الأصل",
     "keywords": ["حالة", "ممتاز", "جيد", "متوسط", "سيئ", "جديد", "قديم", "مجدد",
                  "إنشاء", "condition", "excellent", "good", "fair", "poor"]},
    {"key": "current_use",       "label": "الاستخدام الحالي",
     "keywords": ["استخدام", "مؤجر", "شاغر", "مستخدم", "مشغول", "خالي", "تجاري",
                  "سكني", "إداري", "فارغ", "use", "vacant", "occupied", "leased"]},
    {"key": "report_type",       "label": "نوع التقرير",
     "keywords": ["تقليدي", "تفصيلي", "احترافي", "نوع التقرير",
                  "traditional", "detailed", "professional"]},
    {"key": "selected_standards","label": "معايير التقييم",
     "keywords": ["معيار", "المعايير", "IVS", "ايفاس", "RICS", "ريكس",
                  "standards", "ivs", "rics"]},
]

_OPTIONAL_FIELDS: List[Dict[str, Any]] = [
    {"key": "income_data",    "label": "بيانات الدخل",
     "keywords": ["إيجار", "دخل", "عائد", "أجرة", "إيرادات", "نفقات", "إشغال",
                  "rent", "income", "occupancy", "revenue"]},
    {"key": "comparables",    "label": "بيانات مقارنة سوقية",
     "keywords": ["مقارنة", "مشابه", "صفقة", "مبيع", "سعر السوق",
                  "comparable", "market price", "transaction"]},
    {"key": "valuation_date", "label": "تاريخ التقييم",
     "keywords": ["تاريخ", "٢٠٢", "2025", "2026", "2027", "هجري", "ميلادي",
                  "date", "2024", "2023"]},
    {"key": "intended_user",  "label": "المستخدم المقصود",
     "keywords": ["مستخدم", "عميل", "بنك", "مصرف", "جهة", "طالب", "موكل",
                  "client", "bank", "user"]},
    {"key": "basis_of_value", "label": "أساس القيمة",
     "keywords": ["قيمة السوق", "القيمة العادلة", "تكلفة الاستبدال",
                  "أساس القيمة", "market value", "fair value"]},
    {"key": "legal_status",   "label": "الحالة القانونية",
     "keywords": ["نظامي", "قانوني", "مرخص", "رخصة", "بلدية", "تصريح", "مخالفة",
                  "legal", "licensed", "permit", "violation"]},
]

_DOC_KEYWORDS: List[str] = [
    "مستند", "وثيقة", "صورة", "ملف مرفق", "صك", "عقد ملكية", "رفع وثيقة",
    "document", "attachment", "upload", "deed", "certificate",
]

# ── Intent Guard Context ──────────────────────────────────────────────────────

CHAT_INTENT_GUARD_CONTEXT: Dict[str, Any] = {
    "chat_intent_guard_enabled": True,
    "scope": "professional_valuation_chat_box",
    "classification_categories": [
        "valuation_relevant",
        "report_generation_relevant",
        "document_or_attachment_relevant",
        "special_report_relevant",
        "clarification_request",
        "irrelevant_general_chat",
        "unsafe_or_out_of_scope",
        "ambiguous_needs_confirmation",
    ],
    "irrelevant_messages_blocked_from_report_context": True,
    "ambiguous_messages_require_confirmation": True,
    "relevant_messages_structured_before_saving": True,
    "raw_unrelated_chat_not_used_in_pdf": True,
    "raw_unrelated_chat_not_used_in_excel": True,
    "user_warning_visible": True,
    "quick_actions_visible": True,
    "preservation_pass": True,
    "irrelevant_messages_excluded_from_report_outputs": True,
    "ambiguous_messages_excluded_until_confirmed": True,
    "pdf_generation_uses_filtered_chat_context": True,
    "excel_generation_uses_filtered_chat_context": True,
    "raw_chat_not_used_as_assumptions": True,
    "advisory_only": True,
    "not_real_training": True,
    "no_internal_paths": True,
    "ordinary_valuation_unaffected": True,
    "tax_appeal_unaffected": True,
}

# ── Data Quality Context ──────────────────────────────────────────────────────

CHAT_DATA_QUALITY_CONTEXT: Dict[str, Any] = {
    "chat_data_quality_scoring_enabled": True,
    "intent_guard_integrated": True,
    "minimum_requirements_drive_quality_score": True,
    "irrelevant_messages_not_scored": True,
    "valuation_relevant_messages_scored": True,
    "weak_data_blocks_final_conclusion": True,
    "strong_data_requires_minimum_requirements": True,
    "pdf_excel_include_data_quality_summary": True,
    "expert_review_required": True,
    "quality_levels": ["very_weak", "weak", "acceptable", "good", "strong"],
    "quality_level_labels_ar": {
        "very_weak": "ضعيفة جداً",
        "weak": "ضعيفة",
        "acceptable": "مقبولة",
        "good": "جيدة",
        "strong": "قوية",
    },
    "scoring_weights": {
        "minimum_required_completion": 0.60,
        "required_if_applicable_completion": 0.20,
        "recommended_data_completion": 0.10,
        "document_support_completion": 0.10,
    },
    "readiness_statuses": [
        "not_ready",
        "partial",
        "reviewable_draft",
        "ready_for_expert_review",
    ],
    "advisory_only": True,
    "not_real_training": True,
}

# ── Filtered Chat Context ─────────────────────────────────────────────────────

FILTERED_VALUATION_CHAT_CONTEXT: Dict[str, Any] = {
    "valuation_relevant_messages": [],
    "structured_inputs": [],
    "excluded_messages_count": 0,
    "ambiguous_pending_count": 0,
}


# ── Classifier Functions ──────────────────────────────────────────────────────

def classify_chat_message_intent(text: str) -> Dict[str, Any]:
    """Classify a chat message into one of the 8 intent categories."""
    if not text or not text.strip():
        return {"category": "ambiguous_needs_confirmation", "confidence": "high", "reason": "empty"}

    lower = text.lower()

    # Count valuation and irrelevant keyword hits
    v_score = sum(1 for kw in _VALUATION_KEYWORDS if kw.lower() in lower)
    i_score = sum(1 for kw in _IRRELEVANT_KEYWORDS if kw.lower() in lower)

    # Special report keywords (override)
    special_kws = ["هبيو", "hbu", "مراجعة تقرير", "محاكاة تقرير", "امتثال معايير"]
    for kw in special_kws:
        if kw.lower() in lower:
            return {"category": "special_report_relevant", "confidence": "high", "valuation_score": v_score}

    # Report generation keywords
    report_kws = ["pdf", "excel", "إصدار تقرير", "طباعة تقرير", "نسخة pdf", "نسخة excel"]
    for kw in report_kws:
        if kw.lower() in lower:
            return {"category": "report_generation_relevant", "confidence": "high", "valuation_score": v_score}

    # Document keywords
    doc_kws = ["رفع مستند", "رفع وثيقة", "ملف مرفق", "وثيقة رسمية", "صك المبنى"]
    for kw in doc_kws:
        if kw.lower() in lower:
            return {"category": "document_or_attachment_relevant", "confidence": "high", "valuation_score": v_score}

    # Unsafe keywords
    unsafe_kws = ["احتيال", "تزوير", "غش", "تلاعب"]
    for kw in unsafe_kws:
        if kw in lower:
            return {"category": "unsafe_or_out_of_scope", "confidence": "high", "valuation_score": 0}

    # Clarification
    clar_kws = ["هل يمكن", "كيف أقوم", "ما هو الفرق", "شرح لي", "وضح لي"]
    for kw in clar_kws:
        if kw in lower and v_score >= 1:
            return {"category": "clarification_request", "confidence": "medium", "valuation_score": v_score}

    # Main decision tree
    if v_score >= 2:
        conf = "high" if v_score >= 4 else "medium"
        return {"category": "valuation_relevant", "confidence": conf, "valuation_score": v_score}

    if i_score >= 2 and v_score == 0:
        return {"category": "irrelevant_general_chat", "confidence": "high", "irrelevant_score": i_score}

    if i_score >= 1 and v_score <= 1:
        return {"category": "irrelevant_general_chat", "confidence": "medium", "irrelevant_score": i_score}

    if v_score == 1:
        return {"category": "valuation_relevant", "confidence": "low", "valuation_score": v_score}

    return {"category": "ambiguous_needs_confirmation", "confidence": "low"}


def is_message_valuation_relevant(text: str) -> bool:
    result = classify_chat_message_intent(text)
    return result["category"] not in ("irrelevant_general_chat", "unsafe_or_out_of_scope")


def extract_minimum_requirement_coverage(text: str) -> Dict[str, Any]:
    """Extract which minimum requirements are covered by the message text."""
    if not text:
        return {"found": [], "missing": [f["label"] for f in _MIN_REQUIRED_FIELDS],
                "optional_found": [], "doc_found": False}
    lower = text.lower()
    found, missing, opt_found = [], [], []
    for field in _MIN_REQUIRED_FIELDS:
        hit = any(kw.lower() in lower for kw in field["keywords"])
        if hit:
            found.append(field["label"])
        else:
            missing.append(field["label"])
    for field in _OPTIONAL_FIELDS:
        hit = any(kw.lower() in lower for kw in field["keywords"])
        if hit:
            opt_found.append(field["label"])
    doc_found = any(kw in lower for kw in _DOC_KEYWORDS)
    return {"found": found, "missing": missing, "optional_found": opt_found, "doc_found": doc_found}


def calculate_chat_data_quality_score(coverage: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate data quality score from coverage dict."""
    min_total = len(_MIN_REQUIRED_FIELDS)
    opt_total = len(_OPTIONAL_FIELDS)
    min_comp = len(coverage["found"]) / min_total if min_total else 0.0
    opt_comp = len(coverage["optional_found"]) / opt_total if opt_total else 0.0
    doc_comp = 1.0 if coverage.get("doc_found") else 0.0

    score = round(min_comp * 60 + opt_comp * 20 + opt_comp * 10 + doc_comp * 10)
    # Cap score if minimum requirements mostly incomplete
    if min_comp < 0.5:
        score = min(score, 49)

    if score <= 24:
        level, level_ar = "very_weak", "ضعيفة جداً"
    elif score <= 49:
        level, level_ar = "weak", "ضعيفة"
    elif score <= 69:
        level, level_ar = "acceptable", "مقبولة"
    elif score <= 84:
        level, level_ar = "good", "جيدة"
    else:
        level, level_ar = "strong", "قوية"

    if min_comp < 0.3:
        readiness = "not_ready"
    elif min_comp < 0.6:
        readiness = "partial"
    elif min_comp < 0.9:
        readiness = "reviewable_draft"
    else:
        readiness = "ready_for_expert_review"

    found_labels = coverage["found"]
    missing_labels = coverage["missing"]
    reason_parts = []
    if found_labels:
        reason_parts.append("تم ذكر: " + "، ".join(found_labels))
    if missing_labels:
        shown = missing_labels[:4]
        suffix = "..." if len(missing_labels) > 4 else ""
        reason_parts.append("غير مكتمل: " + "، ".join(shown) + suffix)
    reason = ". ".join(reason_parts)

    return {
        "score": score,
        "level": level,
        "level_ar": level_ar,
        "found": found_labels,
        "missing": missing_labels,
        "optional_found": coverage["optional_found"],
        "readiness": readiness,
        "reason": reason,
        "expert_review_required": True,
    }


# ── Accessor Functions ────────────────────────────────────────────────────────

def get_chat_intent_guard_context() -> Dict[str, Any]:
    return dict(CHAT_INTENT_GUARD_CONTEXT)


def get_chat_data_quality_context() -> Dict[str, Any]:
    return dict(CHAT_DATA_QUALITY_CONTEXT)


def get_filtered_valuation_chat_context() -> Dict[str, Any]:
    return dict(FILTERED_VALUATION_CHAT_CONTEXT)
