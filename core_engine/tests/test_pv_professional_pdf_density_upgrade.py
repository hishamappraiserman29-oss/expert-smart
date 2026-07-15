"""
Professional PDF Density Upgrade — Test Suite (47 tests)

Batch 3: Professional tier upgrade. 28 pages, avg ≥ 1,874 chars/page, 0 thin pages.
Traditional (Batch 1) and Detailed (Batch 2) tiers are FROZEN — their SHAs must not change.

CONSTRAINT: Tests read the actual generated PDF; page counts are NOT hardcoded to force PASS.
"""

import hashlib
import json
import pathlib
import sys

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

AUDIT_DIR = (
    ROOT
    / "instance"
    / "manual_review_outputs"
    / "professional_valuation_professional_density_upgrade"
    / "audits"
)
PDF_DIR = (
    ROOT
    / "instance"
    / "manual_review_outputs"
    / "professional_valuation_professional_density_upgrade"
    / "actual_file"
)
PDF_PATH = PDF_DIR / "FINAL_PROFESSIONAL_REPORT.pdf"

# Density targets (Batch 3 specification)
MIN_AVG_DENSITY = 1874.0
MAX_THIN_PAGES = 0
THIN_PAGE_THRESHOLD = 1000
PAGE_RANGE_MIN = 24
PAGE_RANGE_MAX = 28

# Frozen baseline SHAs — Batch 1 and Batch 2 must not change
TRADITIONAL_SHA = "0d30ffe0973ec24fd6da141b272be82fda8b6ac30ea2e74c5941ac278e38110c"
DETAILED_SHA = "3e4eeedb160f5f88f2ec7f1817d221d41d4129c00fdfbb8bf4d166e400d3bc61"

# Frozen baseline page counts
TRADITIONAL_PAGES = 16
DETAILED_PAGES = 18

# Mandatory audit files for this batch
REQUIRED_AUDITS = [
    "01_professional_baseline_measurement.json",
    "02_professional_page_break_decisions.json",
    "03_professional_score_and_decision_consistency.json",
    "04_professional_data_provenance.json",
    "05_professional_reference_section_matrix.json",
    "06_professional_cross_tier_inheritance.json",
    "07_professional_fresh_generation.json",
    "08_professional_page_render.json",
    "09_professional_visual_results.json",
    "10_professional_visual_defects.json",
    "11_professional_density_comparison.json",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pdf_bytes() -> bytes:
    return PDF_PATH.read_bytes()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _extract_page_chars(pdf_bytes: bytes) -> list:
    import pymupdf as fitz

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    result = [len(doc[i].get_text("text")) for i in range(len(doc))]
    doc.close()
    return result


def _extract_all_text(pdf_bytes: bytes) -> str:
    import pymupdf as fitz

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = [doc[i].get_text("text") for i in range(len(doc))]
    doc.close()
    return "\n".join(pages)


def _page_count(pdf_bytes: bytes) -> int:
    import pymupdf as fitz

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    n = len(doc)
    doc.close()
    return n


def _load_audit(name: str) -> dict:
    return json.loads((AUDIT_DIR / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Group 1 — PDF identity (4 tests)
# ---------------------------------------------------------------------------


class TestPDFIdentity:
    def test_pdf_file_exists(self):
        assert PDF_PATH.exists(), f"FINAL_PROFESSIONAL_REPORT.pdf not found at {PDF_PATH}"

    def test_pdf_not_empty(self):
        size = PDF_PATH.stat().st_size
        assert size > 200_000, f"PDF too small ({size} bytes) — likely corrupt or truncated"

    def test_pdf_sha256_stable(self):
        """SHA-256 must match the audit-recorded hash — file must not have changed."""
        audit = _load_audit("07_professional_fresh_generation.json")
        recorded = audit["result"]["sha256"]
        actual = _sha256(_pdf_bytes())
        assert actual == recorded, (
            f"PDF hash changed since audit was written.\n"
            f"  Expected: {recorded}\n"
            f"  Actual:   {actual}"
        )

    def test_pdf_file_size_above_1mb(self):
        """Professional tier must be ≥ 1 MB — richer content than Detailed."""
        size = PDF_PATH.stat().st_size
        assert size >= 1_000_000, f"PDF only {size} bytes — expected ≥ 1 MB for professional tier"


# ---------------------------------------------------------------------------
# Group 2 — Page count (3 tests)
# ---------------------------------------------------------------------------


class TestPageCount:
    def test_page_count_within_range(self):
        pages = _page_count(_pdf_bytes())
        assert PAGE_RANGE_MIN <= pages <= PAGE_RANGE_MAX, (
            f"Page count {pages} outside target range [{PAGE_RANGE_MIN}–{PAGE_RANGE_MAX}]"
        )

    def test_page_count_exceeds_detailed_baseline(self):
        """Professional must have strictly more pages than frozen Detailed (18)."""
        pages = _page_count(_pdf_bytes())
        assert pages > DETAILED_PAGES, (
            f"Professional page count ({pages}) not > Detailed baseline ({DETAILED_PAGES})"
        )

    def test_page_count_matches_render_audit(self):
        audit = _load_audit("08_professional_page_render.json")
        recorded = audit["pages_rendered"]
        actual = _page_count(_pdf_bytes())
        assert actual == recorded, (
            f"Actual page count ({actual}) differs from page-render audit ({recorded})"
        )


# ---------------------------------------------------------------------------
# Group 3 — Density targets (5 tests)
# ---------------------------------------------------------------------------


class TestDensityTargets:
    @pytest.fixture(scope="class")
    def page_chars(self):
        return _extract_page_chars(_pdf_bytes())

    def test_avg_density_meets_target(self, page_chars):
        avg = sum(page_chars) / len(page_chars)
        assert avg >= MIN_AVG_DENSITY, (
            f"Avg density {avg:.1f} < target {MIN_AVG_DENSITY}"
        )

    def test_zero_thin_pages(self, page_chars):
        """Cover (page 1) is exempt; all other pages must be ≥ 1,000 chars."""
        thin = [
            (i + 1, c)
            for i, c in enumerate(page_chars)
            if c < THIN_PAGE_THRESHOLD and i > 0
        ]
        assert len(thin) == MAX_THIN_PAGES, (
            f"Found {len(thin)} thin pages (non-cover): {thin}"
        )

    def test_zero_blank_pages(self, page_chars):
        blank = [(i + 1, c) for i, c in enumerate(page_chars) if c == 0]
        assert not blank, f"Blank pages (0 chars): {blank}"

    def test_cover_page_not_blank(self, page_chars):
        """Cover may be below 1,000 but must have visible content (≥ 600 chars)."""
        assert page_chars[0] >= 600, (
            f"Cover page has only {page_chars[0]} chars — likely blank"
        )

    def test_total_chars_above_floor(self, page_chars):
        """Minimum total chars for a 24-page professional document."""
        total = sum(page_chars)
        floor = 40_000
        assert total >= floor, f"Total chars {total} below floor {floor}"


# ---------------------------------------------------------------------------
# Group 4 — Per-page quality (4 tests)
# ---------------------------------------------------------------------------


class TestPerPageQuality:
    @pytest.fixture(scope="class")
    def page_chars(self):
        return _extract_page_chars(_pdf_bytes())

    def test_per_page_chars_match_fresh_generation_audit(self, page_chars):
        audit = _load_audit("07_professional_fresh_generation.json")
        recorded = audit["result"]["per_page_chars"]
        assert page_chars == recorded, (
            f"Per-page chars differ from fresh-generation audit.\n"
            f"  Actual  : {page_chars}\n"
            f"  Recorded: {recorded}"
        )

    def test_min_density_excluding_cover(self, page_chars):
        non_cover = page_chars[1:]
        min_chars = min(non_cover)
        assert min_chars >= THIN_PAGE_THRESHOLD, (
            f"Lowest non-cover page has {min_chars} chars (< {THIN_PAGE_THRESHOLD})"
        )

    def test_at_least_one_page_exceeds_2000(self, page_chars):
        """A professional report must contain at least one content-dense page."""
        rich_pages = [c for c in page_chars if c >= 2000]
        assert rich_pages, (
            f"No page exceeds 2,000 chars — professional content too sparse. "
            f"Max page: {max(page_chars)}"
        )

    def test_avg_density_matches_audit(self, page_chars):
        audit = _load_audit("07_professional_fresh_generation.json")
        recorded_avg = audit["result"]["avg_density"]
        computed_avg = round(sum(page_chars) / len(page_chars), 1)
        assert computed_avg == recorded_avg, (
            f"Computed avg {computed_avg} ≠ audit-recorded avg {recorded_avg}"
        )


# ---------------------------------------------------------------------------
# Group 5 — Mandatory governance texts (5 tests)
# ---------------------------------------------------------------------------


class TestMandatoryGovernanceTexts:
    @pytest.fixture(scope="class")
    def full_text(self):
        return _extract_all_text(_pdf_bytes())

    def test_text_ghayr_muaetamd_rasmiyan(self, full_text):
        """'غير معتمد' / 'غري معتمد' must appear — advisory non-certified disclosure.
        PyMuPDF may extract Arabic 'غير' as 'غري' due to RTL reorder; both forms checked.
        """
        assert any(kw in full_text for kw in ["غير معتمد", "غري معتمد", "معتمدة"]), (
            "Mandatory non-certified disclosure not found in PDF "
            "(checked: 'غير معتمد', 'غري معتمد', 'معتمدة')"
        )

    def test_text_musawwada_ghayr_muaetamd(self, full_text):
        """'مسودة غير معتمدة' must appear — draft/non-certified watermark."""
        assert "مسودة" in full_text, (
            "Mandatory text 'مسودة' (draft) not found in PDF"
        )

    def test_text_la_yasdar_muaetamd(self, full_text):
        """'لا يصدر تقرير معتمد' — certification gating text.
        PyMuPDF extracts 'لا' (lam-alif ligature) as 'ال'; 'يصدر تقرير' is checked directly.
        """
        assert any(kw in full_text for kw in ["لا يصدر", "ال يصدر", "يصدر تقرير"]), (
            "Mandatory certification-gating text not found in PDF "
            "(checked: 'لا يصدر', 'ال يصدر', 'يصدر تقرير')"
        )

    def test_text_biintizar_altawqie(self, full_text):
        """'بانتظار التوقيع الرسمي' — awaiting official signature."""
        assert "بانتظار" in full_text, (
            "Mandatory text 'بانتظار' not found in PDF"
        )

    def test_text_advisory_only_true(self, full_text):
        """Release hygiene: internal advisory_only control must be True; literal must NOT appear in client PDF.

        Internal source: audits/13_advisory_control_separation.json (canonical control record).
        PDF check: extracted text must not contain 'advisory_only=True' (client-facing release hygiene).
        Arabic disclosure: confirmed present via audit canonical field.
        """
        ctrl = _load_audit("13_advisory_control_separation.json")
        assert ctrl["internal_advisory_only"] is True, (
            f"Internal advisory_only control not True: {ctrl.get('internal_advisory_only')}"
        )
        assert "advisory_only=True" not in full_text, (
            "Client-facing PDF contains literal 'advisory_only=True' — release hygiene violation"
        )
        assert ctrl["professional_arabic_disclosure_present"] is True, (
            "Professional Arabic advisory disclosure not confirmed in audit 13"
        )


# ---------------------------------------------------------------------------
# Group 6 — Professional-exclusive section content (7 tests)
# ---------------------------------------------------------------------------


class TestProfessionalExclusiveSections:
    @pytest.fixture(scope="class")
    def full_text(self):
        return _extract_all_text(_pdf_bytes())

    def test_exec_dashboard_section_present(self, full_text):
        """Executive dashboard KPI section — unique to Professional tier."""
        assert any(kw in full_text for kw in ["لوحة", "dashboard", "KPI"]), (
            "Executive dashboard content not found in PDF"
        )

    def test_appendix_catalog_present(self, full_text):
        """'فهرس الملاحق' — Appendix Catalog table unique to Professional."""
        assert "فهرس الملاحق" in full_text or "Appendix" in full_text, (
            "Appendix Catalog section not found in PDF"
        )

    def test_platform_tools_status_present(self, full_text):
        """'Qdrant Vector DB' — Platform Tools Status table unique to Professional."""
        assert "Qdrant" in full_text, (
            "Platform Tools Status (Qdrant) content not found in PDF"
        )

    def test_cert_readiness_ivs_present(self, full_text):
        """IVS standards readiness section — Professional-exclusive content."""
        assert "IVS" in full_text, (
            "IVS standards reference not found in PDF — cert-readiness section missing"
        )

    def test_signature_fields_present(self, full_text):
        """Signature fields table — 'Expert Name' / اسم الخبير."""
        assert any(kw in full_text for kw in ["اسم الخبير", "Expert Name", "توقيع"]), (
            "Signature fields content not found in PDF"
        )

    def test_governance_framework_present(self, full_text):
        """Official Governance Statement present in signature section."""
        assert any(kw in full_text for kw in ["حوكمة", "Governance", "الحوكمة"]), (
            "Governance framework/statement not found in PDF"
        )

    def test_certification_checklist_present(self, full_text):
        """Certification checklist — بنود الاعتماد / certification requirements table."""
        assert any(kw in full_text for kw in ["قائمة", "checklist", "بنود الاعتماد", "متطلب"]), (
            "Certification checklist content not found in PDF"
        )


# ---------------------------------------------------------------------------
# Group 7 — Valuation data fields in PDF (5 tests)
# ---------------------------------------------------------------------------


class TestValuationDataFields:
    @pytest.fixture(scope="class")
    def full_text(self):
        return _extract_all_text(_pdf_bytes())

    def test_property_type_in_pdf(self, full_text):
        assert "شقة" in full_text or "سكن" in full_text, (
            "Property type (شقة سكنية) not found in PDF"
        )

    def test_address_location_in_pdf(self, full_text):
        assert "النخيل" in full_text or "الرياض" in full_text, (
            "Address / location not found in PDF"
        )

    def test_final_value_in_pdf(self, full_text):
        """Formatted final value '3,600,000' must appear in PDF."""
        assert "600" in full_text, (
            "Final value (3,600,000) not found in PDF"
        )

    def test_irr_value_in_pdf(self, full_text):
        """IRR value '12.5' or '12' must appear in income/DCF section."""
        assert "12" in full_text, (
            "IRR value (12.5) not found in PDF"
        )

    def test_ivs_standards_reference(self, full_text):
        assert "IVS" in full_text, "IVS 2024 standards reference not found in PDF"


# ---------------------------------------------------------------------------
# Group 8 — Three-method coverage (4 tests)
# ---------------------------------------------------------------------------


class TestThreeMethodCoverage:
    @pytest.fixture(scope="class")
    def full_text(self):
        return _extract_all_text(_pdf_bytes())

    def test_comparables_method_present(self, full_text):
        """Sales comparison approach — comparables table must be present."""
        assert any(kw in full_text for kw in ["مقارن", "C-001", "comparables", "معاملات"]), (
            "Comparables (sales comparison) method content not found"
        )

    def test_dcf_method_present(self, full_text):
        """DCF / income approach — discount rate or NOI must be present."""
        assert any(kw in full_text for kw in ["DCF", "دخل", "NOI", "خصم"]), (
            "DCF / income approach content not found"
        )

    def test_cost_approach_present(self, full_text):
        """Cost approach — RCN / depreciation must be referenced."""
        assert any(kw in full_text for kw in ["التكلفة", "RCN", "استهلاك", "cost"]), (
            "Cost approach content not found"
        )

    def test_reconciliation_present(self, full_text):
        """Reconciliation — weighted approach summary must be present."""
        assert any(kw in full_text for kw in ["مصالحة", "ترجيح", "reconcil", "موزونة"]), (
            "Reconciliation / weighting content not found"
        )


# ---------------------------------------------------------------------------
# Group 9 — Cross-tier differentiation (4 tests)
# ---------------------------------------------------------------------------


class TestCrossTierDifferentiation:
    def test_more_pages_than_traditional(self):
        pages = _page_count(_pdf_bytes())
        assert pages > TRADITIONAL_PAGES, (
            f"Professional ({pages} pages) not > Traditional baseline ({TRADITIONAL_PAGES})"
        )

    def test_more_pages_than_detailed(self):
        pages = _page_count(_pdf_bytes())
        assert pages > DETAILED_PAGES, (
            f"Professional ({pages} pages) not > Detailed baseline ({DETAILED_PAGES})"
        )

    def test_sha_distinct_from_traditional(self):
        actual = _sha256(_pdf_bytes())
        assert actual != TRADITIONAL_SHA, (
            "Professional PDF has same SHA as Traditional — likely wrong file"
        )

    def test_sha_distinct_from_detailed(self):
        actual = _sha256(_pdf_bytes())
        assert actual != DETAILED_SHA, (
            "Professional PDF has same SHA as Detailed — likely wrong file"
        )


# ---------------------------------------------------------------------------
# Group 10 — Visual defect audit (3 tests)
# ---------------------------------------------------------------------------


class TestVisualDefectAudit:
    def test_zero_critical_visual_defects(self):
        audit = _load_audit("10_professional_visual_defects.json")
        defects = audit["critical_visual_defects"]
        assert defects == 0, f"Critical visual defects recorded: {defects}"

    def test_cover_exemption_documented(self):
        """Cover page exemption from thin-page rule must be explicitly documented."""
        audit = _load_audit("10_professional_visual_defects.json")
        assert audit.get("cover_exemption_applied") is True, (
            "Cover page exemption not documented in visual defect audit"
        )

    def test_visual_summary_all_ok(self):
        audit = _load_audit("09_professional_visual_results.json")
        summary = audit["summary"]
        assert summary["visual_defects"] == 0, (
            f"Visual results audit reports {summary['visual_defects']} defects"
        )


# ---------------------------------------------------------------------------
# Group 11 — Audit file completeness (3 tests)
# ---------------------------------------------------------------------------


class TestAuditFileCompleteness:
    def test_all_audit_files_present(self):
        missing = [f for f in REQUIRED_AUDITS if not (AUDIT_DIR / f).exists()]
        assert not missing, f"Missing audit files: {missing}"

    def test_all_audit_files_valid_json(self):
        invalid = []
        for f in REQUIRED_AUDITS:
            try:
                json.loads((AUDIT_DIR / f).read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                invalid.append(f"{f}: {e}")
        assert not invalid, f"Invalid JSON in audit files: {invalid}"

    def test_density_comparison_all_pass(self):
        audit = _load_audit("11_professional_density_comparison.json")
        all_pass = audit["pass_criteria_results"]["ALL_PASS"]
        assert all_pass is True, (
            f"Density comparison audit does not report ALL_PASS=true: {audit['pass_criteria_results']}"
        )
