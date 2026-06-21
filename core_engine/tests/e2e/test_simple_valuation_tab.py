"""
E2E tests — Simple Valuation Tab ("التقييم").

Verifies:
  1.  The "التقييم" tab button exists and opens the tab.
  2.  The simple valuation header is visible.
  3.  Basic form fields are visible: location, description, area, property-type, condition.
  4.  Professional controls are NOT in the simple tab
      (asset-type, val-purpose, requirements checklist, purpose integration matrix).
  5.  Composite controls are NOT in the simple tab
      (component table, portfolio, composite workflow).
  6.  Only one report action button is visible ("إصدار تقرير تقييم مبدئي").
  7.  Three-report-choice buttons are NOT visible in the simple tab.
  8.  Clicking the report button shows one draft report output area (with mocked API).
  9.  Draft warning is visible in output.
  10. Expert review CTA is visible in output.
  11. Other tabs still exist (chat / professional / composite).
  12. The chat tab still opens (regression guard).
  13. Professional tab remains accessible.

These tests do NOT require a valid JWT.
"""
from __future__ import annotations

import json
import pytest
from playwright.sync_api import Page, Route, expect


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _go_to_simple_valuation_tab(page: Page, live_server: str) -> None:
    """Navigate to root and click the التقييم tab."""
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator("#es-tab-valuation").click()
    page.locator("[data-testid='simple-valuation-tab']").wait_for(state="visible", timeout=5_000)


def _fill_form_minimum(page: Page) -> None:
    """Fill the minimum required fields so svGenerate() won't alert-and-abort."""
    # Select country Egypt (EG) — triggers geoSync so sv-location gets a value
    page.locator("#geo-country").select_option("EG")
    # Wait for province to become enabled
    page.locator("#geo-province").wait_for(state="attached")
    page.locator("#geo-province").select_option("القاهرة")
    page.locator("#geo-city").select_option("المعادي")

    page.locator("[data-testid='simple-valuation-description']").fill("شقة سكنية في المعادي تشطيب ممتاز")
    page.locator("[data-testid='simple-valuation-area']").fill("120")
    page.locator("[data-testid='simple-valuation-property-type']").select_option("شقة سكنية")
    page.locator("[data-testid='simple-valuation-condition']").select_option("جيدة")


def _mock_valuation_api(page: Page) -> None:
    """Intercept /api/valuation and return a predictable success payload."""
    def _handle(route: Route) -> None:
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "status": "success",
                "market_value": 2_500_000,
                "report_id": "DRAFT-E2E-001",
                "excel_url": None,
            }),
        )
    page.route("**/api/valuation", _handle)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_SV_tab_button_exists(page: Page, live_server: str) -> None:
    """The التقييم tab button is present in the navigation bar."""
    page.goto(live_server, wait_until="domcontentloaded")
    expect(page.locator("#es-tab-valuation")).to_be_visible()


def test_SV_tab_opens(page: Page, live_server: str) -> None:
    """Clicking التقييم tab opens the simple valuation workspace."""
    _go_to_simple_valuation_tab(page, live_server)
    expect(page.locator("[data-testid='simple-valuation-tab']")).to_be_visible()


def test_SV_header_visible(page: Page, live_server: str) -> None:
    """The simple valuation header card is visible with correct title."""
    _go_to_simple_valuation_tab(page, live_server)
    header = page.locator("[data-testid='simple-valuation-header']")
    expect(header).to_be_visible()
    assert "المبسط" in header.inner_text()


def test_SV_form_visible(page: Page, live_server: str) -> None:
    """The simple valuation form container is visible."""
    _go_to_simple_valuation_tab(page, live_server)
    expect(page.locator("[data-testid='simple-valuation-form']")).to_be_visible()


def test_SV_location_field_visible(page: Page, live_server: str) -> None:
    """The geographic scope / location section is visible."""
    _go_to_simple_valuation_tab(page, live_server)
    expect(page.locator("[data-testid='simple-valuation-location']")).to_be_visible()
    expect(page.locator("#geo-country")).to_be_visible()


def test_SV_description_field_visible(page: Page, live_server: str) -> None:
    """Property description textarea is visible."""
    _go_to_simple_valuation_tab(page, live_server)
    expect(page.locator("[data-testid='simple-valuation-description']")).to_be_visible()


def test_SV_area_field_visible(page: Page, live_server: str) -> None:
    """Area input is visible."""
    _go_to_simple_valuation_tab(page, live_server)
    expect(page.locator("[data-testid='simple-valuation-area']")).to_be_visible()


def test_SV_property_type_visible(page: Page, live_server: str) -> None:
    """Simplified property type selector is visible."""
    _go_to_simple_valuation_tab(page, live_server)
    expect(page.locator("[data-testid='simple-valuation-property-type']")).to_be_visible()


def test_SV_condition_field_visible(page: Page, live_server: str) -> None:
    """Property condition selector is visible."""
    _go_to_simple_valuation_tab(page, live_server)
    expect(page.locator("[data-testid='simple-valuation-condition']")).to_be_visible()


def test_SV_no_asset_family_in_simple_tab(page: Page, live_server: str) -> None:
    """Asset Family / أسرة الأصول is NOT visible in the simple valuation tab."""
    _go_to_simple_valuation_tab(page, live_server)
    tab = page.locator("[data-testid='simple-valuation-tab']")
    tab_text = tab.inner_text()
    assert "أسرة الأصول" not in tab_text
    assert "Asset Family" not in tab_text


def test_SV_no_asset_subtype_in_simple_tab(page: Page, live_server: str) -> None:
    """The professional asset-type selector (#asset-type) is NOT visible in the simple tab."""
    _go_to_simple_valuation_tab(page, live_server)
    # The professional asset-type selector should not be in this workspace
    el = page.locator("[data-testid='simple-valuation-tab'] #asset-type")
    expect(el).to_have_count(0)


def test_SV_no_purpose_route_in_simple_tab(page: Page, live_server: str) -> None:
    """Purpose Route / val-purpose professional dropdown is NOT in the simple tab."""
    _go_to_simple_valuation_tab(page, live_server)
    el = page.locator("[data-testid='simple-valuation-tab'] #val-purpose")
    expect(el).to_have_count(0)


def test_SV_no_requirements_checklist_in_simple_tab(page: Page, live_server: str) -> None:
    """Requirements checklist is NOT visible in the simple valuation tab."""
    _go_to_simple_valuation_tab(page, live_server)
    tab_text = page.locator("[data-testid='simple-valuation-tab']").inner_text()
    assert "قائمة المتطلبات" not in tab_text
    assert "requirements-checklist" not in tab_text.lower()


def test_SV_no_purpose_integration_matrix_in_simple_tab(page: Page, live_server: str) -> None:
    """Purpose Integration Matrix is NOT in the simple valuation tab."""
    _go_to_simple_valuation_tab(page, live_server)
    tab_text = page.locator("[data-testid='simple-valuation-tab']").inner_text()
    assert "مصفوفة" not in tab_text


def test_SV_no_component_table_in_simple_tab(page: Page, live_server: str) -> None:
    """Composite component table is NOT in the simple valuation tab."""
    _go_to_simple_valuation_tab(page, live_server)
    el = page.locator("[data-testid='simple-valuation-tab'] [id*='component']")
    expect(el).to_have_count(0)


def test_SV_no_portfolio_composite_in_simple_tab(page: Page, live_server: str) -> None:
    """Portfolio / composite workflow controls are NOT in the simple tab."""
    _go_to_simple_valuation_tab(page, live_server)
    tab_text = page.locator("[data-testid='simple-valuation-tab']").inner_text()
    assert "التقييم المجمع" not in tab_text
    assert "portfolio" not in tab_text.lower()


def test_SV_one_report_action_visible(page: Page, live_server: str) -> None:
    """Exactly one primary report action button is visible with correct label."""
    _go_to_simple_valuation_tab(page, live_server)
    btn = page.locator("[data-testid='simple-valuation-generate']")
    expect(btn).to_be_visible()
    assert "مبدئي" in btn.inner_text()


def test_SV_no_three_report_buttons(page: Page, live_server: str) -> None:
    """Three distinct report-type option buttons are NOT visible in the simple tab."""
    _go_to_simple_valuation_tab(page, live_server)
    tab_text = page.locator("[data-testid='simple-valuation-tab']").inner_text()
    # Professional report labels must not appear as user-facing choices
    assert "تقرير شامل" not in tab_text
    assert "تقرير مختصر" not in tab_text
    assert "تقرير أكاديمي" not in tab_text


def test_SV_clicking_button_shows_draft_output(page: Page, live_server: str) -> None:
    """Clicking the report button shows the draft output area."""
    _mock_valuation_api(page)
    _go_to_simple_valuation_tab(page, live_server)
    _fill_form_minimum(page)

    page.locator("[data-testid='simple-valuation-generate']").click()

    output = page.locator("[data-testid='simple-valuation-output']")
    expect(output).to_be_visible(timeout=8_000)
    assert "مبدئي" in output.inner_text()


def test_SV_draft_warning_visible_after_generate(page: Page, live_server: str) -> None:
    """Draft warning is visible inside the output after generating the report."""
    _mock_valuation_api(page)
    _go_to_simple_valuation_tab(page, live_server)
    _fill_form_minimum(page)
    page.locator("[data-testid='simple-valuation-generate']").click()

    warning = page.locator("[data-testid='simple-valuation-draft-warning']")
    expect(warning).to_be_visible(timeout=8_000)
    text = warning.inner_text()
    assert "مبدئي" in text or "Draft" in text
    assert "غير معتمد" in text


def test_SV_expert_cta_visible_after_generate(page: Page, live_server: str) -> None:
    """Expert review CTA is visible inside the output after generating the report."""
    _mock_valuation_api(page)
    _go_to_simple_valuation_tab(page, live_server)
    _fill_form_minimum(page)
    page.locator("[data-testid='simple-valuation-generate']").click()

    cta = page.locator("[data-testid='simple-valuation-expert-cta']")
    expect(cta).to_be_visible(timeout=8_000)
    assert "مراجعة" in cta.inner_text()


def test_SV_other_tab_chat_exists(page: Page, live_server: str) -> None:
    """The chat tab button is still present."""
    page.goto(live_server, wait_until="domcontentloaded")
    expect(page.locator("[data-testid='chat-tab']")).to_be_visible()


def test_SV_other_tab_professional_exists(page: Page, live_server: str) -> None:
    """The professional valuation tab button is still present."""
    page.goto(live_server, wait_until="domcontentloaded")
    expect(page.locator("#es-tab-professional")).to_be_visible()


def test_SV_other_tab_composite_exists(page: Page, live_server: str) -> None:
    """The composite valuation tab button is still present."""
    page.goto(live_server, wait_until="domcontentloaded")
    expect(page.locator("#es-tab-composite")).to_be_visible()


def test_SV_chat_tab_still_works(page: Page, live_server: str) -> None:
    """Clicking the chat tab after visiting the simple valuation tab still works."""
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='chat-tab']").click()
    expect(page.locator("[data-testid='chat-landing']")).to_be_visible(timeout=5_000)


# ---------------------------------------------------------------------------
# Task-B tests — date, purpose, output policy, enriched output
# ---------------------------------------------------------------------------

def test_SV_date_field_visible(page: Page, live_server: str) -> None:
    """Valuation date field is visible in the form."""
    _go_to_simple_valuation_tab(page, live_server)
    expect(page.locator("[data-testid='simple-valuation-date']")).to_be_visible()


def test_SV_date_field_defaults_to_today(page: Page, live_server: str) -> None:
    """Valuation date field has a non-empty default value (today's date)."""
    _go_to_simple_valuation_tab(page, live_server)
    val = page.locator("[data-testid='simple-valuation-date']").input_value()
    assert val, "Date field should default to today (non-empty)"
    # Must be a valid YYYY-MM-DD pattern
    import re
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", val), f"Unexpected date format: {val}"


def test_SV_date_field_is_type_date(page: Page, live_server: str) -> None:
    """Date field has type=date (native date picker)."""
    _go_to_simple_valuation_tab(page, live_server)
    el = page.locator("[data-testid='simple-valuation-date']")
    assert el.get_attribute("type") == "date"


def test_SV_purpose_badge_visible(page: Page, live_server: str) -> None:
    """Fixed purpose badge is visible in the form."""
    _go_to_simple_valuation_tab(page, live_server)
    expect(page.locator("[data-testid='simple-valuation-purpose']")).to_be_visible()


def test_SV_purpose_badge_shows_market_value(page: Page, live_server: str) -> None:
    """Purpose badge contains the Arabic text القيمة السوقية."""
    _go_to_simple_valuation_tab(page, live_server)
    text = page.locator("[data-testid='simple-valuation-purpose']").inner_text()
    assert "القيمة السوقية" in text


def test_SV_purpose_is_not_an_editable_select(page: Page, live_server: str) -> None:
    """Purpose element does NOT have a <select> child — it is not an editable dropdown."""
    _go_to_simple_valuation_tab(page, live_server)
    # The purpose badge must not be a select itself
    el = page.locator("[data-testid='simple-valuation-purpose']")
    assert el.evaluate("e => e.tagName.toLowerCase()") != "select"
    # And no nested select for purpose
    nested = page.locator("[data-testid='simple-valuation-purpose'] select")
    expect(nested).to_have_count(0)


def test_SV_output_policy_visible(page: Page, live_server: str) -> None:
    """Output policy note is visible in the form (before the generate button)."""
    _go_to_simple_valuation_tab(page, live_server)
    expect(page.locator("[data-testid='simple-valuation-output-policy']")).to_be_visible()


def test_SV_output_policy_mentions_draft(page: Page, live_server: str) -> None:
    """Output policy note mentions draft-only output (مبدئي)."""
    _go_to_simple_valuation_tab(page, live_server)
    text = page.locator("[data-testid='simple-valuation-output-policy']").inner_text()
    assert "مبدئي" in text


def test_SV_output_policy_mentions_excel_internal(page: Page, live_server: str) -> None:
    """Output policy note mentions Excel as internal (Excel داخلي or similar)."""
    _go_to_simple_valuation_tab(page, live_server)
    text = page.locator("[data-testid='simple-valuation-output-policy']").inner_text()
    assert "Excel" in text


def test_SV_output_policy_mentions_pdf_for_user(page: Page, live_server: str) -> None:
    """Output policy note mentions PDF for the ordinary user."""
    _go_to_simple_valuation_tab(page, live_server)
    text = page.locator("[data-testid='simple-valuation-output-policy']").inner_text()
    assert "PDF" in text


def test_SV_output_contains_date(page: Page, live_server: str) -> None:
    """After generating, the valuation date appears in the output table."""
    _mock_valuation_api(page)
    _go_to_simple_valuation_tab(page, live_server)
    _fill_form_minimum(page)

    page.locator("[data-testid='simple-valuation-generate']").click()

    output = page.locator("[data-testid='simple-valuation-output']")
    expect(output).to_be_visible(timeout=8_000)
    assert "تاريخ" in output.inner_text()


def test_SV_output_contains_purpose(page: Page, live_server: str) -> None:
    """After generating, القيمة السوقية appears in the output."""
    _mock_valuation_api(page)
    _go_to_simple_valuation_tab(page, live_server)
    _fill_form_minimum(page)

    page.locator("[data-testid='simple-valuation-generate']").click()

    output = page.locator("[data-testid='simple-valuation-output']")
    expect(output).to_be_visible(timeout=8_000)
    assert "القيمة السوقية" in output.inner_text()


def test_SV_output_contains_description(page: Page, live_server: str) -> None:
    """After generating, the description entered by the user appears in the output."""
    _mock_valuation_api(page)
    _go_to_simple_valuation_tab(page, live_server)
    _fill_form_minimum(page)

    page.locator("[data-testid='simple-valuation-generate']").click()

    output = page.locator("[data-testid='simple-valuation-output']")
    expect(output).to_be_visible(timeout=8_000)
    assert "شقة سكنية في المعادي" in output.inner_text()


def test_SV_output_contains_notes_when_filled(page: Page, live_server: str) -> None:
    """After generating, user-entered notes appear in the output."""
    _mock_valuation_api(page)
    _go_to_simple_valuation_tab(page, live_server)
    _fill_form_minimum(page)
    page.locator("#sv-notes").fill("ملاحظة خاصة للاختبار")

    page.locator("[data-testid='simple-valuation-generate']").click()

    output = page.locator("[data-testid='simple-valuation-output']")
    expect(output).to_be_visible(timeout=8_000)
    assert "ملاحظة خاصة للاختبار" in output.inner_text()


def test_SV_output_omits_notes_row_when_empty(page: Page, live_server: str) -> None:
    """After generating with no notes, the ملاحظات row is NOT in the output."""
    _mock_valuation_api(page)
    _go_to_simple_valuation_tab(page, live_server)
    _fill_form_minimum(page)
    # Ensure notes field is empty
    page.locator("#sv-notes").fill("")

    page.locator("[data-testid='simple-valuation-generate']").click()

    output = page.locator("[data-testid='simple-valuation-output']")
    expect(output).to_be_visible(timeout=8_000)
    # The notes row label should not appear when notes is empty
    table_html = output.locator("table").inner_html()
    assert "ملاحظات:" not in table_html


def test_SV_file_policy_note_visible_in_output(page: Page, live_server: str) -> None:
    """After generating, the file-policy note is visible in the output."""
    _mock_valuation_api(page)
    _go_to_simple_valuation_tab(page, live_server)
    _fill_form_minimum(page)

    page.locator("[data-testid='simple-valuation-generate']").click()

    policy = page.locator("[data-testid='simple-valuation-file-policy']")
    expect(policy).to_be_visible(timeout=8_000)


def test_SV_file_policy_mentions_pdf_and_excel(page: Page, live_server: str) -> None:
    """File-policy note in output mentions both PDF (user copy) and Excel (expert/admin)."""
    _mock_valuation_api(page)
    _go_to_simple_valuation_tab(page, live_server)
    _fill_form_minimum(page)

    page.locator("[data-testid='simple-valuation-generate']").click()

    text = page.locator("[data-testid='simple-valuation-file-policy']").inner_text(timeout=8_000)
    assert "PDF" in text
    assert "Excel" in text


def test_SV_no_direct_excel_download_link_in_output(page: Page, live_server: str) -> None:
    """Even when the API returns an excel_url, no direct Excel download link appears in the output."""
    def _handle_with_excel(route: Route) -> None:
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "status": "success",
                "market_value": 1_800_000,
                "report_id": "DRAFT-XLS-001",
                "excel_url": "/api/reports/DRAFT-XLS-001.xlsx",
            }),
        )
    page.route("**/api/valuation", _handle_with_excel)

    _go_to_simple_valuation_tab(page, live_server)
    _fill_form_minimum(page)

    page.locator("[data-testid='simple-valuation-generate']").click()

    output = page.locator("[data-testid='simple-valuation-output']")
    expect(output).to_be_visible(timeout=8_000)

    # No anchor tag pointing to an xlsx/excel file should be rendered
    excel_links = output.locator("a[href*='.xlsx'], a[href*='excel']")
    expect(excel_links).to_have_count(0)


def test_SV_expert_cta_mentions_expert_review(page: Page, live_server: str) -> None:
    """Expert CTA in output mentions requesting certified review from the expert."""
    _mock_valuation_api(page)
    _go_to_simple_valuation_tab(page, live_server)
    _fill_form_minimum(page)

    page.locator("[data-testid='simple-valuation-generate']").click()

    cta = page.locator("[data-testid='simple-valuation-expert-cta']")
    expect(cta).to_be_visible(timeout=8_000)
    text = cta.inner_text()
    assert "الخبير" in text


# ---------------------------------------------------------------------------
# Task-C tests — certified report request card
# ---------------------------------------------------------------------------

def _generate_draft(page: Page, live_server: str) -> None:
    """Helper: navigate to tab, mock API, fill form, click generate."""
    _mock_valuation_api(page)
    _go_to_simple_valuation_tab(page, live_server)
    _fill_form_minimum(page)
    page.locator("[data-testid='simple-valuation-generate']").click()
    page.locator("[data-testid='simple-valuation-output']").wait_for(state="visible", timeout=8_000)


def test_SV_cert_card_visible_after_generate(page: Page, live_server: str) -> None:
    """After generating the draft report, the certified request card becomes visible."""
    _generate_draft(page, live_server)
    expect(page.locator("[data-testid='simple-valuation-cert-request-card']")).to_be_visible(timeout=5_000)


def test_SV_cert_card_title_contains_request_text(page: Page, live_server: str) -> None:
    """The certified request card title contains the expected Arabic heading."""
    _generate_draft(page, live_server)
    text = page.locator("[data-testid='simple-valuation-cert-request-card']").inner_text(timeout=5_000)
    # Updated title in Task E: "طلب مراجعة واعتماد التقرير من خبير التقييم"
    assert "اعتماد التقرير" in text


def test_SV_cert_delivery_note_visible(page: Page, live_server: str) -> None:
    """The delivery note is visible inside the certified request card."""
    _generate_draft(page, live_server)
    expect(page.locator("[data-testid='simple-cert-delivery-note']")).to_be_visible(timeout=5_000)


def test_SV_cert_delivery_note_mentions_whatsapp(page: Page, live_server: str) -> None:
    """The delivery note mentions WhatsApp as a delivery option."""
    _generate_draft(page, live_server)
    text = page.locator("[data-testid='simple-cert-delivery-note']").inner_text(timeout=5_000)
    assert "واتساب" in text


def test_SV_cert_delivery_note_mentions_email(page: Page, live_server: str) -> None:
    """The delivery note mentions email as a delivery option."""
    _generate_draft(page, live_server)
    text = page.locator("[data-testid='simple-cert-delivery-note']").inner_text(timeout=5_000)
    assert "البريد الإلكتروني" in text


def test_SV_cert_name_field_visible(page: Page, live_server: str) -> None:
    """Name field is visible in the certified request form."""
    _generate_draft(page, live_server)
    expect(page.locator("[data-testid='simple-cert-name']")).to_be_visible(timeout=5_000)


def test_SV_cert_phone_field_visible(page: Page, live_server: str) -> None:
    """Phone/WhatsApp field is visible in the certified request form."""
    _generate_draft(page, live_server)
    expect(page.locator("[data-testid='simple-cert-phone']")).to_be_visible(timeout=5_000)


def test_SV_cert_email_field_visible(page: Page, live_server: str) -> None:
    """Email field is visible in the certified request form."""
    _generate_draft(page, live_server)
    expect(page.locator("[data-testid='simple-cert-email']")).to_be_visible(timeout=5_000)


def test_SV_cert_delivery_method_visible(page: Page, live_server: str) -> None:
    """Delivery method selector is visible in the certified request form."""
    _generate_draft(page, live_server)
    expect(page.locator("[data-testid='simple-cert-delivery-method']")).to_be_visible(timeout=5_000)


def test_SV_cert_delivery_method_options(page: Page, live_server: str) -> None:
    """Delivery method selector has all three options: WhatsApp, Email, Both."""
    _generate_draft(page, live_server)
    select = page.locator("[data-testid='simple-cert-delivery-method']")
    options = select.locator("option").all_inner_texts()
    flat = " | ".join(options)
    assert "واتساب" in flat
    assert "البريد الإلكتروني" in flat
    assert "واتساب والبريد الإلكتروني" in flat


def test_SV_cert_notes_field_visible(page: Page, live_server: str) -> None:
    """Notes/summary field is visible in the certified request form."""
    _generate_draft(page, live_server)
    expect(page.locator("[data-testid='simple-cert-notes']")).to_be_visible(timeout=5_000)


def test_SV_cert_submit_button_visible(page: Page, live_server: str) -> None:
    """Submit button is visible in the certified request form."""
    _generate_draft(page, live_server)
    expect(page.locator("[data-testid='simple-cert-submit']")).to_be_visible(timeout=5_000)


def test_SV_cert_empty_submit_no_confirmation(page: Page, live_server: str) -> None:
    """Submitting with empty fields does NOT show the confirmation div."""
    _generate_draft(page, live_server)
    page.locator("[data-testid='simple-cert-submit']").click()
    confirm = page.locator("[data-testid='simple-cert-confirmation']")
    expect(confirm).to_be_hidden()


def test_SV_cert_submit_with_name_and_phone(page: Page, live_server: str) -> None:
    """Filling name + phone + delivery method then submitting shows confirmation."""
    _generate_draft(page, live_server)
    page.locator("[data-testid='simple-cert-name']").fill("محمد اختبار")
    page.locator("[data-testid='simple-cert-phone']").fill("01012345678")
    page.locator("[data-testid='simple-cert-delivery-method']").select_option("واتساب")
    page.locator("[data-testid='simple-cert-submit']").click()
    confirm = page.locator("[data-testid='simple-cert-confirmation']")
    expect(confirm).to_be_visible(timeout=5_000)


def test_SV_cert_submit_with_name_and_email(page: Page, live_server: str) -> None:
    """Filling name + email + delivery method then submitting shows confirmation."""
    _generate_draft(page, live_server)
    page.locator("[data-testid='simple-cert-name']").fill("أحمد اختبار")
    page.locator("[data-testid='simple-cert-email']").fill("test@example.com")
    page.locator("[data-testid='simple-cert-delivery-method']").select_option("البريد الإلكتروني")
    page.locator("[data-testid='simple-cert-submit']").click()
    confirm = page.locator("[data-testid='simple-cert-confirmation']")
    expect(confirm).to_be_visible(timeout=5_000)


def test_SV_cert_confirmation_no_false_send_claim(page: Page, live_server: str) -> None:
    """Confirmation text does NOT claim a real email or WhatsApp was actually sent right now."""
    _generate_draft(page, live_server)
    page.locator("[data-testid='simple-cert-name']").fill("مستخدم اختبار")
    page.locator("[data-testid='simple-cert-phone']").fill("01099999999")
    page.locator("[data-testid='simple-cert-delivery-method']").select_option("واتساب والبريد الإلكتروني")
    page.locator("[data-testid='simple-cert-submit']").click()

    confirm = page.locator("[data-testid='simple-cert-confirmation']")
    expect(confirm).to_be_visible(timeout=5_000)
    text = confirm.inner_text()
    # Must NOT contain definite past-tense delivery claims:
    # "تم الإرسال" = the sending is done; "أُرسل" = was sent (instant past)
    # Note: "يتم إرسال … عند تفعيل نظام التواصل" (will be sent upon activation) is acceptable.
    assert "تم الإرسال" not in text
    assert "أُرسل" not in text
    # Must contain the "عند تفعيل" conditional clause or similar to show it's pending
    assert any(phrase in text for phrase in ["عند تفعيل", "مبدئيًا", "سيتم", "لاحقًا"])


def test_SV_cert_card_hidden_before_generate(page: Page, live_server: str) -> None:
    """The certified request card is NOT visible before the generate button is clicked."""
    _go_to_simple_valuation_tab(page, live_server)
    card = page.locator("[data-testid='simple-valuation-cert-request-card']")
    expect(card).to_be_hidden()


# ---------------------------------------------------------------------------
# Task-D tests — documents upload, mic dictation, expanded geography
# ---------------------------------------------------------------------------

# ── Documents (Part A) ──────────────────────────────────────────────────────

def test_SV_docs_section_visible(page: Page, live_server: str) -> None:
    """Documents section card is visible in the form."""
    _go_to_simple_valuation_tab(page, live_server)
    expect(page.locator("[data-testid='simple-documents-section']")).to_be_visible()


def test_SV_docs_upload_btn_visible(page: Page, live_server: str) -> None:
    """Paperclip/upload button is visible in the documents section."""
    _go_to_simple_valuation_tab(page, live_server)
    expect(page.locator("[data-testid='simple-documents-upload-btn']")).to_be_visible()


def test_SV_docs_input_exists_and_accepts_multiple(page: Page, live_server: str) -> None:
    """The hidden file input exists, accepts multiple files, and the right MIME types."""
    _go_to_simple_valuation_tab(page, live_server)
    el = page.locator("[data-testid='simple-documents-input']")
    assert el.get_attribute("multiple") is not None
    accept = el.get_attribute("accept") or ""
    for ext in [".pdf", ".jpg", ".png", ".doc", ".docx"]:
        assert ext in accept, f"Extension {ext} not in accept attr"


def test_SV_docs_selecting_files_shows_names(page: Page, live_server: str) -> None:
    """Selecting test files via the input displays their names in the file list."""
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-documents-input']").set_input_files([
        {"name": "عقد_البيع.pdf",   "mimeType": "application/pdf",  "buffer": b"fake-pdf"},
        {"name": "صورة_العقار.jpg", "mimeType": "image/jpeg",        "buffer": b"fake-jpg"},
    ])
    file_list = page.locator("[data-testid='simple-documents-list']")
    expect(file_list).to_be_visible()
    list_text = file_list.inner_text()
    assert "عقد_البيع.pdf" in list_text
    assert "صورة_العقار.jpg" in list_text


def test_SV_docs_note_mentions_not_uploaded(page: Page, live_server: str) -> None:
    """The documents policy note states that files are not actually uploaded yet."""
    _go_to_simple_valuation_tab(page, live_server)
    note_text = page.locator("[data-testid='simple-documents-note']").inner_text()
    # Accept either old or new phrasing (updated in Task E)
    assert "لا يتم رفع" in note_text or "لا يتم رفعها فعليًا" in note_text


def test_SV_docs_output_includes_file_names(page: Page, live_server: str) -> None:
    """After generating, selected document names appear in the draft output."""
    _mock_valuation_api(page)
    _go_to_simple_valuation_tab(page, live_server)
    # Attach files AFTER navigation so the page is already loaded
    page.locator("[data-testid='simple-documents-input']").set_input_files([
        {"name": "وثيقة_الملكية.pdf", "mimeType": "application/pdf", "buffer": b"x"},
    ])
    _fill_form_minimum(page)
    page.locator("[data-testid='simple-valuation-generate']").click()

    output = page.locator("[data-testid='simple-valuation-output']")
    expect(output).to_be_visible(timeout=8_000)
    assert "وثيقة_الملكية.pdf" in output.inner_text()


def test_SV_docs_output_notes_not_uploaded(page: Page, live_server: str) -> None:
    """Draft output clarifies that attached documents were not actually uploaded."""
    _mock_valuation_api(page)
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-documents-input']").set_input_files([
        {"name": "test_doc.pdf", "mimeType": "application/pdf", "buffer": b"x"},
    ])
    _fill_form_minimum(page)
    page.locator("[data-testid='simple-valuation-generate']").click()

    output = page.locator("[data-testid='simple-valuation-output']")
    expect(output).to_be_visible(timeout=8_000)
    text = output.inner_text()
    assert "لم يتم رفعها فعليًا" in text or "ستُرسل مع طلب الاعتماد" in text


# ── Microphone (Part B) ─────────────────────────────────────────────────────

def test_SV_mic_description_visible(page: Page, live_server: str) -> None:
    """Mic button for property description is visible in the form."""
    _go_to_simple_valuation_tab(page, live_server)
    expect(page.locator("[data-testid='simple-mic-description']")).to_be_visible()


def test_SV_mic_notes_visible(page: Page, live_server: str) -> None:
    """Mic button for additional notes is visible in the form."""
    _go_to_simple_valuation_tab(page, live_server)
    expect(page.locator("[data-testid='simple-mic-notes']")).to_be_visible()


def test_SV_mic_cert_notes_visible_after_generate(page: Page, live_server: str) -> None:
    """Mic button for cert-request notes is visible after generating the draft."""
    _generate_draft(page, live_server)
    expect(page.locator("[data-testid='simple-mic-cert-notes']")).to_be_visible(timeout=5_000)


def test_SV_mic_unsupported_browser_shows_message(page: Page, live_server: str) -> None:
    """Clicking mic when Web Speech API is unavailable shows the unsupported message."""
    _go_to_simple_valuation_tab(page, live_server)
    # Disable the Speech API in this page context
    page.evaluate("delete window.SpeechRecognition; delete window.webkitSpeechRecognition;")
    page.locator("[data-testid='simple-mic-description']").click()
    status = page.locator("[data-testid='simple-voice-status']")
    expect(status).to_be_visible(timeout=3_000)
    assert "غير مدعوم" in status.inner_text()


# ── Geography (Part C) ──────────────────────────────────────────────────────

def test_SV_geo_country_selector_visible(page: Page, live_server: str) -> None:
    """Country selector with data-testid is visible."""
    _go_to_simple_valuation_tab(page, live_server)
    expect(page.locator("[data-testid='simple-valuation-country']")).to_be_visible()


def test_SV_geo_egypt_shows_governorates(page: Page, live_server: str) -> None:
    """Selecting Egypt populates the region selector with all key governorates."""
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-valuation-country']").select_option("EG")
    options = page.locator("[data-testid='simple-valuation-region'] option").all_inner_texts()
    flat = " | ".join(options)
    for gov in ["القاهرة", "الجيزة", "الغربية", "الإسكندرية", "الدقهلية", "الشرقية"]:
        assert gov in flat, f"Governorate '{gov}' missing from EG province list"


def test_SV_geo_gharbia_shows_tanta_and_mahalla(page: Page, live_server: str) -> None:
    """Selecting الغربية as province shows cities including طنطا and المحلة الكبرى."""
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-valuation-country']").select_option("EG")
    page.locator("[data-testid='simple-valuation-region']").select_option("الغربية")
    options = page.locator("[data-testid='simple-valuation-city'] option").all_inner_texts()
    flat = " | ".join(options)
    assert "طنطا" in flat
    assert "المحلة الكبرى" in flat


def test_SV_geo_saudi_shows_regions(page: Page, live_server: str) -> None:
    """Selecting Saudi Arabia populates region selector with all key regions."""
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-valuation-country']").select_option("SA")
    options = page.locator("[data-testid='simple-valuation-region'] option").all_inner_texts()
    flat = " | ".join(options)
    for region in ["الرياض", "المنطقة الشرقية", "مكة المكرمة", "المدينة المنورة"]:
        assert region in flat, f"Region '{region}' missing from SA province list"


def test_SV_geo_eastern_region_shows_dammam_and_khobar(page: Page, live_server: str) -> None:
    """Selecting المنطقة الشرقية shows cities including الدمام and الخبر."""
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-valuation-country']").select_option("SA")
    page.locator("[data-testid='simple-valuation-region']").select_option("المنطقة الشرقية")
    options = page.locator("[data-testid='simple-valuation-city'] option").all_inner_texts()
    flat = " | ".join(options)
    assert "الدمام" in flat
    assert "الخبر" in flat


def test_SV_geo_non_detailed_country_shows_freetext_or_note(page: Page, live_server: str) -> None:
    """All Arab countries now have province and city selects with مدينة أخرى option."""
    _go_to_simple_valuation_tab(page, live_server)
    # Jordan has provinces — verify province select is populated
    page.locator("[data-testid='simple-valuation-country']").select_option("JO")
    options = page.locator("[data-testid='simple-valuation-region'] option").all_inner_texts()
    flat = " | ".join(options)
    assert "عمان" in flat and "إربد" in flat, \
        "Expected Jordan province options to include عمان and إربد"
    # Selecting a province shows city select with مدينة أخرى
    page.locator("[data-testid='simple-valuation-region']").select_option("عمان")
    city_select = page.locator("[data-testid='simple-valuation-city']")
    expect(city_select).to_be_visible(timeout=3_000)
    city_options = page.locator("[data-testid='simple-valuation-city'] option").all_inner_texts()
    city_flat = " | ".join(city_options)
    assert "مدينة أخرى" in city_flat, "City select should include مدينة أخرى option"


def test_SV_geo_output_includes_country_region_city(page: Page, live_server: str) -> None:
    """Draft output includes الدولة, المحافظة/المنطقة, and المدينة rows."""
    _generate_draft(page, live_server)
    output_text = page.locator("[data-testid='simple-valuation-output']").inner_text(timeout=8_000)
    # _generate_draft fills EG / القاهرة / المعادي
    assert "مصر" in output_text or "الدولة" in output_text
    assert "القاهرة" in output_text
    assert "المعادي" in output_text


# ---------------------------------------------------------------------------
# Task-E tests — Parts A, B, C, D
# ---------------------------------------------------------------------------

# ── Part A: Documents belong to draft workflow ───────────────────────────────

def test_SV_docs_draft_row_always_present(page: Page, live_server: str) -> None:
    """Draft output always contains the documents row (even when no files selected)."""
    _generate_draft(page, live_server)
    output = page.locator("[data-testid='simple-valuation-output']")
    expect(output).to_be_visible(timeout=8_000)
    row = page.locator("[data-testid='simple-draft-documents-row']")
    expect(row).to_be_visible(timeout=5_000)


def test_SV_docs_draft_no_files_shows_none_msg(page: Page, live_server: str) -> None:
    """Draft output shows 'لم يتم اختيار مستندات' when no files are attached."""
    _generate_draft(page, live_server)
    output = page.locator("[data-testid='simple-valuation-output']")
    expect(output).to_be_visible(timeout=8_000)
    assert "لم يتم اختيار مستندات" in output.inner_text()


def test_SV_docs_draft_files_appear_in_row(page: Page, live_server: str) -> None:
    """After attaching a file and generating, it appears in the draft documents row."""
    _mock_valuation_api(page)
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-documents-input']").set_input_files([
        {"name": "صك_الملكية.pdf", "mimeType": "application/pdf", "buffer": b"x"},
    ])
    _fill_form_minimum(page)
    page.locator("[data-testid='simple-valuation-generate']").click()
    output = page.locator("[data-testid='simple-valuation-output']")
    expect(output).to_be_visible(timeout=8_000)
    row = page.locator("[data-testid='simple-draft-documents-row']")
    expect(row).to_be_visible(timeout=5_000)
    assert "صك_الملكية.pdf" in row.inner_text()


def test_SV_docs_draft_note_files_not_uploaded(page: Page, live_server: str) -> None:
    """Draft output row for docs clarifies files are not uploaded to server."""
    _mock_valuation_api(page)
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-documents-input']").set_input_files([
        {"name": "ملف.pdf", "mimeType": "application/pdf", "buffer": b"x"},
    ])
    _fill_form_minimum(page)
    page.locator("[data-testid='simple-valuation-generate']").click()
    output = page.locator("[data-testid='simple-valuation-output']")
    expect(output).to_be_visible(timeout=8_000)
    text = output.inner_text()
    assert "لم يتم رفعها فعليًا" in text or "لم يتم رفع" in text


def test_SV_docs_no_cert_required_for_draft_docs(page: Page, live_server: str) -> None:
    """Attached documents appear in draft output without needing to submit the cert request."""
    _mock_valuation_api(page)
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-documents-input']").set_input_files([
        {"name": "رخصة_البناء.pdf", "mimeType": "application/pdf", "buffer": b"x"},
    ])
    _fill_form_minimum(page)
    page.locator("[data-testid='simple-valuation-generate']").click()
    output = page.locator("[data-testid='simple-valuation-output']")
    expect(output).to_be_visible(timeout=8_000)
    # Doc name must appear in output without cert request being submitted
    assert "رخصة_البناء.pdf" in output.inner_text()
    # Cert confirmation must still be hidden (not submitted)
    expect(page.locator("[data-testid='simple-cert-confirmation']")).to_be_hidden()


# ── Part B: Expert request clarity ───────────────────────────────────────────

def test_SV_expert_intro_card_visible_before_generate(page: Page, live_server: str) -> None:
    """The always-visible expert request intro card is visible before generating."""
    _go_to_simple_valuation_tab(page, live_server)
    expect(page.locator("[data-testid='simple-expert-request-intro']")).to_be_visible()


def test_SV_expert_request_button_exists(page: Page, live_server: str) -> None:
    """The expert request button inside the intro card is visible."""
    _go_to_simple_valuation_tab(page, live_server)
    expect(page.locator("[data-testid='simple-expert-request-button']")).to_be_visible()


def test_SV_expert_request_button_reveals_cert_card(page: Page, live_server: str) -> None:
    """Clicking the expert request button shows the certified request card."""
    _go_to_simple_valuation_tab(page, live_server)
    cert_card = page.locator("[data-testid='simple-valuation-cert-request-card']")
    expect(cert_card).to_be_hidden()
    page.locator("[data-testid='simple-expert-request-button']").click()
    expect(cert_card).to_be_visible(timeout=3_000)


def test_SV_cert_card_mentions_approved_pdf(page: Page, live_server: str) -> None:
    """Certified request card states that an approved PDF will be sent after expert review."""
    _generate_draft(page, live_server)
    cert_note = page.locator("[data-testid='simple-cert-delivery-note']")
    expect(cert_note).to_be_visible(timeout=5_000)
    text = cert_note.inner_text()
    assert "PDF" in text, "Cert card should mention PDF"


def test_SV_cert_card_excel_internal_only(page: Page, live_server: str) -> None:
    """Certified request card states that Excel files are internal for expert/admin only."""
    _generate_draft(page, live_server)
    cert_note = page.locator("[data-testid='simple-cert-delivery-note']")
    expect(cert_note).to_be_visible(timeout=5_000)
    text = cert_note.inner_text()
    assert "Excel" in text and ("داخلية" in text or "داخلي" in text), \
        "Cert card should state Excel is internal"


# ── Part C: Geography — all Arab countries have regions ──────────────────────

def test_SV_geo_UAE_has_regions(page: Page, live_server: str) -> None:
    """UAE shows region options including أبوظبي، دبي، الشارقة."""
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-valuation-country']").select_option("AE")
    options = page.locator("[data-testid='simple-valuation-region'] option").all_inner_texts()
    flat = " | ".join(options)
    for region in ["أبوظبي", "دبي", "الشارقة"]:
        assert region in flat, f"UAE region '{region}' missing"


def test_SV_geo_Kuwait_has_regions(page: Page, live_server: str) -> None:
    """Kuwait shows region options including العاصمة، حولي، الفروانية."""
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-valuation-country']").select_option("KW")
    options = page.locator("[data-testid='simple-valuation-region'] option").all_inner_texts()
    flat = " | ".join(options)
    for region in ["العاصمة", "حولي", "الفروانية"]:
        assert region in flat, f"Kuwait region '{region}' missing"


def test_SV_geo_Jordan_has_regions(page: Page, live_server: str) -> None:
    """Jordan shows region options including عمان، إربد، الزرقاء."""
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-valuation-country']").select_option("JO")
    options = page.locator("[data-testid='simple-valuation-region'] option").all_inner_texts()
    flat = " | ".join(options)
    for region in ["عمان", "إربد", "الزرقاء"]:
        assert region in flat, f"Jordan region '{region}' missing"


def test_SV_geo_Palestine_has_regions(page: Page, live_server: str) -> None:
    """Palestine shows region options including القدس، رام الله والبيرة، غزة."""
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-valuation-country']").select_option("PS")
    options = page.locator("[data-testid='simple-valuation-region'] option").all_inner_texts()
    flat = " | ".join(options)
    for region in ["القدس", "رام الله والبيرة", "غزة"]:
        assert region in flat, f"Palestine region '{region}' missing"


def test_SV_geo_Morocco_has_regions(page: Page, live_server: str) -> None:
    """Morocco shows region options including الدار البيضاء سطات and الرباط سلا القنيطرة."""
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-valuation-country']").select_option("MA")
    options = page.locator("[data-testid='simple-valuation-region'] option").all_inner_texts()
    flat = " | ".join(options)
    for region in ["الدار البيضاء سطات", "الرباط سلا القنيطرة"]:
        assert region in flat, f"Morocco region '{region}' missing"


def test_SV_geo_Tunisia_has_regions(page: Page, live_server: str) -> None:
    """Tunisia shows region options including تونس، صفاقس، سوسة."""
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-valuation-country']").select_option("TN")
    options = page.locator("[data-testid='simple-valuation-region'] option").all_inner_texts()
    flat = " | ".join(options)
    for region in ["تونس", "صفاقس", "سوسة"]:
        assert region in flat, f"Tunisia region '{region}' missing"


def test_SV_geo_Sudan_has_regions(page: Page, live_server: str) -> None:
    """Sudan shows region options including الخرطوم and الجزيرة."""
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-valuation-country']").select_option("SD")
    options = page.locator("[data-testid='simple-valuation-region'] option").all_inner_texts()
    flat = " | ".join(options)
    for region in ["الخرطوم", "الجزيرة"]:
        assert region in flat, f"Sudan region '{region}' missing"


def test_SV_geo_province_only_city_freetext(page: Page, live_server: str) -> None:
    """Selecting 'مدينة أخرى' from the city dropdown shows the free-text city input."""
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-valuation-country']").select_option("AE")
    page.locator("[data-testid='simple-valuation-region']").select_option("دبي")
    # City select should now be visible with options
    city_select = page.locator("[data-testid='simple-valuation-city']")
    expect(city_select).to_be_visible(timeout=3_000)
    # دبي cities should include دبي and مدينة أخرى
    city_opts = page.locator("[data-testid='simple-valuation-city'] option").all_inner_texts()
    city_flat = " | ".join(city_opts)
    assert "دبي" in city_flat and "مدينة أخرى" in city_flat
    # Selecting مدينة أخرى reveals free-text input
    page.locator("[data-testid='simple-valuation-city']").select_option("مدينة أخرى")
    city_text = page.locator("#geo-city-text")
    expect(city_text).to_be_visible(timeout=3_000)


def test_SV_geo_province_only_draft_output(page: Page, live_server: str) -> None:
    """Selecting 'مدينة أخرى' and typing a city name shows it in the draft output."""
    _mock_valuation_api(page)
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-valuation-country']").select_option("JO")
    page.locator("[data-testid='simple-valuation-region']").select_option("عمان")
    page.locator("[data-testid='simple-valuation-city']").select_option("مدينة أخرى")
    page.locator("#geo-city-text").fill("وسط البلد")
    page.locator("[data-testid='simple-valuation-description']").fill("شقة سكنية في عمان للاستثمار")
    page.locator("[data-testid='simple-valuation-area']").fill("100")
    page.locator("[data-testid='simple-valuation-property-type']").select_option("شقة سكنية")
    page.locator("[data-testid='simple-valuation-condition']").select_option("جيدة")
    page.locator("[data-testid='simple-valuation-generate']").click()
    output = page.locator("[data-testid='simple-valuation-output']")
    expect(output).to_be_visible(timeout=8_000)
    text = output.inner_text()
    assert "الأردن" in text or "الدولة" in text
    assert "عمان" in text
    assert "وسط البلد" in text


# ---------------------------------------------------------------------------
# Refinement tests — Part A: docs inside basic property; Part B: expanded cities
# ---------------------------------------------------------------------------

# ── Documents inside basic property section ────────────────────────────────

def test_SV_docs_section_inside_basic_property(page: Page, live_server: str) -> None:
    """Documents section is nested inside the basic property information section."""
    _go_to_simple_valuation_tab(page, live_server)
    is_inside = page.evaluate("""() => {
        const docsEl = document.querySelector('[data-testid="simple-documents-section"]');
        const parentSection = docsEl && docsEl.closest('[data-testid="simple-basic-property-section"]');
        return !!parentSection;
    }""")
    assert is_inside, "Documents section should be inside the basic property section"


def test_SV_docs_in_property_section_visible(page: Page, live_server: str) -> None:
    """Documents upload button and note are visible inside the basic property section."""
    _go_to_simple_valuation_tab(page, live_server)
    prop_section = page.locator("[data-testid='simple-basic-property-section']")
    expect(prop_section.locator("[data-testid='simple-documents-upload-btn']")).to_be_visible()
    expect(prop_section.locator("[data-testid='simple-documents-note']")).to_be_visible()


def test_SV_docs_in_property_note_says_draft_report(page: Page, live_server: str) -> None:
    """Documents note mentions the draft report, not only certified approval."""
    _go_to_simple_valuation_tab(page, live_server)
    note = page.locator("[data-testid='simple-documents-note']").inner_text()
    assert "التقرير المبدئي" in note, "Note should mention the draft report"


def test_SV_docs_before_generate_visible_in_property_section(page: Page, live_server: str) -> None:
    """Document list appears inside the property section after selecting files."""
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-documents-input']").set_input_files([
        {"name": "رخصة.pdf", "mimeType": "application/pdf", "buffer": b"x"},
    ])
    prop_section = page.locator("[data-testid='simple-basic-property-section']")
    doc_list = prop_section.locator("[data-testid='simple-documents-list']")
    expect(doc_list).to_be_visible()
    assert "رخصة.pdf" in doc_list.inner_text()


# ── Expanded city dropdown tests ────────────────────────────────────────────

def test_SV_geo_UAE_Dubai_shows_cities(page: Page, live_server: str) -> None:
    """UAE / Dubai shows city options including دبي، ديرة، جبل علي and مدينة أخرى."""
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-valuation-country']").select_option("AE")
    page.locator("[data-testid='simple-valuation-region']").select_option("دبي")
    options = page.locator("[data-testid='simple-valuation-city'] option").all_inner_texts()
    flat = " | ".join(options)
    for city in ["دبي", "ديرة", "جبل علي", "مدينة أخرى"]:
        assert city in flat, f"Dubai city missing: {city}"


def test_SV_geo_Kuwait_Hawalli_shows_cities(page: Page, live_server: str) -> None:
    """Kuwait / حولي shows السالمية and الجابرية."""
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-valuation-country']").select_option("KW")
    page.locator("[data-testid='simple-valuation-region']").select_option("حولي")
    options = page.locator("[data-testid='simple-valuation-city'] option").all_inner_texts()
    flat = " | ".join(options)
    assert "السالمية" in flat and "الجابرية" in flat


def test_SV_geo_Qatar_Doha_shows_cities(page: Page, live_server: str) -> None:
    """Qatar / الدوحة shows الدوحة and السد."""
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-valuation-country']").select_option("QA")
    page.locator("[data-testid='simple-valuation-region']").select_option("الدوحة")
    options = page.locator("[data-testid='simple-valuation-city'] option").all_inner_texts()
    flat = " | ".join(options)
    assert "الدوحة" in flat and "السد" in flat


def test_SV_geo_Jordan_Amman_shows_cities(page: Page, live_server: str) -> None:
    """Jordan / عمان shows عمان and عبدون."""
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-valuation-country']").select_option("JO")
    page.locator("[data-testid='simple-valuation-region']").select_option("عمان")
    options = page.locator("[data-testid='simple-valuation-city'] option").all_inner_texts()
    flat = " | ".join(options)
    assert "عمان" in flat and "عبدون" in flat


def test_SV_geo_Palestine_Gaza_shows_cities(page: Page, live_server: str) -> None:
    """Palestine / غزة shows غزة and الرمال."""
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-valuation-country']").select_option("PS")
    page.locator("[data-testid='simple-valuation-region']").select_option("غزة")
    options = page.locator("[data-testid='simple-valuation-city'] option").all_inner_texts()
    flat = " | ".join(options)
    assert "غزة" in flat and "الرمال" in flat


def test_SV_geo_Morocco_Casablanca_shows_cities(page: Page, live_server: str) -> None:
    """Morocco / الدار البيضاء سطات shows الدار البيضاء and سطات."""
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-valuation-country']").select_option("MA")
    page.locator("[data-testid='simple-valuation-region']").select_option("الدار البيضاء سطات")
    options = page.locator("[data-testid='simple-valuation-city'] option").all_inner_texts()
    flat = " | ".join(options)
    assert "الدار البيضاء" in flat and "سطات" in flat


def test_SV_geo_Algeria_Algiers_shows_cities(page: Page, live_server: str) -> None:
    """Algeria / الجزائر العاصمة shows الجزائر العاصمة."""
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-valuation-country']").select_option("DZ")
    page.locator("[data-testid='simple-valuation-region']").select_option("الجزائر العاصمة")
    options = page.locator("[data-testid='simple-valuation-city'] option").all_inner_texts()
    flat = " | ".join(options)
    assert "الجزائر العاصمة" in flat


def test_SV_geo_Tunisia_Tunis_shows_cities(page: Page, live_server: str) -> None:
    """Tunisia / تونس shows تونس and المرسى."""
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-valuation-country']").select_option("TN")
    page.locator("[data-testid='simple-valuation-region']").select_option("تونس")
    options = page.locator("[data-testid='simple-valuation-city'] option").all_inner_texts()
    flat = " | ".join(options)
    assert "تونس" in flat and "المرسى" in flat


def test_SV_geo_Libya_Tripoli_shows_cities(page: Page, live_server: str) -> None:
    """Libya / طرابلس shows طرابلس and تاجوراء."""
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-valuation-country']").select_option("LY")
    page.locator("[data-testid='simple-valuation-region']").select_option("طرابلس")
    options = page.locator("[data-testid='simple-valuation-city'] option").all_inner_texts()
    flat = " | ".join(options)
    assert "طرابلس" in flat and "تاجوراء" in flat


def test_SV_geo_Sudan_Khartoum_shows_cities(page: Page, live_server: str) -> None:
    """Sudan / الخرطوم shows الخرطوم and أم درمان."""
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-valuation-country']").select_option("SD")
    page.locator("[data-testid='simple-valuation-region']").select_option("الخرطوم")
    options = page.locator("[data-testid='simple-valuation-city'] option").all_inner_texts()
    flat = " | ".join(options)
    assert "الخرطوم" in flat and "أم درمان" in flat


def test_SV_geo_madina_ukhra_shows_freetext(page: Page, live_server: str) -> None:
    """Selecting 'مدينة أخرى' from city dropdown shows the free-text city input field."""
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-valuation-country']").select_option("EG")
    page.locator("[data-testid='simple-valuation-region']").select_option("القاهرة")
    page.locator("[data-testid='simple-valuation-city']").select_option("مدينة أخرى")
    city_text = page.locator("#geo-city-text")
    expect(city_text).to_be_visible(timeout=3_000)


def test_SV_geo_draft_output_shows_madina_ukhra_text(page: Page, live_server: str) -> None:
    """Draft output shows the manually entered city (not the label 'مدينة أخرى')."""
    _mock_valuation_api(page)
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-valuation-country']").select_option("EG")
    page.locator("[data-testid='simple-valuation-region']").select_option("القاهرة")
    page.locator("[data-testid='simple-valuation-city']").select_option("مدينة أخرى")
    page.locator("#geo-city-text").fill("قرية الشيخ زايد")
    page.locator("[data-testid='simple-valuation-description']").fill("منزل في ضاحية هادئة")
    page.locator("[data-testid='simple-valuation-area']").fill("150")
    page.locator("[data-testid='simple-valuation-property-type']").select_option("فيلا")
    page.locator("[data-testid='simple-valuation-condition']").select_option("ممتازة")
    page.locator("[data-testid='simple-valuation-generate']").click()
    output = page.locator("[data-testid='simple-valuation-output']")
    expect(output).to_be_visible(timeout=8_000)
    text = output.inner_text()
    assert "قرية الشيخ زايد" in text, "Custom city text should appear in draft output"


def test_SV_geo_district_freetext_available(page: Page, live_server: str) -> None:
    """District / neighborhood field becomes editable after city is selected."""
    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-valuation-country']").select_option("SA")
    page.locator("[data-testid='simple-valuation-region']").select_option("الرياض")
    page.locator("[data-testid='simple-valuation-city']").select_option("الرياض")
    district = page.locator("[data-testid='simple-valuation-district']")
    expect(district).to_be_enabled(timeout=3_000)
    district.fill("حي النخيل")
    assert district.input_value() == "حي النخيل"


# ---------------------------------------------------------------------------
# Shared Backend integration tests — Simple Valuation cert-request form
# ---------------------------------------------------------------------------

def test_SV_cert_request_saves_to_backend(page: Page, live_server: str) -> None:
    """Submitting the cert request form posts to /api/expert-requests and shows confirmation."""
    import json as _json
    _mock_body = _json.dumps({
        "status":          "success",
        "request_id":      "REQ-TEST0001",
        "source_page":     "simple_valuation",
        "request_kind":    "certified_report_request",
        "message":         "تم تسجيل الطلب بنجاح. رقم الطلب: REQ-TEST0001.",
        "pdf_available":   True,
        "pdf_download_url":"/api/expert-requests/REQ-TEST0001/draft-pdf",
        "non_certified":   True,
        "documents_saved": 0,
        "document_errors": [],
    }).encode()
    page.route("**/api/expert-requests", lambda r: r.fulfill(
        status=201, body=_mock_body, content_type="application/json"
    ))

    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-expert-request-button']").click()
    cert_card = page.locator("[data-testid='simple-valuation-cert-request-card']")
    cert_card.wait_for(state="visible", timeout=5_000)

    page.locator("[data-testid='simple-cert-name']").fill("محمد أحمد الاختبار")
    page.locator("[data-testid='simple-cert-phone']").fill("01012345678")
    page.locator("[data-testid='simple-cert-delivery-method']").select_option("واتساب")
    page.locator("[data-testid='simple-cert-submit']").click()

    confirm = page.locator("[data-testid='simple-cert-confirmation']")
    expect(confirm).to_be_visible(timeout=8_000)
    assert "تم" in confirm.inner_text()


def test_SV_cert_request_confirmation_shows_request_id(page: Page, live_server: str) -> None:
    """Confirmation message includes the request_id returned by the backend."""
    import json as _json
    _mock_body = _json.dumps({
        "status":          "success",
        "request_id":      "REQ-ABCD1234",
        "message":         "تم تسجيل الطلب.",
        "pdf_available":   False,
        "non_certified":   True,
        "documents_saved": 0,
        "document_errors": [],
    }).encode()
    page.route("**/api/expert-requests", lambda r: r.fulfill(
        status=201, body=_mock_body, content_type="application/json"
    ))

    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-expert-request-button']").click()
    page.locator("[data-testid='simple-valuation-cert-request-card']").wait_for(
        state="visible", timeout=5_000
    )
    page.locator("[data-testid='simple-cert-name']").fill("محمد الاختبار")
    page.locator("[data-testid='simple-cert-phone']").fill("01099999999")
    page.locator("[data-testid='simple-cert-delivery-method']").select_option("البريد الإلكتروني")
    page.locator("[data-testid='simple-cert-submit']").click()

    confirm = page.locator("[data-testid='simple-cert-confirmation']")
    expect(confirm).to_be_visible(timeout=8_000)
    assert "REQ-ABCD1234" in confirm.inner_text()


def test_SV_cert_pdf_link_shown_when_available(page: Page, live_server: str) -> None:
    """When pdf_available=True, a PDF download link appears in confirmation."""
    import json as _json
    _mock_body = _json.dumps({
        "status":          "success",
        "request_id":      "REQ-PDFTEST1",
        "message":         "تم تسجيل الطلب.",
        "pdf_available":   True,
        "pdf_download_url":"/api/expert-requests/REQ-PDFTEST1/draft-pdf",
        "non_certified":   True,
        "documents_saved": 0,
        "document_errors": [],
    }).encode()
    page.route("**/api/expert-requests", lambda r: r.fulfill(
        status=201, body=_mock_body, content_type="application/json"
    ))

    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-expert-request-button']").click()
    page.locator("[data-testid='simple-valuation-cert-request-card']").wait_for(
        state="visible", timeout=5_000
    )
    page.locator("[data-testid='simple-cert-name']").fill("اختبار PDF")
    page.locator("[data-testid='simple-cert-phone']").fill("01011111111")
    page.locator("[data-testid='simple-cert-delivery-method']").select_option("واتساب")
    page.locator("[data-testid='simple-cert-submit']").click()

    confirm = page.locator("[data-testid='simple-cert-confirmation']")
    expect(confirm).to_be_visible(timeout=8_000)
    pdf_link = confirm.locator("a[href*='/api/expert-requests/']")
    expect(pdf_link).to_have_count(1)


def test_SV_cert_no_whatsapp_email_sent_field(page: Page, live_server: str) -> None:
    """Backend for simple valuation cert request never claims WhatsApp/email was sent."""
    import json as _json
    captured = {}

    def _intercept(route):
        resp = route.fetch()
        try:
            captured["json"] = resp.json()
        except Exception:
            captured["json"] = {}
        route.fulfill(response=resp)

    page.route("**/api/expert-requests", _intercept)

    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-expert-request-button']").click()
    page.locator("[data-testid='simple-valuation-cert-request-card']").wait_for(
        state="visible", timeout=5_000
    )
    page.locator("[data-testid='simple-cert-name']").fill("اختبار")
    page.locator("[data-testid='simple-cert-phone']").fill("01012345678")
    page.locator("[data-testid='simple-cert-delivery-method']").select_option("واتساب")
    page.locator("[data-testid='simple-cert-submit']").click()
    page.locator("[data-testid='simple-cert-confirmation']").wait_for(
        state="visible", timeout=8_000
    )

    if captured.get("json"):
        resp_str = str(captured["json"])
        assert "email_sent"    not in resp_str
        assert "whatsapp_sent" not in resp_str


def test_SV_cert_excel_hidden_in_confirmation(page: Page, live_server: str) -> None:
    """No Excel download link appears in the simple valuation cert confirmation."""
    import json as _json
    _mock_body = _json.dumps({
        "status":          "success",
        "request_id":      "REQ-XLSTEST1",
        "message":         "تم تسجيل الطلب.",
        "pdf_available":   False,
        "non_certified":   True,
        "documents_saved": 0,
        "document_errors": [],
    }).encode()
    page.route("**/api/expert-requests", lambda r: r.fulfill(
        status=201, body=_mock_body, content_type="application/json"
    ))

    _go_to_simple_valuation_tab(page, live_server)
    page.locator("[data-testid='simple-expert-request-button']").click()
    page.locator("[data-testid='simple-valuation-cert-request-card']").wait_for(
        state="visible", timeout=5_000
    )
    page.locator("[data-testid='simple-cert-name']").fill("اختبار Excel")
    page.locator("[data-testid='simple-cert-phone']").fill("01011111111")
    page.locator("[data-testid='simple-cert-delivery-method']").select_option("واتساب")
    page.locator("[data-testid='simple-cert-submit']").click()

    confirm = page.locator("[data-testid='simple-cert-confirmation']")
    expect(confirm).to_be_visible(timeout=8_000)
    html = confirm.inner_html()
    assert ".xlsx" not in html
    assert ".xlsm" not in html


# ---------------------------------------------------------------------------
# Section I — Parts A–H (new features: mini-engine, range card, docs, PDF, expert, RAG)
# ---------------------------------------------------------------------------

# ── Part A: Mini-engine panel ────────────────────────────────────────────────

def test_SV_mini_engine_panel_exists(page: Page, live_server: str) -> None:
    """Mini-engine info panel is always visible before generating."""
    _go_to_simple_valuation_tab(page, live_server)
    expect(page.locator("[data-testid='simple-valuation-mini-engine']")).to_be_visible()


def test_SV_price_source_note_no_qdrant_active_claim(page: Page, live_server: str) -> None:
    """Price-source note honestly says Qdrant link is future, not currently active."""
    _go_to_simple_valuation_tab(page, live_server)
    note = page.locator("[data-testid='simple-valuation-price-source-note']").inner_text()
    # Must mention future phase, must NOT say Qdrant is currently connected
    assert "المرحلة التالية" in note or "سيتم" in note
    assert "مفعّل حاليًا" not in note


def test_SV_method_note_visible(page: Page, live_server: str) -> None:
    """Method note is visible inside the mini-engine panel."""
    _go_to_simple_valuation_tab(page, live_server)
    expect(page.locator("[data-testid='simple-valuation-method-note']")).to_be_visible()


# ── Part B: Value / range card ───────────────────────────────────────────────

def _generate_draft_helper(page: Page, live_server: str) -> None:
    """Navigate, mock, fill and generate — duplicate of _generate_draft for tests that need it."""
    _mock_valuation_api(page)
    _go_to_simple_valuation_tab(page, live_server)
    _fill_form_minimum(page)
    page.locator("[data-testid='simple-valuation-generate']").click()
    page.locator("[data-testid='simple-valuation-output']").wait_for(state="visible", timeout=8_000)


def test_SV_value_range_card_appears_after_generate(page: Page, live_server: str) -> None:
    """Range card is visible in output after successful generate."""
    _generate_draft_helper(page, live_server)
    expect(page.locator("[data-testid='simple-value-range-card']")).to_be_visible(timeout=5_000)


def test_SV_range_card_has_estimated_value_and_bounds(page: Page, live_server: str) -> None:
    """Range card shows estimated value, low range, high range elements."""
    _generate_draft_helper(page, live_server)
    expect(page.locator("[data-testid='simple-estimated-market-value']")).to_be_visible(timeout=5_000)
    expect(page.locator("[data-testid='simple-price-range-low']")).to_be_visible(timeout=5_000)
    expect(page.locator("[data-testid='simple-price-range-high']")).to_be_visible(timeout=5_000)


def test_SV_data_gap_shown_when_no_market_value(page: Page, live_server: str) -> None:
    """Data-gap panel appears when API returns success but no market_value."""
    page.route("**/api/valuation", lambda r: r.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"status": "success", "report_id": "DRAFT-GAP-001"}),
    ))
    _go_to_simple_valuation_tab(page, live_server)
    _fill_form_minimum(page)
    page.locator("[data-testid='simple-valuation-generate']").click()
    page.locator("[data-testid='simple-valuation-output']").wait_for(state="visible", timeout=8_000)
    expect(page.locator("[data-testid='simple-valuation-data-gap']")).to_be_visible(timeout=5_000)
    # Range card must NOT be visible when there is no value
    expect(page.locator("[data-testid='simple-value-range-card']")).not_to_be_visible()


def test_SV_condition_multiplier_output_visible(page: Page, live_server: str) -> None:
    """Condition multiplier output is visible inside range card after generate."""
    _generate_draft_helper(page, live_server)
    expect(page.locator("[data-testid='simple-condition-multiplier-output']")).to_be_visible(timeout=5_000)


def test_SV_finishing_multiplier_output_visible(page: Page, live_server: str) -> None:
    """Finishing multiplier output is visible inside range card after generate."""
    _generate_draft_helper(page, live_server)
    expect(page.locator("[data-testid='simple-finishing-multiplier-output']")).to_be_visible(timeout=5_000)


def test_SV_value_confidence_note_warns_non_certified(page: Page, live_server: str) -> None:
    """Confidence note in range card clarifies the value is advisory."""
    _generate_draft_helper(page, live_server)
    note = page.locator("[data-testid='simple-value-confidence-note']").inner_text()
    assert "استرشادية" in note or "غير معتمدة" in note or "مبدئية" in note


# ── Part C: Document guidance and OCR ───────────────────────────────────────

def test_SV_required_documents_list_visible(page: Page, live_server: str) -> None:
    """Required documents guidance list is visible before generating."""
    _go_to_simple_valuation_tab(page, live_server)
    expect(page.locator("[data-testid='simple-required-documents-list']")).to_be_visible()


def test_SV_required_documents_includes_title_deed(page: Page, live_server: str) -> None:
    """Documents list includes title deed or sale contract."""
    _go_to_simple_valuation_tab(page, live_server)
    text = page.locator("[data-testid='simple-required-documents-list']").inner_text()
    assert "سند الملكية" in text or "عقد البيع" in text


def test_SV_required_documents_includes_area_sketch(page: Page, live_server: str) -> None:
    """Documents list includes area plan or sketch."""
    _go_to_simple_valuation_tab(page, live_server)
    text = page.locator("[data-testid='simple-required-documents-list']").inner_text()
    assert "كشف مساحة" in text or "رسم كروكي" in text


def test_SV_ocr_note_says_future_not_active(page: Page, live_server: str) -> None:
    """OCR note honestly states the feature is not currently active."""
    _go_to_simple_valuation_tab(page, live_server)
    note = page.locator("[data-testid='simple-ocr-note']").inner_text()
    assert "غير مفعّلة" in note or "لاحقة" in note or "لاحقًا" in note


# ── Part D: Draft PDF ────────────────────────────────────────────────────────

def test_SV_draft_report_warning_says_non_certified(page: Page, live_server: str) -> None:
    """Draft warning in output explicitly says non-certified."""
    _generate_draft_helper(page, live_server)
    warning = page.locator("[data-testid='simple-valuation-draft-warning']").inner_text()
    assert "غير معتمد" in warning


def test_SV_pdf_watermark_note_text(page: Page, live_server: str) -> None:
    """PDF watermark note contains the required non-certified label."""
    _generate_draft_helper(page, live_server)
    note = page.locator("[data-testid='simple-pdf-watermark-note']").inner_text()
    assert "غير معتمد" in note


def test_SV_internal_excel_note_says_expert_only(page: Page, live_server: str) -> None:
    """Internal Excel note states it is for expert/admin only."""
    _generate_draft_helper(page, live_server)
    note = page.locator("[data-testid='simple-internal-excel-note']").inner_text()
    assert "خبير" in note or "إدارة" in note or "داخلي" in note


def test_SV_draft_pdf_button_exists_in_output(page: Page, live_server: str) -> None:
    """Draft PDF button is present in output (may be disabled)."""
    _generate_draft_helper(page, live_server)
    btn = page.locator("[data-testid='simple-draft-pdf-button']")
    expect(btn).to_be_visible(timeout=5_000)


# ── Part E: Expert / certified request card ──────────────────────────────────

def test_SV_certified_request_card_visible_after_generate(page: Page, live_server: str) -> None:
    """Inner certified-request card is visible after generate."""
    _generate_draft_helper(page, live_server)
    expect(page.locator("[data-testid='simple-certified-request-card']")).to_be_visible(timeout=5_000)


def test_SV_certified_request_validation_requires_name(page: Page, live_server: str) -> None:
    """Submitting expert request without name does not show confirmation."""
    _generate_draft_helper(page, live_server)
    page.locator("[data-testid='simple-cert-phone']").fill("01012345678")
    page.locator("[data-testid='simple-cert-delivery-method']").select_option("واتساب")
    page.locator("[data-testid='simple-cert-submit']").click()
    expect(page.locator("[data-testid='simple-cert-confirmation']")).not_to_be_visible()


def test_SV_certified_request_confirmation_not_claiming_certification(page: Page, live_server: str) -> None:
    """Expert request confirmation does not falsely claim the report is certified."""
    page.route("**/api/expert-requests", lambda r: r.fulfill(
        status=201,
        content_type="application/json",
        body=json.dumps({"status": "ok", "request_id": "REQ-CERT-UI-TEST"}),
    ))
    _generate_draft_helper(page, live_server)
    page.locator("[data-testid='simple-cert-name']").fill("محمد أحمد")
    page.locator("[data-testid='simple-cert-phone']").fill("01012345678")
    page.locator("[data-testid='simple-cert-delivery-method']").select_option("واتساب")
    page.locator("[data-testid='simple-cert-submit']").click()
    conf = page.locator("[data-testid='simple-cert-confirmation']")
    expect(conf).to_be_visible(timeout=8_000)
    text = conf.inner_text()
    assert "أصبح معتمدًا" not in text
    assert "مختوم" not in text


# ── Part F: Quick context question ───────────────────────────────────────────

def test_SV_quick_context_question_visible(page: Page, live_server: str) -> None:
    """Quick context question textarea is visible before generating."""
    _go_to_simple_valuation_tab(page, live_server)
    expect(page.locator("[data-testid='simple-quick-context-question']")).to_be_visible()


def test_SV_quick_context_note_no_rag_active_claim(page: Page, live_server: str) -> None:
    """Quick context note says RAG/Qdrant is a future feature, not currently active."""
    _go_to_simple_valuation_tab(page, live_server)
    note = page.locator("[data-testid='simple-quick-context-note']").inner_text()
    assert "لاحقًا" in note or "سيتم" in note


def test_SV_quick_context_appears_in_output(page: Page, live_server: str) -> None:
    """Quick context question text is echoed in the draft output."""
    page.route("**/api/valuation", lambda r: r.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"status": "success", "market_value": 2_500_000, "report_id": "DRAFT-QC-001"}),
    ))
    _go_to_simple_valuation_tab(page, live_server)
    _fill_form_minimum(page)
    page.locator("[data-testid='simple-quick-context-question']").fill("هل السعر سيزيد بعد فتح المحور الجديد؟")
    page.locator("[data-testid='simple-valuation-generate']").click()
    ctx_out = page.locator("[data-testid='simple-quick-context-output']")
    ctx_out.wait_for(state="visible", timeout=8_000)
    assert "المحور" in ctx_out.inner_text()


# ── Part G: Suggested next action ────────────────────────────────────────────

def test_SV_suggested_next_action_appears_after_generate(page: Page, live_server: str) -> None:
    """Suggested-next-action card appears in output after generate."""
    _generate_draft_helper(page, live_server)
    expect(page.locator("[data-testid='simple-suggested-next-action']")).to_be_visible(timeout=5_000)


def test_SV_suggested_next_action_mentions_expert_when_value_available(page: Page, live_server: str) -> None:
    """When a value is calculated, next action mentions expert review."""
    _generate_draft_helper(page, live_server)
    text = page.locator("[data-testid='simple-suggested-next-action']").inner_text()
    assert "خبير" in text or "تقريرًا" in text or "راجع" in text


# ---------------------------------------------------------------------------
# Section J — Draft PDF functional tests (real /api/simple-valuation/draft-pdf)
# ---------------------------------------------------------------------------

def _mock_draft_pdf_endpoint(page: Page) -> None:
    """Mock /api/simple-valuation/draft-pdf to return minimal valid PDF bytes."""
    page.route("**/api/simple-valuation/draft-pdf", lambda r: r.fulfill(
        status=200,
        headers={"Content-Type": "application/pdf",
                 "Content-Disposition": 'attachment; filename="draft_valuation_report.pdf"'},
        body=b"%PDF-1.4 1 0 obj<</Type/Catalog>>endobj xref 0 0 trailer<</Size 1>>startxref 9 %%EOF",
    ))


def test_SV_draft_pdf_button_enabled_after_generate(page: Page, live_server: str) -> None:
    """Draft PDF button is enabled (not disabled) after a successful generate."""
    _generate_draft_helper(page, live_server)
    btn = page.locator("[data-testid='simple-draft-pdf-button']")
    expect(btn).to_be_visible(timeout=5_000)
    expect(btn).to_be_enabled()


def test_SV_draft_pdf_button_calls_backend_and_shows_status(page: Page, live_server: str) -> None:
    """Clicking the draft PDF button POSTs to the safe backend route and shows a status message."""
    _mock_draft_pdf_endpoint(page)
    _generate_draft_helper(page, live_server)

    btn = page.locator("[data-testid='simple-draft-pdf-button']")
    expect(btn).to_be_enabled(timeout=5_000)
    btn.click()

    status = page.locator("[data-testid='simple-draft-pdf-status']")
    expect(status).to_be_visible(timeout=8_000)
    # Status must show something (success or error) — not blank
    assert status.inner_text(timeout=8_000).strip() != ""


def test_SV_draft_pdf_download_link_appears_after_success(page: Page, live_server: str) -> None:
    """After a successful mock response the status area contains a download link."""
    _mock_draft_pdf_endpoint(page)
    _generate_draft_helper(page, live_server)

    page.locator("[data-testid='simple-draft-pdf-button']").click()

    dl_link = page.locator("[data-testid='simple-draft-pdf-download']")
    expect(dl_link).to_be_visible(timeout=8_000)
    href = dl_link.get_attribute("href") or ""
    # blob: URL produced by createObjectURL
    assert href.startswith("blob:") or href != ""


def test_SV_draft_pdf_no_excel_link_in_output(page: Page, live_server: str) -> None:
    """No Excel download link is exposed to ordinary users in the output area."""
    _generate_draft_helper(page, live_server)
    output_html = page.locator("[data-testid='simple-valuation-output']").inner_html(timeout=5_000)
    assert ".xlsx" not in output_html.lower()
    assert ".xlsm" not in output_html.lower()
    # The internal Excel note must say it's for expert/admin only, not a download link
    excel_note = page.locator("[data-testid='simple-internal-excel-note']")
    expect(excel_note).to_be_visible(timeout=5_000)
    assert "خبير" in excel_note.inner_text() or "إدارة" in excel_note.inner_text()


def test_SV_draft_pdf_data_gap_button_also_enabled(page: Page, live_server: str) -> None:
    """Even when API returns no market_value (data gap), the PDF button is still enabled."""
    page.route("**/api/valuation", lambda r: r.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"status": "success", "report_id": "DRAFT-GAP-J01"}),
    ))
    _go_to_simple_valuation_tab(page, live_server)
    _fill_form_minimum(page)
    page.locator("[data-testid='simple-valuation-generate']").click()
    page.locator("[data-testid='simple-valuation-output']").wait_for(state="visible", timeout=8_000)

    btn = page.locator("[data-testid='simple-draft-pdf-button']")
    expect(btn).to_be_visible(timeout=5_000)
    expect(btn).to_be_enabled()


def test_SV_draft_pdf_expert_cta_still_visible_after_pdf_click(page: Page, live_server: str) -> None:
    """Expert approval CTA remains visible after clicking the draft PDF button."""
    _mock_draft_pdf_endpoint(page)
    _generate_draft_helper(page, live_server)

    page.locator("[data-testid='simple-draft-pdf-button']").click()
    # Wait for status to appear (ensures the click completed)
    page.locator("[data-testid='simple-draft-pdf-status']").wait_for(state="visible", timeout=8_000)

    # Expert CTA must still be visible
    cta = page.locator("[data-testid='simple-valuation-expert-cta']")
    expect(cta).to_be_visible(timeout=5_000)
    assert "مراجعة" in cta.inner_text()
