"""
Backend tests — PVS5: Professional Valuation Common Asset Requirements Restore
Task: PVS5-HARD-RESTORE

Tests verify:
1. API accepts all common asset types that have fillable data (hotel, resort, factory, etc.)
2. API accepts uncommon/special asset types (petrol_station, cinema, padel, etc.)
3. No old property types were removed
4. Backend-level asset type normalization works
5. Request creation succeeds for all required asset types
6. No internal paths exposed
7. Ordinary valuation endpoints unaffected
"""
import os
import sys
import pytest
from pathlib import Path

_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(str(_CORE))
os.environ.setdefault("JWT_SECRET", "pvs5-restore-test-secret-xxxxx")

from bridge_api import app  # noqa: E402
from auth.tokens import generate_token  # noqa: E402

app.config["TESTING"] = True


def _auth() -> dict:
    return {"Authorization": "Bearer " + generate_token("test-admin")}


def _create(client, asset_type: str, extra: dict | None = None) -> dict:
    body = {
        "client_name": "pvs5-test",
        "property_type": asset_type,
        "valuation_purpose": "financing_mortgage",
        "city": "Cairo",
        "district": "Downtown",
    }
    if extra:
        body.update(extra)
    r = client.post(
        "/api/professional-valuation/requests",
        json=body,
        content_type="application/json",
        headers=_auth(),
    )
    return r.get_json() or {}


# ── AR01: API health endpoint still works ─────────────────────────────────
def test_AR01_api_health_still_works() -> None:
    """AR01: Health endpoint responds after restore changes (status 'ok')."""
    with app.test_client() as c:
        r = c.get("/api/advisor/health")
        assert r.status_code == 200
        data = r.get_json() or {}
        # Health endpoint returns either {ok: true} or {status: 'ok'}
        assert data.get("ok") is True or data.get("status") == "ok"


# ── AR02: Hotel asset type accepted ───────────────────────────────────────
def test_AR02_hotel_asset_type_accepted() -> None:
    """AR02: property_type=hotel is accepted and returns a request_id."""
    with app.test_client() as c:
        data = _create(c, "hotel")
        assert data.get("ok") is True
        assert data.get("request_id")


# ── AR03: Resort alias accepted ───────────────────────────────────────────
def test_AR03_resort_alias_accepted() -> None:
    """AR03: property_type=resort is accepted."""
    with app.test_client() as c:
        data = _create(c, "resort")
        assert data.get("ok") is True
        assert data.get("request_id")


# ── AR04: Industrial factory accepted ─────────────────────────────────────
def test_AR04_industrial_factory_accepted() -> None:
    """AR04: property_type=industrial_factory is accepted."""
    with app.test_client() as c:
        data = _create(c, "industrial_factory")
        assert data.get("ok") is True


# ── AR05: Warehouse accepted ───────────────────────────────────────────────
def test_AR05_warehouse_accepted() -> None:
    """AR05: property_type=warehouse is accepted."""
    with app.test_client() as c:
        data = _create(c, "warehouse")
        assert data.get("ok") is True


# ── AR06: Urban land accepted ──────────────────────────────────────────────
def test_AR06_urban_land_accepted() -> None:
    """AR06: property_type=urban_land is accepted."""
    with app.test_client() as c:
        data = _create(c, "urban_land")
        assert data.get("ok") is True


# ── AR07: Residential apartment accepted ──────────────────────────────────
def test_AR07_residential_apartment_accepted() -> None:
    """AR07: property_type=residential_apartment is accepted."""
    with app.test_client() as c:
        data = _create(c, "residential_apartment")
        assert data.get("ok") is True


# ── AR08: Administrative office accepted ──────────────────────────────────
def test_AR08_administrative_office_accepted() -> None:
    """AR08: property_type=administrative_office is accepted."""
    with app.test_client() as c:
        data = _create(c, "administrative_office")
        assert data.get("ok") is True


# ── AR09: Retail shop accepted ────────────────────────────────────────────
def test_AR09_retail_shop_accepted() -> None:
    """AR09: property_type=retail_shop is accepted."""
    with app.test_client() as c:
        data = _create(c, "retail_shop")
        assert data.get("ok") is True


# ── AR10: Shopping mall (alias) accepted ──────────────────────────────────
def test_AR10_shopping_mall_alias_accepted() -> None:
    """AR10: property_type=shopping_mall is accepted."""
    with app.test_client() as c:
        data = _create(c, "shopping_mall")
        assert data.get("ok") is True


# ── AR11: Residential villa (alias) accepted ──────────────────────────────
def test_AR11_residential_villa_alias_accepted() -> None:
    """AR11: property_type=residential_villa is accepted."""
    with app.test_client() as c:
        data = _create(c, "residential_villa")
        assert data.get("ok") is True


# ── AR12: Residential building (alias) accepted ───────────────────────────
def test_AR12_residential_building_alias_accepted() -> None:
    """AR12: property_type=residential_building is accepted."""
    with app.test_client() as c:
        data = _create(c, "residential_building")
        assert data.get("ok") is True


# ── AR13: Agricultural land (alias) accepted ──────────────────────────────
def test_AR13_agricultural_land_alias_accepted() -> None:
    """AR13: property_type=agricultural_land is accepted."""
    with app.test_client() as c:
        data = _create(c, "agricultural_land")
        assert data.get("ok") is True


# ── AR14: Mixed use asset (alias) accepted ────────────────────────────────
def test_AR14_mixed_use_asset_alias_accepted() -> None:
    """AR14: property_type=mixed_use_asset is accepted."""
    with app.test_client() as c:
        data = _create(c, "mixed_use_asset")
        assert data.get("ok") is True


# ── AR15: Floating hotel (alias) accepted ────────────────────────────────
def test_AR15_floating_hotel_alias_accepted() -> None:
    """AR15: property_type=floating_hotel is accepted."""
    with app.test_client() as c:
        data = _create(c, "floating_hotel")
        assert data.get("ok") is True


# ── AR16: Serviced apartments (alias) accepted ────────────────────────────
def test_AR16_serviced_apartments_alias_accepted() -> None:
    """AR16: property_type=serviced_apartments is accepted."""
    with app.test_client() as c:
        data = _create(c, "serviced_apartments")
        assert data.get("ok") is True


# ── AR17: Prefabricated factory (alias) accepted ─────────────────────────
def test_AR17_prefabricated_factory_alias_accepted() -> None:
    """AR17: property_type=prefabricated_factory is accepted."""
    with app.test_client() as c:
        data = _create(c, "prefabricated_factory")
        assert data.get("ok") is True


# ── AR18: Cold storage (alias) accepted ───────────────────────────────────
def test_AR18_cold_storage_alias_accepted() -> None:
    """AR18: property_type=cold_storage is accepted."""
    with app.test_client() as c:
        data = _create(c, "cold_storage")
        assert data.get("ok") is True


# ── AR19: Petrol station asset type accepted ──────────────────────────────
def test_AR19_petrol_station_accepted() -> None:
    """AR19: property_type=petrol_station is accepted (new uncommon asset)."""
    with app.test_client() as c:
        data = _create(c, "petrol_station")
        assert data.get("ok") is True


# ── AR20: Gas station alias accepted ──────────────────────────────────────
def test_AR20_gas_station_alias_accepted() -> None:
    """AR20: property_type=gas_station (alias for petrol_station) is accepted."""
    with app.test_client() as c:
        data = _create(c, "gas_station")
        assert data.get("ok") is True


# ── AR21: Request detail contains property_type for hotel ─────────────────
def test_AR21_request_detail_has_property_type_hotel() -> None:
    """AR21: Created hotel request detail returns property_type=hotel."""
    with app.test_client() as c:
        created = _create(c, "hotel")
        assert created.get("ok") is True
        rid = created.get("request_id", "")
        r2 = c.get(
            f"/api/professional-valuation/requests/{rid}",
            headers=_auth(),
        )
        detail = r2.get_json() or {}
        req = detail.get("request", {})
        pt = req.get("property_type") or req.get("asset_type", "")
        assert pt == "hotel"


# ── AR22: Request detail contains property_type for industrial_factory ────
def test_AR22_request_detail_has_property_type_factory() -> None:
    """AR22: Created industrial_factory request returns correct property_type."""
    with app.test_client() as c:
        created = _create(c, "industrial_factory")
        assert created.get("ok") is True
        rid = created.get("request_id", "")
        r2 = c.get(
            f"/api/professional-valuation/requests/{rid}",
            headers=_auth(),
        )
        detail = r2.get_json() or {}
        req = detail.get("request", {})
        pt = req.get("property_type") or req.get("asset_type", "")
        assert pt == "industrial_factory"


# ── AR23: Request detail contains property_type for urban_land ────────────
def test_AR23_request_detail_has_property_type_urban_land() -> None:
    """AR23: Created urban_land request returns correct property_type."""
    with app.test_client() as c:
        created = _create(c, "urban_land")
        assert created.get("ok") is True
        rid = created.get("request_id", "")
        r2 = c.get(
            f"/api/professional-valuation/requests/{rid}",
            headers=_auth(),
        )
        detail = r2.get_json() or {}
        req = detail.get("request", {})
        pt = req.get("property_type") or req.get("asset_type", "")
        assert pt == "urban_land"


# ── AR24: No internal file paths in creation response ──────────────────────
def test_AR24_no_internal_paths_in_hotel_create() -> None:
    """AR24: Hotel creation response does not expose internal file paths."""
    with app.test_client() as c:
        data = _create(c, "hotel")
        raw = str(data)
        assert "/home/" not in raw
        assert "C:\\" not in raw
        assert ".py" not in raw


# ── AR25: Hotel request detail contains full context data ────────────────
def test_AR25_hotel_request_detail_contains_context() -> None:
    """AR25: GET /requests/{rid} returns full context including asset_type for hotel."""
    with app.test_client() as c:
        created = _create(c, "hotel")
        assert created.get("ok") is True
        rid = created.get("request_id", "")
        r2 = c.get(
            f"/api/professional-valuation/requests/{rid}",
            headers=_auth(),
        )
        assert r2.status_code == 200
        detail = r2.get_json() or {}
        assert detail.get("ok") is True
        req = detail.get("request", {})
        assert req.get("property_type") == "hotel" or req.get("asset_type") == "hotel"


# ── AR26: Missing property_type returns 400 ───────────────────────────────
def test_AR26_missing_property_type_returns_400() -> None:
    """AR26: Creating a request without property_type returns 400."""
    with app.test_client() as c:
        body = {
            "client_name": "pvs5-test",
            "valuation_purpose": "financing_mortgage",
            "city": "Cairo",
        }
        r = c.post(
            "/api/professional-valuation/requests",
            json=body,
            content_type="application/json",
            headers=_auth(),
        )
        assert r.status_code == 400


# ── AR27: Residential apartment request detail contains context ───────────
def test_AR27_residential_request_detail_contains_context() -> None:
    """AR27: GET /requests/{rid} returns full context for residential_apartment."""
    with app.test_client() as c:
        created = _create(c, "residential_apartment")
        assert created.get("ok") is True
        rid = created.get("request_id", "")
        r2 = c.get(
            f"/api/professional-valuation/requests/{rid}",
            headers=_auth(),
        )
        assert r2.status_code == 200
        detail = r2.get_json() or {}
        assert detail.get("ok") is True
        req = detail.get("request", {})
        assert req.get("property_type") == "residential_apartment" or req.get("asset_type") == "residential_apartment"


# ── AR28: Requests list endpoint still works ──────────────────────────────
def test_AR28_requests_list_endpoint_works() -> None:
    """AR28: GET /api/professional-valuation/requests returns ok=true."""
    with app.test_client() as c:
        r = c.get("/api/professional-valuation/requests", headers=_auth())
        data = r.get_json() or {}
        assert data.get("ok") is True


# ── AR29: No common asset type was removed (hotel present in list) ─────────
def test_AR29_hotel_present_in_requests_list_after_creation() -> None:
    """AR29: Created hotel request appears in requests list."""
    with app.test_client() as c:
        created = _create(c, "hotel")
        rid = created.get("request_id", "")
        r2 = c.get("/api/professional-valuation/requests", headers=_auth())
        data = r2.get_json() or {}
        assert data.get("ok") is True
        requests = data.get("requests", [])
        found = any(req.get("request_id") == rid for req in requests)
        assert found


# ── AR30: Request created with asset_type key (alternative to property_type)
def test_AR30_asset_type_key_works_as_alternative() -> None:
    """AR30: Using asset_type instead of property_type is accepted."""
    with app.test_client() as c:
        body = {
            "client_name": "pvs5-test-at",
            "asset_type": "warehouse",
            "valuation_purpose": "financing_mortgage",
            "city": "Alexandria",
            "district": "Miami",
        }
        r = c.post(
            "/api/professional-valuation/requests",
            json=body,
            content_type="application/json",
            headers=_auth(),
        )
        data = r.get_json() or {}
        assert data.get("ok") is True


# ── AR31: Office building alias returns ok ────────────────────────────────
def test_AR31_office_building_alias_returns_ok() -> None:
    """AR31: property_type=office_building (alias for administrative_office) is accepted."""
    with app.test_client() as c:
        data = _create(c, "office_building")
        assert data.get("ok") is True


# ── AR32: Residential compound alias returns ok ───────────────────────────
def test_AR32_residential_compound_alias_returns_ok() -> None:
    """AR32: property_type=residential_compound (alias) is accepted."""
    with app.test_client() as c:
        data = _create(c, "residential_compound")
        assert data.get("ok") is True


# ── AR33: No old API endpoint was removed ────────────────────────────────
def test_AR33_no_old_professional_valuation_endpoint_removed() -> None:
    """AR33: Core API endpoints (list, create, detail, transition) still exist."""
    with app.test_client() as c:
        # GET requests list
        r1 = c.get("/api/professional-valuation/requests", headers=_auth())
        assert r1.status_code in (200, 201)

        # POST create new request
        created = _create(c, "apartment")
        rid = created.get("request_id", "")
        assert rid, "Could not create request"

        # GET request detail
        r3 = c.get(
            f"/api/professional-valuation/requests/{rid}",
            headers=_auth(),
        )
        assert r3.status_code == 200

        # POST to transition (exists even if it returns validation error)
        r4 = c.post(
            f"/api/professional-valuation/requests/{rid}/transition",
            json={"transition": "submit"},
            content_type="application/json",
            headers=_auth(),
        )
        # Transition endpoint exists — may succeed or fail (422) but not 404
        assert r4.status_code != 404, "Transition endpoint should exist (not 404)"
