"""
test_mv_audit_trail.py — P7 tests: Leakage Check (D-08) + Audit Trail (M-07, M-08).
Tests: AT-01 → AT-12
"""
import re
import pytest

from core_engine.mass_valuation.runner import (
    MassValuationRunner,
    _check_leakage,
    _get_code_commit,
)


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

_BASE = {
    "property_id":       "P-BASE",
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

_REC_A      = {**_BASE, "property_id": "P-A", "transaction_date": "2023-06-15"}
_REC_B      = {**_BASE, "property_id": "P-B", "transaction_date": "2024-06-15"}
_REC_JEDDAH = {**_BASE, "property_id": "P-C", "city": "Jeddah", "district": "Al Hamra"}
_CUTOFF     = "2023-12-31"


# ---------------------------------------------------------------------------
# AT-01 → AT-06  _check_leakage / D-08
# ---------------------------------------------------------------------------

def test_at_01_leakage_check_flag_always_true():
    """D-08: run() result must always contain leakage_check=True."""
    result = MassValuationRunner().run([_REC_A])
    assert result["leakage_check"] is True


def test_at_02_leakage_check_method_documented():
    """D-08: leakage_check_method must be a non-empty string."""
    result = MassValuationRunner().run([_REC_A])
    assert isinstance(result["leakage_check_method"], str)
    assert len(result["leakage_check_method"]) > 0


def test_at_03_clean_split_no_leakage():
    """D-08: disjoint property_ids across buckets → leakage_found=False."""
    result = MassValuationRunner().run(
        [_REC_A, _REC_B, _REC_JEDDAH],
        cutoff_date=_CUTOFF,
        holdout_cities=["Jeddah"],
    )
    assert result["leakage_found"] is False


def test_at_04_duplicate_property_id_across_buckets_detected():
    """D-08: same property_id in train and validation → leakage_found=True."""
    rec_dup = {**_BASE, "property_id": "P-A", "transaction_date": "2024-06-15"}
    leakage = _check_leakage(
        train_records=[_REC_A],
        val_records=[rec_dup],
        holdout_records=[],
    )
    assert leakage["leakage_found"] is True
    assert leakage["leakage_count"] == 1
    assert "P-A" in leakage["leakage_ids"]


def test_at_05_check_leakage_unit_no_overlap():
    """_check_leakage returns leakage_count=0 when all property_ids are distinct."""
    result = _check_leakage(
        train_records=[{"property_id": "T-1"}, {"property_id": "T-2"}],
        val_records=[{"property_id": "V-1"}],
        holdout_records=[{"property_id": "H-1"}],
    )
    assert result["leakage_found"] is False
    assert result["leakage_count"] == 0
    assert result["leakage_check"] is True


def test_at_06_validation_strategy_in_run_record():
    """validation_strategy dict is present when cutoff_date is provided."""
    result = MassValuationRunner().run(
        [_REC_A, _REC_B],
        cutoff_date=_CUTOFF,
    )
    vs = result.get("validation_strategy")
    assert isinstance(vs, dict)
    assert "type" in vs
    assert vs["type"] == "temporal_split"
    assert vs["leakage_check"] is True


# ---------------------------------------------------------------------------
# AT-07 → AT-08  random_seed (M-07)
# ---------------------------------------------------------------------------

def test_at_07_random_seed_present_in_run_record():
    """M-07: run record must contain random_seed as integer."""
    result = MassValuationRunner(random_seed=42).run([_REC_A])
    assert "random_seed" in result
    assert isinstance(result["random_seed"], int)


def test_at_08_random_seed_matches_constructor():
    """M-07: random_seed in run record must equal constructor value."""
    result = MassValuationRunner(random_seed=99).run([_REC_A])
    assert result["random_seed"] == 99


# ---------------------------------------------------------------------------
# AT-09 → AT-12  Audit hash triad (M-08)
# ---------------------------------------------------------------------------

def test_at_09_dataset_hash_present_and_sha256():
    """M-08: dataset_hash must be a 64-char lowercase hex SHA-256."""
    result = MassValuationRunner().run([_REC_A])
    h = result.get("dataset_hash", "")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_at_10_model_hash_present_and_sha256():
    """M-08: model_hash must be a 64-char lowercase hex SHA-256."""
    result = MassValuationRunner().run([_REC_A])
    h = result.get("model_hash", "")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_at_11_code_commit_present_and_nonempty():
    """M-08: code_commit must be a non-empty string in run record."""
    result = MassValuationRunner().run([_REC_A])
    cc = result.get("code_commit")
    assert isinstance(cc, str)
    assert len(cc) > 0


def test_at_12_code_commit_is_valid_git_sha_or_unknown():
    """M-08: code_commit is a 7-40 char hex SHA or the literal 'unknown'."""
    result = MassValuationRunner().run([_REC_A])
    cc = result["code_commit"]
    valid_sha = re.fullmatch(r"[0-9a-f]{7,40}", cc) is not None
    assert valid_sha or cc == "unknown", (
        f"code_commit {cc!r} is neither a valid git SHA nor 'unknown'"
    )
