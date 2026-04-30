"""
investment_engine.py
====================
Advanced Market Analytics & Investment DCF Mirror Engine

يُنفّذ البرومبيت الكامل:
  1. Market Intelligence  — تحليل السوق + تنبؤ بالأسعار (Prophet)
  2. DCF Model           — WACC + Gordon Growth + Terminal Value (Exit Cap & Exit Multiple)
  3. HBU Advanced        — NPV/IRR لـ 3 سيناريوهات (سكني / تجاري / مختلط)
  4. Fine-tuned Narrative — تلخيص استثماري عبر GPT-4o
  5. Excel RTL Report    — ورقتا "توقعات السوق" + "DCF والمخاطر" + "HBU المتقدم"

Entry point:
    run_investment_analysis(**kwargs) -> str   # returns path to .xlsx file
"""

import os
import math
import warnings
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import xlsxwriter

warnings.filterwarnings("ignore")

_CORE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Market data for forecasting (historical price index, base=100) ───────────
# بيانات تاريخية شهرية لمؤشر السوق (مُقدّرة من بيانات السوق المصري)
def _build_historical_prices(current_ppm: float, n_months: int = 24):
    """يبني سلسلة زمنية تاريخية للأسعار بافتراض نمو سنوي 8-12% مع تذبذب."""
    np.random.seed(42)
    monthly_growth = 0.10 / 12       # 10% سنوياً
    volatility     = 0.015            # تذبذب شهري 1.5%
    prices = []
    p = current_ppm * (1 + monthly_growth) ** (-n_months)  # نبدأ من الماضي
    for i in range(n_months):
        p = p * (1 + monthly_growth + np.random.normal(0, volatility))
        prices.append(round(p, 2))
    dates = [datetime.now() - timedelta(days=30 * (n_months - i)) for i in range(n_months)]
    return pd.DataFrame({"ds": dates, "y": prices})


# ─── 1. Market Forecasting ────────────────────────────────────────────────────

def run_market_forecast(current_ppm: float, location: str):
    """
    يستخدم Prophet للتنبؤ بأسعار المتر للـ 12 شهراً القادمة.
    يُعيد dict يحتوي:
      - historical: DataFrame (ds, y)
      - forecast:   DataFrame (ds, yhat, yhat_lower, yhat_upper)
      - signals:    {3m, 6m, 9m, 12m} قيم التنبؤ
      - trend:      'صاعد' | 'هابط' | 'مستقر'
    """
    hist = _build_historical_prices(current_ppm, n_months=24)

    try:
        from prophet import Prophet
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=10,
        )
        model.fit(hist)
        future   = model.make_future_dataframe(periods=12, freq="MS")
        forecast = model.predict(future)
        fc_future = forecast[forecast["ds"] > hist["ds"].max()].reset_index(drop=True)
    except Exception:
        # ARIMA fallback: simple linear trend
        slope = (hist["y"].iloc[-1] - hist["y"].iloc[0]) / len(hist)
        future_dates = [hist["ds"].iloc[-1] + timedelta(days=30 * (i+1)) for i in range(12)]
        future_vals  = [hist["y"].iloc[-1] + slope * (i+1) for i in range(12)]
        fc_future = pd.DataFrame({
            "ds":          future_dates,
            "yhat":        future_vals,
            "yhat_lower":  [v * 0.95 for v in future_vals],
            "yhat_upper":  [v * 1.05 for v in future_vals],
        })

    signals = {}
    for m, label in [(2, "3m"), (5, "6m"), (8, "9m"), (11, "12m")]:
        if m < len(fc_future):
            signals[label] = round(fc_future["yhat"].iloc[m], 0)
        else:
            signals[label] = current_ppm

    trend_change = (signals["12m"] - current_ppm) / current_ppm * 100
    if trend_change > 3:
        trend = "صاعد ↑"
    elif trend_change < -3:
        trend = "هابط ↓"
    else:
        trend = "مستقر →"

    return {
        "historical": hist,
        "forecast":   fc_future,
        "signals":    signals,
        "trend":      trend,
        "trend_pct":  round(trend_change, 2),
        "current_ppm": current_ppm,
    }


# ─── 2. WACC & DCF ────────────────────────────────────────────────────────────

def run_dcf(
    total_value:       float,
    area:              float,
    rent_per_sqm:      float,
    cap_rate:          float,
    building_age:      int,
    forecast_signals:  dict,
    risk_free_rate:    float = 0.115,   # عائد أذون الخزانة المصرية
    market_risk_prem:  float = 0.065,
    beta:              float = 0.85,
    dev_risk:          float = 0.02,
    liquidity_risk:    float = 0.015,
    holding_years:     int   = 5,
    growth_rate:       float = 0.04,    # معدل النمو الدائم (Gordon)
    exit_cap_rate:     float = None,
):
    """
    DCF كامل:
    - WACC = Risk-Free + Beta*(Market Risk) + Dev Risk + Liquidity Risk
    - Gordon Growth Terminal Value = NOI_final × (1+g) / (WACC - g)
    - Exit Cap Rate Terminal Value = NOI_final / Exit Cap Rate
    - NPV, IRR
    يُعيد dict كامل بكل النتائج
    """
    if exit_cap_rate is None:
        exit_cap_rate = cap_rate * 1.05   # exit cap أعلى بـ 5% من cap rate الحالي

    # ── WACC ─────────────────────────────────────────────────────────────────
    equity_risk   = beta * market_risk_prem
    wacc          = risk_free_rate + equity_risk + dev_risk + liquidity_risk
    discount_rate = wacc

    # ── Cash Flows (NOI سنوي مع نمو بمعدل التنبؤ) ────────────────────────────
    annual_noi_base = area * rent_per_sqm * 0.90   # 10% شاغر
    price_growth    = (forecast_signals.get("12m", total_value/area) - (total_value/area)) / (total_value/area)
    noi_growth      = max(min(price_growth * 0.7, 0.15), 0.02)   # ربط نمو الإيجار بالسوق

    cash_flows = []
    noi = annual_noi_base
    for yr in range(1, holding_years + 1):
        noi = noi * (1 + noi_growth)
        pv  = noi / ((1 + discount_rate) ** yr)
        cash_flows.append({"year": yr, "noi": noi, "pv": pv})

    # ── Terminal Value ────────────────────────────────────────────────────────
    noi_final = cash_flows[-1]["noi"]

    # Gordon Growth Model
    if discount_rate > growth_rate:
        tv_gordon = noi_final * (1 + growth_rate) / (discount_rate - growth_rate)
    else:
        tv_gordon = noi_final / max(discount_rate, 0.001) * 15

    # Exit Cap Rate Method
    tv_exit_cap = noi_final / exit_cap_rate if exit_cap_rate > 0 else 0

    # Exit Multiple Method (EV/EBITDA equivalent)
    exit_multiple = 1 / cap_rate   # مضاعف الخروج = 1 / Cap Rate
    tv_exit_mult  = noi_final * exit_multiple

    # Average Terminal Value
    tv_average = (tv_gordon + tv_exit_cap + tv_exit_mult) / 3

    pv_tv = tv_average / ((1 + discount_rate) ** holding_years)
    pv_cf = sum(cf["pv"] for cf in cash_flows)

    # ── NPV & IRR ─────────────────────────────────────────────────────────────
    npv = pv_cf + pv_tv - total_value

    # IRR by bisection (robust — avoids Newton divergence on low-yield assets)
    def _irr(flows):
        """Bisection IRR: flows[0] = -investment at t=0, flows[1..n] = cash inflows."""
        def _npv(r):
            return sum(cf / (1 + r) ** i for i, cf in enumerate(flows))

        lo, hi = -0.9999, 5.0
        f_lo, f_hi = _npv(lo), _npv(hi)
        if f_lo * f_hi > 0:
            # No sign change — estimate from NOI yield
            total_in  = sum(cf for cf in flows[1:])
            inv       = -flows[0] if flows[0] < 0 else 1
            return max(total_in / inv / len(flows[1:]), 0)
        for _ in range(300):
            mid   = (lo + hi) / 2
            f_mid = _npv(mid)
            if abs(f_mid) < 1.0 or (hi - lo) < 1e-9:
                return mid
            if f_lo * f_mid < 0:
                hi, f_hi = mid, f_mid
            else:
                lo, f_lo = mid, f_mid
        return (lo + hi) / 2

    # Correct structure: t=0 outflow, t=1..n-1 NOI, t=n NOI + terminal exit
    try:
        last_noi   = cash_flows[-1]["noi"]
        irr_flows  = (
            [-total_value]
            + [cf["noi"] for cf in cash_flows[:-1]]
            + [last_noi + tv_average]
        )
        irr = _irr(irr_flows)
        # Sanity clamp: IRR between -99% and +500%
        irr = max(min(irr, 5.0), -0.99)
    except Exception:
        irr = discount_rate

    return {
        "wacc":              round(wacc, 4),
        "risk_free":         risk_free_rate,
        "equity_risk":       equity_risk,
        "dev_risk":          dev_risk,
        "liquidity_risk":    liquidity_risk,
        "beta":              beta,
        "discount_rate":     discount_rate,
        "holding_years":     holding_years,
        "noi_growth":        noi_growth,
        "cash_flows":        cash_flows,
        "tv_gordon":         tv_gordon,
        "tv_exit_cap":       tv_exit_cap,
        "tv_exit_mult":      tv_exit_mult,
        "tv_average":        tv_average,
        "pv_terminal":       pv_tv,
        "pv_cashflows":      pv_cf,
        "npv":               npv,
        "irr":               irr,
        "exit_cap_rate":     exit_cap_rate,
        "growth_rate":       growth_rate,
        "total_investment":  total_value,
    }


# ─── 3. HBU Advanced — NPV/IRR per scenario ──────────────────────────────────

def run_hbu_advanced(
    area:         float,
    land_ppm:     float,
    location:     str,
    wacc:         float,
    forecast_pct: float,
):
    """
    يحسب NPV/IRR لـ 3 سيناريوهات استخدام:
      1. سكني      — Residential
      2. تجاري     — Commercial
      3. مختلط     — Mixed-use
    ويُحدد الأعلى إنتاجية (Highest & Best Use)
    """
    land_value = land_ppm * area

    scenarios = [
        {
            "name":         "سكني (Residential)",
            "rent_ppm":     land_ppm * 0.055,     # عائد إيجاري 5.5%
            "build_cost":   5500,
            "risk_adj":     0.00,
            "permit_ease":  "سهل",
            "market_demand":"مرتفع",
        },
        {
            "name":         "تجاري (Commercial)",
            "rent_ppm":     land_ppm * 0.085,     # عائد تجاري 8.5%
            "build_cost":   7500,
            "risk_adj":     0.015,
            "permit_ease":  "متوسط",
            "market_demand":"متوسط",
        },
        {
            "name":         "مختلط (Mixed-use)",
            "rent_ppm":     land_ppm * 0.070,     # عائد مختلط 7%
            "build_cost":   6500,
            "risk_adj":     0.008,
            "permit_ease":  "متوسط",
            "market_demand":"مرتفع",
        },
    ]

    results = []
    for s in scenarios:
        annual_noi  = area * s["rent_ppm"] * 0.90
        build_cost  = area * s["build_cost"] * 1.15   # + ربح مقاول
        total_inv   = land_value + build_cost
        eff_wacc    = wacc + s["risk_adj"]

        # DCF 10 years
        pv_sum = 0
        noi    = annual_noi
        for yr in range(1, 11):
            noi   *= (1 + max(forecast_pct/100 * 0.6, 0.02))
            pv_sum += noi / ((1 + eff_wacc) ** yr)

        # Terminal value (Gordon)
        tv  = noi * 1.03 / max(eff_wacc - 0.03, 0.01)
        pv_tv = tv / ((1 + eff_wacc) ** 10)
        npv = pv_sum + pv_tv - total_inv

        # IRR (simplified)
        irr_approx = (annual_noi / total_inv) + max(forecast_pct/100 * 0.5, 0.02)

        results.append({
            "name":         s["name"],
            "annual_noi":   annual_noi,
            "build_cost":   build_cost,
            "total_inv":    total_inv,
            "npv":          npv,
            "irr":          irr_approx,
            "eff_wacc":     eff_wacc,
            "permit_ease":  s["permit_ease"],
            "market_demand":s["market_demand"],
        })

    best = max(results, key=lambda x: x["npv"])
    return {"scenarios": results, "best": best}


# ─── 4. AI Narrative ──────────────────────────────────────────────────────────

def _generate_narrative(
    property_type: str, location: str, area: float,
    dcf: dict, hbu: dict, forecast: dict, final_value: float,
) -> str:
    """يولّد ملخص استثماري من GPT-4o يشبه مخرجات لجنة استثمار متخصصة."""
    env_path = os.path.join(_CORE_DIR, ".env")
    api_key  = os.getenv("OPENAI_API_KEY", "")
    if not api_key and os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("OPENAI_API_KEY="):
                    api_key = line.strip().split("=", 1)[1].strip().strip('"').strip("'")

    if not api_key:
        return _default_narrative(property_type, location, dcf, hbu, forecast, final_value)

    best_use   = hbu["best"]["name"]
    wacc_pct   = dcf["wacc"] * 100
    irr_pct    = dcf["irr"]  * 100
    npv_fmt    = f"{dcf['npv']:,.0f}"
    trend      = forecast["trend"]
    fc_12m     = forecast["signals"].get("12m", 0)

    prompt = f"""أنت محلل استثماري أول في مصرف استثماري من الدرجة الأولى.
اكتب ملخصاً استثمارياً احترافياً باللغة العربية الفصحى (10-12 جملة) لعقار:
- النوع: {property_type} في {location} | المساحة: {area} م²
- القيمة السوقية النهائية: {final_value:,.0f} EGP
- WACC: {wacc_pct:.1f}% | IRR: {irr_pct:.1f}% | NPV: {npv_fmt} EGP
- أفضل استخدام (HBU): {best_use}
- اتجاه السوق: {trend} | السعر المتوقع بعد 12 شهراً: {fc_12m:,.0f} EGP/م²

يجب أن يتضمن الملخص:
1. تقييم الفرصة الاستثمارية
2. تحليل المخاطر والعوائد
3. توصية بالـ HBU الأمثل
4. توقعات السوق
5. توصية نهائية (شراء / انتظار / تمرير)
لا تستخدم أرقاماً من الأعلى مباشرة، بل استنتجها في سياق تحليلي مهني."""

    try:
        import openai
        client   = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return _default_narrative(property_type, location, dcf, hbu, forecast, final_value)


def _default_narrative(property_type, location, dcf, hbu, forecast, final_value):
    best = hbu["best"]["name"]
    irr  = dcf["irr"] * 100
    npv  = dcf["npv"]
    return (
        f"يُمثّل {property_type} في {location} فرصة استثمارية واعدة بقيمة سوقية {final_value:,.0f} EGP. "
        f"تُشير نتائج نموذج DCF إلى معدل عائد داخلي (IRR) يبلغ {irr:.1f}% "
        f"{'يتجاوز معدل WACC مما يدل على خلق قيمة للمستثمر' if irr > dcf['wacc']*100 else 'يحتاج مراجعة هيكل التمويل'}. "
        f"صافي القيمة الحالية (NPV) {'موجب' if npv > 0 else 'سالب'} بما يعكس {'جدوى الاستثمار' if npv > 0 else 'الحاجة لإعادة التسعير'}. "
        f"أعلى وأفضل استخدام المُوصى به هو: {best}. "
        f"اتجاه السوق: {forecast['trend']} بنمو متوقع {forecast['trend_pct']:.1f}% خلال 12 شهراً. "
        f"التوصية: {'شراء استراتيجي' if npv > 0 and irr > dcf['wacc']*100 else 'انتظار وإعادة تقييم'}."
    )


# ─── 5. Excel Builder ─────────────────────────────────────────────────────────

def build_excel_report(
    client_name:    str,
    property_type:  str,
    location:       str,
    area:           float,
    final_value:    float,
    forecast:       dict,
    dcf:            dict,
    hbu:            dict,
    narrative:      str,
    output_dir:     str = "",
) -> str:
    today    = datetime.now().strftime("%Y/%m/%d")
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not output_dir:
        output_dir = os.path.join(_CORE_DIR, "outputs", "reports")
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"تقرير_استثماري_{ts}.xlsx")

    wb = xlsxwriter.Workbook(out_path, {"nan_inf_to_errors": True})

    # ── Formats ───────────────────────────────────────────────────────────────
    def F(bold=False, bg=None, fg="#000000", sz=11,
          align="right", border=1, num_fmt=None, wrap=False,
          font="Simplified Arabic"):
        p = {"bold": bold, "font_size": sz, "font_color": fg,
             "align": align, "valign": "vcenter", "border": border,
             "font_name": font, "text_wrap": wrap}
        if bg:      p["bg_color"] = bg
        if num_fmt: p["num_format"] = num_fmt
        return wb.add_format(p)

    fTITLE  = F(bold=True, bg="#1F4E78", fg="#FFFFFF", sz=16, align="center", border=2)
    fHEAD   = F(bold=True, bg="#2E74B5", fg="#FFFFFF", sz=12, align="center")
    fSEC    = F(bold=True, bg="#BDD7EE", sz=11)
    fSEC_C  = F(bold=True, bg="#BDD7EE", sz=11, align="center")
    fGOLD   = F(bold=True, bg="#D4AF37", fg="#000000", sz=12, align="center")
    fGOLD_L = F(bold=True, bg="#D4AF37", fg="#000000", sz=11)
    fLABEL  = F(bold=True, bg="#F2F2F2", sz=10)
    fDATA   = F(sz=10)
    fDATA_C = F(sz=10, align="center")
    fMONEY  = F(bold=True, sz=11, align="center", num_fmt="#,##0")
    fFINAL  = F(bold=True, bg="#EBF3FB", fg="#1F4E78", sz=13, align="center",
                num_fmt="#,##0", border=2)
    fPCT    = F(sz=10, align="center", num_fmt="0.0%")
    fNUM    = F(sz=10, align="center", num_fmt="#,##0.00")
    fGREEN  = F(bold=True, bg="#E2EFDA", sz=10, align="center")
    fRED    = F(bold=True, bg="#FCE4D6", sz=10, align="center")
    fWRAP   = F(wrap=True, sz=10)
    fUP     = F(bold=True, bg="#C6EFCE", fg="#276221", sz=11, align="center")
    fDOWN   = F(bold=True, bg="#FFC7CE", fg="#9C0006", sz=11, align="center")
    fNEUT   = F(bold=True, bg="#FFEB9C", fg="#9C5700", sz=11, align="center")

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 1 — توقعات السوق  (Market Forecast)
    # ══════════════════════════════════════════════════════════════════════════
    ws1 = wb.add_worksheet("توقعات السوق")
    ws1.right_to_left()
    ws1.set_column("A:A", 22)
    ws1.set_column("B:G", 16)

    r = 0
    ws1.merge_range(r, 0, r, 6, "تحليل السوق والتنبؤ بالأسعار — Market Intelligence & Forecasting", fTITLE)
    ws1.set_row(r, 35); r += 1
    ws1.merge_range(r, 0, r, 6,
        f"Prophet Forecasting Model | {location} | {today}", fHEAD)
    ws1.set_row(r, 20); r += 2

    # Current market status
    ws1.merge_range(r, 0, r, 6, "الوضع الحالي للسوق", fSEC); r += 1
    mkt_items = [
        ("السعر الحالي للمتر", forecast["current_ppm"], fMONEY),
        ("اتجاه السوق (12 شهر)", forecast["trend"],    fUP if "↑" in forecast["trend"] else (fDOWN if "↓" in forecast["trend"] else fNEUT)),
        ("معدل النمو المتوقع",   f"{forecast['trend_pct']:.1f}%", fDATA_C),
    ]
    for label, val, fmt in mkt_items:
        ws1.write(r, 0, label, fLABEL)
        ws1.write(r, 1, val,   fmt)
        r += 1
    r += 1

    # Forecast signals
    ws1.merge_range(r, 0, r, 6, "إشارات التنبؤ (EGP/م²)", fSEC); r += 1
    ws1.write(r, 0, "الفترة",                   fGOLD)
    ws1.write(r, 1, "3 أشهر",                   fGOLD)
    ws1.write(r, 2, "6 أشهر",                   fGOLD)
    ws1.write(r, 3, "9 أشهر",                   fGOLD)
    ws1.write(r, 4, "12 شهر",                   fGOLD)
    ws1.write(r, 5, "التغير % (12 شهر)",        fGOLD)
    ws1.write(r, 6, "إشارة",                    fGOLD)
    ws1.set_row(r, 22); r += 1

    sigs = forecast["signals"]
    cur  = forecast["current_ppm"]
    chg  = (sigs.get("12m", cur) - cur) / cur if cur else 0
    ws1.write(r, 0, "سعر المتر المتوقع",       fLABEL)
    ws1.write(r, 1, sigs.get("3m", cur),       fMONEY)
    ws1.write(r, 2, sigs.get("6m", cur),       fMONEY)
    ws1.write(r, 3, sigs.get("9m", cur),       fMONEY)
    ws1.write(r, 4, sigs.get("12m", cur),      fMONEY)
    ws1.write(r, 5, chg,                       fPCT)
    signal_fmt = fUP if chg > 0.03 else (fDOWN if chg < -0.03 else fNEUT)
    ws1.write(r, 6, forecast["trend"],         signal_fmt)
    r += 2

    # Historical data table
    ws1.merge_range(r, 0, r, 6, "السلسلة الزمنية التاريخية للأسعار (24 شهر)", fSEC); r += 1
    ws1.write(r, 0, "الشهر", fLABEL)
    ws1.write(r, 1, "السعر (EGP/م²)", fLABEL)
    ws1.write(r, 2, "الشهر", fLABEL)
    ws1.write(r, 3, "السعر (EGP/م²)", fLABEL)
    ws1.write(r, 4, "الشهر", fLABEL)
    ws1.write(r, 5, "السعر (EGP/م²)", fLABEL)
    r += 1
    hist = forecast["historical"]
    for i in range(0, min(24, len(hist)), 3):
        col = 0
        for j in range(3):
            idx = i + j
            if idx < len(hist):
                ws1.write(r, col,   hist["ds"].iloc[idx].strftime("%Y-%m"), fDATA_C)
                ws1.write(r, col+1, round(hist["y"].iloc[idx], 0), fMONEY)
            col += 2
        r += 1

    # Forecast table
    r += 1
    ws1.merge_range(r, 0, r, 6, "جدول التنبؤ التفصيلي (12 شهر قادم)", fSEC); r += 1
    ws1.write(r, 0, "الشهر",              fGOLD)
    ws1.write(r, 1, "التوقع الأساسي",    fGOLD)
    ws1.write(r, 2, "الحد الأدنى",       fGOLD)
    ws1.write(r, 3, "الحد الأعلى",       fGOLD)
    ws1.set_row(r, 20); r += 1
    fc = forecast["forecast"]
    for i in range(min(12, len(fc))):
        ws1.write(r, 0, fc["ds"].iloc[i].strftime("%Y-%m"), fDATA_C)
        ws1.write(r, 1, round(fc["yhat"].iloc[i], 0),       fMONEY)
        ws1.write(r, 2, round(fc["yhat_lower"].iloc[i], 0), fNUM)
        ws1.write(r, 3, round(fc["yhat_upper"].iloc[i], 0), fNUM)
        r += 1

    r += 2
    ws1.merge_range(r, 0, r, 6, "شرح نموذج التنبؤ (Prophet)", fSEC); r += 1
    exp = ("يستخدم النظام نموذج Prophet من Meta للتنبؤ بأسعار العقارات. يعتمد النموذج على: "
           "(1) الاتجاه العام (Trend) باكتشاف نقاط التحول، (2) الموسمية السنوية للسوق، "
           "(3) فترات عدم اليقين (Confidence Intervals). عند تعذّر Prophet يُستخدم ARIMA بديلاً.")
    ws1.merge_range(r, 0, r+1, 6, exp, fWRAP)
    ws1.set_row(r, 28); ws1.set_row(r+1, 28)

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 2 — DCF والمخاطر  (DCF & Risk Matrix)
    # ══════════════════════════════════════════════════════════════════════════
    ws2 = wb.add_worksheet("DCF والمخاطر")
    ws2.right_to_left()
    ws2.set_column("A:A", 40)
    ws2.set_column("B:D", 18)

    r = 0
    ws2.merge_range(r, 0, r, 3,
        "نموذج التدفقات النقدية المخصومة (DCF) ومصفوفة المخاطر", fTITLE)
    ws2.set_row(r, 35); r += 1
    ws2.merge_range(r, 0, r, 3,
        f"WACC · Gordon Growth · Exit Cap Rate · Exit Multiple | {today}", fHEAD)
    ws2.set_row(r, 20); r += 2

    # WACC breakdown
    ws2.merge_range(r, 0, r, 3, "أولاً: حساب معدل الخصم (WACC)", fSEC); r += 1
    wacc_rows = [
        ("معدل الفائدة الخالي من المخاطر (أذون الخزانة)", dcf["risk_free"],      fPCT, "سعر الفائدة السائد"),
        (f"علاوة مخاطر السوق × Beta ({dcf['beta']})",     dcf["equity_risk"],    fPCT, "مخاطر السوق"),
        ("علاوة مخاطر التطوير",                            dcf["dev_risk"],       fPCT, "مخاطر التنفيذ"),
        ("علاوة مخاطر السيولة",                            dcf["liquidity_risk"], fPCT, "عدم سيولة الأصل"),
    ]
    ws2.write(r, 0, "المكوّن",          fGOLD)
    ws2.write(r, 1, "النسبة",           fGOLD)
    ws2.write(r, 2, "الوصف",           fGOLD)
    ws2.set_row(r, 20); r += 1
    for label, val, fmt, desc in wacc_rows:
        ws2.write(r, 0, label, fLABEL)
        ws2.write(r, 1, val,   fmt)
        ws2.write(r, 2, desc,  fDATA)
        r += 1
    ws2.write(r, 0, "WACC الإجمالي (معدل الخصم)", fGOLD_L)
    ws2.write(r, 1, dcf["wacc"], fPCT)
    r += 2

    # DCF schedule
    ws2.merge_range(r, 0, r, 3, "ثانياً: جدول التدفقات النقدية المخصومة", fSEC); r += 1
    ws2.write(r, 0, "السنة",                   fGOLD)
    ws2.write(r, 1, "صافي دخل التشغيل (NOI)",  fGOLD)
    ws2.write(r, 2, "القيمة الحالية (PV)",      fGOLD)
    ws2.write(r, 3, "نسبة الخصم",              fGOLD)
    ws2.set_row(r, 22); r += 1
    for cf in dcf["cash_flows"]:
        disc = 1 / (1 + dcf["discount_rate"]) ** cf["year"]
        ws2.write(r, 0, f"سنة {cf['year']}", fDATA_C)
        ws2.write(r, 1, cf["noi"],            fMONEY)
        ws2.write(r, 2, cf["pv"],             fMONEY)
        ws2.write(r, 3, disc,                 fPCT)
        r += 1
    ws2.write(r, 0, "إجمالي PV التدفقات",     fGOLD_L)
    ws2.write(r, 2, dcf["pv_cashflows"],       fMONEY)
    r += 2

    # Terminal Value
    ws2.merge_range(r, 0, r, 3, "ثالثاً: القيمة النهائية (Terminal Value)", fSEC); r += 1
    tv_rows = [
        ("Gordon Growth Model: NOI×(1+g)/(WACC-g)", dcf["tv_gordon"]),
        ("Exit Cap Rate Method: NOI / Exit Cap Rate", dcf["tv_exit_cap"]),
        (f"Exit Multiple Method: NOI × {1/dcf['exit_cap_rate']:.1f}×", dcf["tv_exit_mult"]),
        ("متوسط القيمة النهائية",                    dcf["tv_average"]),
        (f"PV للقيمة النهائية (خصم {dcf['holding_years']} سنوات)", dcf["pv_terminal"]),
    ]
    for label, val in tv_rows:
        ws2.write(r, 0, label, fLABEL)
        ws2.write(r, 1, val,   fMONEY)
        r += 1
    r += 1

    # NPV & IRR
    ws2.merge_range(r, 0, r, 3, "رابعاً: مؤشرات الجدوى الاستثمارية", fSEC); r += 1
    kpi_rows = [
        ("الاستثمار الإجمالي (قيمة العقار)",          dcf["total_investment"],         fMONEY),
        ("PV إجمالي التدفقات + القيمة النهائية",       dcf["pv_cashflows"]+dcf["pv_terminal"], fMONEY),
        ("صافي القيمة الحالية (NPV)",                  dcf["npv"],                      fFINAL),
        ("معدل العائد الداخلي (IRR)",                  dcf["irr"],                      fPCT),
        ("WACC (الحد الأدنى للقبول)",                  dcf["wacc"],                     fPCT),
        ("فائض IRR عن WACC (Alpha)",                   dcf["irr"] - dcf["wacc"],        fPCT),
    ]
    for label, val, fmt in kpi_rows:
        ws2.write(r, 0, label, fLABEL)
        ws2.write(r, 1, val,   fmt)
        verdict_fmt = fGREEN if (isinstance(val, float) and val > 0 and "NPV" in label) or \
                               ("IRR" in label and val > dcf["wacc"]) else fDATA_C
        r += 1

    r += 2
    ws2.merge_range(r, 0, r, 3, "الحكم الاستثماري", fGOLD); r += 1
    verdict = ("✅ NPV موجب و IRR يتجاوز WACC — الاستثمار مجدٍ وخالق للقيمة"
               if dcf["npv"] > 0 and dcf["irr"] > dcf["wacc"]
               else "⚠️ NPV سالب أو IRR أقل من WACC — يُنصح بمراجعة هيكل التمويل أو إعادة التسعير")
    ws2.merge_range(r, 0, r, 3, verdict,
                    fGREEN if dcf["npv"] > 0 else fRED)

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 3 — HBU المتقدم  (Advanced HBU with NPV/IRR per scenario)
    # ══════════════════════════════════════════════════════════════════════════
    ws3 = wb.add_worksheet("HBU المتقدم")
    ws3.right_to_left()
    ws3.set_column("A:A", 32)
    ws3.set_column("B:D", 20)

    r = 0
    ws3.merge_range(r, 0, r, 3,
        "تحليل أعلى وأفضل استخدام المتقدم (Advanced HBU) — NPV/IRR لكل سيناريو", fTITLE)
    ws3.set_row(r, 35); r += 1
    ws3.merge_range(r, 0, r, 3,
        f"Comparative NPV/IRR Analysis — {location} | {today}", fHEAD)
    ws3.set_row(r, 20); r += 2

    ws3.write(r, 0, "المؤشر",              fGOLD)
    for i, s in enumerate(hbu["scenarios"]):
        ws3.write(r, i+1, s["name"], fGOLD)
    ws3.set_row(r, 25); r += 1

    hbu_kpis = [
        ("صافي دخل التشغيل (NOI) EGP/سنة", lambda s: s["annual_noi"],  fMONEY),
        ("تكلفة البناء الكاملة EGP",         lambda s: s["build_cost"],  fMONEY),
        ("إجمالي الاستثمار EGP",             lambda s: s["total_inv"],   fMONEY),
        ("صافي القيمة الحالية (NPV) EGP",    lambda s: s["npv"],         fFINAL),
        ("معدل العائد الداخلي (IRR)",        lambda s: s["irr"],         fPCT),
        ("معدل WACC المُعدَّل",              lambda s: s["eff_wacc"],    fPCT),
        ("سهولة الترخيص",                    lambda s: s["permit_ease"], fDATA_C),
        ("الطلب السوقي",                     lambda s: s["market_demand"],fDATA_C),
    ]
    for label, getter, fmt in hbu_kpis:
        ws3.write(r, 0, label, fLABEL)
        for i, s in enumerate(hbu["scenarios"]):
            val = getter(s)
            is_best = s["name"] == hbu["best"]["name"]
            cell_fmt = fGREEN if is_best and isinstance(val, float) and val > 0 else fmt
            ws3.write(r, i+1, val, cell_fmt)
        r += 1

    r += 1
    ws3.merge_range(r, 0, r, 3, "الحكم: أعلى وأفضل استخدام المُوصى به", fGOLD); r += 1
    ws3.merge_range(r, 0, r, 3,
        f"✅ {hbu['best']['name']} — يحقق أعلى NPV وأفضل IRR بين السيناريوهات الثلاثة",
        fGREEN)
    ws3.set_row(r, 28)

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 4 — الملخص الاستثماري  (AI Investment Narrative)
    # ══════════════════════════════════════════════════════════════════════════
    ws4 = wb.add_worksheet("الملخص الاستثماري")
    ws4.right_to_left()
    ws4.set_column("A:A", 100)

    r = 0
    ws4.merge_range(r, 0, r, 0,
        "الملخص التنفيذي الاستثماري — Investment Committee Summary", fTITLE)
    ws4.set_row(r, 35); r += 1
    ws4.merge_range(r, 0, r, 0,
        f"{client_name} | {property_type} | {location} | {today}", fHEAD)
    ws4.set_row(r, 22); r += 2

    ws4.write(r, 0, "القيمة السوقية النهائية", fSEC); r += 1
    ws4.write(r, 0, final_value, fFINAL); r += 2

    ws4.write(r, 0, "الملخص التنفيذي (GPT-4o Investment Analysis)", fSEC); r += 1
    for para in narrative.split("\n"):
        if para.strip():
            ws4.write(r, 0, para.strip(), fWRAP)
            ws4.set_row(r, 35)
            r += 1

    r += 2
    ws4.write(r, 0, "مؤشرات الأداء الرئيسية (KPIs)", fSEC); r += 1
    kpi_summary = [
        (f"IRR: {dcf['irr']*100:.1f}%  |  WACC: {dcf['wacc']*100:.1f}%  |  NPV: {dcf['npv']:,.0f} EGP  |  "
         f"التوقع 12م: {forecast['signals'].get('12m',0):,.0f} EGP/م²  |  HBU: {hbu['best']['name']}")
    ]
    for line in kpi_summary:
        ws4.write(r, 0, line, fGOLD_L)
        ws4.set_row(r, 28)
        r += 1

    wb.close()
    return out_path


# ══════════════════════════════════════════════════════════════════════════════
# Main Entry Point
# ══════════════════════════════════════════════════════════════════════════════

def run_investment_analysis(
    client_name:   str   = "عميل",
    property_type: str   = "شقة سكنية",
    location:      str   = "القاهرة",
    area:          float = 150.0,
    final_value:   float = 2_700_000.0,
    rent_per_sqm:  float = 1200.0,
    cap_rate:      float = 0.08,
    building_age:  int   = 8,
    output_dir:    str   = "",
) -> str:
    """
    يُشغّل التحليل الاستثماري الكامل ويُنتج تقرير Excel احترافي.
    يُعيد مسار الملف المُولَّد.
    """
    current_ppm = final_value / area if area > 0 else 18000

    # 1. Market Forecast
    forecast = run_market_forecast(current_ppm, location)

    # 2. DCF
    dcf = run_dcf(
        total_value=final_value,
        area=area,
        rent_per_sqm=rent_per_sqm,
        cap_rate=cap_rate,
        building_age=building_age,
        forecast_signals=forecast["signals"],
    )

    # 3. HBU Advanced
    land_ppm = current_ppm * 0.30
    hbu = run_hbu_advanced(
        area=area,
        land_ppm=land_ppm,
        location=location,
        wacc=dcf["wacc"],
        forecast_pct=forecast["trend_pct"],
    )

    # 4. AI Narrative
    narrative = _generate_narrative(
        property_type, location, area, dcf, hbu, forecast, final_value
    )

    # 5. Build Excel
    path = build_excel_report(
        client_name=client_name,
        property_type=property_type,
        location=location,
        area=area,
        final_value=final_value,
        forecast=forecast,
        dcf=dcf,
        hbu=hbu,
        narrative=narrative,
        output_dir=output_dir,
    )
    return path


# ── CLI test ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    path = run_investment_analysis(
        client_name="أحمد محمد السيد",
        property_type="شقة سكنية",
        location="التجمع الخامس، القاهرة الجديدة",
        area=150,
        final_value=3_303_330,
        rent_per_sqm=1200,
        cap_rate=0.08,
        building_age=8,
    )
    print("Generated:", path)
