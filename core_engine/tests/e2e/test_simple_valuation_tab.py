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
