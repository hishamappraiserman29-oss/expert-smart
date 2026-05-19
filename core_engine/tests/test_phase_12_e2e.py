"""
test_phase_12_e2e.py — Phase 12: Batch Valuation E2E Tests

20 tests covering:
  1.  BatchProcessor unit — 5 properties, all completed
  2.  BatchProcessor unit — mixed valid/invalid (validation)
  3.  BatchProcessor unit — partial failure (process + fail)
  4.  BatchStatus.is_terminal() for all 6 states
  5.  POST /api/valuation/batch — pre-valued strategy (valuation_value)
  6.  POST /api/valuation/batch — price_per_sqm strategy
  7.  POST /api/valuation/batch — mixed strategies + one failure
  8.  POST /api/valuation/batch — empty properties → 400 error
  9.  POST /api/valuation/batch — generate_report=True creates download_url
  10. POST /api/valuation/batch response structure (all required keys present)
  11. BatchReportBuilder creates 3-sheet workbook
  12. Batch Summary sheet contains batch_id
  13. Completed Properties sheet has correct row count
  14. Failed & Skipped sheet shows failure message
  15. Empty batch (0 completed) does not crash sheet builder
  16. BatchRegistry register + get roundtrip
  17. BatchRegistry get unknown id → None
  18. BatchRegistry list_recent newest-first ordering
  19. GET /api/valuation/batch/<batch_id> → 200 after POST
  20. GET /api/valuation/batch/<batch_id> unknown id → 404
"""
from __future__ import annotations

import sys
from pathlib import Path

_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import os
os.environ.setdefault("JWT_SECRET", "test-secret-e2e-bundle")
os.chdir(str(_CORE))

from bridge_api import app
from auth.tokens import generate_token as _gen_token
_AUTH_HDR = {"Authorization": f"Bearer {_gen_token('test-user-e2e')}"}
from adapters.batch_processor import BatchProcessor, BatchStatus
from adapters.batch_registry import BatchRegistry
from reports.batch_report_builder import BatchReportBuilder


# ── Unit tests ────────────────────────────────────────────────────────────────

def test_batch_processor_five_properties():
    """BatchProcessor processes 5 properties to completion with correct totals."""
    bp = BatchProcessor("Five-Property Batch")
    vals = [3_645_000, 7_750_000, 2_500_000, 4_200_000, 3_500_000]
    for i, v in enumerate(vals, 1):
        bp.add_property(f"P{i}", f"Property {i}", "residential", 120.0,
                        {"valuation_value": v})

    bp.validate_batch()
    bp.start_processing()
    for idx, v in enumerate(vals):
        bp.process_property(idx, v)
    bp.complete_batch()

    assert bp.metrics.completed == 5
    assert bp.metrics.total_valuation_value == sum(vals)
    assert bp.metrics.status == BatchStatus.COMPLETED
    assert bp.metrics.progress_pct == 100.0
    assert abs(bp.metrics.average_valuation - sum(vals) / 5) < 1.0
    print(f"[PASS] test_batch_processor_five_properties — "
          f"total EGP {bp.metrics.total_valuation_value:,.0f}")


def test_batch_validation_mixed():
    """validate_batch() marks negative-area property as skipped."""
    bp = BatchProcessor("Mixed Validation")
    bp.add_property("P1", "Valid",        "residential",  120.0, {})
    bp.add_property("P2", "Bad Area",     "commercial",  -500.0, {})
    bp.add_property("P3", "Valid Land",   "land",        1000.0, {})

    issues = bp.validate_batch()
    assert issues["valid"]   == 2
    assert issues["invalid"] == 1
    assert bp.properties[1].status == "skipped"
    print(f"[PASS] test_batch_validation_mixed — 2 valid, 1 skipped")


def test_batch_partial_failure():
    """fail_property() tracks failed count; completion report groups correctly."""
    bp = BatchProcessor("Partial Failure")
    bp.add_property("P1", "Good",   "residential", 100.0, {})
    bp.add_property("P2", "Bad",    "commercial",  200.0, {})
    bp.add_property("P3", "Good2",  "land",        300.0, {})
    bp.validate_batch()
    bp.start_processing()
    bp.process_property(0, 3_000_000)
    bp.fail_property(1, "Insufficient data")
    bp.process_property(2, 2_500_000)
    bp.complete_batch()

    assert bp.metrics.completed == 2
    assert bp.metrics.failed    == 1
    r = bp.get_completion_report()
    assert len(r["completed_properties"]) == 2
    assert len(r["failed_properties"])    == 1
    assert r["failed_properties"][0]["error"] == "Insufficient data"
    print("[PASS] test_batch_partial_failure — 2 completed, 1 failed")


def test_batch_status_terminal():
    """BatchStatus.is_terminal() returns True iff status is final."""
    assert BatchStatus.is_terminal(BatchStatus.COMPLETED)  is True
    assert BatchStatus.is_terminal(BatchStatus.FAILED)     is True
    assert BatchStatus.is_terminal(BatchStatus.CANCELLED)  is True
    assert BatchStatus.is_terminal(BatchStatus.ERROR)      is True
    assert BatchStatus.is_terminal(BatchStatus.PENDING)    is False
    assert BatchStatus.is_terminal(BatchStatus.PROCESSING) is False
    print("[PASS] test_batch_status_terminal — 4 terminal, 2 non-terminal")


# ── API tests ─────────────────────────────────────────────────────────────────

_PRE_VALUED = [
    {"property_id": "A1", "property_name": "Tower A", "property_type": "commercial",
     "area_sqm": 500, "input_data": {"valuation_value": 7_750_000, "primary_purpose": "market_value"}},
    {"property_id": "A2", "property_name": "Villa B", "property_type": "residential",
     "area_sqm": 200, "input_data": {"valuation_value": 4_200_000}},
    {"property_id": "A3", "property_name": "Plot C",  "property_type": "land",
     "area_sqm": 800, "input_data": {"valuation_value": 2_500_000}},
]


def test_api_batch_pre_valued():
    """POST /api/valuation/batch with valuation_value strategy — all 3 complete."""
    with app.test_client() as client:
        resp = client.post("/api/valuation/batch", json={
            "batch_name": "Pre-Valued Test",
            "properties": _PRE_VALUED,
        }, headers=_AUTH_HDR)
        assert resp.status_code == 200
        d = resp.get_json()
        assert d["status"]               == "success"
        assert d["summary"]["completed"] == 3
        assert d["summary"]["failed"]    == 0
        assert d["summary"]["total_valuation_value"] == 7_750_000 + 4_200_000 + 2_500_000
    print(f"[PASS] test_api_batch_pre_valued — "
          f"total EGP {d['summary']['total_valuation_value']:,.0f}")


def test_api_batch_price_per_sqm():
    """POST /api/valuation/batch with price_per_sqm strategy — value = rate × area."""
    with app.test_client() as client:
        resp = client.post("/api/valuation/batch", json={
            "batch_name": "Rate-Based Test",
            "properties": [
                {"property_id": "B1", "property_name": "Office B1",
                 "property_type": "commercial", "area_sqm": 300,
                 "input_data": {"price_per_sqm": 25_000}},
                {"property_id": "B2", "property_name": "Apt B2",
                 "property_type": "residential", "area_sqm": 120,
                 "input_data": {"price_per_sqm": 30_000}},
            ],
        }, headers=_AUTH_HDR)
        assert resp.status_code == 200
        d = resp.get_json()
        assert d["summary"]["completed"] == 2
        values = {p["property_id"]: p["valuation_value"]
                  for p in d["completed_properties"]}
        assert values["B1"] == 300 * 25_000
        assert values["B2"] == 120 * 30_000
    print(f"[PASS] test_api_batch_price_per_sqm — "
          f"B1={values['B1']:,.0f}  B2={values['B2']:,.0f}")


def test_api_batch_mixed_strategies():
    """POST /api/valuation/batch — pre-valued + rate-based + no-data (fail)."""
    with app.test_client() as client:
        resp = client.post("/api/valuation/batch", json={
            "batch_name": "Mixed Strategy Test",
            "properties": [
                {"property_id": "M1", "property_name": "Pre-valued",
                 "property_type": "residential", "area_sqm": 150,
                 "input_data": {"valuation_value": 3_000_000}},
                {"property_id": "M2", "property_name": "Rate-based",
                 "property_type": "commercial", "area_sqm": 200,
                 "input_data": {"price_per_sqm": 20_000}},
                {"property_id": "M3", "property_name": "No data",
                 "property_type": "land", "area_sqm": 500,
                 "input_data": {}},
            ],
        }, headers=_AUTH_HDR)
        assert resp.status_code == 200
        d = resp.get_json()
        assert d["summary"]["completed"] == 2
        assert d["summary"]["failed"]    == 1
        assert d["failed_properties"][0]["id"] == "M3"
    print(f"[PASS] test_api_batch_mixed_strategies — 2 completed, 1 failed")


def test_api_batch_empty_properties():
    """POST /api/valuation/batch with empty properties → 400."""
    with app.test_client() as client:
        resp = client.post("/api/valuation/batch", json={
            "batch_name": "Empty",
            "properties": [],
        }, headers=_AUTH_HDR)
        assert resp.status_code == 400
        d = resp.get_json()
        assert d["status"] == "error"
    print("[PASS] test_api_batch_empty_properties — 400 as expected")


def test_api_batch_generate_report():
    """POST /api/valuation/batch with generate_report=True returns download_url."""
    with app.test_client() as client:
        resp = client.post("/api/valuation/batch", json={
            "batch_name": "Report Test",
            "properties": _PRE_VALUED,
            "generate_report": True,
        }, headers=_AUTH_HDR)
        assert resp.status_code == 200
        d = resp.get_json()
        assert d["report_id"]    is not None
        assert d["download_url"] is not None
        assert d["download_url"].endswith(".xlsx")
    print(f"[PASS] test_api_batch_generate_report — {d['download_url']}")


def test_api_batch_response_structure():
    """POST /api/valuation/batch response contains all required top-level keys."""
    with app.test_client() as client:
        resp = client.post("/api/valuation/batch", json={
            "batch_name": "Structure Check",
            "properties": _PRE_VALUED[:1],
        }, headers=_AUTH_HDR)
        assert resp.status_code == 200
        d = resp.get_json()
        required = {
            "status", "batch_id", "batch_name", "summary",
            "completed_properties", "failed_properties",
            "skipped_properties", "report_id", "download_url", "timestamp",
        }
        missing = required - set(d.keys())
        assert not missing, f"Missing keys: {missing}"
        summary_required = {
            "total_submitted", "completed", "failed",
            "skipped", "total_valuation_value", "average_valuation",
        }
        missing_s = summary_required - set(d["summary"].keys())
        assert not missing_s, f"Missing summary keys: {missing_s}"
    print(f"[PASS] test_api_batch_response_structure — {len(d)} top-level keys")


# ── BatchReportBuilder sheet tests (Task 12.2) ────────────────────────────────

def _make_completion_report(n_completed: int = 3,
                             n_failed: int = 1,
                             n_skipped: int = 0) -> dict:
    """Minimal completion report matching get_completion_report() shape."""
    completed = [
        {
            "property_id":     f"P{i}",
            "property_name":   f"Property {i}",
            "property_type":   "residential",
            "area_sqm":        120.0,
            "status":          "completed",
            "valuation_value": 3_000_000 + i * 500_000,
            "primary_purpose": "market_value",
            "processed_at":    "2026-05-08T10:00:00",
            "error_message":   "",
        }
        for i in range(1, n_completed + 1)
    ]
    failed = [
        {"id": f"F{i}", "name": f"Failed {i}", "error": "Insufficient data"}
        for i in range(1, n_failed + 1)
    ]
    skipped = [
        {"id": f"S{i}", "name": f"Skipped {i}"}
        for i in range(1, n_skipped + 1)
    ]
    total_val = sum(p["valuation_value"] for p in completed)
    avg_val   = total_val / n_completed if n_completed else 0
    return {
        "batch_id":    "test-batch-uuid-1234",
        "status":      "completed",
        "summary": {
            "total_submitted":       n_completed + n_failed + n_skipped,
            "completed":             n_completed,
            "failed":                n_failed,
            "skipped":               n_skipped,
            "total_valuation_value": total_val,
            "average_valuation":     avg_val,
        },
        "completed_properties": completed,
        "failed_properties":    failed,
        "skipped_properties":   skipped,
        "completed_at":         "2026-05-08T10:05:00",
    }


def test_batch_report_three_sheets():
    """BatchReportBuilder.build() creates exactly 3 sheets."""
    rpt = _make_completion_report()
    b   = BatchReportBuilder(rpt)
    b.sheet_batch_summary()
    b.sheet_completed_properties()
    b.sheet_failed_skipped()
    names = [ws.title for ws in b.workbook.worksheets]
    assert names == ["Batch Summary", "Completed Properties", "Failed & Skipped"], \
        f"Unexpected sheets: {names}"
    print(f"[PASS] test_batch_report_three_sheets — {names}")


def test_batch_summary_contains_batch_id():
    """Batch Summary sheet contains the batch_id value somewhere in column B."""
    rpt = _make_completion_report()
    b   = BatchReportBuilder(rpt)
    b.sheet_batch_summary()
    ws  = b.workbook["Batch Summary"]
    col_b = [ws.cell(row=r, column=2).value for r in range(1, ws.max_row + 1)]
    assert "test-batch-uuid-1234" in col_b, \
        f"batch_id not found in column B: {col_b}"
    print("[PASS] test_batch_summary_contains_batch_id")


def test_completed_sheet_row_count():
    """Completed Properties sheet has header row + 1 data row per completed property."""
    rpt     = _make_completion_report(n_completed=4, n_failed=0)
    b       = BatchReportBuilder(rpt)
    b.sheet_completed_properties()
    ws      = b.workbook["Completed Properties"]
    # Row 1 = title, row 3 = column headers, rows 4+ = data
    data_rows = [
        r for r in range(4, ws.max_row + 1)
        if ws.cell(row=r, column=1).value
    ]
    assert len(data_rows) == 4, f"Expected 4 data rows, got {len(data_rows)}"
    print(f"[PASS] test_completed_sheet_row_count — {len(data_rows)} property rows")


def test_failed_sheet_shows_error_message():
    """Failed & Skipped sheet contains the error message for failed properties."""
    rpt = _make_completion_report(n_completed=1, n_failed=2)
    b   = BatchReportBuilder(rpt)
    b.sheet_failed_skipped()
    ws  = b.workbook["Failed & Skipped"]
    all_vals = [
        ws.cell(row=r, column=c).value
        for r in range(1, ws.max_row + 1)
        for c in range(1, 5)
    ]
    assert "Insufficient data" in all_vals, \
        "Error message not found on Failed & Skipped sheet"
    print("[PASS] test_failed_sheet_shows_error_message")


def test_empty_batch_no_crash():
    """BatchReportBuilder handles 0 completed, 0 failed, 0 skipped without error."""
    rpt = _make_completion_report(n_completed=0, n_failed=0, n_skipped=0)
    b   = BatchReportBuilder(rpt)
    try:
        b.sheet_batch_summary()
        b.sheet_completed_properties()
        b.sheet_failed_skipped()
        print("[PASS] test_empty_batch_no_crash")
    except Exception as exc:
        raise AssertionError(f"Crashed on empty batch: {exc}") from exc


# ── Runner ────────────────────────────────────────────────────────────────────

# ── BatchRegistry tests (Task 12.3) ──────────────────────────────────────────

def test_registry_register_get():
    """BatchRegistry stores and retrieves a report by batch_id."""
    reg = BatchRegistry()
    report = {"batch_id": "abc-123", "status": "completed",
              "summary": {"completed": 2}}
    reg.register("abc-123", report)
    stored = reg.get("abc-123")
    assert stored is not None
    assert stored["batch_id"]            == "abc-123"
    assert stored["status"]              == "completed"
    assert "registered_at"               in stored
    print("[PASS] test_registry_register_get")


def test_registry_get_unknown():
    """BatchRegistry.get() returns None for an unknown batch_id."""
    reg = BatchRegistry()
    assert reg.get("does-not-exist") is None
    print("[PASS] test_registry_get_unknown")


def test_registry_list_recent_ordering():
    """list_recent() returns entries newest-first."""
    reg = BatchRegistry()
    for i in range(5):
        reg.register(f"batch-{i}", {"batch_id": f"batch-{i}", "seq": i})
    recent = reg.list_recent(limit=5)
    seqs = [r["seq"] for r in recent]
    assert seqs == sorted(seqs, reverse=True), f"Not newest-first: {seqs}"
    print(f"[PASS] test_registry_list_recent_ordering — order: {seqs}")


def test_api_get_batch_after_post():
    """GET /api/valuation/batch/<id> returns 200 for a batch submitted via POST."""
    with app.test_client() as client:
        post_resp = client.post("/api/valuation/batch", json={
            "batch_name": "Registry Test",
            "properties": _PRE_VALUED[:2],
        }, headers=_AUTH_HDR)
        assert post_resp.status_code == 200
        batch_id = post_resp.get_json()["batch_id"]

        get_resp = client.get(f"/api/valuation/batch/{batch_id}", headers=_AUTH_HDR)
        assert get_resp.status_code == 200
        d = get_resp.get_json()
        assert d["status"]                     == "success"
        assert d["batch"]["batch_id"]          == batch_id
        assert d["batch"]["summary"]["completed"] == 2
    print(f"[PASS] test_api_get_batch_after_post — id: {batch_id[:8]}…")


def test_api_get_batch_unknown_404():
    """GET /api/valuation/batch/<unknown-id> returns 404."""
    with app.test_client() as client:
        resp = client.get("/api/valuation/batch/nonexistent-id-xyz", headers=_AUTH_HDR)
        assert resp.status_code == 404
        d = resp.get_json()
        assert d["status"] == "not_found"
    print("[PASS] test_api_get_batch_unknown_404")


def test_all_phase_12_tests():
    print("\n=== Phase 12 E2E Tests ===")
    tests = [
        test_batch_processor_five_properties,
        test_batch_validation_mixed,
        test_batch_partial_failure,
        test_batch_status_terminal,
        test_api_batch_pre_valued,
        test_api_batch_price_per_sqm,
        test_api_batch_mixed_strategies,
        test_api_batch_empty_properties,
        test_api_batch_generate_report,
        test_api_batch_response_structure,
        test_batch_report_three_sheets,
        test_batch_summary_contains_batch_id,
        test_completed_sheet_row_count,
        test_failed_sheet_shows_error_message,
        test_empty_batch_no_crash,
        test_registry_register_get,
        test_registry_get_unknown,
        test_registry_list_recent_ordering,
        test_api_get_batch_after_post,
        test_api_get_batch_unknown_404,
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
        print("Phase 12 E2E COMPLETE")


if __name__ == "__main__":
    test_all_phase_12_tests()
