"""
source_log.py — Phase 19 source record builder.

Constructs SourceLogEntry instances for each data source consulted.
No scraping, no internet, no external calls.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Optional

from .models import SourceLogEntry


def _make_source_id(source_name: str, district: str, retrieved_at: str) -> str:
    """Stable short ID for a source record."""
    raw = f"{source_name}:{district}:{retrieved_at}"
    return "src_" + hashlib.md5(raw.encode()).hexdigest()[:12]


def make_local_static_entry(
    source_name:  str,
    district:     str,
    city:         str,
    region:       str,
    country_code: str,
    confidence:   float,
    notes:        str = "",
    source_uri:   str = "core_engine/market_intelligence.py",
) -> SourceLogEntry:
    """Build a SourceLogEntry for the local static price-range dictionary."""
    now = datetime.now(timezone.utc).isoformat()
    return SourceLogEntry(
        source_id=        _make_source_id(source_name, district, now),
        source_type=      "local_static",
        source_name=      source_name,
        source_uri=       source_uri,
        retrieved_at=     now,
        source_date=      "2025-01-01",     # price dict last updated
        country_code=     country_code,
        region=           region,
        city=             city,
        district=         district,
        confidence_score= confidence,
        extraction_method="price_range_lookup",
        notes=            notes,
    )


def make_mock_entry(
    district:     str,
    city:         str,
    region:       str,
    country_code: str,
    confidence:   float = 30.0,
) -> SourceLogEntry:
    """Build a SourceLogEntry for a mock/test provider."""
    now = datetime.now(timezone.utc).isoformat()
    return SourceLogEntry(
        source_id=        _make_source_id("MockMarketProvider", district, now),
        source_type=      "mock",
        source_name=      "MockMarketProvider",
        source_uri=       "memory",
        retrieved_at=     now,
        source_date=      "unknown",
        country_code=     country_code,
        region=           region,
        city=             city,
        district=         district,
        confidence_score= confidence,
        extraction_method="mock",
        notes=            "Test/mock provider — not for production use",
    )


def make_manual_entry(
    source_name:  str,
    source_uri:   str,
    district:     str,
    city:         str,
    region:       str,
    country_code: str,
    source_date:  str,
    confidence:   float,
    notes:        str = "",
) -> SourceLogEntry:
    """Build a SourceLogEntry for a manually provided data record."""
    now = datetime.now(timezone.utc).isoformat()
    return SourceLogEntry(
        source_id=        _make_source_id(source_name, district, now),
        source_type=      "manual",
        source_name=      source_name,
        source_uri=       source_uri,
        retrieved_at=     now,
        source_date=      source_date,
        country_code=     country_code,
        region=           region,
        city=             city,
        district=         district,
        confidence_score= confidence,
        extraction_method="manual",
        notes=            notes,
    )


def make_knowledge_store_entry(
    district:     str,
    city:         str,
    region:       str,
    country_code: str,
    confidence:   float,
    notes:        str = "",
) -> SourceLogEntry:
    """Build a SourceLogEntry for a Qdrant/knowledge-store lookup."""
    now = datetime.now(timezone.utc).isoformat()
    return SourceLogEntry(
        source_id=        _make_source_id("KnowledgeStoreProvider", district, now),
        source_type=      "knowledge_store",
        source_name=      "KnowledgeStoreProvider",
        source_uri=       "expert_smart_system/vector_db",
        retrieved_at=     now,
        source_date=      "2025-01-01",
        country_code=     country_code,
        region=           region,
        city=             city,
        district=         district,
        confidence_score= confidence,
        extraction_method="qdrant_query",
        notes=            notes,
    )
