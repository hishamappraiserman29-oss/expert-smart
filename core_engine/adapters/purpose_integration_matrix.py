"""
Purpose Integration Matrix — Phase 8 (METADATA + VALIDATION + STRUCTURE ONLY).

Defines the nine-layer integration matrix for valuation purposes.  This module
is metadata-only:

  ⚠️  NO valuation engine logic.
  ⚠️  NO scrapers, web fetches, or external service calls.
  ⚠️  NO automatic data population or external enrichment.
  ⚠️  NO report generation.
  ⚠️  NO database migrations.
  ⚠️  NO API contract changes.

Central governance rule (enforced in every matrix):
    Any auto-enriched value must NOT enter a final report without an explicit
    human approval record (approval_status == "approved").
    If auto-enriched data is present and approval_status != "approved",
    the report state must be "draft_pending_human_review".

Relationship to existing modules
---------------------------------
  purpose_routes.py  (Phase 7) — group_id / route_id identifiers reused.
  valuation_requirements.py   — FieldSpec field codes reused where possible.
  purpose_adapter.py          — PURPOSE_RULES / multipliers UNCHANGED.

Currently implemented matrices
-------------------------------
  market_value / market_value_with_habu  →  Market Value based on HABU

Usage
-----
    from adapters.purpose_integration_matrix import (
        list_available_matrices,
        get_purpose_matrix,
        get_market_value_habu_matrix,
        validate_matrix_definition,
        list_matrix_fields,
        list_fields_by_layer,
        requires_human_approval,
        APPROVAL_STATUSES,
        REPORT_STATUSES,
    )

    matrix = get_market_value_habu_matrix()
    fields = list_matrix_fields(matrix)
    needs_approval = requires_human_approval(matrix, {"is_automated_fill": True})
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── Governance constants ──────────────────────────────────────────────────────

APPROVAL_STATUSES: frozenset[str] = frozenset({
    "not_required",
    "pending_human_review",
    "approved",
    "rejected",
})

REPORT_STATUSES: frozenset[str] = frozenset({
    "draft_pending_human_review",
    "ready_for_final",
    "final_approved",
})

# Auto-enriched values are NEVER final-approved by default; they start as draft.
_AUTO_ENRICH_DEFAULT_APPROVAL: str = "pending_human_review"
_AUTO_ENRICH_DEFAULT_REPORT_STATUS: str = "draft_pending_human_review"


# ── Layer definitions ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class UIFieldSpec:
    """Metadata descriptor for a single UI input field."""
    field_code:  str
    label_en:    str
    label_ar:    str
    field_type:  str                       # "text" | "number" | "coordinate" | "select"
    required:    bool = False
    ui_required: bool = False


@dataclass(frozen=True)
class DBFieldSpec:
    """Metadata descriptor for a database-persisted field.

    No migration is created here — this is structural documentation only.
    """
    field_code:       str
    db_column:        str
    field_type:       str
    nullable:         bool = True
    is_automated_fill_candidate: bool = False


@dataclass(frozen=True)
class EngineInputSpec:
    """A field consumed by a valuation engine as input.

    No engine is built here — this documents expected future inputs only.
    """
    field_code:   str
    label_en:     str
    required:     bool = True
    unit:         str  = ""


@dataclass(frozen=True)
class MarketComparableSpec:
    """A market comparable data point required for this purpose route."""
    field_code:   str
    label_en:     str
    label_ar:     str
    required:     bool = True


@dataclass(frozen=True)
class AgenticEnrichmentSpec:
    """Metadata-only descriptor for a field that may be auto-enriched.

    ⚠️  NO scraping, NO web fetches, NO automatic population is performed here.
        This is a structural declaration of what an enrichment pipeline
        *would* need to supply and what governance it must respect.

    Governance:
        - Every auto-enriched value starts with approval_status = "pending_human_review".
        - It may NOT be treated as final_approved until a human expert approves it.
        - If is_automated_fill=True and approval_status != "approved", the report
          state must be "draft_pending_human_review".
    """
    field_code:             str
    label_en:               str
    default_approval_status: str = "pending_human_review"
    requires_human_review:  bool = True


@dataclass(frozen=True)
class ValidationRule:
    """A single field-level or cross-field validation rule."""
    rule_id:     str
    field_codes: tuple[str, ...]
    description: str
    severity:    str = "error"             # "error" | "warning"


@dataclass(frozen=True)
class HumanApprovalSpec:
    """Governance rules for human approval within this matrix."""
    required_if_auto_enriched:         bool
    default_status_for_auto_enriched:  str
    report_state_without_approval:     str
    allowed_approval_statuses:         tuple[str, ...]
    auto_enriched_may_be_final_default: bool = False


@dataclass(frozen=True)
class ReportDisclosureSpec:
    """Metadata about what must be disclosed in the final report."""
    field_code:  str
    label_en:    str
    disclose_if: str    # "always" | "if_auto_enriched" | "if_present"


@dataclass(frozen=True)
class OutputContractSpec:
    """Expected output key from a future valuation engine for this route."""
    key:         str
    label_en:    str
    optional:    bool = False


# ── Top-level matrix ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PurposeIntegrationMatrix:
    """Nine-layer integration matrix for one purpose_group / purpose_route pair.

    Layers
    ------
    1. ui_fields            — fields collected by the UI
    2. db_mapping           — persistence metadata (no migrations)
    3. engine_inputs        — inputs consumed by a future valuation engine
    4. market_comparables   — market comparable data points required
    5. agentic_enrichment   — auto-enrichment metadata (no scraping/fetching)
    6. validation_rules     — field and cross-field validation rules
    7. human_approval       — governance / approval rules
    8. report_disclosure    — disclosure obligations
    9. output_contract      — expected engine output keys
    """
    # Identity
    purpose_group:     str
    purpose_route:     str
    name_en:           str
    name_ar:           str
    valuation_basis:   str
    default_ifrs_level: str

    # Governance flags
    human_approval_required_if_auto_enriched:         bool
    final_report_allowed_without_human_approval_if_auto_enriched: bool

    # Nine layers
    ui_fields:           tuple[UIFieldSpec, ...]
    db_mapping:          tuple[DBFieldSpec, ...]
    engine_inputs:       tuple[EngineInputSpec, ...]
    market_comparables:  tuple[MarketComparableSpec, ...]
    agentic_enrichment:  tuple[AgenticEnrichmentSpec, ...]
    validation_rules:    tuple[ValidationRule, ...]
    human_approval:      HumanApprovalSpec
    report_disclosure:   tuple[ReportDisclosureSpec, ...]
    output_contract:     tuple[OutputContractSpec, ...]


# ── Matrix: Market Value based on HABU ───────────────────────────────────────

_MV_HABU_UI_FIELDS: tuple[UIFieldSpec, ...] = (
    UIFieldSpec("property_id",          "Property ID",                  "رقم العقار",                      "text",       required=True,  ui_required=True),
    UIFieldSpec("total_land_area",      "Total Land Area (m²)",         "مساحة الأرض الإجمالية (م²)",      "number",     required=True,  ui_required=True),
    UIFieldSpec("gps_coordinates",      "GPS Coordinates",              "إحداثيات GPS",                    "coordinate", required=False, ui_required=False),
    UIFieldSpec("current_use",          "Current Use",                  "الاستخدام الحالي",                "text",       required=True,  ui_required=True),
    UIFieldSpec("proposed_habu_use",    "Proposed HABU Use",            "الاستخدام المقترح (HABU)",        "text",       required=True,  ui_required=True),
    UIFieldSpec("max_far_allowed",      "Max FAR Allowed",              "نسبة البناء القصوى المسموح بها",  "number",     required=True,  ui_required=True),
    UIFieldSpec("expected_habu_noi",    "Expected HABU NOI (SAR/yr)",   "صافي الدخل التشغيلي المتوقع (ريال/سنة)", "number", required=True, ui_required=True),
    UIFieldSpec("comp_avg_price_m2",    "Comp Avg Price (SAR/m²)",      "متوسط سعر المقارنات (ريال/م²)",  "number",     required=True,  ui_required=True),
    UIFieldSpec("comp_adjustment_rate", "Comp Adjustment Rate (%)",     "معدل التعديل على المقارنات (%)", "number",     required=True,  ui_required=True),
    UIFieldSpec("market_vacancy_rate",  "Market Vacancy Rate (%)",      "معدل الشواغر السوقية (%)",       "number",     required=True,  ui_required=True),
)

_MV_HABU_DB_MAPPING: tuple[DBFieldSpec, ...] = (
    DBFieldSpec("property_id",          "property_id",          "varchar",  nullable=False),
    DBFieldSpec("total_land_area",      "total_land_area",      "numeric",  nullable=False),
    DBFieldSpec("gps_coordinates",      "gps_coordinates",      "varchar",  nullable=True),
    DBFieldSpec("current_use",          "current_use",          "varchar",  nullable=False),
    DBFieldSpec("proposed_habu_use",    "proposed_habu_use",    "varchar",  nullable=False),
    DBFieldSpec("max_far_allowed",      "max_far_allowed",      "numeric",  nullable=False),
    DBFieldSpec("expected_habu_noi",    "expected_habu_noi",    "numeric",  nullable=False),
    DBFieldSpec("comp_avg_price_m2",    "comp_avg_price_m2",    "numeric",  nullable=False),
    DBFieldSpec("comp_adjustment_rate", "comp_adjustment_rate", "numeric",  nullable=False),
    DBFieldSpec("market_vacancy_rate",  "market_vacancy_rate",  "numeric",  nullable=False),
    # Enrichment/governance fields
    DBFieldSpec("purpose_route",        "purpose_route",        "varchar",  nullable=False),
    DBFieldSpec("is_automated_fill",    "is_automated_fill",    "boolean",  nullable=False, is_automated_fill_candidate=True),
    DBFieldSpec("data_source_log",      "data_source_log",      "jsonb",    nullable=True,  is_automated_fill_candidate=True),
    DBFieldSpec("confidence_score",     "confidence_score",     "numeric",  nullable=True,  is_automated_fill_candidate=True),
    DBFieldSpec("approval_status",      "approval_status",      "varchar",  nullable=False, is_automated_fill_candidate=True),
)

_MV_HABU_ENGINE_INPUTS: tuple[EngineInputSpec, ...] = (
    EngineInputSpec("total_land_area",      "Total Land Area (m²)",        required=True,  unit="m²"),
    EngineInputSpec("proposed_habu_use",    "Proposed HABU Use",           required=True,  unit=""),
    EngineInputSpec("max_far_allowed",      "Max FAR Allowed",             required=True,  unit="ratio"),
    EngineInputSpec("expected_habu_noi",    "Expected HABU NOI (SAR/yr)",  required=True,  unit="SAR/yr"),
    EngineInputSpec("comp_avg_price_m2",    "Comp Avg Price (SAR/m²)",     required=True,  unit="SAR/m²"),
    EngineInputSpec("comp_adjustment_rate", "Comp Adjustment Rate (%)",    required=True,  unit="%"),
    EngineInputSpec("market_vacancy_rate",  "Market Vacancy Rate (%)",     required=True,  unit="%"),
)

_MV_HABU_MARKET_COMPARABLES: tuple[MarketComparableSpec, ...] = (
    MarketComparableSpec("comp_avg_price_m2",        "Comp Avg Price (SAR/m²)",     "متوسط سعر المقارنات (ريال/م²)",   required=True),
    MarketComparableSpec("comp_adjustment_rate",     "Comp Adjustment Rate (%)",    "معدل التعديل على المقارنات (%)",  required=True),
    MarketComparableSpec("comparable_count",         "Comparable Count",            "عدد المقارنات",                   required=True),
    MarketComparableSpec("comparable_search_radius", "Comparable Search Radius",    "نطاق البحث عن المقارنات",         required=False),
    MarketComparableSpec("comparable_date_range",    "Comparable Date Range",       "نطاق تواريخ المقارنات",           required=False),
    MarketComparableSpec("market_vacancy_rate",      "Market Vacancy Rate (%)",     "معدل الشواغر السوقية (%)",        required=True),
)

# Agentic enrichment: metadata only — no scraping, no fetching, no auto-population.
_MV_HABU_AGENTIC_ENRICHMENT: tuple[AgenticEnrichmentSpec, ...] = (
    AgenticEnrichmentSpec("is_automated_fill",  "Is Automated Fill Flag",  default_approval_status="pending_human_review", requires_human_review=True),
    AgenticEnrichmentSpec("data_source_log",    "Data Source Log",         default_approval_status="pending_human_review", requires_human_review=True),
    AgenticEnrichmentSpec("confidence_score",   "Confidence Score (0–100)","pending_human_review",                         requires_human_review=True),
    AgenticEnrichmentSpec("source_timestamp",   "Source Timestamp",        "pending_human_review",                         requires_human_review=True),
    AgenticEnrichmentSpec("source_url",         "Source URL",              "pending_human_review",                         requires_human_review=True),
    AgenticEnrichmentSpec("source_type",        "Source Type",             "pending_human_review",                         requires_human_review=True),
    AgenticEnrichmentSpec("approval_status",    "Approval Status",         "pending_human_review",                         requires_human_review=True),
)

_MV_HABU_VALIDATION_RULES: tuple[ValidationRule, ...] = (
    ValidationRule(
        "VAL_HABU_01",
        ("total_land_area",),
        "total_land_area must be > 0 when entered manually",
        severity="error",
    ),
    ValidationRule(
        "VAL_HABU_02",
        ("gps_coordinates",),
        "gps_coordinates is required only when auto-enrichment is requested",
        severity="warning",
    ),
    ValidationRule(
        "VAL_HABU_03",
        ("max_far_allowed",),
        "max_far_allowed must be >= 0",
        severity="error",
    ),
    ValidationRule(
        "VAL_HABU_04",
        ("expected_habu_noi",),
        "expected_habu_noi must be >= 0",
        severity="error",
    ),
    ValidationRule(
        "VAL_HABU_05",
        ("comp_avg_price_m2",),
        "comp_avg_price_m2 must be >= 0",
        severity="error",
    ),
    ValidationRule(
        "VAL_HABU_06",
        ("comp_adjustment_rate",),
        "comp_adjustment_rate must be within a safe percentage range (e.g. -50% to +50%)",
        severity="error",
    ),
    ValidationRule(
        "VAL_HABU_07",
        ("confidence_score",),
        "confidence_score must be between 0 and 100 (inclusive)",
        severity="error",
    ),
    ValidationRule(
        "VAL_HABU_08",
        ("is_automated_fill", "data_source_log"),
        "if is_automated_fill=True then data_source_log must be present",
        severity="error",
    ),
    ValidationRule(
        "VAL_HABU_09",
        ("is_automated_fill", "approval_status"),
        "if is_automated_fill=True then approval_status must not be 'final_approved' by default",
        severity="error",
    ),
)

_MV_HABU_HUMAN_APPROVAL: HumanApprovalSpec = HumanApprovalSpec(
    required_if_auto_enriched=True,
    default_status_for_auto_enriched="pending_human_review",
    report_state_without_approval="draft_pending_human_review",
    allowed_approval_statuses=tuple(sorted(APPROVAL_STATUSES)),
    auto_enriched_may_be_final_default=False,
)

_MV_HABU_REPORT_DISCLOSURE: tuple[ReportDisclosureSpec, ...] = (
    ReportDisclosureSpec("proposed_habu_use",    "HABU Assumption Disclosure",              "always"),
    ReportDisclosureSpec("is_automated_fill",    "Whether Market Data is Auto-Enriched",    "if_auto_enriched"),
    ReportDisclosureSpec("confidence_score",     "Confidence Score of Enriched Data",       "if_auto_enriched"),
    ReportDisclosureSpec("data_source_log",      "Data Source Log",                         "if_auto_enriched"),
    ReportDisclosureSpec("market_vacancy_rate",  "Market Vacancy Rate Used",                "always"),
    ReportDisclosureSpec("comp_adjustment_rate", "Comparable Adjustment Rate Applied",      "always"),
    ReportDisclosureSpec("approval_status",      "Human Approval Status of Enriched Data",  "if_present"),
)

_MV_HABU_OUTPUT_CONTRACT: tuple[OutputContractSpec, ...] = (
    OutputContractSpec("valuation_basis",        "Valuation Basis",              optional=False),
    OutputContractSpec("purpose_route",          "Purpose Route",                optional=False),
    OutputContractSpec("final_value",            "Final Indicated Value (SAR)",  optional=False),
    OutputContractSpec("habu_use",               "HABU Use Adopted",             optional=False),
    OutputContractSpec("habu_noi",               "HABU NOI Applied (SAR/yr)",    optional=False),
    OutputContractSpec("market_value_indication","Market Value Indication (SAR)", optional=False),
    OutputContractSpec("adjustment_summary",     "Comparable Adjustment Summary", optional=False),
    OutputContractSpec("confidence_score",       "Confidence Score",             optional=True),
    OutputContractSpec("approval_status",        "Human Approval Status",        optional=False),
    OutputContractSpec("report_status",          "Report Status",                optional=False),
    OutputContractSpec("disclosures",            "Disclosure Statements",        optional=False),
)

# The matrix instance
_MARKET_VALUE_HABU_MATRIX = PurposeIntegrationMatrix(
    purpose_group   = "market_value",
    purpose_route   = "market_value_with_habu",
    name_en         = "Market Value based on HABU",
    name_ar         = "القيمة السوقية بناءً على أعلى وأفضل استغلال",
    valuation_basis = "Market Value",
    default_ifrs_level = "Level 2",

    human_approval_required_if_auto_enriched = True,
    final_report_allowed_without_human_approval_if_auto_enriched = False,

    ui_fields          = _MV_HABU_UI_FIELDS,
    db_mapping         = _MV_HABU_DB_MAPPING,
    engine_inputs      = _MV_HABU_ENGINE_INPUTS,
    market_comparables = _MV_HABU_MARKET_COMPARABLES,
    agentic_enrichment = _MV_HABU_AGENTIC_ENRICHMENT,
    validation_rules   = _MV_HABU_VALIDATION_RULES,
    human_approval     = _MV_HABU_HUMAN_APPROVAL,
    report_disclosure  = _MV_HABU_REPORT_DISCLOSURE,
    output_contract    = _MV_HABU_OUTPUT_CONTRACT,
)


# ── Registry ──────────────────────────────────────────────────────────────────

# Keyed by (purpose_group, purpose_route)
_MATRIX_REGISTRY: dict[tuple[str, str], PurposeIntegrationMatrix] = {
    (_MARKET_VALUE_HABU_MATRIX.purpose_group,
     _MARKET_VALUE_HABU_MATRIX.purpose_route): _MARKET_VALUE_HABU_MATRIX,
}

_NINE_LAYER_NAMES: tuple[str, ...] = (
    "ui_fields",
    "db_mapping",
    "engine_inputs",
    "market_comparables",
    "agentic_enrichment",
    "validation_rules",
    "human_approval",
    "report_disclosure",
    "output_contract",
)


# ── Public API ────────────────────────────────────────────────────────────────

def list_available_matrices() -> list[tuple[str, str]]:
    """Return all (purpose_group, purpose_route) keys sorted."""
    return sorted(_MATRIX_REGISTRY.keys())


def get_purpose_matrix(purpose_group: str, purpose_route: str) -> PurposeIntegrationMatrix:
    """Return the integration matrix for the given group/route pair.

    Raises
    ------
    ValueError
        If no matrix is registered for that combination.
    """
    key = (purpose_group, purpose_route)
    matrix = _MATRIX_REGISTRY.get(key)
    if matrix is None:
        registered = sorted(str(k) for k in _MATRIX_REGISTRY)
        raise ValueError(
            f"No integration matrix for ({purpose_group!r}, {purpose_route!r}). "
            f"Registered: {registered}"
        )
    return matrix


def get_market_value_habu_matrix() -> PurposeIntegrationMatrix:
    """Convenience accessor for the Market Value / HABU matrix."""
    return _MARKET_VALUE_HABU_MATRIX


def validate_matrix_definition(matrix: PurposeIntegrationMatrix) -> list[str]:
    """Validate structural completeness of a matrix definition.

    Returns a list of error strings.  An empty list means the matrix is valid.
    Does NOT validate runtime data values — use validation_rules for that.
    """
    errors: list[str] = []

    if not matrix.purpose_group:
        errors.append("purpose_group must not be empty")
    if not matrix.purpose_route:
        errors.append("purpose_route must not be empty")
    if not matrix.name_en:
        errors.append("name_en must not be empty")
    if not matrix.name_ar:
        errors.append("name_ar must not be empty")
    if not matrix.valuation_basis:
        errors.append("valuation_basis must not be empty")
    if not matrix.default_ifrs_level:
        errors.append("default_ifrs_level must not be empty")

    for layer in _NINE_LAYER_NAMES:
        val = getattr(matrix, layer)
        if val is None:
            errors.append(f"Layer '{layer}' must not be None")

    # human_approval governance invariants
    ha = matrix.human_approval
    if ha.auto_enriched_may_be_final_default:
        errors.append(
            "human_approval.auto_enriched_may_be_final_default must be False "
            "(auto-enriched values are never final-approved by default)"
        )
    for status in ha.allowed_approval_statuses:
        if status not in APPROVAL_STATUSES:
            errors.append(
                f"human_approval.allowed_approval_statuses contains unknown "
                f"status {status!r}. Allowed: {sorted(APPROVAL_STATUSES)}"
            )
    if ha.report_state_without_approval not in REPORT_STATUSES:
        errors.append(
            f"human_approval.report_state_without_approval {ha.report_state_without_approval!r} "
            f"is not a valid report status. Allowed: {sorted(REPORT_STATUSES)}"
        )

    # Every agentic_enrichment field must default to pending_human_review
    for ae in matrix.agentic_enrichment:
        if ae.default_approval_status == "approved":
            errors.append(
                f"AgenticEnrichmentSpec '{ae.field_code}': "
                f"default_approval_status must not be 'approved' "
                f"(auto-enriched values start as drafts)"
            )

    return errors


def list_matrix_fields(matrix: PurposeIntegrationMatrix) -> list[str]:
    """Return all unique field_codes referenced in the matrix (all layers)."""
    codes: set[str] = set()
    for f in matrix.ui_fields:
        codes.add(f.field_code)
    for f in matrix.db_mapping:
        codes.add(f.field_code)
    for f in matrix.engine_inputs:
        codes.add(f.field_code)
    for f in matrix.market_comparables:
        codes.add(f.field_code)
    for f in matrix.agentic_enrichment:
        codes.add(f.field_code)
    for r in matrix.validation_rules:
        codes.update(r.field_codes)
    for f in matrix.report_disclosure:
        codes.add(f.field_code)
    for f in matrix.output_contract:
        codes.add(f.key)
    return sorted(codes)


def list_fields_by_layer(
    matrix: PurposeIntegrationMatrix,
    layer: str,
) -> list[str]:
    """Return field_codes for a named layer.

    Parameters
    ----------
    layer
        One of: ui_fields, db_mapping, engine_inputs, market_comparables,
        agentic_enrichment, validation_rules, human_approval,
        report_disclosure, output_contract.

    Raises
    ------
    ValueError
        If layer name is not one of the nine layer names.
    """
    if layer not in _NINE_LAYER_NAMES:
        raise ValueError(
            f"Unknown layer {layer!r}. Valid layers: {list(_NINE_LAYER_NAMES)}"
        )

    val = getattr(matrix, layer)

    if layer == "human_approval":
        # Single struct — return its allowed_approval_statuses as context
        return list(val.allowed_approval_statuses)
    if layer == "validation_rules":
        # Return rule_ids
        return [r.rule_id for r in val]
    if layer == "output_contract":
        return [f.key for f in val]
    # All other layers: items have field_code
    return [f.field_code for f in val]


def requires_human_approval(
    matrix: PurposeIntegrationMatrix,
    data: dict[str, Any],
) -> bool:
    """Return True if the supplied data requires human approval before final report.

    Logic
    -----
    If the matrix has human_approval_required_if_auto_enriched=True AND
    data contains is_automated_fill=True (or any agentic enrichment field
    is present with a non-approved status), human approval is required.

    Parameters
    ----------
    data
        A dict of field_code → value representing current submission data.
    """
    if not matrix.human_approval_required_if_auto_enriched:
        return False

    # Explicit auto-fill flag
    if data.get("is_automated_fill") is True:
        return True

    # Any agentic enrichment field present with non-approved status
    approval = data.get("approval_status", "not_required")
    if approval not in ("not_required", "approved"):
        # Check if any enrichment field is present
        enrichment_codes = {ae.field_code for ae in matrix.agentic_enrichment}
        if any(k in enrichment_codes for k in data):
            return True

    return False
