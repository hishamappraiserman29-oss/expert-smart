from decimal import Decimal

from engines.base import AuditEntry
from .base import PurposeAdapter, PurposeResult, Adjustment, ValidationIssue

_VALID_CAP_RATE_SOURCES = {"market", "published", "expert"}


class IFRS13FairValueAdapter(PurposeAdapter):
    """
    Fair Value per IFRS 13 — Fair Value Measurement.

    Definition (IFRS 13.9):
        "The price that would be received to sell an asset or paid to transfer
        a liability in an orderly transaction between market participants at
        the measurement date."

    Fair Value Hierarchy (IFRS 13.72-90):
        Level 2 — Observable inputs (comparable transactions + market cap rate)
        Level 3 — Unobservable inputs (expert judgment, thin market)
        Level 2/3 — Blended classification (observable comps + published cap rate)

    Note: Level 1 (quoted prices in active markets) is not applicable to
    individual real estate assets in the Egyptian market.
    """

    name    = "ifrs_13"
    version = "1.0.0"

    def __init__(self) -> None:
        self.hierarchy_thresholds = {
            "level_2_min_comparables": 3,
            "level_3_max_comparables": 2,
        }

        # Weight presets — observable inputs justify heavier comparable weighting
        self.level_2_weights = {"comparative": 0.70, "cost": 0.20, "income": 0.10}
        self.level_3_weights = {"comparative": 0.40, "cost": 0.40, "income": 0.20}

        # Risk premiums reflect illiquidity and estimation uncertainty
        self.risk_premium_level_2 = 1.02   # +2% — minor uncertainty (observable inputs)
        self.risk_premium_level_3 = 1.08   # +8% — significant uncertainty (unobservable)

    # ──────────────────────────────────────────────────────────────────────────
    # Abstract method implementations
    # ──────────────────────────────────────────────────────────────────────────

    def validate_context(self, three_values: dict, inputs: dict) -> list[ValidationIssue]:
        """Validate engine values and IFRS 13 hierarchy inputs."""
        issues: list[ValidationIssue] = []

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

        count = inputs.get("comparable_count")
        if count is not None and count < 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_COMPARABLE_COUNT",
                message=f"comparable_count must be >= 0; got {count}",
            ))

        source = inputs.get("cap_rate_source")
        if source is not None and source not in _VALID_CAP_RATE_SOURCES:
            issues.append(ValidationIssue(
                severity="warning",
                code="UNKNOWN_CAP_RATE_SOURCE",
                message=(
                    f"Unrecognised cap_rate_source '{source}'; "
                    f"expected one of {sorted(_VALID_CAP_RATE_SOURCES)}. "
                    "Defaulting to 'market' for hierarchy classification."
                ),
            ))

        return issues

    def adjust(self, three_values: dict, inputs: dict) -> PurposeResult:
        """Classify hierarchy level, weight values, apply risk premium."""
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

        comparable_count  = inputs.get("comparable_count", 0)
        cap_rate_source   = inputs.get("cap_rate_source", "market")
        if cap_rate_source not in _VALID_CAP_RATE_SOURCES:
            cap_rate_source = "market"   # default per validation warning

        # ── Classify Fair Value Hierarchy level ───────────────────────────────
        # Level 2: sufficient observable comparables AND market cap rate data
        # Level 3: thin market (<3 comps) OR expert-only judgment on cap rate
        # Level 2/3: observable comps present but cap rate is published (not live market)
        if comparable_count >= 3 and cap_rate_source == "market":
            hierarchy_level = "Level 2"
            weights         = self.level_2_weights
            risk_premium    = self.risk_premium_level_2

        elif comparable_count < 3 or cap_rate_source == "expert":
            hierarchy_level = "Level 3"
            weights         = self.level_3_weights
            risk_premium    = self.risk_premium_level_3

        else:
            # comparable_count >= 3 but cap_rate_source is "published" (or other non-market)
            hierarchy_level = "Level 2/3"
            weights = {
                "comparative": (0.70 * 0.6) + (0.40 * 0.4),   # 0.58
                "cost":        (0.20 * 0.6) + (0.40 * 0.4),   # 0.28
                "income":      (0.10 * 0.6) + (0.20 * 0.4),   # 0.14
            }
            risk_premium = (self.risk_premium_level_2 * 0.6) + (self.risk_premium_level_3 * 0.4)

        audit_trail: list[AuditEntry] = []

        # ── Step 1: Hierarchy assessment ──────────────────────────────────────
        audit_trail.append(AuditEntry(
            step_name="Assess IFRS 13 Fair Value Hierarchy",
            inputs={
                "comparable_count": comparable_count,
                "cap_rate_source":  cap_rate_source,
            },
            outputs={
                "hierarchy_level": hierarchy_level,
                "weights":         weights,
                "risk_premium":    risk_premium,
            },
            formula="Hierarchy determined by data availability (IFRS 13.72-90)",
            references=["IFRS_13-72", "IFRS_13-73", "IFRS_13-74", "IFRS_13-75"],
        ))

        # ── Step 2: Weighted base value ───────────────────────────────────────
        comp = float(three_values["comparative"])
        cost = float(three_values["cost"])
        inc  = float(three_values["income"])

        base_value_f = (
            comp * weights["comparative"] +
            cost * weights["cost"] +
            inc  * weights["income"]
        )
        base_value = Decimal(str(round(base_value_f, 2)))

        audit_trail.append(AuditEntry(
            step_name="Calculate base fair value (weighted average)",
            inputs={
                "comparative": comp, "cost": cost, "income": inc,
                "weights":     weights,
            },
            outputs={"base_value": float(base_value)},
            formula=(
                f"base = comp×{weights['comparative']:.2f} + "
                f"cost×{weights['cost']:.2f} + income×{weights['income']:.2f}"
            ),
            references=["IFRS_13-54", "IFRS_13-55"],
        ))

        # ── Step 3: Risk premium for hierarchy level ──────────────────────────
        fair_value_f = base_value_f * risk_premium
        fair_value   = Decimal(str(round(fair_value_f, 2)))

        audit_trail.append(AuditEntry(
            step_name="Apply risk premium for hierarchy level",
            inputs={"base_value": float(base_value), "risk_premium": risk_premium},
            outputs={"fair_value": float(fair_value)},
            formula=f"fair_value = base × {risk_premium:.4f}  ({hierarchy_level})",
            references=["IFRS_13-89", "IFRS_13-90"],
        ))

        # ── Confidence ────────────────────────────────────────────────────────
        if hierarchy_level == "Level 2":
            confidence = "high"
        else:
            confidence = "medium"   # Level 3 and Level 2/3 both start at medium

        if cap_rate_source == "expert" and hierarchy_level == "Level 3":
            confidence = "medium"   # expert judgment acceptable but not high-confidence

        if comparable_count >= 5:
            confidence = "high"     # strong comparable set always overrides level concern

        # ── Adjustments ───────────────────────────────────────────────────────
        adjustments: list[Adjustment] = [
            Adjustment(
                factor_name="HIERARCHY_WEIGHTING",
                before_value=three_values["comparative"],
                after_value=base_value,
                percentage=weights["comparative"],
                reason=f"Fair Value Hierarchy {hierarchy_level} weighting applied",
            ),
            Adjustment(
                factor_name="HIERARCHY_RISK_PREMIUM",
                before_value=base_value,
                after_value=fair_value,
                percentage=risk_premium,
                reason=(
                    f"{hierarchy_level} illiquidity/uncertainty adjustment "
                    f"(+{(risk_premium - 1) * 100:.1f}%)"
                ),
            ),
        ]

        metadata = {
            "hierarchy_level":      hierarchy_level,
            "weights":              weights,
            "comparable_count":     comparable_count,
            "cap_rate_source":      cap_rate_source,
            "risk_premium_pct":     round((risk_premium - 1) * 100, 4),
            "base_value":           base_value,
            "fair_value":           fair_value,
            "ifrs_13_section_refs": ["IFRS_13-1", "IFRS_13-54", "IFRS_13-72"],
        }

        disclosures = [
            "IFRS_13-1",    # Scope and objective
            "IFRS_13-54",   # Definition of fair value
            "IFRS_13-55",   # Market participant assumption
            "IFRS_13-72",   # Fair Value Hierarchy (intro)
            "IFRS_13-73",   # Level 1
            "IFRS_13-74",   # Level 2
            "IFRS_13-75",   # Level 3
            "IFRS_13-89",   # Non-performance risk
            "IFRS_13-90",   # Valuation adjustments
            "EGVS_1.0",     # Cross-reference to EGVS
        ]

        return PurposeResult(
            purpose_name="ifrs_13_fair_value",
            adjusted_value=fair_value,
            confidence=confidence,
            adjustments=adjustments,
            audit_trail=audit_trail,
            disclosures=disclosures,
            metadata=metadata,
            issues=issues,
        )
