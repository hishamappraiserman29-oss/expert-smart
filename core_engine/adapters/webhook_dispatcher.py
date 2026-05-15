"""
webhook_dispatcher.py — Webhook Notification Dispatcher (Phase 14.0)

Fires an HTTP POST to a caller-supplied URL when a batch completes.
Retries up to max_attempts times with exponential back-off.
Runs in a daemon thread so it never blocks the HTTP response.

Classes:
    WebhookDelivery    — per-delivery state record
    WebhookDispatcher  — background thread dispatcher with retry
"""
from __future__ import annotations

import json
import threading
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional


# ── Delivery record ───────────────────────────────────────────────────────────

@dataclass
class WebhookDelivery:
    """Mutable state record for one webhook delivery attempt sequence."""

    url:          str
    payload:      Dict
    batch_id:     str   = ""
    max_attempts: int   = 3

    # Updated by dispatcher during delivery
    status:        str           = "pending"   # pending | delivered | failed
    attempt_count: int           = 0
    last_status:   int           = 0           # last HTTP status code (0 = no response)
    last_error:    str           = ""
    delivered_at:  Optional[str] = None
    created_at:    str           = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "url":          self.url,
            "batch_id":     self.batch_id,
            "status":       self.status,
            "attempt_count":self.attempt_count,
            "last_status":  self.last_status,
            "last_error":   self.last_error,
            "delivered_at": self.delivered_at,
            "created_at":   self.created_at,
        }


# ── Dispatcher ────────────────────────────────────────────────────────────────

class WebhookDispatcher:
    """
    Fire-and-forget webhook dispatcher with configurable retry back-off.

    Parameters
    ----------
    base_delay   : seconds between attempt 1→2. Doubled each retry.
                   Pass a small value (e.g. 0.01) in tests for fast execution.
    max_attempts : total number of POST attempts before marking as failed.
    timeout      : per-request socket timeout in seconds.
    """

    def __init__(
        self,
        base_delay:   float = 2.0,
        max_attempts: int   = 3,
        timeout:      float = 10.0,
    ) -> None:
        self.base_delay   = base_delay
        self.max_attempts = max_attempts
        self.timeout      = timeout

    # ── Public interface ──────────────────────────────────────────────────────

    def dispatch(self, url: str, payload: Dict, batch_id: str = "",
                 on_complete=None) -> WebhookDelivery:
        """
        Start an async delivery in a daemon thread.
        Returns the WebhookDelivery immediately (status still 'pending').
        on_complete(delivery) is called from the thread when done (success or failure).
        """
        delivery = WebhookDelivery(
            url=url, payload=payload,
            batch_id=batch_id, max_attempts=self.max_attempts,
        )
        t = threading.Thread(
            target=self._send_with_retry, args=(delivery, on_complete), daemon=True
        )
        t.start()
        return delivery

    def dispatch_sync(self, url: str, payload: Dict, batch_id: str = "",
                      on_complete=None) -> WebhookDelivery:
        """
        Synchronous delivery — blocks until done or exhausted.
        Use in tests; do NOT use in request handlers.
        """
        delivery = WebhookDelivery(
            url=url, payload=payload,
            batch_id=batch_id, max_attempts=self.max_attempts,
        )
        self._send_with_retry(delivery, on_complete)
        return delivery

    # ── Internal retry loop ───────────────────────────────────────────────────

    def _send_with_retry(self, delivery: WebhookDelivery, on_complete=None) -> None:
        data = json.dumps(delivery.payload).encode("utf-8")

        for attempt in range(1, delivery.max_attempts + 1):
            delivery.attempt_count = attempt
            try:
                req = urllib.request.Request(
                    delivery.url,
                    data=data,
                    headers={"Content-Type": "application/json",
                             "X-ExpertSmart-Event": "batch.completed"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    delivery.last_status = resp.status
                    if 200 <= resp.status < 300:
                        delivery.status       = "delivered"
                        delivery.delivered_at = datetime.now().isoformat()
                        if on_complete is not None:
                            try:
                                on_complete(delivery)
                            except Exception:
                                pass
                        return
                    delivery.last_error = f"HTTP {resp.status}"

            except urllib.error.HTTPError as exc:
                delivery.last_status = exc.code
                delivery.last_error  = f"HTTP {exc.code}: {exc.reason}"

            except Exception as exc:
                delivery.last_status = 0
                delivery.last_error  = str(exc)

            if attempt < delivery.max_attempts:
                time.sleep(self.base_delay * (2 ** (attempt - 1)))

        delivery.status = "failed"
        if on_complete is not None:
            try:
                on_complete(delivery)
            except Exception:
                pass
