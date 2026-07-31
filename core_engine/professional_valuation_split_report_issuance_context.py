# professional_valuation_split_report_issuance_context.py
# advisory_only=True | not_real_training=True | no_commit=True
# Split Report Issuance Controls — Core Valuation + Special Report Workflows

SPLIT_REPORT_ISSUANCE_CONTROLS_CONTEXT = {
    "split_controls_enabled": True,

    # ── Core Valuation Report Issuance ──────────────────────────────────────
    "core_report_control_enabled": True,
    "core_report_types": [
        "traditional_report",
        "detailed_report",
        "professional_report"
    ],
    "core_output_formats": [
        "user_pdf",
        "admin_excel"
    ],
    "core_control_location": "below_chat_box",
    "core_advisory_notice_visible": True,
    "core_certification_gate_required": True,

    # ── Special Report Workflows ─────────────────────────────────────────────
    "special_report_control_enabled": True,
    "special_report_types": [
        "report_review_output",
        "simulated_uploaded_report",
        "hbu_analysis_report",
        "standards_compliance_report"
    ],
    "special_reports_have_dedicated_requirement_tables": True,
    "generic_chat_upload_for_special_reports_removed": True,

    # ── Legacy / Backward Compatibility ─────────────────────────────────────
    "legacy_seven_report_selector_removed_as_primary": True,
    "duplicate_lower_pdf_chat_buttons_removed": True,
    "backend_keys_preserved": True,
    "legacy_aliases_preserved": True,

    # ── Dedicated Requirement Tables ─────────────────────────────────────────
    "report_review_output_requirement_table": {
        "groups": [
            "بيانات التقرير محل المراجعة",
            "نطاق المراجعة",
            "اكتمال محتوى التقرير",
            "مراجعة أساليب التقييم",
            "مراجعة البيانات والمدخلات",
            "مراجعة الافتراضات والقيود",
            "مراجعة الامتثال للمعايير",
            "ملاحظات المراجع ومخاطر التقرير"
        ],
        "new_valuation_conclusion": False,
        "completeness_checklist": True,
        "risk_flags": True,
        "action_button": "إصدار تقرير مراجعة PDF",
        "output_key": "report_review_output"
    },
    "simulated_uploaded_report_requirement_table": {
        "groups": [
            "حالة المادة المصدرية",
            "نطاق المحاكاة",
            "أقسام التقرير المفترضة",
            "بيانات الأصل المفترضة",
            "أساليب التقييم المفترضة",
            "الفجوات والمخاطر",
            "نتائج المحاكاة"
        ],
        "real_report_uploaded": False,
        "fake_uploaded_report_claim": False,
        "simulation_scope": True,
        "action_button": "إصدار تقرير المحاكاة PDF",
        "output_key": "simulated_uploaded_report"
    },
    "hbu_analysis_report_requirement_table": {
        "groups": [
            "بيانات الأصل والموقع",
            "الاستخدام الحالي",
            "الاستخدامات البديلة",
            "الاختبار الفيزيائي",
            "الاختبار القانوني والتنظيمي",
            "الاختبار المالي",
            "أعلى إنتاجية",
            "مصفوفة السيناريوهات",
            "نتيجة أعلى وأفضل استخدام"
        ],
        "hbu_four_tests": [
            "physically_possible",
            "legally_permissible",
            "financially_feasible",
            "maximally_productive"
        ],
        "is_valuation_report": False,
        "action_button": "إصدار تقرير HBU PDF",
        "output_key": "hbu_analysis_report"
    },
    "standards_compliance_report_requirement_table": {
        "groups": [
            "المعايير المختارة",
            "نطاق فحص الامتثال",
            "بيانات التقرير أو التقييم",
            "IVS 2025 Compliance Matrix",
            "RICS & USPAP Compliance",
            "IFRS 13",
            "المراجع المحلية والتنظيمية",
            "فجوات الامتثال",
            "نتيجة الامتثال الاسترشادية"
        ],
        "standards_matrix": True,
        "valuation_conclusion_included": False,
        "advisory_compliance_only": True,
        "action_button": "إصدار تقرير امتثال المعايير PDF",
        "output_key": "standards_compliance_report"
    },

    # ── Safety / Advisory Flags ───────────────────────────────────────────────
    "advisory_only": True,
    "not_real_training": True,
    "no_internal_paths": True,
    "preservation_pass": True,
    "ordinary_valuation_unaffected": True,
    "tax_appeal_unaffected": True
}


def get_split_report_issuance_controls_context() -> dict:
    return dict(SPLIT_REPORT_ISSUANCE_CONTROLS_CONTEXT)
