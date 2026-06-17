"""
Phase 22 — Security & Production Readiness tests.

SEC22-01  JWT test secret is >= 32 bytes (RFC 7518 §3.2 for HS256)
SEC22-02  Production mode rejects JWT_SECRET shorter than 32 bytes
SEC22-03  Production mode accepts JWT_SECRET of exactly 32 bytes
SEC22-04  validate_secret_strength() returns issues for short secret
SEC22-05  validate_secret_strength() returns empty list for strong secret
SEC22-06  dev auth endpoint returns 404 when FLASK_ENV=production
SEC22-07  dev auth endpoint returns 404 when EXPERT_SMART_DEV_AUTH not set
SEC22-08  CORS: wildcard origin is never allowed by default config
SEC22-09  Static route /<path> blocks path-traversal via send_from_directory safe_join
SEC22-10  /api/download/<filename> requires auth (Excel/report not public)
SEC22-11  /api/valuation/report/download/<filename> requires auth
SEC22-12  /api/download path traversal blocked (backslash encoded)
SEC22-13  Missing report file returns 404 (safe error, not traceback)
SEC22-14  Broad warning suppression is gone from investment_engine and master_report_generator
SEC22-15  No real secrets hardcoded in tokens.py or dev_auth.py
"""
from __future__ import annotations

import os
import sys
import ast
import warnings
from pathlib import Path

import pytest

# ── path setup ────────────────────────────────────────────────────────────────
_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(str(_CORE))

# ── constants ─────────────────────────────────────────────────────────────────
_STRONG_SECRET = "phase22-security-test-secret-32b!!"   # 34 bytes — well above minimum
_SHORT_SECRET  = "tooshort"                              # 8 bytes  — below minimum


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Ensure each test starts with a known env state."""
    monkeypatch.setenv("JWT_SECRET", _STRONG_SECRET)
    monkeypatch.delenv("FLASK_ENV",              raising=False)
    monkeypatch.delenv("APP_ENV",                raising=False)
    monkeypatch.delenv("EXPERT_SMART_DEV_AUTH",  raising=False)
    monkeypatch.delenv("JWT_TTL_SECONDS",        raising=False)


@pytest.fixture()
def client():
    from bridge_api import app
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture()
def auth_headers():
    from auth.tokens import generate_token
    token = generate_token("sec22-test-user")
    return {"Authorization": f"Bearer {token}"}


# ── SEC22-01: JWT test secret length ─────────────────────────────────────────

def test_SEC22_01_strong_secret_meets_rfc7518():
    """SEC22-01: _STRONG_SECRET constant is ≥ 32 bytes (RFC 7518 §3.2 for HS256)."""
    assert len(_STRONG_SECRET.encode()) >= 32, (
        f"_STRONG_SECRET is only {len(_STRONG_SECRET.encode())} bytes; "
        "HS256 requires ≥ 32 bytes"
    )


# ── SEC22-02: production rejects short secret ─────────────────────────────────

def test_SEC22_02_production_rejects_short_jwt_secret(monkeypatch):
    """SEC22-02: FLASK_ENV=production with a short JWT_SECRET raises AuthError."""
    from auth.tokens import AuthError, generate_token
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", _SHORT_SECRET)
    with pytest.raises(AuthError, match="too short"):
        generate_token("any-user")


# ── SEC22-03: production accepts 32-byte secret ───────────────────────────────

def test_SEC22_03_production_accepts_32byte_secret(monkeypatch):
    """SEC22-03: FLASK_ENV=production with a 32-byte secret does not raise."""
    from auth.tokens import generate_token, verify_token
    secret_32 = "a" * 32   # exactly 32 bytes
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", secret_32)
    token = generate_token("prod-user")
    payload = verify_token(token)
    assert payload["sub"] == "prod-user"


# ── SEC22-04: validate_secret_strength reports short secrets ──────────────────

def test_SEC22_04_validate_secret_strength_short():
    """SEC22-04: validate_secret_strength() returns issues for short secrets."""
    from auth.tokens import validate_secret_strength
    issues = validate_secret_strength(_SHORT_SECRET)
    assert len(issues) >= 1
    assert any("32" in i for i in issues), (
        f"Expected mention of '32 bytes' in issues, got: {issues}"
    )


# ── SEC22-05: validate_secret_strength clears strong secrets ──────────────────

def test_SEC22_05_validate_secret_strength_strong():
    """SEC22-05: validate_secret_strength() returns [] for a strong secret."""
    from auth.tokens import validate_secret_strength
    issues = validate_secret_strength(_STRONG_SECRET)
    assert issues == [], f"Strong secret should have no issues, got: {issues}"


# ── SEC22-06: dev auth blocked in production ──────────────────────────────────

def test_SEC22_06_dev_auth_blocked_in_production(monkeypatch, client):
    """SEC22-06: /api/dev/auth-token returns 404 when FLASK_ENV=production."""
    monkeypatch.setenv("EXPERT_SMART_DEV_AUTH", "1")
    monkeypatch.setenv("FLASK_ENV", "production")
    resp = client.get("/api/dev/auth-token", headers={"Host": "127.0.0.1:5000"})
    assert resp.status_code == 404, (
        f"Dev auth must return 404 in production, got {resp.status_code}"
    )


# ── SEC22-07: dev auth blocked when flag not set ──────────────────────────────

def test_SEC22_07_dev_auth_blocked_when_flag_unset(client):
    """SEC22-07: /api/dev/auth-token returns 404 when EXPERT_SMART_DEV_AUTH is unset."""
    resp = client.get("/api/dev/auth-token", headers={"Host": "127.0.0.1:5000"})
    assert resp.status_code == 404


# ── SEC22-08: CORS never allows wildcard ─────────────────────────────────────

def test_SEC22_08_cors_no_wildcard_in_default_config():
    """SEC22-08: Default CORS origins list never contains '*'."""
    # Read ALLOWED_ORIGINS logic from bridge_api module constants
    import bridge_api as ba
    allowed = getattr(ba, "_CORS_ORIGINS", [])
    assert "*" not in allowed, (
        "CORS wildcard '*' must never appear in _CORS_ORIGINS"
    )
    # No entry should be a wildcard
    for origin in allowed:
        assert origin != "*", f"Wildcard origin found: {origin!r}"


# ── SEC22-09: static route path traversal blocked ────────────────────────────

def test_SEC22_09_static_route_path_traversal_blocked(client):
    """SEC22-09: /<path> static route blocks traversal via werkzeug safe_join."""
    # werkzeug's send_from_directory raises NotFound for traversal attempts
    # These should NOT return 200 or expose files outside frontend/
    traversal_paths = [
        "..%2Fcore_engine%2Fbridge_api.py",   # encoded /
        "..%5Ccore_engine%5Cbridge_api.py",   # encoded backslash
    ]
    for path in traversal_paths:
        resp = client.get(f"/{path}")
        assert resp.status_code != 200, (
            f"Traversal path {path!r} returned 200 — path traversal not blocked!"
        )


# ── SEC22-10: /api/download requires auth ────────────────────────────────────

def test_SEC22_10_download_requires_auth(client):
    """SEC22-10: /api/download/<filename> returns 401 without a token (not public)."""
    resp = client.get("/api/download/internal_report.xlsx")
    assert resp.status_code == 401, (
        f"Excel download must require auth, got {resp.status_code}"
    )


# ── SEC22-11: /api/valuation/report/download requires auth ───────────────────

def test_SEC22_11_valuation_download_requires_auth(client):
    """SEC22-11: /api/valuation/report/download/<f> returns 401 without a token."""
    resp = client.get("/api/valuation/report/download/report.xlsx")
    assert resp.status_code == 401, (
        f"Valuation Excel download must require auth, got {resp.status_code}"
    )


# ── SEC22-12: /api/download traversal blocked ────────────────────────────────

def test_SEC22_12_download_traversal_blocked_backslash(client, auth_headers):
    """SEC22-12: /api/download with backslash traversal returns 400, not 200."""
    resp = client.get("/api/download/..%5Csecret.txt", headers=auth_headers)
    assert resp.status_code == 400, (
        f"Backslash traversal on /api/download must return 400, got {resp.status_code}"
    )


# ── SEC22-13: missing report returns safe 404 ────────────────────────────────

def test_SEC22_13_missing_report_returns_safe_404(client, auth_headers, tmp_path, monkeypatch):
    """SEC22-13: A missing file at /api/download returns 404, not a traceback."""
    import bridge_api
    monkeypatch.setattr(bridge_api, "OUTPUTS", str(tmp_path))
    resp = client.get("/api/download/nonexistent_report.xlsx", headers=auth_headers)
    assert resp.status_code == 404
    # Response must be JSON (safe error), not an HTML traceback
    data = resp.get_json()
    assert data is not None, "Missing-file response must be JSON, not HTML traceback"
    assert "error" in data or "message" in data


# ── SEC22-14: broad warning suppression removed ───────────────────────────────

def test_SEC22_14_targeted_warning_suppression_in_report_engines():
    """SEC22-14: investment_engine.py and master_report_generator.py no longer use
    blanket warnings.filterwarnings('ignore') — only targeted suppressions.
    Verified by AST parsing (no runtime import side effects).
    """
    for module_name in ("investment_engine.py", "master_report_generator.py"):
        src = (_CORE / module_name).read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            # Detect: warnings.filterwarnings("ignore") — no category argument
            if not (
                isinstance(func, ast.Attribute)
                and func.attr == "filterwarnings"
                and isinstance(func.value, ast.Name)
                and func.value.id == "warnings"
            ):
                continue
            # args[0] must be "ignore"
            if not (node.args and isinstance(node.args[0], ast.Constant)
                    and node.args[0].value == "ignore"):
                continue
            # If there are keywords (category=...), the call is targeted → OK
            has_category = any(kw.arg == "category" for kw in node.keywords)
            assert has_category, (
                f"{module_name}: found blanket warnings.filterwarnings('ignore') "
                "without a category= argument. Replace with targeted suppression."
            )


# ── SEC22-15: no hardcoded real secrets ──────────────────────────────────────

def test_SEC22_15_no_hardcoded_secrets_in_source():
    """SEC22-15: tokens.py and dev_auth.py contain no hardcoded real secrets."""
    suspicious_patterns = ["sk-", "ghp_", "AKIA", "ya29.", "xoxb-"]
    for fname in ("auth/tokens.py", "dev_auth.py"):
        src = (_CORE / fname).read_text(encoding="utf-8")
        for pat in suspicious_patterns:
            assert pat not in src, (
                f"{fname}: found suspicious secret pattern {pat!r} in source code"
            )
