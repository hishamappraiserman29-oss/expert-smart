"""Admin authorization primitives.

Admin identity is determined by the ADMIN_USER_IDS env var
(comma-separated user_ids). For example:
    ADMIN_USER_IDS=alice,bob,operations@example.com

Future upgrade path: replace with JWT role claim (role == 'admin').
"""
from __future__ import annotations

import os
from functools import wraps
from typing import Callable

from flask import g, jsonify


def _admin_set() -> set[str]:
    """Parse ADMIN_USER_IDS into a set. Empty if env var unset."""
    raw = os.environ.get("ADMIN_USER_IDS", "")
    return {x.strip() for x in raw.split(",") if x.strip()}


def is_admin(user_id: str | None) -> bool:
    """True iff user_id is in the configured admin set."""
    if not user_id:
        return False
    return user_id in _admin_set()


def require_admin(fn: Callable) -> Callable:
    """Reject non-admin requests.

    401 if no authenticated user (no token / invalid token).
    403 if authenticated but not in admin set.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = getattr(g, "user_id", None)
        if not user_id:
            return jsonify({
                "status": "unauthorized",
                "message": "Authentication required",
            }), 401
        if not is_admin(user_id):
            return jsonify({
                "status": "forbidden",
                "message": "Admin access required",
            }), 403
        return fn(*args, **kwargs)
    return wrapper
