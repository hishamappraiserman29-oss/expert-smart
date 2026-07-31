# reporting_ui_deduplication_chat_layout_context.py
# Reporting UI Deduplication and Chat Layout Merge
# advisory_only=True | not_real_training=True | no_commit=True
#
# Phase: REPORTING_UI_DUPLICATION_AND_CHAT_LAYOUT_MERGE
# Merges duplicated report sections and places unified reporting inside chat container.

REPORTING_UI_DEDUPLICATION_CHAT_LAYOUT_CONTEXT = {

    # ── Merge: main reporting sections ───────────────────────────────────────
    "main_unified_section_heading": "إصدار ومراجعة تقارير التقييم",
    "main_unified_section_testid": "pv-unified-report-type-section",
    "main_unified_section_inside_chat_container": True,
    "chat_container_testid": "pro-val-chat-command-center",

    "merged_from_sections": [
        "محتوى التقرير: تحليل وإصدار التقارير",
        "إصدار تقارير التقييم الأساسية",
    ],

    "old_heading_removed": "إصدار تقارير التقييم الأساسية",
    "old_heading_max_occurrences": 0,

    # ── Format availability ───────────────────────────────────────────────────
    "user_formats_available": ["PDF", "HTML"],
    "user_format_pdf_testid": "pv-format-label-pdf",
    "user_format_html_view_testid": "pv-format-label-html-view",
    "user_format_html_download_testid": "pv-format-label-html-download",
    "excel_hidden_from_normal_user": True,
    "admin_excel_role_controlled": True,
    "admin_excel_testid": "pro-val-generate-admin-excel-sheets",

    # ── Actions inside unified section ────────────────────────────────────────
    "review_action_in_unified_section": True,
    "review_action_testid": "pv-unified-action-review-report",
    "review_action_label": "مراجعة تقرير التقييم",
    "hbu_action_in_unified_section": True,
    "hbu_action_testid": "pv-unified-action-hbu",
    "hbu_action_label": "تحليل HBU",

    # ── Report type chips preserved ───────────────────────────────────────────
    "core_report_types": [
        "traditional_report",
        "detailed_report",
        "professional_report",
    ],
    "core_report_chips_testids": [
        "pv-unified-card-traditional",
        "pv-unified-card-detailed",
        "pv-unified-card-professional",
    ],
    "core_report_issuance_section_testid": "pv-unified-report-type-section",
    "core_report_issuance_section_preserved": True,

    # ── Merge: advanced/upload sections ──────────────────────────────────────
    "advanced_section_heading": "التقارير الخاصة والتحليلات المتقدمة",
    "advanced_section_testid": "pv-special-report-workflows",
    "advanced_section_outside_chat_container": True,

    "simulation_section_merged_into_advanced": True,
    "standalone_simulation_heading_removed": True,
    "simulation_action_testid": "pv-open-simulation-table",
    "simulation_action_label": "رفع تقرير للمراجعة والتحليل",

    "uploaded_report_review_testid": "pv-open-report-review-table",
    "uploaded_report_review_label": "مراجعة التقرير المرفوع",

    # ── Chat toggle cleanup ───────────────────────────────────────────────────
    "simulation_clip_removed_from_chat_box": True,
    "simulation_clip_backward_compat_span": True,
    "simulation_clip_span_testid": "pro-val-simulation-report-clip",
    "review_toggle_removed_from_chat_box": True,
    "review_toggle_backward_compat_span": True,
    "hbu_toggle_removed_from_chat_box": True,
    "hbu_toggle_backward_compat_span": True,

    # ── Upload control ────────────────────────────────────────────────────────
    "file_upload_control_present": True,
    "file_upload_control_testid": "rr-pdf-upload",
    "file_upload_control_count_max": 1,

    # ── Safety / Advisory Flags ───────────────────────────────────────────────
    "advisory_only": True,
    "not_real_training": True,
    "no_internal_paths": True,
    "report_calculations_unmodified": True,
    "download_security_unmodified": True,
    "backend_role_rules_unmodified": True,
    "pdf_generation_capability_preserved": True,
    "html_generation_capability_preserved": True,
    "admin_excel_generation_capability_preserved": True,
    "existing_report_actions_preserved": True,
}


def get_reporting_ui_deduplication_chat_layout_context() -> dict:
    return dict(REPORTING_UI_DEDUPLICATION_CHAT_LAYOUT_CONTEXT)
