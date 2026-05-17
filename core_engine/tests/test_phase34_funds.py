"""
test_phase34_funds.py — Phase 34: FRA / Funds & Fair Value Tests

Test groups:
  A — FairValueCalculator (A01-A12)
  B — NAVCalculator (B01-B10)
  C — FundValuationEngine (C01-C10)
  D — FRAComplianceEngine (D01-D08)
  E — PortfolioManager (E01-E06)
  F — ValuationHierarchyManager (F01-F06)
  G — BenchmarkSystem (G01-G06)
  H — FundDashboard (H01-H06)
  I — RiskAnalytics (I01-I06)
"""

import sys
import os
import pytest
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from funds.fair_value_calculator import (
    FairValueCalculator, ValuationInput, FairValueInput,
    ValuationLevel, ValuationApproach,
)
from funds.nav_calculator import NAVCalculator, FundAsset, FundLiability
from funds.fund_engine import FundValuationEngine, FundType, FundStrategy
from funds.fra_compliance import FRAComplianceEngine
from funds.portfolio_manager import PortfolioManager, AllocationTarget
from funds.valuation_hierarchy import ValuationHierarchyManager
from funds.benchmark_system import BenchmarkSystem, BenchmarkIndex
from funds.fund_dashboard import FundDashboard
from funds.risk_analytics import RiskAnalytics


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fvc():
    return FairValueCalculator()


@pytest.fixture
def nav_calc():
    return NAVCalculator()


@pytest.fixture
def fund_eng():
    return FundValuationEngine()


@pytest.fixture
def fra_eng():
    return FRAComplianceEngine()


@pytest.fixture
def pm():
    return PortfolioManager()


@pytest.fixture
def vh():
    return ValuationHierarchyManager()


@pytest.fixture
def bs():
    return BenchmarkSystem()


@pytest.fixture
def fd():
    return FundDashboard()


@pytest.fixture
def ra():
    return RiskAnalytics()


def _l1_input(value=1_000_000.0):
    return ValuationInput(
        input_type=FairValueInput.QUOTED_PRICE,
        value=value, date=date.today(), source="exchange",
        observable=True, weight=1.0, confidence=1.0,
    )


def _l2_input(value=950_000.0):
    return ValuationInput(
        input_type=FairValueInput.COMPARABLE_PRICE,
        value=value, date=date.today(), source="broker",
        observable=True, weight=1.0, confidence=0.9,
    )


def _l3_input(value=900_000.0):
    return ValuationInput(
        input_type=FairValueInput.APPRAISAL,
        value=value, date=date.today(), source="appraiser",
        observable=False, weight=1.0, confidence=0.8,
    )


def _make_assets():
    return [
        FundAsset("A1", "residential", 5_000_000, 4_000_000,
                  date(2020, 1, 1), date.today()),
        FundAsset("A2", "commercial", 3_000_000, 2_500_000,
                  date(2019, 6, 1), date.today()),
    ]


def _make_liabilities():
    return [FundLiability("L1", "mortgage", 1_000_000)]


# ---------------------------------------------------------------------------
# A — FairValueCalculator
# ---------------------------------------------------------------------------

class TestFairValueCalculator:

    def test_A01_level1_determination(self, fvc):
        result = fvc.assess_fair_value("AS1", "residential", [_l1_input()])
        assert result.valuation_level == ValuationLevel.LEVEL_1

    def test_A02_level2_determination(self, fvc):
        result = fvc.assess_fair_value("AS2", "commercial", [_l2_input()])
        assert result.valuation_level == ValuationLevel.LEVEL_2

    def test_A03_level3_determination(self, fvc):
        result = fvc.assess_fair_value("AS3", "industrial", [_l3_input()])
        assert result.valuation_level == ValuationLevel.LEVEL_3

    def test_A04_fair_value_level1_no_discount(self, fvc):
        inp = _l1_input(2_000_000)
        result = fvc.assess_fair_value("AS4", "residential", [inp])
        assert result.liquidity_discount == 0.0
        assert abs(result.fair_value - 2_000_000) < 1

    def test_A05_fair_value_level3_liquidity_discount_commercial(self, fvc):
        inp = _l3_input(1_000_000)
        result = fvc.assess_fair_value("AS5", "commercial", [inp])
        # 5% liquidity discount for commercial; _l3_input has confidence=0.8
        # weighted_value = 1_000_000 * 1.0 * 0.8 = 800_000
        # fair_value = 800_000 * (1 - 0.05) = 760_000
        expected_mid = 1_000_000 * 0.8 * 0.95
        assert result.liquidity_discount == pytest.approx(0.05)
        assert result.fair_value == pytest.approx(expected_mid)

    def test_A06_weighted_average_two_inputs(self, fvc):
        i1 = ValuationInput(FairValueInput.COMPARABLE_PRICE, 1_000_000, date.today(),
                            "src", True, weight=2.0, confidence=1.0)
        i2 = ValuationInput(FairValueInput.COMPARABLE_PRICE, 2_000_000, date.today(),
                            "src", True, weight=1.0, confidence=1.0)
        result = fvc.assess_fair_value("AS6", "residential", [i1, i2])
        expected = (1_000_000 * 2 + 2_000_000 * 1) / 3
        assert result.fair_value == pytest.approx(expected, rel=1e-4)

    def test_A07_range_computed(self, fvc):
        result = fvc.assess_fair_value("AS7", "commercial", [_l2_input(1_000_000)])
        assert result.range_low < result.range_mid <= result.range_high

    def test_A08_ifrs13_compliant_flag(self, fvc):
        result = fvc.assess_fair_value("AS8", "residential", [_l1_input()])
        assert result.ifrs13_compliant is True

    def test_A09_to_dict_structure(self, fvc):
        result = fvc.assess_fair_value("AS9", "industrial", [_l3_input()])
        d = result.to_dict()
        assert "fair_value" in d
        assert "valuation_level" in d
        assert "range" in d
        assert "liquidity_discount_pct" in d

    def test_A10_disclosure_text(self, fvc):
        result = fvc.assess_fair_value("AS10", "residential", [_l1_input()])
        text = fvc.generate_ifrs13_disclosure(result)
        assert "IFRS 13" in text
        assert "AS10" in text

    def test_A11_empty_inputs_raises(self, fvc):
        with pytest.raises(ValueError):
            fvc.assess_fair_value("AS11", "residential", [])

    def test_A12_level3_industrial_discount(self, fvc):
        result = fvc.assess_fair_value("AS12", "industrial", [_l3_input(1_000_000)])
        assert result.liquidity_discount == pytest.approx(0.10)


# ---------------------------------------------------------------------------
# B — NAVCalculator
# ---------------------------------------------------------------------------

class TestNAVCalculator:

    def test_B01_basic_nav(self, nav_calc):
        assets = _make_assets()
        liabs = _make_liabilities()
        result = nav_calc.calculate_nav("F1", assets, liabs, 1_000_000)
        assert result.net_asset_value == pytest.approx(7_000_000)

    def test_B02_nav_per_share(self, nav_calc):
        assets = [FundAsset("A1", "residential", 10_000_000, 8_000_000,
                            date.today(), date.today())]
        result = nav_calc.calculate_nav("F2", assets, [], 1_000_000)
        assert result.nav_per_share == pytest.approx(10.0)

    def test_B03_zero_shares_raises(self, nav_calc):
        with pytest.raises(ValueError):
            nav_calc.calculate_nav("F3", _make_assets(), [], 0)

    def test_B04_percentage_of_fund_computed(self, nav_calc):
        assets = _make_assets()
        nav_calc.calculate_nav("F4", assets, [], 1_000_000)
        total = sum(a.current_value for a in assets)
        for asset in assets:
            expected = asset.current_value / total * 100
            assert asset.percentage_of_fund == pytest.approx(expected)

    def test_B05_nav_change_first_run_is_zero(self, nav_calc):
        result = nav_calc.calculate_nav("F5", _make_assets(), [], 500_000)
        assert result.nav_change_percentage == 0.0

    def test_B06_nav_change_second_run(self, nav_calc):
        assets1 = [FundAsset("A1", "residential", 10_000_000, 8_000_000,
                              date.today(), date.today())]
        nav_calc.calculate_nav("F6", assets1, [], 1_000_000)
        assets2 = [FundAsset("A1", "residential", 12_000_000, 8_000_000,
                              date.today(), date.today())]
        result2 = nav_calc.calculate_nav("F6", assets2, [], 1_000_000)
        assert result2.nav_change_percentage == pytest.approx(20.0)

    def test_B07_to_dict_keys(self, nav_calc):
        result = nav_calc.calculate_nav("F7", _make_assets(), _make_liabilities(), 1_000_000)
        d = result.to_dict()
        assert "net_asset_value" in d
        assert "nav_per_share" in d
        assert "assets" in d

    def test_B08_report_contains_fund_id(self, nav_calc):
        result = nav_calc.calculate_nav("FUND-X", _make_assets(), [], 1_000_000)
        report = nav_calc.generate_nav_report(result)
        assert "FUND-X" in report

    def test_B09_no_liabilities(self, nav_calc):
        assets = [FundAsset("A1", "residential", 5_000_000, 4_000_000,
                            date.today(), date.today())]
        result = nav_calc.calculate_nav("F9", assets, [], 1_000_000)
        assert result.total_liabilities == 0.0
        assert result.net_asset_value == 5_000_000.0

    def test_B10_multiple_liabilities(self, nav_calc):
        assets = [FundAsset("A1", "residential", 10_000_000, 8_000_000,
                            date.today(), date.today())]
        liabs = [
            FundLiability("L1", "mortgage", 2_000_000),
            FundLiability("L2", "fees", 500_000),
        ]
        result = nav_calc.calculate_nav("F10", assets, liabs, 1_000_000)
        assert result.net_asset_value == pytest.approx(7_500_000)


# ---------------------------------------------------------------------------
# C — FundValuationEngine
# ---------------------------------------------------------------------------

class TestFundValuationEngine:

    def _base_fund(self, eng, fid="F1", ytd=0.12, vol=0.08, rfr=0.08):
        return eng.value_fund(
            fund_id=fid, fund_name="Test REIT",
            fund_type=FundType.REIT, strategy=FundStrategy.COMMERCIAL,
            aum=100_000_000, nav=90_000_000, shares_outstanding=9_000_000,
            ytd_return=ytd, volatility=vol, fra_registered=True,
            risk_free_rate=rfr if vol > 0 else None,
        )

    def test_C01_nav_per_share(self, fund_eng):
        result = self._base_fund(fund_eng)
        assert result.nav_per_share == pytest.approx(10.0)

    def test_C02_sharpe_ratio(self, fund_eng):
        result = self._base_fund(fund_eng, ytd=0.12, vol=0.08, rfr=0.08)
        expected = (0.12 - 0.08) / 0.08
        assert result.sharpe_ratio == pytest.approx(expected)

    def test_C03_max_drawdown(self, fund_eng):
        result = self._base_fund(fund_eng, vol=0.08)
        assert result.max_drawdown == pytest.approx(0.08 * 2.5)

    def test_C04_dividend_yield(self, fund_eng):
        result = fund_eng.value_fund(
            "F4", "Test Fund", FundType.REIT, FundStrategy.RESIDENTIAL,
            50_000_000, 10_000_000, 1_000_000, 0.10, 0.05,
            dividend_per_share=0.5, risk_free_rate=0.08,
        )
        # nav_per_share = 10; yield = 0.5/10 * 100 = 5%
        assert result.dividend_yield == pytest.approx(5.0)

    def test_C05_zero_volatility_sharpe(self, fund_eng):
        result = self._base_fund(fund_eng, vol=0.0)
        assert result.sharpe_ratio == 0.0

    def test_C06_negative_shares_raises(self, fund_eng):
        with pytest.raises(ValueError):
            fund_eng.value_fund("F6", "Bad Fund", FundType.MUTUAL_FUND,
                                FundStrategy.MIXED, 1_000_000, 1_000_000, -1,
                                0.10, 0.05)

    def test_C07_to_dict_structure(self, fund_eng):
        result = self._base_fund(fund_eng, "F7")
        d = result.to_dict()
        assert "performance" in d
        assert "income" in d
        assert "fra_registered" in d

    def test_C08_compare_funds(self, fund_eng):
        r1 = self._base_fund(fund_eng, "FA", ytd=0.15, vol=0.08)
        r2 = self._base_fund(fund_eng, "FB", ytd=0.05, vol=0.04)
        comparison = fund_eng.compare_funds([r1, r2])
        assert comparison["best_return"]["fund_id"] == "FA"
        assert comparison["fund_count"] == 2

    def test_C09_fund_type_values(self, fund_eng):
        for ft in FundType:
            result = fund_eng.value_fund(
                f"F-{ft.value}", "Fund", ft, FundStrategy.MIXED,
                1_000_000, 1_000_000, 100_000, 0.10, 0.05,
                risk_free_rate=0.08,
            )
            assert result.fund_type == ft

    def test_C10_all_fund_strategies(self, fund_eng):
        for fs in FundStrategy:
            result = fund_eng.value_fund(
                f"F-{fs.value}", "Fund", FundType.REIT, fs,
                1_000_000, 1_000_000, 100_000, 0.10, 0.05,
                risk_free_rate=0.08,
            )
            assert result.strategy == fs

    def test_C11_missing_risk_free_rate_raises(self, fund_eng):
        with pytest.raises(ValueError, match="risk_free_rate is required"):
            fund_eng.value_fund(
                "F11", "Bad Fund", FundType.REIT, FundStrategy.MIXED,
                1_000_000, 1_000_000, 100_000, 0.10, 0.05,
                # risk_free_rate omitted — volatility=0.05 > 0, must raise
            )


# ---------------------------------------------------------------------------
# D — FRAComplianceEngine
# ---------------------------------------------------------------------------

class TestFRAComplianceEngine:

    def test_D01_fully_compliant(self, fra_eng):
        data = {"fra_registered": True, "has_annual_audit": True, "ifrs13_disclosure": True}
        result = fra_eng.check_compliance("FUND-1", data)
        assert result.overall_status == "compliant"
        assert result.compliance_percentage == pytest.approx(100.0)

    def test_D02_not_fully_compliant_missing_three(self, fra_eng):
        # 3 failed out of 18 = 83.3% → partially_compliant (not fully compliant)
        data = {"fra_registered": False, "has_annual_audit": False, "ifrs13_disclosure": False}
        result = fra_eng.check_compliance("FUND-2", data)
        assert result.overall_status != "compliant"
        assert len(result.failed_checks) == 3

    def test_D03_partially_compliant(self, fra_eng):
        data = {"fra_registered": True, "has_annual_audit": False, "ifrs13_disclosure": False}
        result = fra_eng.check_compliance("FUND-3", data)
        # 16/18 = 88.9% → partially_compliant
        assert result.overall_status in ("compliant", "partially_compliant")
        assert result.compliance_percentage >= 75.0

    def test_D04_total_checks_is_18(self, fra_eng):
        result = fra_eng.check_compliance("FUND-4", {})
        assert result.total_checks == 18

    def test_D05_issues_listed_when_not_registered(self, fra_eng):
        result = fra_eng.check_compliance("FUND-5", {"fra_registered": False})
        assert any("not registered" in i.lower() for i in result.issues)

    def test_D06_compliance_report_text(self, fra_eng):
        data = {"fra_registered": True, "has_annual_audit": True, "ifrs13_disclosure": True}
        result = fra_eng.check_compliance("FUND-6", data)
        report = fra_eng.generate_compliance_report(result)
        assert "FRA Compliance" in report
        assert "FUND-6" in report

    def test_D07_next_audit_date_is_future(self, fra_eng):
        result = fra_eng.check_compliance("FUND-7", {"fra_registered": True})
        assert result.next_audit_date > result.check_date

    def test_D08_get_requirements_returns_18(self, fra_eng):
        reqs = fra_eng.get_requirements()
        assert len(reqs) == 18


# ---------------------------------------------------------------------------
# E — PortfolioManager
# ---------------------------------------------------------------------------

class TestPortfolioManager:

    def _targets(self):
        return [
            AllocationTarget("F1", 0.50, 0.40, 0.60),
            AllocationTarget("F2", 0.30, 0.20, 0.40),
            AllocationTarget("F3", 0.20, 0.10, 0.30),
        ]

    def test_E01_create_portfolio(self, pm):
        pm.create_portfolio("P1", self._targets())
        assert "P1" in pm.list_portfolios()

    def test_E02_weights_not_summing_raises(self, pm):
        bad = [AllocationTarget("F1", 0.40, 0.30, 0.50),
               AllocationTarget("F2", 0.40, 0.30, 0.50)]
        with pytest.raises(ValueError):
            pm.create_portfolio("P-BAD", bad)

    def test_E03_snapshot_total_nav(self, pm):
        pm.create_portfolio("P2", self._targets())
        navs = {"F1": 500_000, "F2": 300_000, "F3": 200_000}
        snap = pm.get_snapshot("P2", navs)
        assert snap.total_nav == pytest.approx(1_000_000)

    def test_E04_no_drift_when_on_target(self, pm):
        pm.create_portfolio("P3", self._targets())
        navs = {"F1": 500_000, "F2": 300_000, "F3": 200_000}
        snap = pm.get_snapshot("P3", navs)
        assert not snap.rebalance_required

    def test_E05_drift_triggers_rebalance(self, pm):
        pm.create_portfolio("P4", self._targets())
        # F1 now 80% — far from 50% target
        navs = {"F1": 800_000, "F2": 100_000, "F3": 100_000}
        snap = pm.get_snapshot("P4", navs)
        assert snap.rebalance_required

    def test_E06_unknown_portfolio_raises(self, pm):
        with pytest.raises(ValueError):
            pm.get_snapshot("NONEXISTENT", {"F1": 1_000})


# ---------------------------------------------------------------------------
# F — ValuationHierarchyManager
# ---------------------------------------------------------------------------

class TestValuationHierarchyManager:

    def test_F01_register_and_retrieve(self, vh):
        entry = vh.register_asset("AS1", "F1", "residential",
                                  ValuationLevel.LEVEL_1, 1_000_000, "2025-01-01")
        assert vh.get_asset("AS1") is not None
        assert entry.valuation_level == ValuationLevel.LEVEL_1

    def test_F02_fund_summary_totals(self, vh):
        vh.register_asset("AS2", "F2", "commercial", ValuationLevel.LEVEL_2, 500_000, "2025-01-01")
        vh.register_asset("AS3", "F2", "industrial", ValuationLevel.LEVEL_3, 300_000, "2025-01-01")
        summary = vh.get_fund_summary("F2")
        assert summary.total_fair_value == pytest.approx(800_000)
        assert summary.level_2_value == pytest.approx(500_000)
        assert summary.level_3_value == pytest.approx(300_000)

    def test_F03_level3_concentration_breach(self, vh):
        vh.register_asset("AS4", "F3", "commercial", ValuationLevel.LEVEL_3, 800_000, "2025-01-01")
        vh.register_asset("AS5", "F3", "residential", ValuationLevel.LEVEL_1, 200_000, "2025-01-01")
        summary = vh.get_fund_summary("F3")
        # L3 = 80% > 30% limit
        assert summary.concentration_breach is True

    def test_F04_update_level(self, vh):
        vh.register_asset("AS6", "F4", "residential", ValuationLevel.LEVEL_3, 500_000, "2025-01-01")
        updated = vh.update_level("AS6", ValuationLevel.LEVEL_2, 520_000, "2025-06-01")
        assert updated is True
        assert vh.get_asset("AS6").valuation_level == ValuationLevel.LEVEL_2

    def test_F05_update_nonexistent_returns_false(self, vh):
        result = vh.update_level("NOASSET", ValuationLevel.LEVEL_1, 100, "2025-01-01")
        assert result is False

    def test_F06_count(self, vh):
        initial = vh.count()
        vh.register_asset("AS99", "F9", "residential", ValuationLevel.LEVEL_1, 100_000, "2025-01-01")
        assert vh.count() == initial + 1


# ---------------------------------------------------------------------------
# G — BenchmarkSystem
# ---------------------------------------------------------------------------

class TestBenchmarkSystem:

    def _index(self, iid="IDX-1"):
        return BenchmarkIndex(
            index_id=iid, name="EGX Real Estate Index",
            ytd_return=0.10, one_year_return=0.12, three_year_return=0.35,
            asset_class="real_estate", region="Egypt",
        )

    def test_G01_register_and_retrieve(self, bs):
        bs.register_index(self._index("IDX-G01"))
        assert bs.get_index("IDX-G01") is not None

    def test_G02_compare_outperforming(self, bs):
        bs.register_index(self._index("IDX-G02"))
        result = bs.compare_fund("FUND-G02", 0.15, 0.05, "IDX-G02")
        assert result.outperforming is True
        assert result.alpha == pytest.approx(0.05)

    def test_G03_compare_underperforming(self, bs):
        bs.register_index(self._index("IDX-G03"))
        result = bs.compare_fund("FUND-G03", 0.05, 0.05, "IDX-G03")
        assert result.outperforming is False

    def test_G04_unknown_index_raises(self, bs):
        with pytest.raises(ValueError):
            bs.compare_fund("F", 0.10, 0.05, "NO-IDX")

    def test_G05_to_dict_keys(self, bs):
        bs.register_index(self._index("IDX-G05"))
        result = bs.compare_fund("F-G05", 0.12, 0.04, "IDX-G05")
        d = result.to_dict()
        assert "alpha_pct" in d
        assert "information_ratio" in d

    def test_G06_count(self, bs):
        bs.register_index(self._index("IDX-G06a"))
        bs.register_index(self._index("IDX-G06b"))
        assert bs.count() >= 2


# ---------------------------------------------------------------------------
# H — FundDashboard
# ---------------------------------------------------------------------------

class TestFundDashboard:

    def _make_results(self, fund_eng):
        r1 = fund_eng.value_fund("FA", "Fund A", FundType.REIT,
                                 FundStrategy.COMMERCIAL, 100_000_000,
                                 90_000_000, 9_000_000, 0.15, 0.08,
                                 fra_registered=True, risk_free_rate=0.08)
        r2 = fund_eng.value_fund("FB", "Fund B", FundType.OPEN_ENDED,
                                 FundStrategy.RESIDENTIAL, 50_000_000,
                                 45_000_000, 4_500_000, 0.05, 0.04,
                                 fra_registered=True, risk_free_rate=0.08)
        return [r1, r2]

    def test_H01_total_aum(self, fd, fund_eng):
        results = self._make_results(fund_eng)
        metrics = fd.compute_metrics("MGR-1", results)
        assert metrics.total_aum == pytest.approx(150_000_000)

    def test_H02_top_performer(self, fd, fund_eng):
        results = self._make_results(fund_eng)
        metrics = fd.compute_metrics("MGR-2", results)
        assert metrics.top_performer_id == "FA"

    def test_H03_compliance_rate_all_registered(self, fd, fund_eng):
        results = self._make_results(fund_eng)
        metrics = fd.compute_metrics("MGR-3", results)
        assert metrics.compliance_rate == pytest.approx(1.0)

    def test_H04_empty_funds(self, fd):
        metrics = fd.compute_metrics("MGR-4", [])
        assert metrics.fund_count == 0
        assert metrics.total_aum == 0.0

    def test_H05_get_snapshot(self, fd, fund_eng):
        results = self._make_results(fund_eng)
        fd.compute_metrics("MGR-5", results)
        snap = fd.get_snapshot("MGR-5")
        assert snap is not None
        assert snap.fund_count == 2

    def test_H06_report_text(self, fd, fund_eng):
        results = self._make_results(fund_eng)
        metrics = fd.compute_metrics("MGR-6", results)
        report = fd.generate_summary_report(metrics)
        assert "MGR-6" in report
        assert "Sharpe" in report


# ---------------------------------------------------------------------------
# I — RiskAnalytics
# ---------------------------------------------------------------------------

class TestRiskAnalytics:

    def test_I01_var_95_basic(self, ra):
        result = ra.calculate_var("F1", 10_000_000, 0.01, 0.95, 1)
        assert result.var_percentage == pytest.approx(1.645 * 0.01, rel=1e-3)
        assert result.var_amount == pytest.approx(10_000_000 * 1.645 * 0.01, rel=1e-3)

    def test_I02_var_99(self, ra):
        result = ra.calculate_var("F2", 10_000_000, 0.01, 0.99, 1)
        assert result.var_percentage == pytest.approx(2.326 * 0.01, rel=1e-3)

    def test_I03_var_horizon_scales_with_sqrt(self, ra):
        r1 = ra.calculate_var("F3", 1_000_000, 0.01, 0.95, 1)
        r5 = ra.calculate_var("F3", 1_000_000, 0.01, 0.95, 4)
        assert r5.var_percentage == pytest.approx(r1.var_percentage * 2, rel=1e-3)

    def test_I04_invalid_confidence_raises(self, ra):
        with pytest.raises(ValueError):
            ra.calculate_var("F4", 1_000_000, 0.01, 0.80)

    def test_I05_risk_profile_categories(self, ra):
        low_p = ra.build_risk_profile("F5", 0.004, 1_000_000)
        high_p = ra.build_risk_profile("F6", 0.02, 1_000_000)
        assert low_p.risk_category == "low"
        assert high_p.risk_category in ("elevated", "high")

    def test_I06_correlation_matrix_diagonal_is_one(self, ra):
        returns = [[0.01, 0.02, -0.01, 0.03], [0.01, 0.02, -0.01, 0.03]]
        result = ra.correlation_matrix(["F1", "F2"], returns)
        matrix = result["correlation_matrix"]
        assert matrix["F1"]["F1"] == pytest.approx(1.0)
        assert matrix["F2"]["F2"] == pytest.approx(1.0)
