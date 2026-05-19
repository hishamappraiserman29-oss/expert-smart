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


# /api/radar/start and /api/price-index intentionally use plain fetch (not
# esFetch) so they fire anonymously on page load without triggering the login
# modal — see docs/AUTH_FLOW.md §5.  They return 401 for anonymous requests
# and the browser logs a resource-load console error for each.
_EXPECTED_BG_AUTH_PATHS = ("/api/radar/start", "/api/price-index")


def _is_expected_bg_401(err_text: str) -> bool:
    """True for the browser-level 401 console errors from the two background auto-calls.

    Strategy:
    - If Playwright embeds the request URL in msg.text we match by path (surgical).
    - If the URL is absent in msg.text we fall back to suppressing all
      'Failed to load resource' + '401' errors (preserves stability across
      Playwright/Chromium versions that omit the URL from the message string).
    """
    if "Failed to load resource" not in err_text or "401" not in err_text:
        return False
    if any(path in err_text for path in _EXPECTED_BG_AUTH_PATHS):
        return True  # surgical: URL present, matches known background path
    # Fallback: URL absent — suppress if no other /api/ path info in the text
    has_other_api_path = any(seg in err_text for seg in ("/api/", "http://", "https://"))
    return not has_other_api_path


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------

def test_page_loads_without_console_errors(page: Page, live_server: str) -> None:
    """Home page loads and emits no unexpected JS console errors.

    Expected 401s from /api/radar/start and /api/price-index are filtered
    (background auto-calls that intentionally bypass esFetch).
    TypeError, ReferenceError, SyntaxError, 5xx errors, failed JS/CSS assets,
    and uncaught exceptions are NOT filtered and will fail this test.
    """
    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

    page.goto(live_server, wait_until="networkidle")

    real_errors = [e for e in errors if not _is_expected_bg_401(e)]
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
    - the empty-state div being non-empty (zero reports, or auth-guard message).

    Both outcomes are valid; the test only verifies the UI reacts to the click.
    Without a stored JWT session, esFetch intercepts the 401 and the state div
    shows an Arabic error message — the expected auth-guard behaviour.
    """
    page.goto(live_server, wait_until="networkidle")

    refresh_btn = page.locator("button", has_text="تحديث السجل")
    refresh_btn.click()

    # Give the async fetch up to 8 s to resolve
    table_wrap = page.locator("#es-reports-table-wrap")
    state_div = page.locator("#es-reports-state")

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


# ---------------------------------------------------------------------------
# Auth #7b — Frontend login modal + esFetch wrapper
# ---------------------------------------------------------------------------

class TestAuthUI:
    """Frontend auth #7b — login modal, localStorage session, logged-in bar, esFetch.

    Most tests inject a mock session directly into localStorage via page.evaluate
    rather than performing a real token exchange.  This isolates UI behaviour from
    server-side token validation (covered by test_bridge_api_login.py AV01-AV10).
    """

    def test_login_modal_present_in_dom(self, page: Page, live_server: str) -> None:
        """Login modal is in the DOM and hidden by default when no session exists."""
        page.goto(live_server, wait_until="networkidle")
        page.evaluate("localStorage.removeItem('es_auth')")
        page.reload(wait_until="networkidle")
        modal = page.locator("#es-login-modal")
        expect(modal).to_be_attached()
        assert not modal.is_visible(), "Login modal should be hidden on load with no session"

    def test_login_modal_contains_token_input_and_submit(
        self, page: Page, live_server: str
    ) -> None:
        """Login modal contains the token textarea and a submit button."""
        page.goto(live_server, wait_until="networkidle")
        assert page.locator("#es-token-input").count() == 1, "#es-token-input must exist"
        assert page.locator("#es-login-submit").count() == 1, "#es-login-submit must exist"

    def test_logged_in_bar_hidden_without_session(
        self, page: Page, live_server: str
    ) -> None:
        """Logged-in bar is hidden when no es_auth entry exists in localStorage."""
        page.goto(live_server, wait_until="networkidle")
        page.evaluate("localStorage.removeItem('es_auth')")
        page.reload(wait_until="networkidle")
        bar = page.locator("#es-logged-in-bar")
        expect(bar).to_be_attached()
        assert not bar.is_visible(), "Logged-in bar should be hidden with no session"

    def test_logged_in_bar_visible_with_session(
        self, page: Page, live_server: str
    ) -> None:
        """Logged-in bar appears and shows user_id when a session is pre-loaded."""
        page.goto(live_server, wait_until="networkidle")
        page.evaluate(
            "localStorage.setItem('es_auth', JSON.stringify("
            "{token:'mock.jwt.token', user_id:'test-user', is_admin:false}))"
        )
        page.reload(wait_until="networkidle")
        bar = page.locator("#es-logged-in-bar")
        expect(bar).to_be_visible()
        label_text = page.locator("#es-logged-in-label").inner_text()
        assert "test-user" in label_text, f"user_id not in bar label: {label_text!r}"

    def test_admin_badge_shown_for_admin_session(
        self, page: Page, live_server: str
    ) -> None:
        """Admin badge [مسؤول] appears when is_admin=true in the stored session."""
        page.goto(live_server, wait_until="networkidle")
        page.evaluate(
            "localStorage.setItem('es_auth', JSON.stringify("
            "{token:'mock.admin.token', user_id:'admin-alice', is_admin:true}))"
        )
        page.reload(wait_until="networkidle")
        label_text = page.locator("#es-logged-in-label").inner_text()
        assert "admin-alice" in label_text
        assert "مسؤول" in label_text, f"Admin badge not shown: {label_text!r}"

    def test_logout_clears_session_and_hides_bar(
        self, page: Page, live_server: str
    ) -> None:
        """Clicking logout clears localStorage and hides the logged-in bar."""
        page.goto(live_server, wait_until="networkidle")
        page.evaluate(
            "localStorage.setItem('es_auth', JSON.stringify("
            "{token:'mock.jwt.token', user_id:'test-user', is_admin:false}))"
        )
        page.reload(wait_until="networkidle")
        logout_btn = page.locator("#es-logout-btn")
        expect(logout_btn).to_be_visible()
        logout_btn.click()
        expect(page.locator("#es-logged-in-bar")).not_to_be_visible()
        stored = page.evaluate("localStorage.getItem('es_auth')")
        assert stored is None, "es_auth should be removed from localStorage after logout"

    def test_esfetch_attaches_authorization_header(
        self, page: Page, live_server: str
    ) -> None:
        """esFetch attaches Authorization: Bearer <token> to protected /api/reports calls."""
        captured: dict[str, str] = {}

        def _intercept(route):
            captured["authorization"] = route.request.headers.get("authorization", "")
            route.abort()  # abort after capturing header — we don't need the response

        page.route("**/api/reports*", _intercept)
        page.goto(live_server, wait_until="networkidle")
        page.evaluate(
            "localStorage.setItem('es_auth', JSON.stringify("
            "{token:'sentinel-bearer-token', user_id:'u1', is_admin:false}))"
        )

        refresh_btn = page.locator("button", has_text="تحديث السجل")
        refresh_btn.click()
        page.wait_for_timeout(2_000)  # allow the intercepted fetch to fire

        assert "authorization" in captured, (
            "esFetch did not send any /api/reports request — route was never triggered"
        )
        assert captured["authorization"] == "Bearer sentinel-bearer-token", (
            f"Unexpected Authorization header value: {captured['authorization']!r}"
        )
