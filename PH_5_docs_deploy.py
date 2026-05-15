"""
PH_5_docs_deploy.py -- Production Hardening: Documentation & Deployment Runner

Produces a full deployment readiness assessment:
  1. Config audit     -- validate environment configuration
  2. Health checks    -- verify all system components
  3. Startup checks   -- pre-flight validation
  4. API inventory    -- enumerate all registered Flask routes
  5. Package audit    -- check required dependencies are installed

Usage:
    python PH_5_docs_deploy.py              # full check
    python PH_5_docs_deploy.py --json       # write ph5_deployment_report.json
    python PH_5_docs_deploy.py --api-docs   # also write API_DOCS.md
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent
CORE = ROOT / "core_engine"
OUT = ROOT / "ph5_deployment_report.json"
API_DOCS_OUT = ROOT / "API_DOCS.md"

sys.path.insert(0, str(CORE))

PYTHON = sys.executable


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class CheckItem:
    category: str
    name: str
    passed: bool
    detail: str
    severity: str = "FAIL"   # FAIL | WARN | INFO

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "name": self.name,
            "passed": self.passed,
            "severity": self.severity if not self.passed else "OK",
            "detail": self.detail,
        }


@dataclass
class DeploymentReport:
    generated_at: str
    python_version: str
    items: List[CheckItem] = field(default_factory=list)
    gate_passed: bool = True
    failing_gates: List[str] = field(default_factory=list)

    @property
    def fail_count(self) -> int:
        return sum(1 for i in self.items if not i.passed and i.severity == "FAIL")

    @property
    def warn_count(self) -> int:
        return sum(1 for i in self.items if not i.passed and i.severity == "WARN")

    @property
    def pass_count(self) -> int:
        return sum(1 for i in self.items if i.passed)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sep(char: str = "=", width: int = 70) -> str:
    return char * width


def _ok(category: str, name: str, detail: str) -> CheckItem:
    return CheckItem(category, name, True, detail, "INFO")


def _fail(category: str, name: str, detail: str, severity: str = "FAIL") -> CheckItem:
    return CheckItem(category, name, False, detail, severity)


# ---------------------------------------------------------------------------
# 1. Config audit
# ---------------------------------------------------------------------------

def audit_config() -> List[CheckItem]:
    print("\n[1/5] Config audit...")
    items: List[CheckItem] = []

    try:
        from deployment.config import load_config, ConfigValidator
        cfg = load_config()
        issues = ConfigValidator.validate(cfg)
        if issues:
            for fname, msg in issues:
                items.append(_fail("config", fname, msg, "WARN"))
        else:
            items.append(_ok("config", "validation", "All config fields valid"))

        # Specific checks
        if not cfg.secret_key:
            items.append(_fail("config", "secret_key",
                               "EXPERT_SMART_SECRET_KEY not set -- required for production", "WARN"))
        else:
            items.append(_ok("config", "secret_key", "Secret key is set"))

        if cfg.debug:
            items.append(_fail("config", "debug_mode",
                               "debug=True -- must be False in production", "WARN"))
        else:
            items.append(_ok("config", "debug_mode", "debug=False"))

        items.append(_ok("config", "load_config", f"Config loaded OK (port={cfg.port})"))

    except Exception as exc:
        items.append(_fail("config", "load_config", str(exc)))

    return items


# ---------------------------------------------------------------------------
# 2. Health checks
# ---------------------------------------------------------------------------

def run_health_checks() -> List[CheckItem]:
    print("\n[2/5] Health checks...")
    items: List[CheckItem] = []

    try:
        from deployment.health import HealthChecker, HealthStatus, disk_space_check, import_check

        hc = HealthChecker(timeout_seconds=5.0)
        hc.register_fn("disk_space", disk_space_check(".", warn_pct=80.0, crit_pct=95.0))
        hc.register_fn("import:flask", import_check("flask"))
        hc.register_fn("import:waitress", import_check("waitress"))
        hc.register_fn("import:openpyxl", import_check("openpyxl"))
        hc.register_fn("import:pandas", import_check("pandas"))

        result = hc.run_all()

        for name, comp in result["checks"].items():
            if comp["status"] == HealthStatus.HEALTHY:
                items.append(_ok("health", name, comp.get("detail", "healthy")))
            elif comp["status"] == HealthStatus.DEGRADED:
                items.append(_fail("health", name, comp.get("detail", "degraded"), "WARN"))
            else:
                items.append(_fail("health", name, comp.get("error", "unhealthy"), "WARN"))

    except Exception as exc:
        items.append(_fail("health", "health_checker", str(exc)))

    return items


# ---------------------------------------------------------------------------
# 3. Startup validation
# ---------------------------------------------------------------------------

def run_startup_checks() -> List[CheckItem]:
    print("\n[3/5] Startup checks...")
    items: List[CheckItem] = []

    try:
        from deployment.startup import StartupValidator, CheckSeverity

        v = StartupValidator()
        v.add_python_version_check(3, 9)
        v.add_file_check(str(CORE / "bridge_api.py"), CheckSeverity.FAIL)
        v.add_directory_check(str(ROOT / "frontend"), CheckSeverity.WARN)
        v.add_import_check("flask", CheckSeverity.FAIL)
        v.add_import_check("waitress", CheckSeverity.WARN)
        v.add_env_var_check("EXPERT_SMART_SECRET_KEY", CheckSeverity.WARN)

        report = v.run()
        for check in report.checks:
            if check.passed:
                items.append(_ok("startup", check.name, check.message))
            else:
                items.append(_fail("startup", check.name, check.message,
                                   check.severity if check.severity != "INFO" else "WARN"))

    except Exception as exc:
        items.append(_fail("startup", "startup_validator", str(exc)))

    return items


# ---------------------------------------------------------------------------
# 4. Package audit
# ---------------------------------------------------------------------------

REQUIRED_PACKAGES: List[Tuple[str, str]] = [
    ("flask", "FAIL"),
    ("waitress", "WARN"),
    ("openpyxl", "WARN"),
    ("pandas", "WARN"),
    ("httpx", "WARN"),
    ("fastmcp", "WARN"),
    ("pytest", "WARN"),
    ("black", "INFO"),
    ("isort", "INFO"),
    ("bandit", "INFO"),
    ("safety", "INFO"),
]


def audit_packages() -> List[CheckItem]:
    print("\n[4/5] Package audit...")
    items: List[CheckItem] = []

    for pkg, severity in REQUIRED_PACKAGES:
        try:
            mod = importlib.import_module(pkg)
            version = getattr(mod, "__version__", "unknown")
            items.append(_ok("packages", pkg, f"{pkg}=={version}"))
        except ImportError:
            items.append(_fail("packages", pkg, f"{pkg} not installed", severity))

    return items


# ---------------------------------------------------------------------------
# 5. API inventory
# ---------------------------------------------------------------------------

def inventory_api() -> List[CheckItem]:
    print("\n[5/5] API inventory...")
    items: List[CheckItem] = []

    try:
        import ast
        bridge_path = CORE / "bridge_api.py"
        if not bridge_path.exists():
            items.append(_fail("api", "bridge_api.py", "File not found"))
            return items

        source = bridge_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)

        route_count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for deco in node.decorator_list:
                    if isinstance(deco, ast.Call):
                        func = deco.func
                        if isinstance(func, ast.Attribute) and func.attr == "route":
                            route_count += 1
                            break

        items.append(_ok("api", "route_count", f"{route_count} Flask routes registered"))

        # Check key endpoints exist by scanning for the route string
        KEY_ROUTES = [
            "/api/advisor/health",
            "/api/valuation/batch",
            "/api/agent/chat",
        ]
        for route in KEY_ROUTES:
            if route in source:
                items.append(_ok("api", route, f"Route present"))
            else:
                items.append(_fail("api", route, "Route not found in bridge_api.py", "WARN"))

    except Exception as exc:
        items.append(_fail("api", "inventory", str(exc)))

    return items


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def build_report(all_items: List[CheckItem]) -> DeploymentReport:
    failing = [f"{i.category}/{i.name}: {i.detail}"
               for i in all_items if not i.passed and i.severity == "FAIL"]
    rep = DeploymentReport(
        generated_at=datetime.now().isoformat(timespec="seconds"),
        python_version=sys.version.split()[0],
        items=all_items,
        gate_passed=len(failing) == 0,
        failing_gates=failing,
    )
    return rep


def print_report(rep: DeploymentReport) -> None:
    print(f"\n{_sep()}")
    print("  PH.5 DEPLOYMENT READINESS REPORT")
    print(f"  Generated : {rep.generated_at}")
    print(f"  Python    : {rep.python_version}")
    print(_sep())

    current_cat = ""
    for item in rep.items:
        if item.category != current_cat:
            print(f"\n  -- {item.category.upper()} --")
            current_cat = item.category
        icon = "OK  " if item.passed else ("FAIL" if item.severity == "FAIL" else "WARN")
        print(f"  [{icon}] {item.name:<40} {item.detail[:50]}")

    print(f"\n{_sep()}")
    print(f"  TOTAL: {rep.pass_count} pass  {rep.warn_count} warn  {rep.fail_count} fail")
    if rep.gate_passed:
        print("  GATE: PASSED -- ready to deploy")
    else:
        print("  GATE: FAILED")
        for g in rep.failing_gates:
            print(f"    - {g}")
    print(_sep())


def save_report(rep: DeploymentReport) -> None:
    OUT.write_text(
        json.dumps({
            "generated_at": rep.generated_at,
            "python_version": rep.python_version,
            "gate_passed": rep.gate_passed,
            "pass": rep.pass_count,
            "warn": rep.warn_count,
            "fail": rep.fail_count,
            "failing_gates": rep.failing_gates,
            "checks": [i.to_dict() for i in rep.items],
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\n  Report saved -> {OUT.name}")


# ---------------------------------------------------------------------------
# API Docs generator
# ---------------------------------------------------------------------------

def generate_api_docs() -> None:
    """Write a Markdown API reference by parsing bridge_api.py route decorators."""
    import re

    bridge_path = CORE / "bridge_api.py"
    if not bridge_path.exists():
        print("  [SKIP] bridge_api.py not found -- cannot generate API docs")
        return

    source = bridge_path.read_text(encoding="utf-8", errors="replace")
    lines = source.splitlines()

    # Find @app.route(...) + function name + first docstring
    route_re = re.compile(r'''@app\.route\(["']([^"']+)["'](?:.*methods=\[([^\]]+)\])?\)''')
    func_re = re.compile(r'^def\s+(\w+)\s*\(')

    entries = []
    i = 0
    while i < len(lines):
        m = route_re.search(lines[i])
        if m:
            path = m.group(1)
            methods_raw = m.group(2) or '"GET"'
            methods = [x.strip().strip('"\'') for x in methods_raw.split(",")]
            # Look for function def within next 3 lines
            fn_name = ""
            docstring = ""
            for j in range(i + 1, min(i + 4, len(lines))):
                fm = func_re.match(lines[j])
                if fm:
                    fn_name = fm.group(1)
                    # Look for docstring
                    if j + 1 < len(lines) and '"""' in lines[j + 1]:
                        doc_lines = []
                        for k in range(j + 1, min(j + 8, len(lines))):
                            doc_lines.append(lines[k].strip().strip('"""').strip())
                            if k > j + 1 and '"""' in lines[k]:
                                break
                        docstring = " ".join(l for l in doc_lines if l)
                    break
            entries.append((path, methods, fn_name, docstring))
        i += 1

    # Write Markdown
    doc_lines = [
        "# Expert Smart — API Reference",
        "",
        f"> Auto-generated by PH_5_docs_deploy.py on {datetime.now().strftime('%Y-%m-%d')}",
        "",
        f"Total routes: **{len(entries)}**",
        "",
        "---",
        "",
    ]

    for path, methods, fn_name, docstring in entries:
        methods_str = " / ".join(f"`{m}`" for m in methods)
        doc_lines.append(f"## `{path}`")
        doc_lines.append(f"**Methods**: {methods_str}  ")
        if fn_name:
            doc_lines.append(f"**Handler**: `{fn_name}`  ")
        if docstring:
            doc_lines.append(f"**Description**: {docstring[:200]}  ")
        doc_lines.append("")

    API_DOCS_OUT.write_text("\n".join(doc_lines), encoding="utf-8")
    print(f"  API docs saved -> {API_DOCS_OUT.name}  ({len(entries)} routes)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="PH.5 Deployment Readiness Runner")
    ap.add_argument("--api-docs", action="store_true", help="Also generate API_DOCS.md")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    all_items: List[CheckItem] = []
    all_items.extend(audit_config())
    all_items.extend(run_health_checks())
    all_items.extend(run_startup_checks())
    all_items.extend(audit_packages())
    all_items.extend(inventory_api())

    rep = build_report(all_items)
    print_report(rep)
    save_report(rep)

    if args.api_docs:
        print("\n  Generating API documentation...")
        generate_api_docs()

    return 0 if rep.gate_passed else 1


if __name__ == "__main__":
    sys.exit(main())
