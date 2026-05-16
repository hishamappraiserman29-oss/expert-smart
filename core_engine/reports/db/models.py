"""ReportRecord dataclass — the in-memory representation of a persisted report."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReportRecord:
    """Immutable snapshot of a report row returned from the DB."""

    report_id:      str
    profile_key:    str
    status:         str              # 'draft' | 'final' | 'archived'
    appraiser_name: str | None
    market_value:   float | None
    created_at:     str              # ISO 8601
    updated_at:     str              # ISO 8601
    data:           dict[str, Any]   # full report DTO, round-trip identical
    owner_user_id:  str = "__system__"  # placed last so existing callers need no change
