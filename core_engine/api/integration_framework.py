"""
integration_framework.py — Integration Framework (Phase 38)

Third-party integration registration, webhook management, and event dispatch.

Note: The spec defined both an `IntegrationEvent` enum and an `IntegrationEvent`
dataclass (name collision). The dataclass is renamed `FiredEvent` here to resolve
the conflict while keeping the enum accessible as `IntegrationEvent`.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class IntegrationEvent(str, Enum):
    """Events that integrations can subscribe to."""
    VALUATION_COMPLETED = "valuation.completed"
    REPORT_GENERATED = "report.generated"
    PROPERTY_CREATED = "property.created"
    PROPERTY_UPDATED = "property.updated"
    SEARCH_COMPLETED = "search.completed"
    ERROR_OCCURRED = "error.occurred"


@dataclass
class FiredEvent:
    """A single dispatched integration event record."""
    event_type: IntegrationEvent
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event": self.event_type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class Integration:
    integration_id: str
    name: str
    provider: str
    webhook_url: Optional[str] = None
    api_key: Optional[str] = None
    subscribed_events: List[IntegrationEvent] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_event_at: Optional[datetime] = None
    is_active: bool = True
    success_count: int = 0
    failure_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "integration_id": self.integration_id,
            "name": self.name,
            "provider": self.provider,
            "is_active": self.is_active,
            "webhook_url": self.webhook_url,
            "subscribed_events": [e.value for e in self.subscribed_events],
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "created_at": self.created_at.isoformat(),
        }


class IntegrationFramework:
    """Register integrations and dispatch events to subscribed webhooks."""

    def __init__(self) -> None:
        self.integrations: Dict[str, Integration] = {}
        self.event_queue: List[FiredEvent] = []
        self._lock = threading.Lock()
        logger.info("Integration Framework initialized")

    def register_integration(
        self,
        integration_id: str,
        name: str,
        provider: str,
        webhook_url: Optional[str] = None,
        events: Optional[List[IntegrationEvent]] = None,
    ) -> Integration:
        integration = Integration(
            integration_id=integration_id,
            name=name,
            provider=provider,
            webhook_url=webhook_url,
            subscribed_events=events or [],
        )
        with self._lock:
            self.integrations[integration_id] = integration
        logger.info("Integration registered: %s (%s)", name, provider)
        return integration

    def deactivate_integration(self, integration_id: str) -> bool:
        with self._lock:
            integ = self.integrations.get(integration_id)
        if integ is None:
            return False
        integ.is_active = False
        return True

    def emit_event(self, event_type: IntegrationEvent, data: Dict[str, Any]) -> int:
        fired = FiredEvent(event_type=event_type, data=data)
        with self._lock:
            self.event_queue.append(fired)
            targets = [
                i for i in self.integrations.values()
                if i.is_active and event_type in i.subscribed_events
            ]

        triggered = 0
        for integration in targets:
            success = self._trigger_integration(integration, fired)
            triggered += 1 if success else 0

        logger.info("Event emitted: %s → %d integrations triggered", event_type.value, triggered)
        return triggered

    def get_integration(self, integration_id: str) -> Optional[Integration]:
        with self._lock:
            return self.integrations.get(integration_id)

    def get_integration_statistics(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self.integrations)
            active = sum(1 for i in self.integrations.values() if i.is_active)
            total_events = sum(
                i.success_count + i.failure_count for i in self.integrations.values()
            )
            queue_len = len(self.event_queue)
        return {
            "total_integrations": total,
            "active_integrations": active,
            "total_events_sent": total_events,
            "event_queue_length": queue_len,
        }

    def count(self) -> int:
        with self._lock:
            return len(self.integrations)

    # ── private ────────────────────────────────────────────────────────────────

    def _trigger_integration(self, integration: Integration, event: FiredEvent) -> bool:
        # Production: HTTP POST to integration.webhook_url; simulated here.
        success = True
        if success:
            integration.success_count += 1
        else:
            integration.failure_count += 1
        integration.last_event_at = datetime.utcnow()
        return success


integration_framework = IntegrationFramework()
