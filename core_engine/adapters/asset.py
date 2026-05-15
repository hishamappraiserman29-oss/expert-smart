from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional

from engines.base import AuditEntry
from .base import PurposeResult, ValidationIssue


@dataclass
class AssetValuationResult:
    """Result from an asset adapter — property-type-specific valuation."""

    asset_type:     str             # "residential" | "commercial" | "land"
    primary_purpose: str            # always "market_value" per EGVS 2.0
    primary_value:  Optional[Decimal]
    confidence:     str             # "high" | "medium" | "low" | "insufficient"

    alternative_values: dict[str, Decimal]  = field(default_factory=dict)
    weights_applied:    dict[str, float]    = field(default_factory=dict)
    audit_trail:        list[AuditEntry]    = field(default_factory=list)
    issues:             list[ValidationIssue] = field(default_factory=list)
    metadata:           dict[str, Any]      = field(default_factory=dict)
    disclosures:        list[str]           = field(default_factory=list)


class AssetAdapter(ABC):
    """
    Abstract base for property-type-specific valuation logic.

    Sits above the Phase 5 purpose adapters.  Each concrete subclass
    knows which weight preset to use, what validations apply, and
    whether any post-reconciliation adjustments are needed for that
    property category.

    Subclasses must implement three abstract methods:
        validate_inputs()         — property-type validation rules
        calculate_weights()       — 3-approach weight preset selection
        apply_asset_adjustments() — optional post-reconciliation tweaks
    The concrete value() method orchestrates them in a fixed sequence.
    """

    name:    str = "base_asset"
    version: str = "1.0.0"
    supported_asset_types: list[str] = []

    def __init__(self) -> None:
        pass   # subclasses add their own state

    # ──────────────────────────────────────────────────────────────────────────
    # Abstract methods — subclasses must override all three
    # ──────────────────────────────────────────────────────────────────────────

    @abstractmethod
    def validate_inputs(
        self,
        subject_property: dict,
        purpose_results: dict,
    ) -> list[ValidationIssue]:
        """
        Validate inputs before any calculation.

        Parameters
        ----------
        subject_property : dict
            Keys include: property_type, area_sqm, age_years, quality_tier, location
        purpose_results : dict
            Keys: "comparable", "cost", "income" (Decimal values from Phase 4 engines)

        Returns
        -------
        list[ValidationIssue]  — empty if all valid
        """
        ...

    @abstractmethod
    def calculate_weights(self, subject_property: dict) -> dict[str, float]:
        """
        Return the 3-approach weight preset for this property type.

        Must return a dict with exactly the keys "comparable", "cost", "income"
        whose values sum to 1.0 (±0.001).
        """
        ...

    @abstractmethod
    def apply_asset_adjustments(
        self,
        reconciled_value: Decimal,
        subject_property: dict,
        metadata: dict,
    ) -> Decimal:
        """
        Apply any property-type-specific post-reconciliation adjustments.

        Return the adjusted final value.  Subclasses that need no adjustment
        simply return reconciled_value unchanged.
        """
        ...

    # ──────────────────────────────────────────────────────────────────────────
    # Concrete orchestration — subclasses normally do NOT override this
    # ──────────────────────────────────────────────────────────────────────────

    def value(
        self,
        subject_property: dict,
        three_values: dict,
        phase5_result: PurposeResult,
    ) -> AssetValuationResult:
        """
        Full asset-layer valuation pipeline.

        Steps
        -----
        1. Validate inputs; abort on critical errors.
        2. Calculate property-type weight preset.
        3. Reconcile three Phase 4 values with those weights.
        4. Apply asset-specific adjustments.
        5. Build audit trail (Phase 5 entries first, then Phase 6 entry).
        6. Build metadata and disclosures.
        7. Return AssetValuationResult.
        """

        # Step 1 — Validate
        issues = self.validate_inputs(subject_property, three_values)
        errors = [i for i in issues if i.severity == "error"]
        if errors:
            return AssetValuationResult(
                asset_type=self.name,
                primary_purpose="market_value",
                primary_value=None,
                confidence="insufficient",
                issues=issues,
            )

        # Step 2 — Weights
        weights = self.calculate_weights(subject_property)

        # Step 3 — Reconcile (weighted average)
        comp = three_values["comparable"]
        cost = three_values["cost"]
        inc  = three_values["income"]

        reconciled = (
            comp * Decimal(str(weights["comparable"])) +
            cost * Decimal(str(weights["cost"])) +
            inc  * Decimal(str(weights["income"]))
        )

        # Step 4 — Asset-specific adjustments
        build_metadata: dict[str, Any] = {
            "weights_applied":  weights,
            "comparable":       float(comp),
            "cost":             float(cost),
            "income":           float(inc),
            "reconciled_value": float(reconciled),
        }
        final_value = self.apply_asset_adjustments(reconciled, subject_property, build_metadata)

        # Step 5 — Audit trail
        audit_trail: list[AuditEntry] = list(phase5_result.audit_trail) + [
            AuditEntry(
                step_name=f"Apply {self.name} asset adapter weights",
                inputs={
                    "comparable": float(comp),
                    "cost":       float(cost),
                    "income":     float(inc),
                    "weights":    weights,
                },
                outputs={
                    "reconciled_value": float(reconciled),
                    "final_value":      float(final_value),
                },
                formula=(
                    f"final = comp×{weights['comparable']} + "
                    f"cost×{weights['cost']} + "
                    f"income×{weights['income']}"
                ),
                references=[f"AssetAdapter_{self.name.upper()}"],
            )
        ]

        # Step 6 — Metadata and disclosures
        metadata: dict[str, Any] = {
            "asset_type":       self.name,
            "property_type":    subject_property.get("property_type"),
            "weights_applied":  weights,
            "comparable":       float(comp),
            "cost":             float(cost),
            "income":           float(inc),
            "reconciled_value": float(reconciled),
            "final_value":      float(final_value),
            **{k: v for k, v in subject_property.items() if k != "property_type"},
        }

        disclosures: list[str] = list(phase5_result.disclosures) + [
            f"AssetAdapter_{self.name.upper()}"
        ]

        # Step 7 — Return
        return AssetValuationResult(
            asset_type=self.name,
            primary_purpose="market_value",
            primary_value=final_value,
            confidence=phase5_result.confidence,
            alternative_values={},   # caller populates with other purpose values
            weights_applied=weights,
            audit_trail=audit_trail,
            issues=issues,
            metadata=metadata,
            disclosures=disclosures,
        )
