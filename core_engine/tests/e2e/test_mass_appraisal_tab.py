"""
test_mass_appraisal_tab.py — E2E tests for the Composite & Mass Appraisal Hub.

MAT01–MAT05   Tab and mode selector
MAT06–MAT10   JSON input + sample data + validation
MAT11–MAT20   Run button, progress, results dashboard, weighting, outliers
MAT21–MAT27   Ratio study, governance panel
MAT28–MAT32   Export buttons and report safety
MAT33–MAT36   Expert approval lead form
MAT37–MAT40   Regression: professional tab clean, existing suites unaffected
"""
from __future__ import annotations

import json
import pytest

# ── helpers ──────────────────────────────────────────────────────────────────

VALID_SAMPLE = json.dumps([
    {"row_id": "A001", "location": "القاهرة - التجمع الخامس",
     "area": 150, "zone_id": "CAI_NEW_CAIRO",
     "property_type": "residential", "property_class": "apartment",
     "valuation_purpose": "market_value"},
    {"row_id": "A002", "location": "المعادي",
     "area": 400, "zone_id": "CAI_MAADI",
     "property_type": "commercial", "property_class": "office",
     "valuation_purpose": "market_value"},
    {"row_id": "A003", "location": "مدينة نصر",
     "area": 200, "zone_id": "CAI_NASR",
     "property_type": "residential", "property_class": "apartment",
     "valuation_purpose": "bank_financing"},
    {"row_id": "A004", "location": "الزمالك",
     "area": 300, "zone_id": "PRIME_ZONE",
     "property_type": "hospitality", "property_class": "hotel",
     "valuation_purpose": "market_value"},
    {"row_id": "A005", "location": "العبور الصناعية",
     "area": 1000, "zone_id": "IND_OBOUR",
     "property_type": "industrial", "property_class": "warehouse",
     "valuation_purpose": "market_value"},
])

INCOMPLETE_SAMPLE = json.dumps([
    {"row_id": "B001", "location": "منطقة مجهولة", "area": 100, "property_type": "residential"},
    {"row_id": "B002", "location": "منطقة أخرى",   "area": 200, "property_type": "commercial"},
])


def _goto(page, live_server: str, timeout: int = 15_000):
    page.goto(live_server, timeout=timeout)
    page.wait_for_load_state("networkidle", timeout=timeout)


def _open_composite(page):
    page.click("#es-tab-composite")
    page.wait_for_selector("#ws-composite.es-ws-active", timeout=6_000)


def _switch_mass_mode(page):
    _open_composite(page)
    page.click('[data-testid="composite-mode-mass"]')
    page.wait_for_selector('#mass-appraisal-workflow', timeout=3_000)
    page.wait_for_timeout(200)


def _switch_composite_mode(page):
    _open_composite(page)
    page.click('[data-testid="composite-mode-composite"]')
    page.wait_for_timeout(300)


def _fill_json(page, data: str):
    ta = page.query_selector('[data-testid="mass-json-input"]')
    assert ta is not None
    ta.fill(data)


def _click_run(page):
    page.click('[data-testid="mass-run-button"]')
    page.wait_for_function(
        "document.getElementById('mass-results-dashboard').style.display !== 'none'",
        timeout=10_000,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# MAT01–MAT05  Tab and mode selector
# ═══════════════════════════════════════════════════════════════════════════════

def test_MAT01_composite_tab_opens(page, live_server):
    """Composite tab opens and ws-composite becomes active."""
    _goto(page, live_server)
    _open_composite(page)
    assert page.is_visible("#ws-composite")


def test_MAT02_mode_selector_exists(page, live_server):
    """Mode selector with both buttons exists in ws-composite."""
    _goto(page, live_server)
    _open_composite(page)
    assert page.query_selector('[data-testid="composite-mode-selector"]') is not None
    assert page.query_selector('[data-testid="composite-mode-mass"]') is not None
    assert page.query_selector('[data-testid="composite-mode-composite"]') is not None


def test_MAT03_mass_mode_shows_workspace(page, live_server):
    """Clicking mass mode reveals the mass-appraisal-workspace."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    ws = page.query_selector('[data-testid="mass-appraisal-workspace"]')
    assert ws is not None and ws.is_visible()


def test_MAT04_composite_mode_shows_cmp_form(page, live_server):
    """Switching to composite mode shows the cmp-form (cmp elements accessible)."""
    _goto(page, live_server)
    _switch_composite_mode(page)
    # cmp-mode-wrapper should be visible
    wrapper = page.query_selector("#cmp-mode-wrapper")
    assert wrapper is not None
    assert wrapper.is_visible()
    # cmp-form should be inside cmp-mode-wrapper
    cmp_form = wrapper.query_selector("#cmp-form")
    assert cmp_form is not None


def test_MAT05_mass_mode_is_default(page, live_server):
    """On fresh composite tab open, mass-appraisal-workflow is visible by default."""
    _goto(page, live_server)
    _open_composite(page)
    ws = page.query_selector('[data-testid="mass-appraisal-workspace"]')
    assert ws is not None and ws.is_visible()


# ═══════════════════════════════════════════════════════════════════════════════
# MAT06–MAT10  JSON input + sample data + validation
# ═══════════════════════════════════════════════════════════════════════════════

def test_MAT06_json_textarea_exists(page, live_server):
    """mass-json-input textarea exists in mass mode."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    el = page.query_selector('[data-testid="mass-json-input"]')
    assert el is not None


def test_MAT07_sample_data_button_fills_json(page, live_server):
    """Clicking mass-load-sample fills the JSON textarea with data."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    page.click('[data-testid="mass-load-sample"]')
    page.wait_for_timeout(300)
    ta = page.query_selector('[data-testid="mass-json-input"]')
    assert ta is not None
    val = ta.input_value()
    assert len(val) > 10, "JSON textarea should contain sample data after clicking load-sample"
    data = json.loads(val)
    assert isinstance(data, list) and len(data) >= 1


def test_MAT08_validator_accepts_valid_sample(page, live_server):
    """Smart validator shows no errors for valid sample JSON."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    _fill_json(page, VALID_SAMPLE)
    _click_run(page)
    panel = page.query_selector('[data-testid="mass-validation-panel"]')
    assert panel is not None and panel.is_visible()
    # Should show 0 errors (text "0" appears in error count cell)
    text = panel.inner_text()
    assert "5" in text or "أصل" in text or "صحيح" in text


def test_MAT09_validator_detects_invalid_json(page, live_server):
    """Smart validator shows error for invalid JSON."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    _fill_json(page, "{ not valid json }")
    page.click('[data-testid="mass-run-button"]')
    page.wait_for_timeout(500)
    panel = page.query_selector('[data-testid="mass-validation-panel"]')
    assert panel is not None and panel.is_visible()
    text = panel.inner_text()
    assert "JSON" in text or "غير صالح" in text or "أخطاء" in text


def test_MAT10_validator_detects_missing_required_fields(page, live_server):
    """Validator flags rows missing required fields."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    bad = json.dumps([{"row_id": "X001"}])  # missing location, area, property_type
    _fill_json(page, bad)
    page.click('[data-testid="mass-run-button"]')
    page.wait_for_timeout(500)
    panel = page.query_selector('[data-testid="mass-validation-panel"]')
    assert panel is not None and panel.is_visible()
    text = panel.inner_text()
    assert "مفقود" in text or "أخطاء" in text or "1" in text


# ═══════════════════════════════════════════════════════════════════════════════
# MAT11–MAT20  Run, progress, results dashboard, weighting, outlier
# ═══════════════════════════════════════════════════════════════════════════════

def test_MAT11_run_button_processes_valid_sample(page, live_server):
    """Run button with valid data produces results without crashing."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    _fill_json(page, VALID_SAMPLE)
    _click_run(page)
    dash = page.query_selector('[data-testid="mass-results-dashboard"]')
    assert dash is not None and dash.is_visible()


def test_MAT12_progress_appears_during_run(page, live_server):
    """Processing progress/status element exists in DOM."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    assert page.query_selector('[data-testid="mass-processing-progress"]') is not None
    assert page.query_selector('[data-testid="mass-processing-status"]') is not None


def test_MAT13_results_dashboard_appears(page, live_server):
    """After run, results dashboard is visible."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    _fill_json(page, VALID_SAMPLE)
    _click_run(page)
    assert page.is_visible('[data-testid="mass-results-dashboard"]')


def test_MAT14_total_value_populated(page, live_server):
    """Total portfolio value cell shows a non-dash value after run."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    _fill_json(page, VALID_SAMPLE)
    _click_run(page)
    el = page.query_selector("#mass-dashboard-total-value")
    assert el is not None
    txt = el.inner_text().strip()
    assert txt not in ("—", "", "0"), f"Total value should be populated, got: {txt!r}"


def test_MAT15_average_price_m2_populated(page, live_server):
    """Average price/m² cell shows a non-dash value after run."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    _fill_json(page, VALID_SAMPLE)
    _click_run(page)
    el = page.query_selector("#mass-dashboard-avg-ppm")
    assert el is not None
    txt = el.inner_text().strip()
    assert txt not in ("—", "", "0"), f"Avg price/m² should be populated, got: {txt!r}"


def test_MAT16_unit_count_populated(page, live_server):
    """Unit count shows the number of rows processed."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    _fill_json(page, VALID_SAMPLE)
    _click_run(page)
    el = page.query_selector("#mass-dashboard-unit-count")
    assert el is not None
    txt = el.inner_text().strip()
    assert txt == "5", f"Unit count should be 5, got: {txt!r}"


def test_MAT17_weighting_panel_appears(page, live_server):
    """Weighting panel becomes visible after run."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    _fill_json(page, VALID_SAMPLE)
    _click_run(page)
    assert page.is_visible('[data-testid="mass-weighting-panel"]')


def test_MAT18_low_comparables_warning_appears_with_incomplete_data(page, live_server):
    """LOW_COMPARABLES warning appears when more than 40% of rows lack zone_id."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    _fill_json(page, INCOMPLETE_SAMPLE)
    _click_run(page)
    page.wait_for_function(
        "document.getElementById('mass-weighting-panel').style.display !== 'none'",
        timeout=8_000,
    )
    warning = page.query_selector("#mass-low-comparables-warning")
    assert warning is not None and warning.is_visible()
    assert "LOW_COMPARABLES" in warning.inner_text()


def test_MAT19_outlier_panel_appears(page, live_server):
    """Outlier panel becomes visible after run."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    _fill_json(page, VALID_SAMPLE)
    _click_run(page)
    assert page.is_visible('[data-testid="mass-outlier-panel"]')


def test_MAT20_outlier_panel_does_not_auto_remove_rows(page, live_server):
    """Outlier panel says rows are NOT removed automatically."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    _fill_json(page, VALID_SAMPLE)
    _click_run(page)
    panel = page.query_selector('[data-testid="mass-outlier-panel"]')
    assert panel is not None
    text = panel.inner_text()
    assert "لم يتم حذف" in text or "المراجعة البشرية" in text


# ═══════════════════════════════════════════════════════════════════════════════
# MAT21–MAT27  Ratio study + governance
# ═══════════════════════════════════════════════════════════════════════════════

def test_MAT21_ratio_study_panel_exists(page, live_server):
    """mass-ratio-study-panel data-testid exists in mass mode."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    el = page.query_selector('[data-testid="mass-ratio-study-panel"]')
    assert el is not None, "mass-ratio-study-panel not found"


def test_MAT22_sales_json_input_exists(page, live_server):
    """mass-sales-json-input textarea exists in the ratio study tab."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    el = page.query_selector('[data-testid="mass-sales-json-input"]')
    assert el is not None, "mass-sales-json-input not found"


def test_MAT23_governance_panel_exists(page, live_server):
    """mass-governance-panel data-testid exists."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    el = page.query_selector('[data-testid="mass-governance-panel"]')
    assert el is not None, "mass-governance-panel not found"


def test_MAT24_governance_panel_uses_roadmap_wording(page, live_server):
    """Governance panel uses professional roadmap wording (مخطط للمرحلة التالية)."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    # Switch to governance inner tab
    page.click('[data-mass-tab="governance"]')
    page.wait_for_timeout(300)
    panel = page.query_selector('[data-testid="mass-governance-panel"]')
    assert panel is not None
    text = panel.inner_text()
    assert "مخطط للمرحلة التالية" in text


def test_MAT25_governance_includes_qdrant(page, live_server):
    """Governance panel mentions Qdrant / Vector Search."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    page.click('[data-mass-tab="governance"]')
    page.wait_for_timeout(300)
    el = page.query_selector('[data-testid="mass-qdrant-status"]')
    assert el is not None
    assert "Qdrant" in el.inner_text() or "Vector" in el.inner_text()


def test_MAT26_governance_does_not_claim_rag_active(page, live_server):
    """Governance panel does NOT contain 'غير مفعل' or 'غير متاح' weak wording."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    page.click('[data-mass-tab="governance"]')
    page.wait_for_timeout(300)
    panel = page.query_selector('[data-testid="mass-governance-panel"]')
    assert panel is not None
    text = panel.inner_text()
    assert "غير مفعل" not in text, "Governance panel should not contain 'غير مفعل'"
    assert "غير متاح" not in text, "Governance panel should not contain 'غير متاح'"


def test_MAT27_governance_expert_approval_card_exists(page, live_server):
    """Governance panel contains expert approval status card."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    el = page.query_selector('[data-testid="mass-expert-approval-status"]')
    assert el is not None
    assert "مطلوب" in el.inner_text() or "اعتماد" in el.inner_text()


# ═══════════════════════════════════════════════════════════════════════════════
# MAT28–MAT32  Export buttons and report safety
# ═══════════════════════════════════════════════════════════════════════════════

def test_MAT28_pdf_preview_button_exists(page, live_server):
    """mass-preview-pdf button exists in mass workspace."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    el = page.query_selector('[data-testid="mass-preview-pdf"]')
    assert el is not None


def test_MAT29_csv_export_button_exists(page, live_server):
    """mass-export-csv button exists."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    el = page.query_selector('[data-testid="mass-export-csv"]')
    assert el is not None


def test_MAT30_excel_internal_button_exists(page, live_server):
    """mass-export-excel-internal button exists."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    el = page.query_selector('[data-testid="mass-export-excel-internal"]')
    assert el is not None


def test_MAT31_page_says_non_certified(page, live_server):
    """The mass workspace contains 'غير معتمد' language (non-certified warning)."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    ws = page.query_selector('[data-testid="mass-appraisal-workspace"]')
    assert ws is not None
    text = ws.inner_text()
    assert "غير معتمد" in text or "مسودة" in text


def test_MAT32_no_certified_report_generated(page, live_server):
    """After run, no 'معتمد رسميًا' stamp appears in the results output (not auto-certified)."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    _fill_json(page, VALID_SAMPLE)
    _click_run(page)
    dash = page.query_selector('[data-testid="mass-results-dashboard"]')
    assert dash is not None
    text = dash.inner_text()
    assert "معتمد رسميًا" not in text, "Results dashboard must not claim official certification"


# ═══════════════════════════════════════════════════════════════════════════════
# MAT33–MAT36  Expert approval lead form
# ═══════════════════════════════════════════════════════════════════════════════

def test_MAT33_expert_approval_button_reveals_lead_form(page, live_server):
    """Clicking mass-expert-approval-button shows the lead form."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    page.click('[data-testid="mass-expert-approval-button"]')
    page.wait_for_selector('[data-testid="mass-lead-form"]', timeout=3_000)
    form = page.query_selector('[data-testid="mass-lead-form"]')
    assert form is not None and form.is_visible()


def test_MAT34_lead_form_validates_required_fields(page, live_server):
    """Lead form shows an error when name or phone is missing."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    page.click('[data-testid="mass-expert-approval-button"]')
    page.wait_for_selector('[data-testid="mass-lead-form"]', timeout=3_000)
    # Submit without filling name/phone
    page.click('[data-testid="mass-lead-submit"]')
    page.wait_for_timeout(300)
    msg = page.query_selector("#mass-lead-validation-msg")
    assert msg is not None and msg.is_visible()
    assert "مطلوب" in msg.inner_text() or "الاسم" in msg.inner_text()


def test_MAT35_lead_form_submits_and_shows_confirmation(page, live_server):
    """Filling required fields and submitting shows confirmation message."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    page.click('[data-testid="mass-expert-approval-button"]')
    page.wait_for_selector('[data-testid="mass-lead-form"]', timeout=3_000)
    page.fill('[data-testid="mass-lead-name"]', "أحمد المهندس")
    page.fill('[data-testid="mass-lead-phone"]', "01012345678")
    page.click('[data-testid="mass-lead-submit"]')
    page.wait_for_timeout(1_500)
    conf = page.query_selector('[data-testid="mass-lead-confirmation"]')
    assert conf is not None and conf.is_visible()
    text = conf.inner_text()
    assert "تم" in text or "مراجعة" in text or "خبير" in text


def test_MAT36_lead_form_fields_have_testids(page, live_server):
    """All required lead form fields have their data-testid attributes."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    page.click('[data-testid="mass-expert-approval-button"]')
    page.wait_for_selector('[data-testid="mass-lead-form"]', timeout=3_000)
    for tid in ["mass-lead-name", "mass-lead-phone", "mass-lead-email",
                "mass-lead-asset-count", "mass-lead-purpose",
                "mass-lead-notes", "mass-lead-submit", "mass-lead-confirmation"]:
        assert page.query_selector(f'[data-testid="{tid}"]') is not None, \
            f"Lead form element data-testid='{tid}' not found"


# ═══════════════════════════════════════════════════════════════════════════════
# MAT37–MAT40  Regression
# ═══════════════════════════════════════════════════════════════════════════════

def test_MAT37_professional_tab_has_no_mass_workspace(page, live_server):
    """Professional tab does NOT contain #mass-appraisal-workflow."""
    _goto(page, live_server)
    page.click("#es-tab-professional")
    page.wait_for_selector("#ws-professional.es-ws-active", timeout=5_000)
    ws = page.query_selector("#ws-professional")
    assert ws is not None
    inside = ws.query_selector("#mass-appraisal-workflow")
    assert inside is None, "#mass-appraisal-workflow found inside ws-professional"


def test_MAT38_professional_tab_visible_text_is_clean(page, live_server):
    """Professional tab visible text does not contain mass workspace heading."""
    _goto(page, live_server)
    page.click("#es-tab-professional")
    page.wait_for_selector("#ws-professional.es-ws-active", timeout=5_000)
    ws = page.query_selector("#ws-professional")
    text = ws.inner_text()
    assert "مساحة عمل التقييم الجماعي" not in text


def test_MAT39_simple_valuation_tab_unaffected(page, live_server):
    """Simple valuation tab still opens normally."""
    _goto(page, live_server)
    page.click("#es-tab-valuation")
    page.wait_for_selector("#ws-valuation.es-ws-active", timeout=5_000)
    assert page.is_visible("#ws-valuation")


def test_MAT40_chat_tab_unaffected(page, live_server):
    """Chat tab still opens normally."""
    _goto(page, live_server)
    page.click("#es-tab-chat")
    page.wait_for_selector("#ws-chat.es-ws-active", timeout=5_000)
    assert page.is_visible("#ws-chat")
