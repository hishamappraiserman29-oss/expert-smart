"""
security_layer.py — API Security Layer (Phase 38)

API key generation/validation, rate limiting, HMAC signing.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class RateLimitTier(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class AuthenticationMethod(str, Enum):
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    OAUTH2 = "oauth2"
    HMAC_SIGNATURE = "hmac"


@dataclass
class APIKey:
    key_id: str
    key_secret: str
    partner_id: str
    partner_name: str
    tier: RateLimitTier = RateLimitTier.STARTER
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    is_active: bool = True
    is_rotated: bool = False
    total_requests: int = 0
    failed_requests: int = 0
    allowed_endpoints: List[str] = field(default_factory=list)
    allowed_ips: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key_id": self.key_id,
            "partner_id": self.partner_id,
            "partner_name": self.partner_name,
            "tier": self.tier.value,
            "is_active": self.is_active,
            "total_requests": self.total_requests,
            "last_used": self.last_used_at.isoformat() if self.last_used_at else None,
        }


@dataclass
class RateLimitConfig:
    tier: RateLimitTier
    requests_per_hour: int
    requests_per_minute: int
    requests_per_second: int
    burst_allowance: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier.value,
            "requests_per_hour": self.requests_per_hour,
            "requests_per_minute": self.requests_per_minute,
            "burst_allowance": self.burst_allowance,
        }


class APISecurityLayer:
    """API key management, rate limiting, and HMAC request signing."""

    def __init__(self) -> None:
        self.rate_limits: Dict[RateLimitTier, RateLimitConfig] = {
            RateLimitTier.FREE: RateLimitConfig(
                tier=RateLimitTier.FREE,
                requests_per_hour=100,
                requests_per_minute=5,
                requests_per_second=1,
                burst_allowance=10,
            ),
            RateLimitTier.STARTER: RateLimitConfig(
                tier=RateLimitTier.STARTER,
                requests_per_hour=1_000,
                requests_per_minute=50,
                requests_per_second=10,
                burst_allowance=50,
            ),
            RateLimitTier.PROFESSIONAL: RateLimitConfig(
                tier=RateLimitTier.PROFESSIONAL,
                requests_per_hour=10_000,
                requests_per_minute=500,
                requests_per_second=100,
                burst_allowance=500,
            ),
            RateLimitTier.ENTERPRISE: RateLimitConfig(
                tier=RateLimitTier.ENTERPRISE,
                requests_per_hour=999_999,
                requests_per_minute=999_999,
                requests_per_second=999_999,
                burst_allowance=999_999,
            ),
        }
        self.api_keys: Dict[str, APIKey] = {}
        self.request_history: Dict[str, List[datetime]] = {}
        self._lock = threading.Lock()
        logger.info("API Security Layer initialized")

    def generate_api_key(
        self,
        partner_id: str,
        partner_name: str,
        tier: RateLimitTier = RateLimitTier.STARTER,
    ) -> APIKey:
        key_id = f"sk_{secrets.token_urlsafe(16)}"
        key_secret = secrets.token_urlsafe(32)
        api_key = APIKey(
            key_id=key_id,
            key_secret=key_secret,
            partner_id=partner_id,
            partner_name=partner_name,
            tier=tier,
            expires_at=datetime.utcnow() + timedelta(days=365),
        )
        with self._lock:
            self.api_keys[key_id] = api_key
        logger.info("API key generated: %s for %s", key_id, partner_name)
        return api_key

    def validate_api_key(
        self,
        key_id: str,
        key_secret: str,
        client_ip: Optional[str] = None,
    ) -> Tuple[bool, Optional[APIKey]]:
        with self._lock:
            api_key = self.api_keys.get(key_id)

        if api_key is None:
            logger.warning("Unknown API key: %s", key_id)
            return False, None

        if not api_key.is_active:
            logger.warning("Inactive API key: %s", key_id)
            return False, None

        if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
            logger.warning("Expired API key: %s", key_id)
            return False, None

        if not hmac.compare_digest(api_key.key_secret, key_secret):
            logger.warning("Invalid secret for API key: %s", key_id)
            api_key.failed_requests += 1
            return False, None

        if api_key.allowed_ips and client_ip and client_ip not in api_key.allowed_ips:
            logger.warning("IP %s not whitelisted for key %s", client_ip, key_id)
            return False, None

        return True, api_key

    def check_rate_limit(
        self,
        key_id: str,
        api_key: APIKey,
    ) -> Tuple[bool, Dict[str, Any]]:
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=1)

        with self._lock:
            if key_id not in self.request_history:
                self.request_history[key_id] = []
            self.request_history[key_id] = [
                ts for ts in self.request_history[key_id] if ts > cutoff
            ]
            hour_count = len(self.request_history[key_id])
            config = self.rate_limits[api_key.tier]

            if hour_count >= config.requests_per_hour:
                return False, {
                    "limit": config.requests_per_hour,
                    "current": hour_count,
                    "remaining": 0,
                    "reset": (now + timedelta(hours=1)).isoformat(),
                }

            self.request_history[key_id].append(now)
            api_key.total_requests += 1
            api_key.last_used_at = now

        return True, {
            "limit": config.requests_per_hour,
            "current": hour_count + 1,
            "remaining": config.requests_per_hour - (hour_count + 1),
            "reset": (now + timedelta(hours=1)).isoformat(),
        }

    def rotate_api_key(self, key_id: str) -> Optional[APIKey]:
        with self._lock:
            old_key = self.api_keys.get(key_id)
        if old_key is None:
            return None
        new_key = self.generate_api_key(
            partner_id=old_key.partner_id,
            partner_name=old_key.partner_name,
            tier=old_key.tier,
        )
        old_key.is_rotated = True
        old_key.is_active = False
        logger.info("API key rotated: %s -> %s", key_id, new_key.key_id)
        return new_key

    def sign_request(self, api_secret: str, request_data: str) -> str:
        return hmac.new(
            api_secret.encode(),
            request_data.encode(),
            hashlib.sha256,
        ).hexdigest()

    def verify_signature(self, api_secret: str, request_data: str, signature: str) -> bool:
        expected = self.sign_request(api_secret, request_data)
        return hmac.compare_digest(expected, signature)

    def get_security_status(self) -> Dict[str, Any]:
        with self._lock:
            active_keys = sum(1 for k in self.api_keys.values() if k.is_active)
            total_requests = sum(k.total_requests for k in self.api_keys.values())
        return {
            "active_api_keys": active_keys,
            "total_api_keys": len(self.api_keys),
            "total_requests": total_requests,
            "rate_tiers": {
                tier.value: cfg.requests_per_hour
                for tier, cfg in self.rate_limits.items()
            },
        }

    def count(self) -> int:
        with self._lock:
            return len(self.api_keys)


api_security = APISecurityLayer()
