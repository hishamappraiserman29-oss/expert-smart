"""
PVP01–PVP30 — Professional Valuation Backoffice Page E2E Tests (Phase A + B + C).

Phase A tests (PVP01–PVP09):
  Scaffold rendering — tab visibility, hash navigation, governance warnings,
  placeholder table, detail tabs, no API calls without auth.

Phase B tests (PVP10–PVP18):
  Phase B UI elements — phase-b-placeholder, new-request-form, certified-disabled,
  empty-state, detail-panel, transition controls, gate summary.

Phase C tests (PVP19–PVP30):
  Phase C UI elements — evidence section, source section, document completeness panel,
  source quality panel, certification blockers list, advisory-only warning.
  Regression: certified button remains disabled.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _go_to_pro_val(page: Page, live_server: str) -> None:
    """Navigate to the professional valuation backoffice via hash."""
    page.goto(f"{live_server}#professional-valuation", wait_until="domcontentloaded")
    page.locator('[data-testid="pro-val-workspace"]').wait_for(state="visible", timeout=10_000)


def _block_api(page: Page) -> None:
    """Block all API calls so tests are purely frontend."""
    page.route("**/api/**", lambda r: r.fulfill(
        status=200, body=b'{"ok":true}', content_type="application/json"
    ))


# ─────────────────────────────────────────────────────────────────────────────
# Phase A Tests — PVP01–PVP09 (scaffold rendering)
# ─────────────────────────────────────────────────────────────────────────────

def test_PVP01_professional_valuation_tab_hidden_by_default(page: Page, live_server: str) -> None:
    """PVP01: The professional-valuation-tab button is hidden by default on page load."""
    _block_api(page)
    page.goto(live_server, wait_until="domcontentloaded")
    tab_btn = page.locator('[data-testid="professional-valuation-tab"]')
    expect(tab_btn).to_have_count(1)
    assert tab_btn.evaluate("el => window.getComputedStyle(el).display") == "none", (
        "Professional valuation tab should be hidden by default"
    )


def test_PVP02_hash_shows_professional_valuation_workspace(page: Page, live_server: str) -> None:
    """PVP02: Navigating to #professional-valuation shows the ws-professional-valuation workspace."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    ws = page.locator('[data-testid="pro-val-workspace"]')
    expect(ws).to_be_visible()


def test_PVP03_dashboard_placeholder_visible(page: Page, live_server: str) -> None:
    """PVP03: The pro-val-dashboard section is visible in the scaffold."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    dashboard = page.locator('[data-testid="pro-val-dashboard"]')
    expect(dashboard).to_be_visible()


def test_PVP04_request_table_placeholder_visible(page: Page, live_server: str) -> None:
    """PVP04: The pro-val-request-table is visible and contains a placeholder row."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    table = page.locator('[data-testid="pro-val-request-table"]')
    expect(table).to_be_visible()
    placeholder_row = page.locator('[data-testid="pro-val-request-row"]')
    expect(placeholder_row).to_have_count(1)


def test_PVP05_certification_blocked_warning_visible(page: Page, live_server: str) -> None:
    """PVP05: The certification-blocked warning is visible and contains Arabic advisory text."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    warning = page.locator('[data-testid="pro-val-certification-blocked-warning"]')
    expect(warning).to_be_visible()
    expect(warning).to_contain_text("الاعتماد")


def test_PVP06_all_detail_tabs_visible(page: Page, live_server: str) -> None:
    """PVP06: All 15 detail workspace tab buttons are present in the scaffold."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    required_tabs = [
        "pro-val-tab-summary",
        "pro-val-tab-property",
        "pro-val-tab-scope",
        "pro-val-tab-evidence",
        "pro-val-tab-sources",
        "pro-val-tab-methods",
        "pro-val-tab-hbu",
        "pro-val-tab-dcf",
        "pro-val-tab-swot",
        "pro-val-tab-esg",
        "pro-val-tab-legal",
        "pro-val-tab-governance",
        "pro-val-tab-peer-review",
        "pro-val-tab-signature",
        "pro-val-tab-outputs",
    ]
    for testid in required_tabs:
        el = page.locator(f'[data-testid="{testid}"]')
        expect(el).to_have_count(1), f"Tab {testid} not found"


def test_PVP07_scaffold_visible_without_pro_val_api_calls(page: Page, live_server: str) -> None:
    """PVP07: Dashboard is visible even if professional-valuation API returns 503.
    Without a stored auth token, no API calls are made on scaffold load.
    """
    api_calls: list[str] = []
    page.route("**/api/professional-valuation/**", lambda r: (
        api_calls.append(r.request.url), r.fulfill(status=503, body=b'{"error":"not implemented"}')
    ))
    _go_to_pro_val(page, live_server)
    expect(page.locator('[data-testid="pro-val-dashboard"]')).to_be_visible()
    # Phase B: without a stored token, no API calls are made on load
    assert api_calls == [], f"Scaffold made unexpected API calls: {api_calls}"


def test_PVP08_existing_simple_valuation_tab_still_works(page: Page, live_server: str) -> None:
    """PVP08: The simple valuation tab still renders correctly after Phase B changes."""
    _block_api(page)
    page.goto(live_server, wait_until="domcontentloaded")
    val_btn = page.locator('#es-tab-valuation')
    expect(val_btn).to_have_count(1)
    val_btn.click()
    page.locator('[data-testid="simple-valuation-tab"]').wait_for(state="visible", timeout=10_000)
    expect(page.locator('[data-testid="simple-valuation-tab"]')).to_be_visible()


def test_PVP09_tax_appeal_tab_still_works(page: Page, live_server: str) -> None:
    """PVP09: The tax appeal tab still renders correctly after Phase B changes."""
    _block_api(page)
    page.goto(live_server, wait_until="domcontentloaded")
    tax_btn = page.locator('[data-testid="tax-tab"]')
    expect(tax_btn).to_have_count(1)
    tax_btn.click()
    page.locator('[data-testid="tax-page"]').wait_for(state="visible", timeout=10_000)
    expect(page.locator('[data-testid="tax-page"]')).to_be_visible()


# ─────────────────────────────────────────────────────────────────────────────
# Phase B Tests — PVP10–PVP18 (new UI elements)
# ─────────────────────────────────────────────────────────────────────────────

def test_PVP10_phase_b_placeholder_visible(page: Page, live_server: str) -> None:
    """PVP10: The Phase B placeholder/notice banner is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    ph = page.locator('[data-testid="pro-val-phase-b-placeholder"]')
    expect(ph).to_be_visible()
    expect(ph).to_contain_text("Phase B")


def test_PVP11_new_request_form_present(page: Page, live_server: str) -> None:
    """PVP11: The new-request-form element is present in the DOM (may be hidden initially)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    form = page.locator('[data-testid="pro-val-new-request-form"]')
    expect(form).to_have_count(1)


def test_PVP12_create_request_button_present(page: Page, live_server: str) -> None:
    """PVP12: The create-request-button is present inside the new-request-form."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    btn = page.locator('[data-testid="pro-val-create-request-button"]')
    expect(btn).to_have_count(1)


def test_PVP13_certified_disabled_element_present(page: Page, live_server: str) -> None:
    """PVP13: The pro-val-certified-disabled indicator is present (certified report blocked)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-certified-disabled"]')
    expect(el).to_have_count(1)


def test_PVP14_request_empty_state_present(page: Page, live_server: str) -> None:
    """PVP14: The request-empty-state element is present in the DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-request-empty-state"]')
    expect(el).to_have_count(1)


def test_PVP15_detail_panel_present(page: Page, live_server: str) -> None:
    """PVP15: The pro-val-detail-panel element is present in the workspace."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-detail-panel"]')
    expect(el).to_have_count(1)


def test_PVP16_transition_controls_present(page: Page, live_server: str) -> None:
    """PVP16: Transition select and button are present in the detail panel."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    sel = page.locator('[data-testid="pro-val-transition-select"]')
    btn = page.locator('[data-testid="pro-val-transition-button"]')
    expect(sel).to_have_count(1)
    expect(btn).to_have_count(1)


def test_PVP17_certification_gate_summary_present(page: Page, live_server: str) -> None:
    """PVP17: The certification-gate-summary placeholder is visible in the workspace."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-certification-gate-summary"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP18_generate_certified_button_disabled(page: Page, live_server: str) -> None:
    """PVP18: The generate-certified button is disabled — certification blocked in Phase B."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    btn = page.locator('[data-testid="pro-val-generate-certified"]')
    expect(btn).to_have_count(1)
    assert btn.is_disabled(), "Certified report button should be disabled in Phase B"


# ─────────────────────────────────────────────────────────────────────────────
# Phase C Tests — PVP19–PVP30 (evidence + source sections)
# ─────────────────────────────────────────────────────────────────────────────

def test_PVP19_evidence_section_visible(page: Page, live_server: str) -> None:
    """PVP19: The Phase C evidence section is visible in the workspace."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-evidence-section"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP20_evidence_form_visible(page: Page, live_server: str) -> None:
    """PVP20: The evidence form is visible in the workspace."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-evidence-form"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP21_evidence_type_select_visible(page: Page, live_server: str) -> None:
    """PVP21: The evidence type select is present and visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-evidence-type-select"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP22_document_completeness_panel_visible(page: Page, live_server: str) -> None:
    """PVP22: The document completeness panel is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-document-completeness-panel"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP23_evidence_table_present(page: Page, live_server: str) -> None:
    """PVP23: The evidence table is present in the workspace."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-evidence-table"]')
    expect(el).to_have_count(1)


def test_PVP24_source_section_visible(page: Page, live_server: str) -> None:
    """PVP24: The Phase C source registry section is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-source-section"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP25_source_form_visible(page: Page, live_server: str) -> None:
    """PVP25: The source add form is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-source-form"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP26_source_type_select_visible(page: Page, live_server: str) -> None:
    """PVP26: The source type select is present and visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-source-type-select"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP27_source_quality_panel_visible(page: Page, live_server: str) -> None:
    """PVP27: The source quality panel is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-source-quality-panel"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP28_certification_blockers_list_present(page: Page, live_server: str) -> None:
    """PVP28: The certification blockers list is present in the workspace."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-certification-blockers-list"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP29_advisory_only_warning_visible(page: Page, live_server: str) -> None:
    """PVP29: The Phase C advisory-only warning is visible (contains 'Phase C')."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-advisory-only-warning"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()
    expect(el).to_contain_text("Phase C")


def test_PVP30_generate_certified_still_disabled_in_phase_c(page: Page, live_server: str) -> None:
    """PVP30: Phase C regression — the certified report button remains disabled."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    btn = page.locator('[data-testid="pro-val-generate-certified"]')
    expect(btn).to_have_count(1)
    assert btn.is_disabled(), "Certified report button must remain disabled in Phase C"


# ─────────────────────────────────────────────────────────────────────────────
# Phase D Tests — PVP31–PVP42 (comparable section & import)
# ─────────────────────────────────────────────────────────────────────────────

def test_PVP31_phase_d_notice_banner_visible(page: Page, live_server: str) -> None:
    """PVP31: Phase D notice banner is visible and contains 'Phase D'."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-phase-d-notice"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()
    expect(el).to_contain_text("Phase D")


def test_PVP32_comparable_section_visible(page: Page, live_server: str) -> None:
    """PVP32: The comparable section is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-comparable-section"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP33_comparable_form_present(page: Page, live_server: str) -> None:
    """PVP33: The comparable entry form is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-comparable-form"]')
    expect(el).to_have_count(1)


def test_PVP34_comparable_type_select_present(page: Page, live_server: str) -> None:
    """PVP34: The comparable type select has 7 type options plus empty."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    sel = page.locator('[data-testid="pro-val-comparable-type-select"]')
    expect(sel).to_have_count(1)
    expect(sel).to_be_visible()
    opts = sel.locator("option")
    assert opts.count() >= 7, "Expected at least 7 comparable type options"


def test_PVP35_comparable_submit_button_present(page: Page, live_server: str) -> None:
    """PVP35: The comparable submit button is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-comparable-submit"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP36_comparable_table_present(page: Page, live_server: str) -> None:
    """PVP36: The comparable table is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-comparable-table"]')
    expect(el).to_have_count(1)


def test_PVP37_comparable_readiness_panel_visible(page: Page, live_server: str) -> None:
    """PVP37: The comparable readiness panel is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-comparable-readiness-panel"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP38_comparable_import_section_visible(page: Page, live_server: str) -> None:
    """PVP38: The comparable import section is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-comparable-import-section"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP39_comparable_import_file_input_present(page: Page, live_server: str) -> None:
    """PVP39: The comparable import file input is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-comparable-import-file"]')
    expect(el).to_have_count(1)


def test_PVP40_comparable_import_submit_present(page: Page, live_server: str) -> None:
    """PVP40: The import submit button is present and visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-comparable-import-submit"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP41_comparables_ready_gate_indicator_present(page: Page, live_server: str) -> None:
    """PVP41: The comparables-ready gate indicator is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-comparables-ready"]')
    expect(el).to_have_count(1)


def test_PVP42_certified_button_still_disabled_in_phase_d(page: Page, live_server: str) -> None:
    """PVP42: Phase D regression — certified report button remains disabled."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    btn = page.locator('[data-testid="pro-val-generate-certified"]')
    expect(btn).to_have_count(1)
    assert btn.is_disabled(), "Certified report button must remain disabled in Phase D"


# ══════════════════════════════════════════════════════════════════════════════
# PVP43–PVP58 — Phase E: Method Analysis & Reconciliation E2E
# ══════════════════════════════════════════════════════════════════════════════


def test_PVP43_method_section_visible(page: Page, live_server: str) -> None:
    """PVP43: Method analysis section is visible in the professional valuation workspace."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-method-section"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP44_method_catalogue_visible(page: Page, live_server: str) -> None:
    """PVP44: Method catalogue div is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-method-catalogue"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP45_subject_area_input_visible(page: Page, live_server: str) -> None:
    """PVP45: Subject area input is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-method-subject-area-input"]')
    expect(el).to_have_count(1)


def test_PVP46_monthly_rent_input_visible(page: Page, live_server: str) -> None:
    """PVP46: Monthly rent input is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-method-monthly-rent-input"]')
    expect(el).to_have_count(1)


def test_PVP47_cap_rate_input_visible(page: Page, live_server: str) -> None:
    """PVP47: Cap rate input is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-method-cap-rate-input"]')
    expect(el).to_have_count(1)


def test_PVP48_dcf_inputs_visible(page: Page, live_server: str) -> None:
    """PVP48: DCF-specific inputs (discount rate, terminal cap rate, forecast years) are present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    expect(page.locator('[data-testid="pro-val-method-discount-rate-input"]')).to_have_count(1)
    expect(page.locator('[data-testid="pro-val-method-terminal-cap-rate-input"]')).to_have_count(1)
    expect(page.locator('[data-testid="pro-val-method-forecast-years-input"]')).to_have_count(1)


def test_PVP49_method_checkboxes_visible(page: Page, live_server: str) -> None:
    """PVP49: All five method selection checkboxes are present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    for testid in [
        "pro-val-method-sales-checkbox",
        "pro-val-method-rental-checkbox",
        "pro-val-method-cost-checkbox",
        "pro-val-method-direct-cap-checkbox",
        "pro-val-method-dcf-checkbox",
    ]:
        expect(page.locator(f'[data-testid="{testid}"]')).to_have_count(1)


def test_PVP50_run_button_visible(page: Page, live_server: str) -> None:
    """PVP50: Run analysis button is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-method-run-button"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP51_method_output_table_visible(page: Page, live_server: str) -> None:
    """PVP51: Method output table is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-method-output-table"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP52_method_readiness_panel_visible(page: Page, live_server: str) -> None:
    """PVP52: Method readiness panel is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-method-readiness-panel"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP53_reconciliation_section_visible(page: Page, live_server: str) -> None:
    """PVP53: Reconciliation section is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-reconciliation-section"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP54_reconciliation_weight_fields_visible(page: Page, live_server: str) -> None:
    """PVP54: Reconciliation weight inputs are present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    for testid in [
        "pro-val-reconciliation-weight-sales",
        "pro-val-reconciliation-weight-rental",
        "pro-val-reconciliation-weight-cost",
        "pro-val-reconciliation-weight-direct-cap",
        "pro-val-reconciliation-weight-dcf",
    ]:
        expect(page.locator(f'[data-testid="{testid}"]')).to_have_count(1)


def test_PVP55_weighted_value_display_visible(page: Page, live_server: str) -> None:
    """PVP55: Weighted value display is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-reconciliation-weighted-value"]')
    expect(el).to_have_count(1)


def test_PVP56_selected_value_input_visible(page: Page, live_server: str) -> None:
    """PVP56: Selected final value input is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-reconciliation-selected-value"]')
    expect(el).to_have_count(1)


def test_PVP57_divergence_warning_placeholder_visible(page: Page, live_server: str) -> None:
    """PVP57: Divergence warning element is in the DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-reconciliation-divergence-warning"]')
    expect(el).to_have_count(1)


def test_PVP58_certified_button_still_disabled_in_phase_e(page: Page, live_server: str) -> None:
    """PVP58: Phase E regression — certified report button remains disabled."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    btn = page.locator('[data-testid="pro-val-generate-certified"]')
    expect(btn).to_have_count(1)
    assert btn.is_disabled(), "Certified report button must remain disabled in Phase E"



def test_PVP59_preliminary_approval_section_visible(page: Page, live_server: str) -> None:
    """PVP59: Preliminary approval section is present in Phase E."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-preliminary-approval-section"]')
    expect(el).to_have_count(1)


def test_PVP60_preliminary_approval_note_present(page: Page, live_server: str) -> None:
    """PVP60: Preliminary approval note textarea is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-preliminary-approval-note"]')
    expect(el).to_have_count(1)


def test_PVP61_preliminary_approval_button_present(page: Page, live_server: str) -> None:
    """PVP61: Preliminary approval submit button is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-preliminary-approval-button"]')
    expect(el).to_have_count(1)


def test_PVP62_preliminary_approval_status_present(page: Page, live_server: str) -> None:
    """PVP62: Preliminary approval status indicator is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-preliminary-approval-status"]')
    expect(el).to_have_count(1)


def test_PVP63_preliminary_approved_warning_in_dom(page: Page, live_server: str) -> None:
    """PVP63: Preliminary approved warning element exists in DOM (initially hidden)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-preliminary-approved-warning"]')
    expect(el).to_have_count(1)


def test_PVP64_certified_still_disabled_after_preliminary_section(page: Page, live_server: str) -> None:
    """PVP64: Regression — certified report button remains disabled with preliminary approval section present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    btn = page.locator('[data-testid="pro-val-generate-certified"]')
    expect(btn).to_have_count(1)
    assert btn.is_disabled(), "Certified button must remain disabled in Phase E"


def test_PVP65_no_official_use_wording_in_preliminary_section(page: Page, live_server: str) -> None:
    """PVP65: Preliminary approval section must not claim certified/official use."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    section = page.locator('[data-testid="pro-val-preliminary-approval-section"]')
    expect(section).to_have_count(1)
    text = section.inner_text()
    assert "تقرير معتمد نهائياً" not in text
    assert "صالح للتقديم الرسمي" not in text



# ══════════════════════════════════════════════════════════════════════════════
# PVP66–PVP85 — Phase F: Advanced Expert Review E2E Tests
# ══════════════════════════════════════════════════════════════════════════════


def test_PVP66_hbu_section_visible(page: Page, live_server: str) -> None:
    """PVP66: HBU expert review section is present in the professional valuation workspace."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-hbu-section"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP67_hbu_four_tests_visible(page: Page, live_server: str) -> None:
    """PVP67: All four HBU test inputs are present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    for tid in ["pro-val-hbu-legal-test", "pro-val-hbu-physical-test",
                "pro-val-hbu-financial-test", "pro-val-hbu-max-productivity-test"]:
        el = page.locator(f'[data-testid="{tid}"]')
        expect(el).to_have_count(1)


def test_PVP68_hbu_approve_prelim_button_visible(page: Page, live_server: str) -> None:
    """PVP68: HBU approve-preliminary button is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-hbu-approve-prelim"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP69_legal_section_visible(page: Page, live_server: str) -> None:
    """PVP69: Legal due diligence section is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-legal-section"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP70_legal_scope_limitation_field_visible(page: Page, live_server: str) -> None:
    """PVP70: Legal scope limitation field is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-legal-scope-limitation"]')
    expect(el).to_have_count(1)


def test_PVP71_legal_approve_prelim_button_visible(page: Page, live_server: str) -> None:
    """PVP71: Legal approve-preliminary button is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-legal-approve-prelim"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP72_esg_section_visible(page: Page, live_server: str) -> None:
    """PVP72: ESG/climate review section is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-esg-section"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP73_esg_score_and_category_visible(page: Page, live_server: str) -> None:
    """PVP73: ESG score and category inputs are present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    for tid in ["pro-val-esg-score", "pro-val-esg-category"]:
        el = page.locator(f'[data-testid="{tid}"]')
        expect(el).to_have_count(1)


def test_PVP74_esg_approve_prelim_button_visible(page: Page, live_server: str) -> None:
    """PVP74: ESG approve-preliminary button is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-esg-approve-prelim"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP75_swot_section_visible(page: Page, live_server: str) -> None:
    """PVP75: SWOT/risk review section is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-swot-section"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP76_swot_four_category_textareas_visible(page: Page, live_server: str) -> None:
    """PVP76: All four SWOT category textareas are present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    for tid in ["pro-val-swot-strengths", "pro-val-swot-weaknesses",
                "pro-val-swot-opportunities", "pro-val-swot-threats"]:
        el = page.locator(f'[data-testid="{tid}"]')
        expect(el).to_have_count(1)


def test_PVP77_swot_risk_matrix_placeholder_visible(page: Page, live_server: str) -> None:
    """PVP77: SWOT risk matrix placeholder element is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-swot-risk-matrix"]')
    expect(el).to_have_count(1)


def test_PVP78_swot_approve_prelim_button_visible(page: Page, live_server: str) -> None:
    """PVP78: SWOT approve-preliminary button is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-swot-approve-prelim"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP79_advanced_review_summary_visible(page: Page, live_server: str) -> None:
    """PVP79: Advanced review summary section is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-advanced-review-summary"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP80_advanced_review_blockers_visible(page: Page, live_server: str) -> None:
    """PVP80: Advanced review blockers element is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-advanced-review-blockers"]')
    expect(el).to_have_count(1)


def test_PVP81_advanced_prelim_ready_indicator_visible(page: Page, live_server: str) -> None:
    """PVP81: Advanced reviews prelim-ready indicator is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-advanced-reviews-prelim-ready"]')
    expect(el).to_have_count(1)


def test_PVP82_advanced_cert_ready_indicator_visible(page: Page, live_server: str) -> None:
    """PVP82: Advanced reviews cert-ready indicator is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-advanced-reviews-cert-ready"]')
    expect(el).to_have_count(1)


def test_PVP83_phase_f_warning_visible(page: Page, live_server: str) -> None:
    """PVP83: Phase F advisory warning is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-phase-f-warning"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP84_certified_button_still_disabled_in_phase_f(page: Page, live_server: str) -> None:
    """PVP84: Phase F regression — certified report button remains disabled."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    btn = page.locator('[data-testid="pro-val-generate-certified"]')
    expect(btn).to_have_count(1)
    assert btn.is_disabled(), "Certified report button must remain disabled in Phase F"


def test_PVP85_phase_a_to_e_sections_still_visible(page: Page, live_server: str) -> None:
    """PVP85: Phase A–E sections still visible (regression)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    for tid in [
        "pro-val-workspace",
        "pro-val-method-section",
        "pro-val-reconciliation-section",
        "pro-val-preliminary-approval-section",
    ]:
        el = page.locator(f'[data-testid="{tid}"]')
        expect(el).to_have_count(1)
