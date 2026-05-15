"""
rate_limiter.py — PH.3 Sliding-Window Rate Limiter

Thread-safe, in-memory rate limiter using a sliding window algorithm.

Classes:
    RateLimitResult  — outcome of a single rate-limit check
    RateLimiter      — check / consume / reset rate limits per key
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional


# ---------------------------------------------------------------------------
# RateLimitResult
# ---------------------------------------------------------------------------

@dataclass
class RateLimitResult:
    """Outcome of a rate-limit check."""

    allowed: bool
    key: str
    limit: int          # max requests allowed in the window
    window_seconds: int
    current_count: int  # requests in the current window (after this one)
    retry_after: float  # seconds until the oldest request expires (0 if allowed)

    def __bool__(self) -> bool:
        return self.allowed

    def to_dict(self) -> Dict:
        return {
            'allowed': self.allowed,
            'key': self.key,
            'limit': self.limit,
            'window_seconds': self.window_seconds,
            'current_count': self.current_count,
            'retry_after': round(self.retry_after, 2),
        }


# ---------------------------------------------------------------------------
# RateLimiter
# ---------------------------------------------------------------------------

class RateLimiter:
    """
    Sliding-window rate limiter.

    Parameters
    ----------
    limit          : max allowed requests per window per key
    window_seconds : length of the sliding window in seconds
    """

    def __init__(self, limit: int = 60, window_seconds: int = 60) -> None:
        if limit < 1:
            raise ValueError('limit must be >= 1')
        if window_seconds < 1:
            raise ValueError('window_seconds must be >= 1')

        self._limit = limit
        self._window = window_seconds
        self._lock = threading.Lock()
        # key -> deque of request timestamps (float)
        self._windows: Dict[str, Deque[float]] = {}

    # -- Core check -----------------------------------------------------------

    def check(self, key: str, consume: bool = True) -> RateLimitResult:
        """
        Check (and optionally record) a request for *key*.

        Parameters
        ----------
        key     : identifies the caller (IP, user ID, API key, …)
        consume : if True (default), record this request in the window

        Returns
        -------
        RateLimitResult with .allowed=True if under the limit.
        """
        now = time.monotonic()
        cutoff = now - self._window

        with self._lock:
            window = self._windows.setdefault(key, deque())

            # Evict expired timestamps
            while window and window[0] <= cutoff:
                window.popleft()

            current = len(window)

            if current >= self._limit:
                # Oldest request determines when a slot opens
                oldest = window[0] if window else now
                retry_after = max(0.0, oldest - cutoff)
                return RateLimitResult(
                    allowed=False,
                    key=key,
                    limit=self._limit,
                    window_seconds=self._window,
                    current_count=current,
                    retry_after=retry_after,
                )

            if consume:
                window.append(now)
                current += 1

            return RateLimitResult(
                allowed=True,
                key=key,
                limit=self._limit,
                window_seconds=self._window,
                current_count=current,
                retry_after=0.0,
            )

    # -- Convenience wrappers -------------------------------------------------

    def is_allowed(self, key: str) -> bool:
        """Return True and consume a token if under the limit."""
        return self.check(key, consume=True).allowed

    def peek(self, key: str) -> RateLimitResult:
        """Check without consuming a token."""
        return self.check(key, consume=False)

    # -- Management -----------------------------------------------------------

    def reset(self, key: str) -> None:
        """Clear all recorded requests for *key*."""
        with self._lock:
            self._windows.pop(key, None)

    def reset_all(self) -> None:
        """Clear recorded requests for ALL keys."""
        with self._lock:
            self._windows.clear()

    def get_count(self, key: str) -> int:
        """Return the number of requests in the current window for *key*."""
        now = time.monotonic()
        cutoff = now - self._window
        with self._lock:
            window = self._windows.get(key, deque())
            return sum(1 for ts in window if ts > cutoff)

    @property
    def limit(self) -> int:
        return self._limit

    @property
    def window_seconds(self) -> int:
        return self._window

    def tracked_keys(self) -> int:
        """Return number of keys currently tracked (for monitoring)."""
        with self._lock:
            return len(self._windows)
