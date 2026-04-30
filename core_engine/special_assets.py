"""
special_assets.py
=================
Specialized Asset Valuation Templates
--------------------------------------
Implements calculation models for:
  1. Hospitals        — bed-capacity basis (DCF on EBITDA per bed)
  2. Factories        — industrial throughput + replacement cost
  3. Warehouses       — net operating income + WAULT
  4. Quarries         — depletion / reserve basis
  5. Hotels           — RevPAR / ADR income model
  6. REITs            — FFO / NAV institutional model
  7. Retail Malls     — anchor tenant + GLA income model

Usage:
    from special_assets import value_hospital, value_quarry, value_reit, value_warehouse
"""
from __future__ import annotations
import math
from typing import Dict, Optional


# ─── 1. Hospital Valuation ────────────────────────────────────────────────────

def value_hospital(
    beds: int,
    occupancy_rate: float = 0.72,
    revenue_per_occupied_bed_day: float = 3500,   # EGP
    ebitda_margin: float = 0.22,
    cap_rate: float = 0.085,
    land_area_m2: float = 5000,
    land_ppm: float = 8000,
    building_area_m2: float = 12000,
    build_age: int = 10,
    location: str = "Cairo",
    region: str = "EG",
) -> Dict:
    """
    Hospital valuation — bed-capacity income approach.
    Primary method: DCF on EBITDA.
    Secondary method: Cost approach on specialized building.
    """
    mul = 2.5 if region.upper() == "SA" else 1.0

    rev_per_bed_day = revenue_per_occupied_bed_day * mul
    days_per_year   = 365
    annual_revenue  = beds * occupancy_rate * days_per_year * rev_per_bed_day
    ebitda          = annual_revenue * ebitda_margin
    income_value    = ebitda / cap_rate

    # Cost approach (specialized hospital: 16,000–22,000 EGP/m²)
    from advanced_cost_engine import calc_rcn
    cost_res = calc_rcn(building_area_m2, "hospital", "lux", build_age, location,
                        land_area=land_area_m2, land_ppm=land_ppm * mul)
    cost_value = cost_res["total_value"]

    # Reconcile 60% income / 40% cost
    reconciled = income_value * 0.60 + cost_value * 0.40

    return {
        "asset_type":            "hospital",
        "beds":                  beds,
        "occupancy_rate":        occupancy_rate,
        "annual_revenue":        round(annual_revenue, 0),
        "ebitda":                round(ebitda, 0),
        "ebitda_margin":         ebitda_margin,
        "cap_rate":              cap_rate,
        "income_value":          round(income_value, 0),
        "cost_value":            round(cost_value, 0),
        "reconciled_value":      round(reconciled, 0),
        "value_per_bed":         round(reconciled / max(beds, 1), 0),
        "ppm_building":          round(reconciled / max(building_area_m2, 1), 0),
    }


# ─── 2. Factory / Industrial Facility ────────────────────────────────────────

def value_factory(
    gla_m2: float,                  # gross leasable area
    annual_throughput_tons: float,  # production capacity
    revenue_per_ton: float = 500,   # EGP per ton of output
    ebitda_margin: float = 0.18,
    cap_rate: float = 0.10,
    land_area_m2: float = 0.0,
    land_ppm: float = 2500,
    build_age: int = 15,
    location: str = "Cairo",
    region: str = "EG",
) -> Dict:
    """Factory / manufacturing plant valuation."""
    mul = 2.5 if region.upper() == "SA" else 1.0
    rev = annual_throughput_tons * revenue_per_ton * mul
    ebitda = rev * ebitda_margin
    income_value = ebitda / cap_rate

    from advanced_cost_engine import calc_rcn
    land_a = land_area_m2 if land_area_m2 > 0 else gla_m2 * 1.5
    cost_res = calc_rcn(gla_m2, "industrial", "standard", build_age, location,
                        land_area=land_a, land_ppm=land_ppm * mul)
    cost_value = cost_res["total_value"]

    reconciled = income_value * 0.50 + cost_value * 0.50

    return {
        "asset_type":            "factory",
        "gla_m2":                gla_m2,
        "annual_throughput_tons":annual_throughput_tons,
        "annual_revenue":        round(rev, 0),
        "ebitda":                round(ebitda, 0),
        "income_value":          round(income_value, 0),
        "cost_value":            round(cost_value, 0),
        "reconciled_value":      round(reconciled, 0),
        "value_per_m2":          round(reconciled / max(gla_m2, 1), 0),
    }


# ─── 3. Warehouse / Logistics ─────────────────────────────────────────────────

def value_warehouse(
    gla_m2: float,
    annual_rent_pm2: float = 200,   # EGP/m²/year
    occupancy: float = 0.92,
    wault_years: float = 4.5,       # Weighted Average Unexpired Lease Term
    cap_rate: float = 0.09,
    land_area_m2: float = 0.0,
    land_ppm: float = 2000,
    build_age: int = 8,
    location: str = "Cairo",
    region: str = "EG",
) -> Dict:
    """Warehouse / logistics facility — income approach with WAULT adjustment."""
    mul = 2.5 if region.upper() == "SA" else 1.0
    rent_pm2 = annual_rent_pm2 * mul
    noi      = gla_m2 * rent_pm2 * occupancy
    # WAULT discount: shorter lease = higher cap rate
    wault_adj_cap = cap_rate * (1 + max(0, (3 - wault_years) * 0.005))
    income_value  = noi / wault_adj_cap

    from advanced_cost_engine import calc_rcn
    land_a = land_area_m2 if land_area_m2 > 0 else gla_m2 * 2.0
    cost_res = calc_rcn(gla_m2, "warehouse", "standard", build_age, location,
                        land_area=land_a, land_ppm=land_ppm * mul)
    cost_value = cost_res["total_value"]

    reconciled = income_value * 0.65 + cost_value * 0.35

    return {
        "asset_type":       "warehouse",
        "gla_m2":           gla_m2,
        "annual_rent_pm2":  round(rent_pm2, 0),
        "occupancy":        occupancy,
        "wault_years":      wault_years,
        "noi":              round(noi, 0),
        "cap_rate_adj":     round(wault_adj_cap, 4),
        "income_value":     round(income_value, 0),
        "cost_value":       round(cost_value, 0),
        "reconciled_value": round(reconciled, 0),
        "value_per_m2":     round(reconciled / max(gla_m2, 1), 0),
    }


# ─── 4. Quarry — Depletion / Reserve Basis ────────────────────────────────────

def value_quarry(
    reserve_tons: float,            # total remaining reserve
    annual_extraction_tons: float,  # current extraction capacity/year
    price_per_ton: float = 120,     # net realization price EGP/ton
    operating_cost_pct: float = 0.55,
    discount_rate: float = 0.12,
    rehabilitation_cost: float = 0.0,
    land_area_m2: float = 50000,
    land_ppm: float = 150,
    region: str = "EG",
) -> Dict:
    """
    Quarry valuation — Discounted Cash Flow on proven reserves.
    Depletion method: annual extraction → revenue stream until exhaustion.
    """
    mul = 2.5 if region.upper() == "SA" else 1.0
    net_price = price_per_ton * mul
    life_years = reserve_tons / max(annual_extraction_tons, 1)
    life_years = min(life_years, 50)

    annual_revenue = annual_extraction_tons * net_price
    annual_opex    = annual_revenue * operating_cost_pct
    annual_ncf     = annual_revenue - annual_opex  # net cash flow per year

    # DCF over quarry life
    pv_ncf = sum(annual_ncf / (1 + discount_rate) ** t for t in range(1, int(life_years) + 1))

    # Rehabilitation (decommissioning) cost — deducted at end
    pv_rehab = rehabilitation_cost / (1 + discount_rate) ** int(life_years)

    # Land residual value after exhaustion
    land_residual = land_area_m2 * land_ppm * mul
    pv_land       = land_residual / (1 + discount_rate) ** int(life_years)

    quarry_value = pv_ncf - pv_rehab + pv_land

    return {
        "asset_type":           "quarry",
        "reserve_tons":         reserve_tons,
        "annual_extraction":    annual_extraction_tons,
        "price_per_ton":        round(net_price, 2),
        "life_years":           round(life_years, 1),
        "annual_revenue":       round(annual_revenue, 0),
        "annual_ncf":           round(annual_ncf, 0),
        "pv_cash_flows":        round(pv_ncf, 0),
        "pv_rehab_cost":        round(pv_rehab, 0),
        "pv_land_residual":     round(pv_land, 0),
        "reconciled_value":     round(max(quarry_value, 0), 0),
        "value_per_ton_reserve":round(max(quarry_value, 0) / max(reserve_tons, 1), 2),
        "discount_rate":        discount_rate,
    }


# ─── 5. Hotel Valuation ───────────────────────────────────────────────────────

def value_hotel(
    rooms: int,
    adr: float = 800,           # Average Daily Rate EGP
    occupancy: float = 0.68,    # annual occupancy
    trevpar: float = 1200,      # Total Revenue per Available Room (EGP/night)
    ebitda_margin: float = 0.28,
    cap_rate: float = 0.085,
    building_area_m2: float = 0.0,
    land_area_m2: float = 0.0,
    land_ppm: float = 8000,
    build_age: int = 10,
    location: str = "Cairo",
    region: str = "EG",
) -> Dict:
    """Hotel valuation — RevPAR income approach + cost check."""
    mul = 2.5 if region.upper() == "SA" else 1.0
    adr_loc       = adr * mul
    trevpar_loc   = trevpar * mul
    rev_par       = adr_loc * occupancy
    annual_rev    = rev_par * rooms * 365
    ebitda        = annual_rev * ebitda_margin
    income_value  = ebitda / cap_rate

    build_area = building_area_m2 if building_area_m2 > 0 else rooms * 65
    from advanced_cost_engine import calc_rcn
    cost_res = calc_rcn(build_area, "hotel", "lux", build_age, location,
                        land_area=land_area_m2 if land_area_m2 else rooms * 40,
                        land_ppm=land_ppm * mul)
    cost_value = cost_res["total_value"]

    reconciled = income_value * 0.65 + cost_value * 0.35

    return {
        "asset_type":        "hotel",
        "rooms":             rooms,
        "adr":               round(adr_loc, 0),
        "occupancy":         occupancy,
        "revpar":            round(rev_par, 0),
        "annual_revenue":    round(annual_rev, 0),
        "ebitda":            round(ebitda, 0),
        "income_value":      round(income_value, 0),
        "cost_value":        round(cost_value, 0),
        "reconciled_value":  round(reconciled, 0),
        "value_per_key":     round(reconciled / max(rooms, 1), 0),
    }


# ─── 6. REIT / Institutional NAV ─────────────────────────────────────────────

def value_reit_nav(
    portfolio: list,   # list of {name, asset_type, area, annual_noi, cap_rate, debt}
    total_debt: float = 0.0,
    shares_outstanding: int = 100_000_000,
    management_expense_ratio: float = 0.015,
    region: str = "EG",
) -> Dict:
    """
    REIT NAV (Net Asset Value) calculation.
    NAV = Σ(GAV of assets) - Total Debt - Management liabilities
    FFO = Σ(NOI) - Interest expense
    """
    mul = 2.5 if region.upper() == "SA" else 1.0
    gav_items = []
    total_noi = 0.0
    total_gav = 0.0

    for asset in portfolio:
        noi = float(asset.get("annual_noi", 0)) * mul
        cap = float(asset.get("cap_rate", 0.09))
        gav = noi / cap if cap > 0 else 0
        gav_items.append({
            "name":    asset.get("name", "Asset"),
            "type":    asset.get("asset_type", "office"),
            "noi":     round(noi, 0),
            "cap":     cap,
            "gav":     round(gav, 0),
        })
        total_noi += noi
        total_gav += gav

    mgmt_liability = total_gav * management_expense_ratio
    nav             = total_gav - total_debt - mgmt_liability
    nav_per_share   = nav / max(shares_outstanding, 1)

    # FFO (simplified: NOI - interest on debt at 8%)
    interest_expense = total_debt * 0.08
    ffo              = total_noi - interest_expense
    ffo_per_share    = ffo / max(shares_outstanding, 1)

    return {
        "asset_type":        "reit",
        "gav_items":         gav_items,
        "total_gav":         round(total_gav, 0),
        "total_debt":        round(total_debt, 0),
        "mgmt_liability":    round(mgmt_liability, 0),
        "nav":               round(nav, 0),
        "nav_per_share":     round(nav_per_share, 4),
        "total_noi":         round(total_noi, 0),
        "interest_expense":  round(interest_expense, 0),
        "ffo":               round(ffo, 0),
        "ffo_per_share":     round(ffo_per_share, 4),
        "shares_outstanding":shares_outstanding,
        "loan_to_value":     round(total_debt / max(total_gav, 1) * 100, 1),
    }


# ─── CLI test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    h = value_hospital(beds=200, location="Cairo", region="EG")
    print(f"Hospital (200 beds): {h['reconciled_value']:,.0f} EGP  |  per bed: {h['value_per_bed']:,.0f}")

    q = value_quarry(reserve_tons=5_000_000, annual_extraction_tons=200_000)
    print(f"Quarry (5M tons): {q['reconciled_value']:,.0f} EGP  |  life: {q['life_years']} yrs")

    w = value_warehouse(gla_m2=10000, annual_rent_pm2=180)
    print(f"Warehouse 10Km²: {w['reconciled_value']:,.0f} EGP  |  {w['value_per_m2']:,.0f}/m²")

    reit = value_reit_nav([
        {"name": "Office Tower A", "asset_type": "office",    "annual_noi": 8_000_000, "cap_rate": 0.09},
        {"name": "Mall B",         "asset_type": "retail",    "annual_noi": 12_000_000,"cap_rate": 0.085},
        {"name": "Warehouse C",    "asset_type": "warehouse", "annual_noi": 4_000_000, "cap_rate": 0.10},
    ], total_debt=50_000_000)
    print(f"REIT NAV: {reit['nav']:,.0f} EGP  |  NAV/share: {reit['nav_per_share']:.4f}  |  LTV: {reit['loan_to_value']}%")
