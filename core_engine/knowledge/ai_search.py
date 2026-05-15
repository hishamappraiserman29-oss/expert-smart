"""
ai_search.py — AI-Powered Smart Search (Phase 35)

Query expansion and semantic relevance scoring.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_SYNONYMS: Dict[str, List[str]] = {
    "property": ["real estate", "asset", "building", "land"],
    "valuation": ["appraisal", "assessment", "evaluation", "price"],
    "residential": ["housing", "apartment", "house", "home"],
    "commercial": ["office", "retail", "shop", "business"],
    "industrial": ["warehouse", "factory", "manufacturing"],
    "mortgage": ["loan", "financing", "credit"],
    "depreciation": ["wear and tear", "deterioration", "aging"],
    "comparable": ["similar", "comparable sales", "comps"],
    "income": ["rent", "yield", "revenue", "cash flow"],
    "standard": ["guidelines", "regulation", "requirement", "rule"],
}


class SmartSearchEngine:
    """AI-powered search with query expansion and semantic scoring."""

    def __init__(self) -> None:
        self._search_history: List[str] = []
        logger.info("Smart Search Engine initialized")

    def expand_query(self, query: str) -> List[str]:
        terms = {query.lower()}
        for word, syns in _SYNONYMS.items():
            if word in query.lower():
                terms.update(syns)
        return list(terms)

    def semantic_search(
        self,
        query: str,
        content_list: List[Any],
        similarity_threshold: float = 0.3,
    ) -> List[Tuple[Any, float]]:
        self._search_history.append(query)
        expanded = self.expand_query(query)
        results: List[Tuple[Any, float]] = []
        for content in content_list:
            score = self._calculate_relevance(expanded, content)
            if score >= similarity_threshold:
                results.append((content, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def _calculate_relevance(self, terms: List[str], content: Any) -> float:
        content_text = ""
        if hasattr(content, "title"):
            content_text += content.title.lower() + " "
        if hasattr(content, "description"):
            content_text += content.description.lower() + " "
        if hasattr(content, "tags"):
            content_text += " ".join(getattr(content, "tags", [])).lower() + " "
        if hasattr(content, "body"):
            content_text += content.body.lower()[:500] + " "

        if not terms:
            return 0.0
        matches = sum(1 for term in terms if term in content_text)
        return min(1.0, matches / len(terms) * 1.5)

    def autocomplete(
        self,
        partial_query: str,
        suggestions_list: List[str],
        limit: int = 5,
    ) -> List[str]:
        partial_lower = partial_query.lower()
        matches = [s for s in suggestions_list if s.lower().startswith(partial_lower)]
        # also include contains-matches after startswith
        contains = [s for s in suggestions_list if partial_lower in s.lower() and not s.lower().startswith(partial_lower)]
        return (matches + contains)[:limit]

    def get_search_suggestions(self, query: str) -> List[str]:
        """Return synonym-based search suggestions."""
        expanded = self.expand_query(query)
        return [t for t in expanded if t != query.lower()][:8]

    def get_search_history(self, limit: int = 10) -> List[str]:
        return list(self._search_history[-limit:])


smart_search = SmartSearchEngine()
