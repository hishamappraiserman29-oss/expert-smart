"""
advanced_cost_engine.py
=======================
Replacement Cost New (RCN) Calculator
--------------------------------------
Produces a fully itemized cost table following:
  • Egyptian EFSA & Saudi TAQEEM construction benchmarks
  • RICS NRM1 cost plan structure (7 elemental groups)
  • Depreciation: Physical (straight-line) + Functional + External obsolescence

Usage:
    from advanced_cost_engine import calc_rcn, FINISHING_GRADES
    result = calc_rcn(area=250, property_type="villa", finishing="super_lux",
                      building_age=8, location="Cairo", floors=3)
"""
from __future__ import annotations
import math
from typing import Dict, List

# ─── Construction Cost Benchmarks (EGP/m²) ────────────────────────────────────
# Source: Egyptian Engineers Syndicate 2025 index + TAQEEM KSA benchmarks
# Indexed to Q1-2026. Adjust via COST_INDEX multiplier.

COST_INDEX = 1.0   # Set > 1.0 to inflate for regional premium

_BASE_BUILD_COST: Dict[str, Dict[str, float]] = {
    # property_type → {grade: EGP/m²}
    "apartment":  {"economy": 4500, "standard": 5500, "lux": 7000, "super_lux": 9500},
    "villa":      {"economy": 5500, "standard": 7000, "lux": 9500, "super_lux": 14000},
    "office":     {"economy": 5000, "standard": 6500, "lux": 8500, "super_lux": 12000},
    "retail":     {"economy": 4000, "standard": 5500, "lux": 7500, "super_lux": 10000},
    "warehouse":  {"economy": 2500, "standard": 3500, "lux": 4500, "super_lux": 6000},
    "hospital":   {"economy": 9000, "standard": 12000,"lux": 16000,"super_lux": 22000},
    "hotel":      {"economy": 8000, "standard": 11000,"lux": 15000,"super_lux": 20000},
    "industrial": {"economy": 2000, "standard": 3000, "lux": 4000, "super_lux": 5500},
}

FINISHING_GRADES = list(next(iter(_BASE_BUILD_COST.values())).keys())

# ─── NRM1 Elemental Cost Breakdown (% of total build cost) ────────────────────
# 7 elements per RICS NRM1 structure
_ELEMENTS: List[Dict] = [
    {"code": "1A", "name_ar": "الهيكل الإنشائي والأساسات",  "name_en": "Substructure & Foundations", "pct": 0.18},
    {"code": "2A", "name_ar": "الهيكل الخرساني والإنشائي", "name_en": "Frame & Upper Floors",        "pct": 0.22},
    {"code": "2B", "name_ar": "الأسقف والطوابق",            "name_en": "Roof & Stairs",               "pct": 0.08},
    {"code": "2C", "name_ar": "الواجهات والأبواب والنوافذ", "name_en": "External Walls & Windows",    "pct": 0.12},
    {"code": "3A", "name_ar": "التشطيبات الداخلية",         "name_en": "Internal Finishes",           "pct": 0.20},
    {"code": "4A", "name_ar": "الكهرباء والسباكة والميكانيكا","name_en":"MEP (Elec/Plumbing/HVAC)",   "pct": 0.14},
    {"code": "5A", "name_ar": "الطوارئ والأعمال الخارجية",  "name_en": "Contingency & Externals",    "pct": 0.06},
]

# ─── Depreciation profiles ────────────────────────────────────────────────────
_ECONOMIC_LIFE = {
    "apartment": 60, "villa": 60, "office": 50, "retail": 45,
    "warehouse": 40, "hospital": 50, "hotel": 50, "industrial": 35,
}

_FUNCTIONAL_OBSOLESCENCE = {
    # Property types prone to functional obsolescence (old layouts, outdated MEP)
    "apartment": 0.02, "villa": 0.015, "office": 0.03,
    "retail": 0.025,   "warehouse": 0.02, "hospital": 0.04,
    "hotel": 0.03,     "industrial": 0.025,
}

# ─── Location multipliers ──────────────────────────────────────────────────────
_LOCATION_MUL = {
    "Riyadh": 1.30, "Jeddah": 1.25, "NEOM": 1.60, "Dammam": 1.20,
    "Cairo":  1.00, "Alexandria": 1.05, "New Cairo": 1.10,
    "6th October": 0.95, "North Coast": 0.90,
}

def _location_multiplier(location: str) -> float:
    for key, mul in _LOCATION_MUL.items():
        if key.lower() in location.lower():
            return mul
    return 1.0


# ─── Main RCN Calculator ──────────────────────────────────────────────────────

def calc_rcn(
    area: float,
    property_type: str = "apartment",
    finishing: str = "standard",
    building_age: int = 0,
    location: str = "Cairo",
    floors: int = 1,
    land_area: float = 0.0,
    land_ppm: float = 0.0,
    include_land: bool = True,
    contractor_profit_pct: float = 0.15,
    developer_profit_pct: float = 0.12,
    region: str = "EG",
) -> Dict:
    """
    Calculate Replacement Cost New (RCN) with full itemized breakdown.

    Returns dict:
    {
      "rcn_gross":         float  — total gross replacement cost
      "depreciation":      float  — total depreciation (all types)
      "rcn_net":           float  — depreciated replacement cost (DRC)
      "land_value":        float  — land value (if include_land)
      "total_value":       float  — DRC + land
      "ppm":               float  — total value / area
      "elements":          list   — itemized cost table
      "depr_breakdown":    dict   — {physical, functional, external}
      "build_cost_pm2":    float  — blended build cost per m²
      "economic_life":     int
      "remaining_life":    int
      "location_mul":      float
    }
    """
    ptype    = property_type.lower().replace(" ", "_").replace("-", "_")
    if ptype not in _BASE_BUILD_COST:
        ptype = "apartment"
    if finishing not in _BASE_BUILD_COST[ptype]:
        finishing = "standard"

    loc_mul       = _location_multiplier(location)
    base_cost_pm2 = _BASE_BUILD_COST[ptype][finishing] * loc_mul * COST_INDEX

    # Floor multiplier (taller buildings cost more per m²)
    floor_mul = 1.0 + (floors - 1) * 0.015

    build_cost_pm2 = base_cost_pm2 * floor_mul
    gross_build    = build_cost_pm2 * area

    # Add contractor and developer profit
    contractor_p   = gross_build * contractor_profit_pct
    developer_p    = gross_build * developer_profit_pct
    rcn_gross      = gross_build + contractor_p + developer_p

    # ── Depreciation ──────────────────────────────────────────────────────────
    econ_life    = _ECONOMIC_LIFE.get(ptype, 60)
    eff_age      = min(building_age, econ_life)
    remaining    = max(econ_life - eff_age, 1)

    phys_depr    = (eff_age / econ_life) * rcn_gross
    func_depr    = rcn_gross * _FUNCTIONAL_OBSOLESCENCE.get(ptype, 0.02)
    # External obsolescence — market-derived (use 3% in distressed markets, 0 in prime)
    ext_depr     = 0.0   # adjust externally based on market conditions

    total_depr   = phys_depr + func_depr + ext_depr
    rcn_net      = rcn_gross - total_depr

    # ── Land ─────────────────────────────────────────────────────────────────
    if include_land:
        la  = land_area if land_area > 0 else area
        lppm = land_ppm if land_ppm > 0 else build_cost_pm2 * 0.35
        lv  = la * lppm
    else:
        lv  = 0.0

    total_value = rcn_net + lv
    ppm         = total_value / area if area > 0 else 0

    # ── Itemized elements table ───────────────────────────────────────────────
    elements = []
    for el in _ELEMENTS:
        el_cost = gross_build * el["pct"]
        elements.append({
            "code":    el["code"],
            "name_ar": el["name_ar"],
            "name_en": el["name_en"],
            "pct":     el["pct"],
            "cost":    round(el_cost, 0),
        })

    return {
        "property_type":     ptype,
        "finishing":         finishing,
        "area":              area,
        "floors":            floors,
        "location":          location,
        "location_mul":      loc_mul,
        "build_cost_pm2":    round(build_cost_pm2, 0),
        "gross_build":       round(gross_build, 0),
        "contractor_profit": round(contractor_p, 0),
        "developer_profit":  round(developer_p, 0),
        "rcn_gross":         round(rcn_gross, 0),
        "depr_breakdown": {
            "physical":         round(phys_depr, 0),
            "functional":       round(func_depr, 0),
            "external":         round(ext_depr, 0),
            "total":            round(total_depr, 0),
            "depr_rate_pct":    round(eff_age / econ_life * 100, 1),
        },
        "depreciation":      round(total_depr, 0),
        "rcn_net":           round(rcn_net, 0),
        "land_value":        round(lv, 0),
        "total_value":       round(total_value, 0),
        "ppm":               round(ppm, 0),
        "economic_life":     econ_life,
        "effective_age":     eff_age,
        "remaining_life":    remaining,
        "elements":          elements,
    }


# ─── Land Valuation ──────────────────────────────────────────────────────────

# Land comparable database (Cairo / KSA reference)
_LAND_COMPS = [
    {"id": "L-001", "area": 500,  "ppm": 8000,  "zone": "New Cairo",      "use": "residential", "x": 30.009, "y": 31.500},
    {"id": "L-002", "area": 800,  "ppm": 6500,  "zone": "6th October",    "use": "residential", "x": 29.930, "y": 30.936},
    {"id": "L-003", "area": 1000, "ppm": 12000, "zone": "Zamalek",        "use": "residential", "x": 30.059, "y": 31.224},
    {"id": "L-004", "area": 2000, "ppm": 4500,  "zone": "Cairo-Outskirts","use": "industrial",  "x": 30.100, "y": 31.600},
    {"id": "L-005", "area": 600,  "ppm": 9500,  "zone": "Maadi",          "use": "residential", "x": 29.961, "y": 31.258},
    {"id": "L-006", "area": 1500, "ppm": 5500,  "zone": "Sheikh Zayed",   "use": "residential", "x": 30.010, "y": 30.957},
    {"id": "L-007", "area": 3000, "ppm": 3200,  "zone": "Badr City",      "use": "industrial",  "x": 30.120, "y": 31.720},
    {"id": "L-008", "area": 700,  "ppm": 11500, "zone": "Nasr City",      "use": "commercial",  "x": 30.074, "y": 31.338},
]


def calc_land_value(
    area: float,
    location: str = "Cairo",
    use_type: str = "residential",
    method: str = "sales_comparison",
    residual_data: dict = None,
) -> Dict:
    """
    Land valuation via:
      method='sales_comparison' → adjusted comparables
      method='residual'         → GDV - development cost
    """
    if method == "residual" and residual_data:
        return _land_residual(area, location, residual_data)
    return _land_sales_comparison(area, location, use_type)


def _land_sales_comparison(area, location, use_type) -> Dict:
    comps = [c for c in _LAND_COMPS if c["use"] == use_type]
    if not comps:
        comps = _LAND_COMPS

    # Simple proximity + use adjustment
    adjusted = []
    for c in comps[:5]:
        adj_use      = 1.0 if c["use"] == use_type else 0.90
        adj_size     = 1.05 if c["area"] > area * 1.5 else (0.97 if c["area"] < area * 0.5 else 1.0)
        adj_ppm      = c["ppm"] * adj_use * adj_size
        adjusted.append({**c, "adj_ppm": round(adj_ppm, 0)})

    avg_ppm    = sum(c["adj_ppm"] for c in adjusted) / len(adjusted)
    land_value = avg_ppm * area

    return {
        "method":      "sales_comparison",
        "area":        area,
        "location":    location,
        "use_type":    use_type,
        "avg_ppm":     round(avg_ppm, 0),
        "land_value":  round(land_value, 0),
        "comparables": adjusted,
    }


def _land_residual(area, location, data: dict) -> Dict:
    """
    Residual Method: Land Value = GDV - (Build Cost + Profit + Fees)
    data keys: gdv_pm2, build_cost_pm2, developer_profit_pct, agent_fees_pct
    """
    gdv_pm2   = float(data.get("gdv_pm2", 20000))
    bc_pm2    = float(data.get("build_cost_pm2", 7000))
    dev_prof  = float(data.get("developer_profit_pct", 0.18))
    fees      = float(data.get("agent_fees_pct", 0.03))

    gdv         = gdv_pm2 * area
    build_total = bc_pm2 * area
    dev_profit  = gdv * dev_prof
    agent_fees  = gdv * fees
    total_costs = build_total + dev_profit + agent_fees

    land_value = gdv - total_costs
    land_ppm   = land_value / area if area > 0 else 0

    return {
        "method":       "residual",
        "area":         area,
        "location":     location,
        "gdv":          round(gdv, 0),
        "build_total":  round(build_total, 0),
        "dev_profit":   round(dev_profit, 0),
        "agent_fees":   round(agent_fees, 0),
        "total_costs":  round(total_costs, 0),
        "land_value":   round(max(land_value, 0), 0),
        "land_ppm":     round(max(land_ppm, 0), 0),
    }


# ─── CLI test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    r = calc_rcn(area=250, property_type="villa", finishing="super_lux",
                 building_age=8, location="New Cairo", floors=3)
    print(f"RCN Gross  : {r['rcn_gross']:>12,.0f} EGP")
    print(f"Depreciation: {r['depreciation']:>11,.0f} EGP ({r['depr_breakdown']['depr_rate_pct']}%)")
    print(f"RCN Net    : {r['rcn_net']:>12,.0f} EGP")
    print(f"Total Value: {r['total_value']:>12,.0f} EGP  ({r['ppm']:,.0f} EGP/m²)")
    print("\nItemized elements:")
    for el in r["elements"]:
        print(f"  [{el['code']}] {el['name_ar']:<30} {el['cost']:>12,.0f} EGP ({el['pct']*100:.0f}%)")

    lv = calc_land_value(500, "New Cairo", "residential")
    print(f"\nLand (S/C): {lv['land_value']:,.0f} EGP @ {lv['avg_ppm']:,.0f}/m²")

    lr = calc_land_value(500, "Cairo", "residential", method="residual",
                         residual_data={"gdv_pm2": 22000, "build_cost_pm2": 8000})
    print(f"Land (Resid): {lr['land_value']:,.0f} EGP @ {lr['land_ppm']:,.0f}/m²")
