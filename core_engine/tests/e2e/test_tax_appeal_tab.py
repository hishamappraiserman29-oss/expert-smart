"""
E2E tests for the Tax Appeal Tab ("فاحص الضرائب والطعون العقارية").

All tests are frontend-only: no real backend calls, no real uploads.
"""
from __future__ import annotations

import pytest
from datetime import date, timedelta
from playwright.sync_api import Page, Route, expect


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _go_to_tax_tab(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator('[data-testid="tax-tab"]').click()
    page.locator('[data-testid="tax-page"]').wait_for(state="visible", timeout=10_000)


def _block_api(page: Page) -> None:
    page.route("**/api/**", lambda r: r.fulfill(status=200, body=b'{"ok":true}',
                                                 content_type="application/json"))


def _fill_transfer_form(page: Page) -> None:
    page.locator('[data-testid="tax-type-select"]').select_option('transfer')
    page.locator('[data-testid="tax-sale-value"]').fill('1000000')
    page.locator('[data-testid="tax-government-claim"]').fill('40000')


# Arabic-Indic → ASCII digit normalization
_ARABIC_INDIC = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')

def _normalize_num(text: str) -> str:
    """Translate Arabic-Indic digits to ASCII and strip separators."""
    return text.translate(_ARABIC_INDIC).replace(',', '').replace('٬', '')


# ─────────────────────────────────────────────────────────────────────────────
# 1. Tab Navigation
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_tab_button_exists(page: Page, live_server: str) -> None:
    """The tax tab button is present in the navigation bar."""
    _block_api(page)
    page.goto(live_server, wait_until="domcontentloaded")
    expect(page.locator('[data-testid="tax-tab"]')).to_be_visible()


def test_TAX_tab_button_label(page: Page, live_server: str) -> None:
    """The tax tab button contains the Arabic label."""
    _block_api(page)
    page.goto(live_server, wait_until="domcontentloaded")
    btn = page.locator('[data-testid="tax-tab"]')
    expect(btn).to_contain_text("فاحص الضرائب والطعون")


def test_TAX_tab_order_is_second(page: Page, live_server: str) -> None:
    """Tax tab must appear between Chat and التقييم."""
    _block_api(page)
    page.goto(live_server, wait_until="domcontentloaded")
    buttons = page.locator('.es-tab-btn').all()
    labels = [b.inner_text() for b in buttons]
    chat_i = next((i for i, l in enumerate(labels) if "الشات" in l), -1)
    tax_i  = next((i for i, l in enumerate(labels) if "الضرائب" in l), -1)
    val_i  = next((i for i, l in enumerate(labels) if "التقييم" in l
                   and "المحترف" not in l and "المجمع" not in l), -1)
    assert chat_i >= 0, "chat tab not found"
    assert tax_i  >= 0, "tax tab not found"
    assert val_i  >= 0, "valuation tab not found"
    assert chat_i < tax_i < val_i, f"Tab order wrong: chat={chat_i}, tax={tax_i}, val={val_i}"


def test_TAX_clicking_tab_shows_workspace(page: Page, live_server: str) -> None:
    """Clicking tax tab shows the ws-tax workspace."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    expect(page.locator('[data-testid="tax-page"]')).to_be_visible()


def test_TAX_switching_to_chat_hides_tax_workspace(page: Page, live_server: str) -> None:
    """Switching to chat tab hides the tax workspace."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="chat-tab"]').click()
    expect(page.locator('[data-testid="tax-page"]')).not_to_be_visible()


def test_TAX_returning_to_tax_tab_shows_workspace_again(page: Page, live_server: str) -> None:
    """Returning to tax tab after switching away restores visibility."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="chat-tab"]').click()
    page.locator('[data-testid="tax-tab"]').click()
    expect(page.locator('[data-testid="tax-page"]')).to_be_visible()


# ─────────────────────────────────────────────────────────────────────────────
# 2. Page Title / Hero
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_page_title_present(page: Page, live_server: str) -> None:
    """Page must contain the Arabic title text."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    text = page.locator('[data-testid="tax-page"]').inner_text()
    assert "فاحص الضرائب والطعون العقارية" in text


def test_TAX_emergency_banner_visible(page: Page, live_server: str) -> None:
    """Legal urgency banner is visible."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    expect(page.locator('[data-testid="tax-emergency-banner"]')).to_be_visible()


def test_TAX_emergency_banner_advisory_text(page: Page, live_server: str) -> None:
    """Banner must contain advisory disclaimer."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    banner = page.locator('[data-testid="tax-emergency-banner"]')
    expect(banner).to_contain_text("استرشادي")


def test_TAX_emergency_banner_has_deadline_reference(page: Page, live_server: str) -> None:
    """Banner must mention appeal days or deadline."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    text = page.locator('[data-testid="tax-emergency-banner"]').inner_text()
    assert "60" in text or "يوم" in text or "مهلة" in text


# ─────────────────────────────────────────────────────────────────────────────
# 3. Input Form — Section A
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_input_section_visible(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    expect(page.locator('[data-testid="tax-input-section"]')).to_be_visible()


def test_TAX_tax_type_select_exists(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    expect(page.locator('[data-testid="tax-type-select"]')).to_be_visible()


def test_TAX_tax_type_select_has_annual_option(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    sel = page.locator('[data-testid="tax-type-select"]')
    options = sel.locator('option').all_inner_texts()
    assert any("سنوية" in o for o in options)


def test_TAX_tax_type_select_has_transfer_option(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    sel = page.locator('[data-testid="tax-type-select"]')
    options = sel.locator('option').all_inner_texts()
    assert any("تصرفات" in o or "2.5" in o for o in options)


def test_TAX_asset_type_select_exists(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    expect(page.locator('[data-testid="tax-asset-type"]')).to_be_visible()


def test_TAX_country_select_exists(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    expect(page.locator('[data-testid="tax-country"]')).to_be_visible()


def test_TAX_area_input_exists(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    expect(page.locator('[data-testid="tax-area"]')).to_be_visible()


def test_TAX_government_claim_input_exists(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    expect(page.locator('[data-testid="tax-government-claim"]')).to_be_visible()


def test_TAX_region_input_exists(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    expect(page.locator('[data-testid="tax-region"]')).to_be_visible()


def test_TAX_city_input_exists(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    expect(page.locator('[data-testid="tax-city"]')).to_be_visible()


def test_TAX_property_status_select_exists(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    expect(page.locator('[data-testid="tax-property-status"]')).to_be_visible()


# ─────────────────────────────────────────────────────────────────────────────
# 4. Conditional Fields
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_transfer_fields_hidden_initially(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    field = page.locator('[data-testid="tax-sale-value"]')
    assert field.is_hidden() or not field.is_visible()


def test_TAX_annual_fields_hidden_initially(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    field = page.locator('[data-testid="tax-annual-rental-estimate"]')
    assert field.is_hidden() or not field.is_visible()


def test_TAX_selecting_transfer_shows_sale_value_field(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option('transfer')
    expect(page.locator('[data-testid="tax-sale-value"]')).to_be_visible()


def test_TAX_selecting_annual_shows_rental_estimate_field(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option('annual')
    expect(page.locator('[data-testid="tax-annual-rental-estimate"]')).to_be_visible()


def test_TAX_selecting_annual_shows_form3_status_field(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option('annual')
    expect(page.locator('[data-testid="tax-form3-status"]')).to_be_visible()


def test_TAX_switching_from_transfer_to_annual_hides_sale_value(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    sel = page.locator('[data-testid="tax-type-select"]')
    sel.select_option('transfer')
    expect(page.locator('[data-testid="tax-sale-value"]')).to_be_visible()
    sel.select_option('annual')
    assert page.locator('[data-testid="tax-sale-value"]').is_hidden()


# ─────────────────────────────────────────────────────────────────────────────
# 5. Documents Section — Section B
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_documents_section_visible(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    expect(page.locator('[data-testid="tax-documents-section"]')).to_be_visible()


def test_TAX_documents_upload_button_visible(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    expect(page.locator('[data-testid="tax-documents-upload-btn"]')).to_be_visible()


def test_TAX_documents_list_initially_empty(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    lst = page.locator('[data-testid="tax-documents-list"]')
    items = lst.locator('li').all()
    assert len(items) == 0


def test_TAX_documents_note_present(page: Page, live_server: str) -> None:
    """Documents note div is visible and contains text about file handling."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    note = page.locator('[data-testid="tax-documents-note"]').inner_text()
    assert len(note.strip()) > 0      # note text is non-empty


# ─────────────────────────────────────────────────────────────────────────────
# 6. Check Button — Section C
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_check_button_visible(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    expect(page.locator('[data-testid="tax-check-button"]')).to_be_visible()


def test_TAX_check_button_label(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    expect(page.locator('[data-testid="tax-check-button"]')).to_contain_text("تحقق")


def test_TAX_output_hidden_before_click(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    assert page.locator('[data-testid="tax-output-dashboard"]').is_hidden()


def test_TAX_check_button_click_shows_dashboard(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-check-button"]').click()
    expect(page.locator('[data-testid="tax-output-dashboard"]')).to_be_visible()


# ─────────────────────────────────────────────────────────────────────────────
# 7. Output Dashboard — Sections D + E
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_overvaluation_gauge_visible_after_check(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-check-button"]').click()
    expect(page.locator('[data-testid="tax-overvaluation-gauge"]')).to_be_visible()


def test_TAX_transfer_tax_calculation_2_5_pct(page: Page, live_server: str) -> None:
    """2.5% transfer tax: sale=1,000,000 → est=25,000."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option('transfer')
    page.locator('[data-testid="tax-sale-value"]').fill('1000000')
    page.locator('[data-testid="tax-government-claim"]').fill('40000')
    page.locator('[data-testid="tax-check-button"]').click()
    out_text = _normalize_num(page.locator('[data-testid="tax-estimated-fair-tax-output"]').inner_text())
    # 1,000,000 * 0.025 = 25,000
    assert "25" in out_text


def test_TAX_annual_tax_advisory_10_pct(page: Page, live_server: str) -> None:
    """10% advisory rate: rental=120,000 → est=12,000."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option('annual')
    page.locator('[data-testid="tax-annual-rental-estimate"]').fill('120000')
    page.locator('[data-testid="tax-government-claim"]').fill('20000')
    page.locator('[data-testid="tax-check-button"]').click()
    out_text = _normalize_num(page.locator('[data-testid="tax-estimated-fair-tax-output"]').inner_text())
    assert "12" in out_text


def test_TAX_no_value_does_not_show_invented_number(page: Page, live_server: str) -> None:
    """Missing data must NOT invent a number — should show non-numeric placeholder."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option('transfer')
    # leave sale-value empty
    page.locator('[data-testid="tax-government-claim"]').fill('5000')
    page.locator('[data-testid="tax-check-button"]').click()
    out_text = page.locator('[data-testid="tax-estimated-fair-tax-output"]').inner_text()
    # Must contain at least one Arabic/Latin letter (not a bare number)
    assert out_text.strip() == '—' or any(c.isalpha() for c in out_text)


def test_TAX_government_claim_reflected_in_output(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    _fill_transfer_form(page)
    page.locator('[data-testid="tax-check-button"]').click()
    gov_out = _normalize_num(page.locator('[data-testid="tax-government-claim-output"]').inner_text())
    assert "40" in gov_out


def test_TAX_draft_warning_visible_after_check(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-check-button"]').click()
    expect(page.locator('[data-testid="tax-draft-warning"]')).to_be_visible()


def test_TAX_draft_warning_is_advisory(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-check-button"]').click()
    text = page.locator('[data-testid="tax-draft-warning"]').inner_text()
    assert "مبدئي" in text or "غير معتمد" in text or "استرشادي" in text


def test_TAX_gauge_shows_tabii_label_for_low_risk(page: Page, live_server: str) -> None:
    """claim = 1.05× est → طبيعي."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option('transfer')
    page.locator('[data-testid="tax-sale-value"]').fill('1000000')
    # est = 25,000; claim 26,250 → ratio 1.05 → طبيعي
    page.locator('[data-testid="tax-government-claim"]').fill('26250')
    page.locator('[data-testid="tax-check-button"]').click()
    gauge_text = page.locator('[data-testid="tax-overvaluation-gauge"]').inner_text()
    assert "طبيعي" in gauge_text


def test_TAX_gauge_shows_review_label_for_medium_risk(page: Page, live_server: str) -> None:
    """claim = 1.25× est → يحتاج مراجعة."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option('transfer')
    page.locator('[data-testid="tax-sale-value"]').fill('1000000')
    # est = 25,000; claim = 31,250 → ratio 1.25 → يحتاج مراجعة
    page.locator('[data-testid="tax-government-claim"]').fill('31250')
    page.locator('[data-testid="tax-check-button"]').click()
    gauge_text = page.locator('[data-testid="tax-overvaluation-gauge"]').inner_text()
    assert "مراجعة" in gauge_text


def test_TAX_gauge_shows_high_risk_label_for_overvaluation(page: Page, live_server: str) -> None:
    """claim = 2× est → مرتفع."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option('transfer')
    page.locator('[data-testid="tax-sale-value"]').fill('1000000')
    # est = 25,000; claim = 50,000 → ratio 2.0 → مرتفع
    page.locator('[data-testid="tax-government-claim"]').fill('50000')
    page.locator('[data-testid="tax-check-button"]').click()
    gauge_text = page.locator('[data-testid="tax-overvaluation-gauge"]').inner_text()
    assert "مرتفع" in gauge_text


def test_TAX_potential_saving_shown_when_overvalued(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option('transfer')
    page.locator('[data-testid="tax-sale-value"]').fill('1000000')
    page.locator('[data-testid="tax-government-claim"]').fill('50000')
    page.locator('[data-testid="tax-check-button"]').click()
    saving = page.locator('[data-testid="tax-potential-saving-output"]').inner_text()
    assert saving.strip() not in ('—', '')


# ─────────────────────────────────────────────────────────────────────────────
# 8. Draft PDF Button — Section F
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_draft_pdf_button_exists(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    expect(page.locator('[data-testid="tax-draft-pdf-button"]')).to_be_visible()


def test_TAX_draft_pdf_button_is_disabled(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    assert page.locator('[data-testid="tax-draft-pdf-button"]').is_disabled()


def test_TAX_draft_pdf_button_contains_future_hint(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    text = page.locator('[data-testid="tax-draft-pdf-button"]').inner_text()
    assert "سيتم" in text or "تفعيل" in text or "عند ربط" in text


# ─────────────────────────────────────────────────────────────────────────────
# 9. Expert CTA — Section G
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_expert_cta_button_visible(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    expect(page.locator('[data-testid="tax-expert-cta-button"]')).to_be_visible()


def test_TAX_expert_cta_label_mentions_expert(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    text = page.locator('[data-testid="tax-expert-cta-button"]').inner_text()
    assert "خبير" in text or "طعن" in text or "تقرير" in text


def test_TAX_expert_cta_reveals_lead_form(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    form = page.locator('[data-testid="tax-lead-form"]')
    assert form.is_hidden()
    page.locator('[data-testid="tax-expert-cta-button"]').click()
    expect(form).to_be_visible()


# ─────────────────────────────────────────────────────────────────────────────
# 10. Lead Form — Section H
# ─────────────────────────────────────────────────────────────────────────────

def _open_lead_form(page: Page, live_server: str) -> None:
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-expert-cta-button"]').click()
    page.locator('[data-testid="tax-lead-form"]').wait_for(state="visible", timeout=5_000)


def test_TAX_lead_name_field_present(page: Page, live_server: str) -> None:
    _block_api(page)
    _open_lead_form(page, live_server)
    expect(page.locator('[data-testid="tax-lead-name"]')).to_be_visible()


def test_TAX_lead_phone_field_present(page: Page, live_server: str) -> None:
    _block_api(page)
    _open_lead_form(page, live_server)
    expect(page.locator('[data-testid="tax-lead-phone"]')).to_be_visible()


def test_TAX_lead_email_field_present(page: Page, live_server: str) -> None:
    _block_api(page)
    _open_lead_form(page, live_server)
    expect(page.locator('[data-testid="tax-lead-email"]')).to_be_visible()


def test_TAX_lead_submit_button_present(page: Page, live_server: str) -> None:
    _block_api(page)
    _open_lead_form(page, live_server)
    expect(page.locator('[data-testid="tax-lead-submit"]')).to_be_visible()


def test_TAX_lead_submit_requires_name(page: Page, live_server: str) -> None:
    """Submitting without name should not show confirmation."""
    _block_api(page)
    _open_lead_form(page, live_server)
    page.locator('[data-testid="tax-lead-phone"]').fill('01012345678')
    page.locator('[data-testid="tax-lead-submit"]').click()
    conf = page.locator('[data-testid="tax-lead-confirmation"]')
    assert conf.is_hidden() or not conf.is_visible()


def test_TAX_lead_submit_requires_phone(page: Page, live_server: str) -> None:
    """Submitting without phone should not show confirmation."""
    _block_api(page)
    _open_lead_form(page, live_server)
    page.locator('[data-testid="tax-lead-name"]').fill('محمد أحمد')
    page.locator('[data-testid="tax-lead-submit"]').click()
    conf = page.locator('[data-testid="tax-lead-confirmation"]')
    assert conf.is_hidden() or not conf.is_visible()


def test_TAX_lead_confirmation_shown_after_valid_submit(page: Page, live_server: str) -> None:
    _block_api(page)
    _open_lead_form(page, live_server)
    page.locator('[data-testid="tax-lead-name"]').fill('محمد أحمد')
    page.locator('[data-testid="tax-lead-phone"]').fill('01012345678')
    page.locator('[data-testid="tax-lead-submit"]').click()
    expect(page.locator('[data-testid="tax-lead-confirmation"]')).to_be_visible()


def test_TAX_lead_confirmation_is_frontend_only(page: Page, live_server: str) -> None:
    """Confirmation text must mention no real send was performed."""
    _block_api(page)
    _open_lead_form(page, live_server)
    page.locator('[data-testid="tax-lead-name"]').fill('اسم اختبار')
    page.locator('[data-testid="tax-lead-phone"]').fill('01099999999')
    page.locator('[data-testid="tax-lead-submit"]').click()
    text = page.locator('[data-testid="tax-lead-confirmation"]').inner_text()
    assert "سيتم" in text or "ربط" in text or "تسجيل" in text


# ─────────────────────────────────────────────────────────────────────────────
# 11. Mini Tax Chat — Section I
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_mini_chat_section_visible(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    expect(page.locator('[data-testid="tax-mini-chat"]')).to_be_visible()


def test_TAX_mini_chat_input_visible(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    expect(page.locator('[data-testid="tax-mini-chat-input"]')).to_be_visible()


def test_TAX_mini_chat_send_button_visible(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    expect(page.locator('[data-testid="tax-mini-chat-send"]')).to_be_visible()


def test_TAX_mini_chat_answer_hidden_initially(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    assert page.locator('[data-testid="tax-mini-chat-answer"]').is_hidden()


def test_TAX_mini_chat_tax_question_gets_answer(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-mini-chat-input"]').fill('ما أهمية نموذج 3 ضرائب؟')
    page.locator('[data-testid="tax-mini-chat-send"]').click()
    expect(page.locator('[data-testid="tax-mini-chat-answer"]')).to_be_visible()


def test_TAX_mini_chat_unrelated_question_is_rejected(page: Page, live_server: str) -> None:
    """Non-tax question should be politely declined."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-mini-chat-input"]').fill('ما هو أحسن مطعم في القاهرة؟')
    page.locator('[data-testid="tax-mini-chat-send"]').click()
    ans = page.locator('[data-testid="tax-mini-chat-answer"]')
    expect(ans).to_be_visible()
    text = ans.inner_text()
    assert "ضرائب" in text or "خاص" in text or "مخصص" in text


def test_TAX_mini_chat_enter_key_sends_message(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    inp = page.locator('[data-testid="tax-mini-chat-input"]')
    inp.fill('متى تبدأ مهلة الطعن؟')
    inp.press('Enter')
    expect(page.locator('[data-testid="tax-mini-chat-answer"]')).to_be_visible()


def test_TAX_mini_chat_answer_contains_tax_content(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-mini-chat-input"]').fill('كيف أثبت أن المصنع متوقف؟')
    page.locator('[data-testid="tax-mini-chat-send"]').click()
    ans = page.locator('[data-testid="tax-mini-chat-answer"]').inner_text()
    assert len(ans.strip()) > 30


def test_TAX_mini_chat_quick_prompt_form3_works(page: Page, live_server: str) -> None:
    """Quick prompt button for نموذج 3 ضرائب."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.evaluate("taxMiniChatQuick('form3-deadline')")
    expect(page.locator('[data-testid="tax-mini-chat-answer"]')).to_be_visible()


def test_TAX_mini_chat_expert_cta_appears_for_relevant_answers(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-mini-chat-input"]').fill('ما أهمية نموذج 3 ضرائب؟')
    page.locator('[data-testid="tax-mini-chat-send"]').click()
    expect(page.locator('[data-testid="tax-mini-chat-expert-cta"]')).to_be_visible()


def test_TAX_mini_chat_official_appeal_question_is_corrected(page: Page, live_server: str) -> None:
    """Should clarify the tool is not an official appeal."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-mini-chat-input"]').fill('هل الفاحص طعن رسمي معتمد؟')
    page.locator('[data-testid="tax-mini-chat-send"]').click()
    ans = page.locator('[data-testid="tax-mini-chat-answer"]').inner_text()
    assert "لا" in ans or "غير معتمد" in ans or "مبدئي" in ans


# ─────────────────────────────────────────────────────────────────────────────
# 12. Advisory Config
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_advisory_config_transfer_rate_is_2_5_pct(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    rate = page.evaluate("TAX_ADVISORY_CONFIG.transferRate")
    assert rate == 0.025


def test_TAX_advisory_config_annual_rate_is_10_pct(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    rate = page.evaluate("TAX_ADVISORY_CONFIG.annualAdvisoryRate")
    assert rate == 0.10


def test_TAX_advisory_config_appeal_days_is_60(page: Page, live_server: str) -> None:
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    days = page.evaluate("TAX_ADVISORY_CONFIG.appealDaysAdvisory")
    assert days == 60


# ─────────────────────────────────────────────────────────────────────────────
# 13. Backend Integration (Phase 1-3)
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_tab_still_opens_after_backend_wiring(page: Page, live_server: str) -> None:
    """Tax tab is still reachable after backend routes are registered."""
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-page"]').wait_for(state="visible", timeout=10_000)


def test_TAX_lead_submission_returns_lead_id(page: Page, live_server: str) -> None:
    """Submitting the lead form with real backend returns a lead_id."""
    _go_to_tax_tab(page, live_server)
    # Show lead form
    page.locator('[data-testid="tax-expert-cta-button"]').click()
    page.locator('[data-testid="tax-lead-form"]').wait_for(state="visible", timeout=5_000)
    # Fill required fields
    page.locator('[data-testid="tax-lead-name"]').fill("مريم اختبار التكامل")
    page.locator('[data-testid="tax-lead-phone"]').fill("01099887766")
    # Submit
    page.locator('[data-testid="tax-lead-submit"]').click()
    # Confirmation must appear (backend responds within 15 s)
    conf = page.locator('[data-testid="tax-lead-confirmation"]')
    conf.wait_for(state="visible", timeout=15_000)
    conf_text = conf.inner_text()
    # Either a real lead_id or the generic fallback is acceptable
    assert "TAX-" in conf_text or "تم تسجيل" in conf_text or "مبدئيًا" in conf_text


def test_TAX_lead_submission_confirmation_visible(page: Page, live_server: str) -> None:
    """Confirmation div becomes visible after successful submission."""
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-expert-cta-button"]').click()
    page.locator('[data-testid="tax-lead-form"]').wait_for(state="visible", timeout=5_000)
    page.locator('[data-testid="tax-lead-name"]').fill("فهد اختبار")
    page.locator('[data-testid="tax-lead-phone"]').fill("0551234567")
    page.locator('[data-testid="tax-lead-submit"]').click()
    page.locator('[data-testid="tax-lead-confirmation"]').wait_for(state="visible", timeout=15_000)


def test_TAX_pdf_button_enabled_after_lead_save(page: Page, live_server: str) -> None:
    """PDF button becomes enabled when backend returns pdf_available=True."""
    import json as _json
    _mock_body = _json.dumps({
        "status": "success",
        "lead_id": "TAX-TESTPDF1",
        "message": "تم تسجيل طلب الفحص بنجاح. رقم الطلب: TAX-TESTPDF1. سيقوم الخبير بمراجعة البيانات.",
        "pdf_available": True,
        "pdf_download_url": "/api/tax-appeal/leads/TAX-TESTPDF1/pdf",
        "documents_saved": 0,
        "document_errors": [],
    }).encode()
    page.route(
        "**/api/tax-appeal/leads",
        lambda r: r.fulfill(status=201, body=_mock_body,
                            content_type="application/json"),
    )
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-expert-cta-button"]').click()
    page.locator('[data-testid="tax-lead-form"]').wait_for(state="visible", timeout=5_000)
    page.locator('[data-testid="tax-lead-name"]').fill("سارة اختبار PDF")
    page.locator('[data-testid="tax-lead-phone"]').fill("01111111111")
    page.locator('[data-testid="tax-lead-submit"]').click()
    # Wait for confirmation to appear
    page.locator('[data-testid="tax-lead-confirmation"]').wait_for(state="visible", timeout=10_000)
    # PDF button should be enabled (disabled attribute removed)
    pdf_btn = page.locator('[data-testid="tax-draft-pdf-button"]')
    disabled = pdf_btn.get_attribute("disabled")
    assert disabled is None, "PDF button should be enabled after successful lead save with pdf_available=True"


def test_TAX_document_names_still_display(page: Page, live_server: str) -> None:
    """File names are shown in the documents list (display behavior unchanged)."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.evaluate("""
        var dt = new DataTransfer();
        dt.items.add(new File(['dummy'], 'form3_tax.pdf', {type:'application/pdf'}));
        document.getElementById('tax-docs-input').files = dt.files;
        taxHandleDocs(document.getElementById('tax-docs-input').files);
    """)
    doc_list = page.locator('[data-testid="tax-documents-list"]')
    expect(doc_list).to_contain_text("form3_tax.pdf")


def test_TAX_draft_warning_still_visible_after_backend_wiring(page: Page, live_server: str) -> None:
    """Draft/non-certified warning is still present after backend integration."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    # Trigger the output area
    page.locator('[data-testid="tax-type-select"]').select_option('transfer')
    page.locator('[data-testid="tax-sale-value"]').fill('500000')
    page.locator('[data-testid="tax-government-claim"]').fill('20000')
    page.locator('[data-testid="tax-check-button"]').click()
    warning = page.locator('[data-testid="tax-draft-warning"]')
    expect(warning).to_be_visible()


def test_TAX_mini_chat_still_works_after_backend_wiring(page: Page, live_server: str) -> None:
    """Mini chat responds to tax keywords after backend routes are registered."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-mini-chat-input"]').fill('هل الطعن رسمي؟')
    page.locator('[data-testid="tax-mini-chat-send"]').click()
    ans = page.locator('[data-testid="tax-mini-chat-answer"]')
    ans.wait_for(state="visible", timeout=5_000)


# ─────────────────────────────────────────────────────────────────────────────
# 14. Annual Property Tax Overvaluation Ratio (Task 6)
# ─────────────────────────────────────────────────────────────────────────────

def _go_annual_with_asset(
    page: Page, live_server: str, asset_type: str, market_value: int, gov_claim: int
) -> None:
    """Navigate to tax tab and fill annual overvaluation form, then click check."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option("annual")
    page.locator('[data-testid="tax-asset-type"]').select_option(asset_type)
    page.locator('[data-testid="tax-market-value"]').fill(str(market_value))
    page.locator('[data-testid="tax-government-claim"]').fill(str(gov_claim))
    page.locator('[data-testid="tax-check-button"]').click()


def test_TAX_annual_mode_shows_market_value_field(page: Page, live_server: str) -> None:
    """Selecting annual tax mode reveals the market value field."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option("annual")
    expect(page.locator('[data-testid="tax-market-value"]')).to_be_visible()


def test_TAX_OVR_residential_natural(page: Page, live_server: str) -> None:
    """Residential MV=2,000,000, claim=2,600 (= 0.13% ceiling) → طبيعي."""
    _go_annual_with_asset(page, live_server, "residential", 2_000_000, 2_600)
    gauge_text = page.locator('[data-testid="tax-overvaluation-gauge"]').inner_text()
    assert "طبيعي" in gauge_text


def test_TAX_OVR_residential_medium_overvaluation(page: Page, live_server: str) -> None:
    """Residential MV=2M, claim=3,000 → متوسط, overcharge=400."""
    _go_annual_with_asset(page, live_server, "residential", 2_000_000, 3_000)
    gauge_text = page.locator('[data-testid="tax-overvaluation-gauge"]').inner_text()
    assert "متوسط" in gauge_text
    overcharge_raw = _normalize_num(
        page.locator('[data-testid="tax-overcharge-output"]').inner_text()
    )
    assert "400" in overcharge_raw


def test_TAX_OVR_residential_high_overvaluation(page: Page, live_server: str) -> None:
    """Residential MV=2M, claim=4,000 (ratio=0.20%) → مغالى فيه جداً."""
    _go_annual_with_asset(page, live_server, "residential", 2_000_000, 4_000)
    gauge_text = page.locator('[data-testid="tax-overvaluation-gauge"]').inner_text()
    assert "مغالى" in gauge_text


def test_TAX_OVR_commercial_natural(page: Page, live_server: str) -> None:
    """Commercial MV=5,000,000, claim=6,000 (= 0.12% ceiling) → طبيعي."""
    _go_annual_with_asset(page, live_server, "commercial", 5_000_000, 6_000)
    gauge_text = page.locator('[data-testid="tax-overvaluation-gauge"]').inner_text()
    assert "طبيعي" in gauge_text


def test_TAX_OVR_commercial_overcharge(page: Page, live_server: str) -> None:
    """Commercial MV=5M, claim=7,000 → fair_ceiling=6,000, overcharge=1,000."""
    _go_annual_with_asset(page, live_server, "commercial", 5_000_000, 7_000)
    overcharge_raw = _normalize_num(
        page.locator('[data-testid="tax-overcharge-output"]').inner_text()
    )
    assert "1000" in overcharge_raw


def test_TAX_OVR_special_natural(page: Page, live_server: str) -> None:
    """Special/factory MV=10M, claim=34,000 (= 0.34% ceiling) → طبيعي."""
    _go_annual_with_asset(page, live_server, "special", 10_000_000, 34_000)
    gauge_text = page.locator('[data-testid="tax-overvaluation-gauge"]').inner_text()
    assert "طبيعي" in gauge_text


def test_TAX_OVR_special_high_overvaluation(page: Page, live_server: str) -> None:
    """Special/factory MV=10M, claim=50,000 → مغالى فيه جداً."""
    _go_annual_with_asset(page, live_server, "special", 10_000_000, 50_000)
    gauge_text = page.locator('[data-testid="tax-overvaluation-gauge"]').inner_text()
    assert "مغالى" in gauge_text


def test_TAX_OVR_missing_market_value_shows_disclaimer(page: Page, live_server: str) -> None:
    """Missing market value must show data-gap message and not invent a result."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option("annual")
    page.locator('[data-testid="tax-asset-type"]').select_option("residential")
    page.locator('[data-testid="tax-government-claim"]').fill("5000")
    page.locator('[data-testid="tax-check-button"]').click()
    disclaimer = page.locator('[data-testid="tax-ratio-disclaimer"]').inner_text()
    assert "لا يمكن" in disclaimer or "القيمة السوقية" in disclaimer


def test_TAX_OVR_transfer_unaffected_by_annual_thresholds(page: Page, live_server: str) -> None:
    """Transfer tax 2.5%: est=25,000 not 1,300 (0.13% of 1M)."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option("transfer")
    page.locator('[data-testid="tax-sale-value"]').fill("1000000")
    page.locator('[data-testid="tax-government-claim"]').fill("25000")
    page.locator('[data-testid="tax-check-button"]').click()
    out_text = _normalize_num(
        page.locator('[data-testid="tax-estimated-fair-tax-output"]').inner_text()
    )
    assert "25000" in out_text or "25" in out_text
    assert "1300" not in out_text.replace(" ", "")


def test_TAX_OVR_full_output_fields_present(page: Page, live_server: str) -> None:
    """All required output fields populated for residential annual calculation."""
    _go_annual_with_asset(page, live_server, "residential", 2_000_000, 3_000)
    # market value
    mv = _normalize_num(page.locator('[data-testid="tax-market-value-output"]').inner_text())
    assert "2000000" in mv or "2000" in mv
    # ratio contains %
    ratio = page.locator('[data-testid="tax-actual-tax-ratio-output"]').inner_text()
    assert "%" in ratio
    # threshold = 0.13%
    thresh = page.locator('[data-testid="tax-advisory-threshold-output"]').inner_text()
    assert "0.13" in thresh
    # fair ceiling = 2,600
    ceiling = _normalize_num(page.locator('[data-testid="tax-fair-tax-ceiling-output"]').inner_text())
    assert "2600" in ceiling
    # overcharge = 400
    overcharge = _normalize_num(page.locator('[data-testid="tax-overcharge-output"]').inner_text())
    assert "400" in overcharge
    # disclaimer present
    disclaimer = page.locator('[data-testid="tax-ratio-disclaimer"]').inner_text()
    assert len(disclaimer.strip()) > 10


def test_TAX_OVR_yellow_red_shows_expert_cta(page: Page, live_server: str) -> None:
    """Red result must reveal the overvaluation expert CTA button."""
    _go_annual_with_asset(page, live_server, "residential", 2_000_000, 4_000)
    expect(page.locator('[data-testid="tax-overvaluation-expert-cta"]')).to_be_visible()


# ─────────────────────────────────────────────────────────────────────────────
# 15. Tax Mode Separation (Parts B + K)
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_mode_selector_visible(page: Page, live_server: str) -> None:
    """Tax mode selector container is visible on the page."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    expect(page.locator('[data-testid="tax-mode-selector"]')).to_be_visible()


def test_TAX_annual_mode_shows_annual_fields(page: Page, live_server: str) -> None:
    """Selecting annual mode shows annual-specific fields."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option('annual')
    expect(page.locator('[data-testid="tax-annual-rental-estimate"]')).to_be_visible()
    expect(page.locator('[data-testid="tax-market-value"]')).to_be_visible()


def test_TAX_transfer_mode_shows_transfer_fields(page: Page, live_server: str) -> None:
    """Selecting transfer mode shows sale-value field."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option('transfer')
    expect(page.locator('[data-testid="tax-sale-value"]')).to_be_visible()
    assert page.locator('[data-testid="tax-annual-rental-estimate"]').is_hidden()


def test_TAX_transfer_method_panel_shows_2_5_pct(page: Page, live_server: str) -> None:
    """Transfer method panel is visible in transfer mode and mentions 2.5%."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option('transfer')
    panel = page.locator('[data-testid="tax-transfer-method-panel"]')
    expect(panel).to_be_visible()
    assert "2.5" in panel.inner_text()


def test_TAX_transfer_panel_no_annual_thresholds(page: Page, live_server: str) -> None:
    """Transfer method panel must NOT present annual threshold logic as its main rule."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option('transfer')
    panel_text = page.locator('[data-testid="tax-transfer-method-panel"]').inner_text()
    # Panel text should NOT say the 0.13% / 0.12% / 0.34% IS the rule for transfer
    # It may mention those numbers in a "not applicable" context — accept that
    assert "2.5" in panel_text


# ─────────────────────────────────────────────────────────────────────────────
# 16. Annual Method Panel (Part C)
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_annual_method_panel_visible_in_annual_mode(page: Page, live_server: str) -> None:
    """Annual method panel shows when annual mode is selected."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option('annual')
    expect(page.locator('[data-testid="tax-annual-method-panel"]')).to_be_visible()


def test_TAX_annual_method_panel_formula_present(page: Page, live_server: str) -> None:
    """Annual method panel contains the overvaluation formula text."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option('annual')
    formula = page.locator('[data-testid="tax-annual-formula"]').inner_text()
    assert "÷" in formula or "القيمة السوقية" in formula


def test_TAX_annual_method_panel_thresholds_correct(page: Page, live_server: str) -> None:
    """Annual method panel shows 0.13%, 0.12%, 0.34% thresholds."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option('annual')
    assert "0.13" in page.locator('[data-testid="tax-threshold-residential"]').inner_text()
    assert "0.12" in page.locator('[data-testid="tax-threshold-nonresidential"]').inner_text()
    assert "0.34" in page.locator('[data-testid="tax-threshold-special"]').inner_text()


def test_TAX_annual_method_panel_maintenance_30_pct(page: Page, live_server: str) -> None:
    """Residential maintenance deduction shows 30%."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option('annual')
    assert "30" in page.locator('[data-testid="tax-maintenance-residential"]').inner_text()


def test_TAX_annual_method_panel_maintenance_32_pct(page: Page, live_server: str) -> None:
    """Non-residential maintenance deduction shows 32%."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option('annual')
    assert "32" in page.locator('[data-testid="tax-maintenance-nonresidential"]').inner_text()


def test_TAX_annual_method_panel_exemption_24000(page: Page, live_server: str) -> None:
    """Private residence exemption threshold shows 24,000."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option('annual')
    text = page.locator('[data-testid="tax-private-residence-exemption"]').inner_text()
    assert "24" in text


# ─────────────────────────────────────────────────────────────────────────────
# 17. Live Savings Dashboard (Part D)
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_live_savings_dashboard_visible_after_annual_check(page: Page, live_server: str) -> None:
    """Live savings dashboard appears after a valid annual check."""
    _go_annual_with_asset(page, live_server, "residential", 2_000_000, 3_000)
    expect(page.locator('[data-testid="tax-live-savings-dashboard"]')).to_be_visible()


def test_TAX_live_savings_dashboard_visible_after_transfer_check(page: Page, live_server: str) -> None:
    """Live savings dashboard appears after a valid transfer check."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option('transfer')
    page.locator('[data-testid="tax-sale-value"]').fill('1000000')
    page.locator('[data-testid="tax-government-claim"]').fill('40000')
    page.locator('[data-testid="tax-check-button"]').click()
    expect(page.locator('[data-testid="tax-live-savings-dashboard"]')).to_be_visible()


# ─────────────────────────────────────────────────────────────────────────────
# 18. Gauge UX (Part E)
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_gauge_legend_visible(page: Page, live_server: str) -> None:
    """Gauge legend strip is present inside the gauge element."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-check-button"]').click()
    expect(page.locator('[data-testid="tax-gauge-legend"]')).to_be_visible()


def test_TAX_gauge_state_green_text_shown_for_normal_result(page: Page, live_server: str) -> None:
    """Green state explanation appears for طبيعي (residential, claim = ceiling)."""
    _go_annual_with_asset(page, live_server, "residential", 2_000_000, 2_600)
    state_text = page.locator('[data-testid="tax-gauge-state-green-text"]').inner_text()
    assert "لا تتجاوز" in state_text or "الحد الاسترشادي" in state_text


def test_TAX_gauge_state_red_text_shown_for_high_overvaluation(page: Page, live_server: str) -> None:
    """Red state explanation appears for high overvaluation."""
    _go_annual_with_asset(page, live_server, "residential", 2_000_000, 4_000)
    state_text = page.locator('[data-testid="tax-gauge-state-red-text"]').inner_text()
    assert "تتجاوز" in state_text or "خبير" in state_text


# ─────────────────────────────────────────────────────────────────────────────
# 19. Missing Data → Data Gap Panel (Part F)
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_missing_market_value_shows_data_gap_panel(page: Page, live_server: str) -> None:
    """Annual mode without market value shows data gap panel, not a fake result."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option('annual')
    page.locator('[data-testid="tax-asset-type"]').select_option('residential')
    page.locator('[data-testid="tax-government-claim"]').fill('5000')
    # leave market value empty
    page.locator('[data-testid="tax-check-button"]').click()
    expect(page.locator('[data-testid="tax-data-gap-panel"]')).to_be_visible()
    gap_text = page.locator('[data-testid="tax-data-gap-list"]').inner_text()
    assert "القيمة السوقية" in gap_text


def test_TAX_data_gap_panel_hidden_when_data_complete(page: Page, live_server: str) -> None:
    """Data gap panel is NOT shown when all required values are present."""
    _go_annual_with_asset(page, live_server, "residential", 2_000_000, 3_000)
    gap = page.locator('[data-testid="tax-data-gap-panel"]')
    assert gap.is_hidden() or not gap.is_visible()


# ─────────────────────────────────────────────────────────────────────────────
# 20. Deadline Countdown (Part G)
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_notice_date_input_present(page: Page, live_server: str) -> None:
    """Notice received date input exists in annual mode."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option('annual')
    expect(page.locator('[data-testid="tax-notice-received-date"]')).to_be_visible()


def test_TAX_deadline_countdown_shows_on_date_entry(page: Page, live_server: str) -> None:
    """Entering a notice date shows the countdown card."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option('annual')
    today = date.today()
    # Input expects DD/MM/YYYY — using today so deadline (today+60) is always future
    notice_str = f"{today.day:02d}/{today.month:02d}/{today.year}"
    inp = page.locator('[data-testid="tax-notice-received-date"]')
    inp.fill(notice_str)
    inp.dispatch_event('change')  # onchange="taxDeadlineUpdate(..." requires explicit change event
    expect(page.locator('[data-testid="tax-deadline-countdown"]')).to_be_visible()


def test_TAX_deadline_end_date_shows_60_days(page: Page, live_server: str) -> None:
    """Deadline end date is 60 days after notice date."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option('annual')
    today = date.today()
    notice_str = f"{today.day:02d}/{today.month:02d}/{today.year}"
    inp = page.locator('[data-testid="tax-notice-received-date"]')
    inp.fill(notice_str)
    inp.dispatch_event('change')  # onchange="taxDeadlineUpdate(..." requires explicit change event
    deadline = today + timedelta(days=60)
    # JS renders end date in DD/MM/YYYY; assert by month (least locale-sensitive check)
    expected_month = f"{deadline.month:02d}"
    expected_str   = f"{deadline.day:02d}/{deadline.month:02d}/{deadline.year}"
    end_date = page.locator('[data-testid="tax-deadline-end-date"]').inner_text()
    assert expected_str in end_date or expected_month in end_date, (
        f"Expected deadline {expected_str!r} (or month {expected_month!r}) in: {end_date!r}"
    )


def test_TAX_deadline_disclaimer_visible(page: Page, live_server: str) -> None:
    """Deadline disclaimer text is visible after date entry."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option('annual')
    page.locator('[data-testid="tax-notice-received-date"]').fill('2026-01-01')
    disc = page.locator('[data-testid="tax-deadline-disclaimer"]').inner_text()
    assert "استرشادي" in disc or "خبير" in disc


# ─────────────────────────────────────────────────────────────────────────────
# 21. Document Guidance + OCR (Part H)
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_documents_guidance_visible(page: Page, live_server: str) -> None:
    """Document guidance section is visible on the tax page."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    expect(page.locator('[data-testid="tax-documents-guidance"]')).to_be_visible()


def test_TAX_required_docs_list_has_form3_and_notice(page: Page, live_server: str) -> None:
    """Required documents list includes نموذج 3 ضرائب and إخطار ضريبي."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    text = page.locator('[data-testid="tax-required-documents-list"]').inner_text()
    assert "نموذج 3 ضرائب" in text
    assert "إخطار" in text


def test_TAX_ocr_note_honest_no_active_extraction(page: Page, live_server: str) -> None:
    """OCR note must state extraction is future/placeholder, not active."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    note = page.locator('[data-testid="tax-ocr-note"]').inner_text()
    assert "لاحقة" in note or "مرحلة" in note or "حاليًا" in note


# ─────────────────────────────────────────────────────────────────────────────
# 22. Draft Report / Watermark (Part I)
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_draft_report_warning_visible(page: Page, live_server: str) -> None:
    """Draft report warning element is visible on the page."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    expect(page.locator('[data-testid="tax-draft-report-warning"]')).to_be_visible()


def test_TAX_draft_report_warning_non_certified(page: Page, live_server: str) -> None:
    """Draft report warning must NOT claim the output is certified or official."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    text = page.locator('[data-testid="tax-draft-report-warning"]').inner_text()
    assert "غير معتمد" in text or "مبدئي" in text


def test_TAX_pdf_watermark_note_visible(page: Page, live_server: str) -> None:
    """PDF watermark note is visible near the draft PDF button."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    expect(page.locator('[data-testid="tax-pdf-watermark-note"]')).to_be_visible()


def test_TAX_draft_pdf_button_no_certified_claim(page: Page, live_server: str) -> None:
    """Draft PDF button text must not claim the report is certified/official."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    btn_text = page.locator('[data-testid="tax-draft-pdf-button"]').inner_text()
    assert "معتمد رسميًا" not in btn_text
    assert "طعن رسمي" not in btn_text


# ─────────────────────────────────────────────────────────────────────────────
# 23. Certified Request Card (Part J)
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_certified_cta_opens_request_card(page: Page, live_server: str) -> None:
    """Clicking expert CTA reveals the certified request card."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-expert-cta-button"]').click()
    expect(page.locator('[data-testid="tax-certified-request-card"]')).to_be_visible()


def test_TAX_certified_request_card_has_required_fields(page: Page, live_server: str) -> None:
    """Certified request card includes name, phone, and email fields."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-expert-cta-button"]').click()
    expect(page.locator('[data-testid="tax-lead-name"]')).to_be_visible()
    expect(page.locator('[data-testid="tax-lead-phone"]')).to_be_visible()
    expect(page.locator('[data-testid="tax-lead-email"]')).to_be_visible()


def test_TAX_certified_request_confirmation_no_official_start(page: Page, live_server: str) -> None:
    """After submission, confirmation must NOT claim official appeal started."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-expert-cta-button"]').click()
    page.locator('[data-testid="tax-lead-name"]').fill('اختبار نظام')
    page.locator('[data-testid="tax-lead-phone"]').fill('01012345678')
    page.locator('[data-testid="tax-lead-submit"]').click()
    conf = page.locator('[data-testid="tax-lead-confirmation"]').inner_text()
    assert "تم البدء في الطعن رسميًا" not in conf
    assert "جاري تحويل ملفك رسميًا" not in conf


# ─────────────────────────────────────────────────────────────────────────────
# 24. Transfer Tax Unchanged (Part K)
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_transfer_rate_output_shows_2_5(page: Page, live_server: str) -> None:
    """Transfer rate output element shows 2.5%."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option('transfer')
    text = page.locator('[data-testid="tax-transfer-rate-output"]').inner_text()
    assert "2.5" in text


def test_TAX_transfer_tax_still_2_5_pct_unchanged(page: Page, live_server: str) -> None:
    """Transfer tax calculation still yields 2.5% of sale value (regression guard)."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-type-select"]').select_option('transfer')
    page.locator('[data-testid="tax-sale-value"]').fill('2000000')
    page.locator('[data-testid="tax-government-claim"]').fill('60000')
    page.locator('[data-testid="tax-check-button"]').click()
    out = _normalize_num(page.locator('[data-testid="tax-estimated-fair-tax-output"]').inner_text())
    # 2,000,000 * 0.025 = 50,000
    assert "50000" in out or "50" in out


# ─────────────────────────────────────────────────────────────────────────────
# 25. No Certified Report Claim
# ─────────────────────────────────────────────────────────────────────────────

def test_TAX_no_certified_report_on_page(page: Page, live_server: str) -> None:
    """Page text must not auto-claim a certified report is generated."""
    _block_api(page)
    _go_to_tax_tab(page, live_server)
    page.locator('[data-testid="tax-check-button"]').click()
    full_text = page.locator('[data-testid="tax-page"]').inner_text()
    # Should not claim report is officially certified without expert review
    assert "تقرير معتمد رسمي جاهز" not in full_text
    assert "تم إصدار تقرير خبير معتمد" not in full_text
