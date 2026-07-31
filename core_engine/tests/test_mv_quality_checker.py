"""
test_mv_quality_checker.py — P12 tests: Quality Rules (D-03, D-04, D-05).
Tests: QC-01 → QC-30

D-03: All 16 quality rules (QR-001 → QR-016) are enforced.
D-04: transaction_price and location (city/coordinates) are NEVER statistically imputed.
D-05: Isolation Forest and Z-score produce flag_for_review ONLY (auto_delete=False).
"""
import datetime
import pytest

from core_engine.mass_valuation.quality_checker import (
    QualityResult,
    RuleViolation,
    check_record,
    check_batch,
)


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

_TODAY = datetime.date(2026, 7, 30)

_CLEAN = {
    "property_id":       "P-QC",
    "property_type":     "residential",
    "city":              "Riyadh",
    "district":          "Al Nakheel",
    "land_area_m2":      300.0,
    "built_up_area_m2":  200.0,
    "transaction_date":  "2024-06-15",
    "transaction_price": 2_000_000,
    "evidence_type":     "registered_sale",
    "latitude":          24.7136,
    "longitude":         46.6753,
}


def _check(record, **kw):
    """Shortcut: run check_record with today fixed to _TODAY."""
    return check_record(record, today=_TODAY, **kw)


# ---------------------------------------------------------------------------
# QC-01  Clean record passes with no violations
# ---------------------------------------------------------------------------

def test_qc_01_clean_record_passes():
    """D-03: A fully valid record must produce action='pass' with no violations."""
    result = _check(_CLEAN)
    assert result.action == "pass"
    assert result.violations == []
    assert result.rejected is False
    assert result.review_required is False


# ---------------------------------------------------------------------------
# QC-02  QR-001 missing required field → reject
# ---------------------------------------------------------------------------

def test_qc_02_qr001_missing_property_id_rejects():
    """QR-001: missing property_id must trigger reject."""
    record = {**_CLEAN, "property_id": None}
    result = _check(record)
    assert result.rejected is True
    rule_ids = result.quality_flags
    assert "QR-001" in rule_ids


def test_qc_03_qr001_missing_transaction_price_rejects():
    """QR-001: missing transaction_price must trigger reject."""
    record = {k: v for k, v in _CLEAN.items() if k != "transaction_price"}
    result = _check(record)
    assert result.rejected is True
    assert "QR-001" in result.quality_flags


def test_qc_04_qr001_missing_land_area_rejects():
    """QR-001: missing land_area_m2 must trigger reject."""
    record = {k: v for k, v in _CLEAN.items() if k != "land_area_m2"}
    result = _check(record)
    assert result.rejected is True
    assert "QR-001" in result.quality_flags


# ---------------------------------------------------------------------------
# QC-05  QR-004 zero / negative / sub-1000 price → reject
# ---------------------------------------------------------------------------

def test_qc_05_qr004_zero_price_rejects():
    """QR-004: transaction_price=0 must be rejected (CRITICAL: no imputation)."""
    result = _check({**_CLEAN, "transaction_price": 0})
    assert result.rejected is True
    assert "QR-004" in result.quality_flags


def test_qc_06_qr004_negative_price_rejects():
    """QR-004: negative transaction_price must be rejected."""
    result = _check({**_CLEAN, "transaction_price": -500})
    assert result.rejected is True
    assert "QR-004" in result.quality_flags


def test_qc_07_qr004_below_1000_sar_rejects():
    """QR-004: price below 1000 SAR must be rejected (probable data error)."""
    result = _check({**_CLEAN, "transaction_price": 999})
    assert result.rejected is True
    assert "QR-004" in result.quality_flags


# ---------------------------------------------------------------------------
# QC-08  QR-005 zero / negative area → reject
# ---------------------------------------------------------------------------

def test_qc_08_qr005_zero_land_area_rejects():
    """QR-005: land_area_m2=0 must be rejected."""
    result = _check({**_CLEAN, "land_area_m2": 0})
    assert result.rejected is True
    assert "QR-005" in result.quality_flags


def test_qc_09_qr005_negative_land_area_rejects():
    """QR-005: negative land_area_m2 must be rejected."""
    result = _check({**_CLEAN, "land_area_m2": -10})
    assert result.rejected is True
    assert "QR-005" in result.quality_flags


def test_qc_10_qr005_negative_built_up_area_rejects():
    """QR-005: negative built_up_area_m2 must be rejected."""
    result = _check({**_CLEAN, "built_up_area_m2": -1})
    assert result.rejected is True
    assert "QR-005" in result.quality_flags


# ---------------------------------------------------------------------------
# QC-11  QR-006 future transaction date → reject
# ---------------------------------------------------------------------------

def test_qc_11_qr006_future_date_rejects():
    """QR-006: transaction_date after today must be rejected."""
    future = (_TODAY + datetime.timedelta(days=1)).isoformat()
    result = _check({**_CLEAN, "transaction_date": future})
    assert result.rejected is True
    assert "QR-006" in result.quality_flags


def test_qc_12_qr006_today_date_is_valid():
    """QR-006: transaction_date == today is valid (not future)."""
    result = _check({**_CLEAN, "transaction_date": _TODAY.isoformat()})
    assert "QR-006" not in result.quality_flags


# ---------------------------------------------------------------------------
# QC-13  QR-007 outside lookback window → flag_out_of_window
# ---------------------------------------------------------------------------

def test_qc_13_qr007_outside_lookback_flags():
    """QR-007: transaction_date older than lookback_months triggers flag_out_of_window."""
    old_date = "2020-01-01"  # well outside 36-month window from 2026-07-30
    result = _check({**_CLEAN, "transaction_date": old_date})
    assert "QR-007" in result.quality_flags
    violations = {v.rule_id: v for v in result.violations}
    assert violations["QR-007"].action == "flag_out_of_window"
    assert result.review_required is True


def test_qc_14_qr007_within_lookback_is_clean():
    """QR-007: transaction_date within lookback does not trigger flag_out_of_window."""
    recent = "2024-06-15"
    result = _check({**_CLEAN, "transaction_date": recent})
    assert "QR-007" not in result.quality_flags


# ---------------------------------------------------------------------------
# QC-15  QR-008 coordinates outside SA → reject
# ---------------------------------------------------------------------------

def test_qc_15_qr008_outside_sa_rejects():
    """QR-008: coordinates outside SA bounding box must be rejected."""
    result = _check({**_CLEAN, "latitude": 0.0, "longitude": 0.0})
    assert result.rejected is True
    assert "QR-008" in result.quality_flags


def test_qc_16_qr008_inside_sa_is_clean():
    """QR-008: coordinates inside SA bounding box are valid."""
    result = _check({**_CLEAN, "latitude": 24.7, "longitude": 46.7})
    assert "QR-008" not in result.quality_flags


# ---------------------------------------------------------------------------
# QC-17  QR-009 partial coordinates → reject
# ---------------------------------------------------------------------------

def test_qc_17_qr009_lat_only_rejects():
    """QR-009: providing only latitude (no longitude) must be rejected."""
    record = {**_CLEAN}
    del record["longitude"]
    record["latitude"] = 24.7136
    result = _check(record)
    assert result.rejected is True
    assert "QR-009" in result.quality_flags


def test_qc_18_qr009_no_coords_is_valid():
    """QR-009: providing no coordinates at all is valid (city-only location)."""
    record = {**_CLEAN}
    del record["latitude"]
    del record["longitude"]
    result = _check(record)
    assert "QR-009" not in result.quality_flags


# ---------------------------------------------------------------------------
# QC-19  QR-010 built area exceeds land area ratio → flag_for_review
# ---------------------------------------------------------------------------

def test_qc_19_qr010_built_exceeds_residential_ratio_flags():
    """QR-010: built_up_area > land_area × 4 for residential triggers flag_for_review."""
    result = _check({
        **_CLEAN,
        "land_area_m2":     100.0,
        "built_up_area_m2": 500.0,  # 5× land — exceeds residential max (4×)
    })
    assert "QR-010" in result.quality_flags
    v = next(v for v in result.violations if v.rule_id == "QR-010")
    assert v.action == "flag_for_review"
    assert result.rejected is False  # must NOT be rejected


def test_qc_20_qr010_reasonable_built_area_is_clean():
    """QR-010: built_up_area ≤ land_area × 4 for residential is valid."""
    result = _check({
        **_CLEAN,
        "land_area_m2":     300.0,
        "built_up_area_m2": 200.0,  # well within 4×
    })
    assert "QR-010" not in result.quality_flags


# ---------------------------------------------------------------------------
# QC-21  QR-011 rentable exceeds built → flag_for_review
# ---------------------------------------------------------------------------

def test_qc_21_qr011_rentable_exceeds_built_flags():
    """QR-011: rentable_area_m2 > built_up_area_m2 triggers flag_for_review."""
    result = _check({
        **_CLEAN,
        "built_up_area_m2": 200.0,
        "rentable_area_m2": 300.0,
    })
    assert "QR-011" in result.quality_flags
    v = next(v for v in result.violations if v.rule_id == "QR-011")
    assert v.action == "flag_for_review"
    assert result.rejected is False


# ---------------------------------------------------------------------------
# QC-22  QR-012 Isolation Forest → flag_for_review (D-05 governance)
# ---------------------------------------------------------------------------

def test_qc_22_qr012_isolation_forest_flags_not_rejects():
    """
    D-05: Isolation Forest anomaly must produce flag_for_review ONLY.
    GOVERNANCE: auto_delete=False — record is NEVER automatically deleted.
    """
    result = _check(_CLEAN, isolation_forest_score=0.01)  # below 0.05 threshold
    assert "QR-012" in result.quality_flags
    v = next(v for v in result.violations if v.rule_id == "QR-012")
    assert v.action == "flag_for_review", (
        "D-05: Isolation Forest must produce flag_for_review, not reject or exclude"
    )
    assert result.rejected is False, (
        "D-05: Isolation Forest MUST NOT reject the record — auto_delete=False"
    )


def test_qc_23_qr012_isolation_forest_above_threshold_is_clean():
    """D-05: IF score above threshold → no violation."""
    result = _check(_CLEAN, isolation_forest_score=0.10)  # above 0.05
    assert "QR-012" not in result.quality_flags


def test_qc_24_qr012_no_score_produces_no_violation():
    """D-05: When no Isolation Forest score supplied, QR-012 is not triggered."""
    result = _check(_CLEAN, isolation_forest_score=None)
    assert "QR-012" not in result.quality_flags


# ---------------------------------------------------------------------------
# QC-25  QR-013 Z-score → flag_for_review (D-05 governance)
# ---------------------------------------------------------------------------

def test_qc_25_qr013_zscore_flags_not_rejects():
    """
    D-05: Z-score outlier must produce flag_for_review ONLY.
    GOVERNANCE: auto_delete=False — record is NEVER automatically deleted.
    """
    result = _check(_CLEAN, z_score=4.5)  # > 3.0 threshold
    assert "QR-013" in result.quality_flags
    v = next(v for v in result.violations if v.rule_id == "QR-013")
    assert v.action == "flag_for_review", (
        "D-05: Z-score must produce flag_for_review, not reject or exclude"
    )
    assert result.rejected is False, (
        "D-05: Z-score MUST NOT reject the record — auto_delete=False"
    )


def test_qc_26_qr013_negative_zscore_flags():
    """D-05: Negative Z-score below -3.0 also triggers QR-013."""
    result = _check(_CLEAN, z_score=-3.5)
    assert "QR-013" in result.quality_flags


def test_qc_27_qr013_within_threshold_is_clean():
    """D-05: Z-score ≤ 3.0 → no QR-013 violation."""
    result = _check(_CLEAN, z_score=2.9)
    assert "QR-013" not in result.quality_flags


# ---------------------------------------------------------------------------
# QC-28  QR-014 currency ambiguity → flag_for_review
# ---------------------------------------------------------------------------

def test_qc_28_qr014_suspiciously_low_price_flags():
    """QR-014: price < min_plausible_SAR for property type triggers flag_for_review."""
    result = _check({**_CLEAN, "transaction_price": 10_000})  # < 50k SAR residential floor
    # QR-004 rejects prices < 1000; price of 10k passes QR-004 but fails QR-014
    assert "QR-014" in result.quality_flags
    v = next(v for v in result.violations if v.rule_id == "QR-014")
    assert v.action == "flag_for_review"


# ---------------------------------------------------------------------------
# QC-29  QR-015 location both missing → flag_for_review (D-04)
# ---------------------------------------------------------------------------

def test_qc_29_qr015_no_city_no_coords_flags():
    """
    D-04: When both city and coordinates are absent, QR-015 must fire.
    GOVERNANCE: Location is NEVER statistically imputed.
    """
    record = {
        **_CLEAN,
        "city":      None,
        "latitude":  None,
        "longitude": None,
    }
    result = _check(record)
    assert "QR-015" in result.quality_flags
    v = next(v for v in result.violations if v.rule_id == "QR-015")
    assert v.action == "flag_for_review"
    assert result.rejected is False, (
        "D-04: QR-015 must flag_for_review, not reject — record is kept for manual review"
    )


def test_qc_30_qr015_city_present_no_coords_is_valid():
    """D-04: city present without coordinates → no QR-015 (city is sufficient for location)."""
    record = {
        **_CLEAN,
        "latitude":  None,
        "longitude": None,
    }
    result = _check(record)
    assert "QR-015" not in result.quality_flags


# ---------------------------------------------------------------------------
# QC-31  QR-016 non-arms-length → flag_for_review
# ---------------------------------------------------------------------------

def test_qc_31_qr016_manual_entry_no_docs_flags():
    """QR-016: evidence_type='manual_entry' without source_documentation triggers flag."""
    result = _check({
        **_CLEAN,
        "evidence_type":       "manual_entry",
        "source_documentation": None,
    })
    assert "QR-016" in result.quality_flags
    v = next(v for v in result.violations if v.rule_id == "QR-016")
    assert v.action == "flag_for_review"


def test_qc_32_qr016_registered_sale_is_clean():
    """QR-016: evidence_type='registered_sale' does not trigger QR-016."""
    result = _check({**_CLEAN, "evidence_type": "registered_sale"})
    assert "QR-016" not in result.quality_flags


# ---------------------------------------------------------------------------
# QC-33  Severity ordering — reject wins over flag_for_review
# ---------------------------------------------------------------------------

def test_qc_33_reject_wins_over_flag_for_review():
    """D-03: When both reject and flag_for_review violations exist, action='reject'."""
    record = {
        **_CLEAN,
        "transaction_price": 0,          # QR-004 → reject
        "rentable_area_m2":  999_999.0,  # QR-011 → flag_for_review
        "built_up_area_m2":  200.0,
    }
    result = _check(record)
    assert result.action == "reject"
    assert "QR-004" in result.quality_flags
    assert "QR-011" in result.quality_flags


# ---------------------------------------------------------------------------
# QC-34  QR-002 duplicate property_id in batch → flag_for_review
# ---------------------------------------------------------------------------

def test_qc_34_qr002_duplicate_pid_in_batch_flags():
    """QR-002: same property_id appearing twice in a batch must trigger flag_for_review."""
    r1 = {**_CLEAN, "property_id": "P-DUP"}
    r2 = {**_CLEAN, "property_id": "P-DUP", "transaction_price": 2_100_000}
    results = check_batch([r1, r2], today=_TODAY)
    for qr in results:
        assert "QR-002" in qr.quality_flags, (
            f"property_id='P-DUP' is duplicated — QR-002 must fire for every occurrence"
        )


def test_qc_35_qr002_unique_pids_no_duplicate_flag():
    """QR-002: batch with unique property_ids must not trigger QR-002."""
    r1 = {**_CLEAN, "property_id": "P-A"}
    r2 = {**_CLEAN, "property_id": "P-B"}
    results = check_batch([r1, r2], today=_TODAY)
    for qr in results:
        assert "QR-002" not in qr.quality_flags


# ---------------------------------------------------------------------------
# QC-36  QualityResult structure
# ---------------------------------------------------------------------------

def test_qc_36_quality_result_is_correct_type():
    """D-03: check_record always returns a QualityResult."""
    result = _check(_CLEAN)
    assert isinstance(result, QualityResult)
    assert isinstance(result.quality_flags, list)
    assert isinstance(result.violations, list)
    d = result.to_dict()
    assert "action" in d
    assert "violations" in d
    assert "review_required" in d


# ---------------------------------------------------------------------------
# QC-37  D-04 transaction_price=0 has no fallback / imputation path
# ---------------------------------------------------------------------------

def test_qc_37_d04_price_zero_is_rejected_never_imputed():
    """
    D-04: transaction_price=0 must be rejected immediately.
    The checker must never impute or replace it — rejected=True, no 'transaction_price'
    in the quality_flags other than QR-004 (price rule).
    """
    result = _check({**_CLEAN, "transaction_price": 0})
    assert result.rejected is True, "D-04: zero price must be rejected, not imputed"
    assert "QR-004" in result.quality_flags
    # Verify no imputation-related flags appear
    for v in result.violations:
        assert "imputed" not in v.name.lower(), (
            "D-04: checker must not trigger any imputation path for transaction_price"
        )


# ---------------------------------------------------------------------------
# QC-38  D-05 combined Isolation Forest + Z-score both flag, neither deletes
# ---------------------------------------------------------------------------

def test_qc_38_d05_both_anomaly_flags_without_rejection():
    """
    D-05: A record flagged by BOTH Isolation Forest AND Z-score must receive
    two flag_for_review violations and must NOT be rejected or excluded.
    GOVERNANCE: combined_anomaly = priority review, still never auto-deleted.
    """
    result = _check(_CLEAN, isolation_forest_score=0.01, z_score=4.5)
    assert "QR-012" in result.quality_flags
    assert "QR-013" in result.quality_flags
    assert result.rejected is False, (
        "D-05: combined IF+Z-score flag must NOT cause rejection — auto_delete=False"
    )
    assert result.action == "flag_for_review", (
        "D-05: combined anomaly action must be flag_for_review, not reject or exclude"
    )
