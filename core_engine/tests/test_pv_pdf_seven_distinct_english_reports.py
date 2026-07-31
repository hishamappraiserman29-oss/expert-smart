# test_pv_pdf_seven_distinct_english_reports.py
# Backend tests — Radical PDF Rebuild: 7 Distinct English Report Types
# advisory_only=True | not_real_training=True | no_commit=True

import json
import pathlib
import pytest

BASE = pathlib.Path(
    "core_engine/instance/manual_review_outputs/"
    "professional_valuation_pdf_seven_distinct_english_reports"
)
PDF_OUT   = BASE / "pdf_outputs"
RT_AUDITS = BASE / "report_type_audits"
M_AUDITS  = BASE / "method_audits"
EXCEL_REF = BASE / "legacy_excel_reference_audits"
PREVIEWS  = BASE / "pdf_visual_previews"
FIXTURES  = BASE / "fixtures"
FINAL     = BASE / "final_report"

PDF_FILES = [
    "traditional_report.pdf",
    "detailed_report.pdf",
    "professional_report.pdf",
    "hbu_analysis_report.pdf",
    "standards_compliance_report.pdf",
    "report_review_output.pdf",
    "simulated_uploaded_report.pdf",
]

PROFESSIONAL = PDF_OUT / "professional_report.pdf"
DETAILED     = PDF_OUT / "detailed_report.pdf"
HBU          = PDF_OUT / "hbu_analysis_report.pdf"


# ── T01: QA output folder exists ──────────────────────────────────────────────
def test_T01_output_folder_exists():
    assert BASE.exists(), f"Output folder missing: {BASE}"


# ── T02: All seven PDFs physically exist ─────────────────────────────────────
def test_T02_all_seven_pdfs_exist():
    for fname in PDF_FILES:
        f = PDF_OUT / fname
        assert f.exists(), f"PDF missing: {f}"


# ── T03: All seven PDFs are non-empty (> 15 KB) ───────────────────────────────
def test_T03_all_pdfs_non_empty():
    for fname in PDF_FILES:
        f = PDF_OUT / fname
        assert f.exists(), f"PDF missing: {f}"
        sz = f.stat().st_size
        assert sz > 15_000, f"{fname} is {sz/1024:.1f} KB — too small for multi-section report"


# ── T04: All seven PDFs are English (metadata marker) ─────────────────────────
def test_T04_all_pdfs_english():
    for fname in PDF_FILES:
        f = PDF_OUT / fname
        assert f.exists(), f"PDF missing: {f}"
        content = f.read_bytes()
        assert b"Expert Smart" in content, (
            f"English advisory marker 'Expert Smart' missing in {fname}"
        )


# ── T05: English language audit confirms PASS ─────────────────────────────────
def test_T05_english_language_audit_pass():
    audit = RT_AUDITS / "pdf_english_language_audit.json"
    assert audit.exists(), f"Language audit missing: {audit}"
    data = json.loads(audit.read_text(encoding="utf-8"))
    assert data["pdf_language_required"] == "en"
    assert data["english_primary_headings"] is True
    assert data["arabic_primary_headings_found"] == []
    assert data["language_status"] == "PASS"


# ── T06: Traditional report — Market Approach covered ─────────────────────────
def test_T06_traditional_report_market_approach():
    audit = M_AUDITS / "pdf_method_coverage_audit.json"
    assert audit.exists()
    data = json.loads(audit.read_text(encoding="utf-8"))
    trad = data["traditional_report"]
    assert trad["market_approach"] is True


# ── T07: Traditional report — Income and Cost Approach covered ────────────────
def test_T07_traditional_income_and_cost():
    data = json.loads((M_AUDITS/"pdf_method_coverage_audit.json").read_text(encoding="utf-8"))
    trad = data["traditional_report"]
    assert trad["income_approach"] is True
    assert trad["cost_approach"] is True


# ── T08: Traditional report — AVM-Assisted Indication covered ────────────────
def test_T08_traditional_avm_indication():
    data = json.loads((M_AUDITS/"pdf_method_coverage_audit.json").read_text(encoding="utf-8"))
    assert data["traditional_report"]["avm_assisted_indication"] is True


# ── T09: Detailed report — Excel-style depth and DCF covered ──────────────────
def test_T09_detailed_excel_style_dcf():
    data = json.loads((M_AUDITS/"pdf_method_coverage_audit.json").read_text(encoding="utf-8"))
    det = data["detailed_report"]
    assert det["legacy_excel_style_detail"] is True
    assert det["dcf_summary"] is True
    assert det["sensitivity_snapshot"] is True


# ── T10: Detailed report is richer than traditional (larger file) ─────────────
def test_T10_detailed_richer_than_traditional():
    trad_sz = (PDF_OUT / "traditional_report.pdf").stat().st_size
    det_sz  = (PDF_OUT / "detailed_report.pdf").stat().st_size
    assert det_sz > trad_sz, (
        f"detailed_report ({det_sz/1024:.1f} KB) must be larger than traditional_report ({trad_sz/1024:.1f} KB)"
    )


# ── T11: Professional report is richer than detailed (larger file) ────────────
def test_T11_professional_richer_than_detailed():
    det_sz  = DETAILED.stat().st_size
    prof_sz = PROFESSIONAL.stat().st_size
    assert prof_sz > det_sz, (
        f"professional_report ({prof_sz/1024:.1f} KB) must be larger than detailed_report ({det_sz/1024:.1f} KB)"
    )


# ── T12: Professional report — DCF, HBU, Scenario, Sensitivity, Risk, AVM, Recon ─
def test_T12_professional_full_modern_methods():
    data = json.loads((M_AUDITS/"pdf_method_coverage_audit.json").read_text(encoding="utf-8"))
    prof = data["professional_report"]
    for method in ["dcf_analysis","hbu_summary","scenario_analysis","sensitivity_analysis",
                   "risk_adjusted_valuation","avm_assisted_indication","weighted_reconciliation"]:
        assert prof[method] is True, f"professional_report missing method: {method}"


# ── T13: Professional report — traditional methods also covered ───────────────
def test_T13_professional_traditional_methods():
    data = json.loads((M_AUDITS/"pdf_method_coverage_audit.json").read_text(encoding="utf-8"))
    prof = data["professional_report"]
    for m in ["market_approach","income_approach","cost_approach"]:
        assert prof[m] is True, f"professional_report missing: {m}"


# ── T14: HBU report — all four tests covered ─────────────────────────────────
def test_T14_hbu_four_tests_covered():
    data = json.loads((M_AUDITS/"pdf_method_coverage_audit.json").read_text(encoding="utf-8"))
    hbu = data["hbu_analysis_report"]
    for test in ["physically_possible","legally_permissible","financially_feasible","maximally_productive"]:
        assert hbu[test] is True, f"HBU report missing test: {test}"


# ── T15: HBU report — not flagged as valuation report ────────────────────────
def test_T15_hbu_not_ordinary_valuation():
    data = json.loads((M_AUDITS/"pdf_method_coverage_audit.json").read_text(encoding="utf-8"))
    assert data["hbu_analysis_report"]["is_valuation_report"] is False


# ── T16: HBU report — residual method and alternative use scenarios covered ───
def test_T16_hbu_residual_and_scenarios():
    data = json.loads((M_AUDITS/"pdf_method_coverage_audit.json").read_text(encoding="utf-8"))
    hbu = data["hbu_analysis_report"]
    assert hbu["residual_land_value"] is True
    assert hbu["alternative_use_scenarios"] is True


# ── T17: Standards compliance report — compliance matrix, no value conclusion ─
def test_T17_standards_compliance_no_conclusion():
    data = json.loads((M_AUDITS/"pdf_method_coverage_audit.json").read_text(encoding="utf-8"))
    std = data["standards_compliance_report"]
    assert std["standards_matrix"] is True
    assert std["advisory_compliance_only"] is True
    assert std["valuation_conclusion_included"] is False


# ── T18: Report review output — review checklist, no new valuation ────────────
def test_T18_review_output_checklist_no_new_valuation():
    data = json.loads((M_AUDITS/"pdf_method_coverage_audit.json").read_text(encoding="utf-8"))
    rev = data["report_review_output"]
    assert rev["completeness_checklist"] is True
    assert rev["new_valuation_conclusion"] is False
    assert rev["risk_flags"] is True


# ── T19: Simulated report — simulation scope, no fake upload claim ────────────
def test_T19_simulation_no_fake_upload():
    data = json.loads((M_AUDITS/"pdf_method_coverage_audit.json").read_text(encoding="utf-8"))
    sim = data["simulated_uploaded_report"]
    assert sim["simulation_scope"] is True
    assert sim["real_report_uploaded"] is False
    assert sim["fake_uploaded_report_claim"] is False


# ── T20: Practical examples in every PDF ─────────────────────────────────────
def test_T20_practical_examples_in_all_pdfs():
    audit = M_AUDITS / "pdf_practical_examples_audit.json"
    assert audit.exists(), f"Practical examples audit missing: {audit}"
    data = json.loads(audit.read_text(encoding="utf-8"))
    assert data["all_pdfs_have_practical_examples"] is True
    for rtype in ["traditional_report","detailed_report","professional_report",
                  "hbu_analysis_report","standards_compliance_report",
                  "report_review_output","simulated_uploaded_report"]:
        assert data[rtype]["practical_examples_present"] is True, (
            f"{rtype}: practical_examples_present is not True"
        )


# ── T21: Seven PDF distinctness audit passes ─────────────────────────────────
def test_T21_seven_pdfs_distinctness_pass():
    audit = RT_AUDITS / "seven_pdf_distinctness_audit.json"
    assert audit.exists(), f"Distinctness audit missing: {audit}"
    data = json.loads(audit.read_text(encoding="utf-8"))
    assert data["reports_are_distinct"] is True
    assert data["near_duplicate_report_pairs"] == []
    assert data["distinctness_verdict"].startswith("PASS")


# ── T22: English language audit path exists ───────────────────────────────────
def test_T22_english_language_audit_exists():
    assert (RT_AUDITS / "pdf_english_language_audit.json").exists()


# ── T23: Method coverage audit path exists ────────────────────────────────────
def test_T23_method_coverage_audit_exists():
    assert (M_AUDITS / "pdf_method_coverage_audit.json").exists()


# ── T24: Physical file audit — status PASS ────────────────────────────────────
def test_T24_physical_audit_status_pass():
    audit = RT_AUDITS / "pdf_physical_files_audit.json"
    assert audit.exists()
    data = json.loads(audit.read_text(encoding="utf-8"))
    assert data["pdf_generation_status"] == "PASS", (
        f"PDF generation status: {data['pdf_generation_status']}"
    )
    assert data["pdf_language"] == "en"
    assert data["advisory_only"] is True
    for rec in data["pdf_files"]:
        assert rec["pdf_generation_status"] == "PASS", (
            f"{rec['file_name']}: generation status is {rec['pdf_generation_status']}"
        )
        assert rec["language"] == "en"
        assert rec["contains_fake_certification"] is False
        assert rec["contains_internal_paths"] is False


# ── T25: No fake certification in any PDF ─────────────────────────────────────
def test_T25_no_fake_certification():
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


# ── T26: No internal paths in PDFs ────────────────────────────────────────────
def test_T26_no_internal_paths():
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


# ── T27: Visual previews exist ────────────────────────────────────────────────
def test_T27_visual_previews_exist():
    assert (PREVIEWS / "pdf_visual_review_index.html").exists()
    for fname in PDF_FILES:
        preview = PREVIEWS / fname.replace(".pdf", "_preview.html")
        assert preview.exists(), f"Preview missing: {preview.name}"


# ── T28: Advanced report type registry exists ─────────────────────────────────
def test_T28_advanced_registry_exists():
    reg = RT_AUDITS / "advanced_report_type_registry.json"
    assert reg.exists()
    data = json.loads(reg.read_text(encoding="utf-8"))
    for key in ["traditional_valuation_report","detailed_valuation_report",
                "professional_valuation_report","hbu_analysis_report",
                "standards_compliance_report","valuation_review_report",
                "simulated_uploaded_report_analysis"]:
        assert key in data, f"Missing registry entry: {key}"


# ── T29: Legacy Excel reference audit exists ──────────────────────────────────
def test_T29_legacy_excel_reference_audit():
    audit = EXCEL_REF / "legacy_excel_reference_audit.json"
    assert audit.exists()
    data = json.loads(audit.read_text(encoding="utf-8"))
    assert data["files_overwritten"] is False
    assert data["excel_parity_claimed"] is False


# ── T30: Final report exists ──────────────────────────────────────────────────
def test_T30_final_report_exists():
    rpt = FINAL / "final_pdf_seven_distinct_english_reports_report.txt"
    assert rpt.exists(), f"Final report missing: {rpt}"
    text = rpt.read_text(encoding="utf-8")
    assert "COMPLETE" in text
    assert "advisory_only=True" in text
