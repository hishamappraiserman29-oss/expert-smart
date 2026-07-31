"""test_pv_currency_context.py — Currency-context unit tests for pv_three_tier_pdf_builder.

Verifies that value_in_words uses currency from the report context dict, not a
hardcoded default. Required by STEP 5 of CANONICAL_SAUDI_GEOGRAPHY_FINAL_SCOPE_REVIEW.

Three permanent cases:
  1. SAR context: currency='ريال سعودي' → value_in_words ends with 'ريال سعودي'
  2. Non-SAR context: currency='م.ج' → value_in_words ends with 'م.ج'
  3. Missing currency: no currency key → value_in_words ends with 'جنيه مصري' (legacy fallback)
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).parent.parent.parent
CORE = ROOT / "core_engine"
sys.path.insert(0, str(CORE / "reports"))


def _make_minimal(extra: dict | None = None) -> dict:
    base = {
        "final_value": 3_200_000,
        "property_address": "حي النخيل، شمال الرياض",
        "area_sqm": 150,
        "property_type": "شقة سكنية",
    }
    if extra:
        base.update(extra)
    return base


def _html(data: dict) -> str:
    from pv_three_tier_pdf_builder import build_traditional_html
    return build_traditional_html(data)


def test_saudi_riyal_currency_in_value_in_words() -> None:
    """SAR context: currency='ريال سعودي' must appear in value_in_words HTML output."""
    html = _html(_make_minimal({"currency": "ريال سعودي"}))
    assert "ريال سعودي" in html, (
        "SAR context: 'ريال سعودي' not found in HTML — "
        "currency label must be sourced from d.get('currency'), not hardcoded"
    )
    assert "جنيه مصري" not in html, (
        "SAR context: 'جنيه مصري' must not appear when currency='ريال سعودي'"
    )


def test_non_sar_currency_in_value_in_words() -> None:
    """Non-SAR context: currency='م.ج' (EGP abbreviated) must appear in HTML output."""
    html = _html(_make_minimal({"currency": "م.ج"}))
    assert "م.ج" in html, (
        "Non-SAR context: 'م.ج' not found in HTML — "
        "currency label must be sourced from d.get('currency')"
    )


def test_missing_currency_falls_back_to_legacy_default() -> None:
    """No currency key → value_in_words uses legacy fallback 'جنيه مصري'.

    This preserves backward compatibility for existing callers that do not
    supply a currency field. The fallback must not be SAR-specific.
    """
    data = _make_minimal()
    assert "currency" not in data, "Precondition: no currency key in data"
    html = _html(data)
    assert "جنيه مصري" in html, (
        "Missing currency: legacy fallback 'جنيه مصري' not found in HTML — "
        "d.get('currency', 'جنيه مصري') must be the default"
    )


def test_currency_label_override_takes_priority_over_currency() -> None:
    """currency_label field takes priority over currency field (explicit display override)."""
    html = _html(_make_minimal({
        "currency": "ريال سعودي",
        "currency_label": "SAR",
    }))
    assert "SAR" in html, (
        "currency_label override: 'SAR' not found in HTML — "
        "d.get('currency_label') must take priority over d.get('currency')"
    )
