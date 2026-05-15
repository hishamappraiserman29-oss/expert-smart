from decimal import Decimal

from engines.base import AuditEntry
from .base import PurposeAdapter, PurposeResult, Adjustment, ValidationIssue
from .reconciliation import ReconciliationEngine


class MarketValueAdapter(PurposeAdapter):
    """
    EGVS standard Market Value adapter.

    Definition (EGVS 1.0):
        The most probable price a property would bring in a competitive and open
        market under all conditions requisite to a fair sale, in an arm's length
        transaction between a willing buyer and a willing seller.

    Uses ReconciliationEngine with weight presets that shift automatically when
    comparable evidence is thin (< 3 comparables).
    """

    name    = "market_value"
    version = "1.0.0"

    def __init__(self) -> None:
        self.reconciliation_engine = ReconciliationEngine()
        self.default_preset   = "market_value_default"   # 60/25/15 — standard evidence
        self.low_comps_preset = "market_value_low_comps" # 40/40/20 — thin evidence

    # ──────────────────────────────────────────────────────────────────────────
    # Abstract method implementations
    # ──────────────────────────────────────────────────────────────────────────

    def validate_context(self, three_values: dict, inputs: dict) -> list[ValidationIssue]:
        """Validate engine values; warn on thin comparable evidence."""
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

        comparable_count = inputs.get("comparable_count")
        if comparable_count is not None and comparable_count < 3:
            issues.append(ValidationIssue(
                severity="warning",
                code="LOW_COMPARABLES",
                message=(
                    f"Less than 3 comparables ({comparable_count}); "
                    "weights shift to low-comps preset (40/40/20) and confidence reduced"
                ),
            ))

        return issues

    def adjust(self, three_values: dict, inputs: dict) -> PurposeResult:
        """Calculate Market Value per EGVS with automatic weight selection."""
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

        # ── Select weight preset based on comparable evidence ─────────────────
        comparable_count   = inputs.get("comparable_count", 5)
        comparable_quality = inputs.get("comparable_quality", "standard")

        if comparable_count >= 3:
            preset      = self.default_preset
            preset_name = "EGVS Standard (3+ comparables) — 60/25/15"
        else:
            preset      = self.low_comps_preset
            preset_name = "Low Comparable Adjustment (< 3 comparables) — 40/40/20"

        # ── Delegate to ReconciliationEngine ──────────────────────────────────
        rec = self.reconciliation_engine.adjust(
            three_values,
            {"preset": preset, "comparable_count": comparable_count},
        )

        # ── Adjust confidence based on appraiser-supplied comparable quality ──
        base_confidence = rec.confidence
        if comparable_quality == "strong" and base_confidence in ("medium", "low"):
            confidence = "high"
        elif comparable_quality == "weak":
            confidence = "low"
        else:
            confidence = base_confidence

        # ── Extend audit trail with EGVS definition step ──────────────────────
        audit_trail = rec.audit_trail + [
            AuditEntry(
                step_name="Apply EGVS Market Value definition",
                inputs={
                    "comparable_count":   comparable_count,
                    "comparable_quality": comparable_quality,
                    "weights_preset":     preset_name,
                },
                outputs={
                    "market_value":       float(rec.adjusted_value),
                    "confidence":         confidence,
                },
                formula="Market Value = most probable price in arm's length transaction (EGVS 1.0)",
                references=["EGVS_1.0", "EGVS_2.0", "EGVS_3.0"],
            ),
        ]

        disclosures = [
            "EGVS_1.0",  # Definition of Market Value
            "EGVS_1.1",  # Market Value vs Other Values
            "EGVS_2.0",  # Assumptions and Limiting Conditions
            "EGVS_2.1",  # Market Conditions
            "EGVS_2.2",  # Most Probable Price
            "EGVS_2.3",  # Arm's Length Transaction
            "EGVS_3.0",  # Three Approaches to Value
            "EGVS_3.1",  # Comparable Approach
            "EGVS_3.2",  # Cost Approach
            "EGVS_3.3",  # Income Approach
        ]

        metadata = {
            "preset_used":        preset_name,
            "comparable_count":   comparable_count,
            "comparable_quality": comparable_quality,
            "weights":            rec.metadata["weights"],
            "cv":                 rec.metadata["coefficient_of_variation"],
            "weight_breakdown":   rec.metadata["weight_breakdown"],
        }

        return PurposeResult(
            purpose_name=self.name,
            adjusted_value=rec.adjusted_value,
            confidence=confidence,
            adjustments=[],   # market value is the baseline — no further adjustments
            audit_trail=audit_trail,
            disclosures=disclosures,
            metadata=metadata,
            issues=issues,
        )
