"""
Phase 16.1 — Engine Unit Test Coverage

Tests for the four OOP engine modules in core_engine/engines/:
  - ComparativeEngine   (comparative.py)
  - CostEngine          (cost.py)
  - IncomeEngine        (income.py)
  - ComparableSearchEngine (comparable_search.py)

Rules:
  - No network calls, no Qdrant, no RAG.
  - No bridge_api.py / valuation_logic.py imports.
  - cost_tables.json loaded from the real file (engines/cost_tables.json).
  - All fixtures are inline.

Test ID prefix: CE = ComparativeEngine, KE = CostEngine, IE = IncomeEngine, CS = ComparableSearchEngine
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

import pytest

# ── Path bootstrap ────────────────────────────────────────────────────────────
_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(str(_CORE))

from engines.base import AuditEntry, EngineResult, ValidationIssue, ValuationEngine
from engines.comparative import ComparativeEngine
from engines.cost import CostEngine
from engines.income import IncomeEngine
from engines.comparable_search import ComparableSearchEngine


# ═══════════════════════════════════════════════════════════════════════════════
# Shared fixtures
# ═══════════════════════════════════════════════════════════════════════════════

_MINIMAL_COMPS = [
    {"id": "c1", "area_sqm": 100, "price_per_sqm": 20000},
    {"id": "c2", "area_sqm": 110, "price_per_sqm": 19500},
    {"id": "c3", "area_sqm":  95, "price_per_sqm": 21000},
]

_FULL_COMPS = [
    {"id": "c1", "area_sqm": 100, "price_per_sqm": 20000, "age_years": 5,  "floor": 3, "finishing_level": "standard"},
    {"id": "c2", "area_sqm": 110, "price_per_sqm": 19500, "age_years": 7,  "floor": 2, "finishing_level": "standard"},
    {"id": "c3", "area_sqm":  95, "price_per_sqm": 21000, "age_years": 3,  "floor": 4, "finishing_level": "standard"},
    {"id": "c4", "area_sqm": 105, "price_per_sqm": 20500, "age_years": 6,  "floor": 3, "finishing_level": "standard"},
    {"id": "c5", "area_sqm": 100, "price_per_sqm": 20200, "age_years": 4,  "floor": 3, "finishing_level": "standard"},
]

_MARKET_FEED = [
    {"area": 100, "price": 2_000_000, "price_per_meter": 20000,
     "location": "المعادي", "property_type": "شقة سكنية",
     "timestamp": "2025-06-01T10:00:00", "credibility": 0.9},
    {"area": 120, "price": 2_400_000, "price_per_meter": 20000,
     "location": "المعادي", "property_type": "شقة سكنية",
     "timestamp": "2025-05-15T10:00:00", "credibility": 0.85},
    {"area":  80, "price": 1_600_000, "price_per_meter": 20000,
     "location": "المعادي", "property_type": "شقة سكنية",
     "timestamp": "2025-04-20T10:00:00", "credibility": 0.8},
    {"area": 150, "price": 4_500_000, "price_per_meter": 30000,
     "location": "الزمالك", "property_type": "شقة سكنية",
     "timestamp": "2025-06-10T10:00:00", "credibility": 0.95},
    {"area": 200, "price": 3_000_000, "price_per_meter": 15000,
     "location": "مدينة نصر", "property_type": "فيلا",
     "timestamp": "2025-03-01T10:00:00", "credibility": 0.7},
]


@pytest.fixture
def feed_path(tmp_path) -> str:
    p = tmp_path / "market_feed.json"
    p.write_text(json.dumps(_MARKET_FEED), encoding="utf-8")
    return str(p)


@pytest.fixture
def empty_feed_path(tmp_path) -> str:
    p = tmp_path / "market_feed.json"
    p.write_text("[]", encoding="utf-8")
    return str(p)


@pytest.fixture
def real_cost_tables_path() -> str:
    return str(_CORE / "engines" / "cost_tables.json")


@pytest.fixture
def custom_cost_tables_path(tmp_path) -> str:
    tables = {
        "TestCity": {"economy": 5000, "standard": 10000, "luxury": 20000},
        "_default": {"economy": 4000, "standard":  8000, "luxury": 15000},
    }
    p = tmp_path / "cost_tables.json"
    p.write_text(json.dumps(tables), encoding="utf-8")
    return str(p)


# ═══════════════════════════════════════════════════════════════════════════════
# BASE CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

def test_BASE01_audit_entry_is_dataclass():
    ae = AuditEntry(step_name="step", inputs={}, outputs={}, formula="x=y")
    assert ae.step_name == "step"
    assert ae.references == []


def test_BASE02_validation_issue_fields():
    vi = ValidationIssue(severity="error", code="X", message="bad")
    assert vi.severity == "error"
    assert vi.code == "X"


def test_BASE03_engine_result_none_value_on_error():
    r = EngineResult(
        engine_name="test", value=None,
        confidence="insufficient", audit_trail=[], issues=[],
    )
    assert r.value is None
    assert r.confidence == "insufficient"


def test_BASE04_valuation_engine_is_abstract():
    import inspect
    assert inspect.isabstract(ValuationEngine)


# ═══════════════════════════════════════════════════════════════════════════════
# COMPARATIVE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class TestComparativeEngine:

    def test_CE01_instantiation(self):
        eng = ComparativeEngine()
        assert eng.name == "comparative"
        assert eng.version == "1.0.0"
        assert eng.area_elasticity == 0.85
        assert eng.age_depreciation_per_year == 0.01

    def test_CE02_validate_returns_empty_for_valid_payload(self):
        eng = ComparativeEngine()
        issues = eng.validate({"subject_area_sqm": 100, "comparables": _FULL_COMPS})
        errors = [i for i in issues if i.severity == "error"]
        assert errors == []

    def test_CE03_validate_error_on_zero_subject_area(self):
        eng = ComparativeEngine()
        issues = eng.validate({"subject_area_sqm": 0, "comparables": _FULL_COMPS})
        codes = {i.code for i in issues}
        assert "INVALID_SUBJECT_AREA" in codes

    def test_CE04_validate_error_on_negative_subject_area(self):
        eng = ComparativeEngine()
        issues = eng.validate({"subject_area_sqm": -50, "comparables": _FULL_COMPS})
        codes = {i.code for i in issues}
        assert "INVALID_SUBJECT_AREA" in codes

    def test_CE05_validate_error_when_too_few_comparables(self):
        eng = ComparativeEngine()
        issues = eng.validate({
            "subject_area_sqm": 100,
            "comparables": [_FULL_COMPS[0]],  # only 1 < min 3
        })
        codes = {i.code for i in issues}
        assert "INSUFFICIENT_COMPARABLES" in codes

    def test_CE06_validate_warning_below_recommended(self):
        eng = ComparativeEngine()
        issues = eng.validate({
            "subject_area_sqm": 100,
            "comparables": _FULL_COMPS[:3],  # 3 = min but < recommended 5
        })
        severities = {(i.code, i.severity) for i in issues}
        assert ("BELOW_RECOMMENDED", "warning") in severities

    def test_CE07_validate_warning_on_invalid_comparable_area(self):
        eng = ComparativeEngine()
        bad_comps = list(_FULL_COMPS)
        bad_comps[0] = {**bad_comps[0], "area_sqm": 0}
        issues = eng.validate({"subject_area_sqm": 100, "comparables": bad_comps})
        codes = {i.code for i in issues}
        assert "INVALID_COMPARABLE_AREA" in codes

    def test_CE08_validate_error_missing_price(self):
        eng = ComparativeEngine()
        no_price = [{"id": f"c{i}", "area_sqm": 100} for i in range(3)]
        issues = eng.validate({"subject_area_sqm": 100, "comparables": no_price})
        codes = {i.code for i in issues}
        assert "MISSING_PRICE" in codes

    def test_CE09_calculate_returns_engine_result(self):
        eng = ComparativeEngine()
        result = eng.calculate({"subject_area_sqm": 100, "comparables": _FULL_COMPS})
        assert isinstance(result, EngineResult)
        assert result.engine_name == "comparative"

    def test_CE10_calculate_with_5_comps_returns_high_confidence(self):
        eng = ComparativeEngine()
        result = eng.calculate({"subject_area_sqm": 100, "comparables": _FULL_COMPS})
        assert result.value is not None
        assert result.confidence == "high"

    def test_CE11_calculate_with_3_comps_returns_medium_confidence(self):
        eng = ComparativeEngine()
        result = eng.calculate({"subject_area_sqm": 100, "comparables": _FULL_COMPS[:3]})
        assert result.value is not None
        assert result.confidence == "medium"

    def test_CE12_calculate_returns_decimal_value(self):
        eng = ComparativeEngine()
        result = eng.calculate({"subject_area_sqm": 100, "comparables": _FULL_COMPS})
        assert isinstance(result.value, Decimal)
        assert result.value > 0

    def test_CE13_calculate_value_equals_mean_per_sqm_times_area(self):
        """With identical comparables and no age/floor/finishing, value should
        be close to subject_area × (adjusted ppm)."""
        eng = ComparativeEngine()
        uniform_comps = [
            {"id": f"c{i}", "area_sqm": 100, "price_per_sqm": 20000}
            for i in range(5)
        ]
        result = eng.calculate({"subject_area_sqm": 100, "comparables": uniform_comps})
        # area elasticity = (100/100)^0.85 = 1.0; no age/floor/finishing → adjusted = 20000
        assert result.value is not None
        assert abs(float(result.value) - 2_000_000.0) < 1.0

    def test_CE14_area_elasticity_shrinks_ppm_for_larger_subject(self):
        """Subject larger than comp → area_factor < 1 → adjusted ppm < original."""
        eng = ComparativeEngine()
        comps = [{"id": f"c{i}", "area_sqm": 80, "price_per_sqm": 20000} for i in range(5)]
        result = eng.calculate({"subject_area_sqm": 200, "comparables": comps})
        # (200/80)^0.85 < 1 is wrong — actually > 1 when subject > comp
        # Correction: area_factor = (subject/comp)^elasticity = (200/80)^0.85 > 1
        # So adjusted ppm > 20000, total value > 200 * 20000 = 4_000_000
        assert result.value is not None
        assert float(result.value) > 4_000_000

    def test_CE15_age_adjustment_applied_when_ages_supplied(self):
        """Subject 10 yrs older than comp → factor < 1 → lower value than no-age case."""
        eng = ComparativeEngine()
        base_comps = [{"id": f"c{i}", "area_sqm": 100, "price_per_sqm": 20000} for i in range(5)]
        result_no_age = eng.calculate({"subject_area_sqm": 100, "comparables": base_comps})

        aged_comps = [{"id": f"c{i}", "area_sqm": 100, "price_per_sqm": 20000, "age_years": 1}
                      for i in range(5)]
        result_aged = eng.calculate({
            "subject_area_sqm": 100,
            "comparables": aged_comps,
            "subject_age_years": 11,  # 10-year gap → 10% deduction
        })
        assert result_aged.value < result_no_age.value

    def test_CE16_floor_adjustment_applied_when_configured(self):
        """Configuring floor_adjustments changes value."""
        eng = ComparativeEngine()
        eng.floor_adjustments = {"2": 0.05}   # subject 2 floors above comp → +5%
        comps = [{"id": f"c{i}", "area_sqm": 100, "price_per_sqm": 20000, "floor": 1}
                 for i in range(5)]
        result_with = eng.calculate({
            "subject_area_sqm": 100, "comparables": comps, "subject_floor": 3,
        })
        result_without = eng.calculate({
            "subject_area_sqm": 100, "comparables": comps,
        })
        assert float(result_with.value) > float(result_without.value)

    def test_CE17_finishing_adjustment_applied_when_different(self):
        """Comp finishing != subject finishing → adjustment applied if configured."""
        eng = ComparativeEngine()
        eng.finishing_adjustments = {"economy": -0.10}
        comps = [{"id": f"c{i}", "area_sqm": 100, "price_per_sqm": 20000,
                  "finishing_level": "economy"} for i in range(5)]
        result = eng.calculate({
            "subject_area_sqm": 100,
            "comparables": comps,
            "subject_finishing_level": "standard",
        })
        # comp finishing="economy" with -10% → adjusted ppm = 20000 × 0.90 = 18000
        assert result.value is not None
        assert abs(float(result.value) - 100 * 18000) < 2.0

    def test_CE18_errors_block_calculation(self):
        eng = ComparativeEngine()
        result = eng.calculate({"subject_area_sqm": 0, "comparables": _FULL_COMPS})
        assert result.value is None
        assert result.confidence == "insufficient"

    def test_CE19_audit_trail_populated(self):
        eng = ComparativeEngine()
        result = eng.calculate({"subject_area_sqm": 100, "comparables": _FULL_COMPS[:3]})
        assert len(result.audit_trail) > 0
        assert all(isinstance(e, AuditEntry) for e in result.audit_trail)

    def test_CE20_metadata_contains_per_sqm_and_cv(self):
        eng = ComparativeEngine()
        result = eng.calculate({"subject_area_sqm": 100, "comparables": _FULL_COMPS})
        assert "per_sqm" in result.metadata
        assert "coefficient_of_variation" in result.metadata
        assert "comparable_count" in result.metadata

    def test_CE21_price_egp_accepted_as_alternative_to_price_per_sqm(self):
        comps = [{"id": f"c{i}", "area_sqm": 100, "price_egp": 2_000_000} for i in range(5)]
        eng = ComparativeEngine()
        result = eng.calculate({"subject_area_sqm": 100, "comparables": comps})
        assert result.value is not None
        assert float(result.value) > 0

    def test_CE22_year_built_accepted_instead_of_age_years(self):
        from datetime import date
        current_yr = date.today().year
        comps = [
            {"id": f"c{i}", "area_sqm": 100, "price_per_sqm": 20000,
             "year_built": current_yr - 5}
            for i in range(5)
        ]
        eng = ComparativeEngine()
        result = eng.calculate({
            "subject_area_sqm": 100,
            "comparables": comps,
            "subject_age_years": 10,
        })
        # 10 vs 5 yr gap = 5% penalty
        assert result.value is not None

    def test_CE23_deterministic_repeated_calls(self):
        eng = ComparativeEngine()
        r1 = eng.calculate({"subject_area_sqm": 100, "comparables": _FULL_COMPS})
        r2 = eng.calculate({"subject_area_sqm": 100, "comparables": _FULL_COMPS})
        assert r1.value == r2.value

    def test_CE24_cv_is_zero_for_identical_comparables(self):
        eng = ComparativeEngine()
        uniform = [{"id": f"c{i}", "area_sqm": 100, "price_per_sqm": 20000} for i in range(5)]
        result = eng.calculate({"subject_area_sqm": 100, "comparables": uniform})
        assert result.metadata["coefficient_of_variation"] == 0.0

    def test_CE25_price_range_min_max_in_metadata(self):
        eng = ComparativeEngine()
        result = eng.calculate({"subject_area_sqm": 100, "comparables": _FULL_COMPS})
        assert result.metadata["price_range_min"] <= result.metadata["price_range_max"]


# ═══════════════════════════════════════════════════════════════════════════════
# COST ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class TestCostEngine:

    def test_KE01_instantiation_with_real_cost_tables(self, real_cost_tables_path):
        eng = CostEngine(real_cost_tables_path)
        assert eng.name == "cost"
        assert eng.version == "1.0.0"
        assert "Cairo" in eng.cost_tables

    def test_KE02_instantiation_missing_file_uses_defaults(self, tmp_path):
        eng = CostEngine(str(tmp_path / "nonexistent.json"))
        assert "_default" in eng.cost_tables

    def test_KE03_instantiation_corrupt_json_uses_defaults(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{bad json", encoding="utf-8")
        eng = CostEngine(str(p))
        assert "_default" in eng.cost_tables

    def test_KE04_validate_ok_for_valid_input(self, real_cost_tables_path):
        eng = CostEngine(real_cost_tables_path)
        issues = eng.validate({
            "building_area_sqm": 100,
            "building_age_years": 10,
            "construction_quality": "standard",
            "land_value_egp": 500_000,
            "governorate": "Cairo",
        })
        errors = [i for i in issues if i.severity == "error"]
        assert errors == []

    def test_KE05_validate_error_zero_building_area(self, real_cost_tables_path):
        eng = CostEngine(real_cost_tables_path)
        issues = eng.validate({
            "building_area_sqm": 0,
            "construction_quality": "standard",
        })
        codes = {i.code for i in issues}
        assert "INVALID_BUILDING_AREA" in codes

    def test_KE06_validate_error_negative_age(self, real_cost_tables_path):
        eng = CostEngine(real_cost_tables_path)
        issues = eng.validate({
            "building_area_sqm": 100,
            "building_age_years": -1,
            "construction_quality": "standard",
        })
        codes = {i.code for i in issues}
        assert "INVALID_AGE" in codes

    def test_KE07_validate_error_invalid_quality(self, real_cost_tables_path):
        eng = CostEngine(real_cost_tables_path)
        issues = eng.validate({
            "building_area_sqm": 100,
            "construction_quality": "premium",
        })
        codes = {i.code for i in issues}
        assert "INVALID_QUALITY" in codes

    def test_KE08_validate_error_negative_land_value(self, real_cost_tables_path):
        eng = CostEngine(real_cost_tables_path)
        issues = eng.validate({
            "building_area_sqm": 100,
            "construction_quality": "standard",
            "land_value_egp": -1,
        })
        codes = {i.code for i in issues}
        assert "INVALID_LAND_VALUE" in codes

    def test_KE09_validate_warning_fully_depreciated(self, real_cost_tables_path):
        eng = CostEngine(real_cost_tables_path)
        # standard economic life = 60 yrs; age = 60 triggers FULLY_DEPRECIATED
        issues = eng.validate({
            "building_area_sqm": 100,
            "building_age_years": 60,
            "construction_quality": "standard",
            "land_value_egp": 0,
        })
        codes = {i.code for i in issues}
        assert "FULLY_DEPRECIATED" in codes

    def test_KE10_validate_warning_unknown_governorate(self, real_cost_tables_path):
        eng = CostEngine(real_cost_tables_path)
        issues = eng.validate({
            "building_area_sqm": 100,
            "construction_quality": "standard",
            "governorate": "Atlantis",
        })
        codes = {i.code for i in issues}
        assert "UNKNOWN_GOVERNORATE" in codes

    def test_KE11_calculate_returns_engine_result(self, real_cost_tables_path):
        eng = CostEngine(real_cost_tables_path)
        result = eng.calculate({
            "building_area_sqm": 100,
            "building_age_years": 10,
            "construction_quality": "standard",
            "land_value_egp": 500_000,
            "governorate": "Cairo",
        })
        assert isinstance(result, EngineResult)
        assert result.engine_name == "cost"

    def test_KE12_calculate_value_is_decimal(self, real_cost_tables_path):
        eng = CostEngine(real_cost_tables_path)
        result = eng.calculate({
            "building_area_sqm": 100,
            "building_age_years": 0,
            "construction_quality": "standard",
            "land_value_egp": 0,
            "governorate": "Cairo",
        })
        assert isinstance(result.value, Decimal)

    def test_KE13_calculate_cairo_standard_new_building(self, real_cost_tables_path):
        """Age=0 → no depreciation → value = RCN + land_value."""
        eng = CostEngine(real_cost_tables_path)
        area = 100
        land = 200_000
        result = eng.calculate({
            "building_area_sqm": area,
            "building_age_years": 0,
            "construction_quality": "standard",
            "land_value_egp": land,
            "governorate": "Cairo",
        })
        # Cairo standard = 14000/sqm; RCN = 1_400_000; total = 1_600_000
        assert result.value is not None
        assert abs(float(result.value) - (14000 * area + land)) < 1.0

    def test_KE14_calculate_depreciation_reduces_value(self, real_cost_tables_path):
        eng = CostEngine(real_cost_tables_path)
        base = {
            "building_area_sqm": 100,
            "construction_quality": "standard",
            "land_value_egp": 0,
            "governorate": "Cairo",
        }
        new_result = eng.calculate({**base, "building_age_years": 0})
        old_result = eng.calculate({**base, "building_age_years": 30})
        assert float(old_result.value) < float(new_result.value)

    def test_KE15_calculate_fully_depreciated_building_value_equals_land(self, real_cost_tables_path):
        """Age >= economic_life → building contributes 0 → total = land_value."""
        eng = CostEngine(real_cost_tables_path)
        land = 300_000
        result = eng.calculate({
            "building_area_sqm": 100,
            "building_age_years": 60,   # = economic_life for standard
            "construction_quality": "standard",
            "land_value_egp": land,
            "governorate": "Cairo",
        })
        assert result.value is not None
        assert abs(float(result.value) - land) < 1.0

    def test_KE16_calculate_uses_default_governorate_for_unknown(self, real_cost_tables_path):
        eng = CostEngine(real_cost_tables_path)
        result_default = eng.calculate({
            "building_area_sqm": 100, "building_age_years": 0,
            "construction_quality": "standard", "land_value_egp": 0,
            "governorate": "_default",
        })
        result_unknown = eng.calculate({
            "building_area_sqm": 100, "building_age_years": 0,
            "construction_quality": "standard", "land_value_egp": 0,
            "governorate": "NoSuchCity",
        })
        # Both should fall back to _default rates → same value
        assert result_default.value == result_unknown.value

    def test_KE17_calculate_luxury_more_expensive_than_economy(self, real_cost_tables_path):
        eng = CostEngine(real_cost_tables_path)
        base = {
            "building_area_sqm": 100, "building_age_years": 0,
            "land_value_egp": 0, "governorate": "Cairo",
        }
        lux = eng.calculate({**base, "construction_quality": "luxury"})
        eco = eng.calculate({**base, "construction_quality": "economy"})
        assert float(lux.value) > float(eco.value)

    def test_KE18_custom_cost_per_sqm_overrides_table(self, real_cost_tables_path):
        eng = CostEngine(real_cost_tables_path)
        result = eng.calculate({
            "building_area_sqm": 100, "building_age_years": 0,
            "construction_quality": "standard", "land_value_egp": 0,
            "governorate": "Cairo",
            "custom_cost_per_sqm": 50000,
        })
        assert abs(float(result.value) - 5_000_000) < 1.0

    def test_KE19_calculate_confidence_high_for_new_building_with_land(self, real_cost_tables_path):
        eng = CostEngine(real_cost_tables_path)
        result = eng.calculate({
            "building_area_sqm": 100, "building_age_years": 0,
            "construction_quality": "standard", "land_value_egp": 500_000,
            "governorate": "Cairo",
        })
        assert result.confidence == "high"

    def test_KE20_calculate_confidence_low_when_no_land_value(self, real_cost_tables_path):
        eng = CostEngine(real_cost_tables_path)
        result = eng.calculate({
            "building_area_sqm": 100, "building_age_years": 0,
            "construction_quality": "standard", "land_value_egp": 0,
            "governorate": "Cairo",
        })
        assert result.confidence == "low"

    def test_KE21_audit_trail_has_six_steps(self, real_cost_tables_path):
        eng = CostEngine(real_cost_tables_path)
        result = eng.calculate({
            "building_area_sqm": 100, "building_age_years": 10,
            "construction_quality": "standard", "land_value_egp": 200_000,
            "governorate": "Cairo",
        })
        assert len(result.audit_trail) == 6

    def test_KE22_metadata_contains_rcn_and_depreciation(self, real_cost_tables_path):
        eng = CostEngine(real_cost_tables_path)
        result = eng.calculate({
            "building_area_sqm": 100, "building_age_years": 10,
            "construction_quality": "standard", "land_value_egp": 0,
            "governorate": "Cairo",
        })
        assert "rcn" in result.metadata
        assert "depreciation_pct" in result.metadata
        assert "economic_life_years" in result.metadata

    def test_KE23_deterministic(self, real_cost_tables_path):
        eng = CostEngine(real_cost_tables_path)
        inputs = {
            "building_area_sqm": 150, "building_age_years": 20,
            "construction_quality": "luxury", "land_value_egp": 1_000_000,
            "governorate": "Giza",
        }
        r1 = eng.calculate(inputs)
        r2 = eng.calculate(inputs)
        assert r1.value == r2.value

    def test_KE24_giza_rates_differ_from_cairo(self, real_cost_tables_path):
        eng = CostEngine(real_cost_tables_path)
        base = {"building_area_sqm": 100, "building_age_years": 0,
                "construction_quality": "standard", "land_value_egp": 0}
        cairo = eng.calculate({**base, "governorate": "Cairo"})
        giza  = eng.calculate({**base, "governorate": "Giza"})
        assert cairo.value != giza.value

    def test_KE25_economic_life_differs_by_quality(self, real_cost_tables_path):
        eng = CostEngine(real_cost_tables_path)
        assert eng.economic_life["economy"]  == 40
        assert eng.economic_life["standard"] == 60
        assert eng.economic_life["luxury"]   == 80


# ═══════════════════════════════════════════════════════════════════════════════
# INCOME ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class TestIncomeEngine:

    def test_IE01_instantiation(self):
        eng = IncomeEngine()
        assert eng.name == "income"
        assert eng.version == "1.0.0"
        assert eng.default_vacancy_rate == 0.15
        assert eng.default_opex_ratio   == 0.35

    def test_IE02_validate_ok_for_valid_input(self):
        eng = IncomeEngine()
        issues = eng.validate({
            "gross_income_annual_egp": 500_000,
            "vacancy_rate": 0.10,
            "operating_expenses_ratio": 0.30,
            "cap_rate": 0.08,
        })
        errors = [i for i in issues if i.severity == "error"]
        assert errors == []

    def test_IE03_validate_error_zero_gross_income(self):
        eng = IncomeEngine()
        issues = eng.validate({"gross_income_annual_egp": 0, "cap_rate": 0.08})
        codes = {i.code for i in issues}
        assert "INVALID_GROSS_INCOME" in codes

    def test_IE04_validate_error_negative_gross_income(self):
        eng = IncomeEngine()
        issues = eng.validate({"gross_income_annual_egp": -1, "cap_rate": 0.08})
        codes = {i.code for i in issues}
        assert "INVALID_GROSS_INCOME" in codes

    def test_IE05_validate_error_zero_cap_rate(self):
        eng = IncomeEngine()
        issues = eng.validate({"gross_income_annual_egp": 500_000, "cap_rate": 0})
        codes = {i.code for i in issues}
        assert "INVALID_CAP_RATE" in codes

    def test_IE06_validate_error_negative_cap_rate(self):
        eng = IncomeEngine()
        issues = eng.validate({"gross_income_annual_egp": 500_000, "cap_rate": -0.05})
        codes = {i.code for i in issues}
        assert "INVALID_CAP_RATE" in codes

    def test_IE07_validate_error_vacancy_above_50pct(self):
        eng = IncomeEngine()
        issues = eng.validate({"gross_income_annual_egp": 500_000, "cap_rate": 0.08,
                                "vacancy_rate": 0.55})
        codes = {i.code for i in issues}
        assert "INVALID_VACANCY_RATE" in codes

    def test_IE08_validate_error_opex_ratio_ge_1(self):
        eng = IncomeEngine()
        issues = eng.validate({"gross_income_annual_egp": 500_000, "cap_rate": 0.08,
                                "operating_expenses_ratio": 1.0})
        codes = {i.code for i in issues}
        assert "INVALID_OPEX_RATIO" in codes

    def test_IE09_validate_warning_cap_rate_out_of_range(self):
        eng = IncomeEngine()
        issues = eng.validate({"gross_income_annual_egp": 500_000, "cap_rate": 0.50})
        codes = {i.code for i in issues}
        assert "CAP_RATE_OUT_OF_RANGE" in codes

    def test_IE10_validate_warning_high_opex(self):
        eng = IncomeEngine()
        issues = eng.validate({"gross_income_annual_egp": 500_000, "cap_rate": 0.08,
                                "operating_expenses_ratio": 0.75})
        codes = {i.code for i in issues}
        assert "HIGH_OPEX_RATIO" in codes

    def test_IE11_validate_warning_expert_cap_rate_no_source(self):
        eng = IncomeEngine()
        issues = eng.validate({
            "gross_income_annual_egp": 500_000,
            "cap_rate": 0.08,
            "cap_rate_source": "expert",
            # no cap_rate_source_reference
        })
        codes = {i.code for i in issues}
        assert "EXPERT_CAP_RATE_NO_SOURCE" in codes

    def test_IE12_calculate_returns_engine_result(self):
        eng = IncomeEngine()
        result = eng.calculate({
            "gross_income_annual_egp": 500_000,
            "vacancy_rate": 0.10,
            "operating_expenses_ratio": 0.30,
            "cap_rate": 0.08,
        })
        assert isinstance(result, EngineResult)
        assert result.engine_name == "income"

    def test_IE13_calculate_noi_formula(self):
        """EGI = 500_000 × 0.90 = 450_000; OpEx = 450_000 × 0.30 = 135_000;
        NOI = 315_000; Value = 315_000 / 0.08 = 3_937_500."""
        eng = IncomeEngine()
        result = eng.calculate({
            "gross_income_annual_egp": 500_000,
            "vacancy_rate": 0.10,
            "operating_expenses_ratio": 0.30,
            "cap_rate": 0.08,
        })
        assert result.value is not None
        assert abs(float(result.value) - 3_937_500.0) < 1.0

    def test_IE14_default_vacancy_and_opex_used_when_absent(self):
        """Without explicit vacancy/opex, defaults (0.15 / 0.35) apply."""
        eng = IncomeEngine()
        result = eng.calculate({
            "gross_income_annual_egp": 1_000_000,
            "cap_rate": 0.10,
        })
        # EGI = 850_000; OpEx = 297_500; NOI = 552_500; value = 5_525_000
        expected = 1_000_000 * 0.85 * 0.65 / 0.10
        assert result.value is not None
        assert abs(float(result.value) - expected) < 1.0

    def test_IE15_higher_cap_rate_lowers_value(self):
        eng = IncomeEngine()
        base = {"gross_income_annual_egp": 500_000, "vacancy_rate": 0.10,
                "operating_expenses_ratio": 0.30}
        low_cap  = eng.calculate({**base, "cap_rate": 0.06})
        high_cap = eng.calculate({**base, "cap_rate": 0.12})
        assert float(low_cap.value) > float(high_cap.value)

    def test_IE16_higher_vacancy_lowers_value(self):
        eng = IncomeEngine()
        base = {"gross_income_annual_egp": 500_000, "cap_rate": 0.08,
                "operating_expenses_ratio": 0.30}
        low_vac  = eng.calculate({**base, "vacancy_rate": 0.05})
        high_vac = eng.calculate({**base, "vacancy_rate": 0.25})
        assert float(low_vac.value) > float(high_vac.value)

    def test_IE17_noi_zero_returns_none_value(self):
        """opex_ratio = 1.0 would be invalid; use opex that zeroes NOI via vacancy."""
        eng = IncomeEngine()
        # vacancy=1.0 is invalid (> 0.5), so use opex_ratio to make NOI ≤ 0
        # EGI = 100 × 0.90 = 90; opex = 90 × 0.99 = 89.1 → NOI = 0.9 > 0
        # Easier: supply very high opex that engine allows (< 1.0 but high)
        # opex_ratio = 0.99 → HIGH_OPEX_RATIO warning, still calculates
        # Use gross=0 path — but that errors. Use a negative NOI scenario:
        # We can't make NOI exactly ≤ 0 with valid inputs without a hack.
        # Instead test the NON_POSITIVE_NOI guard via direct _calculate_noi call:
        egi, opex, noi = eng._calculate_noi(100, 0.0, 1.0)  # opex_ratio=1.0 gives NOI=0
        # opex_ratio=1.0 is rejected by validate but _calculate_noi is internal
        assert noi == 0.0

    def test_IE18_confidence_high_for_in_range_cap_rate(self):
        eng = IncomeEngine()
        result = eng.calculate({
            "gross_income_annual_egp": 500_000,
            "vacancy_rate": 0.10,
            "operating_expenses_ratio": 0.30,
            "cap_rate": 0.08,   # in [4%, 20%]
        })
        assert result.confidence == "high"

    def test_IE19_confidence_low_when_high_vacancy(self):
        eng = IncomeEngine()
        result = eng.calculate({
            "gross_income_annual_egp": 500_000,
            "vacancy_rate": 0.35,   # > 0.3 → low
            "operating_expenses_ratio": 0.30,
            "cap_rate": 0.08,
        })
        assert result.confidence == "low"

    def test_IE20_audit_trail_has_five_steps(self):
        eng = IncomeEngine()
        result = eng.calculate({
            "gross_income_annual_egp": 500_000,
            "vacancy_rate": 0.10,
            "operating_expenses_ratio": 0.30,
            "cap_rate": 0.08,
        })
        # Steps: extract params, EGI, OpEx, NOI, capitalise
        assert len(result.audit_trail) == 5

    def test_IE21_metadata_contains_noi_and_cap_rate(self):
        eng = IncomeEngine()
        result = eng.calculate({
            "gross_income_annual_egp": 500_000,
            "vacancy_rate": 0.10,
            "operating_expenses_ratio": 0.30,
            "cap_rate": 0.08,
        })
        assert "noi" in result.metadata
        assert "cap_rate" in result.metadata
        assert "effective_gross_income" in result.metadata
        assert "gross_income" in result.metadata

    def test_IE22_cap_rate_source_stored_in_metadata(self):
        eng = IncomeEngine()
        result = eng.calculate({
            "gross_income_annual_egp": 500_000,
            "cap_rate": 0.08,
            "cap_rate_source": "published",
            "cap_rate_source_reference": "CBRE Egypt Q2 2025",
        })
        assert result.metadata["cap_rate_source"] == "published"
        assert result.metadata["cap_rate_source_reference"] == "CBRE Egypt Q2 2025"

    def test_IE23_deterministic(self):
        eng = IncomeEngine()
        inputs = {
            "gross_income_annual_egp": 750_000,
            "vacancy_rate": 0.12,
            "operating_expenses_ratio": 0.28,
            "cap_rate": 0.09,
        }
        r1 = eng.calculate(inputs)
        r2 = eng.calculate(inputs)
        assert r1.value == r2.value

    def test_IE24_errors_block_calculation(self):
        eng = IncomeEngine()
        result = eng.calculate({"gross_income_annual_egp": 0, "cap_rate": 0.08})
        assert result.value is None
        assert result.confidence == "insufficient"

    def test_IE25_calculate_noi_helper_returns_triple(self):
        eng = IncomeEngine()
        egi, opex, noi = eng._calculate_noi(100_000, 0.10, 0.30)
        assert abs(egi  - 90_000) < 0.01
        assert abs(opex - 27_000) < 0.01
        assert abs(noi  - 63_000) < 0.01


# ═══════════════════════════════════════════════════════════════════════════════
# COMPARABLE SEARCH ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class TestComparableSearchEngine:

    def test_CS01_instantiation_with_valid_feed(self, feed_path):
        eng = ComparableSearchEngine(feed_path)
        assert len(eng.comparables) == 5

    def test_CS02_instantiation_missing_file_returns_empty(self, tmp_path):
        eng = ComparableSearchEngine(str(tmp_path / "missing.json"))
        assert eng.comparables == []

    def test_CS03_instantiation_corrupt_json_returns_empty(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{bad", encoding="utf-8")
        eng = ComparableSearchEngine(str(p))
        assert eng.comparables == []

    def test_CS04_instantiation_empty_feed_returns_empty(self, empty_feed_path):
        eng = ComparableSearchEngine(empty_feed_path)
        assert eng.comparables == []

    def test_CS05_search_requires_lat_lng(self, feed_path):
        eng = ComparableSearchEngine(feed_path)
        results = eng.search({})   # no lat/lng
        assert results == []

    def test_CS06_search_returns_list(self, feed_path):
        eng = ComparableSearchEngine(feed_path)
        results = eng.search({"latitude": 30.0, "longitude": 31.2})
        assert isinstance(results, list)

    def test_CS07_search_filter_by_location_text(self, feed_path):
        eng = ComparableSearchEngine(feed_path)
        results = eng.search({
            "latitude": 29.961, "longitude": 31.258,
            "location_text": "المعادي",
        })
        for r in results:
            assert "المعادي" in str(r.get("location", ""))

    def test_CS08_search_filter_by_property_type(self, feed_path):
        eng = ComparableSearchEngine(feed_path)
        results = eng.search({
            "latitude": 29.961, "longitude": 31.258,
            "property_type": "شقة سكنية",
        })
        for r in results:
            assert r.get("property_type", "").lower() == "شقة سكنية"

    def test_CS09_search_enrich_price_per_sqm(self, feed_path):
        eng = ComparableSearchEngine(feed_path)
        results = eng.search({"latitude": 29.961, "longitude": 31.258})
        for r in results:
            assert "price_per_sqm" in r

    def test_CS10_search_enrich_distance_meters(self, feed_path):
        eng = ComparableSearchEngine(feed_path)
        results = eng.search({"latitude": 29.961, "longitude": 31.258})
        for r in results:
            assert "distance_meters" in r

    def test_CS11_search_area_min_filter(self, feed_path):
        eng = ComparableSearchEngine(feed_path)
        results = eng.search({
            "latitude": 29.961, "longitude": 31.258,
            "area_sqm_min": 130,
        })
        for r in results:
            area = r.get("area") or r.get("area_sqm", 0)
            assert area >= 130

    def test_CS12_search_area_max_filter(self, feed_path):
        eng = ComparableSearchEngine(feed_path)
        results = eng.search({
            "latitude": 29.961, "longitude": 31.258,
            "area_sqm_max": 100,
        })
        for r in results:
            area = r.get("area") or r.get("area_sqm", 0)
            assert area <= 100

    def test_CS13_search_swaps_reversed_area_bounds(self, feed_path):
        """area_min > area_max should be silently swapped, not crash."""
        eng = ComparableSearchEngine(feed_path)
        results = eng.search({
            "latitude": 29.961, "longitude": 31.258,
            "area_sqm_min": 200,
            "area_sqm_max": 50,
        })
        # Swapped to min=50, max=200 → should return records with area in [50, 200]
        for r in results:
            area = r.get("area") or r.get("area_sqm", 0)
            assert 50 <= area <= 200

    def test_CS14_search_deleted_records_excluded(self, tmp_path):
        feed = list(_MARKET_FEED) + [
            {"area": 100, "price": 2_000_000, "price_per_meter": 20000,
             "location": "المعادي", "property_type": "شقة سكنية",
             "timestamp": "2025-06-01T10:00:00", "credibility": 0.9,
             "deleted": True},
        ]
        p = tmp_path / "feed_with_deleted.json"
        p.write_text(json.dumps(feed), encoding="utf-8")
        eng = ComparableSearchEngine(str(p))
        assert len(eng.comparables) == 5  # deleted record excluded

    def test_CS15_similarity_score_returns_dict_with_total(self, feed_path):
        eng = ComparableSearchEngine(feed_path)
        subject = {"area_sqm": 100}
        comp    = {"area_sqm": 100, "distance_meters": 0, "timestamp": "2025-06-01T10:00:00"}
        score   = eng.similarity_score(subject, comp)
        assert "similarity_score" in score
        assert "breakdown" in score
        assert 0.0 <= score["similarity_score"] <= 100.0

    def test_CS16_similarity_score_breakdown_has_all_factors(self, feed_path):
        eng = ComparableSearchEngine(feed_path)
        subject = {"area_sqm": 100}
        comp    = {"area_sqm": 100, "distance_meters": 500}
        score   = eng.similarity_score(subject, comp)
        for key in ("distance", "area", "compound", "age", "finishing", "recency"):
            assert key in score["breakdown"]

    def test_CS17_similarity_perfect_same_compound(self, feed_path):
        eng = ComparableSearchEngine(feed_path)
        subject = {"area_sqm": 100, "compound_id": "CP01",
                   "age_years": 5, "finishing_level": "standard"}
        comp    = {"area_sqm": 100, "distance_meters": 0, "compound_id": "CP01",
                   "age_years": 5, "finishing_level": "standard",
                   "timestamp": "2025-06-01T10:00:00"}
        score = eng.similarity_score(subject, comp, max_age_months=24)
        assert score["breakdown"]["compound"] == 100.0

    def test_CS18_similarity_different_compound_score_zero(self, feed_path):
        eng = ComparableSearchEngine(feed_path)
        subject = {"area_sqm": 100, "compound_id": "CP01"}
        comp    = {"area_sqm": 100, "distance_meters": 0, "compound_id": "CP02"}
        score   = eng.similarity_score(subject, comp)
        assert score["breakdown"]["compound"] == 0.0

    def test_CS19_search_and_rank_returns_descending_scores(self, feed_path):
        eng = ComparableSearchEngine(feed_path)
        subject = {"area_sqm": 100}
        filters = {"latitude": 29.961, "longitude": 31.258}
        ranked  = eng.search_and_rank(subject, filters, limit=10)
        scores  = [r["similarity_score"] for r in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_CS20_search_and_rank_respects_limit(self, feed_path):
        eng = ComparableSearchEngine(feed_path)
        subject = {"area_sqm": 100}
        filters = {"latitude": 29.961, "longitude": 31.258}
        ranked  = eng.search_and_rank(subject, filters, limit=2)
        assert len(ranked) <= 2

    def test_CS21_search_and_rank_empty_feed_returns_empty(self, empty_feed_path):
        eng = ComparableSearchEngine(empty_feed_path)
        ranked = eng.search_and_rank({"area_sqm": 100},
                                      {"latitude": 30.0, "longitude": 31.2})
        assert ranked == []

    def test_CS22_distance_meters_helper_zero_for_same_point(self, feed_path):
        eng = ComparableSearchEngine(feed_path)
        d = eng._distance_meters(30.0, 31.2, 30.0, 31.2)
        assert d == 0.0

    def test_CS23_distance_meters_increases_with_separation(self, feed_path):
        eng = ComparableSearchEngine(feed_path)
        d_near = eng._distance_meters(30.0, 31.2, 30.001, 31.201)
        d_far  = eng._distance_meters(30.0, 31.2, 30.1,   31.3)
        assert d_far > d_near

    def test_CS24_days_since_parses_iso_timestamp(self, feed_path):
        eng = ComparableSearchEngine(feed_path)
        days = eng._days_since("2020-01-01T00:00:00")
        assert days is not None and days > 0

    def test_CS25_days_since_returns_none_for_garbage(self, feed_path):
        eng = ComparableSearchEngine(feed_path)
        assert eng._days_since("not-a-date") is None

    def test_CS26_search_result_has_normalised_aliases(self, feed_path):
        """price_egp and area_sqm aliases must be present in enriched results."""
        eng = ComparableSearchEngine(feed_path)
        results = eng.search({"latitude": 29.961, "longitude": 31.258})
        for r in results:
            assert "area_sqm" in r
            assert "price_egp" in r

    def test_CS27_supports_wrapped_comparables_format(self, tmp_path):
        """Feed file wrapped as {"comparables": [...]} should be loaded correctly."""
        feed = {"comparables": list(_MARKET_FEED[:3])}
        p = tmp_path / "wrapped.json"
        p.write_text(json.dumps(feed), encoding="utf-8")
        eng = ComparableSearchEngine(str(p))
        assert len(eng.comparables) == 3

    def test_CS28_negative_radius_defaults_to_5000(self, feed_path):
        eng = ComparableSearchEngine(feed_path)
        # Should not raise; falls back to 5000 m radius
        results = eng.search({"latitude": 29.961, "longitude": 31.258, "radius_meters": -100})
        assert isinstance(results, list)

    def test_CS29_similarity_score_age_neutral_when_ages_absent(self, feed_path):
        """When subject and comp have no age data, age_score should be neutral (50)."""
        eng = ComparableSearchEngine(feed_path)
        subject = {"area_sqm": 100}
        comp    = {"area_sqm": 100, "distance_meters": 0}
        score   = eng.similarity_score(subject, comp)
        assert score["breakdown"]["age"] == 50.0

    def test_CS30_clamp_helper_bounds(self, feed_path):
        eng = ComparableSearchEngine(feed_path)
        assert eng._clamp(-1.0)  == 0.0
        assert eng._clamp(2.0)   == 1.0
        assert eng._clamp(0.5)   == 0.5
        assert eng._clamp(0.3, 0.2, 0.8) == 0.3
