"""
supervised_agent.py — Supervised Autonomy (Phase 19.0)

Wraps the ValuationPipelineOrchestrator with:
  • ExecutionMode — controls what the agent may do without human approval
  • BackupManager  — creates and restores workspace snapshots
  • SupervisedAgent — gates every action through the execution mode and an
                      optional approval callback, then records everything
                      in an in-memory action log

Execution modes:
  AUTONOMOUS  — all actions auto-approved, no callback invoked
  SUPERVISED  — routine actions auto-approved; risky ones (delete, restore,
                run_pipeline) require callback approval
  MANUAL      — every action requires callback approval
  READONLY    — write / valuate / pipeline actions are blocked outright

Classes:
    ExecutionMode
    ActionType
    ActionRecord      — one logged agent action
    BackupInfo        — metadata for one workspace snapshot
    BackupManager     — create / restore / list / delete backups
    SupervisedAgent   — gated pipeline runner with action log
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
from pathlib import Path
import shutil
from typing import Any, Callable, Dict, List, Optional
import uuid

# ── Enums ─────────────────────────────────────────────────────────────────────


class ExecutionMode(str, Enum):
    AUTONOMOUS = "autonomous"  # fully automated — no approval needed
    SUPERVISED = "supervised"  # routine actions auto; risky actions gated
    MANUAL = "manual"  # every action requires approval
    READONLY = "readonly"  # no writes, valuations, or pipeline runs


class ActionType(str, Enum):
    SCAN = "scan"
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    DELETE_FILE = "delete_file"
    VALUATE = "valuate"
    BACKUP = "backup"
    RESTORE = "restore"
    RUN_PIPELINE = "run_pipeline"


# Actions that are blocked entirely in READONLY mode
_WRITE_ACTIONS: frozenset = frozenset(
    {
        ActionType.WRITE_FILE,
        ActionType.DELETE_FILE,
        ActionType.VALUATE,
        ActionType.RUN_PIPELINE,
        ActionType.RESTORE,
    }
)

# Actions that need approval in SUPERVISED mode (but not in AUTONOMOUS)
_RISKY_ACTIONS: frozenset = frozenset(
    {
        ActionType.DELETE_FILE,
        ActionType.RESTORE,
        ActionType.RUN_PIPELINE,
    }
)


# ── ActionRecord ──────────────────────────────────────────────────────────────


@dataclass
class ActionRecord:
    """One entry in the agent's action log."""

    action_id: str
    action_type: str
    workspace_id: str
    details: Dict
    execution_mode: str
    status: str  # pending | approved | rejected | completed | failed
    created_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "workspace_id": self.workspace_id,
            "execution_mode": self.execution_mode,
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "error": self.error,
        }


# ── BackupInfo ────────────────────────────────────────────────────────────────


@dataclass
class BackupInfo:
    """Metadata for a single workspace backup snapshot."""

    backup_id: str
    workspace_id: str
    label: str
    backup_path: str
    file_count: int
    size_bytes: int
    created_at: str

    def to_dict(self) -> Dict:
        return {
            "backup_id": self.backup_id,
            "workspace_id": self.workspace_id,
            "label": self.label,
            "backup_path": self.backup_path,
            "file_count": self.file_count,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at,
        }


# ── BackupManager ─────────────────────────────────────────────────────────────


class BackupManager:
    """
    Create and manage point-in-time snapshots of a workspace.

    Backups are stored under <base_dir>/_backups/<backup_id>/ alongside a
    backup.json metadata file.  The workspace.json marker file is never
    included in a backup (it belongs to WorkspaceManager).
    """

    _BACKUP_DIR = "_backups"
    _META_FILE = "backup.json"
    _WS_META = "workspace.json"

    def __init__(self, workspace_manager: Any) -> None:
        self._wm = workspace_manager
        self._backup_root = workspace_manager.base_dir / self._BACKUP_DIR
        self._backup_root.mkdir(parents=True, exist_ok=True)

    # ── Create ────────────────────────────────────────────────────────────────

    def create_backup(self, workspace_id: str, label: str = "") -> BackupInfo:
        """
        Snapshot all files in the workspace to a new backup directory.
        Raises KeyError if workspace_id is unknown.
        """
        ws = self._wm.get_workspace(workspace_id)
        if ws is None:
            raise KeyError(f"Workspace not found: {workspace_id}")

        backup_id = str(uuid.uuid4())
        backup_dir = self._backup_root / backup_id
        backup_dir.mkdir(parents=True)

        src_root = Path(ws.root_path)
        file_count = 0
        total_bytes = 0

        for src in src_root.rglob("*"):
            if not src.is_file():
                continue
            if src.name in (self._WS_META, self._META_FILE):
                continue
            rel = src.relative_to(src_root)
            dst = backup_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            file_count += 1
            total_bytes += src.stat().st_size

        stamp = label or f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        info = BackupInfo(
            backup_id=backup_id,
            workspace_id=workspace_id,
            label=stamp,
            backup_path=str(backup_dir),
            file_count=file_count,
            size_bytes=total_bytes,
            created_at=datetime.now().isoformat(),
        )
        (backup_dir / self._META_FILE).write_text(json.dumps(info.to_dict(), indent=2), encoding="utf-8")
        return info

    # ── Restore ───────────────────────────────────────────────────────────────

    def restore_backup(self, workspace_id: str, backup_id: str) -> bool:
        """
        Restore a backup into the workspace:
          1. Delete all current files (except workspace.json).
          2. Copy backed-up files back.
        Returns False if the backup or workspace is not found, or if the
        backup belongs to a different workspace.
        """
        ws = self._wm.get_workspace(workspace_id)
        if ws is None:
            return False

        backup_dir = self._backup_root / backup_id
        meta_path = backup_dir / self._META_FILE
        if not meta_path.exists():
            return False

        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("workspace_id") != workspace_id:
            return False

        ws_root = Path(ws.root_path)

        # Remove current files
        for f in list(ws_root.rglob("*")):
            if f.is_file() and f.name not in (self._WS_META,):
                f.unlink()

        # Restore from backup
        for src in backup_dir.rglob("*"):
            if src.is_file() and src.name != self._META_FILE:
                rel = src.relative_to(backup_dir)
                dst = ws_root / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

        return True

    # ── List / Delete ─────────────────────────────────────────────────────────

    def list_backups(self, workspace_id: str) -> List[BackupInfo]:
        """Return all backups for the given workspace, sorted by created_at."""
        results: List[BackupInfo] = []
        for d in self._backup_root.iterdir():
            if not d.is_dir():
                continue
            meta_path = d / self._META_FILE
            if not meta_path.exists():
                continue
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                if meta.get("workspace_id") != workspace_id:
                    continue
                results.append(BackupInfo(**{k: meta[k] for k in BackupInfo.__dataclass_fields__}))
            except Exception:
                continue
        return sorted(results, key=lambda b: b.created_at)

    def delete_backup(self, backup_id: str) -> bool:
        """Remove a backup directory entirely. Returns True if removed."""
        backup_dir = self._backup_root / backup_id
        if not backup_dir.exists():
            return False
        shutil.rmtree(str(backup_dir), ignore_errors=True)
        return not backup_dir.exists()


# ── SupervisedAgent ───────────────────────────────────────────────────────────


class SupervisedAgent:
    """
    Gated pipeline runner with configurable execution mode.

    Parameters
    ----------
    workspace_manager  : WorkspaceManager
    bridge             : ExpertSmartBridge (or mock)
    execution_mode     : initial ExecutionMode (default SUPERVISED)
    approval_callback  : optional Callable[[action_type, details], bool]
                         Called for actions that require human approval.
                         Must return True to approve, False to reject.
                         If None, all gated actions are auto-rejected.
    """

    def __init__(
        self,
        workspace_manager: Any,
        bridge: Any,
        execution_mode: str = ExecutionMode.SUPERVISED,
        approval_callback: Optional[Callable] = None,
    ) -> None:
        self._wm = workspace_manager
        self._bridge = bridge
        self._mode = execution_mode
        self._approval_callback = approval_callback
        self._backup_mgr = BackupManager(workspace_manager)
        self._action_log: List[ActionRecord] = []

        from agents.pipeline_orchestrator import ValuationPipelineOrchestrator

        self._pipeline = ValuationPipelineOrchestrator(workspace_manager, bridge)

    # ── Configuration ─────────────────────────────────────────────────────────

    def set_mode(self, mode: str) -> None:
        """Switch the execution mode at runtime."""
        self._mode = mode

    def set_approval_callback(self, cb: Callable) -> None:
        self._approval_callback = cb

    def get_action_log(self) -> List[ActionRecord]:
        return list(self._action_log)

    # ── Internal gate ─────────────────────────────────────────────────────────

    def _log(
        self,
        action_type: str,
        workspace_id: str,
        details: Dict,
        status: str,
        error: Optional[str] = None,
    ) -> ActionRecord:
        rec = ActionRecord(
            action_id=str(uuid.uuid4()),
            action_type=action_type,
            workspace_id=workspace_id,
            details=details,
            execution_mode=self._mode,
            status=status,
            created_at=datetime.now().isoformat(),
            error=error,
        )
        self._action_log.append(rec)
        return rec

    def _gate(
        self,
        action_type: str,
        workspace_id: str,
        details: Dict,
    ) -> bool:
        """
        Evaluate the action against the current mode.
        Returns True if permitted, False if rejected.
        Always appends an ActionRecord.
        """
        # READONLY — block write-class actions outright
        if self._mode == ExecutionMode.READONLY:
            if action_type in _WRITE_ACTIONS:
                self._log(
                    action_type,
                    workspace_id,
                    details,
                    "rejected",
                    error="Rejected: readonly mode disallows write actions",
                )
                return False
            self._log(action_type, workspace_id, details, "approved")
            return True

        # AUTONOMOUS — approve everything without callback
        if self._mode == ExecutionMode.AUTONOMOUS:
            self._log(action_type, workspace_id, details, "approved")
            return True

        # SUPERVISED — non-risky actions auto-approved
        if self._mode == ExecutionMode.SUPERVISED:
            if action_type not in _RISKY_ACTIONS:
                self._log(action_type, workspace_id, details, "approved")
                return True
            # fall through to callback

        # MANUAL or SUPERVISED+risky — invoke callback
        if self._approval_callback is not None:
            approved = bool(self._approval_callback(action_type, dict(details)))
        else:
            approved = False

        if approved:
            self._log(action_type, workspace_id, details, "approved")
        else:
            self._log(action_type, workspace_id, details, "rejected", error="Approval denied")
        return approved

    # ── Public operations ─────────────────────────────────────────────────────

    def run_pipeline(
        self,
        workspace_id: str,
        primary_purpose: str = "market_value",
        auto_backup: bool = True,
    ) -> Any:  # returns PipelineReport — Any avoids circular import
        """
        Run the valuation pipeline under supervision controls.

        Raises PermissionError if the execution mode or approval callback
        rejects the action.
        """
        if not self._gate(ActionType.RUN_PIPELINE, workspace_id, {"primary_purpose": primary_purpose}):
            raise PermissionError(f"Pipeline run rejected under execution mode '{self._mode}'")

        # Backup before running (best-effort, never blocks pipeline)
        if auto_backup:
            try:
                bk = self._backup_mgr.create_backup(workspace_id, label="pre_pipeline")
                self._log(ActionType.BACKUP, workspace_id, {"backup_id": bk.backup_id, "label": bk.label}, "completed")
            except Exception as exc:
                self._log(ActionType.BACKUP, workspace_id, {}, "failed", error=str(exc))

        try:
            report = self._pipeline.run(workspace_id, primary_purpose)
            self._log(
                ActionType.RUN_PIPELINE,
                workspace_id,
                {"completed": report.completed, "failed": report.failed},
                "completed",
            )
            return report
        except Exception as exc:
            self._log(ActionType.RUN_PIPELINE, workspace_id, {}, "failed", error=str(exc))
            raise

    def create_backup(self, workspace_id: str, label: str = "") -> BackupInfo:
        """Create a workspace backup (always permitted, logged)."""
        info = self._backup_mgr.create_backup(workspace_id, label)
        self._log(ActionType.BACKUP, workspace_id, {"backup_id": info.backup_id}, "completed")
        return info

    def restore_backup(self, workspace_id: str, backup_id: str) -> bool:
        """Restore a backup — subject to approval gate."""
        if not self._gate(ActionType.RESTORE, workspace_id, {"backup_id": backup_id}):
            return False
        ok = self._backup_mgr.restore_backup(workspace_id, backup_id)
        self._log(ActionType.RESTORE, workspace_id, {"backup_id": backup_id}, "completed" if ok else "failed")
        return ok
