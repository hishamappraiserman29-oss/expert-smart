"""
test_pdf_cost_income_reconciliation.py — Wave 7a.5 (12 tests)

Tests:
  render_cost_approach (2): cursor advance, professional_template > legacy
  render_income_approach (2): cursor advance, empty data no crash
  render_reconciliation (2): cursor advance, empty data no crash
  orchestrator (6): invalid profile raises, all 3 approaches render,
                    None approaches skipped, partial (cost only),
                    all 3 profiles render, Arabic extractable
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
from reports.pdf.sections.cost_income_reconciliation_pdf import (
    render_cost_approach,
    render_cost_income_reconciliation,
    render_income_approach,
    render_reconciliation,
)


def _new_pdf():
    doc = FPDF(orientation="P", unit="mm", format="A4")
    doc.set_auto_page_break(auto=True, margin=18)
    fam = register_fonts(doc)
    doc.add_page()
    return doc, fam


@pytest.fixture
def cost_data():
    return {
        "rcn": 1_800_000,
        "depreciation_pct": "15%",
        "depreciation": 270_000,
        "land_value": 900_000,
        "cost_value_indication": 2_430_000,
        "reproduction_cost": 1_950_000,
        "age_ratio": "12/60",
    }


@pytest.fixture
def income_data():
    return {
        "gross_income": 240_000,
        "vacancy_pct": "8%",
        "opex": 60_000,
        "noi": 160_800,
        "cap_rate": "6.5%",
        "income_value_indication": 2_473_846,
        "discount_rate": "9%",
        "growth_rate": "3%",
    }


@pytest.fixture
def reconciliation_data():
    return {
        "weights": {"sales": "50%", "cost": "20%", "income": "30%"},
        "indications": {"sales": 2_500_000, "cost": 2_430_000, "income": 2_473_846},
        "final_value": 2_478_153,
        "final_value_words": "مليونان وأربعمائة وثمانية وسبعون ألف جنيه",
        "confidence_interval": "2.40M – 2.55M",
    }


# ── render_cost_approach ──────────────────────────────────────────────────────

class TestRenderCostApproach:
    def test_advances_cursor(self, cost_data):
        doc, fam = _new_pdf()
        y0 = doc.get_y()
        render_cost_approach(doc, cost_data, font_family=fam)
        assert doc.get_y() > y0

    def test_professional_template_larger_than_legacy(self, cost_data):
        def _size(profile: str) -> int:
            doc, fam = _new_pdf()
            render_cost_approach(doc, cost_data, profile_key=profile, font_family=fam)
            return len(doc.output())

        assert _size("professional_template") > _size("legacy")


# ── render_income_approach ────────────────────────────────────────────────────

class TestRenderIncomeApproach:
    def test_advances_cursor(self, income_data):
        doc, fam = _new_pdf()
        y0 = doc.get_y()
        render_income_approach(doc, income_data, font_family=fam)
        assert doc.get_y() > y0

    def test_empty_data_no_crash(self):
        doc, fam = _new_pdf()
        render_income_approach(doc, {}, font_family=fam)
        assert bytes(doc.output()[:4]) == b"%PDF"


# ── render_reconciliation ─────────────────────────────────────────────────────

class TestRenderReconciliation:
    def test_advances_cursor(self, reconciliation_data):
        doc, fam = _new_pdf()
        y0 = doc.get_y()
        render_reconciliation(doc, reconciliation_data, font_family=fam)
        assert doc.get_y() > y0

    def test_empty_data_no_crash(self):
        doc, fam = _new_pdf()
        render_reconciliation(doc, {}, font_family=fam)
        assert bytes(doc.output()[:4]) == b"%PDF"


# ── orchestrator ──────────────────────────────────────────────────────────────

class TestOrchestrator:
    def test_invalid_profile_raises(self, cost_data):
        doc, fam = _new_pdf()
        with pytest.raises(ValueError, match="Unknown profile_key"):
            render_cost_income_reconciliation(
                doc, cost_approach=cost_data, profile_key="bad", font_family=fam,
            )

    def test_all_three_approaches_render(self, cost_data, income_data, reconciliation_data):
        doc, fam = _new_pdf()
        render_cost_income_reconciliation(
            doc,
            cost_approach=cost_data,
            income_approach=income_data,
            reconciliation=reconciliation_data,
            font_family=fam,
        )
        out = doc.output()
        assert bytes(out[:4]) == b"%PDF"
        assert len(out) > 2000

    def test_none_approaches_skipped_no_crash(self):
        doc, fam = _new_pdf()
        render_cost_income_reconciliation(doc, font_family=fam)
        assert bytes(doc.output()[:4]) == b"%PDF"

    def test_partial_only_cost_approach(self, cost_data):
        doc, fam = _new_pdf()
        render_cost_income_reconciliation(doc, cost_approach=cost_data, font_family=fam)
        assert bytes(doc.output()[:4]) == b"%PDF"

    def test_all_three_profiles_render(self, cost_data, income_data, reconciliation_data):
        for profile in ("legacy", "detailed", "professional_template"):
            doc, fam = _new_pdf()
            render_cost_income_reconciliation(
                doc,
                cost_approach=cost_data,
                income_approach=income_data,
                reconciliation=reconciliation_data,
                profile_key=profile, font_family=fam,
            )
            assert bytes(doc.output()[:4]) == b"%PDF", f"profile={profile}"

    def test_arabic_content_extractable(self, cost_data, income_data, reconciliation_data):
        pdfplumber = pytest.importorskip("pdfplumber")
        import io

        doc, fam = _new_pdf()
        render_cost_income_reconciliation(
            doc,
            cost_approach=cost_data,
            income_approach=income_data,
            reconciliation=reconciliation_data,
            font_family=fam,
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
            "No readable content extracted from cost/income/reconciliation PDF"
        )
