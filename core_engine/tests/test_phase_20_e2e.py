"""
test_phase_20_e2e.py — Phase 20.0 Folder Watcher (12 tests)

Tests:
  01  WatchEventType enum — all 3 values
  02  FileEvent dataclass — fields and to_dict()
  03  FileWatcher start / stop — is_running transitions
  04  FileWatcher detects CREATED event when a new file appears
  05  FileWatcher detects MODIFIED event when a file's content changes
  06  FileWatcher detects DELETED event when a file is removed
  07  FileWatcher extension filter — .txt files are ignored
  08  FileWatcher callback exception is swallowed (watcher stays alive)
  09  WatcherManager.watch registers watcher — list_watched returns ids
  10  WatcherManager.unwatch stops watcher; returns False for unknown id
  11  WatcherManager.stop_all stops every active watcher
  12  make_pipeline_trigger calls agent.run_pipeline on CREATED event
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

_CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_CORE))
os.chdir(str(_CORE))

from agents.file_watcher import (
    WatchEventType, FileEvent, FileWatcher, WatcherManager,
)

# Short poll interval for deterministic tests
_POLL = 0.05   # 50 ms
_WAIT = 0.25   # 250 ms — enough for ≥ 1 poll cycle to run


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tmp_dir() -> Path:
    return Path(tempfile.mkdtemp())


def _write(path: Path, content: bytes = b"data") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _collect_events(workspace_id: str, workspace_path: Path) -> tuple:
    """Return (events_list, FileWatcher) with poll_interval=_POLL."""
    events = []
    watcher = FileWatcher(
        workspace_id, workspace_path,
        callback=events.append,
        poll_interval=_POLL,
    )
    return events, watcher


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_01_watch_event_type_enum():
    assert WatchEventType.CREATED  == "created"
    assert WatchEventType.MODIFIED == "modified"
    assert WatchEventType.DELETED  == "deleted"
    vals = {e.value for e in WatchEventType}
    assert vals == {"created", "modified", "deleted"}


def test_02_file_event_dataclass():
    evt = FileEvent(
        event_type=WatchEventType.CREATED,
        workspace_id="ws-1",
        relative_path="data.csv",
        absolute_path="/tmp/ws-1/data.csv",
        detected_at="2026-05-08T10:00:00",
    )
    assert evt.event_type    == "created"
    assert evt.workspace_id  == "ws-1"
    assert evt.relative_path == "data.csv"
    assert evt.detected_at   == "2026-05-08T10:00:00"

    d = evt.to_dict()
    assert d["event_type"]    == "created"
    assert d["workspace_id"]  == "ws-1"
    assert d["relative_path"] == "data.csv"
    assert d["absolute_path"] == "/tmp/ws-1/data.csv"
    assert d["detected_at"]   == "2026-05-08T10:00:00"


def test_03_file_watcher_start_stop():
    root = _tmp_dir()
    events, watcher = _collect_events("ws-st", root)

    assert watcher.is_running is False

    watcher.start()
    assert watcher.is_running is True

    watcher.stop()
    assert watcher.is_running is False


def test_04_file_watcher_detects_created():
    root = _tmp_dir()
    events, watcher = _collect_events("ws-cr", root)
    watcher.start()

    _write(root / "new_file.csv", b"id,value\n1,100\n")
    time.sleep(_WAIT)
    watcher.stop()

    created = [e for e in events if e.event_type == WatchEventType.CREATED]
    assert len(created) >= 1
    assert any("new_file.csv" in e.relative_path for e in created)
    assert created[0].workspace_id == "ws-cr"
    assert created[0].detected_at  # non-empty timestamp


def test_05_file_watcher_detects_modified():
    root = _tmp_dir()
    existing = root / "existing.csv"
    _write(existing, b"original content")

    events, watcher = _collect_events("ws-mod", root)
    watcher.start()

    # Wait for initial snapshot to be taken, then modify
    time.sleep(_WAIT)
    _write(existing, b"new content that changes mtime")
    # Touch mtime explicitly to guarantee the OS reflects the change
    existing.touch()
    time.sleep(_WAIT)
    watcher.stop()

    modified = [e for e in events if e.event_type == WatchEventType.MODIFIED]
    assert len(modified) >= 1
    assert any("existing.csv" in e.relative_path for e in modified)


def test_06_file_watcher_detects_deleted():
    root = _tmp_dir()
    target = root / "to_delete.json"
    _write(target, b'{"id": 1}')

    events, watcher = _collect_events("ws-del", root)
    watcher.start()

    time.sleep(_WAIT)
    target.unlink()
    time.sleep(_WAIT)
    watcher.stop()

    deleted = [e for e in events if e.event_type == WatchEventType.DELETED]
    assert len(deleted) >= 1
    assert any("to_delete.json" in e.relative_path for e in deleted)


def test_07_file_watcher_extension_filter():
    root = _tmp_dir()
    events, watcher = _collect_events("ws-ext", root)
    watcher.start()

    # .txt should be ignored; .csv should be tracked
    _write(root / "ignored.txt", b"plain text")
    _write(root / "tracked.csv", b"id,v\n1,1\n")
    time.sleep(_WAIT)
    watcher.stop()

    paths = [e.relative_path for e in events]
    assert any("tracked.csv" in p for p in paths)
    assert not any("ignored.txt" in p for p in paths)


def test_08_file_watcher_callback_error_is_swallowed():
    root = _tmp_dir()
    call_count = [0]

    def bad_callback(event: FileEvent) -> None:
        call_count[0] += 1
        raise RuntimeError("intentional callback error")

    watcher = FileWatcher("ws-err", root, callback=bad_callback, poll_interval=_POLL)
    watcher.start()

    _write(root / "trigger.csv", b"x")
    time.sleep(_WAIT)

    # Watcher must still be alive despite callback exceptions
    assert watcher.is_running is True
    watcher.stop()
    assert call_count[0] >= 1    # callback was invoked at least once


def test_09_watcher_manager_watch_and_list():
    mgr   = WatcherManager()
    root1 = _tmp_dir()
    root2 = _tmp_dir()

    assert mgr.list_watched() == []

    mgr.watch("ws-a", root1, lambda e: None, poll_interval=_POLL)
    mgr.watch("ws-b", root2, lambda e: None, poll_interval=_POLL)

    listed = mgr.list_watched()
    assert set(listed) == {"ws-a", "ws-b"}

    mgr.stop_all()


def test_10_watcher_manager_unwatch():
    mgr  = WatcherManager()
    root = _tmp_dir()

    mgr.watch("ws-x", root, lambda e: None, poll_interval=_POLL)
    assert "ws-x" in mgr.list_watched()

    assert mgr.unwatch("ws-x") is True
    assert "ws-x" not in mgr.list_watched()

    # Stopping a non-existent watcher returns False
    assert mgr.unwatch("ws-x")        is False
    assert mgr.unwatch("no-such-id")  is False


def test_11_watcher_manager_stop_all():
    mgr = WatcherManager()
    roots = [_tmp_dir() for _ in range(3)]
    for i, r in enumerate(roots):
        mgr.watch(f"ws-{i}", r, lambda e: None, poll_interval=_POLL)

    assert len(mgr.list_watched()) == 3

    mgr.stop_all()
    assert mgr.list_watched() == []


def test_12_make_pipeline_trigger():
    mgr   = WatcherManager()
    root  = _tmp_dir()

    agent = MagicMock()
    agent.run_pipeline.return_value = MagicMock(status="completed")

    callback = mgr.make_pipeline_trigger(agent, "ws-trig", primary_purpose="market_value")

    # CREATED event → must trigger run_pipeline
    created_evt = FileEvent(
        event_type=WatchEventType.CREATED,
        workspace_id="ws-trig",
        relative_path="props.csv",
        absolute_path=str(root / "props.csv"),
        detected_at=__import__("datetime").datetime.now().isoformat(),
    )
    callback(created_evt)
    agent.run_pipeline.assert_called_once_with(
        "ws-trig", primary_purpose="market_value", auto_backup=False
    )

    # MODIFIED event → must NOT trigger run_pipeline again
    modified_evt = FileEvent(
        event_type=WatchEventType.MODIFIED,
        workspace_id="ws-trig",
        relative_path="props.csv",
        absolute_path=str(root / "props.csv"),
        detected_at=__import__("datetime").datetime.now().isoformat(),
    )
    callback(modified_evt)
    agent.run_pipeline.assert_called_once()   # still only 1 call

    # DELETED event → no additional call
    deleted_evt = FileEvent(
        event_type=WatchEventType.DELETED,
        workspace_id="ws-trig",
        relative_path="props.csv",
        absolute_path=str(root / "props.csv"),
        detected_at=__import__("datetime").datetime.now().isoformat(),
    )
    callback(deleted_evt)
    agent.run_pipeline.assert_called_once()   # still 1 call


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
