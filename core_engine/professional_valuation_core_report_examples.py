"""
professional_valuation_core_report_examples.py
Controlled illustrative fixture data for the three core Professional Valuation reports.
All values are indicative for illustration purposes only.
advisory_only=True | not_real_training=True
Do NOT use any figures in this module in a real financial or legal transaction.
"""
from __future__ import annotations

ADVISORY_NOTE = (
    "Indicative for illustration purposes only. "
    "Not for use in any financial, legal, or official transaction."
)

SUBJECT: dict = {
    "request_id": "PV-2026-QA-001",
    "report_date": "30 June 2026",
    "inspection_date": "28 June 2026",
    "valuation_date": "30 June 2026",
    "client": "Financing Institution (Mortgage)",
    "client_type": "Commercial Bank",
    "property_address": "Plot 22, Al-Narjes District, North Riyadh, Saudi Arabia",
    "property_type": "Residential Apartment",
    "gross_floor_area_m2": 185,
    "net_internal_area_m2": 172,
    "floor": "3rd Floor",
    "age_years": 6,
    "bedrooms": 4,
    "bathrooms": 3,
    "parking": "2 underground spaces",
    "purpose": "Real Estate Finance — Mortgage Valuation",
    "basis_of_value": "Market Value (IVSC / IVS 2025)",
    "currency": "Saudi Riyal (SAR)",
    "plot_number": "22",
    "district": "Al-Narjes",
    "city": "Riyadh",
    "country": "Saudi Arabia",
    "coordinates": "24.8021°N, 46.6753°E (illustrative)",
    "tenure": "Freehold",
    "legal_status": "Clear title (indicative — legal confirmation pending)",
    "zoning": "R-2 Residential",
    "building_permit_year": 2018,
}

COMPARABLES: list[dict] = [
    {"id": "C1", "address": "Al-Narjes Compound A", "area_m2": 180,
     "price_sar": 1_180_000, "price_per_sqm": 6_556, "age_years": 5,
     "floor": "2nd", "parking": "Yes", "condition": "Good", "sale_date": "Mar 2026", "distance_km": 0.4},
    {"id": "C2", "address": "Al-Yaqout Towers, Al-Narjes", "area_m2": 195,
     "price_sar": 1_315_000, "price_per_sqm": 6_744, "age_years": 7,
     "floor": "4th", "parking": "Yes", "condition": "Excellent", "sale_date": "May 2026", "distance_km": 0.6},
    {"id": "C3", "address": "Al-Yasmine District, West Block", "area_m2": 175,
     "price_sar": 1_090_000, "price_per_sqm": 6_229, "age_years": 9,
     "floor": "1st", "parking": "No", "condition": "Good", "sale_date": "Apr 2026", "distance_km": 1.2},
    {"id": "C4", "address": "Al-Wahah Residential Tower", "area_m2": 190,
     "price_sar": 1_250_000, "price_per_sqm": 6_579, "age_years": 4,
     "floor": "5th", "parking": "Yes", "condition": "Very Good", "sale_date": "Jun 2026", "distance_km": 1.8},
    {"id": "C5", "address": "Al-Jouhara Complex, Al-Narjes", "area_m2": 200,
     "price_sar": 1_390_000, "price_per_sqm": 6_950, "age_years": 3,
     "floor": "6th", "parking": "Yes", "condition": "Excellent", "sale_date": "Jun 2026", "distance_km": 0.3},
]

# Adjustment % per factor per comparable (C1..C5)
ADJUSTMENTS: dict[str, dict] = {
    "location":   {"label": "Location / Proximity",  "values": [0,  -2, -5, -3,  0]},
    "size":       {"label": "Size / GFA",             "values": [+3, -5, +4, -3, -8]},
    "condition":  {"label": "Condition / Quality",    "values": [0,   0, -3,  0,  0]},
    "floor":      {"label": "Floor Level",            "values": [-2, +2, -3, +3, +4]},
    "parking":    {"label": "Parking Provision",      "values": [0,   0, +4,  0,  0]},
    "age":        {"label": "Building Age",           "values": [-2,  0, -3, +2, +3]},
}

ADJUSTED_PRICES_PER_SQM: list[int] = [6_425, 6_531, 6_232, 6_557, 6_512]
INDICATED_MARKET_VALUE_PER_SQM: int = 6_500
INDICATED_MARKET_VALUE: int = 1_202_500  # 6,500 × 185

INCOME: dict = {
    "gross_market_rent_annual": 78_000,
    "vacancy_rate_pct": 8.0,
    "vacancy_deduction": 6_240,
    "effective_gross_income": 71_760,
    "management_fee_pct": 4.0,
    "management_fee": 2_870,
    "maintenance_pct": 6.0,
    "maintenance": 4_306,
    "insurance_pct": 1.5,
    "insurance": 1_076,
    "service_charge_pct": 2.0,
    "service_charge": 1_435,
    "other_opex": 500,
    "total_opex": 10_187,
    "net_operating_income": 61_573,
    "cap_rate_pct": 5.00,
    "indicated_income_value": 1_231_460,
}

COST: dict = {
    "land_area_m2": 185,
    "land_value_per_sqm": 3_800,
    "land_value": 703_000,
    "replacement_cost_per_sqm": 4_500,
    "gross_replacement_cost": 832_500,
    "age_years": 6,
    "effective_life_years": 40,
    "physical_depreciation_pct": 15.0,
    "functional_obsolescence_pct": 0.0,
    "economic_obsolescence_pct": 0.0,
    "total_depreciation_pct": 15.0,
    "total_depreciation_sar": 124_875,
    "depreciated_improvement_value": 707_625,
    "indicated_cost_value": 1_410_625,
}

AVM: dict = {
    "avm_low_95pct": 1_150_000,
    "avm_midpoint": 1_235_000,
    "avm_high_95pct": 1_340_000,
    "confidence_level": "Moderate",
    "data_sources_count": 3,
    "comparables_used": 12,
    "model_type": "Hedonic Price Model — Indicative",
    "note": ADVISORY_NOTE,
}

RECONCILIATION: dict = {
    "market_approach_weight_pct": 50,
    "income_approach_weight_pct": 30,
    "cost_approach_weight_pct": 20,
    "market_value": 1_202_500,
    "income_value": 1_231_460,
    "cost_value": 1_410_625,
    "market_contribution": 601_250,
    "income_contribution": 369_438,
    "cost_contribution": 282_125,
    "weighted_total": 1_252_813,
    "adopted_value": 1_250_000,
    "rationale": (
        "The Market Approach is weighted highest (50%) given adequate comparable sales evidence. "
        "The Income Approach (30%) reflects active rental market conditions. "
        "The Cost Approach (20%) provides a floor value reference; limited standalone reliability for "
        "income-producing assets in an active market."
    ),
}

DCF_5YEAR: dict = {
    "discount_rate_pct": 8.0,
    "terminal_cap_rate_pct": 5.25,
    "growth_rate_pct": 2.5,
    "years": [1, 2, 3, 4, 5],
    "noi":        [61_573, 63_112, 64_690, 66_307, 67_965],
    "pv_factor":  [0.9259, 0.8573, 0.7938, 0.7350, 0.6806],
    "pv_noi":     [57_011, 54_124, 51_370, 48_736, 46_271],
    "cumulative_pv_noi": 257_512,
    "terminal_value": 1_294_571,
    "pv_terminal": 881_285,
    "total_dcf_value": 1_138_797,
}

DCF_10YEAR: dict = {
    "discount_rate_pct": 8.0,
    "terminal_cap_rate_pct": 5.25,
    "growth_rate_pct": 2.5,
    "years": list(range(1, 11)),
    "noi":       [61_573, 63_112, 64_690, 66_307, 67_965, 69_664, 71_406, 73_191, 75_021, 76_896],
    "pv_factor": [0.9259, 0.8573, 0.7938, 0.7350, 0.6806, 0.6302, 0.5835, 0.5403, 0.5002, 0.4632],
    "pv_noi":    [57_011, 54_124, 51_370, 48_736, 46_271, 43_917, 41_665, 39_548, 37_535, 35_639],
    "cumulative_pv_noi": 455_816,
    "terminal_noi": 78_818,
    "terminal_value": 1_501_295,
    "pv_terminal": 695_400,
    "total_dcf_value": 1_151_216,
}

SCENARIOS: list[dict] = [
    {
        "name": "Base Case",        "growth_pct": 2.5, "discount_rate_pct": 8.0,
        "cap_rate_pct": 5.00, "occupancy_pct": 92,
        "dcf_value": 1_151_216, "market_value": 1_202_500,
        "income_value": 1_231_460, "adopted_value": 1_250_000, "probability_pct": 60,
    },
    {
        "name": "Upside Case",       "growth_pct": 4.0, "discount_rate_pct": 7.5,
        "cap_rate_pct": 4.50, "occupancy_pct": 96,
        "dcf_value": 1_345_000, "market_value": 1_330_000,
        "income_value": 1_370_000, "adopted_value": 1_345_000, "probability_pct": 25,
    },
    {
        "name": "Downside Case",     "growth_pct": 1.0, "discount_rate_pct": 9.0,
        "cap_rate_pct": 5.75, "occupancy_pct": 85,
        "dcf_value": 975_000,  "market_value": 1_075_000,
        "income_value": 1_070_000, "adopted_value": 1_060_000, "probability_pct": 15,
    },
]
PROBABILITY_WEIGHTED_VALUE: int = round(
    1_250_000 * 0.60 + 1_345_000 * 0.25 + 1_060_000 * 0.15
)  # = 1_245_250

SENSITIVITY_MATRIX: dict = {
    "row_variable": "Discount Rate (%)",
    "col_variable": "Capitalisation Rate (%)",
    "rows": [7.0, 7.5, 8.0, 8.5, 9.0],
    "cols": [4.50, 4.75, 5.00, 5.25, 5.50],
    "values": [
        [1_342_000, 1_298_000, 1_260_000, 1_225_000, 1_193_000],
        [1_282_000, 1_240_000, 1_205_000, 1_172_000, 1_143_000],
        [1_226_000, 1_187_000, 1_154_000, 1_123_000, 1_095_000],
        [1_174_000, 1_137_000, 1_106_000, 1_077_000, 1_051_000],
        [1_125_000, 1_091_000, 1_061_000, 1_033_000, 1_009_000],
    ],
}

RISKS: list[dict] = [
    {"id": "R1", "category": "Market Risk",      "description": "Residential market softening in North Riyadh",
     "probability": "Low",     "impact": "Medium",    "score": 4, "mitigation": "Comparable evidence supports current pricing"},
    {"id": "R2", "category": "Income Risk",      "description": "Vacancy rate increase above 10%",
     "probability": "Low",     "impact": "Medium",    "score": 4, "mitigation": "Strong rental demand in Al-Narjes"},
    {"id": "R3", "category": "Physical Risk",    "description": "Structural defect not identified at inspection",
     "probability": "Very Low","impact": "High",      "score": 3, "mitigation": "Visual inspection completed; no defects observed"},
    {"id": "R4", "category": "Legal Risk",       "description": "Title dispute or encumbrance",
     "probability": "Very Low","impact": "Very High", "score": 4, "mitigation": "Legal review pending — standard advisory risk"},
    {"id": "R5", "category": "Regulatory Risk",  "description": "Zoning or regulatory change",
     "probability": "Very Low","impact": "Medium",    "score": 2, "mitigation": "Current zoning confirmed R-2 residential"},
    {"id": "R6", "category": "Data Risk",        "description": "Limited comparable transactional data",
     "probability": "Low",     "impact": "Low",       "score": 2, "mitigation": "5 comparable sales within 2km identified"},
    {"id": "R7", "category": "Inflation Risk",   "description": "Construction cost inflation affecting cost approach",
     "probability": "Medium",  "impact": "Low",       "score": 4, "mitigation": "RCN estimated using current unit rates"},
    {"id": "R8", "category": "Discount Rate Risk","description": "Interest rate changes affecting DCF assumptions",
     "probability": "Medium",  "impact": "Medium",    "score": 6, "mitigation": "Sensitivity analysis covers ±1% range"},
]

STANDARDS: list[dict] = [
    {"code": "IVS 101", "name": "Scope of Work",              "status": "Addressed",           "notes": "Scope defined in engagement letter"},
    {"code": "IVS 102", "name": "Investigations & Compliance","status": "Addressed",           "notes": "Site inspection completed 28/06/2026"},
    {"code": "IVS 103", "name": "Written Reports",            "status": "Addressed",           "notes": "Report satisfies written report requirements"},
    {"code": "IVS 104", "name": "Bases of Value",             "status": "Addressed",           "notes": "Market Value per IVS 2025 defined"},
    {"code": "IVS 105", "name": "Valuation Approaches",       "status": "Addressed",           "notes": "Three approaches applied; selection justified"},
    {"code": "IVS 400", "name": "Real Property Interests",    "status": "Addressed",           "notes": "Freehold interest valued; legal status indicative"},
    {"code": "IVS 500", "name": "Financial Instruments",      "status": "N/A",                 "notes": "Not applicable for this property type"},
    {"code": "RICS PS 1","name": "Global Standards",          "status": "Addressed",           "notes": "Report format compliant with RICS PS 1"},
    {"code": "RICS PS 2","name": "Ethics and Competence",     "status": "Addressed",           "notes": "Advisory; expert review required"},
    {"code": "RICS VPS 1","name":"Terms of Engagement",       "status": "Addressed",           "notes": "Terms confirmed in appointment"},
    {"code": "RICS VPS 4","name":"Inspection",                "status": "Addressed",           "notes": "Physical inspection completed"},
    {"code": "RICS VPS 5","name":"Valuation Report",          "status": "Addressed",           "notes": "Report includes required VPS 5 content"},
    {"code": "IFRS 13",  "name": "Fair Value Measurement",    "status": "Partially Addressed", "notes": "Market Value aligned with IFRS 13 Fair Value"},
    {"code": "FRA SA",   "name": "Saudi FRA Requirements",    "status": "Addressed",           "notes": "Local regulatory framework considered"},
    {"code": "Basel III","name": "Collateral Valuation",      "status": "Addressed",           "notes": "LTV and stress scenario noted"},
]

DATA_INPUTS: list[dict] = [
    {"input": "Gross Floor Area",    "source": "Title Deed / Survey",  "value": "185 m²",              "reliability": "High",       "status": "Confirmed"},
    {"input": "Inspection Date",     "source": "Site Visit",           "value": "28 June 2026",         "reliability": "High",       "status": "Confirmed"},
    {"input": "Comparable Sale C1",  "source": "Market Research",      "value": "SAR 1,180,000",        "reliability": "High",       "status": "Confirmed"},
    {"input": "Comparable Sale C2",  "source": "Market Research",      "value": "SAR 1,315,000",        "reliability": "High",       "status": "Confirmed"},
    {"input": "Comparable Sale C3",  "source": "Market Research",      "value": "SAR 1,090,000",        "reliability": "Medium",     "status": "Confirmed"},
    {"input": "Comparable Sale C4",  "source": "Market Research",      "value": "SAR 1,250,000",        "reliability": "High",       "status": "Confirmed"},
    {"input": "Comparable Sale C5",  "source": "Market Research",      "value": "SAR 1,390,000",        "reliability": "High",       "status": "Confirmed"},
    {"input": "Market Rent",         "source": "Rental Survey",        "value": "SAR 78,000 / year",    "reliability": "Medium",     "status": "Indicative"},
    {"input": "Vacancy Rate",        "source": "Market Survey",        "value": "8%",                   "reliability": "Medium",     "status": "Indicative"},
    {"input": "Capitalisation Rate", "source": "Market Evidence",      "value": "5.00%",                "reliability": "Medium",     "status": "Indicative"},
    {"input": "Land Value",          "source": "Market Research",      "value": "SAR 3,800 / m²",       "reliability": "Medium",     "status": "Indicative"},
    {"input": "Replacement Cost",    "source": "QS Estimate",          "value": "SAR 4,500 / m²",       "reliability": "Medium",     "status": "Indicative"},
    {"input": "Depreciation Rate",   "source": "Age / Life Method",    "value": "15%",                  "reliability": "Medium",     "status": "Calculated"},
    {"input": "Discount Rate (DCF)", "source": "WACC Analysis",        "value": "8.0%",                 "reliability": "Medium",     "status": "Indicative"},
    {"input": "Terminal Cap Rate",   "source": "Market Evidence",      "value": "5.25%",                "reliability": "Low-Medium", "status": "Indicative"},
    {"input": "Growth Rate",         "source": "Market Forecast",      "value": "2.5% p.a.",            "reliability": "Low",        "status": "Indicative"},
    {"input": "AVM Midpoint",        "source": "Hedonic Model",        "value": "SAR 1,235,000",        "reliability": "Low-Medium", "status": "Advisory"},
    {"input": "Title Status",        "source": "Legal Review",         "value": "Freehold (indicative)","reliability": "Low",        "status": "Pending"},
    {"input": "Zoning Class",        "source": "Municipality Records", "value": "R-2 Residential",      "reliability": "High",       "status": "Confirmed"},
    {"input": "Building Permit",     "source": "Municipality Records", "value": "Issued 2018",          "reliability": "High",       "status": "Confirmed"},
]

METHOD_SELECTION: list[dict] = [
    {"method": "Market (Sales Comparison) Approach", "data_available": "Yes",     "applicable": "Yes", "weight_pct": 50, "justification": "Adequate comparable sales evidence"},
    {"method": "Income (Capitalisation) Approach",   "data_available": "Yes",     "applicable": "Yes", "weight_pct": 30, "justification": "Active rental market; reliable income data"},
    {"method": "Cost (Replacement Cost) Approach",   "data_available": "Yes",     "applicable": "Yes", "weight_pct": 20, "justification": "Floor value reference; limited standalone reliability"},
    {"method": "DCF Analysis",                       "data_available": "Partial", "applicable": "Yes", "weight_pct": 0,  "justification": "Cross-check only; income approach preferred"},
    {"method": "Residual / Development Method",      "data_available": "N/A",     "applicable": "No",  "weight_pct": 0,  "justification": "Completed property; no development scenario"},
]

HBU: dict = {
    "current_use": "Residential Apartment (As-Is)",
    "legally_permissible": {"result": "Residential use is legally permissible under R-2 zoning.", "status": "Pass"},
    "physically_possible":  {"result": "Property is physically suitable for continued residential use.", "status": "Pass"},
    "financially_feasible": {"result": "Residential use generates positive NOI at current cap rates.", "status": "Pass"},
    "maximally_productive": {"result": "Continued residential use represents the maximally productive use.", "status": "Pass"},
    "hbu_conclusion": "Continued residential use as-is.",
}

RECONCILIATION_SCORECARD: list[dict] = [
    {"method": "Market Approach",  "indicated_value": 1_202_500, "weight_pct": 50,  "reliability": "High",   "data_quality": "Good",       "contribution": 601_250},
    {"method": "Income Approach",  "indicated_value": 1_231_460, "weight_pct": 30,  "reliability": "Medium", "data_quality": "Acceptable", "contribution": 369_438},
    {"method": "Cost Approach",    "indicated_value": 1_410_625, "weight_pct": 20,  "reliability": "Medium", "data_quality": "Acceptable", "contribution": 282_125},
    {"method": "Weighted Total",   "indicated_value": None,       "weight_pct": 100, "reliability": "—",      "data_quality": "—",          "contribution": 1_252_813},
    {"method": "Adopted Value",    "indicated_value": 1_250_000, "weight_pct": None,"reliability": "—",      "data_quality": "—",          "contribution": None},
]

ADVISORY_FLAGS: dict = {
    "advisory_only": True,
    "not_real_training": True,
    "fake_approval_created": False,
    "certification_ready": False,
}
