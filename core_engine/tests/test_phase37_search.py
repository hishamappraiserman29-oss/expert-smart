"""
Tests for Phase 37 — Comparable Search Enhancement
32 tests: A01-A12 (ComparableSearchEngine), B01-B10 (SmartMatcher),
          C01-C10 (AdjustmentFactorEngine)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from datetime import datetime

from search.comparable_search import (
    ComparableSearchEngine,
    SearchCriteria,
    SearchType,
    ComparableResult,
)
from search.similarity_matcher import SmartMatcher, MatchingStrategy, MatchScore
from search.adjustment_factors import (
    AdjustmentFactorEngine,
    AdjustmentCategory,
    PriceAdjustment,
)


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_prop(pid, area=150, price=1_500_000, location="Cairo", condition="good", ptype="residential"):
    return {
        "property_id": pid,
        "property_type": ptype,
        "location": location,
        "area_sqm": area,
        "price": price,
        "condition": condition,
        "age_years": 5,
        "bedrooms": 3,
        "bathrooms": 2,
        "features": ["parking"],
    }


def _wide_criteria(**overrides):
    """Default criteria that comfortably matches _make_prop defaults."""
    defaults = dict(
        property_type="residential",
        location="Cairo",
        area_sqm_min=100,
        area_sqm_max=200,
        price_min=1_000_000,
        price_max=2_000_000,
        min_similarity_score=0.5,
    )
    defaults.update(overrides)
    return SearchCriteria(**defaults)


# ── TestComparableSearchEngine ─────────────────────────────────────────────────

class TestComparableSearchEngine:

    @pytest.fixture
    def engine(self):
        return ComparableSearchEngine()

    def test_A01_register_property_returns_true(self, engine):
        assert engine.register_property("P1", _make_prop("P1")) is True

    def test_A02_registered_property_stored(self, engine):
        engine.register_property("P1", _make_prop("P1"))
        assert "P1" in engine.properties

    def test_A03_search_returns_results(self, engine):
        engine.register_property("P1", _make_prop("P1"))
        engine.register_property("P2", _make_prop("P2", area=160, price=1_600_000))
        criteria = _wide_criteria()
        results = engine.search_comparables(criteria)
        assert len(results) >= 2

    def test_A04_search_filters_wrong_property_type(self, engine):
        engine.register_property("P1", _make_prop("P1", ptype="commercial"))
        criteria = _wide_criteria(property_type="residential")
        results = engine.search_comparables(criteria)
        assert all(r.property_id != "P1" for r in results)

    def test_A05_search_filters_out_of_area_range(self, engine):
        engine.register_property("P1", _make_prop("P1", area=50))  # below min 100
        criteria = _wide_criteria()
        results = engine.search_comparables(criteria)
        assert all(r.property_id != "P1" for r in results)

    def test_A06_search_filters_out_of_price_range(self, engine):
        engine.register_property("P1", _make_prop("P1", price=5_000_000))  # above max
        criteria = _wide_criteria()
        results = engine.search_comparables(criteria)
        assert all(r.property_id != "P1" for r in results)

    def test_A07_exclude_property_ids_respected(self, engine):
        engine.register_property("P1", _make_prop("P1"))
        criteria = _wide_criteria(exclude_property_ids=["P1"])
        results = engine.search_comparables(criteria)
        assert all(r.property_id != "P1" for r in results)

    def test_A08_max_results_limits_count(self, engine):
        for i in range(10):
            engine.register_property(f"P{i}", _make_prop(f"P{i}"))
        criteria = _wide_criteria(max_results=3)
        results = engine.search_comparables(criteria)
        assert len(results) <= 3

    def test_A09_sort_by_similarity_highest_first(self, engine):
        engine.register_property("P1", _make_prop("P1", area=150, price=1_500_000))  # near mid
        engine.register_property("P2", _make_prop("P2", area=195, price=1_950_000))  # near edge
        criteria = _wide_criteria(sort_by="similarity")
        results = engine.search_comparables(criteria)
        if len(results) >= 2:
            assert results[0].similarity_score >= results[1].similarity_score

    def test_A10_sort_by_price_cheapest_first(self, engine):
        engine.register_property("P1", _make_prop("P1", price=1_800_000))
        engine.register_property("P2", _make_prop("P2", price=1_200_000))
        criteria = _wide_criteria(sort_by="price")
        results = engine.search_comparables(criteria)
        if len(results) >= 2:
            assert results[0].property_data["price"] <= results[1].property_data["price"]

    def test_A11_results_have_rank_assigned(self, engine):
        engine.register_property("P1", _make_prop("P1"))
        criteria = _wide_criteria()
        results = engine.search_comparables(criteria)
        assert len(results) > 0
        assert results[0].rank == 1

    def test_A12_user_search_history_tracked(self, engine):
        engine.register_property("P1", _make_prop("P1"))
        criteria = _wide_criteria()
        engine.search_comparables(criteria, user_id="USER_1")
        stats = engine.get_search_statistics(user_id="USER_1")
        assert stats["total_searches"] == 1

    def test_A13_get_statistics_without_user(self, engine):
        engine.register_property("P1", _make_prop("P1"))
        stats = engine.get_search_statistics()
        assert stats["total_properties"] == 1

    def test_A14_result_price_per_sqm_computed(self, engine):
        engine.register_property("P1", _make_prop("P1", area=150, price=1_500_000))
        criteria = _wide_criteria()
        results = engine.search_comparables(criteria)
        assert len(results) > 0
        assert abs(results[0].price_per_sqm - 10_000) < 1


# ── TestSmartMatcher ───────────────────────────────────────────────────────────

class TestSmartMatcher:

    @pytest.fixture
    def matcher(self):
        return SmartMatcher()

    def _candidate(self, pid, area=150, price=1_500_000, location="Cairo", condition="good"):
        return {
            "property_id": pid,
            "property_type": "residential",
            "location": location,
            "area_sqm": area,
            "price": price,
            "condition": condition,
            "age_years": 5,
            "bedrooms": 3,
            "bathrooms": 2,
        }

    def test_B01_weighted_match_returns_match_score_list(self, matcher):
        subject = self._candidate("S1")
        candidates = [self._candidate("C1")]
        results = matcher.match_properties(subject, candidates, MatchingStrategy.WEIGHTED)
        assert len(results) == 1
        assert isinstance(results[0], MatchScore)

    def test_B02_matches_sorted_descending(self, matcher):
        subject = self._candidate("S1")
        candidates = [self._candidate("C1"), self._candidate("C2", area=300, price=3_000_000)]
        results = matcher.match_properties(subject, candidates, MatchingStrategy.WEIGHTED)
        assert len(results) == 2
        assert results[0].overall_score >= results[1].overall_score

    def test_B03_identical_properties_score_high(self, matcher):
        subject = self._candidate("S1")
        candidates = [self._candidate("C1")]
        results = matcher.match_properties(subject, candidates, MatchingStrategy.WEIGHTED)
        assert results[0].overall_score > 90

    def test_B04_different_properties_score_lower_than_identical(self, matcher):
        subject = self._candidate("S1")
        identical = self._candidate("C_SAME")
        different = self._candidate("C_DIFF", area=1000, price=10_000_000)
        res_same = matcher.match_properties(subject, [identical], MatchingStrategy.WEIGHTED)
        res_diff = matcher.match_properties(subject, [different], MatchingStrategy.WEIGHTED)
        assert res_same[0].overall_score > res_diff[0].overall_score

    def test_B05_exact_strategy_returns_match_score(self, matcher):
        subject = self._candidate("S1")
        candidates = [self._candidate("C1")]
        results = matcher.match_properties(subject, candidates, MatchingStrategy.EXACT)
        assert len(results) == 1
        assert results[0].overall_score > 0

    def test_B06_hybrid_strategy_produces_score(self, matcher):
        subject = self._candidate("S1")
        candidates = [self._candidate("C1")]
        results = matcher.match_properties(subject, candidates, MatchingStrategy.HYBRID)
        assert results[0].overall_score > 0

    def test_B07_attribute_similarity_string_equal(self, matcher):
        score = matcher._calculate_attribute_similarity("location", "Cairo", "Cairo")
        assert score == 100.0

    def test_B08_attribute_similarity_string_different(self, matcher):
        score = matcher._calculate_attribute_similarity("location", "Cairo", "Alexandria")
        assert score == 50.0

    def test_B09_attribute_similarity_numeric_within_5pct(self, matcher):
        score = matcher._calculate_attribute_similarity("area_sqm", 100, 103)
        assert score == 100.0

    def test_B10_score_to_grade_mapping(self, matcher):
        assert matcher._score_to_grade(96) == "A+"
        assert matcher._score_to_grade(91) == "A"
        assert matcher._score_to_grade(86) == "B+"
        assert matcher._score_to_grade(81) == "B"
        assert matcher._score_to_grade(76) == "B-"
        assert matcher._score_to_grade(71) == "C+"
        assert matcher._score_to_grade(61) == "C"
        assert matcher._score_to_grade(50) == "F"


# ── TestAdjustmentFactorEngine ─────────────────────────────────────────────────

class TestAdjustmentFactorEngine:

    @pytest.fixture
    def eng(self):
        return AdjustmentFactorEngine()

    # Time adjustments

    def test_C01_time_adj_0_to_90_days_is_zero(self, eng):
        adj = eng.create_time_adjustment(60)
        assert adj.adjustment_percentage == 0.0
        assert adj.category == AdjustmentCategory.TIME

    def test_C02_time_adj_3_to_6_months_is_minus_1(self, eng):
        adj = eng.create_time_adjustment(120)
        assert adj.adjustment_percentage == -1.0

    def test_C03_time_adj_6_to_12_months_is_minus_2_5(self, eng):
        adj = eng.create_time_adjustment(240)
        assert adj.adjustment_percentage == -2.5

    def test_C04_time_adj_over_12_months_is_minus_5(self, eng):
        adj = eng.create_time_adjustment(400)
        assert adj.adjustment_percentage == -5.0

    # Condition adjustments

    def test_C05_condition_excellent_plus_10(self, eng):
        adj = eng.create_condition_adjustment("excellent")
        assert adj.adjustment_percentage == 10.0
        assert adj.category == AdjustmentCategory.CONDITION

    def test_C06_condition_good_zero(self, eng):
        adj = eng.create_condition_adjustment("good")
        assert adj.adjustment_percentage == 0.0

    def test_C07_condition_fair_minus_5(self, eng):
        adj = eng.create_condition_adjustment("fair")
        assert adj.adjustment_percentage == -5.0

    def test_C08_condition_poor_minus_15(self, eng):
        adj = eng.create_condition_adjustment("poor")
        assert adj.adjustment_percentage == -15.0

    # Apply adjustments

    def test_C09_apply_no_adjustments_returns_original(self, eng):
        result = eng.apply_adjustments("COMP_01", 1_000_000, [])
        assert result.adjusted_price == 1_000_000
        assert result.total_adjustment_percentage == 0.0

    def test_C10_apply_time_adjustment_reduces_price(self, eng):
        adj = eng.create_time_adjustment(400)  # -5%
        result = eng.apply_adjustments("COMP_02", 1_000_000, [adj])
        assert result.adjusted_price == pytest.approx(950_000.0)
        assert result.total_adjustment_percentage == -5.0
