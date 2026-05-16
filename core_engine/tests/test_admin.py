"""Unit tests for core_engine.admin — is_admin and require_admin."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parents[1]
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from admin import is_admin  # noqa: E402


class TestIsAdmin:
    def test_none_user_not_admin(self, monkeypatch):
        monkeypatch.setenv("ADMIN_USER_IDS", "alice,bob")
        assert is_admin(None) is False

    def test_empty_string_not_admin(self, monkeypatch):
        monkeypatch.setenv("ADMIN_USER_IDS", "alice,bob")
        assert is_admin("") is False

    def test_user_in_set_is_admin(self, monkeypatch):
        monkeypatch.setenv("ADMIN_USER_IDS", "alice,bob")
        assert is_admin("alice") is True
        assert is_admin("bob") is True

    def test_user_not_in_set(self, monkeypatch):
        monkeypatch.setenv("ADMIN_USER_IDS", "alice,bob")
        assert is_admin("carol") is False

    def test_whitespace_trimmed(self, monkeypatch):
        monkeypatch.setenv("ADMIN_USER_IDS", " alice , bob ")
        assert is_admin("alice") is True

    def test_empty_env_no_admins(self, monkeypatch):
        monkeypatch.setenv("ADMIN_USER_IDS", "")
        assert is_admin("alice") is False

    def test_unset_env_no_admins(self, monkeypatch):
        monkeypatch.delenv("ADMIN_USER_IDS", raising=False)
        assert is_admin("alice") is False

    def test_email_style_id(self, monkeypatch):
        monkeypatch.setenv("ADMIN_USER_IDS", "ops@example.com")
        assert is_admin("ops@example.com") is True

    def test_single_admin(self, monkeypatch):
        monkeypatch.setenv("ADMIN_USER_IDS", "superuser")
        assert is_admin("superuser") is True
        assert is_admin("alice") is False

    def test_case_sensitive(self, monkeypatch):
        monkeypatch.setenv("ADMIN_USER_IDS", "Alice")
        assert is_admin("alice") is False
        assert is_admin("Alice") is True
