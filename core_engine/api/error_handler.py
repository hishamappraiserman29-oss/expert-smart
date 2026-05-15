"""
error_handler.py — API Hardening: Centralised Error Handling
Structured error classes with HTTP status codes and a catch-all Flask decorator.
TimeoutError is exported as an alias for OperationTimeoutError (spec compat).
"""

from __future__ import annotations

import builtins
import functools
import logging
import traceback
from enum import Enum
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Stash built-in before any aliasing
_builtin_TimeoutError = builtins.TimeoutError


class ErrorCode(str, Enum):
    VALIDATION_ERROR      = "VALIDATION_ERROR"
    NOT_FOUND             = "NOT_FOUND"
    UNAUTHORIZED          = "UNAUTHORIZED"
    FORBIDDEN             = "FORBIDDEN"
    CONFLICT              = "CONFLICT"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    SERVICE_UNAVAILABLE   = "SERVICE_UNAVAILABLE"
    TIMEOUT               = "TIMEOUT"
    RATE_LIMITED          = "RATE_LIMITED"
    DATABASE_ERROR        = "DATABASE_ERROR"


class APIError(Exception):
    """Base class for all structured API errors."""

    def __init__(
        self,
        code:        ErrorCode,
        message:     str,
        status_code: int            = 500,
        details:     Optional[Dict] = None,
    ) -> None:
        self.code        = code
        self.message     = message
        self.status_code = status_code
        self.details     = details or {}
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code":    self.code.value,
            "message": self.message,
            "details": self.details,
        }


class ValidationError(APIError):
    def __init__(self, field: str, message: str) -> None:
        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"Validation failed: {message}",
            status_code=400,
            details={"field": field},
        )


class NotFoundError(APIError):
    def __init__(self, resource: str, identifier: str) -> None:
        super().__init__(
            code=ErrorCode.NOT_FOUND,
            message=f"{resource} not found",
            status_code=404,
            details={"resource": resource, "identifier": identifier},
        )


class OperationTimeoutError(APIError):
    """Timeout error — named to avoid shadowing Python's built-in TimeoutError."""

    def __init__(self, operation: str, timeout_seconds: float) -> None:
        super().__init__(
            code=ErrorCode.TIMEOUT,
            message=f"{operation} timed out after {timeout_seconds}s",
            status_code=504,
            details={"operation": operation, "timeout": timeout_seconds},
        )


# Spec-compatibility alias
TimeoutError = OperationTimeoutError  # noqa: A001


class DatabaseError(APIError):
    def __init__(self, message: str) -> None:
        super().__init__(
            code=ErrorCode.DATABASE_ERROR,
            message=f"Database error: {message}",
            status_code=500,
        )


def handle_api_error(func: Callable) -> Callable:
    """Decorator — catches all exceptions and returns structured JSON errors."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        from flask import jsonify
        try:
            return func(*args, **kwargs)
        except APIError as exc:
            logger.error("APIError %s: %s", exc.code.value, exc.message)
            return jsonify({"status": "error", "error": exc.to_dict()}), exc.status_code
        except _builtin_TimeoutError as exc:
            logger.error("Timeout: %s", exc)
            return jsonify({"status": "error", "error": {
                "code": ErrorCode.TIMEOUT.value,
                "message": "Operation timed out",
            }}), 504
        except ConnectionError as exc:
            logger.error("Connection error: %s", exc)
            return jsonify({"status": "error", "error": {
                "code": ErrorCode.SERVICE_UNAVAILABLE.value,
                "message": "Service temporarily unavailable",
            }}), 503
        except Exception as exc:
            logger.error("Unexpected error: %s\n%s", exc, traceback.format_exc())
            return jsonify({"status": "error", "error": {
                "code": ErrorCode.INTERNAL_SERVER_ERROR.value,
                "message": "Internal server error",
            }}), 500

    return wrapper
