"""
pv_sim_market_methods.py
Applies the four valuation methods to the subject property
using sourced inputs from pv_sim_sourced_inputs.SourcingResult.

Methods applied on subject property:
  1. Sales Comparison  — price/m² + 3-factor adjustments
  2. Income Capitalisation — EGI/NOI + documented cap rate
  3. Cost Approach — land + improvements (documented cost + depreciation)
  4. DCF — 10-year horizon + terminal value
  5. Weighted Reconciliation

Governance:
  advisory_only=True · certification_ready=False · fake_signature_created=False
  All sourced inputs cite their provenance records
  NO engine modification (READ-ONLY)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .pv_sim_sourced_inputs import InputProvenance, SourcingResult


# ── RAG thresholds (% diff from simulation value) ─────────────────────────────
_GREEN_MAX  = 10.0
_YELLOW_MAX = 25.0


def _rag(diff_pct: Optional[float]) -> str:
    if diff_pct is None:
        return "⚪"
    d = abs(diff_pct)
    if d < _GREEN_MAX:
        return "🟢"
    if d < _YELLOW_MAX:
        return "🟡"
    return "🔴"


# ── Method result dataclass ───────────────────────────────────────────────────

@dataclass
class MethodResult:
    method_id: str
    method_name_ar: str
    computed_value: Optional[float]
    simulation_value: Optional[float]      # BASE scenario value for comparison
    diff_amount: Optional[float]
    diff_pct: Optional[float]
    rag_status: str
    input_source_summary: str
    calculation_steps: List[Dict[str, Any]] = field(default_factory=list)
    input_prov_ids: List[str] = field(default_factory=list)
    advisory_only: bool = True
    certification_ready: bool = False
    fake_signature_created: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method_id":            self.method_id,
            "method_name_ar":       self.method_name_ar,
            "computed_value":       self.computed_value,
            "simulation_value":     self.simulation_value,
            "diff_amount":          self.diff_amount,
            "diff_pct":             self.diff_pct,
            "rag_status":           self.rag_status,
            "input_source_summary": self.input_source_summary,
            "calculation_steps":    self.calculation_steps,
            "input_prov_ids":       self.input_prov_ids,
            "advisory_only":        self.advisory_only,
            "certification_ready":  self.certification_ready,
            "fake_signature_created": self.fake_signature_created,
        }


@dataclass
class MethodsResult:
    subject_case_id: str
    currency: str
    methods: List[MethodResult]
    comparison_table: List[Dict[str, Any]]
    reconciliation: Dict[str, Any]
    advisory_only: bool = True
    certification_ready: bool = False
    fake_signature_created: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject_case_id":        self.subject_case_id,
            "currency":               self.currency,
            "methods":                [m.to_dict() for m in self.methods],
            "comparison_table":       self.comparison_table,
            "reconciliation":         self.reconciliation,
            "advisory_only":          self.advisory_only,
            "certification_ready":    self.certification_ready,
            "fake_signature_created": self.fake_signature_created,
        }


# ── Diff helpers ──────────────────────────────────────────────────────────────

def _diff(computed: Optional[float], sim: Optional[float]) -> tuple:
    if computed is None or not sim:
        return None, None
    da = computed - sim
    dp = da / sim * 100
    return round(da), round(dp, 2)


# ── Method 1: Sales Comparison ────────────────────────────────────────────────

def _apply_sales_comparison(
    si: Dict[str, Any],
    sim_value: Optional[float],
    currency: str,
    comparables: List[Dict[str, Any]],
) -> MethodResult:
    price_m2 = si.get("price_per_m2")
    area     = si.get("built_up_area_m2", 850.0)

    if price_m2 is None:
        return MethodResult(
            method_id="sales_comparison",
            method_name_ar="مقارنة البيوع",
            computed_value=None, simulation_value=sim_value,
            diff_amount=None, diff_pct=None,
            rag_status="⚪",
            input_source_summary="غير متاح — سعر المتر المربع مفقود",
            input_prov_ids=["price_per_m2"],
        )

    # 3-factor adjustment (neutral baseline — no comp-specific data)
    adj_size     = 1.00
    adj_age      = 1.00
    adj_location = 1.00
    adj_price_m2 = price_m2 * adj_size * adj_age * adj_location
    computed     = round(adj_price_m2 * area)

    steps: List[Dict[str, Any]] = [
        {"label": "سعر المتر المربع المصدري",      "value": f"{price_m2:,.0f} {currency}/م²"},
        {"label": "تسوية الحجم (adj_size)",         "value": f"× {adj_size:.2f}"},
        {"label": "تسوية العمر (adj_age)",           "value": f"× {adj_age:.2f}"},
        {"label": "تسوية الموقع (adj_location)",    "value": f"× {adj_location:.2f}"},
        {"label": "السعر المعدَّل / م²",             "value": f"{adj_price_m2:,.0f} {currency}/م²"},
        {"label": "المساحة المبنية",                 "value": f"{area:,.0f} م²"},
        {"label": "القيمة المحسوبة",                 "value": f"{computed:,.0f} {currency}"},
    ]

    # Enrichment comparables matrix (informational)
    comp_matrix = []
    for c in comparables[:5]:
        lo  = c.get("price_m2_lo", 0)
        hi  = c.get("price_m2_hi", 0)
        mid = (lo + hi) / 2 if lo and hi else 0
        comp_matrix.append({
            "description": c.get("description", "—"),
            "location":    c.get("location", "—"),
            "price_m2_lo": lo,
            "price_m2_hi": hi,
            "adj_value":   round(mid * area) if mid else None,
        })
    if comp_matrix:
        steps.append({"label": "مصفوفة المقارنات (Enrichment)", "value": comp_matrix})

    da, dp = _diff(computed, sim_value)
    return MethodResult(
        method_id="sales_comparison",
        method_name_ar="مقارنة البيوع",
        computed_value=computed, simulation_value=sim_value,
        diff_amount=da, diff_pct=dp,
        rag_status=_rag(dp),
        input_source_summary="سعر المتر المربع المصدري (نموذج مجمع أو Draft محوكم)",
        calculation_steps=steps,
        input_prov_ids=["price_per_m2"],
    )


# ── Method 2: Income Capitalisation ──────────────────────────────────────────

def _apply_income_approach(
    si: Dict[str, Any],
    sim_value: Optional[float],
    currency: str,
) -> MethodResult:
    cap_rate = si.get("cap_rate")
    rent_m2  = si.get("market_rent_per_m2_monthly")
    area     = si.get("built_up_area_m2", 850.0)
    vac_pct  = si.get("vacancy_rate")
    op_pct   = si.get("op_expenses", 10.0)
    maint_pct = si.get("maint_reserve", 5.0)
    coll_pct  = si.get("collection_loss", 2.0)

    # Fallback: derive rent/m² from body monthly_rent
    if rent_m2 is None:
        monthly_rent = si.get("monthly_rent", 12000.0)
        rent_m2 = monthly_rent / area if area else 0.0

    if not cap_rate or not rent_m2 or float(cap_rate) <= 0:
        return MethodResult(
            method_id="income_capitalisation",
            method_name_ar="رسملة الدخل",
            computed_value=None, simulation_value=sim_value,
            diff_amount=None, diff_pct=None,
            rag_status="⚪",
            input_source_summary="غير متاح — معدل الرسملة أو الإيجار مفقود",
            input_prov_ids=["cap_rate", "market_rent_per_m2_monthly"],
        )

    cap_f   = float(cap_rate) / 100 if float(cap_rate) > 1 else float(cap_rate)
    vac_f   = (float(vac_pct) / 100 if vac_pct and float(vac_pct) > 1
               else float(vac_pct or 0.05))
    coll_f  = float(coll_pct) / 100
    op_f    = float(op_pct) / 100
    maint_f = float(maint_pct) / 100

    gpi  = float(rent_m2) * area * 12
    egi  = gpi * (1 - vac_f) * (1 - coll_f)
    noi  = egi * (1 - op_f - maint_f)
    computed = round(noi / cap_f) if cap_f > 0 else None

    steps = [
        {"label": "الإيجار الشهري / م² (مصدري)",   "value": f"{float(rent_m2):,.2f} {currency}/م²/شهر"},
        {"label": "الدخل الإجمالي المحتمل (GPI)",   "value": f"{gpi:,.0f} {currency}"},
        {"label": "معدل الشواغر",                    "value": f"{vac_f*100:.1f}%"},
        {"label": "خسارة التحصيل",                   "value": f"{coll_f*100:.1f}%"},
        {"label": "الدخل الإجمالي الفعلي (EGI)",     "value": f"{egi:,.0f} {currency}"},
        {"label": "مصاريف التشغيل",                  "value": f"{op_f*100:.1f}%"},
        {"label": "احتياطي الصيانة",                 "value": f"{maint_f*100:.1f}%"},
        {"label": "صافي الدخل التشغيلي (NOI)",       "value": f"{noi:,.0f} {currency}"},
        {"label": "معدل الرسملة المصدري",             "value": f"{cap_f*100:.2f}%"},
        {"label": "القيمة المحسوبة (NOI ÷ cap)",     "value": f"{computed:,.0f} {currency}" if computed else "—"},
    ]

    da, dp = _diff(computed, sim_value)
    return MethodResult(
        method_id="income_capitalisation",
        method_name_ar="رسملة الدخل",
        computed_value=computed, simulation_value=sim_value,
        diff_amount=da, diff_pct=dp,
        rag_status=_rag(dp),
        input_source_summary="معدل الرسملة + الإيجار المصدريَّان (Draft محوكم)",
        calculation_steps=steps,
        input_prov_ids=["cap_rate", "market_rent_per_m2_monthly", "vacancy_rate"],
    )


# ── Method 3: Cost Approach ───────────────────────────────────────────────────

def _apply_cost_approach(
    si: Dict[str, Any],
    sim_value: Optional[float],
    currency: str,
) -> MethodResult:
    land_price = si.get("land_price_per_m2")
    const_cost = si.get("construction_cost_per_m2")
    land_area  = si.get("land_area_m2", 1200.0)
    built_area = si.get("built_up_area_m2", 850.0)
    phys_depr  = si.get("phys_depr", 15.0)
    func_depr  = si.get("func_depr", 5.0)
    ext_depr   = si.get("ext_depr", 3.0)

    if land_price is None or const_cost is None:
        return MethodResult(
            method_id="cost_approach",
            method_name_ar="أسلوب التكلفة",
            computed_value=None, simulation_value=sim_value,
            diff_amount=None, diff_pct=None,
            rag_status="⚪",
            input_source_summary="غير متاح — تكلفة البناء أو سعر الأرض مفقودان",
            input_prov_ids=["construction_cost_per_m2", "land_price_per_m2"],
        )

    phys_f       = float(phys_depr) / 100
    func_f       = float(func_depr) / 100
    ext_f        = float(ext_depr)  / 100
    total_depr_f = 1 - (1 - phys_f) * (1 - func_f) * (1 - ext_f)

    land_val    = float(land_price) * land_area
    improve_val = float(const_cost) * built_area * (1 - total_depr_f)
    computed    = round(land_val + improve_val)

    steps = [
        {"label": "سعر الأرض / م² (مصدري)",          "value": f"{float(land_price):,.0f} {currency}/م²"},
        {"label": "مساحة الأرض",                      "value": f"{land_area:,.0f} م²"},
        {"label": "قيمة الأرض",                       "value": f"{land_val:,.0f} {currency}"},
        {"label": "تكلفة البناء / م² (مصدرية)",      "value": f"{float(const_cost):,.0f} {currency}/م²"},
        {"label": "المساحة المبنية",                   "value": f"{built_area:,.0f} م²"},
        {"label": "الإهلاك المادي",                    "value": f"{phys_f*100:.1f}%"},
        {"label": "الإهلاك الوظيفي",                  "value": f"{func_f*100:.1f}%"},
        {"label": "الإهلاك الخارجي",                  "value": f"{ext_f*100:.1f}%"},
        {"label": "إجمالي الإهلاك",                   "value": f"{total_depr_f*100:.1f}%"},
        {"label": "قيمة التحسينات (صافي)",            "value": f"{improve_val:,.0f} {currency}"},
        {"label": "القيمة الإجمالية (أرض + تحسينات)", "value": f"{computed:,.0f} {currency}"},
    ]

    da, dp = _diff(computed, sim_value)
    return MethodResult(
        method_id="cost_approach",
        method_name_ar="أسلوب التكلفة",
        computed_value=computed, simulation_value=sim_value,
        diff_amount=da, diff_pct=dp,
        rag_status=_rag(dp),
        input_source_summary="سعر الأرض + تكلفة البناء المصدريَّان (نموذج مجمع مشتق)",
        calculation_steps=steps,
        input_prov_ids=["construction_cost_per_m2", "land_price_per_m2"],
    )


# ── Method 4: DCF ─────────────────────────────────────────────────────────────

def _apply_dcf(
    si: Dict[str, Any],
    sim_value: Optional[float],
    currency: str,
    hold_years: int = 10,
) -> MethodResult:
    cap_rate   = si.get("cap_rate")
    rent_m2    = si.get("market_rent_per_m2_monthly")
    disc_rate  = si.get("discount_rate", 0.10)
    growth_r   = si.get("annual_growth_rate", 0.03)
    area       = si.get("built_up_area_m2", 850.0)
    vac_pct    = si.get("vacancy_rate")
    op_pct     = si.get("op_expenses", 10.0)
    maint_pct  = si.get("maint_reserve", 5.0)
    coll_pct   = si.get("collection_loss", 2.0)

    if rent_m2 is None:
        monthly = si.get("monthly_rent", 12000.0)
        rent_m2 = monthly / area if area else 0.0
    if cap_rate is None:
        cap_rate = 6.5
    if not disc_rate or float(disc_rate) <= 0:
        disc_rate = 0.10
    if not growth_r:
        growth_r = 0.03

    cap_f  = float(cap_rate) / 100  if float(cap_rate) > 1  else float(cap_rate)
    disc_f = float(disc_rate) / 100 if float(disc_rate) > 1 else float(disc_rate)
    grow_f = float(growth_r) / 100  if float(growth_r) > 1  else float(growth_r)
    vac_f  = (float(vac_pct) / 100 if vac_pct and float(vac_pct) > 1
              else float(vac_pct or 0.05))
    coll_f  = float(coll_pct) / 100
    op_f    = float(op_pct) / 100
    maint_f = float(maint_pct) / 100

    gpi_y1 = float(rent_m2) * area * 12
    egi_y1 = gpi_y1 * (1 - vac_f) * (1 - coll_f)
    noi_y1 = egi_y1 * (1 - op_f - maint_f)

    pv_ops = 0.0
    cf_rows = []
    for t in range(1, hold_years + 1):
        noi_t = noi_y1 * (1 + grow_f) ** (t - 1)
        pv_t  = noi_t / (1 + disc_f) ** t
        pv_ops += pv_t
        if t <= 3 or t == hold_years:
            cf_rows.append({"السنة": t, "NOI": round(noi_t), "PV": round(pv_t)})

    noi_terminal = noi_y1 * (1 + grow_f) ** hold_years
    terminal_spread = cap_f - grow_f
    tv = noi_terminal / terminal_spread if terminal_spread > 0 else 0.0
    pv_tv = tv / (1 + disc_f) ** hold_years
    computed = round(pv_ops + pv_tv)

    steps: List[Dict[str, Any]] = [
        {"label": "NOI السنة الأولى",                  "value": f"{noi_y1:,.0f} {currency}"},
        {"label": "معدل النمو السنوي (مصدري)",         "value": f"{grow_f*100:.2f}%"},
        {"label": "معدل الخصم (مصدري)",                "value": f"{disc_f*100:.2f}%"},
        {"label": "معدل الرسملة النهائية",              "value": f"{cap_f*100:.2f}%"},
        {"label": "مدة الاحتفاظ",                      "value": f"{hold_years} سنة"},
        {"label": "تدفقات نقدية (y1–y3)",              "value": cf_rows[:3]},
        {"label": "القيمة النهائية (Terminal Value)",  "value": f"{tv:,.0f} {currency}"},
        {"label": "PV للقيمة النهائية",                "value": f"{pv_tv:,.0f} {currency}"},
        {"label": "PV للتدفقات التشغيلية",             "value": f"{pv_ops:,.0f} {currency}"},
        {"label": "القيمة الإجمالية (DCF)",            "value": f"{computed:,.0f} {currency}"},
    ]

    da, dp = _diff(computed, sim_value)
    return MethodResult(
        method_id="dcf",
        method_name_ar="التدفق النقدي المخصوم (DCF)",
        computed_value=computed, simulation_value=sim_value,
        diff_amount=da, diff_pct=dp,
        rag_status=_rag(dp),
        input_source_summary="معدل الخصم + النمو + NOI المصدرية (Draft محوكم)",
        calculation_steps=steps,
        input_prov_ids=["discount_rate", "annual_growth_rate", "cap_rate", "market_rent_per_m2_monthly"],
    )


# ── Reconciliation ─────────────────────────────────────────────────────────────

def _reconcile(
    methods: List[MethodResult],
    weights: Dict[str, float],
    sim_base_final: Optional[float],
    currency: str,
) -> Dict[str, Any]:
    w_s = weights.get("sales", 50) / 100
    w_i = weights.get("income", 35) / 100
    w_c = weights.get("cost", 15) / 100

    weight_map = {
        "sales_comparison":    w_s,
        "income_capitalisation": w_i,
        "cost_approach":       w_c,
        "dcf":                 0.0,
    }
    available = {m.method_id: m.computed_value for m in methods if m.computed_value is not None}
    if not available:
        return {
            "reconciled_value":   None,
            "advisory_range_lo":  None,
            "advisory_range_hi":  None,
            "diff_from_simulation": None,
            "diff_pct":           None,
            "rag_status":         "⚪",
            "note":               "لا قيم مُحسَبة متاحة",
        }

    total_w = sum(weight_map.get(mid, 0.0) for mid in available)
    if total_w > 0:
        w_sum = sum(v * weight_map.get(mid, 0.0) for mid, v in available.items())
        reconciled = round(w_sum / total_w / 1000) * 1000
    else:
        reconciled = round(sum(available.values()) / len(available) / 1000) * 1000

    lo = round(min(available.values()) * 0.95 / 1000) * 1000
    hi = round(max(available.values()) * 1.05 / 1000) * 1000

    diff   = (reconciled - sim_base_final) if sim_base_final else None
    diff_p = (diff / sim_base_final * 100)  if sim_base_final else None

    return {
        "reconciled_value":    reconciled,
        "advisory_range_lo":   lo,
        "advisory_range_hi":   hi,
        "diff_from_simulation": round(diff) if diff is not None else None,
        "diff_pct":            round(diff_p, 2) if diff_p is not None else None,
        "rag_status":          _rag(diff_p),
        "currency":            currency,
        "note": (
            f"قيمة استرشادية مجمَّعة: {reconciled:,.0f} {currency} | "
            f"نطاق استشاري: {lo:,.0f} – {hi:,.0f} {currency}"
        ),
    }


# ── Comparison table ──────────────────────────────────────────────────────────

def _build_comparison_table(methods: List[MethodResult]) -> List[Dict[str, Any]]:
    return [
        {
            "method_id":            m.method_id,
            "method_name_ar":       m.method_name_ar,
            "simulation_value":     m.simulation_value,
            "computed_value":       m.computed_value,
            "diff_amount":          m.diff_amount,
            "diff_pct":             m.diff_pct,
            "rag_status":           m.rag_status,
            "input_source_summary": m.input_source_summary,
            "input_prov_ids":       m.input_prov_ids,
        }
        for m in methods
    ]


# ── Main entry point ──────────────────────────────────────────────────────────

def apply_methods_to_subject(
    sourcing_result: SourcingResult,
    body: Dict[str, Any],
    scenarios: List[Dict[str, Any]],
    shadow_results: List[Dict[str, Any]],
    currency: str = "QAR",
) -> MethodsResult:
    """
    Apply all four valuation methods to the subject property using sourced inputs.

    Parameters
    ----------
    sourcing_result : output of source_subject_inputs()
    body            : original request body
    scenarios       : output of _run_three_scenarios() — provides BASE sub-values
    shadow_results  : output of shadow calculations — provides DCF shadow value
    currency        : currency code

    GOVERNANCE:
      advisory_only=True · certification_ready=False · fake_signature_created=False
    """
    si      = sourcing_result.subject_inputs
    case_id = body.get("case_id", "—")

    # Extract BASE scenario sub-values for comparison
    base = next((s for s in scenarios if s.get("scenario_id") == "BASE"), {})
    sim_sales  = base.get("sales_comparison_value") or None
    sim_income = base.get("income_value") or None
    sim_cost   = base.get("cost_value")  or None

    # DCF is absent in BASE — use shadow DCF value
    sim_dcf = None
    for sr in shadow_results:
        if sr.get("method") == "dcf":
            sim_dcf = sr.get("shadow_value")
            break

    methods = [
        _apply_sales_comparison(si, sim_sales,  currency, sourcing_result.enrichment_comparables),
        _apply_income_approach(si, sim_income, currency),
        _apply_cost_approach(si, sim_cost, currency),
        _apply_dcf(si, sim_dcf, currency),
    ]

    weights = {
        "sales":  float(body.get("weight_sales",  50)),
        "income": float(body.get("weight_income", 35)),
        "cost":   float(body.get("weight_cost",   15)),
    }
    sim_base_final = base.get("final_value") or None

    reconciliation   = _reconcile(methods, weights, sim_base_final, currency)
    comparison_table = _build_comparison_table(methods)

    return MethodsResult(
        subject_case_id=case_id,
        currency=currency,
        methods=methods,
        comparison_table=comparison_table,
        reconciliation=reconciliation,
        advisory_only=True,
        certification_ready=False,
        fake_signature_created=False,
    )
