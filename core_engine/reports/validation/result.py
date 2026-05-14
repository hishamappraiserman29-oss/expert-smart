"""
result.py — Validation result types for EXPERT_SMART report validation.

Three public types:
  Severity         — ERROR / WARNING / INFO
  ValidationIssue  — frozen, bilingual, machine-readable code
  ValidationResult — frozen container with filtering helpers and merge()

Display-only — no computation, no side effects, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


# ── Severity ──────────────────────────────────────────────────────────────────

class Severity(Enum):
    """Impact level of a validation finding."""

    ERROR   = "error"    # blocks report generation
    WARNING = "warning"  # allows generation, flags issue
    INFO    = "info"     # informational / advisory note


# ── ValidationIssue ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ValidationIssue:
    """A single immutable validation finding.

    Attributes:
        field:      Dotted path to the offending field
                    (e.g. "reconciliation.weights.sales").
        severity:   Severity level (ERROR / WARNING / INFO).
        code:       Stable machine-readable code
                    (e.g. "WEIGHTS_SUM_MISMATCH") — never changes between
                    releases so callers can programmatically react.
        message_ar: Human-readable Arabic description — never empty.
        message_en: Human-readable English description — never empty.
    """

    field:      str
    severity:   Severity
    code:       str
    message_ar: str
    message_en: str


# ── ValidationResult ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ValidationResult:
    """Immutable collection of validation findings.

    Usage::

        result = validate_report(data)
        if not result.is_valid:
            for issue in result.errors:
                print(issue.code, issue.message_ar)

    Attributes:
        issues: All findings (ERROR + WARNING + INFO), ordered as produced.
    """

    issues: tuple[ValidationIssue, ...]

    # ── Constructors ──────────────────────────────────────────────────────────

    @classmethod
    def empty(cls) -> "ValidationResult":
        """Return a result with no issues (is_valid == True)."""
        return cls(issues=())

    @classmethod
    def from_iterable(cls, it: Iterable[ValidationIssue | None]) -> "ValidationResult":
        """Build from an iterable that may contain None entries (skipped)."""
        return cls(issues=tuple(i for i in it if i is not None))

    # ── Filtering properties ──────────────────────────────────────────────────

    @property
    def is_valid(self) -> bool:
        """True when there are no ERROR-level issues."""
        return not any(i.severity is Severity.ERROR for i in self.issues)

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity is Severity.ERROR)

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity is Severity.WARNING)

    @property
    def infos(self) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity is Severity.INFO)

    # ── Merge ─────────────────────────────────────────────────────────────────

    def merge(self, *others: "ValidationResult") -> "ValidationResult":
        """Return a new result combining this and all *others* (order preserved)."""
        combined: tuple[ValidationIssue, ...] = self.issues
        for other in others:
            combined = combined + other.issues
        return ValidationResult(issues=combined)

    # ── Dunder helpers ────────────────────────────────────────────────────────

    def __bool__(self) -> bool:
        return self.is_valid

    def __len__(self) -> int:
        return len(self.issues)
