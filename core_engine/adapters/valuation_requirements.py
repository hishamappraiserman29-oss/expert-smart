"""
Single-Property Valuation Requirements Matrix — Phase 8A.

Declarative registry of which metadata fields are required or recommended
for each (asset_type, primary_purpose) combination in the single-property
report pipeline.

Role in the system
------------------
- NOT the adapter validate_inputs() — that validates subject_property inputs
  at run-time before the adapter computes a value.
- NOT quality_auditor.ReportQualityAuditor — that scores a completed
  AssetValuationResult against EGVS/USPAP compliance and methodology.
- THIS MODULE answers: "for a given (asset_type, purpose), which metadata
  fields must the AssetValuationResult carry for the report to be buildable
  and complete?"

Usage
-----
    from adapters.valuation_requirements import (
        get_requirements,
        validate_result,
        list_supported_asset_types,
        list_supported_purposes,
    )

    reqs = get_requirements("residential", "mortgage_lending")
    violations = validate_result(result)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from adapters.asset import AssetValuationResult


# ── Supported combinations ────────────────────────────────────────────────────

SUPPORTED_ASSET_TYPES: frozenset[str] = frozenset({
    "residential",
    "commercial",
    "land",
})

SUPPORTED_PURPOSES_BY_ASSET_TYPE: dict[str, frozenset[str]] = {
    "residential": frozenset({
        "market_value",
        "mortgage_lending",
        "insurance",
        "liquidation",
    }),
    "commercial": frozenset({
        "market_value",
        "investment_analysis",
        "insurance",
        "liquidation",
    }),
    "land": frozenset({
        "market_value",
        "investment_analysis",
        "liquidation",
    }),
}

SUPPORTED_PURPOSES: frozenset[str] = frozenset().union(
    *SUPPORTED_PURPOSES_BY_ASSET_TYPE.values()
)


# ── Field specification ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class FieldSpec:
    """Specification for a single metadata field in a ValuationRequirements."""

    name:         str
    required:     bool
    field_type:   str             # "str" | "float" | "int" | "decimal" | "list"
    description:  str
    valid_values: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ValuationRequirements:
    """Requirements for one (asset_type, purpose) combination."""

    asset_type:      str
    purpose:         str
    metadata_fields: tuple[FieldSpec, ...]

    @property
    def required_fields(self) -> tuple[FieldSpec, ...]:
        return tuple(f for f in self.metadata_fields if f.required)

    @property
    def optional_fields(self) -> tuple[FieldSpec, ...]:
        return tuple(f for f in self.metadata_fields if not f.required)


# ── Shared field definitions ──────────────────────────────────────────────────

_COMMON: tuple[FieldSpec, ...] = (
    FieldSpec("comparable",      True,  "float", "Comparable-sales approach value (EGP)"),
    FieldSpec("income",          True,  "float", "Income-capitalization approach value (EGP)"),
    FieldSpec("client_name",     False, "str",   "Client or borrower name"),
    FieldSpec("location",        False, "str",   "Property address or location description"),
    FieldSpec("area",            False, "float", "Floor / land area (sqm)"),
    FieldSpec("valuation_date",  False, "str",   "Date of valuation (YYYY-MM-DD)"),
    FieldSpec("appraiser_name",  False, "str",   "Appraiser full name"),
    FieldSpec("comparables",     False, "list",  "List of comparable sales dicts"),
)

_RESIDENTIAL: tuple[FieldSpec, ...] = _COMMON + (
    FieldSpec(
        "cost", True, "float",
        "Cost-approach value (EGP) — all three approaches apply for improved property",
    ),
    FieldSpec(
        "ownership_type", False, "str",
        "Ownership type driving weight preset",
        ("owner_occupied", "rental", "mixed"),
    ),
    FieldSpec(
        "quality_tier", False, "str",
        "Build-quality tier affecting post-reconciliation adjustment",
        ("luxury", "standard", "economy", "heritage"),
    ),
    FieldSpec("age_years", False, "int", "Building age in years"),
)

_COMMERCIAL: tuple[FieldSpec, ...] = _COMMON + (
    FieldSpec(
        "cost", True, "float",
        "Cost-approach value (EGP) — all three approaches apply for improved property",
    ),
    FieldSpec("annual_rent",    False, "float", "Annual rental income (EGP)"),
    FieldSpec("cap_rate",       False, "float", "Capitalization rate (0.0–1.0)"),
    FieldSpec(
        "development_stage", False, "str",
        "Development stage driving weight preset",
        ("stabilized", "core", "new_construction", "redevelopment"),
    ),
    FieldSpec("occupancy_rate", False, "float", "Occupancy rate (0.0–1.0)"),
    FieldSpec(
        "property_class", False, "str",
        "Building grade for post-reconciliation adjustment",
        ("class_a", "class_b", "class_c"),
    ),
)

_LAND: tuple[FieldSpec, ...] = _COMMON + (
    FieldSpec(
        "hbu", False, "str",
        "Highest-and-best-use driving weight preset (cost weight = 0 for land)",
        ("residential", "commercial", "mixed_use", "industrial", "agricultural", "speculative"),
    ),
    FieldSpec(
        "location_desirability", False, "str",
        "Location desirability multiplier",
        ("prime", "good", "standard", "secondary", "remote"),
    ),
    FieldSpec(
        "zoning", False, "str",
        "Zoning restriction multiplier",
        ("unrestricted", "general_commercial", "residential_only", "restricted"),
    ),
    FieldSpec(
        "development_feasibility", False, "str",
        "Development feasibility multiplier",
        ("ready_to_build", "feasible", "challenging", "very_difficult"),
    ),
)


# ── Build the matrix ──────────────────────────────────────────────────────────

def _build_matrix() -> dict[tuple[str, str], ValuationRequirements]:
    _fields_by_type = {
        "residential": _RESIDENTIAL,
        "commercial":  _COMMERCIAL,
        "land":        _LAND,
    }
    matrix: dict[tuple[str, str], ValuationRequirements] = {}
    for asset_type, purposes in SUPPORTED_PURPOSES_BY_ASSET_TYPE.items():
        for purpose in purposes:
            matrix[(asset_type, purpose)] = ValuationRequirements(
                asset_type=asset_type,
                purpose=purpose,
                metadata_fields=_fields_by_type[asset_type],
            )
    return matrix


REQUIREMENTS_MATRIX: dict[tuple[str, str], ValuationRequirements] = _build_matrix()


# ── Public API ────────────────────────────────────────────────────────────────

def get_requirements(asset_type: str, purpose: str) -> ValuationRequirements:
    """Return the ValuationRequirements for (asset_type, purpose).

    Raises
    ------
    ValueError
        If the combination is not in the matrix.
    """
    key = (asset_type, purpose)
    entry = REQUIREMENTS_MATRIX.get(key)
    if entry is None:
        valid_purposes = sorted(
            SUPPORTED_PURPOSES_BY_ASSET_TYPE.get(asset_type, set())
        )
        raise ValueError(
            f"No requirements defined for (asset_type={asset_type!r}, "
            f"purpose={purpose!r}). "
            f"Valid asset types: {sorted(SUPPORTED_ASSET_TYPES)}. "
            f"Valid purposes for {asset_type!r}: {valid_purposes}."
        )
    return entry


def list_supported_asset_types() -> list[str]:
    """Return sorted list of supported asset types."""
    return sorted(SUPPORTED_ASSET_TYPES)


def list_supported_purposes(asset_type: str) -> list[str]:
    """Return sorted list of supported purposes for asset_type.

    Raises
    ------
    ValueError
        If asset_type is not supported.
    """
    if asset_type not in SUPPORTED_PURPOSES_BY_ASSET_TYPE:
        raise ValueError(
            f"Unknown asset_type {asset_type!r}. "
            f"Valid: {sorted(SUPPORTED_ASSET_TYPES)}"
        )
    return sorted(SUPPORTED_PURPOSES_BY_ASSET_TYPE[asset_type])


@dataclass
class RequirementsViolation:
    """A single violation found by validate_result()."""

    field:    str
    message:  str
    severity: str   # "error" | "warning"


def validate_result(result: Any) -> list[RequirementsViolation]:
    """Validate an AssetValuationResult against the Requirements Matrix.

    Checks
    ------
    1. asset_type is in SUPPORTED_ASSET_TYPES.
    2. primary_purpose is supported for this asset_type.
    3. All required metadata fields are present.
    4. Enum metadata fields (where present) carry a value in valid_values.

    Parameters
    ----------
    result : AssetValuationResult
        Any object with .asset_type, .primary_purpose, and .metadata attributes.

    Returns
    -------
    list[RequirementsViolation]
        Empty list = fully compliant.
    """
    violations: list[RequirementsViolation] = []

    asset_type = getattr(result, "asset_type", None) or ""
    purpose    = getattr(result, "primary_purpose", None) or ""
    metadata   = getattr(result, "metadata", {}) or {}

    if asset_type not in SUPPORTED_ASSET_TYPES:
        violations.append(RequirementsViolation(
            field="asset_type",
            message=(
                f"asset_type {asset_type!r} is not supported. "
                f"Valid: {sorted(SUPPORTED_ASSET_TYPES)}"
            ),
            severity="error",
        ))
        return violations   # cannot proceed without a valid asset_type

    valid_purposes = SUPPORTED_PURPOSES_BY_ASSET_TYPE[asset_type]
    if purpose not in valid_purposes:
        violations.append(RequirementsViolation(
            field="primary_purpose",
            message=(
                f"primary_purpose {purpose!r} is not supported for "
                f"asset_type {asset_type!r}. "
                f"Valid: {sorted(valid_purposes)}"
            ),
            severity="error",
        ))
        return violations   # cannot fetch requirements without a valid purpose

    reqs = get_requirements(asset_type, purpose)

    for spec in reqs.metadata_fields:
        value = metadata.get(spec.name)

        if spec.required and value is None:
            violations.append(RequirementsViolation(
                field=f"metadata.{spec.name}",
                message=f"Required field '{spec.name}' is absent from metadata.",
                severity="error",
            ))

        elif value is not None and spec.valid_values:
            if str(value) not in spec.valid_values:
                violations.append(RequirementsViolation(
                    field=f"metadata.{spec.name}",
                    message=(
                        f"Field '{spec.name}' value {value!r} is not in "
                        f"valid values: {spec.valid_values}"
                    ),
                    severity="warning",
                ))

    return violations
