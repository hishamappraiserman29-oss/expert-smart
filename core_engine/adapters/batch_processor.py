"""
batch_processor.py — Batch Processing Framework (Phase 12.0)

Bulk property valuation pipeline: queue multiple properties, track progress,
aggregate results. Additive layer — no Phase 4-11 logic is modified.

Classes:
    BatchStatus       — Processing state enum
    PropertyInBatch   — Single property in batch context
    BatchMetrics      — Batch-level statistics
    BatchProcessor    — Chainable processor with progress tracking
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


# ── Status enum ───────────────────────────────────────────────────────────────

class BatchStatus(str, Enum):
    """Batch processing status."""

    PENDING    = "pending"       # Submitted, waiting to process
    PROCESSING = "processing"    # Currently processing properties
    COMPLETED  = "completed"     # All properties processed
    FAILED     = "failed"        # Batch failed (recoverable)
    CANCELLED  = "cancelled"     # User cancelled
    ERROR      = "error"         # System error (unrecoverable)

    @staticmethod
    def is_terminal(status: str) -> bool:
        """Return True if status is terminal (no further state changes)."""
        return status in (
            BatchStatus.COMPLETED,
            BatchStatus.FAILED,
            BatchStatus.CANCELLED,
            BatchStatus.ERROR,
        )


# ── Per-property record ───────────────────────────────────────────────────────

@dataclass
class PropertyInBatch:
    """Single property in batch processing context."""

    property_id:   str
    property_name: str
    property_type: str    # residential | commercial | land
    area_sqm:      float

    input_data: Dict = field(default_factory=dict)   # Raw input JSON

    status:          str   = "pending"       # pending | processing | completed | failed | skipped
    valuation_value: float = 0.0
    primary_purpose: str   = "market_value"

    error_message: str           = ""
    processed_at:  Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "property_id":      self.property_id,
            "property_name":    self.property_name,
            "property_type":    self.property_type,
            "area_sqm":         self.area_sqm,
            "status":           self.status,
            "valuation_value":  round(self.valuation_value, 2) if self.valuation_value > 0 else None,
            "error_message":    self.error_message,
            "processed_at":     self.processed_at,
        }


# ── Batch metrics ─────────────────────────────────────────────────────────────

@dataclass
class BatchMetrics:
    """Batch-level aggregate statistics."""

    batch_id:   str
    batch_name: str

    total_properties: int = 0
    completed:        int = 0
    failed:           int = 0
    skipped:          int = 0

    total_valuation_value: float = 0.0
    average_valuation:     float = 0.0

    submitted_at:  str           = ""
    started_at:    Optional[str] = None
    completed_at:  Optional[str] = None

    status:       str   = BatchStatus.PENDING
    progress_pct: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "batch_id":              self.batch_id,
            "batch_name":            self.batch_name,
            "total_properties":      self.total_properties,
            "completed":             self.completed,
            "failed":                self.failed,
            "skipped":               self.skipped,
            "total_valuation_value": round(self.total_valuation_value, 2),
            "average_valuation":     round(self.average_valuation, 2),
            "submitted_at":          self.submitted_at,
            "started_at":            self.started_at,
            "completed_at":          self.completed_at,
            "status":                self.status,
            "progress_pct":          round(self.progress_pct, 1),
        }


# ── Batch processor ───────────────────────────────────────────────────────────

class BatchProcessor:
    """Process a batch of properties with progress tracking."""

    def __init__(self, batch_name: str = "Unnamed Batch") -> None:
        self.batch_id   = str(uuid.uuid4())
        self.batch_name = batch_name
        self.properties: List[PropertyInBatch] = []
        self.metrics = BatchMetrics(
            batch_id=self.batch_id,
            batch_name=batch_name,
            submitted_at=datetime.now().isoformat(),
        )

    # ── Building ──────────────────────────────────────────────────────────────

    def add_property(
        self,
        property_id:   str,
        property_name: str,
        property_type: str,
        area_sqm:      float,
        input_data:    Dict,
    ) -> "BatchProcessor":
        """Add property to batch; returns self for chaining."""
        self.properties.append(PropertyInBatch(
            property_id=property_id,
            property_name=property_name,
            property_type=property_type,
            area_sqm=area_sqm,
            input_data=input_data,
            status="pending",
        ))
        self.metrics.total_properties = len(self.properties)
        return self

    # ── Validation ────────────────────────────────────────────────────────────

    def validate_batch(self) -> Dict:
        """Validate all properties; marks invalid ones as skipped."""
        issues: Dict = {
            "total_properties": len(self.properties),
            "valid":   0,
            "invalid": 0,
            "issues":  [],
        }

        for prop in self.properties:
            valid = True

            if not prop.property_id:
                issues["issues"].append(f"{prop.property_name}: Missing property_id")
                valid = False

            if not prop.property_type:
                issues["issues"].append(f"{prop.property_name}: Missing property_type")
                valid = False

            if prop.area_sqm <= 0:
                issues["issues"].append(
                    f"{prop.property_name}: Invalid area_sqm ({prop.area_sqm})"
                )
                valid = False

            if valid:
                issues["valid"] += 1
                prop.status = "pending"
            else:
                issues["invalid"] += 1
                prop.status = "skipped"

        self.metrics.skipped = issues["invalid"]
        return issues

    # ── Processing ────────────────────────────────────────────────────────────

    def process_property(
        self,
        property_idx:    int,
        valuation_value: float,
        primary_purpose: str = "market_value",
    ) -> None:
        """Record a successful valuation result for one property."""
        if property_idx < 0 or property_idx >= len(self.properties):
            return

        prop = self.properties[property_idx]
        if prop.status == "skipped":
            return

        prop.status          = "completed"
        prop.valuation_value = valuation_value
        prop.primary_purpose = primary_purpose
        prop.processed_at    = datetime.now().isoformat()

        self.metrics.completed             += 1
        self.metrics.total_valuation_value += valuation_value

        self._update_progress()

    def fail_property(self, property_idx: int, error_message: str) -> None:
        """Mark one property as failed with an error message."""
        if property_idx < 0 or property_idx >= len(self.properties):
            return

        prop              = self.properties[property_idx]
        prop.status        = "failed"
        prop.error_message = error_message

        self.metrics.failed += 1
        self._update_progress()

    def _update_progress(self) -> None:
        """Recompute progress_pct and average_valuation."""
        processed = self.metrics.completed + self.metrics.failed
        total     = self.metrics.total_properties - self.metrics.skipped

        if total > 0:
            self.metrics.progress_pct = (processed / total) * 100

        if self.metrics.completed > 0:
            self.metrics.average_valuation = (
                self.metrics.total_valuation_value / self.metrics.completed
            )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start_processing(self) -> None:
        """Transition batch to PROCESSING state."""
        self.metrics.status     = BatchStatus.PROCESSING
        self.metrics.started_at = datetime.now().isoformat()

    def complete_batch(self) -> None:
        """Transition batch to COMPLETED state."""
        self.metrics.status       = BatchStatus.COMPLETED
        self.metrics.completed_at = datetime.now().isoformat()
        self.metrics.progress_pct = 100.0

    def fail_batch(self, error_message: str = "") -> None:
        """Transition batch to FAILED state."""
        self.metrics.status       = BatchStatus.FAILED
        self.metrics.completed_at = datetime.now().isoformat()

    # ── Reporting ─────────────────────────────────────────────────────────────

    def get_batch_summary(self) -> Dict:
        """Return complete batch summary (JSON-serialisable)."""
        return {
            "batch_id":   self.batch_id,
            "batch_name": self.batch_name,
            "metrics":    self.metrics.to_dict(),
            "properties": [p.to_dict() for p in self.properties],
        }

    def get_completion_report(self) -> Dict:
        """Return structured completion report grouped by outcome."""
        completed = [p for p in self.properties if p.status == "completed"]
        failed    = [p for p in self.properties if p.status == "failed"]
        skipped   = [p for p in self.properties if p.status == "skipped"]

        return {
            "batch_id": self.batch_id,
            "status":   self.metrics.status,
            "summary": {
                "total_submitted":       self.metrics.total_properties,
                "completed":             len(completed),
                "failed":                len(failed),
                "skipped":               len(skipped),
                "total_valuation_value": round(self.metrics.total_valuation_value, 2),
                "average_valuation":     round(self.metrics.average_valuation, 2),
            },
            "completed_properties": [p.to_dict() for p in completed],
            "failed_properties": [
                {"id": p.property_id, "name": p.property_name, "error": p.error_message}
                for p in failed
            ],
            "skipped_properties": [
                {"id": p.property_id, "name": p.property_name}
                for p in skipped
            ],
            "completed_at": self.metrics.completed_at,
        }
