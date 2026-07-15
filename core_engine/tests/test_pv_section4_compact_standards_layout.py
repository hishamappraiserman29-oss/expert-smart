"""
Phase CS4 — Backend tests for Section 4.1 Compact Horizontal Standard Chips.
Tests: CS4_BE_01 through CS4_BE_15.

advisory_only=True | not_real_training=True | no_commit=True
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core_engine.applied_standards_compact_layout_context import (
    applied_standards_compact_layout_context as _CTX,
)


# ── CS4_BE_01: Context object exists ─────────────────────────────────────────
def test_CS4_BE_01_context_object_exists():
    """CS4_BE_01: applied_standards_compact_layout_context exists and is a dict."""
    assert isinstance(_CTX, dict)


# ── CS4_BE_02: compact_horizontal_layout_enabled = True ──────────────────────
def test_CS4_BE_02_compact_horizontal_layout_enabled():
    """CS4_BE_02: compact_horizontal_layout_enabled must be True."""
    assert _CTX.get("compact_horizontal_layout_enabled") is True


# ── CS4_BE_03: standards_display_mode = horizontal_chips ─────────────────────
def test_CS4_BE_03_standards_display_mode_horizontal_chips():
    """CS4_BE_03: standards_display_mode must be 'horizontal_chips'."""
    assert _CTX.get("standards_display_mode") == "horizontal_chips"


# ── CS4_BE_04: wraps_to_one_or_two_rows = True ───────────────────────────────
def test_CS4_BE_04_wraps_to_one_or_two_rows():
    """CS4_BE_04: wraps_to_one_or_two_rows must be True."""
    assert _CTX.get("wraps_to_one_or_two_rows") is True


# ── CS4_BE_05: All 8 standard keys preserved ─────────────────────────────────
def test_CS4_BE_05_all_standard_keys_preserved():
    """CS4_BE_05: All 8 standard keys must be present in standard_keys list."""
    required = {
        "uspap", "ivs_2025", "rics_red_book_2025", "ifrs_13",
        "gcc_standards", "fra_egypt", "custom_local_standard", "basel_iii",
    }
    keys = set(_CTX.get("standard_keys", []))
    assert required.issubset(keys), f"Missing keys: {required - keys}"


# ── CS4_BE_06: deleted_standards = [] ────────────────────────────────────────
def test_CS4_BE_06_deleted_standards_empty():
    """CS4_BE_06: deleted_standards must be an empty list."""
    assert _CTX.get("deleted_standards") == []


# ── CS4_BE_07: backend_keys_preserved = True ─────────────────────────────────
def test_CS4_BE_07_backend_keys_preserved():
    """CS4_BE_07: backend_keys_preserved must be True."""
    assert _CTX.get("backend_keys_preserved") is True


# ── CS4_BE_08: advisory_notice_preserved = True ──────────────────────────────
def test_CS4_BE_08_advisory_notice_preserved():
    """CS4_BE_08: advisory_notice_preserved must be True."""
    assert _CTX.get("advisory_notice_preserved") is True


# ── CS4_BE_09: duplicate_advisory_notice_removed = True ──────────────────────
def test_CS4_BE_09_duplicate_advisory_notice_removed():
    """CS4_BE_09: duplicate_advisory_notice_removed must be True."""
    assert _CTX.get("duplicate_advisory_notice_removed") is True


# ── CS4_BE_10: Basel III NOT a pure valuation standard ───────────────────────
def test_CS4_BE_10_basel_iii_not_pure_valuation_standard():
    """CS4_BE_10: Basel III must be classified as risk/banking, NOT pure valuation standard."""
    assert _CTX.get("basel_iii_is_pure_valuation_standard") is False
    cats = _CTX.get("standard_classifications", {})
    assert cats.get("basel_iii") == "risk_banking_collateral", (
        f"Basel III classification must be 'risk_banking_collateral', got {cats.get('basel_iii')}"
    )


# ── CS4_BE_11: IFRS 13 is financial_reporting_accounting context ──────────────
def test_CS4_BE_11_ifrs_13_financial_reporting_context():
    """CS4_BE_11: IFRS 13 must be classified as financial_reporting_accounting."""
    cats = _CTX.get("standard_classifications", {})
    assert cats.get("ifrs_13") == "financial_reporting_accounting", (
        f"IFRS 13 classification must be 'financial_reporting_accounting', got {cats.get('ifrs_13')}"
    )
    assert _CTX.get("ifrs_13_is_financial_reporting_context") is True


# ── CS4_BE_12: Professional standards correctly classified ────────────────────
def test_CS4_BE_12_professional_standards_classification():
    """CS4_BE_12: USPAP, IVS 2025, RICS Red Book 2025 all classified as professional_valuation_standard."""
    cats = _CTX.get("standard_classifications", {})
    for key in ("uspap", "ivs_2025", "rics_red_book_2025"):
        assert cats.get(key) == "professional_valuation_standard", (
            f"{key} must be 'professional_valuation_standard', got {cats.get(key)}"
        )


# ── CS4_BE_13: Section 2 and 3 unaffected ────────────────────────────────────
def test_CS4_BE_13_section_2_3_unaffected():
    """CS4_BE_13: Section 2 requirement tables and Section 3 purpose/scope are unaffected."""
    assert _CTX.get("section_2_requirement_tables_unaffected") is True
    assert _CTX.get("section_3_purpose_scope_unaffected") is True


# ── CS4_BE_14: advisory_only and not_real_training flags intact ───────────────
def test_CS4_BE_14_advisory_flags_intact():
    """CS4_BE_14: advisory_only=True and not_real_training=True must be set."""
    assert _CTX.get("advisory_only") is True
    assert _CTX.get("not_real_training") is True


# ── CS4_BE_15: No internal paths in context ──────────────────────────────────
def test_CS4_BE_15_no_internal_paths():
    """CS4_BE_15: Context must not contain internal filesystem paths."""
    import json
    ctx_str = json.dumps(_CTX, ensure_ascii=False)
    forbidden = ["C:\\Users\\", "/home/", "/Users/", "Desktop\\", "AppData\\"]
    for pattern in forbidden:
        assert pattern not in ctx_str, f"Internal path found in context: {pattern}"
