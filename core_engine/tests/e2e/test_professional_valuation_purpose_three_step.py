"""
PVPTS E2E Browser Tests
Professional Valuation Page — Section 3 Three-Step Restructure

26 tests covering Step 3.1 / 3.2 / 3.3 container visibility, routing summary
panel, disclosures/warnings section, new dropdown options, partial interest
panel, and no-internal-paths DOM assertion.

All tests navigate to the live server root URL where ws-professional is the
default active workspace — same pattern as PVPBSR / PVVIS tests.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


# ── Helpers ───────────────────────────────────────────────────────────────────

def _goto(page: Page, live_server: str) -> None:
    """Navigate and wait for the professional wizard to be visible."""
    page.route("**/api/**", lambda r: r.fulfill(
        status=200, body=b'{"ok":true}', content_type="application/json"
    ))
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator('[data-testid="professional-wizard"]').wait_for(
        state="visible", timeout=12_000
    )


def _section3(page: Page):
    return page.locator('#ws-professional [data-testid="pro-val-section-valuation-purpose"]')


# ── PVPTS01 — Section 3 outer container visible ───────────────────────────────

def test_PVPTS01_section3_visible(page: Page, live_server: str) -> None:
    """Section 3 الغرض من التقييم outer container is visible on the page."""
    _goto(page, live_server)
    expect(_section3(page)).to_be_visible()


# ── PVPTS02 — Step 3.1 wrapper visible ───────────────────────────────────────

def test_PVPTS02_step31_wrapper_visible(page: Page, live_server: str) -> None:
    """Step 3.1 wrapper [data-testid=pro-val-purpose-step] is visible."""
    _goto(page, live_server)
    step = _section3(page).locator('[data-testid="pro-val-purpose-step"]')
    expect(step).to_be_visible()


# ── PVPTS03 — Step 3.2 wrapper visible ───────────────────────────────────────

def test_PVPTS03_step32_wrapper_visible(page: Page, live_server: str) -> None:
    """Step 3.2 wrapper [data-testid=pro-val-intended-user-pathway-step] is visible."""
    _goto(page, live_server)
    step = _section3(page).locator('[data-testid="pro-val-intended-user-pathway-step"]')
    expect(step).to_be_visible()


# ── PVPTS04 — Step 3.3 wrapper visible ───────────────────────────────────────

def test_PVPTS04_step33_wrapper_visible(page: Page, live_server: str) -> None:
    """Step 3.3 wrapper [data-testid=pro-val-basis-value-premise-step] is visible."""
    _goto(page, live_server)
    step = _section3(page).locator('[data-testid="pro-val-basis-value-premise-step"]')
    expect(step).to_be_visible()


# ── PVPTS05 — Step 3.1 heading contains "3.1" ────────────────────────────────

def test_PVPTS05_step31_heading_label(page: Page, live_server: str) -> None:
    """Step 3.1 heading text contains '3.1'."""
    _goto(page, live_server)
    step = _section3(page).locator('[data-testid="pro-val-purpose-step"]')
    # Assert text '3.1' appears somewhere inside the step
    expect(step).to_contain_text("3.1")


# ── PVPTS06 — Step 3.2 heading contains "3.2" ────────────────────────────────

def test_PVPTS06_step32_heading_label(page: Page, live_server: str) -> None:
    """Step 3.2 heading text contains '3.2'."""
    _goto(page, live_server)
    step = _section3(page).locator('[data-testid="pro-val-intended-user-pathway-step"]')
    expect(step).to_contain_text("3.2")


# ── PVPTS07 — Step 3.3 heading contains "3.3" ────────────────────────────────

def test_PVPTS07_step33_heading_label(page: Page, live_server: str) -> None:
    """Step 3.3 heading text contains '3.3'."""
    _goto(page, live_server)
    step = _section3(page).locator('[data-testid="pro-val-basis-value-premise-step"]')
    expect(step).to_contain_text("3.3")


# ── PVPTS08 — Routing summary panel present ───────────────────────────────────

def test_PVPTS08_routing_summary_section_present(page: Page, live_server: str) -> None:
    """Routing summary panel [data-testid=pro-val-purpose-routing-summary] is present in DOM."""
    _goto(page, live_server)
    panel = _section3(page).locator('[data-testid="pro-val-purpose-routing-summary"]')
    expect(panel).to_have_count(1)


# ── PVPTS09 — Routing summary text element present ───────────────────────────

def test_PVPTS09_routing_summary_text_element_present(page: Page, live_server: str) -> None:
    """Routing summary text element [data-testid=pro-val-purpose-routing-summary-text] is in DOM."""
    _goto(page, live_server)
    el = _section3(page).locator('[data-testid="pro-val-purpose-routing-summary-text"]')
    expect(el).to_have_count(1)


# ── PVPTS10 — Routing methods list element present ───────────────────────────

def test_PVPTS10_routing_methods_list_present(page: Page, live_server: str) -> None:
    """Routing methods list [data-testid=pro-val-purpose-routing-methods-list] is in DOM."""
    _goto(page, live_server)
    el = _section3(page).locator('[data-testid="pro-val-purpose-routing-methods-list"]')
    expect(el).to_have_count(1)


# ── PVPTS11 — Required disclosures list element present ───────────────────────

def test_PVPTS11_routing_disclosures_list_present(page: Page, live_server: str) -> None:
    """Required disclosures list [data-testid=pro-val-purpose-routing-required-disclosures-list] in DOM."""
    _goto(page, live_server)
    el = _section3(page).locator(
        '[data-testid="pro-val-purpose-routing-required-disclosures-list"]'
    )
    expect(el).to_have_count(1)


# ── PVPTS12 — Disclosures/warnings section NOT visible (removed from visible UI) ──────────────────

def test_PVPTS12_disclosures_warnings_section_not_visible(page: Page, live_server: str) -> None:
    """Disclosures & warnings section [data-testid=pro-val-purpose-disclosures-warnings] NOT visible (removed)."""
    _goto(page, live_server)
    section = _section3(page).locator('[data-testid="pro-val-purpose-disclosures-warnings"]')
    expect(section).not_to_be_visible()


# ── PVPTS13 — Legacy disclosures-warnings subsection still present ────────────

def test_PVPTS13_legacy_disclosures_warnings_subsection_present(page: Page, live_server: str) -> None:
    """Legacy testid [data-testid=pro-val-disclosures-warnings-subsection] still present in DOM."""
    _goto(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-disclosures-warnings-subsection"]')
    expect(el).to_have_count(1)


# ── PVPTS14 — New purpose warning list present ────────────────────────────────

def test_PVPTS14_purpose_warning_list_present(page: Page, live_server: str) -> None:
    """New warning list [data-testid=pro-val-purpose-warning-list] is present in DOM."""
    _goto(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-purpose-warning-list"]')
    expect(el).to_have_count(1)


# ── PVPTS15 — Legacy warning list alias span present ─────────────────────────

def test_PVPTS15_legacy_warning_list_alias_present(page: Page, live_server: str) -> None:
    """Legacy alias [data-testid=pro-val-warning-list] span still present (for backward compat)."""
    _goto(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-warning-list"]')
    expect(el).to_have_count(1)


# ── PVPTS16 — Disclosure list present ────────────────────────────────────────

def test_PVPTS16_disclosure_list_present(page: Page, live_server: str) -> None:
    """Disclosure list [data-testid=pro-val-disclosure-list] is present in DOM."""
    _goto(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-disclosure-list"]')
    expect(el).to_have_count(1)


# ── PVPTS17 — Review required flags element present ──────────────────────────

def test_PVPTS17_review_required_flags_present(page: Page, live_server: str) -> None:
    """Review required flags [data-testid=pro-val-review-required-flags] present in DOM."""
    _goto(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-review-required-flags"]')
    expect(el).to_have_count(1)


# ── PVPTS18 — Intended user subsection visible ────────────────────────────────

def test_PVPTS18_intended_user_subsection_visible(page: Page, live_server: str) -> None:
    """Intended user subsection [data-testid=pro-val-intended-user-subsection] is visible."""
    _goto(page, live_server)
    el = _section3(page).locator('[data-testid="pro-val-intended-user-subsection"]')
    expect(el).to_be_visible()


# ── PVPTS19 — Professional purpose section visible ────────────────────────────

def test_PVPTS19_professional_purpose_section_visible(page: Page, live_server: str) -> None:
    """Professional purpose section [data-testid=pro-val-professional-purpose-section] visible."""
    _goto(page, live_server)
    el = _section3(page).locator('[data-testid="pro-val-professional-purpose-section"]')
    expect(el).to_be_visible()


# ── PVPTS20 — New pathway option tax_authority_path present ──────────────────

def test_PVPTS20_new_pathway_tax_authority_path_present(page: Page, live_server: str) -> None:
    """New professional_purpose_path option 'tax_authority_path' is in the dropdown."""
    _goto(page, live_server)
    sel = _section3(page).locator('[data-testid="pro-val-professional-purpose-path-select"]')
    opt = sel.locator('option[value="tax_authority_path"]')
    expect(opt).to_have_count(1)


# ── PVPTS21 — New pathway option ifrs_financial_reporting_path present ────────

def test_PVPTS21_new_pathway_ifrs_path_present(page: Page, live_server: str) -> None:
    """New professional_purpose_path option 'ifrs_financial_reporting_path' is in the dropdown."""
    _goto(page, live_server)
    sel = _section3(page).locator('[data-testid="pro-val-professional-purpose-path-select"]')
    opt = sel.locator('option[value="ifrs_financial_reporting_path"]')
    expect(opt).to_have_count(1)


# ── PVPTS22 — New intended_user_category option 'bank' present ───────────────

def test_PVPTS22_new_user_category_bank_present(page: Page, live_server: str) -> None:
    """New intended_user_category option 'bank' is present in the dropdown."""
    _goto(page, live_server)
    sel = _section3(page).locator('[data-testid="pro-val-intended-user-category-select"]')
    opt = sel.locator('option[value="bank"]')
    expect(opt).to_have_count(1)


# ── PVPTS23 — New intended_user_category option 'court' present ──────────────

def test_PVPTS23_new_user_category_court_present(page: Page, live_server: str) -> None:
    """New intended_user_category option 'court' is present in the dropdown."""
    _goto(page, live_server)
    sel = _section3(page).locator('[data-testid="pro-val-intended-user-category-select"]')
    opt = sel.locator('option[value="court"]')
    expect(opt).to_have_count(1)


# ── PVPTS24 — Basis of value select visible ───────────────────────────────────

def test_PVPTS24_basis_of_value_select_visible(page: Page, live_server: str) -> None:
    """Basis of value select [data-testid=pro-val-basis-of-value-select] is visible."""
    _goto(page, live_server)
    sel = _section3(page).locator('[data-testid="pro-val-basis-of-value-select"]')
    expect(sel).to_be_visible()


# ── PVPTS25 — Partial interest panel present in DOM ──────────────────────────

def test_PVPTS25_partial_interest_panel_in_dom(page: Page, live_server: str) -> None:
    """Partial interest panel [data-testid=pro-val-partial-interest-panel] is present in DOM."""
    _goto(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-partial-interest-panel"]')
    expect(el).to_have_count(1)


# ── PVPTS26 — No internal file-system paths in the DOM ───────────────────────

def test_PVPTS26_no_internal_paths_in_dom(page: Page, live_server: str) -> None:
    """Section 3 DOM content must not contain any internal file-system path fragments."""
    _goto(page, live_server)
    section_html = _section3(page).inner_html()
    forbidden_fragments = [
        "core_engine/",
        "C:\\Users",
        "c:\\users",
        "__file__",
        "/home/",
        "/var/",
        "instance/",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in section_html, (
            f"Internal path fragment '{fragment}' found in Section 3 DOM"
        )
