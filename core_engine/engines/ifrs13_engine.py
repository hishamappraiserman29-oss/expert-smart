"""
IFRS 13 Fair Value Engine (IVS 104 / IFRS 13 Fair Value Measurement).

Supports fair value measurement and disclosure for investment properties,
PPE, and other assets subject to IFRS 13 revaluation.

Formula:
    revaluation_amount      = fair_value − carrying_amount   (signed; + = surplus)
    revaluation_surplus     = max(revaluation_amount, 0)
    revaluation_deficit     = max(−revaluation_amount, 0)

    net_book_value (if accumulated_depreciation supplied):
        net_book_value  = carrying_amount − accumulated_depreciation
        uplift_from_nbv = fair_value − net_book_value

IFRS 13 Fair Value Hierarchy:
    Level 1 — Quoted prices in active markets for identical assets (most reliable)
    Level 2 — Observable inputs other than Level 1 prices (comparable transactions)
    Level 3 — Unobservable inputs (valuation models, DCF, cost approach)

Confidence mapping:
    Level 1 → high   (market-observable, minimal estimation)
    Level 2 → medium (observable analogues, some judgement)
    Level 3 → low    (model-dependent, extensive disclosure required)

Safety:
    This engine is STANDALONE — fair value output does NOT automatically trigger
    accounting entries or replace market_value in any report or API response.
    No integration with any accounting system.
"""

from decimal import Decimal
from typing import Optional

from .base import (
    EngineResult, AuditEntry, ValidationIssue, ValuationEngine,
)

_SIGNIFICANT_CHANGE_THRESHOLD: float = 0.20   # 20% of carrying amount
_LARGE_UPLIFT_THRESHOLD: float        = 0.50   # 50% above NBV
_VALID_LEVELS = {1, 2, 3}

_DISCLOSURE_TEMPLATES = {
    1: (
        "Level 1 — Quoted market price: Disclose the quoted price used, "
        "the principal or most advantageous market, and the date of the quote."
    ),
    2: (
        "Level 2 — Observable inputs: Disclose valuation technique(s) used, "
        "observable market inputs applied (e.g. comparable transactions, yields), "
        "and any significant adjustments made."
    ),
    3: (
        "Level 3 — Unobservable inputs: Disclose valuation technique(s), "
        "all significant unobservable inputs and their ranges, "
        "a sensitivity analysis showing the effect of changes to unobservable inputs, "
        "and a reconciliation of opening to closing balances (IFRS 13 para. 93(e))."
    ),
}

_LEVEL_DESCRIPTIONS = {
    1: "Quoted prices in active markets for identical assets",
    2: "Observable inputs other than quoted prices (Level 1)",
    3: "Unobservable inputs — significant estimation required",
}


class IFRS13Engine(ValuationEngine):
    """
    IFRS 13 Fair Value engine — Phase 16.5 v1.

    Inputs (dict keys):
        fair_value                float  required (> 0) — assessed fair value
        carrying_amount           float  required (≥ 0) — current book value
        accumulated_depreciation  float  optional (≥ 0) — total accumulated dep.
        ifrs_level                int    required: 1 | 2 | 3
        asset_class               str    optional — e.g. "investment_property", "ppe"

    Outputs (EngineResult):
        value      = fair_value (Decimal, EGP)
        confidence = high (L1) | medium (L2) | low (L3) | insufficient (errors)
        metadata   = {fair_value, carrying_amount, accumulated_depreciation,
                      ifrs_level, level_description, revaluation_amount,
                      revaluation_surplus, revaluation_deficit,
                      net_book_value, uplift_from_nbv,
                      disclosure_notes, input_level_validation, asset_class}
    """

    name    = "ifrs13"
    version = "1.0.0"

    # ------------------------------------------------------------------
    # Abstract method implementations
    # ------------------------------------------------------------------

    def validate(self, inputs: dict) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        fv = inputs.get("fair_value")
        if fv is None:
            issues.append(ValidationIssue(
                severity="error",
                code="MISSING_FAIR_VALUE",
                message="fair_value is required",
            ))
        elif float(fv) <= 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_FAIR_VALUE",
                message=f"fair_value must be > 0; got {fv}",
            ))

        ca = inputs.get("carrying_amount")
        if ca is None:
            issues.append(ValidationIssue(
                severity="error",
                code="MISSING_CARRYING_AMOUNT",
                message=(
                    "carrying_amount is required "
                    "(use 0 for fully depreciated assets)"
                ),
            ))
        elif float(ca) < 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_CARRYING_AMOUNT",
                message=f"carrying_amount must be ≥ 0; got {ca}",
            ))

        level = inputs.get("ifrs_level")
        if level is None:
            issues.append(ValidationIssue(
                severity="error",
                code="MISSING_IFRS_LEVEL",
                message="ifrs_level is required: 1 (quoted price), 2 (observable), or 3 (unobservable)",
            ))
        elif int(level) not in _VALID_LEVELS:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_IFRS_LEVEL",
                message=(
                    f"ifrs_level must be 1, 2, or 3 per IFRS 13 hierarchy; got {level}"
                ),
            ))

        acc_dep = inputs.get("accumulated_depreciation")
        if acc_dep is None:
            issues.append(ValidationIssue(
                severity="warning",
                code="MISSING_ACCUMULATED_DEPRECIATION",
                message=(
                    "accumulated_depreciation not supplied — "
                    "net book value (NBV) cannot be derived"
                ),
            ))
        elif float(acc_dep) < 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_ACCUMULATED_DEPRECIATION",
                message=f"accumulated_depreciation must be ≥ 0; got {acc_dep}",
            ))
        elif ca is not None and float(acc_dep) > float(ca):
            issues.append(ValidationIssue(
                severity="error",
                code="ACCUMULATED_DEP_EXCEEDS_CARRYING",
                message=(
                    f"accumulated_depreciation {acc_dep} > "
                    f"carrying_amount {ca} — verify asset records"
                ),
            ))

        return issues

    def calculate(self, inputs: dict) -> EngineResult:
        """fair_value → level validation → revaluation → NBV → disclosure → EngineResult."""
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

        fv      = float(inputs["fair_value"])
        ca      = float(inputs["carrying_amount"])
        level   = int(inputs["ifrs_level"])
        acc_dep = inputs.get("accumulated_depreciation")
        ac      = inputs.get("asset_class", "unspecified")

        audit_trail: list[AuditEntry] = []

        # ── Step 1: Validate and describe hierarchy level ─────────────
        level_desc    = _LEVEL_DESCRIPTIONS[level]
        input_level_validation = (
            f"Level {level} validated — {level_desc}. "
            f"Confidence: {'high' if level==1 else 'medium' if level==2 else 'low'}."
        )
        audit_trail.append(AuditEntry(
            step_name="Validate IFRS 13 fair value hierarchy level",
            inputs={"ifrs_level": level, "asset_class": ac},
            outputs={
                "level_description":       level_desc,
                "input_level_validation":  input_level_validation,
            },
            formula="IFRS 13 para. 72–90: Fair Value Hierarchy Level 1 / 2 / 3",
            references=["IFRS 13 para. 76: Level 1", "IFRS 13 para. 81: Level 2",
                        "IFRS 13 para. 86: Level 3"],
        ))

        # ── Step 2: Revaluation surplus / (deficit) ───────────────────
        reval_amount  = fv - ca
        reval_surplus = max(reval_amount, 0.0)
        reval_deficit = max(-reval_amount, 0.0)

        # Significant change warnings
        if ca > 0:
            change_ratio = abs(reval_amount) / ca
            if reval_surplus > 0 and change_ratio > _SIGNIFICANT_CHANGE_THRESHOLD:
                issues.append(ValidationIssue(
                    severity="warning",
                    code="SIGNIFICANT_REVALUATION_SURPLUS",
                    message=(
                        f"Revaluation surplus {reval_surplus:,.0f} EGP is "
                        f"{change_ratio:.0%} of carrying amount — "
                        "review valuation basis and consider third-party verification"
                    ),
                ))
            elif reval_deficit > 0 and change_ratio > _SIGNIFICANT_CHANGE_THRESHOLD:
                issues.append(ValidationIssue(
                    severity="warning",
                    code="SIGNIFICANT_REVALUATION_DEFICIT",
                    message=(
                        f"Revaluation deficit {reval_deficit:,.0f} EGP is "
                        f"{change_ratio:.0%} of carrying amount — "
                        "impairment indicators may need assessment under IAS 36"
                    ),
                ))

        audit_trail.append(AuditEntry(
            step_name="Compute revaluation surplus / (deficit)",
            inputs={"fair_value": round(fv, 2), "carrying_amount": round(ca, 2)},
            outputs={
                "revaluation_amount":  round(reval_amount, 2),
                "revaluation_surplus": round(reval_surplus, 2),
                "revaluation_deficit": round(reval_deficit, 2),
            },
            formula="revaluation_amount = fair_value − carrying_amount",
            references=["IAS 40: Investment Property Revaluation",
                        "IAS 16: PPE Revaluation Model", "IFRS 13: Fair Value"],
        ))

        # ── Step 3: Net Book Value (conditional) ──────────────────────
        nbv: Optional[float]         = None
        uplift_from_nbv: Optional[float] = None
        if acc_dep is not None:
            dep = float(acc_dep)
            nbv = ca - dep
            uplift_from_nbv = fv - nbv
            if nbv > 0 and uplift_from_nbv / nbv > _LARGE_UPLIFT_THRESHOLD:
                issues.append(ValidationIssue(
                    severity="warning",
                    code="LARGE_UPLIFT_FROM_NBV",
                    message=(
                        f"fair_value is {uplift_from_nbv/nbv:.0%} above NBV "
                        f"({nbv:,.0f} EGP) — "
                        "large movements from NBV should be separately disclosed"
                    ),
                ))
            audit_trail.append(AuditEntry(
                step_name="Derive net book value (NBV) and uplift",
                inputs={
                    "carrying_amount":          round(ca, 2),
                    "accumulated_depreciation": round(dep, 2),
                    "fair_value":               round(fv, 2),
                },
                outputs={
                    "net_book_value":   round(nbv, 2),
                    "uplift_from_nbv":  round(uplift_from_nbv, 2),
                },
                formula="NBV = carrying_amount − accumulated_depreciation; "
                        "uplift = fair_value − NBV",
                references=["IAS 36: Impairment / NBV", "IFRS 13: Fair Value vs NBV"],
            ))

        # ── Step 4: Disclosure requirements ───────────────────────────
        disclosure_notes = _DISCLOSURE_TEMPLATES[level]
        if level == 3:
            issues.append(ValidationIssue(
                severity="warning",
                code="LEVEL_3_EXTENSIVE_DISCLOSURE",
                message=(
                    "IFRS 13 Level 3 requires extensive disclosure including "
                    "sensitivity analysis and reconciliation of balances (para. 93)"
                ),
            ))
        audit_trail.append(AuditEntry(
            step_name="Generate IFRS 13 disclosure requirements",
            inputs={"ifrs_level": level},
            outputs={"disclosure_notes": disclosure_notes},
            formula="IFRS 13 para. 91–99: Disclosure Requirements by Level",
            references=["IFRS 13 para. 91: Disclosure", "IFRS 13 para. 93: Level 3 Disclosure"],
        ))

        # ── Confidence ────────────────────────────────────────────────
        confidence = {1: "high", 2: "medium", 3: "low"}[level]

        metadata: dict = {
            "fair_value":                round(fv, 2),
            "carrying_amount":           round(ca, 2),
            "accumulated_depreciation":  round(float(acc_dep), 2) if acc_dep is not None else None,
            "ifrs_level":                level,
            "level_description":         level_desc,
            "input_level_validation":    input_level_validation,
            "revaluation_amount":        round(reval_amount, 2),
            "revaluation_surplus":       round(reval_surplus, 2),
            "revaluation_deficit":       round(reval_deficit, 2),
            "net_book_value":            round(nbv, 2) if nbv is not None else None,
            "uplift_from_nbv":           round(uplift_from_nbv, 2) if uplift_from_nbv is not None else None,
            "disclosure_notes":          disclosure_notes,
            "asset_class":               ac,
        }

        return EngineResult(
            engine_name=self.name,
            value=Decimal(str(round(fv, 2))),
            confidence=confidence,
            audit_trail=audit_trail,
            issues=issues,
            metadata=metadata,
        )
