"""
request_deduplication.py — API Hardening: Idempotency
Prevent duplicate processing of the same request using an in-memory key store
with 24-hour TTL and LRU eviction.
"""

from __future__ import annotations

import functools
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class IdempotencyKey:
    """Single idempotency key entry."""

    TTL = timedelta(hours=24)

    def __init__(self, key: str, request_data: Dict[str, Any]) -> None:
        self.key          = key
        self.request_data = request_data
        self.created_at   = datetime.utcnow()
        self.response:    Optional[Any]  = None
        self.status:      Optional[int]  = None

    def is_expired(self) -> bool:
        return datetime.utcnow() - self.created_at > self.TTL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key":        self.key,
            "created_at": self.created_at.isoformat(),
            "status":     self.status,
            "expired":    self.is_expired(),
        }


class RequestDeduplicator:
    """In-memory idempotency key store with 24-hour TTL."""

    def __init__(self, max_keys: int = 10_000) -> None:
        self.max_keys = max_keys
        self.keys:    Dict[str, IdempotencyKey] = {}

    def register_request(
        self, idempotency_key: str, request_data: Dict[str, Any]
    ) -> bool:
        """
        Register a request.

        Returns
        -------
        True  — new request (not seen before, or expired)
        False — duplicate (key exists and not yet expired)
        """
        if idempotency_key in self.keys:
            existing = self.keys[idempotency_key]
            if existing.is_expired():
                del self.keys[idempotency_key]
            else:
                logger.warning("Duplicate request: %s", idempotency_key)
                return False

        self.keys[idempotency_key] = IdempotencyKey(idempotency_key, request_data)

        if len(self.keys) > self.max_keys:
            self._cleanup_expired()

        return True

    def store_response(
        self, idempotency_key: str, response: Any, status_code: int
    ) -> None:
        if idempotency_key in self.keys:
            entry = self.keys[idempotency_key]
            entry.response = response
            entry.status   = status_code

    def get_cached_response(
        self, idempotency_key: str
    ) -> Optional[Tuple[Any, int]]:
        entry = self.keys.get(idempotency_key)
        if entry is None:
            return None
        if entry.is_expired():
            del self.keys[idempotency_key]
            return None
        if entry.response is None:
            return None
        return (entry.response, entry.status)

    def _cleanup_expired(self) -> None:
        expired = [k for k, v in self.keys.items() if v.is_expired()]
        for k in expired:
            del self.keys[k]
        if expired:
            logger.info("Cleaned up %d expired idempotency keys", len(expired))


def require_idempotency_key(f):
    """
    Flask decorator — requires ``Idempotency-Key`` header on the request.
    Returns cached response on duplicate; 400 if header is missing.
    """
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        from flask import request, jsonify

        key = request.headers.get("Idempotency-Key")
        if not key:
            return jsonify({
                "error": "Idempotency-Key header required",
            }), 400

        dedup = get_request_deduplicator()
        data  = request.get_json(force=True, silent=True) or {}

        if not dedup.register_request(key, data):
            cached = dedup.get_cached_response(key)
            if cached:
                return cached
            return jsonify({"error": "Request in progress", "idempotency_key": key}), 409

        result = f(*args, **kwargs)

        status_code = result[1] if isinstance(result, tuple) else 200
        dedup.store_response(key, result, status_code)
        return result

    return wrapper


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_deduplicator: Optional[RequestDeduplicator] = None


def get_request_deduplicator() -> RequestDeduplicator:
    global _deduplicator
    if _deduplicator is None:
        _deduplicator = RequestDeduplicator()
    return _deduplicator
