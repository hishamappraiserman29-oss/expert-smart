"""
test_phase24_scenarios.py — Phase 24 Scenario Modeling Tests

Covers:
  A. ScenarioBuilder    — build_all, delta ordering, fluent API, to_dict
  B. MonteCarloEngine   — statistics, ordering, reproducibility, edge cases
  C. SensitivityMatrix  — dimensions, zero-change, monotonicity, to_dict
  D. StressTestSuite    — built-ins, custom, worst/best-case, to_dict
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scenarios.scenario_builder import ScenarioType, ScenarioResult, ScenarioBuilder
from scenarios.monte_carlo import MonteCarloConfig, MonteCarloResult, MonteCarloEngine
from scenarios.sensitivity_matrix import SensitivityResult, SensitivityMatrix
from scenarios.stress_test import StressScenario, StressTestResult, StressTestSuite


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BASE_VALUE = 3_000_000.0  # EGP 3M residential property

def _builder() -> ScenarioBuilder:
    return (
        ScenarioBuilder(BASE_VALUE)
        .add_parameter("market_growth",  0, optimistic_delta=+12, pessimistic_delta=-12)
        .add_parameter("location_premium", 0, optimistic_delta=+5, pessimistic_delta=-8)
    )


# ===========================================================================
# A. ScenarioBuilder
# ===========================================================================

class TestScenarioBuilder:

    def test_A01_build_base_case_equals_base_value(self):
        result = _builder().build_scenario(ScenarioType.BASE_CASE)
        assert result.value == BASE_VALUE

    def test_A02_base_case_delta_pct_is_zero(self):
        result = _builder().build_scenario(ScenarioType.BASE_CASE)
        assert result.delta_pct == 0.0

    def test_A03_optimistic_greater_than_base(self):
        b  = _builder()
        opt = b.build_scenario(ScenarioType.OPTIMISTIC)
        base = b.build_scenario(ScenarioType.BASE_CASE)
        assert opt.value > base.value

    def test_A04_pessimistic_less_than_base(self):
        b   = _builder()
        pess = b.build_scenario(ScenarioType.PESSIMISTIC)
        base = b.build_scenario(ScenarioType.BASE_CASE)
        assert pess.value < base.value

    def test_A05_build_all_returns_three_scenarios(self):
        results = _builder().build_all()
        assert len(results) == 3

    def test_A06_build_all_types_correct(self):
        types = {r.scenario_type for r in _builder().build_all()}
        assert ScenarioType.OPTIMISTIC  in types
        assert ScenarioType.BASE_CASE   in types
        assert ScenarioType.PESSIMISTIC in types

    def test_A07_to_dict_has_required_keys(self):
        result = _builder().build_scenario(ScenarioType.OPTIMISTIC)
        d = result.to_dict()
        for key in ("scenario_type", "name", "value", "base_value", "delta_pct", "parameters"):
            assert key in d

    def test_A08_add_parameter_returns_self(self):
        sb = ScenarioBuilder(1_000_000)
        ret = sb.add_parameter("x", 0, 10, -10)
        assert ret is sb

    def test_A09_no_parameters_optimistic_equals_base(self):
        result = ScenarioBuilder(BASE_VALUE).build_scenario(ScenarioType.OPTIMISTIC)
        assert result.value == BASE_VALUE

    def test_A10_optimistic_delta_pct_positive(self):
        result = _builder().build_scenario(ScenarioType.OPTIMISTIC)
        assert result.delta_pct > 0

    def test_A11_pessimistic_delta_pct_negative(self):
        result = _builder().build_scenario(ScenarioType.PESSIMISTIC)
        assert result.delta_pct < 0

    def test_A12_parameters_in_to_dict(self):
        result = _builder().build_scenario(ScenarioType.BASE_CASE)
        assert len(result.to_dict()["parameters"]) == 2


# ===========================================================================
# B. MonteCarloEngine
# ===========================================================================

class TestMonteCarloEngine:

    def test_B01_run_returns_montecarlo_result(self):
        engine = MonteCarloEngine(MonteCarloConfig(iterations=1000, seed=42))
        result = engine.run(BASE_VALUE, volatility=15)
        assert isinstance(result, MonteCarloResult)

    def test_B02_mean_close_to_base_value(self):
        engine = MonteCarloEngine(MonteCarloConfig(iterations=10_000, seed=42))
        result = engine.run(BASE_VALUE, volatility=15)
        assert abs(result.mean - BASE_VALUE) < BASE_VALUE * 0.05

    def test_B03_std_positive_for_nonzero_volatility(self):
        engine = MonteCarloEngine(MonteCarloConfig(iterations=1000, seed=42))
        result = engine.run(BASE_VALUE, volatility=15)
        assert result.std > 0

    def test_B04_percentile_ordering_p5_p50_p95(self):
        engine = MonteCarloEngine(MonteCarloConfig(iterations=5000, seed=42))
        result = engine.run(BASE_VALUE, volatility=15)
        assert result.p5 < result.p50 < result.p95

    def test_B05_p25_less_than_p75(self):
        engine = MonteCarloEngine(MonteCarloConfig(iterations=5000, seed=42))
        result = engine.run(BASE_VALUE, volatility=15)
        assert result.p25 < result.p75

    def test_B06_iterations_matches_config(self):
        engine = MonteCarloEngine(MonteCarloConfig(iterations=500, seed=1))
        result = engine.run(BASE_VALUE, volatility=10)
        assert result.iterations == 500

    def test_B07_seed_produces_reproducible_results(self):
        cfg = MonteCarloConfig(iterations=1000, seed=99)
        r1  = MonteCarloEngine(cfg).run(BASE_VALUE, volatility=20)
        r2  = MonteCarloEngine(cfg).run(BASE_VALUE, volatility=20)
        assert r1.mean == r2.mean
        assert r1.p50  == r2.p50

    def test_B08_zero_volatility_gives_constant(self):
        engine = MonteCarloEngine(MonteCarloConfig(iterations=200, seed=0))
        result = engine.run(BASE_VALUE, volatility=0)
        assert result.std == 0.0
        assert result.mean == BASE_VALUE

    def test_B09_to_dict_has_required_keys(self):
        engine = MonteCarloEngine(MonteCarloConfig(iterations=500, seed=7))
        d = engine.run(BASE_VALUE, volatility=10).to_dict()
        for key in ("mean", "std", "p5", "p25", "p50", "p75", "p95",
                    "iterations", "confidence_interval"):
            assert key in d

    def test_B10_higher_volatility_larger_std(self):
        cfg  = MonteCarloConfig(iterations=5000, seed=42)
        low  = MonteCarloEngine(cfg).run(BASE_VALUE, volatility=5)
        high = MonteCarloEngine(cfg).run(BASE_VALUE, volatility=25)
        assert high.std > low.std

    def test_B11_run_with_parameters_returns_result(self):
        engine = MonteCarloEngine(MonteCarloConfig(iterations=1000, seed=42))
        params = [
            {"name": "location", "std_pct": 10, "weight": 0.6},
            {"name": "market",   "std_pct": 8,  "weight": 0.4},
        ]
        result = engine.run_with_parameters(BASE_VALUE, params)
        assert isinstance(result, MonteCarloResult)

    def test_B12_confidence_interval_ordered(self):
        engine = MonteCarloEngine(MonteCarloConfig(iterations=2000, seed=42))
        result = engine.run(BASE_VALUE, volatility=15)
        lo, hi = result.confidence_interval
        assert lo < hi


# ===========================================================================
# C. SensitivityMatrix
# ===========================================================================

class TestSensitivityMatrix:

    def test_C01_analyze_returns_sensitivity_result(self):
        sm = SensitivityMatrix(BASE_VALUE)
        result = sm.analyze("cap_rate", [-10, 0, 10], "location", [-5, 0, 5])
        assert isinstance(result, SensitivityResult)

    def test_C02_matrix_dimensions_correct(self):
        sm     = SensitivityMatrix(BASE_VALUE)
        result = sm.analyze("v1", [-10, 0, 10], "v2", [-5, 0, 5, 10])
        assert len(result.matrix) == 3       # rows = var1
        assert len(result.matrix[0]) == 4    # cols = var2

    def test_C03_zero_change_equals_base_value(self):
        sm     = SensitivityMatrix(BASE_VALUE)
        result = sm.analyze("v1", [0], "v2", [0])
        assert abs(result.matrix[0][0] - BASE_VALUE) < 0.01

    def test_C04_positive_changes_increase_value(self):
        sm     = SensitivityMatrix(BASE_VALUE)
        result = sm.analyze("v1", [10], "v2", [10])
        assert result.matrix[0][0] > BASE_VALUE

    def test_C05_negative_changes_decrease_value(self):
        sm     = SensitivityMatrix(BASE_VALUE)
        result = sm.analyze("v1", [-10], "v2", [-10])
        assert result.matrix[0][0] < BASE_VALUE

    def test_C06_to_dict_has_matrix_key(self):
        sm = SensitivityMatrix(BASE_VALUE)
        d  = sm.analyze("v1", [-10, 0, 10], "v2", [-10, 0, 10]).to_dict()
        assert "matrix" in d
        assert "var1_name" in d
        assert "var2_name" in d
        assert "base_value" in d

    def test_C07_get_value_matches_matrix(self):
        sm     = SensitivityMatrix(BASE_VALUE)
        result = sm.analyze("v1", [-10, 0, 10], "v2", [-5, 0, 5])
        assert result.get_value(1, 1) == result.matrix[1][1]

    def test_C08_var_values_match_input(self):
        changes = [-20, -10, 0, 10, 20]
        sm      = SensitivityMatrix(BASE_VALUE)
        result  = sm.analyze("v1", changes, "v2", [0])
        assert result.var1_values == changes

    def test_C09_multiplicative_symmetry(self):
        # base*(1+0.1)*(1-0.1) == base*(1-0.1)*(1+0.1)
        sm  = SensitivityMatrix(BASE_VALUE)
        r   = sm.analyze("v1", [-10, 10], "v2", [-10, 10])
        assert abs(r.matrix[0][1] - r.matrix[1][0]) < 0.01

    def test_C10_custom_value_fn(self):
        sm = SensitivityMatrix(1_000_000)
        fn = lambda base, d1, d2: base + d1 + d2
        r  = sm.analyze("v1", [100], "v2", [200], value_fn=fn)
        assert r.matrix[0][0] == 1_000_300


# ===========================================================================
# D. StressTestSuite
# ===========================================================================

class TestStressTestSuite:

    def test_D01_run_all_returns_list(self):
        results = StressTestSuite().run_all(BASE_VALUE)
        assert isinstance(results, list)

    def test_D02_run_all_length_matches_scenarios(self):
        suite = StressTestSuite()
        assert len(suite.run_all(BASE_VALUE)) == len(suite.scenarios)

    def test_D03_run_scenario_returns_result(self):
        suite    = StressTestSuite()
        scenario = suite.scenarios[0]
        result   = suite.run_scenario(scenario, BASE_VALUE)
        assert isinstance(result, StressTestResult)

    def test_D04_covid_shock_reduces_value(self):
        suite  = StressTestSuite()
        covid  = suite.get_scenario("covid_shock")
        result = suite.run_scenario(covid, BASE_VALUE)
        assert result.stressed_value < BASE_VALUE

    def test_D05_recovery_boom_increases_value(self):
        suite    = StressTestSuite()
        recovery = suite.get_scenario("recovery_boom")
        result   = suite.run_scenario(recovery, BASE_VALUE)
        assert result.stressed_value > BASE_VALUE

    def test_D06_worst_case_is_minimum(self):
        suite   = StressTestSuite()
        worst   = suite.worst_case(BASE_VALUE)
        results = suite.run_all(BASE_VALUE)
        min_val = min(r.stressed_value for r in results)
        assert abs(worst.stressed_value - min_val) < 0.01

    def test_D07_best_case_is_maximum(self):
        suite   = StressTestSuite()
        best    = suite.best_case(BASE_VALUE)
        results = suite.run_all(BASE_VALUE)
        max_val = max(r.stressed_value for r in results)
        assert abs(best.stressed_value - max_val) < 0.01

    def test_D08_add_custom_scenario(self):
        suite  = StressTestSuite()
        before = len(suite.scenarios)
        custom = StressScenario("my_shock", "Custom test", {"factor": -5}, "mild")
        suite.add_scenario(custom)
        assert len(suite.scenarios) == before + 1

    def test_D09_get_scenario_by_name(self):
        suite = StressTestSuite()
        s     = suite.get_scenario("market_crash")
        assert s is not None
        assert s.name == "market_crash"

    def test_D10_get_nonexistent_scenario_returns_none(self):
        assert StressTestSuite().get_scenario("does_not_exist") is None

    def test_D11_stress_result_to_dict_keys(self):
        suite  = StressTestSuite()
        result = suite.run_scenario(suite.scenarios[0], BASE_VALUE)
        d      = result.to_dict()
        for key in ("scenario", "base_value", "stressed_value", "impact_pct", "severity"):
            assert key in d

    def test_D12_summary_has_all_keys(self):
        d = StressTestSuite().summary(BASE_VALUE)
        for key in ("base_value", "scenarios", "worst_case", "best_case", "total_scenarios"):
            assert key in d
