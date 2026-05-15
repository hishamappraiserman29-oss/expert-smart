"""
command_parser.py — Natural-Language Command Parser (Phase 21.0)

Converts free-text user input into structured ParsedCommand objects using
priority-ordered regex patterns.  No LLM dependency — fully deterministic.

Classes:
    CommandIntent   — all recognised agent actions
    ParsedCommand   — one classified command with extracted parameters
    CommandParser   — parse() + get_help_text()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, Dict, Optional

# ── CommandIntent ─────────────────────────────────────────────────────────────


class CommandIntent(str, Enum):
    RUN_PIPELINE = "run_pipeline"
    CREATE_BACKUP = "create_backup"
    RESTORE_BACKUP = "restore_backup"
    LIST_BACKUPS = "list_backups"
    CREATE_WORKSPACE = "create_workspace"
    DELETE_WORKSPACE = "delete_workspace"
    LIST_WORKSPACES = "list_workspaces"
    WATCH_WORKSPACE = "watch_workspace"
    UNWATCH_WORKSPACE = "unwatch_workspace"
    SHOW_STATUS = "show_status"
    SHOW_LOG = "show_log"
    SET_MODE = "set_mode"
    HELP = "help"
    UNKNOWN = "unknown"


# ── ParsedCommand ─────────────────────────────────────────────────────────────


@dataclass
class ParsedCommand:
    """One classified user command with extracted parameters."""

    intent: str
    params: Dict[str, Any]
    raw_text: str
    confidence: float = 1.0  # 0.0 = no match, 1.0 = pattern matched

    def to_dict(self) -> Dict:
        return {
            "intent": self.intent,
            "params": self.params,
            "raw_text": self.raw_text,
            "confidence": self.confidence,
        }


# ── Compiled patterns ─────────────────────────────────────────────────────────

_UUID_RE = re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', re.I)
_QUOTED_RE = re.compile(r'"([^"]+)"|\'([^\']+)\'')
_MODE_RE = re.compile(r'\b(autonomous|supervised|manual|readonly)\b', re.I)
_PURPOSE_RE = re.compile(r'\b(market_value|mortgage|insurance|ifrs_13)\b', re.I)

# Priority order: first match wins.
_INTENT_PATTERNS = [
    (CommandIntent.HELP, re.compile(r'^\s*[?]+\s*$|\bhelp\b', re.I)),
    (
        CommandIntent.RUN_PIPELINE,
        re.compile(
            r'\brun\b.{0,30}\bpipeline\b'
            r'|\bstart\b.{0,30}\bpipeline\b'
            r'|\bpipeline\b.{0,20}\brun\b'
            r'|\bexecute\b.{0,30}\bpipeline\b'
            r'|\bprocess\b.{0,30}\bpipeline\b'
            r'|\bvaluate\b'
            r'|\brun\b.{0,20}\bvaluat',
            re.I,
        ),
    ),
    (CommandIntent.RESTORE_BACKUP, re.compile(r'\brestore\b', re.I)),
    (
        CommandIntent.CREATE_BACKUP,
        re.compile(
            r'\b(?:create|make|take|new)\b.{0,20}\bbackup\b'
            r'|\bbackup\b.{0,20}\b(?:create|make|now)\b'
            r'|\bsnapshot\b',
            re.I,
        ),
    ),
    (
        CommandIntent.LIST_BACKUPS,
        re.compile(r'\b(?:list|show|get)\b.{0,20}\bbackup' r'|\bbackup.{0,20}\b(?:list|show)\b', re.I),
    ),
    (CommandIntent.CREATE_WORKSPACE, re.compile(r'\b(?:create|new|add)\b.{0,20}\bworkspace\b', re.I)),
    (CommandIntent.DELETE_WORKSPACE, re.compile(r'\b(?:delete|remove|drop)\b.{0,20}\bworkspace\b', re.I)),
    (
        CommandIntent.LIST_WORKSPACES,
        re.compile(r'\b(?:list|show|get)\b.{0,20}\bworkspace' r'|\bworkspace.{0,20}\b(?:list|show)\b', re.I),
    ),
    (
        CommandIntent.WATCH_WORKSPACE,
        re.compile(r'\b(?:watch|monitor|observe)\b.{0,20}\bworkspace\b' r'|\bstart\b.{0,20}\bwatch\b', re.I),
    ),
    (CommandIntent.UNWATCH_WORKSPACE, re.compile(r'\bunwatch\b|\bstop\b.{0,20}\b(?:watch|monitor)\b', re.I)),
    (CommandIntent.SHOW_LOG, re.compile(r'\b(?:log|logs|history|audit|actions?)\b', re.I)),
    (CommandIntent.SHOW_STATUS, re.compile(r'\b(?:status|state|health|info)\b', re.I)),
    (
        CommandIntent.SET_MODE,
        re.compile(
            r'\bset\b.{0,20}\bmode\b'
            r'|\bmode\b.{0,20}\bset\b'
            r'|\bswitch\b.{0,20}\bmode\b'
            r'|\b(?:autonomous|supervised|manual|readonly)\b',
            re.I,
        ),
    ),
]


# ── CommandParser ─────────────────────────────────────────────────────────────


class CommandParser:
    """
    Rule-based parser: regex patterns → CommandIntent + parameter extraction.

    Usage
    -----
    parser = CommandParser()
    cmd    = parser.parse("run pipeline on ws-abc")
    # → ParsedCommand(intent="run_pipeline", params={"workspace_id": "ws-abc"}, …)
    """

    def parse(self, text: str) -> ParsedCommand:
        stripped = text.strip()
        if not stripped:
            return ParsedCommand(
                intent=CommandIntent.UNKNOWN,
                params={},
                raw_text=text,
                confidence=0.0,
            )

        intent = CommandIntent.UNKNOWN
        confidence = 0.5

        for candidate, pattern in _INTENT_PATTERNS:
            if pattern.search(stripped):
                intent = candidate
                confidence = 1.0
                break

        params = self._extract_params(stripped, intent)
        return ParsedCommand(intent=intent, params=params, raw_text=text, confidence=confidence)

    # ── Parameter extraction ──────────────────────────────────────────────────

    def _extract_params(self, text: str, intent: str) -> Dict[str, Any]:
        params: Dict[str, Any] = {}

        # UUID detection — route to workspace_id or backup_id by intent
        uuids = _UUID_RE.findall(text)
        if uuids:
            if intent in (
                CommandIntent.RESTORE_BACKUP,
                CommandIntent.LIST_BACKUPS,
            ):
                params["backup_id"] = uuids[0]
                if len(uuids) > 1:
                    params["workspace_id"] = uuids[1]
            else:
                params["workspace_id"] = uuids[0]
                if len(uuids) > 1:
                    params["backup_id"] = uuids[1]

        # Execution mode
        m = _MODE_RE.search(text)
        if m:
            params["mode"] = m.group(1).lower()

        # Quoted string → name (workspace) or label (backup)
        q = _QUOTED_RE.search(text)
        if q:
            value = q.group(1) or q.group(2)
            if intent == CommandIntent.CREATE_WORKSPACE:
                params["name"] = value
            elif intent == CommandIntent.CREATE_BACKUP:
                params["label"] = value

        # Valuation purpose
        p = _PURPOSE_RE.search(text)
        if p:
            params["primary_purpose"] = p.group(1).lower()

        return params

    # ── Help text ─────────────────────────────────────────────────────────────

    def get_help_text(self) -> str:
        return (
            "Available commands:\n"
            "  run pipeline [on <workspace_id>]         — Run valuation pipeline\n"
            "  create backup [\"<label>\"]                 — Snapshot workspace\n"
            "  restore backup <backup_id>               — Restore a backup\n"
            "  list backups [<workspace_id>]            — Show all backups\n"
            "  create workspace \"<name>\"                — New workspace\n"
            "  delete workspace <workspace_id>          — Remove workspace\n"
            "  list workspaces                          — Show all workspaces\n"
            "  watch workspace <workspace_id>           — Start folder watcher\n"
            "  unwatch workspace <workspace_id>         — Stop folder watcher\n"
            "  status                                   — Agent status summary\n"
            "  log / history                            — Last 10 actions\n"
            "  set mode <autonomous|supervised|manual|readonly>\n"
            "  help / ?                                 — This message\n"
        )
