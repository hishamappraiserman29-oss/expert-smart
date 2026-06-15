"""
Liquidation / Forced Sale Value Engine (IVS 104 / RICS Red Book GN 2).

Computes the value a property would fetch under a forced sale or liquidation
scenario — typically lower than open-market value due to time pressure, limited
marketing, and distressed seller conditions.

Formula:
    gross_liquidation_value = market_value × (1 − forced_sale_discount)
    total_costs             = auction_costs + legal_costs
    net_liquidation_value   = gross_liquidation_value − total_costs

    sensitivity_conservative = market_value × (1 − (forced_sale_discount + 0.05)) − total_costs
    sensitivity_optimistic   = market_value × (1 − max(forced_sale_discount − 0.05, 0)) − total_costs

Safety:
    This engine is STANDALONE. liquidation_value does NOT automatically replace
    market_value in any report or API response.
    A negative net liquidation value is represented as value=None with a warning.
"""

from decimal import Decimal
from typing import Optional

from .base import (
    EngineResult, AuditEntry, ValidationIssue, ValuationEngine,
)

_HIGH_DISCOUNT_WARN: float = 0.50   # > 50% forced sale discount → unusual
_LOW_DISCOUNT_WARN:  float = 0.10   # < 10% → possibly understated
_SENSITIVITY_STEP:   float = 0.05   # ±5% discount stress
_SHORT_MARKETING_MONTHS: int = 1    # < 1 month → very short


class LiquidationEngine(ValuationEngine):
    """
    Liquidation / Forced Sale Value engine — Phase 16.4 v1.

    Inputs (dict keys):
        market_value              float  required (> 0) — open market value basis
        forced_sale_discount      float  required [0, 1) — fraction deducted for urgency
        marketing_period_months   int    optional (≥ 0) — informational
        auction_costs             float  optional (≥ 0, absolute EGP)
        legal_costs               float  optional (≥ 0, absolute EGP)

    Outputs (EngineResult):
        value      = net_liquidation_value (Decimal, EGP); None if result ≤ 0
        confidence = high | medium | low | insufficient
        metadata   = {market_value, forced_sale_discount, gross_liquidation_value,
                      auction_costs, legal_costs, total_costs, net_liquidation_value,
                      marketing_period_months, feasibility_status,
                      sensitivity_conservative, sensitivity_optimistic}
    """

    name    = "liquidation"
    version = "1.0.0"

    # ------------------------------------------------------------------
    # Abstract method implementations
    # ------------------------------------------------------------------

    def validate(self, inputs: dict) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        mv = inputs.get("market_value")
        if mv is None:
            issues.append(ValidationIssue(
                severity="error",
                code="MISSING_MARKET_VALUE",
                message="market_value is required",
            ))
        elif float(mv) <= 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_MARKET_VALUE",
                message=f"market_value must be > 0; got {mv}",
            ))

        fsd = inputs.get("forced_sale_discount")
        if fsd is None:
            issues.append(ValidationIssue(
                severity="error",
                code="MISSING_FORCED_SALE_DISCOUNT",
                message="forced_sale_discount is required (e.g. 0.25 = 25%)",
            ))
        else:
            fsd_f = float(fsd)
            if not (0.0 <= fsd_f < 1.0):
                issues.append(ValidationIssue(
                    severity="error",
                    code="INVALID_FORCED_SALE_DISCOUNT",
                    message=f"forced_sale_discount must be in [0, 1); got {fsd}",
                ))
            elif fsd_f > _HIGH_DISCOUNT_WARN:
                issues.append(ValidationIssue(
                    severity="warning",
                    code="HIGH_FORCED_SALE_DISCOUNT",
                    message=(
                        f"forced_sale_discount {fsd_f:.0%} exceeds {_HIGH_DISCOUNT_WARN:.0%} — "
                        "verify scenario; extremely high discounts may indicate distress or error"
                    ),
                ))
            elif fsd_f < _LOW_DISCOUNT_WARN:
                issues.append(ValidationIssue(
                    severity="warning",
                    code="LOW_FORCED_SALE_DISCOUNT",
                    message=(
                        f"forced_sale_discount {fsd_f:.0%} is below {_LOW_DISCOUNT_WARN:.0%} — "
                        "may understate liquidity risk in a forced sale scenario"
                    ),
                ))

        for field, code in (
            ("auction_costs", "MISSING_AUCTION_COSTS"),
            ("legal_costs",   "MISSING_LEGAL_COSTS"),
        ):
            val = inputs.get(field)
            if val is None:
                issues.append(ValidationIssue(
                    severity="warning",
                    code=code,
                    message=f"{field} not supplied — assumed zero; may overstate net proceeds",
                ))
            elif float(val) < 0:
                issues.append(ValidationIssue(
                    severity="error",
                    code=f"INVALID_{field.upper()}",
                    message=f"{field} must be ≥ 0; got {val}",
                ))

        mkt_months = inputs.get("marketing_period_months")
        if mkt_months is not None and int(mkt_months) < _SHORT_MARKETING_MONTHS:
            issues.append(ValidationIssue(
                severity="warning",
                code="SHORT_MARKETING_PERIOD",
                message=(
                    f"marketing_period_months {mkt_months} < {_SHORT_MARKETING_MONTHS} month — "
                    "very compressed timeline; liquidation discount may need to be higher"
                ),
            ))

        return issues

    def calculate(self, inputs: dict) -> EngineResult:
        """market_value → forced discount → deduct costs → sensitivity → EngineResult."""
        issues = self.validate(inputs)
        if any(i.severity == "error" for i in issues):
            return EngineResult(
                engine_name=self.name,
                value=None,
                confidence="insufficient",
                audit_trail=[],
                issues=issues,
                metadata={},
            )

        mv          = float(inputs["market_value"])
        fsd         = float(inputs["forced_sale_discount"])
        auction     = float(inputs.get("auction_costs") or 0)
        legal       = float(inputs.get("legal_costs")   or 0)
        mkt_months  = inputs.get("marketing_period_months")

        audit_trail: list[AuditEntry] = []

        # ── Step 1: Apply forced sale discount ───────────────────────
        gross_lv = mv * (1.0 - fsd)
        audit_trail.append(AuditEntry(
            step_name="Apply forced sale discount",
            inputs={
                "market_value":         round(mv, 2),
                "forced_sale_discount": fsd,
            },
            outputs={"gross_liquidation_value": round(gross_lv, 2)},
            formula="gross_liquidation_value = market_value × (1 − forced_sale_discount)",
            references=["IVS 104: Liquidation Value", "RICS Red Book GN 2: Forced Sale"],
        ))

        # ── Step 2: Deduct transaction costs ─────────────────────────
        total_costs = auction + legal
        net_lv      = gross_lv - total_costs
        audit_trail.append(AuditEntry(
            step_name="Deduct transaction costs — net liquidation value",
            inputs={
                "gross_liquidation_value": round(gross_lv, 2),
                "auction_costs":           round(auction, 2),
                "legal_costs":             round(legal, 2),
                "total_costs":             round(total_costs, 2),
            },
            outputs={"net_liquidation_value": round(net_lv, 2)},
            formula="net_liquidation_value = gross_liquidation_value − auction_costs − legal_costs",
            references=["EGVS_8.1: Liquidation Net Proceeds", "IVS 104: Transaction Costs"],
        ))

        # Warn if negative
        if net_lv <= 0:
            issues.append(ValidationIssue(
                severity="warning",
                code="NEGATIVE_LIQUIDATION_VALUE",
                message=(
                    f"net_liquidation_value = {net_lv:,.2f} EGP ≤ 0 — "
                    "transaction costs exceed gross proceeds; review discount and cost inputs"
                ),
            ))

        # ── Step 3: Sensitivity analysis ±5% discount ─────────────────
        disc_high = min(fsd + _SENSITIVITY_STEP, 0.99)
        disc_low  = max(fsd - _SENSITIVITY_STEP, 0.0)
        sens_conservative = mv * (1.0 - disc_high) - total_costs
        sens_optimistic   = mv * (1.0 - disc_low)  - total_costs
        audit_trail.append(AuditEntry(
            step_name="Sensitivity analysis — ±5% forced sale discount stress",
            inputs={
                "market_value":  round(mv, 2),
                "total_costs":   round(total_costs, 2),
                "discount_step": _SENSITIVITY_STEP,
            },
            outputs={
                "sensitivity_conservative": round(sens_conservative, 2),
                "sensitivity_optimistic":   round(sens_optimistic,   2),
            },
            formula=(
                "conservative = MV × (1 − (disc+5%)) − costs; "
                "optimistic   = MV × (1 − (disc−5%)) − costs"
            ),
            references=["RICS GN 2: Sensitivity", "EGVS_8.2: Liquidation Stress Testing"],
        ))

        # ── Confidence ────────────────────────────────────────────────
        discount_in_range = _LOW_DISCOUNT_WARN <= fsd <= _HIGH_DISCOUNT_WARN
        has_auction       = auction > 0
        has_legal         = legal   > 0

        if net_lv <= 0:
            confidence = "low"
        elif discount_in_range and has_auction and has_legal:
            confidence = "high"
        elif discount_in_range:
            confidence = "medium"
        else:
            confidence = "low"

        result_value: Optional[Decimal] = (
            Decimal(str(round(net_lv, 2))) if net_lv > 0 else None
        )

        feasibility_status = "feasible" if net_lv > 0 else "not_feasible"

        metadata: dict = {
            "market_value":              round(mv, 2),
            "forced_sale_discount":      fsd,
            "gross_liquidation_value":   round(gross_lv, 2),
            "auction_costs":             round(auction, 2),
            "legal_costs":               round(legal, 2),
            "total_costs":               round(total_costs, 2),
            "net_liquidation_value":     round(net_lv, 2),
            "marketing_period_months":   mkt_months,
            "feasibility_status":        feasibility_status,
            "sensitivity_conservative":  round(sens_conservative, 2),
            "sensitivity_optimistic":    round(sens_optimistic,   2),
        }

        return EngineResult(
            engine_name=self.name,
            value=result_value,
            confidence=confidence,
            audit_trail=audit_trail,
            issues=issues,
            metadata=metadata,
        )
