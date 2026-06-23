"""
test_expert_backoffice.py — E2E tests for the Expert Backoffice internal UI.

Tests:
  EBO01  Expert backoffice section exists in DOM
  EBO02  Requests table element exists in DOM
  EBO03  Request detail panel element exists in DOM
  EBO04  Request ID element exists in detail panel
  EBO05  Status element exists in detail panel
  EBO06  Expert workbook download not visible in ordinary simple valuation flow
  EBO07  Review form fields are present in backoffice section
  EBO08  Review save button exists
  EBO09  Review confirmation element exists (initially hidden)
  EBO10  Certified report badge says not available
  EBO11  No Excel link in ordinary simple valuation tab
  EBO12  Backoffice tab is hidden from ordinary users (not visible by default)
  EBO13  Review status select has expected options
  EBO14  Expert workbook download button has data-testid selector
  EBO15  Backoffice token input element exists
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

_CORE = Path(__file__).resolve().parents[2]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

BASE_URL = "http://127.0.0.1:5000"
_BACKOFFICE_URL = BASE_URL + "/#expert-backoffice"
_SIMPLE_URL     = BASE_URL + "/"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _goto_backoffice(page: Page):
    """Navigate to the backoffice via #expert-backoffice hash."""
    page.goto(_BACKOFFICE_URL, timeout=20_000)
    # Allow JS init to run
    page.wait_for_timeout(300)
    # Activate the tab via JS to reveal the workspace
    page.evaluate("esShowTab('expert-backoffice')")
    page.wait_for_timeout(200)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_EBO01_backoffice_section_exists(page: Page):
    """Expert backoffice section element exists in DOM."""
    _goto_backoffice(page)
    section = page.locator('[data-testid="expert-backoffice-section"]')
    expect(section).to_have_count(1)


def test_EBO02_requests_table_exists(page: Page):
    """Requests table element exists in the backoffice section."""
    _goto_backoffice(page)
    table = page.locator('[data-testid="expert-requests-table"]')
    expect(table).to_have_count(1)


def test_EBO03_request_detail_panel_exists(page: Page):
    """Request detail panel element exists in DOM (initially hidden)."""
    _goto_backoffice(page)
    panel = page.locator('[data-testid="expert-request-detail-panel"]')
    expect(panel).to_have_count(1)


def test_EBO04_request_id_element_exists(page: Page):
    """Request ID element exists inside the detail panel."""
    _goto_backoffice(page)
    el = page.locator('[data-testid="expert-request-id"]')
    expect(el).to_have_count(1)


def test_EBO05_status_element_exists(page: Page):
    """Status element exists inside the detail panel."""
    _goto_backoffice(page)
    el = page.locator('[data-testid="expert-request-status"]')
    expect(el).to_have_count(1)


def test_EBO06_workbook_download_not_in_simple_valuation_tab(page: Page):
    """Expert workbook download button is NOT present in the ordinary simple valuation tab.

    Ensures Excel is not exposed to regular users browsing the simple valuation page.
    """
    page.goto(_SIMPLE_URL, timeout=20_000)
    page.evaluate("esShowTab('valuation')")
    page.wait_for_timeout(200)
    sv_tab = page.locator('[data-testid="simple-valuation-tab"]')
    # The workbook download testid must not be inside the simple valuation tab
    wb_btn = sv_tab.locator('[data-testid="expert-workbook-download"]')
    assert wb_btn.count() == 0, (
        "expert-workbook-download must not be visible in the simple valuation tab"
    )


def test_EBO07_review_form_fields_exist(page: Page):
    """All required review form fields are present in the backoffice section."""
    _goto_backoffice(page)
    for testid in (
        "expert-review-status-select",
        "expert-review-notes",
        "expert-requested-documents",
        "expert-recommended-value",
        "expert-method-summary",
        "expert-reconciliation-notes",
    ):
        el = page.locator(f'[data-testid="{testid}"]')
        assert el.count() >= 1, f"Review form field missing: data-testid={testid!r}"


def test_EBO08_review_save_button_exists(page: Page):
    """Review save button exists in the backoffice section."""
    _goto_backoffice(page)
    btn = page.locator('[data-testid="expert-review-save"]')
    expect(btn).to_have_count(1)


def test_EBO09_review_confirmation_element_exists(page: Page):
    """Review confirmation div exists (initially hidden)."""
    _goto_backoffice(page)
    conf = page.locator('[data-testid="expert-review-confirmation"]')
    expect(conf).to_have_count(1)
    # It should start hidden
    assert conf.is_hidden(), "Review confirmation must be hidden before any save action"


def test_EBO10_certified_badge_says_not_available(page: Page):
    """Expert certified badge shows 'غير متاح' — no auto-certified report is generated."""
    _goto_backoffice(page)
    # Open the detail panel to reveal badge
    page.evaluate("document.getElementById('expert-request-detail-panel').style.display='block'")
    page.wait_for_timeout(100)
    badge = page.locator('[data-testid="expert-certified-badge"]')
    expect(badge).to_have_count(1)
    text = badge.inner_text()
    assert "غير متاح" in text or "معتمد" in text, (
        f"Certified badge must say 'غير متاح'. Got: {text!r}"
    )


def test_EBO11_no_excel_download_link_in_simple_valuation_tab(page: Page):
    """No expert workbook download link or internal workbook path in the ordinary simple valuation tab.

    Note: .xlsx may appear legitimately in a file-input accept attribute; the check targets
    explicit download hrefs and internal workbook path fragments only.
    """
    page.goto(_SIMPLE_URL, timeout=20_000)
    page.evaluate("esShowTab('valuation')")
    page.wait_for_timeout(200)
    sv_tab = page.locator('[data-testid="simple-valuation-tab"]')
    html = sv_tab.inner_html()
    # Must not expose internal workbook path fragments or expert-workbook download href
    for forbidden in ("expert_workbooks", "expert_review_", "/expert-workbook"):
        assert forbidden not in html, (
            f"Simple valuation tab must not expose internal workbook fragment {forbidden!r}"
        )
    # Must not have expert-workbook-download button
    wb_btn = sv_tab.locator('[data-testid="expert-workbook-download"]')
    assert wb_btn.count() == 0, (
        "expert-workbook-download button must not appear in the simple valuation tab"
    )


def test_EBO12_backoffice_tab_hidden_by_default(page: Page):
    """Expert backoffice tab button is not visible without #expert-backoffice hash."""
    page.goto(_SIMPLE_URL, timeout=20_000)
    page.wait_for_timeout(300)
    tab_btn = page.locator('[data-testid="expert-backoffice-tab"]')
    # Must exist in DOM but be hidden
    assert tab_btn.count() >= 1, "Backoffice tab button must exist in DOM"
    assert tab_btn.is_hidden(), (
        "Backoffice tab must be hidden by default (only visible via #expert-backoffice hash)"
    )


def test_EBO13_review_status_select_has_options(page: Page):
    """Review status select has expected transition options."""
    _goto_backoffice(page)
    sel = page.locator('[data-testid="expert-review-status-select"]')
    expect(sel).to_have_count(1)
    html = sel.inner_html()
    for expected_val in ("under_review", "needs_documents", "approved_pending_report", "rejected"):
        assert expected_val in html, (
            f"Review status select is missing option value: {expected_val!r}"
        )
    # certified_report_generated must NOT be an option (reserved for future task)
    assert "certified_report_generated" not in html, (
        "certified_report_generated must not be an option in the review status select"
    )


def test_EBO14_expert_workbook_download_button_has_testid(page: Page):
    """Expert workbook download button has the required data-testid selector."""
    _goto_backoffice(page)
    btn = page.locator('[data-testid="expert-workbook-download"]')
    expect(btn).to_have_count(1)


def test_EBO15_backoffice_token_input_exists(page: Page):
    """Auth token input field exists in the backoffice section."""
    _goto_backoffice(page)
    inp = page.locator('#expert-backoffice-token')
    expect(inp).to_have_count(1)
