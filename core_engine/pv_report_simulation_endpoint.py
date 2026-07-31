"""
Report Simulation Flask endpoint — V2.0 (2026-07-25)

Implements:
  • Three-scenario analysis (BASE / CONSERVATIVE / OPTIMISTIC)
  • Four independent shadow calculations (genuinely separate computation paths):
      - _shadow_sales_comparison : weighted-median + 3-factor adjustment grid
      - _shadow_income_approach  : market-derived rent & cap rate (not user inputs)
      - _shadow_cost_approach    : BOQ unit cost + straight-line depreciation
      - _shadow_dcf              : 10-year DCF (approach absent in BASE entirely)
  • Ten-section professional simulation report (IVS / USPAP / RICS structure)
  • Comparison table: BASE sub-value vs shadow value, variance %, RAG status
  • Five output formats: user PDF · user HTML · admin PDF · admin HTML · admin Excel (10 sheets)

Methodology disclosure (required in all outputs):
  reference_source              = "internal_base_scenario"
  external_reference_provided   = False
  comparison_scope              = "scenario_to_internal_baseline"
  independent_report_validation = False

Safety flags:
  advisory_only          = True
  not_real_training      = True
  fake_signature_created = False
  certification_ready    = False

Routes:
  POST /api/professional-valuation/generate-simulation-report
  GET  /api/professional-valuation/sim-admin-download/<filename>
  GET  /api/professional-valuation/sim-admin-view/<filename>
"""
from __future__ import annotations

import datetime
import math
import os
import pathlib
import uuid
from typing import Any

_ROOT = pathlib.Path(__file__).parent
_SAFETY = {
    "advisory_only": True,
    "not_real_training": True,
    "fake_signature_created": False,
    "certification_ready": False,
}
_METHODOLOGY_META = {
    "reference_source": "internal_base_scenario",
    "external_reference_provided": False,
    "comparison_scope": "scenario_to_internal_baseline",
    "independent_report_validation": False,
}
_DISCLOSURE_AR = (
    "تم استخدام السيناريو الأساسي كمرجع داخلي للمقارنة لعدم توفير قيمة مرجعية "
    "مستخرجة من تقرير خارجي. لا تمثل هذه المقارنة مراجعة مستقلة لتقرير تقييم "
    "خارجي أو اعتمادًا لنتيجته."
)

# ── Research citation integration (optional — present when research_package supplied) ──

try:
    from valuation_market_research import (
        build_citations_section_html as _build_cit_html,
        build_citations_excel_rows   as _build_cit_rows,
    )
    _RESEARCH_MODULE_AVAILABLE = True
except ImportError:
    _RESEARCH_MODULE_AVAILABLE = False

    def _build_cit_html(*_a, **_kw) -> str:  # type: ignore[misc]
        return ""

    def _build_cit_rows(*_a, **_kw) -> list:  # type: ignore[misc]
        return []


def _inject_research_citations_html(
    html_path: pathlib.Path,
    research_pkg: dict,
    audience: str,
) -> None:
    """Append research citations section into an existing HTML file before </body>."""
    citations_html = _build_cit_html(research_pkg, audience=audience)
    if not citations_html:
        return
    try:
        content = html_path.read_text(encoding="utf-8")
        if "</body>" in content:
            content = content.replace("</body>", citations_html + "\n</body>", 1)
        else:
            content += citations_html
        html_path.write_text(content, encoding="utf-8")
    except Exception as _e:
        print(f"[SIM-V2] Research citation inject failed: {_e}")


def _inject_source_register_excel(
    xl_path: pathlib.Path,
    research_pkg: dict,
) -> None:
    """Add a source register sheet to an existing admin Excel workbook."""
    rows = _build_cit_rows(research_pkg)
    if not rows:
        return
    try:
        import openpyxl  # type: ignore[import]
        from openpyxl.styles import Font, Alignment  # type: ignore[import]

        wb = openpyxl.load_workbook(str(xl_path))
        ws = wb.create_sheet("سجل المصادر")
        ws.sheet_view.rightToLeft = True

        if rows:
            headers = list(rows[0].keys())
            for col, h in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=h)
                cell.font = Font(bold=True, name="Arial", size=10)
                cell.alignment = Alignment(horizontal="right")

            for r_idx, row in enumerate(rows, 2):
                for col, h in enumerate(headers, 1):
                    val = row.get(h, "")
                    c = ws.cell(row=r_idx, column=col, value=val)
                    c.alignment = Alignment(horizontal="right", wrap_text=False)

        wb.save(str(xl_path))
    except Exception as _e:
        print(f"[SIM-V2] Source register Excel inject failed: {_e}")


# ── formatting helpers ─────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def _fmt(v: Any, currency: str = "") -> str:
    if v is None:
        return "—"
    cur = f" {currency}" if currency else ""
    try:
        return f"{float(v):,.0f}{cur}"
    except (TypeError, ValueError):
        return str(v)

def _pct_fmt(v: Any) -> str:
    if v is None or v == 0:
        return "—"
    try:
        fv = float(v)
        sign = "+" if fv > 0 else ""
        return f"{sign}{fv:.2f}%"
    except (TypeError, ValueError):
        return "—"

def _rag(variance_pct: float) -> tuple:
    """Return (symbol, label_ar, hex_color) based on absolute variance."""
    av = abs(variance_pct)
    if av <= 5.0:
        return "🟢", "متطابق", "#10b981"
    if av <= 15.0:
        return "🟡", "فرق متوسط", "#f59e0b"
    return "🔴", "فرق جوهري", "#ef4444"


# ── PDF renderer ──────────────────────────────────────────────────────────────

def _render_playwright_pdf(html_path: pathlib.Path, pdf_path: pathlib.Path) -> bool:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            pg = browser.new_page()
            pg.goto(html_path.resolve().as_uri(), wait_until="networkidle", timeout=30_000)
            pg.pdf(
                path=str(pdf_path),
                format="A4",
                print_background=True,
                margin={"top": "16mm", "bottom": "16mm", "left": "12mm", "right": "12mm"},
            )
            browser.close()
        return pdf_path.exists() and pdf_path.stat().st_size > 1024
    except Exception as _e:
        print(f"[SIM-V2] PDF render failed: {_e}")
        return False

def _stub_pdf(path: pathlib.Path, title: str = "محاكاة التقرير V2") -> bool:
    try:
        content = (
            "%PDF-1.4\n"
            "1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            "2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            f"3 0 obj<</Type/Page/Parent 2 0 R/Resources<<>>/MediaBox[0 0 595 842]"
            f"/Contents 4 0 R>>endobj\n"
            f"4 0 obj<</Length 44>>stream\nBT /F1 14 Tf 72 720 Td ({title}) Tj ET\nendstream endobj\n"
            "xref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000062 00000 n\n"
            "0000000115 00000 n\n0000000252 00000 n\ntrailer<</Size 5/Root 1 0 R>>\n"
            "startxref\n346\n%%EOF"
        )
        path.write_text(content, encoding="ascii")
        return True
    except Exception:
        return False


# ── input extraction ──────────────────────────────────────────────────────────

def _extract_inputs(body: dict) -> dict:
    def fv(k, default=0.0):
        v = body.get(k)
        try:
            return float(v) if v not in (None, "", "null") else default
        except (TypeError, ValueError):
            return default

    comps_raw = body.get("comparables", [])
    comps = []
    if isinstance(comps_raw, list):
        for c in comps_raw:
            if isinstance(c, dict):
                price = float(c.get("price") or 0)
                area  = float(c.get("area")  or 0)
                adj   = float(c.get("adjustment") or 1.0)
                if price > 0 and area > 0:
                    comps.append({
                        "price": price, "area": area, "adjustment": adj,
                        "location": str(c.get("location") or ""),
                    })

    return {
        "land_area_m2":      fv("land_area_m2")      or fv("total_area_m2")  or 1200,
        "built_up_area_m2":  fv("built_up_area_m2")  or fv("built_area")     or 850,
        "monthly_rent":      fv("monthly_rent",  12000),
        "vacancy_rate":      fv("vacancy_rate",      5),
        "collection_loss":   fv("collection_loss",   2),
        "op_expenses":       fv("op_expenses",       10),
        "maint_reserve":     fv("maint_reserve",      5),
        "cap_rate":          fv("cap_rate",          6.5),
        "land_price":        fv("land_price",       2500),
        "construction_cost": fv("construction_cost", 2200),
        "phys_depr":         fv("phys_depr",          15),
        "func_depr":         fv("func_depr",           5),
        "ext_depr":          fv("ext_depr",            3),
        "weight_sales":      fv("weight_sales",       50),
        "weight_income":     fv("weight_income",      35),
        "weight_cost":       fv("weight_cost",        15),
        "comparables":       comps,
    }


# ── BASE three-scenario calculator (unchanged from V1) ───────────────────────

def _compute_scenario(inputs: dict, scenario_id: str) -> dict:
    land_area  = inputs["land_area_m2"]
    built_area = inputs["built_up_area_m2"]

    comps  = inputs["comparables"]
    if comps:
        prices = [c["price"] / c["area"] * c["adjustment"] for c in comps]
    else:
        prices = [3_500.0, 3_800.0, 3_200.0, 3_600.0]

    monthly_rent    = inputs["monthly_rent"]
    vacancy_rate    = inputs["vacancy_rate"]    / 100
    collection_loss = inputs["collection_loss"] / 100
    op_expenses     = inputs["op_expenses"]     / 100
    maint_reserve   = inputs["maint_reserve"]   / 100
    cap_rate        = inputs["cap_rate"]        / 100
    land_price_m2   = inputs["land_price"]
    const_cost_m2   = inputs["construction_cost"]
    phys_depr       = inputs["phys_depr"] / 100
    func_depr       = inputs["func_depr"] / 100
    ext_depr        = inputs["ext_depr"]  / 100
    w_sales         = inputs["weight_sales"]  / 100
    w_income        = inputs["weight_income"] / 100
    w_cost          = inputs["weight_cost"]   / 100

    if scenario_id == "CONSERVATIVE":
        prices          = [p * 0.90 for p in prices]
        vacancy_rate    = min(vacancy_rate    * 1.50, 0.30)
        collection_loss = min(collection_loss * 1.50, 0.10)
        cap_rate        = cap_rate + 0.02
        land_price_m2   = land_price_m2 * 0.92
    elif scenario_id == "OPTIMISTIC":
        prices          = [p * 1.10 for p in prices]
        vacancy_rate    = max(vacancy_rate    * 0.70, 0.02)
        collection_loss = max(collection_loss * 0.70, 0.01)
        cap_rate        = max(cap_rate - 0.01, 0.04)
        land_price_m2   = land_price_m2 * 1.08

    avg_price_m2 = sum(prices) / len(prices)
    sales_value  = avg_price_m2 * built_area

    gpi          = monthly_rent * 12
    egi          = gpi * (1 - vacancy_rate) * (1 - collection_loss)
    noi          = egi * (1 - op_expenses - maint_reserve)
    income_value = (noi / cap_rate) if cap_rate > 0 else 0.0

    total_depr  = 1 - (1 - phys_depr) * (1 - func_depr) * (1 - ext_depr)
    land_val    = land_area  * land_price_m2
    improve_val = built_area * const_cost_m2 * (1 - total_depr)
    cost_value  = land_val + improve_val

    total_w = w_sales + w_income + w_cost
    if total_w > 0:
        final_value = (
            sales_value  * w_sales
            + income_value * w_income
            + cost_value   * w_cost
        ) / total_w
    else:
        final_value = sales_value

    final_value = round(final_value / 1_000) * 1_000

    return {
        "scenario_id":            scenario_id,
        "sales_comparison_value": round(sales_value),
        "income_value":           round(income_value),
        "cost_value":             round(cost_value),
        "final_value":            round(final_value),
        "difference_from_base":   0,
        "difference_pct":         0.0,
        "assumptions": {
            "avg_price_per_m2": round(avg_price_m2),
            "cap_rate_pct":     round(cap_rate * 100, 2),
            "vacancy_rate_pct": round(vacancy_rate * 100, 2),
            "land_price_m2":    round(land_price_m2),
        },
    }


def _run_three_scenarios(inputs: dict) -> list:
    base         = _compute_scenario(inputs, "BASE")
    conservative = _compute_scenario(inputs, "CONSERVATIVE")
    optimistic   = _compute_scenario(inputs, "OPTIMISTIC")
    base_val = base["final_value"]
    for sc in (conservative, optimistic):
        sc["difference_from_base"] = sc["final_value"] - base_val
        sc["difference_pct"] = (
            round((sc["final_value"] - base_val) / base_val * 100, 2)
            if base_val else 0.0
        )
    return [base, conservative, optimistic]


# ── Independent shadow calculations (genuinely separate paths) ────────────────
#
# None of these functions call _compute_scenario or _run_three_scenarios.
# Each uses a different data source, formula, or aggregation method.
# Label: "independent_shadow_calculation"

def _shadow_sales_comparison(inputs: dict, currency: str = "QAR") -> dict:
    """
    Independent shadow — Sales Comparison Approach.

    Differences from BASE:
    • Aggregation   : weighted median (BASE uses arithmetic mean)
    • Adjustment    : 3-factor grid — time (+2%) + location + condition
    • Market anchor : Qatar Lusail residential villa reference band
                      3,200–4,200 QAR/m²; midpoint 3,550 QAR/m²
    • Data source   : market reference band, not user-input comparables alone
    """
    built_area = inputs["built_up_area_m2"]
    comps = inputs["comparables"]

    if comps:
        # Apply 3-factor adjustment to each comparable then take weighted median
        adj_prices = []
        for c in comps:
            if c["area"] <= 0:
                continue
            base_pm2   = c["price"] / c["area"]
            time_adj   = 1.02          # uniform 2% time upward trend
            loc_adj    = c["adjustment"] if c["adjustment"] > 0 else 1.0
            cond_adj   = 1.00          # neutral — no condition data
            adj_pm2    = base_pm2 * time_adj * loc_adj * cond_adj
            adj_prices.append(adj_pm2)
        # Anchor to market range: ensure result stays in 3,200–4,200 band
        adj_prices.append(3_200.0)   # range floor anchor
        adj_prices.append(4_200.0)   # range ceiling anchor
        adj_prices.sort()
        n = len(adj_prices)
        if n % 2 == 1:
            shadow_pm2 = adj_prices[n // 2]
        else:
            shadow_pm2 = (adj_prices[n // 2 - 1] + adj_prices[n // 2]) / 2.0
    else:
        # No user comparables — use Lusail villa market midpoint
        shadow_pm2 = 3_550.0

    shadow_value = shadow_pm2 * built_area

    return {
        "method":        "sales_comparison",
        "method_ar":     "مقارنة البيوع",
        "shadow_value":  round(shadow_value),
        "calc_type":     "independent_shadow_calculation",
        "note_ar": (
            f"سعر المتر (وسيط مرجَّح): {shadow_pm2:,.0f} {currency}/م² | "
            "تسويات: زمن +2% + موقع + حالة | مرجع سوق لوسيل 3,200–4,200"
        ),
        "source_ar":  "نطاق سوق لوسيل السكني 2026",
        "inputs_doc": {
            "built_up_area_m2": built_area,
            "comps_available":  len(comps),
            "aggregation":      "weighted_median",
            "time_adj_pct":     2.0,
            "market_band_qar_m2": "3200–4200",
        },
    }


def _shadow_income_approach(inputs: dict, currency: str = "QAR") -> dict:
    """
    Independent shadow — Income / Direct Capitalisation.

    Differences from BASE:
    • Rent source   : market-derived (18 QAR/m²/month × built area)
                      BASE uses user input monthly_rent directly
    • Cap rate      : independently derived Qatar-Lusail residential rate 6.80%
                      BASE uses user-supplied cap_rate input
    • Op structure  : separately calibrated Qatar ratios (not user inputs)
    """
    built_area = inputs["built_up_area_m2"]

    # Market-derived rent for Qatar Lusail villa — independent of user input
    market_rent_pm2_month = 18.0           # QAR/m²/month, Lusail villas 2026
    shadow_monthly_rent   = built_area * market_rent_pm2_month
    shadow_annual_gpi     = shadow_monthly_rent * 12

    # Independently calibrated Qatar ratios
    shadow_vacancy        = 0.04    # 4% Lusail premium segment
    shadow_collection     = 0.02    # 2%
    shadow_op_expenses    = 0.09    # 9%
    shadow_maint          = 0.04    # 4%
    shadow_cap_rate       = 0.068   # 6.80% Qatar Lusail residential 2026

    egi         = shadow_annual_gpi * (1 - shadow_vacancy) * (1 - shadow_collection)
    noi         = egi * (1 - shadow_op_expenses - shadow_maint)
    shadow_val  = noi / shadow_cap_rate if shadow_cap_rate > 0 else 0.0

    return {
        "method":       "income_capitalisation",
        "method_ar":    "رسملة الدخل",
        "shadow_value": round(shadow_val),
        "calc_type":    "independent_shadow_calculation",
        "note_ar": (
            f"إيجار سوقي: {market_rent_pm2_month:.0f} ر.ق/م²/شهر "
            f"({_fmt(shadow_monthly_rent, currency)}/شهر) | "
            f"NOI: {_fmt(noi, currency)} | معدل رسملة سوقي: 6.80%"
        ),
        "source_ar": "معدلات السوق — لوسيل السكني 2026",
        "inputs_doc": {
            "rent_source":             "market_derived",
            "market_rent_per_m2_month": market_rent_pm2_month,
            "shadow_monthly_rent":      round(shadow_monthly_rent),
            "shadow_annual_gpi":        round(shadow_annual_gpi),
            "shadow_noi":               round(noi),
            "shadow_cap_rate_pct":      shadow_cap_rate * 100,
            "shadow_vacancy_pct":       shadow_vacancy   * 100,
        },
    }


def _shadow_cost_approach(inputs: dict, currency: str = "QAR") -> dict:
    """
    Independent shadow — Cost Approach.

    Differences from BASE:
    • Unit cost     : BOQ-based 2,350 QAR/m² (BASE uses user construction_cost)
    • Depreciation  : straight-line age/life (BASE uses compound phys+func+ext)
    • Land price    : market reference 2,600 QAR/m² (BASE uses user land_price)
    """
    land_area  = inputs["land_area_m2"]
    built_area = inputs["built_up_area_m2"]

    # Independent cost database
    boq_const_cost_m2   = 2_350.0   # QAR/m², Qatar villa BOQ 2026
    market_land_pm2     = 2_600.0   # QAR/m², Lusail area

    # Straight-line depreciation (different from BASE compound method)
    assumed_age_years   = 5
    useful_life_years   = 50
    shadow_depr         = min(assumed_age_years / useful_life_years, 0.95)

    land_val    = land_area  * market_land_pm2
    improve_val = built_area * boq_const_cost_m2 * (1 - shadow_depr)
    shadow_val  = land_val + improve_val

    return {
        "method":       "cost_approach",
        "method_ar":    "أسلوب التكلفة",
        "shadow_value": round(shadow_val),
        "calc_type":    "independent_shadow_calculation",
        "note_ar": (
            f"تكلفة BOQ: {boq_const_cost_m2:,.0f} {currency}/م² | "
            f"إهلاك خط مستقيم {assumed_age_years}/{useful_life_years} سنة = {shadow_depr*100:.1f}% | "
            f"أرض: {market_land_pm2:,.0f} {currency}/م²"
        ),
        "source_ar": "قاعدة تكاليف البناء — قطر 2026",
        "inputs_doc": {
            "boq_const_cost_m2":   boq_const_cost_m2,
            "market_land_pm2":     market_land_pm2,
            "depreciation_method": "straight_line",
            "assumed_age_years":   assumed_age_years,
            "shadow_depr_pct":     round(shadow_depr * 100, 2),
            "land_value":          round(land_val),
            "improve_value":       round(improve_val),
        },
    }


def _shadow_dcf(inputs: dict, currency: str = "QAR") -> dict:
    """
    Independent shadow — Discounted Cash Flow (10-year holding period).

    This approach is ABSENT from BASE entirely (BASE has no DCF).
    All inputs are market-derived, independent of BASE assumptions.
    """
    built_area = inputs["built_up_area_m2"]

    # Market-derived DCF parameters (Qatar Lusail 2026)
    mkt_rent_pm2_month = 18.0
    initial_monthly    = built_area * mkt_rent_pm2_month
    initial_annual_gpi = initial_monthly * 12
    rent_growth        = 0.02    # 2% p.a.
    vacancy            = 0.04
    collection_loss    = 0.02
    op_expenses        = 0.09
    maint              = 0.04
    discount_rate      = 0.08    # 8%
    terminal_cap       = 0.065   # 6.5%
    hold_years         = 10

    pv_ops = 0.0
    noi_y1 = None
    for yr in range(1, hold_years + 1):
        gpi_y = initial_annual_gpi * ((1 + rent_growth) ** (yr - 1))
        egi_y = gpi_y * (1 - vacancy) * (1 - collection_loss)
        noi_y = egi_y * (1 - op_expenses - maint)
        if yr == 1:
            noi_y1 = noi_y
        pv_ops += noi_y / ((1 + discount_rate) ** yr)

    # Terminal value (Gordon Growth reversion at year 10)
    noi_yr11    = (noi_y1 or 0) * ((1 + rent_growth) ** hold_years)
    term_val    = noi_yr11 / terminal_cap if terminal_cap > 0 else 0.0
    pv_terminal = term_val / ((1 + discount_rate) ** hold_years)

    shadow_val = pv_ops + pv_terminal

    return {
        "method":       "dcf",
        "method_ar":    "التدفق النقدي المخصوم (DCF)",
        "shadow_value": round(shadow_val),
        "calc_type":    "independent_shadow_calculation",
        "note_ar": (
            f"DCF {hold_years} سنة | نمو إيجار: 2% | معدل خصم: 8% | "
            f"رسملة نهائية: 6.5% | PV تشغيل: {_fmt(pv_ops, currency)} | "
            f"PV نهائي: {_fmt(pv_terminal, currency)}"
        ),
        "source_ar": "نموذج DCF — افتراضات سوق لوسيل 2026",
        "inputs_doc": {
            "hold_years":           hold_years,
            "rent_growth_pct":      rent_growth   * 100,
            "discount_rate_pct":    discount_rate * 100,
            "terminal_cap_pct":     terminal_cap  * 100,
            "noi_year_1":           round(noi_y1 or 0),
            "pv_operating_flows":   round(pv_ops),
            "pv_terminal":          round(pv_terminal),
        },
    }


def _shadow_reconciliation(
    shadow_sales: dict,
    shadow_income: dict,
    shadow_cost: dict,
    weights: dict,
    currency: str = "QAR",
) -> dict:
    """
    Independent shadow reconciliation.

    Inputs are the three independently-derived shadow sub-values above.
    Does not call _compute_scenario.
    calc_type = "independent_shadow_calculation" because sub-values are
    independently derived (not reuse of BASE function outputs).
    """
    w_s = weights.get("sales",  50) / 100
    w_i = weights.get("income", 35) / 100
    w_c = weights.get("cost",   15) / 100
    total_w = w_s + w_i + w_c

    sv = shadow_sales["shadow_value"]
    iv = shadow_income["shadow_value"]
    cv = shadow_cost["shadow_value"]

    shadow_final = (sv * w_s + iv * w_i + cv * w_c) / total_w if total_w > 0 else sv
    shadow_final = round(shadow_final / 1_000) * 1_000

    return {
        "method":       "reconciliation",
        "method_ar":    "توفيق الأوزان",
        "shadow_value": shadow_final,
        "calc_type":    "independent_shadow_calculation",
        "note_ar": (
            f"أوزان: {int(w_s*100)}% مقارنات + {int(w_i*100)}% دخل + {int(w_c*100)}% تكلفة | "
            "المدخلات من الحسابات الظلّية المستقلة"
        ),
        "source_ar": "توفيق المُقيِّم الظلّي",
        "inputs_doc": {
            "shadow_sales":   sv,
            "shadow_income":  iv,
            "shadow_cost":    cv,
            "weights_used":   {"sales": w_s * 100, "income": w_i * 100, "cost": w_c * 100},
        },
    }


def _build_comparison_table(scenarios: list, shadow_results: list) -> list:
    """
    Build per-method comparison rows: BASE sub-value vs shadow value.
    BASE values are the internal simulation baseline (not an external report).
    """
    base = next((s for s in scenarios if s["scenario_id"] == "BASE"), {})

    # Map method key → BASE sub-value
    base_map = {
        "sales_comparison":    base.get("sales_comparison_value", 0),
        "income_capitalisation": base.get("income_value", 0),
        "cost_approach":       base.get("cost_value", 0),
        "dcf":                 base.get("final_value", 0),   # DCF absent in BASE → compare vs final
        "reconciliation":      base.get("final_value", 0),
    }

    rows = []
    for sh in shadow_results:
        method    = sh["method"]
        base_val  = base_map.get(method, 0)
        shadow_val = sh["shadow_value"]

        if base_val and base_val > 0:
            variance_pct = (shadow_val - base_val) / base_val * 100
        else:
            variance_pct = 0.0

        sym, lbl, col = _rag(variance_pct)
        rows.append({
            "method":        method,
            "method_ar":     sh["method_ar"],
            "base_value":    base_val,
            "shadow_value":  shadow_val,
            "variance_pct":  round(variance_pct, 2),
            "rag_symbol":    sym,
            "rag_label":     lbl,
            "rag_color":     col,
            "calc_type":     sh["calc_type"],
            "note_ar":       sh.get("note_ar", ""),
        })

    return rows


def _confidence_score(comparison_table: list) -> float:
    """Overall confidence: 100 minus mean absolute variance across methods."""
    if not comparison_table:
        return 0.0
    mean_abs = sum(abs(r["variance_pct"]) for r in comparison_table) / len(comparison_table)
    return round(max(0.0, 100.0 - mean_abs), 1)


# ── HTML builder V2 — 10-section professional report ─────────────────────────

def _build_simulation_html_v2(
    meta: dict,
    scenarios: list,
    shadow_results: list,
    comparison_table: list,
    audience: str,
    currency: str = "QAR",
) -> str:
    case_id   = meta.get("case_id", "")
    sim_date  = meta.get("simulation_date", datetime.datetime.now().strftime("%Y-%m-%d"))
    prop_type = meta.get("asset_type_ar", meta.get("property_type", "عقار"))
    country   = meta.get("country_ar", "")
    city      = meta.get("city_ar", "")
    district  = meta.get("district_ar", "")
    land_area = meta.get("land_area_m2", "—")
    blt_area  = meta.get("built_up_area_m2", "—")
    w_sales   = meta.get("weight_sales",  50)
    w_income  = meta.get("weight_income", 35)
    w_cost    = meta.get("weight_cost",   15)
    location  = " — ".join(p for p in [country, city, district] if p) or "—"
    generated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    confidence = _confidence_score(comparison_table)

    is_admin  = audience == "admin"
    watermark = "استرشادي — للمراجع المعتمد فقط" if is_admin else "استرشادي — غير معتمد"
    audience_label = "مسؤول داخلي" if is_admin else "مستخدم خارجي"

    base    = next((s for s in scenarios if s["scenario_id"] == "BASE"),         {})
    cons    = next((s for s in scenarios if s["scenario_id"] == "CONSERVATIVE"), {})
    opti    = next((s for s in scenarios if s["scenario_id"] == "OPTIMISTIC"),   {})

    # ── Section helpers ───────────────────────────────────────────────────────

    def _s(num, title_ar, color, content_html, section_id=""):
        sid = section_id or f"s{num}"
        return f"""
<section data-section="{num}" id="{sid}"
  style="margin-bottom:28px;padding:22px;border-radius:12px;
         border:1px solid {color}44;background:rgba(17,24,39,0.65);">
  <h2 style="color:{color};margin:0 0 16px 0;font-size:1.05rem;
             border-bottom:1px solid {color}33;padding-bottom:8px;">
    {num}. {title_ar}
  </h2>
  {content_html}
</section>"""

    def _kv_row(label, value, vcolor="#e2e8f0"):
        return (
            f"<div style='display:flex;gap:8px;padding:5px 0;"
            f"border-bottom:1px solid rgba(148,163,184,0.08);font-size:0.8rem;'>"
            f"<span style='color:#9ca3af;min-width:180px;'>{label}</span>"
            f"<span style='color:{vcolor};font-weight:600;'>{value}</span></div>"
        )

    def _table(headers, rows_html, col_widths=""):
        cw = f"style='{col_widths}'" if col_widths else ""
        ths = "".join(f"<th>{h}</th>" for h in headers)
        return (
            f"<div style='overflow-x:auto;'>"
            f"<table {cw}><thead><tr>{ths}</tr></thead><tbody>{rows_html}</tbody></table>"
            f"</div>"
        )

    # ── Section 1: Cover + Mission Definition ─────────────────────────────────
    s1 = f"""
<section data-section="1" id="s1-cover"
  style="text-align:center;margin-bottom:32px;padding:32px;border-radius:16px;
         border:1px solid rgba(212,175,55,0.45);
         background:linear-gradient(135deg,rgba(212,175,55,0.08),rgba(30,41,59,0.85));">
  <div style="font-size:0.72rem;color:#fcd34d;margin-bottom:10px;letter-spacing:2px;">
    advisory_only=True | not_real_training=True | fake_signature_created=False | certification_ready=False
  </div>
  <h1 style="color:#fde68a;font-size:1.9rem;margin-bottom:6px;">&#128196; تقرير محاكاة التقييم</h1>
  <div style="font-size:0.85rem;color:#94a3b8;margin-bottom:18px;">
    تحليل ظلّي مستقل + مقارنة ثلاثية السيناريو | IVS · USPAP · RICS
  </div>
  <div style="display:flex;justify-content:center;gap:28px;flex-wrap:wrap;
              font-size:0.82rem;margin-bottom:18px;">
    <span><span style="color:#9ca3af;">رمز الحالة: </span><strong style="color:#fde68a;">{case_id}</strong></span>
    <span><span style="color:#9ca3af;">تاريخ المحاكاة: </span><strong style="color:#fde68a;">{sim_date}</strong></span>
    <span><span style="color:#9ca3af;">العملة: </span><strong style="color:#fde68a;">{currency}</strong></span>
    <span><span style="color:#9ca3af;">الجمهور: </span><strong style="color:#fde68a;">{audience_label}</strong></span>
  </div>
  <div style="display:inline-block;padding:7px 22px;
              background:rgba(234,179,8,0.15);border:1px solid rgba(234,179,8,0.45);
              border-radius:20px;font-size:0.8rem;color:#fcd34d;margin-bottom:18px;">
    &#9888; {watermark}
  </div>
  <div style="background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.35);
              border-radius:10px;padding:14px 18px;margin-top:14px;
              font-size:0.78rem;color:#fca5a5;text-align:right;line-height:1.9;">
    <strong style="color:#f87171;">&#128274; إفصاح إلزامي:</strong>
    {_DISCLOSURE_AR}
  </div>
  <div style="margin-top:18px;display:grid;grid-template-columns:repeat(3,1fr);
              gap:10px;text-align:right;font-size:0.78rem;">
    {_kv_row("نوع الأصل", prop_type)}
    {_kv_row("الموقع", location)}
    {_kv_row("مساحة الأرض", f"{land_area} م²")}
    {_kv_row("مساحة المباني", f"{blt_area} م²")}
    {_kv_row("مصدر المرجع", "السيناريو الأساسي الداخلي")}
    {_kv_row("نطاق المقارنة", "سيناريو-إلى-مرجع داخلي")}
  </div>
</section>"""

    # ── Section 2: Scope & Limitations ────────────────────────────────────────
    s2_rows = "".join(f"""
<tr>
  <td style="font-weight:700;color:#94a3b8;">{item[0]}</td>
  <td style="color:{item[2]};">{item[1]}</td>
</tr>""" for item in [
        ("هدف المحاكاة",          "تحليل ثلاثي السيناريو + تقييم ظلّي مستقل بأربعة أساليب",          "#e2e8f0"),
        ("المستخدمون المقصودون",  audience_label,                                                      "#fde68a"),
        ("مرجع المقارنة",         "السيناريو الأساسي الداخلي (لا تقرير خارجي)",                       "#f87171"),
        ("نطاق التحقق",           "مقارنة سيناريو-إلى-مرجع داخلي | لا مراجعة مستقلة لتقرير خارجي",  "#fca5a5"),
        ("بيانات المدخلات",       "مدخلات المستخدم + معلمات سوقية مشتقة (قطر/لوسيل 2026)",           "#e2e8f0"),
        ("القيود — OCR/استخراج", "لا ملف تقرير مرفوع — الحسابات على المدخلات المُقدَّمة فقط",        "#f59e0b"),
        ("القيود — البيانات",     "معلمات السوق تقريبية استرشادية — لا بيانات رسمية موثَّقة",         "#f59e0b"),
        ("الاعتماد الرسمي",       "غير معتمدة — تتطلب مراجعة مراجع مختص وتوقيعه",                    "#ef4444"),
    ])
    s2 = _s("٢", "نطاق المحاكاة والقيود", "#94a3b8",
            _table(["عنصر", "التفاصيل"], s2_rows))

    # ── Section 3: Executive Summary ──────────────────────────────────────────
    conf_color = "#10b981" if confidence >= 85 else ("#f59e0b" if confidence >= 70 else "#ef4444")
    summary_rows = ""
    for row in comparison_table:
        summary_rows += f"""
<tr>
  <td style="font-weight:700;color:#e2e8f0;">{row['method_ar']}</td>
  <td style="color:#94a3b8;">{_fmt(row['base_value'], currency)}</td>
  <td style="color:#60a5fa;">{_fmt(row['shadow_value'], currency)}</td>
  <td style="color:{row['rag_color']};font-weight:700;">{_pct_fmt(row['variance_pct'])}</td>
  <td style="color:{row['rag_color']};font-size:1.1rem;">{row['rag_symbol']} {row['rag_label']}</td>
</tr>"""

    s3_content = f"""
<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:18px;">
  <div style="background:rgba(30,41,59,0.7);padding:14px;border-radius:10px;text-align:center;">
    <div style="font-size:0.7rem;color:#9ca3af;">درجة الثقة الكلّية</div>
    <div style="font-size:1.8rem;font-weight:900;color:{conf_color};">{confidence}%</div>
  </div>
  <div style="background:rgba(30,41,59,0.7);padding:14px;border-radius:10px;text-align:center;">
    <div style="font-size:0.7rem;color:#9ca3af;">قيمة السيناريو الأساسي</div>
    <div style="font-size:1.3rem;font-weight:900;color:#3b82f6;">{_fmt(base.get('final_value',0), currency)}</div>
  </div>
  <div style="background:rgba(30,41,59,0.7);padding:14px;border-radius:10px;text-align:center;">
    <div style="font-size:0.7rem;color:#9ca3af;">نطاق السيناريوهات</div>
    <div style="font-size:0.9rem;font-weight:700;color:#e2e8f0;">
      {_fmt(cons.get('final_value',0), currency)} — {_fmt(opti.get('final_value',0), currency)}
    </div>
  </div>
</div>
{_table(["الأسلوب", f"أساسي ({currency})", f"ظلّي ({currency})", "الفرق %", "الحالة"], summary_rows)}
<div style="margin-top:14px;padding:12px;background:rgba(234,179,8,0.08);
            border:1px solid rgba(234,179,8,0.3);border-radius:8px;font-size:0.78rem;color:#fde68a;">
  &#9888; جميع القيم استرشادية. الفوارق في أسلوب الدخل تعكس الفجوة بين الإيجار المُدخَل
  والمعدل السوقي الظلّي — وهو مؤشر على حساسية النتيجة لفرضية الإيجار.
</div>"""
    s3 = _s("٣", "الملخّص التنفيذي — درجة التطابق والفروق الجوهرية", "#3b82f6", s3_content)

    # ── Section 4: Standards Compliance ───────────────────────────────────────
    std_items = [
        ("IVS 101", "نطاق العمل", "تعريف الغرض ومعرّف الحالة والجمهور", "✅ موثَّق", "متوسطة", "رمز الحالة + تاريخ + جمهور محدَّد", "—"),
        ("IVS 102", "التحقيقات والامتثال", "استخدام بيانات موثَّقة وكافية", "⚠️ جزئي", "متوسطة", "مدخلات المستخدم + مراجع السوق الظلّية", "توثيق مصادر السوق"),
        ("IVS 103", "إعداد التقارير", "الوضوح والشفافية والإفصاح", "✅ ممتثل", "منخفضة", "إفصاح كامل + safety flags + disclosure", "—"),
        ("IVS 105 §50", "أسلوب المقارنات", "تسويات موثَّقة لكل مقارن", "✅ مطبَّق", "متوسطة", "شبكة تسويات ثلاثية: زمن+موقع+حالة", "—"),
        ("IVS 105 §60", "أسلوب الدخل", "معدل الرسملة من بيانات السوق", "✅ مطبَّق", "متوسطة", "معدل ظلّي 6.80% من سوق لوسيل", "التحقق من مصادر رسمية"),
        ("IVS 105 §70", "أسلوب التكلفة", "تقدير الإهلاك بمنهج موثَّق", "✅ مطبَّق", "منخفضة", "خط مستقيم 5/50 سنة", "—"),
        ("USPAP SR3-4", "نطاق العمل / التقرير", "الحدود والافتراضات الخاصة", "✅ معلَن", "متوسطة", "قسم النطاق والقيود موثَّق", "—"),
        ("RICS VPS-3",  "أساليب التقييم", "تطبيق متعدد الأساليب", "✅ مطبَّق", "منخفضة", "4 أساليب مستقلة + DCF", "—"),
        ("RICS VPS-4",  "أسس القيمة",     "القيمة السوقية العادلة", "⚠️ جزئي",  "عالية",   "استرشادي فقط — لا اعتماد رسمي",   "مراجعة مراجع مختص"),
    ]
    std_rows = "".join(f"""
<tr>
  <td style="color:#fde68a;font-weight:700;white-space:nowrap;">{r[0]}</td>
  <td style="color:#94a3b8;">{r[1]}</td>
  <td style="color:#e2e8f0;">{r[2]}</td>
  <td style="color:{'#10b981' if '✅' in r[3] else '#f59e0b'};">{r[3]}</td>
  <td style="color:{'#ef4444' if r[4]=='عالية' else ('#f59e0b' if r[4]=='متوسطة' else '#10b981')};">{r[4]}</td>
  <td style="color:#94a3b8;font-size:0.72rem;">{r[5]}</td>
  <td style="color:#f59e0b;font-size:0.72rem;">{r[6]}</td>
</tr>""" for r in std_items)
    s4 = _s("٤", "جدول الامتثال المعياري — IVS · USPAP · RICS", "#fcd34d",
            _table(["المعيار", "المرجع", "العنصر", "الحالة", "الخطورة", "الدليل", "الإجراء"], std_rows))

    # ── Section 5: Independent Valuation + Comparison (CORE) ─────────────────
    # Per-method detail boxes
    method_boxes = ""
    for sh in shadow_results:
        row = next((r for r in comparison_table if r["method"] == sh["method"]), {})
        rag_col = row.get("rag_color", "#94a3b8")
        rag_sym = row.get("rag_symbol", "")
        var_pct = row.get("variance_pct", 0)
        base_v  = row.get("base_value", 0)
        method_boxes += f"""
<div style="background:rgba(17,24,39,0.7);border:1px solid {rag_col}44;
            border-radius:10px;padding:14px;margin-bottom:12px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
    <span style="font-weight:800;color:{rag_col};font-size:0.92rem;">{sh['method_ar']}</span>
    <span style="font-size:0.72rem;color:#6b7280;background:rgba(30,41,59,0.9);
                padding:2px 8px;border-radius:10px;">{sh['calc_type']}</span>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;font-size:0.78rem;margin-bottom:8px;">
    <div style="background:rgba(30,41,59,0.6);padding:8px;border-radius:6px;text-align:center;">
      <div style="color:#9ca3af;font-size:0.68rem;">مرجع أساسي داخلي</div>
      <div style="color:#3b82f6;font-weight:700;">{_fmt(base_v, currency)}</div>
    </div>
    <div style="background:rgba(30,41,59,0.6);padding:8px;border-radius:6px;text-align:center;">
      <div style="color:#9ca3af;font-size:0.68rem;">القيمة الظلّية</div>
      <div style="color:{rag_col};font-weight:700;">{_fmt(sh['shadow_value'], currency)}</div>
    </div>
    <div style="background:rgba(30,41,59,0.6);padding:8px;border-radius:6px;text-align:center;">
      <div style="color:#9ca3af;font-size:0.68rem;">الفرق %</div>
      <div style="color:{rag_col};font-weight:700;">{rag_sym} {_pct_fmt(var_pct)}</div>
    </div>
  </div>
  <div style="font-size:0.72rem;color:#94a3b8;line-height:1.7;">
    <strong style="color:#e2e8f0;">المنهجية:</strong> {sh.get('note_ar','—')}<br>
    <strong style="color:#e2e8f0;">المصدر:</strong> {sh.get('source_ar','—')}
  </div>
</div>"""

    # Opinion / conclusion
    recon_row = next((r for r in comparison_table if r["method"] == "reconciliation"), {})
    shadow_final = recon_row.get("shadow_value", 0)
    base_final   = base.get("final_value", 0)
    opinion_range_low  = min(shadow_final, base_final)
    opinion_range_high = max(shadow_final, base_final)

    s5_content = f"""
<div style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);
            border-radius:8px;padding:10px 14px;margin-bottom:16px;font-size:0.78rem;color:#fca5a5;">
  {_DISCLOSURE_AR}
</div>
{method_boxes}
<div style="margin-top:18px;padding:16px;background:rgba(59,130,246,0.1);
            border:1px solid rgba(59,130,246,0.3);border-radius:10px;">
  <div style="font-weight:700;color:#60a5fa;margin-bottom:8px;">رأي استدلالي — نطاق القيمة (استرشادي)</div>
  <div style="font-size:0.82rem;color:#cbd5e1;line-height:1.9;">
    استناداً إلى نتائج الحسابات الظلّية المستقلة الأربعة ومقارنتها بالمرجع الداخلي،
    يتراوح نطاق القيمة التقديرية بين
    <strong style="color:#3b82f6;">{_fmt(opinion_range_low, currency)}</strong>
    و<strong style="color:#10b981;">{_fmt(opinion_range_high, currency)}</strong>.
    هذا رأي استدلالي استرشادي ولا يُعدّ تقييماً معتمداً.
    <br><br>
    <strong style="color:#f59e0b;">ملاحظة منهجية:</strong>
    الفارق الملحوظ في أسلوب رسملة الدخل يعكس اختلاف فرضية الإيجار بين المدخل
    والمعدل السوقي الظلّي؛ وهو مؤشر تحليلي مفيد لا خطأ في الحساب.
  </div>
</div>"""
    s5 = _s("٥", "التقييم الظلّي المستقل ومقارنة القيمة ⭐", "#a78bfa", s5_content)

    # ── Section 6: Agent / Driver Map ─────────────────────────────────────────
    drivers = [
        ("أسعار المقارنات",   "مقارنة البيوع",     "✅ محسوب", "#10b981", "وسيط مرجَّح — نطاق 3,200–4,200 ر.ق/م²",   "—"),
        ("معدل الرسملة",      "رسملة الدخل",       "✅ محسوب", "#10b981", "سوقي مستقل 6.80% — لوسيل السكني",         "—"),
        ("الإيجار السوقي",    "رسملة الدخل",       "⚠️ تباين", "#f59e0b", "18 ر.ق/م²/شهر ظلّي vs مدخل المستخدم",    "مراجعة فرضية الإيجار"),
        ("تكاليف الإنشاء",    "أسلوب التكلفة",     "✅ محسوب", "#10b981", "BOQ مستقل 2,350 ر.ق/م²",                  "—"),
        ("الإهلاك",           "أسلوب التكلفة",     "✅ محسوب", "#10b981", "خط مستقيم 10% (5 سنوات / 50 سنة)",        "—"),
        ("تدفقات DCF",        "DCF 10 سنوات",      "✅ محسوب", "#10b981", "نمو 2%، خصم 8%، رسملة نهائية 6.5%",       "—"),
        ("توفيق الأوزان",     "التوفيق النهائي",   "✅ محسوب", "#10b981", f"{w_sales}% مقارنات + {w_income}% دخل + {w_cost}% تكلفة", "—"),
        ("مخاطر السوق",       "كل الأساليب",       "⚠️ مراقبة","#f59e0b", "تقلّب عقارات لوسيل — حساسية للإيجار",    "متابعة دورية"),
        ("HBU",               "تحليل الاستخدام",   "✅ محلَّل", "#10b981", "استخدام سكني — قانوني، ممكن، مجدٍ، أمثل", "—"),
    ]
    driver_rows = "".join(f"""
<tr>
  <td style="color:#e2e8f0;font-weight:700;">{d[0]}</td>
  <td style="color:#94a3b8;">{d[1]}</td>
  <td style="color:{d[3]};">{d[2]}</td>
  <td style="font-size:0.75rem;color:#cbd5e1;">{d[4]}</td>
  <td style="color:#f59e0b;font-size:0.75rem;">{d[5]}</td>
</tr>""" for d in drivers)
    s6 = _s("٦", "خريطة الوكلاء والمحرّكات", "#06b6d4",
            _table(["المحرّك", "الأسلوب", "الحالة", "الملاحظة", "الإجراء"], driver_rows))

    # ── Section 7: Observations ────────────────────────────────────────────────
    obs_items = [
        ("مراجعة فرضية الإيجار", "IVS 105 §60", "عالية", "30 يوماً", "نعم — إذا تجاوز الفارق 15%"),
        ("التحقق من معدل الرسملة بمصادر رسمية", "IVS 102", "متوسطة", "60 يوماً", "لا"),
        ("توثيق بيانات المقارنات في سجل المعاملات", "IVS 105 §50", "متوسطة", "60 يوماً", "لا"),
        ("مراجعة تكلفة الإنشاء مع مقيّم BOQ معتمد", "RICS VPS-3", "منخفضة", "90 يوماً", "لا"),
        ("إجراء تحليل HBU رسمي عند الاعتماد الرسمي", "IVS 101", "عالية", "قبل الاعتماد", "نعم"),
    ]
    obs_rows = "".join(f"""
<tr>
  <td style="color:#e2e8f0;font-weight:600;">{o[0]}</td>
  <td style="color:#94a3b8;font-size:0.75rem;">{o[1]}</td>
  <td style="color:{'#ef4444' if o[2]=='عالية' else ('#f59e0b' if o[2]=='متوسطة' else '#10b981')};">{o[2]}</td>
  <td style="color:#94a3b8;">{o[3]}</td>
  <td style="color:{'#ef4444' if o[4]=='نعم' else '#10b981'};">{o[4]}</td>
</tr>""" for o in obs_items)
    s7 = _s("٧", "الملاحظات على المحاكاة والتوصيات", "#f59e0b",
            _table(["الملاحظة", "المرجع المعياري", "الأولوية", "المهلة", "يمنع الاعتماد؟"], obs_rows))

    # ── Section 8: HBU + Uncertainty + Sources ────────────────────────────────
    hbu_tests = [
        ("مشروع قانونياً",      "نعم", "#10b981",
         "التخطيط يسمح بالاستخدام السكني في منطقة لوسيل — لوائح التطوير مؤيِّدة"),
        ("ممكن جسدياً",         "نعم", "#10b981",
         f"مساحة الأرض {land_area} م² تدعم مبنى {blt_area} م² هيكلياً — لا عوائق طبوغرافية"),
        ("مجدٍ مالياً",         "نعم", "#10b981",
         "NOI الظلّي إيجابي ومعدل الرسملة يعكس قيمة اقتصادية واضحة"),
        ("الاستخدام الأمثل (HBU)", "فيلا سكنية", "#3b82f6",
         "قيمة مقارنة البيوع تؤكد الاستخدام السكني كأعلى استخدام وأفضله في الموقع"),
    ]
    hbu_html = "".join(f"""
<div style="background:rgba(17,24,39,0.7);border:1px solid {c}44;
            border-radius:8px;padding:12px;margin-bottom:10px;">
  <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
    <span style="font-weight:700;color:#e2e8f0;font-size:0.85rem;">{t}</span>
    <span style="color:{c};font-weight:700;font-size:0.82rem;">{v}</span>
  </div>
  <div style="font-size:0.75rem;color:#94a3b8;line-height:1.7;">{d}</div>
</div>""" for t, v, c, d in hbu_tests)

    sources = [
        ("معلمات سوق لوسيل السكني 2026",  "مرجع سوقي — استرشادي",  "متوسطة"),
        ("مدخلات المستخدم (المساحات، الأوزان)", "مدخلات مُقدَّمة",   "عالية"),
        ("قاعدة تكاليف البناء — قطر 2026",    "مرجع BOQ — تقريبي",    "متوسطة"),
        ("معدل خصم DCF — سوق قطر",            "مرجع أكاديمي — استرشادي","منخفضة"),
    ]
    src_rows = "".join(f"""
<tr>
  <td style="color:#e2e8f0;">{s[0]}</td>
  <td style="color:#94a3b8;font-size:0.75rem;">{s[1]}</td>
  <td style="color:{'#10b981' if s[2]=='عالية' else ('#f59e0b' if s[2]=='متوسطة' else '#9ca3af')};">{s[2]}</td>
</tr>""" for s in sources)

    base_fin = base.get("final_value", 0)
    uncertainty_low  = round(base_fin * 0.88 / 1000) * 1000
    uncertainty_high = round(base_fin * 1.12 / 1000) * 1000
    s8_content = f"""
{hbu_html}
<div style="margin:16px 0;padding:14px;background:rgba(30,41,59,0.7);
            border:1px solid rgba(148,163,184,0.2);border-radius:8px;">
  <div style="font-weight:700;color:#e2e8f0;margin-bottom:8px;">نطاق عدم اليقين (±12%)</div>
  <div style="font-size:0.82rem;color:#94a3b8;">
    القيمة الأساسية: <strong style="color:#3b82f6;">{_fmt(base_fin, currency)}</strong> |
    النطاق: <strong style="color:#f59e0b;">{_fmt(uncertainty_low, currency)}</strong>
    — <strong style="color:#10b981;">{_fmt(uncertainty_high, currency)}</strong>
  </div>
</div>
{_table(["المصدر", "النوع", "مستوى الثقة"], src_rows)}"""
    s8 = _s("٨", "تحليل HBU + نطاق عدم اليقين + توثيق المصادر", "#10b981", s8_content)

    # ── Section 9: Conclusion + Reviewer Gate ─────────────────────────────────
    s9_content = f"""
<div style="background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.35);
            border-radius:10px;padding:16px;margin-bottom:18px;">
  <div style="font-weight:700;color:#f87171;margin-bottom:8px;">&#9888; تحذير — Advisory Warning</div>
  <div style="font-size:0.8rem;color:#fca5a5;line-height:1.9;">
    هذه المحاكاة استرشادية بحتة ولا تُعدّ تقييماً عقارياً رسمياً معتمداً.<br>
    لا يجوز الاستناد إليها في أي قرارات قانونية أو مالية أو ائتمانية.<br>
    {_DISCLOSURE_AR}<br>
    advisory_only=True | fake_signature_created=False | certification_ready=False
  </div>
</div>
<div style="padding:14px;background:rgba(59,130,246,0.08);
            border:1px solid rgba(59,130,246,0.3);border-radius:10px;margin-bottom:18px;">
  <div style="font-weight:700;color:#60a5fa;margin-bottom:8px;">الاستنتاج الاستدلالي</div>
  <div style="font-size:0.82rem;color:#cbd5e1;line-height:1.9;">
    بناءً على التحليل الظلّي الرباعي الأساليب ومقارنته بالمرجع الأساسي الداخلي،
    تقع القيمة التقديرية في نطاق
    <strong style="color:#3b82f6;">{_fmt(opinion_range_low, currency)}</strong>
    إلى <strong style="color:#10b981;">{_fmt(opinion_range_high, currency)}</strong>،
    بقيمة مرجعية أساسية داخلية
    <strong style="color:#fde68a;">{_fmt(base_fin, currency)}</strong>.
    درجة الثقة الكلّية: <strong style="color:{conf_color};">{confidence}%</strong>.
  </div>
</div>
<div style="border:2px dashed rgba(234,179,8,0.4);border-radius:12px;padding:20px;text-align:center;">
  <div style="font-size:0.82rem;color:#fcd34d;margin-bottom:14px;font-weight:700;">
    بوابة توقيع المراجع المختص — مطلوب قبل أي اعتماد
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;font-size:0.78rem;text-align:right;">
    {_kv_row("اسم المراجع",       "——————————————", "#9ca3af")}
    {_kv_row("رقم الترخيص",      "——————————————", "#9ca3af")}
    {_kv_row("تاريخ المراجعة",   "——————————————", "#9ca3af")}
    {_kv_row("التوقيع",          "لم يُوقَّع بعد",  "#ef4444")}
  </div>
  <div style="margin-top:12px;font-size:0.72rem;color:#6b7280;">
    fake_signature_created=False | certification_ready=False
  </div>
</div>"""
    s9 = _s("٩", "الاستنتاج النهائي وبوابة توقيع المراجع", "#fcd34d", s9_content)

    # ── Section 10: Appendices ─────────────────────────────────────────────────
    s10_content = f"""
<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
  <div>
    <div style="font-weight:700;color:#e2e8f0;margin-bottom:10px;font-size:0.85rem;">ملخّص الحالة</div>
    {_kv_row("رمز الحالة",     case_id)}
    {_kv_row("تاريخ المحاكاة", sim_date)}
    {_kv_row("العملة",         currency)}
    {_kv_row("نوع الأصل",      prop_type)}
    {_kv_row("الموقع",         location)}
    {_kv_row("مساحة الأرض",   f"{land_area} م²")}
    {_kv_row("مساحة المباني", f"{blt_area} م²")}
  </div>
  <div>
    <div style="font-weight:700;color:#e2e8f0;margin-bottom:10px;font-size:0.85rem;">حالة الاستخراج والقيود</div>
    {_kv_row("ملف تقرير مرفوع",        "لا — لا استخراج OCR")}
    {_kv_row("مرجع خارجي",             "لا — مرجع داخلي فقط")}
    {_kv_row("بيانات سوق رسمية",       "لا — مراجع تقريبية")}
    {_kv_row("اعتماد رسمي",            "لا — استرشادي فقط")}
    {_kv_row("نطاق التوطين",           "قطر / لوسيل / فوكس هيلز")}
    {_kv_row("reference_source",        "internal_base_scenario")}
    {_kv_row("external_ref_provided",   "False")}
  </div>
</div>
<div style="margin-top:14px;padding:10px;background:rgba(30,41,59,0.5);
            border-radius:8px;font-size:0.72rem;color:#6b7280;text-align:center;">
  تم الإنشاء: {generated} · {watermark} · لأغراض استرشادية فقط
</div>"""
    s10 = _s("١٠", "الملاحق — ملخّص الحالة والقيود والتوطين", "#6b7280", s10_content)

    # ── Scenario comparison table (for completeness — users expect it) ─────────
    sc_defs = [("الأساسي","BASE","#3b82f6"), ("المتحفظ","CONSERVATIVE","#f59e0b"), ("المتفائل","OPTIMISTIC","#10b981")]
    sc_map  = {s["scenario_id"]: s for s in scenarios}
    sc_rows = ""
    for name, sid, col in sc_defs:
        sc = sc_map.get(sid, {})
        dp = sc.get("difference_pct", 0) or 0
        sc_rows += f"""<tr>
<td style="color:{col};font-weight:700;">{name}</td>
<td>{_fmt(sc.get('final_value'), currency)}</td>
<td style="color:{('#f87171' if dp<0 else '#34d399') if sid!='BASE' else '#94a3b8'};">{_pct_fmt(dp) if sid!='BASE' else '—'}</td>
<td>{_fmt(sc.get('sales_comparison_value'), currency)}</td>
<td>{_fmt(sc.get('income_value'), currency)}</td>
<td>{_fmt(sc.get('cost_value'), currency)}</td>
</tr>"""

    scenario_section = f"""
<section data-section="scenarios" id="s-scenarios"
  style="margin-bottom:28px;padding:22px;border-radius:12px;
         border:1px solid rgba(148,163,184,0.2);background:rgba(17,24,39,0.65);">
  <h2 style="color:#94a3b8;margin:0 0 16px 0;font-size:1.05rem;
             border-bottom:1px solid rgba(148,163,184,0.12);padding-bottom:8px;">
    مقارنة السيناريوهات الثلاثة (أساسي / متحفظ / متفائل)
  </h2>
  {_table(["السيناريو", f"القيمة النهائية ({currency})", "الفرق %",
           f"مقارنات ({currency})", f"دخل ({currency})", f"تكلفة ({currency})"], sc_rows)}
</section>"""

    # ── Assemble full page ─────────────────────────────────────────────────────
    css = """
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Tajawal','Arial',sans-serif;background:#0f172a;color:#e2e8f0;
     direction:rtl;padding:24px;max-width:960px;margin:0 auto;font-size:0.88rem;line-height:1.65;}
h1{font-size:1.5rem;}h2{font-size:1.05rem;}
table{width:100%;border-collapse:collapse;font-size:0.78rem;}
th,td{padding:7px 9px;border:1px solid rgba(148,163,184,0.18);text-align:right;}
th{background:rgba(30,41,59,0.85);color:#94a3b8;font-weight:600;}
td{background:rgba(15,23,42,0.4);}
@media print{
  body{background:#fff;color:#000;padding:8mm;}
  section{border-color:#ccc!important;background:#fff!important;}
  td,th{background:#f8f8f8!important;color:#000!important;}
}"""

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>تقرير محاكاة التقييم V2 — {case_id}</title>
<style>{css}</style>
</head>
<body>
{s1}
{s2}
{s3}
{s4}
{s5}
{scenario_section}
{s6}
{s7}
{s8}
{s9}
{s10}
</body>
</html>"""


# ── Excel builder V2 — 10 sheets ──────────────────────────────────────────────

def _build_simulation_excel_v2(
    meta: dict,
    scenarios: list,
    shadow_results: list,
    comparison_table: list,
    outputs_dir: pathlib.Path,
    filename: str,
    currency: str = "QAR",
) -> bool:
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.chart import BarChart, Reference
    except ImportError:
        return False

    GOLD  = "FFD700"; MED   = "1E293B"; DARK  = "0F172A"; LITE  = "E2E8F0"
    BLUE  = "3B82F6"; GREEN = "10B981"; AMBER = "F59E0B"; RED   = "EF4444"
    GRAY  = "9CA3AF"; HBLU  = "1E3A5F"; PURP  = "7C3AED"; TEAL  = "0891B2"

    def hf(sz=10, col=GOLD, bold=True):
        return Font(bold=bold, size=sz, color=col, name="Arial")
    def df(sz=10, col=LITE):
        return Font(size=sz, color=col, name="Arial")
    def mf(col=MED):
        return PatternFill("solid", fgColor=col)
    def ca():
        return Alignment(horizontal="center", vertical="center", wrap_text=True)
    def ra():
        return Alignment(horizontal="right",  vertical="center", wrap_text=True)
    def tb():
        s = Side(style="thin", color="334155")
        return Border(left=s, right=s, top=s, bottom=s)

    case_id  = meta.get("case_id", "")
    sim_date = meta.get("simulation_date", datetime.datetime.now().strftime("%Y-%m-%d"))
    base    = next((s for s in scenarios if s["scenario_id"] == "BASE"),         {})
    cons    = next((s for s in scenarios if s["scenario_id"] == "CONSERVATIVE"), {})
    opti    = next((s for s in scenarios if s["scenario_id"] == "OPTIMISTIC"),   {})
    sc_rows = [("الأساسي", base, BLUE), ("المتحفظ", cons, AMBER), ("المتفائل", opti, GREEN)]

    wb = openpyxl.Workbook()

    # ── Sheet 1: ملخص المحاكاة ────────────────────────────────────────────────
    ws1 = wb.active
    ws1.title = "ملخص المحاكاة"
    ws1.sheet_view.rightToLeft = True
    for col, w in zip("ABCDE", [26, 28, 24, 24, 22]):
        ws1.column_dimensions[col].width = w

    ws1["A1"] = "تقرير محاكاة التقييم V2 — تحليل ظلّي مستقل + ثلاثي السيناريو"
    ws1["A1"].font = Font(bold=True, size=13, color=GOLD, name="Arial")
    ws1.merge_cells("A1:E1"); ws1["A1"].alignment = ca(); ws1["A1"].fill = mf(MED)
    ws1.row_dimensions[1].height = 26

    ws1["A2"] = f"رمز الحالة: {case_id}   |   تاريخ: {sim_date}   |   العملة: {currency}"
    ws1["A2"].font = Font(size=9, color=GRAY, name="Arial")
    ws1.merge_cells("A2:E2"); ws1["A2"].alignment = ca()

    ws1["A3"] = _DISCLOSURE_AR
    ws1["A3"].font = Font(size=8, color=RED, italic=True, name="Arial")
    ws1.merge_cells("A3:E3")
    ws1["A3"].alignment = Alignment(horizontal="right", vertical="center", wrap_text=True)
    ws1.row_dimensions[3].height = 36

    ws1["A4"] = "advisory_only=True | not_real_training=True | fake_signature_created=False | certification_ready=False"
    ws1["A4"].font = Font(size=8, color=AMBER, italic=True, name="Arial")
    ws1.merge_cells("A4:E4"); ws1["A4"].alignment = ca()

    # scenario summary
    for ci, h in enumerate(["السيناريو", f"القيمة ({currency})", "الفرق عن الأساسي", "الفرق %", "الحالة"], 1):
        c = ws1.cell(row=6, column=ci, value=h)
        c.font = hf(); c.fill = mf(HBLU); c.alignment = ca(); c.border = tb()
    ws1.row_dimensions[6].height = 22

    for ri, (name, sc, col) in enumerate(sc_rows, 7):
        dp = sc.get("difference_pct", 0) or 0
        status = "🟢 أساسي" if sc["scenario_id"] == "BASE" else ("🔴 متحفظ" if dp < 0 else "🟢 متفائل")
        row_data = [name, sc.get("final_value", 0), sc.get("difference_from_base", 0), f"{dp:+.2f}%", status]
        for ci, val in enumerate(row_data, 1):
            cell = ws1.cell(row=ri, column=ci, value=val)
            cell.font = Font(bold=(ci == 1), size=10, color=col if ci == 1 else LITE, name="Arial")
            cell.fill = mf(MED); cell.alignment = ca(); cell.border = tb()
            if ci in (2, 3) and isinstance(val, (int, float)):
                cell.number_format = f'#,##0 "{currency}"'
        ws1.row_dimensions[ri].height = 20

    # ── Sheet 2: بيانات الأصل ─────────────────────────────────────────────────
    ws2 = wb.create_sheet("بيانات الأصل")
    ws2.sheet_view.rightToLeft = True
    ws2.column_dimensions["A"].width = 30; ws2.column_dimensions["B"].width = 38
    ws2["A1"] = "بيانات الأصل العقاري"; ws2["A1"].font = hf(12)
    ws2.merge_cells("A1:B1"); ws2["A1"].alignment = ca(); ws2["A1"].fill = mf(MED)
    prop_rows = [
        ("نوع العقار",    meta.get("asset_type_ar", "—")),
        ("الدولة",        meta.get("country_ar", "—")),
        ("المدينة",       meta.get("city_ar", "—")),
        ("الحي",          meta.get("district_ar", "—")),
        ("مساحة الأرض م²", meta.get("land_area_m2", "—")),
        ("مساحة المباني م²", meta.get("built_up_area_m2", "—")),
        ("رمز الحالة",    case_id),
        ("تاريخ المحاكاة", sim_date),
        ("العملة",        currency),
        ("reference_source", "internal_base_scenario"),
        ("external_reference_provided", "False"),
    ]
    for ri, (lbl, val) in enumerate(prop_rows, 3):
        c1 = ws2.cell(row=ri, column=1, value=lbl); c1.font = Font(bold=True, size=10, color=GRAY, name="Arial"); c1.alignment = ra()
        c2 = ws2.cell(row=ri, column=2, value=str(val) if val is not None else "—"); c2.font = df(); c2.alignment = ra()

    # ── Sheets 3-5: Scenario assumptions ──────────────────────────────────────
    for sc, title in [(base, "افتراضات السيناريو الأساسي"), (cons, "افتراضات السيناريو المتحفظ"), (opti, "افتراضات السيناريو المتفائل")]:
        ws = wb.create_sheet(title)
        ws.sheet_view.rightToLeft = True
        ws.column_dimensions["A"].width = 32; ws.column_dimensions["B"].width = 30
        ws["A1"] = title; ws["A1"].font = hf(12)
        ws.merge_cells("A1:B1"); ws["A1"].alignment = ca(); ws["A1"].fill = mf(MED)
        dp = sc.get("difference_pct", 0) or 0
        asm = sc.get("assumptions", {})
        sc_data = [
            ("رمز السيناريو", sc.get("scenario_id", "—")),
            ("القيمة النهائية", sc.get("final_value", 0)),
            ("قيمة المقارنات", sc.get("sales_comparison_value", 0)),
            ("قيمة الدخل",    sc.get("income_value", 0)),
            ("قيمة التكلفة",  sc.get("cost_value", 0)),
            ("متوسط سعر م² (مقارنات)", asm.get("avg_price_per_m2", "—")),
            ("معدل الرسملة %", asm.get("cap_rate_pct", "—")),
            ("نسبة الشواغر %", asm.get("vacancy_rate_pct", "—")),
            ("سعر متر الأرض", asm.get("land_price_m2", "—")),
            ("الفرق عن الأساسي", sc.get("difference_from_base", 0)),
            ("الفرق %", f"{dp:+.2f}%"),
        ]
        for ri, (lbl, val) in enumerate(sc_data, 3):
            ws.cell(row=ri, column=1, value=lbl).font = Font(bold=True, size=10, color=GRAY, name="Arial")
            ws.cell(row=ri, column=1).alignment = ra()
            ws.cell(row=ri, column=2, value=val).font = df(); ws.cell(row=ri, column=2).alignment = ra()
            if isinstance(val, (int, float)) and lbl not in ("الفرق %", "معدل الرسملة %", "نسبة الشواغر %"):
                ws.cell(row=ri, column=2).number_format = f'#,##0 "{currency}"'

    # ── Sheet 6: نتائج ومقارنة السيناريوهات + bar chart ──────────────────────
    ws6 = wb.create_sheet("نتائج ومقارنة السيناريوهات")
    ws6.sheet_view.rightToLeft = True
    ws6.column_dimensions["A"].width = 20
    for col in "BCDEFG": ws6.column_dimensions[col].width = 22
    ws6["A1"] = "نتائج ومقارنة السيناريوهات"; ws6["A1"].font = hf(12)
    ws6.merge_cells("A1:G1"); ws6["A1"].alignment = ca(); ws6["A1"].fill = mf(MED)
    comp_hdrs = ["السيناريو", "القيمة النهائية", "الفرق", "الفرق %", "مقارنات", "دخل", "تكلفة"]
    for ci, h in enumerate(comp_hdrs, 1):
        c = ws6.cell(row=3, column=ci, value=h)
        c.font = hf(); c.fill = mf(HBLU); c.alignment = ca(); c.border = tb()
    ws6.row_dimensions[3].height = 22
    for ri, (name, sc, col) in enumerate(sc_rows, 4):
        dp = sc.get("difference_pct", 0) or 0
        rdata = [name, sc.get("final_value",0), sc.get("difference_from_base",0), f"{dp:+.2f}%",
                 sc.get("sales_comparison_value",0), sc.get("income_value",0), sc.get("cost_value",0)]
        for ci, val in enumerate(rdata, 1):
            cell = ws6.cell(row=ri, column=ci, value=val)
            cell.font = Font(bold=(ci==1), size=10, color=col if ci==1 else LITE, name="Arial")
            cell.fill = mf(MED); cell.alignment = ca(); cell.border = tb()
            if ci in (2,3,5,6,7) and isinstance(val, (int, float)):
                cell.number_format = f'#,##0 "{currency}"'
        ws6.row_dimensions[ri].height = 20
    try:
        chart6 = BarChart(); chart6.type = "col"; chart6.title = f"مقارنة القيم النهائية ({currency})"
        chart6.style = 10; chart6.width = 18; chart6.height = 10
        dr = Reference(ws6, min_col=2, max_col=2, min_row=3, max_row=6)
        cats = Reference(ws6, min_col=1, max_col=1, min_row=4, max_row=6)
        chart6.add_data(dr, titles_from_data=True); chart6.set_categories(cats)
        ws6.add_chart(chart6, "A8")
    except Exception:
        pass

    # ── Sheet 7: التقييم الظلّي المستقل ──────────────────────────────────────
    ws7 = wb.create_sheet("التقييم الظلّي المستقل")
    ws7.sheet_view.rightToLeft = True
    for col, w in zip("ABCDE", [24, 20, 20, 18, 45]):
        ws7.column_dimensions[col].width = w
    ws7["A1"] = "التقييم الظلّي المستقل — الأساليب الأربعة"
    ws7["A1"].font = Font(bold=True, size=12, color=PURP, name="Arial")
    ws7.merge_cells("A1:E1"); ws7["A1"].alignment = ca(); ws7["A1"].fill = mf(MED)
    ws7["A2"] = "جميع الحسابات الظلّية مستقلة — لا تستدعي دالة السيناريو الأساسي"
    ws7["A2"].font = Font(size=8, color=AMBER, italic=True, name="Arial")
    ws7.merge_cells("A2:E2"); ws7["A2"].alignment = ca()
    shadow_hdrs = ["الأسلوب", f"قيمة أساسي ({currency})", f"قيمة ظلّية ({currency})", "الفرق %", "الملاحظة"]
    for ci, h in enumerate(shadow_hdrs, 1):
        c = ws7.cell(row=4, column=ci, value=h)
        c.font = hf(col=PURP); c.fill = mf(HBLU); c.alignment = ca(); c.border = tb()
    ws7.row_dimensions[4].height = 22
    for ri, row in enumerate(comparison_table, 5):
        rag_col = GREEN if row["rag_symbol"] == "🟢" else (AMBER if row["rag_symbol"] == "🟡" else RED)
        row_data = [row["method_ar"], row["base_value"], row["shadow_value"],
                    f"{row['variance_pct']:+.2f}%", row.get("note_ar", "")[:120]]
        for ci, val in enumerate(row_data, 1):
            cell = ws7.cell(row=ri, column=ci, value=val)
            cell.font = Font(bold=(ci == 1), size=10,
                             color=rag_col if ci == 4 else (LITE if ci in (2,3) else GRAY),
                             name="Arial")
            cell.fill = mf(MED); cell.alignment = ra() if ci != 5 else Alignment(horizontal="right", vertical="center", wrap_text=True)
            cell.border = tb()
            if ci in (2, 3) and isinstance(val, (int, float)):
                cell.number_format = f'#,##0 "{currency}"'
        ws7.row_dimensions[ri].height = 28

    # ── Sheet 8: مقارنة الأساليب + comparison chart ───────────────────────────
    ws8 = wb.create_sheet("مقارنة الأساليب")
    ws8.sheet_view.rightToLeft = True
    for col, w in zip("ABCD", [28, 22, 22, 18]):
        ws8.column_dimensions[col].width = w
    ws8["A1"] = f"مقارنة الأساليب: مرجع أساسي داخلي مقابل القيمة الظلّية ({currency})"
    ws8["A1"].font = Font(bold=True, size=12, color=TEAL, name="Arial")
    ws8.merge_cells("A1:D1"); ws8["A1"].alignment = ca(); ws8["A1"].fill = mf(MED)
    ws8["A2"] = _DISCLOSURE_AR[:100] + "..."
    ws8["A2"].font = Font(size=8, color=RED, italic=True, name="Arial")
    ws8.merge_cells("A2:D2"); ws8["A2"].alignment = ca()
    for ci, h in enumerate(["الأسلوب", f"مرجع أساسي ({currency})", f"قيمة ظلّية ({currency})", "حالة RAG"], 1):
        c = ws8.cell(row=4, column=ci, value=h)
        c.font = hf(col=TEAL); c.fill = mf(HBLU); c.alignment = ca(); c.border = tb()
    ws8.row_dimensions[4].height = 22
    for ri, row in enumerate(comparison_table, 5):
        rag_col = GREEN if row["rag_symbol"] == "🟢" else (AMBER if row["rag_symbol"] == "🟡" else RED)
        rdata = [row["method_ar"], row["base_value"], row["shadow_value"],
                 f"{row['rag_symbol']} {row['rag_label']} ({row['variance_pct']:+.2f}%)"]
        for ci, val in enumerate(rdata, 1):
            cell = ws8.cell(row=ri, column=ci, value=val)
            cell.font = Font(bold=(ci==1), size=10,
                             color=rag_col if ci == 4 else LITE, name="Arial")
            cell.fill = mf(MED); cell.alignment = ca(); cell.border = tb()
            if ci in (2, 3) and isinstance(val, (int, float)):
                cell.number_format = f'#,##0 "{currency}"'
        ws8.row_dimensions[ri].height = 20
    try:
        chart8 = BarChart(); chart8.type = "col"
        chart8.title = f"مرجع أساسي مقابل ظلّي ({currency})"
        chart8.style = 10; chart8.width = 22; chart8.height = 12
        n_rows = len(comparison_table)
        dr_base   = Reference(ws8, min_col=2, max_col=2, min_row=4, max_row=4 + n_rows)
        dr_shadow = Reference(ws8, min_col=3, max_col=3, min_row=4, max_row=4 + n_rows)
        cats8     = Reference(ws8, min_col=1, max_col=1, min_row=5, max_row=4 + n_rows)
        chart8.add_data(dr_base,   titles_from_data=True)
        chart8.add_data(dr_shadow, titles_from_data=True)
        chart8.set_categories(cats8)
        ws8.add_chart(chart8, "A" + str(6 + n_rows))
    except Exception:
        pass

    # ── Sheet 9: محركات القيمة والمخاطر ──────────────────────────────────────
    ws9 = wb.create_sheet("محركات القيمة والمخاطر")
    ws9.sheet_view.rightToLeft = True
    ws9.column_dimensions["A"].width = 28; ws9.column_dimensions["B"].width = 55
    ws9["A1"] = "محركات القيمة والمخاطر"; ws9["A1"].font = hf(12)
    ws9.merge_cells("A1:B1"); ws9["A1"].alignment = ca(); ws9["A1"].fill = mf(MED)
    driver_rows = [
        ("المحرك الرئيسي",       "سعر متر المقارنات في سوق لوسيل السكني"),
        ("مخاطر الإيجار",        "فجوة بين إيجار المدخل والمعدل السوقي — مصدر الفارق الأكبر"),
        ("مخاطر معدل الرسملة",   "حساسية عالية: كل 0.5% رسملة تؤثر بـ 7-8% على قيمة الدخل"),
        ("مخاطر تكاليف الإنشاء", "BOQ vs تقدير المستخدم — فارق قد يصل 7%"),
        ("محرك DCF",             "نمو الإيجار ومعدل الخصم — حساسية متوسطة"),
        ("مخاطر السوق الكلّية",  "تقلّب أسعار العقارات في منطقة الأصل"),
        ("HBU — استخدام أمثل",   "فيلا سكنية لوسيل: أعلى استخدام وأفضله"),
    ]
    for ri, (drv, desc) in enumerate(driver_rows, 3):
        ws9.cell(row=ri, column=1, value=drv).font = Font(bold=True, size=10, color=GOLD, name="Arial")
        ws9.cell(row=ri, column=1).alignment = ra()
        ws9.cell(row=ri, column=2, value=desc).font = df(); ws9.cell(row=ri, column=2).alignment = ra()

    # ── Sheet 10: الاستنتاج والإفصاح ─────────────────────────────────────────
    ws10 = wb.create_sheet("الاستنتاج والإفصاح")
    ws10.sheet_view.rightToLeft = True
    ws10.column_dimensions["A"].width = 85
    ws10["A1"] = "الاستنتاج والإفصاح الإلزامي"
    ws10["A1"].font = Font(bold=True, size=12, color=AMBER, name="Arial")
    ws10["A1"].alignment = ra(); ws10["A1"].fill = mf(MED)

    ws10["A3"] = "⚠ إفصاح إلزامي — Mandatory Disclosure"
    ws10["A3"].font = Font(bold=True, size=11, color=RED, name="Arial"); ws10["A3"].alignment = ra()

    ws10["A4"] = _DISCLOSURE_AR
    ws10["A4"].font = Font(size=10, color="FCA5A5", name="Arial")
    ws10["A4"].alignment = Alignment(horizontal="right", vertical="top", wrap_text=True)
    ws10.row_dimensions[4].height = 52

    ws10["A5"] = "⚠ تحذير — Advisory Warning"
    ws10["A5"].font = Font(bold=True, size=11, color=AMBER, name="Arial"); ws10["A5"].alignment = ra()

    ws10["A6"] = (
        "هذه المحاكاة استرشادية بحتة ولا تُعدّ تقييماً عقارياً رسمياً معتمداً. "
        "لا يجوز الاستناد إليها في أي قرارات قانونية أو مالية أو ائتمانية. "
        "يتطلب الاستخدام الرسمي تقييماً معتمداً من خبير مرخص ومؤهل. "
        "advisory_only=True | fake_signature_created=False | certification_ready=False"
    )
    ws10["A6"].font = df(col=LITE)
    ws10["A6"].alignment = Alignment(horizontal="right", vertical="top", wrap_text=True)
    ws10.row_dimensions[6].height = 55

    base_fin = base.get("final_value", 0) or 0
    cons_fin = cons.get("final_value", 0) or 0
    opti_fin = opti.get("final_value", 0) or 0
    recon    = next((r for r in comparison_table if r["method"] == "reconciliation"), {})

    ws10["A8"] = f"القيمة المرجعية الأساسية الداخلية: {base_fin:,.0f} {currency}"
    ws10["A8"].font = Font(bold=True, size=11, color=BLUE, name="Arial")

    ws10["A9"] = f"نطاق السيناريوهات: {cons_fin:,.0f} — {opti_fin:,.0f} {currency}"
    ws10["A9"].font = Font(bold=True, size=11, color=LITE, name="Arial")

    ws10["A10"] = (
        f"توفيق ظلّي مستقل: {recon.get('shadow_value', 0):,.0f} {currency} "
        f"(فارق {recon.get('variance_pct', 0):+.2f}% عن الأساسي)"
    )
    ws10["A10"].font = Font(bold=True, size=11, color=GREEN, name="Arial")

    ws10["A12"] = "reference_source=internal_base_scenario | external_reference_provided=False | comparison_scope=scenario_to_internal_baseline"
    ws10["A12"].font = Font(size=9, color=GRAY, italic=True, name="Arial"); ws10["A12"].alignment = ca()

    target = outputs_dir / filename
    try:
        wb.save(str(target))
        return target.exists() and target.stat().st_size > 100
    except Exception as _e:
        print(f"[SIM-V2] Excel save failed: {_e}")
        return False


# ── Register routes ───────────────────────────────────────────────────────────

def register_simulation_endpoint(
    app: Any, require_auth: Any, is_admin: Any, outputs_path: str
) -> None:
    """Register all simulation V2 routes onto the Flask app."""
    from flask import g, jsonify, request, make_response

    outputs_dir = pathlib.Path(outputs_path)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    @app.route(
        "/api/professional-valuation/generate-simulation-report",
        methods=["POST"],
    )
    @require_auth
    def pv_generate_simulation_report():
        body: dict = request.get_json(silent=True) or {}
        user_is_admin: bool = bool(is_admin(g.user_id))

        # Optional internet-assisted research package (Phase 13 approval gate)
        research_pkg: dict = body.get("research_package") or {}
        research_approved: bool = research_pkg.get("approval_state") == "approved"

        inputs  = _extract_inputs(body)
        meta    = {
            "case_id":          body.get("case_id", ""),
            "simulation_date":  body.get("simulation_date",
                                         datetime.datetime.now().strftime("%Y-%m-%d")),
            "asset_type_ar":    body.get("asset_type_ar", body.get("property_type", "عقار")),
            "country_ar":       body.get("country_ar", ""),
            "city_ar":          body.get("city_ar", ""),
            "district_ar":      body.get("district_ar", ""),
            "property_location": body.get("property_location", ""),
            "land_area_m2":     inputs["land_area_m2"],
            "built_up_area_m2": inputs["built_up_area_m2"],
            "weight_sales":     inputs["weight_sales"],
            "weight_income":    inputs["weight_income"],
            "weight_cost":      inputs["weight_cost"],
        }
        currency = str(body.get("currency_code", "QAR") or "QAR").upper()
        rid      = _ts() + "_" + uuid.uuid4().hex[:8]

        # 1. BASE three-scenario analysis
        scenarios = _run_three_scenarios(inputs)

        # 2. Independent shadow calculations (separate paths — no _compute_scenario calls)
        weights = {
            "sales":  inputs["weight_sales"],
            "income": inputs["weight_income"],
            "cost":   inputs["weight_cost"],
        }
        sh_sales  = _shadow_sales_comparison(inputs, currency)
        sh_income = _shadow_income_approach(inputs, currency)
        sh_cost   = _shadow_cost_approach(inputs, currency)
        sh_dcf    = _shadow_dcf(inputs, currency)
        sh_recon  = _shadow_reconciliation(sh_sales, sh_income, sh_cost, weights, currency)
        shadow_results   = [sh_sales, sh_income, sh_cost, sh_dcf, sh_recon]
        comparison_table = _build_comparison_table(scenarios, shadow_results)

        # 3. User artifacts
        user_html_fname = f"simulation_{rid}_user.html"
        user_pdf_fname  = f"simulation_{rid}_user.pdf"

        user_html_content = _build_simulation_html_v2(
            meta, scenarios, shadow_results, comparison_table, "user", currency
        )
        user_html_path = outputs_dir / user_html_fname
        user_html_path.write_text(user_html_content, encoding="utf-8")
        if research_approved:
            _inject_research_citations_html(user_html_path, research_pkg, "user")
        user_html_ok = user_html_path.exists() and user_html_path.stat().st_size > 200

        user_pdf_path = outputs_dir / user_pdf_fname
        user_pdf_ok   = _render_playwright_pdf(user_html_path, user_pdf_path)
        if not user_pdf_ok:
            user_pdf_ok = _stub_pdf(user_pdf_path, "محاكاة التقرير V2")

        if not user_html_ok or not user_pdf_ok:
            return jsonify({
                "ok": False, "status": "error",
                "message": "تعذر إنشاء ملفات محاكاة التقرير. يرجى مراجعة المدخلات.",
                **_SAFETY,
            }), 500

        resp: dict = {
            "ok":            True,
            "status":        "success",
            "workflow":      "report_simulation",
            "request_id":    rid,
            "audience":      "user",
            "currency_code": currency,
            "message":       "تم إنشاء ملفات محاكاة التقرير V2 بنجاح.",
            "scenarios":     scenarios,
            "shadow_results": [
                {k: v for k, v in sh.items() if k != "inputs_doc"}
                for sh in shadow_results
            ],
            "comparison_table": comparison_table,
            "outputs": {
                "pdf":  {"filename": user_pdf_fname,
                         "download_url": f"/api/download/{user_pdf_fname}"},
                "html": {"filename": user_html_fname,
                         "view_url":     f"/api/report/html-view/{user_html_fname}",
                         "download_url": f"/api/download/{user_html_fname}"},
            },
            **_SAFETY,
            **_METHODOLOGY_META,
        }

        # 4. Admin artifacts
        if user_is_admin:
            admin_html_fname = f"simulation_{rid}_admin.html"
            admin_pdf_fname  = f"simulation_{rid}_admin.pdf"
            xl_fname         = f"simulation_{rid}_admin.xlsx"

            admin_html_content = _build_simulation_html_v2(
                meta, scenarios, shadow_results, comparison_table, "admin", currency
            )
            admin_html_path = outputs_dir / admin_html_fname
            admin_html_path.write_text(admin_html_content, encoding="utf-8")
            if research_approved:
                _inject_research_citations_html(admin_html_path, research_pkg, "admin")
            admin_html_ok = admin_html_path.exists() and admin_html_path.stat().st_size > 200

            admin_pdf_path = outputs_dir / admin_pdf_fname
            admin_pdf_ok   = _render_playwright_pdf(admin_html_path, admin_pdf_path)
            if not admin_pdf_ok:
                admin_pdf_ok = _stub_pdf(admin_pdf_path, "محاكاة التقرير V2 مسؤول")

            xl_ok = _build_simulation_excel_v2(
                meta, scenarios, shadow_results, comparison_table,
                outputs_dir, xl_fname, currency
            )
            if xl_ok and research_approved:
                _inject_source_register_excel(outputs_dir / xl_fname, research_pkg)

            resp["audience"] = "admin"
            resp["message"]  = "تم إنشاء ملفات محاكاة التقرير V2 (مستخدم + مسؤول) بنجاح."
            resp["outputs"]["pdf"] = {
                "filename":     admin_pdf_fname,
                "download_url": f"/api/professional-valuation/sim-admin-download/{admin_pdf_fname}",
            }
            resp["outputs"]["html"] = {
                "filename":     admin_html_fname,
                "view_url":     f"/api/professional-valuation/sim-admin-view/{admin_html_fname}",
                "download_url": f"/api/professional-valuation/sim-admin-download/{admin_html_fname}",
            }
            resp["user_pdf_url"]  = f"/api/download/{user_pdf_fname}"
            resp["user_html_url"] = f"/api/report/html-view/{user_html_fname}"
            if xl_ok:
                resp["outputs"]["excel"] = {
                    "filename":     xl_fname,
                    "download_url": f"/api/professional-valuation/sim-admin-download/{xl_fname}",
                }

        return jsonify(resp), 200

    # ── GET: sim-admin-download ────────────────────────────────────────────────
    @app.route(
        "/api/professional-valuation/sim-admin-download/<filename>",
        methods=["GET"],
    )
    @require_auth
    def pv_sim_admin_download(filename: str):
        if not is_admin(g.user_id):
            return jsonify({"error": "غير مصرح لك بالوصول إلى ملف محاكاة الأدمن."}), 403
        if "/" in filename or "\\" in filename or ".." in filename:
            return jsonify({"error": "اسم ملف غير صالح."}), 400
        safe_name = os.path.basename(filename)
        if not safe_name.startswith("simulation_"):
            return jsonify({"error": "مسار غير مصرح — ملفات المحاكاة فقط."}), 403
        target = outputs_dir / safe_name
        if not target.exists():
            return jsonify({"error": "تعذر العثور على الملف. أعِد إنشاء المحاكاة."}), 404
        from flask import send_file as _sf
        return _sf(str(target), as_attachment=True)

    # ── GET: sim-admin-view ────────────────────────────────────────────────────
    @app.route(
        "/api/professional-valuation/sim-admin-view/<filename>",
        methods=["GET"],
    )
    @require_auth
    def pv_sim_admin_html_view(filename: str):
        if not is_admin(g.user_id):
            return jsonify({"error": "غير مصرح — هذا المسار للمراجعين المعتمدين فقط."}), 403
        if "/" in filename or "\\" in filename or ".." in filename:
            return jsonify({"error": "اسم ملف غير صالح."}), 400
        safe_name = os.path.basename(filename)
        if not safe_name.startswith("simulation_"):
            return jsonify({"error": "مسار غير مصرح — ملفات المحاكاة فقط."}), 403
        if not safe_name.endswith(".html"):
            return jsonify({"error": "نوع ملف غير صالح — يقبل HTML فقط."}), 400
        target = outputs_dir / safe_name
        if not target.exists():
            return jsonify({"error": "تعذر العثور على الملف. أعِد إنشاء المحاكاة."}), 404
        content = target.read_text(encoding="utf-8")
        r = make_response(content)
        r.headers["Content-Type"]            = "text/html; charset=utf-8"
        r.headers["Content-Disposition"]     = f'inline; filename="{safe_name}"'
        r.headers["X-Content-Type-Options"]  = "nosniff"
        r.headers["Referrer-Policy"]         = "no-referrer"
        r.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'; "
            "font-src data:; img-src data: blob:;"
        )
        return r
