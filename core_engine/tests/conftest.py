"""Pytest configuration — disable rate limiting and audit logging by default."""
import os
import pytest


@pytest.fixture(autouse=True)
def _disable_rate_limit(monkeypatch):
    """All tests run with rate limiting OFF unless they opt in.

    Rate limit tests set RATE_LIMIT_ENABLED=true via their own fixture,
    which runs after this autouse fixture and overrides the value.
    """
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")


@pytest.fixture(autouse=True)
def _disable_audit(monkeypatch):
    """All tests run with audit logging OFF unless they opt in.

    Audit tests set AUDIT_ENABLED=true via their own fixture,
    which runs after this autouse fixture and overrides the value.
    """
    monkeypatch.setenv("AUDIT_ENABLED", "false")
