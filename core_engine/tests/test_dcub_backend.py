"""
DCUB Backend Tests
Professional Valuation Page — Remove Duplicate Upper Chat Box (DCUB)

8 tests covering:
- duplicate_chat_box_cleanup_context present in POST response (DCUB-B01)
- upper_duplicate_chat_box_removed is True (DCUB-B02)
- real_lower_chat_box_preserved is True (DCUB-B03)
- backend_output_context_preserved is True (DCUB-B04)
- certification_gates_preserved is True (DCUB-B05)
- debug_tokens_visible is False (DCUB-B06)
- no internal paths in response body (DCUB-B07)
- ordinary valuation route unaffected (DCUB-B08)
- tax appeal route unaffected (DCUB-B09)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

# ── Path setup ────────────────────────────────────────────────────────────────

_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_ORIG_CWD = os.getcwd()
try:
    os.chdir(str(_CORE))

    from bridge_api import app                     # noqa: E402
    from auth.tokens import generate_token         # noqa: E402
    import professional_valuation_routes as _pvr  # noqa: E402
finally:
    os.chdir(_ORIG_CWD)

_TEST_SECRET = "dcub-backend-test-secret-32char"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def _clean_pvr_datastore_dcub():
    """Clear accumulated test records before the session."""
    if _pvr._REQ_FILE.exists():
        _pvr._REQ_FILE.write_bytes(b"")
    if _pvr._EVENTS_FILE.exists():
        _pvr._EVENTS_FILE.write_bytes(b"")


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", _TEST_SECRET)
    monkeypatch.delenv("JWT_TTL_SECONDS", raising=False)


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _auth() -> dict:
    return {"Authorization": f"Bearer {generate_token('test-admin')}"}


_BASE_PAYLOAD: dict = {
    "client_name":       "مختبر DCUB",
    "property_type":     "شقة سكنية",
    "valuation_purpose": "financing_mortgage",
    "city":              "القاهرة",
    "district":          "مصر الجديدة",
}


def _create(client, extra: dict | None = None):
    data = dict(_BASE_PAYLOAD)
    if extra:
        data.update(extra)
    return client.post(
        "/api/professional-valuation/requests",
        json=data,
        content_type="application/json",
    )


def _get_dcub_ctx(client, resp) -> dict:
    """Extract duplicate_chat_box_cleanup_context from create response or detail."""
    body = resp.get_json() or {}
    if "duplicate_chat_box_cleanup_context" in body:
        return body["duplicate_chat_box_cleanup_context"]
    rid = body.get("request_id", "")
    if rid:
        detail = client.get(
            f"/api/professional-valuation/requests/{rid}",
            headers=_auth(),
        ).get_json() or {}
        return (
            detail.get("request", {}).get("duplicate_chat_box_cleanup_context")
            or detail.get("duplicate_chat_box_cleanup_context")
            or {}
        )
    return {}


# ── DCUB-B01: cleanup context present ─────────────────────────────────────────

def test_DCUB_B01_cleanup_context_in_response(client):
    """DCUB-B01: duplicate_chat_box_cleanup_context present in POST response."""
    resp = _create(client)
    assert resp.status_code == 201
    ctx = _get_dcub_ctx(client, resp)
    assert ctx, "duplicate_chat_box_cleanup_context missing from create response"


# ── DCUB-B02: upper duplicate removed flag ────────────────────────────────────

def test_DCUB_B02_upper_duplicate_removed_is_true(client):
    """DCUB-B02: upper_duplicate_chat_box_removed is True."""
    resp = _create(client)
    assert resp.status_code == 201
    ctx = _get_dcub_ctx(client, resp)
    assert ctx.get("upper_duplicate_chat_box_removed") is True, (
        f"upper_duplicate_chat_box_removed is not True: {ctx}"
    )


# ── DCUB-B03: real lower chat box preserved ───────────────────────────────────

def test_DCUB_B03_real_lower_chat_box_preserved_is_true(client):
    """DCUB-B03: real_lower_chat_box_preserved is True."""
    resp = _create(client)
    assert resp.status_code == 201
    ctx = _get_dcub_ctx(client, resp)
    assert ctx.get("real_lower_chat_box_preserved") is True, (
        f"real_lower_chat_box_preserved is not True: {ctx}"
    )


# ── DCUB-B04: backend output context preserved ───────────────────────────────

def test_DCUB_B04_backend_output_context_preserved(client):
    """DCUB-B04: backend_output_context_preserved is True."""
    resp = _create(client)
    assert resp.status_code == 201
    ctx = _get_dcub_ctx(client, resp)
    assert ctx.get("backend_output_context_preserved") is True, (
        f"backend_output_context_preserved is not True: {ctx}"
    )


# ── DCUB-B05: certification gates preserved ──────────────────────────────────

def test_DCUB_B05_certification_gates_preserved(client):
    """DCUB-B05: certification_gates_preserved is True."""
    resp = _create(client)
    assert resp.status_code == 201
    ctx = _get_dcub_ctx(client, resp)
    assert ctx.get("certification_gates_preserved") is True, (
        f"certification_gates_preserved is not True: {ctx}"
    )


# ── DCUB-B06: debug tokens not visible ───────────────────────────────────────

def test_DCUB_B06_debug_tokens_visible_is_false(client):
    """DCUB-B06: debug_tokens_visible is False."""
    resp = _create(client)
    assert resp.status_code == 201
    ctx = _get_dcub_ctx(client, resp)
    assert ctx.get("debug_tokens_visible") is False, (
        f"debug_tokens_visible is not False: {ctx}"
    )


# ── DCUB-B07: no internal paths in visible context ───────────────────────────

def test_DCUB_B07_no_internal_paths_in_response(client):
    """DCUB-B07: Response JSON does not expose internal file system paths."""
    resp = _create(client)
    assert resp.status_code == 201
    body_str = resp.get_data(as_text=True)
    forbidden = [r"C:\\Users\\", r"C:/Users/", "/home/", "core_engine/instance/"]
    for path in forbidden:
        assert path not in body_str, f"Internal path '{path}' found in response"


# ── DCUB-B08: ordinary valuation route unaffected ───────────────────────────

def test_DCUB_B08_ordinary_valuation_route_unaffected(client):
    """DCUB-B08: Ordinary (simple) valuation route not broken by DCUB changes."""
    resp = client.post(
        "/api/simple-valuation/draft-pdf",
        json={"property_type": "شقة", "area": 120},
        content_type="application/json",
    )
    assert resp.status_code not in (404, 405), (
        f"Simple valuation route broken after DCUB: {resp.status_code}"
    )


# ── DCUB-B09: tax appeal route unaffected ───────────────────────────────────

def test_DCUB_B09_tax_appeal_route_unaffected(client):
    """DCUB-B09: Tax appeal route not broken by DCUB changes."""
    resp = client.get(
        "/api/tax-appeal/expert-requests",
        headers=_auth(),
    )
    assert resp.status_code not in (404, 405, 500), (
        f"Tax appeal route broken after DCUB: {resp.status_code}"
    )
