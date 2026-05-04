"""
core_engine/sales_verification.py
==================================
Mass Appraisal Phase 3.2 — Sales Data Intake & Verification Layer

Pure-Python sales evidence intake.  NO valuation, NO calibration,
NO ratio studies, NO database, NO file I/O, NO Flask imports.

This module prepares verified sales evidence for future calibration and
ratio studies.  It does NOT modify any valuation formula.

Public API:
    validate_sales_records(records: list, options: dict | None = None) -> dict
    verify_sales_records(records: list, options: dict | None = None)  -> dict

Constants:
    MAX_SALES_RECORDS = 1000
"""
from __future__ import annotations

import statistics
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# ── Constants ─────────────────────────────────────────────────────────────────

MAX_SALES_RECORDS: int = 1000

_REQUIRED_FIELDS: Tuple[str, ...] = (
    "sale_id", "sale_price", "sale_date", "location", "property_type", "area",
)

# Buyer/seller types that indicate a non-arm's-length transaction
_RELATED_PARTY_TYPES = frozenset({
    "related", "family", "relative", "عائلة", "قريب", "أقارب",
    "partner", "affiliate", "subsidiary", "shareholder",
})

_ABNORMAL_FINANCING_TYPES = frozenset({
    "assumption", "seller_financed", "seller financed", "land_contract",
    "بيع بالتقسيط بدون بنك", "deferred",
})

# Keywords in `notes` that signal a distressed or non-arm's-length sale
_DISTRESS_KEYWORDS = (
    "forced", "distressed", "foreclosure", "liquidation", "تصفية",
    "قسري", "إجباري", "إفلاس", "اضطرار", "أقارب", "قريب",
    "بين أطراف ذوي صلة", "بيع بين", "relative", "family",
)

# Verification status values
_VS_VERIFIED     = "verified"
_VS_NEEDS_REVIEW = "needs_review"
_VS_REJECTED     = "rejected"

# Usability status values
_US_USABLE       = "usable"
_US_EXCLUDED     = "excluded"
_US_NEEDS_REVIEW = "needs_review"

# Exclusion reason codes
_ER_INVALID_PRICE    = "INVALID_PRICE"
_ER_INVALID_AREA     = "INVALID_AREA"
_ER_MISSING_FIELD    = "MISSING_REQUIRED_FIELD"
_ER_RELATED_PARTY    = "RELATED_PARTY"
_ER_DISTRESSED_SALE  = "DISTRESSED_SALE"
_ER_ABNORMAL_FIN     = "ABNORMAL_FINANCING"
_ER_UNVERIFIED       = "UNVERIFIED_SOURCE"
_ER_UNKNOWN          = "UNKNOWN"


# ── Internal helpers ──────────────────────────────────────────────────────────

def _vflag(severity: str, code: str, message: str) -> Dict[str, str]:
    return {"severity": severity, "code": code, "message": message}


def _clean_str(val: Any) -> str:
    return str(val).strip() if val is not None else ""


def _to_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _check_arms_length(rec: dict) -> Tuple[bool, List[Dict[str, str]], Optional[str]]:
    """
    Return (arms_length: bool, flags: list, exclusion_reason: str|None).

    arms_length is False when the transaction exhibits related-party,
    distressed-sale, or abnormal-financing characteristics.
    """
    flags: List[Dict[str, str]] = []
    exclusion_reason: Optional[str] = None
    arms_length = True

    # 1. Explicit relationship_flag
    if rec.get("relationship_flag") is True:
        arms_length = False
        exclusion_reason = _ER_RELATED_PARTY
        flags.append(_vflag("warning", _ER_RELATED_PARTY,
                             "relationship_flag is true; transaction may not be arm's length."))

    # 2. buyer_type / seller_type
    buyer  = _clean_str(rec.get("buyer_type")).lower()
    seller = _clean_str(rec.get("seller_type")).lower()
    if buyer in _RELATED_PARTY_TYPES or seller in _RELATED_PARTY_TYPES:
        arms_length = False
        if exclusion_reason is None:
            exclusion_reason = _ER_RELATED_PARTY
        flags.append(_vflag("warning", _ER_RELATED_PARTY,
                             f"buyer_type='{buyer or 'N/A'}' or seller_type='{seller or 'N/A'}' "
                             "indicates a related-party transaction."))

    # 3. financing_type
    fin = _clean_str(rec.get("financing_type")).lower()
    if fin and fin in _ABNORMAL_FINANCING_TYPES:
        arms_length = False
        if exclusion_reason is None:
            exclusion_reason = _ER_ABNORMAL_FIN
        flags.append(_vflag("warning", _ER_ABNORMAL_FIN,
                             f"financing_type='{fin}' indicates an abnormal financing arrangement."))

    # 4. notes keyword scan
    notes_raw = _clean_str(rec.get("notes")).lower()
    if notes_raw:
        for kw in _DISTRESS_KEYWORDS:
            if kw in notes_raw:
                arms_length = False
                if exclusion_reason is None:
                    exclusion_reason = _ER_DISTRESSED_SALE
                flags.append(_vflag("warning", _ER_DISTRESSED_SALE,
                                     f"notes contain keyword '{kw}' suggesting a distressed or "
                                     "related-party sale."))
                break  # one flag per record is enough

    return arms_length, flags, exclusion_reason


def _parse_sale_record(
    index: int, rec: dict, options: dict
) -> Dict[str, Any]:
    """
    Validate and enrich a single sale record.
    Returns the full per-record result dict.
    """
    errors:  List[str] = []
    warnings: List[str] = []
    vflags:  List[Dict[str, str]] = []

    # ── Identity ─────────────────────────────────────────────────────────────
    raw_sid = rec.get("sale_id")
    sale_id = (_clean_str(raw_sid) if raw_sid is not None else "") or f"S-{index + 1:04d}"

    # ── Required field checks ─────────────────────────────────────────────────
    missing = [f for f in _REQUIRED_FIELDS if rec.get(f) in (None, "")]
    for f in missing:
        errors.append(f"missing required field: {f}")
        vflags.append(_vflag("error", _ER_MISSING_FIELD,
                              f"Required field '{f}' is missing or blank."))

    # ── sale_price ────────────────────────────────────────────────────────────
    raw_price = _to_float(rec.get("sale_price"))
    exclusion_reason: Optional[str] = None

    if raw_price is None and "sale_price" not in missing:
        errors.append("sale_price must be numeric")
        vflags.append(_vflag("error", _ER_INVALID_PRICE, "sale_price is not numeric."))
        raw_price = None
    elif raw_price is not None and raw_price <= 0:
        errors.append("sale_price must be > 0")
        vflags.append(_vflag("error", _ER_INVALID_PRICE,
                              f"sale_price={raw_price} is not positive."))
        exclusion_reason = _ER_INVALID_PRICE
        raw_price = None  # treat as unusable

    # ── area ─────────────────────────────────────────────────────────────────
    raw_area = _to_float(rec.get("area"))

    if raw_area is None and "area" not in missing:
        errors.append("area must be numeric")
        vflags.append(_vflag("error", _ER_INVALID_AREA, "area is not numeric."))
        raw_area = None
    elif raw_area is not None and raw_area <= 0:
        errors.append("area must be > 0")
        vflags.append(_vflag("error", _ER_INVALID_AREA,
                              f"area={raw_area} is not positive."))
        if exclusion_reason is None:
            exclusion_reason = _ER_INVALID_AREA
        raw_area = None

    # ── sale_price_per_m2 ─────────────────────────────────────────────────────
    ppm2: Optional[float] = None
    if raw_price is not None and raw_area is not None and raw_area > 0:
        ppm2 = round(raw_price / raw_area, 2)

    # ── sale_date (basic string validation — no strict parsing) ───────────────
    sale_date_str = _clean_str(rec.get("sale_date"))
    if sale_date_str and len(sale_date_str) < 6:
        warnings.append("sale_date format looks unusual; expected YYYY-MM-DD.")
        vflags.append(_vflag("warning", "UNUSUAL_DATE_FORMAT",
                              f"sale_date='{sale_date_str}' may not be in YYYY-MM-DD format."))

    # ── Zone/class fields (same normalisation as mass_zones) ─────────────────
    zone_id      = _clean_str(rec.get("zone_id"))     or None
    neighborhood = _clean_str(rec.get("neighborhood")) or None
    submarket    = _clean_str(rec.get("submarket"))    or None

    raw_pc = rec.get("property_class")
    if raw_pc is None or _clean_str(raw_pc) == "":
        property_class: Optional[str] = None
    else:
        pc = _clean_str(raw_pc)
        # Lowercase only ASCII-looking strings; preserve Arabic
        property_class = pc.lower() if pc.isascii() else pc

    # ── Arms-length check ─────────────────────────────────────────────────────
    is_valid_so_far = len(errors) == 0

    if is_valid_so_far:
        al, al_flags, al_excl = _check_arms_length(rec)
        vflags.extend(al_flags)
        if not al and exclusion_reason is None:
            exclusion_reason = al_excl
    else:
        al = True  # irrelevant for invalid records

    # ── Data source / verification source ────────────────────────────────────
    has_datasource = bool(
        _clean_str(rec.get("verification_source")) or _clean_str(rec.get("data_source"))
    )
    if not has_datasource and is_valid_so_far:
        warnings.append("No verification_source or data_source supplied.")
        vflags.append(_vflag("warning", _ER_UNVERIFIED,
                              "Neither verification_source nor data_source is provided; "
                              "usability will be set to needs_review."))

    # ── Determine verification_status / usability_status ─────────────────────
    valid = len(errors) == 0

    if not valid:
        verification_status = _VS_REJECTED
        usability_status    = _US_EXCLUDED
        if exclusion_reason is None:
            exclusion_reason = _ER_MISSING_FIELD if missing else _ER_UNKNOWN
    elif not al:
        verification_status = _VS_NEEDS_REVIEW
        usability_status    = _US_EXCLUDED
    elif not has_datasource:
        verification_status = _VS_NEEDS_REVIEW
        usability_status    = _US_NEEDS_REVIEW
    else:
        verification_status = _VS_VERIFIED
        usability_status    = _US_USABLE

    return {
        "sale_index":         index,
        "sale_id":            sale_id,
        "valid":              valid,
        "verification_status": verification_status,
        "usability_status":   usability_status,
        "exclusion_reason":   exclusion_reason,
        "warnings":           warnings,
        "errors":             errors,
        "sale_price":         raw_price,
        "area":               raw_area,
        "sale_price_per_m2":  ppm2,
        "sale_date":          sale_date_str or None,
        "location":           _clean_str(rec.get("location")) or None,
        "zone_id":            zone_id,
        "neighborhood":       neighborhood,
        "submarket":          submarket,
        "property_class":     property_class,
        "property_type":      _clean_str(rec.get("property_type")) or None,
        "arms_length":        al,
        "verification_flags": vflags,
    }


# ── Public API ────────────────────────────────────────────────────────────────

def validate_sales_records(
    records: list, options: Optional[dict] = None
) -> dict:
    """
    Validate a list of sale records without computing aggregate statistics.

    Returns a lightweight preview result (validation only, no summaries).
    """
    options = options or {}

    if not isinstance(records, list):
        return {"status": "error", "error_code": "INVALID_RECORDS_TYPE",
                "message": "records must be a list of sale record dictionaries."}
    if len(records) == 0:
        return {"status": "error", "error_code": "MISSING_RECORDS",
                "message": "records[] is empty; at least one sale record is required."}
    if len(records) > MAX_SALES_RECORDS:
        return {"status": "error", "error_code": "TOO_MANY_RECORDS",
                "message": (f"records[] has {len(records)} entries; "
                            f"maximum is {MAX_SALES_RECORDS}."),
                "limit": MAX_SALES_RECORDS}

    parsed: List[Dict[str, Any]] = []
    valid_count   = 0
    invalid_count = 0

    for i, rec in enumerate(records):
        if not isinstance(rec, dict):
            parsed.append({
                "sale_index": i,
                "sale_id":    f"S-{i + 1:04d}",
                "valid":      False,
                "errors":     ["record is not a dict"],
                "warnings":   [],
                "verification_status": _VS_REJECTED,
                "usability_status":    _US_EXCLUDED,
                "exclusion_reason":    _ER_UNKNOWN,
                "verification_flags":  [_vflag("error", _ER_UNKNOWN,
                                                "Record is not a dictionary.")],
            })
            invalid_count += 1
            continue

        result = _parse_sale_record(i, rec, options)
        parsed.append(result)
        if result["valid"]:
            valid_count += 1
        else:
            invalid_count += 1

    return {
        "status": "success",
        "phase":  "sales_validation",
        "summary": {
            "total_records":   len(records),
            "valid_records":   valid_count,
            "invalid_records": invalid_count,
        },
        "records": parsed,
    }


def verify_sales_records(
    records: list, options: Optional[dict] = None
) -> dict:
    """
    Validate and produce full verification results with aggregate statistics.

    Aggregate statistics cover only records where sale_price and area are
    available (valid numeric values).  Invalid records contribute to counts
    but not to price/area metrics.

    zone_summary groups by zone_id (uses "UNSPECIFIED" when absent).
    property_class_summary groups by property_class (uses "UNSPECIFIED" when absent).
    """
    options = options or {}

    # Reuse validate for guard checks + per-record parsing
    pre = validate_sales_records(records, options)
    if pre.get("status") == "error":
        return pre

    parsed = pre["records"]

    # ── Aggregate counters ────────────────────────────────────────────────────
    usable_count      = 0
    excluded_count    = 0
    needs_review_count = 0
    exclusion_counts: Dict[str, int] = {}

    all_prices:  List[float] = []
    all_ppm2s:   List[float] = []

    # zone_summary: keyed by zone_id (or "UNSPECIFIED")
    zone_agg:   Dict[str, Dict[str, Any]] = {}
    pclass_agg: Dict[str, Dict[str, Any]] = {}

    def _ensure_group(agg: dict, key: str) -> dict:
        if key not in agg:
            agg[key] = {
                "sale_count":        0,
                "usable_count":      0,
                "excluded_count":    0,
                "needs_review_count": 0,
                "_prices":           [],
                "_ppm2s":            [],
            }
        return agg[key]

    for rr in parsed:
        us = rr.get("usability_status", _US_EXCLUDED)
        if us == _US_USABLE:
            usable_count += 1
        elif us == _US_EXCLUDED:
            excluded_count += 1
        else:
            needs_review_count += 1

        er = rr.get("exclusion_reason")
        if er:
            exclusion_counts[er] = exclusion_counts.get(er, 0) + 1

        sp   = rr.get("sale_price")
        ppm2 = rr.get("sale_price_per_m2")

        if isinstance(sp,   (int, float)) and sp   > 0:
            all_prices.append(sp)
        if isinstance(ppm2, (int, float)) and ppm2 > 0:
            all_ppm2s.append(ppm2)

        # Zone grouping
        zone_key = rr.get("zone_id") or "UNSPECIFIED"
        zb = _ensure_group(zone_agg, zone_key)
        zb["sale_count"] += 1
        if us == _US_USABLE:       zb["usable_count"]      += 1
        elif us == _US_EXCLUDED:   zb["excluded_count"]     += 1
        else:                      zb["needs_review_count"] += 1
        if isinstance(sp,   (int, float)) and sp   > 0: zb["_prices"].append(sp)
        if isinstance(ppm2, (int, float)) and ppm2 > 0: zb["_ppm2s"].append(ppm2)

        # Property-class grouping
        pc_key = rr.get("property_class") or "UNSPECIFIED"
        pb = _ensure_group(pclass_agg, pc_key)
        pb["sale_count"] += 1
        if us == _US_USABLE:       pb["usable_count"]      += 1
        elif us == _US_EXCLUDED:   pb["excluded_count"]     += 1
        else:                      pb["needs_review_count"] += 1
        if isinstance(sp,   (int, float)) and sp   > 0: pb["_prices"].append(sp)
        if isinstance(ppm2, (int, float)) and ppm2 > 0: pb["_ppm2s"].append(ppm2)

    # ── Portfolio-level statistics ────────────────────────────────────────────
    def _avg(lst: list) -> Optional[float]:
        return round(sum(lst) / len(lst), 2) if lst else None

    def _med(lst: list) -> Optional[float]:
        return round(statistics.median(lst), 2) if lst else None

    avg_price  = _avg(all_prices)
    med_price  = _med(all_prices)
    avg_ppm2   = _avg(all_ppm2s)
    med_ppm2   = _med(all_ppm2s)

    # ── Finalise group summaries ──────────────────────────────────────────────
    def _finalise(agg: dict) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for key, b in sorted(agg.items()):
            out[key] = {
                "sale_count":           b["sale_count"],
                "usable_count":         b["usable_count"],
                "excluded_count":       b["excluded_count"],
                "needs_review_count":   b["needs_review_count"],
                "average_sale_price":   _avg(b["_prices"]),
                "median_sale_price":    _med(b["_prices"]),
                "average_price_per_m2": _avg(b["_ppm2s"]),
                "median_price_per_m2":  _med(b["_ppm2s"]),
            }
        return out

    zone_summary   = _finalise(zone_agg)
    pclass_summary = _finalise(pclass_agg)

    return {
        "status": "success",
        "phase":  "sales_verification",
        "summary": {
            "total_records":      len(records),
            "valid_records":      pre["summary"]["valid_records"],
            "invalid_records":    pre["summary"]["invalid_records"],
            "usable_sales":       usable_count,
            "excluded_sales":     excluded_count,
            "needs_review_sales": needs_review_count,
            "average_sale_price":   avg_price,
            "median_sale_price":    med_price,
            "average_price_per_m2": avg_ppm2,
            "median_price_per_m2":  med_ppm2,
            "zone_summary":              zone_summary,
            "property_class_summary":    pclass_summary,
            "exclusion_reason_counts":   exclusion_counts,
        },
        "records": parsed,
    }


__all__ = [
    "MAX_SALES_RECORDS",
    "validate_sales_records",
    "verify_sales_records",
]
