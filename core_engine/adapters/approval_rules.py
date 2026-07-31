"""
Human Approval & Auto-Enrichment Rules — Phase 13 (METADATA + HELPERS ONLY).

Standalone helper functions for enforcing the central governance rule:
    Auto-enriched values NEVER enter final reports without explicit human approval
    (approval_status == "approved"). Default for auto-enriched = "pending_human_review".

These functions operate on plain data dicts — no matrix object required.

Relationship to existing modules
---------------------------------
  purpose_integration_matrix.py (Phase 8) — APPROVAL_STATUSES, REPORT_STATUSES
      are defined there and re-exported here to avoid duplication.

Usage
-----
    from adapters.approval_rules import (
        APPROVAL_STATUSES,
        REPORT_STATUSES,
        normalize_approval_status,
        requires_human_approval,
        validate_auto_enrichment_metadata,
        can_generate_final_report,
        get_report_status_from_approval,
    )
"""
from __future__ import annotations

from typing import Any

from adapters.purpose_integration_matrix import APPROVAL_STATUSES, REPORT_STATUSES

__all__ = [
    "APPROVAL_STATUSES",
    "REPORT_STATUSES",
    "normalize_approval_status",
    "requires_human_approval",
    "validate_auto_enrichment_metadata",
    "can_generate_final_report",
    "get_report_status_from_approval",
]


def normalize_approval_status(value: Any) -> str:
    """Validate and return the canonical approval status string.

    Raises
    ------
    ValueError
        If *value* is not a member of APPROVAL_STATUSES.
    """
    if value not in APPROVAL_STATUSES:
        raise ValueError(
            f"Unknown approval_status {value!r}. "
            f"Allowed: {sorted(APPROVAL_STATUSES)}"
        )
    return str(value)


def requires_human_approval(data: dict[str, Any]) -> bool:
    """Return True if the data dict requires human approval before a final report.

    Returns True when ``data["is_automated_fill"]`` is exactly ``True``.
    """
    return data.get("is_automated_fill") is True


def validate_auto_enrichment_metadata(data: dict[str, Any]) -> list[str]:
    """Validate auto-enrichment metadata in a plain data dict.

    Returns a list of error strings; an empty list means the data is valid.

    Checks performed
    ----------------
    - ``data_source_log`` must be present (non-empty) when ``is_automated_fill=True``
    - ``confidence_score`` must be present when ``is_automated_fill=True``
    - ``confidence_score`` must be in [0, 100] when supplied
    - ``approval_status`` must be a member of APPROVAL_STATUSES when supplied
    - Auto-enriched data must NOT start with ``approval_status="approved"``
      (default must be ``"pending_human_review"``)
    """
    errors: list[str] = []
    is_automated = data.get("is_automated_fill") is True

    if is_automated:
        if not data.get("data_source_log"):
            errors.append(
                "data_source_log must be present when is_automated_fill=True"
            )
        if data.get("confidence_score") is None:
            errors.append(
                "confidence_score must be present when is_automated_fill=True"
            )

    score = data.get("confidence_score")
    if score is not None:
        try:
            s = float(score)
            if not (0.0 <= s <= 100.0):
                errors.append(
                    f"confidence_score must be between 0 and 100 inclusive, got {score!r}"
                )
        except (TypeError, ValueError):
            errors.append(f"confidence_score must be numeric, got {score!r}")

    status = data.get("approval_status")
    if status is not None and status not in APPROVAL_STATUSES:
        errors.append(
            f"approval_status {status!r} is not valid. "
            f"Allowed: {sorted(APPROVAL_STATUSES)}"
        )

    if is_automated and data.get("approval_status") == "approved":
        errors.append(
            "auto-enriched data must not start with approval_status='approved'; "
            "use 'pending_human_review' as the default"
        )

    return errors


def can_generate_final_report(data: dict[str, Any]) -> bool:
    """Return True if a final report can be generated from this data.

    Returns False when the data is auto-enriched and not yet explicitly approved
    by a human reviewer.
    """
    if data.get("is_automated_fill") is True:
        return data.get("approval_status") == "approved"
    return True


def get_report_status_from_approval(data: dict[str, Any]) -> str:
    """Return the report status string derived from the approval state.

    Returns
    -------
    "ready_for_final"
        Data is non-automated, or automated and explicitly approved.
    "draft_pending_human_review"
        Data is auto-enriched and pending review (or no status supplied).
    "draft_rejected"
        Data is auto-enriched and explicitly rejected.
    """
    if data.get("is_automated_fill") is not True:
        return "ready_for_final"

    status = data.get("approval_status", "pending_human_review")
    if status == "approved":
        return "ready_for_final"
    if status == "rejected":
        return "draft_rejected"
    return "draft_pending_human_review"
