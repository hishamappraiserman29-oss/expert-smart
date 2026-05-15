"""
stripe_plugin.py — Example Stripe payment integration plugin.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from plugins.plugin_system import BasePlugin, PluginMetadata, PluginType

logger = logging.getLogger(__name__)


class StripePlugin(BasePlugin):
    """Accept payments via Stripe."""

    def __init__(self) -> None:
        self.metadata = PluginMetadata(
            name="Stripe Payments",
            version="1.0.0",
            plugin_type=PluginType.INTEGRATION,
            description="Accept payments via Stripe",
            author="Expert Smart",
            author_email="plugins@expert-smart.com",
            homepage="https://stripe.com",
            documentation="https://docs.stripe.com",
            requires_credentials=True,
            required_fields=["api_key", "secret_key"],
        )
        self._stripe: Optional[Any] = None
        self._config: Dict[str, Any] = {}

    def initialize(self, config: Dict[str, Any]) -> bool:
        if not self.validate_config(config):
            return False
        try:
            import stripe  # type: ignore
            stripe.api_key = config["secret_key"]
            self._stripe = stripe
            self._config = config
            logger.info("Stripe plugin initialized")
            return True
        except ImportError:
            logger.warning("stripe package not installed — Stripe plugin disabled")
            return False
        except Exception as exc:
            logger.error("Stripe init error: %s", exc)
            return False

    def execute(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        if self._stripe is None:
            return {"success": False, "error": "Stripe not initialized"}
        try:
            amount = kwargs.get("amount", 0)
            currency = kwargs.get("currency", "usd")
            description = kwargs.get("description", "")
            intent = self._stripe.PaymentIntent.create(
                amount=int(amount * 100),
                currency=currency,
                description=description,
            )
            return {
                "success": True,
                "payment_id": intent.id,
                "status": intent.status,
                "client_secret": intent.client_secret,
            }
        except Exception as exc:
            logger.error("Stripe payment error: %s", exc)
            return {"success": False, "error": str(exc)}

    def on_install(self) -> bool:
        logger.info("Stripe plugin installed")
        return True

    def on_uninstall(self) -> bool:
        self._stripe = None
        logger.info("Stripe plugin uninstalled")
        return True

    def get_status(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.metadata.plugin_id,
            "name": self.metadata.name,
            "version": self.metadata.version,
            "status": "active" if self._stripe else "inactive",
        }


stripe_plugin = StripePlugin()
