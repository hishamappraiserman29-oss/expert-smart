"""
Professional Valuation — Chat Box Helper Controls Cleanup Context

advisory_only=True | not_real_training=True | no_commit=True

Changes tracked:
  - Voice dictation control (إملاء صوتي) and property documents upload (وثائق العقار)
    are now in the same horizontal row.
  - Report Review quick key removed from Chat Box.
  - HBU quick key removed from Chat Box.
  - Expert review request styled like ordinary Valuation page (gold theme, matching label).
  - Dedicated Report Review and HBU requirement tables are preserved in their section.
  - Certification gate is preserved.
"""

from typing import Dict, Any, List

# ---------------------------------------------------------------------------
# Chat Box Helper Controls Cleanup Context
# ---------------------------------------------------------------------------

chat_box_helper_controls_cleanup_context: Dict[str, Any] = {
    "advisory_only": True,
    "not_real_training": True,
    "voice_dictation_control_enabled": True,
    "property_documents_upload_control_enabled": True,
    "voice_and_documents_controls_same_row": True,
    "report_review_key_removed_from_chat_box": True,
    "hbu_key_removed_from_chat_box": True,
    "report_review_requirement_table_preserved": True,
    "hbu_requirement_table_preserved": True,
    "expert_review_request_matches_ordinary_valuation": True,
    "fake_expert_approval_created": False,
    "certification_gate_preserved": True,
    "preservation_pass": True,
}

# ---------------------------------------------------------------------------
# Voice Dictation Control Context
# ---------------------------------------------------------------------------

voice_dictation_control_context: Dict[str, Any] = {
    "enabled": True,
    "location": "chat_box_helper_row",
    "label": "إملاء صوتي",
    "same_row_as_property_documents": True,
    "passes_through_chat_intent_guard": True,
    "passes_through_data_quality_scoring": True,
    "passes_through_minimum_requirements_check": True,
    "status_messages": {
        "ready": "الإملاء الصوتي جاهز",
        "listening": "جارٍ الاستماع...",
        "converted": "تم تحويل الصوت إلى نص",
        "not_supported": "الإملاء الصوتي غير مدعوم في هذا المتصفح",
    },
}

# ---------------------------------------------------------------------------
# Property Documents Upload Context
# ---------------------------------------------------------------------------

property_documents_upload_context: Dict[str, Any] = {
    "enabled": True,
    "location": "chat_box_helper_row",
    "label": "وثائق العقار",
    "accepted_file_types": ["pdf", "jpg", "jpeg", "png", "xls", "xlsx", "doc", "docx"],
    "linked_to": "asset_property_documents",
    "not_linked_to": [
        "report_review_upload",
        "hbu_upload",
        "simulation_upload",
    ],
    "document_categories": [
        "سند الملكية",
        "رخصة البناء",
        "رخصة التشغيل",
        "عقود الإيجار",
        "كشف المساحات",
        "صور العقار",
        "خريطة / كروكي",
        "شهادة الضرائب العقارية",
        "موافقات بيئية",
        "موافقة دفاع مدني",
        "مستندات أخرى تخص العقار",
    ],
}

# ---------------------------------------------------------------------------
# Expert Review Request Context
# ---------------------------------------------------------------------------

expert_review_request_context: Dict[str, Any] = {
    "enabled": True,
    "matched_ordinary_valuation_page_style": True,
    "expert_review_requested": False,
    "certification_ready_changed": False,
    "fake_approval_created": False,
    "source_style": "ordinary_valuation_page",
    "button_label": "📜 طلب مراجعة واعتماد من خبير التقييم",
    "theme": "gold",
    "color_scheme": {
        "border": "rgba(212,175,55,0.35)",
        "background": "rgba(212,175,55,0.12)",
        "text": "var(--gold,#d4af37)",
        "border_radius": "8px",
        "font_weight": "700",
    },
    "advisory_notice": (
        "طلب المراجعة لا يُعتمد التقرير تلقائياً — "
        "يتطلب مراجعة الخبير وموافقته عبر بوابة الاعتماد."
    ),
}

# ---------------------------------------------------------------------------
# Removed Controls Registry
# ---------------------------------------------------------------------------

REMOVED_CHAT_BOX_CONTROLS: List[Dict[str, str]] = [
    {
        "label_ar": "مراجعة التقارير",
        "testid": "pro-val-report-review-toggle",
        "reason": "report_review_quick_key_removed_from_chat_box",
        "tombstone_testid": "pv-chat-report-review-key-removed",
        "preserved_in": "dedicated_special_report_requirement_tables",
    },
    {
        "label_ar": "تقارير أعلى وأفضل استخدام",
        "testid": "pro-val-hbu-report-toggle",
        "reason": "hbu_quick_key_removed_from_chat_box",
        "tombstone_testid": "pv-chat-hbu-key-removed",
        "preserved_in": "dedicated_special_report_requirement_tables",
    },
]

# ---------------------------------------------------------------------------
# Preserved Controls Registry (must NOT be touched)
# ---------------------------------------------------------------------------

PRESERVED_OUTSIDE_CHAT_BOX: List[Dict[str, str]] = [
    {
        "description": "Dedicated Report Review requirement table",
        "section": "special_reports_section",
        "preservation_required": True,
    },
    {
        "description": "Dedicated HBU requirement table",
        "section": "special_reports_section",
        "preservation_required": True,
    },
    {
        "description": "PDF generation logic",
        "preservation_required": True,
    },
    {
        "description": "Excel generation logic",
        "preservation_required": True,
    },
    {
        "description": "Core report generation",
        "preservation_required": True,
    },
]

# ---------------------------------------------------------------------------
# Unified Chat Context Helper Controls Structure
# ---------------------------------------------------------------------------

CHAT_CONTEXT_HELPER_CONTROLS_STRUCTURE: Dict[str, Any] = {
    "chat_helper_controls": {
        "voice_dictation_enabled": True,
        "property_documents_upload_enabled": True,
        "voice_and_documents_same_row": True,
        "report_review_quick_key_removed": True,
        "hbu_quick_key_removed": True,
        "simulation_upload_shortcut_removed": True,
        "review_upload_shortcut_removed": True,
        "property_documents": [],
        "expert_review_request": {
            "enabled": True,
            "style_matches_ordinary_valuation_page": True,
            "requested": False,
            "certification_ready_changed": False,
            "fake_approval_created": False,
            "source_style": "ordinary_valuation_page",
        },
    }
}
