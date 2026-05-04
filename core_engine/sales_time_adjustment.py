"""
core_engine/sales_time_adjustment.py
======================================
Mass Appraisal Phase 3.4 — Time Adjustment / Price Index Integration

Adjusts verified sale prices from their sale_date to a common valuation_date
so that sales from different periods can be compared on equal footing before
ratio studies and future calibration.

Does NOT modify assessed values, valuation formulas, or AVM logic.
Does NOT calibrate models.  Read-only reuse of price_index_engine helpers.

Adjustment methods:
    monthly_growth_rate (default)
        factor = (1 + rate) ** months_diff
        months_diff = whole-month difference (sale_month → valuation_month)

    provided_index_series (when use_price_index=True and index_series is given)
        factor = index_series[valuation_month] / index_series[sale_month]
        Falls back to monthly_growth_rate if either month is missing.

Public API:
    adjust_sales_for_time(sale_records, valuation_date, options=None) -> dict
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

# ── Try to reuse date helpers from price_index_engine (read-only) ─────────────
# If the import fails, identical local fallbacks are used automatically.

_pie_parse_dt = None
try:
    try:
        from core_engine.price_index_engine import _parse_dt as _ext_parse
    except Exception:
        from price_index_engine import _parse_dt as _ext_parse  # type: ignore
    _pie_parse_dt = _ext_parse
except Exception:
    pass  # use local fallback below


def _parse_date(ts: Any) -> Optional[datetime]:
    """Parse a date string into a datetime.  Returns None on failure."""
    if _pie_parse_dt is not None:
        return _pie_parse_dt(ts)
    # Local fallback (mirrors price_index_engine._parse_dt)
    if isinstance(ts, datetime):
        return ts
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", ""))
    except Exception:
        try:
            return datetime.strptime(str(ts)[:10], "%Y-%m-%d")
        except Exception:
            return None


def _months_diff(from_dt: datetime, to_dt: datetime) -> int:
    """Whole-month difference: positive when to_dt > from_dt."""
    return (to_dt.year - from_dt.year) * 12 + (to_dt.month - from_dt.month)


def _month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


# ── Constants ─────────────────────────────────────────────────────────────────

_DEFAULT_MONTHLY_GROWTH_RATE: float = 0.01
_METHOD_MONTHLY              = "monthly_growth_rate"
_METHOD_INDEX                = "provided_index_series"


# ── Per-record adjustment ─────────────────────────────────────────────────────

def _adjust_one(
    rec: dict,
    val_dt: datetime,
    rate: float,
    use_index: bool,
    index_series: Dict[str, float],
) -> Dict[str, Any]:
    """
    Return a copy of the sale record with time-adjustment fields appended.
    Never mutates the input dict.
    """
    out = dict(rec)
    adj_warnings: List[str] = []

    raw_sp = rec.get("sale_price")
    try:
        sale_price = float(raw_sp) if raw_sp is not None else 0.0
    except (TypeError, ValueError):
        sale_price = 0.0

    sale_date_str = str(rec.get("sale_date") or "").strip()
    sale_dt       = _parse_date(sale_date_str)

    # ── Date validation ────────────────────────────────────────────────────────
    if sale_dt is None:
        out.update({
            "valuation_date":          val_dt.strftime("%Y-%m-%d"),
            "original_sale_price":     sale_price,
            "adjusted_sale_price":     sale_price,
            "time_adjustment_factor":  1.0,
            "months_to_valuation_date": None,
            "time_adjustment_method":  None,
            "time_adjustment_applied": False,
            "time_adjustment_warnings": ["INVALID_SALE_DATE: sale_date is missing or unparseable."],
        })
        return out

    months = _months_diff(sale_dt, val_dt)

    if months < 0:
        adj_warnings.append(
            "FUTURE_SALE_DATE: sale_date is after valuation_date; "
            "adjustment factor will be < 1."
        )

    # ── Compute adjustment factor ─────────────────────────────────────────────
    method = _METHOD_MONTHLY
    factor: float
    fallback_note: Optional[str] = None

    if use_index and index_series:
        sale_mk = _month_key(sale_dt)
        val_mk  = _month_key(val_dt)
        sale_idx = index_series.get(sale_mk)
        val_idx  = index_series.get(val_mk)

        if sale_idx and val_idx and float(sale_idx) > 0:
            factor = round(float(val_idx) / float(sale_idx), 8)
            method = _METHOD_INDEX
        else:
            # Fallback: one or both months missing from the provided index
            factor = round((1.0 + rate) ** months, 8)
            fallback_note = (
                f"INDEX_MONTH_MISSING: month '{sale_mk}' or '{val_mk}' "
                "not found in index_series; falling back to monthly_growth_rate."
            )
            adj_warnings.append(fallback_note)
    else:
        factor = round((1.0 + rate) ** months, 8)

    adjusted = round(sale_price * factor, 2)
    applied  = abs(factor - 1.0) > 1e-9  # True unless factor is exactly 1.0

    out.update({
        "valuation_date":           val_dt.strftime("%Y-%m-%d"),
        "original_sale_price":      sale_price,
        "adjusted_sale_price":      adjusted,
        "time_adjustment_factor":   factor,
        "months_to_valuation_date": months,
        "time_adjustment_method":   method,
        "time_adjustment_applied":  applied,
        "time_adjustment_warnings": adj_warnings,
    })
    return out


# ── Public API ────────────────────────────────────────────────────────────────

def adjust_sales_for_time(
    sale_records: list,
    valuation_date: str,
    options: Optional[dict] = None,
) -> dict:
    """
    Time-adjust a list of verified sale records to a common valuation_date.

    Parameters
    ----------
    sale_records : list
        Verified sale records (from /api/mass-appraisal/sales/verify or raw).
    valuation_date : str
        ISO-format date string, e.g. "2026-05-02".
    options : dict | None
        monthly_growth_rate  (float, default 0.01)
        use_price_index      (bool,  default False)
        index_series         (dict   {YYYY-MM: index_value}, optional)
        date_field           (str,   default "sale_date")

    Returns
    -------
    dict with keys: status, phase, valuation_date, summary, records
    """
    options = options or {}

    # ── Input validation ──────────────────────────────────────────────────────
    if not isinstance(sale_records, list) or len(sale_records) == 0:
        return {
            "status":     "error",
            "error_code": "MISSING_SALE_RECORDS",
            "message":    "sale_records must be a non-empty list.",
        }

    val_dt = _parse_date(str(valuation_date).strip() if valuation_date else "")
    if val_dt is None:
        return {
            "status":     "error",
            "error_code": "INVALID_VALUATION_DATE",
            "message":    "valuation_date must be a valid ISO date string (e.g. '2026-05-02').",
        }

    # ── Options ───────────────────────────────────────────────────────────────
    rate: float = float(options.get("monthly_growth_rate", _DEFAULT_MONTHLY_GROWTH_RATE))
    use_index: bool = bool(options.get("use_price_index", False))
    raw_series = options.get("index_series")
    index_series: Dict[str, float] = (
        {str(k): float(v) for k, v in raw_series.items() if v is not None}
        if isinstance(raw_series, dict) else {}
    )

    # ── Process records ───────────────────────────────────────────────────────
    adjusted_records: List[Dict[str, Any]] = []
    n_adjusted = 0
    n_unadjusted = 0
    factors: List[float] = []
    warnings_count = 0

    for rec in sale_records:
        if not isinstance(rec, dict):
            # Pass through non-dict items with a minimal error annotation
            adjusted_records.append({
                "original_sale_price":     None,
                "adjusted_sale_price":     None,
                "time_adjustment_applied": False,
                "time_adjustment_warnings": ["RECORD_NOT_DICT: record is not a dictionary."],
            })
            n_unadjusted += 1
            warnings_count += 1
            continue

        out = _adjust_one(rec, val_dt, rate, use_index, index_series)
        adjusted_records.append(out)

        if out.get("time_adjustment_applied"):
            n_adjusted += 1
            f = out.get("time_adjustment_factor")
            if isinstance(f, float):
                factors.append(f)
        else:
            n_unadjusted += 1

        if out.get("time_adjustment_warnings"):
            warnings_count += len(out["time_adjustment_warnings"])

    # ── Summary statistics ────────────────────────────────────────────────────
    avg_factor = round(sum(factors) / len(factors), 6) if factors else None
    min_factor = round(min(factors), 6) if factors else None
    max_factor = round(max(factors), 6) if factors else None

    method_note = "monthly_growth_rate"
    if use_index and index_series:
        method_note = "provided_index_series (with monthly_growth_rate fallback)"
    elif use_index and not index_series:
        method_note = "monthly_growth_rate (price index requested but no index_series provided)"

    return {
        "status":          "success",
        "phase":           "sales_time_adjustment",
        "valuation_date":  val_dt.strftime("%Y-%m-%d"),
        "summary": {
            "total_records":           len(sale_records),
            "adjusted_records":        n_adjusted,
            "unadjusted_records":      n_unadjusted,
            "average_adjustment_factor": avg_factor,
            "min_adjustment_factor":   min_factor,
            "max_adjustment_factor":   max_factor,
            "monthly_growth_rate_used": rate,
            "adjustment_method":       method_note,
            "warnings_count":          warnings_count,
        },
        "records": adjusted_records,
    }


__all__ = ["adjust_sales_for_time"]
