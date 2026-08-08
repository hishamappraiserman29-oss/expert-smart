"""
ood_detector.py — P4 Out-of-Distribution detection for mass valuation units.
M-06: every prediction receives a real ood_score and distribution_status.

Backend selection (explicit — dependency presence never selects the algorithm):
    AVM_OOD_BACKEND=isolation_forest (default): uses scikit-learn IsolationForest.
    AVM_OOD_BACKEND=zscore:                    uses MAD-based robust Z-score (pure Python).

Score convention (mirrors IsolationForest.decision_function):
    ood_score > 0  → within expected distribution
    ood_score ≤ 0  → potentially out-of-distribution
distribution_status ∈ {"in_distribution", "out_of_distribution"}
"""
from __future__ import annotations

import os as _os
from typing import Any, Dict, List, Tuple

try:
    from sklearn.ensemble import IsolationForest as _IsolationForest
    import numpy as _np
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False


# Public constant — importable by CI assertions and tests
DEFAULT_AVM_OOD_BACKEND: str = "isolation_forest"

_ZSCORE_THRESHOLD = 2.5   # max robust Z across features triggers OOD
_IF_THRESHOLD     = 0.0   # IsolationForest.decision_function sign boundary

_SUPPORTED_BACKENDS = frozenset({"zscore", "isolation_forest"})


class OODBackendConfigurationError(ValueError):
    """Raised when AVM_OOD_BACKEND is set to an unsupported value."""


class OODBackendUnavailableError(RuntimeError):
    """Raised when the requested backend requires a dependency that is not installed."""


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

def _features(unit: Dict[str, Any]) -> List[float]:
    """Extract numeric OOD features from an appraisal-result unit dict."""
    return [
        float(unit.get("area",       100.0)),
        float(unit.get("floor",      1.0)),
        float(unit.get("year_built", 2010.0)),
        float(unit.get("final_ppm",  0.0)),
    ]


# ---------------------------------------------------------------------------
# Backend resolution
# ---------------------------------------------------------------------------

def _get_backend() -> str:
    """Return the configured OOD backend, validated against supported values."""
    raw = _os.environ.get("AVM_OOD_BACKEND", DEFAULT_AVM_OOD_BACKEND).strip().lower()
    if raw not in _SUPPORTED_BACKENDS:
        raise OODBackendConfigurationError(
            f"Unsupported AVM_OOD_BACKEND={raw!r}. "
            f"Supported values: {sorted(_SUPPORTED_BACKENDS)!r}. "
            "Set AVM_OOD_BACKEND=zscore or AVM_OOD_BACKEND=isolation_forest."
        )
    return raw


def resolve_backend() -> str:
    """
    Wave 4B2: public accessor for the resolved OOD backend identity.

    detect_ood() itself never returns which backend produced its results
    (score/status only), so callers that need to persist provenance call
    this separately. Uses the same env-var resolution and validation as
    detect_ood() — raises OODBackendConfigurationError under the same
    conditions, so a caller resolving this before detect_ood() will see
    the same error detect_ood() would have raised.
    """
    return _get_backend()


# ---------------------------------------------------------------------------
# Robust Z-score helpers (MAD-based)
# ---------------------------------------------------------------------------

def _median(values: List[float]) -> float:
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return (s[mid - 1] + s[mid]) / 2.0 if n % 2 == 0 else s[mid]


def _robust_zscore_fallback(units: List[Dict[str, Any]]) -> List[Tuple[float, str]]:
    """
    MAD-based robust Z-score OOD detection (no external dependencies).
    Uses max robust Z-score across features; robust to outlier masking.
    Returns list of (ood_score, distribution_status) parallel to `units`.
    """
    if not units:
        return []

    feat_matrix = [_features(u) for u in units]
    n_feats = len(feat_matrix[0])

    # Per-feature robust statistics
    medians: List[float] = [
        _median([row[j] for row in feat_matrix]) for j in range(n_feats)
    ]
    scaled_mads: List[float] = []
    for j in range(n_feats):
        abs_devs = [abs(row[j] - medians[j]) for row in feat_matrix]
        raw_mad = _median(abs_devs) * 1.4826   # scale to match std for Normal
        scaled_mads.append(max(raw_mad, 1.0))  # prevent division by zero

    results: List[Tuple[float, str]] = []
    for row in feat_matrix:
        z_scores = [abs(row[j] - medians[j]) / scaled_mads[j] for j in range(n_feats)]
        max_z = max(z_scores)
        # Score: 0 = typical unit, increasingly negative = increasingly anomalous
        ood_score = round(-(max_z / 5.0), 4)
        status = "out_of_distribution" if max_z > _ZSCORE_THRESHOLD else "in_distribution"
        results.append((ood_score, status))

    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_ood(
    units: List[Dict[str, Any]],
    random_seed: int = 42,
) -> List[Tuple[float, str]]:
    """
    Compute (ood_score, distribution_status) for each unit in the batch.

    Backend is selected by AVM_OOD_BACKEND environment variable:
        "isolation_forest" (default): uses scikit-learn IsolationForest.
        "zscore": uses MAD-based robust Z-score (pure Python, no dependencies).

    Raises OODBackendConfigurationError for unsupported AVM_OOD_BACKEND values.
    Raises OODBackendUnavailableError if isolation_forest is requested but sklearn absent.

    Dependency presence never selects the backend.

    Parameters
    ----------
    units       : list of appraisal-result unit dicts (area, floor, year_built, final_ppm).
    random_seed : passed to IsolationForest for reproducibility.

    Returns
    -------
    List parallel to `units` — each element (ood_score: float, status: str).
    Returns [] for empty input.
    """
    if not units:
        return []

    if len(units) < 4:
        # Both backends use Z-score for tiny batches (IsolationForest needs ≥4 samples)
        return _robust_zscore_fallback(units)

    backend = _get_backend()

    if backend == "zscore":
        return _robust_zscore_fallback(units)

    # backend == "isolation_forest"
    if not _SKLEARN_AVAILABLE:
        raise OODBackendUnavailableError(
            "AVM_OOD_BACKEND=isolation_forest requires scikit-learn, which is not installed. "
            "Install scikit-learn (see core_engine/requirements-ml.txt) or "
            "set AVM_OOD_BACKEND=zscore."
        )

    X = _np.array([_features(u) for u in units], dtype=float)
    clf = _IsolationForest(
        n_estimators=100,
        contamination="auto",
        random_state=random_seed,
    )
    clf.fit(X)
    scores = clf.decision_function(X)
    return [
        (
            round(float(s), 4),
            "in_distribution" if s >= _IF_THRESHOLD else "out_of_distribution",
        )
        for s in scores
    ]
