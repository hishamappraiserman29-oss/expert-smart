"""
knowledge/ — Phase 22 Knowledge Base + RAG Enhancement package.

Modules:
    knowledge_base   — KB management with in-memory + Qdrant vector store
    rag_enhancer     — retrieval-augmented generation helpers
    context_manager  — context compression and Claude prompt building
    seed_data        — initial EGVS / IVSC / CBE domain entries
"""

from .knowledge_base import KnowledgeBase, KnowledgeEntry, KnowledgeCategory, LanguageCode
from .rag_enhancer import RAGEnhancer
from .context_manager import ContextManager
from .seed_data import get_seed_entries

__all__ = [
    "KnowledgeBase",
    "KnowledgeEntry",
    "KnowledgeCategory",
    "LanguageCode",
    "RAGEnhancer",
    "ContextManager",
    "get_seed_entries",
]
