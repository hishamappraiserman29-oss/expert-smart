from dataclasses import dataclass, field
from typing import Optional, Any
from decimal import Decimal
from abc import ABC, abstractmethod


@dataclass
class AuditEntry:
    """Log a single calculation step for court-grade traceability."""
    step_name: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    formula: str
    references: list[str] = field(default_factory=list)


@dataclass
class ValidationIssue:
    """Flag a problem found during input validation or calculation."""
    severity: str   # "error" | "warning" | "info"
    code: str       # machine-readable, e.g. "INSUFFICIENT_COMPARABLES"
    message: str    # human-readable explanation


@dataclass
class EngineResult:
    """Complete output of any valuation engine."""
    engine_name: str
    value: Optional[Decimal]        # final value in EGP; None if errors blocked calculation
    confidence: str                 # "high" | "medium" | "low" | "insufficient"
    audit_trail: list[AuditEntry]
    issues: list[ValidationIssue]
    metadata: dict[str, Any] = field(default_factory=dict)


class ValuationEngine(ABC):
    """Abstract base that every Phase 4 engine (Comparative, Cost, Income) inherits."""

    name: str = "base"
    version: str = "0.0.0"

    @abstractmethod
    def validate(self, inputs: Any) -> list[ValidationIssue]:
        """Check inputs before calculation. Return empty list if valid."""
        ...

    @abstractmethod
    def calculate(self, inputs: Any) -> EngineResult:
        """Perform calculation and return a fully-logged EngineResult."""
        ...
