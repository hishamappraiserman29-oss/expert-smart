"""
Phase 16.7 — Engine Dispatcher tests.

ED01–ED20  EngineDispatcher

Safety scope:
  • Only tests the new engine_dispatcher module.
  • Does NOT touch bridge_api, valuation_logic, or any /api/* route.
  • Existing /api/valuation compatibility confirmed separately via the
    unchanged test_bridge_api_* and test_valuation_requirements.py suites.
"""

import pytest
from decimal import Decimal

from core_engine.engines.engine_dispatcher import (
    list_engines,
    is_supported,
    resolve_engine,
    run_engine,
    get_engine_metadata,
)
from core_engine.engines.base import EngineResult, ValuationEngine

_ALL_KEYS = [
    "habu", "sales_comparison", "cost_approach", "income_approach",
    "dcf", "residual_land", "insurance", "mortgage_lending",
    "liquidation", "market_rental", "ifrs13", "rights",
    "litigation_compensation", "esg_remediation",
]

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def habu_inputs():
    # dev_cost kept low (5,000/m²) so GDV (60M) > costs (30M+9M) → positive residual
    return {
        "total_land_area_sqm":         2000,
        "max_far_allowed":             3.0,
        "expected_noi_per_sqm_annual": 800,
        "development_cost_per_m2":     5_000,
        "cap_rate":                    0.08,
    }


@pytest.fixture
def sales_comparison_inputs():
    return {
        "subject_area_sqm": 150,
        "comparables": [
            {"price_per_m2": 10_000, "location_adjustment": 0.02,
             "physical_adjustment": -0.01, "market_condition_adjustment": 0.0},
            {"price_per_m2": 11_000, "location_adjustment": -0.01,
             "physical_adjustment":  0.00, "market_condition_adjustment": 0.01},
            {"price_per_m2": 10_500, "location_adjustment":  0.00,
             "physical_adjustment":  0.01, "market_condition_adjustment": 0.0},
        ],
    }


# ── Registry / list tests ─────────────────────────────────────────────────────

def test_ED01_list_engines_returns_all_14():
    """ED01: list_engines() includes all 14 registered keys."""
    result = list_engines()
    assert len(result) == 14
    for key in _ALL_KEYS:
        assert key in result, f"Expected '{key}' in list_engines()"


def test_ED02_list_engines_sorted():
    """ED02: list_engines() is alphabetically sorted."""
    result = list_engines()
    assert result == sorted(result)


def test_ED03_is_supported_true_for_all_keys():
    """ED03: is_supported() returns True for every registered key."""
    for key in _ALL_KEYS:
        assert is_supported(key), f"Expected is_supported('{key}') == True"


def test_ED04_is_supported_false_unknown():
    """ED04: is_supported() returns False for unknown / empty keys."""
    assert is_supported("unknown_method") is False
    assert is_supported("") is False
    assert is_supported("avm") is False


def test_ED05_resolve_engine_returns_valuation_engine():
    """ED05: resolve_engine() returns a ValuationEngine instance for every key."""
    for key in _ALL_KEYS:
        engine = resolve_engine(key)
        assert isinstance(engine, ValuationEngine), \
            f"Expected ValuationEngine for key '{key}', got {type(engine)}"


def test_ED06_resolve_engine_singleton():
    """ED06: resolve_engine() returns the same instance on repeated calls."""
    e1 = resolve_engine("habu")
    e2 = resolve_engine("habu")
    assert e1 is e2


def test_ED07_resolve_engine_unsupported_returns_none():
    """ED07: resolve_engine() returns None for unsupported key — never raises."""
    assert resolve_engine("not_a_real_engine") is None
    assert resolve_engine("") is None


# ── Metadata tests ─────────────────────────────────────────────────────────────

def test_ED08_get_engine_metadata_supported():
    """ED08: metadata dict for supported key has required fields."""
    meta = get_engine_metadata("habu")
    assert meta["supported"] is True
    assert meta["engine_key"] == "habu"
    assert meta["engine_name"] == "habu"
    assert "version" in meta
    assert "class" in meta


def test_ED09_get_engine_metadata_unsupported():
    """ED09: metadata dict for unsupported key has supported=False."""
    meta = get_engine_metadata("imaginary_engine")
    assert meta["supported"] is False
    assert meta["engine_key"] == "imaginary_engine"


def test_ED10_all_engine_names_match_registry_keys():
    """ED10: each engine's .name attribute equals its registry key."""
    for key in _ALL_KEYS:
        engine = resolve_engine(key)
        assert engine.name == key, \
            f"Engine name mismatch: registry key='{key}', engine.name='{engine.name}'"


# ── run_engine — supported ─────────────────────────────────────────────────────

def test_ED11_run_engine_habu_returns_engine_result(habu_inputs):
    """ED11: run_engine('habu', ...) returns an EngineResult."""
    result = run_engine("habu", habu_inputs)
    assert isinstance(result, EngineResult)


def test_ED12_run_engine_habu_value_positive(habu_inputs):
    """ED12: HABU engine produces a positive Decimal value for valid inputs."""
    result = run_engine("habu", habu_inputs)
    assert result.value is not None
    assert isinstance(result.value, Decimal)
    assert result.value > 0


def test_ED13_run_engine_sales_comparison_returns_engine_result(sales_comparison_inputs):
    """ED13: run_engine('sales_comparison', ...) returns an EngineResult."""
    result = run_engine("sales_comparison", sales_comparison_inputs)
    assert isinstance(result, EngineResult)


def test_ED14_run_engine_sales_comparison_has_confidence(sales_comparison_inputs):
    """ED14: SalesComparison result has a valid confidence level."""
    result = run_engine("sales_comparison", sales_comparison_inputs)
    assert result.confidence in ("high", "medium", "low", "insufficient")


def test_ED15_run_engine_habu_engine_name_in_result(habu_inputs):
    """ED15: EngineResult.engine_name matches the registered key."""
    result = run_engine("habu", habu_inputs)
    assert result.engine_name == "habu"


# ── run_engine — unsupported (safe fallback) ───────────────────────────────────

def test_ED16_run_engine_unsupported_returns_dict():
    """ED16: run_engine with unknown key returns a dict (not an exception)."""
    result = run_engine("not_a_real_engine", {})
    assert isinstance(result, dict)


def test_ED17_run_engine_unsupported_structured_warning():
    """ED17: unsupported-key dict has supported=False, warning, available_engines."""
    result = run_engine("no_such_engine", {})
    assert result.get("supported") is False
    assert "warning" in result
    assert "available_engines" in result
    assert isinstance(result["available_engines"], list)
    assert len(result["available_engines"]) == 14


def test_ED18_run_engine_unsupported_lists_engines_sorted():
    """ED18: available_engines in unsupported-key result is sorted."""
    result = run_engine("xyz", {})
    ae = result["available_engines"]
    assert ae == sorted(ae)


def test_ED19_run_engine_unsupported_engine_key_echoed():
    """ED19: engine_key field in unsupported-key result echoes the input key."""
    result = run_engine("my_custom_key", {})
    assert result["engine_key"] == "my_custom_key"


# ── Compatibility guard ────────────────────────────────────────────────────────

def test_ED20_dispatcher_does_not_import_bridge_api():
    """ED20: engine_dispatcher does not import bridge_api or valuation_logic."""
    import inspect, re
    import core_engine.engines.engine_dispatcher as disp_mod
    src = inspect.getsource(disp_mod)
    # Check for actual import statements — docstring mentions are not imports
    assert not re.search(r'^\s*(import|from)\s+.*bridge_api', src, re.MULTILINE)
    assert not re.search(r'^\s*(import|from)\s+.*valuation_logic', src, re.MULTILINE)
