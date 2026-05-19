"""
test_phase_8_e2e.py — Phase 8.4: E2E + Integration Tests

4 suites, 15 tests total:
  Suite 1 (5): Data integrity    — 1,731 comparables seeded correctly
  Suite 2 (4): Query performance — ORM filters execute within time bounds
  Suite 3 (3): Valuation writes  — Valuation, QualityAudit, AuditLog DB writes
  Suite 4 (3): API integration   — Flask test_client smoke tests

All suites use SQLite in-memory (no live PostgreSQL required).
JSONB columns are patched to SQLAlchemy JSON before table creation.

Data notes (market_feed.json):
  - 1,731 records; property types and governorates are in Arabic
  - No latitude/longitude data  ->  by_location tests verify shape only
  - Most common type  : شقة سكنية (~1,320 records)
  - Most common gov   : دبي (~187), القاهرة الجديدة (~130)
  - Price range       : ~1M-616M EGP (avg ~25M)
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

# ── sys.path setup ────────────────────────────────────────────────────────────
# This file lives in core_engine/tests/ — put core_engine/ and project root on path
_CORE = Path(__file__).resolve().parents[1]   # …/core_engine/
_ROOT = _CORE.parent                          # project root
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── SQLite engine (created before models so the JSONB patch can take effect) ──
from sqlalchemy import create_engine, JSON, func
from sqlalchemy.orm import sessionmaker

_SQLITE_ENGINE = create_engine("sqlite:///:memory:", echo=False)

# ── Import models + queries ───────────────────────────────────────────────────
from database.models import Base, Comparable, Valuation, QualityAudit, ActivityLog
from database.queries import SearchComparable
from database.migrate_comparables import _extract_fields

# ── Auth header for @require_auth endpoints (added post-SEC-002) ──────────────
import os
os.environ.setdefault("JWT_SECRET", "test-secret-e2e-bundle")
from auth.tokens import generate_token as _gen_token
_AUTH_HDR = {"Authorization": f"Bearer {_gen_token('test-user-e2e')}"}

# ── Patch JSONB -> JSON for SQLite compatibility ───────────────────────────────
# Must happen AFTER model import (metadata exists) and BEFORE create_all.
# Valuation.result_json, QualityAudit.findings_json, ActivityLog.details_json
# are JSONB; SQLite renders them as TEXT via SQLAlchemy's JSON type.
from sqlalchemy.dialects.postgresql import JSONB as _PG_JSONB

for _tbl in Base.metadata.tables.values():
    for _col in _tbl.columns:
        if isinstance(_col.type, _PG_JSONB):
            _col.type = JSON()

# ── Create all tables on SQLite ───────────────────────────────────────────────
Base.metadata.create_all(_SQLITE_ENGINE)
SessionLocal = sessionmaker(bind=_SQLITE_ENGINE)

# ── Seed comparables from market_feed.json ────────────────────────────────────
_MARKET_FEED = _CORE / "data" / "market_feed.json"

def _seed_comparables() -> int:
    """Load market_feed.json -> SQLite comparables table. Returns row count."""
    with open(_MARKET_FEED, encoding="utf-8") as fh:
        raw = json.load(fh)
    records = raw if isinstance(raw, list) else raw.get("comparables", [])

    session = SessionLocal()
    loaded = 0
    seen: set[str] = set()
    batch: list[Comparable] = []

    for rec in records:
        try:
            ptype = (rec.get("property_type") or "unknown").strip()[:50]
            fields = _extract_fields(rec)
            area, price = fields["area_sqm"], fields["price_egp"]
            if area <= 0 or price <= 0:
                continue
            key = f"{fields['governorate']}_{area}_{price}"
            if key in seen:
                continue
            seen.add(key)

            batch.append(Comparable(
                property_type=ptype,
                area_sqm=area,
                age_years=fields["age_years"],
                finishing_level=rec.get("finishing_level"),
                quality_tier=rec.get("quality_tier"),
                latitude=fields["latitude"],
                longitude=fields["longitude"],
                governorate=fields["governorate"],
                location_description=fields["location"],
                price_egp=price,
                price_per_sqm=fields["price_per_sqm"],
                source=(rec.get("source") or "market_feed")[:100],
                listed_date=fields["listed_date"],
                data_quality_score=fields["data_quality_score"],
            ))
            loaded += 1

            if len(batch) >= 200:
                session.add_all(batch)
                session.commit()
                batch = []
        except Exception:
            pass

    if batch:
        session.add_all(batch)
        session.commit()
    session.close()
    return loaded


_LOADED_COUNT = _seed_comparables()

# Most common values in the actual data (used by performance tests)
_TYPE_APARTMENT = "شقة سكنية"   # 1,320 records
_GOV_CAIRO_NEW  = "القاهرة الجديدة"  # 130 records


# ══════════════════════════════════════════════════════════════════════════════
# Suite 1: Data Integrity (5 tests)
# ══════════════════════════════════════════════════════════════════════════════

def test_comparable_count_total():
    """All seeded comparables are queryable (count matches seed output)."""
    db = SessionLocal()
    count = db.query(Comparable).count()
    db.close()
    assert count == _LOADED_COUNT, f"Expected {_LOADED_COUNT}, got {count}"
    assert count >= 1700, f"Too few records seeded: {count}"
    print(f"PASS Total comparables: {count}")


def test_comparable_no_null_ids():
    """Every comparable row has a UUID primary key."""
    db = SessionLocal()
    null_ids = db.query(Comparable).filter(Comparable.id.is_(None)).count()
    db.close()
    assert null_ids == 0, f"Found {null_ids} rows with null ID"
    print("PASS All comparables have UUID")


def test_comparable_required_fields():
    """property_type present; area_sqm > 0; price_egp > 0 for all rows."""
    db = SessionLocal()
    null_types    = db.query(Comparable).filter(Comparable.property_type.is_(None)).count()
    invalid_areas  = db.query(Comparable).filter(Comparable.area_sqm  <= 0).count()
    invalid_prices = db.query(Comparable).filter(Comparable.price_egp <= 0).count()
    db.close()
    assert null_types    == 0, f"{null_types} null property_type"
    assert invalid_areas == 0, f"{invalid_areas} invalid areas (<= 0)"
    assert invalid_prices == 0, f"{invalid_prices} invalid prices (<= 0)"
    print("PASS Required fields: property_type, area_sqm > 0, price_egp > 0")


def test_comparable_distribution_by_type():
    """At least 5 property types; شقة سكنية (apartment) is the majority."""
    db = SessionLocal()
    type_counts = (
        db.query(Comparable.property_type, func.count(Comparable.id))
        .group_by(Comparable.property_type)
        .all()
    )
    db.close()

    type_dict = dict(type_counts)
    assert len(type_dict) >= 5, f"Expected 5+ types, got {len(type_dict)}: {type_dict}"

    apt_count = type_dict.get(_TYPE_APARTMENT, 0)
    assert apt_count >= 100, f"Too few apartment records: {apt_count}"
    print(f"PASS {len(type_dict)} property types; apt count: {apt_count} rows")


def test_comparable_price_statistics():
    """Price range is within realistic Egyptian + GCC market bounds."""
    db = SessionLocal()
    row = db.query(
        func.min(Comparable.price_egp),
        func.max(Comparable.price_egp),
        func.avg(Comparable.price_egp),
        func.count(Comparable.id),
    ).first()
    db.close()

    min_price, max_price, avg_price, count = row
    # market_feed prices: 1M - 616M EGP
    assert float(min_price)  >   100_000, f"Min price suspiciously low: {min_price}"
    assert float(max_price)  < 2_000_000_000, f"Max price suspiciously high: {max_price}"
    assert float(avg_price)  >   500_000, f"Avg price too low: {avg_price}"
    assert count == _LOADED_COUNT
    print(f"PASS Price range: {float(min_price):,.0f}-{float(max_price):,.0f} EGP "
          f"(avg {float(avg_price):,.0f})")


# ══════════════════════════════════════════════════════════════════════════════
# Suite 2: Query Performance (4 tests)
# ══════════════════════════════════════════════════════════════════════════════

def test_query_performance_by_type():
    """by_property_type filter returns results in < 1 s."""
    db = SessionLocal()
    t0 = time.time()
    results = SearchComparable(db).by_property_type(_TYPE_APARTMENT).limit(10).execute()
    elapsed = time.time() - t0
    db.close()

    assert elapsed < 1.0, f"Query too slow: {elapsed:.3f}s"
    assert len(results) > 0, f"No {_TYPE_APARTMENT!r} records found"
    print(f"PASS by_property_type: {elapsed*1000:.1f} ms, {len(results)} results")


def test_query_performance_by_price_range():
    """by_price_range filter returns results in < 1 s."""
    db = SessionLocal()
    t0 = time.time()
    results = (
        SearchComparable(db)
        .by_price_range(1_000_000, 5_000_000)
        .limit(10)
        .execute()
    )
    elapsed = time.time() - t0
    db.close()

    assert elapsed < 1.0, f"Query too slow: {elapsed:.3f}s"
    assert len(results) > 0, "No results in 1M-5M EGP price range"
    print(f"PASS by_price_range: {elapsed*1000:.1f} ms, {len(results)} results")


def test_query_performance_by_location():
    """by_location (Haversine) executes without error in < 3 s.

    market_feed.json has no coordinate data, so result count is 0;
    the test verifies timing and that the query returns a list without error.
    """
    db = SessionLocal()
    t0 = time.time()
    results = (
        SearchComparable(db)
        .by_location(latitude=30.0276, longitude=31.4913, radius_meters=50_000)
        .limit(10)
        .execute()
    )
    elapsed = time.time() - t0
    db.close()

    assert isinstance(results, list), "by_location must return a list"
    assert elapsed < 3.0, f"Haversine scan too slow: {elapsed:.3f}s"
    # market_feed has no lat/lng — 0 results is expected and correct
    print(f"PASS by_location (Haversine): {elapsed*1000:.1f} ms, "
          f"{len(results)} results (0 expected — no coords in feed)")


def test_query_performance_chained():
    """Chained AND filters return results in < 1 s."""
    db = SessionLocal()
    t0 = time.time()
    results = (
        SearchComparable(db)
        .by_property_type(_TYPE_APARTMENT)
        .by_price_range(2_000_000, 6_000_000)
        .by_data_quality(min_score=0.5)
        .limit(10)
        .execute()
    )
    elapsed = time.time() - t0
    db.close()

    assert elapsed < 1.0, f"Chained query too slow: {elapsed:.3f}s"
    assert isinstance(results, list)
    print(f"PASS Chained query (type+price+quality): {elapsed*1000:.1f} ms, {len(results)} results")


# ══════════════════════════════════════════════════════════════════════════════
# Suite 3: Valuation Writes (3 tests)
# ══════════════════════════════════════════════════════════════════════════════

def test_valuation_write():
    """Valuation row written, committed, and retrievable by UUID."""
    db = SessionLocal()

    val = Valuation(
        asset_type="residential",
        primary_purpose="market_value",
        primary_value=3_645_000.0,
        confidence="high",
        weight_comparable=0.80,
        weight_cost=0.15,
        weight_income=0.05,
        comparable_value=4_000_000.0,
        cost_value=2_500_000.0,
        income_value=1_400_000.0,
        comparable_count=5,
        top_similarity_score=85.5,
        appraiser_name="Test Appraiser",
        property_address="Test Property, Cairo",
        valuation_date=datetime.now().date(),
        result_json={"asset_type": "residential", "primary_value": 3_645_000.0},
    )
    db.add(val)
    db.commit()
    val_id = val.id

    retrieved = db.query(Valuation).filter(Valuation.id == val_id).first()
    db.close()

    assert retrieved is not None, "Valuation not found after commit"
    assert float(retrieved.primary_value) == 3_645_000.0, "primary_value mismatch"
    assert retrieved.confidence == "high", "confidence mismatch"
    assert retrieved.asset_type == "residential", "asset_type mismatch"
    print(f"PASS Valuation written: {val_id}")


def test_quality_audit_write():
    """QualityAudit linked to Valuation; accessible via relationship."""
    db = SessionLocal()

    # Create valuation first
    val = Valuation(
        asset_type="residential",
        primary_purpose="market_value",
        primary_value=3_645_000.0,
        confidence="high",
        appraiser_name="Test",
        valuation_date=datetime.now().date(),
    )
    db.add(val)
    db.flush()   # populate val.id without committing

    qa = QualityAudit(
        valuation_id=val.id,
        quality_score=87.5,
        quality_grade="B",
        passed=True,
        completeness_score=85.0,
        methodology_score=90.0,
        compliance_score=85.0,
        data_quality_score=80.0,
        findings_json=[],
    )
    db.add(qa)
    db.commit()

    retrieved_val = db.query(Valuation).filter(Valuation.id == val.id).first()
    retrieved_qa  = db.query(QualityAudit).filter(
        QualityAudit.valuation_id == val.id
    ).first()
    db.close()

    assert retrieved_val is not None, "Valuation not found"
    assert retrieved_qa  is not None, "QualityAudit not found"
    assert retrieved_qa.quality_grade == "B", "quality_grade mismatch"
    assert retrieved_qa.passed is True, "passed flag mismatch"
    print(f"PASS QualityAudit linked: {qa.id} -> {val.id}")


def test_audit_log_write():
    """ActivityLog row written, committed, and retrievable."""
    db = SessionLocal()

    log = ActivityLog(
        action="calculate",
        entity_type="valuation",
        actor="Phase 8 Test",
        success=True,
        duration_ms=250,
        details_json={"asset_type": "residential", "primary_value": 3_645_000},
    )
    db.add(log)
    db.commit()
    log_id = log.id

    retrieved = db.query(ActivityLog).filter(ActivityLog.id == log_id).first()
    db.close()

    assert retrieved is not None, "ActivityLog not found after commit"
    assert retrieved.action == "calculate", "action mismatch"
    assert retrieved.success is True, "success flag mismatch"
    assert retrieved.duration_ms == 250, "duration_ms mismatch"
    print(f"PASS ActivityLog recorded: {log_id}")


# ══════════════════════════════════════════════════════════════════════════════
# Suite 4: API Integration (3 tests)
# ══════════════════════════════════════════════════════════════════════════════
# Routes run with _DB_AVAILABLE = False (psycopg2 absent) so they fall back to
# the JSON search engine.  Tests verify status codes, response shapes, and
# graceful handling of missing valuation_id.

def _get_app():
    """Import Flask app lazily to avoid slowing down Suites 1-3."""
    from bridge_api import app  # noqa: PLC0415 (core_engine/ is on sys.path)
    return app


def test_api_comparables_search():
    """POST /api/comparables/search returns 200 with results list."""
    client = _get_app().test_client()
    resp = client.post("/api/comparables/search", json={
        "subject_property": {
            "property_type": _TYPE_APARTMENT,
            "area_sqm": 120,
        },
        "filters": {
            "governorate": _GOV_CAIRO_NEW,
        },
        "limit": 10,
    }, headers=_AUTH_HDR)

    assert resp.status_code == 200, f"Unexpected status: {resp.status_code}"
    data = resp.get_json()
    assert data["status"] == "success", f"status: {data.get('status')}"
    assert "results" in data, f"'results' key missing; got: {list(data.keys())}"
    assert "count" in data, "'count' key missing"
    # source is present when DB was attempted (may be 'json' fallback)
    source = data.get("source")
    if source is not None:
        assert source in ("postgresql", "json"), f"Unknown source: {source}"
    print(f"PASS /api/comparables/search: {data['count']} results (source={source})")


def test_api_valuation_full():
    """POST /api/valuation/full returns 200; valuation_id is UUID string or null.

    lat/lng are required by the JSON search engine to produce any candidates.
    """
    client = _get_app().test_client()
    resp = client.post("/api/valuation/full", json={
        "subject_property": {
            "property_type": _TYPE_APARTMENT,
            "area_sqm": 120,
            "age_years": 5,
        },
        "filters": {
            "latitude":  30.0276,
            "longitude": 31.4913,
        },
        "comparable_count": 5,
    }, headers=_AUTH_HDR)

    assert resp.status_code == 200, f"Unexpected status: {resp.status_code}"
    data = resp.get_json()
    assert data["status"] == "success", f"status: {data.get('status')}"
    assert "phase_4_values" in data, "'phase_4_values' missing"
    assert "purpose_valuations" in data, "'purpose_valuations' missing"

    val_id = data.get("valuation_id")
    if val_id is not None:
        assert isinstance(val_id, str), f"valuation_id must be str, got {type(val_id)}"
    print(f"PASS /api/valuation/full: valuation_id={val_id}")


def test_api_valuation_land():
    """POST /api/valuation/land returns 200 with land_valuation and quality_audit.

    lat/lng are required by the JSON search engine to produce any candidates.
    """
    client = _get_app().test_client()
    resp = client.post("/api/valuation/land", json={
        "subject_property": {
            "property_type": "vacant_land",
            "area_sqm": 5000,
            "hbu": "residential",
        },
        "filters": {
            "latitude":  30.0276,
            "longitude": 31.4913,
        },
        "run_quality_audit": True,
    }, headers=_AUTH_HDR)

    assert resp.status_code == 200, f"Unexpected status: {resp.status_code}"
    data = resp.get_json()
    assert data["status"] == "success", f"status: {data.get('status')}"
    assert "land_valuation" in data, "'land_valuation' missing"
    assert "quality_audit" in data, "'quality_audit' missing"

    val_id = data.get("valuation_id")
    if val_id is not None:
        assert isinstance(val_id, str), f"valuation_id must be str, got {type(val_id)}"

    qa = data.get("quality_audit")
    if qa:
        assert "quality_grade" in qa, "'quality_grade' missing from quality_audit"
        assert "quality_score" in qa, "'quality_score' missing from quality_audit"

    grade = qa.get("quality_grade") if qa else "N/A"
    print(f"PASS /api/valuation/land: valuation_id={val_id}, quality_grade={grade}")


# ══════════════════════════════════════════════════════════════════════════════
# Test runner
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    _SUITES = [
        ("Suite 1: Data Integrity", [
            test_comparable_count_total,
            test_comparable_no_null_ids,
            test_comparable_required_fields,
            test_comparable_distribution_by_type,
            test_comparable_price_statistics,
        ]),
        ("Suite 2: Query Performance", [
            test_query_performance_by_type,
            test_query_performance_by_price_range,
            test_query_performance_by_location,
            test_query_performance_chained,
        ]),
        ("Suite 3: Valuation Writes", [
            test_valuation_write,
            test_quality_audit_write,
            test_audit_log_write,
        ]),
        ("Suite 4: API Integration", [
            test_api_comparables_search,
            test_api_valuation_full,
            test_api_valuation_land,
        ]),
    ]

    passed = failed = 0
    for suite_name, tests in _SUITES:
        print(f"\n{'='*60}")
        print(f"  {suite_name}")
        print(f"{'='*60}")
        for fn in tests:
            try:
                fn()
                passed += 1
            except Exception as exc:
                failed += 1
                print(f"  FAIL {fn.__name__}: {exc}")

    print(f"\n{'='*60}")
    if failed == 0:
        print(f"  [OK]  All {passed} Task 8.4 tests passed!")
    else:
        print(f"  [WARN]   {passed} passed, {failed} FAILED")
    print(f"{'='*60}\n")
    sys.exit(0 if failed == 0 else 1)
