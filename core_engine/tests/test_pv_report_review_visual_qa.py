"""
Backend tests for Professional Valuation Report Review Visual QA.
19 tests covering folder structure, audit files, PDF, Excel, safety constraints.
"""

from __future__ import annotations
import json
import pathlib
import pytest

_ROOT = pathlib.Path(__file__).parent.parent
_QA   = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_report_review_visual_qa"
_SRC  = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_report_review_complete_workflow"

# ── folder structure ──────────────────────────────────────────────────────────

def test_Q01_visual_qa_folder_exists():
    assert _QA.exists(), f"Visual QA folder missing: {_QA}"

def test_Q02_screenshots_folder_exists():
    assert (_QA / "screenshots").exists()

def test_Q03_visual_index_exists():
    idx = _QA / "visual_previews" / "OPEN_REPORT_REVIEW_VISUAL_QA_INDEX.html"
    assert idx.exists(), f"Visual index missing: {idx}"
    content = idx.read_text(encoding="utf-8", errors="ignore")
    assert "مراجعة تقرير" in content
    assert "report_review_output.pdf" in content

# ── audit files ───────────────────────────────────────────────────────────────

def test_Q04_browser_entry_audit_exists():
    p = _QA / "report_review_audits" / "01_browser_entry_visual_audit.json"
    assert p.exists()
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d.get("wizard_steps_count") == 5
    assert d.get("not_inside_chat_box") is True

def test_Q05_upload_extraction_audit_exists():
    p = _QA / "report_review_audits" / "02_upload_extraction_visual_audit.json"
    assert p.exists()
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d.get("pdf_upload_control_visible") is True
    assert d.get("text_extraction_status_visible") is True

def test_Q06_review_info_audit_exists():
    p = _QA / "report_review_audits" / "03_review_info_visual_audit.json"
    assert p.exists()
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d.get("review_info_step_visible") is True
    assert d.get("arabic_input_supported") is True

def test_Q07_standards_audit_exists():
    p = _QA / "report_review_audits" / "04_standards_visual_audit.json"
    assert p.exists()
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d.get("ivs_checklist_visible") is True
    assert d.get("uspap_checklist_visible") is True
    assert d.get("rics_checklist_visible") is True
    assert d.get("fra_checklist_visible") is True

def test_Q08_technical_numeric_audit_exists():
    p = _QA / "report_review_audits" / "05_technical_numeric_visual_audit.json"
    assert p.exists()
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d.get("review_agents_panel_visible") is True
    assert d.get("human_review_flags_panel_visible") is True

def test_Q09_final_decision_audit_exists():
    p = _QA / "report_review_audits" / "06_final_decision_pdf_generation_visual_audit.json"
    assert p.exists()
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d.get("generate_pdf_button_visible") is True
    assert d.get("download_button_visible") is True
    assert d.get("fake_reviewer_signature_created") is False

def test_Q10_generated_pdf_visual_audit_exists():
    p = _QA / "report_review_audits" / "07_generated_pdf_visual_audit.json"
    assert p.exists()
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d.get("report_review_pdf_exists") is True
    assert d.get("fake_reviewer_signature_created") is False

# ── physical files ────────────────────────────────────────────────────────────

def test_Q11_report_review_output_pdf_exists():
    pdf = _QA / "pdf_outputs" / "report_review_output.pdf"
    assert pdf.exists(), "report_review_output.pdf is missing from QA pdf_outputs"

def test_Q12_report_review_output_pdf_nonempty():
    pdf = _QA / "pdf_outputs" / "report_review_output.pdf"
    if not pdf.exists():
        pytest.skip("PDF missing")
    assert pdf.stat().st_size > 10_000, f"PDF too small ({pdf.stat().st_size} bytes)"

def test_Q13_pdf_text_extract_exists():
    txt = _QA / "pdf_text_extracts" / "report_review_output_text.txt"
    assert txt.exists()
    content = txt.read_text(encoding="utf-8", errors="ignore")
    assert len(content) > 100, "Text extract is nearly empty"

def test_Q14_pdf_page_previews_exist():
    pp_dir = _QA / "visual_previews" / "report_review_pdf_pages"
    if not pp_dir.exists():
        pytest.skip("PDF page previews folder missing")
    pages = list(pp_dir.glob("*.html"))
    assert len(pages) >= 10, f"Expected >= 10 page previews, got {len(pages)}"

def test_Q15_excel_integration_audit_exists():
    p = _QA / "report_review_audits" / "08_excel_integration_visual_audit.json"
    assert p.exists()
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d.get("review_sheets_present") is True
    assert d.get("old_sheets_preserved") is True

# ── safety constraints ────────────────────────────────────────────────────────

def test_Q16_no_fake_reviewer_signature():
    """None of the QA audit files claim a fake reviewer signature was created."""
    for audit_file in (_QA / "report_review_audits").glob("*.json"):
        d = json.loads(audit_file.read_text(encoding="utf-8"))
        sig = d.get("fake_reviewer_signature_created", False)
        assert sig is False, f"{audit_file.name}: fake_reviewer_signature_created must be False"

def test_Q17_no_fake_certification():
    """No audit claims certification_ready=True."""
    for audit_file in (_QA / "report_review_audits").glob("*.json"):
        d = json.loads(audit_file.read_text(encoding="utf-8"))
        cert = d.get("certification_ready", False)
        assert cert is False, f"{audit_file.name}: certification_ready must be False"

def test_Q18_no_internal_paths_in_visual_index():
    idx = _QA / "visual_previews" / "OPEN_REPORT_REVIEW_VISUAL_QA_INDEX.html"
    if not idx.exists():
        pytest.skip("Visual index not found")
    content = idx.read_text(encoding="utf-8", errors="ignore")
    assert "C:\\Users" not in content, "Internal Windows path found in visual index"
    assert "C:/Users" not in content, "Internal Windows path found in visual index"
    assert "Lenovo" not in content, "Username in visual index"

def test_Q19_final_status_consistent_with_pdf():
    """If PDF is missing, final report must NOT claim PASS."""
    final = _QA / "final_report" / "final_report_review_visual_qa_report.txt"
    if not final.exists():
        pytest.skip("Final report missing")
    pdf_exists = (_QA / "pdf_outputs" / "report_review_output.pdf").exists()
    content = final.read_text(encoding="utf-8", errors="ignore")
    if not pdf_exists:
        assert "PASS" not in content.split("Visual QA status:")[1][:20] if "Visual QA status:" in content else True, \
            "Final report claims PASS but PDF is missing"
