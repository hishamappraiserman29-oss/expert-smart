"""
test_mv_pipeline.py — P13 tests: import pipeline integration (D-02 + D-03/D-04/D-05).
Tests: PL-01 → PL-12
"""
import pytest

from core_engine.mass_valuation.pipeline import PipelineResult, run_pipeline

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_GOOD = {
    "property_id":       "P-001",
    "property_type":     "residential",
    "city":              "Riyadh",
    "land_area_m2":      300.0,
    "transaction_date":  "2024-10-01",
    "transaction_price": 2_000_000,
    "evidence_type":     "registered_sale",
}
_BAD_PRICE = {**_GOOD, "property_id": "P-002", "transaction_price": 0}
_BAD_DATE  = {**_GOOD, "property_id": "P-003", "transaction_date": "2099-01-01"}


# ---------------------------------------------------------------------------
# PL-01  Clean record → eligible
# ---------------------------------------------------------------------------

def test_pl_01_clean_record_eligible():
    """Pipeline: a clean record passes both stages and is eligible."""
    result = run_pipeline([_GOOD])
    assert isinstance(result, PipelineResult)
    assert result.n_input == 1
    assert result.n_eligible == 1
    assert result.n_rejected == 0
    assert result.n_flagged == 0


# ---------------------------------------------------------------------------
# PL-02  Zero price → rejected (QR-004, D-04 no imputation)
# ---------------------------------------------------------------------------

def test_pl_02_zero_price_rejected():
    """D-04: transaction_price=0 must be rejected at quality stage, never imputed."""
    result = run_pipeline([_BAD_PRICE])
    assert result.n_rejected == 1
    assert result.n_eligible == 0


# ---------------------------------------------------------------------------
# PL-03  Future date → rejected (QR-006)
# ---------------------------------------------------------------------------

def test_pl_03_future_date_rejected():
    """Quality stage rejects records with a future transaction_date."""
    result = run_pipeline([_BAD_DATE])
    assert result.n_rejected == 1
    assert result.n_eligible == 0


# ---------------------------------------------------------------------------
# PL-04  Mixed batch → correct counts
# ---------------------------------------------------------------------------

def test_pl_04_mixed_batch_counts():
    """Pipeline counts are correct across a mixed accepted/rejected batch."""
    result = run_pipeline([_GOOD, _BAD_PRICE, _BAD_DATE])
    assert result.n_input == 3
    assert result.n_rejected == 2
    assert result.n_eligible == 1


# ---------------------------------------------------------------------------
# PL-05  Arabic alias → canonical before quality check
# ---------------------------------------------------------------------------

def test_pl_05_arabic_alias_canonical_before_qc():
    """D-02: Arabic aliases are resolved to canonical names before quality rules fire."""
    raw = {
        "رقم_العقار":        "P-AR-001",
        "property_type":     "residential",
        "city":              "Riyadh",
        "land_area_m2":      300.0,
        "transaction_date":  "2024-10-01",
        "قيمة_الصفقة":       2_000_000,
    }
    result = run_pipeline([raw])
    assert result.n_eligible == 1
    assert result.n_rejected == 0


# ---------------------------------------------------------------------------
# PL-06  CSV alias → canonical before quality check
# ---------------------------------------------------------------------------

def test_pl_06_csv_alias_canonical_before_qc():
    """D-02: CSV alias columns (Plot_Area, Sale_Value) resolve before QR-001 fires."""
    raw = {
        "Property_No":       "P-CSV",
        "property_type":     "residential",
        "city":              "Riyadh",
        "Plot_Area":         "300",
        "Sale_Date":         "2023-06-15",
        "Sale_Value":        "2000000",
    }
    result = run_pipeline([raw])
    assert result.n_eligible == 1
    assert result.n_rejected == 0


# ---------------------------------------------------------------------------
# PL-07  Unmapped field names collected across batch
# ---------------------------------------------------------------------------

def test_pl_07_unmapped_fields_collected():
    """Unknown source columns are collected in unmapped_field_names, not silently dropped."""
    raw = {**_GOOD, "obsolete_col": "x", "legacy_field": "y"}
    result = run_pipeline([raw])
    assert "obsolete_col" in result.unmapped_field_names
    assert "legacy_field" in result.unmapped_field_names
    # Known canonical fields are NOT in unmapped
    assert "property_id" not in result.unmapped_field_names


# ---------------------------------------------------------------------------
# PL-08  pipeline_report structure
# ---------------------------------------------------------------------------

def test_pl_08_pipeline_report_structure():
    """Each entry in pipeline_report has the required keys."""
    result = run_pipeline([_GOOD, _BAD_PRICE])
    report = result.pipeline_report()
    assert len(report) == 2
    required_keys = {"index", "property_id", "action", "quality_flags", "unmapped_keys"}
    for entry in report:
        assert required_keys.issubset(entry.keys())


# ---------------------------------------------------------------------------
# PL-09  eligible_records contain canonical keys, not source aliases
# ---------------------------------------------------------------------------

def test_pl_09_eligible_records_are_canonical():
    """D-02: eligible_records use canonical field names, not the original source aliases."""
    raw = {
        "Sale_Value":        "2000000",
        "Property_No":       "P-009",
        "property_type":     "residential",
        "city":              "Riyadh",
        "Plot_Area":         "300",
        "Sale_Date":         "2023-06-15",
    }
    result = run_pipeline([raw])
    assert result.n_eligible == 1
    canonical = result.eligible_records[0]
    assert "transaction_price" in canonical   # canonical name
    assert "property_id"       in canonical
    assert "Sale_Value"        not in canonical  # source alias not present
    assert "Property_No"       not in canonical


# ---------------------------------------------------------------------------
# PL-10  Rejected records NOT in eligible_records
# ---------------------------------------------------------------------------

def test_pl_10_rejected_not_in_eligible():
    """Records rejected at quality stage are excluded from eligible_records."""
    result = run_pipeline([_GOOD, _BAD_PRICE])
    pids = [r.get("property_id") for r in result.eligible_records]
    assert "P-001" in pids
    assert "P-002" not in pids   # _BAD_PRICE rejected by QR-004


# ---------------------------------------------------------------------------
# PL-11  Missing location → flag_for_review, not rejected (D-04 no imputation)
# ---------------------------------------------------------------------------

def test_pl_11_missing_location_flagged_not_rejected():
    """
    D-04: when city is absent and coordinates are absent, QR-015 fires → flag_for_review.
    The record is still eligible (flagged for analyst review, not rejected).
    """
    raw = {k: v for k, v in _GOOD.items() if k != "city"}
    raw["property_id"] = "P-011"
    result = run_pipeline([raw])
    assert result.n_eligible == 1    # not rejected
    assert result.n_flagged  == 1    # flagged for review
    assert result.n_rejected == 0


# ---------------------------------------------------------------------------
# PL-12  D-04 price=0 rejected, never imputed
# ---------------------------------------------------------------------------

def test_pl_12_price_zero_rejected_not_imputed():
    """D-04: zero transaction_price is rejected (QR-004); no imputation occurs."""
    raw = {**_GOOD, "property_id": "P-012", "transaction_price": 0}
    result = run_pipeline([raw])
    assert result.n_rejected == 1
    assert result.n_eligible == 0
    rec = result.records[0]
    assert "QR-004" in rec.quality.quality_flags
    # canonical record must not have a filled-in price (no imputation)
    assert rec.canonical.get("transaction_price") == 0
