from decimal import Decimal

from engines.base import AuditEntry
from .base import PurposeAdapter, PurposeResult, Adjustment, ValidationIssue

_KNOWN_GOVERNORATES = {
    "Cairo", "Giza", "Alexandria", "Ismailia", "Suez", "Port Said",
    "Qalyubia", "Dakahlia", "Sharqia", "Gharbia", "Beheira", "Kafr El-Sheikh",
    "Monufia", "Fayyum", "Beni Suef", "Minya", "Asyut", "Sohag", "Qena",
    "Luxor", "Aswan", "Red Sea", "North Sinai", "South Sinai", "Matruh",
    "New Valley", "Damietta",
}


class InsuranceValueAdapter(PurposeAdapter):
    """
    Insurance valuation — replacement cost for building coverage.

    Insurance principle: cover the cost to rebuild, NOT market value.
      - Market value includes land (not insurable)
      - Replacement cost is building only + inflation buffer + fees + demolition

    The adapter sources RCN from the Cost engine value (which already excludes
    land when land_value_egp = 0), then applies a risk-tier uplift and caps at
    the comparable value to prevent over-insurance.
    """

    name    = "insurance"
    version = "1.0.0"

    def __init__(self) -> None:
        # Risk tier rules — keyed by age-derived tier
        self.risk_tiers: dict[str, dict] = {
            "preferred": {"uplift_mult": 1.25, "deductible_pct": 0.01},  # newer building
            "standard":  {"uplift_mult": 1.28, "deductible_pct": 0.02},  # typical building
            "high_risk": {"uplift_mult": 1.35, "deductible_pct": 0.05},  # old / risky
        }
        # Default combined uplift explanation
        # preferred 1.25 = ~8% inflation + ~10% fees + ~7% demolition
        # standard  1.28 = ~8% inflation + ~12% fees + ~8% demolition
        # high_risk 1.35 = ~10% inflation + ~15% fees + ~10% demolition

        self.land_value_exclusion = True  # Insurance covers building only

    # ──────────────────────────────────────────────────────────────────────────
    # Abstract method implementations
    # ──────────────────────────────────────────────────────────────────────────

    def validate_context(self, three_values: dict, inputs: dict) -> list[ValidationIssue]:
        """Validate engine values and insurance-specific inputs."""
        issues: list[ValidationIssue] = []

        cost = three_values.get("cost")
        if cost is None or float(cost) <= 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_COST",
                message=f"Cost value required for insurance (replacement cost basis); got {cost}",
            ))

        comp = three_values.get("comparative")
        if comp is None or float(comp) <= 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_COMPARABLE",
                message=f"Comparative value must be > 0 (used as insurance cap); got {comp}",
            ))

        age = inputs.get("building_age_years")
        if age is not None and age < 0:
            issues.append(ValidationIssue(
                severity="warning",
                code="INVALID_AGE",
                message=f"building_age_years must be >= 0; got {age}. Defaulting to 10.",
            ))

        location = inputs.get("location")
        if location is not None and location not in _KNOWN_GOVERNORATES:
            issues.append(ValidationIssue(
                severity="warning",
                code="UNKNOWN_LOCATION",
                message=(
                    f"Location '{location}' not in known governorates; "
                    "audit trail note only — no calculation impact."
                ),
            ))

        return issues

    def adjust(self, three_values: dict, inputs: dict) -> PurposeResult:
        """Calculate insurance replacement-cost value with uplift and comparable cap."""
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

        # ── Resolve risk tier from building age ───────────────────────────────
        building_age = inputs.get("building_age_years", 10)
        if building_age < 0:
            building_age = 10   # validated above; default if invalid

        if building_age <= 5:
            risk_tier = "preferred"
        elif building_age <= 30:
            risk_tier = "standard"
        else:
            risk_tier = "high_risk"

        tier_rules  = self.risk_tiers[risk_tier]
        uplift_mult = tier_rules["uplift_mult"]

        audit_trail: list[AuditEntry] = []

        # ── Step 1: Source RCN from cost engine ───────────────────────────────
        rcn = three_values["cost"]   # Decimal — building cost, land excluded at Phase 4

        # ── Step 2: Apply uplift (inflation + contractor fees + demolition) ───
        uplifted_rcn = rcn * Decimal(str(uplift_mult))

        inflation_pct  = 8 if risk_tier == "preferred" else (8 if risk_tier == "standard" else 10)
        fees_pct       = 10 if risk_tier == "preferred" else (12 if risk_tier == "standard" else 15)
        demolition_pct = round((uplift_mult - 1) * 100 - inflation_pct - fees_pct)

        audit_trail.append(AuditEntry(
            step_name="Apply insurance uplift (inflation + fees + demolition)",
            inputs={"rcn": float(rcn), "uplift_multiplier": uplift_mult, "risk_tier": risk_tier},
            outputs={"uplifted_rcn": float(uplifted_rcn)},
            formula=f"uplifted = RCN × {uplift_mult}",
            references=["Insurance_Industry_Standard"],
        ))

        # ── Step 3: Cap at comparable (prevent over-insurance) ────────────────
        comparable   = three_values["comparative"]
        insurance_value = min(uplifted_rcn, comparable)
        capped_by_comparable = insurance_value < uplifted_rcn

        audit_trail.append(AuditEntry(
            step_name="Cap insurance value at comparable",
            inputs={"uplifted_rcn": float(uplifted_rcn), "comparable": float(comparable)},
            outputs={
                "insurance_value":       float(insurance_value),
                "cap_applied":           capped_by_comparable,
            },
            formula="insurance = min(uplifted_rcn, comparable)",
            references=["Insurance_Underwriting_Rule"],
        ))

        # ── Confidence (risk tier baseline) ───────────────────────────────────
        confidence = "high" if risk_tier in ("preferred", "standard") else "medium"

        # ── Claim history adjustments ─────────────────────────────────────────
        claim_history = inputs.get("claim_history", "clean")
        if claim_history == "recent_claim":
            issues.append(ValidationIssue(
                severity="warning",
                code="RECENT_CLAIM_HISTORY",
                message="Recent claim may affect premium or coverage terms",
            ))
        elif claim_history == "multiple_claims":
            issues.append(ValidationIssue(
                severity="warning",
                code="MULTIPLE_CLAIMS",
                message="Multiple claims may result in coverage denial or exclusions",
            ))
            confidence = "low"   # always downgrade for multiple claims

        # ── Adjustments ───────────────────────────────────────────────────────
        cap_pct = float(insurance_value / uplifted_rcn) if float(uplifted_rcn) > 0 else 1.0

        adjustments: list[Adjustment] = [
            Adjustment(
                factor_name="RCN_UPLIFT",
                before_value=rcn,
                after_value=uplifted_rcn,
                percentage=uplift_mult,
                reason=(
                    f"Insurance uplift {(uplift_mult - 1) * 100:.0f}% "
                    f"(inflation {inflation_pct}% + fees {fees_pct}% + demolition {demolition_pct}%)"
                ),
            ),
            Adjustment(
                factor_name="COMPARABLE_CAP",
                before_value=uplifted_rcn,
                after_value=insurance_value,
                percentage=cap_pct,
                reason="Cap at comparable to prevent over-insurance",
            ),
        ]

        metadata = {
            "rcn":                        rcn,
            "uplift_multiplier":          uplift_mult,
            "uplifted_rcn":               uplifted_rcn,
            "comparable_cap":             float(comparable),
            "cap_applied":                capped_by_comparable,
            "risk_tier":                  risk_tier,
            "building_age_years":         building_age,
            "claim_history":              claim_history,
            "deductible_pct":             tier_rules["deductible_pct"],
            "annual_premium_estimate_pct": self._estimate_premium(risk_tier),
        }

        disclosures = [
            "EGVS_2.4",                       # Insurance valuation purpose
            "EGVS_2.5",                       # Underwriting assumptions
            "EGVS_4.0",                       # Replacement Cost basis
            "Insurance_Industry_Standards",
            "Egyptian_Insurance_Regulations",
        ]

        return PurposeResult(
            purpose_name=self.name,
            adjusted_value=insurance_value,
            confidence=confidence,
            adjustments=adjustments,
            audit_trail=audit_trail,
            disclosures=disclosures,
            metadata=metadata,
            issues=issues,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Helper
    # ──────────────────────────────────────────────────────────────────────────

    def _estimate_premium(self, risk_tier: str) -> float:
        """Reference annual premium as % of insured value (for client information only)."""
        if risk_tier == "preferred":
            return 0.005   # 0.5% — newer building, lower risk
        elif risk_tier == "standard":
            return 0.010   # 1.0% — typical Egyptian residential
        else:
            return 0.020   # 2.0% — old / high-risk building
