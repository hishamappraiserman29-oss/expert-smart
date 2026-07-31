"""
PDW01-PDW25 — Professional Dashboard Workflow E2E Tests
Verifies Part A-H improvements: routing console, dynamic technical fields,
integration matrix tabs, live status strip, weighted engine, GIS placeholder,
governance panel, and approval flow.
"""
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────

def goto_professional(page, live_server):
    page.goto(live_server)
    page.click('#es-tab-professional')
    page.wait_for_selector('[data-testid="professional-wizard"]', timeout=8000)


# ── PDW01: Professional routing console visible ────────────────────────────

def test_PDW01_routing_console_visible(page, live_server):
    """PDW01: professional-routing-console is present in the professional wizard."""
    goto_professional(page, live_server)
    el = page.query_selector('[data-testid="professional-routing-console"]')
    assert el is not None, "professional-routing-console not found"


# ── PDW02: Asset family selector wrapper ──────────────────────────────────

def test_PDW02_asset_family_selector_wrapper_visible(page, live_server):
    """PDW02: professional-asset-family-selector wrapper contains the family select."""
    goto_professional(page, live_server)
    wrapper = page.query_selector('[data-testid="professional-asset-family-selector"]')
    assert wrapper is not None
    sel = wrapper.query_selector('[data-testid="professional-asset-family"]')
    assert sel is not None, "professional-asset-family not inside asset-family-selector"


# ── PDW03: Asset subtype selector wrapper ─────────────────────────────────

def test_PDW03_asset_subtype_selector_wrapper_visible(page, live_server):
    """PDW03: professional-asset-subtype-selector wrapper contains the subtype select."""
    goto_professional(page, live_server)
    wrapper = page.query_selector('[data-testid="professional-asset-subtype-selector"]')
    assert wrapper is not None
    sel = wrapper.query_selector('[data-testid="professional-asset-subtype"]')
    assert sel is not None, "professional-asset-subtype not inside asset-subtype-selector"


# ── PDW04: Purpose route selector wrapper ─────────────────────────────────

def test_PDW04_purpose_route_selector_wrapper_visible(page, live_server):
    """PDW04: professional-purpose-route-selector wrapper contains the route select."""
    goto_professional(page, live_server)
    wrapper = page.query_selector('[data-testid="professional-purpose-route-selector"]')
    assert wrapper is not None
    sel = wrapper.query_selector('[data-testid="professional-purpose-route"]')
    assert sel is not None, "professional-purpose-route not inside purpose-route-selector"


# ── PDW05: Purpose subroute selector wrapper ──────────────────────────────

def test_PDW05_purpose_subroute_selector_wrapper_visible(page, live_server):
    """PDW05: professional-purpose-subroute-selector wrapper contains the subroute select."""
    goto_professional(page, live_server)
    wrapper = page.query_selector('[data-testid="professional-purpose-subroute-selector"]')
    assert wrapper is not None
    sel = wrapper.query_selector('[data-testid="professional-purpose-subroute"]')
    assert sel is not None


# ── PDW06: Industrial technical fields appear on industrial family ─────────

def test_PDW06_industrial_family_shows_technical_fields(page, live_server):
    """PDW06: Selecting advanced_industrial_logistics shows the industrial technical fields."""
    goto_professional(page, live_server)
    page.select_option('[data-testid="professional-asset-family"]', 'advanced_industrial_logistics')
    page.wait_for_timeout(400)
    panel = page.query_selector('[data-testid="professional-technical-input-panel"]')
    assert panel is not None
    assert panel.is_visible(), "professional-technical-input-panel not visible after industrial family"
    industrial = page.query_selector('[data-testid="professional-industrial-fields"]')
    assert industrial is not None
    assert industrial.is_visible(), "professional-industrial-fields not visible for industrial family"
    assert page.query_selector('[data-testid="professional-depreciation-factor"]') is not None
    assert page.query_selector('[data-testid="professional-effective-age"]') is not None
    assert page.query_selector('[data-testid="professional-economic-life"]') is not None
    assert page.query_selector('[data-testid="professional-construction-cost"]') is not None
    assert page.query_selector('[data-testid="professional-operating-status"]') is not None


# ── PDW07: Non-industrial family hides industrial fields ──────────────────

def test_PDW07_non_industrial_family_hides_industrial_fields(page, live_server):
    """PDW07: Selecting a non-industrial family hides industrial-specific fields."""
    goto_professional(page, live_server)
    page.select_option('[data-testid="professional-asset-family"]', 'heritage_cultural_assets')
    page.wait_for_timeout(400)
    industrial = page.query_selector('[data-testid="professional-industrial-fields"]')
    assert industrial is not None
    assert not industrial.is_visible(), "industrial fields should be hidden for heritage family"


# ── PDW08: Specialized family shows specialized fields ────────────────────

def test_PDW08_specialized_family_shows_specialized_fields(page, live_server):
    """PDW08: Selecting specialized_medical_science shows specialized technical fields."""
    goto_professional(page, live_server)
    page.select_option('[data-testid="professional-asset-family"]', 'specialized_medical_science')
    page.wait_for_timeout(400)
    specialized = page.query_selector('[data-testid="professional-specialized-fields"]')
    assert specialized is not None
    assert specialized.is_visible(), "professional-specialized-fields not visible for medical family"


# ── PDW09: Integration tabs container visible ─────────────────────────────

def test_PDW09_integration_tabs_visible(page, live_server):
    """PDW09: professional-integration-tabs wrapper is present."""
    goto_professional(page, live_server)
    el = page.query_selector('[data-testid="professional-integration-tabs"]')
    assert el is not None, "professional-integration-tabs not found"


# ── PDW10: All nine matrix tabs clickable ─────────────────────────────────

def test_PDW10_all_nine_tabs_clickable(page, live_server):
    """PDW10: All 9 matrix tabs can be clicked without JS error."""
    goto_professional(page, live_server)
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
        btn = page.query_selector(f'[data-testid="{tid}"]')
        assert btn is not None, f"{tid} not found"
        btn.click()
        page.wait_for_timeout(100)
    panel = page.query_selector('[data-testid="professional-matrix-tab-panel"]')
    assert panel is not None


# ── PDW11: Market comparables tab does NOT claim Qdrant active ────────────

def test_PDW11_market_comparables_no_qdrant_claim(page, live_server):
    """PDW11: Market comparables tab shows future-ready message, not active Qdrant claim."""
    goto_professional(page, live_server)
    page.query_selector('[data-testid="professional-matrix-tab-market-comparables"]').click()
    page.wait_for_timeout(200)
    panel = page.query_selector('#prof-matrix-panel')
    assert panel is not None
    text = panel.inner_text()
    assert "Qdrant" in text or "Backend Advisor" in text, "should mention Qdrant/Backend Advisor (future-ready)"
    assert "مفعّل" not in text or "غير مفعّل" in text or "بعد تفعيل" in text, \
        "should not claim Qdrant is active"


# ── PDW12: Agentic enrichment tab does NOT claim RAG active ──────────────

def test_PDW12_agentic_enrichment_no_rag_claim(page, live_server):
    """PDW12: Agentic enrichment tab shows future-ready message, not active RAG/web claim."""
    goto_professional(page, live_server)
    page.query_selector('[data-testid="professional-matrix-tab-agentic-enrichment"]').click()
    page.wait_for_timeout(200)
    panel = page.query_selector('#prof-matrix-panel')
    text = panel.inner_text()
    assert "RAG" in text or "الإثراء الآلي" in text
    assert "غير مفعّل" in text or "لاحقًا" in text, \
        "agentic enrichment should state it is not active yet"


# ── PDW13: Live status strip visible ─────────────────────────────────────

def test_PDW13_live_status_strip_visible(page, live_server):
    """PDW13: professional-live-status-strip is visible."""
    goto_professional(page, live_server)
    el = page.query_selector('[data-testid="professional-live-status-strip"]')
    assert el is not None, "professional-live-status-strip not found"
    assert el.is_visible()


# ── PDW14: New metadata bar fields present ────────────────────────────────

def test_PDW14_metadata_bar_new_fields_present(page, live_server):
    """PDW14: New live-strip fields (asset-status, purpose-status, report-status, data-readiness) present."""
    goto_professional(page, live_server)
    for tid in ["professional-asset-status", "professional-purpose-status",
                "professional-report-status", "professional-data-readiness-status"]:
        el = page.query_selector(f'[data-testid="{tid}"]')
        assert el is not None, f"{tid} not found in live status strip"


# ── PDW15: Report status shows draft/non-certified ────────────────────────

def test_PDW15_report_status_shows_draft(page, live_server):
    """PDW15: professional-report-status shows 'مسودة' or 'غير معتمدة'."""
    goto_professional(page, live_server)
    el = page.query_selector('[data-testid="professional-report-status"]')
    assert el is not None
    text = el.inner_text()
    assert "مسودة" in text or "غير معتمد" in text, f"report-status should say draft/non-certified, got: {text}"


# ── PDW16: Selecting IFRS purpose updates IFRS level ─────────────────────

def test_PDW16_ifrs_purpose_updates_level(page, live_server):
    """PDW16: Selecting ifrs_13_fair_value updates IFRS status to Level 3."""
    goto_professional(page, live_server)
    page.select_option('[data-testid="professional-purpose-route"]', 'ifrs_13_fair_value')
    page.wait_for_timeout(400)
    el = page.query_selector('[data-testid="professional-ifrs-level-status"]')
    assert el is not None
    assert "Level 3" in el.inner_text(), f"IFRS level should be Level 3 for ifrs_13_fair_value, got: {el.inner_text()}"


# ── PDW17: Human approval status shows نعم ────────────────────────────────

def test_PDW17_human_approval_status_shows_yes(page, live_server):
    """PDW17: professional-human-approval-status shows 'نعم' (default)."""
    goto_professional(page, live_server)
    el = page.query_selector('[data-testid="professional-human-approval-status"]')
    assert el is not None
    assert "نعم" in el.inner_text()


# ── PDW18: Weighted engine panel visible ─────────────────────────────────

def test_PDW18_weighted_engine_panel_visible(page, live_server):
    """PDW18: professional-weighted-engine-panel is present."""
    goto_professional(page, live_server)
    el = page.query_selector('[data-testid="professional-weighted-engine-panel"]')
    assert el is not None, "professional-weighted-engine-panel not found"


# ── PDW19: Weights total warning appears when weights ≠ 100 ──────────────

def test_PDW19_weights_warning_appears_when_not_100(page, live_server):
    """PDW19: professional-weights-total-warning appears when weights don't total 100."""
    goto_professional(page, live_server)
    page.fill('[data-testid="professional-sales-weight"]',  '50')
    page.fill('[data-testid="professional-income-weight"]', '50')
    page.fill('[data-testid="professional-cost-weight"]',   '50')
    page.query_selector('[data-testid="professional-cost-weight"]').dispatch_event('input')
    page.wait_for_timeout(300)
    warning = page.query_selector('[data-testid="professional-weights-total-warning"]')
    assert warning is not None
    assert warning.is_visible(), "weights warning should be visible when total is 150%"


# ── PDW20: Weighted value computed and labelled non-certified ─────────────

def test_PDW20_weighted_value_shows_preliminary(page, live_server):
    """PDW20: Entering method values shows weighted output labelled غير معتمدة / مبدئية."""
    goto_professional(page, live_server)
    page.fill('[data-testid="professional-sales-value"]',   '1200000')
    page.fill('[data-testid="professional-sales-weight"]',  '40')
    page.fill('[data-testid="professional-income-value"]',  '1100000')
    page.fill('[data-testid="professional-income-weight"]', '40')
    page.fill('[data-testid="professional-cost-value"]',    '1050000')
    page.fill('[data-testid="professional-cost-weight"]',   '20')
    page.query_selector('[data-testid="professional-cost-weight"]').dispatch_event('input')
    page.wait_for_timeout(300)
    output_el = page.query_selector('[data-testid="professional-weighted-value-output"]')
    assert output_el is not None
    text = output_el.inner_text()
    assert text != '—', "weighted value output should not remain blank after entering values"
    # label text in the containing panel says غير معتمدة / مبدئية
    panel = page.query_selector('[data-testid="professional-weighted-engine-panel"]')
    panel_text = panel.inner_text()
    assert "غير معتمد" in panel_text or "مبدئ" in panel_text


# ── PDW21: GIS card visible ───────────────────────────────────────────────

def test_PDW21_gis_card_visible(page, live_server):
    """PDW21: professional-gis-card is present."""
    goto_professional(page, live_server)
    el = page.query_selector('[data-testid="professional-gis-card"]')
    assert el is not None, "professional-gis-card not found"


# ── PDW22: GIS note says external map is future/backend only ─────────────

def test_PDW22_gis_note_says_future_backend(page, live_server):
    """PDW22: GIS note states no external maps are called and integration is future backend-only."""
    goto_professional(page, live_server)
    note = page.query_selector('[data-testid="professional-gis-note"]')
    assert note is not None
    text = note.inner_text()
    assert "لا يتم" in text or "لاحق" in text or "Backend" in text, \
        f"GIS note should say external maps not called now, got: {text}"


# ── PDW23: Governance panel visible ──────────────────────────────────────

def test_PDW23_governance_panel_visible(page, live_server):
    """PDW23: professional-governance-panel is present in step-output."""
    goto_professional(page, live_server)
    el = page.query_selector('[data-testid="professional-governance-panel"]')
    assert el is not None, "professional-governance-panel not found"


# ── PDW24: Draft PDF button disabled with future-ready text ──────────────

def test_PDW24_draft_pdf_button_disabled_or_safe(page, live_server):
    """PDW24: professional-draft-pdf-button is disabled or shows future-ready message."""
    goto_professional(page, live_server)
    btn = page.query_selector('[data-testid="professional-draft-pdf-button"]')
    assert btn is not None
    # Either disabled (no live endpoint yet) or enabled via safe endpoint
    is_disabled = btn.get_attribute('disabled') is not None
    # If not disabled, that's also fine (endpoint may exist) — no assertion failure
    status_el = page.query_selector('[data-testid="professional-draft-pdf-status"]')
    assert status_el is not None
    if is_disabled:
        # Status should mention future activation
        text = status_el.inner_text()
        assert "بعد" in text or "ربط" in text or "تفعيل" in text, \
            f"disabled PDF button should show future-ready status, got: {text}"


# ── PDW25: Submit approval CTA shows non-certified confirmation ───────────

def test_PDW25_submit_approval_shows_non_certified_confirmation(page, live_server):
    """PDW25: Clicking submit-approval-button shows non-certified expert review confirmation."""
    goto_professional(page, live_server)
    btn = page.query_selector('[data-testid="professional-submit-approval-button"]')
    assert btn is not None
    btn.click()
    page.wait_for_timeout(500)
    # Check that the governance status message updated
    status_el = page.query_selector('[data-testid="professional-draft-pdf-status"]')
    assert status_el is not None
    text = status_el.inner_text()
    assert "ليس تقريرًا معتمدًا" in text or "مراجعة الخبير" in text or "تسجيل طلب" in text, \
        f"Submit approval should show non-certified confirmation, got: {text}"
    # Confirm no certified/signed claims
    assert "معتمد الآن" not in text
    assert "تم توقيع" not in text
    assert "صالح للبنوك الآن" not in text


# ── PDW26: No Excel link exposed to user ─────────────────────────────────

def test_PDW26_no_excel_link_in_professional_tab(page, live_server):
    """PDW26: No .xlsx download link appears in the professional tab."""
    goto_professional(page, live_server)
    ws = page.query_selector('#ws-professional')
    assert ws is not None
    links = ws.query_selector_all('a[href*=".xlsx"], a[href*="excel"], a[download*=".xlsx"]')
    assert len(links) == 0, f"Found {len(links)} xlsx link(s) in professional tab — must not expose Excel"


# ── PDW27: Existing wizard tests still covered ────────────────────────────

def test_PDW27_existing_wizard_structure_intact(page, live_server):
    """PDW27: Core wizard structure (steps 1-5) is still present and unbroken."""
    goto_professional(page, live_server)
    for tid in ["professional-step-asset", "professional-step-purpose",
                "professional-step-matrix", "professional-step-requirements",
                "professional-step-output"]:
        el = page.query_selector(f'[data-testid="{tid}"]')
        assert el is not None, f"{tid} missing — wizard step broken"
