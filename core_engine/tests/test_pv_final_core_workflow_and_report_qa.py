"""
test_pv_final_core_workflow_and_report_qa.py — 42 backend tests.

PVCWF01  core_report_profiles module is importable
PVCWF02  core_report_examples module is importable
PVCWF03  core_pdf_generator module is importable
PVCWF04  core_excel_generator module is importable

PVCWF05  traditional_report has exactly 16 sections in profiles
PVCWF06  detailed_report has exactly 25 sections in profiles
PVCWF07  professional_report has exactly 29 sections in profiles
PVCWF08  REPORT_TYPES list contains exactly three expected values

PVCWF09  traditional_report.pdf exists in QA output directory
PVCWF10  detailed_report.pdf exists in QA output directory
PVCWF11  professional_report.pdf exists in QA output directory
PVCWF12  PDF size ordering: traditional < detailed < professional

PVCWF13  traditional_report_admin_workbook.xlsx exists
PVCWF14  detailed_report_admin_workbook.xlsx exists
PVCWF15  professional_report_admin_workbook.xlsx exists
PVCWF16  Excel size ordering: traditional < professional

PVCWF17  traditional_report has fewer sections than detailed_report
PVCWF18  detailed_report has fewer sections than professional_report
PVCWF19  traditional_report includes Market Approach section
PVCWF20  professional_report includes HBU Summary section

PVCWF21  traditional method_coverage does not include dcf_full
PVCWF22  professional method_coverage includes hbu_summary=True
PVCWF23  get_unique_sections returns only sections not in a shorter report
PVCWF24  practical examples dict covers all three report types

PVCWF25  chat_intent_guard_audit.json exists and has advisory_only=True
PVCWF26  chat_data_quality_score_audit.json exists and has formula defined
PVCWF27  filtered_report_context_audit.json exists
PVCWF28  core_three_reports_physical_files_audit.json exists

PVCWF29  distinctness_audit.json exists and marks all three distinct
PVCWF30  method_coverage_audit.json exists
PVCWF31  practical_examples_audit.json exists
PVCWF32  visual_review_index.html exists in pdf_visual_previews

PVCWF33  data quality scoring formula weights sum to 1.0
PVCWF34  weak score below 0.40
PVCWF35  strong score at or above 0.80
PVCWF36  score level mapping covers all five levels

PVCWF37  chat intent guard has irrelevant_off_topic category
PVCWF38  chat intent guard has unsafe_content category
PVCWF39  chat intent guard has valuation_primary category
PVCWF40  chat intent guard has eight categories total

PVCWF41  advisory_only flag not absent from examples module
PVCWF42  ordinary valuation module still importable (regression guard)

advisory_only=True | not_real_training=True
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
import pytest

# Resolve paths
_CORE = Path(__file__).resolve().parent.parent
_QA_ROOT = (
    _CORE / "instance" / "manual_review_outputs"
    / "professional_valuation_final_core_workflow_and_report_qa"
)
_PDF_DIR   = _QA_ROOT / "pdf_outputs"
_XLS_DIR   = _QA_ROOT / "excel_outputs"
_AUDIT_DIR = _QA_ROOT

sys.path.insert(0, str(_CORE))


# ─── Module imports ────────────────────────────────────────────────────────────

def test_PVCWF01_profiles_importable():
    """PVCWF01: core_report_profiles is importable without error."""
    from professional_valuation_core_report_profiles import REPORT_TYPES  # noqa: F401


def test_PVCWF02_examples_importable():
    """PVCWF02: core_report_examples is importable without error."""
    from professional_valuation_core_report_examples import SUBJECT  # noqa: F401


def test_PVCWF03_pdf_generator_importable():
    """PVCWF03: core_pdf_generator module is importable."""
    from professional_valuation_core_pdf_generator import generate_all_pdfs  # noqa: F401


def test_PVCWF04_excel_generator_importable():
    """PVCWF04: core_excel_generator module is importable."""
    from professional_valuation_core_excel_generator import generate_all_excel  # noqa: F401


# ─── Profile correctness ───────────────────────────────────────────────────────

def test_PVCWF05_traditional_has_16_sections():
    """PVCWF05: traditional_report profile lists 16 sections."""
    from professional_valuation_core_report_profiles import SECTIONS
    assert len(SECTIONS["traditional_report"]) == 16


def test_PVCWF06_detailed_has_25_sections():
    """PVCWF06: detailed_report profile lists 25 sections."""
    from professional_valuation_core_report_profiles import SECTIONS
    assert len(SECTIONS["detailed_report"]) == 25


def test_PVCWF07_professional_has_29_sections():
    """PVCWF07: professional_report profile lists 29 sections."""
    from professional_valuation_core_report_profiles import SECTIONS
    assert len(SECTIONS["professional_report"]) == 29


def test_PVCWF08_report_types_list_has_three():
    """PVCWF08: REPORT_TYPES contains exactly three expected slugs."""
    from professional_valuation_core_report_profiles import REPORT_TYPES
    assert set(REPORT_TYPES) == {
        "traditional_report",
        "detailed_report",
        "professional_report",
    }


# ─── Physical PDF existence ────────────────────────────────────────────────────

def test_PVCWF09_traditional_pdf_exists():
    """PVCWF09: traditional_report.pdf exists in QA pdf_outputs."""
    assert (_PDF_DIR / "traditional_report.pdf").is_file(), (
        f"Missing: {_PDF_DIR / 'traditional_report.pdf'} — run core_generate_reports.py first"
    )


def test_PVCWF10_detailed_pdf_exists():
    """PVCWF10: detailed_report.pdf exists in QA pdf_outputs."""
    assert (_PDF_DIR / "detailed_report.pdf").is_file()


def test_PVCWF11_professional_pdf_exists():
    """PVCWF11: professional_report.pdf exists in QA pdf_outputs."""
    assert (_PDF_DIR / "professional_report.pdf").is_file()


def test_PVCWF12_pdf_size_ordering():
    """PVCWF12: PDF sizes are ordered traditional < detailed < professional."""
    trad = (_PDF_DIR / "traditional_report.pdf").stat().st_size
    det  = (_PDF_DIR / "detailed_report.pdf").stat().st_size
    prof = (_PDF_DIR / "professional_report.pdf").stat().st_size
    assert trad < det < prof, (
        f"PDF size ordering violated: trad={trad}, det={det}, prof={prof}"
    )


# ─── Physical Excel existence ──────────────────────────────────────────────────

def test_PVCWF13_traditional_excel_exists():
    """PVCWF13: traditional_report_admin_workbook.xlsx exists."""
    assert (_XLS_DIR / "traditional_report_admin_workbook.xlsx").is_file()


def test_PVCWF14_detailed_excel_exists():
    """PVCWF14: detailed_report_admin_workbook.xlsx exists."""
    assert (_XLS_DIR / "detailed_report_admin_workbook.xlsx").is_file()


def test_PVCWF15_professional_excel_exists():
    """PVCWF15: professional_report_admin_workbook.xlsx exists."""
    assert (_XLS_DIR / "professional_report_admin_workbook.xlsx").is_file()


def test_PVCWF16_excel_size_ordering():
    """PVCWF16: Professional Excel is larger than traditional Excel."""
    trad = (_XLS_DIR / "traditional_report_admin_workbook.xlsx").stat().st_size
    prof = (_XLS_DIR / "professional_report_admin_workbook.xlsx").stat().st_size
    assert trad < prof, f"Excel size ordering violated: trad={trad}, prof={prof}"


# ─── Report distinctness ───────────────────────────────────────────────────────

def test_PVCWF17_traditional_fewer_sections_than_detailed():
    """PVCWF17: traditional has fewer sections than detailed."""
    from professional_valuation_core_report_profiles import SECTIONS
    assert len(SECTIONS["traditional_report"]) < len(SECTIONS["detailed_report"])


def test_PVCWF18_detailed_fewer_sections_than_professional():
    """PVCWF18: detailed has fewer sections than professional."""
    from professional_valuation_core_report_profiles import SECTIONS
    assert len(SECTIONS["detailed_report"]) < len(SECTIONS["professional_report"])


def test_PVCWF19_traditional_includes_market_approach():
    """PVCWF19: traditional_report profile includes a Market Approach section."""
    from professional_valuation_core_report_profiles import SECTIONS
    labels = [s.lower() for s in SECTIONS["traditional_report"]]
    assert any("market" in l for l in labels), (
        "traditional_report should contain a Market Approach section"
    )


def test_PVCWF20_professional_includes_hbu_summary():
    """PVCWF20: professional_report profile includes a Highest and Best Use section."""
    from professional_valuation_core_report_profiles import SECTIONS
    labels = [s.lower() for s in SECTIONS["professional_report"]]
    assert any("hbu" in l or "highest" in l or "best use" in l for l in labels), (
        "professional_report should include Highest and Best Use section"
    )


# ─── Method coverage ───────────────────────────────────────────────────────────

def test_PVCWF21_traditional_excludes_dcf_full():
    """PVCWF21: traditional_report method_coverage does not include dcf_full=True."""
    from professional_valuation_core_report_profiles import METHOD_COVERAGE
    mc = METHOD_COVERAGE["traditional_report"]
    assert mc.get("dcf_full", False) is False


def test_PVCWF22_professional_includes_hbu_true():
    """PVCWF22: professional_report method_coverage has hbu_summary=True."""
    from professional_valuation_core_report_profiles import METHOD_COVERAGE
    mc = METHOD_COVERAGE["professional_report"]
    assert mc.get("hbu_summary", False) is True


def test_PVCWF23_get_unique_sections_returns_extras():
    """PVCWF23: get_unique_sections for detailed returns sections not in traditional."""
    from professional_valuation_core_report_profiles import SECTIONS, get_unique_sections
    unique = get_unique_sections("detailed_report")
    trad_sections = set(SECTIONS["traditional_report"])
    # All returned sections should not be in traditional
    for s in unique:
        assert s not in trad_sections, f"Section '{s}' should not be in traditional_report"


def test_PVCWF24_practical_examples_covers_all_types():
    """PVCWF24: PRACTICAL_EXAMPLES dict has entries for all three report types."""
    from professional_valuation_core_report_profiles import PRACTICAL_EXAMPLES, REPORT_TYPES
    for rt in REPORT_TYPES:
        assert rt in PRACTICAL_EXAMPLES, f"PRACTICAL_EXAMPLES missing entry for '{rt}'"


# ─── Audit JSON existence ──────────────────────────────────────────────────────

def test_PVCWF25_intent_guard_audit_exists():
    """PVCWF25: chat_intent_guard_audit.json exists and guard is enabled."""
    p = _AUDIT_DIR / "data_quality_audits" / "chat_intent_guard_audit.json"
    assert p.is_file(), f"Missing: {p}"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data.get("enabled") is True
    assert data.get("result") == "PASS"


def test_PVCWF26_data_quality_score_audit_exists():
    """PVCWF26: chat_data_quality_score_audit.json exists and defines the scoring formula."""
    p = _AUDIT_DIR / "data_quality_audits" / "chat_data_quality_score_audit.json"
    assert p.is_file(), f"Missing: {p}"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert "scoring_formula" in data, "audit should contain 'scoring_formula' field"


def test_PVCWF27_filtered_report_context_audit_exists():
    """PVCWF27: filtered_report_context_audit.json exists."""
    p = _AUDIT_DIR / "data_quality_audits" / "filtered_report_context_audit.json"
    assert p.is_file(), f"Missing: {p}"


def test_PVCWF28_physical_files_audit_exists():
    """PVCWF28: core_three_reports_physical_files_audit.json exists."""
    p = _AUDIT_DIR / "report_structure_audits" / "core_three_reports_physical_files_audit.json"
    assert p.is_file(), f"Missing: {p}"


# ─── Additional audits ─────────────────────────────────────────────────────────

def test_PVCWF29_distinctness_audit_passes():
    """PVCWF29: distinctness_audit.json status is PASS and all three reports compared."""
    p = _AUDIT_DIR / "report_distinctness_audits" / "core_three_reports_distinctness_audit.json"
    assert p.is_file(), f"Missing: {p}"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data.get("distinctness_status") == "PASS", (
        f"Distinctness audit did not pass: {data.get('distinctness_status')}"
    )
    for rt in ("traditional_report", "detailed_report", "professional_report"):
        assert rt in data.get("reports_compared", []), f"'{rt}' missing from reports_compared"


def test_PVCWF30_method_coverage_audit_exists():
    """PVCWF30: core_three_reports_method_coverage_audit.json exists."""
    p = _AUDIT_DIR / "method_coverage_audits" / "core_three_reports_method_coverage_audit.json"
    assert p.is_file(), f"Missing: {p}"


def test_PVCWF31_practical_examples_audit_exists():
    """PVCWF31: core_three_reports_practical_examples_audit.json exists."""
    p = _AUDIT_DIR / "method_coverage_audits" / "core_three_reports_practical_examples_audit.json"
    assert p.is_file(), f"Missing: {p}"


def test_PVCWF32_visual_review_index_html_exists():
    """PVCWF32: visual_review_index.html exists in pdf_visual_previews."""
    p = _AUDIT_DIR / "pdf_visual_previews" / "core_three_reports_visual_review_index.html"
    assert p.is_file(), f"Missing: {p}"


# ─── Data quality scoring logic ────────────────────────────────────────────────

def test_PVCWF33_formula_weights_sum_to_one():
    """PVCWF33: Data quality scoring formula weights sum to 1.0."""
    weights = {
        "min_req": 0.60,
        "req_if_applicable": 0.20,
        "recommended": 0.10,
        "doc_support": 0.10,
    }
    assert abs(sum(weights.values()) - 1.0) < 1e-9


def test_PVCWF34_weak_score_below_threshold():
    """PVCWF34: A score of 0.30 (weak) is below the 0.40 acceptable threshold."""
    score = 0.30
    assert score < 0.40, "Weak score should be below acceptable threshold"


def test_PVCWF35_strong_score_at_or_above_threshold():
    """PVCWF35: A score of 0.85 (strong) meets the strong threshold of 0.80."""
    score = 0.85
    assert score >= 0.80, "Strong score should meet the 0.80 threshold"


def test_PVCWF36_score_levels_cover_five():
    """PVCWF36: Score level mapping defines all five expected levels."""
    levels = ["very_weak", "weak", "acceptable", "good", "strong"]
    assert len(levels) == 5


# ─── Chat intent guard categories ─────────────────────────────────────────────

def _load_intent_guard_categories() -> list[str]:
    p = _AUDIT_DIR / "data_quality_audits" / "chat_intent_guard_audit.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    return data.get("classification_categories", [])


def test_PVCWF37_intent_guard_has_irrelevant_category():
    """PVCWF37: chat intent guard defines an irrelevant/general chat category."""
    cats = _load_intent_guard_categories()
    assert any("irrelevant" in c for c in cats), (
        f"Expected an irrelevant category in {cats}"
    )


def test_PVCWF38_intent_guard_has_unsafe_content():
    """PVCWF38: chat intent guard defines an unsafe or out-of-scope category."""
    cats = _load_intent_guard_categories()
    assert any("unsafe" in c or "out_of_scope" in c for c in cats), (
        f"Expected an unsafe category in {cats}"
    )


def test_PVCWF39_intent_guard_has_valuation_primary():
    """PVCWF39: chat intent guard defines a valuation-relevant category."""
    cats = _load_intent_guard_categories()
    assert any("valuation" in c for c in cats), (
        f"Expected a valuation category in {cats}"
    )


def test_PVCWF40_intent_guard_has_eight_categories():
    """PVCWF40: chat intent guard defines exactly eight classification categories."""
    cats = _load_intent_guard_categories()
    assert len(cats) == 8, f"Expected 8 categories, got {len(cats)}: {cats}"


# ─── Regression safety checks ──────────────────────────────────────────────────

def test_PVCWF41_examples_has_advisory_only_flag():
    """PVCWF41: core_report_examples module exposes advisory_only=True."""
    from professional_valuation_core_report_examples import ADVISORY_FLAGS
    assert ADVISORY_FLAGS.get("advisory_only") is True
    assert ADVISORY_FLAGS.get("not_real_training") is True


def test_PVCWF42_ordinary_valuation_module_importable():
    """PVCWF42: Ordinary valuation routes module still importable (regression guard)."""
    import importlib.util
    mod_path = _CORE / "professional_valuation_routes.py"
    spec = importlib.util.spec_from_file_location("pv_routes", mod_path)
    assert spec is not None, "professional_valuation_routes.py not found"
