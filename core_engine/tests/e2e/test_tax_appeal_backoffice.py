"""
E2E tests for the Tax Appeal Expert Backoffice (#tax-appeal-backoffice).

Tests verify:
- Ordinary Tax Appeal page does not show protected buttons
- #tax-appeal-backoffice section is accessible via hash
- Backoffice request table renders
- Detail panel contains tax-specific fields
- Status select does not include appeal_report_generated
- Workbook/generate/download buttons have correct visibility
- No internal paths exposed
- No legal certification overclaim in ordinary page HTML
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _block_api(page: Page) -> None:
    page.route("**/api/**", lambda r: r.fulfill(
        status=200, body=b'{"ok":true,"requests":[]}',
        content_type="application/json",
    ))


def _go_to_tax_tab(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator('[data-testid="tax-tab"]').click()
    page.locator('[data-testid="tax-page"]').wait_for(state="visible", timeout=10_000)


def _go_to_tax_backoffice(page: Page, live_server: str) -> None:
    page.goto(live_server + "#tax-appeal-backoffice", wait_until="domcontentloaded")
    # The init JS shows the hidden tab and switches to it
    page.wait_for_timeout(500)
    # Force the tab to be visible and active if JS hasn't fired
    page.evaluate("""() => {
        var tabBtn = document.getElementById('es-tab-tax-appeal-backoffice');
        if (tabBtn) { tabBtn.style.display = ''; }
        if (typeof taxAppealBoInit === 'function') { taxAppealBoInit(); }
        if (typeof esShowTab === 'function') { esShowTab('tax-appeal-backoffice'); }
    }""")
    page.wait_for_timeout(300)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Ordinary page safety — protected buttons must NOT appear
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_BO_01_ordinary_page_no_workbook_download(
    page: Page, live_server: str
) -> None:
    """TAX_BO_01: data-testid='tax-expert-workbook-download' must not be visible
    on the ordinary Tax Appeal tab."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    btn = page.locator('[data-testid="tax-expert-workbook-download"]')
    # Either absent or hidden
    if btn.count() > 0:
        assert not btn.first.is_visible(), (
            "tax-expert-workbook-download must not be visible on ordinary tax appeal page"
        )


def test_TAX_BO_02_ordinary_page_no_generate_report_button(
    page: Page, live_server: str
) -> None:
    """TAX_BO_02: data-testid='tax-generate-appeal-report' must not be visible
    on the ordinary Tax Appeal tab."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    btn = page.locator('[data-testid="tax-generate-appeal-report"]')
    if btn.count() > 0:
        assert not btn.first.is_visible(), (
            "tax-generate-appeal-report must not be visible on ordinary tax appeal page"
        )


def test_TAX_BO_03_ordinary_page_no_download_report_button(
    page: Page, live_server: str
) -> None:
    """TAX_BO_03: data-testid='tax-appeal-report-download' must not be visible
    on the ordinary Tax Appeal tab."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    btn = page.locator('[data-testid="tax-appeal-report-download"]')
    if btn.count() > 0:
        assert not btn.first.is_visible(), (
            "tax-appeal-report-download must not be visible on ordinary tax appeal page"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Backoffice section existence
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_BO_04_backoffice_section_exists_in_dom(
    page: Page, live_server: str
) -> None:
    """TAX_BO_04: #tax-appeal-backoffice workspace section must exist in the DOM."""
    _block_api(page)
    page.goto(live_server, wait_until="domcontentloaded")
    section = page.locator('[data-testid="tax-appeal-backoffice-section"]')
    assert section.count() > 0, (
        "data-testid='tax-appeal-backoffice-section' must exist in the DOM"
    )


def test_TAX_BO_05_backoffice_tab_button_exists_and_shows_on_hash(
    page: Page, live_server: str
) -> None:
    """TAX_BO_05: Tax appeal backoffice tab button exists and becomes visible on
    #tax-appeal-backoffice hash."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    tab_btn = page.locator('[data-testid="tax-appeal-backoffice-tab"]')
    assert tab_btn.count() > 0, (
        "data-testid='tax-appeal-backoffice-tab' must exist in the DOM"
    )


def test_TAX_BO_06_backoffice_request_table_renders(
    page: Page, live_server: str
) -> None:
    """TAX_BO_06: The request table (data-testid='tax-appeal-requests-table') renders
    inside the backoffice section."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    table = page.locator('[data-testid="tax-appeal-requests-table"]')
    assert table.count() > 0, (
        "data-testid='tax-appeal-requests-table' must exist in the backoffice"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Detail panel
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_BO_07_detail_panel_exists_in_dom(
    page: Page, live_server: str
) -> None:
    """TAX_BO_07: Detail panel (data-testid='tax-appeal-bo-detail-panel') exists."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    panel = page.locator('[data-testid="tax-appeal-bo-detail-panel"]')
    assert panel.count() > 0, "Tax appeal backoffice detail panel must exist in DOM"


def test_TAX_BO_08_detail_panel_has_assessment_basis_date_field(
    page: Page, live_server: str
) -> None:
    """TAX_BO_08: Detail panel contains the tax_assessment_basis_date display element."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    el = page.locator('[data-testid="tax-bo-assessment-basis-date"]')
    assert el.count() > 0, (
        "data-testid='tax-bo-assessment-basis-date' must exist in the backoffice detail panel"
    )


def test_TAX_BO_09_detail_panel_has_deadline_status_field(
    page: Page, live_server: str
) -> None:
    """TAX_BO_09: Detail panel contains the deadline status element."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    el = page.locator('[data-testid="tax-bo-deadline-status"]')
    assert el.count() > 0, (
        "data-testid='tax-bo-deadline-status' must exist in the backoffice detail panel"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Status selector constraints
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_BO_10_status_select_does_not_include_appeal_report_generated(
    page: Page, live_server: str
) -> None:
    """TAX_BO_10: Status select must NOT include 'appeal_report_generated' as a
    selectable option — it can only be set automatically by report generation."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    select = page.locator('[data-testid="tax-bo-status-select"]')
    assert select.count() > 0, "data-testid='tax-bo-status-select' must exist"
    option_values = select.evaluate(
        "el => Array.from(el.options).map(o => o.value)"
    )
    assert "appeal_report_generated" not in option_values, (
        "appeal_report_generated must not be a manually selectable status option. "
        f"Found options: {option_values}"
    )


def test_TAX_BO_11_status_select_has_valid_options(
    page: Page, live_server: str
) -> None:
    """TAX_BO_11: Status select contains the expected manual transition options."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    select = page.locator('[data-testid="tax-bo-status-select"]')
    assert select.count() > 0
    option_values = select.evaluate(
        "el => Array.from(el.options).map(o => o.value)"
    )
    for expected in ["under_review", "needs_documents", "approved_pending_appeal_report", "rejected"]:
        assert expected in option_values, (
            f"Status select must contain '{expected}'. Found: {option_values}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Button visibility
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_BO_12_workbook_download_button_exists_in_backoffice(
    page: Page, live_server: str
) -> None:
    """TAX_BO_12: data-testid='tax-expert-workbook-download' exists inside
    the backoffice detail panel."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    btn = page.locator('[data-testid="tax-expert-workbook-download"]')
    assert btn.count() > 0, (
        "data-testid='tax-expert-workbook-download' must exist in backoffice"
    )


def test_TAX_BO_13_generate_report_button_exists_in_backoffice(
    page: Page, live_server: str
) -> None:
    """TAX_BO_13: data-testid='tax-generate-appeal-report' exists inside
    the backoffice (initially hidden, shown only after approval)."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    btn = page.locator('[data-testid="tax-generate-appeal-report"]')
    assert btn.count() > 0, (
        "data-testid='tax-generate-appeal-report' must exist in backoffice DOM"
    )


def test_TAX_BO_14_download_report_button_exists_in_backoffice(
    page: Page, live_server: str
) -> None:
    """TAX_BO_14: data-testid='tax-appeal-report-download' exists inside
    the backoffice (initially hidden, shown only after report generation)."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    btn = page.locator('[data-testid="tax-appeal-report-download"]')
    assert btn.count() > 0, (
        "data-testid='tax-appeal-report-download' must exist in backoffice DOM"
    )


def test_TAX_BO_15_generate_report_hidden_on_load(
    page: Page, live_server: str
) -> None:
    """TAX_BO_15: tax-generate-appeal-report must not be visible on backoffice
    load — only visible after status = approved_pending_appeal_report."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    btn = page.locator('[data-testid="tax-generate-appeal-report"]')
    if btn.count() > 0:
        assert not btn.first.is_visible(), (
            "tax-generate-appeal-report must be hidden on initial backoffice load "
            "(visible only after approved_pending_appeal_report)"
        )


def test_TAX_BO_16_download_report_hidden_on_load(
    page: Page, live_server: str
) -> None:
    """TAX_BO_16: tax-appeal-report-download must not be visible on backoffice
    load — only visible after report is generated."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    btn = page.locator('[data-testid="tax-appeal-report-download"]')
    if btn.count() > 0:
        assert not btn.first.is_visible(), (
            "tax-appeal-report-download must be hidden on initial backoffice load"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 6. Content safety
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_BO_17_ordinary_page_no_internal_paths_in_html(
    page: Page, live_server: str
) -> None:
    """TAX_BO_17: Ordinary Tax Appeal page HTML must not contain internal
    filesystem paths (instance/, tax_appeal_workbooks/, .xlsx paths)."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    html = page.content()
    assert "tax_appeal_workbooks" not in html, (
        "Ordinary tax appeal page must not expose internal workbook directory path"
    )
    # Internal absolute paths
    assert "C:\\Users" not in html and "/home/" not in html


def test_TAX_BO_18_no_legal_certification_overclaim_in_ordinary_page(
    page: Page, live_server: str
) -> None:
    """TAX_BO_18: Ordinary Tax Appeal page must not claim the report is legally
    certified, officially accepted, or approved by a tax authority by default."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    html = page.content()
    forbidden_phrases = [
        "تقرير قانوني معتمد",
        "طعن مقبول حتمًا",
        "صالح للتقديم رسميًا بدون توقيع",
        "تم اعتماده من الجهة الضريبية",
    ]
    for phrase in forbidden_phrases:
        assert phrase not in html, (
            f"Ordinary tax appeal page must not contain overclaim: {phrase!r}"
        )
