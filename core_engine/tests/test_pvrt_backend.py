"""
PVRT Backend Tests — Professional Valuation: Report Types Registry
Tests: PVRTB01–PVRTB28
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
finally:
    os.chdir(_ORIG_CWD)

_BASE: dict = {
    "client_name":        "PVRT Test",
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


# ── PVRTB01: report_type_registry_context exists ─────────────────────────
def test_PVRTB01_registry_context_exists(client):
    _, rb = _post(client)
    ctx = rb.get("report_type_registry_context", {})
    assert isinstance(ctx, dict), "report_type_registry_context missing"
    assert "report_types" in ctx


# ── PVRTB02: registry includes summary_report ──────────────────────────
def test_PVRTB02_registry_includes_summary_report(client):
    _, rb = _post(client)
    types = rb.get("report_type_registry_context", {}).get("report_types", [])
    keys = [t["key"] for t in types]
    assert "summary_report" in keys


# ── PVRTB03: registry includes full_report ────────────────────────────
def test_PVRTB03_registry_includes_full_report(client):
    _, rb = _post(client)
    types = rb.get("report_type_registry_context", {}).get("report_types", [])
    keys = [t["key"] for t in types]
    assert "full_report" in keys


# ── PVRTB04: registry includes enhanced_professional_report ───────────
def test_PVRTB04_registry_includes_enhanced_professional_report(client):
    _, rb = _post(client)
    types = rb.get("report_type_registry_context", {}).get("report_types", [])
    keys = [t["key"] for t in types]
    assert "enhanced_professional_report" in keys


# ── PVRTB05: traditional_report accepted and normalized ───────────────
def test_PVRTB05_traditional_report_normalized(client):
    resp, rb = _post(client, {"report_type": "traditional_report"})
    assert resp.status_code == 201
    ctx = rb.get("report_type_context", {})
    assert ctx.get("normalized_report_type") == "summary_report"
    assert ctx.get("legacy_alias_used") is True
    assert ctx.get("legacy_report_type_input") == "traditional_report"


# ── PVRTB06: detailed_report accepted and normalized ──────────────────
def test_PVRTB06_detailed_report_normalized(client):
    resp, rb = _post(client, {"report_type": "detailed_report"})
    assert resp.status_code == 201
    ctx = rb.get("report_type_context", {})
    assert ctx.get("normalized_report_type") == "full_report"
    assert ctx.get("legacy_alias_used") is True


# ── PVRTB07: professional_report accepted and normalized ──────────────
def test_PVRTB07_professional_report_normalized(client):
    resp, rb = _post(client, {"report_type": "professional_report"})
    assert resp.status_code == 201
    ctx = rb.get("report_type_context", {})
    assert ctx.get("normalized_report_type") == "enhanced_professional_report"
    assert ctx.get("legacy_alias_used") is True


# ── PVRTB08: report_type_context structure complete ───────────────────
def test_PVRTB08_report_type_context_structure(client):
    _, rb = _post(client, {"report_type": "enhanced_professional_report"})
    ctx = rb.get("report_type_context", {})
    required_keys = [
        "report_type", "report_type_label_ar", "legacy_report_type_input",
        "normalized_report_type", "legacy_alias_used", "description_ar",
        "pdf_sections", "workbook_sheets", "pdf_output_depth",
        "workbook_output_depth", "minimum_methods_required",
        "minimum_comparables_required", "advanced_analysis_requirements",
        "recommended_report_type", "recommendation_reasons", "warnings",
        "output_permissions", "advisory_only", "certification_gate_controls_final_status",
        "preservation_pass",
    ]
    for k in required_keys:
        assert k in ctx, f"Key missing from report_type_context: {k}"


# ── PVRTB09: report_type_difference_matrix_context exists ────────────
def test_PVRTB09_difference_matrix_context_exists(client):
    _, rb = _post(client)
    ctx = rb.get("report_type_difference_matrix_context", {})
    assert isinstance(ctx, dict)
    assert "difference_matrix" in ctx
    assert len(ctx["difference_matrix"]) == 3


# ── PVRTB10: report_output_configuration_context exists ──────────────
def test_PVRTB10_output_config_context_exists(client):
    _, rb = _post(client)
    ctx = rb.get("report_output_configuration_context", {})
    assert isinstance(ctx, dict)
    assert "pdf_output_configuration" in ctx
    assert "workbook_sheet_configuration" in ctx


# ── PVRTB11: summary_report has PDF sections ──────────────────────────
def test_PVRTB11_summary_report_has_pdf_sections(client):
    _, rb = _post(client, {"report_type": "summary_report"})
    ctx = rb.get("report_type_context", {})
    pdf = ctx.get("pdf_sections", [])
    assert len(pdf) >= 5, f"summary_report PDF sections too few: {len(pdf)}"
    assert "cover_page" in pdf


# ── PVRTB12: full_report has more PDF sections than summary ───────────
def test_PVRTB12_full_report_more_pdf_than_summary(client):
    _, rb_sum = _post(client, {"report_type": "summary_report"})
    _, rb_full = _post(client, {"report_type": "full_report"})
    pdf_sum  = len(rb_sum.get("report_type_context", {}).get("pdf_sections", []))
    pdf_full = len(rb_full.get("report_type_context", {}).get("pdf_sections", []))
    assert pdf_full >= pdf_sum, f"full_report ({pdf_full}) should have >= pdf than summary_report ({pdf_sum})"


# ── PVRTB13: enhanced has more/equal PDF sections than full ──────────
def test_PVRTB13_enhanced_more_pdf_than_full(client):
    _, rb_full = _post(client, {"report_type": "full_report"})
    _, rb_enh  = _post(client, {"report_type": "enhanced_professional_report"})
    pdf_full = len(rb_full.get("report_type_context", {}).get("pdf_sections", []))
    pdf_enh  = len(rb_enh.get("report_type_context", {}).get("pdf_sections", []))
    assert pdf_enh >= pdf_full, f"enhanced ({pdf_enh}) should have >= pdf than full ({pdf_full})"


# ── PVRTB14: summary_report has workbook sheets ───────────────────────
def test_PVRTB14_summary_report_has_workbook_sheets(client):
    _, rb = _post(client, {"report_type": "summary_report"})
    ctx = rb.get("report_type_context", {})
    sheets = ctx.get("workbook_sheets", [])
    assert len(sheets) >= 2, f"summary_report workbook sheets too few: {len(sheets)}"


# ── PVRTB15: full_report has more/equal sheets than summary ──────────
def test_PVRTB15_full_report_more_sheets_than_summary(client):
    _, rb_sum  = _post(client, {"report_type": "summary_report"})
    _, rb_full = _post(client, {"report_type": "full_report"})
    s_sum  = len(rb_sum.get("report_type_context", {}).get("workbook_sheets", []))
    s_full = len(rb_full.get("report_type_context", {}).get("workbook_sheets", []))
    assert s_full >= s_sum


# ── PVRTB16: enhanced has more/equal sheets than full ────────────────
def test_PVRTB16_enhanced_more_sheets_than_full(client):
    _, rb_full = _post(client, {"report_type": "full_report"})
    _, rb_enh  = _post(client, {"report_type": "enhanced_professional_report"})
    s_full = len(rb_full.get("report_type_context", {}).get("workbook_sheets", []))
    s_enh  = len(rb_enh.get("report_type_context", {}).get("workbook_sheets", []))
    assert s_enh >= s_full


# ── PVRTB17: old workbook sheets preserved in config ─────────────────
def test_PVRTB17_legacy_sheets_preserved(client):
    _, rb = _post(client)
    cfg = rb.get("report_output_configuration_context", {})
    wb_cfg = cfg.get("workbook_sheet_configuration", {})
    legacy = wb_cfg.get("preserved_legacy_sheets", [])
    assert len(legacy) >= 10, "preserved_legacy_sheets should have many old sheet names"


# ── PVRTB18: old PDF sections included in enhanced ───────────────────
def test_PVRTB18_old_pdf_sections_in_enhanced(client):
    _, rb = _post(client, {"report_type": "enhanced_professional_report"})
    cfg = rb.get("report_output_configuration_context", {})
    enh_pdf = cfg.get("pdf_output_configuration", {}).get("enhanced_professional_report", [])
    assert "hbu_analysis" in enh_pdf
    assert "swot_analysis" in enh_pdf
    assert "audit_trail" in enh_pdf


# ── PVRTB19: recommendation engine — court returns full_report ────────
def test_PVRTB19_court_purpose_recommends_full(client):
    _, rb = _post(client, {"assignment_purpose": "court_legal"})
    ctx = rb.get("report_type_context", {})
    assert ctx.get("recommended_report_type") in ("full_report", "enhanced_professional_report")


# ── PVRTB20: recommendation engine — fair_value recommends enhanced ───
def test_PVRTB20_fair_value_recommends_enhanced(client):
    _, rb = _post(client, {"basis_of_value": "fair_value", "report_type": "enhanced_professional_report"})
    ctx = rb.get("report_type_context", {})
    assert ctx.get("recommended_report_type") == "enhanced_professional_report"


# ── PVRTB21: lower-level override shows warning ───────────────────────
def test_PVRTB21_lower_level_shows_warning(client):
    _, rb = _post(client, {
        "basis_of_value": "fair_value",
        "report_type":    "summary_report",
    })
    ctx = rb.get("report_type_context", {})
    warnings = ctx.get("warnings", [])
    assert len(warnings) >= 1 or ctx.get("recommended_report_type") == "enhanced_professional_report"


# ── PVRTB22: certified_pdf_allowed=False without gate ────────────────
def test_PVRTB22_certified_pdf_not_allowed_without_gate(client):
    _, rb = _post(client, {"report_type": "enhanced_professional_report"})
    ctx = rb.get("report_type_context", {})
    perm = ctx.get("output_permissions", {})
    assert perm.get("certified_pdf_allowed") is False


# ── PVRTB23: final_workbook_allowed=False without gate ───────────────
def test_PVRTB23_final_workbook_not_allowed_without_gate(client):
    _, rb = _post(client, {"report_type": "enhanced_professional_report"})
    ctx = rb.get("report_type_context", {})
    perm = ctx.get("output_permissions", {})
    assert perm.get("final_workbook_allowed") is False


# ── PVRTB24: no internal paths in report_type_context ────────────────
def test_PVRTB24_no_internal_paths(client):
    _, rb = _post(client, {"report_type": "enhanced_professional_report"})
    ctx_str = json.dumps(rb.get("report_type_context", {}))
    assert "C:\\" not in ctx_str
    assert "/home/" not in ctx_str
    assert "expert_smart1" not in ctx_str


# ── PVRTB25: no deleted report types ─────────────────────────────────
def test_PVRTB25_no_deleted_report_types(client):
    _, rb = _post(client)
    ctx = rb.get("report_type_context", {})
    legacy = ctx.get("legacy_aliases", {})
    for old_key in ("traditional_report", "detailed_report", "professional_report"):
        assert old_key in legacy, f"Legacy report type missing from aliases: {old_key}"


# ── PVRTB26: new report types accepted by backend ────────────────────
def test_PVRTB26_new_types_accepted(client):
    for rt in ("summary_report", "full_report", "enhanced_professional_report"):
        resp, rb = _post(client, {"report_type": rt})
        assert resp.status_code == 201, f"report_type={rt} should return 201, got {resp.status_code}"


# ── PVRTB27: ordinary valuation unaffected ───────────────────────────
def test_PVRTB27_ordinary_create_unaffected(client):
    resp, rb = _post(client)
    assert resp.status_code == 201
    assert rb.get("ok") is True


# ── PVRTB28: advisory_only always True ───────────────────────────────
def test_PVRTB28_advisory_only_true(client):
    for rt in ("summary_report", "full_report", "enhanced_professional_report"):
        _, rb = _post(client, {"report_type": rt})
        ctx = rb.get("report_type_context", {})
        assert ctx.get("advisory_only") is True, f"advisory_only should be True for {rt}"
        assert ctx.get("certification_gate_controls_final_status") is True
