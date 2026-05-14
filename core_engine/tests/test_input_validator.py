"""
test_input_validator.py — Wave 7b.2 (14 tests)

Tests:
  valid DTO → is_valid
  each ERROR rule triggered individually
  each WARNING rule triggered
  cost/income None → skipped
  comparables loop
  profile gate (discount_rate only in professional_template)
  PROFILE_UNKNOWN → ERROR
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_CORE))
os.chdir(str(_CORE))

from reports.validation.input_validator import validate_inputs
from reports.validation.result import Severity


# ── Valid full DTO ────────────────────────────────────────────────────────────

_GOOD = {
    "appraiser": {"name": "د. محمد", "license": "EG-2026-001", "date": "2026-05-15"},
    "property_info": {"address": "القاهرة", "type": "سكني", "area": 320},
    "comparables": [
        {"ref": "ع1", "sale_price": 2_400_000, "area": 310,
         "price_per_sqm": 7_741, "adjustment_pct": "+3%", "adjusted_value": 2_472_000},
    ],
    "cost_approach": {
        "rcn": 1_800_000, "depreciation": 270_000,
        "land_value": 900_000, "cost_value_indication": 2_430_000,
    },
    "income_approach": {
        "gross_income": 240_000, "vacancy_pct": "8%",
        "opex": 60_000, "noi": 160_800, "cap_rate": "6.5%",
        "income_value_indication": 2_473_846,
    },
    "reconciliation": {
        "weights": {"sales": "50%", "cost": "20%", "income": "30%"},
        "indications": {"sales": 2_500_000, "cost": 2_430_000, "income": 2_473_846},
        "final_value": 2_478_153,
    },
}


class TestInputValidatorValid:
    def test_good_dto_is_valid(self):
        result = validate_inputs(_GOOD)
        assert result.is_valid, [i.code for i in result.errors]

    def test_good_dto_no_errors(self):
        result = validate_inputs(_GOOD)
        assert len(result.errors) == 0


class TestInputValidatorErrors:
    def test_unknown_profile(self):
        result = validate_inputs(_GOOD, profile_key="bad")
        assert any(i.code == "PROFILE_UNKNOWN" for i in result.errors)

    def test_appraiser_name_missing(self):
        data = {**_GOOD, "appraiser": {"license": "X", "date": "2026"}}
        result = validate_inputs(data)
        assert any(i.code == "APPRAISER_NAME_MISSING" for i in result.errors)

    def test_property_area_missing(self):
        data = {**_GOOD, "property_info": {"type": "سكني"}}
        result = validate_inputs(data)
        assert any(i.code == "PROPERTY_AREA_MISSING" for i in result.errors)

    def test_property_area_zero(self):
        data = {**_GOOD, "property_info": {"area": 0, "type": "سكني"}}
        result = validate_inputs(data)
        assert any(i.code == "PROPERTY_AREA_POSITIVE" for i in result.errors)

    def test_cost_rcn_zero(self):
        cost = {**_GOOD["cost_approach"], "rcn": 0}
        result = validate_inputs({**_GOOD, "cost_approach": cost})
        assert any(i.code == "COST_RCN_POSITIVE" for i in result.errors)

    def test_cost_land_zero(self):
        cost = {**_GOOD["cost_approach"], "land_value": -1}
        result = validate_inputs({**_GOOD, "cost_approach": cost})
        assert any(i.code == "COST_LAND_VALUE_POSITIVE" for i in result.errors)

    def test_income_gross_zero(self):
        inc = {**_GOOD["income_approach"], "gross_income": 0}
        result = validate_inputs({**_GOOD, "income_approach": inc})
        assert any(i.code == "INCOME_GROSS_POSITIVE" for i in result.errors)

    def test_comparable_sale_price_zero(self):
        comps = [{"ref": "ع1", "sale_price": 0, "area": 100}]
        result = validate_inputs({**_GOOD, "comparables": comps})
        assert any(i.code == "COMPARABLE_SALE_PRICE_POSITIVE" for i in result.errors)

    def test_comparable_area_negative(self):
        comps = [{"ref": "ع1", "sale_price": 100_000, "area": -5}]
        result = validate_inputs({**_GOOD, "comparables": comps})
        assert any(i.code == "COMPARABLE_AREA_POSITIVE" for i in result.errors)

    def test_weights_negative(self):
        recon = {**_GOOD["reconciliation"],
                 "weights": {"sales": "-10%", "cost": "60%", "income": "50%"}}
        result = validate_inputs({**_GOOD, "reconciliation": recon})
        assert any(i.code == "WEIGHTS_NEGATIVE" for i in result.errors)


class TestInputValidatorWarnings:
    def test_appraiser_license_missing_warning(self):
        data = {**_GOOD, "appraiser": {"name": "محمد", "date": "2026"}}
        result = validate_inputs(data)
        assert any(i.code == "APPRAISER_LICENSE_MISSING" for i in result.warnings)
        assert result.is_valid  # WARNING does not block

    def test_cap_rate_too_high_warning(self):
        inc = {**_GOOD["income_approach"], "cap_rate": "35%"}
        result = validate_inputs({**_GOOD, "income_approach": inc})
        assert any(i.code == "INCOME_CAP_RATE_RANGE" for i in result.warnings)
        assert result.is_valid

    def test_depreciation_exceeds_rcn_warning(self):
        cost = {**_GOOD["cost_approach"], "depreciation": 2_000_000}
        result = validate_inputs({**_GOOD, "cost_approach": cost})
        assert any(i.code == "COST_DEPRECIATION_RANGE" for i in result.warnings)


class TestInputValidatorProfileGates:
    def test_discount_rate_only_checked_for_professional(self):
        inc = {**_GOOD["income_approach"], "discount_rate": "50%"}
        # legacy → no INCOME_DISCOUNT_RATE_RANGE warning
        r_legacy = validate_inputs({**_GOOD, "income_approach": inc},
                                   profile_key="legacy")
        assert not any(i.code == "INCOME_DISCOUNT_RATE_RANGE" for i in r_legacy.issues)
        # professional_template → warning triggered
        r_prof = validate_inputs({**_GOOD, "income_approach": inc},
                                 profile_key="professional_template")
        assert any(i.code == "INCOME_DISCOUNT_RATE_RANGE" for i in r_prof.warnings)

    def test_cost_none_skips_cost_rules(self):
        data = {**_GOOD, "cost_approach": None}
        result = validate_inputs(data)
        assert not any("COST_" in i.code for i in result.issues)

    def test_income_none_skips_income_rules(self):
        data = {**_GOOD, "income_approach": None}
        result = validate_inputs(data)
        assert not any("INCOME_" in i.code for i in result.issues)

    def test_empty_comparables_no_crash(self):
        result = validate_inputs({**_GOOD, "comparables": []})
        assert result.is_valid
