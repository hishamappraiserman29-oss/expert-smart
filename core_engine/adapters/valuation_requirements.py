"""
Single-Property Valuation Requirements Matrix — Phase 8A / 8H.2A.

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

Phase 8H.2A additions
---------------------
FieldSpec gains four new optional attributes (all with defaults — fully
backward-compatible with existing call-sites):

  role        "user_input" | "engine_value"
              Engine-value fields (comparable / cost / income / comparables)
              are computed approach values or evidence containers; they must
              NOT be rendered as user data-collection inputs.  All other
              fields default to "user_input".

  label_ar    Arabic display label for the field.  Empty string = not yet
              translated (legacy fields carry "" until updated).

  group       "document" — field represents a document the user is asked
              to provide (rendered as a checkbox).  "" = data field.

  ui_required True when the frontend dynamic form SHOULD treat this field
              as mandatory (red asterisk, blocked submit).  Deliberately
              separated from `required` (runtime validation) so that new
              user-facing fields do not break existing valuation results
              that pre-date the enriched registry.

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
    """Specification for a single metadata field in a ValuationRequirements.

    Attributes
    ----------
    name, required, field_type, description, valid_values
        Original 8A attributes — semantics unchanged.
    role
        "user_input"   — field should be collected from the user (default).
        "engine_value" — field is a computed approach value or internal
                         evidence container; must NOT be rendered as a
                         user data-entry input in the UI.
    label_ar
        Arabic display label.  Empty string for fields not yet translated.
    group
        "document" — field is a document the user is asked to provide;
                     render as a checkbox in the dynamic form.
        ""         — regular data field (default).
    ui_required
        True  — the frontend form SHOULD treat this field as mandatory.
        False — optional in the UI (default).
        Deliberately independent of `required` so new fields do not
        break runtime validate_result() on existing valuation results.
    """

    name:         str
    required:     bool
    field_type:   str             # "str" | "float" | "int" | "bool" | "list"
    description:  str
    valid_values: tuple[str, ...] = field(default_factory=tuple)
    role:         str  = "user_input"   # "user_input" | "engine_value"
    label_ar:     str  = ""
    group:        str  = ""             # "document" | ""
    ui_required:  bool = False


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
# Fields marked role="engine_value" are approach values or evidence containers
# used by the valuation engine.  They are kept required=True for runtime
# validate_result() compatibility and must NOT be rendered as user inputs.

_COMMON: tuple[FieldSpec, ...] = (
    FieldSpec(
        "comparable", True, "float",
        "Comparable-sales approach value (EGP)",
        role="engine_value",
    ),
    FieldSpec(
        "income", True, "float",
        "Income-capitalization approach value (EGP)",
        role="engine_value",
    ),
    FieldSpec("client_name",    False, "str",   "Client or borrower name",                 label_ar="اسم العميل"),
    FieldSpec("location",       False, "str",   "Property address or location description", label_ar="الموقع"),
    FieldSpec("area",           False, "float", "Floor / land area (sqm)",                 label_ar="المساحة (م²)"),
    FieldSpec("valuation_date", False, "str",   "Date of valuation (YYYY-MM-DD)",           label_ar="تاريخ التقييم"),
    FieldSpec("appraiser_name", False, "str",   "Appraiser full name",                      label_ar="اسم المقيّم"),
    FieldSpec(
        "comparables", False, "list",
        "List of comparable sales dicts",
        role="engine_value",
    ),
)

_RESIDENTIAL: tuple[FieldSpec, ...] = _COMMON + (
    # ── Existing engine / weight fields ──────────────────────────────────────
    FieldSpec(
        "cost", True, "float",
        "Cost-approach value (EGP) — all three approaches apply for improved property",
        role="engine_value",
    ),
    FieldSpec(
        "ownership_type", False, "str",
        "Ownership type driving weight preset",
        ("owner_occupied", "rental", "mixed"),
        label_ar="نوع الملكية",
    ),
    FieldSpec(
        "quality_tier", False, "str",
        "Build-quality tier affecting post-reconciliation adjustment",
        ("luxury", "standard", "economy", "heritage"),
        label_ar="درجة الجودة",
    ),
    FieldSpec("age_years", False, "int", "Building age in years", label_ar="عمر المبنى (سنة)"),

    # ── New user-input / form fields (Phase 8H.2A) ───────────────────────────
    FieldSpec("area_sqm",     False, "float", "Floor area (sqm)",
              label_ar="المساحة (م²)", ui_required=True),
    FieldSpec("floor_number", False, "int",   "Floor number within the building",
              label_ar="رقم الطابق", ui_required=True),
    FieldSpec("rooms_count",  False, "int",   "Number of rooms",
              label_ar="عدد الغرف", ui_required=True),
    FieldSpec(
        "finishing_level", False, "str",
        "Finishing level of the unit",
        ("shell", "semi_finished", "standard_finished", "luxury_finished"),
        label_ar="مستوى التشطيب",
        ui_required=True,
    ),
    FieldSpec("building_age", False, "int", "Building age in years (user-facing form field)",
              label_ar="عمر المبنى (سنة)"),
    FieldSpec(
        "elevator_available", False, "str",
        "Elevator available in the building",
        ("yes", "no"),
        label_ar="يوجد مصعد",
    ),
    FieldSpec(
        "parking_available", False, "str",
        "Dedicated parking space available",
        ("yes", "no"),
        label_ar="يوجد موقف سيارة",
    ),
    FieldSpec(
        "legal_status", False, "str",
        "Legal / title status of the property",
        ("registered_title", "preliminary_contract", "allocation", "unknown"),
        label_ar="الحالة القانونية",
        ui_required=True,
    ),
    FieldSpec(
        "view_quality", False, "str",
        "View quality from the unit",
        ("ordinary", "good", "premium"),
        label_ar="جودة الإطلالة",
    ),
    FieldSpec("services_available", False, "str",
              "Available building services (free text)", label_ar="الخدمات المتاحة"),

    # ── Residential document checklist items ─────────────────────────────────
    FieldSpec("ownership_document",   False, "bool",
              "Ownership deed / title document",
              label_ar="سند الملكية", group="document"),
    FieldSpec("site_croquis_or_location", False, "bool",
              "Site croquis or location map",
              label_ar="كروكي الموقع", group="document"),
    FieldSpec("recent_photos",        False, "bool",
              "Recent property photos",
              label_ar="صور حديثة للعقار", group="document"),
    FieldSpec("nearby_sale_comparables_if_available", False, "bool",
              "Nearby sale comparables (if available)",
              label_ar="مقارنات بيع قريبة (إن وجدت)", group="document"),
)

_COMMERCIAL: tuple[FieldSpec, ...] = _COMMON + (
    FieldSpec(
        "cost", True, "float",
        "Cost-approach value (EGP) — all three approaches apply for improved property",
        role="engine_value",
    ),
    FieldSpec("annual_rent",    False, "float", "Annual rental income (EGP)",          label_ar="الإيجار السنوي (ج.م.)"),
    FieldSpec("cap_rate",       False, "float", "Capitalization rate (0.0–1.0)",        label_ar="معدل الرسملة"),
    FieldSpec(
        "development_stage", False, "str",
        "Development stage driving weight preset",
        ("stabilized", "core", "new_construction", "redevelopment"),
        label_ar="مرحلة التطوير",
    ),
    FieldSpec("occupancy_rate", False, "float", "Occupancy rate (0.0–1.0)",             label_ar="نسبة الإشغال"),
    FieldSpec(
        "property_class", False, "str",
        "Building grade for post-reconciliation adjustment",
        ("class_a", "class_b", "class_c"),
        label_ar="فئة المبنى",
    ),
)

_LAND: tuple[FieldSpec, ...] = _COMMON + (
    # ── Existing engine / weight fields ──────────────────────────────────────
    FieldSpec(
        "hbu", False, "str",
        "Highest-and-best-use driving weight preset (cost weight = 0 for land)",
        ("residential", "commercial", "mixed_use", "industrial", "agricultural", "speculative"),
        label_ar="أفضل استخدام (HBU)",
    ),
    FieldSpec(
        "location_desirability", False, "str",
        "Location desirability multiplier",
        ("prime", "good", "standard", "secondary", "remote"),
        label_ar="جاذبية الموقع",
    ),
    FieldSpec(
        "zoning", False, "str",
        "Zoning restriction multiplier",
        ("unrestricted", "general_commercial", "residential_only", "restricted"),
        label_ar="التخطيط العمراني",
    ),
    FieldSpec(
        "development_feasibility", False, "str",
        "Development feasibility multiplier",
        ("ready_to_build", "feasible", "challenging", "very_difficult"),
        label_ar="جدوى التطوير",
    ),

    # ── New user-input / form fields (Phase 8H.2A) ───────────────────────────
    FieldSpec("land_area_sqm",  False, "float", "Land area (sqm)",
              label_ar="مساحة الأرض (م²)", ui_required=True),
    FieldSpec("frontage_m",     False, "float", "Street frontage width (m)",
              label_ar="واجهة الأرض (م)", ui_required=True),
    FieldSpec("street_width_m", False, "float", "Adjacent street width (m)",
              label_ar="عرض الشارع (م)", ui_required=True),
    FieldSpec(
        "zoning_type", False, "str",
        "Zoning classification",
        ("residential", "commercial", "administrative", "mixed_use", "agricultural", "unknown"),
        label_ar="نوع التخطيط العمراني",
        ui_required=True,
    ),
    FieldSpec(
        "utilities_available", False, "list",
        "Available utilities on the plot",
        ("electricity", "water", "sewage", "gas", "paved_road"),
        label_ar="الخدمات المتاحة",
    ),
    FieldSpec(
        "buildability_status", False, "str",
        "Buildability and planning constraints",
        ("buildable", "needs_verification", "planning_restrictions", "unknown"),
        label_ar="حالة قابلية البناء",
        ui_required=True,
    ),
    FieldSpec(
        "legal_status", False, "str",
        "Legal / title status of the land",
        ("registered_title", "preliminary_contract", "allocation", "unknown"),
        label_ar="الحالة القانونية",
        ui_required=True,
    ),

    # ── Land document checklist items ─────────────────────────────────────────
    FieldSpec("ownership_document",    False, "bool",
              "Ownership deed / title document",
              label_ar="سند الملكية", group="document"),
    FieldSpec("site_plan_or_croquis",  False, "bool",
              "Site plan or croquis",
              label_ar="كروكي المخطط", group="document"),
    FieldSpec("area_statement",        False, "bool",
              "Area statement / survey certificate",
              label_ar="بيان مساحة", group="document"),
    FieldSpec("coordinates_or_map_location", False, "bool",
              "GPS coordinates or map location",
              label_ar="إحداثيات / موقع خرائطي", group="document"),
    FieldSpec("site_photos",           False, "bool",
              "Site photographs",
              label_ar="صور الموقع", group="document"),
    FieldSpec("building_regulations_if_available", False, "bool",
              "Building regulations (if available)",
              label_ar="اشتراطات البناء (إن وجدت)", group="document"),
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

    Note: only fields with required=True are enforced here.  Fields added
    in Phase 8H.2A carry required=False / ui_required=True; they are NOT
    checked by this function to preserve backward compatibility with
    existing valuation results that pre-date the enriched registry.

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

        elif value is not None and spec.valid_values and spec.field_type != "list":
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
