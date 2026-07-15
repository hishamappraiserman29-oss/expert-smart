"""
PVS6 — Unified Professional Valuation Page Context & Outputs — E2E Browser Tests
Tests PVUPC-E01 through PVUPC-E42
Runs Playwright against the live server.
live_server fixture provided by core_engine/tests/e2e/conftest.py
"""
from __future__ import annotations

import os
import pytest
from playwright.sync_api import Page, expect

# ── output directory ───────────────────────────────────────────────────────
_SHOT_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "instance",
    "manual_review_outputs",
    "professional_valuation_unified_page_context_chat_outputs",
)


def _ensure_shot_dir():
    os.makedirs(_SHOT_DIR, exist_ok=True)


def _goto(page: Page, live_server: str) -> None:
    page.route("**/api/**", lambda r: r.fulfill(
        status=200,
        body=b'{"ok":true,"request_id":"pvupc-test-001","status":"submitted",'
             b'"chat_command_center_context":{"visible_report_selectors_count":1,'
             b'"upper_duplicate_report_selector_visible":false,'
             b'"lower_report_selector_preserved":true,'
             b'"compact_property_docs_clip":true,"microphone_restored":true,'
             b'"simulation_report_clip_available":true,'
             b'"review_report_clip_available":true,'
             b'"real_ml_training_claimed":false,"debug_tokens_visible":false,'
             b'"advisory_only":true,"certification_gates_preserved":true},'
             b'"unified_professional_valuation_page_context":{"advisory_only":true}}',
        content_type="application/json",
    ))
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator('[data-testid="professional-wizard"]').wait_for(
        state="visible", timeout=15_000
    )


def _ws(page: Page):
    return page.locator("#ws-professional")


# ── PVUPC-E01: Professional wizard section is visible ─────────────────────
def test_PVUPC_E01_professional_wizard_visible(page: Page, live_server: str):
    _goto(page, live_server)
    expect(page.locator('[data-testid="professional-wizard"]').first).to_be_visible()


# ── PVUPC-E02: Chat command center is visible ──────────────────────────────
def test_PVUPC_E02_chat_command_center_visible(page: Page, live_server: str):
    _goto(page, live_server)
    expect(_ws(page).locator('[data-testid="pro-val-chat-command-center"]').first).to_be_visible()


# ── PVUPC-E03: Only one chat command center ────────────────────────────────
def test_PVUPC_E03_single_chat_command_center(page: Page, live_server: str):
    _goto(page, live_server)
    count = _ws(page).locator('[data-testid="pro-val-chat-command-center"]').count()
    assert count == 1, f"Expected 1, got {count}"


# ── PVUPC-E04: Microphone button is visible ────────────────────────────────
def test_PVUPC_E04_microphone_button_visible(page: Page, live_server: str):
    _goto(page, live_server)
    expect(_ws(page).locator('[data-testid="pro-val-chat-microphone-button"]').first).to_be_visible()


# ── PVUPC-E05: Microphone status span is in DOM ────────────────────────────
def test_PVUPC_E05_microphone_status_in_dom(page: Page, live_server: str):
    _goto(page, live_server)
    count = _ws(page).locator('[data-testid="pro-val-chat-microphone-status"]').count()
    assert count >= 1


# ── PVUPC-E06: Property docs clip is visible and compact ──────────────────
def test_PVUPC_E06_property_docs_clip_visible(page: Page, live_server: str):
    _goto(page, live_server)
    clip = _ws(page).locator('[data-testid="pro-val-property-docs-clip"]').first
    expect(clip).to_be_visible()


# ── PVUPC-E07: Property docs clip has inline-flex style (compact) ──────────
def test_PVUPC_E07_property_docs_clip_compact(page: Page, live_server: str):
    _goto(page, live_server)
    clip = _ws(page).locator('[data-testid="pro-val-property-docs-clip"]').first
    style = clip.get_attribute("style") or ""
    assert "inline-flex" in style or "border-radius" in style, \
        f"Clip does not appear compact: style={style!r}"


# ── PVUPC-E08: Simulation report clip is visible ──────────────────────────
def test_PVUPC_E08_simulation_report_clip_visible(page: Page, live_server: str):
    _goto(page, live_server)
    expect(_ws(page).locator('[data-testid="pro-val-simulation-report-clip"]').first).to_be_visible()


# ── PVUPC-E09: Simulation clip Arabic label present ───────────────────────
def test_PVUPC_E09_simulation_clip_arabic_label(page: Page, live_server: str):
    _goto(page, live_server)
    clip = _ws(page).locator('[data-testid="pro-val-simulation-report-clip"]').first
    text = clip.inner_text()
    assert "محاكاة" in text, f"Expected Arabic label, got: {text!r}"


# ── PVUPC-E10: Review report clip is visible ──────────────────────────────
def test_PVUPC_E10_review_report_clip_visible(page: Page, live_server: str):
    _goto(page, live_server)
    expect(_ws(page).locator('[data-testid="pro-val-review-report-clip"]').first).to_be_visible()


# ── PVUPC-E11: Review clip Arabic label present ───────────────────────────
def test_PVUPC_E11_review_clip_arabic_label(page: Page, live_server: str):
    _goto(page, live_server)
    clip = _ws(page).locator('[data-testid="pro-val-review-report-clip"]').first
    text = clip.inner_text()
    assert "مراجعة" in text, f"Expected Arabic label, got: {text!r}"


# ── PVUPC-E12: Unified report action selector is visible ──────────────────
def test_PVUPC_E12_unified_selector_visible(page: Page, live_server: str):
    _goto(page, live_server)
    expect(_ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]').first).to_be_visible()


# ── PVUPC-E13: Only one visible report action selector ────────────────────
def test_PVUPC_E13_single_visible_selector(page: Page, live_server: str):
    _goto(page, live_server)
    # Upper duplicate must NOT be visible
    expect(_ws(page).locator('[data-testid="pro-val-report-level-subsection"]')).not_to_be_visible()
    # Unified must BE visible
    expect(_ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]').first).to_be_visible()


# ── PVUPC-E14: Unified selector has exactly 7 options ─────────────────────
def test_PVUPC_E14_unified_selector_7_options(page: Page, live_server: str):
    _goto(page, live_server)
    sel = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]').first
    options = sel.locator("option").all()
    assert len(options) == 7, f"Expected 7 options, got {len(options)}"


# ── PVUPC-E15: traditional_report option present ──────────────────────────
def test_PVUPC_E15_traditional_option(page: Page, live_server: str):
    _goto(page, live_server)
    sel = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]').first
    text = sel.inner_text()
    assert "تقليدي" in text


# ── PVUPC-E16: detailed_report option present ─────────────────────────────
def test_PVUPC_E16_detailed_option(page: Page, live_server: str):
    _goto(page, live_server)
    sel = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]').first
    text = sel.inner_text()
    assert "تفصيلي" in text


# ── PVUPC-E17: professional_report option present ─────────────────────────
def test_PVUPC_E17_professional_option(page: Page, live_server: str):
    _goto(page, live_server)
    sel = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]').first
    text = sel.inner_text()
    assert "احترافي" in text


# ── PVUPC-E18: simulated_uploaded_report option present ────────────────────
def test_PVUPC_E18_simulated_option(page: Page, live_server: str):
    _goto(page, live_server)
    sel = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]').first
    text = sel.inner_text()
    assert "محاكاة" in text


# ── PVUPC-E19: report_review_output option present ────────────────────────
def test_PVUPC_E19_review_option(page: Page, live_server: str):
    _goto(page, live_server)
    sel = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]').first
    text = sel.inner_text()
    assert "مراجعة" in text


# ── PVUPC-E20: hbu_analysis_report option present ─────────────────────────
def test_PVUPC_E20_hbu_option(page: Page, live_server: str):
    _goto(page, live_server)
    sel = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]').first
    text = sel.inner_text()
    assert "أعلى وأفضل" in text


# ── PVUPC-E21: standards_compliance_report option present ──────────────────
def test_PVUPC_E21_standards_option(page: Page, live_server: str):
    _goto(page, live_server)
    sel = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]').first
    text = sel.inner_text()
    assert "امتثال" in text


# ── PVUPC-E22: User PDF button visible (canonical testid) ─────────────────
def test_PVUPC_E22_user_pdf_button_visible(page: Page, live_server: str):
    _goto(page, live_server)
    expect(_ws(page).locator('[data-testid="pro-val-unified-generate-user-pdf"]').first).to_be_visible()


# ── PVUPC-E23: Admin Excel hidden for non-admin ───────────────────────────
def test_PVUPC_E23_admin_excel_hidden(page: Page, live_server: str):
    _goto(page, live_server)
    expect(_ws(page).locator('[data-testid="pro-val-unified-generate-admin-excel"]')).not_to_be_visible()


# ── PVUPC-E24: Selected output button visible ──────────────────────────────
def test_PVUPC_E24_selected_output_button_visible(page: Page, live_server: str):
    _goto(page, live_server)
    expect(_ws(page).locator('[data-testid="pro-val-unified-generate-selected-output"]').first).to_be_visible()


# ── PVUPC-E25: Selecting simulated shows guidance ─────────────────────────
def test_PVUPC_E25_simulated_shows_guidance(page: Page, live_server: str):
    _goto(page, live_server)
    sel = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]').first
    sel.select_option("simulated_uploaded_report")
    page.wait_for_timeout(300)
    guidance = _ws(page).locator('[data-testid="pro-val-chat-action-guidance"]').first
    assert guidance.inner_text() != ""


# ── PVUPC-E26: Selecting review shows guidance ────────────────────────────
def test_PVUPC_E26_review_shows_guidance(page: Page, live_server: str):
    _goto(page, live_server)
    sel = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]').first
    sel.select_option("report_review_output")
    page.wait_for_timeout(300)
    guidance = _ws(page).locator('[data-testid="pro-val-chat-action-guidance"]').first
    assert guidance.inner_text() != ""


# ── PVUPC-E27: Selecting HBU shows guidance ───────────────────────────────
def test_PVUPC_E27_hbu_shows_guidance(page: Page, live_server: str):
    _goto(page, live_server)
    sel = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]').first
    sel.select_option("hbu_analysis_report")
    page.wait_for_timeout(300)
    guidance = _ws(page).locator('[data-testid="pro-val-chat-action-guidance"]').first
    assert guidance.inner_text() != ""


# ── PVUPC-E28: Selecting standards shows guidance ─────────────────────────
def test_PVUPC_E28_standards_shows_guidance(page: Page, live_server: str):
    _goto(page, live_server)
    sel = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]').first
    sel.select_option("standards_compliance_report")
    page.wait_for_timeout(300)
    guidance = _ws(page).locator('[data-testid="pro-val-chat-action-guidance"]').first
    assert guidance.inner_text() != ""


# ── PVUPC-E29: Chat input visible ─────────────────────────────────────────
def test_PVUPC_E29_chat_input_visible(page: Page, live_server: str):
    _goto(page, live_server)
    expect(_ws(page).locator('[data-testid="pro-val-chat-input"]').first).to_be_visible()


# ── PVUPC-E30: No internal paths in DOM ───────────────────────────────────
def test_PVUPC_E30_no_internal_paths_dom(page: Page, live_server: str):
    _goto(page, live_server)
    html = page.evaluate("document.body.innerHTML")
    bad = ["C:\\Users\\", "/home/", "core_engine/instance/", "__pycache__"]
    for b in bad:
        assert b not in html, f"Internal path in DOM: {b!r}"


# ── PVUPC-E31: No debug tokens in visible text ────────────────────────────
def test_PVUPC_E31_no_debug_tokens_visible(page: Page, live_server: str):
    _goto(page, live_server)
    text = page.evaluate("document.body.innerText")
    bad = ["market_value ·", "habu_value ·", "confidence_score ·", "· ifrs_level"]
    for b in bad:
        assert b not in text, f"Debug token visible: {b!r}"


# ── PVUPC-E32: No duplicate chat-input testids ────────────────────────────
def test_PVUPC_E32_no_duplicate_chat_input(page: Page, live_server: str):
    _goto(page, live_server)
    count = _ws(page).locator('[data-testid="pro-val-chat-input"]').count()
    assert count == 1, f"Duplicate chat-input found: {count}"


# ── PVUPC-E33: No duplicate unified selector testids ──────────────────────
def test_PVUPC_E33_no_duplicate_unified_selector(page: Page, live_server: str):
    _goto(page, live_server)
    # Only the hidden compat spans plus the real select — real ones are selects
    visible_selects = _ws(page).locator(
        'select[data-testid="pro-val-unified-analyze-generate-reports-select"]'
    )
    count = visible_selects.count()
    assert count == 1, f"Expected 1 unified selector <select>, found {count}"


# ── PVUPC-E34: Old pvr-report-type-main NOT visible ───────────────────────
def test_PVUPC_E34_old_upper_selector_not_visible(page: Page, live_server: str):
    _goto(page, live_server)
    expect(_ws(page).locator('[data-testid="pro-val-report-level-subsection"]')).not_to_be_visible()


# ── PVUPC-E35: Backward-compat span pro-val-report-type-select in DOM ──────
def test_PVUPC_E35_compat_span_in_dom(page: Page, live_server: str):
    _goto(page, live_server)
    count = _ws(page).locator('[data-testid="pro-val-report-type-select"]').count()
    assert count >= 1, "Backward-compat hidden span not in DOM"
    # Must not be visible
    expect(_ws(page).locator('[data-testid="pro-val-report-type-select"]').first).not_to_be_visible()


# ── PVUPC-E36: Property docs upload input in DOM ──────────────────────────
def test_PVUPC_E36_property_docs_upload_in_dom(page: Page, live_server: str):
    _goto(page, live_server)
    count = _ws(page).locator('[data-testid="pro-val-property-docs-upload"]').count()
    assert count >= 1


# ── PVUPC-E37: Simulation report upload input in DOM ──────────────────────
def test_PVUPC_E37_simulation_upload_in_dom(page: Page, live_server: str):
    _goto(page, live_server)
    count = _ws(page).locator('[data-testid="pro-val-simulation-report-upload"]').count()
    assert count >= 1


# ── PVUPC-E38: Review report upload input in DOM ──────────────────────────
def test_PVUPC_E38_review_upload_in_dom(page: Page, live_server: str):
    _goto(page, live_server)
    count = _ws(page).locator('[data-testid="pro-val-review-report-upload"]').count()
    assert count >= 1


# ── PVUPC-E39: Screenshot — chat toolbar overview ─────────────────────────
def test_PVUPC_E39_screenshot_chat_toolbar(page: Page, live_server: str):
    _ensure_shot_dir()
    _goto(page, live_server)
    toolbar = _ws(page).locator('[data-testid="pro-val-chat-command-center"]').first
    toolbar.screenshot(path=os.path.join(_SHOT_DIR, "01_chat_toolbar_overview.png"))


# ── PVUPC-E40: Screenshot — compact clips area ────────────────────────────
def test_PVUPC_E40_screenshot_compact_clips(page: Page, live_server: str):
    _ensure_shot_dir()
    _goto(page, live_server)
    page.screenshot(path=os.path.join(_SHOT_DIR, "02_compact_clips_area.png"),
                    full_page=False)


# ── PVUPC-E41: Screenshot — unified report selector ──────────────────────
def test_PVUPC_E41_screenshot_unified_selector(page: Page, live_server: str):
    _ensure_shot_dir()
    _goto(page, live_server)
    sel = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]').first
    sel.screenshot(path=os.path.join(_SHOT_DIR, "03_unified_report_selector.png"))


# ── PVUPC-E42: Screenshot — simulated guidance active ─────────────────────
def test_PVUPC_E42_screenshot_simulated_guidance(page: Page, live_server: str):
    _ensure_shot_dir()
    _goto(page, live_server)
    sel = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]').first
    sel.select_option("simulated_uploaded_report")
    page.wait_for_timeout(400)
    page.screenshot(path=os.path.join(_SHOT_DIR, "04_simulated_guidance_active.png"),
                    full_page=False)
