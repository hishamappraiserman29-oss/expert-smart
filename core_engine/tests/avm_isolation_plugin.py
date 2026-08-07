"""Pytest plugin — AVM repository isolation guard (Wave 4B1).

Loaded explicitly with: -p core_engine.tests.avm_isolation_plugin

Guarantees that no persistent AVM artifact write lands inside the repository
tree during any AVM CI lane. Configures worker-specific artifact roots before
application test modules are imported, snapshots the repository state before
collection, and compares it after the session.

Snapshot contract
─────────────────
- Monitored entries: directories, files, symlinks, Windows reparse points.
- Content hash: SHA-256 of each file.
- Metadata: mtime_ns.
- Never follows symlinks or reparse points.
- Maximum depth: 8 levels below the repo root.
- Maximum entries: 10 000.

Detects: additions, deletions, content changes, type changes.

Fails CI on any delta or cleanup failure.
Preserves an existing failing pytest exit code.
Propagates xdist worker-cleanup failures to the master.
"""
from __future__ import annotations

import hashlib
import logging
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pytest

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
_MAX_DEPTH = 8
_MAX_ENTRIES = 10_000

# Paths to ignore inside the repository (generated artefacts, caches, etc.)
_IGNORE_NAMES = frozenset({
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".git", "*.pyc", "node_modules", ".venv", "venv",
    "instance",           # runtime flat-file stores (leads.jsonl etc.)
    "outputs",            # legacy local outputs dir — not under lifecycle
    "tax_appeal",         # runtime data store for tax-appeal module (uploads/reports)
})


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]   # ExpertSmart_Unified/


def _should_ignore(name: str) -> bool:
    if name in _IGNORE_NAMES:
        return True
    if name.endswith(".pyc"):
        return True
    return False


def _is_symlink_or_reparse(path: Path) -> bool:
    """Return True if path is a symlink or Windows reparse point (no-follow)."""
    try:
        st = os.lstat(str(path))
        if stat.S_ISLNK(st.st_mode):
            return True
    except OSError:
        return False
    if os.name == "nt":
        try:
            import ctypes
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))  # type: ignore[attr-defined]
            return attrs != 0xFFFFFFFF and bool(attrs & 0x400)
        except Exception:
            pass
    return False


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
    except OSError:
        return "unreadable"
    return h.hexdigest()


SnapshotEntry = Tuple[str, int, str]   # (kind, mtime_ns, sha256_or_empty)
Snapshot = Dict[str, SnapshotEntry]    # repo-relative-path → entry


def _snapshot(root: Path) -> Snapshot:
    """Walk the repository tree, never following symlinks or reparse points."""
    snap: Snapshot = {}
    stack = [(root, 0)]

    while stack:
        current, depth = stack.pop()
        if depth > _MAX_DEPTH:
            continue
        if len(snap) >= _MAX_ENTRIES:
            logger.warning("AVM isolation snapshot reached %d-entry limit", _MAX_ENTRIES)
            break

        try:
            entries = list(os.scandir(str(current)))
        except OSError:
            continue

        for entry in entries:
            if _should_ignore(entry.name):
                continue

            rel = str(Path(entry.path).relative_to(root))
            try:
                is_link = _is_symlink_or_reparse(Path(entry.path))
            except OSError:
                continue

            if is_link:
                try:
                    mtime = entry.stat(follow_symlinks=False).st_mtime_ns
                except OSError:
                    mtime = 0
                snap[rel] = ("symlink", mtime, "")
                continue

            try:
                st = entry.stat(follow_symlinks=False)
            except OSError:
                continue

            if stat.S_ISDIR(st.st_mode):
                snap[rel] = ("dir", st.st_mtime_ns, "")
                if depth + 1 <= _MAX_DEPTH:
                    stack.append((Path(entry.path), depth + 1))
            elif stat.S_ISREG(st.st_mode):
                sha = _file_sha256(Path(entry.path))
                snap[rel] = ("file", st.st_mtime_ns, sha)

    return snap


def _diff_snapshots(before: Snapshot, after: Snapshot) -> list[str]:
    problems: list[str] = []
    added = set(after) - set(before)
    deleted = set(before) - set(after)
    for path in sorted(added):
        kind, _, _ = after[path]
        problems.append(f"ADDED {kind}: {path}")
    for path in sorted(deleted):
        kind, _, _ = before[path]
        problems.append(f"DELETED {kind}: {path}")
    for path in sorted(set(before) & set(after)):
        bkind, _, bsha = before[path]
        akind, _, asha = after[path]
        if bkind != akind:
            problems.append(f"TYPE CHANGE {path}: {bkind} → {akind}")
        elif bkind == "file" and bsha != asha:
            problems.append(f"MODIFIED file: {path}")
    return problems


# ── Plugin state ───────────────────────────────────────────────────────────────
_before_snapshot: Optional[Snapshot] = None
_worker_failures: List[str] = []
_plugin_owned_runtime_root: Optional[Path] = None

# Prefix for wave4b1 runtime roots — never matches user-data directories
_WAVE4B1_PREFIX = "expert_smart_wave4b1_runtime_"

# Storage variables managed by this plugin
_STORAGE_VARS = (
    "EXPERT_SMART_VECTOR_DB_PATH",
    "EXPERT_SMART_LIBRARY_DIR",
    "EXPERT_SMART_STYLE_PROFILES_DIR",
    "EXPERT_SMART_MARKET_RADAR_DB_PATH",
    "EXPERT_SMART_MODEL_REGISTRY_DIR",
    "EXPERT_SMART_UPLOAD_DIR",
)


def _is_inside_repo(path: Path) -> bool:
    """Return True if path resolves to inside the repository tree."""
    try:
        path.resolve().relative_to(_repo_root().resolve())
        return True
    except ValueError:
        return False


def _runtime_subpath(rt_root: Path, var: str) -> Path:
    """Return the canonical subpath within rt_root for a given storage variable."""
    mapping = {
        "EXPERT_SMART_VECTOR_DB_PATH":       rt_root / "vector_db",
        "EXPERT_SMART_LIBRARY_DIR":          rt_root / "library",
        "EXPERT_SMART_STYLE_PROFILES_DIR":   rt_root / "style_profiles",
        "EXPERT_SMART_MARKET_RADAR_DB_PATH": rt_root / "market_radar.db",
        "EXPERT_SMART_MODEL_REGISTRY_DIR":   rt_root / "models" / "registry",
        "EXPERT_SMART_UPLOAD_DIR":           rt_root / "uploads",
    }
    return mapping[var]


def pytest_configure(config: pytest.Config) -> None:
    """Set up worker-specific AVM artifact roots before any test modules import."""
    global _plugin_owned_runtime_root

    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "") or "main"

    # ── Existing AVM_ARTIFACT_ROOT (unchanged behavior) ────────────────────────
    tmp_root = Path(tempfile.gettempdir()) / "expert_smart_avm_ci"
    worker_root = tmp_root / worker_id
    worker_root.mkdir(parents=True, exist_ok=True)
    os.environ["AVM_ARTIFACT_ROOT"] = str(worker_root)

    # ── Wave 4B1 runtime storage root — unique per (pid, worker) ──────────────
    rt_root = (
        Path(tempfile.gettempdir())
        / f"{_WAVE4B1_PREFIX}{os.getpid()}_{worker_id}"
    )
    rt_root.mkdir(parents=True, exist_ok=True)
    _plugin_owned_runtime_root = rt_root

    # ── Configure storage variables ────────────────────────────────────────────
    for var in _STORAGE_VARS:
        existing = os.environ.get(var)
        if existing:
            # Validate the pre-set value is outside the repo
            try:
                if _is_inside_repo(Path(existing)):
                    logger.error(
                        "AVM isolation plugin: %s=%r resolves inside the repository — "
                        "overriding with safe external path",
                        var, existing,
                    )
                    os.environ[var] = str(_runtime_subpath(rt_root, var))
                # else: preserve the pre-set external value; do not claim ownership
            except Exception:
                pass  # path may not exist yet — preserve as-is
        else:
            os.environ[var] = str(_runtime_subpath(rt_root, var))


def pytest_sessionstart(session: pytest.Session) -> None:
    """Snapshot repository state before collection begins."""
    global _before_snapshot
    if _before_snapshot is None:
        _before_snapshot = _snapshot(_repo_root())


def _cleanup_plugin_runtime_root() -> List[str]:
    """Remove the plugin-owned runtime root safely. Returns a list of error messages."""
    global _plugin_owned_runtime_root
    problems: List[str] = []
    if _plugin_owned_runtime_root is None:
        return problems

    rt = _plugin_owned_runtime_root
    try:
        rt_resolved = rt.resolve()
    except Exception:
        rt_resolved = rt

    tmp_dir = Path(tempfile.gettempdir()).resolve()

    # Safety checks before deletion
    name = rt_resolved.name
    rt_str = str(rt_resolved)
    is_safe = (
        bool(name)
        and name.startswith(_WAVE4B1_PREFIX)
        and rt_str not in ("", "/", str(Path("/")))
        and rt_str != str(tmp_dir)
        and not _is_inside_repo(rt_resolved)
        and _safe_under_temp(rt_resolved, tmp_dir)
    )

    if not is_safe:
        msg = (
            f"AVM isolation plugin: plugin-owned runtime root {rt_resolved!r} "
            f"failed safety check — skipping cleanup"
        )
        logger.error(msg)
        problems.append(msg)
        return problems

    try:
        shutil.rmtree(str(rt_resolved), ignore_errors=False)
        _plugin_owned_runtime_root = None
    except Exception as exc:
        msg = (
            f"AVM isolation plugin: failed to remove runtime root "
            f"{rt_resolved!r}: {exc}"
        )
        logger.error(msg)
        problems.append(msg)

    return problems


def _safe_under_temp(path: Path, tmp_dir: Path) -> bool:
    """Return True if path is directly under the system temp directory."""
    try:
        path.relative_to(tmp_dir)
        return True
    except ValueError:
        return False


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Compare repository state after session; clean up plugin root; fail on delta."""
    if _before_snapshot is None:
        return

    # Step 1: repository-delta validation
    after = _snapshot(_repo_root())
    problems = _diff_snapshots(_before_snapshot, after)

    if _worker_failures:
        problems.extend(_worker_failures)

    if problems:
        logger.error(
            "AVM isolation plugin detected %d repository change(s):\n%s",
            len(problems),
            "\n".join(f"  {p}" for p in problems),
        )
        print(
            f"\n[avm_isolation_plugin] FAIL — {len(problems)} repository delta(s):",
            file=sys.stderr,
        )
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        if exitstatus == 0:
            session.exitstatus = 1

    # Step 2: remove plugin-owned runtime root
    cleanup_problems = _cleanup_plugin_runtime_root()
    if cleanup_problems:
        for p in cleanup_problems:
            print(f"\n[avm_isolation_plugin] CLEANUP FAIL: {p}", file=sys.stderr)
        if session.exitstatus == 0:
            session.exitstatus = 1


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call):
    outcome = yield
    if call.when == "teardown":
        report = outcome.get_result()
        if report.failed:
            _worker_failures.append(
                f"worker cleanup failure in {item.nodeid}: {report.longreprtext}"
            )
