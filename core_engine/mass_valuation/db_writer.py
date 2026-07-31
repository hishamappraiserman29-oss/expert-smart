"""
db_writer.py — P2 DB persistence for mass valuation runs.
Uses raw SQL (session.execute + text()) against the 3 tables defined in schema.sql.
Graceful degradation: all public functions return None/[]/0 on DB failure rather
than propagating exceptions to callers.
advisory_only=True and certification_ready=False are re-enforced on every read.
reviewed_by <> 'system' is validated in Python before any DB write.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from sqlalchemy import text as _sa_text
except ImportError:
    def _sa_text(q):  # pragma: no cover — only used when sqlalchemy unavailable
        return q

_VALID_DECISIONS = frozenset({"accepted", "overridden", "rejected"})


# ---------------------------------------------------------------------------
# Internal validators — raise ValueError before touching the DB
# ---------------------------------------------------------------------------

def _validate_reviewed_by(reviewed_by: str) -> None:
    if reviewed_by == "system":
        raise ValueError("reviewed_by cannot be 'system' — human review required (G-02)")


def _validate_decision(decision: str) -> None:
    if decision not in _VALID_DECISIONS:
        raise ValueError(
            f"decision must be one of {sorted(_VALID_DECISIONS)}, got: {decision!r}"
        )


def _validate_reason(reason: str) -> None:
    if not reason or not reason.strip():
        raise ValueError("reason is required for review decisions")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def _parse_jsonb(value: Any, default: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return default
    return value if value is not None else default


# ---------------------------------------------------------------------------
# Write — mass_valuation_runs
# ---------------------------------------------------------------------------

def save_run(run_result: Dict[str, Any], db) -> Optional[str]:
    """
    Persist MassValuationRun to mass_valuation_runs.
    Returns run_id (str) on success, None on DB error.
    advisory_only and certification_ready are hard-coded TRUE/FALSE in SQL.
    """
    run_id = run_result.get("run_id", str(uuid.uuid4()))
    try:
        db.execute(_sa_text("""
            INSERT INTO mass_valuation_runs (
                run_id, run_name, property_type, jurisdiction, status, method,
                n_input_records, n_rejected, n_flagged, n_training_records,
                n_predicted_properties, ood_property_count,
                manual_review_required_count, dataset_hash, random_seed,
                iaao_summary, advisory_only, certification_ready,
                started_at, completed_at
            ) VALUES (
                :run_id, :run_name, :property_type, :jurisdiction, :status, :method,
                :n_input, :n_rejected, :n_flagged, :n_training,
                :n_predicted, :ood_count, :manual_review_count,
                :dataset_hash, :random_seed,
                cast(:iaao_summary AS jsonb), TRUE, FALSE,
                :started_at, :completed_at
            )
            ON CONFLICT (run_id) DO NOTHING
        """), {
            "run_id":             run_id,
            "run_name":           run_result.get("run_name") or "Unnamed Run",
            "property_type":      run_result.get("property_type") or "residential",
            "jurisdiction":       run_result.get("jurisdiction") or "SA",
            "status":             run_result.get("status") or "validated",
            "method":             run_result.get("method") or "avm",
            "n_input":            int(run_result.get("n_input_records", 0)),
            "n_rejected":         int(run_result.get("n_rejected", 0)),
            "n_flagged":          int(run_result.get("n_flagged", 0)),
            "n_training":         int(run_result.get("n_training_records", 0)),
            "n_predicted":        int(run_result.get("n_predicted_properties", 0)),
            "ood_count":          int(run_result.get("ood_property_count", 0)),
            "manual_review_count": int(run_result.get("manual_review_required_count", 0)),
            "dataset_hash":       run_result.get("dataset_hash"),
            "random_seed":        int(run_result.get("random_seed", 42)),
            "iaao_summary":       _json(run_result.get("iaao_summary") or {}),
            "started_at":         run_result.get("started_at") or _utcnow(),
            "completed_at":       run_result.get("completed_at") or _utcnow(),
        })
        db.commit()
        return run_id
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return None


# ---------------------------------------------------------------------------
# Write — property_predictions
# ---------------------------------------------------------------------------

def save_predictions(
    predictions: List[Dict[str, Any]],
    run_id: str,
    db,
) -> int:
    """
    Persist property predictions to property_predictions.
    Returns count of rows saved (0 on error).
    advisory_only hard-coded TRUE in SQL.
    """
    saved = 0
    try:
        for pred in predictions:
            db.execute(_sa_text("""
                INSERT INTO property_predictions (
                    prediction_id, run_id, property_id,
                    estimated_value, unit_value,
                    prediction_interval_low, prediction_interval_high,
                    confidence, distribution_status, review_status,
                    model_version, shap_values, quality_flags,
                    comparable_ids, limitations, advisory_only
                ) VALUES (
                    :pred_id, :run_id, :property_id,
                    :estimated_value, :unit_value,
                    :pi_low, :pi_high,
                    :confidence, :dist_status, :review_status,
                    :model_version,
                    cast(:shap_values   AS jsonb),
                    cast(:quality_flags AS jsonb),
                    cast(:comparable_ids AS jsonb),
                    cast(:limitations   AS jsonb),
                    TRUE
                )
                ON CONFLICT (prediction_id) DO NOTHING
            """), {
                "pred_id":        pred.get("prediction_id") or str(uuid.uuid4()),
                "run_id":         run_id,
                "property_id":    str(pred.get("property_id", "")),
                "estimated_value": pred.get("estimated_value"),
                "unit_value":     pred.get("unit_value"),
                "pi_low":         pred.get("prediction_interval_low"),
                "pi_high":        pred.get("prediction_interval_high"),
                "confidence":     pred.get("confidence", "low"),
                "dist_status":    pred.get("distribution_status", "unknown"),
                "review_status":  pred.get("review_status", "manual_review_required"),
                "model_version":  pred.get("model_version", "hedonic-v1"),
                "shap_values":    _json(pred.get("shap_values") or {}),
                "quality_flags":  _json(pred.get("quality_flags") or []),
                "comparable_ids": _json(pred.get("comparable_ids") or []),
                "limitations":    _json(pred.get("limitations") or []),
            })
            saved += 1
        db.commit()
        return saved
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return 0


# ---------------------------------------------------------------------------
# Read — mass_valuation_runs (list)
# ---------------------------------------------------------------------------

def list_runs(
    db,
    role: str = "analyst",
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Return recent runs from mass_valuation_runs, RBAC-filtered by role.
    Returns [] on DB error.
    """
    base_cols = (
        "run_id, run_name, property_type, jurisdiction, status, method, "
        "n_input_records, n_rejected, n_predicted_properties, "
        "advisory_only, certification_ready, started_at"
    )
    analyst_cols = ", n_flagged, ood_property_count, manual_review_required_count, iaao_summary"
    admin_cols   = ", dataset_hash, random_seed, completed_at"

    if role == "admin":
        cols = base_cols + analyst_cols + admin_cols
    elif role == "analyst":
        cols = base_cols + analyst_cols
    else:
        cols = base_cols

    try:
        rows = db.execute(
            _sa_text(f"SELECT {cols} FROM mass_valuation_runs "
                 "ORDER BY started_at DESC NULLS LAST LIMIT :limit"),
            {"limit": max(1, int(limit))},
        ).mappings().all()

        result = []
        for row in rows:
            d = dict(row)
            d["advisory_only"]       = True
            d["certification_ready"] = False
            if "iaao_summary" in d:
                d["iaao_summary"] = _parse_jsonb(d["iaao_summary"], {})
            result.append(d)
        return result
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Read — property_predictions (by run)
# ---------------------------------------------------------------------------

def get_predictions_for_run(
    run_id: str,
    db,
) -> List[Dict[str, Any]]:
    """
    Return all predictions for a run_id from property_predictions.
    Returns [] on DB error or run not found.
    """
    try:
        rows = db.execute(_sa_text("""
            SELECT prediction_id, run_id, property_id,
                   estimated_value, unit_value,
                   prediction_interval_low, prediction_interval_high,
                   confidence, distribution_status, review_status,
                   model_version, shap_values, quality_flags,
                   comparable_ids, limitations, advisory_only
            FROM property_predictions
            WHERE run_id = :run_id
            ORDER BY property_id
        """), {"run_id": run_id}).mappings().all()

        result = []
        for row in rows:
            d = dict(row)
            d["advisory_only"] = True
            for field, default in (
                ("shap_values",   {}),
                ("quality_flags", []),
                ("comparable_ids", []),
                ("limitations",   []),
            ):
                d[field] = _parse_jsonb(d.get(field), default)
            result.append(d)
        return result
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Write — review_decisions
# ---------------------------------------------------------------------------

def save_review_decision(
    prediction_id: str,
    run_id: str,
    decision: str,
    reason: str,
    reviewed_by: str,
    db,
    property_id: str = "",
    model_value: Optional[float] = None,
    reviewed_value: Optional[float] = None,
) -> Optional[str]:
    """
    Persist a human review decision to review_decisions.
    Raises ValueError if reviewed_by='system', decision is invalid, or reason is empty.
    Returns decision_id (str) on success, None on DB error.
    """
    _validate_reviewed_by(reviewed_by)
    _validate_decision(decision)
    _validate_reason(reason)

    decision_id = str(uuid.uuid4())
    try:
        db.execute(_sa_text("""
            INSERT INTO review_decisions (
                decision_id, prediction_id, property_id, run_id,
                model_value, reviewed_value,
                decision, reason, reviewed_by, reviewed_at
            ) VALUES (
                :decision_id, :prediction_id, :property_id, :run_id,
                :model_value, :reviewed_value,
                :decision, :reason, :reviewed_by, :reviewed_at
            )
        """), {
            "decision_id":   decision_id,
            "prediction_id": prediction_id,
            "property_id":   property_id or "",
            "run_id":        run_id,
            "model_value":   model_value,
            "reviewed_value": reviewed_value,
            "decision":      decision,
            "reason":        reason.strip(),
            "reviewed_by":   reviewed_by,
            "reviewed_at":   _utcnow(),
        })
        db.commit()
        return decision_id
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return None
