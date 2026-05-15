"""
test_ph5_deployment.py — PH.5 Documentation & Deployment Tests

Covers:
  A. AppConfig / ConfigValidator — env loading, defaults, validation rules
  B. HealthChecker               — register, run, aggregate, timeout, factories
  C. StartupValidator            — built-in checks, report, ok_to_start logic
"""

from __future__ import annotations

import os
import sys
import time
import socket
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from deployment.config import AppConfig, ConfigValidator, load_config
from deployment.health import (
    HealthChecker, HealthStatus, ComponentHealth,
    disk_space_check, directory_writable_check, import_check,
)
from deployment.startup import (
    StartupValidator, StartupCheck, StartupReport, CheckSeverity,
)


# ===========================================================================
# A. AppConfig + ConfigValidator
# ===========================================================================

class TestAppConfig:

    def test_A01_defaults_are_sane(self):
        cfg = AppConfig()
        assert cfg.port == 5000
        assert cfg.debug is False
        assert cfg.workers == 4
        assert cfg.log_level == "INFO"
        assert cfg.cache_max_size == 512

    def test_A02_to_dict_redacts_secret_key(self):
        cfg = AppConfig(secret_key="s3cr3t!")
        d = cfg.to_dict()
        assert d["secret_key"] == "***"
        assert d["port"] == 5000

    def test_A03_is_production_flag(self):
        dev = AppConfig(debug=True, secret_key="x")
        assert not dev.is_production
        prod = AppConfig(debug=False, secret_key="s3cr3t!")
        assert prod.is_production

    def test_A04_load_config_from_env(self):
        with patch.dict(os.environ, {
            "EXPERT_SMART_PORT": "8080",
            "EXPERT_SMART_DEBUG": "true",
            "EXPERT_SMART_WORKERS": "8",
            "EXPERT_SMART_LOG_LEVEL": "DEBUG",
        }):
            cfg = load_config()
        assert cfg.port == 8080
        assert cfg.debug is True
        assert cfg.workers == 8
        assert cfg.log_level == "DEBUG"

    def test_A05_env_list_parsing(self):
        with patch.dict(os.environ, {
            "EXPERT_SMART_ALLOWED_ORIGINS": "https://app.com,https://admin.com"
        }):
            cfg = load_config()
        assert "https://app.com" in cfg.allowed_origins
        assert "https://admin.com" in cfg.allowed_origins

    def test_A06_validator_passes_valid_config(self):
        cfg = AppConfig(port=8080, workers=2, log_level="WARNING",
                        cache_max_size=100, rate_limit_requests=30)
        assert ConfigValidator.is_valid(cfg)

    def test_A07_validator_catches_bad_port(self):
        cfg = AppConfig(port=0)
        issues = ConfigValidator.validate(cfg)
        field_names = [f for f, _ in issues]
        assert "port" in field_names

    def test_A08_validator_catches_bad_log_level(self):
        cfg = AppConfig(log_level="VERBOSE")
        issues = ConfigValidator.validate(cfg)
        assert any(f == "log_level" for f, _ in issues)

    def test_A09_validator_catches_multiple_errors(self):
        cfg = AppConfig(port=99999, workers=0, cache_max_size=-1)
        issues = ConfigValidator.validate(cfg)
        assert len(issues) >= 3

    def test_A10_env_bool_parsing(self):
        for val in ("1", "true", "yes", "on"):
            with patch.dict(os.environ, {"EXPERT_SMART_DEBUG": val}):
                assert load_config().debug is True
        for val in ("0", "false", "no", "off"):
            with patch.dict(os.environ, {"EXPERT_SMART_DEBUG": val}):
                assert load_config().debug is False


# ===========================================================================
# B. HealthChecker
# ===========================================================================

class TestHealthChecker:

    def test_B01_register_and_run_healthy(self):
        hc = HealthChecker()

        @hc.register("db")
        def _check() -> ComponentHealth:
            return ComponentHealth.healthy("db", detail="connected")

        result = hc.run_all()
        assert result["status"] == HealthStatus.HEALTHY
        assert result["checks"]["db"]["status"] == HealthStatus.HEALTHY

    def test_B02_degraded_propagates_to_overall(self):
        hc = HealthChecker()
        hc.register_fn("cache", lambda: ComponentHealth.healthy("cache"))
        hc.register_fn("mcp", lambda: ComponentHealth.degraded("mcp", detail="slow"))
        result = hc.run_all()
        assert result["status"] == HealthStatus.DEGRADED

    def test_B03_unhealthy_overrides_degraded(self):
        hc = HealthChecker()
        hc.register_fn("c1", lambda: ComponentHealth.degraded("c1"))
        hc.register_fn("c2", lambda: ComponentHealth.unhealthy("c2", error="down"))
        result = hc.run_all()
        assert result["status"] == HealthStatus.UNHEALTHY

    def test_B04_exception_becomes_unhealthy(self):
        hc = HealthChecker()

        def bad_check() -> ComponentHealth:
            raise RuntimeError("connection refused")

        hc.register_fn("broken", bad_check)
        result = hc.run_all()
        assert result["checks"]["broken"]["status"] == HealthStatus.UNHEALTHY
        assert "connection refused" in result["checks"]["broken"]["error"]

    def test_B05_timeout_returns_unhealthy(self):
        hc = HealthChecker(timeout_seconds=0.05)

        def slow_check() -> ComponentHealth:
            time.sleep(1.0)
            return ComponentHealth.healthy("slow")

        hc.register_fn("slow", slow_check)
        ch = hc.run_check("slow")
        assert ch.status == HealthStatus.UNHEALTHY
        assert "Timed out" in ch.error

    def test_B06_summary_counts(self):
        hc = HealthChecker()
        hc.register_fn("a", lambda: ComponentHealth.healthy("a"))
        hc.register_fn("b", lambda: ComponentHealth.degraded("b"))
        hc.register_fn("c", lambda: ComponentHealth.unhealthy("c", error="err"))
        result = hc.run_all()
        assert result["summary"]["healthy"] == 1
        assert result["summary"]["degraded"] == 1
        assert result["summary"]["unhealthy"] == 1
        assert result["summary"]["total"] == 3

    def test_B07_component_health_to_dict(self):
        ch = ComponentHealth.healthy("api", latency_ms=2.5, detail="OK")
        d = ch.to_dict()
        assert d["name"] == "api"
        assert d["latency_ms"] == 2.5
        assert d["error"] is None

    def test_B08_unregister(self):
        hc = HealthChecker()
        hc.register_fn("tmp", lambda: ComponentHealth.healthy("tmp"))
        assert "tmp" in hc.registered_names()
        hc.unregister("tmp")
        assert "tmp" not in hc.registered_names()

    def test_B09_disk_space_check_runs(self):
        check_fn = disk_space_check(path=".")
        result = check_fn()
        assert result.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
        assert "%" in result.detail

    def test_B10_import_check_healthy(self):
        check_fn = import_check("json")
        result = check_fn()
        assert result.status == HealthStatus.HEALTHY

    def test_B11_import_check_unhealthy(self):
        check_fn = import_check("nonexistent_module_xyz_abc")
        result = check_fn()
        assert result.status == HealthStatus.UNHEALTHY

    def test_B12_directory_writable_check(self, tmp_path):
        check_fn = directory_writable_check(str(tmp_path))
        result = check_fn()
        assert result.status == HealthStatus.HEALTHY

        check_bad = directory_writable_check("/nonexistent_path_xyz")
        result_bad = check_bad()
        assert result_bad.status == HealthStatus.UNHEALTHY


# ===========================================================================
# C. StartupValidator
# ===========================================================================

class TestStartupValidator:

    def test_C01_all_pass_is_ok_to_start(self):
        v = StartupValidator()
        v.add_check("always_pass", lambda: (True, "great"), CheckSeverity.FAIL)
        report = v.run()
        assert report.ok_to_start is True
        assert report.pass_count == 1

    def test_C02_fail_check_blocks_startup(self):
        v = StartupValidator()
        v.add_check("must_fail", lambda: (False, "broken"), CheckSeverity.FAIL)
        report = v.run()
        assert report.ok_to_start is False
        assert report.fail_count == 1

    def test_C03_warn_check_does_not_block(self):
        v = StartupValidator()
        v.add_check("warn_only", lambda: (False, "sub-optimal"), CheckSeverity.WARN)
        report = v.run()
        assert report.ok_to_start is True   # warn never blocks
        assert report.warn_count == 1

    def test_C04_all_checks_run_even_if_one_fails(self):
        v = StartupValidator()
        v.add_check("fail1", lambda: (False, "f1"), CheckSeverity.FAIL)
        v.add_check("fail2", lambda: (False, "f2"), CheckSeverity.FAIL)
        v.add_check("pass1", lambda: (True, "ok"), CheckSeverity.FAIL)
        report = v.run()
        assert len(report.checks) == 3
        assert report.fail_count == 2
        assert report.pass_count == 1

    def test_C05_exception_in_check_is_caught(self):
        v = StartupValidator()
        def bad():
            raise ValueError("crash")
        v.add_check("boom", bad, CheckSeverity.FAIL)
        report = v.run()
        assert report.ok_to_start is False
        assert "crash" in report.checks[0].message

    def test_C06_python_version_check_passes(self):
        v = StartupValidator()
        v.add_python_version_check(3, 0)    # always true on Python 3
        report = v.run()
        assert report.checks[0].passed is True

    def test_C07_python_version_check_fails(self):
        v = StartupValidator()
        v.add_python_version_check(99, 99)  # impossibly high
        report = v.run()
        assert report.checks[0].passed is False

    def test_C08_directory_check_existing(self, tmp_path):
        v = StartupValidator()
        v.add_directory_check(str(tmp_path))
        report = v.run()
        assert report.checks[0].passed is True

    def test_C09_directory_check_creates_missing(self, tmp_path):
        new_dir = str(tmp_path / "auto_created")
        v = StartupValidator()
        v.add_directory_check(new_dir, create=True)
        report = v.run()
        assert report.checks[0].passed is True
        assert Path(new_dir).exists()

    def test_C10_import_check_pass_and_fail(self):
        v = StartupValidator()
        v.add_import_check("os", CheckSeverity.FAIL)
        v.add_import_check("nonexistent_xyz_module", CheckSeverity.WARN)
        report = v.run()
        assert report.checks[0].passed is True
        assert report.checks[1].passed is False
        assert report.ok_to_start is True   # second is WARN

    def test_C11_report_to_dict(self):
        v = StartupValidator()
        v.add_check("x", lambda: (True, "ok"), CheckSeverity.FAIL)
        report = v.run()
        d = report.to_dict()
        assert d["ok_to_start"] is True
        assert len(d["checks"]) == 1
        assert d["checks"][0]["passed"] is True

    def test_C12_format_summary(self):
        v = StartupValidator()
        v.add_check("passing", lambda: (True, "all good"), CheckSeverity.FAIL)
        v.add_check("failing", lambda: (False, "bad"), CheckSeverity.WARN)
        report = v.run()
        summary = report.format_summary()
        assert "WARN" in summary
        assert "passing" in summary
        assert "failing" in summary
