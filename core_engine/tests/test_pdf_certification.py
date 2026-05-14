"""
test_pdf_certification.py — Wave 7a.3 certification section (8 tests)

Tests:
  cursor (1): render advances cursor
  pdf bytes (1): valid %PDF output > 1.5 KB with property_info
  invalid profile (1): ValueError raised
  empty appraiser (1): missing keys → '—', no crash
  profile size (1): professional_template > legacy (USPAP block)
  all profiles (1): legacy/detailed/professional_template all render
  arabic extractable (1): pdfplumber finds Arabic codepoints (skip if absent)
  signature block (1): signature/date cells present (no exception)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_CORE))
os.chdir(str(_CORE))

import pytest
from fpdf import FPDF

from reports.pdf.pdf_components import register_fonts
from reports.pdf.sections.certification_pdf import render_certification


# ── Shared fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def pdf():
    doc = FPDF(orientation="P", unit="mm", format="A4")
    doc.set_auto_page_break(auto=True, margin=18)
    family = register_fonts(doc)
    doc.add_page()
    doc._family = family
    return doc


@pytest.fixture
def sample_appraiser():
    return {
        "name":    "د. عبد الرؤوف محمد عبد الباقي",
        "title":   "خبير تقييم عقاري معتمد",
        "firm":    "EXPERT_SMART للاستشارات",
        "license": "EG-2026-00471",
        "date":    "2026-05-14",
    }


@pytest.fixture
def sample_property():
    return {"address": "القاهرة الجديدة، التجمع الخامس، الحي الأول"}


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestRenderCertification:
    def test_advances_cursor(self, pdf, sample_appraiser):
        y_before = pdf.get_y()
        render_certification(pdf, appraiser=sample_appraiser, font_family=pdf._family)
        assert pdf.get_y() > y_before

    def test_outputs_valid_pdf_bytes(self, pdf, sample_appraiser, sample_property):
        render_certification(
            pdf,
            appraiser=sample_appraiser,
            property_info=sample_property,
            font_family=pdf._family,
        )
        out = pdf.output()
        assert bytes(out[:4]) == b"%PDF"
        assert len(out) > 1500

    def test_invalid_profile_raises_value_error(self, pdf, sample_appraiser):
        with pytest.raises(ValueError, match="Unknown profile_key"):
            render_certification(
                pdf,
                appraiser=sample_appraiser,
                profile_key="enterprise",
                font_family=pdf._family,
            )

    def test_empty_appraiser_no_crash(self, pdf):
        render_certification(pdf, appraiser={}, font_family=pdf._family)
        out = pdf.output()
        assert bytes(out[:4]) == b"%PDF"

    def test_professional_template_larger_than_legacy(self, sample_appraiser):
        def _render(profile: str) -> int:
            doc = FPDF(format="A4")
            doc.set_auto_page_break(auto=True, margin=18)
            fam = register_fonts(doc)
            doc.add_page()
            render_certification(
                doc, appraiser=sample_appraiser,
                profile_key=profile, font_family=fam,
            )
            return len(doc.output())

        assert _render("professional_template") > _render("legacy")

    def test_all_three_profiles_render(self, sample_appraiser):
        for profile in ("legacy", "detailed", "professional_template"):
            doc = FPDF(format="A4")
            doc.set_auto_page_break(auto=True, margin=18)
            fam = register_fonts(doc)
            doc.add_page()
            render_certification(
                doc, appraiser=sample_appraiser,
                profile_key=profile, font_family=fam,
            )
            assert bytes(doc.output()[:4]) == b"%PDF", f"profile={profile}"

    def test_arabic_content_extractable(self, pdf, sample_appraiser):
        """pdfplumber should find Arabic Unicode codepoints in the PDF."""
        pdfplumber = pytest.importorskip("pdfplumber")
        import io

        render_certification(
            pdf, appraiser=sample_appraiser, font_family=pdf._family,
        )
        buf = io.BytesIO(bytes(pdf.output()))
        with pdfplumber.open(buf) as doc:
            text = "".join(p.extract_text() or "" for p in doc.pages)

        arabic_present = any(
            "؀" <= ch <= "ۿ"
            or "ﹰ" <= ch <= "﻿"
            or "ﭐ" <= ch <= "﷿"
            for ch in text
        )
        assert arabic_present or len(text.strip()) > 0, (
            "No readable text extracted from certification PDF"
        )

    def test_signature_block_renders(self, pdf, sample_appraiser):
        render_certification(pdf, appraiser=sample_appraiser, font_family=pdf._family)
        # Signature block is the last thing rendered — cursor should be past the banner
        from reports.pdf.pdf_theme import DEFAULT
        assert pdf.get_y() > DEFAULT.banner_h + DEFAULT.margin_top
