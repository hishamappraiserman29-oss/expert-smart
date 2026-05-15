"""
context_manager.py — Phase 22 Context Compression & Management

Fits knowledge into Claude's context window efficiently with three
compression levels, provides a Claude system-prompt builder, and
truncates oversized contexts at sentence boundaries.

Classes:
    ContextManager — compress entries, build prompts, fit context windows
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .knowledge_base import KnowledgeEntry


class ContextManager:
    """
    Manage and compress knowledge entries to fit a context window.

    Parameters
    ----------
    max_tokens : default maximum tokens for context window operations
                 (also used as the default for fit_context_window when
                 no explicit max_tokens argument is supplied)
    """

    def __init__(self, max_tokens: int = 8000) -> None:
        self.max_tokens = max_tokens

    # -- Compression ----------------------------------------------------------

    def compress_knowledge_entries(
        self,
        entries: List[KnowledgeEntry],
        compression_level: str = "medium",
    ) -> str:
        """
        Compress *entries* to a text block.

        Parameters
        ----------
        compression_level : "high"   — first sentence only per entry
                            "medium" — first paragraph only (default)
                            "low"    — full content
        """
        level = compression_level.lower()
        if level == "high":
            return self._summarize_entries(entries)
        if level == "medium":
            return self._extract_key_points(entries)
        return self._format_entries_full(entries)

    def _summarize_entries(self, entries: List[KnowledgeEntry]) -> str:
        parts: List[str] = []
        for e in entries:
            sentences = e.content.split(".")
            summary = (sentences[0].strip() + ".") if sentences else e.content[:120]
            parts.append(f"{e.title}: {summary}")
        return "\n".join(parts)

    def _extract_key_points(self, entries: List[KnowledgeEntry]) -> str:
        parts: List[str] = []
        for e in entries:
            paragraphs = e.content.split("\n\n")
            excerpt = paragraphs[0].strip() if paragraphs else e.content[:200]
            parts.append(f"### {e.title}\n{excerpt}")
        return "\n\n".join(parts)

    def _format_entries_full(self, entries: List[KnowledgeEntry]) -> str:
        parts: List[str] = []
        for e in entries:
            parts.append(
                f"\n## {e.title}\n"
                f"**Category:** {e.category.value}\n"
                f"**Source:** {e.source}\n\n"
                f"{e.content}\n"
            )
        return "\n".join(parts)

    # -- Prompt building ------------------------------------------------------

    def build_claude_system_prompt(
        self,
        kb_context: str,
        domain: str = "real_estate",
    ) -> str:
        """
        Build a Claude system prompt that embeds *kb_context*.

        Parameters
        ----------
        kb_context : pre-formatted knowledge block
        domain     : application domain label (informational only)
        """
        return (
            "You are an expert real estate valuation assistant specialising in "
            "Egyptian property markets.\n\n"
            "Your expertise includes:\n"
            "- EGVS (Egyptian Valuation Standards)\n"
            "- IVSC (International Valuation Standards)\n"
            "- CBE (Central Bank of Egypt) regulations\n"
            "- Egyptian real estate market analysis\n\n"
            "## Knowledge Base Context\n\n"
            f"{kb_context}\n\n"
            "## Instructions\n\n"
            "1. Always cite sources when using knowledge from the KB.\n"
            "2. Provide evidence-based valuations using comparable sales.\n"
            "3. Consider local market conditions and regulations.\n"
            "4. Follow EGVS and IVSC standards.\n"
            "5. Be transparent about assumptions and limitations.\n\n"
            "When responding:\n"
            "- Start with a clear summary.\n"
            "- Provide methodology and calculations.\n"
            "- Include relevant citations.\n"
            "- Address limitations and uncertainties.\n"
        )

    # -- Token estimation -----------------------------------------------------

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Rough token estimate: ~1 token per 4 characters.

        GPT-family models average ~4 chars/token for English prose;
        Arabic text averages fewer characters per token, so this is
        conservative (may over-count) which is the safe direction.
        """
        return len(text) // 4

    # -- Context fitting ------------------------------------------------------

    def fit_context_window(
        self,
        context: str,
        query: str,
        system_prompt: str,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Truncate *context* so the total prompt fits within *max_tokens*.

        Uses ``self.max_tokens`` when *max_tokens* is not supplied,
        so ``ContextManager(max_tokens=1000).fit_context_window(...)``
        constrains to 1 000 tokens without extra arguments.

        Truncation is done at the last sentence boundary for readability.
        A ``[Context truncated ...]`` notice is appended when truncated.
        """
        limit = max_tokens if max_tokens is not None else self.max_tokens

        prompt_tokens  = self.estimate_tokens(system_prompt)
        query_tokens   = self.estimate_tokens(query)
        buffer         = min(500, limit // 2)
        available      = limit - prompt_tokens - query_tokens - buffer

        if available <= 0:
            return "[Context omitted: insufficient token budget]"

        context_tokens = self.estimate_tokens(context)
        if context_tokens <= available:
            return context

        # Truncate to character limit, snap to last sentence boundary
        max_chars  = available * 4
        truncated  = context[:max_chars]
        last_dot   = truncated.rfind(".")
        if last_dot > 0:
            truncated = truncated[: last_dot + 1]

        return truncated + "\n\n[Context truncated to fit window]"
