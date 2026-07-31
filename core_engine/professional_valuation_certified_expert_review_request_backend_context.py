"""
Professional Valuation — Certified Expert Review Request Backend Context
advisory_only=True | not_real_training=True | certification_ready=False

This module defines the context registry for the certified expert review
request section in the Professional Valuation page.  The section mirrors
the ordinary Valuation page in structure, wording, and behaviour.

Business rules enforced here:
  - Expert review request does NOT issue a certified report immediately.
  - certification_ready is NEVER set automatically.
  - No fake approval, signature, or stamp is created.
  - Admin Excel workbooks remain internal (expert/admin only).
  - Certified PDF delivery happens only after expert approval.
"""

from __future__ import annotations

# ── Context registry ─────────────────────────────────────────────────────────

expert_review_certified_request_context: dict = {
    "enabled": True,
    "source_style": "ordinary_valuation_page",
    "matched_ordinary_valuation_page_style": True,
    "request_title": "هل تحتاج تقرير تقييم معتمد؟",
    "expert_review_requested": False,
    "delivery_method": None,                # "whatsapp" | "email" | None
    "email": "",
    "phone_whatsapp": "",
    "full_name": "",
    "requested_report_type": "",
    "request_status": "not_requested",      # not_requested | draft_registered | pending_expert_review
    "certification_ready_changed": False,
    "fake_approval_created": False,
    "fake_signature_created": False,
    "fake_stamp_created": False,
    "certified_pdf_generated_immediately": False,
    "admin_excel_sent_to_user": False,
    "future_delivery_integration_required": True,
}

professional_valuation_certified_expert_review_request_backend_context: dict = {
    "certified_expert_review_request_enabled": True,
    "matched_ordinary_valuation_page": True,
    "request_does_not_issue_certified_report_immediately": True,
    "expert_review_required_before_certified_pdf": True,
    "delivery_methods": ["whatsapp", "email"],
    "email_required_when_email_selected": True,
    "phone_required_when_whatsapp_selected": True,
    "full_name_required": True,
    "requested_report_type_optional": True,
    "admin_excel_internal_only": True,
    "certification_gate_preserved": True,
    "fake_approval_created": False,
    "fake_signature_created": False,
    "fake_stamp_created": False,
    "preservation_pass": True,
}

unified_professional_valuation_page_context_expert_review_request: dict = {
    "enabled": True,
    "style_matches_ordinary_valuation_page": True,
    "requested": False,
    "delivery_method": "",
    "email": "",
    "phone_whatsapp": "",
    "full_name": "",
    "requested_report_type": "",
    "status": "not_requested",
    "certification_ready_changed": False,
    "excel_internal_only": True,
    "certified_pdf_delivery_after_expert_approval_only": True,
}

# ── Required text content (for DOM / QA verification) ───────────────────────

REQUIRED_VISIBLE_TEXT: dict[str, str] = {
    "title":           "هل تحتاج تقرير تقييم معتمد؟",
    "description":     "يمكنك تحويل المسودة المبدئية إلى طلب مراجعة خبير",
    "request_label":   "طلب مراجعة واعتماد من خبير التقييم",
    "delivery_label":  "طريقة استلام التقرير المعتمد",
    "delivery_placeholder": "- اختر طريقة الاستلام -",
    "whatsapp_option": "واتساب",
    "email_option":    "البريد الإلكتروني",
    "phone_label":     "رقم الهاتف / واتساب",
    "name_label":      "الاسم بالكامل",
    "report_type_label": "نوع التقرير المطلوب",
    "excel_notice":    "ملفات Excel التفصيلية تظل داخلية للخبير أو الإدارة فقط ولا تُرسل للمستخدم",
    "no_immediate_certification": "يتم تسجيل الطلب مبدئيًا داخل الواجهة فقط",
}

# ── Delivery method validation rules ────────────────────────────────────────

DELIVERY_VALIDATION_RULES: dict = {
    "البريد الإلكتروني": {
        "required_field": "email",
        "validate_format": True,
    },
    "واتساب": {
        "required_field": "phone_whatsapp",
        "validate_format": False,
    },
    "": {
        "required_field": None,
        "error": "يرجى اختيار طريقة استلام التقرير المعتمد",
    },
}

# ── Report type options ──────────────────────────────────────────────────────

REPORT_TYPE_OPTIONS: list[dict] = [
    {"value": "traditional_report",       "label": "تقرير تقليدي"},
    {"value": "detailed_report",          "label": "تقرير تفصيلي"},
    {"value": "professional_report",      "label": "تقرير احترافي"},
    {"value": "report_review",            "label": "تقرير مراجعة"},
    {"value": "simulation_report",        "label": "تقرير محاكاة"},
    {"value": "hbu_report",               "label": "تقرير أعلى وأفضل استخدام"},
    {"value": "standards_compliance_report", "label": "تقرير امتثال المعايير"},
]


def get_backend_context() -> dict:
    """Return the full backend context dict for this feature."""
    return professional_valuation_certified_expert_review_request_backend_context


def get_expert_review_request_context() -> dict:
    """Return the certified expert review request context."""
    return expert_review_certified_request_context


def validate_delivery_method(delivery_method: str, email: str, phone: str) -> dict:
    """Validate delivery method fields.  Returns {'valid': bool, 'error': str}."""
    if not delivery_method:
        return {"valid": False, "error": "يرجى اختيار طريقة استلام التقرير المعتمد."}
    if delivery_method == "البريد الإلكتروني":
        if not email or not email.strip():
            return {"valid": False, "error": "يرجى إدخال البريد الإلكتروني."}
        import re
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email.strip()):
            return {"valid": False, "error": "صيغة البريد الإلكتروني غير صحيحة."}
    if delivery_method == "واتساب":
        if not phone or not phone.strip():
            return {"valid": False, "error": "يرجى إدخال رقم الهاتف / واتساب."}
    return {"valid": True, "error": ""}
