"""
cache.py — PH.4 Thread-Safe TTL + LRU Cache

In-memory cache with:
  - Per-entry TTL (time-to-live) — entries expire automatically on access
  - LRU eviction — when capacity is reached, the least-recently-used entry
    is removed to make room
  - Thread-safe — all operations protected by a single RLock
  - Hit/miss statistics

Classes:
    CacheEntry         — value wrapper with expiry timestamp
    TTLCache           — the cache itself
    cached()           — decorator factory for memoising function results
"""

from __future__ import annotations

import functools
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, Hashable, Optional, Tuple, TypeVar

V = TypeVar("V")


# ---------------------------------------------------------------------------
# CacheEntry
# ---------------------------------------------------------------------------

@dataclass
class CacheEntry:
    """Value + expiry metadata for one cache slot."""

    value: Any
    expires_at: Optional[float]   # monotonic clock; None = never expires

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.monotonic() >= self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        remaining = None
        if self.expires_at is not None:
            remaining = max(0.0, round(self.expires_at - time.monotonic(), 3))
        return {"expires_in_seconds": remaining, "expired": self.is_expired}


# ---------------------------------------------------------------------------
# TTLCache
# ---------------------------------------------------------------------------

class TTLCache:
    """
    Thread-safe, size-bounded cache with per-entry TTL and LRU eviction.

    Parameters
    ----------
    max_size    : maximum number of entries (default 256)
    default_ttl : default time-to-live in seconds; None = no expiry
    """

    def __init__(self, max_size: int = 256, default_ttl: Optional[float] = None) -> None:
        if max_size < 1:
            raise ValueError("max_size must be >= 1")
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = threading.RLock()
        # OrderedDict preserves insertion/access order for LRU eviction
        self._store: OrderedDict[Hashable, CacheEntry] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    # -- Core operations ------------------------------------------------------

    def get(self, key: Hashable) -> Optional[Any]:
        """
        Return the cached value for *key*, or None on miss / expiry.
        Moves the entry to the end of the LRU order on hit.
        """
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.is_expired:
                del self._store[key]
                self._misses += 1
                return None
            # Promote to most-recently-used
            self._store.move_to_end(key)
            self._hits += 1
            return entry.value

    def set(self, key: Hashable, value: Any, ttl: Optional[float] = None) -> None:
        """
        Store *value* under *key*.

        Parameters
        ----------
        ttl : override the cache-level default TTL for this entry (seconds).
              Pass 0 to make the entry never expire (overrides default_ttl).
              Pass None to use the cache-level default_ttl.
        """
        effective_ttl = ttl if ttl is not None else self._default_ttl
        if effective_ttl == 0:
            expires_at = None
        elif effective_ttl is not None:
            expires_at = time.monotonic() + effective_ttl
        else:
            expires_at = None

        entry = CacheEntry(value=value, expires_at=expires_at)

        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = entry

            # Evict LRU if over capacity
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)
                self._evictions += 1

    def delete(self, key: Hashable) -> bool:
        """Remove *key* from the cache. Returns True if it existed."""
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def clear(self) -> None:
        """Remove all entries."""
        with self._lock:
            self._store.clear()

    # -- Introspection --------------------------------------------------------

    def __contains__(self, key: Hashable) -> bool:
        """Support `key in cache` — also evicts expired entries."""
        return self.get(key) is not None

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)

    @property
    def size(self) -> int:
        return len(self)

    @property
    def max_size(self) -> int:
        return self._max_size

    def stats(self) -> Dict[str, Any]:
        """Return hit/miss/eviction counters and current size."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = round(self._hits / total * 100, 1) if total else 0.0
            return {
                "size": len(self._store),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_pct": hit_rate,
                "evictions": self._evictions,
            }

    def reset_stats(self) -> None:
        with self._lock:
            self._hits = 0
            self._misses = 0
            self._evictions = 0

    def keys(self) -> list:
        with self._lock:
            return list(self._store.keys())


# ---------------------------------------------------------------------------
# @cached decorator
# ---------------------------------------------------------------------------

def cached(
    cache: TTLCache,
    key_fn: Optional[Callable[..., Hashable]] = None,
    ttl: Optional[float] = None,
) -> Callable:
    """
    Decorator that memoises a function's return value in *cache*.

    Parameters
    ----------
    cache  : the TTLCache instance to use
    key_fn : optional function(*args, **kwargs) → Hashable cache key.
             If None, uses (function.__qualname__, args, frozenset(kwargs.items()))
    ttl    : per-call TTL override (seconds); None = cache default

    Example
    -------
    valuation_cache = TTLCache(max_size=512, default_ttl=300)

    @cached(valuation_cache, ttl=60)
    def get_market_value(property_id: str) -> dict:
        ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if key_fn is not None:
                key: Hashable = key_fn(*args, **kwargs)
            else:
                try:
                    key = (func.__qualname__, args, frozenset(kwargs.items()))
                except TypeError:
                    # Unhashable args — skip caching
                    return func(*args, **kwargs)

            hit = cache.get(key)
            if hit is not None:
                return hit

            result = func(*args, **kwargs)
            cache.set(key, result, ttl=ttl)
            return result

        wrapper.cache = cache       # type: ignore[attr-defined]
        wrapper.invalidate = lambda *a, **kw: cache.delete(  # type: ignore[attr-defined]
            key_fn(*a, **kw) if key_fn else (func.__qualname__, a, frozenset(kw.items()))
        )
        return wrapper

    return decorator
