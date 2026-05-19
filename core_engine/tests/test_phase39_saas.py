"""
test_phase39_saas.py — Phase 39: SaaS Readiness Tests

TestHealthCheckMonitor  A01–A12
TestLoadTester          B01–B10
TestSaaSReadinessChecker C01–C08
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.health_check import HealthCheckMonitor
from scripts.loadtest import LoadTester
from scripts.saas_readiness_check import ReadinessCheck, ReadinessReport, SaaSReadinessChecker


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def monitor() -> HealthCheckMonitor:
    return HealthCheckMonitor(api_url="http://localhost:19999", check_interval=60)


@pytest.fixture()
def tester() -> LoadTester:
    return LoadTester(api_url="http://localhost:19999", num_workers=2)


@pytest.fixture()
def checker() -> SaaSReadinessChecker:
    return SaaSReadinessChecker()


# ── TestHealthCheckMonitor ────────────────────────────────────────────────────

class TestHealthCheckMonitor:

    def test_A01_init_stores_api_url(self, monitor: HealthCheckMonitor) -> None:
        assert monitor.api_url == "http://localhost:19999"

    def test_A02_init_stores_check_interval(self, monitor: HealthCheckMonitor) -> None:
        assert monitor.check_interval == 60

    def test_A03_init_empty_history(self, monitor: HealthCheckMonitor) -> None:
        assert monitor.health_history == []

    def test_A04_check_disk_returns_dict(self, monitor: HealthCheckMonitor) -> None:
        result = monitor.check_disk_space()
        assert isinstance(result, dict)

    def test_A05_check_disk_has_service_key(self, monitor: HealthCheckMonitor) -> None:
        result = monitor.check_disk_space()
        assert result["service"] == "disk"

    def test_A06_check_disk_has_valid_status(self, monitor: HealthCheckMonitor) -> None:
        result = monitor.check_disk_space()
        assert result["status"] in {"healthy", "warning", "critical", "error"}

    def test_A07_check_disk_has_timestamp(self, monitor: HealthCheckMonitor) -> None:
        result = monitor.check_disk_space()
        assert "timestamp" in result

    def test_A08_check_api_offline_returns_error(self, monitor: HealthCheckMonitor) -> None:
        result = monitor.check_api_health()
        assert result["service"] == "api"
        assert result["status"] in {"error", "unhealthy"}

    def test_A09_check_api_offline_no_raise(self, monitor: HealthCheckMonitor) -> None:
        result = monitor.check_api_health()
        assert isinstance(result, dict)

    def test_A10_run_health_check_returns_structure(self, monitor: HealthCheckMonitor) -> None:
        result = monitor.run_health_check()
        assert "overall_status" in result
        assert "timestamp" in result
        assert "checks" in result

    def test_A11_run_health_check_appends_history(self, monitor: HealthCheckMonitor) -> None:
        monitor.run_health_check()
        assert len(monitor.health_history) == 1

    def test_A12_run_health_check_has_four_check_keys(self, monitor: HealthCheckMonitor) -> None:
        result = monitor.run_health_check()
        assert set(result["checks"].keys()) == {"api", "database", "redis", "disk"}


# ── TestLoadTester ────────────────────────────────────────────────────────────

class TestLoadTester:

    def test_B01_init_stores_api_url(self, tester: LoadTester) -> None:
        assert tester.api_url == "http://localhost:19999"

    def test_B02_init_stores_num_workers(self, tester: LoadTester) -> None:
        assert tester.num_workers == 2

    def test_B03_init_empty_results(self, tester: LoadTester) -> None:
        assert tester.results == []

    def test_B04_test_endpoint_offline_returns_dict(self, tester: LoadTester) -> None:
        result = tester.test_endpoint("/api/health")
        assert isinstance(result, dict)

    def test_B05_test_endpoint_offline_not_success(self, tester: LoadTester) -> None:
        result = tester.test_endpoint("/api/health")
        assert result["success"] is False

    def test_B06_test_endpoint_offline_has_endpoint(self, tester: LoadTester) -> None:
        result = tester.test_endpoint("/api/health")
        assert result["endpoint"] == "/api/health"

    def test_B07_run_load_test_returns_summary(self, tester: LoadTester) -> None:
        result = tester.run_load_test("/api/health", num_requests=3)
        assert isinstance(result, dict)

    def test_B08_run_load_test_has_all_metric_keys(self, tester: LoadTester) -> None:
        result = tester.run_load_test("/api/health", num_requests=3)
        required = {
            "endpoint", "total_requests", "successful", "failed",
            "success_rate", "avg_response_time", "min_response_time",
            "max_response_time", "p95_response_time",
        }
        assert required.issubset(result.keys())

    def test_B09_run_load_test_total_requests_matches(self, tester: LoadTester) -> None:
        result = tester.run_load_test("/api/health", num_requests=5)
        assert result["total_requests"] == 5

    def test_B10_run_load_test_appends_results(self, tester: LoadTester) -> None:
        tester.run_load_test("/api/health", num_requests=3)
        assert len(tester.results) == 1


# ── TestSaaSReadinessChecker ──────────────────────────────────────────────────

class TestSaaSReadinessChecker:

    # env config

    def test_C01_env_config_passes_when_all_required_present(self, checker: SaaSReadinessChecker) -> None:
        env = {"DATABASE_URL": "postgres://...", "FLASK_ENV": "production", "SECRET_KEY": "abc"}
        result = checker.check_env_config(env)
        assert result.passed is True
        assert result.issues == []

    def test_C02_env_config_fails_when_missing_required(self, checker: SaaSReadinessChecker) -> None:
        result = checker.check_env_config({"FLASK_ENV": "production"})
        assert result.passed is False
        assert any("DATABASE_URL" in issue for issue in result.issues)

    def test_C03_env_config_reports_missing_recommended(self, checker: SaaSReadinessChecker) -> None:
        env = {"DATABASE_URL": "x", "FLASK_ENV": "prod", "SECRET_KEY": "s"}
        result = checker.check_env_config(env)
        assert len(result.details["missing_recommended"]) > 0

    # server config

    def test_C04_server_config_passes_valid(self, checker: SaaSReadinessChecker) -> None:
        cfg = {"workers": 4, "max_requests": 1000, "timeout": 60}
        result = checker.check_server_config(cfg)
        assert result.passed is True

    def test_C05_server_config_fails_low_workers(self, checker: SaaSReadinessChecker) -> None:
        cfg = {"workers": 1, "max_requests": 500, "timeout": 60}
        result = checker.check_server_config(cfg)
        assert result.passed is False

    # security config

    def test_C06_security_config_passes_all_enabled(self, checker: SaaSReadinessChecker) -> None:
        cfg = {"https_enabled": True, "rate_limiting_enabled": True, "debug_mode": False}
        result = checker.check_security_config(cfg)
        assert result.passed is True

    def test_C07_security_config_fails_debug_mode_on(self, checker: SaaSReadinessChecker) -> None:
        cfg = {"https_enabled": True, "rate_limiting_enabled": True, "debug_mode": True}
        result = checker.check_security_config(cfg)
        assert result.passed is False

    # scaling config & generate_report

    def test_C08_generate_report_ready_when_all_pass(self, checker: SaaSReadinessChecker) -> None:
        env = {"DATABASE_URL": "x", "FLASK_ENV": "prod", "SECRET_KEY": "s"}
        server = {"workers": 4, "max_requests": 500, "timeout": 60}
        security = {"https_enabled": True, "rate_limiting_enabled": True, "debug_mode": False}
        scaling = {"min_replicas": 2, "max_replicas": 5}
        report = checker.generate_report(env, server, security, scaling)
        assert isinstance(report, ReadinessReport)
        assert report.ready is True
        assert report.passed_count == 4
        assert report.failed_count == 0

    def test_C09_generate_report_not_ready_when_any_fail(self, checker: SaaSReadinessChecker) -> None:
        env: Dict[str, str] = {}  # all required missing
        server = {"workers": 4, "max_requests": 500, "timeout": 60}
        security = {"https_enabled": True, "rate_limiting_enabled": True, "debug_mode": False}
        scaling = {"min_replicas": 2, "max_replicas": 5}
        report = checker.generate_report(env, server, security, scaling)
        assert report.ready is False

    def test_C10_readiness_check_to_dict(self, checker: SaaSReadinessChecker) -> None:
        env = {"DATABASE_URL": "x", "FLASK_ENV": "prod", "SECRET_KEY": "s"}
        result = checker.check_env_config(env)
        d = result.to_dict()
        assert set(d.keys()) == {"name", "passed", "issues", "details"}

    def test_C11_readiness_report_to_dict(self, checker: SaaSReadinessChecker) -> None:
        env = {"DATABASE_URL": "x", "FLASK_ENV": "prod", "SECRET_KEY": "s"}
        server = {"workers": 4, "max_requests": 500, "timeout": 60}
        security = {"https_enabled": True, "rate_limiting_enabled": True, "debug_mode": False}
        scaling = {"min_replicas": 2, "max_replicas": 5}
        report = checker.generate_report(env, server, security, scaling)
        d = report.to_dict()
        assert "ready" in d and "passed" in d and "failed" in d and "total" in d and "checks" in d

    def test_C12_scaling_config_fails_when_min_less_than_2(self, checker: SaaSReadinessChecker) -> None:
        result = checker.check_scaling_config({"min_replicas": 1, "max_replicas": 5})
        assert result.passed is False

    def test_C13_scaling_config_fails_when_max_not_greater_than_min(self, checker: SaaSReadinessChecker) -> None:
        result = checker.check_scaling_config({"min_replicas": 2, "max_replicas": 2})
        assert result.passed is False

    def test_C14_scaling_config_passes_valid(self, checker: SaaSReadinessChecker) -> None:
        result = checker.check_scaling_config({"min_replicas": 2, "max_replicas": 10})
        assert result.passed is True
