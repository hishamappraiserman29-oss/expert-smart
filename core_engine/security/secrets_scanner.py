"""
secrets_scanner.py — PH.3 Credential / Secret Leak Scanner

Scans Python source files for patterns that indicate accidental credential
leaks: API keys, passwords, tokens, connection strings, private keys, etc.

Classes:
    SecretFinding  — a single detected credential pattern
    SecretsScanner — scan files, directories, or strings
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------
# Each entry: (label, compiled_pattern, severity)
# severity: "HIGH" | "MEDIUM" | "LOW"
#
# Patterns are intentionally conservative to minimise false positives on
# a real-estate valuation codebase.

_PATTERNS: List[Tuple[str, re.Pattern[str], str]] = [
    # Generic assignment patterns (password=, secret=, api_key=, token=, …)
    (
        'Hardcoded password',
        re.compile(
            r'(?i)(password|passwd|pwd)\s*[=:]\s*["\'][^"\']{4,}["\']',
            re.IGNORECASE,
        ),
        'HIGH',
    ),
    (
        'Hardcoded API key',
        re.compile(
            r'(?i)(api[_-]?key|apikey|app[_-]?key)\s*[=:]\s*["\'][A-Za-z0-9\-_]{8,}["\']',
            re.IGNORECASE,
        ),
        'HIGH',
    ),
    (
        'Hardcoded secret',
        re.compile(
            r'(?i)(secret[_-]?key|client[_-]?secret)\s*[=:]\s*["\'][^"\']{6,}["\']',
            re.IGNORECASE,
        ),
        'HIGH',
    ),
    (
        'Hardcoded token',
        re.compile(
            r'(?i)(access[_-]?token|auth[_-]?token|bearer[_-]?token)\s*[=:]\s*["\'][^"\']{10,}["\']',
            re.IGNORECASE,
        ),
        'HIGH',
    ),
    # Cloud provider key patterns
    (
        'AWS access key',
        re.compile(r'AKIA[0-9A-Z]{16}'),
        'HIGH',
    ),
    (
        'AWS secret access key',
        re.compile(r'(?i)aws[_-]?secret[_-]?access[_-]?key\s*[=:]\s*["\'][^"\']{20,}["\']'),
        'HIGH',
    ),
    (
        'Google API key',
        re.compile(r'AIza[0-9A-Za-z\-_]{34,}'),
        'HIGH',
    ),
    (
        'Google service account',
        re.compile(r'"private_key"\s*:\s*"-----BEGIN'),
        'HIGH',
    ),
    # Connection strings
    (
        'Database connection string with credentials',
        re.compile(
            r'(?i)(mysql|postgres|postgresql|mongodb|mssql|redis|amqp)://[^:@\s]+:[^@\s]+@',
            re.IGNORECASE,
        ),
        'HIGH',
    ),
    # Private keys / certificates
    (
        'Private key header',
        re.compile(r'-----BEGIN (RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----'),
        'HIGH',
    ),
    # JWT-like tokens (3 base64 segments separated by dots)
    (
        'JWT token',
        re.compile(r'eyJ[A-Za-z0-9\-_=]{10,}\.[A-Za-z0-9\-_=]{10,}\.[A-Za-z0-9\-_.+/=]{10,}'),
        'MEDIUM',
    ),
    # Generic long hex secrets (32+ hex chars assigned to sensitive names)
    (
        'Hardcoded hex secret',
        re.compile(
            r'(?i)(secret|token|key|hash|salt)\s*[=:]\s*["\'][0-9a-f]{32,}["\']',
            re.IGNORECASE,
        ),
        'MEDIUM',
    ),
    # Slack / GitHub tokens
    (
        'Slack token',
        re.compile(r'xox[baprs]-[0-9A-Za-z\-]{10,}'),
        'HIGH',
    ),
    (
        'GitHub token',
        re.compile(r'gh[pousr]_[A-Za-z0-9]{36,}'),
        'HIGH',
    ),
]

# Lines that look like comments describing what to put in an env var, or
# placeholder values — these generate too many false positives.
_PLACEHOLDER_VALUES = frozenset({
    'your_key_here', 'your_secret_here', 'changeme', 'placeholder',
    'example', 'xxxxxxxx', 'xxxxxxxxxx', 'todo', 'fixme',
    '<secret>', '<key>', '<token>', '<password>',
    'secret', 'password', 'key', 'token',  # single generic words
})

_COMMENT_RE = re.compile(r'^\s*#')
_QUOTED_VALUE_RE = re.compile(r'''["']([^"']{1,200})["']''')


# ---------------------------------------------------------------------------
# SecretFinding
# ---------------------------------------------------------------------------

@dataclass
class SecretFinding:
    """A single detected credential pattern in a source file."""

    file_path: str
    line_number: int
    line_text: str      # original line (stripped)
    pattern_name: str
    severity: str       # HIGH | MEDIUM | LOW

    def to_dict(self) -> Dict:
        return {
            'file': self.file_path,
            'line': self.line_number,
            'text': self.line_text[:200],   # cap to avoid huge JSON
            'pattern': self.pattern_name,
            'severity': self.severity,
        }


# ---------------------------------------------------------------------------
# SecretsScanner
# ---------------------------------------------------------------------------

class SecretsScanner:
    """
    Scan Python source files for accidental credential leaks.

    Parameters
    ----------
    skip_comments      : skip lines that start with '#' (default True)
    skip_placeholders  : skip matches whose value looks like a placeholder
                         (default True)
    min_severity       : 'LOW' | 'MEDIUM' | 'HIGH' — skip findings below
                         this severity (default 'LOW' = include all)
    """

    _SEVERITY_ORDER = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2}

    def __init__(
        self,
        skip_comments: bool = True,
        skip_placeholders: bool = True,
        min_severity: str = 'LOW',
    ) -> None:
        self._skip_comments = skip_comments
        self._skip_placeholders = skip_placeholders
        self._min_sev = self._SEVERITY_ORDER.get(min_severity.upper(), 0)

    # -- Scan string ----------------------------------------------------------

    def scan_string(self, text: str, source_label: str = '<string>') -> List[SecretFinding]:
        """Scan raw text for secrets. Returns list of findings."""
        findings: List[SecretFinding] = []
        for lineno, raw_line in enumerate(text.splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            if self._skip_comments and _COMMENT_RE.match(raw_line):
                continue
            for label, pattern, severity in _PATTERNS:
                if self._SEVERITY_ORDER.get(severity, 0) < self._min_sev:
                    continue
                if pattern.search(line):
                    if self._skip_placeholders and self._is_placeholder(line):
                        continue
                    findings.append(SecretFinding(
                        file_path=source_label,
                        line_number=lineno,
                        line_text=line,
                        pattern_name=label,
                        severity=severity,
                    ))
                    break  # only report first matching pattern per line
        return findings

    # -- Scan file ------------------------------------------------------------

    def scan_file(self, path: str) -> List[SecretFinding]:
        """Scan a single file. Returns empty list if unreadable."""
        try:
            text = Path(path).read_text(encoding='utf-8', errors='replace')
        except OSError:
            return []
        return self.scan_string(text, source_label=path)

    # -- Scan directory -------------------------------------------------------

    def scan_directory(
        self,
        directory: str,
        extensions: Optional[List[str]] = None,
        exclude_dirs: Optional[List[str]] = None,
    ) -> List[SecretFinding]:
        """
        Recursively scan all files in *directory*.

        Parameters
        ----------
        extensions   : e.g. ['.py', '.env', '.json'] — None = all files
        exclude_dirs : directory names to skip (e.g. ['__pycache__', 'venv'])
        """
        ext_set = {e.lower() for e in (extensions or [])}
        skip_dirs = set(exclude_dirs or ['__pycache__', 'venv', '.git', 'htmlcov', 'node_modules'])

        findings: List[SecretFinding] = []
        root = Path(directory)

        for p in root.rglob('*'):
            if not p.is_file():
                continue
            # Skip excluded directories
            if any(part in skip_dirs for part in p.parts):
                continue
            if ext_set and p.suffix.lower() not in ext_set:
                continue
            findings.extend(self.scan_file(str(p)))

        return sorted(findings, key=lambda f: (f.file_path, f.line_number))

    # -- Summary --------------------------------------------------------------

    @staticmethod
    def summarize(findings: List[SecretFinding]) -> Dict:
        """Return a summary dict for reporting."""
        high = sum(1 for f in findings if f.severity == 'HIGH')
        medium = sum(1 for f in findings if f.severity == 'MEDIUM')
        low = sum(1 for f in findings if f.severity == 'LOW')
        files = len({f.file_path for f in findings})
        return {
            'total': len(findings),
            'high': high,
            'medium': medium,
            'low': low,
            'affected_files': files,
        }

    # -- Helpers --------------------------------------------------------------

    @staticmethod
    def _is_placeholder(line: str) -> bool:
        """Return True if the VALUE part of the line looks like a placeholder.

        Extracts quoted values rather than checking the whole line, so that
        field names like 'api_key' or 'password' don't produce false positives.
        """
        quoted_values = _QUOTED_VALUE_RE.findall(line)
        if not quoted_values:
            # No quoted value — raw patterns like BEGIN PRIVATE KEY are real findings
            return False
        for val in quoted_values:
            lower_val = val.lower().strip()
            if lower_val in _PLACEHOLDER_VALUES:
                return True
            if lower_val.startswith('your_') or lower_val.startswith('<'):
                return True
        return False
