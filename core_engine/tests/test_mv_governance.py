"""
test_mv_governance.py — P9 tests: Governance (G-01, G-02, G-03, G-04, G-05, G-06, G-08).
Tests: GV-01 → GV-12
"""
import pytest

from core_engine.mass_valuation.runner import (
    MassValuationRunner,
    make_review_decision,
    _audit_trail_complete,
    filter_output_for_role,
    _build_predictions,
    _BASEL_LTV_KEYS,
)


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

_BASE = {
    "property_id":       "P-GOV",
    "property_type":     "residential",
    "city":              "Riyadh",
    "district":          "Al Nakheel",
    "land_area_m2":      300.0,
    "built_up_area_m2":  200.0,
    "transaction_date":  "2023-06-15",
    "transaction_price": 2_000_000,
    "evidence_type":     "registered_sale",
    "age":               5,
    "condition":         "good",
    "use":               "owner_occupied",
    "quality_finish":    "standard",
    "latitude":          24.7136,
    "longitude":         46.6753,
}


# ---------------------------------------------------------------------------
# GV-01 → GV-02  Status never "active" + approval_events (G-01)
# ---------------------------------------------------------------------------

def test_gv_01_run_status_is_never_active():
    """G-01: run() must not produce status='active' — activation requires human approval."""
    result = MassValuationRunner().run([_BASE])
    assert result["status"] != "active", (
        "status must never be 'active' without a human approval_event"
    )
    assert result["status"] == "validated"


def test_gv_02_approval_events_is_empty_list():
    """G-01: approval_events must be an empty list — no automated state transitions."""
    result = MassValuationRunner().run([_BASE])
    assert "approval_events" in result
    assert result["approval_events"] == [], (
        "approval_events must start empty; state changes require human action"
    )


# ---------------------------------------------------------------------------
# GV-03 → GV-04  ReviewDecision (G-02)
# ---------------------------------------------------------------------------

def test_gv_03_review_decision_rejects_system_reviewer():
    """G-02: make_review_decision must raise ValueError when reviewed_by='system'."""
    with pytest.raises(ValueError, match="G-02"):
        make_review_decision(
            prediction_id="pred-001",
            reviewed_by="system",
            decision="accepted",
        )


def test_gv_04_review_decision_accepts_valid_human_reviewer():
    """G-02: make_review_decision succeeds for a non-system reviewer."""
    decision = make_review_decision(
        prediction_id="pred-001",
        reviewed_by="ahmed.ali",
        decision="accepted",
        notes="Verified against field inspection",
    )
    assert decision["reviewed_by"] == "ahmed.ali"
    assert decision["decision"] == "accepted"
    assert decision["prediction_id"] == "pred-001"
    assert "timestamp" in decision


# ---------------------------------------------------------------------------
# GV-05 → GV-06  Audit trail completeness (G-03)
# ---------------------------------------------------------------------------

def test_gv_05_audit_trail_complete_returns_true_for_full_record():
    """G-03: _audit_trail_complete returns True when all required audit fields are present."""
    mock = {
        "run_id":               "r-001",
        "dataset_hash":         "a" * 64,
        "model_hash":           "b" * 64,
        "code_commit":          "abc1234",
        "random_seed":          42,
        "leakage_check":        True,
        "started_at":           "2026-07-30T00:00:00+00:00",
        "advisory_only":        True,
        "certification_ready":  False,
    }
    assert _audit_trail_complete(mock) is True


def test_gv_06_audit_trail_complete_in_run_record():
    """G-03: run record must contain audit_trail_complete=True when all fields present."""
    result = MassValuationRunner().run([_BASE])
    assert "audit_trail_complete" in result
    assert result["audit_trail_complete"] is True


# ---------------------------------------------------------------------------
# GV-07  Property lifecycle (G-04)
# ---------------------------------------------------------------------------

def test_gv_07_property_lifecycle_stages_present_in_prediction():
    """G-04: each prediction must carry property_lifecycle with all required stages."""
    result = MassValuationRunner().run([_BASE])
    assert result["predictions"], "Expected at least one prediction"
    pred = result["predictions"][0]
    assert "property_lifecycle" in pred
    lifecycle = pred["property_lifecycle"]
    required_stages = {
        "stage_ingestion", "stage_quality", "stage_exceptions",
        "stage_review", "stage_decision", "stage_issuance",
    }
    missing = required_stages - lifecycle.keys()
    assert not missing, f"property_lifecycle missing stages: {missing}"
    assert lifecycle["stage_ingestion"] == "completed"
    assert lifecycle["stage_review"] == "manual_review_required"
    assert lifecycle["stage_decision"] is None
    assert lifecycle["stage_issuance"] is None


# ---------------------------------------------------------------------------
# GV-08 → GV-09  insufficient_evidence → null (G-05)
# ---------------------------------------------------------------------------

# unit_value=0 triggers the insufficient_evidence path in _build_predictions.
# We test _build_predictions directly because schema validation rejects
# transaction_price=0 before the runner reaches the prediction stage.
_ZERO_UNIT = {
    "id":         "P-ZERO",
    "unit_value": 0.0,
    "area":       100.0,
    "year_built": 2010,
    "condition":  "good",
    "sale_price": 0.0,
    "final_ppm":  0.0,
}


def test_gv_08_insufficient_evidence_yields_null_estimated_value():
    """G-05: when unit_value=0, _build_predictions must set estimated_value=None (null in DB)."""
    preds = _build_predictions([_ZERO_UNIT], run_id="r-gv08")
    assert preds, "Expected at least one prediction"
    assert preds[0]["estimated_value"] is None, (
        f"estimated_value must be None for insufficient_evidence, got {preds[0]['estimated_value']}"
    )


def test_gv_09_insufficient_evidence_distribution_status():
    """G-05: when unit_value=0, distribution_status must be 'insufficient_evidence'."""
    preds = _build_predictions([_ZERO_UNIT], run_id="r-gv09")
    assert preds[0]["distribution_status"] == "insufficient_evidence"


# ---------------------------------------------------------------------------
# GV-10 → GV-11  advisory_only / certification_ready invariants (G-06)
# ---------------------------------------------------------------------------

def test_gv_10_advisory_only_is_always_true():
    """G-06: advisory_only=True is an invariant on every run record."""
    result = MassValuationRunner().run([_BASE])
    assert result["advisory_only"] is True


def test_gv_11_certification_ready_is_always_false():
    """G-06: certification_ready=False is an invariant on every run record."""
    result = MassValuationRunner().run([_BASE])
    assert result["certification_ready"] is False


# ---------------------------------------------------------------------------
# GV-12  Basel/LTV hidden from user role (G-08)
# ---------------------------------------------------------------------------

def test_gv_12_filter_output_for_role_strips_basel_ltv_for_user():
    """G-08: filter_output_for_role removes all Basel/LTV keys for role='user'."""
    mock_record = {
        "run_id":       "r-001",
        "advisory_only": True,
        "ltv_ratio":    0.75,          # Basel/LTV key — must be stripped
        "ltv_band":     "normal",      # Basel/LTV key — must be stripped
        "capital_requirement": 0.08,   # Basel/LTV key — must be stripped
        "predictions": [
            {
                "prediction_id": "p-001",
                "estimated_value": 2_000_000,
                "ltv":            0.75,   # must be stripped inside predictions
            }
        ],
    }
    filtered = filter_output_for_role(mock_record, role="user")

    # No Basel/LTV keys in top-level output
    for key in _BASEL_LTV_KEYS:
        assert key not in filtered, f"Basel/LTV key '{key}' must not appear for role='user'"

    # No Basel/LTV keys in predictions either
    for pred in filtered.get("predictions", []):
        for key in _BASEL_LTV_KEYS:
            assert key not in pred, (
                f"Basel/LTV key '{key}' must not appear in predictions for role='user'"
            )

    # Non-Basel keys must be preserved
    assert filtered["run_id"] == "r-001"
    assert filtered["predictions"][0]["estimated_value"] == 2_000_000
