"""
secrets_scanner.py — P3 output security scanner (O-04, G-07).

Scans any dict/list/str for:
  - Absolute filesystem paths (Windows and Unix)
  - API keys / bearer tokens / connection strings
  - TAQEEM compliance claims (G-07)

All functions are pure Python with no external dependencies.
Returns findings as a list of dicts; empty list = clean.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

_WINDOWS_PATH  = re.compile(r'[A-Za-z]:\\(?:[^\s"\'<>{}\|\\]+\\)+', re.IGNORECASE)
_UNIX_PATH     = re.compile(r'/(?:home|usr|etc|var|root|srv|opt|mnt)/\S+')
_CONN_STRING   = re.compile(
    r'(?:postgresql|mysql|mongodb|redis|mssql)://[^\s"\']+', re.IGNORECASE
)
_BEARER_TOKEN  = re.compile(r'Bearer\s+[A-Za-z0-9\-_.=]{20,}', re.IGNORECASE)
_API_KEY       = re.compile(
    r'(?:api[_\-]?key|secret[_\-]?key|access[_\-]?token|private[_\-]?key)'
    r'\s*[=:]\s*["\']?[A-Za-z0-9\-_.]{16,}',
    re.IGNORECASE,
)
_TAQEEM_CLAIM  = re.compile(r'TAQEEM[\s\-]*complian', re.IGNORECASE)

_FORBIDDEN_TERMS = {
    # User-facing output must not contain these (O-02 / G-08)
    "shap",
    "hyperparameter",
    "basel",
    "ltv",
    "loan.to.value",
    "cod",
    "prd",
    "prb",
}

_COMPILED_FORBIDDEN = re.compile(
    r'\b(' + '|'.join(re.escape(t) for t in _FORBIDDEN_TERMS) + r')\b',
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_strings(value: Any, path: str = "") -> List[tuple[str, str]]:
    """Recursively walk a nested structure and yield (path, string_value)."""
    results: List[tuple[str, str]] = []
    if isinstance(value, str):
        results.append((path, value))
    elif isinstance(value, dict):
        for k, v in value.items():
            results.extend(_extract_strings(v, f"{path}.{k}" if path else k))
    elif isinstance(value, (list, tuple)):
        for i, item in enumerate(value):
            results.extend(_extract_strings(item, f"{path}[{i}]"))
    return results


def _check_patterns(text: str, field: str, findings: List[Dict]) -> None:
    for pattern, kind in (
        (_WINDOWS_PATH,  "windows_path"),
        (_UNIX_PATH,     "unix_path"),
        (_CONN_STRING,   "connection_string"),
        (_BEARER_TOKEN,  "bearer_token"),
        (_API_KEY,       "api_key"),
        (_TAQEEM_CLAIM,  "taqeem_compliance_claim"),
    ):
        match = pattern.search(text)
        if match:
            findings.append({
                "field":   field,
                "kind":    kind,
                "excerpt": text[max(0, match.start() - 10):match.end() + 10].strip(),
            })


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scan_output(data: Any) -> List[Dict[str, str]]:
    """
    Scan any dict/list/string for secrets or forbidden content.
    Returns a list of finding dicts (empty = clean).
    Each finding: {"field": str, "kind": str, "excerpt": str}
    """
    findings: List[Dict] = []
    for field, text in _extract_strings(data):
        _check_patterns(text, field, findings)
    return findings


def scan_for_forbidden_terms(text: str) -> List[str]:
    """
    Check a plain string for technical terms that must not appear in
    user-facing output (O-02).
    Returns list of matched terms (empty = clean).
    """
    return list({m.group(0).lower() for m in _COMPILED_FORBIDDEN.finditer(text)})


def check_taqeem_claim(text: str) -> bool:
    """
    Return True if the text contains a TAQEEM compliance claim (G-07 violation).
    A True result means the output MUST be rejected / corrected.
    """
    return bool(_TAQEEM_CLAIM.search(text))


def verify_file_signature(data: bytes, file_type: str) -> bool:
    """
    Verify that a file's leading bytes match the expected magic bytes (O-06).
    Supported file_type values: 'html', 'xlsx', 'pdf'.
    Returns True if the signature matches, False otherwise.
    """
    signatures: Dict[str, bytes] = {
        "html": b"<!DOCTYPE",
        "xlsx": b"PK\x03\x04",
        "pdf":  b"%PDF",
    }
    expected = signatures.get(file_type.lower())
    if expected is None:
        return False
    return data[:len(expected)] == expected


def assert_clean(data: Any, context: str = "") -> None:
    """
    Raise ValueError if scan_output finds any issues.
    Convenience wrapper for use in tests and pre-flight checks.
    """
    findings = scan_output(data)
    if findings:
        detail = "; ".join(f"{f['field']}:{f['kind']}" for f in findings)
        raise ValueError(f"Output security violation{' in ' + context if context else ''}: {detail}")
