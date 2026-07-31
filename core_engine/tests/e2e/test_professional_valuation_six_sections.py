"""
PVSS01–PVSS26 — ws-professional Six-Section Layout E2E Tests (Part H).

ws-professional is the VISIBLE default workspace at root URL (http://127.0.0.1:5000/).
These tests verify the restructured 6-section layout and the Advanced Controls panel.

Sections in ws-professional:
  1. pro-val-section-basic-valuation-data
  2. pro-val-section-asset-type-selection
  3. pro-val-section-valuation-purpose  (merged purpose + basis-of-value)
  4. pro-val-section-applied-valuation-standards  (NEW)
  5. pro-val-section-report-type
  6. pro-val-section-chat-box

Advanced Controls Panel:
  pro-val-advanced-controls-panel
    pro-val-active-controls-list
    pro-val-inactive-controls-list
    pro-val-control-activation-roadmap
    pro-val-report-reflection-matrix

Compat spans (DOM-present but hidden):
  pro-val-section-asset-definition       — inside Section 1  (count>=1)
  pro-val-section-assignment-purpose     — inside Section 3  (count>=1)
  pro-val-section-basis-of-value         — inside Section 3  (count>=1)
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def _go_to_visible_pv(page: Page, live_server: str) -> None:
    """Navigate to root URL where ws-professional is the visible default workspace."""
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator("#ws-professional").wait_for(state="visible", timeout=10_000)
    page.locator('[data-testid="professional-wizard"]').wait_for(state="attached", timeout=10_000)


def _block_api(page: Page) -> None:
    """Block all API calls so tests are purely frontend."""
    page.route("**/api/**", lambda r: r.fulfill(
        status=200, body=b'{"ok":true}', content_type="application/json"
    ))


# ─────────────────────────────────────────────────────────────────────────────
# PVSS01–PVSS07: Workspace & Section presence
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.e2e
def test_PVSS01_ws_professional_is_active_visible_at_root(page: Page, live_server: str) -> None:
    """PVSS01: ws-professional is the active visible workspace at root URL."""
    _block_api(page)
    _go_to_visible_pv(page, live_server)
    ws = page.locator("#ws-professional")
    expect(ws).to_be_visible()


@pytest.mark.e2e
def test_PVSS02_section_1_basic_valuation_data_exists(page: Page, live_server: str) -> None:
    """PVSS02: Section 1 (pro-val-section-basic-valuation-data) exists with count==1 in ws-professional."""
    _block_api(page)
    _go_to_visible_pv(page, live_server)
    el = page.locator("#ws-professional [data-testid='pro-val-section-basic-valuation-data']")
    expect(el).to_have_count(1)


@pytest.mark.e2e
def test_PVSS03_section_2_asset_type_selection_exists(page: Page, live_server: str) -> None:
    """PVSS03: Section 2 (pro-val-section-asset-type-selection) exists with count==1 in ws-professional."""
    _block_api(page)
    _go_to_visible_pv(page, live_server)
    el = page.locator("#ws-professional [data-testid='pro-val-section-asset-type-selection']")
    expect(el).to_have_count(1)


@pytest.mark.e2e
def test_PVSS04_section_3_valuation_purpose_exists(page: Page, live_server: str) -> None:
    """PVSS04: Section 3 (pro-val-section-valuation-purpose) exists with count==1 in ws-professional."""
    _block_api(page)
    _go_to_visible_pv(page, live_server)
    el = page.locator("#ws-professional [data-testid='pro-val-section-valuation-purpose']")
    expect(el).to_have_count(1)


@pytest.mark.e2e
def test_PVSS05_section_4_applied_valuation_standards_exists(page: Page, live_server: str) -> None:
    """PVSS05: Section 4 (pro-val-section-applied-valuation-standards) exists with count==1 in ws-professional."""
    _block_api(page)
    _go_to_visible_pv(page, live_server)
    el = page.locator("#ws-professional [data-testid='pro-val-section-applied-valuation-standards']")
    expect(el).to_have_count(1)


@pytest.mark.e2e
def test_PVSS06_section_5_report_type_exists_in_ws_professional(page: Page, live_server: str) -> None:
    """PVSS06: Section 5 (pro-val-section-report-type) exists in ws-professional.
    This testid also appears in ws-professional-valuation; scope to ws-professional using .first."""
    _block_api(page)
    _go_to_visible_pv(page, live_server)
    el = page.locator("#ws-professional [data-testid='pro-val-section-report-type']")
    # Scoped to ws-professional — must have at least 1
    assert el.count() >= 1, "pro-val-section-report-type not found inside #ws-professional"


@pytest.mark.e2e
def test_PVSS07_section_6_chat_box_exists(page: Page, live_server: str) -> None:
    """PVSS07: Section 6 (pro-val-section-chat-box) exists with count==1 in ws-professional."""
    _block_api(page)
    _go_to_visible_pv(page, live_server)
    el = page.locator("#ws-professional [data-testid='pro-val-section-chat-box']")
    expect(el).to_have_count(1)


# ─────────────────────────────────────────────────────────────────────────────
# PVSS08–PVSS12: Advanced Controls Panel
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.e2e
def test_PVSS08_advanced_controls_panel_exists(page: Page, live_server: str) -> None:
    """PVSS08: pro-val-advanced-controls-panel exists with count==1."""
    _block_api(page)
    _go_to_visible_pv(page, live_server)
    el = page.locator("[data-testid='pro-val-advanced-controls-panel']")
    expect(el).to_have_count(1)


@pytest.mark.e2e
def test_PVSS09_active_controls_list_exists(page: Page, live_server: str) -> None:
    """PVSS09: pro-val-active-controls-list exists with count==1 inside ws-professional."""
    _block_api(page)
    _go_to_visible_pv(page, live_server)
    el = page.locator("#ws-professional [data-testid='pro-val-active-controls-list']")
    expect(el).to_have_count(1)


@pytest.mark.e2e
def test_PVSS10_inactive_controls_list_exists(page: Page, live_server: str) -> None:
    """PVSS10: pro-val-inactive-controls-list exists with count==1 inside ws-professional."""
    _block_api(page)
    _go_to_visible_pv(page, live_server)
    el = page.locator("#ws-professional [data-testid='pro-val-inactive-controls-list']")
    expect(el).to_have_count(1)


@pytest.mark.e2e
def test_PVSS11_control_activation_roadmap_exists(page: Page, live_server: str) -> None:
    """PVSS11: pro-val-control-activation-roadmap exists with count==1 inside ws-professional."""
    _block_api(page)
    _go_to_visible_pv(page, live_server)
    el = page.locator("#ws-professional [data-testid='pro-val-control-activation-roadmap']")
    expect(el).to_have_count(1)


@pytest.mark.e2e
def test_PVSS12_report_reflection_matrix_exists(page: Page, live_server: str) -> None:
    """PVSS12: pro-val-report-reflection-matrix exists with count==1 inside ws-professional."""
    _block_api(page)
    _go_to_visible_pv(page, live_server)
    el = page.locator("#ws-professional [data-testid='pro-val-report-reflection-matrix']")
    expect(el).to_have_count(1)


# ─────────────────────────────────────────────────────────────────────────────
# PVSS13–PVSS15: Compat spans (DOM-present, hidden)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.e2e
def test_PVSS13_compat_span_asset_definition_in_dom(page: Page, live_server: str) -> None:
    """PVSS13: Compat span pro-val-section-asset-definition is in DOM (count>=1, likely 2)."""
    _block_api(page)
    _go_to_visible_pv(page, live_server)
    el = page.locator("[data-testid='pro-val-section-asset-definition']")
    assert el.count() >= 1, (
        "Expected pro-val-section-asset-definition compat span to be present in DOM"
    )


@pytest.mark.e2e
def test_PVSS14_compat_span_assignment_purpose_in_dom(page: Page, live_server: str) -> None:
    """PVSS14: Compat span pro-val-section-assignment-purpose is in DOM (count>=1)."""
    _block_api(page)
    _go_to_visible_pv(page, live_server)
    el = page.locator("[data-testid='pro-val-section-assignment-purpose']")
    assert el.count() >= 1, (
        "Expected pro-val-section-assignment-purpose compat span to be present in DOM"
    )


@pytest.mark.e2e
def test_PVSS15_compat_span_basis_of_value_in_dom(page: Page, live_server: str) -> None:
    """PVSS15: Compat span pro-val-section-basis-of-value is in DOM (count>=1)."""
    _block_api(page)
    _go_to_visible_pv(page, live_server)
    el = page.locator("[data-testid='pro-val-section-basis-of-value']")
    assert el.count() >= 1, (
        "Expected pro-val-section-basis-of-value compat span to be present in DOM"
    )


# ─────────────────────────────────────────────────────────────────────────────
# PVSS16–PVSS20: Section 4 (Applied Valuation Standards) selects
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.e2e
def test_PVSS16_section_4_valuation_standard_basis_select_visible(page: Page, live_server: str) -> None:
    """PVSS16: Section 4 has pro-val-valuation-standard-basis-select visible (count==1 within ws-professional)."""
    _block_api(page)
    _go_to_visible_pv(page, live_server)
    el = page.locator("#ws-professional [data-testid='pro-val-valuation-standard-basis-select']")
    expect(el).to_have_count(1)


@pytest.mark.e2e
def test_PVSS17_section_4_ifrs_value_level_select_exists(page: Page, live_server: str) -> None:
    """PVSS17: Section 4 has pro-val-ifrs-value-level-select (count==1 within ws-professional)."""
    _block_api(page)
    _go_to_visible_pv(page, live_server)
    el = page.locator("#ws-professional [data-testid='pro-val-ifrs-value-level-select']")
    expect(el).to_have_count(1)


@pytest.mark.e2e
def test_PVSS18_section_4_ivs_standard_reference_select_exists(page: Page, live_server: str) -> None:
    """PVSS18: Section 4 has pro-val-ivs-standard-reference-select (count==1 within ws-professional)."""
    _block_api(page)
    _go_to_visible_pv(page, live_server)
    el = page.locator("#ws-professional [data-testid='pro-val-ivs-standard-reference-select']")
    expect(el).to_have_count(1)


@pytest.mark.e2e
def test_PVSS19_section_4_local_standard_reference_select_exists(page: Page, live_server: str) -> None:
    """PVSS19: Section 4 has pro-val-local-standard-reference-select (count==1 within ws-professional)."""
    _block_api(page)
    _go_to_visible_pv(page, live_server)
    el = page.locator("#ws-professional [data-testid='pro-val-local-standard-reference-select']")
    expect(el).to_have_count(1)


@pytest.mark.e2e
def test_PVSS20_section_4_compliance_disclosure_level_select_exists(page: Page, live_server: str) -> None:
    """PVSS20: Section 4 has pro-val-compliance-disclosure-level-select (count==1 within ws-professional)."""
    _block_api(page)
    _go_to_visible_pv(page, live_server)
    el = page.locator("#ws-professional [data-testid='pro-val-compliance-disclosure-level-select']")
    expect(el).to_have_count(1)


# ─────────────────────────────────────────────────────────────────────────────
# PVSS21–PVSS23: Section 6 Chat Box controls
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.e2e
def test_PVSS21_chat_input_textarea_in_dom(page: Page, live_server: str) -> None:
    """PVSS21: pro-val-chat-input (textarea) is in DOM within ws-professional."""
    _block_api(page)
    _go_to_visible_pv(page, live_server)
    el = page.locator("#ws-professional [data-testid='pro-val-chat-input']")
    assert el.count() >= 1, "pro-val-chat-input textarea not found inside #ws-professional"


@pytest.mark.e2e
def test_PVSS22_chat_send_button_in_dom(page: Page, live_server: str) -> None:
    """PVSS22: pro-val-chat-send-button is in DOM within ws-professional."""
    _block_api(page)
    _go_to_visible_pv(page, live_server)
    el = page.locator("#ws-professional [data-testid='pro-val-chat-send-button']")
    assert el.count() >= 1, "pro-val-chat-send-button not found inside #ws-professional"


@pytest.mark.e2e
def test_PVSS23_paperclip_upload_control_in_dom(page: Page, live_server: str) -> None:
    """PVSS23: pro-val-paperclip-upload-control is in DOM within ws-professional."""
    _block_api(page)
    _go_to_visible_pv(page, live_server)
    el = page.locator("#ws-professional [data-testid='pro-val-paperclip-upload-control']")
    assert el.count() >= 1, "pro-val-paperclip-upload-control not found inside #ws-professional"


# ─────────────────────────────────────────────────────────────────────────────
# PVSS24–PVSS26: Additional structural checks
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.e2e
def test_PVSS24_section_1_contains_basic_valuation_card(page: Page, live_server: str) -> None:
    """PVSS24: Section 1 contains pro-val-basic-valuation-card (the header span)."""
    _block_api(page)
    _go_to_visible_pv(page, live_server)
    el = page.locator("#ws-professional [data-testid='pro-val-basic-valuation-card']")
    assert el.count() >= 1, (
        "pro-val-basic-valuation-card not found inside #ws-professional Section 1"
    )


@pytest.mark.e2e
def test_PVSS25_engine_governance_audit_panel_exists(page: Page, live_server: str) -> None:
    """PVSS25: Engine governance audit panel (pro-val-engine-governance-audit-panel) exists with count>=1."""
    _block_api(page)
    _go_to_visible_pv(page, live_server)
    el = page.locator("[data-testid='pro-val-engine-governance-audit-panel']")
    assert el.count() >= 1, (
        "pro-val-engine-governance-audit-panel not found in DOM"
    )


@pytest.mark.e2e
def test_PVSS26_professional_wizard_wrapper_exists_in_ws_professional(page: Page, live_server: str) -> None:
    """PVSS26: professional-wizard wrapper exists within ws-professional."""
    _block_api(page)
    _go_to_visible_pv(page, live_server)
    el = page.locator("#ws-professional [data-testid='professional-wizard']")
    assert el.count() >= 1, (
        "data-testid='professional-wizard' not found inside #ws-professional"
    )
