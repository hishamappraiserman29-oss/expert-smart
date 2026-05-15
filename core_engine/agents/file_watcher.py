"""
file_watcher.py — Folder Watcher (Phase 20.0)

Monitors a workspace directory for file-system changes and emits FileEvent
objects to a caller-supplied callback.  Uses a background polling thread —
no external dependencies required.

Classes:
    WatchEventType    — CREATED / MODIFIED / DELETED
    FileEvent         — one detected file-system change
    FileWatcher       — per-workspace background poller
    WatcherManager    — registry of active FileWatcher instances;
                        provides make_pipeline_trigger() helper
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
import threading
from typing import Any, Callable, Dict, List, Optional, Set

# ── WatchEventType ────────────────────────────────────────────────────────────


class WatchEventType(str, Enum):
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"


# ── FileEvent ─────────────────────────────────────────────────────────────────


@dataclass
class FileEvent:
    """One detected change in a watched workspace."""

    event_type: str
    workspace_id: str
    relative_path: str
    absolute_path: str
    detected_at: str

    def to_dict(self) -> Dict:
        return {
            "event_type": self.event_type,
            "workspace_id": self.workspace_id,
            "relative_path": self.relative_path,
            "absolute_path": self.absolute_path,
            "detected_at": self.detected_at,
        }


# ── FileWatcher ───────────────────────────────────────────────────────────────

_DEFAULT_EXTENSIONS: frozenset = frozenset({".csv", ".json", ".xlsx", ".xls"})
_DEFAULT_SKIP_FILES: frozenset = frozenset({"workspace.json", "backup.json"})


class FileWatcher:
    """
    Background polling watcher for one workspace directory.

    Parameters
    ----------
    workspace_id   : identifier for the workspace (included in every FileEvent)
    workspace_path : root directory to monitor
    callback       : Callable[[FileEvent], None] — invoked for every change;
                     exceptions in the callback are swallowed so the watcher
                     thread never dies due to caller bugs
    poll_interval  : seconds between directory scans (default 1.0)
    extensions     : file extensions to track (default csv/json/xlsx/xls)
    skip_files     : file names to ignore (default workspace.json, backup.json)
    """

    def __init__(
        self,
        workspace_id: str,
        workspace_path: str | Path,
        callback: Callable[[FileEvent], None],
        poll_interval: float = 1.0,
        extensions: Optional[Set[str]] = None,
        skip_files: Optional[Set[str]] = None,
    ) -> None:
        self._workspace_id = workspace_id
        self._workspace_path = Path(workspace_path)
        self._callback = callback
        self._poll_interval = poll_interval
        self._extensions = frozenset(extensions) if extensions else _DEFAULT_EXTENSIONS
        self._skip_files = frozenset(skip_files) if skip_files is not None else _DEFAULT_SKIP_FILES
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._snapshot: Dict[str, float] = {}  # rel_path → mtime

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Take an initial snapshot and start the background polling thread."""
        if self.is_running:
            return
        self._snapshot = self._take_snapshot()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name=f"fw-{self._workspace_id[:8]}")
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the polling thread to stop and wait for it to exit."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ── Internals ─────────────────────────────────────────────────────────────

    def _take_snapshot(self) -> Dict[str, float]:
        """Return {relative_path: mtime} for all tracked files."""
        snap: Dict[str, float] = {}
        root = self._workspace_path
        if not root.exists():
            return snap
        for f in root.rglob("*"):
            if not f.is_file():
                continue
            if f.name in self._skip_files:
                continue
            if f.suffix.lower() not in self._extensions:
                continue
            rel = str(f.relative_to(root))
            try:
                snap[rel] = f.stat().st_mtime
            except OSError:
                pass
        return snap

    def _poll_loop(self) -> None:
        while not self._stop_event.wait(self._poll_interval):
            new_snap = self._take_snapshot()
            self._diff_and_emit(new_snap)
            self._snapshot = new_snap

    def _diff_and_emit(self, new_snap: Dict[str, float]) -> None:
        old = self._snapshot
        for rel, mtime in new_snap.items():
            if rel not in old:
                self._emit(WatchEventType.CREATED, rel)
            elif mtime != old[rel]:
                self._emit(WatchEventType.MODIFIED, rel)
        for rel in old:
            if rel not in new_snap:
                self._emit(WatchEventType.DELETED, rel)

    def _emit(self, event_type: str, rel_path: str) -> None:
        event = FileEvent(
            event_type=event_type,
            workspace_id=self._workspace_id,
            relative_path=rel_path,
            absolute_path=str(self._workspace_path / rel_path),
            detected_at=datetime.now().isoformat(),
        )
        try:
            self._callback(event)
        except Exception:
            pass  # callback errors must never crash the watcher thread


# ── WatcherManager ────────────────────────────────────────────────────────────


class WatcherManager:
    """
    Registry of active FileWatcher instances.

    One workspace → one watcher at a time.  Starting a second watch for the
    same workspace_id replaces (and stops) the previous one.
    """

    def __init__(self) -> None:
        self._watchers: Dict[str, FileWatcher] = {}

    # ── Registration ──────────────────────────────────────────────────────────

    def watch(
        self,
        workspace_id: str,
        workspace_path: str | Path,
        callback: Callable[[FileEvent], None],
        poll_interval: float = 1.0,
        extensions: Optional[Set[str]] = None,
    ) -> FileWatcher:
        """
        Start watching a workspace directory.
        Replaces any existing watcher for the same workspace_id.
        """
        self.unwatch(workspace_id)
        watcher = FileWatcher(
            workspace_id,
            workspace_path,
            callback,
            poll_interval=poll_interval,
            extensions=extensions,
        )
        watcher.start()
        self._watchers[workspace_id] = watcher
        return watcher

    def unwatch(self, workspace_id: str) -> bool:
        """Stop and remove the watcher for workspace_id. Returns False if none."""
        watcher = self._watchers.pop(workspace_id, None)
        if watcher is None:
            return False
        watcher.stop()
        return True

    def list_watched(self) -> List[str]:
        """Return IDs of all currently watched workspaces."""
        return list(self._watchers.keys())

    def stop_all(self) -> None:
        """Stop every active watcher."""
        for ws_id in list(self._watchers):
            self.unwatch(ws_id)

    # ── Auto-trigger helper ───────────────────────────────────────────────────

    def make_pipeline_trigger(
        self,
        agent: Any,
        workspace_id: str,
        primary_purpose: str = "market_value",
        auto_backup: bool = False,
    ) -> Callable[[FileEvent], None]:
        """
        Return a FileEvent callback that calls agent.run_pipeline() whenever
        a property file is CREATED in the watched workspace.

        Pipeline errors are swallowed — the watcher must remain alive regardless.
        """

        def _trigger(event: FileEvent) -> None:
            if event.event_type != WatchEventType.CREATED:
                return
            try:
                agent.run_pipeline(
                    workspace_id,
                    primary_purpose=primary_purpose,
                    auto_backup=auto_backup,
                )
            except Exception:
                pass

        return _trigger
