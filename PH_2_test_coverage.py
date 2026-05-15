"""
PH_2_test_coverage.py — Production Hardening: Coverage Runner & Gate

Runs all agent/MCP test suites under pytest-cov, reports per-module
coverage, enforces per-file minimums, and writes ph2_coverage_report.json.

Usage:
    python PH_2_test_coverage.py              # full run with gates
    python PH_2_test_coverage.py --baseline   # skip gates, just report
    python PH_2_test_coverage.py --html       # also open HTML report
    python PH_2_test_coverage.py --fast       # skip slow mcp_setup tests
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT  = Path(__file__).resolve().parent
CORE  = ROOT / "core_engine"
HTML  = ROOT / "htmlcov" / "index.html"
JSON  = ROOT / "ph2_coverage.json"
OUT   = ROOT / "ph2_coverage_report.json"

PYTHON = sys.executable

# ── Coverage thresholds (%) ───────────────────────────────────────────────────
# These are the MINIMUM acceptable coverage levels for production.
# Increase over time as dead-code is removed.

THRESHOLDS: Dict[str, int] = {
    "agents/__init__.py":            100,
    "agents/workspace_manager.py":    88,
    "agents/file_scanner.py":         90,
    "agents/pipeline_orchestrator.py":88,
    "agents/supervised_agent.py":     88,
    "agents/file_watcher.py":         90,
    "agents/command_parser.py":       95,
    "agents/chat_agent.py":           85,
    "mcp_bridge.py":                  75,
    "mcp_setup.py":                   70,
}

GLOBAL_THRESHOLD = 82   # overall must be >= this

# ── Test suites ───────────────────────────────────────────────────────────────

SUITES = [
    "tests/test_phase_16_e2e.py",
    "tests/test_phase_16_1_e2e.py",
    "tests/test_phase_17_e2e.py",
    "tests/test_phase_18_e2e.py",
    "tests/test_phase_19_e2e.py",
    "tests/test_phase_20_e2e.py",
    "tests/test_phase_21_e2e.py",
    "tests/test_ph2_coverage_gaps.py",   # gap-filling tests added in PH.2
]


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class ModuleCoverage:
    name:          str
    stmts:         int
    miss:          int
    cover_pct:     float
    missing_lines: List[int]  = field(default_factory=list)
    threshold:     Optional[int] = None

    @property
    def passed(self) -> bool:
        if self.threshold is None:
            return True
        return self.cover_pct >= self.threshold

    @property
    def gap(self) -> int:
        if self.threshold is None:
            return 0
        return max(0, self.threshold - int(self.cover_pct))


@dataclass
class CoverageReport:
    generated_at:   str
    python_version: str
    total_stmts:    int
    total_miss:     int
    total_cover:    float
    modules:        Dict[str, ModuleCoverage] = field(default_factory=dict)
    tests_passed:   int = 0
    tests_failed:   int = 0
    gate_passed:    bool = True
    failing_gates:  List[str] = field(default_factory=list)


# ── Runner ────────────────────────────────────────────────────────────────────

def _run_pytest(suites: List[str], html: bool = False) -> Tuple[int, str]:
    existing = [s for s in suites
                if (CORE / s).exists()]
    if not existing:
        return -1, "No test files found"

    cov_sources = ["--cov=agents", "--cov=mcp_bridge", "--cov=mcp_setup"]
    cov_reports = ["--cov-report=term-missing",
                   f"--cov-report=json:{JSON}"]
    if html:
        cov_reports.append("--cov-report=html:htmlcov")

    cmd = [PYTHON, "-m", "pytest", *existing,
           *cov_sources, *cov_reports,
           "-q", "--tb=short",
           "--timeout=30"]

    t0 = time.perf_counter()
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace",
                            cwd=str(CORE))
    elapsed = time.perf_counter() - t0
    output  = result.stdout + result.stderr
    print(output)
    print(f"  pytest finished in {elapsed:.1f}s")
    return result.returncode, output


def _parse_coverage_json() -> Optional[Dict]:
    if not JSON.exists():
        return None
    try:
        return json.loads(JSON.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _count_tests(output: str) -> Tuple[int, int]:
    """Extract passed/failed counts from pytest output."""
    import re
    m = re.search(r'(\d+) passed', output)
    passed = int(m.group(1)) if m else 0
    m = re.search(r'(\d+) failed', output)
    failed = int(m.group(1)) if m else 0
    return passed, failed


def build_coverage_report(json_data: Dict, test_output: str,
                           baseline_only: bool = False) -> CoverageReport:
    files   = json_data.get("files", {})
    totals  = json_data.get("totals", {})
    passed, failed = _count_tests(test_output)

    report = CoverageReport(
        generated_at=datetime.now().isoformat(timespec="seconds"),
        python_version=sys.version.split()[0],
        total_stmts=totals.get("num_statements", 0),
        total_miss=totals.get("missing_lines",  0),
        total_cover=round(totals.get("percent_covered", 0), 1),
        tests_passed=passed,
        tests_failed=failed,
    )

    failing: List[str] = []

    for path, fdata in files.items():
        # Normalise path to forward-slash relative key
        norm = path.replace("\\", "/")
        # Strip leading "core_engine/"
        if "core_engine/" in norm:
            norm = norm[norm.index("core_engine/") + len("core_engine/"):]

        summary = fdata.get("summary", {})
        stmts   = summary.get("num_statements", 0)
        miss    = summary.get("missing_lines",  0)
        pct     = round(summary.get("percent_covered", 0), 1)
        missing = fdata.get("missing_line_numbers", [])
        thresh  = THRESHOLDS.get(norm)

        mc = ModuleCoverage(
            name=norm, stmts=stmts, miss=miss,
            cover_pct=pct, missing_lines=missing,
            threshold=thresh,
        )
        report.modules[norm] = mc

        if not baseline_only and thresh and pct < thresh:
            failing.append(f"{norm}: {pct}% < {thresh}% required")

    if not baseline_only:
        if report.total_cover < GLOBAL_THRESHOLD:
            failing.append(
                f"TOTAL: {report.total_cover}% < {GLOBAL_THRESHOLD}% required"
            )

    report.gate_passed    = (len(failing) == 0 and failed == 0)
    report.failing_gates  = failing
    return report


def print_report(rep: CoverageReport) -> None:
    sep = "=" * 70
    print(f"\n{sep}")
    print("  PH.2 COVERAGE REPORT")
    print(f"  Generated : {rep.generated_at}")
    print(f"  Python    : {rep.python_version}")
    print(f"  Tests     : {rep.tests_passed} passed, {rep.tests_failed} failed")
    print(sep)

    # Sort: failing gates first, then by name
    sorted_mods = sorted(
        rep.modules.values(),
        key=lambda m: (m.passed, m.name),
    )
    for mc in sorted_mods:
        bar_len  = 20
        filled   = int(mc.cover_pct / 100 * bar_len)
        bar      = "#" * filled + "." * (bar_len - filled)
        gate_str = ""
        if mc.threshold is not None:
            gate_str = f"  [PASS]" if mc.passed else f"  [FAIL need {mc.threshold}%]"
        miss_str = f"  miss:{mc.miss}" if mc.miss else ""
        print(f"  {mc.cover_pct:5.1f}%  [{bar}]  {mc.name:<45}{gate_str}{miss_str}")

    print(f"\n{sep}")
    print(f"  TOTAL: {rep.total_cover}% coverage  "
          f"({rep.total_stmts - rep.total_miss}/{rep.total_stmts} stmts)")

    if rep.gate_passed:
        print("  GATE: PASSED")
    else:
        print("  GATE: FAILED")
        for f in rep.failing_gates:
            print(f"    - {f}")
    print(sep)


def save_report(rep: CoverageReport) -> None:
    def _ser(obj):
        if hasattr(obj, "__dataclass_fields__"):
            import dataclasses
            return dataclasses.asdict(obj)
        return str(obj)
    OUT.write_text(
        json.dumps({
            "generated_at":   rep.generated_at,
            "python_version": rep.python_version,
            "total_stmts":    rep.total_stmts,
            "total_miss":     rep.total_miss,
            "total_cover":    rep.total_cover,
            "tests_passed":   rep.tests_passed,
            "tests_failed":   rep.tests_failed,
            "gate_passed":    rep.gate_passed,
            "failing_gates":  rep.failing_gates,
            "modules":        {k: {
                "cover_pct":     v.cover_pct,
                "stmts":         v.stmts,
                "miss":          v.miss,
                "threshold":     v.threshold,
                "passed":        v.passed,
                "missing_lines": v.missing_lines[:20],   # first 20
            } for k, v in rep.modules.items()},
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\n  Report saved -> {OUT.name}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="PH.2 Coverage Runner")
    ap.add_argument("--baseline", action="store_true",
                    help="Report only — skip threshold gates")
    ap.add_argument("--html",     action="store_true",
                    help="Generate HTML report and open in browser")
    ap.add_argument("--fast",     action="store_true",
                    help="Skip slow tests (mcp_setup)")
    args = ap.parse_args()

    suites = SUITES
    if args.fast:
        suites = [s for s in suites if "16_1" not in s]

    rc, output = _run_pytest(suites, html=args.html)

    cov_data = _parse_coverage_json()
    if cov_data is None:
        print("ERROR: coverage JSON not found — did pytest-cov run?")
        return 1

    report = build_coverage_report(cov_data, output,
                                   baseline_only=args.baseline)
    print_report(report)
    save_report(report)

    if args.html and HTML.exists():
        webbrowser.open(str(HTML))

    # Return 0 only if all gates pass and no tests failed
    return 0 if report.gate_passed else 1


if __name__ == "__main__":
    sys.exit(main())
