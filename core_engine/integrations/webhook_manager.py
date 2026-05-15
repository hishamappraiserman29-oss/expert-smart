"""
webhook_manager.py — Real-time webhook event delivery.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import uuid

try:
    import requests
except ImportError:
    requests = None  # type: ignore
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class WebhookEventType(str, Enum):
    """Supported webhook event types."""
    VALUATION_CREATED = "valuation.created"
    VALUATION_COMPLETED = "valuation.completed"
    VALUATION_UPDATED = "valuation.updated"
    BATCH_STARTED = "batch.started"
    BATCH_COMPLETED = "batch.completed"
    REPORT_GENERATED = "report.generated"
    USER_CREATED = "user.created"
    PAYMENT_RECEIVED = "payment.received"
    PLUGIN_EXECUTED = "plugin.executed"
    PLUGIN_FAILED = "plugin.failed"
    IMPORT_STARTED = "import.started"
    EXPORT_STARTED = "export.started"


@dataclass
class Webhook:
    """A registered webhook subscription."""
    webhook_id: str
    tenant_id: str
    url: str
    events: List[WebhookEventType]
    active: bool = True
    secret: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_triggered: Optional[datetime] = None
    failure_count: int = 0

    def to_dict(self) -> Dict:
        return {
            "webhook_id": self.webhook_id,
            "tenant_id": self.tenant_id,
            "url": self.url,
            "events": [e.value for e in self.events],
            "active": self.active,
            "created_at": self.created_at.isoformat(),
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None,
            "failure_count": self.failure_count,
        }


@dataclass
class WebhookPayload:
    """Event payload dispatched to webhook endpoints."""
    event_type: WebhookEventType
    tenant_id: str
    timestamp: datetime
    data: Dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_payload(self) -> Dict:
        return {
            "event_id": self.event_id,
            "event": self.event_type.value,
            "tenant_id": self.tenant_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


class WebhookManager:
    """Register webhooks and deliver events with HMAC signatures and retries."""

    def __init__(self, max_retries: int = 3, timeout: int = 10) -> None:
        self.webhooks: Dict[str, Webhook] = {}
        self.max_retries = max_retries
        self.timeout = timeout
        self._disable_threshold = 10

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_webhook(
        self, tenant_id: str, url: str, events: List[WebhookEventType]
    ) -> Webhook:
        webhook_id = str(uuid.uuid4())
        wh = Webhook(
            webhook_id=webhook_id,
            tenant_id=tenant_id,
            url=url,
            events=events,
        )
        self.webhooks[webhook_id] = wh
        logger.info("Webhook registered: %s for %d events", webhook_id, len(events))
        return wh

    def unregister_webhook(self, webhook_id: str) -> bool:
        if webhook_id not in self.webhooks:
            return False
        del self.webhooks[webhook_id]
        logger.info("Webhook removed: %s", webhook_id)
        return True

    # ------------------------------------------------------------------
    # Event dispatch
    # ------------------------------------------------------------------

    def trigger_event(self, event: WebhookPayload) -> Dict[str, Any]:
        payload = event.to_payload()
        result: Dict[str, Any] = {
            "event_id": event.event_id,
            "event": event.event_type.value,
            "sent": 0,
            "failed": 0,
            "results": [],
        }

        targets = [
            wh for wh in self.webhooks.values()
            if wh.tenant_id == event.tenant_id
            and event.event_type in wh.events
            and wh.active
        ]
        logger.info(
            "Triggering %s to %d webhooks", event.event_type.value, len(targets)
        )

        for wh in targets:
            ok = self._deliver_webhook(wh, payload)
            if ok:
                result["sent"] += 1
                wh.last_triggered = datetime.utcnow()
                wh.failure_count = 0
            else:
                result["failed"] += 1
                wh.failure_count += 1
                if wh.failure_count >= self._disable_threshold:
                    wh.active = False
                    logger.warning("Webhook disabled (too many failures): %s", wh.webhook_id)

            result["results"].append(
                {"webhook_id": wh.webhook_id, "url": wh.url, "success": ok}
            )

        return result

    def _deliver_webhook(self, webhook: Webhook, payload: Dict) -> bool:
        body = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            webhook.secret.encode(),
            body.encode(),
            hashlib.sha256,
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": f"sha256={signature}",
        }

        if requests is None:
            logger.error("requests library not available for webhook delivery")
            return False

        for attempt in range(self.max_retries):
            try:
                resp = requests.post(
                    webhook.url,
                    data=body,
                    headers=headers,
                    timeout=self.timeout,
                )
                if 200 <= resp.status_code < 300:
                    logger.info("Webhook delivered: %s", webhook.webhook_id)
                    return True
                logger.warning(
                    "Webhook HTTP %s (attempt %d): %s",
                    resp.status_code, attempt + 1, webhook.webhook_id,
                )
            except Exception as exc:
                logger.warning(
                    "Webhook error (attempt %d): %s — %s",
                    attempt + 1, webhook.webhook_id, exc,
                )

            if attempt < self.max_retries - 1:
                time.sleep(2 ** attempt)

        logger.error("Webhook failed after %d attempts: %s", self.max_retries, webhook.webhook_id)
        return False

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_webhooks(self, tenant_id: str) -> List[Webhook]:
        return [wh for wh in self.webhooks.values() if wh.tenant_id == tenant_id]

    def get_webhook(self, webhook_id: str) -> Optional[Webhook]:
        return self.webhooks.get(webhook_id)


webhook_manager = WebhookManager()
