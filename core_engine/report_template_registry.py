"""
Report Template Registry — Expert Smart PropTech Platform
=========================================================
Centralised registry of named report template definitions.
Templates define metadata only; they do NOT trigger automatic generation.
Certified reports are issued only after expert review and approval.

Part E — Template library note:
    Previous Excel/Word/PDF report samples can be used to enrich templates.
    Extract structure, sheet names, section layouts, and wording only.
    Never commit client-sensitive data, real names, addresses, or stamps.
    Anonymise all sample data before any extraction.
    Real sample files must not be exposed publicly.
    Template extraction produces reusable structure, not copies of private data.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Registry — each entry is a plain dict with documented keys:
#
#   template_id               str   unique identifier (snake_case)
#   name_ar                   str   Arabic display name
#   audience                  str   user | expert | admin | institution
#   output_type               str   pdf | excel | pdf_and_excel
#   certification_status      str   non_certified | expert_required | certified_after_approval
#   page_scope                list  which source pages this template applies to
#   required_sections         list  expected section headings (for rendering / checklist)
#   applicable_pages          list  same as page_scope (alias for API use)
#   notes                     str   brief description / policy note
# ---------------------------------------------------------------------------

REPORT_TEMPLATES: dict[str, dict] = {

    "simple_dashboard_draft": {
        "template_id":          "simple_dashboard_draft",
        "name_ar":              "تقرير مبدئي Dashboard",
        "audience":             "user",
        "output_type":          "pdf",
        "certification_status": "non_certified",
        "page_scope":           ["simple_valuation"],
        "required_sections": [
            "ملخص العقار",
            "بيانات التقييم المبدئي",
            "نطاق السعر (±10%)",
            "إخلاء المسؤولية",
        ],
        "applicable_pages": ["simple_valuation"],
        "notes": (
            "مسودة تقييم آلية مختصرة للمستخدم مع Dashboard وملخص طرق التقييم. "
            "غير معتمدة. تُصدر فورًا بدون مراجعة خبير."
        ),
    },

    "residential_summary_three_methods": {
        "template_id":          "residential_summary_three_methods",
        "name_ar":              "تقرير تقييم ملخص سكني بالثلاث طرق",
        "audience":             "expert",
        "output_type":          "pdf",
        "certification_status": "certified_after_approval",
        "page_scope":           ["simple_valuation", "professional_valuation"],
        "required_sections": [
            "ملخص العقار",
            "تاريخ التقييم",
            "تاريخ التقرير",
            "الغرض من التقييم",
            "وصف العقار",
            "مقارنة البيوع",
            "أسلوب المقارنة السوقية",
            "أسلوب الدخل",
            "أسلوب التكلفة",
            "التوفيق بين النتائج",
            "القيمة النهائية",
            "الحساسية ±10%",
            "إخلاء المسؤولية",
            "توقيع الخبير",
        ],
        "applicable_pages": ["simple_valuation", "professional_valuation"],
        "notes": (
            "تقرير سكني ملخص يشمل الثلاث طرق بشكل مختصر مع مقارنات وتوفيق. "
            "يصدر بعد مراجعة واعتماد الخبير."
        ),
    },

    "full_three_approach_report": {
        "template_id":          "full_three_approach_report",
        "name_ar":              "تقرير تقييم كامل بالثلاث طرق",
        "audience":             "expert",
        "output_type":          "pdf_and_excel",
        "certification_status": "certified_after_approval",
        "page_scope":           ["professional_valuation", "simple_valuation"],
        "required_sections": [
            "ملخص العقار",
            "تاريخ التقييم",
            "تاريخ التقرير",
            "الغرض من التقييم",
            "وصف تفصيلي للعقار",
            "الحقوق والقيود",
            "الافتراضات والشروط المحددة",
            "مقارنة البيوع — جدول تفصيلي",
            "أسلوب المقارنة السوقية — تحليل كامل",
            "أسلوب الدخل — NOI ومعدل الرسملة",
            "أسلوب التكلفة — أرض ومباني",
            "التوفيق بين النتائج",
            "القيمة النهائية المعتمدة",
            "الحساسية ±10%",
            "إخلاء المسؤولية",
            "توقيع وختم الخبير",
        ],
        "applicable_pages": ["professional_valuation", "simple_valuation"],
        "notes": (
            "تقرير كامل بالثلاث طرق مع تحليل تفصيلي وجداول مقارنة وتوفيق معلل. "
            "يصدر بعد مراجعة واعتماد الخبير ويشمل Excel داخلي."
        ),
    },

    "bank_financing_report": {
        "template_id":          "bank_financing_report",
        "name_ar":              "تقرير تمويل بنكي / رهن",
        "audience":             "institution",
        "output_type":          "pdf",
        "certification_status": "certified_after_approval",
        "page_scope":           ["professional_valuation", "simple_valuation"],
        "required_sections": [
            "ملخص العقار",
            "تاريخ التقييم",
            "الغرض: تمويل / رهن عقاري",
            "وصف العقار",
            "القيمة السوقية",
            "نسبة التمويل إلى القيمة LTV",
            "مقارنة البيوع",
            "أسلوب المقارنة السوقية",
            "الحساسية ±10%",
            "شروط الرهن",
            "إخلاء المسؤولية",
            "توقيع وختم الخبير",
        ],
        "applicable_pages": ["simple_valuation", "professional_valuation"],
        "notes": (
            "تقرير تقييم للتمويل البنكي يشمل تحليل LTV وشروط الرهن. "
            "يصدر بعد مراجعة واعتماد الخبير ويلتزم بمعايير Basel III/IV."
        ),
    },

    "court_litigation_report": {
        "template_id":          "court_litigation_report",
        "name_ar":              "تقرير نزاع أو محكمة",
        "audience":             "institution",
        "output_type":          "pdf",
        "certification_status": "certified_after_approval",
        "page_scope":           ["professional_valuation"],
        "required_sections": [
            "ملخص العقار",
            "تاريخ التقييم",
            "الغرض: نزاع قانوني / محكمة",
            "وصف تفصيلي للعقار",
            "الحقوق والقيود والعوارض",
            "الافتراضات والشروط المحددة",
            "مقارنة البيوع",
            "أسلوب المقارنة السوقية",
            "أسلوب التكلفة (إن لزم)",
            "التوفيق بين النتائج",
            "القيمة النهائية المعتمدة",
            "شهادة الخبير",
            "إخلاء المسؤولية",
            "توقيع وختم الخبير",
        ],
        "applicable_pages": ["professional_valuation"],
        "notes": (
            "تقرير تقييم للنزاعات القانونية والمحاكم. "
            "يتضمن شهادة الخبير وتسلسلًا محكمًا للأدلة والمنهجية. "
            "يصدر بعد مراجعة واعتماد الخبير."
        ),
    },

    "tax_appeal_report": {
        "template_id":          "tax_appeal_report",
        "name_ar":              "تقرير ضريبي / طعن",
        "audience":             "institution",
        "output_type":          "pdf",
        "certification_status": "certified_after_approval",
        "page_scope":           ["tax_appeal"],
        "required_sections": [
            "ملخص العقار",
            "تاريخ التقييم الضريبي",
            "القيمة التقييمية الأصلية",
            "قيمة الطعن المقترحة",
            "أسس الطعن",
            "مقارنة البيوع الداعمة",
            "تحليل تعديلات الأسعار",
            "خلاصة الطعن",
            "إخلاء المسؤولية",
            "توقيع وختم الخبير",
        ],
        "applicable_pages": ["tax_appeal"],
        "notes": (
            "تقرير تقييم لدعم الطعن الضريبي أمام جهات التقييم الجماعي. "
            "يصدر بعد مراجعة واعتماد الخبير."
        ),
    },

    "special_asset_factory_report": {
        "template_id":          "special_asset_factory_report",
        "name_ar":              "تقرير منشأة خاصة / مصنع",
        "audience":             "expert",
        "output_type":          "pdf_and_excel",
        "certification_status": "certified_after_approval",
        "page_scope":           ["professional_valuation"],
        "required_sections": [
            "ملخص الأصل",
            "وصف تفصيلي للمنشأة",
            "بيانات الأرض والمباني والمعدات",
            "الطاقة الإنتاجية",
            "أسلوب التكلفة — أرض ومباني ومعدات",
            "أسلوب الدخل — تدفقات نقدية DCF",
            "أسلوب المقارنة (إن توفر)",
            "التوفيق بين النتائج",
            "القيمة النهائية",
            "الحساسية ±10%",
            "إخلاء المسؤولية",
            "توقيع وختم الخبير",
        ],
        "applicable_pages": ["professional_valuation"],
        "notes": (
            "تقرير تقييم لمنشآت صناعية وأصول خاصة ومصانع. "
            "يشمل تقييم المعدات وتحليل DCF. "
            "يصدر بعد مراجعة واعتماد الخبير."
        ),
    },

    "hbu_land_report": {
        "template_id":          "hbu_land_report",
        "name_ar":              "تقرير أرض وأعلى وأفضل استخدام",
        "audience":             "expert",
        "output_type":          "pdf",
        "certification_status": "certified_after_approval",
        "page_scope":           ["professional_valuation"],
        "required_sections": [
            "ملخص الأرض",
            "تاريخ التقييم",
            "وصف الأرض وموقعها",
            "الاشتراطات التخطيطية",
            "تحليل أعلى وأفضل استخدام HBU",
            "الاستخدام الأمثل المقترح",
            "مقارنة قطع الأراضي",
            "أسلوب المقارنة السوقية",
            "التوفيق بين النتائج",
            "القيمة النهائية",
            "إخلاء المسؤولية",
            "توقيع وختم الخبير",
        ],
        "applicable_pages": ["professional_valuation"],
        "notes": (
            "تقرير تقييم أرض مع تحليل أعلى وأفضل استخدام. "
            "يشمل تحليل الاشتراطات التخطيطية والاستخدام الأمثل. "
            "يصدر بعد مراجعة واعتماد الخبير."
        ),
    },

    "ifrs_fair_value_report": {
        "template_id":          "ifrs_fair_value_report",
        "name_ar":              "تقرير IFRS / Fair Value",
        "audience":             "institution",
        "output_type":          "pdf_and_excel",
        "certification_status": "certified_after_approval",
        "page_scope":           ["professional_valuation"],
        "required_sections": [
            "ملخص الأصل",
            "تاريخ التقييم",
            "معيار التقييم المُطبق (IFRS 13)",
            "تصنيف المدخلات (Level 1 / 2 / 3)",
            "وصف الأصل",
            "أسلوب التقييم المختار وسبب الاختيار",
            "المدخلات الرئيسية وافتراضاتها",
            "القيمة العادلة Fair Value",
            "حساسية القيمة العادلة",
            "القيود والتحفظات",
            "إخلاء المسؤولية",
            "توقيع وختم الخبير",
        ],
        "applicable_pages": ["professional_valuation"],
        "notes": (
            "تقرير تقييم وفق معايير IFRS 13 لأغراض القوائم المالية. "
            "يشمل تصنيف مدخلات القيمة العادلة. "
            "يصدر بعد مراجعة واعتماد الخبير."
        ),
    },

    "mass_appraisal_portfolio_report": {
        "template_id":          "mass_appraisal_portfolio_report",
        "name_ar":              "تقرير تقييم جماعي لمحفظة عقارية",
        "audience":             "institution",
        "output_type":          "pdf_and_excel",
        "certification_status": "expert_required",
        "page_scope":           ["composite_valuation"],
        "required_sections": [
            "ملخص المحفظة",
            "إجمالي عدد الأصول",
            "إجمالي القيمة التقديرية",
            "Dashboard ملخص KPI",
            "دراسة النسب والتوزيع",
            "معامل الاختلاف COD",
            "تحليل الشواذ",
            "حوكمة النموذج",
            "حدود الاستخدام والقيود",
            "إخلاء المسؤولية",
            "توقيع وختم الخبير",
        ],
        "applicable_pages": ["composite_valuation"],
        "notes": (
            "تقرير تقييم جماعي لمحافظ العقارات. "
            "يشمل Dashboard إحصائي ودراسة النسب ومعامل COD. "
            "يصدر بعد مراجعة واعتماد الخبير."
        ),
    },
}

# Ordered list of all template IDs
TEMPLATE_IDS: list[str] = list(REPORT_TEMPLATES.keys())


def get_template(template_id: str) -> dict | None:
    """Return template entry by ID, or None if not found."""
    return REPORT_TEMPLATES.get(template_id)


def get_template_name_ar(template_id: str, default: str = "") -> str:
    """Return the Arabic name of a template, or *default* if not found."""
    entry = REPORT_TEMPLATES.get(template_id)
    return entry["name_ar"] if entry else default
