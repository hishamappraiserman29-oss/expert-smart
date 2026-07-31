"""
Phase: remove-duplicate-chat-pdf-send-buttons
Chat Report Output Deduplication Context
advisory_only=True | not_real_training=True | no_commit=True
"""

chat_report_output_deduplication_context = {
    "phase": "remove_duplicate_chat_output_buttons",
    "main_unified_report_section_preserved": True,
    "main_unified_report_label": "تحليل وإصدار التقارير",
    "visible_report_types_count": 7,
    "report_types": [
        "traditional_report",
        "detailed_report",
        "professional_report",
        "simulated_uploaded_report",
        "report_review_output",
        "hbu_analysis_report",
        "standards_compliance_report",
    ],
    "duplicate_lower_pdf_button_removed": True,
    "duplicate_lower_send_to_chat_button_removed": True,
    "removed_button_labels": [
        "إصدار تقرير PDF للمستخدم",
        "إرسال للشات",
    ],
    "pdf_generation_capability_preserved": True,
    "admin_excel_generation_capability_preserved": True,
    "feature_toggles_preserved": True,
    "advisory_notice_preserved": True,
    "legacy_aliases_preserved": True,
    "deleted_backend_capabilities": [],
    "preservation_pass": True,
    "advisory_only": True,
    "not_real_training": True,
}
