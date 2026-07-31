"""
PVCC E2E Browser Tests — Professional Valuation Chat Command Center
Tests PVCC-E01 through PVCC-E41
Runs Playwright against the live server.
live_server fixture provided by core_engine/tests/e2e/conftest.py
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


def _goto(page: Page, live_server: str) -> None:
    page.route("**/api/**", lambda r: r.fulfill(
        status=200, body=b'{"ok":true,"request_id":"pvcc-test-001"}',
        content_type="application/json",
    ))
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator('[data-testid="professional-wizard"]').wait_for(
        state="visible", timeout=15_000
    )


def _ws(page: Page):
    return page.locator("#ws-professional")


# PVCC-E01: Real Chat Box is visible
def test_PVCC_E01_real_chat_box_visible(page: Page, live_server: str):
    _goto(page, live_server)
    expect(_ws(page).locator('[data-testid="pro-val-chat-command-center"]').first).to_be_visible()


# PVCC-E02: Only one visible chat command center
def test_PVCC_E02_only_one_chat_command_center(page: Page, live_server: str):
    _goto(page, live_server)
    count = _ws(page).locator('[data-testid="pro-val-chat-command-center"]').count()
    assert count == 1, f"Expected 1 chat command center, found {count}"


# PVCC-E03: Duplicate upper chat/output box not visible
def test_PVCC_E03_duplicate_upper_chat_not_visible(page: Page, live_server: str):
    _goto(page, live_server)
    expect(_ws(page).locator('[data-testid="professional-step-output"]')).not_to_be_visible()


# PVCC-E04: Corrupted text not visible
def test_PVCC_E04_chot_box_not_visible(page: Page, live_server: str):
    _goto(page, live_server)
    body_text = page.evaluate("document.body.innerText")
    assert "Chot Box" not in body_text
    assert "Chot Ber" not in body_text


# PVCC-E05: Corrupted text "Rapert" not visible
def test_PVCC_E05_rapert_not_visible(page: Page, live_server: str):
    _goto(page, live_server)
    body_text = page.evaluate("document.body.innerText")
    assert "Rapert" not in body_text
    assert "Dutgut" not in body_text
    assert "Augort" not in body_text


# PVCC-E06: Chat input is visible
def test_PVCC_E06_chat_input_visible(page: Page, live_server: str):
    _goto(page, live_server)
    expect(_ws(page).locator('[data-testid="pro-val-chat-input"]')).to_be_visible()


# PVCC-E07: Property Docs clip is visible
def test_PVCC_E07_property_docs_clip_visible(page: Page, live_server: str):
    _goto(page, live_server)
    expect(_ws(page).locator('[data-testid="pro-val-property-docs-clip"]').first).to_be_visible()


# PVCC-E08: Simulation Report clip is visible (renamed from training)
def test_PVCC_E08_simulation_report_clip_visible(page: Page, live_server: str):
    _goto(page, live_server)
    expect(_ws(page).locator('[data-testid="pro-val-simulation-report-clip"]').first).to_be_visible()


# PVCC-E09: Unified report/action dropdown is visible
def test_PVCC_E09_report_action_dropdown_visible(page: Page, live_server: str):
    _goto(page, live_server)
    expect(_ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]').first).to_be_visible()


# PVCC-E10: Dropdown contains "تقرير تقليدي"
def test_PVCC_E10_dropdown_contains_traditional(page: Page, live_server: str):
    _goto(page, live_server)
    sel = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]').first
    expect(sel).to_be_visible()
    text = sel.inner_text()
    assert "تقرير تقليدي" in text


# PVCC-E11: Dropdown contains "تقرير تفصيلي"
def test_PVCC_E11_dropdown_contains_detailed(page: Page, live_server: str):
    _goto(page, live_server)
    sel = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]').first
    text = sel.inner_text()
    assert "تقرير تفصيلي" in text


# PVCC-E12: Dropdown contains "تقرير احترافي"
def test_PVCC_E12_dropdown_contains_professional(page: Page, live_server: str):
    _goto(page, live_server)
    sel = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]').first
    text = sel.inner_text()
    assert "تقرير احترافي" in text


# PVCC-E13: Dropdown contains "محاكاة تقرير مرفوع"
def test_PVCC_E13_dropdown_contains_simulated(page: Page, live_server: str):
    _goto(page, live_server)
    sel = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]').first
    text = sel.inner_text()
    assert "محاكاة" in text


# PVCC-E14: Dropdown contains "مراجعة تقرير"
def test_PVCC_E14_dropdown_contains_review(page: Page, live_server: str):
    _goto(page, live_server)
    sel = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]').first
    text = sel.inner_text()
    assert "مراجعة" in text


# PVCC-E15: Dropdown contains "أعلى وأفضل"
def test_PVCC_E15_dropdown_contains_hbu(page: Page, live_server: str):
    _goto(page, live_server)
    sel = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]').first
    text = sel.inner_text()
    assert "أعلى وأفضل" in text


# PVCC-E16: Dropdown contains "امتثال المعايير"
def test_PVCC_E16_dropdown_contains_standards(page: Page, live_server: str):
    _goto(page, live_server)
    sel = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]').first
    text = sel.inner_text()
    assert "امتثال" in text


# PVCC-E17: Super Intelligence toggle visible
def test_PVCC_E17_super_intelligence_toggle_visible(page: Page, live_server: str):
    _goto(page, live_server)
    expect(_ws(page).locator('[data-testid="pro-val-feature-super-intelligence-toggle"]').first).to_be_visible()


# PVCC-E18: Digital Inspector toggle visible
def test_PVCC_E18_digital_inspector_toggle_visible(page: Page, live_server: str):
    _goto(page, live_server)
    expect(_ws(page).locator('[data-testid="pro-val-feature-digital-inspector-toggle"]').first).to_be_visible()


# PVCC-E19: Geotechnical Risk toggle visible
def test_PVCC_E19_geotechnical_risk_toggle_visible(page: Page, live_server: str):
    _goto(page, live_server)
    expect(_ws(page).locator('[data-testid="pro-val-feature-geotechnical-risk-toggle"]').first).to_be_visible()


# PVCC-E20: Migration Radar toggle visible
def test_PVCC_E20_migration_radar_toggle_visible(page: Page, live_server: str):
    _goto(page, live_server)
    expect(_ws(page).locator('[data-testid="pro-val-feature-migration-radar-toggle"]').first).to_be_visible()


# PVCC-E21: Asset Portfolio toggle visible
def test_PVCC_E21_asset_portfolio_toggle_visible(page: Page, live_server: str):
    _goto(page, live_server)
    expect(_ws(page).locator('[data-testid="pro-val-feature-asset-portfolio-toggle"]').first).to_be_visible()


# PVCC-E22: Reference Library toggle visible
def test_PVCC_E22_reference_library_toggle_visible(page: Page, live_server: str):
    _goto(page, live_server)
    expect(_ws(page).locator('[data-testid="pro-val-feature-reference-library-toggle"]').first).to_be_visible()


# PVCC-E23: Feature state labels visible (advisory/future badge)
def test_PVCC_E23_feature_state_labels_visible(page: Page, live_server: str):
    _goto(page, live_server)
    advisory_count = _ws(page).locator("text=استرشادي").count()
    future_count   = _ws(page).locator("text=قادم").count()
    assert (advisory_count + future_count) > 0, "No feature state labels found"


# PVCC-E24: Future/advisory warning visible for inactive features
def test_PVCC_E24_future_stub_badge_visible(page: Page, live_server: str):
    _goto(page, live_server)
    assert _ws(page).locator("text=قادم").count() >= 1


# PVCC-E25: User PDF button visible (canonical testid)
def test_PVCC_E25_user_pdf_button_visible(page: Page, live_server: str):
    _goto(page, live_server)
    expect(_ws(page).locator('[data-testid="pro-val-unified-generate-user-pdf"]').first).to_be_visible()


# PVCC-E26: Admin Excel hidden/disabled for non-admin
def test_PVCC_E26_admin_excel_hidden_for_non_admin(page: Page, live_server: str):
    _goto(page, live_server)
    expect(_ws(page).locator('[data-testid="pro-val-unified-generate-admin-excel"]')).not_to_be_visible()


# PVCC-E27: Selecting simulated report shows guidance
def test_PVCC_E27_simulated_requires_simulation_upload(page: Page, live_server: str):
    _goto(page, live_server)
    sel = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]').first
    sel.select_option("simulated_uploaded_report")
    page.wait_for_timeout(300)
    guidance = _ws(page).locator('[data-testid="pro-val-chat-action-guidance"]').first
    guidance_text = guidance.inner_text()
    assert guidance_text != ""


# PVCC-E28: Selecting HBU report shows HBU guidance
def test_PVCC_E28_hbu_selection_shows_guidance(page: Page, live_server: str):
    _goto(page, live_server)
    sel = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]').first
    sel.select_option("hbu_analysis_report")
    page.wait_for_timeout(300)
    guidance = _ws(page).locator('[data-testid="pro-val-chat-action-guidance"]').first
    guidance_text = guidance.inner_text()
    assert guidance_text != ""


# PVCC-E29: Selecting standards compliance shows standards requirement
def test_PVCC_E29_standards_selection_shows_guidance(page: Page, live_server: str):
    _goto(page, live_server)
    sel = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]').first
    sel.select_option("standards_compliance_report")
    page.wait_for_timeout(300)
    guidance = _ws(page).locator('[data-testid="pro-val-chat-action-guidance"]').first
    guidance_text = guidance.inner_text()
    assert guidance_text != ""


# PVCC-E30: Old "طريقة الإدخال" block not visible
def test_PVCC_E30_old_input_method_not_visible(page: Page, live_server: str):
    _goto(page, live_server)
    expect(_ws(page).locator('[data-testid="pro-val-vis-input-mode-select"]')).not_to_be_visible()


# PVCC-E31: Old separate report buttons not visible
def test_PVCC_E31_old_report_buttons_not_visible(page: Page, live_server: str):
    _goto(page, live_server)
    expect(_ws(page).locator('[data-testid="pro-val-vis-generate-traditional"]')).not_to_be_visible()
    expect(_ws(page).locator('[data-testid="pro-val-vis-generate-detailed"]')).not_to_be_visible()
    expect(_ws(page).locator('[data-testid="pro-val-vis-generate-professional"]')).not_to_be_visible()


# PVCC-E32: Output contract summary not visible
def test_PVCC_E32_output_contract_summary_not_visible(page: Page, live_server: str):
    _goto(page, live_server)
    expect(_ws(page).locator('[data-testid="professional-output-contract-summary"]')).not_to_be_visible()


# PVCC-E33: market_value debug token not visible
def test_PVCC_E33_market_value_not_visible(page: Page, live_server: str):
    _goto(page, live_server)
    body_text = page.evaluate("document.body.innerText")
    assert "market_value · habu_value" not in body_text


# PVCC-E34: habu_value debug token not visible
def test_PVCC_E34_habu_value_not_visible(page: Page, live_server: str):
    _goto(page, live_server)
    body_text = page.evaluate("document.body.innerText")
    assert "habu_value · confidence_score" not in body_text


# PVCC-E35: confidence_score debug token not visible
def test_PVCC_E35_confidence_score_not_visible(page: Page, live_server: str):
    _goto(page, live_server)
    body_text = page.evaluate("document.body.innerText")
    assert "confidence_score · comparable_count_used" not in body_text


# PVCC-E36: comparable_count_used not visible
def test_PVCC_E36_comparable_count_not_visible(page: Page, live_server: str):
    _goto(page, live_server)
    body_text = page.evaluate("document.body.innerText")
    assert "comparable_count_used · adjustment_summary" not in body_text


# PVCC-E37: adjustment_summary not visible
def test_PVCC_E37_adjustment_summary_not_visible(page: Page, live_server: str):
    _goto(page, live_server)
    body_text = page.evaluate("document.body.innerText")
    assert "adjustment_summary · ifrs_level" not in body_text


# PVCC-E38: ifrs_level debug token not visible
def test_PVCC_E38_ifrs_level_not_visible(page: Page, live_server: str):
    _goto(page, live_server)
    body_text = page.evaluate("document.body.innerText")
    assert "· ifrs_level" not in body_text


# PVCC-E39: Governance panel not visible
def test_PVCC_E39_governance_panel_not_visible(page: Page, live_server: str):
    _goto(page, live_server)
    expect(_ws(page).locator('[data-testid="professional-governance-panel"]')).not_to_be_visible()


# PVCC-E40: No internal paths in DOM
def test_PVCC_E40_no_internal_paths_in_dom(page: Page, live_server: str):
    _goto(page, live_server)
    body_html = page.evaluate("document.body.innerHTML")
    bad = ["C:\\Users\\", "/home/", "core_engine/instance/", "__pycache__"]
    for b in bad:
        assert b not in body_html, f"Internal path found in DOM: {b!r}"


# PVCC-E41: No duplicate chat-input testids (only one visible)
def test_PVCC_E41_no_duplicate_chat_input_testids(page: Page, live_server: str):
    _goto(page, live_server)
    all_inputs = _ws(page).locator('[data-testid="pro-val-chat-input"]')
    count = all_inputs.count()
    assert count == 1, f"Expected 1 chat-input, found {count}"
