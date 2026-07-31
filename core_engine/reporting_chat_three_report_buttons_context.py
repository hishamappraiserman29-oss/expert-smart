# reporting_chat_three_report_buttons_context.py
# Chat Three Report Buttons and Duplication Removal
# advisory_only=True | not_real_training=True | no_commit=True
#
# Mandate: REPORTING_CHAT_THREE_REPORT_BUTTONS_AND_DUPLICATION_REMOVAL_APPROVED
# Removes seven-report dropdown from chat, two obsolete buttons, and the
# duplicated expert-review section.  Preserves three report cards as the
# only report-type selection path before the Send action.

REPORTING_CHAT_THREE_REPORT_BUTTONS_CONTEXT = {

    # ── Chat report buttons ───────────────────────────────────────────────────
    "chat_report_button_count": 3,
    "chat_report_button_testids": [
        "pv-unified-card-traditional",
        "pv-unified-card-detailed",
        "pv-unified-card-professional",
    ],
    "chat_report_button_tier_map": {
        "pv-unified-card-traditional":  "traditional_report",
        "pv-unified-card-detailed":     "detailed_report",
        "pv-unified-card-professional": "professional_report",
    },
    "chat_report_button_labels": {
        "pv-unified-card-traditional":  "تقرير تقليدي",
        "pv-unified-card-detailed":     "تقرير تفصيلي",
        "pv-unified-card-professional": "تقرير احترافي",
    },

    # ── Removed from chat ─────────────────────────────────────────────────────
    "seven_report_dropdown_removed_from_chat": True,
    "seven_report_dropdown_chat_testid":      "pv-legacy-seven-report-selector-hidden",
    "seven_report_dropdown_chat_hidden_in_static_html": True,

    "obsolete_pdf_user_button_removed": True,
    "obsolete_pdf_user_button_testid":  "pro-val-unified-generate-user-pdf",
    "obsolete_pdf_user_button_label":   "إصدار تقرير PDF للمستخدم",

    "obsolete_selected_output_button_removed": True,
    "obsolete_selected_output_button_testid":  "pro-val-unified-generate-selected-output",
    "obsolete_selected_output_button_label":   "إصدار المخرج المختار",

    "duplicate_expert_review_section_removed_from_chat": True,
    "duplicate_expert_review_section_heading":            "طلب مراجعة خبير معتمد",

    # ── Preserved at bottom ───────────────────────────────────────────────────
    "authoritative_expert_review_section_preserved": True,
    "authoritative_expert_review_section_testid":    "pro-val-expert-review-request-section",
    "authoritative_expert_review_section_outside_chat": True,

    "authoritative_expert_review_report_selector_testid": "pro-val-cert-report-type",
    "authoritative_expert_review_report_options_count":   7,
    "authoritative_expert_review_report_options": [
        "traditional_report",
        "detailed_report",
        "professional_report",
        "report_review",
        "simulation_report",
        "hbu_report",
        "standards_compliance_report",
    ],

    # ── Normal-user output formats ────────────────────────────────────────────
    "normal_user_pdf_available":   True,
    "normal_user_html_available":  True,
    "normal_user_excel_available": False,
    "user_format_pdf_testid":          "pv-format-label-pdf",
    "user_format_html_view_testid":    "pv-format-label-html-view",
    "user_format_html_download_testid": "pv-format-label-html-download",

    # ── Administrator output formats ──────────────────────────────────────────
    "admin_pdf_available":   True,
    "admin_html_available":  True,
    "admin_excel_available": True,
    "admin_excel_testid":    "pro-val-generate-admin-excel-sheets",
    "admin_excel_hidden_in_static_html": True,
    "admin_excel_revealed_by_role_js":   True,

    # ── Tier mapping ──────────────────────────────────────────────────────────
    "traditional_button_calls_traditional_tier":  True,
    "detailed_button_calls_detailed_tier":        True,
    "professional_button_calls_professional_tier": True,
    "chat_buttons_do_not_invoke_seven_report_review_api": True,

    # ── Backward compat ───────────────────────────────────────────────────────
    "backward_compat_spans_present": True,
    "backward_compat_pdf_user_span_testid":         "pro-val-unified-generate-user-pdf",
    "backward_compat_selected_output_span_testid":  "pro-val-unified-generate-selected-output",
    "backward_compat_expert_review_button_testid":  "pro-val-request-expert-review-button",

    # ── Safety flags ──────────────────────────────────────────────────────────
    "advisory_only":                         True,
    "not_real_training":                     True,
    "report_calculations_unmodified":        True,
    "backend_role_rules_unmodified":         True,
    "download_security_unmodified":          True,
    "pdf_generation_capability_preserved":   True,
    "html_generation_capability_preserved":  True,
    "admin_excel_generation_preserved":      True,
    "seven_report_review_workflow_preserved": True,
    "existing_report_actions_preserved":     True,
}


def get_reporting_chat_three_report_buttons_context() -> dict:
    return dict(REPORTING_CHAT_THREE_REPORT_BUTTONS_CONTEXT)
