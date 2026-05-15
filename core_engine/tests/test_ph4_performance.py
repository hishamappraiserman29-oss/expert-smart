"""
test_ph4_performance.py — PH.4 Performance & Scaling Tests

Covers:
  A. TTLCache     — set/get, TTL expiry, LRU eviction, thread-safety,
                    stats, @cached decorator
  B. Paginator    — basic pagination, sort, edge cases, PageRequest.from_dict
  C. Profiler     — @timed, context manager, stats, reset, thread-safety
"""

from __future__ import annotations

import sys
import time
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from performance.cache import TTLCache, CacheEntry, cached
from performance.paginator import Paginator, PageRequest, PageResult
from performance.profiler import PerformanceProfiler, TimingRecord, timed, profiler


# ===========================================================================
# A. TTLCache
# ===========================================================================

class TestTTLCache:

    def test_A01_set_and_get(self):
        c = TTLCache(max_size=10)
        c.set("k1", "hello")
        assert c.get("k1") == "hello"

    def test_A02_miss_returns_none(self):
        c = TTLCache()
        assert c.get("nonexistent") is None

    def test_A03_ttl_expiry(self):
        c = TTLCache(default_ttl=0.05)   # 50 ms
        c.set("short", 42)
        assert c.get("short") == 42
        time.sleep(0.08)
        assert c.get("short") is None    # expired

    def test_A04_no_ttl_persists(self):
        c = TTLCache(default_ttl=0.01)   # 10 ms default
        c.set("permanent", 99, ttl=0)    # ttl=0 → no expiry
        time.sleep(0.02)
        assert c.get("permanent") == 99  # still alive

    def test_A05_lru_eviction(self):
        c = TTLCache(max_size=3)
        c.set("a", 1)
        c.set("b", 2)
        c.set("c", 3)
        c.get("a")           # promote a to MRU
        c.set("d", 4)        # should evict b (LRU after a was promoted)
        assert c.get("a") == 1
        assert c.get("b") is None   # evicted
        assert c.get("c") == 3
        assert c.get("d") == 4

    def test_A06_delete(self):
        c = TTLCache()
        c.set("x", 7)
        assert c.delete("x") is True
        assert c.get("x") is None
        assert c.delete("x") is False

    def test_A07_clear(self):
        c = TTLCache()
        c.set("a", 1)
        c.set("b", 2)
        c.clear()
        assert len(c) == 0

    def test_A08_contains(self):
        c = TTLCache(default_ttl=0.05)
        c.set("yes", True)
        assert "yes" in c
        time.sleep(0.07)
        assert "yes" not in c   # expired

    def test_A09_stats(self):
        c = TTLCache(max_size=5)
        c.set("k", "v")
        c.get("k")         # hit
        c.get("missing")   # miss
        s = c.stats()
        assert s["hits"] == 1
        assert s["misses"] == 1
        assert s["size"] == 1

    def test_A10_cached_decorator(self):
        cache = TTLCache(max_size=50, default_ttl=10)
        call_count = [0]

        @cached(cache)
        def expensive(x: int) -> int:
            call_count[0] += 1
            return x * 2

        assert expensive(3) == 6
        assert expensive(3) == 6   # second call — from cache
        assert call_count[0] == 1  # underlying function called once

    def test_A11_thread_safety(self):
        c = TTLCache(max_size=100)
        errors = []

        def writer(n: int) -> None:
            try:
                for i in range(20):
                    c.set(f"{n}:{i}", n * i)
            except Exception as e:
                errors.append(e)

        def reader(n: int) -> None:
            try:
                for i in range(20):
                    c.get(f"{n}:{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(n,)) for n in range(5)]
        threads += [threading.Thread(target=reader, args=(n,)) for n in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []

    def test_A12_eviction_counter(self):
        c = TTLCache(max_size=2)
        c.set("a", 1)
        c.set("b", 2)
        c.set("c", 3)   # triggers eviction
        assert c.stats()["evictions"] >= 1


# ===========================================================================
# B. Paginator
# ===========================================================================

class TestPaginator:

    ITEMS = [{"id": i, "value": i * 10} for i in range(1, 26)]  # 25 items

    def test_B01_basic_pagination(self):
        r = Paginator.paginate(self.ITEMS, page=1, page_size=10)
        assert len(r.items) == 10
        assert r.total == 25
        assert r.total_pages == 3
        assert r.has_next is True
        assert r.has_prev is False

    def test_B02_last_page_partial(self):
        r = Paginator.paginate(self.ITEMS, page=3, page_size=10)
        assert len(r.items) == 5    # 25 - 20 = 5 remaining
        assert r.has_next is False
        assert r.has_prev is True

    def test_B03_empty_list(self):
        r = Paginator.paginate([], page=1, page_size=10)
        assert r.items == []
        assert r.total == 0
        assert r.total_pages == 1

    def test_B04_page_beyond_last_clamped(self):
        r = Paginator.paginate(self.ITEMS, page=99, page_size=10)
        assert r.page == 3          # clamped to last valid page
        assert len(r.items) == 5

    def test_B05_sort_ascending(self):
        items = [{"v": 3}, {"v": 1}, {"v": 2}]
        r = Paginator.paginate(items, page=1, page_size=10, sort_by="v", sort_dir="asc")
        assert [x["v"] for x in r.items] == [1, 2, 3]

    def test_B06_sort_descending(self):
        items = [{"v": 3}, {"v": 1}, {"v": 2}]
        r = Paginator.paginate(items, page=1, page_size=10, sort_by="v", sort_dir="desc")
        assert [x["v"] for x in r.items] == [3, 2, 1]

    def test_B07_page_request_from_dict(self):
        req = PageRequest.from_dict({"page": "2", "page_size": "5", "sort_by": "id", "sort_dir": "desc"})
        assert req.page == 2
        assert req.page_size == 5
        assert req.sort_by == "id"
        assert req.sort_dir == "desc"

    def test_B08_page_result_to_dict(self):
        r = Paginator.paginate(self.ITEMS, page=2, page_size=10)
        d = r.to_dict()
        assert "items" in d
        assert d["pagination"]["page"] == 2
        assert d["pagination"]["has_next"] is True
        assert d["pagination"]["has_prev"] is True

    def test_B09_from_dict_convenience(self):
        r = Paginator.from_dict(self.ITEMS, {"page": 1, "page_size": 5})
        assert len(r.items) == 5
        assert r.total == 25

    def test_B10_page_size_clamped(self):
        req = PageRequest(page=1, page_size=9999)
        assert req.page_size == 200   # clamped to MAX_PAGE_SIZE

    def test_B11_single_item(self):
        r = Paginator.paginate([{"x": 1}], page=1, page_size=10)
        assert r.total == 1
        assert r.total_pages == 1
        assert r.has_next is False
        assert r.has_prev is False


# ===========================================================================
# C. PerformanceProfiler
# ===========================================================================

class TestPerformanceProfiler:

    def setup_method(self):
        self.prof = PerformanceProfiler()

    def test_C01_timed_decorator(self):
        @self.prof.timed
        def slow() -> str:
            time.sleep(0.01)
            return "done"

        result = slow()
        assert result == "done"
        stats = self.prof.get_stats("TestPerformanceProfiler.setup_method.<locals>.slow"
                                    if False else None)
        # Check that something was recorded
        all_stats = self.prof.get_stats()
        assert len(all_stats) == 1
        rec = list(all_stats.values())[0]
        assert rec["calls"] == 1
        assert rec["total_ms"] >= 8   # ~10ms sleep

    def test_C02_context_manager(self):
        with self.prof.profile("db_query"):
            time.sleep(0.005)

        s = self.prof.get_stats("db_query")
        assert s["calls"] == 1
        assert s["total_ms"] >= 3

    def test_C03_multiple_calls_accumulate(self):
        @self.prof.timed
        def fast() -> None:
            pass

        for _ in range(5):
            fast()

        all_stats = self.prof.get_stats()
        rec = list(all_stats.values())[0]
        assert rec["calls"] == 5

    def test_C04_min_max_tracking(self):
        with self.prof.profile("work"):
            time.sleep(0.005)
        with self.prof.profile("work"):
            time.sleep(0.015)

        s = self.prof.get_stats("work")
        assert s["min_ms"] < s["max_ms"]
        assert s["calls"] == 2

    def test_C05_reset_single(self):
        self.prof.record("fn_a", 10.0)
        self.prof.record("fn_b", 20.0)
        self.prof.reset("fn_a")
        assert self.prof.get_stats("fn_a") == {}
        assert self.prof.get_stats("fn_b")["calls"] == 1

    def test_C06_reset_all(self):
        self.prof.record("x", 1.0)
        self.prof.record("y", 2.0)
        self.prof.reset()
        assert self.prof.get_stats() == {}

    def test_C07_error_in_timed_func(self):
        @self.prof.timed
        def bad() -> None:
            raise ValueError("oops")

        with pytest.raises(ValueError):
            bad()

        all_stats = self.prof.get_stats()
        rec = list(all_stats.values())[0]
        assert rec["calls"] == 1
        assert rec["errors"] == 1

    def test_C08_sorted_by(self):
        self.prof.record("slow", 100.0)
        self.prof.record("fast", 2.0)
        self.prof.record("medium", 30.0)
        rows = self.prof.sorted_by("total_ms")
        assert rows[0]["name"] == "slow"
        assert rows[-1]["name"] == "fast"

    def test_C09_thread_safety(self):
        errors = []

        def worker(n: int) -> None:
            try:
                for _ in range(50):
                    with self.prof.profile(f"section_{n % 3}"):
                        pass
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        total_calls = sum(r["calls"] for r in self.prof.get_stats().values())
        assert total_calls == 6 * 50

    def test_C10_summary(self):
        self.prof.record("a", 50.0)
        self.prof.record("b", 10.0)
        s = self.prof.summary()
        assert s["functions_tracked"] == 2
        assert s["total_calls"] == 2
        assert s["slowest_fn"] == "a"

    def test_C11_timing_record_to_dict(self):
        rec = TimingRecord(name="test_fn")
        rec.record(5.5)
        rec.record(3.3)
        d = rec.to_dict()
        assert d["calls"] == 2
        assert d["avg_ms"] == pytest.approx(4.4, abs=0.01)
        assert d["min_ms"] == pytest.approx(3.3, abs=0.01)

    def test_C12_module_level_timed_decorator(self):
        # Verify the module-level `timed` and `profiler` singleton work
        profiler.reset()

        @timed
        def sample_fn() -> int:
            return 42

        assert sample_fn() == 42
        assert profiler.get_stats()  # something was recorded
