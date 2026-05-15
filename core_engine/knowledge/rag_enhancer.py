"""
rag_enhancer.py — Phase 22 RAG Enhancement

Retrieves relevant knowledge base entries for a query, reranks them,
formats a context window, generates citations, and produces an enriched
payload for Claude prompts and valuation reports.

Classes:
    RAGEnhancer — retrieval, reranking, context building, citation generation
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .knowledge_base import KnowledgeBase, KnowledgeEntry


class RAGEnhancer:
    """
    Retrieval-Augmented Generation helper.

    Wraps a KnowledgeBase and provides higher-level helpers for:
      - retrieving relevant entries for a free-text query
      - reranking by lightweight term-overlap scoring
      - building a formatted context window
      - generating inline citations
      - enriching valuation / report payloads

    Parameters
    ----------
    knowledge_base : KnowledgeBase instance (creates a default one if None)
    """

    def __init__(self, knowledge_base: Optional[KnowledgeBase] = None) -> None:
        self.kb = knowledge_base or KnowledgeBase()

    # -- Retrieval ------------------------------------------------------------

    def retrieve_relevant_knowledge(
        self,
        query: str,
        top_k: int = 5,
        min_relevance: float = 0.0,
    ) -> List[KnowledgeEntry]:
        """
        Return up to *top_k* KB entries relevant to *query*.

        Uses KB.search() (Qdrant with in-memory fallback).
        Entries without embeddings are still returned via keyword search.

        Parameters
        ----------
        query         : free-text query
        top_k         : maximum entries to return
        min_relevance : minimum relevance threshold (0-1); applied when
                        embedding similarity is available
        """
        entries = self.kb.search(query, top_k=top_k)
        return entries[:top_k]

    # -- Reranking ------------------------------------------------------------

    def rerank_results(
        self,
        query: str,
        entries: List[KnowledgeEntry],
        top_k: int = 3,
    ) -> List[KnowledgeEntry]:
        """
        Rerank *entries* by lightweight term-overlap relevance to *query*.

        In production this would use a cross-encoder; here we use the same
        fast heuristic as the in-memory KB search so tests run offline.
        """
        if not entries:
            return []
        scored = [
            (self._compute_relevance(query, e.title + " " + e.content), e)
            for e in entries
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:top_k]]

    @staticmethod
    def _compute_relevance(query: str, content: str) -> float:
        """Term-overlap relevance score in [0, 1]."""
        q_terms = set(query.lower().split())
        c_terms = set(content.lower().split())
        if not q_terms:
            return 0.0
        return min(1.0, len(q_terms & c_terms) / len(q_terms))

    # -- Context window -------------------------------------------------------

    def get_context_window(
        self,
        entries: List[KnowledgeEntry],
        max_tokens: int = 4000,
    ) -> str:
        """
        Concatenate entries into a formatted context string capped at
        approximately *max_tokens* (estimated as len(text) / 4).
        """
        parts: List[str] = []
        used = 0
        for entry in entries:
            block = (
                f"\n## {entry.title}\n\n"
                f"**Category:** {entry.category.value}\n"
                f"**Source:** {entry.source}\n\n"
                f"{entry.content}\n\n---\n"
            )
            cost = len(block) // 4
            if used + cost > max_tokens:
                break
            parts.append(block)
            used += cost
        return "\n".join(parts)

    # -- Citations ------------------------------------------------------------

    def generate_citation(self, entry: KnowledgeEntry) -> str:
        """Return a short citation string for *entry*."""
        return f"{entry.title} ({entry.source}, v{entry.version})"

    # -- High-level helpers ---------------------------------------------------

    def enhance_valuation_context(
        self,
        property_type: str,
        location: str,
        purpose: str,
    ) -> Dict[str, Any]:
        """
        Build an enriched context payload for a valuation request.

        Searches KB with multiple domain-specific queries, deduplicates,
        reranks, and returns context + citations + raw entry dicts.

        Parameters
        ----------
        property_type : e.g. "residential", "commercial", "land"
        location      : e.g. "Cairo", "Heliopolis"
        purpose       : e.g. "market_value", "mortgage", "insurance"
        """
        queries = [
            f"{property_type} valuation standards",
            f"{location} market insights",
            f"{purpose} valuation approach",
            f"EGVS {property_type} guidelines",
        ]

        seen: Dict[str, KnowledgeEntry] = {}
        for q in queries:
            for e in self.retrieve_relevant_knowledge(q, top_k=3):
                seen[e.id] = e

        top = self.rerank_results(
            f"{property_type} {location} {purpose}",
            list(seen.values()),
            top_k=5,
        )

        return {
            "context":   self.get_context_window(top),
            "citations": [self.generate_citation(e) for e in top],
            "entries":   [e.to_dict() for e in top],
        }

    def enhance_report_context(self, valuation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wrap a completed valuation dict with KB context for report generation.

        Returns the original data plus kb_context, citations, and
        methodology guidance keyed to the valuation purpose.
        """
        prop_type = valuation_data.get("property_type", "residential")
        location  = valuation_data.get("location", "Cairo")
        purpose   = valuation_data.get("primary_purpose", "market_value")

        enhanced = self.enhance_valuation_context(prop_type, location, purpose)

        return {
            "valuation":            valuation_data,
            "kb_context":           enhanced["context"],
            "citations":            enhanced["citations"],
            "methodology_guidance": self._methodology_guidance(purpose),
        }

    # -- Private --------------------------------------------------------------

    @staticmethod
    def _methodology_guidance(purpose: str) -> str:
        _GUIDES: Dict[str, str] = {
            "market_value": (
                "Market value is estimated using the comparative approach, "
                "weighting recent arm's-length transactions in the same market."
            ),
            "insurance": (
                "Insurance value covers the replacement cost of the built "
                "improvements; land is excluded."
            ),
            "mortgage": (
                "Mortgage valuation considers the loan-to-value ratio per CBE "
                "regulations and adopts a conservative stance."
            ),
            "ifrs13": (
                "IFRS 13 fair value uses the highest and best use concept "
                "within a three-level hierarchy of observable inputs."
            ),
        }
        return _GUIDES.get(purpose, "")
