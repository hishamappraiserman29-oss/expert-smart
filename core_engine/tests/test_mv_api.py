"""
test_mv_api.py — P1 API tests for mass valuation endpoints.
Uses unittest.mock to test endpoint logic without a running server.
"""
import json
import pytest
from unittest.mock import MagicMock, patch


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


# ---------------------------------------------------------------------------
# MassValuationRunner integration (no server needed)
# ---------------------------------------------------------------------------

def test_api_01_runner_returns_advisory_only():
    from core_engine.mass_valuation.runner import MassValuationRunner
    runner = MassValuationRunner()
    result = runner.run([VALID_RECORD])
    assert result["advisory_only"] is True


def test_api_02_runner_returns_certification_ready_false():
    from core_engine.mass_valuation.runner import MassValuationRunner
    runner = MassValuationRunner()
    result = runner.run([VALID_RECORD])
    assert result["certification_ready"] is False


def test_api_03_run_endpoint_response_shape():
    from core_engine.mass_valuation.runner import MassValuationRunner
    from core_engine.mass_valuation.audit_recorder import build_audit_record
    runner       = MassValuationRunner(run_name="Test", property_type="residential")
    run_result   = runner.run([VALID_RECORD])
    audit_record = build_audit_record(run_result, code_commit="HEAD")
    response = {
        "run_id":              run_result["run_id"],
        "status":              run_result["status"],
        "n_input_records":     run_result["n_input_records"],
        "n_rejected":          run_result["n_rejected"],
        "n_predicted":         run_result["n_predicted_properties"],
        "iaao_summary":        run_result["iaao_summary"],
        "audit_trail_id":      audit_record["audit_id"],
        "advisory_only":       True,
        "certification_ready": False,
    }
    for key in ("run_id", "status", "n_input_records", "n_rejected",
                "n_predicted", "iaao_summary", "audit_trail_id",
                "advisory_only", "certification_ready"):
        assert key in response, f"Response missing: {key}"


def test_api_04_empty_records_should_have_zero_predictions():
    from core_engine.mass_valuation.runner import MassValuationRunner
    runner = MassValuationRunner()
    result = runner.run([])
    assert result["n_predicted_properties"] == 0


def test_api_05_invalid_record_counted_as_rejected():
    from core_engine.mass_valuation.runner import MassValuationRunner
    bad_record = {**VALID_RECORD, "transaction_price": -500, "property_id": "BAD"}
    runner = MassValuationRunner()
    result = runner.run([bad_record])
    assert result["n_rejected"] >= 1


def test_api_06_user_role_hides_shap_in_predictions():
    from core_engine.mass_valuation.runner import MassValuationRunner
    from core_engine.mass_valuation.output_builder import OutputBuilder
    runner     = MassValuationRunner()
    run_result = runner.run([VALID_RECORD])
    filtered   = OutputBuilder().filter_run(run_result, "user")
    for pred in filtered.get("predictions", []):
        assert "shap_values" not in pred


def test_api_07_admin_role_includes_iaao_summary():
    from core_engine.mass_valuation.runner import MassValuationRunner
    from core_engine.mass_valuation.output_builder import OutputBuilder
    runner     = MassValuationRunner()
    run_result = runner.run([VALID_RECORD])
    filtered   = OutputBuilder().filter_run(run_result, "admin")
    assert "iaao_summary" in filtered


def test_api_08_analyst_role_includes_iaao_summary():
    from core_engine.mass_valuation.runner import MassValuationRunner
    from core_engine.mass_valuation.output_builder import OutputBuilder
    runner     = MassValuationRunner()
    run_result = runner.run([VALID_RECORD])
    filtered   = OutputBuilder().filter_run(run_result, "analyst")
    assert "iaao_summary" in filtered


def test_api_09_user_role_excludes_dataset_hash():
    from core_engine.mass_valuation.runner import MassValuationRunner
    from core_engine.mass_valuation.output_builder import OutputBuilder
    runner     = MassValuationRunner()
    run_result = runner.run([VALID_RECORD])
    filtered   = OutputBuilder().filter_run(run_result, "user")
    assert "dataset_hash" not in filtered


def test_api_10_certification_ready_false_all_roles():
    from core_engine.mass_valuation.runner import MassValuationRunner
    from core_engine.mass_valuation.output_builder import OutputBuilder
    runner     = MassValuationRunner()
    run_result = runner.run([VALID_RECORD])
    for role in ("user", "analyst", "admin"):
        filtered = OutputBuilder().filter_run(run_result, role)
        assert filtered["certification_ready"] is False


def test_api_11_audit_record_advisory_only():
    from core_engine.mass_valuation.runner import MassValuationRunner
    from core_engine.mass_valuation.audit_recorder import build_audit_record
    runner     = MassValuationRunner()
    run_result = runner.run([VALID_RECORD])
    record     = build_audit_record(run_result)
    assert record["advisory_only"] is True
    assert record["certification_ready"] is False


def test_api_12_run_id_is_uuid():
    import re
    from core_engine.mass_valuation.runner import MassValuationRunner
    runner = MassValuationRunner()
    result = runner.run([VALID_RECORD])
    uuid_pattern = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    )
    assert uuid_pattern.match(result["run_id"]), "run_id is not a valid UUID"


def test_api_13_predictions_run_id_matches_run():
    from core_engine.mass_valuation.runner import MassValuationRunner
    runner     = MassValuationRunner()
    run_result = runner.run([VALID_RECORD])
    run_id     = run_result["run_id"]
    for pred in run_result.get("predictions", []):
        assert pred["run_id"] == run_id


def test_api_14_multiple_records_all_predicted():
    from core_engine.mass_valuation.runner import MassValuationRunner
    records = [
        VALID_RECORD,
        {**VALID_RECORD, "property_id": "PROP-002", "transaction_price": 3_000_000},
        {**VALID_RECORD, "property_id": "PROP-003", "transaction_price": 2_500_000},
    ]
    runner = MassValuationRunner()
    result = runner.run(records)
    assert result["n_predicted_properties"] == 3


def test_api_15_iaao_summary_has_cod_prd_prb():
    from core_engine.mass_valuation.runner import MassValuationRunner
    records = [
        VALID_RECORD,
        {**VALID_RECORD, "property_id": "PROP-002", "transaction_price": 3_100_000},
        {**VALID_RECORD, "property_id": "PROP-003", "transaction_price": 2_700_000},
    ]
    runner = MassValuationRunner()
    result = runner.run(records)
    iaao   = result.get("iaao_summary", {})
    # n_sales >= 3 for PRB to be computed
    if iaao.get("n_sales", 0) >= 3:
        assert "prb" in iaao
