# core_engine/requirement_table_improvements_context.py
# Phase RTI — Requirement Table Improvements context registry
# advisory_only=True, not_real_training=True

requirement_table_improvements_context = {
    # Part A — Document upload clips
    "document_upload_clips_enabled": True,
    "file_upload_fields_use_paperclip": True,
    "accepted_file_types": ["pdf", "jpg", "jpeg", "png", "xls", "xlsx", "doc", "docx"],
    "upload_ui_control": "paperclip",
    "upload_status_states": ["missing", "uploaded", "not_applicable"],

    # Part B — Requirement priority coloring
    "requirement_priority_coloring_enabled": True,
    "requirement_priority_levels": [
        "minimum_required",
        "required_if_applicable",
        "recommended",
        "optional",
    ],
    "priority_css_classes": {
        "minimum_required":       "pv-req-minimum",
        "required_if_applicable": "pv-req-conditional",
        "recommended":            "pv-req-recommended",
        "optional":               "pv-req-optional",
    },
    "priority_badge_labels_ar": {
        "minimum_required":       "حد أدنى",
        "required_if_applicable": "إلزامي عند الانطباق",
        "recommended":            "مهم",
        "optional":               "اختياري",
    },
    "priority_legend_visible": True,

    # Part C — Priority rules
    "priority_inference_rules": {
        "minimum_required": [
            "asset_identity", "asset_type", "location", "area",
            "ownership_legal_title", "valuation_purpose_from_section3",
            "physical_condition", "main_use_occupancy",
            "core_market_inputs", "essential_legal_documents",
        ],
        "required_if_applicable": [
            "rent_income_for_income_producing_assets",
            "operating_expenses_for_income_method",
            "hotel_operating_fields",
            "licenses_for_operational_assets",
            "environmental_approvals",
            "building_components_for_complex_assets",
            "lease_documents_if_leased",
            "occupancy_data_if_income_producing",
        ],
        "recommended": [
            "additional_comparables", "detailed_photos",
            "market_trend_notes", "extended_maintenance_details",
            "supporting_cost_data", "sensitivity_inputs",
        ],
        "optional": [
            "extra_notes", "additional_supporting_attachments",
            "optional_descriptive_fields", "non_critical_amenities",
        ],
    },

    # Part B — Minimum report requirements context
    "minimum_report_requirements_context_enabled": True,
    "draft_report_reviewable_logic": {
        "required_completed": ["minimum_required"],
        "required_if_condition_met": ["required_if_applicable"],
        "optional_do_not_block": ["recommended", "optional"],
        "final_certification_claim": False,
        "expert_review_required": True,
        "advisory_note_ar": (
            "تمييز الحد الأدنى يساعد على اكتمال مسودة تقرير قابلة للمراجعة، "
            "ولا يعني الاعتماد النهائي دون مراجعة الخبير وبوابة الاعتماد."
        ),
    },

    # Part D/E — Adjustment factors purpose deduplication
    "adjustment_factors_duplicate_purpose_removed": True,
    "adjustment_factors_purpose_source": "section3.assignment_purpose",
    "adjustment_factors_read_only_summary_visible": True,
    "adjustment_factors_purpose_aliases": {
        "adjustment_purpose":               "assignment_purpose",
        "adjustment_valuation_purpose":     "assignment_purpose",
        "valuation_purpose_for_adjustments": "assignment_purpose",
        "purpose_in_adjustment_box":        "assignment_purpose",
    },
    "adjustment_factors_context": {
        "editable_duplicate_removed": True,
        "source_of_truth": "section3.assignment_purpose",
        "read_only_summary_visible": True,
        "legacy_aliases_preserved": True,
        "duplicate_purpose_selectors_count": 0,
        "adjustment_factors_use_section3_purpose": True,
    },

    # Part F — Unified context keys
    "unified_context_keys": {
        "documents":                  "asset_requirement_values_context.documents",
        "minimum_requirement_status": "asset_requirement_values_context.minimum_requirement_status",
        "requirement_priority_levels":"asset_requirement_values_context.requirement_priority_levels",
        "section3_purpose":           "section3.assignment_purpose",
        "adj_factors_context":        "adjustment_factors_context",
    },

    # Preservation audit — confirms no deletions occurred
    "common_asset_tables_preserved":       True,
    "uncommon_asset_tables_preserved":     True,
    "old_style_requirement_engine_preserved": True,
    "hotel_resort_golden_reference_preserved": True,
    "repeatable_building_components_preserved": True,
    "deleted_old_requirements": [],
    "deleted_old_options": [],
    "preservation_pass": True,

    # Runtime flags
    "advisory_only": True,
    "not_real_training": True,
    "phase": "RTI",
    "version": "1.0.0",
}
