"""
Purpose Routes Registry — Phase 7 (METADATA ONLY).

Organises valuation purposes into thirteen logical groups, each with
purpose routes and purpose sub-routes.

⚠️  METADATA ONLY — no valuation engines, no multipliers, no adjustment
    logic.  Sub-route IDs are descriptive labels; they carry no numerical
    weights and apply no calculations.

Relationship to purpose_adapter.py / PURPOSE_RULES
---------------------------------------------------
purpose_adapter.py contains PURPOSE_RULES: a catalog of 14 Arabic-labeled
purposes with explicit multipliers (market/financing/liquidation/insurance)
and ten deferred complex-route purposes.

    ┌─ PURPOSE_RULES (purpose_adapter.py) ─────────────────────────────┐
    │  14 Arabic labels → multiplier / route / deep flag               │
    │  These are UNCHANGED by Phase 7.  Red line.                      │
    └──────────────────────────────────────────────────────────────────┘
                         ↕  LEGACY MAPPING (this module)
    ┌─ PURPOSE_ROUTES_REGISTRY (this module) ──────────────────────────┐
    │  13 Phase 7 groups → routes → sub-routes  (metadata only)       │
    └──────────────────────────────────────────────────────────────────┘

The mapping is one-way and purely informational: Phase 7 group IDs
classify the existing purposes for organisational purposes only.

Relationship to valuation_requirements.py
-----------------------------------------
valuation_requirements.py defines five snake_case SUPPORTED_PURPOSES:
  market_value · mortgage_lending · insurance · liquidation · investment_analysis

These map to Phase 7 group IDs via LEGACY_SNAKE_PURPOSE_TO_GROUP.
Note: ``liquidation`` (snake_case) maps to ``liquidation_restructuring``
(Phase 7 group_id) — documented alias, no renaming of either code.

Legacy adapter internal route codes
------------------------------------
PURPOSE_RULES uses internal route codes (e.g. "market_baseline",
"ifrs13_hierarchy_route"). These are NOT Phase 7 route_ids.
The mapping LEGACY_ADAPTER_ROUTE_TO_PHASE7_ROUTE documents the
correspondence but does not replace or modify those codes.

Usage
-----
    from adapters.purpose_routes import (
        list_purpose_groups,
        get_purpose_group,
        list_purpose_routes,
        list_purpose_sub_routes,
        resolve_purpose_group_for_route,
        resolve_route_for_legacy_purpose,
        is_supported_purpose_group,
        is_supported_purpose_route,
    )

    groups   = list_purpose_groups()       # sorted list of PurposeGroup
    group    = get_purpose_group("market_value")
    routes   = list_purpose_routes("market_value")
    subs     = list_purpose_sub_routes("market_value", "standard_market_value")
    gid      = resolve_purpose_group_for_route("standard_market_value")  # → "market_value"
    gid2     = resolve_route_for_legacy_purpose("market_value")           # → "market_value"
"""
from __future__ import annotations

from dataclasses import dataclass


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PurposeSubRoute:
    """A single analytical sub-dimension within a purpose route.

    sub_route_id  Unique snake_case identifier within its parent route.
    display_ar    Arabic display label.
    """
    sub_route_id: str
    display_ar:   str


@dataclass(frozen=True)
class PurposeRoute:
    """A purpose route within a group.

    route_id    Globally unique snake_case identifier.
    display_ar  Arabic display label.
    group_id    Parent group identifier.
    sub_routes  Tuple of PurposeSubRoute — may be empty (documented).
    """
    route_id:   str
    display_ar: str
    group_id:   str
    sub_routes: tuple[PurposeSubRoute, ...]


@dataclass(frozen=True)
class PurposeGroup:
    """A logical grouping of related purpose routes.

    group_id    Globally unique snake_case identifier.
    display_ar  Arabic display label.
    routes      Tuple of PurposeRoute instances belonging to this group.
    """
    group_id:   str
    display_ar: str
    routes:     tuple[PurposeRoute, ...]


# ── Helper: build routes with shared sub-routes ───────────────────────────────

def _routes(
    group_id: str,
    route_specs: list[tuple[str, str]],
    shared_sub_routes: list[tuple[str, str]],
) -> tuple[PurposeRoute, ...]:
    """Build a tuple of PurposeRoute where every route shares the same sub-routes."""
    subs = tuple(PurposeSubRoute(sid, sar) for sid, sar in shared_sub_routes)
    return tuple(
        PurposeRoute(rid, rar, group_id, subs)
        for rid, rar in route_specs
    )


# ── Group 1 — Market Value ────────────────────────────────────────────────────

_GROUP_MARKET_VALUE = PurposeGroup(
    group_id   = "market_value",
    display_ar = "القيمة السوقية العادلة",
    routes     = _routes(
        "market_value",
        [
            ("standard_market_value",            "القيمة السوقية القياسية"),
            ("market_value_with_habu",           "القيمة السوقية مع أعلى وأفضل استغلال"),
            ("sales_comparison_market_value",    "القيمة السوقية بالمقارنة"),
        ],
        [
            ("observed_market_inputs",  "مدخلات السوق الملحوظة"),
            ("habu_required",           "تحليل HABU مطلوب"),
            ("comparable_adjustment",   "تعديلات المقارنات"),
        ],
    ),
)


# ── Group 2 — Investment Analysis ────────────────────────────────────────────

_GROUP_INVESTMENT = PurposeGroup(
    group_id   = "investment_analysis",
    display_ar = "التحليل الاستثماري والجدوى",
    routes     = _routes(
        "investment_analysis",
        [
            ("acquisition_synergy_value",      "قيمة الاستحواذ والتآزر"),
            ("development_feasibility",        "جدوى التطوير"),
            ("dcf_investment_value",           "القيمة الاستثمارية بالتدفقات النقدية المخصومة"),
            ("reit_nav",                       "صافي أصول صندوق الاستثمار العقاري"),
            ("asset_backed_securitization",    "التوريق بضمان الأصول"),
            ("asset_swap",                     "المبادلة العقارية"),
        ],
        [
            ("wacc_based",              "قائم على تكلفة رأس المال المرجّحة (WACC)"),
            ("target_irr_based",        "قائم على معدل العائد الداخلي المستهدف"),
            ("terminal_cap_rate_based", "قائم على معدل رسملة القيمة النهائية"),
            ("portfolio_nav_based",     "قائم على صافي قيمة الأصول المحفظة"),
        ],
    ),
)


# ── Group 3 — Mortgage Lending ───────────────────────────────────────────────

_GROUP_MORTGAGE = PurposeGroup(
    group_id   = "mortgage_lending",
    display_ar = "الرهن والتمويل البنكي",
    routes     = _routes(
        "mortgage_lending",
        [
            ("secured_lending_value", "القيمة للإقراض المضمون"),
            ("bank_risk_haircut",     "خصم مخاطر البنك"),
            ("ltv_assessment",        "تقييم نسبة القرض إلى القيمة (LTV)"),
        ],
        [
            ("stable_income_basis",      "قائم على الدخل المستقر"),
            ("remaining_economic_life",  "العمر الاقتصادي المتبقي"),
            ("credit_risk_buffer",       "احتياطي مخاطر الائتمان"),
        ],
    ),
)


# ── Group 4 — Liquidation & Restructuring ────────────────────────────────────

_GROUP_LIQUIDATION = PurposeGroup(
    group_id   = "liquidation_restructuring",
    display_ar = "التصفية وإعادة الهيكلة",
    routes     = _routes(
        "liquidation_restructuring",
        [
            ("forced_sale",                      "البيع الجبري"),
            ("court_liquidation",                "التصفية القضائية"),
            ("bankruptcy_restructuring",         "إعادة هيكلة الإفلاس"),
            ("going_concern_vs_liquidation",     "الاستمرارية مقابل التصفية"),
        ],
        [
            ("time_pressure_discount",   "خصم الضغط الزمني"),
            ("auction_costs",            "تكاليف المزاد"),
            ("creditor_recovery_basis",  "أساس استرداد الدائنين"),
        ],
    ),
)


# ── Group 5 — Insurance ──────────────────────────────────────────────────────

_GROUP_INSURANCE = PurposeGroup(
    group_id   = "insurance",
    display_ar = "التأمين وإعادة الإنشاء",
    routes     = _routes(
        "insurance",
        [
            ("reinstatement_cost_new", "تكلفة إعادة الإنشاء بالجديد"),
            ("policy_issuance",        "إصدار وثيقة التأمين"),
            ("damage_assessment",      "تقدير الضرر"),
            ("loss_adjustment",        "تسوية الخسارة"),
        ],
        [
            ("debris_removal",          "إزالة الأنقاض"),
            ("professional_fees",       "الأتعاب المهنية"),
            ("construction_inflation",  "تضخم تكاليف البناء"),
            ("cost_to_cure",            "تكلفة الإصلاح"),
        ],
    ),
)


# ── Group 6 — Market Rental Value ────────────────────────────────────────────

_GROUP_RENTAL = PurposeGroup(
    group_id   = "market_rental_value",
    display_ar = "القيمة الإيجارية العادلة",
    routes     = _routes(
        "market_rental_value",
        [
            ("net_rent",      "الإيجار الصافي"),
            ("gross_rent",    "الإيجار الإجمالي"),
            ("lease_renewal", "تجديد عقد الإيجار"),
            ("rent_review",   "مراجعة الإيجار"),
        ],
        [
            ("gla_based",                      "قائم على مساحة الإيجار الإجمالية (GLA)"),
            ("operating_cost_pass_through",    "تمرير تكاليف التشغيل"),
            ("rent_free_period_adjustment",    "تعديل فترة الإيجار المجاني"),
        ],
    ),
)


# ── Group 7 — Tax Assessment ─────────────────────────────────────────────────

_GROUP_TAX = PurposeGroup(
    group_id   = "tax_assessment",
    display_ar = "التقييم الضريبي",
    routes     = _routes(
        "tax_assessment",
        [
            ("mass_appraisal",    "التقييم الجماعي"),
            ("property_tax",      "الضريبة العقارية"),
            ("government_rating", "التقدير الحكومي"),
        ],
        [
            ("cadastral_value",  "القيمة المساحية"),
            ("street_factor",    "معامل الشارع"),
            ("exemption_rate",   "معدل الإعفاء"),
        ],
    ),
)


# ── Group 8 — Financial Reporting ────────────────────────────────────────────

_GROUP_FINANCIAL_REPORTING = PurposeGroup(
    group_id   = "financial_reporting",
    display_ar = "التقارير المالية والمحاسبية",
    routes     = _routes(
        "financial_reporting",
        [
            ("ifrs_13_fair_value",   "القيمة العادلة IFRS 13"),
            ("ias_16_revaluation",   "إعادة التقييم IAS 16"),
            ("impairment_review",    "مراجعة الاضمحلال"),
            ("disclosure_support",   "دعم الإفصاح"),
        ],
        [
            ("level_1_inputs",      "مدخلات المستوى الأول"),
            ("level_2_inputs",      "مدخلات المستوى الثاني"),
            ("level_3_inputs",      "مدخلات المستوى الثالث"),
            ("revaluation_surplus", "فائض إعادة التقييم"),
        ],
    ),
)


# ── Group 9 — Property Rights & Interest ─────────────────────────────────────

_GROUP_RIGHTS = PurposeGroup(
    group_id   = "property_rights_interest",
    display_ar = "حقوق الملكية والانتفاع",
    routes     = _routes(
        "property_rights_interest",
        [
            ("usufruct_right",        "حق الانتفاع"),
            ("bare_ownership",        "ملكية الرقبة"),
            ("minority_interest",     "حصة الأقلية"),
            ("inheritance_partition", "قسمة الميراث"),
            ("undivided_share",       "الحصة الشائعة"),
        ],
        [
            ("remaining_term_value", "قيمة المدة المتبقية"),
            ("dloc_adjustment",      "تعديل خصم ضعف السيطرة (DLOC)"),
            ("dlom_adjustment",      "تعديل خصم ضعف التسويق (DLOM)"),
            ("income_right_basis",   "أساس حق الدخل"),
        ],
    ),
)


# ── Group 10 — Valuation Uncertainty ─────────────────────────────────────────

_GROUP_UNCERTAINTY = PurposeGroup(
    group_id   = "valuation_uncertainty",
    display_ar = "التقييم في حالة عدم اليقين",
    routes     = _routes(
        "valuation_uncertainty",
        [
            ("sensitivity_analysis",        "تحليل الحساسية"),
            ("scenario_analysis",           "تحليل السيناريوهات"),
            ("probability_weighted_value",  "القيمة المرجّحة باحتمالات"),
            ("stress_case",                 "سيناريو الإجهاد"),
        ],
        [
            ("optimistic_base_pessimistic", "متفائل / قاعدي / متشائم"),
            ("discount_rate_shock",         "صدمة معدل الخصم"),
            ("vacancy_shock",               "صدمة نسبة الشغور"),
            ("market_price_decline",        "انخفاض أسعار السوق"),
        ],
    ),
)


# ── Group 11 — Environmental & ESG ───────────────────────────────────────────

_GROUP_ESG = PurposeGroup(
    group_id   = "environmental_esg",
    display_ar = "البيئة والحوكمة والاستدامة (ESG)",
    routes     = _routes(
        "environmental_esg",
        [
            ("remediation_cost",          "تكلفة المعالجة البيئية"),
            ("green_premium",             "العلاوة الخضراء"),
            ("carbon_credit_value",       "قيمة ائتمانات الكربون"),
            ("environmental_liability",   "الالتزامات البيئية"),
        ],
        [
            ("soil_remediation",     "معالجة التربة"),
            ("water_treatment",      "معالجة المياه"),
            ("energy_savings",       "وفورات الطاقة"),
            ("carbon_credit_income", "دخل ائتمانات الكربون"),
        ],
    ),
)


# ── Group 12 — Litigation & Compensation ─────────────────────────────────────

_GROUP_LITIGATION = PurposeGroup(
    group_id   = "litigation_compensation",
    display_ar = "التعويضات القضائية والخسائر",
    routes     = _routes(
        "litigation_compensation",
        [
            ("court_damages",                        "الأضرار القضائية"),
            ("diminution_in_value",                  "نقص القيمة"),
            ("cost_to_cure",                         "تكلفة الإصلاح القضائي"),
            ("eminent_domain",                       "نزع الملكية للمنفعة العامة"),
            ("severance_damage",                     "ضرر التقطيع"),
            ("compulsory_acquisition_compensation",  "تعويض الاستملاك الجبري"),
        ],
        [
            ("before_after_value",     "القيمة قبل وبعد"),
            ("repair_cost_basis",      "أساس تكلفة الإصلاح"),
            ("partial_take",           "الأخذ الجزئي"),
            ("remaining_land_damage",  "الضرر على الأرض المتبقية"),
        ],
    ),
)


# ── Group 13 — Privatization & Sovereign Assets ──────────────────────────────

_GROUP_PRIVATIZATION = PurposeGroup(
    group_id   = "privatization_sovereign_assets",
    display_ar = "الخصخصة والأصول السيادية",
    routes     = _routes(
        "privatization_sovereign_assets",
        [
            ("public_to_private_conversion", "التحويل من العام إلى الخاص"),
            ("concession_value",             "قيمة الامتياز"),
            ("labor_liability_adjustment",   "تعديل الالتزامات العمالية"),
            ("infrastructure_modernization", "تحديث البنية التحتية"),
        ],
        [
            ("commercialized_noi",       "صافي الدخل التشغيلي المُسوَّق"),
            ("capex_modernization",      "نفقات رأس المال للتحديث"),
            ("transferred_liabilities",  "الالتزامات المنقولة"),
            ("sovereign_constraints",    "القيود السيادية"),
        ],
    ),
)


# ── Registry ──────────────────────────────────────────────────────────────────

_ALL_GROUPS: tuple[PurposeGroup, ...] = (
    _GROUP_MARKET_VALUE,
    _GROUP_INVESTMENT,
    _GROUP_MORTGAGE,
    _GROUP_LIQUIDATION,
    _GROUP_INSURANCE,
    _GROUP_RENTAL,
    _GROUP_TAX,
    _GROUP_FINANCIAL_REPORTING,
    _GROUP_RIGHTS,
    _GROUP_UNCERTAINTY,
    _GROUP_ESG,
    _GROUP_LITIGATION,
    _GROUP_PRIVATIZATION,
)

# O(1) group lookup
PURPOSE_GROUPS_REGISTRY: dict[str, PurposeGroup] = {
    g.group_id: g for g in _ALL_GROUPS
}

# O(1) route lookup (route_ids are globally unique)
PURPOSE_ROUTES_INDEX: dict[str, PurposeRoute] = {
    r.route_id: r
    for g in _ALL_GROUPS
    for r in g.routes
}


# ── Legacy mappings (read-only, no behavior change) ───────────────────────────

# 14 Arabic PURPOSE_RULES keys (purpose_adapter.py) → Phase 7 group_id
# These labels are UNCHANGED; only the classification mapping is new.
LEGACY_PURPOSE_LABEL_TO_GROUP: dict[str, str] = {
    "البيع والشراء - القيمة السوقية العادلة (Market Value)":
        "market_value",
    "الرهن والتمويل البنكي - القيمة السوقية لأغراض التمويل (0.95x)":
        "mortgage_lending",
    "التصفية الإجبارية - القيمة التصفوية (Liquidation Value x0.82)":
        "liquidation_restructuring",
    "التأمين - قيمة إعادة الإنشاء (Reinstatement Value x1.08)":
        "insurance",
    "الاستحواذ والاندماج - القيمة الاستثمارية (Investment Value)":
        "investment_analysis",
    "التحليل الاستثماري - IRR / NPV / DCF":
        "investment_analysis",
    "تحديد الأجرة - القيمة الإيجارية العادلة (Rental Value)":
        "market_rental_value",
    "الضرائب - القيمة للأغراض الضريبية / الضريبة العقارية":
        "tax_assessment",
    "التقارير المالية والمحاسبية - القيمة العادلة (13 Fair Value - IFRS)":
        "financial_reporting",
    "حق الانتفاع - تقييم حقوق المنفعة العقارية (Usufruct Right)":
        "property_rights_interest",
    "التقييم في حالة عدم اليقين (Valuation Under Uncertainty)":
        "valuation_uncertainty",
    "تحليل أعلى وأفضل استغلال (Highest and Best Use Analysis)":
        "market_value",               # maps to market_value_with_habu route
    "التقييم لأغراض الصناديق الاستثمارية (Valuation for Investment Funds / REITs)":
        "investment_analysis",
    "تقييم الأثر البيئي (Environmental Impact Assessment - EIA)":
        "environmental_esg",
}

# 5 snake_case keys from valuation_requirements.py → Phase 7 group_id
# Note: "liquidation" → "liquidation_restructuring" (alias, no renaming)
LEGACY_SNAKE_PURPOSE_TO_GROUP: dict[str, str] = {
    "market_value":       "market_value",
    "mortgage_lending":   "mortgage_lending",
    "insurance":          "insurance",
    "liquidation":        "liquidation_restructuring",   # alias
    "investment_analysis":"investment_analysis",
}

# Internal adapter route codes (PURPOSE_RULES["route"]) → Phase 7 route_id
# Informational only — does not modify purpose_adapter.py
LEGACY_ADAPTER_ROUTE_TO_PHASE7_ROUTE: dict[str, str] = {
    "market_baseline":                  "standard_market_value",
    "financing_risk_haircut":           "bank_risk_haircut",
    "liquidation_distress_discount":    "forced_sale",
    "insurance_reinstatement_premium":  "reinstatement_cost_new",
    "investment_synergy_route":         "acquisition_synergy_value",
    "financial_metrics_trigger":        "dcf_investment_value",
    "rental_yield_route":               "net_rent",
    "tax_statutory_route":              "mass_appraisal",
    "ifrs13_hierarchy_route":           "ifrs_13_fair_value",
    "usufruct_finite_cashflow_route":   "usufruct_right",
    "uncertainty_range_bound_route":    "sensitivity_analysis",
    "habu_feasibility_route":           "market_value_with_habu",
    "reit_cma_route":                   "reit_nav",
    "eia_green_liability_route":        "remediation_cost",
}


# ── Public API ────────────────────────────────────────────────────────────────

def list_purpose_groups() -> list[PurposeGroup]:
    """Return all purpose groups sorted by group_id."""
    return sorted(PURPOSE_GROUPS_REGISTRY.values(), key=lambda g: g.group_id)


def get_purpose_group(group_id: str) -> PurposeGroup:
    """Return the PurposeGroup for *group_id*.

    Raises
    ------
    ValueError
        If group_id is not in the registry.
    """
    entry = PURPOSE_GROUPS_REGISTRY.get(group_id)
    if entry is None:
        raise ValueError(
            f"Unknown purpose group {group_id!r}. "
            f"Valid groups: {sorted(PURPOSE_GROUPS_REGISTRY)}"
        )
    return entry


def list_purpose_routes(group_id: str) -> list[PurposeRoute]:
    """Return routes for *group_id* sorted by route_id.

    Raises
    ------
    ValueError
        If group_id is not in the registry.
    """
    return sorted(get_purpose_group(group_id).routes, key=lambda r: r.route_id)


def list_purpose_sub_routes(group_id: str, route_id: str) -> list[PurposeSubRoute]:
    """Return sub-routes for *route_id* within *group_id*, sorted by sub_route_id.

    Raises
    ------
    ValueError
        If group_id or route_id is not found.
    """
    group = get_purpose_group(group_id)
    route_map = {r.route_id: r for r in group.routes}
    route = route_map.get(route_id)
    if route is None:
        valid = sorted(r.route_id for r in group.routes)
        raise ValueError(
            f"Route {route_id!r} not found in group {group_id!r}. "
            f"Valid routes: {valid}"
        )
    return sorted(route.sub_routes, key=lambda s: s.sub_route_id)


def resolve_purpose_group_for_route(route_id: str) -> str:
    """Return the group_id that owns *route_id*.

    Raises
    ------
    ValueError
        If route_id is not in the index.
    """
    entry = PURPOSE_ROUTES_INDEX.get(route_id)
    if entry is None:
        raise ValueError(
            f"Unknown purpose route {route_id!r}. "
            f"Valid routes: {sorted(PURPOSE_ROUTES_INDEX)}"
        )
    return entry.group_id


def resolve_route_for_legacy_purpose(purpose_key_or_label: str) -> str:
    """Return the Phase 7 group_id for a legacy purpose identifier.

    Accepts:
    - Snake_case keys from valuation_requirements.py  (e.g. "market_value")
    - Arabic label keys from PURPOSE_RULES             (e.g. "البيع والشراء…")

    Raises
    ------
    ValueError
        If the key is not found in either legacy mapping.
    """
    # Try snake_case first (shorter, faster path)
    result = LEGACY_SNAKE_PURPOSE_TO_GROUP.get(purpose_key_or_label)
    if result is not None:
        return result
    # Try Arabic label
    result = LEGACY_PURPOSE_LABEL_TO_GROUP.get(purpose_key_or_label)
    if result is not None:
        return result
    raise ValueError(
        f"Unknown legacy purpose {purpose_key_or_label!r}. "
        f"Valid snake_case keys: {sorted(LEGACY_SNAKE_PURPOSE_TO_GROUP)}. "
        f"Valid Arabic labels: see LEGACY_PURPOSE_LABEL_TO_GROUP."
    )


def is_supported_purpose_group(group_id: str) -> bool:
    """Return True if *group_id* is a recognised Phase 7 purpose group."""
    return group_id in PURPOSE_GROUPS_REGISTRY


def is_supported_purpose_route(route_id: str) -> bool:
    """Return True if *route_id* is a recognised Phase 7 purpose route."""
    return route_id in PURPOSE_ROUTES_INDEX
