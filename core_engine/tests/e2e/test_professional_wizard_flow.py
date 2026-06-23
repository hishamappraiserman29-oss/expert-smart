"""
PWF01-PWF29 — Professional Wizard Flow E2E Tests
Verifies the 5-step wizard layout on the professional valuation tab.
"""
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────

def goto_professional(page, live_server):
    page.goto(live_server)
    page.click('[data-testid="professional-tab"]')
    page.wait_for_selector('[data-testid="professional-wizard"]', timeout=8000)


# ── PWF01: Wizard wrapper exists ───────────────────────────────────────────

def test_pwf01_wizard_wrapper_exists(page, live_server):
    """PWF01: data-testid=professional-wizard present inside ws-professional."""
    page.goto(live_server)
    ws = page.query_selector("#ws-professional")
    assert ws is not None
    wizard = ws.query_selector('[data-testid="professional-wizard"]')
    assert wizard is not None, "professional-wizard not found inside ws-professional"


# ── PWF02-PWF07: Step 1 — Asset Definition Console ────────────────────────

def test_pwf02_step_asset_exists(page, live_server):
    """PWF02: professional-step-asset is present."""
    page.goto(live_server)
    ws = page.query_selector("#ws-professional")
    assert ws.query_selector('[data-testid="professional-step-asset"]') is not None


def test_pwf03_asset_console_header_exists(page, live_server):
    """PWF03: professional-asset-console header exists inside step-asset."""
    page.goto(live_server)
    step = page.query_selector('[data-testid="professional-step-asset"]')
    assert step is not None
    hdr = step.query_selector('[data-testid="professional-asset-console"]')
    assert hdr is not None


def test_pwf04_asset_family_has_testid(page, live_server):
    """PWF04: prof-asset-family has data-testid=professional-asset-family."""
    page.goto(live_server)
    el = page.query_selector('[data-testid="professional-asset-family"]')
    assert el is not None
    assert el.get_attribute("id") == "prof-asset-family"


def test_pwf05_asset_subtype_has_testid(page, live_server):
    """PWF05: prof-asset-subtype has data-testid=professional-asset-subtype."""
    page.goto(live_server)
    el = page.query_selector('[data-testid="professional-asset-subtype"]')
    assert el is not None
    assert el.get_attribute("id") == "prof-asset-subtype"


def test_pwf06_asset_family_visible(page, live_server):
    """PWF06: prof-asset-family is visible as canonical asset family selector (Task 7 revised)."""
    page.goto(live_server)
    assert page.is_visible("#prof-asset-family"), "#prof-asset-family must be visible"


def test_pwf07_valuation_profile_exists(page, live_server):
    """PWF07: professional-valuation-profile element exists inside ws-professional."""
    page.goto(live_server)
    ws = page.query_selector("#ws-professional")
    el = ws.query_selector('[data-testid="professional-valuation-profile"]')
    assert el is not None


# ── PWF08-PWF12: Step 2 — Valuation Purpose Router ────────────────────────

def test_pwf08_step_purpose_exists(page, live_server):
    """PWF08: professional-step-purpose present in ws-professional."""
    page.goto(live_server)
    ws = page.query_selector("#ws-professional")
    assert ws.query_selector('[data-testid="professional-step-purpose"]') is not None


def test_pwf09_purpose_router_header_exists(page, live_server):
    """PWF09: professional-purpose-router header inside step-purpose."""
    page.goto(live_server)
    step = page.query_selector('[data-testid="professional-step-purpose"]')
    assert step is not None
    hdr = step.query_selector('[data-testid="professional-purpose-router"]')
    assert hdr is not None


def test_pwf10_purpose_route_has_testid(page, live_server):
    """PWF10: prof-purpose-route has data-testid=professional-purpose-route."""
    page.goto(live_server)
    el = page.query_selector('[data-testid="professional-purpose-route"]')
    assert el is not None
    assert el.get_attribute("id") == "prof-purpose-route"


def test_pwf11_purpose_subroute_has_testid(page, live_server):
    """PWF11: prof-purpose-subroute has data-testid=professional-purpose-subroute."""
    page.goto(live_server)
    el = page.query_selector('[data-testid="professional-purpose-subroute"]')
    assert el is not None
    assert el.get_attribute("id") == "prof-purpose-subroute"


def test_pwf12_purpose_summary_exists(page, live_server):
    """PWF12: professional-purpose-summary div exists in step-purpose."""
    page.goto(live_server)
    step = page.query_selector('[data-testid="professional-step-purpose"]')
    assert step is not None
    assert step.query_selector('[data-testid="professional-purpose-summary"]') is not None


# ── PWF13-PWF22: Step 3 — Interactive Matrix Dashboard ────────────────────

def test_pwf13_step_matrix_exists(page, live_server):
    """PWF13: professional-step-matrix present."""
    page.goto(live_server)
    ws = page.query_selector("#ws-professional")
    assert ws.query_selector('[data-testid="professional-step-matrix"]') is not None


def test_pwf14_matrix_dashboard_header(page, live_server):
    """PWF14: professional-matrix-dashboard header inside step-matrix."""
    page.goto(live_server)
    step = page.query_selector('[data-testid="professional-step-matrix"]')
    assert step.query_selector('[data-testid="professional-matrix-dashboard"]') is not None


def test_pwf15_matrix_metadata_bar(page, live_server):
    """PWF15: professional-live-status-strip bar exists (renamed from professional-matrix-metadata)."""
    page.goto(live_server)
    assert page.query_selector('[data-testid="professional-live-status-strip"]') is not None


def test_pwf16_matrix_active_route(page, live_server):
    """PWF16: professional-active-route-status element exists (renamed)."""
    page.goto(live_server)
    el = page.query_selector('[data-testid="professional-active-route-status"]')
    assert el is not None
    assert len(el.inner_text().strip()) > 0


def test_pwf17_matrix_ifrs_level(page, live_server):
    """PWF17: professional-ifrs-level-status element exists and shows level info (renamed)."""
    page.goto(live_server)
    el = page.query_selector('[data-testid="professional-ifrs-level-status"]')
    assert el is not None


def test_pwf18_human_approval_required_shows_yes(page, live_server):
    """PWF18: professional-human-approval-status shows 'نعم' (renamed)."""
    page.goto(live_server)
    el = page.query_selector('[data-testid="professional-human-approval-status"]')
    assert el is not None
    assert "نعم" in el.inner_text()


def test_pwf19_final_without_approval_shows_no(page, live_server):
    """PWF19: professional-final-without-approval shows 'لا'."""
    page.goto(live_server)
    el = page.query_selector('[data-testid="professional-final-without-approval"]')
    assert el is not None
    assert "لا" in el.inner_text()


def test_pwf20_draft_status_exists(page, live_server):
    """PWF20: professional-draft-status element exists."""
    page.goto(live_server)
    assert page.query_selector('[data-testid="professional-draft-status"]') is not None


def test_pwf21_all_nine_matrix_tabs_exist(page, live_server):
    """PWF21: All 9 matrix tab buttons exist inside professional-matrix-tabs."""
    page.goto(live_server)
    container = page.query_selector('[data-testid="professional-matrix-tabs"]')
    assert container is not None
    tab_testids = [
        "professional-matrix-tab-ui-fields",
        "professional-matrix-tab-db-mapping",
        "professional-matrix-tab-engine-inputs",
        "professional-matrix-tab-market-comparables",
        "professional-matrix-tab-agentic-enrichment",
        "professional-matrix-tab-validation-rules",
        "professional-matrix-tab-human-approval",
        "professional-matrix-tab-report-disclosure",
        "professional-matrix-tab-output-contract",
    ]
    for tid in tab_testids:
        el = container.query_selector(f'[data-testid="{tid}"]')
        assert el is not None, f"Tab {tid} not found inside professional-matrix-tabs"


def test_pwf22_matrix_tab_panel_exists(page, live_server):
    """PWF22: professional-matrix-tab-panel exists and has id=prof-matrix-panel."""
    page.goto(live_server)
    el = page.query_selector('[data-testid="professional-matrix-tab-panel"]')
    assert el is not None
    assert el.get_attribute("id") == "prof-matrix-panel"


# ── PWF23-PWF26: Step 4 — Requirements / Validation / Approval ────────────

def test_pwf23_step_requirements_exists(page, live_server):
    """PWF23: professional-step-requirements present."""
    page.goto(live_server)
    ws = page.query_selector("#ws-professional")
    assert ws.query_selector('[data-testid="professional-step-requirements"]') is not None


def test_pwf24_requirements_approval_header(page, live_server):
    """PWF24: professional-requirements-approval header inside step-requirements."""
    page.goto(live_server)
    step = page.query_selector('[data-testid="professional-step-requirements"]')
    assert step.query_selector('[data-testid="professional-requirements-approval"]') is not None


def test_pwf25_requirements_checklist_wraps_es_req_panel(page, live_server):
    """PWF25: professional-requirements-checklist contains #es-req-panel."""
    page.goto(live_server)
    checklist = page.query_selector('[data-testid="professional-requirements-checklist"]')
    assert checklist is not None
    req_panel = checklist.query_selector("#es-req-panel")
    assert req_panel is not None, "#es-req-panel not found inside professional-requirements-checklist"


def test_pwf26_step4_sub_elements_exist(page, live_server):
    """PWF26: validation-summary, human-approval-panel, expert-review-cta all exist."""
    page.goto(live_server)
    for tid in ["professional-validation-summary",
                "professional-human-approval-panel",
                "professional-expert-review-cta"]:
        assert page.query_selector(f'[data-testid="{tid}"]') is not None, f"{tid} missing"


# ── PWF27-PWF29: Step 5 — Draft Output / Expert Review ────────────────────

def test_pwf27_step_output_exists(page, live_server):
    """PWF27: professional-step-output present."""
    page.goto(live_server)
    ws = page.query_selector("#ws-professional")
    assert ws.query_selector('[data-testid="professional-step-output"]') is not None


def test_pwf28_output_section_header(page, live_server):
    """PWF28: professional-output-section header inside step-output."""
    page.goto(live_server)
    step = page.query_selector('[data-testid="professional-step-output"]')
    assert step.query_selector('[data-testid="professional-output-section"]') is not None


def test_pwf29_step5_sub_elements_exist(page, live_server):
    """PWF29: draft-warning, output-contract-summary, request-expert-review all exist."""
    page.goto(live_server)
    for tid in ["professional-draft-warning",
                "professional-output-contract-summary",
                "professional-request-expert-review"]:
        assert page.query_selector(f'[data-testid="{tid}"]') is not None, f"{tid} missing"
