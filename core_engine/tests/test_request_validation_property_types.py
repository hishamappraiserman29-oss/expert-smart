"""
test_request_validation_property_types.py — Wave 2 property-type contract tests

PT01  Registry delegation — allowed_values must equal sorted(SUPPORTED_ASSET_TYPES)
PT02  land accepted
PT03  industrial accepted (backward-compatibility gate — INDUSTRIAL_POLICY=KEEP)
PT04  hotel accepted (5-type registry, NOT 3-type as legacy 43dffaf intended)
PT05a residential accepted
PT05b commercial accepted
PT06  unknown value rejected with clear error message
PT07  missing property_type rejected (required-field contract)
PT08  case sensitivity — 'Land' is rejected (no normalization in current code)
PT09  no-industrial-retirement guard
"""

from __future__ import annotations

import sys
from pathlib import Path

_TESTS = Path(__file__).parent.resolve()   # .../core_engine/tests
_CORE  = _TESTS.parent.resolve()           # .../core_engine
_ROOT  = _CORE.parent.resolve()            # .../ExpertSmart_Unified

for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest  # noqa: E402

from api.request_validation import request_validator  # noqa: E402
from adapters.valuation_requirements import SUPPORTED_ASSET_TYPES  # noqa: E402


# ── helpers ────────────────────────────────────────────────────────────────────

def _search(property_type: str):
    return request_validator.validate_request("search", {"property_type": property_type})


def _search_empty():
    return request_validator.validate_request("search", {})


# ── PT01 — Registry delegation ─────────────────────────────────────────────────

def test_PT01_registry_delegation():
    schema_values = request_validator.schemas["search"]["property_type"]["allowed_values"]
    assert schema_values == sorted(SUPPORTED_ASSET_TYPES), (
        "Search schema allowed_values must equal sorted(SUPPORTED_ASSET_TYPES) — "
        "no hardcoded list permitted"
    )


# ── PT02 — land accepted ───────────────────────────────────────────────────────

def test_PT02_land_accepted():
    ok, errors = _search("land")
    assert ok is True, f"Expected 'land' to be accepted; errors: {errors}"
    assert errors == []


# ── PT03 — industrial accepted (backward-compatibility gate) ───────────────────

def test_PT03_industrial_accepted():
    ok, errors = _search("industrial")
    assert ok is True, (
        f"Expected 'industrial' to be accepted (INDUSTRIAL_POLICY=KEEP); errors: {errors}"
    )
    assert errors == []


# ── PT04 — hotel accepted (5-type registry) ────────────────────────────────────

def test_PT04_hotel_accepted():
    ok, errors = _search("hotel")
    assert ok is True, (
        f"Expected 'hotel' to be accepted (present in SUPPORTED_ASSET_TYPES); errors: {errors}"
    )
    assert errors == []


# ── PT05 — existing canonical types remain accepted ────────────────────────────

@pytest.mark.parametrize("ptype", ["residential", "commercial"])
def test_PT05_canonical_types_accepted(ptype: str):
    ok, errors = _search(ptype)
    assert ok is True, f"Expected '{ptype}' to be accepted; errors: {errors}"
    assert errors == []


# ── PT06 — unknown value rejected ─────────────────────────────────────────────

def test_PT06_unknown_value_rejected():
    ok, errors = _search("unknown_asset")
    assert ok is False, "Expected 'unknown_asset' to be rejected"
    assert len(errors) == 1
    assert "property_type" in errors[0]
    assert "must be one of" in errors[0]


# ── PT07 — missing property_type rejected ─────────────────────────────────────

def test_PT07_missing_property_type_rejected():
    ok, errors = _search_empty()
    assert ok is False, "Expected missing property_type to be rejected"
    assert any(
        "Missing required field" in e and "property_type" in e
        for e in errors
    )


# ── PT08 — case sensitivity (no normalization — documents current contract) ───

def test_PT08_case_sensitivity_land_rejected():
    ok, errors = _search("Land")
    assert ok is False, (
        "Expected 'Land' (title-case) to be rejected — no case normalization "
        "is implemented; this test documents the current contract"
    )


# ── PT09 — no-industrial-retirement guard ─────────────────────────────────────

def test_PT09_no_industrial_retirement_guard():
    assert "industrial" in SUPPORTED_ASSET_TYPES, (
        "SUPPORTED_ASSET_TYPES must contain 'industrial' — retirement is blocked "
        "by Phase 9.1 expansion and active CI gates REQ19/REQ21"
    )
    schema_values = request_validator.schemas["search"]["property_type"]["allowed_values"]
    assert "industrial" in schema_values, (
        "Search schema allowed_values must not exclude 'industrial' — "
        "backward-compatibility contract"
    )
