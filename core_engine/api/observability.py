"""
observability.py — API Hardening: Structured Logging & Request Tracing
Attaches a UUID request_id to every request; logs request/response/error as JSON.
"""

from __future__ import annotations

import functools
import json
import logging
import time
import uuid
from typing import Optional


class StructuredLogger:
    """Emit structured JSON log lines for requests, responses, and errors."""

    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)

    def log_request(
        self,
        method:     str,
        path:       str,
        request_id: str,
        user_id:    Optional[str] = None,
    ) -> None:
        self._logger.info(json.dumps({
            "event":      "request_received",
            "request_id": request_id,
            "method":     method,
            "path":       path,
            "user_id":    user_id,
        }))

    def log_response(
        self,
        request_id:  str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        self._logger.info(json.dumps({
            "event":       "response_sent",
            "request_id":  request_id,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
        }))

    def log_error(
        self,
        request_id:    str,
        error_code:    str,
        error_message: str,
        stack_trace:   Optional[str] = None,
    ) -> None:
        self._logger.error(json.dumps({
            "event":         "error_occurred",
            "request_id":    request_id,
            "error_code":    error_code,
            "error_message": error_message,
            "stack_trace":   stack_trace,
        }))

    def log_database_query(
        self,
        request_id:  str,
        query_type:  str,
        duration_ms: float,
    ) -> None:
        self._logger.debug(json.dumps({
            "event":       "database_query",
            "request_id":  request_id,
            "query_type":  query_type,
            "duration_ms": round(duration_ms, 2),
        }))


def track_request(f):
    """
    Flask decorator — attaches a UUID request_id via Flask ``g``,
    logs request arrival and response timing.
    """
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        from flask import request, g

        request_id  = str(uuid.uuid4())
        g.request_id = request_id
        start       = time.time()

        _logger = StructuredLogger(__name__)
        _logger.log_request(
            method=request.method,
            path=request.path,
            request_id=request_id,
            user_id=request.headers.get("X-User-ID"),
        )

        try:
            result       = f(*args, **kwargs)
            duration_ms  = (time.time() - start) * 1000
            status_code  = result[1] if isinstance(result, tuple) else 200
            _logger.log_response(request_id, status_code, duration_ms)
            return result
        except Exception as exc:
            duration_ms = (time.time() - start) * 1000
            _logger.log_error(
                request_id=request_id,
                error_code=type(exc).__name__,
                error_message=str(exc),
            )
            raise

    return wrapper
