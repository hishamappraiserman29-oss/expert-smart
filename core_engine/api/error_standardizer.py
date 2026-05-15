"""
error_standardizer.py — Error Standardizer (Phase 38)

Consistent error responses with codes, request IDs, and structured details.
Note: Uses a separate ErrorCode enum from api/error_handler.py (Phase API Hardening).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class StandardErrorCode(str, Enum):
    INVALID_REQUEST = "INVALID_REQUEST"
    AUTHENTICATION_FAILED = "AUTH_FAILED"
    AUTHORIZATION_FAILED = "AUTHZ_FAILED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"


# Alias exposed as ErrorCode for spec compatibility
ErrorCode = StandardErrorCode


@dataclass
class StandardError:
    error_code: StandardErrorCode
    error_message: str
    http_status: int
    request_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    details: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.details is None:
            self.details = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": {
                "code": self.error_code.value,
                "message": self.error_message,
                "request_id": self.request_id,
                "timestamp": self.timestamp.isoformat(),
                "details": self.details,
            }
        }


class ErrorStandardizer:
    """Factory for consistent StandardError responses."""

    def __init__(self) -> None:
        logger.info("Error Standardizer initialized")

    def create_error(
        self,
        error_code: StandardErrorCode,
        message: str,
        status: int,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> StandardError:
        error = StandardError(
            error_code=error_code,
            error_message=message,
            http_status=status,
            request_id=request_id,
            details=details or {},
        )
        logger.warning("Error %d [%s]: %s", status, error_code.value, message)
        return error

    def handle_validation_error(
        self,
        errors: List[str],
        request_id: Optional[str] = None,
    ) -> StandardError:
        return self.create_error(
            error_code=StandardErrorCode.VALIDATION_ERROR,
            message=f"Request validation failed ({len(errors)} error{'s' if len(errors) != 1 else ''})",
            status=400,
            request_id=request_id,
            details={"validation_errors": errors},
        )

    def handle_auth_error(self, request_id: Optional[str] = None) -> StandardError:
        return self.create_error(
            error_code=StandardErrorCode.AUTHENTICATION_FAILED,
            message="Invalid or missing authentication credentials",
            status=401,
            request_id=request_id,
        )

    def handle_rate_limit(
        self,
        remaining: int,
        reset: datetime,
        request_id: Optional[str] = None,
    ) -> StandardError:
        return self.create_error(
            error_code=StandardErrorCode.RATE_LIMIT_EXCEEDED,
            message="Rate limit exceeded",
            status=429,
            request_id=request_id,
            details={"remaining_requests": remaining, "reset_at": reset.isoformat()},
        )

    def handle_not_found(
        self, resource: str, request_id: Optional[str] = None
    ) -> StandardError:
        return self.create_error(
            error_code=StandardErrorCode.NOT_FOUND,
            message=f"{resource} not found",
            status=404,
            request_id=request_id,
        )

    def handle_internal_error(
        self, detail: str = "", request_id: Optional[str] = None
    ) -> StandardError:
        return self.create_error(
            error_code=StandardErrorCode.INTERNAL_ERROR,
            message="An internal server error occurred",
            status=500,
            request_id=request_id,
            details={"detail": detail} if detail else {},
        )


error_standardizer = ErrorStandardizer()
