"""
PVPBSR Backend Tests
Professional Valuation Page — Purpose, Basis of Value, Intended User,
Scope, Standards, Weighting & Registry Integration

27 tests covering:
- New purpose labels (tax_appeal, partial_interest_valuation, merger_acquisition)
- New fields parsed and stored in record
- valuation_purpose_context returned in response
- Registry dicts returned in response
- Partial interest context populated when purpose=partial_interest_valuation
- Weighting totals computed correctly
- Routing matrix incompatibilities detected
- Preservation pass verified
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
_ORIG_CWD = os.getcwd()
try:
    os.chdir(str(_CORE))

    from bridge_api import app
    import professional_valuation_routes as _pvr
finally:
    os.chdir(_ORIG_CWD)

_TEST_SECRET = "pvr-pvpbsr-test-secret-32chars!!!"


@pytest.fixture(scope="session", autouse=True)
def _clean_pvr_datastore():
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


_BASE: dict = {
    "client_name":        "PVPBSR Test",
    "property_type":      "apartment",
    "property_title":     "Test Property",
    "assignment_purpose": "sale_purchase",
    "basis_of_value":     "market_value",
    "city":               "الرياض",
    "district":           "العليا",
}


def _post(client, extra: dict | None = None) -> tuple:
    body = dict(_BASE)
    if extra:
        body.update(extra)
    resp = client.post(
        "/api/professional-valuation/requests",
        json=body,
        content_type="application/json",
    )
    rb = resp.get_json() or {}
    return resp, rb


def _ctx(rb: dict) -> dict:
    return rb.get("valuation_purpose_context", {})


# ── PVPBSRB01 — New purpose label: tax_appeal ────────────────────────────────
def test_PVPBSRB01_tax_appeal_label(client):
    resp, rb = _post(client, {"assignment_purpose": "tax_appeal"})
    assert resp.status_code == 201
    summary = rb.get("valuation_purpose_routes_summary", {})
    assert summary.get("assignment_purpose_label_ar") == "طعن ضريبي"


# ── PVPBSRB02 — New purpose label: partial_interest_valuation ────────────────
def test_PVPBSRB02_partial_interest_label(client):
    resp, rb = _post(client, {"assignment_purpose": "partial_interest_valuation"})
    assert resp.status_code == 201
    summary = rb.get("valuation_purpose_routes_summary", {})
    assert summary.get("assignment_purpose_label_ar") == "تقييم مصالح جزئية"


# ── PVPBSRB03 — New purpose label: merger_acquisition ────────────────────────
def test_PVPBSRB03_merger_acquisition_label(client):
    resp, rb = _post(client, {"assignment_purpose": "merger_acquisition"})
    assert resp.status_code == 201
    summary = rb.get("valuation_purpose_routes_summary", {})
    assert summary.get("assignment_purpose_label_ar") == "اندماج واستحواذ"


# ── PVPBSRB04 — valuation_purpose_context key present in response ─────────────
def test_PVPBSRB04_purpose_context_in_response(client):
    resp, rb = _post(client)
    assert resp.status_code == 201
    assert "valuation_purpose_context" in rb


# ── PVPBSRB05 — valuation_purpose_context has required keys ──────────────────
def test_PVPBSRB05_purpose_context_keys(client):
    _, rb = _post(client)
    ctx = _ctx(rb)
    for key in ("purpose", "intended_use", "intended_user", "basis_of_value",
                "value_premise", "scope_of_work", "preliminary_weighting",
                "disclosures", "warnings", "standards_guidance",
                "routing_matrix_result", "legacy_aliases", "preservation_pass"):
        assert key in ctx, f"Missing key: {key}"


# ── PVPBSRB06 — preservation_pass is True ────────────────────────────────────
def test_PVPBSRB06_preservation_pass_true(client):
    _, rb = _post(client)
    assert _ctx(rb)["preservation_pass"] is True


# ── PVPBSRB07 — intended_user_name field stored ──────────────────────────────
def test_PVPBSRB07_intended_user_name(client):
    _, rb = _post(client, {"intended_user_name": "بنك التنمية العقارية"})
    assert _ctx(rb)["intended_user_name"] == "بنك التنمية العقارية"


# ── PVPBSRB08 — scope_of_work field stored ───────────────────────────────────
def test_PVPBSRB08_scope_of_work(client):
    _, rb = _post(client, {"scope_of_work": "full_inspection"})
    assert _ctx(rb)["scope_of_work"] == "full_inspection"


# ── PVPBSRB09 — inspection_scope field stored ────────────────────────────────
def test_PVPBSRB09_inspection_scope(client):
    _, rb = _post(client, {"inspection_scope": "exterior_only"})
    assert _ctx(rb)["inspection_scope"] == "exterior_only"


# ── PVPBSRB10 — data_scope field stored ──────────────────────────────────────
def test_PVPBSRB10_data_scope(client):
    _, rb = _post(client, {"data_scope": "limited_market_data"})
    assert _ctx(rb)["data_scope"] == "limited_market_data"


# ── PVPBSRB11 — limiting_conditions stored ───────────────────────────────────
def test_PVPBSRB11_limiting_conditions(client):
    _, rb = _post(client, {"limiting_conditions": "no_legal_title_review"})
    assert _ctx(rb)["limiting_conditions"] == "no_legal_title_review"


# ── PVPBSRB12 — extraordinary_assumptions stored ─────────────────────────────
def test_PVPBSRB12_extraordinary_assumptions(client):
    _, rb = _post(client, {"extraordinary_assumptions": "assumes_planning_granted"})
    assert _ctx(rb)["extraordinary_assumptions"] == "assumes_planning_granted"


# ── PVPBSRB13 — hypothetical_conditions stored ───────────────────────────────
def test_PVPBSRB13_hypothetical_conditions(client):
    _, rb = _post(client, {"hypothetical_conditions": "as_if_vacant"})
    assert _ctx(rb)["hypothetical_conditions"] == "as_if_vacant"


# ── PVPBSRB14 — weighting total computed (valid: 60+30+10=100) ───────────────
def test_PVPBSRB14_weighting_total_valid(client):
    _, rb = _post(client, {
        "sales_comparison_weight": "60",
        "income_approach_weight": "30",
        "cost_approach_weight": "10",
    })
    wgt = _ctx(rb)["preliminary_weighting"]
    assert wgt["total_percent"] == 100.0
    assert wgt["is_valid_total"] is True


# ── PVPBSRB15 — weighting total invalid (50+30+10=90) ────────────────────────
def test_PVPBSRB15_weighting_total_invalid(client):
    _, rb = _post(client, {
        "sales_comparison_weight": "50",
        "income_approach_weight": "30",
        "cost_approach_weight": "10",
    })
    wgt = _ctx(rb)["preliminary_weighting"]
    assert wgt["total_percent"] == 90.0
    assert wgt["is_valid_total"] is False


# ── PVPBSRB16 — partial_interest_context None when purpose != partial ─────────
def test_PVPBSRB16_partial_interest_none_for_other_purpose(client):
    _, rb = _post(client)
    assert _ctx(rb)["partial_interest_context"] is None


# ── PVPBSRB17 — partial_interest_context populated when purpose=partial ───────
def test_PVPBSRB17_partial_interest_context_populated(client):
    _, rb = _post(client, {
        "assignment_purpose": "partial_interest_valuation",
        "ownership_interest_percent": "40",
        "dloc_percent": "15",
        "dlom_percent": "10",
        "discount_justification": "خصم السيولة",
    })
    pi = _ctx(rb)["partial_interest_context"]
    assert pi is not None
    assert pi["ownership_interest_percent"] == "40"
    assert pi["dloc_percent"] == "15"
    assert pi["dlom_percent"] == "10"
    assert pi["discount_justification"] == "خصم السيولة"


# ── PVPBSRB18 — partial_interest_context combined_discount computed ───────────
def test_PVPBSRB18_combined_discount(client):
    _, rb = _post(client, {
        "assignment_purpose": "partial_interest_valuation",
        "ownership_interest_percent": "50",
        "dloc_percent": "20",
        "dlom_percent": "5",
        "discount_justification": "test",
    })
    pi = _ctx(rb)["partial_interest_context"]
    assert pi["combined_discount_percent"] == 25.0


# ── PVPBSRB19 — partial_interest requires_expert_review always True ────────────
def test_PVPBSRB19_partial_interest_expert_review(client):
    _, rb = _post(client, {
        "assignment_purpose": "partial_interest_valuation",
        "ownership_interest_percent": "30",
        "dloc_percent": "10",
        "dlom_percent": "5",
        "discount_justification": "test",
    })
    pi = _ctx(rb)["partial_interest_context"]
    assert pi["requires_expert_review"] is True
    assert pi["auto_approval_disabled"] is True


# ── PVPBSRB20 — routing_matrix_result in response ────────────────────────────
def test_PVPBSRB20_routing_matrix_result(client):
    _, rb = _post(client)
    rm = _ctx(rb)["routing_matrix_result"]
    assert "recommended_methods" in rm
    assert "disclosures" in rm
    assert "incompatibilities" in rm


# ── PVPBSRB21 — routing matrix detects liquidation/financial_reporting incompat
def test_PVPBSRB21_routing_incompatibility_detected(client):
    _, rb = _post(client, {
        "assignment_purpose": "financial_reporting",
        "basis_of_value": "liquidation_value",
    })
    warnings = _ctx(rb)["warnings"]
    assert any("liquidation" in w for w in warnings)


# ── PVPBSRB22 — purpose_registry_context in response ────────────────────────
def test_PVPBSRB22_purpose_registry_in_response(client):
    _, rb = _post(client)
    assert "purpose_registry_context" in rb
    entries = rb["purpose_registry_context"]["entries"]
    keys = [e["key"] for e in entries]
    assert "partial_interest_valuation" in keys
    assert "tax_appeal" in keys
    assert "merger_acquisition" in keys


# ── PVPBSRB23 — basis_registry_context in response ───────────────────────────
def test_PVPBSRB23_basis_registry_in_response(client):
    _, rb = _post(client)
    assert "basis_registry_context" in rb
    entries = rb["basis_registry_context"]["entries"]
    keys = [e["key"] for e in entries]
    assert "value_in_use" in keys
    assert "special_value" in keys
    assert "synergistic_value" in keys


# ── PVPBSRB24 — intended_user_registry_context in response ───────────────────
def test_PVPBSRB24_intended_user_registry(client):
    _, rb = _post(client)
    assert "intended_user_registry_context" in rb


# ── PVPBSRB25 — scope_registry_context in response ───────────────────────────
def test_PVPBSRB25_scope_registry(client):
    _, rb = _post(client)
    assert "scope_registry_context" in rb
    sc = rb["scope_registry_context"]
    assert "scope_of_work_options" in sc
    assert "inspection_scope_options" in sc


# ── PVPBSRB26 — purpose registry preserves all 14 legacy purposes ────────────
def test_PVPBSRB26_legacy_purposes_preserved(client):
    _, rb = _post(client)
    entries = rb["purpose_registry_context"]["entries"]
    keys = {e["key"] for e in entries}
    legacy = {
        "sale_purchase", "financing_mortgage", "court_dispute",
        "investment_decision", "internal_advisory", "tax_government",
        "insurance", "financial_reporting", "environmental_risk_review",
        "liquidation_restructuring", "inheritance_partition",
        "regulatory_compliance", "portfolio_management", "development_feasibility",
    }
    missing = legacy - keys
    assert not missing, f"Missing legacy purposes: {missing}"


# ── PVPBSRB27 — value_scope / value_basis_route / value_basis_subroute stored
def test_PVPBSRB27_extended_axis3_fields(client):
    _, rb = _post(client, {
        "value_scope": "full_assessment",
        "value_basis_route": "rics_red_book",
        "value_basis_subroute": "vps_4",
    })
    ctx = _ctx(rb)
    assert ctx["value_scope"] == "full_assessment"
    assert ctx["value_basis_route"] == "rics_red_book"
    assert ctx["value_basis_subroute"] == "vps_4"
