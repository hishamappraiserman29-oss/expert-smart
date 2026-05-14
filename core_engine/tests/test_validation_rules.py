"""
test_validation_rules.py — Wave 7b.1 (16 tests)

Tests:
  _parse_numeric (3): percentage strings, plain floats, None/bad
  require (2): missing/empty → issue, present → None
  check_positive (2): zero/negative → issue, positive → None
  check_nonneg (2): negative → issue, zero/positive → None
  check_range (2): out-of-range → issue, in-range → None
  check_not_nan_inf (2): NaN/Inf → issue, normal → None
  check_lte (1): a > b → issue, a ≤ b → None
  check_weights_sum (2): mismatch → issue, decimal-fraction → INFO
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

_CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_CORE))
os.chdir(str(_CORE))

from reports.validation.result import Severity, ValidationIssue
from reports.validation.rules import (
    _parse_numeric,
    check_lte,
    check_nonneg,
    check_not_nan_inf,
    check_positive,
    check_range,
    check_weights_sum,
    require,
)

# ── Shared kwargs helpers ─────────────────────────────────────────────────────

_KW = dict(code="X", message_ar="خطأ", message_en="error")


# ── _parse_numeric ────────────────────────────────────────────────────────────

class TestParseNumeric:
    def test_percentage_string(self):
        assert _parse_numeric("15%") == 15.0
        assert _parse_numeric("6.5%") == 6.5
        assert _parse_numeric("  50%  ") == 50.0

    def test_plain_float(self):
        assert _parse_numeric(6.5) == 6.5
        assert _parse_numeric(0) == 0.0
        assert _parse_numeric(100) == 100.0

    def test_none_and_bad(self):
        assert _parse_numeric(None) is None
        assert _parse_numeric("") is None
        assert _parse_numeric("abc") is None
        assert _parse_numeric(math.nan) is None
        assert _parse_numeric(math.inf) is None


# ── require ───────────────────────────────────────────────────────────────────

class TestRequire:
    def test_missing_field_returns_issue(self):
        issue = require({}, "area", **_KW)
        assert isinstance(issue, ValidationIssue)
        assert issue.severity is Severity.ERROR

    def test_none_value_returns_issue(self):
        issue = require({"area": None}, "area", **_KW)
        assert issue is not None

    def test_empty_string_returns_issue(self):
        issue = require({"area": ""}, "area", **_KW)
        assert issue is not None

    def test_present_value_returns_none(self):
        assert require({"area": 100}, "area", **_KW) is None

    def test_custom_severity(self):
        issue = require({}, "x", severity=Severity.WARNING, **_KW)
        assert issue.severity is Severity.WARNING


# ── check_positive ────────────────────────────────────────────────────────────

class TestCheckPositive:
    def test_zero_returns_issue(self):
        assert check_positive({"v": 0}, "v", **_KW) is not None

    def test_negative_returns_issue(self):
        assert check_positive({"v": -5}, "v", **_KW) is not None

    def test_positive_returns_none(self):
        assert check_positive({"v": 1_000}, "v", **_KW) is None

    def test_percentage_string_positive(self):
        assert check_positive({"v": "5%"}, "v", **_KW) is None

    def test_missing_skipped(self):
        assert check_positive({}, "v", **_KW) is None


# ── check_nonneg ──────────────────────────────────────────────────────────────

class TestCheckNonneg:
    def test_negative_returns_issue(self):
        assert check_nonneg({"v": -1}, "v", **_KW) is not None

    def test_zero_returns_none(self):
        assert check_nonneg({"v": 0}, "v", **_KW) is None

    def test_positive_returns_none(self):
        assert check_nonneg({"v": 10}, "v", **_KW) is None


# ── check_range ───────────────────────────────────────────────────────────────

class TestCheckRange:
    def test_below_min_returns_issue(self):
        issue = check_range({"cap": "0.5%"}, "cap", min_val=1.0, max_val=20.0, **_KW)
        assert issue is not None

    def test_above_max_returns_issue(self):
        issue = check_range({"cap": 25.0}, "cap", min_val=1.0, max_val=20.0, **_KW)
        assert issue is not None

    def test_in_range_returns_none(self):
        assert check_range({"cap": "6.5%"}, "cap", min_val=1.0, max_val=20.0, **_KW) is None

    def test_missing_skipped(self):
        assert check_range({}, "cap", min_val=1.0, max_val=20.0, **_KW) is None

    def test_non_numeric_string_skipped(self):
        assert check_range({"cap": "n/a"}, "cap", min_val=1.0, max_val=20.0, **_KW) is None


# ── check_not_nan_inf ─────────────────────────────────────────────────────────

class TestCheckNotNanInf:
    def test_nan_returns_issue(self):
        assert check_not_nan_inf({"v": math.nan}, "v", **_KW) is not None

    def test_inf_returns_issue(self):
        assert check_not_nan_inf({"v": math.inf}, "v", **_KW) is not None

    def test_neg_inf_returns_issue(self):
        assert check_not_nan_inf({"v": -math.inf}, "v", **_KW) is not None

    def test_normal_returns_none(self):
        assert check_not_nan_inf({"v": 2_500_000}, "v", **_KW) is None

    def test_missing_skipped(self):
        assert check_not_nan_inf({}, "v", **_KW) is None


# ── check_lte ─────────────────────────────────────────────────────────────────

class TestCheckLte:
    def test_a_greater_than_b_returns_issue(self):
        data = {"depreciation": 500_000, "rcn": 300_000}
        issue = check_lte(data, "depreciation", "rcn", **_KW)
        assert issue is not None
        assert issue.field == "depreciation"

    def test_a_equal_b_returns_none(self):
        data = {"depreciation": 300_000, "rcn": 300_000}
        assert check_lte(data, "depreciation", "rcn", **_KW) is None

    def test_a_less_than_b_returns_none(self):
        data = {"depreciation": 270_000, "rcn": 1_800_000}
        assert check_lte(data, "depreciation", "rcn", **_KW) is None

    def test_missing_field_skipped(self):
        assert check_lte({"rcn": 1_000}, "depreciation", "rcn", **_KW) is None


# ── check_weights_sum ─────────────────────────────────────────────────────────

class TestCheckWeightsSum:
    def test_correct_sum_returns_none(self):
        w = {"sales": "50%", "cost": "20%", "income": "30%"}
        assert check_weights_sum(w, **_KW) is None

    def test_mismatch_returns_error(self):
        w = {"sales": "60%", "cost": "20%", "income": "30%"}
        issue = check_weights_sum(w, **_KW)
        assert issue is not None
        assert issue.severity is Severity.ERROR

    def test_decimal_fractions_returns_info(self):
        w = {"sales": 0.5, "cost": 0.2, "income": 0.3}
        issue = check_weights_sum(w, **_KW)
        assert issue is not None
        assert issue.severity is Severity.INFO

    def test_empty_dict_skipped(self):
        assert check_weights_sum({}, **_KW) is None

    def test_custom_tolerance(self):
        w = {"sales": "50.3%", "cost": "20%", "income": "30%"}
        # sum = 100.3 — within tolerance=1.0
        assert check_weights_sum(w, tolerance=1.0, **_KW) is None
        # but outside tolerance=0.1
        assert check_weights_sum(w, tolerance=0.1, **_KW) is not None
