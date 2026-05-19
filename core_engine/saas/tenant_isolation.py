"""
tenant_isolation.py — Data isolation and request scoping for multi-tenant SaaS.
"""

from __future__ import annotations

import functools
import threading
from typing import Any, Callable, Dict, Optional

from .tenant_manager import TenantManager, TenantStatus, get_tenant_manager

# Thread-local storage for active tenant context
_local = threading.local()


def get_current_tenant_id() -> Optional[str]:
    return getattr(_local, "tenant_id", None)


def set_current_tenant_id(tenant_id: Optional[str]) -> None:
    _local.tenant_id = tenant_id


class TenantContext:
    """Context manager that sets/restores tenant scope."""

    def __init__(self, tenant_id: str) -> None:
        self.tenant_id = tenant_id
        self._previous: Optional[str] = None

    def __enter__(self) -> "TenantContext":
        self._previous = get_current_tenant_id()
        set_current_tenant_id(self.tenant_id)
        return self

    def __exit__(self, *_) -> None:
        set_current_tenant_id(self._previous)


class TenantIsolationValidator:
    """Validates tenant access and enforces data boundaries."""

    def __init__(self, manager: Optional[TenantManager] = None) -> None:
        self._manager = manager or get_tenant_manager()

    def validate_tenant_active(self, tenant_id: str) -> bool:
        tenant = self._manager.get_tenant(tenant_id)
        if tenant is None:
            return False
        return tenant.status in (TenantStatus.ACTIVE, TenantStatus.TRIAL)

    def validate_user_belongs_to_tenant(self, tenant_id: str, user_id: str) -> bool:
        user = self._manager.get_user(tenant_id, user_id)
        return user is not None and user.is_active

    def validate_resource_access(
        self,
        tenant_id: str,
        resource_tenant_id: str,
    ) -> bool:
        """Ensure a tenant cannot access another tenant's resource."""
        return tenant_id == resource_tenant_id

    def scope_query(self, tenant_id: str, query_params: Dict) -> Dict:
        """Inject tenant_id filter into arbitrary query params."""
        scoped = dict(query_params)
        scoped["tenant_id"] = tenant_id
        return scoped

    def validate_api_quota(self, tenant_id: str, calls_today: int) -> bool:
        tenant = self._manager.get_tenant(tenant_id)
        if tenant is None:
            return False
        limit = tenant.get_limits()["api_calls_per_day"]
        return calls_today < limit

    def validate_user_limit(self, tenant_id: str) -> bool:
        tenant = self._manager.get_tenant(tenant_id)
        if tenant is None:
            return False
        active = sum(1 for u in tenant.users if u.is_active)
        return active < tenant.get_limits()["max_users"]

    def validate_valuation_quota(
        self, tenant_id: str, valuations_this_month: int
    ) -> bool:
        tenant = self._manager.get_tenant(tenant_id)
        if tenant is None:
            return False
        limit = tenant.get_limits()["monthly_valuations"]
        return valuations_this_month < limit


def require_tenant_context(f: Callable) -> Callable:
    """
    Decorator that injects `tenant_id` from Flask request headers
    or falls back to thread-local context, then validates the tenant is active.
    """
    @functools.wraps(f)
    def wrapper(*args, **kwargs) -> Any:
        # Try to pull tenant_id from Flask request if available
        tenant_id: Optional[str] = None
        try:
            from flask import request, jsonify
            tenant_id = request.headers.get("X-Tenant-ID") or kwargs.get("tenant_id")
        except ImportError:
            pass

        if tenant_id is None:
            tenant_id = get_current_tenant_id()

        if tenant_id is None:
            try:
                from flask import jsonify
                return jsonify({"error": "X-Tenant-ID header required"}), 400
            except ImportError:
                raise ValueError("No tenant context available")

        validator = TenantIsolationValidator()
        if not validator.validate_tenant_active(tenant_id):
            try:
                from flask import jsonify
                return jsonify({"error": f"Tenant '{tenant_id}' is not active"}), 403
            except ImportError:
                raise PermissionError(f"Tenant '{tenant_id}' is not active")

        kwargs["tenant_id"] = tenant_id
        with TenantContext(tenant_id):
            return f(*args, **kwargs)

    return wrapper


# ---------------------------------------------------------------------------
# Optional: TenantAwareQuery (wraps DB model queries with tenant filter)
# ---------------------------------------------------------------------------
try:
    from database.models import Valuation as _Valuation  # type: ignore

    class TenantAwareQuery:
        """Wraps a SQLAlchemy-style query to automatically filter by tenant."""

        def __init__(self, model, session) -> None:
            self._model = model
            self._session = session

        def filter_by_tenant(self, tenant_id: str):
            return self._session.query(self._model).filter(
                self._model.tenant_id == tenant_id
            )

except Exception:
    # DB layer not available in this environment — provide a stub
    class TenantAwareQuery:  # type: ignore
        """Stub used when database layer is unavailable."""

        def __init__(self, model=None, session=None) -> None:
            self._model = model
            self._session = session

        def filter_by_tenant(self, tenant_id: str):
            raise NotImplementedError("Database layer not configured")
