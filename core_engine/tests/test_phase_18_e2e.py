"""
test_phase_18_e2e.py — Phase 18.0 Automated Valuation Pipeline (12 tests)

Tests:
  01  PipelineStatus enum — all values + is_terminal()
  02  PropertyRecord dataclass fields and to_dict()
  03  PipelineResult dataclass fields and to_dict()
  04  parse_file — CSV with 3 valid rows → 3 PropertyRecords
  05  parse_file — CSV with flexible column aliases (area, type, city)
  06  parse_file — JSON array → PropertyRecord list
  07  parse_file — unsupported extension (.txt) → empty list
  08  scan_workspace — finds + parses CSV and JSON files together
  09  run() with mock bridge (success) → PipelineReport, results CSV written
  10  run() with mock bridge (API failure) → failed results recorded
  11  PipelineReport aggregate maths — total, average, counts
  12  cancel() sets status to CANCELLED; subsequent records marked skipped
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

_CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_CORE))
os.chdir(str(_CORE))

from agents.pipeline_orchestrator import (
    PipelineStatus, PropertyRecord, PipelineResult, PipelineReport,
    ValuationPipelineOrchestrator,
)
from agents.workspace_manager import WorkspaceManager
from mcp_bridge import APIResponse


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _fresh() -> tuple:
    """Return (WorkspaceManager, mock_bridge, orchestrator) with fresh temp dir."""
    tmp = tempfile.mkdtemp()
    wm  = WorkspaceManager(base_dir=tmp)
    bridge = MagicMock()
    bridge.evaluate_property.return_value = APIResponse(
        success=True, status="success",
        data={"primary_value": 3_000_000, "status": "success"},
    )
    orch = ValuationPipelineOrchestrator(wm, bridge)
    return wm, bridge, orch


def _csv_bytes(*rows: dict) -> bytes:
    import csv, io
    if not rows:
        return b"property_id,property_type,area_sqm,location\n"
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_01_pipeline_status_enum():
    assert PipelineStatus.IDLE      == "idle"
    assert PipelineStatus.COMPLETED == "completed"
    assert PipelineStatus.FAILED    == "failed"
    assert PipelineStatus.CANCELLED == "cancelled"

    assert PipelineStatus.is_terminal("completed") is True
    assert PipelineStatus.is_terminal("failed")    is True
    assert PipelineStatus.is_terminal("cancelled") is True
    assert PipelineStatus.is_terminal("running")   is False
    assert PipelineStatus.is_terminal("idle")      is False


def test_02_property_record_dataclass():
    r = PropertyRecord(
        record_id="P1", property_type="residential",
        area_sqm=150.0, location="Cairo",
        source_file="data.csv", raw_data={"k": "v"},
    )
    assert r.record_id     == "P1"
    assert r.area_sqm      == 150.0
    assert r.source_file   == "data.csv"
    d = r.to_dict()
    assert d["record_id"]     == "P1"
    assert d["property_type"] == "residential"
    assert "raw_data" not in d          # raw_data not serialised


def test_03_pipeline_result_dataclass():
    r = PipelineResult(
        record_id="P1", property_type="commercial",
        area_sqm=300.0, location="Giza",
        status="success", primary_purpose="market_value",
        valuation_value=7_500_000.0,
    )
    assert r.status          == "success"
    assert r.valuation_value == 7_500_000.0
    assert r.error           is None
    assert r.processed_at                # non-empty timestamp
    d = r.to_dict()
    assert d["valuation_value"] == 7_500_000.0
    assert d["error"]           == ""    # None → "" in to_dict


def test_04_parse_file_csv_standard_columns():
    wm, _, orch = _fresh()
    ws = wm.create_workspace("CSV WS")
    csv_data = _csv_bytes(
        {"property_id": "P1", "property_type": "residential", "area_sqm": "120", "location": "Cairo"},
        {"property_id": "P2", "property_type": "commercial",  "area_sqm": "500", "location": "Giza"},
        {"property_id": "P3", "property_type": "land",        "area_sqm": "800", "location": "Alexandria"},
    )
    wm.write_file(ws.workspace_id, "props.csv", csv_data)
    records = orch.parse_file(ws.workspace_id, "props.csv")

    assert len(records) == 3
    assert records[0].record_id     == "P1"
    assert records[0].area_sqm      == 120.0
    assert records[1].property_type == "commercial"
    assert records[2].location      == "Alexandria"


def test_05_parse_file_csv_flexible_aliases():
    wm, _, orch = _fresh()
    ws = wm.create_workspace("Alias WS")
    # Use non-standard aliases: 'id', 'type', 'area', 'city'
    csv_data = _csv_bytes(
        {"id": "X1", "type": "residential", "area": "200", "city": "Luxor"},
        {"id": "X2", "type": "commercial",  "area": "350", "city": "Aswan"},
    )
    wm.write_file(ws.workspace_id, "aliases.csv", csv_data)
    records = orch.parse_file(ws.workspace_id, "aliases.csv")

    assert len(records) == 2
    assert records[0].record_id == "X1"
    assert records[0].area_sqm  == 200.0
    assert records[1].location  == "Aswan"


def test_06_parse_file_json_array():
    wm, _, orch = _fresh()
    ws = wm.create_workspace("JSON WS")
    data = json.dumps([
        {"property_id": "J1", "property_type": "residential", "area_sqm": 90,  "location": "Cairo"},
        {"property_id": "J2", "property_type": "commercial",  "area_sqm": 400, "location": "Giza"},
    ]).encode("utf-8")
    wm.write_file(ws.workspace_id, "data.json", data)
    records = orch.parse_file(ws.workspace_id, "data.json")

    assert len(records) == 2
    assert records[0].record_id == "J1"
    assert records[1].area_sqm  == 400.0


def test_07_parse_file_unsupported_extension():
    wm, _, orch = _fresh()
    ws = wm.create_workspace("Unsup WS")
    wm.write_file(ws.workspace_id, "notes.txt", b"not a property file")
    records = orch.parse_file(ws.workspace_id, "notes.txt")
    assert records == []


def test_08_scan_workspace_combines_files():
    wm, _, orch = _fresh()
    ws = wm.create_workspace("Scan WS")
    wm.write_file(ws.workspace_id, "a.csv", _csv_bytes(
        {"property_id": "C1", "property_type": "residential", "area_sqm": "100", "location": "Cairo"},
    ))
    wm.write_file(ws.workspace_id, "b.json", json.dumps([
        {"property_id": "J1", "property_type": "commercial", "area_sqm": "200", "location": "Giza"},
        {"property_id": "J2", "property_type": "land",       "area_sqm": "500", "location": "Aswan"},
    ]).encode("utf-8"))
    wm.write_file(ws.workspace_id, "ignore.txt", b"ignored")

    records = orch.scan_workspace(ws.workspace_id)
    assert len(records) == 3
    ids = {r.record_id for r in records}
    assert ids == {"C1", "J1", "J2"}


def test_09_run_success_writes_results_csv():
    wm, bridge, orch = _fresh()
    ws = wm.create_workspace("Run WS")
    wm.write_file(ws.workspace_id, "props.csv", _csv_bytes(
        {"property_id": "P1", "property_type": "residential", "area_sqm": "150", "location": "Cairo"},
        {"property_id": "P2", "property_type": "commercial",  "area_sqm": "300", "location": "Giza"},
    ))

    report = orch.run(ws.workspace_id)

    assert report.status        == PipelineStatus.COMPLETED
    assert report.total_records == 2
    assert report.completed     == 2
    assert report.failed        == 0
    assert report.output_file is not None
    assert report.completed_at  is not None
    assert report.total_valuation_value == 6_000_000.0
    assert report.average_valuation     == 3_000_000.0

    # Results CSV must exist in workspace
    files = wm.list_files(ws.workspace_id)
    assert any(f.startswith("pipeline_results_") and f.endswith(".csv")
               for f in files)

    assert orch.get_status() == PipelineStatus.COMPLETED
    assert bridge.evaluate_property.call_count == 2


def test_10_run_api_failure_records_failed():
    wm, bridge, orch = _fresh()
    bridge.evaluate_property.return_value = APIResponse(
        success=False, status="error", error="Valuation engine unavailable"
    )
    ws = wm.create_workspace("Fail WS")
    wm.write_file(ws.workspace_id, "props.csv", _csv_bytes(
        {"property_id": "P1", "property_type": "residential",
         "area_sqm": "100", "location": "Cairo"},
    ))

    report = orch.run(ws.workspace_id)

    assert report.status    == PipelineStatus.COMPLETED
    assert report.failed    == 1
    assert report.completed == 0
    result = report.results[0]
    assert result.status == "failed"
    assert "unavailable" in (result.error or "").lower()


def test_11_pipeline_report_aggregate_maths():
    report = PipelineReport(
        pipeline_id="pid", workspace_id="wid",
        status=PipelineStatus.COMPLETED,
        total_records=4, completed=3, failed=1, skipped=0,
        total_valuation_value=12_000_000.0,
        average_valuation=4_000_000.0,
        started_at="2026-05-08T10:00:00",
    )
    d = report.to_dict()
    assert d["total_records"]         == 4
    assert d["completed"]             == 3
    assert d["total_valuation_value"] == 12_000_000.0
    assert d["average_valuation"]     == 4_000_000.0
    assert d["output_file"]           is None   # not set yet


def test_12_cancel_marks_remaining_skipped():
    wm, bridge, orch = _fresh()

    call_count = [0]

    def slow_valuate(area_sqm, location, property_type, primary_purpose):
        call_count[0] += 1
        if call_count[0] == 1:
            orch.cancel()   # cancel after first record
        return APIResponse(success=True, status="success",
                           data={"primary_value": 1_000_000})

    bridge.evaluate_property.side_effect = slow_valuate

    ws = wm.create_workspace("Cancel WS")
    wm.write_file(ws.workspace_id, "props.csv", _csv_bytes(
        {"property_id": "P1", "property_type": "residential",
         "area_sqm": "100", "location": "Cairo"},
        {"property_id": "P2", "property_type": "commercial",
         "area_sqm": "200", "location": "Giza"},
        {"property_id": "P3", "property_type": "land",
         "area_sqm": "500", "location": "Aswan"},
    ))

    report = orch.run(ws.workspace_id)

    skipped = [r for r in report.results if r.status == "skipped"]
    assert len(skipped) >= 1
    assert any("cancel" in (r.error or "").lower() for r in skipped)


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for fn in tests:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
            passed += 1
        except Exception as exc:
            import traceback
            print(f"  FAIL  {fn.__name__}: {exc}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed}/{passed + failed} tests passed")
