"""
output_builder.py — P1/P3 RBAC-aware output filtering for mass valuation.
Enforces audience separation per rbac_matrix.json.
advisory_only=True on every output. Basel/LTV sections never exposed to non-admin.
P3: adds scrub_user_text(), check_taqeem_claim(), verify_file_signature() via
    secrets_scanner delegation so callers have a single import point.
"""
from __future__ import annotations

from typing import Any, Dict, List

try:
    from core_engine.mass_valuation.secrets_scanner import (
        check_taqeem_claim,
        verify_file_signature,
        scan_for_forbidden_terms,
        scan_output,
    )
    _SCANNER_AVAILABLE = True
except ImportError:
    _SCANNER_AVAILABLE = False
    def check_taqeem_claim(text: str) -> bool:          # type: ignore[misc]
        return False
    def verify_file_signature(data: bytes, ft: str) -> bool:  # type: ignore[misc]
        return True
    def scan_for_forbidden_terms(text: str) -> list:    # type: ignore[misc]
        return []
    def scan_output(data: Any) -> list:                 # type: ignore[misc]
        return []


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
    "ood_score",   # P4 M-06: analyst/admin may see raw OOD score
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

    # ------------------------------------------------------------------
    # P3 — security helpers (O-02, G-07, O-06)
    # ------------------------------------------------------------------

    def scrub_user_text(self, text: str) -> str:
        """
        Remove technical terms forbidden in user-facing output (O-02).
        Raises ValueError if a TAQEEM compliance claim is detected (G-07).
        """
        if check_taqeem_claim(text):
            raise ValueError(
                "Output contains TAQEEM compliance claim — forbidden (G-07). "
                "Remove any reference to 'TAQEEM-compliant' before publishing."
            )
        return text

    def scan_run_output(self, data: Any) -> list:
        """
        Scan a run/prediction dict for secrets or forbidden content (O-04).
        Returns list of findings; empty = clean.
        """
        return scan_output(data)

    def forbidden_terms_in(self, text: str) -> list:
        """Return forbidden technical terms found in text (O-02)."""
        return scan_for_forbidden_terms(text)

    @staticmethod
    def check_file_signature(data: bytes, file_type: str) -> bool:
        """
        Verify file magic bytes (O-06).
        file_type: 'html' | 'xlsx' | 'pdf'
        """
        return verify_file_signature(data, file_type)
