"""
MVR-01 -> MVR-19  Mass Valuation Runs History — read-only, Wave 4C-2.

MVR-19 was added by the concurrency-correction pass: it proves the
single-flight guard in mvLoadRunsHistory() via real browser request
observation (not source inspection), after a prior review found no
in-flight protection against duplicate/out-of-order Runs requests.

Kept in its own file, separate from the closed Wave 4C-1 shell suite
(test_mv_workspace_shell.py), per the Wave 4C-2 governance decision.

Exercises the shared MV frontend foundation (API wrapper, error
normalization, loading state, context-aware errors, workspace 503 banner,
advisory helper, local labels) introduced alongside Runs History, using
Playwright request interception (page.route) to deterministically produce
401 / 403 / 404 / 503 / network-failure conditions that the real backend
does not naturally return for this endpoint, so the frontend's own
normalization logic is verified directly rather than only its happy path.

Uses the same live_server + Playwright page fixtures and localStorage-based
auth injection convention as test_mv_import_ui.py / test_mv_workspace_shell.py.
"""
from __future__ import annotations

import json

import pytest
from playwright.sync_api import expect

_ADMIN = json.dumps({"token": "mock-token", "user_id": "u1", "is_admin": True})

_TAB = '[data-testid="mass-valuation-tab"]'
_NAV_RUNS = '[data-testid="mv-nav-runs"]'
_NAV_IMPORT = '[data-testid="mv-nav-import"]'
_RUNS_LOADING = '[data-testid="mv-runs-loading"]'
_RUNS_EMPTY = '[data-testid="mv-runs-empty"]'
_RUNS_ERROR = '[data-testid="mv-runs-error"]'
_RUNS_TABLE_WRAPPER = '[data-testid="mv-runs-table-wrapper"]'
_RUNS_ADVISORY = '[data-testid="mv-runs-advisory"]'
_WORKSPACE_BANNER = '[data-testid="mv-workspace-banner"]'
_RUNS_URL = "**/api/mass-valuation/runs*"

_SAMPLE_RUNS = {
    "runs": [
        {
            "run_id": "11111111-1111-1111-1111-111111111111",
            "run_name": "Riyadh Q3 Batch",
            "status": "validated",
            "started_at": "2026-08-01T10:00:00",
            "n_input_records": 120,
            "n_predicted_properties": 118,
            "ood_property_count": 4,
            "method": "avm",
            "manual_review_required_count": 777,
        },
        {
            "run_id": "22222222-2222-2222-2222-222222222222",
            "run_name": "Jeddah Batch",
            "status": "validated",
            "started_at": "2026-07-15T09:30:00",
            "n_input_records": 60,
            "n_predicted_properties": 60,
            "ood_property_count": 0,
            "method": "avm",
            "manual_review_required_count": 3,
        },
    ],
    "count": 2,
    "advisory_only": True,
}


def _as_admin(page):
    page.add_init_script(f"localStorage.setItem('es_auth', '{_ADMIN}')")


def _open_tab(page, base_url):
    page.goto(base_url)
    page.locator(_TAB).click()


def _mock_runs(page, *, status=200, body=None, abort=False, delay_ms=0):
    def handler(route):
        if abort:
            route.abort("failed")
            return
        if delay_ms:
            page.wait_for_timeout(delay_ms)
        route.fulfill(status=status, content_type="application/json", body=json.dumps(body or {}))
    page.route(_RUNS_URL, handler)


# ── 1. Screen exists within MV workspace (MVR-01) ───────────────────────────

def test_mvr_01_runs_screen_exists_within_mv_workspace(page, live_server):
    _as_admin(page)
    _mock_runs(page, status=200, body=_SAMPLE_RUNS)
    _open_tab(page, live_server)
    page.locator(_NAV_RUNS).click()
    expect(page.locator('[data-testid="mv-screen-runs"]')).to_be_visible()
    expect(page.locator("#ws-mass-valuation")).to_be_visible()


# ── 2. No fetch merely from opening the MV workspace (MVR-02) ──────────────

def test_mvr_02_runs_not_fetched_on_workspace_open(page, live_server):
    requests = []
    page.on("request", lambda req: requests.append(req.url) if "/api/mass-valuation/runs" in req.url else None)
    _as_admin(page)
    page.goto(live_server)
    page.locator(_TAB).click()
    page.wait_for_timeout(400)
    assert requests == [], f"Unexpected runs requests on passive tab open: {requests}"


# ── 3. Navigating to Runs triggers exactly the authorized GET endpoint (MVR-03) ──

def test_mvr_03_navigating_to_runs_triggers_get_runs(page, live_server):
    requests = []
    page.on("request", lambda req: requests.append((req.method, req.url)) if "/api/mass-valuation/runs" in req.url else None)
    _as_admin(page)
    _mock_runs(page, status=200, body=_SAMPLE_RUNS)
    _open_tab(page, live_server)
    page.locator(_NAV_RUNS).click()
    page.wait_for_timeout(500)
    assert len(requests) == 1, f"Expected exactly 1 request, got: {requests}"
    method, url = requests[0]
    assert method == "GET"
    assert "/api/mass-valuation/runs" in url
    assert "/api/mass-valuation/predictions" not in url


# ── 4. Loading state shown correctly (MVR-04) ───────────────────────────────

def test_mvr_04_loading_state_shown_while_request_in_flight(page, live_server):
    _as_admin(page)
    _mock_runs(page, status=200, body=_SAMPLE_RUNS, delay_ms=800)
    _open_tab(page, live_server)
    page.locator(_NAV_RUNS).click()
    expect(page.locator(_RUNS_LOADING)).to_be_visible()
    expect(page.locator(_RUNS_LOADING)).not_to_have_text("")
    page.wait_for_timeout(1000)
    expect(page.locator(_RUNS_LOADING)).to_have_css("display", "none")


# ── 5. Successful run data renders (MVR-05) ─────────────────────────────────

def test_mvr_05_successful_run_data_renders(page, live_server):
    _as_admin(page)
    _mock_runs(page, status=200, body=_SAMPLE_RUNS)
    _open_tab(page, live_server)
    page.locator(_NAV_RUNS).click()
    expect(page.locator(_RUNS_TABLE_WRAPPER)).to_be_visible()
    rows = page.locator("#mv-runs-tbody tr")
    expect(rows).to_have_count(2)
    expect(page.locator("#mv-runs-tbody")).to_contain_text("Riyadh Q3 Batch")
    expect(page.locator("#mv-runs-tbody")).to_contain_text("Jeddah Batch")
    expect(page.locator("#mv-runs-tbody")).to_contain_text("avm")


# ── 6. Empty runs array renders explicit empty state (MVR-06) ──────────────

def test_mvr_06_empty_runs_renders_empty_state(page, live_server):
    _as_admin(page)
    _mock_runs(page, status=200, body={"runs": [], "count": 0, "advisory_only": True})
    _open_tab(page, live_server)
    page.locator(_NAV_RUNS).click()
    expect(page.locator(_RUNS_EMPTY)).to_be_visible()
    expect(page.locator(_RUNS_TABLE_WRAPPER)).to_have_css("display", "none")


# ── 7. 401 normalized safely (MVR-07) ───────────────────────────────────────

def test_mvr_07_401_normalized_safely(page, live_server):
    _as_admin(page)
    _mock_runs(page, status=401, body={"error": "invalid or expired token"})
    _open_tab(page, live_server)
    page.locator(_NAV_RUNS).click()
    page.wait_for_timeout(400)
    # Positive: the normalized message (read from the app's own mvLabel(),
    # not duplicated as literal text in this test) actually renders in the
    # screen's error region.
    error_el = page.locator(_RUNS_ERROR)
    expect(error_el).to_be_visible()
    expected_message = page.evaluate("mvLabel('err_401')")
    expect(error_el).to_have_text(expected_message)
    # Negative: esFetch's 401 path never lets mvLoadRunsHistory render the
    # raw backend exception string anywhere on the page.
    body_text = page.locator("body").inner_text()
    assert "invalid or expired token" not in body_text


# ── 8. 403 normalized safely (MVR-08) ───────────────────────────────────────

def test_mvr_08_403_normalized_safely(page, live_server):
    _as_admin(page)
    _mock_runs(page, status=403, body={"error": "admin role required"})
    _open_tab(page, live_server)
    page.locator(_NAV_RUNS).click()
    page.wait_for_timeout(400)
    error_el = page.locator(_RUNS_ERROR)
    expect(error_el).to_be_visible()
    expected_message = page.evaluate("mvLabel('err_403')")
    expect(error_el).to_have_text(expected_message)
    body_text = page.locator("body").inner_text()
    assert "admin role required" not in body_text


# ── 9. 404 normalization is non-disclosing (MVR-09) ─────────────────────────

def test_mvr_09_404_normalization_is_non_disclosing(page, live_server):
    _as_admin(page)
    _mock_runs(page, status=404, body={"error": "run not found", "run_id": "zz"})
    _open_tab(page, live_server)
    page.locator(_NAV_RUNS).click()
    page.wait_for_timeout(400)
    error_el = page.locator(_RUNS_ERROR)
    expect(error_el).to_be_visible()
    text = error_el.inner_text()
    assert "run not found" not in text
    assert "zz" not in text
    # Must not claim/imply a specific reason (exists-for-someone-else vs never-existed).
    assert "another" not in text and "different" not in text and "belongs" not in text


# ── 10. 503 produces workspace/service-unavailable disclosure (MVR-10) ─────

def test_mvr_10_503_produces_workspace_banner(page, live_server):
    _as_admin(page)
    _mock_runs(page, status=503, body={"error": "database temporarily unavailable"})
    _open_tab(page, live_server)
    page.locator(_NAV_RUNS).click()
    page.wait_for_timeout(400)
    banner = page.locator(_WORKSPACE_BANNER)
    expect(banner).to_be_visible()
    text = banner.inner_text()
    assert "database temporarily unavailable" not in text
    # Must not misreport a 503 as an authorization failure.
    assert "admin" not in text and "صلاحيات" not in text
    expect(page.locator(_RUNS_ERROR)).to_have_css("display", "none")


# ── 11. Network failure safely normalized (MVR-11) ──────────────────────────

def test_mvr_11_network_failure_normalized(page, live_server):
    _as_admin(page)
    _mock_runs(page, abort=True)
    _open_tab(page, live_server)
    page.locator(_NAV_RUNS).click()
    page.wait_for_timeout(600)
    expect(page.locator(_RUNS_ERROR)).to_be_visible()
    expect(page.locator(_RUNS_LOADING)).to_have_css("display", "none")


# ── 12. Advisory-only disclosure visible on Runs screen (MVR-12) ───────────

def test_mvr_12_advisory_disclosure_visible_on_runs_screen(page, live_server):
    _as_admin(page)
    _mock_runs(page, status=200, body=_SAMPLE_RUNS)
    _open_tab(page, live_server)
    page.locator(_NAV_RUNS).click()
    advisory = page.locator(_RUNS_ADVISORY)
    expect(advisory).to_be_visible()
    expect(advisory).to_contain_text("advisory_only")
    expect(advisory).to_contain_text("certification_ready")


# ── 13. No fabricated "Pending Reviews" from manual_review_required_count (MVR-13) ──

def test_mvr_13_no_fabricated_pending_reviews_count(page, live_server):
    _as_admin(page)
    _mock_runs(page, status=200, body=_SAMPLE_RUNS)
    _open_tab(page, live_server)
    page.locator(_NAV_RUNS).click()
    expect(page.locator(_RUNS_TABLE_WRAPPER)).to_be_visible()
    table_text = page.locator("#mv-runs-table").inner_text()
    assert "777" not in table_text, "manual_review_required_count value leaked into rendered table"
    assert "Pending Review" not in table_text
    assert "قيد المراجعة" not in table_text
    assert "للمراجعة" not in table_text


# ── 14/15/16. No predictions / review / export endpoint called (MVR-14,15,16) ──

def test_mvr_14_15_16_no_predictions_review_export_calls(page, live_server):
    other_requests = []
    page.on(
        "request",
        lambda req: other_requests.append(req.url) if (
            "/api/mass-valuation/predictions" in req.url
            or "/api/mass-valuation/review" in req.url
            or "/export" in req.url
        ) else None,
    )
    _as_admin(page)
    _mock_runs(page, status=200, body=_SAMPLE_RUNS)
    _open_tab(page, live_server)
    page.locator(_NAV_RUNS).click()
    page.wait_for_timeout(500)
    assert other_requests == [], f"Unexpected predictions/review/export requests: {other_requests}"


# ── 17. Mass Appraisal navigation remains exact (MVR-17) ────────────────────

def test_mvr_17_mass_appraisal_navigation_unchanged(page, live_server):
    _as_admin(page)
    _open_tab(page, live_server)
    page.locator('[data-testid="mv-suite-product-mass-appraisal"]').click()
    expect(page.locator("#ws-composite")).to_have_class("es-workspace es-ws-active")
    expect(page.locator("#mass-appraisal-workflow")).to_be_visible()


# ── 18. Import behavior unaffected by Runs History interactions (MVR-18) ───

def test_mvr_18_import_behavior_unaffected(page, live_server):
    _as_admin(page)
    _mock_runs(page, status=200, body=_SAMPLE_RUNS)
    _open_tab(page, live_server)
    page.locator(_NAV_RUNS).click()
    page.wait_for_timeout(300)
    page.locator(_NAV_IMPORT).click()
    expect(page.locator('[data-testid="mv-screen-import"]')).to_be_visible()
    expect(page.locator('[data-testid="mv-mode-csv"]')).to_be_visible()
    expect(page.locator('[data-testid="mv-btn-preview"]')).to_be_disabled()
    page.locator('[data-testid="mv-mode-json"]').click()
    page.fill(
        '[data-testid="mv-json-input"]',
        '[{"property_id":"P001","price":500000,"location":"Riyadh","area_sqm":200}]',
    )
    expect(page.locator('[data-testid="mv-btn-preview"]')).not_to_be_disabled()


# ── 19. Single-flight: no duplicate GET while a Runs request is in flight (MVR-19) ──
# Correction: mvLoadRunsHistory() previously had no in-flight guard, so a
# second explicit Runs navigation while the first request was still pending
# could start a second GET and let an out-of-order response overwrite the
# table with stale data. This test proves exactly one GET is observed by the
# real browser (not just source inspection) while the first request remains
# unresolved, and that a later navigation — after the first has settled —
# is still free to issue a fresh GET.

def test_mvr_19_no_duplicate_runs_request_while_first_in_flight(page, live_server):
    request_log: list[str] = []
    page.on(
        "request",
        lambda req: request_log.append(req.url)
        if req.method == "GET" and "/api/mass-valuation/runs" in req.url
        else None,
    )

    call_count = {"n": 0}

    def handler(route):
        call_count["n"] += 1
        if call_count["n"] == 1:
            # Hold the first request open long enough to attempt a second
            # explicit Runs navigation while it is still unresolved.
            page.wait_for_timeout(1200)
        route.fulfill(status=200, content_type="application/json", body=json.dumps(_SAMPLE_RUNS))

    page.route(_RUNS_URL, handler)

    _as_admin(page)
    _open_tab(page, live_server)

    page.locator(_NAV_RUNS).click()  # starts request #1 (held ~1200ms by the handler)
    expect(page.locator(_RUNS_LOADING)).to_be_visible()

    # Explicit re-navigation to Runs while request #1 is still in flight —
    # the single-flight guard must make this a no-op (no second GET).
    page.locator(_NAV_RUNS).click()

    # Checked well before the 1200ms delay elapses, so request #1 is
    # provably still unresolved at this point.
    page.wait_for_timeout(300)
    assert len(request_log) == 1, f"Expected exactly 1 in-flight GET, observed: {request_log}"

    # Let request #1 resolve; the screen must settle normally.
    expect(page.locator(_RUNS_TABLE_WRAPPER)).to_be_visible()
    expect(page.locator(_RUNS_LOADING)).to_have_css("display", "none")
    assert len(request_log) == 1, f"A second GET must never have started: {request_log}"

    # After the first request has settled, a fresh explicit Runs navigation
    # is authorized to issue a new GET.
    page.locator(_NAV_RUNS).click()
    page.wait_for_timeout(400)
    assert len(request_log) == 2, f"A post-settle navigation should issue a new GET: {request_log}"
