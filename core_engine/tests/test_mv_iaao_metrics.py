"""
test_mv_iaao_metrics.py — P8 tests: IAAO Metrics (M-01, M-02, M-03, M-04).
Tests: RS-01 → RS-12
"""
import pytest

from core_engine.mass_appraisal import (
    _ratio_study,
    _compute_prb,
    _compute_r_squared,
)


# ---------------------------------------------------------------------------
# Shared test datasets
# ---------------------------------------------------------------------------

# Low dispersion — COD ≈ 2.8%, PRD = 1.0, equal sale_prices → PRB=None, R²=None
_LOW_DISP = [
    {"unit_value":   950_000.0, "sale_price": 1_000_000.0},  # ratio=0.95
    {"unit_value":   980_000.0, "sale_price": 1_000_000.0},  # ratio=0.98
    {"unit_value": 1_000_000.0, "sale_price": 1_000_000.0},  # ratio=1.00
    {"unit_value": 1_020_000.0, "sale_price": 1_000_000.0},  # ratio=1.02
    {"unit_value": 1_050_000.0, "sale_price": 1_000_000.0},  # ratio=1.05
]

# High dispersion — COD ≈ 21.8%, PRD = 1.0 (equal sp), cod_pass=False at default 15%
_HIGH_DISP = [
    {"unit_value":   700_000.0, "sale_price": 1_000_000.0},  # ratio=0.70
    {"unit_value":   900_000.0, "sale_price": 1_000_000.0},  # ratio=0.90
    {"unit_value": 1_100_000.0, "sale_price": 1_000_000.0},  # ratio=1.10
    {"unit_value": 1_300_000.0, "sale_price": 1_000_000.0},  # ratio=1.30
    {"unit_value": 1_500_000.0, "sale_price": 1_000_000.0},  # ratio=1.50
]

# Progressive — high-value properties have higher ratios → PRD off (≈ 0.79)
_PROGRESSIVE = [
    {"unit_value":   180_000.0, "sale_price":   200_000.0},   # ratio=0.90
    {"unit_value":   270_000.0, "sale_price":   300_000.0},   # ratio=0.90
    {"unit_value":   270_000.0, "sale_price":   300_000.0},   # ratio=0.90
    {"unit_value": 2_000_000.0, "sale_price": 1_000_000.0},   # ratio=2.00
    {"unit_value": 2_400_000.0, "sale_price": 1_200_000.0},   # ratio=2.00
]

# Varied sale prices — PRB and R² are computable (n ≥ 3, not all sp equal)
_VARIED_SP = [
    {"unit_value":   800_000.0, "sale_price":   500_000.0},
    {"unit_value": 1_000_000.0, "sale_price": 1_000_000.0},
    {"unit_value": 1_200_000.0, "sale_price": 2_000_000.0},
    {"unit_value": 1_350_000.0, "sale_price": 3_000_000.0},
    {"unit_value": 1_500_000.0, "sale_price": 5_000_000.0},
]

# Two records — below PRB minimum (n < 3) and below R² minimum (n < 2 pairs at same sp)
_TWO_REC = [
    {"unit_value": 1_000_000.0, "sale_price": 1_000_000.0},
    {"unit_value": 1_200_000.0, "sale_price": 1_200_000.0},
]

# Both appraised and sale prices vary — R² computable and in [0, 1]
_BOTH_VARY = [
    {"unit_value":   950_000.0, "sale_price":   900_000.0},
    {"unit_value": 1_000_000.0, "sale_price": 1_000_000.0},
    {"unit_value": 1_100_000.0, "sale_price": 1_050_000.0},
    {"unit_value": 1_200_000.0, "sale_price": 1_150_000.0},
    {"unit_value": 1_300_000.0, "sale_price": 1_250_000.0},
]


# ---------------------------------------------------------------------------
# RS-01 → RS-04  COD (M-01)
# ---------------------------------------------------------------------------

def test_rs_01_ratio_study_required_keys_present():
    """M-01/M-02/M-03/M-04: all required keys present in ratio_study output."""
    result = _ratio_study(_LOW_DISP)
    required = {
        "n_sales", "cod", "prd", "prb",
        "cod_pass", "prd_pass", "prb_pass",
        "r_squared", "r_squared_diagnostic_only",
    }
    missing = required - result.keys()
    assert not missing, f"ratio_study missing keys: {missing}"


def test_rs_02_cod_is_numeric_and_non_negative():
    """M-01: COD must be a non-negative float."""
    result = _ratio_study(_LOW_DISP)
    assert isinstance(result["cod"], float)
    assert result["cod"] >= 0.0


def test_rs_03_cod_pass_with_default_threshold_low_dispersion():
    """M-01: COD ≈ 2.8% is below default threshold of 15% → cod_pass=True."""
    result = _ratio_study(_LOW_DISP)
    assert result["cod"] < 15.0, f"Expected low COD, got {result['cod']}"
    assert result["cod_pass"] is True


def test_rs_04_custom_cod_max_changes_pass_fail():
    """M-01: high-COD dataset fails at default threshold but passes with custom cod_max=25."""
    default_result = _ratio_study(_HIGH_DISP)
    custom_result  = _ratio_study(_HIGH_DISP, thresholds={"cod_max": 25.0})

    assert default_result["cod"] > 15.0, (
        f"_HIGH_DISP should have COD > 15, got {default_result['cod']}"
    )
    assert default_result["cod_pass"] is False, "Expected cod_pass=False with default threshold"
    assert custom_result["cod_pass"] is True, (
        f"Expected cod_pass=True with cod_max=25, COD={custom_result['cod']}"
    )


# ---------------------------------------------------------------------------
# RS-05 → RS-06  PRD (M-02)
# ---------------------------------------------------------------------------

def test_rs_05_prd_is_numeric():
    """M-02: PRD must be a float."""
    result = _ratio_study(_LOW_DISP)
    assert isinstance(result["prd"], float)


def test_rs_06_custom_prd_range_changes_pass_fail():
    """M-02: PRD outside default (0.98, 1.03) passes with a wider custom range."""
    default_result = _ratio_study(_PROGRESSIVE)
    custom_result  = _ratio_study(_PROGRESSIVE, thresholds={"prd_range": (0.50, 2.00)})

    assert default_result["prd_pass"] is False, (
        f"Progressive dataset should fail default PRD range, got prd={default_result['prd']}"
    )
    assert custom_result["prd_pass"] is True, (
        f"Progressive dataset should pass custom PRD range (0.50-2.00), got prd={custom_result['prd']}"
    )


# ---------------------------------------------------------------------------
# RS-07 → RS-09  PRB (M-03)
# ---------------------------------------------------------------------------

def test_rs_07_prb_key_present_in_ratio_study():
    """M-03: 'prb' must be a key in ratio_study output."""
    result = _ratio_study(_LOW_DISP)
    assert "prb" in result


def test_rs_08_prb_none_when_fewer_than_3_records():
    """M-03: PRB requires n ≥ 3; with only 2 records it must be None."""
    result = _ratio_study(_TWO_REC)
    assert result["prb"] is None, (
        f"PRB should be None with n=2, got {result['prb']}"
    )


def test_rs_09_prb_numeric_with_n_ge_3_and_varied_sale_prices():
    """M-03: PRB is computed (not None) with n ≥ 3 and varied sale prices."""
    result = _ratio_study(_VARIED_SP)
    assert result["prb"] is not None, (
        "PRB should be computable with 5 units and varied sale prices"
    )
    assert isinstance(result["prb"], float)


# ---------------------------------------------------------------------------
# RS-10 → RS-12  R² (M-04)
# ---------------------------------------------------------------------------

def test_rs_10_r_squared_key_present():
    """M-04: 'r_squared' must be a key in ratio_study output."""
    result = _ratio_study(_LOW_DISP)
    assert "r_squared" in result


def test_rs_11_r_squared_diagnostic_only_flag():
    """M-04: r_squared_diagnostic_only must be True — R² must not gate acceptance."""
    result = _ratio_study(_LOW_DISP)
    assert result.get("r_squared_diagnostic_only") is True, (
        "r_squared_diagnostic_only must be True to prevent misuse as acceptance condition"
    )


def test_rs_12_r_squared_in_valid_range_when_computable():
    """M-04: r_squared is in [0.0, 1.0] when both appraised and sale prices vary."""
    result = _ratio_study(_BOTH_VARY)
    r2 = result["r_squared"]
    assert r2 is not None, "r_squared should be computable for _BOTH_VARY dataset"
    assert isinstance(r2, float)
    assert 0.0 <= r2 <= 1.0, f"r_squared must be in [0, 1], got {r2}"
