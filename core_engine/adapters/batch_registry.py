"""
batch_registry.py — In-Memory Batch Status Store (Phase 12.3)

Thread-safe singleton registry: completed batch reports are stored keyed
by batch_id so callers can retrieve status after the POST request returns.

Max 500 entries (FIFO eviction). Designed for single-process use (Waitress
or Flask dev server). Does not survive server restarts — intentional for now.

Usage:
    from adapters.batch_registry import registry
    registry.register(batch_id, completion_report)
    report = registry.get(batch_id)        # None if not found
    recent = registry.list_recent(limit=20)
"""
from __future__ import annotations

import threading
from datetime import datetime
from typing import Dict, List, Optional


class BatchRegistry:
    """Thread-safe in-memory store for completed batch reports."""

    def __init__(self, max_entries: int = 500) -> None:
        self._store:  Dict[str, dict] = {}
        self._order:  List[str]       = []   # insertion order, oldest first
        self._lock    = threading.Lock()
        self.max_entries = max_entries

    # ── Write ─────────────────────────────────────────────────────────────────

    def register(self, batch_id: str, completion_report: dict) -> None:
        """Store a completion report; evict oldest if over max_entries."""
        with self._lock:
            entry = {
                **completion_report,
                "registered_at": datetime.now().isoformat(),
            }
            if batch_id not in self._store:
                self._order.append(batch_id)
            self._store[batch_id] = entry

            while len(self._order) > self.max_entries:
                oldest = self._order.pop(0)
                self._store.pop(oldest, None)

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(self, batch_id: str) -> Optional[dict]:
        """Return stored report for batch_id, or None if not found."""
        with self._lock:
            return self._store.get(batch_id)

    def list_recent(self, limit: int = 20) -> List[dict]:
        """Return up to `limit` most recently registered reports (newest first)."""
        with self._lock:
            recent_ids = self._order[-limit:][::-1]
            return [self._store[bid] for bid in recent_ids if bid in self._store]

    # ── Introspection ─────────────────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self._store)

    def clear(self) -> None:
        """Remove all entries — intended for tests only."""
        with self._lock:
            self._store.clear()
            self._order.clear()


# Module-level singleton — imported by bridge_api and tests
registry = BatchRegistry()
