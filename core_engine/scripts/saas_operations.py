"""
saas_operations.py — Operational runner for Phase 26 SaaS components.
Verifies imports, creates demo tenants, and exercises the full lifecycle.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CHECKS = []


def _check(name: str, fn):
    try:
        result = fn()
        CHECKS.append((name, True, result or "OK"))
    except Exception as exc:
        CHECKS.append((name, False, str(exc)))


def main() -> None:
    print("[saas-ops] Running Phase 26 SaaS operations checks ...")

    # -----------------------------------------------------------------------
    # 1. Import checks
    # -----------------------------------------------------------------------
    _check("saas package imports", lambda: (
        __import__("saas", fromlist=["TenantManager", "BillingEngine"])
        and "imports OK"
    ))

    # -----------------------------------------------------------------------
    # 2. Tenant lifecycle
    # -----------------------------------------------------------------------
    from saas.tenant_manager import TenantManager, SubscriptionTier, UserRole, TenantStatus

    manager = TenantManager()

    _check("create free tenant", lambda: (
        manager.create_tenant("FreeOrg", "free.example.com")
        and "tenant created"
    ))

    _check("create trial tenant", lambda: (
        manager.create_tenant("TrialOrg", "trial.example.com", trial_days=14)
        and "trial created"
    ))

    _check("create professional tenant", lambda: (
        manager.create_tenant("ProOrg", "pro.example.com", tier=SubscriptionTier.PROFESSIONAL)
        and "professional tenant created"
    ))

    pro_tenant = manager.get_tenant_by_domain("pro.example.com")
    _check("add users to tenant", lambda: (
        manager.add_user(pro_tenant.tenant_id, "alice@pro.example.com", UserRole.ADMIN)
        and manager.add_user(pro_tenant.tenant_id, "bob@pro.example.com", UserRole.ANALYST)
        and "users added"
    ))

    # -----------------------------------------------------------------------
    # 3. Isolation validator
    # -----------------------------------------------------------------------
    from saas.tenant_isolation import TenantIsolationValidator

    validator = TenantIsolationValidator(manager)
    _check("isolation validator active tenant", lambda: (
        validator.validate_tenant_active(pro_tenant.tenant_id)
        and "active tenant validates"
    ))

    # -----------------------------------------------------------------------
    # 4. Billing
    # -----------------------------------------------------------------------
    from saas.billing_engine import BillingEngine, UsageMetric

    billing = BillingEngine()
    billing.record_usage(pro_tenant.tenant_id, UsageMetric.VALUATION, 5.0)
    billing.record_usage(pro_tenant.tenant_id, UsageMetric.API_CALL, 100.0)
    billing.record_usage(pro_tenant.tenant_id, UsageMetric.REPORT, 2.0)

    _check("generate invoice", lambda: (
        billing.generate_invoice(pro_tenant.tenant_id, "professional").total_amount > 0
        and "invoice generated"
    ))

    # -----------------------------------------------------------------------
    # 5. Subscription manager
    # -----------------------------------------------------------------------
    from saas.subscription_manager import SubscriptionManager

    sm = SubscriptionManager(tenant_manager=manager, billing_engine=billing)
    trial_t = manager.get_tenant_by_domain("trial.example.com")
    _check("convert trial to paid", lambda: (
        sm.convert_to_paid(trial_t.tenant_id, SubscriptionTier.STARTER)
        and "trial converted"
    ))

    _check("billing summary", lambda: (
        "outstanding_balance" in sm.get_billing_summary(pro_tenant.tenant_id)
        and "billing summary OK"
    ))

    # -----------------------------------------------------------------------
    # 6. Dashboard
    # -----------------------------------------------------------------------
    from saas.dashboard import TenantDashboard

    dashboard = TenantDashboard(
        tenant_manager=manager,
        billing_engine=billing,
        subscription_manager=sm,
    )

    _check("dashboard overview", lambda: (
        "tier" in dashboard.get_overview(pro_tenant.tenant_id)
        and "overview OK"
    ))

    _check("platform stats", lambda: (
        dashboard.get_platform_stats()["total_tenants"] >= 3
        and "platform stats OK"
    ))

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    passed = sum(1 for _, ok, _ in CHECKS if ok)
    failed = len(CHECKS) - passed

    print()
    for name, ok, msg in CHECKS:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}: {msg}")

    print()
    print(f"[saas-ops] Results: {passed} pass, {failed} fail out of {len(CHECKS)} checks")

    if failed:
        sys.exit(1)
    print("[saas-ops] All checks passed.")


if __name__ == "__main__":
    main()
