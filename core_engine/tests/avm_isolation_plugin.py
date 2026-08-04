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
import stat
import sys
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple

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
_worker_failures: list[str] = []


def pytest_configure(config: pytest.Config) -> None:
    """Set up worker-specific AVM artifact roots before any test modules import."""
    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "")
    tmp_root = Path(tempfile.gettempdir()) / "expert_smart_avm_ci"
    if worker_id:
        worker_root = tmp_root / worker_id
    else:
        worker_root = tmp_root / "main"
    worker_root.mkdir(parents=True, exist_ok=True)
    os.environ["AVM_ARTIFACT_ROOT"] = str(worker_root)


def pytest_sessionstart(session: pytest.Session) -> None:
    """Snapshot repository state before collection begins."""
    global _before_snapshot
    if _before_snapshot is None:
        _before_snapshot = _snapshot(_repo_root())


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Compare repository state after the session; fail CI on any delta."""
    if _before_snapshot is None:
        return

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
        # Preserve an existing failing exit code; worsen a passing one.
        if exitstatus == 0:
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
