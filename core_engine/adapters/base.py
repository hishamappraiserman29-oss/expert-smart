from dataclasses import dataclass, field
from typing import Optional, Any
from decimal import Decimal
from abc import ABC, abstractmethod

# Reuse Phase 4 types so audit trails chain seamlessly across both phases.
from engines.base import AuditEntry, ValidationIssue  # noqa: F401 — re-exported


@dataclass
class Adjustment:
    """Log one purpose-specific adjustment step (e.g., LTV haircut, location premium)."""
    factor_name:  str      # "LTV_DISCOUNT", "RISK_ADJUSTMENT", "WEIGHT_COMPARATIVE", …
    before_value: Decimal  # value entering this adjustment
    after_value:  Decimal  # value leaving this adjustment
    percentage:   float    # factor applied (0.80 = 20% discount, 1.05 = 5% premium)
    reason:       str      # human-readable explanation


@dataclass
class PurposeResult:
    """Complete output of any purpose adapter."""
    purpose_name:   str                    # "reconciliation", "market_value", "mortgage", …
    adjusted_value: Optional[Decimal]      # final EGP value; None if validation blocked calc
    confidence:     str                    # "high" | "medium" | "low" | "insufficient"
    adjustments:    list[Adjustment]       # purpose-specific steps applied
    audit_trail:    list[AuditEntry]       # every calculation step (Phase 4 + Phase 5)
    disclosures:    list[str]              # required EgVS / IFRS sections
    metadata:       dict[str, Any] = field(default_factory=dict)
    issues:         list[ValidationIssue] = field(default_factory=list)


class PurposeAdapter(ABC):
    """Abstract template every Phase 5 purpose adapter must implement."""

    name:    str = "base"
    version: str = "0.0.0"

    @abstractmethod
    def validate_context(self, three_values: dict, inputs: dict) -> list[ValidationIssue]:
        """
        Validate three_values + adapter-specific inputs BEFORE adaptation.

        Parameters
        ----------
        three_values : {"comparative": Decimal, "cost": Decimal, "income": Decimal}
        inputs       : adapter-specific (varies per subclass)

        Returns
        -------
        list[ValidationIssue] — empty = valid, non-empty = has issues
        """
        ...

    @abstractmethod
    def adjust(self, three_values: dict, inputs: dict) -> PurposeResult:
        """
        Apply purpose-specific logic and return an adjusted PurposeResult.

        Parameters
        ----------
        three_values : {"comparative": Decimal, "cost": Decimal, "income": Decimal}
        inputs       : adapter-specific

        Returns
        -------
        PurposeResult — adjusted_value is None if any error-severity issue was found
        """
        ...
