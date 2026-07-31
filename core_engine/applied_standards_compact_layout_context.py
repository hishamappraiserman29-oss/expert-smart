"""
Phase CS4 — Section 4.1 Applied Valuation Standards Compact Horizontal Chips
Backend context registry for the compact layout change.

advisory_only=True | not_real_training=True | no_commit=True
"""

applied_standards_compact_layout_context: dict = {
    # Layout descriptor
    "section": "4.1",
    "compact_horizontal_layout_enabled": True,
    "standards_display_mode": "horizontal_chips",
    "wraps_to_one_or_two_rows": True,

    # Preservation audit
    "standards_preserved": True,
    "deleted_standards": [],
    "backend_keys_preserved": True,

    # Keys in use (values on name="selected_standards" checkboxes)
    "standard_keys": [
        "uspap",
        "ivs_2025",
        "rics_red_book_2025",
        "ifrs_13",
        "gcc_standards",
        "fra_egypt",
        "custom_local_standard",
        "basel_iii",
    ],

    # Standard aliases preserved in legacy hidden <select>
    "legacy_alias_keys": [
        "ivs_2022",
        "rics_red_book",
        "egyptian_standard",
        "gcc_standard",
        "local_regulatory",
        "basel",
        "basel3",
    ],

    # Category metadata (preserved as data-std-category attributes on chips)
    "categories": {
        "professional_valuation_standard": ["uspap", "ivs_2025", "rics_red_book_2025"],
        "financial_reporting": ["ifrs_13"],
        "local_regulatory": ["gcc_standards", "fra_egypt", "custom_local_standard"],
        "risk_banking_collateral": ["basel_iii"],
    },

    # Classification correctness
    "standard_classifications": {
        "uspap": "professional_valuation_standard",
        "ivs_2025": "professional_valuation_standard",
        "rics_red_book_2025": "professional_valuation_standard",
        "ifrs_13": "financial_reporting_accounting",
        "gcc_standards": "local_regulatory",
        "fra_egypt": "local_regulatory",
        "custom_local_standard": "local_regulatory",
        "basel_iii": "risk_banking_collateral",  # NOT a pure valuation standard
    },
    "basel_iii_is_pure_valuation_standard": False,
    "ifrs_13_is_financial_reporting_context": True,

    # Advisory notice
    "advisory_notice_preserved": True,
    "duplicate_advisory_notice_removed": True,
    "advisory_notice_text": (
        "الاختيار استرشادي — لا يُصدر حكم امتثال نهائي إلا بعد مراجعة خبير مؤهل وبوابة الاعتماد."
    ),

    # Visual categories
    "visual_categories_compacted": True,
    "category_headers_removed_from_dom": True,
    "category_metadata_preserved_as_data_attributes": True,

    # Chip order (CS4 spec)
    "chip_display_order": [
        "uspap",
        "ivs_2025",
        "rics_red_book_2025",
        "ifrs_13",
        "gcc_standards",
        "fra_egypt",
        "custom_local_standard",
        "basel_iii",
    ],

    # Impact on other sections
    "section_2_requirement_tables_unaffected": True,
    "section_3_purpose_scope_unaffected": True,
    "chat_box_unaffected": True,
    "pdf_excel_outputs_unaffected": True,
    "certification_gate_unaffected": True,

    # Governance
    "advisory_only": True,
    "not_real_training": True,
}
