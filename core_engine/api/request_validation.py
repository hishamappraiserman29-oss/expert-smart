"""
request_validation.py — Request/Response Validation (Phase 38)

Schema-based validation, type checking, input sanitization.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class ValidationType(str, Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    CONDITIONAL = "conditional"


class DataType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    DATETIME = "datetime"
    EMAIL = "email"
    URL = "url"


class RequestValidator:
    """Schema-based API request validator."""

    def __init__(self) -> None:
        self.schemas: Dict[str, Dict[str, Any]] = {
            "valuation": {
                "property_id": {
                    "type": DataType.STRING,
                    "validation": ValidationType.REQUIRED,
                    "min_length": 1,
                    "max_length": 50,
                },
                "area_sqm": {
                    "type": DataType.FLOAT,
                    "validation": ValidationType.REQUIRED,
                    "min": 10,
                    "max": 100_000,
                },
                "location": {
                    "type": DataType.STRING,
                    "validation": ValidationType.REQUIRED,
                    "min_length": 2,
                    "max_length": 100,
                },
                "price": {
                    "type": DataType.FLOAT,
                    "validation": ValidationType.OPTIONAL,
                    "min": 0,
                },
            },
            "search": {
                "property_type": {
                    "type": DataType.STRING,
                    "validation": ValidationType.REQUIRED,
                    "allowed_values": ["residential", "commercial", "industrial"],
                },
                "distance_km": {
                    "type": DataType.FLOAT,
                    "validation": ValidationType.OPTIONAL,
                    "min": 0,
                    "max": 50,
                },
            },
        }
        logger.info("Request Validator initialized")

    def validate_request(
        self, endpoint: str, data: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        if endpoint not in self.schemas:
            return True, []

        schema = self.schemas[endpoint]
        errors: List[str] = []

        for field_name, field_schema in schema.items():
            value = data.get(field_name)

            if field_schema["validation"] == ValidationType.REQUIRED and value is None:
                errors.append(f"Missing required field: {field_name}")
                continue

            if value is None:
                continue

            if not self._validate_type(value, field_schema["type"]):
                errors.append(
                    f"Invalid type for {field_name}: expected {field_schema['type'].value}"
                )
                continue

            errors.extend(self._validate_constraints(field_name, value, field_schema))

        return len(errors) == 0, errors

    def add_schema(self, endpoint: str, schema: Dict[str, Any]) -> None:
        self.schemas[endpoint] = schema

    def sanitize_string(self, value: str) -> str:
        value = value.replace("\x00", "")
        value = "".join(ch for ch in value if ord(ch) >= 32 or ch in "\n\r\t")
        return value[:10_000]

    # ── private ────────────────────────────────────────────────────────────────

    def _validate_type(self, value: Any, expected: DataType) -> bool:
        if expected == DataType.STRING:
            return isinstance(value, str)
        if expected == DataType.INTEGER:
            return isinstance(value, int) and not isinstance(value, bool)
        if expected == DataType.FLOAT:
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if expected == DataType.BOOLEAN:
            return isinstance(value, bool)
        if expected == DataType.ARRAY:
            return isinstance(value, list)
        if expected == DataType.OBJECT:
            return isinstance(value, dict)
        return True

    def _validate_constraints(
        self, field_name: str, value: Any, schema: Dict[str, Any]
    ) -> List[str]:
        errors: List[str] = []

        if "min" in schema and isinstance(value, (int, float)):
            if value < schema["min"]:
                errors.append(f"{field_name} must be >= {schema['min']}")

        if "max" in schema and isinstance(value, (int, float)):
            if value > schema["max"]:
                errors.append(f"{field_name} must be <= {schema['max']}")

        if "min_length" in schema and isinstance(value, str):
            if len(value) < schema["min_length"]:
                errors.append(
                    f"{field_name} must be at least {schema['min_length']} characters"
                )

        if "max_length" in schema and isinstance(value, str):
            if len(value) > schema["max_length"]:
                errors.append(
                    f"{field_name} must be at most {schema['max_length']} characters"
                )

        if "allowed_values" in schema and value not in schema["allowed_values"]:
            errors.append(f"{field_name} must be one of {schema['allowed_values']}")

        return errors


request_validator = RequestValidator()
