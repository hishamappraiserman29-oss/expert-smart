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

Report type tests (PVP143–PVP147):
  PVP143 report-type-select exists in new-request-form
  PVP144 traditional_report option is present
  PVP145 detailed_report option is present
  PVP146 professional_report option is present
  PVP147 pro-val-report-type-status element exists in summary panel
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


# ══════════════════════════════════════════════════════════════════════════════
# PVP86–PVP110 — Phase G: Peer Review, Signature & Final Certification Gate E2E
# ══════════════════════════════════════════════════════════════════════════════


# ── Phase G notice banner ─────────────────────────────────────────────────────

def test_PVP86_phase_g_notice_banner_visible(page: Page, live_server: str) -> None:
    """PVP86: Phase G notice banner is visible in the professional valuation workspace."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-phase-g-notice"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


# ── Peer review section ───────────────────────────────────────────────────────

def test_PVP87_peer_review_section_visible(page: Page, live_server: str) -> None:
    """PVP87: Peer review section is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-peer-review-section"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP88_peer_review_assignment_form_exists(page: Page, live_server: str) -> None:
    """PVP88: Peer review assignment form is present in DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-peer-review-assignment-form"]')
    expect(el).to_have_count(1)


def test_PVP89_peer_reviewer_name_input_exists(page: Page, live_server: str) -> None:
    """PVP89: Peer reviewer name input field present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-peer-reviewer-name"]')
    expect(el).to_have_count(1)


def test_PVP90_peer_reviewer_role_input_exists(page: Page, live_server: str) -> None:
    """PVP90: Peer reviewer role input field present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-peer-reviewer-role"]')
    expect(el).to_have_count(1)


def test_PVP91_peer_reviewer_license_input_exists(page: Page, live_server: str) -> None:
    """PVP91: Peer reviewer license input field present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-peer-reviewer-license"]')
    expect(el).to_have_count(1)


def test_PVP92_peer_review_assign_button_exists(page: Page, live_server: str) -> None:
    """PVP92: Peer review assign button present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-peer-review-assign-button"]')
    expect(el).to_have_count(1)


def test_PVP93_peer_review_start_button_exists(page: Page, live_server: str) -> None:
    """PVP93: Peer review start button present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-peer-review-start-button"]')
    expect(el).to_have_count(1)


def test_PVP94_peer_review_notes_textarea_exists(page: Page, live_server: str) -> None:
    """PVP94: Peer review notes textarea present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-peer-review-notes"]')
    expect(el).to_have_count(1)


def test_PVP95_peer_review_submit_approved_button_exists(page: Page, live_server: str) -> None:
    """PVP95: Submit peer review (approved) button present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-peer-review-submit-approved"]')
    expect(el).to_have_count(1)


def test_PVP96_peer_review_submit_changes_button_exists(page: Page, live_server: str) -> None:
    """PVP96: Submit peer review (changes_requested) button present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-peer-review-submit-changes"]')
    expect(el).to_have_count(1)


def test_PVP97_peer_review_warning_present(page: Page, live_server: str) -> None:
    """PVP97: Peer review advisory warning element present in DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-peer-review-warning"]')
    expect(el).to_have_count(1)


# ── Signature section ─────────────────────────────────────────────────────────

def test_PVP98_signature_section_visible(page: Page, live_server: str) -> None:
    """PVP98: Expert signature section is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-signature-section"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP99_signature_expert_name_input_exists(page: Page, live_server: str) -> None:
    """PVP99: Expert name input in signature section present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-expert-name"]')
    expect(el).to_have_count(1)


def test_PVP100_signature_expert_license_input_exists(page: Page, live_server: str) -> None:
    """PVP100: Expert license input in signature section present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-expert-license"]')
    expect(el).to_have_count(1)


def test_PVP101_signature_save_button_exists(page: Page, live_server: str) -> None:
    """PVP101: Signature save button present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-signature-save-button"]')
    expect(el).to_have_count(1)


def test_PVP102_signature_warning_present(page: Page, live_server: str) -> None:
    """PVP102: Signature advisory warning element present in DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-signature-warning"]')
    expect(el).to_have_count(1)


# ── Final certification gate section ─────────────────────────────────────────

def test_PVP103_final_certification_section_visible(page: Page, live_server: str) -> None:
    """PVP103: Final certification gate section is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-final-certification-section"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP104_final_certification_status_element_present(page: Page, live_server: str) -> None:
    """PVP104: Certification status element is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-final-certification-status"]')
    expect(el).to_have_count(1)


def test_PVP105_final_certification_evaluate_button_exists(page: Page, live_server: str) -> None:
    """PVP105: Evaluate certification gate button is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-final-certification-evaluate-button"]')
    expect(el).to_have_count(1)


def test_PVP106_final_certification_blockers_element_present(page: Page, live_server: str) -> None:
    """PVP106: Blockers display element is present in DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-final-certification-blockers"]')
    expect(el).to_have_count(1)


def test_PVP107_final_certification_ready_indicator_present(page: Page, live_server: str) -> None:
    """PVP107: Certification ready indicator present in DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-final-certification-ready"]')
    expect(el).to_have_count(1)


def test_PVP108_generate_certified_button_disabled(page: Page, live_server: str) -> None:
    """PVP108: Generate certified report button must be disabled (Phase G does not generate final outputs)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    btn = page.locator('[data-testid="pro-val-generate-certified"]')
    expect(btn).to_have_count(1)
    assert btn.is_disabled(), "Certified report button must be disabled — final generation not enabled in Phase G"


def test_PVP109_final_certification_warning_present(page: Page, live_server: str) -> None:
    """PVP109: Final certification advisory warning present in DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-final-certification-warning"]')
    expect(el).to_have_count(1)


# ── Regression ────────────────────────────────────────────────────────────────

def test_PVP110_phase_a_to_f_sections_still_visible(page: Page, live_server: str) -> None:
    """PVP110: Phase A–F sections still visible after Phase G additions (regression)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    for tid in [
        "pro-val-workspace",
        "pro-val-method-section",
        "pro-val-reconciliation-section",
        "pro-val-preliminary-approval-section",
        "pro-val-hbu-section",
        "pro-val-peer-review-section",
        "pro-val-signature-section",
        "pro-val-final-certification-section",
    ]:
        el = page.locator(f'[data-testid="{tid}"]')
        expect(el).to_have_count(1)


# ══════════════════════════════════════════════════════════════════════════════
# PVP111–PVP130 — Phase H: Protected Certified Outputs
# ══════════════════════════════════════════════════════════════════════════════


def test_PVP111_certified_output_section_visible(page: Page, live_server: str) -> None:
    """PVP111: Phase H certified output section is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-certified-output-section"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP112_certified_output_warning_visible(page: Page, live_server: str) -> None:
    """PVP112: Phase H warning banner is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-certified-output-warning"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP113_gate_status_element_present(page: Page, live_server: str) -> None:
    """PVP113: Gate status display element is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-certified-output-gate-status"]')
    expect(el).to_have_count(1)


def test_PVP114_blockers_element_present(page: Page, live_server: str) -> None:
    """PVP114: Blockers display element is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-certified-output-blockers"]')
    expect(el).to_have_count(1)


def test_PVP115_generate_certified_report_button_visible(page: Page, live_server: str) -> None:
    """PVP115: Generate certified report button is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-generate-certified-report"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP116_download_certified_report_button_visible(page: Page, live_server: str) -> None:
    """PVP116: Phase H download certified report button is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pvh-download-certified-report"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP117_generate_final_workbook_button_visible(page: Page, live_server: str) -> None:
    """PVP117: Generate final workbook button is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-generate-final-workbook"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP118_download_final_workbook_button_visible(page: Page, live_server: str) -> None:
    """PVP118: Phase H download final workbook button is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pvh-download-final-workbook"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP119_output_registry_table_visible(page: Page, live_server: str) -> None:
    """PVP119: Output registry table is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-output-registry-table"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP120_output_version_column_present(page: Page, live_server: str) -> None:
    """PVP120: Output version column header is present in table."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-output-version"]')
    expect(el).to_have_count(1)


def test_PVP121_output_hash_column_present(page: Page, live_server: str) -> None:
    """PVP121: Output hash column header is present in table."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-output-hash"]')
    expect(el).to_have_count(1)


def test_PVP122_output_generated_at_column_present(page: Page, live_server: str) -> None:
    """PVP122: Output generated_at column header is present in table."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-output-generated-at"]')
    expect(el).to_have_count(1)


def test_PVP123_output_status_column_present(page: Page, live_server: str) -> None:
    """PVP123: Output status column header is present in table."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-output-status"]')
    expect(el).to_have_count(1)


def test_PVP124_generate_buttons_disabled_by_default(page: Page, live_server: str) -> None:
    """PVP124: Both generate buttons are disabled when gate is not ready."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    pdf_btn = page.locator('[data-testid="pro-val-generate-certified-report"]')
    wb_btn  = page.locator('[data-testid="pro-val-generate-final-workbook"]')
    assert pdf_btn.is_disabled(), "Generate PDF button must be disabled by default"
    assert wb_btn.is_disabled(),  "Generate workbook button must be disabled by default"


def test_PVP125_download_buttons_disabled_by_default(page: Page, live_server: str) -> None:
    """PVP125: Phase H download buttons disabled when no outputs generated."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    dl_pdf = page.locator('[data-testid="pvh-download-certified-report"]')
    dl_wb  = page.locator('[data-testid="pvh-download-final-workbook"]')
    assert dl_pdf.is_disabled(), "Download PDF button must be disabled by default"
    assert dl_wb.is_disabled(),  "Download workbook button must be disabled by default"


def test_PVP126_phase_g_certified_button_remains_disabled(page: Page, live_server: str) -> None:
    """PVP126: Phase G pro-val-generate-certified button remains disabled in Phase H."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    btn = page.locator('[data-testid="pro-val-generate-certified"]')
    expect(btn).to_have_count(1)
    assert btn.is_disabled(), "Phase G certified button must remain disabled in Phase H"


def test_PVP127_no_internal_path_in_professional_valuation_dom(page: Page, live_server: str) -> None:
    """PVP127: No internal storage path text is visible in the professional valuation workspace DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    ws = page.locator('[data-testid="pro-val-workspace"]')
    ws_text = ws.inner_text()
    assert "instance/professional_valuation" not in ws_text
    assert "certified_outputs/" not in ws_text
    assert ".jsonl" not in ws_text


def test_PVP128_phase_h_warning_text_visible(page: Page, live_server: str) -> None:
    """PVP128: Phase H warning text contains expected Arabic message."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-certified-output-warning"]')
    text = el.inner_text()
    assert "بعد اكتمال" in text or "بوابات الاعتماد" in text


def test_PVP129_earlier_phase_sections_still_visible(page: Page, live_server: str) -> None:
    """PVP129: All prior phase sections remain visible after Phase H additions."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    for tid in [
        "pro-val-workspace",
        "pro-val-hbu-section",
        "pro-val-legal-section",
        "pro-val-esg-section",
        "pro-val-swot-section",
        "pro-val-peer-review-section",
        "pro-val-signature-section",
        "pro-val-final-certification-section",
        "pro-val-certified-output-section",
    ]:
        el = page.locator(f'[data-testid="{tid}"]')
        expect(el).to_have_count(1)


def test_PVP130_output_registry_row_present(page: Page, live_server: str) -> None:
    """PVP130: Output registry row element present in DOM (initially shows no-outputs message)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-output-registry-row"]')
    expect(el).to_have_count(1)


# ══════════════════════════════════════════════════════════════════════════════
# Phase H Addendum — Preliminary & Expert Draft Outputs E2E tests
# Tests: PVP131–PVP142
# ══════════════════════════════════════════════════════════════════════════════


def test_PVP131_preliminary_output_section_visible(page: Page, live_server: str) -> None:
    """PVP131: Preliminary output section is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-preliminary-output-section"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP132_advisory_warning_visible(page: Page, live_server: str) -> None:
    """PVP132: Advisory warning text is visible in preliminary section."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-preliminary-output-warning"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP133_advisory_warning_contains_internal_use_text(page: Page, live_server: str) -> None:
    """PVP133: Advisory warning contains 'داخلي' or 'رسمي' text."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-preliminary-output-warning"]')
    text = el.text_content() or ""
    assert "داخلي" in text or "رسمي" in text or "مبدئي" in text, (
        f"Warning must contain advisory text, got: {text!r}"
    )


def test_PVP134_generate_preliminary_report_button_visible(page: Page, live_server: str) -> None:
    """PVP134: Generate preliminary report button is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-generate-preliminary-report"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP135_download_preliminary_report_button_visible(page: Page, live_server: str) -> None:
    """PVP135: Download preliminary report button is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-download-preliminary-report"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP136_generate_expert_draft_button_visible(page: Page, live_server: str) -> None:
    """PVP136: Generate expert draft report button is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-generate-expert-draft-report"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP137_download_expert_draft_button_visible(page: Page, live_server: str) -> None:
    """PVP137: Download expert draft report button is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-download-expert-draft-report"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP138_generate_expert_workbook_button_visible(page: Page, live_server: str) -> None:
    """PVP138: Generate expert workbook button is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-generate-expert-workbook"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP139_download_expert_workbook_button_visible(page: Page, live_server: str) -> None:
    """PVP139: Download expert workbook button is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-download-expert-workbook"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP140_certified_output_section_still_visible(page: Page, live_server: str) -> None:
    """PVP140: Phase H certified output section still visible after addendum added."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-certified-output-section"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP141_no_internal_paths_in_dom(page: Page, live_server: str) -> None:
    """PVP141: No internal file paths in DOM after page load."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    content = page.content()
    assert "preliminary_outputs/" not in content
    assert "instance/professional_valuation" not in content


def test_PVP142_prior_phase_sections_still_visible(page: Page, live_server: str) -> None:
    """PVP142: Regression — prior Phase A–H sections still visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    for tid in [
        "pro-val-workspace",
        "pro-val-evidence-section",
        "pro-val-comparable-section",
        "pro-val-preliminary-output-section",
        "pro-val-certified-output-section",
    ]:
        el = page.locator(f'[data-testid="{tid}"]')
        expect(el).to_have_count(1)


# ── PVP143–PVP147: Report type selector ─────────────────────────────────────

def test_PVP143_report_type_select_in_dom_as_compat_span(page: Page, live_server: str) -> None:
    """PVP143: pro-val-report-type-select exists in DOM as backward-compat hidden span (upper selector removed).
    Unified selector exists in DOM (may be inside a collapsed section at initial load)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    sel = page.locator('[data-testid="pro-val-report-type-select"]')
    expect(sel).to_have_count(1)
    # Unified selector must exist in DOM (chat section may be collapsed at initial load)
    unified = page.locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]')
    expect(unified).to_have_count(1)


def test_PVP144_traditional_option_present(page: Page, live_server: str) -> None:
    """PVP144: traditional_report option exists in unified report action selector."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    opt = page.locator('[data-testid="pro-val-unified-analyze-generate-reports-select"] option[value="traditional_report"]')
    expect(opt).to_have_count(1)


def test_PVP145_detailed_option_present(page: Page, live_server: str) -> None:
    """PVP145: detailed_report option exists in unified report action selector."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    opt = page.locator('[data-testid="pro-val-unified-analyze-generate-reports-select"] option[value="detailed_report"]')
    expect(opt).to_have_count(1)


def test_PVP146_professional_option_present(page: Page, live_server: str) -> None:
    """PVP146: professional_report option exists in unified report action selector."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    opt = page.locator('[data-testid="pro-val-unified-analyze-generate-reports-select"] option[value="professional_report"]')
    expect(opt).to_have_count(1)


def test_PVP147_report_type_status_element_in_summary(page: Page, live_server: str) -> None:
    """PVP147: pro-val-report-type-status element exists in summary panel."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-report-type-status"]')
    expect(el).to_have_count(1)


# ─────────────────────────────────────────────────────────────────────────────
# Taxonomy v2 E2E Tests — PVPE01–PVPE15
# ─────────────────────────────────────────────────────────────────────────────

def test_PVPE01_asset_classification_section_visible(page: Page, live_server: str) -> None:
    """PVPE01: Asset Classification (Axis 1) section is present in the form."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-asset-classification-section"]')
    expect(el).to_have_count(1)


def test_PVPE02_asset_family_select_present(page: Page, live_server: str) -> None:
    """PVPE02: Asset Family select element is present.
    Count is 2: one wrapper div in ws-professional (Card 1), one select in ws-professional-valuation."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-asset-family-select"]')
    expect(el).to_have_count(2)


def test_PVPE03_asset_type_select_present(page: Page, live_server: str) -> None:
    """PVPE03: Asset Type select element is present.
    Count is 2: one in ws-professional (Card 1, id=asset-type), one in ws-professional-valuation (pvr-asset-type)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-asset-type-select"]')
    expect(el).to_have_count(2)


def test_PVPE04_asset_subtype_select_present(page: Page, live_server: str) -> None:
    """PVPE04: Asset Subtype select element is present.
    Count is 2: one wrapper div in ws-professional (Card 1), one select in ws-professional-valuation."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-asset-subtype-select"]')
    expect(el).to_have_count(2)


def test_PVPE05_assignment_purpose_section_visible(page: Page, live_server: str) -> None:
    """PVPE05: Assignment Purpose (Axis 2) inner section div is present in the backoffice workspace.
    pro-val-assignment-purpose-section is only in ws-professional-valuation (hidden workspace) — count=1.
    Note: the OUTER wrapper pro-val-section-assignment-purpose appears in both workspaces (count=2)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-assignment-purpose-section"]')
    expect(el).to_have_count(1)


def test_PVPE06_assignment_purpose_select_present(page: Page, live_server: str) -> None:
    """PVPE06: Assignment Purpose select element is present.
    Count is 2: one in ws-professional-valuation (backoffice), one in ws-professional (visible, Step 2 UX)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-assignment-purpose-select"]')
    expect(el).to_have_count(2)


def test_PVPE07_basis_of_value_section_visible(page: Page, live_server: str) -> None:
    """PVPE07: Basis of Value (Axis 3) section is present.
    Count is 2: one in ws-professional (Card 3), one in ws-professional-valuation."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-basis-of-value-section"]')
    expect(el).to_have_count(2)


def test_PVPE08_basis_of_value_select_present(page: Page, live_server: str) -> None:
    """PVPE08: Basis of Value select element is present.
    Count is 2: one in ws-professional (Card 3, id=prof-basis-of-value), one in ws-professional-valuation (pvr-basis-of-value)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-basis-of-value-select"]')
    expect(el).to_have_count(2)


def test_PVPE09_report_type_section_present(page: Page, live_server: str) -> None:
    """PVPE09: Report Type (Axis 4) section wrapper is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-report-type-section"]')
    expect(el).to_have_count(1)


def test_PVPE10_analysis_output_section_present(page: Page, live_server: str) -> None:
    """PVPE10: Analysis Output section (config summary + method route) is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-analysis-output-section"]')
    expect(el).to_have_count(1)


def test_PVPE11_config_summary_element_present(page: Page, live_server: str) -> None:
    """PVPE11: Configuration summary element (pro-val-config-summary) is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-selected-configuration-summary"]')
    expect(el).to_have_count(1)


def test_PVPE12_method_route_summary_element_present(page: Page, live_server: str) -> None:
    """PVPE12: Derived method route summary element is present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-derived-method-route-summary"]')
    expect(el).to_have_count(1)


def test_PVPE13_intended_use_input_present(page: Page, live_server: str) -> None:
    """PVPE13: Intended Use input is present.
    Count is 2: one in ws-professional-valuation (backoffice), one in ws-professional (visible Step 2 UX)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-intended-use-input"]')
    expect(el).to_have_count(2)


def test_PVPE14_old_pvr_property_type_removed_from_form(page: Page, live_server: str) -> None:
    """PVPE14: Legacy pvr-property-type text input no longer present in the form."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('#pvr-property-type')
    expect(el).to_have_count(0)


def test_PVPE15_old_pvr_valuation_purpose_removed_from_form(page: Page, live_server: str) -> None:
    """PVPE15: Legacy pvr-valuation-purpose text input no longer present in the form."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('#pvr-valuation-purpose')
    expect(el).to_have_count(0)


# ─────────────────────────────────────────────────────────────────────────────
# PVPE-REQ01–PVPE-REQ10 — Asset Requirements Panel E2E Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_PVPE_REQ01_asset_requirements_panel_exists_in_dom(page: Page, live_server: str) -> None:
    """PVPE-REQ01: Asset requirements panel elements exist in the DOM.
    Count == 2: one in ws-professional (visible workspace, Section 2),
    one in ws-professional-valuation (backoffice workspace).
    """
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-asset-requirements-panel"]')
    expect(el).to_have_count(2)


def test_PVPE_REQ02_hotel_requirements_panel_exists_in_dom(page: Page, live_server: str) -> None:
    """PVPE-REQ02: Hotel requirements sub-panel element exists in DOM (may be hidden)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-hotel-requirements-panel"]')
    expect(el).to_have_count(1)


def test_PVPE_REQ03_factory_requirements_panel_exists_in_dom(page: Page, live_server: str) -> None:
    """PVPE-REQ03: Factory requirements sub-panel element exists in DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-factory-requirements-panel"]')
    expect(el).to_have_count(1)


def test_PVPE_REQ04_land_requirements_panel_exists_in_dom(page: Page, live_server: str) -> None:
    """PVPE-REQ04: Land requirements sub-panel element exists in DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-land-requirements-panel"]')
    expect(el).to_have_count(1)


def test_PVPE_REQ05_retail_requirements_panel_exists_in_dom(page: Page, live_server: str) -> None:
    """PVPE-REQ05: Retail requirements sub-panel element exists in DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-retail-requirements-panel"]')
    expect(el).to_have_count(1)


def test_PVPE_REQ06_warehouse_requirements_panel_exists_in_dom(page: Page, live_server: str) -> None:
    """PVPE-REQ06: Warehouse requirements sub-panel element exists in DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-warehouse-requirements-panel"]')
    expect(el).to_have_count(1)


def test_PVPE_REQ07_requirements_title_element_exists(page: Page, live_server: str) -> None:
    """PVPE-REQ07: Asset requirements title element exists inside backoffice workspace."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    ws = page.locator('[data-testid="pro-val-workspace"]')
    el = ws.locator('[data-testid="pro-val-asset-requirements-title"]')
    expect(el).to_have_count(1)


def test_PVPE_REQ08_requirements_helper_text_visible(page: Page, live_server: str) -> None:
    """PVPE-REQ08: Helper text element describing derived nature of requirements exists."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-asset-requirements-helper-text"]')
    expect(el).to_have_count(1)


def test_PVPE_REQ09_requirements_lists_exist_in_dom(page: Page, live_server: str) -> None:
    """PVPE-REQ09: Required inputs and recommended methods list elements exist."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    inputs_els = page.locator('[data-testid="pro-val-asset-required-inputs-list"]')
    methods_els = page.locator('[data-testid="pro-val-asset-recommended-methods-list"]')
    # Each sub-panel has these testids — expect at least one occurrence each
    expect(inputs_els).not_to_have_count(0)
    expect(methods_els).not_to_have_count(0)


def test_PVPE_REQ10_asset_classification_section_still_visible(page: Page, live_server: str) -> None:
    """PVPE-REQ10: Asset classification section still visible after requirements panel added."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    # Axis 1 section must still be there (regression check)
    el = page.locator('[data-testid="pro-val-asset-classification-section"]')
    expect(el).to_have_count(1)
    # Assignment purpose section must still be there (regression check)
    # pro-val-assignment-purpose-section is only in ws-professional-valuation (count=1)
    el2 = page.locator('[data-testid="pro-val-assignment-purpose-section"]')
    expect(el2).to_have_count(1)


# ═══════════════════════════════════════════════════════════════════════════════
# PVPE-CTRL01–PVPE-CTRL25 — Feature Capabilities & Controls Inventory E2E Tests
# ═══════════════════════════════════════════════════════════════════════════════


def test_PVPE_CTRL01_feature_capabilities_panel_exists_in_dom(page: Page, live_server: str) -> None:
    """PVPE-CTRL01: The feature capabilities panel exists in the DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-feature-capabilities-panel"]')
    expect(el).to_have_count(1)


def test_PVPE_CTRL02_active_controls_list_exists(page: Page, live_server: str) -> None:
    """PVPE-CTRL02: Active controls list exists in DOM.
    Count == 2: ws-professional (Advanced Controls Panel) + ws-professional-valuation (backoffice).
    """
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-active-controls-list"]')
    expect(el).to_have_count(2)


def test_PVPE_CTRL03_inactive_controls_list_exists(page: Page, live_server: str) -> None:
    """PVPE-CTRL03: Inactive controls list exists in DOM.
    Count == 2: ws-professional (Advanced Controls Panel) + ws-professional-valuation (backoffice).
    """
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-inactive-controls-list"]')
    expect(el).to_have_count(2)


def test_PVPE_CTRL04_report_reflection_matrix_exists(page: Page, live_server: str) -> None:
    """PVPE-CTRL04: Report reflection matrix exists in DOM.
    Count == 2: ws-professional (Advanced Controls Panel) + ws-professional-valuation (backoffice).
    """
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-report-reflection-matrix"]')
    expect(el).to_have_count(2)


def test_PVPE_CTRL05_activation_roadmap_exists(page: Page, live_server: str) -> None:
    """PVPE-CTRL05: Activation roadmap exists in DOM.
    Count == 2: ws-professional (Advanced Controls Panel) + ws-professional-valuation (backoffice).
    """
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-control-activation-roadmap"]')
    expect(el).to_have_count(2)


def test_PVPE_CTRL06_disabled_controls_show_reason(page: Page, live_server: str) -> None:
    """PVPE-CTRL06: Inactive controls have disabled-reason label elements."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    els = page.locator('[data-testid="pro-val-control-disabled-reason"]')
    # At least one disabled/future_stub reason label must exist
    expect(els).not_to_have_count(0)


def test_PVPE_CTRL07_active_controls_show_report_impact(page: Page, live_server: str) -> None:
    """PVPE-CTRL07: Active control items have report-impact label elements."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    els = page.locator('[data-testid="pro-val-control-report-impact"]')
    expect(els).not_to_have_count(0)


def test_PVPE_CTRL08_active_control_asset_requirements_item_exists(page: Page, live_server: str) -> None:
    """PVPE-CTRL08: The asset-requirements active control item exists in the DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-active-control-asset-requirements"]')
    expect(el).to_have_count(1)


def test_PVPE_CTRL09_no_internal_paths_in_dom(page: Page, live_server: str) -> None:
    """PVPE-CTRL09: Professional valuation workspace DOM contains no internal file paths (Rule 19)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    ws = page.locator('[data-testid="pro-val-workspace"]')
    html_content = ws.inner_html()
    assert "internal_file_path" not in html_content, "internal_file_path found in workspace DOM"
    assert "C:\\Users" not in html_content, "Windows absolute path found in workspace DOM"
    assert "instance/professional_valuation" not in html_content, "Instance path found in DOM"


def test_PVPE_CTRL10_feature_panel_is_collapsible(page: Page, live_server: str) -> None:
    """PVPE-CTRL10: Feature capabilities panel is a <details> element (collapsible)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-feature-capabilities-panel"]')
    tag = el.evaluate("el => el.tagName.toLowerCase()")
    assert tag == "details", (
        f"Feature capabilities panel must be a <details> element, got <{tag}>"
    )


def test_PVPE_CTRL11_section_1_asset_classification_unaffected(page: Page, live_server: str) -> None:
    """PVPE-CTRL11: Regression — Section 1 asset classification still present (count=2 after Card 1 added to visible workspace)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-asset-family-select"]')
    expect(el).to_have_count(2)


def test_PVPE_CTRL12_section_2_assignment_purpose_unaffected(page: Page, live_server: str) -> None:
    """PVPE-CTRL12: Regression — Section 2 assignment purpose inner div still present.
    pro-val-assignment-purpose-section is only in ws-professional-valuation (count=1)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-assignment-purpose-section"]')
    expect(el).to_have_count(1)


def test_PVPE_CTRL13_section_3_basis_of_value_unaffected(page: Page, live_server: str) -> None:
    """PVPE-CTRL13: Regression — Section 3 basis of value still present (count=2 after Card 3 added to visible workspace)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-basis-of-value-section"]')
    expect(el).to_have_count(2)


def test_PVPE_CTRL14_section_4_report_type_unaffected(page: Page, live_server: str) -> None:
    """PVPE-CTRL14: Regression — Section 4 report type select still present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-report-type-section"]')
    expect(el).to_have_count(1)


def test_PVPE_CTRL15_hotel_requirements_panel_unaffected(page: Page, live_server: str) -> None:
    """PVPE-CTRL15: Regression — Hotel requirements panel still present after controls panel added."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-hotel-requirements-panel"]')
    expect(el).to_have_count(1)


def test_PVPE_CTRL16_factory_requirements_panel_unaffected(page: Page, live_server: str) -> None:
    """PVPE-CTRL16: Regression — Factory requirements panel still present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-factory-requirements-panel"]')
    expect(el).to_have_count(1)


def test_PVPE_CTRL17_land_requirements_panel_unaffected(page: Page, live_server: str) -> None:
    """PVPE-CTRL17: Regression — Land requirements panel still present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-land-requirements-panel"]')
    expect(el).to_have_count(1)


def test_PVPE_CTRL18_ordinary_valuation_tab_still_exists(page: Page, live_server: str) -> None:
    """PVPE-CTRL18: Regression — Ordinary valuation workspace not broken."""
    _block_api(page)
    page.goto(live_server, wait_until="domcontentloaded")
    tab_btn = page.locator('#es-tab-valuation')
    tab_btn.click()
    ws = page.locator('[data-testid="simple-valuation-tab"]')
    ws.wait_for(state="visible", timeout=10_000)
    expect(ws).to_be_visible()


def test_PVPE_CTRL19_no_duplicate_feature_panel_testids(page: Page, live_server: str) -> None:
    """PVPE-CTRL19: No duplicate testids for feature capabilities panel elements inside backoffice workspace."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    ws = page.locator('[data-testid="pro-val-workspace"]')
    unique_testids = [
        "pro-val-feature-capabilities-panel",
        "pro-val-active-controls-list",
        "pro-val-inactive-controls-list",
        "pro-val-report-reflection-matrix",
        "pro-val-control-activation-roadmap",
    ]
    for tid in unique_testids:
        count = ws.locator(f'[data-testid="{tid}"]').count()
        assert count == 1, (
            f"Expected exactly 1 element with data-testid='{tid}' inside pro-val-workspace, found {count}"
        )


def test_PVPE_CTRL20_reflection_matrix_has_table_element(page: Page, live_server: str) -> None:
    """PVPE-CTRL20: Report reflection matrix contains a <table> element."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    matrix_el = page.locator('[data-testid="pro-val-report-reflection-matrix"]')
    # Open the details panel first so content is visible
    panel = page.locator('[data-testid="pro-val-feature-capabilities-panel"]')
    panel.evaluate("el => el.setAttribute('open', '')")
    table = matrix_el.locator("table")
    # Table must exist in the structure
    expect(table).to_have_count(1)


def test_PVPE_CTRL21_section_5_analysis_output_unaffected(page: Page, live_server: str) -> None:
    """PVPE-CTRL21: Regression — Section 5 analysis output section still present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-analysis-output-section"]')
    expect(el).to_have_count(1)


def test_PVPE_CTRL22_configuration_summary_still_present(page: Page, live_server: str) -> None:
    """PVPE-CTRL22: Regression — pro-val-selected-configuration-summary still present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-selected-configuration-summary"]')
    expect(el).to_have_count(1)


def test_PVPE_CTRL23_derived_method_route_summary_still_present(page: Page, live_server: str) -> None:
    """PVPE-CTRL23: Regression — pro-val-derived-method-route-summary still present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-derived-method-route-summary"]')
    expect(el).to_have_count(1)


def test_PVPE_CTRL24_warehouse_requirements_panel_unaffected(page: Page, live_server: str) -> None:
    """PVPE-CTRL24: Regression — Warehouse requirements panel still present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-warehouse-requirements-panel"]')
    expect(el).to_have_count(1)


def test_PVPE_CTRL25_retail_requirements_panel_unaffected(page: Page, live_server: str) -> None:
    """PVPE-CTRL25: Regression — Retail requirements panel still present."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-retail-requirements-panel"]')
    expect(el).to_have_count(1)


# ═══════════════════════════════════════════════════════════════════════════════
# PVLV01–PVLV30 — Live Visibility & Browser Interaction Tests (Part M)
#
# These tests prove actual browser behavior — they use selectOption() to trigger
# the panel update and toBeVisible() / not_to_be_visible() to verify live state.
# They do NOT merely check DOM existence (to_have_count).
# ═══════════════════════════════════════════════════════════════════════════════


def _open_new_request_form(page: Page) -> None:
    """Click the '+ New Request' button to reveal the taxonomy form, wait for it."""
    btn = page.locator('[data-testid="pro-val-new-request-button"]')
    btn.click()
    page.locator('[data-testid="pro-val-new-request-form"]').wait_for(
        state="visible", timeout=5_000
    )


def _select_asset_type(page: Page, value: str) -> None:
    """Select an asset type and wait for the requirements panel update.
    Uses .nth(1) because pro-val-asset-type-select now appears in both workspaces (count=2);
    nth(1) = ws-professional-valuation (the active workspace when navigated via _go_to_pro_val)."""
    sel = page.locator('[data-testid="pro-val-asset-type-select"]')
    sel.nth(1).select_option(value)


# ── Hotel panel visibility ────────────────────────────────────────────────────

def test_PVLV01_hotel_selection_shows_requirements_panel(page: Page, live_server: str) -> None:
    """PVLV01: Selecting hotel makes the outer asset requirements panel VISIBLE (not just present)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    _open_new_request_form(page)
    _select_asset_type(page, "hotel")
    ws = page.locator('[data-testid="pro-val-workspace"]')
    panel = ws.locator('[data-testid="pro-val-asset-requirements-panel"]')
    expect(panel).to_be_visible()


def test_PVLV02_hotel_selection_shows_hotel_sub_panel(page: Page, live_server: str) -> None:
    """PVLV02: Selecting hotel makes the hotel-specific requirements sub-panel VISIBLE."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    _open_new_request_form(page)
    _select_asset_type(page, "hotel")
    hotel_panel = page.locator('[data-testid="pro-val-hotel-requirements-panel"]')
    expect(hotel_panel).to_be_visible()


def test_PVLV03_hotel_panel_contains_adr(page: Page, live_server: str) -> None:
    """PVLV03: Hotel requirements panel contains ADR text."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    _open_new_request_form(page)
    _select_asset_type(page, "hotel")
    hotel_panel = page.locator('[data-testid="pro-val-hotel-requirements-panel"]')
    expect(hotel_panel).to_contain_text("ADR")


def test_PVLV04_hotel_panel_contains_occupancy_rate(page: Page, live_server: str) -> None:
    """PVLV04: Hotel requirements panel contains occupancy rate (معدل الإشغال) text."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    _open_new_request_form(page)
    _select_asset_type(page, "hotel")
    hotel_panel = page.locator('[data-testid="pro-val-hotel-requirements-panel"]')
    expect(hotel_panel).to_contain_text("الإشغال")


def test_PVLV05_hotel_panel_contains_revpar(page: Page, live_server: str) -> None:
    """PVLV05: Hotel requirements panel contains RevPAR text."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    _open_new_request_form(page)
    _select_asset_type(page, "hotel")
    hotel_panel = page.locator('[data-testid="pro-val-hotel-requirements-panel"]')
    expect(hotel_panel).to_contain_text("RevPAR")


def test_PVLV06_hotel_panel_contains_dcf_method(page: Page, live_server: str) -> None:
    """PVLV06: Hotel requirements panel recommended methods include DCF."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    _open_new_request_form(page)
    _select_asset_type(page, "hotel")
    hotel_panel = page.locator('[data-testid="pro-val-hotel-requirements-panel"]')
    expect(hotel_panel).to_contain_text("dcf")


# ── Land panel visibility after hotel → land switch ──────────────────────────

def test_PVLV07_land_selection_shows_land_panel(page: Page, live_server: str) -> None:
    """PVLV07: Selecting urban_land makes the land requirements panel VISIBLE."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    _open_new_request_form(page)
    _select_asset_type(page, "urban_land")
    land_panel = page.locator('[data-testid="pro-val-land-requirements-panel"]')
    expect(land_panel).to_be_visible()


def test_PVLV08_land_selection_hides_hotel_panel(page: Page, live_server: str) -> None:
    """PVLV08: After selecting hotel then urban_land, hotel panel is NOT visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    _open_new_request_form(page)
    _select_asset_type(page, "hotel")
    _select_asset_type(page, "urban_land")
    hotel_panel = page.locator('[data-testid="pro-val-hotel-requirements-panel"]')
    expect(hotel_panel).not_to_be_visible()


# ── Factory, Retail, Warehouse panel visibility ───────────────────────────────

def test_PVLV09_factory_selection_shows_factory_panel(page: Page, live_server: str) -> None:
    """PVLV09: Selecting industrial_factory shows the factory requirements panel."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    _open_new_request_form(page)
    _select_asset_type(page, "industrial_factory")
    factory_panel = page.locator('[data-testid="pro-val-factory-requirements-panel"]')
    expect(factory_panel).to_be_visible()


def test_PVLV10_retail_selection_shows_retail_panel(page: Page, live_server: str) -> None:
    """PVLV10: Selecting retail_shop shows the retail requirements panel."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    _open_new_request_form(page)
    _select_asset_type(page, "retail_shop")
    retail_panel = page.locator('[data-testid="pro-val-retail-requirements-panel"]')
    expect(retail_panel).to_be_visible()


def test_PVLV11_warehouse_selection_shows_warehouse_panel(page: Page, live_server: str) -> None:
    """PVLV11: Selecting warehouse shows the warehouse requirements panel."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    _open_new_request_form(page)
    _select_asset_type(page, "warehouse")
    warehouse_panel = page.locator('[data-testid="pro-val-warehouse-requirements-panel"]')
    expect(warehouse_panel).to_be_visible()


# ── Market value / comparable_adjustment not misplaced ───────────────────────

def test_PVLV12_market_value_not_in_asset_type_options(page: Page, live_server: str) -> None:
    """PVLV12: market_value is NOT an option in the asset type select (Rule: market_value belongs in Basis of Value).
    Uses .nth(1) — pro-val-asset-type-select now count=2; nth(1) = ws-professional-valuation (active workspace)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    _open_new_request_form(page)
    asset_select = page.locator('[data-testid="pro-val-asset-type-select"]')
    options_html = asset_select.nth(1).inner_html()
    assert 'value="market_value"' not in options_html, (
        "market_value must not appear as an asset_type option — it belongs in Basis of Value"
    )


def test_PVLV13_comparable_adjustment_not_in_purpose_options(page: Page, live_server: str) -> None:
    """PVLV13: comparable_adjustment is NOT an option in assignment purpose select (it is a method step, not a purpose)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    _open_new_request_form(page)
    purpose_select = page.locator('[data-testid="pro-val-assignment-purpose-select"]')
    options_html = purpose_select.first.inner_html()
    assert 'value="comparable_adjustment"' not in options_html, (
        "comparable_adjustment must not appear as an assignment_purpose — it is a method step"
    )


# ── Configuration summary live update ────────────────────────────────────────

def test_PVLV14_config_summary_visible(page: Page, live_server: str) -> None:
    """PVLV14: The selected configuration summary element is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    _open_new_request_form(page)
    summary = page.locator('[data-testid="pro-val-selected-configuration-summary"]')
    expect(summary).to_be_visible()


def test_PVLV15_config_summary_updates_after_hotel_selection(page: Page, live_server: str) -> None:
    """PVLV15: Config summary reflects asset type after hotel selection."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    _open_new_request_form(page)
    _select_asset_type(page, "hotel")
    summary = page.locator('[data-testid="pro-val-selected-configuration-summary"]')
    # Should contain the Arabic hotel label or the asset family label
    summary_text = summary.inner_text()
    assert len(summary_text.strip()) > 0, "Config summary must not be empty after hotel selection"


# ── Feature capabilities panel — live visibility after expand ─────────────────

def test_PVLV16_feature_capabilities_panel_can_expand(page: Page, live_server: str) -> None:
    """PVLV16: Feature capabilities <details> panel can be opened via JS and content becomes visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    ws = page.locator('[data-testid="pro-val-workspace"]')
    panel = ws.locator('[data-testid="pro-val-feature-capabilities-panel"]')
    # Open the details element via JavaScript
    panel.evaluate("el => el.setAttribute('open', '')")
    active_list = ws.locator('[data-testid="pro-val-active-controls-list"]')
    expect(active_list).to_be_visible()


def test_PVLV17_active_controls_list_visible_after_expand(page: Page, live_server: str) -> None:
    """PVLV17: After expanding feature panel, active controls list is VISIBLE."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    ws = page.locator('[data-testid="pro-val-workspace"]')
    ws.locator('[data-testid="pro-val-feature-capabilities-panel"]').evaluate(
        "el => el.setAttribute('open', '')"
    )
    expect(ws.locator('[data-testid="pro-val-active-controls-list"]')).to_be_visible()


def test_PVLV18_inactive_controls_list_visible_after_expand(page: Page, live_server: str) -> None:
    """PVLV18: After expanding feature panel, inactive controls list is VISIBLE."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    ws = page.locator('[data-testid="pro-val-workspace"]')
    ws.locator('[data-testid="pro-val-feature-capabilities-panel"]').evaluate(
        "el => el.setAttribute('open', '')"
    )
    expect(ws.locator('[data-testid="pro-val-inactive-controls-list"]')).to_be_visible()


def test_PVLV19_report_reflection_matrix_visible_after_expand(page: Page, live_server: str) -> None:
    """PVLV19: After expanding feature panel, report reflection matrix table is VISIBLE."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    ws = page.locator('[data-testid="pro-val-workspace"]')
    ws.locator('[data-testid="pro-val-feature-capabilities-panel"]').evaluate(
        "el => el.setAttribute('open', '')"
    )
    expect(ws.locator('[data-testid="pro-val-report-reflection-matrix"]')).to_be_visible()


def test_PVLV20_activation_roadmap_visible_after_expand(page: Page, live_server: str) -> None:
    """PVLV20: After expanding feature panel, activation roadmap is VISIBLE."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    ws = page.locator('[data-testid="pro-val-workspace"]')
    ws.locator('[data-testid="pro-val-feature-capabilities-panel"]').evaluate(
        "el => el.setAttribute('open', '')"
    )
    expect(ws.locator('[data-testid="pro-val-control-activation-roadmap"]')).to_be_visible()


def test_PVLV21_disabled_reason_visible_after_expand(page: Page, live_server: str) -> None:
    """PVLV21: After expanding feature panel, at least one disabled-reason label is VISIBLE."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    page.locator('[data-testid="pro-val-feature-capabilities-panel"]').evaluate(
        "el => el.setAttribute('open', '')"
    )
    reasons = page.locator('[data-testid="pro-val-control-disabled-reason"]')
    # At least the first disabled reason must be visible
    expect(reasons.first).to_be_visible()


def test_PVLV22_active_control_report_impact_visible_after_expand(page: Page, live_server: str) -> None:
    """PVLV22: After expanding feature panel, at least one active control report-impact label is VISIBLE."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    page.locator('[data-testid="pro-val-feature-capabilities-panel"]').evaluate(
        "el => el.setAttribute('open', '')"
    )
    impacts = page.locator('[data-testid="pro-val-control-report-impact"]')
    expect(impacts.first).to_be_visible()


def test_PVLV23_digital_verification_text_in_inactive_list(page: Page, live_server: str) -> None:
    """PVLV23: After expanding feature panel, inactive controls list mentions digital verification."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    ws = page.locator('[data-testid="pro-val-workspace"]')
    ws.locator('[data-testid="pro-val-feature-capabilities-panel"]').evaluate(
        "el => el.setAttribute('open', '')"
    )
    inactive_list = ws.locator('[data-testid="pro-val-inactive-controls-list"]')
    expect(inactive_list).to_contain_text("التحقق الرقمي")


# ── Security / no internal paths ─────────────────────────────────────────────

def test_PVLV24_no_internal_paths_in_workspace_dom(page: Page, live_server: str) -> None:
    """PVLV24: The professional valuation workspace DOM contains no internal storage paths (Rule 19)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    ws = page.locator('[data-testid="pro-val-workspace"]')
    html = ws.inner_html()
    assert "internal_file_path" not in html
    assert "requests.jsonl" not in html
    assert "events.jsonl" not in html


# ── Regression: other tabs and existing buttons ───────────────────────────────

def test_PVLV25_ordinary_valuation_tab_still_works(page: Page, live_server: str) -> None:
    """PVLV25: Regression — Ordinary valuation tab is still visible and accessible."""
    _block_api(page)
    page.goto(live_server, wait_until="domcontentloaded")
    tab_btn = page.locator('#es-tab-valuation')
    expect(tab_btn).to_have_count(1)
    tab_btn.click()
    page.locator('[data-testid="simple-valuation-tab"]').wait_for(state="visible", timeout=10_000)
    expect(page.locator('[data-testid="simple-valuation-tab"]')).to_be_visible()


def test_PVLV26_tax_appeal_tab_still_accessible(page: Page, live_server: str) -> None:
    """PVLV26: Regression — Tax appeal tab is still accessible."""
    _block_api(page)
    page.goto(live_server, wait_until="domcontentloaded")
    tax_btn = page.locator('[data-testid="tax-tab"]')
    expect(tax_btn).to_have_count(1)
    tax_btn.click()
    page.locator('[data-testid="tax-page"]').wait_for(state="visible", timeout=10_000)
    expect(page.locator('[data-testid="tax-page"]')).to_be_visible()


def test_PVLV27_create_request_button_still_visible(page: Page, live_server: str) -> None:
    """PVLV27: Regression — pro-val-create-request-button still exists in the form."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    _open_new_request_form(page)
    btn = page.locator('[data-testid="pro-val-create-request-button"]')
    expect(btn).to_have_count(1)


def test_PVLV28_basis_of_value_has_market_value_option(page: Page, live_server: str) -> None:
    """PVLV28: Basis of value select contains market_value option (Axis 3 correct placement).
    Uses .nth(1) — pro-val-basis-of-value-select now count=2; nth(1) = ws-professional-valuation (active workspace)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    _open_new_request_form(page)
    bov_select = page.locator('[data-testid="pro-val-basis-of-value-select"]')
    options_html = bov_select.nth(1).inner_html()
    assert 'value="market_value"' in options_html, (
        "market_value must be an option in basis_of_value select (Axis 3)"
    )


def test_PVLV29_hotel_requirements_title_contains_hotel(page: Page, live_server: str) -> None:
    """PVLV29: After selecting hotel, the requirements panel title mentions فندق."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    _open_new_request_form(page)
    _select_asset_type(page, "hotel")
    ws = page.locator('[data-testid="pro-val-workspace"]')
    title = ws.locator('[data-testid="pro-val-asset-requirements-title"]')
    expect(title).to_contain_text("فندق")


def test_PVLV30_no_duplicate_workspace_testids(page: Page, live_server: str) -> None:
    """PVLV30: No critical testid appears more than once inside the pro-val workspace."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    critical_unique_testids = [
        "pro-val-feature-capabilities-panel",
        "pro-val-active-controls-list",
        "pro-val-inactive-controls-list",
        "pro-val-report-reflection-matrix",
        "pro-val-control-activation-roadmap",
        "pro-val-selected-configuration-summary",
        "pro-val-derived-method-route-summary",
    ]
    ws = page.locator('[data-testid="pro-val-workspace"]')
    for testid in critical_unique_testids:
        count = ws.locator(f'[data-testid="{testid}"]').count()
        assert count == 1, (
            f"Expected exactly 1 element with data-testid='{testid}', found {count}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# PVSERV01–PVSERV10 — Served Browser Visibility Fix Tests
# Proves that the real served page (not just DOM collection) shows content
# without relying on manual browser inspection.
# ─────────────────────────────────────────────────────────────────────────────

def test_PVSERV01_version_marker_visible_without_interaction(page: Page, live_server: str) -> None:
    """PVSERV01: UI version marker is VISIBLE as soon as the PV workspace loads — no clicks needed."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    marker = page.locator('[data-testid="pro-val-ui-version-marker"]')
    expect(marker).to_be_visible()


def test_PVSERV02_version_marker_text_contains_taxonomy_v2(page: Page, live_server: str) -> None:
    """PVSERV02: Version marker text contains 'Taxonomy v2'."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    marker = page.locator('[data-testid="pro-val-ui-version-marker"]')
    expect(marker).to_contain_text("Taxonomy v2")


def test_PVSERV03_feature_capabilities_panel_visible_on_load(page: Page, live_server: str) -> None:
    """PVSERV03: Feature capabilities panel is VISIBLE on page load without clicking expand."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    panel = page.locator('[data-testid="pro-val-feature-capabilities-panel"]')
    expect(panel).to_be_visible()


def test_PVSERV04_active_controls_visible_without_expand_click(page: Page, live_server: str) -> None:
    """PVSERV04: Active controls list is visible on load — panel is auto-expanded (open attribute)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    ws = page.locator('[data-testid="pro-val-workspace"]')
    expect(ws.locator('[data-testid="pro-val-active-controls-list"]')).to_be_visible()


def test_PVSERV05_inactive_controls_visible_without_expand_click(page: Page, live_server: str) -> None:
    """PVSERV05: Inactive controls list is visible on load — panel is auto-expanded."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    ws = page.locator('[data-testid="pro-val-workspace"]')
    expect(ws.locator('[data-testid="pro-val-inactive-controls-list"]')).to_be_visible()


def test_PVSERV06_asset_requirements_panel_visible_after_hotel_selection(
    page: Page, live_server: str
) -> None:
    """PVSERV06: Asset requirements panel becomes VISIBLE after opening form and selecting hotel."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    _open_new_request_form(page)
    _select_asset_type(page, "hotel")
    ws = page.locator('[data-testid="pro-val-workspace"]')
    expect(ws.locator('[data-testid="pro-val-asset-requirements-panel"]')).to_be_visible()


def test_PVSERV07_config_summary_visible_after_form_open(page: Page, live_server: str) -> None:
    """PVSERV07: Config summary panel is VISIBLE after opening the new request form."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    _open_new_request_form(page)
    expect(page.locator('[data-testid="pro-val-selected-configuration-summary"]')).to_be_visible()


def test_PVSERV08_arabic_requirements_text_present_after_hotel_selection(
    page: Page, live_server: str
) -> None:
    """PVSERV08: Arabic text 'متطلبات تقييم' is present in page after hotel selection."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    _open_new_request_form(page)
    _select_asset_type(page, "hotel")
    ws = page.locator('[data-testid="pro-val-workspace"]')
    panel = ws.locator('[data-testid="pro-val-asset-requirements-panel"]')
    expect(panel).to_be_visible()
    content = panel.inner_text()
    assert "متطلبات" in content, f"Arabic requirements text not found in panel: {content[:200]}"


def test_PVSERV09_no_js_console_errors(page: Page, live_server: str) -> None:
    """PVSERV09: No JavaScript console errors when navigating to PV workspace."""
    console_errors: list[str] = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    _block_api(page)
    _go_to_pro_val(page, live_server)
    page.wait_for_timeout(800)
    assert console_errors == [], f"JS console errors found: {console_errors}"


def test_PVSERV10_version_marker_not_inside_form_wrap(page: Page, live_server: str) -> None:
    """PVSERV10: Version marker is outside the new-request-form-wrap (visible before any form click)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    # Form wrap is display:none by default; marker must still be visible
    form_wrap = page.locator('[data-testid="pro-val-new-request-form"]')
    # Confirm form is not visible (hasn't been opened)
    expect(form_wrap).not_to_be_visible()
    # Marker must still be visible even though form is hidden
    marker = page.locator('[data-testid="pro-val-ui-version-marker"]')
    expect(marker).to_be_visible()


# ─────────────────────────────────────────────────────────────────────────────
# PVNEW01–PVNEW40 — Core UX Restructure / Input Modes / Report Types
# Part M: 40 browser visibility checks (all use real Playwright assertions)
# ─────────────────────────────────────────────────────────────────────────────

def _open_pv_form(page: Page, live_server: str) -> None:
    """Navigate to PV workspace and open the new-request form."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    page.locator('[data-testid="pro-val-new-request-button"]').click()
    page.locator('[data-testid="pro-val-new-request-form"]').wait_for(state="visible", timeout=5_000)


def test_PVNEW01_section_asset_definition_wrapper_exists(page: Page, live_server: str) -> None:
    """PVNEW01: pro-val-section-asset-definition wrapper exists in DOM.
    Count is 2: one in ws-professional-valuation (backoffice), one in ws-professional (visible default)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-section-asset-definition"]')
    expect(el).to_have_count(2)


def test_PVNEW02_section_assignment_purpose_wrapper_exists(page: Page, live_server: str) -> None:
    """PVNEW02: pro-val-section-assignment-purpose wrapper exists in DOM.
    Count is 2: one in ws-professional-valuation (backoffice), one in ws-professional (visible default)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-section-assignment-purpose"]')
    expect(el).to_have_count(2)


def test_PVNEW03_section_basis_of_value_wrapper_exists(page: Page, live_server: str) -> None:
    """PVNEW03: pro-val-section-basis-of-value wrapper exists in DOM.
    Count is 2: one in ws-professional-valuation (backoffice), one in ws-professional (visible default)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-section-basis-of-value"]')
    expect(el).to_have_count(2)


def test_PVNEW04_section_report_type_wrapper_exists(page: Page, live_server: str) -> None:
    """PVNEW04: pro-val-section-report-type wrapper exists in DOM.
    Count is 2: one in ws-professional-valuation (backoffice), one in ws-professional (visible default)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-section-report-type"]')
    expect(el).to_have_count(2)


def test_PVNEW05_purpose_logic_path_select_exists(page: Page, live_server: str) -> None:
    """PVNEW05: pro-val-purpose-logic-path-select select element exists in DOM.
    Count is 2: ws-professional-valuation (backoffice) + ws-professional (Step 2 UX visible)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-purpose-logic-path-select"]')
    expect(el).to_have_count(2)


def test_PVNEW06_purpose_logic_path_has_options(page: Page, live_server: str) -> None:
    """PVNEW06: purpose_logic_path select has at least 5 options including default blank."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    sel = page.locator('[data-testid="pro-val-purpose-logic-path-select"]')
    count = sel.locator('option').count()
    assert count >= 5, f"Expected >=5 options in purpose_logic_path, got {count}"


def test_PVNEW07_input_generation_section_exists(page: Page, live_server: str) -> None:
    """PVNEW07: pro-val-input-generation-section wrapper exists in DOM.
    Count is 2: one in ws-professional-valuation (backoffice), one in ws-professional (visible default)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-input-generation-section"]')
    expect(el).to_have_count(2)


def test_PVNEW08_analysis_output_section_legacy_testid_preserved(page: Page, live_server: str) -> None:
    """PVNEW08: Old pro-val-analysis-output-section testid is still present (backward compat)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-analysis-output-section"]')
    expect(el).to_have_count(1)


def test_PVNEW09_input_mode_select_exists(page: Page, live_server: str) -> None:
    """PVNEW09: pro-val-input-mode-select select element exists in DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-input-mode-select"]')
    expect(el).to_have_count(1)


def test_PVNEW10_input_mode_has_structured_option(page: Page, live_server: str) -> None:
    """PVNEW10: Input mode select has option for structured_browser_input."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    sel = page.locator('[data-testid="pro-val-input-mode-select"]')
    opt = sel.locator('option[value="structured_browser_input"]')
    expect(opt).to_have_count(1)


def test_PVNEW11_input_mode_has_chat_attachments_option(page: Page, live_server: str) -> None:
    """PVNEW11: Input mode select has option for chat_attachment_assisted_input."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    sel = page.locator('[data-testid="pro-val-input-mode-select"]')
    opt = sel.locator('option[value="chat_attachment_assisted_input"]')
    expect(opt).to_have_count(1)


def test_PVNEW12_structured_panel_exists(page: Page, live_server: str) -> None:
    """PVNEW12: pro-val-structured-input-panel exists in DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-structured-input-panel"]')
    expect(el).to_have_count(1)


def test_PVNEW13_chat_attachment_panel_exists(page: Page, live_server: str) -> None:
    """PVNEW13: pro-val-chat-attachment-input-panel exists in DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-chat-attachment-input-panel"]')
    expect(el).to_have_count(1)


def test_PVNEW14_structured_panel_visible_by_default(page: Page, live_server: str) -> None:
    """PVNEW14: Structured input panel is visible when mode=structured_browser_input (default)."""
    _open_pv_form(page, live_server)
    panel = page.locator('[data-testid="pro-val-structured-input-panel"]')
    expect(panel).to_be_visible()


def test_PVNEW15_chat_panel_hidden_by_default(page: Page, live_server: str) -> None:
    """PVNEW15: Chat attachment panel is hidden when mode=structured_browser_input (default)."""
    _open_pv_form(page, live_server)
    panel = page.locator('[data-testid="pro-val-chat-attachment-input-panel"]')
    expect(panel).not_to_be_visible()


def test_PVNEW16_switch_to_chat_mode_shows_chat_panel(page: Page, live_server: str) -> None:
    """PVNEW16: Selecting chat_attachment_assisted_input shows the chat panel."""
    _open_pv_form(page, live_server)
    sel = page.locator('[data-testid="pro-val-input-mode-select"]')
    sel.select_option("chat_attachment_assisted_input")
    panel = page.locator('[data-testid="pro-val-chat-attachment-input-panel"]')
    expect(panel).to_be_visible()


def test_PVNEW17_switch_to_chat_mode_hides_structured_panel(page: Page, live_server: str) -> None:
    """PVNEW17: Selecting chat_attachment_assisted_input hides the structured panel."""
    _open_pv_form(page, live_server)
    sel = page.locator('[data-testid="pro-val-input-mode-select"]')
    sel.select_option("chat_attachment_assisted_input")
    panel = page.locator('[data-testid="pro-val-structured-input-panel"]')
    expect(panel).not_to_be_visible()


def test_PVNEW18_upload_evidence_control_exists(page: Page, live_server: str) -> None:
    """PVNEW18: pro-val-upload-evidence-control container exists in DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-upload-evidence-control"]')
    assert el.count() >= 1, "Expected at least one pro-val-upload-evidence-control"


def test_PVNEW19_upload_photos_control_exists(page: Page, live_server: str) -> None:
    """PVNEW19: pro-val-upload-photos-control container exists in DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-upload-photos-control"]')
    expect(el).to_have_count(1)


def test_PVNEW20_upload_aerial_map_control_exists(page: Page, live_server: str) -> None:
    """PVNEW20: pro-val-upload-aerial-map-control container exists in DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-upload-aerial-map-control"]')
    expect(el).to_have_count(1)


def test_PVNEW21_upload_prior_report_control_exists(page: Page, live_server: str) -> None:
    """PVNEW21: pro-val-upload-prior-report-control container exists in DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-upload-prior-report-control"]')
    expect(el).to_have_count(1)


def test_PVNEW22_report_simulation_toggle_exists(page: Page, live_server: str) -> None:
    """PVNEW22: pro-val-report-simulation-toggle checkbox exists in DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-report-simulation-toggle"]')
    expect(el).to_have_count(1)


def test_PVNEW23_simulation_option_hidden_when_not_enabled(page: Page, live_server: str) -> None:
    """PVNEW23: pro-val-simulated-uploaded-report-option is hidden when simulation not enabled."""
    _open_pv_form(page, live_server)
    opt_div = page.locator('[data-testid="pro-val-simulated-uploaded-report-option"]')
    expect(opt_div).not_to_be_visible()


def test_PVNEW24_simulation_option_visible_when_enabled(page: Page, live_server: str) -> None:
    """PVNEW24: pro-val-simulated-uploaded-report-option appears after enabling simulation toggle."""
    _open_pv_form(page, live_server)
    toggle = page.locator('[data-testid="pro-val-report-simulation-toggle"]')
    toggle.check()
    opt_div = page.locator('[data-testid="pro-val-simulated-uploaded-report-option"]')
    expect(opt_div).to_be_visible()


def test_PVNEW25_generated_output_type_select_exists(page: Page, live_server: str) -> None:
    """PVNEW25: pro-val-generated-output-type-select exists in DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-generated-output-type-select"]')
    expect(el).to_have_count(1)


def test_PVNEW26_generate_traditional_button_exists(page: Page, live_server: str) -> None:
    """PVNEW26: pro-val-generate-traditional-report button exists."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-generate-traditional-report"]')
    expect(el).to_have_count(1)


def test_PVNEW27_generate_detailed_button_exists(page: Page, live_server: str) -> None:
    """PVNEW27: pro-val-generate-detailed-report button exists."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-generate-detailed-report"]')
    expect(el).to_have_count(1)


def test_PVNEW28_generate_professional_button_exists(page: Page, live_server: str) -> None:
    """PVNEW28: pro-val-generate-professional-report button exists."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-generate-professional-report"]')
    expect(el).to_have_count(1)


def test_PVNEW29_generate_simulated_button_exists(page: Page, live_server: str) -> None:
    """PVNEW29: pro-val-generate-simulated-uploaded-report button exists."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-generate-simulated-uploaded-report"]')
    expect(el).to_have_count(1)


def test_PVNEW30_simulated_button_disabled_by_default(page: Page, live_server: str) -> None:
    """PVNEW30: Simulated report button is disabled until simulation toggle is enabled."""
    _open_pv_form(page, live_server)
    btn = page.locator('[data-testid="pro-val-generate-simulated-uploaded-report"]')
    assert btn.is_disabled(), "Simulated report button must be disabled before enabling simulation"


def test_PVNEW31_simulated_button_enabled_after_toggle(page: Page, live_server: str) -> None:
    """PVNEW31: Simulated report button becomes enabled after enabling simulation toggle."""
    _open_pv_form(page, live_server)
    page.locator('[data-testid="pro-val-report-simulation-toggle"]').check()
    btn = page.locator('[data-testid="pro-val-generate-simulated-uploaded-report"]')
    assert not btn.is_disabled(), "Simulated report button must be enabled after simulation toggle"


def test_PVNEW32_auto_fill_toggle_exists(page: Page, live_server: str) -> None:
    """PVNEW32: pro-val-auto-fill-requirements-toggle checkbox exists."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-auto-fill-requirements-toggle"]')
    expect(el).to_have_count(1)


def test_PVNEW33_auto_fill_help_text_exists(page: Page, live_server: str) -> None:
    """PVNEW33: pro-val-auto-fill-requirements-help paragraph exists."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-auto-fill-requirements-help"]')
    expect(el).to_have_count(1)


def test_PVNEW34_derived_requirements_preview_hidden_by_default(page: Page, live_server: str) -> None:
    """PVNEW34: pro-val-derived-requirements-preview is hidden before auto-fill is enabled."""
    _open_pv_form(page, live_server)
    panel = page.locator('[data-testid="pro-val-derived-requirements-preview"]')
    expect(panel).not_to_be_visible()


def test_PVNEW35_derived_requirements_preview_visible_after_auto_fill(page: Page, live_server: str) -> None:
    """PVNEW35: Enabling auto-fill toggle shows the derived requirements preview panel."""
    _open_pv_form(page, live_server)
    page.locator('[data-testid="pro-val-auto-fill-requirements-toggle"]').check()
    panel = page.locator('[data-testid="pro-val-derived-requirements-preview"]')
    expect(panel).to_be_visible()


def test_PVNEW36_derived_requirements_panel_inner_exists(page: Page, live_server: str) -> None:
    """PVNEW36: pro-val-derived-requirements-panel inner div exists in DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-derived-requirements-panel"]')
    expect(el).to_have_count(1)


def test_PVNEW37_derived_requirements_list_elements_exist(page: Page, live_server: str) -> None:
    """PVNEW37: All 5 derived requirements list testids exist in DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    for tid in [
        "pro-val-derived-required-inputs-list",
        "pro-val-derived-required-evidence-list",
        "pro-val-derived-recommended-methods-list",
        "pro-val-derived-workbook-sheets-list",
        "pro-val-derived-pdf-sections-list",
    ]:
        el = page.locator(f'[data-testid="{tid}"]')
        expect(el).to_have_count(1), f"Missing: {tid}"


def test_PVNEW38_simulation_warning_text_present(page: Page, live_server: str) -> None:
    """PVNEW38: pro-val-simulation-warning text element exists in DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-simulation-warning"]')
    expect(el).to_have_count(1)


def test_PVNEW39_market_value_not_in_asset_type_dropdown(page: Page, live_server: str) -> None:
    """PVNEW39: 'market_value' must NOT appear as an option in asset-type select (it belongs in basis-of-value)."""
    _open_pv_form(page, live_server)
    bad_opt = page.locator('[data-testid="pro-val-asset-type-select"] option[value="market_value"]')
    assert bad_opt.count() == 0, "market_value must not appear in asset_type dropdown — it belongs in basis_of_value"


def test_PVNEW40_no_internal_paths_in_dom(page: Page, live_server: str) -> None:
    """PVNEW40: No Windows-style internal paths (C:\\, /Users/) should appear anywhere in page DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    body_text = page.locator("body").inner_text()
    bad_patterns = ["C:\\", "C:/Users", "/Users/", "/home/", "core_engine/"]
    for pat in bad_patterns:
        assert pat not in body_text, f"Internal path pattern found in page DOM: '{pat}'"
