"""
core_engine/ratio_studies.py
=============================
Mass Appraisal Phase 3.3 — Ratio Study Module

Pure-Python IAAO-standard ratio study calculations.
NO valuation formula changes, NO calibration, NO database,
NO file I/O, NO Flask imports.

Compares appraised/assessed values against verified sale prices
and produces mass appraisal quality-control metrics by portfolio,
zone, and property class.  Does NOT modify assessed values or
valuation formulas.

Public API:
    run_ratio_study(subject_rows, sale_records, options=None) -> dict
"""
from __future__ import annotations

import statistics
from typing import Any, Dict, List, Optional, Tuple

# ── Matching tier definitions ─────────────────────────────────────────────────
# Lower tier number = better / more specific match.

_TIER_BASIS: Dict[int, str] = {
    1: "zone_id+property_class",
    2: "zone_id+property_type",
    3: "zone_id",
    4: "location+property_class",
    5: "neighborhood+property_class",
    6: "location",
    7: "neighborhood",
}


def _cs(val: Any) -> str:
    """Clean-string helper: strip and return empty string for None."""
    return str(val).strip() if val is not None else ""


def _match_tier(sale: dict, subject: dict) -> Optional[int]:
    """
    Return the best matching priority tier (1 = strongest) or None (no match).

    Matching hierarchy:
      1 — zone_id + property_class (best)
      2 — zone_id + property_type
      3 — zone_id only
      4 — location + property_class
      5 — neighborhood + property_class
      6 — location only
      7 — neighborhood only
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

    zone_match  = bool(s_zone  and r_zone  and s_zone  == r_zone)
    class_match = bool(s_class and r_class and s_class == r_class)
    loc_match   = bool(s_loc   and r_loc   and s_loc   == r_loc)
    nbhd_match  = bool(s_nbhd  and r_nbhd  and s_nbhd  == r_nbhd)
    ptype_match = bool(s_ptype and r_ptype and s_ptype == r_ptype)

    if zone_match and class_match:  return 1
    if zone_match and ptype_match:  return 2
    if zone_match:                  return 3
    if loc_match  and class_match:  return 4
    if nbhd_match and class_match:  return 5
    if loc_match:                   return 6
    if nbhd_match:                  return 7
    return None


def _appraised_value(row: dict) -> Optional[float]:
    """Return a positive appraised value from market_value or assessed_value."""
    for key in ("market_value", "assessed_value"):
        v = row.get(key)
        if isinstance(v, (int, float)) and float(v) > 0:
            return float(v)
    return None


def _safe_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# ── Core metric computations ──────────────────────────────────────────────────

def _compute_metrics(pairs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute IAAO ratio study metrics for a list of matched pairs.

    Formulas:
      mean_ratio          = average(ratio)
      median_ratio        = median(ratio)
      weighted_mean_ratio = Σ(appraised_value) / Σ(sale_price)
      COD                 = mean(|ratio - median|) / median * 100
      PRD                 = mean_ratio / weighted_mean_ratio
    """
    if not pairs:
        return {
            "sample_size": 0,
            "mean_ratio": None, "median_ratio": None, "weighted_mean_ratio": None,
            "cod": None, "prd": None, "min_ratio": None, "max_ratio": None,
            "warnings": [{"code": "NO_PAIRS",
                          "message": "No matched pairs available in this group."}],
        }

    ratios      = [p["ratio"]           for p in pairs]
    appraisals  = [p["appraised_value"] for p in pairs]
    sale_prices = [p["sale_price"]      for p in pairs]

    n         = len(ratios)
    mean_r    = sum(ratios) / n
    median_r  = statistics.median(ratios)
    sum_appr  = sum(appraisals)
    sum_sales = sum(sale_prices)

    wt_mean_r: Optional[float] = (round(sum_appr / sum_sales, 6)
                                   if sum_sales > 0 else None)

    cod: Optional[float] = None
    if median_r > 0:
        cod = round(
            sum(abs(r - median_r) for r in ratios) / n / median_r * 100, 4
        )

    prd: Optional[float] = None
    if wt_mean_r and wt_mean_r > 0:
        prd = round(mean_r / wt_mean_r, 6)

    warnings: List[Dict[str, str]] = []
    if n < 3:
        warnings.append({
            "code":    "LOW_SAMPLE_SIZE",
            "message": (f"Sample size {n} is below the minimum recommended of 3 "
                        "for reliable IAAO statistics."),
        })

    return {
        "sample_size":         n,
        "mean_ratio":          round(mean_r,   6),
        "median_ratio":        round(median_r, 6),
        "weighted_mean_ratio": wt_mean_r,
        "cod":                 cod,
        "prd":                 prd,
        "min_ratio":           round(min(ratios), 6),
        "max_ratio":           round(max(ratios), 6),
        "warnings":            warnings,
    }


def _group_metrics(
    pairs: List[Dict[str, Any]], group_key: str
) -> Dict[str, Dict[str, Any]]:
    """Group matched pairs by group_key and compute metrics per group."""
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for p in pairs:
        k = _cs(p.get(group_key)) or "UNSPECIFIED"
        groups.setdefault(k, []).append(p)
    return {k: _compute_metrics(v) for k, v in sorted(groups.items())}


# ── Public API ────────────────────────────────────────────────────────────────

def run_ratio_study(
    subject_rows: list,
    sale_records: list,
    options: Optional[dict] = None,
) -> dict:
    """
    Compare appraised values against verified sale prices and compute
    IAAO-standard ratio study metrics.

    Matching priority (per sale):
      Tier 1: zone_id + property_class  (strongest)
      Tier 2: zone_id + property_type
      Tier 3: zone_id only
      Tier 4: location + property_class
      Tier 5: neighborhood + property_class
      Tier 6: location only
      Tier 7: neighborhood only  (weakest)

    Within each tier, the subject with the smallest area difference is
    selected.  A sale that finds no matching subject is left unmatched.
    Subjects may be matched to multiple sales (each sale drives one ratio
    observation).

    Does NOT modify assessed values, valuation formulas, or AVM logic.
    """
    options = options or {}
    include_nr_sales = bool(options.get("include_needs_review_sales", False))

    # ── Guard checks ──────────────────────────────────────────────────────────
    if not isinstance(subject_rows, list):
        return {"status": "error", "error_code": "INVALID_SUBJECT_ROWS_TYPE",
                "message": "subject_rows must be a list of row dicts."}
    if not isinstance(sale_records, list):
        return {"status": "error", "error_code": "INVALID_SALE_RECORDS_TYPE",
                "message": "sale_records must be a list of sale record dicts."}

    # ── Filter qualifying sales ───────────────────────────────────────────────
    accepted_us = {"usable"}
    if include_nr_sales:
        accepted_us.add("needs_review")

    qualifying_sales: List[dict] = [
        s for s in sale_records
        if isinstance(s, dict)
        and _cs(s.get("usability_status")) in accepted_us
        and isinstance(s.get("sale_price"), (int, float))
        and float(s["sale_price"]) > 0
    ]

    # ── Filter valid subject rows (must carry a positive appraised value) ─────
    valid_subjects: List[dict] = [
        r for r in subject_rows
        if isinstance(r, dict) and _appraised_value(r) is not None
    ]

    # ── Matching: for each sale, find best-matching subject ───────────────────
    matched_pairs:      List[Dict[str, Any]] = []
    matched_subject_ids: set = set()
    matched_sale_ids:    set = set()

    for sale in qualifying_sales:
        sale_price = float(sale["sale_price"])
        sale_area  = _safe_float(sale.get("area"))

        best_tier:      Optional[int]  = None
        best_subject:   Optional[dict] = None
        best_area_diff: float          = float("inf")

        for subj in valid_subjects:
            tier = _match_tier(sale, subj)
            if tier is None:
                continue

            subj_area  = _safe_float(subj.get("area"))
            area_diff  = (abs(subj_area - sale_area)
                          if sale_area is not None and subj_area is not None
                          else float("inf"))

            # Prefer lower tier (better match); break ties by smaller area diff
            if (best_tier is None
                    or tier < best_tier
                    or (tier == best_tier and area_diff < best_area_diff)):
                best_tier      = tier
                best_subject   = subj
                best_area_diff = area_diff

        if best_subject is None:
            continue  # no subject matches this sale

        appr_val = _appraised_value(best_subject)  # guaranteed non-None

        # Phase 3.5 / 3.4: price priority: final_adjusted > adjusted > raw
        _fin_sp = sale.get("final_adjusted_sale_price")
        _adj_sp = sale.get("adjusted_sale_price")
        if isinstance(_fin_sp, (int, float)) and float(_fin_sp) > 0:
            sale_price_used   = float(_fin_sp)
            sale_price_source = "final_adjusted_sale_price"
        elif isinstance(_adj_sp, (int, float)) and float(_adj_sp) > 0:
            sale_price_used   = float(_adj_sp)
            sale_price_source = "adjusted_sale_price"
        else:
            sale_price_used   = sale_price
            sale_price_source = "sale_price"

        ratio = round(appr_val / sale_price_used, 6)

        # Per-m² prices (best-effort)
        subj_area_v = _safe_float(best_subject.get("area"))
        appr_pm2: Optional[float] = (
            round(appr_val / subj_area_v, 2) if subj_area_v and subj_area_v > 0 else None
        )
        sale_pm2 = _safe_float(sale.get("sale_price_per_m2"))
        if sale_pm2 is None and sale_area and sale_area > 0:
            sale_pm2 = round(sale_price_used / sale_area, 2)

        pair: Dict[str, Any] = {
            "subject_row_id":          best_subject.get("row_id"),
            "sale_id":                 sale.get("sale_id"),
            "zone_id":                 _cs(best_subject.get("zone_id")) or _cs(sale.get("zone_id")) or None,
            "neighborhood":            _cs(best_subject.get("neighborhood")) or _cs(sale.get("neighborhood")) or None,
            "submarket":               _cs(best_subject.get("submarket")) or _cs(sale.get("submarket")) or None,
            "property_class":          _cs(best_subject.get("property_class")) or _cs(sale.get("property_class")) or None,
            "property_type":           _cs(best_subject.get("property_type")) or _cs(sale.get("property_type")) or None,
            "appraised_value":         round(appr_val, 2),
            "sale_price":              round(sale_price, 2),
            # Phase 3.4 / 3.5 traceability fields
            "sale_price_used":         round(sale_price_used, 2),
            "sale_price_source":       sale_price_source,
            "time_adjustment_factor":  sale.get("time_adjustment_factor"),
            "final_adjustment_factor": sale.get("final_adjustment_factor"),
            "ratio":                   ratio,
            "ratio_pct":               round(ratio * 100, 4),
            "sale_price_per_m2":       round(sale_pm2, 2) if sale_pm2 is not None else None,
            "appraised_value_per_m2":  appr_pm2,
            "match_basis":             _TIER_BASIS.get(best_tier, "unknown"),
            "match_area_diff":         (round(best_area_diff, 2)
                                        if best_area_diff != float("inf") else None),
        }
        matched_pairs.append(pair)
        matched_subject_ids.add(id(best_subject))
        matched_sale_ids.add(id(sale))

    # ── Annotate pairs with deviation from median ─────────────────────────────
    if matched_pairs:
        all_ratios = [p["ratio"] for p in matched_pairs]
        med_all    = statistics.median(all_ratios)
        for p in matched_pairs:
            abs_dev = round(abs(p["ratio"] - med_all), 6)
            pct_dev = round(abs_dev / med_all * 100, 4) if med_all > 0 else None
            p["absolute_deviation_from_median"] = abs_dev
            p["percent_deviation_from_median"]  = pct_dev

    # ── Unmatched tracking ────────────────────────────────────────────────────
    unmatched_subjects: List[Dict[str, Any]] = [
        {
            "row_id":         r.get("row_id"),
            "zone_id":        r.get("zone_id"),
            "property_class": r.get("property_class"),
            "location":       r.get("location"),
            "area":           r.get("area"),
        }
        for r in valid_subjects
        if id(r) not in matched_subject_ids
    ]
    unmatched_sales: List[Dict[str, Any]] = [
        {
            "sale_id":        s.get("sale_id"),
            "zone_id":        s.get("zone_id"),
            "property_class": s.get("property_class"),
            "location":       s.get("location"),
            "sale_price":     s.get("sale_price"),
        }
        for s in qualifying_sales
        if id(s) not in matched_sale_ids
    ]

    # ── Portfolio-level metrics ───────────────────────────────────────────────
    portfolio_metrics = _compute_metrics(matched_pairs)

    # ── Group metrics ─────────────────────────────────────────────────────────
    zone_metrics           = _group_metrics(matched_pairs, "zone_id")
    property_class_metrics = _group_metrics(matched_pairs, "property_class")

    # Submarket metrics only when at least one pair carries a submarket
    submarket_metrics: Dict[str, Any] = (
        _group_metrics(matched_pairs, "submarket")
        if any(p.get("submarket") for p in matched_pairs) else {}
    )

    # ── Collect top-level warnings ────────────────────────────────────────────
    top_warnings = list(portfolio_metrics.get("warnings") or [])
    if len(qualifying_sales) == 0:
        top_warnings.append({
            "code":    "NO_QUALIFYING_SALES",
            "message": ("No sales with usability_status='usable' were found. "
                        "Run sales verification first or set include_needs_review_sales=true."),
        })
    if len(valid_subjects) == 0:
        top_warnings.append({
            "code":    "NO_VALID_SUBJECTS",
            "message": "No subject rows with a positive appraised value were found.",
        })

    return {
        "status": "success",
        "phase":  "ratio_study",
        "summary": {
            "subject_count":           len(subject_rows),
            "sales_count":             len(sale_records),
            "usable_sales_count":      len(qualifying_sales),
            "matched_pair_count":      len(matched_pairs),
            "unmatched_subject_count": len(unmatched_subjects),
            "unmatched_sales_count":   len(unmatched_sales),
            "portfolio_metrics":       portfolio_metrics,
            "warnings":                top_warnings,
        },
        "matched_pairs":            matched_pairs,
        "zone_metrics":             zone_metrics,
        "property_class_metrics":   property_class_metrics,
        "submarket_metrics":        submarket_metrics,
        "unmatched_subjects":       unmatched_subjects,
        "unmatched_sales":          unmatched_sales,
    }


__all__ = ["run_ratio_study"]
