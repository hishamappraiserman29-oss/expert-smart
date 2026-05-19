"""
dashboard.py — Self-service tenant dashboard for SaaS portal.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .tenant_manager import TenantManager, TenantStatus, SubscriptionTier, get_tenant_manager
from .billing_engine import BillingEngine, UsageMetric
from .subscription_manager import SubscriptionManager


class TenantDashboard:
    """Aggregates metrics and summaries for the self-service portal."""

    def __init__(
        self,
        tenant_manager: Optional[TenantManager] = None,
        billing_engine: Optional[BillingEngine] = None,
        subscription_manager: Optional[SubscriptionManager] = None,
    ) -> None:
        self._tm = tenant_manager or get_tenant_manager()
        self._billing = billing_engine or BillingEngine()
        self._sm = subscription_manager or SubscriptionManager(
            tenant_manager=self._tm,
            billing_engine=self._billing,
        )

    # ------------------------------------------------------------------
    # Overview panel
    # ------------------------------------------------------------------

    def get_overview(self, tenant_id: str) -> Dict:
        tenant = self._tm._get_or_raise(tenant_id)
        limits = tenant.get_limits()
        active_users = [u for u in tenant.users if u.is_active]

        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        usage_this_month = self._billing.get_usage_summary(tenant_id, since=month_start)

        return {
            "tenant_id": tenant_id,
            "name": tenant.name,
            "status": tenant.status.value,
            "tier": tenant.subscription.tier.value,
            "subscription": tenant.subscription.to_dict(),
            "users": {
                "active": len(active_users),
                "limit": limits["max_users"],
                "utilization_pct": round(len(active_users) / max(limits["max_users"], 1) * 100, 1),
            },
            "usage_this_month": usage_this_month,
            "limits": limits,
            "outstanding_balance": self._billing.get_outstanding_balance(tenant_id),
        }

    # ------------------------------------------------------------------
    # Usage analytics
    # ------------------------------------------------------------------

    def get_usage_analytics(
        self, tenant_id: str, days: int = 30
    ) -> Dict:
        since = datetime.utcnow() - timedelta(days=days)
        records = self._billing.get_usage(tenant_id, since=since)

        daily: Dict[str, Dict[str, float]] = {}
        for r in records:
            day_key = r.timestamp.strftime("%Y-%m-%d")
            daily.setdefault(day_key, {})
            metric_key = r.metric.value
            daily[day_key][metric_key] = daily[day_key].get(metric_key, 0.0) + r.quantity

        totals: Dict[str, float] = {}
        for metric_data in daily.values():
            for k, v in metric_data.items():
                totals[k] = totals.get(k, 0.0) + v

        return {
            "tenant_id": tenant_id,
            "period_days": days,
            "daily_breakdown": daily,
            "totals": totals,
            "record_count": len(records),
        }

    # ------------------------------------------------------------------
    # Billing panel
    # ------------------------------------------------------------------

    def get_billing_overview(self, tenant_id: str) -> Dict:
        invoices = self._billing.get_invoices(tenant_id)
        outstanding = self._billing.get_outstanding_balance(tenant_id)
        paid_total = round(
            sum(inv.total_amount for inv in invoices if inv.paid), 2
        )
        return {
            "tenant_id": tenant_id,
            "outstanding_balance": outstanding,
            "total_paid": paid_total,
            "invoice_count": len(invoices),
            "unpaid_invoices": [inv.to_dict() for inv in invoices if not inv.paid],
        }

    # ------------------------------------------------------------------
    # Admin: platform-wide statistics
    # ------------------------------------------------------------------

    def get_platform_stats(self) -> Dict:
        stats = self._tm.get_stats()
        all_tenants = self._tm.list_tenants()
        total_outstanding = round(
            sum(self._billing.get_outstanding_balance(t.tenant_id) for t in all_tenants), 2
        )
        return {
            **stats,
            "total_outstanding_balance": total_outstanding,
            "generated_at": datetime.utcnow().isoformat(),
        }

    # ------------------------------------------------------------------
    # Upgrade recommendations
    # ------------------------------------------------------------------

    def get_upgrade_recommendation(self, tenant_id: str) -> Optional[Dict]:
        tenant = self._tm._get_or_raise(tenant_id)
        limits = tenant.get_limits()
        active_users = sum(1 for u in tenant.users if u.is_active)

        # Recommend upgrade when at 80% of any limit
        user_utilization = active_users / max(limits["max_users"], 1)

        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        usage = self._billing.get_usage_summary(tenant_id, since=month_start)
        val_count = usage.get("valuation", 0.0)
        val_utilization = val_count / max(limits["monthly_valuations"], 1)

        max_util = max(user_utilization, val_utilization)
        if max_util < 0.8:
            return None

        # Find next tier
        tier_order = [
            SubscriptionTier.FREE,
            SubscriptionTier.STARTER,
            SubscriptionTier.PROFESSIONAL,
            SubscriptionTier.ENTERPRISE,
        ]
        current_idx = tier_order.index(tenant.subscription.tier)
        if current_idx >= len(tier_order) - 1:
            return None

        next_tier = tier_order[current_idx + 1]
        return {
            "tenant_id": tenant_id,
            "current_tier": tenant.subscription.tier.value,
            "recommended_tier": next_tier.value,
            "reason": f"Utilization at {max_util:.0%} of current plan limits",
            "user_utilization": round(user_utilization * 100, 1),
            "valuation_utilization": round(val_utilization * 100, 1),
        }

    # ------------------------------------------------------------------
    # User management panel
    # ------------------------------------------------------------------

    def get_user_summary(self, tenant_id: str) -> Dict:
        users = self._tm.list_users(tenant_id, active_only=False)
        active = [u for u in users if u.is_active]
        role_distribution: Dict[str, int] = {}
        for u in active:
            role_distribution[u.role.value] = role_distribution.get(u.role.value, 0) + 1
        return {
            "tenant_id": tenant_id,
            "total_users": len(users),
            "active_users": len(active),
            "inactive_users": len(users) - len(active),
            "role_distribution": role_distribution,
        }
