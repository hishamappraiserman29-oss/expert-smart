# engine/valuation_logic.py
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _to_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None or x == "":
            return default
        s = str(x).strip().replace(",", "").replace("%", "")
        if s == "":
            return default
        return float(s)
    except Exception:
        return default


def _pct_to_fraction(pct: Any, default_pct: float) -> float:
    # 7.5 => 0.075
    val_pct = _to_float(pct, default_pct)
    return val_pct / 100.0


def calculate_dcf(
    noi_annual: Any = None,
    discount_rate_percent: Any = None,
    growth_rate_percent: Any = None,
    exit_yield_percent: Any = None,
    projection_years: Any = 5,
    cap_rate_percent: Any = None,  # optional (not required for DCF calc here)
    **kwargs,
) -> Dict[str, Any]:
    """
    DCF based on NOI growing annually, discounted, plus terminal value using exit yield.
    Accepts the keyword names used in main.py.
    Also tolerates aliases via kwargs.
    """

    # ---- aliases (لو في نداءات قديمة) ----
    if noi_annual is None:
        noi_annual = (
            kwargs.get("noi")
            or kwargs.get("noiAnnual")
            or kwargs.get("net_operating_income")
        )

    if discount_rate_percent is None:
        discount_rate_percent = (
            kwargs.get("discount_rate")
            or kwargs.get("discountRate")
            or kwargs.get("discount_rate_pct")
        )

    if growth_rate_percent is None:
        growth_rate_percent = (
            kwargs.get("growth_rate")
            or kwargs.get("growthRate")
            or kwargs.get("growth_rate_pct")
        )

    if exit_yield_percent is None:
        exit_yield_percent = (
            kwargs.get("exit_yield")
            or kwargs.get("exitYield")
            or kwargs.get("exit_yield_pct")
        )

    if projection_years in (None, "", 0):
        projection_years = kwargs.get("years") or kwargs.get("projection") or 5

    # ---- sanitize ----
    noi_annual_f = _to_float(noi_annual, 0.0)
    discount_rate = _pct_to_fraction(discount_rate_percent, 10.0)
    growth_rate = _pct_to_fraction(growth_rate_percent, 2.0)
    exit_yield = _pct_to_fraction(exit_yield_percent, 8.0)
    years = int(_to_float(projection_years, 5))

    cashflows: List[Dict[str, Any]] = []
    noi_t = noi_annual_f

    for t in range(1, years + 1):
        if t > 1:
            noi_t = noi_t * (1.0 + growth_rate)
        pv = noi_t / ((1.0 + discount_rate) ** t) if discount_rate > -1 else 0.0
        cashflows.append({"year": t, "noi": noi_t, "pv": pv})

    terminal_noi = noi_t * (1.0 + growth_rate)
    terminal_value = terminal_noi / exit_yield if exit_yield > 0 else 0.0
    terminal_pv = terminal_value / ((1.0 + discount_rate) ** years) if discount_rate > -1 else 0.0

    dcf_value = sum(x["pv"] for x in cashflows) + terminal_pv

    # cap_rate_percent is not required for the DCF above, but we keep it in inputs for logging
    return {
        "dcf_value": dcf_value,
        "cashflows": cashflows,
        "terminal_noi": terminal_noi,
        "terminal_value": terminal_value,
        "terminal_pv": terminal_pv,
        "inputs": {
            "noi_annual": noi_annual_f,
            "discount_rate_percent": _to_float(discount_rate_percent, 10.0),
            "growth_rate_percent": _to_float(growth_rate_percent, 2.0),
            "exit_yield_percent": _to_float(exit_yield_percent, 8.0),
            "projection_years": years,
            "cap_rate_percent": _to_float(cap_rate_percent, 0.0) if cap_rate_percent is not None else None,
        },
    }


def calculate_residual(
    gdv: Any = None,
    dev_cost: Any = None,
    dev_profit_percent: Any = 20,
    **kwargs,
) -> Dict[str, Any]:
    """
    Residual Land Value = GDV - DevCost - DeveloperProfit
    DeveloperProfit = (dev_profit_percent %) * GDV
    Accepts aliases via kwargs.
    """

    if gdv is None:
        gdv = kwargs.get("gdv_sales") or kwargs.get("sales") or kwargs.get("gross_development_value")

    if dev_cost is None:
        dev_cost = kwargs.get("dev_cost_fees") or kwargs.get("cost") or kwargs.get("development_cost")

    if dev_profit_percent in (None, ""):
        dev_profit_percent = kwargs.get("profit_percent") or kwargs.get("developer_profit") or 20

    gdv_f = _to_float(gdv, 0.0)
    dev_cost_f = _to_float(dev_cost, 0.0)
    profit_frac = _pct_to_fraction(dev_profit_percent, 20.0)

    developer_profit_value = gdv_f * profit_frac
    residual_land_value = gdv_f - dev_cost_f - developer_profit_value

    return {
        "residual_land_value": residual_land_value,
        "developer_profit_value": developer_profit_value,
        "inputs": {
            "gdv": gdv_f,
            "dev_cost": dev_cost_f,
            "dev_profit_percent": _to_float(dev_profit_percent, 20.0),
        },
    }
