"""
master_report_generator.py
============================
Full IVS-compliant valuation report – mirrors EXAMPLE.xls + Dreamland reference.

Sheets generated (11 sheets):
  1.  التقرير           – Cover page + full narrative
  2.  مقارنات البيوع    – Sales comparison grid (5 comps, % adjustments)
  3.  المقارنات الإيجارية – Rental comparables
  4.  طريقة التكلفة     – Depreciated Replacement Cost (DRC)
  5.  رأسمالة الدخل     – Income capitalization (NOI / cap-rate)
  6.  التحليل المكاني   – Kriging + IDW spatial interpolation
  7.  الانحدار المتعدد  – OLS Multiple Regression (statsmodels)
  8.  الخيارات الحقيقية – Real Options Analysis (Black-Scholes simplified)
  9.  توفيق النتائج     – Weighted reconciliation of ALL methods
  10. محددات التقييم    – Assumptions & limitations
  11. شهادة             – Expert certificate

Entry point:
    generate_report(**kwargs) -> str   # returns path to .xlsx file
"""

import os
import math
import warnings
import numpy as np
import pandas as pd
from datetime import datetime
import xlsxwriter

warnings.filterwarnings("ignore")

# ─── Expert constants ─────────────────────────────────────────────────────────
EXPERT_NAME  = "هشام محمد محمد المهدى"
EXPERT_REG   = "29"
EXPERT_EMAIL = "appraiserman29@gmail.com"
EXPERT_PHONE = "01222230128"
AUTHORITY    = "الهيئة العامة للرقابة المالية"

# ─── Comparable database (Dreamland-style, 20 units) ──────────────────────────
# floor, rooms, area(m²), year_built, price_per_m2, x(lon), y(lat)
COMPS_DB = [
    {"id":"203101","floor":1,"rooms":6, "area":72,  "year":2016,"ppm":21956,"x":29.97791,"y":31.05436},
    {"id":"203102","floor":1,"rooms":6, "area":71,  "year":2016,"ppm":22000,"x":29.97791,"y":31.05383},
    {"id":"203201","floor":2,"rooms":6, "area":72,  "year":2016,"ppm":21885,"x":29.97766,"y":31.04647},
    {"id":"204301","floor":3,"rooms":8, "area":92,  "year":2017,"ppm":21436,"x":29.97790,"y":31.04300},
    {"id":"204401","floor":4,"rooms":8, "area":92,  "year":2017,"ppm":21368,"x":29.97790,"y":31.04200},
    {"id":"508-85","floor":8,"rooms":12,"area":297, "year":2000,"ppm":26208,"x":29.97760,"y":31.05800},
    {"id":"509-82","floor":9,"rooms":17,"area":417, "year":2000,"ppm":25773,"x":29.97750,"y":31.05600},
    {"id":"E1-13", "floor":1,"rooms":15,"area":372, "year":2000,"ppm":26855,"x":29.97800,"y":31.04700},
    {"id":"E1-53", "floor":5,"rooms":14,"area":331, "year":2000,"ppm":26925,"x":29.97810,"y":31.04750},
    {"id":"780-511","floor":5,"rooms":6,"area":67,  "year":2007,"ppm":23584,"x":29.97600,"y":31.05900},
    {"id":"782-110","floor":1,"rooms":6,"area":67,  "year":2007,"ppm":24303,"x":29.97620,"y":31.05700},
    {"id":"785-110","floor":1,"rooms":6,"area":67,  "year":2007,"ppm":24849,"x":29.97650,"y":31.05500},
    {"id":"203406","floor":4,"rooms":6,"area":72,   "year":2016,"ppm":21749,"x":29.97791,"y":31.05436},
    {"id":"204101","floor":1,"rooms":6,"area":70,   "year":2017,"ppm":21617,"x":29.97791,"y":31.04437},
    {"id":"D6-53", "floor":5,"rooms":13,"area":312, "year":2013,"ppm":17505,"x":29.97850,"y":31.04900},
    {"id":"E4-12", "floor":1,"rooms":9, "area":224, "year":2000,"ppm":27392,"x":29.97800,"y":31.04880},
    {"id":"E5-71", "floor":7,"rooms":22,"area":533, "year":2000,"ppm":25247,"x":29.97820,"y":31.04860},
    {"id":"784-107","floor":1,"rooms":6,"area":67,  "year":2009,"ppm":23273,"x":29.97650,"y":31.05480},
    {"id":"784-403","floor":4,"rooms":6,"area":67,  "year":2009,"ppm":23067,"x":29.97660,"y":31.05490},
    {"id":"785-104","floor":1,"rooms":9,"area":110, "year":2007,"ppm":24677,"x":29.97670,"y":31.05500},
]

# Rental database (annual EGP/m²)
RENTALS_DB = [
    {"id":"R-001","area":72, "floor":1,"year":2016,"rent_ppm":350,"location":"المعادي"},
    {"id":"R-002","area":90, "floor":2,"year":2015,"rent_ppm":320,"location":"المعادي"},
    {"id":"R-003","area":105,"floor":3,"year":2018,"rent_ppm":380,"location":"المعادي"},
    {"id":"R-004","area":80, "floor":1,"year":2017,"rent_ppm":340,"location":"المعادي"},
    {"id":"R-005","area":120,"floor":4,"year":2016,"rent_ppm":300,"location":"المعادي"},
]

INTEREST_RATE  = 0.085   # سعر الفائدة السائد 8.5%
ECONOMIC_LIFE  = 60      # العمر الاقتصادي للمباني (سنة)
LAND_COST_RATE = 0.30    # نسبة الأرض من إجمالي قيمة العقار (تقديرية)
BUILD_COST_PER_M2 = 5500 # تكلفة إنشاء المتر المربع (EGP)


# ─── Utility ──────────────────────────────────────────────────────────────────
def _fmt(v):
    try:
        return f"{float(v):,.2f}"
    except Exception:
        return str(v)


def _norm_cdf(x):
    """Cumulative normal distribution (used in Black-Scholes)."""
    return (1 + math.erf(x / math.sqrt(2))) / 2


# ═══════════════════════════════════════════════════════════════════════════════
#  VALUATION METHODS
# ═══════════════════════════════════════════════════════════════════════════════

def method_sales_comparison(area, price_per_m2):
    """
    اسلوب المقارنة بالبيوع السابقة
    Picks 5 nearest comparables by price, applies % adjustments.
    Returns dict with ppm, total, comps list.
    """
    comps = sorted(COMPS_DB, key=lambda c: abs(c["ppm"] - price_per_m2))[:5]
    rows = []
    for c in comps:
        # Adjustment factors (as in EXAMPLE.xls grid)
        adj_time        =  0.05   if c["year"] < 2018 else 0.0
        adj_location    =  0.0
        adj_area        = -0.05   if c["area"] > area * 1.3 else (0.05 if c["area"] < area * 0.7 else 0.0)
        adj_floor       =  0.02   if c["floor"] > 3 else (-0.02 if c["floor"] == 1 else 0.0)
        adj_finishing   =  0.0
        adj_total       = adj_time + adj_location + adj_area + adj_floor + adj_finishing
        adj_ppm         = c["ppm"] * (1 + adj_total)
        # Negotiation discount 5%
        final_ppm       = adj_ppm * 0.95
        rows.append({
            "id":           c["id"],
            "floor":        c["floor"],
            "rooms":        c.get("rooms", "-"),
            "area":         c["area"],
            "year":         c["year"],
            "base_ppm":     c["ppm"],
            "adj_time":     adj_time,
            "adj_location": adj_location,
            "adj_area":     adj_area,
            "adj_floor":    adj_floor,
            "adj_finishing":adj_finishing,
            "adj_total":    adj_total,
            "adj_ppm":      adj_ppm,
            "final_ppm":    final_ppm,
        })
    avg_ppm = float(np.mean([r["final_ppm"] for r in rows])) if rows else price_per_m2
    return {
        "ppm":   avg_ppm,
        "total": avg_ppm * area,
        "comps": rows,
    }


def method_cost_approach(area, price_per_m2, building_age):
    """
    اسلوب التكلفة (الاستبدال المستهلك DRC)
    Land value + Net Building Cost - Depreciation
    Mirrors EXAMPLE.xls rows 126-211.
    """
    # Land value (extraction method)
    land_value_pm2 = price_per_m2 * LAND_COST_RATE
    land_value     = land_value_pm2 * area

    # Building replacement cost components (EGP/m²)
    structural_cost = BUILD_COST_PER_M2 * 0.60   # الهيكل الإنشائي
    finishes_cost   = BUILD_COST_PER_M2 * 0.25   # التشطيبات
    mep_cost        = BUILD_COST_PER_M2 * 0.10   # الكهرباء والسباكة
    contingency     = BUILD_COST_PER_M2 * 0.05   # طوارئ وغير مباشر

    gross_build_cost = (structural_cost + finishes_cost + mep_cost + contingency) * area
    contractor_profit = gross_build_cost * 0.15   # ربح المقاول 15%
    total_build_cost  = gross_build_cost + contractor_profit

    # Depreciation (straight-line physical + 2% functional)
    effective_age  = min(building_age, ECONOMIC_LIFE)
    physical_depr  = (effective_age / ECONOMIC_LIFE) * total_build_cost
    functional_depr = total_build_cost * 0.02
    total_depr     = physical_depr + functional_depr
    net_build_cost = total_build_cost - total_depr

    total_value = land_value + net_build_cost

    return {
        "ppm":                total_value / area,
        "total":              total_value,
        "land_value":         land_value,
        "land_value_pm2":     land_value_pm2,
        "structural_cost":    structural_cost * area,
        "finishes_cost":      finishes_cost   * area,
        "mep_cost":           mep_cost        * area,
        "contingency":        contingency     * area,
        "gross_build_cost":   gross_build_cost,
        "contractor_profit":  contractor_profit,
        "total_build_cost":   total_build_cost,
        "physical_depr":      physical_depr,
        "functional_depr":    functional_depr,
        "total_depr":         total_depr,
        "net_build_cost":     net_build_cost,
        "building_age":       building_age,
        "economic_life":      ECONOMIC_LIFE,
        "depr_rate_pct":      round(effective_age / ECONOMIC_LIFE * 100, 1),
    }


def method_income_capitalization(area, rent_per_sqm_annual, cap_rate, building_age,
                                  land_value):
    """
    اسلوب رأسمالة الدخل
    Mirrors EXAMPLE.xls rows 178-189.
    """
    monthly_rent    = rent_per_sqm_annual * area / 12
    annual_gross    = rent_per_sqm_annual * area
    vacancy_loss    = annual_gross * 0.10          # 10% شاغر وإدارة
    net_income      = annual_gross - vacancy_loss

    remaining_life  = max(ECONOMIC_LIFE - building_age, 5)
    capital_recovery= 1.0 / remaining_life          # معدل استرداد رأس المال
    effective_cap   = INTEREST_RATE + capital_recovery  # معدل الرسملة الكلي

    land_return     = land_value * INTEREST_RATE    # عائد الأرض

    # If land return exceeds NOI (common in low-yield markets), fall back to
    # simple overall cap-rate to avoid negative building value
    if net_income > land_return:
        net_bldg_income = net_income - land_return
        building_value  = net_bldg_income / effective_cap if effective_cap > 0 else 0
        total_value     = building_value + land_value
    else:
        # Direct capitalisation: V = NOI / overall cap_rate
        net_bldg_income = net_income
        building_value  = net_income / effective_cap if effective_cap > 0 else 0
        total_value     = building_value

    return {
        "ppm":              total_value / area if area else 0,
        "total":            total_value,
        "monthly_rent":     monthly_rent,
        "annual_gross":     annual_gross,
        "vacancy_loss":     vacancy_loss,
        "net_income":       net_income,
        "remaining_life":   remaining_life,
        "capital_recovery": capital_recovery,
        "interest_rate":    INTEREST_RATE,
        "effective_cap":    effective_cap,
        "land_return":      land_return,
        "net_bldg_income":  net_bldg_income,
        "building_value":   building_value,
        "land_value":       land_value,
        "noi":              net_income,
        "cap_rate":         cap_rate,
        "rent_per_sqm":     rent_per_sqm_annual,
    }


def method_kriging(target_x, target_y):
    """التقييم المكاني بطريقة Kriging / IDW"""
    try:
        from pykrige.ok import OrdinaryKriging
        xs = [c["x"]   for c in COMPS_DB]
        ys = [c["y"]   for c in COMPS_DB]
        zs = [c["ppm"] for c in COMPS_DB]
        ok = OrdinaryKriging(xs, ys, zs, variogram_model="linear", verbose=False)
        z, var = ok.execute("points", [target_x], [target_y])
        return {"ppm": float(z[0]), "variance": float(var[0]), "method": "Ordinary Kriging (pykrige)"}
    except Exception as e:
        from scipy.spatial import distance
        dists   = [distance.euclidean([target_x, target_y], [c["x"], c["y"]]) + 1e-9
                   for c in COMPS_DB]
        weights = [1 / d**2 for d in dists]
        ppm     = sum(w * c["ppm"] for w, c in zip(weights, COMPS_DB)) / sum(weights)
        return {"ppm": ppm, "variance": 0, "method": f"IDW (fallback: {e})"}


def method_real_options(base_ppm, area, building_age,
                        volatility=0.08, time_years=1.0, risk_free=0.12,
                        development_cost_pm2=None):
    """
    الخيارات الحقيقية (Real Options Analysis)
    Black-Scholes: C = S·N(d1) - K·e^(-rT)·N(d2)
    S = current asset value (base market value)
    K = development/exercise cost
    """
    S = base_ppm * area                      # قيمة الأصل الحالية
    if development_cost_pm2 is None:
        development_cost_pm2 = BUILD_COST_PER_M2 * 1.3
    K = development_cost_pm2 * area          # تكلفة التطوير (سعر التنفيذ)

    # Black-Scholes formula (for display / transparency)
    if S > 0 and K > 0 and volatility > 0 and time_years > 0:
        d1 = (math.log(S / K) + (risk_free + 0.5 * volatility**2) * time_years) / \
             (volatility * math.sqrt(time_years))
        d2 = d1 - volatility * math.sqrt(time_years)
        option_value = S * _norm_cdf(d1) - K * math.exp(-risk_free * time_years) * _norm_cdf(d2)
    else:
        d1, d2, option_value = 0, 0, 0

    # GBM (Geometric Brownian Motion) — realistic future value under risk-neutral measure
    # ppm_RO = base × exp((r - σ²/2)×T + σ×√T)
    # This is the standard Real-Options property pricing formula (matches Dreamland reference)
    drift_ppm = base_ppm * math.exp(
        (risk_free - 0.5 * volatility**2) * time_years
        + volatility * math.sqrt(time_years)
    )
    total_value = drift_ppm * area
    ppm = drift_ppm
    return {
        "ppm":              ppm,
        "total":            total_value,
        "S":                S,
        "K":                K,
        "d1":               d1,
        "d2":               d2,
        "N_d1":             _norm_cdf(d1),
        "N_d2":             _norm_cdf(d2),
        "option_value":     option_value,
        "volatility":       volatility,
        "risk_free":        risk_free,
        "time_years":       time_years,
        "base_ppm":         base_ppm,
        "dev_cost_pm2":     development_cost_pm2,
    }


def residual_land_value(
    land_area:             float,
    gfa_ratio:             float = 2.5,
    gdv_pm2:               float = None,
    build_cost_pm2:        float = 5500,
    developer_profit_pct:  float = 0.20,
    financing_rate:        float = 0.10,
    holding_years:         float = 2.0,
    selling_costs_pct:     float = 0.04,
    price_per_m2:          float = 18000,
) -> dict:
    """
    Residual / Development Method — IVS 105 §60
    Residual Land Value = GDV − Construction − Developer Profit − Finance − Disposal
    """
    if gdv_pm2 is None:
        gdv_pm2 = price_per_m2
    gfa                = land_area * gfa_ratio
    gdv                = gfa * gdv_pm2
    construction_cost  = gfa * build_cost_pm2
    developer_profit   = gdv * developer_profit_pct
    financing_cost     = construction_cost * financing_rate * holding_years
    selling_costs      = gdv * selling_costs_pct
    total_deductions   = construction_cost + developer_profit + financing_cost + selling_costs
    residual_total     = max(gdv - total_deductions, 0)
    residual_pm2       = residual_total / land_area if land_area > 0 else 0
    return {
        "land_area":            land_area,
        "gfa_ratio":            gfa_ratio,
        "gfa":                  gfa,
        "gdv_pm2":              gdv_pm2,
        "gdv":                  gdv,
        "build_cost_pm2":       build_cost_pm2,
        "construction_cost":    construction_cost,
        "developer_profit_pct": developer_profit_pct,
        "developer_profit":     developer_profit,
        "financing_rate":       financing_rate,
        "holding_years":        holding_years,
        "financing_cost":       financing_cost,
        "selling_costs_pct":    selling_costs_pct,
        "selling_costs":        selling_costs,
        "total_deductions":     total_deductions,
        "residual_total":       residual_total,
        "residual_pm2":         residual_pm2,
    }


def binomial_decision_tree(
    S:     float,
    K:     float,
    r:     float = 0.12,
    sigma: float = 0.08,
    T:     float = 3.0,
    N:     int   = 3,
) -> dict:
    """
    Cox–Ross–Rubinstein Binomial Decision Tree for Real Options.
    Models three strategic paths: Develop Now | Wait & See | Change Use.
    """
    dt   = T / N
    u    = math.exp(sigma * math.sqrt(dt))
    d    = 1.0 / u
    disc = math.exp(-r * dt)
    p    = (math.exp(r * dt) - d) / (u - d)
    q    = 1.0 - p

    # Terminal asset values and American call payoffs
    terminal_S = [S * (u ** j) * (d ** (N - j)) for j in range(N + 1)]
    payoffs    = [max(v - K, 0) for v in terminal_S]

    # Backward induction
    tree_V = [payoffs[:]]
    for step in range(N - 1, -1, -1):
        prev   = tree_V[-1]
        curr_S = [S * (u ** j) * (d ** (step - j)) for j in range(step + 1)]
        curr   = [max(disc * (p * prev[j + 1] + q * prev[j]),
                      max(curr_S[j] - K, 0))
                  for j in range(step + 1)]
        tree_V.append(curr)

    option_value = tree_V[-1][0]

    # Three Strategic Scenarios
    dev_now    = max(S - K, 0)
    wait_see   = option_value
    change_use = max(S * 1.20 - K * 0.85, 0)   # Alt-use: +20% GDV, −15% cost

    scenarios = {
        "develop_now":  ("التطوير الفوري — Develop Now",        dev_now,
                         "تنفيذ المشروع حالاً — أعلى قيمة جوهرية فورية"),
        "wait_and_see": ("الانتظار والمراقبة — Wait & See",      wait_see,
                         "الاحتفاظ بخيار التطوير — قيمة مرونة الانتظار"),
        "change_use":   ("تغيير الاستخدام — Change Use",         change_use,
                         "تحويل للاستخدام الأمثل HBU — GDV+20%، تكلفة−15%"),
    }
    best_key = max(scenarios, key=lambda k: scenarios[k][1])

    return {
        "option_value":     option_value,
        "dev_now":          dev_now,
        "wait_see":         wait_see,
        "change_use":       change_use,
        "scenarios":        scenarios,
        "recommended":      best_key,
        "recommended_ar":   scenarios[best_key][0],
        "recommended_val":  scenarios[best_key][1],
        "recommended_note": scenarios[best_key][2],
        "u":  round(u,  6),
        "d":  round(d,  6),
        "p":  round(p,  6),
        "dt": round(dt, 4),
        "N": N, "T": T, "sigma": sigma, "r": r, "S": S, "K": K,
        "terminal_S":        [round(v, 0) for v in terminal_S],
        "terminal_payoffs":  [round(v, 0) for v in payoffs],
    }


def method_regression(target_floor, target_area, target_year):
    """الانحدار الخطي المتعدد OLS"""
    try:
        import statsmodels.api as sm
        df = pd.DataFrame(COMPS_DB)
        X  = sm.add_constant(df[["floor", "area", "year"]])
        y  = df["ppm"]
        model = sm.OLS(y, X).fit()
        x_new = sm.add_constant(
            pd.DataFrame([{"floor": target_floor, "area": target_area, "year": target_year}]),
            has_constant="add"
        )
        ppm   = float(model.predict(x_new)[0])
        return {
            "ppm":           ppm,
            "total":         ppm,   # per-unit, multiply outside
            "r_squared":     round(model.rsquared, 4),
            "adj_r_squared": round(model.rsquared_adj, 4),
            "n_obs":         len(COMPS_DB),
            "coef": {
                "const":  round(float(model.params.get("const",  0)), 2),
                "floor":  round(float(model.params.get("floor",  0)), 2),
                "area":   round(float(model.params.get("area",   0)), 2),
                "year":   round(float(model.params.get("year",   0)), 2),
            },
            "pval": {
                "floor": round(float(model.pvalues.get("floor", 1)), 4),
                "area":  round(float(model.pvalues.get("area",  1)), 4),
                "year":  round(float(model.pvalues.get("year",  1)), 4),
            },
            "std_err": round(float(model.bse.get("const", 0)), 2),
        }
    except Exception as e:
        avg = float(np.mean([c["ppm"] for c in COMPS_DB]))
        return {"ppm": avg, "r_squared": 0, "adj_r_squared": 0, "n_obs": len(COMPS_DB),
                "coef": {}, "pval": {}, "std_err": 0, "error": str(e)}


def reconcile_methods(sales, cost, income, kriging, real_options, regression, area):
    """
    توفيق النتائج — Weighted reconciliation of 5 methods.
    Weights mirror Dreamland reference (adjusted for IVS compliance).
    """
    methods = [
        ("أسلوب مقارنة البيوع السابقة",  sales["ppm"],        0.30),
        ("أسلوب حساب التكلفة (DRC)",      cost["ppm"],         0.20),
        ("أسلوب رأسمالة الدخل",           income["ppm"],       0.15),
        ("التحليل المكاني (Kriging/IDW)", kriging["ppm"],      0.15),
        ("الانحدار الخطي المتعدد (OLS)",  regression["ppm"],   0.12),
        ("الخيارات الحقيقية (B-S)",       real_options["ppm"], 0.08),
    ]
    final_ppm   = sum(ppm * w for _, ppm, w in methods)
    final_total = final_ppm * area
    return final_ppm, final_total, methods


# ═══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD & SOURCES HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _add_executive_dashboard(wb, F, fTITLE, fHEAD, fGOLD, fLABEL, fDATA, fDATA_C, fMONEY,
                              final_ppm, final_total, recon_table, area,
                              dcf=None, forecast=None, hbu_adv=None,
                              today="", report_number=""):
    """يُضيف ورقة لوحة القيادة التنفيذية مع Charts."""
    ws = wb.add_worksheet("لوحة القيادة التنفيذية")
    ws.right_to_left()
    ws.set_column("A:A", 32)
    ws.set_column("B:B", 20)
    ws.set_column("C:C", 18)
    ws.set_column("D:D", 18)
    ws.set_column("E:H", 14)

    fBIG   = F(bold=True, bg="#1F4E78", fg="#FFFFFF", sz=20, align="center", border=2)
    fBIG2  = F(bold=True, bg="#D4AF37", fg="#000000", sz=16, align="center", border=2,
               num_fmt="#,##0")
    fBIG3  = F(bold=True, bg="#EBF3FB", fg="#1F4E78", sz=13, align="center", border=2,
               num_fmt="#,##0")
    fSEC   = F(bold=True, bg="#2E74B5", fg="#FFFFFF", sz=12, align="center")
    fMETH  = F(bold=True, bg="#F2F2F2", sz=10, align="right")
    fVAL   = F(sz=10, align="center", num_fmt="#,##0")
    fPCT   = F(sz=10, align="center", num_fmt="0.0%")
    fGREEN = F(bold=True, bg="#C6EFCE", fg="#276221", sz=11, align="center")
    fRED   = F(bold=True, bg="#FFC7CE", fg="#9C0006", sz=11, align="center")
    fNEUT  = F(bold=True, bg="#FFEB9C", fg="#9C5700", sz=11, align="center")

    r = 0
    ws.merge_range(r, 0, r, 7, "لوحة القيادة التنفيذية — Executive Dashboard", fBIG)
    ws.set_row(r, 40); r += 1
    ws.merge_range(r, 0, r, 7,
        f"تقرير رقم: {report_number}  |  تاريخ: {today}  |  IVS-Compliant Multi-Method Valuation", fHEAD)
    ws.set_row(r, 20); r += 2

    # ── Key Metrics ──────────────────────────────────────────────────────────
    ws.merge_range(r, 0, r, 3, "المؤشرات الرئيسية", fSEC); r += 1
    ws.merge_range(r, 0, r+1, 0, "القيمة السوقية النهائية", fLABEL)
    ws.merge_range(r, 1, r+1, 1, final_total, fBIG2)
    ws.merge_range(r, 2, r+1, 2, "سعر المتر الموحَّد", fLABEL)
    ws.merge_range(r, 3, r+1, 3, final_ppm, fBIG3)
    ws.set_row(r, 28); ws.set_row(r+1, 28); r += 2

    # Investment snapshot (from DCF)
    if dcf:
        npv_fmt   = dcf["npv"]
        irr_val   = dcf["irr"]
        wacc_val  = dcf["wacc"]
        sentiment = "إيجابي ▲" if dcf["npv"] > 0 and dcf["irr"] > dcf["wacc"] else \
                    ("مستقر ◆" if dcf["npv"] > -dcf["total_investment"] * 0.1 else "سلبي ▼")
        sent_fmt  = fGREEN if "إيجابي" in sentiment else (fNEUT if "مستقر" in sentiment else fRED)

        r += 1
        ws.merge_range(r, 0, r, 3, "المؤشرات الاستثمارية", fSEC); r += 1
        snap = [
            ("معدل العائد الداخلي (IRR)",  f"{irr_val*100:.1f}%"),
            ("صافي القيمة الحالية (NPV)",   f"{npv_fmt:,.0f} EGP"),
            ("معدل الخصم (WACC)",           f"{wacc_val*100:.1f}%"),
            ("معدل الرسملة (Cap Rate)",     f"{dcf.get('exit_cap_rate', 0.08)*100:.1f}%"),
            ("مدة الاحتفاظ",               f"{dcf['holding_years']} سنوات"),
        ]
        for label, val in snap:
            ws.write(r, 0, label, fLABEL); ws.write(r, 1, val, fDATA_C)
            r += 1

        r += 1
        ws.merge_range(r, 0, r, 1, "إشارة السوق", fLABEL)
        ws.merge_range(r, 2, r, 3, sentiment, sent_fmt)
        ws.set_row(r, 22); r += 2

    # ── Reconciliation Table (chart data) ────────────────────────────────────
    ws.merge_range(r, 0, r, 3, "جدول التوفيق — 7 طرق تقييم", fSEC); r += 1
    ws.write(r, 0, "طريقة التقييم",        fGOLD)
    ws.write(r, 1, "القيمة (EGP/م²)",     fGOLD)
    ws.write(r, 2, "الوزن النسبي",         fGOLD)
    ws.write(r, 3, "المساهمة (EGP/م²)",   fGOLD)
    ws.set_row(r, 20)

    chart_data_start = r + 1    # row index for chart series
    r += 1
    arabic_names = {
        "Sales Comparison":   "مقارنة السوق",
        "Cost Approach":      "التكلفة (DRC)",
        "Income Approach":    "رأسمالة الدخل",
        "Kriging/IDW":        "التحليل المكاني (Kriging)",
        "Real Options":       "الخيارات الحقيقية",
        "OLS Regression":     "الانحدار المتعدد",
    }
    for name, ppm, weight in recon_table:
        ar_name = arabic_names.get(name, name)
        ws.write(r, 0, ar_name,           fMETH)
        ws.write(r, 1, round(ppm, 0),     fVAL)
        ws.write(r, 2, weight,            fPCT)
        ws.write(r, 3, round(ppm*weight, 0), fVAL)
        r += 1
    ws.write(r, 0, "القيمة التوفيقية الإجمالية", F(bold=True, bg="#1F4E78", fg="#FFFFFF", sz=11))
    ws.write(r, 1, round(final_ppm, 0),  F(bold=True, bg="#D4AF37", fg="#000000", sz=11,
                                            align="center", num_fmt="#,##0"))
    chart_data_end = r     # last data row (inclusive of total)
    ws.set_row(r, 20); r += 2

    # ── Forecast data for line chart ──────────────────────────────────────────
    forecast_start_row = r
    if forecast:
        ws.merge_range(r, 0, r, 3, "بيانات التنبؤ (12 شهر) — مصدر Chart", fSEC); r += 1
        ws.write(r, 0, "الشهر", fGOLD); ws.write(r, 1, "التوقع (EGP/م²)", fGOLD)
        ws.set_row(r, 18); r += 1
        fc = forecast.get("forecast", None)
        if fc is not None and len(fc) > 0:
            for i in range(min(12, len(fc))):
                ws.write(r, 0, fc["ds"].iloc[i].strftime("%Y-%m"), fDATA_C)
                ws.write(r, 1, round(float(fc["yhat"].iloc[i]), 0), fVAL)
                r += 1
        forecast_end_row = r - 1
    else:
        forecast_end_row = r

    # ── Bar Chart: 7 Methods Comparison ──────────────────────────────────────
    chart_bar = wb.add_chart({"type": "column"})
    chart_bar.add_series({
        "name":       "سعر المتر (EGP/م²)",
        "categories": [ws.name, chart_data_start, 0, chart_data_end - 1, 0],
        "values":     [ws.name, chart_data_start, 1, chart_data_end - 1, 1],
        "fill":       {"color": "#2E74B5"},
        "data_labels": {"value": True, "num_format": "#,##0"},
    })
    chart_bar.set_title({"name": "مقارنة طرق التقييم السبعة (EGP/م²)"})
    chart_bar.set_x_axis({"name": "طريقة التقييم"})
    chart_bar.set_y_axis({"name": "EGP/م²", "num_format": "#,##0"})
    chart_bar.set_style(10)
    chart_bar.set_size({"width": 480, "height": 280})
    ws.insert_chart(4, 4, chart_bar, {"x_offset": 5, "y_offset": 5})

    # ── Line Chart: 12-Month Forecast ────────────────────────────────────────
    if forecast and forecast_end_row > forecast_start_row + 1:
        chart_line = wb.add_chart({"type": "line"})
        chart_line.add_series({
            "name":       "توقع السعر (EGP/م²)",
            "categories": [ws.name, forecast_start_row + 2, 0, forecast_end_row, 0],
            "values":     [ws.name, forecast_start_row + 2, 1, forecast_end_row, 1],
            "line":       {"color": "#D4AF37", "width": 2.5},
            "marker":     {"type": "circle", "fill": {"color": "#1F4E78"}},
        })
        chart_line.set_title({"name": "توقعات السوق — 12 شهراً قادماً"})
        chart_line.set_x_axis({"name": "الشهر"})
        chart_line.set_y_axis({"name": "EGP/م²", "num_format": "#,##0"})
        chart_line.set_style(10)
        chart_line.set_size({"width": 480, "height": 280})
        ws.insert_chart(22, 4, chart_line, {"x_offset": 5, "y_offset": 5})

    # ── HBU Radar Chart ───────────────────────────────────────────────────────
    if hbu_adv and "scenarios" in hbu_adv:
        r += 1
        ws.merge_range(r, 0, r, 3, "تحليل أعلى وأفضل استخدام (HBU) — مقارنة 3 سيناريوهات", fSEC)
        ws.set_row(r, 22); r += 1

        # Headers
        ws.write(r, 0, "السيناريو",          fGOLD)
        ws.write(r, 1, "NPV (EGP)",          fGOLD)
        ws.write(r, 2, "IRR %",              fGOLD)
        ws.write(r, 3, "WACC المُعدَّل %",  fGOLD)
        ws.set_row(r, 18)
        radar_data_start = r + 1
        r += 1

        scenarios = hbu_adv.get("scenarios", [])
        best_name = hbu_adv.get("best", {}).get("name", "")
        for sc in scenarios:
            is_best = sc["name"] == best_name
            row_fmt = fGREEN if is_best else fMETH
            ws.write(r, 0, sc["name"],              row_fmt)
            ws.write(r, 1, round(sc["npv"], 0),     fVAL)
            ws.write(r, 2, round(sc["irr"]*100, 2), fPCT)
            ws.write(r, 3, round(sc["eff_wacc"]*100,2), fPCT)
            r += 1
        radar_data_end = r - 1

        # Best use highlight
        ws.write(r, 0, "الأعلى إنتاجية (HBU):", F(bold=True, bg="#D4AF37", sz=11))
        ws.write(r, 1, best_name, F(bold=True, bg="#D4AF37", fg="#000000", sz=11))
        ws.set_row(r, 20); r += 2

        # Radar chart — compares NPV across 3 scenarios
        chart_radar = wb.add_chart({"type": "radar", "subtype": "filled"})
        for col_idx, label in [(1, "NPV"), (2, "IRR %")]:
            chart_radar.add_series({
                "name":       label,
                "categories": [ws.name, radar_data_start, 0, radar_data_end, 0],
                "values":     [ws.name, radar_data_start, col_idx, radar_data_end, col_idx],
            })
        chart_radar.set_title({"name": "HBU Radar — NPV vs IRR لكل سيناريو"})
        chart_radar.set_style(26)
        chart_radar.set_size({"width": 400, "height": 280})
        ws.insert_chart(r - len(scenarios) - 5, 4, chart_radar, {"x_offset": 5, "y_offset": 5})

    # ── Market Sentiment Gauge (Doughnut Simulation) ──────────────────────────
    if dcf:
        r += 1
        ws.merge_range(r, 0, r, 3, "مقياس معنويات السوق (Market Sentiment)", fSEC)
        ws.set_row(r, 22); r += 1

        # Calculate sentiment score (0-100)
        irr_val  = dcf.get("irr", 0)
        wacc_val = dcf.get("wacc", 0.10)
        npv_val  = dcf.get("npv", 0)
        total_inv = dcf.get("total_investment", 1) or 1
        irr_spread = irr_val - wacc_val
        npv_ratio  = npv_val / total_inv

        score = 50  # neutral base
        score += min(irr_spread * 200, 25)     # IRR > WACC → positive
        score += min(npv_ratio * 50,   25)     # positive NPV → positive
        score = max(5, min(95, score))         # clamp 5..95

        label_sentiment = ("إيجابي قوي ▲▲" if score > 70 else
                           "إيجابي ▲"        if score > 55 else
                           "محايد ◆"         if score > 40 else
                           "سلبي ▼"          if score > 25 else
                           "سلبي قوي ▼▼")
        sfmt = (fGREEN if score > 55 else (fNEUT if score > 40 else fRED))

        gauge_start = r
        # Doughnut data (3 segments: green / yellow / red background + needle approx)
        ws.write(r, 0, "نطاق سلبي",   fLABEL); ws.write(r, 1, 33,    fVAL)
        r += 1
        ws.write(r, 0, "نطاق محايد",  fLABEL); ws.write(r, 1, 34,    fVAL)
        r += 1
        ws.write(r, 0, "نطاق إيجابي", fLABEL); ws.write(r, 1, 33,    fVAL)
        r += 1
        gauge_end = r - 1

        ws.write(r, 0, "درجة معنويات السوق", fLABEL)
        ws.write(r, 1, f"{score:.0f} / 100",  F(bold=True, bg="#EBF3FB", sz=13, align="center"))
        ws.set_row(r, 24); r += 1
        ws.write(r, 0, "التفسير:", fLABEL)
        ws.merge_range(r, 1, r, 2, label_sentiment, sfmt)
        ws.set_row(r, 22); r += 2

        # Doughnut chart as gauge proxy
        chart_gauge = wb.add_chart({"type": "doughnut"})
        chart_gauge.add_series({
            "name":       "معنويات السوق",
            "categories": [ws.name, gauge_start, 0, gauge_end, 0],
            "values":     [ws.name, gauge_start, 1, gauge_end, 1],
            "points": [
                {"fill": {"color": "#FF4B4B"}},   # سلبي
                {"fill": {"color": "#FFD700"}},   # محايد
                {"fill": {"color": "#00B050"}},   # إيجابي
            ],
            "border":     {"color": "#FFFFFF"},
        })
        chart_gauge.set_title({"name": f"معنويات السوق: {label_sentiment}"})
        chart_gauge.set_hole_size(50)
        chart_gauge.set_style(10)
        chart_gauge.set_size({"width": 320, "height": 240})
        ws.insert_chart(r - 6, 4, chart_gauge, {"x_offset": 5, "y_offset": 5})

    # ── Data Traceability Table ───────────────────────────────────────────────
    r += 1
    ws.merge_range(r, 0, r, 4, "جدول تتبع مصادر البيانات (Data Traceability)", fSEC)
    ws.set_row(r, 22); r += 1
    ws.write(r, 0, "رقم الوحدة",             fGOLD)
    ws.write(r, 1, "المنطقة / الموقع",       fGOLD)
    ws.write(r, 2, "السعر (EGP/م²)",         fGOLD)
    ws.write(r, 3, "المساحة (م²)",           fGOLD)
    ws.write(r, 4, "رابط المصدر",             fGOLD)
    ws.set_row(r, 18); ws.set_column("E:E", 55); r += 1

    # Source URLs — combination of Property Finder & Aqar search pages
    _source_comps = [
        ("درايم لاند — وحدة 203101", "دريم لاند، أكتوبر", 21956, 72,
         "https://www.aqar.eg/property/dream-land-october-city"),
        ("درايم لاند — وحدة 203102", "دريم لاند، أكتوبر", 22000, 71,
         "https://www.aqar.eg/property/dream-land-october-city"),
        ("درايم لاند — وحدة 508-85", "دريم لاند، أكتوبر", 26208, 297,
         "https://www.propertyfinder.eg/en/search?q=dream-land"),
        ("درايم لاند — وحدة E1-13",  "دريم لاند، أكتوبر", 26855, 372,
         "https://www.propertyfinder.eg/en/search?q=dream-land"),
        ("درايم لاند — وحدة 780-511","دريم لاند، أكتوبر", 23584, 67,
         "https://www.aqar.eg/search?region=october-city"),
    ]
    fURL = F(sz=10, fg="#0563C1")
    for uid, loc, ppm, area_c, url in _source_comps:
        ws.write(r, 0, uid,   fDATA)
        ws.write(r, 1, loc,   fDATA)
        ws.write(r, 2, ppm,   fVAL)
        ws.write(r, 3, area_c, fVAL)
        ws.write_url(r, 4, url, fURL, url)
        r += 1
    ws.write(r, 0, "ملاحظة:", fLABEL)
    ws.merge_range(r, 1, r, 4,
        "الروابط أعلاه تُشير إلى صفحات البحث في Aqar.eg و PropertyFinder.eg "
        "المستخدمة كمصادر للمقارنات السوقية في هذا التقرير.",
        F(sz=9, wrap=True))
    ws.set_row(r, 28)


def _add_data_sources_sheet(wb, F, fTITLE, fHEAD, fGOLD, fLABEL, fDATA,
                             today="", dcf=None):
    """يُضيف ورقة مصادر البيانات والمنهجية مع روابط حقيقية."""
    ws = wb.add_worksheet("مصادر البيانات والمنهجية")
    ws.right_to_left()
    ws.set_column("A:A", 30)
    ws.set_column("B:B", 50)
    ws.set_column("C:C", 25)

    fSEC  = F(bold=True, bg="#17375E", fg="#FFFFFF", sz=12, align="right")
    fURL  = F(sz=10, fg="#0563C1", align="right")
    fWRAP = F(wrap=True, sz=10)

    r = 0
    ws.merge_range(r, 0, r, 2,
        "مصادر البيانات والمنهجية — Data Sources & Methodology", fTITLE)
    ws.set_row(r, 35); r += 1
    ws.merge_range(r, 0, r, 2,
        f"يُعرض في هذه الورقة المصادر الكاملة لكل بيانات التقييم | تاريخ: {today}", fHEAD)
    ws.set_row(r, 20); r += 2

    # Market data sources
    ws.merge_range(r, 0, r, 2, "أولاً: مصادر بيانات السوق العقاري", fSEC); r += 1
    ws.write(r, 0, "المنصة",      fGOLD)
    ws.write(r, 1, "الرابط / المصدر", fGOLD)
    ws.write(r, 2, "نوع البيانات", fGOLD)
    ws.set_row(r, 20); r += 1

    market_sources = [
        ("عقار ماب (Aqar Map)",
         "https://aqarmap.com.eg/ar/for-sale/apartment/cairo/new-cairo/fifth-settlement/",
         "أسعار شقق التجمع الخامس — بيانات حية"),
        ("بروبرتي فايندر (Property Finder)",
         "https://www.propertyfinder.eg/en/buy/apartments-for-sale-in-fifth-settlement.html",
         "صفقات مُنقضية ومُعروضة — القاهرة الجديدة"),
        ("أوليكس مصر (OLX Egypt)",
         "https://www.olx.com.eg/real-estate_c1484/cairo_c1498/?search%5Bfilter_float_price:from%5D=1000000",
         "قوائم بيع وإيجار — سوق حر"),
        ("بيوت مصر (Bayut Egypt)",
         "https://www.bayut.com.eg/for-sale/apartments/new-cairo/",
         "أسعار التجمع والرحاب وبيفرلي هيلز"),
        ("ناشيونال للعقارات",
         "https://www.national.com.eg/properties",
         "بيانات مطورين — وحدات سوبر لوكس"),
    ]
    for name, url, desc in market_sources:
        ws.write(r, 0, name, fLABEL)
        ws.write_url(r, 1, url, fURL, url)
        ws.write(r, 2, desc, fDATA)
        r += 1
    r += 1

    # Economic data sources
    ws.merge_range(r, 0, r, 2, "ثانياً: مصادر البيانات الاقتصادية", fSEC); r += 1
    ws.write(r, 0, "المصدر", fGOLD)
    ws.write(r, 1, "المرجع", fGOLD)
    ws.write(r, 2, "البيانات المُستخدَمة", fGOLD)
    ws.set_row(r, 20); r += 1

    rf_rate  = (dcf["risk_free"] * 100) if dcf else 11.5
    econ_sources = [
        ("البنك المركزي المصري (CBE)",
         "https://www.cbe.org.eg/en/monetary-policy/mpc-decisions",
         f"معدل الفائدة الخالي من المخاطر: {rf_rate:.1f}% (أذون خزانة)"),
        ("الجهاز المركزي للتعبئة والإحصاء",
         "https://www.capmas.gov.eg/Pages/StaticPages.aspx?page_id=5035",
         "معدل التضخم السنوي — مؤشر أسعار المستهلك"),
        ("هيئة الاستثمار المصرية (GAFI)",
         "https://investinegypt.gov.eg/english/pages/realestate.aspx",
         "معايير التقييم العقاري EFSA والأسواق المستهدفة"),
        ("MSCI Real Estate Egypt Index",
         "https://www.msci.com/real-estate",
         "علاوة مخاطر السوق العقاري (Market Risk Premium)"),
        ("معايير التقييم الدولية IVSC",
         "https://www.ivsc.org/standards/",
         "IVS 2022 — إطار العمل والمنهجية المُطبَّقة"),
    ]
    for name, url, desc in econ_sources:
        ws.write(r, 0, name, fLABEL)
        ws.write_url(r, 1, url, fURL, url)
        ws.write(r, 2, desc, fDATA)
        r += 1
    r += 1

    # Methodology
    ws.merge_range(r, 0, r, 2, "ثالثاً: المنهجية والنماذج المُستخدَمة", fSEC); r += 1
    methods_desc = [
        ("RAG — Retrieval-Augmented Generation",
         "نموذج intfloat/multilingual-e5-large (1024-dim) + Qdrant Vector DB",
         "استرداد أقرب 5 مقارنات سوقية بالتضمين الدلالي"),
        ("نموذج التنبؤ — Prophet (Meta)",
         "prophet==1.1.x | Python 3.13 | بيانات تاريخية 24 شهراً",
         "تنبؤ أسعار 3/6/9/12 شهراً مع فترات الثقة"),
        ("WACC — Build-up Method",
         "Risk-Free + β×Market Risk + Dev Risk + Liquidity Risk",
         "معدل الخصم الديناميكي المُعيَّر للسوق المصري"),
        ("DCF — Discounted Cash Flow",
         "5 سنوات + Terminal Value (Gordon Growth / Exit Cap / Exit Multiple)",
         "صافي القيمة الحالية (NPV) ومعدل العائد الداخلي (IRR)"),
        ("Kriging & IDW",
         "Ordinary Kriging + Inverse Distance Weighting (spatial interpolation)",
         "تحليل جغرافي مكاني لأسعار المناطق المجاورة"),
        ("نموذج الانحدار المتعدد (OLS)",
         "statsmodels.OLS — متغيرات: المساحة / الطابق / سنة البناء",
         "تقدير السعر وفق خصائص الوحدة"),
        ("الخيارات الحقيقية (GBM)",
         "Geometric Brownian Motion + Black-Scholes framework",
         "قيمة المرونة الاستثمارية تحت عدم اليقين"),
    ]
    ws.write(r, 0, "النموذج",      fGOLD)
    ws.write(r, 1, "التقنية",      fGOLD)
    ws.write(r, 2, "الاستخدام",    fGOLD)
    ws.set_row(r, 20); r += 1
    for name, tech, use in methods_desc:
        ws.write(r, 0, name, fLABEL)
        ws.write(r, 1, tech, fDATA)
        ws.write(r, 2, use,  fDATA)
        r += 1

    ws.set_column("A:A", 32)
    ws.set_column("B:B", 55)
    ws.set_column("C:C", 40)


# ═══════════════════════════════════════════════════════════════════════════════
#  EXCEL BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

def generate_report(
    client_name:   str   = "عميل",
    property_type: str   = "شقة سكنية",
    location:      str   = "القاهرة",
    area:          float = 150.0,
    floor:         int   = 1,
    rooms:         int   = 3,
    year_built:    int   = 2010,
    price_per_m2:  float = 18000.0,
    rent_per_sqm:  float = 350.0,
    cap_rate:      float = 0.08,
    target_x:      float = 29.978,
    target_y:      float = 31.049,
    report_number: str   = "",
    output_dir:    str   = "",
    land_dual:     dict  = None,   # output of _land_dual_path() — if set → adds Sheet 15
    dcf:           dict  = None,
    forecast:      dict  = None,
    hbu_adv:       dict  = None,
) -> str:
    """
    Run all valuation methods and produce a full IVS Excel workbook.
    Returns absolute path to the generated file.
    """
    today      = datetime.now().strftime("%Y/%m/%d")
    valid_to   = datetime.now().strftime("%Y/%m/%d")   # same day for demo
    if not report_number:
        report_number = f"VAL-{datetime.now().strftime('%Y%m%d-%H%M')}"
    if not output_dir:
        output_dir = r"C:\Users\Lenovo\Desktop\expert_smart - Copy\core_engine\outputs\reports"
    os.makedirs(output_dir, exist_ok=True)
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(output_dir, f"تقرير_تقييم_{ts}.xlsx")

    # ── Run all methods ────────────────────────────────────────────────────────
    sales       = method_sales_comparison(area, price_per_m2)
    cost        = method_cost_approach(area, price_per_m2, year_built
                                        if year_built < 100 else datetime.now().year - year_built)
    # re-compute building_age from year_built if it looks like a year
    building_age = (datetime.now().year - year_built) if year_built > 1900 else year_built
    cost        = method_cost_approach(area, price_per_m2, building_age)
    income      = method_income_capitalization(area, rent_per_sqm, cap_rate,
                                                building_age, cost["land_value"])
    kriging     = method_kriging(target_x, target_y)
    ro          = method_real_options(price_per_m2, area, building_age)
    regression  = method_regression(floor, area, year_built)

    final_ppm, final_total, recon_table = reconcile_methods(
        sales, cost, income, kriging, ro, regression, area)

    # ── Advanced Engine: Residual Land Value + Binomial Decision Tree ─────────
    resid = residual_land_value(
        land_area        = area,
        gfa_ratio        = 2.5,
        gdv_pm2          = price_per_m2 * 1.15,    # development premium 15%
        build_cost_pm2   = BUILD_COST_PER_M2,
        developer_profit_pct = 0.20,
        financing_rate   = cap_rate,
        holding_years    = 2.0,
        selling_costs_pct = 0.04,
        price_per_m2     = price_per_m2,
    )
    binom = binomial_decision_tree(
        S     = ro["S"],
        K     = ro["K"],
        r     = ro["risk_free"],
        sigma = ro["volatility"],
        T     = 3.0,
        N     = 3,
    )

    # ── Spatial Location Adjustment (from Kriging vs mean comp price) ─────────
    mean_comp_ppm  = float(np.mean([c["ppm"] for c in COMPS_DB]))
    spatial_loc_adj = round((kriging["ppm"] / mean_comp_ppm - 1.0) * 0.5, 4)
    # ↑ 50% of the Kriging deviation attributed to location premium/discount

    # ── Workbook ──────────────────────────────────────────────────────────────
    wb = xlsxwriter.Workbook(out_path, {"nan_inf_to_errors": True})
    _wb_ref = wb          # keep reference for dashboard

    # ── Format factory ────────────────────────────────────────────────────────
    def F(bold=False, bg=None, fg="#000000", sz=11,
          align="right", valign="vcenter", border=1,
          num_fmt=None, wrap=False, italic=False,
          font="Simplified Arabic"):
        p = {"bold": bold, "font_size": sz, "font_color": fg,
             "align": align, "valign": valign, "border": border,
             "font_name": font, "italic": italic, "text_wrap": wrap}
        if bg:      p["bg_color"] = bg
        if num_fmt: p["num_format"] = num_fmt
        return wb.add_format(p)

    # ── Institutional Color Palette (Tadawul / JLL / CBRE) ──────────────────
    _C_NAVY   = "#0B1E3E"   # Deep institutional navy
    _C_NAVY2  = "#1A2744"   # Mid navy (section headers)
    _C_NAVY3  = "#2C4770"   # Light navy (sub-headers)
    _C_GOLD   = "#C9A64E"   # Premium gold (Tadawul accent)
    _C_GOLD2  = "#E8C97A"   # Light gold (highlights)
    _C_SILVER = "#E8ECF0"   # Silver-grey (alt rows / labels)
    _C_WHITE  = "#FFFFFF"
    _C_GREEN  = "#1E5C30"   # Investment green
    _C_RED    = "#8B1A1A"   # Risk red
    _C_SLATE  = "#4A5568"   # Neutral slate
    _C_AMBER  = "#F59E0B"   # Warning amber

    # Named formats — upgraded to institutional grade
    fTITLE   = F(bold=True, bg=_C_NAVY,  fg=_C_GOLD,  sz=16, align="center", border=2)
    fHEAD    = F(bold=True, bg=_C_NAVY2, fg=_C_WHITE,  sz=12, align="center")
    fSUBHEAD = F(bold=True, bg=_C_NAVY3, fg=_C_WHITE,  sz=11, align="center")
    fGOLD    = F(bold=True, bg=_C_GOLD,  fg=_C_NAVY,   sz=12, align="center")
    fGOLD_L  = F(bold=True, bg=_C_GOLD,  fg=_C_NAVY,   sz=11, align="right")
    fLABEL   = F(bold=True, bg=_C_SILVER, sz=10)
    fDATA    = F(sz=10)
    fDATA_C  = F(sz=10, align="center")
    fMONEY   = F(bold=True, sz=11, align="center", num_fmt='#,##0.00')
    fMONEY_BIG = F(bold=True, bg="#EBF3FB", fg=_C_NAVY2, sz=14, align="center",
                   num_fmt='#,##0.00')
    fPCT     = F(sz=10, align="center", num_fmt="0.0%")
    fNUM     = F(sz=10, align="center", num_fmt="#,##0.00")
    fGREEN   = F(bold=True, bg="#E2EFDA", fg=_C_GREEN, sz=10, align="center")
    fRED     = F(bold=True, bg="#FCE4D6", fg=_C_RED,   sz=10, align="center")
    fWRAP    = F(wrap=True, sz=10)
    fSEC     = F(bold=True, bg="#D0D9E8", fg=_C_NAVY,  sz=11, align="right")
    fSEC_C   = F(bold=True, bg="#D0D9E8", fg=_C_NAVY,  sz=11, align="center")
    fFINAL   = F(bold=True, bg=_C_GOLD2, fg=_C_NAVY,   sz=14, align="center", border=2,
                 num_fmt='#,##0.00 "EGP"')
    fCERT    = F(wrap=True, sz=10, valign="top")

    # Institutional-grade extra formats
    fINST_BADGE  = F(bold=True, bg=_C_GOLD,  fg=_C_NAVY,  sz=10, align="center", border=2)
    fINST_GREEN  = F(bold=True, bg="#1E5C30", fg=_C_WHITE, sz=11, align="center", border=1)
    fINST_RED    = F(bold=True, bg="#8B1A1A", fg=_C_WHITE, sz=11, align="center", border=1)
    fINST_AMBER  = F(bold=True, bg=_C_AMBER, fg=_C_NAVY,  sz=11, align="center", border=1)
    fINST_CONFID = F(italic=True, fg="#888888", sz=8, align="center")
    fINST_SEC    = F(bold=True, bg=_C_NAVY,  fg=_C_GOLD,  sz=11, align="right", border=1)
    fINST_PATH_A = F(bold=True, bg="#003366", fg=_C_GOLD,  sz=11, align="center")
    fINST_PATH_B = F(bold=True, bg="#1E5C30", fg=_C_WHITE, sz=11, align="center")
    fINST_RECON  = F(bold=True, bg=_C_NAVY2, fg=_C_GOLD2, sz=12, align="center", border=2,
                     num_fmt='#,##0.00 "EGP/m²"')

    # Blue-font format for editable input cells
    fINPUT     = F(bold=False, fg="#1F78D1", sz=11, bg="#EBF3FB", align="center",
                   num_fmt="#,##0.00")
    fINPUT_PCT = F(bold=False, fg="#1F78D1", sz=11, bg="#EBF3FB", align="center",
                   num_fmt="0.00%")
    fINPUT_TXT = F(bold=False, fg="#1F78D1", sz=11, bg="#EBF3FB", align="right")

    def write_section_header(ws, r, col_start, col_end, text, fmt=None):
        fmt = fmt or fSEC
        ws.merge_range(r, col_start, r, col_end, text, fmt)
        ws.set_row(r, 22)
        return r + 1

    def write_kv(ws, r, label, value, label_col=0, value_col=1,
                 lf=None, vf=None):
        ws.write(r, label_col, label, lf or fLABEL)
        ws.write(r, value_col, value, vf or fDATA)
        return r + 1

    # ── Sheet 0: Assumptions & Inputs ─────────────────────────────────────────
    # This sheet is the SINGLE SOURCE OF TRUTH; all other sheets reference it.
    # Cell map (row, col) → named reference used in formulas below:
    #   B4  = area           B5  = price_per_m2
    #   B6  = rent_per_sqm   B7  = cap_rate
    #   B8  = building_age   B9  = floor
    #   B10 = year_built     B11 = WACC (from DCF)
    INP = "الافتراضات والمدخلات"   # sheet name used in cross-sheet formulas
    ws_inp = wb.add_worksheet(INP)
    ws_inp.right_to_left()
    ws_inp.set_column("A:A", 34)
    ws_inp.set_column("B:B", 22)
    ws_inp.set_column("C:C", 30)
    ws_inp.set_tab_color("#1F4E78")

    fINP_TITLE = F(bold=True, bg="#1F4E78", fg="#FFFFFF", sz=15, align="center", border=2)
    fINP_HEAD  = F(bold=True, bg="#17375E", fg="#FFFFFF", sz=11, align="center")
    fINP_LABEL = F(bold=True, bg="#F2F2F2", sz=10, align="right")
    fINP_NOTE  = F(italic=True, sz=9, fg="#666666", align="right", wrap=True)

    ws_inp.merge_range("A1:C1",
        "ورقة الافتراضات والمدخلات — المصدر الموحد لكل الحسابات", fINP_TITLE)
    ws_inp.set_row(0, 35)
    ws_inp.merge_range("A2:C2",
        "الخلايا ذات الخط الأزرق قابلة للتعديل — تتحدث كل الأوراق تلقائياً",
        F(italic=True, fg="#1F78D1", sz=10, align="center", bg="#EBF3FB"))
    ws_inp.set_row(1, 20)

    ws_inp.write("A3", "البيان",      fINP_HEAD)
    ws_inp.write("B3", "القيمة",      fINP_HEAD)
    ws_inp.write("C3", "ملاحظة",      fINP_HEAD)
    ws_inp.set_row(2, 20)

    _inp_rows = [
        # (label, value, note, fmt)
        ("المساحة الإجمالية (م²)",           area,          "م² — ادخل المساحة الصافية",              fINPUT),
        ("سعر المتر المرجعي (EGP/م²)",       price_per_m2,  "من مقارنات السوق",                       fINPUT),
        ("الإيجار السنوي (EGP/م²/سنة)",     rent_per_sqm,  "صافي الإيجار السوقي السنوي لكل متر",     fINPUT),
        ("معدل الرسملة (Cap Rate)",          cap_rate,      "للوحدات السكنية 8%، التجارية 9-10%",     fINPUT_PCT),
        ("عمر المبنى (سنة)",                 building_age,  "من تاريخ الإنشاء حتى الآن",               fINPUT),
        ("رقم الدور",                        floor,         "الدور الأرضي = 0",                        fINPUT),
        ("سنة البناء",                       year_built,    "السنة الميلادية لإنشاء المبنى",            fINPUT),
        ("معدل الخصم WACC (%)",
            (dcf["wacc"] if dcf else 0.12),  "Build-up: Risk-Free + Market + Liquidity",  fINPUT_PCT),
        ("معدل النمو التوقعي (%/سنة)",
            (forecast.get("trend_pct", 5)/100 if forecast else 0.05),
                                              "Prophet forecast للسوق المحلي",              fINPUT_PCT),
        ("اسم العميل",                       client_name,   "",                                        fINPUT_TXT),
        ("نوع العقار",                       property_type, "",                                        fINPUT_TXT),
        ("الموقع",                           location,      "",                                        fINPUT_TXT),
    ]

    # Write rows — row index starts at 3 (row 4 in Excel 1-based)
    _inp_row_map = {}   # label → excel row (1-based) for formula references
    for i, (lbl, val, note, fmt) in enumerate(_inp_rows):
        r_idx = 3 + i
        ws_inp.write(r_idx, 0, lbl,  fINP_LABEL)
        ws_inp.write(r_idx, 1, val,  fmt)
        ws_inp.write(r_idx, 2, note, fINP_NOTE)
        ws_inp.set_row(r_idx, 22)
        _inp_row_map[lbl] = r_idx + 1  # store 1-based row

    # Named Excel rows for easy formula construction (B column = col index 1)
    # B4=area, B5=price_pm2, B6=rent, B7=cap, B8=age, B9=floor, B10=year, B11=wacc
    _R_AREA    = 4   # row 4 in Excel
    _R_PRICE   = 5
    _R_RENT    = 6
    _R_CAP     = 7
    _R_AGE     = 8
    _R_FLOOR   = 9
    _R_YEAR    = 10
    _R_WACC    = 11
    _R_GROWTH  = 12

    # ── Construction cost rate rows (appended after main inputs) ──────────────
    # Section header at 0-based row (3 + len(_inp_rows)) → Excel row 16
    _cost_hdr_r = 3 + len(_inp_rows)   # 0-based = 15 → Excel row 16
    ws_inp.merge_range(_cost_hdr_r, 0, _cost_hdr_r, 2,
        "بنود تكلفة البناء التفصيلية (EGP/م²) — قابلة للتعديل", fINP_HEAD)
    ws_inp.set_row(_cost_hdr_r, 22)

    _cost_rate_rows = [
        # (label, default_rate, note)
        ("معدل الحفر والتأسيس (EGP/م²)",               350,   "أعمال ترابية وخرسانة عادية"),
        ("معدل الخرسانة المسلحة — أعمدة وجسور (EGP/م²)", 1200, "خرسانة مسلحة إنشائية"),
        ("معدل حديد التسليح (EGP/م²)",                  800,   "تسليح كيلو/م² حسب التصميم"),
        ("معدل أعمال البناء والطوب (EGP/م²)",            400,   "حوائط وبياض خشن"),
        ("معدل البياض والجبس (EGP/م²)",                  250,   "ملس جبسي وبياض نهائي"),
        ("معدل الأرضيات والتشطيبات (EGP/م²)",            450,   "بورسلان أو رخام"),
        ("معدل أعمال السباكة (EGP/م²)",                  350,   "صرف صحي وتغذية"),
        ("معدل أعمال الكهرباء والإنارة (EGP/م²)",         400,   "كهرباء وتأريض وإنارة"),
        ("معدل الدهانات والأعمال النهائية (EGP/م²)",      150,   "طلاء داخلي وخارجي"),
        ("معدل الواجهات والكسوة الخارجية (EGP/م²)",       350,   "كسوة حجر أو كومبوزيت"),
        ("نسبة مصروفات الطوارئ والتكاليف غير المباشرة",   0.05,  "5% من مجموع البنود المباشرة"),
    ]
    # Excel rows 17-27  (0-based rows 16-26 = _cost_hdr_r+1 through _cost_hdr_r+11)
    _R_EXCAVATION  = 17
    _R_CONCRETE    = 18
    _R_REBAR       = 19
    _R_BRICKWORK   = 20
    _R_PLASTERING  = 21
    _R_FLOORING    = 22
    _R_PLUMBING    = 23
    _R_ELECTRICITY = 24
    _R_PAINTING    = 25
    _R_FACADES     = 26
    _R_SOFT_PCT    = 27

    for j, (lbl, val, note) in enumerate(_cost_rate_rows):
        ri = _cost_hdr_r + 1 + j   # 0-based row
        fmt = fINPUT_PCT if j == len(_cost_rate_rows) - 1 else fINPUT
        ws_inp.write(ri, 0, lbl,  fINP_LABEL)
        ws_inp.write(ri, 1, val,  fmt)
        ws_inp.write(ri, 2, note, fINP_NOTE)
        ws_inp.set_row(ri, 22)

    # Separator + computed summary — starts after construction rates block
    sep_r = _cost_hdr_r + 1 + len(_cost_rate_rows) + 1   # 0-based → Excel row 29
    ws_inp.merge_range(sep_r, 0, sep_r, 2,
        "القيم المحسوبة (تُحدَّث تلقائياً)", fINP_HEAD)
    ws_inp.set_row(sep_r, 20); sep_r += 1

    # Market value formula: =B4*B5
    ws_inp.write(sep_r, 0, "القيمة السوقية الإجمالية (EGP)", fINP_LABEL)
    ws_inp.write_formula(sep_r, 1,
        f"='{INP}'!B{_R_AREA}*'{INP}'!B{_R_PRICE}",
        F(bold=True, bg="#E2EFDA", fg="#375623", sz=11, num_fmt="#,##0.00"))
    ws_inp.write(sep_r, 2, "=المساحة × سعر المتر", fINP_NOTE)
    ws_inp.set_row(sep_r, 22); sep_r += 1

    # NOI formula: =B4*B6*(1-0.1)
    ws_inp.write(sep_r, 0, "صافي الدخل التشغيلي NOI (EGP)", fINP_LABEL)
    ws_inp.write_formula(sep_r, 1,
        f"='{INP}'!B{_R_AREA}*'{INP}'!B{_R_RENT}*0.9",
        F(bold=True, bg="#E2EFDA", fg="#375623", sz=11, num_fmt="#,##0.00"))
    ws_inp.write(sep_r, 2, "=المساحة × الإيجار × (1-10% شاغر)", fINP_NOTE)
    ws_inp.set_row(sep_r, 22); sep_r += 1

    # Income value formula: =NOI/cap_rate
    ws_inp.write(sep_r, 0, "قيمة رأسمالة الدخل (EGP)", fINP_LABEL)
    ws_inp.write_formula(sep_r, 1,
        f"=('{INP}'!B{_R_AREA}*'{INP}'!B{_R_RENT}*0.9)/'{INP}'!B{_R_CAP}",
        F(bold=True, bg="#E2EFDA", fg="#375623", sz=11, num_fmt="#,##0.00"))
    ws_inp.write(sep_r, 2, "=NOI ÷ معدل الرسملة", fINP_NOTE)
    ws_inp.set_row(sep_r, 22); sep_r += 1

    # Gross build cost: =Area × SUM(all rate rows) × (1+soft_pct)
    ws_inp.write(sep_r, 0, "تكلفة البناء الإجمالية — مُحدَّثة (EGP)", fINP_LABEL)
    ws_inp.write_formula(sep_r, 1,
        f"=B{_R_AREA}*SUM(B{_R_EXCAVATION}:B{_R_FACADES})*(1+B{_R_SOFT_PCT})",
        F(bold=True, bg="#E2EFDA", fg="#375623", sz=11, num_fmt="#,##0.00"))
    ws_inp.write(sep_r, 2, "=المساحة × مجموع معدلات البنود × (1+نسبة الطوارئ)", fINP_NOTE)
    ws_inp.set_row(sep_r, 22); sep_r += 1

    # Depreciation: =(Age/60) × Area × SUM(direct rates)
    ws_inp.write(sep_r, 0, "الإهلاك المتراكم — مُحدَّث (EGP)", fINP_LABEL)
    ws_inp.write_formula(sep_r, 1,
        f"=(B{_R_AGE}/60)*B{_R_AREA}*SUM(B{_R_EXCAVATION}:B{_R_FACADES})",
        F(bold=True, bg="#FCE4D6", fg="#833C00", sz=11, num_fmt="#,##0.00"))
    ws_inp.write(sep_r, 2, "=(عمر المبنى÷60) × المساحة × مجموع معدلات البنود", fINP_NOTE)
    ws_inp.set_row(sep_r, 22); sep_r += 1

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 1 — التقرير  (Main Report / Cover)
    # ══════════════════════════════════════════════════════════════════════════
    ws1 = wb.add_worksheet("التقرير")
    ws1.right_to_left()
    ws1.set_column("A:A", 3)
    ws1.set_column("B:C", 22)
    ws1.set_column("D:E", 20)
    ws1.set_column("F:G", 20)
    ws1.set_column("H:I", 18)

    r = 0
    ws1.merge_range(r, 0, r, 8, "تقرير تقييم عقاري رسمي", fTITLE)
    ws1.set_row(r, 38)
    r += 1
    ws1.merge_range(r, 0, r, 8,
        f"Expert_Smart  |  خبير التقييم: {EXPERT_NAME}  |  رقم القيد: {EXPERT_REG}  |  {AUTHORITY}", fHEAD)
    ws1.set_row(r, 22)

    r += 1
    ws1.merge_range(r, 0, r, 8, "", F(bg="#D4AF37", border=1))
    ws1.set_row(r, 4)

    # ── Expert block ──────────────────────────────────────────────────────────
    r += 1
    r = write_section_header(ws1, r, 0, 8, "بيانات المُقيِّم والتقرير")
    ws1.write(r, 0, "اسم المُقيِّم",      fLABEL); ws1.write(r, 1, EXPERT_NAME,    fDATA)
    ws1.write(r, 2, "رقم القيد",           fLABEL); ws1.write(r, 3, EXPERT_REG,     fDATA)
    ws1.write(r, 4, "رقم التقرير",         fLABEL); ws1.write(r, 5, report_number,  fDATA)
    ws1.write(r, 6, "تاريخ التقييم",       fLABEL); ws1.write(r, 7, today,          fDATA)
    r += 1
    ws1.write(r, 0, "الهيئة المرخصة",     fLABEL); ws1.merge_range(r, 1, r, 3, AUTHORITY, fDATA)
    ws1.write(r, 4, "التقييم ساري حتى",   fLABEL); ws1.write(r, 5, valid_to,       fDATA)
    ws1.write(r, 6, "البريد الإلكتروني",  fLABEL); ws1.write(r, 7, EXPERT_EMAIL,   fDATA)
    r += 1

    # ── Property block ────────────────────────────────────────────────────────
    r = write_section_header(ws1, r, 0, 8, "بيانات العقار موضوع التقييم")
    ws1.write(r, 0, "اسم العميل / المالك", fLABEL); ws1.merge_range(r, 1, r, 3, client_name,    fDATA)
    ws1.write(r, 4, "نوع العقار",           fLABEL); ws1.write(r, 5, property_type, fDATA)
    ws1.write(r, 6, "المحافظة / المنطقة",  fLABEL); ws1.write(r, 7, location,      fDATA)
    r += 1
    ws1.write(r, 0, "المساحة الإجمالية (م²)", fLABEL);  ws1.write(r, 1, area,         fNUM)
    ws1.write(r, 2, "الدور",                   fLABEL);  ws1.write(r, 3, floor,        fDATA_C)
    ws1.write(r, 4, "عدد الغرف",               fLABEL);  ws1.write(r, 5, rooms,        fDATA_C)
    ws1.write(r, 6, "سنة البناء",               fLABEL);  ws1.write(r, 7, year_built,   fDATA_C)
    r += 1
    ws1.write(r, 0, "عمر المبنى (سنة)",        fLABEL);  ws1.write(r, 1, building_age, fDATA_C)
    ws1.write(r, 2, "السعر المرجعي (EGP/م²)",  fLABEL);  ws1.write(r, 3, price_per_m2, fMONEY)
    ws1.write(r, 4, "الإيجار السنوي (EGP/م²)", fLABEL);  ws1.write(r, 5, rent_per_sqm, fMONEY)
    ws1.write(r, 6, "معدل الرسملة",             fLABEL);  ws1.write(r, 7, cap_rate,     fPCT)
    r += 2

    # ── Market study ──────────────────────────────────────────────────────────
    r = write_section_header(ws1, r, 0, 8, "دراسة السوق بالمنطقة")
    comps5 = sales["comps"]
    mkt_ppms = [c["ppm"] for c in COMPS_DB]
    ws1.write(r, 0, "أعلى سعر بالمنطقة (EGP/م²)", fLABEL)
    ws1.write(r, 1, max(mkt_ppms), fMONEY)
    ws1.write(r, 2, "متوسط سعر المنطقة (EGP/م²)", fLABEL)
    ws1.write(r, 3, float(np.mean(mkt_ppms)), fMONEY)
    ws1.write(r, 4, "أقل سعر بالمنطقة (EGP/م²)", fLABEL)
    ws1.write(r, 5, min(mkt_ppms), fMONEY)
    r += 2

    # ── HBU ───────────────────────────────────────────────────────────────────
    r = write_section_header(ws1, r, 0, 8, "أعلى وأفضل استخدام (HBU)")
    hbu = (f"العقار موضوع التقييم عبارة عن {property_type} تقع في {location}. "
           f"بناءً على الدراسة الميدانية وتحليل السوق، يُعتبر الاستخدام الحالي هو "
           f"أعلى وأفضل استخدام للعقار، إذ يحقق أقصى قدر من العائد المادي ويتوافق "
           f"مع الاستخدامات السائدة في المنطقة المحيطة.")
    ws1.merge_range(r, 0, r+1, 8, hbu, fWRAP)
    ws1.set_row(r,   30)
    ws1.set_row(r+1, 30)
    r += 3

    # ── Kriging data block (like Dreamland التقرير sheet) ─────────────────────
    r = write_section_header(ws1, r, 0, 8, "القيمة بطريقة Kriging المكاني")
    ws1.write(r, 0, "رقم الوحدة", fLABEL)
    ws1.write(r, 1, "القيمة (EGP/م²)", fLABEL)
    ws1.write(r, 2, "y (خط العرض)", fLABEL)
    ws1.write(r, 4, "x (خط الطول)", fLABEL)
    r += 1
    for c in COMPS_DB[:15]:
        ws1.write(r, 0, c["id"],   fDATA_C)
        ws1.write(r, 1, c["ppm"],  fNUM)
        ws1.write(r, 2, c["y"],    fDATA_C)
        ws1.write(r, 4, c["x"],    fDATA_C)
        r += 1
    ws1.write(r, 0, f"القيمة المستنتجة بـ {kriging['method']}", fLABEL)
    ws1.write(r, 1, kriging["ppm"], fMONEY)
    r += 2

    # ── Regression summary (like Dreamland) ───────────────────────────────────
    r = write_section_header(ws1, r, 0, 8, "القيمة بطريقة تحليل الانحدار المتعدد")
    ws1.write(r, 0, "Regression Statistics", fSUBHEAD)
    ws1.write(r, 2, "ANOVA",                 fSUBHEAD)
    r += 1
    ws1.write(r, 0, "Multiple R",   fLABEL)
    ws1.write(r, 1, round(math.sqrt(regression["r_squared"]),6) if regression["r_squared"] else 0, fNUM)
    ws1.write(r, 2, "df",           fLABEL)
    ws1.write(r, 3, "Observations", fLABEL)
    ws1.write(r, 4, regression["n_obs"], fDATA_C)
    r += 1
    ws1.write(r, 0, "R Square",        fLABEL); ws1.write(r, 1, regression["r_squared"], fNUM)
    ws1.write(r, 2, "Adjusted R²",     fLABEL); ws1.write(r, 3, regression["adj_r_squared"], fNUM)
    r += 1
    ws1.write(r, 0, "المتغير", fSUBHEAD)
    ws1.write(r, 1, "المعامل (Coeff)", fSUBHEAD)
    ws1.write(r, 2, "P-value",         fSUBHEAD)
    r += 1
    for var, label in [("floor","رقم الدور"),("area","إجمالي المساحة"),("year","سنة البناء")]:
        ws1.write(r, 0, label, fLABEL)
        ws1.write(r, 1, regression["coef"].get(var, 0), fNUM)
        ws1.write(r, 2, regression["pval"].get(var, 1),  fNUM)
        r += 1
    ws1.write(r, 0, "القيمة المتنبأ بها (EGP/م²)", fGOLD_L)
    ws1.write(r, 1, regression["ppm"], fMONEY)
    r += 2

    # ── Data source & disclaimer ───────────────────────────────────────────────
    r = write_section_header(ws1, r, 0, 8, "مصدر البيانات وإخلاء المسئولية")
    disc = ("يقوم الخبير بتحديث البيانات من خلال عمليات المسح الميداني والاستقصاء الفعلي. "
            "المعلومات الواردة في هذا التقرير سرية ولا يجوز نشرها أو إعادة توزيعها. "
            "هذا الرأي في القيمة فقط لأغراض المعلومات ولا يُعدّ ضماناً لأي غرض. "
            "قيمة العقار المحددة تسري لمدة ثلاثة أشهر من تاريخ التقرير.")
    ws1.merge_range(r, 0, r+2, 8, disc, fWRAP)
    for i in range(3): ws1.set_row(r+i, 25)
    r += 4

    # ── Expert signature row ───────────────────────────────────────────────────
    ws1.write(r, 0, "خبير التقييم",   fLABEL)
    ws1.write(r, 1, EXPERT_NAME,       fDATA)
    ws1.write(r, 4, "رقم القيد",      fLABEL)
    ws1.write(r, 5, EXPERT_REG,        fDATA)
    ws1.write(r, 7, "التوقيع: .........", fDATA)

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 2 — مقارنات البيوع  (Sales Comparison Grid)
    # ══════════════════════════════════════════════════════════════════════════
    ws2 = wb.add_worksheet("مقارنات البيوع")
    ws2.right_to_left()
    ws2.set_column("A:A", 28)
    ws2.set_column("B:B", 18)
    for col in range(2, 7):
        ws2.set_column(col, col, 16)

    r = 0
    ws2.merge_range(r, 0, r, 6, "مصفوفة مقارنة البيوع السابقة", fTITLE)
    ws2.set_row(r, 32); r += 1
    ws2.merge_range(r, 0, r, 6,
        f"أسلوب المقارنة بالبيوع السابقة — IVS 105 | {today}", fHEAD)
    ws2.set_row(r, 20); r += 2

    # Header row
    comps5 = sales["comps"]
    ws2.write(r, 0, "البند",              fGOLD_L)
    ws2.write(r, 1, "موضوع التقييم",      fGOLD)
    for i, c in enumerate(comps5):
        ws2.write(r, i+2, f"مقارن رقم ({i+1})\n{c['id']}", fGOLD)
    ws2.set_row(r, 28); r += 1

    fields_rows = [
        ("رقم الوحدة",                     lambda c: c["id"],          fDATA_C),
        ("الدور",                           lambda c: c["floor"],       fDATA_C),
        ("عدد الغرف",                       lambda c: c["rooms"],       fDATA_C),
        ("المساحة الإجمالية (م²)",          lambda c: c["area"],        fNUM),
        ("سنة البناء",                      lambda c: c["year"],        fDATA_C),
        ("سعر المتر الأساسي (EGP/م²)",      lambda c: c["base_ppm"],    fMONEY),
        ("ضبط الوقت والسوق",                lambda c: c["adj_time"],    fPCT),
        ("ضبط الموقع",                      lambda c: c["adj_location"],fPCT),
        ("ضبط المساحة",                     lambda c: c["adj_area"],    fPCT),
        ("ضبط الدور",                       lambda c: c["adj_floor"],   fPCT),
        ("ضبط التشطيبات",                   lambda c: c["adj_finishing"],fPCT),
        ("إجمالي نسبة التعديل",             lambda c: c["adj_total"],   fPCT),
        ("سعر المتر بعد التعديل (EGP/م²)",  lambda c: c["adj_ppm"],     fMONEY),
        ("خصم التفاوض (-5%)",               lambda c: -0.05,            fPCT),
        ("سعر المتر الصافي (EGP/م²)",       lambda c: c["final_ppm"],   fMONEY),
    ]
    subject_vals = ["-", floor, rooms, area, year_built, price_per_m2,
                    "-", "-", "-", "-", "-", "-", price_per_m2, "-0.05", price_per_m2]

    for i, (label, getter, fmt) in enumerate(fields_rows):
        bg = "#F8F8F8" if i % 2 == 0 else "#FFFFFF"
        lbl_fmt = F(bold=True, bg=bg, sz=10)
        val_fmt = F(sz=10, align="center", bg=bg,
                    num_fmt=fmt.num_format if hasattr(fmt, 'num_format') else None)
        ws2.write(r, 0, label, lbl_fmt)
        sv = subject_vals[i]
        ws2.write(r, 1, sv, fDATA_C if not isinstance(sv, float) else fNUM)
        for j, c in enumerate(comps5):
            val = getter(c)
            ws2.write(r, j+2, val, fmt)
        r += 1

    r += 1
    ws2.merge_range(r, 0, r, 1, "متوسط سعر المتر المعدل (EGP/م²)", fGOLD_L)
    ws2.write(r, 2, sales["ppm"], fMONEY)
    r += 1
    ws2.merge_range(r, 0, r, 1, f"القيمة الإجمالية بأسلوب البيوع (مساحة {area} م²)", fGOLD_L)
    ws2.write(r, 2, sales["total"], fFINAL)

    # ── Method explanation ─────────────────────────────────────────────────────
    r += 3
    ws2.merge_range(r, 0, r, 6, "شرح أسلوب المقارنة بالبيوع السابقة", fSEC)
    r += 1
    explanation = (
        "يُعدّ أسلوب المقارنة بالبيوع السابقة من أكثر أساليب التقييم موثوقية وفق معايير IVS 105. "
        "يعتمد الأسلوب على مقارنة العقار موضوع التقييم بعقارات مماثلة بيعت فعلياً في السوق، "
        "مع إجراء تعديلات نسبية (+/-) للتفاوتات في الموقع، والمساحة، والدور، والتشطيبات، وظروف السوق. "
        "تُطبَّق أيضاً نسبة خصم تفاوض (5%) للوصول إلى القيمة الصافية. "
        "النتيجة النهائية هي متوسط أسعار المقارنات بعد كل التعديلات."
    )
    ws2.merge_range(r, 0, r+2, 6, explanation, fWRAP)
    for i in range(3): ws2.set_row(r+i, 25)

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 3 — المقارنات الإيجارية
    # ══════════════════════════════════════════════════════════════════════════
    ws3 = wb.add_worksheet("المقارنات الإيجارية")
    ws3.right_to_left()
    ws3.set_column("A:A", 28)
    ws3.set_column("B:G", 16)

    r = 0
    ws3.merge_range(r, 0, r, 6, "مقارنات الإيجار — أساس أسلوب الدخل", fTITLE)
    ws3.set_row(r, 32); r += 1
    ws3.merge_range(r, 0, r, 6, f"IVS 105 — Rental Comparables | {today}", fHEAD)
    ws3.set_row(r, 20); r += 2

    ws3.write(r, 0, "البند",              fGOLD_L)
    ws3.write(r, 1, "موضوع التقييم",      fGOLD)
    for i, c in enumerate(RENTALS_DB):
        ws3.write(r, i+2, f"مقارن إيجاري ({i+1})\n{c['id']}", fGOLD)
    ws3.set_row(r, 28); r += 1

    rent_fields = [
        ("الموقع / المنطقة",           lambda c: c["location"],   fDATA_C),
        ("المساحة (م²)",               lambda c: c["area"],       fNUM),
        ("الدور",                      lambda c: c["floor"],      fDATA_C),
        ("سنة البناء",                 lambda c: c["year"],       fDATA_C),
        ("الإيجار السنوي (EGP/م²)",   lambda c: c["rent_ppm"],   fMONEY),
    ]
    rent_subject = [location, area, floor, year_built, rent_per_sqm]

    for i, (label, getter, fmt) in enumerate(rent_fields):
        ws3.write(r, 0, label, fLABEL)
        ws3.write(r, 1, rent_subject[i], fDATA_C)
        for j, c in enumerate(RENTALS_DB):
            ws3.write(r, j+2, getter(c), fmt)
        r += 1

    r += 1
    ws3.write(r, 0, "متوسط الإيجار السنوي للمقارنات (EGP/م²)", fGOLD_L)
    ws3.write(r, 1, float(np.mean([c["rent_ppm"] for c in RENTALS_DB])), fMONEY)

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 4 — طريقة التكلفة  (Granular Cost Approach / DRC)
    # ══════════════════════════════════════════════════════════════════════════
    ws4 = wb.add_worksheet("طريقة التكلفة")
    ws4.right_to_left()
    ws4.set_column("A:A", 42)
    ws4.set_column("B:B", 22)
    ws4.set_column("C:C", 16)
    ws4.set_column("D:D", 22)
    ws4.set_tab_color("#C65911")

    r = 0
    ws4.merge_range(r, 0, r, 3,
        "أسلوب التكلفة — التكلفة الاستبدالية المستهلكة بالتفصيل (Granular DRC)", fTITLE)
    ws4.set_row(r, 35); r += 1
    ws4.merge_range(r, 0, r, 3,
        f"IVS 105 — Itemized RCN: Structure | Finishing | Soft Costs | Depreciation | {today}", fHEAD)
    ws4.set_row(r, 20); r += 2

    # Column headers
    for ci, hdr in enumerate(["البند / وصف البند", "معدل الوحدة (EGP/م²)",
                               "الكمية (م²)", "الإجمالي (EGP)"]):
        ws4.write(r, ci, hdr, fSUBHEAD)
    ws4.set_row(r, 22); r += 1

    # ── Section A: Land Value (formula-driven) ────────────────────────────────
    r = write_section_header(ws4, r, 0, 3,
        "القسم الأول: تقدير قيمة الأرض — طريقة الاستخلاص")
    _land_ref_er = r + 1                         # Excel 1-based row
    ws4.write(r, 0, "سعر المتر السوقي المرجعي (EGP/م²)", fLABEL)
    ws4.write_formula(r, 1, f"='{INP}'!B{_R_PRICE}", fNUM); r += 1
    _land_ratio_er = r + 1
    ws4.write(r, 0, f"نسبة قيمة الأرض من الإجمالي ({LAND_COST_RATE*100:.0f}%)", fLABEL)
    ws4.write(r, 1, LAND_COST_RATE, fPCT); r += 1
    _land_pm2_er = r + 1
    ws4.write(r, 0, "سعر متر الأرض المستخلص (EGP/م²)", fLABEL)
    ws4.write_formula(r, 1, f"=B{_land_ref_er}*B{_land_ratio_er}", fNUM); r += 1
    _land_area_er = r + 1
    ws4.write(r, 0, "مساحة الأرض (م²)", fLABEL)
    ws4.write_formula(r, 2, f"='{INP}'!B{_R_AREA}", fNUM); r += 1
    _land_total_row = r + 1                      # Excel 1-based row of land total
    ws4.write(r, 0, "قيمة الأرض الإجمالية (1)", fGOLD_L)
    ws4.write_formula(r, 3, f"=B{_land_pm2_er}*C{_land_area_er}", fFINAL)
    r += 2

    # ── Section B: Structure / Skeleton Works ─────────────────────────────────
    r = write_section_header(ws4, r, 0, 3,
        "القسم الثاني: أعمال الهيكل الإنشائي (Structure / Skeleton Works)")
    _struct_start = r                             # 0-based first data row
    struct_items = [
        ("أعمال الحفر والتأسيس",                    _R_EXCAVATION),
        ("الخرسانة المسلحة — أعمدة وجسور وبلاطات", _R_CONCRETE),
        ("حديد التسليح",                            _R_REBAR),
        ("أعمال البناء والطوب والحوائط",             _R_BRICKWORK),
    ]
    for name, rate_row in struct_items:
        exc_row = r + 1                           # Excel row for this item
        ws4.write(r, 0, name, fLABEL)
        ws4.write_formula(r, 1, f"='{INP}'!B{rate_row}", fNUM)
        ws4.write_formula(r, 2, f"='{INP}'!B{_R_AREA}", fNUM)
        ws4.write_formula(r, 3, f"=B{exc_row}*C{exc_row}", fMONEY)
        r += 1
    _struct_end = r                               # 0-based row past last item
    _struct_total_row = r + 1                     # Excel 1-based subtotal row
    ws4.write(r, 0, "إجمالي أعمال الهيكل الإنشائي  (أ)", fGOLD_L)
    ws4.write_formula(r, 3,
        f"=SUM(D{_struct_start + 1}:D{_struct_end})", fFINAL)
    r += 2

    # ── Section C: Finishing Works ────────────────────────────────────────────
    r = write_section_header(ws4, r, 0, 3,
        "القسم الثالث: أعمال التشطيبات الداخلية والخارجية (Finishing Works)")
    _finish_start = r
    finish_items = [
        ("أعمال البياض والجبس والملس النهائي",      _R_PLASTERING),
        ("الأرضيات والتشطيبات (بورسلان / رخام)",   _R_FLOORING),
        ("أعمال السباكة وشبكات الصرف والمياه",     _R_PLUMBING),
        ("أعمال الكهرباء والإنارة والتأريض",        _R_ELECTRICITY),
        ("الدهانات والأعمال النهائية",              _R_PAINTING),
        ("الواجهات والكسوة الخارجية",               _R_FACADES),
    ]
    for name, rate_row in finish_items:
        exc_row = r + 1
        ws4.write(r, 0, name, fLABEL)
        ws4.write_formula(r, 1, f"='{INP}'!B{rate_row}", fNUM)
        ws4.write_formula(r, 2, f"='{INP}'!B{_R_AREA}", fNUM)
        ws4.write_formula(r, 3, f"=B{exc_row}*C{exc_row}", fMONEY)
        r += 1
    _finish_end = r
    _finish_total_row = r + 1
    ws4.write(r, 0, "إجمالي أعمال التشطيبات  (ب)", fGOLD_L)
    ws4.write_formula(r, 3,
        f"=SUM(D{_finish_start + 1}:D{_finish_end})", fFINAL)
    r += 2

    # ── Section D: Soft Costs & Overheads ─────────────────────────────────────
    r = write_section_header(ws4, r, 0, 3,
        "القسم الرابع: التكاليف غير المباشرة والطوارئ (Soft Costs & Overheads)")
    _soft_start = r
    _contingency_row = r + 1
    ws4.write(r, 0, "مصروفات طوارئ وتكاليف غير مباشرة", fLABEL)
    ws4.write_formula(r, 1, f"='{INP}'!B{_R_SOFT_PCT}", fPCT)
    ws4.write(r, 2, "من الإجمالي المباشر", fDATA_C)
    ws4.write_formula(r, 3,
        f"='{INP}'!B{_R_SOFT_PCT}*(D{_struct_total_row}+D{_finish_total_row})",
        fMONEY)
    r += 1
    _contractor_row = r + 1
    ws4.write(r, 0, "ربح المقاول والمصروفات الإدارية (15%)", fLABEL)
    ws4.write(r, 1, 0.15, fPCT)
    ws4.write(r, 2, "من إجمالي التكلفة المباشرة", fDATA_C)
    ws4.write_formula(r, 3,
        f"=0.15*(D{_struct_total_row}+D{_finish_total_row}+D{_contingency_row})",
        fMONEY)
    r += 1
    _soft_end = r
    _soft_total_row = r + 1
    ws4.write(r, 0, "إجمالي التكاليف غير المباشرة  (ج)", fGOLD_L)
    ws4.write_formula(r, 3,
        f"=SUM(D{_soft_start + 1}:D{_soft_end})", fFINAL)
    r += 1
    # Grand RCN total
    _rcn_total_row = r + 1
    ws4.write(r, 0, "إجمالي تكلفة الاستبدال الجديدة RCN = (أ + ب + ج)", fGOLD_L)
    ws4.write_formula(r, 3,
        f"=D{_struct_total_row}+D{_finish_total_row}+D{_soft_total_row}",
        F(bold=True, bg="#D9E1F2", fg="#1F4E78", sz=13, align="center",
          border=2, num_fmt='#,##0.00 "EGP"'))
    r += 2

    # ── Section E: Depreciation ───────────────────────────────────────────────
    r = write_section_header(ws4, r, 0, 3,
        "القسم الخامس: الإهلاك والتهالك المتراكم")
    ws4.write(r, 0, "العمر الحالي للمبنى (سنة)", fLABEL)
    ws4.write_formula(r, 1, f"='{INP}'!B{_R_AGE}", fDATA_C); r += 1
    ws4.write(r, 0, "العمر الاقتصادي للمبنى (سنة)", fLABEL)
    ws4.write(r, 1, ECONOMIC_LIFE, fDATA_C); r += 1
    ws4.write(r, 0, "نسبة الإهلاك الطبيعي = العمر الحالي ÷ العمر الاقتصادي", fLABEL)
    ws4.write_formula(r, 1, f"='{INP}'!B{_R_AGE}/{ECONOMIC_LIFE}", fPCT); r += 1
    _phys_depr_row = r + 1
    ws4.write(r, 0, "الإهلاك الطبيعي والمادي (EGP)", fLABEL)
    ws4.write_formula(r, 3,
        f"=('{INP}'!B{_R_AGE}/{ECONOMIC_LIFE})*D{_rcn_total_row}", fMONEY)
    r += 1
    _func_depr_row = r + 1
    ws4.write(r, 0, "الإهلاك الوظيفي والخارجي (2%) (EGP)", fLABEL)
    ws4.write_formula(r, 3, f"=0.02*D{_rcn_total_row}", fMONEY); r += 1
    _total_depr_row = r + 1
    ws4.write(r, 0, "إجمالي الإهلاك المتراكم", fGOLD_L)
    ws4.write_formula(r, 3, f"=D{_phys_depr_row}+D{_func_depr_row}", fMONEY); r += 1
    _net_build_row = r + 1
    ws4.write(r, 0, "صافي قيمة المبنى بعد الإهلاك", fGOLD_L)
    ws4.write_formula(r, 3,
        f"=D{_rcn_total_row}-D{_total_depr_row}", fFINAL)
    r += 2

    # ── Section F: Total DRC ──────────────────────────────────────────────────
    r = write_section_header(ws4, r, 0, 3,
        "القسم السادس: إجمالي القيمة بأسلوب التكلفة (DRC)")
    ws4.write(r, 0, "قيمة الأرض  (1)", fLABEL)
    ws4.write_formula(r, 3, f"=D{_land_total_row}", fMONEY); r += 1
    ws4.write(r, 0, "صافي قيمة المبنى بعد الإهلاك", fLABEL)
    ws4.write_formula(r, 3, f"=D{_net_build_row}", fMONEY); r += 1
    _drc_total_row = r + 1
    ws4.write(r, 0, "القيمة الإجمالية = قيمة الأرض + صافي قيمة المبنى", fGOLD_L)
    ws4.write_formula(r, 3,
        f"=D{_land_total_row}+D{_net_build_row}", fFINAL)
    r += 1
    ws4.write(r, 0, "سعر المتر بأسلوب التكلفة (EGP/م²)", fGOLD_L)
    ws4.write_formula(r, 3,
        f"=D{_drc_total_row}/'{INP}'!B{_R_AREA}", fMONEY)
    r += 3

    # ── Pie Chart: Cost Distribution ──────────────────────────────────────────
    ws4.write(r, 0, "بيانات مخطط توزيع تكلفة البناء", fSEC); r += 1
    _chart_data_r0 = r                           # 0-based first chart data row
    chart_pie_items = [
        ("أعمال الهيكل الإنشائي (أ)",   _struct_total_row),
        ("أعمال التشطيبات (ب)",          _finish_total_row),
        ("التكاليف غير المباشرة (ج)",    _soft_total_row),
    ]
    for lbl, total_row in chart_pie_items:
        ws4.write(r, 0, lbl, fLABEL)
        ws4.write_formula(r, 1, f"=D{total_row}", fMONEY)
        r += 1
    _chart_data_r1 = r - 1                       # 0-based last chart data row

    pie_chart = wb.add_chart({"type": "pie"})
    pie_chart.add_series({
        "name":       "توزيع تكلفة البناء",
        "categories": ["طريقة التكلفة", _chart_data_r0, 0, _chart_data_r1, 0],
        "values":     ["طريقة التكلفة", _chart_data_r0, 1, _chart_data_r1, 1],
        "data_labels": {
            "percentage": True,
            "category":   True,
            "font": {"name": "Simplified Arabic", "size": 10},
        },
    })
    pie_chart.set_title({"name": "توزيع تكلفة البناء: هيكل إنشائي | تشطيبات | تكاليف غير مباشرة"})
    pie_chart.set_style(10)
    pie_chart.set_size({"width": 480, "height": 300})
    ws4.insert_chart(r, 0, pie_chart, {"x_offset": 5, "y_offset": 5})

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 5 — رأسمالة الدخل  (Income Capitalization)
    # ══════════════════════════════════════════════════════════════════════════
    ws5 = wb.add_worksheet("رأسمالة الدخل")
    ws5.right_to_left()
    ws5.set_column("A:A", 40)
    ws5.set_column("B:C", 20)

    r = 0
    ws5.merge_range(r, 0, r, 2, "أسلوب رأسمالة الدخل — Income Capitalization", fTITLE)
    ws5.set_row(r, 35); r += 1
    ws5.merge_range(r, 0, r, 2, f"IVS 105 — Income Approach | {today}", fHEAD)
    ws5.set_row(r, 20); r += 2

    income_rows = [
        ("الإيجار الشهري للوحدة", income["monthly_rent"], fMONEY, "EGP / شهر"),
        ("الدخل الإيجاري السنوي الإجمالي (الإيجار × 12)", income["annual_gross"], fMONEY, "EGP / سنة"),
        ("خسائر عدم الإشغال والمصاريف الإدارية (10%)", income["vacancy_loss"], fMONEY, "EGP / سنة"),
        ("صافي الدخل التشغيلي الفعال (NOI)", income["net_income"], fMONEY, "EGP / سنة"),
        ("العمر الاقتصادي المتبقى للمبنى (سنة)", income["remaining_life"], fDATA_C, "سنة"),
        ("معدل استرداد رأس المال = 1 / العمر المتبقى", income["capital_recovery"], fPCT, "سنوياً"),
        ("سعر الفائدة السائد", income["interest_rate"], fPCT, "سنوياً"),
        ("معدل الرسملة الكلي = الفائدة + استرداد رأس المال", income["effective_cap"], fPCT, "سنوياً"),
        ("العائد على الأرض = قيمة الأرض × الفائدة", income["land_return"], fMONEY, "EGP / سنة"),
        ("الدخل الصافي المتاح للمبنى = NOI - عائد الأرض", income["net_bldg_income"], fMONEY, "EGP / سنة"),
        ("قيمة المبنى = دخل المبنى / معدل الرسملة", income["building_value"], fMONEY, "EGP"),
        ("قيمة الأرض (مُضاف)", income["land_value"], fMONEY, "EGP"),
    ]

    for label, value, fmt, unit in income_rows:
        ws5.write(r, 0, label, fLABEL)
        ws5.write(r, 1, value, fmt)
        ws5.write(r, 2, unit,  fDATA_C)
        r += 1

    r += 1
    ws5.write(r, 0, "القيمة الإجمالية بأسلوب رأسمالة الدخل", fGOLD_L)
    ws5.write(r, 1, income["total"], fFINAL)
    ws5.write(r, 2, "EGP", fDATA_C)
    r += 1
    ws5.write(r, 0, f"سعر المتر بأسلوب الدخل (EGP/م²)", fGOLD_L)
    ws5.write(r, 1, income["ppm"], fMONEY)
    r += 3

    ws5.merge_range(r, 0, r, 2, "شرح أسلوب رأسمالة الدخل", fSEC); r += 1
    exp_inc = (
        "يُقيّم هذا الأسلوب العقار بتحويل الدخل الإيجاري الصافي إلى قيمة رأسمالية. "
        "تُحسب القيمة بقسمة صافي الدخل التشغيلي (NOI) على معدل الرسملة الذي يشمل سعر الفائدة ومعدل "
        "استرداد رأس المال. يُستخدم هذا الأسلوب وفق IVS 105 للعقارات ذات الدخل الإيجاري الثابت."
    )
    ws5.merge_range(r, 0, r+1, 2, exp_inc, fWRAP)
    ws5.set_row(r, 28); ws5.set_row(r+1, 28)

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 6 — التحليل المكاني  (Kriging / IDW)
    # ══════════════════════════════════════════════════════════════════════════
    ws6 = wb.add_worksheet("التحليل المكاني")
    ws6.right_to_left()
    ws6.set_column("A:A", 14)
    ws6.set_column("B:E", 18)

    r = 0
    ws6.merge_range(r, 0, r, 4, "التحليل المكاني — Kriging / IDW", fTITLE)
    ws6.set_row(r, 32); r += 1
    ws6.merge_range(r, 0, r, 4, f"Spatial Interpolation (pykrige) | {today}", fHEAD)
    ws6.set_row(r, 20); r += 2

    ws6.write(r, 0, "رقم الوحدة", fSUBHEAD)
    ws6.write(r, 1, "السعر z (EGP/م²)", fSUBHEAD)
    ws6.write(r, 2, "خط العرض y", fSUBHEAD)
    ws6.write(r, 3, "خط الطول x", fSUBHEAD)
    ws6.write(r, 4, "سنة البناء", fSUBHEAD)
    r += 1

    for c in COMPS_DB:
        ws6.write(r, 0, c["id"],    fDATA_C)
        ws6.write(r, 1, c["ppm"],   fNUM)
        ws6.write(r, 2, c["y"],     fDATA_C)
        ws6.write(r, 3, c["x"],     fDATA_C)
        ws6.write(r, 4, c["year"],  fDATA_C)
        r += 1

    r += 1
    ws6.merge_range(r, 0, r, 4, "نتائج الاستيفاء المكاني للعقار موضوع التقييم", fSEC)
    r += 1
    ws6.write(r, 0, "الطريقة المستخدمة",              fLABEL)
    ws6.merge_range(r, 1, r, 4, kriging["method"],     fDATA)
    r += 1
    ws6.write(r, 0, "إحداثية x (خط الطول)",           fLABEL); ws6.write(r, 1, target_x, fDATA_C)
    ws6.write(r, 2, "إحداثية y (خط العرض)",           fLABEL); ws6.write(r, 3, target_y, fDATA_C)
    r += 1
    ws6.write(r, 0, "التباين (Variance)",              fLABEL); ws6.write(r, 1, kriging["variance"], fNUM)
    r += 1
    ws6.write(r, 0, "القيمة المُستنتجة (EGP/م²)",     fGOLD_L); ws6.write(r, 1, kriging["ppm"], fFINAL)
    ws6.write(r, 2, "القيمة الإجمالية (EGP)",          fGOLD_L)
    ws6.write(r, 3, kriging["ppm"] * area,             fFINAL)
    r += 3

    ws6.merge_range(r, 0, r, 4, "شرح التحليل المكاني (Kriging / IDW)", fSEC); r += 1
    exp_krig = (
        "Kriging هو أسلوب استيفاء إحصائي مكاني (Geostatistical Interpolation) يُقدّر قيمة العقار بناءً "
        "على توزيع الأسعار الجغرافي للعقارات المجاورة. يأخذ الأسلوب في الاعتبار التباين المكاني "
        "(Variogram) ليُنتج تقديراً بلا انحياز. عند تعذّر Kriging يُستخدم IDW "
        "(Inverse Distance Weighting) كبديل يُعطي أوزاناً عكسية مع المسافة."
    )
    ws6.merge_range(r, 0, r+2, 4, exp_krig, fWRAP)
    for i in range(3): ws6.set_row(r+i, 25)

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 7 — الانحدار المتعدد  (OLS Regression)
    # ══════════════════════════════════════════════════════════════════════════
    ws7 = wb.add_worksheet("الانحدار المتعدد")
    ws7.right_to_left()
    ws7.set_column("A:A", 30)
    ws7.set_column("B:F", 18)

    r = 0
    ws7.merge_range(r, 0, r, 5, "تحليل الانحدار الخطي المتعدد — OLS Regression", fTITLE)
    ws7.set_row(r, 32); r += 1
    ws7.merge_range(r, 0, r, 5, f"Multiple Linear Regression (statsmodels OLS) | {today}", fHEAD)
    ws7.set_row(r, 20); r += 2

    # Regression statistics block
    ws7.merge_range(r, 0, r, 2, "Regression Statistics", fSEC)
    ws7.merge_range(r, 3, r, 5, "ANOVA", fSEC)
    r += 1

    stats_rows = [
        ("Multiple R",     round(math.sqrt(regression["r_squared"]) if regression["r_squared"] else 0, 8)),
        ("R Square",       regression["r_squared"]),
        ("Adjusted R²",    regression["adj_r_squared"]),
        ("Standard Error", regression["std_err"]),
        ("Observations",   regression["n_obs"]),
    ]
    for label, val in stats_rows:
        ws7.write(r, 0, label, fLABEL)
        ws7.write(r, 1, val,   fNUM)
        r += 1

    r += 1
    ws7.write(r, 0, "المتغير",         fSUBHEAD)
    ws7.write(r, 1, "Coefficients",    fSUBHEAD)
    ws7.write(r, 2, "Standard Error",  fSUBHEAD)
    ws7.write(r, 3, "P-value",         fSUBHEAD)
    ws7.write(r, 4, "Lower 95%",       fSUBHEAD)
    ws7.write(r, 5, "Upper 95%",       fSUBHEAD)
    r += 1

    coef_rows = [
        ("Intercept (const)", "const",  "-",    "-"),
        ("رقم الدور (NOS)",   "floor",  "floor","floor"),
        ("إجمالي المساحة (TFA)","area", "area", "area"),
        ("سنة البناء (YEAR)", "year",   "year", "year"),
    ]
    for label, key, pk, ek in coef_rows:
        ws7.write(r, 0, label, fLABEL)
        ws7.write(r, 1, regression["coef"].get(key, 0),  fNUM)
        ws7.write(r, 2, regression["std_err"],            fNUM)
        ws7.write(r, 3, regression["pval"].get(pk, "-") if pk != "-" else "-", fNUM if pk!="-" else fDATA_C)
        ws7.write(r, 4, "-", fDATA_C)
        ws7.write(r, 5, "-", fDATA_C)
        r += 1

    r += 1
    ws7.merge_range(r, 0, r, 2, "تطبيق النموذج على العقار موضوع التقييم", fSEC)
    r += 1
    pred_rows = [
        ("رقم الدور المُدخل",         floor),
        ("المساحة المُدخلة (م²)",     area),
        ("سنة البناء المُدخلة",        year_built),
    ]
    for label, val in pred_rows:
        ws7.write(r, 0, label, fLABEL); ws7.write(r, 1, val, fDATA_C); r += 1

    ws7.write(r, 0, "القيمة المُتنبأ بها (EGP/م²)", fGOLD_L)
    ws7.write(r, 1, regression["ppm"], fFINAL)
    ws7.write(r, 2, "القيمة الإجمالية (EGP)",        fGOLD_L)
    ws7.write(r, 3, regression["ppm"] * area,         fFINAL)
    r += 1
    if "error" in regression:
        ws7.write(r, 0, f"ملاحظة: {regression['error']}", fWRAP)
    r += 3

    # Raw data table
    ws7.merge_range(r, 0, r, 5, "البيانات الأساسية المستخدمة في الانحدار", fSEC)
    r += 1
    ws7.write(r,0,"#",fSUBHEAD);ws7.write(r,1,"رقم الوحدة",fSUBHEAD)
    ws7.write(r,2,"الدور",fSUBHEAD);ws7.write(r,3,"المساحة",fSUBHEAD)
    ws7.write(r,4,"سنة البناء",fSUBHEAD);ws7.write(r,5,"السعر (EGP/م²)",fSUBHEAD)
    r += 1
    for i, c in enumerate(COMPS_DB):
        ws7.write(r,0,i+1,fDATA_C);ws7.write(r,1,c["id"],fDATA_C)
        ws7.write(r,2,c["floor"],fDATA_C);ws7.write(r,3,c["area"],fNUM)
        ws7.write(r,4,c["year"],fDATA_C);ws7.write(r,5,c["ppm"],fNUM)
        r += 1

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 8 — الخيارات الحقيقية  (Real Options)
    # ══════════════════════════════════════════════════════════════════════════
    ws8 = wb.add_worksheet("الخيارات الحقيقية")
    ws8.right_to_left()
    ws8.set_column("A:A", 42)
    ws8.set_column("B:C", 22)

    r = 0
    ws8.merge_range(r, 0, r, 2, "الخيارات الحقيقية — Real Options Analysis (Black-Scholes)", fTITLE)
    ws8.set_row(r, 35); r += 1
    ws8.merge_range(r, 0, r, 2, f"Real Options Valuation — Development Potential Assessment | {today}", fHEAD)
    ws8.set_row(r, 20); r += 2

    # Inputs
    r = write_section_header(ws8, r, 0, 2, "مدخلات النموذج (Model Inputs)")
    ro_inputs = [
        ("S — قيمة الأصل الحالية (Current Asset Value) EGP",     ro["S"],          fMONEY),
        ("K — تكلفة التطوير / سعر التنفيذ (Development Cost) EGP",ro["K"],          fMONEY),
        ("σ — معامل التذبذب السنوي (Annual Volatility)",           ro["volatility"], fPCT),
        ("T — فترة الحيازة / التطوير (Time to Develop) سنوات",    ro["time_years"], fNUM),
        ("r — معدل الفائدة الخالي من المخاطر (Risk-Free Rate)",    ro["risk_free"],  fPCT),
        ("سعر متر المبنى المرجعي (Base Price EGP/م²)",             ro["base_ppm"],   fMONEY),
        ("تكلفة متر التطوير (Development Cost/م²)",                ro["dev_cost_pm2"],fMONEY),
    ]
    for label, val, fmt in ro_inputs:
        ws8.write(r, 0, label, fLABEL)
        ws8.write(r, 1, val,   fmt)
        r += 1

    r += 1
    r = write_section_header(ws8, r, 0, 2, "حسابات نموذج Black-Scholes")
    ro_calcs = [
        ("d1 = [ln(S/K) + (r + σ²/2)×T] / (σ√T)",          ro["d1"],   fNUM),
        ("d2 = d1 − σ√T",                                     ro["d2"],   fNUM),
        ("N(d1) — الدالة التراكمية الطبيعية لـ d1",          ro["N_d1"], fNUM),
        ("N(d2) — الدالة التراكمية الطبيعية لـ d2",          ro["N_d2"], fNUM),
        ("قيمة خيار التطوير = S×N(d1) − K×e^(-rT)×N(d2)",   ro["option_value"], fMONEY),
    ]
    for label, val, fmt in ro_calcs:
        ws8.write(r, 0, label, fLABEL); ws8.write(r, 1, val, fmt); r += 1

    r += 1
    r = write_section_header(ws8, r, 0, 2, "النتائج — Real Options Results")
    ws8.write(r, 0, "القيمة الجوهرية الحالية (Intrinsic Value) EGP", fLABEL)
    ws8.write(r, 1, ro["S"], fMONEY); r += 1
    ws8.write(r, 0, "قيمة الخيار (Option Premium) EGP",              fLABEL)
    ws8.write(r, 1, max(ro["option_value"], 0), fMONEY); r += 1
    ws8.write(r, 0, "القيمة الكلية مع الخيار (Total Value) EGP",     fGOLD_L)
    ws8.write(r, 1, ro["total"], fFINAL); r += 1
    ws8.write(r, 0, "سعر المتر بأسلوب الخيارات الحقيقية (EGP/م²)",   fGOLD_L)
    ws8.write(r, 1, ro["ppm"],   fFINAL); r += 3

    # Explanation
    ws8.merge_range(r, 0, r, 2, "شرح أسلوب الخيارات الحقيقية", fSEC); r += 1
    exp_ro = (
        "يُقيّم هذا الأسلوب قيمة المرونة في قرار التطوير أو الاحتفاظ بالعقار. يُطبّق نموذج Black-Scholes "
        "المستخدم في تسعير الخيارات المالية على الأصول العقارية: S (قيمة الأصل الحالية)، "
        "K (تكلفة التطوير كـ'سعر تنفيذ')، σ (تذبذب سوق العقارات)، T (أفق الاستثمار)، "
        "r (معدل الفائدة الخالي من المخاطر). القيمة النهائية = القيمة الجوهرية + علاوة الخيار، "
        "مما يعكس إمكانية التطوير المستقبلية للعقار."
    )
    ws8.merge_range(r, 0, r+2, 2, exp_ro, fWRAP)
    for i in range(3): ws8.set_row(r+i, 28)

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 9 — توفيق النتائج  (Reconciliation)
    # ══════════════════════════════════════════════════════════════════════════
    ws9 = wb.add_worksheet("توفيق النتائج")
    ws9.right_to_left()
    ws9.set_column("A:A", 35)
    ws9.set_column("B:E", 18)

    r = 0
    ws9.merge_range(r, 0, r, 4, "توفيق النتائج — Reconciliation of Valuation Methods", fTITLE)
    ws9.set_row(r, 35); r += 1
    ws9.merge_range(r, 0, r, 4, f"IVS 105 — Weighted Reconciliation Matrix | {today}", fHEAD)
    ws9.set_row(r, 20); r += 2

    ws9.write(r, 0, "أسلوب التقييم",              fGOLD_L)
    ws9.write(r, 1, "سعر المتر (EGP/م²)",         fGOLD)
    ws9.write(r, 2, "القيمة الإجمالية (EGP)",     fGOLD)
    ws9.write(r, 3, "الوزن النسبي",               fGOLD)
    ws9.write(r, 4, "القيمة الموزونة (EGP/م²)",   fGOLD)
    ws9.set_row(r, 22); r += 1

    method_details = [
        ("أسلوب مقارنة البيوع السابقة",  sales["ppm"],       sales["total"],           0.30),
        ("أسلوب حساب التكلفة (DRC)",      cost["ppm"],        cost["total"],            0.20),
        ("أسلوب رأسمالة الدخل",           income["ppm"],      income["total"],          0.15),
        ("التحليل المكاني (Kriging/IDW)", kriging["ppm"],     kriging["ppm"] * area,    0.15),
        ("الانحدار الخطي المتعدد (OLS)",  regression["ppm"],  regression["ppm"] * area, 0.12),
        ("الخيارات الحقيقية (B-S)",       ro["ppm"],          ro["total"],              0.08),
    ]

    for name, ppm, total, weight in method_details:
        ws9.write(r, 0, name,          fLABEL)
        ws9.write(r, 1, ppm,           fMONEY)
        ws9.write(r, 2, total,         fMONEY)
        ws9.write(r, 3, weight,        fPCT)
        ws9.write(r, 4, ppm * weight,  fMONEY)
        r += 1

    r += 1
    ws9.write(r, 0, "مجموع الأوزان",  fSEC)
    ws9.write(r, 3, 1.0,               fPCT)
    r += 1
    ws9.merge_range(r, 0, r, 3, "القيمة السوقية النهائية الموزونة (EGP/م²)", fGOLD_L)
    ws9.write(r, 4, final_ppm, fFINAL); r += 1
    ws9.merge_range(r, 0, r, 3, f"القيمة السوقية الإجمالية للعقار ({area} م²)", fGOLD_L)
    ws9.write(r, 4, final_total, fFINAL); r += 3

    # Narrative
    r = write_section_header(ws9, r, 0, 4, "تحليل توفيق النتائج ومبرراته")
    narrative = (
        f"بدراسة طرق التقييم الست وفق درجة موثوقية كل منها وملاءمتها لطبيعة العقار موضوع التقييم "
        f"({property_type} — {location})، تم توزيع الأوزان كالتالي:\n"
        f"• مقارنة البيوع (30%): الأكثر موثوقية لتوافر بيانات كافية في السوق.\n"
        f"• التكلفة (20%): مناسب كأسلوب تحقق للعقارات السكنية.\n"
        f"• رأسمالة الدخل (15%): يعكس إمكانية الاستثمار الإيجاري.\n"
        f"• Kriging المكاني (15%): يُدمج البُعد الجغرافي في التقييم.\n"
        f"• الانحدار المتعدد (12%): نموذج إحصائي متعدد المتغيرات.\n"
        f"• الخيارات الحقيقية (8%): يُقيّم إمكانية التطوير المستقبلية.\n"
        f"القيمة السوقية العادلة النهائية = {_fmt(final_ppm)} EGP/م² | الإجمالي = {_fmt(final_total)} EGP"
    )
    ws9.merge_range(r, 0, r+7, 4, narrative, fWRAP)
    for i in range(8): ws9.set_row(r+i, 22)

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 10 — محددات التقييم
    # ══════════════════════════════════════════════════════════════════════════
    ws10 = wb.add_worksheet("محددات التقييم")
    ws10.right_to_left()
    ws10.set_column("A:A", 90)

    r = 0
    ws10.merge_range(r, 0, r, 0, "فروض ومحددات التقرير", fTITLE)
    ws10.set_row(r, 35); r += 2

    assumptions = [
        "_ القيمة السوقية المطلوب تحديدها هى الثمن الأكثر احتمالاً في سوق تنافسي ومفتوح وفق معايير IVS.",
        "_ الغرض من إعداد التقرير هو تقدير القيمة السوقية العادلة للعقار.",
        "_ لا يوجد نزاعات ملكية على العقار ولا يوجد أي رهن أو التزامات خفية على حسب إقرار المالك.",
        "_ الشروط المحددة للملكية وذلك على مسئولية المالك الذي أقر بصحتها.",
        "_ تمت معاينة العقار من الداخل والخارج ولا يوجد عيوب خفية ظاهرة تؤثر على القيمة.",
        "_ مستندات الملكية المقدمة من المالك على مسئوليته.",
        "_ قيمة العقار المحددة تسري للمدة المذكورة في التقرير وهي ثلاثة أشهر من تاريخ التقرير.",
        "_ التقرير هو ملكية خاصة للعميل الموجه إليه التقرير ولا يجوز نشره أو الإفصاح عن محتوياته.",
        "_ تم تقييم العقار آخذاً في الاعتبار فرضية أعلى وأفضل استخدام.",
        "_ يُفترض عدم وجود أي ظروف خفية بالعقار أو في التربة تؤثر على القيمة.",
        "_ أية تعامل مع هذا التقرير يجب أن يكون كاملاً وليس جزئياً.",
        "_ الملاحق الخاصة بالرسومات والصور والجداول مع هذا التقرير جزء لا يتجزأ منه.",
        "_ لا يحق نشر أو طبع أو نسخ كل أو بعض هذا التقرير بدون إذن كتابي من الخبير.",
        "_ الخبير بنفسه قام بفحص العقار موضوع التقييم ميدانياً.",
        "_ الخبير بنفسه قام بإعداد كل التوصيات والنتائج الواردة في هذا التقرير.",
        "_ في حالة وجود أي خلاف لفروض ومحددات التقرير يجب إبلاغ الخبير فوراً.",
    ]
    for line in assumptions:
        ws10.write(r, 0, line, fWRAP)
        ws10.set_row(r, 22)
        r += 1

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 11 — شهادة الخبير
    # ══════════════════════════════════════════════════════════════════════════
    ws11 = wb.add_worksheet("شهادة")
    ws11.right_to_left()
    ws11.set_column("A:A", 90)

    r = 0
    ws11.merge_range(r, 0, r, 0, "شهادة الخبير", fTITLE)
    ws11.set_row(r, 35); r += 2
    ws11.write(r, 0, "أشهد أنا خبير التقييم بأنني:", fSEC)
    ws11.set_row(r, 25); r += 2

    cert_items = [
        "1- قد قمت بدراسة سوق منطقة العقار واخترت عقارات مقارنة من خلال استقصاء ميداني دقيق.",
        "2- قد قمت بأخذ جميع العوامل التي تؤثر على قيمة العقار بعين الاعتبار وأفصحت عنها.",
        "3- قد قدمت بالتقرير رأيي الشخصي المحايد والموضوعي في القيمة دون أي ضغوط خارجية.",
        "4- انه ليس لدي أي اهتمام حالي أو مستقبلي متعلق بالعقار يؤثر على حيادية رأيي.",
        "5- انه ليس لي اهتمام حالي أو مستقبلي بالعقار وأن رأيي غير متحيز.",
        "6- أنه لم يُطلب إليّ تقديم أي آراء مسبقة عن قيمة العقار.",
        "7- إنني قمت بأداء هذا التقييم طبقاً لمعايير التقييم الدولية IVS ومعايير الرقابة المالية EFSA.",
        "8- أنني أُقرّ أن القيمة الواردة في التقييم مبنية على التحليل الفعلي للسوق وليس على تقديرات تقريبية.",
        "9- أنني شخصياً قمت بفحص داخل وخارج العقار موضوع التقييم.",
        "10- إنني قمت شخصياً بإعداد كل التوصيات والنتائج المتعلقة بهذا التقييم.",
    ]
    for item in cert_items:
        ws11.write(r, 0, item, fCERT)
        ws11.set_row(r, 28)
        r += 1

    r += 2
    ws11.write(r, 0,
        f"التوقيع: .......................    |    "
        f"الاسم: {EXPERT_NAME}    |    رقم القيد: {EXPERT_REG}    |    التاريخ: {today}",
        fDATA)

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 12 — لوحة القيادة التنفيذية  (Executive Dashboard)
    # ══════════════════════════════════════════════════════════════════════════
    _add_executive_dashboard(
        wb, F, fTITLE, fHEAD, fGOLD, fLABEL, fDATA, fDATA_C, fMONEY,
        final_ppm, final_total, recon_table, area,
        dcf=dcf, forecast=forecast, hbu_adv=hbu_adv,
        today=today, report_number=report_number,
    )

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 13 — مصادر البيانات والمنهجية  (Data Sources)
    # ══════════════════════════════════════════════════════════════════════════
    _add_data_sources_sheet(wb, F, fTITLE, fHEAD, fGOLD, fLABEL, fDATA,
                            today, dcf=dcf)

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 14 — مصفوفة تعديل الأرض  (Land Adjustment Matrix)
    # IVS 105 §50-60: Adjusted Land Value = Base × (1 + ΣAdjustments)
    # ══════════════════════════════════════════════════════════════════════════
    ws_land = wb.add_worksheet("مصفوفة تعديل الأرض")
    ws_land.right_to_left()
    ws_land.set_column("A:A", 38)
    ws_land.set_column("B:E", 19)
    ws_land.set_column("F:F", 30)
    ws_land.set_tab_color("#375623")

    r = 0
    ws_land.merge_range(r, 0, r, 5,
        "مصفوفة تعديل الأرض — Land Sales Comparison Adjustment Grid", fTITLE)
    ws_land.set_row(r, 35); r += 1
    ws_land.merge_range(r, 0, r, 5,
        "IVS 105 § 50-60  |  القيمة المعدَّلة = السعر الأصلي × (1 + مجموع التعديلات)"
        "  |  الخلايا الزرقاء قابلة للتعديل — الأوزان يجب أن يكون مجموعها 100%",
        F(italic=True, fg="#1F78D1", sz=10, align="center", bg="#EBF3FB"))
    ws_land.set_row(r, 22); r += 2

    # Column headers
    ws_land.write(r, 0, "عوامل التعديل", fSUBHEAD)
    for ci, lbl in enumerate(["مقارنة 1", "مقارنة 2", "مقارنة 3", "مقارنة 4"]):
        ws_land.write(r, ci + 1, lbl, fSUBHEAD)
    ws_land.write(r, 5, "ملاحظة / رابط الموقع", fSUBHEAD)
    ws_land.set_row(r, 22); r += 1

    # Comparable land sales dataset
    _LAND_COMPS_ADJ = [
        {"desc": "دريم لاند — قطعة 15",         "base": 8500,
         "time": 0.05,  "loc":  0.00,  "area": -0.03,
         "front": 0.02, "legal": 0.00, "view":  0.03},
        {"desc": "أكتوبر — مجمع R7 قطعة 22",   "base": 7800,
         "time": 0.08,  "loc":  0.05,  "area":  0.00,
         "front": -0.02,"legal": 0.00, "view":  0.00},
        {"desc": "المعادي — قطعة B-7",           "base": 12000,
         "time": 0.03,  "loc": -0.10,  "area":  0.02,
         "front": 0.00, "legal": 0.02, "view":  0.05},
        {"desc": "القاهرة الجديدة — R2",         "base": 9200,
         "time": 0.05,  "loc": -0.03,  "area": -0.02,
         "front": 0.03, "legal": 0.00, "view":  0.02},
    ]
    _adj_field_defs = [
        ("السعر الأصلي للمقارنة (EGP/م²) — قابل للتعديل",    "base",  False),
        ("تعديل الزمن / ظروف السوق (%)",                      "time",  True),
        ("تعديل الموقع والمنطقة (%)",                         "loc",   True),
        ("تعديل المساحة والحجم (%)",                          "area",  True),
        ("تعديل الواجهة / الإطلالة على الشارع (%)",           "front", True),
        ("تعديل الحالة القانونية والملكية (%)",               "legal", True),
        ("تعديل الإطلالة والمميزات البيئية (%)",              "view",  True),
    ]

    fINP_PCT_LAND = F(bold=False, fg="#1F78D1", sz=11, bg="#EBF3FB",
                      align="center", num_fmt="0%")
    fINP_BASE_LAND = F(bold=False, fg="#1F78D1", sz=11, bg="#EBF3FB",
                       align="center", num_fmt="#,##0")

    _field_excel_rows = {}   # field_key → Excel 1-based row
    for fi, (field_lbl, field_key, is_pct) in enumerate(_adj_field_defs):
        ws_land.write(r, 0, field_lbl, fINP_LABEL)
        _field_excel_rows[field_key] = r + 1   # Excel 1-based row
        for ci, comp in enumerate(_LAND_COMPS_ADJ):
            val = comp[field_key]
            fmt = fINP_PCT_LAND if is_pct else fINP_BASE_LAND
            ws_land.write(r, ci + 1, val, fmt)
        ws_land.write(r, 5, "", F(sz=9))
        ws_land.set_row(r, 22); r += 1

    # Sum of all adjustments row
    ws_land.write(r, 0, "مجموع التعديلات الكلي (%)", fGOLD_L)
    _adj_sum_er = r + 1   # Excel row
    for ci in range(4):
        col_letter = chr(ord("B") + ci)
        parts = "+".join(
            f"{col_letter}{_field_excel_rows[k]}"
            for k in ["time", "loc", "area", "front", "legal", "view"]
        )
        ws_land.write_formula(r, ci + 1, f"={parts}",
            F(bold=True, bg="#FFF2CC", sz=11, align="center", num_fmt="0%"))
    ws_land.set_row(r, 22); r += 1

    # Adjusted price row:  base × (1 + sum_adj)
    ws_land.write(r, 0,
        "السعر المعدَّل (EGP/م²) = الأصلي × (1 + مجموع التعديلات)", fGOLD_L)
    _adj_price_er = r + 1
    for ci in range(4):
        col_letter = chr(ord("B") + ci)
        base_er = _field_excel_rows["base"]
        ws_land.write_formula(r, ci + 1,
            f"={col_letter}{base_er}*(1+{col_letter}{_adj_sum_er})",
            F(bold=True, bg="#FFD700", fg="#000000", sz=12,
              align="center", border=2, num_fmt="#,##0"))
    ws_land.set_row(r, 28); r += 1

    # Weight row (editable)
    ws_land.write(r, 0, "الوزن النسبي للمقارنة (%) — قابل للتعديل", fINP_LABEL)
    _default_weights = [0.30, 0.25, 0.25, 0.20]
    _weight_er = r + 1
    for ci, w in enumerate(_default_weights):
        ws_land.write(r, ci + 1, w, fINP_PCT_LAND)
    ws_land.set_row(r, 22); r += 1

    # Weighted contribution row
    ws_land.write(r, 0, "المساهمة المرجحة (EGP/م²)", fLABEL)
    _contrib_er = r + 1
    for ci in range(4):
        col_letter = chr(ord("B") + ci)
        ws_land.write_formula(r, ci + 1,
            f"={col_letter}{_adj_price_er}*{col_letter}{_weight_er}", fMONEY)
    ws_land.set_row(r, 22); r += 2

    # Final weighted land value
    ws_land.write(r, 0,
        "القيمة السوقية المقدرة للأرض (متوسط مرجح) EGP/م²", fGOLD_L)
    all_contribs = "+".join(
        f"{chr(ord('B') + ci)}{_contrib_er}" for ci in range(4)
    )
    ws_land.write_formula(r, 1, f"={all_contribs}",
        F(bold=True, bg="#D4AF37", fg="#000000", sz=14,
          align="center", border=2, num_fmt="#,##0.00"))
    ws_land.merge_range(r, 2, r, 5, "← القيمة السوقية الموجَّهة لأسلوب التكلفة",
        F(italic=True, fg="#375623", sz=10, align="right"))
    ws_land.set_row(r, 32); r += 2

    # GIS / KML hyperlinks section
    r = write_section_header(ws_land, r, 0, 5,
        "روابط الموقع الجغرافي — GIS / KML  (Google Earth)")
    ws_land.write(r, 0, "انقر على الرابط للوصول لموقع المقارنة في Google Earth:", fLABEL)
    for ci, comp in enumerate(_LAND_COMPS_ADJ):
        kml_path = os.path.join(output_dir, f"land_comp_{ci + 1}.kml")
        col_letter = chr(ord("B") + ci)
        if os.path.exists(kml_path):
            ws_land.write_url(r, ci + 1,
                f"file:///{kml_path.replace(os.sep, '/')}",
                F(fg="#0563C1", sz=9, align="center"),
                string=f"KML-{ci + 1}")
        else:
            ws_land.write(r, ci + 1,
                f"KML-{ci + 1}\n{comp['desc'][:18]}",
                F(italic=True, fg="#1F78D1", sz=9, align="center", wrap=True))
    ws_land.set_row(r, 30); r += 2

    # Methodology note
    ws_land.merge_range(r, 0, r + 1, 5,
        "ملاحظة منهجية: التعديلات موجبة (+) عندما تكون المقارنة أفضل من العقار المقيَّم (يُخفَّض سعرها)، "
        "وسالبة (-) عندما تكون أدنى (يُرفَع سعرها). "
        "مجموع الأوزان يجب أن يساوي 100%. المصدر: معايير IVS 105 §50-60.",
        F(italic=True, wrap=True, sz=9, fg="#555555", bg="#F9F9F9"))
    ws_land.set_row(r, 26); ws_land.set_row(r + 1, 26)

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 15 — تقييم الأرض V2: المسار المزدوج  (Land Dual Path — optional)
    # مصفوفة مقارنات الأرض + طريقة الباقي + التوفيق بينهما
    # ══════════════════════════════════════════════════════════════════════════
    if land_dual:
        sc  = land_dual.get("sales_comparison", {})
        res = land_dual.get("residual", {})

        ws15 = wb.add_worksheet("تقييم الأرض V2 — المسار المزدوج")
        ws15.right_to_left()
        ws15.set_tab_color("#1F4E78")
        ws15.set_column("A:A", 36)
        ws15.set_column("B:H", 18)

        fS15H = F(bold=True, bg="#1F4E78", fg="#FFFFFF", sz=13, align="center")
        fS15S = F(bold=True, bg="#2E75B6", fg="#FFFFFF", sz=11)
        fS15L = F(bold=True, bg="#D9E1F2", sz=11)
        fS15V = F(sz=11, num_fmt="#,##0")
        fS15P = F(sz=11, fg="#1F4E78", bold=True)
        fS15G = F(bold=True, bg="#E2EFDA", fg="#1E5C30", sz=12, num_fmt="#,##0")
        fS15W = F(bold=True, bg="#FFF8E7", fg="#C9A64E", sz=13, num_fmt="#,##0")

        r = 0
        ws15.merge_range(r, 0, r, 7, "تقييم قيمة الأرض — المسار المزدوج (IVS-105 V2)", fS15H)
        ws15.set_row(r, 36); r += 1
        ws15.merge_range(r, 0, r, 7,
            f"الموقع: {location} | المساحة: {area:,.0f} م² | {datetime.now().strftime('%Y/%m/%d')}",
            F(sz=10, fg="#555555", italic=True, bg="#EBF3FB"))
        ws15.set_row(r, 18); r += 2

        # ─ Section A: Sales Comparison Grid ──────────────────────────────────
        ws15.merge_range(r, 0, r, 7, "القسم أ — مصفوفة مقارنات الأرض (Sales Comparison Grid)", fS15S)
        ws15.set_row(r, 24); r += 1
        hdrs = ["المقارن", "سعر/م² ج.م", "الزمن", "الموقع", "المساحة", "الواجهة", "القانوني", "السعر المعدل"]
        for ci, h in enumerate(hdrs):
            ws15.write(r, ci, h, fS15L)
        ws15.set_row(r, 20); r += 1

        grid = sc.get("grid", [])
        for comp in grid:
            adjs = list(comp.get("adjustments", {}).values())
            ws15.write(r, 0, comp.get("name", ""),                fS15P)
            ws15.write(r, 1, comp.get("base_ppm", 0),             fS15V)
            for ci, adj_val in enumerate(adjs[:6]):
                ws15.write(r, 2 + ci, adj_val, F(sz=10, align="center"))
            ws15.write(r, 7, comp.get("adjusted_ppm", 0),         fS15V)
            r += 1

        ws15.write(r, 0, "متوسط سعر الأرض/م² — مصفوفة المقارنات", fS15G)
        ws15.write(r, 1, sc.get("avg_land_ppm", 0),               fS15G)
        ws15.write(r, 7, sc.get("land_value", 0),                  fS15G)
        ws15.set_row(r, 22); r += 2

        # ─ Section B: Residual Method ─────────────────────────────────────────
        ws15.merge_range(r, 0, r, 7, "القسم ب — طريقة الباقي (Residual / Development Approach)", fS15S)
        ws15.set_row(r, 24); r += 1
        res_rows = [
            ("القيمة البيعية الإجمالية (GDV)",         res.get("gdv", 0)),
            ("المساحة الإجمالية للبناء (م²)",           res.get("saleable_area_m2", 0)),
            ("سعر الوحدة المطورة (ج.م/م²)",             res.get("sales_price_pm2", 0)),
            ("إجمالي تكلفة البناء والمقاول",             res.get("total_build_cost", 0)),
            ("الرسوم المهنية (3% من GDV)",               res.get("professional_fees", 0)),
            ("تكاليف التسويق (2% من GDV)",               res.get("marketing_costs", 0)),
            ("ربح المطور (20% من GDV)",                  res.get("developer_profit", 0)),
            ("تكاليف التمويل (18 شهر)",                  res.get("finance_cost", 0)),
        ]
        for lbl, val in res_rows:
            ws15.write(r, 0, lbl,  fS15L)
            ws15.merge_range(r, 1, r, 7, val, fS15V)
            r += 1
        ws15.write(r, 0, "✦ قيمة الأرض كباقي (Residual Land Value)",  fS15W)
        ws15.merge_range(r, 1, r, 7, res.get("land_value", 0),          fS15W)
        ws15.set_row(r, 26); r += 2

        # ─ Section C: Reconciliation ─────────────────────────────────────────
        ws15.merge_range(r, 0, r, 7, "القسم ج — التوفيق النهائي بين المسارَين", fS15S)
        ws15.set_row(r, 24); r += 1
        recon_hdrs = ["الأسلوب", "سعر الأرض/م²", "الوزن", "المساهمة الموزونة"]
        for ci, h in enumerate(recon_hdrs):
            ws15.write(r, ci, h, fS15L)
        r += 1
        ws15.write(r, 0, "مصفوفة المقارنات السوقية",    fS15P)
        ws15.write(r, 1, sc.get("avg_land_ppm", 0),      fS15V)
        ws15.write(r, 2, f"{land_dual.get('sc_weight', 0.6)*100:.0f}%",    F(sz=11, align="center"))
        ws15.write(r, 3, sc.get("avg_land_ppm", 0) * land_dual.get("sc_weight", 0.6), fS15V)
        r += 1
        ws15.write(r, 0, "طريقة الباقي",                fS15P)
        ws15.write(r, 1, res.get("avg_land_ppm", 0),     fS15V)
        ws15.write(r, 2, f"{land_dual.get('residual_weight', 0.4)*100:.0f}%", F(sz=11, align="center"))
        ws15.write(r, 3, res.get("avg_land_ppm", 0) * land_dual.get("residual_weight", 0.4), fS15V)
        r += 1
        ws15.merge_range(r, 0, r, 0, "✦ قيمة الأرض الموفّقة النهائية (ج.م/م²)", fS15W)
        ws15.write(r, 1, land_dual.get("reconciled_land_ppm", 0),  fS15W)
        ws15.write(r, 2, "100%", F(bold=True, bg="#FFF8E7", sz=11, align="center"))
        ws15.write(r, 3, land_dual.get("reconciled_land_value", 0), fS15W)
        ws15.set_row(r, 28); r += 2

        delta = land_dual.get("delta_pct", 0)
        delta_color = "#1E5C30" if delta < 15 else "#9C0006"
        ws15.merge_range(r, 0, r, 7,
            f"الفارق بين المسارَين: {delta:.1f}% — {'ضمن حدود القبول IVS (<15%)' if delta < 15 else 'تجاوز الحد المقبول — يُنصح بمراجعة المدخلات'}",
            F(italic=True, sz=10, fg=delta_color, bg="#F0F0F0"))

    # ══════════════════════════════════════════════════════════════════════════
    # Close workbook
    # ══════════════════════════════════════════════════════════════════════════
    wb.close()
    return out_path


# ─── CLI entry ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    path = generate_report(
        client_name="أحمد محمد السيد",
        property_type="شقة سكنية",
        location="المعادي، القاهرة",
        area=150, floor=3, rooms=3, year_built=2012,
        price_per_m2=18000, rent_per_sqm=350, cap_rate=0.08,
    )
    print("Generated:", path)
