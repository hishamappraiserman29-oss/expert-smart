"""
test_phase_19_e2e.py — Phase 19.0 Supervised Autonomy (12 tests)

Tests:
  01  ExecutionMode enum — all 4 values
  02  ActionType enum — all 8 values + _WRITE_ACTIONS / _RISKY_ACTIONS membership
  03  ActionRecord dataclass — fields and to_dict()
  04  BackupManager.create_backup — copies workspace files, writes backup.json
  05  BackupManager.list_backups — returns only backups for the given workspace
  06  BackupManager.restore_backup — restores files, verifies content
  07  BackupManager.delete_backup — removes directory, returns False for missing
  08  SupervisedAgent AUTONOMOUS mode — run_pipeline auto-approved, report returned
  09  SupervisedAgent READONLY mode — run_pipeline raises PermissionError
  10  SupervisedAgent SUPERVISED mode — non-risky action auto-approved; risky gated
  11  SupervisedAgent MANUAL mode — every action requires callback
  12  auto_backup=True creates pre_pipeline backup; action log records all events
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

from agents.supervised_agent import (
    ExecutionMode, ActionType,
    ActionRecord, BackupInfo, BackupManager, SupervisedAgent,
    _WRITE_ACTIONS, _RISKY_ACTIONS,
)
from agents.workspace_manager import WorkspaceManager
from mcp_bridge import APIResponse


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _fresh():
    """Return (WorkspaceManager, mock_bridge, SupervisedAgent in AUTONOMOUS mode)."""
    tmp    = tempfile.mkdtemp()
    wm     = WorkspaceManager(base_dir=tmp)
    bridge = MagicMock()
    bridge.evaluate_property.return_value = APIResponse(
        success=True, status="success",
        data={"primary_value": 2_000_000},
    )
    agent = SupervisedAgent(wm, bridge, execution_mode=ExecutionMode.AUTONOMOUS)
    return wm, bridge, agent


def _csv_bytes(*rows):
    import csv, io
    if not rows:
        return b"property_id,property_type,area_sqm,location\n"
    buf = io.StringIO()
    w   = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_01_execution_mode_enum():
    assert ExecutionMode.AUTONOMOUS == "autonomous"
    assert ExecutionMode.SUPERVISED == "supervised"
    assert ExecutionMode.MANUAL     == "manual"
    assert ExecutionMode.READONLY   == "readonly"
    modes = {m.value for m in ExecutionMode}
    assert modes == {"autonomous", "supervised", "manual", "readonly"}


def test_02_action_type_enum_and_frozensets():
    assert ActionType.SCAN         == "scan"
    assert ActionType.READ_FILE    == "read_file"
    assert ActionType.WRITE_FILE   == "write_file"
    assert ActionType.DELETE_FILE  == "delete_file"
    assert ActionType.VALUATE      == "valuate"
    assert ActionType.BACKUP       == "backup"
    assert ActionType.RESTORE      == "restore"
    assert ActionType.RUN_PIPELINE == "run_pipeline"

    # _WRITE_ACTIONS blocks writes in READONLY
    assert ActionType.WRITE_FILE   in _WRITE_ACTIONS
    assert ActionType.DELETE_FILE  in _WRITE_ACTIONS
    assert ActionType.RUN_PIPELINE in _WRITE_ACTIONS
    assert ActionType.SCAN         not in _WRITE_ACTIONS

    # _RISKY_ACTIONS require approval in SUPERVISED
    assert ActionType.DELETE_FILE  in _RISKY_ACTIONS
    assert ActionType.RESTORE      in _RISKY_ACTIONS
    assert ActionType.RUN_PIPELINE in _RISKY_ACTIONS
    assert ActionType.WRITE_FILE   not in _RISKY_ACTIONS


def test_03_action_record_dataclass():
    rec = ActionRecord(
        action_id="aid-1",
        action_type=ActionType.BACKUP,
        workspace_id="ws-1",
        details={"label": "pre_run"},
        execution_mode=ExecutionMode.SUPERVISED,
        status="completed",
        created_at="2026-05-08T10:00:00",
    )
    assert rec.action_id      == "aid-1"
    assert rec.status         == "completed"
    assert rec.completed_at   is None
    assert rec.error          is None

    d = rec.to_dict()
    assert d["action_type"]    == ActionType.BACKUP
    assert d["execution_mode"] == ExecutionMode.SUPERVISED
    assert "details" not in d       # details excluded from to_dict


def test_04_backup_manager_create_backup():
    tmp = tempfile.mkdtemp()
    wm  = WorkspaceManager(base_dir=tmp)
    ws  = wm.create_workspace("BM WS")
    wm.write_file(ws.workspace_id, "data.csv", b"id,value\n1,100\n")
    wm.write_file(ws.workspace_id, "report.txt", b"text")

    bm   = BackupManager(wm)
    info = bm.create_backup(ws.workspace_id, label="snapshot_1")

    assert info.backup_id
    assert info.workspace_id == ws.workspace_id
    assert info.label        == "snapshot_1"
    assert info.file_count   == 2
    assert info.size_bytes   > 0

    # backup.json must exist inside backup directory
    backup_dir = Path(info.backup_path)
    assert (backup_dir / "backup.json").exists()

    # workspace.json must NOT be in backup
    assert not (backup_dir / "workspace.json").exists()

    # to_dict
    d = info.to_dict()
    assert d["workspace_id"] == ws.workspace_id
    assert d["file_count"]   == 2


def test_05_backup_manager_list_backups():
    tmp = tempfile.mkdtemp()
    wm  = WorkspaceManager(base_dir=tmp)
    ws1 = wm.create_workspace("WS-1")
    ws2 = wm.create_workspace("WS-2")
    wm.write_file(ws1.workspace_id, "a.csv", b"x")
    wm.write_file(ws2.workspace_id, "b.csv", b"y")

    bm = BackupManager(wm)
    b1 = bm.create_backup(ws1.workspace_id, "first")
    b2 = bm.create_backup(ws1.workspace_id, "second")
    bm.create_backup(ws2.workspace_id, "other")

    listed = bm.list_backups(ws1.workspace_id)
    assert len(listed) == 2
    ids = {b.backup_id for b in listed}
    assert ids == {b1.backup_id, b2.backup_id}

    # sorted by created_at
    assert listed[0].label in ("first", "second")


def test_06_backup_manager_restore_backup():
    tmp = tempfile.mkdtemp()
    wm  = WorkspaceManager(base_dir=tmp)
    ws  = wm.create_workspace("Restore WS")
    wm.write_file(ws.workspace_id, "original.csv", b"id,v\n1,100\n")

    bm   = BackupManager(wm)
    info = bm.create_backup(ws.workspace_id, "before_edit")

    # Overwrite the file
    wm.write_file(ws.workspace_id, "original.csv", b"id,v\n1,CHANGED\n")
    assert wm.read_file(ws.workspace_id, "original.csv") == b"id,v\n1,CHANGED\n"

    # Restore
    ok = bm.restore_backup(ws.workspace_id, info.backup_id)
    assert ok is True

    restored = wm.read_file(ws.workspace_id, "original.csv")
    assert restored == b"id,v\n1,100\n"

    # workspace.json must still exist after restore
    assert (Path(ws.root_path) / "workspace.json").exists()


def test_07_backup_manager_delete_backup():
    tmp = tempfile.mkdtemp()
    wm  = WorkspaceManager(base_dir=tmp)
    ws  = wm.create_workspace("Del WS")
    wm.write_file(ws.workspace_id, "x.csv", b"data")

    bm   = BackupManager(wm)
    info = bm.create_backup(ws.workspace_id)

    assert Path(info.backup_path).exists()
    assert bm.delete_backup(info.backup_id) is True
    assert not Path(info.backup_path).exists()

    # Second delete returns False
    assert bm.delete_backup(info.backup_id) is False


def test_08_supervised_agent_autonomous_run_pipeline():
    wm, bridge, agent = _fresh()
    ws = wm.create_workspace("Auto WS")
    wm.write_file(ws.workspace_id, "props.csv", _csv_bytes(
        {"property_id": "P1", "property_type": "residential",
         "area_sqm": "150", "location": "Cairo"},
    ))

    report = agent.run_pipeline(ws.workspace_id, auto_backup=False)

    assert report.status    == "completed"
    assert report.completed == 1
    assert report.failed    == 0
    bridge.evaluate_property.assert_called_once()


def test_09_supervised_agent_readonly_blocks_pipeline():
    wm, bridge, _ = _fresh()
    agent = SupervisedAgent(wm, bridge, execution_mode=ExecutionMode.READONLY)
    ws    = wm.create_workspace("RO WS")

    try:
        agent.run_pipeline(ws.workspace_id)
        assert False, "Expected PermissionError"
    except PermissionError as exc:
        assert "readonly" in str(exc).lower() or "rejected" in str(exc).lower()

    bridge.evaluate_property.assert_not_called()

    # Action log must record the rejection
    log = agent.get_action_log()
    assert any(r.status == "rejected" for r in log)


def test_10_supervised_mode_risky_vs_non_risky():
    tmp    = tempfile.mkdtemp()
    wm     = WorkspaceManager(base_dir=tmp)
    bridge = MagicMock()
    bridge.evaluate_property.return_value = APIResponse(
        success=True, status="success", data={"primary_value": 1_000_000}
    )

    # Approve callback that always approves
    approve_all  = MagicMock(return_value=True)
    reject_all   = MagicMock(return_value=False)

    # SUPERVISED + approve callback → risky action (RUN_PIPELINE) should call callback
    agent = SupervisedAgent(wm, bridge,
                            execution_mode=ExecutionMode.SUPERVISED,
                            approval_callback=approve_all)
    ws = wm.create_workspace("Sup WS")
    wm.write_file(ws.workspace_id, "props.csv", _csv_bytes(
        {"property_id": "P1", "property_type": "residential",
         "area_sqm": "100", "location": "Cairo"},
    ))

    report = agent.run_pipeline(ws.workspace_id, auto_backup=False)
    assert report.status == "completed"
    approve_all.assert_called_once()   # callback invoked for run_pipeline

    # SUPERVISED + reject callback → PermissionError
    agent2 = SupervisedAgent(wm, bridge,
                             execution_mode=ExecutionMode.SUPERVISED,
                             approval_callback=reject_all)
    ws2 = wm.create_workspace("Sup WS 2")
    try:
        agent2.run_pipeline(ws2.workspace_id, auto_backup=False)
        assert False, "Expected PermissionError"
    except PermissionError:
        pass
    reject_all.assert_called_once()


def test_11_manual_mode_every_action_gated():
    tmp    = tempfile.mkdtemp()
    wm     = WorkspaceManager(base_dir=tmp)
    bridge = MagicMock()
    bridge.evaluate_property.return_value = APIResponse(
        success=True, status="success", data={"primary_value": 5_000_000}
    )

    call_count = [0]

    def counting_callback(action_type, details):
        call_count[0] += 1
        return True   # always approve

    agent = SupervisedAgent(wm, bridge,
                            execution_mode=ExecutionMode.MANUAL,
                            approval_callback=counting_callback)
    ws = wm.create_workspace("Manual WS")
    wm.write_file(ws.workspace_id, "props.csv", _csv_bytes(
        {"property_id": "P1", "property_type": "residential",
         "area_sqm": "200", "location": "Giza"},
    ))

    agent.run_pipeline(ws.workspace_id, auto_backup=False)

    # MANUAL mode gates every action — RUN_PIPELINE must have triggered callback
    assert call_count[0] >= 1


def test_12_auto_backup_and_action_log():
    wm, bridge, _ = _fresh()
    agent = SupervisedAgent(wm, bridge, execution_mode=ExecutionMode.AUTONOMOUS)

    ws = wm.create_workspace("Log WS")
    wm.write_file(ws.workspace_id, "props.csv", _csv_bytes(
        {"property_id": "P1", "property_type": "residential",
         "area_sqm": "120", "location": "Cairo"},
        {"property_id": "P2", "property_type": "commercial",
         "area_sqm": "300", "location": "Giza"},
    ))

    report = agent.run_pipeline(ws.workspace_id, auto_backup=True)
    assert report.status == "completed"

    log = agent.get_action_log()
    action_types = [r.action_type for r in log]

    # auto_backup must produce a BACKUP record
    assert ActionType.BACKUP in action_types

    # RUN_PIPELINE must appear in log
    assert ActionType.RUN_PIPELINE in action_types

    # All log entries must have a status
    assert all(r.status in ("approved", "completed", "failed", "rejected")
               for r in log)

    # Backup directory must physically exist
    bm      = agent._backup_mgr
    backups = bm.list_backups(ws.workspace_id)
    assert len(backups) >= 1
    assert backups[0].label == "pre_pipeline"


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
