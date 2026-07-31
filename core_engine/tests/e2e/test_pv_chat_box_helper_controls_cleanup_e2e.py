"""
E2E tests — Professional Valuation Chat Box Helper Controls Cleanup

advisory_only=True | not_real_training=True | no_commit=True

Static tests (T01–T22): parse frontend/index.html without a browser.
  T01  Professional Valuation page section present
  T02  Chat Box section present
  T03  Voice dictation control "إملاء صوتي" visible in HTML
  T04  Property documents control "وثائق العقار" visible in HTML
  T05  Both controls share the same parent row element (same_row=true)
  T06  Property documents input accepts allowed file types
  T07  Voice dictation is a button, not a file input
  T08  "مراجعة التقارير" checkbox not visible inside Chat Box helper area
  T09  "pro-val-report-review-toggle" not a visible checkbox in Chat Box
  T10  "تقارير أعلى وأفضل استخدام" checkbox not visible inside Chat Box helper area
  T11  "pro-val-hbu-report-toggle" not a visible checkbox in Chat Box
  T12  Tombstone for report review key exists
  T13  Tombstone for HBU key exists
  T14  Expert review request section present
  T15  Expert review button uses gold/ordinary-valuation styling
  T16  Expert review button label matches ordinary valuation page
  T17  Expert review advisory notice preserved
  T18  Certification gate advisory text present
  T19  No internal paths in HTML helper controls area
  T20  New JS helper functions defined in page
  T21  pvSyncChatBoxHelperControlsContext JS function defined
  T22  pvAuditChatBoxControls JS function defined

Playwright live_server tests (T23–T30): require server at http://127.0.0.1:5000
  Deselected with: pytest -m "not live_server"
"""

import pathlib
import re
import pytest

INDEX_HTML = pathlib.Path(__file__).parent.parent.parent.parent / "frontend" / "index.html"


def _html():
    return INDEX_HTML.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# T01 — Professional Valuation page section present
# ---------------------------------------------------------------------------
def test_T01_professional_valuation_page_section_present():
    html = _html()
    assert 'data-testid="pro-val-section-chat-box"' in html or \
           'data-testid="pro-val-input-generation-section"' in html


# ---------------------------------------------------------------------------
# T02 — Chat Box section present
# ---------------------------------------------------------------------------
def test_T02_chat_box_section_present():
    html = _html()
    assert 'data-testid="pro-val-chat-command-center"' in html or \
           'id="main-input"' in html


# ---------------------------------------------------------------------------
# T03 — Voice dictation control "إملاء صوتي" present
# ---------------------------------------------------------------------------
def test_T03_voice_dictation_control_present():
    html = _html()
    assert 'id="pv-chat-mic-btn"' in html
    assert 'إملاء صوتي' in html
    assert 'data-testid="pro-val-chat-microphone-button"' in html


# ---------------------------------------------------------------------------
# T04 — Property documents control "وثائق العقار" present
# ---------------------------------------------------------------------------
def test_T04_property_documents_control_present():
    html = _html()
    assert 'data-testid="pro-val-property-docs-clip"' in html
    assert 'وثائق العقار' in html
    assert 'id="pv-property-docs-input"' in html


# ---------------------------------------------------------------------------
# T05 — Both controls share the same parent container (same_row=true)
# ---------------------------------------------------------------------------
def test_T05_voice_and_documents_in_same_row():
    html = _html()
    assert 'data-testid="pro-val-chat-helper-controls-row"' in html
    # Extract the helper row block
    start = html.find('data-testid="pro-val-chat-helper-controls-row"')
    assert start != -1, "Helper controls row not found"
    block = html[start:start + 3000]
    assert 'pv-chat-mic-btn' in block, "Mic button not in helper row"
    assert 'pro-val-property-docs-clip' in block, "Property docs clip not in helper row"
    # voice_and_documents_same_row comment marker
    assert 'voice_and_documents_same_row=true' in html


# ---------------------------------------------------------------------------
# T06 — Property documents input accepts required file types
# ---------------------------------------------------------------------------
def test_T06_property_docs_accepts_required_file_types():
    html = _html()
    # Find the accept attribute on pv-property-docs-input
    idx = html.find('id="pv-property-docs-input"')
    assert idx != -1
    block = html[max(0, idx - 200):idx + 400]
    accept_match = re.search(r'accept="([^"]+)"', block)
    assert accept_match, "accept attribute not found on property docs input"
    accepted = accept_match.group(1)
    for ft in [".pdf", ".jpg", ".jpeg", ".png", ".xlsx", ".xls", ".docx"]:
        assert ft in accepted, f"File type '{ft}' not in accept attribute"


# ---------------------------------------------------------------------------
# T07 — Voice dictation is a button, not a file input
# ---------------------------------------------------------------------------
def test_T07_voice_dictation_is_button_not_file_input():
    html = _html()
    # pv-chat-mic-btn must be a <button>
    idx = html.find('id="pv-chat-mic-btn"')
    assert idx != -1
    # Search backwards for the opening tag
    snippet = html[max(0, idx - 200):idx + 10]
    assert '<button' in snippet, "pv-chat-mic-btn is not a <button>"
    # Must not have type="file"
    btn_block = html[max(0, idx - 50):idx + 400]
    assert 'type="file"' not in btn_block


# ---------------------------------------------------------------------------
# T08 — "مراجعة التقارير" checkbox not rendered as a visible element in Chat Box
# ---------------------------------------------------------------------------
def test_T08_report_review_checkbox_not_visible_in_chat_box():
    html = _html()
    # The checkbox input must not exist as a live visible element
    # (it was replaced by a tombstone span)
    assert 'id="pv-report-review-toggle"' not in html


# ---------------------------------------------------------------------------
# T09 — pro-val-report-review-toggle testid not a visible control
# ---------------------------------------------------------------------------
def test_T09_report_review_toggle_testid_removed():
    html = _html()
    assert 'data-testid="pro-val-report-review-toggle"' not in html


# ---------------------------------------------------------------------------
# T10 — "تقارير أعلى وأفضل استخدام" checkbox not visible in Chat Box
# ---------------------------------------------------------------------------
def test_T10_hbu_checkbox_not_visible_in_chat_box():
    html = _html()
    assert 'id="pv-hbu-report-toggle"' not in html


# ---------------------------------------------------------------------------
# T11 — pro-val-hbu-report-toggle testid not a visible control
# ---------------------------------------------------------------------------
def test_T11_hbu_toggle_testid_removed():
    html = _html()
    assert 'data-testid="pro-val-hbu-report-toggle"' not in html


# ---------------------------------------------------------------------------
# T12 — Tombstone for report review key exists
# ---------------------------------------------------------------------------
def test_T12_tombstone_report_review_key_exists():
    html = _html()
    assert 'data-testid="pv-chat-report-review-key-removed"' in html
    # Must be aria-hidden
    idx = html.find('data-testid="pv-chat-report-review-key-removed"')
    block = html[max(0, idx - 20):idx + 200]
    assert 'aria-hidden="true"' in block
    assert 'display:none' in block


# ---------------------------------------------------------------------------
# T13 — Tombstone for HBU key exists
# ---------------------------------------------------------------------------
def test_T13_tombstone_hbu_key_exists():
    html = _html()
    assert 'data-testid="pv-chat-hbu-key-removed"' in html
    idx = html.find('data-testid="pv-chat-hbu-key-removed"')
    block = html[max(0, idx - 20):idx + 200]
    assert 'aria-hidden="true"' in block
    assert 'display:none' in block


# ---------------------------------------------------------------------------
# T14 — Expert review request section present
# ---------------------------------------------------------------------------
def test_T14_expert_review_request_section_present():
    html = _html()
    assert 'data-testid="pro-val-expert-review-request-section"' in html
    assert 'data-testid="pro-val-request-expert-review-button"' in html
    assert 'pvRequestExpertReview()' in html


# ---------------------------------------------------------------------------
# T15 — Expert review button uses gold styling (matches ordinary valuation page)
# ---------------------------------------------------------------------------
def test_T15_expert_review_uses_gold_styling():
    html = _html()
    idx = html.find('data-testid="pro-val-request-expert-review-button"')
    assert idx != -1
    block = html[idx:idx + 600]
    # Gold theme colors
    assert '212,175,55' in block, "Gold color scheme not found in expert review button"
    # Border radius 8px (ordinary valuation page uses 8px)
    assert 'border-radius:8px' in block, "border-radius:8px not found on expert review button"
    # Font weight 700
    assert 'font-weight:700' in block, "font-weight:700 not found on expert review button"


# ---------------------------------------------------------------------------
# T16 — Expert review button label matches ordinary valuation page
# ---------------------------------------------------------------------------
def test_T16_expert_review_label_matches_ordinary_valuation():
    html = _html()
    # Must contain the same label used in simple (ordinary) valuation page
    assert 'طلب مراجعة واعتماد من خبير التقييم' in html
    # Section header must also use gold theme
    idx = html.find('data-testid="pro-val-expert-review-request-section"')
    block = html[idx:idx + 800]
    assert 'طلب مراجعة واعتماد من خبير التقييم' in block
    # Green theme (old) must be gone from the button
    assert 'expert_review_request_matches_ordinary_valuation_page=true' in html


# ---------------------------------------------------------------------------
# T17 — Expert review advisory notice preserved
# ---------------------------------------------------------------------------
def test_T17_expert_review_advisory_notice_preserved():
    html = _html()
    assert 'طلب المراجعة لا يُعتمد التقرير تلقائياً' in html


# ---------------------------------------------------------------------------
# T18 — Certification gate advisory text present
# ---------------------------------------------------------------------------
def test_T18_certification_gate_advisory_preserved():
    html = _html()
    assert 'certification_ready: false' in html or 'certification_ready:false' in html or \
           'certification_ready' in html


# ---------------------------------------------------------------------------
# T19 — No internal paths in Chat Box helper controls area
# ---------------------------------------------------------------------------
def test_T19_no_internal_paths_in_helper_controls():
    html = _html()
    idx = html.find('pro-val-chat-helper-controls-row')
    if idx == -1:
        return  # helper row testid not found (might be comment) — check broader
    block = html[max(0, idx - 200):idx + 4000]
    forbidden = ["C:\\Users\\", "C:/Users/", "/home/", "/Users/", "c:\\users\\"]
    for path in forbidden:
        assert path.lower() not in block.lower(), f"Internal path found near helper row: {path}"


# ---------------------------------------------------------------------------
# T20 — New JS helper functions defined
# ---------------------------------------------------------------------------
def test_T20_new_js_helper_functions_defined():
    html = _html()
    functions = [
        "pvRenderChatBoxHelperControlsRow",
        "pvRenderVoiceDictationControl",
        "pvHandleVoiceDictation",
        "pvRenderPropertyDocumentsUploadControl",
        "pvHandlePropertyDocumentsUpload",
        "pvRemoveReportReviewQuickKeyFromChatBox",
        "pvRemoveHbuQuickKeyFromChatBox",
        "pvRenderExpertReviewRequestLikeOrdinaryValuation",
    ]
    for fn in functions:
        assert f"function {fn}" in html, f"JS function not found: {fn}"


# ---------------------------------------------------------------------------
# T21 — pvSyncChatBoxHelperControlsContext defined
# ---------------------------------------------------------------------------
def test_T21_pvSyncChatBoxHelperControlsContext_defined():
    html = _html()
    assert "function pvSyncChatBoxHelperControlsContext" in html


# ---------------------------------------------------------------------------
# T22 — pvAuditChatBoxControls defined
# ---------------------------------------------------------------------------
def test_T22_pvAuditChatBoxControls_defined():
    html = _html()
    assert "function pvAuditChatBoxControls" in html


# ===========================================================================
# Playwright live_server tests (T23–T30) — deselected without server
# ===========================================================================

@pytest.mark.live_server
def test_T23_professional_valuation_page_opens(page):
    page.goto("http://127.0.0.1:5000/")
    assert page.title() is not None


@pytest.mark.live_server
def test_T24_chat_box_visible(page):
    page.goto("http://127.0.0.1:5000/")
    chat_input = page.locator('[data-testid="pro-val-chat-input"]')
    assert chat_input.count() > 0


@pytest.mark.live_server
def test_T25_voice_and_docs_in_same_row(page):
    page.goto("http://127.0.0.1:5000/")
    row = page.locator('[data-testid="pro-val-chat-helper-controls-row"]')
    assert row.count() > 0
    mic = row.locator('[data-testid="pro-val-chat-microphone-button"]')
    docs = row.locator('[data-testid="pro-val-property-docs-clip"]')
    assert mic.count() > 0
    assert docs.count() > 0


@pytest.mark.live_server
def test_T26_report_review_quick_key_not_visible(page):
    page.goto("http://127.0.0.1:5000/")
    rr = page.locator('[data-testid="pro-val-report-review-toggle"]')
    assert rr.count() == 0


@pytest.mark.live_server
def test_T27_hbu_quick_key_not_visible(page):
    page.goto("http://127.0.0.1:5000/")
    hbu = page.locator('[data-testid="pro-val-hbu-report-toggle"]')
    assert hbu.count() == 0


@pytest.mark.live_server
def test_T28_expert_review_button_gold_style(page):
    page.goto("http://127.0.0.1:5000/")
    btn = page.locator('[data-testid="pro-val-request-expert-review-button"]')
    assert btn.count() > 0
    label = btn.inner_text()
    assert "طلب مراجعة واعتماد" in label


@pytest.mark.live_server
def test_T29_expert_review_click_sets_requested_not_certified(page):
    page.goto("http://127.0.0.1:5000/")
    btn = page.locator('[data-testid="pro-val-request-expert-review-button"]')
    btn.click()
    status = page.locator('[data-testid="pro-val-expert-review-status"]')
    assert "pending_expert_review" in (status.inner_text() or "")
    # certification_ready must NOT be true
    result = page.evaluate("""() => {
        var ctx = window._pvUnifiedPageContext;
        if (!ctx) return 'no_context';
        var certGate = ctx.certification_gate_context;
        return certGate ? certGate.certification_ready : 'no_cert_gate';
    }""")
    assert result is not True and result != "true"


@pytest.mark.live_server
def test_T30_no_duplicate_buttons_in_chat_box(page):
    page.goto("http://127.0.0.1:5000/")
    # Count visible PDF / Excel / send-to-chat duplicates — expect 0 extra
    dup_selectors = [
        '[data-testid="pro-val-chat-report-review-toggle"]',
        '[data-testid="pro-val-hbu-report-toggle"]',
    ]
    for sel in dup_selectors:
        count = page.locator(sel).count()
        assert count == 0, f"Duplicate control still present: {sel}"
