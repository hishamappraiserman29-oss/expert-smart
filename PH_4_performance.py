"""
PH_4_performance.py -- Production Hardening: Performance & Scaling Runner

Runs a suite of micro-benchmarks to validate and document the performance
characteristics of the performance/ package components:
  1. TTLCache      -- throughput, hit-rate, TTL overhead
  2. Paginator     -- pagination speed across list sizes
  3. Profiler      -- overhead measurement of the @timed decorator
  4. Integration   -- simulated API page + cache workflow

Usage:
    python PH_4_performance.py              # full benchmark run
    python PH_4_performance.py --quick      # 10x fewer iterations
    python PH_4_performance.py --json       # save ph4_performance_report.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
CORE = ROOT / "core_engine"
OUT = ROOT / "ph4_performance_report.json"

sys.path.insert(0, str(CORE))


# -- Data structures ---------------------------------------------------------

@dataclass
class BenchResult:
    name: str
    ops: int                # operations performed
    elapsed_ms: float
    ops_per_sec: float
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "ops": self.ops,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "ops_per_sec": round(self.ops_per_sec),
            "notes": self.notes,
        }


@dataclass
class PerfReport:
    generated_at: str
    python_version: str
    results: List[BenchResult] = field(default_factory=list)
    gate_passed: bool = True
    failing_gates: List[str] = field(default_factory=list)


# -- Helpers -----------------------------------------------------------------

def _sep(char: str = "=", width: int = 70) -> str:
    return char * width


def _bench(name: str, fn: Any, ops: int) -> BenchResult:
    t0 = time.perf_counter()
    fn()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    ops_per_sec = ops / (elapsed_ms / 1000) if elapsed_ms > 0 else float("inf")
    return BenchResult(name=name, ops=ops, elapsed_ms=elapsed_ms, ops_per_sec=ops_per_sec)


# -- Benchmarks --------------------------------------------------------------

def bench_cache_write(n: int) -> BenchResult:
    from performance.cache import TTLCache
    cache = TTLCache(max_size=n + 100, default_ttl=60)

    def run() -> None:
        for i in range(n):
            cache.set(f"key:{i}", {"value": i, "data": "x" * 32})

    return _bench(f"cache_write ({n:,} entries)", run, n)


def bench_cache_read_hit(n: int) -> BenchResult:
    from performance.cache import TTLCache
    cache = TTLCache(max_size=n + 100, default_ttl=60)
    for i in range(n):
        cache.set(f"key:{i}", i)

    def run() -> None:
        for i in range(n):
            _ = cache.get(f"key:{i}")

    r = _bench(f"cache_read_hit ({n:,} hits)", run, n)
    r.notes = f"hit_rate=100%"
    return r


def bench_cache_lru_eviction(n: int) -> BenchResult:
    from performance.cache import TTLCache
    cache = TTLCache(max_size=n // 2)   # evict half

    def run() -> None:
        for i in range(n):
            cache.set(f"k{i}", i)

    r = _bench(f"cache_lru_eviction ({n:,} sets, cap={n // 2})", run, n)
    r.notes = f"evictions={cache.stats()['evictions']}"
    return r


def bench_paginator_small(n_items: int, page_size: int) -> BenchResult:
    from performance.paginator import Paginator
    items = [{"id": i, "value": i} for i in range(n_items)]

    ops = 100

    def run() -> None:
        for page in range(1, ops + 1):
            Paginator.paginate(items, page=((page - 1) % (n_items // page_size + 1)) + 1,
                               page_size=page_size)

    return _bench(f"paginator ({n_items} items, pg_size={page_size}, {ops} calls)", run, ops)


def bench_paginator_sort(n_items: int) -> BenchResult:
    from performance.paginator import Paginator
    import random
    items = [{"id": i, "value": random.randint(0, 10000)} for i in range(n_items)]

    ops = 20

    def run() -> None:
        for _ in range(ops):
            Paginator.paginate(items, page=1, page_size=20, sort_by="value", sort_dir="desc")

    return _bench(f"paginator_sort ({n_items} items, {ops} calls)", run, ops)


def bench_profiler_overhead(n: int) -> BenchResult:
    from performance.profiler import PerformanceProfiler
    prof = PerformanceProfiler()

    @prof.timed
    def noop() -> None:
        pass

    def run() -> None:
        for _ in range(n):
            noop()

    r = _bench(f"profiler_overhead ({n:,} calls)", run, n)
    stats = prof.get_stats()
    if stats:
        rec = list(stats.values())[0]
        r.notes = f"avg_overhead={rec['avg_ms']:.4f}ms/call"
    return r


def bench_cached_decorator(n: int) -> BenchResult:
    from performance.cache import TTLCache, cached

    cache = TTLCache(max_size=n, default_ttl=30)
    call_count = [0]

    @cached(cache)
    def compute(x: int) -> int:
        call_count[0] += 1
        return x * x

    # Prime cache
    for i in range(100):
        compute(i)

    def run() -> None:
        for _ in range(n):
            compute(_ % 100)   # all hits after priming

    r = _bench(f"cached_decorator ({n:,} calls, 100-key cache)", run, n)
    s = cache.stats()
    r.notes = f"hit_rate={s['hit_rate_pct']}%"
    return r


# -- Integration benchmark ---------------------------------------------------

def bench_integration(n_items: int) -> BenchResult:
    """Simulates a typical paginated API endpoint backed by TTLCache."""
    from performance.cache import TTLCache
    from performance.paginator import Paginator

    cache = TTLCache(max_size=50, default_ttl=60)
    # Simulate a dataset that takes time to build
    raw_data = [{"id": i, "price": i * 1000, "area": 100 + i} for i in range(n_items)]

    def handle_request(page: int, page_size: int = 20) -> Dict[str, Any]:
        cache_key = f"list:p{page}:s{page_size}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        # Simulate sort + paginate
        result = Paginator.paginate(raw_data, page=page, page_size=page_size,
                                    sort_by="price", sort_dir="desc")
        payload = result.to_dict()
        cache.set(cache_key, payload)
        return payload

    n_requests = 200

    def run() -> None:
        for i in range(n_requests):
            page = (i % 5) + 1
            handle_request(page)

    r = _bench(f"integration_api ({n_items} records, {n_requests} requests)", run, n_requests)
    s = cache.stats()
    r.notes = f"cache_hit_rate={s['hit_rate_pct']}%  (5 unique pages, {n_requests} requests)"
    return r


# -- Gates -------------------------------------------------------------------

# Minimum acceptable performance thresholds
GATES: Dict[str, int] = {
    "cache_write":           50_000,   # 50K writes/sec
    "cache_read_hit":       200_000,   # 200K reads/sec
    "profiler_overhead":     30_000,   # 30K instrumented calls/sec
}


def check_gates(results: List[BenchResult]) -> List[str]:
    failing = []
    for r in results:
        for gate_name, min_ops in GATES.items():
            if gate_name in r.name and r.ops_per_sec < min_ops:
                failing.append(
                    f"{r.name}: {r.ops_per_sec:,.0f} ops/s < {min_ops:,} required"
                )
    return failing


# -- Report ------------------------------------------------------------------

def print_report(rep: PerfReport) -> None:
    print(f"\n{_sep()}")
    print("  PH.4 PERFORMANCE REPORT")
    print(f"  Generated : {rep.generated_at}")
    print(f"  Python    : {rep.python_version}")
    print(_sep())

    print(f"\n  {'Benchmark':<55} {'ops/sec':>12}  {'ms':>8}  Notes")
    print(f"  {'-' * 54} {'-' * 12}  {'-' * 8}  -----")
    for r in rep.results:
        print(f"  {r.name:<55} {r.ops_per_sec:>12,.0f}  {r.elapsed_ms:>7.1f}ms  {r.notes}")

    print(f"\n{_sep()}")
    if rep.gate_passed:
        print("  GATE: PASSED")
    else:
        print("  GATE: FAILED")
        for g in rep.failing_gates:
            print(f"    - {g}")
    print(_sep())


def save_report(rep: PerfReport) -> None:
    OUT.write_text(
        json.dumps({
            "generated_at": rep.generated_at,
            "python_version": rep.python_version,
            "gate_passed": rep.gate_passed,
            "failing_gates": rep.failing_gates,
            "results": [r.to_dict() for r in rep.results],
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\n  Report saved -> {OUT.name}")


# -- Main --------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="PH.4 Performance Runner")
    ap.add_argument("--quick", action="store_true", help="10x fewer iterations")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    scale = 10 if args.quick else 100

    print(f"\n{_sep()}")
    print("  PH.4 PERFORMANCE BENCHMARKS")
    print(f"  Scale: {'quick (10x)' if args.quick else 'full'}")
    print(_sep())

    results: List[BenchResult] = []

    print("\n  [1/4] TTLCache benchmarks...")
    results.append(bench_cache_write(500 * scale))
    results.append(bench_cache_read_hit(500 * scale))
    results.append(bench_cache_lru_eviction(500 * scale))
    results.append(bench_cached_decorator(1000 * scale))

    print("  [2/4] Paginator benchmarks...")
    results.append(bench_paginator_small(1000, 20))
    results.append(bench_paginator_small(10000, 50))
    results.append(bench_paginator_sort(5000))

    print("  [3/4] Profiler benchmarks...")
    results.append(bench_profiler_overhead(500 * scale))

    print("  [4/4] Integration benchmark...")
    results.append(bench_integration(500))

    failing = check_gates(results)
    gate_passed = len(failing) == 0

    rep = PerfReport(
        generated_at=datetime.now().isoformat(timespec="seconds"),
        python_version=sys.version.split()[0],
        results=results,
        gate_passed=gate_passed,
        failing_gates=failing,
    )

    print_report(rep)

    if args.json:
        save_report(rep)
    else:
        save_report(rep)   # always save

    return 0 if gate_passed else 1


if __name__ == "__main__":
    sys.exit(main())
