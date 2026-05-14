#!/usr/bin/env python3
"""Standalone tests for sections/certification_pdf — run directly or via pytest."""

import sys
import io
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_ROOT = Path(__file__).resolve().parent.parent
_CORE = _ROOT / "core_engine"
for _p in (str(_ROOT), str(_CORE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest
from fpdf import FPDF

from core_engine.reports.pdf.pdf_components import register_fonts
from core_engine.reports.pdf.sections.certification_pdf import render_certification
from core_engine.reports.pdf.pdf_theme import DEFAULT


@pytest.fixture
def pdf():
    doc = FPDF(orientation="P", unit="mm", format="A4")
    doc.set_auto_page_break(auto=True, margin=18)
    family = register_fonts(doc)
    doc.add_page()
    doc._family = family
    return doc


@pytest.fixture
def appraiser():
    return {
        "name": "د. عبد الرؤوف محمد عبد الباقي",
        "title": "خبير تقييم عقاري معتمد",
        "firm": "EXPERT_SMART للاستشارات",
        "license": "EG-2026-00471",
        "date": "2026-05-14",
    }


def test_advances_cursor(pdf, appraiser):
    y0 = pdf.get_y()
    render_certification(pdf, appraiser=appraiser, font_family=pdf._family)
    assert pdf.get_y() > y0


def test_outputs_valid_pdf(pdf, appraiser):
    render_certification(pdf, appraiser=appraiser, font_family=pdf._family)
    out = pdf.output()
    assert bytes(out[:4]) == b"%PDF"
    assert len(out) > 1500


def test_invalid_profile_raises(pdf, appraiser):
    with pytest.raises(ValueError, match="Unknown profile_key"):
        render_certification(pdf, appraiser=appraiser, profile_key="unknown_profile")


def test_empty_appraiser_no_crash(pdf):
    render_certification(pdf, appraiser={}, font_family=pdf._family)
    out = pdf.output()
    assert bytes(out[:4]) == b"%PDF"


def test_professional_template_larger_than_legacy(appraiser):
    def _render(profile):
        doc = FPDF(format="A4")
        doc.set_auto_page_break(auto=True, margin=18)
        fam = register_fonts(doc)
        doc.add_page()
        render_certification(doc, appraiser=appraiser, profile_key=profile, font_family=fam)
        return len(doc.output())

    assert _render("professional_template") > _render("legacy")


def test_all_profiles_render(appraiser):
    for p in ("legacy", "detailed", "professional_template"):
        doc = FPDF(format="A4")
        doc.set_auto_page_break(auto=True, margin=18)
        fam = register_fonts(doc)
        doc.add_page()
        render_certification(doc, appraiser=appraiser, profile_key=p, font_family=fam)
        assert bytes(doc.output()[:4]) == b"%PDF", f"profile={p}"


def test_with_property_info(pdf, appraiser):
    prop = {"address": "القاهرة الجديدة، التجمع الخامس"}
    render_certification(pdf, appraiser=appraiser, property_info=prop, font_family=pdf._family)
    out = pdf.output()
    assert bytes(out[:4]) == b"%PDF"


if __name__ == "__main__":
    print("✓ Run via: pytest tests/test_pdf_certification.py -v")
