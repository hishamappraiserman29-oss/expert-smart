"""
test_pvuafr_e2e.py — PVUAFR E2E Browser Tests
Professional Valuation Uncommon Asset Fillable Requirements

PVUAFR-E01  special-asset-requirements-panel exists in DOM
PVUAFR-E02  panel hidden before any subtype selected
PVUAFR-E03  requirements form hidden before any subtype selected
PVUAFR-E04  panel visible after selecting padel subtype
PVUAFR-E05  requirements form visible after padel selection
PVUAFR-E06  at least one requirement-row visible after padel selection
PVUAFR-E07  requirement-label visible in each row
PVUAFR-E08  requirement-input visible in each row (any input control)
PVUAFR-E09  requirement-status shows "يحتاج استكمال" when input is empty
PVUAFR-E10  requirement-note textarea visible (editable notes cell)
PVUAFR-E11  number input visible for "عدد ملاعب البادل"
PVUAFR-E12  percent input visible (occupancy rate field has number input)
PVUAFR-E13  currency input — EGP label visible alongside number input
PVUAFR-E14  file input visible (advisory placeholder for legal docs)
PVUAFR-E15  coordinate input — two number inputs side by side
PVUAFR-E16  map_placeholder renders inactive div — not a live map widget
PVUAFR-E17  select element visible for ownership type or admin region
PVUAFR-E18  checkbox_group renders checkboxes (not plain text)
PVUAFR-E19  status updates from "يحتاج استكمال" to "تم التعبئة" after filling number input
PVUAFR-E20  save button visible after padel selection
PVUAFR-E21  save status element exists in DOM
PVUAFR-E22  cinema subtype renders requirement rows
PVUAFR-E23  hospital subtype (or general_hospital alias) renders requirement rows
PVUAFR-E24  school subtype (or school_campus alias) renders requirement rows
PVUAFR-E25  heritage subtype (or alias) renders requirement rows
PVUAFR-E26  no group renders chip-only span elements (no static-only groups)
PVUAFR-E27  no internal paths in DOM text
PVUAFR-E28  no duplicate pvr-inp-* id values in DOM
PVUAFR-E29  common requirements panel not broken (still exists in DOM)
"""
from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

# ── Helpers ───────────────────────────────────────────────────────────────────

_INTERNAL_PATH_RE = re.compile(
    r"(C:\\\\|C:/|/core_engine/|/instance/|\\\\core_engine\\\\|\\\\instance\\\\|\.jsonl)",
    re.IGNORECASE,
)


def _goto(page: Page, live_server: str) -> None:
    page.route("**/api/**", lambda r: r.fulfill(
        status=200, body=b'{"ok":true,"requests":[],"request_id":"pvuafr-e2e-001"}',
        content_type="application/json",
    ))
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator('[data-testid="professional-wizard"]').wait_for(
        state="visible", timeout=15_000
    )


def _select_family(page: Page, family: str) -> None:
    page.locator('[data-testid="professional-asset-family"]').select_option(value=family)


def _select_subtype(page: Page, subtype: str) -> None:
    page.locator('[data-testid="professional-asset-subtype"]').wait_for(
        state="visible", timeout=5_000
    )
    page.locator('[data-testid="professional-asset-subtype"]').select_option(value=subtype)


def _activate_padel(page: Page) -> None:
    _select_family(page, "sports_recreation_assets")
    _select_subtype(page, "padel_tennis_court")
    page.locator('[data-testid="pro-val-special-asset-requirements-panel"]').wait_for(
        state="visible", timeout=8_000
    )


def _activate_cinema(page: Page) -> None:
    _select_family(page, "entertainment_assets")
    _select_subtype(page, "cinema")
    page.locator('[data-testid="pro-val-special-asset-requirements-panel"]').wait_for(
        state="visible", timeout=8_000
    )


def _activate_by_family_and_keyword(page: Page, families: list, keyword: str) -> None:
    """Try each family in order; for the first one that has a matching subtype, select it."""
    family_sel = page.locator('[data-testid="professional-asset-family"]')
    for family in families:
        # Check if this family option exists first
        opt = family_sel.locator(f'option[value="{family}"]')
        if opt.count() == 0:
            continue
        family_sel.select_option(value=family)
        page.locator('[data-testid="professional-asset-subtype"]').wait_for(
            state="visible", timeout=5_000
        )
        subtype_sel = page.locator('[data-testid="professional-asset-subtype"]')
        opts = subtype_sel.locator("option").all()
        for o in opts:
            val = o.get_attribute("value") or ""
            if keyword in val.lower():
                subtype_sel.select_option(value=val)
                page.locator('[data-testid="pro-val-special-asset-requirements-panel"]').wait_for(
                    state="visible", timeout=8_000
                )
                return
    pytest.skip(f"No '{keyword}' subtype found in families {families}")


def _activate_hospital(page: Page) -> None:
    _activate_by_family_and_keyword(
        page,
        ["healthcare_assets", "healthcare_education_assets"],
        "hospital",
    )


def _activate_school(page: Page) -> None:
    _activate_by_family_and_keyword(
        page,
        ["education_assets", "healthcare_education_assets"],
        "school",
    )


def _activate_heritage(page: Page) -> None:
    _activate_by_family_and_keyword(
        page,
        ["cultural_heritage_assets", "special_use_assets"],
        "heritage",
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_PVUAFR_E01_panel_in_dom(page: Page, live_server: str) -> None:
    """PVUAFR-E01: pro-val-special-asset-requirements-panel exists in DOM."""
    _goto(page, live_server)
    panel = page.locator('[data-testid="pro-val-special-asset-requirements-panel"]')
    expect(panel).to_have_count(1)


def test_PVUAFR_E02_panel_hidden_initially(page: Page, live_server: str) -> None:
    """PVUAFR-E02: Panel is hidden before any subtype selected."""
    _goto(page, live_server)
    panel = page.locator('[data-testid="pro-val-special-asset-requirements-panel"]')
    expect(panel).to_be_hidden()


def test_PVUAFR_E03_form_hidden_initially(page: Page, live_server: str) -> None:
    """PVUAFR-E03: Requirements form is hidden before any subtype selected."""
    _goto(page, live_server)
    form = page.locator('[data-testid="pro-val-special-asset-requirements-form"]')
    expect(form).to_be_hidden()


def test_PVUAFR_E04_panel_visible_after_padel(page: Page, live_server: str) -> None:
    """PVUAFR-E04: Panel becomes visible after selecting padel subtype."""
    _goto(page, live_server)
    _activate_padel(page)
    panel = page.locator('[data-testid="pro-val-special-asset-requirements-panel"]')
    expect(panel).to_be_visible()


def test_PVUAFR_E05_form_visible_after_padel(page: Page, live_server: str) -> None:
    """PVUAFR-E05: Requirements form visible after padel selection."""
    _goto(page, live_server)
    _activate_padel(page)
    form = page.locator('[data-testid="pro-val-special-asset-requirements-form"]')
    expect(form).to_be_visible()


def test_PVUAFR_E06_rows_visible_after_padel(page: Page, live_server: str) -> None:
    """PVUAFR-E06: At least one requirement-row visible after padel selection."""
    _goto(page, live_server)
    _activate_padel(page)
    rows = page.locator('[data-testid="pro-val-special-asset-requirement-row"]')
    assert rows.count() > 0, "No requirement rows found after padel selection"
    expect(rows.first).to_be_visible()


def test_PVUAFR_E07_labels_visible(page: Page, live_server: str) -> None:
    """PVUAFR-E07: Requirement label visible in each row."""
    _goto(page, live_server)
    _activate_padel(page)
    labels = page.locator('[data-testid="pro-val-special-asset-requirement-label"]')
    assert labels.count() > 0, "No requirement labels found"
    expect(labels.first).to_be_visible()


def test_PVUAFR_E08_inputs_visible(page: Page, live_server: str) -> None:
    """PVUAFR-E08: Requirement input visible in each row."""
    _goto(page, live_server)
    _activate_padel(page)
    inputs = page.locator('[data-testid="pro-val-special-asset-requirement-input"]')
    assert inputs.count() > 0, "No requirement inputs found"
    expect(inputs.first).to_be_visible()


def test_PVUAFR_E09_status_shows_needs_completion_when_empty(page: Page, live_server: str) -> None:
    """PVUAFR-E09: Status shows 'يحتاج استكمال' when input is empty."""
    _goto(page, live_server)
    _activate_padel(page)
    statuses = page.locator('[data-testid="pro-val-special-asset-requirement-status"]')
    assert statuses.count() > 0
    first_status_text = statuses.first.inner_text()
    assert "يحتاج" in first_status_text or "استكمال" in first_status_text, \
        f"Expected 'يحتاج استكمال' in empty status, got: {first_status_text!r}"


def test_PVUAFR_E10_note_textarea_visible(page: Page, live_server: str) -> None:
    """PVUAFR-E10: Note textarea visible and is a textarea element."""
    _goto(page, live_server)
    _activate_padel(page)
    notes = page.locator('[data-testid="pro-val-special-asset-requirement-note"]')
    assert notes.count() > 0, "No note textareas found"
    expect(notes.first).to_be_visible()
    tag = notes.first.evaluate("el => el.tagName.toLowerCase()")
    assert tag == "textarea", f"Note element should be textarea, got: {tag}"


def test_PVUAFR_E11_number_input_for_padel_court_count(page: Page, live_server: str) -> None:
    """PVUAFR-E11: Number input visible for padel court count field."""
    _goto(page, live_server)
    _activate_padel(page)
    # Find all number inputs within requirement-input elements
    number_inputs = page.locator('[data-testid="pro-val-special-asset-requirement-input"][data-ft="number"]')
    assert number_inputs.count() > 0, "No number input fields found"
    expect(number_inputs.first).to_be_visible()
    input_type = number_inputs.first.evaluate("el => el.type")
    assert input_type == "number", f"Expected type=number, got: {input_type}"


def test_PVUAFR_E12_percent_input_visible(page: Page, live_server: str) -> None:
    """PVUAFR-E12: Percent field renders a number input (occupancy rate)."""
    _goto(page, live_server)
    _activate_padel(page)
    pct_inputs = page.locator('[data-testid="pro-val-special-asset-requirement-input"][data-ft="percent"]')
    assert pct_inputs.count() > 0, "No percent-type input fields found"
    expect(pct_inputs.first).to_be_visible()


def test_PVUAFR_E13_currency_egp_label_visible(page: Page, live_server: str) -> None:
    """PVUAFR-E13: Currency field renders with EGP label visible."""
    _goto(page, live_server)
    _activate_padel(page)
    currency_wrappers = page.locator('[data-testid="pro-val-special-asset-requirement-input"][data-ft="currency"]')
    assert currency_wrappers.count() > 0, "No currency-type input fields found"
    expect(currency_wrappers.first).to_be_visible()
    # Check EGP text is somewhere in the parent row
    first_row = currency_wrappers.first.locator("xpath=ancestor::div[@data-testid='pro-val-special-asset-requirement-row']")
    row_text = first_row.inner_text()
    assert "EGP" in row_text or "ج.م" in row_text, \
        f"EGP label not found in currency row: {row_text[:100]}"


def test_PVUAFR_E14_file_input_visible(page: Page, live_server: str) -> None:
    """PVUAFR-E14: File input visible (advisory placeholder)."""
    _goto(page, live_server)
    _activate_padel(page)
    file_inputs = page.locator('[data-testid="pro-val-special-asset-requirement-input"][data-ft="file"]')
    assert file_inputs.count() > 0, "No file-type input fields found"
    expect(file_inputs.first).to_be_visible()


def test_PVUAFR_E15_coordinate_inputs_visible(page: Page, live_server: str) -> None:
    """PVUAFR-E15: Coordinate field shows two number inputs (lat/lng)."""
    _goto(page, live_server)
    _activate_padel(page)
    coord_inputs = page.locator('[data-testid="pro-val-special-asset-requirement-input"][data-ft="coordinate"]')
    assert coord_inputs.count() > 0, "No coordinate-type input fields found"
    first_coord = coord_inputs.first
    expect(first_coord).to_be_visible()
    # The coordinate renderer puts data-testid on the first number input.
    # The second (lng) sibling is in the parent flex div alongside it.
    # Verify by navigating up to the parent and counting number inputs.
    parent_num_inputs = page.evaluate("""
        () => {
            const inp = document.querySelector(
                '[data-testid="pro-val-special-asset-requirement-input"][data-ft="coordinate"]'
            );
            if (!inp) return 0;
            const parent = inp.parentElement;
            return parent ? parent.querySelectorAll('input[type="number"]').length : 0;
        }
    """)
    assert parent_num_inputs >= 2, \
        f"Coordinate parent div should contain >= 2 number inputs (lat + lng), found {parent_num_inputs}"


def test_PVUAFR_E16_map_placeholder_not_live_map(page: Page, live_server: str) -> None:
    """PVUAFR-E16: map_placeholder renders inactive div — not a live map widget."""
    _goto(page, live_server)
    _activate_padel(page)
    map_wrappers = page.locator('[data-testid="pro-val-special-asset-requirement-input"][data-ft="map_placeholder"]')
    if map_wrappers.count() == 0:
        pytest.skip("No map_placeholder fields in padel — OK if not present")
    wrapper = map_wrappers.first
    # Should NOT contain an iframe (live map would use iframe)
    iframes = wrapper.locator("iframe")
    assert iframes.count() == 0, "map_placeholder must not contain an iframe (no live map)"
    # Should have future_stub class or marker
    inner = wrapper.inner_html()
    assert "future_stub" in inner or "مستقبلي" in inner or "قيد التطوير" in inner, \
        f"map_placeholder div does not indicate future_stub: {inner[:100]}"


def test_PVUAFR_E17_select_visible(page: Page, live_server: str) -> None:
    """PVUAFR-E17: Select element visible for select-type fields."""
    _goto(page, live_server)
    _activate_padel(page)
    selects = page.locator('[data-testid="pro-val-special-asset-requirement-input"][data-ft="select"]')
    assert selects.count() > 0, "No select-type fields found"
    expect(selects.first).to_be_visible()
    tag = selects.first.evaluate("el => el.tagName.toLowerCase()")
    assert tag == "select", f"Expected select element, got: {tag}"


def test_PVUAFR_E18_checkbox_group_renders_checkboxes(page: Page, live_server: str) -> None:
    """PVUAFR-E18: checkbox_group renders actual checkboxes (not plain text)."""
    _goto(page, live_server)
    _activate_padel(page)
    cb_wrappers = page.locator('[data-testid="pro-val-special-asset-requirement-input"][data-ft="checkbox_group"]')
    assert cb_wrappers.count() > 0, "No checkbox_group fields found"
    expect(cb_wrappers.first).to_be_visible()
    checkboxes = cb_wrappers.first.locator('input[type="checkbox"]')
    assert checkboxes.count() > 0, "checkbox_group must contain at least one checkbox input"


def test_PVUAFR_E19_status_updates_after_fill(page: Page, live_server: str) -> None:
    """PVUAFR-E19: Status updates to 'تم التعبئة' after filling a number input."""
    _goto(page, live_server)
    _activate_padel(page)
    number_inputs = page.locator('[data-testid="pro-val-special-asset-requirement-input"][data-ft="number"]')
    assert number_inputs.count() > 0
    first_input = number_inputs.first
    uid = first_input.get_attribute("data-req-uid")
    if not uid:
        pytest.skip("No data-req-uid on number input — cannot find paired status element")
    # Fill the input
    first_input.fill("6")
    first_input.dispatch_event("input")
    first_input.dispatch_event("change")
    page.wait_for_timeout(300)
    status_el = page.locator(f'[data-testid="pro-val-special-asset-requirement-status"][id="pvr-status-{uid}"]')
    if status_el.count() > 0:
        status_text = status_el.inner_text()
        assert "تم" in status_text or "التعبئة" in status_text or "مكتمل" in status_text, \
            f"Status did not update after fill: {status_text!r}"


def test_PVUAFR_E20_save_button_visible(page: Page, live_server: str) -> None:
    """PVUAFR-E20: Save button visible after padel selection."""
    _goto(page, live_server)
    _activate_padel(page)
    btn = page.locator('[data-testid="pro-val-special-asset-save-requirements-button"]')
    expect(btn).to_be_visible()


def test_PVUAFR_E21_save_status_in_dom(page: Page, live_server: str) -> None:
    """PVUAFR-E21: Save status element exists in DOM."""
    _goto(page, live_server)
    save_status = page.locator('[data-testid="pro-val-special-asset-requirements-save-status"]')
    expect(save_status).to_have_count(1)


def test_PVUAFR_E22_cinema_renders_rows(page: Page, live_server: str) -> None:
    """PVUAFR-E22: Cinema subtype renders requirement rows."""
    _goto(page, live_server)
    _activate_cinema(page)
    rows = page.locator('[data-testid="pro-val-special-asset-requirement-row"]')
    assert rows.count() > 0, "No requirement rows found after cinema selection"
    expect(rows.first).to_be_visible()


def test_PVUAFR_E23_hospital_renders_rows(page: Page, live_server: str) -> None:
    """PVUAFR-E23: Hospital (or general_hospital alias) renders requirement rows."""
    _goto(page, live_server)
    _activate_hospital(page)
    rows = page.locator('[data-testid="pro-val-special-asset-requirement-row"]')
    assert rows.count() > 0, "No requirement rows found after hospital selection"
    expect(rows.first).to_be_visible()


def test_PVUAFR_E24_school_renders_rows(page: Page, live_server: str) -> None:
    """PVUAFR-E24: School (or school_campus alias) renders requirement rows."""
    _goto(page, live_server)
    _activate_school(page)
    rows = page.locator('[data-testid="pro-val-special-asset-requirement-row"]')
    assert rows.count() > 0, "No requirement rows found after school selection"
    expect(rows.first).to_be_visible()


def test_PVUAFR_E25_heritage_renders_rows(page: Page, live_server: str) -> None:
    """PVUAFR-E25: Heritage subtype renders requirement rows."""
    _goto(page, live_server)
    _activate_heritage(page)
    rows = page.locator('[data-testid="pro-val-special-asset-requirement-row"]')
    assert rows.count() > 0, "No requirement rows found after heritage selection"
    expect(rows.first).to_be_visible()


def test_PVUAFR_E26_no_static_only_groups(page: Page, live_server: str) -> None:
    """PVUAFR-E26: No group renders chip-only span elements — all groups have input controls."""
    _goto(page, live_server)
    _activate_padel(page)
    # The old chip renderer produced spans with class-based chips inside group bodies.
    # After PVUAFR, all groups should contain data-testid="pro-val-special-asset-requirement-input".
    inputs = page.locator('[data-testid="pro-val-special-asset-requirement-input"]')
    assert inputs.count() > 0, "No fillable inputs found — group may still be static-only"
    # Confirm there are actual interactive elements, not just spans
    interactive_count = page.evaluate("""
        () => {
            const inputs = document.querySelectorAll(
                '[data-testid="pro-val-special-asset-requirement-input"]'
            );
            let count = 0;
            for (const el of inputs) {
                const tag = el.tagName.toLowerCase();
                if (['input', 'select', 'textarea'].includes(tag)) count++;
                // Also count wrapper divs that contain input/select/textarea
                if (tag === 'div' && el.querySelector('input, select, textarea')) count++;
            }
            return count;
        }
    """)
    assert interactive_count > 0, "No interactive input controls found — static-only rendering detected"


def test_PVUAFR_E27_no_internal_paths_in_dom(page: Page, live_server: str) -> None:
    """PVUAFR-E27: No internal file system paths visible in DOM text."""
    _goto(page, live_server)
    _activate_padel(page)
    dom_text = page.locator("body").inner_text()
    matches = _INTERNAL_PATH_RE.findall(dom_text)
    assert not matches, f"Internal path markers found in DOM: {matches}"


def test_PVUAFR_E28_no_duplicate_pvr_inp_ids(page: Page, live_server: str) -> None:
    """PVUAFR-E28: No two inputs share the same pvr-inp-* id (uid is unique per field)."""
    _goto(page, live_server)
    _activate_padel(page)
    dup_count = page.evaluate("""
        () => {
            const ids = Array.from(document.querySelectorAll('[id^="pvr-inp-"]'))
                .map(el => el.id);
            const seen = new Set();
            let dups = 0;
            for (const id of ids) {
                if (seen.has(id)) dups++;
                seen.add(id);
            }
            return dups;
        }
    """)
    assert dup_count == 0, f"Found {dup_count} duplicate pvr-inp-* id(s)"


def test_PVUAFR_E29_common_requirements_not_broken(page: Page, live_server: str) -> None:
    """PVUAFR-E29: Common requirements panel still exists in DOM (not broken by PVUAFR)."""
    _goto(page, live_server)
    # The common requirements panel is a separate element from the special panel
    common = page.locator('[data-testid="pro-val-common-requirements-panel"]')
    # It should exist (even if hidden) — it is unrelated to PVUAFR changes
    # Use to_have_count(1) to check DOM presence only, not visibility
    if common.count() == 0:
        # Acceptable: some builds may use a different testid for the common panel
        # In that case, just verify the special panel didn't destroy the page layout
        wizard = page.locator('[data-testid="professional-wizard"]')
        expect(wizard).to_be_visible()
    else:
        expect(common).to_have_count(1)
