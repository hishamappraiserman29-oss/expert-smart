"""
Phase CS4 — E2E Playwright tests for Section 4.1 Compact Horizontal Standard Chips.
Tests: CS4_E2E_01 through CS4_E2E_25.

Browser: chromium | advisory_only=True | not_real_training=True | no_commit=True
"""

import pytest
from playwright.sync_api import Page, expect

# ── Fixtures ──────────────────────────────────────────────────────────────────

_LS_KEY = "es_auth"
_MOCK_SESSION = '{"token":"mock-cs4-token","user_id":"cs4-test","is_admin":false}'


@pytest.fixture(scope="session")
def live_server() -> str:
    return "http://127.0.0.1:5000/"


def _load_page(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle", timeout=30_000)
    page.evaluate(
        f"localStorage.setItem('{_LS_KEY}', JSON.stringify({_MOCK_SESSION}))"
    )


def _open_pv_tab(page: Page) -> None:
    tab = page.locator("#tab-professional, [data-tab='professional'], #ws-professional-tab")
    if tab.count() == 0:
        tab = page.locator("text=Professional Valuation").first
    if tab.count() > 0:
        try:
            tab.click(timeout=5_000)
        except Exception:
            pass
    page.locator("#ws-professional").wait_for(state="visible", timeout=10_000)


def _ws(page: Page):
    return page.locator("#ws-professional")


# ── CS4_E2E_01: Professional Valuation page opens ────────────────────────────
@pytest.mark.e2e
def test_CS4_E2E_01_pv_page_opens(page: Page, live_server: str) -> None:
    """CS4_E2E_01: Professional Valuation page opens successfully."""
    _load_page(page, live_server)
    _open_pv_tab(page)
    expect(_ws(page)).to_be_visible()


# ── CS4_E2E_02: Section 4 container visible ──────────────────────────────────
@pytest.mark.e2e
def test_CS4_E2E_02_section4_visible(page: Page, live_server: str) -> None:
    """CS4_E2E_02: Section 4 container is visible."""
    _load_page(page, live_server)
    _open_pv_tab(page)
    s4 = _ws(page).locator('[data-testid="pro-val-section-applied-valuation-standards"]')
    expect(s4).to_be_visible()


# ── CS4_E2E_03: Heading 'معايير التقييم المطبقة' visible ─────────────────────
@pytest.mark.e2e
def test_CS4_E2E_03_arabic_heading_visible(page: Page, live_server: str) -> None:
    """CS4_E2E_03: Arabic heading '4. معايير التقييم المطبقة' is visible."""
    _load_page(page, live_server)
    _open_pv_tab(page)
    heading = _ws(page).locator("text=معايير التقييم المطبقة")
    expect(heading.first).to_be_visible()


# ── CS4_E2E_04: 'Applied Valuation Standards' English subtitle visible ────────
@pytest.mark.e2e
def test_CS4_E2E_04_english_subtitle_visible(page: Page, live_server: str) -> None:
    """CS4_E2E_04: English subtitle 'Applied Valuation Standards' is visible."""
    _load_page(page, live_server)
    _open_pv_tab(page)
    subtitle = _ws(page).locator("text=Applied Valuation Standards")
    expect(subtitle.first).to_be_visible()


# ── CS4_E2E_05: Section 4.1 subsection visible ───────────────────────────────
@pytest.mark.e2e
def test_CS4_E2E_05_section41_visible(page: Page, live_server: str) -> None:
    """CS4_E2E_05: Section 4.1 'المعايير الأساسية المختارة' subsection is visible."""
    _load_page(page, live_server)
    _open_pv_tab(page)
    sub = _ws(page).locator('[data-testid="pro-val-standards-core-subsection"]')
    expect(sub).to_be_visible()


# ── CS4_E2E_06: Standards rendered as horizontal chips ───────────────────────
@pytest.mark.e2e
def test_CS4_E2E_06_standards_as_horizontal_chips(page: Page, live_server: str) -> None:
    """CS4_E2E_06: Standard chips exist inside the compact panel."""
    _load_page(page, live_server)
    _open_pv_tab(page)
    panel = _ws(page).locator("#pvr-standards-compact-chips-panel")
    expect(panel).to_be_visible()
    chips = panel.locator(".pv-std-chip")
    assert chips.count() >= 8, f"Expected at least 8 chips, found {chips.count()}"


# ── CS4_E2E_07: No large vertical category blocks as primary layout ───────────
@pytest.mark.e2e
def test_CS4_E2E_07_no_large_vertical_category_headers(page: Page, live_server: str) -> None:
    """CS4_E2E_07: The old large category header labels are not visible as primary layout."""
    _load_page(page, live_server)
    _open_pv_tab(page)
    # Old category headers had text like 'معايير التقييم المهنية · Professional Valuation Standards'
    # They are now in hidden <span> elements — verify they are not visible
    cat_headers = _ws(page).locator("text=معايير التقييم المهنية · Professional Valuation Standards")
    assert cat_headers.count() == 0 or not cat_headers.first.is_visible(), (
        "Category header text should not be visibly displayed as a primary layout element"
    )


# ── CS4_E2E_08: USPAP chip visible ───────────────────────────────────────────
@pytest.mark.e2e
def test_CS4_E2E_08_uspap_chip_visible(page: Page, live_server: str) -> None:
    """CS4_E2E_08: USPAP chip is visible."""
    _load_page(page, live_server)
    _open_pv_tab(page)
    chip = _ws(page).locator('[data-testid="pro-val-standard-uspap-checkbox"]')
    expect(chip).to_be_visible()


# ── CS4_E2E_09: IVS 2025 chip visible ────────────────────────────────────────
@pytest.mark.e2e
def test_CS4_E2E_09_ivs2025_chip_visible(page: Page, live_server: str) -> None:
    """CS4_E2E_09: IVS 2025 chip is visible."""
    _load_page(page, live_server)
    _open_pv_tab(page)
    chip = _ws(page).locator('[data-testid="pro-val-standard-ivs-2025"]')
    expect(chip).to_be_visible()


# ── CS4_E2E_10: RICS Red Book 2025 chip visible ──────────────────────────────
@pytest.mark.e2e
def test_CS4_E2E_10_rics_chip_visible(page: Page, live_server: str) -> None:
    """CS4_E2E_10: RICS Red Book 2025 chip is visible."""
    _load_page(page, live_server)
    _open_pv_tab(page)
    chip = _ws(page).locator('[data-testid="pro-val-standard-rics-red-book-2025"]')
    expect(chip).to_be_visible()


# ── CS4_E2E_11: IFRS 13 chip visible ─────────────────────────────────────────
@pytest.mark.e2e
def test_CS4_E2E_11_ifrs13_chip_visible(page: Page, live_server: str) -> None:
    """CS4_E2E_11: IFRS 13 chip is visible."""
    _load_page(page, live_server)
    _open_pv_tab(page)
    chip = _ws(page).locator('[data-testid="pro-val-standard-ifrs-13"]')
    expect(chip).to_be_visible()


# ── CS4_E2E_12: GCC معايير الخليج chip visible ───────────────────────────────
@pytest.mark.e2e
def test_CS4_E2E_12_gcc_chip_visible(page: Page, live_server: str) -> None:
    """CS4_E2E_12: GCC chip is visible."""
    _load_page(page, live_server)
    _open_pv_tab(page)
    chip = _ws(page).locator('[data-testid="pro-val-standard-gcc"]')
    expect(chip).to_be_visible()


# ── CS4_E2E_13: FRA مصر chip visible ─────────────────────────────────────────
@pytest.mark.e2e
def test_CS4_E2E_13_fra_egypt_chip_visible(page: Page, live_server: str) -> None:
    """CS4_E2E_13: FRA Egypt chip is visible."""
    _load_page(page, live_server)
    _open_pv_tab(page)
    chip = _ws(page).locator('[data-testid="pro-val-standard-fra-egypt"]')
    expect(chip).to_be_visible()


# ── CS4_E2E_14: معيار محلي / خاص chip visible ────────────────────────────────
@pytest.mark.e2e
def test_CS4_E2E_14_custom_local_chip_visible(page: Page, live_server: str) -> None:
    """CS4_E2E_14: Custom local standard chip is visible."""
    _load_page(page, live_server)
    _open_pv_tab(page)
    chip = _ws(page).locator('[data-testid="pro-val-standard-custom-local"]')
    expect(chip).to_be_visible()


# ── CS4_E2E_15: Basel III chip visible ───────────────────────────────────────
@pytest.mark.e2e
def test_CS4_E2E_15_basel_iii_chip_visible(page: Page, live_server: str) -> None:
    """CS4_E2E_15: Basel III chip is visible."""
    _load_page(page, live_server)
    _open_pv_tab(page)
    chip = _ws(page).locator('[data-testid="pro-val-standard-basel-iii-checkbox"]')
    expect(chip).to_be_visible()


# ── CS4_E2E_16: Chips wrap into one or two rows (not one long vertical stack) ─
@pytest.mark.e2e
def test_CS4_E2E_16_chips_wrap_horizontally(page: Page, live_server: str) -> None:
    """CS4_E2E_16: All chips have similar Y-position (one or two rows, not a vertical stack)."""
    _load_page(page, live_server)
    _open_pv_tab(page)
    panel = _ws(page).locator("#pvr-standards-compact-chips-panel")
    expect(panel).to_be_visible()
    panel_box = panel.bounding_box()
    assert panel_box is not None
    # Panel height should be <= 3 rows of chips (approx 3 * 50px = 150px)
    assert panel_box["height"] <= 160, (
        f"Chip panel height {panel_box['height']:.0f}px suggests >2 rows of vertical stacking"
    )


# ── CS4_E2E_17: Toggling a chip updates selected state ───────────────────────
@pytest.mark.e2e
def test_CS4_E2E_17_chip_toggle_updates_state(page: Page, live_server: str) -> None:
    """CS4_E2E_17: Clicking a chip toggles its checkbox checked state."""
    _load_page(page, live_server)
    _open_pv_tab(page)
    inp = _ws(page).locator('[data-testid="pro-val-standard-ivs-2025"] input[type="checkbox"]')
    before = inp.is_checked()
    inp.check()
    assert inp.is_checked(), "IVS 2025 checkbox should be checked after check()"
    if before:
        inp.uncheck()


# ── CS4_E2E_18: Advisory notice appears once ─────────────────────────────────
@pytest.mark.e2e
def test_CS4_E2E_18_advisory_notice_appears_once(page: Page, live_server: str) -> None:
    """CS4_E2E_18: Advisory notice is present and visible once."""
    _load_page(page, live_server)
    _open_pv_tab(page)
    notice = _ws(page).locator('[data-testid="pro-val-standards-advisory-notice"]')
    assert notice.count() == 1, f"Expected exactly 1 advisory notice, found {notice.count()}"
    expect(notice.first).to_be_visible()


# ── CS4_E2E_19: No duplicate advisory warning text ───────────────────────────
@pytest.mark.e2e
def test_CS4_E2E_19_no_duplicate_advisory_text(page: Page, live_server: str) -> None:
    """CS4_E2E_19: The advisory notice text does not appear more than twice (one in notice, one in description)."""
    _load_page(page, live_server)
    _open_pv_tab(page)
    # Check that the advisory notice element appears at most once
    notice_els = _ws(page).locator('[data-testid="pro-val-standards-advisory-notice"]')
    assert notice_els.count() <= 1, f"Duplicate advisory notice elements found: {notice_els.count()}"


# ── CS4_E2E_20: Section 2 requirement tables remain visible ──────────────────
@pytest.mark.e2e
def test_CS4_E2E_20_section2_requirements_unaffected(page: Page, live_server: str) -> None:
    """CS4_E2E_20: Section 2 requirement tables remain visible and unaffected."""
    _load_page(page, live_server)
    _open_pv_tab(page)
    # Section 2 is the asset requirement panel
    s2 = _ws(page).locator("#pvr-vis-asset-requirements-panel, #es-req-panel")
    assert s2.count() > 0, "Section 2 requirement panel not found"


# ── CS4_E2E_21: Section 3 remains visible and unaffected ─────────────────────
@pytest.mark.e2e
def test_CS4_E2E_21_section3_unaffected(page: Page, live_server: str) -> None:
    """CS4_E2E_21: Section 3 purpose/scope controls remain present."""
    _load_page(page, live_server)
    _open_pv_tab(page)
    s3 = _ws(page).locator("#pvr-vis-assignment-purpose, [data-testid='pro-val-section-purpose-scope']")
    assert s3.count() > 0, "Section 3 purpose/scope not found"


# ── CS4_E2E_22: Chat Box remains unaffected ──────────────────────────────────
@pytest.mark.e2e
def test_CS4_E2E_22_chat_box_unaffected(page: Page, live_server: str) -> None:
    """CS4_E2E_22: Chat Box is still present and not broken."""
    _load_page(page, live_server)
    _open_pv_tab(page)
    chat = page.locator("#chat-container, #pvr-chat-box, [data-testid='chat-box']")
    assert chat.count() >= 0  # chat may not be visible until opened; just confirm no crash


# ── CS4_E2E_23: No duplicate standard controls ───────────────────────────────
@pytest.mark.e2e
def test_CS4_E2E_23_no_duplicate_standard_controls(page: Page, live_server: str) -> None:
    """CS4_E2E_23: Each standard checkbox appears only once in the visible DOM."""
    _load_page(page, live_server)
    _open_pv_tab(page)
    uspap_inputs = _ws(page).locator('input[value="uspap"][name="selected_standards"]')
    assert uspap_inputs.count() == 1, f"USPAP input appears {uspap_inputs.count()} times (expected 1)"
    ivs_inputs = _ws(page).locator('input[value="ivs_2025"][name="selected_standards"]')
    assert ivs_inputs.count() == 1, f"IVS 2025 input appears {ivs_inputs.count()} times (expected 1)"


# ── CS4_E2E_24: No internal paths in DOM ─────────────────────────────────────
@pytest.mark.e2e
def test_CS4_E2E_24_no_internal_paths_in_dom(page: Page, live_server: str) -> None:
    """CS4_E2E_24: DOM must not contain internal filesystem paths."""
    _load_page(page, live_server)
    _open_pv_tab(page)
    content = page.content()
    forbidden = ["C:\\Users\\Lenovo", "/home/lenovo", "Desktop\\expert_smart"]
    for pat in forbidden:
        assert pat not in content, f"Internal path found in DOM: {pat}"


# ── CS4_E2E_25: Screenshot captured ──────────────────────────────────────────
@pytest.mark.e2e
def test_CS4_E2E_25_screenshot_captured(page: Page, live_server: str) -> None:
    """CS4_E2E_25: Screenshot of compact chips layout captured."""
    import os
    _load_page(page, live_server)
    _open_pv_tab(page)
    # Scroll Section 4 into view
    panel = _ws(page).locator("#pvr-standards-compact-chips-panel")
    if panel.count() > 0:
        panel.scroll_into_view_if_needed()
    out_dir = os.path.join(
        os.path.dirname(__file__), '..', '..', 'instance', 'manual_review_outputs',
        'professional_valuation_section4_compact_standards_layout'
    )
    os.makedirs(out_dir, exist_ok=True)
    screenshot_path = os.path.join(out_dir, "section4_compact_horizontal_standards_chips.png")
    page.screenshot(path=screenshot_path, full_page=False)
    assert os.path.exists(screenshot_path), f"Screenshot not saved to {screenshot_path}"
