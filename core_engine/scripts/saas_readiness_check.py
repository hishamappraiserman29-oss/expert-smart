"""
saas_readiness_check.py — SaaS Deployment Readiness Checker (Phase 39)

Validates environment configuration, resource settings, and deployment
requirements for production SaaS readiness without requiring live services.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ReadinessCheck:
    name: str
    passed: bool
    issues: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "issues": self.issues,
            "details": self.details,
        }


@dataclass
class ReadinessReport:
    ready: bool
    checks: List[ReadinessCheck]
    generated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ready": self.ready,
            "passed": self.passed_count,
            "failed": self.failed_count,
            "total": len(self.checks),
            "generated_at": self.generated_at.isoformat(),
            "checks": [c.to_dict() for c in self.checks],
        }


class SaaSReadinessChecker:
    """Validate deployment configuration for production SaaS readiness."""

    REQUIRED_ENV_VARS = [
        "DATABASE_URL",
        "FLASK_ENV",
        "SECRET_KEY",
    ]

    RECOMMENDED_ENV_VARS = [
        "REDIS_URL",
        "OLLAMA_HOST",
        "QDRANT_URL",
    ]

    def check_env_config(self, env: Dict[str, str]) -> ReadinessCheck:
        missing = [v for v in self.REQUIRED_ENV_VARS if v not in env]
        missing_rec = [v for v in self.RECOMMENDED_ENV_VARS if v not in env]
        issues: List[str] = [f"Missing required env var: {v}" for v in missing]
        details: Dict[str, Any] = {
            "required_present": len(self.REQUIRED_ENV_VARS) - len(missing),
            "required_total": len(self.REQUIRED_ENV_VARS),
            "missing_recommended": missing_rec,
        }
        return ReadinessCheck(
            name="environment_config",
            passed=len(missing) == 0,
            issues=issues,
            details=details,
        )

    def check_server_config(self, config: Dict[str, Any]) -> ReadinessCheck:
        issues: List[str] = []
        workers = config.get("workers", 0)
        max_requests = config.get("max_requests", 0)
        timeout = config.get("timeout", 0)

        if workers < 2:
            issues.append(f"workers={workers} should be >= 2 for production")
        if max_requests < 100:
            issues.append(f"max_requests={max_requests} should be >= 100")
        if timeout < 30:
            issues.append(f"timeout={timeout}s should be >= 30s")

        return ReadinessCheck(
            name="server_config",
            passed=len(issues) == 0,
            issues=issues,
            details={"workers": workers, "max_requests": max_requests, "timeout": timeout},
        )

    def check_security_config(self, config: Dict[str, Any]) -> ReadinessCheck:
        issues: List[str] = []
        if not config.get("https_enabled", False):
            issues.append("HTTPS is not enabled")
        if not config.get("rate_limiting_enabled", False):
            issues.append("Rate limiting is not configured")
        if config.get("debug_mode", True):
            issues.append("debug_mode must be False in production")
        return ReadinessCheck(
            name="security_config",
            passed=len(issues) == 0,
            issues=issues,
            details=config,
        )

    def check_scaling_config(self, config: Dict[str, Any]) -> ReadinessCheck:
        issues: List[str] = []
        min_replicas = config.get("min_replicas", 0)
        max_replicas = config.get("max_replicas", 0)

        if min_replicas < 2:
            issues.append(f"min_replicas={min_replicas} should be >= 2 for HA")
        if max_replicas <= min_replicas:
            issues.append("max_replicas must be greater than min_replicas")

        return ReadinessCheck(
            name="scaling_config",
            passed=len(issues) == 0,
            issues=issues,
            details={"min_replicas": min_replicas, "max_replicas": max_replicas},
        )

    def generate_report(
        self,
        env: Dict[str, str],
        server_config: Dict[str, Any],
        security_config: Dict[str, Any],
        scaling_config: Dict[str, Any],
    ) -> ReadinessReport:
        checks = [
            self.check_env_config(env),
            self.check_server_config(server_config),
            self.check_security_config(security_config),
            self.check_scaling_config(scaling_config),
        ]
        ready = all(c.passed for c in checks)
        report = ReadinessReport(ready=ready, checks=checks)
        logger.info(
            "SaaS readiness report: %s (%d/%d checks passed)",
            "READY" if ready else "NOT READY",
            report.passed_count,
            len(checks),
        )
        return report


saas_readiness_checker = SaaSReadinessChecker()
