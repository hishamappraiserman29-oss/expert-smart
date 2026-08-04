"""Tests for avm_lifecycle.py — AVM artifact root lifecycle manager (Wave 4B1).

Covers the 12-step creation contract, symlink/reparse-point rejection,
in-repository rejection, immutability after first init, and test reset.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from avm_lifecycle import (
    LifecycleConfigError,
    create_run_dir,
    reset_lifecycle_state_for_tests,
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
    repo_root = Path(__file__).resolve().parents[2]   # ExpertSmart_Unified/
    inside = repo_root / "core_engine" / "avm_test_artifact_root_inside"
    monkeypatch.setenv("AVM_ARTIFACT_ROOT", str(inside))
    with pytest.raises(LifecycleConfigError, match="outside the repository"):
        create_run_dir()


# ── ALC-05: Symlink root rejected ─────────────────────────────────────────────

@pytest.mark.skipif(
    os.name == "nt",
    reason="Symlink creation requires elevated privileges on Windows; skipped in CI.",
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
