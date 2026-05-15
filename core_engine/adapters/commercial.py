from decimal import Decimal

from .asset import AssetAdapter
from .base import ValidationIssue


class CommercialAdapter(AssetAdapter):
    """
    Commercial property valuation — offices, retail, mixed-use, industrial.

    Development stage drives the 3-approach weight preset:
      stabilized       30 / 20 / 50  (income-dominant, cash-flowing asset)
      core             35 / 25 / 40  (established, good income + market data)
      new_construction 20 / 50 / 30  (cost-dominant, no income history)
      redevelopment    25 / 40 / 35  (between new and stabilized)

    Post-reconciliation adjustments (cumulative multipliers):
      property_class    class_a +10%, class_c −10%
      occupancy_tier    fully_leased +5% → vacant −15%
        (auto-derived from occupancy_rate when provided)
      market_cap_rate   applied when rate differs >15% from the 10% default
    """

    name    = "commercial"
    version = "1.0.0"
    supported_asset_types = ["office", "retail", "mixed_use", "industrial", "warehouse"]

    def __init__(self) -> None:
        super().__init__()
        self.name    = "commercial"
        self.version = "1.0.0"
        self.supported_asset_types = [
            "office", "retail", "mixed_use", "industrial", "warehouse",
        ]

        self.stage_weights: dict[str, dict[str, float]] = {
            "stabilized":      {"comparable": 0.30, "cost": 0.20, "income": 0.50},
            "core":            {"comparable": 0.35, "cost": 0.25, "income": 0.40},
            "new_construction":{"comparable": 0.20, "cost": 0.50, "income": 0.30},
            "redevelopment":   {"comparable": 0.25, "cost": 0.40, "income": 0.35},
        }

        self.occupancy_adjustments: dict[str, float] = {
            "fully_leased":   0.05,
            "high_occupancy": 0.02,
            "standard":       0.00,
            "low_occupancy":  -0.05,
            "vacant":         -0.15,
        }

        self.property_class_adjustments: dict[str, float] = {
            "class_a":  0.10,
            "class_b":  0.00,
            "class_c": -0.10,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Abstract method implementations
    # ──────────────────────────────────────────────────────────────────────────

    def validate_inputs(
        self,
        subject_property: dict,
        purpose_results: dict,
    ) -> list[ValidationIssue]:
        """Commercial-specific validation rules."""
        issues: list[ValidationIssue] = []

        # Property type
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

        # Area sanity check (commercial = up to 50 000 sqm)
        area = subject_property.get("area_sqm", 0)
        if area <= 0 or area > 50_000:
            issues.append(ValidationIssue(
                severity="warning",
                code="UNUSUAL_COMMERCIAL_AREA",
                message=(
                    f"Area {area} sqm is unusual for commercial "
                    "(typical: 500–20,000)"
                ),
            ))

        # Age
        age = subject_property.get("age_years", 0)
        if age < 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_AGE",
                message=f"Age cannot be negative ({age})",
            ))
        elif age > 80:
            issues.append(ValidationIssue(
                severity="warning",
                code="VERY_OLD_BUILDING",
                message=(
                    f"Building is {age} years old — "
                    "may require major renovation"
                ),
            ))

        # Development stage
        stage = subject_property.get("development_stage", "stabilized").lower()
        if stage not in self.stage_weights:
            issues.append(ValidationIssue(
                severity="warning",
                code="UNKNOWN_DEVELOPMENT_STAGE",
                message=(
                    f"Development stage '{stage}' unknown, "
                    "defaulting to 'stabilized'"
                ),
            ))

        # Occupancy rate range
        occupancy = subject_property.get("occupancy_rate")
        if occupancy is not None and not (0.0 <= occupancy <= 1.0):
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_OCCUPANCY",
                message=f"Occupancy rate must be 0–1.0 (got {occupancy})",
            ))

        # Property class
        prop_class = subject_property.get("property_class", "class_b").lower()
        if prop_class not in self.property_class_adjustments:
            issues.append(ValidationIssue(
                severity="warning",
                code="UNKNOWN_PROPERTY_CLASS",
                message=(
                    f"Property class '{prop_class}' unknown, "
                    "defaulting to 'class_b'"
                ),
            ))

        # Phase 4 values — all three required and positive
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
        """Return 3-approach weights based on development stage."""
        stage = subject_property.get("development_stage", "stabilized").lower()
        return self.stage_weights.get(stage, self.stage_weights["stabilized"])

    def apply_asset_adjustments(
        self,
        reconciled_value: Decimal,
        subject_property: dict,
        metadata: dict,
    ) -> Decimal:
        """Apply property-class, occupancy, and cap-rate multipliers (cumulative)."""
        value = reconciled_value

        # 1. Property class
        prop_class = subject_property.get("property_class", "class_b").lower()
        class_factor = self.property_class_adjustments.get(prop_class, 0.0)
        if class_factor != 0.0:
            value = value * (Decimal("1") + Decimal(str(class_factor)))

        # 2. Occupancy — auto-derive from rate when present, else use tier key
        occupancy_rate = subject_property.get("occupancy_rate")
        if occupancy_rate is not None:
            if occupancy_rate >= 0.95:
                occ_factor = self.occupancy_adjustments["fully_leased"]
            elif occupancy_rate >= 0.90:
                occ_factor = self.occupancy_adjustments["high_occupancy"]
            elif occupancy_rate >= 0.70:
                occ_factor = self.occupancy_adjustments["standard"]
            elif occupancy_rate > 0.0:
                occ_factor = self.occupancy_adjustments["low_occupancy"]
            else:
                occ_factor = self.occupancy_adjustments["vacant"]
        else:
            occ_tier = subject_property.get("occupancy_tier", "standard")
            occ_factor = self.occupancy_adjustments.get(occ_tier, 0.0)

        if occ_factor != 0.0:
            value = value * (Decimal("1") + Decimal(str(occ_factor)))

        # 3. Cap rate — only when market rate differs >15% from the 10% default
        market_cap_rate = subject_property.get("market_cap_rate")
        if market_cap_rate is not None and market_cap_rate > 0:
            assumed = Decimal("0.10")
            ratio = assumed / Decimal(str(market_cap_rate))
            if ratio < Decimal("0.85") or ratio > Decimal("1.15"):
                cap_adjustment = float(ratio) - 1.0
                value = value * (Decimal("1") + Decimal(str(cap_adjustment)))

        return value
