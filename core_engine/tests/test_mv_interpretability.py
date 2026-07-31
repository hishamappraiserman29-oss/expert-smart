"""
test_mv_interpretability.py — P5 tests: Interpretability (I-01 → I-04).
Tests: INT-01 → INT-12
"""
import pytest

from core_engine.mass_valuation.runner import (
    _derive_confidence,
    _build_limitations,
    _compute_shap_proxy,
    _compute_batch_stats,
    _build_predictions,
)
from core_engine.mass_valuation.output_builder import OutputBuilder
from core_engine.mass_valuation.secrets_scanner import scan_for_forbidden_terms


# ---------------------------------------------------------------------------
# INT-01 → INT-04  _derive_confidence (I-03)
# ---------------------------------------------------------------------------

def test_int_01_ood_status_gives_low_confidence():
    """out_of_distribution → confidence must be 'low'."""
    assert _derive_confidence("out_of_distribution", -0.8, 1_000_000) == "low"


def test_int_02_typical_property_gives_high_confidence():
    """ood_score ≥ -0.2, in_distribution → confidence 'high'."""
    assert _derive_confidence("in_distribution", -0.1, 1_000_000) == "high"


def test_int_03_borderline_property_gives_medium_confidence():
    """in_distribution, ood_score < -0.2 → confidence 'medium'."""
    assert _derive_confidence("in_distribution", -0.35, 1_000_000) == "medium"


def test_int_04_zero_unit_value_gives_insufficient_confidence():
    """unit_value ≤ 0 → 'insufficient' regardless of OOD status."""
    assert _derive_confidence("in_distribution",     0.0, 0) == "insufficient"
    assert _derive_confidence("out_of_distribution", -0.8, 0) == "insufficient"


# ---------------------------------------------------------------------------
# INT-05 → INT-08  _build_limitations (I-02 + I-04)
# ---------------------------------------------------------------------------

def test_int_05_ood_property_has_limitations():
    """OOD property must have at least one limitation string."""
    lims = _build_limitations("out_of_distribution", -0.8, 1_000_000, {"final_ppm": 28_000.0})
    assert len(lims) > 0


def test_int_06_normal_property_with_market_data_has_no_limitations():
    """Typical in-distribution property with valid ppm → empty limitations."""
    lims = _build_limitations("in_distribution", -0.1, 1_000_000, {"final_ppm": 28_000.0})
    assert lims == []


def test_int_07_limitation_strings_contain_no_forbidden_jargon():
    """I-04: every auto-generated limitation must pass the O-02 jargon scan."""
    scenarios = [
        ("out_of_distribution", -0.8,  1_000_000, {"final_ppm": 28_000.0}),
        ("in_distribution",     -0.35, 1_000_000, {"final_ppm": 28_000.0}),
        ("in_distribution",     -0.1,  1_000_000, {"final_ppm": 0.0}),
    ]
    for ood_status, ood_score, unit_value, unit in scenarios:
        for text in _build_limitations(ood_status, ood_score, unit_value, unit):
            forbidden = scan_for_forbidden_terms(text)
            assert forbidden == [], (
                f"Limitation text contains forbidden jargon {forbidden!r}: {text!r}"
            )


def test_int_08_zero_ppm_adds_no_market_data_limitation():
    """final_ppm=0 → limitation mentions lack of comparable market transactions."""
    lims = _build_limitations("in_distribution", -0.1, 1_000_000, {"final_ppm": 0.0})
    assert len(lims) == 1
    assert "comparable" in lims[0].lower() or "market" in lims[0].lower()


# ---------------------------------------------------------------------------
# INT-09 → INT-11  _compute_shap_proxy (I-01)
# ---------------------------------------------------------------------------

_BATCH_STATS = {
    "median_area":  200.0,
    "median_ppm":   28_000.0,
    "median_year":  2015.0,
    "n_units":      8.0,
}


def test_int_09_shap_proxy_has_expected_keys():
    """SHAP proxy for a valid unit must contain attribution + metadata keys."""
    unit = {"area": 300.0, "final_ppm": 30_000.0, "year_built": 2018.0}
    proxy = _compute_shap_proxy(unit, _BATCH_STATS, 9_000_000.0)
    assert "area_contribution"         in proxy
    assert "market_price_contribution" in proxy
    assert "age_contribution"          in proxy
    assert proxy.get("method") == "linear_decomposition_proxy"


def test_int_10_shap_proxy_empty_for_zero_value():
    """SHAP proxy returns {} when unit_value ≤ 0 (aligns with G-05)."""
    unit = {"area": 200.0, "final_ppm": 28_000.0, "year_built": 2015.0}
    assert _compute_shap_proxy(unit, _BATCH_STATS, 0.0) == {}


def test_int_11_shap_values_hidden_from_user_role():
    """shap_values must not appear in user-role output (I-01 RBAC check)."""
    pred = {
        "prediction_id": "p1", "property_id": "P001",
        "estimated_value": 1_000_000, "unit_value": 5000,
        "prediction_interval_low": 850_000,
        "prediction_interval_high": 1_150_000,
        "confidence": "high", "distribution_status": "in_distribution",
        "ood_score": -0.1, "limitations": [], "advisory_only": True,
        "shap_values": {
            "area_contribution": 500_000,
            "market_price_contribution": -200_000,
            "age_contribution": 10_000,
            "method": "linear_decomposition_proxy",
            "advisory_note": "Approximate attribution only — not SHAP.",
        },
        "quality_flags": [], "comparable_ids": [],
        "model_version": "hedonic-v1", "review_status": "manual_review_required",
    }
    user_view = OutputBuilder().filter_prediction(pred, "user")
    assert "shap_values" not in user_view, "shap_values must be hidden from user role"

    analyst_view = OutputBuilder().filter_prediction(pred, "analyst")
    assert "shap_values" in analyst_view, "shap_values must be visible to analyst role"


# ---------------------------------------------------------------------------
# INT-12  Integration — confidence reflects OOD (not hardcoded 'medium')
# ---------------------------------------------------------------------------

def test_int_12_build_predictions_confidence_reflects_ood():
    """
    _build_predictions must set confidence='low' for an OOD unit
    and 'high' or 'medium' for a normal unit — not the old hardcoded 'medium'.
    """
    normal_unit = {
        "id": "N-1", "area": 200.0, "floor": 1.0, "year_built": 2015,
        "condition": "good", "sale_price": 0,
        "unit_value": 5_600_000.0, "final_ppm": 28_000.0,
    }
    ood_unit = {
        "id": "OOD-1", "area": 50_000.0, "floor": 1.0, "year_built": 2015,
        "condition": "good", "sale_price": 0,
        "unit_value": 1_400_000_000.0, "final_ppm": 28_000.0,
    }
    units = [normal_unit, ood_unit]
    ood_results = [(-0.1, "in_distribution"), (-1.0, "out_of_distribution")]
    batch_stats = _compute_batch_stats(units)

    preds = _build_predictions(units, "test-run-p5", ood_results, batch_stats)

    assert preds[0]["confidence"] in {"high", "medium"}, (
        f"Normal property expected high/medium confidence, got {preds[0]['confidence']!r}"
    )
    assert preds[1]["confidence"] == "low", (
        f"OOD property expected 'low' confidence, got {preds[1]['confidence']!r}"
    )
