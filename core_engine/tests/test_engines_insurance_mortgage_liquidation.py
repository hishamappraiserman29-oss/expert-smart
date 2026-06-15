"""
Tests for Phase 16.4 engines:
  - InsuranceEngine       (IN01–IN20) — core_engine/engines/insurance_engine.py
  - MortgageLendingEngine (MO01–MO20) — core_engine/engines/mortgage_lending_engine.py
  - LiquidationEngine     (LI01–LI20) — core_engine/engines/liquidation_engine.py

All tests are pure-unit / deterministic — no server, no DB, no RAG.
"""

from decimal import Decimal

import pytest

from core_engine.engines.insurance_engine import InsuranceEngine
from core_engine.engines.liquidation_engine import LiquidationEngine
from core_engine.engines.mortgage_lending_engine import MortgageLendingEngine

# ══════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════

@pytest.fixture
def ins_engine():
    return InsuranceEngine()


@pytest.fixture
def mtg_engine():
    return MortgageLendingEngine()


@pytest.fixture
def liq_engine():
    return LiquidationEngine()


# ── Insurance golden fixture ──────────────────────────────────────────
# area=300, const=8000, finish=2000 → building_cost = 300×10000 = 3_000_000
# mep=500_000, debris=100_000, fees=200_000 → add=800_000
# rcn = 3_800_000 ; insurance_value = 3_800_000 × 1.10 = 4_180_000
@pytest.fixture
def ins_full_inputs():
    return {
        "building_area_sqm":          300.0,
        "construction_cost_per_m2":  8000.0,
        "finishing_cost_per_m2":     2000.0,
        "mep_cost":                500_000.0,
        "debris_removal_cost":     100_000.0,
        "professional_fees":       200_000.0,
        "construction_inflation_rate": 0.10,
    }


# ── Mortgage golden fixture ───────────────────────────────────────────
# mv=5M, haircut=0.20, ltv=0.70
# lending_value = 5M × 0.80 = 4_000_000
# max_approved_loan = 4M × 0.70 = 2_800_000
# actual_ltv = 2.5M / 5M = 0.50
# noi_coverage = 300_000 / (2_500_000 × 0.08) = 1.50
@pytest.fixture
def mtg_full_inputs():
    return {
        "market_value":            5_000_000.0,
        "haircut":                 0.20,
        "ltv":                     0.70,
        "requested_loan_amount":   2_500_000.0,
        "stable_noi":               300_000.0,
        "remaining_economic_life": 40,
    }


# ── Liquidation golden fixture ────────────────────────────────────────
# mv=5M, disc=0.25, auction=100k, legal=50k
# gross_lv = 5M × 0.75 = 3_750_000
# total_costs = 150_000
# net_lv = 3_600_000
# sens_conservative = 5M×0.70 − 150k = 3_350_000
# sens_optimistic   = 5M×0.80 − 150k = 3_850_000
@pytest.fixture
def liq_full_inputs():
    return {
        "market_value":            5_000_000.0,
        "forced_sale_discount":    0.25,
        "auction_costs":           100_000.0,
        "legal_costs":              50_000.0,
        "marketing_period_months": 3,
    }


# ══════════════════════════════════════════════════════════════════════
# InsuranceEngine Tests
# ══════════════════════════════════════════════════════════════════════

class TestInsuranceEngine:

    # IN01 – RCN computed from components
    def test_in01_rcn_from_components(self, ins_engine, ins_full_inputs):
        result = ins_engine.calculate(ins_full_inputs)
        assert result.metadata["reinstatement_cost_new"] == pytest.approx(3_800_000.0)

    # IN02 – insurance_value = RCN × (1 + inflation)
    def test_in02_insurance_value(self, ins_engine, ins_full_inputs):
        result = ins_engine.calculate(ins_full_inputs)
        assert float(result.value) == pytest.approx(4_180_000.0)

    # IN03 – caller-supplied reinstatement_cost_new skips component calculation
    def test_in03_rcn_override(self, ins_engine):
        inputs = {
            "reinstatement_cost_new":      5_000_000.0,
            "construction_inflation_rate": 0.10,
        }
        result = ins_engine.calculate(inputs)
        assert result.value is not None
        assert float(result.value) == pytest.approx(5_500_000.0)
        assert result.metadata["rcn_source"] == "caller-supplied reinstatement_cost_new override"

    # IN04 – confidence = high (3+ optional components + inflation supplied)
    def test_in04_confidence_high(self, ins_engine, ins_full_inputs):
        result = ins_engine.calculate(ins_full_inputs)
        assert result.confidence == "high"

    # IN05 – confidence = medium (only 1 optional component, no inflation)
    def test_in05_confidence_medium(self, ins_engine):
        inputs = {
            "building_area_sqm":         300.0,
            "construction_cost_per_m2": 8000.0,
            "mep_cost":               500_000.0,
            # no finishing, no debris, no fees, no inflation
        }
        result = ins_engine.calculate(inputs)
        assert result.confidence == "medium"

    # IN06 – confidence = low (no optional components, no inflation)
    def test_in06_confidence_low(self, ins_engine):
        inputs = {
            "building_area_sqm":         300.0,
            "construction_cost_per_m2": 8000.0,
        }
        result = ins_engine.calculate(inputs)
        assert result.confidence == "low"

    # IN07 – engine_name = "insurance"
    def test_in07_engine_name(self, ins_engine):
        assert ins_engine.name == "insurance"

    # IN08 – version = "1.0.0"
    def test_in08_version(self, ins_engine):
        assert ins_engine.version == "1.0.0"

    # IN09 – value is Decimal
    def test_in09_value_is_decimal(self, ins_engine, ins_full_inputs):
        result = ins_engine.calculate(ins_full_inputs)
        assert isinstance(result.value, Decimal)

    # IN10 – audit trail = 2 steps
    def test_in10_audit_trail_length(self, ins_engine, ins_full_inputs):
        result = ins_engine.calculate(ins_full_inputs)
        assert len(result.audit_trail) == 2

    # IN11 – metadata contains all expected keys
    def test_in11_metadata_keys(self, ins_engine, ins_full_inputs):
        result = ins_engine.calculate(ins_full_inputs)
        for key in (
            "reinstatement_cost_new", "rcn_source", "building_cost",
            "finishing_cost", "mep_cost", "debris_removal_cost",
            "professional_fees", "construction_inflation_rate", "insurance_value",
        ):
            assert key in result.metadata, f"Missing metadata key: {key}"

    # IN12 – MISSING_MEP_COST warning when mep_cost not supplied
    def test_in12_warning_missing_mep(self, ins_engine):
        inputs = {
            "building_area_sqm":         300.0,
            "construction_cost_per_m2": 8000.0,
            "construction_inflation_rate": 0.10,
        }
        result = ins_engine.calculate(inputs)
        codes = [i.code for i in result.issues]
        assert "MISSING_MEP_COST" in codes

    # IN13 – MISSING_DEBRIS_REMOVAL_COST warning
    def test_in13_warning_missing_debris(self, ins_engine):
        inputs = {
            "building_area_sqm":         300.0,
            "construction_cost_per_m2": 8000.0,
        }
        result = ins_engine.calculate(inputs)
        codes = [i.code for i in result.issues]
        assert "MISSING_DEBRIS_REMOVAL_COST" in codes

    # IN14 – MISSING_PROFESSIONAL_FEES warning
    def test_in14_warning_missing_fees(self, ins_engine):
        inputs = {
            "building_area_sqm":         300.0,
            "construction_cost_per_m2": 8000.0,
        }
        result = ins_engine.calculate(inputs)
        codes = [i.code for i in result.issues]
        assert "MISSING_PROFESSIONAL_FEES" in codes

    # IN15 – HIGH_INFLATION_RATE warning (> 30%)
    def test_in15_warning_high_inflation(self, ins_engine):
        inputs = {
            "building_area_sqm":          300.0,
            "construction_cost_per_m2":  8000.0,
            "construction_inflation_rate": 0.40,
        }
        result = ins_engine.calculate(inputs)
        codes = [i.code for i in result.issues]
        assert "HIGH_INFLATION_RATE" in codes

    # IN16 – ZERO_INFLATION_RATE warning when rate not supplied
    def test_in16_warning_zero_inflation(self, ins_engine):
        inputs = {
            "building_area_sqm":         300.0,
            "construction_cost_per_m2": 8000.0,
        }
        result = ins_engine.calculate(inputs)
        codes = [i.code for i in result.issues]
        assert "ZERO_INFLATION_RATE" in codes

    # IN17 – error: MISSING_BUILDING_AREA when no override
    def test_in17_error_missing_building_area(self, ins_engine):
        result = ins_engine.calculate({"construction_cost_per_m2": 8000.0})
        codes = [i.code for i in result.issues]
        assert "MISSING_BUILDING_AREA" in codes
        assert result.value is None

    # IN18 – error: MISSING_CONSTRUCTION_COST
    def test_in18_error_missing_construction_cost(self, ins_engine):
        result = ins_engine.calculate({"building_area_sqm": 300.0})
        codes = [i.code for i in result.issues]
        assert "MISSING_CONSTRUCTION_COST" in codes
        assert result.value is None

    # IN19 – error: INVALID_FINISHING_COST (negative)
    def test_in19_error_invalid_finishing_cost(self, ins_engine):
        result = ins_engine.calculate({
            "building_area_sqm":         300.0,
            "construction_cost_per_m2": 8000.0,
            "finishing_cost_per_m2":      -500.0,
        })
        codes = [i.code for i in result.issues]
        assert "INVALID_FINISHING_COST" in codes
        assert result.value is None

    # IN20 – error: INVALID_INFLATION_RATE (negative)
    def test_in20_error_invalid_inflation_rate(self, ins_engine):
        result = ins_engine.calculate({
            "building_area_sqm":          300.0,
            "construction_cost_per_m2":  8000.0,
            "construction_inflation_rate": -0.05,
        })
        codes = [i.code for i in result.issues]
        assert "INVALID_INFLATION_RATE" in codes
        assert result.value is None


# ══════════════════════════════════════════════════════════════════════
# MortgageLendingEngine Tests
# ══════════════════════════════════════════════════════════════════════

class TestMortgageLendingEngine:

    # MO01 – lending_value = market_value × (1 − haircut)
    def test_mo01_lending_value(self, mtg_engine, mtg_full_inputs):
        result = mtg_engine.calculate(mtg_full_inputs)
        assert float(result.value) == pytest.approx(4_000_000.0)

    # MO02 – max_approved_loan = lending_value × ltv
    def test_mo02_max_approved_loan(self, mtg_engine, mtg_full_inputs):
        result = mtg_engine.calculate(mtg_full_inputs)
        assert result.metadata["max_approved_loan"] == pytest.approx(2_800_000.0)

    # MO03 – actual_ltv = requested_loan / market_value
    def test_mo03_actual_ltv(self, mtg_engine, mtg_full_inputs):
        result = mtg_engine.calculate(mtg_full_inputs)
        assert result.metadata["actual_ltv"] == pytest.approx(0.50)

    # MO04 – LOAN_EXCEEDS_LENDING_VALUE warning when loan > max_approved_loan
    def test_mo04_loan_exceeds_warning(self, mtg_engine):
        inputs = {
            "market_value":           5_000_000.0,
            "haircut":                0.20,
            "ltv":                    0.70,
            "requested_loan_amount":  3_500_000.0,  # > max_approved_loan 2_800_000
        }
        result = mtg_engine.calculate(inputs)
        codes = [i.code for i in result.issues]
        assert "LOAN_EXCEEDS_LENDING_VALUE" in codes

    # MO05 – HIGH_LTV warning when ltv > 0.80
    def test_mo05_high_ltv_warning(self, mtg_engine):
        result = mtg_engine.calculate({
            "market_value": 5_000_000.0,
            "ltv":          0.85,
        })
        codes = [i.code for i in result.issues]
        assert "HIGH_LTV" in codes

    # MO06 – LOW_REMAINING_LIFE warning when < 15 years
    def test_mo06_low_remaining_life_warning(self, mtg_engine):
        result = mtg_engine.calculate({
            "market_value":            5_000_000.0,
            "remaining_economic_life": 10,
        })
        codes = [i.code for i in result.issues]
        assert "LOW_REMAINING_LIFE" in codes

    # MO07 – confidence = high (haircut + ltv + remaining_life all supplied)
    def test_mo07_confidence_high(self, mtg_engine, mtg_full_inputs):
        result = mtg_engine.calculate(mtg_full_inputs)
        assert result.confidence == "high"

    # MO08 – confidence = medium (haircut supplied, remaining_life missing)
    def test_mo08_confidence_medium(self, mtg_engine):
        inputs = {
            "market_value": 5_000_000.0,
            "haircut":      0.20,
            "ltv":          0.70,
            # no remaining_economic_life
        }
        result = mtg_engine.calculate(inputs)
        assert result.confidence == "medium"

    # MO09 – confidence = low (no explicit haircut or ltv)
    def test_mo09_confidence_low(self, mtg_engine):
        result = mtg_engine.calculate({"market_value": 5_000_000.0})
        assert result.confidence == "low"

    # MO10 – engine_name = "mortgage_lending"
    def test_mo10_engine_name(self, mtg_engine):
        assert mtg_engine.name == "mortgage_lending"

    # MO11 – version = "1.0.0"
    def test_mo11_version(self, mtg_engine):
        assert mtg_engine.version == "1.0.0"

    # MO12 – metadata contains all expected keys
    def test_mo12_metadata_keys(self, mtg_engine, mtg_full_inputs):
        result = mtg_engine.calculate(mtg_full_inputs)
        for key in (
            "market_value", "haircut", "ltv", "lending_value", "max_approved_loan",
            "actual_ltv", "noi_coverage", "remaining_economic_life", "risk_notes",
        ):
            assert key in result.metadata, f"Missing metadata key: {key}"

    # MO13 – value is Decimal
    def test_mo13_value_is_decimal(self, mtg_engine, mtg_full_inputs):
        result = mtg_engine.calculate(mtg_full_inputs)
        assert isinstance(result.value, Decimal)

    # MO14 – error: MISSING_MARKET_VALUE
    def test_mo14_error_missing_market_value(self, mtg_engine):
        result = mtg_engine.calculate({"haircut": 0.20})
        codes = [i.code for i in result.issues]
        assert "MISSING_MARKET_VALUE" in codes
        assert result.value is None

    # MO15 – error: INVALID_MARKET_VALUE (= 0)
    def test_mo15_error_invalid_market_value_zero(self, mtg_engine):
        result = mtg_engine.calculate({"market_value": 0.0})
        codes = [i.code for i in result.issues]
        assert "INVALID_MARKET_VALUE" in codes

    # MO16 – error: INVALID_LTV (> 1.0)
    def test_mo16_error_invalid_ltv(self, mtg_engine):
        result = mtg_engine.calculate({"market_value": 5_000_000.0, "ltv": 1.1})
        codes = [i.code for i in result.issues]
        assert "INVALID_LTV" in codes
        assert result.value is None

    # MO17 – error: INVALID_HAIRCUT (= 1.0 — full wipeout)
    def test_mo17_error_invalid_haircut_one(self, mtg_engine):
        result = mtg_engine.calculate({"market_value": 5_000_000.0, "haircut": 1.0})
        codes = [i.code for i in result.issues]
        assert "INVALID_HAIRCUT" in codes
        assert result.value is None

    # MO18 – ZERO_HAIRCUT warning when haircut = 0
    def test_mo18_zero_haircut_warning(self, mtg_engine):
        result = mtg_engine.calculate({"market_value": 5_000_000.0, "haircut": 0.0})
        codes = [i.code for i in result.issues]
        assert "ZERO_HAIRCUT" in codes
        # Engine still calculates (warning, not error)
        assert result.value is not None
        assert float(result.value) == pytest.approx(5_000_000.0)

    # MO19 – noi_coverage computed when stable_noi + loan supplied
    # coverage = 300_000 / (2_500_000 × 0.08) = 1.50
    def test_mo19_noi_coverage_computed(self, mtg_engine, mtg_full_inputs):
        result = mtg_engine.calculate(mtg_full_inputs)
        assert result.metadata["noi_coverage"] == pytest.approx(1.50, rel=1e-4)

    # MO20 – LOW_NOI_COVERAGE warning when coverage < 1.25
    # stable_noi=100k, loan=2.5M → coverage = 100k/(2.5M×0.08) = 0.50 < 1.25
    def test_mo20_low_noi_coverage_warning(self, mtg_engine):
        inputs = {
            "market_value":           5_000_000.0,
            "haircut":                0.20,
            "ltv":                    0.70,
            "requested_loan_amount":  2_500_000.0,
            "stable_noi":               100_000.0,
        }
        result = mtg_engine.calculate(inputs)
        codes = [i.code for i in result.issues]
        assert "LOW_NOI_COVERAGE" in codes


# ══════════════════════════════════════════════════════════════════════
# LiquidationEngine Tests
# ══════════════════════════════════════════════════════════════════════

class TestLiquidationEngine:

    # LI01 – net_liquidation_value = gross_lv − costs
    def test_li01_net_liquidation_value(self, liq_engine, liq_full_inputs):
        result = liq_engine.calculate(liq_full_inputs)
        assert float(result.value) == pytest.approx(3_600_000.0)

    # LI02 – gross_liquidation_value = market_value × (1 − discount)
    def test_li02_gross_liquidation_value(self, liq_engine, liq_full_inputs):
        result = liq_engine.calculate(liq_full_inputs)
        assert result.metadata["gross_liquidation_value"] == pytest.approx(3_750_000.0)

    # LI03 – sensitivity_conservative = MV × (1 − 0.30) − 150k = 3_350_000
    def test_li03_sensitivity_conservative(self, liq_engine, liq_full_inputs):
        result = liq_engine.calculate(liq_full_inputs)
        assert result.metadata["sensitivity_conservative"] == pytest.approx(3_350_000.0)

    # LI04 – sensitivity_optimistic = MV × (1 − 0.20) − 150k = 3_850_000
    def test_li04_sensitivity_optimistic(self, liq_engine, liq_full_inputs):
        result = liq_engine.calculate(liq_full_inputs)
        assert result.metadata["sensitivity_optimistic"] == pytest.approx(3_850_000.0)

    # LI05 – confidence = high (costs supplied, discount in [10%, 50%])
    def test_li05_confidence_high(self, liq_engine, liq_full_inputs):
        result = liq_engine.calculate(liq_full_inputs)
        assert result.confidence == "high"

    # LI06 – confidence = medium (discount in range, but no auction/legal costs)
    def test_li06_confidence_medium(self, liq_engine):
        inputs = {
            "market_value":         5_000_000.0,
            "forced_sale_discount": 0.25,
            # no auction_costs, no legal_costs → both default to 0
        }
        result = liq_engine.calculate(inputs)
        assert result.confidence == "medium"

    # LI07 – confidence = low when net_lv ≤ 0
    def test_li07_confidence_low_negative_result(self, liq_engine):
        inputs = {
            "market_value":         5_000_000.0,
            "forced_sale_discount": 0.30,
            "auction_costs":        4_000_000.0,   # costs exceed gross proceeds
        }
        result = liq_engine.calculate(inputs)
        assert result.confidence == "low"

    # LI08 – engine_name = "liquidation"
    def test_li08_engine_name(self, liq_engine):
        assert liq_engine.name == "liquidation"

    # LI09 – version = "1.0.0"
    def test_li09_version(self, liq_engine):
        assert liq_engine.version == "1.0.0"

    # LI10 – value is Decimal when net_lv > 0
    def test_li10_value_is_decimal(self, liq_engine, liq_full_inputs):
        result = liq_engine.calculate(liq_full_inputs)
        assert isinstance(result.value, Decimal)

    # LI11 – audit trail = 3 steps
    def test_li11_audit_trail_length(self, liq_engine, liq_full_inputs):
        result = liq_engine.calculate(liq_full_inputs)
        assert len(result.audit_trail) == 3

    # LI12 – HIGH_FORCED_SALE_DISCOUNT warning (> 50%)
    def test_li12_high_discount_warning(self, liq_engine):
        result = liq_engine.calculate({
            "market_value":         5_000_000.0,
            "forced_sale_discount": 0.60,
        })
        codes = [i.code for i in result.issues]
        assert "HIGH_FORCED_SALE_DISCOUNT" in codes

    # LI13 – LOW_FORCED_SALE_DISCOUNT warning (< 10%)
    def test_li13_low_discount_warning(self, liq_engine):
        result = liq_engine.calculate({
            "market_value":         5_000_000.0,
            "forced_sale_discount": 0.05,
        })
        codes = [i.code for i in result.issues]
        assert "LOW_FORCED_SALE_DISCOUNT" in codes

    # LI14 – MISSING_AUCTION_COSTS warning when not supplied
    def test_li14_missing_auction_costs_warning(self, liq_engine):
        result = liq_engine.calculate({
            "market_value":         5_000_000.0,
            "forced_sale_discount": 0.25,
        })
        codes = [i.code for i in result.issues]
        assert "MISSING_AUCTION_COSTS" in codes

    # LI15 – MISSING_LEGAL_COSTS warning when not supplied
    def test_li15_missing_legal_costs_warning(self, liq_engine):
        result = liq_engine.calculate({
            "market_value":         5_000_000.0,
            "forced_sale_discount": 0.25,
        })
        codes = [i.code for i in result.issues]
        assert "MISSING_LEGAL_COSTS" in codes

    # LI16 – NEGATIVE_LIQUIDATION_VALUE warning + value = None
    def test_li16_negative_lv_value_none(self, liq_engine):
        inputs = {
            "market_value":         1_000_000.0,
            "forced_sale_discount": 0.25,
            "auction_costs":        900_000.0,   # gross = 750k, net = 750k - 900k = -150k
        }
        result = liq_engine.calculate(inputs)
        codes = [i.code for i in result.issues]
        assert "NEGATIVE_LIQUIDATION_VALUE" in codes
        assert result.value is None

    # LI17 – error: MISSING_MARKET_VALUE
    def test_li17_error_missing_market_value(self, liq_engine):
        result = liq_engine.calculate({"forced_sale_discount": 0.25})
        codes = [i.code for i in result.issues]
        assert "MISSING_MARKET_VALUE" in codes
        assert result.value is None

    # LI18 – error: INVALID_MARKET_VALUE (≤ 0)
    def test_li18_error_invalid_market_value(self, liq_engine):
        result = liq_engine.calculate({
            "market_value":         -1_000_000.0,
            "forced_sale_discount":  0.25,
        })
        codes = [i.code for i in result.issues]
        assert "INVALID_MARKET_VALUE" in codes

    # LI19 – error: MISSING_FORCED_SALE_DISCOUNT
    def test_li19_error_missing_discount(self, liq_engine):
        result = liq_engine.calculate({"market_value": 5_000_000.0})
        codes = [i.code for i in result.issues]
        assert "MISSING_FORCED_SALE_DISCOUNT" in codes
        assert result.value is None

    # LI20 – error: INVALID_FORCED_SALE_DISCOUNT (= 1.0)
    def test_li20_error_invalid_discount_one(self, liq_engine):
        result = liq_engine.calculate({
            "market_value":         5_000_000.0,
            "forced_sale_discount": 1.0,
        })
        codes = [i.code for i in result.issues]
        assert "INVALID_FORCED_SALE_DISCOUNT" in codes
        assert result.value is None
