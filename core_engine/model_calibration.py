"""
core_engine/model_calibration.py
==================================
Mass Appraisal Phase 3.6 — Calibration Preview

Analyzes Mass Appraisal batch results against verified/time-adjusted/
final-adjusted sale records and produces calibration factor hints by
portfolio, zone, property class, and zone+property_class combination.

PREVIEW-ONLY. Does NOT modify subject values, valuation formulas, AVM
engine, or /api/valuation.  All suggested factors are for analyst review.

Public API:
    preview_calibration(
        subject_rows, sale_records,
        ratio_study=None, options=None
    ) -> dict
"""
from __future__ import annotations

import statistics
from typing import Any, Dict, List, Optional, Tuple

_CALIBRATION_NOTE = (
    "هذه النتائج معايرة مبدئية للمراجعة فقط "
    "ولا يتم تطبيقها تلقائيًا على القيم."
)

# ── Recommendation thresholds (spec §calibration_recommendation_levels) ───────
_NO_ACTION     = (0.97, 1.03)
_MINOR_LO      = (0.90, 0.97)
_MINOR_HI      = (1.03, 1.10)
_MODERATE_LO   = (0.80, 0.90)
_MODERATE_HI   = (1.10, 1.25)


# ── Low-level helpers ─────────────────────────────────────────────────────────

def _cs(val: Any) -> str:
    return str(val).strip() if val is not None else ""


def _safe_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _appraised_value(row: dict) -> Optional[float]:
    """Return the first positive market_value or assessed_value."""
    for key in ("market_value", "assessed_value"):
        v = row.get(key)
        if isinstance(v, (int, float)) and float(v) > 0:
            return float(v)
    return None


def _price_for_sale(sale: dict) -> Tuple[Optional[float], str]:
    """
    3-tier price selection (mirrors ratio_studies.py Phase 3.5 / 3.4).
      1. final_adjusted_sale_price  (Phase 3.5)
      2. adjusted_sale_price        (Phase 3.4)
      3. sale_price                 (raw)
    Returns (price, source_label) or (None, "none") when no valid price.
    """
    for field in ("final_adjusted_sale_price", "adjusted_sale_price", "sale_price"):
        v = _safe_float(sale.get(field))
        if v is not None and v > 0:
            return v, field
    return None, "none"


# ── Matching (mirrors ratio_studies._match_tier — private API not imported) ───

def _match_tier(sale: dict, subject: dict) -> Optional[int]:
    """
    Return best matching tier (1 = strongest) or None.
    Tiers: 1=zone+class, 2=zone+ptype, 3=zone, 4=loc+class,
           5=nbhd+class, 6=loc, 7=nbhd.
    """
    s_zone  = _cs(sale.get("zone_id"))
    s_class = _cs(sale.get("property_class")).lower()
    s_loc   = _cs(sale.get("location"))
    s_nbhd  = _cs(sale.get("neighborhood"))
    s_ptype = _cs(sale.get("property_type"))

    r_zone  = _cs(subject.get("zone_id"))
    r_class = _cs(subject.get("property_class")).lower()
    r_loc   = _cs(subject.get("location"))
    r_nbhd  = _cs(subject.get("neighborhood"))
    r_ptype = _cs(subject.get("property_type"))

    zone_m  = bool(s_zone  and r_zone  and s_zone  == r_zone)
    class_m = bool(s_class and r_class and s_class == r_class)
    loc_m   = bool(s_loc   and r_loc   and s_loc   == r_loc)
    nbhd_m  = bool(s_nbhd  and r_nbhd  and s_nbhd  == r_nbhd)
    ptype_m = bool(s_ptype and r_ptype and s_ptype == r_ptype)

    if zone_m and class_m: return 1
    if zone_m and ptype_m: return 2
    if zone_m:             return 3
    if loc_m  and class_m: return 4
    if nbhd_m and class_m: return 5
    if loc_m:              return 6
    if nbhd_m:             return 7
    return None


# ── Recommendation level ──────────────────────────────────────────────────────

def _recommendation(factor: float) -> str:
    if _NO_ACTION[0] <= factor <= _NO_ACTION[1]:
        return "no_action"
    if _MINOR_LO[0] <= factor < _MINOR_LO[1] or _MINOR_HI[0] < factor <= _MINOR_HI[1]:
        return "minor_adjustment"
    if _MODERATE_LO[0] <= factor < _MODERATE_LO[1] or _MODERATE_HI[0] < factor <= _MODERATE_HI[1]:
        return "moderate_adjustment"
    return "major_review"


# ── Core calibration metric block ─────────────────────────────────────────────

def _compute_calib(
    pairs: List[Dict[str, Any]],
    target: float,
    min_n: int,
) -> Dict[str, Any]:
    """
    Compute IAAO-style calibration metrics for a list of matched pairs.
    Returns suggested_factor = target / median_ratio (preview hint only).
    """
    if not pairs:
        return {
            "sample_size": 0,
            "median_ratio": None, "mean_ratio": None,
            "weighted_mean_ratio": None,
            "cod": None, "prd": None,
            "suggested_factor": None,
            "recommendation": None,
            "warnings": [{"code": "NO_PAIRS",
                           "message": "No matched pairs in this group."}],
        }

    ratios     = [p["ratio"]           for p in pairs]
    appraisals = [p["appraised_value"] for p in pairs]
    prices     = [p["sale_price_used"] for p in pairs]
    n = len(ratios)

    mean_r   = sum(ratios) / n
    median_r = statistics.median(ratios)
    sum_appr  = sum(appraisals)
    sum_sales = sum(prices)

    wt_mean_r: Optional[float] = (
        round(sum_appr / sum_sales, 6) if sum_sales > 0 else None
    )

    cod: Optional[float] = None
    if median_r > 0:
        cod = round(
            sum(abs(r - median_r) for r in ratios) / n / median_r * 100, 4
        )

    prd: Optional[float] = None
    if wt_mean_r and wt_mean_r > 0:
        prd = round(mean_r / wt_mean_r, 6)

    suggested_factor: Optional[float] = (
        round(target / median_r, 6) if median_r > 0 else None
    )
    rec: Optional[str] = (
        _recommendation(suggested_factor) if suggested_factor is not None else None
    )

    warnings: List[Dict[str, str]] = []
    if n < min_n:
        warnings.append({
            "code":    "LOW_SAMPLE_SIZE",
            "message": f"Sample size {n} is below the minimum {min_n}.",
        })
    if cod is not None and cod > 15:
        warnings.append({
            "code":    "HIGH_COD",
            "message": f"COD {cod:.2f}% exceeds IAAO guideline of 15%.",
        })
    if prd is not None and (prd < 0.98 or prd > 1.03):
        warnings.append({
            "code":    "PRD_OUT_OF_RANGE",
            "message": f"PRD {prd:.6f} is outside [0.98, 1.03]; price-related bias detected.",
        })
    if suggested_factor is not None and (suggested_factor < 0.75 or suggested_factor > 1.35):
        warnings.append({
            "code":    "EXTREME_CALIBRATION_FACTOR",
            "message": (f"suggested_factor {suggested_factor:.6f} is outside [0.75, 1.35]. "
                        "Major analyst review required."),
        })

    return {
        "sample_size":         n,
        "median_ratio":        round(median_r, 6),
        "mean_ratio":          round(mean_r, 6),
        "weighted_mean_ratio": wt_mean_r,
        "cod":                 cod,
        "prd":                 prd,
        "suggested_factor":    suggested_factor,
        "recommendation":      rec,
        "warnings":            warnings,
    }


# ── Group-level helpers ───────────────────────────────────────────────────────

def _group_calib(
    pairs: List[Dict[str, Any]],
    group_key: str,
    target: float,
    min_n: int,
) -> Dict[str, Dict[str, Any]]:
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for p in pairs:
        k = _cs(p.get(group_key)) or "UNSPECIFIED"
        groups.setdefault(k, []).append(p)
    return {k: _compute_calib(v, target, min_n) for k, v in sorted(groups.items())}


def _combo_calib(
    pairs: List[Dict[str, Any]],
    target: float,
    min_n: int,
) -> Dict[str, Dict[str, Any]]:
    """Zone+property_class combination metrics."""
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for p in pairs:
        z = _cs(p.get("zone_id"))        or "UNK"
        c = _cs(p.get("property_class")) or "UNK"
        groups.setdefault(f"{z}|{c}", []).append(p)
    return {k: _compute_calib(v, target, min_n) for k, v in sorted(groups.items())}


# ── Internal pair builder (fallback when no ratio_study supplied) ─────────────

def _build_pairs_internal(
    valid_subjects: List[dict],
    qualifying_sales: List[dict],
) -> List[Dict[str, Any]]:
    """
    Match each qualifying sale to the best-matching subject (lowest tier,
    then smallest area difference).  Each sale drives one ratio observation.
    """
    pairs: List[Dict[str, Any]] = []
    for sale in qualifying_sales:
        price, _ = _price_for_sale(sale)
        if price is None:
            continue
        sale_area = _safe_float(sale.get("area"))

        best_tier:      Optional[int]  = None
        best_subject:   Optional[dict] = None
        best_area_diff: float          = float("inf")

        for subj in valid_subjects:
            tier = _match_tier(sale, subj)
            if tier is None:
                continue
            subj_area = _safe_float(subj.get("area"))
            area_diff = (abs(subj_area - sale_area)
                         if sale_area is not None and subj_area is not None
                         else float("inf"))
            if (best_tier is None
                    or tier < best_tier
                    or (tier == best_tier and area_diff < best_area_diff)):
                best_tier      = tier
                best_subject   = subj
                best_area_diff = area_diff

        if best_subject is None:
            continue
        appr_val = _appraised_value(best_subject)
        if appr_val is None:
            continue

        ratio = round(appr_val / price, 6)
        pairs.append({
            "subject_row_id": best_subject.get("row_id"),
            "sale_id":        sale.get("sale_id"),
            "zone_id":        (_cs(best_subject.get("zone_id"))
                               or _cs(sale.get("zone_id")) or None),
            "property_class": (_cs(best_subject.get("property_class"))
                               or _cs(sale.get("property_class")) or None),
            "neighborhood":   (_cs(best_subject.get("neighborhood"))
                               or _cs(sale.get("neighborhood")) or None),
            "appraised_value": round(appr_val, 2),
            "sale_price_used": round(price, 2),
            "ratio":           ratio,
        })
    return pairs


# ── Public API ────────────────────────────────────────────────────────────────

def preview_calibration(
    subject_rows: list,
    sale_records: list,
    ratio_study: Optional[dict] = None,
    options: Optional[dict] = None,
) -> dict:
    """
    Produce calibration factor hints by portfolio, zone, property class,
    and zone+property_class combination.

    PREVIEW ONLY — does not modify any appraised values or formulas.

    Parameters
    ----------
    subject_rows : list
        Mass Appraisal batch run result rows.
    sale_records : list
        Verified/time-adjusted/final-adjusted sale records.
    ratio_study : dict | None
        Optional Phase 3.3 ratio study result; its matched_pairs are
        reused directly when available to avoid redundant re-matching.
    options : dict | None
        target_median_ratio       (float, default 1.0)
        min_sample_size           (int,   default 3)
        include_needs_review_sales (bool,  default False)
    """
    options = options or {}
    target: float = float(options.get("target_median_ratio", 1.0))
    min_n:  int   = int(options.get("min_sample_size", 3))
    include_nr    = bool(options.get("include_needs_review_sales", False))

    # ── Input guards ──────────────────────────────────────────────────────────
    if not isinstance(subject_rows, list):
        return {
            "status":     "error",
            "error_code": "INVALID_SUBJECT_ROWS_TYPE",
            "message":    "subject_rows must be a list of row dicts.",
        }
    if not isinstance(sale_records, list):
        return {
            "status":     "error",
            "error_code": "INVALID_SALE_RECORDS_TYPE",
            "message":    "sale_records must be a list of sale record dicts.",
        }

    # ── Pair sourcing: prefer ratio_study matched_pairs ───────────────────────
    pairs: List[Dict[str, Any]] = []
    pairs_source = "internal"

    if isinstance(ratio_study, dict) and ratio_study.get("status") == "success":
        raw = ratio_study.get("matched_pairs")
        if isinstance(raw, list) and raw:
            for p in raw:
                sp  = _safe_float(p.get("sale_price_used"))
                apv = _safe_float(p.get("appraised_value"))
                rat = _safe_float(p.get("ratio"))
                if sp and sp > 0 and apv and apv > 0 and rat is not None:
                    pairs.append({
                        "subject_row_id": p.get("subject_row_id"),
                        "sale_id":        p.get("sale_id"),
                        "zone_id":        p.get("zone_id"),
                        "property_class": p.get("property_class"),
                        "neighborhood":   p.get("neighborhood"),
                        "appraised_value": apv,
                        "sale_price_used": sp,
                        "ratio":           rat,
                    })
            if pairs:
                pairs_source = "ratio_study"

    # ── Fallback: build pairs internally ──────────────────────────────────────
    if not pairs:
        accepted = {"usable", "needs_review"} if include_nr else {"usable"}
        valid_subjects = [
            r for r in subject_rows
            if isinstance(r, dict)
            and _appraised_value(r) is not None
            and _cs(r.get("status")) not in ("excluded", "error")
        ]
        qualifying_sales = [
            s for s in sale_records
            if isinstance(s, dict)
            and _cs(s.get("usability_status")) in accepted
        ]
        pairs = _build_pairs_internal(valid_subjects, qualifying_sales)

    # ── Compute calibration metrics ───────────────────────────────────────────
    portfolio_calib = _compute_calib(pairs, target, min_n)
    zone_calib      = _group_calib(pairs, "zone_id",        target, min_n)
    pclass_calib    = _group_calib(pairs, "property_class", target, min_n)
    combo_calib     = _combo_calib(pairs, target, min_n)

    # ── Summary KPIs ──────────────────────────────────────────────────────────
    port_sf  = portfolio_calib.get("suggested_factor")
    port_rec = portfolio_calib.get("recommendation")

    all_groups = (list(zone_calib.values()) +
                  list(pclass_calib.values()) +
                  list(combo_calib.values()))
    low_sample_count   = sum(
        1 for g in all_groups
        if 0 < g.get("sample_size", 0) < min_n
    )
    major_review_count = sum(
        1 for g in all_groups
        if g.get("recommendation") == "major_review"
    )

    top_warnings: List[Dict[str, str]] = list(portfolio_calib.get("warnings") or [])
    if not pairs:
        top_warnings.append({
            "code":    "NO_PAIRS",
            "message": ("No matched sale/subject pairs were found. "
                        "Check that subject_rows have market_value and "
                        "sale_records have usability_status='usable'."),
        })

    return {
        "status": "success",
        "phase":  "calibration_preview",
        "summary": {
            "subject_count":                len(subject_rows),
            "sales_count":                  len(sale_records),
            "matched_pair_count":           len(pairs),
            "pairs_source":                 pairs_source,
            "target_median_ratio":          target,
            "portfolio_suggested_factor":   port_sf,
            "portfolio_recommendation":     port_rec,
            "groups_with_low_sample":       low_sample_count,
            "groups_requiring_major_review": major_review_count,
            "warnings":                     top_warnings,
        },
        "portfolio_calibration":             portfolio_calib,
        "zone_calibration":                  zone_calib,
        "property_class_calibration":        pclass_calib,
        "zone_property_class_calibration":   combo_calib,
        "calibration_notes":                 [_CALIBRATION_NOTE],
    }


__all__ = ["preview_calibration"]
