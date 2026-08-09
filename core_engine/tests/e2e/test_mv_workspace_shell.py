"""
MVW-01 -> MVW-14  Mass Valuation workspace shell — product/suite navigation
and Dashboard / New Run / Runs History / Run Detail sub-navigation.

Wave 4C-1: frontend-only structural unit. Adds a product/suite header (Mass
Valuation vs. Mass Appraisal) and a Mass Valuation sub-navigation bar on top
of the existing, functionally-unchanged Phase 13 import UI (see
test_mv_import_ui.py, which continues to pass unmodified against the same
markup, now re-housed inside #mv-screen-import).

Uses the same live_server + Playwright page fixtures and localStorage-based
auth injection convention as test_mv_import_ui.py.
"""
from __future__ import annotations

import json

import pytest
from playwright.sync_api import expect

_ADMIN = json.dumps({"token": "mock-token", "user_id": "u1", "is_admin": True})
_USER = json.dumps({"token": "mock-token", "user_id": "u1", "is_admin": False})

_TAB = '[data-testid="mass-valuation-tab"]'
_SUITE_HEADER = '[data-testid="mv-suite-header"]'
_PRODUCT_MV = '[data-testid="mv-suite-product-mass-valuation"]'
_PRODUCT_MA = '[data-testid="mv-suite-product-mass-appraisal"]'
_SUBNAV = '[data-testid="mv-subnav"]'
_NAV_DASHBOARD = '[data-testid="mv-nav-dashboard"]'
_NAV_IMPORT = '[data-testid="mv-nav-import"]'
_NAV_RUNS = '[data-testid="mv-nav-runs"]'
_NAV_DETAIL = '[data-testid="mv-nav-detail"]'
_SCREEN_DASHBOARD = '[data-testid="mv-screen-dashboard"]'
_SCREEN_IMPORT = '[data-testid="mv-screen-import"]'
_SCREEN_RUNS = '[data-testid="mv-screen-runs"]'
_SCREEN_DETAIL = '[data-testid="mv-screen-detail"]'


def _as_admin(page):
    page.add_init_script(f"localStorage.setItem('es_auth', '{_ADMIN}')")


def _as_user(page):
    page.add_init_script(f"localStorage.setItem('es_auth', '{_USER}')")


def _open_tab(page, base_url):
    page.goto(base_url)
    page.locator(_TAB).click()


# ── Existing tab/testid unaffected (MVW-01) ─────────────────────────────────

def test_mv_workspace_01_existing_tab_testid_still_works(page, live_server):
    _as_admin(page)
    _open_tab(page, live_server)
    expect(page.locator("#ws-mass-valuation")).to_be_visible()


# ── Admin sees new shell (MVW-02 -> MVW-04) ─────────────────────────────────

def test_mv_workspace_02_admin_sees_suite_header_and_subnav(page, live_server):
    _as_admin(page)
    _open_tab(page, live_server)
    expect(page.locator(_SUITE_HEADER)).to_be_visible()
    expect(page.locator(_SUBNAV)).to_be_visible()


def test_mv_workspace_03_admin_sees_both_product_entries(page, live_server):
    _as_admin(page)
    _open_tab(page, live_server)
    expect(page.locator(_PRODUCT_MV)).to_be_visible()
    expect(page.locator(_PRODUCT_MA)).to_be_visible()
    expect(page.locator(_PRODUCT_MV)).to_contain_text("التقييم الجماعي")
    expect(page.locator(_PRODUCT_MA)).to_contain_text("التثمين الجماعي")


def test_mv_workspace_04_mv_subnav_has_four_entries(page, live_server):
    _as_admin(page)
    _open_tab(page, live_server)
    expect(page.locator(_NAV_DASHBOARD)).to_be_visible()
    expect(page.locator(_NAV_IMPORT)).to_be_visible()
    expect(page.locator(_NAV_RUNS)).to_be_visible()
    # Run Detail is dynamic/contextual — hidden until a run is selected (not in 4C-1 scope).
    expect(page.locator(_NAV_DETAIL)).to_have_css("display", "none")


# ── Mass Appraisal navigation — exact two-call sequence (MVW-05) ───────────

def test_mv_workspace_05_mass_appraisal_entry_navigates_via_composite_mass_mode(page, live_server):
    _as_admin(page)
    _open_tab(page, live_server)
    page.locator(_PRODUCT_MA).click()
    expect(page.locator("#ws-composite")).to_have_class("es-workspace es-ws-active")
    expect(page.locator("#mass-appraisal-workflow")).to_be_visible()


# ── Non-admin: existing locked experience, no functional sub-nav (MVW-06) ──

def test_mv_workspace_06_non_admin_still_gets_locked_guard_no_subnav_interaction(page, live_server):
    _as_user(page)
    page.goto(live_server)
    page.evaluate("esShowTab('mass-valuation')")
    expect(page.locator("#mv-admin-guard")).to_be_visible()
    expect(page.locator("#mv-main-content")).to_have_css("display", "none")
    # The sub-nav lives inside #mv-main-content, so it is not interactable for non-admins.
    expect(page.locator(_SUBNAV)).not_to_be_visible()


# ── Navigation switches between the 4 screens (MVW-07 -> MVW-10) ───────────

def test_mv_workspace_07_import_is_the_default_active_screen(page, live_server):
    _as_admin(page)
    _open_tab(page, live_server)
    expect(page.locator(_SCREEN_IMPORT)).to_be_visible()
    expect(page.locator(_SCREEN_DASHBOARD)).to_have_css("display", "none")
    expect(page.locator(_SCREEN_RUNS)).to_have_css("display", "none")


def test_mv_workspace_08_dashboard_nav_shows_dashboard_and_hides_import(page, live_server):
    _as_admin(page)
    _open_tab(page, live_server)
    page.locator(_NAV_DASHBOARD).click()
    expect(page.locator(_SCREEN_DASHBOARD)).to_be_visible()
    expect(page.locator(_SCREEN_IMPORT)).to_have_css("display", "none")


def test_mv_workspace_09_runs_nav_shows_runs_and_hides_dashboard(page, live_server):
    _as_admin(page)
    _open_tab(page, live_server)
    page.locator(_NAV_DASHBOARD).click()
    page.locator(_NAV_RUNS).click()
    expect(page.locator(_SCREEN_RUNS)).to_be_visible()
    expect(page.locator(_SCREEN_DASHBOARD)).to_have_css("display", "none")


def test_mv_workspace_10_nav_back_to_import_restores_existing_import_ui(page, live_server):
    _as_admin(page)
    _open_tab(page, live_server)
    page.locator(_NAV_RUNS).click()
    page.locator(_NAV_IMPORT).click()
    expect(page.locator(_SCREEN_IMPORT)).to_be_visible()
    expect(page.locator('[data-testid="mv-mode-csv"]')).to_be_visible()
    expect(page.locator('[data-testid="mv-btn-preview"]')).to_be_visible()


# ── Existing import remains structurally reachable, unchanged (MVW-11) ─────

def test_mv_workspace_11_existing_import_controls_reachable_without_extra_nav(page, live_server):
    _as_admin(page)
    _open_tab(page, live_server)
    expect(page.locator('[data-testid="mv-mode-csv"]')).to_be_visible()
    expect(page.locator('[data-testid="mv-mode-xlsx"]')).to_be_visible()
    expect(page.locator('[data-testid="mv-mode-json"]')).to_be_visible()
    expect(page.locator('[data-testid="mv-lookback"]')).to_be_visible()


# ── No MV API calls from passive, non-Runs shell navigation (MVW-12) ───────
# Wave 4C-2 note: navigating explicitly to Runs is now authorized to trigger
# GET /api/mass-valuation/runs (see test_mv_runs_history.py for that
# contract). This test's invariant is narrowed accordingly: switching among
# the still-passive shell screens (Dashboard, Import) must not fetch MV
# data. It deliberately does NOT navigate to Runs, so it stays a pure shell
# test and does not duplicate the Runs History contract.

def test_mv_workspace_12_passive_non_runs_shell_navigation_does_not_fetch_mv_data(page, live_server):
    mv_requests: list[str] = []
    page.on(
        "request",
        lambda req: mv_requests.append(req.url) if "/api/mass-valuation/" in req.url else None,
    )
    _as_admin(page)
    _open_tab(page, live_server)
    page.locator(_NAV_DASHBOARD).click()
    page.locator(_NAV_IMPORT).click()
    page.wait_for_timeout(400)
    assert mv_requests == [], f"Unexpected MV API requests from passive non-Runs navigation: {mv_requests}"


# ── No console errors from the new shell (MVW-13) ───────────────────────────

def test_mv_workspace_13_no_console_errors_from_shell_navigation(page, live_server):
    js_errors: list[str] = []
    page.on("pageerror", lambda e: js_errors.append(str(e)))
    _as_admin(page)
    _open_tab(page, live_server)
    page.locator(_NAV_DASHBOARD).click()
    page.locator(_NAV_RUNS).click()
    page.locator(_NAV_IMPORT).click()
    page.wait_for_timeout(400)
    assert not js_errors, f"Uncaught JS errors during shell navigation: {js_errors}"


# ── Unknown screen names are ignored (defensive, MVW-14) ───────────────────

def test_mv_workspace_14_unknown_screen_name_is_a_no_op(page, live_server):
    _as_admin(page)
    _open_tab(page, live_server)
    page.evaluate("mvNavigate('does-not-exist')")
    # Import must remain the active screen — an unrecognized name must not blank the workspace.
    expect(page.locator(_SCREEN_IMPORT)).to_be_visible()
