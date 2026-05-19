"""
test_phase_13_e2e.py — Phase 13: Persistent Storage E2E Tests

10 tests covering:
  1.  BatchStore creates table on init (file exists after construction)
  2.  save() + get() roundtrip — exact field values preserved
  3.  get() for unknown batch_id returns None
  4.  list_recent() returns newest-first ordering
  5.  count() reflects number of saved records
  6.  Persistence: save in one BatchStore instance, retrieve in a second (same db file)
  7.  list_recent(limit) caps results correctly
  8.  API: POST /api/valuation/batch then GET /<id> retrieves from SQLite
  9.  API: GET /api/valuation/batch (list) returns stored batches
  10. delete() / clear_all() remove records correctly
"""
from __future__ import annotations

import sys
import os
import tempfile
from pathlib import Path

_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.environ.setdefault("JWT_SECRET", "test-secret-e2e-bundle")
os.chdir(str(_CORE))

from bridge_api import app
from auth.tokens import generate_token as _gen_token
_AUTH_HDR = {"Authorization": f"Bearer {_gen_token('test-user-e2e')}"}
from database.batch_store import BatchStore


# ── Shared helpers ────────────────────────────────────────────────────────────

def _tmp_store() -> BatchStore:
    """Fresh BatchStore backed by a temp DB file — isolated per test."""
    db_path = os.path.join(tempfile.mkdtemp(), "test_batches.db")
    return BatchStore(db_path=db_path)


def _sample_report(batch_id: str = "test-batch-001",
                   batch_name: str = "Test Batch",
                   n_completed: int = 3,
                   n_failed: int = 1) -> dict:
    return {
        "batch_id":   batch_id,
        "batch_name": batch_name,
        "status":     "completed",
        "summary": {
            "total_submitted":       n_completed + n_failed,
            "completed":             n_completed,
            "failed":                n_failed,
            "skipped":               0,
            "total_valuation_value": n_completed * 3_000_000.0,
            "average_valuation":     3_000_000.0,
        },
        "completed_properties": [
            {"property_id": f"P{i}", "property_name": f"Prop {i}",
             "property_type": "residential", "area_sqm": 120,
             "status": "completed", "valuation_value": 3_000_000,
             "primary_purpose": "market_value", "processed_at": "2026-05-08T10:00:00",
             "error_message": ""}
            for i in range(1, n_completed + 1)
        ],
        "failed_properties": [
            {"id": f"F{i}", "name": f"Failed {i}", "error": "Insufficient data"}
            for i in range(1, n_failed + 1)
        ],
        "skipped_properties": [],
        "completed_at": "2026-05-08T10:05:00",
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_store_creates_db_file():
    """BatchStore init creates the SQLite file on disk."""
    db_path = os.path.join(tempfile.mkdtemp(), "create_test.db")
    assert not os.path.exists(db_path)
    BatchStore(db_path=db_path)
    assert os.path.exists(db_path), f"DB file not created at {db_path}"
    print(f"[PASS] test_store_creates_db_file — {db_path}")


def test_save_get_roundtrip():
    """save() then get() returns exact batch_id, status, summary counts."""
    store  = _tmp_store()
    report = _sample_report("batch-rt-001", "Roundtrip Test", n_completed=4, n_failed=1)
    store.save(report)

    stored = store.get("batch-rt-001")
    assert stored is not None
    assert stored["batch_id"]                      == "batch-rt-001"
    assert stored["status"]                        == "completed"
    assert stored["summary"]["completed"]          == 4
    assert stored["summary"]["failed"]             == 1
    assert stored["summary"]["total_valuation_value"] == 12_000_000.0
    assert len(stored["completed_properties"])     == 4
    assert len(stored["failed_properties"])        == 1
    assert "registered_at" in stored
    print(f"[PASS] test_save_get_roundtrip — 4 completed, 1 failed preserved")


def test_get_unknown_returns_none():
    """get() for an unregistered batch_id returns None."""
    store = _tmp_store()
    assert store.get("nonexistent-id-xyz") is None
    print("[PASS] test_get_unknown_returns_none")


def test_list_recent_newest_first():
    """list_recent() returns records in newest-registered_at-first order."""
    store = _tmp_store()
    import time
    for i in range(5):
        store.save(_sample_report(f"batch-order-{i}", f"Batch {i}"))
        time.sleep(0.01)   # ensure distinct timestamps

    recent = store.list_recent(limit=5)
    ids    = [r["batch_id"] for r in recent]
    assert ids == list(reversed([f"batch-order-{i}" for i in range(5)])), \
        f"Not newest-first: {ids}"
    print(f"[PASS] test_list_recent_newest_first — {ids}")


def test_count_reflects_saves():
    """count() returns the exact number of saved records."""
    store = _tmp_store()
    assert store.count() == 0
    for i in range(7):
        store.save(_sample_report(f"batch-count-{i}"))
    assert store.count() == 7
    print(f"[PASS] test_count_reflects_saves — count = {store.count()}")


def test_persistence_across_instances():
    """A record saved in one BatchStore instance is retrievable in a second instance
    pointing to the same DB file — confirming SQLite durability."""
    db_path = os.path.join(tempfile.mkdtemp(), "persist_test.db")
    store_a = BatchStore(db_path=db_path)
    store_a.save(_sample_report("persist-batch-1", "Persistence Test"))

    store_b = BatchStore(db_path=db_path)   # new connection, same file
    stored  = store_b.get("persist-batch-1")
    assert stored is not None
    assert stored["batch_id"] == "persist-batch-1"
    print(f"[PASS] test_persistence_across_instances — retrieved from fresh connection")


def test_list_recent_limit():
    """list_recent(limit=3) returns at most 3 records from a larger store."""
    store = _tmp_store()
    for i in range(10):
        store.save(_sample_report(f"batch-lim-{i}"))
    recent = store.list_recent(limit=3)
    assert len(recent) == 3
    print(f"[PASS] test_list_recent_limit — 3/{store.count()} returned")


def test_api_post_then_get_from_sqlite():
    """POST /api/valuation/batch followed by GET /<id> retrieves record from SQLite."""
    with app.test_client() as client:
        post_resp = client.post("/api/valuation/batch", json={
            "batch_name": "SQLite Integration Test",
            "properties": [
                {"property_id": "X1", "property_name": "Prop X1",
                 "property_type": "commercial", "area_sqm": 300,
                 "input_data": {"valuation_value": 5_000_000}},
                {"property_id": "X2", "property_name": "Prop X2",
                 "property_type": "residential", "area_sqm": 150,
                 "input_data": {"price_per_sqm": 28_000}},
            ],
        }, headers=_AUTH_HDR)
        assert post_resp.status_code == 200
        batch_id = post_resp.get_json()["batch_id"]

        get_resp = client.get(f"/api/valuation/batch/{batch_id}", headers=_AUTH_HDR)
        assert get_resp.status_code == 200
        d = get_resp.get_json()
        assert d["status"]                          == "success"
        assert d["batch"]["batch_id"]               == batch_id
        assert d["batch"]["summary"]["completed"]   == 2
    print(f"[PASS] test_api_post_then_get_from_sqlite — id: {batch_id[:8]}…")


def test_api_list_includes_posted_batch():
    """GET /api/valuation/batch?limit=50 includes a batch submitted via POST."""
    with app.test_client() as client:
        post_resp = client.post("/api/valuation/batch", json={
            "batch_name": "List Test Batch",
            "properties": [
                {"property_id": "L1", "property_name": "List Prop",
                 "property_type": "land", "area_sqm": 500,
                 "input_data": {"valuation_value": 2_000_000}},
            ],
        }, headers=_AUTH_HDR)
        assert post_resp.status_code == 200
        batch_id = post_resp.get_json()["batch_id"]

        list_resp = client.get("/api/valuation/batch?limit=50", headers=_AUTH_HDR)
        assert list_resp.status_code == 200
        ld = list_resp.get_json()
        assert ld["status"] == "success"
        listed_ids = [b["batch_id"] for b in ld["batches"]]
        assert batch_id in listed_ids, f"{batch_id[:8]}… not in {listed_ids}"
    print(f"[PASS] test_api_list_includes_posted_batch — {len(listed_ids)} batches listed")


def test_delete_and_clear():
    """delete() removes one record; clear_all() removes all records."""
    store = _tmp_store()
    for i in range(5):
        store.save(_sample_report(f"batch-del-{i}"))
    assert store.count() == 5

    store.delete("batch-del-2")
    assert store.count() == 4
    assert store.get("batch-del-2") is None

    store.clear_all()
    assert store.count() == 0
    print("[PASS] test_delete_and_clear — delete 1, then clear_all → 0")


# ── Runner ────────────────────────────────────────────────────────────────────

def test_all_phase_13_tests():
    print("\n=== Phase 13 E2E Tests ===")
    tests = [
        test_store_creates_db_file,
        test_save_get_roundtrip,
        test_get_unknown_returns_none,
        test_list_recent_newest_first,
        test_count_reflects_saves,
        test_persistence_across_instances,
        test_list_recent_limit,
        test_api_post_then_get_from_sqlite,
        test_api_list_includes_posted_batch,
        test_delete_and_clear,
    ]
    passed = 0
    for fn in tests:
        try:
            fn()
            passed += 1
        except Exception as exc:
            print(f"[FAIL] {fn.__name__} — {exc}")
    print(f"\n{passed}/{len(tests)} tests passed.")
    if passed == len(tests):
        print("Phase 13 E2E COMPLETE")


if __name__ == "__main__":
    test_all_phase_13_tests()
