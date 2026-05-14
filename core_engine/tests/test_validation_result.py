"""
test_validation_result.py — Wave 7b.1 (12 tests)

Tests:
  Severity enum (2): values, identity
  ValidationIssue (2): frozen, bilingual non-empty
  ValidationResult (8): empty, is_valid, filters, merge, __bool__, __len__,
                        from_iterable, error blocks is_valid
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_CORE))
os.chdir(str(_CORE))

import pytest

from reports.validation.result import Severity, ValidationIssue, ValidationResult


# ── Helpers ───────────────────────────────────────────────────────────────────

def _issue(severity=Severity.ERROR, code="TEST_CODE",
           field="test.field", ar="رسالة", en="message"):
    return ValidationIssue(
        field=field, severity=severity, code=code,
        message_ar=ar, message_en=en,
    )


# ── Severity ──────────────────────────────────────────────────────────────────

class TestSeverity:
    def test_values(self):
        assert Severity.ERROR.value   == "error"
        assert Severity.WARNING.value == "warning"
        assert Severity.INFO.value    == "info"

    def test_identity(self):
        assert Severity.ERROR is not Severity.WARNING
        assert Severity.WARNING is not Severity.INFO


# ── ValidationIssue ───────────────────────────────────────────────────────────

class TestValidationIssue:
    def test_frozen(self):
        issue = _issue()
        with pytest.raises((AttributeError, TypeError)):
            issue.code = "CHANGED"  # type: ignore[misc]

    def test_bilingual_non_empty(self):
        issue = _issue(ar="نص عربي", en="English text")
        assert issue.message_ar
        assert issue.message_en


# ── ValidationResult ──────────────────────────────────────────────────────────

class TestValidationResult:
    def test_empty_is_valid(self):
        r = ValidationResult.empty()
        assert r.is_valid
        assert len(r) == 0

    def test_error_blocks_is_valid(self):
        r = ValidationResult(issues=(_issue(Severity.ERROR),))
        assert not r.is_valid

    def test_warning_does_not_block_is_valid(self):
        r = ValidationResult(issues=(_issue(Severity.WARNING),))
        assert r.is_valid

    def test_info_does_not_block_is_valid(self):
        r = ValidationResult(issues=(_issue(Severity.INFO),))
        assert r.is_valid

    def test_filters(self):
        err  = _issue(Severity.ERROR,   code="E")
        warn = _issue(Severity.WARNING, code="W")
        info = _issue(Severity.INFO,    code="I")
        r = ValidationResult(issues=(err, warn, info))
        assert r.errors   == (err,)
        assert r.warnings == (warn,)
        assert r.infos    == (info,)

    def test_merge(self):
        r1 = ValidationResult(issues=(_issue(Severity.ERROR,   code="A"),))
        r2 = ValidationResult(issues=(_issue(Severity.WARNING, code="B"),))
        merged = r1.merge(r2)
        assert len(merged) == 2
        assert merged.errors[0].code   == "A"
        assert merged.warnings[0].code == "B"

    def test_merge_multiple(self):
        r1 = ValidationResult(issues=(_issue(code="X"),))
        r2 = ValidationResult(issues=(_issue(code="Y"),))
        r3 = ValidationResult(issues=(_issue(code="Z"),))
        merged = r1.merge(r2, r3)
        assert len(merged) == 3

    def test_merge_preserves_order(self):
        codes = ["A", "B", "C"]
        results = [ValidationResult(issues=(_issue(code=c),)) for c in codes]
        merged = results[0].merge(*results[1:])
        assert [i.code for i in merged.issues] == codes

    def test_bool_alias(self):
        assert bool(ValidationResult.empty()) is True
        assert bool(ValidationResult(issues=(_issue(Severity.ERROR),))) is False

    def test_len(self):
        r = ValidationResult(issues=(_issue(), _issue(), _issue()))
        assert len(r) == 3

    def test_from_iterable_skips_none(self):
        issues = [_issue(code="A"), None, _issue(code="B"), None]
        r = ValidationResult.from_iterable(issues)
        assert len(r) == 2
        assert r.issues[0].code == "A"
        assert r.issues[1].code == "B"
