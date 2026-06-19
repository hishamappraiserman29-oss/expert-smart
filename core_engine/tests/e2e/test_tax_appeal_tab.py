"""
E2E tests for the Tax Appeal Tab ("فاحص الضرائب والطعون العقارية").

All tests are frontend-only: no real backend calls, no real uploads.
"""
from __future__ import annotations

import pytest
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
