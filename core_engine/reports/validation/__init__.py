"""core_engine/reports/validation — Report Validation Engine (Wave 7b).

Public API::

    from core_engine.reports.validation import validate_report
    from core_engine.reports.validation import (
        validate_inputs, validate_outputs,
        ValidationResult, ValidationIssue, Severity,
    )
"""

from .input_validator import validate_inputs
from .output_validator import validate_outputs
from .result import Severity, ValidationIssue, ValidationResult
from .validation_engine import validate_report

__all__ = [
    "validate_report",
    "validate_inputs",
    "validate_outputs",
    "ValidationResult",
    "ValidationIssue",
    "Severity",
]
