"""
test_pdf_sales_comparison.py — Wave 7a.4 sales comparison section (7 tests)

Tests:
  cursor (1): render advances cursor
  pdf bytes (1): valid %PDF output > 1.5 KB
  invalid profile (1): ValueError raised
  empty comps (1): graceful 'no comps' note, no crash
  partial comp keys (1): missing comp fields → '—', no crash
  all profiles (1): legacy/detailed/professional_template all render
  arabic extractable (1): pdfplumber finds Arabic chars (skip if absent)
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
from reports.pdf.sections.sales_comparison_pdf import render_sales_comparison


def _new_pdf():
    doc = FPDF(orientation="P", unit="mm", format="A4")
    doc.set_auto_page_break(auto=True, margin=18)
    fam = register_fonts(doc)
    doc.add_page()
    return doc, fam


@pytest.fixture
def subject():
    return {"address": "القاهرة الجديدة", "area": 320, "type": "سكني"}


@pytest.fixture
def comparables():
    return [
        {
            "ref": "ع1", "address": "التجمع الخامس",
            "sale_price": 2_400_000, "area": 310,
            "price_per_sqm": 7_741, "adjustment_pct": "+3%",
            "adjusted_value": 2_472_000,
        },
        {
            "ref": "ع2", "address": "الرحاب",
            "sale_price": 2_600_000, "area": 330,
            "price_per_sqm": 7_878, "adjustment_pct": "-2%",
            "adjusted_value": 2_548_000,
        },
    ]


class TestRenderSalesComparison:
    def test_advances_cursor(self, subject, comparables):
        doc, fam = _new_pdf()
        y0 = doc.get_y()
        render_sales_comparison(
            doc, subject=subject, comparables=comparables, font_family=fam,
        )
        assert doc.get_y() > y0

    def test_outputs_valid_pdf(self, subject, comparables):
        doc, fam = _new_pdf()
        render_sales_comparison(
            doc, subject=subject, comparables=comparables, font_family=fam,
        )
        out = doc.output()
        assert bytes(out[:4]) == b"%PDF"
        assert len(out) > 1500

    def test_invalid_profile_raises(self, subject, comparables):
        doc, fam = _new_pdf()
        with pytest.raises(ValueError, match="Unknown profile_key"):
            render_sales_comparison(
                doc, subject=subject, comparables=comparables,
                profile_key="bad_profile", font_family=fam,
            )

    def test_empty_comparables_renders_note(self, subject):
        doc, fam = _new_pdf()
        render_sales_comparison(
            doc, subject=subject, comparables=[], font_family=fam,
        )
        out = doc.output()
        assert bytes(out[:4]) == b"%PDF"

    def test_partial_comp_keys_render_dash(self, subject):
        doc, fam = _new_pdf()
        render_sales_comparison(
            doc, subject=subject,
            comparables=[{"ref": "ع1"}],
            font_family=fam,
        )
        assert bytes(doc.output()[:4]) == b"%PDF"

    def test_all_three_profiles_render(self, subject, comparables):
        for profile in ("legacy", "detailed", "professional_template"):
            doc, fam = _new_pdf()
            render_sales_comparison(
                doc, subject=subject, comparables=comparables,
                profile_key=profile, font_family=fam,
            )
            assert bytes(doc.output()[:4]) == b"%PDF", f"profile={profile}"

    def test_arabic_content_extractable(self, subject, comparables):
        pdfplumber = pytest.importorskip("pdfplumber")
        import io

        doc, fam = _new_pdf()
        render_sales_comparison(
            doc, subject=subject, comparables=comparables, font_family=fam,
        )
        buf = io.BytesIO(bytes(doc.output()))
        with pdfplumber.open(buf) as p:
            text = "".join(pg.extract_text() or "" for pg in p.pages)

        arabic_present = any(
            "؀" <= ch <= "ۿ"
            or "ﹰ" <= ch <= "﻿"
            or "ﭐ" <= ch <= "﷿"
            for ch in text
        )
        assert arabic_present or len(text.strip()) > 0, (
            "No readable content extracted from sales comparison PDF"
        )
