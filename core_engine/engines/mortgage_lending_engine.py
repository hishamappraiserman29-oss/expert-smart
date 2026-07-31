"""
Mortgage Lending Value Engine (IVS 230 / Basel III-IV / RICS Mortgage Valuation).

Computes the sustainable Mortgage Lending Value (MLV) — the conservative long-term
value of a property used to size secured lending.

Formula:
    lending_value    = market_value × (1 − haircut)
    max_approved_loan = lending_value × ltv

    NOI coverage (if stable_noi and requested_loan_amount supplied):
        noi_coverage = stable_noi / (requested_loan_amount × _ASSUMED_LOAN_RATE)

Safety:
    This engine is STANDALONE. lending_value and max_approved_loan are informational
    outputs for the analyst. They do NOT automatically replace market_value in any
    report or API response.

Key distinctions from Basel LTV:
    • haircut = margin of safety applied to market_value (e.g. 0.20 = 20% cushion)
    • ltv     = loan fraction applied to lending_value (e.g. 0.70 = 70% of MLV)
    • These together cap the loan at market_value × (1−haircut) × ltv
"""

from decimal import Decimal
from typing import Optional

from .base import (
    EngineResult, AuditEntry, ValidationIssue, ValuationEngine,
)

_DEFAULT_HAIRCUT: float    = 0.20    # 20% margin of safety
_DEFAULT_LTV: float        = 0.70    # 70% of lending value
_HIGH_LTV_WARN: float      = 0.80    # LTV > 80% → risk flag
_MIN_LIFE_WARN_YEARS: int  = 15      # remaining life < 15y → flag
_ASSUMED_LOAN_RATE: float  = 0.08    # 8% p.a. interest-only for DSCR proxy
_MIN_NOI_COVERAGE: float   = 1.25    # DSCR below 1.25 → warning


class MortgageLendingEngine(ValuationEngine):
    """
    Mortgage Lending Value engine — Phase 16.4 v1.

    Inputs (dict keys):
        market_value              float  required (> 0) — current market value
        haircut                   float  optional [0, 1), default 0.20
        ltv                       float  optional (0, 1], default 0.70
        requested_loan_amount     float  optional (≥ 0) — loan size to assess
        stable_noi                float  optional (≥ 0) — income for DSCR check
        remaining_economic_life   int    optional (> 0) — years left in asset life

    Outputs (EngineResult):
        value      = lending_value (Decimal, EGP)
        confidence = high | medium | low | insufficient
        metadata   = {market_value, haircut, ltv, lending_value, max_approved_loan,
                      actual_ltv, noi_coverage, remaining_economic_life, risk_notes}
    """

    name    = "mortgage_lending"
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

        haircut = inputs.get("haircut")
        if haircut is not None:
            hv = float(haircut)
            if not (0.0 <= hv < 1.0):
                issues.append(ValidationIssue(
                    severity="error",
                    code="INVALID_HAIRCUT",
                    message=f"haircut must be in [0, 1); got {haircut}",
                ))
            elif hv == 0.0:
                issues.append(ValidationIssue(
                    severity="warning",
                    code="ZERO_HAIRCUT",
                    message=(
                        "haircut = 0 — lending_value equals market_value; "
                        "no margin of safety applied"
                    ),
                ))

        ltv = inputs.get("ltv")
        if ltv is not None:
            lv = float(ltv)
            if not (0.0 < lv <= 1.0):
                issues.append(ValidationIssue(
                    severity="error",
                    code="INVALID_LTV",
                    message=f"ltv must be in (0, 1]; got {ltv}",
                ))
            elif lv > _HIGH_LTV_WARN:
                issues.append(ValidationIssue(
                    severity="warning",
                    code="HIGH_LTV",
                    message=(
                        f"ltv {lv:.0%} exceeds {_HIGH_LTV_WARN:.0%} — elevated credit risk; "
                        "verify lender policy and Basel capital requirements"
                    ),
                ))

        rel = inputs.get("remaining_economic_life")
        if rel is not None:
            if int(rel) < _MIN_LIFE_WARN_YEARS:
                issues.append(ValidationIssue(
                    severity="warning",
                    code="LOW_REMAINING_LIFE",
                    message=(
                        f"remaining_economic_life {rel} years < {_MIN_LIFE_WARN_YEARS} years — "
                        "collateral value may decline faster than loan amortisation"
                    ),
                ))

        req_loan = inputs.get("requested_loan_amount")
        if req_loan is not None and float(req_loan) < 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_LOAN_AMOUNT",
                message=f"requested_loan_amount must be ≥ 0; got {req_loan}",
            ))

        stable_noi = inputs.get("stable_noi")
        if stable_noi is not None and float(stable_noi) < 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_STABLE_NOI",
                message=f"stable_noi must be ≥ 0; got {stable_noi}",
            ))

        return issues

    def calculate(self, inputs: dict) -> EngineResult:
        """market_value → haircut → lending_value → LTV → loan assessment → EngineResult."""
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

        mv              = float(inputs["market_value"])
        haircut_in      = inputs.get("haircut")
        ltv_in          = inputs.get("ltv")
        req_loan        = inputs.get("requested_loan_amount")
        stable_noi_in   = inputs.get("stable_noi")
        rel             = inputs.get("remaining_economic_life")

        haircut         = float(haircut_in) if haircut_in is not None else _DEFAULT_HAIRCUT
        ltv             = float(ltv_in)    if ltv_in    is not None else _DEFAULT_LTV

        audit_trail: list[AuditEntry] = []
        risk_notes: list[str] = []

        # ── Step 1: Apply haircut → lending value ─────────────────────
        lending_value = mv * (1.0 - haircut)
        audit_trail.append(AuditEntry(
            step_name="Apply haircut — derive Mortgage Lending Value",
            inputs={
                "market_value": round(mv, 2),
                "haircut":      haircut,
                "source":       "caller-supplied" if haircut_in is not None else f"default ({_DEFAULT_HAIRCUT:.0%})",
            },
            outputs={"lending_value": round(lending_value, 2)},
            formula="lending_value = market_value × (1 − haircut)",
            references=["IVS 230: Mortgage Lending Value", "RICS: Secured Lending Guidance"],
        ))

        # ── Step 2: Compute maximum approved loan ────────────────────
        max_approved_loan = lending_value * ltv
        audit_trail.append(AuditEntry(
            step_name="Compute maximum approved loan (LTV cap)",
            inputs={
                "lending_value": round(lending_value, 2),
                "ltv":           ltv,
                "source":        "caller-supplied" if ltv_in is not None else f"default ({_DEFAULT_LTV:.0%})",
            },
            outputs={"max_approved_loan": round(max_approved_loan, 2)},
            formula="max_approved_loan = lending_value × ltv",
            references=["Basel III/IV: LTV Capital Requirements", "EGVS_9.1: Secured Lending"],
        ))

        # ── Step 3: Assess requested loan (conditional) ──────────────
        actual_ltv: Optional[float] = None
        if req_loan is not None:
            req = float(req_loan)
            actual_ltv = req / mv if mv > 0 else None
            loan_ok    = req <= max_approved_loan
            if not loan_ok:
                excess = req - max_approved_loan
                risk_notes.append(
                    f"Requested loan {req:,.0f} exceeds max_approved_loan "
                    f"{max_approved_loan:,.0f} by {excess:,.0f} EGP"
                )
                issues.append(ValidationIssue(
                    severity="warning",
                    code="LOAN_EXCEEDS_LENDING_VALUE",
                    message=(
                        f"requested_loan_amount {req:,.0f} exceeds "
                        f"max_approved_loan {max_approved_loan:,.0f}"
                    ),
                ))
            audit_trail.append(AuditEntry(
                step_name="Assess requested loan against lending value",
                inputs={
                    "requested_loan_amount": round(req, 2),
                    "max_approved_loan":     round(max_approved_loan, 2),
                    "market_value":          round(mv, 2),
                },
                outputs={
                    "actual_ltv":   round(actual_ltv, 4) if actual_ltv is not None else None,
                    "loan_approved": loan_ok,
                },
                formula="actual_ltv = requested_loan / market_value",
                references=["EGVS_9.2: Loan Assessment"],
            ))

        # ── Step 4: NOI coverage ratio (conditional) ─────────────────
        noi_coverage: Optional[float] = None
        if stable_noi_in is not None and req_loan is not None and float(req_loan) > 0:
            noi = float(stable_noi_in)
            debt_service_proxy = float(req_loan) * _ASSUMED_LOAN_RATE
            noi_coverage = noi / debt_service_proxy if debt_service_proxy > 0 else None
            if noi_coverage is not None and noi_coverage < _MIN_NOI_COVERAGE:
                risk_notes.append(
                    f"NOI coverage {noi_coverage:.2f}× is below minimum "
                    f"{_MIN_NOI_COVERAGE:.2f}× (assumed rate {_ASSUMED_LOAN_RATE:.0%} p.a.)"
                )
                issues.append(ValidationIssue(
                    severity="warning",
                    code="LOW_NOI_COVERAGE",
                    message=(
                        f"NOI coverage ratio {noi_coverage:.2f}× < {_MIN_NOI_COVERAGE:.2f}× "
                        f"(DSCR proxy at {_ASSUMED_LOAN_RATE:.0%} assumed rate)"
                    ),
                ))
            audit_trail.append(AuditEntry(
                step_name="Compute NOI income coverage ratio (DSCR proxy)",
                inputs={
                    "stable_noi":              round(noi, 2),
                    "requested_loan_amount":   round(float(req_loan), 2),
                    "assumed_rate":            _ASSUMED_LOAN_RATE,
                    "debt_service_proxy":      round(debt_service_proxy, 2),
                },
                outputs={"noi_coverage": round(noi_coverage, 4) if noi_coverage else None},
                formula="noi_coverage = stable_noi / (requested_loan × assumed_rate)",
                references=["EGVS_9.3: Debt Service Coverage", "Basel: DSCR Requirements"],
            ))

        if rel is not None and int(rel) < _MIN_LIFE_WARN_YEARS:
            risk_notes.append(
                f"Remaining economic life {rel} years is below minimum "
                f"{_MIN_LIFE_WARN_YEARS} years threshold"
            )

        # ── Confidence ────────────────────────────────────────────────
        has_explicit_haircut = haircut_in is not None
        has_explicit_ltv     = ltv_in is not None
        has_rel              = rel is not None

        if has_explicit_haircut and has_explicit_ltv and has_rel:
            confidence = "high"
        elif has_explicit_haircut or has_explicit_ltv:
            confidence = "medium"
        else:
            confidence = "low"

        metadata: dict = {
            "market_value":            round(mv, 2),
            "haircut":                 haircut,
            "haircut_source":          "caller-supplied" if haircut_in is not None else "default",
            "ltv":                     ltv,
            "ltv_source":              "caller-supplied" if ltv_in is not None else "default",
            "lending_value":           round(lending_value, 2),
            "max_approved_loan":       round(max_approved_loan, 2),
            "actual_ltv":              round(actual_ltv, 4) if actual_ltv is not None else None,
            "noi_coverage":            round(noi_coverage, 4) if noi_coverage is not None else None,
            "remaining_economic_life": rel,
            "risk_notes":              risk_notes,
        }

        return EngineResult(
            engine_name=self.name,
            value=Decimal(str(round(lending_value, 2))),
            confidence=confidence,
            audit_trail=audit_trail,
            issues=issues,
            metadata=metadata,
        )
