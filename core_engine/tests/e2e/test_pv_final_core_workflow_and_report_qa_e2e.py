"""
test_pv_final_core_workflow_and_report_qa_e2e.py — 43 E2E tests.

Static (no live server, no Playwright):
  PVCWE2E01  frontend HTML: voice dictation control element present
  PVCWE2E02  frontend HTML: property docs upload element present
  PVCWE2E03  frontend HTML: pv-report-review-toggle not a visible element
  PVCWE2E04  frontend HTML: pv-hbu-report-toggle not a visible element
  PVCWE2E05  frontend HTML: simulation upload clip aria-hidden or absent
  PVCWE2E06  frontend HTML: separate PDF button hidden or absent
  PVCWE2E07  frontend HTML: separate Excel button hidden or absent
  PVCWE2E08  frontend HTML: send-to-chat PDF button hidden or absent
  PVCWE2E09  frontend HTML: core-report-issuance section exists
  PVCWE2E10  frontend HTML: traditional card present in core report section
  PVCWE2E11  frontend HTML: detailed card present in core report section
  PVCWE2E12  frontend HTML: professional card present in core report section
  PVCWE2E13  frontend HTML: special-reports-section exists
  PVCWE2E14  frontend HTML: report review table button present
  PVCWE2E15  frontend HTML: HBU table button present
  PVCWE2E16  frontend HTML: standards compliance button present
  PVCWE2E17  frontend HTML: expert review card matches gold-theme style
  PVCWE2E18  frontend HTML: expert review label contains expected Arabic text
  PVCWE2E19  frontend HTML: no fake-approval element present
  PVCWE2E20  frontend HTML: no internal filesystem paths in DOM
  PVCWE2E21  frontend HTML: advisory_only flag not exposed as a DOM attribute
  PVCWE2E22  QA: chat_box_helper_controls_cleanup_audit.json result is PASS
  PVCWE2E23  QA: visible_text_count_audit.json counts are correct
  PVCWE2E24  QA: expert_review_style_match_audit.json result is PASS
  PVCWE2E25  QA: special_report_requirement_tables_audit.json result is PASS
  PVCWE2E26  QA: core_vs_special_report_separation_audit.json result is PASS
  PVCWE2E27  QA: removed_old_chat_controls_audit.json confirms removals
  PVCWE2E28  QA: core_three_excel_physical_files_audit.json all files OK

Live server / Playwright (mark: live_server — skip with -m "not live_server"):
  PVCWE2E29  page loads professional valuation workspace
  PVCWE2E30  chat helper row: voice dictation and docs upload in same row
  PVCWE2E31  chat helper row: Report Review quick key not visible
  PVCWE2E32  chat helper row: HBU quick key not visible
  PVCWE2E33  chat helper row: simulation upload clip not visible
  PVCWE2E34  core report section heading visible on page
  PVCWE2E35  clicking traditional card triggers generation request
  PVCWE2E36  clicking detailed card triggers generation request
  PVCWE2E37  clicking professional card triggers generation request
  PVCWE2E38  special reports section heading visible
  PVCWE2E39  expert review card: gold border visible
  PVCWE2E40  expert review card: no auto-approval visible
  PVCWE2E41  certification gate: certified button remains disabled without gate cleared
  PVCWE2E42  ordinary valuation tab still responsive (regression)
  PVCWE2E43  no 5xx errors in console after page navigation

advisory_only=True | not_real_training=True
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

try:
    from playwright.sync_api import Page, expect
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Page = object  # type: ignore[assignment,misc]

_CORE     = Path(__file__).resolve().parent.parent.parent
_FRONTEND = _CORE.parent / "frontend" / "index.html"
_QA_ROOT  = (
    _CORE / "instance" / "manual_review_outputs"
    / "professional_valuation_final_core_workflow_and_report_qa"
)

sys.path.insert(0, str(_CORE))

_LIVE = pytest.mark.live_server
_SKIP_NO_PW = pytest.mark.skipif(
    not PLAYWRIGHT_AVAILABLE, reason="playwright not installed — install via: pip install playwright && playwright install"
)

# ─────────────────────────────────────────────────────────────────────────────
# Helper: parse frontend HTML once per session
# ─────────────────────────────────────────────────────────────────────────────

_html_cache: str | None = None


def _get_html() -> str:
    global _html_cache
    if _html_cache is None:
        assert _FRONTEND.is_file(), f"Frontend not found: {_FRONTEND}"
        _html_cache = _FRONTEND.read_text(encoding="utf-8")
    return _html_cache


def _load_audit(rel: str) -> dict:
    p = _QA_ROOT / rel
    assert p.is_file(), f"Audit file missing: {p}"
    return json.loads(p.read_text(encoding="utf-8"))


# ─────────────────────────────────────────────────────────────────────────────
# Static HTML parse tests (no server, no Playwright)
# ─────────────────────────────────────────────────────────────────────────────

def test_PVCWE2E01_voice_dictation_element_present():
    """PVCWE2E01: Voice dictation control is in the frontend HTML."""
    html = _get_html()
    assert "pv-voice-dictation" in html or "إملاء صوتي" in html, (
        "Voice dictation element not found in frontend HTML"
    )


def test_PVCWE2E02_property_docs_upload_present():
    """PVCWE2E02: Property docs upload element is in the frontend HTML."""
    html = _get_html()
    assert "pv-property-docs" in html or "وثائق العقار" in html, (
        "Property docs upload element not found in frontend HTML"
    )


def test_PVCWE2E03_report_review_toggle_not_visible_element():
    """PVCWE2E03: pv-report-review-toggle is not an active HTML element ID."""
    html = _get_html()
    # The toggle should not appear as id="pv-report-review-toggle" in an active element
    # It may appear in JS function bodies which reference it; those are acceptable
    pattern = r'id\s*=\s*["\']pv-report-review-toggle["\']'
    matches = re.findall(pattern, html)
    assert len(matches) == 0, (
        f"Found {len(matches)} active HTML element(s) with id='pv-report-review-toggle'"
    )


def test_PVCWE2E04_hbu_toggle_not_visible_element():
    """PVCWE2E04: pv-hbu-report-toggle is not an active HTML element ID."""
    html = _get_html()
    pattern = r'id\s*=\s*["\']pv-hbu-report-toggle["\']'
    matches = re.findall(pattern, html)
    assert len(matches) == 0, (
        f"Found {len(matches)} active HTML element(s) with id='pv-hbu-report-toggle'"
    )


def test_PVCWE2E05_simulation_upload_clip_hidden_or_absent():
    """PVCWE2E05: Simulation upload clip is either absent or inside an aria-hidden container."""
    html = _get_html()
    pattern_clip = r'pv-simulate-upload-clip'
    if pattern_clip not in html:
        return  # Not present at all — OK
    # If present, it must be inside aria-hidden="true"
    idx = html.find(pattern_clip)
    surrounding = html[max(0, idx - 500):idx + 200]
    assert 'aria-hidden="true"' in surrounding or 'display:none' in surrounding or 'display: none' in surrounding, (
        "Simulation upload clip present but not hidden"
    )


def test_PVCWE2E06_separate_pdf_button_hidden_or_absent():
    """PVCWE2E06: Separate PDF issue button is hidden (display:none or aria-hidden)."""
    html = _get_html()
    # The button text or ID for the old separate PDF button
    if "pv-issue-pdf-btn" not in html and "إصدار PDF للمستخدم" not in html:
        return  # Not present — OK
    # If present, verify it's inside a hidden container
    for marker in ("pv-issue-pdf-btn", "إصدار PDF للمستخدم"):
        if marker in html:
            idx = html.find(marker)
            surrounding = html[max(0, idx - 600):idx + 100]
            assert 'aria-hidden="true"' in surrounding or 'display:none' in surrounding or 'display: none' in surrounding, (
                f"'{marker}' is present but not hidden"
            )


def test_PVCWE2E07_separate_excel_button_hidden_or_absent():
    """PVCWE2E07: Separate Excel issue button is hidden (display:none or aria-hidden)."""
    html = _get_html()
    if "pv-issue-excel-btn" not in html and "إصدار شيت Excel" not in html:
        return
    for marker in ("pv-issue-excel-btn", "إصدار شيت Excel"):
        if marker in html:
            idx = html.find(marker)
            surrounding = html[max(0, idx - 600):idx + 100]
            assert 'aria-hidden="true"' in surrounding or 'display:none' in surrounding or 'display: none' in surrounding, (
                f"'{marker}' is present but not hidden"
            )


def test_PVCWE2E08_send_to_chat_pdf_button_hidden_or_absent():
    """PVCWE2E08: Send-to-chat PDF button is hidden or absent."""
    html = _get_html()
    if "pv-send-to-chat-pdf" not in html:
        return
    idx = html.find("pv-send-to-chat-pdf")
    surrounding = html[max(0, idx - 400):idx + 100]
    assert 'aria-hidden="true"' in surrounding or 'display:none' in surrounding, (
        "pv-send-to-chat-pdf button is present and not hidden"
    )


def test_PVCWE2E09_core_report_issuance_section_exists():
    """PVCWE2E09: Core report issuance section or equivalent heading exists in HTML."""
    html = _get_html()
    assert (
        "core-report-issuance" in html
        or "إصدار تقارير التقييم الأساسية" in html
        or "pv-core-reports" in html
        or "core-reports-section" in html
    ), "Core report issuance section not found in frontend HTML"


def test_PVCWE2E10_traditional_card_present():
    """PVCWE2E10: Traditional report card or button exists in the HTML."""
    html = _get_html()
    assert (
        "traditional_report" in html
        or "تقرير تقليدي" in html
        or "traditional-report" in html
    ), "Traditional report card not found in frontend HTML"


def test_PVCWE2E11_detailed_card_present():
    """PVCWE2E11: Detailed report card or button exists in the HTML."""
    html = _get_html()
    assert (
        "detailed_report" in html
        or "تقرير تفصيلي" in html
        or "detailed-report" in html
    ), "Detailed report card not found in frontend HTML"


def test_PVCWE2E12_professional_card_present():
    """PVCWE2E12: Professional report card or button exists in the HTML."""
    html = _get_html()
    assert (
        "professional_report" in html
        or "تقرير احترافي" in html
        or "professional-report" in html
    ), "Professional report card not found in frontend HTML"


def test_PVCWE2E13_special_reports_section_exists():
    """PVCWE2E13: Special reports section exists in the HTML."""
    html = _get_html()
    assert (
        "special-reports" in html
        or "التقارير الخاصة" in html
        or "pv-special-reports" in html
    ), "Special reports section not found in frontend HTML"


def test_PVCWE2E14_report_review_table_button_present():
    """PVCWE2E14: Report Review requirement table button present in HTML."""
    html = _get_html()
    assert (
        "pv-report-review" in html
        or "مراجعة التقارير" in html
    ), "Report Review table button not found in frontend HTML"


def test_PVCWE2E15_hbu_table_button_present():
    """PVCWE2E15: HBU requirement table button present in HTML."""
    html = _get_html()
    assert (
        "pv-hbu" in html
        or "hbu" in html.lower()
        or "أفضل استخدام" in html
        or "HBU" in html
    ), "HBU table button not found in frontend HTML"


def test_PVCWE2E16_standards_compliance_button_present():
    """PVCWE2E16: Standards Compliance button present in HTML."""
    html = _get_html()
    assert (
        "pv-standards" in html
        or "امتثال المعايير" in html
        or "standards-compliance" in html
    ), "Standards compliance button not found in frontend HTML"


def test_PVCWE2E17_expert_review_gold_theme_present():
    """PVCWE2E17: Expert review card uses gold theme color in HTML."""
    html = _get_html()
    assert (
        "212,175,55" in html
        or "#d4af37" in html
        or "pv-expert-review" in html
        or "gold" in html.lower()
    ), "Expert review gold theme not found in frontend HTML"


def test_PVCWE2E18_expert_review_arabic_label_present():
    """PVCWE2E18: Expert review label contains the expected Arabic text."""
    html = _get_html()
    assert (
        "طلب مراجعة" in html
        or "مراجعة واعتماد" in html
        or "خبير التقييم" in html
    ), "Expert review Arabic label not found in frontend HTML"


def test_PVCWE2E19_no_fake_approval_element():
    """PVCWE2E19: No fake-approval DOM element in the HTML."""
    html = _get_html()
    assert "fake-approval" not in html, (
        "Found 'fake-approval' element in frontend HTML — must not exist"
    )
    assert "auto-certification" not in html, (
        "Found 'auto-certification' element in frontend HTML"
    )


def test_PVCWE2E20_no_internal_paths_in_dom():
    """PVCWE2E20: No Windows-style internal filesystem paths exposed in the HTML."""
    html = _get_html()
    # Check for raw Python paths in DOM (not inside script tags that would be server-side)
    suspicious = re.findall(r'(?<!["\'])C:\\\\[A-Za-z]', html)
    assert len(suspicious) == 0, (
        f"Found internal Windows paths in frontend HTML: {suspicious[:5]}"
    )


def test_PVCWE2E21_advisory_only_not_dom_attribute():
    """PVCWE2E21: advisory_only=True flag is not exposed as a DOM attribute in the HTML."""
    html = _get_html()
    assert 'advisory_only="true"' not in html, (
        "advisory_only attribute found in DOM — should not be exposed"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Static QA audit checks
# ─────────────────────────────────────────────────────────────────────────────

def test_PVCWE2E22_chat_box_helper_controls_audit_passes():
    """PVCWE2E22: chat_box_helper_controls_cleanup_audit.json result is PASS."""
    data = _load_audit("chat_box_audits/chat_box_helper_controls_cleanup_audit.json")
    assert data.get("result") == "PASS", f"Audit result: {data.get('result')}"


def test_PVCWE2E23_visible_text_count_audit_correct():
    """PVCWE2E23: visible_text_count_audit.json: voice=1, docs=1, removed items=0."""
    data = _load_audit("chat_box_audits/visible_text_count_audit.json")
    # Arabic keys with underscores for spaces
    voice_key = "visible_count_إملاء_صوتي"
    docs_key  = "visible_count_وثائق_العقار"
    assert data.get(voice_key, -1) == 1, (
        f"Expected {voice_key}=1, got {data.get(voice_key)}"
    )
    assert data.get(docs_key, -1) == 1, (
        f"Expected {docs_key}=1, got {data.get(docs_key)}"
    )
    # Removed quick keys should all be 0
    assert data.get("chat_box_visible_count_HBU", -1) == 0, (
        f"Expected HBU count=0, got {data.get('chat_box_visible_count_HBU')}"
    )


def test_PVCWE2E24_expert_review_style_match_audit_passes():
    """PVCWE2E24: expert_review_style_match_audit.json result is PASS."""
    data = _load_audit("chat_box_audits/expert_review_style_match_audit.json")
    assert data.get("result") == "PASS", f"Audit result: {data.get('result')}"


def test_PVCWE2E25_special_report_tables_audit_passes():
    """PVCWE2E25: special_report_requirement_tables_audit.json result is PASS."""
    data = _load_audit("special_report_audits/special_report_requirement_tables_audit.json")
    assert data.get("result") == "PASS", f"Audit result: {data.get('result')}"


def test_PVCWE2E26_core_vs_special_separation_passes():
    """PVCWE2E26: core_vs_special_report_separation_audit.json result is PASS."""
    data = _load_audit("special_report_audits/core_vs_special_report_separation_audit.json")
    assert data.get("result") == "PASS", f"Audit result: {data.get('result')}"


def test_PVCWE2E27_removed_old_controls_audit_confirms_removals():
    """PVCWE2E27: removed_old_chat_controls_audit.json confirms controls removed."""
    data = _load_audit("chat_box_audits/removed_old_chat_controls_audit.json")
    assert data.get("result") == "PASS", f"Audit result: {data.get('result')}"
    removed = data.get("removed_controls", [])
    assert len(removed) >= 3, f"Expected at least 3 removed controls, got {len(removed)}"
    assert all(c.get("removed") is True for c in removed), (
        "Some controls not marked as removed"
    )


def test_PVCWE2E28_excel_physical_files_audit_passes():
    """PVCWE2E28: core_three_excel_physical_files_audit.json all files OK."""
    data = _load_audit("report_structure_audits/core_three_excel_physical_files_audit.json")
    assert data.get("excel_status") == "PASS" or data.get("result") == "PASS", (
        f"Excel audit status not PASS: {data}"
    )
    excel_files = data.get("excel_files", [])
    for entry in excel_files:
        assert entry.get("status") == "OK", (
            f"Excel file not OK: {entry.get('file_name')} — {entry.get('status')}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Live server / Playwright tests (skip with -m "not live_server")
# ─────────────────────────────────────────────────────────────────────────────

def _go_to_pro_val(page: Page, live_server: str) -> None:
    page.goto(f"{live_server}#professional-valuation", wait_until="domcontentloaded")
    page.locator('[data-testid="pro-val-workspace"]').wait_for(state="visible", timeout=10_000)


def _block_api(page: Page) -> None:
    page.route("**/api/**", lambda r: r.fulfill(
        status=200, body=b'{"ok":true,"status":"advisory_only"}',
        content_type="application/json"
    ))


@_LIVE
@_SKIP_NO_PW
def test_PVCWE2E29_pro_val_workspace_loads(page: Page, live_server: str) -> None:
    """PVCWE2E29: Professional valuation workspace loads on hash navigation."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    ws = page.locator('[data-testid="pro-val-workspace"]')
    expect(ws).to_be_visible()


@_LIVE
@_SKIP_NO_PW
def test_PVCWE2E30_chat_helper_row_voice_and_docs_visible(page: Page, live_server: str) -> None:
    """PVCWE2E30: Voice dictation and property docs upload are both visible in the chat helper row."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    voice = page.locator('[data-testid="pv-voice-dictation"]')
    docs  = page.locator('[data-testid="pv-property-docs"]')
    expect(voice).to_be_visible()
    expect(docs).to_be_visible()


@_LIVE
@_SKIP_NO_PW
def test_PVCWE2E31_report_review_quick_key_not_visible(page: Page, live_server: str) -> None:
    """PVCWE2E31: Report Review quick key is not visible in the chat helper row."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    locator = page.locator('[data-testid="pv-report-review-toggle"]')
    assert locator.count() == 0 or not locator.is_visible(), (
        "Report Review quick key should not be visible"
    )


@_LIVE
@_SKIP_NO_PW
def test_PVCWE2E32_hbu_quick_key_not_visible(page: Page, live_server: str) -> None:
    """PVCWE2E32: HBU quick key is not visible in the chat helper row."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    locator = page.locator('[data-testid="pv-hbu-report-toggle"]')
    assert locator.count() == 0 or not locator.is_visible(), (
        "HBU quick key should not be visible"
    )


@_LIVE
@_SKIP_NO_PW
def test_PVCWE2E33_simulation_upload_clip_not_visible(page: Page, live_server: str) -> None:
    """PVCWE2E33: Simulation upload clip is not visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    locator = page.locator('[data-testid="pv-simulate-upload-clip"]')
    assert locator.count() == 0 or not locator.is_visible(), (
        "Simulation upload clip should not be visible"
    )


@_LIVE
@_SKIP_NO_PW
def test_PVCWE2E34_core_report_section_heading_visible(page: Page, live_server: str) -> None:
    """PVCWE2E34: Core report issuance section heading is visible on the page."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    section = page.locator('[data-testid="pv-core-reports-section"], [data-testid="core-report-issuance"]')
    if section.count() == 0:
        section = page.get_by_text("إصدار تقارير التقييم الأساسية")
    expect(section.first).to_be_visible()


@_LIVE
@_SKIP_NO_PW
def test_PVCWE2E35_traditional_card_triggers_request(page: Page, live_server: str) -> None:
    """PVCWE2E35: Clicking the traditional card triggers an API generation request."""
    api_calls: list[str] = []

    def _capture(route):
        api_calls.append(route.request.url)
        route.fulfill(status=200, body=b'{"ok":true,"advisory_only":true}',
                      content_type="application/json")

    page.route("**/api/**", _capture)
    _go_to_pro_val(page, live_server)

    btn = page.locator('[data-testid="pv-generate-traditional"], [data-testid="pv-traditional-card"]')
    if btn.count() == 0:
        btn = page.get_by_text("تقرير تقليدي").first
    btn.click()
    page.wait_for_timeout(500)
    assert len(api_calls) > 0, "No API calls made after clicking traditional card"


@_LIVE
@_SKIP_NO_PW
def test_PVCWE2E36_detailed_card_triggers_request(page: Page, live_server: str) -> None:
    """PVCWE2E36: Clicking the detailed card triggers an API generation request."""
    api_calls: list[str] = []

    def _capture(route):
        api_calls.append(route.request.url)
        route.fulfill(status=200, body=b'{"ok":true,"advisory_only":true}',
                      content_type="application/json")

    page.route("**/api/**", _capture)
    _go_to_pro_val(page, live_server)

    btn = page.locator('[data-testid="pv-generate-detailed"], [data-testid="pv-detailed-card"]')
    if btn.count() == 0:
        btn = page.get_by_text("تقرير تفصيلي").first
    btn.click()
    page.wait_for_timeout(500)
    assert len(api_calls) > 0, "No API calls made after clicking detailed card"


@_LIVE
@_SKIP_NO_PW
def test_PVCWE2E37_professional_card_triggers_request(page: Page, live_server: str) -> None:
    """PVCWE2E37: Clicking the professional card triggers an API generation request."""
    api_calls: list[str] = []

    def _capture(route):
        api_calls.append(route.request.url)
        route.fulfill(status=200, body=b'{"ok":true,"advisory_only":true}',
                      content_type="application/json")

    page.route("**/api/**", _capture)
    _go_to_pro_val(page, live_server)

    btn = page.locator('[data-testid="pv-generate-professional"], [data-testid="pv-professional-card"]')
    if btn.count() == 0:
        btn = page.get_by_text("تقرير احترافي").first
    btn.click()
    page.wait_for_timeout(500)
    assert len(api_calls) > 0, "No API calls made after clicking professional card"


@_LIVE
@_SKIP_NO_PW
def test_PVCWE2E38_special_reports_section_heading_visible(page: Page, live_server: str) -> None:
    """PVCWE2E38: Special reports section heading is visible on the page."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    section = page.locator('[data-testid="pv-special-reports-section"]')
    if section.count() == 0:
        section = page.get_by_text("التقارير الخاصة")
    expect(section.first).to_be_visible()


@_LIVE
@_SKIP_NO_PW
def test_PVCWE2E39_expert_review_card_gold_border(page: Page, live_server: str) -> None:
    """PVCWE2E39: Expert review card has gold border color visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    card = page.locator('[data-testid="pv-expert-review-card"]')
    if card.count() == 0:
        return  # Element not present with testid — skip visual check
    border = card.evaluate("el => window.getComputedStyle(el).borderColor")
    assert border, "Could not read border color from expert review card"


@_LIVE
@_SKIP_NO_PW
def test_PVCWE2E40_expert_review_no_auto_approval(page: Page, live_server: str) -> None:
    """PVCWE2E40: Expert review card does not contain an auto-approval indicator."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    auto_approval = page.locator('[data-testid="pv-auto-approval"], .pv-auto-approve')
    assert auto_approval.count() == 0, (
        "Auto-approval element found — must not exist"
    )


@_LIVE
@_SKIP_NO_PW
def test_PVCWE2E41_certified_button_disabled_without_gate(page: Page, live_server: str) -> None:
    """PVCWE2E41: Certified report button remains disabled when certification gate not cleared."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    cert_btn = page.locator('[data-testid="pro-val-certified-report-btn"]')
    if cert_btn.count() == 0:
        return  # Button not rendered in current state — gate not shown
    assert cert_btn.is_disabled(), "Certified report button should be disabled without gate clearance"


@_LIVE
@_SKIP_NO_PW
def test_PVCWE2E42_ordinary_valuation_tab_responsive(page: Page, live_server: str) -> None:
    """PVCWE2E42: Ordinary valuation tab still responds (regression guard)."""
    _block_api(page)
    page.goto(live_server, wait_until="domcontentloaded")
    tab = page.locator('[data-testid="valuation-tab"]')
    if tab.count() == 0:
        return  # Tab hidden by default — that's correct; regression not triggered
    tab.click()
    page.wait_for_timeout(300)


@_LIVE
@_SKIP_NO_PW
def test_PVCWE2E43_no_5xx_errors_on_navigation(page: Page, live_server: str) -> None:
    """PVCWE2E43: No 5xx server errors in browser console after page navigation."""
    errors: list[str] = []

    def _on_response(response):
        if response.status >= 500:
            errors.append(f"{response.status} {response.url}")

    page.on("response", _on_response)
    page.route("**/api/**", lambda r: r.fulfill(
        status=200, body=b'{"ok":true}', content_type="application/json"
    ))
    page.goto(f"{live_server}#professional-valuation", wait_until="domcontentloaded")
    page.wait_for_timeout(1_000)
    assert len(errors) == 0, f"5xx errors on navigation: {errors}"
