"""
PVASR Backend Tests — Professional Valuation: Applied Standards Registry
Tests: PVASRB01–PVASRB31
"""
import json
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

_BASE: dict = {
    "client_name":        "PVASR Test",
    "property_type":      "apartment",
    "property_title":     "Test Property",
    "assignment_purpose": "sale_purchase",
    "basis_of_value":     "market_value",
    "city":               "القاهرة",
    "district":           "مصر الجديدة",
}


@pytest.fixture(scope="module")
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _post(client, extra=None):
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


# ── PVASRB01: standards_registry exists in backend module context ─────────
def test_PVASRB01_standards_registry_exists(client):
    _, rb = _post(client)
    ctx = rb.get("standards_registry_context", {})
    assert isinstance(ctx, dict), "standards_registry_context missing from response"
    assert "standards" in ctx


# ── PVASRB02: standards registry includes IVS 2025 ───────────────────────
def test_PVASRB02_registry_includes_ivs_2025(client):
    _, rb = _post(client)
    standards = rb.get("standards_registry_context", {}).get("standards", [])
    keys = [s["key"] for s in standards]
    assert "ivs_2025" in keys


# ── PVASRB03: standards registry includes RICS Red Book 2025 ─────────────
def test_PVASRB03_registry_includes_rics(client):
    _, rb = _post(client)
    standards = rb.get("standards_registry_context", {}).get("standards", [])
    keys = [s["key"] for s in standards]
    assert "rics_red_book_2025" in keys


# ── PVASRB04: standards registry includes IFRS 13 ────────────────────────
def test_PVASRB04_registry_includes_ifrs_13(client):
    _, rb = _post(client)
    standards = rb.get("standards_registry_context", {}).get("standards", [])
    keys = [s["key"] for s in standards]
    assert "ifrs_13" in keys


# ── PVASRB05: standards registry includes FRA Egypt ──────────────────────
def test_PVASRB05_registry_includes_fra_egypt(client):
    _, rb = _post(client)
    standards = rb.get("standards_registry_context", {}).get("standards", [])
    keys = [s["key"] for s in standards]
    assert "fra_egypt" in keys


# ── PVASRB06: local standards registry exists ────────────────────────────
def test_PVASRB06_local_standards_registry_exists(client):
    _, rb = _post(client)
    ctx = rb.get("standards_registry_context", {})
    assert "local_standards" in ctx
    assert len(ctx["local_standards"]) >= 5


# ── PVASRB07: IVS references registry exists ─────────────────────────────
def test_PVASRB07_ivs_references_exist(client):
    _, rb = _post(client)
    ctx = rb.get("standards_registry_context", {})
    ivs_refs = ctx.get("ivs_references", [])
    keys = [r["key"] for r in ivs_refs]
    assert "ivs_100_framework" in keys
    assert "ivs_400_real_property_interests" in keys


# ── PVASRB08: IFRS levels registry exists ────────────────────────────────
def test_PVASRB08_ifrs_levels_exist(client):
    _, rb = _post(client)
    ctx = rb.get("standards_registry_context", {})
    levels = ctx.get("ifrs_levels", [])
    keys = [l["key"] for l in levels]
    assert "level_1" in keys
    assert "level_2" in keys
    assert "level_3" in keys
    assert "na" in keys


# ── PVASRB09: disclosure levels registry exists ───────────────────────────
def test_PVASRB09_disclosure_levels_exist(client):
    _, rb = _post(client)
    ctx = rb.get("standards_registry_context", {})
    dl = ctx.get("disclosure_levels", [])
    keys = [d["key"] for d in dl]
    assert "full_compliance" in keys
    assert "limited_disclosure" in keys


# ── PVASRB10: create accepts selected_standards ──────────────────────────
def test_PVASRB10_accepts_selected_standards(client):
    resp, rb = _post(client, {"selected_standards": ["ivs_2025", "rics_red_book_2025"]})
    assert resp.status_code == 201
    ctx = rb.get("applied_standards_context", {})
    assert "ivs_2025" in ctx.get("selected_standards", [])
    assert "rics_red_book_2025" in ctx.get("selected_standards", [])


# ── PVASRB11: create accepts jurisdiction_country ────────────────────────
def test_PVASRB11_accepts_jurisdiction_country(client):
    resp, rb = _post(client, {"jurisdiction_country": "egypt"})
    assert resp.status_code == 201
    ctx = rb.get("applied_standards_context", {})
    assert ctx.get("jurisdiction_country") == "egypt"


# ── PVASRB12: create accepts local_reference ─────────────────────────────
def test_PVASRB12_accepts_local_reference(client):
    resp, rb = _post(client, {"local_reference": "fra_egypt"})
    assert resp.status_code == 201
    ctx = rb.get("applied_standards_context", {})
    assert ctx.get("local_reference") == "fra_egypt"


# ── PVASRB13: create accepts ivs_reference ───────────────────────────────
def test_PVASRB13_accepts_ivs_reference(client):
    resp, rb = _post(client, {"ivs_reference": "ivs_101_scope_of_work"})
    assert resp.status_code == 201
    ctx = rb.get("applied_standards_context", {})
    assert ctx.get("ivs_reference") == "ivs_101_scope_of_work"


# ── PVASRB14: create accepts ifrs_fair_value_level ───────────────────────
def test_PVASRB14_accepts_ifrs_fair_value_level(client):
    resp, rb = _post(client, {"ifrs_fair_value_level": "level_2"})
    assert resp.status_code == 201
    ctx = rb.get("applied_standards_context", {})
    assert ctx.get("ifrs_fair_value_level") == "level_2"


# ── PVASRB15: create accepts compliance_disclosure_level ─────────────────
def test_PVASRB15_accepts_compliance_disclosure_level(client):
    resp, rb = _post(client, {"compliance_disclosure_level": "full_compliance"})
    assert resp.status_code == 201
    ctx = rb.get("applied_standards_context", {})
    assert ctx.get("compliance_disclosure_level") == "full_compliance"


# ── PVASRB16: create accepts compliance_target ───────────────────────────
def test_PVASRB16_accepts_compliance_target(client):
    resp, rb = _post(client, {"compliance_target": "expert_review_ready"})
    assert resp.status_code == 201
    ctx = rb.get("applied_standards_context", {})
    assert ctx.get("compliance_target") == "expert_review_ready"


# ── PVASRB17: detail returns applied_standards_context ───────────────────
def test_PVASRB17_detail_returns_applied_standards_context(client):
    _, rb = _post(client, {"selected_standards": ["ivs_2025"]})
    assert "applied_standards_context" in rb
    ctx = rb["applied_standards_context"]
    required_keys = [
        "selected_standards", "compliance_status", "compliance_status_label_ar",
        "missing_requirements", "required_disclosures", "standards_warnings",
        "recommended_actions", "report_disclosure_guidance",
        "required_pdf_sections", "required_workbook_sheets",
        "advisory_only", "expert_review_required",
        "certification_gate_controls_final_status", "preservation_pass",
    ]
    for k in required_keys:
        assert k in ctx, f"Key missing: {k}"


# ── PVASRB18: detail returns standards_registry_context ──────────────────
def test_PVASRB18_detail_returns_standards_registry_context(client):
    _, rb = _post(client)
    assert "standards_registry_context" in rb
    ctx = rb["standards_registry_context"]
    assert "standards" in ctx
    assert "local_standards" in ctx
    assert "ivs_references" in ctx
    assert "rics_references" in ctx
    assert "ifrs_levels" in ctx
    assert "disclosure_levels" in ctx


# ── PVASRB19: compliance evaluator returns insufficient_data when no standards
def test_PVASRB19_no_standards_insufficient_data(client):
    _, rb = _post(client, {"selected_standards": []})
    ctx = rb.get("applied_standards_context", {})
    assert ctx.get("compliance_status") == "insufficient_data"
    assert any("لم يتم اختيار" in w for w in ctx.get("standards_warnings", []))


# ── PVASRB20: IFRS 13 + non-fair-value basis → warning ──────────────────
def test_PVASRB20_ifrs_nonfair_warning(client):
    _, rb = _post(client, {
        "selected_standards": ["ifrs_13"],
        "basis_of_value": "market_value",
    })
    ctx = rb.get("applied_standards_context", {})
    warnings = ctx.get("standards_warnings", [])
    assert any("IFRS 13" in w for w in warnings)


# ── PVASRB21: fair_value without IFRS 13 → warning ───────────────────────
def test_PVASRB21_fair_value_without_ifrs_warning(client):
    _, rb = _post(client, {
        "selected_standards": ["ivs_2025"],
        "basis_of_value": "fair_value",
    })
    ctx = rb.get("applied_standards_context", {})
    warnings = ctx.get("standards_warnings", [])
    assert any("IFRS 13" in w for w in warnings)


# ── PVASRB22: certified target → certification gate warning ──────────────
def test_PVASRB22_certified_target_warning(client):
    _, rb = _post(client, {
        "selected_standards": ["ivs_2025"],
        "compliance_target": "certified_report_ready",
    })
    ctx = rb.get("applied_standards_context", {})
    warnings = ctx.get("standards_warnings", [])
    assert any("بوابات الاعتماد" in w for w in warnings)


# ── PVASRB23: limited disclosure → warning ───────────────────────────────
def test_PVASRB23_limited_disclosure_warning(client):
    _, rb = _post(client, {
        "selected_standards": ["ivs_2025"],
        "compliance_disclosure_level": "limited_disclosure",
    })
    ctx = rb.get("applied_standards_context", {})
    warnings = ctx.get("standards_warnings", [])
    assert any("الإفصاح" in w for w in warnings)


# ── PVASRB24: custom local standard requires expert review ────────────────
def test_PVASRB24_custom_standard_expert_review(client):
    _, rb = _post(client, {"selected_standards": ["custom_local_standard"]})
    ctx = rb.get("applied_standards_context", {})
    missing = ctx.get("missing_requirements", [])
    assert any("خبير" in m for m in missing)


# ── PVASRB25: no internal paths in applied_standards_context ─────────────
def test_PVASRB25_no_internal_paths(client):
    _, rb = _post(client, {"selected_standards": ["ivs_2025"]})
    ctx_str = json.dumps(rb.get("applied_standards_context", {}))
    assert "C:\\" not in ctx_str
    assert "/home/" not in ctx_str
    assert "expert_smart1" not in ctx_str


# ── PVASRB26: no deleted registry items (legacy keys preserved) ───────────
def test_PVASRB26_legacy_keys_preserved(client):
    _, rb = _post(client)
    ctx = rb.get("applied_standards_context", {})
    legacy = ctx.get("legacy_aliases", {})
    old_standards = legacy.get("standard_options", [])
    for k in ["ivs_2022", "rics_red_book", "egyptian_standard", "gcc_standard", "local_regulatory"]:
        assert k in old_standards, f"Legacy key missing: {k}"
    old_ivs = legacy.get("ivs_refs", [])
    for k in ["ivs_104", "ivs_105", "ivs_400", "ivs_410", "ivs_500", "ivs_600"]:
        assert k in old_ivs, f"Legacy IVS ref missing: {k}"
    old_local = legacy.get("local_refs", [])
    for k in ["eg_valuation_law", "eg_cma_circular", "uae_rera"]:
        assert k in old_local, f"Legacy local ref missing: {k}"


# ── PVASRB27: ordinary valuation tests — basic create still works ─────────
def test_PVASRB27_ordinary_create_unaffected(client):
    resp, rb = _post(client)
    assert resp.status_code == 201
    assert rb.get("ok") is True


# ── PVASRB28: advisory_only is always True ───────────────────────────────
def test_PVASRB28_advisory_only_true(client):
    _, rb = _post(client, {"selected_standards": ["ivs_2025", "rics_red_book_2025"]})
    ctx = rb.get("applied_standards_context", {})
    assert ctx.get("advisory_only") is True
    assert ctx.get("certification_gate_controls_final_status") is True


# ── PVASRB29: standards catalogue route requires auth ────────────────────
def test_PVASRB29_catalogue_route_requires_auth(client):
    resp = client.get("/api/professional-valuation/standards/catalogue")
    # should return 401 without auth token
    assert resp.status_code in (401, 403)


# ── PVASRB30: standards_mapping_matrix_context present ───────────────────
def test_PVASRB30_mapping_matrix_context_present(client):
    _, rb = _post(client)
    ctx = rb.get("standards_mapping_matrix_context", {})
    assert isinstance(ctx, dict)
    assert "mapping_matrix" in ctx
    mm = ctx["mapping_matrix"]
    assert "purpose_standards_map" in mm
    assert "basis_standards_map" in mm


# ── PVASRB31: standards_compliance_rules_context present ─────────────────
def test_PVASRB31_compliance_rules_context_present(client):
    _, rb = _post(client, {"selected_standards": ["ivs_2025"]})
    ctx = rb.get("standards_compliance_rules_context", {})
    assert isinstance(ctx, dict)
    assert "compliance_rules" in ctx
    assert ctx.get("advisory_only") is True
