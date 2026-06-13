"""
Tests for the Purpose Integration Matrix — Phase 8.

Matrix safety tests:
  PIM01  — module is importable without any valuation engine or bridge_api
  PIM02  — exactly one matrix currently registered (market_value / market_value_with_habu)
  PIM03  — get_market_value_habu_matrix returns correct identity fields
  PIM04  — matrix contains all nine required layers (non-None, non-empty)
  PIM05  — UI Fields layer contains all required field_codes
  PIM06  — Engine Inputs layer contains all required field_codes
  PIM07  — Market Comparables layer contains the required field_codes
  PIM08  — Agentic Enrichment layer is metadata-only (all fields start as pending review)
  PIM09  — Auto-enriched values are NEVER final-approved by default
  PIM10  — Human Approval spec is correctly defined
  PIM11  — Report Disclosure layer contains required disclosure items
  PIM12  — Output Contract layer contains required output keys
  PIM13  — validate_matrix_definition returns zero errors for the HABU matrix
  PIM14  — list_matrix_fields returns a superset of UI field_codes
  PIM15  — list_fields_by_layer works for each of the nine layers
  PIM16  — list_fields_by_layer raises ValueError for unknown layer
  PIM17  — requires_human_approval: is_automated_fill=True triggers approval
  PIM18  — requires_human_approval: no auto-fill flag → no approval required
  PIM19  — requires_human_approval: pending enrichment field → approval required
  PIM20  — get_purpose_matrix succeeds with correct group/route
  PIM21  — get_purpose_matrix raises ValueError for unknown combination
  PIM22  — list_available_matrices returns the registered pair
  PIM23  — PURPOSE_RULES multipliers/routes/deep flags UNCHANGED (regression)
  PIM24  — purpose_adapter SUPPORTED_PURPOSES still returns 5 keys
  PIM25  — DB Mapping includes governance fields (is_automated_fill, approval_status)
  PIM26  — Validation rules cover all governance constraints
  PIM27  — No agentic enrichment field has default_approval_status == "approved"
  PIM28  — human_approval.auto_enriched_may_be_final_default is False
  PIM29  — APPROVAL_STATUSES constant matches the four expected values
  PIM30  — REPORT_STATUSES constant matches the three expected values
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# ── Path setup ────────────────────────────────────────────────────────────────
_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(str(_CORE))

from adapters.purpose_integration_matrix import (  # noqa: E402
    APPROVAL_STATUSES,
    REPORT_STATUSES,
    AgenticEnrichmentSpec,
    DBFieldSpec,
    EngineInputSpec,
    HumanApprovalSpec,
    MarketComparableSpec,
    OutputContractSpec,
    PurposeIntegrationMatrix,
    ReportDisclosureSpec,
    UIFieldSpec,
    ValidationRule,
    get_market_value_habu_matrix,
    get_purpose_matrix,
    list_available_matrices,
    list_fields_by_layer,
    list_matrix_fields,
    requires_human_approval,
    validate_matrix_definition,
)

_NINE_LAYERS = (
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

# Required UI field codes (from task spec)
_REQUIRED_UI_FIELDS = frozenset({
    "property_id",
    "total_land_area",
    "gps_coordinates",
    "current_use",
    "proposed_habu_use",
    "max_far_allowed",
    "expected_habu_noi",
    "comp_avg_price_m2",
    "comp_adjustment_rate",
    "market_vacancy_rate",
})

# Required engine input codes
_REQUIRED_ENGINE_INPUTS = frozenset({
    "total_land_area",
    "proposed_habu_use",
    "max_far_allowed",
    "expected_habu_noi",
    "comp_avg_price_m2",
    "comp_adjustment_rate",
    "market_vacancy_rate",
})

# Required output contract keys
_REQUIRED_OUTPUT_KEYS = frozenset({
    "valuation_basis",
    "purpose_route",
    "final_value",
    "habu_use",
    "habu_noi",
    "market_value_indication",
    "adjustment_summary",
    "approval_status",
    "report_status",
    "disclosures",
})


# ── PIM01 — Importable without engines ───────────────────────────────────────

def test_PIM01_importable_without_engines():
    """Module imports with no valuation engine or bridge_api dependency."""
    assert PurposeIntegrationMatrix is not None
    assert get_market_value_habu_matrix is not None


# ── PIM02 — Exactly one matrix registered ────────────────────────────────────

def test_PIM02_exactly_one_matrix_registered():
    """Exactly one matrix is registered in Phase 8."""
    matrices = list_available_matrices()
    assert len(matrices) == 1, (
        f"Expected exactly 1 matrix, got {len(matrices)}: {matrices}"
    )
    assert ("market_value", "market_value_with_habu") in matrices


# ── PIM03 — HABU matrix identity fields ──────────────────────────────────────

def test_PIM03_habu_matrix_identity_fields():
    """Market Value HABU matrix has correct identity metadata."""
    m = get_market_value_habu_matrix()
    assert m.purpose_group == "market_value"
    assert m.purpose_route == "market_value_with_habu"
    assert m.name_en == "Market Value based on HABU"
    assert "أعلى وأفضل استغلال" in m.name_ar
    assert m.valuation_basis == "Market Value"
    assert m.default_ifrs_level == "Level 2"
    assert m.human_approval_required_if_auto_enriched is True
    assert m.final_report_allowed_without_human_approval_if_auto_enriched is False


# ── PIM04 — All nine layers present and non-empty ─────────────────────────────

def test_PIM04_all_nine_layers_present():
    """Matrix contains all nine layers, each non-None."""
    m = get_market_value_habu_matrix()
    for layer in _NINE_LAYERS:
        val = getattr(m, layer)
        assert val is not None, f"Layer '{layer}' is None"
        if layer == "human_approval":
            assert isinstance(val, HumanApprovalSpec)
        else:
            assert len(val) >= 1, f"Layer '{layer}' is empty"


# ── PIM05 — UI Fields contains required field_codes ───────────────────────────

def test_PIM05_ui_fields_contains_required():
    """UI Fields layer contains all 10 required field_codes."""
    m = get_market_value_habu_matrix()
    ui_codes = {f.field_code for f in m.ui_fields}
    missing = _REQUIRED_UI_FIELDS - ui_codes
    assert not missing, (
        f"UI Fields missing required field_codes: {sorted(missing)}"
    )


# ── PIM06 — Engine Inputs contains required field_codes ───────────────────────

def test_PIM06_engine_inputs_contains_required():
    """Engine Inputs layer contains all 7 required field_codes."""
    m = get_market_value_habu_matrix()
    engine_codes = {f.field_code for f in m.engine_inputs}
    missing = _REQUIRED_ENGINE_INPUTS - engine_codes
    assert not missing, (
        f"Engine Inputs missing required field_codes: {sorted(missing)}"
    )


# ── PIM07 — Market Comparables contains required fields ───────────────────────

def test_PIM07_market_comparables_contains_required():
    """Market Comparables layer contains the core required comparable fields."""
    m = get_market_value_habu_matrix()
    comp_codes = {f.field_code for f in m.market_comparables}
    required = {"comp_avg_price_m2", "comp_adjustment_rate",
                "comparable_count", "market_vacancy_rate"}
    missing = required - comp_codes
    assert not missing, (
        f"Market Comparables missing: {sorted(missing)}"
    )


# ── PIM08 — Agentic Enrichment is metadata-only ───────────────────────────────

def test_PIM08_agentic_enrichment_metadata_only():
    """Agentic Enrichment layer declares metadata only — all fields default to pending."""
    m = get_market_value_habu_matrix()
    expected_codes = {
        "is_automated_fill", "data_source_log", "confidence_score",
        "source_timestamp", "source_url", "source_type", "approval_status",
    }
    actual_codes = {ae.field_code for ae in m.agentic_enrichment}
    missing = expected_codes - actual_codes
    assert not missing, (
        f"Agentic Enrichment missing field_codes: {sorted(missing)}"
    )
    for ae in m.agentic_enrichment:
        assert ae.requires_human_review is True, (
            f"AgenticEnrichmentSpec '{ae.field_code}' has requires_human_review=False"
        )
        assert ae.default_approval_status != "approved", (
            f"AgenticEnrichmentSpec '{ae.field_code}' defaults to 'approved' — "
            f"auto-enriched values must start as drafts"
        )


# ── PIM09 — Auto-enriched values NEVER final-approved by default ──────────────

def test_PIM09_auto_enriched_never_final_approved_by_default():
    """No agentic enrichment field may have default_approval_status='approved'."""
    m = get_market_value_habu_matrix()
    for ae in m.agentic_enrichment:
        assert ae.default_approval_status != "approved", (
            f"GOVERNANCE VIOLATION: '{ae.field_code}' has "
            f"default_approval_status='approved'. "
            f"Auto-enriched values must start as 'pending_human_review'."
        )
    assert m.human_approval.auto_enriched_may_be_final_default is False, (
        "GOVERNANCE VIOLATION: auto_enriched_may_be_final_default must be False"
    )
    assert m.final_report_allowed_without_human_approval_if_auto_enriched is False, (
        "GOVERNANCE VIOLATION: final_report_allowed_without_human_approval must be False"
    )


# ── PIM10 — Human Approval spec is correctly defined ─────────────────────────

def test_PIM10_human_approval_spec():
    """Human Approval spec encodes correct governance rules."""
    m = get_market_value_habu_matrix()
    ha = m.human_approval
    assert ha.required_if_auto_enriched is True
    assert ha.default_status_for_auto_enriched == "pending_human_review"
    assert ha.report_state_without_approval == "draft_pending_human_review"
    assert ha.auto_enriched_may_be_final_default is False
    for status in ha.allowed_approval_statuses:
        assert status in APPROVAL_STATUSES, (
            f"Unknown approval status: {status!r}"
        )
    # All four statuses must be present
    assert set(ha.allowed_approval_statuses) == APPROVAL_STATUSES


# ── PIM11 — Report Disclosure layer ──────────────────────────────────────────

def test_PIM11_report_disclosure_contains_required():
    """Report Disclosure layer contains required disclosure items."""
    m = get_market_value_habu_matrix()
    disclosure_codes = {rd.field_code for rd in m.report_disclosure}
    required = {"proposed_habu_use", "is_automated_fill",
                "confidence_score", "data_source_log", "approval_status"}
    missing = required - disclosure_codes
    assert not missing, (
        f"Report Disclosure missing: {sorted(missing)}"
    )
    disclose_ifs = {rd.disclose_if for rd in m.report_disclosure}
    assert "always" in disclose_ifs
    assert "if_auto_enriched" in disclose_ifs


# ── PIM12 — Output Contract contains required keys ───────────────────────────

def test_PIM12_output_contract_required_keys():
    """Output Contract layer contains all required output keys."""
    m = get_market_value_habu_matrix()
    actual_keys = {oc.key for oc in m.output_contract}
    missing = _REQUIRED_OUTPUT_KEYS - actual_keys
    assert not missing, (
        f"Output Contract missing keys: {sorted(missing)}"
    )


# ── PIM13 — validate_matrix_definition returns zero errors ───────────────────

def test_PIM13_validate_matrix_definition_zero_errors():
    """validate_matrix_definition returns an empty list for the HABU matrix."""
    m = get_market_value_habu_matrix()
    errors = validate_matrix_definition(m)
    assert errors == [], (
        f"Matrix definition has validation errors:\n" + "\n".join(errors)
    )


# ── PIM14 — list_matrix_fields returns superset of UI codes ──────────────────

def test_PIM14_list_matrix_fields_superset_of_ui():
    """list_matrix_fields returns all unique field codes including all UI codes."""
    m = get_market_value_habu_matrix()
    all_fields = set(list_matrix_fields(m))
    for code in _REQUIRED_UI_FIELDS:
        assert code in all_fields, (
            f"UI field_code '{code}' missing from list_matrix_fields() result"
        )


# ── PIM15 — list_fields_by_layer works for each of the nine layers ────────────

@pytest.mark.parametrize("layer", list(_NINE_LAYERS))
def test_PIM15_list_fields_by_layer(layer):
    """list_fields_by_layer returns a non-empty list for each named layer."""
    m = get_market_value_habu_matrix()
    result = list_fields_by_layer(m, layer)
    assert isinstance(result, list), (
        f"list_fields_by_layer('{layer}') should return a list"
    )
    assert len(result) >= 1, (
        f"list_fields_by_layer('{layer}') returned an empty list"
    )


# ── PIM16 — list_fields_by_layer raises for unknown layer ────────────────────

def test_PIM16_list_fields_by_layer_unknown_raises():
    """list_fields_by_layer raises ValueError for an unrecognised layer name."""
    m = get_market_value_habu_matrix()
    with pytest.raises(ValueError, match="Unknown layer"):
        list_fields_by_layer(m, "nonexistent_layer_xyz")


# ── PIM17 — requires_human_approval: is_automated_fill=True ──────────────────

def test_PIM17_requires_human_approval_automated_fill():
    """requires_human_approval returns True when is_automated_fill=True."""
    m = get_market_value_habu_matrix()
    assert requires_human_approval(m, {"is_automated_fill": True}) is True


# ── PIM18 — requires_human_approval: no auto-fill → False ────────────────────

def test_PIM18_requires_human_approval_no_auto_fill():
    """requires_human_approval returns False when no auto-fill flag and no enrichment."""
    m = get_market_value_habu_matrix()
    data = {
        "property_id": "P001",
        "total_land_area": 500.0,
        "current_use": "vacant",
    }
    assert requires_human_approval(m, data) is False


# ── PIM19 — requires_human_approval: pending enrichment → True ───────────────

def test_PIM19_requires_human_approval_pending_enrichment():
    """requires_human_approval returns True if enrichment field present and not approved."""
    m = get_market_value_habu_matrix()
    data = {
        "confidence_score": 72.5,
        "approval_status": "pending_human_review",
    }
    assert requires_human_approval(m, data) is True


# ── PIM20 — get_purpose_matrix correct ───────────────────────────────────────

def test_PIM20_get_purpose_matrix_correct():
    """get_purpose_matrix returns the correct matrix for the known group/route."""
    m = get_purpose_matrix("market_value", "market_value_with_habu")
    assert m.purpose_group == "market_value"
    assert m.purpose_route == "market_value_with_habu"


# ── PIM21 — get_purpose_matrix raises for unknown ─────────────────────────────

def test_PIM21_get_purpose_matrix_unknown_raises():
    """get_purpose_matrix raises ValueError for an unregistered combination."""
    with pytest.raises(ValueError, match="No integration matrix"):
        get_purpose_matrix("nonexistent_group", "nonexistent_route")


# ── PIM22 — list_available_matrices ──────────────────────────────────────────

def test_PIM22_list_available_matrices():
    """list_available_matrices returns a sorted list with the registered pair."""
    matrices = list_available_matrices()
    assert isinstance(matrices, list)
    assert ("market_value", "market_value_with_habu") in matrices


# ── PIM23 — PURPOSE_RULES UNCHANGED (regression guard) ───────────────────────

def test_PIM23_purpose_rules_unchanged():
    """PURPOSE_RULES multipliers, routes, and deep flags must remain unchanged."""
    from adapters.purpose_adapter import PURPOSE_RULES

    critical = {
        "البيع والشراء - القيمة السوقية العادلة (Market Value)": (1.00, "market_baseline", False),
        "الرهن والتمويل البنكي - القيمة السوقية لأغراض التمويل (0.95x)": (0.95, "financing_risk_haircut", False),
        "التصفية الإجبارية - القيمة التصفوية (Liquidation Value x0.82)": (0.82, "liquidation_distress_discount", False),
        "التأمين - قيمة إعادة الإنشاء (Reinstatement Value x1.08)": (1.08, "insurance_reinstatement_premium", False),
    }
    for label, (exp_mult, exp_route, exp_deep) in critical.items():
        assert label in PURPOSE_RULES, f"PURPOSE_RULES missing: {label!r}"
        rule = PURPOSE_RULES[label]
        assert rule["multiplier"] == exp_mult, (
            f"Multiplier changed for {label!r}: expected {exp_mult}, got {rule['multiplier']}"
        )
        assert rule["route"] == exp_route, (
            f"Route changed for {label!r}: expected {exp_route!r}, got {rule['route']!r}"
        )
        assert bool(rule.get("deep", False)) == exp_deep
    assert len(PURPOSE_RULES) == 14, (
        f"PURPOSE_RULES count changed: expected 14, got {len(PURPOSE_RULES)}"
    )


# ── PIM24 — SUPPORTED_PURPOSES unchanged ─────────────────────────────────────

def test_PIM24_supported_purposes_unchanged():
    """SUPPORTED_PURPOSES still contains exactly 5 entries."""
    from adapters.valuation_requirements import SUPPORTED_PURPOSES
    assert len(SUPPORTED_PURPOSES) == 5, (
        f"SUPPORTED_PURPOSES count changed: expected 5, got {len(SUPPORTED_PURPOSES)}"
    )
    for purpose in ("market_value", "mortgage_lending", "insurance",
                    "liquidation", "investment_analysis"):
        assert purpose in SUPPORTED_PURPOSES


# ── PIM25 — DB Mapping includes governance fields ─────────────────────────────

def test_PIM25_db_mapping_governance_fields():
    """DB Mapping layer includes all required governance/enrichment fields."""
    m = get_market_value_habu_matrix()
    db_codes = {f.field_code for f in m.db_mapping}
    governance = {
        "purpose_route", "is_automated_fill",
        "data_source_log", "confidence_score", "approval_status",
    }
    missing = governance - db_codes
    assert not missing, (
        f"DB Mapping missing governance fields: {sorted(missing)}"
    )
    # is_automated_fill and approval_status must be flagged as fill candidates
    fill_candidates = {
        f.field_code for f in m.db_mapping if f.is_automated_fill_candidate
    }
    for code in ("is_automated_fill", "data_source_log",
                 "confidence_score", "approval_status"):
        assert code in fill_candidates, (
            f"'{code}' should be flagged is_automated_fill_candidate=True"
        )


# ── PIM26 — Validation rules cover governance constraints ─────────────────────

def test_PIM26_validation_rules_governance_coverage():
    """Validation rules include all required governance rule IDs."""
    m = get_market_value_habu_matrix()
    rule_ids = {r.rule_id for r in m.validation_rules}
    required = {
        "VAL_HABU_01",  # total_land_area > 0
        "VAL_HABU_08",  # is_automated_fill → data_source_log required
        "VAL_HABU_09",  # is_automated_fill → approval_status not final_approved
    }
    missing = required - rule_ids
    assert not missing, (
        f"Validation rules missing governance rules: {sorted(missing)}"
    )
    # Rule 09 must protect against auto-final-approval
    rule_09 = next((r for r in m.validation_rules if r.rule_id == "VAL_HABU_09"), None)
    assert rule_09 is not None
    assert "is_automated_fill" in rule_09.field_codes
    assert "approval_status" in rule_09.field_codes


# ── PIM27 — No agentic enrichment field defaults to "approved" ───────────────

def test_PIM27_no_agentic_enrichment_defaults_approved():
    """No AgenticEnrichmentSpec may have default_approval_status == 'approved'."""
    m = get_market_value_habu_matrix()
    for ae in m.agentic_enrichment:
        assert ae.default_approval_status != "approved", (
            f"'{ae.field_code}' defaults to 'approved' — governance violation"
        )


# ── PIM28 — auto_enriched_may_be_final_default is False ──────────────────────

def test_PIM28_auto_enriched_may_be_final_default_false():
    """HumanApprovalSpec.auto_enriched_may_be_final_default must be False."""
    m = get_market_value_habu_matrix()
    assert m.human_approval.auto_enriched_may_be_final_default is False, (
        "GOVERNANCE VIOLATION: auto_enriched_may_be_final_default must be False"
    )


# ── PIM29 — APPROVAL_STATUSES constant ───────────────────────────────────────

def test_PIM29_approval_statuses_constant():
    """APPROVAL_STATUSES contains exactly the four expected values."""
    assert APPROVAL_STATUSES == frozenset({
        "not_required",
        "pending_human_review",
        "approved",
        "rejected",
    })


# ── PIM30 — REPORT_STATUSES constant ─────────────────────────────────────────

def test_PIM30_report_statuses_constant():
    """REPORT_STATUSES contains exactly the three expected values."""
    assert REPORT_STATUSES == frozenset({
        "draft_pending_human_review",
        "ready_for_final",
        "final_approved",
    })
