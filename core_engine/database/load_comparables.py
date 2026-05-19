#!/usr/bin/env python3
"""
load_comparables.py — Seed the comparables table from market_feed.json.

Flags:
  --dry-run   Validate records; no database writes.
  --limit N   Process only the first N records.
  --reset     Delete all existing rows before inserting (live mode only).

Usage (from repo root):
  python core_engine/database/load_comparables.py --dry-run
  python core_engine/database/load_comparables.py --dry-run --limit 10
  python core_engine/database/load_comparables.py --limit 100
  python core_engine/database/load_comparables.py
  python core_engine/database/load_comparables.py --reset
"""
import argparse
import json
import sys
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from pathlib import Path

# Put core_engine/ on sys.path so "database.*" imports resolve regardless of cwd.
_ROOT = Path(__file__).resolve().parents[1]   # core_engine/
sys.path.insert(0, str(_ROOT))

from database.connection import get_session_factory, init_db
from database.models import Comparable

_MARKET_FEED  = _ROOT / "data" / "market_feed.json"
_CURRENT_YEAR = datetime.now().year
_BATCH_COMMIT = 200   # commit every N inserts to bound memory usage


# ── Field mapping helpers ────────────────────────────────────────

def _parse_date(ts: str) -> date | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts).date()
    except (ValueError, TypeError):
        return None


def _parse_governorate(location: str) -> str | None:
    """
    Extract the first segment of 'City - District' strings.
    Returns None for garbled (question-mark) strings.
    """
    if not location or "?" in location:
        return None
    gov = location.split(" - ", 1)[0].strip()
    return gov or None


def _to_decimal(val, *, clamp_max: Decimal | None = None) -> Decimal | None:
    if val is None:
        return None
    try:
        d = Decimal(str(val))
        if clamp_max is not None:
            d = min(d, clamp_max)
        return d
    except InvalidOperation:
        return None


def map_record(raw: dict) -> dict | None:
    """
    Map one market_feed entry to Comparable constructor kwargs.
    Returns None if the record is invalid and must be skipped.
    """
    area  = _to_decimal(raw.get("area"))
    price = _to_decimal(raw.get("price"))

    # Mandatory: positive area and price
    if area is None or area <= 0 or price is None or price <= 0:
        return None

    prop_type = (raw.get("property_type") or "").strip()
    if not prop_type:
        return None

    location  = (raw.get("location") or "").strip()
    source    = (raw.get("source")   or "").strip() or None
    notes     = (raw.get("notes")    or "").strip()
    timestamp = raw.get("timestamp") or ""

    # Age in years derived from year_built
    age_years: int | None = None
    yb = raw.get("year_built")
    if yb:
        try:
            yb_int = int(float(yb))
            if 1900 < yb_int <= _CURRENT_YEAR:
                age_years = max(0, _CURRENT_YEAR - yb_int)
        except (TypeError, ValueError):
            pass

    # Location description: prefer location string; fall back to notes
    # when location is absent (garbled strings are kept as-is).
    loc_desc: str | None = location or (notes if notes else None)

    # Lat/lng not present in this feed, but map them if ever added
    lat = _to_decimal(raw.get("lat") or raw.get("latitude"))
    lng = _to_decimal(raw.get("lng") or raw.get("longitude"))

    return {
        "property_type":       prop_type[:50],
        "area_sqm":            area,
        "price_egp":           price,
        "price_per_sqm":       _to_decimal(raw.get("price_per_meter")),
        "source":              source[:100] if source else None,
        "location_description": loc_desc,
        "governorate":         _parse_governorate(location),
        "listed_date":         _parse_date(timestamp),
        "age_years":           age_years,
        "data_quality_score":  _to_decimal(raw.get("credibility"),
                                           clamp_max=Decimal("1.00")),
        "latitude":            lat,
        "longitude":           lng,
    }


# ── Idempotency ──────────────────────────────────────────────────

def _exists(session, kw: dict) -> bool:
    """
    Return True if a row with the same composite fingerprint already exists:
    (price_egp, area_sqm, source, listed_date).
    NULL is matched explicitly so SQL NULL != NULL doesn't cause false misses.
    """
    source      = kw.get("source")
    listed_date = kw.get("listed_date")

    q = session.query(Comparable).filter(
        Comparable.price_egp == kw["price_egp"],
        Comparable.area_sqm  == kw["area_sqm"],
    )
    q = (q.filter(Comparable.source == source)
         if source is not None
         else q.filter(Comparable.source.is_(None)))
    q = (q.filter(Comparable.listed_date == listed_date)
         if listed_date is not None
         else q.filter(Comparable.listed_date.is_(None)))

    return session.query(q.exists()).scalar()


# ── Main loader ──────────────────────────────────────────────────

def load(
    *,
    dry_run: bool = False,
    limit:   int | None = None,
    reset:   bool = False,
) -> dict:
    """
    Load comparables from market_feed.json.
    Returns a summary dict; raises on file-not-found or malformed JSON.
    """
    raw_records: list[dict] = json.loads(
        _MARKET_FEED.read_text(encoding="utf-8")
    )
    if not isinstance(raw_records, list):
        raise ValueError("market_feed.json must be a flat JSON array at the root.")

    if limit is not None:
        raw_records = raw_records[:limit]

    total_read       = len(raw_records)
    inserted         = 0
    skipped_existing = 0
    skipped_invalid  = 0
    errors           = 0

    # ── Dry run: no DB connection needed ────────────────────────
    if dry_run:
        for raw in raw_records:
            if map_record(raw) is None:
                skipped_invalid += 1
            else:
                inserted += 1   # "would insert" (duplicates not checked)
        return {
            "dry_run":         True,
            "read":            total_read,
            "would_insert":    inserted,
            "skipped_invalid": skipped_invalid,
        }

    # ── Live run ─────────────────────────────────────────────────
    init_db()   # CREATE TABLE IF NOT EXISTS (idempotent)
    session = get_session_factory()()
    try:
        if reset:
            session.query(Comparable).delete()
            session.commit()
            print("  [RESET] All existing comparables deleted.")

        pending = 0
        for raw in raw_records:
            try:
                kw = map_record(raw)
                if kw is None:
                    skipped_invalid += 1
                    continue

                if _exists(session, kw):
                    skipped_existing += 1
                    continue

                with session.begin_nested():   # savepoint — isolates per-record errors
                    session.add(Comparable(**kw))

                inserted += 1
                pending  += 1

                if pending >= _BATCH_COMMIT:
                    session.commit()
                    pending = 0

            except Exception as exc:
                errors += 1
                print(
                    f"  [ERROR] id={raw.get('id', '?')} — {exc}",
                    file=sys.stderr,
                )

        session.commit()   # flush the final partial batch

    finally:
        session.close()

    return {
        "dry_run":          False,
        "read":             total_read,
        "inserted":         inserted,
        "skipped_existing": skipped_existing,
        "skipped_invalid":  skipped_invalid,
        "errors":           errors,
    }


# ── CLI ──────────────────────────────────────────────────────────

def _print_banner(args: argparse.Namespace) -> None:
    print()
    print("=" * 60)
    print("  Expert_Smart — Load Comparables")
    print(f"  Source : {_MARKET_FEED}")
    print(f"  Mode   : {'DRY RUN (no writes)' if args.dry_run else 'LIVE'}")
    if args.limit:
        print(f"  Limit  : first {args.limit} records")
    if args.reset and not args.dry_run:
        print("  Reset  : YES — existing rows will be deleted first")
    print("=" * 60)


def _print_summary(summary: dict) -> None:
    print()
    print("  SUMMARY")
    print(f"  Records read         : {summary['read']}")
    if summary["dry_run"]:
        print(f"  Would insert         : {summary['would_insert']}")
        print(f"    (duplicates not checked in dry-run mode)")
        print(f"  Skipped (invalid)    : {summary['skipped_invalid']}")
    else:
        print(f"  Inserted             : {summary['inserted']}")
        print(f"  Skipped (duplicate)  : {summary['skipped_existing']}")
        print(f"  Skipped (invalid)    : {summary['skipped_invalid']}")
        print(f"  Errors               : {summary['errors']}")
    print()
    print("=" * 60)
    if summary["dry_run"]:
        print("  Dry run complete — no data written.")
    else:
        print("  Done.")
    print("=" * 60)
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Load market_feed.json comparables into PostgreSQL. "
            "Idempotent: repeated runs skip existing rows."
        )
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate and count records without touching the database.",
    )
    parser.add_argument(
        "--limit", type=int, default=None, metavar="N",
        help="Process only the first N records.",
    )
    parser.add_argument(
        "--reset", action="store_true",
        help=(
            "Delete all existing comparables before inserting "
            "(live mode only; ignored in --dry-run)."
        ),
    )
    args = parser.parse_args()

    _print_banner(args)
    summary = load(dry_run=args.dry_run, limit=args.limit, reset=args.reset)
    _print_summary(summary)


if __name__ == "__main__":
    main()
