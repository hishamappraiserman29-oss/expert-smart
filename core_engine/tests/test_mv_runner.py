"""
test_mv_runner.py — P1 tests for MassValuationRunner, AuditRecorder, OutputBuilder.
Structural tests only. No valuation logic asserted (values may differ by run).
"""
import pytest
from core_engine.mass_valuation.runner import (
    MassValuationRunner,
    _to_appraisal_unit,
    _sha256_of,
)
from core_engine.mass_valuation.audit_recorder import build_audit_record
from core_engine.mass_valuation.output_builder import OutputBuilder

# ---------------------------------------------------------------------------
# Shared fixtures
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

VALID_RECORD_2 = {
    **VALID_RECORD,
    "property_id":       "PROP-2024-RY-002",
    "transaction_price": 3_200_000,
    "land_area_m2":      800.0,
    "built_up_area_m2":  600.0,
}


# ---------------------------------------------------------------------------
# MassValuationRunner — basic structure
# ---------------------------------------------------------------------------

def test_mv_01_run_returns_run_id():
    runner = MassValuationRunner()
    result = runner.run([VALID_RECORD])
    assert "run_id" in result
    assert len(result["run_id"]) == 36  # UUID


def test_mv_02_advisory_only_invariant():
    runner = MassValuationRunner()
    result = runner.run([VALID_RECORD])
    assert result["advisory_only"] is True
    assert result["certification_ready"] is False


def test_mv_03_n_input_records_correct():
    runner = MassValuationRunner()
    result = runner.run([VALID_RECORD, VALID_RECORD_2])
    assert result["n_input_records"] == 2


def test_mv_04_rejected_count_propagates():
    bad = {**VALID_RECORD, "transaction_price": 0, "property_id": "BAD-001"}
    runner = MassValuationRunner()
    result = runner.run([VALID_RECORD, bad])
    assert result["n_rejected"] == 1


def test_mv_05_empty_input():
    runner = MassValuationRunner()
    result = runner.run([])
    assert result["n_input_records"] == 0
    assert result["n_predicted_properties"] == 0
    assert result["advisory_only"] is True


def test_mv_06_dataset_hash_is_64_hex():
    runner = MassValuationRunner()
    result = runner.run([VALID_RECORD])
    h = result["dataset_hash"]
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_mv_07_dataset_hash_deterministic():
    runner = MassValuationRunner()
    h1 = runner.run([VALID_RECORD])["dataset_hash"]
    h2 = runner.run([VALID_RECORD])["dataset_hash"]
    assert h1 == h2


def test_mv_08_status_is_validated():
    runner = MassValuationRunner()
    result = runner.run([VALID_RECORD])
    assert result["status"] == "validated"


def test_mv_09_predictions_have_advisory_only():
    runner = MassValuationRunner()
    result = runner.run([VALID_RECORD])
    for pred in result.get("predictions", []):
        assert pred["advisory_only"] is True


def test_mv_10_predictions_have_required_fields():
    runner = MassValuationRunner()
    result = runner.run([VALID_RECORD])
    required = {
        "prediction_id", "run_id", "property_id",
        "confidence", "distribution_status", "review_status",
        "advisory_only",
    }
    for pred in result.get("predictions", []):
        for f in required:
            assert f in pred, f"Prediction missing field: {f}"


def test_mv_11_review_status_is_manual_review():
    runner = MassValuationRunner()
    result = runner.run([VALID_RECORD])
    for pred in result.get("predictions", []):
        assert pred["review_status"] == "manual_review_required"


def test_mv_12_configurable_thresholds_do_not_break():
    thresholds = {"cod_max": 20.0, "prd_range": (0.96, 1.04), "prb_range": (-0.10, 0.10)}
    runner = MassValuationRunner(iaao_thresholds=thresholds)
    result = runner.run([VALID_RECORD, VALID_RECORD_2])
    assert result["advisory_only"] is True


def test_mv_13_run_name_in_result():
    runner = MassValuationRunner(run_name="Riyadh Q1 2026")
    result = runner.run([VALID_RECORD])
    assert result["run_name"] == "Riyadh Q1 2026"


def test_mv_14_validation_report_in_result():
    runner = MassValuationRunner()
    result = runner.run([VALID_RECORD])
    vr = result["validation_report"]
    assert "total" in vr
    assert "rejected" in vr


# ---------------------------------------------------------------------------
# _to_appraisal_unit
# ---------------------------------------------------------------------------

def test_mv_15_maps_property_id():
    unit = _to_appraisal_unit(VALID_RECORD)
    assert unit["id"] == "PROP-2024-RY-001"


def test_mv_16_prefers_built_up_area():
    unit = _to_appraisal_unit(VALID_RECORD)
    assert unit["area"] == 450.0


def test_mv_17_falls_back_to_land_area():
    rec = {**VALID_RECORD}
    rec.pop("built_up_area_m2")
    unit = _to_appraisal_unit(rec)
    assert unit["area"] == 600.0


def test_mv_18_year_built_from_age():
    from datetime import datetime, timezone
    unit = _to_appraisal_unit(VALID_RECORD)  # age=8
    expected = datetime.now(timezone.utc).year - 8
    assert unit["year_built"] == expected


def test_mv_19_condition_lowercased():
    rec = {**VALID_RECORD, "condition": "GOOD"}
    unit = _to_appraisal_unit(rec)
    assert unit["condition"] == "good"


def test_mv_20_sale_price_mapped():
    unit = _to_appraisal_unit(VALID_RECORD)
    assert unit["sale_price"] == 2_850_000


# ---------------------------------------------------------------------------
# _sha256_of
# ---------------------------------------------------------------------------

def test_mv_21_sha256_length():
    assert len(_sha256_of({"x": 1})) == 64


def test_mv_22_sha256_stable_on_key_order():
    h1 = _sha256_of({"a": 1, "b": 2})
    h2 = _sha256_of({"b": 2, "a": 1})
    assert h1 == h2


def test_mv_23_sha256_different_inputs_differ():
    assert _sha256_of({"a": 1}) != _sha256_of({"a": 2})


# ---------------------------------------------------------------------------
# AuditRecorder
# ---------------------------------------------------------------------------

def test_mv_24_audit_record_required_fields():
    runner = MassValuationRunner()
    run_result = runner.run([VALID_RECORD])
    record = build_audit_record(run_result, code_commit="abc1234")
    required = [
        "audit_id", "run_id", "dataset_id", "model_id",
        "run_hash", "dataset_hash", "model_hash",
        "code_commit", "feature_schema_hash",
        "hyperparameters", "random_seed",
        "training_period", "validation_strategy",
        "standard_version_id", "created_at",
        "advisory_only", "certification_ready",
    ]
    for f in required:
        assert f in record, f"Audit record missing: {f}"


def test_mv_25_audit_advisory_flags():
    runner = MassValuationRunner()
    run_result = runner.run([VALID_RECORD])
    record = build_audit_record(run_result)
    assert record["advisory_only"] is True
    assert record["certification_ready"] is False


def test_mv_26_audit_hash_lengths():
    runner = MassValuationRunner()
    run_result = runner.run([VALID_RECORD])
    record = build_audit_record(run_result)
    assert len(record["run_hash"]) == 64
    assert len(record["dataset_hash"]) == 64
    assert len(record["feature_schema_hash"]) == 64


def test_mv_27_audit_iaao_metrics_keys():
    runner = MassValuationRunner()
    run_result = runner.run([VALID_RECORD, VALID_RECORD_2])
    record = build_audit_record(run_result)
    iam = record["iaao_metrics"]
    for k in ("cod", "prd", "prb", "r_squared"):
        assert k in iam, f"iaao_metrics missing: {k}"


def test_mv_28_audit_leakage_check_true():
    runner = MassValuationRunner()
    run_result = runner.run([VALID_RECORD])
    record = build_audit_record(run_result)
    assert record["validation_strategy"]["leakage_check"] is True


# ---------------------------------------------------------------------------
# OutputBuilder
# ---------------------------------------------------------------------------

_FULL_PRED = {
    "prediction_id":            "p1",
    "run_id":                   "r1",
    "property_id":              "PROP-001",
    "estimated_value":          1_234_567,
    "unit_value":               2000,
    "prediction_interval_low":  1_000_000,
    "prediction_interval_high": 1_400_000,
    "confidence":               "medium",
    "distribution_status":      "in_distribution",
    "review_status":            "manual_review_required",
    "limitations":              [],
    "advisory_only":            True,
    "shap_values":              {"area": 0.4, "age": -0.2},
    "quality_flags":            [],
    "comparable_ids":           [],
    "model_version":            "hedonic-v1",
}


def test_mv_29_user_hides_shap():
    view = OutputBuilder().filter_prediction(_FULL_PRED, "user")
    assert "shap_values" not in view


def test_mv_30_user_hides_model_version():
    view = OutputBuilder().filter_prediction(_FULL_PRED, "user")
    assert "model_version" not in view


def test_mv_31_user_rounds_estimated_value():
    view = OutputBuilder().filter_prediction(_FULL_PRED, "user")
    assert view["estimated_value"] % 1000 == 0


def test_mv_32_analyst_sees_shap():
    view = OutputBuilder().filter_prediction(_FULL_PRED, "analyst")
    assert "shap_values" in view


def test_mv_33_analyst_sees_model_version():
    view = OutputBuilder().filter_prediction(_FULL_PRED, "analyst")
    assert "model_version" in view


def test_mv_34_admin_sees_everything():
    view = OutputBuilder().filter_prediction(_FULL_PRED, "admin")
    assert "shap_values" in view
    assert "model_version" in view


def test_mv_35_advisory_always_true_in_prediction():
    builder = OutputBuilder()
    for role in ("user", "analyst", "admin"):
        view = builder.filter_prediction(_FULL_PRED, role)
        assert view["advisory_only"] is True, f"advisory_only False for role={role}"


def test_mv_36_unknown_role_treated_as_user():
    view = OutputBuilder().filter_prediction(_FULL_PRED, "superuser")
    assert "shap_values" not in view


def test_mv_37_user_run_hides_dataset_hash():
    runner = MassValuationRunner()
    run_result = runner.run([VALID_RECORD])
    filtered = OutputBuilder().filter_run(run_result, "user")
    assert "dataset_hash" not in filtered


def test_mv_38_admin_run_includes_dataset_hash():
    runner = MassValuationRunner()
    run_result = runner.run([VALID_RECORD])
    filtered = OutputBuilder().filter_run(run_result, "admin")
    assert "dataset_hash" in filtered


def test_mv_39_run_advisory_always_true():
    runner = MassValuationRunner()
    run_result = runner.run([VALID_RECORD])
    for role in ("user", "analyst", "admin"):
        filtered = OutputBuilder().filter_run(run_result, role)
        assert filtered["advisory_only"] is True
        assert filtered["certification_ready"] is False


def test_mv_40_filter_predictions_list():
    builder = OutputBuilder()
    preds = [_FULL_PRED, _FULL_PRED]
    result = builder.filter_predictions_list(preds, "user")
    assert len(result) == 2
    for r in result:
        assert "shap_values" not in r
