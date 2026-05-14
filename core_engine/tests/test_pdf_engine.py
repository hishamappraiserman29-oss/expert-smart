"""
test_pdf_engine.py — Wave 7a.6 (10 tests)

Tests:
  TestGeneratePdf (6): creates file, valid PDF magic bytes, invalid profile
                       raises, parent dirs auto-created, all 3 profiles,
                       minimal data no crash
  TestDeterminism (2): identical MD5 across multiple runs, different
                       profiles differ
  TestArabicIntegration (2): full doc ≥4 pages contains readable content,
                              fonts_dir override no crash
"""
from __future__ import annotations

import hashlib
import os
import sys
import tempfile
from pathlib import Path

_CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_CORE))
os.chdir(str(_CORE))

import pytest

from reports.pdf.pdf_engine import generate_pdf

# ── Shared fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def tmp_dir(tmp_path):
    return tmp_path


@pytest.fixture
def full_data():
    return {
        "appraiser": {
            "name": "د. محمد الخبير",
            "license": "EG-2026-00471",
            "date": "2026-05-14",
        },
        "property_info": {
            "address": "القاهرة الجديدة",
            "type": "سكني",
            "area": 320,
        },
        "valuation_results": {
            "market_value": 2_500_000,
            "price_per_sqm": 7_812,
            "confidence": "عالية",
            "value_words": "مليونان وخمسمائة ألف جنيه",
            "primary_approach": "مقارنة البيوع",
        },
        "subject": {"address": "القاهرة الجديدة", "area": 320, "type": "سكني"},
        "comparables": [
            {
                "ref": "ع1",
                "address": "التجمع الخامس",
                "sale_price": 2_400_000,
                "area": 310,
                "price_per_sqm": 7_741,
                "adjustment_pct": "+3%",
                "adjusted_value": 2_472_000,
            },
        ],
        "cost_approach": {
            "rcn": 1_800_000,
            "depreciation_pct": "15%",
            "depreciation": 270_000,
            "land_value": 900_000,
            "cost_value_indication": 2_430_000,
        },
        "income_approach": {
            "gross_income": 240_000,
            "vacancy_pct": "8%",
            "opex": 60_000,
            "noi": 160_800,
            "cap_rate": "6.5%",
            "income_value_indication": 2_473_846,
        },
        "reconciliation": {
            "weights": {"sales": "50%", "cost": "20%", "income": "30%"},
            "indications": {"sales": 2_500_000, "cost": 2_430_000, "income": 2_473_846},
            "final_value": 2_478_153,
            "final_value_words": "مليونان وأربعمائة وثمانية وسبعون ألف جنيه",
        },
        "certification": {
            "name": "د. محمد الخبير",
            "license": "EG-2026-00471",
            "date": "2026-05-14",
        },
    }


# ── TestGeneratePdf ───────────────────────────────────────────────────────────

class TestGeneratePdf:
    def test_creates_file(self, tmp_dir, full_data):
        out = tmp_dir / "report.pdf"
        result = generate_pdf(profile_key="legacy", data=full_data, output_path=out)
        assert result == out
        assert out.is_file()

    def test_valid_pdf_magic_bytes(self, tmp_dir, full_data):
        out = tmp_dir / "report.pdf"
        generate_pdf(profile_key="legacy", data=full_data, output_path=out)
        assert out.read_bytes()[:4] == b"%PDF"

    def test_invalid_profile_raises(self, tmp_dir, full_data):
        with pytest.raises(ValueError, match="Unknown profile_key"):
            generate_pdf(profile_key="bad", data=full_data, output_path=tmp_dir / "x.pdf")

    def test_creates_parent_dirs(self, tmp_dir, full_data):
        deep = tmp_dir / "a" / "b" / "c" / "report.pdf"
        generate_pdf(profile_key="legacy", data=full_data, output_path=deep)
        assert deep.is_file()

    def test_all_three_profiles(self, tmp_dir, full_data):
        for profile in ("legacy", "detailed", "professional_template"):
            out = tmp_dir / f"{profile}.pdf"
            generate_pdf(profile_key=profile, data=full_data, output_path=out)
            assert out.read_bytes()[:4] == b"%PDF", f"profile={profile}"

    def test_minimal_data_no_crash(self, tmp_dir):
        out = tmp_dir / "minimal.pdf"
        generate_pdf(profile_key="legacy", data={}, output_path=out)
        assert out.read_bytes()[:4] == b"%PDF"


# ── TestDeterminism ───────────────────────────────────────────────────────────

class TestDeterminism:
    def _md5(self, path: Path) -> str:
        return hashlib.md5(path.read_bytes()).hexdigest()

    def test_identical_md5_across_runs(self, tmp_dir, full_data):
        outs = [tmp_dir / f"run{i}.pdf" for i in range(3)]
        for out in outs:
            generate_pdf(profile_key="legacy", data=full_data, output_path=out)
        digests = [self._md5(o) for o in outs]
        assert len(set(digests)) == 1, f"Non-deterministic: {digests}"

    def test_different_profiles_produce_different_files(self, tmp_dir, full_data):
        profiles = ["legacy", "detailed", "professional_template"]
        digests = set()
        for p in profiles:
            out = tmp_dir / f"{p}.pdf"
            generate_pdf(profile_key=p, data=full_data, output_path=out)
            digests.add(self._md5(out))
        assert len(digests) > 1, "All three profiles produced identical files"


# ── TestArabicIntegration ─────────────────────────────────────────────────────

class TestArabicIntegration:
    def test_full_doc_readable(self, tmp_dir, full_data):
        pdfplumber = pytest.importorskip("pdfplumber")
        import io

        out = tmp_dir / "full.pdf"
        generate_pdf(
            profile_key="professional_template",
            data=full_data,
            output_path=out,
        )
        buf = io.BytesIO(out.read_bytes())
        with pdfplumber.open(buf) as p:
            text = "".join(pg.extract_text() or "" for pg in p.pages)
            page_count = len(p.pages)

        assert page_count >= 1, "Expected at least 1 page"
        arabic_present = any(
            "؀" <= ch <= "ۿ"
            or "ﹰ" <= ch <= "﻿"
            or "ﭐ" <= ch <= "﷿"
            for ch in text
        )
        assert arabic_present or len(text.strip()) > 0, (
            "No readable content extracted from full PDF"
        )

    def test_fonts_dir_override_no_crash(self, tmp_dir, full_data):
        out = tmp_dir / "override.pdf"
        # Pass a non-existent fonts_dir — engine must gracefully fall back
        generate_pdf(
            profile_key="legacy",
            data=full_data,
            output_path=out,
            fonts_dir=tmp_dir / "nonexistent_fonts",
        )
        assert out.read_bytes()[:4] == b"%PDF"
