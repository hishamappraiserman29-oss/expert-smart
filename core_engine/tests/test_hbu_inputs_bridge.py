"""
Tests — HBU Inputs Sourcing Bridge (hbu_inputs_bridge.py) — Wave 1B.

Safety scope
------------
• Tests only the additive bridge module.
• Engines (mass_appraisal, enrichment) used READ-ONLY via public API.
• Deterministic: enrichment uses MockMarketProvider (use_mock_enrichment=True)
  unless a stub layer is injected.
• No network calls, no absolute paths, no real customer data,
  no project-tree outputs.

HB01  Mass appraisal is PRIMARY source — tier=internal_primary, status=approved_internal.
HB02  Enrichment stays DRAFT — pending_human_review, cannot generate final report.
HB03  No fabrication — missing inputs in `unavailable`, never invented.
HB04  Provenance table covers every produced input.
HB05  Conflict reconciliation prefers mass appraisal, records note.
HB06  Governance flags: advisory_only, engines_readonly, no model training.
HB07  No comparable units → mass appraisal not used, no crash, no fabrication.
HB08  Enrichment source restricted to Egypt + SA request → unavailable (geography_unsupported).
HB09  No ratio study → confidence=None with status/reason (no fixed 65% heuristic).
HB10  base_market_ppm=0 (missing default) is a Neutral Sentinel — avg_ppm unchanged.
HB11  Enrichment disabled by default → all enrichment fields → enrichment_not_enabled.
HB12  Explicit enrichment_layer injection — injected layer is used, no second layer.
HB13  Internal temp directory cleaned up after call (work_dir=None).
HB14  Caller-supplied work_dir not deleted by module.
HB15  comparable_units=[] (explicit empty list) → mass appraisal not called.
HB16  run_mass_appraisal exception propagates — no fabricated fallback.
HB17  enrichment_layer.enrich() exception propagates — no partial success.
HB18  Input case dict not mutated by build_hbu_inputs.
HB19  case_id does not leak into source_name or reconciliation_note.
"""
from __future__ import annotations

import copy
import glob
import os
import sys
import tempfile
import unittest.mock as mock

import pytest

# ── bootstrap import path ─────────────────────────────────────────────────────
_CORE_ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _CORE_ENGINE not in sys.path:
    sys.path.insert(0, _CORE_ENGINE)

from hbu_inputs_bridge import (  # noqa: E402
    STATUS_APPROVED_INT,
    STATUS_DRAFT,
    TIER_INTERNAL_PRIMARY,
    build_hbu_inputs,
)

try:
    from enrichment.market_enrichment import MarketEnrichmentLayer  # type: ignore
except ImportError:
    from core_engine.enrichment.market_enrichment import MarketEnrichmentLayer  # type: ignore


# ── Fixtures and helpers ──────────────────────────────────────────────────────

def _case() -> dict:
    """QA fixture — Riyadh land parcel with 3 comparables (no sale_price → no ratio study)."""
    return {
        "case_id": "QA-HBU-BRIDGE-001",
        "country_code": "SA",
        "region": "SA",
        "city": "Riyadh",
        "district": "النرجس",
        "asset_type": "residential",
        "valuation_purpose": "market_value",
        "land_area_m2": 2400,
        "comparable_units": [
            {"id": "C1", "area": 400, "floor": 0, "year_built": 2015, "condition": "good"},
            {"id": "C2", "area": 500, "floor": 0, "year_built": 2018, "condition": "excellent"},
            {"id": "C3", "area": 450, "floor": 0, "year_built": 2016, "condition": "good"},
        ],
    }


def _case_no_comps() -> dict:
    """Fixture without comparable_units — mass appraisal not triggered."""
    c = _case()
    c.pop("comparable_units")
    return c


@pytest.fixture()
def result():
    return build_hbu_inputs(_case(), use_mock_enrichment=True)


# ── HB01-HB07: Original governance tests (updated for new API) ───────────────

def test_hb01_mass_appraisal_is_primary(result):
    assert result["mass_appraisal"]["used"] is True
    ppm = result["inputs"].get("price_per_m2")
    assert ppm is not None
    assert ppm["source_kind"] == "mass_appraisal"
    assert ppm["tier"] == TIER_INTERNAL_PRIMARY
    assert ppm["status"] == STATUS_APPROVED_INT
    assert isinstance(ppm["value"], (int, float)) and ppm["value"] > 0


def test_hb02_enrichment_stays_draft(result):
    draft = result["enrichment_draft"]
    assert draft["approval_status"] == "pending_human_review"
    assert draft["can_generate_final_report"] is False
    assert result["governance"]["enrichment_is_draft"] is True
    assert result["governance"]["web_data_status"] == "draft_pending_review"


def test_hb03_no_fabrication_for_missing(result):
    missing_keys = {u["input"] for u in result["unavailable"]}
    assert {"rent_per_m2", "cap_rate_range", "market_vacancy_rate"} <= missing_keys
    for k in ("rent_per_m2", "cap_rate_range", "market_vacancy_rate"):
        assert k not in result["inputs"]
    assert all(u.get("reason") for u in result["unavailable"])


def test_hb04_provenance_covers_all_inputs(result):
    prov_inputs = {p["input"] for p in result["provenance"]}
    assert prov_inputs == set(result["inputs"].keys())
    for p in result["provenance"]:
        assert p["source_name"] and p["tier"] and p["status"]


def test_hb05_conflict_prefers_mass_appraisal(result):
    # Mock enrichment DOES suggest comp_avg_price_m2; mass appraisal must win.
    ppm = result["inputs"]["price_per_m2"]
    assert ppm["source_kind"] == "mass_appraisal"
    assert "المجمع" in ppm["reconciliation_note"]


def test_hb06_governance_flags(result):
    gov = result["governance"]
    assert gov["advisory_only"] is True
    assert gov["engines_readonly"] is True
    assert gov["web_trains_model"] is False
    assert gov["fake_official_data"] is False
    assert gov["primary_source"] == "mass_appraisal"


def test_hb07_bridge_without_comparables_no_crash_no_fabrication():
    case = _case_no_comps()
    res = build_hbu_inputs(case, use_mock_enrichment=True)
    assert res["mass_appraisal"]["used"] is False
    ppm = res["inputs"].get("price_per_m2")
    if ppm is not None:
        assert ppm["status"] == STATUS_DRAFT


# ── HB08: Geography guard ─────────────────────────────────────────────────────

class _EgyptSourceStub:
    """Stub that returns Egyptian pricing under source_name=EgyptianPriceRangeDictionary."""

    @property
    def name(self) -> str:
        return "EgyptSourceStub"

    def fetch(self, request) -> dict:
        try:
            from enrichment.source_log import make_local_static_entry  # type: ignore
        except ImportError:
            from core_engine.enrichment.source_log import make_local_static_entry  # type: ignore
        entry = make_local_static_entry(
            source_name="EgyptianPriceRangeDictionary",
            district=request.district or request.city,
            city=request.city,
            region=request.region,
            country_code=request.country_code,
            confidence=70.0,
            notes="Geography test stub",
        )
        return {
            "suggested_values": {
                "comp_avg_price_m2": 12_000.0,
                "market_vacancy_rate": None,
                "rent_per_m2": None,
                "cap_rate_range": None,
            },
            "comparable_suggestions": [],
            "market_indicators": {
                "price_range_lo": 10_000.0,
                "price_range_hi": 14_000.0,
            },
            "source_log": [entry],
            "warnings": [],
        }


def test_hb08_unsupported_geography():
    """Egyptian source for SA request → enrichment values go to unavailable, not inputs."""
    layer = MarketEnrichmentLayer(providers=[_EgyptSourceStub()])
    case = _case_no_comps()
    res = build_hbu_inputs(case, enrichment_layer=layer)

    assert "price_per_m2" not in res["inputs"]
    by_input = {u["input"]: u["reason"] for u in res["unavailable"]}
    assert by_input.get("price_per_m2") == "enrichment_geography_unsupported"
    for field in ("rent_per_m2", "cap_rate_range", "market_vacancy_rate"):
        assert by_input.get(field) == "enrichment_geography_unsupported"


# ── HB09: Confidence from ratio study only ───────────────────────────────────

def test_hb09_missing_ratio_study_confidence_none():
    """No sale_price → n_sales=0 → confidence=None, NOT the old 65% heuristic."""
    res = build_hbu_inputs(_case(), use_mock_enrichment=True)
    ppm = res["inputs"].get("price_per_m2")
    assert ppm is not None
    # No ratio study in _case() fixture (no sale_price on comparables)
    assert res["mass_appraisal"]["ratio_study"]["n_sales"] == 0
    assert ppm["confidence"] is None
    assert ppm.get("confidence_status") == "unavailable"
    assert ppm.get("confidence_reason") == "ratio_study_missing"
    # Provenance row must propagate the same fields
    prov = {p["input"]: p for p in res["provenance"]}
    assert prov["price_per_m2"].get("confidence_reason") == "ratio_study_missing"


# ── HB10: base_market_ppm Neutral Sentinel ───────────────────────────────────

def test_hb10_base_market_ppm_neutral_sentinel():
    """
    base_market_ppm=0 (missing default) has no effect on avg_ppm.
    Confirmed by reading _market_adjustment: market_ppm param is accepted but never used.
    Also verified that an arbitrary non-zero value produces the same avg_ppm.
    """
    case_zero = copy.deepcopy(_case())
    case_zero["base_market_ppm"] = 0

    case_missing = copy.deepcopy(_case())
    # No base_market_ppm key at all

    case_nonzero = copy.deepcopy(_case())
    case_nonzero["base_market_ppm"] = 99_999

    res_zero    = build_hbu_inputs(case_zero,    use_mock_enrichment=True)
    res_missing = build_hbu_inputs(case_missing, use_mock_enrichment=True)
    res_nonzero = build_hbu_inputs(case_nonzero, use_mock_enrichment=True)

    ppm_zero    = res_zero["inputs"]["price_per_m2"]["value"]
    ppm_missing = res_missing["inputs"]["price_per_m2"]["value"]
    ppm_nonzero = res_nonzero["inputs"]["price_per_m2"]["value"]

    assert ppm_zero == ppm_missing, (
        f"Explicit 0 vs missing base_market_ppm changed avg_ppm: {ppm_zero} vs {ppm_missing}"
    )
    assert ppm_nonzero == ppm_missing, (
        f"base_market_ppm=99999 changed avg_ppm: {ppm_nonzero} vs {ppm_missing}. "
        "If this fails, _market_adjustment no longer ignores market_ppm — use Path A handling."
    )


# ── HB11: Enrichment disabled by default ─────────────────────────────────────

def test_hb11_enrichment_disabled_by_default():
    """No layer, enable_enrichment=False, use_mock_enrichment=False → no providers, all unavailable."""
    case = _case_no_comps()
    res = build_hbu_inputs(case)  # all defaults

    by_input = {u["input"]: u["reason"] for u in res["unavailable"]}
    for field in ("price_per_m2", "rent_per_m2", "cap_rate_range", "market_vacancy_rate"):
        assert field in by_input, f"Expected {field!r} in unavailable"
        assert by_input[field] == "enrichment_not_enabled", (
            f"{field}: got reason {by_input[field]!r}, expected 'enrichment_not_enabled'"
        )
    assert res["enrichment_draft"].get("status") == "enrichment_not_enabled"
    assert res["governance"]["enrichment_is_draft"] is False


# ── HB12: Explicit enrichment_layer injection ────────────────────────────────

def test_hb12_explicit_enrichment_injection():
    """Injected enrichment_layer is called once; no second MarketEnrichmentLayer created."""
    call_log: list = []

    class _TrackingLayer:
        def enrich(self, request):
            call_log.append(request)
            return MarketEnrichmentLayer(use_mock=True).enrich(request)

    case = _case_no_comps()
    res = build_hbu_inputs(case, enrichment_layer=_TrackingLayer())

    assert len(call_log) == 1, f"Expected 1 enrich() call, got {len(call_log)}"
    assert res["enrichment_draft"].get("approval_status") == "pending_human_review"
    assert res["governance"]["enrichment_is_draft"] is True


# ── HB13: Internal temp directory cleaned up ─────────────────────────────────

def test_hb13_internal_tmp_cleanup():
    """work_dir=None → auto-temp directory is deleted after call completes."""
    tmp_root = tempfile.gettempdir()
    before = set(glob.glob(os.path.join(tmp_root, "hbu_ma_*")))

    build_hbu_inputs(_case(), use_mock_enrichment=True)  # work_dir=None

    after = set(glob.glob(os.path.join(tmp_root, "hbu_ma_*")))
    new_dirs = after - before
    assert not new_dirs, f"Temp dirs not cleaned up after call: {new_dirs}"


# ── HB14: Caller-supplied work_dir not deleted ───────────────────────────────

def test_hb14_caller_work_dir_not_deleted():
    """Module must not delete a caller-supplied work_dir."""
    with tempfile.TemporaryDirectory(prefix="hb14_test_") as caller_dir:
        build_hbu_inputs(_case(), use_mock_enrichment=True, work_dir=caller_dir)
        assert os.path.isdir(caller_dir), "Module deleted the caller-supplied work_dir"


# ── HB15: Explicit empty comparable_units ────────────────────────────────────

def test_hb15_empty_comparables_no_mass_appraisal():
    """comparable_units=[] (explicit empty) → mass appraisal not triggered, used=False."""
    case = _case()
    case["comparable_units"] = []
    res = build_hbu_inputs(case, use_mock_enrichment=True)
    assert res["mass_appraisal"]["used"] is False
    assert res["mass_appraisal"]["n_units"] == 0


# ── HB16: Mass appraisal exception propagates ────────────────────────────────

def test_hb16_mass_appraisal_exception_propagates():
    """run_mass_appraisal raising must propagate — no fabricated enrichment fallback."""
    case = _case()
    with mock.patch("hbu_inputs_bridge.run_mass_appraisal", side_effect=RuntimeError("MA_FAILURE")):
        with pytest.raises(RuntimeError, match="MA_FAILURE"):
            build_hbu_inputs(case, use_mock_enrichment=True)


# ── HB17: Enrichment exception propagates ────────────────────────────────────

def test_hb17_enrichment_exception_propagates():
    """enrichment_layer.enrich() raising must propagate — no partial success masking it."""
    bad_layer = mock.MagicMock()
    bad_layer.enrich.side_effect = RuntimeError("ENR_FAILURE")

    case = _case_no_comps()
    with pytest.raises(RuntimeError, match="ENR_FAILURE"):
        build_hbu_inputs(case, enrichment_layer=bad_layer)


# ── HB18: Input case dict is not mutated ─────────────────────────────────────

def test_hb18_input_case_immutable():
    """build_hbu_inputs must not modify the caller's case dict."""
    case = _case()
    snapshot = copy.deepcopy(case)
    build_hbu_inputs(case, use_mock_enrichment=True)
    assert case == snapshot, "case dict was mutated by build_hbu_inputs"


# ── HB19: case_id does not leak into source metadata ─────────────────────────

def test_hb19_identifier_not_leaked_to_source_metadata():
    """case_id must not appear in source_name, model_or_uri, or reconciliation_note."""
    case = _case()
    case["case_id"] = "CONFIDENTIAL-CLIENT-7890"
    res = build_hbu_inputs(case, use_mock_enrichment=True)

    _marker = "CONFIDENTIAL-CLIENT-7890"
    for p in res["provenance"]:
        assert _marker not in str(p.get("source_name", "")), \
            f"case_id leaked into provenance source_name: {p}"
        assert _marker not in str(p.get("reconciliation_note", "")), \
            f"case_id leaked into reconciliation_note: {p}"
        assert _marker not in str(p.get("model_or_uri", "")), \
            f"case_id leaked into model_or_uri: {p}"

    for log in res["enrichment_draft"].get("data_source_log", []):
        assert _marker not in str(log), f"case_id leaked into enrichment source log: {log}"
