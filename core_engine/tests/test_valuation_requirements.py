"""
Tests for the Single-Property Valuation Requirements Matrix (Phase 8A).

Covers:
  - SUPPORTED_ASSET_TYPES / SUPPORTED_PURPOSES constants
  - REQUIREMENTS_MATRIX completeness
  - get_requirements() — valid combinations and error cases
  - list_supported_asset_types() / list_supported_purposes()
  - FieldSpec properties (required / valid_values)
  - validate_result() — valid result, unknown type/purpose, missing required field,
    invalid enum value, land cost-not-required invariant

Tests: RM01 – RM20
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

# ── path setup ────────────────────────────────────────────────────────────────
_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(str(_CORE))

from adapters.valuation_requirements import (  # noqa: E402
    REQUIREMENTS_MATRIX,
    SUPPORTED_ASSET_TYPES,
    SUPPORTED_PURPOSES,
    SUPPORTED_PURPOSES_BY_ASSET_TYPE,
    FieldSpec,
    RequirementsViolation,
    ValuationRequirements,
    get_requirements,
    list_supported_asset_types,
    list_supported_purposes,
    validate_result,
)


# ── Minimal stub for AssetValuationResult ─────────────────────────────────────

@dataclass
class _Result:
    """Lightweight stand-in — mirrors the fields validate_result() reads."""
    asset_type:      str
    primary_purpose: str
    metadata:        dict[str, Any] = field(default_factory=dict)


def _residential(overrides: dict | None = None) -> _Result:
    md = {
        "comparable": 2_500_000.0,
        "cost":       2_600_000.0,
        "income":     2_450_000.0,
    }
    if overrides:
        md.update(overrides)
    return _Result("residential", "market_value", md)


def _commercial(overrides: dict | None = None) -> _Result:
    md = {
        "comparable": 8_500_000.0,
        "cost":       9_200_000.0,
        "income":     8_800_000.0,
    }
    if overrides:
        md.update(overrides)
    return _Result("commercial", "market_value", md)


def _land(overrides: dict | None = None) -> _Result:
    md = {
        "comparable": 3_000_000.0,
        "income":     2_800_000.0,
    }
    if overrides:
        md.update(overrides)
    return _Result("land", "market_value", md)


# ── RM01 — Supported asset types ─────────────────────────────────────────────

def test_RM01_supported_asset_types_contains_all_three():
    assert "residential" in SUPPORTED_ASSET_TYPES
    assert "commercial"  in SUPPORTED_ASSET_TYPES
    assert "land"        in SUPPORTED_ASSET_TYPES
    assert len(SUPPORTED_ASSET_TYPES) == 3


# ── RM02 — Each asset type has at least one purpose ───────────────────────────

def test_RM02_each_asset_type_has_at_least_one_purpose():
    for asset_type in SUPPORTED_ASSET_TYPES:
        purposes = SUPPORTED_PURPOSES_BY_ASSET_TYPE.get(asset_type, set())
        assert len(purposes) >= 1, f"{asset_type} has no supported purposes"


# ── RM03 — Matrix covers all declared combinations ────────────────────────────

def test_RM03_matrix_covers_all_declared_combinations():
    for asset_type, purposes in SUPPORTED_PURPOSES_BY_ASSET_TYPE.items():
        for purpose in purposes:
            key = (asset_type, purpose)
            assert key in REQUIREMENTS_MATRIX, (
                f"REQUIREMENTS_MATRIX is missing ({asset_type!r}, {purpose!r})"
            )


# ── RM04 — get_requirements returns ValuationRequirements ─────────────────────

@pytest.mark.parametrize("asset_type,purpose", [
    ("residential", "market_value"),
    ("residential", "mortgage_lending"),
    ("commercial",  "market_value"),
    ("commercial",  "investment_analysis"),
    ("land",        "market_value"),
    ("land",        "investment_analysis"),
])
def test_RM04_get_requirements_valid_combination(asset_type, purpose):
    reqs = get_requirements(asset_type, purpose)
    assert isinstance(reqs, ValuationRequirements)
    assert reqs.asset_type == asset_type
    assert reqs.purpose    == purpose


# ── RM05 — get_requirements raises ValueError for unknown asset_type ──────────

def test_RM05_get_requirements_unknown_asset_type_raises():
    with pytest.raises(ValueError, match="asset_type"):
        get_requirements("industrial_park", "market_value")


# ── RM06 — get_requirements raises ValueError for unsupported purpose ─────────

def test_RM06_get_requirements_unsupported_purpose_raises():
    with pytest.raises(ValueError, match="purpose"):
        get_requirements("residential", "nonexistent_purpose")


# ── RM07 — list_supported_asset_types is sorted and complete ──────────────────

def test_RM07_list_supported_asset_types():
    result = list_supported_asset_types()
    assert result == sorted(SUPPORTED_ASSET_TYPES)
    assert "residential" in result
    assert "commercial"  in result
    assert "land"        in result


# ── RM08 — list_supported_purposes returns sorted purposes per type ───────────

def test_RM08_list_supported_purposes_residential():
    purposes = list_supported_purposes("residential")
    assert sorted(purposes) == purposes
    assert "market_value"    in purposes
    assert "mortgage_lending" in purposes


def test_RM09_list_supported_purposes_land():
    purposes = list_supported_purposes("land")
    assert "market_value" in purposes
    assert "investment_analysis" in purposes


def test_RM10_list_supported_purposes_unknown_raises():
    with pytest.raises(ValueError, match="Unknown asset_type"):
        list_supported_purposes("warehouse_district")


# ── RM11 — required_fields / optional_fields properties ──────────────────────

def test_RM11_required_fields_are_subset_of_metadata_fields():
    reqs = get_requirements("residential", "market_value")
    all_names = {f.name for f in reqs.metadata_fields}
    for spec in reqs.required_fields:
        assert spec.name in all_names
        assert spec.required is True
    for spec in reqs.optional_fields:
        assert spec.name in all_names
        assert spec.required is False


# ── RM12 — Land does NOT require cost field ───────────────────────────────────

def test_RM12_land_cost_field_not_required():
    reqs = get_requirements("land", "market_value")
    required_names = {f.name for f in reqs.required_fields}
    assert "cost" not in required_names, (
        "Land cost weight = 0; the cost field must not be required in land requirements"
    )


# ── RM13 — Residential requires cost field ───────────────────────────────────

def test_RM13_residential_cost_field_required():
    reqs = get_requirements("residential", "market_value")
    required_names = {f.name for f in reqs.required_fields}
    assert "cost" in required_names


# ── RM14 — Commercial requires cost field ────────────────────────────────────

def test_RM14_commercial_cost_field_required():
    reqs = get_requirements("commercial", "market_value")
    required_names = {f.name for f in reqs.required_fields}
    assert "cost" in required_names


# ── RM15 — validate_result: valid residential returns no violations ───────────

def test_RM15_validate_result_valid_residential_no_violations():
    violations = validate_result(_residential())
    errors = [v for v in violations if v.severity == "error"]
    assert errors == [], f"Unexpected errors: {errors}"


# ── RM16 — validate_result: valid commercial returns no violations ────────────

def test_RM16_validate_result_valid_commercial_no_violations():
    violations = validate_result(_commercial())
    errors = [v for v in violations if v.severity == "error"]
    assert errors == [], f"Unexpected errors: {errors}"


# ── RM17 — validate_result: valid land returns no violations ──────────────────

def test_RM17_validate_result_valid_land_no_violations():
    violations = validate_result(_land())
    errors = [v for v in violations if v.severity == "error"]
    assert errors == [], f"Unexpected errors: {errors}"


# ── RM18 — validate_result: unknown asset_type → error violation ──────────────

def test_RM18_validate_result_unknown_asset_type():
    result = _Result("farmhouse", "market_value", {})
    violations = validate_result(result)
    assert any(v.field == "asset_type" and v.severity == "error" for v in violations)


# ── RM19 — validate_result: unsupported purpose → error violation ─────────────

def test_RM19_validate_result_unsupported_purpose():
    result = _Result("residential", "habu_analysis", {"comparable": 1.0, "cost": 1.0, "income": 1.0})
    violations = validate_result(result)
    assert any(v.field == "primary_purpose" and v.severity == "error" for v in violations)


# ── RM20 — validate_result: missing required field → error violation ──────────

def test_RM20_validate_result_missing_required_field():
    # residential requires "comparable" — omit it
    result = _Result("residential", "market_value", {"cost": 1.0, "income": 1.0})
    violations = validate_result(result)
    missing = [v for v in violations if "comparable" in v.field and v.severity == "error"]
    assert missing, "Expected an error violation for missing 'comparable' field"


# ── RM21 — validate_result: invalid enum value → warning violation ────────────

def test_RM21_validate_result_invalid_enum_value_warning():
    result = _residential({"ownership_type": "partnership_unknown"})
    violations = validate_result(result)
    enum_warnings = [
        v for v in violations
        if "ownership_type" in v.field and v.severity == "warning"
    ]
    assert enum_warnings, (
        "Expected a warning violation for an invalid ownership_type enum value"
    )


# ── RM22 — FieldSpec valid_values populated for enum fields ──────────────────

def test_RM22_enum_fieldspecs_have_valid_values():
    reqs = get_requirements("residential", "market_value")
    enum_fields = [f for f in reqs.metadata_fields if f.valid_values]
    assert len(enum_fields) >= 1, "Expected at least one enum FieldSpec for residential"
    for spec in enum_fields:
        assert len(spec.valid_values) > 0
