"""
saas — Multi-Tenant SaaS Readiness package for Expert Smart.

Provides tenant management, data isolation, billing, subscription lifecycle,
and self-service dashboard capabilities.
"""

from .tenant_manager import (
    TenantStatus, UserRole, SubscriptionTier,
    TenantUser, TenantSubscription, Tenant,
    TenantManager, get_tenant_manager,
)
from .tenant_isolation import TenantIsolationValidator, require_tenant_context
from .billing_engine import UsageMetric, UsageRecord, Invoice, BillingEngine
from .subscription_manager import SubscriptionManager
from .dashboard import TenantDashboard

__all__ = [
    "TenantStatus", "UserRole", "SubscriptionTier",
    "TenantUser", "TenantSubscription", "Tenant",
    "TenantManager", "get_tenant_manager",
    "TenantIsolationValidator", "require_tenant_context",
    "UsageMetric", "UsageRecord", "Invoice", "BillingEngine",
    "SubscriptionManager",
    "TenantDashboard",
]
