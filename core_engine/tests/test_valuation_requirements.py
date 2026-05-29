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


# ══ Phase 8H.2A — enriched registry tests (RM23 – RM37) ═════════════════════

# ── RM23 — FieldSpec carries Phase 8H.2A attributes ──────────────────────────

def test_RM23_fieldspec_has_8h2a_attributes():
    """FieldSpec exposes role / label_ar / group / ui_required with correct defaults."""
    spec = FieldSpec("test_field", False, "str", "A test field")
    assert hasattr(spec, "role"),        "FieldSpec must have 'role' attribute"
    assert hasattr(spec, "label_ar"),    "FieldSpec must have 'label_ar' attribute"
    assert hasattr(spec, "group"),       "FieldSpec must have 'group' attribute"
    assert hasattr(spec, "ui_required"), "FieldSpec must have 'ui_required' attribute"
    assert spec.role        == "user_input"
    assert spec.label_ar    == ""
    assert spec.group       == ""
    assert spec.ui_required is False


# ── RM24 — Engine-value fields carry role="engine_value" ─────────────────────

def test_RM24_engine_value_fields_marked_correctly():
    """comparable / cost / income / comparables have role='engine_value'."""
    reqs = get_requirements("residential", "market_value")
    field_map = {f.name: f for f in reqs.metadata_fields}

    for name in ("comparable", "cost", "income", "comparables"):
        assert name in field_map, f"Field '{name}' missing from residential"
        assert field_map[name].role == "engine_value", (
            f"Field '{name}' must have role='engine_value', got {field_map[name].role!r}"
        )

    # Land does not have cost but does have comparable / income / comparables
    land_reqs = get_requirements("land", "market_value")
    land_map = {f.name: f for f in land_reqs.metadata_fields}
    for name in ("comparable", "income", "comparables"):
        assert land_map[name].role == "engine_value", (
            f"Land field '{name}' must have role='engine_value'"
        )


# ── RM25 — Residential user-input form fields present ────────────────────────

def test_RM25_residential_user_input_fields_present():
    """Residential registry contains the Phase 8H.2A user-facing form fields."""
    reqs = get_requirements("residential", "market_value")
    names = {f.name for f in reqs.metadata_fields}

    expected = {
        "area_sqm", "floor_number", "rooms_count", "finishing_level",
        "building_age", "elevator_available", "parking_available",
        "legal_status", "view_quality", "services_available",
    }
    for field_name in expected:
        assert field_name in names, (
            f"Residential registry missing expected user-input field '{field_name}'"
        )


# ── RM26 — Residential document fields present with group="document" ─────────

def test_RM26_residential_document_fields_present():
    """Residential registry contains document checklist items with group='document'."""
    reqs = get_requirements("residential", "market_value")
    doc_fields = {f.name for f in reqs.metadata_fields if f.group == "document"}

    expected_docs = {
        "ownership_document",
        "site_croquis_or_location",
        "recent_photos",
        "nearby_sale_comparables_if_available",
    }
    for doc_name in expected_docs:
        assert doc_name in doc_fields, (
            f"Residential registry missing document field '{doc_name}'"
        )
    # All document fields must be bool type
    for spec in reqs.metadata_fields:
        if spec.group == "document":
            assert spec.field_type == "bool", (
                f"Document field '{spec.name}' must have field_type='bool', "
                f"got {spec.field_type!r}"
            )


# ── RM27 — Land user-input form fields present ───────────────────────────────

def test_RM27_land_user_input_fields_present():
    """Land registry contains the Phase 8H.2A user-facing form fields."""
    reqs = get_requirements("land", "market_value")
    names = {f.name for f in reqs.metadata_fields}

    expected = {
        "land_area_sqm", "frontage_m", "street_width_m",
        "zoning_type", "utilities_available", "buildability_status", "legal_status",
    }
    for field_name in expected:
        assert field_name in names, (
            f"Land registry missing expected user-input field '{field_name}'"
        )


# ── RM28 — Land document fields present with group="document" ────────────────

def test_RM28_land_document_fields_present():
    """Land registry contains document checklist items with group='document'."""
    reqs = get_requirements("land", "market_value")
    doc_fields = {f.name for f in reqs.metadata_fields if f.group == "document"}

    expected_docs = {
        "ownership_document",
        "site_plan_or_croquis",
        "area_statement",
        "coordinates_or_map_location",
        "site_photos",
        "building_regulations_if_available",
    }
    for doc_name in expected_docs:
        assert doc_name in doc_fields, (
            f"Land registry missing document field '{doc_name}'"
        )
    for spec in reqs.metadata_fields:
        if spec.group == "document":
            assert spec.field_type == "bool", (
                f"Document field '{spec.name}' must have field_type='bool'"
            )


# ── RM29 — finishing_level valid_values match spec ───────────────────────────

def test_RM29_finishing_level_valid_values():
    """finishing_level must have the four approved option codes."""
    reqs = get_requirements("residential", "market_value")
    spec = next(f for f in reqs.metadata_fields if f.name == "finishing_level")
    expected = {"shell", "semi_finished", "standard_finished", "luxury_finished"}
    assert set(spec.valid_values) == expected, (
        f"finishing_level valid_values mismatch. Got: {set(spec.valid_values)}"
    )


# ── RM30 — legal_status valid_values match spec (residential) ────────────────

def test_RM30_legal_status_valid_values_residential():
    """residential legal_status must have the four approved option codes."""
    reqs = get_requirements("residential", "market_value")
    spec = next(f for f in reqs.metadata_fields if f.name == "legal_status")
    expected = {"registered_title", "preliminary_contract", "allocation", "unknown"}
    assert set(spec.valid_values) == expected, (
        f"Residential legal_status valid_values mismatch. Got: {set(spec.valid_values)}"
    )


# ── RM31 — zoning_type valid_values match spec (land) ────────────────────────

def test_RM31_zoning_type_valid_values_land():
    """land zoning_type must have the six approved option codes."""
    reqs = get_requirements("land", "market_value")
    spec = next(f for f in reqs.metadata_fields if f.name == "zoning_type")
    expected = {
        "residential", "commercial", "administrative",
        "mixed_use", "agricultural", "unknown",
    }
    assert set(spec.valid_values) == expected, (
        f"Land zoning_type valid_values mismatch. Got: {set(spec.valid_values)}"
    )


# ── RM32 — All user_input fields have non-empty label_ar ─────────────────────

def test_RM32_user_input_fields_have_label_ar():
    """Every user_input field in residential and land has a non-empty label_ar."""
    for asset_type in ("residential", "land"):
        reqs = get_requirements(asset_type, "market_value")
        for spec in reqs.metadata_fields:
            if spec.role == "user_input":
                assert spec.label_ar, (
                    f"user_input field '{spec.name}' in {asset_type} "
                    f"has empty label_ar"
                )


# ── RM33 — ui_required fields in residential match the approved set ───────────

def test_RM33_residential_ui_required_fields():
    """Residential ui_required=True fields match the approved set."""
    reqs = get_requirements("residential", "market_value")
    ui_req = {f.name for f in reqs.metadata_fields if f.ui_required}
    expected = {"area_sqm", "floor_number", "rooms_count", "finishing_level", "legal_status"}
    assert expected.issubset(ui_req), (
        f"Some expected ui_required fields missing. "
        f"Expected subset: {expected}. Got: {ui_req}"
    )
    # Engine-value fields must NOT be ui_required
    for name in ("comparable", "cost", "income", "comparables"):
        assert name not in ui_req, (
            f"Engine-value field '{name}' must NOT be ui_required"
        )


# ── RM34 — ui_required fields in land match the approved set ─────────────────

def test_RM34_land_ui_required_fields():
    """Land ui_required=True fields match the approved set."""
    reqs = get_requirements("land", "market_value")
    ui_req = {f.name for f in reqs.metadata_fields if f.ui_required}
    expected = {
        "land_area_sqm", "frontage_m", "street_width_m",
        "zoning_type", "buildability_status", "legal_status",
    }
    assert expected.issubset(ui_req), (
        f"Some expected land ui_required fields missing. "
        f"Expected subset: {expected}. Got: {ui_req}"
    )
    for name in ("comparable", "income", "comparables"):
        assert name not in ui_req, (
            f"Engine-value field '{name}' must NOT be ui_required in land"
        )


# ── RM35 — Residential dynamic_fields (enum fields) include new fields ────────

def test_RM35_residential_enum_fields_include_new():
    """Residential metadata_fields with valid_values include the new enum fields."""
    reqs = get_requirements("residential", "market_value")
    enum_names = {f.name for f in reqs.metadata_fields if f.valid_values}
    for name in ("finishing_level", "legal_status", "elevator_available",
                 "parking_available", "view_quality"):
        assert name in enum_names, (
            f"Residential new enum field '{name}' not found in fields with valid_values"
        )


# ── RM36 — Land dynamic_fields (enum fields) include new fields ───────────────

def test_RM36_land_enum_fields_include_new():
    """Land metadata_fields with valid_values include the new enum fields."""
    reqs = get_requirements("land", "market_value")
    enum_names = {f.name for f in reqs.metadata_fields if f.valid_values}
    for name in ("zoning_type", "buildability_status", "legal_status", "utilities_available"):
        assert name in enum_names, (
            f"Land new enum field '{name}' not found in fields with valid_values"
        )


# ── RM37 — validate_result backward-compatible with pre-8H.2A fixtures ────────

def test_RM37_validate_result_backward_compatible():
    """Existing fixtures (engine-value fields only) produce zero error violations.

    This confirms that the new required=False / ui_required=True fields do NOT
    break validate_result() for valuation results produced before Phase 8H.2A.
    """
    # Residential: only the three engine-value fields present (legacy fixture)
    res_result = _residential()   # provides comparable / cost / income only
    violations = validate_result(res_result)
    errors = [v for v in violations if v.severity == "error"]
    assert errors == [], (
        f"Residential legacy fixture must not produce errors after 8H.2A. "
        f"Got: {errors}"
    )

    # Land: comparable + income only (legacy fixture)
    land_result = _land()
    violations = validate_result(land_result)
    errors = [v for v in violations if v.severity == "error"]
    assert errors == [], (
        f"Land legacy fixture must not produce errors after 8H.2A. "
        f"Got: {errors}"
    )
