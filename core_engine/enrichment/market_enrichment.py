"""
market_enrichment.py — Phase 19 Agentic Market Enrichment Layer.

Main orchestrator for building market enrichment suggestions from geographic scope.

Governance rules (enforced here):
  - All outputs: is_automated_fill=True, approval_status="pending_human_review"
  - can_generate_final_report() = False until expert sets approval_status="approved"
  - No scraping, no internet, no model training
  - Source log mandatory when is_automated_fill=True

Usage (operator/API — NOT integrated into /api/valuation):
    from enrichment.market_enrichment import MarketEnrichmentLayer, build_request

    layer = MarketEnrichmentLayer()
    request = build_request(
        country_code="EG", region="Cairo", city="Cairo",
        district="التجمع الخامس", asset_type="residential",
        valuation_purpose="market_value",
    )
    result = layer.enrich(request)
    # result.approval_status == "pending_human_review"
    # result.can_generate_final_report() == False
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .confidence import calculate_confidence
from .models import (
    ComparableSuggestion,
    EnrichmentRequest,
    EnrichmentResult,
    SourceLogEntry,
)
from .providers import (
    BaseMarketProvider,
    ExistingLocalMarketFeedProvider,
    KnowledgeStoreProvider,
    ManualMarketProvider,
    MockMarketProvider,
)


# ---------------------------------------------------------------------------
# Convenience constructor for EnrichmentRequest
# ---------------------------------------------------------------------------

def build_request(
    country_code:      str,
    region:            str,
    city:              str,
    district:          str,
    asset_type:        str,
    valuation_purpose: str,
    asset_family:      str                  = "residential",
    purpose_route:     str                  = "",
    gps_coordinates:   Optional[str]        = None,
    search_radius:     float                = 5.0,
    data_needed:       Optional[List[str]]  = None,
    requested_by:      str                  = "system",
) -> EnrichmentRequest:
    """Construct an EnrichmentRequest with an ISO timestamp."""
    return EnrichmentRequest(
        country_code=       country_code,
        region=             region,
        city=               city,
        district=           district,
        asset_type=         asset_type,
        valuation_purpose=  valuation_purpose,
        asset_family=       asset_family,
        purpose_route=      purpose_route,
        gps_coordinates=    gps_coordinates,
        search_radius=      search_radius,
        data_needed=        data_needed or [],
        requested_by=       requested_by,
        request_timestamp=  datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# Stable enrichment ID
# ---------------------------------------------------------------------------

def _enrichment_id(request: EnrichmentRequest, created_at: str) -> str:
    raw = f"{request.district}:{request.asset_type}:{request.valuation_purpose}:{created_at}"
    return "enr_" + hashlib.md5(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# MarketEnrichmentLayer
# ---------------------------------------------------------------------------

class MarketEnrichmentLayer:
    """
    Agentic market enrichment orchestrator.

    Collects suggestions from configured providers, calculates a confidence
    score, and wraps results in an EnrichmentResult that is:
      - always is_automated_fill = True
      - always approval_status = "pending_human_review"
      - can_generate_final_report() = False until approved
    """

    def __init__(
        self,
        providers:   Optional[List[BaseMarketProvider]] = None,
        use_mock:    bool = False,
    ) -> None:
        """
        Parameters
        ----------
        providers : explicit provider list (overrides default stack)
        use_mock  : if True, only MockMarketProvider is used (for tests)
        """
        if providers is not None:
            self._providers: List[BaseMarketProvider] = providers
        elif use_mock:
            self._providers = [MockMarketProvider()]
        else:
            self._providers = [
                ExistingLocalMarketFeedProvider(),
                KnowledgeStoreProvider(),
            ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enrich(self, request: EnrichmentRequest) -> EnrichmentResult:
        """
        Run all providers against the request and return an EnrichmentResult.

        The result is ALWAYS a draft (pending_human_review).
        It NEVER enters a final report without explicit approval.
        """
        created_at = datetime.now(timezone.utc).isoformat()
        expires_at = ""   # expiry policy is domain-specific; left to caller

        # Collect from all providers
        all_source_logs:  List[SourceLogEntry]     = []
        all_comparables:  List[ComparableSuggestion] = []
        merged_suggested: Dict[str, Any]           = {}
        merged_indicators: Dict[str, Any]          = {}
        all_warnings:     List[str]                = []

        for provider in self._providers:
            try:
                result = provider.fetch(request)
            except Exception as exc:
                all_warnings.append(f"Provider {provider.name} raised: {exc}")
                continue

            # Merge source logs
            all_source_logs.extend(result.get("source_log", []))

            # Merge comparables
            all_comparables.extend(result.get("comparable_suggestions", []))

            # Merge suggested values (first non-None value wins per key)
            for k, v in result.get("suggested_values", {}).items():
                if k not in merged_suggested or merged_suggested[k] is None:
                    merged_suggested[k] = v

            # Merge market indicators
            merged_indicators.update(result.get("market_indicators", {}))

            # Collect warnings
            all_warnings.extend(result.get("warnings", []))

        # Warn if no sources produced anything
        if not all_source_logs:
            all_warnings.append(
                "No market data sources returned results — enrichment has zero confidence"
            )

        # Calculate confidence
        confidence = calculate_confidence(
            sources=    all_source_logs,
            asset_type= request.asset_type,
            district=   request.district,
        )

        eid = _enrichment_id(request, created_at)

        # GOVERNANCE: result always starts pending_human_review
        return EnrichmentResult(
            enrichment_id=       eid,
            is_automated_fill=   True,
            approval_status=     "pending_human_review",
            confidence_score=    confidence,
            data_source_log=     all_source_logs,
            suggested_values=    merged_suggested,
            comparable_suggestions= all_comparables,
            market_indicators=   merged_indicators,
            warnings=            all_warnings,
            created_at=          created_at,
            expires_at=          expires_at,
            source_count=        len(all_source_logs),
            geographic_scope={
                "country_code":   request.country_code,
                "region":         request.region,
                "city":           request.city,
                "district":       request.district,
                "gps_coordinates": request.gps_coordinates,
                "search_radius":  request.search_radius,
            },
            asset_type=          request.asset_type,
            valuation_purpose=   request.valuation_purpose,
        )

    def enrich_from_scope(
        self,
        country_code:      str,
        region:            str,
        city:              str,
        district:          str,
        asset_type:        str,
        valuation_purpose: str,
        **kwargs: Any,
    ) -> EnrichmentResult:
        """Convenience wrapper — build request inline and call enrich()."""
        req = build_request(
            country_code=      country_code,
            region=            region,
            city=              city,
            district=          district,
            asset_type=        asset_type,
            valuation_purpose= valuation_purpose,
            **kwargs,
        )
        return self.enrich(req)


# ---------------------------------------------------------------------------
# Approval helpers (re-export from Phase 13 adapter)
# ---------------------------------------------------------------------------

def approve_enrichment(result: EnrichmentResult, approved_by: str = "expert") -> EnrichmentResult:
    """
    Mark an enrichment result as approved by a human expert.
    After approval, can_generate_final_report() returns True.
    """
    result.approval_status = "approved"
    result.market_indicators["approved_by"] = approved_by
    result.market_indicators["approved_at"] = datetime.now(timezone.utc).isoformat()
    return result


def reject_enrichment(result: EnrichmentResult, reason: str = "") -> EnrichmentResult:
    """Mark an enrichment result as rejected."""
    result.approval_status = "rejected"
    result.market_indicators["rejection_reason"] = reason
    result.market_indicators["rejected_at"] = datetime.now(timezone.utc).isoformat()
    return result
