"""
PVDSR E2E Browser Tests
Professional Valuation Page — Dynamic Special Asset Requirements (Section 2)

30 tests covering the five-group dynamic requirements panel:
- DOM presence / initial hidden state (PVDSR01-04)
- Panel visibility after subtype selection (PVDSR05-09)
- Five-group structure visible per group (PVDSR10-14)
- Progress bar, preservation marker, field types summary (PVDSR15-17)
- Methodology guidance panel (PVDSR18-19)
- Report / workbook context panel (PVDSR20-21)
- Future integrations placeholder (PVDSR22)
- Panel hides on family change (PVDSR23-24)
- Additional subtypes: cinema, hospital, school, heritage (PVDSR25-28)
- Regression: old requirements panel unaffected (PVDSR29)
- No internal paths in DOM (PVDSR30)
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


def _select_family(page: Page, family: str) -> None:
    page.locator('[data-testid="professional-asset-family"]').select_option(value=family)


def _select_subtype(page: Page, subtype: str) -> None:
    page.locator('[data-testid="professional-asset-subtype"]').select_option(value=subtype)


def _activate_padel(page: Page) -> None:
    """Select sports family + padel subtype to activate the five-group panel."""
    _select_family(page, "sports_recreation_assets")
    page.locator('[data-testid="professional-asset-subtype"]').wait_for(state="visible", timeout=5_000)
    _select_subtype(page, "padel_tennis_court")
    page.locator('[data-testid="pro-val-special-asset-requirements-panel"]').wait_for(
        state="visible", timeout=8_000
    )


# ── PVDSR01: Panel exists in DOM ──────────────────────────────────────────────

def test_PVDSR01_special_panel_in_dom(page: Page, live_server: str) -> None:
    """PVDSR01: pro-val-special-asset-requirements-panel exists in DOM."""
    _goto(page, live_server)
    panel = page.locator('[data-testid="pro-val-special-asset-requirements-panel"]')
    expect(panel).to_have_count(1)


# ── PVDSR02: Panel hidden by default ─────────────────────────────────────────

def test_PVDSR02_panel_hidden_initially(page: Page, live_server: str) -> None:
    """PVDSR02: Five-group panel is hidden (display:none) before any subtype is selected."""
    _goto(page, live_server)
    panel = page.locator('[data-testid="pro-val-special-asset-requirements-panel"]')
    expect(panel).to_be_hidden()


# ── PVDSR03: Progress bar element in DOM ──────────────────────────────────────

def test_PVDSR03_progress_bar_in_dom(page: Page, live_server: str) -> None:
    """PVDSR03: pro-val-special-asset-progress-bar element exists in DOM."""
    _goto(page, live_server)
    el = page.locator('[data-testid="pro-val-special-asset-progress-bar"]')
    expect(el).to_have_count(1)


# ── PVDSR04: Preservation marker in DOM ──────────────────────────────────────

def test_PVDSR04_preservation_marker_in_dom(page: Page, live_server: str) -> None:
    """PVDSR04: pro-val-special-asset-preservation-marker element exists in DOM."""
    _goto(page, live_server)
    el = page.locator('[data-testid="pro-val-special-asset-preservation-marker"]')
    expect(el).to_have_count(1)


# ── PVDSR05: Panel shows after padel subtype selected ─────────────────────────

def test_PVDSR05_panel_visible_after_padel_selection(page: Page, live_server: str) -> None:
    """PVDSR05: Five-group panel becomes visible when padel_tennis_court is selected."""
    _goto(page, live_server)
    _activate_padel(page)
    expect(
        page.locator('[data-testid="pro-val-special-asset-requirements-panel"]')
    ).to_be_visible()


# ── PVDSR06: Section 2 container still visible ───────────────────────────────

def test_PVDSR06_section2_still_visible_after_activation(page: Page, live_server: str) -> None:
    """PVDSR06: Section 2 pro-val-section-asset-type-selection is still visible after panel activation."""
    _goto(page, live_server)
    _activate_padel(page)
    expect(
        page.locator('[data-testid="pro-val-section-asset-type-selection"]')
    ).to_be_visible()


# ── PVDSR07: Descriptive group visible ───────────────────────────────────────

def test_PVDSR07_group_descriptive_visible(page: Page, live_server: str) -> None:
    """PVDSR07: pro-val-requirements-group-descriptive is visible after padel selection."""
    _goto(page, live_server)
    _activate_padel(page)
    expect(
        page.locator('[data-testid="pro-val-requirements-group-descriptive"]')
    ).to_be_visible()


# ── PVDSR08: Physical group visible ──────────────────────────────────────────

def test_PVDSR08_group_physical_visible(page: Page, live_server: str) -> None:
    """PVDSR08: pro-val-requirements-group-physical is visible after padel selection."""
    _goto(page, live_server)
    _activate_padel(page)
    expect(
        page.locator('[data-testid="pro-val-requirements-group-physical"]')
    ).to_be_visible()


# ── PVDSR09: Operational group visible ───────────────────────────────────────

def test_PVDSR09_group_operational_visible(page: Page, live_server: str) -> None:
    """PVDSR09: pro-val-requirements-group-operational is visible after padel selection."""
    _goto(page, live_server)
    _activate_padel(page)
    expect(
        page.locator('[data-testid="pro-val-requirements-group-operational"]')
    ).to_be_visible()


# ── PVDSR10: Legal group visible ─────────────────────────────────────────────

def test_PVDSR10_group_legal_visible(page: Page, live_server: str) -> None:
    """PVDSR10: pro-val-requirements-group-legal is visible after padel selection."""
    _goto(page, live_server)
    _activate_padel(page)
    expect(
        page.locator('[data-testid="pro-val-requirements-group-legal"]')
    ).to_be_visible()


# ── PVDSR11: Market group visible ─────────────────────────────────────────────

def test_PVDSR11_group_market_visible(page: Page, live_server: str) -> None:
    """PVDSR11: pro-val-requirements-group-market is visible after padel selection."""
    _goto(page, live_server)
    _activate_padel(page)
    expect(
        page.locator('[data-testid="pro-val-requirements-group-market"]')
    ).to_be_visible()


# ── PVDSR12: All five group testids in DOM ────────────────────────────────────

def test_PVDSR12_all_five_group_testids_in_dom(page: Page, live_server: str) -> None:
    """PVDSR12: All five group data-testid containers exist in DOM."""
    _goto(page, live_server)
    groups = [
        "pro-val-requirements-group-descriptive",
        "pro-val-requirements-group-physical",
        "pro-val-requirements-group-operational",
        "pro-val-requirements-group-legal",
        "pro-val-requirements-group-market",
    ]
    for g in groups:
        expect(page.locator(f'[data-testid="{g}"]')).to_have_count(1), f"Missing testid: {g}"


# ── PVDSR13: Progress bar shows count after activation ───────────────────────

def test_PVDSR13_progress_bar_shows_count(page: Page, live_server: str) -> None:
    """PVDSR13: Progress bar text contains a number (requirement count) after padel activation."""
    _goto(page, live_server)
    _activate_padel(page)
    bar = page.locator('[data-testid="pro-val-special-asset-progress-bar"]')
    expect(bar).to_be_visible()
    bar_text = bar.inner_text()
    assert any(ch.isdigit() for ch in bar_text), (
        f"Progress bar should contain a digit (count), got: '{bar_text}'"
    )


# ── PVDSR14: Progress bar contains advisory note ──────────────────────────────

def test_PVDSR14_progress_bar_advisory(page: Page, live_server: str) -> None:
    """PVDSR14: Progress bar text contains 'استرشادي' (advisory) notice."""
    _goto(page, live_server)
    _activate_padel(page)
    bar_text = page.locator('[data-testid="pro-val-special-asset-progress-bar"]').inner_text()
    assert "استرشادي" in bar_text, (
        f"Progress bar must contain advisory notice 'استرشادي', got: '{bar_text}'"
    )


# ── PVDSR15: Preservation marker visible ─────────────────────────────────────

def test_PVDSR15_preservation_marker_visible(page: Page, live_server: str) -> None:
    """PVDSR15: Preservation marker is visible when panel is active."""
    _goto(page, live_server)
    _activate_padel(page)
    expect(
        page.locator('[data-testid="pro-val-special-asset-preservation-marker"]')
    ).to_be_visible()


# ── PVDSR16: Field types summary visible ─────────────────────────────────────

def test_PVDSR16_field_types_summary_visible(page: Page, live_server: str) -> None:
    """PVDSR16: pro-val-special-asset-field-types-summary is visible after activation."""
    _goto(page, live_server)
    _activate_padel(page)
    expect(
        page.locator('[data-testid="pro-val-special-asset-field-types-summary"]')
    ).to_be_visible()


# ── PVDSR17: Methodology guidance visible ────────────────────────────────────

def test_PVDSR17_methodology_guidance_visible(page: Page, live_server: str) -> None:
    """PVDSR17: pro-val-special-asset-methodology-guidance is visible after padel activation."""
    _goto(page, live_server)
    _activate_padel(page)
    expect(
        page.locator('[data-testid="pro-val-special-asset-methodology-guidance"]')
    ).to_be_visible()


# ── PVDSR18: Methodology contains advisory warning ───────────────────────────

def test_PVDSR18_methodology_contains_advisory_warning(page: Page, live_server: str) -> None:
    """PVDSR18: Methodology guidance section contains advisory-only text."""
    _goto(page, live_server)
    _activate_padel(page)
    meth = page.locator('[data-testid="pro-val-special-asset-methodology-guidance"]')
    meth_text = meth.inner_text()
    assert "استرشادي" in meth_text, (
        f"Methodology guidance must contain 'استرشادي', got: '{meth_text[:200]}'"
    )


# ── PVDSR19: Report/workbook context visible ──────────────────────────────────

def test_PVDSR19_report_workbook_context_visible(page: Page, live_server: str) -> None:
    """PVDSR19: pro-val-special-asset-report-workbook-context is visible after activation."""
    _goto(page, live_server)
    _activate_padel(page)
    expect(
        page.locator('[data-testid="pro-val-special-asset-report-workbook-context"]')
    ).to_be_visible()


# ── PVDSR20: Report context contains advisory warning ────────────────────────

def test_PVDSR20_report_context_contains_advisory(page: Page, live_server: str) -> None:
    """PVDSR20: Report/workbook context contains advisory-only warning."""
    _goto(page, live_server)
    _activate_padel(page)
    ctx = page.locator('[data-testid="pro-val-special-asset-report-workbook-context"]')
    ctx_text = ctx.inner_text()
    assert "استرشادي" in ctx_text, (
        f"Report context must contain 'استرشادي', got: '{ctx_text[:200]}'"
    )


# ── PVDSR21: Future integrations placeholder visible ─────────────────────────

def test_PVDSR21_future_integrations_visible(page: Page, live_server: str) -> None:
    """PVDSR21: pro-val-special-asset-future-integrations is visible after activation."""
    _goto(page, live_server)
    _activate_padel(page)
    expect(
        page.locator('[data-testid="pro-val-special-asset-future-integrations"]')
    ).to_be_visible()


# ── PVDSR22: Future integrations contains stub marker ────────────────────────

def test_PVDSR22_future_integrations_stub_marker(page: Page, live_server: str) -> None:
    """PVDSR22: Future integrations section contains 'future_stub' text."""
    _goto(page, live_server)
    _activate_padel(page)
    fi_text = page.locator(
        '[data-testid="pro-val-special-asset-future-integrations"]'
    ).inner_text()
    assert "future_stub" in fi_text, (
        f"Future integrations must contain 'future_stub', got: '{fi_text[:200]}'"
    )


# ── PVDSR23: Panel hides when family changes ──────────────────────────────────

def test_PVDSR23_panel_hides_on_family_change(page: Page, live_server: str) -> None:
    """PVDSR23: Special panel becomes hidden when the family dropdown is changed."""
    _goto(page, live_server)
    _activate_padel(page)
    expect(
        page.locator('[data-testid="pro-val-special-asset-requirements-panel"]')
    ).to_be_visible()
    _select_family(page, "healthcare_assets")
    expect(
        page.locator('[data-testid="pro-val-special-asset-requirements-panel"]')
    ).to_be_hidden()


# ── PVDSR24: Panel hides on family reset ─────────────────────────────────────

def test_PVDSR24_panel_hides_on_empty_family(page: Page, live_server: str) -> None:
    """PVDSR24: Special panel stays/goes hidden when family is reset to empty."""
    _goto(page, live_server)
    _activate_padel(page)
    # Select empty option
    page.locator('[data-testid="professional-asset-family"]').select_option(value="")
    expect(
        page.locator('[data-testid="pro-val-special-asset-requirements-panel"]')
    ).to_be_hidden()


# ── PVDSR25: Cinema subtype activates panel ──────────────────────────────────

def test_PVDSR25_cinema_subtype_activates_panel(page: Page, live_server: str) -> None:
    """PVDSR25: Selecting cinema subtype activates the five-group panel."""
    _goto(page, live_server)
    _select_family(page, "entertainment_assets")
    page.locator('[data-testid="professional-asset-subtype"]').wait_for(
        state="visible", timeout=5_000
    )
    _select_subtype(page, "cinema")
    page.locator('[data-testid="pro-val-special-asset-requirements-panel"]').wait_for(
        state="visible", timeout=8_000
    )
    expect(
        page.locator('[data-testid="pro-val-special-asset-requirements-panel"]')
    ).to_be_visible()


# ── PVDSR26: Hospital subtype activates panel ────────────────────────────────

def test_PVDSR26_hospital_subtype_activates_panel(page: Page, live_server: str) -> None:
    """PVDSR26: Selecting general_hospital subtype activates the five-group panel."""
    _goto(page, live_server)
    _select_family(page, "healthcare_assets")
    page.locator('[data-testid="professional-asset-subtype"]').wait_for(
        state="visible", timeout=5_000
    )
    _select_subtype(page, "general_hospital")
    page.locator('[data-testid="pro-val-special-asset-requirements-panel"]').wait_for(
        state="visible", timeout=8_000
    )
    expect(
        page.locator('[data-testid="pro-val-special-asset-requirements-panel"]')
    ).to_be_visible()


# ── PVDSR27: School subtype activates panel ──────────────────────────────────

def test_PVDSR27_school_campus_subtype_activates_panel(page: Page, live_server: str) -> None:
    """PVDSR27: Selecting school_campus subtype activates the five-group panel."""
    _goto(page, live_server)
    _select_family(page, "education_assets")
    page.locator('[data-testid="professional-asset-subtype"]').wait_for(
        state="visible", timeout=5_000
    )
    _select_subtype(page, "school_campus")
    page.locator('[data-testid="pro-val-special-asset-requirements-panel"]').wait_for(
        state="visible", timeout=8_000
    )
    expect(
        page.locator('[data-testid="pro-val-special-asset-requirements-panel"]')
    ).to_be_visible()


# ── PVDSR28: Heritage subtype activates panel ────────────────────────────────

def test_PVDSR28_heritage_subtype_activates_panel(page: Page, live_server: str) -> None:
    """PVDSR28: Selecting distinguished_architectural_heritage (under heritage_assets) activates the panel."""
    _goto(page, live_server)
    _select_family(page, "heritage_assets")
    page.locator('[data-testid="professional-asset-subtype"]').wait_for(
        state="visible", timeout=5_000
    )
    _select_subtype(page, "distinguished_architectural_heritage")
    page.locator('[data-testid="pro-val-special-asset-requirements-panel"]').wait_for(
        state="visible", timeout=8_000
    )
    expect(
        page.locator('[data-testid="pro-val-special-asset-requirements-panel"]')
    ).to_be_visible()


# ── PVDSR29: Old requirements panel still present ────────────────────────────

def test_PVDSR29_old_requirements_panel_still_present(page: Page, live_server: str) -> None:
    """PVDSR29: Regression — old pvr-vis-asset-requirements-panel still exists in #ws-professional (not deleted)."""
    _goto(page, live_server)
    # Scope to ws-professional to avoid counting the same testid in ws-backoffice
    old_panel = page.locator('#ws-professional [data-testid="pro-val-asset-requirements-panel"]')
    # Panel may be hidden but must exist in DOM
    expect(old_panel).to_have_count(1)


# ── PVDSR30: No internal paths in special panel DOM ──────────────────────────

def test_PVDSR30_no_internal_paths_in_panel_dom(page: Page, live_server: str) -> None:
    """PVDSR30: Five-group panel DOM must not expose internal server file paths."""
    _goto(page, live_server)
    _activate_padel(page)
    panel = page.locator('[data-testid="pro-val-special-asset-requirements-panel"]')
    panel_html = panel.inner_html()
    assert "C:\\" not in panel_html, "Panel HTML must not expose Windows paths"
    assert "core_engine/" not in panel_html, "Panel HTML must not expose core_engine path"
    assert "/home/" not in panel_html, "Panel HTML must not expose /home/ paths"
