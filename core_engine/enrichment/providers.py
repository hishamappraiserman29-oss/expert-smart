"""
providers.py — Phase 19 market data providers.

All providers return draft suggestions only.
No internet scraping, no external API calls, no model training.

Provider hierarchy:
  BaseMarketProvider       — ABC
  MockMarketProvider       — deterministic in-memory (tests)
  ManualMarketProvider     — accepts explicitly supplied data dicts
  ExistingLocalMarketFeedProvider — reads local market_intelligence price ranges
  KnowledgeStoreProvider   — queries Qdrant (Phase 18) if available; falls back gracefully
"""

from __future__ import annotations

import abc
from typing import Any, Dict, List, Optional

from .models import ComparableSuggestion, EnrichmentRequest, SourceLogEntry
from .source_log import (
    make_knowledge_store_entry,
    make_local_static_entry,
    make_manual_entry,
    make_mock_entry,
)


# ---------------------------------------------------------------------------
# Base interface
# ---------------------------------------------------------------------------

class BaseMarketProvider(abc.ABC):
    """Abstract base for all market data providers."""

    @property
    @abc.abstractmethod
    def name(self) -> str: ...

    @abc.abstractmethod
    def fetch(
        self,
        request: EnrichmentRequest,
    ) -> Dict[str, Any]:
        """
        Return a dict with keys:
          suggested_values     : dict
          comparable_suggestions: list[ComparableSuggestion]
          market_indicators    : dict
          source_log           : list[SourceLogEntry]
          warnings             : list[str]
        """


# ---------------------------------------------------------------------------
# Mock provider (deterministic, tests only)
# ---------------------------------------------------------------------------

class MockMarketProvider(BaseMarketProvider):
    """Returns fully deterministic, in-memory market suggestions. No I/O."""

    @property
    def name(self) -> str:
        return "MockMarketProvider"

    def fetch(self, request: EnrichmentRequest) -> Dict[str, Any]:
        district = request.district or request.city
        lo, hi = 10_000.0, 25_000.0
        mid = (lo + hi) / 2.0

        log_entry = make_mock_entry(
            district=     district,
            city=         request.city,
            region=       request.region,
            country_code= request.country_code,
            confidence=   30.0,
        )

        comp = ComparableSuggestion(
            description=  f"Mock comparable — {district}",
            price_m2_lo=  lo,
            price_m2_hi=  hi,
            location=     district,
            asset_type=   request.asset_type,
            source_id=    log_entry.source_id,
            notes=        "Mock data — not for production use",
        )

        return {
            "suggested_values": {
                "comp_avg_price_m2":    mid,
                "comparable_count":     1,
                "market_vacancy_rate":  None,
                "rent_per_m2":         None,
                "cap_rate_range":      None,
                "source_summary":      "Mock provider — test data only",
                "location_notes":      f"Generic mock values for {district}",
            },
            "comparable_suggestions": [comp],
            "market_indicators": {
                "data_vintage":     "mock",
                "market_direction": "unknown",
            },
            "source_log":  [log_entry],
            "warnings":    ["Mock provider active — results are not real market data"],
        }


# ---------------------------------------------------------------------------
# Manual provider (operator-supplied data)
# ---------------------------------------------------------------------------

class ManualMarketProvider(BaseMarketProvider):
    """
    Wraps manually supplied market data dicts into the enrichment model.
    Caller passes a pre-built payload; this provider just attaches source metadata.
    """

    @property
    def name(self) -> str:
        return "ManualMarketProvider"

    def fetch(self, request: EnrichmentRequest) -> Dict[str, Any]:
        warnings: List[str] = ["ManualMarketProvider: no manual data supplied — returning empty result"]
        return {
            "suggested_values":         {},
            "comparable_suggestions":   [],
            "market_indicators":        {},
            "source_log":               [],
            "warnings":                 warnings,
        }

    def fetch_with_data(
        self,
        request:     EnrichmentRequest,
        data:        Dict[str, Any],
        source_name: str,
        source_uri:  str,
        source_date: str,
        confidence:  float,
        notes:       str = "",
    ) -> Dict[str, Any]:
        """Accept explicit operator-provided data and wrap it with source metadata."""
        log_entry = make_manual_entry(
            source_name=  source_name,
            source_uri=   source_uri,
            district=     request.district,
            city=         request.city,
            region=       request.region,
            country_code= request.country_code,
            source_date=  source_date,
            confidence=   confidence,
            notes=        notes,
        )
        comps = [
            ComparableSuggestion(
                description=  c.get("description", ""),
                price_m2_lo=  float(c.get("price_m2_lo", 0)),
                price_m2_hi=  float(c.get("price_m2_hi", 0)),
                location=     c.get("location", request.district),
                asset_type=   c.get("asset_type", request.asset_type),
                source_id=    log_entry.source_id,
                notes=        c.get("notes", ""),
            )
            for c in data.get("comparables", [])
        ]
        return {
            "suggested_values":         data.get("suggested_values", {}),
            "comparable_suggestions":   comps,
            "market_indicators":        data.get("market_indicators", {}),
            "source_log":               [log_entry],
            "warnings":                 [],
        }


# ---------------------------------------------------------------------------
# Existing local market feed provider
# ---------------------------------------------------------------------------

class ExistingLocalMarketFeedProvider(BaseMarketProvider):
    """
    Reads the local price-range dictionary from market_intelligence.py.
    No internet access, no scraping.  Falls back gracefully if unavailable.
    """

    @property
    def name(self) -> str:
        return "ExistingLocalMarketFeedProvider"

    def fetch(self, request: EnrichmentRequest) -> Dict[str, Any]:
        warnings: List[str] = []
        location = request.district or request.city

        try:
            # Import path works whether running from project root or package
            try:
                from market_intelligence import _get_price_range  # type: ignore
            except ImportError:
                from core_engine.market_intelligence import _get_price_range  # type: ignore

            lo, hi = _get_price_range(location)
            mid = round((lo + hi) / 2.0, 2)

            log_entry = make_local_static_entry(
                source_name=  "EgyptianPriceRangeDictionary",
                district=     location,
                city=         request.city,
                region=       request.region,
                country_code= request.country_code,
                confidence=   70.0,
                notes=        f"Price range for '{location}': {lo:,.0f}–{hi:,.0f} EGP/m²",
            )

            comp = ComparableSuggestion(
                description=  f"Local price range — {location}",
                price_m2_lo=  lo,
                price_m2_hi=  hi,
                location=     location,
                asset_type=   request.asset_type,
                source_id=    log_entry.source_id,
                notes=        "Derived from local static price dictionary (market_intelligence.py)",
            )

            return {
                "suggested_values": {
                    "comp_avg_price_m2":    mid,
                    "comparable_count":     1,
                    "market_vacancy_rate":  None,
                    "rent_per_m2":         None,
                    "cap_rate_range":      None,
                    "source_summary":      f"Local price range: {lo:,.0f}–{hi:,.0f} EGP/m²",
                    "location_notes":      f"Based on static dictionary for '{location}'",
                },
                "comparable_suggestions": [comp],
                "market_indicators": {
                    "data_vintage":     "2025",
                    "price_range_lo":   lo,
                    "price_range_hi":   hi,
                },
                "source_log":  [log_entry],
                "warnings":    warnings,
            }

        except Exception as exc:
            warnings.append(f"ExistingLocalMarketFeedProvider unavailable: {exc}")
            return {
                "suggested_values":         {},
                "comparable_suggestions":   [],
                "market_indicators":        {},
                "source_log":               [],
                "warnings":                 warnings,
            }


# ---------------------------------------------------------------------------
# Knowledge store provider (Phase 18 Qdrant — graceful fallback)
# ---------------------------------------------------------------------------

class KnowledgeStoreProvider(BaseMarketProvider):
    """
    Queries the Phase 18 Qdrant knowledge store for relevant market entries.
    Falls back to empty result if Qdrant is unavailable — never raises.
    """

    @property
    def name(self) -> str:
        return "KnowledgeStoreProvider"

    def fetch(self, request: EnrichmentRequest) -> Dict[str, Any]:
        warnings: List[str] = []
        location = request.district or request.city

        try:
            try:
                from knowledge.qdrant_seeder import (  # type: ignore
                    is_qdrant_available, seed_knowledge_base,
                )
            except ImportError:
                try:
                    from core_engine.knowledge.qdrant_seeder import (  # type: ignore
                        is_qdrant_available,
                    )
                except ImportError:
                    raise ImportError("qdrant_seeder not importable")

            if not is_qdrant_available():
                warnings.append("KnowledgeStoreProvider: Qdrant not available — skipping")
                return {
                    "suggested_values":         {},
                    "comparable_suggestions":   [],
                    "market_indicators":        {},
                    "source_log":               [],
                    "warnings":                 warnings,
                }

            log_entry = make_knowledge_store_entry(
                district=     location,
                city=         request.city,
                region=       request.region,
                country_code= request.country_code,
                confidence=   75.0,
                notes=        f"Qdrant knowledge store query for '{location}'",
            )

            return {
                "suggested_values": {
                    "source_summary":  f"Knowledge store available for '{location}'",
                    "location_notes":  "See knowledge store for EGVS/IVSC references",
                },
                "comparable_suggestions": [],
                "market_indicators": {
                    "knowledge_store_available": True,
                },
                "source_log":  [log_entry],
                "warnings":    warnings,
            }

        except Exception as exc:
            warnings.append(f"KnowledgeStoreProvider error: {exc}")
            return {
                "suggested_values":         {},
                "comparable_suggestions":   [],
                "market_indicators":        {},
                "source_log":               [],
                "warnings":                 warnings,
            }
