"""
test_phase_17_e2e.py — Phase 17.0 Local Workspace Agent (12 tests)

Tests:
  01  WorkspaceManager creates base directory + workspace subdirectory
  02  create_workspace returns WorkspaceInfo with correct fields
  03  get_workspace returns same workspace with refreshed stats
  04  list_workspaces shows all created workspaces, sorted by created_at
  05  safe_path blocks path traversal (../ escape attempt)
  06  write_file + read_file roundtrip — bytes preserved exactly
  07  list_files with glob pattern filters correctly
  08  delete_file removes the file, returns False for missing
  09  delete_workspace removes directory and de-indexes
  10  FileScanner.classify_file — all four type buckets + unknown
  11  FileScanner.scan_workspace returns ScannedFile objects, sorted
  12  FileScanner.find_property_files + get_workspace_stats
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_CORE))
os.chdir(str(_CORE))

from agents.workspace_manager import WorkspaceManager, WorkspaceStatus
from agents.file_scanner import FileScanner, FileType


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _manager() -> tuple:
    """Return (WorkspaceManager, tmp_dir_path) using a fresh temp directory."""
    tmp = tempfile.mkdtemp()
    return WorkspaceManager(base_dir=tmp), tmp


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_01_workspace_manager_creates_directory():
    mgr, base = _manager()
    ws = mgr.create_workspace("Test WS")
    assert Path(base).exists()
    root = Path(ws.root_path)
    assert root.exists()
    assert root.parent == Path(base)
    assert (root / "workspace.json").exists()


def test_02_create_workspace_info_fields():
    mgr, _ = _manager()
    ws = mgr.create_workspace("Alpha Portfolio", status=WorkspaceStatus.ACTIVE)
    assert ws.workspace_id
    assert ws.name        == "Alpha Portfolio"
    assert ws.status      == WorkspaceStatus.ACTIVE
    assert ws.created_at
    assert ws.file_count       == 0
    assert ws.total_size_bytes == 0
    d = ws.to_dict()
    assert d["name"] == "Alpha Portfolio"


def test_03_get_workspace_refreshes_stats():
    mgr, _ = _manager()
    ws = mgr.create_workspace("Beta WS")
    # Write a file directly
    mgr.write_file(ws.workspace_id, "data.csv", b"id,value\n1,100\n")
    # get_workspace must reflect the new file
    fetched = mgr.get_workspace(ws.workspace_id)
    assert fetched.file_count       == 1
    assert fetched.total_size_bytes  > 0
    assert fetched.name             == "Beta WS"


def test_04_list_workspaces_sorted():
    mgr, _ = _manager()
    w1 = mgr.create_workspace("First")
    w2 = mgr.create_workspace("Second")
    w3 = mgr.create_workspace("Third")
    listed = mgr.list_workspaces()
    assert len(listed) == 3
    names = [w.name for w in listed]
    assert names == ["First", "Second", "Third"]
    ids = {w.workspace_id for w in listed}
    assert ids == {w1.workspace_id, w2.workspace_id, w3.workspace_id}


def test_05_safe_path_blocks_traversal():
    mgr, _ = _manager()
    ws = mgr.create_workspace("Safe WS")

    # Legal path — must succeed
    legal = mgr.safe_path(ws.workspace_id, "subdir/data.json")
    assert "subdir" in str(legal)

    # Path traversal — must raise
    try:
        mgr.safe_path(ws.workspace_id, "../../etc/passwd")
        assert False, "Expected ValueError for path traversal"
    except ValueError as exc:
        assert "escape" in str(exc).lower() or "outside" in str(exc).lower()

    # Unknown workspace — must raise KeyError
    try:
        mgr.safe_path("no-such-id", "file.txt")
        assert False, "Expected KeyError for unknown workspace"
    except KeyError:
        pass


def test_06_write_read_roundtrip():
    mgr, _ = _manager()
    ws = mgr.create_workspace("RW WS")

    content = b"property_id,value\nP1,5000000\nP2,8000000\n"
    written = mgr.write_file(ws.workspace_id, "properties.csv", content)
    assert written == len(content)

    read_back = mgr.read_file(ws.workspace_id, "properties.csv")
    assert read_back == content

    # Nested path — parent dirs created automatically
    mgr.write_file(ws.workspace_id, "reports/2024/jan.txt", b"report data")
    assert mgr.read_file(ws.workspace_id, "reports/2024/jan.txt") == b"report data"


def test_07_list_files_with_pattern():
    mgr, _ = _manager()
    ws = mgr.create_workspace("List WS")
    mgr.write_file(ws.workspace_id, "a.csv",  b"csv1")
    mgr.write_file(ws.workspace_id, "b.csv",  b"csv2")
    mgr.write_file(ws.workspace_id, "c.xlsx", b"xlsx1")
    mgr.write_file(ws.workspace_id, "d.json", b"{}")

    all_files = mgr.list_files(ws.workspace_id)
    assert len(all_files) == 4

    csv_only = mgr.list_files(ws.workspace_id, "*.csv")
    assert len(csv_only) == 2
    assert all(f.endswith(".csv") for f in csv_only)


def test_08_delete_file():
    mgr, _ = _manager()
    ws = mgr.create_workspace("Del WS")
    mgr.write_file(ws.workspace_id, "target.txt", b"delete me")

    assert mgr.delete_file(ws.workspace_id, "target.txt") is True
    assert mgr.delete_file(ws.workspace_id, "target.txt") is False  # already gone

    try:
        mgr.read_file(ws.workspace_id, "target.txt")
        assert False, "Expected FileNotFoundError"
    except FileNotFoundError:
        pass


def test_09_delete_workspace():
    mgr, _ = _manager()
    ws = mgr.create_workspace("Temp WS")
    mgr.write_file(ws.workspace_id, "keep.txt", b"data")
    root = Path(ws.root_path)

    assert mgr.delete_workspace(ws.workspace_id) is True
    assert not root.exists()
    assert mgr.get_workspace(ws.workspace_id) is None
    assert mgr.delete_workspace(ws.workspace_id) is False  # already removed


def test_10_file_scanner_classify_file():
    clf = FileScanner.classify_file

    assert clf(Path("data.xlsx"))   == FileType.PROPERTY_DATA
    assert clf(Path("data.xls"))    == FileType.PROPERTY_DATA
    assert clf(Path("data.csv"))    == FileType.PROPERTY_DATA
    assert clf(Path("data.json"))   == FileType.PROPERTY_DATA

    assert clf(Path("report.pdf"))  == FileType.REPORT
    assert clf(Path("report.docx")) == FileType.REPORT

    assert clf(Path("config.yaml")) == FileType.CONFIG
    assert clf(Path("config.yml"))  == FileType.CONFIG
    assert clf(Path("config.toml")) == FileType.CONFIG

    assert clf(Path("photo.png"))   == FileType.IMAGE
    assert clf(Path("photo.jpg"))   == FileType.IMAGE

    assert clf(Path("notes.txt"))   == FileType.UNKNOWN
    assert clf(Path("script.py"))   == FileType.UNKNOWN


def test_11_scan_workspace_returns_sorted_files():
    mgr, _ = _manager()
    ws = mgr.create_workspace("Scan WS")
    mgr.write_file(ws.workspace_id, "z_last.csv",   b"z")
    mgr.write_file(ws.workspace_id, "a_first.xlsx", b"a")
    mgr.write_file(ws.workspace_id, "m_mid.json",   b"{}")

    scanner = FileScanner()
    files   = scanner.scan_workspace(ws.root_path)

    assert len(files) == 3
    names = [f.name for f in files]
    assert names == sorted(names)    # alphabetical by relative_path

    f0 = files[0]
    assert f0.extension    in (".csv", ".json", ".xlsx")
    assert f0.size_bytes    > 0
    assert f0.modified_at          # non-empty ISO timestamp
    assert f0.absolute_path        # absolute path present
    assert f0.file_type == FileType.PROPERTY_DATA


def test_12_find_property_files_and_stats():
    mgr, _ = _manager()
    ws = mgr.create_workspace("Stats WS")
    mgr.write_file(ws.workspace_id, "props.csv",    b"id,v\n1,100\n")
    mgr.write_file(ws.workspace_id, "report.pdf",   b"%PDF")
    mgr.write_file(ws.workspace_id, "config.yaml",  b"key: value")
    mgr.write_file(ws.workspace_id, "data.xlsx",    b"PK")
    mgr.write_file(ws.workspace_id, "photo.png",    b"\x89PNG")

    scanner = FileScanner()

    # find_property_files
    pf = scanner.find_property_files(ws.root_path)
    assert len(pf) == 2
    assert all(f.file_type == FileType.PROPERTY_DATA for f in pf)

    # get_workspace_stats
    stats = scanner.get_workspace_stats(ws.root_path)
    assert stats["total_files"]         == 5
    assert stats["property_data_files"] == 2
    assert stats["total_size_bytes"]     > 0
    assert stats["by_type"][FileType.REPORT]        == 1
    assert stats["by_type"][FileType.CONFIG]        == 1
    assert stats["by_type"][FileType.IMAGE]         == 1
    assert stats["largest_file"] is not None


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
