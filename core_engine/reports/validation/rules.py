"""
rules.py — Composable validation rule primitives for EXPERT_SMART.

Each function inspects a value and returns a ValidationIssue if the rule
fails, or None if the value is acceptable.  All primitives are pure
functions with no side effects.

Percentage parsing:
  Many report fields arrive as "15%" strings.  _parse_numeric() normalises
  "15%" → 15.0, 6.5 → 6.5, None → None, unparseable → None.
  Callers that need a true percentage (not a decimal fraction) should
  pass the parsed value to check_range with min_val/max_val expressed
  as plain numbers (e.g. check_range for cap_rate: min_val=1.0, max_val=20.0).
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Optional

from .result import Severity, ValidationIssue


# ── Internal helpers ──────────────────────────────────────────────────────────

def _parse_numeric(value: Any) -> Optional[float]:
    """Coerce value to float, stripping a trailing '%' if present.

    Returns None for None, empty strings, or values that cannot be parsed.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if math.isnan(value) or math.isinf(value):
            return None
        return float(value)
    if isinstance(value, str):
        s = value.strip().rstrip("%")
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _get_nested(data: Mapping[str, Any], field: str) -> Any:
    """Resolve a simple (non-dotted) field from a flat mapping."""
    return data.get(field)


def _make(field: str, severity: Severity, code: str,
          message_ar: str, message_en: str) -> ValidationIssue:
    return ValidationIssue(
        field=field, severity=severity, code=code,
        message_ar=message_ar, message_en=message_en,
    )


# ── Rule primitives ───────────────────────────────────────────────────────────

def require(
    data: Mapping[str, Any],
    field: str,
    *,
    code: str,
    message_ar: str,
    message_en: str,
    severity: Severity = Severity.ERROR,
) -> Optional[ValidationIssue]:
    """Return an issue when *field* is missing or empty/None in *data*."""
    value = data.get(field)
    if value is None or value == "":
        return _make(field, severity, code, message_ar, message_en)
    return None


def check_type(
    data: Mapping[str, Any],
    field: str,
    expected_type: type | tuple,
    *,
    code: str,
    message_ar: str,
    message_en: str,
    severity: Severity = Severity.WARNING,
) -> Optional[ValidationIssue]:
    """Return an issue when the value of *field* is not an instance of *expected_type*."""
    value = data.get(field)
    if value is None:
        return None  # absence is handled by require()
    if not isinstance(value, expected_type):
        return _make(field, severity, code, message_ar, message_en)
    return None


def check_positive(
    data: Mapping[str, Any],
    field: str,
    *,
    code: str,
    message_ar: str,
    message_en: str,
    severity: Severity = Severity.ERROR,
) -> Optional[ValidationIssue]:
    """Return an issue when the numeric value of *field* is ≤ 0.

    Accepts numeric values and '%'-strings.  Missing/None values are
    silently skipped (use require() separately to catch absence).
    """
    value = data.get(field)
    if value is None:
        return None
    parsed = _parse_numeric(value)
    if parsed is None or parsed <= 0:
        return _make(field, severity, code, message_ar, message_en)
    return None


def check_nonneg(
    data: Mapping[str, Any],
    field: str,
    *,
    code: str,
    message_ar: str,
    message_en: str,
    severity: Severity = Severity.WARNING,
) -> Optional[ValidationIssue]:
    """Return an issue when the numeric value of *field* is < 0."""
    value = data.get(field)
    if value is None:
        return None
    parsed = _parse_numeric(value)
    if parsed is None or parsed < 0:
        return _make(field, severity, code, message_ar, message_en)
    return None


def check_range(
    data: Mapping[str, Any],
    field: str,
    *,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
    code: str,
    message_ar: str,
    message_en: str,
    severity: Severity = Severity.WARNING,
) -> Optional[ValidationIssue]:
    """Return an issue when the numeric value is outside [min_val, max_val].

    Either bound may be None (unbounded on that side).
    Missing/None values are silently skipped.
    Handles '%'-strings via _parse_numeric.
    """
    value = data.get(field)
    if value is None:
        return None
    parsed = _parse_numeric(value)
    if parsed is None:
        return None  # non-numeric strings are not range-checked
    if min_val is not None and parsed < min_val:
        return _make(field, severity, code, message_ar, message_en)
    if max_val is not None and parsed > max_val:
        return _make(field, severity, code, message_ar, message_en)
    return None


def check_not_nan_inf(
    data: Mapping[str, Any],
    field: str,
    *,
    code: str,
    message_ar: str,
    message_en: str,
    severity: Severity = Severity.ERROR,
) -> Optional[ValidationIssue]:
    """Return an issue when the value of *field* is NaN or ±Infinity."""
    value = data.get(field)
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if math.isnan(value) or math.isinf(value):
            return _make(field, severity, code, message_ar, message_en)
    return None


def check_lte(
    data: Mapping[str, Any],
    field_a: str,
    field_b: str,
    *,
    code: str,
    message_ar: str,
    message_en: str,
    severity: Severity = Severity.WARNING,
) -> Optional[ValidationIssue]:
    """Return an issue when numeric value of *field_a* > *field_b*.

    E.g. check_lte(cost, 'depreciation', 'rcn') — depreciation must be ≤ RCN.
    Both fields must be numeric and present; otherwise the check is skipped.
    """
    a = _parse_numeric(data.get(field_a))
    b = _parse_numeric(data.get(field_b))
    if a is None or b is None:
        return None
    if a > b:
        return _make(field_a, severity, code, message_ar, message_en)
    return None


def check_weights_sum(
    weights_dict: Mapping[str, Any],
    *,
    field: str = "reconciliation.weights",
    expected: float = 100.0,
    tolerance: float = 0.5,
    code: str,
    message_ar: str,
    message_en: str,
    severity: Severity = Severity.ERROR,
) -> Optional[ValidationIssue]:
    """Return an issue when the sum of *weights_dict* values ≠ *expected* ± *tolerance*.

    Handles '%'-strings ("50%" → 50.0).

    Special case: if the parsed sum is close to 1.0 (decimal fractions
    rather than percentages), returns an INFO issue instead of the caller's
    severity to avoid a false ERROR while still flagging the inconsistency.
    """
    if not weights_dict:
        return None

    parsed = [_parse_numeric(v) for v in weights_dict.values()]
    numeric = [p for p in parsed if p is not None]
    if not numeric:
        return None

    total = sum(numeric)

    # Decimal-fraction shortcut (e.g. 0.5 + 0.2 + 0.3 = 1.0)
    if abs(total - 1.0) <= (tolerance / 100.0):
        return _make(
            field, Severity.INFO,
            code + "_DECIMAL",
            "أوزان المناهج تبدو كسور عشرية — يُفضَّل تمريرها كنسب مئوية (مثل '50%' أو 50.0)",
            "Weights appear to be decimal fractions; prefer percentage format (e.g. '50%' or 50.0)",
        )

    if abs(total - expected) > tolerance:
        return _make(field, severity, code, message_ar, message_en)

    return None
