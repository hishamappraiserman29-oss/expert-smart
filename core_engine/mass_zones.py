"""
core_engine/mass_zones.py
=========================
Mass Appraisal Phase 3.1 — Market Zones & Property-Class Segmentation

Pure-Python helpers for zone/class grouping.
No valuation logic, no file I/O, no Flask imports.

Public API:
    extract_zone_fields(row: dict) -> dict
    build_zone_summary(per_row_results: list) -> dict
    build_property_class_summary(per_row_results: list) -> dict
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

_ZONE_FIELD_NAMES = ("zone_id", "neighborhood", "submarket", "property_class")

# Known property_class values — used only for lowercase normalisation of
# ASCII/English class names.  Arabic strings are preserved as-is.
_ASCII_CLASSES = frozenset({
    "residential", "commercial", "industrial", "agricultural", "administrative",
    "mixed", "hospitality", "retail", "office", "land",
})


def extract_zone_fields(row: dict) -> Dict[str, Optional[str]]:
    """Extract and lightly normalise zone/classification fields from a row dict.

    Rules:
    - All fields are optional.  Missing or blank values default to None.
    - zone_id, neighborhood, submarket: strip whitespace only.
    - property_class: strip + lowercase for ASCII-only values;
      Arabic strings are preserved verbatim (do not lowercase Arabic).
    - Does NOT mutate the input dict.
    """
    def _clean(val: Any) -> Optional[str]:
        if val is None:
            return None
        s = str(val).strip()
        return s if s else None

    zone_id      = _clean(row.get("zone_id"))
    neighborhood = _clean(row.get("neighborhood"))
    submarket    = _clean(row.get("submarket"))

    raw_pc = row.get("property_class")
    if raw_pc is None:
        property_class: Optional[str] = None
    else:
        pc = str(raw_pc).strip()
        if not pc:
            property_class = None
        elif pc.lower() in _ASCII_CLASSES:
            property_class = pc.lower()
        else:
            property_class = pc  # preserve Arabic or unknown strings as-is

    return {
        "zone_id":        zone_id,
        "neighborhood":   neighborhood,
        "submarket":      submarket,
        "property_class": property_class,
    }


def build_zone_summary(per_row_results: List[dict]) -> Dict[str, Any]:
    """Return zone_summary dict keyed by zone_id.

    Counts all rows per zone.  Numeric metrics (market_value, area) are
    accumulated from successful rows only.

    Rows without zone_id do NOT appear in the summary (they are simply
    skipped).  This keeps the summary clean for batches that mix zoned
    and unzoned rows.
    """
    agg: Dict[str, Dict[str, Any]] = {}

    for rr in per_row_results:
        zone = rr.get("zone_id")
        if not zone:
            continue
        if zone not in agg:
            agg[zone] = {
                "row_count":           0,
                "successful_rows":     0,
                "failed_rows":         0,
                "skipped_rows":        0,
                "_total_market_value": 0.0,
                "_total_area":         0.0,
                # Carry first neighborhood/submarket seen for this zone
                "neighborhood":        None,
                "submarket":           None,
            }
        bucket = agg[zone]
        bucket["row_count"] += 1

        # Carry through the first non-null neighborhood / submarket we see
        if bucket["neighborhood"] is None and rr.get("neighborhood"):
            bucket["neighborhood"] = rr["neighborhood"]
        if bucket["submarket"] is None and rr.get("submarket"):
            bucket["submarket"] = rr["submarket"]

        status = rr.get("status", "")
        if status == "success":
            bucket["successful_rows"] += 1
            mv = rr.get("market_value")
            if isinstance(mv, (int, float)):
                bucket["_total_market_value"] += mv
            area = rr.get("area")
            if isinstance(area, (int, float)) and area > 0:
                bucket["_total_area"] += area
        elif status == "error":
            bucket["failed_rows"] += 1
        elif status == "skipped":
            bucket["skipped_rows"] += 1

    # Compute derived fields; drop internal accumulators
    result: Dict[str, Any] = {}
    for zone, b in sorted(agg.items()):
        total_mv   = round(b["_total_market_value"], 2)
        total_area = round(b["_total_area"], 2)
        n_ok       = b["successful_rows"]
        avg_mv     = round(total_mv / n_ok,        2) if n_ok        > 0 else 0.0
        avg_vpm2   = round(total_mv / total_area,  2) if total_area  > 0 else 0.0
        result[zone] = {
            "neighborhood":         b["neighborhood"],
            "submarket":            b["submarket"],
            "row_count":            b["row_count"],
            "successful_rows":      n_ok,
            "failed_rows":          b["failed_rows"],
            "skipped_rows":         b["skipped_rows"],
            "total_market_value":   total_mv,
            "average_market_value": avg_mv,
            "total_area":           total_area,
            "average_value_per_m2": avg_vpm2,
        }
    return result


def build_property_class_summary(per_row_results: List[dict]) -> Dict[str, Any]:
    """Return property_class_summary dict keyed by property_class.

    Rows without property_class do NOT appear in the summary (same rationale
    as build_zone_summary — keeps output clean for mixed batches).
    """
    agg: Dict[str, Dict[str, Any]] = {}

    for rr in per_row_results:
        pc = rr.get("property_class")
        if not pc:
            continue
        if pc not in agg:
            agg[pc] = {
                "row_count":           0,
                "successful_rows":     0,
                "failed_rows":         0,
                "skipped_rows":        0,
                "_total_market_value": 0.0,
                "_total_area":         0.0,
            }
        bucket = agg[pc]
        bucket["row_count"] += 1
        status = rr.get("status", "")
        if status == "success":
            bucket["successful_rows"] += 1
            mv = rr.get("market_value")
            if isinstance(mv, (int, float)):
                bucket["_total_market_value"] += mv
            area = rr.get("area")
            if isinstance(area, (int, float)) and area > 0:
                bucket["_total_area"] += area
        elif status == "error":
            bucket["failed_rows"] += 1
        elif status == "skipped":
            bucket["skipped_rows"] += 1

    result: Dict[str, Any] = {}
    for pc, b in sorted(agg.items()):
        total_mv   = round(b["_total_market_value"], 2)
        total_area = round(b["_total_area"], 2)
        n_ok       = b["successful_rows"]
        avg_mv     = round(total_mv / n_ok,       2) if n_ok       > 0 else 0.0
        avg_vpm2   = round(total_mv / total_area, 2) if total_area > 0 else 0.0
        result[pc] = {
            "row_count":            b["row_count"],
            "successful_rows":      n_ok,
            "failed_rows":          b["failed_rows"],
            "skipped_rows":         b["skipped_rows"],
            "total_market_value":   total_mv,
            "average_market_value": avg_mv,
            "total_area":           total_area,
            "average_value_per_m2": avg_vpm2,
        }
    return result


__all__ = [
    "extract_zone_fields",
    "build_zone_summary",
    "build_property_class_summary",
]
