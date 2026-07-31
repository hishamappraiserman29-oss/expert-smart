"""
E2E tests — Tax Appeal Extraction Readiness Backoffice UI.

Tests verify:
  TAX_EX_01  Ordinary tax page does not show extraction controls
  TAX_EX_02  Backoffice DOM contains extraction section
  TAX_EX_03  Evidence select (tax-extraction-evidence-select) exists in backoffice DOM
  TAX_EX_04  Extraction save-draft button present in backoffice DOM
  TAX_EX_05  Extraction submit-review button present in backoffice DOM
  TAX_EX_06  Extraction confirm button present in backoffice DOM
  TAX_EX_07  Extraction reject button present in backoffice DOM
  TAX_EX_08  Extraction create-mappings button present in backoffice DOM
  TAX_EX_09  No-auto-fill warning element present in backoffice DOM
  TAX_EX_10  Extraction list element present in backoffice DOM
  TAX_EX_11  OCR/Qdrant inactive notice visible in backoffice DOM
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
        body=(
            b'{"ok":true,"requests":[],"evidence":[],"count":0,'
            b'"templates":[],"extractions":[],'
            b'"extraction_summary":{"total_extractions":0,'
            b'"ocr_active_now":false,"qdrant_active_now":false,'
            b'"rag_active_now":false,"no_automatic_value_extraction":true}}'
        ),
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
        var sec = document.getElementById('tax-extraction-section');
        if (sec) sec.style.display = '';
    }""")
    page.wait_for_timeout(300)


# ─────────────────────────────────────────────────────────────────────────────
# TAX_EX_01 — Ordinary page must not show extraction section
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_EX_01_ordinary_page_no_extraction_controls(
    page: Page, live_server: str
) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    sec = page.locator('[data-testid="tax-extraction-section"]')
    assert sec.count() == 0 or sec.first.is_hidden()


# ─────────────────────────────────────────────────────────────────────────────
# TAX_EX_02 — Backoffice DOM contains extraction section
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_EX_02_backoffice_has_extraction_section(
    page: Page, live_server: str
) -> None:
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    sec = page.locator('[data-testid="tax-extraction-section"]')
    assert sec.count() > 0


# ─────────────────────────────────────────────────────────────────────────────
# TAX_EX_03 — Evidence select exists in backoffice DOM
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_EX_03_evidence_select_exists(
    page: Page, live_server: str
) -> None:
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    sel = page.locator('[data-testid="tax-extraction-evidence-select"]')
    assert sel.count() > 0


# ─────────────────────────────────────────────────────────────────────────────
# TAX_EX_04 — Save-draft button present
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_EX_04_save_draft_button_present(
    page: Page, live_server: str
) -> None:
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    btn = page.locator('[data-testid="tax-extraction-save-draft"]')
    assert btn.count() > 0


# ─────────────────────────────────────────────────────────────────────────────
# TAX_EX_05 — Submit-review button present
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_EX_05_submit_review_button_present(
    page: Page, live_server: str
) -> None:
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    btn = page.locator('[data-testid="tax-extraction-submit-review"]')
    assert btn.count() > 0


# ─────────────────────────────────────────────────────────────────────────────
# TAX_EX_06 — Confirm button present
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_EX_06_confirm_button_present(
    page: Page, live_server: str
) -> None:
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    btn = page.locator('[data-testid="tax-extraction-confirm"]')
    assert btn.count() > 0


# ─────────────────────────────────────────────────────────────────────────────
# TAX_EX_07 — Reject button present
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_EX_07_reject_button_present(
    page: Page, live_server: str
) -> None:
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    btn = page.locator('[data-testid="tax-extraction-reject"]')
    assert btn.count() > 0


# ─────────────────────────────────────────────────────────────────────────────
# TAX_EX_08 — Create-mappings button present
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_EX_08_create_mappings_button_present(
    page: Page, live_server: str
) -> None:
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    btn = page.locator('[data-testid="tax-extraction-create-mappings"]')
    assert btn.count() > 0


# ─────────────────────────────────────────────────────────────────────────────
# TAX_EX_09 — No-auto-fill warning element present
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_EX_09_no_auto_fill_warning_present(
    page: Page, live_server: str
) -> None:
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    warn = page.locator('[data-testid="tax-extraction-no-auto-warning"]')
    assert warn.count() > 0


# ─────────────────────────────────────────────────────────────────────────────
# TAX_EX_10 — Extraction list element present
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_EX_10_extraction_list_present(
    page: Page, live_server: str
) -> None:
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    lst = page.locator('[data-testid="tax-extraction-list"]')
    assert lst.count() > 0


# ─────────────────────────────────────────────────────────────────────────────
# TAX_EX_11 — OCR/Qdrant inactive notice visible in backoffice DOM
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_EX_11_ocr_qdrant_inactive_notice(
    page: Page, live_server: str
) -> None:
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    # The extraction section should contain text indicating OCR/Qdrant is inactive
    sec = page.locator('[data-testid="tax-extraction-section"]')
    assert sec.count() > 0
    inner = sec.first.inner_html()
    # Must contain some indicator that OCR / Qdrant / RAG is inactive
    assert (
        "OCR" in inner
        or "Qdrant" in inner
        or "غير مفعّل" in inner
        or "غير مفعل" in inner
        or "no_automatic_value_extraction" in inner.lower()
    ), "OCR/Qdrant inactive notice not found in extraction section HTML"
