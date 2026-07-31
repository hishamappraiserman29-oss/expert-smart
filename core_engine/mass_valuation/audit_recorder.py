"""
audit_recorder.py — P1 audit trail building for mass valuation runs.
Builds AuditTrailRecord conforming to audit_trail.schema.json.
advisory_only=True and certification_ready=False are invariants.
Storage: written to audit_logs.details_json (P0 strategy); P1 adds dedicated table.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _sha256_of(obj: Any) -> str:
    canonical = json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


_DEFAULT_FEATURE_SCHEMA: Dict[str, Any] = {
    "version": "1.0.0",
    "fields": [
        "property_id", "property_type", "land_area_m2",
        "built_up_area_m2", "age", "condition", "use",
        "transaction_date", "transaction_price",
    ],
}


def compute_artifact_hashes(artifacts: Dict[str, bytes]) -> Dict[str, str]:
    """O-05: SHA-256 each artifact. Returns {filename: 64-char hex digest}."""
    return {name: hashlib.sha256(data).hexdigest() for name, data in artifacts.items()}


def build_audit_record(
    run_result: Dict[str, Any],
    code_commit: str = "unknown",
    standard_version_id: str = "IAAO-2023",
    hyperparameters: Optional[Dict] = None,
    feature_schema: Optional[Dict] = None,
    artifact_hashes: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Build an AuditTrailRecord from a completed run result dict.
    Structural only — no value logic.
    """
    run_id       = run_result.get("run_id", str(uuid.uuid4()))
    dataset_hash = run_result.get("dataset_hash", "0" * 64)
    feat_schema  = feature_schema or _DEFAULT_FEATURE_SCHEMA
    feat_hash    = _sha256_of(feat_schema)

    run_hash = _sha256_of({
        "run_id":      run_id,
        "dataset_hash": dataset_hash,
        "random_seed": run_result.get("random_seed", 0),
    })
    model_hash = "0" * 64  # placeholder until ML model artifact is persisted

    iaao = run_result.get("iaao_summary", {})

    return {
        "audit_id":            str(uuid.uuid4()),
        "run_id":              run_id,
        "dataset_id":          f"dataset-{dataset_hash[:8]}",
        "model_id":            "hedonic-v1",
        "run_hash":            run_hash,
        "dataset_hash":        dataset_hash,
        "model_hash":          model_hash,
        "code_commit":         code_commit,
        "feature_schema":      feat_schema,
        "feature_schema_hash": feat_hash,
        "hyperparameters":     hyperparameters or {
            "method":      run_result.get("method", "avm"),
            "random_seed": run_result.get("random_seed", 42),
        },
        "random_seed":         run_result.get("random_seed", 42),
        "training_period": {
            "start_date": "2023-01-01",
            "end_date":   "2024-12-31",
        },
        "validation_strategy": {
            "type":               "temporal_split",
            "temporal_holdout":   {"description": "last 20% by transaction_date"},
            "geographic_holdout": {"description": "holdout region set per run config"},
            "leakage_check":      True,
        },
        "standard_version_id": standard_version_id,
        "iaao_metrics": {
            "cod":       iaao.get("cod"),
            "prd":       iaao.get("prd"),
            "prb":       iaao.get("prb"),
            "r_squared": None,
        },
        "user_overrides":      [],
        "approval_events":     [],
        "artifact_hashes":     artifact_hashes or {},
        "created_at":          datetime.now(timezone.utc).isoformat(),
        "advisory_only":       True,
        "certification_ready": False,
    }
