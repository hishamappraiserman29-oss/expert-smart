"""
test_phase_16_e2e.py — Phase 16.0 MCP Bridge (10 tests)

All tests mock httpx.Client so no live server is required.

Tests:
  01  APIResponse dataclass fields and to_dict()
  02  ExpertSmartBridge instantiation (base URL, client)
  03  health_check — 200 response → success=True, status="healthy"
  04  health_check — connection error → success=False, status="unreachable"
  05  evaluate_property — correct URL and payload sent
  06  evaluate_land — correct URL and payload sent
  07  search_comparables — filters passed through correctly
  08  batch_valuate — uses /api/valuation/batch (not legacy /api/batch/valuate)
  09  get_batch_status — GET /api/valuation/batch/<id>
  10  MCP server exposes exactly 10 registered tools with correct names
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

_CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_CORE))
os.chdir(str(_CORE))

from mcp_bridge import APIResponse, ExpertSmartBridge, mcp


# ── Mock helpers ──────────────────────────────────────────────────────────────

def _mock_resp(status_code: int, body: dict) -> MagicMock:
    m = MagicMock()
    m.status_code = status_code
    m.json.return_value = body
    m.text = json.dumps(body)
    return m


def _bridge_with_mock_get(status_code: int, body: dict) -> tuple:
    b = ExpertSmartBridge("http://test-server")
    b.client.get = MagicMock(return_value=_mock_resp(status_code, body))
    return b


def _bridge_with_mock_post(status_code: int, body: dict) -> tuple:
    b = ExpertSmartBridge("http://test-server")
    b.client.post = MagicMock(return_value=_mock_resp(status_code, body))
    return b


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_01_api_response_dataclass():
    r = APIResponse(success=True, status="ok", data={"k": "v"})
    assert r.success is True
    assert r.status  == "ok"
    assert r.data    == {"k": "v"}
    assert r.error   is None

    d = r.to_dict()
    assert d["success"] is True
    assert d["status"]  == "ok"
    assert d["data"]    == {"k": "v"}
    assert d["error"]   is None

    r2 = APIResponse(success=False, status="error", error="oops")
    assert r2.to_dict()["error"] == "oops"


def test_02_bridge_instantiation():
    b = ExpertSmartBridge("http://localhost:5000")
    assert b.api_base == "http://localhost:5000"
    assert b.client is not None

    # Trailing slash stripped
    b2 = ExpertSmartBridge("http://localhost:5000/")
    assert b2.api_base == "http://localhost:5000"


def test_03_health_check_success():
    b = _bridge_with_mock_get(200, {"status": "ok", "version": "1.0"})
    r = b.health_check()
    assert r.success is True
    assert r.status  == "healthy"
    assert r.data is not None
    b.client.get.assert_called_once_with("http://test-server/api/advisor/health")


def test_04_health_check_unreachable():
    b = ExpertSmartBridge("http://test-server")
    b.client.get = MagicMock(side_effect=Exception("Connection refused"))
    r = b.health_check()
    assert r.success is False
    assert r.status  == "unreachable"
    assert "Connection refused" in r.error


def test_05_evaluate_property_payload():
    b = _bridge_with_mock_post(200, {"status": "success", "primary_value": 3_000_000})
    r = b.evaluate_property(150.0, "Cairo", "residential", "market_value")

    assert r.success is True
    assert r.data["primary_value"] == 3_000_000

    call_kwargs = b.client.post.call_args
    url     = call_kwargs[0][0]
    payload = call_kwargs[1]["json"]

    assert url == "http://test-server/api/valuation/full"
    assert payload["subject_property"]["area_sqm"]      == 150.0
    assert payload["subject_property"]["property_type"] == "residential"
    assert payload["subject_property"]["location"]      == "Cairo"
    assert payload["primary_purpose"]                   == "market_value"


def test_06_evaluate_land_payload():
    b = _bridge_with_mock_post(200, {"status": "success", "hbu": "residential"})
    r = b.evaluate_land(800.0, "Giza")

    assert r.success is True
    call_kwargs = b.client.post.call_args
    url     = call_kwargs[0][0]
    payload = call_kwargs[1]["json"]

    assert url == "http://test-server/api/valuation/land"
    assert payload["subject_property"]["property_type"] == "land"
    assert payload["subject_property"]["area_sqm"]      == 800.0
    assert payload["subject_property"]["location"]      == "Giza"


def test_07_search_comparables_filters():
    b = _bridge_with_mock_post(200, {"status": "success", "comparables": []})

    # with location
    r = b.search_comparables("commercial", "Alexandria")
    assert r.success is True
    payload = b.client.post.call_args[1]["json"]
    assert payload["filters"]["property_type"] == "commercial"
    assert payload["filters"]["governorate"]   == "Alexandria"

    # without location — key must be absent
    b2 = _bridge_with_mock_post(200, {"status": "success", "comparables": []})
    b2.search_comparables("residential")
    payload2 = b2.client.post.call_args[1]["json"]
    assert "governorate" not in payload2["filters"]


def test_08_batch_valuate_correct_url():
    b = _bridge_with_mock_post(200, {
        "status": "success", "batch_id": "abc-123",
        "summary": {"completed": 2, "failed": 0},
    })
    properties = [
        {"property_id": "P1", "property_type": "residential",
         "area_sqm": 100, "input_data": {"valuation_value": 500_000}},
        {"property_id": "P2", "property_type": "commercial",
         "area_sqm": 300, "input_data": {"price_per_sqm": 8_000}},
    ]
    r = b.batch_valuate(properties)
    assert r.success is True
    assert r.data["batch_id"] == "abc-123"

    url = b.client.post.call_args[0][0]
    assert url == "http://test-server/api/valuation/batch", \
        f"Wrong URL: expected /api/valuation/batch, got {url}"


def test_09_get_batch_status_url():
    b = _bridge_with_mock_get(200, {
        "status": "success", "batch_id": "xyz-789",
        "summary": {"completed": 5, "failed": 0},
    })
    r = b.get_batch_status("xyz-789")
    assert r.success is True

    url = b.client.get.call_args[0][0]
    assert url == "http://test-server/api/valuation/batch/xyz-789", \
        f"Wrong URL: {url}"


def test_10_mcp_has_10_tools():
    expected = {
        "health_check", "evaluate_property", "evaluate_land",
        "search_comparables", "analyze_portfolio", "batch_valuate",
        "get_batch_status", "generate_report", "audit_valuation",
        "dcf_analyze",
    }

    async def _check():
        tools = await mcp.list_tools()
        return {t.name for t in tools}

    registered = asyncio.run(_check())
    assert len(registered) == 10, f"Expected 10 tools, got {len(registered)}: {registered}"
    assert registered == expected, f"Missing: {expected - registered}, Extra: {registered - expected}"


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for fn in tests:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
            passed += 1
        except Exception as exc:
            import traceback
            print(f"  FAIL  {fn.__name__}: {exc}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed}/{passed + failed} tests passed")
