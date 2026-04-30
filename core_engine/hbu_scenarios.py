"""
hbu_scenarios.py
================
Highest & Best Use (HBU) — Financial Feasibility Engine
---------------------------------------------------------
Produces NPV / IRR for 3+ development scenarios:
  1. Residential (for-sale apartments / villas)
  2. Commercial  (retail / offices)
  3. Industrial  (warehouse / light industrial)
  + optional: Hotel, Mixed-Use

Each scenario uses a 10-year DCF model.

Usage:
    from hbu_scenarios import run_hbu_scenarios, SCENARIO_TYPES
    results = run_hbu_scenarios(land_area=1000, land_value=5_000_000,
                                location="New Cairo", region="EG")
"""
from __future__ import annotations
import math
from typing import Dict, List, Optional


# ─── Scenario Definitions ─────────────────────────────────────────────────────
# Egyptian market benchmarks (EGP); KSA benchmarks ~2.5× via KSA_MULTIPLIER

KSA_MULTIPLIER = 2.5   # SAR ≈ 2.5× EGP for comparable properties

SCENARIO_TYPES = ["residential", "commercial", "industrial", "hotel", "mixed_use"]

_SCENARIOS: Dict[str, Dict] = {
    "residential": {
        "name_ar":       "التطوير السكني",
        "name_en":       "Residential Development",
        "gdv_ppm":       22000,    # EGP/m² gross development value
        "build_cost_pm2": 8500,   # EGP/m²
        "gfa_ratio":     2.5,      # gross floor area / land area (FAR)
        "dev_period_yr": 2.5,      # construction period
        "absorption_yr": 2.0,      # sales absorption period
        "occ_rate":      0.85,     # occupancy / sales rate (buy-to-let)
        "rent_pm2":      420,      # annual rent EGP/m² (for unsold portion)
        "cap_rate":      0.08,
        "annual_growth": 0.07,
        "dev_profit_pct":0.18,
        "agent_fees_pct":0.025,
        "icon": "🏘️",
    },
    "commercial": {
        "name_ar":       "التطوير التجاري / المكتبي",
        "name_en":       "Commercial / Office Development",
        "gdv_ppm":       28000,
        "build_cost_pm2": 10000,
        "gfa_ratio":     3.0,
        "dev_period_yr": 3.0,
        "absorption_yr": 3.0,
        "occ_rate":      0.80,
        "rent_pm2":      600,
        "cap_rate":      0.09,
        "annual_growth": 0.06,
        "dev_profit_pct":0.20,
        "agent_fees_pct":0.03,
        "icon": "🏢",
    },
    "industrial": {
        "name_ar":       "التطوير الصناعي / اللوجستي",
        "name_en":       "Industrial / Logistics Development",
        "gdv_ppm":       8000,
        "build_cost_pm2": 3500,
        "gfa_ratio":     0.60,
        "dev_period_yr": 1.5,
        "absorption_yr": 1.5,
        "occ_rate":      0.90,
        "rent_pm2":      180,
        "cap_rate":      0.10,
        "annual_growth": 0.05,
        "dev_profit_pct":0.15,
        "agent_fees_pct":0.02,
        "icon": "🏭",
    },
    "hotel": {
        "name_ar":       "فندق / شقق فندقية",
        "name_en":       "Hotel / Serviced Apartments",
        "gdv_ppm":       35000,
        "build_cost_pm2": 15000,
        "gfa_ratio":     2.0,
        "dev_period_yr": 3.5,
        "absorption_yr": 4.0,
        "occ_rate":      0.70,
        "rent_pm2":      900,     # room revenue equivalent
        "cap_rate":      0.085,
        "annual_growth": 0.08,
        "dev_profit_pct":0.22,
        "agent_fees_pct":0.04,
        "icon": "🏨",
    },
    "mixed_use": {
        "name_ar":       "استخدامات مختلطة (سكني + تجاري)",
        "name_en":       "Mixed-Use (Residential 60% + Commercial 40%)",
        "gdv_ppm":       24000,
        "build_cost_pm2": 9000,
        "gfa_ratio":     2.8,
        "dev_period_yr": 3.0,
        "absorption_yr": 2.5,
        "occ_rate":      0.82,
        "rent_pm2":      480,
        "cap_rate":      0.085,
        "annual_growth": 0.065,
        "dev_profit_pct":0.19,
        "agent_fees_pct":0.028,
        "icon": "🏗️",
    },
}


# ─── DCF Engine ───────────────────────────────────────────────────────────────

def _irr(cash_flows: List[float], guess: float = 0.10) -> float:
    """Newton-Raphson IRR solver."""
    rate = guess
    for _ in range(200):
        npv  = sum(cf / (1 + rate) ** t for t, cf in enumerate(cash_flows))
        dnpv = sum(-t * cf / (1 + rate) ** (t + 1) for t, cf in enumerate(cash_flows))
        if abs(dnpv) < 1e-10:
            break
        rate -= npv / dnpv
        rate = max(-0.99, min(rate, 10.0))
    return rate


def _dcf_scenario(
    land_area: float,
    land_value: float,
    scenario: Dict,
    wacc: float = 0.14,
    years: int = 10,
    region: str = "EG",
) -> Dict:
    """10-year DCF for one development scenario."""
    mul = KSA_MULTIPLIER if region.upper() == "SA" else 1.0

    gfa         = land_area * scenario["gfa_ratio"]
    gdv_pm2     = scenario["gdv_ppm"] * mul
    bc_pm2      = scenario["build_cost_pm2"] * mul
    rent_pm2    = scenario["rent_pm2"] * mul

    gdv         = gdv_pm2 * gfa
    build_cost  = bc_pm2 * gfa
    dev_profit  = gdv * scenario["dev_profit_pct"]
    agent_fees  = gdv * scenario["agent_fees_pct"]
    total_cost  = build_cost + dev_profit + agent_fees + land_value

    # Cash flow construction
    dev_yr   = scenario["dev_period_yr"]
    abs_yr   = scenario["absorption_yr"]
    growth   = scenario["annual_growth"]
    occ      = scenario["occ_rate"]
    cap      = scenario["cap_rate"]

    cfs = [-land_value]   # Year 0: land acquisition

    for yr in range(1, years + 1):
        # Construction phase: outflows
        if yr <= math.ceil(dev_yr):
            build_out = build_cost / math.ceil(dev_yr)
        else:
            build_out = 0.0

        # Sales inflows (during absorption period after dev_period)
        sales_start = math.ceil(dev_yr)
        if sales_start < yr <= sales_start + math.ceil(abs_yr):
            sales_in = (gdv * occ) / math.ceil(abs_yr)
        else:
            sales_in = 0.0

        # Rental income (post-sales, for retained units)
        if yr > sales_start:
            unsold   = max(1 - occ, 0)
            rental_in = rent_pm2 * gfa * unsold * (1 + growth) ** (yr - sales_start)
        else:
            rental_in = 0.0

        net_cf = sales_in + rental_in - build_out
        cfs.append(net_cf)

    # Terminal value at year 10 (Gordon growth)
    terminal_noi = rent_pm2 * gfa * (1 - scenario["occ_rate"]) * (1 + growth) ** years
    terminal_val = terminal_noi / (cap - min(growth * 0.5, 0.03))
    cfs[-1] += terminal_val

    npv   = sum(cf / (1 + wacc) ** t for t, cf in enumerate(cfs))
    try:
        irr = _irr(cfs)
    except Exception:
        irr = 0.0

    payback = None
    cumulative = 0.0
    for t, cf in enumerate(cfs):
        cumulative += cf
        if cumulative >= 0:
            payback = t
            break

    equity_multiple = (npv + total_cost) / total_cost if total_cost > 0 else 1.0

    return {
        "gfa":            round(gfa, 0),
        "gdv":            round(gdv, 0),
        "build_cost":     round(build_cost, 0),
        "total_cost":     round(total_cost, 0),
        "npv":            round(npv, 0),
        "irr":            round(irr * 100, 2),
        "payback_years":  payback,
        "equity_multiple":round(equity_multiple, 2),
        "cash_flows":     [round(cf, 0) for cf in cfs],
        "terminal_value": round(terminal_val, 0),
        "wacc_used":      round(wacc * 100, 2),
    }


# ─── Main Entry ───────────────────────────────────────────────────────────────

def run_hbu_scenarios(
    land_area: float,
    land_value: float,
    location: str = "Cairo",
    region: str = "EG",
    wacc: float = 0.14,
    years: int = 10,
    scenarios: Optional[List[str]] = None,
) -> Dict:
    """
    Run HBU financial feasibility for selected scenarios.

    Returns:
    {
      "scenarios": {
         "residential": {...dcf result + scenario meta...},
         "commercial": {...},
         ...
      },
      "recommended": "commercial",   ← highest NPV
      "ranking": [...by NPV desc],
      "summary_table": [...]
    }
    """
    if scenarios is None:
        scenarios = ["residential", "commercial", "industrial"]

    results: Dict[str, Dict] = {}

    for sc_key in scenarios:
        if sc_key not in _SCENARIOS:
            continue
        sc_def = _SCENARIOS[sc_key]
        dcf    = _dcf_scenario(land_area, land_value, sc_def, wacc, years, region)
        results[sc_key] = {
            "name_ar":        sc_def["name_ar"],
            "name_en":        sc_def["name_en"],
            "icon":           sc_def["icon"],
            "gfa_ratio":      sc_def["gfa_ratio"],
            "occ_rate":       sc_def["occ_rate"],
            "dev_period_yr":  sc_def["dev_period_yr"],
            **dcf,
        }

    if not results:
        return {"scenarios": {}, "recommended": None, "ranking": [], "summary_table": []}

    ranking = sorted(results.keys(), key=lambda k: results[k]["npv"], reverse=True)
    recommended = ranking[0]

    summary = []
    for k in ranking:
        r = results[k]
        summary.append({
            "scenario":     k,
            "name_ar":      r["name_ar"],
            "icon":         r["icon"],
            "gfa_m2":       r["gfa"],
            "gdv":          r["gdv"],
            "npv":          r["npv"],
            "irr_pct":      r["irr"],
            "payback":      r["payback_years"],
            "em":           r["equity_multiple"],
            "feasible":     r["npv"] > 0 and r["irr"] > wacc * 100,
        })

    return {
        "land_area":    land_area,
        "land_value":   land_value,
        "location":     location,
        "wacc_pct":     round(wacc * 100, 2),
        "scenarios":    results,
        "recommended":  recommended,
        "ranking":      ranking,
        "summary_table":summary,
    }


if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    res = run_hbu_scenarios(
        land_area=1000, land_value=8_000_000,
        location="New Cairo", region="EG", wacc=0.14
    )
    print(f"Recommended: {res['recommended']} — {res['scenarios'][res['recommended']]['name_ar']}")
    print("\nScenario Ranking:")
    for row in res["summary_table"]:
        feasible = "✅" if row["feasible"] else "❌"
        print(f"  {row['icon']} {row['name_ar']:<30} NPV={row['npv']:>12,.0f}  IRR={row['irr_pct']:>5.1f}%  {feasible}")
