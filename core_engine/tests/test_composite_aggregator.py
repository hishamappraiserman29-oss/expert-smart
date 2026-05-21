"""
Unit tests for valuation_engines/composite_aggregator.py (Wave 7A).

All tests are pure — no Flask, no DB, no HTTP.
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import pytest

# ── sys.path ──────────────────────────────────────────────────────────
_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent

for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(str(_CORE))

from adapters.purpose_adapter import AdjustedValuation
from valuation_engines.composite_aggregator import (
    AggregationResult,
    CompositeAggregatorError,
    aggregate,
)

# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def _av(baseline: float, adjusted: float) -> AdjustedValuation:
    return AdjustedValuation(
        component_id="x",
        name="test",
        asset_type="وحدة سكنية (شقة / فيلا)",
        purpose="البيع والشراء - القيمة السوقية العادلة (Market Value)",
        baseline_value=baseline,
        multiplier_applied=round(adjusted / baseline, 4) if baseline else 1.0,
        adjusted_value=adjusted,
        route="market_baseline",
        deep_route_deferred=False,
        iaao_block_triggered=False,
        uspap_standards=("Standard 1", "Standard 2"),
        notes=(),
    )


# ─────────────────────────────────────────────────────────────────────
# 1. Return type and fields
# ─────────────────────────────────────────────────────────────────────

class TestReturnShape:
    def test_returns_aggregation_result(self):
        result = aggregate([_av(1_000_000, 950_000)])
        assert isinstance(result, AggregationResult)

    def test_all_five_fields_present(self):
        r = aggregate([_av(1_000_000, 950_000)])
        assert hasattr(r, "total_baseline")
        assert hasattr(r, "total_adjusted_before_synergy")
        assert hasattr(r, "synergy_adjustment_percent")
        assert hasattr(r, "synergy_adjustment_amount")
        assert hasattr(r, "total_adjusted_after_synergy")

    def test_result_is_immutable(self):
        r = aggregate([_av(1_000_000, 950_000)])
        with pytest.raises(Exception):
            r.total_baseline = 99  # frozen dataclass


# ─────────────────────────────────────────────────────────────────────
# 2. Total baseline
# ─────────────────────────────────────────────────────────────────────

class TestTotalBaseline:
    def test_single_component(self):
        r = aggregate([_av(1_000_000, 950_000)])
        assert r.total_baseline == pytest.approx(1_000_000.0)

    def test_two_components_summed(self):
        r = aggregate([_av(1_000_000, 950_000), _av(500_000, 400_000)])
        assert r.total_baseline == pytest.approx(1_500_000.0)

    def test_empty_list_zero(self):
        r = aggregate([])
        assert r.total_baseline == 0.0

    def test_rounded_to_two_decimal_places(self):
        r = aggregate([_av(1_000_000.005, 950_000)])
        assert r.total_baseline == round(1_000_000.005, 2)


# ─────────────────────────────────────────────────────────────────────
# 3. Zero synergy (default)
# ─────────────────────────────────────────────────────────────────────

class TestZeroSynergy:
    def test_default_synergy_is_zero(self):
        r = aggregate([_av(1_000_000, 950_000)])
        assert r.synergy_adjustment_percent == 0.0

    def test_zero_synergy_amount_is_zero(self):
        r = aggregate([_av(1_000_000, 950_000)])
        assert r.synergy_adjustment_amount == 0.0

    def test_zero_synergy_after_equals_before(self):
        r = aggregate([_av(1_000_000, 950_000)])
        assert r.total_adjusted_after_synergy == r.total_adjusted_before_synergy

    def test_explicit_zero_same_as_default(self):
        r1 = aggregate([_av(1_000_000, 950_000)])
        r2 = aggregate([_av(1_000_000, 950_000)], synergy_adjustment_percent=0.0)
        assert r1 == r2


# ─────────────────────────────────────────────────────────────────────
# 4. Positive synergy
# ─────────────────────────────────────────────────────────────────────

class TestPositiveSynergy:
    def test_positive_synergy_increases_total(self):
        r = aggregate([_av(1_000_000, 1_000_000)], synergy_adjustment_percent=10.0)
        assert r.total_adjusted_after_synergy > r.total_adjusted_before_synergy

    def test_positive_synergy_amount_formula(self):
        # 1_000_000 before × 5% = 50_000 amount
        r = aggregate([_av(1_000_000, 1_000_000)], synergy_adjustment_percent=5.0)
        assert r.synergy_adjustment_amount == pytest.approx(50_000.0)

    def test_positive_synergy_after_value(self):
        # 1_000_000 + 50_000 = 1_050_000
        r = aggregate([_av(1_000_000, 1_000_000)], synergy_adjustment_percent=5.0)
        assert r.total_adjusted_after_synergy == pytest.approx(1_050_000.0)

    def test_positive_synergy_two_components(self):
        # (500_000 + 500_000) × 10% = 100_000 → 1_100_000
        avs = [_av(500_000, 500_000), _av(500_000, 500_000)]
        r = aggregate(avs, synergy_adjustment_percent=10.0)
        assert r.synergy_adjustment_amount == pytest.approx(100_000.0)
        assert r.total_adjusted_after_synergy == pytest.approx(1_100_000.0)


# ─────────────────────────────────────────────────────────────────────
# 5. Negative synergy
# ─────────────────────────────────────────────────────────────────────

class TestNegativeSynergy:
    def test_negative_synergy_decreases_total(self):
        r = aggregate([_av(1_000_000, 1_000_000)], synergy_adjustment_percent=-10.0)
        assert r.total_adjusted_after_synergy < r.total_adjusted_before_synergy

    def test_negative_synergy_amount_is_negative(self):
        r = aggregate([_av(1_000_000, 1_000_000)], synergy_adjustment_percent=-10.0)
        assert r.synergy_adjustment_amount < 0.0

    def test_negative_synergy_amount_formula(self):
        # 1_000_000 × -10% = -100_000
        r = aggregate([_av(1_000_000, 1_000_000)], synergy_adjustment_percent=-10.0)
        assert r.synergy_adjustment_amount == pytest.approx(-100_000.0)

    def test_negative_synergy_after_value(self):
        # 1_000_000 + (-100_000) = 900_000
        r = aggregate([_av(1_000_000, 1_000_000)], synergy_adjustment_percent=-10.0)
        assert r.total_adjusted_after_synergy == pytest.approx(900_000.0)


# ─────────────────────────────────────────────────────────────────────
# 6. Rounding
# ─────────────────────────────────────────────────────────────────────

class TestRounding:
    def test_totals_rounded_to_2dp(self):
        # 3 × 333_333.33... baseline
        avs = [_av(1_000_000 / 3, 1_000_000 / 3)] * 3
        r = aggregate(avs)
        # result must be a float with at most 2 decimal places
        assert r.total_baseline == round(r.total_baseline, 2)
        assert r.total_adjusted_before_synergy == round(r.total_adjusted_before_synergy, 2)

    def test_synergy_amount_rounded_to_2dp(self):
        r = aggregate([_av(1_000_000, 100)], synergy_adjustment_percent=3.333)
        assert r.synergy_adjustment_amount == round(r.synergy_adjustment_amount, 2)

    def test_total_after_rounded_to_2dp(self):
        r = aggregate([_av(1_000_000, 100)], synergy_adjustment_percent=3.333)
        assert r.total_adjusted_after_synergy == round(r.total_adjusted_after_synergy, 2)


# ─────────────────────────────────────────────────────────────────────
# 7. Invalid input → CompositeAggregatorError
# ─────────────────────────────────────────────────────────────────────

class TestInvalidInput:
    def test_string_synergy_raises(self):
        with pytest.raises(CompositeAggregatorError):
            aggregate([_av(1_000_000, 950_000)], synergy_adjustment_percent="5.0")

    def test_none_synergy_raises(self):
        with pytest.raises(CompositeAggregatorError):
            aggregate([_av(1_000_000, 950_000)], synergy_adjustment_percent=None)

    def test_bool_true_raises(self):
        with pytest.raises(CompositeAggregatorError):
            aggregate([_av(1_000_000, 950_000)], synergy_adjustment_percent=True)

    def test_bool_false_raises(self):
        with pytest.raises(CompositeAggregatorError):
            aggregate([_av(1_000_000, 950_000)], synergy_adjustment_percent=False)

    def test_nan_raises(self):
        with pytest.raises(CompositeAggregatorError):
            aggregate([_av(1_000_000, 950_000)], synergy_adjustment_percent=float("nan"))

    def test_inf_raises(self):
        with pytest.raises(CompositeAggregatorError):
            aggregate([_av(1_000_000, 950_000)], synergy_adjustment_percent=float("inf"))

    def test_error_message_contains_type(self):
        with pytest.raises(CompositeAggregatorError, match="str"):
            aggregate([_av(1_000_000, 950_000)], synergy_adjustment_percent="bad")
