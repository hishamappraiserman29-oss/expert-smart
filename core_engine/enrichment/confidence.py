"""
confidence.py — Phase 19 deterministic confidence scorer.

Scores data quality (0–100) based on objective, measurable criteria only.
Does NOT express valuation certainty. No model training, no external calls.
"""

from __future__ import annotations

from typing import List

from .models import SourceLogEntry


# ---------------------------------------------------------------------------
# Weights (must sum to 100)
# ---------------------------------------------------------------------------

_W_SOURCE_COUNT     = 20   # more sources → higher confidence
_W_RECENCY          = 25   # how recent the source data is
_W_GEO_MATCH        = 25   # geographic precision (district > city > region)
_W_ASSET_MATCH      = 15   # asset type specificity
_W_SOURCE_RELIABILITY = 15  # source category reliability tier


# ---------------------------------------------------------------------------
# Sub-scorers (each returns 0–100)
# ---------------------------------------------------------------------------

def _score_source_count(count: int) -> float:
    """More sources → higher score (saturates at 5+)."""
    if count == 0:
        return 0.0
    if count == 1:
        return 40.0
    if count == 2:
        return 65.0
    if count == 3:
        return 80.0
    if count == 4:
        return 90.0
    return 100.0


def _score_recency(source_date: str) -> float:
    """
    Recency score based on source_date (ISO YYYY-MM-DD prefix).
    Fresher data scores higher.  Unknown date → 20.
    """
    if not source_date or source_date == "unknown":
        return 20.0
    try:
        year = int(source_date[:4])
        # Using 2026 as reference year (current)
        age_years = max(0, 2026 - year)
        if age_years == 0:
            return 100.0
        if age_years == 1:
            return 85.0
        if age_years == 2:
            return 65.0
        if age_years == 3:
            return 45.0
        return max(10.0, 40.0 - age_years * 5.0)
    except (ValueError, TypeError):
        return 20.0


def _score_geo_match(extraction_method: str, district: str) -> float:
    """Geographic specificity of the match."""
    if extraction_method == "price_range_lookup" and district:
        return 90.0
    if extraction_method in ("manual", "qdrant_query") and district:
        return 80.0
    if district:
        return 60.0
    return 30.0


def _score_asset_match(source_name: str, asset_type: str) -> float:
    """Asset-type specificity."""
    if not asset_type or not source_name:
        return 40.0
    # Exact asset-type mention in source name scores highest
    asset_lower = asset_type.lower()
    source_lower = source_name.lower()
    if asset_lower in source_lower or source_lower in asset_lower:
        return 95.0
    return 60.0


def _score_source_reliability(source_type: str) -> float:
    """Reliability tier by source category."""
    tiers = {
        "manual":           90.0,
        "knowledge_store":  80.0,
        "local_feed":       75.0,
        "local_static":     65.0,
        "mock":             30.0,
    }
    return tiers.get(source_type, 40.0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_confidence(
    sources:    List[SourceLogEntry],
    asset_type: str = "",
    district:   str = "",
) -> float:
    """
    Return a deterministic confidence score in [0, 100].

    Parameters
    ----------
    sources     : list of SourceLogEntry consulted during enrichment
    asset_type  : requested asset type (for specificity scoring)
    district    : target district (for geo-match scoring)

    Returns
    -------
    float in [0.0, 100.0] — a DATA QUALITY indicator, not a valuation certainty.
    """
    if not sources:
        return 0.0

    count_score = _score_source_count(len(sources))

    # Average sub-scores across all sources
    recency_scores      = [_score_recency(s.source_date)                        for s in sources]
    geo_scores          = [_score_geo_match(s.extraction_method, district)      for s in sources]
    asset_scores        = [_score_asset_match(s.source_name, asset_type)        for s in sources]
    reliability_scores  = [_score_source_reliability(s.source_type)             for s in sources]

    avg_recency     = sum(recency_scores)     / len(sources)
    avg_geo         = sum(geo_scores)         / len(sources)
    avg_asset       = sum(asset_scores)       / len(sources)
    avg_reliability = sum(reliability_scores) / len(sources)

    weighted = (
        (_W_SOURCE_COUNT     / 100.0) * count_score
        + (_W_RECENCY        / 100.0) * avg_recency
        + (_W_GEO_MATCH      / 100.0) * avg_geo
        + (_W_ASSET_MATCH    / 100.0) * avg_asset
        + (_W_SOURCE_RELIABILITY / 100.0) * avg_reliability
    )

    return round(min(100.0, max(0.0, weighted)), 2)
