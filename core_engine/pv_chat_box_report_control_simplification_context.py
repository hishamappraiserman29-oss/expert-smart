# pv_chat_box_report_control_simplification_context.py
# advisory_only=True | not_real_training=True | no_commit=True
# Chat Box Report Control Simplification — Remove Upload Clips & Separate Buttons;
# Core report chip click now generates both PDF + Excel automatically.

CHAT_BOX_REPORT_CONTROL_SIMPLIFICATION_CONTEXT = {
    "core_report_click_generates_both_outputs": True,

    "core_report_types": [
        "traditional_report",
        "detailed_report",
        "professional_report",
    ],

    "separate_user_pdf_button_removed": True,
    "separate_admin_excel_button_removed": True,
    "send_to_chat_button_removed": True,

    "simulation_upload_clip_removed_from_chat_box": True,
    "report_review_upload_clip_removed_from_chat_box": True,

    "special_reports_managed_by_dedicated_requirement_tables": True,

    "pdf_generation_capability_preserved": True,
    "admin_excel_generation_capability_preserved": True,

    "special_report_keys_preserved": True,
    "legacy_aliases_preserved": True,
    "preservation_pass": True,

    # ── Core report output bundle context ────────────────────────────────────
    "core_report_output_bundle_context": {
        "enabled": True,
        "trigger_mode": "click_report_type_generates_pdf_and_excel",
        "selected_report_type": None,
        "generated_outputs": {
            "user_pdf": {
                "requested": False,
                "generated": False,
                "file_name": None,
                "file_exists": False,
                "blocker": None,
            },
            "admin_excel": {
                "requested": False,
                "generated": False,
                "file_name": None,
                "file_exists": False,
                "blocker": None,
            },
        },
        "separate_pdf_button_removed": True,
        "separate_excel_button_removed": True,
    },

    # ── Unified context update ────────────────────────────────────────────────
    "unified_context_report_issuance_core_reports": {
        "enabled": True,
        "trigger_mode": "report_type_click_generates_both_outputs",
        "report_types": [
            "traditional_report",
            "detailed_report",
            "professional_report",
        ],
        "separate_output_format_buttons_visible": False,
        "removed_buttons": [
            "إصدار PDF للمستخدم",
            "إصدار شيت Excel للأدمن",
            "إرسال للشات",
        ],
        "chat_upload_shortcuts_removed": [
            "simulation_report_upload",
            "report_review_upload",
        ],
        "last_generated_bundle": {
            "report_type": None,
            "user_pdf": {},
            "admin_excel": {},
        },
    },

    "unified_context_report_issuance_special_reports": {
        "managed_by_dedicated_requirement_tables": True,
        "chat_upload_shortcuts_removed": True,
    },

    # ── Safety / Advisory Flags ───────────────────────────────────────────────
    "advisory_only": True,
    "not_real_training": True,
    "no_internal_paths": True,
    "ordinary_valuation_unaffected": True,
    "tax_appeal_unaffected": True,
}


def get_chat_box_report_control_simplification_context() -> dict:
    return dict(CHAT_BOX_REPORT_CONTROL_SIMPLIFICATION_CONTEXT)
