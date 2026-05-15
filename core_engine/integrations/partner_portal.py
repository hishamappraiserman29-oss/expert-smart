"""
partner_portal.py — Partner Integration Portal (Phase 40)

Self-service account management for integration partners.
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PartnerTier(str, Enum):
    TRIAL = "trial"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


_TIER_LIMITS: Dict[str, Dict[str, Any]] = {
    PartnerTier.TRIAL: {"max_connectors": 1, "max_webhooks": 1, "api_calls_month": 1_000},
    PartnerTier.BASIC: {"max_connectors": 5, "max_webhooks": 5, "api_calls_month": 10_000},
    PartnerTier.PROFESSIONAL: {"max_connectors": 20, "max_webhooks": 20, "api_calls_month": 100_000},
    PartnerTier.ENTERPRISE: {"max_connectors": -1, "max_webhooks": -1, "api_calls_month": -1},
}


@dataclass
class Partner:
    partner_id: str
    name: str
    email: str
    tier: PartnerTier = PartnerTier.TRIAL
    api_key: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    is_active: bool = True
    connectors: List[str] = field(default_factory=list)
    webhooks: List[str] = field(default_factory=list)
    api_calls: int = 0
    records_synced: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "partner_id": self.partner_id,
            "name": self.name,
            "email": self.email,
            "tier": self.tier.value,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "connectors_count": len(self.connectors),
            "webhooks_count": len(self.webhooks),
            "api_calls": self.api_calls,
            "records_synced": self.records_synced,
        }


class PartnerPortal:
    """Manage partner accounts and their integration resources."""

    def __init__(self) -> None:
        self.partners: Dict[str, Partner] = {}
        logger.info("PartnerPortal initialized")

    def create_partner(
        self,
        partner_id: str,
        name: str,
        email: str,
        tier: PartnerTier = PartnerTier.TRIAL,
    ) -> Partner:
        partner = Partner(partner_id=partner_id, name=name, email=email, tier=tier)
        self.partners[partner_id] = partner
        logger.info("Partner created: %s (%s)", name, tier.value)
        return partner

    def get_partner(self, partner_id: str) -> Optional[Partner]:
        return self.partners.get(partner_id)

    def add_connector_to_partner(self, partner_id: str, connector_id: str) -> bool:
        partner = self.partners.get(partner_id)
        if partner is None:
            return False
        if connector_id not in partner.connectors:
            partner.connectors.append(connector_id)
        logger.info("Connector %s added to partner %s", connector_id, partner_id)
        return True

    def add_webhook_to_partner(self, partner_id: str, webhook_id: str) -> bool:
        partner = self.partners.get(partner_id)
        if partner is None:
            return False
        if webhook_id not in partner.webhooks:
            partner.webhooks.append(webhook_id)
        logger.info("Webhook %s added to partner %s", webhook_id, partner_id)
        return True

    def record_api_call(self, partner_id: str) -> None:
        partner = self.partners.get(partner_id)
        if partner is not None:
            partner.api_calls += 1

    def record_sync(self, partner_id: str, records: int) -> None:
        partner = self.partners.get(partner_id)
        if partner is not None:
            partner.records_synced += records

    def get_partner_dashboard(self, partner_id: str) -> Dict[str, Any]:
        partner = self.partners.get(partner_id)
        if partner is None:
            return {}
        limits = _TIER_LIMITS.get(partner.tier, {})
        return {
            "partner": partner.to_dict(),
            "integrations": {
                "connectors": len(partner.connectors),
                "webhooks": len(partner.webhooks),
            },
            "usage": {
                "api_calls": partner.api_calls,
                "records_synced": partner.records_synced,
            },
            "limits": limits,
        }

    def list_partners(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self.partners.values()]

    def deactivate_partner(self, partner_id: str) -> bool:
        partner = self.partners.get(partner_id)
        if partner is None:
            return False
        partner.is_active = False
        return True


partner_portal = PartnerPortal()
