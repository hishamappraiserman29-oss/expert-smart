"""
Tests for Human Approval & Auto-Enrichment Rules — Phase 13.

AR01  — module is importable without bridge_api or valuation engine
AR02  — APPROVAL_STATUSES contains exactly the four expected values
AR03  — REPORT_STATUSES contains exactly the three expected values
AR04  — normalize_approval_status: each valid status round-trips correctly
AR05  — normalize_approval_status: unknown value raises ValueError
AR06  — requires_human_approval: True when is_automated_fill=True
AR07  — requires_human_approval: False when is_automated_fill=False
AR08  — requires_human_approval: False when is_automated_fill key is absent
AR09  — validate_auto_enrichment_metadata: no errors for valid non-automated data
AR10  — validate_auto_enrichment_metadata: error when data_source_log missing and automated
AR11  — validate_auto_enrichment_metadata: error when confidence_score missing and automated
AR12  — validate_auto_enrichment_metadata: error when confidence_score > 100
AR13  — validate_auto_enrichment_metadata: error when confidence_score < 0
AR14  — validate_auto_enrichment_metadata: error when automated data has approval_status='approved'
AR15  — validate_auto_enrichment_metadata: error when approval_status is invalid string
AR16  — validate_auto_enrichment_metadata: no errors for fully valid automated data
AR17  — can_generate_final_report: False when automated + pending_human_review
AR18  — can_generate_final_report: False when automated + rejected
AR19  — can_generate_final_report: True when automated + approved
AR20  — can_generate_final_report: True when not automated (no approval_status required)
AR21  — get_report_status_from_approval: ready_for_final for non-automated data
AR22  — get_report_status_from_approval: draft_pending_human_review for automated+pending
AR23  — get_report_status_from_approval: draft_pending_human_review for automated+no status
AR24  — get_report_status_from_approval: draft_rejected for automated+rejected
AR25  — get_report_status_from_approval: ready_for_final for automated+approved
AR26  — APPROVAL_STATUSES and REPORT_STATUSES are frozensets (immutable)
AR27  — validate_auto_enrichment_metadata: confidence_score=0 is valid boundary
AR28  — validate_auto_enrichment_metadata: confidence_score=100 is valid boundary
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# ── Path setup ────────────────────────────────────────────────────────────────
_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(str(_CORE))

from adapters.approval_rules import (  # noqa: E402
    APPROVAL_STATUSES,
    REPORT_STATUSES,
    can_generate_final_report,
    get_report_status_from_approval,
    normalize_approval_status,
    requires_human_approval,
    validate_auto_enrichment_metadata,
)


# ── AR01 ─────────────────────────────────────────────────────────────────────

def test_AR01_module_importable() -> None:
    """Module imports cleanly without bridge_api or engine."""
    import adapters.approval_rules as mod
    assert hasattr(mod, "APPROVAL_STATUSES")
    assert hasattr(mod, "REPORT_STATUSES")
    assert hasattr(mod, "normalize_approval_status")
    assert hasattr(mod, "requires_human_approval")
    assert hasattr(mod, "validate_auto_enrichment_metadata")
    assert hasattr(mod, "can_generate_final_report")
    assert hasattr(mod, "get_report_status_from_approval")


# ── AR02 / AR03 ───────────────────────────────────────────────────────────────

def test_AR02_approval_statuses_values() -> None:
    assert APPROVAL_STATUSES == frozenset({
        "not_required",
        "pending_human_review",
        "approved",
        "rejected",
    })


def test_AR03_report_statuses_values() -> None:
    assert REPORT_STATUSES == frozenset({
        "draft_pending_human_review",
        "ready_for_final",
        "final_approved",
    })


# ── AR04 / AR05 ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("status", [
    "not_required",
    "pending_human_review",
    "approved",
    "rejected",
])
def test_AR04_normalize_valid_statuses(status: str) -> None:
    assert normalize_approval_status(status) == status


def test_AR05_normalize_invalid_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unknown approval_status"):
        normalize_approval_status("auto_approved")


# ── AR06 / AR07 / AR08 ────────────────────────────────────────────────────────

def test_AR06_requires_human_approval_true_when_automated() -> None:
    assert requires_human_approval({"is_automated_fill": True}) is True


def test_AR07_requires_human_approval_false_when_not_automated() -> None:
    assert requires_human_approval({"is_automated_fill": False}) is False


def test_AR08_requires_human_approval_false_when_key_absent() -> None:
    assert requires_human_approval({}) is False
    assert requires_human_approval({"confidence_score": 80.0}) is False


# ── AR09–AR16 ────────────────────────────────────────────────────────────────

def test_AR09_validate_no_errors_for_valid_non_automated() -> None:
    data = {
        "is_automated_fill": False,
        "approval_status": "not_required",
    }
    assert validate_auto_enrichment_metadata(data) == []


def test_AR10_validate_error_missing_data_source_log_when_automated() -> None:
    data = {
        "is_automated_fill": True,
        "confidence_score": 75.0,
        "approval_status": "pending_human_review",
        # data_source_log intentionally absent
    }
    errors = validate_auto_enrichment_metadata(data)
    assert any("data_source_log" in e for e in errors)


def test_AR11_validate_error_missing_confidence_score_when_automated() -> None:
    data = {
        "is_automated_fill": True,
        "data_source_log": ["source_a"],
        "approval_status": "pending_human_review",
        # confidence_score intentionally absent
    }
    errors = validate_auto_enrichment_metadata(data)
    assert any("confidence_score" in e for e in errors)


def test_AR12_validate_error_confidence_score_above_100() -> None:
    data = {
        "is_automated_fill": False,
        "confidence_score": 101.0,
    }
    errors = validate_auto_enrichment_metadata(data)
    assert any("0 and 100" in e for e in errors)


def test_AR13_validate_error_confidence_score_below_0() -> None:
    data = {
        "is_automated_fill": False,
        "confidence_score": -1.0,
    }
    errors = validate_auto_enrichment_metadata(data)
    assert any("0 and 100" in e for e in errors)


def test_AR14_validate_error_automated_starts_as_approved() -> None:
    data = {
        "is_automated_fill": True,
        "data_source_log": ["api_x"],
        "confidence_score": 90.0,
        "approval_status": "approved",
    }
    errors = validate_auto_enrichment_metadata(data)
    assert any("pending_human_review" in e for e in errors)


def test_AR15_validate_error_invalid_approval_status() -> None:
    data = {
        "is_automated_fill": False,
        "approval_status": "unknown_status",
    }
    errors = validate_auto_enrichment_metadata(data)
    assert any("not valid" in e for e in errors)


def test_AR16_validate_no_errors_for_valid_automated_data() -> None:
    data = {
        "is_automated_fill": True,
        "data_source_log": ["source_a", "source_b"],
        "confidence_score": 85.0,
        "approval_status": "pending_human_review",
    }
    assert validate_auto_enrichment_metadata(data) == []


# ── AR17–AR20 ────────────────────────────────────────────────────────────────

def test_AR17_cannot_generate_final_report_when_automated_pending() -> None:
    data = {"is_automated_fill": True, "approval_status": "pending_human_review"}
    assert can_generate_final_report(data) is False


def test_AR18_cannot_generate_final_report_when_automated_rejected() -> None:
    data = {"is_automated_fill": True, "approval_status": "rejected"}
    assert can_generate_final_report(data) is False


def test_AR19_can_generate_final_report_when_automated_approved() -> None:
    data = {"is_automated_fill": True, "approval_status": "approved"}
    assert can_generate_final_report(data) is True


def test_AR20_can_generate_final_report_when_not_automated() -> None:
    assert can_generate_final_report({"is_automated_fill": False}) is True
    assert can_generate_final_report({}) is True


# ── AR21–AR25 ────────────────────────────────────────────────────────────────

def test_AR21_report_status_ready_for_non_automated() -> None:
    assert get_report_status_from_approval({"is_automated_fill": False}) == "ready_for_final"
    assert get_report_status_from_approval({}) == "ready_for_final"


def test_AR22_report_status_draft_pending_for_automated_pending() -> None:
    data = {"is_automated_fill": True, "approval_status": "pending_human_review"}
    assert get_report_status_from_approval(data) == "draft_pending_human_review"


def test_AR23_report_status_draft_pending_for_automated_no_status() -> None:
    data = {"is_automated_fill": True}
    assert get_report_status_from_approval(data) == "draft_pending_human_review"


def test_AR24_report_status_draft_rejected_for_automated_rejected() -> None:
    data = {"is_automated_fill": True, "approval_status": "rejected"}
    assert get_report_status_from_approval(data) == "draft_rejected"


def test_AR25_report_status_ready_for_automated_approved() -> None:
    data = {"is_automated_fill": True, "approval_status": "approved"}
    assert get_report_status_from_approval(data) == "ready_for_final"


# ── AR26–AR28 ────────────────────────────────────────────────────────────────

def test_AR26_constants_are_frozensets() -> None:
    assert isinstance(APPROVAL_STATUSES, frozenset)
    assert isinstance(REPORT_STATUSES, frozenset)


def test_AR27_confidence_score_zero_is_valid_boundary() -> None:
    data = {
        "is_automated_fill": True,
        "data_source_log": ["source"],
        "confidence_score": 0.0,
        "approval_status": "pending_human_review",
    }
    assert validate_auto_enrichment_metadata(data) == []


def test_AR28_confidence_score_100_is_valid_boundary() -> None:
    data = {
        "is_automated_fill": True,
        "data_source_log": ["source"],
        "confidence_score": 100.0,
        "approval_status": "pending_human_review",
    }
    assert validate_auto_enrichment_metadata(data) == []
