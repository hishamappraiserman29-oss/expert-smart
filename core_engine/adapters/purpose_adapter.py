"""
Purpose Compliance Adapter — applies valuation-purpose adjustments.

Wave 2 of the Composite Property Architecture. Takes a ComponentValuation
(baseline, from CompositeEngine — Wave 1) and a valuation purpose, and
produces an AdjustedValuation.

Honest design (mirrors Wave 1):
- Purposes with an explicit multiplier (Market / Financing / Liquidation /
  Insurance) → multiplier applied directly.
- Complex-route purposes (DCF / HABU / REIT / Usufruct / IFRS13 / ...) →
  multiplier 1.0 + route label + explicit NOTE that the deep logic is
  deferred to a later wave. The adapter does NOT fake those computations.

USPAP / IAAO:
- USPAP Standard 1 & 2 markers attached at component level (always).
- USPAP Standard 5 & 6 markers attached when the purpose is tax /
  mass-appraisal.
- IAAO COD / PRD / Assessment Ratio are POPULATION statistics — computed
  at the aggregate level (Wave 7), NOT per component. The adapter only
  sets the `iaao_block_triggered` flag.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from valuation_engines.composite_engine import ComponentValuation


# ─────────────────────────────────────────────────────────────────────
# Purpose rules catalog — 14 purposes
# ─────────────────────────────────────────────────────────────────────

PURPOSE_RULES: dict[str, dict[str, Any]] = {
    # ── 4 explicit-multiplier purposes ───────────────────────────────
    "البيع والشراء - القيمة السوقية العادلة (Market Value)": {
        "multiplier": 1.00,
        "route": "market_baseline",
        "deep": False,
    },
    "الرهن والتمويل البنكي - القيمة السوقية لأغراض التمويل (0.95x)": {
        "multiplier": 0.95,
        "route": "financing_risk_haircut",
        "deep": False,
    },
    "التصفية الإجبارية - القيمة التصفوية (Liquidation Value x0.82)": {
        "multiplier": 0.82,
        "route": "liquidation_distress_discount",
        "deep": False,
    },
    "التأمين - قيمة إعادة الإنشاء (Reinstatement Value x1.08)": {
        "multiplier": 1.08,
        "route": "insurance_reinstatement_premium",
        "deep": False,
        "note": (
            "1.08x applied on full baseline. NOTE: USPAP reinstatement "
            "is structure-only — land-component exclusion needs a "
            "structure/land split not present in Wave-1 baseline. "
            "Domain review (د. عبد الرؤوف) required."
        ),
    },
    # ── 10 complex-route purposes (multiplier 1.0 + NOTE deferred) ───
    "الاستحواذ والاندماج - القيمة الاستثمارية (Investment Value)": {
        "multiplier": 1.00,
        "route": "investment_synergy_route",
        "deep": True,
        "note": (
            "Investment Value needs synergy / hurdle-rate modelling — "
            "deferred to aggregation wave (synergy_adjustment_percent)."
        ),
    },
    "التحليل الاستثماري - IRR / NPV / DCF": {
        "multiplier": 1.00,
        "route": "financial_metrics_trigger",
        "deep": True,
        "note": (
            "IRR/NPV/DCF financial metrics deferred — requires cashflow "
            "schedule input not in Wave-1 baseline."
        ),
    },
    "تحديد الأجرة - القيمة الإيجارية العادلة (Rental Value)": {
        "multiplier": 1.00,
        "route": "rental_yield_route",
        "deep": True,
        "note": (
            "Annual rental-yield layout deferred — requires yield rate "
            "input + rental layout engine."
        ),
    },
    "الضرائب - القيمة للأغراض الضريبية / الضريبة العقارية": {
        "multiplier": 1.00,
        "route": "tax_statutory_route",
        "deep": True,
        "triggers_iaao": True,
        "note": (
            "Statutory tax layout + IAAO ratios. COD/PRD/Assessment "
            "Ratio are POPULATION statistics — computed at aggregate "
            "level (Wave 7), not per-component. Adapter flags only."
        ),
    },
    "التقارير المالية والمحاسبية - القيمة العادلة (13 Fair Value - IFRS)": {
        "multiplier": 1.00,
        "route": "ifrs13_hierarchy_route",
        "deep": True,
        "note": (
            "IFRS 13 fair-value hierarchy disclosure deferred — "
            "requires Level 1/2/3 input classification."
        ),
    },
    "حق الانتفاع - تقييم حقوق المنفعة العقارية (Usufruct Right)": {
        "multiplier": 1.00,
        "route": "usufruct_finite_cashflow_route",
        "deep": True,
        "note": (
            "Usufruct = present value of finite cashflows over tenure — "
            "deferred; requires tenure years + discount rate inputs."
        ),
    },
    "التقييم في حالة عدم اليقين (Valuation Under Uncertainty)": {
        "multiplier": 1.00,
        "route": "uncertainty_range_bound_route",
        "deep": True,
        "note": (
            "Range-bound upper/lower layout deferred — requires "
            "confidence interval / volatility input."
        ),
    },
    "تحليل أعلى وأفضل استغلال (Highest and Best Use Analysis)": {
        "multiplier": 1.00,
        "route": "habu_feasibility_route",
        "deep": True,
        "note": (
            "HABU 4-filter feasibility matrix deferred (legally "
            "permissible / physically possible / financially feasible / "
            "maximally productive)."
        ),
    },
    "التقييم لأغراض الصناديق الاستثمارية (Valuation for Investment Funds / REITs)": {
        "multiplier": 1.00,
        "route": "reit_cma_route",
        "deep": True,
        "note": (
            "REIT / CMA compliance layout deferred — requires FRA "
            "reporting structures."
        ),
    },
    "تقييم الأثر البيئي (Environmental Impact Assessment - EIA)": {
        "multiplier": 1.00,
        "route": "eia_green_liability_route",
        "deep": True,
        "note": (
            "Green liability / remediation deduction deferred — "
            "requires remediation_cost input. If component data carries "
            "'remediation_cost', a future wave deducts it."
        ),
    },
}


@dataclass(frozen=True)
class AdjustedValuation:
    """Result of applying a valuation purpose to a baseline ComponentValuation."""

    component_id: Any
    name: str
    asset_type: str
    purpose: str
    baseline_value: float
    multiplier_applied: float
    adjusted_value: float
    route: str
    deep_route_deferred: bool
    iaao_block_triggered: bool
    uspap_standards: tuple[str, ...]
    notes: tuple[str, ...] = field(default_factory=tuple)


class PurposeAdapterError(Exception):
    """Raised for unknown purpose."""


class PurposeComplianceAdapter:
    """Applies the 14 valuation-purpose rules to baseline component values."""

    def adapt(
        self,
        valuation: ComponentValuation,
        purpose: str,
        *,
        iaao_mass_appraisal_mode: bool = False,
    ) -> AdjustedValuation:
        """Apply `purpose` to a single ComponentValuation.

        Raises:
            PurposeAdapterError: purpose not in PURPOSE_RULES.
        """
        rule = PURPOSE_RULES.get(purpose)
        if rule is None:
            raise PurposeAdapterError(
                f"Unknown purpose {purpose!r}. "
                f"Valid: {sorted(PURPOSE_RULES.keys())}"
            )

        multiplier = float(rule["multiplier"])
        route = rule["route"]
        deep = bool(rule.get("deep", False))
        triggers_iaao = bool(rule.get("triggers_iaao", False))

        adjusted = round(valuation.baseline_value * multiplier, 2)

        notes: list[str] = list(valuation.notes)
        if rule.get("note"):
            notes.append(rule["note"])
        if deep:
            notes.append(
                f"NOTE: route '{route}' applies multiplier 1.0 only — "
                "deep computation deferred to a later wave."
            )

        uspap = ["Standard 1", "Standard 2"]
        if triggers_iaao:
            uspap += ["Standard 5", "Standard 6"]

        iaao_triggered = triggers_iaao and iaao_mass_appraisal_mode
        if triggers_iaao and not iaao_mass_appraisal_mode:
            notes.append(
                "NOTE: tax purpose normally triggers IAAO statistics, but "
                "iaao_mass_appraisal_mode is disabled — block skipped."
            )

        return AdjustedValuation(
            component_id=valuation.component_id,
            name=valuation.name,
            asset_type=valuation.asset_type,
            purpose=purpose,
            baseline_value=valuation.baseline_value,
            multiplier_applied=multiplier,
            adjusted_value=adjusted,
            route=route,
            deep_route_deferred=deep,
            iaao_block_triggered=iaao_triggered,
            uspap_standards=tuple(uspap),
            notes=tuple(notes),
        )

    def adapt_all(
        self,
        valuations: list[ComponentValuation],
        purposes: list[str],
        *,
        iaao_mass_appraisal_mode: bool = False,
    ) -> list[AdjustedValuation]:
        """Apply per-component purposes. `purposes` must align with `valuations`.

        Raises:
            ValueError: length mismatch.
        """
        if len(valuations) != len(purposes):
            raise ValueError(
                f"valuations ({len(valuations)}) and purposes "
                f"({len(purposes)}) length mismatch"
            )
        return [
            self.adapt(v, p, iaao_mass_appraisal_mode=iaao_mass_appraisal_mode)
            for v, p in zip(valuations, purposes)
        ]
