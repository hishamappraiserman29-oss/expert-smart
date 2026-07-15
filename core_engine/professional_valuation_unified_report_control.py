"""
Professional Valuation — Unified Report Generation Control Module
=================================================================
Defines the canonical "تحليل وإصدار التقارير" control context:
- One visible page-level dropdown with exactly 7 report/action types
- Alias mapping from old payload keys to the canonical unified_report_action
- Output permissions context

Rules enforced here:
- advisory_only = True always
- admin_excel_visible_to_current_user = False (protected)
- no_real_training = True (simulation flag)
- no internal file paths exposed
"""

from __future__ import annotations
from typing import Any

# ── Canonical 7 report/action options ─────────────────────────────────────

UNIFIED_REPORT_ACTION_OPTIONS: list[dict[str, str]] = [
    {
        "key":      "traditional_report",
        "label_ar": "تقرير تقليدي",
        "label_en": "Traditional Report",
    },
    {
        "key":      "detailed_report",
        "label_ar": "تقرير تفصيلي",
        "label_en": "Detailed Report",
    },
    {
        "key":      "professional_report",
        "label_ar": "تقرير احترافي",
        "label_en": "Professional Report",
    },
    {
        "key":      "simulated_uploaded_report",
        "label_ar": "محاكاة تقرير مرفوع",
        "label_en": "Simulated Uploaded Report",
    },
    {
        "key":      "report_review_output",
        "label_ar": "مراجعة تقرير",
        "label_en": "Report Review Output",
    },
    {
        "key":      "hbu_analysis_report",
        "label_ar": "تقرير تحليل أعلى وأفضل استخدام",
        "label_en": "Highest and Best Use Analysis Report",
    },
    {
        "key":      "standards_compliance_report",
        "label_ar": "تقرير امتثال المعايير",
        "label_en": "Standards Compliance Report",
    },
]

# ── Alias mapping: old payload keys → canonical unified_report_action ──────

REPORT_ACTION_ALIAS_MAPPING: dict[str, str] = {
    "report_type":                     "unified_report_action",
    "report_action":                   "unified_report_action",
    "selected_report_type":            "unified_report_action",
    "selected_report_action":          "unified_report_action",
    "output_type":                     "unified_report_action",
    "نوع التقرير أو الإجراء":          "unified_report_action",
    "تحليل وإصدار التقرير":            "unified_report_action",
    "تحليل وإصدار التقارير":           "unified_report_action",
}

# ── Backend-compatible report type map for PDF generation ─────────────────
# These 7 frontend actions map to valid backend report_type values.
# Actions without a direct PDF route fall back to professional_report.

UNIFIED_TO_BACKEND_REPORT_TYPE_MAP: dict[str, str] = {
    "traditional_report":          "traditional_report",
    "detailed_report":             "detailed_report",
    "professional_report":         "professional_report",
    "simulated_uploaded_report":   "simulated_uploaded_report",
    "report_review_output":        "professional_report",
    "hbu_analysis_report":         "professional_report",
    "standards_compliance_report": "professional_report",
}

# ── Required context structure ─────────────────────────────────────────────

UNIFIED_REPORT_GENERATION_CONTROL_CONTEXT: dict[str, Any] = {
    "single_visible_control":                   True,
    "canonical_label_ar":                       "تحليل وإصدار التقارير",
    "canonical_key":                            "unified_report_action",
    "canonical_testid":                         "pro-val-unified-analyze-generate-reports-select",
    "visible_options_count":                    7,
    "visible_options":                          [o["key"] for o in UNIFIED_REPORT_ACTION_OPTIONS],
    "legacy_aliases_preserved":                 True,
    "removed_duplicate_visible_controls":       True,
    "removed_labels": [
        "نوع التقرير أو الإجراء",
        "تحليل وإصدار التقرير",
    ],
    "excel_pattern_is_not_main_report_selector": True,
    "applies_to_whole_professional_valuation_page": True,
    "uses_unified_professional_valuation_page_context": True,
    "advisory_only":                            True,
    "no_internal_paths":                        True,
}


def build_unified_report_generation_control_context(
    selected_unified_report_action: str = "traditional_report",
    pdf_permissions_enabled: bool = True,
    admin_excel_visible_to_current_user: bool = False,
) -> dict[str, Any]:
    """
    Build the full unified report generation control context for a request.

    Parameters
    ----------
    selected_unified_report_action
        The value from the unified dropdown (one of the 7 canonical keys).
    pdf_permissions_enabled
        Whether PDF generation is available for this request.
    admin_excel_visible_to_current_user
        Always False for non-admin; only True for authenticated admins.
    """
    option_keys = [o["key"] for o in UNIFIED_REPORT_ACTION_OPTIONS]
    effective_action = (
        selected_unified_report_action
        if selected_unified_report_action in option_keys
        else "traditional_report"
    )
    backend_report_type = UNIFIED_TO_BACKEND_REPORT_TYPE_MAP.get(
        effective_action, "professional_report"
    )
    return {
        **UNIFIED_REPORT_GENERATION_CONTROL_CONTEXT,
        "selected_unified_report_action":            effective_action,
        "backend_report_type_for_pdf":               backend_report_type,
        "pdf_generation_uses_unified_report_action": True,
        "excel_generation_uses_unified_report_action": True,
        "output_permissions": {
            "can_generate_user_pdf":       pdf_permissions_enabled,
            "can_generate_admin_excel":    admin_excel_visible_to_current_user,
            "admin_excel_visible_to_current_user": admin_excel_visible_to_current_user,
            "advisory_only":               True,
        },
        "report_action_alias_mapping":              REPORT_ACTION_ALIAS_MAPPING,
    }


def resolve_unified_report_action_from_payload(payload: dict[str, Any]) -> str:
    """
    Read unified_report_action (or its legacy aliases) from a request payload.

    Checks, in priority order:
    1. unified_report_action
    2. report_action
    3. selected_report_action
    4. report_type
    Returns 'traditional_report' as default.
    """
    for key in ("unified_report_action", "report_action",
                "selected_report_action", "report_type"):
        val = payload.get(key, "")
        if val:
            return str(val)
    return "traditional_report"
