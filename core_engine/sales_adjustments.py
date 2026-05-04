"""
core_engine/sales_adjustments.py
==================================
Mass Appraisal Phase 3.5 — Sales Adjustment Factors

Applies non-time, non-arms-length adjustments to verified or time-adjusted
sale records, producing a final_adjusted_sale_price for use in ratio studies
and future calibration.

Does NOT modify assessed values, valuation formulas, AVM logic, or subject
property values.  Does NOT calibrate models.

Supported adjustment factors (all multiplicative):
    location_factor, size_factor, condition_factor, quality_factor,
    financing_factor, property_rights_factor

Public API:
    apply_sales_adjustments(sale_records, adjustment_profile=None, options=None)
    -> dict
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# ── Constants ─────────────────────────────────────────────────────────────────

MAX_SALES_RECORDS: int = 1000

_FACTOR_NAMES: List[str] = [
    "location_factor",
    "size_factor",
    "condition_factor",
    "quality_factor",
    "financing_factor",
    "property_rights_factor",
]

# Record-level override field names (parallel order to _FACTOR_NAMES)
_RECORD_FACTOR_FIELDS: List[str] = [
    "location_adjustment_factor",
    "size_adjustment_factor",
    "condition_adjustment_factor",
    "quality_adjustment_factor",
    "financing_adjustment_factor",
    "property_rights_adjustment_factor",
]

_DEFAULT_PROFILE: Dict[str, float] = {name: 1.0 for name in _FACTOR_NAMES}

# Warning thresholds
_FACTOR_LOW  = 0.70
_FACTOR_HIGH = 1.30
_TOTAL_LOW   = 0.60
_TOTAL_HIGH  = 1.60


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_positive_float(val: Any) -> Optional[float]:
    """Return val as a positive float, or None."""
    try:
        f = float(val)
        return f if f > 0 else None
    except (TypeError, ValueError):
        return None


def _resolve_factor(
    rec: dict,
    record_field: str,
    profile_factor: float,
) -> tuple[float, Optional[str]]:
    """
    Return (factor_value, warning_or_None).
    Precedence: record-level field > profile default.
    Validates the factor and falls back to 1.0 on invalid values.
    """
    raw = rec.get(record_field)
    warnings: list[str] = []

    if raw is not None:
        try:
            f = float(raw)
        except (TypeError, ValueError):
            return 1.0, f"INVALID_ADJUSTMENT_FACTOR: {record_field}={raw!r} is not numeric; defaulting to 1.0."
        if f <= 0:
            return 1.0, f"INVALID_ADJUSTMENT_FACTOR: {record_field}={f} is <= 0; defaulting to 1.0."
        factor = f
    else:
        factor = profile_factor

    if factor < _FACTOR_LOW or factor > _FACTOR_HIGH:
        return factor, f"HIGH_ADJUSTMENT_FACTOR: {record_field}={factor} is outside [0.70, 1.30]."

    return factor, None


# ── Per-record adjustment ─────────────────────────────────────────────────────

def _adjust_one(rec: dict, profile: Dict[str, float]) -> Dict[str, Any]:
    """
    Return a copy of the sale record with all Phase 3.5 adjustment fields appended.
    Never mutates the input dict.
    """
    out = dict(rec)
    adj_warnings: List[str] = []

    # ── Determine base sale price ──────────────────────────────────────────────
    adj_sp  = _safe_positive_float(rec.get("adjusted_sale_price"))
    sale_sp = _safe_positive_float(rec.get("sale_price"))

    if adj_sp is not None:
        base = adj_sp
    elif sale_sp is not None:
        base = sale_sp
    else:
        # No valid price — cannot adjust
        out.update({
            "base_sale_price_for_adjustment":   None,
            "location_adjustment_factor":       None,
            "size_adjustment_factor":           None,
            "condition_adjustment_factor":      None,
            "quality_adjustment_factor":        None,
            "financing_adjustment_factor":      None,
            "property_rights_adjustment_factor": None,
            "final_adjustment_factor":          None,
            "final_adjusted_sale_price":        None,
            "adjustment_method":                None,
            "adjustment_applied":               False,
            "adjustment_warnings":              ["INVALID_SALE_PRICE: no positive sale_price or adjusted_sale_price."],
        })
        return out

    # ── Resolve each factor ────────────────────────────────────────────────────
    resolved_factors: Dict[str, float] = {}
    for fname, rfield in zip(_FACTOR_NAMES, _RECORD_FACTOR_FIELDS):
        pf = profile.get(fname, 1.0)
        factor, warn = _resolve_factor(rec, rfield, pf)
        resolved_factors[rfield] = factor
        if warn:
            adj_warnings.append(warn)

    # ── Compute composite factor ───────────────────────────────────────────────
    final_factor = 1.0
    for f in resolved_factors.values():
        final_factor *= f
    final_factor = round(final_factor, 8)

    if final_factor < _TOTAL_LOW or final_factor > _TOTAL_HIGH:
        adj_warnings.append(
            f"TOTAL_ADJUSTMENT_OUT_OF_RANGE: final_adjustment_factor={final_factor} "
            f"is outside [{_TOTAL_LOW}, {_TOTAL_HIGH}]."
        )

    final_price = round(base * final_factor, 2)
    applied = abs(final_factor - 1.0) > 1e-9

    method_parts = [
        f"{rfield}={resolved_factors[rfield]}"
        for fname, rfield in zip(_FACTOR_NAMES, _RECORD_FACTOR_FIELDS)
        if abs(resolved_factors[rfield] - 1.0) > 1e-9
    ]
    method_str = ("compound_factor: " + " × ".join(method_parts)) if method_parts else "no_adjustment"

    out.update({
        "base_sale_price_for_adjustment":    round(base, 2),
        "location_adjustment_factor":        resolved_factors["location_adjustment_factor"],
        "size_adjustment_factor":            resolved_factors["size_adjustment_factor"],
        "condition_adjustment_factor":       resolved_factors["condition_adjustment_factor"],
        "quality_adjustment_factor":         resolved_factors["quality_adjustment_factor"],
        "financing_adjustment_factor":       resolved_factors["financing_adjustment_factor"],
        "property_rights_adjustment_factor": resolved_factors["property_rights_adjustment_factor"],
        "final_adjustment_factor":           final_factor,
        "final_adjusted_sale_price":         final_price,
        "adjustment_method":                 method_str,
        "adjustment_applied":                applied,
        "adjustment_warnings":               adj_warnings,
    })
    return out


# ── Public API ────────────────────────────────────────────────────────────────

def apply_sales_adjustments(
    sale_records: list,
    adjustment_profile: Optional[dict] = None,
    options: Optional[dict] = None,  # reserved for future use
) -> dict:
    """
    Apply multiplicative non-time sales adjustment factors to a list of
    verified or time-adjusted sale records.

    Parameters
    ----------
    sale_records : list
        Verified/time-adjusted sale records.
    adjustment_profile : dict | None
        Portfolio-level default factors.  Missing keys default to 1.0.
        Per-record override fields in each sale dict take precedence.
    options : dict | None
        Reserved.  Currently unused.

    Returns
    -------
    dict with keys: status, phase, summary, records
    """
    # ── Input validation ──────────────────────────────────────────────────────
    if sale_records is None or not isinstance(sale_records, list):
        return {
            "status":     "error",
            "error_code": "MISSING_SALE_RECORDS" if sale_records is None else "INVALID_SALE_RECORDS_TYPE",
            "message":    "sale_records must be a non-empty list of sale record dicts.",
        }

    if len(sale_records) == 0:
        return {
            "status":     "error",
            "error_code": "MISSING_SALE_RECORDS",
            "message":    "sale_records must be a non-empty list.",
        }

    if len(sale_records) > MAX_SALES_RECORDS:
        return {
            "status":     "error",
            "error_code": "TOO_MANY_RECORDS",
            "message":    (f"sale_records contains {len(sale_records)} records; "
                           f"maximum allowed is {MAX_SALES_RECORDS}."),
        }

    # ── Build effective profile ───────────────────────────────────────────────
    profile: Dict[str, float] = dict(_DEFAULT_PROFILE)
    if isinstance(adjustment_profile, dict):
        for name in _FACTOR_NAMES:
            raw = adjustment_profile.get(name)
            if raw is not None:
                try:
                    v = float(raw)
                    profile[name] = v if v > 0 else 1.0
                except (TypeError, ValueError):
                    pass  # keep default

    # ── Process records ───────────────────────────────────────────────────────
    adjusted_records: List[Dict[str, Any]] = []
    n_adjusted   = 0
    n_unadjusted = 0
    factors: List[float] = []
    warnings_count = 0

    for rec in sale_records:
        if not isinstance(rec, dict):
            adjusted_records.append({
                "adjustment_applied":   False,
                "final_adjusted_sale_price": None,
                "adjustment_warnings":  ["RECORD_NOT_DICT: record is not a dictionary."],
            })
            n_unadjusted += 1
            warnings_count += 1
            continue

        out = _adjust_one(rec, profile)
        adjusted_records.append(out)

        if out.get("adjustment_applied"):
            n_adjusted += 1
            f = out.get("final_adjustment_factor")
            if isinstance(f, (int, float)):
                factors.append(float(f))
        else:
            n_unadjusted += 1

        warnings_count += len(out.get("adjustment_warnings") or [])

    # ── Summary statistics ────────────────────────────────────────────────────
    avg_factor = round(sum(factors) / len(factors), 6) if factors else None
    min_factor = round(min(factors), 6)                if factors else None
    max_factor = round(max(factors), 6)                if factors else None

    return {
        "status": "success",
        "phase":  "sales_adjustments",
        "summary": {
            "total_records":                  len(sale_records),
            "adjusted_records":               n_adjusted,
            "unadjusted_records":             n_unadjusted,
            "average_final_adjustment_factor": avg_factor,
            "min_final_adjustment_factor":    min_factor,
            "max_final_adjustment_factor":    max_factor,
            "warnings_count":                 warnings_count,
        },
        "records": adjusted_records,
    }


__all__ = ["apply_sales_adjustments"]
