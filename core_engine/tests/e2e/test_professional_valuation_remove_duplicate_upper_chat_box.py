"""
DCUB E2E Browser Tests — 29 tests
Professional Valuation Page — Remove Duplicate Upper Chat Box (DCUB)

Proves:
- Upper duplicate 'صندوق الشات والمخرجات' container is not visible (DCUB-E01..E24)
- Real lower ai-section chat box is visible and usable (DCUB-E25..E26)
- DOM structure integrity maintained (DCUB-E27..E29)

Rule 30: Browser visibility proven with real Playwright assertions.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


# ── Helpers ───────────────────────────────────────────────────────────────────

def _goto(page: Page, live_server: str) -> None:
    page.route("**/api/**", lambda r: r.fulfill(
        status=200, body=b'{"ok":true}', content_type="application/json"
    ))
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator('[data-testid="professional-wizard"]').wait_for(
        state="visible", timeout=15_000
    )


def _ws(page: Page):
    """Scope locators to the professional workspace."""
    return page.locator("#ws-professional")


# ── DCUB-E01..E03: Duplicate header / subtitle removed ───────────────────────

def test_DCUB_E01_upper_duplicate_section_header_not_visible(page: Page, live_server: str) -> None:
    """DCUB-E01: '5. صندوق الشات والمخرجات' heading is not visible anywhere on the page."""
    _goto(page, live_server)
    # The header was inside a visible div with gold border; it is now gone
    header = _ws(page).locator("text=5. صندوق الشات والمخرجات")
    expect(header).not_to_be_visible()


def test_DCUB_E02_chat_box_report_output_actions_subtitle_not_visible(page: Page, live_server: str) -> None:
    """DCUB-E02: 'Chat Box & Report Output Actions' subtitle is not visible."""
    _goto(page, live_server)
    subtitle = _ws(page).locator("text=Chat Box & Report Output Actions")
    expect(subtitle).not_to_be_visible()


def test_DCUB_E03_corrupted_subtitle_chot_box_not_visible(page: Page, live_server: str) -> None:
    """DCUB-E03: Corrupted 'Chot Box' / 'Chot Ber' subtitle is not visible."""
    _goto(page, live_server)
    # Use evaluate to check visible text doesn't contain corrupted strings
    body_text: str = page.evaluate("document.body.innerText")
    assert "Chot Box" not in body_text, "Corrupted subtitle 'Chot Box' found in visible DOM"
    assert "Chot Ber" not in body_text, "Corrupted subtitle 'Chot Ber' found in visible DOM"
    assert "Rapert Dutgut" not in body_text, "Corrupted subtitle 'Rapert Dutgut' found in visible DOM"
    assert "Augort Dutgut" not in body_text, "Corrupted subtitle 'Augort Dutgut' found in visible DOM"


# ── DCUB-E04..E05: Input method section removed ──────────────────────────────

def test_DCUB_E04_input_method_selector_not_visible(page: Page, live_server: str) -> None:
    """DCUB-E04: 'طريقة الإدخال' input mode select is not visible (was in duplicate block)."""
    _goto(page, live_server)
    sel = _ws(page).locator('[data-testid="pro-val-vis-input-mode-select"]')
    expect(sel).not_to_be_visible()


def test_DCUB_E05_structured_browser_input_option_not_visible(page: Page, live_server: str) -> None:
    """DCUB-E05: 'أ. الإدخال المنظم من المتصفح' option not visible."""
    _goto(page, live_server)
    opt = _ws(page).locator('[data-testid="pro-val-vis-input-mode-structured"]')
    expect(opt).not_to_be_visible()


# ── DCUB-E06..E08: Upload controls in duplicate block removed ─────────────────

def test_DCUB_E06_upload_evidence_control_not_visible(page: Page, live_server: str) -> None:
    """DCUB-E06: 'رفع وثائق الإثبات والملكية' upload control not visible."""
    _goto(page, live_server)
    el = _ws(page).locator('[data-testid="pro-val-vis-upload-evidence"]')
    expect(el).not_to_be_visible()


def test_DCUB_E07_upload_photos_control_not_visible(page: Page, live_server: str) -> None:
    """DCUB-E07: 'رفع صور الأصل' upload control not visible."""
    _goto(page, live_server)
    el = _ws(page).locator('[data-testid="pro-val-vis-upload-photos"]')
    expect(el).not_to_be_visible()


def test_DCUB_E08_upload_aerial_duplicate_control_not_visible(page: Page, live_server: str) -> None:
    """DCUB-E08: 'رفع خريطة جوية' duplicate upload control not visible (duplicate-area version)."""
    _goto(page, live_server)
    # The dup-area aerial upload had testid pro-val-vis-upload-aerial (now compat span)
    el = _ws(page).locator('[data-testid="pro-val-vis-upload-aerial"]')
    expect(el).not_to_be_visible()


# ── DCUB-E09..E11: Old standalone report generation buttons removed ───────────

def test_DCUB_E09_standalone_traditional_button_not_visible(page: Page, live_server: str) -> None:
    """DCUB-E09: Old '📄 تقليدي' standalone button not visible."""
    _goto(page, live_server)
    btn = _ws(page).locator('[data-testid="pro-val-vis-generate-traditional"]')
    expect(btn).not_to_be_visible()


def test_DCUB_E10_standalone_detailed_button_not_visible(page: Page, live_server: str) -> None:
    """DCUB-E10: Old '📊 تفصيلي' standalone button not visible."""
    _goto(page, live_server)
    btn = _ws(page).locator('[data-testid="pro-val-vis-generate-detailed"]')
    expect(btn).not_to_be_visible()


def test_DCUB_E11_standalone_professional_button_not_visible(page: Page, live_server: str) -> None:
    """DCUB-E11: Old '🏆 احترافي' standalone button not visible."""
    _goto(page, live_server)
    btn = _ws(page).locator('[data-testid="pro-val-vis-generate-professional"]')
    expect(btn).not_to_be_visible()


# ── DCUB-E12: Output contract summary removed ─────────────────────────────────

def test_DCUB_E12_output_contract_summary_not_visible(page: Page, live_server: str) -> None:
    """DCUB-E12: 'ملخص عقد المخرجات' output contract summary not visible."""
    _goto(page, live_server)
    el = _ws(page).locator('[data-testid="professional-output-contract-summary"]')
    expect(el).not_to_be_visible()


# ── DCUB-E13..E20: Debug output contract tokens not visible ──────────────────

def test_DCUB_E13_market_value_debug_token_not_visible(page: Page, live_server: str) -> None:
    """DCUB-E13: 'market_value' as inline debug token text not visible."""
    _goto(page, live_server)
    body_text: str = page.evaluate("document.body.innerText")
    assert "market_value · habu_value" not in body_text, \
        "Debug output contract token 'market_value · habu_value' visible in DOM"


def test_DCUB_E14_habu_value_debug_token_not_visible(page: Page, live_server: str) -> None:
    """DCUB-E14: 'habu_value' debug token not visible in contract summary."""
    _goto(page, live_server)
    # The contract summary text had 'habu_value' inline — now hidden
    body_text: str = page.evaluate("document.body.innerText")
    assert "habu_value" not in body_text, "'habu_value' visible in page innerText"


def test_DCUB_E15_confidence_score_debug_token_not_visible(page: Page, live_server: str) -> None:
    """DCUB-E15: 'confidence_score' debug token not visible."""
    _goto(page, live_server)
    body_text: str = page.evaluate("document.body.innerText")
    assert "confidence_score" not in body_text, "'confidence_score' visible in page innerText"


def test_DCUB_E16_comfidence_acore_typo_not_visible(page: Page, live_server: str) -> None:
    """DCUB-E16: Typo 'comfidence_acore' not visible."""
    _goto(page, live_server)
    body_text: str = page.evaluate("document.body.innerText")
    assert "comfidence_acore" not in body_text, "'comfidence_acore' visible in page innerText"


def test_DCUB_E17_comparable_count_used_not_visible(page: Page, live_server: str) -> None:
    """DCUB-E17: 'comparable_count_used' debug token not visible."""
    _goto(page, live_server)
    body_text: str = page.evaluate("document.body.innerText")
    assert "comparable_count_used" not in body_text, "'comparable_count_used' visible in page innerText"


def test_DCUB_E18_adjustment_summary_not_visible(page: Page, live_server: str) -> None:
    """DCUB-E18: 'adjustment_summary' debug token not visible."""
    _goto(page, live_server)
    body_text: str = page.evaluate("document.body.innerText")
    assert "adjustment_summary" not in body_text, "'adjustment_summary' visible in page innerText"


def test_DCUB_E19_ifrs_level_debug_token_not_visible(page: Page, live_server: str) -> None:
    """DCUB-E19: 'ifrs_level' debug token not visible in output contract."""
    _goto(page, live_server)
    # Check the output contract text specifically (the contract div is hidden)
    el = _ws(page).locator('[data-testid="professional-output-contract-summary"]')
    expect(el).not_to_be_visible()
    # Also verify the combined token string is absent from visible page text
    body_text: str = page.evaluate("document.body.innerText")
    assert "market_value · habu_value · confidence_score · comparable_count_used · adjustment_summary · ifrs_level" \
        not in body_text, "Full output contract token string visible"


def test_DCUB_E20_Ifrs_level_capitalized_not_visible(page: Page, live_server: str) -> None:
    """DCUB-E20: 'Ifrs_level' (capitalized variant) not visible."""
    _goto(page, live_server)
    body_text: str = page.evaluate("document.body.innerText")
    assert "Ifrs_level" not in body_text, "'Ifrs_level' visible in page innerText"


# ── DCUB-E21..E24: Governance/actions panel removed ──────────────────────────

def test_DCUB_E21_governance_panel_not_visible(page: Page, live_server: str) -> None:
    """DCUB-E21: 'حوكمة التقرير والإجراءات' governance panel not visible."""
    _goto(page, live_server)
    panel = _ws(page).locator('[data-testid="professional-governance-panel"]')
    expect(panel).not_to_be_visible()


def test_DCUB_E22_draft_pdf_button_not_visible(page: Page, live_server: str) -> None:
    """DCUB-E22: 'تحميل مسودة PDF مهنية' button not visible."""
    _goto(page, live_server)
    btn = _ws(page).locator('[data-testid="professional-draft-pdf-button"]')
    expect(btn).not_to_be_visible()


def test_DCUB_E23_save_draft_button_not_visible(page: Page, live_server: str) -> None:
    """DCUB-E23: 'حفظ مسودة التقييم' button not visible."""
    _goto(page, live_server)
    btn = _ws(page).locator('[data-testid="professional-save-draft-button"]')
    expect(btn).not_to_be_visible()


def test_DCUB_E24_submit_approval_button_not_visible_in_duplicate(page: Page, live_server: str) -> None:
    """DCUB-E24: 'إرسال للمراجعة والاعتماد' button from the duplicate governance panel is not visible."""
    _goto(page, live_server)
    btn = _ws(page).locator('[data-testid="professional-submit-approval-button"]')
    expect(btn).not_to_be_visible()


# ── DCUB-E25..E26: Real lower chat box visible and usable ─────────────────────

def test_DCUB_E25_real_lower_chat_box_visible(page: Page, live_server: str) -> None:
    """DCUB-E25: Real lower ai-section chat box is visible."""
    _goto(page, live_server)
    # The ai-section is the real chat box
    ai_section = _ws(page).locator(".ai-section").first
    expect(ai_section).to_be_visible()


def test_DCUB_E26_real_chat_input_textarea_usable(page: Page, live_server: str) -> None:
    """DCUB-E26: Real chat textarea (pro-val-chat-input) is visible and usable."""
    _goto(page, live_server)
    textarea = _ws(page).locator('[data-testid="pro-val-chat-input"]')
    expect(textarea).to_be_visible()
    # Verify it is enabled (not disabled)
    assert not textarea.is_disabled(), "Real chat textarea must not be disabled"


# ── DCUB-E27..E29: DOM structure integrity ────────────────────────────────────

def test_DCUB_E27_input_generation_section_count_preserved(page: Page, live_server: str) -> None:
    """DCUB-E27: pro-val-input-generation-section count is 2 (ws-professional + backoffice workspace).
    Preserves PVNEW07 contract."""
    _goto(page, live_server)
    el = page.locator('[data-testid="pro-val-input-generation-section"]')
    assert el.count() == 2, (
        f"Expected 2 pro-val-input-generation-section elements, got {el.count()}"
    )


def test_DCUB_E28_no_duplicate_chat_input_testid_in_ws_professional(page: Page, live_server: str) -> None:
    """DCUB-E28: pro-val-chat-input appears exactly once in ws-professional (no duplicate)."""
    _goto(page, live_server)
    inputs = _ws(page).locator('[data-testid="pro-val-chat-input"]')
    count = inputs.count()
    assert count == 1, f"Expected exactly 1 pro-val-chat-input in ws-professional, got {count}"


def test_DCUB_E29_no_internal_paths_in_dom(page: Page, live_server: str) -> None:
    """DCUB-E29: No internal file system paths exposed in visible DOM text."""
    _goto(page, live_server)
    body_text: str = page.evaluate("document.body.innerText")
    forbidden_patterns = [
        "C:\\Users\\",
        "c:/users/",
        "/home/",
        "core_engine/instance/",
        "requests.jsonl",
    ]
    for pattern in forbidden_patterns:
        assert pattern.lower() not in body_text.lower(), (
            f"Internal path pattern '{pattern}' found in visible DOM"
        )
