"""
pipeline.py — import pipeline: raw source records → column_mapper → quality_checker.
Wires D-02 (column_mapper) + D-03/D-04/D-05 (quality_checker) into a single callable.
Eligible records (non-rejected) are ready to pass to MassValuationRunner.

GOVERNANCE:
  - No statistical imputation at any stage (D-04).
  - Rejected records are documented, never silently dropped.
  - Anomaly flags are flag_for_review only; eligible_records includes flagged records (D-05).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .column_mapper import MappingResult, map_record
from .quality_checker import QualityResult, check_batch


@dataclass
class PipelineRecord:
    index: int
    canonical: Dict[str, Any]
    unmapped_keys: List[str]
    quality: QualityResult

    @property
    def property_id(self) -> Optional[str]:
        return self.quality.property_id

    @property
    def action(self) -> str:
        return self.quality.action

    @property
    def eligible(self) -> bool:
        """Eligible = not rejected. Flagged records ARE eligible and go to the runner."""
        return not self.quality.rejected

    def summary(self) -> Dict[str, Any]:
        return {
            "index":         self.index,
            "property_id":   self.property_id,
            "action":        self.action,
            "quality_flags": self.quality.quality_flags,
            "unmapped_keys": self.unmapped_keys,
        }


@dataclass
class PipelineResult:
    records: List[PipelineRecord] = field(default_factory=list)

    @property
    def n_input(self) -> int:
        return len(self.records)

    @property
    def n_rejected(self) -> int:
        return sum(1 for r in self.records if r.quality.rejected)

    @property
    def n_flagged(self) -> int:
        return sum(
            1 for r in self.records
            if not r.quality.rejected and r.quality.review_required
        )

    @property
    def n_eligible(self) -> int:
        return sum(1 for r in self.records if r.eligible)

    @property
    def eligible_records(self) -> List[Dict[str, Any]]:
        """Canonical records ready for MassValuationRunner (rejected excluded)."""
        return [r.canonical for r in self.records if r.eligible]

    @property
    def unmapped_field_names(self) -> List[str]:
        """Unique source column names that had no contract alias match."""
        seen: set = set()
        for r in self.records:
            seen.update(r.unmapped_keys)
        return sorted(seen)

    def pipeline_report(self) -> List[Dict[str, Any]]:
        return [r.summary() for r in self.records]


def run_pipeline(
    raw_records: List[Dict[str, Any]],
    source: str = "csv",
    lookback_months: int = 36,
) -> PipelineResult:
    """
    Map + quality-check a batch of raw source records.

    Stage 1 (D-02): column_mapper maps each record's source keys to canonical names.
    Stage 2 (D-03/D-04/D-05): quality_checker enforces QR-001 → QR-016 on canonical records.

    Returns a PipelineResult containing per-record summaries and the eligible subset
    ready for MassValuationRunner. Missing fields are documented; nothing is imputed.
    """
    # Stage 1: column mapping (D-02)
    mapping_results: List[MappingResult] = [
        map_record(raw, source=source) for raw in raw_records
    ]
    canonical_records = [mr.canonical for mr in mapping_results]

    # Stage 2: quality check (D-03/D-04/D-05)
    quality_results: List[QualityResult] = check_batch(
        canonical_records, lookback_months=lookback_months
    )

    pipeline_records = [
        PipelineRecord(
            index=idx,
            canonical=mr.canonical,
            unmapped_keys=mr.unmapped_keys,
            quality=qr,
        )
        for idx, (mr, qr) in enumerate(zip(mapping_results, quality_results))
    ]

    return PipelineResult(records=pipeline_records)
