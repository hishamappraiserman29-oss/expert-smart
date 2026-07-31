"""
test_mv_reproducibility.py — P11 tests: Reproducibility (R-01, R-02) + Holdout (D-05).
Tests: RP-01 → RP-09
"""
import uuid as _uuid_module

import pytest

from core_engine.mass_valuation.runner import MassValuationRunner


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

_BASE = {
    "property_id":       "P-RP",
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

_REC_BEFORE = {**_BASE, "property_id": "P-TRAIN", "transaction_date": "2023-06-15"}
_REC_AFTER  = {**_BASE, "property_id": "P-VAL",   "transaction_date": "2024-06-15"}
_REC_JEDDAH = {
    **_BASE,
    "property_id": "P-HOLDOUT",
    "city":        "Jeddah",
    "district":    "Al Hamra",
}
_CUTOFF = "2023-12-31"


# ---------------------------------------------------------------------------
# RP-01 → RP-05  Determinism (R-01)
# ---------------------------------------------------------------------------

def test_rp_01_same_data_same_seed_same_dataset_hash():
    """R-01: dataset_hash must be identical across two runs with the same inputs."""
    r1 = MassValuationRunner(random_seed=42).run([_BASE])
    r2 = MassValuationRunner(random_seed=42).run([_BASE])
    assert r1["dataset_hash"] == r2["dataset_hash"], (
        "dataset_hash must be deterministic for identical input records"
    )


def test_rp_02_same_data_same_seed_same_model_hash():
    """R-01: model_hash must be identical across two runs with the same seed and data."""
    r1 = MassValuationRunner(random_seed=42).run([_BASE])
    r2 = MassValuationRunner(random_seed=42).run([_BASE])
    assert r1["model_hash"] == r2["model_hash"], (
        "model_hash must be deterministic — same training data + same seed → same hash"
    )


def test_rp_03_same_data_same_seed_same_estimated_values():
    """R-01: estimated_value in every prediction must be identical across re-runs."""
    r1 = MassValuationRunner(random_seed=42).run([_BASE])
    r2 = MassValuationRunner(random_seed=42).run([_BASE])
    vals1 = [p["estimated_value"] for p in r1["predictions"]]
    vals2 = [p["estimated_value"] for p in r2["predictions"]]
    assert vals1 == vals2, (
        f"estimated_values must be reproducible; got {vals1} vs {vals2}"
    )


def test_rp_04_different_seed_produces_different_model_hash():
    """R-01: random_seed is part of the model_hash input — different seeds → different hashes."""
    r1 = MassValuationRunner(random_seed=42).run([_BASE])
    r2 = MassValuationRunner(random_seed=99).run([_BASE])
    assert r1["model_hash"] != r2["model_hash"], (
        "model_hash must encode random_seed — different seeds must not collide"
    )


def test_rp_05_different_data_produces_different_dataset_hash():
    """R-01: dataset_hash must differ when the input property records differ."""
    _OTHER = {**_BASE, "property_id": "P-DIFF", "transaction_price": 3_000_000}
    r1 = MassValuationRunner(random_seed=42).run([_BASE])
    r2 = MassValuationRunner(random_seed=42).run([_OTHER])
    assert r1["dataset_hash"] != r2["dataset_hash"], (
        "dataset_hash must change when input records change"
    )


# ---------------------------------------------------------------------------
# RP-06 → RP-07  run_id uniqueness and format (R-02)
# ---------------------------------------------------------------------------

def test_rp_06_run_id_is_unique_across_runs():
    """R-02: Each invocation must produce a distinct run_id — no duplicates."""
    run_ids = {MassValuationRunner(random_seed=42).run([_BASE])["run_id"] for _ in range(5)}
    assert len(run_ids) == 5, (
        "run_id must be unique on every invocation; found duplicates"
    )


def test_rp_07_run_id_is_valid_uuid4():
    """R-02: run_id must be a properly formatted UUID4 string."""
    result  = MassValuationRunner(random_seed=42).run([_BASE])
    run_id  = result["run_id"]
    parsed  = _uuid_module.UUID(run_id, version=4)
    assert str(parsed) == run_id, (
        f"run_id {run_id!r} is not a valid UUID4 string"
    )


# ---------------------------------------------------------------------------
# RP-08 → RP-09  Holdout integrity (D-05)
# ---------------------------------------------------------------------------

def test_rp_08_validation_property_ids_not_in_training_predictions():
    """
    D-05: After a temporal split, properties assigned to validation must NOT
    appear in training predictions — they are held out for evaluation only.
    """
    result = MassValuationRunner(random_seed=42).run(
        [_REC_BEFORE, _REC_AFTER],
        cutoff_date=_CUTOFF,
    )
    assert result["n_training_records"]   == 1, (
        f"Expected 1 training record, got {result['n_training_records']}"
    )
    assert result["n_validation_records"] == 1, (
        f"Expected 1 validation record, got {result['n_validation_records']}"
    )
    assert result["leakage_found"] is False, (
        "leakage_found must be False when train/val sets are disjoint"
    )
    pred_property_ids = {p["property_id"] for p in result["predictions"]}
    assert "P-VAL" not in pred_property_ids, (
        "D-05: validation property P-VAL must not appear in training predictions"
    )


def test_rp_09_holdout_city_properties_not_in_training_predictions():
    """
    D-05: Properties in holdout cities must not appear in training predictions —
    geographic holdout enforces the same integrity guarantee as temporal holdout.
    """
    result = MassValuationRunner(random_seed=42).run(
        [_BASE, _REC_JEDDAH],
        holdout_cities=["Jeddah"],
    )
    assert result["n_training_records"] == 1, (
        f"Expected 1 training record, got {result['n_training_records']}"
    )
    assert result["n_holdout_records"]  == 1, (
        f"Expected 1 holdout record, got {result['n_holdout_records']}"
    )
    assert result["leakage_found"] is False
    pred_property_ids = {p["property_id"] for p in result["predictions"]}
    assert "P-HOLDOUT" not in pred_property_ids, (
        "D-05: holdout property P-HOLDOUT must not appear in training predictions"
    )
