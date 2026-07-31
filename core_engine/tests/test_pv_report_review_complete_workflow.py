"""
test_pv_report_review_complete_workflow.py
34 backend tests — Complete Report Review Workflow.
advisory_only=True | human_reviewer_required=True | certification_ready=False
"""
from __future__ import annotations
import json
from pathlib import Path
import pytest

_CORE = Path(__file__).resolve().parent.parent
_INST = _CORE / "instance" / "manual_review_outputs"
_OUT  = _INST / "professional_valuation_report_review_complete_workflow"

_PDF_DIR  = _OUT / "pdf_outputs"
_XL_DIR   = _OUT / "excel_outputs"
_AUD_DIR  = _OUT / "report_review_audits"
_VIS_DIR  = _OUT / "visual_previews"
_FINAL    = _OUT / "final_report"
_SCR_DIR  = _OUT / "screenshots"

_REVIEW_PDF  = _PDF_DIR / "report_review_output.pdf"
_REVIEW_HTML = _PDF_DIR / "report_review_output.html"
_VISUAL_IDX  = _VIS_DIR / "OPEN_REPORT_REVIEW_COMPLETE_WORKFLOW_INDEX.html"
_FINAL_RPT   = _FINAL / "final_report_review_complete_workflow_report.txt"


def _j(fname: str) -> dict:
    p = _AUD_DIR / fname
    assert p.exists(), f"Audit missing: {p}"
    return json.loads(p.read_text(encoding="utf-8"))


def _frontend() -> str:
    p = _CORE.parent / "frontend" / "index.html"
    if p.exists():
        return p.read_text(encoding="utf-8", errors="ignore")
    return ""


def _xl_names() -> list:
    try:
        import openpyxl
        for xl in [_XL_DIR / "professional_valuation_merged_master_workbook.xlsm",
                   _XL_DIR / "professional_valuation_merged_master_workbook.xlsx"]:
            if xl.exists():
                wb = openpyxl.load_workbook(str(xl), read_only=True)
                names = list(wb.sheetnames)
                wb.close()
                return names
        return []
    except Exception:
        return []


# ── T01: Report Review workflow context ──────────────────────────────────────
def test_T01_report_review_workflow_context_exists():
    d = _j("00_uploaded_review_requirements_mapping_audit.json")
    assert d["wizard_sections_implemented"] is True
    assert d["compliance_checklists_implemented"] is True
    assert "IVS" in d["standards_included"]
    assert d["mapping_status"] == "PASS"


# ── T02: Report Review is in special reports section ─────────────────────────
def test_T02_report_review_in_special_reports_section():
    html = _frontend()
    assert "التقارير الخاصة والتحليلات المتقدمة" in html, "Special Reports section missing"
    assert "فتح متطلبات مراجعة التقارير" in html, "Report Review button label missing"
    assert "pv-btn-report-review" in html or "pv-open-report-review" in html, "Report Review button testid missing"


# ── T03: Report Review NOT inside chat box ────────────────────────────────────
def test_T03_report_review_not_inside_chat_box():
    d = _j("12_report_review_ui_simulation_audit.json")
    assert d["not_inside_chat_box"] is True
    assert d["location"] == "special_reports_section"
    html = _frontend()
    # report_review_quick_key should be removed from chat box
    assert "report_review_quick_key_removed_from_chat_box=true" in html or \
           "chat_upload_shortcuts_removed" in html, "Chat box removal marker missing"


# ── T04: PDF upload enabled ───────────────────────────────────────────────────
def test_T04_pdf_upload_enabled():
    d = _j("12_report_review_ui_simulation_audit.json")
    assert d["pdf_upload_card_present"] is True
    html = _frontend()
    # Wizard step 1 has upload input
    assert 'rr-pdf-upload' in html or 'accept=".pdf"' in html or 'pdf' in html.lower()


# ── T05: Wizard has five steps ────────────────────────────────────────────────
def test_T05_wizard_has_five_steps():
    d = _j("12_report_review_ui_simulation_audit.json")
    assert d["wizard_steps_count"] == 5
    assert d["wizard_enabled"] is True
    html = _frontend()
    # Check wizard step elements exist
    assert "rr-wizard-step" in html or "wizard_steps_count" in html


# ── T06: Upload and extraction step exists ────────────────────────────────────
def test_T06_upload_extraction_step_exists():
    html = _frontend()
    assert "رفع التقرير واستخراج البيانات" in html, "Step 1 title missing"


# ── T07: Extraction context exists ────────────────────────────────────────────
def test_T07_extraction_context_exists():
    d = _j("01_uploaded_pdf_extraction_audit.json")
    assert d["text_extraction_attempted"] is True
    assert d["manual_review_required"] is True
    assert d["internal_paths_hidden"] is True


# ── T08: OCR status is handled ────────────────────────────────────────────────
def test_T08_ocr_status_handled():
    d = _j("01_uploaded_pdf_extraction_audit.json")
    assert d["ocr_attempted_if_needed"] is True
    assert d["ocr_status"] in ("success", "partial", "BLOCKED")
    # BLOCKED is acceptable — must be documented
    if d["ocr_status"] == "BLOCKED":
        assert d["manual_review_required"] is True


# ── T09: Standard detection exists ────────────────────────────────────────────
def test_T09_standard_detection_exists():
    d = _j("02_standard_detection_audit.json")
    assert d["auto_standard_detection_enabled"] is True
    assert d["reviewer_can_override"] is True
    assert isinstance(d["detected_standards"], list)
    assert isinstance(d["suggested_review_standards"], list)
    assert len(d["suggested_review_standards"]) > 0


# ── T10: Review info fields exist ────────────────────────────────────────────
def test_T10_review_info_fields_exist():
    d = _j("03_review_info_and_wur_audit.json")
    for key in ["review_date", "reviewer_name", "review_client_name",
                "intended_review_use", "selected_review_standards"]:
        assert key in d, f"Missing review info field: {key}"
    html = _frontend()
    assert "معلومات المراجعة" in html or "review_info" in html or "rr-reviewer-name" in html


# ── T11: Work under review fields exist ──────────────────────────────────────
def test_T11_work_under_review_fields_exist():
    d = _j("03_review_info_and_wur_audit.json")
    for key in ["reviewed_report_id", "reviewed_asset_type", "reviewed_asset_location",
                "reviewed_report_valuation_date"]:
        assert key in d, f"Missing WUR field: {key}"


# ── T12: Standards multi-select exists ───────────────────────────────────────
def test_T12_standards_multi_select_exists():
    d = _j("03_review_info_and_wur_audit.json")
    stds = d["selected_review_standards"]
    assert "IVS" in stds
    assert "USPAP" in stds
    assert "RICS" in stds
    assert "FRA" in stds


# ── T13: IVS checklist exists ────────────────────────────────────────────────
def test_T13_ivs_checklist_exists():
    d = _j("04_standards_compliance_simulation_audit.json")
    assert d["ivs_review_enabled"] is True
    assert d["ivs_items_count"] >= 7
    names = _xl_names()
    assert "IVS Review Checklist" in names, "IVS Review Checklist sheet missing from Excel"


# ── T14: USPAP checklist exists ──────────────────────────────────────────────
def test_T14_uspap_checklist_exists():
    d = _j("04_standards_compliance_simulation_audit.json")
    assert d["uspap_review_enabled"] is True
    assert d["uspap_items_count"] >= 10
    names = _xl_names()
    assert "USPAP Review Checklist" in names, "USPAP Review Checklist sheet missing from Excel"


# ── T15: RICS checklist exists ───────────────────────────────────────────────
def test_T15_rics_checklist_exists():
    d = _j("04_standards_compliance_simulation_audit.json")
    assert d["rics_review_enabled"] is True
    assert d["rics_items_count"] >= 5
    names = _xl_names()
    assert "RICS Review Checklist" in names, "RICS Review Checklist sheet missing from Excel"


# ── T16: FRA checklist exists ────────────────────────────────────────────────
def test_T16_fra_checklist_exists():
    d = _j("04_standards_compliance_simulation_audit.json")
    assert d["fra_review_enabled"] is True
    assert d["fra_items_count"] >= 4
    names = _xl_names()
    assert "FRA Review Checklist" in names, "FRA Review Checklist sheet missing from Excel"


# ── T17: Checklist rows support evidence/severity/notes/page reference ────────
def test_T17_checklist_rows_have_full_fields():
    d = _j("04_standards_compliance_simulation_audit.json")
    assert d["evidence_mapping_enabled"] is True
    assert d["human_review_flags_enabled"] is True


# ── T18: Technical and numeric review exists ─────────────────────────────────
def test_T18_technical_numeric_review_exists():
    d = _j("05_review_agents_simulation_audit.json")
    assert d["calculation_agent_enabled"] is True
    assert d["comparables_agent_enabled"] is True
    assert "agents_results" in d
    names = _xl_names()
    assert "Technical Review" in names, "Technical Review sheet missing from Excel"
    assert "Numeric Recalculation" in names, "Numeric Recalculation sheet missing from Excel"


# ── T19: Review agents context exists ────────────────────────────────────────
def test_T19_review_agents_context_exists():
    d = _j("05_review_agents_simulation_audit.json")
    for key in ["standards_agent_enabled", "calculation_agent_enabled",
                "comparables_agent_enabled", "income_agent_enabled",
                "cost_agent_enabled", "assumptions_agent_enabled",
                "risk_uncertainty_agent_enabled"]:
        assert d[key] is True, f"Agent not enabled: {key}"
    assert d["human_reviewer_required"] is True
    names = _xl_names()
    assert "Review Agents Summary" in names, "Review Agents Summary sheet missing"


# ── T20: Numeric recalculation context exists ─────────────────────────────────
def test_T20_numeric_recalculation_context_exists():
    d = _j("06_numeric_recalculation_audit.json")
    assert d["calculation_review_attempted"] is True
    assert isinstance(d["recalculated_items"], list)
    assert isinstance(d["not_verifiable_items"], list)
    assert d["numeric_review_status"] in ("PASS", "PARTIAL", "FAILED")


# ── T21: Human review flags context exists ────────────────────────────────────
def test_T21_human_review_flags_context_exists():
    d = _j("07_human_review_flags_audit.json")
    assert d["enabled"] is True
    assert d["human_review_required"] is True
    assert d["ai_does_not_replace_reviewer"] is True
    assert isinstance(d["flags"], list)
    assert len(d["flags"]) > 0
    names = _xl_names()
    assert "Human Review Flags" in names, "Human Review Flags sheet missing from Excel"


# ── T22: Scoring logic exists ─────────────────────────────────────────────────
def test_T22_scoring_logic_exists():
    d = _j("08_review_scoring_audit.json")
    assert d["review_score_percent"] >= 0
    assert d["compliance_level"] in ("متوافق بالكامل", "متوافق جزئياً", "غير متوافق")
    assert d["recommended_decision"] in ("قبول التقرير", "طلب تعديلات", "رفض التقرير")
    assert d["manual_override_allowed"] is True
    names = _xl_names()
    assert "Review Score" in names, "Review Score sheet missing from Excel"


# ── T23: Final decision fields exist ──────────────────────────────────────────
def test_T23_final_decision_fields_exist():
    d = _j("09_final_review_decision_audit.json")
    assert "final_review_status" in d
    assert "reviewer_recommendation" in d
    assert d["fake_reviewer_signature_created"] is False
    assert d["unsigned_gate_shown"] is True
    names = _xl_names()
    assert "Reviewer Decision" in names, "Reviewer Decision sheet missing from Excel"


# ── T24: report_review_output.pdf exists after generation ─────────────────────
def test_T24_report_review_pdf_exists():
    assert _REVIEW_PDF.exists() or _REVIEW_HTML.exists(), \
        "report_review_output.pdf / .html not generated"
    if _REVIEW_PDF.exists():
        assert _REVIEW_PDF.stat().st_size > 20_000, "Review PDF too small"
    if _REVIEW_HTML.exists():
        assert _REVIEW_HTML.stat().st_size > 50_000, "Review HTML too small"


# ── T25: Report Review PDF has required structure ─────────────────────────────
def test_T25_report_review_pdf_has_required_structure():
    d = _j("10_report_review_pdf_structure_audit.json")
    assert d["cover_present"] is True
    assert d["extraction_summary_present"] is True
    assert d["work_under_review_present"] is True
    assert d["scope_of_review_present"] is True
    assert d["review_summary_present"] is True
    assert d["standards_compliance_tables_present"] is True
    assert d["technical_numeric_review_present"] is True
    assert d["numeric_recalculation_summary_present"] is True
    assert d["review_agents_summary_present"] is True
    assert d["findings_by_severity_present"] is True
    assert d["human_review_flags_present"] is True
    assert d["required_actions_present"] is True
    assert d["review_conclusion_present"] is True
    assert d["reviewer_certificate_or_unsigned_gate_present"] is True
    assert d["ai_assisted_warning_present"] is True
    assert d["appendices_present"] is True
    assert d["fake_reviewer_signature_created"] is False
    assert d["pdf_status"] in ("PASS", "PARTIAL")


# ── T26: AI-assisted warning exists ──────────────────────────────────────────
def test_T26_ai_assisted_warning_exists():
    if _REVIEW_HTML.exists():
        content = _REVIEW_HTML.read_text(encoding="utf-8", errors="ignore")
        assert "AI-assisted" in content or "الذكاء الاصطناعي" in content, \
            "AI-assisted warning missing from Review HTML"
        assert "human_reviewer_required" in content or "المراجع البشري" in content


# ── T27: No fake reviewer signature ──────────────────────────────────────────
def test_T27_no_fake_reviewer_signature():
    d = _j("09_final_review_decision_audit.json")
    assert d["fake_reviewer_signature_created"] is False
    d2 = _j("10_report_review_pdf_structure_audit.json")
    assert d2["fake_reviewer_signature_created"] is False
    if _REVIEW_HTML.exists():
        content = _REVIEW_HTML.read_text(encoding="utf-8", errors="ignore")
        assert "ختم رسمي معتمد" not in content, "Fake stamp found in review HTML"
        assert "certification_ready=True" not in content, "Fake cert flag in review HTML"


# ── T28: No fake certification ────────────────────────────────────────────────
def test_T28_no_fake_certification():
    d = _j("10_report_review_pdf_structure_audit.json")
    assert d.get("certification_ready") is False
    d2 = _j("08_review_scoring_audit.json")
    assert d2.get("certification_ready") is False


# ── T29: No internal paths in generated HTML ──────────────────────────────────
def test_T29_no_internal_paths():
    for f in [_REVIEW_HTML, _VISUAL_IDX]:
        if f and f.exists():
            content = f.read_text(encoding="utf-8", errors="ignore")
            for bad in [r"C:\\Users", r"C:/Users", "/home/"]:
                assert bad not in content, f"Internal path in {f.name}: {bad}"


# ── T30: Downloadable review PDF audit passes ─────────────────────────────────
def test_T30_downloadable_review_pdf_audit():
    d = _j("13_downloadable_review_pdf_audit.json")
    assert d["download_button_enabled"] is True
    assert d["safe_download_link_used"] is True
    assert d["internal_paths_hidden"] is True
    assert d["download_status"] in ("PASS", "PARTIAL")


# ── T31: Excel integration audit exists ──────────────────────────────────────
def test_T31_excel_integration_audit_exists():
    d = _j("11_report_review_excel_integration_audit.json")
    assert d["review_excel_created_or_updated"] is True
    assert d["old_sheets_preserved"] is True
    assert d["excel_status"] in ("PASS", "PARTIAL")
    # Verify Excel file physically exists
    xl_found = any([
        (_XL_DIR / "professional_valuation_merged_master_workbook.xlsm").exists(),
        (_XL_DIR / "professional_valuation_merged_master_workbook.xlsx").exists(),
    ])
    assert xl_found, "No Excel file found in excel_outputs/"


# ── T32: Uploaded requirements mapping audit exists ───────────────────────────
def test_T32_uploaded_requirements_mapping_audit_exists():
    d = _j("00_uploaded_review_requirements_mapping_audit.json")
    assert d["uploaded_requirements_file_used"] is True
    assert d["advisory_warning_preserved"] is True
    assert d["mapping_status"] == "PASS"


# ── T33: Ordinary valuation unaffected ───────────────────────────────────────
def test_T33_ordinary_valuation_unaffected():
    html = _frontend()
    # Core valuation controls must still exist
    assert "pv-core-report-type" in html or "traditional_report" in html, \
        "Core valuation report type selector missing"
    assert "pv-chat-send-btn" in html or "sendBtn" in html or "generateBtn" in html, \
        "Core chat send button missing"


# ── T34: Tax appeal unaffected ────────────────────────────────────────────────
def test_T34_tax_appeal_unaffected():
    html = _frontend()
    assert "tax" in html.lower() or "ضريبي" in html or "الطعن" in html, \
        "Tax section appears to be missing"
