# -*- coding: utf-8 -*-
"""
test_tax_appeal_structured_parser_backoffice.py — E2E tests for Tax Appeal
Structured Parser Pilot UI.

Tests:
  TSP01 — Ordinary tax page does not show structured parser section
  TSP02 — Structured parser section element exists in DOM
  TSP03 — Advisory section wrapper exists
  TSP04 — Structured parser warning badge exists
  TSP05 — Structured parser evidence select exists with 3 options
  TSP06 — Run structured parser button exists
  TSP07 — Structured parser status element exists
  TSP08 — Structured parser columns display element exists
  TSP09 — Structured parser summary display element exists
  TSP10 — Create extraction draft button exists
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page


# ── Helpers ───────────────────────────────────────────────────────────────────

def _block_api(page: Page) -> None:
    page.route("**/api/**", lambda r: r.fulfill(
        status=200,
        body=b'{"ok":true,"requests":[],"ocr_jobs":[],"parse_jobs":[]}',
        content_type="application/json",
    ))


def _go(page: Page, live_server: str) -> None:
    _block_api(page)
    page.goto(live_server, wait_until="domcontentloaded")


# ── TSP01 — Ordinary tax page does not show structured parser section ──────────
def test_TSP01_ordinary_page_no_sp_section(page: Page, live_server: str) -> None:
    """Structured parser section must not be visible on the ordinary tax page."""
    _go(page, live_server)
    sp_section = page.locator("[data-testid='tax-structured-parser-section']")
    if sp_section.count() > 0:
        assert not sp_section.is_visible(), \
            "Structured parser section must not be visible on ordinary page"


# ── TSP02 — Structured parser section element exists in DOM ───────────────────
def test_TSP02_sp_section_element_exists(page: Page, live_server: str) -> None:
    _go(page, live_server)
    assert page.locator("[data-testid='tax-structured-parser-section']").count() > 0, \
        "tax-structured-parser-section not found in DOM"


# ── TSP03 — Advisory section wrapper exists ───────────────────────────────────
def test_TSP03_advisory_section_wrapper_exists(page: Page, live_server: str) -> None:
    _go(page, live_server)
    assert page.locator("[data-testid='tax-advisory-section']").count() > 0, \
        "tax-advisory-section not found in DOM"


# ── TSP04 — Structured parser warning badge exists ────────────────────────────
def test_TSP04_sp_warning_badge_exists(page: Page, live_server: str) -> None:
    _go(page, live_server)
    warning = page.locator("[data-testid='tax-structured-parser-warning']")
    assert warning.count() > 0, "tax-structured-parser-warning not found in DOM"


# ── TSP05 — Structured parser evidence select exists with 3 options ───────────
def test_TSP05_sp_evidence_select_exists_with_options(page: Page, live_server: str) -> None:
    _go(page, live_server)
    sel = page.locator("[data-testid='tax-structured-parser-evidence-select']")
    assert sel.count() > 0, "tax-structured-parser-evidence-select not found in DOM"
    # Should have at least 3 options (market, rental, tax)
    options = sel.locator("option")
    assert options.count() >= 3, \
        f"Expected >= 3 options in evidence select, got {options.count()}"


# ── TSP06 — Run structured parser button exists ───────────────────────────────
def test_TSP06_sp_run_button_exists(page: Page, live_server: str) -> None:
    _go(page, live_server)
    btn = page.locator("[data-testid='tax-structured-parser-run-button']")
    assert btn.count() > 0, "tax-structured-parser-run-button not found in DOM"


# ── TSP07 — Structured parser status element exists ───────────────────────────
def test_TSP07_sp_status_element_exists(page: Page, live_server: str) -> None:
    _go(page, live_server)
    status = page.locator("[data-testid='tax-structured-parser-status']")
    assert status.count() > 0, "tax-structured-parser-status not found in DOM"


# ── TSP08 — Structured parser columns display element exists ──────────────────
def test_TSP08_sp_columns_element_exists(page: Page, live_server: str) -> None:
    _go(page, live_server)
    cols = page.locator("[data-testid='tax-structured-parser-columns']")
    assert cols.count() > 0, "tax-structured-parser-columns not found in DOM"


# ── TSP09 — Structured parser summary display element exists ──────────────────
def test_TSP09_sp_summary_element_exists(page: Page, live_server: str) -> None:
    _go(page, live_server)
    summ = page.locator("[data-testid='tax-structured-parser-summary']")
    assert summ.count() > 0, "tax-structured-parser-summary not found in DOM"


# ── TSP10 — Create extraction draft button exists ─────────────────────────────
def test_TSP10_sp_create_draft_button_exists(page: Page, live_server: str) -> None:
    _go(page, live_server)
    btn = page.locator("[data-testid='tax-structured-parser-create-extraction-draft']")
    assert btn.count() > 0, "tax-structured-parser-create-extraction-draft not found in DOM"
