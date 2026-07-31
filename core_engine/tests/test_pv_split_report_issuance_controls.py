# test_pv_split_report_issuance_controls.py
# Backend tests — Split Report Issuance Controls
# advisory_only=True | not_real_training=True | no_commit=True

import json
import pathlib
import sys
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

BASE  = pathlib.Path("core_engine/instance/manual_review_outputs/"
                     "professional_valuation_split_report_issuance_controls")
HTML  = pathlib.Path("frontend/index.html")

CORE_TYPES    = ["traditional_report", "detailed_report", "professional_report"]
SPECIAL_TYPES = ["report_review_output", "simulated_uploaded_report",
                 "hbu_analysis_report", "standards_compliance_report"]


def _ctx():
    from core_engine.professional_valuation_split_report_issuance_context import (
        get_split_report_issuance_controls_context,
    )
    return get_split_report_issuance_controls_context()


def _html():
    return HTML.read_text(encoding="utf-8", errors="replace")


# ── T01: Context module importable and returns dict ───────────────────────────
def test_T01_split_report_issuance_controls_context_exists():
    ctx = _ctx()
    assert isinstance(ctx, dict)
    assert len(ctx) > 0


# ── T02: split_controls_enabled = True ────────────────────────────────────────
def test_T02_split_controls_enabled():
    assert _ctx()["split_controls_enabled"] is True


# ── T03: core_report_control_enabled = True ───────────────────────────────────
def test_T03_core_report_control_enabled():
    assert _ctx()["core_report_control_enabled"] is True


# ── T04: Core report types exactly traditional/detailed/professional ──────────
def test_T04_core_report_types():
    ctx = _ctx()
    assert sorted(ctx["core_report_types"]) == sorted(CORE_TYPES)
    for t in SPECIAL_TYPES:
        assert t not in ctx["core_report_types"], f"Special type in core: {t}"


# ── T05: Core output formats user_pdf + admin_excel ───────────────────────────
def test_T05_core_output_formats():
    ctx = _ctx()
    assert "user_pdf"    in ctx["core_output_formats"]
    assert "admin_excel" in ctx["core_output_formats"]


# ── T06: Core control location = below_chat_box ───────────────────────────────
def test_T06_core_control_location_below_chat_box():
    assert _ctx()["core_control_location"] == "below_chat_box"


# ── T07: special_report_control_enabled = True ───────────────────────────────
def test_T07_special_report_control_enabled():
    assert _ctx()["special_report_control_enabled"] is True


# ── T08: Special report types exactly four ───────────────────────────────────
def test_T08_special_report_types():
    ctx = _ctx()
    assert sorted(ctx["special_report_types"]) == sorted(SPECIAL_TYPES)
    for t in CORE_TYPES:
        assert t not in ctx["special_report_types"], f"Core type in special: {t}"


# ── T09: Each special report has a dedicated requirement table ────────────────
def test_T09_each_special_report_has_dedicated_requirement_table():
    ctx = _ctx()
    assert ctx["special_reports_have_dedicated_requirement_tables"] is True
    for t in SPECIAL_TYPES:
        key = f"{t}_requirement_table"
        assert key in ctx, f"Missing requirement table key: {key}"
        tbl = ctx[key]
        assert isinstance(tbl.get("groups"), list) and len(tbl["groups"]) >= 3
        assert "output_key" in tbl


# ── T10: Legacy seven-report selector removed as primary ─────────────────────
def test_T10_legacy_seven_report_selector_removed_as_primary():
    assert _ctx()["legacy_seven_report_selector_removed_as_primary"] is True


# ── T11: Duplicate lower PDF/chat buttons removed ────────────────────────────
def test_T11_duplicate_lower_pdf_chat_buttons_removed():
    assert _ctx()["duplicate_lower_pdf_chat_buttons_removed"] is True


# ── T12: Generic special report chat uploads removed ─────────────────────────
def test_T12_generic_special_report_chat_uploads_removed():
    assert _ctx()["generic_chat_upload_for_special_reports_removed"] is True


# ── T13: Backend keys preserved ──────────────────────────────────────────────
def test_T13_backend_keys_preserved():
    ctx = _ctx()
    assert ctx["backend_keys_preserved"] is True
    html = _html()
    for key in CORE_TYPES + SPECIAL_TYPES:
        assert key in html, f"Backend key missing from HTML: {key}"


# ── T14: Legacy aliases preserved ────────────────────────────────────────────
def test_T14_legacy_aliases_preserved():
    assert _ctx()["legacy_aliases_preserved"] is True


# ── T15: No internal paths ────────────────────────────────────────────────────
def test_T15_no_internal_paths():
    ctx = _ctx()
    assert ctx["no_internal_paths"] is True
    html = _html()
    for pat in ["C:\\Users\\Lenovo", "AppData\\Local", "__file__"]:
        assert pat not in html, f"Internal path in HTML: {pat}"


# ── T16: Ordinary valuation unaffected ───────────────────────────────────────
def test_T16_ordinary_valuation_unaffected():
    assert _ctx()["ordinary_valuation_unaffected"] is True
    html = _html()
    # Section 2 requirement tables must still exist
    assert "pro-val-section-report-type" in html or "pvr-generic-requirements" in html


# ── T17: Tax appeal unaffected ───────────────────────────────────────────────
def test_T17_tax_appeal_unaffected():
    assert _ctx()["tax_appeal_unaffected"] is True
    html = _html()
    assert "tax" in html.lower()


# ── T18: Core report issuance testid present in HTML ────────────────────────
def test_T18_core_report_issuance_testid_in_html():
    html = _html()
    assert 'pv-core-valuation-report-issuance' in html
    assert 'pv-core-report-type-chips'         in html


# ── T19: Core output buttons in HTML ─────────────────────────────────────────
def test_T19_core_output_buttons_in_html():
    html = _html()
    assert 'pv-core-generate-user-pdf'   in html
    assert 'pv-core-generate-admin-excel' in html
    assert 'إصدار PDF للمستخدم'         in html
    assert 'إصدار شيت Excel للأدمن'     in html


# ── T20: Special workflow buttons in HTML ────────────────────────────────────
def test_T20_special_workflow_buttons_in_html():
    html = _html()
    assert 'pv-open-report-review-table' in html
    assert 'pv-open-simulation-table'    in html
    assert 'pv-open-hbu-table'           in html
    assert 'pv-open-standards-table'     in html
    # Labels updated by REPORTING_UI_DUPLICATION_AND_CHAT_LAYOUT_MERGE
    assert 'مراجعة التقرير المرفوع'             in html
    assert 'رفع تقرير للمراجعة والتحليل'        in html
    assert 'فتح متطلبات أعلى وأفضل استخدام'    in html
    assert 'فتح متطلبات امتثال المعايير'        in html


# ── T21: Each special panel testid present in HTML ───────────────────────────
def test_T21_each_special_panel_testid_in_html():
    html = _html()
    for t in SPECIAL_TYPES:
        testid = f"pv-special-req-panel-{t}"
        assert testid in html, f"Panel testid missing: {testid}"


# ── T22: Four special panels are distinct (different IDs/headings) ────────────
def test_T22_four_special_panels_distinct():
    html = _html()
    # Panel headings updated in REPORTING_UI_DUPLICATION_AND_CHAT_LAYOUT_MERGE
    titles = [
        'مراجعة تقرير تقييم',                        # report_review_output panel header
        'محاكاة تقرير مرفوع',                         # simulated_uploaded_report panel header
        'متطلبات تحليل أعلى وأفضل استخدام',           # hbu panel data-panel-title
        'تقرير الامتثال للمعايير المهنية',             # standards panel header
    ]
    for title in titles:
        assert title in html, f"Panel title missing: {title}"


# ── T23: Legacy select hidden (not primary visible control) ──────────────────
def test_T23_legacy_select_hidden_not_primary():
    html = _html()
    assert 'pv-legacy-seven-report-selector-hidden' in html
    # The hidden wrapper must appear before the new core area
    assert html.index('pv-legacy-seven-report-selector-hidden') < html.index('pv-core-valuation-report-issuance')


# ── T24: HBU four tests in requirement table ─────────────────────────────────
def test_T24_hbu_four_tests_in_requirement_table():
    ctx = _ctx()
    hbu = ctx["hbu_analysis_report_requirement_table"]
    four = hbu["hbu_four_tests"]
    assert "physically_possible"  in four
    assert "legally_permissible"  in four
    assert "financially_feasible" in four
    assert "maximally_productive" in four
    assert hbu["is_valuation_report"] is False


# ── T25: Standards compliance has no valuation conclusion ────────────────────
def test_T25_standards_compliance_no_valuation_conclusion():
    ctx = _ctx()
    sc = ctx["standards_compliance_report_requirement_table"]
    assert sc["valuation_conclusion_included"] is False
    assert sc["advisory_compliance_only"] is True


# ── T26: Report review has completeness checklist, no new valuation ───────────
def test_T26_report_review_completeness_no_new_valuation():
    ctx = _ctx()
    rr = ctx["report_review_output_requirement_table"]
    assert rr["completeness_checklist"] is True
    assert rr["new_valuation_conclusion"] is False
    assert rr["risk_flags"] is True


# ── T27: Simulation no fake upload claim ─────────────────────────────────────
def test_T27_simulation_no_fake_upload():
    ctx = _ctx()
    sim = ctx["simulated_uploaded_report_requirement_table"]
    assert sim["real_report_uploaded"] is False
    assert sim["fake_uploaded_report_claim"] is False


# ── T28: Advisory / safety flags set ─────────────────────────────────────────
def test_T28_advisory_safety_flags():
    ctx = _ctx()
    assert ctx["advisory_only"] is True
    assert ctx["not_real_training"] is True
    assert ctx["preservation_pass"] is True


# ── T29: pvSyncSplitReportIssuanceContext referenced in HTML ─────────────────
def test_T29_js_functions_in_html():
    html = _html()
    for fn in ['pvSelectCoreValuationReportType', 'pvGenerateCoreValuationUserPdf',
               'pvGenerateCoreValuationAdminExcel', 'pvOpenSpecialReportRequirementsTable',
               'pvSyncSplitReportIssuanceContext', 'pvIssueSpecialReportPdf']:
        assert fn in html, f"JS function missing from HTML: {fn}"


# ── T30: QA audit folder and key files exist ─────────────────────────────────
@pytest.mark.skipif(
    not BASE.exists(),
    reason="Manual QA audit artifacts are not tracked in CI",
)
def test_T30_qa_output_folder_exists():
    assert BASE.exists(), f"QA folder missing: {BASE}"
    for fname in [
        "00_split_report_issuance_index.json",
        "02_core_report_control_audit.json",
        "03_special_report_workflow_audit.json",
        "04_report_review_requirements_table_audit.json",
        "05_simulated_report_requirements_table_audit.json",
        "06_hbu_requirements_table_audit.json",
        "07_standards_compliance_requirements_table_audit.json",
        "08_legacy_selector_removal_audit.json",
        "09_unified_context_audit.json",
    ]:
        assert (BASE / fname).exists(), f"QA file missing: {fname}"
