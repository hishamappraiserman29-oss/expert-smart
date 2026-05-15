"""
PH_1_code_quality.py — Production Hardening: Code Quality Runner

Runs every configured quality tool against the core_engine/ package, collects
results, prints a consolidated report, and writes machine-readable JSON to
ph1_quality_report.json.

Tools:
    flake8   — PEP-8 style + pyflakes error detection
    pylint   — comprehensive lint (errors + warnings only, no style noise)
    bandit   — security vulnerability scanner
    radon    — cyclomatic complexity + maintainability index
    vulture  — dead-code detection
    mypy     — static type checking (agent modules only)

Usage:
    python PH_1_code_quality.py [--fix] [--tool TOOL] [--json]

    --fix        Run black + isort to auto-fix formatting (safe changes only)
    --tool TOOL  Run only one tool (flake8|pylint|bandit|radon|vulture|mypy)
    --json       Write ph1_quality_report.json and exit quietly
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# ── Paths ─────────────────────────────────────────────────────────────────────

ROOT       = Path(__file__).resolve().parent
CORE       = ROOT / "core_engine"
AGENTS     = CORE / "agents"
PYTHON     = sys.executable
REPORT_OUT = ROOT / "ph1_quality_report.json"


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class QualityIssue:
    tool:     str
    severity: str       # error | warning | info
    file:     str
    line:     int
    code:     str
    message:  str


@dataclass
class ToolResult:
    tool:        str
    ran:         bool
    exit_code:   int
    duration_s:  float
    issues:      List[QualityIssue] = field(default_factory=list)
    raw_output:  str = ""
    error:       Optional[str] = None

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")


@dataclass
class QualityReport:
    generated_at:   str
    python_version: str
    total_issues:   int
    error_count:    int
    warning_count:  int
    tools:          Dict[str, ToolResult] = field(default_factory=dict)
    grade:          str = "?"       # A–F


# ── Tool runners ──────────────────────────────────────────────────────────────

def _run(cmd: List[str], cwd: Path = ROOT) -> tuple[int, str]:
    """Run a subprocess; return (exit_code, combined stdout+stderr)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", cwd=str(cwd),
        )
        return result.returncode, result.stdout + result.stderr
    except FileNotFoundError as exc:
        return -1, f"Tool not found: {exc}"


# ── flake8 ────────────────────────────────────────────────────────────────────

def run_flake8() -> ToolResult:
    t0 = time.perf_counter()
    rc, out = _run([PYTHON, "-m", "flake8", "core_engine/",
                    "--config", ".flake8",
                    "--format=%(path)s:%(row)d:%(col)d: %(code)s %(text)s"])
    duration = time.perf_counter() - t0

    issues: List[QualityIssue] = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("core_engine") is False:
            if not (len(line) > 3 and line[0].isalpha() and ":" in line):
                continue
        parts = line.split(":", 3)
        if len(parts) < 4:
            continue
        try:
            fname, lineno, col, rest = parts
            rest  = rest.strip()
            code  = rest.split()[0] if rest else "?"
            msg   = rest[len(code):].strip()
            sev   = "error" if code.startswith("E") else "warning"
            issues.append(QualityIssue(
                tool="flake8", severity=sev,
                file=fname.strip(), line=int(lineno),
                code=code, message=msg,
            ))
        except (ValueError, IndexError):
            continue

    return ToolResult(tool="flake8", ran=rc != -1, exit_code=rc,
                      duration_s=duration, issues=issues, raw_output=out)


# ── pylint ────────────────────────────────────────────────────────────────────

def run_pylint() -> ToolResult:
    t0 = time.perf_counter()
    # Run only on agents/ and key modules; bridge_api.py is too large for strict
    targets = [
        "core_engine/agents/",
        "core_engine/mcp_bridge.py",
        "core_engine/mcp_setup.py",
    ]
    rc, out = _run([PYTHON, "-m", "pylint", *targets,
                    "--rcfile=.pylintrc",
                    "--output-format=text",
                    "--errors-only"])          # errors only for CI gate
    duration = time.perf_counter() - t0

    issues: List[QualityIssue] = []
    for line in out.splitlines():
        # Format: path:line:col: Exxxx (symbol) message
        if line.startswith("*") or line.startswith("-") or not line.strip():
            continue
        parts = line.split(":", 3)
        if len(parts) < 4:
            continue
        try:
            fname, lineno, col, rest = parts
            rest  = rest.strip()
            code  = rest.split()[0] if rest else "?"
            msg   = rest[len(code):].strip()
            sev   = "error" if code.startswith("E") else "warning"
            issues.append(QualityIssue(
                tool="pylint", severity=sev,
                file=fname.strip(), line=int(lineno),
                code=code, message=msg,
            ))
        except (ValueError, IndexError):
            continue

    return ToolResult(tool="pylint", ran=rc != -1, exit_code=rc,
                      duration_s=duration, issues=issues, raw_output=out)


# ── bandit ────────────────────────────────────────────────────────────────────

def run_bandit() -> ToolResult:
    t0 = time.perf_counter()
    rc, out = _run([PYTHON, "-m", "bandit",
                    "-r", "core_engine/",
                    "-c", ".bandit",
                    "--format", "json",
                    "--quiet"])
    duration = time.perf_counter() - t0

    issues: List[QualityIssue] = []
    try:
        data    = json.loads(out)
        results = data.get("results", [])
        for r in results:
            sev = r.get("issue_severity", "LOW").lower()
            sev = "error" if sev == "high" else ("warning" if sev == "medium" else "info")
            issues.append(QualityIssue(
                tool="bandit", severity=sev,
                file=r.get("filename", "?"),
                line=r.get("line_number", 0),
                code=r.get("test_id", "?"),
                message=f"{r.get('test_name','')}: {r.get('issue_text','')}",
            ))
    except (json.JSONDecodeError, KeyError):
        pass

    return ToolResult(tool="bandit", ran=rc != -1, exit_code=rc,
                      duration_s=duration, issues=issues, raw_output=out)


# ── radon (complexity) ────────────────────────────────────────────────────────

def run_radon() -> ToolResult:
    """Report functions with complexity >= C (moderate)."""
    t0 = time.perf_counter()
    rc, out = _run([PYTHON, "-m", "radon", "cc", "core_engine/",
                    "--min", "C",     # C=complex, D=very, E=critical, F=untestable
                    "--show-complexity",
                    "--average"])
    duration = time.perf_counter() - t0

    issues: List[QualityIssue] = []
    current_file = ""
    for line in out.splitlines():
        line = line.rstrip()
        if not line:
            continue
        if not line.startswith("    "):
            current_file = line.strip()
            continue
        # "    M 23:4 my_function - D (15)"
        parts = line.strip().split()
        if len(parts) < 5:
            continue
        try:
            kind, loc, name, dash, grade_score = parts[0], parts[1], parts[2], parts[3], parts[4]
            lineno   = int(loc.split(":")[0])
            grade_ch = grade_score.strip("()")
            sev      = "error" if grade_ch in ("E", "F") else "warning"
            score    = parts[5].strip("()") if len(parts) > 5 else "?"
            issues.append(QualityIssue(
                tool="radon", severity=sev,
                file=current_file, line=lineno,
                code=f"CC-{grade_ch}",
                message=f"{name} cyclomatic complexity {grade_ch} ({score})",
            ))
        except (ValueError, IndexError):
            continue

    return ToolResult(tool="radon", ran=rc != -1, exit_code=rc,
                      duration_s=duration, issues=issues, raw_output=out)


# ── vulture (dead code) ───────────────────────────────────────────────────────

def run_vulture() -> ToolResult:
    t0 = time.perf_counter()
    whitelist = ".vulture_whitelist.py"
    cmd = [PYTHON, "-m", "vulture",
           "core_engine/agents/",
           "core_engine/mcp_bridge.py",
           "core_engine/mcp_setup.py",
           "--min-confidence", "80"]
    if Path(whitelist).exists():
        cmd.insert(3, whitelist)
    rc, out = _run(cmd)
    duration = time.perf_counter() - t0

    issues: List[QualityIssue] = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        # "path/file.py:42: unused variable 'x' (80% confidence)"
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        try:
            fname, lineno, rest = parts
            issues.append(QualityIssue(
                tool="vulture", severity="warning",
                file=fname.strip(), line=int(lineno),
                code="VUL001",
                message=rest.strip(),
            ))
        except (ValueError, IndexError):
            continue

    return ToolResult(tool="vulture", ran=rc != -1, exit_code=rc,
                      duration_s=duration, issues=issues, raw_output=out)


# ── mypy (type checking) ──────────────────────────────────────────────────────

def run_mypy() -> ToolResult:
    t0 = time.perf_counter()
    targets = [
        "core_engine/agents/workspace_manager.py",
        "core_engine/agents/file_scanner.py",
        "core_engine/agents/pipeline_orchestrator.py",
        "core_engine/agents/supervised_agent.py",
        "core_engine/agents/file_watcher.py",
        "core_engine/agents/command_parser.py",
        "core_engine/agents/chat_agent.py",
        "core_engine/mcp_bridge.py",
    ]
    rc, out = _run([PYTHON, "-m", "mypy", *targets,
                    "--config-file", "pyproject.toml",
                    "--no-error-summary"])
    duration = time.perf_counter() - t0

    issues: List[QualityIssue] = []
    for line in out.splitlines():
        if ": error:" in line or ": warning:" in line or ": note:" in line:
            try:
                head, msg = line.split(": ", 1)
                parts     = head.rsplit(":", 2)
                fname     = parts[0]
                lineno    = int(parts[1]) if len(parts) > 1 else 0
                if ": error:" in line:
                    sev, code = "error",   "mypy-error"
                elif ": warning:" in line:
                    sev, code = "warning", "mypy-warning"
                else:
                    sev, code = "info",    "mypy-note"
                issues.append(QualityIssue(
                    tool="mypy", severity=sev,
                    file=fname, line=lineno,
                    code=code, message=msg.strip(),
                ))
            except (ValueError, IndexError):
                continue

    return ToolResult(tool="mypy", ran=rc != -1, exit_code=rc,
                      duration_s=duration, issues=issues, raw_output=out)


# ── Auto-fix (black + isort) ──────────────────────────────────────────────────

def run_autofix(target: str = "core_engine/agents/") -> None:
    print(f"\n{'-'*60}")
    print("  AUTO-FIX: black + isort on", target)
    print(f"{'-'*60}")

    rc_black, out_black = _run([PYTHON, "-m", "black", target, "--line-length", "120"])
    print("  black:", "OK" if rc_black == 0 else "ERRORS")
    if out_black.strip():
        for l in out_black.strip().splitlines()[-10:]:
            print("    ", l)

    rc_isort, out_isort = _run([PYTHON, "-m", "isort", target, "--profile", "black"])
    print("  isort:", "OK" if rc_isort == 0 else "ERRORS")
    if out_isort.strip():
        for l in out_isort.strip().splitlines()[-10:]:
            print("    ", l)


# ── Grading ───────────────────────────────────────────────────────────────────

def _grade(error_count: int, warning_count: int) -> str:
    total = error_count * 3 + warning_count
    if error_count == 0 and total == 0:
        return "A"
    if error_count == 0 and total <= 10:
        return "B"
    if error_count <= 3 and total <= 30:
        return "C"
    if error_count <= 10:
        return "D"
    return "F"


# ── Report ────────────────────────────────────────────────────────────────────

_SEV_COLOR = {
    "error":   "\033[91m",   # red
    "warning": "\033[93m",   # yellow
    "info":    "\033[96m",   # cyan
}
_RESET = "\033[0m"
_BOLD  = "\033[1m"


def _color(text: str, code: str) -> str:
    return f"{code}{text}{_RESET}" if sys.stdout.isatty() else text


def print_report(report: QualityReport) -> None:
    sep = "=" * 70
    print(f"\n{sep}")
    print(f"  PH.1 CODE QUALITY REPORT")
    print(f"  Generated : {report.generated_at}")
    print(f"  Python    : {report.python_version}")
    print(sep)

    for name, tr in report.tools.items():
        if not tr.ran:
            print(f"\n  {'⚠':2}  {name:10} — NOT RUN (tool missing?)")
            continue
        status = "OK" if tr.exit_code in (0, 1) else "!!"
        counts = f"{tr.error_count} errors, {tr.warning_count} warnings"
        print(f"\n  {status}  {name:18} {counts:30} ({tr.duration_s:.1f}s)")

        shown = [i for i in tr.issues if i.severity in ("error", "warning")][:20]
        for issue in shown:
            fname = Path(issue.file).name
            sev_ch = issue.severity[0].upper()
            print(f"     {sev_ch}  {fname}:{issue.line}  [{issue.code}]  {issue.message[:80]}")
        if len(tr.issues) > 20:
            print(f"     … and {len(tr.issues) - 20} more (see ph1_quality_report.json)")

    print(f"\n{sep}")
    print(f"  TOTAL  {report.error_count} errors, {report.warning_count} warnings"
          f"   Grade: {report.grade}")
    print(sep)


def build_report(results: Dict[str, ToolResult]) -> QualityReport:
    errors   = sum(t.error_count   for t in results.values())
    warnings = sum(t.warning_count for t in results.values())
    total    = sum(len(t.issues)   for t in results.values())
    return QualityReport(
        generated_at=datetime.now().isoformat(timespec="seconds"),
        python_version=sys.version.split()[0],
        total_issues=total,
        error_count=errors,
        warning_count=warnings,
        tools=results,
        grade=_grade(errors, warnings),
    )


def save_report(report: QualityReport) -> None:
    def _serialise(obj):
        if isinstance(obj, QualityIssue):
            return asdict(obj)
        if isinstance(obj, ToolResult):
            d = asdict(obj)
            d["error_count"]   = obj.error_count
            d["warning_count"] = obj.warning_count
            return d
        if isinstance(obj, QualityReport):
            d = asdict(obj)
            d["tools"] = {k: _serialise(v) for k, v in obj.tools.items()}
            return d
        return str(obj)

    REPORT_OUT.write_text(
        json.dumps(_serialise(report), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\n  Report saved -> {REPORT_OUT.name}")


# ── CLI ───────────────────────────────────────────────────────────────────────

_TOOL_MAP = {
    "flake8":  run_flake8,
    "pylint":  run_pylint,
    "bandit":  run_bandit,
    "radon":   run_radon,
    "vulture": run_vulture,
    "mypy":    run_mypy,
}

_ALL_TOOLS = ["flake8", "pylint", "bandit", "radon", "vulture", "mypy"]


def main() -> int:
    parser = argparse.ArgumentParser(description="PH.1 Code Quality Runner")
    parser.add_argument("--fix",  action="store_true",
                        help="Auto-format agents/ with black + isort")
    parser.add_argument("--tool", choices=list(_TOOL_MAP), default=None,
                        help="Run only one tool")
    parser.add_argument("--json", action="store_true",
                        help="Write JSON report and suppress verbose output")
    args = parser.parse_args()

    os.chdir(ROOT)

    if args.fix:
        run_autofix()
        if not args.tool:
            return 0

    tools_to_run = [args.tool] if args.tool else _ALL_TOOLS
    results: Dict[str, ToolResult] = {}

    for name in tools_to_run:
        if not args.json:
            print(f"  Running {name}…", end="", flush=True)
        tr = _TOOL_MAP[name]()
        results[name] = tr
        if not args.json:
            print(f" {tr.error_count}E {tr.warning_count}W  ({tr.duration_s:.1f}s)")

    report = build_report(results)
    save_report(report)

    if not args.json:
        print_report(report)

    # Exit non-zero only on hard errors (pylint/mypy/bandit found critical issues)
    critical = (
        results.get("pylint",  ToolResult("", False, 0, 0)).error_count
        + results.get("mypy",  ToolResult("", False, 0, 0)).error_count
        + results.get("bandit", ToolResult("", False, 0, 0)).error_count
    )
    return 1 if critical > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
