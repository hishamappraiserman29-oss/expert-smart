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

Capacity contract (pre-generation)
────────────────────────────────────
MAX_ROOT_ENTRIES     = 1000  — inspect at most this many root children
PRE_GENERATION_TARGET = 900  — stop deleting when approved count < 900
ORPHAN_TTL_SECONDS   = 3600  — empty UUID4 dirs without metadata deleted after TTL
RETENTION_SECONDS    = 604800 — 7-day retention for completed runs

Unknown entries directly under root → mark storage unsafe → block generation.
Symlinks/reparse points under root → immediately unsafe.
Never delete an unclean run or a non-empty metadata-less run.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import stat
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_lock = threading.Lock()

# Cached state — cleared only by reset_lifecycle_state_for_tests()
_validated_root: Optional[Path] = None
_storage_safety_state: Optional[bool] = None
_capacity_cache: Optional[dict] = None
_cleanup_cache: Optional[dict] = None
_init_failure_cache: Optional[str] = None

# ── Capacity constants ──────────────────────────────────────────────────────────
MAX_ROOT_ENTRIES      = 1000
PRE_GENERATION_TARGET = 900
ORPHAN_TTL_SECONDS    = 3600
RETENTION_SECONDS     = 604800   # 7 days

# Allowed filenames inside a run directory
_ALLOWED_RUN_FILES = frozenset({"run_metadata.json", "mass_appraisal.xlsx"})


# ── Exception hierarchy ─────────────────────────────────────────────────────────

class LifecycleConfigError(RuntimeError):
    """Raised when the artifact root cannot be safely established."""


class LifecycleCapacityError(RuntimeError):
    """Raised when capacity cannot be restored below PRE_GENERATION_TARGET."""


class LifecycleStorageUnsafeError(RuntimeError):
    """Raised when an unknown or unsafe entry is detected under the artifact root."""


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
            f"AVM artifact root must be outside the repository tree "
            f"(got {candidate}, repo={repo})"
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
            # Steps 1-2: explicit root from environment (NOT resolved yet — _validate_and_create
            # must see the raw path so step 9 can detect Windows Junctions / reparse points
            # before resolve() follows them to their real target).
            candidate = Path(env_val)
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


# ── UUID4 validation ────────────────────────────────────────────────────────────

def _is_valid_uuid4(name: str) -> bool:
    """Return True if *name* is a valid UUID4 string."""
    try:
        parsed = uuid.UUID(name, version=4)
        return str(parsed) == name
    except (ValueError, AttributeError):
        return False


# ── Root inspection and capacity management ─────────────────────────────────────

class _RunInfo:
    """Lightweight descriptor for a single run directory."""
    __slots__ = ("path", "run_id", "status", "created_at", "is_clean",
                 "has_metadata", "is_empty", "mtime")

    def __init__(
        self,
        path: Path,
        run_id: str,
        status: str,
        created_at: float,
        is_clean: bool,
        has_metadata: bool,
        is_empty: bool,
        mtime: float,
    ) -> None:
        self.path = path
        self.run_id = run_id
        self.status = status
        self.created_at = created_at
        self.is_clean = is_clean
        self.has_metadata = has_metadata
        self.is_empty = is_empty
        self.mtime = mtime


def _inspect_root(root: Path) -> tuple[list[_RunInfo], bool]:
    """Inspect the artifact root.

    Returns (run_infos, is_safe):
    - run_infos: parsed _RunInfo list for all UUID4 run directories
    - is_safe: False if any unknown or unsafe entry is found

    Inspects at most MAX_ROOT_ENTRIES children.
    Raises LifecycleStorageUnsafeError immediately on the first unknown entry.
    """
    is_safe = True
    run_infos: list[_RunInfo] = []
    entry_count = 0

    try:
        entries = list(os.scandir(str(root)))
    except OSError as exc:
        raise LifecycleConfigError(f"Cannot scan artifact root: {exc}") from exc

    for entry in entries:
        entry_count += 1
        if entry_count > MAX_ROOT_ENTRIES:
            logger.warning(
                "AVM lifecycle: root has >%d entries — truncating inspection",
                MAX_ROOT_ENTRIES,
            )
            break

        child = Path(entry.path)

        # Any symlink or reparse point under root is immediately unsafe
        if _is_symlink_or_reparse(child):
            is_safe = False
            raise LifecycleStorageUnsafeError(
                f"Symlink or reparse point found under artifact root: {child}"
            )

        # Only UUID4 directories are allowed at the root level
        if not entry.is_dir(follow_symlinks=False):
            is_safe = False
            raise LifecycleStorageUnsafeError(
                f"Non-directory entry found under artifact root: {child}"
            )

        if not _is_valid_uuid4(entry.name):
            is_safe = False
            raise LifecycleStorageUnsafeError(
                f"Unknown (non-UUID4) directory found under artifact root: {child}"
            )

        # It's a valid UUID4 directory — inspect its contents
        try:
            run_entries = list(os.scandir(str(child)))
        except OSError:
            run_entries = []

        has_metadata = False
        is_empty = len(run_entries) == 0
        is_clean = True
        status = "unknown"
        created_at: float = 0.0

        # Check for unknown files inside the run directory
        for re in run_entries:
            if re.name not in _ALLOWED_RUN_FILES:
                is_clean = False
            if re.name == "run_metadata.json":
                has_metadata = True
                try:
                    meta_path = Path(re.path)
                    meta_text = meta_path.read_text(encoding="utf-8")
                    meta = json.loads(meta_text)
                    status = str(meta.get("status", "unknown"))
                    # Parse ISO-8601 created_at
                    cat_str = meta.get("created_at_iso", "")
                    if cat_str:
                        try:
                            dt = datetime.fromisoformat(cat_str.replace("Z", "+00:00"))
                            created_at = dt.timestamp()
                        except (ValueError, TypeError):
                            pass
                except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                    pass

        try:
            mtime = entry.stat(follow_symlinks=False).st_mtime
        except OSError:
            mtime = 0.0

        if created_at == 0.0:
            created_at = mtime

        run_infos.append(_RunInfo(
            path=child,
            run_id=entry.name,
            status=status,
            created_at=created_at,
            is_clean=is_clean,
            has_metadata=has_metadata,
            is_empty=is_empty,
            mtime=mtime,
        ))

    return run_infos, is_safe


def _safe_delete_run(run: _RunInfo) -> bool:
    """Delete a run directory safely. Returns True on success."""
    try:
        shutil.rmtree(str(run.path))
        logger.info("AVM lifecycle: deleted run %s (status=%s)", run.run_id, run.status)
        return True
    except OSError as exc:
        logger.warning("AVM lifecycle: failed to delete run %s: %s", run.run_id, exc)
        return False


def _pre_generation_cleanup(root: Path) -> None:
    """Inspect root, fail on unknown entries, delete eligible runs for capacity.

    Called before every create_run_dir() call.

    Raises:
        LifecycleStorageUnsafeError: on any unknown or unsafe root entry.
        LifecycleCapacityError: if capacity cannot be restored below PRE_GENERATION_TARGET.
    """
    run_infos, _is_safe = _inspect_root(root)  # raises on unsafe entry

    now = time.time()

    # Separate runs into candidates for deletion vs protected
    approved: list[_RunInfo] = []
    protected: list[_RunInfo] = []

    for ri in run_infos:
        # Never delete: unclean runs, non-empty metadata-less runs
        if not ri.is_clean:
            protected.append(ri)
            continue
        if not ri.has_metadata and not ri.is_empty:
            protected.append(ri)
            continue

        # Empty UUID4 without metadata: delete only after orphan TTL
        if not ri.has_metadata and ri.is_empty:
            age = now - ri.mtime
            if age < ORPHAN_TTL_SECONDS:
                protected.append(ri)
                continue
            # Eligible for orphan cleanup
            approved.append(ri)
            continue

        # Runs with metadata: delete if past retention and status is complete/failed
        if ri.status in ("complete", "failed"):
            age = now - ri.created_at
            if age > RETENTION_SECONDS:
                approved.append(ri)
                continue

        protected.append(ri)

    total_approved = len(approved)
    total = len(run_infos)

    # Check if we are already below the target
    if total < PRE_GENERATION_TARGET:
        return

    # Sort approved by created_at ascending (delete oldest first)
    approved.sort(key=lambda r: r.created_at)

    deleted = 0
    remaining = total

    for ri in approved:
        if remaining < PRE_GENERATION_TARGET:
            break
        if _safe_delete_run(ri):
            deleted += 1
            remaining -= 1

    logger.info(
        "AVM lifecycle: pre-generation cleanup: deleted=%d, remaining=%d, target=%d",
        deleted, remaining, PRE_GENERATION_TARGET,
    )

    # Re-check capacity
    if remaining >= PRE_GENERATION_TARGET:
        raise LifecycleCapacityError(
            f"AVM artifact root has {remaining} entries and cannot be reduced "
            f"below PRE_GENERATION_TARGET={PRE_GENERATION_TARGET}. "
            f"Manual cleanup required."
        )


# ── Metadata helpers ────────────────────────────────────────────────────────────

def _write_initial_metadata(run_dir: Path, run_id: str) -> None:
    """Write run_metadata.json with status 'pending'."""
    meta = {
        "run_id": run_id,
        "created_at_iso": datetime.now(timezone.utc).isoformat(),
        "generator": "expert_smart_avm",
        "status": "pending",
    }
    meta_path = run_dir / "run_metadata.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def update_run_metadata_status(run_dir: Path, status: str) -> None:
    """Atomically update the status field in run_metadata.json.

    status must be one of: 'pending', 'complete', 'failed'.
    Safe to call concurrently from different threads for different run_dirs.
    """
    if status not in ("pending", "complete", "failed"):
        raise ValueError(f"Invalid status '{status}'; expected pending/complete/failed")

    meta_path = run_dir / "run_metadata.json"
    try:
        text = meta_path.read_text(encoding="utf-8")
        meta = json.loads(text)
    except (OSError, json.JSONDecodeError):
        meta = {}

    meta["status"] = status
    tmp_path = meta_path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(meta_path)


# ── Public API ──────────────────────────────────────────────────────────────────

def create_run_dir() -> Path:
    """Create and return a new server-generated UUID4 run directory.

    Structure:
        <artifact_root>/<uuid4>/
            run_metadata.json   (status: pending)

    Raises LifecycleConfigError on configuration failure.
    Raises LifecycleCapacityError when storage cannot be freed.
    Raises LifecycleStorageUnsafeError when an unknown entry is detected.
    Raises OSError on disk errors.
    """
    root = _get_validated_root()
    _pre_generation_cleanup(root)

    run_id = str(uuid.uuid4())
    run_dir = root / run_id
    run_dir.mkdir(parents=False, exist_ok=False)

    # Write run_metadata.json before returning (must exist before any workbook write)
    _write_initial_metadata(run_dir, run_id)

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
