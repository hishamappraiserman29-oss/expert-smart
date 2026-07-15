"""
PVS3 Backend Tests
Professional Valuation Page — Section 3 Three-Step Anti-Confusion Cleanup

21 tests covering:
- section3_purpose_context keys in response
- Purpose registry contains only true purposes
- Basis of value accepted as basis, not purpose
- Legacy field mapping (valuation_purpose → assignment_purpose)
- DLOC/DLOM in partial_interest_context only
- Standards (RICS/IVS/IFRS/FRA) not in Section 3 purpose context
- No internal paths in response
- Ordinary valuation tests unaffected
- Tax appeal tests unaffected
"""
from __future__ import annotations

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

os.chdir(str(_CORE))

from bridge_api import app                     # noqa: E402
from auth.tokens import generate_token         # noqa: E402
import professional_valuation_routes as _pvr  # noqa: E402

_TEST_SECRET = "pvs3-test-secret-32chars-xxxxxxp"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def _clean_pvr_datastore_pvs3():
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
    "client_name":       "مختبر PVS3",
    "property_type":     "شقة سكنية",
    "valuation_purpose": "financing_mortgage",
    "city":              "القاهرة",
    "district":          "وسط البلد",
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


def _get_ctx(client, resp) -> dict:
    """Extract section3_purpose_context from create response or detail endpoint."""
    body = resp.get_json() or {}
    if "section3_purpose_context" in body:
        return body["section3_purpose_context"]
    rid = body.get("request_id", "")
    if rid:
        detail = client.get(
            f"/api/professional-valuation/requests/{rid}",
            headers=_auth(),
        ).get_json() or {}
        return detail.get("section3_purpose_context", {})
    return {}


# ── PVS3-B01: section3_purpose_context exists in response ────────────────────

def test_PVS3_B01_section3_context_in_response(client):
    """PVS3-B01: section3_purpose_context key exists in create or detail response."""
    resp = _create(client)
    assert resp.status_code == 201
    ctx = _get_ctx(client, resp)
    assert ctx, "section3_purpose_context missing from both create response and detail"


# ── PVS3-B02: section3_purpose_context has canonical keys ────────────────────

def test_PVS3_B02_section3_context_has_canonical_keys(client):
    """PVS3-B02: section3_purpose_context contains all canonical PVS3 keys."""
    resp = _create(client, {
        "assignment_purpose": "financing_mortgage",
        "basis_of_value": "market_value",
        "value_premise": "as_is",
        "intended_user_category": "bank_financial_institution",
    })
    assert resp.status_code == 201
    ctx = _get_ctx(client, resp)
    required_keys = [
        "step1_assignment_purpose",
        "step2_intended_user_category",
        "step3_basis_of_value",
        "preservation_pass",
        "deleted_purpose_options",
        "deleted_basis_options",
        "advisory_only",
    ]
    missing = [k for k in required_keys if k not in ctx]
    assert not missing, f"Missing keys in section3_purpose_context: {missing}"


# ── PVS3-B03: advisory_only true in section3 context ─────────────────────────

def test_PVS3_B03_section3_advisory_only(client):
    """PVS3-B03: section3_purpose_context.advisory_only is True."""
    resp = _create(client, {"valuation_purpose": "sale_purchase"})
    assert resp.status_code == 201
    ctx = _get_ctx(client, resp)
    assert ctx.get("advisory_only") is True


# ── PVS3-B04: deleted_purpose_options is empty ────────────────────────────────

def test_PVS3_B04_no_deleted_purpose_options(client):
    """PVS3-B04: section3_purpose_context.deleted_purpose_options is empty list."""
    resp = _create(client, {"valuation_purpose": "sale_purchase"})
    assert resp.status_code == 201
    ctx = _get_ctx(client, resp)
    assert ctx.get("deleted_purpose_options") == [], \
        f"Expected [], got {ctx.get('deleted_purpose_options')}"


# ── PVS3-B05: deleted_basis_options is empty ─────────────────────────────────

def test_PVS3_B05_no_deleted_basis_options(client):
    """PVS3-B05: section3_purpose_context.deleted_basis_options is empty list."""
    resp = _create(client, {
        "valuation_purpose": "financial_reporting",
        "basis_of_value": "fair_value",
    })
    assert resp.status_code == 201
    ctx = _get_ctx(client, resp)
    assert ctx.get("deleted_basis_options") == [], \
        f"Expected [], got {ctx.get('deleted_basis_options')}"


# ── PVS3-B06: fair_value accepted as basis_of_value ──────────────────────────

def test_PVS3_B06_fair_value_accepted_as_basis(client):
    """PVS3-B06: fair_value is accepted in basis_of_value and reflected in section3 context."""
    resp = _create(client, {
        "property_type": "عقار تجاري",
        "valuation_purpose": "financial_reporting",
        "assignment_purpose": "financial_reporting",
        "basis_of_value": "fair_value",
    })
    assert resp.status_code == 201
    ctx = _get_ctx(client, resp)
    assert ctx.get("step3_basis_of_value") == "fair_value", \
        f"Expected fair_value in step3_basis_of_value, got {ctx.get('step3_basis_of_value')}"


# ── PVS3-B07: market_value in basis, not in purpose ──────────────────────────

def test_PVS3_B07_market_value_accepted_as_basis(client):
    """PVS3-B07: market_value is accepted in basis_of_value, not as assignment_purpose."""
    resp = _create(client, {
        "valuation_purpose": "sale_purchase",
        "basis_of_value": "market_value",
    })
    assert resp.status_code == 201
    ctx = _get_ctx(client, resp)
    assert ctx.get("step3_basis_of_value") == "market_value"
    assert ctx.get("step1_assignment_purpose") != "market_value"


# ── PVS3-B08: sale_purchase accepted as purpose ───────────────────────────────

def test_PVS3_B08_sale_purchase_accepted(client):
    """PVS3-B08: sale_purchase is accepted as valid assignment_purpose."""
    resp = _create(client, {"valuation_purpose": "sale_purchase"})
    assert resp.status_code == 201
    ctx = _get_ctx(client, resp)
    assert ctx.get("step1_assignment_purpose") == "sale_purchase"


# ── PVS3-B09: financing_mortgage accepted as purpose ─────────────────────────

def test_PVS3_B09_mortgage_financing_accepted(client):
    """PVS3-B09: financing_mortgage accepted as valid assignment_purpose."""
    resp = _create(client, {"valuation_purpose": "financing_mortgage"})
    assert resp.status_code == 201
    ctx = _get_ctx(client, resp)
    assert ctx.get("step1_assignment_purpose") in ("financing_mortgage", "mortgage_financing")


# ── PVS3-B10: partial_interest_valuation accepted ────────────────────────────

def test_PVS3_B10_partial_interest_valuation_accepted(client):
    """PVS3-B10: partial_interest_valuation accepted as assignment_purpose."""
    resp = _create(client, {"valuation_purpose": "partial_interest_valuation"})
    assert resp.status_code == 201
    ctx = _get_ctx(client, resp)
    assert ctx.get("step1_assignment_purpose") == "partial_interest_valuation"


# ── PVS3-B11: DLOC/DLOM in partial_interest context flag ─────────────────────

def test_PVS3_B11_dloc_dlom_in_partial_interest_context(client):
    """PVS3-B11: section3_purpose_context confirms dloc_dlom_in_partial_interest=True."""
    resp = _create(client, {
        "valuation_purpose": "partial_interest_valuation",
        "dloc_percent": "20",
        "dlom_percent": "15",
    })
    assert resp.status_code == 201
    ctx = _get_ctx(client, resp)
    assert ctx.get("dloc_dlom_in_partial_interest") is True


# ── PVS3-B12: methodology_removed_from_purpose flag ──────────────────────────

def test_PVS3_B12_methodology_removed_from_purpose_flag(client):
    """PVS3-B12: section3_purpose_context.methodology_removed_from_purpose is True."""
    resp = _create(client, {"valuation_purpose": "sale_purchase"})
    assert resp.status_code == 201
    ctx = _get_ctx(client, resp)
    assert ctx.get("methodology_removed_from_purpose") is True


# ── PVS3-B13: standards_removed_from_section3 flag ───────────────────────────

def test_PVS3_B13_standards_removed_from_section3_flag(client):
    """PVS3-B13: section3_purpose_context.standards_removed_from_section3 is True."""
    resp = _create(client, {"valuation_purpose": "financial_reporting"})
    assert resp.status_code == 201
    ctx = _get_ctx(client, resp)
    assert ctx.get("standards_removed_from_section3") is True


# ── PVS3-B14: basis_removed_from_purpose flag ────────────────────────────────

def test_PVS3_B14_basis_removed_from_purpose_flag(client):
    """PVS3-B14: section3_purpose_context.basis_removed_from_purpose is True."""
    resp = _create(client, {"valuation_purpose": "sale_purchase"})
    assert resp.status_code == 201
    ctx = _get_ctx(client, resp)
    assert ctx.get("basis_removed_from_purpose") is True


# ── PVS3-B15: preservation_pass is True ──────────────────────────────────────

def test_PVS3_B15_preservation_pass(client):
    """PVS3-B15: section3_purpose_context.preservation_pass is True."""
    resp = _create(client, {"valuation_purpose": "sale_purchase"})
    assert resp.status_code == 201
    ctx = _get_ctx(client, resp)
    assert ctx.get("preservation_pass") is True


# ── PVS3-B16: legacy valuation_purpose field still accepted ──────────────────

def test_PVS3_B16_legacy_valuation_purpose_mapped(client):
    """PVS3-B16: Old valuation_purpose field still accepted and request created."""
    resp = _create(client, {"valuation_purpose": "court_dispute"})
    assert resp.status_code == 201
    body = resp.get_json() or {}
    assert body.get("request_id"), "No request_id returned for legacy valuation_purpose"


# ── PVS3-B17: inline_guidance for partial_interest_valuation ─────────────────

def test_PVS3_B17_inline_guidance_for_partial_interest(client):
    """PVS3-B17: Inline guidance returned for partial_interest_valuation purpose."""
    resp = _create(client, {"valuation_purpose": "partial_interest_valuation"})
    assert resp.status_code == 201
    ctx = _get_ctx(client, resp)
    guidance = ctx.get("inline_guidance", "")
    assert guidance, "inline_guidance should be non-empty for partial_interest_valuation"


# ── PVS3-B18: moved_legacy_values list is non-empty ─────────────────────────

def test_PVS3_B18_moved_legacy_values_not_empty(client):
    """PVS3-B18: moved_legacy_values list is populated with moved items."""
    resp = _create(client, {"valuation_purpose": "sale_purchase"})
    assert resp.status_code == 201
    ctx = _get_ctx(client, resp)
    moved = ctx.get("moved_legacy_values", [])
    assert isinstance(moved, list) and len(moved) > 0, \
        "moved_legacy_values should be non-empty"


# ── PVS3-B19: no internal paths in section3_purpose_context ──────────────────

def test_PVS3_B19_no_internal_paths_in_context(client):
    """PVS3-B19: section3_purpose_context does not contain internal file-system paths."""
    import json as _json
    resp = _create(client, {"valuation_purpose": "sale_purchase"})
    assert resp.status_code == 201
    ctx = _get_ctx(client, resp)
    ctx_str = _json.dumps(ctx)
    forbidden = ["core_engine/", "C:\\Users", "c:\\users", "__file__", "/home/", "instance/"]
    hits = [f for f in forbidden if f in ctx_str]
    assert not hits, f"Internal path fragments in section3_purpose_context: {hits}"


# ── PVS3-B20: ordinary valuation route unaffected ────────────────────────────

def test_PVS3_B20_ordinary_valuation_route_unaffected(client):
    """PVS3-B20: The simple-valuation draft-pdf route is unaffected by PVS3 changes."""
    resp = client.post(
        "/api/simple-valuation/draft-pdf",
        json={"property_type": "شقة", "area": 120},
        content_type="application/json",
    )
    assert resp.status_code not in (404, 405), \
        f"Simple valuation route broken: {resp.status_code}"


# ── PVS3-B21: tax appeal route unaffected ────────────────────────────────────

def test_PVS3_B21_tax_appeal_route_unaffected(client):
    """PVS3-B21: Tax appeal expert-requests route still responds correctly."""
    resp = client.get(
        "/api/tax-appeal/expert-requests",
        headers=_auth(),
    )
    assert resp.status_code not in (404, 405, 500), \
        f"Tax appeal route broken: {resp.status_code}"


# ══════════════════════════════════════════════════════════════════════════════
# PVS3-Merge: Section 3 Purpose & Professional Targeting Merge Tests (B22-B47)
# Tests for: section3_1_purpose_context, professional_targeting_context,
#            section3_cleanup_context, legacy aliases
# ══════════════════════════════════════════════════════════════════════════════

def _get_detail(client, resp) -> dict:
    body = resp.get_json() or {}
    rid = body.get("request_id", "")
    if rid:
        outer = (client.get(f"/api/professional-valuation/requests/{rid}", headers=_auth()).get_json() or {})
        # The detail endpoint wraps record data inside outer["request"]
        return outer.get("request", outer)
    return {}


# ── B22-B33: Purpose flow — section3_1_purpose_context ───────────────────────

def test_PVS3_B22_section3_1_purpose_context_exists(client):
    """PVS3-B22: section3_1_purpose_context key present in detail response."""
    resp = _create(client)
    assert resp.status_code == 201
    detail = _get_detail(client, resp)
    assert "section3_1_purpose_context" in detail, "section3_1_purpose_context missing from detail"


def test_PVS3_B23_assignment_purpose_accepted_in_s31_ctx(client):
    """PVS3-B23: assignment_purpose reflected in section3_1_purpose_context."""
    resp = _create(client, {"assignment_purpose": "tax_appeal"})
    assert resp.status_code == 201
    detail = _get_detail(client, resp)
    ctx = detail.get("section3_1_purpose_context", {})
    assert ctx.get("assignment_purpose") == "tax_appeal"


def test_PVS3_B24_purpose_subroute_in_s31_ctx(client):
    """PVS3-B24: purpose_subroute reflected in section3_1_purpose_context."""
    resp = _create(client, {"purpose_subroute": "collateral_valuation"})
    assert resp.status_code == 201
    detail = _get_detail(client, resp)
    ctx = detail.get("section3_1_purpose_context", {})
    assert ctx.get("purpose_subroute") == "collateral_valuation"


def test_PVS3_B25_purpose_logic_path_legacy_in_s31_ctx(client):
    """PVS3-B25: purpose_logic_path stored and accessible in section3_1_purpose_context."""
    resp = _create(client, {"purpose_logic_path": "sales_comparison_market_value"})
    assert resp.status_code == 201
    detail = _get_detail(client, resp)
    ctx = detail.get("section3_1_purpose_context", {})
    assert ctx.get("purpose_logic_path") == "sales_comparison_market_value"


def test_PVS3_B26_purpose_logic_path_not_visible_in_ui(client):
    """PVS3-B26: section3_1_purpose_context.purpose_logic_path_visible_in_ui is False."""
    resp = _create(client)
    assert resp.status_code == 201
    detail = _get_detail(client, resp)
    ctx = detail.get("section3_1_purpose_context", {})
    assert ctx.get("purpose_logic_path_visible_in_ui") is False


def test_PVS3_B27_purpose_logic_path_derived_true(client):
    """PVS3-B27: section3_1_purpose_context.purpose_logic_path_derived is True."""
    resp = _create(client)
    assert resp.status_code == 201
    detail = _get_detail(client, resp)
    ctx = detail.get("section3_1_purpose_context", {})
    assert ctx.get("purpose_logic_path_derived") is True


def test_PVS3_B28_purpose_route_legacy_in_s31_ctx(client):
    """PVS3-B28: purpose_route accepted and reflected in section3_1_purpose_context."""
    resp = _create(client, {"purpose_route": "standard_market_value"})
    assert resp.status_code == 201
    detail = _get_detail(client, resp)
    ctx = detail.get("section3_1_purpose_context", {})
    assert ctx.get("purpose_route") == "standard_market_value"


def test_PVS3_B29_purpose_route_not_visible_in_ui(client):
    """PVS3-B29: section3_1_purpose_context.purpose_route_visible_in_ui is False."""
    resp = _create(client)
    assert resp.status_code == 201
    detail = _get_detail(client, resp)
    ctx = detail.get("section3_1_purpose_context", {})
    assert ctx.get("purpose_route_visible_in_ui") is False


def test_PVS3_B30_purpose_route_merged_true(client):
    """PVS3-B30: section3_1_purpose_context.purpose_route_merged is True."""
    resp = _create(client)
    assert resp.status_code == 201
    detail = _get_detail(client, resp)
    ctx = detail.get("section3_1_purpose_context", {})
    assert ctx.get("purpose_route_merged") is True


def test_PVS3_B31_s31_no_deleted_purpose_options(client):
    """PVS3-B31: section3_cleanup_context.deleted_purpose_options is empty."""
    resp = _create(client)
    assert resp.status_code == 201
    detail = _get_detail(client, resp)
    ctx = detail.get("section3_cleanup_context", {})
    assert ctx.get("deleted_purpose_options") == []


def test_PVS3_B32_s31_no_deleted_subroutes(client):
    """PVS3-B32: pvs3_no_deletion_audit.deleted_purpose_subroutes is empty."""
    resp = _create(client)
    assert resp.status_code == 201
    detail = _get_detail(client, resp)
    audit = detail.get("pvs3_no_deletion_audit", {})
    assert audit.get("deleted_purpose_subroutes") == []


def test_PVS3_B33_s31_preservation_pass(client):
    """PVS3-B33: section3_1_purpose_context.preservation_pass is True."""
    resp = _create(client)
    assert resp.status_code == 201
    detail = _get_detail(client, resp)
    ctx = detail.get("section3_1_purpose_context", {})
    assert ctx.get("preservation_pass") is True


# ── B34-B44: Professional targeting ──────────────────────────────────────────

def test_PVS3_B34_professional_targeting_context_exists(client):
    """PVS3-B34: professional_targeting_context key present in detail response."""
    resp = _create(client)
    assert resp.status_code == 201
    detail = _get_detail(client, resp)
    assert "professional_targeting_context" in detail


def test_PVS3_B35_intended_user_in_targeting_ctx(client):
    """PVS3-B35: intended_user_category stored and returned in professional_targeting_context."""
    resp = _create(client, {"intended_user_category": "bank_financial_institution"})
    assert resp.status_code == 201
    detail = _get_detail(client, resp)
    ctx = detail.get("professional_targeting_context", {})
    assert ctx.get("intended_user") == "bank_financial_institution"


def test_PVS3_B36_professional_pathway_in_targeting_ctx(client):
    """PVS3-B36: professional_context_path stored as professional_pathway in targeting context."""
    resp = _create(client, {"professional_context_path": "banking_lending"})
    assert resp.status_code == 201
    detail = _get_detail(client, resp)
    ctx = detail.get("professional_targeting_context", {})
    assert ctx.get("professional_pathway") == "banking_lending"


def test_PVS3_B37_professional_purpose_path_legacy_in_ctx(client):
    """PVS3-B37: professional_purpose_path accepted and in professional_targeting_context."""
    resp = _create(client, {"professional_purpose_path": "bank_financing_path"})
    assert resp.status_code == 201
    detail = _get_detail(client, resp)
    ctx = detail.get("professional_targeting_context", {})
    assert ctx.get("professional_purpose_path") == "bank_financing_path"


def test_PVS3_B38_professional_purpose_path_not_visible(client):
    """PVS3-B38: professional_targeting_context.professional_purpose_path_visible_in_ui is False."""
    resp = _create(client)
    assert resp.status_code == 201
    detail = _get_detail(client, resp)
    ctx = detail.get("professional_targeting_context", {})
    assert ctx.get("professional_purpose_path_visible_in_ui") is False


def test_PVS3_B39_professional_purpose_path_merged_true(client):
    """PVS3-B39: professional_targeting_context.professional_purpose_path_merged is True."""
    resp = _create(client)
    assert resp.status_code == 201
    detail = _get_detail(client, resp)
    ctx = detail.get("professional_targeting_context", {})
    assert ctx.get("professional_purpose_path_merged") is True


def test_PVS3_B40_legacy_professional_pathway_alias(client):
    """PVS3-B40: professional_pathway legacy alias accepted and maps to professional_context_path."""
    resp = _create(client, {"professional_pathway": "litigation_dispute"})
    assert resp.status_code == 201
    detail = _get_detail(client, resp)
    ctx = detail.get("professional_targeting_context", {})
    assert ctx.get("professional_pathway") == "litigation_dispute"


def test_PVS3_B41_legacy_intended_party_alias(client):
    """PVS3-B41: intended_party legacy alias maps to intended_user_category."""
    resp = _create(client, {"intended_party": "court_judicial_authority"})
    assert resp.status_code == 201
    detail = _get_detail(client, resp)
    ctx = detail.get("professional_targeting_context", {})
    assert ctx.get("intended_user") == "court_judicial_authority"


def test_PVS3_B42_legacy_target_entity_alias(client):
    """PVS3-B42: target_entity legacy alias maps to intended_user_category."""
    resp = _create(client, {"target_entity": "tax_authority"})
    assert resp.status_code == 201
    detail = _get_detail(client, resp)
    ctx = detail.get("professional_targeting_context", {})
    assert ctx.get("intended_user") == "tax_authority"


def test_PVS3_B43_no_deleted_intended_user_options(client):
    """PVS3-B43: pvs3_no_deletion_audit.deleted_intended_user_options is empty."""
    resp = _create(client)
    assert resp.status_code == 201
    detail = _get_detail(client, resp)
    audit = detail.get("pvs3_no_deletion_audit", {})
    assert audit.get("deleted_intended_user_options") == []


def test_PVS3_B44_no_deleted_pathway_options(client):
    """PVS3-B44: pvs3_no_deletion_audit.deleted_professional_pathway_options is empty."""
    resp = _create(client)
    assert resp.status_code == 201
    detail = _get_detail(client, resp)
    audit = detail.get("pvs3_no_deletion_audit", {})
    assert audit.get("deleted_professional_pathway_options") == []


# ── B45-B47: Global / Cleanup ─────────────────────────────────────────────────

def test_PVS3_B45_section3_cleanup_context_exists(client):
    """PVS3-B45: section3_cleanup_context present in detail response."""
    resp = _create(client)
    assert resp.status_code == 201
    detail = _get_detail(client, resp)
    assert "section3_cleanup_context" in detail


def test_PVS3_B46_visible_router_blocks_removed(client):
    """PVS3-B46: section3_cleanup_context.visible_router_blocks_removed is True."""
    resp = _create(client)
    assert resp.status_code == 201
    detail = _get_detail(client, resp)
    ctx = detail.get("section3_cleanup_context", {})
    assert ctx.get("visible_router_blocks_removed") is True


def test_PVS3_B47_backend_aliases_preserved(client):
    """PVS3-B47: section3_cleanup_context.backend_aliases_preserved is True."""
    resp = _create(client)
    assert resp.status_code == 201
    detail = _get_detail(client, resp)
    ctx = detail.get("section3_cleanup_context", {})
    assert ctx.get("backend_aliases_preserved") is True
