"""
SEC-009 tests — .env.example presence and content safety.

The file must exist, must document all required security vars, and
must not contain any real secrets or production credentials.
"""
from __future__ import annotations

from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_ENV_EXAMPLE = _ROOT / ".env.example"


@pytest.fixture(scope="module")
def env_content() -> str:
    return _ENV_EXAMPLE.read_text(encoding="utf-8")


class TestEnvExampleExists:
    def test_file_exists(self):
        assert _ENV_EXAMPLE.exists(), ".env.example must exist at repo root"

    def test_file_is_not_empty(self, env_content):
        assert len(env_content.strip()) > 0


class TestEnvExampleRequiredVars:
    """All security-critical env vars must be documented."""

    def test_jwt_secret_documented(self, env_content):
        assert "JWT_SECRET" in env_content

    def test_jwt_ttl_documented(self, env_content):
        assert "JWT_TTL_SECONDS" in env_content

    def test_govt_signing_key_documented(self, env_content):
        assert "GOVT_SIGNING_KEY" in env_content

    def test_admin_user_ids_documented(self, env_content):
        assert "ADMIN_USER_IDS" in env_content

    def test_allowed_origins_documented(self, env_content):
        assert "ALLOWED_ORIGINS" in env_content

    def test_rate_limit_documented(self, env_content):
        assert "RATE_LIMIT_ENABLED" in env_content

    def test_audit_enabled_documented(self, env_content):
        assert "AUDIT_ENABLED" in env_content

    def test_audit_db_path_documented(self, env_content):
        assert "AUDIT_DB_PATH" in env_content


class TestEnvExampleNoRealSecrets:
    """The file must not contain real secrets or production credentials."""

    def test_no_obvious_placeholder_secret(self, env_content):
        # Common lazy placeholder secrets that should not appear
        bad = ["secret123", "password123", "mysecret", "letmein", "admin123"]
        for s in bad:
            assert s not in env_content.lower(), f"Found weak placeholder '{s}'"

    def test_no_private_key_block(self, env_content):
        assert "BEGIN RSA PRIVATE KEY" not in env_content
        assert "BEGIN PRIVATE KEY" not in env_content
        assert "BEGIN EC PRIVATE KEY" not in env_content

    def test_no_live_jwt_token(self, env_content):
        # Real JWTs start with eyJ (base64 of {"...)
        import re
        tokens = re.findall(r'eyJ[A-Za-z0-9_-]{20,}', env_content)
        assert len(tokens) == 0, f"Found potential live JWT token(s): {tokens}"

    def test_no_production_url_with_credentials(self, env_content):
        import re
        # URLs with embedded credentials: https://user:pass@host
        cred_urls = re.findall(r'https?://[^/\s:]+:[^/\s@]+@', env_content)
        assert len(cred_urls) == 0, f"Found URL with embedded credentials: {cred_urls}"

    def test_placeholder_value_signals_change_needed(self, env_content):
        # Our own placeholder strings are present
        assert "change-me" in env_content
