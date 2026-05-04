"""
core_engine/calibration_sandbox.py
=====================================
Mass Appraisal Phase 3.7 — Calibration Application Sandbox

Applies Phase 3.6 calibration preview factors to a *copy* of Mass Appraisal
run rows for what-if analysis.

SANDBOX ONLY:
  - Original market_value fields are NEVER modified.
  - No calibration factors are persisted.
  - No future runs are affected.
  - No valuation formulas are changed.
  - /api/valuation and /api/mass-appraisal/run are untouched.

Public API:
    apply_calibration_sandbox(
        subject_rows, calibration_preview,
        options=None
    ) -> dict
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# ── Constants ─────────────────────────────────────────────────────────────────

_DEFAULT_PRIORITY: List[str] = [
    "zone_property_class",
    "zone",
    "property_class",
    "portfolio",
]
_DEFAULT_MIN_FACTOR: float = 0.75
_DEFAULT_MAX_FACTOR: float = 1.35
_DEFAULT_ROUND_TO:   int   = 1000
_DEFAULT_APPLY_TO:   list  = ["success"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _cs(val: Any) -> str:
    return str(val).strip() if val is not None else ""


def _safe_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        f = float(val)
        return f
    except (TypeError, ValueError):
        return None


def _round_to_nearest(value: float, nearest: int) -> float:
    """Round value to the nearest multiple of nearest (> 0)."""
    if nearest <= 0:
        return value
    return round(value / nearest) * nearest


def _get_suggested_factor(metrics: Optional[dict]) -> Optional[float]:
    """Extract a positive suggested_factor from a calibration metrics block."""
    if not isinstance(metrics, dict):
        return None
    sf = _safe_float(metrics.get("suggested_factor"))
    return sf if sf is not None and sf > 0 else None


# ── Factor resolution ─────────────────────────────────────────────────────────

def _resolve_factor(
    row: dict,
    calib: dict,
    priority: List[str],
    min_factor: float,
    max_factor: float,
) -> Tuple[float, str, List[str]]:
    """
    Walk the priority list and return (factor, source_label, warnings).
    Factor is clamped to [min_factor, max_factor].
    """
    zone_id       = _cs(row.get("zone_id"))
    prop_class    = _cs(row.get("property_class")).lower()
    combo_key     = f"{zone_id}|{prop_class}" if zone_id and prop_class else ""

    zone_pc_map   = calib.get("zone_property_class_calibration") or {}
    zone_map      = calib.get("zone_calibration") or {}
    pclass_map    = calib.get("property_class_calibration") or {}
    portfolio     = calib.get("portfolio_calibration") or {}

    # Normalise property_class keys in maps to lowercase for comparison
    def _lower_keys(d: dict) -> Dict[str, Any]:
        return {k.lower(): v for k, v in d.items()} if isinstance(d, dict) else {}

    zone_pc_norm  = {k.lower(): v for k, v in zone_pc_map.items()} if isinstance(zone_pc_map, dict) else {}
    pclass_norm   = _lower_keys(pclass_map)
    # zone_map keys are zone_ids — keep as-is

    for source in priority:
        if source == "zone_property_class":
            sf = _get_suggested_factor(zone_pc_norm.get(combo_key.lower()))
            if sf is not None:
                return _clamp(sf, min_factor, max_factor)

        elif source == "zone":
            sf = _get_suggested_factor(zone_map.get(zone_id) if zone_id else None)
            if sf is not None:
                return _clamp(sf, min_factor, max_factor)

        elif source == "property_class":
            sf = _get_suggested_factor(pclass_norm.get(prop_class))
            if sf is not None:
                return _clamp(sf, min_factor, max_factor)

        elif source == "portfolio":
            sf = _get_suggested_factor(portfolio)
            if sf is not None:
                return _clamp(sf, min_factor, max_factor)

    return 1.0, "none", []


def _clamp(
    factor: float,
    min_f: float,
    max_f: float,
) -> Tuple[float, str, List[str]]:
    """Return (clamped_factor, source_placeholder, warnings)."""
    # Source label is filled by the caller; we only handle clamping here.
    warns: List[str] = []
    if factor < min_f:
        warns.append(
            f"FACTOR_CLAMPED_LOW: factor {factor:.6f} < min {min_f}; clamped."
        )
        factor = min_f
    elif factor > max_f:
        warns.append(
            f"FACTOR_CLAMPED_HIGH: factor {factor:.6f} > max {max_f}; clamped."
        )
        factor = max_f
    return factor, "", warns


def _resolve_factor_with_source(
    row: dict,
    calib: dict,
    priority: List[str],
    min_factor: float,
    max_factor: float,
) -> Tuple[float, str, List[str]]:
    """
    Full resolution returning (factor, source_label, warnings).
    Implemented directly to keep source-labelling paired with clamping.
    """
    zone_id    = _cs(row.get("zone_id"))
    prop_class = _cs(row.get("property_class")).lower()
    combo_key  = f"{zone_id}|{prop_class}" if zone_id and prop_class else ""

    zone_pc_map = calib.get("zone_property_class_calibration") or {}
    zone_map    = calib.get("zone_calibration") or {}
    pclass_map  = calib.get("property_class_calibration") or {}
    portfolio   = calib.get("portfolio_calibration") or {}

    zone_pc_norm = {k.lower(): v for k, v in zone_pc_map.items()} if isinstance(zone_pc_map, dict) else {}
    pclass_norm  = {k.lower(): v for k, v in pclass_map.items()} if isinstance(pclass_map, dict) else {}

    def _apply_clamp(raw_f: float, src: str) -> Tuple[float, str, List[str]]:
        warns: List[str] = []
        if raw_f < min_factor:
            warns.append(
                f"FACTOR_CLAMPED_LOW: suggested_factor {raw_f:.6f} < min {min_factor}; "
                f"clamped to {min_factor}."
            )
            raw_f = min_factor
        elif raw_f > max_factor:
            warns.append(
                f"FACTOR_CLAMPED_HIGH: suggested_factor {raw_f:.6f} > max {max_factor}; "
                f"clamped to {max_factor}."
            )
            raw_f = max_factor
        return raw_f, src, warns

    for source in priority:
        if source == "zone_property_class" and combo_key:
            sf = _get_suggested_factor(zone_pc_norm.get(combo_key.lower()))
            if sf is not None:
                return _apply_clamp(sf, "zone_property_class")

        elif source == "zone" and zone_id:
            sf = _get_suggested_factor(zone_map.get(zone_id))
            if sf is not None:
                return _apply_clamp(sf, "zone")

        elif source == "property_class" and prop_class:
            sf = _get_suggested_factor(pclass_norm.get(prop_class))
            if sf is not None:
                return _apply_clamp(sf, "property_class")

        elif source == "portfolio":
            sf = _get_suggested_factor(portfolio)
            if sf is not None:
                return _apply_clamp(sf, "portfolio")

    return 1.0, "none", []


# ── Per-row sandbox application ───────────────────────────────────────────────

def _apply_one(
    row: dict,
    calib: dict,
    priority: List[str],
    min_factor: float,
    max_factor: float,
    apply_to_status: set,
    round_to: int,
) -> Tuple[Dict[str, Any], bool, Optional[float]]:
    """
    Return (output_row_dict, was_calibrated, factor_applied).
    Output dict is a copy — original dict is never mutated.
    """
    out = dict(row)
    sandbox_warns: List[str] = []

    status = _cs(row.get("status"))
    mv = _safe_float(row.get("market_value"))

    # Original value always preserved
    out["original_market_value"] = mv

    # Skip rows not in apply_to_status
    if status not in apply_to_status:
        out.update({
            "sandbox_calibrated_value":    None,
            "calibration_factor_applied":  None,
            "calibration_factor_source":   "none",
            "sandbox_value_delta":         None,
            "sandbox_value_delta_pct":     None,
            "sandbox_value_per_m2":        None,
            "calibration_sandbox_warnings": [],
        })
        return out, False, None

    # Validate market_value
    if mv is None or mv <= 0:
        sandbox_warns.append(
            "INVALID_MARKET_VALUE: market_value is missing or <= 0; sandbox skipped."
        )
        out.update({
            "sandbox_calibrated_value":    None,
            "calibration_factor_applied":  None,
            "calibration_factor_source":   "none",
            "sandbox_value_delta":         None,
            "sandbox_value_delta_pct":     None,
            "sandbox_value_per_m2":        None,
            "calibration_sandbox_warnings": sandbox_warns,
        })
        return out, False, None

    # Resolve factor
    factor, source, clamp_warns = _resolve_factor_with_source(
        row, calib, priority, min_factor, max_factor
    )
    sandbox_warns.extend(clamp_warns)

    # Compute sandbox value
    raw_sandbox = mv * factor
    if round_to > 0:
        sandbox_val = _round_to_nearest(raw_sandbox, round_to)
    else:
        sandbox_val = round(raw_sandbox, 2)

    delta     = round(sandbox_val - mv, 2)
    delta_pct = round((sandbox_val - mv) / mv * 100, 4) if mv > 0 else None

    area = _safe_float(row.get("area"))
    sb_pm2: Optional[float] = (
        round(sandbox_val / area, 2) if area and area > 0 else None
    )

    out.update({
        "sandbox_calibrated_value":    sandbox_val,
        "calibration_factor_applied":  round(factor, 8),
        "calibration_factor_source":   source,
        "sandbox_value_delta":         delta,
        "sandbox_value_delta_pct":     delta_pct,
        "sandbox_value_per_m2":        sb_pm2,
        "calibration_sandbox_warnings": sandbox_warns,
    })
    return out, True, factor


# ── Public API ────────────────────────────────────────────────────────────────

def apply_calibration_sandbox(
    subject_rows: list,
    calibration_preview: dict,
    options: Optional[dict] = None,
) -> dict:
    """
    Apply Phase 3.6 calibration factors to a sandbox copy of Mass Appraisal
    run rows.  Original market_value is NEVER modified.

    Parameters
    ----------
    subject_rows : list
        Mass Appraisal batch run result rows.
    calibration_preview : dict
        Phase 3.6 preview_calibration() output.
    options : dict | None
        factor_priority  (list,  default zone_property_class > zone > property_class > portfolio)
        min_factor       (float, default 0.75)
        max_factor       (float, default 1.35)
        apply_to_status  (list,  default ["success"])
        round_to         (int,   default 1000)
    """
    # ── Input validation ──────────────────────────────────────────────────────
    if subject_rows is None or not isinstance(subject_rows, list):
        return {
            "status":     "error",
            "error_code": ("MISSING_SUBJECT_ROWS" if subject_rows is None
                           else "INVALID_SUBJECT_ROWS_TYPE"),
            "message":    "subject_rows must be a non-empty list of row dicts.",
        }

    if calibration_preview is None:
        return {
            "status":     "error",
            "error_code": "MISSING_CALIBRATION_PREVIEW",
            "message":    "calibration_preview must be provided.",
        }
    if not isinstance(calibration_preview, dict):
        return {
            "status":     "error",
            "error_code": "INVALID_CALIBRATION_PREVIEW",
            "message":    "calibration_preview must be a dict (Phase 3.6 output).",
        }
    # Accept both a raw calibration_preview dict and a full API response
    # (i.e. if caller passes the full JSON response, unwrap portfolio_calibration etc.)
    if "portfolio_calibration" not in calibration_preview:
        return {
            "status":     "error",
            "error_code": "INVALID_CALIBRATION_PREVIEW",
            "message":    ("calibration_preview must contain 'portfolio_calibration'. "
                           "Pass the Phase 3.6 result directly."),
        }

    # ── Options ───────────────────────────────────────────────────────────────
    opts             = options or {}
    priority: List[str] = list(opts.get("factor_priority", _DEFAULT_PRIORITY))
    min_factor: float   = float(opts.get("min_factor", _DEFAULT_MIN_FACTOR))
    max_factor: float   = float(opts.get("max_factor", _DEFAULT_MAX_FACTOR))
    round_to: int       = int(opts.get("round_to", _DEFAULT_ROUND_TO))
    apply_to_status: set = set(opts.get("apply_to_status", _DEFAULT_APPLY_TO))

    # ── Process rows ──────────────────────────────────────────────────────────
    output_rows: List[Dict[str, Any]] = []
    n_calibrated   = 0
    n_unchanged    = 0
    factors_used: List[float] = []
    source_counts: Dict[str, int] = {}
    warnings_count = 0

    orig_total  = 0.0
    sb_total    = 0.0

    for row in subject_rows:
        if not isinstance(row, dict):
            output_rows.append({
                "original_market_value":        None,
                "sandbox_calibrated_value":     None,
                "calibration_factor_applied":   None,
                "calibration_factor_source":    "none",
                "sandbox_value_delta":          None,
                "sandbox_value_delta_pct":      None,
                "sandbox_value_per_m2":         None,
                "calibration_sandbox_warnings": ["RECORD_NOT_DICT: row is not a dict."],
            })
            n_unchanged += 1
            warnings_count += 1
            continue

        out_row, calibrated, factor = _apply_one(
            row, calibration_preview, priority,
            min_factor, max_factor, apply_to_status, round_to
        )
        output_rows.append(out_row)

        mv_raw = _safe_float(row.get("market_value"))
        if mv_raw and mv_raw > 0:
            orig_total += mv_raw

        sb_val = out_row.get("sandbox_calibrated_value")
        if isinstance(sb_val, (int, float)):
            sb_total += sb_val
        elif mv_raw and mv_raw > 0:
            sb_total += mv_raw  # unchanged rows contribute original value

        if calibrated:
            n_calibrated += 1
            if factor is not None:
                factors_used.append(factor)
            src = out_row.get("calibration_factor_source", "none")
            source_counts[src] = source_counts.get(src, 0) + 1
        else:
            n_unchanged += 1

        warnings_count += len(out_row.get("calibration_sandbox_warnings") or [])

    # ── Summary ───────────────────────────────────────────────────────────────
    avg_factor = (round(sum(factors_used) / len(factors_used), 6)
                  if factors_used else None)
    total_delta = round(sb_total - orig_total, 2)
    total_delta_pct = (round(total_delta / orig_total * 100, 4)
                       if orig_total > 0 else None)

    return {
        "status": "success",
        "phase":  "calibration_sandbox",
        "summary": {
            "total_rows":                 len(subject_rows),
            "calibrated_rows":            n_calibrated,
            "unchanged_rows":             n_unchanged,
            "original_total_market_value": round(orig_total, 2),
            "sandbox_total_market_value":  round(sb_total, 2),
            "total_value_delta":           total_delta,
            "total_value_delta_pct":       total_delta_pct,
            "average_calibration_factor":  avg_factor,
            "factor_source_counts":        source_counts,
            "warnings_count":              warnings_count,
        },
        "rows": output_rows,
    }


__all__ = ["apply_calibration_sandbox"]
