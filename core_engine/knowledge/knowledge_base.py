"""
knowledge_base.py — Phase 22 Knowledge Base Framework

Stores domain knowledge (EGVS, IVSC, CBE, market insights, case studies)
with optional Qdrant vector-store integration.

When Qdrant / Ollama are unavailable the KB falls back transparently to an
in-memory keyword-overlap search so all functionality keeps working.

Classes:
    KnowledgeCategory  — entry category enum
    LanguageCode       — supported language enum
    KnowledgeEntry     — single KB entry (content + optional embedding)
    KnowledgeBase      — add / search / list / export / import entries
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class KnowledgeCategory(str, Enum):
    EGVS           = "egyptian_valuation_standards"
    IVSC           = "international_valuation_standards"
    CBE            = "central_bank_egypt"
    CASE_STUDY     = "case_study"
    MARKET_INSIGHT = "market_insight"
    REGULATORY     = "regulatory"
    METHODOLOGY    = "methodology"
    EXAMPLE        = "example"


class LanguageCode(str, Enum):
    ARABIC  = "ar"
    ENGLISH = "en"
    FRENCH  = "fr"


# ---------------------------------------------------------------------------
# KnowledgeEntry
# ---------------------------------------------------------------------------

@dataclass
class KnowledgeEntry:
    """Single knowledge entry with optional embedding vector."""

    id:         str
    title:      str
    category:   KnowledgeCategory
    content:    str
    language:   LanguageCode       = LanguageCode.ENGLISH
    tags:       List[str]          = field(default_factory=list)
    source:     str                = ""
    version:    str                = "1.0"
    created_at: datetime           = field(default_factory=datetime.utcnow)
    updated_at: datetime           = field(default_factory=datetime.utcnow)
    embedding:  Optional[List[float]] = None
    metadata:   Dict[str, Any]     = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id":         self.id,
            "title":      self.title,
            "category":   self.category.value,
            "content":    self.content,
            "language":   self.language.value,
            "tags":       self.tags,
            "source":     self.source,
            "version":    self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata":   self.metadata,
        }


# ---------------------------------------------------------------------------
# KnowledgeBase
# ---------------------------------------------------------------------------

class KnowledgeBase:
    """
    Manage the domain knowledge store.

    Primary store: in-memory dict (always available).
    Optional vector store: Qdrant (requires Qdrant + Ollama running).
    When the external services are unavailable every method degrades
    gracefully to in-memory keyword search.

    Parameters
    ----------
    qdrant_url       : Qdrant REST endpoint (default: http://localhost:6333)
    collection_name  : Qdrant collection name
    ollama_url       : Ollama embedding endpoint (default: http://localhost:11434)
    """

    def __init__(
        self,
        qdrant_url: str = "http://localhost:6333",
        collection_name: str = "expert_smart_kb",
        ollama_url: str = "http://localhost:11434",
    ) -> None:
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name
        self.ollama_url = ollama_url
        self.entries: Dict[str, KnowledgeEntry] = {}

    # -- Embedding ------------------------------------------------------------

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding via Ollama. Returns [] on any failure."""
        try:
            import requests
            response = requests.post(
                f"{self.ollama_url}/api/embeddings",
                json={"model": "llama2", "prompt": text},
                timeout=5,
            )
            if response.status_code == 200:
                return response.json().get("embedding", [])
        except Exception:
            pass
        return []

    # -- Write ----------------------------------------------------------------

    def add_entry(self, entry: KnowledgeEntry, auto_embed: bool = True) -> bool:
        """
        Add or update an entry in the KB.

        Parameters
        ----------
        entry      : the entry to add
        auto_embed : generate an Ollama embedding if entry has none
        """
        try:
            if auto_embed and not entry.embedding:
                entry.embedding = self.generate_embedding(entry.content)
            self.entries[entry.id] = entry
            self._upsert_to_qdrant(entry)
            return True
        except Exception as exc:
            print(f"[KB] Error adding entry {entry.id}: {exc}")
            return False

    def _upsert_to_qdrant(self, entry: KnowledgeEntry) -> None:
        """Best-effort Qdrant upsert — silently ignored if unavailable."""
        if not entry.embedding:
            return
        try:
            import requests
            point = {
                "id":      hash(entry.id) % (2 ** 53),
                "vector":  entry.embedding,
                "payload": entry.to_dict(),
            }
            requests.put(
                f"{self.qdrant_url}/collections/{self.collection_name}/points",
                json={"points": [point]},
                timeout=3,
            )
        except Exception:
            pass

    # -- Search ---------------------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int = 5,
        language: Optional[LanguageCode] = None,
        category: Optional[KnowledgeCategory] = None,
    ) -> List[KnowledgeEntry]:
        """
        Semantic search via Qdrant, falling back to in-memory keyword search.

        Filters by *language* and *category* if provided.
        """
        results = self._qdrant_search(query, top_k, language, category)
        if results:
            return results
        return self._keyword_search(query, top_k, language, category)

    def _qdrant_search(
        self,
        query: str,
        top_k: int,
        language: Optional[LanguageCode],
        category: Optional[KnowledgeCategory],
    ) -> List[KnowledgeEntry]:
        """Attempt Qdrant vector search. Returns [] on any failure."""
        try:
            import requests
            q_emb = self.generate_embedding(query)
            if not q_emb:
                return []
            resp = requests.post(
                f"{self.qdrant_url}/collections/{self.collection_name}/points/search",
                json={"vector": q_emb, "limit": top_k * 2},
                timeout=5,
            )
            if resp.status_code != 200:
                return []
            hits = resp.json().get("result", [])
            entries: List[KnowledgeEntry] = []
            for hit in hits:
                eid = hit.get("payload", {}).get("id")
                if eid and eid in self.entries:
                    e = self.entries[eid]
                    if language and e.language != language:
                        continue
                    if category and e.category != category:
                        continue
                    entries.append(e)
            return entries[:top_k]
        except Exception:
            return []

    def _keyword_search(
        self,
        query: str,
        top_k: int,
        language: Optional[LanguageCode],
        category: Optional[KnowledgeCategory],
    ) -> List[KnowledgeEntry]:
        """
        In-memory keyword overlap search — always available.

        Scores each entry by (matching query terms) / (total query terms)
        against title + content + tags combined.
        """
        query_terms = set(query.lower().split())
        scored: List[tuple] = []

        for entry in self.entries.values():
            if language and entry.language != language:
                continue
            if category and entry.category != category:
                continue
            text = " ".join([
                entry.title,
                entry.content,
                " ".join(entry.tags),
                entry.source,
            ]).lower()
            text_terms = set(text.split())
            overlap = len(query_terms & text_terms)
            if overlap:
                score = overlap / len(query_terms) if query_terms else 0.0
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:top_k]]

    # -- Read -----------------------------------------------------------------

    def get_entry(self, entry_id: str) -> Optional[KnowledgeEntry]:
        return self.entries.get(entry_id)

    def list_entries(
        self,
        category: Optional[KnowledgeCategory] = None,
        language: Optional[LanguageCode] = None,
    ) -> List[KnowledgeEntry]:
        entries = list(self.entries.values())
        if category:
            entries = [e for e in entries if e.category == category]
        if language:
            entries = [e for e in entries if e.language == language]
        return entries

    # -- Stats ----------------------------------------------------------------

    def get_statistics(self) -> Dict[str, Any]:
        by_category: Dict[str, int] = {}
        by_language: Dict[str, int] = {}
        for entry in self.entries.values():
            cat  = entry.category.value
            lang = entry.language.value
            by_category[cat]  = by_category.get(cat, 0)  + 1
            by_language[lang] = by_language.get(lang, 0) + 1

        last_updated = max(
            (e.updated_at for e in self.entries.values()),
            default=datetime.utcnow(),
        ).isoformat()

        return {
            "total_entries": len(self.entries),
            "by_category":   by_category,
            "by_language":   by_language,
            "last_updated":  last_updated,
        }

    # -- Import / Export ------------------------------------------------------

    def export(self, filename: str = "knowledge_base.json") -> None:
        data = {
            "entries": [e.to_dict() for e in self.entries.values()],
            "stats":   self.get_statistics(),
        }
        Path(filename).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[KB] Exported {len(self.entries)} entries -> {filename}")

    def import_entries(self, filename: str) -> None:
        data = json.loads(Path(filename).read_text(encoding="utf-8"))
        before = len(self.entries)
        for d in data.get("entries", []):
            entry = KnowledgeEntry(
                id=d["id"],
                title=d["title"],
                category=KnowledgeCategory(d["category"]),
                content=d["content"],
                language=LanguageCode(d.get("language", "en")),
                tags=d.get("tags", []),
                source=d.get("source", ""),
                version=d.get("version", "1.0"),
                metadata=d.get("metadata", {}),
            )
            self.add_entry(entry, auto_embed=True)
        added = len(self.entries) - before
        print(f"[KB] Imported {added} entries from {filename}")
