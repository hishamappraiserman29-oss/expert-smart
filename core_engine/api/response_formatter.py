"""
response_formatter.py — API Hardening: Consistent Response Format
All API responses share the same envelope: status, timestamp, data, errors, metadata.
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ResponseStatus(str, Enum):
    SUCCESS    = "success"
    ERROR      = "error"
    PROCESSING = "processing"
    PARTIAL    = "partial"


class StandardResponse:
    """Unified API response envelope."""

    def __init__(
        self,
        status:   ResponseStatus,
        data:     Optional[Any]         = None,
        message:  Optional[str]         = None,
        errors:   Optional[List[Dict]]  = None,
        metadata: Optional[Dict]        = None,
    ) -> None:
        self.status    = status
        self.data      = data
        self.message   = message
        self.errors    = errors or []
        self.metadata  = metadata or {}
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "status":    self.status.value,
            "timestamp": self.timestamp,
        }
        if self.message:
            result["message"] = self.message
        if self.data is not None:
            result["data"] = self.data
        if self.errors:
            result["errors"] = self.errors
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class ResponseFormatter:
    """Factory for StandardResponse objects."""

    @staticmethod
    def success(
        data:     Any  = None,
        message:  str  = None,
        metadata: Dict = None,
    ) -> StandardResponse:
        return StandardResponse(
            status=ResponseStatus.SUCCESS,
            data=data,
            message=message or "Operation completed successfully",
            metadata=metadata,
        )

    @staticmethod
    def error(
        message: str,
        errors:  List[Dict] = None,
        data:    Any        = None,
    ) -> StandardResponse:
        return StandardResponse(
            status=ResponseStatus.ERROR,
            message=message,
            errors=errors or [],
            data=data,
        )

    @staticmethod
    def processing(request_id: str, message: str = None) -> StandardResponse:
        return StandardResponse(
            status=ResponseStatus.PROCESSING,
            message=message or "Request is being processed",
            metadata={"request_id": request_id},
        )

    @staticmethod
    def partial(
        data:         Any,
        failed_count: int,
        message:      str = None,
    ) -> StandardResponse:
        return StandardResponse(
            status=ResponseStatus.PARTIAL,
            data=data,
            message=message or "Operation completed with some failures",
            metadata={"failed_count": failed_count},
        )

    @staticmethod
    def validation_error(field: str, error: str) -> StandardResponse:
        return StandardResponse(
            status=ResponseStatus.ERROR,
            message="Validation failed",
            errors=[{"field": field, "error": error, "code": "VALIDATION_ERROR"}],
        )


def format_response(response: StandardResponse, status_code: int = 200):
    """Return a Flask (jsonify, status_code) tuple."""
    from flask import jsonify
    return jsonify(response.to_dict()), status_code
