"""
test_phase40_integrations.py — Phase 40: Integration Framework Tests

TestConnectorBase    A01–A10  connector config + result dataclasses
TestBankConnector    B01–B08  bank connector (offline behavior)
TestDataMapper       C01–C10  field mapping and data transformation
TestSyncEngine       D01–D08  sync scheduling and statistics
TestPartnerPortal    E01–E10  partner CRUD and dashboard
TestWebhookManager   F01–F08  existing webhook manager (Phase 26)
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from integrations.connector_base import (
    ConnectorConfig,
    ConnectorStatus,
    ConnectorType,
    SyncDirection,
    SyncResult,
)
from integrations.connectors.bank_connector import BankConnector
from integrations.data_mapper import DataMapper, FieldMapping
from integrations.partner_portal import Partner, PartnerPortal, PartnerTier
from integrations.sync_engine import SyncEngine
from integrations.webhook_manager import WebhookEventType, WebhookManager


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def bank_config() -> ConnectorConfig:
    return ConnectorConfig(
        connector_id="BANK_TEST_01",
        connector_type=ConnectorType.BANKING,
        name="Test Bank",
        endpoint_url="http://localhost:19999",
        api_key="test-key-abc",
        sync_direction=SyncDirection.BIDIRECTIONAL,
        custom_params={"bank_code": "NBE", "branch_id": "B001"},
    )


@pytest.fixture()
def bank_connector(bank_config: ConnectorConfig) -> BankConnector:
    return BankConnector(bank_config)


@pytest.fixture()
def mapper() -> DataMapper:
    return DataMapper()


@pytest.fixture()
def sync_engine_fresh() -> SyncEngine:
    return SyncEngine()


@pytest.fixture()
def portal() -> PartnerPortal:
    return PartnerPortal()


@pytest.fixture()
def wh_manager() -> WebhookManager:
    return WebhookManager()


# ── TestConnectorBase ─────────────────────────────────────────────────────────

class TestConnectorBase:

    def test_A01_connector_config_stores_id(self, bank_config: ConnectorConfig) -> None:
        assert bank_config.connector_id == "BANK_TEST_01"

    def test_A02_connector_config_stores_type(self, bank_config: ConnectorConfig) -> None:
        assert bank_config.connector_type == ConnectorType.BANKING

    def test_A03_connector_config_to_dict_excludes_secrets(self, bank_config: ConnectorConfig) -> None:
        d = bank_config.to_dict()
        assert "api_key" not in d
        assert "api_secret" not in d
        assert "password" not in d

    def test_A04_connector_config_to_dict_has_required_keys(self, bank_config: ConnectorConfig) -> None:
        d = bank_config.to_dict()
        assert {"connector_id", "connector_type", "name", "endpoint_url"}.issubset(d.keys())

    def test_A05_sync_direction_enum_values(self) -> None:
        assert SyncDirection.INCOMING.value == "incoming"
        assert SyncDirection.OUTGOING.value == "outgoing"
        assert SyncDirection.BIDIRECTIONAL.value == "bidirectional"

    def test_A06_connector_type_enum_has_banking(self) -> None:
        assert ConnectorType.BANKING.value == "banking"

    def test_A07_connector_status_enum_values(self) -> None:
        assert ConnectorStatus.ACTIVE.value == "active"
        assert ConnectorStatus.ERROR.value == "error"

    def test_A08_sync_result_default_success_true(self, bank_config: ConnectorConfig) -> None:
        from datetime import datetime
        result = SyncResult(
            connector_id="X",
            sync_time=datetime.utcnow(),
            direction=SyncDirection.INCOMING,
        )
        assert result.is_success is True

    def test_A09_sync_result_to_dict_has_required_keys(self, bank_config: ConnectorConfig) -> None:
        from datetime import datetime
        result = SyncResult(
            connector_id="X",
            sync_time=datetime.utcnow(),
            direction=SyncDirection.INCOMING,
        )
        d = result.to_dict()
        assert {"connector_id", "sync_time", "records_synced", "is_success", "duration_seconds"}.issubset(d.keys())

    def test_A10_connector_config_default_enabled_true(self, bank_config: ConnectorConfig) -> None:
        assert bank_config.enabled is True


# ── TestBankConnector ─────────────────────────────────────────────────────────

class TestBankConnector:

    def test_B01_bank_connector_stores_bank_code(self, bank_connector: BankConnector) -> None:
        assert bank_connector.bank_code == "NBE"

    def test_B02_bank_connector_stores_branch_id(self, bank_connector: BankConnector) -> None:
        assert bank_connector.branch_id == "B001"

    def test_B03_validate_connection_offline_returns_false(self, bank_connector: BankConnector) -> None:
        result = bank_connector.validate_connection()
        assert result is False

    def test_B04_validate_connection_does_not_raise(self, bank_connector: BankConnector) -> None:
        try:
            bank_connector.validate_connection()
        except Exception:
            pytest.fail("validate_connection raised an exception")

    def test_B05_pull_data_offline_returns_error_string(self, bank_connector: BankConnector) -> None:
        records, error = bank_connector.pull_data()
        assert records == []
        assert error is not None

    def test_B06_pull_data_offline_no_raise(self, bank_connector: BankConnector) -> None:
        records, error = bank_connector.pull_data()
        assert isinstance(records, list)

    def test_B07_transform_incoming_maps_fields(self, bank_connector: BankConnector) -> None:
        external = {
            "mortgage_id": "M001",
            "property_id": "P001",
            "loan_amount": 500000,
            "purpose": "purchase",
            "borrower_id": "B001",
            "property_type": "residential",
            "area_sqm": 150,
        }
        result = bank_connector.transform_incoming(external)
        assert result["external_id"] == "M001"
        assert result["collateral_id"] == "P001"
        assert result["loan_amount"] == 500000
        assert result["status"] == "pending_valuation"

    def test_B08_transform_outgoing_maps_fields(self, bank_connector: BankConnector) -> None:
        internal = {
            "collateral_id": "C001",
            "valuation_id": "V001",
            "final_value": 1_200_000,
            "property_type": "residential",
            "ltv": 0.75,
        }
        result = bank_connector.transform_outgoing(internal)
        assert result["collateral_id"] == "C001"
        assert result["appraised_value"] == 1_200_000
        assert result["ltv"] == 0.75


# ── TestDataMapper ────────────────────────────────────────────────────────────

class TestDataMapper:

    def test_C01_mapper_has_prebuilt_mappings(self, mapper: DataMapper) -> None:
        assert len(mapper.list_mappings()) >= 4

    def test_C02_map_property_to_bank_maps_collateral_id(self, mapper: DataMapper) -> None:
        source: Dict[str, Any] = {
            "property_id": "PROP_001",
            "area_sqm": 150,
            "price": 1_500_000,
            "property_type": "residential",
            "location": "Cairo",
            "condition": "good",
        }
        result = mapper.map_data(source, "property_to_bank")
        assert result["collateral_id"] == "PROP_001"

    def test_C03_map_property_to_bank_maps_appraised_value(self, mapper: DataMapper) -> None:
        source: Dict[str, Any] = {
            "property_id": "PROP_002",
            "price": 2_000_000,
            "property_type": "commercial",
            "location": "Giza",
            "condition": "excellent",
        }
        result = mapper.map_data(source, "property_to_bank")
        assert result["appraised_value"] == 2_000_000.0

    def test_C04_map_data_unknown_mapping_raises(self, mapper: DataMapper) -> None:
        with pytest.raises(ValueError, match="not found"):
            mapper.map_data({}, "nonexistent_mapping")

    def test_C05_validate_mapping_passes_valid_data(self, mapper: DataMapper) -> None:
        source: Dict[str, Any] = {"property_id": "X", "price": 100}
        ok, msg = mapper.validate_mapping(source, "property_to_bank")
        assert ok is True

    def test_C06_validate_mapping_unknown_mapping_fails(self, mapper: DataMapper) -> None:
        ok, msg = mapper.validate_mapping({}, "ghost_mapping")
        assert ok is False

    def test_C07_register_custom_mapping(self, mapper: DataMapper) -> None:
        mapper.register_mapping("custom_test", {
            "field_a": FieldMapping("src_a", "dst_a"),
        })
        assert "custom_test" in mapper.list_mappings()

    def test_C08_custom_mapping_maps_field(self, mapper: DataMapper) -> None:
        mapper.register_mapping("custom_x", {
            "val": FieldMapping("raw_val", "clean_val", lambda x: x * 2),
        })
        result = mapper.map_data({"raw_val": 5}, "custom_x")
        assert result["clean_val"] == 10

    def test_C09_field_mapping_returns_none_for_missing_optional(self, mapper: DataMapper) -> None:
        fm = FieldMapping("missing_field", "dest_field", required=False)
        dest, val = fm.apply({"other_field": 1})
        assert dest is None
        assert val is None

    def test_C10_field_mapping_raises_for_missing_required(self, mapper: DataMapper) -> None:
        fm = FieldMapping("required_field", "dest_field", required=True)
        with pytest.raises(ValueError, match="Required field missing"):
            fm.apply({"other_field": 1})


# ── TestSyncEngine ────────────────────────────────────────────────────────────

class TestSyncEngine:

    def test_D01_fresh_engine_has_no_connectors(self, sync_engine_fresh: SyncEngine) -> None:
        assert sync_engine_fresh.connectors == {}

    def test_D02_statistics_keys_present_on_fresh_engine(self, sync_engine_fresh: SyncEngine) -> None:
        stats = sync_engine_fresh.get_sync_statistics()
        assert {"total_connectors", "active_connectors", "total_syncs", "successful_syncs", "success_rate"}.issubset(stats.keys())

    def test_D03_fresh_engine_zero_connectors(self, sync_engine_fresh: SyncEngine) -> None:
        stats = sync_engine_fresh.get_sync_statistics()
        assert stats["total_connectors"] == 0

    def test_D04_sync_unknown_connector_returns_false(self, sync_engine_fresh: SyncEngine) -> None:
        result = sync_engine_fresh.sync_connector("NONEXISTENT")
        assert result is False

    def test_D05_register_connector_adds_to_registry(self, sync_engine_fresh: SyncEngine, bank_connector: BankConnector) -> None:
        sync_engine_fresh.register_connector(bank_connector)
        assert "BANK_TEST_01" in sync_engine_fresh.connectors

    def test_D06_registered_connector_stats_updated(self, sync_engine_fresh: SyncEngine, bank_connector: BankConnector) -> None:
        sync_engine_fresh.register_connector(bank_connector)
        stats = sync_engine_fresh.get_sync_statistics()
        assert stats["total_connectors"] == 1

    def test_D07_disabled_connector_sync_returns_false(self, sync_engine_fresh: SyncEngine, bank_config: ConnectorConfig) -> None:
        bank_config.enabled = False
        connector = BankConnector(bank_config)
        sync_engine_fresh.register_connector(connector)
        result = sync_engine_fresh.sync_connector(bank_config.connector_id)
        assert result is False

    def test_D08_sync_all_returns_dict(self, sync_engine_fresh: SyncEngine) -> None:
        result = sync_engine_fresh.sync_all()
        assert isinstance(result, dict)


# ── TestPartnerPortal ─────────────────────────────────────────────────────────

class TestPartnerPortal:

    def test_E01_create_partner_stores_partner(self, portal: PartnerPortal) -> None:
        portal.create_partner("P001", "Acme Bank", "contact@acme.com")
        assert "P001" in portal.partners

    def test_E02_partner_has_api_key(self, portal: PartnerPortal) -> None:
        partner = portal.create_partner("P002", "Beta Corp", "b@beta.com")
        assert partner.api_key is not None
        assert len(partner.api_key) > 10

    def test_E03_partner_tier_set_correctly(self, portal: PartnerPortal) -> None:
        partner = portal.create_partner("P003", "Gamma Ltd", "g@gamma.com", PartnerTier.PROFESSIONAL)
        assert partner.tier == PartnerTier.PROFESSIONAL

    def test_E04_add_connector_to_partner(self, portal: PartnerPortal) -> None:
        portal.create_partner("P004", "Delta Co", "d@delta.com")
        ok = portal.add_connector_to_partner("P004", "CONN_001")
        assert ok is True
        assert "CONN_001" in portal.partners["P004"].connectors

    def test_E05_add_webhook_to_partner(self, portal: PartnerPortal) -> None:
        portal.create_partner("P005", "Epsilon SA", "e@eps.com")
        ok = portal.add_webhook_to_partner("P005", "WH_001")
        assert ok is True

    def test_E06_record_api_call_increments(self, portal: PartnerPortal) -> None:
        portal.create_partner("P006", "Zeta Bank", "z@zeta.com")
        portal.record_api_call("P006")
        portal.record_api_call("P006")
        assert portal.partners["P006"].api_calls == 2

    def test_E07_record_sync_increments(self, portal: PartnerPortal) -> None:
        portal.create_partner("P007", "Eta Corp", "e@eta.com")
        portal.record_sync("P007", 150)
        assert portal.partners["P007"].records_synced == 150

    def test_E08_dashboard_has_required_keys(self, portal: PartnerPortal) -> None:
        portal.create_partner("P008", "Theta Inc", "t@theta.com")
        dashboard = portal.get_partner_dashboard("P008")
        assert {"partner", "integrations", "usage", "limits"}.issubset(dashboard.keys())

    def test_E09_dashboard_returns_empty_for_unknown_partner(self, portal: PartnerPortal) -> None:
        dashboard = portal.get_partner_dashboard("NONEXISTENT")
        assert dashboard == {}

    def test_E10_deactivate_partner(self, portal: PartnerPortal) -> None:
        portal.create_partner("P009", "Iota Ltd", "i@iota.com")
        ok = portal.deactivate_partner("P009")
        assert ok is True
        assert portal.partners["P009"].is_active is False


# ── TestWebhookManager ────────────────────────────────────────────────────────

class TestWebhookManager:

    def test_F01_register_webhook_returns_webhook(self, wh_manager: WebhookManager) -> None:
        wh = wh_manager.register_webhook(
            tenant_id="T001",
            url="https://example.com/hook",
            events=[WebhookEventType.VALUATION_COMPLETED],
        )
        assert wh.tenant_id == "T001"

    def test_F02_webhook_url_stored(self, wh_manager: WebhookManager) -> None:
        wh = wh_manager.register_webhook(
            tenant_id="T002",
            url="https://hooks.example.com/v1",
            events=[WebhookEventType.REPORT_GENERATED],
        )
        assert wh.url == "https://hooks.example.com/v1"

    def test_F03_webhook_events_stored(self, wh_manager: WebhookManager) -> None:
        wh = wh_manager.register_webhook(
            tenant_id="T003",
            url="https://example.com/ev",
            events=[WebhookEventType.BATCH_COMPLETED, WebhookEventType.VALUATION_COMPLETED],
        )
        assert WebhookEventType.BATCH_COMPLETED in wh.events

    def test_F04_webhook_active_by_default(self, wh_manager: WebhookManager) -> None:
        wh = wh_manager.register_webhook(
            tenant_id="T004",
            url="https://example.com/",
            events=[WebhookEventType.VALUATION_CREATED],
        )
        assert wh.active is True

    def test_F05_unregister_webhook_removes_it(self, wh_manager: WebhookManager) -> None:
        wh = wh_manager.register_webhook(
            tenant_id="T005",
            url="https://example.com/",
            events=[WebhookEventType.USER_CREATED],
        )
        ok = wh_manager.unregister_webhook(wh.webhook_id)
        assert ok is True
        assert wh.webhook_id not in wh_manager.webhooks

    def test_F06_unregister_unknown_returns_false(self, wh_manager: WebhookManager) -> None:
        ok = wh_manager.unregister_webhook("nonexistent-id")
        assert ok is False

    def test_F07_list_webhooks_by_tenant(self, wh_manager: WebhookManager) -> None:
        wh_manager.register_webhook("TENANT_A", "https://a.com/", [WebhookEventType.REPORT_GENERATED])
        wh_manager.register_webhook("TENANT_B", "https://b.com/", [WebhookEventType.REPORT_GENERATED])
        result = wh_manager.list_webhooks("TENANT_A")
        assert len(result) == 1
        assert result[0].tenant_id == "TENANT_A"

    def test_F08_webhook_to_dict_has_required_keys(self, wh_manager: WebhookManager) -> None:
        wh = wh_manager.register_webhook(
            tenant_id="T008",
            url="https://example.com/",
            events=[WebhookEventType.VALUATION_COMPLETED],
        )
        d = wh.to_dict()
        assert {"webhook_id", "tenant_id", "url", "events", "active"}.issubset(d.keys())
