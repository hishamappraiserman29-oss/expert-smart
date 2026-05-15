"""
performance_optimizer.py — Performance Optimizer (Phase 38)

Response caching with TTL, gzip compression, cache statistics.
"""

from __future__ import annotations

import gzip
import json
import logging
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class PerformanceOptimizer:
    """TTL-based response cache and gzip compression."""

    _DEFAULT_TTL: Dict[str, int] = {
        "search": 300,
        "analytics": 600,
        "market_data": 3_600,
        "standards": 86_400,
        "knowledge": 86_400,
    }

    def __init__(self) -> None:
        self.response_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl: Dict[str, int] = dict(self._DEFAULT_TTL)
        self._lock = threading.Lock()
        logger.info("Performance Optimizer initialized")

    def get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            entry = self.response_cache.get(cache_key)
        if entry is None:
            return None
        if entry["expires_at"] < datetime.utcnow():
            with self._lock:
                self.response_cache.pop(cache_key, None)
            return None
        logger.debug("Cache hit: %s", cache_key)
        return entry["data"]

    def cache_response(
        self, cache_key: str, response_data: Dict[str, Any], endpoint: str
    ) -> None:
        ttl = self.cache_ttl.get(endpoint, 300)
        entry = {
            "data": response_data,
            "expires_at": datetime.utcnow() + timedelta(seconds=ttl),
            "created_at": datetime.utcnow(),
        }
        with self._lock:
            self.response_cache[cache_key] = entry
        logger.info("Response cached: %s (TTL=%ds)", cache_key, ttl)

    def compress_response(self, response_data: Dict[str, Any]) -> bytes:
        json_bytes = json.dumps(response_data).encode()
        compressed = gzip.compress(json_bytes)
        ratio = len(compressed) / len(json_bytes)
        logger.info("Response compressed (ratio=%.1f%%)", ratio * 100)
        return compressed

    def invalidate(self, cache_key: str) -> bool:
        with self._lock:
            existed = cache_key in self.response_cache
            self.response_cache.pop(cache_key, None)
        return existed

    def get_cache_statistics(self) -> Dict[str, Any]:
        now = datetime.utcnow()
        with self._lock:
            total = len(self.response_cache)
            expired = sum(
                1 for e in self.response_cache.values() if e["expires_at"] < now
            )
        return {
            "total_cached": total,
            "expired": expired,
            "valid": total - expired,
            "configured_endpoints": len(self.cache_ttl),
        }

    def count(self) -> int:
        with self._lock:
            return len(self.response_cache)


performance_optimizer = PerformanceOptimizer()
