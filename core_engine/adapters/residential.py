from decimal import Decimal

from .asset import AssetAdapter
from .base import ValidationIssue


class ResidentialAdapter(AssetAdapter):
    """
    Residential property valuation — apartments, villas, townhouses.

    Ownership type drives the 3-approach weight preset:
      owner_occupied  80 / 15 / 5   (buyer pays market price, not yield)
      rental          50 / 20 / 30  (investor values income stream)
      mixed           65 / 18 / 17  (balanced)

    Post-reconciliation adjustments (cumulative multipliers):
      quality_tier      luxury +10%, economy −10%, heritage +5%
      location_premium  caller-supplied float, e.g. 0.15 = +15%
      condition_factor  caller-supplied float, e.g. −0.10 = −10%
    """

    name    = "residential"
    version = "1.0.0"
    supported_asset_types = ["apartment", "villa", "townhouse", "duplex", "penthouse"]

    def __init__(self) -> None:
        super().__init__()
        self.name    = "residential"
        self.version = "1.0.0"
        self.supported_asset_types = [
            "apartment", "villa", "townhouse", "duplex", "penthouse",
        ]

        self.ownership_weights: dict[str, dict[str, float]] = {
            "owner_occupied": {"comparable": 0.80, "cost": 0.15, "income": 0.05},
            "rental":         {"comparable": 0.50, "cost": 0.20, "income": 0.30},
            "mixed":          {"comparable": 0.65, "cost": 0.18, "income": 0.17},
        }

        self.quality_adjustments: dict[str, float] = {
            "luxury":   0.10,
            "standard": 0.00,
            "economy": -0.10,
            "heritage": 0.05,
        }

        self.age_brackets: dict[str, tuple] = {
            "new":    (0,   5),
            "young":  (5,   15),
            "mature": (15,  30),
            "aging":  (30,  50),
            "old":    (50,  float("inf")),
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Abstract method implementations
    # ──────────────────────────────────────────────────────────────────────────

    def validate_inputs(
        self,
        subject_property: dict,
        purpose_results: dict,
    ) -> list[ValidationIssue]:
        """Residential-specific validation rules."""
        issues: list[ValidationIssue] = []

        # Property type must be in supported list
        prop_type = subject_property.get("property_type", "").lower()
        if prop_type not in self.supported_asset_types:
            issues.append(ValidationIssue(
                severity="error",
                code="UNSUPPORTED_PROPERTY_TYPE",
                message=(
                    f"Property type '{prop_type}' not in "
                    f"{self.supported_asset_types}"
                ),
            ))

        # Area sanity check
        area = subject_property.get("area_sqm", 0)
        if area <= 0 or area > 1000:
            issues.append(ValidationIssue(
                severity="warning",
                code="UNUSUAL_AREA",
                message=(
                    f"Area {area} sqm is unusual for residential "
                    "(typical: 50–500)"
                ),
            ))

        # Age must be non-negative; > 100 years triggers a warning
        age = subject_property.get("age_years", 0)
        if age < 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_AGE",
                message=f"Age cannot be negative ({age})",
            ))
        elif age > 100:
            issues.append(ValidationIssue(
                severity="warning",
                code="VERY_OLD_PROPERTY",
                message=(
                    f"Property is {age} years old — very old, "
                    "low confidence recommended"
                ),
            ))

        # Quality tier must be known
        quality = subject_property.get("quality_tier", "standard").lower()
        if quality not in self.quality_adjustments:
            issues.append(ValidationIssue(
                severity="warning",
                code="UNKNOWN_QUALITY_TIER",
                message=(
                    f"Quality tier '{quality}' unknown, "
                    "defaulting to 'standard'"
                ),
            ))

        # All three Phase 4 values required and positive
        for key in ("comparable", "cost", "income"):
            val = purpose_results.get(key)
            if val is None:
                issues.append(ValidationIssue(
                    severity="error",
                    code=f"MISSING_{key.upper()}",
                    message=f"Missing {key} value from Phase 4",
                ))
            elif float(val) <= 0:
                issues.append(ValidationIssue(
                    severity="error",
                    code=f"INVALID_{key.upper()}",
                    message=f"{key} value must be > 0 (got {val})",
                ))

        return issues

    def calculate_weights(self, subject_property: dict) -> dict[str, float]:
        """Return 3-approach weights based on ownership type."""
        ownership = subject_property.get("ownership_type", "owner_occupied").lower()
        return self.ownership_weights.get(ownership, self.ownership_weights["owner_occupied"])

    def apply_asset_adjustments(
        self,
        reconciled_value: Decimal,
        subject_property: dict,
        metadata: dict,
    ) -> Decimal:
        """Apply quality, location, and condition multipliers (cumulative)."""
        value = reconciled_value

        # Quality tier
        quality = subject_property.get("quality_tier", "standard").lower()
        quality_factor = self.quality_adjustments.get(quality, 0.0)
        if quality_factor != 0.0:
            value = value * (Decimal("1") + Decimal(str(quality_factor)))

        # Location premium (optional, caller-supplied)
        location_premium = subject_property.get("location_premium", 0.0)
        if location_premium != 0.0:
            value = value * (Decimal("1") + Decimal(str(location_premium)))

        # Condition factor (optional, caller-supplied)
        condition_factor = subject_property.get("condition_factor", 0.0)
        if condition_factor != 0.0:
            value = value * (Decimal("1") + Decimal(str(condition_factor)))

        return value
