"""
runner.py — P1 Mass Valuation MVP Runner.
Orchestrates: validate → appraise → build predictions → record audit.
No valuation logic — delegates to mass_appraisal.run_mass_appraisal().
advisory_only=True on every output. certification_ready=False always.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core_engine.mass_valuation.contract.schema_validator import (
    BatchValidationResult,
    SchemaValidator,
    ValidationResult,
)
from core_engine.mass_appraisal import run_mass_appraisal


# ---------------------------------------------------------------------------
# Field mapping: data_contract → mass_appraisal unit dict
# ---------------------------------------------------------------------------

def _current_year() -> int:
    return datetime.now(timezone.utc).year


def _to_appraisal_unit(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a data-contract record to mass_appraisal unit format."""
    age = rec.get("age")
    if age is not None:
        try:
            year_built = _current_year() - int(float(age))
        except (TypeError, ValueError):
            year_built = 2010
    else:
        year_built = 2010

    area = rec.get("built_up_area_m2") or rec.get("land_area_m2") or 100.0

    return {
        "id":         str(rec.get("property_id", f"PROP-{uuid.uuid4().hex[:8]}")),
        "area":       float(area),
        "floor":      1.0,
        "year_built": int(year_built),
        "condition":  str(rec.get("condition", "good")).lower(),
        "sale_price": float(rec.get("transaction_price", 0) or 0),
    }


def _sha256_of(obj: Any) -> str:
    """SHA-256 of the canonical JSON representation of an object."""
    canonical = json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Prediction builder
# ---------------------------------------------------------------------------

def _build_predictions(units: List[Dict], run_id: str) -> List[Dict]:
    """Convert mass_appraisal per-unit results to PropertyPrediction records."""
    predictions: List[Dict] = []
    for u in units:
        unit_value  = float(u.get("unit_value", 0) or 0)
        area        = float(u.get("area", 1) or 1)
        unit_per_m2 = round(unit_value / area, 0) if area > 0 else None

        if unit_value <= 0:
            dist_status = "insufficient_evidence"
            confidence  = "insufficient"
            estimated   = None
            pi_low      = None
            pi_high     = None
            limitations = ["insufficient_evidence: no positive value produced by model"]
        else:
            dist_status = "in_distribution"
            confidence  = "medium"
            estimated   = round(unit_value, 0)
            pi_low      = round(unit_value * 0.85, 0)
            pi_high     = round(unit_value * 1.15, 0)
            limitations = []

        predictions.append({
            "prediction_id":            str(uuid.uuid4()),
            "run_id":                   run_id,
            "property_id":              str(u.get("id", "UNKNOWN")),
            "estimated_value":          estimated,
            "unit_value":               unit_per_m2,
            "prediction_interval_low":  pi_low,
            "prediction_interval_high": pi_high,
            "confidence":               confidence,
            "distribution_status":      dist_status,
            "review_status":            "manual_review_required",
            "quality_flags":            [],
            "comparable_ids":           [],
            "shap_values":              {},
            "model_version":            "hedonic-v1",
            "limitations":              limitations,
            "advisory_only":            True,
        })

    return predictions


# ---------------------------------------------------------------------------
# MassValuationRunner
# ---------------------------------------------------------------------------

class MassValuationRunner:
    """
    P1 MVP runner for mass valuation.
    Validates records using SchemaValidator, delegates computation to
    run_mass_appraisal(), then wraps results in a MassValuationRun record.
    advisory_only=True and certification_ready=False are invariants.
    """

    advisory_only:       bool = True
    certification_ready: bool = False

    def __init__(
        self,
        run_name: str = "MVP Run",
        property_type: str = "residential",
        jurisdiction: str = "SA",
        method: str = "avm",
        iaao_thresholds: Optional[Dict] = None,
        random_seed: int = 42,
    ) -> None:
        self.run_name        = run_name
        self.property_type   = property_type
        self.jurisdiction    = jurisdiction
        self.method          = method
        self.iaao_thresholds = iaao_thresholds
        self.random_seed     = random_seed
        self._validator      = SchemaValidator()

    def run(
        self,
        records: List[Dict[str, Any]],
        base_market_ppm: float = 0.0,
        location: str = "Riyadh",
    ) -> Dict[str, Any]:
        """
        Execute a mass valuation run.

        Steps:
          1. Validate all records with SchemaValidator.
          2. Convert valid records to mass_appraisal unit format.
          3. Run mass_appraisal (hedonic / comparable / both).
          4. Build PropertyPrediction records.
          5. Return MassValuationRun structure.

        Returns a dict conforming to data_models.schema.json::MassValuationRun.
        """
        run_id  = str(uuid.uuid4())
        started = datetime.now(timezone.utc).isoformat()

        # ── 1. Validate ───────────────────────────────────────────────────
        batch: BatchValidationResult = self._validator.validate_batch(records)
        valid_records = [
            records[i]
            for i, r in enumerate(batch.records)
            if r.is_valid
        ]

        # ── 2. Convert ────────────────────────────────────────────────────
        units = [_to_appraisal_unit(r) for r in valid_records]

        # ── 3. Appraise ───────────────────────────────────────────────────
        region = "SA" if self.jurisdiction.upper().startswith("SA") else "EG"
        if units:
            appraisal = run_mass_appraisal(
                units,
                base_market_ppm=base_market_ppm,
                location=location,
                region=region,
                method=self.method,
                iaao_thresholds=self.iaao_thresholds,
                output_dir="",
            )
        else:
            appraisal = {
                "n_units": 0,
                "total_portfolio_value": 0,
                "avg_ppm": 0,
                "ratio_study": {"n_sales": 0},
                "units": [],
            }

        # ── 4. Build predictions ──────────────────────────────────────────
        predictions = _build_predictions(appraisal.get("units", []), run_id)

        # ── 5. Assemble run record ────────────────────────────────────────
        dataset_hash = _sha256_of(records)
        iaao_summary = appraisal.get("ratio_study", {})

        return {
            "run_id":                       run_id,
            "run_name":                     self.run_name,
            "property_type":                self.property_type,
            "jurisdiction":                 self.jurisdiction,
            "status":                       "validated",
            "method":                       self.method,
            "n_input_records":              len(records),
            "n_rejected":                   batch.rejected,
            "n_flagged":                    batch.flagged,
            "n_training_records":           len(units),
            "n_predicted_properties":       len(predictions),
            "ood_property_count":           0,
            "manual_review_required_count": batch.flagged,
            "dataset_hash":                 dataset_hash,
            "random_seed":                  self.random_seed,
            "iaao_summary":                 iaao_summary,
            "started_at":                   started,
            "completed_at":                 datetime.now(timezone.utc).isoformat(),
            "advisory_only":                True,
            "certification_ready":          False,
            "predictions":                  predictions,
            "validation_report":            batch.to_dict(),
        }
