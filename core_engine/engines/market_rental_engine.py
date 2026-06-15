"""
Market Rental Value Engine (IVS 230 / RICS Valuation — PS 2).

Computes the Market Rental Value (MRV) — the estimated amount for which an
interest in real property would be leased on the date of valuation between a
willing lessor and a willing lessee on appropriate lease terms in an arm's
length transaction.

Formulas:
    market_rental_value = gla × rent_per_m2   (annual EGP — full market rent)

    Gross lease (landlord pays operating costs):
        net_rent_per_m2     = rent_per_m2 − operating_costs_per_m2
        net_rent_to_landlord = gla × net_rent_per_m2

    Net lease (tenant pays operating costs directly):
        net_rent_to_landlord = gla × rent_per_m2   (no operating deduction)

    Effective rent (accounts for rent-free incentive period):
        effective_rent = gla × rent_per_m2 × (lease_term_months − rent_free_months)
                       / lease_term_months

Safety:
    This engine is STANDALONE. MRV does NOT automatically replace the market
    value in any report or `/api/valuation` response.
"""

from decimal import Decimal
from typing import Optional

from .base import (
    EngineResult, AuditEntry, ValidationIssue, ValuationEngine,
)

_VALID_LEASE_TYPES = {"gross", "net"}
_HIGH_RENT_FREE_RATIO: float = 0.20   # rent-free > 20% of term → warn


class MarketRentalEngine(ValuationEngine):
    """
    Market Rental Value engine — Phase 16.5 v1.

    Inputs (dict keys):
        gla                      float  required (> 0) — Gross Leasable Area (m²)
        rent_per_m2              float  required (> 0) — annual rent EGP/m²
        gross_or_net_lease       str    required: "gross" | "net"
        operating_costs_per_m2   float  optional (≥ 0) — annual EGP/m² (relevant for gross)
        rent_free_months         int    optional (≥ 0) — lease incentive months
        lease_term_months        int    optional (> 0) — total lease term in months

    Outputs (EngineResult):
        value      = market_rental_value (Decimal, annual EGP)
        confidence = high | medium | low | insufficient
        metadata   = {gla, rent_per_m2, lease_type, market_rental_value,
                      net_rent_to_landlord, operating_costs_per_m2,
                      rent_free_months, lease_term_months,
                      effective_rent, effective_rent_per_m2}
    """

    name    = "market_rental"
    version = "1.0.0"

    # ------------------------------------------------------------------
    # Abstract method implementations
    # ------------------------------------------------------------------

    def validate(self, inputs: dict) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        gla = inputs.get("gla", 0) or 0
        if float(gla) <= 0:
            issues.append(ValidationIssue(
                severity="error",
                code="MISSING_GLA",
                message=f"gla (Gross Leasable Area) must be > 0 m²; got {gla}",
            ))

        rent = inputs.get("rent_per_m2", 0) or 0
        if float(rent) <= 0:
            issues.append(ValidationIssue(
                severity="error",
                code="MISSING_RENT_PER_M2",
                message=f"rent_per_m2 must be > 0 EGP/m²/year; got {rent}",
            ))

        lease_type = inputs.get("gross_or_net_lease")
        if lease_type is None:
            issues.append(ValidationIssue(
                severity="error",
                code="MISSING_LEASE_TYPE",
                message="gross_or_net_lease is required: 'gross' or 'net'",
            ))
        elif str(lease_type).lower() not in _VALID_LEASE_TYPES:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_LEASE_TYPE",
                message=(
                    f"gross_or_net_lease must be 'gross' or 'net'; got '{lease_type}'"
                ),
            ))

        op_costs = inputs.get("operating_costs_per_m2")
        if op_costs is not None and float(op_costs) < 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_OPERATING_COSTS",
                message=f"operating_costs_per_m2 must be ≥ 0; got {op_costs}",
            ))
        if (
            op_costs is None
            and lease_type is not None
            and str(lease_type).lower() == "gross"
        ):
            issues.append(ValidationIssue(
                severity="warning",
                code="MISSING_OPERATING_COSTS",
                message=(
                    "operating_costs_per_m2 not supplied for gross lease — "
                    "net rent to landlord will equal gross rent; may overstate net income"
                ),
            ))

        lt_months = inputs.get("lease_term_months")
        if lt_months is None:
            issues.append(ValidationIssue(
                severity="warning",
                code="MISSING_LEASE_TERM",
                message=(
                    "lease_term_months not supplied — "
                    "effective rent (rent-free adjusted) cannot be computed"
                ),
            ))
        elif int(lt_months) <= 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_LEASE_TERM",
                message=f"lease_term_months must be > 0; got {lt_months}",
            ))

        rf_months = inputs.get("rent_free_months")
        if rf_months is not None:
            rf = int(rf_months)
            if rf < 0:
                issues.append(ValidationIssue(
                    severity="error",
                    code="INVALID_RENT_FREE_MONTHS",
                    message=f"rent_free_months must be ≥ 0; got {rf_months}",
                ))
            elif lt_months is not None and rf >= int(lt_months):
                issues.append(ValidationIssue(
                    severity="error",
                    code="INVALID_RENT_FREE_MONTHS",
                    message=(
                        f"rent_free_months {rf} ≥ lease_term_months {lt_months} — "
                        "rent-free period cannot equal or exceed the full lease term"
                    ),
                ))
            elif lt_months is not None and rf / int(lt_months) > _HIGH_RENT_FREE_RATIO:
                issues.append(ValidationIssue(
                    severity="warning",
                    code="HIGH_RENT_FREE_RATIO",
                    message=(
                        f"rent_free_months {rf} is {rf/int(lt_months):.0%} of lease term — "
                        f"exceeds typical {_HIGH_RENT_FREE_RATIO:.0%} threshold; "
                        "verify market conditions"
                    ),
                ))

        return issues

    def calculate(self, inputs: dict) -> EngineResult:
        """GLA × rent → lease type adjustment → rent-free → EngineResult."""
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

        gla        = float(inputs["gla"])
        rent_pm2   = float(inputs["rent_per_m2"])
        lease_type = str(inputs["gross_or_net_lease"]).lower()
        op_costs   = float(inputs.get("operating_costs_per_m2") or 0)
        lt_months  = inputs.get("lease_term_months")
        rf_months  = inputs.get("rent_free_months")

        audit_trail: list[AuditEntry] = []

        # ── Step 1: Market Rental Value (gross headline rent) ─────────
        mrv = gla * rent_pm2
        audit_trail.append(AuditEntry(
            step_name="Calculate Market Rental Value (MRV)",
            inputs={"gla": gla, "rent_per_m2": rent_pm2},
            outputs={"market_rental_value": round(mrv, 2)},
            formula="market_rental_value = gla × rent_per_m2",
            references=["IVS 230: Market Rental Value", "RICS PS 2: Market Rent"],
        ))

        # ── Step 2: Net rent by lease type ───────────────────────────
        if lease_type == "gross":
            net_rent_pm2   = rent_pm2 - op_costs
            net_rent       = gla * net_rent_pm2
            lease_note     = f"gross lease — landlord pays {op_costs:.2f} EGP/m²/yr operating costs"
        else:
            net_rent_pm2   = rent_pm2
            net_rent       = gla * rent_pm2
            lease_note     = "net lease — tenant pays operating costs; full rent to landlord"

        audit_trail.append(AuditEntry(
            step_name="Determine net rent by lease type",
            inputs={
                "lease_type":              lease_type,
                "rent_per_m2":             rent_pm2,
                "operating_costs_per_m2":  op_costs,
                "gla":                     gla,
            },
            outputs={
                "net_rent_per_m2":     round(net_rent_pm2, 2),
                "net_rent_to_landlord": round(net_rent, 2),
                "note":                lease_note,
            },
            formula=(
                "gross: net_rent = gla × (rent_per_m2 − op_costs); "
                "net: net_rent = gla × rent_per_m2"
            ),
            references=["RICS: Gross vs Net Lease", "EGVS_5.5: Lease Adjustment"],
        ))

        # ── Step 3: Effective rent (rent-free adjustment) ─────────────
        effective_rent: Optional[float] = None
        effective_rent_pm2: Optional[float] = None
        if lt_months is not None:
            lt  = int(lt_months)
            rf  = int(rf_months) if rf_months is not None else 0
            effective_rent_pm2 = rent_pm2 * (lt - rf) / lt
            effective_rent     = gla * effective_rent_pm2
            audit_trail.append(AuditEntry(
                step_name="Apply rent-free period — effective rent",
                inputs={
                    "rent_per_m2":       rent_pm2,
                    "lease_term_months": lt,
                    "rent_free_months":  rf,
                    "gla":               gla,
                },
                outputs={
                    "effective_rent_per_m2": round(effective_rent_pm2, 2),
                    "effective_rent":        round(effective_rent, 2),
                },
                formula=(
                    "effective_rent = gla × rent_per_m2 × "
                    "(lease_term_months − rent_free_months) / lease_term_months"
                ),
                references=["RICS: Effective Rent", "EGVS_5.6: Lease Incentives"],
            ))

        # ── Confidence ────────────────────────────────────────────────
        has_op_costs  = inputs.get("operating_costs_per_m2") is not None
        has_lt        = lt_months is not None
        has_rf        = rf_months is not None

        if has_op_costs and has_lt and has_rf:
            confidence = "high"
        elif has_op_costs or has_lt or has_rf:
            confidence = "medium"
        else:
            confidence = "low"

        metadata: dict = {
            "gla":                   gla,
            "rent_per_m2":           rent_pm2,
            "lease_type":            lease_type,
            "market_rental_value":   round(mrv, 2),
            "net_rent_per_m2":       round(net_rent_pm2, 2),
            "net_rent_to_landlord":  round(net_rent, 2),
            "operating_costs_per_m2": op_costs,
            "rent_free_months":       rf_months,
            "lease_term_months":      lt_months,
            "effective_rent":         round(effective_rent, 2) if effective_rent is not None else None,
            "effective_rent_per_m2":  round(effective_rent_pm2, 2) if effective_rent_pm2 is not None else None,
        }

        return EngineResult(
            engine_name=self.name,
            value=Decimal(str(round(mrv, 2))),
            confidence=confidence,
            audit_trail=audit_trail,
            issues=issues,
            metadata=metadata,
        )
