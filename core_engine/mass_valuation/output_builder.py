"""
output_builder.py — P1 RBAC-aware output filtering for mass valuation.
Enforces audience separation per rbac_matrix.json.
advisory_only=True on every output. Basel/LTV sections never exposed to non-admin.
"""
from __future__ import annotations

from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Field-level access sets (from rbac_matrix.json)
# ---------------------------------------------------------------------------

_PRED_USER_FIELDS = frozenset({
    "prediction_id", "property_id", "estimated_value", "unit_value",
    "prediction_interval_low", "prediction_interval_high",
    "confidence", "distribution_status", "limitations", "advisory_only",
})

_PRED_ANALYST_EXTRA = frozenset({
    "shap_values", "quality_flags", "comparable_ids",
    "model_version", "review_status",
})

_RUN_USER_FIELDS = frozenset({
    "run_id", "run_name", "property_type", "jurisdiction",
    "status", "method", "n_predicted_properties",
    "advisory_only", "certification_ready",
})

_RUN_ANALYST_EXTRA = frozenset({
    "n_input_records", "n_rejected", "n_flagged",
    "n_training_records", "iaao_summary",
    "ood_property_count", "manual_review_required_count",
})

_RUN_ADMIN_EXTRA = frozenset({
    "dataset_hash", "random_seed", "validation_report",
    "started_at", "completed_at",
})


class OutputBuilder:
    """
    Filters prediction and run records to role-permitted fields.
    Roles: user / analyst / admin.
    Unknown roles are treated as user (most restrictive).
    """

    def filter_prediction(self, prediction: Dict[str, Any], role: str) -> Dict[str, Any]:
        """Return prediction dict with only fields allowed for role."""
        if role == "admin":
            filtered = dict(prediction)
        elif role == "analyst":
            allowed  = _PRED_USER_FIELDS | _PRED_ANALYST_EXTRA
            filtered = {k: v for k, v in prediction.items() if k in allowed}
        else:
            filtered = {k: v for k, v in prediction.items() if k in _PRED_USER_FIELDS}
            # Round estimated_value to nearest 1,000 SAR for user role
            ev = filtered.get("estimated_value")
            if ev is not None:
                filtered["estimated_value"] = round(ev / 1000) * 1000

        filtered["advisory_only"] = True
        return filtered

    def filter_run(self, run_record: Dict[str, Any], role: str) -> Dict[str, Any]:
        """Return run record filtered for role, with nested predictions filtered."""
        preds = run_record.get("predictions", [])

        if role == "admin":
            allowed  = _RUN_USER_FIELDS | _RUN_ANALYST_EXTRA | _RUN_ADMIN_EXTRA
            # Admin gets everything except the raw predictions list (replaced below)
            filtered = {k: v for k, v in run_record.items()
                        if k != "predictions" and k in (allowed | {"audit_trail_id"})}
            filtered["predictions"] = [self.filter_prediction(p, "admin") for p in preds]
        elif role == "analyst":
            allowed  = _RUN_USER_FIELDS | _RUN_ANALYST_EXTRA
            filtered = {k: v for k, v in run_record.items() if k in allowed}
            filtered["predictions"] = [self.filter_prediction(p, "analyst") for p in preds]
        else:
            filtered = {k: v for k, v in run_record.items() if k in _RUN_USER_FIELDS}
            filtered["predictions"] = [self.filter_prediction(p, "user") for p in preds]

        filtered["advisory_only"]       = True
        filtered["certification_ready"] = False
        return filtered

    def filter_predictions_list(
        self,
        predictions: List[Dict[str, Any]],
        role: str,
    ) -> List[Dict[str, Any]]:
        return [self.filter_prediction(p, role) for p in predictions]
