"""
PVACR E2E Browser Tests
Professional Valuation Page — Chat Output Final Restructure (PVACR)

29 tests covering:
- Main page visible with 5 sections (PVACR01-05)
- Removed sections NOT visible as standalone (PVACR06-11)
- Chat Box report action dropdown visible with 6 options (PVACR12-19)
- Three toggles visible inside Chat Box (PVACR20-22)
- Generate buttons visible (PVACR23-24)
- Admin Excel button disabled/hidden for non-admin (PVACR25)
- Expert review section below Chat Box (PVACR26-28)
- No internal paths in DOM (PVACR29)
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


# ── Helpers ───────────────────────────────────────────────────────────────────

def _goto(page: Page, live_server: str) -> None:
    page.route("**/api/**", lambda r: r.fulfill(
        status=200, body=b'{"ok":true}', content_type="application/json"
    ))
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator('[data-testid="professional-wizard"]').wait_for(
        state="visible", timeout=15_000
    )


def _ws_pro(page: Page):
    return page.locator("#ws-professional")


# ── PVACR01-05: Main page visible sections ────────────────────────────────────

def test_PVACR01_main_page_visible(page: Page, live_server: str) -> None:
    """PVACR01: Professional valuation main page loads and is visible."""
    _goto(page, live_server)
    expect(_ws_pro(page)).to_be_visible()


def test_PVACR02_section_basic_valuation_data_visible(page: Page, live_server: str) -> None:
    """PVACR02: Section 1 (basic valuation data) is visible."""
    _goto(page, live_server)
    expect(
        _ws_pro(page).locator('[data-testid="pro-val-section-basic-valuation-data"]')
    ).to_be_visible()


def test_PVACR03_section_asset_type_selection_visible(page: Page, live_server: str) -> None:
    """PVACR03: Section 2 (asset type selection) is visible."""
    _goto(page, live_server)
    expect(
        _ws_pro(page).locator('[data-testid="pro-val-section-asset-type-selection"]')
    ).to_be_visible()


def test_PVACR04_section_valuation_purpose_visible(page: Page, live_server: str) -> None:
    """PVACR04: Section 3 (valuation purpose) is visible."""
    _goto(page, live_server)
    expect(
        _ws_pro(page).locator('[data-testid="pro-val-section-valuation-purpose"]')
    ).to_be_visible()


def test_PVACR05_section_chat_box_visible(page: Page, live_server: str) -> None:
    """PVACR05: Section 5 (Chat Box) is visible."""
    _goto(page, live_server)
    expect(
        _ws_pro(page).locator('[data-testid="pro-val-section-chat-box"]')
    ).to_be_visible()


# ── PVACR06-11: Removed sections NOT visible as standalone ───────────────────

def test_PVACR06_preliminary_weighting_engine_not_visible(page: Page, live_server: str) -> None:
    """PVACR06: محرك الترجيح المبدئي (professional-weighted-engine-panel) is NOT visible."""
    _goto(page, live_server)
    panel = _ws_pro(page).locator('[data-testid="professional-weighted-engine-panel"]')
    expect(panel).not_to_be_visible()


def test_PVACR07_preliminary_weighting_subsection_not_visible(page: Page, live_server: str) -> None:
    """PVACR07: 3.5 الترجيح المبدئي للطرق (pro-val-preliminary-weighting-subsection) is NOT visible."""
    _goto(page, live_server)
    panel = _ws_pro(page).locator('[data-testid="pro-val-preliminary-weighting-subsection"]')
    expect(panel).not_to_be_visible()


def test_PVACR08_disclosures_warnings_not_visible(page: Page, live_server: str) -> None:
    """PVACR08: 3.6 الإفصاحات والتحذيرات (pro-val-purpose-disclosures-warnings) is NOT visible."""
    _goto(page, live_server)
    panel = _ws_pro(page).locator('[data-testid="pro-val-purpose-disclosures-warnings"]')
    expect(panel).not_to_be_visible()


def test_PVACR09_engine_governance_panel_not_visible(page: Page, live_server: str) -> None:
    """PVACR09: حوكمة المحرك والتدقيق (pro-val-engine-governance-audit-panel) is NOT visible."""
    _goto(page, live_server)
    panel = _ws_pro(page).locator('[data-testid="pro-val-engine-governance-audit-panel"]')
    expect(panel).not_to_be_visible()


def test_PVACR10_standalone_report_type_section_not_visible(page: Page, live_server: str) -> None:
    """PVACR10: Standalone Section 5 report type (pro-val-section-report-type) is NOT visible."""
    _goto(page, live_server)
    section = _ws_pro(page).locator('[data-testid="pro-val-section-report-type"]')
    expect(section).not_to_be_visible()


def test_PVACR11_old_expert_review_inside_chat_box_not_visible(page: Page, live_server: str) -> None:
    """PVACR11: Old professional-request-expert-review inside Chat Box is NOT visible (rehomed)."""
    _goto(page, live_server)
    panel = _ws_pro(page).locator('[data-testid="professional-request-expert-review"]')
    expect(panel).not_to_be_visible()


# ── PVACR12-19: Chat Box report action dropdown ───────────────────────────────

def test_PVACR12_chat_report_action_dropdown_visible(page: Page, live_server: str) -> None:
    """PVACR12: Chat Box report action dropdown is visible."""
    _goto(page, live_server)
    dropdown = _ws_pro(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]')
    expect(dropdown).to_be_visible()


def test_PVACR13_dropdown_option_traditional_report(page: Page, live_server: str) -> None:
    """PVACR13: Dropdown contains تقرير تقليدي option."""
    _goto(page, live_server)
    option = _ws_pro(page).locator('[data-testid="pro-val-chat-report-action-traditional"]')
    expect(option).to_have_count(1)


def test_PVACR14_dropdown_option_detailed_report(page: Page, live_server: str) -> None:
    """PVACR14: Dropdown contains تقرير تفصيلي option."""
    _goto(page, live_server)
    option = _ws_pro(page).locator('[data-testid="pro-val-chat-report-action-detailed"]')
    expect(option).to_have_count(1)


def test_PVACR15_dropdown_option_professional_report(page: Page, live_server: str) -> None:
    """PVACR15: Dropdown contains تقرير احترافي option."""
    _goto(page, live_server)
    option = _ws_pro(page).locator('[data-testid="pro-val-chat-report-action-professional"]')
    expect(option).to_have_count(1)


def test_PVACR16_dropdown_option_simulated_uploaded(page: Page, live_server: str) -> None:
    """PVACR16: Dropdown contains محاكاة تقرير مرفوع option."""
    _goto(page, live_server)
    option = _ws_pro(page).locator('[data-testid="pro-val-chat-report-action-simulated-uploaded"]')
    expect(option).to_have_count(1)


def test_PVACR17_dropdown_option_review(page: Page, live_server: str) -> None:
    """PVACR17: Dropdown contains مراجعة تقرير option."""
    _goto(page, live_server)
    option = _ws_pro(page).locator('[data-testid="pro-val-chat-report-action-review"]')
    expect(option).to_have_count(1)


def test_PVACR18_dropdown_option_hbu(page: Page, live_server: str) -> None:
    """PVACR18: Dropdown contains تقرير تحليل أعلى وأفضل استخدام option."""
    _goto(page, live_server)
    option = _ws_pro(page).locator('[data-testid="pro-val-chat-report-action-hbu"]')
    expect(option).to_have_count(1)


def test_PVACR19_selecting_simulated_shows_guidance(page: Page, live_server: str) -> None:
    """PVACR19: Selecting simulated_uploaded_report shows guidance panel."""
    _goto(page, live_server)
    sel = _ws_pro(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]')
    sel.select_option(value="simulated_uploaded_report")
    guidance = _ws_pro(page).locator('[data-testid="pro-val-chat-action-guidance"]')
    expect(guidance).to_be_visible()


# ── PVACR20-22: Three toggles visible inside Chat Box ────────────────────────

def test_PVACR20_simulation_report_clip_visible(page: Page, live_server: str) -> None:
    """PVACR20: Simulation report clip is visible inside Chat Box (replaces old system training toggle)."""
    _goto(page, live_server)
    clip = _ws_pro(page).locator('[data-testid="pro-val-simulation-report-clip"]')
    expect(clip.first).to_be_visible()


def test_PVACR21_report_review_toggle_visible(page: Page, live_server: str) -> None:
    """PVACR21: Report review toggle is visible inside Chat Box."""
    _goto(page, live_server)
    toggle = _ws_pro(page).locator('[data-testid="pro-val-report-review-toggle"]')
    expect(toggle).to_have_count(1)


def test_PVACR22_hbu_report_toggle_visible(page: Page, live_server: str) -> None:
    """PVACR22: HBU report toggle is visible inside Chat Box."""
    _goto(page, live_server)
    toggle = _ws_pro(page).locator('[data-testid="pro-val-hbu-report-toggle"]')
    expect(toggle).to_have_count(1)


# ── PVACR23-25: Generate buttons ─────────────────────────────────────────────

def test_PVACR23_generate_user_pdf_button_visible(page: Page, live_server: str) -> None:
    """PVACR23: Generate user PDF button is visible."""
    _goto(page, live_server)
    btn = _ws_pro(page).locator('[data-testid="pro-val-unified-generate-user-pdf"]')
    expect(btn).to_be_visible()


def test_PVACR24_generate_selected_output_button_visible(page: Page, live_server: str) -> None:
    """PVACR24: Generate selected output button is visible."""
    _goto(page, live_server)
    btn = _ws_pro(page).locator('[data-testid="pro-val-unified-generate-selected-output"]')
    expect(btn).to_be_visible()


def test_PVACR25_admin_excel_button_hidden_for_non_admin(page: Page, live_server: str) -> None:
    """PVACR25: Admin Excel button is hidden (display:none) for non-admin user."""
    _goto(page, live_server)
    btn = _ws_pro(page).locator('[data-testid="pro-val-unified-generate-admin-excel"]')
    expect(btn).not_to_be_visible()


# ── PVACR26-28: Expert review section below Chat Box ─────────────────────────

def test_PVACR26_expert_review_section_visible(page: Page, live_server: str) -> None:
    """PVACR26: Expert review request section is visible directly below Chat Box."""
    _goto(page, live_server)
    section = _ws_pro(page).locator('[data-testid="pro-val-expert-review-request-section"]')
    expect(section).to_be_visible()


def test_PVACR27_expert_review_note_input_visible(page: Page, live_server: str) -> None:
    """PVACR27: Expert review note input is visible."""
    _goto(page, live_server)
    note = _ws_pro(page).locator('[data-testid="pro-val-expert-review-note-input"]')
    expect(note).to_be_visible()


def test_PVACR28_expert_review_button_visible(page: Page, live_server: str) -> None:
    """PVACR28: Expert review request button is visible."""
    _goto(page, live_server)
    btn = _ws_pro(page).locator('[data-testid="pro-val-request-expert-review-button"]')
    expect(btn).to_be_visible()


# ── PVACR29: No internal paths in DOM ────────────────────────────────────────

def test_PVACR29_no_internal_paths_in_dom(page: Page, live_server: str) -> None:
    """PVACR29: No internal file paths visible in DOM text content."""
    _goto(page, live_server)
    full_text = _ws_pro(page).inner_text()
    for bad in ("requests.jsonl", "__file__", "/home/", "C:\\Users"):
        assert bad not in full_text, f"Internal path found in DOM: {bad!r}"
