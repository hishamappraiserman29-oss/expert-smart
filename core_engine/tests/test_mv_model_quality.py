"""
test_mv_model_quality.py — P4 tests: OOD detection (M-06) + PI coverage (M-05).
Tests: MOD-01 → MOD-12
"""
import pytest

from core_engine.mass_valuation.ood_detector import (
    detect_ood,
    _robust_zscore_fallback,
    OODBackendConfigurationError,
    OODBackendUnavailableError,
)
from core_engine.mass_valuation.runner import (
    MassValuationRunner,
    _compute_pi_coverage,
)
from core_engine.mass_valuation.output_builder import OutputBuilder


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_NORMAL_UNIT = {
    "id": "U-001", "area": 200.0, "floor": 1.0,
    "year_built": 2015.0, "final_ppm": 28000.0,
    "unit_value": 5_600_000.0, "sale_price": 0,
}

def _make_unit(area, final_ppm=28000.0, sale_price=0):
    return {
        "id": f"U-{area}",
        "area": float(area),
        "floor": 1.0,
        "year_built": 2015.0,
        "final_ppm": float(final_ppm),
        "unit_value": float(area) * float(final_ppm),
        "sale_price": float(sale_price),
    }

_NORMAL_BATCH = [_make_unit(a) for a in [100, 150, 200, 250, 300, 350, 400, 450]]
_OUTLIER_UNIT = _make_unit(50000)  # extreme area — far from batch distribution

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

VALID_RECORD_2 = {**VALID_RECORD, "property_id": "PROP-2024-RY-002",
                  "transaction_price": 3_200_000, "built_up_area_m2": 600.0}


# ---------------------------------------------------------------------------
# MOD-01 → MOD-05  detect_ood — unit tests
# ---------------------------------------------------------------------------

def test_mod_01_empty_input_returns_empty():
    assert detect_ood([]) == []


def test_mod_02_single_unit_returns_one_result():
    results = detect_ood([_NORMAL_UNIT])
    assert len(results) == 1
    score, status = results[0]
    assert isinstance(score, float)
    assert status in {"in_distribution", "out_of_distribution"}


def test_mod_03_small_batch_uses_fallback_correct_length():
    """Batches with < 4 units use Z-score fallback — result length matches input."""
    batch = _NORMAL_BATCH[:3]
    results = detect_ood(batch)
    assert len(results) == len(batch)
    for score, status in results:
        assert isinstance(score, float)
        assert status in {"in_distribution", "out_of_distribution"}


def test_mod_04_extreme_outlier_flagged_as_ood():
    """A property with extreme area (50 000 m²) in a normal batch must be OOD."""
    batch = _NORMAL_BATCH + [_OUTLIER_UNIT]
    results = detect_ood(batch)
    assert len(results) == len(batch)
    # Last unit is the outlier
    _, status = results[-1]
    assert status == "out_of_distribution", (
        f"Extreme property (area=50000) expected 'out_of_distribution', got '{status}'"
    )


def test_mod_05_normal_properties_in_distribution():
    """All normal properties in a homogeneous batch should be in_distribution."""
    batch = _NORMAL_BATCH + [_OUTLIER_UNIT]
    results = detect_ood(batch)
    # First 8 are the normal batch
    for i, (score, status) in enumerate(results[:8]):
        assert status == "in_distribution", (
            f"Normal property {i} should be in_distribution, got {status!r}"
        )


# ---------------------------------------------------------------------------
# MOD-06 → MOD-07  Runner integration (M-06)
# ---------------------------------------------------------------------------

def test_mod_06_predictions_have_ood_score():
    """Every prediction returned by the runner must include an ood_score."""
    runner = MassValuationRunner()
    result = runner.run([VALID_RECORD, VALID_RECORD_2])
    for pred in result["predictions"]:
        assert "ood_score" in pred, "Prediction missing ood_score (M-06)"
        assert isinstance(pred["ood_score"], float)


def test_mod_07_ood_property_count_matches_predictions():
    """ood_property_count in run record must equal count of OOD predictions."""
    runner = MassValuationRunner()
    result = runner.run([VALID_RECORD, VALID_RECORD_2])
    actual_ood = sum(
        1 for p in result["predictions"]
        if p.get("distribution_status") == "out_of_distribution"
    )
    assert result["ood_property_count"] == actual_ood, (
        f"ood_property_count={result['ood_property_count']} != "
        f"actual count={actual_ood}"
    )


# ---------------------------------------------------------------------------
# MOD-08 → MOD-10  _compute_pi_coverage (M-05)
# ---------------------------------------------------------------------------

def test_mod_08_pi_coverage_100pct_when_sales_inside_bounds():
    """All sale prices exactly at estimated_value → coverage = 1.0 (within PI)."""
    n = 10
    units = [{"sale_price": 1_000_000.0} for _ in range(n)]
    preds = [
        {
            "prediction_interval_low":  850_000.0,
            "prediction_interval_high": 1_150_000.0,
        }
        for _ in range(n)
    ]
    report = _compute_pi_coverage(units, preds)
    assert report["coverage_fraction"] == 1.0
    assert report["meets_90pct_threshold"] is True
    assert report["insufficient_sales_for_coverage_check"] is False


def test_mod_09_pi_coverage_below_90_reported_correctly():
    """When most sales are outside PI, meets_90pct_threshold must be False."""
    n = 10
    units = [{"sale_price": 2_000_000.0} for _ in range(n)]  # all outside PI
    preds = [
        {
            "prediction_interval_low":  850_000.0,
            "prediction_interval_high": 1_150_000.0,
        }
        for _ in range(n)
    ]
    report = _compute_pi_coverage(units, preds)
    assert report["coverage_fraction"] == 0.0
    assert report["meets_90pct_threshold"] is False


def test_mod_10_insufficient_sales_flagged():
    """Fewer than 5 sold units → insufficient_sales_for_coverage_check=True."""
    units = [{"sale_price": 1_000_000.0} for _ in range(3)]
    preds = [
        {"prediction_interval_low": 850_000.0, "prediction_interval_high": 1_150_000.0}
        for _ in range(3)
    ]
    report = _compute_pi_coverage(units, preds)
    assert report["insufficient_sales_for_coverage_check"] is True
    assert report["coverage_fraction"] is None
    assert report["meets_90pct_threshold"] is None


# ---------------------------------------------------------------------------
# MOD-11  PI coverage present in run record iaao_summary
# ---------------------------------------------------------------------------

def test_mod_11_pi_coverage_in_iaao_summary():
    """iaao_summary in run result must include pi_coverage key after P4."""
    runner = MassValuationRunner()
    result = runner.run([VALID_RECORD, VALID_RECORD_2])
    iaao = result.get("iaao_summary", {})
    assert "pi_coverage" in iaao, (
        "iaao_summary must contain pi_coverage after M-05 integration"
    )
    pc = iaao["pi_coverage"]
    assert "n_sold_units" in pc
    assert "insufficient_sales_for_coverage_check" in pc


# ---------------------------------------------------------------------------
# MOD-12  ood_score hidden from user role (RBAC)
# ---------------------------------------------------------------------------

def test_mod_12_ood_score_hidden_from_user_role():
    """ood_score is a technical field — must not appear in user-role output."""
    pred_with_ood = {
        "prediction_id": "p1", "property_id": "PROP-001",
        "estimated_value": 1_000_000, "unit_value": 2000,
        "prediction_interval_low": 850_000,
        "prediction_interval_high": 1_150_000,
        "confidence": "medium",
        "distribution_status": "in_distribution",
        "ood_score": -0.12,
        "review_status": "manual_review_required",
        "limitations": [], "advisory_only": True,
        "shap_values": {}, "quality_flags": [],
        "comparable_ids": [], "model_version": "hedonic-v1",
    }
    user_view = OutputBuilder().filter_prediction(pred_with_ood, "user")
    assert "ood_score" not in user_view, "ood_score must be hidden from user role"

    analyst_view = OutputBuilder().filter_prediction(pred_with_ood, "analyst")
    assert "ood_score" in analyst_view, "ood_score must be visible to analyst role"


# ---------------------------------------------------------------------------
# OOD backend-selection tests  (OOD_BACKEND_SELECTION_TEST_COUNT = 6)
# ---------------------------------------------------------------------------

class TestOODBackendSelection:
    """Six tests proving explicit backend governance.

    All six use monkeypatch so they are independent of the environment-level
    AVM_OOD_BACKEND value and of whether sklearn is actually installed.
    """

    def test_zscore_forces_fallback_even_with_sklearn(self, monkeypatch):
        """AVM_OOD_BACKEND=zscore uses Z-score even when sklearn is installed."""
        monkeypatch.setenv("AVM_OOD_BACKEND", "zscore")
        import core_engine.mass_valuation.ood_detector as _mod
        assert _mod._SKLEARN_AVAILABLE, "sklearn must be installed for this test to be non-trivial"
        results = _mod.detect_ood(_NORMAL_BATCH)
        assert len(results) == len(_NORMAL_BATCH)
        for _, label in results:
            assert label == "in_distribution"

    def test_isolation_forest_uses_sklearn(self, monkeypatch):
        """AVM_OOD_BACKEND=isolation_forest uses IsolationForest when sklearn installed."""
        monkeypatch.setenv("AVM_OOD_BACKEND", "isolation_forest")
        import core_engine.mass_valuation.ood_detector as _mod
        assert _mod._SKLEARN_AVAILABLE, "sklearn must be installed"
        results = _mod.detect_ood(_NORMAL_BATCH)
        assert len(results) == len(_NORMAL_BATCH)
        for score, label in results:
            assert isinstance(score, float)
            assert label in {"in_distribution", "out_of_distribution"}

    def test_dependency_presence_does_not_select_backend(self, monkeypatch):
        """With AVM_OOD_BACKEND=zscore, Z-score is used even when sklearn is present."""
        monkeypatch.setenv("AVM_OOD_BACKEND", "zscore")
        import core_engine.mass_valuation.ood_detector as _mod
        assert _mod._SKLEARN_AVAILABLE, "sklearn must be installed for this assertion to be meaningful"
        # Outlier batch — outlier must be OOD under Z-score too
        batch_with_outlier = _NORMAL_BATCH + [_OUTLIER_UNIT]
        results = _mod.detect_ood(batch_with_outlier)
        _, outlier_label = results[-1]
        assert outlier_label == "out_of_distribution"
        for _, label in results[:8]:
            assert label == "in_distribution"

    def test_unsupported_backend_raises_configuration_error(self, monkeypatch):
        """Unsupported AVM_OOD_BACKEND value raises OODBackendConfigurationError."""
        monkeypatch.setenv("AVM_OOD_BACKEND", "random_forest")
        with pytest.raises(OODBackendConfigurationError):
            detect_ood(_NORMAL_BATCH)

    def test_isolation_forest_without_sklearn_raises_unavailable_error(self, monkeypatch):
        """isolation_forest backend raises OODBackendUnavailableError when sklearn absent."""
        monkeypatch.setenv("AVM_OOD_BACKEND", "isolation_forest")
        import core_engine.mass_valuation.ood_detector as _mod
        monkeypatch.setattr(_mod, "_SKLEARN_AVAILABLE", False)
        with pytest.raises(OODBackendUnavailableError):
            _mod.detect_ood(_NORMAL_BATCH)

    def test_zscore_works_when_sklearn_unavailable(self, monkeypatch):
        """Z-score backend works even when sklearn is patched as unavailable."""
        monkeypatch.setenv("AVM_OOD_BACKEND", "zscore")
        import core_engine.mass_valuation.ood_detector as _mod
        monkeypatch.setattr(_mod, "_SKLEARN_AVAILABLE", False)
        results = _mod.detect_ood(_NORMAL_BATCH)
        assert len(results) == len(_NORMAL_BATCH)
        for _, label in results:
            assert label == "in_distribution"
