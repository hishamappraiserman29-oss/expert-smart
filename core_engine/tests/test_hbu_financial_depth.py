"""
Tests — HBU Financial-Depth layer (hbu_financial_depth.py).

Safety scope: additive layer only; reuses hbu_analysis_engine math READ-ONLY.

FD01  RLV = NPV + land_cost, and setting land_cost = RLV drives NPV to ~0.
FD02  Sensitivity grid is fully computed (no placeholders) and monotone in revenue.
FD03  Payback is surfaced for every scenario.
FD04  Equity IRR computed with financing, UNAVAILABLE without (no fabrication).
FD05  Governance flags present (advisory, engine read-only, reuses engine math).
FD06  Missing discount_rate must NOT fall back to 10% — sensitivity unavailable.
FD07  land_area_m2=0 must yield rlv_per_m2=None (no ZeroDivisionError).
FD08  Invalid financing (ltv>=1, ltv<0, missing loan_rate) → unavailable equity IRR.
FD09  Cashflows with no sign change → not_computable (no exception raised).
FD10  Empty scenarios list → no fabricated target or sensitivity in financial_depth.
FD11  cashflows=None → developer_metrics unavailable (no silent zero-profit fabrication).
FD12  Sensitivity output labels must use correct percentage units (no double-conversion).
"""
from __future__ import annotations

import copy
import os
import sys

import pytest

_CORE_ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _CORE_ENGINE not in sys.path:
    sys.path.insert(0, _CORE_ENGINE)

from hbu_analysis_engine import _build_cashflows, _npv, run_hbu_analysis  # noqa: E402
from hbu_financial_depth import enhance_hbu_financials  # noqa: E402


def _payload() -> dict:
    return {
        "property": {"location": "الرياض - النرجس", "area": 2400},
        "discount_rate": 0.10,
        "alternative_uses": [
            {"use_name": "استمرار السكني", "construction_cost": 0, "annual_revenue": 168000,
             "annual_opex": 25000, "holding_period_years": 10, "exit_value": 1500000, "land_cost": 3000000},
            {"use_name": "تطوير مختلط", "construction_cost": 5280000, "construction_period_years": 2,
             "annual_revenue": 1080000, "annual_opex": 250000, "holding_period_years": 10,
             "exit_value": 9000000, "land_cost": 3000000},
        ],
    }


@pytest.fixture()
def enhanced():
    res = run_hbu_analysis(_payload())
    return enhance_hbu_financials(res, financing={"ltv": 0.5, "loan_rate": 0.08}, land_area_m2=2400)


def test_fd01_rlv_identity(enhanced):
    ev = enhanced["scenarios_evaluated"][1]
    rlv = ev["residual_land_value"]
    assert abs(rlv - (ev["npv"] + 3000000)) < 1.0
    scn = {"construction_cost": 5280000, "construction_period_years": 2, "annual_revenue": 1080000,
           "annual_opex": 250000, "holding_period_years": 10, "exit_value": 9000000, "land_cost": rlv}
    assert abs(_npv(0.10, _build_cashflows(scn))) < 1.0


def test_fd02_sensitivity_computed(enhanced):
    sens = enhanced["financial_depth"]["sensitivity"]
    grid = sens["cost_revenue_grid"]
    assert len(grid) == 9
    assert all(isinstance(c["npv"], (int, float)) for c in grid)
    assert len(sens["discount_sensitivity"]) == 3
    base_cost = sorted((c for c in grid if c["cost_delta_pct"] == 0), key=lambda c: c["revenue_delta_pct"])
    assert base_cost[0]["npv"] < base_cost[-1]["npv"]


def test_fd03_payback_surfaced(enhanced):
    assert all("payback_years" in e for e in enhanced["scenarios_evaluated"])


def test_fd04_equity_irr_gated():
    res = run_hbu_analysis(_payload())
    with_fin = enhance_hbu_financials(res, financing={"ltv": 0.5, "loan_rate": 0.08})
    without = enhance_hbu_financials(res, financing=None)
    assert with_fin["scenarios_evaluated"][1]["equity_irr"]["status"] == "computed"
    eq = without["scenarios_evaluated"][1]["equity_irr"]
    assert eq["value"] is None and eq["status"] == "unavailable" and eq.get("reason")


def test_fd05_governance(enhanced):
    g = enhanced["financial_depth_governance"]
    assert g["advisory_only"] and g["engine_readonly"] and g["reuses_engine_math"] and g["no_fabrication"]


# ── FD06-FD12: governance fixes edge cases ────────────────────────────────────

def test_fd06_missing_discount_rate():
    """discount_rate absent in result dict must not fabricate 10% — sensitivity unavailable."""
    res = run_hbu_analysis(_payload())
    res_no_dr = {k: v for k, v in res.items() if k != "discount_rate"}
    enhanced = enhance_hbu_financials(res_no_dr)
    fd = enhanced["financial_depth"]
    assert fd.get("discount_rate_pct") is None
    assert fd["sensitivity"]["status"] == "unavailable"
    assert fd["sensitivity"]["reason"] == "discount_rate_missing"


def test_fd07_zero_land_area():
    """land_area_m2=0 must yield rlv_per_m2=None in all scenarios (no ZeroDivisionError)."""
    res = run_hbu_analysis(_payload())
    enhanced = enhance_hbu_financials(res, land_area_m2=0)
    for ev in enhanced["scenarios_evaluated"]:
        assert ev["rlv_per_m2"] is None
    fd = enhanced["financial_depth"]
    if "rlv_per_m2" in fd:
        assert fd["rlv_per_m2"] is None


def test_fd08_invalid_financing():
    """ltv=1.0, ltv>1, ltv<0, and missing loan_rate must all yield unavailable equity IRR."""
    res = run_hbu_analysis(_payload())
    invalid_cases = [
        {"ltv": 1.0,  "loan_rate": 0.08},
        {"ltv": 1.5,  "loan_rate": 0.08},
        {"ltv": -0.1, "loan_rate": 0.08},
        {"ltv": 0.5},
    ]
    for financing in invalid_cases:
        enhanced = enhance_hbu_financials(res, financing=financing)
        for ev in enhanced["scenarios_evaluated"]:
            eq = ev["equity_irr"]
            assert eq["status"] == "unavailable", \
                f"Expected unavailable for financing={financing}, got {eq}"
            assert eq.get("reason") is not None


def test_fd09_irr_not_computable():
    """All-negative cashflows with zero total_investment must return not_computable without exception."""
    res = run_hbu_analysis(_payload())
    res_mod = copy.deepcopy(res)
    for ev in res_mod["scenarios_evaluated"]:
        ev["cashflows"] = [-1000.0, -500.0, -500.0]
        ev["construction_cost"] = 0
        ev["land_cost"] = 0
    enhanced = enhance_hbu_financials(res_mod, financing={"ltv": 0.5, "loan_rate": 0.08})
    for ev in enhanced["scenarios_evaluated"]:
        assert ev["equity_irr"]["status"] in ("not_computable", "unavailable")


def test_fd10_empty_scenarios():
    """Empty scenarios_evaluated must not generate fabricated target or sensitivity."""
    res = run_hbu_analysis(_payload())
    res_mod = copy.deepcopy(res)
    res_mod["scenarios_evaluated"] = []
    res_mod["recommended_use"] = None
    enhanced = enhance_hbu_financials(res_mod)
    fd = enhanced["financial_depth"]
    assert "sensitivity" not in fd
    assert "target_use" not in fd
    assert "residual_land_value" not in fd


def test_fd11_missing_cashflows():
    """cashflows=None must yield unavailable developer_metrics and equity_irr (no silent fabrication)."""
    res = run_hbu_analysis(_payload())
    res_mod = copy.deepcopy(res)
    for ev in res_mod["scenarios_evaluated"]:
        ev["cashflows"] = None
    enhanced = enhance_hbu_financials(res_mod, financing={"ltv": 0.5, "loan_rate": 0.08})
    for ev in enhanced["scenarios_evaluated"]:
        dm = ev["developer_metrics"]
        assert dm.get("status") == "unavailable"
        assert dm.get("reason") == "cashflows_missing"
        eq = ev["equity_irr"]
        assert eq["status"] == "unavailable"


def test_fd12_sensitivity_units(enhanced):
    """Grid deltas must be integer pct; discount rows must span ±2pp; no unit confusion."""
    sens = enhanced["financial_depth"]["sensitivity"]
    grid = sens["cost_revenue_grid"]

    cost_deltas = sorted({c["cost_delta_pct"] for c in grid})
    rev_deltas  = sorted({c["revenue_delta_pct"] for c in grid})
    assert cost_deltas == [-10, 0, 10]
    assert rev_deltas  == [-10, 0, 10]

    disc = sens["discount_sensitivity"]
    assert len(disc) == 3
    rates = sorted(r["discount_rate_pct"] for r in disc)
    assert abs(rates[1] - rates[0] - 2.0) < 0.01, f"Expected 2pp spacing, got {rates}"
    assert abs(rates[2] - rates[1] - 2.0) < 0.01, f"Expected 2pp spacing, got {rates}"
    assert abs(rates[1] - 10.0) < 0.01, f"Expected center at 10.0pct, got {rates[1]}"

    for c in grid:
        assert isinstance(c["npv"], (int, float))
    for r in disc:
        assert isinstance(r["npv"], (int, float))
