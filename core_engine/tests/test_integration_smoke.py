"""
End-to-end integration smoke test for the three report engines.

Verifies validation → pdf → db work together with realistic data,
BEFORE bridge_api wiring. Pure verification — touches no engine code.

If an interface mismatch surfaces here, that is the intended finding:
report it, do NOT patch a frozen engine.

Chain: sample_data → validate_report → generate_pdf → save_report
                                                    → get_report
                                                    → list_reports
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parents[1]    # core_engine/
_TESTS = Path(__file__).resolve().parent       # core_engine/tests/
sys.path.insert(0, str(_CORE))
sys.path.insert(0, str(_TESTS))
os.chdir(str(_CORE))

from reports.db import (  # noqa: E402
    ReportRecord,
    get_report,
    list_reports,
    save_report,
)
from reports.pdf import generate_pdf  # noqa: E402
from reports.validation import validate_report  # noqa: E402
from _sample_reports import all_profiles, sample_report_data  # noqa: E402


# ── 1. Validation Engine ─────────────────────────────────────────────

class TestValidationIntegration:
    @pytest.mark.parametrize("profile", all_profiles())
    def test_SI01_sample_data_passes_validation(self, profile):
        """Each profile's sample DTO must validate cleanly (no ERRORs)."""
        result = validate_report(
            sample_report_data(profile), profile_key=profile,
        )
        assert result.is_valid, (
            f"Sample data for '{profile}' has validation errors: "
            f"{[i.code for i in result.errors]}"
        )

    @pytest.mark.parametrize("profile", all_profiles())
    def test_SI02_validation_result_bilingual(self, profile):
        """Every issue (if any) must carry both Arabic and English messages."""
        result = validate_report(
            sample_report_data(profile), profile_key=profile,
        )
        for issue in result.issues:
            assert issue.message_ar, f"Missing Arabic message: {issue.code}"
            assert issue.message_en, f"Missing English message: {issue.code}"

    @pytest.mark.parametrize("profile", all_profiles())
    def test_SI03_validation_result_has_correct_shape(self, profile):
        """ValidationResult must expose .is_valid, .errors, .warnings, .issues."""
        result = validate_report(
            sample_report_data(profile), profile_key=profile,
        )
        assert hasattr(result, "is_valid")
        assert hasattr(result, "errors")
        assert hasattr(result, "warnings")
        assert hasattr(result, "issues")


# ── 2. PDF Engine ────────────────────────────────────────────────────

class TestPdfIntegration:
    @pytest.mark.parametrize("profile", all_profiles())
    def test_SI04_generate_pdf_produces_valid_file(self, tmp_path, profile):
        """generate_pdf must produce a non-empty valid PDF for each profile."""
        out = tmp_path / f"{profile}.pdf"
        generate_pdf(
            profile_key=profile,
            data=sample_report_data(profile),
            output_path=out,
        )
        assert out.exists(), f"PDF not created for profile '{profile}'"
        assert out.read_bytes()[:4] == b"%PDF", "File does not start with PDF magic bytes"
        assert out.stat().st_size > 3_000, "PDF is suspiciously small"

    def test_SI05_pdf_deterministic(self, tmp_path):
        """Same input → identical PDF bytes (7a.6 determinism guarantee)."""
        data = sample_report_data("detailed")
        hashes: set[str] = set()
        for i in range(2):
            out = tmp_path / f"run_{i}.pdf"
            generate_pdf(profile_key="detailed", data=data, output_path=out)
            hashes.add(hashlib.md5(out.read_bytes()).hexdigest())
        assert len(hashes) == 1, "PDF output is not deterministic"

    @pytest.mark.parametrize("profile", all_profiles())
    def test_SI06_pdf_returns_path_object(self, tmp_path, profile):
        out = tmp_path / f"ret_{profile}.pdf"
        result = generate_pdf(
            profile_key=profile,
            data=sample_report_data(profile),
            output_path=out,
        )
        assert isinstance(result, Path)
        assert result == out


# ── 3. DB Engine ─────────────────────────────────────────────────────

class TestDbIntegration:
    @pytest.mark.parametrize("profile", all_profiles())
    def test_SI07_save_get_round_trip(self, tmp_path, profile):
        """save_report → get_report must return identical data for each profile."""
        db = tmp_path / f"{profile}_smoke.db"
        data = sample_report_data(profile)
        rid = save_report(data, profile_key=profile, db_path=db)
        rec = get_report(rid, db_path=db)
        assert isinstance(rec, ReportRecord)
        assert rec.data == data
        assert rec.profile_key == profile

    def test_SI08_list_after_saving_all_profiles(self, tmp_path):
        """list_reports must return one record per saved profile."""
        db = tmp_path / "smoke_all.db"
        profiles = all_profiles()
        for profile in profiles:
            save_report(sample_report_data(profile),
                        profile_key=profile, db_path=db)
        records = list_reports(db_path=db)
        assert len(records) == len(profiles)

    def test_SI09_db_indexed_fields_extracted(self, tmp_path):
        """appraiser_name and market_value must be indexed from the DTO."""
        db = tmp_path / "idx.db"
        data = sample_report_data("legacy")
        rid = save_report(data, profile_key="legacy", db_path=db)
        rec = get_report(rid, db_path=db)
        assert rec.appraiser_name == "د. عبد الرؤوف محمد عبد الباقي"
        assert rec.market_value == pytest.approx(2_478_153)


# ── 4. Full Pipeline — validate → pdf → save → get → list ────────────

class TestEndToEndPipeline:
    @pytest.mark.parametrize("profile", all_profiles())
    def test_SI10_full_pipeline(self, tmp_path, profile):
        """Complete intended flow for each profile, top-to-bottom.

        1. validate  → zero ERRORs
        2. generate  → valid PDF on disk
        3. persist   → save_report returns a non-empty id
        4. retrieve  → get_report round-trips data byte-identically
        5. confirm   → report appears in list_reports results
        """
        data = sample_report_data(profile)
        db = tmp_path / f"pipeline_{profile}.db"
        pdf_out = tmp_path / f"pipeline_{profile}.pdf"

        # 1. Validate
        result = validate_report(data, profile_key=profile)
        assert result.is_valid, (
            f"{profile}: validation errors = "
            f"{[i.code for i in result.errors]}"
        )

        # 2. Generate PDF
        generate_pdf(profile_key=profile, data=data, output_path=pdf_out)
        assert pdf_out.exists()
        assert pdf_out.read_bytes()[:4] == b"%PDF"

        # 3. Persist
        rid = save_report(data, profile_key=profile,
                          status="final", db_path=db)
        assert isinstance(rid, str) and rid

        # 4. Retrieve + round-trip fidelity
        rec = get_report(rid, db_path=db)
        assert rec is not None
        assert rec.data == data
        assert rec.status == "final"
        assert rec.profile_key == profile

        # 5. Confirm in listing
        listed = list_reports(profile_key=profile, db_path=db)
        assert any(r.report_id == rid for r in listed)
