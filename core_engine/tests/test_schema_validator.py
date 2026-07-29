"""
test_schema_validator.py — Tests for mass_valuation/contract/schema_validator.py

Structural schema validation only. No valuation logic tested.
"""

import pytest
from core_engine.mass_valuation.contract.schema_validator import SchemaValidator, BatchValidationResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_RECORD = {
    "property_id":       "PROP-2024-RY-001",
    "property_type":     "residential",
    "city":              "Riyadh",
    "district":          "Al Nakheel",
    "land_area_m2":      600.0,
    "built_up_area_m2":  450.0,
    "transaction_date":  "2024-03-15",
    "transaction_price": 2_850_000,
    "evidence_type":     "registered_sale",
    "age":               8,
    "condition":         "good",
    "use":               "owner_occupied",
    "quality_finish":    "high",
    "latitude":          24.7136,
    "longitude":         46.6753,
}


@pytest.fixture
def sv():
    return SchemaValidator()


# ---------------------------------------------------------------------------
# SV-01 → SV-10: Required fields
# ---------------------------------------------------------------------------

def test_sv_01_valid_record_passes(sv):
    """SV-01: A fully valid record produces is_valid=True with no errors."""
    result = sv.validate_record(VALID_RECORD)
    assert result.is_valid is True
    assert result.errors == []


def test_sv_02_missing_property_id_rejected(sv):
    """SV-02: Missing property_id is rejected (QR-001)."""
    rec = {**VALID_RECORD, "property_id": None}
    result = sv.validate_record(rec)
    assert not result.is_valid
    assert any("property_id" in e for e in result.errors)


def test_sv_03_missing_property_type_rejected(sv):
    """SV-03: Missing property_type is rejected (QR-001)."""
    rec = {**VALID_RECORD, "property_type": ""}
    result = sv.validate_record(rec)
    assert not result.is_valid


def test_sv_04_missing_transaction_date_rejected(sv):
    """SV-04: Missing transaction_date is rejected (QR-001)."""
    rec = dict(VALID_RECORD)
    rec.pop("transaction_date")
    result = sv.validate_record(rec)
    assert not result.is_valid


def test_sv_05_missing_transaction_price_rejected(sv):
    """SV-05: Missing transaction_price is rejected (QR-001)."""
    rec = dict(VALID_RECORD)
    rec.pop("transaction_price")
    result = sv.validate_record(rec)
    assert not result.is_valid


def test_sv_06_missing_land_area_rejected(sv):
    """SV-06: Missing land_area_m2 is rejected (QR-001)."""
    rec = dict(VALID_RECORD)
    rec.pop("land_area_m2")
    result = sv.validate_record(rec)
    assert not result.is_valid


# ---------------------------------------------------------------------------
# SV-07 → SV-12: Price validation (QR-004)
# ---------------------------------------------------------------------------

def test_sv_07_zero_price_rejected(sv):
    """SV-07: Zero transaction_price is rejected (QR-004)."""
    rec = {**VALID_RECORD, "transaction_price": 0}
    result = sv.validate_record(rec)
    assert not result.is_valid
    assert any("QR-004" in e for e in result.errors)


def test_sv_08_negative_price_rejected(sv):
    """SV-08: Negative transaction_price is rejected (QR-004)."""
    rec = {**VALID_RECORD, "transaction_price": -100}
    result = sv.validate_record(rec)
    assert not result.is_valid


def test_sv_09_price_below_1000_sar_rejected(sv):
    """SV-09: Price < 1,000 SAR rejected as invalid/currency error (QR-004)."""
    rec = {**VALID_RECORD, "transaction_price": 500}
    result = sv.validate_record(rec)
    assert not result.is_valid


def test_sv_10_valid_price_passes(sv):
    """SV-10: Positive SAR price ≥ 1,000 passes."""
    rec = {**VALID_RECORD, "transaction_price": 1_500_000}
    result = sv.validate_record(rec)
    assert result.is_valid


# ---------------------------------------------------------------------------
# SV-11 → SV-15: Area validation (QR-005)
# ---------------------------------------------------------------------------

def test_sv_11_zero_area_rejected(sv):
    """SV-11: Zero land_area_m2 is rejected (QR-005)."""
    rec = {**VALID_RECORD, "land_area_m2": 0}
    result = sv.validate_record(rec)
    assert not result.is_valid


def test_sv_12_negative_area_rejected(sv):
    """SV-12: Negative land_area_m2 is rejected (QR-005)."""
    rec = {**VALID_RECORD, "land_area_m2": -50}
    result = sv.validate_record(rec)
    assert not result.is_valid


def test_sv_13_very_large_area_warns_not_rejects(sv):
    """SV-13: Very large area (> 10M m²) produces warning but is not rejected."""
    rec = {**VALID_RECORD, "land_area_m2": 15_000_000}
    result = sv.validate_record(rec)
    assert result.is_valid
    assert any("10,000,000" in w for w in result.warnings)


def test_sv_14_non_numeric_area_rejected(sv):
    """SV-14: Non-numeric land_area_m2 is rejected."""
    rec = {**VALID_RECORD, "land_area_m2": "large"}
    result = sv.validate_record(rec)
    assert not result.is_valid


# ---------------------------------------------------------------------------
# SV-15 → SV-20: Coordinates (QR-008, QR-009)
# ---------------------------------------------------------------------------

def test_sv_15_coordinates_outside_saudi_rejected(sv):
    """SV-15: Coordinates outside Saudi bounds are rejected (QR-008)."""
    rec = {**VALID_RECORD, "latitude": 36.0, "longitude": 46.0}
    result = sv.validate_record(rec)
    assert not result.is_valid
    assert any("QR-008" in e for e in result.errors)


def test_sv_16_partial_coordinates_rejected(sv):
    """SV-16: Only latitude provided (no longitude) is rejected (QR-009)."""
    rec = {**VALID_RECORD, "longitude": None}
    result = sv.validate_record(rec)
    assert not result.is_valid
    assert any("QR-009" in e for e in result.errors)


def test_sv_17_both_coordinates_null_passes(sv):
    """SV-17: Both coordinates null is valid (location from city)."""
    rec = {**VALID_RECORD, "latitude": None, "longitude": None}
    result = sv.validate_record(rec)
    assert result.is_valid


def test_sv_18_valid_saudi_coordinates_pass(sv):
    """SV-18: Coordinates within Saudi Arabia bounds pass."""
    rec = {**VALID_RECORD, "latitude": 21.3891, "longitude": 39.8579}
    result = sv.validate_record(rec)
    assert result.is_valid


# ---------------------------------------------------------------------------
# SV-19 → SV-23: Date validation
# ---------------------------------------------------------------------------

def test_sv_19_invalid_date_format_rejected(sv):
    """SV-19: Non-ISO8601 date format is rejected."""
    rec = {**VALID_RECORD, "transaction_date": "15/03/2024"}
    result = sv.validate_record(rec)
    assert not result.is_valid


def test_sv_20_valid_iso_date_passes(sv):
    """SV-20: Valid ISO8601 date passes."""
    rec = {**VALID_RECORD, "transaction_date": "2023-11-30"}
    result = sv.validate_record(rec)
    assert result.is_valid


# ---------------------------------------------------------------------------
# SV-21 → SV-26: Enum validation
# ---------------------------------------------------------------------------

def test_sv_21_invalid_property_type_rejected(sv):
    """SV-21: Unknown property_type is rejected."""
    rec = {**VALID_RECORD, "property_type": "mansion"}
    result = sv.validate_record(rec)
    assert not result.is_valid


def test_sv_22_unknown_condition_warns_not_rejects(sv):
    """SV-22: Unknown condition value produces warning and flag, not rejection."""
    rec = {**VALID_RECORD, "condition": "dilapidated"}
    result = sv.validate_record(rec)
    assert result.is_valid
    assert any("condition" in w for w in result.warnings)
    assert "condition_normalised_to_unknown" in result.flags


def test_sv_23_valid_condition_passes(sv):
    """SV-23: Valid condition 'excellent' passes cleanly."""
    rec = {**VALID_RECORD, "condition": "excellent"}
    result = sv.validate_record(rec)
    assert result.is_valid
    assert result.warnings == []


def test_sv_24_unknown_evidence_type_warns(sv):
    """SV-24: Unknown evidence_type produces warning."""
    rec = {**VALID_RECORD, "evidence_type": "rumour"}
    result = sv.validate_record(rec)
    assert result.is_valid
    assert any("evidence_type" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# SV-25 → SV-30: Occupancy, age, location flags
# ---------------------------------------------------------------------------

def test_sv_25_occupancy_out_of_range_rejected(sv):
    """SV-25: Occupancy > 100 is rejected."""
    rec = {**VALID_RECORD, "occupancy": 110.0}
    result = sv.validate_record(rec)
    assert not result.is_valid


def test_sv_26_negative_occupancy_rejected(sv):
    """SV-26: Negative occupancy is rejected."""
    rec = {**VALID_RECORD, "occupancy": -5.0}
    result = sv.validate_record(rec)
    assert not result.is_valid


def test_sv_27_valid_occupancy_passes(sv):
    """SV-27: Occupancy 85% passes."""
    rec = {**VALID_RECORD, "occupancy": 85.0}
    result = sv.validate_record(rec)
    assert result.is_valid


def test_sv_28_negative_age_rejected(sv):
    """SV-28: Negative age is rejected."""
    rec = {**VALID_RECORD, "age": -3}
    result = sv.validate_record(rec)
    assert not result.is_valid


def test_sv_29_no_city_no_coordinates_flags_review(sv):
    """SV-29: Record with no city and no coordinates is flagged for review (QR-015)."""
    rec = {**VALID_RECORD, "city": None, "latitude": None, "longitude": None}
    result = sv.validate_record(rec)
    assert result.is_valid
    assert "QR-015: both city and coordinates absent — flag_for_review" in result.flags


# ---------------------------------------------------------------------------
# SV-30 → SV-35: Batch validation
# ---------------------------------------------------------------------------

def test_sv_30_batch_all_valid(sv):
    """SV-30: Batch of 3 valid records produces rejected=0, passed=3."""
    records = [VALID_RECORD, VALID_RECORD, VALID_RECORD]
    batch = sv.validate_batch(records)
    assert isinstance(batch, BatchValidationResult)
    assert batch.total == 3
    assert batch.rejected == 0
    assert batch.passed == 3


def test_sv_31_batch_mixed(sv):
    """SV-31: Batch with 1 invalid record produces rejected=1."""
    bad = {**VALID_RECORD, "transaction_price": 0}
    records = [VALID_RECORD, bad, VALID_RECORD]
    batch = sv.validate_batch(records)
    assert batch.total == 3
    assert batch.rejected == 1


def test_sv_32_batch_empty(sv):
    """SV-32: Empty batch returns total=0."""
    batch = sv.validate_batch([])
    assert batch.total == 0
    assert batch.rejected == 0


def test_sv_33_batch_to_dict(sv):
    """SV-33: BatchValidationResult.to_dict() returns expected keys."""
    batch = sv.validate_batch([VALID_RECORD])
    d = batch.to_dict()
    assert "total" in d
    assert "rejected" in d
    assert "flagged" in d
    assert "passed" in d
    assert "records" in d


# ---------------------------------------------------------------------------
# SV-34 → SV-38: Audit trail structural check
# ---------------------------------------------------------------------------

VALID_AUDIT = {
    "audit_id":             "a1b2c3d4-0000-0000-0000-000000000001",
    "run_id":               "a1b2c3d4-0000-0000-0000-000000000002",
    "dataset_id":           "a1b2c3d4-0000-0000-0000-000000000003",
    "model_id":             "avm-hedonic-v1",
    "run_hash":             "a" * 64,
    "dataset_hash":         "b" * 64,
    "model_hash":           "c" * 64,
    "code_commit":          "abc1234",
    "feature_schema_hash":  "d" * 64,
    "hyperparameters":      {"n_estimators": 300, "max_depth": 5},
    "random_seed":          42,
    "training_period":      {"start_date": "2023-01-01", "end_date": "2023-12-31"},
    "validation_strategy":  {"type": "temporal_split", "temporal_holdout": {}, "geographic_holdout": {}},
    "standard_version_id":  "IAAO-2023",
    "created_at":           "2026-07-29T10:00:00Z",
    "advisory_only":        True,
    "certification_ready":  False,
}


def test_sv_34_valid_audit_trail_passes(sv):
    """SV-34: A complete audit trail record passes structural check."""
    ok, errors = sv.validate_audit_trail_required_fields(VALID_AUDIT)
    assert ok is True
    assert errors == []


def test_sv_35_audit_trail_missing_random_seed_fails(sv):
    """SV-35: Audit trail missing random_seed fails."""
    audit = dict(VALID_AUDIT)
    audit.pop("random_seed")
    ok, errors = sv.validate_audit_trail_required_fields(audit)
    assert not ok
    assert any("random_seed" in e for e in errors)


def test_sv_36_audit_trail_advisory_only_false_fails(sv):
    """SV-36: Audit trail with advisory_only=False fails."""
    audit = {**VALID_AUDIT, "advisory_only": False}
    ok, errors = sv.validate_audit_trail_required_fields(audit)
    assert not ok


def test_sv_37_audit_trail_certification_ready_true_fails(sv):
    """SV-37: Audit trail with certification_ready=True fails."""
    audit = {**VALID_AUDIT, "certification_ready": True}
    ok, errors = sv.validate_audit_trail_required_fields(audit)
    assert not ok


# ---------------------------------------------------------------------------
# SV-38 → SV-42: Run state transitions
# ---------------------------------------------------------------------------

def test_sv_38_valid_transition_draft_to_training(sv):
    """SV-38: draft → training is a valid transition."""
    ok, msg = sv.validate_run_state_transition("draft", "training")
    assert ok is True


def test_sv_39_valid_transition_validated_to_approved(sv):
    """SV-39: validated → approved_for_internal_use is valid."""
    ok, msg = sv.validate_run_state_transition("validated", "approved_for_internal_use")
    assert ok is True


def test_sv_40_invalid_transition_draft_to_active_blocked(sv):
    """SV-40: draft → active is not a permitted transition."""
    ok, msg = sv.validate_run_state_transition("draft", "active")
    assert ok is False
    assert "not permitted" in msg


def test_sv_41_archived_is_terminal(sv):
    """SV-41: archived → anything is not permitted (terminal state)."""
    ok, msg = sv.validate_run_state_transition("archived", "active")
    assert ok is False


def test_sv_42_active_cannot_go_to_training(sv):
    """SV-42: active → training is not a permitted transition."""
    ok, msg = sv.validate_run_state_transition("active", "training")
    assert ok is False
