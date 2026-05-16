"""
tools/perf_baseline.py

Capture current performance numbers for the 3 engines
(validation, PDF, DB) plus the full combined pipeline.

Usage:
    python tools/perf_baseline.py --iterations 5 --out docs/PERF_BASELINE_v1.0.0.md
"""
from __future__ import annotations

import argparse
import gc
import platform
import statistics
import sys
import time
import tracemalloc
from pathlib import Path
from tempfile import TemporaryDirectory

# ── resolve paths so the script works when invoked from the project root ──
_ROOT = Path(__file__).resolve().parent.parent
_CORE = _ROOT / "core_engine"
_TESTS = _CORE / "tests"
for _p in (_CORE, _TESTS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from reports.db import get_report, save_report          # noqa: E402
from reports.pdf import generate_pdf                    # noqa: E402
from reports.validation import validate_report          # noqa: E402
from _sample_reports import sample_report_data          # noqa: E402


# ─────────────────────────── timing helpers ──────────────────────────────────

def _time_call(fn) -> tuple[float, int]:
    """Run fn once; return (elapsed_seconds, peak_bytes)."""
    gc.collect()
    tracemalloc.start()
    t0 = time.perf_counter()
    fn()
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak


def measure(label: str, fn, n: int) -> dict:
    """Run fn n times and collect timing + memory statistics."""
    times, peaks = [], []
    for _ in range(n):
        t, p = _time_call(fn)
        times.append(t)
        peaks.append(p)
    return {
        "label": label,
        "n": n,
        "time_s": {
            "min":    round(min(times), 4),
            "median": round(statistics.median(times), 4),
            "mean":   round(statistics.mean(times), 4),
            "max":    round(max(times), 4),
        },
        "mem_mb": {
            "min":    round(min(peaks) / 1_048_576, 2),
            "median": round(statistics.median(peaks) / 1_048_576, 2),
            "max":    round(max(peaks) / 1_048_576, 2),
        },
    }


# ─────────────────────────── main ────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Capture engine performance baseline.")
    parser.add_argument("--iterations", type=int, default=5, help="Runs per scenario")
    parser.add_argument("--out", type=Path, default=Path("docs/PERF_BASELINE_v1.0.0.md"))
    parser.add_argument("--profile", default="professional_template",
                        choices=["legacy", "detailed", "professional_template"])
    args = parser.parse_args()

    data = sample_report_data(args.profile)
    results = []

    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path  = tmp_path / "perf.db"

        # 1. validate_report
        results.append(measure(
            "validate_report",
            lambda: validate_report(data, profile_key=args.profile),
            args.iterations,
        ))

        # 2. generate_pdf
        results.append(measure(
            "generate_pdf",
            lambda: generate_pdf(
                profile_key=args.profile,
                data=data,
                output_path=tmp_path / "perf.pdf",
            ),
            args.iterations,
        ))

        # 3. save_report  (unique report_id each call to avoid PK clash)
        counter = [0]

        def _save():
            counter[0] += 1
            save_report(
                data,
                profile_key=args.profile,
                report_id=f"perf-save-{counter[0]}",
                db_path=db_path,
            )

        results.append(measure("save_report", _save, args.iterations))

        # 4. get_report  (read the first saved record repeatedly)
        results.append(measure(
            "get_report",
            lambda: get_report("perf-save-1", db_path=db_path),
            args.iterations,
        ))

        # 5. full pipeline: validate + pdf + save
        pipe = [0]

        def _pipeline():
            pipe[0] += 1
            validate_report(data, profile_key=args.profile)
            generate_pdf(
                profile_key=args.profile,
                data=data,
                output_path=tmp_path / f"pipe_{pipe[0]}.pdf",
            )
            save_report(
                data,
                profile_key=args.profile,
                report_id=f"perf-pipe-{pipe[0]}",
                db_path=db_path,
            )

        results.append(measure("full pipeline (validate+pdf+save)", _pipeline, args.iterations))

    # ── write markdown ────────────────────────────────────────────────────────
    args.out.parent.mkdir(parents=True, exist_ok=True)
    captured_at = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

    lines = [
        "# Performance Baseline — v1.0.0",
        "",
        f"**Captured:** {captured_at}",
        f"**Iterations:** {args.iterations}",
        f"**Profile:** `{args.profile}`",
        f"**Platform:** `{platform.platform()}`",
        f"**Python:** `{sys.version.split()[0]}`",
        "",
        "## Numbers",
        "",
        "| Scenario | n | min (s) | median (s) | mean (s) | max (s) | peak mem (MB) median |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        t, m = r["time_s"], r["mem_mb"]
        lines.append(
            f"| {r['label']} | {r['n']} "
            f"| {t['min']} | {t['median']} | {t['mean']} | {t['max']} "
            f"| {m['median']} |"
        )

    lines += [
        "",
        "## Regression Policy",
        "",
        "Any commit whose **median time exceeds 2× the median** above for any scenario",
        "should trigger investigation before merging.",
        "Re-run this script after the change and compare.",
        "",
        "## How to re-run",
        "",
        "```bash",
        f"python tools/perf_baseline.py --iterations {args.iterations} --profile {args.profile}",
        "```",
        "",
        "Overwrite this file only when deliberately updating the baseline (e.g. after",
        "a performance improvement or a major engine refactor). Commit the updated file",
        "alongside the change so the history is traceable.",
    ]

    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"OK  Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
