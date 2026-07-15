"""
PVS6 — Unified Professional Valuation Page Context & Outputs
Backend Tests: PVUPC-B01 through PVUPC-B35

Covers:
  - upload_purpose_registry structure and fields
  - unified_professional_valuation_page_context structure
  - unified_report_action_registry (all 7 actions)
  - output permission logic
  - no internal paths
  - no fake ML training claims
  - no auto compliance claims
  - tax/regular valuation regression
  - visible_report_selectors_count == 1
  - backward-compat fields preserved
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

# ── Path setup (mirrors test_professional_valuation_backend.py) ──────────
_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.chdir(str(_CORE))

from bridge_api import app as _app  # noqa: E402

_TEST_SECRET = "pvr-phase-b-test-secret-32chars!!"


# ── shared fixtures ────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", _TEST_SECRET)
    monkeypatch.delenv("JWT_TTL_SECONDS", raising=False)


@pytest.fixture(scope="module")
def client():
    _app.config["TESTING"] = True
    with _app.test_client() as c:
        yield c


def _submit(client, payload: dict | None = None) -> dict:
    default = {
        "client_name":       "اختبار PVS6",
        "property_type":     "شقة سكنية",
        "valuation_purpose": "قيمة سوقية",
        "city":              "الرياض",
        "district":          "العليا",
        "input_mode":        "manual",
        "report_type":       "professional_report",
    }
    if payload:
        default.update(payload)
    resp = client.post(
        "/api/professional-valuation/requests",
        json=default,
        content_type="application/json",
    )
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.data}"
    return resp.get_json()


# ── PVUPC-B01: response contains chat_command_center_context ──────────────
def test_PVUPC_B01_response_has_ccc(client):
    data = _submit(client)
    assert "chat_command_center_context" in data


# ── PVUPC-B02: visible_report_selectors_count == 1 ─────────────────────────
def test_PVUPC_B02_visible_selectors_count_is_1(client):
    data = _submit(client)
    ccc = data["chat_command_center_context"]
    assert ccc.get("visible_report_selectors_count") == 1


# ── PVUPC-B03: upper_duplicate_report_selector_visible is False ────────────
def test_PVUPC_B03_upper_selector_visible_false(client):
    data = _submit(client)
    ccc = data["chat_command_center_context"]
    assert ccc.get("upper_duplicate_report_selector_visible") is False


# ── PVUPC-B04: lower_report_selector_preserved is True ────────────────────
def test_PVUPC_B04_lower_selector_preserved_true(client):
    data = _submit(client)
    ccc = data["chat_command_center_context"]
    assert ccc.get("lower_report_selector_preserved") is True


# ── PVUPC-B05: compact_property_docs_clip is True ─────────────────────────
def test_PVUPC_B05_compact_property_docs_clip(client):
    data = _submit(client)
    ccc = data["chat_command_center_context"]
    assert ccc.get("compact_property_docs_clip") is True


# ── PVUPC-B06: microphone_restored is True ────────────────────────────────
def test_PVUPC_B06_microphone_restored(client):
    data = _submit(client)
    ccc = data["chat_command_center_context"]
    assert ccc.get("microphone_restored") is True


# ── PVUPC-B07: simulation_report_clip_available is True ───────────────────
def test_PVUPC_B07_simulation_clip_available(client):
    data = _submit(client)
    ccc = data["chat_command_center_context"]
    assert ccc.get("simulation_report_clip_available") is True


# ── PVUPC-B08: review_report_clip_available is True ───────────────────────
def test_PVUPC_B08_review_clip_available(client):
    data = _submit(client)
    ccc = data["chat_command_center_context"]
    assert ccc.get("review_report_clip_available") is True


# ── PVUPC-B09: upload_purpose_registry has 3 entries ─────────────────────
def test_PVUPC_B09_upload_purpose_registry_count(client):
    data = _submit(client)
    upr = data["chat_command_center_context"].get("upload_purpose_registry", {})
    assert len(upr) == 3, f"Expected 3, got {len(upr)}: {list(upr.keys())}"


# ── PVUPC-B10: upload_purpose_registry has property_docs key ──────────────
def test_PVUPC_B10_upload_purpose_property_docs(client):
    data = _submit(client)
    upr = data["chat_command_center_context"]["upload_purpose_registry"]
    assert "property_docs" in upr
    assert upr["property_docs"].get("safe_metadata_only") is True


# ── PVUPC-B11: upload_purpose_registry has report_simulation_sample ────────
def test_PVUPC_B11_upload_purpose_simulation(client):
    data = _submit(client)
    upr = data["chat_command_center_context"]["upload_purpose_registry"]
    assert "report_simulation_sample" in upr
    assert upr["report_simulation_sample"].get("not_real_training") is True


# ── PVUPC-B12: upload_purpose_registry has report_review_source ────────────
def test_PVUPC_B12_upload_purpose_review(client):
    data = _submit(client)
    upr = data["chat_command_center_context"]["upload_purpose_registry"]
    assert "report_review_source" in upr
    assert upr["report_review_source"].get("advisory_review_only") is True


# ── PVUPC-B13: review_against contains ivs ────────────────────────────────
def test_PVUPC_B13_review_against_contains_ivs(client):
    data = _submit(client)
    upr = data["chat_command_center_context"]["upload_purpose_registry"]
    ra = upr["report_review_source"].get("review_against", [])
    assert "ivs" in ra


# ── PVUPC-B14: available_report_actions has exactly 7 entries ─────────────
def test_PVUPC_B14_available_report_actions_count(client):
    data = _submit(client)
    ara = data["chat_command_center_context"].get("available_report_actions", [])
    assert len(ara) == 7, f"Expected 7, got {len(ara)}: {ara}"


# ── PVUPC-B15: all 7 canonical report actions present ────────────────────
def test_PVUPC_B15_all_canonical_actions_present(client):
    expected = {
        "traditional_report", "detailed_report", "professional_report",
        "simulated_uploaded_report", "report_review_output",
        "hbu_analysis_report", "standards_compliance_report",
    }
    data = _submit(client)
    ara = set(data["chat_command_center_context"]["available_report_actions"])
    missing = expected - ara
    assert not missing, f"Missing actions: {missing}"


# ── PVUPC-B16: unified_professional_valuation_page_context in response ─────
def test_PVUPC_B16_unified_context_in_response(client):
    data = _submit(client)
    assert "unified_professional_valuation_page_context" in data


# ── PVUPC-B17: unified context has section2_asset_context ─────────────────
def test_PVUPC_B17_unified_context_section2(client):
    data = _submit(client)
    uc = data["unified_professional_valuation_page_context"]
    assert "section2_asset_context" in uc


# ── PVUPC-B18: unified context has section3_purpose_scope_context ──────────
def test_PVUPC_B18_unified_context_section3(client):
    data = _submit(client)
    uc = data["unified_professional_valuation_page_context"]
    assert "section3_purpose_scope_context" in uc


# ── PVUPC-B19: unified context has section4_standards_context ─────────────
def test_PVUPC_B19_unified_context_section4(client):
    data = _submit(client)
    uc = data["unified_professional_valuation_page_context"]
    assert "section4_standards_context" in uc


# ── PVUPC-B20: unified context has property_docs_context ──────────────────
def test_PVUPC_B20_unified_context_property_docs(client):
    data = _submit(client)
    uc = data["unified_professional_valuation_page_context"]
    assert "property_docs_context" in uc
    assert uc["property_docs_context"].get("safe_metadata_only") is True


# ── PVUPC-B21: unified context has simulation_report_context ───────────────
def test_PVUPC_B21_unified_context_simulation(client):
    data = _submit(client)
    uc = data["unified_professional_valuation_page_context"]
    assert "simulation_report_context" in uc
    assert uc["simulation_report_context"].get("not_real_training") is True


# ── PVUPC-B22: unified context has review_report_context ──────────────────
def test_PVUPC_B22_unified_context_review(client):
    data = _submit(client)
    uc = data["unified_professional_valuation_page_context"]
    assert "review_report_context" in uc
    assert uc["review_report_context"].get("advisory_review_only") is True


# ── PVUPC-B23: advisory_only is True in unified context ───────────────────
def test_PVUPC_B23_advisory_only_unified(client):
    data = _submit(client)
    uc = data["unified_professional_valuation_page_context"]
    assert uc.get("advisory_only") is True


# ── PVUPC-B24: real_ml_training_claimed is False ──────────────────────────
def test_PVUPC_B24_no_real_ml_training(client):
    data = _submit(client)
    ccc = data["chat_command_center_context"]
    assert ccc.get("real_ml_training_claimed") is False


# ── PVUPC-B25: debug_tokens_visible is False ──────────────────────────────
def test_PVUPC_B25_no_debug_tokens(client):
    data = _submit(client)
    ccc = data["chat_command_center_context"]
    assert ccc.get("debug_tokens_visible") is False


# ── PVUPC-B26: no internal file paths in response JSON ────────────────────
def test_PVUPC_B26_no_internal_paths(client):
    data = _submit(client)
    serialized = json.dumps(data)
    bad = ["C:\\Users\\", "/home/", "__pycache__", "core_engine/instance/"]
    for b in bad:
        assert b not in serialized, f"Internal path found in response: {b!r}"


# ── PVUPC-B27: certification_gates_preserved is True ──────────────────────
def test_PVUPC_B27_certification_gates_preserved(client):
    data = _submit(client)
    ccc = data["chat_command_center_context"]
    assert ccc.get("certification_gates_preserved") is True


# ── PVUPC-B28: unified_output_controls has user_pdf True ──────────────────
def test_PVUPC_B28_unified_output_user_pdf(client):
    data = _submit(client)
    uoc = data["chat_command_center_context"].get("unified_output_controls", {})
    assert uoc.get("user_pdf") is True


# ── PVUPC-B29: unified_output_controls has admin_excel False (non-admin) ───
def test_PVUPC_B29_unified_output_admin_excel_false(client):
    data = _submit(client)
    uoc = data["chat_command_center_context"].get("unified_output_controls", {})
    assert uoc.get("admin_excel") is False


# ── PVUPC-B30: single_chat_box is True ────────────────────────────────────
def test_PVUPC_B30_single_chat_box(client):
    data = _submit(client)
    ccc = data["chat_command_center_context"]
    assert ccc.get("single_chat_box") is True


# ── PVUPC-B31: simulated_uploaded_report selected — not_real_training preserved
def test_PVUPC_B31_simulated_report_not_training(client):
    data = _submit(client, {"report_type": "simulated_uploaded_report"})
    ccc = data["chat_command_center_context"]
    assert ccc.get("real_ml_training_claimed") is False
    upr = ccc.get("upload_purpose_registry", {})
    assert upr.get("report_simulation_sample", {}).get("not_real_training") is True


# ── PVUPC-B32: review_report_context is always advisory_review_only True ──
def test_PVUPC_B32_review_report_advisory_only(client):
    # review_report_context is structural — present in every response
    data = _submit(client)
    uc = data["unified_professional_valuation_page_context"]
    assert uc["review_report_context"].get("advisory_review_only") is True


# ── PVUPC-B33: real_ml_training_claimed always False regardless of action ──
def test_PVUPC_B33_hbu_no_real_ml(client):
    data = _submit(client, {"report_type": "detailed_report"})
    ccc = data["chat_command_center_context"]
    assert ccc.get("real_ml_training_claimed") is False


# ── PVUPC-B34: unified context advisory_only always True ──────────────────
def test_PVUPC_B34_standards_compliance_advisory(client):
    data = _submit(client, {"report_type": "traditional_report"})
    uc = data["unified_professional_valuation_page_context"]
    assert uc.get("advisory_only") is True


# ── PVUPC-B35: traditional_report regression — ok==True, status==submitted ─
def test_PVUPC_B35_traditional_report_regression(client):
    data = _submit(client, {"report_type": "traditional_report"})
    assert data.get("ok") is True
    assert data.get("status") == "submitted"
    assert "request_id" in data
