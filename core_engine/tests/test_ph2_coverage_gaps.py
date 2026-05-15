"""
test_ph2_coverage_gaps.py — PH.2 Coverage Gap-Filling Tests

Targets specific uncovered lines identified by the baseline coverage run:
  - chat_agent.py          54% -> handlers for delete/backup/restore/watch/mode
  - workspace_manager.py   88% -> _load_existing(), size limit, empty list_files
  - mcp_bridge.py          65% -> error paths, uncalled bridge methods, MCP tools
  - mcp_setup.py           59% -> print_config, print_prerequisites, error paths
  - supervised_agent.py    85% -> backup edge cases, set_mode, set_approval_callback
  - pipeline_orchestrator  90% -> cancel edge cases, JSON dict wrapper, parse errors
"""
from __future__ import annotations

import asyncio
import csv
import io
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

_CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_CORE))
os.chdir(str(_CORE))

from agents.chat_agent import ChatAgent, ChatResponse
from agents.command_parser import CommandIntent
from agents.file_watcher import WatcherManager
from agents.pipeline_orchestrator import ValuationPipelineOrchestrator
from agents.supervised_agent import BackupManager, ExecutionMode, SupervisedAgent
from agents.workspace_manager import WorkspaceManager
from mcp_bridge import APIResponse, ExpertSmartBridge


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _stack():
    """Return (wm, agent, bot) backed by a fresh temp dir."""
    tmp = tempfile.mkdtemp()
    wm = WorkspaceManager(base_dir=tmp)
    bridge = MagicMock()
    bridge.evaluate_property.return_value = APIResponse(
        success=True, status="success", data={"primary_value": 1_000_000}
    )
    agent = SupervisedAgent(wm, bridge, execution_mode=ExecutionMode.AUTONOMOUS)
    bot = ChatAgent(wm, agent)
    return wm, agent, bot


def _csv_bytes(*rows):
    buf = io.StringIO()
    if not rows:
        return b"property_id,property_type,area_sqm,location\n"
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


# ══════════════════════════════════════════════════════════════════════════════
# Section A: chat_agent.py — uncovered handlers
# ══════════════════════════════════════════════════════════════════════════════


def test_A01_chat_response_to_dict():
    r = ChatResponse(success=True, message="ok", data={"k": "v"}, intent="help")
    d = r.to_dict()
    assert d["success"] is True
    assert d["message"] == "ok"
    assert d["data"] == {"k": "v"}
    assert d["intent"] == "help"


def test_A02_delete_workspace_via_chat():
    wm, agent, bot = _stack()
    ws = wm.create_workspace("To Delete")

    # success path
    resp = bot.chat(f"delete workspace {ws.workspace_id}")
    assert resp.success is True
    assert resp.intent == CommandIntent.DELETE_WORKSPACE
    assert wm.get_workspace(ws.workspace_id) is None

    # not found path
    resp2 = bot.chat(f"delete workspace {ws.workspace_id}")  # already deleted
    assert resp2.success is False
    assert "not found" in resp2.message.lower()

    # no workspace_id
    resp3 = bot.chat("delete workspace")
    assert resp3.success is False
    assert "provide" in resp3.message.lower()


def test_A03_create_backup_via_chat():
    wm, agent, bot = _stack()
    ws = wm.create_workspace("Backup WS")
    wm.write_file(ws.workspace_id, "data.csv", b"id,v\n1,100\n")

    # success with label
    resp = bot.chat(f'create backup "pre_release" on {ws.workspace_id}', workspace_id=ws.workspace_id)
    assert resp.success is True
    assert resp.intent == CommandIntent.CREATE_BACKUP
    assert resp.data is not None
    assert "backup_id" in resp.data

    # no workspace_id → error
    resp2 = bot.chat("create backup")
    assert resp2.success is False
    assert "workspace_id" in resp2.message.lower() or "provide" in resp2.message.lower()

    # no agent configured
    bot_no_agent = ChatAgent(wm, supervised_agent=None)
    resp3 = bot_no_agent.chat("create backup", workspace_id=ws.workspace_id)
    assert resp3.success is False
    assert "agent" in resp3.message.lower()


def test_A04_restore_backup_via_chat():
    wm, agent, bot = _stack()
    ws = wm.create_workspace("Restore WS")
    wm.write_file(ws.workspace_id, "data.csv", b"original")
    backup = agent.create_backup(ws.workspace_id, label="snap")

    # success
    wm.write_file(ws.workspace_id, "data.csv", b"changed")
    resp = bot.chat(f"restore backup {backup.backup_id}", workspace_id=ws.workspace_id)
    assert resp.success is True
    assert resp.intent == CommandIntent.RESTORE_BACKUP

    # no workspace_id
    resp2 = bot.chat(f"restore backup {backup.backup_id}")
    assert resp2.success is False

    # no backup_id
    resp3 = bot.chat("restore backup", workspace_id=ws.workspace_id)
    assert resp3.success is False
    assert "backup_id" in resp3.message.lower()

    # no agent
    bot_no_agent = ChatAgent(wm, supervised_agent=None)
    resp4 = bot_no_agent.chat(f"restore backup {backup.backup_id}",
                              workspace_id=ws.workspace_id)
    assert resp4.success is False


def test_A05_list_backups_via_chat():
    wm, agent, bot = _stack()
    ws = wm.create_workspace("LB WS")
    wm.write_file(ws.workspace_id, "x.csv", b"d")

    # empty
    resp = bot.chat("list backups", workspace_id=ws.workspace_id)
    assert resp.success is True
    assert resp.data["backups"] == []

    # with backups
    agent.create_backup(ws.workspace_id, "snap1")
    agent.create_backup(ws.workspace_id, "snap2")
    resp2 = bot.chat("list backups", workspace_id=ws.workspace_id)
    assert resp2.success is True
    assert len(resp2.data["backups"]) == 2

    # no workspace_id
    resp3 = bot.chat("list backups")
    assert resp3.success is False

    # no agent
    bot2 = ChatAgent(wm, supervised_agent=None)
    resp4 = bot2.chat("list backups", workspace_id=ws.workspace_id)
    assert resp4.success is False


def test_A06_set_mode_via_chat():
    wm, agent, bot = _stack()

    # success
    resp = bot.chat("set mode readonly")
    assert resp.success is True
    assert resp.intent == CommandIntent.SET_MODE
    assert agent._mode == "readonly"

    # no mode specified
    resp2 = bot.chat("set mode")
    assert resp2.success is False
    assert "mode" in resp2.message.lower()

    # no agent
    bot2 = ChatAgent(wm, supervised_agent=None)
    resp3 = bot2.chat("set mode supervised")
    assert resp3.success is False


def test_A07_watch_unwatch_via_chat():
    wm, agent, bot = _stack()
    ws = wm.create_workspace("Watch WS")

    # watch — success
    resp = bot.chat(f"watch workspace {ws.workspace_id}")
    assert resp.success is True
    assert resp.intent == CommandIntent.WATCH_WORKSPACE
    bot._watcher.stop_all()   # cleanup threads

    # watch — workspace not found
    resp2 = bot.chat("watch workspace aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    assert resp2.success is False
    assert "not found" in resp2.message.lower()

    # watch — no workspace_id
    resp3 = bot.chat("watch workspace")
    assert resp3.success is False

    # unwatch — success
    bot.chat(f"watch workspace {ws.workspace_id}")
    resp4 = bot.chat(f"unwatch workspace {ws.workspace_id}")
    assert resp4.success is True
    assert resp4.intent == CommandIntent.UNWATCH_WORKSPACE

    # unwatch — not being watched
    resp5 = bot.chat(f"unwatch workspace {ws.workspace_id}")
    assert resp5.success is False
    assert "not being watched" in resp5.message.lower()

    # unwatch — no workspace_id
    resp6 = bot.chat("unwatch workspace")
    assert resp6.success is False


def test_A08_dispatch_exception_handling():
    """Errors inside handlers must be caught and returned as failed ChatResponse."""
    wm, agent, bot = _stack()

    # Inject a RuntimeError into list_workspaces to trigger the except branch
    bot._wm.list_workspaces = MagicMock(side_effect=RuntimeError("injected error"))
    resp = bot.chat("list workspaces")
    assert isinstance(resp, ChatResponse)
    assert resp.success is False
    assert "error" in resp.message.lower() or "injected" in resp.message.lower()


def test_A09_run_pipeline_no_workspace_and_no_agent():
    wm, agent, _ = _stack()

    # No workspace_id
    bot = ChatAgent(wm, agent)
    resp = bot.chat("run pipeline")
    assert resp.success is False
    assert "workspace_id" in resp.message.lower() or "provide" in resp.message.lower()

    # No agent
    bot2 = ChatAgent(wm, supervised_agent=None)
    ws = wm.create_workspace("P WS")
    resp2 = bot2.chat("run pipeline", workspace_id=ws.workspace_id)
    assert resp2.success is False
    assert "agent" in resp2.message.lower()


# ══════════════════════════════════════════════════════════════════════════════
# Section B: workspace_manager.py — uncovered paths
# ══════════════════════════════════════════════════════════════════════════════


def test_B01_load_existing_on_init():
    """WorkspaceManager re-loads persisted workspaces when re-instantiated."""
    tmp = tempfile.mkdtemp()
    wm1 = WorkspaceManager(base_dir=tmp)
    ws  = wm1.create_workspace("Persisted WS")
    wm1.write_file(ws.workspace_id, "data.csv", b"id,v\n1,100\n")

    # Second instance over same dir — must discover the workspace
    wm2 = WorkspaceManager(base_dir=tmp)
    loaded = wm2.get_workspace(ws.workspace_id)
    assert loaded is not None
    assert loaded.name         == "Persisted WS"
    assert loaded.file_count   == 1


def test_B02_write_file_size_limit():
    """write_file must reject content over the 100 MB limit."""
    tmp = tempfile.mkdtemp()
    wm  = WorkspaceManager(base_dir=tmp)
    ws  = wm.create_workspace("Size WS")

    big = b"x" * (101 * 1024 * 1024)  # 101 MB
    try:
        wm.write_file(ws.workspace_id, "big.bin", big)
        assert False, "Expected ValueError for oversized file"
    except ValueError as exc:
        assert "exceeds" in str(exc).lower() or "limit" in str(exc).lower()


def test_B03_list_files_empty_workspace():
    """list_files returns [] for a workspace with no tracked files."""
    tmp = tempfile.mkdtemp()
    wm  = WorkspaceManager(base_dir=tmp)
    ws  = wm.create_workspace("Empty WS")

    files = wm.list_files(ws.workspace_id)
    assert files == []


# ══════════════════════════════════════════════════════════════════════════════
# Section C: mcp_bridge.py — error paths + uncalled bridge methods
# ══════════════════════════════════════════════════════════════════════════════


def _mock_bridge():
    """Return ExpertSmartBridge with mocked httpx.Client."""
    bridge = ExpertSmartBridge(api_base="http://localhost:5000")
    bridge.client = MagicMock()
    return bridge


def test_C01_get_returns_error_on_non_200():
    bridge = _mock_bridge()
    resp_mock = MagicMock()
    resp_mock.status_code = 500
    resp_mock.text        = "Internal Server Error"
    bridge.client.get.return_value = resp_mock

    result = bridge.health_check()
    assert result.success is False
    assert "500" in (result.error or "")


def test_C02_get_raises_exception():
    bridge = _mock_bridge()
    bridge.client.get.side_effect = ConnectionError("refused")

    result = bridge.health_check()
    assert result.success is False
    assert result.status == "unreachable"
    assert "refused" in (result.error or "")


def test_C03_health_check_unhealthy_response():
    bridge = _mock_bridge()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"status": "unhealthy", "service": "advisor"}
    bridge.client.get.return_value = resp

    result = bridge.health_check()
    assert result.success is True
    assert result.data["status"] == "unhealthy"


def test_C04_search_comparables_with_price_range():
    bridge = _mock_bridge()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"status": "success", "comparables": []}
    bridge.client.post.return_value = resp

    result = bridge.search_comparables(
        property_type="residential",
        location="Cairo",
        price_range=(500_000, 2_000_000),    # exercises line 148
    )
    assert result.success is True
    call_args = bridge.client.post.call_args
    payload   = call_args[1].get("json") or call_args[0][1]
    assert "price_range" in payload.get("filters", {})


def test_C05_analyze_portfolio():
    bridge = _mock_bridge()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"status": "success", "portfolio_value": 10_000_000}
    bridge.client.post.return_value = resp

    result = bridge.analyze_portfolio(
        properties=[{"property_type": "residential", "area_sqm": 120, "location": "Cairo"}]
    )
    assert result.success is True
    call_args = bridge.client.post.call_args
    payload   = call_args[1].get("json") or call_args[0][1]
    assert "properties" in payload


def test_C06_generate_report():
    bridge = _mock_bridge()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"status": "success", "report_url": "/reports/abc.xlsx"}
    bridge.client.post.return_value = resp

    result = bridge.generate_report(
        area_sqm=150, location="Giza", property_type="residential"
    )
    assert result.success is True


def test_C07_audit_valuation():
    bridge = _mock_bridge()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"status": "success", "audit_result": "pass"}
    bridge.client.post.return_value = resp

    result = bridge.audit_valuation(
        area_sqm=200, location="Alexandria", property_type="commercial"
    )
    assert result.success is True


def test_C08_dcf_analyze():
    bridge = _mock_bridge()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"status": "success", "npv": 5_000_000}
    bridge.client.post.return_value = resp

    result = bridge.dcf_analyze(
        discount_rate=0.12,
        holding_period=5,
        annual_projections=[500_000] * 5,
    )
    assert result.success is True
    call_args = bridge.client.post.call_args
    payload   = call_args[1].get("json") or call_args[0][1]
    assert "dcf_assumptions" in payload
    assert payload["dcf_assumptions"]["discount_rate"] == 0.12


def test_C09_mcp_tool_functions():
    """Call MCP tool functions via asyncio.run(mcp.call_tool(...))."""
    import mcp_bridge as mb

    # Patch the module-level bridge singleton
    mock_bridge = MagicMock()
    mock_bridge.health_check.return_value = APIResponse(
        success=True, status="success", data={"status": "ok"}
    )
    mock_bridge.evaluate_property.return_value = APIResponse(
        success=True, status="success", data={"primary_value": 2_000_000}
    )
    mock_bridge.get_batch_status.return_value = APIResponse(
        success=True, status="success", data={"batch_id": "abc"}
    )

    with patch.object(mb, "bridge", mock_bridge):
        # Test _dump helper
        r = APIResponse(success=True, status="success", data={"k": "v"})
        dumped = json.loads(mb._dump(r))
        assert dumped["success"] is True

        # Test tool functions directly through asyncio.run
        result = asyncio.run(mb.mcp.call_tool("health_check", {}))
        assert result is not None

        result2 = asyncio.run(mb.mcp.call_tool("evaluate_property", {
            "area_sqm": 150, "location": "Cairo",
            "property_type": "residential", "primary_purpose": "market_value",
        }))
        assert result2 is not None


# ══════════════════════════════════════════════════════════════════════════════
# Section D: mcp_setup.py — uncovered paths
# ══════════════════════════════════════════════════════════════════════════════


def test_D01_print_config(capsys=None):
    from mcp_setup import MCPSetup
    setup = MCPSetup()
    cfg   = setup.generate_config()

    # Capture print output by redirecting to StringIO
    import io as _io
    old_stdout, sys.stdout = sys.stdout, _io.StringIO()
    setup.print_config()
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout

    assert "expert_smart" in output.lower() or "mcp" in output.lower()


def test_D02_print_prerequisites():
    from mcp_setup import MCPSetup
    setup = MCPSetup()

    import io as _io
    old_stdout, sys.stdout = sys.stdout, _io.StringIO()
    ok = setup.print_prerequisites()
    sys.stdout = old_stdout

    assert isinstance(ok, bool)


def test_D03_check_prerequisites_handles_missing_python():
    """check_prerequisites must not raise even when the python exe is missing."""
    from mcp_setup import MCPSetup
    setup  = MCPSetup(python_exe="nonexistent_python_xyz")
    checks = setup.check_prerequisites()
    assert isinstance(checks, list)
    assert len(checks) > 0
    # The Python-exe check should exist and report failure gracefully
    py_check = next((c for c in checks if "python" in c["name"].lower()), None)
    assert py_check is not None
    assert py_check["ok"] is False


def test_D04_install_error_path():
    """install() must return an error dict when the target path can't be created."""
    import tempfile
    from mcp_setup import MCPSetup
    setup = MCPSetup()
    # Use an existing FILE as if it were a parent directory — mkdir will fail
    tmp_file = Path(tempfile.mktemp())
    tmp_file.write_text("block", encoding="utf-8")
    try:
        result = setup.install(target_path=tmp_file / "sub" / "config.json")
        assert result["ok"] is False
        assert result["action"] == "error"
        assert result["error"] is not None
    finally:
        tmp_file.unlink(missing_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# Section E: supervised_agent.py — remaining gaps
# ══════════════════════════════════════════════════════════════════════════════


def test_E01_set_mode_and_set_approval_callback():
    tmp = tempfile.mkdtemp()
    wm  = WorkspaceManager(base_dir=tmp)
    agent = SupervisedAgent(wm, None, execution_mode=ExecutionMode.MANUAL)

    agent.set_mode(ExecutionMode.AUTONOMOUS)
    assert agent._mode == ExecutionMode.AUTONOMOUS

    cb = MagicMock(return_value=True)
    agent.set_approval_callback(cb)
    assert agent._approval_callback is cb


def test_E02_backup_manager_create_empty_workspace():
    """create_backup on a workspace with zero files returns file_count=0."""
    tmp = tempfile.mkdtemp()
    wm  = WorkspaceManager(base_dir=tmp)
    ws  = wm.create_workspace("Empty BK WS")

    bm   = BackupManager(wm)
    info = bm.create_backup(ws.workspace_id)
    assert info.file_count == 0
    assert info.size_bytes == 0


def test_E03_backup_manager_restore_wrong_workspace():
    """restore_backup must return False if backup belongs to a different workspace."""
    tmp = tempfile.mkdtemp()
    wm  = WorkspaceManager(base_dir=tmp)
    ws1 = wm.create_workspace("WS-1")
    ws2 = wm.create_workspace("WS-2")
    wm.write_file(ws1.workspace_id, "x.csv", b"data")

    bm   = BackupManager(wm)
    info = bm.create_backup(ws1.workspace_id)

    # Try to restore ws1's backup into ws2
    ok = bm.restore_backup(ws2.workspace_id, info.backup_id)
    assert ok is False


def test_E04_backup_manager_restore_missing_backup():
    tmp = tempfile.mkdtemp()
    wm  = WorkspaceManager(base_dir=tmp)
    ws  = wm.create_workspace("WS")

    bm = BackupManager(wm)
    ok = bm.restore_backup(ws.workspace_id, "nonexistent-backup-id")
    assert ok is False


def test_E05_gate_rejects_unknown_workspace_in_readonly():
    """READONLY mode must reject write actions even for unknown workspace."""
    tmp   = tempfile.mkdtemp()
    wm    = WorkspaceManager(base_dir=tmp)
    agent = SupervisedAgent(wm, None, execution_mode=ExecutionMode.READONLY)

    try:
        agent.run_pipeline("no-such-workspace-id")
        assert False, "Expected PermissionError"
    except PermissionError:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# Section F: pipeline_orchestrator.py — remaining gaps
# ══════════════════════════════════════════════════════════════════════════════


def test_F01_parse_json_dict_wrapper():
    """JSON file with {'properties': [...]} wrapper must parse correctly."""
    tmp = tempfile.mkdtemp()
    wm  = WorkspaceManager(base_dir=tmp)
    ws  = wm.create_workspace("JSON WS")

    data = json.dumps({"properties": [
        {"property_id": "P1", "property_type": "residential",
         "area_sqm": 120, "location": "Cairo"},
    ]}).encode("utf-8")
    wm.write_file(ws.workspace_id, "wrapped.json", data)

    bridge = MagicMock()
    orch   = ValuationPipelineOrchestrator(wm, bridge)
    records = orch.parse_file(ws.workspace_id, "wrapped.json")

    assert len(records) == 1
    assert records[0].record_id == "P1"


def test_F02_parse_csv_skips_invalid_rows():
    """Rows with zero area or missing location are silently skipped."""
    tmp = tempfile.mkdtemp()
    wm  = WorkspaceManager(base_dir=tmp)
    ws  = wm.create_workspace("Skip WS")

    content = _csv_bytes(
        {"property_id": "P1", "property_type": "residential",
         "area_sqm": "0",   "location": "Cairo"},       # area = 0 → skip
        {"property_id": "P2", "property_type": "residential",
         "area_sqm": "100", "location": ""},             # no location → skip
        {"property_id": "P3", "property_type": "residential",
         "area_sqm": "100", "location": "Giza"},         # valid
    )
    wm.write_file(ws.workspace_id, "data.csv", content)

    bridge = MagicMock()
    orch   = ValuationPipelineOrchestrator(wm, bridge)
    records = orch.parse_file(ws.workspace_id, "data.csv")

    assert len(records) == 1
    assert records[0].record_id == "P3"


def test_F03_run_empty_workspace_returns_completed():
    """Pipeline on an empty workspace must return COMPLETED with 0 records."""
    tmp = tempfile.mkdtemp()
    wm  = WorkspaceManager(base_dir=tmp)
    ws  = wm.create_workspace("Empty WS")

    bridge = MagicMock()
    orch   = ValuationPipelineOrchestrator(wm, bridge)
    report = orch.run(ws.workspace_id)

    assert report.status       == "completed"
    assert report.total_records == 0
    bridge.evaluate_property.assert_not_called()


def test_F04_get_status_and_get_report():
    """get_status() and get_report() reflect pipeline state."""
    tmp = tempfile.mkdtemp()
    wm  = WorkspaceManager(base_dir=tmp)
    ws  = wm.create_workspace("Status WS")

    bridge = MagicMock()
    bridge.evaluate_property.return_value = APIResponse(
        success=True, status="success", data={"primary_value": 500_000}
    )
    orch = ValuationPipelineOrchestrator(wm, bridge)
    assert orch.get_status() == "idle"
    assert orch.get_report() is None

    wm.write_file(ws.workspace_id, "p.csv", _csv_bytes(
        {"property_id": "P1", "property_type": "residential",
         "area_sqm": "100", "location": "Cairo"},
    ))
    report = orch.run(ws.workspace_id)

    assert orch.get_status() == "completed"
    assert orch.get_report() is report


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests  = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
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
