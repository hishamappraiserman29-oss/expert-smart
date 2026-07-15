"""
PVBG01–PVBG13 — Professional Valuation: Basis of Value Cleanup & Engine Governance Panel E2E Tests.

Verifies that:
- Section 3 "أساس القيمة المطلوب" is clean and contains only user-facing basis fields.
- Section 3 does NOT contain internal engine/governance/pipeline data.
- The Engine Governance Audit Panel exists and contains the moved items.
- No duplicate section-3 headings exist.
- No internal paths exposed in DOM.

Navigation: default URL (no hash) → ws-professional is the active workspace.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _go_to_visible_pv(page: Page, live_server: str) -> None:
    """Navigate to default page — ws-professional is the active workspace."""
    page.route("**/api/**", lambda r: r.fulfill(
        status=200, body=b'{"ok":true}', content_type="application/json"
    ))
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator('[data-testid="professional-wizard"]').wait_for(state="visible", timeout=10_000)


def _section3_html(page: Page) -> str:
    """Return innerHTML of the basis-of-value card inside Section 3 (ws-professional).
    Uses pro-val-basis-of-value-section (the inner card wrapping the 3 basis selects)
    since pro-val-section-basis-of-value is now a compat span (empty) inside Section 3.
    """
    return page.evaluate(
        "() => { var el = document.querySelector('[data-testid=\"pro-val-basis-of-value-section\"]');"
        " return el ? el.innerHTML : ''; }"
    )


def _governance_panel_html(page: Page) -> str:
    """Return innerHTML of the engine governance audit panel."""
    return page.evaluate(
        "() => { var el = document.querySelector('[data-testid=\"pro-val-engine-governance-audit-panel\"]');"
        " return el ? el.innerHTML : ''; }"
    )


# ─────────────────────────────────────────────────────────────────────────────
# PVBG01: Section 3 exists
# ─────────────────────────────────────────────────────────────────────────────

def test_PVBG01_section_basis_of_value_exists(page: Page, live_server: str) -> None:
    """PVBG01: pro-val-section-basis-of-value element is present in DOM."""
    _go_to_visible_pv(page, live_server)
    el = page.locator('[data-testid="pro-val-section-basis-of-value"]')
    assert el.count() >= 1, "pro-val-section-basis-of-value must exist"


# ─────────────────────────────────────────────────────────────────────────────
# PVBG02: Section 3 contains user-facing basis fields
# ─────────────────────────────────────────────────────────────────────────────

def test_PVBG02_section3_contains_basis_of_value_label(page: Page, live_server: str) -> None:
    """PVBG02: Section 3 contains 'أساس القيمة' label text."""
    _go_to_visible_pv(page, live_server)
    html = _section3_html(page)
    assert "أساس القيمة" in html, "Section 3 must contain 'أساس القيمة'"


def test_PVBG03_section3_contains_value_output_type_label(page: Page, live_server: str) -> None:
    """PVBG03: Section 3 contains 'نوع القيمة المطلوبة' label."""
    _go_to_visible_pv(page, live_server)
    html = _section3_html(page)
    assert "نوع القيمة المطلوبة" in html, "Section 3 must contain 'نوع القيمة المطلوبة'"


def test_PVBG04_section3_contains_value_premise_label(page: Page, live_server: str) -> None:
    """PVBG04: Section 3 contains 'فرضية القيمة' label."""
    _go_to_visible_pv(page, live_server)
    html = _section3_html(page)
    assert "فرضية القيمة" in html, "Section 3 must contain 'فرضية القيمة'"


# ─────────────────────────────────────────────────────────────────────────────
# PVBG05-07: Section 3 does NOT contain governance/pipeline data
# ─────────────────────────────────────────────────────────────────────────────

def test_PVBG05_section3_does_not_contain_draft_status(page: Page, live_server: str) -> None:
    """PVBG05: Section 3 (ws-professional) must NOT contain 'draft_pending_human_review'."""
    _go_to_visible_pv(page, live_server)
    html = _section3_html(page)
    assert "draft_pending_human_review" not in html, (
        "Section 3 must not contain draft_pending_human_review — that belongs in the governance panel"
    )


def test_PVBG06_section3_does_not_contain_pipeline_step_interface_fields(page: Page, live_server: str) -> None:
    """PVBG06: Section 3 must NOT contain 'حقول الواجهة' (pipeline step 1)."""
    _go_to_visible_pv(page, live_server)
    html = _section3_html(page)
    assert "حقول الواجهة" not in html, (
        "Section 3 must not contain 'حقول الواجهة' — pipeline steps belong in governance panel"
    )


def test_PVBG07_section3_does_not_contain_pipeline_step_output_contract(page: Page, live_server: str) -> None:
    """PVBG07: Section 3 must NOT contain 'عقد المخرجات' (pipeline step 9)."""
    _go_to_visible_pv(page, live_server)
    html = _section3_html(page)
    assert "عقد المخرجات" not in html, (
        "Section 3 must not contain 'عقد المخرجات' — pipeline steps belong in governance panel"
    )


# ─────────────────────────────────────────────────────────────────────────────
# PVBG08-11: Engine Governance Audit Panel
# ─────────────────────────────────────────────────────────────────────────────

def test_PVBG08_engine_governance_panel_exists(page: Page, live_server: str) -> None:
    """PVBG08: pro-val-engine-governance-audit-panel element is present."""
    _go_to_visible_pv(page, live_server)
    el = page.locator('[data-testid="pro-val-engine-governance-audit-panel"]')
    assert el.count() == 1, "pro-val-engine-governance-audit-panel must exist exactly once"


def test_PVBG09_governance_panel_contains_draft_status(page: Page, live_server: str) -> None:
    """PVBG09: Engine governance panel contains 'حالة المسودة'."""
    _go_to_visible_pv(page, live_server)
    html = _governance_panel_html(page)
    assert "حالة المسودة" in html, "Governance panel must contain 'حالة المسودة'"


def test_PVBG10_governance_panel_contains_validation_rules(page: Page, live_server: str) -> None:
    """PVBG10: Engine governance panel contains 'قواعد التحقق' (pipeline step 6)."""
    _go_to_visible_pv(page, live_server)
    html = _governance_panel_html(page)
    assert "قواعد التحقق" in html, "Governance panel must contain 'قواعد التحقق'"


def test_PVBG11_governance_panel_contains_output_contract(page: Page, live_server: str) -> None:
    """PVBG11: Engine governance panel contains 'عقد المخرجات' (pipeline step 9)."""
    _go_to_visible_pv(page, live_server)
    html = _governance_panel_html(page)
    assert "عقد المخرجات" in html, "Governance panel must contain 'عقد المخرجات'"


# ─────────────────────────────────────────────────────────────────────────────
# PVBG12: No duplicate "3. أساس القيمة المطلوب" heading
# ─────────────────────────────────────────────────────────────────────────────

def test_PVBG12_no_duplicate_section3_heading(page: Page, live_server: str) -> None:
    """PVBG12: The heading '3. أساس القيمة المطلوب' appears at most once per workspace in ws-professional."""
    _go_to_visible_pv(page, live_server)
    section3_html = _section3_html(page)
    count = section3_html.count("3. أساس القيمة المطلوب")
    assert count <= 1, (
        f"'3. أساس القيمة المطلوب' must not be duplicated within Section 3, found {count} occurrences"
    )


# ─────────────────────────────────────────────────────────────────────────────
# PVBG13: No internal filesystem paths in DOM
# ─────────────────────────────────────────────────────────────────────────────

def test_PVBG13_no_internal_paths_in_basis_or_governance_dom(page: Page, live_server: str) -> None:
    """PVBG13: No internal filesystem paths in Section 3 or governance panel."""
    _go_to_visible_pv(page, live_server)
    section3 = _section3_html(page)
    governance = _governance_panel_html(page)
    combined = section3 + governance
    for forbidden in ("C:\\", "/home/", "/var/", "core_engine/", "bridge_api"):
        assert forbidden not in combined, (
            f"Internal path fragment '{forbidden}' found in basis/governance DOM"
        )
