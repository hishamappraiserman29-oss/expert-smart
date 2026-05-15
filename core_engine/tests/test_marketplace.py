"""
test_marketplace.py — Integration Marketplace Tests

Covers:
  A. PluginSystem      (A01–A10)
  B. OAuthManager      (B01–B08)
  C. WebhookManager    (C01–C08)
  D. Marketplace       (D01–D12)
  E. PluginRegistry    (E01–E06)
  F. PaymentIntegration (F01–F06)
"""

from __future__ import annotations

import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from plugins.plugin_system import (
    BasePlugin,
    PluginInstance,
    PluginMetadata,
    PluginStatus,
    PluginSystem,
    PluginType,
)
from plugins.plugin_registry import PluginRegistry
from integrations.oauth_manager import OAuthConfig, OAuthManager, OAuthToken
from integrations.webhook_manager import (
    Webhook,
    WebhookEventType,
    WebhookManager,
    WebhookPayload,
)
from integrations.payment_integration import (
    PaymentIntegration,
    PaymentProvider,
    PaymentStatus,
)
from marketplace.marketplace import ListingStatus, Marketplace


# ===========================================================================
# Helpers
# ===========================================================================

def _make_metadata(
    name: str = "Test Plugin",
    plugin_type: PluginType = PluginType.INTEGRATION,
    required_fields: list = None,
    requires_credentials: bool = False,
) -> PluginMetadata:
    return PluginMetadata(
        name=name,
        version="1.0.0",
        plugin_type=plugin_type,
        description=f"{name} description",
        author="Tester",
        author_email="test@example.com",
        required_fields=required_fields or [],
        requires_credentials=requires_credentials,
    )


class GoodPlugin(BasePlugin):
    """A plugin that always initializes and executes successfully."""

    def __init__(self, name: str = "Good Plugin", required_fields: list = None) -> None:
        self.metadata = _make_metadata(name, required_fields=required_fields)
        self.initialized = False
        self.installed = False
        self.uninstalled = False

    def initialize(self, config: Dict[str, Any]) -> bool:
        self.initialized = True
        return True

    def execute(self, *args: Any, **kwargs: Any) -> str:
        return f"executed:{kwargs.get('action', 'default')}"

    def on_install(self) -> bool:
        self.installed = True
        return True

    def on_uninstall(self) -> bool:
        self.uninstalled = True
        return True


class FailingPlugin(BasePlugin):
    """A plugin whose initialize() always returns False."""

    def __init__(self) -> None:
        self.metadata = _make_metadata("Failing Plugin")

    def initialize(self, config: Dict[str, Any]) -> bool:
        return False

    def execute(self, *args: Any, **kwargs: Any) -> None:
        raise RuntimeError("should not execute")

    def on_install(self) -> bool:
        return True

    def on_uninstall(self) -> bool:
        return True


# ===========================================================================
# A. PluginSystem
# ===========================================================================

class TestPluginSystem:

    def setup_method(self):
        self.ps = PluginSystem()
        self.plugin = GoodPlugin()
        self.tenant = "tenant-abc"

    def test_A01_register_plugin_succeeds(self):
        assert self.ps.register_plugin(self.plugin) is True
        assert self.plugin.metadata.plugin_id in self.ps.plugins

    def test_A02_register_same_plugin_twice_returns_false(self):
        self.ps.register_plugin(self.plugin)
        assert self.ps.register_plugin(self.plugin) is False

    def test_A03_install_plugin_creates_active_instance(self):
        self.ps.register_plugin(self.plugin)
        pid = self.plugin.metadata.plugin_id
        inst = self.ps.install_plugin(self.tenant, pid, {})
        assert inst is not None
        assert inst.status == PluginStatus.ACTIVE
        assert inst.tenant_id == self.tenant

    def test_A04_install_plugin_validates_required_fields(self):
        p = GoodPlugin(required_fields=["api_key"])
        self.ps.register_plugin(p)
        inst = self.ps.install_plugin(self.tenant, p.metadata.plugin_id, {})
        assert inst is None

    def test_A05_install_plugin_with_required_fields_succeeds(self):
        p = GoodPlugin(required_fields=["api_key"])
        self.ps.register_plugin(p)
        inst = self.ps.install_plugin(self.tenant, p.metadata.plugin_id, {"api_key": "k"})
        assert inst is not None
        assert inst.status == PluginStatus.ACTIVE

    def test_A06_install_failing_plugin_returns_none(self):
        p = FailingPlugin()
        self.ps.register_plugin(p)
        inst = self.ps.install_plugin(self.tenant, p.metadata.plugin_id, {})
        assert inst is None

    def test_A07_execute_plugin_returns_result_and_tracks_usage(self):
        self.ps.register_plugin(self.plugin)
        pid = self.plugin.metadata.plugin_id
        self.ps.install_plugin(self.tenant, pid, {})
        result = self.ps.execute_plugin(self.tenant, pid, action="run")
        assert result == "executed:run"
        inst = self.ps.instances[f"{self.tenant}_{pid}"]
        assert inst.usage_stats.get(f"{pid}_executions", 0) == 1

    def test_A08_execute_uninstalled_plugin_returns_none(self):
        self.ps.register_plugin(self.plugin)
        result = self.ps.execute_plugin(self.tenant, self.plugin.metadata.plugin_id)
        assert result is None

    def test_A09_uninstall_plugin_removes_instance(self):
        self.ps.register_plugin(self.plugin)
        pid = self.plugin.metadata.plugin_id
        self.ps.install_plugin(self.tenant, pid, {})
        assert self.ps.uninstall_plugin(self.tenant, pid) is True
        assert f"{self.tenant}_{pid}" not in self.ps.instances

    def test_A10_list_installed_filters_by_tenant(self):
        p1 = GoodPlugin("P1")
        p2 = GoodPlugin("P2")
        self.ps.register_plugin(p1)
        self.ps.register_plugin(p2)
        self.ps.install_plugin("tenant-1", p1.metadata.plugin_id, {})
        self.ps.install_plugin("tenant-2", p2.metadata.plugin_id, {})
        t1_plugins = self.ps.list_installed_plugins("tenant-1")
        assert len(t1_plugins) == 1
        assert t1_plugins[0].name == "P1"


# ===========================================================================
# B. OAuthManager
# ===========================================================================

class TestOAuthManager:

    def setup_method(self):
        self.om = OAuthManager()
        self.config = OAuthConfig(
            client_id="cid",
            client_secret="csecret",
            authorize_url="https://auth.example.com/oauth",
            token_url="https://auth.example.com/token",
            scopes=["read", "write"],
        )
        self.om.register_oauth("myservice", self.config)

    def test_B01_register_oauth_stores_config(self):
        assert "myservice" in self.om.configs

    def test_B02_get_authorization_url_contains_client_id(self):
        url = self.om.get_authorization_url("myservice")
        assert "cid" in url
        assert "https://auth.example.com/oauth" in url

    def test_B03_get_authorization_url_generates_state(self):
        url = self.om.get_authorization_url("myservice")
        assert "state=" in url
        assert len(self.om.states) == 1

    def test_B04_get_authorization_url_unregistered_service_raises(self):
        with pytest.raises(ValueError):
            self.om.get_authorization_url("unknown")

    def test_B05_oauth_token_not_expired_when_fresh(self):
        token = OAuthToken("tok", expires_in=3600)
        assert token.is_expired() is False

    def test_B06_oauth_token_expired_when_past_expiry(self):
        token = OAuthToken("tok", expires_in=3600)
        token.expires_at = datetime.utcnow() - timedelta(seconds=1)
        assert token.is_expired() is True

    def test_B07_exchange_code_state_validation_fails_unknown_state(self):
        result = self.om.exchange_code_for_token("myservice", "code123", state="bad-state")
        assert result is None

    def test_B08_exchange_code_with_valid_state_calls_token_endpoint(self):
        url = self.om.get_authorization_url("myservice")
        state = list(self.om.states.keys())[0]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "access_token": "access123",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        with patch("integrations.oauth_manager.requests.post", return_value=mock_resp):
            token = self.om.exchange_code_for_token("myservice", "code123", state=state)
        assert token is not None
        assert token.access_token == "access123"
        assert state not in self.om.states


# ===========================================================================
# C. WebhookManager
# ===========================================================================

class TestWebhookManager:

    def setup_method(self):
        self.wm = WebhookManager()
        self.tenant = "t-webhook"

    def _payload(self, event_type=WebhookEventType.VALUATION_CREATED) -> WebhookPayload:
        return WebhookPayload(
            event_type=event_type,
            tenant_id=self.tenant,
            timestamp=datetime.utcnow(),
            data={"valuation_id": "v-001"},
        )

    def test_C01_register_webhook_creates_entry(self):
        wh = self.wm.register_webhook(
            self.tenant, "https://example.com/hook",
            [WebhookEventType.VALUATION_CREATED],
        )
        assert wh.webhook_id in self.wm.webhooks
        assert wh.active is True

    def test_C02_unregister_webhook_removes_entry(self):
        wh = self.wm.register_webhook(self.tenant, "https://x.com", [WebhookEventType.USER_CREATED])
        assert self.wm.unregister_webhook(wh.webhook_id) is True
        assert wh.webhook_id not in self.wm.webhooks

    def test_C03_unregister_nonexistent_returns_false(self):
        assert self.wm.unregister_webhook("nope") is False

    def test_C04_trigger_event_delivers_to_matching_webhook(self):
        self.wm.register_webhook(
            self.tenant, "https://example.com/hook",
            [WebhookEventType.VALUATION_CREATED],
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("integrations.webhook_manager.requests.post", return_value=mock_resp):
            result = self.wm.trigger_event(self._payload())
        assert result["sent"] == 1
        assert result["failed"] == 0

    def test_C05_trigger_event_skips_inactive_webhooks(self):
        wh = self.wm.register_webhook(
            self.tenant, "https://example.com/hook",
            [WebhookEventType.VALUATION_CREATED],
        )
        wh.active = False
        with patch("integrations.webhook_manager.requests.post") as mock_post:
            result = self.wm.trigger_event(self._payload())
        mock_post.assert_not_called()
        assert result["sent"] == 0

    def test_C06_trigger_event_skips_wrong_event_type(self):
        self.wm.register_webhook(
            self.tenant, "https://example.com/hook",
            [WebhookEventType.BATCH_COMPLETED],
        )
        with patch("integrations.webhook_manager.requests.post") as mock_post:
            result = self.wm.trigger_event(self._payload(WebhookEventType.VALUATION_CREATED))
        mock_post.assert_not_called()
        assert result["sent"] == 0

    def test_C07_webhook_payload_has_required_keys(self):
        p = self._payload()
        d = p.to_payload()
        for key in ("event_id", "event", "tenant_id", "timestamp", "data"):
            assert key in d

    def test_C08_delivery_failure_increments_failure_count(self):
        wh = self.wm.register_webhook(
            self.tenant, "https://bad.example.com",
            [WebhookEventType.VALUATION_CREATED],
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        with patch("integrations.webhook_manager.requests.post", return_value=mock_resp), \
             patch("integrations.webhook_manager.time.sleep"):
            result = self.wm.trigger_event(self._payload())
        assert result["failed"] == 1
        assert wh.failure_count == 1


# ===========================================================================
# D. Marketplace
# ===========================================================================

class TestMarketplace:

    def setup_method(self):
        self.mp = Marketplace()
        self.listing = self.mp.publish_listing(
            plugin_id="plugin-001",
            name="CRM Connector",
            description="Connect to your CRM system",
            category="CRM",
            price=49.0,
            author="Acme",
        )
        self.listing2 = self.mp.publish_listing(
            plugin_id="plugin-002",
            name="Analytics Hub",
            description="Advanced analytics dashboard",
            category="Analytics",
            price=0.0,
            author="DataCo",
        )

    def test_D01_publish_listing_creates_published_listing(self):
        assert self.listing.status == ListingStatus.PUBLISHED
        assert self.listing.listing_id in self.mp.listings

    def test_D02_search_plugins_by_name(self):
        results = self.mp.search_plugins(query="CRM")
        assert len(results) == 1
        assert results[0].name == "CRM Connector"

    def test_D03_search_plugins_by_category(self):
        results = self.mp.search_plugins(category="Analytics")
        assert len(results) == 1
        assert results[0].category == "Analytics"

    def test_D04_search_plugins_empty_query_returns_all_published(self):
        results = self.mp.search_plugins()
        assert len(results) == 2

    def test_D05_search_plugins_sorts_by_rating(self):
        self.mp.add_review(self.listing2.listing_id, "t1", 5, "Great", "Loved it")
        results = self.mp.search_plugins(sort_by="rating")
        assert results[0].listing_id == self.listing2.listing_id

    def test_D06_search_plugins_sorts_by_downloads(self):
        self.mp.record_installation("tenant-x", "plugin-002")
        results = self.mp.search_plugins(sort_by="downloads")
        assert results[0].plugin_id == "plugin-002"

    def test_D07_add_review_creates_review(self):
        review = self.mp.add_review(self.listing.listing_id, "t1", 4, "Good", "Works well")
        assert review is not None
        assert review.rating == 4

    def test_D08_add_review_updates_aggregate_rating(self):
        self.mp.add_review(self.listing.listing_id, "t1", 4, "OK", "OK")
        self.mp.add_review(self.listing.listing_id, "t2", 2, "Meh", "Not great")
        listing = self.mp.listings[self.listing.listing_id]
        assert abs(listing.ratings - 3.0) < 0.001
        assert listing.review_count == 2

    def test_D09_add_review_rejects_rating_below_1(self):
        review = self.mp.add_review(self.listing.listing_id, "t1", 0, "Zero", "Bad")
        assert review is None

    def test_D10_add_review_rejects_rating_above_5(self):
        review = self.mp.add_review(self.listing.listing_id, "t1", 6, "Too high", "Bad")
        assert review is None

    def test_D11_get_reviews_returns_correct_reviews(self):
        self.mp.add_review(self.listing.listing_id, "t1", 5, "A", "A")
        self.mp.add_review(self.listing2.listing_id, "t2", 3, "B", "B")
        reviews = self.mp.get_reviews(self.listing.listing_id)
        assert len(reviews) == 1
        assert reviews[0].rating == 5

    def test_D12_record_installation_increments_download_count(self):
        before = self.listing.download_count
        self.mp.record_installation("tenant-y", "plugin-001")
        assert self.listing.download_count == before + 1

    def test_D13_get_category_counts_returns_correct_counts(self):
        counts = self.mp.get_category_counts()
        assert counts.get("CRM", 0) == 1
        assert counts.get("Analytics", 0) == 1

    def test_D14_get_trending_plugins_respects_limit(self):
        for i in range(5):
            self.mp.publish_listing(f"extra-{i}", f"Plugin {i}", "desc", "Extra")
        trending = self.mp.get_trending_plugins(limit=3)
        assert len(trending) == 3

    def test_D15_unpublish_listing_archives_it(self):
        self.mp.unpublish_listing(self.listing.listing_id)
        assert self.listing.status == ListingStatus.ARCHIVED
        results = self.mp.search_plugins()
        assert all(r.listing_id != self.listing.listing_id for r in results)


# ===========================================================================
# E. PluginRegistry
# ===========================================================================

class TestPluginRegistry:

    def setup_method(self):
        self.reg = PluginRegistry()
        self.meta_int = _make_metadata("Integration A", PluginType.INTEGRATION)
        self.meta_ext = _make_metadata("Extension B", PluginType.EXTENSION)
        self.reg.register(self.meta_int)
        self.reg.register(self.meta_ext)

    def test_E01_register_stores_metadata(self):
        assert self.reg.get(self.meta_int.plugin_id) is not None

    def test_E02_register_duplicate_returns_false(self):
        assert self.reg.register(self.meta_int) is False

    def test_E03_search_by_query_matches_name(self):
        results = self.reg.search(query="Integration")
        assert len(results) == 1
        assert results[0].name == "Integration A"

    def test_E04_get_by_type_filters_correctly(self):
        integrations = self.reg.get_by_type(PluginType.INTEGRATION)
        assert all(m.plugin_type == PluginType.INTEGRATION for m in integrations)

    def test_E05_unregister_removes_plugin(self):
        self.reg.unregister(self.meta_int.plugin_id)
        assert self.reg.get(self.meta_int.plugin_id) is None

    def test_E06_get_stats_reports_totals(self):
        stats = self.reg.get_stats()
        assert stats["total"] == 2
        assert "integration" in stats["by_type"]


# ===========================================================================
# F. PaymentIntegration (mock provider)
# ===========================================================================

class TestPaymentIntegration:

    def setup_method(self):
        self.pi = PaymentIntegration(provider=PaymentProvider.MOCK)

    def test_F01_create_payment_intent_returns_pending(self):
        intent = self.pi.create_payment_intent(100.0, "egp", "Test")
        assert intent.status == PaymentStatus.PENDING
        assert intent.amount == 100.0

    def test_F02_confirm_payment_marks_succeeded(self):
        intent = self.pi.create_payment_intent(50.0)
        assert self.pi.confirm_payment(intent.payment_id) is True
        assert self.pi.get_payment_status(intent.payment_id).status == PaymentStatus.SUCCEEDED

    def test_F03_refund_after_confirm_marks_refunded(self):
        intent = self.pi.create_payment_intent(200.0)
        self.pi.confirm_payment(intent.payment_id)
        assert self.pi.refund_payment(intent.payment_id) is True
        assert self.pi.get_payment_status(intent.payment_id).status == PaymentStatus.REFUNDED

    def test_F04_refund_pending_payment_returns_false(self):
        intent = self.pi.create_payment_intent(30.0)
        assert self.pi.refund_payment(intent.payment_id) is False

    def test_F05_cancel_pending_payment_marks_cancelled(self):
        intent = self.pi.create_payment_intent(10.0)
        assert self.pi.cancel_payment(intent.payment_id) is True
        assert self.pi.get_payment_status(intent.payment_id).status == PaymentStatus.CANCELLED

    def test_F06_payment_intent_to_dict_has_required_keys(self):
        intent = self.pi.create_payment_intent(75.0, "usd", "Valuation fee")
        d = intent.to_dict()
        for key in ("payment_id", "provider", "amount", "currency", "status"):
            assert key in d
