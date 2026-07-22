"""
Integration tests for POST /api/valuation/composite (Wave 4).

Tests cover: happy path, golden snapshot regression guard, determinism,
blocking validation (422), advisory-visible-in-200, auth (401), bad
input (400), purpose broadcast, length mismatch, and summary contract.

Golden snapshot values — manual arithmetic verification:
  component[0] airport/ports: area 100 × rate 5 000 = 500 000 baseline
                               × 1.00 (Market Value)    = 500 000 adjusted  ✓
  component[1] residential:   area 10 000 × rate 2 000 = 20 000 000 baseline
                               × 0.95 (Financing)       = 19 000 000 adjusted ✓
  total_baseline = 20 500 000  total_adjusted = 19 500 000  advisory = 0  ✓
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

# ── sys.path + cwd setup ──────────────────────────────────────────────────────
_CORE = Path(__file__).resolve().parents[1]   # …/core_engine/
_ROOT = _CORE.parent

for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_ORIG_CWD = os.getcwd()
try:
    os.chdir(str(_CORE))

    from bridge_api import app  # noqa: E402  — triggers composite_routes registration
finally:
    os.chdir(_ORIG_CWD)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _jwt_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-wave4-composite")


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture()
def auth(monkeypatch):
    """Return Authorization header dict for a test user."""
    monkeypatch.setenv("JWT_SECRET", "test-secret-wave4-composite")
    from auth.tokens import generate_token
    return {"Authorization": f"Bearer {generate_token('composite-test-user')}"}


# ── Golden snapshot ───────────────────────────────────────────────────────────

_AIRPORT_NOTE = (
    "NOTE: Airport/seaport valuation is concession-based DCF — "
    "Wave 1 returns area×rate placeholder only. Full concession "
    "cashflow model + domain expert (د. عبد الرؤوف) review required "
    "before any client-facing use."
)

_MARKET_VALUE   = "البيع والشراء - القيمة السوقية العادلة (Market Value)"
_FINANCING_095  = "الرهن والتمويل البنكي - القيمة السوقية لأغراض التمويل (0.95x)"
_DCF_PURPOSE    = "التحليل الاستثماري - IRR / NPV / DCF"
_AIRPORT_TYPE   = "المطارات والموانئ"
_RESIDENTIAL    = "وحدة سكنية (شقة / فيلا)"

# Snapshot input — all explicit, zero hidden defaults
_SNAPSHOT_INPUT = {
    "components": [
        {
            "id": "airport-1",
            "name": "snapshot-airport",
            "asset_type": _AIRPORT_TYPE,
            "area_sqm": 100.0,
            "base_rate_per_sqm": 5000.0,
            "specific_attributes": {
                "facility_subtype": "snapshot",
                "annual_throughput": 1_000_000.0,
                "berth_or_runway_count": 2,
                "concession_years_remaining": 25.0,
            },
        },
        {
            "id": "residential-1",
            "name": "snapshot-flat",
            "asset_type": _RESIDENTIAL,
            "area_sqm": 10_000.0,
            "base_rate_per_sqm": 2_000.0,
            "specific_attributes": {
                "bedrooms_count": 3,
                "floor_number": 2,
            },
        },
    ],
    "purposes": [_MARKET_VALUE, _FINANCING_095],
}

EXPECTED_BASELINE_SNAPSHOT = {
    "composite_api_version": 1,
    "status": "ok",
    "validation": {
        "is_blocking": False,
        "blocking_count": 0,
        "advisory_count": 0,
        "issues": [],
    },
    "components": [
        {
            "component_id": "airport-1",
            "name": "snapshot-airport",
            "asset_type": _AIRPORT_TYPE,
            "purpose": _MARKET_VALUE,
            "baseline_value": 500_000.0,
            "multiplier_applied": 1.0,
            "adjusted_value": 500_000.0,
            "route": "market_baseline",
            "deep_route_deferred": False,
            "iaao_block_triggered": False,
            "uspap_standards": ["Standard 1", "Standard 2"],
            "notes": [_AIRPORT_NOTE],
        },
        {
            "component_id": "residential-1",
            "name": "snapshot-flat",
            "asset_type": _RESIDENTIAL,
            "purpose": _FINANCING_095,
            "baseline_value": 20_000_000.0,
            "multiplier_applied": 0.95,
            "adjusted_value": 19_000_000.0,
            "route": "financing_risk_haircut",
            "deep_route_deferred": False,
            "iaao_block_triggered": False,
            "uspap_standards": ["Standard 1", "Standard 2"],
            "notes": [],
        },
    ],
    "summary": {
        "component_count": 2,
        "total_baseline_value": 20_500_000.0,
        "total_adjusted_value": 19_500_000.0,
        "note": (
            "totals are a NAIVE sum — synergy / portfolio aggregation "
            "is applied in Wave 7, not here."
        ),
    },
    "aggregation": {
        "total_baseline": 20_500_000.0,
        "total_adjusted_before_synergy": 19_500_000.0,
        "synergy_adjustment_percent": 0.0,
        "synergy_adjustment_amount": 0.0,
        "total_adjusted_after_synergy": 19_500_000.0,
    },
    "uspap_reporting": {
        "standards_applied": ["Standard 1", "Standard 2"],
        "mass_appraisal_standards_present": False,
        "components_count": 2,
        "note": (
            "USPAP-aware reporting markers, aggregated from per-component standards "
            "produced by PurposeAdapter. Not a certified compliance statement."
        ),
    },
    "iaao_reporting": {
        "iaao_triggered_count": 0,
        "deep_routes_deferred_count": 0,
        "cod": None,
        "prd": None,
        "ratio_study_status": "not_computed",
        "note": (
            "COD/PRD are mass-appraisal population statistics requiring a "
            "sales-ratio dataset; the composite endpoint accepts none, so they are "
            "not computed. IAAO-style statistical support markers only — "
            "not a certified compliance statement."
        ),
    },
}

_ENDPOINT = "/api/valuation/composite"


# ─────────────────────────────────────────────────────────────────────────────
# Happy path
# ─────────────────────────────────────────────────────────────────────────────

class TestHappyPath:
    def test_200_and_status_ok(self, client, auth):
        resp = client.post(_ENDPOINT, json=_SNAPSHOT_INPUT, headers=auth)
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"

    def test_component_count(self, client, auth):
        resp = client.post(_ENDPOINT, json=_SNAPSHOT_INPUT, headers=auth)
        data = resp.get_json()
        assert len(data["components"]) == 2

    def test_adjusted_values_explicit_multipliers(self, client, auth):
        resp = client.post(_ENDPOINT, json=_SNAPSHOT_INPUT, headers=auth)
        comps = resp.get_json()["components"]
        # airport: 100 × 5000 × 1.00 = 500 000
        assert comps[0]["adjusted_value"] == 500_000.0
        # residential: 10000 × 2000 × 0.95 = 19 000 000
        assert comps[1]["adjusted_value"] == 19_000_000.0

    def test_api_version_present(self, client, auth):
        resp = client.post(_ENDPOINT, json=_SNAPSHOT_INPUT, headers=auth)
        assert resp.get_json()["composite_api_version"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# Golden snapshot (regression guard for Waves 5-7)
# ─────────────────────────────────────────────────────────────────────────────

class TestGoldenSnapshot:
    def test_full_snapshot_equality(self, client, auth):
        """The entire response must be deep-equal to the frozen snapshot.

        This test guards against silent regressions in Waves 5-7.
        Snapshot values were manually verified arithmetically before
        freezing (see module docstring).
        """
        resp = client.post(_ENDPOINT, json=_SNAPSHOT_INPUT, headers=auth)
        assert resp.status_code == 200
        assert resp.get_json() == EXPECTED_BASELINE_SNAPSHOT


# ─────────────────────────────────────────────────────────────────────────────
# Determinism
# ─────────────────────────────────────────────────────────────────────────────

class TestDeterminism:
    def test_two_calls_identical(self, client, auth):
        r1 = client.post(_ENDPOINT, json=_SNAPSHOT_INPUT, headers=auth).get_json()
        r2 = client.post(_ENDPOINT, json=_SNAPSHOT_INPUT, headers=auth).get_json()
        assert r1 == r2


# ─────────────────────────────────────────────────────────────────────────────
# Blocking validation → 422 rejected
# ─────────────────────────────────────────────────────────────────────────────

class TestBlockingValidation:
    def _bad_body(self):
        return {
            "components": [
                {
                    "id": "bad",
                    "name": "bad",
                    "asset_type": "نوع غير معروف",  # unknown
                    "area_sqm": 100.0,
                    "specific_attributes": {},
                }
            ],
            "purposes": [_MARKET_VALUE],
        }

    def test_unknown_asset_type_returns_422(self, client, auth):
        resp = client.post(_ENDPOINT, json=self._bad_body(), headers=auth)
        assert resp.status_code == 422

    def test_rejected_status(self, client, auth):
        resp = client.post(_ENDPOINT, json=self._bad_body(), headers=auth)
        assert resp.get_json()["status"] == "rejected"

    def test_rejected_has_no_components_key(self, client, auth):
        data = client.post(_ENDPOINT, json=self._bad_body(), headers=auth).get_json()
        assert "components" not in data

    def test_rejected_validation_has_blocking_issues(self, client, auth):
        data = client.post(_ENDPOINT, json=self._bad_body(), headers=auth).get_json()
        assert data["validation"]["blocking_count"] > 0
        assert data["validation"]["is_blocking"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Advisory issues visible in 200
# ─────────────────────────────────────────────────────────────────────────────

class TestAdvisory:
    def test_deep_route_advisory_in_200(self, client, auth):
        """DCF purpose (deep=True) → 200 with DEFERRED_DEEP_ROUTE advisory."""
        body = {
            "components": [
                {
                    "id": "r1",
                    "name": "x",
                    "asset_type": _RESIDENTIAL,
                    "area_sqm": 100.0,
                    "base_rate_per_sqm": 1000.0,
                    "specific_attributes": {"bedrooms_count": 2, "floor_number": 1},
                }
            ],
            "purposes": [_DCF_PURPOSE],
        }
        resp = client.post(_ENDPOINT, json=body, headers=auth)
        assert resp.status_code == 200
        data = resp.get_json()
        codes = [i["code"] for i in data["validation"]["issues"]]
        assert "DEFERRED_DEEP_ROUTE" in codes

    def test_airport_financing_coherence_advisory_200(self, client, auth):
        """Airport/ports + Financing → 200 with PURPOSE_ASSET_COHERENCE advisory.

        Kept separate from the golden snapshot which uses Market Value to keep
        the snapshot advisory-free.
        """
        body = {
            "components": [
                {
                    "id": "ap",
                    "name": "x",
                    "asset_type": _AIRPORT_TYPE,
                    "area_sqm": 100.0,
                    "base_rate_per_sqm": 1000.0,
                    "specific_attributes": {
                        "facility_subtype": "test",
                        "annual_throughput": 1e6,
                        "berth_or_runway_count": 1,
                        "concession_years_remaining": 20.0,
                    },
                }
            ],
            "purposes": [_FINANCING_095],
        }
        resp = client.post(_ENDPOINT, json=body, headers=auth)
        assert resp.status_code == 200
        data = resp.get_json()
        codes = [i["code"] for i in data["validation"]["issues"]]
        assert "PURPOSE_ASSET_COHERENCE" in codes
        # advisory only — not blocking
        assert data["validation"]["is_blocking"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Unknown purpose → 422 via validator
# ─────────────────────────────────────────────────────────────────────────────

class TestUnknownPurpose:
    def test_unknown_purpose_returns_422(self, client, auth):
        body = {
            "components": [
                {
                    "id": "r1",
                    "name": "x",
                    "asset_type": _RESIDENTIAL,
                    "area_sqm": 100.0,
                    "specific_attributes": {"bedrooms_count": 2, "floor_number": 1},
                }
            ],
            "purposes": ["غرض غير معروف مطلقاً"],
        }
        resp = client.post(_ENDPOINT, json=body, headers=auth)
        assert resp.status_code == 422
        assert resp.get_json()["status"] == "rejected"


# ─────────────────────────────────────────────────────────────────────────────
# Bad input → 400
# ─────────────────────────────────────────────────────────────────────────────

class TestBadInput:
    def test_malformed_json_400(self, client, auth):
        resp = client.post(
            _ENDPOINT,
            data=b"not-json{{{",
            content_type="application/json",
            headers=auth,
        )
        assert resp.status_code == 400

    def test_missing_body_400(self, client, auth):
        resp = client.post(_ENDPOINT, headers=auth)
        assert resp.status_code == 400

    def test_missing_components_key_400(self, client, auth):
        resp = client.post(_ENDPOINT, json={"purposes": [_MARKET_VALUE]}, headers=auth)
        assert resp.status_code == 400

    def test_missing_purposes_key_400(self, client, auth):
        resp = client.post(
            _ENDPOINT,
            json={"components": [{"asset_type": _RESIDENTIAL}]},
            headers=auth,
        )
        assert resp.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# Purpose broadcast
# ─────────────────────────────────────────────────────────────────────────────

class TestPurposeBroadcast:
    def test_single_string_applied_to_all(self, client, auth):
        """A single string purpose is broadcast to every component."""
        body = {
            "components": [
                {"id": "r1", "name": "a", "asset_type": _RESIDENTIAL,
                 "area_sqm": 100.0, "base_rate_per_sqm": 1000.0,
                 "specific_attributes": {"bedrooms_count": 2, "floor_number": 1}},
                {"id": "r2", "name": "b", "asset_type": _RESIDENTIAL,
                 "area_sqm": 200.0, "base_rate_per_sqm": 1000.0,
                 "specific_attributes": {"bedrooms_count": 3, "floor_number": 2}},
            ],
            "purposes": _MARKET_VALUE,   # single string
        }
        resp = client.post(_ENDPOINT, json=body, headers=auth)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["components"]) == 2
        assert all(c["route"] == "market_baseline" for c in data["components"])


# ─────────────────────────────────────────────────────────────────────────────
# Length mismatch
# ─────────────────────────────────────────────────────────────────────────────

class TestLengthMismatch:
    def test_mismatch_is_not_500(self, client, auth):
        body = {
            "components": [
                {"id": "r1", "name": "a", "asset_type": _RESIDENTIAL,
                 "area_sqm": 100.0, "specific_attributes": {"bedrooms_count": 2, "floor_number": 1}},
            ],
            "purposes": [_MARKET_VALUE, _FINANCING_095],  # 2 purposes, 1 component
        }
        resp = client.post(_ENDPOINT, json=body, headers=auth)
        assert resp.status_code != 500
        assert resp.status_code in (400, 422)


# ─────────────────────────────────────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────────────────────────────────────

class TestAuth:
    def test_no_token_returns_401(self, client):
        resp = client.post(_ENDPOINT, json=_SNAPSHOT_INPUT)
        assert resp.status_code == 401
        assert resp.get_json()["status"] == "unauthorized"


# ─────────────────────────────────────────────────────────────────────────────
# Summary contract
# ─────────────────────────────────────────────────────────────────────────────

class TestSummary:
    def test_totals_match_arithmetic(self, client, auth):
        resp = client.post(_ENDPOINT, json=_SNAPSHOT_INPUT, headers=auth)
        s = resp.get_json()["summary"]
        assert s["total_baseline_value"] == 20_500_000.0
        assert s["total_adjusted_value"] == 19_500_000.0

    def test_note_key_present_with_wave7_warning(self, client, auth):
        resp = client.post(_ENDPOINT, json=_SNAPSHOT_INPUT, headers=auth)
        note = resp.get_json()["summary"]["note"]
        assert "Wave 7" in note
        assert "NAIVE" in note


# ─────────────────────────────────────────────────────────────────────────────
# Aggregation block (Wave 7A)
# ─────────────────────────────────────────────────────────────────────────────

class TestAggregation:
    """Integration tests for the Wave 7A 'aggregation' response block."""

    # ── key presence ─────────────────────────────────────────────────

    def test_aggregation_key_present(self, client, auth):
        data = client.post(_ENDPOINT, json=_SNAPSHOT_INPUT, headers=auth).get_json()
        assert "aggregation" in data

    def test_aggregation_has_all_five_fields(self, client, auth):
        agg = client.post(_ENDPOINT, json=_SNAPSHOT_INPUT, headers=auth).get_json()["aggregation"]
        for key in (
            "total_baseline",
            "total_adjusted_before_synergy",
            "synergy_adjustment_percent",
            "synergy_adjustment_amount",
            "total_adjusted_after_synergy",
        ):
            assert key in agg, f"Missing field: {key!r}"

    # ── zero synergy (default — no synergy_adjustment_percent in body) ────

    def test_default_zero_synergy_percent(self, client, auth):
        agg = client.post(_ENDPOINT, json=_SNAPSHOT_INPUT, headers=auth).get_json()["aggregation"]
        assert agg["synergy_adjustment_percent"] == 0.0

    def test_default_zero_synergy_amount(self, client, auth):
        agg = client.post(_ENDPOINT, json=_SNAPSHOT_INPUT, headers=auth).get_json()["aggregation"]
        assert agg["synergy_adjustment_amount"] == 0.0

    def test_default_zero_after_equals_before(self, client, auth):
        agg = client.post(_ENDPOINT, json=_SNAPSHOT_INPUT, headers=auth).get_json()["aggregation"]
        assert agg["total_adjusted_after_synergy"] == agg["total_adjusted_before_synergy"]

    # ── arithmetic snapshot (zero synergy) ───────────────────────────

    def test_aggregation_arithmetic_snapshot(self, client, auth):
        """
        Manual verification (same as golden snapshot comment):
          airport:     100 × 5000 × 1.00  =   500_000 baseline / adjusted
          residential: 10000 × 2000 × 0.95 = 19_000_000 adjusted
          total_baseline  = 500_000 + 20_000_000 = 20_500_000
          total_before    = 500_000 + 19_000_000 = 19_500_000
          synergy_pct     = 0.0  →  amount = 0.0
          total_after     = 19_500_000
        """
        agg = client.post(_ENDPOINT, json=_SNAPSHOT_INPUT, headers=auth).get_json()["aggregation"]
        assert agg["total_baseline"] == 20_500_000.0
        assert agg["total_adjusted_before_synergy"] == 19_500_000.0
        assert agg["synergy_adjustment_percent"] == 0.0
        assert agg["synergy_adjustment_amount"] == 0.0
        assert agg["total_adjusted_after_synergy"] == 19_500_000.0

    # ── positive synergy ─────────────────────────────────────────────

    def test_positive_synergy_increases_after_total(self, client, auth):
        """
        total_adjusted_before = 19_500_000
        synergy 5% → amount = 975_000 → after = 20_475_000
        """
        body = {**_SNAPSHOT_INPUT, "synergy_adjustment_percent": 5.0}
        agg = client.post(_ENDPOINT, json=body, headers=auth).get_json()["aggregation"]
        assert agg["synergy_adjustment_percent"] == 5.0
        assert agg["synergy_adjustment_amount"] == pytest.approx(975_000.0)
        assert agg["total_adjusted_after_synergy"] == pytest.approx(20_475_000.0)
        assert agg["total_adjusted_after_synergy"] > agg["total_adjusted_before_synergy"]

    # ── negative synergy ─────────────────────────────────────────────

    def test_negative_synergy_decreases_after_total(self, client, auth):
        """
        total_adjusted_before = 19_500_000
        synergy -10% → amount = -1_950_000 → after = 17_550_000
        """
        body = {**_SNAPSHOT_INPUT, "synergy_adjustment_percent": -10.0}
        agg = client.post(_ENDPOINT, json=body, headers=auth).get_json()["aggregation"]
        assert agg["synergy_adjustment_percent"] == -10.0
        assert agg["synergy_adjustment_amount"] == pytest.approx(-1_950_000.0)
        assert agg["total_adjusted_after_synergy"] == pytest.approx(17_550_000.0)
        assert agg["total_adjusted_after_synergy"] < agg["total_adjusted_before_synergy"]

    # ── invalid synergy input → 422 ──────────────────────────────────

    def test_string_synergy_returns_422(self, client, auth):
        body = {**_SNAPSHOT_INPUT, "synergy_adjustment_percent": "five"}
        resp = client.post(_ENDPOINT, json=body, headers=auth)
        assert resp.status_code == 422

    def test_bool_synergy_returns_422(self, client, auth):
        body = {**_SNAPSHOT_INPUT, "synergy_adjustment_percent": True}
        resp = client.post(_ENDPOINT, json=body, headers=auth)
        assert resp.status_code == 422

    # ── summary block backward-compat ────────────────────────────────

    def test_summary_total_baseline_value_unchanged(self, client, auth):
        """summary.total_baseline_value must equal aggregation.total_baseline."""
        data = client.post(_ENDPOINT, json=_SNAPSHOT_INPUT, headers=auth).get_json()
        assert data["summary"]["total_baseline_value"] == data["aggregation"]["total_baseline"]

    def test_summary_total_adjusted_value_unchanged(self, client, auth):
        """summary.total_adjusted_value must equal aggregation.total_adjusted_before_synergy."""
        data = client.post(_ENDPOINT, json=_SNAPSHOT_INPUT, headers=auth).get_json()
        assert (
            data["summary"]["total_adjusted_value"]
            == data["aggregation"]["total_adjusted_before_synergy"]
        )


# ─────────────────────────────────────────────────────────────────────────────
# Reporting blocks (Wave 7B)
# ─────────────────────────────────────────────────────────────────────────────

class TestReportingBlocks:
    """Integration tests for the Wave 7B uspap_reporting / iaao_reporting blocks."""

    def test_uspap_reporting_present_in_200(self, client, auth):
        data = client.post(_ENDPOINT, json=_SNAPSHOT_INPUT, headers=auth).get_json()
        assert "uspap_reporting" in data

    def test_iaao_reporting_present_in_200(self, client, auth):
        data = client.post(_ENDPOINT, json=_SNAPSHOT_INPUT, headers=auth).get_json()
        assert "iaao_reporting" in data

    def test_standards_applied_snapshot(self, client, auth):
        r = client.post(_ENDPOINT, json=_SNAPSHOT_INPUT, headers=auth).get_json()
        assert r["uspap_reporting"]["standards_applied"] == ["Standard 1", "Standard 2"]

    def test_mass_appraisal_false_for_non_tax_snapshot(self, client, auth):
        r = client.post(_ENDPOINT, json=_SNAPSHOT_INPUT, headers=auth).get_json()
        assert r["uspap_reporting"]["mass_appraisal_standards_present"] is False

    def test_cod_null_default(self, client, auth):
        r = client.post(_ENDPOINT, json=_SNAPSHOT_INPUT, headers=auth).get_json()
        assert r["iaao_reporting"]["cod"] is None

    def test_prd_null_default(self, client, auth):
        r = client.post(_ENDPOINT, json=_SNAPSHOT_INPUT, headers=auth).get_json()
        assert r["iaao_reporting"]["prd"] is None

    def test_iaao_triggered_count_zero_snapshot(self, client, auth):
        r = client.post(_ENDPOINT, json=_SNAPSHOT_INPUT, headers=auth).get_json()
        assert r["iaao_reporting"]["iaao_triggered_count"] == 0

    def test_deep_routes_deferred_count_zero_snapshot(self, client, auth):
        r = client.post(_ENDPOINT, json=_SNAPSHOT_INPUT, headers=auth).get_json()
        assert r["iaao_reporting"]["deep_routes_deferred_count"] == 0

    def test_422_blocking_has_no_uspap_reporting(self, client, auth):
        bad = {
            "components": [
                {"id": "b", "name": "b", "asset_type": "نوع غير معروف",
                 "area_sqm": 100.0, "specific_attributes": {}}
            ],
            "purposes": [_MARKET_VALUE],
        }
        data = client.post(_ENDPOINT, json=bad, headers=auth).get_json()
        assert data["status"] == "rejected"
        assert "uspap_reporting" not in data
        assert "iaao_reporting" not in data
