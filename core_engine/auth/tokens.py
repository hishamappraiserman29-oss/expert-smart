"""JWT token generation + verification.

Secret comes from JWT_SECRET env var. For tests, set it via monkeypatch.
Production deployments MUST set a strong secret; this module raises
AuthError if it is missing AND a token operation is attempted.
"""
from __future__ import annotations

import os
import time
from typing import Any

import jwt


class AuthError(Exception):
    """Raised for any token-related failure (missing secret, expired, tampered, ...)."""


_ALGORITHM = "HS256"
_DEFAULT_TTL_SECONDS = 3600   # 1 hour


def _get_secret() -> str:
    secret = os.environ.get("JWT_SECRET", "").strip()
    if not secret:
        raise AuthError(
            "JWT_SECRET environment variable is not set. "
            "Set a strong random secret before generating or verifying tokens."
        )
    return secret


def _get_ttl() -> int:
    raw = os.environ.get("JWT_TTL_SECONDS")
    if raw is None:
        return _DEFAULT_TTL_SECONDS
    try:
        ttl = int(raw)
        if ttl <= 0:
            raise ValueError
        return ttl
    except ValueError:
        raise AuthError(
            f"JWT_TTL_SECONDS must be a positive integer, got: {raw!r}"
        )


def generate_token(user_id: str, *, ttl_seconds: int | None = None) -> str:
    """Generate a signed JWT for *user_id*.

    Args:
        user_id: Non-empty identifier for the authenticated principal.
        ttl_seconds: Override token lifetime. None reads JWT_TTL_SECONDS
                     env var, or falls back to 3600 s.

    Returns:
        Encoded JWT string.

    Raises:
        AuthError: invalid user_id, negative TTL, or JWT_SECRET unset.
    """
    if not user_id or not isinstance(user_id, str):
        raise AuthError(f"user_id must be a non-empty string, got: {user_id!r}")

    ttl = ttl_seconds if ttl_seconds is not None else _get_ttl()
    if ttl <= 0:
        raise AuthError(f"ttl_seconds must be positive, got: {ttl}")

    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": user_id,
        "iat": now,
        "exp": now + ttl,
    }
    return jwt.encode(payload, _get_secret(), algorithm=_ALGORITHM)


def verify_token(token: str) -> dict[str, Any]:
    """Verify a JWT and return its decoded payload.

    Args:
        token: Encoded JWT string.

    Returns:
        Decoded payload dict with at least 'sub', 'iat', 'exp'.

    Raises:
        AuthError: missing/invalid/expired/tampered token, or JWT_SECRET unset.
    """
    if not token or not isinstance(token, str):
        raise AuthError("token must be a non-empty string")

    try:
        payload = jwt.decode(
            token,
            _get_secret(),
            algorithms=[_ALGORITHM],
            options={"require": ["sub", "iat", "exp"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthError(f"token expired: {exc}") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError(f"invalid token: {exc}") from exc

    sub = payload.get("sub")
    if not sub or not isinstance(sub, str):
        raise AuthError("token payload missing valid 'sub' claim")
    return payload
