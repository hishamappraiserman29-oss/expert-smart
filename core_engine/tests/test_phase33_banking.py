"""
test_phase33_banking.py — Phase 33 CBE / Banking Collateral Pilot Tests

Covers:
  A. CollateralValuationEngine  (A01–A10)
  B. LTVCalculator              (B01–B10)
  C. CreditRiskAssessment       (C01–C08)
  D. CollateralRegistry         (D01–D08)
  E. PropertyRiskAnalyzer       (E01–E06)
  F. CBEComplianceTracker       (F01–F06)
  G. LoanServicingManager       (G01–G06)
  H. MarketMonitor              (H01–H06)
  I. BankDashboard              (I01–I04)
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from banking.collateral_engine import (
    CollateralProperty,
    CollateralQuality,
    CollateralType,
    CollateralValuationEngine,
)
from banking.ltv_calculator import CreditRiskRating, LTVCalculator, LTVTier
from banking.collateral_registry import CollateralRegistry
from banking.risk_assessment import BaselRiskWeight, PropertyRiskAnalyzer
from banking.compliance_tracker import CBEComplianceTracker, CBERequirement
from banking.loan_servicing import LoanServicingManager, LoanStatus
from banking.market_monitoring import MarketMonitor, MarketUpdate
from banking.bank_dashboard import BankDashboard


# ===========================================================================
# Helpers
# ===========================================================================

def _make_collateral(
    cid: str = "COL-001",
    market_value: float = 2_000_000,
    condition: str = "good",
    ctype: CollateralType = CollateralType.RESIDENTIAL_PROPERTY,
    existing_liens: int = 0,
) -> CollateralProperty:
    return CollateralProperty(
        collateral_id=cid,
        property_id=f"PROP-{cid}",
        owner_name="Ahmed Hassan",
        owner_id="EID-12345",
        property_type=ctype,
        location="10 Tahrir Square",
        city="Cairo",
        area_sqm=150,
        year_built=2015,
        condition=condition,
        legal_status="free",
        existing_liens=existing_liens,
        market_value=market_value,
    )


def _registry_with_entries(bank_id: str = "BANK-001") -> CollateralRegistry:
    reg = CollateralRegistry()
    for i in range(3):
        reg.register_collateral(
            collateral_id=f"COL-{i}",
            property_id=f"PROP-{i}",
            owner_id="OWN-001",
            loan_id=f"LOAN-{i}",
            bank_id=bank_id,
            collateral_value=2_000_000,
            loan_amount=1_200_000,
            ltv_ratio=60.0,
            loan_maturity_date=datetime.utcnow() + timedelta(days=3650),
        )
    return reg


# ===========================================================================
# A. CollateralValuationEngine
# ===========================================================================

class TestCollateralValuationEngine:

    def setup_method(self):
        self.engine = CollateralValuationEngine()

    def test_A01_basic_valuation_returns_result(self):
        col = _make_collateral(market_value=2_000_000)
        result = self.engine.value_collateral(col)
        assert result.collateral_id == "COL-001"
        assert result.appraised_value > 0

    def test_A02_conservative_value_is_less_than_appraised(self):
        col = _make_collateral(market_value=2_000_000)
        result = self.engine.value_collateral(col)
        assert result.conservative_value < result.appraised_value

    def test_A03_forced_sale_less_than_conservative(self):
        col = _make_collateral(market_value=2_000_000)
        result = self.engine.value_collateral(col)
        assert result.forced_sale_value < result.conservative_value

    def test_A04_good_condition_no_adjustment(self):
        col = _make_collateral(market_value=1_000_000, condition="good")
        result = self.engine.value_collateral(col)
        assert result.appraised_value == pytest.approx(1_000_000, rel=0.01)

    def test_A05_excellent_condition_adds_premium(self):
        col = _make_collateral(market_value=1_000_000, condition="excellent")
        result = self.engine.value_collateral(col)
        assert result.appraised_value == pytest.approx(1_050_000, rel=0.01)

    def test_A06_poor_condition_applies_discount(self):
        col = _make_collateral(market_value=1_000_000, condition="poor")
        result = self.engine.value_collateral(col)
        assert result.appraised_value == pytest.approx(850_000, rel=0.01)

    def test_A07_quality_rating_residential_good_is_acceptable_or_better(self):
        col = _make_collateral(condition="good", ctype=CollateralType.RESIDENTIAL_PROPERTY)
        result = self.engine.value_collateral(col)
        assert result.quality_rating in (
            CollateralQuality.EXCELLENT, CollateralQuality.GOOD, CollateralQuality.ACCEPTABLE
        )

    def test_A08_existing_liens_degrade_quality(self):
        col_no_lien = _make_collateral("NO-LIEN", existing_liens=0)
        col_lien    = _make_collateral("LIEN",    existing_liens=3)
        r1 = self.engine.value_collateral(col_no_lien)
        r2 = self.engine.value_collateral(col_lien)
        quality_order = [
            CollateralQuality.EXCELLENT, CollateralQuality.GOOD,
            CollateralQuality.ACCEPTABLE, CollateralQuality.FAIR, CollateralQuality.POOR,
        ]
        assert quality_order.index(r2.quality_rating) >= quality_order.index(r1.quality_rating)

    def test_A09_to_dict_has_required_keys(self):
        col = _make_collateral()
        result = self.engine.value_collateral(col)
        d = result.to_dict()
        for key in (
            "collateral_id", "appraised_value", "conservative_value", "forced_sale_value",
            "quality_rating", "valuation_confidence", "valuation_date", "valuation_expiry",
            "comparable_properties", "methodology", "days_valid",
        ):
            assert key in d, f"Missing key: {key}"

    def test_A10_zero_market_value_raises(self):
        col = _make_collateral(market_value=0)
        with pytest.raises(ValueError):
            self.engine.value_collateral(col)

    def test_A11_coverage_ratio_calculation(self):
        col = _make_collateral(market_value=2_000_000)
        result = self.engine.value_collateral(col)
        ratio = self.engine.calculate_coverage_ratio(result, loan_amount=1_000_000)
        assert ratio == pytest.approx(result.appraised_value / 1_000_000, rel=0.001)

    def test_A12_confidence_increases_with_more_comparables(self):
        col = _make_collateral()
        r3 = self.engine.value_collateral(col, comparable_count=3)
        r8 = self.engine.value_collateral(col, comparable_count=8)
        assert r8.valuation_confidence >= r3.valuation_confidence


# ===========================================================================
# B. LTVCalculator — ratio and tier
# ===========================================================================

class TestLTVCalculator:

    def setup_method(self):
        self.calc = LTVCalculator()

    def test_B01_prime_tier_at_50pct(self):
        r = self.calc.calculate_ltv("L1", 1_000_000, 2_000_000)
        assert r.ltv_ratio == pytest.approx(50.0)
        assert r.ltv_tier == LTVTier.PRIME

    def test_B02_prime_tier_boundary_at_70pct(self):
        r = self.calc.calculate_ltv("L2", 700_000, 1_000_000)
        assert r.ltv_tier == LTVTier.PRIME

    def test_B03_conventional_tier(self):
        r = self.calc.calculate_ltv("L3", 800_000, 1_000_000)
        assert r.ltv_tier == LTVTier.CONVENTIONAL

    def test_B04_conforming_tier(self):
        r = self.calc.calculate_ltv("L4", 900_000, 1_000_000)
        assert r.ltv_tier == LTVTier.CONFORMING

    def test_B05_high_ltv_tier(self):
        r = self.calc.calculate_ltv("L5", 970_000, 1_000_000)
        assert r.ltv_tier == LTVTier.HIGH_LTV
        assert r.to_dict()["is_over_leveraged"] is True

    def test_B06_coverage_multiple_inverse_of_ltv(self):
        r = self.calc.calculate_ltv("L6", 1_000_000, 2_000_000)
        assert r.coverage_multiple == pytest.approx(2.0)

    def test_B07_zero_collateral_raises(self):
        with pytest.raises(ValueError):
            self.calc.calculate_ltv("L7", 1_000_000, 0)

    def test_B08_to_dict_has_required_keys(self):
        r = self.calc.calculate_ltv("L8", 500_000, 1_000_000)
        d = r.to_dict()
        for key in ("loan_id", "loan_amount", "collateral_value", "ltv_ratio", "ltv_tier",
                    "coverage_multiple", "is_over_leveraged", "calculated_at"):
            assert key in d


# ===========================================================================
# C. CreditRiskAssessment
# ===========================================================================

class TestCreditRiskAssessment:

    def setup_method(self):
        self.calc = LTVCalculator()

    def _assess(self, score=750, ltv=60.0, quality="excellent", market="Strong"):
        return self.calc.assess_credit_risk(
            loan_id="TEST", borrower_credit_score=score,
            ltv_ratio=ltv, property_quality=quality,
            loan_purpose="residential_mortgage", market_conditions=market,
        )

    def test_C01_prime_borrower_low_risk_rating(self):
        a = self._assess(score=800, ltv=50.0)
        assert a.risk_rating in (CreditRiskRating.AAA, CreditRiskRating.AA, CreditRiskRating.A)

    def test_C02_poor_credit_raises_default_probability(self):
        a_good = self._assess(score=800)
        a_poor = self._assess(score=400)
        assert a_poor.default_probability > a_good.default_probability

    def test_C03_high_ltv_raises_default_probability(self):
        a_low  = self._assess(ltv=50.0)
        a_high = self._assess(ltv=97.0)
        assert a_high.default_probability > a_low.default_probability

    def test_C04_declining_market_raises_risk(self):
        a_stable   = self._assess(market="Stable")
        a_decline  = self._assess(market="Declining")
        assert a_decline.default_probability > a_stable.default_probability

    def test_C05_strong_market_lowers_risk(self):
        a_stable = self._assess(market="Stable")
        a_strong = self._assess(market="Strong")
        assert a_strong.default_probability <= a_stable.default_probability

    def test_C06_recommendations_for_high_ltv(self):
        a = self._assess(ltv=96.0)
        assert any("insurance" in r.lower() for r in a.recommendations)

    def test_C07_to_dict_has_required_keys(self):
        a = self._assess()
        d = a.to_dict()
        for key in ("loan_id", "risk_rating", "default_probability",
                    "loss_given_default", "expected_loss", "recommendations"):
            assert key in d

    def test_C08_default_probability_within_bounds(self):
        a = self._assess(score=200, ltv=100.0, quality="poor", market="Declining")
        assert 0 <= a.default_probability <= 99


# ===========================================================================
# D. CollateralRegistry
# ===========================================================================

class TestCollateralRegistry:

    def setup_method(self):
        self.reg = CollateralRegistry()

    def _register(self, cid: str, loan_id: str = "LOAN-A", bank_id: str = "BANK-X"):
        return self.reg.register_collateral(
            collateral_id=cid, property_id=f"P-{cid}", owner_id="OWN-1",
            loan_id=loan_id, bank_id=bank_id,
            collateral_value=2_000_000, loan_amount=1_200_000, ltv_ratio=60.0,
            loan_maturity_date=datetime.utcnow() + timedelta(days=3650),
        )

    def test_D01_register_returns_entry(self):
        entry = self._register("C1")
        assert entry.collateral_id == "C1"
        assert entry.status == "active"

    def test_D02_get_by_loan(self):
        self._register("C2", loan_id="LOAN-Z")
        self._register("C3", loan_id="LOAN-Z")
        self._register("C4", loan_id="LOAN-W")
        results = self.reg.get_by_loan("LOAN-Z")
        assert len(results) == 2
        assert all(e.loan_id == "LOAN-Z" for e in results)

    def test_D03_get_by_property(self):
        entry = self._register("C5")
        results = self.reg.get_by_property(entry.property_id)
        assert len(results) >= 1

    def test_D04_bank_portfolio_aggregates_values(self):
        reg = _registry_with_entries("BANK-AGG")
        portfolio = reg.get_bank_portfolio("BANK-AGG")
        assert portfolio["total_collateral_value"] == 6_000_000
        assert portfolio["total_loan_amount"] == 3_600_000

    def test_D05_update_status_changes_entry(self):
        entry = self._register("C6")
        ok = self.reg.update_status("C6", "paid_off")
        assert ok is True
        assert self.reg.get("C6").status == "paid_off"

    def test_D06_update_loan_status_affects_all(self):
        self._register("C7", loan_id="LOAN-MULTI")
        self._register("C8", loan_id="LOAN-MULTI")
        count = self.reg.update_loan_status("LOAN-MULTI", "in_default")
        assert count == 2
        for e in self.reg.get_by_loan("LOAN-MULTI"):
            assert e.status == "in_default"

    def test_D07_to_dict_has_required_keys(self):
        entry = self._register("C9")
        d = entry.to_dict()
        for key in ("collateral_id", "loan_id", "bank_id", "collateral_value",
                    "loan_amount", "ltv_ratio", "status"):
            assert key in d

    def test_D08_count_tracks_entries(self):
        reg = CollateralRegistry()
        assert reg.count() == 0
        self._register("C10")
        assert self.reg.count() >= 1


# ===========================================================================
# E. PropertyRiskAnalyzer
# ===========================================================================

class TestPropertyRiskAnalyzer:

    def setup_method(self):
        self.analyzer = PropertyRiskAnalyzer()

    def _profile(self, city="Cairo", condition="good", ptype="residential_property", ltv=70.0):
        return self.analyzer.assess(
            property_id="PROP-R", property_type=ptype,
            condition=condition, year_built=2015, city=city,
            legal_status="free", ltv_ratio=ltv,
        )

    def test_E01_returns_risk_profile(self):
        p = self._profile()
        assert p.property_id == "PROP-R"
        assert 0 <= p.overall_risk_score <= 100

    def test_E02_prime_residential_gets_low_basel_weight(self):
        p = self._profile(ltv=70.0, ptype="residential_property")
        assert p.basel_risk_weight == BaselRiskWeight.RW_35

    def test_E03_commercial_property_higher_risk_score(self):
        res = self._profile(ptype="residential_property")
        com = self._profile(ptype="commercial_property")
        assert com.overall_risk_score > res.overall_risk_score

    def test_E04_excellent_condition_lower_risk_than_poor(self):
        good = self._profile(condition="excellent")
        poor = self._profile(condition="poor")
        assert poor.overall_risk_score > good.overall_risk_score

    def test_E05_to_dict_has_required_keys(self):
        p = self._profile()
        d = p.to_dict()
        for key in ("property_id", "overall_risk_score", "basel_risk_weight",
                    "risk_factors", "risk_summary", "assessed_at"):
            assert key in d

    def test_E06_risk_factors_count(self):
        p = self._profile()
        assert len(p.risk_factors) == 6  # 6 factors defined in analyzer


# ===========================================================================
# F. CBEComplianceTracker
# ===========================================================================

class TestCBEComplianceTracker:

    def setup_method(self):
        self.tracker = CBEComplianceTracker()

    def _check(self, loan_id="L1", ltv=70.0, bank_id="BANK-1", **kw):
        return self.tracker.check_loan(loan_id=loan_id, bank_id=bank_id, ltv_ratio=ltv, **kw)

    def test_F01_fully_compliant_loan(self):
        status = self._check(ltv=70.0)
        assert status.is_compliant is True
        assert status.compliance_score == pytest.approx(100.0)

    def test_F02_ltv_breach_detected(self):
        status = self._check(ltv=90.0, collateral_type="residential_property")
        assert CBERequirement.LTV_LIMIT in status.requirements_failed
        assert status.is_compliant is False

    def test_F03_missing_documentation_detected(self):
        status = self._check(documentation_complete=False)
        assert CBERequirement.DOCUMENTATION_COMPLETE in status.requirements_failed

    def test_F04_unapproved_appraiser_detected(self):
        status = self._check(cbe_approved_appraiser=False)
        assert CBERequirement.APPRAISER_APPROVAL in status.requirements_failed

    def test_F05_compliance_score_partial(self):
        status = self._check(documentation_complete=False, property_insured=False)
        assert 0 < status.compliance_score < 100

    def test_F06_bank_summary_aggregates(self):
        self._check("LA", bank_id="BANK-SUM")
        self._check("LB", bank_id="BANK-SUM")
        self._check("LC", bank_id="BANK-SUM", ltv=95.0, documentation_complete=False)
        summary = self.tracker.get_bank_compliance_summary("BANK-SUM")
        assert summary["total_loans"] == 3
        assert "compliance_rate" in summary


# ===========================================================================
# G. LoanServicingManager
# ===========================================================================

class TestLoanServicingManager:

    def setup_method(self):
        self.mgr = LoanServicingManager()

    def test_G01_originate_loan(self):
        loan = self.mgr.originate("BANK-1", "BRW-1", "COL-1", 1_000_000, 12.0, 240)
        assert loan.principal == 1_000_000
        assert loan.status == LoanStatus.ACTIVE

    def test_G02_monthly_payment_positive(self):
        loan = self.mgr.originate("BANK-1", "BRW-2", "COL-2", 1_000_000, 12.0, 240)
        assert loan.monthly_payment > 0

    def test_G03_record_payment_reduces_balance(self):
        loan = self.mgr.originate("BANK-1", "BRW-3", "COL-3", 1_000_000, 12.0, 240,
                                   loan_id="L-PAY-001")
        payment = self.mgr.record_payment("L-PAY-001", loan.monthly_payment)
        assert payment is not None
        assert payment.outstanding_after < 1_000_000

    def test_G04_mark_delinquent_updates_status(self):
        loan = self.mgr.originate("BANK-1", "BRW-4", "COL-4", 500_000, 10.0, 120,
                                   loan_id="L-DEL-001")
        ok = self.mgr.mark_delinquent("L-DEL-001", days_past_due=30)
        assert ok is True
        assert self.mgr.get("L-DEL-001").status == LoanStatus.DELINQUENT

    def test_G05_90_days_past_due_is_in_default(self):
        loan = self.mgr.originate("BANK-1", "BRW-5", "COL-5", 500_000, 10.0, 120,
                                   loan_id="L-DEF-001")
        self.mgr.mark_delinquent("L-DEF-001", days_past_due=90)
        assert self.mgr.get("L-DEF-001").status == LoanStatus.IN_DEFAULT

    def test_G06_to_dict_has_required_keys(self):
        loan = self.mgr.originate("BANK-1", "BRW-6", "COL-6", 300_000, 8.0, 60)
        d = loan.to_dict()
        for key in ("loan_id", "principal", "interest_rate", "term_months",
                    "status", "outstanding_balance", "monthly_payment"):
            assert key in d


# ===========================================================================
# H. MarketMonitor
# ===========================================================================

class TestMarketMonitor:

    def setup_method(self):
        self.monitor = MarketMonitor()

    def test_H01_publish_update_stored(self):
        upd = MarketUpdate("U1", "cairo_residential", 105.0, 5.0, "CBE Index")
        self.monitor.publish_update(upd)
        retrieved = self.monitor.get_index("cairo_residential")
        assert retrieved is not None
        assert retrieved.index_value == 105.0

    def test_H02_no_alert_below_threshold(self):
        alerts = self.monitor.check_collateral("COL-1", "LOAN-1", 2_000_000, 1_000_000)
        assert alerts == []  # LTV = 50%, below all thresholds

    def test_H03_medium_alert_raised(self):
        alerts = self.monitor.check_collateral("COL-2", "LOAN-2", 1_000_000, 780_000)
        assert len(alerts) >= 1  # LTV = 78% > 75% medium threshold

    def test_H04_critical_alert_raised(self):
        alerts = self.monitor.check_collateral("COL-3", "LOAN-3", 1_000_000, 960_000)
        assert alerts[0].severity in ("high", "critical")

    def test_H05_resolve_alert(self):
        alerts = self.monitor.check_collateral("COL-4", "LOAN-4", 1_000_000, 900_000)
        if alerts:
            ok = self.monitor.resolve_alert(alerts[0].alert_id)
            assert ok is True
            active = self.monitor.get_active_alerts()
            assert not any(a.alert_id == alerts[0].alert_id for a in active)

    def test_H06_alert_to_dict_has_required_keys(self):
        alerts = self.monitor.check_collateral("COL-5", "LOAN-5", 1_000_000, 900_000)
        if alerts:
            d = alerts[0].to_dict()
            for key in ("alert_id", "collateral_id", "loan_id", "alert_type",
                        "severity", "message", "current_ltv", "threshold_ltv"):
                assert key in d


# ===========================================================================
# I. BankDashboard
# ===========================================================================

class TestBankDashboard:

    def setup_method(self):
        self.dash = BankDashboard()
        self.entries = [
            {"collateral_value": 2_000_000, "loan_amount": 1_200_000,
             "ltv_ratio": 60.0, "status": "active"},
            {"collateral_value": 1_500_000, "loan_amount": 1_200_000,
             "ltv_ratio": 80.0, "status": "active"},
            {"collateral_value": 1_000_000, "loan_amount": 900_000,
             "ltv_ratio": 90.0, "status": "in_default"},
        ]

    def test_I01_metrics_calculated_correctly(self):
        m = self.dash.calculate_portfolio_metrics("BANK-A", self.entries)
        assert m.number_of_loans == 3
        assert m.total_collateral_value == pytest.approx(4_500_000)
        assert m.in_default_loans == 1

    def test_I02_default_rate_calculation(self):
        m = self.dash.calculate_portfolio_metrics("BANK-B", self.entries)
        assert m.default_rate == pytest.approx(1 / 3 * 100, rel=0.01)

    def test_I03_empty_entries_produces_zero_metrics(self):
        m = self.dash.calculate_portfolio_metrics("BANK-C", [])
        assert m.number_of_loans == 0
        assert m.total_loan_amount == 0

    def test_I04_dashboard_summary_has_required_keys(self):
        self.dash.calculate_portfolio_metrics("BANK-D", self.entries)
        summary = self.dash.get_dashboard_summary("BANK-D")
        assert "bank_id" in summary
        assert "summary" in summary
        assert "alerts" in summary
