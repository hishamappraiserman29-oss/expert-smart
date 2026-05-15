"""
chat_agent.py — Chat-Driven Agent Dispatcher (Phase 21.0)

Takes free-text from a user, parses it with CommandParser, then dispatches
the resulting ParsedCommand to the appropriate WorkspaceManager /
SupervisedAgent / WatcherManager method.

Classes:
    ChatResponse  — one agent reply (success flag, message, optional data)
    ChatAgent     — parse + dispatch + reply
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from agents.command_parser import CommandIntent, CommandParser, ParsedCommand
from agents.file_watcher import WatcherManager

# ── ChatResponse ──────────────────────────────────────────────────────────────


@dataclass
class ChatResponse:
    """One response from the ChatAgent."""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    intent: str = ""

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "intent": self.intent,
        }


# ── ChatAgent ─────────────────────────────────────────────────────────────────


class ChatAgent:
    """
    Conversational front-end over the Expert Smart agent stack.

    Parameters
    ----------
    workspace_manager : WorkspaceManager
    supervised_agent  : SupervisedAgent (optional — only required for pipeline
                        and backup operations)
    watcher_manager   : WatcherManager (optional — created fresh if omitted)
    """

    def __init__(
        self,
        workspace_manager: Any,
        supervised_agent: Any = None,
        watcher_manager: Optional[WatcherManager] = None,
    ) -> None:
        self._wm = workspace_manager
        self._agent = supervised_agent
        self._watcher = watcher_manager or WatcherManager()
        self._parser = CommandParser()

    # ── Public ────────────────────────────────────────────────────────────────

    def chat(self, text: str, workspace_id: Optional[str] = None) -> ChatResponse:
        """Parse *text* and dispatch to the appropriate handler."""
        cmd = self._parser.parse(text)
        return self._dispatch(cmd, workspace_id)

    # ── Dispatch ──────────────────────────────────────────────────────────────

    def _dispatch(self, cmd: ParsedCommand, workspace_id: Optional[str]) -> ChatResponse:
        ws_id = cmd.params.get("workspace_id") or workspace_id
        intent = cmd.intent

        try:
            handlers = {
                CommandIntent.HELP: self._handle_help,
                CommandIntent.LIST_WORKSPACES: self._handle_list_workspaces,
                CommandIntent.CREATE_WORKSPACE: self._handle_create_workspace,
                CommandIntent.DELETE_WORKSPACE: self._handle_delete_workspace,
                CommandIntent.RUN_PIPELINE: self._handle_run_pipeline,
                CommandIntent.CREATE_BACKUP: self._handle_create_backup,
                CommandIntent.RESTORE_BACKUP: self._handle_restore_backup,
                CommandIntent.LIST_BACKUPS: self._handle_list_backups,
                CommandIntent.SHOW_STATUS: self._handle_show_status,
                CommandIntent.SHOW_LOG: self._handle_show_log,
                CommandIntent.SET_MODE: self._handle_set_mode,
                CommandIntent.WATCH_WORKSPACE: self._handle_watch,
                CommandIntent.UNWATCH_WORKSPACE: self._handle_unwatch,
            }
            handler = handlers.get(CommandIntent(intent))
            if handler:
                return handler(cmd, ws_id)  # type: ignore[return-value]
            return ChatResponse(
                success=False,
                intent=intent,
                message="I didn't understand that. Type 'help' to see available commands.",
            )
        except Exception as exc:
            return ChatResponse(success=False, intent=intent, message=f"Error: {exc}")

    # ── Handlers ──────────────────────────────────────────────────────────────

    def _handle_help(self, cmd: ParsedCommand, ws_id: Optional[str]) -> ChatResponse:
        return ChatResponse(
            success=True,
            intent=CommandIntent.HELP,
            message=self._parser.get_help_text(),
        )

    def _handle_list_workspaces(self, cmd: ParsedCommand, ws_id: Optional[str]) -> ChatResponse:
        ws_list = self._wm.list_workspaces()
        if not ws_list:
            return ChatResponse(
                success=True,
                intent=CommandIntent.LIST_WORKSPACES,
                message="No workspaces found.",
                data={"workspaces": []},
            )
        lines = [f"  • {w.name} ({w.workspace_id})" for w in ws_list]
        return ChatResponse(
            success=True,
            intent=CommandIntent.LIST_WORKSPACES,
            message=f"{len(ws_list)} workspace(s):\n" + "\n".join(lines),
            data={"workspaces": [w.to_dict() for w in ws_list]},
        )

    def _handle_create_workspace(self, cmd: ParsedCommand, ws_id: Optional[str]) -> ChatResponse:
        name = cmd.params.get("name") or "New Workspace"
        ws = self._wm.create_workspace(name)
        return ChatResponse(
            success=True,
            intent=CommandIntent.CREATE_WORKSPACE,
            message=f"Workspace '{ws.name}' created (id: {ws.workspace_id})",
            data=ws.to_dict(),
        )

    def _handle_delete_workspace(self, cmd: ParsedCommand, ws_id: Optional[str]) -> ChatResponse:
        if not ws_id:
            return ChatResponse(
                success=False,
                intent=CommandIntent.DELETE_WORKSPACE,
                message="Please provide a workspace_id to delete.",
            )
        ok = self._wm.delete_workspace(ws_id)
        if ok:
            return ChatResponse(
                success=True,
                intent=CommandIntent.DELETE_WORKSPACE,
                message=f"Workspace {ws_id} deleted.",
            )
        return ChatResponse(
            success=False,
            intent=CommandIntent.DELETE_WORKSPACE,
            message=f"Workspace {ws_id} not found.",
        )

    def _handle_run_pipeline(self, cmd: ParsedCommand, ws_id: Optional[str]) -> ChatResponse:
        if not ws_id:
            return ChatResponse(
                success=False,
                intent=CommandIntent.RUN_PIPELINE,
                message="Please provide a workspace_id to run the pipeline.",
            )
        if self._agent is None:
            return ChatResponse(
                success=False,
                intent=CommandIntent.RUN_PIPELINE,
                message="No supervised agent configured.",
            )
        purpose = cmd.params.get("primary_purpose", "market_value")
        report = self._agent.run_pipeline(ws_id, primary_purpose=purpose)
        return ChatResponse(
            success=True,
            intent=CommandIntent.RUN_PIPELINE,
            message=(
                f"Pipeline complete — "
                f"{report.completed} succeeded, "
                f"{report.failed} failed, "
                f"{report.skipped} skipped."
            ),
            data=report.to_dict(),
        )

    def _handle_create_backup(self, cmd: ParsedCommand, ws_id: Optional[str]) -> ChatResponse:
        if not ws_id:
            return ChatResponse(
                success=False,
                intent=CommandIntent.CREATE_BACKUP,
                message="Please provide a workspace_id to back up.",
            )
        if self._agent is None:
            return ChatResponse(
                success=False,
                intent=CommandIntent.CREATE_BACKUP,
                message="No supervised agent configured.",
            )
        label = cmd.params.get("label", "")
        info = self._agent.create_backup(ws_id, label=label)
        return ChatResponse(
            success=True,
            intent=CommandIntent.CREATE_BACKUP,
            message=f"Backup created: {info.label} ({info.backup_id})",
            data=info.to_dict(),
        )

    def _handle_restore_backup(self, cmd: ParsedCommand, ws_id: Optional[str]) -> ChatResponse:
        if not ws_id:
            return ChatResponse(
                success=False,
                intent=CommandIntent.RESTORE_BACKUP,
                message="Please provide a workspace_id.",
            )
        backup_id = cmd.params.get("backup_id")
        if not backup_id:
            return ChatResponse(
                success=False,
                intent=CommandIntent.RESTORE_BACKUP,
                message="Please provide the backup_id to restore.",
            )
        if self._agent is None:
            return ChatResponse(
                success=False,
                intent=CommandIntent.RESTORE_BACKUP,
                message="No supervised agent configured.",
            )
        ok = self._agent.restore_backup(ws_id, backup_id)
        if ok:
            return ChatResponse(
                success=True,
                intent=CommandIntent.RESTORE_BACKUP,
                message=f"Backup {backup_id} restored to workspace {ws_id}.",
            )
        return ChatResponse(
            success=False,
            intent=CommandIntent.RESTORE_BACKUP,
            message="Restore failed — backup or workspace not found.",
        )

    def _handle_list_backups(self, cmd: ParsedCommand, ws_id: Optional[str]) -> ChatResponse:
        if not ws_id:
            return ChatResponse(
                success=False,
                intent=CommandIntent.LIST_BACKUPS,
                message="Please provide a workspace_id.",
            )
        if self._agent is None:
            return ChatResponse(
                success=False,
                intent=CommandIntent.LIST_BACKUPS,
                message="No supervised agent configured.",
            )
        backups = self._agent._backup_mgr.list_backups(ws_id)
        if not backups:
            return ChatResponse(
                success=True,
                intent=CommandIntent.LIST_BACKUPS,
                message="No backups found for this workspace.",
                data={"backups": []},
            )
        lines = [f"  • {b.label} ({b.backup_id[:8]}…) — {b.file_count} files" for b in backups]
        return ChatResponse(
            success=True,
            intent=CommandIntent.LIST_BACKUPS,
            message=f"{len(backups)} backup(s):\n" + "\n".join(lines),
            data={"backups": [b.to_dict() for b in backups]},
        )

    def _handle_show_status(self, cmd: ParsedCommand, ws_id: Optional[str]) -> ChatResponse:
        ws_count = len(self._wm.list_workspaces())
        mode = str(getattr(self._agent, "_mode", "N/A")) if self._agent else "N/A"
        watched = self._watcher.list_watched()
        log_count = len(self._agent.get_action_log()) if self._agent else 0
        msg = (
            f"Agent status:\n"
            f"  Workspaces : {ws_count}\n"
            f"  Mode       : {mode}\n"
            f"  Watched    : {len(watched)}\n"
            f"  Log entries: {log_count}"
        )
        return ChatResponse(
            success=True,
            intent=CommandIntent.SHOW_STATUS,
            message=msg,
            data={
                "workspace_count": ws_count,
                "mode": mode,
                "watched": watched,
                "log_entries": log_count,
            },
        )

    def _handle_show_log(self, cmd: ParsedCommand, ws_id: Optional[str]) -> ChatResponse:
        if self._agent is None:
            return ChatResponse(
                success=False,
                intent=CommandIntent.SHOW_LOG,
                message="No supervised agent configured.",
            )
        log = self._agent.get_action_log()
        if not log:
            return ChatResponse(
                success=True,
                intent=CommandIntent.SHOW_LOG,
                message="Action log is empty.",
                data={"log": []},
            )
        recent = log[-10:]
        lines = [f"  {r.created_at[:19]} [{r.status:>9}] {r.action_type}" for r in recent]
        msg = f"{len(log)} action(s) (showing last {len(recent)}):\n" + "\n".join(lines)
        return ChatResponse(
            success=True,
            intent=CommandIntent.SHOW_LOG,
            message=msg,
            data={"log": [r.to_dict() for r in log]},
        )

    def _handle_set_mode(self, cmd: ParsedCommand, ws_id: Optional[str]) -> ChatResponse:
        mode = cmd.params.get("mode")
        if not mode:
            return ChatResponse(
                success=False,
                intent=CommandIntent.SET_MODE,
                message="Specify a mode: autonomous | supervised | manual | readonly",
            )
        if self._agent is None:
            return ChatResponse(
                success=False,
                intent=CommandIntent.SET_MODE,
                message="No supervised agent configured.",
            )
        self._agent.set_mode(mode)
        return ChatResponse(
            success=True,
            intent=CommandIntent.SET_MODE,
            message=f"Execution mode set to '{mode}'.",
            data={"mode": mode},
        )

    def _handle_watch(self, cmd: ParsedCommand, ws_id: Optional[str]) -> ChatResponse:
        if not ws_id:
            return ChatResponse(
                success=False,
                intent=CommandIntent.WATCH_WORKSPACE,
                message="Please provide a workspace_id to watch.",
            )
        ws = self._wm.get_workspace(ws_id)
        if ws is None:
            return ChatResponse(
                success=False,
                intent=CommandIntent.WATCH_WORKSPACE,
                message=f"Workspace {ws_id} not found.",
            )
        trigger = self._watcher.make_pipeline_trigger(self._agent, ws_id) if self._agent else lambda _: None
        self._watcher.watch(ws_id, ws.root_path, trigger)
        return ChatResponse(
            success=True,
            intent=CommandIntent.WATCH_WORKSPACE,
            message=f"Now watching workspace {ws_id}.",
        )

    def _handle_unwatch(self, cmd: ParsedCommand, ws_id: Optional[str]) -> ChatResponse:
        if not ws_id:
            return ChatResponse(
                success=False,
                intent=CommandIntent.UNWATCH_WORKSPACE,
                message="Please provide a workspace_id to unwatch.",
            )
        ok = self._watcher.unwatch(ws_id)
        if ok:
            return ChatResponse(
                success=True,
                intent=CommandIntent.UNWATCH_WORKSPACE,
                message=f"Stopped watching workspace {ws_id}.",
            )
        return ChatResponse(
            success=False,
            intent=CommandIntent.UNWATCH_WORKSPACE,
            message=f"Workspace {ws_id} was not being watched.",
        )
