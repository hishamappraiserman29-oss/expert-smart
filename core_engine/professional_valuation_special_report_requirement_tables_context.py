# professional_valuation_special_report_requirement_tables_context.py
# advisory_only=True | not_real_training=True | no_commit=True
# Special Report Requirement Tables — Second Key for Four Special Workflows

SPECIAL_REPORT_REQUIREMENT_TABLES_CONTEXT = {
    "special_report_workflows_enabled": True,

    "special_report_types": [
        "report_review_output",
        "simulated_uploaded_report",
        "hbu_analysis_report",
        "standards_compliance_report"
    ],

    "each_special_report_has_dedicated_requirement_table": True,

    "report_review_requirements_enabled": True,
    "simulated_uploaded_report_requirements_enabled": True,
    "hbu_requirements_enabled": True,
    "standards_compliance_requirements_enabled": True,

    "special_reports_removed_from_core_report_selector": True,
    "generic_chat_uploads_for_special_reports_removed": True,

    "completion_validation_enabled": True,
    "minimum_requirement_tracking_enabled": True,

    "expert_review_required": True,
    "backend_keys_preserved": True,
    "legacy_aliases_preserved": True,
    "preservation_pass": True,

    # ── Report Review ────────────────────────────────────────────────────
    "report_review_requirement_table": {
        "output_key": "report_review_output",
        "panel_title": "متطلبات مراجعة التقارير",
        "purpose": "review_existing_report",
        "new_valuation_conclusion": False,
        "completeness_checklist": True,
        "risk_flags": True,
        "methodology_review_group": True,
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
        "minimum_required_fields": [
            "rr-report-name", "rr-report-date", "rr-asset-type",
            "rr-risk-severity", "rr-certifiable"
        ],
        "action_button": "إصدار تقرير مراجعة PDF",
        "advisory_only": True,
    },

    # ── Simulated Uploaded Report ────────────────────────────────────────
    "simulated_uploaded_report_requirement_table": {
        "output_key": "simulated_uploaded_report",
        "panel_title": "متطلبات محاكاة تقرير مرفوع",
        "purpose": "simulate_uploaded_report",
        "real_report_uploaded": False,
        "fake_uploaded_report_claim": False,
        "simulation_scope": True,
        "source_material_status_group": True,
        "groups": [
            "حالة المادة المصدرية",
            "نطاق المحاكاة",
            "أقسام التقرير المفترضة",
            "بيانات الأصل المفترضة",
            "أساليب التقييم المفترضة",
            "الفجوات والمخاطر",
            "نتائج المحاكاة"
        ],
        "minimum_required_fields": ["sim-real-report-exists"],
        "action_button": "إصدار تقرير المحاكاة PDF",
        "advisory_only": True,
    },

    # ── HBU Analysis ─────────────────────────────────────────────────────
    "hbu_analysis_report_requirement_table": {
        "output_key": "hbu_analysis_report",
        "panel_title": "متطلبات تحليل أعلى وأفضل استخدام",
        "purpose": "highest_and_best_use_analysis",
        "is_valuation_report": False,
        "hbu_four_tests": {
            "physically_possible": True,
            "legally_permissible": True,
            "financially_feasible": True,
            "maximally_productive": True,
        },
        "repeatable_alternative_uses": True,
        "repeatable_scenario_matrix": True,
        "groups": [
            "بيانات الأصل والموقع",
            "الاستخدام الحالي",
            "الاستخدامات البديلة",
            "الاختبار الفيزيائي",
            "الاختبار القانوني والتنظيمي",
            "الاختبار المالي",
            "اختبار أعلى إنتاجية",
            "مصفوفة السيناريوهات",
            "نتيجة أعلى وأفضل استخدام"
        ],
        "minimum_required_fields": [
            "hbu-asset-type", "hbu-location",
            "hbu-physically-possible", "hbu-financially-feasible"
        ],
        "action_button": "إصدار تقرير HBU PDF",
        "advisory_only": True,
    },

    # ── Standards Compliance ─────────────────────────────────────────────
    "standards_compliance_report_requirement_table": {
        "output_key": "standards_compliance_report",
        "panel_title": "متطلبات امتثال المعايير",
        "purpose": "advisory_standards_compliance_check",
        "valuation_conclusion_included": False,
        "advisory_compliance_only": True,
        "standards_matrix": True,
        "ivs_matrix": {
            "rows": [
                "Scope of Work", "Basis of Value", "Data and Inputs",
                "Valuation Approach", "Reporting", "Documentation Status"
            ],
            "status_options": ["Addressed", "Partially Addressed", "Missing", "Not Applicable"]
        },
        "uspap_matrix": {
            "rows": [
                "Scope of Work", "Intended Use", "Intended User",
                "Development", "Reporting", "Ethics / Conduct", "Review where applicable"
            ],
            "status_options": ["Addressed", "Partially Addressed", "Missing", "Not Applicable"]
        },
        "rics_matrix": {
            "rows": [
                "Terms of Engagement", "Inspection", "Assumptions",
                "Valuation Approach", "Reporting", "Disclosures", "Professional Review"
            ],
            "status_options": ["Addressed", "Partially Addressed", "Missing", "Not Applicable"]
        },
        "ifrs13_matrix": {
            "rows": [
                "Fair Value Context", "Market Participants",
                "Principal / Most Advantageous Market", "Highest and Best Use",
                "Inputs Hierarchy", "Valuation Technique", "Disclosure Support"
            ],
            "status_options": ["Addressed", "Partially Addressed", "Missing", "Not Applicable"]
        },
        "local_regulatory_matrix": {
            "rows": [
                "FRA Egypt", "GCC References", "Local Standard",
                "Basel III / Collateral Risk", "Internal Policy"
            ],
            "status_options": ["Addressed", "Partially Addressed", "Missing", "Not Applicable"]
        },
        "groups": [
            "المعايير المختارة",
            "نطاق فحص الامتثال",
            "بيانات التقرير أو التقييم",
            "IVS 2025 Compliance Matrix",
            "USPAP Matrix",
            "RICS Red Book 2025 Matrix",
            "IFRS 13 Matrix",
            "المراجع المحلية والتنظيمية",
            "فجوات الامتثال",
            "نتيجة الامتثال الاسترشادية"
        ],
        "minimum_required_fields": ["sc-overall-status"],
        "action_button": "إصدار تقرير امتثال المعايير PDF",
        "advisory_only": True,
    },

    # ── Unified Context Structure ─────────────────────────────────────────
    "unified_context_structure": {
        "enabled": True,
        "selected_special_report_type": None,
        "opened_requirement_table": None,
        "special_report_types": [
            "report_review_output",
            "simulated_uploaded_report",
            "hbu_analysis_report",
            "standards_compliance_report"
        ],
        "requirement_values": {
            "report_review_output": {},
            "simulated_uploaded_report": {},
            "hbu_analysis_report": {},
            "standards_compliance_report": {}
        },
        "completion_status": {
            "report_review_output": {},
            "simulated_uploaded_report": {},
            "hbu_analysis_report": {},
            "standards_compliance_report": {}
        },
        "missing_minimum_requirements": {
            "report_review_output": [],
            "simulated_uploaded_report": [],
            "hbu_analysis_report": [],
            "standards_compliance_report": []
        }
    },

    # ── Safety / Advisory Flags ───────────────────────────────────────────
    "advisory_only": True,
    "not_real_training": True,
    "no_internal_paths": True,
    "ordinary_valuation_unaffected": True,
    "tax_appeal_unaffected": True,
}


def get_special_report_requirement_tables_context() -> dict:
    return dict(SPECIAL_REPORT_REQUIREMENT_TABLES_CONTEXT)
