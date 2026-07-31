"""
PVVIS01–PVVIS20 — Professional Valuation Visible UI Browser Proof Tests (Part F).

These tests navigate to the DEFAULT URL (no hash) so the default workspace
ws-professional (id="ws-professional", es-ws-active) is shown.  They prove that
the UX V2 five-section structure and input/generation controls are actually visible
to the user in the browser — not merely present in a hidden workspace.

Part F requirements:
  1.  pro-val-visible-ui-v2-marker visible
  2.  Section 1 (pro-val-section-asset-definition) visible
  3.  Section 2 (pro-val-section-assignment-purpose) visible
  4.  Section 3 (pro-val-section-basis-of-value) visible
  5.  Section 4 (pro-val-section-report-type) visible
  6.  Section 5 (pro-val-input-generation-section) visible
  7.  Report type select visible
  8.  Traditional / Detailed / Professional options visible
  9.  Input mode selector visible
  10. Auto-fill requirements toggle visible
  11. Prior report simulation toggle visible
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _go_to_visible_pv(page: Page, live_server: str) -> None:
    """Navigate to the default page — ws-professional is the active workspace."""
    page.route("**/api/**", lambda r: r.fulfill(
        status=200, body=b'{"ok":true}', content_type="application/json"
    ))
    page.goto(live_server, wait_until="domcontentloaded")
    # ws-professional is active by default — wait for wizard
    page.locator('[data-testid="professional-wizard"]').wait_for(state="visible", timeout=10_000)


# ─────────────────────────────────────────────────────────────────────────────
# PVVIS01–PVVIS06 — Visible marker and five section wrappers
# ─────────────────────────────────────────────────────────────────────────────

def test_PVVIS01_visible_ui_v2_marker_visible(page: Page, live_server: str) -> None:
    """PVVIS01: pro-val-visible-ui-v2-marker is visible on the default page load."""
    _go_to_visible_pv(page, live_server)
    marker = page.locator('[data-testid="pro-val-visible-ui-v2-marker"]')
    expect(marker).to_be_visible()


def test_PVVIS02_section_asset_definition_visible(page: Page, live_server: str) -> None:
    """PVVIS02: Section 2 wrapper (pro-val-section-asset-type-selection) is visible.
    Old testid pro-val-section-asset-definition is now a compat span; the active
    6-section layout uses pro-val-section-asset-type-selection for Section 2."""
    _go_to_visible_pv(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-section-asset-type-selection"]')
    expect(el).to_be_visible()


def test_PVVIS03_section_assignment_purpose_visible(page: Page, live_server: str) -> None:
    """PVVIS03: Section 3 wrapper (pro-val-section-valuation-purpose) is visible.
    Old pro-val-section-assignment-purpose is a compat span; purpose + basis are
    merged into Section 3 pro-val-section-valuation-purpose in the 6-section layout."""
    _go_to_visible_pv(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-section-valuation-purpose"]')
    expect(el).to_be_visible()


def test_PVVIS04_section_basis_of_value_visible(page: Page, live_server: str) -> None:
    """PVVIS04: Section 4 wrapper (pro-val-section-applied-valuation-standards) is visible.
    Old pro-val-section-basis-of-value is a compat span; the new 6-section layout adds
    Section 4 for applied valuation standards (معايير التقييم المطبقة)."""
    _go_to_visible_pv(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-section-applied-valuation-standards"]')
    expect(el).to_be_visible()


def test_PVVIS05_section_report_type_visible(page: Page, live_server: str) -> None:
    """PVVIS05: Section 4 wrapper (pro-val-section-report-type) is visible."""
    _go_to_visible_pv(page, live_server)
    el = page.locator('[data-testid="pro-val-section-report-type"]').first
    expect(el).to_be_visible()


def test_PVVIS06_input_generation_section_visible(page: Page, live_server: str) -> None:
    """PVVIS06: Section 5 wrapper (pro-val-input-generation-section) is visible."""
    _go_to_visible_pv(page, live_server)
    el = page.locator('[data-testid="pro-val-input-generation-section"]').first
    expect(el).to_be_visible()


# ─────────────────────────────────────────────────────────────────────────────
# PVVIS07–PVVIS09 — Report type and options
# ─────────────────────────────────────────────────────────────────────────────

def test_PVVIS07_unified_report_action_select_visible(page: Page, live_server: str) -> None:
    """PVVIS07: Unified report action select (canonical) is visible; legacy vis-report-type-select is NOT visible."""
    _go_to_visible_pv(page, live_server)
    # Legacy selector removed — now a hidden span
    expect(page.locator('[data-testid="pro-val-vis-report-type-select"]')).not_to_be_visible()
    # Canonical unified selector is visible in Chat Command Center
    expect(page.locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]')).to_be_visible()


def test_PVVIS08_unified_report_action_options_present(page: Page, live_server: str) -> None:
    """PVVIS08: Unified report action select has all 7 canonical options."""
    _go_to_visible_pv(page, live_server)
    sel = page.locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]')
    for val in ("traditional_report", "detailed_report", "professional_report",
                "simulated_uploaded_report", "report_review_output",
                "hbu_analysis_report", "standards_compliance_report"):
        opt = sel.locator(f'option[value="{val}"]')
        assert opt.count() == 1, f"Missing option: {val}"


def test_PVVIS09_basis_of_value_select_visible(page: Page, live_server: str) -> None:
    """PVVIS09: Basis of value select (Card 3) is visible in Section 3 of ws-professional.
    Testid renamed from pro-val-vis-basis-of-value-select to pro-val-basis-of-value-select (three-cards taxonomy).
    Uses .first because count=2 after adding Card 3 to visible workspace."""
    _go_to_visible_pv(page, live_server)
    sel = page.locator('[data-testid="pro-val-basis-of-value-select"]').first
    expect(sel).to_be_visible()


# ─────────────────────────────────────────────────────────────────────────────
# PVVIS10–PVVIS14 — Section 5 input/generation controls
# ─────────────────────────────────────────────────────────────────────────────

def test_PVVIS10_input_mode_selector_visible(page: Page, live_server: str) -> None:
    """PVVIS10: Input mode selector (pro-val-vis-input-mode-select) is visible."""
    _go_to_visible_pv(page, live_server)
    sel = page.locator('[data-testid="pro-val-vis-input-mode-select"]')
    expect(sel).to_be_visible()


def test_PVVIS11_auto_fill_toggle_visible(page: Page, live_server: str) -> None:
    """PVVIS11: Auto-fill requirements toggle (pro-val-vis-auto-fill-toggle) is visible."""
    _go_to_visible_pv(page, live_server)
    toggle = page.locator('[data-testid="pro-val-vis-auto-fill-toggle"]')
    expect(toggle).to_be_visible()


def test_PVVIS12_simulation_toggle_visible(page: Page, live_server: str) -> None:
    """PVVIS12: Report simulation toggle (pro-val-vis-report-simulation-toggle) is visible."""
    _go_to_visible_pv(page, live_server)
    toggle = page.locator('[data-testid="pro-val-vis-report-simulation-toggle"]')
    expect(toggle).to_be_visible()


def test_PVVIS13_four_generation_buttons_visible(page: Page, live_server: str) -> None:
    """PVVIS13: All four report generation buttons are visible."""
    _go_to_visible_pv(page, live_server)
    for tid in ("pro-val-vis-generate-traditional", "pro-val-vis-generate-detailed",
                "pro-val-vis-generate-professional", "pro-val-vis-generate-simulated"):
        btn = page.locator(f'[data-testid="{tid}"]')
        expect(btn).to_be_visible(), f"Button not visible: {tid}"


def test_PVVIS14_simulated_button_disabled_by_default(page: Page, live_server: str) -> None:
    """PVVIS14: pro-val-vis-generate-simulated button is disabled until toggle is enabled."""
    _go_to_visible_pv(page, live_server)
    btn = page.locator('[data-testid="pro-val-vis-generate-simulated"]')
    assert btn.is_disabled(), "Simulated button must be disabled by default"


# ─────────────────────────────────────────────────────────────────────────────
# PVVIS15–PVVIS17 — Upload controls (Mode A visible by default)
# ─────────────────────────────────────────────────────────────────────────────

def test_PVVIS15_upload_evidence_control_visible(page: Page, live_server: str) -> None:
    """PVVIS15: Upload evidence control is visible in Mode A panel."""
    _go_to_visible_pv(page, live_server)
    el = page.locator('[data-testid="pro-val-vis-upload-evidence"]')
    expect(el).to_be_visible()


def test_PVVIS16_upload_photos_control_visible(page: Page, live_server: str) -> None:
    """PVVIS16: Upload photos control is visible in Mode A panel."""
    _go_to_visible_pv(page, live_server)
    el = page.locator('[data-testid="pro-val-vis-upload-photos"]')
    expect(el).to_be_visible()


def test_PVVIS17_upload_aerial_control_visible(page: Page, live_server: str) -> None:
    """PVVIS17: Upload aerial map control is visible in Mode A panel."""
    _go_to_visible_pv(page, live_server)
    el = page.locator('[data-testid="pro-val-vis-upload-aerial"]')
    expect(el).to_be_visible()


# ─────────────────────────────────────────────────────────────────────────────
# PVVIS18–PVVIS20 — Mode switching and prior report upload
# ─────────────────────────────────────────────────────────────────────────────

def test_PVVIS18_chat_panel_hidden_by_default(page: Page, live_server: str) -> None:
    """PVVIS18: Chat/attachment panel is hidden until Mode B is selected."""
    _go_to_visible_pv(page, live_server)
    panel = page.locator('[data-testid="pro-val-vis-chat-panel"]')
    expect(panel).not_to_be_visible()


def test_PVVIS19_switch_to_chat_mode_shows_prior_report_upload(page: Page, live_server: str) -> None:
    """PVVIS19: Switching to Mode B shows the prior report upload control."""
    _go_to_visible_pv(page, live_server)
    page.locator('[data-testid="pro-val-vis-input-mode-select"]').select_option("chat_attachment_assisted_input")
    prior = page.locator('[data-testid="pro-val-vis-upload-prior-report"]')
    expect(prior).to_be_visible()


def test_PVVIS20_simulation_option_visible_after_toggle(page: Page, live_server: str) -> None:
    """PVVIS20: Simulation option div appears after enabling the simulation toggle."""
    _go_to_visible_pv(page, live_server)
    opt_div = page.locator('[data-testid="pro-val-vis-simulated-option"]')
    expect(opt_div).not_to_be_visible()
    page.locator('[data-testid="pro-val-vis-report-simulation-toggle"]').check()
    expect(opt_div).to_be_visible()
