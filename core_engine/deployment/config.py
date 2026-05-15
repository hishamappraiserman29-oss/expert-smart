"""
config.py — PH.5 Environment-Driven Configuration

Centralises every tuneable parameter in one place.  Values come from:
  1. Environment variables (highest priority)
  2. A .env file in the project root (if python-dotenv is installed)
  3. Hard-coded defaults (always safe for development)

All values are typed and validated before the application starts.

Classes:
    AppConfig        — single dataclass holding every config field
    ConfigValidator  — validates an AppConfig instance, returns issues
    load_config()    — build AppConfig from environment + .env file
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key, "")
    try:
        return int(raw.strip())
    except (ValueError, AttributeError):
        return default


def _env_bool(key: str, default: bool) -> bool:
    raw = os.environ.get(key, "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    return default


def _env_list(key: str, default: Optional[List[str]] = None, sep: str = ",") -> List[str]:
    raw = os.environ.get(key, "").strip()
    if not raw:
        return default or []
    return [item.strip() for item in raw.split(sep) if item.strip()]


# ---------------------------------------------------------------------------
# AppConfig
# ---------------------------------------------------------------------------

@dataclass
class AppConfig:
    """
    Central configuration for Expert Smart.

    Every field maps to an environment variable of the form
    ``EXPERT_SMART_<FIELD_NAME_UPPER>``.  Example:
        host   → EXPERT_SMART_HOST
        port   → EXPERT_SMART_PORT
    """

    # -- Server ---------------------------------------------------------------
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False
    workers: int = 4
    request_timeout: int = 60       # seconds

    # -- Security -------------------------------------------------------------
    secret_key: str = ""            # required in production
    allowed_origins: List[str] = field(
        default_factory=lambda: ["http://localhost:5000", "http://127.0.0.1:5000"]
    )
    max_content_length_mb: int = 50

    # -- Database -------------------------------------------------------------
    db_url: str = ""                # empty = SQLite default
    db_pool_size: int = 5
    db_pool_timeout: int = 30

    # -- Cache ----------------------------------------------------------------
    cache_max_size: int = 512
    cache_ttl_seconds: int = 300

    # -- Rate limiting --------------------------------------------------------
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60

    # -- MCP / Agent bridge ---------------------------------------------------
    mcp_bridge_url: str = "http://localhost:5000"
    mcp_timeout_seconds: int = 30

    # -- Workspaces -----------------------------------------------------------
    workspace_base_dir: str = ""    # empty = auto (system temp)
    max_workspace_size_mb: int = 1024

    # -- Logging --------------------------------------------------------------
    log_level: str = "INFO"
    log_file: str = ""              # empty = stdout only

    # -- Feature flags --------------------------------------------------------
    enable_agent_chat: bool = True
    enable_mcp_bridge: bool = True
    enable_rate_limiting: bool = True

    # -------------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        for f in fields(self):
            val = getattr(self, f.name)
            # Redact the secret key
            if f.name == "secret_key":
                val = "***" if val else ""
            d[f.name] = val
        return d

    @property
    def is_production(self) -> bool:
        return not self.debug and bool(self.secret_key)


# ---------------------------------------------------------------------------
# ConfigValidator
# ---------------------------------------------------------------------------

class ConfigValidator:
    """Validate an AppConfig instance and return a list of (field, issue) tuples."""

    VALID_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})

    @classmethod
    def validate(cls, cfg: AppConfig) -> List[Tuple[str, str]]:
        """
        Return a list of (field_name, error_message) pairs.
        An empty list means the config is valid.
        """
        issues: List[Tuple[str, str]] = []

        # Port
        if not (1 <= cfg.port <= 65535):
            issues.append(("port", f"Must be 1–65535, got {cfg.port}"))

        # Workers
        if cfg.workers < 1:
            issues.append(("workers", "Must be >= 1"))

        # Secret key in production
        if cfg.is_production and not cfg.secret_key:
            issues.append(("secret_key", "Required in production (debug=False)"))

        # Log level
        if cfg.log_level.upper() not in cls.VALID_LOG_LEVELS:
            issues.append(("log_level", f"Must be one of {sorted(cls.VALID_LOG_LEVELS)}"))

        # Cache
        if cfg.cache_max_size < 1:
            issues.append(("cache_max_size", "Must be >= 1"))
        if cfg.cache_ttl_seconds < 0:
            issues.append(("cache_ttl_seconds", "Must be >= 0"))

        # Rate limiting
        if cfg.rate_limit_requests < 1:
            issues.append(("rate_limit_requests", "Must be >= 1"))
        if cfg.rate_limit_window_seconds < 1:
            issues.append(("rate_limit_window_seconds", "Must be >= 1"))

        # Content length
        if cfg.max_content_length_mb < 1:
            issues.append(("max_content_length_mb", "Must be >= 1 MB"))

        # Workspace size
        if cfg.max_workspace_size_mb < 1:
            issues.append(("max_workspace_size_mb", "Must be >= 1 MB"))

        # Timeouts
        if cfg.request_timeout < 1:
            issues.append(("request_timeout", "Must be >= 1 second"))
        if cfg.mcp_timeout_seconds < 1:
            issues.append(("mcp_timeout_seconds", "Must be >= 1 second"))

        return issues

    @classmethod
    def is_valid(cls, cfg: AppConfig) -> bool:
        return len(cls.validate(cfg)) == 0


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------

def load_config(env_file: Optional[str] = None) -> AppConfig:
    """
    Build an AppConfig from environment variables.

    Optionally loads *env_file* (a path to a .env file) first.
    Falls back to searching for .env in the current directory and the
    directory two levels above this file (project root).

    Returns a fully populated AppConfig; never raises.
    """
    _load_dotenv(env_file)

    cfg = AppConfig(
        # Server
        host=_env("EXPERT_SMART_HOST", "0.0.0.0"),
        port=_env_int("EXPERT_SMART_PORT", 5000),
        debug=_env_bool("EXPERT_SMART_DEBUG", False),
        workers=_env_int("EXPERT_SMART_WORKERS", 4),
        request_timeout=_env_int("EXPERT_SMART_REQUEST_TIMEOUT", 60),
        # Security
        secret_key=_env("EXPERT_SMART_SECRET_KEY", ""),
        allowed_origins=_env_list(
            "EXPERT_SMART_ALLOWED_ORIGINS",
            ["http://localhost:5000", "http://127.0.0.1:5000"],
        ),
        max_content_length_mb=_env_int("EXPERT_SMART_MAX_CONTENT_MB", 50),
        # Database
        db_url=_env("EXPERT_SMART_DB_URL", ""),
        db_pool_size=_env_int("EXPERT_SMART_DB_POOL_SIZE", 5),
        db_pool_timeout=_env_int("EXPERT_SMART_DB_POOL_TIMEOUT", 30),
        # Cache
        cache_max_size=_env_int("EXPERT_SMART_CACHE_MAX_SIZE", 512),
        cache_ttl_seconds=_env_int("EXPERT_SMART_CACHE_TTL", 300),
        # Rate limiting
        rate_limit_requests=_env_int("EXPERT_SMART_RATE_LIMIT", 60),
        rate_limit_window_seconds=_env_int("EXPERT_SMART_RATE_WINDOW", 60),
        # MCP
        mcp_bridge_url=_env("EXPERT_SMART_MCP_URL", "http://localhost:5000"),
        mcp_timeout_seconds=_env_int("EXPERT_SMART_MCP_TIMEOUT", 30),
        # Workspaces
        workspace_base_dir=_env("EXPERT_SMART_WORKSPACE_DIR", ""),
        max_workspace_size_mb=_env_int("EXPERT_SMART_MAX_WORKSPACE_MB", 1024),
        # Logging
        log_level=_env("EXPERT_SMART_LOG_LEVEL", "INFO").upper(),
        log_file=_env("EXPERT_SMART_LOG_FILE", ""),
        # Feature flags
        enable_agent_chat=_env_bool("EXPERT_SMART_ENABLE_AGENT_CHAT", True),
        enable_mcp_bridge=_env_bool("EXPERT_SMART_ENABLE_MCP_BRIDGE", True),
        enable_rate_limiting=_env_bool("EXPERT_SMART_ENABLE_RATE_LIMITING", True),
    )
    return cfg


def _load_dotenv(env_file: Optional[str]) -> None:
    """Best-effort .env loader — silently skips if dotenv not installed."""
    try:
        from dotenv import load_dotenv  # type: ignore[import]
    except ImportError:
        return

    if env_file:
        load_dotenv(env_file, override=False)
        return

    # Auto-discover .env in cwd or project root
    candidates = [
        Path(".env"),
        Path(__file__).resolve().parent.parent.parent / ".env",
    ]
    for p in candidates:
        if p.exists():
            load_dotenv(str(p), override=False)
            return
