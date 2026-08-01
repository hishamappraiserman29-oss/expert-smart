"""
MVI-21 → MVI-40  Mass Valuation Import UI — Playwright E2E tests.

Uses live_server (session-scoped, from conftest.py) + pytest-playwright page fixture.
Admin / non-admin state injected via add_init_script before DOMContentLoaded so
mvInitAdminGate() reads the correct session on first load.
"""
from __future__ import annotations

import json
import pytest
from playwright.sync_api import expect

# ── Auth helpers ──────────────────────────────────────────────────────────────
_ADMIN = json.dumps({"token": "mock-token", "user_id": "u1", "is_admin": True})
_USER  = json.dumps({"token": "mock-token", "user_id": "u1", "is_admin": False})

_TAB     = '[data-testid="mass-valuation-tab"]'
_PREVIEW = '[data-testid="mv-btn-preview"]'
_EXECUTE = '[data-testid="mv-btn-execute"]'
_KPIS    = '[data-testid="mv-kpis"]'
_ERROR   = '[data-testid="mv-error"]'


def _as_admin(page):
    page.add_init_script(f"localStorage.setItem('es_auth', '{_ADMIN}')")


def _as_user(page):
    page.add_init_script(f"localStorage.setItem('es_auth', '{_USER}')")


def _open_tab(page, base_url):
    page.goto(base_url)
    page.locator(_TAB).click()


# ── Admin gate (MVI-21 → MVI-23) ─────────────────────────────────────────────

def test_mv_import_21_tab_hidden_for_non_admin(page, live_server):
    _as_user(page)
    page.goto(live_server)
    expect(page.locator(_TAB)).to_have_css("display", "none")


def test_mv_import_22_tab_visible_for_admin(page, live_server):
    _as_admin(page)
    page.goto(live_server)
    expect(page.locator(_TAB)).to_be_visible()


def test_mv_import_23_admin_guard_shown_with_no_session(page, live_server):
    page.goto(live_server)
    page.evaluate("esShowTab('mass-valuation')")
    expect(page.locator("#mv-admin-guard")).to_be_visible()
    expect(page.locator("#mv-main-content")).to_have_css("display", "none")


# ── Mode selector (MVI-24 → MVI-25) ──────────────────────────────────────────

def test_mv_import_24_mode_selector_has_three_buttons(page, live_server):
    _as_admin(page)
    _open_tab(page, live_server)
    for mode in ("csv", "xlsx", "json"):
        expect(page.locator(f'[data-testid="mv-mode-{mode}"]')).to_be_visible()


def test_mv_import_25_switching_mode_hides_other_panels(page, live_server):
    _as_admin(page)
    _open_tab(page, live_server)
    page.locator('[data-testid="mv-mode-xlsx"]').click()
    expect(page.locator("#mv-panel-xlsx")).to_be_visible()
    expect(page.locator("#mv-panel-csv")).to_have_css("display", "none")
    expect(page.locator("#mv-panel-json")).to_have_css("display", "none")


# ── Preview button state (MVI-26 → MVI-27) ───────────────────────────────────

def test_mv_import_26_preview_disabled_initially(page, live_server):
    _as_admin(page)
    _open_tab(page, live_server)
    expect(page.locator(_PREVIEW)).to_be_disabled()


def test_mv_import_27_preview_enabled_after_valid_json_paste(page, live_server):
    _as_admin(page)
    _open_tab(page, live_server)
    page.locator('[data-testid="mv-mode-json"]').click()
    page.fill(
        '[data-testid="mv-json-input"]',
        '[{"property_id":"P001","price":500000,"location":"Riyadh","area_sqm":200}]',
    )
    expect(page.locator(_PREVIEW)).not_to_be_disabled()


# ── Input validation (MVI-28 → MVI-29) ───────────────────────────────────────

def test_mv_import_28_invalid_json_object_shows_error(page, live_server):
    _as_admin(page)
    _open_tab(page, live_server)
    page.locator('[data-testid="mv-mode-json"]').click()
    page.fill('[data-testid="mv-json-input"]', '{"not": "an array"}')
    expect(page.locator(_ERROR)).to_be_visible()
    expect(page.locator(_ERROR)).to_contain_text("JSON")


def test_mv_import_29_malformed_json_keeps_preview_disabled(page, live_server):
    _as_admin(page)
    _open_tab(page, live_server)
    page.locator('[data-testid="mv-mode-json"]').click()
    page.fill('[data-testid="mv-json-input"]', '{malformed!!}')
    expect(page.locator(_PREVIEW)).to_be_disabled()


# ── Pre-preview hidden state (MVI-30 → MVI-32) ───────────────────────────────

def test_mv_import_30_kpis_hidden_before_preview(page, live_server):
    _as_admin(page)
    _open_tab(page, live_server)
    expect(page.locator(_KPIS)).to_have_css("display", "none")


def test_mv_import_31_execute_button_hidden_before_preview(page, live_server):
    _as_admin(page)
    _open_tab(page, live_server)
    expect(page.locator(_EXECUTE)).to_have_css("display", "none")


def test_mv_import_32_pipeline_table_hidden_before_preview(page, live_server):
    _as_admin(page)
    _open_tab(page, live_server)
    expect(page.locator('[data-testid="mv-table-wrapper"]')).to_have_css("display", "none")


# ── Advisory / policy always visible (MVI-33 → MVI-34) ──────────────────────

def test_mv_import_33_advisory_banner_always_visible(page, live_server):
    _as_admin(page)
    _open_tab(page, live_server)
    banner = page.locator(".mv-advisory-banner")
    expect(banner).to_be_visible()
    expect(banner).to_contain_text("advisory_only")
    expect(banner).to_contain_text("certification_ready")


def test_mv_import_34_anomaly_policy_note_always_visible(page, live_server):
    _as_admin(page)
    _open_tab(page, live_server)
    note = page.locator(".mv-policy-note")
    expect(note).to_be_visible()
    expect(note).to_contain_text("for_review")


# ── Preview invalidation (MVI-35) ────────────────────────────────────────────

def test_mv_import_35_mode_change_clears_record_count_and_disables_preview(page, live_server):
    _as_admin(page)
    _open_tab(page, live_server)
    page.locator('[data-testid="mv-mode-json"]').click()
    page.fill('[data-testid="mv-json-input"]', '[{"price":1000}]')
    expect(page.locator("#mv-record-count")).to_contain_text("سجل")
    page.locator('[data-testid="mv-mode-csv"]').click()
    expect(page.locator("#mv-record-count")).to_have_text("")
    expect(page.locator(_PREVIEW)).to_be_disabled()


# ── Layout / structure (MVI-36 → MVI-40) ─────────────────────────────────────

def test_mv_import_36_page_direction_is_rtl(page, live_server):
    _as_admin(page)
    page.goto(live_server)
    assert page.locator("html").get_attribute("dir") == "rtl"


def test_mv_import_37_kpi_grid_has_three_cards(page, live_server):
    _as_admin(page)
    _open_tab(page, live_server)
    page.evaluate("document.getElementById('mv-kpis').style.display = ''")
    expect(page.locator(".mv-kpi-card")).to_have_count(3)


def test_mv_import_38_lookback_input_default_is_36(page, live_server):
    _as_admin(page)
    _open_tab(page, live_server)
    assert page.locator('[data-testid="mv-lookback"]').input_value() == "36"


def test_mv_import_39_no_console_errors_on_admin_tab_open(page, live_server):
    # Use pageerror (uncaught JS exceptions) not console "error" events so that
    # pre-existing 401 network failures from other app endpoints (which use the
    # mock token and legitimately return 401) are not counted against Phase 13.
    js_errors: list[str] = []
    page.on("pageerror", lambda e: js_errors.append(str(e)))
    _as_admin(page)
    page.goto(live_server)
    page.locator(_TAB).click()
    page.wait_for_timeout(400)
    assert not js_errors, f"Uncaught JS errors on tab open: {js_errors}"


def test_mv_import_40_run_result_hidden_before_execute(page, live_server):
    _as_admin(page)
    _open_tab(page, live_server)
    expect(page.locator('[data-testid="mv-run-result"]')).to_have_css("display", "none")


# ── Browser evidence: requests and console errors (MVI-41 → MVI-43) ──────────


def test_mv_import_41_no_mv_api_requests_on_tab_open(page, live_server):
    """Passive tab open must not trigger any request to /api/mass-valuation/import."""
    mv_requests: list[str] = []
    page.on(
        "request",
        lambda req: mv_requests.append(req.url) if "/api/mass-valuation/import" in req.url else None,
    )
    _as_admin(page)
    page.goto(live_server)
    page.locator(_TAB).click()
    page.wait_for_timeout(400)
    assert mv_requests == [], f"Unexpected MV import requests on passive tab open: {mv_requests}"


def test_mv_import_42_preview_sends_exactly_one_request_no_duplicate(page, live_server):
    """
    Clicking Preview once sends exactly 1 request to /api/mass-valuation/import.
    No duplicate requests (_mvPendingRequest guard).
    The mock token causes a 401 auth response (expected in test environment — esFetch
    catches it silently). A 401 response is NOT a requestfailed event; the request
    received a response and is counted as an expected auth failure, not a network error.
    """
    mv_requests: list[str] = []
    mv_failed: list[str] = []
    page.on(
        "request",
        lambda req: mv_requests.append(req.url) if "/api/mass-valuation/import" in req.url else None,
    )
    page.on(
        "requestfailed",
        lambda req: mv_failed.append(req.url) if "/api/mass-valuation/import" in req.url else None,
    )
    _as_admin(page)
    _open_tab(page, live_server)
    page.locator('[data-testid="mv-mode-json"]').click()
    page.fill(
        '[data-testid="mv-json-input"]',
        '[{"property_id":"P001","transaction_price":500000,"address":"Riyadh","land_area_m2":200}]',
    )
    expect(page.locator(_PREVIEW)).not_to_be_disabled()
    page.locator(_PREVIEW).click()
    page.wait_for_timeout(600)
    assert len(mv_requests) == 1, (
        f"Expected exactly 1 MV import request (got {len(mv_requests)}): {mv_requests}"
    )
    assert mv_failed == [], f"Network-level MV import failures: {mv_failed}"


def test_mv_import_43_no_phase_b_console_errors(page, live_server):
    """
    Phase B UI produces 0 code-level console.error messages during tab interactions.

    Two categories of console errors are separated:
    - network_errors: browser-generated "Failed to load resource" / "net::" messages
      from auto-fired app endpoints (pre-existing; mock token → 401)
    - code_errors: explicit console.error() calls from JavaScript code

    Phase B JS contains no console.error() calls (static fact); code_errors must be 0.
    Passive interactions only (no Preview click) so /api/mass-valuation/import is not
    requested and cannot generate errors in this test.
    """
    all_errors: list[str] = []
    page.on("console", lambda msg: all_errors.append(msg.text) if msg.type == "error" else None)
    _as_admin(page)
    _open_tab(page, live_server)
    page.locator('[data-testid="mv-mode-json"]').click()
    page.locator('[data-testid="mv-mode-xlsx"]').click()
    page.locator('[data-testid="mv-mode-csv"]').click()
    page.wait_for_timeout(400)

    network_errors = [e for e in all_errors if "Failed to load resource" in e or "net::" in e]
    code_errors    = [e for e in all_errors if e not in network_errors]
    assert not code_errors, (
        f"Phase B console.error (code-level) messages: {code_errors}\n"
        f"(Pre-existing browser network errors filtered: {len(network_errors)})"
    )
