"""
E2E guard tests — Chat Tab Landing (Phase 12 advisory landing).

Verified:
  1.  Chat tab button exists and navigates to the chat landing.
  2.  Hero title is visible.
  3.  Disclaimer is visible.
  4.  Feasibility section is visible.
  5.  Suggestion chips are visible.
  6.  Clicking a suggestion populates the chat input.
  7.  Clicking إرسال shows a visible advisory answer area.
  8.  Answer card contains advisory wording and does not claim certification.
  9.  Expert contact card is always visible.
  10. Clicking the contact card button opens the lead form.
  11. Filling and submitting the lead form shows confirmation.
  12. JWT login UI is NOT visible in chat landing on initial load:
        - modal not active
        - "تسجيل الدخول" title not visible
        - "الصق رمز JWT" not visible
        - "انتهت صلاحية الجلسة" error not visible
        - no eyJ token text in landing
  13. Other tabs (valuation / professional / composite) still exist.
  14. Chat input and send button are present.

These tests do NOT require a valid JWT, a live RAG backend, or external network calls.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _open_chat_tab(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    page.locator("[data-testid='chat-tab']").click()
    page.wait_for_selector("[data-testid='chat-landing']", state="visible", timeout=5_000)


def _send_chat_question(page: Page, question: str, timeout: int = 20_000) -> None:
    page.locator("[data-testid='chat-input']").fill(question)
    page.locator("[data-testid='chat-send-button']").click()
    page.wait_for_selector("[data-testid='chat-answer-area']", state="visible", timeout=timeout)


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
    assert "المستشار" in title.inner_text()


def test_CS_chat_disclaimer_visible(page: Page, live_server: str) -> None:
    """Disclaimer text is visible in the chat landing."""
    _open_chat_tab(page, live_server)
    disclaimer = page.locator("[data-testid='chat-disclaimer']")
    expect(disclaimer).to_be_visible()
    assert "تقرير تقييم رسمي" in disclaimer.inner_text()


def test_CS_chat_feasibility_section_visible(page: Page, live_server: str) -> None:
    """Feasibility/investment section is visible in the chat landing."""
    _open_chat_tab(page, live_server)
    section = page.locator("[data-testid='chat-feasibility-section']")
    expect(section).to_be_visible()
    assert "جدوى" in section.inner_text()


def test_CS_chat_suggestions_visible(page: Page, live_server: str) -> None:
    """Category suggestion chips container and at least one chip are visible."""
    _open_chat_tab(page, live_server)
    expect(page.locator("[data-testid='chat-suggestions']")).to_be_visible()
    expect(page.locator("[data-testid='chat-suggestion-card']").first).to_be_visible()


def test_CS_chat_feasibility_chip_fills_input(page: Page, live_server: str) -> None:
    """Clicking a feasibility chip fills the chat textarea with the question text."""
    _open_chat_tab(page, live_server)
    chip = page.locator("[data-testid='chat-feasibility-section'] button.chat-chip").first
    chip.click()
    filled = page.locator("[data-testid='chat-input']").input_value()
    assert filled.strip() and len(filled) > 5


def test_CS_chat_send_shows_answer_area(page: Page, live_server: str) -> None:
    """Clicking إرسال makes the advisory answer area visible (real response or fallback)."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "ما الفرق بين تقرير مبسط وتقرير تقييم احترافي؟")
    expect(page.locator("[data-testid='chat-answer-area']")).to_be_visible()
    expect(page.locator("[data-testid='chat-answer-card']")).to_be_visible()


def test_CS_chat_answer_is_advisory_not_certified(page: Page, live_server: str) -> None:
    """Answer does not claim to be a certified report; contains advisory language."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "كيف أطعن على تقدير الضرائب العقارية لعقار غير مستغل؟")
    text = page.locator("[data-testid='chat-answer-area']").inner_text()
    # Must not claim to be an official certified report without the negation
    assert "لا تُعد" in text or "إرشادي" in text or "إجابة" in text, (
        "Answer must contain advisory disclaimer language"
    )
    assert "تقرير تقييم رسمي معتمد" not in text, (
        "Answer must not claim to be a certified valuation report"
    )


def test_CS_chat_expert_contact_card_always_visible(page: Page, live_server: str) -> None:
    """Expert contact card is always visible in the chat landing (before any send)."""
    _open_chat_tab(page, live_server)
    card = page.locator("[data-testid='expert-contact-card']")
    expect(card).to_be_visible()
    assert "خبير" in card.inner_text()


def test_CS_chat_lead_form_opens_on_button_click(page: Page, live_server: str) -> None:
    """Clicking 'أريد تواصل الخبير' expands the lead form."""
    _open_chat_tab(page, live_server)
    page.locator("[data-testid='expert-contact-card'] button").click()
    expect(page.locator("[data-testid='expert-lead-form']")).to_be_visible(timeout=3_000)


def test_CS_chat_lead_form_submit_shows_confirmation(page: Page, live_server: str) -> None:
    """Filling name and phone and submitting shows the confirmation message."""
    _open_chat_tab(page, live_server)
    page.locator("[data-testid='expert-contact-card'] button").click()
    page.locator("[data-testid='expert-lead-name']").fill("أحمد محمد")
    page.locator("[data-testid='expert-lead-phone']").fill("01234567890")
    page.locator("[data-testid='expert-lead-submit']").click()
    confirm = page.locator("[data-testid='expert-lead-confirmation']")
    expect(confirm).to_be_visible(timeout=3_000)
    assert "تم" in confirm.inner_text()


def test_CS_chat_no_jwt_modal_on_load(page: Page, live_server: str) -> None:
    """JWT login modal is NOT active when chat tab loads without user action."""
    _open_chat_tab(page, live_server)
    modal = page.locator("#es-login-modal")
    assert not modal.evaluate("el => el.classList.contains('es-active')")
    assert not page.get_by_text("تسجيل الدخول — ALHADY FOR REAL PROPERTY").is_visible()
    assert not page.get_by_text("الصق رمز JWT الخاص بك").is_visible()


def test_CS_chat_no_expired_session_error_on_load(page: Page, live_server: str) -> None:
    """chat-error and global modal are hidden on initial chat tab load."""
    _open_chat_tab(page, live_server)
    assert not page.locator("#chat-error").is_visible()
    assert not page.locator("#es-login-modal").evaluate("el => el.classList.contains('es-active')")


def test_CS_chat_no_jwt_token_text_in_landing(page: Page, live_server: str) -> None:
    """No JWT token sample text (eyJ…) appears inside the chat landing."""
    _open_chat_tab(page, live_server)
    assert "eyJ" not in page.locator("[data-testid='chat-landing']").inner_text()


def test_CS_chat_other_tabs_exist(page: Page, live_server: str) -> None:
    """All four tabs are present after chat tab is opened."""
    _open_chat_tab(page, live_server)
    expect(page.locator("#es-tab-chat")).to_be_visible()
    expect(page.locator("#es-tab-valuation")).to_be_visible()
    expect(page.locator("#es-tab-professional")).to_be_visible()
    expect(page.locator("#es-tab-composite")).to_be_visible()


def test_CS_chat_input_and_send_button_present(page: Page, live_server: str) -> None:
    """Chat textarea and send button are present and not disabled on landing load."""
    _open_chat_tab(page, live_server)
    expect(page.locator("[data-testid='chat-input']")).to_be_visible()
    send_btn = page.locator("[data-testid='chat-send-button']")
    expect(send_btn).to_be_visible()
    assert not send_btn.is_disabled()


def test_CS_chat_discount_vs_cap_rate_answer(page: Page, live_server: str) -> None:
    """Asking the cap-rate vs discount-rate question returns a direct answer with all required terms."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "ما الفرق بين معدل الخصم ومعدل الرسملة؟")
    text = page.locator("[data-testid='chat-answer-area']").inner_text()
    assert "معدل الرسملة" in text, "Answer must explain Cap Rate"
    assert "معدل الخصم" in text, "Answer must explain Discount Rate"
    assert "DCF" in text or "التدفقات النقدية" in text, "Answer must mention DCF or cash flows"
    assert "NOI" in text or "صافي دخل" in text, "Answer must mention NOI or net income"
    assert "إرشادية" in text, "Answer must contain advisory disclaimer"


def test_CS_chat_readability_regression(page: Page, live_server: str) -> None:
    """Key UI elements are visible after page load (readability regression guard)."""
    _open_chat_tab(page, live_server)
    expect(page.locator("[data-testid='chat-input']")).to_be_visible()
    expect(page.locator("[data-testid='chat-send-button']")).to_be_visible()
    expect(page.locator("[data-testid='expert-contact-card']")).to_be_visible()
    expect(page.locator("[data-testid='chat-suggestions']")).to_be_visible()
    expect(page.locator("[data-testid='chat-feasibility-section']")).to_be_visible()


def test_CS_chat_detailed_cap_rate_answer(page: Page, live_server: str) -> None:
    """Cap-rate answer contains numerical example: 1,000,000 → 10,000,000 at 10% cap rate."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "ما الفرق بين معدل الخصم ومعدل الرسملة؟")
    text = page.locator("[data-testid='chat-answer-area']").inner_text()
    assert "1,000,000" in text or "1000000" in text, "Answer must show NOI = 1,000,000"
    assert "10,000,000" in text or "10000000" in text, "Answer must show cap value 10,000,000"
    assert "NOI" in text or "صافي دخل" in text, "Answer must mention NOI"
    assert "DCF" in text or "التدفقات النقدية" in text, "Answer must mention DCF"
    assert "إرشادية" in text, "Answer must contain advisory disclaimer"


def test_CS_chat_detailed_feasibility_answer(page: Page, live_server: str) -> None:
    """Feasibility answer contains numerical example: 17,000,000 total cost, 22,000,000 sales, ROI."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "كيف أعمل دراسة جدوى لمشروع عقاري؟")
    text = page.locator("[data-testid='chat-answer-area']").inner_text()
    assert "17,000,000" in text or "17000000" in text, "Answer must show total cost 17,000,000"
    assert "22,000,000" in text or "22000000" in text, "Answer must show sales 22,000,000"
    assert "تكلفة" in text, "Answer must mention تكلفة (cost)"
    assert "إيرادات" in text, "Answer must mention إيرادات (revenue)"
    assert "ROI" in text, "Answer must mention ROI"
    assert "إرشادية" in text, "Answer must contain advisory disclaimer"


def test_CS_chat_unknown_categorized_question(page: Page, live_server: str) -> None:
    """Unknown question about a leased shop triggers income-category fallback with دخل/إيجار context."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "إزاي أقيم محل مؤجر بعقد طويل؟")
    text = page.locator("[data-testid='chat-answer-area']").inner_text()
    assert "دخل" in text or "إيجار" in text, "Income category answer must mention دخل or إيجار"
    assert "موقع" in text or "نوع العقار" in text, "Answer must ask for property type or location"
    assert "إرشادية" in text, "Answer must contain advisory disclaimer"


def test_CS_chat_unknown_generic_question(page: Page, live_server: str) -> None:
    """Completely unknown question triggers generic 'need more info' fallback with 4 context fields."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "ما المطلوب لتقييم حالة خاصة غير موجودة في القائمة؟")
    text = page.locator("[data-testid='chat-answer-area']").inner_text()
    assert "نوع العقار" in text, "Must ask for property type"
    assert "الموقع" in text, "Must ask for location"
    assert "الغرض" in text, "Must ask for purpose"
    assert "المستندات" in text, "Must ask for documents"


# ---------------------------------------------------------------------------
# New tests: category fallback numerical examples + web toggle (22 → 28)
# ---------------------------------------------------------------------------

def test_CS_chat_income_category_noi_numerical(page: Page, live_server: str) -> None:
    """Income/rental question triggers NOI category with معدل الرسملة and 5,000,000 example."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "إزاي أقيم محل مؤجر بعقد طويل؟")
    text = page.locator("[data-testid='chat-answer-area']").inner_text()
    assert "إيجار" in text or "دخل" in text, "Income category must mention إيجار or دخل"
    assert "NOI" in text or "صافي الدخل" in text, "Income category must mention NOI"
    assert "معدل الرسملة" in text, "Income category must mention معدل الرسملة"
    assert "5,000,000" in text or "5000000" in text, "Income category must show 5,000,000 example"
    assert "إرشادية" in text, "Answer must contain advisory disclaimer"


def test_CS_chat_cma_category_numerical(page: Page, live_server: str) -> None:
    """Market-comparison question triggers CMA category with سعر المتر and 2,850,000 example."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "عندي شقة 120 متر وعايز أعرف أستخدم مقارنات السوق إزاي")
    text = page.locator("[data-testid='chat-answer-area']").inner_text()
    assert "مقارن" in text, "CMA category must mention مقارن / مقارنة / مقارنات"
    assert "سعر المتر" in text, "CMA category must mention سعر المتر"
    assert "120" in text, "Answer area must contain 120 (from question echo or example)"
    assert "2,850,000" in text or "2850000" in text, "CMA category must show 2,850,000 example"


def test_CS_chat_mortgage_ltv_numerical(page: Page, live_server: str) -> None:
    """Mortgage question triggers LTV category with 5,950,000 maximum loan example."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "البنك بيحسب قيمة الرهن على أساس إيه؟")
    text = page.locator("[data-testid='chat-answer-area']").inner_text()
    assert "رهن" in text or "تمويل" in text, "Mortgage category must mention رهن or تمويل"
    assert "LTV" in text, "Mortgage category must mention LTV"
    assert "5,950,000" in text or "5950000" in text, "Mortgage category must show 5,950,000 example"


def test_CS_chat_tax_appeal_advisory(page: Page, live_server: str) -> None:
    """Tax question triggers tax-appeal category with إخطار and مستندات guidance."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "وصلني تقدير ضريبة عقارية عالي أعمل إيه؟")
    text = page.locator("[data-testid='chat-answer-area']").inner_text()
    assert "ضريبة" in text or "الضريبي" in text, "Tax category must mention ضريبة"
    assert "إخطار" in text or "مستندات" in text, "Tax category must mention إخطار or مستندات"
    assert "إرشادية" in text, "Answer must contain advisory disclaimer"


def test_CS_chat_generic_context_request(page: Page, live_server: str) -> None:
    """Unknown question triggers generic fallback asking for نوع العقار, الموقع, الغرض, المستندات."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "عندي حالة خاصة ومش عارف أبدأ منين")
    text = page.locator("[data-testid='chat-answer-area']").inner_text()
    assert "نوع العقار" in text, "Generic fallback must ask for نوع العقار"
    assert "الموقع" in text, "Generic fallback must ask for الموقع"
    assert "الغرض" in text, "Generic fallback must ask for الغرض"
    assert "المستندات" in text, "Generic fallback must ask for المستندات"


def test_CS_chat_web_toggle_shows_coming_soon(page: Page, live_server: str) -> None:
    """Web search toggle shows 'coming later' message; checkbox stays unchecked; no external call."""
    _open_chat_tab(page, live_server)
    # Click the toggle label
    page.locator("[data-testid='chat-web-toggle-label']").click()
    # Error element should become visible with the 'coming later' message
    err = page.locator("#chat-error")
    expect(err).to_be_visible(timeout=3_000)
    msg_text = err.inner_text()
    assert "سيتم تفعيل البحث" in msg_text or "مرحلة لاحقة" in msg_text, (
        f"Expected coming-soon message, got: {msg_text!r}"
    )
    # Checkbox must remain unchecked (chatWebToggleClick unchecks it)
    assert not page.locator("#chat-web-toggle").is_checked()


# ---------------------------------------------------------------------------
# Shared Backend integration tests — Chat expert lead form
# ---------------------------------------------------------------------------

def test_CS_chat_expert_lead_saves_to_backend(page: Page, live_server: str) -> None:
    """Chat expert lead form posts to /api/expert-requests and shows confirmation."""
    import json as _json
    _mock_body = _json.dumps({
        "status":          "success",
        "request_id":      "REQ-CHAT0001",
        "source_page":     "chat",
        "request_kind":    "expert_contact",
        "message":         "تم تسجيل الطلب بنجاح. رقم الطلب: REQ-CHAT0001.",
        "pdf_available":   False,
        "non_certified":   True,
        "documents_saved": 0,
        "document_errors": [],
    }).encode()
    page.route("**/api/expert-requests", lambda r: r.fulfill(
        status=201, body=_mock_body, content_type="application/json"
    ))

    _open_chat_tab(page, live_server)
    page.locator("[data-testid='expert-contact-card'] button").click()
    page.locator("[data-testid='expert-lead-form']").wait_for(state="visible", timeout=3_000)

    page.locator("[data-testid='expert-lead-name']").fill("أحمد محمد اختبار")
    page.locator("[data-testid='expert-lead-phone']").fill("01012345678")
    page.locator("[data-testid='expert-lead-submit']").click()

    confirm = page.locator("[data-testid='expert-lead-confirmation']")
    expect(confirm).to_be_visible(timeout=8_000)
    assert "تم" in confirm.inner_text()


def test_CS_chat_expert_lead_confirmation_has_request_id(page: Page, live_server: str) -> None:
    """Chat expert lead confirmation includes the request_id from the backend."""
    import json as _json
    _mock_body = _json.dumps({
        "status":          "success",
        "request_id":      "REQ-CHATID01",
        "message":         "تم تسجيل الطلب بنجاح. رقم الطلب: REQ-CHATID01.",
        "pdf_available":   False,
        "non_certified":   True,
        "documents_saved": 0,
        "document_errors": [],
    }).encode()
    page.route("**/api/expert-requests", lambda r: r.fulfill(
        status=201, body=_mock_body, content_type="application/json"
    ))

    _open_chat_tab(page, live_server)
    page.locator("[data-testid='expert-contact-card'] button").click()
    page.locator("[data-testid='expert-lead-form']").wait_for(state="visible", timeout=3_000)

    page.locator("[data-testid='expert-lead-name']").fill("اختبار ID")
    page.locator("[data-testid='expert-lead-phone']").fill("01099999999")
    page.locator("[data-testid='expert-lead-submit']").click()

    confirm = page.locator("[data-testid='expert-lead-confirmation']")
    expect(confirm).to_be_visible(timeout=8_000)
    assert "REQ-CHATID01" in confirm.inner_text()
