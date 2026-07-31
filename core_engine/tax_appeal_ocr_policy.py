# -*- coding: utf-8 -*-
"""
tax_appeal_ocr_policy.py — Evidence-type OCR policy matrix for Tax Appeal.

Rules enforced in matrix:
  - raw_text_visible_to_ordinary_user = False for all types
  - expert_review_required = True for all types
  - certified_usage_requires_confirmation = True for all types
  - structured_parser_supported = True only for Excel/CSV types (placeholder in this phase)
  - ocr_supported = False for Excel/CSV types
"""
from __future__ import annotations
from typing import Optional


_MATRIX: list[dict] = [
    {
        "evidence_type": "tax_notice_form3",
        "ocr_supported": True,
        "text_passthrough_supported": True,
        "structured_parser_supported": False,
        "preliminary_advisory_display_allowed": True,
        "expert_review_required": True,
        "certified_usage_requires_confirmation": True,
        "raw_text_visible_to_expert": True,
        "raw_text_visible_to_ordinary_user": False,
        "candidate_fields_supported": True,
        "limitations_ar": "الاستخراج النصي من PDF ممكن عبر PyMuPDF. الصور تحتاج Tesseract.",
    },
    {
        "evidence_type": "ownership_document",
        "ocr_supported": True,
        "text_passthrough_supported": True,
        "structured_parser_supported": False,
        "preliminary_advisory_display_allowed": True,
        "expert_review_required": True,
        "certified_usage_requires_confirmation": True,
        "raw_text_visible_to_expert": True,
        "raw_text_visible_to_ordinary_user": False,
        "candidate_fields_supported": True,
        "limitations_ar": "وثائق الملكية قد تكون مصوَّرة — يُفضَّل النص المحوسب. الحقول القانونية تحتاج تحقق يدوي.",
    },
    {
        "evidence_type": "lease_contract",
        "ocr_supported": True,
        "text_passthrough_supported": True,
        "structured_parser_supported": False,
        "preliminary_advisory_display_allowed": True,
        "expert_review_required": True,
        "certified_usage_requires_confirmation": True,
        "raw_text_visible_to_expert": True,
        "raw_text_visible_to_ordinary_user": False,
        "candidate_fields_supported": True,
        "limitations_ar": "عقود الإيجار قد تحتوي شروطًا تفصيلية — يُوصى بمراجعة الحقول القانونية بشكل خاص.",
    },
    {
        "evidence_type": "building_permit",
        "ocr_supported": True,
        "text_passthrough_supported": True,
        "structured_parser_supported": False,
        "preliminary_advisory_display_allowed": True,
        "expert_review_required": True,
        "certified_usage_requires_confirmation": True,
        "raw_text_visible_to_expert": True,
        "raw_text_visible_to_ordinary_user": False,
        "candidate_fields_supported": True,
        "limitations_ar": "رخص البناء قد تكون مصوَّرة بجودة منخفضة — التحقق اليدوي ضروري للأرقام والتواريخ.",
    },
    {
        "evidence_type": "occupancy_or_completion_certificate",
        "ocr_supported": True,
        "text_passthrough_supported": True,
        "structured_parser_supported": False,
        "preliminary_advisory_display_allowed": True,
        "expert_review_required": True,
        "certified_usage_requires_confirmation": True,
        "raw_text_visible_to_expert": True,
        "raw_text_visible_to_ordinary_user": False,
        "candidate_fields_supported": True,
        "limitations_ar": "شهادات الإشغال قد تتضمن ختمًا صعب القراءة — تحقق من التواريخ يدويًا.",
    },
    {
        "evidence_type": "activity_license",
        "ocr_supported": True,
        "text_passthrough_supported": True,
        "structured_parser_supported": False,
        "preliminary_advisory_display_allowed": True,
        "expert_review_required": True,
        "certified_usage_requires_confirmation": True,
        "raw_text_visible_to_expert": True,
        "raw_text_visible_to_ordinary_user": False,
        "candidate_fields_supported": True,
        "limitations_ar": "تراخيص النشاط قد تحتوي على أكواد حكومية — تحتاج مراجعة دقيقة.",
    },
    {
        "evidence_type": "commercial_register",
        "ocr_supported": True,
        "text_passthrough_supported": True,
        "structured_parser_supported": False,
        "preliminary_advisory_display_allowed": True,
        "expert_review_required": True,
        "certified_usage_requires_confirmation": True,
        "raw_text_visible_to_expert": True,
        "raw_text_visible_to_ordinary_user": False,
        "candidate_fields_supported": True,
        "limitations_ar": "السجلات التجارية عادةً نص محوسب في PDF — الاستخراج موثوق نسبيًا.",
    },
    {
        "evidence_type": "industrial_license",
        "ocr_supported": True,
        "text_passthrough_supported": True,
        "structured_parser_supported": False,
        "preliminary_advisory_display_allowed": True,
        "expert_review_required": True,
        "certified_usage_requires_confirmation": True,
        "raw_text_visible_to_expert": True,
        "raw_text_visible_to_ordinary_user": False,
        "candidate_fields_supported": True,
        "limitations_ar": "تراخيص الصناعية قد تحتوي على مرفقات تقنية — تحقق من الأرقام والمساحات.",
    },
    {
        "evidence_type": "land_allocation_document",
        "ocr_supported": True,
        "text_passthrough_supported": True,
        "structured_parser_supported": False,
        "preliminary_advisory_display_allowed": True,
        "expert_review_required": True,
        "certified_usage_requires_confirmation": True,
        "raw_text_visible_to_expert": True,
        "raw_text_visible_to_ordinary_user": False,
        "candidate_fields_supported": True,
        "limitations_ar": "مستندات التخصيص قد تحتوي قرارات حكومية — التحقق من الأرقام القانونية ضروري.",
    },
    {
        "evidence_type": "area_statement",
        "ocr_supported": True,
        "text_passthrough_supported": True,
        "structured_parser_supported": False,
        "preliminary_advisory_display_allowed": True,
        "expert_review_required": True,
        "certified_usage_requires_confirmation": True,
        "raw_text_visible_to_expert": True,
        "raw_text_visible_to_ordinary_user": False,
        "candidate_fields_supported": True,
        "limitations_ar": "كشوف المساحة تحتاج مقارنة بالمخططات الهندسية — لا تستخدم تلقائيًا.",
    },
    {
        "evidence_type": "floor_plan",
        "ocr_supported": True,
        "text_passthrough_supported": False,
        "structured_parser_supported": False,
        "preliminary_advisory_display_allowed": True,
        "expert_review_required": True,
        "certified_usage_requires_confirmation": True,
        "raw_text_visible_to_expert": True,
        "raw_text_visible_to_ordinary_user": False,
        "candidate_fields_supported": True,
        "limitations_ar": "مخططات البناء — OCR يستخرج النصوص الظاهرة فقط، لا يستنتج مساحات أو مقاسات هندسية تلقائيًا.",
    },
    {
        "evidence_type": "property_photos",
        "ocr_supported": True,
        "text_passthrough_supported": False,
        "structured_parser_supported": False,
        "preliminary_advisory_display_allowed": True,
        "expert_review_required": True,
        "certified_usage_requires_confirmation": True,
        "raw_text_visible_to_expert": True,
        "raw_text_visible_to_ordinary_user": False,
        "candidate_fields_supported": True,
        "limitations_ar": "صور العقار — OCR يستخرج النصوص الظاهرة فقط. لا يتم تقدير الحالة أو المساحة تلقائيًا من الصور.",
    },
    {
        "evidence_type": "map_or_aerial_image",
        "ocr_supported": True,
        "text_passthrough_supported": False,
        "structured_parser_supported": False,
        "preliminary_advisory_display_allowed": True,
        "expert_review_required": True,
        "certified_usage_requires_confirmation": True,
        "raw_text_visible_to_expert": True,
        "raw_text_visible_to_ordinary_user": False,
        "candidate_fields_supported": True,
        "limitations_ar": "صور الخرائط والمسح الجوي — OCR يستخرج النصوص الظاهرة فقط. لا يستنتج مواقع أو مسافات تلقائيًا.",
    },
    {
        "evidence_type": "market_comparables_excel",
        "ocr_supported": False,
        "text_passthrough_supported": False,
        "structured_parser_supported": True,
        "preliminary_advisory_display_allowed": True,
        "expert_review_required": True,
        "certified_usage_requires_confirmation": True,
        "raw_text_visible_to_expert": False,
        "raw_text_visible_to_ordinary_user": False,
        "candidate_fields_supported": False,
        "limitations_ar": "ملف Excel — يحتاج محلل بنيوي (structured parser) منفصل. لا يعالج كـ OCR في هذه المرحلة.",
    },
    {
        "evidence_type": "rental_comparables_excel",
        "ocr_supported": False,
        "text_passthrough_supported": False,
        "structured_parser_supported": True,
        "preliminary_advisory_display_allowed": True,
        "expert_review_required": True,
        "certified_usage_requires_confirmation": True,
        "raw_text_visible_to_expert": False,
        "raw_text_visible_to_ordinary_user": False,
        "candidate_fields_supported": False,
        "limitations_ar": "ملف Excel — يحتاج محلل بنيوي منفصل. لا يعالج كـ OCR في هذه المرحلة.",
    },
    {
        "evidence_type": "tax_comparables_excel",
        "ocr_supported": False,
        "text_passthrough_supported": False,
        "structured_parser_supported": True,
        "preliminary_advisory_display_allowed": True,
        "expert_review_required": True,
        "certified_usage_requires_confirmation": True,
        "raw_text_visible_to_expert": False,
        "raw_text_visible_to_ordinary_user": False,
        "candidate_fields_supported": False,
        "limitations_ar": "ملف Excel — يحتاج محلل بنيوي منفصل. لا يعالج كـ OCR في هذه المرحلة.",
    },
    {
        "evidence_type": "factory_cost_guidance",
        "ocr_supported": True,
        "text_passthrough_supported": True,
        "structured_parser_supported": False,
        "preliminary_advisory_display_allowed": True,
        "expert_review_required": True,
        "certified_usage_requires_confirmation": True,
        "raw_text_visible_to_expert": True,
        "raw_text_visible_to_ordinary_user": False,
        "candidate_fields_supported": True,
        "limitations_ar": "أدلة تكاليف المصانع — التحقق من التواريخ والمصادر ضروري للاستخدام في التقرير.",
    },
    {
        "evidence_type": "ain_shams_factory_cost_reference",
        "ocr_supported": True,
        "text_passthrough_supported": True,
        "structured_parser_supported": False,
        "preliminary_advisory_display_allowed": True,
        "expert_review_required": True,
        "certified_usage_requires_confirmation": True,
        "raw_text_visible_to_expert": True,
        "raw_text_visible_to_ordinary_user": False,
        "candidate_fields_supported": True,
        "limitations_ar": "مرجع عين شمس — تحقق من سنة الإصدار وصلاحية تطبيق الأسعار.",
    },
    {
        "evidence_type": "nuca_land_price_reference",
        "ocr_supported": True,
        "text_passthrough_supported": True,
        "structured_parser_supported": False,
        "preliminary_advisory_display_allowed": True,
        "expert_review_required": True,
        "certified_usage_requires_confirmation": True,
        "raw_text_visible_to_expert": True,
        "raw_text_visible_to_ordinary_user": False,
        "candidate_fields_supported": True,
        "limitations_ar": "مرجع NUCA — أسعار الأراضي تتغير بمرور الوقت، تحقق من تاريخ المرجع.",
    },
    {
        "evidence_type": "expert_note",
        "ocr_supported": True,
        "text_passthrough_supported": True,
        "structured_parser_supported": False,
        "preliminary_advisory_display_allowed": True,
        "expert_review_required": True,
        "certified_usage_requires_confirmation": True,
        "raw_text_visible_to_expert": True,
        "raw_text_visible_to_ordinary_user": False,
        "candidate_fields_supported": True,
        "limitations_ar": "مذكرة الخبير — محتواها للاطلاع الداخلي. الملخص المبدئي فقط يظهر في تقرير أولي.",
    },
    {
        "evidence_type": "legal_note",
        "ocr_supported": True,
        "text_passthrough_supported": True,
        "structured_parser_supported": False,
        "preliminary_advisory_display_allowed": True,
        "expert_review_required": True,
        "certified_usage_requires_confirmation": True,
        "raw_text_visible_to_expert": True,
        "raw_text_visible_to_ordinary_user": False,
        "candidate_fields_supported": True,
        "limitations_ar": "مذكرة قانونية — يجب أن يراجعها المستشار القانوني قبل أي استخدام رسمي.",
    },
    {
        "evidence_type": "other",
        "ocr_supported": True,
        "text_passthrough_supported": True,
        "structured_parser_supported": False,
        "preliminary_advisory_display_allowed": True,
        "expert_review_required": True,
        "certified_usage_requires_confirmation": True,
        "raw_text_visible_to_expert": True,
        "raw_text_visible_to_ordinary_user": False,
        "candidate_fields_supported": True,
        "limitations_ar": "مستند غير مصنف — يحتاج إدخال يدوي من الخبير.",
    },
]

# Fast lookup index
_MATRIX_INDEX: dict[str, dict] = {row["evidence_type"]: row for row in _MATRIX}


def get_ocr_evidence_policy_matrix() -> list[dict]:
    """Return the full OCR policy matrix for all supported evidence types."""
    return _MATRIX


def get_ocr_policy_for_evidence_type(evidence_type: str) -> Optional[dict]:
    """Return the OCR policy row for a specific evidence type, or None."""
    return _MATRIX_INDEX.get(evidence_type)


def get_structured_evidence_types() -> list[str]:
    """Return evidence types that require a structured parser (not OCR)."""
    return [
        row["evidence_type"] for row in _MATRIX
        if row["structured_parser_supported"] and not row["ocr_supported"]
    ]


def get_ocr_supported_evidence_types() -> list[str]:
    """Return evidence types where local OCR is supported."""
    return [row["evidence_type"] for row in _MATRIX if row["ocr_supported"]]
