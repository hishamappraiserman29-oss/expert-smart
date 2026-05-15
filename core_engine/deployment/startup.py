"""
startup.py — PH.5 Pre-Flight Startup Validator

Runs a sequence of checks before the server accepts requests.
Any FAIL check causes the server to abort with a clear error message.
WARN checks are reported but do not block startup.

Classes:
    CheckSeverity    — FAIL | WARN | INFO
    StartupCheck     — one pre-flight check result
    StartupReport    — aggregated result of all checks
    StartupValidator — register and run all checks
"""

from __future__ import annotations

import importlib
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# CheckSeverity
# ---------------------------------------------------------------------------

class CheckSeverity(str, Enum):
    FAIL = "FAIL"   # blocks startup
    WARN = "WARN"   # logged but continues
    INFO = "INFO"   # informational only


# ---------------------------------------------------------------------------
# StartupCheck
# ---------------------------------------------------------------------------

@dataclass
class StartupCheck:
    """Result of one pre-flight check."""

    name: str
    severity: str       # CheckSeverity value if failed; INFO if passed
    passed: bool
    message: str
    elapsed_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "severity": self.severity if not self.passed else "OK",
            "message": self.message,
            "elapsed_ms": round(self.elapsed_ms, 2),
        }


# ---------------------------------------------------------------------------
# StartupReport
# ---------------------------------------------------------------------------

@dataclass
class StartupReport:
    """Aggregated result of all startup checks."""

    checks: List[StartupCheck] = field(default_factory=list)
    ok_to_start: bool = True        # False if any FAIL check failed

    @property
    def fail_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed and c.severity == CheckSeverity.FAIL)

    @property
    def warn_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed and c.severity == CheckSeverity.WARN)

    @property
    def pass_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok_to_start": self.ok_to_start,
            "pass": self.pass_count,
            "warn": self.warn_count,
            "fail": self.fail_count,
            "checks": [c.to_dict() for c in self.checks],
        }

    def format_summary(self) -> str:
        lines = [
            f"Startup validation: {'OK' if self.ok_to_start else 'FAILED'}",
            f"  {self.pass_count} passed, {self.warn_count} warnings, {self.fail_count} failed",
        ]
        for c in self.checks:
            icon = "OK  " if c.passed else ("FAIL" if c.severity == CheckSeverity.FAIL else "WARN")
            lines.append(f"  [{icon}] {c.name}: {c.message}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# StartupValidator
# ---------------------------------------------------------------------------

class StartupValidator:
    """
    Register named pre-flight checks and run them in order.

    Each check is a zero-argument callable that returns a (bool, str) tuple:
        (True, "description of what passed")
        (False, "description of what failed")

    Checks are run in registration order.  Any FAIL check sets
    ``report.ok_to_start = False`` but all checks still run (so you see
    all problems at once, not just the first one).

    Built-in checks are registered via the ``add_*`` convenience methods.
    """

    def __init__(self) -> None:
        # (name, callable, severity_if_fail)
        self._checks: List[Tuple[str, Callable[[], Tuple[bool, str]], str]] = []

    # -- Registration ---------------------------------------------------------

    def add_check(
        self,
        name: str,
        fn: Callable[[], Tuple[bool, str]],
        severity: str = CheckSeverity.FAIL,
    ) -> "StartupValidator":
        """Register a custom check function. Returns self for chaining."""
        self._checks.append((name, fn, severity))
        return self

    # -- Built-in checks ------------------------------------------------------

    def add_python_version_check(self, min_major: int = 3, min_minor: int = 9) -> "StartupValidator":
        def _check() -> Tuple[bool, str]:
            major, minor = sys.version_info[:2]
            if (major, minor) < (min_major, min_minor):
                return False, f"Python {major}.{minor} < required {min_major}.{min_minor}"
            return True, f"Python {major}.{minor}"
        return self.add_check("python_version", _check, CheckSeverity.FAIL)

    def add_directory_check(self, path: str, create: bool = False) -> "StartupValidator":
        def _check() -> Tuple[bool, str]:
            import os
            p = Path(path)
            if not p.exists():
                if create:
                    try:
                        p.mkdir(parents=True, exist_ok=True)
                        return True, f"Created: {path}"
                    except OSError as exc:
                        return False, f"Cannot create {path}: {exc}"
                return False, f"Does not exist: {path}"
            if not p.is_dir():
                return False, f"Not a directory: {path}"
            if not os.access(str(p), os.W_OK):
                return False, f"Not writable: {path}"
            return True, f"OK: {path}"
        return self.add_check(f"directory:{path}", _check, CheckSeverity.FAIL)

    def add_import_check(self, module: str, severity: str = CheckSeverity.FAIL) -> "StartupValidator":
        def _check() -> Tuple[bool, str]:
            try:
                importlib.import_module(module)
                return True, f"Import OK: {module}"
            except ImportError as exc:
                return False, f"Cannot import {module}: {exc}"
        return self.add_check(f"import:{module}", _check, severity)

    def add_env_var_check(self, var_name: str, severity: str = CheckSeverity.WARN) -> "StartupValidator":
        def _check() -> Tuple[bool, str]:
            import os
            val = os.environ.get(var_name, "")
            if not val:
                return False, f"Environment variable {var_name} is not set"
            return True, f"{var_name} is set"
        return self.add_check(f"env:{var_name}", _check, severity)

    def add_file_check(self, path: str, severity: str = CheckSeverity.FAIL) -> "StartupValidator":
        def _check() -> Tuple[bool, str]:
            p = Path(path)
            if not p.exists():
                return False, f"File not found: {path}"
            if not p.is_file():
                return False, f"Not a file: {path}"
            return True, f"Found: {path} ({p.stat().st_size:,} bytes)"
        return self.add_check(f"file:{path}", _check, severity)

    def add_port_free_check(self, port: int, host: str = "127.0.0.1") -> "StartupValidator":
        def _check() -> Tuple[bool, str]:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex((host, port))
            if result == 0:
                return False, f"Port {port} is already in use on {host}"
            return True, f"Port {port} is available"
        return self.add_check(f"port:{port}", _check, CheckSeverity.WARN)

    # -- Runner ---------------------------------------------------------------

    def run(self) -> StartupReport:
        """Execute all registered checks in order and return a StartupReport."""
        report = StartupReport()

        for name, fn, severity in self._checks:
            t0 = time.perf_counter()
            try:
                passed, message = fn()
            except Exception as exc:
                passed = False
                message = f"Check raised exception: {exc}"
            elapsed_ms = (time.perf_counter() - t0) * 1000

            check = StartupCheck(
                name=name,
                passed=passed,
                severity=severity if not passed else CheckSeverity.INFO,
                message=message,
                elapsed_ms=elapsed_ms,
            )
            report.checks.append(check)

            if not passed and severity == CheckSeverity.FAIL:
                report.ok_to_start = False

        return report


# ---------------------------------------------------------------------------
# Default validator factory
# ---------------------------------------------------------------------------

def default_validator(root_dir: str) -> StartupValidator:
    """
    Build a StartupValidator with the standard Expert Smart checks.

    Parameters
    ----------
    root_dir : project root (where bridge_api.py lives)
    """
    root = Path(root_dir)
    core = root / "core_engine"

    v = StartupValidator()
    v.add_python_version_check(3, 9)
    v.add_file_check(str(core / "bridge_api.py"), severity=CheckSeverity.FAIL)
    v.add_directory_check(str(root / "frontend"), create=False)
    v.add_import_check("flask", CheckSeverity.FAIL)
    v.add_import_check("waitress", CheckSeverity.WARN)
    v.add_import_check("openpyxl", CheckSeverity.WARN)
    v.add_env_var_check("EXPERT_SMART_SECRET_KEY", CheckSeverity.WARN)
    v.add_port_free_check(5000)
    return v
