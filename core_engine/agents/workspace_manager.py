"""
workspace_manager.py — Local Workspace Agent (Phase 17.0)

Provides a sandboxed folder environment for the Expert Smart agent.
All file operations are confined to a workspace root — path traversal
attempts raise ValueError before touching the filesystem.

Classes:
    WorkspaceStatus   — enum (active / readonly / archived)
    WorkspaceInfo     — metadata record for one workspace
    WorkspaceManager  — create, query, and operate on workspaces
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Dict, List, Optional
import uuid

_DEFAULT_BASE = os.environ.get(
    "EXPERT_SMART_WORKSPACE",
    os.path.join(tempfile.gettempdir(), "expert_smart_workspaces"),
)

_META_FILE = "workspace.json"  # stored inside each workspace root
_MAX_FILE_BYTES = 100 * 1024 * 1024  # 100 MB hard limit per write


# ── Status enum ───────────────────────────────────────────────────────────────


class WorkspaceStatus(str, Enum):
    ACTIVE = "active"
    READONLY = "readonly"
    ARCHIVED = "archived"


# ── Info dataclass ────────────────────────────────────────────────────────────


@dataclass
class WorkspaceInfo:
    """Metadata record for a single workspace."""

    workspace_id: str
    name: str
    root_path: str
    status: str  # WorkspaceStatus value
    created_at: str
    file_count: int = 0
    total_size_bytes: int = 0

    def to_dict(self) -> Dict:
        return {
            "workspace_id": self.workspace_id,
            "name": self.name,
            "root_path": self.root_path,
            "status": self.status,
            "created_at": self.created_at,
            "file_count": self.file_count,
            "total_size_bytes": self.total_size_bytes,
        }


# ── Manager ───────────────────────────────────────────────────────────────────


class WorkspaceManager:
    """
    Sandboxed folder manager for agent file operations.

    Each workspace is a subdirectory of base_dir identified by a UUID.
    A workspace.json metadata file lives at the root of every workspace.
    All path arguments are validated to prevent escaping the sandbox.
    """

    def __init__(self, base_dir: str = _DEFAULT_BASE) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._index: Dict[str, WorkspaceInfo] = {}
        self._load_existing()

    # ── Filesystem helpers ────────────────────────────────────────────────────

    def _load_existing(self) -> None:
        """Reconstruct the in-memory index from workspace.json files on disk."""
        for d in self.base_dir.iterdir():
            if not d.is_dir():
                continue
            meta_path = d / _META_FILE
            if not meta_path.exists():
                continue
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                fc, ts = self._compute_stats(d)
                info = WorkspaceInfo(
                    workspace_id=meta["workspace_id"],
                    name=meta["name"],
                    root_path=str(d),
                    status=meta.get("status", WorkspaceStatus.ACTIVE),
                    created_at=meta.get("created_at", ""),
                    file_count=fc,
                    total_size_bytes=ts,
                )
                self._index[info.workspace_id] = info
            except Exception:
                pass

    @staticmethod
    def _compute_stats(root: Path) -> tuple:
        """Return (file_count, total_bytes) excluding the metadata file."""
        count = total = 0
        for f in root.rglob("*"):
            if f.is_file() and f.name != _META_FILE:
                count += 1
                total += f.stat().st_size
        return count, total

    def _write_meta(self, info: WorkspaceInfo) -> None:
        meta = {
            "workspace_id": info.workspace_id,
            "name": info.name,
            "status": info.status,
            "created_at": info.created_at,
        }
        (Path(info.root_path) / _META_FILE).write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def _refresh_stats(self, info: WorkspaceInfo) -> WorkspaceInfo:
        fc, ts = self._compute_stats(Path(info.root_path))
        info.file_count = fc
        info.total_size_bytes = ts
        return info

    # ── Path safety ───────────────────────────────────────────────────────────

    def safe_path(self, workspace_id: str, relative_path: str) -> Path:
        """
        Resolve relative_path inside the workspace root.
        Raises ValueError if the resolved path escapes the sandbox.
        Raises KeyError if workspace_id is unknown.
        """
        info = self.get_workspace(workspace_id)
        if info is None:
            raise KeyError(f"Unknown workspace: {workspace_id}")
        root = Path(info.root_path).resolve()
        target = (root / relative_path).resolve()
        if not str(target).startswith(str(root) + os.sep) and target != root:
            raise ValueError(f"Path escape detected: '{relative_path}' resolves outside workspace")
        return target

    # ── Workspace CRUD ────────────────────────────────────────────────────────

    def create_workspace(
        self,
        name: str,
        status: str = WorkspaceStatus.ACTIVE,
    ) -> WorkspaceInfo:
        """Create a new sandboxed workspace directory."""
        wid = str(uuid.uuid4())
        root = self.base_dir / wid
        root.mkdir(parents=True, exist_ok=True)

        info = WorkspaceInfo(
            workspace_id=wid,
            name=name,
            root_path=str(root),
            status=status,
            created_at=datetime.now().isoformat(),
        )
        self._write_meta(info)
        self._index[wid] = info
        return info

    def get_workspace(self, workspace_id: str) -> Optional[WorkspaceInfo]:
        """Return the workspace info (with refreshed stats), or None."""
        info = self._index.get(workspace_id)
        if info is None:
            return None
        return self._refresh_stats(info)

    def list_workspaces(self) -> List[WorkspaceInfo]:
        """Return all known workspaces, stats refreshed, sorted by created_at."""
        result = [self._refresh_stats(info) for info in self._index.values()]
        return sorted(result, key=lambda i: i.created_at)

    def delete_workspace(self, workspace_id: str) -> bool:
        """Delete workspace directory and remove from index. Returns True on success."""
        info = self._index.get(workspace_id)
        if info is None:
            return False
        try:
            shutil.rmtree(info.root_path, ignore_errors=True)
        finally:
            self._index.pop(workspace_id, None)
        return True

    # ── File operations ───────────────────────────────────────────────────────

    def write_file(
        self,
        workspace_id: str,
        relative_path: str,
        content: bytes,
    ) -> int:
        """
        Write bytes to relative_path inside the workspace.
        Creates parent directories as needed.
        Raises ValueError if the path escapes the sandbox or content exceeds the size limit.
        Returns number of bytes written.
        """
        if len(content) > _MAX_FILE_BYTES:
            raise ValueError(f"Content size {len(content):,} bytes exceeds limit {_MAX_FILE_BYTES:,}")
        target = self.safe_path(workspace_id, relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return len(content)

    def read_file(self, workspace_id: str, relative_path: str) -> bytes:
        """Read and return the file contents. Raises FileNotFoundError if missing."""
        target = self.safe_path(workspace_id, relative_path)
        if not target.exists():
            raise FileNotFoundError(f"File not found in workspace: {relative_path}")
        return target.read_bytes()

    def list_files(
        self,
        workspace_id: str,
        pattern: str = "**/*",
    ) -> List[str]:
        """
        Return relative paths of matching files (not directories, not workspace.json).
        Pattern follows pathlib glob syntax (e.g. '**/*.xlsx', '*.csv').
        """
        info = self.get_workspace(workspace_id)
        if info is None:
            return []
        root = Path(info.root_path)
        result = []
        for p in root.glob(pattern):
            if p.is_file() and p.name != _META_FILE:
                result.append(str(p.relative_to(root)))
        return sorted(result)

    def delete_file(self, workspace_id: str, relative_path: str) -> bool:
        """Delete a single file.  Returns True if deleted, False if not found."""
        try:
            target = self.safe_path(workspace_id, relative_path)
        except (KeyError, ValueError):
            return False
        if not target.exists():
            return False
        target.unlink()
        return True
