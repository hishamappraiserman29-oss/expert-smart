"""
profiler.py — PH.4 Performance Profiler

Lightweight, zero-dependency timing instrumentation:
  - @timed decorator — records elapsed time per function call
  - PerformanceProfiler.profile() context manager — named sections
  - Thread-safe aggregation: calls, total_ms, avg_ms, min_ms, max_ms
  - Module-level `profiler` singleton for drop-in use

Classes:
    TimingRecord       — aggregated stats for one function / section
    PerformanceProfiler — collect, aggregate, and report timing data
    timed()            — decorator bound to the module-level profiler
"""

from __future__ import annotations

import contextlib
import functools
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generator, List, Optional


# ---------------------------------------------------------------------------
# TimingRecord
# ---------------------------------------------------------------------------

@dataclass
class TimingRecord:
    """Aggregated timing statistics for one function or named section."""

    name: str
    calls: int = 0
    total_ms: float = 0.0
    min_ms: float = float("inf")
    max_ms: float = 0.0
    errors: int = 0

    @property
    def avg_ms(self) -> float:
        return round(self.total_ms / self.calls, 3) if self.calls else 0.0

    def record(self, elapsed_ms: float, error: bool = False) -> None:
        self.calls += 1
        self.total_ms = round(self.total_ms + elapsed_ms, 3)
        if elapsed_ms < self.min_ms:
            self.min_ms = elapsed_ms
        if elapsed_ms > self.max_ms:
            self.max_ms = elapsed_ms
        if error:
            self.errors += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "calls": self.calls,
            "total_ms": round(self.total_ms, 3),
            "avg_ms": self.avg_ms,
            "min_ms": round(self.min_ms, 3) if self.min_ms != float("inf") else None,
            "max_ms": round(self.max_ms, 3),
            "errors": self.errors,
        }


# ---------------------------------------------------------------------------
# PerformanceProfiler
# ---------------------------------------------------------------------------

class PerformanceProfiler:
    """
    Collect and aggregate timing data for functions and code sections.

    Thread-safe: multiple threads may record simultaneously.

    Usage
    -----
    Decorator::
        @profiler.timed
        def my_func(): ...

    Context manager::
        with profiler.profile("section_name"):
            heavy_work()

    Stats::
        stats = profiler.get_stats()
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: Dict[str, TimingRecord] = {}

    # -- Decorator ------------------------------------------------------------

    def timed(self, func: Callable) -> Callable:
        """Decorator: record elapsed time for every call to *func*."""
        name = func.__qualname__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            t0 = time.perf_counter()
            error = False
            try:
                return func(*args, **kwargs)
            except Exception:
                error = True
                raise
            finally:
                elapsed_ms = (time.perf_counter() - t0) * 1000
                self._record(name, elapsed_ms, error)

        wrapper._profiler_name = name   # type: ignore[attr-defined]
        return wrapper

    # -- Context manager ------------------------------------------------------

    @contextlib.contextmanager
    def profile(self, name: str) -> Generator[None, None, None]:
        """Context manager: record elapsed time for the enclosed block."""
        t0 = time.perf_counter()
        error = False
        try:
            yield
        except Exception:
            error = True
            raise
        finally:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            self._record(name, elapsed_ms, error)

    # -- Manual record --------------------------------------------------------

    def record(self, name: str, elapsed_ms: float, error: bool = False) -> None:
        """Manually record a timing observation."""
        self._record(name, elapsed_ms, error)

    # -- Stats ----------------------------------------------------------------

    def get_stats(self, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Return aggregated stats.

        Parameters
        ----------
        name : if given, return stats for that name only (or empty dict if
               not yet recorded); otherwise return all names.
        """
        with self._lock:
            if name is not None:
                rec = self._records.get(name)
                return rec.to_dict() if rec else {}
            return {n: r.to_dict() for n, r in self._records.items()}

    def get_record(self, name: str) -> Optional[TimingRecord]:
        """Return the raw TimingRecord for *name*, or None."""
        with self._lock:
            return self._records.get(name)

    def reset(self, name: Optional[str] = None) -> None:
        """
        Clear recorded stats.

        Parameters
        ----------
        name : if given, reset only that entry; otherwise reset all.
        """
        with self._lock:
            if name is not None:
                self._records.pop(name, None)
            else:
                self._records.clear()

    def sorted_by(self, key: str = "total_ms", top_n: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Return stats sorted by *key* descending.

        Parameters
        ----------
        key    : one of 'total_ms', 'avg_ms', 'calls', 'max_ms'
        top_n  : limit to first N entries
        """
        with self._lock:
            rows = [r.to_dict() for r in self._records.values()]
        rows.sort(key=lambda r: r.get(key, 0), reverse=True)
        if top_n is not None:
            rows = rows[:top_n]
        return rows

    def summary(self) -> Dict[str, Any]:
        """High-level summary across all recorded sections."""
        with self._lock:
            records = list(self._records.values())
        if not records:
            return {"functions_tracked": 0, "total_calls": 0, "total_ms": 0.0}
        total_calls = sum(r.calls for r in records)
        total_ms = sum(r.total_ms for r in records)
        slowest = max(records, key=lambda r: r.avg_ms)
        return {
            "functions_tracked": len(records),
            "total_calls": total_calls,
            "total_ms": round(total_ms, 3),
            "slowest_fn": slowest.name,
            "slowest_avg_ms": slowest.avg_ms,
        }

    # -- Internal -------------------------------------------------------------

    def _record(self, name: str, elapsed_ms: float, error: bool) -> None:
        with self._lock:
            if name not in self._records:
                self._records[name] = TimingRecord(name=name)
            self._records[name].record(elapsed_ms, error)


# ---------------------------------------------------------------------------
# Module-level singleton + @timed shortcut
# ---------------------------------------------------------------------------

#: Module-level profiler instance — import and use directly.
profiler = PerformanceProfiler()


def timed(func: Callable) -> Callable:
    """Decorator shortcut — records timing on the module-level `profiler`."""
    return profiler.timed(func)
