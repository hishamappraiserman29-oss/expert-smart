"""
Tests for Phase 16.5 engines:
  - MarketRentalEngine (MR01–MR20) — core_engine/engines/market_rental_engine.py
  - IFRS13Engine       (IF01–IF20) — core_engine/engines/ifrs13_engine.py

All tests are pure-unit / deterministic — no server, no DB, no RAG.
"""

from decimal import Decimal

import pytest

from core_engine.engines.ifrs13_engine import IFRS13Engine
from core_engine.engines.market_rental_engine import MarketRentalEngine

# ══════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════

@pytest.fixture
def mr_engine():
    return MarketRentalEngine()


@pytest.fixture
def if_engine():
    return IFRS13Engine()


# ── Market Rental golden fixture ──────────────────────────────────────
# gla=500, rent=1200, gross, op_costs=200, rf=3, lt=24
# mrv = 500×1200 = 600_000
# net_rent = 500×(1200-200) = 500_000
# effective_rent = 500×1200×(24-3)/24 = 500×1200×0.875 = 525_000
@pytest.fixture
def mr_full_inputs():
    return {
        "gla":                    500.0,
        "rent_per_m2":           1200.0,
        "gross_or_net_lease":    "gross",
        "operating_costs_per_m2": 200.0,
        "rent_free_months":          3,
        "lease_term_months":        24,
    }


# ── IFRS 13 golden fixture (Level 2, small surplus) ──────────────────
# fv=4.2M, ca=4.0M, acc_dep=500k, level=2
# reval_amount = 200_000 (surplus)
# net_book_value = 4_000_000 - 500_000 = 3_500_000
# uplift_from_nbv = 4_200_000 - 3_500_000 = 700_000
# change_ratio = 200k/4M = 5% → no significant warning
@pytest.fixture
def if_full_inputs():
    return {
        "fair_value":               4_200_000.0,
        "carrying_amount":          4_000_000.0,
        "accumulated_depreciation":   500_000.0,
        "ifrs_level":               2,
        "asset_class":              "investment_property",
    }


# ══════════════════════════════════════════════════════════════════════
# MarketRentalEngine Tests
# ══════════════════════════════════════════════════════════════════════

class TestMarketRentalEngine:

    # MR01 – market_rental_value = gla × rent_per_m2 = 600_000
    def test_mr01_market_rental_value(self, mr_engine, mr_full_inputs):
        result = mr_engine.calculate(mr_full_inputs)
        assert float(result.value) == pytest.approx(600_000.0)

    # MR02 – effective_rent = gla × rent_pm2 × (lt-rf)/lt = 525_000
    def test_mr02_effective_rent(self, mr_engine, mr_full_inputs):
        result = mr_engine.calculate(mr_full_inputs)
        assert result.metadata["effective_rent"] == pytest.approx(525_000.0)

    # MR03 – gross lease: net_rent_to_landlord = gla × (rent - op_costs) = 500_000
    def test_mr03_gross_lease_net_rent(self, mr_engine, mr_full_inputs):
        result = mr_engine.calculate(mr_full_inputs)
        assert result.metadata["net_rent_to_landlord"] == pytest.approx(500_000.0)

    # MR04 – net lease: net_rent_to_landlord = gla × rent_per_m2 (no deduction)
    def test_mr04_net_lease_no_deduction(self, mr_engine):
        inputs = {
            "gla":                500.0,
            "rent_per_m2":       1200.0,
            "gross_or_net_lease": "net",
            "operating_costs_per_m2": 200.0,   # supplied but not deducted for net
        }
        result = mr_engine.calculate(inputs)
        assert result.metadata["net_rent_to_landlord"] == pytest.approx(600_000.0)

    # MR05 – confidence = high (op_costs + lease_term + rent_free all supplied)
    def test_mr05_confidence_high(self, mr_engine, mr_full_inputs):
        result = mr_engine.calculate(mr_full_inputs)
        assert result.confidence == "high"

    # MR06 – confidence = medium (only lease_term supplied, no op_costs or rent_free)
    def test_mr06_confidence_medium(self, mr_engine):
        inputs = {
            "gla":                500.0,
            "rent_per_m2":       1200.0,
            "gross_or_net_lease": "net",
            "lease_term_months":   24,
        }
        result = mr_engine.calculate(inputs)
        assert result.confidence == "medium"

    # MR07 – confidence = low (only required inputs, no optional)
    def test_mr07_confidence_low(self, mr_engine):
        inputs = {
            "gla":                500.0,
            "rent_per_m2":       1200.0,
            "gross_or_net_lease": "net",
        }
        result = mr_engine.calculate(inputs)
        assert result.confidence == "low"

    # MR08 – engine_name = "market_rental"
    def test_mr08_engine_name(self, mr_engine):
        assert mr_engine.name == "market_rental"

    # MR09 – version = "1.0.0"
    def test_mr09_version(self, mr_engine):
        assert mr_engine.version == "1.0.0"

    # MR10 – value is Decimal
    def test_mr10_value_is_decimal(self, mr_engine, mr_full_inputs):
        result = mr_engine.calculate(mr_full_inputs)
        assert isinstance(result.value, Decimal)

    # MR11 – audit trail = 3 steps when lease_term supplied
    def test_mr11_audit_trail_three_steps(self, mr_engine, mr_full_inputs):
        result = mr_engine.calculate(mr_full_inputs)
        assert len(result.audit_trail) == 3

    # MR12 – metadata contains all expected keys
    def test_mr12_metadata_keys(self, mr_engine, mr_full_inputs):
        result = mr_engine.calculate(mr_full_inputs)
        for key in (
            "gla", "rent_per_m2", "lease_type", "market_rental_value",
            "net_rent_per_m2", "net_rent_to_landlord", "operating_costs_per_m2",
            "rent_free_months", "lease_term_months",
            "effective_rent", "effective_rent_per_m2",
        ):
            assert key in result.metadata, f"Missing metadata key: {key}"

    # MR13 – MISSING_OPERATING_COSTS warning for gross lease without op costs
    def test_mr13_warning_missing_op_costs_gross(self, mr_engine):
        inputs = {
            "gla":                500.0,
            "rent_per_m2":       1200.0,
            "gross_or_net_lease": "gross",
            # no operating_costs_per_m2
        }
        result = mr_engine.calculate(inputs)
        codes = [i.code for i in result.issues]
        assert "MISSING_OPERATING_COSTS" in codes

    # MR14 – MISSING_LEASE_TERM warning when not supplied
    def test_mr14_warning_missing_lease_term(self, mr_engine):
        inputs = {
            "gla":                500.0,
            "rent_per_m2":       1200.0,
            "gross_or_net_lease": "net",
        }
        result = mr_engine.calculate(inputs)
        codes = [i.code for i in result.issues]
        assert "MISSING_LEASE_TERM" in codes

    # MR15 – HIGH_RENT_FREE_RATIO warning when rf > 20% of term
    # rf=4, lt=12 → 33% > 20% → warning
    def test_mr15_warning_high_rent_free_ratio(self, mr_engine):
        inputs = {
            "gla":                500.0,
            "rent_per_m2":       1200.0,
            "gross_or_net_lease": "net",
            "lease_term_months":  12,
            "rent_free_months":    4,
        }
        result = mr_engine.calculate(inputs)
        codes = [i.code for i in result.issues]
        assert "HIGH_RENT_FREE_RATIO" in codes

    # MR16 – error: MISSING_GLA
    def test_mr16_error_missing_gla(self, mr_engine):
        result = mr_engine.calculate({
            "rent_per_m2":        1200.0,
            "gross_or_net_lease": "net",
        })
        codes = [i.code for i in result.issues]
        assert "MISSING_GLA" in codes
        assert result.value is None

    # MR17 – error: MISSING_RENT_PER_M2
    def test_mr17_error_missing_rent(self, mr_engine):
        result = mr_engine.calculate({
            "gla":                500.0,
            "gross_or_net_lease": "net",
        })
        codes = [i.code for i in result.issues]
        assert "MISSING_RENT_PER_M2" in codes
        assert result.value is None

    # MR18 – error: INVALID_LEASE_TYPE
    def test_mr18_error_invalid_lease_type(self, mr_engine):
        result = mr_engine.calculate({
            "gla":                500.0,
            "rent_per_m2":       1200.0,
            "gross_or_net_lease": "hybrid",
        })
        codes = [i.code for i in result.issues]
        assert "INVALID_LEASE_TYPE" in codes
        assert result.value is None

    # MR19 – error: INVALID_RENT_FREE_MONTHS (≥ lease_term)
    def test_mr19_error_rent_free_exceeds_term(self, mr_engine):
        result = mr_engine.calculate({
            "gla":                500.0,
            "rent_per_m2":       1200.0,
            "gross_or_net_lease": "net",
            "lease_term_months":   12,
            "rent_free_months":    12,   # equal → invalid
        })
        codes = [i.code for i in result.issues]
        assert "INVALID_RENT_FREE_MONTHS" in codes
        assert result.value is None

    # MR20 – effective_rent is None when lease_term not supplied
    def test_mr20_effective_rent_none_without_lease_term(self, mr_engine):
        inputs = {
            "gla":                500.0,
            "rent_per_m2":       1200.0,
            "gross_or_net_lease": "net",
            "rent_free_months":    3,     # rf supplied but no lt → can't compute
        }
        result = mr_engine.calculate(inputs)
        # Engine still runs (MISSING_LEASE_TERM is warning, not error)
        assert result.value is not None
        assert result.metadata["effective_rent"] is None


# ══════════════════════════════════════════════════════════════════════
# IFRS13Engine Tests
# ══════════════════════════════════════════════════════════════════════

class TestIFRS13Engine:

    # IF01 – value = fair_value (engine returns the fair value as its output)
    def test_if01_value_equals_fair_value(self, if_engine, if_full_inputs):
        result = if_engine.calculate(if_full_inputs)
        assert float(result.value) == pytest.approx(4_200_000.0)

    # IF02 – revaluation_surplus = fair_value - carrying_amount = 200_000
    def test_if02_revaluation_surplus(self, if_engine, if_full_inputs):
        result = if_engine.calculate(if_full_inputs)
        assert result.metadata["revaluation_surplus"] == pytest.approx(200_000.0)
        assert result.metadata["revaluation_deficit"] == pytest.approx(0.0)

    # IF03 – revaluation_deficit when carrying_amount > fair_value
    def test_if03_revaluation_deficit(self, if_engine):
        inputs = {
            "fair_value":      3_000_000.0,
            "carrying_amount": 4_000_000.0,
            "ifrs_level":      2,
        }
        result = if_engine.calculate(inputs)
        assert result.metadata["revaluation_deficit"] == pytest.approx(1_000_000.0)
        assert result.metadata["revaluation_surplus"] == pytest.approx(0.0)

    # IF04 – confidence = high for Level 1
    def test_if04_confidence_high_level1(self, if_engine):
        inputs = {
            "fair_value":      5_000_000.0,
            "carrying_amount": 4_000_000.0,
            "ifrs_level":      1,
        }
        result = if_engine.calculate(inputs)
        assert result.confidence == "high"

    # IF05 – confidence = medium for Level 2
    def test_if05_confidence_medium_level2(self, if_engine, if_full_inputs):
        result = if_engine.calculate(if_full_inputs)
        assert result.confidence == "medium"

    # IF06 – confidence = low for Level 3
    def test_if06_confidence_low_level3(self, if_engine):
        inputs = {
            "fair_value":      5_000_000.0,
            "carrying_amount": 4_000_000.0,
            "ifrs_level":      3,
        }
        result = if_engine.calculate(inputs)
        assert result.confidence == "low"

    # IF07 – engine_name = "ifrs13"
    def test_if07_engine_name(self, if_engine):
        assert if_engine.name == "ifrs13"

    # IF08 – version = "1.0.0"
    def test_if08_version(self, if_engine):
        assert if_engine.version == "1.0.0"

    # IF09 – value is Decimal
    def test_if09_value_is_decimal(self, if_engine, if_full_inputs):
        result = if_engine.calculate(if_full_inputs)
        assert isinstance(result.value, Decimal)

    # IF10 – audit trail = 4 steps when accumulated_depreciation supplied
    def test_if10_audit_trail_four_steps(self, if_engine, if_full_inputs):
        result = if_engine.calculate(if_full_inputs)
        assert len(result.audit_trail) == 4

    # IF11 – metadata contains all expected keys
    def test_if11_metadata_keys(self, if_engine, if_full_inputs):
        result = if_engine.calculate(if_full_inputs)
        for key in (
            "fair_value", "carrying_amount", "accumulated_depreciation",
            "ifrs_level", "level_description", "input_level_validation",
            "revaluation_amount", "revaluation_surplus", "revaluation_deficit",
            "net_book_value", "uplift_from_nbv",
            "disclosure_notes", "asset_class",
        ):
            assert key in result.metadata, f"Missing metadata key: {key}"

    # IF12 – LEVEL_3_EXTENSIVE_DISCLOSURE warning for Level 3
    def test_if12_level3_extensive_disclosure_warning(self, if_engine):
        inputs = {
            "fair_value":      5_000_000.0,
            "carrying_amount": 4_000_000.0,
            "ifrs_level":      3,
        }
        result = if_engine.calculate(inputs)
        codes = [i.code for i in result.issues]
        assert "LEVEL_3_EXTENSIVE_DISCLOSURE" in codes

    # IF13 – SIGNIFICANT_REVALUATION_SURPLUS warning (> 20% of carrying)
    # surplus = 1_200_000 / 4_000_000 = 30% > 20%
    def test_if13_significant_surplus_warning(self, if_engine):
        inputs = {
            "fair_value":      5_200_000.0,
            "carrying_amount": 4_000_000.0,
            "ifrs_level":      2,
        }
        result = if_engine.calculate(inputs)
        codes = [i.code for i in result.issues]
        assert "SIGNIFICANT_REVALUATION_SURPLUS" in codes

    # IF14 – SIGNIFICANT_REVALUATION_DEFICIT warning (> 20% of carrying)
    # deficit = 1_200_000 / 4_000_000 = 30% > 20%
    def test_if14_significant_deficit_warning(self, if_engine):
        inputs = {
            "fair_value":      2_800_000.0,
            "carrying_amount": 4_000_000.0,
            "ifrs_level":      2,
        }
        result = if_engine.calculate(inputs)
        codes = [i.code for i in result.issues]
        assert "SIGNIFICANT_REVALUATION_DEFICIT" in codes

    # IF15 – net_book_value = carrying - accumulated_dep = 3_500_000
    def test_if15_net_book_value(self, if_engine, if_full_inputs):
        result = if_engine.calculate(if_full_inputs)
        assert result.metadata["net_book_value"] == pytest.approx(3_500_000.0)
        assert result.metadata["uplift_from_nbv"] == pytest.approx(700_000.0)

    # IF16 – MISSING_ACCUMULATED_DEPRECIATION warning when not supplied
    def test_if16_missing_accumulated_dep_warning(self, if_engine):
        inputs = {
            "fair_value":      5_000_000.0,
            "carrying_amount": 4_000_000.0,
            "ifrs_level":      2,
        }
        result = if_engine.calculate(inputs)
        codes = [i.code for i in result.issues]
        assert "MISSING_ACCUMULATED_DEPRECIATION" in codes
        # Engine still calculates
        assert result.value is not None
        assert result.metadata["net_book_value"] is None

    # IF17 – error: MISSING_FAIR_VALUE
    def test_if17_error_missing_fair_value(self, if_engine):
        result = if_engine.calculate({
            "carrying_amount": 4_000_000.0,
            "ifrs_level":      2,
        })
        codes = [i.code for i in result.issues]
        assert "MISSING_FAIR_VALUE" in codes
        assert result.value is None

    # IF18 – error: MISSING_CARRYING_AMOUNT
    def test_if18_error_missing_carrying_amount(self, if_engine):
        result = if_engine.calculate({
            "fair_value":  5_000_000.0,
            "ifrs_level":  2,
        })
        codes = [i.code for i in result.issues]
        assert "MISSING_CARRYING_AMOUNT" in codes
        assert result.value is None

    # IF19 – error: INVALID_IFRS_LEVEL (= 0)
    def test_if19_error_invalid_ifrs_level(self, if_engine):
        result = if_engine.calculate({
            "fair_value":      5_000_000.0,
            "carrying_amount": 4_000_000.0,
            "ifrs_level":      0,
        })
        codes = [i.code for i in result.issues]
        assert "INVALID_IFRS_LEVEL" in codes
        assert result.value is None

    # IF20 – error: MISSING_IFRS_LEVEL
    def test_if20_error_missing_ifrs_level(self, if_engine):
        result = if_engine.calculate({
            "fair_value":      5_000_000.0,
            "carrying_amount": 4_000_000.0,
        })
        codes = [i.code for i in result.issues]
        assert "MISSING_IFRS_LEVEL" in codes
        assert result.value is None
