"""
performance/ — PH.4 Performance & Scaling package.

Modules:
    cache      — thread-safe TTL LRU cache + @cached decorator
    paginator  — generic pagination for list endpoints
    profiler   — timing decorator, context manager, stats aggregator
"""

from .cache import TTLCache, CacheEntry, cached
from .paginator import Paginator, PageRequest, PageResult
from .profiler import PerformanceProfiler, TimingRecord, timed, profiler

__all__ = [
    "TTLCache",
    "CacheEntry",
    "cached",
    "Paginator",
    "PageRequest",
    "PageResult",
    "PerformanceProfiler",
    "TimingRecord",
    "timed",
    "profiler",
]
