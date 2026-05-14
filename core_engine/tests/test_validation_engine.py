"""
test_validation_engine.py — Wave 7b.3 (12 tests)

Tests:
  validate_report merges input + output issues
  good DTO → is_valid
  bad DTO → both input and output errors present
  unknown profile → ERROR
  bilingual — every issue has non-empty message_ar + message_en
  __init__ exports accessible
  empty data → not is_valid (market_value required)
  all three profiles work without crash
  ValidationResult.merge idempotent
  is_valid / errors / warnings consistency
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_CORE))
os.chdir(str(_CORE))

# ── __init__ exports ──────────────────────────────────────────────────────────

from reports.validation import (
    Severity,
    ValidationIssue,
    ValidationResult,
    validate_inputs,
    validate_outputs,
    validate_report,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

_GOOD = {
    "appraiser": {"name": "د. محمد", "license": "EG-2026-001", "date": "2026-05-15"},
    "property_info": {"address": "القاهرة", "type": "سكني", "area": 320},
    "valuation_results": {
        "market_value": 2_500_000,
        "price_per_sqm": 7_812,
    },
    "cost_approach": {
        "rcn": 1_800_000, "depreciation": 270_000,
        "land_value": 900_000, "cost_value_indication": 2_430_000,
    },
    "income_approach": {
        "gross_income": 240_000, "vacancy_pct": "8%",
        "opex": 60_000, "cap_rate": "6.5%",
        "income_value_indication": 2_473_846,
    },
    "reconciliation": {
        "weights": {"sales": "50%", "cost": "20%", "income": "30%"},
        "final_value": 2_478_153,
    },
}

_BAD = {
    "appraiser": {},                          # APPRAISER_NAME_MISSING (ERROR)
    "property_info": {"area": -5},            # PROPERTY_AREA_POSITIVE (ERROR)
    "valuation_results": {},                  # MARKET_VALUE_MISSING (ERROR)
    "reconciliation": {
        "weights": {"sales": "60%", "cost": "20%", "income": "30%"},  # WEIGHTS_SUM_MISMATCH
        "final_value": 0,                     # RECONCILIATION_FINAL_POSITIVE (ERROR)
    },
}


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestValidateReport:
    def test_good_dto_is_valid(self):
        assert validate_report(_GOOD).is_valid

    def test_empty_data_not_valid(self):
        result = validate_report({})
        assert not result.is_valid

    def test_bad_dto_not_valid(self):
        assert not validate_report(_BAD).is_valid

    def test_bad_dto_has_input_and_output_errors(self):
        result = validate_report(_BAD)
        codes = {i.code for i in result.issues}
        # Input error
        assert "APPRAISER_NAME_MISSING" in codes
        # Output error
        assert "MARKET_VALUE_MISSING" in codes

    def test_unknown_profile_error(self):
        result = validate_report(_GOOD, profile_key="bad_profile")
        assert any(i.code == "PROFILE_UNKNOWN" for i in result.errors)
        assert not result.is_valid

    def test_all_profiles_no_crash(self):
        for profile in ("legacy", "detailed", "professional_template"):
            result = validate_report(_GOOD, profile_key=profile)
            assert isinstance(result, ValidationResult), f"profile={profile}"

    def test_bilingual_all_issues(self):
        result = validate_report(_BAD)
        for issue in result.issues:
            assert issue.message_ar, f"Empty message_ar for code={issue.code}"
            assert issue.message_en, f"Empty message_en for code={issue.code}"

    def test_merge_is_superset_of_both(self):
        input_r  = validate_inputs(_BAD)
        output_r = validate_outputs(_BAD)
        merged   = validate_report(_BAD)
        assert len(merged) >= len(input_r) + len(output_r)

    def test_merge_idempotent_with_empty(self):
        r = validate_report(_GOOD)
        merged = r.merge(ValidationResult.empty())
        assert len(merged) == len(r)

    def test_errors_warnings_consistency(self):
        result = validate_report(_BAD)
        all_codes = {i.code for i in result.issues}
        error_codes   = {i.code for i in result.errors}
        warning_codes = {i.code for i in result.warnings}
        info_codes    = {i.code for i in result.infos}
        assert error_codes | warning_codes | info_codes == all_codes

    def test_init_exports_accessible(self):
        assert callable(validate_report)
        assert callable(validate_inputs)
        assert callable(validate_outputs)
        assert issubclass(ValidationResult, object)
        assert issubclass(ValidationIssue, object)
        assert Severity.ERROR.value == "error"

    def test_warning_only_is_valid(self):
        # DTO with only warnings (license missing, type missing)
        data = {
            "appraiser": {"name": "محمد", "date": "2026"},  # no license → WARNING
            "property_info": {"area": 100},                  # no type → WARNING
            "valuation_results": {"market_value": 1_000_000},
        }
        result = validate_report(data)
        assert result.is_valid  # warnings do not block
        assert len(result.warnings) > 0
