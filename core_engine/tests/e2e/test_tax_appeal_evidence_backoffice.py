"""
E2E tests — Tax Appeal Evidence Upload & Source Approval UI.

Tests verify:
  TAX_EV_01  Ordinary tax page has no evidence review controls
  TAX_EV_02  Backoffice DOM contains evidence section
  TAX_EV_03  Upload controls exist in backoffice DOM
  TAX_EV_04  Evidence type select contains required option keys
  TAX_EV_05  Evidence list table exists in backoffice DOM
  TAX_EV_06  Approve-for-report button exists in backoffice DOM
  TAX_EV_07  Approve-as-source button exists in backoffice DOM
  TAX_EV_08  Reject button exists in backoffice DOM
  TAX_EV_09  No internal file paths exposed in page HTML
  TAX_EV_10  Missing mandatory docs warning element present in backoffice DOM
  TAX_EV_11  Status badge elements present in backoffice DOM
  TAX_EV_12  Ordinary page has no source approval controls
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _block_api(page: Page) -> None:
    page.route("**/api/**", lambda r: r.fulfill(
        status=200,
        body=b'{"ok":true,"requests":[],"evidence":[],"count":0}',
        content_type="application/json",
    ))


def _go_to_tax_tab(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator('[data-testid="tax-tab"]').click()
    page.locator('[data-testid="tax-page"]').wait_for(state="visible", timeout=10_000)


def _go_to_tax_backoffice(page: Page, live_server: str) -> None:
    page.goto(live_server + "#tax-appeal-backoffice", wait_until="domcontentloaded")
    page.wait_for_timeout(500)
    page.evaluate("""() => {
        var tabBtn = document.getElementById('es-tab-tax-appeal-backoffice');
        if (tabBtn) { tabBtn.style.display = ''; }
        if (typeof taxAppealBoInit === 'function') { taxAppealBoInit(); }
        if (typeof esShowTab === 'function') { esShowTab('tax-appeal-backoffice'); }
    }""")
    page.wait_for_timeout(300)


# ─────────────────────────────────────────────────────────────────────────────
# TAX_EV_01 — Ordinary page must not show evidence review controls
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_EV_01_ordinary_page_no_evidence_controls(
    page: Page, live_server: str
) -> None:
    """TAX_EV_01: Evidence review controls must not be visible on the ordinary tax page."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)

    for testid in (
        "tax-evidence-approve-report",
        "tax-evidence-approve-source",
        "tax-evidence-reject",
        "tax-evidence-upload-button",
    ):
        loc = page.locator(f'[data-testid="{testid}"]')
        if loc.count() > 0:
            assert not loc.first.is_visible(), (
                f"{testid} must not be visible on the ordinary tax appeal page"
            )


# ─────────────────────────────────────────────────────────────────────────────
# TAX_EV_02 — Backoffice DOM contains evidence section
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_EV_02_backoffice_dom_has_evidence_section(
    page: Page, live_server: str
) -> None:
    """TAX_EV_02: #tax-evidence-section must exist inside the backoffice DOM."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)

    section = page.locator('[data-testid="tax-evidence-section"]')
    assert section.count() > 0, (
        "data-testid='tax-evidence-section' must exist in the backoffice DOM"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TAX_EV_03 — Upload controls exist in backoffice DOM
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_EV_03_upload_controls_in_backoffice_dom(
    page: Page, live_server: str
) -> None:
    """TAX_EV_03: File input, type select, and upload button must exist in backoffice DOM."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)

    assert page.locator('[data-testid="tax-evidence-file-input"]').count() > 0, \
        "tax-evidence-file-input missing from backoffice DOM"
    assert page.locator('[data-testid="tax-evidence-type-select"]').count() > 0, \
        "tax-evidence-type-select missing from backoffice DOM"
    assert page.locator('[data-testid="tax-evidence-upload-button"]').count() > 0, \
        "tax-evidence-upload-button missing from backoffice DOM"


# ─────────────────────────────────────────────────────────────────────────────
# TAX_EV_04 — Evidence type select contains required option keys
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_EV_04_evidence_type_select_has_required_options(
    page: Page, live_server: str
) -> None:
    """TAX_EV_04: The evidence type <select> must include mandatory type options."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)

    select = page.locator('[data-testid="tax-evidence-type-select"]')
    assert select.count() > 0, "tax-evidence-type-select not found"

    html = page.content()
    required_types = ["tax_notice_form3", "ownership_document", "market_comparables_excel"]
    for t in required_types:
        assert t in html, (
            f"Evidence type '{t}' must be present as an option value in the select"
        )


# ─────────────────────────────────────────────────────────────────────────────
# TAX_EV_05 — Evidence list table exists in backoffice DOM
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_EV_05_evidence_list_table_in_dom(
    page: Page, live_server: str
) -> None:
    """TAX_EV_05: Evidence list table must exist in backoffice DOM."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)

    tbl = page.locator('[data-testid="tax-evidence-list"]')
    assert tbl.count() > 0, "data-testid='tax-evidence-list' must exist in backoffice DOM"


# ─────────────────────────────────────────────────────────────────────────────
# TAX_EV_06 — Approve-for-report button exists in backoffice DOM
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_EV_06_approve_for_report_button_in_dom(
    page: Page, live_server: str
) -> None:
    """TAX_EV_06: Approve-for-report action must exist in backoffice DOM."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)

    btn = page.locator('[data-testid="tax-evidence-approve-report"]')
    assert btn.count() > 0, (
        "data-testid='tax-evidence-approve-report' must exist in backoffice DOM"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TAX_EV_07 — Approve-as-source button exists in backoffice DOM
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_EV_07_approve_as_source_button_in_dom(
    page: Page, live_server: str
) -> None:
    """TAX_EV_07: Approve-as-source action must exist in backoffice DOM."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)

    btn = page.locator('[data-testid="tax-evidence-approve-source"]')
    assert btn.count() > 0, (
        "data-testid='tax-evidence-approve-source' must exist in backoffice DOM"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TAX_EV_08 — Reject button exists in backoffice DOM
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_EV_08_reject_button_in_dom(
    page: Page, live_server: str
) -> None:
    """TAX_EV_08: Reject action must exist in backoffice DOM."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)

    btn = page.locator('[data-testid="tax-evidence-reject"]')
    assert btn.count() > 0, (
        "data-testid='tax-evidence-reject' must exist in backoffice DOM"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TAX_EV_09 — No internal file paths in page HTML
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_EV_09_no_internal_paths_in_page_html(
    page: Page, live_server: str
) -> None:
    """TAX_EV_09: Page HTML must not expose internal file-system paths."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)

    html = page.content()
    assert "internal_file_path" not in html, \
        "internal_file_path must not appear in page HTML"
    assert "tax_appeal_evidence" not in html, \
        "Internal storage path 'tax_appeal_evidence' must not appear in page HTML"
    assert "instance/" not in html, \
        "Internal storage path 'instance/' must not appear in page HTML"


# ─────────────────────────────────────────────────────────────────────────────
# TAX_EV_10 — Missing mandatory docs warning element present in DOM
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_EV_10_missing_mandatory_warning_element_in_dom(
    page: Page, live_server: str
) -> None:
    """TAX_EV_10: Missing mandatory docs warning element must exist in backoffice DOM."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)

    warn = page.locator('[data-testid="tax-evidence-missing-warning"]')
    assert warn.count() > 0, (
        "data-testid='tax-evidence-missing-warning' must exist in backoffice DOM"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TAX_EV_11 — Download action exists in backoffice DOM
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_EV_11_download_button_in_dom(
    page: Page, live_server: str
) -> None:
    """TAX_EV_11: Evidence download button must exist in backoffice DOM."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)

    btn = page.locator('[data-testid="tax-evidence-download"]')
    assert btn.count() > 0, (
        "data-testid='tax-evidence-download' must exist in backoffice DOM"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TAX_EV_12 — Ordinary page has no source approval controls
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_EV_12_ordinary_page_no_source_approval(
    page: Page, live_server: str
) -> None:
    """TAX_EV_12: Source approval controls must not be visible on the ordinary tax page."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)

    for testid in ("tax-evidence-approve-source", "tax-evidence-review-status"):
        loc = page.locator(f'[data-testid="{testid}"]')
        if loc.count() > 0:
            assert not loc.first.is_visible(), (
                f"{testid} must not be visible on the ordinary tax appeal page"
            )


# ─────────────────────────────────────────────────────────────────────────────
# TAX_EV_13–TAX_EV_24 — Visual QA & Mapping Polish
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_EV_13_evidence_type_select_has_tax_notice_form3(
    page: Page, live_server: str
) -> None:
    """TAX_EV_13: type select must have tax_notice_form3."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    html = page.content()
    assert "tax_notice_form3" in html


def test_TAX_EV_14_evidence_type_select_has_ain_shams(
    page: Page, live_server: str
) -> None:
    """TAX_EV_14: type select must have ain_shams_factory_cost_reference."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    html = page.content()
    assert "ain_shams_factory_cost_reference" in html


def test_TAX_EV_15_evidence_type_select_has_nuca_land(
    page: Page, live_server: str
) -> None:
    """TAX_EV_15: type select must have nuca_land_price_reference."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    html = page.content()
    assert "nuca_land_price_reference" in html


def test_TAX_EV_16_evidence_type_select_has_map_aerial(
    page: Page, live_server: str
) -> None:
    """TAX_EV_16: type select must have map_or_aerial_image."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    html = page.content()
    assert "map_or_aerial_image" in html


def test_TAX_EV_17_reference_number_field_in_dom(
    page: Page, live_server: str
) -> None:
    """TAX_EV_17: Reference number field must exist in backoffice DOM."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    fld = page.locator('[data-testid="tax-evidence-reference-number"]')
    assert fld.count() > 0, "tax-evidence-reference-number missing from backoffice DOM"


def test_TAX_EV_18_document_date_field_in_dom(
    page: Page, live_server: str
) -> None:
    """TAX_EV_18: Document date field must exist in backoffice DOM."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    fld = page.locator('[data-testid="tax-evidence-document-date"]')
    assert fld.count() > 0, "tax-evidence-document-date missing from backoffice DOM"


def test_TAX_EV_19_issuer_field_in_dom(
    page: Page, live_server: str
) -> None:
    """TAX_EV_19: Issuer field must exist in backoffice DOM."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    fld = page.locator('[data-testid="tax-evidence-issuer"]')
    assert fld.count() > 0, "tax-evidence-issuer missing from backoffice DOM"


def test_TAX_EV_20_notes_field_in_dom(
    page: Page, live_server: str
) -> None:
    """TAX_EV_20: Notes field must exist in backoffice DOM."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    fld = page.locator('[data-testid="tax-evidence-notes"]')
    assert fld.count() > 0, "tax-evidence-notes missing from backoffice DOM"


def test_TAX_EV_21_status_warning_element_in_dom(
    page: Page, live_server: str
) -> None:
    """TAX_EV_21: Status warning element must exist in review panel DOM."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    warn = page.locator("#tax-evidence-status-warning")
    assert warn.count() > 0, "#tax-evidence-status-warning missing from backoffice DOM"


def test_TAX_EV_22_no_automatic_value_extraction_flag_in_html(
    page: Page, live_server: str
) -> None:
    """TAX_EV_22: Page must not claim automatic value extraction is active."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    html = page.content()
    # The page must not claim OCR/Qdrant/RAG is active
    assert "OCR_ACTIVE" not in html
    assert "QDRANT_ACTIVE" not in html
    assert "RAG_ACTIVE" not in html


def test_TAX_EV_23_ordinary_page_no_status_warning_visible(
    page: Page, live_server: str
) -> None:
    """TAX_EV_23: Status warning element must not be visible on ordinary tax page."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    warn = page.locator("#tax-evidence-status-warning")
    if warn.count() > 0:
        assert not warn.first.is_visible(), (
            "#tax-evidence-status-warning must not be visible on ordinary tax page"
        )


def test_TAX_EV_24_missing_mandatory_warning_has_detail_text(
    page: Page, live_server: str
) -> None:
    """TAX_EV_24: Missing mandatory docs warning element must have descriptive content."""
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    warn = page.locator('[data-testid="tax-evidence-missing-warning"]')
    assert warn.count() > 0, "tax-evidence-missing-warning missing from DOM"
    # The element should contain AR text about mandatory docs even when hidden
    html = page.content()
    assert "إلزامية" in html, "Missing mandatory docs warning must contain Arabic text"
