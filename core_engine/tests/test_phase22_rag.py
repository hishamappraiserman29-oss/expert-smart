"""
test_phase22_rag.py — Phase 22 RAG Enhancement Tests

Covers:
  A. KnowledgeBase  — add/get/list/search/statistics/export-import
  B. RAGEnhancer    — retrieve, rerank, context window, citations, enhance
  C. ContextManager — compression, prompt building, token estimation, window fit
"""

from __future__ import annotations

import sys
import json
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from knowledge.knowledge_base import (
    KnowledgeBase, KnowledgeEntry, KnowledgeCategory, LanguageCode,
)
from knowledge.rag_enhancer import RAGEnhancer
from knowledge.context_manager import ContextManager
from knowledge.seed_data import get_seed_entries


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_entry(eid: str = "e001", category: KnowledgeCategory = KnowledgeCategory.EGVS) -> KnowledgeEntry:
    return KnowledgeEntry(
        id=eid,
        title=f"Entry {eid}",
        category=category,
        content=f"Detailed content about {eid} covering valuation standards methodology.",
        language=LanguageCode.ENGLISH,
        tags=["test", "valuation"],
        source="Test Source",
        version="1.0",
    )


def _kb_with_seeds() -> KnowledgeBase:
    kb = KnowledgeBase()
    for entry in get_seed_entries():
        kb.add_entry(entry, auto_embed=False)
    return kb


# ===========================================================================
# A. KnowledgeBase
# ===========================================================================

class TestKnowledgeBase:

    def test_A01_add_and_get_entry(self):
        kb = KnowledgeBase()
        entry = _make_entry("a01")
        assert kb.add_entry(entry, auto_embed=False)
        retrieved = kb.get_entry("a01")
        assert retrieved is not None
        assert retrieved.id == "a01"

    def test_A02_missing_entry_returns_none(self):
        kb = KnowledgeBase()
        assert kb.get_entry("nonexistent_xyz") is None

    def test_A03_list_all_entries(self):
        kb = _kb_with_seeds()
        all_entries = kb.list_entries()
        assert len(all_entries) == len(get_seed_entries())

    def test_A04_list_filter_by_category(self):
        kb = _kb_with_seeds()
        egvs = kb.list_entries(category=KnowledgeCategory.EGVS)
        assert len(egvs) > 0
        assert all(e.category == KnowledgeCategory.EGVS for e in egvs)

    def test_A05_list_filter_by_language(self):
        kb = _kb_with_seeds()
        english = kb.list_entries(language=LanguageCode.ENGLISH)
        assert len(english) > 0
        assert all(e.language == LanguageCode.ENGLISH for e in english)

    def test_A06_statistics_counts(self):
        kb = _kb_with_seeds()
        stats = kb.get_statistics()
        assert stats["total_entries"] == len(get_seed_entries())
        assert "by_category" in stats
        assert "by_language" in stats
        assert "last_updated" in stats
        assert stats["total_entries"] > 0

    def test_A07_keyword_search_returns_relevant(self):
        kb = _kb_with_seeds()
        results = kb.search("residential valuation comparable")
        assert isinstance(results, list)
        assert len(results) > 0
        titles = [r.title.lower() for r in results]
        assert any("residential" in t for t in titles)

    def test_A08_search_category_filter(self):
        kb = _kb_with_seeds()
        results = kb.search("valuation", top_k=10, category=KnowledgeCategory.CBE)
        assert all(r.category == KnowledgeCategory.CBE for r in results)

    def test_A09_export_and_import(self, tmp_path):
        kb = KnowledgeBase()
        kb.add_entry(_make_entry("exp1"), auto_embed=False)
        kb.add_entry(_make_entry("exp2", KnowledgeCategory.IVSC), auto_embed=False)
        fname = str(tmp_path / "kb_export.json")
        kb.export(fname)
        assert Path(fname).exists()
        data = json.loads(Path(fname).read_text(encoding="utf-8"))
        assert data["stats"]["total_entries"] == 2

    def test_A10_to_dict_structure(self):
        entry = _make_entry("dict_test")
        d = entry.to_dict()
        for key in ("id", "title", "category", "content", "language", "tags", "source"):
            assert key in d
        assert d["id"] == "dict_test"
        assert d["category"] == KnowledgeCategory.EGVS.value

    def test_A11_seed_data_loaded(self):
        entries = get_seed_entries()
        assert len(entries) >= 10
        categories = {e.category for e in entries}
        assert KnowledgeCategory.EGVS           in categories
        assert KnowledgeCategory.IVSC           in categories
        assert KnowledgeCategory.CBE            in categories
        assert KnowledgeCategory.MARKET_INSIGHT in categories
        assert KnowledgeCategory.CASE_STUDY     in categories
        assert KnowledgeCategory.METHODOLOGY    in categories

    def test_A12_add_entry_no_embed_returns_true(self):
        kb = KnowledgeBase()
        ok = kb.add_entry(_make_entry("no_emb"), auto_embed=False)
        assert ok is True


# ===========================================================================
# B. RAGEnhancer
# ===========================================================================

class TestRAGEnhancer:

    def test_B01_retrieve_returns_list(self):
        enhancer = RAGEnhancer(_kb_with_seeds())
        results = enhancer.retrieve_relevant_knowledge("valuation standards")
        assert isinstance(results, list)

    def test_B02_retrieve_finds_relevant_entries(self):
        enhancer = RAGEnhancer(_kb_with_seeds())
        results = enhancer.retrieve_relevant_knowledge("residential valuation EGVS")
        assert len(results) > 0

    def test_B03_rerank_sorts_by_relevance(self):
        kb = _kb_with_seeds()
        all_entries = kb.list_entries()
        enhancer = RAGEnhancer(kb)
        top = enhancer.rerank_results("residential comparable Cairo", all_entries, top_k=3)
        assert len(top) <= 3
        assert isinstance(top, list)

    def test_B04_rerank_empty_input(self):
        enhancer = RAGEnhancer(_kb_with_seeds())
        result = enhancer.rerank_results("any query", [], top_k=5)
        assert result == []

    def test_B05_get_context_window_returns_string(self):
        enhancer = RAGEnhancer(_kb_with_seeds())
        entries = get_seed_entries()[:3]
        context = enhancer.get_context_window(entries)
        assert isinstance(context, str)
        assert len(context) > 0

    def test_B06_context_window_respects_token_limit(self):
        enhancer = RAGEnhancer(_kb_with_seeds())
        entries = get_seed_entries()
        context = enhancer.get_context_window(entries, max_tokens=500)
        estimated_tokens = len(context) // 4
        assert estimated_tokens <= 520   # small tolerance

    def test_B07_generate_citation_format(self):
        entry = _make_entry("cit_01")
        enhancer = RAGEnhancer()
        citation = enhancer.generate_citation(entry)
        assert "Entry cit_01" in citation
        assert "Test Source" in citation
        assert "1.0" in citation

    def test_B08_enhance_valuation_context_keys(self):
        enhancer = RAGEnhancer(_kb_with_seeds())
        result = enhancer.enhance_valuation_context(
            property_type="residential",
            location="Cairo",
            purpose="market_value",
        )
        assert "context"   in result
        assert "citations" in result
        assert "entries"   in result
        assert isinstance(result["citations"], list)
        assert isinstance(result["entries"], list)

    def test_B09_enhance_valuation_returns_context_text(self):
        enhancer = RAGEnhancer(_kb_with_seeds())
        result = enhancer.enhance_valuation_context("commercial", "Heliopolis", "mortgage")
        # With seed data loaded, keyword search should find something
        assert isinstance(result["context"], str)

    def test_B10_enhance_report_context_keys(self):
        enhancer = RAGEnhancer(_kb_with_seeds())
        vdata = {"property_type": "residential", "location": "Cairo",
                 "primary_purpose": "market_value", "value": 1_500_000}
        result = enhancer.enhance_report_context(vdata)
        assert "valuation"            in result
        assert "kb_context"           in result
        assert "citations"            in result
        assert "methodology_guidance" in result

    def test_B11_methodology_guidance_known_purpose(self):
        enhancer = RAGEnhancer()
        result = enhancer.enhance_report_context({"primary_purpose": "mortgage"})
        assert "CBE" in result["methodology_guidance"] or \
               "loan" in result["methodology_guidance"].lower()

    def test_B12_compute_relevance_score(self):
        score_high = RAGEnhancer._compute_relevance(
            "residential valuation Cairo", "residential valuation comparable Cairo market"
        )
        score_low = RAGEnhancer._compute_relevance(
            "residential valuation Cairo", "unrelated text about something else entirely"
        )
        assert score_high > score_low
        assert 0.0 <= score_high <= 1.0


# ===========================================================================
# C. ContextManager
# ===========================================================================

class TestContextManager:

    def test_C01_estimate_tokens_proportional(self):
        cm = ContextManager()
        short = cm.estimate_tokens("Hello")
        long  = cm.estimate_tokens("Hello " * 100)
        assert long > short

    def test_C02_estimate_tokens_rule(self):
        cm = ContextManager()
        text = "A" * 400
        assert cm.estimate_tokens(text) == 100

    def test_C03_compress_high_level_is_shortest(self):
        cm = ContextManager()
        entries = get_seed_entries()[:3]
        high   = cm.compress_knowledge_entries(entries, "high")
        medium = cm.compress_knowledge_entries(entries, "medium")
        low    = cm.compress_knowledge_entries(entries, "low")
        assert len(high) < len(medium) < len(low)

    def test_C04_compress_all_levels_return_string(self):
        cm = ContextManager()
        entries = get_seed_entries()[:2]
        for level in ("low", "medium", "high"):
            result = cm.compress_knowledge_entries(entries, level)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_C05_build_system_prompt_contains_kb(self):
        cm = ContextManager()
        ctx = "## EGVS Standard\nContent here."
        prompt = cm.build_claude_system_prompt(ctx)
        assert "EGVS" in prompt
        assert "real estate" in prompt.lower()
        assert "cite" in prompt.lower()

    def test_C06_build_system_prompt_includes_context(self):
        cm = ContextManager()
        ctx = "UNIQUE_MARKER_12345"
        prompt = cm.build_claude_system_prompt(ctx)
        assert "UNIQUE_MARKER_12345" in prompt

    def test_C07_fit_context_window_truncates(self):
        cm = ContextManager(max_tokens=1000)
        context = "A" * 5000
        fitted  = cm.fit_context_window(context, "short query", "short prompt")
        tokens  = cm.estimate_tokens(fitted)
        assert tokens < 1000

    def test_C08_fit_context_window_no_truncation_when_small(self):
        cm = ContextManager(max_tokens=8000)
        context = "Short context."
        fitted  = cm.fit_context_window(context, "query", "prompt")
        assert context in fitted
        assert "[Context truncated" not in fitted

    def test_C09_fit_context_window_truncation_notice(self):
        cm = ContextManager(max_tokens=500)
        context = "Sentence one. " * 200
        fitted  = cm.fit_context_window(context, "q", "p")
        assert "[Context truncated" in fitted

    def test_C10_fit_uses_instance_max_tokens(self):
        """max_tokens kwarg defaults to self.max_tokens."""
        tight = ContextManager(max_tokens=200)
        loose = ContextManager(max_tokens=8000)
        text  = "Word " * 1000
        t_tight = tight.fit_context_window(text, "q", "p")
        t_loose = loose.fit_context_window(text, "q", "p")
        assert len(t_tight) < len(t_loose)

    def test_C11_compress_high_contains_all_titles(self):
        cm = ContextManager()
        entries = get_seed_entries()[:3]
        compressed = cm.compress_knowledge_entries(entries, "high")
        for e in entries:
            assert e.title in compressed

    def test_C12_compress_medium_contains_first_paragraphs(self):
        cm = ContextManager()
        entries = get_seed_entries()[:2]
        compressed = cm.compress_knowledge_entries(entries, "medium")
        for e in entries:
            first_para = e.content.split("\n\n")[0][:50]
            assert first_para[:30] in compressed
