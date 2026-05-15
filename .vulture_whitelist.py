"""
vulture_whitelist.py — False-positive suppression for vulture dead-code scan.

Vulture flags names that appear unused at static analysis time but are:
  - Flask route functions (called by the framework, not by our code)
  - Enum values referenced by string
  - Dataclass fields accessed via to_dict() / **dataclass_fields
  - Public API surface used by external callers (MCP tools, tests)
"""

# ── Flask route handlers — all decorated with @app.route ─────────────────────
# vulture sees these as unreferenced functions; Flask calls them by introspection
def health_check(): pass
def get_valuation(): pass
def post_valuation(): pass
def generate_report(): pass
def batch_valuate(): pass
def get_batch_status(): pass
def list_batches(): pass
def dcf_analyze(): pass
def portfolio_analyze(): pass
def portfolio_performance(): pass
def enterprise_create_tenant(): pass
def enterprise_get_tenant(): pass
def enterprise_add_user(): pass
def enterprise_get_license(): pass
def enterprise_get_audit(): pass
def agent_chat(): pass
def agent_chat_ui(): pass
def mass_appraisal_ui(): pass

# ── Enum values used by string comparison ────────────────────────────────────
from agents.supervised_agent import ExecutionMode, ActionType
from agents.pipeline_orchestrator import PipelineStatus
from agents.file_watcher import WatchEventType
from agents.command_parser import CommandIntent
from agents.workspace_manager import WorkspaceStatus

_ = ExecutionMode.AUTONOMOUS
_ = ExecutionMode.SUPERVISED
_ = ExecutionMode.MANUAL
_ = ExecutionMode.READONLY
_ = ActionType.SCAN
_ = ActionType.READ_FILE
_ = ActionType.WRITE_FILE
_ = ActionType.DELETE_FILE
_ = ActionType.VALUATE
_ = ActionType.BACKUP
_ = ActionType.RESTORE
_ = ActionType.RUN_PIPELINE
_ = PipelineStatus.IDLE
_ = PipelineStatus.SCANNING
_ = PipelineStatus.PARSING
_ = PipelineStatus.VALUATING
_ = PipelineStatus.SAVING
_ = PipelineStatus.COMPLETED
_ = PipelineStatus.FAILED
_ = PipelineStatus.CANCELLED
_ = WatchEventType.CREATED
_ = WatchEventType.MODIFIED
_ = WatchEventType.DELETED
_ = CommandIntent.RUN_PIPELINE
_ = CommandIntent.CREATE_BACKUP
_ = CommandIntent.RESTORE_BACKUP
_ = CommandIntent.LIST_BACKUPS
_ = CommandIntent.CREATE_WORKSPACE
_ = CommandIntent.DELETE_WORKSPACE
_ = CommandIntent.LIST_WORKSPACES
_ = CommandIntent.WATCH_WORKSPACE
_ = CommandIntent.UNWATCH_WORKSPACE
_ = CommandIntent.SHOW_STATUS
_ = CommandIntent.SHOW_LOG
_ = CommandIntent.SET_MODE
_ = CommandIntent.HELP
_ = CommandIntent.UNKNOWN
_ = WorkspaceStatus.ACTIVE
_ = WorkspaceStatus.READONLY
_ = WorkspaceStatus.ARCHIVED

# ── Dataclass fields accessed via to_dict() ───────────────────────────────────
# These fields appear "unused" to vulture since they're read reflectively
from agents.supervised_agent import ActionRecord, BackupInfo
from agents.pipeline_orchestrator import PropertyRecord, PipelineResult, PipelineReport
from agents.file_watcher import FileEvent
from agents.command_parser import ParsedCommand
from agents.chat_agent import ChatResponse
from agents.workspace_manager import WorkspaceInfo
from agents.file_scanner import ScannedFile

_ = ActionRecord.completed_at
_ = ActionRecord.error
_ = BackupInfo.backup_path
_ = BackupInfo.file_count
_ = BackupInfo.size_bytes
_ = PipelineReport.output_file
_ = PipelineReport.results
_ = PipelineResult.valuation_value
_ = PipelineResult.error
_ = PipelineResult.processed_at
_ = FileEvent.absolute_path
_ = ParsedCommand.confidence
_ = ChatResponse.data
_ = WorkspaceInfo.total_size_bytes
_ = WorkspaceInfo.file_count
