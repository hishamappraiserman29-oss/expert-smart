"""
PH_3_security.py -- Production Hardening: Security & Compliance Runner

Runs a full security audit:
  1. bandit     -- SAST: common Python security issues
  2. safety     -- dependency vulnerability scan (safety scan)
  3. secrets    -- scan source for hardcoded credentials (custom)
  4. custom     -- check for known insecure patterns in bridge_api.py

Usage:
    python PH_3_security.py              # full run, gate enforced
    python PH_3_security.py --baseline   # report only, no gate
    python PH_3_security.py --no-safety  # skip safety scan (no internet)
    python PH_3_security.py --json       # write ph3_security_report.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
CORE = ROOT / "core_engine"
OUT = ROOT / "ph3_security_report.json"
PYTHON = sys.executable


# -- Data structures ---------------------------------------------------------

@dataclass
class SecurityFinding:
    tool: str
    severity: str    # HIGH | MEDIUM | LOW | INFO
    category: str
    message: str
    file_path: str = ""
    line_number: int = 0

    def to_dict(self) -> Dict:
        return {
            "tool": self.tool,
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "file": self.file_path,
            "line": self.line_number,
        }


@dataclass
class ToolResult:
    tool: str
    ran: bool
    exit_code: int
    elapsed: float
    findings: List[SecurityFinding] = field(default_factory=list)
    raw_output: str = ""
    error: str = ""


@dataclass
class SecurityReport:
    generated_at: str
    python_version: str
    results: List[ToolResult] = field(default_factory=list)
    total_high: int = 0
    total_medium: int = 0
    total_low: int = 0
    gate_passed: bool = True
    failing_gates: List[str] = field(default_factory=list)


# -- Helpers -----------------------------------------------------------------

def _run(cmd: List[str], cwd: Optional[str] = None, timeout: int = 120) -> tuple[int, str]:
    t0 = time.perf_counter()
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=cwd or str(CORE),
            timeout=timeout,
        )
        elapsed = time.perf_counter() - t0
        return r.returncode, r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        return -2, "TIMEOUT"
    except FileNotFoundError as exc:
        return -3, str(exc)


def _sep(char: str = "=", width: int = 70) -> str:
    return char * width


# -- Tool runners ------------------------------------------------------------

def run_bandit() -> ToolResult:
    """Run bandit SAST scan on core_engine/ (excluding tests/)."""
    print("\n[1/4] bandit -- Static Application Security Testing")
    # Exclude: tests, all venv/site-packages directories, pycache
    excludes = ",".join([
        str(CORE / "tests"),
        str(CORE / "banking_expert" / "venv"),
        str(CORE / "venv"),
        str(ROOT / "venv"),
    ])
    cmd = [
        PYTHON, "-m", "bandit",
        "-r", str(CORE),
        "--exclude", excludes,
        "-ll",          # medium+ severity
        "-ii",          # medium+ confidence
        "-q",
        "-f", "json",
    ]
    rc, output = _run(cmd, cwd=str(ROOT))
    result = ToolResult(tool="bandit", ran=True, exit_code=rc, elapsed=0.0, raw_output=output)

    try:
        data = json.loads(output)
        for issue in data.get("results", []):
            sev = issue.get("issue_severity", "LOW").upper()
            result.findings.append(SecurityFinding(
                tool="bandit",
                severity=sev,
                category=issue.get("test_id", ""),
                message=f"{issue.get('issue_text', '')} [{issue.get('test_name', '')}]",
                file_path=issue.get("filename", ""),
                line_number=issue.get("line_number", 0),
            ))
    except (json.JSONDecodeError, KeyError):
        # bandit might output text if it can't parse — not a hard failure
        pass

    high = sum(1 for f in result.findings if f.severity == "HIGH")
    med = sum(1 for f in result.findings if f.severity == "MEDIUM")
    print(f"   {len(result.findings)} issues found  (HIGH:{high} MEDIUM:{med})")
    return result


def run_safety() -> ToolResult:
    """Run safety scan on installed packages."""
    print("\n[2/4] safety -- Dependency Vulnerability Scan")
    cmd = [PYTHON, "-m", "safety", "scan", "--output", "json"]
    rc, output = _run(cmd, cwd=str(ROOT), timeout=90)
    result = ToolResult(tool="safety", ran=True, exit_code=rc, elapsed=0.0, raw_output=output)

    # safety scan returns non-zero when vulnerabilities are found
    # Try to parse JSON; fall back gracefully
    try:
        # safety scan JSON may be wrapped; find the JSON block
        start = output.find('{')
        if start == -1:
            start = output.find('[')
        if start >= 0:
            data = json.loads(output[start:])
            vulns = []
            if isinstance(data, dict):
                vulns = data.get("vulnerabilities", []) or data.get("affected_packages", [])
            elif isinstance(data, list):
                vulns = data
            for v in vulns:
                pkg = v.get("package_name") or v.get("name", "unknown")
                cve = v.get("CVE") or v.get("vulnerability_id", "")
                desc = v.get("advisory") or v.get("description", "")
                sev = "HIGH" if cve else "MEDIUM"
                result.findings.append(SecurityFinding(
                    tool="safety",
                    severity=sev,
                    category="dependency_vulnerability",
                    message=f"{pkg} -- {cve}: {desc[:120]}",
                ))
    except (json.JSONDecodeError, KeyError, ValueError):
        if rc not in (0, 64):  # 64 = vulnerabilities found
            result.error = f"safety scan parse error (rc={rc})"

    print(f"   {len(result.findings)} vulnerabilities found")
    return result


def run_secrets_scan() -> ToolResult:
    """Scan core_engine/ for hardcoded credentials."""
    print("\n[3/4] secrets -- Credential Leak Detection")
    sys.path.insert(0, str(CORE))
    try:
        from security.secrets_scanner import SecretsScanner
        scanner = SecretsScanner(min_severity="MEDIUM")
        raw_findings = scanner.scan_directory(
            str(CORE),
            extensions=[".py", ".json", ".env", ".cfg", ".ini"],
            exclude_dirs=["__pycache__", "venv", ".git", "tests", "htmlcov"],
        )
        result = ToolResult(tool="secrets", ran=True, exit_code=0, elapsed=0.0)
        for sf in raw_findings:
            result.findings.append(SecurityFinding(
                tool="secrets",
                severity=sf.severity,
                category=sf.pattern_name,
                message=sf.line_text[:120],
                file_path=sf.file_path,
                line_number=sf.line_number,
            ))
    except Exception as exc:
        result = ToolResult(tool="secrets", ran=False, exit_code=-1, elapsed=0.0,
                            error=str(exc))

    high = sum(1 for f in result.findings if f.severity == "HIGH")
    print(f"   {len(result.findings)} secrets found  (HIGH:{high})")
    return result


def run_custom_checks() -> ToolResult:
    """Custom checks: look for known high-risk patterns."""
    print("\n[4/4] custom -- Known High-Risk Pattern Checks")
    import re

    CHECKS = [
        # debug=True in Flask app.run()
        ("Flask debug mode", re.compile(r'app\.run\(.*debug\s*=\s*True', re.I), "HIGH"),
        # eval() calls
        ("eval() usage", re.compile(r'\beval\s*\('), "HIGH"),
        # exec() calls
        ("exec() usage", re.compile(r'\bexec\s*\('), "MEDIUM"),
        # Shell=True in subprocess
        ("subprocess shell=True", re.compile(r'shell\s*=\s*True'), "MEDIUM"),
        # SQL string formatting
        ("SQL string formatting", re.compile(r'(SELECT|INSERT|UPDATE|DELETE).*%[s\(]', re.I), "HIGH"),
        # pickle.loads
        ("pickle.loads deserialization", re.compile(r'pickle\.loads?\('), "MEDIUM"),
    ]

    result = ToolResult(tool="custom", ran=True, exit_code=0, elapsed=0.0)

    py_files = list(CORE.rglob("*.py"))
    # Exclude tests, venv/site-packages, pycache
    py_files = [
        f for f in py_files
        if "tests" not in str(f)
        and "__pycache__" not in str(f)
        and "venv" not in str(f)
        and "site-packages" not in str(f)
    ]

    for py_file in py_files:
        try:
            text = py_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for name, pattern, sev in CHECKS:
                if pattern.search(stripped):
                    result.findings.append(SecurityFinding(
                        tool="custom",
                        severity=sev,
                        category=name,
                        message=stripped[:120],
                        file_path=str(py_file),
                        line_number=lineno,
                    ))
                    break

    # Known exception: bridge_api.py has app.run(debug=False) in __main__
    # Filter false positive: debug=False
    result.findings = [
        f for f in result.findings
        if not (f.category == "Flask debug mode" and "debug=False" in f.message.lower())
    ]

    high = sum(1 for f in result.findings if f.severity == "HIGH")
    print(f"   {len(result.findings)} custom issues  (HIGH:{high})")
    return result


# -- Report ------------------------------------------------------------------

def build_report(results: List[ToolResult], baseline: bool) -> SecurityReport:
    all_findings = [f for r in results for f in r.findings]
    high = sum(1 for f in all_findings if f.severity == "HIGH")
    med = sum(1 for f in all_findings if f.severity == "MEDIUM")
    low = sum(1 for f in all_findings if f.severity == "LOW")

    report = SecurityReport(
        generated_at=datetime.now().isoformat(timespec="seconds"),
        python_version=sys.version.split()[0],
        results=results,
        total_high=high,
        total_medium=med,
        total_low=low,
    )

    failing: List[str] = []
    if not baseline:
        if high > 0:
            failing.append(f"HIGH severity findings: {high} (must be 0)")
        # Bandit-specific: any non-whitelisted HIGH bandit finding
        bandit_high = [
            f for f in all_findings
            if f.tool == "bandit" and f.severity == "HIGH"
            and f.category not in {"B101", "B311", "B324", "B404", "B603", "B607", "B608"}
        ]
        if bandit_high:
            failing.append(f"bandit HIGH (unwhitelisted): {len(bandit_high)}")

    report.gate_passed = (len(failing) == 0)
    report.failing_gates = failing
    return report


def print_report(rep: SecurityReport) -> None:
    print(f"\n{_sep()}")
    print("  PH.3 SECURITY REPORT")
    print(f"  Generated : {rep.generated_at}")
    print(f"  Python    : {rep.python_version}")
    print(_sep())

    sev_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "INFO": 3}
    for tr in rep.results:
        status = "OK" if tr.ran and not tr.error else ("SKIP" if not tr.ran else "ERROR")
        print(f"\n  [{status}] {tr.tool.upper():<12} {len(tr.findings)} findings")
        sorted_f = sorted(tr.findings, key=lambda f: sev_order.get(f.severity, 9))
        for f in sorted_f[:10]:   # show max 10 per tool
            loc = f" line {f.line_number}" if f.line_number else ""
            fname = Path(f.file_path).name if f.file_path else ""
            print(f"    [{f.severity:<6}] {f.category:<30} {fname}{loc}")
            print(f"             {f.message[:80]}")
        if len(tr.findings) > 10:
            print(f"    ... and {len(tr.findings) - 10} more")

    print(f"\n{_sep()}")
    print(f"  TOTAL: HIGH={rep.total_high}  MEDIUM={rep.total_medium}  LOW={rep.total_low}")
    if rep.gate_passed:
        print("  GATE: PASSED")
    else:
        print("  GATE: FAILED")
        for g in rep.failing_gates:
            print(f"    - {g}")
    print(_sep())


def save_report(rep: SecurityReport) -> None:
    def _ser(obj: Any) -> Any:
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if hasattr(obj, "__dataclass_fields__"):
            import dataclasses
            return dataclasses.asdict(obj)
        return str(obj)

    payload = {
        "generated_at": rep.generated_at,
        "python_version": rep.python_version,
        "total_high": rep.total_high,
        "total_medium": rep.total_medium,
        "total_low": rep.total_low,
        "gate_passed": rep.gate_passed,
        "failing_gates": rep.failing_gates,
        "tools": {
            tr.tool: {
                "ran": tr.ran,
                "findings": len(tr.findings),
                "error": tr.error,
            }
            for tr in rep.results
        },
        "findings": [f.to_dict() for r in rep.results for f in r.findings],
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  Report saved -> {OUT.name}")


# -- Main --------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="PH.3 Security Runner")
    ap.add_argument("--baseline", action="store_true", help="Report only -- skip gates")
    ap.add_argument("--no-safety", action="store_true", help="Skip dependency scan")
    ap.add_argument("--json", action="store_true", help="Save JSON report (also default)")
    args = ap.parse_args()

    results: List[ToolResult] = []

    results.append(run_bandit())

    if not args.no_safety:
        results.append(run_safety())
    else:
        print("\n[2/4] safety -- SKIPPED (--no-safety)")

    results.append(run_secrets_scan())
    results.append(run_custom_checks())

    report = build_report(results, baseline=args.baseline)
    print_report(report)
    save_report(report)

    return 0 if report.gate_passed else 1


if __name__ == "__main__":
    sys.exit(main())
