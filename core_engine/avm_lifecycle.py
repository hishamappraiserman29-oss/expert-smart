"""AVM artifact-root lifecycle manager — Wave 4B1.

Thread-safe, lazy-initialized on first persistent export.
Default root: tempfile.gettempdir()/expert_smart_avm

12-step creation contract
─────────────────────────
1.  Resolve repository root (this file's parent's parent).
2.  Resolve the candidate path (env var or default).
3.  Reject if candidate is inside the repository tree.
4.  lstat the candidate's parent — reject if it does not exist.
5.  Reject if the parent is a symlink, junction, or reparse point.
6.  Create the candidate directory atomically (exist_ok=True).
7.  Set restrictive permissions (chmod 0o700; no-op on Windows).
8.  lstat the created/existing directory immediately.
9.  Reject if the created root is itself a symlink or reparse point.
10. resolve() the path and verify it stays under the approved parent.
11. Cache the validated Path under _lock.
12. Ignore subsequent AVM_ARTIFACT_ROOT changes after first init.
"""
from __future__ import annotations

import logging
import os
import stat
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_lock = threading.Lock()

# Cached state — cleared only by _reset_lifecycle_state_for_tests()
_validated_root: Optional[Path] = None
_storage_safety_state: Optional[bool] = None
_capacity_cache: Optional[dict] = None
_cleanup_cache: Optional[dict] = None
_init_failure_cache: Optional[str] = None   # error message from last failed init


class LifecycleConfigError(RuntimeError):
    """Raised when the artifact root cannot be safely established."""


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _is_reparse_point_windows(path: Path) -> bool:
    """Return True if *path* is a Windows reparse point / junction.

    Uses ctypes FILE_ATTRIBUTE_REPARSE_POINT (0x400) for Python 3.11
    compatibility (Path.stat(follow_symlinks=False) lacks st_reparse_tag).
    """
    try:
        import ctypes
        FILE_ATTRIBUTE_REPARSE_POINT = 0x400
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))  # type: ignore[attr-defined]
        if attrs == 0xFFFFFFFF:
            return False
        return bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)
    except Exception:
        return False


def _lstat_no_follow(path: Path) -> os.stat_result:
    """lstat() that does not follow symlinks (Python 3.11-compatible)."""
    return os.lstat(str(path))


def _is_symlink_or_reparse(path: Path) -> bool:
    """Return True if *path* is a symlink, junction, or reparse point."""
    try:
        st = _lstat_no_follow(path)
        if stat.S_ISLNK(st.st_mode):
            return True
    except OSError:
        return False
    if os.name == "nt":
        return _is_reparse_point_windows(path)
    return False


def _validate_and_create(candidate: Path) -> Path:
    """Execute the 12-step creation contract. Returns the cached validated Path."""
    repo = _repo_root()

    # Step 3 — candidate must not be inside the repository
    try:
        candidate.relative_to(repo)
        raise LifecycleConfigError(
            "AVM artifact root must be outside the repository tree"
        )
    except ValueError:
        pass  # relative_to() raises ValueError when not a subpath — correct

    # Step 4 — parent must exist
    try:
        _lstat_no_follow(candidate.parent)
    except FileNotFoundError:
        raise LifecycleConfigError(
            f"Artifact root parent directory does not exist: {candidate.parent}"
        )

    # Step 5 — parent must not be a symlink/reparse point
    if _is_symlink_or_reparse(candidate.parent):
        raise LifecycleConfigError(
            f"Artifact root parent is a symlink or reparse point: {candidate.parent}"
        )

    # Step 6 — atomic creation
    candidate.mkdir(parents=False, exist_ok=True)

    # Step 7 — restrictive permissions (no-op on Windows)
    try:
        candidate.chmod(0o700)
    except OSError:
        pass

    # Step 8 — lstat the created/existing directory
    try:
        _lstat_no_follow(candidate)
    except FileNotFoundError:
        raise LifecycleConfigError(
            "Artifact root vanished immediately after creation"
        )

    # Step 9 — root itself must not be a symlink/reparse point
    if _is_symlink_or_reparse(candidate):
        raise LifecycleConfigError(
            f"Artifact root is a symlink or reparse point: {candidate}"
        )

    # Step 10 — resolve and verify stays under approved parent
    try:
        final = candidate.resolve()
        approved_parent = candidate.parent.resolve()
        if final.parent != approved_parent:
            raise LifecycleConfigError(
                "Artifact root resolve() escapes the approved parent directory"
            )
    except LifecycleConfigError:
        raise
    except Exception as exc:
        raise LifecycleConfigError(f"Path resolution failed: {exc}") from exc

    # Step 11 — cache (caller already holds _lock)
    return final


def _get_validated_root() -> Path:
    """Return the cached validated root, initializing if needed (thread-safe)."""
    global _validated_root, _init_failure_cache

    # Fast path — already initialized
    if _validated_root is not None:
        return _validated_root

    with _lock:
        # Double-checked locking
        if _validated_root is not None:
            return _validated_root

        # Step 12 — read env var only on first init; ignore later changes
        env_val = os.environ.get("AVM_ARTIFACT_ROOT", "").strip()
        if env_val:
            # Steps 1-2: explicit root from environment
            candidate = Path(env_val).resolve()
        else:
            # Steps 1-2: default root
            candidate = Path(tempfile.gettempdir()) / "expert_smart_avm"

        try:
            _validated_root = _validate_and_create(candidate)
            _init_failure_cache = None
            logger.info("AVM artifact root initialized: %s", _validated_root)
        except LifecycleConfigError as exc:
            _init_failure_cache = str(exc)
            logger.error("AVM lifecycle config error: %s", exc)
            raise

    return _validated_root


def create_run_dir() -> Path:
    """Create and return a new server-generated UUID4 run directory.

    Structure:
        <artifact_root>/<uuid4>/

    Raises LifecycleConfigError on configuration failure.
    Raises OSError on disk errors.
    """
    root = _get_validated_root()
    run_id = str(uuid.uuid4())
    run_dir = root / run_id
    run_dir.mkdir(parents=False, exist_ok=False)
    return run_dir


def artifact_unavailable_response():
    """Return a (response_dict, status_code) tuple for 503 storage-unavailable."""
    return {"error": "artifact_storage_unavailable"}, 503


def reset_lifecycle_state_for_tests() -> None:
    """Clear all cached lifecycle state. FOR TESTS ONLY — not exposed over HTTP."""
    global _validated_root, _storage_safety_state, _capacity_cache
    global _cleanup_cache, _init_failure_cache
    with _lock:
        _validated_root       = None
        _storage_safety_state = None
        _capacity_cache       = None
        _cleanup_cache        = None
        _init_failure_cache   = None
