"""
deployment/ — PH.5 Documentation & Deployment package.

Modules:
    config   — environment-driven configuration with validation
    health   — component health-check registry + aggregator
    startup  — pre-flight validation before server start
"""

from .config import AppConfig, ConfigValidator, load_config
from .health import HealthChecker, HealthStatus, ComponentHealth
from .startup import StartupValidator, StartupCheck, StartupReport

__all__ = [
    "AppConfig",
    "ConfigValidator",
    "load_config",
    "HealthChecker",
    "HealthStatus",
    "ComponentHealth",
    "StartupValidator",
    "StartupCheck",
    "StartupReport",
]
