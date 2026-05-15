from decimal import Decimal

from engines.base import AuditEntry
from .base import PurposeAdapter, PurposeResult, Adjustment, ValidationIssue


_VALID_BORROWER_PROFILES = {"standard", "preferred", "subprime", "first_time_buyer"}
_VALID_MARKET_CONDITIONS  = {"good", "neutral", "weak"}


class MortgageValueAdapter(PurposeAdapter):
    """
    Lender valuation per Egyptian Central Bank (CBE) and Basel III guidelines.

    Applies three sequential haircuts:
      1. Conservative appraisal  — min(comparative, cost)
      2. Forced-sale haircut     — liquidation discount (10–20% by risk tier)
      3. LTV cap                 — lender ceiling (70–85% by risk tier)
    Then an optional income-based backstop and market-cycle multiplier.
    """

    name    = "mortgage"
    version = "1.0.0"

    def __init__(self) -> None:
        # Risk tier rules — keyed by borrower_profile
        self.risk_tiers: dict[str, dict] = {
            "standard": {"ltv": 0.80, "haircut": 0.15, "confidence_mod":  0},
            "preferred": {"ltv": 0.85, "haircut": 0.10, "confidence_mod":  1},
            "subprime":  {"ltv": 0.70, "haircut": 0.20, "confidence_mod": -1},
        }

        # Market cycle multipliers
        self.market_cycle_good    = 1.05   # +5% — buoyant market
        self.market_cycle_weak    = 0.95   # −5% — distressed market
        self.market_cycle_neutral = 1.00   #  0% — steady state

    # ──────────────────────────────────────────────────────────────────────────
    # Abstract method implementations
    # ──────────────────────────────────────────────────────────────────────────

    def validate_context(self, three_values: dict, inputs: dict) -> list[ValidationIssue]:
        """Validate engine values and lender-specific inputs."""
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

        ltv = inputs.get("ltv")
        if ltv is not None and not (0.0 < ltv <= 1.0):
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_LTV",
                message=f"ltv must be in (0.0, 1.0]; got {ltv}",
            ))

        profile = inputs.get("borrower_profile")
        if profile is not None and profile not in _VALID_BORROWER_PROFILES:
            issues.append(ValidationIssue(
                severity="warning",
                code="UNKNOWN_BORROWER_PROFILE",
                message=(
                    f"Unrecognised borrower_profile '{profile}'; "
                    f"expected one of {sorted(_VALID_BORROWER_PROFILES)}. Defaulting to standard."
                ),
            ))

        mkt = inputs.get("market_conditions")
        if mkt is not None and mkt not in _VALID_MARKET_CONDITIONS:
            issues.append(ValidationIssue(
                severity="warning",
                code="UNKNOWN_MARKET_CONDITIONS",
                message=(
                    f"Unrecognised market_conditions '{mkt}'; "
                    f"expected one of {sorted(_VALID_MARKET_CONDITIONS)}. Defaulting to neutral."
                ),
            ))

        return issues

    def adjust(self, three_values: dict, inputs: dict) -> PurposeResult:
        """Apply CBE/Basel III lender haircuts and return mortgage value."""
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

        # ── Resolve risk tier ─────────────────────────────────────────────────
        raw_profile    = inputs.get("borrower_profile", "standard")
        borrower_profile = raw_profile if raw_profile in self.risk_tiers else "standard"
        profile_rules    = self.risk_tiers[borrower_profile]

        ltv_cap              = profile_rules["ltv"]
        forced_sale_haircut  = profile_rules["haircut"]
        confidence_mod       = profile_rules["confidence_mod"]

        # ── Resolve market conditions ─────────────────────────────────────────
        mkt = inputs.get("market_conditions", "neutral")
        if mkt == "good":
            market_cycle_mult = self.market_cycle_good
        elif mkt == "weak":
            market_cycle_mult = self.market_cycle_weak
        else:
            mkt               = "neutral"
            market_cycle_mult = self.market_cycle_neutral

        audit_trail: list[AuditEntry] = []

        # ── Step 1: Conservative appraisal = min(comparable, cost) ───────────
        comp = three_values["comparative"]
        cost = three_values["cost"]
        appraised_value = min(comp, cost)

        audit_trail.append(AuditEntry(
            step_name="Select conservative appraisal (min of comparable and cost)",
            inputs={"comparative": float(comp), "cost": float(cost)},
            outputs={"appraised_value": float(appraised_value)},
            formula="appraised = min(comp, cost)",
            references=["CBE_Circular_Mortgage_Rules"],
        ))

        # ── Step 2: Forced-sale haircut ───────────────────────────────────────
        after_haircut = appraised_value * Decimal(str(1 - forced_sale_haircut))

        audit_trail.append(AuditEntry(
            step_name="Apply forced-sale haircut",
            inputs={
                "appraised_value":  float(appraised_value),
                "haircut_pct":      forced_sale_haircut * 100,
            },
            outputs={"after_haircut": float(after_haircut)},
            formula=f"after_haircut = appraised × (1 − {forced_sale_haircut})",
            references=["Basel_III_LGD", "Egyptian_Lender_Standards"],
        ))

        # ── Step 3: LTV cap ───────────────────────────────────────────────────
        after_ltv = after_haircut * Decimal(str(ltv_cap))
        mortgage_value = after_ltv

        audit_trail.append(AuditEntry(
            step_name="Apply LTV cap",
            inputs={"after_haircut": float(after_haircut), "ltv_cap": ltv_cap},
            outputs={"after_ltv": float(after_ltv)},
            formula=f"after_ltv = after_haircut × {ltv_cap}",
            references=["CBE_Circular_80_Percent_LTV"],
        ))

        # ── Step 4: Income-based backstop (optional limiter) ─────────────────
        income           = three_values["income"]
        income_based_cap = (income / Decimal("0.10")) * Decimal("0.75")
        capped_by_income = income_based_cap < mortgage_value
        mortgage_value   = min(mortgage_value, income_based_cap)

        audit_trail.append(AuditEntry(
            step_name="Apply income-based cap (optional)",
            inputs={
                "income":       float(income),
                "cap_rate":     "0.10 (assumed)",
                "income_cap":   float(income_based_cap),
                "pre_cap_value": float(after_ltv),
            },
            outputs={
                "income_cap_applied": capped_by_income,
                "mortgage_value":     float(mortgage_value),
            },
            formula="income_cap = (income / 0.10) × 0.75",
            references=[],
        ))

        # ── Step 5: Market cycle adjustment (only when not neutral) ───────────
        pre_cycle_value = mortgage_value
        if mkt != "neutral":
            mortgage_value = mortgage_value * Decimal(str(market_cycle_mult))
            audit_trail.append(AuditEntry(
                step_name="Apply market conditions adjustment",
                inputs={
                    "market_conditions": mkt,
                    "multiplier":        market_cycle_mult,
                    "pre_cycle":         float(pre_cycle_value),
                },
                outputs={"adjusted_mortgage": float(mortgage_value)},
                formula=f"adjusted = mortgage × {market_cycle_mult}",
                references=[],
            ))

        # ── Confidence ────────────────────────────────────────────────────────
        if borrower_profile == "preferred":
            confidence = "high"
        elif borrower_profile == "subprime":
            confidence = "low"
        else:
            confidence = "medium"

        # Apply confidence modifier (guards against future preset changes)
        if confidence_mod == 1 and confidence == "medium":
            confidence = "high"
        elif confidence_mod == -1 and confidence == "medium":
            confidence = "low"

        # ── Adjustments ───────────────────────────────────────────────────────
        adjustments: list[Adjustment] = [
            Adjustment(
                factor_name="APPRAISAL_CONSERVATIVE",
                before_value=comp,
                after_value=appraised_value,
                percentage=float(appraised_value / comp),
                reason="Use min(comparable, cost) for lender safety",
            ),
            Adjustment(
                factor_name="FORCED_SALE_HAIRCUT",
                before_value=appraised_value,
                after_value=after_haircut,
                percentage=1 - forced_sale_haircut,
                reason=f"Quick liquidation discount {forced_sale_haircut * 100:.0f}%",
            ),
            Adjustment(
                factor_name="LTV_CAP",
                before_value=after_haircut,
                after_value=after_ltv,   # value right after LTV, before income cap
                percentage=ltv_cap,
                reason=f"Lender LTV cap {ltv_cap * 100:.0f}%",
            ),
        ]

        metadata = {
            "appraised_value":          float(appraised_value),
            "after_haircut":            float(after_haircut),
            "ltv_applied":              ltv_cap,
            "ltv_cap_type":             borrower_profile,
            "forced_sale_haircut_pct":  forced_sale_haircut * 100,
            "income_cap_applied":       capped_by_income,
            "income_based_cap":         float(income_based_cap),
            "market_conditions":        mkt,
            "market_cycle_multiplier":  market_cycle_mult,
            "loan_term_years":          inputs.get("loan_term_years", 20),
            "property_type":            inputs.get("property_type", "residential"),
            "risk_tier":                borrower_profile,
        }

        disclosures = [
            "CBE_Circular_Mortgage_Rules",
            "Basel_III_LGD",
            "Egyptian_Lender_Standards",
            "EGVS_2.1",   # Assumptions and market conditions
            "EGVS_2.3",   # Valuation date + purpose
        ]

        return PurposeResult(
            purpose_name=self.name,
            adjusted_value=Decimal(str(round(float(mortgage_value), 2))),
            confidence=confidence,
            adjustments=adjustments,
            audit_trail=audit_trail,
            disclosures=disclosures,
            metadata=metadata,
            issues=issues,
        )
