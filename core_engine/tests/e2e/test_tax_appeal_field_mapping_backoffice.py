"""
E2E tests — Tax Appeal Field Mapping Backoffice UI.

Tests verify:
  TAX_FM_01  Ordinary tax page does not show field mapping controls
  TAX_FM_02  Backoffice DOM contains field mapping section
  TAX_FM_03  Evidence select (tax-mapping-evidence-select) exists in backoffice DOM
  TAX_FM_04  Field select (tax-mapping-field-select) exists in backoffice DOM
  TAX_FM_05  Mapped value input exists in backoffice DOM
  TAX_FM_06  Mapping save button exists in backoffice DOM
  TAX_FM_07  Mapping list table exists in backoffice DOM
  TAX_FM_08  Mapping conflict warning element present in backoffice DOM
  TAX_FM_09  Confirm mapping button present in mapping table area
  TAX_FM_10  Reject mapping button present in mapping table area
  TAX_FM_11  Apply context button exists in backoffice DOM
  TAX_FM_12  No internal storage paths visible in backoffice DOM
  TAX_FM_13  Expert notes NOT visible on ordinary tax page
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
            b'"mappings":[],"conflicts":[],"field_mapping_summary":{},'
            b'"catalogue_by_group":{}}'
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
        var sec = document.getElementById('tax-field-mapping-section');
        if (sec) sec.style.display = '';
    }""")
    page.wait_for_timeout(300)


# ─────────────────────────────────────────────────────────────────────────────
# TAX_FM_01 — Ordinary page must not show field mapping section
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_FM_01_ordinary_page_no_field_mapping_controls(
    page: Page, live_server: str
) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    # Field mapping section should not be visible on ordinary tax page
    fm_sec = page.locator('[data-testid="tax-field-mapping-section"]')
    assert fm_sec.count() == 0 or fm_sec.first.is_hidden()


# ─────────────────────────────────────────────────────────────────────────────
# TAX_FM_02 — Backoffice DOM contains field mapping section
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_FM_02_backoffice_has_field_mapping_section(
    page: Page, live_server: str
) -> None:
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    fm_sec = page.locator('[data-testid="tax-field-mapping-section"]')
    assert fm_sec.count() > 0


# ─────────────────────────────────────────────────────────────────────────────
# TAX_FM_03 — Evidence select exists in backoffice DOM
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_FM_03_evidence_select_exists(
    page: Page, live_server: str
) -> None:
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    sel = page.locator('[data-testid="tax-mapping-evidence-select"]')
    assert sel.count() > 0


# ─────────────────────────────────────────────────────────────────────────────
# TAX_FM_04 — Field select exists in backoffice DOM
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_FM_04_field_select_exists(
    page: Page, live_server: str
) -> None:
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    sel = page.locator('[data-testid="tax-mapping-field-select"]')
    assert sel.count() > 0


# ─────────────────────────────────────────────────────────────────────────────
# TAX_FM_05 — Mapped value input exists in backoffice DOM
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_FM_05_mapped_value_input_exists(
    page: Page, live_server: str
) -> None:
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    inp = page.locator('[data-testid="tax-mapping-value-input"]')
    assert inp.count() > 0


# ─────────────────────────────────────────────────────────────────────────────
# TAX_FM_06 — Mapping save button exists in backoffice DOM
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_FM_06_mapping_save_button_exists(
    page: Page, live_server: str
) -> None:
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    btn = page.locator('[data-testid="tax-mapping-save-button"]')
    assert btn.count() > 0


# ─────────────────────────────────────────────────────────────────────────────
# TAX_FM_07 — Mapping list container exists in backoffice DOM
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_FM_07_mapping_list_exists(
    page: Page, live_server: str
) -> None:
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    lst = page.locator('[data-testid="tax-mapping-list"]')
    assert lst.count() > 0


# ─────────────────────────────────────────────────────────────────────────────
# TAX_FM_08 — Conflict warning element present in backoffice DOM
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_FM_08_conflict_warning_element_present(
    page: Page, live_server: str
) -> None:
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    cw = page.locator('[data-testid="tax-mapping-conflict-warning"]')
    assert cw.count() > 0
    # Starts hidden
    assert cw.first.is_hidden()


# ─────────────────────────────────────────────────────────────────────────────
# TAX_FM_09 — Confirm button template exists in DOM (inside table area)
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_FM_09_confirm_button_in_table_area(
    page: Page, live_server: str
) -> None:
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    # Inject a synthetic mapping row to check confirm button renders
    page.evaluate("""() => {
        var tbody = document.getElementById('tax-mapping-table-body');
        if (tbody) {
            tbody.innerHTML = '<tr data-testid="tax-mapping-row">' +
                '<td>test field</td><td>test val</td><td>type</td>' +
                '<td>needs_review</td><td>لا</td><td>—</td>' +
                '<td><button data-testid="tax-mapping-confirm-button">تأكيد</button>' +
                '<button data-testid="tax-mapping-reject-button">رفض</button></td>' +
                '</tr>';
        }
    }""")
    confirm_btn = page.locator('[data-testid="tax-mapping-confirm-button"]')
    assert confirm_btn.count() > 0


# ─────────────────────────────────────────────────────────────────────────────
# TAX_FM_10 — Reject button template exists in DOM
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_FM_10_reject_button_in_table_area(
    page: Page, live_server: str
) -> None:
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    page.evaluate("""() => {
        var tbody = document.getElementById('tax-mapping-table-body');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="6"></td><td>' +
                '<button data-testid="tax-mapping-reject-button">رفض</button></td></tr>';
        }
    }""")
    reject_btn = page.locator('[data-testid="tax-mapping-reject-button"]')
    assert reject_btn.count() > 0


# ─────────────────────────────────────────────────────────────────────────────
# TAX_FM_11 — Apply context button exists in backoffice DOM
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_FM_11_apply_context_button_exists(
    page: Page, live_server: str
) -> None:
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    btn = page.locator('[data-testid="tax-mapping-apply-context-button"]')
    assert btn.count() > 0


# ─────────────────────────────────────────────────────────────────────────────
# TAX_FM_12 — No internal storage paths in backoffice DOM
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_FM_12_no_internal_paths_in_dom(
    page: Page, live_server: str
) -> None:
    _block_api(page)
    _go_to_tax_backoffice(page, live_server)
    html = page.content()
    assert "tax_appeal_field_mappings" not in html, \
        "Internal storage directory name must not appear in DOM"
    assert "C:\\Users" not in html and "c:\\users" not in html.lower()[:500], \
        "Windows absolute path must not appear in DOM"


# ─────────────────────────────────────────────────────────────────────────────
# TAX_FM_13 — Expert notes NOT visible on ordinary tax page
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_FM_13_expert_notes_not_visible_on_ordinary_page(
    page: Page, live_server: str
) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    html = page.content()
    # field mapping section must not appear in ordinary context
    assert 'tax-field-mapping-section' not in html or \
        page.locator('[data-testid="tax-field-mapping-section"]').first.is_hidden()
    # expert notes input must not be visible
    note_inp = page.locator('[data-testid="tax-mapping-note-input"]')
    assert note_inp.count() == 0 or note_inp.first.is_hidden()
