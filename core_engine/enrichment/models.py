"""
models.py — Phase 19 Agentic Market Enrichment data models.

All enriched results start as drafts pending human review.
No model training, no scraping, no external API calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enrichment request
# ---------------------------------------------------------------------------

@dataclass
class EnrichmentRequest:
    """Describes what geographic scope and asset context to enrich."""

    country_code:       str
    region:             str
    city:               str
    district:           str
    asset_type:         str
    valuation_purpose:  str

    # Optional enrichment hints
    asset_family:       str                    = "residential"
    purpose_route:      str                    = ""
    gps_coordinates:    Optional[str]          = None
    search_radius:      float                  = 5.0          # km
    data_needed:        List[str]              = field(default_factory=list)
    requested_by:       str                    = "system"
    request_timestamp:  str                    = ""


# ---------------------------------------------------------------------------
# Source log entry (one record per data source consulted)
# ---------------------------------------------------------------------------

@dataclass
class SourceLogEntry:
    """Audit record for a single data source consulted during enrichment."""

    source_id:          str
    source_type:        str          # "local_static" | "local_feed" | "knowledge_store" | "manual" | "mock"
    source_name:        str
    source_uri:         str          # local file path, "memory", "knowledge_store", or empty
    retrieved_at:       str          # ISO 8601
    source_date:        str          # publication / reference date of the data
    country_code:       str
    region:             str
    city:               str
    district:           str
    confidence_score:   float        # 0–100, data quality at this source
    extraction_method:  str          # "price_range_lookup" | "mock" | "manual" | "qdrant_query"
    notes:              str          = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id":        self.source_id,
            "source_type":      self.source_type,
            "source_name":      self.source_name,
            "source_uri":       self.source_uri,
            "retrieved_at":     self.retrieved_at,
            "source_date":      self.source_date,
            "country_code":     self.country_code,
            "region":           self.region,
            "city":             self.city,
            "district":         self.district,
            "confidence_score": self.confidence_score,
            "extraction_method": self.extraction_method,
            "notes":            self.notes,
        }


# ---------------------------------------------------------------------------
# Comparable suggestion (one unit)
# ---------------------------------------------------------------------------

@dataclass
class ComparableSuggestion:
    """A single comparable transaction suggestion — draft only."""

    description:    str
    price_m2_lo:    float
    price_m2_hi:    float
    location:       str
    asset_type:     str
    source_id:      str
    notes:          str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "description":  self.description,
            "price_m2_lo":  self.price_m2_lo,
            "price_m2_hi":  self.price_m2_hi,
            "location":     self.location,
            "asset_type":   self.asset_type,
            "source_id":    self.source_id,
            "notes":        self.notes,
        }


# ---------------------------------------------------------------------------
# Enrichment result (output model)
# ---------------------------------------------------------------------------

@dataclass
class EnrichmentResult:
    """
    The output of one enrichment run.

    Governance invariants (enforced by MarketEnrichmentLayer):
    - is_automated_fill is always True
    - approval_status is always "pending_human_review" on creation
    - can_generate_final_report() returns False until approved
    """

    enrichment_id:      str
    is_automated_fill:  bool                        = True
    approval_status:    str                         = "pending_human_review"

    confidence_score:   float                       = 0.0
    data_source_log:    List[SourceLogEntry]        = field(default_factory=list)

    # Suggested market values (draft — not for final reports)
    suggested_values:   Dict[str, Any]              = field(default_factory=dict)
    comparable_suggestions: List[ComparableSuggestion] = field(default_factory=list)
    market_indicators:  Dict[str, Any]              = field(default_factory=dict)

    warnings:           List[str]                   = field(default_factory=list)
    created_at:         str                         = ""
    expires_at:         str                         = ""
    source_count:       int                         = 0

    # Echo of the request scope
    geographic_scope:   Dict[str, Any]              = field(default_factory=dict)
    asset_type:         str                         = ""
    valuation_purpose:  str                         = ""

    def can_generate_final_report(self) -> bool:
        """Returns False while approval_status != 'approved'."""
        if self.is_automated_fill:
            return self.approval_status == "approved"
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enrichment_id":        self.enrichment_id,
            "is_automated_fill":    self.is_automated_fill,
            "approval_status":      self.approval_status,
            "confidence_score":     self.confidence_score,
            "data_source_log":      [s.to_dict() for s in self.data_source_log],
            "suggested_values":     self.suggested_values,
            "comparable_suggestions": [c.to_dict() for c in self.comparable_suggestions],
            "market_indicators":    self.market_indicators,
            "warnings":             self.warnings,
            "created_at":           self.created_at,
            "expires_at":           self.expires_at,
            "source_count":         self.source_count,
            "geographic_scope":     self.geographic_scope,
            "asset_type":           self.asset_type,
            "valuation_purpose":    self.valuation_purpose,
            "can_generate_final_report": self.can_generate_final_report(),
        }
