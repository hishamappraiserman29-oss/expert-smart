"""
test_mv_data_splits.py — P6 tests: Data Splits (D-06, D-07) + Reproducibility (R-02, R-05).
Tests: DS-01 → DS-12
"""
import pytest

from core_engine.mass_valuation.data_splitter import temporal_split, geographic_split
from core_engine.mass_valuation.runner import MassValuationRunner, _compute_model_hash


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

_BASE = {
    "property_id":      "P-BASE",
    "property_type":    "residential",
    "city":             "Riyadh",
    "district":         "Al Nakheel",
    "land_area_m2":     300.0,
    "built_up_area_m2": 200.0,
    "transaction_date": "2023-06-15",
    "transaction_price": 2_000_000,
    "evidence_type":    "registered_sale",
    "age":              5,
    "condition":        "good",
    "use":              "owner_occupied",
    "quality_finish":   "standard",
    "latitude":         24.7136,
    "longitude":        46.6753,
}

# Records in different periods / cities
_REC_2023    = {**_BASE, "property_id": "P-2023", "transaction_date": "2023-06-15"}
_REC_2024    = {**_BASE, "property_id": "P-2024", "transaction_date": "2024-06-15"}
_REC_CUTOFF  = {**_BASE, "property_id": "P-CUTOFF", "transaction_date": "2023-12-31"}
_REC_NODATE  = {**_BASE, "property_id": "P-NODATE", "transaction_date": None}
_REC_JEDDAH  = {**_BASE, "property_id": "P-JED",   "city": "Jeddah",  "district": "Al Hamra"}
_REC_MAKKAH  = {**_BASE, "property_id": "P-MAK",   "city": "Makkah",  "district": "Al Aziziyah"}

_CUTOFF = "2023-12-31"


# ---------------------------------------------------------------------------
# DS-01 → DS-04  temporal_split (D-06)
# ---------------------------------------------------------------------------

def test_ds_01_records_before_cutoff_in_train():
    """Records with transaction_date on/before cutoff → training set."""
    train, val = temporal_split([_REC_2023], _CUTOFF)
    assert len(train) == 1 and len(val) == 0


def test_ds_02_records_after_cutoff_in_validation():
    """Records with transaction_date strictly after cutoff → validation set."""
    train, val = temporal_split([_REC_2024], _CUTOFF)
    assert len(train) == 0 and len(val) == 1


def test_ds_03_record_on_cutoff_date_goes_to_train():
    """Record whose date equals the cutoff → training (boundary inclusive)."""
    train, val = temporal_split([_REC_CUTOFF], _CUTOFF)
    assert len(train) == 1 and len(val) == 0


def test_ds_04_record_without_date_defaults_to_train():
    """Record with no transaction_date → training (safe default)."""
    train, val = temporal_split([_REC_NODATE], _CUTOFF)
    assert len(train) == 1 and len(val) == 0


# ---------------------------------------------------------------------------
# DS-05 → DS-08  geographic_split (D-07)
# ---------------------------------------------------------------------------

def test_ds_05_holdout_city_record_goes_to_holdout():
    """Record whose city matches holdout list → holdout set."""
    train, holdout = geographic_split([_REC_JEDDAH], ["Jeddah"])
    assert len(holdout) == 1 and len(train) == 0


def test_ds_06_geographic_split_is_case_insensitive():
    """Holdout matching must be case-insensitive."""
    _, holdout_lower = geographic_split([_REC_JEDDAH], ["jeddah"])
    _, holdout_upper = geographic_split([_REC_JEDDAH], ["JEDDAH"])
    assert len(holdout_lower) == 1
    assert len(holdout_upper) == 1


def test_ds_07_empty_holdout_list_puts_all_in_train():
    """Empty holdout_cities → all records in training."""
    records = [_REC_2023, _REC_JEDDAH]
    train, holdout = geographic_split(records, [])
    assert len(train) == 2 and len(holdout) == 0


def test_ds_08_train_does_not_contain_holdout_city():
    """Holdout city must be fully absent from training set."""
    records = [_REC_2023, _REC_JEDDAH, _REC_MAKKAH]
    train, holdout = geographic_split(records, ["Jeddah", "Makkah"])
    train_ids = {r["property_id"] for r in train}
    assert "P-JED" not in train_ids
    assert "P-MAK" not in train_ids
    assert "P-2023" in train_ids


# ---------------------------------------------------------------------------
# DS-09 → DS-11  model_hash (R-02)
# ---------------------------------------------------------------------------

def test_ds_09_model_hash_present_and_is_sha256():
    """Run record must include model_hash — a 64-char hex string (SHA-256)."""
    result = MassValuationRunner().run([_REC_2023])
    assert "model_hash" in result
    h = result["model_hash"]
    assert isinstance(h, str) and len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_ds_10_same_inputs_produce_same_model_hash():
    """R-02 / R-05: identical seed + identical data → identical model_hash."""
    runner = MassValuationRunner(random_seed=42)
    r1 = runner.run([_REC_2023])
    r2 = runner.run([_REC_2023])
    assert r1["model_hash"] == r2["model_hash"]


def test_ds_11_different_seed_produces_different_model_hash():
    """Changing random_seed must change model_hash (seed is part of model identity)."""
    h1 = MassValuationRunner(random_seed=42).run([_REC_2023])["model_hash"]
    h2 = MassValuationRunner(random_seed=99).run([_REC_2023])["model_hash"]
    assert h1 != h2


# ---------------------------------------------------------------------------
# DS-12  Integration — runner honours cutoff_date + holdout_cities (D-06, D-07)
# ---------------------------------------------------------------------------

def test_ds_12_runner_splits_are_reflected_in_run_record():
    """
    Runner with cutoff_date + holdout_cities must report correct
    n_validation_records and n_holdout_records in the run result.

    Records:
      _REC_2023   — city=Riyadh, date=2023-06-15 → train (before cutoff, not holdout)
      _REC_2024   — city=Riyadh, date=2024-06-15 → validation (after cutoff)
      _REC_JEDDAH — city=Jeddah, date=2023-06-15 → holdout (after temporal→ train, then geo→ holdout)
    """
    records = [_REC_2023, _REC_2024, _REC_JEDDAH]
    result  = MassValuationRunner().run(
        records,
        cutoff_date="2023-12-31",
        holdout_cities=["Jeddah"],
    )
    assert result["n_validation_records"] == 1, (
        f"Expected 1 validation record (_REC_2024), got {result['n_validation_records']}"
    )
    assert result["n_holdout_records"] == 1, (
        f"Expected 1 holdout record (_REC_JEDDAH), got {result['n_holdout_records']}"
    )
    assert result["split_cutoff_date"] == "2023-12-31"
    assert "Jeddah" in result["holdout_cities"]
