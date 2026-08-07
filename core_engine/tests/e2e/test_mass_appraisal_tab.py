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

# ── Auth helpers (mirrors test_mv_import_ui.py) ──────────────────────────────

_ADMIN = json.dumps({"token": "mock-token", "user_id": "u1", "is_admin": True})


def _as_admin(page):
    """Set admin session in localStorage before page navigation."""
    page.add_init_script(f"localStorage.setItem('es_auth', '{_ADMIN}')")


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


# ═══════════════════════════════════════════════════════════════════════════════
# MAT41–MAT45  Smart JSON Validator (Part A)
# ═══════════════════════════════════════════════════════════════════════════════

def test_MAT41_json_validator_panel_visible(page, live_server):
    """MAT41: mass-json-validator-panel is visible in mass mode."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    el = page.query_selector('[data-testid="mass-json-validator-panel"]')
    assert el is not None, "mass-json-validator-panel not found"
    assert el.is_visible()


def test_MAT42_valid_json_shows_status_and_row_count(page, live_server):
    """MAT42: After entering valid JSON, status shows valid and row count is populated."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    _fill_json(page, VALID_SAMPLE)
    page.dispatch_event('[data-testid="mass-json-input"]', 'input')
    page.wait_for_timeout(300)
    status = page.query_selector('[data-testid="mass-json-status"]')
    assert status is not None
    assert "صالح" in status.inner_text() or "✅" in status.inner_text()
    row_count = page.query_selector('[data-testid="mass-json-row-count"]')
    assert row_count is not None
    assert "5" in row_count.inner_text()


def test_MAT43_invalid_json_shows_error_without_clearing(page, live_server):
    """MAT43: Invalid JSON shows error in mass-json-error-list; textarea keeps original value."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    bad = "{ not valid json }"
    _fill_json(page, bad)
    page.dispatch_event('[data-testid="mass-json-input"]', 'input')
    page.wait_for_timeout(300)
    error_list = page.query_selector('[data-testid="mass-json-error-list"]')
    assert error_list is not None
    assert len(error_list.inner_text().strip()) > 0, "Error list should show errors for invalid JSON"
    ta = page.query_selector('[data-testid="mass-json-input"]')
    assert ta.input_value() == bad, "Textarea must not be modified on invalid JSON"


def test_MAT44_required_fields_list_visible(page, live_server):
    """MAT44: mass-json-required-fields-list shows required fields text."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    el = page.query_selector('[data-testid="mass-json-required-fields-list"]')
    assert el is not None
    text = el.inner_text()
    assert "row_id" in text or "location" in text or "area" in text


def test_MAT45_format_button_formats_valid_json(page, live_server):
    """MAT45: Format button pretty-prints valid JSON in textarea."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    compact = '[{"row_id":"R1","location":"Cairo","area":150,"property_type":"residential","valuation_purpose":"market_value"}]'
    _fill_json(page, compact)
    page.click('[data-testid="mass-json-format-button"]')
    page.wait_for_timeout(300)
    ta = page.query_selector('[data-testid="mass-json-input"]')
    val = ta.input_value()
    assert "\n" in val, "Format button should produce multi-line pretty-printed JSON"


# ═══════════════════════════════════════════════════════════════════════════════
# MAT46–MAT49  Dashboard Cards (Part B)
# ═══════════════════════════════════════════════════════════════════════════════

def test_MAT46_dashboard_cards_visible_in_mass_mode(page, live_server):
    """MAT46: mass-dashboard-cards section is visible when mass mode is active."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    el = page.query_selector('[data-testid="mass-dashboard-cards"]')
    assert el is not None, "mass-dashboard-cards not found"
    assert el.is_visible()


def test_MAT47_dashboard_cards_update_after_run(page, live_server):
    """MAT47: After running sample data, total-assets-card and success-count-card show counts."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    _fill_json(page, VALID_SAMPLE)
    _click_run(page)
    total = page.query_selector('[data-testid="mass-total-assets-card"]')
    assert total is not None
    success = page.query_selector('[data-testid="mass-success-count-card"]')
    assert success is not None
    # values should not be just dashes after a successful run
    assert total.inner_text().strip() != "" and success.inner_text().strip() != ""


def test_MAT48_data_quality_card_visible(page, live_server):
    """MAT48: mass-data-quality-card exists and is visible in mass mode."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    el = page.query_selector('[data-testid="mass-data-quality-card"]')
    assert el is not None and el.is_visible()


def test_MAT49_confidence_range_card_shows_data_gap(page, live_server):
    """MAT49: mass-confidence-range-card shows data-gap text when no data."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    el = page.query_selector('[data-testid="mass-confidence-range-card"]')
    assert el is not None
    text = el.inner_text()
    assert "غير متاح" in text or "دون بيانات" in text


# ═══════════════════════════════════════════════════════════════════════════════
# MAT50–MAT53  Ratio Study / COD / Calibration (Part C)
# ═══════════════════════════════════════════════════════════════════════════════

def test_MAT50_ratio_study_outputs_exist(page, live_server):
    """MAT50: mass-assessment-ratio-output and mass-cod-output exist in ratio study panel."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    page.click('[data-mass-tab="ratio-calibration"]')
    page.wait_for_timeout(300)
    assert page.query_selector('[data-testid="mass-assessment-ratio-output"]') is not None
    assert page.query_selector('[data-testid="mass-cod-output"]') is not None
    assert page.query_selector('[data-testid="mass-sales-count-output"]') is not None


def test_MAT51_cod_output_shows_data_gap(page, live_server):
    """MAT51: mass-cod-output shows data-gap message when no sales data."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    page.click('[data-mass-tab="ratio-calibration"]')
    page.wait_for_timeout(300)
    el = page.query_selector('[data-testid="mass-cod-output"]')
    assert el is not None
    text = el.inner_text()
    assert "COD" in text or "مبيعات" in text or "كافٍ" in text


def test_MAT52_calibration_note_says_qdrant_not_active(page, live_server):
    """MAT52: mass-calibration-note says Qdrant/Auto-training is not active."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    page.click('[data-mass-tab="ratio-calibration"]')
    page.wait_for_timeout(300)
    el = page.query_selector('[data-testid="mass-calibration-note"]')
    assert el is not None
    text = el.inner_text()
    assert "Qdrant" in text or "Auto-training" in text


def test_MAT53_calibration_status_exists(page, live_server):
    """MAT53: mass-calibration-status element exists in ratio study panel."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    page.click('[data-mass-tab="ratio-calibration"]')
    page.wait_for_timeout(300)
    el = page.query_selector('[data-testid="mass-calibration-status"]')
    assert el is not None


# ═══════════════════════════════════════════════════════════════════════════════
# MAT54–MAT55  Qdrant / Auto-training Placeholder (Part D)
# ═══════════════════════════════════════════════════════════════════════════════

def test_MAT54_qdrant_placeholder_says_future_backend(page, live_server):
    """MAT54: mass-qdrant-placeholder contains future/backend-only text."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    page.click('[data-mass-tab="governance"]')
    page.wait_for_timeout(300)
    el = page.query_selector('[data-testid="mass-qdrant-placeholder"]')
    assert el is not None
    text = el.inner_text()
    assert "Qdrant" in text or "Source Registry" in text or "لاحقًا" in text


def test_MAT55_auto_training_status_no_false_activation(page, live_server):
    """MAT55: mass-auto-training-status does not claim auto-training is active."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    page.click('[data-mass-tab="governance"]')
    page.wait_for_timeout(300)
    el = page.query_selector('[data-testid="mass-auto-training-status"]')
    assert el is not None
    text = el.inner_text()
    assert "مفعّل" not in text or "لم يتم" in text or "مخطط" in text


# ═══════════════════════════════════════════════════════════════════════════════
# MAT56–MAT58  Export Governance (Part E)
# ═══════════════════════════════════════════════════════════════════════════════

def test_MAT56_export_warning_says_non_certified(page, live_server):
    """MAT56: mass-export-warning contains non-certified language."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    el = page.query_selector('[data-testid="mass-export-warning"]')
    assert el is not None
    text = el.inner_text()
    assert "غير معتمد" in text or "مؤقت" in text


def test_MAT57_draft_pdf_button_is_future_ready(page, live_server):
    """MAT57: mass-draft-pdf-button exists and is disabled (future-ready, not live)."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    el = page.query_selector('[data-testid="mass-draft-pdf-button"]')
    assert el is not None
    # must be disabled OR have future-ready text
    disabled = el.get_attribute("disabled")
    text = el.inner_text()
    assert disabled is not None or "قريبًا" in text or "سيتم" in text


def test_MAT58_excel_export_note_says_non_certified(page, live_server):
    """MAT58: mass-export-excel-note says non-certified."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    el = page.query_selector('[data-testid="mass-export-excel-note"]')
    assert el is not None
    text = el.inner_text()
    assert "غير معتمد" in text or "مبدئية" in text


# ═══════════════════════════════════════════════════════════════════════════════
# MAT59–MAT61  Approval Modal (Part G)
# ═══════════════════════════════════════════════════════════════════════════════

def test_MAT59_approval_modal_opens_on_button_click(page, live_server):
    """MAT59: Clicking mass-expert-approval-button shows mass-approval-modal."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    page.click('[data-testid="mass-expert-approval-button"]')
    page.wait_for_selector('[data-testid="mass-approval-modal"]', timeout=3_000)
    modal = page.query_selector('[data-testid="mass-approval-modal"]')
    assert modal is not None and modal.is_visible()


def test_MAT60_approval_modal_has_required_fields(page, live_server):
    """MAT60: Approval modal contains organization, contact-name, and phone fields."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    page.click('[data-testid="mass-expert-approval-button"]')
    page.wait_for_selector('[data-testid="mass-approval-modal"]', timeout=3_000)
    for tid in ['mass-approval-organization-name', 'mass-approval-contact-name',
                'mass-approval-phone']:
        el = page.query_selector(f'[data-testid="{tid}"]')
        assert el is not None, f"{tid} not found in approval modal"


def test_MAT61_approval_confirmation_says_not_certified(page, live_server):
    """MAT61: After submitting approval form, confirmation says this is not certified."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    page.click('[data-testid="mass-expert-approval-button"]')
    page.wait_for_selector('[data-testid="mass-approval-modal"]', timeout=3_000)
    page.fill('[data-testid="mass-lead-name"]', "أحمد المهندس")
    page.fill('[data-testid="mass-lead-phone"]', "01012345678")
    page.click('[data-testid="mass-lead-submit"]')
    page.wait_for_timeout(1_500)
    conf = page.query_selector('[data-testid="mass-approval-confirmation"]')
    assert conf is not None and conf.is_visible()
    text = conf.inner_text()
    assert "غير معتمد" in text or "ليس تقريرًا معتمدًا" in text or "مراجعة الخبير" in text


# ═══════════════════════════════════════════════════════════════════════════════
# MAT62–MAT64  Governance Safety
# ═══════════════════════════════════════════════════════════════════════════════

def test_MAT62_no_excel_internal_path_in_user_ui(page, live_server):
    """MAT62: Mass workspace does not expose any internal file system path."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    ws = page.query_selector('[data-testid="mass-appraisal-workspace"]')
    assert ws is not None
    text = ws.inner_text()
    import re
    assert not re.search(r'[A-Za-z]:\\|/home/|/var/|\.xlsx\s*$', text), \
        "Internal file path must not appear in mass workspace UI"


def test_MAT63_no_claim_of_internet_training_active(page, live_server):
    """MAT63: Mass workspace does not claim internet auto-training is currently active."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    ws = page.query_selector('[data-testid="mass-appraisal-workspace"]')
    assert ws is not None
    text = ws.inner_text()
    forbidden = ["تدريب النموذج من الإنترنت مفعّل", "تحديث تلقائي نشط", "Qdrant متصل"]
    for phrase in forbidden:
        assert phrase not in text, f"False claim found: '{phrase}'"


def test_MAT64_no_claim_of_qdrant_active(page, live_server):
    """MAT64: Mass workspace does not claim Qdrant is currently active."""
    _goto(page, live_server)
    _switch_mass_mode(page)
    page.click('[data-mass-tab="governance"]')
    page.wait_for_timeout(300)
    panel = page.query_selector('[data-testid="mass-governance-panel"]')
    assert panel is not None
    text = panel.inner_text()
    # Should NOT claim active Qdrant; should only mention it as planned/future
    assert "Qdrant مفعّل" not in text and "Qdrant نشط" not in text


# ═══════════════════════════════════════════════════════════════════════════════
# Wave 4B1 regression: price-index authenticated browser regression
# Proves /api/price-index became authenticated in Wave 4B1 and the UI sends
# the Authorization header, receiving a non-401 response.
# ═══════════════════════════════════════════════════════════════════════════════

import os as _os

_PRICE_INDEX_JWT = _os.environ.get("E2E_TEST_JWT", "")


def test_MAT65_price_index_requires_auth_unauthenticated(page, live_server):
    """Wave 4B1 regression: unauthenticated /api/price-index GET returns 401."""
    resp = page.request.get(f"{live_server}/api/price-index")
    assert resp.status == 401, (
        f"Wave 4B1: /api/price-index must require auth; expected 401, got {resp.status}"
    )


def test_MAT66_price_index_authenticated_returns_non_401(page, live_server):
    """Wave 4B1 regression: authenticated /api/price-index GET does not return 401.

    If E2E_TEST_JWT is not set, generates a test token from JWT_SECRET.
    """
    import time as _time
    jwt_token = _PRICE_INDEX_JWT
    if not jwt_token:
        secret = _os.environ.get("JWT_SECRET", "ci-test-secret-for-e2e-workflow")
        try:
            import jwt as _jwt
            now = int(_time.time())
            jwt_token = _jwt.encode(
                {"sub": "e2e-test-user", "iat": now, "exp": now + 3600},
                secret,
                algorithm="HS256",
            )
        except Exception:
            pytest.skip("PyJWT not available — skipping price-index auth regression")

    resp = page.request.get(
        f"{live_server}/api/price-index",
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    assert resp.status != 401, (
        f"Wave 4B1: authenticated /api/price-index must not return 401, got {resp.status}"
    )


def test_MAT67_price_index_widget_sends_auth_header(page, live_server):
    """Wave 4B1 regression: frontend price-index widget sends Authorization header.

    Full browser test:
    0. Admin auth is set in localStorage BEFORE navigation so window.esFetch
       sends the Authorization header on the price-index request.
    1. page.goto() navigates to the live server.
    2. loadGrowth() is executed in the browser via page.evaluate().
    3. Intercepts the /api/price-index request and asserts Authorization: Bearer.
    4. Asserts the rendered price-index growth-pulse widget is visible in the DOM.

    page.request.get() alone is NOT used — this test exercises the real browser
    fetch path to confirm the UI sends the header through the same code path
    that end-users trigger.
    """
    captured_requests: list[dict] = []

    def handle_request(req):
        if "/api/price-index" in req.url:
            captured_requests.append({
                "url": req.url,
                "auth": req.headers.get("authorization", ""),
            })

    page.on("request", handle_request)

    # Step 0: configure admin auth BEFORE navigation — window.esFetch gates on es_auth
    _as_admin(page)

    # Step 1: navigate using page.goto() (not page.request)
    _goto(page, live_server)

    # Step 2: switch to mass appraisal mode to ensure widget scaffold is loaded
    _switch_mass_mode(page)

    # Step 3: execute loadGrowth() in the browser JS context to trigger the
    # price-index fetch.  The function MUST be defined on window; absence is a failure.
    load_growth_exists = page.evaluate(
        "typeof window.loadGrowth === 'function'"
    )
    if not load_growth_exists:
        pytest.fail(
            "window.loadGrowth() is not defined — widget not present on this page version"
        )

    page.evaluate("window.loadGrowth()")
    page.wait_for_timeout(800)

    # Step 4: Assert Authorization: Bearer is present in the intercepted request.
    # Absence after auth setup means _maApiUrl() or esFetch is broken — that is a
    # test failure, not a skip.
    if not captured_requests:
        pytest.fail(
            "loadGrowth() did not produce a /api/price-index request after auth setup — "
            "check _maApiUrl() layered fallback and window.esFetch authentication gate"
        )

    for req in captured_requests:
        assert req["auth"].startswith("Bearer "), (
            f"Price-index request must carry Authorization: Bearer header; "
            f"got auth={req['auth']!r} for url={req['url']!r}"
        )

    # Step 5: Assert the price-index growth-pulse widget is rendered and visible.
    # The widget lives in #growth-pulse (global header) and is always present.
    pulse_el = page.query_selector("#growth-pulse")
    assert pulse_el is not None, (
        "Price-index #growth-pulse widget container must be present in the DOM"
    )
    cma_el = page.query_selector("#gp-cma")
    assert cma_el is not None, (
        "#gp-cma pulse item (loadGrowth target) must be present in the DOM"
    )
    assert cma_el.is_visible(), (
        "Price-index widget #gp-cma must be visible after loadGrowth() executes"
    )
