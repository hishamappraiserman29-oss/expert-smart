"""
MVI-01 → MVI-20  Import endpoint contract — pipeline layer.

Tests run_pipeline() — the function that backs POST /api/mass-valuation/import.

Verified field-name conventions (case-insensitive alias resolution via D-02):
  - "transaction_price"  or alias "Price", "Sale_Value", etc.
  - "land_area_m2"       or alias "Land_Area", "Plot_Area", "Area_m2", etc.
  - "address"            or alias "Location", "Full_Address", etc.
  - "property_id"        or alias "id", "PropertyID", etc.

Action values produced by the pipeline:
  - "flag_for_review"  — eligible, review_required=True
  - "reject"           — rejected, not in eligible_records

advisory_only=True and certification_ready=False are hard-coded in the endpoint
at bridge_api.py lines 13025-13026. MVI-19 and MVI-20 assert they are NOT
present on PipelineResult, keeping concerns separated.
"""
from __future__ import annotations

import pytest
from core_engine.mass_valuation.pipeline import run_pipeline

# ── Shared test data (canonical field names via D-02) ─────────────────────────
VALID = {
    "property_id":       "P001",
    "transaction_price": 1_500_000,
    "land_area_m2":      400.0,
    "address":           "King Fahd Road, Riyadh",
    "city":              "Riyadh",
    "district":          "Al Olaya",
    "transaction_date":  "2024-06-01",
    "property_type":     "residential",
}
ZERO_PRICE = {
    "property_id":       "P002",
    "transaction_price": 0,            # D-04: zero price → always reject
    "land_area_m2":      100.0,
    "address":           "Jeddah",
    "city":              "Jeddah",
    "transaction_date":  "2024-06-01",
    "property_type":     "residential",
}


# ── MVI-01 → MVI-20 ───────────────────────────────────────────────────────────

def test_mv_import_01_valid_record_not_rejected():
    """A well-formed record must not be rejected (may be flag_for_review)."""
    r = run_pipeline([VALID])
    assert r.n_input == 1
    assert r.n_rejected == 0
    assert r.n_eligible == 1


def test_mv_import_02_pipeline_result_has_required_fields():
    r = run_pipeline([VALID])
    for attr in ("n_input", "n_eligible", "n_flagged", "n_rejected",
                 "eligible_records", "unmapped_field_names"):
        assert hasattr(r, attr), f"PipelineResult missing: {attr}"
    assert callable(r.pipeline_report)


def test_mv_import_03_rejected_record_excluded_from_eligible():
    r = run_pipeline([VALID, ZERO_PRICE])
    eligible_ids = {rec.get("property_id") for rec in r.eligible_records}
    assert "P001" in eligible_ids
    assert "P002" not in eligible_ids


def test_mv_import_04_flagged_record_included_in_eligible():
    """flag_for_review action means eligible (not rejected) — record is in eligible_records."""
    r = run_pipeline([VALID])
    # VALID triggers QR-016 (market-data rule) → flag_for_review, still eligible
    assert r.n_eligible == 1
    assert r.n_rejected == 0
    assert len(r.eligible_records) == 1
    # eligible_records includes the flagged record
    assert r.eligible_records[0].get("property_id") == "P001"


def test_mv_import_05_price_zero_rejected():
    """D-04: transaction_price=0 is a hard rejection, never imputed."""
    r = run_pipeline([ZERO_PRICE])
    assert r.n_rejected >= 1
    assert r.n_eligible == 0


def test_mv_import_06_no_price_imputation():
    """D-04 invariant: transaction_price=0 records must not appear in eligible_records."""
    r = run_pipeline([ZERO_PRICE, VALID])
    for rec in r.eligible_records:
        tp = rec.get("transaction_price") or 0
        assert tp != 0, "transaction_price=0 must not survive into eligible_records"


def test_mv_import_07_unmapped_field_names_collected():
    """Unrecognised source columns land in unmapped_field_names (not silently dropped)."""
    rec = {**VALID, "unknown_xyz_field_abc": "test_value"}
    r = run_pipeline([rec])
    assert "unknown_xyz_field_abc" in r.unmapped_field_names


def test_mv_import_08_counts_sum_to_n_input():
    r = run_pipeline([VALID, ZERO_PRICE])
    assert r.n_eligible + r.n_rejected == r.n_input


def test_mv_import_09_all_zero_price_eligible_empty():
    """Batch where every record has transaction_price=0 → n_eligible=0, eligible_records=[]."""
    records = [
        {**ZERO_PRICE, "property_id": f"R{i}"}
        for i in range(3)
    ]
    r = run_pipeline(records)
    assert r.n_eligible == 0
    assert r.eligible_records == []


def test_mv_import_10_pipeline_report_one_entry_per_record():
    r = run_pipeline([VALID, {**VALID, "property_id": "P007"}])
    assert len(r.pipeline_report()) == 2


def test_mv_import_11_pipeline_report_entry_has_required_keys():
    r = run_pipeline([VALID])
    entry = r.pipeline_report()[0]
    for key in ("index", "property_id", "action", "quality_flags", "unmapped_keys"):
        assert key in entry, f"pipeline_report entry missing key: {key}"


def test_mv_import_12_pipeline_report_action_values():
    """Verified action values: 'flag_for_review' (eligible) or 'reject'."""
    r = run_pipeline([VALID, ZERO_PRICE])
    allowed = {"flag_for_review", "reject"}
    for entry in r.pipeline_report():
        assert entry["action"] in allowed, (
            f"unexpected action {entry['action']!r} — expected one of {allowed}"
        )


def test_mv_import_13_n_eligible_equals_input_minus_rejected():
    r = run_pipeline([VALID, VALID, ZERO_PRICE])
    assert r.n_eligible == r.n_input - r.n_rejected


def test_mv_import_14_source_csv_accepted():
    r = run_pipeline([VALID], source="csv")
    assert r.n_input == 1


def test_mv_import_15_source_xlsx_accepted():
    r = run_pipeline([VALID], source="xlsx")
    assert r.n_input == 1


def test_mv_import_16_lookback_months_accepted():
    r = run_pipeline([VALID], lookback_months=12)
    assert r.n_input == 1


def test_mv_import_17_canonical_fields_not_in_unmapped():
    """D-02: canonical field names map correctly and must not appear in unmapped_field_names."""
    r = run_pipeline([VALID])
    canonical_standard = {"transaction_price", "land_area_m2", "address", "property_id"}
    leaked = canonical_standard & set(r.unmapped_field_names)
    assert not leaked, f"Canonical fields appear as unmapped: {leaked}"


def test_mv_import_18_eligible_records_are_dicts():
    r = run_pipeline([VALID, {**VALID, "property_id": "P008"}])
    for rec in r.eligible_records:
        assert isinstance(rec, dict)


def test_mv_import_19_advisory_only_not_in_pipeline_result():
    """
    advisory_only=True is hard-coded in the endpoint (bridge_api.py:13025).
    It must NOT appear on PipelineResult — keeping pipeline and HTTP concerns separated.
    """
    r = run_pipeline([VALID])
    assert not hasattr(r, "advisory_only"), (
        "advisory_only must not be in PipelineResult; it is set by the endpoint only"
    )


def test_mv_import_20_certification_ready_not_in_pipeline_result():
    """
    certification_ready=False is hard-coded in the endpoint (bridge_api.py:13026).
    It must NOT appear on PipelineResult.
    """
    r = run_pipeline([VALID])
    assert not hasattr(r, "certification_ready"), (
        "certification_ready must not be in PipelineResult; it is set by the endpoint only"
    )
