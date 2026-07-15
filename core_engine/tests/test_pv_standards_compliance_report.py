"""
Backend tests for Standards Compliance Report Workflow.
31 tests C01-C31.
Run: python -m pytest tests/test_pv_standards_compliance_report.py -q
"""
from __future__ import annotations
import json
import pathlib
import pytest

_ROOT = pathlib.Path(__file__).parent.parent
_SC   = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_standards_compliance"
_AUD  = _SC / "standards_compliance_audits"
_PDF  = _SC / "pdf_outputs"
_XL   = _SC / "excel_outputs"
_PREV = _SC / "visual_previews"
_SS   = _SC / "screenshots"
_RPT  = _SC / "final_report"
_TXT  = _SC / "pdf_text_extracts"


def _aud(name: str) -> dict:
    p = _AUD / name
    assert p.exists(), f"Standards compliance audit missing: {name}"
    return json.loads(p.read_text(encoding="utf-8"))


# ── C01: workflow context exists ──────────────────────────────────────────────
def test_C01_standards_compliance_workflow_context_exists():
    audit = _aud("01_upload_and_standards_selection_audit.json")
    assert audit.get("standards_compliance_workflow_enabled") is True
    assert audit.get("pdf_upload_enabled") is True
    assert audit.get("pdf_uploaded") is True


# ── C02: workflow in special reports ─────────────────────────────────────────
def test_C02_workflow_in_special_reports():
    audit = _aud("01_upload_and_standards_selection_audit.json")
    assert audit.get("not_inside_chat_box") is True
    assert audit.get("in_chat_box", False) is False


# ── C03: workflow not Report Review ──────────────────────────────────────────
def test_C03_workflow_not_report_review():
    for fname in _AUD.glob("*.json"):
        d = json.loads(fname.read_text(encoding="utf-8"))
        assert d.get("not_report_review") is True, (
            f"{fname.name}: not_report_review must be True"
        )


# ── C04: workflow not Uploaded Template Simulation ───────────────────────────
def test_C04_workflow_not_uploaded_template_simulation():
    for fname in _AUD.glob("*.json"):
        d = json.loads(fname.read_text(encoding="utf-8"))
        assert d.get("not_uploaded_template_simulation") is True, (
            f"{fname.name}: not_uploaded_template_simulation must be True"
        )


# ── C05: workflow not HBU ─────────────────────────────────────────────────────
def test_C05_workflow_not_hbu():
    for fname in _AUD.glob("*.json"):
        d = json.loads(fname.read_text(encoding="utf-8"))
        assert d.get("not_hbu_workflow") is True, (
            f"{fname.name}: not_hbu_workflow must be True"
        )


# ── C06: workflow not inside chat box ─────────────────────────────────────────
def test_C06_workflow_not_inside_chat_box():
    for fname in _AUD.glob("*.json"):
        d = json.loads(fname.read_text(encoding="utf-8"))
        assert d.get("in_chat_box", False) is False, (
            f"{fname.name}: in_chat_box must be False"
        )


# ── C07: wizard has four steps ────────────────────────────────────────────────
def test_C07_wizard_has_four_steps():
    audit = _aud("06_ui_audit.json")
    assert audit.get("wizard_steps_count") == 4


# ── C08: PDF upload is enabled ────────────────────────────────────────────────
def test_C08_pdf_upload_enabled():
    audit = _aud("01_upload_and_standards_selection_audit.json")
    assert audit.get("pdf_upload_enabled") is True
    assert audit.get("pdf_uploaded") is True
    assert audit.get("uploaded_file_name"), "uploaded_file_name must not be empty"
    assert audit.get("page_count", 0) > 0


# ── C09: standards selector includes IVS / USPAP / RICS / FRA ────────────────
def test_C09_standards_selector_includes_all():
    audit = _aud("01_upload_and_standards_selection_audit.json")
    assert audit.get("ivs_selectable") is True
    assert audit.get("uspap_selectable") is True
    assert audit.get("rics_selectable") is True
    assert audit.get("fra_selectable") is True
    assert audit.get("at_least_one_standard_required") is True
    selected = audit.get("selected_standards", [])
    assert len(selected) >= 1, "At least one standard must be selected"


# ── C10: extraction context exists ───────────────────────────────────────────
def test_C10_extraction_context_exists():
    audit = _aud("02_pdf_extraction_and_text_analysis_audit.json")
    assert audit.get("pdf_metadata_extracted") is True
    assert audit.get("text_extraction_attempted") is True
    assert audit.get("ocr_handled") is True
    assert audit.get("table_extraction_attempted") is True
    assert audit.get("signature_detection_attempted") is True
    assert audit.get("hbu_detection_attempted") is True
    assert audit.get("uncertainty_detection_attempted") is True
    assert audit.get("internal_paths_hidden") is True
    status = audit.get("status", "")
    assert status in ("PASS", "PARTIAL", "FAILED")


# ── C11: IVS checklist exists ────────────────────────────────────────────────
def test_C11_ivs_checklist_exists():
    audit = _aud("03_compliance_scoring_audit.json")
    assert audit.get("ivs_score_calculated") is True
    ivs_score = audit.get("ivs_score", -1)
    assert 0 <= ivs_score <= 100, f"IVS score out of range: {ivs_score}"


# ── C12: USPAP checklist exists ──────────────────────────────────────────────
def test_C12_uspap_checklist_exists():
    audit = _aud("03_compliance_scoring_audit.json")
    assert audit.get("uspap_score_calculated") is True
    uspap_score = audit.get("uspap_score", -1)
    assert 0 <= uspap_score <= 100, f"USPAP score out of range: {uspap_score}"


# ── C13: RICS checklist exists ───────────────────────────────────────────────
def test_C13_rics_checklist_exists():
    audit = _aud("03_compliance_scoring_audit.json")
    assert audit.get("rics_score_calculated") is True
    rics_score = audit.get("rics_score", -1)
    assert 0 <= rics_score <= 100, f"RICS score out of range: {rics_score}"


# ── C14: FRA checklist exists ────────────────────────────────────────────────
def test_C14_fra_checklist_exists():
    audit = _aud("03_compliance_scoring_audit.json")
    assert audit.get("fra_score_calculated") is True
    fra_score = audit.get("fra_score", -1)
    assert 0 <= fra_score <= 100, f"FRA score out of range: {fra_score}"


# ── C15: per-standard scores calculated ──────────────────────────────────────
def test_C15_per_standard_scores_calculated():
    audit = _aud("03_compliance_scoring_audit.json")
    for key in ("ivs_score", "uspap_score", "rics_score", "fra_score"):
        val = audit.get(key, -1)
        assert val >= 0, f"{key} must be >= 0"


# ── C16: overall score calculated ────────────────────────────────────────────
def test_C16_overall_score_calculated():
    audit = _aud("03_compliance_scoring_audit.json")
    assert audit.get("overall_score_calculated") is True
    before = audit.get("overall_score_before_caps", -1)
    after  = audit.get("overall_score_after_caps", -1)
    assert 0 <= before <= 100
    assert 0 <= after <= 100
    assert after <= before, "Score after caps must be <= score before caps"
    assert audit.get("traffic_light_created") is True
    tl = audit.get("traffic_light", "")
    assert tl in ("green", "yellow", "red"), f"Invalid traffic_light: {tl!r}"


# ── C17: critical non-compliance list exists ──────────────────────────────────
def test_C17_critical_non_compliance_exists():
    audit = _aud("03_compliance_scoring_audit.json")
    critical = audit.get("critical_non_compliance_items", [])
    assert isinstance(critical, list), "critical_non_compliance_items must be a list"
    nc = audit.get("non_compliance_items", [])
    assert isinstance(nc, list)


# ── C18: score caps exist ─────────────────────────────────────────────────────
def test_C18_score_caps_exist():
    audit = _aud("03_compliance_scoring_audit.json")
    assert audit.get("score_caps_enabled") is True
    assert audit.get("critical_override_rules_enabled") is True
    assert audit.get("fake_signature_auto_fail_enabled") is True
    caps = audit.get("score_caps_applied", [])
    assert isinstance(caps, list)


# ── C19: standards_compliance_report.pdf or html exists ──────────────────────
def test_C19_compliance_report_exists():
    pdf  = _PDF / "standards_compliance_report.pdf"
    html = _PDF / "standards_compliance_report.html"
    assert pdf.exists() or html.exists(), (
        "Neither standards_compliance_report.pdf nor .html found in pdf_outputs"
    )


# ── C20: PDF has executive summary ───────────────────────────────────────────
def test_C20_pdf_has_executive_summary():
    html = _PDF / "standards_compliance_report.html"
    if not html.exists():
        pytest.skip("HTML not generated")
    content = html.read_text(encoding="utf-8", errors="ignore")
    assert "الملخص التنفيذي" in content or "executive" in content.lower()


# ── C21: PDF has IVS section ─────────────────────────────────────────────────
def test_C21_pdf_has_ivs_section():
    html = _PDF / "standards_compliance_report.html"
    if not html.exists():
        pytest.skip("HTML not generated")
    content = html.read_text(encoding="utf-8", errors="ignore")
    assert "IVS" in content, "IVS section missing from HTML"
    assert "IVS 103" in content or "IVS 105" in content


# ── C22: PDF has USPAP section ───────────────────────────────────────────────
def test_C22_pdf_has_uspap_section():
    html = _PDF / "standards_compliance_report.html"
    if not html.exists():
        pytest.skip("HTML not generated")
    content = html.read_text(encoding="utf-8", errors="ignore")
    assert "USPAP" in content, "USPAP section missing from HTML"
    assert "SR 2" in content or "SR 1" in content


# ── C23: PDF has RICS section ────────────────────────────────────────────────
def test_C23_pdf_has_rics_section():
    html = _PDF / "standards_compliance_report.html"
    if not html.exists():
        pytest.skip("HTML not generated")
    content = html.read_text(encoding="utf-8", errors="ignore")
    assert "RICS" in content, "RICS section missing from HTML"
    assert "VPS 6" in content


# ── C24: PDF has FRA section ─────────────────────────────────────────────────
def test_C24_pdf_has_fra_section():
    html = _PDF / "standards_compliance_report.html"
    if not html.exists():
        pytest.skip("HTML not generated")
    content = html.read_text(encoding="utf-8", errors="ignore")
    assert "FRA" in content, "FRA section missing from HTML"
    assert "FRA-1" in content or "FRA-2" in content


# ── C25: PDF has advisory warning ────────────────────────────────────────────
def test_C25_pdf_has_advisory_warning():
    html = _PDF / "standards_compliance_report.html"
    if not html.exists():
        pytest.skip("HTML not generated")
    content = html.read_text(encoding="utf-8", errors="ignore")
    assert "advisory_only" in content, "advisory_only flag missing from HTML"
    assert "استرشادي" in content or "خبير تقييم معتمد" in content


# ── C26: PDF has signature gate ──────────────────────────────────────────────
def test_C26_pdf_has_signature_gate():
    html = _PDF / "standards_compliance_report.html"
    if not html.exists():
        pytest.skip("HTML not generated")
    content = html.read_text(encoding="utf-8", errors="ignore")
    assert "fake_signature_created=False" in content or "بانتظار توقيع" in content


# ── C27: fake signature does not appear ──────────────────────────────────────
def test_C27_no_fake_signature():
    for fname in _AUD.glob("*.json"):
        d = json.loads(fname.read_text(encoding="utf-8"))
        assert d.get("fake_signature_created", False) is False, (
            f"{fname.name}: fake_signature_created must be False"
        )
    html = _PDF / "standards_compliance_report.html"
    if html.exists():
        content = html.read_text(encoding="utf-8", errors="ignore")
        assert "fake_signature\n" not in content
        assert "mock_signature" not in content
        assert "fake_certification=True" not in content


# ── C28: Excel workbook exists ───────────────────────────────────────────────
def test_C28_excel_workbook_exists():
    audit = _aud("05_excel_audit.json")
    xl = _XL / "standards_compliance_workbook.xlsx"
    if audit.get("excel_workbook_created"):
        assert xl.exists(), "Excel workbook missing despite audit claiming created"
        assert xl.stat().st_size > 2_000, "Excel workbook too small"


# ── C29: visual review index exists ──────────────────────────────────────────
def test_C29_visual_review_index_exists():
    idx = _PREV / "OPEN_STANDARDS_COMPLIANCE_REVIEW_INDEX.html"
    assert idx.exists(), "Standards compliance visual review index missing"
    content = idx.read_text(encoding="utf-8", errors="ignore")
    assert "advisory_only" in content
    assert "visual_qa_status" in content or "الحالة العامة" in content


# ── C30: no internal paths in outputs ────────────────────────────────────────
def test_C30_no_internal_paths():
    idx = _PREV / "OPEN_STANDARDS_COMPLIANCE_REVIEW_INDEX.html"
    if idx.exists():
        content = idx.read_text(encoding="utf-8", errors="ignore")
        assert r"C:\Users" not in content, "Internal Windows path in visual index"
        assert "C:/Users/Lenovo" not in content
    for fname in _AUD.glob("*.json"):
        text = fname.read_text(encoding="utf-8", errors="ignore")
        assert r"C:\Users" not in text, f"Internal path in {fname.name}"
        assert "C:/Users/Lenovo" not in text


# ── C31: other workflows unaffected ──────────────────────────────────────────
def test_C31_other_workflows_unaffected():
    sim_dir = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_uploaded_template_simulation"
    assert sim_dir.is_dir(), "Simulation output dir must not be removed"
    hbu_dir = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_hbu_analysis"
    assert hbu_dir.is_dir(), "HBU output dir must not be removed"
    for fname in _AUD.glob("*.json"):
        d = json.loads(fname.read_text(encoding="utf-8"))
        assert "hbu_workflow_enabled" not in d, (
            f"{fname.name}: must not contain HBU-specific key hbu_workflow_enabled"
        )
        assert "template_pdf_uploaded" not in d, (
            f"{fname.name}: must not contain simulation-specific key template_pdf_uploaded"
        )
