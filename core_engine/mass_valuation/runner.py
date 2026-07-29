"""
runner.py — P1 Mass Valuation MVP Runner.
Orchestrates: validate → appraise → build predictions → record audit.
No valuation logic — delegates to mass_appraisal.run_mass_appraisal().
advisory_only=True on every output. certification_ready=False always.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from core_engine.mass_valuation.contract.schema_validator import (
    BatchValidationResult,
    SchemaValidator,
    ValidationResult,
)
from core_engine.mass_appraisal import run_mass_appraisal

try:
    from core_engine.mass_valuation.ood_detector import detect_ood as _detect_ood
    _OOD_AVAILABLE = True
except ImportError:
    _OOD_AVAILABLE = False
    def _detect_ood(units, random_seed=42):  # type: ignore[misc]
        return []

try:
    from core_engine.mass_valuation.data_splitter import (
        temporal_split  as _temporal_split,
        geographic_split as _geographic_split,
    )
except ImportError:
    def _temporal_split(records, cutoff_date):   # type: ignore[misc]
        return records, []
    def _geographic_split(records, holdout_cities):  # type: ignore[misc]
        return records, []


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


def _compute_model_hash(
    training_data_hash: str,
    random_seed: int,
    method: str,
) -> str:
    """R-02: Deterministic model identifier — same inputs → same hash across runs."""
    return _sha256_of({
        "training_data_hash": training_data_hash,
        "random_seed":        random_seed,
        "method":             method,
    })


def _get_code_commit() -> str:
    """M-08: Current git commit SHA — enables exact codebase reproduction."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def _check_leakage(
    train_records: List[Dict[str, Any]],
    val_records: List[Dict[str, Any]],
    holdout_records: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """D-08: Verify no property_id overlaps between training and test buckets."""
    train_ids   = {str(r.get("property_id", "")) for r in train_records}
    val_ids     = {str(r.get("property_id", "")) for r in val_records}
    holdout_ids = {str(r.get("property_id", "")) for r in holdout_records}
    leaked_ids  = (train_ids & val_ids) | (train_ids & holdout_ids)
    return {
        "leakage_check":        True,
        "leakage_check_method": "property_id_intersection",
        "leakage_found":        bool(leaked_ids),
        "leakage_count":        len(leaked_ids),
        "leakage_ids":          sorted(leaked_ids)[:10],
    }


# ---------------------------------------------------------------------------
# P5 — Interpretability helpers (I-01, I-02, I-03)
# ---------------------------------------------------------------------------

def _median_of(values: List[float]) -> float:
    """Compute median of a non-empty list (pure Python, no deps)."""
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return (s[mid - 1] + s[mid]) / 2.0 if n % 2 == 0 else s[mid]


def _compute_batch_stats(units: List[Dict[str, Any]]) -> Dict[str, float]:
    """Batch-level median statistics used by the SHAP proxy."""
    if not units:
        return {}
    return {
        "median_area":  _median_of([float(u.get("area", 100))       for u in units]),
        "median_ppm":   _median_of([float(u.get("final_ppm", 0))    for u in units]),
        "median_year":  _median_of([float(u.get("year_built", 2010)) for u in units]),
        "n_units":      float(len(units)),
    }


def _derive_confidence(
    ood_status: str,
    ood_score: float,
    unit_value: float,
) -> str:
    """I-03: Derive confidence from OOD status and score (not hardcoded)."""
    if unit_value <= 0:
        return "insufficient"
    if ood_status == "out_of_distribution":
        return "low"
    # ood_score ≥ -0.2  ↔  max robust Z < 1.0 (clearly within distribution)
    if ood_score >= -0.2:
        return "high"
    return "medium"


def _build_limitations(
    ood_status: str,
    ood_score: float,
    unit_value: float,
    unit: Dict[str, Any],
) -> List[str]:
    """I-02: Human-readable limitation strings free of technical jargon (I-04)."""
    if unit_value <= 0:
        return ["insufficient_evidence: no positive value produced by model"]

    lims: List[str] = []

    if ood_status == "out_of_distribution":
        lims.append(
            "Property characteristics fall outside the range of comparable properties "
            "used in this analysis; estimate reliability may be reduced."
        )
    elif ood_score < -0.3:
        lims.append(
            "Some property characteristics are less common than typical properties "
            "in this area."
        )

    if float(unit.get("final_ppm", 0)) == 0:
        lims.append(
            "No comparable market transactions were available for this property "
            "type and location; value is based on regional defaults only."
        )

    return lims


def _compute_shap_proxy(
    unit: Dict[str, Any],
    batch_stats: Dict[str, float],
    unit_value: float,
) -> Dict[str, Any]:
    """
    I-01: Linear decomposition proxy for value attribution.
    Signed additive decomposition relative to the batch median property.
    NOT SHAP — an approximation for analyst/admin diagnostic use only.
    """
    if unit_value <= 0 or not batch_stats:
        return {}

    area       = float(unit.get("area", 100))
    final_ppm  = float(unit.get("final_ppm", 0))
    year_built = float(unit.get("year_built", 2010))

    med_area = batch_stats.get("median_area", area)
    med_ppm  = batch_stats.get("median_ppm",  final_ppm)
    med_year = batch_stats.get("median_year", year_built)

    return {
        "area_contribution":         round((area - med_area) * med_ppm, 0),
        "market_price_contribution": round(med_area * (final_ppm - med_ppm), 0),
        "age_contribution":          round((year_built - med_year) * 200.0, 0),
        "method":                    "linear_decomposition_proxy",
        "advisory_note":             "Approximate attribution only — not SHAP.",
    }


# ---------------------------------------------------------------------------
# Prediction builder
# ---------------------------------------------------------------------------

def _build_predictions(
    units: List[Dict],
    run_id: str,
    ood_results: Optional[List[Tuple[float, str]]] = None,
    batch_stats: Optional[Dict[str, Any]] = None,
) -> List[Dict]:
    """Convert mass_appraisal per-unit results to PropertyPrediction records.
    ood_results : (ood_score, distribution_status) parallel to units.
    batch_stats : median statistics for SHAP proxy (I-01).
    """
    predictions: List[Dict] = []
    for i, u in enumerate(units):
        unit_value  = float(u.get("unit_value", 0) or 0)
        area        = float(u.get("area", 1) or 1)
        unit_per_m2 = round(unit_value / area, 0) if area > 0 else None

        # OOD result for this unit (M-06)
        if ood_results and i < len(ood_results):
            ood_score, ood_status = ood_results[i]
        else:
            ood_score, ood_status = 0.0, "in_distribution"

        if unit_value <= 0:
            dist_status = "insufficient_evidence"
            confidence  = "insufficient"
            estimated   = None
            pi_low      = None
            pi_high     = None
            limitations = ["insufficient_evidence: no positive value produced by model"]
        else:
            dist_status = ood_status   # real OOD status (M-06)
            confidence  = _derive_confidence(ood_status, ood_score, unit_value)
            estimated   = round(unit_value, 0)
            pi_low      = round(unit_value * 0.85, 0)
            pi_high     = round(unit_value * 1.15, 0)
            limitations = _build_limitations(ood_status, ood_score, unit_value, u)

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
            "ood_score":                ood_score,
            "review_status":            "manual_review_required",
            "quality_flags":            [],
            "comparable_ids":           [],
            "shap_values":              _compute_shap_proxy(u, batch_stats or {}, unit_value),
            "model_version":            "hedonic-v1",
            "limitations":              limitations,
            "advisory_only":            True,
        })

    return predictions


def _compute_pi_coverage(
    appraisal_units: List[Dict],
    predictions: List[Dict],
) -> Dict[str, Any]:
    """
    M-05: Verify PI 85%/115% bounds on sold units (sale_price > 0).
    Returns a coverage report dict added to iaao_summary.
    """
    sold_pairs: List[Tuple[float, float, float]] = []
    for unit, pred in zip(appraisal_units, predictions):
        sale = float(unit.get("sale_price", 0) or 0)
        if sale <= 0:
            continue
        pi_low  = pred.get("prediction_interval_low")
        pi_high = pred.get("prediction_interval_high")
        if pi_low is None or pi_high is None:
            continue
        sold_pairs.append((sale, float(pi_low), float(pi_high)))

    n_sold = len(sold_pairs)
    if n_sold < 5:
        return {
            "n_sold_units":                        n_sold,
            "coverage_fraction":                   None,
            "meets_90pct_threshold":               None,
            "insufficient_sales_for_coverage_check": True,
        }

    covered = sum(1 for sale, lo, hi in sold_pairs if lo <= sale <= hi)
    fraction = round(covered / n_sold, 4)
    return {
        "n_sold_units":                        n_sold,
        "coverage_fraction":                   fraction,
        "meets_90pct_threshold":               fraction >= 0.90,
        "insufficient_sales_for_coverage_check": False,
        "pi_bounds": {"lower_multiplier": 0.85, "upper_multiplier": 1.15},
    }


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
        cutoff_date: Optional[str] = None,           # D-06: "YYYY-MM-DD"
        holdout_cities: Optional[List[str]] = None,  # D-07: cities excluded from training
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

        # ── 1b. Data splits (D-06, D-07) ─────────────────────────────────
        if cutoff_date:
            train_records, val_records = _temporal_split(valid_records, cutoff_date)
        else:
            train_records, val_records = valid_records, []

        if holdout_cities:
            train_records, holdout_records = _geographic_split(train_records, holdout_cities)
        else:
            holdout_records = []

        # ── 1c. Leakage check (D-08) ──────────────────────────────────────
        leakage_info = _check_leakage(train_records, val_records, holdout_records)

        # ── 2. Convert ────────────────────────────────────────────────────
        units = [_to_appraisal_unit(r) for r in train_records]

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

        # ── 4. OOD detection (M-06) ──────────────────────────────────────
        appraisal_units = appraisal.get("units", [])
        ood_results     = _detect_ood(appraisal_units, random_seed=self.random_seed)

        # ── 4b. Batch statistics for SHAP proxy (I-01) ────────────────────
        batch_stats = _compute_batch_stats(appraisal_units)

        # ── 4c. Model hash (R-02) ─────────────────────────────────────────
        training_hash = _sha256_of(train_records)
        model_hash    = _compute_model_hash(training_hash, self.random_seed, self.method)

        # ── 4d. Code commit (M-08) ────────────────────────────────────────
        code_commit = _get_code_commit()

        # ── 5. Build predictions ──────────────────────────────────────────
        predictions = _build_predictions(appraisal_units, run_id, ood_results, batch_stats)

        # ── 6. PI coverage validation (M-05) ─────────────────────────────
        pi_coverage  = _compute_pi_coverage(appraisal_units, predictions)
        iaao_summary = dict(appraisal.get("ratio_study") or {})
        iaao_summary["pi_coverage"] = pi_coverage

        ood_count = sum(
            1 for p in predictions
            if p.get("distribution_status") == "out_of_distribution"
        )

        # ── 7. Assemble run record ────────────────────────────────────────
        dataset_hash = _sha256_of(records)

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
            "n_validation_records":         len(val_records),
            "n_holdout_records":            len(holdout_records),
            "n_predicted_properties":       len(predictions),
            "ood_property_count":           ood_count,
            "manual_review_required_count": batch.flagged,
            "dataset_hash":                 dataset_hash,
            "model_hash":                   model_hash,
            "code_commit":                  code_commit,
            "split_cutoff_date":            cutoff_date,
            "holdout_cities":               holdout_cities or [],
            "random_seed":                  self.random_seed,
            "leakage_check":                leakage_info["leakage_check"],
            "leakage_check_method":         leakage_info["leakage_check_method"],
            "leakage_found":                leakage_info["leakage_found"],
            "validation_strategy": {
                "type": (
                    "temporal_and_spatial" if (cutoff_date and holdout_cities) else
                    "temporal_split"        if cutoff_date else
                    "spatial_split"         if holdout_cities else
                    "none"
                ),
                "temporal_holdout":  {"cutoff_date": cutoff_date} if cutoff_date else None,
                "geographic_holdout": {"cities_excluded": holdout_cities or []},
                "leakage_check":        leakage_info["leakage_check"],
                "leakage_check_method": leakage_info["leakage_check_method"],
                "leakage_found":        leakage_info["leakage_found"],
                "leakage_count":        leakage_info["leakage_count"],
            },
            "iaao_summary":                 iaao_summary,
            "started_at":                   started,
            "completed_at":                 datetime.now(timezone.utc).isoformat(),
            "advisory_only":                True,
            "certification_ready":          False,
            "predictions":                  predictions,
            "validation_report":            batch.to_dict(),
        }
