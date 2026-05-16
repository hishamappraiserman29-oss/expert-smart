"""Tests for core_engine.auth.tokens — Wave S2."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import jwt
import pytest

_CORE = Path(__file__).resolve().parents[1]
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from auth.tokens import AuthError, generate_token, verify_token

_TEST_SECRET = "test-secret-for-unit-tests-only"


@pytest.fixture(autouse=True)
def jwt_secret(monkeypatch):
    """Deterministic secret for all tests in this module."""
    monkeypatch.setenv("JWT_SECRET", _TEST_SECRET)
    monkeypatch.delenv("JWT_TTL_SECONDS", raising=False)
    yield


class TestGenerateToken:
    def test_generates_valid_jwt(self):
        token = generate_token("alice")
        assert isinstance(token, str) and len(token) > 0
        decoded = jwt.decode(token, _TEST_SECRET, algorithms=["HS256"])
        assert decoded["sub"] == "alice"

    def test_empty_user_id_rejected(self):
        with pytest.raises(AuthError, match="non-empty string"):
            generate_token("")

    def test_non_string_user_id_rejected(self):
        with pytest.raises(AuthError, match="non-empty string"):
            generate_token(None)  # type: ignore[arg-type]

    def test_secret_unset_raises(self, monkeypatch):
        monkeypatch.delenv("JWT_SECRET", raising=False)
        with pytest.raises(AuthError, match="JWT_SECRET"):
            generate_token("alice")

    def test_custom_ttl(self):
        token = generate_token("alice", ttl_seconds=60)
        payload = jwt.decode(token, _TEST_SECRET, algorithms=["HS256"])
        assert payload["exp"] - payload["iat"] == 60

    def test_negative_ttl_rejected(self):
        with pytest.raises(AuthError, match="positive"):
            generate_token("alice", ttl_seconds=-1)

    def test_zero_ttl_rejected(self):
        with pytest.raises(AuthError, match="positive"):
            generate_token("alice", ttl_seconds=0)

    def test_token_contains_iat_and_exp(self):
        token = generate_token("bob")
        payload = jwt.decode(token, _TEST_SECRET, algorithms=["HS256"])
        assert "iat" in payload and "exp" in payload
        assert payload["exp"] > payload["iat"]

    def test_different_users_produce_different_tokens(self):
        t1 = generate_token("alice")
        t2 = generate_token("bob")
        assert t1 != t2


class TestVerifyToken:
    def test_round_trip(self):
        token = generate_token("alice")
        payload = verify_token(token)
        assert payload["sub"] == "alice"
        assert "iat" in payload and "exp" in payload

    def test_empty_token_rejected(self):
        with pytest.raises(AuthError, match="non-empty"):
            verify_token("")

    def test_none_token_rejected(self):
        with pytest.raises(AuthError, match="non-empty"):
            verify_token(None)  # type: ignore[arg-type]

    def test_malformed_token_rejected(self):
        with pytest.raises(AuthError, match="invalid"):
            verify_token("not.a.valid.jwt")

    def test_tampered_signature_rejected(self):
        token = generate_token("alice")
        tampered = token[:-4] + "XXXX"
        with pytest.raises(AuthError, match="invalid"):
            verify_token(tampered)

    def test_expired_token_rejected(self):
        token = generate_token("alice", ttl_seconds=1)
        time.sleep(2)
        with pytest.raises(AuthError, match="expired"):
            verify_token(token)

    def test_wrong_secret_rejected(self, monkeypatch):
        token = generate_token("alice")
        monkeypatch.setenv("JWT_SECRET", "different-secret")
        with pytest.raises(AuthError, match="invalid"):
            verify_token(token)

    def test_sub_claim_returned(self):
        token = generate_token("user-999")
        payload = verify_token(token)
        assert payload["sub"] == "user-999"


class TestEnvironment:
    def test_invalid_ttl_env_raises(self, monkeypatch):
        monkeypatch.setenv("JWT_TTL_SECONDS", "not-a-number")
        with pytest.raises(AuthError, match="positive integer"):
            generate_token("alice")

    def test_zero_ttl_env_raises(self, monkeypatch):
        monkeypatch.setenv("JWT_TTL_SECONDS", "0")
        with pytest.raises(AuthError, match="positive integer"):
            generate_token("alice")

    def test_negative_ttl_env_raises(self, monkeypatch):
        monkeypatch.setenv("JWT_TTL_SECONDS", "-60")
        with pytest.raises(AuthError, match="positive integer"):
            generate_token("alice")

    def test_valid_ttl_env_used(self, monkeypatch):
        monkeypatch.setenv("JWT_TTL_SECONDS", "120")
        token = generate_token("alice")
        payload = jwt.decode(token, _TEST_SECRET, algorithms=["HS256"])
        assert payload["exp"] - payload["iat"] == 120
