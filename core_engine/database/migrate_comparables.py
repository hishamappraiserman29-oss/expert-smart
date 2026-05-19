#!/usr/bin/env python3
"""
migrate_comparables.py — Phase 8.1: Load JSON comparables → PostgreSQL.

Handles both market_feed.json field names (area, price, timestamp, credibility,
year_built) and the canonical spec format (area_sqm, price_egp, listed_date,
age_years, data_quality_score) so the same script works for the live feed and
for unit-test mock data.

CLI:
  python core_engine/database/migrate_comparables.py
"""
import json
import os
import sys
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path

# Put core_engine/ on sys.path so sibling packages resolve.
_ROOT = Path(__file__).resolve().parents[1]   # …/core_engine/
sys.path.insert(0, str(_ROOT))

from database.models import Comparable, Base                         # noqa: E402
from database.connection import get_engine, SessionLocal, init_db, drop_db  # noqa: E402
from sqlalchemy import func                                          # noqa: E402

# Alias for spec compatibility: `engine` referenced in the module spec.
engine = get_engine

_CURRENT_YEAR = datetime.now().year


# ── Field extraction (handles both field-name conventions) ───────

def _parse_date(val) -> date | None:
    """Parse an ISO date/datetime string or return None."""
    if val is None:
        return None
    if isinstance(val, date):
        return val
    try:
        return datetime.fromisoformat(str(val)).date()
    except (ValueError, TypeError):
        return None


def _extract_governorate(location: str) -> str | None:
    """
    Extract the leading city name from 'City - District' strings.
    Returns None for garbled (question-mark) strings.
    """
    if not location or "?" in location:
        return None
    gov = location.split(" - ", 1)[0].strip()
    return gov or None


def _extract_fields(record: dict) -> dict:
    """
    Normalise a raw JSON record to a flat dict with canonical field names.
    Handles both market_feed.json names and spec test-data names.
    """
    # ── Numeric core ────────────────────────────────────────────
    raw_area  = record.get("area_sqm") or record.get("area")
    raw_price = record.get("price_egp") or record.get("price")

    area_sqm  = float(raw_area)  if raw_area  is not None else 0.0
    price_egp = float(raw_price) if raw_price is not None else 0.0

    # ── Location ─────────────────────────────────────────────────
    location = (record.get("location") or "").strip()
    governorate = record.get("governorate") or _extract_governorate(location)

    # ── Age ──────────────────────────────────────────────────────
    age_years: int | None = record.get("age_years")
    if age_years is None:
        yb = record.get("year_built")
        if yb:
            try:
                yb_int = int(float(yb))
                if 1900 < yb_int <= _CURRENT_YEAR:
                    age_years = max(0, _CURRENT_YEAR - yb_int)
            except (TypeError, ValueError):
                pass

    # ── Date ─────────────────────────────────────────────────────
    listed_date = _parse_date(
        record.get("listed_date") or record.get("timestamp")
    )

    # ── Price per sqm ─────────────────────────────────────────────
    price_per_sqm = record.get("price_per_sqm") or record.get("price_per_meter")
    if price_per_sqm is None and area_sqm > 0 and price_egp > 0:
        price_per_sqm = price_egp / area_sqm

    # ── Data quality score ────────────────────────────────────────
    # Prefer explicit credibility/data_quality_score; fall back to completeness.
    dq_score = record.get("data_quality_score") or record.get("credibility")
    if dq_score is None:
        present = [
            record.get("property_type") or record.get("property_type"),
            area_sqm,
            price_egp,
            age_years,
            governorate,
            record.get("latitude") or record.get("lat"),
            record.get("longitude") or record.get("lng"),
        ]
        dq_score = sum(1 for v in present if v) / 7.0

    # ── Coordinates ──────────────────────────────────────────────
    lat = record.get("latitude") or record.get("lat")
    lng = record.get("longitude") or record.get("lng")

    return {
        "area_sqm":            area_sqm,
        "price_egp":           price_egp,
        "governorate":         governorate,
        "location":            location or None,
        "age_years":           age_years,
        "listed_date":         listed_date,
        "price_per_sqm":       float(price_per_sqm) if price_per_sqm else None,
        "data_quality_score":  min(float(dq_score), 1.0) if dq_score is not None else None,
        "latitude":            float(lat) if lat is not None else None,
        "longitude":           float(lng) if lng is not None else None,
    }


# ── Main loader ──────────────────────────────────────────────────

def load_comparables_from_json(
    json_file_path: str,
    batch_size: int = 100,
) -> dict:
    """
    Load comparables from a JSON file and insert them into PostgreSQL.

    Accepts both a flat array and ``{"comparables": [...]}`` wrapper.

    Returns a stats dict: loaded, skipped, errors, duplicates, total,
    start_time, end_time, duration_seconds.
    """
    stats = {
        "loaded":            0,
        "skipped":           0,
        "errors":            0,
        "duplicates":        0,
        "total":             0,
        "start_time":        datetime.now(),
        "end_time":          None,
        "duration_seconds":  0,
    }

    # ── Read JSON ────────────────────────────────────────────────
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        comparables_list = data.get("comparables", [])
    else:
        comparables_list = data

    stats["total"] = len(comparables_list)

    # ── Session + state ──────────────────────────────────────────
    session = SessionLocal()
    batch: list[Comparable] = []
    seen_hashes: set[str] = set()   # in-run duplicate guard

    try:
        for idx, record in enumerate(comparables_list):
            try:
                # ── Mandatory fields ─────────────────────────────
                property_type = (
                    record.get("property_type") or "unknown"
                ).strip()[:50]

                fields = _extract_fields(record)
                area_sqm  = fields["area_sqm"]
                price_egp = fields["price_egp"]

                if area_sqm <= 0 or price_egp <= 0:
                    stats["skipped"] += 1
                    continue

                # ── Optional fields ──────────────────────────────
                age_years          = fields["age_years"]
                finishing_level    = record.get("finishing_level")
                quality_tier       = record.get("quality_tier")
                latitude           = fields["latitude"]
                longitude          = fields["longitude"]
                governorate        = fields["governorate"]
                location_desc      = fields["location"]
                price_per_sqm      = fields["price_per_sqm"]
                source             = (record.get("source") or "market_feed")[:100]
                listed_date        = fields["listed_date"]
                data_quality_score = fields["data_quality_score"]

                # ── Duplicate detection (in-run) ──────────────────
                dup_hash = f"{governorate}_{area_sqm}_{price_egp}"
                if dup_hash in seen_hashes:
                    stats["duplicates"] += 1
                    continue
                seen_hashes.add(dup_hash)

                # ── Build model ───────────────────────────────────
                comparable = Comparable(
                    property_type=property_type,
                    area_sqm=area_sqm,
                    age_years=age_years,
                    finishing_level=finishing_level,
                    quality_tier=quality_tier,
                    latitude=latitude,
                    longitude=longitude,
                    governorate=governorate,
                    location_description=location_desc,
                    price_egp=price_egp,
                    price_per_sqm=price_per_sqm,
                    source=source,
                    listed_date=listed_date,
                    data_quality_score=data_quality_score,
                )
                batch.append(comparable)
                stats["loaded"] += 1

                # ── Commit batch ──────────────────────────────────
                if len(batch) >= batch_size:
                    session.add_all(batch)
                    session.commit()
                    print(f"  Inserted batch at record {idx + 1}/{stats['total']}")
                    batch = []

            except Exception as exc:
                stats["errors"] += 1
                print(f"  Error at record {idx + 1}: {exc}", file=sys.stderr)

        # ── Final batch ──────────────────────────────────────────
        if batch:
            session.add_all(batch)
            session.commit()
            print(f"  Inserted final batch ({len(batch)} records)")

        stats["end_time"] = datetime.now()
        stats["duration_seconds"] = (
            stats["end_time"] - stats["start_time"]
        ).total_seconds()
        return stats

    except Exception as exc:
        print(f"Fatal error: {exc}", file=sys.stderr)
        session.rollback()
        raise

    finally:
        session.close()


# ── Validation ───────────────────────────────────────────────────

def validate_loaded_data(session, expected_count: int = 1731) -> dict:
    """
    Validate that comparables were loaded correctly.

    Queries count, type/governorate distributions, and price/area stats.
    Returns a dict with an ``issues`` list (empty = clean).
    """
    results: dict = {
        "total_count":      0,
        "by_property_type": {},
        "by_governorate":   {},
        "price_stats":      {},
        "area_stats":       {},
        "issues":           [],
    }

    # Total count
    results["total_count"] = session.query(
        func.count(Comparable.id)
    ).scalar()

    # Distribution by property type
    type_counts = session.query(
        Comparable.property_type,
        func.count(Comparable.id),
    ).group_by(Comparable.property_type).all()
    results["by_property_type"] = dict(type_counts)

    # Distribution by governorate
    gov_counts = session.query(
        Comparable.governorate,
        func.count(Comparable.id),
    ).group_by(Comparable.governorate).all()
    results["by_governorate"] = dict(gov_counts)

    # Price statistics (PostgreSQL-specific stddev)
    price_row = session.query(
        func.min(Comparable.price_egp),
        func.max(Comparable.price_egp),
        func.avg(Comparable.price_egp),
        func.stddev(Comparable.price_egp),
    ).first()
    results["price_stats"] = {
        "min":    price_row[0],
        "max":    price_row[1],
        "avg":    price_row[2],
        "stddev": price_row[3],
    }

    # Area statistics
    area_row = session.query(
        func.min(Comparable.area_sqm),
        func.max(Comparable.area_sqm),
        func.avg(Comparable.area_sqm),
    ).first()
    results["area_stats"] = {
        "min": area_row[0],
        "max": area_row[1],
        "avg": area_row[2],
    }

    # Validation checks
    if results["total_count"] != expected_count:
        results["issues"].append(
            f"Expected {expected_count}, got {results['total_count']}"
        )

    if not results["by_governorate"]:
        results["issues"].append("No governorate data loaded")

    min_price = results["price_stats"].get("min")
    if min_price is not None and float(min_price) <= 0:
        results["issues"].append("Invalid price data (<=0)")

    return results


# ── CLI entry point ──────────────────────────────────────────────

def main() -> None:
    """Three-step migration: init DB → load JSON → validate."""
    import sys

    print("=" * 70)
    print("Phase 8.1: Load JSON Comparables → PostgreSQL")
    print("=" * 70)

    # ── Step 1: Init schema ──────────────────────────────────────
    print("\n[1/3] Initializing database schema...")
    try:
        init_db()
        print("  ✓ Database initialized")
    except Exception as exc:
        print(f"  ✗ Error: {exc}")
        sys.exit(1)

    # ── Step 2: Load JSON ────────────────────────────────────────
    json_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "data", "market_feed.json")
    )
    if not os.path.exists(json_path):
        print(f"  ✗ JSON file not found: {json_path}")
        sys.exit(1)

    print(f"\n[2/3] Loading comparables from {json_path}...")
    try:
        stats = load_comparables_from_json(json_path, batch_size=100)
        print("  ✓ Loading complete")
        print(f"    - Total in file : {stats['total']}")
        print(f"    - Loaded        : {stats['loaded']}")
        print(f"    - Duplicates    : {stats['duplicates']}")
        print(f"    - Skipped       : {stats['skipped']}")
        print(f"    - Errors        : {stats['errors']}")
        print(f"    - Duration      : {stats['duration_seconds']:.2f}s")
    except Exception as exc:
        print(f"  ✗ Error: {exc}")
        sys.exit(1)

    # ── Step 3: Validate ─────────────────────────────────────────
    print("\n[3/3] Validating loaded data...")
    try:
        session = SessionLocal()
        validation = validate_loaded_data(session, expected_count=stats["loaded"])

        print("  ✓ Validation complete")
        print(f"    - Total records   : {validation['total_count']}")
        print(f"    - Property types  : {len(validation['by_property_type'])}")
        print(f"      {validation['by_property_type']}")
        print(f"    - Governorates    : {len(validation['by_governorate'])}")
        print(f"      {validation['by_governorate']}")

        ps = validation["price_stats"]
        as_ = validation["area_stats"]
        print(f"    - Price range     : {ps['min']} – {ps['max']} EGP")
        print(f"    - Area range      : {as_['min']} – {as_['max']} sqm")

        if validation["issues"]:
            print(f"    - Issues: {validation['issues']}")
        else:
            print("    - No validation issues ✓")

        session.close()
    except Exception as exc:
        print(f"  ✗ Error: {exc}")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("Migration complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
