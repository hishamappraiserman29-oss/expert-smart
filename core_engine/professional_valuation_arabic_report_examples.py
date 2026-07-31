"""
professional_valuation_arabic_report_examples.py
بيانات توضيحية للتقارير العربية — للأغراض التوضيحية فقط.
advisory_only=True | not_real_training=True
لا تُستخدم هذه البيانات في أي معاملة مالية أو قانونية حقيقية.
"""
from __future__ import annotations

ADVISORY_NOTE_AR = (
    "مثال توضيحي باستخدام بيانات اختبارية، وليس نتيجة تقييم نهائية. "
    "لا تُستخدم في أي معاملة مالية أو قانونية أو رسمية."
)

SUBJECT_AR: dict = {
    "request_id": "PV-2026-QA-001",
    "report_date": "30 يونيو 2026",
    "inspection_date": "28 يونيو 2026",
    "valuation_date": "30 يونيو 2026",
    "client": "مؤسسة تمويلية (تمويل عقاري)",
    "client_type": "بنك تجاري",
    "property_address": "قطعة 22، حي النرجس، شمال الرياض، المملكة العربية السعودية",
    "property_type": "شقة سكنية",
    "gross_floor_area_m2": 185,
    "net_internal_area_m2": 172,
    "floor": "الطابق الثالث",
    "age_years": 6,
    "bedrooms": 4,
    "bathrooms": 3,
    "parking": "موقفان تحت الأرض",
    "purpose": "تمويل عقاري — تقييم رهن عقاري",
    "basis_of_value": "القيمة السوقية (IVS 2025 / IVSC)",
    "currency": "ريال سعودي (SAR)",
    "plot_number": "22",
    "district": "النرجس",
    "city": "الرياض",
    "country": "المملكة العربية السعودية",
    "coordinates": "24.8021°N, 46.6753°E (توضيحي)",
    "tenure": "ملكية تامة",
    "legal_status": "سند ملكية نظيف (توضيحي — يستلزم تأكيداً قانونياً)",
    "zoning": "R-2 سكني",
    "building_permit_year": 2018,
}

COMPARABLES_AR: list[dict] = [
    {"id": "م1", "address": "مجمع النرجس - أ", "area_m2": 180,
     "price_sar": 1_180_000, "price_per_sqm": 6_556, "age_years": 5,
     "floor": "الثاني", "parking": "نعم", "condition": "جيد", "sale_date": "مارس 2026", "distance_km": 0.4},
    {"id": "م2", "address": "أبراج الياقوت، النرجس", "area_m2": 195,
     "price_sar": 1_315_000, "price_per_sqm": 6_744, "age_years": 7,
     "floor": "الرابع", "parking": "نعم", "condition": "ممتاز", "sale_date": "مايو 2026", "distance_km": 0.6},
    {"id": "م3", "address": "حي الياسمين، الكتلة الغربية", "area_m2": 175,
     "price_sar": 1_090_000, "price_per_sqm": 6_229, "age_years": 9,
     "floor": "الأول", "parking": "لا", "condition": "جيد", "sale_date": "أبريل 2026", "distance_km": 1.2},
    {"id": "م4", "address": "برج الواحة السكني", "area_m2": 190,
     "price_sar": 1_250_000, "price_per_sqm": 6_579, "age_years": 4,
     "floor": "الخامس", "parking": "نعم", "condition": "جيد جداً", "sale_date": "يونيو 2026", "distance_km": 1.8},
    {"id": "م5", "address": "مجمع الجوهرة، النرجس", "area_m2": 200,
     "price_sar": 1_390_000, "price_per_sqm": 6_950, "age_years": 3,
     "floor": "السادس", "parking": "نعم", "condition": "ممتاز", "sale_date": "يونيو 2026", "distance_km": 0.3},
]

ADJUSTMENTS_AR: dict[str, dict] = {
    "location":   {"label": "الموقع / القرب",        "values": [0,  -2, -5, -3,  0]},
    "size":       {"label": "المساحة / المبنى",       "values": [+3, -5, +4, -3, -8]},
    "condition":  {"label": "الحالة / الجودة",        "values": [0,   0, -3,  0,  0]},
    "floor":      {"label": "مستوى الطابق",           "values": [-2, +2, -3, +3, +4]},
    "parking":    {"label": "توافر مواقف",            "values": [0,   0, +4,  0,  0]},
    "age":        {"label": "عمر المبنى",             "values": [-2,  0, -3, +2, +3]},
}

ADJUSTED_PRICES_PER_SQM: list[int] = [6_425, 6_531, 6_232, 6_557, 6_512]
INDICATED_MARKET_VALUE_PER_SQM: int = 6_500
INDICATED_MARKET_VALUE: int = 1_202_500  # 6,500 × 185

INCOME_AR: dict = {
    "gross_market_rent_annual": 78_000,
    "vacancy_rate_pct": 8.0,
    "vacancy_deduction": 6_240,
    "effective_gross_income": 71_760,
    "management_fee_pct": 5.0,
    "management_fee": 3_588,
    "maintenance_annual": 4_200,
    "insurance_annual": 1_200,
    "property_tax_annual": 0,
    "total_opex": 8_988,
    "net_operating_income": 62_772,
    "cap_rate_pct": 5.5,
    "indicated_value_income": 1_141_309,
}

COST_AR: dict = {
    "land_area_m2": 210,
    "land_value_per_sqm": 3_200,
    "land_value": 672_000,
    "gross_floor_area_m2": 185,
    "replacement_cost_new_per_sqm": 4_800,
    "replacement_cost_new": 888_000,
    "age_years": 6,
    "effective_life_years": 40,
    "physical_depreciation_pct": 15.0,
    "physical_depreciation": 133_200,
    "functional_obsolescence": 0,
    "economic_obsolescence": 0,
    "depreciated_improvement_value": 754_800,
    "indicated_value_cost": 1_426_800,
}

AVM_AR: dict = {
    "avm_provider": "مؤشر AVM المساعد (توضيحي)",
    "avm_indicated_value": 1_190_000,
    "confidence_level": "متوسط",
    "confidence_score": 0.72,
    "data_freshness": "60 يوماً",
    "comparable_count": 18,
    "note": "مؤشر مساعد فقط — لا يُعتمد وحده.",
}

RECONCILIATION_AR: dict = {
    "market_approach_value": INDICATED_MARKET_VALUE,
    "market_approach_weight_pct": 50,
    "income_approach_value": INCOME_AR["indicated_value_income"],
    "income_approach_weight_pct": 35,
    "cost_approach_value": COST_AR["indicated_value_cost"],
    "cost_approach_weight_pct": 15,
    "weighted_value": round(
        INDICATED_MARKET_VALUE * 0.50
        + INCOME_AR["indicated_value_income"] * 0.35
        + COST_AR["indicated_value_cost"] * 0.15
    ),
    "final_opinion_rounded": 1_200_000,
    "currency": "SAR",
}

DCF_5YEAR_AR: dict = {
    "hold_period_years": 5,
    "initial_noi": 62_772,
    "growth_rate_pct": 3.0,
    "terminal_cap_rate_pct": 5.8,
    "discount_rate_pct": 8.5,
    "year_cash_flows": [62_772, 64_655, 66_595, 68_593, 70_651],
    "terminal_value_year5": 1_218_983,
    "dcf_indicated_value": 1_158_240,
}

DCF_10YEAR_AR: dict = {
    "hold_period_years": 10,
    "initial_noi": 62_772,
    "growth_rate_pct": 3.0,
    "terminal_cap_rate_pct": 5.8,
    "discount_rate_pct": 8.5,
    "dcf_indicated_value": 1_172_600,
}

SCENARIOS_AR: list[dict] = [
    {"scenario": "المتحفظ",   "growth_rate": 1.5, "cap_rate": 6.2, "discount_rate": 9.5, "dcf_value": 1_040_000},
    {"scenario": "الأساسي",   "growth_rate": 3.0, "cap_rate": 5.8, "discount_rate": 8.5, "dcf_value": 1_158_000},
    {"scenario": "المتفائل",  "growth_rate": 4.5, "cap_rate": 5.3, "discount_rate": 7.5, "dcf_value": 1_310_000},
]
PROBABILITY_WEIGHTED_VALUE: int = round(
    1_040_000 * 0.20 + 1_158_000 * 0.60 + 1_310_000 * 0.20
)

SENSITIVITY_MATRIX_AR: dict = {
    "rows": ["معدل الرسملة 5.0%", "معدل الرسملة 5.5%", "معدل الرسملة 6.0%", "معدل الرسملة 6.5%"],
    "cols": ["إشغال 88%", "إشغال 92%", "إشغال 95%", "إشغال 100%"],
    "values": [
        [1_318_000, 1_370_000, 1_413_000, 1_488_000],
        [1_200_000, 1_247_000, 1_286_000, 1_354_000],
        [1_100_000, 1_143_000, 1_179_000, 1_241_000],
        [1_015_000, 1_055_000, 1_088_000, 1_145_000],
    ],
}

RISKS_AR: list[dict] = [
    {"risk": "مخاطر السوق", "severity": "متوسطة", "impact": "تقلب معدلات الرسملة"},
    {"risk": "مخاطر الشغور", "severity": "منخفضة", "impact": "انخفاض صافي الدخل"},
    {"risk": "مخاطر السيولة", "severity": "متوسطة", "impact": "صعوبة البيع السريع"},
    {"risk": "مخاطر تنظيمية", "severity": "منخفضة", "impact": "تغيير الاشتراطات"},
    {"risk": "مخاطر البناء", "severity": "منخفضة", "impact": "تدهور الحالة على المدى البعيد"},
]

STANDARDS_AR: list[dict] = [
    {"standard": "IVS 101", "name": "نطاق العمل",              "status": "مطابق"},
    {"standard": "IVS 102", "name": "التحقيقات والامتثال",      "status": "مطابق"},
    {"standard": "IVS 103", "name": "إعداد التقرير",            "status": "مطابق"},
    {"standard": "IVS 104", "name": "أسس القيمة",               "status": "مطابق"},
    {"standard": "IVS 105", "name": "مناهج وأساليب التقييم",   "status": "مطابق"},
    {"standard": "IVS 400", "name": "التقييم العقاري",          "status": "مطابق"},
]

DATA_INPUTS_AR: list[dict] = [
    {"field": "عنوان العقار",          "status": "مكتمل"},
    {"field": "المساحة الإجمالية",     "status": "مكتمل"},
    {"field": "بيانات الدخل",          "status": "مكتمل"},
    {"field": "تكلفة الإحلال",         "status": "مكتمل"},
    {"field": "مقارنات السوق",         "status": "مكتمل"},
    {"field": "تقرير الكشف",           "status": "مكتمل"},
    {"field": "سند الملكية",           "status": "توضيحي — يستلزم تأكيداً"},
    {"field": "تقرير التقييم القانوني","status": "توضيحي — يستلزم تأكيداً"},
]

METHOD_SELECTION_AR: list[dict] = [
    {"method": "أسلوب السوق / Market Approach",          "applicable": "نعم", "weight_pct": 50, "reason": "بيانات سوق كافية"},
    {"method": "أسلوب الدخل / Income Approach",          "applicable": "نعم", "weight_pct": 35, "reason": "عقار مدر للدخل"},
    {"method": "أسلوب التكلفة / Cost Approach",          "applicable": "نعم", "weight_pct": 15, "reason": "للتحقق والمقارنة"},
    {"method": "التدفقات النقدية / DCF",                 "applicable": "نعم", "weight_pct": 0,  "reason": "تحليل مساعد"},
    {"method": "أعلى وأفضل استخدام / HBU",              "applicable": "جزئي","weight_pct": 0,  "reason": "تحليل ظرفي"},
    {"method": "تقييم آلي مساعد / AVM",                 "applicable": "نعم", "weight_pct": 0,  "reason": "مؤشر مساعد فقط"},
    {"method": "أسلوب المتبقي / Residual",               "applicable": "لا",  "weight_pct": 0,  "reason": "لا ينطبق — لا تطوير"},
]

HBU_AR: dict = {
    "legally_permissible": "الاستخدام السكني المعتمد بموجب اشتراطات التخطيط",
    "physically_possible": "المبنى قائم، في حالة جيدة، قابل للسكن",
    "financially_feasible": "صافي الدخل الإيجاري إيجابي ويدعم الاستخدام السكني",
    "maximally_productive": "الاستخدام السكني الحالي هو أعلى وأفضل استخدام",
    "conclusion": "الاستخدام الحالي (سكني) يُعد أعلى وأفضل استخدام للعقار",
}

RECONCILIATION_SCORECARD_AR: list[dict] = [
    {"approach": "أسلوب السوق", "value_sar": INDICATED_MARKET_VALUE,       "weight_pct": 50, "weighted_sar": int(INDICATED_MARKET_VALUE * 0.50)},
    {"approach": "أسلوب الدخل", "value_sar": INCOME_AR["indicated_value_income"],  "weight_pct": 35, "weighted_sar": int(INCOME_AR["indicated_value_income"] * 0.35)},
    {"approach": "أسلوب التكلفة","value_sar": COST_AR["indicated_value_cost"],     "weight_pct": 15, "weighted_sar": int(COST_AR["indicated_value_cost"] * 0.15)},
]
