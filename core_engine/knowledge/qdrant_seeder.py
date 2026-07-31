"""
qdrant_seeder.py — Phase 18 Qdrant Knowledge Base Seeder

Standalone operator script that creates the egypt_estate collection and seeds
the 13 curated EGVS/IVSC/CBE/market entries from knowledge/seed_data.py.

Usage (operator-run; NOT imported by bridge_api or any API route):
    python core_engine/knowledge/qdrant_seeder.py

Environment variables (see .env.example):
    QDRANT_URL        : full URL e.g. "http://localhost:6333".
                        If blank → local embedded path mode (no Docker required).
    QDRANT_COLLECTION : collection name (default: egypt_estate)
    EMBED_MODEL       : SentenceTransformer model (default: intfloat/multilingual-e5-large)

Design rules
------------
- No scraping, no internet ingestion, no scheduling, no automatic execution.
- Does NOT import bridge_api, valuation_logic, or any API route module.
- Collection already exists → skips creation (idempotent).
- Points already present → upsert overwrites in place (idempotent).
- sentence_transformers unavailable → deterministic fallback for tests.
- Stores source, seeded_at, seeder_version in every point payload.
"""

from __future__ import annotations

import hashlib
import math
import os
import sys
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------

_SEEDER_VERSION:    str = "1.0.0"
_DEFAULT_COLLECTION: str = "egypt_estate"
_DEFAULT_EMBED_MODEL: str = "intfloat/multilingual-e5-large"
_VECTOR_SIZE:        int = 1024   # matches intfloat/multilingual-e5-large output dim

# Paths — qdrant_seeder.py lives in core_engine/knowledge/
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))   # core_engine/knowledge/
_CORE_DIR = os.path.dirname(_THIS_DIR)                    # core_engine/
_ROOT_DIR = os.path.dirname(_CORE_DIR)                    # project root
_VDB_PATH  = os.path.join(_ROOT_DIR, "expert_smart_system", "vector_db")


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------

def _deterministic_embedding(text: str, size: int = _VECTOR_SIZE) -> List[float]:
    """
    Return a stable, L2-normalised float vector of length *size*.
    SHA-256-based — no model download, no external calls.
    Used as a fallback when sentence_transformers is unavailable.
    Identical input always produces identical output.
    """
    raw: List[float] = []
    seed = 0
    while len(raw) < size:
        digest = hashlib.sha256(f"{seed}:{text}".encode()).digest()
        raw.extend((b - 128) / 128.0 for b in digest)
        seed += 1
    raw = raw[:size]
    magnitude = math.sqrt(sum(x * x for x in raw)) or 1.0
    return [x / magnitude for x in raw]


def _get_embed_fn(model_name: Optional[str] = None) -> Callable[[List[str]], List[List[float]]]:
    """
    Return an embedding function that maps a list of texts to 1024-dim vectors.
    Tries SentenceTransformer first; falls back to _deterministic_embedding.
    """
    name = model_name or os.getenv("EMBED_MODEL", _DEFAULT_EMBED_MODEL)
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        _model = SentenceTransformer(name)

        def _st_embed(texts: List[str]) -> List[List[float]]:
            vecs = _model.encode(texts, normalize_embeddings=True)
            return [list(v) for v in vecs]

        return _st_embed
    except Exception:
        return lambda texts: [_deterministic_embedding(t) for t in texts]


# ---------------------------------------------------------------------------
# Qdrant client factory
# ---------------------------------------------------------------------------

def _make_client() -> Optional[Any]:
    """
    Create a QdrantClient using the configured mode.

    Priority:
      1. QDRANT_URL set  → HTTP mode
      2. Otherwise       → local embedded path mode (no server required)

    Returns None if qdrant_client is not installed.
    """
    try:
        from qdrant_client import QdrantClient  # type: ignore

        url = os.getenv("QDRANT_URL", "").strip()
        if url:
            return QdrantClient(url=url)

        # Local embedded — creates the directory if it does not exist
        return QdrantClient(path=_VDB_PATH)

    except Exception:
        return None


# ---------------------------------------------------------------------------
# Qdrant health / availability
# ---------------------------------------------------------------------------

def is_qdrant_available(client: Optional[Any] = None) -> bool:
    """Return True if a Qdrant client can be created and responds."""
    try:
        c = client or _make_client()
        if c is None:
            return False
        c.get_collections()
        return True
    except Exception:
        return False


def qdrant_health_check(client: Optional[Any] = None) -> Dict[str, Any]:
    """Return a structured health status dict for the Qdrant store."""
    collection = os.getenv("QDRANT_COLLECTION", _DEFAULT_COLLECTION)
    try:
        c = client or _make_client()
        if c is None:
            return {
                "available":  False,
                "collection": collection,
                "reason":     "qdrant_client_import_failed",
            }
        resp = c.get_collections()
        names = [col.name for col in resp.collections]
        return {
            "available":   True,
            "collection":  collection,
            "collections": names,
            "reason":      "ok",
        }
    except Exception as exc:
        return {
            "available":  False,
            "collection": collection,
            "reason":     str(exc),
        }


# ---------------------------------------------------------------------------
# Collection management
# ---------------------------------------------------------------------------

def ensure_collection(
    client:          Any,
    collection_name: str = _DEFAULT_COLLECTION,
) -> bool:
    """
    Ensure *collection_name* exists with the correct 1024-dim cosine configuration.
    Creates it if absent.  Returns True on success, False on any error.
    """
    try:
        try:
            client.get_collection(collection_name)
            return True   # already exists — nothing to do
        except Exception:
            pass          # not found — proceed to create

        try:
            from qdrant_client.models import Distance, VectorParams  # type: ignore
            vectors_config = VectorParams(size=_VECTOR_SIZE, distance=Distance.COSINE)
        except ImportError:
            vectors_config = None   # mock/fallback client doesn't need this

        client.create_collection(
            collection_name=collection_name,
            vectors_config=vectors_config,
        )
        return True

    except Exception:
        return False


# ---------------------------------------------------------------------------
# Stable point ID
# ---------------------------------------------------------------------------

def _stable_point_id(entry_id: str) -> int:
    """Map a string entry id to a stable unsigned int63 for Qdrant."""
    return int(hashlib.md5(entry_id.encode()).hexdigest(), 16) % (2 ** 63)


# ---------------------------------------------------------------------------
# Main seeder
# ---------------------------------------------------------------------------

def seed_knowledge_base(
    client:    Optional[Any]                          = None,
    embed_fn:  Optional[Callable[[List[str]], List[List[float]]]] = None,
    collection: Optional[str]                         = None,
) -> Dict[str, Any]:
    """
    Load all seed entries from knowledge/seed_data.py, embed, and upsert to Qdrant.

    Parameters
    ----------
    client     : live QdrantClient; if None, _make_client() is called.
    embed_fn   : embedding function override (useful for testing without downloading
                 the model); if None, _get_embed_fn() is used.
    collection : Qdrant collection override (default: QDRANT_COLLECTION env or egypt_estate).

    Returns
    -------
    dict:
      seeded     : bool — True when all points were upserted successfully.
      count      : int  — number of entries seeded.
      collection : str  — target collection name.
      seeded_at  : str  — ISO timestamp of this seeding run.
      reason     : "ok" | "client_unavailable" | "collection_failed" | "exception:<msg>"
    """
    collection_name = collection or os.getenv("QDRANT_COLLECTION", _DEFAULT_COLLECTION)
    seeded_at = datetime.now(timezone.utc).isoformat()

    _base: Dict[str, Any] = {
        "seeded":     False,
        "count":      0,
        "collection": collection_name,
        "seeded_at":  seeded_at,
    }

    # -- Load seed entries ----------------------------------------------------
    try:
        try:
            from .seed_data import get_seed_entries  # package import
        except ImportError:
            from core_engine.knowledge.seed_data import get_seed_entries  # script mode

        entries = get_seed_entries()
    except Exception as exc:
        return {**_base, "reason": f"seed_data_load_failed:{exc}"}

    # -- Acquire client -------------------------------------------------------
    c = client or _make_client()
    if c is None:
        return {**_base, "reason": "client_unavailable"}

    # -- Ensure collection exists ---------------------------------------------
    if not ensure_collection(c, collection_name):
        return {**_base, "reason": "collection_failed"}

    # -- Embed ----------------------------------------------------------------
    try:
        fn = embed_fn or _get_embed_fn()
        texts  = [entry.content for entry in entries]
        vectors = fn(texts)
    except Exception as exc:
        return {**_base, "reason": f"embedding_failed:{exc}"}

    # -- Build points and upsert ----------------------------------------------
    try:
        try:
            from qdrant_client.models import PointStruct  # type: ignore
        except ImportError:
            class PointStruct:  # type: ignore[no-redef]
                """Minimal fallback used when qdrant_client is unavailable (e.g. unit tests)."""
                def __init__(self, id, vector, payload):  # noqa: A002
                    self.id = id
                    self.vector = vector
                    self.payload = payload

        points = []
        for entry, vector in zip(entries, vectors):
            payload: Dict[str, Any] = {
                "id":             entry.id,
                "title":          entry.title,
                "category":       entry.category.value if hasattr(entry.category, "value") else str(entry.category),
                "content":        entry.content,
                "language":       entry.language.value if hasattr(entry.language, "value") else str(entry.language),
                "tags":           list(entry.tags),
                "source":         entry.source,
                "version":        entry.version,
                "seeded_at":      seeded_at,
                "seeder_version": _SEEDER_VERSION,
            }
            points.append(PointStruct(
                id=     _stable_point_id(entry.id),
                vector= list(vector),
                payload=payload,
            ))

        c.upsert(collection_name=collection_name, points=points)
        return {**_base, "seeded": True, "count": len(points), "reason": "ok"}

    except Exception as exc:
        return {**_base, "reason": f"exception:{exc}"}


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"[qdrant_seeder] version {_SEEDER_VERSION}")
    print(f"[qdrant_seeder] collection: {os.getenv('QDRANT_COLLECTION', _DEFAULT_COLLECTION)}")
    print(f"[qdrant_seeder] embed model: {os.getenv('EMBED_MODEL', _DEFAULT_EMBED_MODEL)}")
    print(f"[qdrant_seeder] Qdrant path (local mode): {_VDB_PATH}")
    print()

    health = qdrant_health_check()
    if not health["available"]:
        print(f"[qdrant_seeder] Qdrant not available: {health['reason']}")
        sys.exit(1)

    print(f"[qdrant_seeder] Qdrant available ✓  existing collections: {health.get('collections', [])}")
    print("[qdrant_seeder] Seeding knowledge base …")

    result = seed_knowledge_base()
    if result["seeded"]:
        print(f"[qdrant_seeder] Done. {result['count']} entries seeded into '{result['collection']}' ✓")
    else:
        print(f"[qdrant_seeder] Seeding failed: {result['reason']}")
        sys.exit(1)
