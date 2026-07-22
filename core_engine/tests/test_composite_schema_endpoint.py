"""Tests for GET /api/valuation/composite/schema (Wave 5a)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# ── sys.path + cwd setup ──────────────────────────────────────────────────────
_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent

for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_ORIG_CWD = os.getcwd()
try:
    os.chdir(str(_CORE))

    from bridge_api import app  # noqa: E402
    from valuation_engines.composite_engine import ASSET_TYPES  # noqa: E402
    from adapters.purpose_adapter import PURPOSE_RULES           # noqa: E402
finally:
    os.chdir(_ORIG_CWD)

_ENDPOINT = "/api/valuation/composite/schema"
_VALUE_EP = "/api/valuation/composite"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _jwt_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-wave5a-schema")


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture()
def auth(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-wave5a-schema")
    from auth.tokens import generate_token
    return {"Authorization": f"Bearer {generate_token('schema-test-user')}"}


@pytest.fixture()
def schema(client, auth):
    """Cached schema response dict."""
    return client.get(_ENDPOINT, headers=auth).get_json()


# ── 200 + top-level shape ─────────────────────────────────────────────────────

class TestResponseShape:
    def test_200(self, client, auth):
        resp = client.get(_ENDPOINT, headers=auth)
        assert resp.status_code == 200

    def test_composite_api_version_key(self, schema):
        assert schema["composite_api_version"] == 1

    def test_asset_types_key_present(self, schema):
        assert "asset_types" in schema

    def test_purposes_key_present(self, schema):
        assert "purposes" in schema


# ── 15 asset types ────────────────────────────────────────────────────────────

class TestAssetTypes:
    def test_exactly_15_types(self, schema):
        assert len(schema["asset_types"]) == 15

    def test_every_entry_has_name(self, schema):
        for entry in schema["asset_types"]:
            assert "name" in entry
            assert isinstance(entry["name"], str)

    def test_every_entry_has_attributes_list(self, schema):
        for entry in schema["asset_types"]:
            assert "attributes" in entry
            assert isinstance(entry["attributes"], list)

    def test_attribute_type_values_are_strings(self, schema):
        valid = {"int", "float", "str", "bool"}
        for entry in schema["asset_types"]:
            for attr in entry["attributes"]:
                assert attr["type"] in valid, (
                    f"Unexpected type {attr['type']!r} on {entry['name']}.{attr['name']}"
                )

    def test_names_match_asset_types_catalog_exactly(self, schema):
        returned = [e["name"] for e in schema["asset_types"]]
        assert returned == list(ASSET_TYPES.keys())

    def test_order_preserved(self, schema):
        returned = [e["name"] for e in schema["asset_types"]]
        expected = list(ASSET_TYPES.keys())
        assert returned == expected


# ── Airport/ports — the Wave 1 new type ──────────────────────────────────────

class TestAirportType:
    _TYPE_NAME = "المطارات والموانئ"
    _EXPECTED_ATTRS = {
        "facility_subtype",
        "annual_throughput",
        "berth_or_runway_count",
        "concession_years_remaining",
    }

    def _airport_entry(self, schema):
        entries = [e for e in schema["asset_types"] if e["name"] == self._TYPE_NAME]
        assert entries, f"{self._TYPE_NAME!r} missing from asset_types"
        return entries[0]

    def test_airport_present(self, schema):
        self._airport_entry(schema)

    def test_airport_has_four_attributes(self, schema):
        entry = self._airport_entry(schema)
        assert len(entry["attributes"]) == 4

    def test_airport_attribute_names(self, schema):
        entry = self._airport_entry(schema)
        names = {a["name"] for a in entry["attributes"]}
        assert names == self._EXPECTED_ATTRS

    def test_airport_facility_subtype_is_str(self, schema):
        entry = self._airport_entry(schema)
        attr = next(a for a in entry["attributes"] if a["name"] == "facility_subtype")
        assert attr["type"] == "str"

    def test_airport_berth_or_runway_count_is_int(self, schema):
        entry = self._airport_entry(schema)
        attr = next(a for a in entry["attributes"] if a["name"] == "berth_or_runway_count")
        assert attr["type"] == "int"


# ── 14 purposes ───────────────────────────────────────────────────────────────

class TestPurposes:
    def test_exactly_14_purposes(self, schema):
        assert len(schema["purposes"]) == 14

    def test_every_purpose_has_name_multiplier_deep(self, schema):
        for p in schema["purposes"]:
            assert "name" in p
            assert "multiplier" in p
            assert "deep" in p

    def test_multiplier_is_float(self, schema):
        for p in schema["purposes"]:
            assert isinstance(p["multiplier"], float)

    def test_deep_is_bool(self, schema):
        for p in schema["purposes"]:
            assert isinstance(p["deep"], bool)

    def test_names_match_purpose_rules_catalog_exactly(self, schema):
        returned = [p["name"] for p in schema["purposes"]]
        assert returned == list(PURPOSE_RULES.keys())

    def test_explicit_multipliers_correct(self, schema):
        by_name = {p["name"]: p for p in schema["purposes"]}
        assert by_name["البيع والشراء - القيمة السوقية العادلة (Market Value)"]["multiplier"] == 1.0
        assert by_name["الرهن والتمويل البنكي - القيمة السوقية لأغراض التمويل (0.95x)"]["multiplier"] == 0.95
        assert by_name["التصفية الإجبارية - القيمة التصفوية (Liquidation Value x0.82)"]["multiplier"] == 0.82
        assert by_name["التأمين - قيمة إعادة الإنشاء (Reinstatement Value x1.08)"]["multiplier"] == 1.08

    def test_4_explicit_multiplier_purposes_not_deep(self, schema):
        not_deep = [p for p in schema["purposes"] if not p["deep"]]
        assert len(not_deep) == 4

    def test_10_deep_route_purposes(self, schema):
        deep = [p for p in schema["purposes"] if p["deep"]]
        assert len(deep) == 10


# ── Determinism ───────────────────────────────────────────────────────────────

class TestDeterminism:
    def test_two_calls_identical(self, client, auth):
        r1 = client.get(_ENDPOINT, headers=auth).get_json()
        r2 = client.get(_ENDPOINT, headers=auth).get_json()
        assert r1 == r2

    def test_asset_type_order_stable(self, client, auth):
        r1 = [e["name"] for e in client.get(_ENDPOINT, headers=auth).get_json()["asset_types"]]
        r2 = [e["name"] for e in client.get(_ENDPOINT, headers=auth).get_json()["asset_types"]]
        assert r1 == r2


# ── Auth ──────────────────────────────────────────────────────────────────────

class TestAuth:
    def test_no_token_returns_401(self, client):
        resp = client.get(_ENDPOINT)
        assert resp.status_code == 401

    def test_post_returns_405(self, client, auth):
        resp = client.post(_ENDPOINT, headers=auth)
        assert resp.status_code == 405


# ── Wave 4 isolation ──────────────────────────────────────────────────────────

class TestWave4Isolation:
    def test_value_endpoint_still_reachable(self, client, auth):
        """POST /api/valuation/composite must still return 200 after Wave 5a changes."""
        body = {
            "components": [{
                "id": "r1", "name": "x",
                "asset_type": "وحدة سكنية (شقة / فيلا)",
                "area_sqm": 50.0, "base_rate_per_sqm": 1000.0,
                "specific_attributes": {"bedrooms_count": 2, "floor_number": 1},
            }],
            "purposes": ["البيع والشراء - القيمة السوقية العادلة (Market Value)"],
        }
        resp = client.post(_VALUE_EP, json=body, headers=auth)
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"
