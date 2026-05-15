from decimal import Decimal
from typing import Dict, List

from .asset import AssetAdapter
from .base import ValidationIssue


class LandAdapter(AssetAdapter):
    """
    Land valuation — vacant land, raw land, development sites, leasehold land.

    Key differences from improved-property adapters:
      - Cost approach weight is always 0% (no building to replace).
      - Weights driven by HBU (Highest and Best Use): what could be built here?
      - Post-reconciliation adjustments: location desirability × zoning × feasibility
        (all cumulative multipliers, same pattern as Residential/Commercial).
    """

    name    = "land"
    version = "1.0.0"
    supported_asset_types = ["vacant_land", "raw_land", "development_site", "leasehold_land"]

    def __init__(self) -> None:
        super().__init__()
        self.name    = "land"
        self.version = "1.0.0"
        self.supported_asset_types = [
            "vacant_land", "raw_land", "development_site", "leasehold_land",
        ]

        self.hbu_weights: dict[str, dict[str, float]] = {
            "residential":  {"comparable": 0.75, "cost": 0.00, "income": 0.25},
            "commercial":   {"comparable": 0.70, "cost": 0.00, "income": 0.30},
            "mixed_use":    {"comparable": 0.65, "cost": 0.00, "income": 0.35},
            "industrial":   {"comparable": 0.60, "cost": 0.00, "income": 0.40},
            "agricultural": {"comparable": 0.80, "cost": 0.00, "income": 0.20},
            "speculative":  {"comparable": 0.50, "cost": 0.00, "income": 0.50},
        }

        self.location_adjustments: dict[str, float] = {
            "prime":     0.15,
            "good":      0.08,
            "standard":  0.00,
            "secondary": -0.10,
            "remote":    -0.20,
        }

        self.zoning_adjustments: dict[str, float] = {
            "unrestricted":       0.10,
            "general_commercial": 0.05,
            "residential_only":   -0.05,
            "restricted":         -0.15,
        }

        self.feasibility_adjustments: dict[str, float] = {
            "ready_to_build": 0.10,
            "feasible":       0.00,
            "challenging":    -0.10,
            "very_difficult": -0.20,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Abstract method implementations
    # ──────────────────────────────────────────────────────────────────────────

    def validate_inputs(
        self,
        subject_property: dict,
        purpose_results: dict,
    ) -> List[ValidationIssue]:
        """Land-specific validation rules."""
        issues: List[ValidationIssue] = []

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

        # Area — land can be very large but must be positive
        area = subject_property.get("area_sqm", 0)
        if area <= 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_AREA",
                message=f"Area must be > 0 sqm (got {area})",
            ))
        elif area > 1_000_000:
            issues.append(ValidationIssue(
                severity="warning",
                code="VERY_LARGE_LAND",
                message=f"Area {area} sqm is very large — verify data",
            ))

        # HBU
        hbu = subject_property.get("hbu", "residential").lower()
        if hbu not in self.hbu_weights:
            issues.append(ValidationIssue(
                severity="warning",
                code="UNKNOWN_HBU",
                message=f"HBU '{hbu}' unknown, defaulting to 'residential'",
            ))

        # Location desirability
        location = subject_property.get("location_desirability", "standard").lower()
        if location not in self.location_adjustments:
            issues.append(ValidationIssue(
                severity="warning",
                code="UNKNOWN_LOCATION",
                message=f"Location '{location}' unknown, defaulting to 'standard'",
            ))

        # Zoning
        zoning = subject_property.get("zoning", "general_commercial").lower()
        if zoning not in self.zoning_adjustments:
            issues.append(ValidationIssue(
                severity="warning",
                code="UNKNOWN_ZONING",
                message=f"Zoning '{zoning}' unknown, defaulting to 'general_commercial'",
            ))

        # Cost value sanity: land should have minimal cost approach result
        cost = purpose_results.get("cost", 0)
        comparable = purpose_results.get("comparable", 0)
        if cost and comparable and float(cost) > float(comparable) * 0.20:
            issues.append(ValidationIssue(
                severity="warning",
                code="HIGH_COST_VALUE",
                message=(
                    f"Cost value ({cost}) is high for land — "
                    "should be <20% of comparable"
                ),
            ))

        # Comparable and income must be present and non-negative
        for key in ("comparable", "income"):
            val = purpose_results.get(key)
            if val is None:
                issues.append(ValidationIssue(
                    severity="error",
                    code=f"MISSING_{key.upper()}",
                    message=f"Missing {key} value from Phase 4",
                ))
            elif float(val) < 0:
                issues.append(ValidationIssue(
                    severity="error",
                    code=f"INVALID_{key.upper()}",
                    message=f"{key} value cannot be negative (got {val})",
                ))

        return issues

    def calculate_weights(self, subject_property: dict) -> Dict[str, float]:
        """Return 3-approach weights based on Highest and Best Use (HBU)."""
        hbu = subject_property.get("hbu", "residential").lower()
        return self.hbu_weights.get(hbu, self.hbu_weights["residential"])

    def apply_asset_adjustments(
        self,
        reconciled_value: Decimal,
        subject_property: dict,
        metadata: dict,
    ) -> Decimal:
        """Apply location × zoning × feasibility multipliers (cumulative).

        Each factor is applied only when its key is explicitly present in
        subject_property; absent keys are skipped (no implicit defaults).
        """
        value = reconciled_value

        # 1. Location desirability
        _loc = subject_property.get("location_desirability")
        if _loc is not None:
            loc_factor = self.location_adjustments.get(_loc.lower(), 0.0)
            if loc_factor != 0.0:
                value = value * (Decimal("1") + Decimal(str(loc_factor)))

        # 2. Zoning restrictions
        _zon = subject_property.get("zoning")
        if _zon is not None:
            zon_factor = self.zoning_adjustments.get(_zon.lower(), 0.0)
            if zon_factor != 0.0:
                value = value * (Decimal("1") + Decimal(str(zon_factor)))

        # 3. Development feasibility
        _feas = subject_property.get("development_feasibility")
        if _feas is not None:
            feas_factor = self.feasibility_adjustments.get(_feas.lower(), 0.0)
            if feas_factor != 0.0:
                value = value * (Decimal("1") + Decimal(str(feas_factor)))

        return value
