"""
Phase 18 — Qdrant Seeder tests.

QS01–QS20   qdrant_seeder.py

Safety scope
------------
• Only tests core_engine/knowledge/qdrant_seeder.py.
• Does NOT touch bridge_api, valuation_logic, or any /api/* route.
• Unit tests require NO Docker / NO running Qdrant server.
• All Qdrant client interactions are handled via an in-process mock.
• Embedding always uses _deterministic_embedding (no model download).

Key tests
---------
QS12 — seed_knowledge_base loads exactly 13 entries from seed_data
QS13 — every upserted point payload contains id, source, seeded_at, seeder_version
QS17 — calling seed_knowledge_base twice with same mock does not raise
QS19 — .env.example declares QDRANT_URL, QDRANT_COLLECTION, EMBED_MODEL
QS20 — seeder does not import bridge_api or valuation_logic
"""

from __future__ import annotations

import inspect
import math
import pathlib
import re

import pytest


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

class _MockClient:
    """Minimal in-process Qdrant client mock — no server, no Docker required."""

    def __init__(self, has_collection: bool = False) -> None:
        self._has_collection = has_collection
        self.upsert_calls: list = []
        self.create_calls: int = 0

    def get_collection(self, name: str):
        if not self._has_collection:
            raise Exception(f"Collection '{name}' not found")
        return True

    def create_collection(self, collection_name: str, vectors_config=None) -> None:
        self._has_collection = True
        self.create_calls += 1

    def upsert(self, collection_name: str, points) -> None:
        self.upsert_calls.extend(points)

    def get_collections(self):
        class _Names:
            collections = []
        return _Names()


@pytest.fixture
def mock_client() -> _MockClient:
    return _MockClient()


@pytest.fixture
def mock_embed():
    """Deterministic embed function — no model download, no internet."""
    from core_engine.knowledge.qdrant_seeder import _deterministic_embedding
    return lambda texts: [_deterministic_embedding(t) for t in texts]


# ---------------------------------------------------------------------------
# QS01–QS05  import · public API surface · module constants
# ---------------------------------------------------------------------------

def test_QS01_module_imports_without_error():
    """QS01: qdrant_seeder imports cleanly and seed_knowledge_base is callable."""
    from core_engine.knowledge.qdrant_seeder import seed_knowledge_base
    assert callable(seed_knowledge_base)


def test_QS02_public_api_surface():
    """QS02: All expected public functions are present and callable."""
    import core_engine.knowledge.qdrant_seeder as mod
    expected = [
        "ensure_collection",
        "is_qdrant_available",
        "qdrant_health_check",
        "seed_knowledge_base",
        "_deterministic_embedding",
        "_make_client",
        "_get_embed_fn",
    ]
    for name in expected:
        assert hasattr(mod, name), f"Missing symbol: {name}"
        assert callable(getattr(mod, name)), f"Not callable: {name}"


def test_QS03_seeder_version_is_string():
    """QS03: _SEEDER_VERSION is a non-empty string."""
    from core_engine.knowledge.qdrant_seeder import _SEEDER_VERSION
    assert isinstance(_SEEDER_VERSION, str) and _SEEDER_VERSION


def test_QS04_default_collection_name():
    """QS04: _DEFAULT_COLLECTION is 'egypt_estate'."""
    from core_engine.knowledge.qdrant_seeder import _DEFAULT_COLLECTION
    assert _DEFAULT_COLLECTION == "egypt_estate"


def test_QS05_vector_size_and_model():
    """QS05: _VECTOR_SIZE is 1024 and _DEFAULT_EMBED_MODEL is the expected model."""
    from core_engine.knowledge.qdrant_seeder import _VECTOR_SIZE, _DEFAULT_EMBED_MODEL
    assert _VECTOR_SIZE == 1024
    assert _DEFAULT_EMBED_MODEL == "intfloat/multilingual-e5-large"


# ---------------------------------------------------------------------------
# QS06–QS08  ensure_collection (mocked client — no Docker)
# ---------------------------------------------------------------------------

def test_QS06_ensure_collection_returns_true_when_exists():
    """QS06: ensure_collection returns True when collection already exists."""
    from core_engine.knowledge.qdrant_seeder import ensure_collection
    client = _MockClient(has_collection=True)
    result = ensure_collection(client, "egypt_estate")
    assert result is True
    assert client.create_calls == 0   # no create needed


def test_QS07_ensure_collection_creates_when_absent():
    """QS07: ensure_collection creates the collection when it does not exist."""
    from core_engine.knowledge.qdrant_seeder import ensure_collection
    client = _MockClient(has_collection=False)
    result = ensure_collection(client, "egypt_estate")
    assert result is True
    assert client.create_calls == 1   # create was called once


def test_QS08_ensure_collection_returns_false_on_error():
    """QS08: ensure_collection returns False when both get and create fail."""
    from core_engine.knowledge.qdrant_seeder import ensure_collection

    class _BrokenClient:
        def get_collection(self, name):
            raise Exception("unreachable")
        def create_collection(self, **kw):
            raise Exception("unreachable")

    result = ensure_collection(_BrokenClient(), "egypt_estate")
    assert result is False


# ---------------------------------------------------------------------------
# QS09–QS11  _deterministic_embedding
# ---------------------------------------------------------------------------

def test_QS09_deterministic_embedding_correct_size():
    """QS09: _deterministic_embedding returns a vector of exactly 1024 floats."""
    from core_engine.knowledge.qdrant_seeder import _deterministic_embedding, _VECTOR_SIZE
    vec = _deterministic_embedding("EGVS residential Cairo", size=_VECTOR_SIZE)
    assert len(vec) == _VECTOR_SIZE
    assert all(isinstance(x, float) for x in vec)


def test_QS10_deterministic_embedding_is_unit_norm():
    """QS10: _deterministic_embedding returns an L2-normalised vector (|v| ≈ 1)."""
    from core_engine.knowledge.qdrant_seeder import _deterministic_embedding
    vec = _deterministic_embedding("CBE Basel III LTV requirements", size=1024)
    magnitude = math.sqrt(sum(x * x for x in vec))
    assert abs(magnitude - 1.0) < 1e-6, f"Expected unit norm, got {magnitude}"


def test_QS11_deterministic_embedding_is_stable():
    """QS11: Same text always produces the same vector (deterministic)."""
    from core_engine.knowledge.qdrant_seeder import _deterministic_embedding
    text = "IVSC fair value hierarchy level 2"
    v1 = _deterministic_embedding(text)
    v2 = _deterministic_embedding(text)
    assert v1 == v2


# ---------------------------------------------------------------------------
# QS12–QS16  seed_knowledge_base (mocked client + deterministic embed)
# ---------------------------------------------------------------------------

def test_QS12_seed_loads_13_entries(mock_client, mock_embed):
    """QS12: seed_knowledge_base upserts exactly 13 points (all seed_data entries)."""
    from core_engine.knowledge.qdrant_seeder import seed_knowledge_base
    result = seed_knowledge_base(client=mock_client, embed_fn=mock_embed)
    assert result["seeded"] is True
    assert result["count"] == 13
    assert len(mock_client.upsert_calls) == 13


def test_QS13_payload_has_required_fields(mock_client, mock_embed):
    """QS13: Every upserted point payload contains id, source, seeded_at, seeder_version."""
    from core_engine.knowledge.qdrant_seeder import seed_knowledge_base
    seed_knowledge_base(client=mock_client, embed_fn=mock_embed)
    assert len(mock_client.upsert_calls) == 13
    for point in mock_client.upsert_calls:
        payload = point.payload
        for field in ("id", "source", "seeded_at", "seeder_version"):
            assert field in payload, f"Missing field '{field}' in payload"
            assert payload[field], f"Empty value for '{field}'"


def test_QS14_seeded_at_is_iso_timestamp(mock_client, mock_embed):
    """QS14: seeded_at in every payload is a valid ISO 8601 timestamp string."""
    from core_engine.knowledge.qdrant_seeder import seed_knowledge_base
    from datetime import datetime
    seed_knowledge_base(client=mock_client, embed_fn=mock_embed)
    for point in mock_client.upsert_calls:
        seeded_at = point.payload["seeded_at"]
        assert isinstance(seeded_at, str)
        # Must parse without raising
        datetime.fromisoformat(seeded_at.replace("Z", "+00:00"))


def test_QS15_seeder_version_matches_constant(mock_client, mock_embed):
    """QS15: seeder_version in payload matches _SEEDER_VERSION module constant."""
    from core_engine.knowledge.qdrant_seeder import _SEEDER_VERSION, seed_knowledge_base
    seed_knowledge_base(client=mock_client, embed_fn=mock_embed)
    for point in mock_client.upsert_calls:
        assert point.payload["seeder_version"] == _SEEDER_VERSION


def test_QS16_seed_result_has_required_keys(mock_client, mock_embed):
    """QS16: seed_knowledge_base result dict contains seeded, count, collection, reason."""
    from core_engine.knowledge.qdrant_seeder import seed_knowledge_base
    result = seed_knowledge_base(client=mock_client, embed_fn=mock_embed)
    for key in ("seeded", "count", "collection", "reason", "seeded_at"):
        assert key in result, f"Missing key '{key}' in result"
    assert result["reason"] == "ok"
    assert result["collection"] == "egypt_estate"


# ---------------------------------------------------------------------------
# QS17–QS18  idempotency · health check
# ---------------------------------------------------------------------------

def test_QS17_seed_twice_is_idempotent(mock_embed):
    """QS17: Calling seed_knowledge_base twice with the same client never raises."""
    from core_engine.knowledge.qdrant_seeder import seed_knowledge_base
    client = _MockClient()
    r1 = seed_knowledge_base(client=client, embed_fn=mock_embed)
    r2 = seed_knowledge_base(client=client, embed_fn=mock_embed)
    assert r1["seeded"] is True
    assert r2["seeded"] is True
    # Both runs succeed; second upsert simply overwrites (26 total calls to upsert)
    assert len(client.upsert_calls) == 26


def test_QS18_health_check_structure():
    """QS18: qdrant_health_check returns a dict with 'available' and 'collection' keys."""
    from core_engine.knowledge.qdrant_seeder import qdrant_health_check

    health = qdrant_health_check(client=_MockClient(has_collection=True))
    assert isinstance(health, dict)
    assert "available" in health
    assert "collection" in health


# ---------------------------------------------------------------------------
# QS19–QS20  env.example · no forbidden imports
# ---------------------------------------------------------------------------

def test_QS19_env_example_has_approved_variables():
    """QS19: .env.example declares QDRANT_URL, QDRANT_COLLECTION, EMBED_MODEL."""
    env_example = pathlib.Path(__file__).parent.parent.parent / ".env.example"
    assert env_example.exists(), ".env.example not found"
    content = env_example.read_text(encoding="utf-8")
    for var in ("QDRANT_URL", "QDRANT_COLLECTION", "EMBED_MODEL"):
        assert var in content, f".env.example missing variable: {var}"


def test_QS20_seeder_does_not_import_bridge_api_or_valuation_logic():
    """QS20: qdrant_seeder.py contains no import of bridge_api or valuation_logic."""
    import core_engine.knowledge.qdrant_seeder as mod
    src = inspect.getsource(mod)
    assert not re.search(
        r'^\s*(import|from)\s+.*bridge_api', src, re.MULTILINE
    ), "qdrant_seeder imports bridge_api"
    assert not re.search(
        r'^\s*(import|from)\s+.*valuation_logic', src, re.MULTILINE
    ), "qdrant_seeder imports valuation_logic"
