"""
Tests for the Purpose Routes Registry — Phase 7.

Registry safety tests:
  PR01  — exactly 13 required groups present with correct IDs
  PR02  — group IDs are globally unique
  PR03  — route IDs are globally unique across all groups
  PR04  — every route references an existing group (group_id ∈ registry)
  PR05  — every route belongs to exactly one group
  PR06  — every group has at least one route
  PR07  — sub-route IDs are unique within their parent route
  PR08  — PURPOSE_RULES multipliers, routes, deep flags are UNCHANGED
  PR09  — PURPOSE_RULES still has exactly 14 entries
  PR10  — LEGACY_PURPOSE_LABEL_TO_GROUP covers all 14 PURPOSE_RULES labels
  PR11  — LEGACY_SNAKE_PURPOSE_TO_GROUP covers all valuation_requirements purposes
  PR12  — liquidation → liquidation_restructuring alias documented
  PR13  — resolve_route_for_legacy_purpose works for snake_case keys
  PR14  — resolve_route_for_legacy_purpose works for Arabic PURPOSE_RULES labels
  PR15  — resolve_route_for_legacy_purpose raises ValueError for unknown
  PR16  — get_purpose_group raises ValueError for unknown group_id
  PR17  — list_purpose_sub_routes raises ValueError for unknown route_id
  PR18  — list_purpose_groups returns all 13 sorted
  PR19  — list_purpose_routes returns sorted routes for a group
  PR20  — list_purpose_sub_routes returns sorted sub-routes
  PR21  — is_supported_purpose_group: True for known, False for unknown
  PR22  — is_supported_purpose_route: True for known, False for unknown
  PR23  — resolve_purpose_group_for_route correct mappings (parametrized)
  PR24  — registry importable without engines or bridge_api
  PR25  — no route appears in the LEGACY_ADAPTER_ROUTE_TO_PHASE7_ROUTE that
           is absent from PURPOSE_ROUTES_INDEX (mapping integrity)
  PR26  — all groups listed in LEGACY_PURPOSE_LABEL_TO_GROUP values exist
           in PURPOSE_GROUPS_REGISTRY
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# ── Path setup ────────────────────────────────────────────────────────────────
_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(str(_CORE))

from adapters.purpose_routes import (  # noqa: E402
    LEGACY_ADAPTER_ROUTE_TO_PHASE7_ROUTE,
    LEGACY_PURPOSE_LABEL_TO_GROUP,
    LEGACY_SNAKE_PURPOSE_TO_GROUP,
    PURPOSE_GROUPS_REGISTRY,
    PURPOSE_ROUTES_INDEX,
    PurposeGroup,
    PurposeRoute,
    PurposeSubRoute,
    get_purpose_group,
    is_supported_purpose_group,
    is_supported_purpose_route,
    list_purpose_groups,
    list_purpose_routes,
    list_purpose_sub_routes,
    resolve_purpose_group_for_route,
    resolve_route_for_legacy_purpose,
)

_REQUIRED_GROUP_IDS: frozenset[str] = frozenset({
    "market_value",
    "investment_analysis",
    "mortgage_lending",
    "liquidation_restructuring",
    "insurance",
    "market_rental_value",
    "tax_assessment",
    "financial_reporting",
    "property_rights_interest",
    "valuation_uncertainty",
    "environmental_esg",
    "litigation_compensation",
    "privatization_sovereign_assets",
})


# ── PR01 — All 13 required groups present ────────────────────────────────────

def test_PR01_all_thirteen_required_groups_present():
    """Exactly the 13 Phase 7 group IDs must exist in the registry."""
    for gid in _REQUIRED_GROUP_IDS:
        assert gid in PURPOSE_GROUPS_REGISTRY, (
            f"Required purpose group '{gid}' missing from PURPOSE_GROUPS_REGISTRY"
        )
    assert len(PURPOSE_GROUPS_REGISTRY) == 13, (
        f"Expected exactly 13 groups, got {len(PURPOSE_GROUPS_REGISTRY)}: "
        f"{sorted(PURPOSE_GROUPS_REGISTRY)}"
    )


# ── PR02 — Group IDs are globally unique ─────────────────────────────────────

def test_PR02_group_ids_are_unique():
    """No two groups share the same group_id."""
    ids = list(PURPOSE_GROUPS_REGISTRY.keys())
    assert len(ids) == len(set(ids)), (
        f"Duplicate group_ids: {[x for x in ids if ids.count(x) > 1]}"
    )


# ── PR03 — Route IDs are globally unique ─────────────────────────────────────

def test_PR03_route_ids_are_globally_unique():
    """No two routes across all groups share the same route_id."""
    all_ids: list[str] = []
    for g in PURPOSE_GROUPS_REGISTRY.values():
        for r in g.routes:
            all_ids.append(r.route_id)
    duplicates = [x for x in all_ids if all_ids.count(x) > 1]
    assert not duplicates, (
        f"Duplicate route_ids detected: {sorted(set(duplicates))}"
    )


# ── PR04 — Every route references an existing group ──────────────────────────

def test_PR04_every_route_references_existing_group():
    """Every PurposeRoute.group_id must exist in PURPOSE_GROUPS_REGISTRY."""
    for route_id, route in PURPOSE_ROUTES_INDEX.items():
        assert route.group_id in PURPOSE_GROUPS_REGISTRY, (
            f"Route '{route_id}' references unknown group_id '{route.group_id}'"
        )


# ── PR05 — Every route belongs to exactly one group ──────────────────────────

def test_PR05_every_route_belongs_to_exactly_one_group():
    """No route_id appears in more than one group's routes tuple."""
    route_to_groups: dict[str, list[str]] = {}
    for g in PURPOSE_GROUPS_REGISTRY.values():
        for r in g.routes:
            route_to_groups.setdefault(r.route_id, []).append(g.group_id)
    multi = {k: v for k, v in route_to_groups.items() if len(v) > 1}
    assert not multi, (
        f"Routes appearing in multiple groups: {multi}"
    )


# ── PR06 — Every group has at least one route ─────────────────────────────────

def test_PR06_every_group_has_at_least_one_route():
    """Every PurposeGroup must contain at least one PurposeRoute."""
    for g in PURPOSE_GROUPS_REGISTRY.values():
        assert len(g.routes) >= 1, (
            f"Purpose group '{g.group_id}' has no routes"
        )


# ── PR07 — Sub-route IDs are unique within their parent route ─────────────────

def test_PR07_sub_route_ids_unique_within_parent_route():
    """Within a single route's sub_routes tuple, no sub_route_id is duplicated."""
    for g in PURPOSE_GROUPS_REGISTRY.values():
        for r in g.routes:
            sub_ids = [s.sub_route_id for s in r.sub_routes]
            duplicates = [x for x in sub_ids if sub_ids.count(x) > 1]
            assert not duplicates, (
                f"Duplicate sub_route_ids in route '{r.route_id}': "
                f"{sorted(set(duplicates))}"
            )


# ── PR08 — PURPOSE_RULES multipliers / routes / deep flags UNCHANGED ──────────

def test_PR08_purpose_rules_multipliers_and_routes_unchanged():
    """Critical safety test: PURPOSE_RULES must retain exact multipliers and routes."""
    from adapters.purpose_adapter import PURPOSE_RULES

    expected = {
        "البيع والشراء - القيمة السوقية العادلة (Market Value)": {
            "multiplier": 1.00, "route": "market_baseline", "deep": False,
        },
        "الرهن والتمويل البنكي - القيمة السوقية لأغراض التمويل (0.95x)": {
            "multiplier": 0.95, "route": "financing_risk_haircut", "deep": False,
        },
        "التصفية الإجبارية - القيمة التصفوية (Liquidation Value x0.82)": {
            "multiplier": 0.82, "route": "liquidation_distress_discount", "deep": False,
        },
        "التأمين - قيمة إعادة الإنشاء (Reinstatement Value x1.08)": {
            "multiplier": 1.08, "route": "insurance_reinstatement_premium", "deep": False,
        },
        "الاستحواذ والاندماج - القيمة الاستثمارية (Investment Value)": {
            "multiplier": 1.00, "route": "investment_synergy_route", "deep": True,
        },
        "التحليل الاستثماري - IRR / NPV / DCF": {
            "multiplier": 1.00, "route": "financial_metrics_trigger", "deep": True,
        },
        "تحديد الأجرة - القيمة الإيجارية العادلة (Rental Value)": {
            "multiplier": 1.00, "route": "rental_yield_route", "deep": True,
        },
        "الضرائب - القيمة للأغراض الضريبية / الضريبة العقارية": {
            "multiplier": 1.00, "route": "tax_statutory_route", "deep": True,
        },
        "التقارير المالية والمحاسبية - القيمة العادلة (13 Fair Value - IFRS)": {
            "multiplier": 1.00, "route": "ifrs13_hierarchy_route", "deep": True,
        },
        "حق الانتفاع - تقييم حقوق المنفعة العقارية (Usufruct Right)": {
            "multiplier": 1.00, "route": "usufruct_finite_cashflow_route", "deep": True,
        },
        "التقييم في حالة عدم اليقين (Valuation Under Uncertainty)": {
            "multiplier": 1.00, "route": "uncertainty_range_bound_route", "deep": True,
        },
        "تحليل أعلى وأفضل استغلال (Highest and Best Use Analysis)": {
            "multiplier": 1.00, "route": "habu_feasibility_route", "deep": True,
        },
        "التقييم لأغراض الصناديق الاستثمارية (Valuation for Investment Funds / REITs)": {
            "multiplier": 1.00, "route": "reit_cma_route", "deep": True,
        },
        "تقييم الأثر البيئي (Environmental Impact Assessment - EIA)": {
            "multiplier": 1.00, "route": "eia_green_liability_route", "deep": True,
        },
    }

    for label, exp in expected.items():
        assert label in PURPOSE_RULES, (
            f"PURPOSE_RULES missing expected label: {label!r}"
        )
        rule = PURPOSE_RULES[label]
        assert rule["multiplier"] == exp["multiplier"], (
            f"PURPOSE_RULES[{label!r}]['multiplier'] changed! "
            f"Expected {exp['multiplier']}, got {rule['multiplier']}"
        )
        assert rule["route"] == exp["route"], (
            f"PURPOSE_RULES[{label!r}]['route'] changed! "
            f"Expected {exp['route']!r}, got {rule['route']!r}"
        )
        assert bool(rule.get("deep", False)) == exp["deep"], (
            f"PURPOSE_RULES[{label!r}]['deep'] changed! "
            f"Expected {exp['deep']}, got {rule.get('deep', False)}"
        )


# ── PR09 — PURPOSE_RULES still has exactly 14 entries ────────────────────────

def test_PR09_purpose_rules_still_has_14_entries():
    """PURPOSE_RULES must retain exactly 14 purpose entries."""
    from adapters.purpose_adapter import PURPOSE_RULES
    assert len(PURPOSE_RULES) == 14, (
        f"PURPOSE_RULES count changed! Expected 14, got {len(PURPOSE_RULES)}"
    )


# ── PR10 — LEGACY_PURPOSE_LABEL_TO_GROUP covers all 14 Arabic labels ─────────

def test_PR10_legacy_label_map_covers_all_purpose_rules():
    """LEGACY_PURPOSE_LABEL_TO_GROUP must map every PURPOSE_RULES Arabic label."""
    from adapters.purpose_adapter import PURPOSE_RULES
    for label in PURPOSE_RULES:
        assert label in LEGACY_PURPOSE_LABEL_TO_GROUP, (
            f"PURPOSE_RULES label not mapped: {label!r}"
        )
    assert len(LEGACY_PURPOSE_LABEL_TO_GROUP) == 14, (
        f"Expected 14 entries in LEGACY_PURPOSE_LABEL_TO_GROUP, "
        f"got {len(LEGACY_PURPOSE_LABEL_TO_GROUP)}"
    )


# ── PR11 — LEGACY_SNAKE_PURPOSE_TO_GROUP covers valuation_requirements purposes

def test_PR11_legacy_snake_map_covers_supported_purposes():
    """LEGACY_SNAKE_PURPOSE_TO_GROUP must map all SUPPORTED_PURPOSES."""
    from adapters.valuation_requirements import SUPPORTED_PURPOSES
    for purpose in SUPPORTED_PURPOSES:
        assert purpose in LEGACY_SNAKE_PURPOSE_TO_GROUP, (
            f"SUPPORTED_PURPOSES key '{purpose}' not in LEGACY_SNAKE_PURPOSE_TO_GROUP"
        )


# ── PR12 — liquidation → liquidation_restructuring alias ─────────────────────

def test_PR12_liquidation_alias_documented():
    """'liquidation' (snake) must map to 'liquidation_restructuring' (Phase 7)."""
    assert LEGACY_SNAKE_PURPOSE_TO_GROUP["liquidation"] == "liquidation_restructuring", (
        "Alias 'liquidation' → 'liquidation_restructuring' is missing or wrong"
    )
    # The Phase 7 group must exist
    assert is_supported_purpose_group("liquidation_restructuring")


# ── PR13 — resolve_route_for_legacy_purpose: snake_case ──────────────────────

@pytest.mark.parametrize("key,expected_group", [
    ("market_value",       "market_value"),
    ("mortgage_lending",   "mortgage_lending"),
    ("insurance",          "insurance"),
    ("liquidation",        "liquidation_restructuring"),
    ("investment_analysis","investment_analysis"),
])
def test_PR13_resolve_snake_purpose_to_group(key, expected_group):
    """resolve_route_for_legacy_purpose resolves snake_case keys correctly."""
    assert resolve_route_for_legacy_purpose(key) == expected_group, (
        f"resolve_route_for_legacy_purpose({key!r}) should return "
        f"'{expected_group}', got '{resolve_route_for_legacy_purpose(key)}'"
    )


# ── PR14 — resolve_route_for_legacy_purpose: Arabic labels ───────────────────

@pytest.mark.parametrize("label,expected_group", [
    ("البيع والشراء - القيمة السوقية العادلة (Market Value)",         "market_value"),
    ("الرهن والتمويل البنكي - القيمة السوقية لأغراض التمويل (0.95x)", "mortgage_lending"),
    ("التصفية الإجبارية - القيمة التصفوية (Liquidation Value x0.82)", "liquidation_restructuring"),
    ("التأمين - قيمة إعادة الإنشاء (Reinstatement Value x1.08)",      "insurance"),
    ("الاستحواذ والاندماج - القيمة الاستثمارية (Investment Value)",    "investment_analysis"),
    ("التحليل الاستثماري - IRR / NPV / DCF",                          "investment_analysis"),
    ("تحديد الأجرة - القيمة الإيجارية العادلة (Rental Value)",        "market_rental_value"),
    ("الضرائب - القيمة للأغراض الضريبية / الضريبة العقارية",         "tax_assessment"),
    ("التقارير المالية والمحاسبية - القيمة العادلة (13 Fair Value - IFRS)", "financial_reporting"),
    ("حق الانتفاع - تقييم حقوق المنفعة العقارية (Usufruct Right)",   "property_rights_interest"),
    ("التقييم في حالة عدم اليقين (Valuation Under Uncertainty)",      "valuation_uncertainty"),
    ("تحليل أعلى وأفضل استغلال (Highest and Best Use Analysis)",       "market_value"),
    ("التقييم لأغراض الصناديق الاستثمارية (Valuation for Investment Funds / REITs)", "investment_analysis"),
    ("تقييم الأثر البيئي (Environmental Impact Assessment - EIA)",    "environmental_esg"),
])
def test_PR14_resolve_arabic_label_to_group(label, expected_group):
    """resolve_route_for_legacy_purpose resolves Arabic PURPOSE_RULES labels correctly."""
    result = resolve_route_for_legacy_purpose(label)
    assert result == expected_group, (
        f"resolve_route_for_legacy_purpose({label!r}) should return "
        f"'{expected_group}', got '{result}'"
    )


# ── PR15 — resolve_route_for_legacy_purpose raises for unknown ───────────────

def test_PR15_resolve_unknown_raises():
    """resolve_route_for_legacy_purpose raises ValueError for unrecognised key."""
    with pytest.raises(ValueError, match="Unknown legacy purpose"):
        resolve_route_for_legacy_purpose("nonexistent_purpose_xyz")


# ── PR16 — get_purpose_group raises for unknown ───────────────────────────────

def test_PR16_get_purpose_group_unknown_raises():
    """get_purpose_group raises ValueError for unrecognised group_id."""
    with pytest.raises(ValueError, match="Unknown purpose group"):
        get_purpose_group("nonexistent_group_xyz")


# ── PR17 — list_purpose_sub_routes raises for unknown route ──────────────────

def test_PR17_list_purpose_sub_routes_unknown_route_raises():
    """list_purpose_sub_routes raises ValueError if route_id not in group."""
    with pytest.raises(ValueError, match="not found in group"):
        list_purpose_sub_routes("market_value", "nonexistent_route_xyz")

def test_PR17b_list_purpose_sub_routes_unknown_group_raises():
    """list_purpose_sub_routes raises ValueError if group_id unknown."""
    with pytest.raises(ValueError, match="Unknown purpose group"):
        list_purpose_sub_routes("nonexistent_group_xyz", "any_route")


# ── PR18 — list_purpose_groups returns all 13 sorted ─────────────────────────

def test_PR18_list_purpose_groups_sorted_and_complete():
    """list_purpose_groups returns all 13 groups sorted by group_id."""
    groups = list_purpose_groups()
    assert len(groups) == 13, f"Expected 13 groups, got {len(groups)}"
    ids = [g.group_id for g in groups]
    assert ids == sorted(ids), f"Groups not sorted: {ids}"
    for gid in _REQUIRED_GROUP_IDS:
        assert any(g.group_id == gid for g in groups), (
            f"Required group '{gid}' missing from list_purpose_groups()"
        )


# ── PR19 — list_purpose_routes returns sorted routes ─────────────────────────

def test_PR19_list_purpose_routes_sorted_and_correct():
    """list_purpose_routes returns routes for a group sorted by route_id."""
    routes = list_purpose_routes("market_value")
    ids = [r.route_id for r in routes]
    assert ids == sorted(ids), f"Routes not sorted: {ids}"
    expected = {"standard_market_value", "market_value_with_habu",
                "sales_comparison_market_value"}
    assert set(ids) == expected, (
        f"market_value routes mismatch. Expected: {sorted(expected)}. Got: {sorted(ids)}"
    )
    for r in routes:
        assert r.group_id == "market_value"


# ── PR20 — list_purpose_sub_routes returns sorted sub-routes ─────────────────

def test_PR20_list_purpose_sub_routes_sorted():
    """list_purpose_sub_routes returns sub-routes sorted by sub_route_id."""
    subs = list_purpose_sub_routes("market_value", "standard_market_value")
    ids = [s.sub_route_id for s in subs]
    assert ids == sorted(ids), f"Sub-routes not sorted: {ids}"
    expected = {"observed_market_inputs", "habu_required", "comparable_adjustment"}
    assert set(ids) == expected, (
        f"market_value/standard_market_value sub-routes mismatch. "
        f"Expected: {sorted(expected)}. Got: {sorted(ids)}"
    )


# ── PR21 — is_supported_purpose_group ────────────────────────────────────────

def test_PR21_is_supported_purpose_group():
    """is_supported_purpose_group returns True for known, False for unknown."""
    assert is_supported_purpose_group("market_value") is True
    assert is_supported_purpose_group("liquidation_restructuring") is True
    assert is_supported_purpose_group("environmental_esg") is True
    assert is_supported_purpose_group("liquidation") is False       # snake legacy key ≠ group_id
    assert is_supported_purpose_group("unknown_group") is False


# ── PR22 — is_supported_purpose_route ────────────────────────────────────────

def test_PR22_is_supported_purpose_route():
    """is_supported_purpose_route returns True for known, False for unknown."""
    assert is_supported_purpose_route("standard_market_value") is True
    assert is_supported_purpose_route("forced_sale") is True
    assert is_supported_purpose_route("ifrs_13_fair_value") is True
    assert is_supported_purpose_route("market_baseline") is False   # legacy adapter code ≠ Phase 7 route
    assert is_supported_purpose_route("unknown_route") is False


# ── PR23 — resolve_purpose_group_for_route correct mappings ──────────────────

@pytest.mark.parametrize("route_id,expected_group", [
    ("standard_market_value",           "market_value"),
    ("market_value_with_habu",          "market_value"),
    ("sales_comparison_market_value",   "market_value"),
    ("acquisition_synergy_value",       "investment_analysis"),
    ("dcf_investment_value",            "investment_analysis"),
    ("reit_nav",                        "investment_analysis"),
    ("bank_risk_haircut",               "mortgage_lending"),
    ("ltv_assessment",                  "mortgage_lending"),
    ("forced_sale",                     "liquidation_restructuring"),
    ("court_liquidation",               "liquidation_restructuring"),
    ("reinstatement_cost_new",          "insurance"),
    ("loss_adjustment",                 "insurance"),
    ("net_rent",                        "market_rental_value"),
    ("rent_review",                     "market_rental_value"),
    ("mass_appraisal",                  "tax_assessment"),
    ("property_tax",                    "tax_assessment"),
    ("ifrs_13_fair_value",              "financial_reporting"),
    ("impairment_review",               "financial_reporting"),
    ("usufruct_right",                  "property_rights_interest"),
    ("minority_interest",               "property_rights_interest"),
    ("sensitivity_analysis",            "valuation_uncertainty"),
    ("stress_case",                     "valuation_uncertainty"),
    ("remediation_cost",                "environmental_esg"),
    ("carbon_credit_value",             "environmental_esg"),
    ("court_damages",                   "litigation_compensation"),
    ("cost_to_cure",                    "litigation_compensation"),
    ("eminent_domain",                  "litigation_compensation"),
    ("public_to_private_conversion",    "privatization_sovereign_assets"),
    ("concession_value",                "privatization_sovereign_assets"),
])
def test_PR23_resolve_purpose_group_for_route(route_id, expected_group):
    """resolve_purpose_group_for_route returns the correct group_id."""
    result = resolve_purpose_group_for_route(route_id)
    assert result == expected_group, (
        f"resolve_purpose_group_for_route('{route_id}') should return "
        f"'{expected_group}', got '{result}'"
    )


# ── PR24 — Registry importable without engines or bridge_api ─────────────────

def test_PR24_registry_importable_without_engines():
    """Importing purpose_routes must not require any valuation engine or bridge_api."""
    assert PURPOSE_GROUPS_REGISTRY is not None
    assert PURPOSE_ROUTES_INDEX is not None
    assert len(PURPOSE_GROUPS_REGISTRY) == 13


# ── PR25 — LEGACY_ADAPTER_ROUTE_TO_PHASE7_ROUTE mapping integrity ────────────

def test_PR25_legacy_adapter_route_mapping_integrity():
    """Every Phase 7 route_id in LEGACY_ADAPTER_ROUTE_TO_PHASE7_ROUTE must exist."""
    for adapter_route, phase7_route in LEGACY_ADAPTER_ROUTE_TO_PHASE7_ROUTE.items():
        assert phase7_route in PURPOSE_ROUTES_INDEX, (
            f"Adapter route '{adapter_route}' maps to Phase 7 route '{phase7_route}' "
            f"which is not in PURPOSE_ROUTES_INDEX"
        )
    # Must cover all 14 adapter routes
    assert len(LEGACY_ADAPTER_ROUTE_TO_PHASE7_ROUTE) == 14, (
        f"Expected 14 adapter route mappings, got "
        f"{len(LEGACY_ADAPTER_ROUTE_TO_PHASE7_ROUTE)}"
    )


# ── PR26 — All group_ids in legacy label map exist in registry ───────────────

def test_PR26_legacy_label_map_group_ids_exist_in_registry():
    """All group_id values in LEGACY_PURPOSE_LABEL_TO_GROUP must exist in registry."""
    for label, gid in LEGACY_PURPOSE_LABEL_TO_GROUP.items():
        assert gid in PURPOSE_GROUPS_REGISTRY, (
            f"Label '{label}' maps to group_id '{gid}' "
            f"which is not in PURPOSE_GROUPS_REGISTRY"
        )
