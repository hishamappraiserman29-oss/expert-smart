"""
Tests for Phase 16.3 engines:
  - DCFEngine (DC01–DC30)  — core_engine/engines/dcf_engine.py
  - ResidualLandEngine (RL01–RL30) — core_engine/engines/residual_land_engine.py

All tests are pure-unit / deterministic — no server, no DB, no RAG.
"""

import math
from decimal import Decimal

import pytest

from core_engine.engines.dcf_engine import DCFEngine
from core_engine.engines.residual_land_engine import ResidualLandEngine

# ══════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════

@pytest.fixture
def dcf_engine():
    return DCFEngine()


@pytest.fixture
def rl_engine():
    return ResidualLandEngine()


# ── DCF golden fixture ────────────────────────────────────────────────
# CF[-1000, 1100], r=0.10, TV=0
# pv_cfs = [-1000, 1100/1.10] = [-1000, 1000]; NPV=0; IRR≈10%
@pytest.fixture
def dcf_breakeven_inputs():
    return {
        "cash_flows":    [-1000.0, 1100.0],
        "discount_rate": 0.10,
        # no terminal_value → warning
    }


# CF[-1000, 500, 600, 700], r=0.12, caller TV=5000
# Detailed values computed in DC10
@pytest.fixture
def dcf_full_inputs():
    return {
        "cash_flows":    [-1_000_000.0, 200_000.0, 300_000.0, 400_000.0],
        "discount_rate": 0.12,
        "terminal_value": 3_000_000.0,
    }


# CF for terminal_cap_rate derivation: [-500, 200, 200], r=0.10, tcap=0.08
# TV = CF[-1]/tcap = 200/0.08 = 2500
@pytest.fixture
def dcf_tcap_inputs():
    return {
        "cash_flows":      [-500.0, 200.0, 200.0],
        "discount_rate":   0.10,
        "terminal_cap_rate": 0.08,
    }


# ── RLV golden fixture ────────────────────────────────────────────────
# GDV=10M, tdc=5M, profit=1.5M, finance=0.5M, fees=0.2M
# total_costs=7.2M, cost_ratio=0.72, rlv=2.8M
# sensitivity_high=3.3M, sensitivity_low=2.3M
@pytest.fixture
def rl_full_inputs():
    return {
        "gross_development_value": 10_000_000.0,
        "total_development_cost":   5_000_000.0,
        "developer_profit":         1_500_000.0,
        "finance_cost":               500_000.0,
        "professional_fees":          200_000.0,
    }


# ══════════════════════════════════════════════════════════════════════
# DCFEngine Tests
# ══════════════════════════════════════════════════════════════════════

class TestDCFEngine:

    # DC01 – breakeven NPV ≈ 0 at r=10% with CF=[-1000, 1100], TV=0
    def test_dc01_npv_breakeven(self, dcf_engine):
        inputs = {"cash_flows": [-1000.0, 1100.0], "discount_rate": 0.10}
        result = dcf_engine.calculate(inputs)
        npv = float(result.value)
        assert abs(npv) < 1e-4, f"Expected NPV≈0; got {npv}"

    # DC02 – caller-supplied terminal_value is included in NPV
    def test_dc02_caller_terminal_value(self, dcf_engine, dcf_full_inputs):
        result = dcf_engine.calculate(dcf_full_inputs)
        assert result.value is not None
        assert result.metadata["terminal_value"] == pytest.approx(3_000_000.0)
        assert result.metadata["terminal_value_source"] == "caller-supplied terminal_value"

    # DC03 – terminal_cap_rate derives TV = CF[-1] / tcap
    def test_dc03_terminal_cap_rate_derivation(self, dcf_engine, dcf_tcap_inputs):
        result = dcf_engine.calculate(dcf_tcap_inputs)
        expected_tv = 200.0 / 0.08
        assert result.metadata["terminal_value"] == pytest.approx(expected_tv, rel=1e-4)
        assert "terminal_cap_rate" in result.metadata["terminal_value_source"]

    # DC04 – IRR is returned and is a float (converged)
    def test_dc04_irr_returned(self, dcf_engine):
        # Simple: CF=[-1000, 1110], TV=0 → IRR=11%
        inputs = {"cash_flows": [-1000.0, 1110.0], "discount_rate": 0.10}
        result = dcf_engine.calculate(inputs)
        irr = result.metadata["irr"]
        assert irr is not None
        assert abs(irr - 0.11) < 1e-4, f"IRR should be ≈0.11; got {irr}"

    # DC05 – IRR returns None when all cash flows are same sign (no zero crossing)
    def test_dc05_irr_no_solution(self, dcf_engine):
        # All positive → NPV(r) always positive → no IRR
        inputs = {"cash_flows": [100.0, 200.0, 300.0], "discount_rate": 0.10}
        result = dcf_engine.calculate(inputs)
        assert result.metadata["irr"] is None

    # DC06 – confidence = high (rate in [5%,30%] + terminal_value supplied)
    def test_dc06_confidence_high(self, dcf_engine, dcf_full_inputs):
        result = dcf_engine.calculate(dcf_full_inputs)
        assert result.confidence == "high"

    # DC07 – confidence = medium (rate in range, no terminal_value or tcap)
    def test_dc07_confidence_medium_no_tv(self, dcf_engine):
        inputs = {"cash_flows": [-100.0, 110.0], "discount_rate": 0.10}
        result = dcf_engine.calculate(inputs)
        assert result.confidence == "medium"

    # DC08 – confidence = low (rate outside [5%,30%])
    def test_dc08_confidence_low_unusual_rate(self, dcf_engine):
        inputs = {
            "cash_flows":     [-100.0, 110.0],
            "discount_rate":   0.40,
            "terminal_value":  500.0,
        }
        result = dcf_engine.calculate(inputs)
        assert result.confidence == "low"

    # DC09 – confidence = low when discount_rate = 0
    def test_dc09_confidence_low_zero_rate(self, dcf_engine):
        inputs = {
            "cash_flows":     [100.0, 200.0],
            "discount_rate":   0.0,
            "terminal_value":  500.0,
        }
        result = dcf_engine.calculate(inputs)
        assert result.confidence == "low"

    # DC10 – NPV includes discounted periodic CFs + discounted terminal value
    def test_dc10_npv_full_formula(self, dcf_engine, dcf_full_inputs):
        result = dcf_engine.calculate(dcf_full_inputs)
        cfs = dcf_full_inputs["cash_flows"]
        r   = dcf_full_inputs["discount_rate"]
        tv  = dcf_full_inputs["terminal_value"]
        n   = len(cfs)
        last_t = n - 1
        expected_pv_cfs = [cf / (1 + r) ** t if t > 0 else cf for t, cf in enumerate(cfs)]
        expected_pv_tv  = tv / (1 + r) ** last_t
        expected_npv    = sum(expected_pv_cfs) + expected_pv_tv
        assert float(result.value) == pytest.approx(expected_npv, rel=1e-4)

    # DC11 – metadata contains all expected keys
    def test_dc11_metadata_keys(self, dcf_engine, dcf_full_inputs):
        result = dcf_engine.calculate(dcf_full_inputs)
        for key in (
            "npv", "irr", "irr_pct", "terminal_value", "terminal_value_source",
            "discount_rate", "projection_years", "cash_flows",
            "pv_of_cash_flows", "pv_of_terminal_value",
        ):
            assert key in result.metadata, f"Missing metadata key: {key}"

    # DC12 – audit trail has exactly 4 steps
    def test_dc12_audit_trail_length(self, dcf_engine, dcf_full_inputs):
        result = dcf_engine.calculate(dcf_full_inputs)
        assert len(result.audit_trail) == 4

    # DC13 – engine_name = "dcf"
    def test_dc13_engine_name(self, dcf_engine):
        assert dcf_engine.name == "dcf"

    # DC14 – version = "1.0.0"
    def test_dc14_version(self, dcf_engine):
        assert dcf_engine.version == "1.0.0"

    # DC15 – value is Decimal when NPV is finite
    def test_dc15_value_is_decimal(self, dcf_engine, dcf_full_inputs):
        result = dcf_engine.calculate(dcf_full_inputs)
        assert isinstance(result.value, Decimal)

    # DC16 – pv_of_cash_flows[0] equals CF[0] exactly (t=0 not discounted)
    def test_dc16_t0_not_discounted(self, dcf_engine, dcf_full_inputs):
        result = dcf_engine.calculate(dcf_full_inputs)
        pv0 = result.metadata["pv_of_cash_flows"][0]
        cf0 = dcf_full_inputs["cash_flows"][0]
        assert pv0 == pytest.approx(cf0)

    # DC17 – terminal_value derived from terminal_cap_rate == CF[-1]/tcap
    def test_dc17_tv_derived_from_tcap(self, dcf_engine, dcf_tcap_inputs):
        result = dcf_engine.calculate(dcf_tcap_inputs)
        cf_last = dcf_tcap_inputs["cash_flows"][-1]
        tcap    = dcf_tcap_inputs["terminal_cap_rate"]
        assert result.metadata["terminal_value"] == pytest.approx(cf_last / tcap, rel=1e-4)

    # DC18 – pv_of_terminal_value correctly discounted to last_t
    def test_dc18_pv_terminal_discounted(self, dcf_engine, dcf_full_inputs):
        result = dcf_engine.calculate(dcf_full_inputs)
        cfs  = dcf_full_inputs["cash_flows"]
        r    = dcf_full_inputs["discount_rate"]
        tv   = dcf_full_inputs["terminal_value"]
        last_t = len(cfs) - 1
        expected = tv / (1 + r) ** last_t
        assert result.metadata["pv_of_terminal_value"] == pytest.approx(expected, rel=1e-4)

    # DC19 – error: MISSING_CASH_FLOWS
    def test_dc19_error_missing_cash_flows(self, dcf_engine):
        result = dcf_engine.calculate({"discount_rate": 0.10})
        assert result.value is None
        assert result.confidence == "insufficient"
        codes = [i.code for i in result.issues]
        assert "MISSING_CASH_FLOWS" in codes

    # DC20 – error: empty cash_flows list
    def test_dc20_error_empty_cash_flows(self, dcf_engine):
        result = dcf_engine.calculate({"cash_flows": [], "discount_rate": 0.10})
        assert result.value is None
        codes = [i.code for i in result.issues]
        assert "MISSING_CASH_FLOWS" in codes

    # DC21 – error: MISSING_DISCOUNT_RATE
    def test_dc21_error_missing_discount_rate(self, dcf_engine):
        result = dcf_engine.calculate({"cash_flows": [-100.0, 110.0]})
        codes = [i.code for i in result.issues]
        assert "MISSING_DISCOUNT_RATE" in codes

    # DC22 – error: INVALID_DISCOUNT_RATE (exactly -1.0)
    def test_dc22_error_discount_rate_minus_one(self, dcf_engine):
        result = dcf_engine.calculate({"cash_flows": [-100.0, 110.0], "discount_rate": -1.0})
        codes = [i.code for i in result.issues]
        assert "INVALID_DISCOUNT_RATE" in codes
        assert result.value is None

    # DC23 – error: INVALID_DISCOUNT_RATE (below -1)
    def test_dc23_error_discount_rate_below_minus_one(self, dcf_engine):
        result = dcf_engine.calculate({"cash_flows": [-100.0, 110.0], "discount_rate": -2.0})
        codes = [i.code for i in result.issues]
        assert "INVALID_DISCOUNT_RATE" in codes

    # DC24 – error: INVALID_TERMINAL_CAP_RATE (= 0)
    def test_dc24_error_terminal_cap_rate_zero(self, dcf_engine):
        result = dcf_engine.calculate({
            "cash_flows":       [-100.0, 110.0],
            "discount_rate":     0.10,
            "terminal_cap_rate": 0.0,
        })
        codes = [i.code for i in result.issues]
        assert "INVALID_TERMINAL_CAP_RATE" in codes
        assert result.value is None

    # DC25 – error: INVALID_TERMINAL_CAP_RATE (negative)
    def test_dc25_error_terminal_cap_rate_negative(self, dcf_engine):
        result = dcf_engine.calculate({
            "cash_flows":       [-100.0, 110.0],
            "discount_rate":     0.10,
            "terminal_cap_rate": -0.05,
        })
        codes = [i.code for i in result.issues]
        assert "INVALID_TERMINAL_CAP_RATE" in codes

    # DC26 – warning: ZERO_DISCOUNT_RATE
    def test_dc26_warning_zero_discount_rate(self, dcf_engine):
        result = dcf_engine.calculate({
            "cash_flows":    [-100.0, 100.0],
            "discount_rate":  0.0,
            "terminal_value": 500.0,
        })
        codes = [i.code for i in result.issues]
        assert "ZERO_DISCOUNT_RATE" in codes
        # Engine still calculates (warning, not error)
        assert result.value is not None

    # DC27 – warning: UNUSUAL_DISCOUNT_RATE (rate > 30%)
    def test_dc27_warning_unusual_rate_high(self, dcf_engine):
        result = dcf_engine.calculate({
            "cash_flows":    [-100.0, 140.0],
            "discount_rate":  0.35,
            "terminal_value": 500.0,
        })
        codes = [i.code for i in result.issues]
        assert "UNUSUAL_DISCOUNT_RATE" in codes

    # DC28 – warning: UNUSUAL_DISCOUNT_RATE (rate > 0 but < 5%)
    def test_dc28_warning_unusual_rate_low(self, dcf_engine):
        result = dcf_engine.calculate({
            "cash_flows":    [-100.0, 103.0],
            "discount_rate":  0.02,
            "terminal_value": 500.0,
        })
        codes = [i.code for i in result.issues]
        assert "UNUSUAL_DISCOUNT_RATE" in codes

    # DC29 – warning: MISSING_TERMINAL_VALUE (neither tv nor tcap supplied)
    def test_dc29_warning_missing_terminal_value(self, dcf_engine):
        result = dcf_engine.calculate({
            "cash_flows":    [-100.0, 110.0],
            "discount_rate":  0.10,
        })
        codes = [i.code for i in result.issues]
        assert "MISSING_TERMINAL_VALUE" in codes

    # DC30 – when both terminal_value and terminal_cap_rate supplied, tv takes priority
    def test_dc30_tv_priority_over_tcap(self, dcf_engine):
        tv_caller = 99_999.0
        result = dcf_engine.calculate({
            "cash_flows":       [-100.0, 110.0],
            "discount_rate":     0.10,
            "terminal_value":    tv_caller,
            "terminal_cap_rate": 0.08,          # would derive different TV
        })
        assert result.metadata["terminal_value"] == pytest.approx(tv_caller)
        assert result.metadata["terminal_value_source"] == "caller-supplied terminal_value"


# ══════════════════════════════════════════════════════════════════════
# ResidualLandEngine Tests
# ══════════════════════════════════════════════════════════════════════

class TestResidualLandEngine:

    # RL01 – full inputs: rlv = 10M - 7.2M = 2.8M
    def test_rl01_rlv_full(self, rl_engine, rl_full_inputs):
        result = rl_engine.calculate(rl_full_inputs)
        assert result.value is not None
        assert float(result.value) == pytest.approx(2_800_000.0)

    # RL02 – sensitivity_high = gdv*1.05 - 7.2M = 3.3M
    def test_rl02_sensitivity_high(self, rl_engine, rl_full_inputs):
        result = rl_engine.calculate(rl_full_inputs)
        assert result.metadata["sensitivity_high"] == pytest.approx(3_300_000.0)

    # RL03 – sensitivity_low = gdv*0.95 - 7.2M = 2.3M
    def test_rl03_sensitivity_low(self, rl_engine, rl_full_inputs):
        result = rl_engine.calculate(rl_full_inputs)
        assert result.metadata["sensitivity_low"] == pytest.approx(2_300_000.0)

    # RL04 – feasibility_status = "feasible" when rlv > 0
    def test_rl04_feasibility_feasible(self, rl_engine, rl_full_inputs):
        result = rl_engine.calculate(rl_full_inputs)
        assert result.metadata["feasibility_status"] == "feasible"

    # RL05 – cost_ratio = 7.2M / 10M = 0.72
    def test_rl05_cost_ratio(self, rl_engine, rl_full_inputs):
        result = rl_engine.calculate(rl_full_inputs)
        assert result.metadata["cost_ratio"] == pytest.approx(0.72)

    # RL06 – engine_name = "residual_land"
    def test_rl06_engine_name(self, rl_engine):
        assert rl_engine.name == "residual_land"

    # RL07 – version = "1.0.0"
    def test_rl07_version(self, rl_engine):
        assert rl_engine.version == "1.0.0"

    # RL08 – value is Decimal when feasible
    def test_rl08_value_is_decimal(self, rl_engine, rl_full_inputs):
        result = rl_engine.calculate(rl_full_inputs)
        assert isinstance(result.value, Decimal)

    # RL09 – audit trail has 3 steps (aggregate costs, RLV, sensitivity)
    def test_rl09_audit_trail_length(self, rl_engine, rl_full_inputs):
        result = rl_engine.calculate(rl_full_inputs)
        assert len(result.audit_trail) == 3

    # RL10 – metadata contains all expected keys
    def test_rl10_metadata_keys(self, rl_engine, rl_full_inputs):
        result = rl_engine.calculate(rl_full_inputs)
        for key in (
            "gross_development_value", "total_development_cost", "developer_profit",
            "finance_cost", "professional_fees", "total_costs", "cost_ratio",
            "residual_land_value", "feasibility_status",
            "sensitivity_high", "sensitivity_low",
        ):
            assert key in result.metadata, f"Missing metadata key: {key}"

    # RL11 – minimal inputs (only GDV + tdc): optional cost items default to 0
    def test_rl11_minimal_inputs(self, rl_engine):
        inputs = {
            "gross_development_value": 5_000_000.0,
            "total_development_cost":  3_000_000.0,
        }
        result = rl_engine.calculate(inputs)
        # developer_profit=0 → ZERO_DEVELOPER_PROFIT warning; but still calculates
        assert result.value is not None
        assert float(result.value) == pytest.approx(2_000_000.0)
        assert result.metadata["developer_profit"] == 0.0

    # RL12 – not_feasible: value = None, feasibility = "not_feasible"
    def test_rl12_not_feasible_value_none(self, rl_engine):
        inputs = {
            "gross_development_value": 5_000_000.0,
            "total_development_cost":  4_000_000.0,
            "developer_profit":        1_500_000.0,
        }
        result = rl_engine.calculate(inputs)
        assert result.value is None
        assert result.metadata["feasibility_status"] == "not_feasible"

    # RL13 – not_feasible: confidence = low
    def test_rl13_not_feasible_confidence_low(self, rl_engine):
        inputs = {
            "gross_development_value": 5_000_000.0,
            "total_development_cost":  6_000_000.0,
            "developer_profit":        0.0,
        }
        result = rl_engine.calculate(inputs)
        assert result.confidence == "low"

    # RL14 – HIGH_COST_RATIO warning when costs ≥ 90% of GDV
    def test_rl14_high_cost_ratio_warning(self, rl_engine):
        inputs = {
            "gross_development_value": 10_000_000.0,
            "total_development_cost":   9_100_000.0,
            "developer_profit":             0.0,
        }
        result = rl_engine.calculate(inputs)
        codes = [i.code for i in result.issues]
        assert "HIGH_COST_RATIO" in codes

    # RL15 – high cost ratio + rlv>0 → confidence = medium
    def test_rl15_high_cost_ratio_confidence_medium(self, rl_engine):
        inputs = {
            "gross_development_value": 10_000_000.0,
            "total_development_cost":   9_050_000.0,   # 90.5% → HIGH_COST_RATIO
            "developer_profit":             0.0,
        }
        result = rl_engine.calculate(inputs)
        assert result.metadata["residual_land_value"] > 0
        assert result.confidence == "medium"

    # RL16 – zero developer_profit → ZERO_DEVELOPER_PROFIT warning
    def test_rl16_zero_profit_warning(self, rl_engine):
        inputs = {
            "gross_development_value": 10_000_000.0,
            "total_development_cost":   7_000_000.0,
            "developer_profit":             0.0,
        }
        result = rl_engine.calculate(inputs)
        codes = [i.code for i in result.issues]
        assert "ZERO_DEVELOPER_PROFIT" in codes

    # RL17 – zero developer_profit + normal cost_ratio → confidence = medium
    def test_rl17_zero_profit_confidence_medium(self, rl_engine):
        inputs = {
            "gross_development_value": 10_000_000.0,
            "total_development_cost":   7_000_000.0,
            "developer_profit":             0.0,
        }
        result = rl_engine.calculate(inputs)
        assert result.confidence == "medium"

    # RL18 – professional_fees = 0 (no warning beyond ZERO_DEVELOPER_PROFIT if profit=0)
    def test_rl18_zero_fees_no_warning(self, rl_engine, rl_full_inputs):
        rl_full_inputs["professional_fees"] = 0.0
        result = rl_engine.calculate(rl_full_inputs)
        codes = [i.code for i in result.issues]
        assert "INVALID_PROFESSIONAL_FEES" not in codes

    # RL19 – finance_cost = 0 (no error)
    def test_rl19_zero_finance_no_error(self, rl_engine, rl_full_inputs):
        rl_full_inputs["finance_cost"] = 0.0
        result = rl_engine.calculate(rl_full_inputs)
        assert result.value is not None
        codes = [i.code for i in result.issues if i.severity == "error"]
        assert "INVALID_FINANCE_COST" not in codes

    # RL20 – rlv exactly 0 → value = None (not > 0)
    def test_rl20_rlv_exactly_zero(self, rl_engine):
        inputs = {
            "gross_development_value": 10_000_000.0,
            "total_development_cost":  10_000_000.0,
            "developer_profit":             0.0,
        }
        result = rl_engine.calculate(inputs)
        assert result.value is None
        assert result.metadata["residual_land_value"] == pytest.approx(0.0)

    # RL21 – error: MISSING_GDV
    def test_rl21_error_missing_gdv(self, rl_engine):
        result = rl_engine.calculate({"total_development_cost": 5_000_000.0})
        codes = [i.code for i in result.issues]
        assert "MISSING_GDV" in codes
        assert result.value is None

    # RL22 – error: INVALID_GDV (= 0)
    def test_rl22_error_gdv_zero(self, rl_engine):
        result = rl_engine.calculate({
            "gross_development_value": 0.0,
            "total_development_cost":  5_000_000.0,
        })
        codes = [i.code for i in result.issues]
        assert "INVALID_GDV" in codes

    # RL23 – error: INVALID_GDV (negative)
    def test_rl23_error_gdv_negative(self, rl_engine):
        result = rl_engine.calculate({
            "gross_development_value": -1_000_000.0,
            "total_development_cost":   5_000_000.0,
        })
        codes = [i.code for i in result.issues]
        assert "INVALID_GDV" in codes

    # RL24 – error: MISSING_DEVELOPMENT_COST
    def test_rl24_error_missing_dev_cost(self, rl_engine):
        result = rl_engine.calculate({"gross_development_value": 10_000_000.0})
        codes = [i.code for i in result.issues]
        assert "MISSING_DEVELOPMENT_COST" in codes

    # RL25 – error: INVALID_DEVELOPMENT_COST (negative)
    def test_rl25_error_negative_dev_cost(self, rl_engine):
        result = rl_engine.calculate({
            "gross_development_value": 10_000_000.0,
            "total_development_cost":  -1_000_000.0,
        })
        codes = [i.code for i in result.issues]
        assert "INVALID_DEVELOPMENT_COST" in codes

    # RL26 – error: INVALID_DEVELOPER_PROFIT (negative)
    def test_rl26_error_negative_profit(self, rl_engine):
        result = rl_engine.calculate({
            "gross_development_value": 10_000_000.0,
            "total_development_cost":   5_000_000.0,
            "developer_profit":            -1.0,
        })
        codes = [i.code for i in result.issues]
        assert "INVALID_DEVELOPER_PROFIT" in codes

    # RL27 – error: INVALID_FINANCE_COST (negative)
    def test_rl27_error_negative_finance_cost(self, rl_engine):
        result = rl_engine.calculate({
            "gross_development_value": 10_000_000.0,
            "total_development_cost":   5_000_000.0,
            "finance_cost":                -1.0,
        })
        codes = [i.code for i in result.issues]
        assert "INVALID_FINANCE_COST" in codes

    # RL28 – error: INVALID_PROFESSIONAL_FEES (negative)
    def test_rl28_error_negative_fees(self, rl_engine):
        result = rl_engine.calculate({
            "gross_development_value": 10_000_000.0,
            "total_development_cost":   5_000_000.0,
            "professional_fees":           -1.0,
        })
        codes = [i.code for i in result.issues]
        assert "INVALID_PROFESSIONAL_FEES" in codes

    # RL29 – validate() standalone returns issues list (not EngineResult)
    def test_rl29_validate_standalone(self, rl_engine):
        issues = rl_engine.validate({})
        codes = [i.code for i in issues]
        assert "MISSING_GDV" in codes
        assert "MISSING_DEVELOPMENT_COST" in codes

    # RL30 – confidence = high: all cost items present, rlv > 0, cost_ratio < 90%
    def test_rl30_confidence_high(self, rl_engine, rl_full_inputs):
        result = rl_engine.calculate(rl_full_inputs)
        # cost_ratio=0.72 < 0.90, profit>0, rlv>0
        assert result.confidence == "high"
