"""
E2E guard tests — Chat Tab Landing (Phase 12 advisory landing).

Verified:
  1.  Chat tab button exists and navigates to the chat landing.
  2.  Hero title is visible.
  3.  Disclaimer is visible.
  4.  Feasibility section is visible.
  5.  Suggestion chips are visible.
  6.  Clicking a feasibility chip fills the textarea.
  7.  JWT "تسجيل الدخول" text is NOT visible in the chat landing on initial load.
  8.  "الصق رمز JWT" instruction text is NOT visible in the chat landing.
  9.  The global JWT login modal is NOT open/visible on initial load.
  10. "انتهت صلاحية الجلسة أو الرمز غير صالح" error is NOT visible on initial load.
  11. No JWT token-like text (eyJ...) is visible in the chat landing area.
  12. The other three tabs (valuation / professional / composite) still exist.

These tests do NOT require a valid JWT, a live RAG backend, or external network calls.
They verify UI state and static landing content only.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CHAT_URL_FRAGMENT = "#"   # page is a single SPA; we navigate to root and click the tab


def _open_chat_tab(page: Page, live_server: str) -> None:
    """Navigate to the app root and switch to the chat tab."""
    page.goto(live_server, wait_until="networkidle")
    chat_tab = page.locator("[data-testid='chat-tab']")
    chat_tab.click()
    # Give the tab switch time to complete (it's synchronous JS, but be safe)
    page.wait_for_selector("[data-testid='chat-landing']", state="visible", timeout=5_000)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_CS_chat_tab_button_exists(page: Page, live_server: str) -> None:
    """Chat tab button is present in the navigation bar."""
    page.goto(live_server, wait_until="networkidle")
    expect(page.locator("[data-testid='chat-tab']")).to_be_visible()


def test_CS_chat_title_visible(page: Page, live_server: str) -> None:
    """Hero title 'المستشار العقاري والضريبي الذكي' is visible after opening chat tab."""
    _open_chat_tab(page, live_server)
    title = page.locator("[data-testid='chat-title']")
    expect(title).to_be_visible()
    assert "المستشار" in title.inner_text(), "Hero title must contain 'المستشار'"


def test_CS_chat_disclaimer_visible(page: Page, live_server: str) -> None:
    """Disclaimer text is visible in the chat landing."""
    _open_chat_tab(page, live_server)
    disclaimer = page.locator("[data-testid='chat-disclaimer']")
    expect(disclaimer).to_be_visible()
    text = disclaimer.inner_text()
    assert "تقرير تقييم رسمي" in text, "Disclaimer must mention 'تقرير تقييم رسمي'"


def test_CS_chat_feasibility_section_visible(page: Page, live_server: str) -> None:
    """Feasibility/investment section is visible in the chat landing."""
    _open_chat_tab(page, live_server)
    section = page.locator("[data-testid='chat-feasibility-section']")
    expect(section).to_be_visible()
    text = section.inner_text()
    assert "جدوى" in text, "Feasibility section must contain 'جدوى'"


def test_CS_chat_suggestions_visible(page: Page, live_server: str) -> None:
    """Category suggestion chips container is visible."""
    _open_chat_tab(page, live_server)
    chips = page.locator("[data-testid='chat-suggestions']")
    expect(chips).to_be_visible()


def test_CS_chat_feasibility_chip_fills_input(page: Page, live_server: str) -> None:
    """Clicking a feasibility chip fills the chat textarea with Arabic question text."""
    _open_chat_tab(page, live_server)
    # Click the first feasibility chip (دراسة جدوى)
    chip = page.locator("[data-testid='chat-feasibility-section'] button.chat-chip").first
    chip.click()
    textarea = page.locator("[data-testid='chat-input']")
    filled = textarea.input_value()
    assert filled.strip(), "Clicking feasibility chip must fill the textarea (non-empty)"
    assert "?" in filled or "؟" in filled or len(filled) > 5, (
        "Textarea value must be a non-trivial Arabic question"
    )


def test_CS_chat_no_jwt_login_title_visible(page: Page, live_server: str) -> None:
    """'تسجيل الدخول - ALHADY FOR REAL PROPERTY' must NOT be visible in the chat landing
    on initial load (without any user interaction)."""
    _open_chat_tab(page, live_server)
    landing = page.locator("[data-testid='chat-landing']")
    # The global modal sits outside the landing div; check it is not open/visible
    modal = page.locator("#es-login-modal")
    # Modal is hidden by default (display:none) — must not have es-active class
    assert not modal.evaluate("el => el.classList.contains('es-active')"), (
        "JWT login modal must NOT be open (es-active) when the chat tab loads without user action"
    )
    # Double check: login title text must not be visible anywhere on page
    login_title = page.get_by_text("تسجيل الدخول — ALHADY FOR REAL PROPERTY")
    assert not login_title.is_visible(), (
        "'تسجيل الدخول' title must not be visible in the chat landing"
    )


def test_CS_chat_no_jwt_paste_instruction_visible(page: Page, live_server: str) -> None:
    """'الصق رمز JWT الخاص بك' instruction must NOT be visible on chat tab load."""
    _open_chat_tab(page, live_server)
    modal = page.locator("#es-login-modal")
    assert not modal.evaluate("el => el.classList.contains('es-active')"), (
        "JWT modal must not be open when chat tab loads"
    )
    jwt_instruction = page.get_by_text("الصق رمز JWT الخاص بك")
    assert not jwt_instruction.is_visible(), (
        "'الصق رمز JWT' must not be visible during initial chat tab load"
    )


def test_CS_chat_no_expired_session_message_on_load(page: Page, live_server: str) -> None:
    """'انتهت صلاحية الجلسة أو الرمز غير صالح' must NOT appear at initial page load."""
    _open_chat_tab(page, live_server)
    # Check the chat-error div (inline error area) is hidden
    error_div = page.locator("#chat-error")
    assert not error_div.is_visible(), (
        "chat-error div must be hidden on initial load — no expired session error"
    )
    # Check global modal is not active
    modal = page.locator("#es-login-modal")
    assert not modal.evaluate("el => el.classList.contains('es-active')"), (
        "JWT modal must not pop on initial load"
    )


def test_CS_chat_no_jwt_token_text_visible_in_landing(page: Page, live_server: str) -> None:
    """No JWT token sample text (eyJ...) must be visible in the chat landing area."""
    _open_chat_tab(page, live_server)
    landing = page.locator("[data-testid='chat-landing']")
    landing_text = landing.inner_text()
    assert "eyJ" not in landing_text, (
        "JWT token sample text 'eyJ...' must not appear in the chat landing content"
    )


def test_CS_chat_other_tabs_exist(page: Page, live_server: str) -> None:
    """All four tabs (chat/valuation/professional/composite) exist after chat tab is opened."""
    _open_chat_tab(page, live_server)
    expect(page.locator("#es-tab-chat")).to_be_visible()
    expect(page.locator("#es-tab-valuation")).to_be_visible()
    expect(page.locator("#es-tab-professional")).to_be_visible()
    expect(page.locator("#es-tab-composite")).to_be_visible()


def test_CS_chat_input_and_send_button_present(page: Page, live_server: str) -> None:
    """Chat textarea and send button are present and interactive."""
    _open_chat_tab(page, live_server)
    textarea = page.locator("[data-testid='chat-input']")
    send_btn = page.locator("[data-testid='chat-send-button']")
    expect(textarea).to_be_visible()
    expect(send_btn).to_be_visible()
    assert not send_btn.is_disabled(), "Send button must not be disabled on landing load"
