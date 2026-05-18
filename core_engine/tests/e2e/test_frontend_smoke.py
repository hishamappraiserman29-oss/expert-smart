"""
Frontend smoke tests — verify the UI loads and core elements are present.

These tests require a running bridge_api server (managed by conftest.py)
and a Playwright browser (chromium).  Run with:

    pytest core_engine/tests/e2e/ -v

or, to skip if the server can't start:

    pytest core_engine/tests/e2e/ -v --ignore-glob="*e2e*"
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base(live_server: str) -> str:
    return live_server


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_page_loads_without_console_errors(page: Page, live_server: str) -> None:
    """Home page loads and emits no JS console errors."""
    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

    page.goto(live_server, wait_until="networkidle")

    # SEC-002 auth hardening makes protected API calls (e.g. /api/radar/start)
    # return 401 for anonymous page load; the browser logs these as resource-load
    # errors. This is expected until a login flow is wired into E2E.
    # TypeError, ReferenceError, SyntaxError, 5xx errors, failed JS/CSS assets,
    # and uncaught exceptions are NOT filtered and will still fail this test.
    real_errors = [
        e for e in errors
        if not ("Failed to load resource" in e and "401" in e)
    ]
    assert real_errors == [], f"Console errors detected on page load: {real_errors}"


def test_reports_panel_visible(page: Page, live_server: str) -> None:
    """Reports panel, filter selects, and refresh button are present in the DOM."""
    page.goto(live_server, wait_until="networkidle")

    # Reports panel wrapper
    expect(page.locator("#es-reports-panel")).to_be_visible()

    # Profile and status filter dropdowns
    expect(page.locator("#es-reports-filter-profile")).to_be_visible()
    expect(page.locator("#es-reports-filter-status")).to_be_visible()

    # Refresh button (Arabic label: تحديث السجل)
    refresh_btn = page.locator("button", has_text="تحديث السجل")
    expect(refresh_btn).to_be_visible()


def test_refresh_renders_table_or_empty_state(page: Page, live_server: str) -> None:
    """
    Clicking the refresh button results in either:
    - the table wrapper becoming visible (≥1 saved reports exist), or
    - the empty-state div being non-empty (zero reports, shows a message).

    Both outcomes are valid; the test only verifies the UI reacts to the click.
    """
    page.goto(live_server, wait_until="networkidle")

    refresh_btn = page.locator("button", has_text="تحديث السجل")
    refresh_btn.click()

    # Give the async fetch up to 8 s to resolve
    table_wrap = page.locator("#es-reports-table-wrap")
    state_div = page.locator("#es-reports-state")

    def _one_is_active() -> bool:
        table_visible = table_wrap.is_visible()
        state_text = state_div.inner_text().strip()
        return table_visible or bool(state_text)

    page.wait_for_function(
        """() => {
            const tw = document.getElementById('es-reports-table-wrap');
            const sd = document.getElementById('es-reports-state');
            return (tw && tw.style.display !== 'none') ||
                   (sd && sd.innerText.trim().length > 0);
        }""",
        timeout=8_000,
    )

    table_visible = table_wrap.is_visible()
    state_text = state_div.inner_text().strip()
    assert table_visible or state_text, (
        "After clicking refresh, neither the table nor the empty-state div became active."
    )


def test_existing_features_still_work(page: Page, live_server: str) -> None:
    """Generate button is present and enabled — core valuation entry point intact."""
    page.goto(live_server, wait_until="networkidle")

    generate_btn = page.locator("#generateBtn")
    expect(generate_btn).to_be_visible()
    # The button must not be hard-disabled (it may be visually styled but should
    # be interactable; we only check it is present and not disabled).
    assert not generate_btn.is_disabled(), "#generateBtn should not be disabled on load"
