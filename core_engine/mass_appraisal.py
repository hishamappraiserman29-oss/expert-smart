"""
mass_appraisal.py
=================
Mass Appraisal Engine (AVM — Automated Valuation Model)
---------------------------------------------------------
Supports valuation of large portfolios (100+ units) using:
  1. Hedonic Regression (OLS) — statistical AVM
  2. Comparable Sales Grid   — adjusted market comps per unit
  3. Ratio Study             — uniformity / equity metrics (COD, PRD)

Tadawul / REIT portfolio compatibility: outputs per-unit table
suitable for regulatory disclosure.

Usage:
    from mass_appraisal import run_mass_appraisal
    results = run_mass_appraisal(units_df_or_list)
"""
from __future__ import annotations
import math
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

# ─── AVM Model coefficients (pre-trained on _SPATIAL_COMPS) ──────────────────
# Hedonic model: price_pm2 = β0 + β1·floor + β2·area + β3·year_built
# Coefficients from OLS in valuation_logic.py (r² ≈ 0.83)
_AVM_COEF = {
    "const":      25_000.0,   # intercept
    "floor":      -120.0,     # higher floor → slight discount
    "area":       -25.0,      # larger area → slight discount per m²
    "year_built":  30.0,      # newer → higher price
}

# ─── Ratio study thresholds (IAAO standards) ──────────────────────────────────
IAAO_COD_MAX   = 15.0   # COD should be < 15% for residential
IAAO_PRD_RANGE = (0.98, 1.03)


def _avm_predict(floor: float, area: float, year_built: float) -> float:
    """Hedonic OLS prediction of price per m²."""
    pred = (
        _AVM_COEF["const"] +
        _AVM_COEF["floor"]      * floor +
        _AVM_COEF["area"]       * area  +
        _AVM_COEF["year_built"] * year_built
    )
    return max(pred, 5_000.0)


def _market_adjustment(base_ppm: float, unit: Dict, market_ppm: float) -> float:
    """Apply location + condition adjustments relative to market."""
    condition_adj = {"new": 1.05, "excellent": 1.02, "good": 1.00,
                     "fair": 0.95, "poor": 0.88}.get(
        unit.get("condition", "good").lower(), 1.0)
    view_adj = 1.03 if unit.get("sea_view") or unit.get("pool_view") else 1.0
    corner_adj = 1.02 if unit.get("corner") else 1.0
    return base_ppm * condition_adj * view_adj * corner_adj


def run_mass_appraisal(
    units: List[Dict],
    base_market_ppm: float = 0.0,
    location: str = "Cairo",
    region: str = "EG",
    method: str = "avm",        # "avm" | "comparable" | "both"
    purpose: str = "fair_market",
    output_dir: str = "",
) -> Dict:
    """
    Mass appraisal for a portfolio of properties.

    Each unit dict must contain:
      id, area, floor, year_built (required)
      Optional: condition, sea_view, corner, sale_price (for ratio study)

    Returns:
    {
      "n_units": int,
      "total_portfolio_value": float,
      "avg_ppm": float,
      "units": [...per-unit results...],
      "ratio_study": {...IAAO metrics...},
      "portfolio_summary": {...},
      "output_xlsx": str (path to Excel output)
    }
    """
    if not units:
        return {"error": "No units provided"}

    mul = 2.5 if region.upper() == "SA" else 1.0

    # Purpose discount
    _disc = {"fair_market": 0, "liquidation": 0.20, "taxation": 0.10, "usufruct": 0}
    disc  = _disc.get(purpose, 0)

    results = []
    for u in units:
        uid        = u.get("id", f"UNIT-{len(results)+1:04d}")
        area       = float(u.get("area", 100))
        floor      = float(u.get("floor", 1))
        year_built = float(u.get("year_built", 2010))

        # AVM prediction
        avm_ppm = _avm_predict(floor, area, year_built) * mul

        # Optional market adjustment
        mkt_ppm = float(base_market_ppm) * mul if base_market_ppm > 0 else avm_ppm
        adj_ppm = _market_adjustment(avm_ppm, u, mkt_ppm)

        if method == "avm":
            final_ppm = avm_ppm
        elif method == "comparable":
            final_ppm = adj_ppm
        else:
            final_ppm = (avm_ppm * 0.60 + adj_ppm * 0.40)

        final_ppm  *= (1 - disc)
        unit_value  = final_ppm * area

        row = {
            "id":            uid,
            "floor":         floor,
            "area":          area,
            "year_built":    int(year_built),
            "condition":     u.get("condition", "good"),
            "avm_ppm":       round(avm_ppm, 0),
            "adj_ppm":       round(adj_ppm, 0),
            "final_ppm":     round(final_ppm, 0),
            "unit_value":    round(unit_value, 0),
            "sale_price":    u.get("sale_price", 0),
        }
        results.append(row)

    # ── Portfolio Summary ──────────────────────────────────────────────────────
    total_value = sum(r["unit_value"] for r in results)
    avg_ppm     = total_value / sum(r["area"] for r in results) if results else 0

    # ── Ratio Study (IAAO) ────────────────────────────────────────────────────
    sold_units = [r for r in results if r["sale_price"] > 0]
    ratio_study = _ratio_study(sold_units) if sold_units else {"n_sales": 0}

    # ── Statistics ────────────────────────────────────────────────────────────
    values = [r["unit_value"] for r in results]
    ppms   = [r["final_ppm"] for r in results]
    p_summary = {
        "min_value":  round(min(values), 0),
        "max_value":  round(max(values), 0),
        "median_val": round(sorted(values)[len(values)//2], 0),
        "min_ppm":    round(min(ppms), 0),
        "max_ppm":    round(max(ppms), 0),
        "median_ppm": round(sorted(ppms)[len(ppms)//2], 0),
        "std_ppm":    round(math.sqrt(sum((p - avg_ppm)**2 for p in ppms) / max(len(ppms)-1, 1)), 0),
    }

    # ── Export to Excel ───────────────────────────────────────────────────────
    xlsx_path = _export_xlsx(results, total_value, avg_ppm, ratio_study,
                             p_summary, location, purpose, output_dir)

    return {
        "n_units":               len(results),
        "total_portfolio_value": round(total_value, 0),
        "avg_ppm":               round(avg_ppm, 0),
        "method":                method,
        "purpose":               purpose,
        "discount_applied":      f"{disc*100:.0f}%",
        "location":              location,
        "units":                 results,
        "ratio_study":           ratio_study,
        "portfolio_summary":     p_summary,
        "output_xlsx":           xlsx_path,
    }


def _ratio_study(sold_units: List[Dict]) -> Dict:
    """IAAO ratio study: COD, PRD, PRB."""
    ratios = [r["unit_value"] / r["sale_price"] for r in sold_units if r["sale_price"] > 0]
    if not ratios:
        return {"n_sales": 0}

    n     = len(ratios)
    med   = sorted(ratios)[n // 2]
    mean  = sum(ratios) / n
    cod   = (sum(abs(r - med) for r in ratios) / n / med) * 100 if med > 0 else 0
    prd   = mean / (sum(r["sale_price"] * ra for r, ra in zip(sold_units, ratios)) /
                    sum(r["sale_price"] for r in sold_units)) if sold_units else 1.0

    return {
        "n_sales":     n,
        "median_ratio":round(med, 3),
        "mean_ratio":  round(mean, 3),
        "cod":         round(cod, 2),
        "prd":         round(prd, 3),
        "cod_pass":    cod <= IAAO_COD_MAX,
        "prd_pass":    IAAO_PRD_RANGE[0] <= prd <= IAAO_PRD_RANGE[1],
        "uniformity":  "ممتاز" if cod <= 10 else ("جيد" if cod <= 15 else "يحتاج مراجعة"),
    }


def _export_xlsx(units, total, avg_ppm, ratio_study, summary,
                 location, purpose, output_dir) -> str:
    """Export portfolio to Excel with formatting."""
    try:
        import xlsxwriter
    except ImportError:
        return ""

    if not output_dir:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "outputs", "reports")
    os.makedirs(output_dir, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"mass_appraisal_{ts}.xlsx")

    wb = xlsxwriter.Workbook(path, {"nan_inf_to_errors": True})

    def F(**kw):
        defaults = {"font_name": "Calibri", "font_size": 10, "border": 1, "valign": "vcenter"}
        defaults.update(kw)
        return wb.add_format(defaults)

    fH  = F(bold=True, bg_color="#1F4E78", font_color="white", font_size=12, align="center", border=2)
    fG  = F(bold=True, bg_color="#D4AF37", align="center")
    fN  = F(num_format="#,##0", align="center")
    fP  = F(num_format="#,##0.00", align="center")
    fT  = F(align="right")
    fOK = F(bg_color="#E2EFDA", align="center", bold=True)
    fER = F(bg_color="#FCE4D6", align="center", bold=True)

    # Sheet 1: Portfolio
    ws = wb.add_worksheet("Portfolio Appraisal")
    ws.right_to_left()
    ws.merge_range("A1:H1", f"تقييم المحفظة العقارية — {location} | {total:,.0f} EGP", fH)
    ws.set_row(0, 30)
    headers = ["رقم الوحدة", "الدور", "المساحة م²", "سنة البناء", "الحالة",
               "سعر AVM/م²", "القيمة النهائية/م²", "قيمة الوحدة (EGP)"]
    for c, h in enumerate(headers):
        ws.write(1, c, h, fG)
    ws.set_row(1, 20)

    for r, u in enumerate(units, 2):
        ws.write(r, 0, u["id"], fT)
        ws.write(r, 1, u["floor"], fP)
        ws.write(r, 2, u["area"], fN)
        ws.write(r, 3, int(u["year_built"]), F(align="center"))
        ws.write(r, 4, u["condition"], fT)
        ws.write(r, 5, u["avm_ppm"], fN)
        ws.write(r, 6, u["final_ppm"], fN)
        ws.write(r, 7, u["unit_value"], fN)

    # Total row
    tr = len(units) + 2
    ws.write(tr, 0, "الإجمالي", F(bold=True))
    ws.write_formula(tr, 7, f"=SUM(H3:H{tr})", F(bold=True, num_format="#,##0", bg_color="#FFD700"))

    ws.set_column("A:A", 18)
    ws.set_column("B:G", 14)
    ws.set_column("H:H", 20)

    # Sheet 2: Ratio Study
    ws2 = wb.add_worksheet("Ratio Study IAAO")
    ws2.right_to_left()
    ws2.merge_range("A1:D1", "دراسة النسب — IAAO Standards", fH)
    ws2.set_row(0, 28)
    items = [
        ("عدد الصفقات المرجعية", ratio_study.get("n_sales", 0)),
        ("الوسيط (Median Ratio)", ratio_study.get("median_ratio", 0)),
        ("المتوسط (Mean Ratio)",  ratio_study.get("mean_ratio", 0)),
        ("COD (معامل التشتت %)", ratio_study.get("cod", 0)),
        ("PRD (معامل التقارب)",   ratio_study.get("prd", 0)),
        ("تقييم التجانس",         ratio_study.get("uniformity", "N/A")),
        ("COD ≤ 15% (Pass/Fail)", "Pass ✅" if ratio_study.get("cod_pass") else "Fail ❌"),
        ("PRD 0.98-1.03 (P/F)",  "Pass ✅" if ratio_study.get("prd_pass") else "Fail ❌"),
    ]
    for i, (lbl, val) in enumerate(items, 2):
        ws2.write(i, 0, lbl, F(bold=True, bg_color="#F2F2F2"))
        ws2.write(i, 1, val, fP if isinstance(val, float) else fT)
    ws2.set_column("A:A", 30)
    ws2.set_column("B:B", 20)

    wb.close()
    return path


# ─── CLI test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys, io, random
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    random.seed(42)

    # Generate 20 test units
    units = [
        {
            "id": f"UNIT-{i:03d}",
            "area": random.choice([80, 100, 120, 150, 200]),
            "floor": random.randint(1, 10),
            "year_built": random.choice([2005, 2010, 2015, 2018, 2022]),
            "condition": random.choice(["good", "excellent", "fair"]),
            "sale_price": random.randint(1_500_000, 4_000_000) if random.random() > 0.6 else 0,
        }
        for i in range(1, 21)
    ]

    res = run_mass_appraisal(units, base_market_ppm=22000, location="Cairo")
    print(f"Portfolio ({res['n_units']} units): {res['total_portfolio_value']:,.0f} EGP")
    print(f"Avg PPM: {res['avg_ppm']:,.0f}  |  Range: {res['portfolio_summary']['min_ppm']:,.0f}–{res['portfolio_summary']['max_ppm']:,.0f}")
    rs = res["ratio_study"]
    if rs.get("n_sales", 0) > 0:
        print(f"Ratio Study: COD={rs['cod']}  PRD={rs['prd']}  Uniformity={rs['uniformity']}")
    print(f"Excel: {res['output_xlsx']}")
