# -*- coding: utf-8 -*-
"""
PVSTEP01–PVSTEP19 — Step 2 UX Cleanup: Visible Workspace Browser Proof Tests (Part J).

These tests navigate to the DEFAULT URL (no hash) so the default workspace
ws-professional (id="ws-professional", es-ws-active) is shown.  They prove that
the Step 2 UX cleanup — Section "2. مسارات وأغراض التقييم" — is actually visible
to the user in the browser under the three numbered subsections:

  2.1 الغرض من التقييم — المسارات المنطقية (assignment_purpose + purpose_logic_path)
  2.2 تحديد غرض التقييم — Valuation Purpose Router (purpose_route + purpose_subroute)
  2.3 مسارات الغرض المهنية (professional_context_path + professional_purpose_path + intended_user_category + intended_use)

No-deletion guarantees tested:
  - market_value is NOT an assignment purpose option (belongs in basis-of-value)
  - comparable_adjustment is NOT an assignment purpose option (it is a method step)
  - asset types (hotel, factory, land) are NOT assignment purpose options

Regression:
  - Section 5 upload/input controls still visible
  - Report type selects are NOT inside Section 2
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


# ─────────────────────────────────────────────────────────────────────────────
# PVSTEP01–PVSTEP05 — Section 2 structure visible
# ─────────────────────────────────────────────────────────────────────────────

def test_PVSTEP01_section2_valuation_purpose_routes_helper_visible(page: Page, live_server: str) -> None:
    """\
    PVSTEP01: pro-val-section-valuation-purpose-routes (helper text div) is visible
    in the default page (ws-professional).  Only present in visible workspace — count=1.
    """
    _go_to_visible_pv(page, live_server)
    el = page.locator('[data-testid="pro-val-section-valuation-purpose-routes"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVSTEP02_section2_heading_text_visible(page: Page, live_server: str) -> None:
    """\
    PVSTEP02: Section 3 main header div (professional-purpose-router) is visible
    and contains the heading text "3. الغرض من التقييم".
    In the 6-section layout, valuation purpose is Section 3 (merged with basis-of-value).
    Only present in visible workspace — count=1.
    """
    _go_to_visible_pv(page, live_server)
    header = page.locator('[data-testid="professional-purpose-router"]')
    expect(header).to_have_count(1)
    expect(header).to_be_visible()
    html = header.inner_html()
    assert "3." in html, "Section 3 header must contain '3.' numbering"
    assert "الغرض" in html, (
        "Section 3 header must contain 'الغرض' (heading الغرض من التقييم)"
    )


def test_PVSTEP03_subsection_21_logical_section_visible(page: Page, live_server: str) -> None:
    """\
    PVSTEP03: Subsection 2.1 container (pro-val-purpose-logical-section) is visible.
    Only in visible workspace — count=1.
    """
    _go_to_visible_pv(page, live_server)
    el = page.locator('[data-testid="pro-val-purpose-logical-section"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVSTEP04_subsection_22_purpose_router_section_visible(page: Page, live_server: str) -> None:
    """\
    PVSTEP04: Subsection 2.2 container (pro-val-purpose-router-section) is visible.
    Only in visible workspace — count=1.
    """
    _go_to_visible_pv(page, live_server)
    el = page.locator('[data-testid="pro-val-purpose-router-section"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVSTEP05_subsection_23_professional_purpose_section_visible(page: Page, live_server: str) -> None:
    """\
    PVSTEP05: Subsection 2.3 container (pro-val-professional-purpose-section) is visible.
    Only in visible workspace — count=1.
    """
    _go_to_visible_pv(page, live_server)
    el = page.locator('[data-testid="pro-val-professional-purpose-section"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


# ─────────────────────────────────────────────────────────────────────────────
# PVSTEP06–PVSTEP12 — Individual select/input controls visible
# Note: some testids appear in both ws-professional AND ws-professional-valuation.
#       Use .first to get the visible-workspace copy (DOM order: visible ~5000, hidden ~36000).
# ─────────────────────────────────────────────────────────────────────────────

def test_PVSTEP06_assignment_purpose_select_visible(page: Page, live_server: str) -> None:
    """\
    PVSTEP06: pro-val-assignment-purpose-select is visible in Section 2.1 of the
    default page.  Testid appears in both workspaces — use .first (visible workspace
    copy precedes hidden workspace copy in DOM).
    """
    _go_to_visible_pv(page, live_server)
    el = page.locator('[data-testid="pro-val-assignment-purpose-select"]').first
    expect(el).to_be_visible()


def test_PVSTEP07_purpose_logic_path_select_visible(page: Page, live_server: str) -> None:
    """\
    PVSTEP07: pro-val-purpose-logic-path-select is visible in Section 2.1.
    Testid appears in both workspaces — use .first.
    """
    _go_to_visible_pv(page, live_server)
    el = page.locator('[data-testid="pro-val-purpose-logic-path-select"]').first
    expect(el).to_be_visible()


def test_PVSTEP08_purpose_route_select_visible(page: Page, live_server: str) -> None:
    """\
    PVSTEP08: pro-val-purpose-route-select (45-option router) is visible in Section 2.2.
    Only in visible workspace — count=1.
    """
    _go_to_visible_pv(page, live_server)
    el = page.locator('[data-testid="pro-val-purpose-route-select"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVSTEP09_purpose_subroute_select_visible(page: Page, live_server: str) -> None:
    """\
    PVSTEP09: pro-val-purpose-subroute-select is visible in Section 2.2.
    Only in visible workspace — count=1.
    """
    _go_to_visible_pv(page, live_server)
    el = page.locator('[data-testid="pro-val-purpose-subroute-select"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVSTEP10_professional_context_path_select_visible(page: Page, live_server: str) -> None:
    """\
    PVSTEP10: pro-val-professional-context-path-select is visible in Section 2.3.
    Testid appears in both workspaces — use .first.
    """
    _go_to_visible_pv(page, live_server)
    el = page.locator('[data-testid="pro-val-professional-context-path-select"]').first
    expect(el).to_be_visible()


def test_PVSTEP11_professional_purpose_path_select_visible(page: Page, live_server: str) -> None:
    """\
    PVSTEP11: pro-val-professional-purpose-path-select is visible in Section 2.3.
    NEW field — only in visible workspace — count=1.
    """
    _go_to_visible_pv(page, live_server)
    el = page.locator('[data-testid="pro-val-professional-purpose-path-select"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVSTEP12_intended_user_category_select_visible(page: Page, live_server: str) -> None:
    """\
    PVSTEP12: pro-val-intended-user-category-select is visible in Section 2.3.
    Testid appears in both workspaces — use .first.
    """
    _go_to_visible_pv(page, live_server)
    el = page.locator('[data-testid="pro-val-intended-user-category-select"]').first
    expect(el).to_be_visible()


# ─────────────────────────────────────────────────────────────────────────────
# PVSTEP13–PVSTEP15 — No-deletion: forbidden values not in assignment purpose
# ─────────────────────────────────────────────────────────────────────────────

def test_PVSTEP13_market_value_not_in_assignment_purpose(page: Page, live_server: str) -> None:
    """\
    PVSTEP13: market_value is NOT an option in the visible assignment purpose select.
    It belongs in Section 3 (Basis of Value), not Section 2.
    Uses .first to read the visible workspace select (avoids strict-mode violation).
    """
    _go_to_visible_pv(page, live_server)
    sel = page.locator('[data-testid="pro-val-assignment-purpose-select"]').first
    html = sel.inner_html()
    assert 'value="market_value"' not in html, (
        "market_value must NOT be an assignment_purpose option — it belongs in Basis of Value (Section 3)"
    )


def test_PVSTEP14_comparable_adjustment_not_in_assignment_purpose(page: Page, live_server: str) -> None:
    """\
    PVSTEP14: comparable_adjustment is NOT an option in the visible assignment purpose select.
    It is a valuation method step, not a purpose.
    """
    _go_to_visible_pv(page, live_server)
    sel = page.locator('[data-testid="pro-val-assignment-purpose-select"]').first
    html = sel.inner_html()
    assert 'value="comparable_adjustment"' not in html, (
        "comparable_adjustment must NOT be an assignment_purpose option — it is a method step"
    )


def test_PVSTEP15_asset_types_not_in_assignment_purpose(page: Page, live_server: str) -> None:
    """\
    PVSTEP15: Asset type values (hotel, factory, land) are NOT options in the
    visible assignment purpose select.  They belong in Section 1 (Asset Definition).
    """
    _go_to_visible_pv(page, live_server)
    sel = page.locator('[data-testid="pro-val-assignment-purpose-select"]').first
    html = sel.inner_html()
    for asset_value in ("hotel", "factory", "land"):
        assert f'value="{asset_value}"' not in html, (
            f"'{asset_value}' must NOT be in assignment_purpose options — asset types belong in Section 1"
        )


# ─────────────────────────────────────────────────────────────────────────────
# PVSTEP16–PVSTEP19 — Regression: other sections unaffected
# ─────────────────────────────────────────────────────────────────────────────

def test_PVSTEP16_report_type_not_inside_section2(page: Page, live_server: str) -> None:
    """\
    PVSTEP16: Report type select (pro-val-report-type-select) is NOT nested inside
    the Section 2 container (pro-val-section-assignment-purpose).
    Report type belongs in Section 4 only.
    """
    _go_to_visible_pv(page, live_server)
    section2 = page.locator('[data-testid="pro-val-section-assignment-purpose"]').first
    report_type_inside_s2 = section2.locator('[data-testid="pro-val-report-type-select"]')
    expect(report_type_inside_s2).to_have_count(0)


def test_PVSTEP17_upload_controls_visible_in_section5(page: Page, live_server: str) -> None:
    """\
    PVSTEP17: Section 5 upload/input controls are still visible in the visible workspace.
    Checks pro-val-vis-structured-panel and pro-val-vis-upload-evidence which are
    unique to the visible workspace Section 5 — not affected by Section 2 restructure.
    """
    _go_to_visible_pv(page, live_server)
    structured_panel = page.locator('[data-testid="pro-val-vis-structured-panel"]')
    expect(structured_panel).to_have_count(1)
    expect(structured_panel).to_be_visible()
    upload_evidence = page.locator('[data-testid="pro-val-vis-upload-evidence"]')
    expect(upload_evidence).to_have_count(1)


def test_PVSTEP18_intended_use_input_visible(page: Page, live_server: str) -> None:
    """\
    PVSTEP18: pro-val-intended-use-input is visible in Section 2.3 of the visible workspace.
    Testid appears in both workspaces — use .first.
    """
    _go_to_visible_pv(page, live_server)
    el = page.locator('[data-testid="pro-val-intended-use-input"]').first
    expect(el).to_be_visible()


def test_PVSTEP19_purpose_router_summary_visible(page: Page, live_server: str) -> None:
    """\
    PVSTEP19: pro-val-purpose-router-summary (advisory summary div in Section 2.2) is
    visible in the default page.  Only in visible workspace — count=1.
    Inner span text-content "professional-purpose-summary-text" preserved for JS compat.
    """
    _go_to_visible_pv(page, live_server)
    el = page.locator('[data-testid="pro-val-purpose-router-summary"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()
    # JS-facing inner span must also be present
    inner_span = el.locator('#professional-purpose-summary-text')
    expect(inner_span).to_have_count(1)
