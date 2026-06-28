# -*- coding: utf-8 -*-
"""
test_tax_appeal_ocr_backoffice.py — E2E tests for Tax Appeal OCR Pilot UI.

Tests:
  TAO01 — Ordinary tax page does not show OCR section
  TAO02 — OCR section element exists in DOM
  TAO03 — OCR evidence select exists
  TAO04 — Run OCR button exists
  TAO05 — OCR no-production warning exists
  TAO06 — OCR warning badge exists
  TAO07 — OCR text preview area exists
  TAO08 — OCR candidate list exists
  TAO09 — Create extraction draft button exists
  TAO10 — Reject OCR button exists
  TAO11 — OCR status badge exists
  TAO12 — No raw internal paths in DOM
  TAO13 — Qdrant/RAG shown inactive in OCR warning
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page


# ── Helpers ───────────────────────────────────────────────────────────────────

def _block_api(page: Page) -> None:
    page.route("**/api/**", lambda r: r.fulfill(
        status=200, body=b'{"ok":true,"requests":[],"ocr_jobs":[]}',
        content_type="application/json",
    ))


def _go(page: Page, live_server: str) -> None:
    _block_api(page)
    page.goto(live_server, wait_until="domcontentloaded")


# ── TAO01 — Ordinary tax page does not show OCR section ───────────────────────
def test_TAO01_ordinary_page_no_ocr_section(page: Page, live_server: str) -> None:
    """OCR section must not be visible on the ordinary tax page."""
    _go(page, live_server)
    ocr_section = page.locator("#tax-ocr-section")
    # Either absent or hidden
    if ocr_section.count() > 0:
        assert not ocr_section.is_visible(), "OCR section must not be visible on ordinary page"


# ── TAO02 — OCR section element exists in DOM ─────────────────────────────────
def test_TAO02_ocr_section_element_exists(page: Page, live_server: str) -> None:
    _go(page, live_server)
    assert page.locator("#tax-ocr-section").count() > 0, "#tax-ocr-section not found in DOM"


# ── TAO03 — OCR evidence select exists ───────────────────────────────────────
def test_TAO03_ocr_evidence_select_exists(page: Page, live_server: str) -> None:
    _go(page, live_server)
    sel = page.locator("[data-testid='tax-ocr-evidence-select']")
    assert sel.count() > 0, "tax-ocr-evidence-select not found in DOM"


# ── TAO04 — Run OCR button exists ─────────────────────────────────────────────
def test_TAO04_ocr_run_button_exists(page: Page, live_server: str) -> None:
    _go(page, live_server)
    btn = page.locator("[data-testid='tax-ocr-run-button']")
    assert btn.count() > 0, "tax-ocr-run-button not found in DOM"


# ── TAO05 — OCR no-production warning exists ─────────────────────────────────
def test_TAO05_ocr_no_production_warning_exists(page: Page, live_server: str) -> None:
    _go(page, live_server)
    warn = page.locator("[data-testid='tax-ocr-no-production-warning']")
    assert warn.count() > 0, "tax-ocr-no-production-warning not found in DOM"


# ── TAO06 — OCR warning badge exists ─────────────────────────────────────────
def test_TAO06_ocr_warning_exists(page: Page, live_server: str) -> None:
    _go(page, live_server)
    warn = page.locator("[data-testid='tax-ocr-warning']")
    assert warn.count() > 0, "tax-ocr-warning not found in DOM"


# ── TAO07 — OCR text preview area exists ─────────────────────────────────────
def test_TAO07_ocr_text_preview_exists(page: Page, live_server: str) -> None:
    _go(page, live_server)
    preview = page.locator("[data-testid='tax-ocr-text-preview']")
    assert preview.count() > 0, "tax-ocr-text-preview not found in DOM"


# ── TAO08 — OCR candidate list exists ────────────────────────────────────────
def test_TAO08_ocr_candidate_list_exists(page: Page, live_server: str) -> None:
    _go(page, live_server)
    clist = page.locator("[data-testid='tax-ocr-candidate-list']")
    assert clist.count() > 0, "tax-ocr-candidate-list not found in DOM"


# ── TAO09 — Create extraction draft button exists ─────────────────────────────
def test_TAO09_ocr_create_extraction_draft_button_exists(page: Page, live_server: str) -> None:
    _go(page, live_server)
    btn = page.locator("[data-testid='tax-ocr-create-extraction-draft']")
    assert btn.count() > 0, "tax-ocr-create-extraction-draft not found in DOM"


# ── TAO10 — Reject OCR button exists ─────────────────────────────────────────
def test_TAO10_ocr_reject_button_exists(page: Page, live_server: str) -> None:
    _go(page, live_server)
    btn = page.locator("[data-testid='tax-ocr-reject-button']")
    assert btn.count() > 0, "tax-ocr-reject-button not found in DOM"


# ── TAO11 — OCR status badge exists ──────────────────────────────────────────
def test_TAO11_ocr_status_badge_exists(page: Page, live_server: str) -> None:
    _go(page, live_server)
    badge = page.locator("[data-testid='tax-ocr-status-badge']")
    assert badge.count() > 0, "tax-ocr-status-badge not found in DOM"


# ── TAO12 — No raw internal paths in DOM ─────────────────────────────────────
def test_TAO12_no_internal_paths_in_dom(page: Page, live_server: str) -> None:
    _go(page, live_server)
    html = page.content()
    assert "C:\\Users\\" not in html, "Windows path leaked into DOM"
    assert "instance\\tax_appeal_ocr" not in html, "OCR storage path leaked"
    assert "internal_file_path" not in html, "internal_file_path leaked into DOM"


# ── TAO13 — Qdrant/RAG shown inactive in OCR warning ─────────────────────────
def test_TAO13_qdrant_rag_shown_inactive(page: Page, live_server: str) -> None:
    _go(page, live_server)
    warn = page.locator("[data-testid='tax-ocr-warning']")
    if warn.count() > 0:
        text = warn.text_content() or ""
        assert "Qdrant" in text or "qdrant" in text.lower(), "Qdrant not mentioned in OCR warning"
        assert "RAG" in text or "rag" in text.lower(), "RAG not mentioned in OCR warning"
