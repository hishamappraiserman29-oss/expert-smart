"""
professional_valuation_core_report_profiles.py
Report type definitions, section lists, depth rules, and method coverage
for the three core Professional Valuation reports.
advisory_only=True | not_real_training=True
"""
from __future__ import annotations

REPORT_TYPES = ["traditional_report", "detailed_report", "professional_report"]

REPORT_LABELS = {
    "traditional_report": "Traditional Valuation Report",
    "detailed_report": "Detailed Valuation Report",
    "professional_report": "Professional Valuation Report",
}

ARABIC_LABELS = {
    "traditional_report": "تقرير تقليدي",
    "detailed_report": "تقرير تفصيلي",
    "professional_report": "تقرير احترافي",
}

MIN_PAGES = {
    "traditional_report": 8,
    "detailed_report": 14,
    "professional_report": 20,
}

SECTIONS: dict[str, list[str]] = {
    "traditional_report": [
        "Cover Page",
        "Executive Summary",
        "Purpose and Scope",
        "Asset Identification",
        "Data Quality and Completeness",
        "Applied Standards",
        "Traditional Valuation Methods Overview",
        "Market Approach",
        "Income Approach",
        "Cost Approach",
        "AVM-Assisted Indication",
        "Reconciliation",
        "Value Conclusion or Missing-Data Blocker",
        "Assumptions and Limiting Conditions",
        "Advisory / Expert Review Notice",
        "Appendices",
    ],
    "detailed_report": [
        "Cover Page",
        "Executive Summary",
        "Instruction and Assignment Summary",
        "Purpose, Intended Use, and Intended Users",
        "Scope of Work",
        "Asset Identification",
        "Legal and Document Review",
        "Site and Location Analysis",
        "Building / Component Breakdown",
        "Requirement Completion Summary",
        "Data Quality and Completeness",
        "Market Evidence Summary",
        "Comparable Sales Grid",
        "Adjustment Matrix",
        "Income Data and Operating Assumptions",
        "Cost Inputs and Depreciation Assumptions",
        "Market Approach Calculation",
        "Income Approach Calculation",
        "Cost Approach Calculation",
        "DCF Summary",
        "Sensitivity Snapshot",
        "Risk Notes",
        "Reconciliation",
        "Assumptions and Limiting Conditions",
        "Appendices",
    ],
    "professional_report": [
        "Professional Cover Page",
        "Executive Summary",
        "Valuation Instruction and Scope of Work",
        "Basis of Value and Premise of Value",
        "Intended Use and Intended Users",
        "Asset Identification and Ownership Summary",
        "Legal / Document Review",
        "Location and Market Context",
        "Asset Requirement Completion Dashboard",
        "Data Quality and Completeness",
        "Component / Building / Use Breakdown",
        "Applied Standards Matrix",
        "Data and Inputs Register",
        "Valuation Method Selection Matrix",
        "Market Approach",
        "Income Approach",
        "Cost Approach",
        "Discounted Cash Flow Analysis",
        "Residual / Development Method",
        "Highest and Best Use Summary",
        "Scenario Analysis",
        "Sensitivity Analysis",
        "Risk-Adjusted Valuation Discussion",
        "AVM-Assisted Indication and Reliability",
        "Weighted Reconciliation Model",
        "Value Conclusion or Blocker",
        "Assumptions and Limiting Conditions",
        "Expert Review and Certification Gate",
        "Appendices",
    ],
}

SHARED_SECTIONS: set[str] = {
    "Cover Page",
    "Professional Cover Page",
    "Executive Summary",
    "Purpose and Scope",
    "Assumptions and Limiting Conditions",
    "Advisory / Expert Review Notice",
    "Appendices",
}

METHOD_COVERAGE: dict[str, dict[str, bool]] = {
    "traditional_report": {
        "market_approach": True,
        "income_approach": True,
        "cost_approach": True,
        "avm_assisted_indication": True,
        "dcf_full": False,
        "hbu_full": False,
        "scenario_analysis_full": False,
        "sensitivity_analysis_full": False,
        "risk_adjusted_valuation": False,
        "weighted_reconciliation": False,
    },
    "detailed_report": {
        "market_approach": True,
        "income_approach": True,
        "cost_approach": True,
        "avm_assisted_indication": False,
        "dcf_summary": True,
        "sensitivity_snapshot": True,
        "risk_notes": True,
        "legacy_excel_style_detail": True,
        "hbu_full": False,
        "scenario_analysis_full": False,
        "risk_adjusted_valuation": False,
        "weighted_reconciliation": False,
    },
    "professional_report": {
        "market_approach": True,
        "income_approach": True,
        "cost_approach": True,
        "dcf_analysis": True,
        "hbu_summary": True,
        "scenario_analysis": True,
        "sensitivity_analysis": True,
        "risk_adjusted_valuation": True,
        "avm_assisted_indication": True,
        "weighted_reconciliation": True,
        "professional_depth_above_detailed": True,
    },
}

PRACTICAL_EXAMPLES: dict[str, dict[str, bool]] = {
    "traditional_report": {
        "market_adjustment_example": True,
        "income_capitalization_example": True,
        "cost_depreciation_example": True,
        "avm_confidence_example": True,
    },
    "detailed_report": {
        "comparable_adjustment_grid": True,
        "cap_rate_sensitivity_snapshot": True,
        "dcf_mini_table": True,
        "depreciation_example": True,
        "reconciliation_weighting_example": True,
    },
    "professional_report": {
        "method_selection_matrix": True,
        "dcf_projection_table": True,
        "scenario_table": True,
        "sensitivity_table": True,
        "risk_scoring_matrix": True,
        "avm_reliability_discussion": True,
        "weighted_reconciliation_scorecard": True,
    },
}

# Context for frontend / JS integration
core_report_profiles_context = {
    "advisory_only": True,
    "not_real_training": True,
    "report_types": REPORT_TYPES,
    "report_labels": REPORT_LABELS,
    "arabic_labels": ARABIC_LABELS,
    "min_pages": MIN_PAGES,
    "section_counts": {rt: len(secs) for rt, secs in SECTIONS.items()},
    "traditional_less_detailed_than_detailed": True,
    "detailed_less_detailed_than_professional": True,
    "professional_is_highest_depth": True,
    "pdf_language": "English",
    "reports_are_distinct": True,
}


def get_unique_sections(report_type: str) -> list[str]:
    order = REPORT_TYPES
    idx = order.index(report_type)
    all_lower: set[str] = set()
    for lower in order[:idx]:
        all_lower.update(SECTIONS[lower])
    return [s for s in SECTIONS[report_type] if s not in all_lower and s not in SHARED_SECTIONS]
