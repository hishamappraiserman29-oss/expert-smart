"""search — Phase 37 Comparable Search Enhancement"""

from search.comparable_search import (
    ComparableSearchEngine, SearchCriteria, SearchType, PropertyAttribute,
    ComparableResult, comparable_search,
)
from search.similarity_matcher import (
    SmartMatcher, MatchingProfile, MatchScore, MatchingStrategy,
    smart_matcher,
)
from search.adjustment_factors import (
    AdjustmentFactorEngine, PriceAdjustment, AdjustedComparable,
    AdjustmentCategory, adjustment_engine,
)

__all__ = [
    "ComparableSearchEngine", "SearchCriteria", "SearchType", "PropertyAttribute",
    "ComparableResult", "comparable_search",
    "SmartMatcher", "MatchingProfile", "MatchScore", "MatchingStrategy", "smart_matcher",
    "AdjustmentFactorEngine", "PriceAdjustment", "AdjustedComparable",
    "AdjustmentCategory", "adjustment_engine",
]
