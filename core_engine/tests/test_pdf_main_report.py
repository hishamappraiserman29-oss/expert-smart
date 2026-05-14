"""
test_pdf_main_report.py — Wave 7a.4 main report section (6 tests)

Tests:
  cursor (1): render advances cursor
  pdf bytes (1): valid %PDF output > 1.5 KB
  invalid profile (1): ValueError raised
  KPI gate (1): detailed > legacy (KPI cards only in non-legacy)
  empty dicts (1): missing keys → '—', no crash
  all profiles (1): legacy/detailed/professional_template all render
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
from reports.pdf.sections.main_report_pdf import render_main_report


def _new_pdf():
    doc = FPDF(orientation="P", unit="mm", format="A4")
    doc.set_auto_page_break(auto=True, margin=18)
    fam = register_fonts(doc)
    doc.add_page()
    return doc, fam


@pytest.fixture
def appraiser():
    return {
        "name": "د. عبد الرؤوف محمد",
        "license": "EG-2026-00471",
        "date": "2026-05-14",
    }


@pytest.fixture
def property_info():
    return {"address": "القاهرة الجديدة", "type": "سكني", "area": 320}


@pytest.fixture
def valuation_results():
    return {
        "market_value": 2_500_000,
        "price_per_sqm": 7_812,
        "confidence": "عالية",
        "value_words": "مليونان وخمسمائة ألف جنيه",
        "primary_approach": "مقارنة البيوع",
    }


class TestRenderMainReport:
    def test_advances_cursor(self, appraiser, property_info, valuation_results):
        doc, fam = _new_pdf()
        y0 = doc.get_y()
        render_main_report(
            doc, appraiser=appraiser, property_info=property_info,
            valuation_results=valuation_results, font_family=fam,
        )
        assert doc.get_y() > y0

    def test_outputs_valid_pdf(self, appraiser, property_info, valuation_results):
        doc, fam = _new_pdf()
        render_main_report(
            doc, appraiser=appraiser, property_info=property_info,
            valuation_results=valuation_results, font_family=fam,
        )
        out = doc.output()
        assert bytes(out[:4]) == b"%PDF"
        assert len(out) > 1500

    def test_invalid_profile_raises(self, appraiser, property_info, valuation_results):
        doc, fam = _new_pdf()
        with pytest.raises(ValueError, match="Unknown profile_key"):
            render_main_report(
                doc, appraiser=appraiser, property_info=property_info,
                valuation_results=valuation_results,
                profile_key="bad_profile", font_family=fam,
            )

    def test_detailed_larger_than_legacy_due_to_kpis(
        self, appraiser, property_info, valuation_results
    ):
        """detailed renders KPI cards → bigger PDF than legacy."""
        def _size(profile: str) -> int:
            doc, fam = _new_pdf()
            render_main_report(
                doc, appraiser=appraiser, property_info=property_info,
                valuation_results=valuation_results,
                profile_key=profile, font_family=fam,
            )
            return len(doc.output())

        assert _size("detailed") > _size("legacy")

    def test_empty_dicts_no_crash(self):
        doc, fam = _new_pdf()
        render_main_report(
            doc, appraiser={}, property_info={},
            valuation_results={}, font_family=fam,
        )
        assert bytes(doc.output()[:4]) == b"%PDF"

    def test_all_three_profiles_render(
        self, appraiser, property_info, valuation_results
    ):
        for profile in ("legacy", "detailed", "professional_template"):
            doc, fam = _new_pdf()
            render_main_report(
                doc, appraiser=appraiser, property_info=property_info,
                valuation_results=valuation_results,
                profile_key=profile, font_family=fam,
            )
            assert bytes(doc.output()[:4]) == b"%PDF", f"profile={profile}"
