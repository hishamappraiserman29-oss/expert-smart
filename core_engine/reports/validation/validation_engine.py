"""
validation_engine.py — EXPERT_SMART Report Validation Orchestrator.

Single public entry point:

    validate_report(data, *, profile_key="legacy") -> ValidationResult

Combines input + output validation and returns a merged ValidationResult.
Callers inspect result.is_valid before generating reports; result.errors
contain everything that would block generation, result.warnings contain
advisory issues that allow generation to proceed.

Raises nothing — always returns a ValidationResult.

Integration note (Phase 7c):
    bridge_api.py will call validate_report() before every generate_pdf() /
    generate_excel() call.  On not result.is_valid → return HTTP 422 with
    the error list.  On warnings-only → generate and attach warnings to the
    response envelope.
"""

from __future__ import annotations

from typing import Any, Mapping

from .input_validator import validate_inputs
from .output_validator import validate_outputs
from .result import ValidationResult


def validate_report(
    data: Mapping[str, Any],
    *,
    profile_key: str = "legacy",
) -> ValidationResult:
    """
    Validate a complete report data dict (inputs + outputs).

    Args:
        data: Top-level report data dict — same shape passed to generate_pdf().
        profile_key: 'legacy' / 'detailed' / 'professional_template'.

    Returns:
        ValidationResult merging all input and output findings.
        is_valid == True iff there are no ERROR-level issues.
        Never raises.
    """
    input_result  = validate_inputs(data,  profile_key=profile_key)
    output_result = validate_outputs(data, profile_key=profile_key)
    return input_result.merge(output_result)
