# -*- coding: utf-8 -*-
"""
professional_valuation_output_matrix.py
Output matrix for Professional Valuation: determines which workbook sheets and
PDF sections to generate based on (report_type, valuation_purpose, property_type).

Rules:
  - No fabricated data, no external APIs, no OCR, no Qdrant, no RAG.
  - No internal paths exposed.
  - This module is IMPORTED by workbook/PDF generators — it does not generate.
"""
from __future__ import annotations

# ══════════════════════════════════════════════════════════════════════════════
# Valid enum values
# ══════════════════════════════════════════════════════════════════════════════

VALID_REPORT_TYPES = frozenset({
    "traditional_report",
    "detailed_report",
    "professional_report",
})

REPORT_TYPE_LABELS = {
    "traditional_report":  "تقرير تقليدي",
    "detailed_report":     "تقرير تفصيلي",
    "professional_report": "تقرير احترافي",
}

VALID_VALUATION_PURPOSES = frozenset({
    "market_value",
    "rental_value",
    "financing_mortgage",
    "court_legal",
    "investment_decision",
    "internal_advisory",
    "environmental_impact",
    "special_purpose",
})

VALUATION_PURPOSE_LABELS = {
    "market_value":         "القيمة السوقية",
    "rental_value":         "القيمة الإيجارية",
    "financing_mortgage":   "تمويل / رهن عقاري",
    "court_legal":          "تقاضٍ / قضائي",
    "investment_decision":  "قرار استثماري",
    "internal_advisory":    "استشارة داخلية",
    "environmental_impact": "أثر بيئي",
    "special_purpose":      "غرض خاص",
}

VALID_PROPERTY_TYPES = frozenset({
    "residential_apartment",
    "residential_villa",
    "administrative_office",
    "retail_shop",
    "land",
    "industrial_factory",
    "warehouse",
    "mixed_use",
    "special_purpose_asset",
})

PROPERTY_TYPE_LABELS = {
    "residential_apartment": "شقة سكنية",
    "residential_villa":     "فيلا سكنية",
    "administrative_office": "مكتب إداري",
    "retail_shop":           "محل تجاري",
    "land":                  "أرض",
    "industrial_factory":    "مصنع / صناعي",
    "warehouse":             "مستودع",
    "mixed_use":             "متعدد الاستخدامات",
    "special_purpose_asset": "أصل ذو غرض خاص",
}

# ══════════════════════════════════════════════════════════════════════════════
# Expert workbook sheet membership
# ══════════════════════════════════════════════════════════════════════════════

# ALWAYS included regardless of report_type
_EXPERT_CORE = frozenset({
    "ملخص المسودة",
    "بيانات الطلب",
    "بيانات العقار",
    "المستندات والمصادر",
    "تحليل الطرق",
    "التوفيق المبدئي",
    "بوابات الاعتماد",
    "سجل المخرجات",
    "مقدمة ونطاق التقييم",
    "الافتراضات والقيود",
    "مصادر الأسعار",
    "التوصية النهائية",
    "بيان الامتثال",
    "الإفصاحات المهنية",
})

# Added for detailed_report and professional_report
_EXPERT_DETAILED = frozenset({
    "المقارنات",
    "طريقة مقارنة البيوع",
    "طريقة الدخل",
    "التدفقات النقدية DCF",
    "طريقة التكلفة",
    "قيمة الأرض",
    "تفصيل الإهلاك",
    "القيمة الإيجارية",
    "مقارنات إيجارية",
    "توفيق القيمة الإيجارية",
    "تحليل مخاطر DCF",
    "سيناريوهات What-If",
    "شراء أم إيجار",
    "نطاق الثقة وعدم اليقين",
    "دعم التعديلات",
    "تحليل الاستدامة ESG",
    "تقييم الأثر البيئي",
    "مؤشرات تكلفة البناء",
    "مصفوفة المخاطر",
    "اختبار اتساق الطرق",
    "حوكمة مصادر البيانات",
    "خارطة طريق الاعتماد",
    "قائمة فحص الاعتماد",
})

# Added for professional_report only (governance + expert internal)
_EXPERT_PROFESSIONAL = frozenset({
    "HBU",
    "الفحص القانوني",
    "ESG",
    "SWOT",
    "مراجعة الخبير",
    "ملاحظات داخلية",
})

# ══════════════════════════════════════════════════════════════════════════════
# Final workbook sheet membership
# ══════════════════════════════════════════════════════════════════════════════

_FINAL_CORE = frozenset({
    "غلاف التقرير",
    "ملخص الاعتماد",
    "نطاق العمل",
    "بيانات العقار",
    "المستندات المعتمدة",
    "مصادر البيانات",
    "تحليل الطرق",
    "التوفيق النهائي",
    "التوصية النهائية",
    "مقدمة ونطاق التقييم",
    "الافتراضات والقيود",
    "مصادر الأسعار",
    "بيان الامتثال",
    "الإفصاحات المهنية",
    "لوحة امتثال التقييم",
})

_FINAL_DETAILED = frozenset({
    "المقارنات المعتمدة",
    "دعم التعديلات",
    "طريقة مقارنة البيوع",
    "طريقة الدخل",
    "التدفقات النقدية DCF",
    "طريقة التكلفة",
    "قيمة الأرض",
    "تفصيل الإهلاك",
    "القيمة الإيجارية",
    "سيناريوهات الحساسية",
    "نطاق الثقة وعدم اليقين",
    "تأثير ESG والمخاطر المناخية",
    "تقييم الأثر البيئي",
    "مؤشرات تكلفة البناء",
    "مصفوفة المخاطر",
    "اختبار اتساق الطرق",
    "حوكمة مصادر البيانات",
    "الملحق — تفاصيل الطرق",
    "الملحق — المقارنات التفصيلية",
})

_FINAL_PROFESSIONAL = frozenset({
    "تحليل HBU",
    "الفحص القانوني",
    "ESG والمخاطر المناخية",
    "تحليل SWOT",
    "مراجعة النظراء",
    "توقيع واعتماد الخبير",
    "سجل التدقيق",
    "موانع الاعتماد السابقة",
    "المخرجات والنسخ",
})

# ══════════════════════════════════════════════════════════════════════════════
# Purpose-specific extra sheets (additive — applied on top of report_type base)
# ══════════════════════════════════════════════════════════════════════════════

_PURPOSE_EXPERT_EXTRA: dict[str, frozenset] = {
    "rental_value": frozenset({
        "القيمة الإيجارية",
        "مقارنات إيجارية",
        "توفيق القيمة الإيجارية",
    }),
    "investment_decision": frozenset({
        "التدفقات النقدية DCF",
        "سيناريوهات What-If",
        "شراء أم إيجار",
        "تحليل مخاطر DCF",
        "مصفوفة المخاطر",
        "SWOT",
    }),
    "financing_mortgage": frozenset({
        "مصفوفة المخاطر",
        "الفحص القانوني",
        "نطاق الثقة وعدم اليقين",
    }),
    "court_legal": frozenset({
        "الفحص القانوني",
        "حوكمة مصادر البيانات",
        "اختبار اتساق الطرق",
        "مراجعة الخبير",
    }),
    "environmental_impact": frozenset({
        "تحليل الاستدامة ESG",
        "تقييم الأثر البيئي",
        "ESG",
        "مصفوفة المخاطر",
    }),
    "market_value": frozenset({
        "المقارنات",
        "طريقة مقارنة البيوع",
        "طريقة التكلفة",
    }),
    "special_purpose": frozenset({
        "طريقة التكلفة",
        "قيمة الأرض",
        "تفصيل الإهلاك",
        "الافتراضات والقيود",
    }),
    "internal_advisory": frozenset({"ملاحظات داخلية"}),
}

_PURPOSE_FINAL_EXTRA: dict[str, frozenset] = {
    "rental_value": frozenset({
        "القيمة الإيجارية",
    }),
    "investment_decision": frozenset({
        "التدفقات النقدية DCF",
        "سيناريوهات الحساسية",
        "مصفوفة المخاطر",
        "تحليل SWOT",
    }),
    "financing_mortgage": frozenset({
        "مصفوفة المخاطر",
        "الفحص القانوني",
    }),
    "court_legal": frozenset({
        "الفحص القانوني",
        "حوكمة مصادر البيانات",
        "سجل التدقيق",
    }),
    "environmental_impact": frozenset({
        "تأثير ESG والمخاطر المناخية",
        "تقييم الأثر البيئي",
        "ESG والمخاطر المناخية",
    }),
    "market_value": frozenset({
        "المقارنات المعتمدة",
        "طريقة مقارنة البيوع",
        "طريقة التكلفة",
    }),
    "special_purpose": frozenset({
        "طريقة التكلفة",
        "قيمة الأرض",
    }),
}

# ══════════════════════════════════════════════════════════════════════════════
# Asset-type specific extra sheets (additive)
# ══════════════════════════════════════════════════════════════════════════════

_ASSET_EXPERT_EXTRA: dict[str, frozenset] = {
    "land": frozenset({
        "قيمة الأرض",
        "HBU",
    }),
    "industrial_factory": frozenset({
        "طريقة التكلفة",
        "تفصيل الإهلاك",
        "تحليل الاستدامة ESG",
        "تقييم الأثر البيئي",
    }),
    "mixed_use": frozenset({
        "طريقة مقارنة البيوع",
        "طريقة الدخل",
        "التوفيق المبدئي",
    }),
    "special_purpose_asset": frozenset({
        "طريقة التكلفة",
        "قيمة الأرض",
        "الافتراضات والقيود",
    }),
    "residential_villa": frozenset({
        "قيمة الأرض",
        "تفصيل الإهلاك",
    }),
}

_ASSET_FINAL_EXTRA: dict[str, frozenset] = {
    "land": frozenset({
        "قيمة الأرض",
        "تحليل HBU",
    }),
    "industrial_factory": frozenset({
        "طريقة التكلفة",
        "تفصيل الإهلاك",
        "تأثير ESG والمخاطر المناخية",
        "تقييم الأثر البيئي",
    }),
    "mixed_use": frozenset({
        "المقارنات المعتمدة",
        "التوفيق النهائي",
    }),
    "special_purpose_asset": frozenset({
        "طريقة التكلفة",
        "قيمة الأرض",
    }),
}

# ══════════════════════════════════════════════════════════════════════════════
# Required methods by purpose + asset type
# ══════════════════════════════════════════════════════════════════════════════

_REQUIRED_METHODS_BY_PURPOSE: dict[str, list] = {
    "market_value":         ["sales_comparison", "cost_approach"],
    "rental_value":         ["rental_comparison", "direct_capitalization"],
    "financing_mortgage":   ["market_value", "risk_analysis"],
    "court_legal":          ["sales_comparison", "cost_approach"],
    "investment_decision":  ["income_approach", "dcf", "sensitivity"],
    "internal_advisory":    ["method_summary"],
    "environmental_impact": ["esg_assessment", "environmental_impact"],
    "special_purpose":      ["cost_approach", "dcf"],
}

_OPTIONAL_METHODS_BY_PURPOSE: dict[str, list] = {
    "market_value":         ["income_approach", "dcf", "esg_assessment"],
    "rental_value":         ["dcf", "market_rent_sensitivity"],
    "financing_mortgage":   ["income_approach"],
    "court_legal":          ["income_approach"],
    "investment_decision":  ["hbu_analysis", "swot_analysis", "break_even_rent"],
    "internal_advisory":    ["sales_comparison", "rental_comparison"],
    "environmental_impact": ["remediation_cost"],
    "special_purpose":      ["income_approach"],
}

_ADDITIONAL_METHODS_BY_ASSET: dict[str, list] = {
    "land":                  ["hbu_analysis", "land_comparison", "residual_land_value"],
    "industrial_factory":    ["esg_assessment", "environmental_impact"],
    "mixed_use":             ["segment_allocation", "blended_reconciliation"],
    "special_purpose_asset": ["replacement_cost"],
    "residential_villa":     ["land_value_separation"],
    "administrative_office": ["direct_capitalization"],
    "retail_shop":           ["direct_capitalization"],
}

# ══════════════════════════════════════════════════════════════════════════════
# PDF sections by report_type
# ══════════════════════════════════════════════════════════════════════════════

_PDF_SECTIONS_TRADITIONAL = frozenset({
    "cover", "advisory_status", "property_summary", "scope",
    "method_summary", "reconciliation_summary", "key_assumptions",
    "final_value", "next_actions",
})

_PDF_SECTIONS_DETAILED = frozenset({
    "cover", "advisory_status", "property_summary", "scope",
    "method_summary", "reconciliation_summary", "key_assumptions",
    "final_value", "next_actions",
    # Additional detailed sections
    "evidence_sources", "comparable_analysis", "cost_approach_detail",
    "income_approach_detail", "dcf_detail", "sales_comparison_detail",
    "rental_comparison_detail", "assumptions_detail", "sensitivity_analysis",
    "hbu_summary", "legal_esg_swot_summaries", "risk_uncertainty",
})

_PDF_SECTIONS_PROFESSIONAL = frozenset({
    "cover", "advisory_status", "property_summary", "scope",
    "method_summary", "reconciliation_summary", "key_assumptions",
    "final_value", "next_actions",
    "evidence_sources", "comparable_analysis", "cost_approach_detail",
    "income_approach_detail", "dcf_detail", "sales_comparison_detail",
    "rental_comparison_detail", "assumptions_detail", "sensitivity_analysis",
    "hbu_summary", "legal_esg_swot_summaries", "risk_uncertainty",
    # Governance / professional only
    "full_hbu", "full_legal", "full_esg_climate", "full_swot_risk",
    "peer_review", "expert_signature", "certification_gate_snapshot",
    "output_hash_version", "audit_trail", "source_registry",
})

# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════

def get_expert_sheets(
    report_type: str,
    valuation_purpose: str = "",
    property_type: str = "",
) -> list[str]:
    """Return ordered list of expert workbook sheets for the given context.

    Sheets from _EXPERT_WB_SHEETS that are NOT in the returned list will be
    removed from the generated workbook before saving.
    """
    rt = report_type if report_type in VALID_REPORT_TYPES else "professional_report"
    vp = valuation_purpose if valuation_purpose in VALID_VALUATION_PURPOSES else ""
    pt = property_type if property_type in VALID_PROPERTY_TYPES else ""

    # Base set
    if rt == "traditional_report":
        active = set(_EXPERT_CORE)
    elif rt == "detailed_report":
        active = set(_EXPERT_CORE) | set(_EXPERT_DETAILED)
    else:  # professional_report
        active = set(_EXPERT_CORE) | set(_EXPERT_DETAILED) | set(_EXPERT_PROFESSIONAL)

    # Add purpose-specific extras
    if vp:
        active |= _PURPOSE_EXPERT_EXTRA.get(vp, frozenset())

    # Add asset-type extras
    if pt:
        active |= _ASSET_EXPERT_EXTRA.get(pt, frozenset())

    return list(active)


def get_final_sheets(
    report_type: str,
    valuation_purpose: str = "",
    property_type: str = "",
) -> list[str]:
    """Return ordered list of final workbook sheets for the given context."""
    rt = report_type if report_type in VALID_REPORT_TYPES else "professional_report"
    vp = valuation_purpose if valuation_purpose in VALID_VALUATION_PURPOSES else ""
    pt = property_type if property_type in VALID_PROPERTY_TYPES else ""

    if rt == "traditional_report":
        active = set(_FINAL_CORE)
    elif rt == "detailed_report":
        active = set(_FINAL_CORE) | set(_FINAL_DETAILED)
    else:
        active = set(_FINAL_CORE) | set(_FINAL_DETAILED) | set(_FINAL_PROFESSIONAL)

    if vp:
        active |= _PURPOSE_FINAL_EXTRA.get(vp, frozenset())
    if pt:
        active |= _ASSET_FINAL_EXTRA.get(pt, frozenset())

    return list(active)


def get_required_methods(
    valuation_purpose: str = "",
    property_type: str = "",
) -> dict:
    """Return required and optional methods for the given purpose and asset type."""
    vp = valuation_purpose if valuation_purpose in VALID_VALUATION_PURPOSES else ""
    pt = property_type if property_type in VALID_PROPERTY_TYPES else ""

    required = list(_REQUIRED_METHODS_BY_PURPOSE.get(vp, []))
    optional = list(_OPTIONAL_METHODS_BY_PURPOSE.get(vp, []))
    asset_additional = list(_ADDITIONAL_METHODS_BY_ASSET.get(pt, []))

    return {
        "required_methods":         required,
        "optional_methods":         optional,
        "asset_additional_methods": asset_additional,
        "all_relevant_methods":     list(set(required + optional + asset_additional)),
    }


def get_pdf_sections(report_type: str) -> frozenset:
    """Return the set of PDF section keys enabled for the given report type."""
    if report_type == "traditional_report":
        return _PDF_SECTIONS_TRADITIONAL
    if report_type == "detailed_report":
        return _PDF_SECTIONS_DETAILED
    return _PDF_SECTIONS_PROFESSIONAL


def get_output_warnings(
    report_type: str,
    valuation_purpose: str = "",
    advisory_only: bool = True,
) -> list[str]:
    """Return advisory warnings appropriate for the given output context."""
    warnings: list[str] = []
    if advisory_only:
        warnings.append("هذا المخرج مبدئي — غير صالح للاستخدام الرسمي أو الاعتماد النهائي")
    if valuation_purpose == "internal_advisory":
        warnings.append("المخرج للاستشارة الداخلية فقط — لا يُعتمد رسمياً")
    if valuation_purpose == "environmental_impact" and advisory_only:
        warnings.append("تقييم الأثر البيئي مبدئي — يلزم مصادر ميدانية معتمدة قبل الاعتماد")
    if valuation_purpose == "court_legal":
        warnings.append("التقرير القضائي يستلزم توقيع خبير معتمد ومراجعة نظراء قبل التسليم")
    if report_type == "traditional_report":
        warnings.append("التقرير التقليدي مختصر — للمراجعة التفصيلية استخدم التقرير الاحترافي")
    return warnings


def validate_report_type(report_type: str) -> tuple[bool, str]:
    """Return (is_valid, error_message). Empty error means valid."""
    if report_type in VALID_REPORT_TYPES:
        return True, ""
    return False, (
        f"نوع التقرير غير صالح: '{report_type}'. "
        f"القيم المقبولة: {sorted(VALID_REPORT_TYPES)}"
    )


def validate_valuation_purpose(purpose: str) -> tuple[bool, str]:
    """Return (is_valid, error_message)."""
    if not purpose:
        return False, "غرض التقييم مطلوب"
    if purpose in VALID_VALUATION_PURPOSES:
        return True, ""
    # Soft validation — unknown purposes are accepted with a warning
    return True, (
        f"غرض التقييم '{purpose}' غير معرّف في المصفوفة — سيُعامل كغرض مخصص"
    )


def validate_property_type(property_type: str) -> tuple[bool, str]:
    """Return (is_valid, warning_message)."""
    if not property_type:
        return False, "نوع العقار مطلوب"
    if property_type in VALID_PROPERTY_TYPES:
        return True, ""
    return True, (
        f"نوع العقار '{property_type}' غير معرّف في المصفوفة — سيُعامل كنوع مخصص"
    )


def get_output_matrix_context(
    report_type: str,
    valuation_purpose: str = "",
    property_type: str = "",
) -> dict:
    """Return context dict for output_matrix key in the full output context."""
    rt  = report_type if report_type in VALID_REPORT_TYPES else "professional_report"
    vp  = valuation_purpose if valuation_purpose in VALID_VALUATION_PURPOSES else valuation_purpose
    pt  = property_type if property_type in VALID_PROPERTY_TYPES else property_type

    expert_sheets = get_expert_sheets(rt, vp, pt)
    final_sheets  = get_final_sheets(rt, vp, pt)
    methods       = get_required_methods(vp, pt)
    pdf_sections  = sorted(get_pdf_sections(rt))

    return {
        "report_type":          rt,
        "report_type_label":    REPORT_TYPE_LABELS.get(rt, rt),
        "valuation_purpose":    vp,
        "valuation_purpose_label": VALUATION_PURPOSE_LABELS.get(vp, vp),
        "property_type":        pt,
        "property_type_label":  PROPERTY_TYPE_LABELS.get(pt, pt),
        "expert_sheet_count":   len(expert_sheets),
        "final_sheet_count":    len(final_sheets),
        "expert_sheets":        expert_sheets,
        "final_sheets":         final_sheets,
        "required_methods":     methods["required_methods"],
        "optional_methods":     methods["optional_methods"],
        "asset_additional_methods": methods["asset_additional_methods"],
        "pdf_sections_enabled": pdf_sections,
    }
