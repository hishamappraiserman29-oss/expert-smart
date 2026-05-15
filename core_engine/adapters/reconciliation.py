from decimal import Decimal
from math import sqrt

from engines.base import AuditEntry
from .base import PurposeAdapter, PurposeResult, Adjustment, ValidationIssue


class ReconciliationEngine(PurposeAdapter):
    """
    Appraiser-weighted reconciliation of three Phase 4 engine values.

    Combines Comparative, Cost, and Income values using explicit weights,
    reports a coefficient of variation (CV) as a confidence indicator, and
    logs every step for EgVS audit-trail compliance.
    """

    name    = "reconciliation"
    version = "1.0.0"

    def __init__(self) -> None:
        self.weight_presets: dict[str, dict[str, float]] = {
            "market_value_default":       {"comparative": 0.60, "cost": 0.25, "income": 0.15},
            "market_value_low_comps":     {"comparative": 0.40, "cost": 0.40, "income": 0.20},
            "residential_owner_occupied": {"comparative": 0.80, "cost": 0.15, "income": 0.05},
            "residential_rental":         {"comparative": 0.50, "cost": 0.20, "income": 0.30},
            "commercial":                 {"comparative": 0.50, "cost": 0.30, "income": 0.20},
        }
        self.default_weights = self.weight_presets["market_value_default"]

    # ──────────────────────────────────────────────────────────────────────────
    # Abstract method implementations
    # ──────────────────────────────────────────────────────────────────────────

    def validate_context(self, three_values: dict, inputs: dict) -> list[ValidationIssue]:
        """Validate engine values and optional custom weights."""
        issues: list[ValidationIssue] = []

        # Each engine value must be a positive number
        for key, code in [
            ("comparative", "INVALID_COMPARATIVE"),
            ("cost",        "INVALID_COST"),
            ("income",      "INVALID_INCOME"),
        ]:
            val = three_values.get(key)
            if val is None or float(val) <= 0:
                issues.append(ValidationIssue(
                    severity="error",
                    code=code,
                    message=f"{key} value must be > 0; got {val}",
                ))

        # Custom weights, if provided, must sum to 1.0 and each be in [0, 1]
        weights = inputs.get("weights")
        if weights is not None:
            total = sum(weights.values())
            if abs(total - 1.0) > 0.01:
                issues.append(ValidationIssue(
                    severity="error",
                    code="INVALID_WEIGHTS_SUM",
                    message=f"Weights must sum to 1.0 (±0.01); got {total:.4f}",
                ))
            for k, v in weights.items():
                if not (0.0 <= v <= 1.0):
                    issues.append(ValidationIssue(
                        severity="error",
                        code="INVALID_WEIGHT_VALUE",
                        message=f"Weight '{k}' must be in [0.0, 1.0]; got {v}",
                    ))

        return issues

    def adjust(self, three_values: dict, inputs: dict) -> PurposeResult:
        """Calculate reconciled value and coefficient of variation."""
        issues = self.validate_context(three_values, inputs)
        errors = [i for i in issues if i.severity == "error"]

        if errors:
            return PurposeResult(
                purpose_name=self.name,
                adjusted_value=None,
                confidence="insufficient",
                adjustments=[],
                audit_trail=[],
                disclosures=[],
                metadata={},
                issues=issues,
            )

        # ── Resolve weights ───────────────────────────────────────────────────
        preset_key = inputs.get("preset")
        if preset_key and preset_key in self.weight_presets:
            weights = self.weight_presets[preset_key]
        elif inputs.get("weights"):
            weights = inputs["weights"]
        else:
            weights = self.default_weights

        comp = float(three_values["comparative"])
        cost = float(three_values["cost"])
        inc  = float(three_values["income"])

        # ── Weighted reconciliation ───────────────────────────────────────────
        reconciled = (
            comp * weights["comparative"] +
            cost * weights["cost"] +
            inc  * weights["income"]
        )

        # ── Coefficient of variation → confidence ─────────────────────────────
        cv = self._calculate_cv([comp, cost, inc])

        if cv < 0.15:
            confidence = "high"    # tight range — approaches agree closely
        elif cv < 0.30:
            confidence = "medium"  # moderate spread
        else:
            confidence = "low"     # wide spread — approaches diverge significantly

        # ── Audit trail ───────────────────────────────────────────────────────
        audit_trail: list[AuditEntry] = [
            AuditEntry(
                step_name="Load three values",
                inputs={"comparative": comp, "cost": cost, "income": inc},
                outputs={"comparative": comp, "cost": cost, "income": inc},
                formula="Extract values from Phase 4 engines",
                references=[],
            ),
            AuditEntry(
                step_name="Apply weights",
                inputs={"weights": weights, "comparative": comp, "cost": cost, "income": inc},
                outputs={"reconciled_value": round(reconciled, 2)},
                formula=(
                    f"reconciled = comparative×{weights['comparative']} + "
                    f"cost×{weights['cost']} + income×{weights['income']}"
                ),
                references=["EGVS_1.0"],
            ),
            AuditEntry(
                step_name="Calculate coefficient of variation",
                inputs={"values": [comp, cost, inc]},
                outputs={"cv": round(cv, 4), "confidence": confidence},
                formula="cv = std_dev / mean",
                references=[],
            ),
        ]

        # ── Per-engine weight adjustments ─────────────────────────────────────
        adjustments: list[Adjustment] = [
            Adjustment(
                factor_name="WEIGHT_COMPARATIVE",
                before_value=Decimal(str(comp)),
                after_value=Decimal(str(round(comp * weights["comparative"], 2))),
                percentage=weights["comparative"],
                reason=f"Comparative weight {weights['comparative'] * 100:.1f}%",
            ),
            Adjustment(
                factor_name="WEIGHT_COST",
                before_value=Decimal(str(cost)),
                after_value=Decimal(str(round(cost * weights["cost"], 2))),
                percentage=weights["cost"],
                reason=f"Cost weight {weights['cost'] * 100:.1f}%",
            ),
            Adjustment(
                factor_name="WEIGHT_INCOME",
                before_value=Decimal(str(inc)),
                after_value=Decimal(str(round(inc * weights["income"], 2))),
                percentage=weights["income"],
                reason=f"Income weight {weights['income'] * 100:.1f}%",
            ),
        ]

        metadata: dict = {
            "coefficient_of_variation": round(cv, 4),
            "weights":                  weights,
            "comparable_count":         inputs.get("comparable_count"),
            "weight_breakdown": {
                "comparative_contribution": round(comp * weights["comparative"], 2),
                "cost_contribution":        round(cost * weights["cost"],        2),
                "income_contribution":      round(inc  * weights["income"],      2),
            },
        }

        return PurposeResult(
            purpose_name=self.name,
            adjusted_value=Decimal(str(round(reconciled, 2))),
            confidence=confidence,
            adjustments=adjustments,
            audit_trail=audit_trail,
            disclosures=["EGVS_1.0", "EGVS_2.0", "EGVS_3.0"],
            metadata=metadata,
            issues=issues,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Helper
    # ──────────────────────────────────────────────────────────────────────────

    def _calculate_cv(self, values: list[float]) -> float:
        """Return coefficient of variation (std_dev / mean). Lower = more consistent."""
        mean = sum(values) / len(values)
        if mean == 0:
            return 0.0
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return sqrt(variance) / mean
