"""
payment_integration.py — Generic payment abstraction with optional Stripe backend.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class PaymentProvider(str, Enum):
    STRIPE = "stripe"
    PAYPAL = "paypal"
    MOCK = "mock"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


@dataclass
class PaymentIntent:
    payment_id: str
    provider: PaymentProvider
    amount: float
    currency: str
    status: PaymentStatus
    description: str = ""
    client_secret: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        return {
            "payment_id": self.payment_id,
            "provider": self.provider.value,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status.value,
            "description": self.description,
            "client_secret": self.client_secret,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


class PaymentIntegration:
    """Unified payment gateway — delegates to provider backend."""

    def __init__(self, provider: PaymentProvider = PaymentProvider.MOCK) -> None:
        self.provider = provider
        self._intents: Dict[str, PaymentIntent] = {}

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_payment_intent(
        self,
        amount: float,
        currency: str = "usd",
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PaymentIntent:
        if self.provider == PaymentProvider.STRIPE:
            return self._stripe_create(amount, currency, description, metadata or {})
        return self._mock_create(amount, currency, description, metadata or {})

    def _stripe_create(
        self, amount: float, currency: str, description: str, metadata: Dict
    ) -> PaymentIntent:
        try:
            import stripe  # type: ignore
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),
                currency=currency,
                description=description,
                metadata=metadata,
            )
            pi = PaymentIntent(
                payment_id=intent.id,
                provider=PaymentProvider.STRIPE,
                amount=amount,
                currency=currency,
                status=PaymentStatus.PENDING,
                description=description,
                client_secret=intent.client_secret,
                metadata=metadata,
            )
            self._intents[pi.payment_id] = pi
            return pi
        except Exception as exc:
            logger.error("Stripe create error: %s", exc)
            raise

    def _mock_create(
        self, amount: float, currency: str, description: str, metadata: Dict
    ) -> PaymentIntent:
        pid = f"pi_mock_{uuid.uuid4().hex[:12]}"
        pi = PaymentIntent(
            payment_id=pid,
            provider=PaymentProvider.MOCK,
            amount=amount,
            currency=currency,
            status=PaymentStatus.PENDING,
            description=description,
            client_secret=f"secret_{pid}",
            metadata=metadata,
        )
        self._intents[pid] = pi
        logger.info("Mock payment created: %s (%.2f %s)", pid, amount, currency)
        return pi

    # ------------------------------------------------------------------
    # Confirm / Refund / Status
    # ------------------------------------------------------------------

    def confirm_payment(self, payment_id: str) -> bool:
        intent = self._intents.get(payment_id)
        if intent is None:
            return False
        intent.status = PaymentStatus.SUCCEEDED
        logger.info("Payment confirmed: %s", payment_id)
        return True

    def refund_payment(self, payment_id: str) -> bool:
        intent = self._intents.get(payment_id)
        if intent is None or intent.status != PaymentStatus.SUCCEEDED:
            return False
        intent.status = PaymentStatus.REFUNDED
        logger.info("Payment refunded: %s", payment_id)
        return True

    def get_payment_status(self, payment_id: str) -> Optional[PaymentIntent]:
        return self._intents.get(payment_id)

    def cancel_payment(self, payment_id: str) -> bool:
        intent = self._intents.get(payment_id)
        if intent is None or intent.status != PaymentStatus.PENDING:
            return False
        intent.status = PaymentStatus.CANCELLED
        return True
