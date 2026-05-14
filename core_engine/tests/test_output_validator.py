"""
test_output_validator.py — Wave 7b.2 (12 tests)

Tests:
  valid full DTO → is_valid
  market_value missing/zero/NaN/Inf → ERRORs
  price_per_sqm zero → WARNING (not blocking)
  cost/income indications positive
  reconciliation final_value + weights_sum
  decimal weights → INFO (not blocking)
  cost/income/reconciliation None → skipped
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

_CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_CORE))
os.chdir(str(_CORE))

from reports.validation.output_validator import validate_outputs
from reports.validation.result import Severity


_GOOD = {
    "valuation_results": {
        "market_value": 2_500_000,
        "price_per_sqm": 7_812,
        "confidence": "عالية",
        "value_words": "مليونان وخمسمائة ألف جنيه",
    },
    "cost_approach": {"cost_value_indication": 2_430_000},
    "income_approach": {"income_value_indication": 2_473_846},
    "reconciliation": {
        "weights": {"sales": "50%", "cost": "20%", "income": "30%"},
        "final_value": 2_478_153,
    },
}


class TestOutputValidatorValid:
    def test_good_dto_is_valid(self):
        assert validate_outputs(_GOOD).is_valid

    def test_good_dto_no_errors(self):
        assert len(validate_outputs(_GOOD).errors) == 0


class TestOutputValidatorMarketValue:
    def test_market_value_missing(self):
        data = {**_GOOD, "valuation_results": {}}
        result = validate_outputs(data)
        assert any(i.code == "MARKET_VALUE_MISSING" for i in result.errors)
        assert not result.is_valid

    def test_market_value_zero(self):
        vr = {**_GOOD["valuation_results"], "market_value": 0}
        result = validate_outputs({**_GOOD, "valuation_results": vr})
        assert any(i.code == "MARKET_VALUE_POSITIVE" for i in result.errors)

    def test_market_value_nan(self):
        vr = {**_GOOD["valuation_results"], "market_value": math.nan}
        result = validate_outputs({**_GOOD, "valuation_results": vr})
        assert any(i.code == "MARKET_VALUE_NAN_INF" for i in result.errors)

    def test_market_value_inf(self):
        vr = {**_GOOD["valuation_results"], "market_value": math.inf}
        result = validate_outputs({**_GOOD, "valuation_results": vr})
        assert any(i.code == "MARKET_VALUE_NAN_INF" for i in result.errors)


class TestOutputValidatorWarnings:
    def test_price_per_sqm_zero_is_warning_not_error(self):
        vr = {**_GOOD["valuation_results"], "price_per_sqm": 0}
        result = validate_outputs({**_GOOD, "valuation_results": vr})
        assert any(i.code == "PRICE_PER_SQM_POSITIVE" for i in result.warnings)
        assert result.is_valid  # WARNING does not block

    def test_cost_indication_zero_warning(self):
        cost = {"cost_value_indication": 0}
        result = validate_outputs({**_GOOD, "cost_approach": cost})
        assert any(i.code == "COST_VALUE_POSITIVE" for i in result.warnings)
        assert result.is_valid

    def test_income_indication_zero_warning(self):
        inc = {"income_value_indication": -1}
        result = validate_outputs({**_GOOD, "income_approach": inc})
        assert any(i.code == "INCOME_VALUE_POSITIVE" for i in result.warnings)


class TestOutputValidatorReconciliation:
    def test_final_value_zero_error(self):
        recon = {**_GOOD["reconciliation"], "final_value": 0}
        result = validate_outputs({**_GOOD, "reconciliation": recon})
        assert any(i.code == "RECONCILIATION_FINAL_POSITIVE" for i in result.errors)

    def test_weights_sum_mismatch_error(self):
        recon = {**_GOOD["reconciliation"],
                 "weights": {"sales": "60%", "cost": "20%", "income": "30%"}}
        result = validate_outputs({**_GOOD, "reconciliation": recon})
        assert any(i.code == "WEIGHTS_SUM_MISMATCH" for i in result.errors)

    def test_decimal_weights_info_not_blocking(self):
        recon = {**_GOOD["reconciliation"],
                 "weights": {"sales": 0.5, "cost": 0.2, "income": 0.3}}
        result = validate_outputs({**_GOOD, "reconciliation": recon})
        assert any(i.severity is Severity.INFO for i in result.issues)
        assert result.is_valid  # INFO does not block

    def test_none_sections_skipped(self):
        data = {
            "valuation_results": _GOOD["valuation_results"],
            "cost_approach": None,
            "income_approach": None,
            "reconciliation": None,
        }
        result = validate_outputs(data)
        assert result.is_valid
        assert not any("COST_" in i.code or "INCOME_" in i.code
                        or "RECON" in i.code for i in result.issues)
