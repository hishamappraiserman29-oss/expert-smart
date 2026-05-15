"""
Tests for Phase 38 — API Hardening & External Integration Readiness
44 tests: A01-A12 (APISecurityLayer), B01-B08 (RequestValidator),
          C01-C06 (PerformanceOptimizer), D01-D08 (ErrorStandardizer),
          E01-E10 (IntegrationFramework)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from datetime import datetime, timedelta

from api.security_layer import APISecurityLayer, RateLimitTier, APIKey
from api.request_validation import RequestValidator, DataType, ValidationType
from api.performance_optimizer import PerformanceOptimizer
from api.error_standardizer import ErrorStandardizer, StandardErrorCode, ErrorCode
from api.integration_framework import (
    IntegrationFramework,
    IntegrationEvent,
    Integration,
)


# ── TestAPISecurityLayer ───────────────────────────────────────────────────────

class TestAPISecurityLayer:

    @pytest.fixture
    def sec(self):
        return APISecurityLayer()

    def test_A01_generate_api_key_prefix(self, sec):
        key = sec.generate_api_key("P1", "PartnerA", RateLimitTier.STARTER)
        assert key.key_id.startswith("sk_")

    def test_A02_generated_key_stored(self, sec):
        key = sec.generate_api_key("P1", "PartnerA", RateLimitTier.STARTER)
        assert key.key_id in sec.api_keys

    def test_A03_generated_key_tier_preserved(self, sec):
        key = sec.generate_api_key("P2", "PartnerB", RateLimitTier.PROFESSIONAL)
        assert key.tier == RateLimitTier.PROFESSIONAL

    def test_A04_validate_correct_credentials_returns_true(self, sec):
        key = sec.generate_api_key("P1", "PartnerA")
        valid, returned_key = sec.validate_api_key(key.key_id, key.key_secret)
        assert valid is True
        assert returned_key is not None

    def test_A05_validate_wrong_secret_returns_false(self, sec):
        key = sec.generate_api_key("P1", "PartnerA")
        valid, _ = sec.validate_api_key(key.key_id, "wrong_secret")
        assert valid is False

    def test_A06_validate_unknown_key_id_returns_false(self, sec):
        valid, _ = sec.validate_api_key("sk_nonexistent", "any_secret")
        assert valid is False

    def test_A07_validate_inactive_key_returns_false(self, sec):
        key = sec.generate_api_key("P1", "PartnerA")
        key.is_active = False
        valid, _ = sec.validate_api_key(key.key_id, key.key_secret)
        assert valid is False

    def test_A08_rate_limit_allows_under_limit(self, sec):
        key = sec.generate_api_key("P1", "PartnerA", RateLimitTier.FREE)
        allowed, info = sec.check_rate_limit(key.key_id, key)
        assert allowed is True
        assert info["remaining"] >= 0

    def test_A09_rate_limit_blocks_when_exhausted(self, sec):
        key = sec.generate_api_key("P1", "PartnerA", RateLimitTier.FREE)
        # Simulate 100 requests (FREE tier limit)
        sec.request_history[key.key_id] = [datetime.utcnow()] * 100
        allowed, info = sec.check_rate_limit(key.key_id, key)
        assert allowed is False
        assert info["remaining"] == 0

    def test_A10_rotate_key_deactivates_old(self, sec):
        key = sec.generate_api_key("P1", "PartnerA")
        old_id = key.key_id
        sec.rotate_api_key(old_id)
        assert sec.api_keys[old_id].is_active is False
        assert sec.api_keys[old_id].is_rotated is True

    def test_A11_rotate_key_returns_new_key(self, sec):
        key = sec.generate_api_key("P1", "PartnerA")
        new_key = sec.rotate_api_key(key.key_id)
        assert new_key is not None
        assert new_key.key_id != key.key_id

    def test_A12_sign_and_verify_signature(self, sec):
        key = sec.generate_api_key("P1", "PartnerA")
        data = '{"amount": 100}'
        sig = sec.sign_request(key.key_secret, data)
        assert isinstance(sig, str)
        assert len(sig) == 64  # SHA-256 hex digest
        assert sec.verify_signature(key.key_secret, data, sig) is True


# ── TestRequestValidator ───────────────────────────────────────────────────────

class TestRequestValidator:

    @pytest.fixture
    def val(self):
        return RequestValidator()

    def test_B01_valid_valuation_request_passes(self, val):
        data = {"property_id": "PROP_01", "area_sqm": 150.0, "location": "Cairo"}
        ok, errors = val.validate_request("valuation", data)
        assert ok is True
        assert errors == []

    def test_B02_missing_required_field_fails(self, val):
        data = {"property_id": "PROP_01"}  # missing area_sqm and location
        ok, errors = val.validate_request("valuation", data)
        assert ok is False
        assert len(errors) >= 2

    def test_B03_wrong_type_fails(self, val):
        data = {"property_id": "PROP_01", "area_sqm": "not_a_number", "location": "Cairo"}
        ok, errors = val.validate_request("valuation", data)
        assert ok is False
        assert any("area_sqm" in e for e in errors)

    def test_B04_below_min_value_fails(self, val):
        data = {"property_id": "P1", "area_sqm": 5.0, "location": "Cairo"}  # min=10
        ok, errors = val.validate_request("valuation", data)
        assert ok is False
        assert any("area_sqm" in e for e in errors)

    def test_B05_above_max_value_fails(self, val):
        data = {"property_id": "P1", "area_sqm": 999_999.0, "location": "Cairo"}
        ok, errors = val.validate_request("valuation", data)
        assert ok is False
        assert any("area_sqm" in e for e in errors)

    def test_B06_unknown_endpoint_passes(self, val):
        ok, errors = val.validate_request("nonexistent_endpoint", {"any": "data"})
        assert ok is True
        assert errors == []

    def test_B07_allowed_values_rejects_invalid(self, val):
        data = {"property_type": "spaceship"}
        ok, errors = val.validate_request("search", data)
        assert ok is False
        assert any("property_type" in e for e in errors)

    def test_B08_sanitize_string_removes_null_bytes(self, val):
        dirty = "hello\x00world"
        clean = val.sanitize_string(dirty)
        assert "\x00" not in clean
        assert "hello" in clean and "world" in clean


# ── TestPerformanceOptimizer ───────────────────────────────────────────────────

class TestPerformanceOptimizer:

    @pytest.fixture
    def opt(self):
        return PerformanceOptimizer()

    def test_C01_cache_response_stores_data(self, opt):
        opt.cache_response("key1", {"result": 42}, "search")
        assert opt.count() == 1

    def test_C02_get_cached_response_returns_data(self, opt):
        payload = {"result": "ok"}
        opt.cache_response("key1", payload, "search")
        result = opt.get_cached_response("key1")
        assert result == payload

    def test_C03_get_cached_response_miss_returns_none(self, opt):
        result = opt.get_cached_response("does_not_exist")
        assert result is None

    def test_C04_compress_response_returns_bytes(self, opt):
        data = {"key": "value" * 100}
        compressed = opt.compress_response(data)
        assert isinstance(compressed, bytes)
        assert len(compressed) > 0

    def test_C05_compression_reduces_size_for_large_data(self, opt):
        import json
        data = {"key": "x" * 5000}
        compressed = opt.compress_response(data)
        original_size = len(json.dumps(data).encode())
        assert len(compressed) < original_size

    def test_C06_get_cache_statistics_returns_dict(self, opt):
        opt.cache_response("k1", {"a": 1}, "search")
        stats = opt.get_cache_statistics()
        assert stats["total_cached"] == 1
        assert "valid" in stats
        assert "expired" in stats


# ── TestErrorStandardizer ─────────────────────────────────────────────────────

class TestErrorStandardizer:

    @pytest.fixture
    def es(self):
        return ErrorStandardizer()

    def test_D01_create_error_returns_standard_error(self, es):
        err = es.create_error(ErrorCode.INVALID_REQUEST, "bad request", 400)
        assert err.http_status == 400
        assert err.error_code == ErrorCode.INVALID_REQUEST

    def test_D02_validation_error_status_400(self, es):
        err = es.handle_validation_error(["field required"])
        assert err.http_status == 400

    def test_D03_validation_error_includes_errors_list(self, es):
        errs = ["field1 missing", "field2 invalid"]
        err = es.handle_validation_error(errs)
        assert "validation_errors" in err.details
        assert len(err.details["validation_errors"]) == 2

    def test_D04_auth_error_status_401(self, es):
        err = es.handle_auth_error()
        assert err.http_status == 401
        assert err.error_code == ErrorCode.AUTHENTICATION_FAILED

    def test_D05_rate_limit_status_429(self, es):
        reset_time = datetime.utcnow() + timedelta(hours=1)
        err = es.handle_rate_limit(remaining=0, reset=reset_time)
        assert err.http_status == 429
        assert err.error_code == ErrorCode.RATE_LIMIT_EXCEEDED

    def test_D06_to_dict_has_error_key(self, es):
        err = es.handle_auth_error()
        d = err.to_dict()
        assert "error" in d
        assert "code" in d["error"]
        assert "message" in d["error"]

    def test_D07_error_code_in_dict_matches_enum_value(self, es):
        err = es.handle_validation_error(["x"])
        d = err.to_dict()
        assert d["error"]["code"] == "VALIDATION_ERROR"

    def test_D08_rate_limit_details_has_reset_at(self, es):
        reset_time = datetime.utcnow() + timedelta(hours=1)
        err = es.handle_rate_limit(remaining=5, reset=reset_time)
        assert "reset_at" in err.details


# ── TestIntegrationFramework ───────────────────────────────────────────────────

class TestIntegrationFramework:

    @pytest.fixture
    def fw(self):
        return IntegrationFramework()

    def test_E01_register_integration_stores_it(self, fw):
        fw.register_integration("INT_1", "BankAPI", "National Bank")
        assert "INT_1" in fw.integrations

    def test_E02_registered_integration_is_active(self, fw):
        integ = fw.register_integration("INT_1", "BankAPI", "National Bank")
        assert integ.is_active is True

    def test_E03_emit_event_adds_to_queue(self, fw):
        fw.emit_event(IntegrationEvent.VALUATION_COMPLETED, {"id": "V1"})
        assert len(fw.event_queue) == 1

    def test_E04_emit_triggers_subscribed_integration(self, fw):
        integ = fw.register_integration(
            "INT_1", "BankAPI", "NB",
            events=[IntegrationEvent.VALUATION_COMPLETED],
        )
        fw.emit_event(IntegrationEvent.VALUATION_COMPLETED, {"id": "V1"})
        assert integ.success_count == 1

    def test_E05_emit_does_not_trigger_unsubscribed_integration(self, fw):
        integ = fw.register_integration(
            "INT_1", "BankAPI", "NB",
            events=[IntegrationEvent.REPORT_GENERATED],
        )
        fw.emit_event(IntegrationEvent.VALUATION_COMPLETED, {"id": "V1"})
        assert integ.success_count == 0

    def test_E06_emit_returns_trigger_count(self, fw):
        fw.register_integration("I1", "A", "P", events=[IntegrationEvent.SEARCH_COMPLETED])
        fw.register_integration("I2", "B", "Q", events=[IntegrationEvent.SEARCH_COMPLETED])
        count = fw.emit_event(IntegrationEvent.SEARCH_COMPLETED, {})
        assert count == 2

    def test_E07_integration_to_dict_includes_events(self, fw):
        integ = fw.register_integration(
            "INT_1", "BankAPI", "NB",
            events=[IntegrationEvent.VALUATION_COMPLETED, IntegrationEvent.ERROR_OCCURRED],
        )
        d = integ.to_dict()
        assert "subscribed_events" in d
        assert len(d["subscribed_events"]) == 2

    def test_E08_inactive_integration_not_triggered(self, fw):
        integ = fw.register_integration(
            "INT_1", "BankAPI", "NB",
            events=[IntegrationEvent.VALUATION_COMPLETED],
        )
        fw.deactivate_integration("INT_1")
        fw.emit_event(IntegrationEvent.VALUATION_COMPLETED, {})
        assert integ.success_count == 0

    def test_E09_statistics_reflects_registrations(self, fw):
        fw.register_integration("I1", "A", "P")
        fw.register_integration("I2", "B", "Q")
        stats = fw.get_integration_statistics()
        assert stats["total_integrations"] == 2
        assert stats["active_integrations"] == 2

    def test_E10_multiple_events_accumulate_in_queue(self, fw):
        for i in range(5):
            fw.emit_event(IntegrationEvent.PROPERTY_CREATED, {"id": str(i)})
        assert len(fw.event_queue) == 5
