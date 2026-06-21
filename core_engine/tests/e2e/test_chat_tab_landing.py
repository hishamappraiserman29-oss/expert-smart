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


# ---------------------------------------------------------------------------
# Part A+  Visual structure (comprehensive)  ──────────────────────────── 31
# ---------------------------------------------------------------------------

def test_chat_page_visual_structure(page: Page, live_server: str) -> None:
    """All required chat page sections and controls are visible on landing."""
    _open_chat_tab(page, live_server)
    for testid in [
        "chat-title",
        "chat-disclaimer",
        "chat-suggestions",
        "chat-feasibility-section",
        "chat-input",
        "chat-send-button",
        "chat-web-toggle-label",
        "expert-contact-card",
    ]:
        expect(page.locator(f"[data-testid='{testid}']")).to_be_visible(), (
            f"{testid} should be visible on chat landing"
        )
    # Error div and answer area are in DOM but hidden initially
    assert page.query_selector("[data-testid='chat-error']") is not None
    assert page.query_selector("[data-testid='chat-answer-area']") is not None


# ---------------------------------------------------------------------------
# Part B  All main suggestion chips fill the input  ──────────────────── 32
# ---------------------------------------------------------------------------

def test_chat_all_main_chips_fill_input(page: Page, live_server: str) -> None:
    """Every chip in the common-questions section fills the textarea with non-empty text."""
    _open_chat_tab(page, live_server)
    chips = page.locator("[data-testid='chat-suggestions'] .chat-chip").all()
    assert len(chips) >= 8, f"Expected at least 8 suggestion chips, got {len(chips)}"
    for i, chip in enumerate(chips):
        chip.click()
        filled = page.locator("[data-testid='chat-input']").input_value()
        assert len(filled.strip()) > 5, (
            f"Chip #{i+1} did not fill the input (got: {filled!r})"
        )


# ---------------------------------------------------------------------------
# Part C  Advisory answer quality  ───────────────────────────────────── 33-35
# ---------------------------------------------------------------------------

def test_chat_hbu_answer_detailed(page: Page, live_server: str) -> None:
    """HBU answer contains all four HBU criteria."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "ما معنى أعلى وأفضل استغلال في الأراضي والعقارات؟")
    text = page.locator("[data-testid='chat-answer-area']").inner_text()
    assert "ممكن قانونًا" in text,         "HBU answer must state 'ممكن قانونًا'"
    assert "ممكن فنيًا" in text,            "HBU answer must state 'ممكن فنيًا'"
    assert "مجدٍ ماليًا" in text,           "HBU answer must state 'مجدٍ ماليًا'"
    assert "الأعلى إنتاجية" in text,        "HBU answer must state 'الأعلى إنتاجية'"
    assert "إرشادية" in text,               "HBU answer must include advisory disclaimer"


def test_chat_drc_answer_conditions(page: Page, live_server: str) -> None:
    """DRC answer names specialized assets, depreciation, numeric example, and not-always-applicable note."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "متى يكون تقرير التكلفة الاستبدالية DRC مناسبًا؟")
    text = page.locator("[data-testid='chat-answer-area']").inner_text()
    assert "DRC" in text or "التكلفة الاستبدالية" in text, "Must mention DRC"
    assert "إهلاك" in text,                  "Must mention depreciation"
    assert "مصانع" in text or "مستشفيات" in text, "Must mention specialized assets"
    assert "20,000,000" in text or "20000000" in text, "Must show 20M numeric example"
    assert "لا يُستخدم" in text,            "Must state DRC is not always appropriate"
    assert "إرشادية" in text,               "Must include advisory disclaimer"


def test_chat_court_inheritance_answer(page: Page, live_server: str) -> None:
    """Court/inheritance answer names qualified expert, legal context, and document review."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "كيف تحسب المحكمة قيمة العقار في قضايا الفرز والتجنيب؟")
    text = page.locator("[data-testid='chat-answer-area']").inner_text()
    assert "خبير" in text,                  "Must mention expert valuation"
    assert "المستندات" in text,             "Must mention supporting documents"
    assert "الفرز" in text or "التجنيب" in text or "المحكمة" in text, (
        "Must mention court/partition context"
    )
    assert "إرشادية" in text,               "Must include advisory disclaimer"


# ---------------------------------------------------------------------------
# Part E  Context fields do not crash or block  ──────────────────────── 36
# ---------------------------------------------------------------------------

def test_chat_context_fields_do_not_break_send(page: Page, live_server: str) -> None:
    """Filling location and property-type context fields then sending works without crash."""
    _open_chat_tab(page, live_server)
    page.locator("[data-testid='chat-location']").fill("طنطا")
    page.locator("[data-testid='chat-property-type']").fill("مصنع")
    _send_chat_question(page, "كيف أطعن على تقدير الضرائب العقارية؟")
    expect(page.locator("[data-testid='chat-answer-area']")).to_be_visible()
    text = page.locator("[data-testid='chat-answer-area']").inner_text()
    assert "ضريبة" in text or "الضريبي" in text or "إخطار" in text, (
        "Answer must be relevant to tax question"
    )


# ---------------------------------------------------------------------------
# Part G  Lead form validation  ──────────────────────────────────────── 37
# ---------------------------------------------------------------------------

def test_chat_expert_contact_form_validation(page: Page, live_server: str) -> None:
    """Submitting the lead form without required name/phone shows error in chat-error."""
    _open_chat_tab(page, live_server)
    page.locator("[data-testid='expert-contact-card'] button").click()
    page.locator("[data-testid='expert-lead-form']").wait_for(state="visible", timeout=3_000)
    # Leave name and phone empty — click submit
    page.locator("[data-testid='expert-lead-submit']").click()
    err = page.locator("[data-testid='chat-error']")
    expect(err).to_be_visible(timeout=3_000)
    assert "الاسم" in err.inner_text() or "الهاتف" in err.inner_text(), (
        f"Validation error must mention name or phone; got: {err.inner_text()!r}"
    )


# ---------------------------------------------------------------------------
# Part C  No certified report claim  ─────────────────────────────────── 38
# ---------------------------------------------------------------------------

def test_chat_no_certified_report_claim(page: Page, live_server: str) -> None:
    """For any question, the answer area never asserts it IS a certified valuation report."""
    _open_chat_tab(page, live_server)
    for question in [
        "ما الفرق بين معدل الخصم ومعدل الرسملة؟",
        "كيف أعمل دراسة جدوى لمشروع عقاري؟",
        "ما معنى أعلى وأفضل استغلال في الأراضي والعقارات؟",
    ]:
        _send_chat_question(page, question)
        text = page.locator("[data-testid='chat-answer-area']").inner_text()
        # Positive claim: "هذا تقرير تقييم رسمي معتمد" must NOT appear
        assert "هذا تقرير تقييم رسمي معتمد" not in text, (
            f"Answer must not claim to be a certified report. Got: {text[:200]}"
        )
        # Advisory disclaimer must appear
        assert "إرشادية" in text or "لا يُعد" in text, (
            f"Answer must contain advisory disclaimer. Got: {text[:200]}"
        )


# ---------------------------------------------------------------------------
# Part H  Security / safety  ─────────────────────────────────────────── 39-41
# ---------------------------------------------------------------------------

def test_chat_xss_input_safe(page: Page, live_server: str) -> None:
    """XSS payload in chat input does not execute: no JS alert is triggered."""
    dialogs: list[str] = []
    page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

    _open_chat_tab(page, live_server)
    _send_chat_question(page, "<img src=x onerror=alert(1)> ما قيمة العقار؟")

    assert len(dialogs) == 0, f"XSS alert was triggered: {dialogs}"
    expect(page.locator("[data-testid='chat-answer-area']")).to_be_visible()


def test_chat_long_input_safe(page: Page, live_server: str) -> None:
    """A 1,500-character question does not crash the UI; answer area appears."""
    _open_chat_tab(page, live_server)
    long_q = "ما قيمة العقار؟ " * 94  # ~1,500 chars
    _send_chat_question(page, long_q, timeout=30_000)
    expect(page.locator("[data-testid='chat-answer-area']")).to_be_visible()


def test_chat_empty_input_handled(page: Page, live_server: str) -> None:
    """Clicking Send without typing shows the 'اكتب سؤالك' error; no crash."""
    _open_chat_tab(page, live_server)
    # Ensure input is clear
    page.locator("[data-testid='chat-input']").fill("")
    page.locator("[data-testid='chat-send-button']").click()
    err = page.locator("[data-testid='chat-error']")
    expect(err).to_be_visible(timeout=3_000)
    assert "سؤالك" in err.inner_text(), (
        f"Expected 'سؤالك' in empty-input error, got: {err.inner_text()!r}"
    )
    # Answer area must NOT appear
    assert not page.locator("[data-testid='chat-answer-area']").is_visible(), (
        "Answer area must stay hidden when input is empty"
    )


# ---------------------------------------------------------------------------
# Part J  Responsive smoke  ──────────────────────────────────────────── 42-43
# ---------------------------------------------------------------------------

def test_chat_responsive_smoke_desktop(page: Page, live_server: str) -> None:
    """Desktop viewport (1280×800): key chat elements are visible and not overflowing."""
    page.set_viewport_size({"width": 1280, "height": 800})
    _open_chat_tab(page, live_server)
    for testid in ["chat-title", "chat-disclaimer", "chat-input",
                   "chat-send-button", "expert-contact-card"]:
        expect(page.locator(f"[data-testid='{testid}']")).to_be_visible()
    # No horizontal scrollbar: scrollWidth <= clientWidth
    overflow = page.evaluate(
        "document.documentElement.scrollWidth > document.documentElement.clientWidth"
    )
    assert not overflow, "Horizontal overflow detected at desktop 1280px width"


def test_chat_responsive_smoke_mobile(page: Page, live_server: str) -> None:
    """Mobile viewport (390×844): key chat elements are still visible."""
    page.set_viewport_size({"width": 390, "height": 844})
    _open_chat_tab(page, live_server)
    for testid in ["chat-title", "chat-input", "chat-send-button"]:
        expect(page.locator(f"[data-testid='{testid}']")).to_be_visible()


# ---------------------------------------------------------------------------
# Part D  Unknown question / land scenario fallback  ─────────────────── 44
# ---------------------------------------------------------------------------

def test_chat_land_sell_develop_fallback(page: Page, live_server: str) -> None:
    """'هل أبيعها أم أطورها' question returns a non-empty advisory answer (generic context fallback)."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "عندي أرض على طريق رئيسي هل أبيعها أم أطورها؟")
    text = page.locator("[data-testid='chat-answer-area']").inner_text()
    assert len(text.strip()) > 50, "Fallback answer must be non-trivially long"
    assert "إرشادية" in text or "لا يُعد" in text, (
        "Fallback answer must contain advisory disclaimer"
    )


# ---------------------------------------------------------------------------
# Valuation-basis routing fix  ───────────────────────────────────────── 45-48
# ---------------------------------------------------------------------------

def test_chat_market_value_vs_investment_value_arabic(page: Page, live_server: str) -> None:
    """'ما الفرق بين القيمة السوقية والقيمة الاستثمارية؟' → valuation-basis answer, NOT feasibility."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "ما الفرق بين القيمة السوقية والقيمة الاستثمارية؟")
    text = page.locator("[data-testid='chat-answer-area']").inner_text()

    # Must contain the correct valuation-basis content
    assert "القيمة السوقية" in text,           "Answer must define القيمة السوقية"
    assert "القيمة الاستثمارية" in text,        "Answer must define القيمة الاستثمارية"
    assert "السوق العام" in text,              "Answer must mention السوق العام (market perspective)"
    assert "مستثمر" in text,                   "Answer must mention investor perspective"
    assert "10,000,000" in text,               "Answer must include the 10M numeric example"
    assert "إرشادية" in text,                  "Answer must include advisory disclaimer"

    # Must NOT be the feasibility-study answer
    assert "دراسات الجدوى العقارية تتضمن" not in text, (
        "Answer must NOT be the generic feasibility-study response"
    )


def test_chat_market_value_vs_investment_value_english(page: Page, live_server: str) -> None:
    """'ما الفرق بين Market Value و Investment Value؟' → same valuation-basis answer."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "ما الفرق بين Market Value و Investment Value؟")
    text = page.locator("[data-testid='chat-answer-area']").inner_text()

    assert "القيمة السوقية" in text or "Market Value" in text, (
        "Answer must reference القيمة السوقية/Market Value"
    )
    assert "الاستثمارية" in text or "Investment Value" in text, (
        "Answer must reference القيمة الاستثمارية/Investment Value"
    )
    assert "إرشادية" in text, "Answer must include advisory disclaimer"
    assert "دراسات الجدوى العقارية تتضمن" not in text, (
        "Answer must NOT be the generic feasibility-study response"
    )


def test_chat_feasibility_regression(page: Page, live_server: str) -> None:
    """Regression: feasibility question still routes to feasibility answer after routing fix."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "كيف أعمل دراسة جدوى لمشروع عقاري؟")
    text = page.locator("[data-testid='chat-answer-area']").inner_text()
    # Direct Q&A hit for feasibility
    assert "التكلفة الإجمالية" in text or "الإيرادات المتوقعة" in text or "ROI" in text, (
        "Feasibility question must still get feasibility answer"
    )
    assert "إرشادية" in text, "Answer must include advisory disclaimer"


def test_chat_investment_return_regression(page: Page, live_server: str) -> None:
    """Regression: investment-return question still routes to return-calculation answer after routing fix."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "كيف أحسب العائد المتوقع من مشروع عقاري؟")
    text = page.locator("[data-testid='chat-answer-area']").inner_text()
    assert "ROI" in text or "IRR" in text or "NPV" in text or "العائد" in text, (
        "Investment-return question must get a return-calculation answer"
    )
    assert "إرشادية" in text, "Answer must include advisory disclaimer"


# ── UX Indicator Tests (49-62) ──────────────────────────────────────────────

def test_chat_answer_category_badge_appears(page: Page, live_server: str) -> None:
    """[49] chat-answer-category badge element is visible after receiving an answer."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "ما الفرق بين القيمة السوقية والقيمة الاستثمارية؟")
    page.wait_for_selector("[data-testid='chat-answer-category']", state="visible", timeout=5_000)
    assert page.is_visible("[data-testid='chat-answer-category']"), (
        "chat-answer-category badge must be visible after answer"
    )


def test_chat_category_market_value_is_valuation(page: Page, live_server: str) -> None:
    """[50] 'ما الفرق بين القيمة السوقية والقيمة الاستثمارية' → category badge = تقييم عقاري."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "ما الفرق بين القيمة السوقية والقيمة الاستثمارية؟")
    page.wait_for_selector("[data-testid='chat-answer-category']", state="visible", timeout=5_000)
    badge_text = page.locator("[data-testid='chat-answer-category']").inner_text()
    assert "تقييم عقاري" in badge_text, (
        f"Expected category 'تقييم عقاري', got: {badge_text!r}"
    )


def test_chat_category_tax_question(page: Page, live_server: str) -> None:
    """[51] Tax question → category badge = ضرائب وطعون."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "كيف أطعن على تقدير الضرائب العقارية لعقار أو مصنع غير مستغل؟")
    page.wait_for_selector("[data-testid='chat-answer-category']", state="visible", timeout=5_000)
    badge_text = page.locator("[data-testid='chat-answer-category']").inner_text()
    assert "ضرائب" in badge_text, (
        f"Expected category 'ضرائب وطعون', got: {badge_text!r}"
    )


def test_chat_category_feasibility_question(page: Page, live_server: str) -> None:
    """[52] Feasibility question → category badge = دراسة جدوى / استثمار."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "كيف أعمل دراسة جدوى لمشروع عقاري؟")
    page.wait_for_selector("[data-testid='chat-answer-category']", state="visible", timeout=5_000)
    badge_text = page.locator("[data-testid='chat-answer-category']").inner_text()
    assert "جدوى" in badge_text or "استثمار" in badge_text, (
        f"Expected category 'دراسة جدوى / استثمار', got: {badge_text!r}"
    )


def test_chat_category_court_question(page: Page, live_server: str) -> None:
    """[53] Court/inheritance question → category badge = نزاعات ومحاكم."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "كيف تحسب المحكمة قيمة العقار في قضايا الفرز والتجنيب؟")
    page.wait_for_selector("[data-testid='chat-answer-category']", state="visible", timeout=5_000)
    badge_text = page.locator("[data-testid='chat-answer-category']").inner_text()
    assert "نزاع" in badge_text or "محاكم" in badge_text, (
        f"Expected category 'نزاعات ومحاكم', got: {badge_text!r}"
    )


def test_chat_complexity_indicator_appears(page: Page, live_server: str) -> None:
    """[54] chat-complexity-indicator element is visible after receiving an answer."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "ما الفرق بين القيمة السوقية والقيمة الاستثمارية؟")
    page.wait_for_selector("[data-testid='chat-complexity-indicator']", state="visible", timeout=5_000)
    assert page.is_visible("[data-testid='chat-complexity-indicator']"), (
        "chat-complexity-indicator must be visible after answer"
    )


def test_chat_complexity_expert_required_for_tax(page: Page, live_server: str) -> None:
    """[55] Tax question → complexity indicator shows 'تحتاج خبير'."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "كيف أطعن على تقدير الضرائب العقارية لعقار أو مصنع غير مستغل؟")
    page.wait_for_selector("[data-testid='chat-complexity-indicator']", state="visible", timeout=5_000)
    cx_text = page.locator("[data-testid='chat-complexity-indicator']").inner_text()
    assert "تحتاج خبير" in cx_text, (
        f"Tax question must show complexity 'تحتاج خبير', got: {cx_text!r}"
    )


def test_chat_complexity_expert_required_for_court(page: Page, live_server: str) -> None:
    """[56] Court question → complexity indicator shows 'تحتاج خبير'."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "كيف تحسب المحكمة قيمة العقار في قضايا الفرز والتجنيب؟")
    page.wait_for_selector("[data-testid='chat-complexity-indicator']", state="visible", timeout=5_000)
    cx_text = page.locator("[data-testid='chat-complexity-indicator']").inner_text()
    assert "تحتاج خبير" in cx_text, (
        f"Court question must show complexity 'تحتاج خبير', got: {cx_text!r}"
    )


def test_chat_complexity_simple_or_medium_for_concept(page: Page, live_server: str) -> None:
    """[57] Concept question → complexity is 'بسيطة' or 'متوسطة', NOT 'تحتاج خبير'."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "ما الفرق بين معدل الخصم ومعدل الرسملة؟")
    page.wait_for_selector("[data-testid='chat-complexity-indicator']", state="visible", timeout=5_000)
    cx_text = page.locator("[data-testid='chat-complexity-indicator']").inner_text()
    assert "بسيطة" in cx_text or "متوسطة" in cx_text, (
        f"Concept question should be 'بسيطة' or 'متوسطة', got: {cx_text!r}"
    )
    assert "تحتاج خبير" not in cx_text, (
        "Simple concept question must NOT be marked 'تحتاج خبير'"
    )


def test_chat_convert_to_expert_opens_lead_form(page: Page, live_server: str) -> None:
    """[58] Expert CTA button (shown for تحتاج خبير) opens the lead form when clicked."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "كيف أطعن على تقدير الضرائب العقارية لعقار أو مصنع غير مستغل؟")
    page.wait_for_selector("[data-testid='chat-convert-to-expert-request']", state="visible", timeout=5_000)
    page.locator("[data-testid='chat-convert-to-expert-request']").click()
    page.wait_for_selector("[data-testid='expert-lead-form']", state="visible", timeout=5_000)
    assert page.is_visible("[data-testid='expert-lead-form']"), (
        "Lead form must become visible after clicking convert-to-expert"
    )


def test_chat_lead_form_summary_prefilled(page: Page, live_server: str) -> None:
    """[59] Clicking convert-to-expert pre-fills the lead form summary with the question."""
    question = "كيف أطعن على تقدير الضرائب العقارية لعقار أو مصنع غير مستغل؟"
    _open_chat_tab(page, live_server)
    _send_chat_question(page, question)
    page.wait_for_selector("[data-testid='chat-convert-to-expert-request']", state="visible", timeout=5_000)
    page.locator("[data-testid='chat-convert-to-expert-request']").click()
    page.wait_for_selector("[data-testid='expert-lead-form']", state="visible", timeout=5_000)
    summary_val = page.locator("[data-testid='expert-lead-summary']").input_value()
    assert question in summary_val or len(summary_val) > 0, (
        "Lead form summary should be pre-filled with the question text"
    )


def test_chat_follow_up_suggestions_appear(page: Page, live_server: str) -> None:
    """[60] chat-follow-up-suggestions panel is visible after receiving an answer."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "ما الفرق بين القيمة السوقية والقيمة الاستثمارية؟")
    page.wait_for_selector("[data-testid='chat-follow-up-suggestions']", state="visible", timeout=5_000)
    fu_text = page.locator("[data-testid='chat-follow-up-suggestions']").inner_text()
    assert len(fu_text.strip()) > 0, "Follow-up suggestions panel must contain text"


def test_chat_suggested_next_page_tax(page: Page, live_server: str) -> None:
    """[61] Tax question → chat-suggested-next-page shows 'فاحص الضرائب والطعون'."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "كيف أطعن على تقدير الضرائب العقارية لعقار أو مصنع غير مستغل؟")
    page.wait_for_selector("[data-testid='chat-suggested-next-page']", state="visible", timeout=5_000)
    np_text = page.locator("[data-testid='chat-suggested-next-page']").inner_text()
    assert "الضرائب" in np_text or "الطعون" in np_text, (
        f"Tax question should suggest tax checker page, got: {np_text!r}"
    )


def test_chat_source_panel_no_fake_sources(page: Page, live_server: str) -> None:
    """[62] Source panel is visible but shows only RAG-placeholder text, not real sources."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "ما الفرق بين القيمة السوقية والقيمة الاستثمارية؟")
    page.wait_for_selector("[data-testid='chat-source-panel']", state="visible", timeout=5_000)
    panel_text = page.locator("[data-testid='chat-source-panel']").inner_text()
    assert "RAG" in panel_text or "Qdrant" in panel_text or "سيتم" in panel_text, (
        "Source panel must show placeholder text about future RAG activation"
    )
    assert "http://" not in panel_text and "https://" not in panel_text, (
        "Source panel must not contain real URLs"
    )


def test_chat_ux_no_certified_report_claim(page: Page, live_server: str) -> None:
    """[63] UX panels do not falsely claim certified reports or real data sources exist."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "ما الفرق بين القيمة السوقية والقيمة الاستثمارية؟")
    page.wait_for_selector("[data-testid='chat-source-panel']", state="visible", timeout=5_000)
    panel_text = page.locator("[data-testid='chat-source-panel']").inner_text()
    assert "مصادر حقيقية" not in panel_text, "Source panel must not claim real sources"
    assert "مصادر موثقة" not in panel_text, "Source panel must not claim verified sources"
    # Answer area should still carry the existing advisory disclaimer
    answer_text = page.locator("[data-testid='chat-answer-area']").inner_text()
    assert "إرشادية" in answer_text, "Answer must still include advisory disclaimer"
    assert "تقرير تقييم رسمي" not in panel_text, "Source panel must not claim official reports"


# ── Part A: Smart Prompt Tabs (64-66) ─────────────────────────────────────────

def test_chat_prompt_tabs_visible(page: Page, live_server: str) -> None:
    """[64] Prompt tab navigation bar and all 8 tab buttons are visible on chat landing."""
    _open_chat_tab(page, live_server)
    expect(page.locator("[data-testid='chat-prompt-tabs']")).to_be_visible()
    for tid in [
        "chat-prompt-tab-all", "chat-prompt-tab-valuation", "chat-prompt-tab-tax",
        "chat-prompt-tab-court", "chat-prompt-tab-feasibility",
        "chat-prompt-tab-special-assets", "chat-prompt-tab-finance",
        "chat-prompt-tab-concepts",
    ]:
        expect(page.locator(f"[data-testid='{tid}']")).to_be_visible(), (
            f"{tid} tab button must be visible"
        )


def test_chat_prompt_tabs_filter_suggestions(page: Page, live_server: str) -> None:
    """[65] Clicking a tab hides chips of other categories; clicking الكل restores all."""
    _open_chat_tab(page, live_server)
    # Click tax tab — only tax chips should be visible
    page.locator("[data-testid='chat-prompt-tab-tax']").click()
    visible_chips = [
        c for c in page.locator("#ws-chat .chat-chip").all()
        if c.is_visible()
    ]
    assert len(visible_chips) >= 1, "At least one chip must be visible after filtering to tax tab"
    all_chips = page.locator("#ws-chat .chat-chip").all()
    assert len(all_chips) > len(visible_chips), (
        "Filtering should hide some chips (not all chips visible when tax tab is active)"
    )
    # Click الكل — all chips should return
    page.locator("[data-testid='chat-prompt-tab-all']").click()
    visible_after_all = [c for c in page.locator("#ws-chat .chat-chip").all() if c.is_visible()]
    assert len(visible_after_all) >= len(all_chips), (
        "الكل tab must restore all chips"
    )


def test_chat_prompt_tab_filtered_chip_still_works(page: Page, live_server: str) -> None:
    """[66] A chip visible after tab filtering still fills the chat input when clicked."""
    _open_chat_tab(page, live_server)
    page.locator("[data-testid='chat-prompt-tab-tax']").click()
    visible_chips = [c for c in page.locator("#ws-chat .chat-chip").all() if c.is_visible()]
    assert len(visible_chips) >= 1, "At least one tax chip must be visible"
    visible_chips[0].click()
    filled = page.locator("[data-testid='chat-input']").input_value()
    assert len(filled.strip()) > 5, (
        f"Filtered chip must still fill input, got: {filled!r}"
    )


# ── Part B: Smart Auto-Fill (67-69) ──────────────────────────────────────────

def test_chat_autofill_property_type_and_location(page: Page, live_server: str) -> None:
    """[67] Question 'مصنع في العاشر من رمضان' fills property-type and location if empty."""
    _open_chat_tab(page, live_server)
    page.locator("[data-testid='chat-property-type']").fill("")
    page.locator("[data-testid='chat-location']").fill("")
    _send_chat_question(page, "عندي مصنع في العاشر من رمضان وجاتلي ضريبة عالية")
    prop = page.locator("[data-testid='chat-property-type']").input_value()
    loc  = page.locator("[data-testid='chat-location']").input_value()
    assert "مصنع" in prop, f"Property type should contain مصنع, got: {prop!r}"
    assert loc.strip() != "", f"Location should be filled from question, got: {loc!r}"


def test_chat_autofill_does_not_overwrite_existing(page: Page, live_server: str) -> None:
    """[68] Auto-fill must NOT overwrite user-entered property type or location."""
    _open_chat_tab(page, live_server)
    page.locator("[data-testid='chat-property-type']").fill("فيلا")
    page.locator("[data-testid='chat-location']").fill("القاهرة")
    _send_chat_question(page, "عندي مصنع في العاشر من رمضان وجاتلي ضريبة عالية")
    prop = page.locator("[data-testid='chat-property-type']").input_value()
    loc  = page.locator("[data-testid='chat-location']").input_value()
    assert prop == "فيلا",    f"Existing property type must not be overwritten, got: {prop!r}"
    assert loc  == "القاهرة", f"Existing location must not be overwritten, got: {loc!r}"


def test_chat_autofill_ambiguous_no_random_fill(page: Page, live_server: str) -> None:
    """[69] Ambiguous question without property type or location cue does not fill garbage."""
    _open_chat_tab(page, live_server)
    page.locator("[data-testid='chat-property-type']").fill("")
    page.locator("[data-testid='chat-location']").fill("")
    _send_chat_question(page, "ما الفرق بين معدل الخصم ومعدل الرسملة؟")
    prop = page.locator("[data-testid='chat-property-type']").input_value()
    loc  = page.locator("[data-testid='chat-location']").input_value()
    # Must not have filled nonsense from a pure-concept question
    assert prop == "", f"No property type should be extracted from concept question, got: {prop!r}"
    assert loc  == "", f"No location should be extracted from concept question, got: {loc!r}"


# ── Part C: Suggested Next Page Button (70-72) ────────────────────────────────

def test_chat_next_page_button_tax(page: Page, live_server: str) -> None:
    """[70] Tax question shows a chat-next-page-button with الضرائب/الطعون label."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "كيف أطعن على تقدير الضرائب العقارية لعقار أو مصنع غير مستغل؟")
    page.wait_for_selector("[data-testid='chat-next-page-button']", state="visible", timeout=5_000)
    btn_text = page.locator("[data-testid='chat-next-page-button']").inner_text()
    assert "الضرائب" in btn_text or "الطعون" in btn_text, (
        f"Tax next-page button must mention الضرائب or الطعون, got: {btn_text!r}"
    )


def test_chat_next_page_button_special_asset(page: Page, live_server: str) -> None:
    """[71] Specialized-asset question shows a chat-next-page-button for التقييم المحترف."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "ما المنهجية المناسبة لتقييم مستشفى أو فندق أو مصنع كأصل متخصص؟")
    page.wait_for_selector("[data-testid='chat-next-page-button']", state="visible", timeout=5_000)
    btn_text = page.locator("[data-testid='chat-next-page-button']").inner_text()
    assert "المحترف" in btn_text or "التقييم" in btn_text, (
        f"Special-asset next-page button must mention المحترف or التقييم, got: {btn_text!r}"
    )


def test_chat_next_page_button_no_crash(page: Page, live_server: str) -> None:
    """[72] Clicking the next-page button does not crash; page stays functional."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "كيف أطعن على تقدير الضرائب العقارية لعقار أو مصنع غير مستغل؟")
    page.wait_for_selector("[data-testid='chat-next-page-button']", state="visible", timeout=5_000)
    # Clicking may switch to another tab — just verify no JS exception is thrown
    dialogs: list = []
    page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
    page.locator("[data-testid='chat-next-page-button']").click()
    assert len(dialogs) == 0, f"Unexpected JS dialog after button click: {dialogs}"
    # Page should still be loaded and navigable
    assert page.title() is not None


# ── Part D: Dynamic Expert Card (73-74) ──────────────────────────────────────

def test_chat_dynamic_expert_card_tax(page: Page, live_server: str) -> None:
    """[73] Tax question shows the dynamic expert card with 'خبير' text and CTA button."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "كيف أطعن على تقدير الضرائب العقارية لعقار أو مصنع غير مستغل؟")
    page.wait_for_selector("[data-testid='chat-dynamic-expert-card']", state="visible", timeout=5_000)
    card_text = page.locator("[data-testid='chat-dynamic-expert-card']").inner_text()
    assert "خبير" in card_text, (
        f"Dynamic expert card must contain 'خبير', got: {card_text!r}"
    )
    expect(page.locator("[data-testid='chat-convert-to-expert-request']")).to_be_visible()


def test_chat_dynamic_expert_card_not_for_concept(page: Page, live_server: str) -> None:
    """[74] Simple concept question must NOT show the dynamic expert card."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "ما الفرق بين معدل الخصم ومعدل الرسملة؟")
    page.wait_for_selector("[data-testid='chat-complexity-indicator']", state="visible", timeout=5_000)
    card = page.locator("[data-testid='chat-dynamic-expert-card']")
    assert not card.is_visible(), (
        "Dynamic expert card must NOT appear for simple concept questions"
    )


# ── Part E: Web/RAG Toggle Wording (75-76) ───────────────────────────────────

def test_chat_web_rag_toggle_honest_message(page: Page, live_server: str) -> None:
    """[75] Web toggle shows honest future-ready message mentioning RAG/Qdrant/Backend Advisor."""
    _open_chat_tab(page, live_server)
    page.locator("[data-testid='chat-web-toggle-label']").click()
    err = page.locator("#chat-error")
    expect(err).to_be_visible(timeout=3_000)
    msg = err.inner_text()
    assert "RAG" in msg or "Qdrant" in msg or "Backend Advisor" in msg, (
        f"Toggle message must mention RAG/Qdrant/Backend Advisor, got: {msg!r}"
    )
    assert not page.locator("#chat-web-toggle").is_checked()


def test_chat_web_rag_toggle_no_fake_loading(page: Page, live_server: str) -> None:
    """[76] Web toggle must not show fake loading message like 'جاري فحص'."""
    _open_chat_tab(page, live_server)
    page.locator("[data-testid='chat-web-toggle-label']").click()
    err = page.locator("#chat-error")
    msg = err.inner_text() if err.is_visible() else ""
    assert "جاري فحص" not in msg, (
        f"Toggle must not show fake loading state; got: {msg!r}"
    )
    assert not page.locator("#chat-web-toggle").is_checked()


# ── Part F: No Direct PDF / Certified Report (77-78) ─────────────────────────

def test_chat_no_direct_pdf_generation(page: Page, live_server: str) -> None:
    """[77] Asking for a report never triggers a PDF download or certified-report claim."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "أريد تقرير تقييم رسمي للعقار")
    text = page.locator("[data-testid='chat-answer-area']").inner_text()
    assert "إرشادية" in text or "لا يُعد" in text, (
        "Answer must contain advisory disclaimer"
    )
    assert "تنزيل PDF" not in text, "Chat must not offer a PDF download link"
    assert "تحميل التقرير" not in text, "Chat must not offer a report download"


def test_chat_report_question_no_certified_claim(page: Page, live_server: str) -> None:
    """[78] Report-related question does not falsely claim to generate a certified report."""
    _open_chat_tab(page, live_server)
    _send_chat_question(page, "كيف أحصل على تقرير تقييم معتمد؟")
    text = page.locator("[data-testid='chat-answer-area']").inner_text()
    assert "هذا تقرير تقييم رسمي معتمد" not in text, (
        "Chat must not claim to generate a certified report"
    )
    assert len(text.strip()) > 20, "Answer must be non-trivially long"
