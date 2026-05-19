"""
tenant_manager.py — Core tenant lifecycle management for Expert Smart SaaS.
"""

from __future__ import annotations

import uuid
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional


class TenantStatus(Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    TRIAL = "trial"
    EXPIRED = "expired"


class UserRole(Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"
    API_USER = "api_user"


class SubscriptionTier(Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


# Tier limits: (max_users, monthly_valuations, storage_gb, api_calls_per_day)
TIER_LIMITS: Dict[SubscriptionTier, Dict[str, int]] = {
    SubscriptionTier.FREE:         {"max_users": 2,   "monthly_valuations": 10,   "storage_gb": 1,   "api_calls_per_day": 100},
    SubscriptionTier.STARTER:      {"max_users": 5,   "monthly_valuations": 100,  "storage_gb": 10,  "api_calls_per_day": 1000},
    SubscriptionTier.PROFESSIONAL: {"max_users": 25,  "monthly_valuations": 1000, "storage_gb": 50,  "api_calls_per_day": 10000},
    SubscriptionTier.ENTERPRISE:   {"max_users": 999, "monthly_valuations": 99999,"storage_gb": 500, "api_calls_per_day": 999999},
}


@dataclass
class TenantUser:
    user_id: str
    tenant_id: str
    email: str
    role: UserRole
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "email": self.email,
            "role": self.role.value,
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active,
        }


@dataclass
class TenantSubscription:
    tier: SubscriptionTier
    started_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    auto_renew: bool = True

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def days_remaining(self) -> Optional[int]:
        if self.expires_at is None:
            return None
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)

    def to_dict(self) -> dict:
        return {
            "tier": self.tier.value,
            "started_at": self.started_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "auto_renew": self.auto_renew,
            "is_expired": self.is_expired,
            "days_remaining": self.days_remaining,
        }


@dataclass
class Tenant:
    tenant_id: str
    name: str
    domain: str
    status: TenantStatus
    subscription: TenantSubscription
    users: List[TenantUser] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict = field(default_factory=dict)

    def get_limits(self) -> Dict[str, int]:
        return TIER_LIMITS[self.subscription.tier]

    def to_dict(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "name": self.name,
            "domain": self.domain,
            "status": self.status.value,
            "subscription": self.subscription.to_dict(),
            "user_count": len(self.users),
            "created_at": self.created_at.isoformat(),
            "limits": self.get_limits(),
            "metadata": self.metadata,
        }


class TenantManager:
    """Thread-safe in-memory tenant registry."""

    def __init__(self) -> None:
        self._tenants: Dict[str, Tenant] = {}
        self._domain_index: Dict[str, str] = {}  # domain -> tenant_id
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Tenant CRUD
    # ------------------------------------------------------------------

    def create_tenant(
        self,
        name: str,
        domain: str,
        tier: SubscriptionTier = SubscriptionTier.FREE,
        trial_days: int = 0,
    ) -> Tenant:
        with self._lock:
            if domain in self._domain_index:
                raise ValueError(f"Domain '{domain}' is already registered")

            tenant_id = str(uuid.uuid4())
            now = datetime.utcnow()

            if trial_days > 0:
                status = TenantStatus.TRIAL
                expires_at = now + timedelta(days=trial_days)
            else:
                status = TenantStatus.ACTIVE
                expires_at = None

            subscription = TenantSubscription(
                tier=tier,
                started_at=now,
                expires_at=expires_at,
            )
            tenant = Tenant(
                tenant_id=tenant_id,
                name=name,
                domain=domain,
                status=status,
                subscription=subscription,
            )
            self._tenants[tenant_id] = tenant
            self._domain_index[domain] = tenant_id
            return tenant

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        return self._tenants.get(tenant_id)

    def get_tenant_by_domain(self, domain: str) -> Optional[Tenant]:
        tenant_id = self._domain_index.get(domain)
        return self._tenants.get(tenant_id) if tenant_id else None

    def update_tenant_status(self, tenant_id: str, status: TenantStatus) -> Tenant:
        with self._lock:
            tenant = self._get_or_raise(tenant_id)
            tenant.status = status
            return tenant

    def delete_tenant(self, tenant_id: str) -> bool:
        with self._lock:
            tenant = self._tenants.pop(tenant_id, None)
            if tenant is None:
                return False
            self._domain_index.pop(tenant.domain, None)
            return True

    def list_tenants(self, status: Optional[TenantStatus] = None) -> List[Tenant]:
        tenants = list(self._tenants.values())
        if status is not None:
            tenants = [t for t in tenants if t.status == status]
        return tenants

    # ------------------------------------------------------------------
    # User management
    # ------------------------------------------------------------------

    def add_user(
        self,
        tenant_id: str,
        email: str,
        role: UserRole = UserRole.ANALYST,
    ) -> TenantUser:
        with self._lock:
            tenant = self._get_or_raise(tenant_id)
            limits = tenant.get_limits()
            active_users = [u for u in tenant.users if u.is_active]
            if len(active_users) >= limits["max_users"]:
                raise ValueError(
                    f"Tenant '{tenant_id}' has reached the user limit "
                    f"({limits['max_users']}) for tier {tenant.subscription.tier.value}"
                )
            user = TenantUser(
                user_id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                email=email,
                role=role,
            )
            tenant.users.append(user)
            return user

    def remove_user(self, tenant_id: str, user_id: str) -> bool:
        with self._lock:
            tenant = self._get_or_raise(tenant_id)
            for user in tenant.users:
                if user.user_id == user_id:
                    user.is_active = False
                    return True
            return False

    def get_user(self, tenant_id: str, user_id: str) -> Optional[TenantUser]:
        tenant = self._tenants.get(tenant_id)
        if tenant is None:
            return None
        for user in tenant.users:
            if user.user_id == user_id:
                return user
        return None

    def list_users(self, tenant_id: str, active_only: bool = True) -> List[TenantUser]:
        tenant = self._get_or_raise(tenant_id)
        users = tenant.users
        if active_only:
            users = [u for u in users if u.is_active]
        return users

    # ------------------------------------------------------------------
    # Subscription management
    # ------------------------------------------------------------------

    def upgrade_subscription(
        self,
        tenant_id: str,
        new_tier: SubscriptionTier,
    ) -> TenantSubscription:
        with self._lock:
            tenant = self._get_or_raise(tenant_id)
            tenant.subscription.tier = new_tier
            tenant.subscription.started_at = datetime.utcnow()
            if tenant.status == TenantStatus.TRIAL:
                tenant.status = TenantStatus.ACTIVE
            return tenant.subscription

    def get_stats(self) -> Dict:
        with self._lock:
            tenants = list(self._tenants.values())
            return {
                "total_tenants": len(tenants),
                "active_tenants": sum(1 for t in tenants if t.status == TenantStatus.ACTIVE),
                "trial_tenants": sum(1 for t in tenants if t.status == TenantStatus.TRIAL),
                "total_users": sum(len(t.users) for t in tenants),
                "tier_distribution": {
                    tier.value: sum(1 for t in tenants if t.subscription.tier == tier)
                    for tier in SubscriptionTier
                },
            }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_or_raise(self, tenant_id: str) -> Tenant:
        tenant = self._tenants.get(tenant_id)
        if tenant is None:
            raise KeyError(f"Tenant '{tenant_id}' not found")
        return tenant


_manager_instance: Optional[TenantManager] = None
_manager_lock = threading.Lock()


def get_tenant_manager() -> TenantManager:
    global _manager_instance
    with _manager_lock:
        if _manager_instance is None:
            _manager_instance = TenantManager()
        return _manager_instance
