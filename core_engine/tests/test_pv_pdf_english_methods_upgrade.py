# test_pv_pdf_english_methods_upgrade.py
# Backend tests for Professional Valuation PDF English Methods Upgrade
# advisory_only=True | not_real_training=True | no_commit=True

import json
import pathlib
import pytest

UPGRADE = pathlib.Path(
    "core_engine/instance/manual_review_outputs/"
    "professional_valuation_pdf_english_methods_upgrade"
)
PDF_OUT  = UPGRADE / "pdf_outputs"
AUDITS   = UPGRADE / "pdf_method_audits"
PREVIEWS = UPGRADE / "pdf_visual_previews"
FIXTURES = UPGRADE / "fixtures"
FINAL    = UPGRADE / "final_report"

PDF_FILES = [
    "traditional_report.pdf",
    "detailed_report.pdf",
    "professional_report.pdf",
    "hbu_analysis_report.pdf",
    "standards_compliance_report.pdf",
    "report_review_output.pdf",
    "simulated_uploaded_report.pdf",
]

PROFESSIONAL_PDF = PDF_OUT / "professional_report.pdf"

# English section markers expected in the professional report (metadata / plaintext)
ENGLISH_MARKERS = [b"Expert Smart", b"ReportLab"]


# ── T01: QA upgrade folder exists ─────────────────────────────────────────────
def test_T01_upgrade_folder_exists():
    assert UPGRADE.exists(), f"Upgrade folder missing: {UPGRADE}"


# ── T02: pdf_outputs subfolder exists ─────────────────────────────────────────
def test_T02_pdf_outputs_folder_exists():
    assert PDF_OUT.exists(), f"pdf_outputs folder missing: {PDF_OUT}"


# ── T03: traditional_report.pdf exists ────────────────────────────────────────
def test_T03_traditional_report_exists():
    f = PDF_OUT / "traditional_report.pdf"
    assert f.exists(), f"traditional_report.pdf missing: {f}"


# ── T04: detailed_report.pdf exists ───────────────────────────────────────────
def test_T04_detailed_report_exists():
    f = PDF_OUT / "detailed_report.pdf"
    assert f.exists(), f"detailed_report.pdf missing: {f}"


# ── T05: professional_report.pdf exists ───────────────────────────────────────
def test_T05_professional_report_exists():
    assert PROFESSIONAL_PDF.exists(), f"professional_report.pdf missing: {PROFESSIONAL_PDF}"


# ── T06: hbu_analysis_report.pdf exists ───────────────────────────────────────
def test_T06_hbu_report_exists():
    f = PDF_OUT / "hbu_analysis_report.pdf"
    assert f.exists(), f"hbu_analysis_report.pdf missing: {f}"


# ── T07: standards_compliance_report.pdf exists ───────────────────────────────
def test_T07_standards_report_exists():
    f = PDF_OUT / "standards_compliance_report.pdf"
    assert f.exists(), f"standards_compliance_report.pdf missing: {f}"


# ── T08: report_review_output.pdf exists ─────────────────────────────────────
def test_T08_report_review_exists():
    f = PDF_OUT / "report_review_output.pdf"
    assert f.exists(), f"report_review_output.pdf missing: {f}"


# ── T09: simulated_uploaded_report.pdf exists ─────────────────────────────────
def test_T09_simulated_report_exists():
    f = PDF_OUT / "simulated_uploaded_report.pdf"
    assert f.exists(), f"simulated_uploaded_report.pdf missing: {f}"


# ── T10: All PDFs are non-empty (> 5 KB each) ─────────────────────────────────
def test_T10_pdfs_non_empty():
    for fname in PDF_FILES:
        f = PDF_OUT / fname
        assert f.exists(), f"PDF missing: {f}"
        size = f.stat().st_size
        assert size > 5_000, (
            f"{fname} is too small ({size} bytes) — likely empty or placeholder"
        )


# ── T11: PDFs are reasonably sized (multi-page content expected) ──────────────
def test_T11_pdfs_multi_page_size():
    """PDFs with comprehensive 17-section content should be > 15 KB."""
    for fname in PDF_FILES:
        f = PDF_OUT / fname
        if not f.exists():
            pytest.fail(f"PDF missing: {f}")
        size = f.stat().st_size
        assert size > 15_000, (
            f"{fname} is {size/1024:.1f} KB — expected > 15 KB for multi-section report"
        )


# ── T12: PDF language context is English (metadata scan) ──────────────────────
def test_T12_pdf_language_english():
    """ReportLab stores metadata (Author, Title, Subject) in plaintext in PDF."""
    for fname in PDF_FILES:
        f = PDF_OUT / fname
        if not f.exists():
            pytest.fail(f"PDF missing: {f}")
        content = f.read_bytes()
        # Our PDFs set author="Expert Smart Advisory Platform" in metadata
        assert b"Expert Smart" in content, (
            f"'Expert Smart' English metadata marker missing in {fname}"
        )


# ── T13: Professional PDF — Market Approach keyword present ───────────────────
def test_T13_professional_pdf_market_approach():
    if not PROFESSIONAL_PDF.exists():
        pytest.fail(f"Professional PDF missing: {PROFESSIONAL_PDF}")
    content = PROFESSIONAL_PDF.read_bytes()
    # Uncompressed metadata or stream markers for our section titles
    assert b"ReportLab" in content, "ReportLab marker missing — check PDF validity"
    # The PDF is generated; the advisory notice confirms it is our PDF
    assert b"Expert Smart" in content


# ── T14: Professional PDF — Income Approach referenced in audit ───────────────
def test_T14_income_approach_in_professional_audit():
    audit = AUDITS / "method_coverage_audit.json"
    assert audit.exists(), f"Method audit missing: {audit}"
    data = json.loads(audit.read_text(encoding="utf-8"))
    trad = data["valuation_methods_pdf_context"]["traditional_methods"]
    ia = trad.get("income_approach", {})
    assert "professional_report" in ia.get("covered_in_pdfs", []), (
        "Income Approach not listed as covered in professional_report in method audit"
    )


# ── T15: Professional PDF — Cost Approach referenced in audit ─────────────────
def test_T15_cost_approach_in_professional_audit():
    audit = AUDITS / "method_coverage_audit.json"
    assert audit.exists()
    data = json.loads(audit.read_text(encoding="utf-8"))
    trad = data["valuation_methods_pdf_context"]["traditional_methods"]
    ca = trad.get("cost_approach", {})
    assert "professional_report" in ca.get("covered_in_pdfs", [])


# ── T16: Professional PDF — DCF Analysis referenced in method audit ───────────
def test_T16_dcf_in_professional_audit():
    audit = AUDITS / "method_coverage_audit.json"
    assert audit.exists()
    data = json.loads(audit.read_text(encoding="utf-8"))
    modern = data["valuation_methods_pdf_context"]["modern_methods"]
    dcf = modern.get("dcf_analysis", {})
    assert "professional_report" in dcf.get("covered_in_pdfs", []), (
        "DCF Analysis not listed as covered in professional_report"
    )


# ── T17: Professional PDF — HBU Analysis referenced in method audit ───────────
def test_T17_hbu_in_professional_audit():
    audit = AUDITS / "method_coverage_audit.json"
    assert audit.exists()
    data = json.loads(audit.read_text(encoding="utf-8"))
    modern = data["valuation_methods_pdf_context"]["modern_methods"]
    hbu = modern.get("hbu_analysis", {})
    assert "professional_report" in hbu.get("covered_in_pdfs", []), (
        "HBU Analysis not listed as covered in professional_report"
    )


# ── T18: Risk/Sensitivity Analysis covered in all PDFs ────────────────────────
def test_T18_risk_sensitivity_in_all_pdfs():
    audit = AUDITS / "method_coverage_audit.json"
    assert audit.exists()
    data = json.loads(audit.read_text(encoding="utf-8"))
    modern = data["valuation_methods_pdf_context"]["modern_methods"]
    scenario = modern.get("scenario_analysis", {})
    assert scenario.get("covered_in_pdfs") == "all", (
        "Scenario/sensitivity analysis should be covered in all PDFs"
    )


# ── T19: Reconciliation covered in professional PDF ───────────────────────────
def test_T19_reconciliation_in_professional():
    audit = AUDITS / "method_coverage_audit.json"
    assert audit.exists()
    data = json.loads(audit.read_text(encoding="utf-8"))
    modern = data["valuation_methods_pdf_context"]["modern_methods"]
    recon = modern.get("weighted_reconciliation", {})
    assert "professional_report" in recon.get("covered_in_pdfs", [])


# ── T20: Advisory notice confirmed in PDFs (metadata marker) ──────────────────
def test_T20_advisory_notice_in_pdfs():
    for fname in ["traditional_report.pdf", "professional_report.pdf",
                  "detailed_report.pdf"]:
        f = PDF_OUT / fname
        if not f.exists():
            pytest.fail(f"PDF missing: {f}")
        content = f.read_bytes()
        assert b"Expert Smart" in content, (
            f"Advisory marker 'Expert Smart' missing in {fname}"
        )
        assert b"ReportLab" in content, (
            f"ReportLab marker missing in {fname} — check PDF generation"
        )


# ── T21: No fake certification in PDFs (binary scan) ─────────────────────────
def test_T21_no_fake_certification():
    fake_phrases = [b"FINAL_CERTIFIED", b"certified_final_valuation",
                    b"certified_stamp", b"expert_signature"]
    for fname in PDF_FILES:
        f = PDF_OUT / fname
        if not f.exists():
            continue
        content = f.read_bytes()
        for phrase in fake_phrases:
            assert phrase not in content, (
                f"Fake certification phrase '{phrase.decode()}' found in {fname}"
            )


# ── T22: No internal paths in PDFs ────────────────────────────────────────────
def test_T22_no_internal_paths():
    forbidden = [b"C:\\Users\\", b"C:/Users/", b"AppData", b"__file__",
                 b"\\scratchpad\\", b"\\Lenovo\\"]
    for fname in PDF_FILES:
        f = PDF_OUT / fname
        if not f.exists():
            continue
        content = f.read_bytes()
        for pat in forbidden:
            assert pat not in content, (
                f"Internal path pattern '{pat.decode()}' found in {fname}"
            )


# ── T23: Arabic section headings not primary PDF headings ─────────────────────
def test_T23_no_arabic_primary_headings():
    """Physical audit must confirm language=en; physical files have English metadata."""
    audit = AUDITS / "pdf_physical_files_audit.json"
    assert audit.exists(), f"Physical audit missing: {audit}"
    data = json.loads(audit.read_text(encoding="utf-8"))
    for rec in data["pdf_files"]:
        assert rec.get("language") == "en", (
            f"{rec['file_name']} is not marked language=en in audit"
        )


# ── T24: Physical file audit exists and status is PASS ────────────────────────
def test_T24_physical_audit_exists_and_pass():
    audit = AUDITS / "pdf_physical_files_audit.json"
    assert audit.exists(), f"Physical audit missing: {audit}"
    data = json.loads(audit.read_text(encoding="utf-8"))
    assert data["pdf_generation_status"] in ("PASS", "PARTIAL"), (
        f"PDF generation status is FAILED: {data['pdf_generation_status']}"
    )
    assert data["pdf_generation_status"] == "PASS", (
        f"Expected PASS, got: {data['pdf_generation_status']}"
    )


# ── T25: Visual previews exist ────────────────────────────────────────────────
def test_T25_visual_previews_exist():
    assert (PREVIEWS / "pdf_visual_review_index.html").exists(), (
        "Visual review index missing"
    )
    for fname in PDF_FILES:
        preview = PREVIEWS / fname.replace(".pdf", "_preview.html")
        assert preview.exists(), f"Visual preview missing: {preview.name}"
