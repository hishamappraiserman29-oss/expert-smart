"""Phase 11 E2E Tests — Complete Portfolio Analysis Pipeline"""
from __future__ import annotations

import sys
from pathlib import Path

_CORE = Path(__file__).resolve().parents[1]   # …/core_engine/
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import os
os.environ.setdefault("JWT_SECRET", "test-secret-e2e-bundle")
os.chdir(str(_CORE))

from adapters.portfolio import PortfolioBuilder
from bridge_api import app
from auth.tokens import generate_token as _gen_token
_AUTH_HDR = {"Authorization": f"Bearer {_gen_token('test-user-e2e')}"}


def test_e2e_portfolio_build_and_analyze():
    """E2E: Build 5-property portfolio, calculate metrics, verify outputs."""
    builder = PortfolioBuilder("Cairo Mixed Portfolio")

    properties_data = [
        ("P1", "Downtown Apt",      "residential", 3_645_000, "high",   365_000, 400_000),
        ("P2", "Giza Office",       "commercial",  7_750_000, "high",   580_000, 650_000),
        ("P3", "New Cairo Land",    "land",        2_500_000, "medium", 100_000, 100_000),
        ("P4", "6th Oct Villa",     "residential", 4_200_000, "high",   420_000, 460_000),
        ("P5", "Alexandria Retail", "commercial",  3_500_000, "medium", 210_000, 280_000),
    ]
    for prop_id, name, ptype, value, conf, noi, income in properties_data:
        builder.add_property(prop_id, name, ptype, value, conf, noi, income)

    builder.calculate_metrics()
    summary = builder.get_portfolio_summary()

    assert summary["metrics"]["total_portfolio_value"] == 21_595_000
    assert summary["metrics"]["number_of_properties"]  == 5
    assert summary["metrics"]["total_annual_noi"]      == 1_675_000
    assert len(summary["properties"])                  == 5

    div_score = builder.get_diversification_score()
    assert 0 < div_score < 1

    print(f"✓ E2E Portfolio (5 props, {summary['metrics']['total_portfolio_value']:,.0f} EGP)")
    print(f"  - Cap Rate: {summary['metrics']['portfolio_cap_rate']*100:.2f}%")
    print(f"  - Diversification: {div_score:.4f}")


def test_e2e_api_portfolio_endpoint():
    """E2E: Call POST /api/valuation/portfolio with 3 properties."""
    with app.test_client() as client:
        response = client.post("/api/valuation/portfolio", json={
            "portfolio_name": "Test Portfolio E2E",
            "properties": [
                {"property_id": "P1", "property_name": "Property 1",
                 "property_type": "residential", "valuation_value": 3_645_000,
                 "valuation_confidence": "high",
                 "annual_noi": 365_000, "annual_gross_income": 400_000},
                {"property_id": "P2", "property_name": "Property 2",
                 "property_type": "commercial", "valuation_value": 7_750_000,
                 "valuation_confidence": "high",
                 "annual_noi": 580_000, "annual_gross_income": 650_000},
                {"property_id": "P3", "property_name": "Property 3",
                 "property_type": "land", "valuation_value": 2_500_000,
                 "valuation_confidence": "medium",
                 "annual_noi": 100_000, "annual_gross_income": 100_000},
            ],
            "generate_report": False,
        }, headers=_AUTH_HDR)

        assert response.status_code == 200
        data = response.get_json()

        assert data["status"]  == "success"
        assert "portfolio"     in data
        assert data["portfolio"]["metrics"]["total_portfolio_value"] == 13_895_000
        assert "diversification_score" in data

    print("✓ E2E API /api/valuation/portfolio (200 OK, 3 properties)")


def test_e2e_api_portfolio_with_report():
    """E2E: Call POST /api/valuation/portfolio with report generation."""
    with app.test_client() as client:
        response = client.post("/api/valuation/portfolio", json={
            "portfolio_name": "Portfolio with Report",
            "properties": [
                {"property_id": "P1", "property_name": "Property 1",
                 "property_type": "residential", "valuation_value": 3_645_000,
                 "valuation_confidence": "high",
                 "annual_noi": 365_000, "annual_gross_income": 400_000},
                {"property_id": "P2", "property_name": "Property 2",
                 "property_type": "commercial", "valuation_value": 7_750_000,
                 "valuation_confidence": "high",
                 "annual_noi": 580_000, "annual_gross_income": 650_000},
            ],
            "generate_report": True,
        }, headers=_AUTH_HDR)

        assert response.status_code == 200
        data = response.get_json()

        assert data["status"]        == "success"
        assert data["report_id"]     is not None
        assert data["download_url"]  is not None

    print(f"✓ E2E API with report generation — report_id: {data['report_id'][:8]}…")


def test_e2e_portfolio_vs_phase_4_income():
    """E2E: Verify portfolio cap rate identity (NOI / value)."""
    builder = PortfolioBuilder("Test")
    builder.add_property("P1", "Prop1", "residential", 3_645_000, "high", 365_000, 400_000)
    builder.add_property("P2", "Prop2", "commercial",  7_750_000, "high", 580_000, 650_000)
    builder.calculate_metrics()

    pv  = builder.metrics.total_portfolio_value
    noi = builder.metrics.total_annual_noi
    cr  = builder.metrics.portfolio_cap_rate

    assert abs(noi / pv - cr) < 0.0001

    p1_cap = 365_000 / 3_645_000
    p2_cap = 580_000 / 7_750_000

    print("✓ E2E Portfolio cap rate verification")
    print(f"  - P1 cap rate: {p1_cap*100:.2f}%")
    print(f"  - P2 cap rate: {p2_cap*100:.2f}%")
    print(f"  - Portfolio:   {cr*100:.2f}%")


def test_e2e_property_weights():
    """E2E: Verify property weights sum to 1.0."""
    builder = PortfolioBuilder("Weights Test")
    builder.add_property("P1", "Prop1", "residential", 3_000_000, "high",   300_000, 330_000)
    builder.add_property("P2", "Prop2", "commercial",  7_000_000, "high",   525_000, 700_000)
    builder.add_property("P3", "Prop3", "land",        2_000_000, "medium", 100_000, 100_000)

    builder.calculate_metrics()

    total_weight = sum(p.portfolio_weight for p in builder.properties)
    assert abs(total_weight - 1.0) < 0.0001

    print(f"✓ E2E Property weights (sum = {total_weight:.6f})")


def test_e2e_confidence_distribution():
    """E2E: Verify confidence counts and high-confidence value."""
    builder = PortfolioBuilder("Confidence Test")
    builder.add_property("P1", "Prop1", "residential", 3_645_000, "high",   365_000, 400_000)
    builder.add_property("P2", "Prop2", "commercial",  7_750_000, "high",   580_000, 650_000)
    builder.add_property("P3", "Prop3", "land",        2_500_000, "medium", 100_000, 100_000)
    builder.add_property("P4", "Prop4", "residential", 1_500_000, "low",     75_000, 100_000)

    builder.calculate_metrics()

    assert builder.metrics.high_confidence_count   == 2
    assert builder.metrics.medium_confidence_count == 1
    assert builder.metrics.low_confidence_count    == 1
    assert builder.metrics.high_confidence_value   == 3_645_000 + 7_750_000

    print(f"✓ E2E Confidence distribution (high={builder.metrics.high_confidence_count}, "
          f"medium={builder.metrics.medium_confidence_count}, "
          f"low={builder.metrics.low_confidence_count})")


def test_e2e_diversification_metrics():
    """E2E: Verify HHI = 0.5 for equal-weighted two-property portfolio."""
    builder = PortfolioBuilder("Diversification Test")
    builder.add_property("P1", "Prop1", "residential", 5_000_000, "high", 500_000, 550_000)
    builder.add_property("P2", "Prop2", "commercial",  5_000_000, "high", 375_000, 500_000)

    builder.calculate_metrics()

    assert abs(builder.metrics.herfindahl_index - 0.5) < 0.01

    div_score = builder.get_diversification_score()
    assert abs(div_score - 0.5) < 0.01

    print(f"✓ E2E Equal-weighted HHI = {builder.metrics.herfindahl_index:.4f}, "
          f"Diversification = {div_score:.4f}")


def test_e2e_type_distribution():
    """E2E: Verify value distribution by property type."""
    builder = PortfolioBuilder("Type Distribution Test")
    builder.add_property("P1", "Res1",  "residential", 3_000_000, "high",   300_000, 330_000)
    builder.add_property("P2", "Res2",  "residential", 2_000_000, "high",   200_000, 220_000)
    builder.add_property("P3", "Com1",  "commercial",  8_000_000, "high",   600_000, 800_000)
    builder.add_property("P4", "Land1", "land",        2_000_000, "medium", 100_000, 100_000)

    builder.calculate_metrics()

    assert builder.metrics.value_by_type["residential"] == 5_000_000
    assert builder.metrics.value_by_type["commercial"]  == 8_000_000
    assert builder.metrics.value_by_type["land"]        == 2_000_000
    assert sum(builder.metrics.value_by_type.values())  == 15_000_000

    res_pct  = builder.metrics.type_percentages["residential"]
    com_pct  = builder.metrics.type_percentages["commercial"]
    land_pct = builder.metrics.type_percentages["land"]

    assert abs(res_pct  - (5_000_000 / 15_000_000)) < 0.001
    assert abs(com_pct  - (8_000_000 / 15_000_000)) < 0.001
    assert abs(land_pct - (2_000_000 / 15_000_000)) < 0.001

    print(f"✓ E2E Type distribution (Res {res_pct*100:.1f}%, "
          f"Com {com_pct*100:.1f}%, Land {land_pct*100:.1f}%)")


def test_e2e_concentration_ratio():
    """E2E: Verify concentration ratio (largest property dominance)."""
    builder = PortfolioBuilder("Concentration Test")
    builder.add_property("P1", "Large", "commercial",  8_000_000, "high", 600_000, 800_000)
    builder.add_property("P2", "Small", "residential", 2_000_000, "high", 200_000, 220_000)

    builder.calculate_metrics()

    assert abs(builder.metrics.concentration_ratio - 0.8) < 0.01

    print(f"✓ E2E Concentration ratio = {builder.metrics.concentration_ratio*100:.1f}% "
          f"(Large dominates)")


# ── Runner ────────────────────────────────────────────────────────────────────

def test_all_phase_11_e2e():
    """Run all Phase 11 E2E tests."""
    print("\n=== Phase 11 E2E Tests ===\n")
    tests = [
        test_e2e_portfolio_build_and_analyze,
        test_e2e_api_portfolio_endpoint,
        test_e2e_api_portfolio_with_report,
        test_e2e_portfolio_vs_phase_4_income,
        test_e2e_property_weights,
        test_e2e_confidence_distribution,
        test_e2e_diversification_metrics,
        test_e2e_type_distribution,
        test_e2e_concentration_ratio,
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
        print("\n✅ All Phase 11 E2E tests passed!")


if __name__ == "__main__":
    test_all_phase_11_e2e()
