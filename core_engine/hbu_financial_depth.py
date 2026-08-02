"""
hbu_financial_depth.py
======================
HBU Financial-Depth Layer — طبقة العمق المالي لتقرير أعلى وأفضل استخدام.

تُضيف فوق مخرجات محرّك التحليل (hbu_analysis_engine.run_hbu_analysis) — READ-ONLY —
مقاييس مالية احترافية كانت ناقصة في التقرير الحالي:

  • القيمة المتبقية للأرض (Residual Land Value):
        RLV = NPV + land_cost   (اشتقاق دقيق: التكلفة الأرضية تدخل خطّيًا عند t0،
        فأعلى ثمن أرض يجعل NPV=0 هو NPV عند land_cost=0 = NPV الحالي + land_cost).
  • فترة الاسترداد (Payback) — إطلاع القيمة المحسوبة أصلًا في المحرّك.
  • هامش المطوّر والعائد على التكلفة (developer margin / return on cost).
  • عائد المستثمر (Equity IRR) — يُحسب فقط عند توفّر بنية تمويل صريحة؛ وإلا «غير متاح + سبب».
  • تحليل حساسية متعدّد المتغيّرات محسوب فعليًا (تكلفة × إيراد × خصم) — بدل «غير قابل للاحتساب».

مبادئ حاكمة:
  • READ-ONLY: نستورد بدائيات الحساب من المحرّك ونعيد استخدامها كما هي — لا تعديل ولا تكرار مختلف.
  • لا تلفيق: أي مقياس يحتاج مدخلًا غير متوفّر يُعلَّم «غير متاح + سبب».
  • حساب شفّاف قابل للتدقيق (يُعرَض ويُعاد حسابه بنفس دوال المحرّك).

وحدة إضافية بحتة — لا تمسّ hbu_analysis_engine.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# ── إعادة استخدام بدائيات المحرّك READ-ONLY (نفس رياضيات NPV/IRR/الاسترداد) ──────
try:  # pragma: no cover - import shim
    from hbu_analysis_engine import _build_cashflows, _irr, _npv, _payback_period  # type: ignore
except ImportError:  # pragma: no cover
    from core_engine.hbu_analysis_engine import (  # type: ignore
        _build_cashflows,
        _irr,
        _npv,
        _payback_period,
    )

_COST_STEPS = (-0.10, 0.0, 0.10)      # تغيّر تكلفة الإنشاء
_REVENUE_STEPS = (-0.10, 0.0, 0.10)   # تغيّر الإيراد السنوي
_DISCOUNT_STEPS = (-0.02, 0.0, 0.02)  # تغيّر معدل الخصم (نقاط مئوية)


def _scenario_inputs(ev: Dict[str, Any]) -> Dict[str, Any]:
    """يعيد بناء مدخلات السيناريو من نتيجة التقييم (لإعادة حساب التدفقات بنفس دوال المحرّك)."""
    return {
        "construction_cost": ev.get("construction_cost", 0),
        "construction_period_years": ev.get("construction_period", 0),
        "holding_period_years": ev.get("holding_period", 10),
        "annual_revenue": ev.get("annual_revenue", 0),
        "annual_opex": ev.get("annual_opex", 0),
        "exit_value": ev.get("exit_value", 0),
        "land_cost": ev.get("land_cost", 0),
    }


def residual_land_value(ev: Dict[str, Any]) -> float:
    """RLV = NPV + land_cost (أعلى ثمن أرض يُبقي المشروع عند NPV=0)."""
    return float(ev.get("npv", 0.0)) + float(ev.get("land_cost", 0.0))


def developer_metrics(ev: Dict[str, Any]) -> Dict[str, Any]:
    """هامش المطوّر والعائد على التكلفة من التدفقات غير المخصومة."""
    cashflows = ev.get("cashflows")
    if cashflows is None:
        return {
            "net_undiscounted_profit": None,
            "total_investment": None,
            "profit_on_cost_pct": None,
            "status": "unavailable",
            "reason": "cashflows_missing",
        }
    net_undiscounted_profit = float(sum(cashflows))
    total_investment = float(ev.get("construction_cost", 0)) + float(ev.get("land_cost", 0))
    profit_on_cost = (net_undiscounted_profit / total_investment) if total_investment > 0 else None
    return {
        "net_undiscounted_profit": round(net_undiscounted_profit, 0),
        "total_investment": round(total_investment, 0),
        "profit_on_cost_pct": round(profit_on_cost * 100, 1) if profit_on_cost is not None else None,
    }


def equity_irr(ev: Dict[str, Any], financing: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    عائد المستثمر (Equity IRR) — قرض بفائدة فقط يُسدّد أصله في سنة الخروج.
    لا يُحسب إلا بمدخلات تمويل صريحة (ltv, loan_rate)؛ وإلا غير متاح (بلا تلفيق).
    """
    if not financing or "ltv" not in financing or "loan_rate" not in financing:
        return {"value": None, "status": "unavailable",
                "reason": "عائد المستثمر يتطلّب بنية تمويل صريحة (ltv, loan_rate) — لا تُلفَّق."}
    ltv = float(financing["ltv"])
    loan_rate = float(financing["loan_rate"])
    if not (0.0 <= ltv < 1.0):
        return {"value": None, "status": "unavailable", "reason": "ltv خارج النطاق [0,1)."}

    base_cf = list(ev.get("cashflows") or [])
    if not base_cf:
        return {"value": None, "status": "unavailable", "reason": "لا تدفقات نقدية."}

    total_investment = float(ev.get("construction_cost", 0)) + float(ev.get("land_cost", 0))
    loan = ltv * total_investment
    equity_cf = list(base_cf)
    equity_cf[0] += loan                                  # القرض يقلّل رأس المال المطلوب t0
    interest = loan * loan_rate
    for t in range(1, len(equity_cf)):
        equity_cf[t] -= interest                          # خدمة الدين (فائدة فقط)
    equity_cf[-1] -= loan                                 # سداد أصل القرض عند الخروج
    irr = _irr(equity_cf)
    return {
        "value": round(irr * 100, 1) if irr is not None else None,
        "status": "computed" if irr is not None else "not_computable",
        "assumption": f"ltv={ltv:.0%}, loan_rate={loan_rate:.2%}, فائدة فقط + سداد الأصل عند الخروج",
    }


def sensitivity_grid(ev: Dict[str, Any], discount_rate: float) -> Dict[str, Any]:
    """
    حساسية محسوبة فعليًا بإعادة بناء التدفقات عبر دوال المحرّك:
      • شبكة تكلفة × إيراد (NPV عند معدل الخصم الأساس)
      • حساسية معدل الخصم على التدفقات الأساس
    """
    base = _scenario_inputs(ev)
    base_cf = _build_cashflows(base)
    base_npv = _npv(discount_rate, base_cf)

    cost_rev_grid: List[Dict[str, Any]] = []
    for dc in _COST_STEPS:
        for dr in _REVENUE_STEPS:
            scn = dict(base)
            scn["construction_cost"] = float(base["construction_cost"]) * (1 + dc)
            scn["annual_revenue"] = float(base["annual_revenue"]) * (1 + dr)
            cf = _build_cashflows(scn)
            npv = _npv(discount_rate, cf)
            cost_rev_grid.append({
                "cost_delta_pct": round(dc * 100),
                "revenue_delta_pct": round(dr * 100),
                "npv": round(npv, 0),
                "feasible": npv > 0,
            })

    discount_row: List[Dict[str, Any]] = []
    for dd in _DISCOUNT_STEPS:
        d = discount_rate + dd
        npv = _npv(d, base_cf)
        discount_row.append({
            "discount_rate_pct": round(d * 100, 1),
            "npv": round(npv, 0),
            "feasible": npv > 0,
        })

    npvs = [c["npv"] for c in cost_rev_grid]
    return {
        "base_npv": round(base_npv, 0),
        "cost_revenue_grid": cost_rev_grid,
        "discount_sensitivity": discount_row,
        "npv_min": min(npvs) if npvs else None,
        "npv_max": max(npvs) if npvs else None,
        "downside_feasible": all(c["feasible"] for c in cost_rev_grid),
    }


def enhance_hbu_financials(
    result: Dict[str, Any],
    *,
    financing: Optional[Dict[str, Any]] = None,
    land_area_m2: Optional[float] = None,
) -> Dict[str, Any]:
    """
    يُثري نتيجة run_hbu_analysis بمقاييس العمق المالي (نسخة جديدة — لا يعدّل المُدخل).

    يضيف لكل سيناريو: residual_land_value · rlv_per_m2 · payback_years (مُطلَعة) ·
    developer_metrics · equity_irr. ويضيف كتلة financial_depth عليا بحساسية السيناريو الموصى به.
    """
    out = dict(result)  # نسخة سطحية — لا نطمس الأصل
    # Validate discount_rate — no fabrication: no_fabrication=True forbids inventing a rate.
    _dr_raw = result.get("discount_rate")
    discount_rate: Optional[float] = None
    if _dr_raw is not None:
        try:
            _dr_cand = float(_dr_raw)
            if _dr_cand > 0:
                discount_rate = _dr_cand
        except (TypeError, ValueError):
            pass
    area = land_area_m2 if land_area_m2 is not None else float(result.get("property", {}).get("area", 0) or 0)

    enhanced_scen: List[Dict[str, Any]] = []
    for ev in result.get("scenarios_evaluated", []):
        e = dict(ev)
        rlv = residual_land_value(ev)
        e["residual_land_value"] = round(rlv, 0)
        e["rlv_per_m2"] = round(rlv / area, 0) if area > 0 else None
        e["payback_years"] = ev.get("payback_years")  # إطلاع القيمة المحسوبة أصلًا
        e["developer_metrics"] = developer_metrics(ev)
        e["equity_irr"] = equity_irr(ev, financing)
        enhanced_scen.append(e)
    out["scenarios_evaluated"] = enhanced_scen

    # كتلة العمق المالي — حساسية السيناريو الموصى به (أو الأعلى NPV)
    rec_name = result.get("recommended_use")
    target = None
    for e in enhanced_scen:
        if rec_name and e["use_name"] == rec_name:
            target = e
            break
    if target is None and enhanced_scen:
        target = max(enhanced_scen, key=lambda x: x.get("npv", float("-inf")))

    financial_depth: Dict[str, Any] = {
        "discount_rate_pct": round(discount_rate * 100, 1) if discount_rate is not None else None,
    }
    if target is not None:
        financial_depth.update({
            "target_use": target["use_name"],
            "residual_land_value": target["residual_land_value"],
            "rlv_per_m2": target["rlv_per_m2"],
            "payback_years": target.get("payback_years"),
            "developer_metrics": target["developer_metrics"],
            "equity_irr": target["equity_irr"],
            "sensitivity": sensitivity_grid(target, discount_rate)
                           if discount_rate is not None
                           else {"status": "unavailable", "reason": "discount_rate_missing"},
        })
    out["financial_depth"] = financial_depth
    out["financial_depth_governance"] = {
        "advisory_only": True,
        "engine_readonly": True,
        "reuses_engine_math": True,   # نفس دوال _npv/_irr/_build_cashflows
        "no_fabrication": True,
    }
    return out
