"""
Tests for HABUEngine (HA01–HA30+) and SalesComparisonEngine (SC01–SC30+).
All tests are pure unit tests: no network, no bridge_api, no qdrant.
"""

import sys
from decimal import Decimal
from pathlib import Path

import pytest

# ── Path setup ─────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core_engine.engines.habu_engine import HABUEngine
from core_engine.engines.sales_comparison_engine import SalesComparisonEngine
from core_engine.engines.base import EngineResult, ValidationIssue


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def habu() -> HABUEngine:
    return HABUEngine()


@pytest.fixture
def sc() -> SalesComparisonEngine:
    return SalesComparisonEngine()


@pytest.fixture
def habu_full_inputs() -> dict:
    """Feasible HABU scenario with all inputs present.

    buildable   = 1000 × 3.0       = 3 000 sqm
    NOI         = 3 000 × 2 000    = 6 000 000
    GDV         = 6 000 000 / 0.08 = 75 000 000
    dev_cost    = 3 000 × 5 000    = 15 000 000
    dev_profit  = 75 000 000 × .15 = 11 250 000
    residual    =                    48 750 000  (positive → feasible)
    """
    return {
        "current_use": "Vacant Land",
        "proposed_habu_use": "Mixed-Use Residential/Commercial",
        "total_land_area_sqm": 1_000.0,
        "max_far_allowed": 3.0,
        "expected_noi_per_sqm_annual": 2_000.0,
        "development_cost_per_m2": 5_000.0,
        "cap_rate": 0.08,
        "developer_profit_rate": 0.15,
    }


@pytest.fixture
def sc_three_comps() -> dict:
    """Three comparables with explicit adjustments, subject area = 100 sqm.

    comp 0: 20 000 × 1.05 × 0.90 × 1.00 = 18 900
    comp 1: 22 000 × 1.00 × 1.00 × 0.95 = 20 900
    comp 2: 19 000 × 1.10 × 1.00 × 1.00 = 20 900
    avg_adjusted_ppm = (18 900 + 20 900 + 20 900) / 3 ≈ 20 233.33
    indicated_value = 20 233.33 × 100 ≈ 2 023 333.33
    """
    return {
        "subject_area_sqm": 100.0,
        "comparables": [
            {
                "price_per_m2": 20_000.0,
                "location_adjustment": 0.05,
                "physical_adjustment": -0.10,
                "market_condition_adjustment": 0.00,
                "label": "Comp A",
            },
            {
                "price_per_m2": 22_000.0,
                "location_adjustment": 0.00,
                "physical_adjustment": 0.00,
                "market_condition_adjustment": -0.05,
            },
            {
                "price_per_m2": 19_000.0,
                "location_adjustment": 0.10,
                "physical_adjustment": 0.00,
                "market_condition_adjustment": 0.00,
            },
        ],
    }


# ===========================================================================
# HABU Engine Tests (HA01–HA30+)
# ===========================================================================

class TestHABUEngine:

    # ── Identity ──────────────────────────────────────────────────────────

    def test_HA01_engine_name(self, habu):
        assert habu.name == "habu"

    def test_HA02_engine_version(self, habu):
        assert habu.version == "1.0.0"

    # ── validate() — errors ───────────────────────────────────────────────

    def test_HA03_error_zero_land_area(self, habu):
        issues = habu.validate({
            "total_land_area_sqm": 0, "max_far_allowed": 2,
            "expected_noi_per_sqm_annual": 1000,
            "development_cost_per_m2": 5000, "cap_rate": 0.08,
        })
        assert any(i.code == "INVALID_LAND_AREA" for i in issues)

    def test_HA04_error_negative_land_area(self, habu):
        issues = habu.validate({
            "total_land_area_sqm": -500, "max_far_allowed": 2,
            "expected_noi_per_sqm_annual": 1000,
            "development_cost_per_m2": 5000, "cap_rate": 0.08,
        })
        assert any(i.code == "INVALID_LAND_AREA" for i in issues)

    def test_HA05_error_zero_far(self, habu):
        issues = habu.validate({
            "total_land_area_sqm": 1000, "max_far_allowed": 0,
            "expected_noi_per_sqm_annual": 1000,
            "development_cost_per_m2": 5000, "cap_rate": 0.08,
        })
        assert any(i.code == "INVALID_FAR" for i in issues)

    def test_HA06_error_missing_noi_per_sqm(self, habu):
        issues = habu.validate({
            "total_land_area_sqm": 1000, "max_far_allowed": 2,
            "development_cost_per_m2": 5000, "cap_rate": 0.08,
        })
        assert any(i.code == "MISSING_NOI_PER_SQM" for i in issues)

    def test_HA07_error_zero_noi_per_sqm(self, habu):
        issues = habu.validate({
            "total_land_area_sqm": 1000, "max_far_allowed": 2,
            "expected_noi_per_sqm_annual": 0,
            "development_cost_per_m2": 5000, "cap_rate": 0.08,
        })
        assert any(i.code == "INVALID_NOI_PER_SQM" for i in issues)

    def test_HA08_error_missing_dev_cost(self, habu):
        issues = habu.validate({
            "total_land_area_sqm": 1000, "max_far_allowed": 2,
            "expected_noi_per_sqm_annual": 1000, "cap_rate": 0.08,
        })
        assert any(i.code == "MISSING_DEV_COST" for i in issues)

    def test_HA09_error_missing_cap_rate(self, habu):
        issues = habu.validate({
            "total_land_area_sqm": 1000, "max_far_allowed": 2,
            "expected_noi_per_sqm_annual": 1000,
            "development_cost_per_m2": 5000,
        })
        assert any(i.code == "MISSING_CAP_RATE" for i in issues)

    def test_HA10_error_cap_rate_too_high(self, habu):
        issues = habu.validate({
            "total_land_area_sqm": 1000, "max_far_allowed": 2,
            "expected_noi_per_sqm_annual": 1000,
            "development_cost_per_m2": 5000, "cap_rate": 1.5,
        })
        assert any(i.code == "INVALID_CAP_RATE" for i in issues)

    def test_HA11_warning_missing_proposed_use(self, habu, habu_full_inputs):
        inp = {k: v for k, v in habu_full_inputs.items() if k != "proposed_habu_use"}
        issues = habu.validate(inp)
        assert any(i.code == "MISSING_PROPOSED_USE" for i in issues)

    def test_HA12_warning_missing_current_use(self, habu, habu_full_inputs):
        inp = {k: v for k, v in habu_full_inputs.items() if k != "current_use"}
        issues = habu.validate(inp)
        assert any(i.code == "MISSING_CURRENT_USE" for i in issues)

    def test_HA13_error_developer_profit_rate_too_high(self, habu, habu_full_inputs):
        inp = dict(habu_full_inputs)
        inp["developer_profit_rate"] = 1.0
        issues = habu.validate(inp)
        assert any(i.code == "INVALID_DEVELOPER_PROFIT_RATE" for i in issues)

    # ── calculate() — error early-return ─────────────────────────────────

    def test_HA14_calculate_returns_none_on_errors(self, habu):
        result = habu.calculate({})
        assert result.value is None
        assert result.confidence == "insufficient"
        assert result.audit_trail == []

    # ── Formula chain ─────────────────────────────────────────────────────

    def test_HA15_buildable_area(self, habu, habu_full_inputs):
        """1 000 × 3.0 = 3 000 sqm"""
        result = habu.calculate(habu_full_inputs)
        assert abs(result.metadata["buildable_area_sqm"] - 3_000.0) < 0.01

    def test_HA16_expected_habu_noi(self, habu, habu_full_inputs):
        """3 000 × 2 000 = 6 000 000 EGP/yr"""
        result = habu.calculate(habu_full_inputs)
        assert abs(result.metadata["expected_habu_noi"] - 6_000_000.0) < 1.0

    def test_HA17_gdv(self, habu, habu_full_inputs):
        """6 000 000 / 0.08 = 75 000 000"""
        result = habu.calculate(habu_full_inputs)
        assert abs(result.metadata["gross_development_value"] - 75_000_000.0) < 1.0

    def test_HA18_development_cost(self, habu, habu_full_inputs):
        """3 000 × 5 000 = 15 000 000"""
        result = habu.calculate(habu_full_inputs)
        assert abs(result.metadata["development_cost"] - 15_000_000.0) < 1.0

    def test_HA19_developer_profit(self, habu, habu_full_inputs):
        """75 000 000 × 0.15 = 11 250 000"""
        result = habu.calculate(habu_full_inputs)
        assert abs(result.metadata["developer_profit"] - 11_250_000.0) < 1.0

    def test_HA20_residual_land_value(self, habu, habu_full_inputs):
        """75 000 000 − 15 000 000 − 11 250 000 = 48 750 000"""
        result = habu.calculate(habu_full_inputs)
        assert abs(float(result.value) - 48_750_000.0) < 1.0

    # ── Feasibility ───────────────────────────────────────────────────────

    def test_HA21_feasibility_feasible(self, habu, habu_full_inputs):
        result = habu.calculate(habu_full_inputs)
        assert result.metadata["feasibility_status"] == "feasible"

    def test_HA22_feasibility_not_feasible(self, habu, habu_full_inputs):
        """Extremely high dev cost → negative residual → not_feasible"""
        inp = dict(habu_full_inputs)
        inp["development_cost_per_m2"] = 50_000.0
        result = habu.calculate(inp)
        assert result.metadata["feasibility_status"] == "not_feasible"

    # ── Default / custom developer profit rate ────────────────────────────

    def test_HA23_default_developer_profit_rate(self, habu, habu_full_inputs):
        inp = {k: v for k, v in habu_full_inputs.items() if k != "developer_profit_rate"}
        result = habu.calculate(inp)
        assert abs(result.metadata["developer_profit_rate"] - 0.15) < 1e-9

    def test_HA24_custom_developer_profit_rate(self, habu, habu_full_inputs):
        inp = dict(habu_full_inputs)
        inp["developer_profit_rate"] = 0.20
        result = habu.calculate(inp)
        gdv    = result.metadata["gross_development_value"]
        expect = gdv * 0.20
        assert abs(result.metadata["developer_profit"] - expect) < 1.0

    # ── Confidence ────────────────────────────────────────────────────────

    def test_HA25_confidence_high_when_feasible_full_inputs(self, habu, habu_full_inputs):
        result = habu.calculate(habu_full_inputs)
        assert result.confidence == "high"

    def test_HA26_confidence_low_when_not_feasible(self, habu, habu_full_inputs):
        inp = dict(habu_full_inputs)
        inp["development_cost_per_m2"] = 50_000.0
        result = habu.calculate(inp)
        assert result.confidence == "low"

    def test_HA27_confidence_low_when_proposed_use_missing(self, habu, habu_full_inputs):
        inp = {k: v for k, v in habu_full_inputs.items() if k != "proposed_habu_use"}
        result = habu.calculate(inp)
        assert result.confidence == "low"

    def test_HA28_confidence_medium_when_existing_building(self, habu, habu_full_inputs):
        inp = dict(habu_full_inputs)
        inp["existing_building_value"] = 5_000_000.0
        result = habu.calculate(inp)
        assert result.confidence == "medium"

    # ── Audit trail ───────────────────────────────────────────────────────

    def test_HA29_audit_trail_has_seven_steps(self, habu, habu_full_inputs):
        result = habu.calculate(habu_full_inputs)
        assert len(result.audit_trail) == 7

    # ── Type / precision ─────────────────────────────────────────────────

    def test_HA30_value_is_decimal(self, habu, habu_full_inputs):
        result = habu.calculate(habu_full_inputs)
        assert isinstance(result.value, Decimal)

    def test_HA31_land_value_per_sqm(self, habu, habu_full_inputs):
        """land_value_per_sqm = residual / total_land_area"""
        result = habu.calculate(habu_full_inputs)
        expected = result.metadata["residual_land_value"] / habu_full_inputs["total_land_area_sqm"]
        assert abs(result.metadata["land_value_per_sqm"] - expected) < 0.01

    def test_HA32_validate_no_errors_for_valid_inputs(self, habu, habu_full_inputs):
        errors = [i for i in habu.validate(habu_full_inputs) if i.severity == "error"]
        assert errors == []

    def test_HA33_cap_rate_zero_is_error(self, habu, habu_full_inputs):
        inp = dict(habu_full_inputs)
        inp["cap_rate"] = 0.0
        issues = habu.validate(inp)
        assert any(i.code == "INVALID_CAP_RATE" for i in issues)

    def test_HA34_assumptions_list_present(self, habu, habu_full_inputs):
        result = habu.calculate(habu_full_inputs)
        assert isinstance(result.metadata.get("assumptions"), list)
        assert len(result.metadata["assumptions"]) > 0

    def test_HA35_no_external_dependencies(self):
        """HABUEngine must not import bridge_api, qdrant, requests, httpx, or urllib."""
        import importlib
        mod = importlib.import_module("core_engine.engines.habu_engine")
        source = Path(mod.__file__).read_text(encoding="utf-8")
        for forbidden in ("bridge_api", "qdrant", "requests", "httpx", "urllib"):
            assert forbidden not in source, (
                f"habu_engine.py must not import '{forbidden}'"
            )


# ===========================================================================
# Sales Comparison Engine Tests (SC01–SC30+)
# ===========================================================================

class TestSalesComparisonEngine:

    # ── Identity ──────────────────────────────────────────────────────────

    def test_SC01_engine_name(self, sc):
        assert sc.name == "sales_comparison"

    def test_SC02_engine_version(self, sc):
        assert sc.version == "1.0.0"

    # ── validate() — errors ───────────────────────────────────────────────

    def test_SC03_error_empty_comparables_list(self, sc):
        issues = sc.validate({"subject_area_sqm": 100, "comparables": []})
        assert any(i.code == "NO_COMPARABLES" for i in issues)

    def test_SC04_error_comparables_key_absent(self, sc):
        issues = sc.validate({"subject_area_sqm": 100})
        assert any(i.code == "NO_COMPARABLES" for i in issues)

    def test_SC05_error_subject_area_zero(self, sc):
        issues = sc.validate({
            "subject_area_sqm": 0,
            "comparables": [{"price_per_m2": 10_000}],
        })
        assert any(i.code == "INVALID_SUBJECT_AREA" for i in issues)

    def test_SC06_error_subject_area_negative(self, sc):
        issues = sc.validate({
            "subject_area_sqm": -50,
            "comparables": [{"price_per_m2": 10_000}],
        })
        assert any(i.code == "INVALID_SUBJECT_AREA" for i in issues)

    def test_SC07_error_comp_price_zero(self, sc):
        issues = sc.validate({
            "subject_area_sqm": 100,
            "comparables": [
                {"price_per_m2": 10_000},
                {"price_per_m2": 0},
                {"price_per_m2": 12_000},
            ],
        })
        assert any("INVALID_COMP_PRICE" in i.code for i in issues)

    def test_SC08_warning_large_location_adjustment(self, sc):
        issues = sc.validate({
            "subject_area_sqm": 100,
            "comparables": [
                {"price_per_m2": 10_000, "location_adjustment": 0.50},
                {"price_per_m2": 11_000},
                {"price_per_m2": 12_000},
            ],
        })
        assert any("LARGE_ADJUSTMENT" in i.code and i.severity == "warning" for i in issues)

    # ── validate() — warnings ─────────────────────────────────────────────

    def test_SC09_warning_one_comparable(self, sc):
        issues = sc.validate({
            "subject_area_sqm": 100,
            "comparables": [{"price_per_m2": 10_000}],
        })
        assert any(i.code == "INSUFFICIENT_COMPARABLES" for i in issues)

    def test_SC10_warning_two_comparables(self, sc):
        issues = sc.validate({
            "subject_area_sqm": 100,
            "comparables": [
                {"price_per_m2": 10_000},
                {"price_per_m2": 12_000},
            ],
        })
        assert any(i.code == "INSUFFICIENT_COMPARABLES" for i in issues)

    # ── calculate() — error early-return ─────────────────────────────────

    def test_SC11_calculate_returns_none_no_comps(self, sc):
        result = sc.calculate({"subject_area_sqm": 100, "comparables": []})
        assert result.value is None
        assert result.confidence == "insufficient"
        assert result.audit_trail == []

    # ── Adjustment formula ────────────────────────────────────────────────

    def test_SC12_zero_adjustments_passthrough(self, sc):
        """When all adjustments = 0, adjusted_ppm == price_per_m2"""
        result = sc.calculate({
            "subject_area_sqm": 100,
            "comparables": [
                {"price_per_m2": 10_000},
                {"price_per_m2": 10_000},
                {"price_per_m2": 10_000},
            ],
        })
        assert result.metadata["avg_adjusted_price_per_m2"] == pytest.approx(10_000.0, rel=1e-6)

    def test_SC13_positive_adjustments(self, sc):
        """10 000 × 1.05 × 1.10 × 1.00 = 11 550 (three identical comps)"""
        result = sc.calculate({
            "subject_area_sqm": 50,
            "comparables": [
                {"price_per_m2": 10_000, "location_adjustment": 0.05, "physical_adjustment": 0.10},
                {"price_per_m2": 10_000, "location_adjustment": 0.05, "physical_adjustment": 0.10},
                {"price_per_m2": 10_000, "location_adjustment": 0.05, "physical_adjustment": 0.10},
            ],
        })
        assert result.metadata["avg_adjusted_price_per_m2"] == pytest.approx(11_550.0, rel=1e-6)

    def test_SC14_negative_adjustments(self, sc):
        """20 000 × 0.95 × 0.90 × 1.00 = 17 100 (three identical comps)"""
        result = sc.calculate({
            "subject_area_sqm": 100,
            "comparables": [
                {"price_per_m2": 20_000, "location_adjustment": -0.05, "physical_adjustment": -0.10},
                {"price_per_m2": 20_000, "location_adjustment": -0.05, "physical_adjustment": -0.10},
                {"price_per_m2": 20_000, "location_adjustment": -0.05, "physical_adjustment": -0.10},
            ],
        })
        expected = 20_000 * 0.95 * 0.90
        assert result.metadata["avg_adjusted_price_per_m2"] == pytest.approx(expected, rel=1e-6)

    def test_SC15_average_adjusted_ppm_is_mean(self, sc, sc_three_comps):
        """avg_adjusted_ppm must equal the arithmetic mean of per-comp adjusted prices"""
        result = sc.calculate(sc_three_comps)
        summary = result.metadata["adjustment_summary"]
        manual_avg = sum(s["adjusted_price_per_m2"] for s in summary) / len(summary)
        assert result.metadata["avg_adjusted_price_per_m2"] == pytest.approx(manual_avg, rel=1e-4)

    def test_SC16_indicated_value_formula(self, sc, sc_three_comps):
        """indicated_value = avg_adjusted_ppm × subject_area (100 sqm)"""
        result = sc.calculate(sc_three_comps)
        expected = result.metadata["avg_adjusted_price_per_m2"] * 100.0
        assert float(result.value) == pytest.approx(expected, rel=1e-4)

    def test_SC17_exact_three_comp_formula(self, sc):
        """
        comp 0: 20 000 × 1.05 × 0.90 × 1.00 = 18 900
        comp 1: 22 000 × 1.00 × 1.00 × 0.95 = 20 900
        comp 2: 19 000 × 1.10 × 1.00 × 1.00 = 20 900
        avg = 60 700 / 3 ≈ 20 233.33
        indicated = 20 233.33 × 100 ≈ 2 023 333.33
        """
        result = sc.calculate({
            "subject_area_sqm": 100.0,
            "comparables": [
                {"price_per_m2": 20_000, "location_adjustment": 0.05,
                 "physical_adjustment": -0.10},
                {"price_per_m2": 22_000, "market_condition_adjustment": -0.05},
                {"price_per_m2": 19_000, "location_adjustment": 0.10},
            ],
        })
        assert result.metadata["avg_adjusted_price_per_m2"] == pytest.approx(20_233.333, rel=1e-4)
        assert float(result.value) == pytest.approx(2_023_333.33, rel=1e-4)

    def test_SC18_mixed_adjustments_compound_correctly(self, sc):
        """loc=-0.05, phy=-0.10, mkt=-0.05 → factor = 0.95 × 0.90 × 0.95 = 0.81225"""
        result = sc.calculate({
            "subject_area_sqm": 100,
            "comparables": [
                {"price_per_m2": 10_000, "location_adjustment": -0.05,
                 "physical_adjustment": -0.10, "market_condition_adjustment": -0.05},
                {"price_per_m2": 10_000, "location_adjustment": -0.05,
                 "physical_adjustment": -0.10, "market_condition_adjustment": -0.05},
                {"price_per_m2": 10_000, "location_adjustment": -0.05,
                 "physical_adjustment": -0.10, "market_condition_adjustment": -0.05},
            ],
        })
        expected_adj = 10_000 * 0.95 * 0.90 * 0.95
        assert result.metadata["avg_adjusted_price_per_m2"] == pytest.approx(expected_adj, rel=1e-6)

    # ── Confidence ────────────────────────────────────────────────────────

    def test_SC19_confidence_low_one_comp(self, sc):
        result = sc.calculate({
            "subject_area_sqm": 100,
            "comparables": [{"price_per_m2": 10_000}],
        })
        assert result.confidence == "low"

    def test_SC20_confidence_high_three_uniform_comps(self, sc):
        """All same price, no adjustments → CV=0 → high"""
        result = sc.calculate({
            "subject_area_sqm": 100,
            "comparables": [
                {"price_per_m2": 10_000},
                {"price_per_m2": 10_000},
                {"price_per_m2": 10_000},
            ],
        })
        assert result.confidence == "high"

    def test_SC21_confidence_medium_high_cv(self, sc):
        """Widely dispersed prices → CV > 20% → medium"""
        result = sc.calculate({
            "subject_area_sqm": 100,
            "comparables": [
                {"price_per_m2": 5_000},
                {"price_per_m2": 25_000},
                {"price_per_m2": 5_000},
            ],
        })
        assert result.confidence == "medium"

    def test_SC22_confidence_medium_large_adj(self, sc):
        """Any individual adjustment > 20% → medium (even when CV is low)"""
        result = sc.calculate({
            "subject_area_sqm": 100,
            "comparables": [
                {"price_per_m2": 10_000, "location_adjustment": 0.25},
                {"price_per_m2": 10_000, "location_adjustment": 0.25},
                {"price_per_m2": 10_000, "location_adjustment": 0.25},
            ],
        })
        assert result.confidence == "medium"

    # ── Metadata ──────────────────────────────────────────────────────────

    def test_SC23_metadata_comparable_count(self, sc, sc_three_comps):
        result = sc.calculate(sc_three_comps)
        assert result.metadata["comparable_count"] == 3

    def test_SC24_metadata_average_price_is_unadjusted_mean(self, sc, sc_three_comps):
        result = sc.calculate(sc_three_comps)
        expected_raw = (20_000 + 22_000 + 19_000) / 3
        assert result.metadata["average_price_per_m2"] == pytest.approx(expected_raw, rel=1e-4)

    def test_SC25_adjustment_summary_has_entry_per_comp(self, sc, sc_three_comps):
        result = sc.calculate(sc_three_comps)
        assert len(result.metadata["adjustment_summary"]) == 3

    def test_SC26_comp_label_preserved(self, sc, sc_three_comps):
        result = sc.calculate(sc_three_comps)
        summary = result.metadata["adjustment_summary"]
        assert summary[0].get("label") == "Comp A"
        assert "label" not in summary[1]

    def test_SC27_audit_trail_has_n_plus_two_entries(self, sc, sc_three_comps):
        """3 comps + 1 average step + 1 indicated step = 5 entries"""
        result = sc.calculate(sc_three_comps)
        assert len(result.audit_trail) == 5

    def test_SC28_metadata_warnings_populated_from_issues(self, sc):
        result = sc.calculate({
            "subject_area_sqm": 100,
            "comparables": [
                {"price_per_m2": 10_000, "location_adjustment": 0.50},
                {"price_per_m2": 10_000},
                {"price_per_m2": 10_000},
            ],
        })
        assert any("50" in w for w in result.metadata["warnings"])

    def test_SC29_value_is_decimal(self, sc, sc_three_comps):
        result = sc.calculate(sc_three_comps)
        assert isinstance(result.value, Decimal)

    def test_SC30_coefficient_of_variation_none_for_single_comp(self, sc):
        result = sc.calculate({
            "subject_area_sqm": 100,
            "comparables": [{"price_per_m2": 10_000}],
        })
        assert result.metadata["coefficient_of_variation"] is None

    def test_SC31_assumptions_list_present(self, sc, sc_three_comps):
        result = sc.calculate(sc_three_comps)
        assert isinstance(result.metadata.get("assumptions"), list)
        assert len(result.metadata["assumptions"]) > 0

    def test_SC32_indicated_value_matches_metadata(self, sc, sc_three_comps):
        result = sc.calculate(sc_three_comps)
        assert float(result.value) == pytest.approx(result.metadata["indicated_value"], rel=1e-6)

    def test_SC33_no_external_dependencies(self):
        """SalesComparisonEngine must not import bridge_api, qdrant, requests, etc."""
        import importlib
        mod = importlib.import_module("core_engine.engines.sales_comparison_engine")
        source = Path(mod.__file__).read_text(encoding="utf-8")
        for forbidden in ("bridge_api", "qdrant", "requests", "httpx", "urllib"):
            assert forbidden not in source, (
                f"sales_comparison_engine.py must not import '{forbidden}'"
            )

    def test_SC34_adjustment_summary_index_matches_position(self, sc, sc_three_comps):
        result = sc.calculate(sc_three_comps)
        for i, entry in enumerate(result.metadata["adjustment_summary"]):
            assert entry["index"] == i

    def test_SC35_single_comp_issues_contain_insufficient_warning(self, sc):
        result = sc.calculate({
            "subject_area_sqm": 100,
            "comparables": [{"price_per_m2": 15_000}],
        })
        codes = [i.code for i in result.issues]
        assert "INSUFFICIENT_COMPARABLES" in codes
