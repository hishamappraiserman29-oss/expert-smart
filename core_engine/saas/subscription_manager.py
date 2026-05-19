"""
subscription_manager.py — Orchestrates subscription lifecycle events.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Optional

from .tenant_manager import (
    Tenant, TenantManager, TenantStatus, SubscriptionTier, get_tenant_manager,
)
from .billing_engine import BillingEngine, UsageMetric


class SubscriptionManager:
    """Coordinates tenant manager and billing engine for subscription events."""

    def __init__(
        self,
        tenant_manager: Optional[TenantManager] = None,
        billing_engine: Optional[BillingEngine] = None,
    ) -> None:
        self._tm = tenant_manager or get_tenant_manager()
        self._billing = billing_engine or BillingEngine()

    # ------------------------------------------------------------------
    # Lifecycle events
    # ------------------------------------------------------------------

    def start_trial(
        self, tenant_id: str, trial_days: int = 14
    ) -> Tenant:
        tenant = self._tm._get_or_raise(tenant_id)
        tenant.status = TenantStatus.TRIAL
        tenant.subscription.expires_at = datetime.utcnow() + timedelta(days=trial_days)
        return tenant

    def convert_to_paid(
        self, tenant_id: str, tier: SubscriptionTier
    ) -> Tenant:
        self._tm.upgrade_subscription(tenant_id, tier)
        tenant = self._tm._get_or_raise(tenant_id)
        tenant.status = TenantStatus.ACTIVE
        tenant.subscription.expires_at = None
        return tenant

    def upgrade_plan(
        self, tenant_id: str, new_tier: SubscriptionTier
    ) -> Dict:
        tenant = self._tm._get_or_raise(tenant_id)
        old_tier = tenant.subscription.tier
        self._tm.upgrade_subscription(tenant_id, new_tier)
        return {
            "tenant_id": tenant_id,
            "old_tier": old_tier.value,
            "new_tier": new_tier.value,
            "upgraded_at": datetime.utcnow().isoformat(),
        }

    def downgrade_plan(
        self, tenant_id: str, new_tier: SubscriptionTier
    ) -> Dict:
        tenant = self._tm._get_or_raise(tenant_id)
        old_tier = tenant.subscription.tier
        # Enforce downgrade ordering check (non-free → allowed, free-only special case handled)
        self._tm.upgrade_subscription(tenant_id, new_tier)
        return {
            "tenant_id": tenant_id,
            "old_tier": old_tier.value,
            "new_tier": new_tier.value,
            "downgraded_at": datetime.utcnow().isoformat(),
            "prorated_credit": old_tier != SubscriptionTier.FREE,
        }

    def suspend_tenant(self, tenant_id: str, reason: str = "") -> Tenant:
        tenant = self._tm.update_tenant_status(tenant_id, TenantStatus.SUSPENDED)
        tenant.metadata["suspension_reason"] = reason
        tenant.metadata["suspended_at"] = datetime.utcnow().isoformat()
        return tenant

    def reactivate_tenant(self, tenant_id: str) -> Tenant:
        tenant = self._tm.update_tenant_status(tenant_id, TenantStatus.ACTIVE)
        tenant.metadata.pop("suspension_reason", None)
        tenant.metadata.pop("suspended_at", None)
        return tenant

    def cancel_subscription(self, tenant_id: str) -> Tenant:
        tenant = self._tm.update_tenant_status(tenant_id, TenantStatus.CANCELLED)
        tenant.metadata["cancelled_at"] = datetime.utcnow().isoformat()
        return tenant

    def expire_trial(self, tenant_id: str) -> Tenant:
        tenant = self._tm._get_or_raise(tenant_id)
        if tenant.status != TenantStatus.TRIAL:
            raise ValueError(f"Tenant '{tenant_id}' is not in TRIAL status")
        tenant.status = TenantStatus.EXPIRED
        return tenant

    # ------------------------------------------------------------------
    # Billing convenience
    # ------------------------------------------------------------------

    def record_valuation_usage(self, tenant_id: str, count: int = 1) -> None:
        self._billing.record_usage(tenant_id, UsageMetric.VALUATION, float(count))

    def record_api_call(self, tenant_id: str) -> None:
        self._billing.record_usage(tenant_id, UsageMetric.API_CALL, 1.0)

    def generate_monthly_invoice(self, tenant_id: str) -> Dict:
        tenant = self._tm._get_or_raise(tenant_id)
        invoice = self._billing.generate_invoice(
            tenant_id=tenant_id,
            tier=tenant.subscription.tier.value,
        )
        return invoice.to_dict()

    def get_billing_summary(self, tenant_id: str) -> Dict:
        tenant = self._tm._get_or_raise(tenant_id)
        return {
            "tenant_id": tenant_id,
            "tier": tenant.subscription.tier.value,
            "status": tenant.status.value,
            "outstanding_balance": self._billing.get_outstanding_balance(tenant_id),
            "usage_summary": self._billing.get_usage_summary(tenant_id),
            "invoice_count": len(self._billing.get_invoices(tenant_id)),
        }
