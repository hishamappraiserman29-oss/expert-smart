"""
test_saas_readiness.py — Phase 26: Multi-Tenant SaaS Readiness Tests

Covers:
  A. TenantManager  (A01–A12)
  B. TenantIsolationValidator  (B01–B08)
  C. BillingEngine  (C01–C10)
  D. SubscriptionManager  (D01–D08)
  E. TenantDashboard  (E01–E07)
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from saas.tenant_manager import (
    TenantManager, TenantStatus, UserRole, SubscriptionTier,
    Tenant, TenantUser, TenantSubscription, TIER_LIMITS,
)
from saas.tenant_isolation import TenantIsolationValidator, TenantContext, get_current_tenant_id
from saas.billing_engine import BillingEngine, UsageMetric, Invoice
from saas.subscription_manager import SubscriptionManager
from saas.dashboard import TenantDashboard


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def manager():
    return TenantManager()


@pytest.fixture
def billing():
    return BillingEngine()


@pytest.fixture
def tenant_with_manager(manager):
    t = manager.create_tenant("Acme Corp", "acme.com", tier=SubscriptionTier.PROFESSIONAL)
    return t, manager


@pytest.fixture
def sub_manager(manager, billing):
    return SubscriptionManager(tenant_manager=manager, billing_engine=billing)


@pytest.fixture
def dashboard(manager, billing, sub_manager):
    return TenantDashboard(
        tenant_manager=manager,
        billing_engine=billing,
        subscription_manager=sub_manager,
    )


# ===========================================================================
# A. TenantManager
# ===========================================================================

class TestTenantManager:

    def test_A01_create_tenant_returns_tenant(self, manager):
        t = manager.create_tenant("TestCo", "test.com")
        assert isinstance(t, Tenant)
        assert t.name == "TestCo"
        assert t.domain == "test.com"

    def test_A02_create_tenant_default_status_active(self, manager):
        t = manager.create_tenant("TestCo", "test.com")
        assert t.status == TenantStatus.ACTIVE

    def test_A03_create_trial_tenant_sets_trial_status(self, manager):
        t = manager.create_tenant("TrialCo", "trial.com", trial_days=14)
        assert t.status == TenantStatus.TRIAL
        assert t.subscription.expires_at is not None

    def test_A04_duplicate_domain_raises(self, manager):
        manager.create_tenant("Co1", "same.com")
        with pytest.raises(ValueError, match="already registered"):
            manager.create_tenant("Co2", "same.com")

    def test_A05_get_tenant_by_id(self, manager):
        t = manager.create_tenant("X", "x.com")
        fetched = manager.get_tenant(t.tenant_id)
        assert fetched is t

    def test_A06_get_tenant_by_domain(self, manager):
        t = manager.create_tenant("Y", "y.com")
        fetched = manager.get_tenant_by_domain("y.com")
        assert fetched is t

    def test_A07_update_tenant_status(self, manager):
        t = manager.create_tenant("Z", "z.com")
        updated = manager.update_tenant_status(t.tenant_id, TenantStatus.SUSPENDED)
        assert updated.status == TenantStatus.SUSPENDED

    def test_A08_delete_tenant(self, manager):
        t = manager.create_tenant("Del", "del.com")
        assert manager.delete_tenant(t.tenant_id) is True
        assert manager.get_tenant(t.tenant_id) is None

    def test_A09_add_user_to_tenant(self, manager):
        t = manager.create_tenant("U", "u.com", tier=SubscriptionTier.STARTER)
        user = manager.add_user(t.tenant_id, "alice@u.com", UserRole.ANALYST)
        assert user.email == "alice@u.com"
        assert user.role == UserRole.ANALYST

    def test_A10_user_limit_enforced(self, manager):
        t = manager.create_tenant("Lim", "lim.com", tier=SubscriptionTier.FREE)
        limit = TIER_LIMITS[SubscriptionTier.FREE]["max_users"]
        for i in range(limit):
            manager.add_user(t.tenant_id, f"u{i}@lim.com")
        with pytest.raises(ValueError, match="user limit"):
            manager.add_user(t.tenant_id, "overflow@lim.com")

    def test_A11_remove_user_deactivates(self, manager):
        t = manager.create_tenant("R", "r.com")
        user = manager.add_user(t.tenant_id, "bob@r.com")
        assert manager.remove_user(t.tenant_id, user.user_id) is True
        fetched = manager.get_user(t.tenant_id, user.user_id)
        assert fetched.is_active is False

    def test_A12_get_stats_counts_correctly(self, manager):
        manager.create_tenant("S1", "s1.com")
        manager.create_tenant("S2", "s2.com", trial_days=7)
        stats = manager.get_stats()
        assert stats["total_tenants"] == 2
        assert stats["active_tenants"] == 1
        assert stats["trial_tenants"] == 1


# ===========================================================================
# B. TenantIsolationValidator
# ===========================================================================

class TestTenantIsolation:

    def test_B01_active_tenant_validates(self, manager):
        t = manager.create_tenant("V", "v.com")
        validator = TenantIsolationValidator(manager)
        assert validator.validate_tenant_active(t.tenant_id) is True

    def test_B02_suspended_tenant_fails_validation(self, manager):
        t = manager.create_tenant("W", "w.com")
        manager.update_tenant_status(t.tenant_id, TenantStatus.SUSPENDED)
        validator = TenantIsolationValidator(manager)
        assert validator.validate_tenant_active(t.tenant_id) is False

    def test_B03_nonexistent_tenant_fails_validation(self, manager):
        validator = TenantIsolationValidator(manager)
        assert validator.validate_tenant_active("ghost-id") is False

    def test_B04_user_belongs_to_correct_tenant(self, manager):
        t = manager.create_tenant("P", "p.com")
        user = manager.add_user(t.tenant_id, "carol@p.com")
        validator = TenantIsolationValidator(manager)
        assert validator.validate_user_belongs_to_tenant(t.tenant_id, user.user_id) is True

    def test_B05_cross_tenant_access_denied(self, manager):
        t1 = manager.create_tenant("T1", "t1.com")
        t2 = manager.create_tenant("T2", "t2.com")
        user = manager.add_user(t1.tenant_id, "x@t1.com")
        validator = TenantIsolationValidator(manager)
        assert validator.validate_user_belongs_to_tenant(t2.tenant_id, user.user_id) is False

    def test_B06_resource_access_same_tenant(self, manager):
        validator = TenantIsolationValidator(manager)
        assert validator.validate_resource_access("tenant-A", "tenant-A") is True

    def test_B07_resource_access_cross_tenant_denied(self, manager):
        validator = TenantIsolationValidator(manager)
        assert validator.validate_resource_access("tenant-A", "tenant-B") is False

    def test_B08_tenant_context_manager(self):
        with TenantContext("my-tenant"):
            assert get_current_tenant_id() == "my-tenant"
        assert get_current_tenant_id() is None


# ===========================================================================
# C. BillingEngine
# ===========================================================================

class TestBillingEngine:

    def test_C01_record_usage_stores_record(self, billing):
        r = billing.record_usage("t1", UsageMetric.VALUATION, 5.0)
        assert r.quantity == 5.0
        assert r.metric == UsageMetric.VALUATION

    def test_C02_get_usage_returns_records(self, billing):
        billing.record_usage("t1", UsageMetric.API_CALL, 10.0)
        billing.record_usage("t1", UsageMetric.API_CALL, 20.0)
        records = billing.get_usage("t1", metric=UsageMetric.API_CALL)
        assert len(records) == 2

    def test_C03_usage_isolation_between_tenants(self, billing):
        billing.record_usage("t1", UsageMetric.VALUATION, 3.0)
        billing.record_usage("t2", UsageMetric.VALUATION, 7.0)
        r1 = billing.get_usage("t1")
        r2 = billing.get_usage("t2")
        assert len(r1) == 1
        assert len(r2) == 1

    def test_C04_usage_summary_aggregates_correctly(self, billing):
        billing.record_usage("t1", UsageMetric.VALUATION, 3.0)
        billing.record_usage("t1", UsageMetric.VALUATION, 2.0)
        billing.record_usage("t1", UsageMetric.API_CALL, 100.0)
        summary = billing.get_usage_summary("t1")
        assert summary["valuation"] == 5.0
        assert summary["api_call"] == 100.0

    def test_C05_generate_invoice_has_correct_structure(self, billing):
        billing.record_usage("t1", UsageMetric.VALUATION, 5.0)
        inv = billing.generate_invoice("t1", "professional")
        assert isinstance(inv, Invoice)
        assert inv.tenant_id == "t1"
        assert inv.tier == "professional"

    def test_C06_invoice_total_includes_base_price(self, billing):
        inv = billing.generate_invoice("t1", "starter")
        assert inv.base_price == 49.0
        assert inv.total_amount >= inv.base_price

    def test_C07_mark_paid_sets_paid_flag(self, billing):
        inv = billing.generate_invoice("t1", "professional")
        assert billing.mark_paid(inv.invoice_id) is True
        invoices = billing.get_invoices("t1")
        assert invoices[0].paid is True

    def test_C08_outstanding_balance_excludes_paid(self, billing):
        billing.record_usage("t1", UsageMetric.VALUATION, 1.0)
        inv = billing.generate_invoice("t1", "professional")
        billing.mark_paid(inv.invoice_id)
        assert billing.get_outstanding_balance("t1") == 0.0

    def test_C09_invoice_to_dict_has_required_keys(self, billing):
        inv = billing.generate_invoice("t1", "starter")
        d = inv.to_dict()
        for key in ("invoice_id", "tenant_id", "tier", "total_amount", "paid", "line_items"):
            assert key in d

    def test_C10_usage_filtered_by_since(self, billing):
        past = datetime.utcnow() - timedelta(days=40)
        r = billing.record_usage("t1", UsageMetric.VALUATION, 1.0)
        r.timestamp = past
        billing.record_usage("t1", UsageMetric.VALUATION, 2.0)  # now
        recent = billing.get_usage("t1", since=datetime.utcnow() - timedelta(days=1))
        assert len(recent) == 1
        assert recent[0].quantity == 2.0


# ===========================================================================
# D. SubscriptionManager
# ===========================================================================

class TestSubscriptionManager:

    def test_D01_start_trial_sets_trial_status(self, manager, sub_manager):
        t = manager.create_tenant("T", "trial-sm.com")
        updated = sub_manager.start_trial(t.tenant_id, trial_days=14)
        assert updated.status == TenantStatus.TRIAL
        assert updated.subscription.days_remaining is not None

    def test_D02_convert_to_paid_clears_expiry(self, manager, sub_manager):
        t = manager.create_tenant("T", "pay-sm.com", trial_days=7)
        sub_manager.convert_to_paid(t.tenant_id, SubscriptionTier.STARTER)
        t = manager.get_tenant(t.tenant_id)
        assert t.status == TenantStatus.ACTIVE
        assert t.subscription.expires_at is None

    def test_D03_upgrade_plan_changes_tier(self, manager, sub_manager):
        t = manager.create_tenant("T", "up-sm.com", tier=SubscriptionTier.STARTER)
        result = sub_manager.upgrade_plan(t.tenant_id, SubscriptionTier.PROFESSIONAL)
        assert result["old_tier"] == "starter"
        assert result["new_tier"] == "professional"

    def test_D04_downgrade_plan_includes_proration_flag(self, manager, sub_manager):
        t = manager.create_tenant("T", "down-sm.com", tier=SubscriptionTier.PROFESSIONAL)
        result = sub_manager.downgrade_plan(t.tenant_id, SubscriptionTier.STARTER)
        assert result["old_tier"] == "professional"
        assert result["prorated_credit"] is True

    def test_D05_suspend_tenant_sets_metadata(self, manager, sub_manager):
        t = manager.create_tenant("T", "sus-sm.com")
        suspended = sub_manager.suspend_tenant(t.tenant_id, reason="payment failed")
        assert suspended.status == TenantStatus.SUSPENDED
        assert "payment failed" in suspended.metadata.get("suspension_reason", "")

    def test_D06_reactivate_clears_suspension_metadata(self, manager, sub_manager):
        t = manager.create_tenant("T", "reac-sm.com")
        sub_manager.suspend_tenant(t.tenant_id)
        reactivated = sub_manager.reactivate_tenant(t.tenant_id)
        assert reactivated.status == TenantStatus.ACTIVE
        assert "suspension_reason" not in reactivated.metadata

    def test_D07_cancel_sets_cancelled_status(self, manager, sub_manager):
        t = manager.create_tenant("T", "cancel-sm.com")
        cancelled = sub_manager.cancel_subscription(t.tenant_id)
        assert cancelled.status == TenantStatus.CANCELLED

    def test_D08_expire_trial_sets_expired_status(self, manager, sub_manager):
        t = manager.create_tenant("T", "exp-sm.com", trial_days=14)
        expired = sub_manager.expire_trial(t.tenant_id)
        assert expired.status == TenantStatus.EXPIRED


# ===========================================================================
# E. TenantDashboard
# ===========================================================================

class TestTenantDashboard:

    def test_E01_get_overview_has_required_keys(self, manager, dashboard):
        t = manager.create_tenant("D", "dash.com", tier=SubscriptionTier.STARTER)
        overview = dashboard.get_overview(t.tenant_id)
        for key in ("tenant_id", "name", "status", "tier", "users", "limits", "outstanding_balance"):
            assert key in overview

    def test_E02_user_utilization_reflects_users(self, manager, dashboard):
        t = manager.create_tenant("D2", "dash2.com", tier=SubscriptionTier.STARTER)
        manager.add_user(t.tenant_id, "a@dash2.com")
        overview = dashboard.get_overview(t.tenant_id)
        assert overview["users"]["active"] == 1
        assert overview["users"]["utilization_pct"] > 0

    def test_E03_get_usage_analytics_structure(self, manager, billing, dashboard):
        t = manager.create_tenant("D3", "dash3.com")
        billing.record_usage(t.tenant_id, UsageMetric.VALUATION, 3.0)
        analytics = dashboard.get_usage_analytics(t.tenant_id, days=30)
        for key in ("tenant_id", "period_days", "totals", "daily_breakdown"):
            assert key in analytics

    def test_E04_get_billing_overview_structure(self, manager, billing, dashboard):
        t = manager.create_tenant("D4", "dash4.com")
        billing.generate_invoice(t.tenant_id, "free")
        billing_view = dashboard.get_billing_overview(t.tenant_id)
        for key in ("outstanding_balance", "invoice_count", "unpaid_invoices"):
            assert key in billing_view

    def test_E05_get_platform_stats_has_tenant_counts(self, manager, dashboard):
        manager.create_tenant("P1", "p1.com")
        manager.create_tenant("P2", "p2.com")
        stats = dashboard.get_platform_stats()
        assert stats["total_tenants"] >= 2

    def test_E06_upgrade_recommendation_below_threshold_returns_none(self, manager, dashboard):
        t = manager.create_tenant("D5", "dash5.com", tier=SubscriptionTier.ENTERPRISE)
        rec = dashboard.get_upgrade_recommendation(t.tenant_id)
        assert rec is None  # already on enterprise, no higher tier

    def test_E07_get_user_summary_counts_roles(self, manager, dashboard):
        t = manager.create_tenant("D6", "dash6.com", tier=SubscriptionTier.PROFESSIONAL)
        manager.add_user(t.tenant_id, "a@d6.com", UserRole.ADMIN)
        manager.add_user(t.tenant_id, "b@d6.com", UserRole.ANALYST)
        summary = dashboard.get_user_summary(t.tenant_id)
        assert summary["active_users"] == 2
        assert summary["role_distribution"]["admin"] == 1
        assert summary["role_distribution"]["analyst"] == 1
