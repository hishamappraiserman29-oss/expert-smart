"""
test_api_hardening.py — API Hardening Tests

Covers:
  A. RetryPolicy / retry decorator
  B. CircuitBreaker
  C. RequestDeduplicator (idempotency)
  D. ResponseFormatter (standard envelope)
  E. Error classes (APIError hierarchy)
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.resilience import (
    RetryPolicy, RetryStrategy, CircuitBreaker, CircuitBreakerState,
    TimeoutHandler, retry,
)
from api.request_deduplication import RequestDeduplicator, IdempotencyKey
from api.response_formatter import ResponseFormatter, ResponseStatus, StandardResponse
from api.error_handler import (
    APIError, ErrorCode, ValidationError, NotFoundError,
    OperationTimeoutError, TimeoutError, DatabaseError,
)


# ===========================================================================
# A. RetryPolicy / retry decorator
# ===========================================================================

class TestRetryLogic:

    def test_A01_success_first_attempt_no_retry(self):
        call_count = [0]

        def func():
            call_count[0] += 1
            return "ok"

        result = retry(RetryPolicy(max_attempts=3))(func)()
        assert result == "ok"
        assert call_count[0] == 1

    def test_A02_retries_and_succeeds(self):
        call_count = [0]

        def func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ConnectionError("transient")
            return "recovered"

        policy  = RetryPolicy(max_attempts=3, initial_delay=0.01, jitter=False)
        result  = retry(policy)(func)()
        assert result == "recovered"
        assert call_count[0] == 3

    def test_A03_raises_after_max_attempts(self):
        def always_fails():
            raise ConnectionError("permanent")

        policy = RetryPolicy(max_attempts=2, initial_delay=0.01, jitter=False)
        with pytest.raises(ConnectionError):
            retry(policy)(always_fails)()

    def test_A04_get_delay_exponential(self):
        p = RetryPolicy(
            initial_delay=1.0,
            backoff_factor=2.0,
            strategy=RetryStrategy.EXPONENTIAL,
            jitter=False,
        )
        assert p.get_delay(1) == 1.0
        assert p.get_delay(2) == 2.0
        assert p.get_delay(3) == 4.0

    def test_A05_get_delay_linear(self):
        p = RetryPolicy(
            initial_delay=1.0,
            strategy=RetryStrategy.LINEAR,
            jitter=False,
        )
        assert p.get_delay(1) == 1.0
        assert p.get_delay(2) == 2.0
        assert p.get_delay(3) == 3.0

    def test_A06_get_delay_fixed(self):
        p = RetryPolicy(initial_delay=0.5, strategy=RetryStrategy.FIXED, jitter=False)
        assert p.get_delay(1) == 0.5
        assert p.get_delay(5) == 0.5

    def test_A07_delay_capped_at_max(self):
        p = RetryPolicy(initial_delay=100.0, max_delay=5.0, jitter=False)
        assert p.get_delay(1) <= 5.0

    def test_A08_retry_preserves_function_name(self):
        def my_function():
            return 1

        decorated = retry(RetryPolicy())(my_function)
        assert decorated.__name__ == "my_function"


# ===========================================================================
# B. CircuitBreaker
# ===========================================================================

class TestCircuitBreaker:

    def test_B01_starts_closed(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitBreakerState.CLOSED

    def test_B02_successful_call_stays_closed(self):
        cb = CircuitBreaker(failure_threshold=3)
        result = cb.call(lambda: "ok")
        assert result == "ok"
        assert cb.state == CircuitBreakerState.CLOSED

    def test_B03_opens_after_threshold_failures(self):
        cb = CircuitBreaker(failure_threshold=2)
        for _ in range(2):
            with pytest.raises(Exception):
                cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
        assert cb.state == CircuitBreakerState.OPEN

    def test_B04_open_circuit_rejects_immediately(self):
        cb = CircuitBreaker(failure_threshold=1)
        with pytest.raises(Exception):
            cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
        assert cb.state == CircuitBreakerState.OPEN
        with pytest.raises(Exception, match="OPEN"):
            cb.call(lambda: "should not run")

    def test_B05_failure_count_increments(self):
        cb = CircuitBreaker(failure_threshold=10)
        for _ in range(3):
            with pytest.raises(Exception):
                cb.call(lambda: (_ for _ in ()).throw(Exception("x")))
        assert cb.failure_count == 3

    def test_B06_success_resets_failure_count(self):
        cb = CircuitBreaker(failure_threshold=5)
        for _ in range(2):
            with pytest.raises(Exception):
                cb.call(lambda: (_ for _ in ()).throw(Exception("x")))
        cb.call(lambda: "ok")
        assert cb.failure_count == 0


# ===========================================================================
# C. RequestDeduplicator
# ===========================================================================

class TestRequestDeduplication:

    def test_C01_new_request_returns_true(self):
        dedup = RequestDeduplicator()
        assert dedup.register_request("k1", {}) is True

    def test_C02_duplicate_returns_false(self):
        dedup = RequestDeduplicator()
        dedup.register_request("k1", {})
        assert dedup.register_request("k1", {}) is False

    def test_C03_different_keys_are_independent(self):
        dedup = RequestDeduplicator()
        assert dedup.register_request("k1", {}) is True
        assert dedup.register_request("k2", {}) is True

    def test_C04_store_and_retrieve_response(self):
        dedup = RequestDeduplicator()
        dedup.register_request("k1", {})
        dedup.store_response("k1", {"value": 42}, 200)
        cached = dedup.get_cached_response("k1")
        assert cached is not None
        assert cached[0] == {"value": 42}
        assert cached[1] == 200

    def test_C05_no_response_before_store_returns_none(self):
        dedup = RequestDeduplicator()
        dedup.register_request("k1", {})
        assert dedup.get_cached_response("k1") is None

    def test_C06_unknown_key_returns_none(self):
        dedup = RequestDeduplicator()
        assert dedup.get_cached_response("nonexistent") is None

    def test_C07_idempotency_key_to_dict(self):
        key = IdempotencyKey("test-key", {"a": 1})
        d   = key.to_dict()
        assert d["key"] == "test-key"
        assert "created_at" in d
        assert "expired" in d


# ===========================================================================
# D. ResponseFormatter
# ===========================================================================

class TestResponseFormatter:

    def test_D01_success_has_correct_status(self):
        r = ResponseFormatter.success(data={"x": 1})
        assert r.to_dict()["status"] == "success"

    def test_D02_success_contains_data(self):
        r = ResponseFormatter.success(data={"value": 999})
        assert r.to_dict()["data"]["value"] == 999

    def test_D03_success_has_timestamp(self):
        r = ResponseFormatter.success()
        assert "timestamp" in r.to_dict()

    def test_D04_error_has_correct_status(self):
        r = ResponseFormatter.error("Something went wrong")
        assert r.to_dict()["status"] == "error"

    def test_D05_error_contains_message(self):
        r = ResponseFormatter.error("bad input")
        assert "bad input" in r.to_dict()["message"]

    def test_D06_error_with_error_list(self):
        r = ResponseFormatter.error("fail", errors=[{"field": "x", "error": "required"}])
        assert len(r.to_dict()["errors"]) == 1

    def test_D07_processing_has_request_id_in_metadata(self):
        r = ResponseFormatter.processing("req-123")
        d = r.to_dict()
        assert d["status"] == "processing"
        assert d["metadata"]["request_id"] == "req-123"

    def test_D08_partial_has_failed_count(self):
        r = ResponseFormatter.partial(data=[], failed_count=3)
        assert r.to_dict()["metadata"]["failed_count"] == 3

    def test_D09_to_json_is_valid_json(self):
        import json
        r = ResponseFormatter.success(data={"k": "v"})
        parsed = json.loads(r.to_json())
        assert parsed["status"] == "success"


# ===========================================================================
# E. Error classes
# ===========================================================================

class TestErrorHandling:

    def test_E01_validation_error_code(self):
        e = ValidationError("area_sqm", "Must be positive")
        assert e.code == ErrorCode.VALIDATION_ERROR

    def test_E02_validation_error_status_400(self):
        assert ValidationError("x", "y").status_code == 400

    def test_E03_validation_error_details_have_field(self):
        e = ValidationError("area_sqm", "bad")
        assert e.details["field"] == "area_sqm"

    def test_E04_not_found_error_code(self):
        e = NotFoundError("Property", "123")
        assert e.code == ErrorCode.NOT_FOUND

    def test_E05_not_found_error_status_404(self):
        assert NotFoundError("X", "1").status_code == 404

    def test_E06_operation_timeout_error_status_504(self):
        e = OperationTimeoutError("valuation", 30.0)
        assert e.status_code == 504
        assert e.code == ErrorCode.TIMEOUT

    def test_E07_timeout_alias_is_operation_timeout(self):
        assert TimeoutError is OperationTimeoutError

    def test_E08_database_error_status_500(self):
        e = DatabaseError("connection refused")
        assert e.status_code == 500
        assert e.code == ErrorCode.DATABASE_ERROR

    def test_E09_api_error_to_dict_keys(self):
        e = NotFoundError("Batch", "b42")
        d = e.to_dict()
        for key in ("code", "message", "details"):
            assert key in d

    def test_E10_all_errors_are_api_error_subclasses(self):
        assert issubclass(ValidationError,        APIError)
        assert issubclass(NotFoundError,          APIError)
        assert issubclass(OperationTimeoutError,  APIError)
        assert issubclass(DatabaseError,          APIError)
