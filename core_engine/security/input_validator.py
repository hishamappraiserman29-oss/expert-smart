"""
input_validator.py — PH.3 Input Validation & Sanitisation

Validates all inbound data before it reaches business logic.
All methods are stateless class methods — no instantiation required for
simple use, but an instance may be created and reused.

Classes:
    SanitisationResult  — outcome of a single validation check
    InputValidator    — collection of validators for common field types
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE,
)

_SAFE_PATH_RE = re.compile(r'^[a-zA-Z0-9_\-. /\\:]+$')

_TRAVERSAL_PARTS = frozenset({'..', '..'})

_VALID_PROPERTY_TYPES = frozenset({
    'residential', 'commercial', 'industrial', 'land',
    'mixed_use', 'hotel', 'retail', 'office', 'warehouse',
    'villa', 'apartment', 'compound',
})

_VALID_EXECUTION_MODES = frozenset({
    'autonomous', 'supervised', 'manual', 'readonly',
})

_VALID_PURPOSES = frozenset({
    'market_value', 'investment_value', 'forced_sale',
    'insurance_value', 'rental_value', 'tax_assessment',
    'dcf_analysis', 'portfolio_analysis',
})

_MAX_AREA_SQM = 10_000_000   # 10 million m² — large enough for any real asset
_MIN_AREA_SQM = 0.1

_MAX_STRING_LEN = 2048

# Control characters (except \t \n \r)
_CONTROL_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


# ---------------------------------------------------------------------------
# SanitisationResult
# ---------------------------------------------------------------------------

@dataclass
class SanitisationResult:
    """Outcome of a single validation check."""

    field_name: str
    is_valid: bool
    value: Any = None               # cleaned / normalised value on success
    error: Optional[str] = None     # human-readable message on failure
    warnings: List[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.is_valid

    def to_dict(self) -> Dict[str, Any]:
        return {
            'field': self.field_name,
            'valid': self.is_valid,
            'value': self.value,
            'error': self.error,
            'warnings': self.warnings,
        }


# ---------------------------------------------------------------------------
# InputValidator
# ---------------------------------------------------------------------------

class InputValidator:
    """Stateless validators for common Expert Smart field types."""

    # -- UUID -----------------------------------------------------------------

    @staticmethod
    def validate_uuid(value: Any, field_name: str = 'id') -> SanitisationResult:
        """Validate that *value* is a well-formed UUID string."""
        if not isinstance(value, str):
            return SanitisationResult(field_name, False, error='Must be a string')
        stripped = value.strip()
        if not stripped:
            return SanitisationResult(field_name, False, error='Must not be empty')
        if not _UUID_RE.match(stripped):
            return SanitisationResult(
                field_name, False,
                error='Invalid UUID format (expected xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)',
            )
        return SanitisationResult(field_name, True, value=stripped.lower())

    # -- File path ------------------------------------------------------------

    @staticmethod
    def validate_file_path(
        value: Any,
        field_name: str = 'path',
        must_exist: bool = False,
        allowed_extensions: Optional[List[str]] = None,
    ) -> SanitisationResult:
        """
        Validate a file path string.

        Rejects:
          - non-string inputs
          - path traversal sequences (..)
          - null bytes
        Optionally checks existence and extension whitelist.
        """
        if not isinstance(value, str):
            return SanitisationResult(field_name, False, error='Must be a string')
        stripped = value.strip()
        if not stripped:
            return SanitisationResult(field_name, False, error='Must not be empty')
        if '\x00' in stripped:
            return SanitisationResult(field_name, False, error='Null byte in path')

        try:
            p = Path(stripped)
        except Exception:
            return SanitisationResult(field_name, False, error='Invalid path syntax')

        # Reject traversal
        for part in p.parts:
            if part in _TRAVERSAL_PARTS:
                return SanitisationResult(field_name, False, error='Path traversal detected (..)')

        if allowed_extensions:
            exts = [e.lower().lstrip('.') for e in allowed_extensions]
            if p.suffix.lower().lstrip('.') not in exts:
                return SanitisationResult(
                    field_name, False,
                    error=f'Extension not allowed; permitted: {allowed_extensions}',
                )

        if must_exist and not p.exists():
            return SanitisationResult(field_name, False, error=f'Path does not exist: {stripped}')

        return SanitisationResult(field_name, True, value=str(p))

    # -- Property type --------------------------------------------------------

    @staticmethod
    def validate_property_type(value: Any, field_name: str = 'property_type') -> SanitisationResult:
        if not isinstance(value, str):
            return SanitisationResult(field_name, False, error='Must be a string')
        normalised = value.strip().lower()
        if normalised not in _VALID_PROPERTY_TYPES:
            return SanitisationResult(
                field_name, False,
                error=f'Unknown property type; valid: {sorted(_VALID_PROPERTY_TYPES)}',
            )
        return SanitisationResult(field_name, True, value=normalised)

    # -- Area -----------------------------------------------------------------

    @staticmethod
    def validate_area(value: Any, field_name: str = 'area_sqm') -> SanitisationResult:
        try:
            num = float(value)
        except (TypeError, ValueError):
            return SanitisationResult(field_name, False, error='Must be a numeric value')
        if num < _MIN_AREA_SQM:
            return SanitisationResult(field_name, False, error=f'Area must be >= {_MIN_AREA_SQM} m²')
        if num > _MAX_AREA_SQM:
            return SanitisationResult(field_name, False, error=f'Area must be <= {_MAX_AREA_SQM:,} m²')
        return SanitisationResult(field_name, True, value=round(num, 4))

    # -- Location string ------------------------------------------------------

    @staticmethod
    def validate_location(value: Any, field_name: str = 'location') -> SanitisationResult:
        if not isinstance(value, str):
            return SanitisationResult(field_name, False, error='Must be a string')
        stripped = value.strip()
        if not stripped:
            return SanitisationResult(field_name, False, error='Must not be empty')
        if len(stripped) > _MAX_STRING_LEN:
            return SanitisationResult(
                field_name, False,
                error=f'Exceeds maximum length of {_MAX_STRING_LEN}',
            )
        if _CONTROL_RE.search(stripped):
            return SanitisationResult(field_name, False, error='Contains invalid control characters')
        return SanitisationResult(field_name, True, value=stripped)

    # -- Execution mode -------------------------------------------------------

    @staticmethod
    def validate_execution_mode(value: Any, field_name: str = 'execution_mode') -> SanitisationResult:
        if not isinstance(value, str):
            return SanitisationResult(field_name, False, error='Must be a string')
        normalised = value.strip().lower()
        if normalised not in _VALID_EXECUTION_MODES:
            return SanitisationResult(
                field_name, False,
                error=f'Invalid mode; valid: {sorted(_VALID_EXECUTION_MODES)}',
            )
        return SanitisationResult(field_name, True, value=normalised)

    # -- Purpose --------------------------------------------------------------

    @staticmethod
    def validate_purpose(value: Any, field_name: str = 'purpose') -> SanitisationResult:
        if not isinstance(value, str):
            return SanitisationResult(field_name, False, error='Must be a string')
        normalised = value.strip().lower()
        if normalised not in _VALID_PURPOSES:
            return SanitisationResult(
                field_name, False,
                error=f'Invalid purpose; valid: {sorted(_VALID_PURPOSES)}',
            )
        return SanitisationResult(field_name, True, value=normalised)

    # -- Batch validation -----------------------------------------------------

    @staticmethod
    def validate_batch(checks: List[SanitisationResult]) -> Dict[str, Any]:
        """
        Aggregate multiple SanitisationResult objects into a single summary dict.

        Returns:
            {
                "valid": bool,
                "errors": {field: error, ...},
                "warnings": {field: [warning, ...], ...},
            }
        """
        errors: Dict[str, str] = {}
        warnings: Dict[str, List[str]] = {}
        for r in checks:
            if not r.is_valid and r.error:
                errors[r.field_name] = r.error
            if r.warnings:
                warnings[r.field_name] = r.warnings
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
        }

    # -- String sanitisation --------------------------------------------------

    @staticmethod
    def sanitize_string(
        value: str,
        max_length: int = _MAX_STRING_LEN,
        strip_control: bool = True,
        normalize_unicode: bool = True,
    ) -> str:
        """
        Return a cleaned version of *value*:
          - truncated to max_length
          - control characters stripped (if strip_control)
          - Unicode normalised to NFC (if normalize_unicode)
        """
        if normalize_unicode:
            value = unicodedata.normalize('NFC', value)
        if strip_control:
            value = _CONTROL_RE.sub('', value)
        return value[:max_length]
