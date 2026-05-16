"""Audit logging for protected endpoint accesses (Auth Wave S5).

Best-effort: write failures are swallowed silently — audit must never
break the response. Production deployments should monitor write failures
via external mechanisms (e.g., DB disk-space alerts).

DB path resolution order:
  1. explicit db_path kwarg (used by unit tests)
  2. AUDIT_DB_PATH env var (used by integration tests via monkeypatch)
  3. DEFAULT_DB_PATH from reports.db.db_engine (production default)
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def is_enabled() -> bool:
    """AUDIT_ENABLED=false disables all logging (default true)."""
    return os.environ.get("AUDIT_ENABLED", "true").lower() == "true"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_db_path(db_path: Path | str | None) -> Path:
    """Resolve effective DB path with 3-level precedence."""
    if db_path is not None:
        return Path(db_path)
    env = os.environ.get("AUDIT_DB_PATH", "")
    if env:
        return Path(env)
    from reports.db.db_engine import DEFAULT_DB_PATH
    return DEFAULT_DB_PATH


def _open(db_path: Path) -> sqlite3.Connection:
    """Open a migrated connection. Callers must close it."""
    from reports.db.db_engine import _connect
    return _connect(db_path)


def log_access(
    *,
    user_id: str | None,
    endpoint: str,
    method: str,
    status: int,
    report_id: str | None = None,
    ip: str | None = None,
    db_path: Path | str | None = None,
) -> None:
    """Write one audit row to report_access_log. Never raises.

    Args:
        user_id:   From g.user_id (None for unauthenticated requests).
        endpoint:  request.path.
        method:    HTTP method.
        status:    Response status code.
        report_id: Extracted from URL params when applicable.
        ip:        request.remote_addr.
        db_path:   Override DB path (tests only; None uses env/default).
    """
    if not is_enabled():
        return
    try:
        conn = _open(_resolve_db_path(db_path))
        try:
            conn.execute(
                "INSERT INTO report_access_log "
                "(user_id, endpoint, method, status, report_id, ip, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, endpoint, method, int(status), report_id, ip, _utc_now_iso()),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass  # best-effort: never propagate audit failures to the caller


def fetch_audit_logs(
    *,
    user_id: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Query the audit log. For admin / forensics use; not exposed via HTTP in S5.

    Returns rows ordered by created_at DESC.
    """
    conn = _open(_resolve_db_path(db_path))
    try:
        clauses: list[str] = []
        params: list[Any] = []
        if user_id is not None:
            clauses.append("user_id = ?")
            params.append(user_id)
        if since is not None:
            clauses.append("created_at >= ?")
            params.append(since)
        if until is not None:
            clauses.append("created_at <= ?")
            params.append(until)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        params.extend([limit, offset])
        cur = conn.execute(
            f"SELECT id, user_id, endpoint, method, status, report_id, ip, created_at "
            f"FROM report_access_log{where} "
            f"ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params,
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()
