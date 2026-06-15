"""
Tests for CostApproachEngine (CA01–CA30) and IncomeApproachEngine (IA01–IA30).
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

from core_engine.engines.cost_approach_engine import CostApproachEngine
from core_engine.engines.income_approach_engine import IncomeApproachEngine
from core_engine.engines.base import EngineResult, ValidationIssue


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def ca() -> CostApproachEngine:
    return CostApproachEngine()


@pytest.fixture
def ia() -> IncomeApproachEngine:
    return IncomeApproachEngine()


@pytest.fixture
def ca_full_inputs() -> dict:
    """Full cost approach scenario.

    RCN  = 200 × 10 000                     = 2 000 000
    dep  = 0.20 + 0.10 + 0.05               = 0.35
    DRC  = 2 000 000 × (1 − 0.35)           = 1 300 000
    land = 500 000
    val  = 1 300 000 + 500 000              = 1 800 000
    """
    return {
        "building_area_sqm":       200.0,
        "cost_per_m2":             10_000.0,
        "land_value":              500_000.0,
        "physical_depreciation":   0.20,
        "functional_obsolescence": 0.10,
        "external_obsolescence":   0.05,
    }


@pytest.fixture
def ia_full_inputs() -> dict:
    """Full income approach scenario.

    gross   = 1 000 000
    vacancy = 0.10  → EGI = 900 000
    op_exp  = 270 000 (absolute)
    NOI     = 900 000 − 270 000 = 630 000
    cap     = 0.07
    value   = 630 000 / 0.07 = 9 000 000
    ratio   = 270 000 / 900 000 = 0.30
    """
    return {
        "gross_income":        1_000_000.0,
        "vacancy_rate":        0.10,
        "operating_expenses":  270_000.0,
        "cap_rate":            0.07,
    }


# ===========================================================================
# CostApproachEngine Tests (CA01–CA30)
# ===========================================================================

class TestCostApproachEngine:

    # ── Identity ──────────────────────────────────────────────────────────

    def test_CA01_engine_name(self, ca):
        assert ca.name == "cost_approach"

    def test_CA02_engine_version(self, ca):
        assert ca.version == "1.0.0"

    # ── validate() — errors ───────────────────────────────────────────────

    def test_CA03_error_zero_building_area(self, ca):
        issues = ca.validate({
            "building_area_sqm": 0, "cost_per_m2": 10_000, "land_value": 100_000,
        })
        assert any(i.code == "INVALID_BUILDING_AREA" for i in issues)

    def test_CA04_error_negative_building_area(self, ca):
        issues = ca.validate({
            "building_area_sqm": -50, "cost_per_m2": 10_000, "land_value": 100_000,
        })
        assert any(i.code == "INVALID_BUILDING_AREA" for i in issues)

    def test_CA05_error_negative_land_value(self, ca):
        issues = ca.validate({
            "building_area_sqm": 100, "cost_per_m2": 10_000, "land_value": -1,
        })
        assert any(i.code == "INVALID_LAND_VALUE" for i in issues)

    def test_CA06_error_missing_land_value(self, ca):
        issues = ca.validate({
            "building_area_sqm": 100, "cost_per_m2": 10_000,
        })
        assert any(i.code == "MISSING_LAND_VALUE" for i in issues)

    def test_CA07_error_missing_cost_input(self, ca):
        issues = ca.validate({
            "building_area_sqm": 100, "land_value": 100_000,
        })
        assert any(i.code == "MISSING_COST_INPUT" for i in issues)

    def test_CA08_error_invalid_cost_per_m2(self, ca):
        issues = ca.validate({
            "building_area_sqm": 100, "cost_per_m2": 0, "land_value": 100_000,
        })
        assert any(i.code == "INVALID_COST_PER_M2" for i in issues)

    def test_CA09_error_depreciation_rate_exceeds_one(self, ca):
        issues = ca.validate({
            "building_area_sqm": 100, "cost_per_m2": 10_000,
            "land_value": 100_000, "depreciation_rate": 1.5,
        })
        assert any(i.code == "INVALID_DEPRECIATION_RATE" for i in issues)

    def test_CA10_error_invalid_physical_depreciation(self, ca):
        issues = ca.validate({
            "building_area_sqm": 100, "cost_per_m2": 10_000,
            "land_value": 100_000, "physical_depreciation": -0.1,
        })
        assert any("INVALID_PHYSICAL_DEPRECIATION" in i.code for i in issues)

    # ── validate() — warnings ─────────────────────────────────────────────

    def test_CA11_warning_zero_depreciation(self, ca):
        issues = ca.validate({
            "building_area_sqm": 100, "cost_per_m2": 10_000, "land_value": 100_000,
        })
        assert any(i.code == "ZERO_DEPRECIATION" for i in issues)

    def test_CA12_warning_zero_land_value(self, ca):
        issues = ca.validate({
            "building_area_sqm": 100, "cost_per_m2": 10_000, "land_value": 0,
        })
        assert any(i.code == "ZERO_LAND_VALUE" for i in issues)

    # ── calculate() — error early-return ─────────────────────────────────

    def test_CA13_calculate_returns_none_on_errors(self, ca):
        result = ca.calculate({"building_area_sqm": 0, "cost_per_m2": 10_000, "land_value": 0})
        assert result.value is None
        assert result.confidence == "insufficient"
        assert result.audit_trail == []

    # ── Formula chain ─────────────────────────────────────────────────────

    def test_CA14_rcn_from_area_times_cost(self, ca, ca_full_inputs):
        """RCN = 200 × 10 000 = 2 000 000"""
        result = ca.calculate(ca_full_inputs)
        assert abs(result.metadata["replacement_cost_new"] - 2_000_000.0) < 1.0

    def test_CA15_rcn_override_takes_precedence(self, ca, ca_full_inputs):
        """caller-supplied RCN overrides area × cost_per_m2"""
        inp = dict(ca_full_inputs)
        inp["replacement_cost_new"] = 3_500_000.0
        result = ca.calculate(inp)
        assert abs(result.metadata["replacement_cost_new"] - 3_500_000.0) < 1.0

    def test_CA16_three_depreciation_forms_sum(self, ca, ca_full_inputs):
        """total_dep = 0.20 + 0.10 + 0.05 = 0.35"""
        result = ca.calculate(ca_full_inputs)
        assert abs(result.metadata["total_depreciation_rate"] - 0.35) < 1e-6

    def test_CA17_depreciation_clamped_to_one(self, ca):
        """0.60 + 0.30 + 0.20 = 1.10 → clamped to 1.0 → DRC = 0"""
        result = ca.calculate({
            "building_area_sqm":       100,
            "cost_per_m2":             10_000,
            "land_value":              200_000,
            "physical_depreciation":   0.60,
            "functional_obsolescence": 0.30,
            "external_obsolescence":   0.20,
        })
        assert abs(result.metadata["total_depreciation_rate"] - 1.0) < 1e-6
        assert abs(result.metadata["depreciated_replacement_cost"] - 0.0) < 1.0

    def test_CA18_depreciation_rate_override(self, ca, ca_full_inputs):
        """depreciation_rate=0.40 overrides individual components"""
        inp = dict(ca_full_inputs)
        inp["depreciation_rate"] = 0.40
        result = ca.calculate(inp)
        assert abs(result.metadata["total_depreciation_rate"] - 0.40) < 1e-6

    def test_CA19_drc_formula(self, ca, ca_full_inputs):
        """DRC = 2 000 000 × (1 − 0.35) = 1 300 000"""
        result = ca.calculate(ca_full_inputs)
        assert abs(result.metadata["depreciated_replacement_cost"] - 1_300_000.0) < 1.0

    def test_CA20_final_value_formula(self, ca, ca_full_inputs):
        """final = DRC + land = 1 300 000 + 500 000 = 1 800 000"""
        result = ca.calculate(ca_full_inputs)
        assert abs(float(result.value) - 1_800_000.0) < 1.0

    def test_CA21_fully_depreciated_value_equals_land(self, ca):
        """depreciation_rate=1.0 → DRC=0 → value = land_value"""
        result = ca.calculate({
            "building_area_sqm":  100,
            "cost_per_m2":        10_000,
            "land_value":         300_000,
            "depreciation_rate":  1.0,
        })
        assert abs(float(result.value) - 300_000.0) < 1.0

    def test_CA22_physical_only(self, ca):
        """Only physical_depreciation=0.25; func=ext=0"""
        result = ca.calculate({
            "building_area_sqm":     100,
            "cost_per_m2":           10_000,
            "land_value":            200_000,
            "physical_depreciation": 0.25,
        })
        # RCN=1_000_000; DRC=750_000; final=950_000
        assert abs(float(result.value) - 950_000.0) < 1.0

    def test_CA23_functional_only(self, ca):
        """Only functional_obsolescence=0.30"""
        result = ca.calculate({
            "building_area_sqm":       100,
            "cost_per_m2":             10_000,
            "land_value":              100_000,
            "functional_obsolescence": 0.30,
        })
        # RCN=1_000_000; DRC=700_000; final=800_000
        assert abs(float(result.value) - 800_000.0) < 1.0

    # ── Confidence ────────────────────────────────────────────────────────

    def test_CA24_confidence_high_normal_case(self, ca, ca_full_inputs):
        result = ca.calculate(ca_full_inputs)
        assert result.confidence == "high"

    def test_CA25_confidence_low_when_land_zero(self, ca):
        result = ca.calculate({
            "building_area_sqm":     100,
            "cost_per_m2":           10_000,
            "land_value":            0,
            "physical_depreciation": 0.20,
        })
        assert result.confidence == "low"

    def test_CA26_confidence_medium_high_depreciation(self, ca):
        """total_dep ≥ 0.80 → medium confidence"""
        result = ca.calculate({
            "building_area_sqm":       100,
            "cost_per_m2":             10_000,
            "land_value":              200_000,
            "physical_depreciation":   0.50,
            "functional_obsolescence": 0.30,
            "external_obsolescence":   0.10,
        })
        assert result.confidence == "medium"

    # ── Audit trail & type ────────────────────────────────────────────────

    def test_CA27_audit_trail_has_four_steps(self, ca, ca_full_inputs):
        result = ca.calculate(ca_full_inputs)
        assert len(result.audit_trail) == 4

    def test_CA28_value_is_decimal(self, ca, ca_full_inputs):
        result = ca.calculate(ca_full_inputs)
        assert isinstance(result.value, Decimal)

    def test_CA29_metadata_contains_expected_keys(self, ca, ca_full_inputs):
        result = ca.calculate(ca_full_inputs)
        for key in (
            "replacement_cost_new", "physical_depreciation",
            "functional_obsolescence", "external_obsolescence",
            "total_depreciation_rate", "depreciated_replacement_cost",
            "land_value", "final_cost_approach_value",
        ):
            assert key in result.metadata, f"Missing metadata key: {key}"

    def test_CA30_no_external_dependencies(self):
        import importlib
        mod = importlib.import_module("core_engine.engines.cost_approach_engine")
        source = Path(mod.__file__).read_text(encoding="utf-8")
        for forbidden in ("bridge_api", "qdrant", "requests", "httpx", "urllib"):
            assert forbidden not in source, (
                f"cost_approach_engine.py must not import '{forbidden}'"
            )


# ===========================================================================
# IncomeApproachEngine Tests (IA01–IA30)
# ===========================================================================

class TestIncomeApproachEngine:

    # ── Identity ──────────────────────────────────────────────────────────

    def test_IA01_engine_name(self, ia):
        assert ia.name == "income_approach"

    def test_IA02_engine_version(self, ia):
        assert ia.version == "1.0.0"

    # ── validate() — errors ───────────────────────────────────────────────

    def test_IA03_error_zero_gross_income(self, ia):
        issues = ia.validate({"gross_income": 0, "cap_rate": 0.08})
        assert any(i.code == "INVALID_GROSS_INCOME" for i in issues)

    def test_IA04_error_negative_gross_income(self, ia):
        issues = ia.validate({"gross_income": -100, "cap_rate": 0.08})
        assert any(i.code == "INVALID_GROSS_INCOME" for i in issues)

    def test_IA05_error_cap_rate_zero(self, ia):
        """cap_rate = 0 must be an error — division by zero safety"""
        issues = ia.validate({"gross_income": 100_000, "cap_rate": 0})
        assert any(i.code == "INVALID_CAP_RATE_ZERO" for i in issues)

    def test_IA06_error_cap_rate_negative(self, ia):
        issues = ia.validate({"gross_income": 100_000, "cap_rate": -0.05})
        assert any(i.code == "INVALID_CAP_RATE_ZERO" for i in issues)

    def test_IA07_error_missing_cap_rate(self, ia):
        issues = ia.validate({"gross_income": 100_000})
        assert any(i.code == "MISSING_CAP_RATE" for i in issues)

    def test_IA08_error_invalid_vacancy_rate(self, ia):
        issues = ia.validate({"gross_income": 100_000, "cap_rate": 0.08, "vacancy_rate": 1.5})
        assert any(i.code == "INVALID_VACANCY_RATE" for i in issues)

    def test_IA09_error_negative_operating_expenses(self, ia):
        issues = ia.validate({
            "gross_income": 100_000, "cap_rate": 0.08, "operating_expenses": -1000,
        })
        assert any(i.code == "INVALID_OPERATING_EXPENSES" for i in issues)

    def test_IA10_error_expense_ratio_ge_one(self, ia):
        issues = ia.validate({
            "gross_income": 100_000, "cap_rate": 0.08, "operating_expense_ratio": 1.0,
        })
        assert any(i.code == "INVALID_EXPENSE_RATIO" for i in issues)

    # ── validate() — warnings ─────────────────────────────────────────────

    def test_IA11_warning_missing_operating_expenses(self, ia):
        issues = ia.validate({"gross_income": 100_000, "cap_rate": 0.08})
        assert any(i.code == "MISSING_OPERATING_EXPENSES" for i in issues)

    def test_IA12_warning_high_vacancy_rate(self, ia):
        issues = ia.validate({
            "gross_income": 100_000, "cap_rate": 0.08,
            "vacancy_rate": 0.60, "operating_expenses": 20_000,
        })
        assert any(i.code == "HIGH_VACANCY_RATE" for i in issues)

    def test_IA13_warning_cap_rate_out_of_range(self, ia):
        issues = ia.validate({
            "gross_income": 100_000, "cap_rate": 0.35, "operating_expenses": 20_000,
        })
        assert any(i.code == "CAP_RATE_OUT_OF_RANGE" for i in issues)

    # ── calculate() — error early-return ─────────────────────────────────

    def test_IA14_calculate_returns_none_on_errors(self, ia):
        result = ia.calculate({"gross_income": 0, "cap_rate": 0.08})
        assert result.value is None
        assert result.confidence == "insufficient"
        assert result.audit_trail == []

    def test_IA15_cap_rate_zero_no_zero_division(self, ia):
        """cap_rate=0 must return error result, never raise ZeroDivisionError"""
        try:
            result = ia.calculate({
                "gross_income": 1_000_000, "operating_expenses": 300_000, "cap_rate": 0,
            })
            assert result.value is None
        except ZeroDivisionError:
            pytest.fail("IncomeApproachEngine raised ZeroDivisionError for cap_rate=0")

    # ── Formula chain ─────────────────────────────────────────────────────

    def test_IA16_egi_formula(self, ia, ia_full_inputs):
        """EGI = 1 000 000 × (1 − 0.10) = 900 000"""
        result = ia.calculate(ia_full_inputs)
        assert abs(result.metadata["effective_gross_income"] - 900_000.0) < 1.0

    def test_IA17_zero_vacancy_egi_equals_gross(self, ia):
        result = ia.calculate({
            "gross_income": 500_000, "vacancy_rate": 0,
            "operating_expenses": 100_000, "cap_rate": 0.08,
        })
        assert abs(result.metadata["effective_gross_income"] - 500_000.0) < 1.0

    def test_IA18_noi_from_absolute_expenses(self, ia, ia_full_inputs):
        """NOI = 900 000 − 270 000 = 630 000"""
        result = ia.calculate(ia_full_inputs)
        assert abs(result.metadata["noi"] - 630_000.0) < 1.0

    def test_IA19_income_value_formula(self, ia, ia_full_inputs):
        """income_value = 630 000 / 0.07 = 9 000 000"""
        result = ia.calculate(ia_full_inputs)
        assert abs(float(result.value) - 9_000_000.0) < 1.0

    def test_IA20_expense_ratio_derived(self, ia, ia_full_inputs):
        """expense_ratio = 270 000 / 900 000 = 0.30"""
        result = ia.calculate(ia_full_inputs)
        assert abs(result.metadata["expense_ratio"] - 0.30) < 1e-4

    def test_IA21_operating_expenses_from_ratio(self, ia):
        """Derive expenses from operating_expense_ratio when absolute not supplied.

        gross=1_000_000, vacancy=0, EGI=1_000_000
        ratio=0.40 → op_exp=400_000; NOI=600_000; value=600_000/0.08=7_500_000
        """
        result = ia.calculate({
            "gross_income":             1_000_000,
            "vacancy_rate":             0,
            "operating_expense_ratio":  0.40,
            "cap_rate":                 0.08,
        })
        assert abs(result.metadata["operating_expenses"] - 400_000.0) < 1.0
        assert abs(float(result.value) - 7_500_000.0) < 1.0

    def test_IA22_absolute_expenses_take_priority_over_ratio(self, ia):
        """When both supplied, absolute operating_expenses takes priority."""
        result = ia.calculate({
            "gross_income":             1_000_000,
            "vacancy_rate":             0,
            "operating_expenses":       200_000,     # absolute — should win
            "operating_expense_ratio":  0.50,        # would give 500_000 — ignored
            "cap_rate":                 0.08,
        })
        assert abs(result.metadata["operating_expenses"] - 200_000.0) < 1.0

    def test_IA23_zero_expenses_noi_equals_egi(self, ia):
        """No expenses supplied → NOI = EGI (warning already raised)"""
        result = ia.calculate({
            "gross_income": 800_000,
            "vacancy_rate": 0,
            "cap_rate":     0.10,
        })
        # NOI = 800_000; value = 8_000_000
        assert abs(result.metadata["noi"] - 800_000.0) < 1.0
        assert abs(float(result.value) - 8_000_000.0) < 1.0

    def test_IA24_non_positive_noi_returns_none(self, ia):
        """operating_expenses ≥ EGI → NOI ≤ 0 → value = None"""
        result = ia.calculate({
            "gross_income":       500_000,
            "vacancy_rate":       0,
            "operating_expenses": 600_000,   # exceeds EGI
            "cap_rate":           0.08,
        })
        assert result.value is None
        assert result.confidence == "insufficient"
        assert any(i.code == "NON_POSITIVE_NOI" for i in result.issues)

    # ── Confidence ────────────────────────────────────────────────────────

    def test_IA25_confidence_high_normal_case(self, ia, ia_full_inputs):
        """cap in range (7%), vacancy=10% ≤ 30% → high"""
        result = ia.calculate(ia_full_inputs)
        assert result.confidence == "high"

    def test_IA26_confidence_medium_high_vacancy(self, ia):
        """cap in range but vacancy > 30% → medium"""
        result = ia.calculate({
            "gross_income":       1_000_000,
            "vacancy_rate":       0.40,
            "operating_expenses": 200_000,
            "cap_rate":           0.08,
        })
        assert result.confidence == "medium"

    def test_IA27_confidence_low_cap_rate_out_of_range(self, ia):
        """cap_rate outside [4%, 20%] → low"""
        result = ia.calculate({
            "gross_income":       1_000_000,
            "vacancy_rate":       0,
            "operating_expenses": 200_000,
            "cap_rate":           0.35,
        })
        assert result.confidence == "low"

    # ── Audit trail & type ────────────────────────────────────────────────

    def test_IA28_audit_trail_has_four_steps_normal(self, ia, ia_full_inputs):
        """4 steps for normal path: EGI, expenses, NOI, capitalise"""
        result = ia.calculate(ia_full_inputs)
        assert len(result.audit_trail) == 4

    def test_IA29_value_is_decimal(self, ia, ia_full_inputs):
        result = ia.calculate(ia_full_inputs)
        assert isinstance(result.value, Decimal)

    def test_IA30_no_external_dependencies(self):
        import importlib
        mod = importlib.import_module("core_engine.engines.income_approach_engine")
        source = Path(mod.__file__).read_text(encoding="utf-8")
        for forbidden in ("bridge_api", "qdrant", "requests", "httpx", "urllib"):
            assert forbidden not in source, (
                f"income_approach_engine.py must not import '{forbidden}'"
            )
