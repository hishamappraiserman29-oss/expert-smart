"""
hbu_analysis_engine.py
=======================
Highest and Best Use (HBU) Analysis Engine
محرك تحليل أعلى وأفضل استغلال للأصل العقاري

Implements the four-test framework used by IVS, USPAP, and the Appraisal
Institute for determining the Highest and Best Use of a property:

    1. Legally Permissible      — ممكن قانونياً (zoning, easements, deed restrictions)
    2. Physically Possible      — ممكن مادياً  (size, shape, soil, access, utilities)
    3. Financially Feasible     — مجدٍ مالياً  (NPV > 0 at market discount rate)
    4. Maximally Productive     — أعلى إنتاجية (highest NPV among feasible alternatives)

Design notes:
    * This module is ADDITIVE only. No existing valuation/audit/tax logic
      is modified or shadowed.
    * Pure-Python NPV / IRR implementations — no numpy/scipy dependency.
    * Composes cleanly with `valuation_logic` & `bridge_api` via /api/hbu/analyze.

Public API:
    run_hbu_analysis(payload)              -> dict
    generate_hbu_excel(result, out_dir)    -> str   (path to .xlsx)
"""

from __future__ import annotations
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_OUT_DIR = os.path.join(_BASE_DIR, "outputs", "reports")


# ════════════════════════════════════════════════════════════════════════════
#  PURE-PYTHON FINANCE PRIMITIVES
# ════════════════════════════════════════════════════════════════════════════

def _npv(rate: float, cashflows: List[float]) -> float:
    """
    Net Present Value at `rate`. cashflows[0] is t=0 (typically negative).
    """
    if rate <= -1:
        return float("nan")
    total = 0.0
    for t, cf in enumerate(cashflows):
        total += cf / ((1.0 + rate) ** t)
    return total


def _irr(cashflows: List[float], guess: float = 0.1, tol: float = 1e-7,
         max_iter: int = 200) -> Optional[float]:
    """
    Internal Rate of Return via Newton-Raphson with bisection fallback.
    Returns None if no real positive IRR is found.
    """
    if not cashflows or all(cf >= 0 for cf in cashflows) or all(cf <= 0 for cf in cashflows):
        return None

    # --- Newton-Raphson ---
    rate = guess
    for _ in range(max_iter):
        f = _npv(rate, cashflows)
        # numerical derivative
        dr = 1e-6
        df = (_npv(rate + dr, cashflows) - f) / dr
        if df == 0:
            break
        new_rate = rate - f / df
        if abs(new_rate - rate) < tol:
            return new_rate
        rate = new_rate
        if rate <= -0.999:
            break

    # --- Bisection fallback in [-0.99, 10] ---
    lo, hi = -0.99, 10.0
    f_lo, f_hi = _npv(lo, cashflows), _npv(hi, cashflows)
    if f_lo * f_hi > 0:
        return None
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        f_mid = _npv(mid, cashflows)
        if abs(f_mid) < tol:
            return mid
        if f_lo * f_mid < 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2


def _payback_period(cashflows: List[float]) -> Optional[float]:
    """
    Discounted-cash payback period (years). Linear interpolation on the
    crossing year. Returns None if cumulative cashflow never turns positive.
    """
    cum = 0.0
    for t, cf in enumerate(cashflows):
        prev_cum = cum
        cum += cf
        if cum >= 0 and prev_cum < 0:
            # interpolate within the year
            return (t - 1) + (-prev_cum / cf) if cf != 0 else float(t)
    return None


# ════════════════════════════════════════════════════════════════════════════
#  CASH-FLOW BUILDER FOR A SINGLE ALTERNATIVE USE
# ════════════════════════════════════════════════════════════════════════════

def _build_cashflows(scenario: Dict[str, Any]) -> List[float]:
    """
    Builds annual cashflow vector for a single alternative-use scenario.

    Convention (year 0 = today):
      year 0..(C-1)    -> construction_cost spread evenly (negative)
      year C..(C+H-1)  -> annual NOI = revenue - opex (after stabilisation)
      year (C+H)       -> terminal exit value added to that year's NOI

    Where:
      C = construction_period_years (default 0 → operating land/existing bldg)
      H = holding_period_years      (default 10)
    """
    construction_cost   = float(scenario.get("construction_cost", 0))
    construction_period = max(0, int(scenario.get("construction_period_years", 0)))
    holding_period      = max(1, int(scenario.get("holding_period_years", 10)))
    annual_revenue      = float(scenario.get("annual_revenue", 0))
    annual_opex         = float(scenario.get("annual_opex", 0))
    exit_value          = float(scenario.get("exit_value", 0))
    land_cost           = float(scenario.get("land_cost", 0))   # optional

    annual_noi = annual_revenue - annual_opex

    # Total horizon = construction + holding + 1 (terminal at end of last hold yr)
    total_years = construction_period + holding_period
    cf: List[float] = [0.0] * (total_years + 1)

    # Year 0: land acquisition + first construction tranche
    if construction_period > 0:
        per_year_constr = construction_cost / construction_period
        cf[0] = -land_cost - per_year_constr
        for t in range(1, construction_period):
            cf[t] = -per_year_constr
    else:
        # Existing building / land already developed → only land cost upfront
        cf[0] = -land_cost - construction_cost

    # Operating years
    op_start = construction_period if construction_period > 0 else 1
    op_end   = construction_period + holding_period
    for t in range(op_start, op_end):
        cf[t] += annual_noi

    # Terminal year: NOI for last operating year + exit value
    cf[op_end] += annual_noi + exit_value

    return cf


# ════════════════════════════════════════════════════════════════════════════
#  CORE HBU ANALYSIS
# ════════════════════════════════════════════════════════════════════════════

_REQUIRED_USE_FIELDS = ("use_name",)


def _evaluate_scenario(scenario: Dict[str, Any], discount_rate: float) -> Dict[str, Any]:
    """
    Runs the four HBU tests on one scenario and returns a per-scenario dict.
    """
    for f in _REQUIRED_USE_FIELDS:
        if f not in scenario:
            raise ValueError(f"alternative_uses[*].{f} مطلوب.")

    use_name: str = str(scenario["use_name"]).strip()
    legally  = bool(scenario.get("is_legally_permissible", True))
    physical = bool(scenario.get("is_physically_possible", True))
    legal_note    = str(scenario.get("legal_note", ""))
    physical_note = str(scenario.get("physical_note", ""))

    # If either of the first two tests fail, financial test is reported but
    # the scenario is automatically disqualified — per IVS doctrine.
    cashflows = _build_cashflows(scenario)
    npv = _npv(discount_rate, cashflows)
    irr = _irr(cashflows)
    payback = _payback_period(cashflows)
    financially_feasible = (npv > 0)

    # Test 4 (maximally productive) is decided across scenarios — handled by caller.
    passes_first_three = legally and physical and financially_feasible

    if not legally:
        verdict = "مرفوض — غير ممكن قانونياً (Test 1 fail)"
    elif not physical:
        verdict = "مرفوض — غير ممكن مادياً (Test 2 fail)"
    elif not financially_feasible:
        verdict = "مرفوض — غير مجدٍ مالياً (Test 3 fail: NPV ≤ 0)"
    else:
        verdict = "مرشَّح — اجتاز الاختبارات الثلاثة الأولى"

    return {
        "use_name":              use_name,
        "test_1_legal":          legally,
        "test_1_note":           legal_note,
        "test_2_physical":       physical,
        "test_2_note":           physical_note,
        "test_3_financial":      financially_feasible,
        "construction_cost":     float(scenario.get("construction_cost", 0)),
        "construction_period":   int(scenario.get("construction_period_years", 0)),
        "holding_period":        int(scenario.get("holding_period_years", 10)),
        "annual_revenue":        float(scenario.get("annual_revenue", 0)),
        "annual_opex":           float(scenario.get("annual_opex", 0)),
        "annual_noi":            float(scenario.get("annual_revenue", 0)) - float(scenario.get("annual_opex", 0)),
        "exit_value":            float(scenario.get("exit_value", 0)),
        "land_cost":             float(scenario.get("land_cost", 0)),
        "cashflows":             cashflows,
        "npv":                   npv,
        "irr":                   irr,
        "irr_pct":               (irr * 100) if irr is not None else None,
        "payback_years":         payback,
        "passes_first_three":    passes_first_three,
        "verdict_so_far":        verdict,
    }


def run_hbu_analysis(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Performs full Highest-and-Best-Use analysis across alternative uses.

    Required payload:
        property        dict
            location          str
            area              float
            current_use       str    (optional)
            current_zoning    str    (optional)
            asset_id          str    (optional)
        alternative_uses  list[dict]   ≥ 2 scenarios
        discount_rate     float        decimal (e.g. 0.10 for 10%)

    Returns
    -------
    dict — full analysis with per-scenario evaluations and recommended use.
    """
    prop = payload.get("property") or {}
    if not isinstance(prop, dict):
        raise ValueError("property يجب أن يكون كائناً يصف الأصل.")

    alternatives: List[Dict[str, Any]] = list(payload.get("alternative_uses") or [])
    if len(alternatives) < 2:
        raise ValueError("يجب توفير سيناريوهين على الأقل في alternative_uses للمقارنة.")

    discount_rate = float(payload.get("discount_rate", 0.10))
    if discount_rate <= 0:
        raise ValueError("discount_rate يجب أن يكون قيمة موجبة (مثلاً 0.10 لـ 10%).")

    valuation_date = str(payload.get("valuation_date") or datetime.today().strftime("%Y-%m-%d"))

    # ── 1. Evaluate each scenario ─────────────────────────────────────────────
    evaluated: List[Dict[str, Any]] = [
        _evaluate_scenario(s, discount_rate) for s in alternatives
    ]

    # ── 2. Test 4: Maximally Productive ───────────────────────────────────────
    candidates = [e for e in evaluated if e["passes_first_three"]]
    if candidates:
        best = max(candidates, key=lambda e: e["npv"])
        recommended_use = best["use_name"]
        recommended_npv = best["npv"]
        recommendation_note = (
            f"الاستخدام «{best['use_name']}» يحقق أعلى صافي قيمة حالية "
            f"({recommended_npv:,.0f}) من بين {len(candidates)} سيناريو مجدٍ، "
            f"وهو يجتاز الاختبارات الأربعة لـ HBU."
        )
        # Mark winning scenario
        for e in evaluated:
            e["test_4_max_productive"] = (e is best)
            e["final_verdict"] = (
                "أعلى وأفضل استغلال (HBU) — موصى به" if e is best
                else (e["verdict_so_far"] if not e["passes_first_three"]
                      else "مرشَّح ولكن ليس الأعلى إنتاجية")
            )
    else:
        recommended_use = None
        recommended_npv = None
        recommendation_note = (
            "لا يوجد سيناريو يجتاز الاختبارات الثلاثة الأولى. "
            "يُوصى بإعادة دراسة المعاملات أو افتراضات السوق."
        )
        for e in evaluated:
            e["test_4_max_productive"] = False
            e["final_verdict"] = e["verdict_so_far"]

    # ── 3. Comparison summary ─────────────────────────────────────────────────
    comparison_table = [
        {
            "use_name":            e["use_name"],
            "legally_permissible": e["test_1_legal"],
            "physically_possible": e["test_2_physical"],
            "financially_feasible": e["test_3_financial"],
            "maximally_productive": e["test_4_max_productive"],
            "npv":                 e["npv"],
            "irr_pct":             e["irr_pct"],
            "payback_years":       e["payback_years"],
            "verdict":             e["final_verdict"],
        }
        for e in evaluated
    ]

    # ── 4. Result ─────────────────────────────────────────────────────────────
    return {
        "logic":             "HBU",
        "valuation_date":    valuation_date,
        "discount_rate":     discount_rate,
        "discount_rate_pct": discount_rate * 100,
        "property": {
            "asset_id":       str(prop.get("asset_id", "")),
            "location":       str(prop.get("location", "غير محدد")),
            "area":           float(prop.get("area", 0)),
            "current_use":    str(prop.get("current_use", "")),
            "current_zoning": str(prop.get("current_zoning", "")),
        },
        "scenarios_evaluated": evaluated,
        "comparison_table":    comparison_table,
        "recommended_use":     recommended_use,
        "recommended_npv":     recommended_npv,
        "recommendation_note": recommendation_note,
        "standards_note": (
            "تم تطبيق إطار IVS / USPAP / Appraisal Institute لتحديد أعلى وأفضل "
            "استغلال عبر الاختبارات الأربعة المتسلسلة: ممكن قانونياً → ممكن مادياً → "
            "مجدٍ مالياً → أعلى إنتاجية."
        ),
    }


# ════════════════════════════════════════════════════════════════════════════
#  EXCEL REPORT
# ════════════════════════════════════════════════════════════════════════════

def generate_hbu_excel(result: Dict[str, Any], output_dir: str = "") -> str:
    """
    Generates an RTL Arabic Excel report for the HBU analysis result.
    Returns the absolute path of the produced .xlsx file.
    """
    import xlsxwriter  # type: ignore

    out_dir = output_dir.strip() if output_dir.strip() else _OUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(out_dir, f"hbu_analysis_{timestamp}.xlsx")

    NAVY, GOLD, WHITE, LIGHT, GREEN, RED, GREY, YELLOW = (
        "#1F3864", "#C9A227", "#FFFFFF", "#EAF0FB", "#1E8449", "#C0392B", "#F2F2F2", "#F4D03F"
    )

    wb = xlsxwriter.Workbook(filepath)

    # ── Sheet 1: Summary ──────────────────────────────────────────────────────
    ws = wb.add_worksheet("ملخص HBU")
    ws.right_to_left()

    title_fmt   = wb.add_format({"bold": True, "font_size": 16, "bg_color": NAVY,
                                 "font_color": WHITE, "align": "center", "valign": "vcenter"})
    section_fmt = wb.add_format({"bold": True, "font_size": 12, "bg_color": GOLD,
                                 "font_color": NAVY, "align": "right"})
    label_fmt   = wb.add_format({"bold": True, "bg_color": LIGHT, "align": "right", "border": 1})
    val_fmt     = wb.add_format({"align": "right", "border": 1})
    num_fmt     = wb.add_format({"num_format": "#,##0.00", "align": "right", "border": 1})
    pct_fmt     = wb.add_format({"num_format": "0.00%", "align": "right", "border": 1})
    head_fmt    = wb.add_format({"bold": True, "bg_color": NAVY, "font_color": WHITE,
                                 "align": "center", "border": 1, "text_wrap": True})
    pass_fmt    = wb.add_format({"bg_color": GREEN, "font_color": WHITE, "align": "center", "border": 1})
    fail_fmt    = wb.add_format({"bg_color": RED,   "font_color": WHITE, "align": "center", "border": 1})
    win_fmt     = wb.add_format({"bg_color": GOLD,  "font_color": NAVY, "bold": True, "align": "center", "border": 1})
    note_fmt    = wb.add_format({"italic": True, "bg_color": GREY, "align": "right", "text_wrap": True, "border": 1})

    ws.set_column(0, 0, 28)
    ws.set_column(1, 1, 40)

    ws.merge_range(0, 0, 0, 1, "تحليل أعلى وأفضل استغلال (HBU Analysis)", title_fmt)
    ws.set_row(0, 32)

    ws.write(1, 0, "تاريخ التقييم", label_fmt);     ws.write(1, 1, result["valuation_date"], val_fmt)
    ws.write(2, 0, "موقع الأصل", label_fmt);       ws.write(2, 1, result["property"]["location"], val_fmt)
    ws.write(3, 0, "المساحة (م²)", label_fmt);     ws.write_number(3, 1, result["property"]["area"], num_fmt)
    ws.write(4, 0, "الاستخدام الحالي", label_fmt); ws.write(4, 1, result["property"]["current_use"] or "—", val_fmt)
    ws.write(5, 0, "النطاق التخطيطي", label_fmt);  ws.write(5, 1, result["property"]["current_zoning"] or "—", val_fmt)
    ws.write(6, 0, "معدل الخصم", label_fmt);       ws.write_number(6, 1, result["discount_rate"], pct_fmt)

    r = 8
    ws.merge_range(r, 0, r, 1, "التوصية", section_fmt); r += 1
    ws.write(r, 0, "أعلى وأفضل استغلال", label_fmt)
    ws.write(r, 1, result["recommended_use"] or "—", win_fmt if result["recommended_use"] else fail_fmt)
    r += 1
    ws.write(r, 0, "صافي القيمة الحالية المتوقعة", label_fmt)
    if result["recommended_npv"] is not None:
        ws.write_number(r, 1, result["recommended_npv"], num_fmt)
    else:
        ws.write(r, 1, "—", val_fmt)
    r += 1
    ws.merge_range(r, 0, r, 1, result["recommendation_note"], note_fmt)
    ws.set_row(r, 38)
    r += 2

    ws.merge_range(r, 0, r, 1, result["standards_note"], note_fmt)
    ws.set_row(r, 38)

    # ── Sheet 2: Comparison Matrix ────────────────────────────────────────────
    ws2 = wb.add_worksheet("جدول المقارنة")
    ws2.right_to_left()
    ws2.set_column(0, 0, 22)
    ws2.set_column(1, 7, 16)

    headers = [
        "الاستخدام البديل",
        "Test 1\nقانوني",
        "Test 2\nمادي",
        "Test 3\nمالي",
        "Test 4\nأعلى إنتاجية",
        "NPV (EGP)",
        "IRR %",
        "فترة الاسترداد (سنوات)",
    ]
    for c, h in enumerate(headers):
        ws2.write(0, c, h, head_fmt)
    ws2.set_row(0, 36)

    def _bool_cell(ws_, row_, col_, val_):
        ws_.write(row_, col_, "✓" if val_ else "✗", pass_fmt if val_ else fail_fmt)

    rr = 1
    for row in result["comparison_table"]:
        ws2.write(rr, 0, row["use_name"], win_fmt if row["maximally_productive"] else label_fmt)
        _bool_cell(ws2, rr, 1, row["legally_permissible"])
        _bool_cell(ws2, rr, 2, row["physically_possible"])
        _bool_cell(ws2, rr, 3, row["financially_feasible"])
        _bool_cell(ws2, rr, 4, row["maximally_productive"])
        ws2.write_number(rr, 5, row["npv"], num_fmt)
        if row["irr_pct"] is not None:
            ws2.write_number(rr, 6, row["irr_pct"] / 100.0, pct_fmt)
        else:
            ws2.write(rr, 6, "—", val_fmt)
        if row["payback_years"] is not None:
            ws2.write_number(rr, 7, row["payback_years"], num_fmt)
        else:
            ws2.write(rr, 7, "—", val_fmt)
        rr += 1

    # Verdict column
    rr += 1
    ws2.merge_range(rr, 0, rr, 7, "ملاحظات الحكم النهائي لكل سيناريو:", section_fmt)
    rr += 1
    for row in result["comparison_table"]:
        ws2.write(rr, 0, row["use_name"], label_fmt)
        ws2.merge_range(rr, 1, rr, 7, row["verdict"],
                        win_fmt if row["maximally_productive"] else val_fmt)
        rr += 1

    # ── Sheet 3: Cashflow Detail per Scenario ─────────────────────────────────
    ws3 = wb.add_worksheet("التدفقات النقدية")
    ws3.right_to_left()
    ws3.set_column(0, 0, 20)

    max_years = max((len(s["cashflows"]) for s in result["scenarios_evaluated"]), default=0)
    ws3.write(0, 0, "السيناريو / السنة", head_fmt)
    for y in range(max_years):
        ws3.write(0, y + 1, f"سنة {y}", head_fmt)
    ws3.set_column(1, max_years, 14)

    for i, s in enumerate(result["scenarios_evaluated"], start=1):
        ws3.write(i, 0, s["use_name"],
                  win_fmt if s.get("test_4_max_productive") else label_fmt)
        for y, cf in enumerate(s["cashflows"]):
            ws3.write_number(i, y + 1, cf, num_fmt)

    wb.close()
    return filepath
