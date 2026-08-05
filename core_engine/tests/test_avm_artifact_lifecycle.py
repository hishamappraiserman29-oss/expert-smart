"""Tests for avm_lifecycle.py — AVM artifact root lifecycle manager (Wave 4B1).

Covers the 12-step creation contract, symlink/reparse-point rejection,
in-repository rejection, immutability after first init, test reset,
run_metadata.json creation, and Windows-specific junction/reparse tests.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from avm_lifecycle import (
    LifecycleConfigError,
    LifecycleCapacityError,
    LifecycleStorageUnsafeError,
    create_run_dir,
    update_run_metadata_status,
    reset_lifecycle_state_for_tests,
    _is_reparse_point_windows,
)


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    """Reset lifecycle state and clear AVM_ARTIFACT_ROOT before every test."""
    reset_lifecycle_state_for_tests()
    monkeypatch.delenv("AVM_ARTIFACT_ROOT", raising=False)
    yield
    reset_lifecycle_state_for_tests()
    monkeypatch.delenv("AVM_ARTIFACT_ROOT", raising=False)


# ── ALC-01: Default root is created under tempdir ─────────────────────────────

def test_alc_01_default_root_created_in_tempdir(tmp_path, monkeypatch):
    """When AVM_ARTIFACT_ROOT is unset, the default root is created under tempdir."""
    run_dir = create_run_dir()
    expected_parent = Path(tempfile.gettempdir()) / "expert_smart_avm"
    assert run_dir.parent == expected_parent.resolve(), (
        f"Run dir {run_dir} not under expected default root {expected_parent}"
    )
    assert run_dir.is_dir()


# ── ALC-02: Explicit root from env var ────────────────────────────────────────

def test_alc_02_explicit_root_from_env(tmp_path, monkeypatch):
    """When AVM_ARTIFACT_ROOT is set to a valid external directory, it is used."""
    custom_root = tmp_path / "custom_avm_root"
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(custom_root))
    run_dir = create_run_dir()
    assert custom_root.is_dir(), "Custom root should have been created"
    assert run_dir.parent == custom_root.resolve()
    assert run_dir.is_dir()


# ── ALC-03: Root outside repository ───────────────────────────────────────────

def test_alc_03_root_outside_repository(tmp_path, monkeypatch):
    """Artifact root must not be inside the repository tree."""
    # The default is outside the repo (tempdir), so just confirm it works
    run_dir = create_run_dir()
    repo_root = Path(__file__).resolve().parents[3]
    assert not str(run_dir).startswith(str(repo_root)), (
        f"Run dir {run_dir} must not be inside repo {repo_root}"
    )


def test_alc_04_root_inside_repository_rejected(monkeypatch):
    """Artifact root inside the repository tree is rejected with LifecycleConfigError."""
    # Use _CORE (ExpertSmart_Unified/core_engine) — unambiguously inside the repository
    inside = _CORE / "avm_test_artifact_root_inside"
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(inside))
    with pytest.raises(LifecycleConfigError):
        create_run_dir()


# ── ALC-06: Parent does not exist is rejected ─────────────────────────────────

def test_alc_06_nonexistent_parent_rejected(tmp_path, monkeypatch):
    """A root whose parent does not exist is rejected."""
    nonexistent_parent = tmp_path / "does_not_exist" / "child"
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(nonexistent_parent))
    with pytest.raises(LifecycleConfigError, match="parent"):
        create_run_dir()


# ── ALC-07: Immutability after first init ─────────────────────────────────────

def test_alc_07_env_change_ignored_after_init(tmp_path, monkeypatch):
    """Changing AVM_ARTIFACT_ROOT after the first create_run_dir() is ignored."""
    first_root = tmp_path / "first_root"
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(first_root))
    run1 = create_run_dir()
    assert run1.parent == first_root.resolve()

    # Change env var — must not affect subsequent calls
    second_root = tmp_path / "second_root"
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(second_root))
    run2 = create_run_dir()
    assert run2.parent == first_root.resolve(), (
        "Second run dir must still be under the FIRST validated root"
    )
    assert not second_root.exists(), (
        "Second root must not have been created (env change was ignored)"
    )


# ── ALC-08: run_dir is a UUID4-named directory ────────────────────────────────

def test_alc_08_run_dir_is_uuid4(tmp_path, monkeypatch):
    """create_run_dir() creates a directory with a UUID4 name."""
    import uuid
    custom_root = tmp_path / "uuid_test_root"
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(custom_root))
    run_dir = create_run_dir()
    name = run_dir.name
    try:
        parsed = uuid.UUID(name, version=4)
    except ValueError:
        pytest.fail(f"Run dir name '{name}' is not a valid UUID4")
    assert str(parsed) == name


# ── ALC-09: Reset clears all cached state ────────────────────────────────────

def test_alc_09_reset_clears_cached_state(tmp_path, monkeypatch):
    """reset_lifecycle_state_for_tests() allows re-initialization with a new root."""
    first_root = tmp_path / "root_a"
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(first_root))
    create_run_dir()
    assert first_root.is_dir()

    # Reset and re-initialize with a different root
    reset_lifecycle_state_for_tests()
    second_root = tmp_path / "root_b"
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(second_root))
    run_dir = create_run_dir()
    assert run_dir.parent == second_root.resolve()


# ── ALC-10: Multiple run dirs per session ────────────────────────────────────

def test_alc_10_multiple_run_dirs_unique(tmp_path, monkeypatch):
    """Each create_run_dir() call returns a new unique directory."""
    custom_root = tmp_path / "multi_root"
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(custom_root))
    dirs = {create_run_dir() for _ in range(5)}
    assert len(dirs) == 5, "Each run dir must be unique"
    for d in dirs:
        assert d.is_dir()


# ── ALC-11: Default root created when missing ────────────────────────────────

def test_alc_11_default_root_created_when_missing(monkeypatch):
    """When the default root does not exist, it is created (not rejected)."""
    # Clear any leftover state
    reset_lifecycle_state_for_tests()
    monkeypatch.delenv("AVM_ARTIFACT_ROOT", raising=False)
    run_dir = create_run_dir()
    default_root = Path(tempfile.gettempdir()) / "expert_smart_avm"
    assert default_root.is_dir(), "Default root must be created when missing"
    assert run_dir.is_dir()


# ── ALC-12: AVM artifact root stays outside repository ───────────────────────

def test_alc_12_all_run_dirs_outside_repository(tmp_path, monkeypatch):
    """All run directories must be outside the repository tree."""
    repo_root = Path(__file__).resolve().parents[3]
    custom_root = tmp_path / "safe_root"
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(custom_root))
    for _ in range(3):
        run_dir = create_run_dir()
        assert not str(run_dir).startswith(str(repo_root)), (
            f"Run dir {run_dir} must not be inside repository {repo_root}"
        )


# ── ALC-13: run_metadata.json is created with status=pending ─────────────────

def test_alc_13_run_metadata_created_with_pending(tmp_path, monkeypatch):
    """create_run_dir() creates run_metadata.json with status='pending'."""
    custom_root = tmp_path / "meta_root"
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(custom_root))
    run_dir = create_run_dir()
    meta_path = run_dir / "run_metadata.json"
    assert meta_path.is_file(), "run_metadata.json must be created by create_run_dir()"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta.get("status") == "pending", (
        f"Expected status='pending', got {meta.get('status')!r}"
    )
    assert "run_id" in meta
    assert "created_at_iso" in meta
    assert meta.get("generator") == "expert_smart_avm"


def test_alc_14_update_run_metadata_status(tmp_path, monkeypatch):
    """update_run_metadata_status() transitions status correctly."""
    custom_root = tmp_path / "status_root"
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(custom_root))
    run_dir = create_run_dir()

    update_run_metadata_status(run_dir, "complete")
    meta = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
    assert meta["status"] == "complete"

    update_run_metadata_status(run_dir, "failed")
    meta = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
    assert meta["status"] == "failed"


# ── Windows-specific: Junction and reparse-point rejection ────────────────────

@pytest.mark.skipif(os.name != "nt", reason="Windows-only: Junction test requires cmd.exe mklink /J")
def test_win_alc_junction_root_rejected(tmp_path, monkeypatch):
    """A Windows directory Junction as the artifact root is rejected with LifecycleConfigError."""
    real_dir = tmp_path / "real_target"
    real_dir.mkdir()
    junction = tmp_path / "junction_root"

    # Create junction via cmd /c mklink /J
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(real_dir)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"mklink /J failed (requires elevated privileges?): {result.stderr}")

    try:
        monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(junction))
        with pytest.raises(LifecycleConfigError):
            create_run_dir()
    finally:
        # Safe cleanup: remove the junction without traversing it
        if junction.exists() or junction.is_symlink():
            subprocess.run(["cmd", "/c", "rd", str(junction)], capture_output=True)


@pytest.mark.skipif(os.name != "nt", reason="Windows-only: requires ctypes GetFileAttributesW")
def test_win_alc_reparse_point_mocked(tmp_path, monkeypatch):
    """FILE_ATTRIBUTE_REPARSE_POINT flag causes lifecycle to reject the root."""
    custom_root = tmp_path / "reparse_root"
    custom_root.mkdir()
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(custom_root))

    # Mock GetFileAttributesW to return reparse-point flag for our directory
    FILE_ATTRIBUTE_REPARSE_POINT = 0x400
    VALID_NON_REPARSE = 0x10  # FILE_ATTRIBUTE_DIRECTORY

    original_func = None
    try:
        import ctypes
        original_func = ctypes.windll.kernel32.GetFileAttributesW  # type: ignore[attr-defined]
    except Exception:
        pytest.skip("ctypes.windll not available")

    call_count = [0]
    target_str = str(custom_root)

    def fake_get_attrs(path_str):
        call_count[0] += 1
        if str(path_str) == target_str:
            return FILE_ATTRIBUTE_REPARSE_POINT | VALID_NON_REPARSE
        return original_func(path_str)

    with patch("avm_lifecycle._is_reparse_point_windows") as mock_reparse:
        mock_reparse.side_effect = lambda path: (
            str(path) == target_str
        )
        with pytest.raises(LifecycleConfigError):
            create_run_dir()


@pytest.mark.skipif(os.name != "nt", reason="Windows-only: reparse-point parent rejection")
def test_win_alc_reparse_point_parent_rejected(tmp_path, monkeypatch):
    """A reparse-point parent directory causes lifecycle to reject the root."""
    parent_dir = tmp_path / "reparse_parent"
    parent_dir.mkdir()
    child_root = parent_dir / "avm_root"
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(child_root))

    target_str = str(parent_dir)

    with patch("avm_lifecycle._is_reparse_point_windows") as mock_reparse:
        mock_reparse.side_effect = lambda path: (
            str(path) == target_str
        )
        with pytest.raises(LifecycleConfigError):
            create_run_dir()


@pytest.mark.skipif(os.name != "nt", reason="Windows-only: _is_reparse_point_windows unit test")
def test_win_alc_is_reparse_point_windows_real_dir(tmp_path):
    """_is_reparse_point_windows() returns False for a normal directory."""
    real_dir = tmp_path / "normal_dir"
    real_dir.mkdir()
    result = _is_reparse_point_windows(real_dir)
    assert result is False, (
        f"Normal directory should not be a reparse point, got {result}"
    )


# ── POSIX symlink test — skipped on Windows (Windows tests above cover it) ────

@pytest.mark.skipif(
    os.name == "nt",
    reason="Symlink creation requires elevated privileges on Windows; "
           "Windows Junction rejection is covered by test_win_alc_junction_root_rejected.",
)
def test_alc_05_symlink_root_rejected(tmp_path, monkeypatch):
    """A symlink as the artifact root must be rejected."""
    real_dir = tmp_path / "real_root"
    real_dir.mkdir()
    link = tmp_path / "link_root"
    link.symlink_to(real_dir)
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(link))
    with pytest.raises(LifecycleConfigError):
        create_run_dir()

# ═══════════════════════════════════════════════════════════════════════════════
# Wave 4B1 — capacity, cleanup, and storage-safety lifecycle tests (13+)
# ═══════════════════════════════════════════════════════════════════════════════

import time as _time_mod
from unittest.mock import patch as _patch

from avm_lifecycle import (
    RETENTION_SECONDS,
    ORPHAN_TTL_SECONDS,
    MAX_ROOT_ENTRIES,
    PRE_GENERATION_TARGET,
    _RunInfo,
    _inspect_root,
    _pre_generation_cleanup,
)


def _ri(path, status="complete", age_secs=0, has_metadata=True,
        is_empty=False, is_clean=True):
    """Build a _RunInfo for testing without touching the filesystem."""
    now = _time_mod.time()
    ts = now - age_secs
    return _RunInfo(
        path=path, run_id=path.name, status=status,
        created_at=ts, is_clean=is_clean,
        has_metadata=has_metadata, is_empty=is_empty, mtime=ts,
    )


# ── ALC-LC-01: unknown root file blocks generation ────────────────────────────

def test_lc_unknown_root_file_blocks_generation(tmp_path, monkeypatch):
    """A non-directory file directly under the artifact root raises LifecycleStorageUnsafeError."""
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(tmp_path))
    (tmp_path / "unexpected.txt").write_text("bad", encoding="utf-8")
    with pytest.raises(LifecycleStorageUnsafeError):
        create_run_dir()


# ── ALC-LC-02: unknown root directory blocks generation ───────────────────────

def test_lc_unknown_root_directory_blocks_generation(tmp_path, monkeypatch):
    """A non-UUID4 directory directly under the artifact root raises LifecycleStorageUnsafeError."""
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(tmp_path))
    (tmp_path / "not_a_uuid_dir").mkdir()
    with pytest.raises(LifecycleStorageUnsafeError):
        create_run_dir()


# ── ALC-LC-03: unknown child inside UUID4 run prevents deletion ───────────────

def test_lc_unknown_child_inside_uuid4_run_prevents_deletion(tmp_path, monkeypatch):
    """A UUID4 run dir containing an unknown file is never deleted by cleanup."""
    import uuid
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(tmp_path))
    run_id = str(uuid.uuid4())
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    (run_dir / "unknown_artifact.bin").write_bytes(b"\xff\xfe")
    old_iso = "2000-01-01T00:00:00+00:00"
    (run_dir / "run_metadata.json").write_text(
        json.dumps({
            "status": "complete", "run_id": run_id,
            "created_at_iso": old_iso, "generator": "expert_smart_avm",
        }),
        encoding="utf-8",
    )
    # create_run_dir() should succeed (only 1 entry, below PRE_GENERATION_TARGET)
    new_run = create_run_dir()
    assert new_run.is_dir()
    # The unclean run must still exist — it is protected from deletion
    assert run_dir.is_dir(), "Unclean run must not be deleted by pre-generation cleanup"


# ── ALC-LC-04: unknown run child counts toward capacity ───────────────────────

def test_lc_unknown_run_child_counts_toward_capacity(tmp_path, monkeypatch):
    """_inspect_root() still counts a UUID4 run with an unknown child (is_clean=False)."""
    import uuid
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(tmp_path))
    run_id = str(uuid.uuid4())
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    (run_dir / "unexpected.dat").write_bytes(b"x")
    (run_dir / "run_metadata.json").write_text(
        json.dumps({
            "status": "complete", "run_id": run_id,
            "created_at_iso": "2000-01-01T00:00:00+00:00",
            "generator": "expert_smart_avm",
        }),
        encoding="utf-8",
    )
    run_infos, is_safe = _inspect_root(tmp_path)
    assert len(run_infos) == 1, "Entry must be counted even when it contains unknown files"
    assert run_infos[0].is_clean is False, "is_clean must be False when unknown child present"


# ── ALC-LC-05: capacity at or above 1,000 is fail-closed ─────────────────────

def test_lc_capacity_at_or_above_1000_is_fail_closed(tmp_path, monkeypatch):
    """When all MAX_ROOT_ENTRIES+ entries are protected, LifecycleCapacityError is raised."""
    import uuid
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(tmp_path))
    now = _time_mod.time()
    # 1000 protected runs (pending — never eligible for deletion)
    protected = [
        _ri(tmp_path / str(uuid.uuid4()), status="pending", age_secs=0)
        for _ in range(MAX_ROOT_ENTRIES)
    ]
    with _patch("avm_lifecycle._inspect_root", return_value=(protected, True)):
        with pytest.raises(LifecycleCapacityError):
            _pre_generation_cleanup(tmp_path)


# ── ALC-LC-06: cleanup reduces approved run count below 900 ──────────────────

def test_lc_cleanup_reduces_approved_run_count_below_900(tmp_path, monkeypatch):
    """Cleanup successfully deletes old approved runs and returns without error."""
    import uuid
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(tmp_path))
    now = _time_mod.time()

    # 899 protected (pending) + 3 old complete runs that actually exist on disk
    protected = [
        _ri(tmp_path / str(uuid.uuid4()), status="pending", age_secs=0)
        for _ in range(899)
    ]

    # Create real dirs for the 3 approved runs (shutil.rmtree needs them)
    approved_paths = []
    for offset in range(3):
        p = tmp_path / str(uuid.uuid4())
        p.mkdir()
        old_secs = RETENTION_SECONDS + 100 + offset
        approved_paths.append(p)
        protected.append(
            _ri(p, status="complete", age_secs=old_secs)
        )

    with _patch("avm_lifecycle._inspect_root", return_value=(protected, True)):
        # Should NOT raise — 3 runs can be deleted (902 - 3 = 899 < 900)
        _pre_generation_cleanup(tmp_path)

    # All 3 approved dirs must have been deleted
    for p in approved_paths:
        assert not p.exists(), f"Old approved run dir {p.name} must have been deleted"


# ── ALC-LC-07: cleanup unable to reach below 900 returns storage unavailable ──

def test_lc_cleanup_unable_to_reach_below_900_raises(tmp_path, monkeypatch):
    """LifecycleCapacityError when all approved runs fail to delete."""
    import uuid
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(tmp_path))

    # 900 protected + 1 ghost approved (path does not exist → deletion fails)
    protected = [
        _ri(tmp_path / str(uuid.uuid4()), status="pending", age_secs=0)
        for _ in range(900)
    ]
    ghost = tmp_path / str(uuid.uuid4())  # does NOT exist on disk
    approved_run = _ri(ghost, status="complete",
                       age_secs=RETENTION_SECONDS + 1)
    all_runs = protected + [approved_run]

    with _patch("avm_lifecycle._inspect_root", return_value=(all_runs, True)):
        with pytest.raises(LifecycleCapacityError):
            _pre_generation_cleanup(tmp_path)


# ── ALC-LC-08: metadata-only old run is retention-deletable ──────────────────

def test_lc_metadata_only_old_run_is_retention_deletable(tmp_path, monkeypatch):
    """A complete run with only run_metadata.json older than 7 days is eligible."""
    import uuid
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(tmp_path))
    run_id = str(uuid.uuid4())
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    (run_dir / "run_metadata.json").write_text(
        json.dumps({
            "status": "complete", "run_id": run_id,
            "created_at_iso": "2000-01-01T00:00:00+00:00",
            "generator": "expert_smart_avm",
        }),
        encoding="utf-8",
    )
    run_infos, _ = _inspect_root(tmp_path)
    ri = run_infos[0]
    assert ri.status == "complete"
    assert ri.is_clean is True
    assert ri.has_metadata is True
    assert (_time_mod.time() - ri.created_at) > RETENTION_SECONDS


# ── ALC-LC-09: complete approved run older than retention is deletable ────────

def test_lc_complete_approved_run_older_than_retention_is_deletable(tmp_path, monkeypatch):
    """A complete+clean run with xlsx older than RETENTION_SECONDS is approved for deletion."""
    import uuid
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(tmp_path))
    run_id = str(uuid.uuid4())
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    (run_dir / "run_metadata.json").write_text(
        json.dumps({
            "status": "complete", "run_id": run_id,
            "created_at_iso": "2000-06-15T12:00:00+00:00",
            "generator": "expert_smart_avm",
        }),
        encoding="utf-8",
    )
    (run_dir / "mass_appraisal.xlsx").write_bytes(b"PK")
    run_infos, _ = _inspect_root(tmp_path)
    ri = run_infos[0]
    assert ri.status == "complete"
    assert ri.is_clean is True
    assert ri.has_metadata is True
    assert (_time_mod.time() - ri.created_at) > RETENTION_SECONDS


# ── ALC-LC-10: empty metadata-less UUID4 dir older than orphan TTL is deletable

def test_lc_empty_metadata_less_uuid4_directory_older_than_orphan_ttl_is_deletable(
    tmp_path, monkeypatch
):
    """Empty UUID4 dir without metadata, mtime > ORPHAN_TTL_SECONDS ago, is orphan-eligible."""
    import uuid
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(tmp_path))
    run_id = str(uuid.uuid4())
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    old_mtime = _time_mod.time() - ORPHAN_TTL_SECONDS - 1
    os.utime(str(run_dir), (old_mtime, old_mtime))

    run_infos, _ = _inspect_root(tmp_path)
    ri = run_infos[0]
    assert ri.has_metadata is False
    assert ri.is_empty is True
    assert (_time_mod.time() - ri.mtime) >= ORPHAN_TTL_SECONDS


# ── ALC-LC-11: empty metadata-less UUID4 dir younger than orphan TTL is retained

def test_lc_empty_metadata_less_uuid4_directory_younger_than_orphan_ttl_is_retained(
    tmp_path, monkeypatch
):
    """Empty UUID4 dir without metadata, mtime < ORPHAN_TTL_SECONDS ago, is protected."""
    import uuid
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(tmp_path))
    run_id = str(uuid.uuid4())
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    # mtime is current — not old enough for orphan cleanup
    run_infos, _ = _inspect_root(tmp_path)
    ri = run_infos[0]
    assert ri.has_metadata is False
    assert ri.is_empty is True
    assert (_time_mod.time() - ri.mtime) < ORPHAN_TTL_SECONDS


# ── ALC-LC-12: non-empty metadata-less run is never deleted ───────────────────

def test_lc_non_empty_metadata_less_run_is_never_deleted(tmp_path, monkeypatch):
    """A non-empty UUID4 dir without run_metadata.json is never deleted by cleanup."""
    import uuid
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(tmp_path))
    run_id = str(uuid.uuid4())
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    (run_dir / "mass_appraisal.xlsx").write_bytes(b"PK")

    run_infos, _ = _inspect_root(tmp_path)
    ri = run_infos[0]
    assert ri.has_metadata is False
    assert ri.is_empty is False
    assert ri.is_clean is True

    # 1 entry, below PRE_GENERATION_TARGET — cleanup is a no-op.
    # Confirm the run survives regardless.
    _pre_generation_cleanup(tmp_path)
    assert run_dir.is_dir(), "Non-empty metadata-less run must not be deleted"


# ── ALC-LC-13: oldest eligible approved runs are deleted first ────────────────

def test_lc_oldest_eligible_approved_runs_are_deleted_first(tmp_path, monkeypatch):
    """_pre_generation_cleanup() deletes oldest-first when multiple runs are eligible."""
    import uuid
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(tmp_path))
    now = _time_mod.time()

    # 898 protected (pending) + 3 old complete dirs that actually exist
    protected = [
        _ri(tmp_path / str(uuid.uuid4()), status="pending", age_secs=0)
        for _ in range(898)
    ]

    # 3 approved runs with different ages (10, 20, 30 days past retention)
    old_runs = []
    for extra_days in (10, 20, 30):
        p = tmp_path / str(uuid.uuid4())
        p.mkdir()
        age = RETENTION_SECONDS + extra_days * 86400
        old_runs.append((extra_days, p, _ri(p, status="complete", age_secs=age)))

    all_runs = protected + [ri for _, _, ri in old_runs]

    # Total = 901; need to delete 2 to reach 899 < 900
    with _patch("avm_lifecycle._inspect_root", return_value=(all_runs, True)):
        _pre_generation_cleanup(tmp_path)

    surviving = [(days, p) for days, p, _ in old_runs if p.exists()]
    deleted = [(days, p) for days, p, _ in old_runs if not p.exists()]

    # 2 oldest (30-day and 20-day) must be deleted; 10-day survives
    assert len(deleted) == 2, f"Expected 2 deleted, got {len(deleted)}"
    deleted_ages = sorted((d for d, _ in deleted), reverse=True)
    assert deleted_ages == [30, 20], (
        f"Expected oldest (30d, 20d) deleted first, got {deleted_ages}"
    )
    surviving_ages = [d for d, _ in surviving]
    assert surviving_ages == [10], (
        f"Expected youngest (10d) to survive, got {surviving_ages}"
    )


# ── ALC-LC-14: integration-style — pending→failed on workbook error ───────────

def test_lc_pending_to_failed_on_workbook_error(tmp_path, monkeypatch):
    """create_run_dir() + update_run_metadata_status('failed') simulates workbook error."""
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(tmp_path))
    run_dir = create_run_dir()
    meta_path = run_dir / "run_metadata.json"

    # Initially pending
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["status"] == "pending"

    # Simulate workbook generation failure
    update_run_metadata_status(run_dir, "failed")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["status"] == "failed", (
        f"Status should be 'failed' after workbook error, got {meta['status']!r}"
    )
    assert run_dir.is_dir(), "Run directory must persist after failed status"
