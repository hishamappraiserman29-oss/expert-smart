"""
enterprise.py — Enterprise Features Framework (Phase 15.0)

Multi-tenant access control, user management, and subscription validation.

Classes:
    TenantRole                  — RBAC enum (admin / operator / analyst / viewer)
    TenantUser                  — User within a tenant organization
    TenantOrganization          — Tenant container (users, settings, limits)
    TenantManager               — Create/manage organizations and users
    EnterpriseLicenseValidator  — Subscription feature gating and quota checks
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


# ── Role enum ────────────────────────────────────────────────────────────────

class TenantRole(str, Enum):
    """Tenant role-based access control."""

    ADMIN    = "admin"      # Full access (users, settings, data)
    OPERATOR = "operator"   # Valuations + batch operations
    ANALYST  = "analyst"    # Read-only valuations + reports
    VIEWER   = "viewer"     # Read-only reports only

    def can_valuate(self) -> bool:
        """Can create valuations."""
        return self in (TenantRole.ADMIN, TenantRole.OPERATOR)

    def can_manage_users(self) -> bool:
        """Can manage tenant users."""
        return self == TenantRole.ADMIN

    def can_view_reports(self) -> bool:
        """Can view reports."""
        return self in (
            TenantRole.ADMIN,
            TenantRole.OPERATOR,
            TenantRole.ANALYST,
            TenantRole.VIEWER,
        )


# ── User ─────────────────────────────────────────────────────────────────────

@dataclass
class TenantUser:
    """User within a tenant organization."""

    user_id:   str
    email:     str
    full_name: str
    role:      str           # TenantRole value

    created_at: str                = ""
    last_login: Optional[str]      = None
    is_active:  bool               = True

    def to_dict(self) -> Dict:
        return {
            "user_id":    self.user_id,
            "email":      self.email,
            "full_name":  self.full_name,
            "role":       self.role,
            "created_at": self.created_at,
            "last_login": self.last_login,
            "is_active":  self.is_active,
        }


# ── Organization ──────────────────────────────────────────────────────────────

@dataclass
class TenantOrganization:
    """Organization (tenant) in the multi-tenant system."""

    tenant_id:         str
    organization_name: str
    country:           str
    subscription_tier: str           # free | professional | enterprise

    users: List[TenantUser] = field(default_factory=list)

    created_at: str           = ""
    expires_at: Optional[str] = None  # Subscription expiry (ISO)

    # Feature toggles
    enable_webhooks:         bool = True
    enable_batch_api:        bool = True
    max_batch_size:          int  = 500
    max_concurrent_batches:  int  = 5

    # Regional
    default_currency:   str       = "EGP"
    supported_standards: List[str] = field(
        default_factory=lambda: ["EGVS", "IVSC", "CBE"]
    )

    def to_dict(self) -> Dict:
        return {
            "tenant_id":         self.tenant_id,
            "organization_name": self.organization_name,
            "country":           self.country,
            "subscription_tier": self.subscription_tier,
            "user_count":        len(self.users),
            "created_at":        self.created_at,
            "expires_at":        self.expires_at,
            "enable_webhooks":   self.enable_webhooks,
            "enable_batch_api":  self.enable_batch_api,
            "max_batch_size":    self.max_batch_size,
            "default_currency":  self.default_currency,
        }


# ── TenantManager ─────────────────────────────────────────────────────────────

class TenantManager:
    """Create and manage multi-tenant organizations."""

    def __init__(self) -> None:
        self.tenants: Dict[str, TenantOrganization] = {}

    # ── Write ─────────────────────────────────────────────────────────────────

    def create_tenant(
        self,
        organization_name: str,
        country: str,
        subscription_tier: str = "professional",
    ) -> TenantOrganization:
        """Create a new tenant organization."""
        import uuid
        tenant_id = str(uuid.uuid4())
        tenant = TenantOrganization(
            tenant_id=tenant_id,
            organization_name=organization_name,
            country=country,
            subscription_tier=subscription_tier,
            created_at=datetime.now().isoformat(),
        )
        self.tenants[tenant_id] = tenant
        return tenant

    def add_user_to_tenant(
        self,
        tenant_id: str,
        email: str,
        full_name: str,
        role: str,
    ) -> Optional[TenantUser]:
        """Add a user to an existing tenant.  Returns None if tenant not found."""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return None

        import uuid
        user = TenantUser(
            user_id=str(uuid.uuid4()),
            email=email,
            full_name=full_name,
            role=role,
            created_at=datetime.now().isoformat(),
        )
        tenant.users.append(user)
        return user

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_tenant(self, tenant_id: str) -> Optional[TenantOrganization]:
        """Return the tenant for the given ID, or None."""
        return self.tenants.get(tenant_id)

    def get_user_by_email(
        self, tenant_id: str, email: str
    ) -> Optional[TenantUser]:
        """Return the first user matching the email within the tenant."""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return None
        for user in tenant.users:
            if user.email == email:
                return user
        return None

    def can_user_valuate(self, tenant_id: str, user_id: str) -> bool:
        """Return True if the user is active and has a role that can valuate."""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False
        for user in tenant.users:
            if user.user_id == user_id and user.is_active:
                return TenantRole(user.role).can_valuate()
        return False

    def get_tenant_summary(self, tenant_id: str) -> Dict:
        """Return a summary dict for the tenant (safe to serialise to JSON)."""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return {}
        return {
            "tenant":     tenant.to_dict(),
            "users":      [u.to_dict() for u in tenant.users],
            "user_count": len(tenant.users),
        }


# ── EnterpriseLicenseValidator ────────────────────────────────────────────────

class EnterpriseLicenseValidator:
    """Validate enterprise licenses, subscription tiers, and feature quotas."""

    TIER_FEATURES: Dict[str, Dict] = {
        "free": {
            "max_valuations_per_month":    10,
            "max_properties_in_portfolio": 5,
            "max_batch_size":              10,
            "webhooks_enabled":            False,
            "api_access":                  False,
            "support_level":               "community",
        },
        "professional": {
            "max_valuations_per_month":    500,
            "max_properties_in_portfolio": 100,
            "max_batch_size":              100,
            "webhooks_enabled":            True,
            "api_access":                  True,
            "support_level":               "email",
        },
        "enterprise": {
            "max_valuations_per_month":    50_000,
            "max_properties_in_portfolio": 10_000,
            "max_batch_size":              1_000,
            "webhooks_enabled":            True,
            "api_access":                  True,
            "support_level":               "phone_email",
        },
    }

    @staticmethod
    def validate_subscription(tenant: TenantOrganization) -> Dict:
        """Check whether the tenant's subscription is valid and return feature set."""
        tier     = tenant.subscription_tier
        features = EnterpriseLicenseValidator.TIER_FEATURES.get(tier, {})

        is_valid = True
        if tenant.expires_at:
            expires = datetime.fromisoformat(tenant.expires_at)
            if expires < datetime.now():
                is_valid = False

        return {
            "tenant_id":  tenant.tenant_id,
            "tier":       tier,
            "is_valid":   is_valid,
            "features":   features,
            "expires_at": tenant.expires_at,
        }

    @staticmethod
    def can_create_valuation(
        tenant: TenantOrganization,
        valuations_this_month: int = 0,
    ) -> bool:
        """Return True if the tenant has quota remaining for another valuation."""
        features     = EnterpriseLicenseValidator.TIER_FEATURES.get(
            tenant.subscription_tier, {}
        )
        max_per_month = features.get("max_valuations_per_month", 0)
        return valuations_this_month < max_per_month

    @staticmethod
    def get_feature_limit(tenant: TenantOrganization, feature: str) -> int:
        """Return the numeric limit for a named feature (0 if not found)."""
        features = EnterpriseLicenseValidator.TIER_FEATURES.get(
            tenant.subscription_tier, {}
        )
        return features.get(feature, 0)
