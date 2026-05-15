"""
test_phase_21_e2e.py — Phase 21.0 Chat UI + CommandParser (12 tests)

Tests:
  01  CommandIntent enum — all 14 values present
  02  ParsedCommand dataclass — fields and to_dict()
  03  CommandParser — RUN_PIPELINE intent (multiple phrasings)
  04  CommandParser — BACKUP intents (create / restore / list)
  05  CommandParser — WORKSPACE intents (create / delete / list)
  06  CommandParser — utility intents (status / log / mode / help / unknown)
  07  CommandParser — parameter extraction (UUID, mode, quoted label, purpose)
  08  ChatAgent — list_workspaces (empty then with workspaces)
  09  ChatAgent — create_workspace extracts quoted name
  10  ChatAgent — run_pipeline dispatches to supervised_agent
  11  ChatAgent — show_log and show_status return structured data
  12  ChatAgent — help returns command list; unknown returns hint
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

_CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_CORE))
os.chdir(str(_CORE))

from agents.command_parser import CommandIntent, CommandParser, ParsedCommand
from agents.chat_agent import ChatAgent, ChatResponse
from agents.workspace_manager import WorkspaceManager
from agents.supervised_agent import SupervisedAgent, ExecutionMode
from mcp_bridge import APIResponse


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _fresh_stack():
    """Return (WorkspaceManager, SupervisedAgent, ChatAgent) backed by temp dir."""
    tmp    = tempfile.mkdtemp()
    wm     = WorkspaceManager(base_dir=tmp)
    bridge = MagicMock()
    bridge.evaluate_property.return_value = APIResponse(
        success=True, status="success",
        data={"primary_value": 1_500_000},
    )
    agent = SupervisedAgent(wm, bridge, execution_mode=ExecutionMode.AUTONOMOUS)
    bot   = ChatAgent(wm, agent)
    return wm, agent, bot


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_01_command_intent_enum():
    expected = {
        "run_pipeline", "create_backup", "restore_backup", "list_backups",
        "create_workspace", "delete_workspace", "list_workspaces",
        "watch_workspace", "unwatch_workspace",
        "show_status", "show_log", "set_mode",
        "help", "unknown",
    }
    actual = {i.value for i in CommandIntent}
    assert actual == expected, f"Missing: {expected - actual}"


def test_02_parsed_command_dataclass():
    cmd = ParsedCommand(
        intent=CommandIntent.RUN_PIPELINE,
        params={"workspace_id": "ws-abc"},
        raw_text="run pipeline on ws-abc",
        confidence=1.0,
    )
    assert cmd.intent     == "run_pipeline"
    assert cmd.confidence == 1.0
    assert cmd.params["workspace_id"] == "ws-abc"

    d = cmd.to_dict()
    assert d["intent"]     == "run_pipeline"
    assert d["confidence"] == 1.0
    assert d["raw_text"]   == "run pipeline on ws-abc"
    assert "params" in d


def test_03_parser_run_pipeline_phrasings():
    p = CommandParser()

    for phrase in [
        "run pipeline",
        "run the pipeline on ws-123",
        "start pipeline",
        "execute pipeline now",
        "valuate all properties",
        "process pipeline for workspace",
    ]:
        cmd = p.parse(phrase)
        assert cmd.intent == CommandIntent.RUN_PIPELINE, \
            f"Expected RUN_PIPELINE for: {phrase!r}, got {cmd.intent!r}"

    assert p.parse("").intent       == CommandIntent.UNKNOWN
    assert p.parse("   ").intent    == CommandIntent.UNKNOWN
    assert p.parse("   ").confidence == 0.0


def test_04_parser_backup_intents():
    p = CommandParser()

    # RESTORE (checked before CREATE because "restore" is unambiguous)
    assert p.parse("restore backup").intent                     == CommandIntent.RESTORE_BACKUP
    assert p.parse("please restore the previous snapshot").intent == CommandIntent.RESTORE_BACKUP

    # CREATE
    assert p.parse("create backup").intent                     == CommandIntent.CREATE_BACKUP
    assert p.parse("take a snapshot of the workspace").intent  == CommandIntent.CREATE_BACKUP
    assert p.parse("make backup now").intent                   == CommandIntent.CREATE_BACKUP

    # LIST
    assert p.parse("list backups").intent             == CommandIntent.LIST_BACKUPS
    assert p.parse("show all backups").intent         == CommandIntent.LIST_BACKUPS
    assert p.parse("get backup list").intent          == CommandIntent.LIST_BACKUPS


def test_05_parser_workspace_intents():
    p = CommandParser()

    assert p.parse("create workspace").intent          == CommandIntent.CREATE_WORKSPACE
    assert p.parse("new workspace for project").intent == CommandIntent.CREATE_WORKSPACE
    assert p.parse("add workspace").intent             == CommandIntent.CREATE_WORKSPACE

    assert p.parse("delete workspace").intent          == CommandIntent.DELETE_WORKSPACE
    assert p.parse("remove workspace abc").intent      == CommandIntent.DELETE_WORKSPACE

    assert p.parse("list workspaces").intent           == CommandIntent.LIST_WORKSPACES
    assert p.parse("show workspaces").intent           == CommandIntent.LIST_WORKSPACES
    assert p.parse("get workspace list").intent        == CommandIntent.LIST_WORKSPACES


def test_06_parser_utility_intents():
    p = CommandParser()

    assert p.parse("status").intent          == CommandIntent.SHOW_STATUS
    assert p.parse("show status").intent     == CommandIntent.SHOW_STATUS
    assert p.parse("health check").intent    == CommandIntent.SHOW_STATUS

    assert p.parse("log").intent             == CommandIntent.SHOW_LOG
    assert p.parse("show history").intent    == CommandIntent.SHOW_LOG
    assert p.parse("audit trail").intent     == CommandIntent.SHOW_LOG

    assert p.parse("set mode supervised").intent      == CommandIntent.SET_MODE
    assert p.parse("switch to autonomous mode").intent == CommandIntent.SET_MODE
    assert p.parse("autonomous").intent               == CommandIntent.SET_MODE

    assert p.parse("help").intent            == CommandIntent.HELP
    assert p.parse("?").intent               == CommandIntent.HELP
    assert p.parse("???").intent             == CommandIntent.HELP

    assert p.parse("xyzzy").intent           == CommandIntent.UNKNOWN
    assert p.parse("123 abc def").intent     == CommandIntent.UNKNOWN


def test_07_parser_parameter_extraction():
    p    = CommandParser()
    uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

    # UUID → workspace_id for RUN_PIPELINE
    cmd = p.parse(f"run pipeline on {uuid}")
    assert cmd.params.get("workspace_id") == uuid

    # UUID → backup_id for RESTORE
    cmd = p.parse(f"restore backup {uuid}")
    assert cmd.params.get("backup_id") == uuid

    # Mode extraction
    cmd = p.parse("set mode readonly")
    assert cmd.params.get("mode") == "readonly"

    cmd = p.parse("switch to supervised")
    assert cmd.params.get("mode") == "supervised"

    # Quoted label for CREATE_BACKUP
    cmd = p.parse('create backup "before_release"')
    assert cmd.params.get("label") == "before_release"

    # Quoted name for CREATE_WORKSPACE
    cmd = p.parse("create workspace \"Cairo Portfolio\"")
    assert cmd.params.get("name") == "Cairo Portfolio"

    # Primary purpose extraction
    cmd = p.parse("run pipeline with purpose mortgage")
    assert cmd.params.get("primary_purpose") == "mortgage"


def test_08_chat_agent_list_workspaces():
    wm, agent, bot = _fresh_stack()

    # Empty
    resp = bot.chat("list workspaces")
    assert resp.success is True
    assert resp.intent  == CommandIntent.LIST_WORKSPACES
    assert resp.data is not None
    assert resp.data["workspaces"] == []

    # With workspaces
    wm.create_workspace("Cairo Fund")
    wm.create_workspace("Giza Commercial")
    resp = bot.chat("show workspaces")
    assert resp.success is True
    assert len(resp.data["workspaces"]) == 2
    assert "Cairo Fund" in resp.message


def test_09_chat_agent_create_workspace():
    wm, agent, bot = _fresh_stack()

    resp = bot.chat('create workspace "Alexandria Retail"')
    assert resp.success is True
    assert resp.intent  == CommandIntent.CREATE_WORKSPACE
    assert resp.data is not None
    assert resp.data["name"] == "Alexandria Retail"
    assert resp.data["workspace_id"]   # non-empty UUID

    # Verify workspace actually exists
    ws = wm.get_workspace(resp.data["workspace_id"])
    assert ws is not None
    assert ws.name == "Alexandria Retail"


def test_10_chat_agent_run_pipeline():
    import csv, io

    wm, agent, bot = _fresh_stack()
    ws = wm.create_workspace("Pipeline WS")

    buf = io.StringIO()
    w   = csv.DictWriter(buf, fieldnames=["property_id", "property_type", "area_sqm", "location"])
    w.writeheader()
    w.writerow({"property_id": "P1", "property_type": "residential",
                "area_sqm": "150", "location": "Cairo"})
    wm.write_file(ws.workspace_id, "props.csv", buf.getvalue().encode("utf-8"))

    resp = bot.chat(f"run pipeline on {ws.workspace_id}")
    assert resp.success is True
    assert resp.intent  == CommandIntent.RUN_PIPELINE
    assert resp.data is not None
    assert resp.data["completed"] == 1
    assert resp.data["failed"]    == 0
    assert "succeeded" in resp.message


def test_11_chat_agent_show_log_and_status():
    wm, agent, bot = _fresh_stack()

    # Empty log
    resp = bot.chat("log")
    assert resp.success is True
    assert resp.intent == CommandIntent.SHOW_LOG
    assert "empty" in resp.message.lower() or resp.data is not None

    # Status
    resp = bot.chat("status")
    assert resp.success is True
    assert resp.intent  == CommandIntent.SHOW_STATUS
    assert resp.data is not None
    assert "workspace_count" in resp.data
    assert "mode" in resp.data
    assert "log_entries" in resp.data

    # After running pipeline, log should have entries
    ws = wm.create_workspace("Log WS")
    resp2 = bot.chat(f"run pipeline on {ws.workspace_id}")
    log_resp = bot.chat("show history")
    assert log_resp.success is True
    assert len(log_resp.data["log"]) > 0


def test_12_chat_agent_help_and_unknown():
    _, _, bot = _fresh_stack()

    # Help
    resp = bot.chat("help")
    assert resp.success is True
    assert resp.intent == CommandIntent.HELP
    assert "run pipeline"      in resp.message.lower()
    assert "create workspace"  in resp.message.lower()
    assert "set mode"          in resp.message.lower()

    resp2 = bot.chat("?")
    assert resp2.intent == CommandIntent.HELP

    # Unknown
    resp3 = bot.chat("xyzzy magic word")
    assert resp3.success is False
    assert resp3.intent == CommandIntent.UNKNOWN
    assert "help" in resp3.message.lower() or "understand" in resp3.message.lower()

    # Empty input
    resp4 = bot.chat("")
    assert resp4.intent == CommandIntent.UNKNOWN


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
