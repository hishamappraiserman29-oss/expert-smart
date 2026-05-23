"""
DEV ONLY — local authentication bootstrap.

Exposes GET /api/dev/auth-token which issues a signed JWT using the running
server's own JWT_SECRET so that local development review does not require
manual token generation or JWT-secret juggling.

The endpoint is completely invisible in all non-dev environments:

    Guard 1  EXPERT_SMART_DEV_AUTH env var must equal exactly "1"
    Guard 2  FLASK_ENV must NOT be "production"
    Guard 3  Request Host must be localhost / 127.0.0.1 / ::1

Guards 1+2 failing  →  404  (endpoint does not exist conceptually)
Guard 3 failing     →  403  (endpoint exists but caller is not local)

Invariants enforced here:
  - @require_auth is NOT touched.
  - No existing protected route is weakened.
  - The full token is never written to any log.
  - No real secret is hardcoded in this file.

To enable (PowerShell):
    $env:EXPERT_SMART_DEV_AUTH = "1"
    $env:JWT_SECRET             = "local-dev-secret-EXPERT-SMART-2026-change-me-32chars"

Registration: bridge_api.py calls register(app) inside a try/except ImportError
block so that deleting this file never affects the running server.
"""
from __future__ import annotations

import os

from flask import jsonify, request

# Hosts accepted as "localhost" for Guard 3
_LOCAL_HOSTS: frozenset[str] = frozenset({"localhost", "127.0.0.1", "::1"})

# Dev-token lifetime: 7 days — generous for review, short enough to force refresh.
# This value is independent of JWT_TTL_SECONDS; the endpoint always uses it.
_DEV_TOKEN_TTL: int = 604_800


def _dev_mode_active() -> bool:
    """Return True iff Guards 1 and 2 both pass."""
    if os.environ.get("EXPERT_SMART_DEV_AUTH", "").strip() != "1":
        return False
    if os.environ.get("FLASK_ENV", "").lower() == "production":
        return False
    return True


def _request_is_local() -> bool:
    """Return True iff the request Host header resolves to localhost (Guard 3)."""
    host = request.host.split(":")[0].strip().lower()
    return host in _LOCAL_HOSTS


def register(app) -> None:  # type: ignore[type-arg]
    """Register GET /api/dev/auth-token on *app*.

    Called once from bridge_api.py.  Importing auth.tokens is deferred to
    inside the view function so the module is importable even if auth/ is not
    yet on sys.path at import time.
    """

    @app.route("/api/dev/auth-token", methods=["GET"])
    def dev_auth_token():  # type: ignore[return]
        """DEV ONLY — issue a short-lived JWT for local development review.

        Query params:
            user_id  (str, optional)  Identity for the token subject.
                                      Defaults to "local-admin".

        Returns 404 when EXPERT_SMART_DEV_AUTH != "1" or FLASK_ENV == "production".
        Returns 403 when the request Host is not localhost / 127.0.0.1.
        Returns 200 with {status, user_id, token, localStorageSnippet} on success.
        """
        # ── Guard 1 + Guard 2 ─────────────────────────────────────────────────
        if not _dev_mode_active():
            return jsonify({"status": "not_found"}), 404

        # ── Guard 3 ───────────────────────────────────────────────────────────
        if not _request_is_local():
            return jsonify({"status": "forbidden", "reason": "localhost only"}), 403

        # ── Resolve user_id ───────────────────────────────────────────────────
        user_id = (request.args.get("user_id", "") or "").strip() or "local-admin"

        # ── Generate token (uses server's live JWT_SECRET) ────────────────────
        try:
            # Import here so that importing dev_auth itself never hard-requires
            # auth.tokens to be on sys.path (safe for test isolation).
            from auth.tokens import generate_token as _gen  # noqa: PLC0415
            token = _gen(user_id, ttl_seconds=_DEV_TOKEN_TTL)
        except Exception as exc:  # noqa: BLE001
            return jsonify({"status": "error", "message": str(exc)}), 500

        # ── Log only a masked prefix — never the full token ───────────────────
        masked = (token[:12] + "...") if len(token) > 12 else "***"
        app.logger.info("[DEV AUTH] token issued user_id=%r prefix=%s", user_id, masked)

        # ── Build localStorage snippet ─────────────────────────────────────────
        ls_snippet = (
            "localStorage.setItem('es_auth', JSON.stringify({"
            f"token: '{token}', "
            f"user_id: '{user_id}', "
            "is_admin: false"
            "})); location.reload();"
        )

        return jsonify({
            "status": "ok",
            "user_id": user_id,
            "token": token,
            "localStorageSnippet": ls_snippet,
        }), 200
