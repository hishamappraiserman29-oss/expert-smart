import math
from decimal import Decimal
from typing import Optional
from datetime import date

from .base import (
    EngineResult, AuditEntry, ValidationIssue, ValuationEngine,
)


class ComparativeEngine(ValuationEngine):
    """
    Sales Comparison (Comparative) Approach engine — Phase 4 v1.

    Flow:  subject + [3-7 comparables] → apply adjustments → weighted mean → EngineResult
    """

    name    = "comparative"
    version = "1.0.0"

    def __init__(self):
        self.area_elasticity              = 0.85   # economy-of-scale exponent
        self.age_depreciation_per_year    = 0.01   # 1% per year age gap
        self.floor_adjustments:      dict = {}     # e.g. {"1": 0.02, "-1": -0.02}
        self.finishing_adjustments:  dict = {}     # e.g. {"semi_finished": -0.10}
        self.config_min_comparables       = 3
        self.config_recommended_comparables = 5

    # ──────────────────────────────────────────────────────────────────
    # Abstract method implementations (required by ValuationEngine)
    # ──────────────────────────────────────────────────────────────────

    def validate(self, inputs: dict) -> list[ValidationIssue]:
        """Check inputs before calculation. Returns list of issues (empty = OK)."""
        issues: list[ValidationIssue] = []

        # Subject area
        subject_area = inputs.get("subject_area_sqm", 0) or 0
        if subject_area <= 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_SUBJECT_AREA",
                message=f"subject_area_sqm must be > 0; got {subject_area}",
            ))

        comps = inputs.get("comparables", [])

        # Comparable count
        if len(comps) < self.config_min_comparables:
            issues.append(ValidationIssue(
                severity="error",
                code="INSUFFICIENT_COMPARABLES",
                message=(
                    f"Minimum {self.config_min_comparables} comparables required; "
                    f"got {len(comps)}"
                ),
            ))
        elif len(comps) < self.config_recommended_comparables:
            issues.append(ValidationIssue(
                severity="warning",
                code="BELOW_RECOMMENDED",
                message=(
                    f"Less than {self.config_recommended_comparables} comparables; "
                    "confidence will be lower"
                ),
            ))

        # Per-comparable checks
        for i, comp in enumerate(comps):
            label = f"Comparable #{i + 1} (id={comp.get('id', '?')})"

            comp_area = comp.get("area_sqm") or comp.get("area") or 0
            if comp_area <= 0:
                issues.append(ValidationIssue(
                    severity="warning",
                    code="INVALID_COMPARABLE_AREA",
                    message=f"{label} has invalid area: {comp_area}",
                ))

            price_egp     = comp.get("price_egp") or comp.get("price")
            price_per_sqm = comp.get("price_per_sqm") or comp.get("price_per_meter")

            if not price_egp and not price_per_sqm:
                issues.append(ValidationIssue(
                    severity="error",
                    code="MISSING_PRICE",
                    message=f"{label} has neither price_egp nor price_per_sqm",
                ))
            else:
                bad_price = (price_egp is not None and float(price_egp) <= 0) or \
                            (price_per_sqm is not None and float(price_per_sqm) <= 0)
                if bad_price:
                    issues.append(ValidationIssue(
                        severity="warning",
                        code="INVALID_PRICE",
                        message=f"{label} has a non-positive price value",
                    ))

        return issues

    def calculate(self, inputs: dict) -> EngineResult:
        """Apply adjustments to each comparable, aggregate, return EngineResult."""
        issues = self.validate(inputs)
        errors = [i for i in issues if i.severity == "error"]

        if errors:
            return EngineResult(
                engine_name=self.name,
                value=None,
                confidence="insufficient",
                audit_trail=[],
                issues=issues,
                metadata={},
            )

        subject_area      = float(inputs["subject_area_sqm"])
        subject_age       = inputs.get("subject_age_years")
        subject_floor     = inputs.get("subject_floor")
        subject_finishing = inputs.get("subject_finishing_level")
        comps             = inputs["comparables"]
        current_year      = date.today().year

        audit_trail: list[AuditEntry]   = []
        adjusted_prices:  list[float]   = []

        audit_trail.append(AuditEntry(
            step_name="Load inputs",
            inputs={"subject_area_sqm": subject_area, "comparable_count": len(comps)},
            outputs={},
            formula="—",
            references=["EGVS_3.1: Sales Comparison Approach", "Phase 4 Comparative Engine v1.0"],
        ))

        for i, comp in enumerate(comps):
            label     = f"comparable #{i + 1}"
            comp_id   = comp.get("id", f"comp_{i + 1}")
            comp_area = float(comp.get("area_sqm") or comp.get("area") or 0)

            price_egp     = comp.get("price_egp") or comp.get("price")
            price_per_sqm = comp.get("price_per_sqm") or comp.get("price_per_meter")

            # Derive original price/sqm
            if price_egp and comp_area > 0:
                original_per_sqm = float(price_egp) / comp_area
            elif price_per_sqm:
                original_per_sqm = float(price_per_sqm)
            else:
                continue  # already caught by validate; skip silently

            audit_trail.append(AuditEntry(
                step_name=f"Extract {label} price/sqm",
                inputs={"comp_id": comp_id, "price_egp": price_egp, "area_sqm": comp_area},
                outputs={"original_price_per_sqm": round(original_per_sqm, 2)},
                formula="price_per_sqm = price_egp / area_sqm",
                references=[f"Comparable {comp_id}"],
            ))

            # Derive comp age from year_built if age_years absent
            comp_age = comp.get("age_years")
            if comp_age is None:
                yb = comp.get("year_built")
                if yb and int(yb) > 0:
                    comp_age = current_year - int(yb)

            area_factor = (subject_area / comp_area) ** self.area_elasticity if comp_area > 0 else 1.0

            audit_trail.append(AuditEntry(
                step_name=f"Adjust {label} for area",
                inputs={
                    "subject_area": subject_area,
                    "comp_area": comp_area,
                    "elasticity": self.area_elasticity,
                },
                outputs={
                    "area_factor": round(area_factor, 4),
                    "adjusted_per_sqm": round(original_per_sqm * area_factor, 2),
                },
                formula=f"area_factor = (subject_area / comp_area) ^ {self.area_elasticity}",
                references=["EGVS_3.2: Area Adjustment", "IAAO Standard on Mass Appraisal"],
            ))

            if subject_age is not None and comp_age is not None:
                age_diff   = abs(subject_age - comp_age)
                age_factor = max(0.0, 1.0 - age_diff * self.age_depreciation_per_year)
                audit_trail.append(AuditEntry(
                    step_name=f"Adjust {label} for age",
                    inputs={
                        "subject_age": subject_age,
                        "comp_age": comp_age,
                        "depreciation_rate": self.age_depreciation_per_year,
                    },
                    outputs={"age_factor": round(age_factor, 4)},
                    formula=(
                        f"age_factor = max(0, 1 - |subject_age - comp_age| "
                        f"× {self.age_depreciation_per_year})"
                    ),
                    references=["EGVS_3.3: Age / Condition Adjustment"],
                ))

            adjusted = self._calculate_adjusted_price_per_sqm(
                original_per_sqm=original_per_sqm,
                subject_area=subject_area,
                comp_area=comp_area,
                subject_age=subject_age,
                comp_age=comp_age,
                subject_floor=subject_floor,
                comp_floor=comp.get("floor"),
                subject_finishing=subject_finishing,
                comp_finishing=comp.get("finishing_level"),
            )

            final_for_comp = adjusted * subject_area
            audit_trail.append(AuditEntry(
                step_name=f"Calculate final value for {label}",
                inputs={"adjusted_per_sqm": round(adjusted, 2), "subject_area": subject_area},
                outputs={"final_value": round(final_for_comp, 2)},
                formula="final_value = adjusted_per_sqm × subject_area",
                references=[f"Comparable {comp_id}"],
            ))

            adjusted_prices.append(adjusted)

        # Guard: all comparables filtered out
        if not adjusted_prices:
            return EngineResult(
                engine_name=self.name,
                value=None,
                confidence="insufficient",
                audit_trail=audit_trail,
                issues=issues + [ValidationIssue(
                    severity="error",
                    code="NO_VALID_COMPARABLES",
                    message="All comparables were skipped due to missing data",
                )],
                metadata={},
            )

        # Aggregate
        mean_per_sqm = sum(adjusted_prices) / len(adjusted_prices)
        final_value  = mean_per_sqm * subject_area
        cv           = self._coefficient_of_variation(adjusted_prices)

        audit_trail.append(AuditEntry(
            step_name="Aggregate all comparables",
            inputs={
                "adjusted_prices_per_sqm": [round(p, 2) for p in adjusted_prices],
                "comparable_count": len(adjusted_prices),
            },
            outputs={
                "mean_per_sqm": round(mean_per_sqm, 2),
                "final_value": round(final_value, 2),
                "coefficient_of_variation": round(cv, 4),
            },
            formula="final_value = mean(adjusted_prices_per_sqm) × subject_area",
            references=["EGVS_3.4: Value Reconciliation", "Phase 4 Comparative Engine v1.0"],
        ))

        n          = len(adjusted_prices)
        confidence = (
            "high"   if n >= self.config_recommended_comparables else
            "medium" if n >= self.config_min_comparables          else
            "low"
        )

        metadata = {
            "per_sqm":                    round(mean_per_sqm, 2),
            "comparable_count":           n,
            "price_range_min":            round(min(adjusted_prices), 2),
            "price_range_max":            round(max(adjusted_prices), 2),
            "coefficient_of_variation":   round(cv, 4),
        }

        return EngineResult(
            engine_name=self.name,
            value=Decimal(str(round(final_value, 2))),
            confidence=confidence,
            audit_trail=audit_trail,
            issues=issues,
            metadata=metadata,
        )

    # ──────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────

    def _calculate_adjusted_price_per_sqm(
        self,
        original_per_sqm: float,
        subject_area: float,
        comp_area: float,
        subject_age: Optional[int],
        comp_age: Optional[int],
        subject_floor: Optional[int],
        comp_floor,
        subject_finishing: Optional[str],
        comp_finishing: Optional[str],
    ) -> float:
        """Apply all configurable adjustments to one comparable's price/sqm."""
        adjusted = original_per_sqm

        # Area adjustment (economy of scale)
        if comp_area > 0:
            adjusted *= (subject_area / comp_area) ** self.area_elasticity

        # Age adjustment
        if subject_age is not None and comp_age is not None:
            age_diff = abs(subject_age - comp_age)
            adjusted *= max(0.0, 1.0 - age_diff * self.age_depreciation_per_year)

        # Floor adjustment (floor_diff → lookup in self.floor_adjustments)
        if subject_floor is not None and comp_floor is not None:
            floor_diff = subject_floor - int(comp_floor)
            floor_adj  = self.floor_adjustments.get(str(floor_diff), 0.0)
            adjusted  *= 1.0 + floor_adj

        # Finishing adjustment
        if subject_finishing and comp_finishing:
            finishing_adj = (
                0.0 if subject_finishing == comp_finishing
                else self.finishing_adjustments.get(comp_finishing, 0.0)
            )
            adjusted *= 1.0 + finishing_adj

        return adjusted

    def _coefficient_of_variation(self, values: list[float]) -> float:
        """CV = std_dev / mean. Lower = more consistent comparable set."""
        if not values:
            return 0.0
        mean = sum(values) / len(values)
        if mean == 0:
            return 0.0
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return math.sqrt(variance) / mean
