"""
test_mv_db.py — P2 tests for db_writer.py.
All DB calls are mocked via MagicMock; no live DB connection needed.
Tests cover: save_run, save_predictions, list_runs, get_predictions_for_run,
save_review_decision, and validator functions.
"""
import pytest
import uuid
from unittest.mock import MagicMock, patch, call

from core_engine.mass_valuation.db_writer import (
    save_run,
    save_predictions,
    list_runs,
    get_predictions_for_run,
    get_run_owner,
    get_prediction_run_id,
    save_review_decision,
    _validate_reviewed_by,
    _validate_decision,
    _validate_reason,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

RUN_ID = str(uuid.uuid4())

SAMPLE_RUN = {
    "run_id":               RUN_ID,
    "run_name":             "Test Run Q1",
    "property_type":        "residential",
    "jurisdiction":         "SA",
    "status":               "validated",
    "method":               "avm",
    "n_input_records":      3,
    "n_rejected":           0,
    "n_flagged":            0,
    "n_training_records":   0,
    "n_predicted_properties": 3,
    "ood_property_count":   0,
    "manual_review_required_count": 3,
    "dataset_hash":         "a" * 64,
    "random_seed":          42,
    "iaao_summary":         {"cod": 10.0, "prd": 1.01, "prb": 0.01},
    "advisory_only":        True,
    "certification_ready":  False,
}

SAMPLE_PRED = {
    "prediction_id":            str(uuid.uuid4()),
    "run_id":                   RUN_ID,
    "property_id":              "PROP-001",
    "estimated_value":          2_500_000,
    "unit_value":               5000,
    "prediction_interval_low":  2_000_000,
    "prediction_interval_high": 3_000_000,
    "confidence":               "medium",
    "distribution_status":      "in_distribution",
    "review_status":            "manual_review_required",
    "model_version":            "hedonic-v1",
    "shap_values":              {"area": 0.4},
    "quality_flags":            [],
    "comparable_ids":           [],
    "limitations":              [],
    "advisory_only":            True,
}


def _make_db(rows=None, raise_on_execute=False):
    """Return a mock SQLAlchemy session."""
    db = MagicMock()
    if raise_on_execute:
        db.execute.side_effect = Exception("DB unavailable")
    else:
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = rows or []
        db.execute.return_value = mock_result
    return db


# ---------------------------------------------------------------------------
# save_run
# ---------------------------------------------------------------------------

def test_db_01_save_run_returns_run_id():
    db = _make_db()
    result = save_run(SAMPLE_RUN, db)
    assert result == RUN_ID


def test_db_02_save_run_commits():
    db = _make_db()
    save_run(SAMPLE_RUN, db)
    db.commit.assert_called_once()


def test_db_03_save_run_returns_none_on_db_error():
    db = _make_db(raise_on_execute=True)
    result = save_run(SAMPLE_RUN, db)
    assert result is None


def test_db_04_save_run_rollback_on_error():
    db = _make_db(raise_on_execute=True)
    save_run(SAMPLE_RUN, db)
    db.rollback.assert_called_once()


def test_db_05_save_run_uses_default_run_name():
    db = _make_db()
    run = {**SAMPLE_RUN, "run_name": None}
    result = save_run(run, db)
    assert result == RUN_ID
    call_kwargs = db.execute.call_args[0][1]
    assert call_kwargs["run_name"] == "Unnamed Run"


# ---------------------------------------------------------------------------
# save_predictions
# ---------------------------------------------------------------------------

def test_db_06_save_predictions_returns_count():
    db = _make_db()
    count = save_predictions([SAMPLE_PRED], RUN_ID, db)
    assert count == 1


def test_db_07_save_predictions_multiple():
    db = _make_db()
    preds = [SAMPLE_PRED, {**SAMPLE_PRED, "prediction_id": str(uuid.uuid4())}]
    count = save_predictions(preds, RUN_ID, db)
    assert count == 2


def test_db_08_save_predictions_zero_on_error():
    db = _make_db(raise_on_execute=True)
    count = save_predictions([SAMPLE_PRED], RUN_ID, db)
    assert count == 0


def test_db_09_save_predictions_empty_list():
    db = _make_db()
    count = save_predictions([], RUN_ID, db)
    assert count == 0


def test_db_10_save_predictions_commits():
    db = _make_db()
    save_predictions([SAMPLE_PRED], RUN_ID, db)
    db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# list_runs
# ---------------------------------------------------------------------------

def test_db_11_list_runs_returns_list():
    rows = [{"run_id": RUN_ID, "advisory_only": True, "certification_ready": False,
             "status": "validated", "run_name": "Test", "property_type": "residential",
             "jurisdiction": "SA", "method": "avm", "n_input_records": 1,
             "n_rejected": 0, "n_predicted_properties": 1, "started_at": "2026-01-01"}]
    db = _make_db(rows=rows)
    result = list_runs(db, role="analyst")
    assert len(result) == 1
    assert result[0]["run_id"] == RUN_ID


def test_db_12_list_runs_empty_on_error():
    db = _make_db(raise_on_execute=True)
    result = list_runs(db)
    assert result == []


def test_db_13_list_runs_enforces_advisory_only():
    rows = [{"run_id": RUN_ID, "advisory_only": False, "certification_ready": True,
             "status": "validated", "run_name": "T", "property_type": "residential",
             "jurisdiction": "SA", "method": "avm", "n_input_records": 0,
             "n_rejected": 0, "n_predicted_properties": 0, "started_at": "2026-01-01"}]
    db = _make_db(rows=rows)
    result = list_runs(db)
    assert result[0]["advisory_only"] is True
    assert result[0]["certification_ready"] is False


def test_db_14_list_runs_parses_iaao_json():
    iaao_str = '{"cod": 12.0, "prd": 1.02}'
    rows = [{"run_id": RUN_ID, "advisory_only": True, "certification_ready": False,
             "status": "validated", "run_name": "T", "property_type": "residential",
             "jurisdiction": "SA", "method": "avm", "n_input_records": 0,
             "n_rejected": 0, "n_predicted_properties": 0, "started_at": "2026-01-01",
             "iaao_summary": iaao_str, "n_flagged": 0,
             "ood_property_count": 0, "manual_review_required_count": 0}]
    db = _make_db(rows=rows)
    result = list_runs(db, role="analyst")
    assert isinstance(result[0]["iaao_summary"], dict)
    assert result[0]["iaao_summary"]["cod"] == 12.0


# ---------------------------------------------------------------------------
# get_predictions_for_run
# ---------------------------------------------------------------------------

def test_db_15_get_predictions_returns_list():
    rows = [{
        "prediction_id": SAMPLE_PRED["prediction_id"],
        "run_id": RUN_ID, "property_id": "PROP-001",
        "estimated_value": 2500000, "unit_value": 5000,
        "prediction_interval_low": 2000000, "prediction_interval_high": 3000000,
        "confidence": "medium", "distribution_status": "in_distribution",
        "review_status": "manual_review_required", "model_version": "hedonic-v1",
        "shap_values": '{"area": 0.4}', "quality_flags": "[]",
        "comparable_ids": "[]", "limitations": "[]", "advisory_only": True,
    }]
    db = _make_db(rows=rows)
    result = get_predictions_for_run(RUN_ID, db)
    assert len(result) == 1
    assert result[0]["advisory_only"] is True


def test_db_16_get_predictions_parses_shap_json():
    rows = [{
        "prediction_id": SAMPLE_PRED["prediction_id"],
        "run_id": RUN_ID, "property_id": "PROP-001",
        "estimated_value": None, "unit_value": None,
        "prediction_interval_low": None, "prediction_interval_high": None,
        "confidence": "low", "distribution_status": "unknown",
        "review_status": "manual_review_required", "model_version": "hedonic-v1",
        "shap_values": '{"area": 0.3, "age": -0.1}',
        "quality_flags": "[]", "comparable_ids": "[]", "limitations": "[]",
        "advisory_only": True,
    }]
    db = _make_db(rows=rows)
    result = get_predictions_for_run(RUN_ID, db)
    assert isinstance(result[0]["shap_values"], dict)
    assert result[0]["shap_values"]["area"] == 0.3


def test_db_17_get_predictions_empty_on_error():
    db = _make_db(raise_on_execute=True)
    result = get_predictions_for_run(RUN_ID, db)
    assert result == []


# ---------------------------------------------------------------------------
# save_review_decision — validator tests
# ---------------------------------------------------------------------------

def test_db_18_validate_reviewed_by_rejects_system():
    with pytest.raises(ValueError, match="system"):
        _validate_reviewed_by("system")


def test_db_19_validate_reviewed_by_accepts_human():
    _validate_reviewed_by("analyst-001")  # should not raise


def test_db_20_validate_decision_rejects_unknown():
    with pytest.raises(ValueError, match="decision"):
        _validate_decision("approve")


def test_db_21_validate_decision_accepts_valid():
    for d in ("accepted", "overridden", "rejected"):
        _validate_decision(d)  # should not raise


def test_db_22_validate_reason_rejects_empty():
    with pytest.raises(ValueError, match="reason"):
        _validate_reason("")


def test_db_23_validate_reason_rejects_whitespace():
    with pytest.raises(ValueError, match="reason"):
        _validate_reason("   ")


# ---------------------------------------------------------------------------
# save_review_decision — DB operations
# ---------------------------------------------------------------------------

def test_db_24_save_review_raises_before_db_on_system_reviewer():
    db = _make_db()
    with pytest.raises(ValueError, match="system"):
        save_review_decision("pred-1", RUN_ID, "accepted", "looks good", "system", db)
    db.execute.assert_not_called()


def test_db_25_save_review_returns_uuid():
    db = _make_db()
    decision_id = save_review_decision(
        "pred-1", RUN_ID, "accepted", "Verified against market data",
        "analyst-ali", db,
    )
    assert decision_id is not None
    assert len(decision_id) == 36


def test_db_26_save_review_returns_none_on_db_error():
    db = _make_db(raise_on_execute=True)
    result = save_review_decision(
        "pred-1", RUN_ID, "rejected", "Outside acceptable range",
        "analyst-sara", db,
    )
    assert result is None


def test_db_27_save_review_commits():
    db = _make_db()
    save_review_decision(
        "pred-1", RUN_ID, "overridden", "Adjusted based on site inspection",
        "analyst-kim", db, reviewed_value=2_800_000,
    )
    db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# Wave 4B2 — provenance round-trip (model_hash, ood_backend, currency,
# created_by, source_method, ood_score)
# ---------------------------------------------------------------------------

def test_db_28_save_run_persists_model_hash():
    db = _make_db()
    run = {**SAMPLE_RUN, "model_hash": "f" * 64}
    save_run(run, db)
    call_kwargs = db.execute.call_args[0][1]
    assert call_kwargs["model_hash"] == "f" * 64


def test_db_29_save_run_persists_ood_backend():
    db = _make_db()
    run = {**SAMPLE_RUN, "ood_backend": "isolation_forest"}
    save_run(run, db)
    call_kwargs = db.execute.call_args[0][1]
    assert call_kwargs["ood_backend"] == "isolation_forest"


def test_db_30_save_run_persists_created_by():
    db = _make_db()
    run = {**SAMPLE_RUN, "created_by": "admin-a-wave4b2"}
    save_run(run, db)
    call_kwargs = db.execute.call_args[0][1]
    assert call_kwargs["created_by"] == "admin-a-wave4b2"


def test_db_31_save_run_created_by_defaults_to_none():
    db = _make_db()
    save_run(SAMPLE_RUN, db)
    call_kwargs = db.execute.call_args[0][1]
    assert call_kwargs["created_by"] is None


def test_db_32_save_run_currency_defaults_to_sar():
    db = _make_db()
    save_run(SAMPLE_RUN, db)
    call_kwargs = db.execute.call_args[0][1]
    assert call_kwargs["currency"] == "SAR"


def test_db_33_save_run_persists_explicit_currency():
    db = _make_db()
    run = {**SAMPLE_RUN, "currency": "SAR"}
    save_run(run, db)
    call_kwargs = db.execute.call_args[0][1]
    assert call_kwargs["currency"] == "SAR"


def test_db_34_save_predictions_persists_source_method():
    db = _make_db()
    pred = {**SAMPLE_PRED, "source_method": "avm"}
    save_predictions([pred], RUN_ID, db)
    call_kwargs = db.execute.call_args[0][1]
    assert call_kwargs["source_method"] == "avm"


def test_db_35_save_predictions_persists_ood_score():
    db = _make_db()
    pred = {**SAMPLE_PRED, "ood_score": 0.87}
    save_predictions([pred], RUN_ID, db)
    call_kwargs = db.execute.call_args[0][1]
    assert call_kwargs["ood_score"] == 0.87


def test_db_36_list_runs_owner_scoping_adds_where_clause():
    db = _make_db(rows=[])
    list_runs(db, role="admin", owner_user_id="admin-a-wave4b2")
    sql_text = str(db.execute.call_args[0][0])
    call_params = db.execute.call_args[0][1]
    assert "created_by = :owner_user_id" in sql_text
    assert call_params["owner_user_id"] == "admin-a-wave4b2"


def test_db_37_list_runs_no_owner_scoping_when_unset():
    db = _make_db(rows=[])
    list_runs(db, role="admin")
    sql_text = str(db.execute.call_args[0][0])
    call_params = db.execute.call_args[0][1]
    assert "created_by = :owner_user_id" not in sql_text
    assert "owner_user_id" not in call_params


def test_db_38_list_runs_admin_role_includes_provenance_columns():
    db = _make_db(rows=[])
    list_runs(db, role="admin", owner_user_id="admin-a-wave4b2")
    sql_text = str(db.execute.call_args[0][0])
    for col in ("model_hash", "ood_backend", "created_by"):
        assert col in sql_text


def test_db_39_get_predictions_for_run_selects_provenance_columns():
    db = _make_db(rows=[])
    get_predictions_for_run(RUN_ID, db)
    sql_text = str(db.execute.call_args[0][0])
    assert "source_method" in sql_text
    assert "ood_score" in sql_text


# ---------------------------------------------------------------------------
# Wave 4B2 — ownership lookups (get_run_owner, get_prediction_run_id)
# ---------------------------------------------------------------------------

def test_db_40_get_run_owner_returns_created_by():
    db = MagicMock()
    db.execute.return_value.mappings.return_value.first.return_value = {
        "created_by": "admin-a-wave4b2"
    }
    assert get_run_owner(RUN_ID, db) == "admin-a-wave4b2"


def test_db_41_get_run_owner_returns_none_for_unknown_run():
    db = MagicMock()
    db.execute.return_value.mappings.return_value.first.return_value = None
    assert get_run_owner("unknown-run", db) is None


def test_db_42_get_run_owner_returns_none_on_db_error():
    db = _make_db(raise_on_execute=True)
    assert get_run_owner(RUN_ID, db) is None


def test_db_43_get_prediction_run_id_returns_run_id():
    db = MagicMock()
    db.execute.return_value.mappings.return_value.first.return_value = {"run_id": RUN_ID}
    assert get_prediction_run_id("pred-1", db) == RUN_ID


def test_db_44_get_prediction_run_id_returns_none_for_unknown_prediction():
    db = MagicMock()
    db.execute.return_value.mappings.return_value.first.return_value = None
    assert get_prediction_run_id("unknown-pred", db) is None


def test_db_45_get_prediction_run_id_returns_none_on_db_error():
    db = _make_db(raise_on_execute=True)
    assert get_prediction_run_id("pred-1", db) is None
