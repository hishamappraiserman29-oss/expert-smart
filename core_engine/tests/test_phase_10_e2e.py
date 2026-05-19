"""
test_phase_10_e2e.py — Phase 10: DCF Integration E2E Tests

5 tests covering:
  1. Basic DCF model math
  2. POST /api/valuation/dcf — 200 OK, property_value > 0
  3. POST /api/valuation/dcf with sensitivity analysis
  4. DCF value vs Phase 4 direct income capitalisation
  5. Sensitivity value range (min < avg < max)
"""
from __future__ import annotations

import sys
from pathlib import Path

# ── sys.path — same pattern as test_phase_8_e2e.py ───────────────────────────
_CORE = Path(__file__).resolve().parents[1]   # …/core_engine/
_ROOT = _CORE.parent                          # project root
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from adapters.dcf_model import DCFModel
from adapters.dcf_sensitivity import DCFSensitivityAnalysis

# Import Flask app (bridge_api.py lives directly in core_engine/)
import os
os.environ.setdefault("JWT_SECRET", "test-secret-e2e-bundle")
os.chdir(str(_CORE))   # bridge_api.py imports adapters via relative names
from bridge_api import app
from auth.tokens import generate_token as _gen_token
_AUTH_HDR = {"Authorization": f"Bearer {_gen_token('test-user-e2e')}"}

# ─────────────────────────────────────────────────────────────────────────────

_PROJECTIONS_5Y = [
    {"year": y, "gross_income": 100000, "vacancy_rate": 0.05,
     "operating_expenses": 40000, "debt_service": 10000}
    for y in range(1, 6)
]


def test_dcf_basic_model():
    """DCF model produces correct Year-1 figures and positive NPV."""
    dcf = DCFModel(discount_rate=0.08, holding_period=5, terminal_cap_rate=0.07)
    for year in range(1, 6):
        dcf.add_annual_cash_flow(year, 100000, 0.05, 40000, 10000)
    dcf.set_terminal_value(55000, method="cap_rate")
    dcf.calculate_npv()

    y1 = dcf.annual_cash_flows[0]
    assert y1.effective_rental_income == 95000
    assert y1.net_operating_income    == 55000
    assert y1.cash_flow_to_investor   == 45000
    assert dcf.property_value   > 0
    assert dcf.pv_cash_flows    > 0
    assert dcf.pv_terminal_value > 0
    print(f"[PASS] test_dcf_basic_model  — value: {dcf.property_value:,.0f}")


def test_dcf_api_route():
    """POST /api/valuation/dcf returns 200 with property_value > 0."""
    with app.test_client() as client:
        resp = client.post("/api/valuation/dcf", json={
            "subject_property": {"property_type": "office", "area_sqm": 500},
            "dcf_assumptions": {
                "holding_period": 5,
                "discount_rate":  0.08,
                "terminal_cap_rate": 0.07,
                "annual_projections": _PROJECTIONS_5Y,
            },
            "include_sensitivity": False,
        }, headers=_AUTH_HDR)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert "dcf_valuation" in data
        assert data["dcf_valuation"]["property_value"] > 0
        assert data["sensitivity_analysis"] is None
    print(f"[PASS] test_dcf_api_route  — value: {data['dcf_valuation']['property_value']:,.0f}")


def test_dcf_with_sensitivity():
    """POST /api/valuation/dcf with sensitivity flag returns scenario data."""
    with app.test_client() as client:
        resp = client.post("/api/valuation/dcf", json={
            "subject_property": {"property_type": "office"},
            "dcf_assumptions": {
                "holding_period": 5,
                "discount_rate":  0.08,
                "terminal_cap_rate": 0.07,
                "annual_projections": _PROJECTIONS_5Y,
            },
            "include_sensitivity": True,
            "sensitivity_cap_rates":      [0.075, 0.07, 0.065],
            "sensitivity_discount_rates": [0.06, 0.07, 0.08, 0.09, 0.10],
        }, headers=_AUTH_HDR)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        sa = data["sensitivity_analysis"]
        assert sa is not None
        assert sa["scenario_count"] == 8   # 3 cap-rate + 5 discount-rate
        assert sa["min_value"] < sa["max_value"]
    print(f"[PASS] test_dcf_with_sensitivity  — {sa['scenario_count']} scenarios, "
          f"range {sa['value_range']:,.0f}")


def test_dcf_vs_income_engine():
    """DCF value < direct cap-rate income value (time value of money effect)."""
    dcf = DCFModel(0.08, 5, 0.07)
    for year in range(1, 6):
        dcf.add_annual_cash_flow(year, 100000, 0.05, 40000, 10000)
    dcf.set_terminal_value(55000)
    dcf.calculate_npv()
    dcf_value = dcf.property_value

    income_value = 55000 / 0.07   # Phase 4 direct capitalisation

    assert dcf_value != income_value
    assert dcf_value < income_value
    print(f"[PASS] test_dcf_vs_income_engine  — "
          f"DCF {dcf_value:,.0f} < Income cap {income_value:,.0f}")


def test_sensitivity_value_range():
    """Sensitivity summary min < average < max."""
    sens = DCFSensitivityAnalysis(0.08, 5, 0.07)
    for year in range(1, 6):
        sens.add_year_projection(year, 100000, 0.05, 40000, 10000)
    sens.create_cap_rate_scenarios(0.075, 0.07, 0.065)
    summary = sens.get_scenario_summary()

    assert summary["min_value"] < summary["average_value"] < summary["max_value"]
    print(f"[PASS] test_sensitivity_value_range  — "
          f"{summary['min_value']:,.0f} – {summary['average_value']:,.0f} – {summary['max_value']:,.0f}")


# ── Runner ────────────────────────────────────────────────────────────────────

def test_all_phase_10_tests():
    print("\n=== Phase 10 E2E Tests ===")
    tests = [
        test_dcf_basic_model,
        test_dcf_api_route,
        test_dcf_with_sensitivity,
        test_dcf_vs_income_engine,
        test_sensitivity_value_range,
    ]
    passed = 0
    for fn in tests:
        try:
            fn()
            passed += 1
        except Exception as exc:
            print(f"[FAIL] {fn.__name__} — {exc}")
    print(f"\n{passed}/{len(tests)} tests passed.")
    if passed == len(tests):
        print("Phase 10 E2E COMPLETE")


if __name__ == "__main__":
    test_all_phase_10_tests()
