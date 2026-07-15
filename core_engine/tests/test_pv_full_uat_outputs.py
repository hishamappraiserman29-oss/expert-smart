# -*- coding: utf-8 -*-
"""
test_pv_full_uat_outputs.py
Professional Valuation Full UAT Backend Tests (PVFUAT-B01 through B28).

Tests:
  B01-B06  Fixture loading and validation
  B07-B12  Unified page context coverage
  B13-B16  Report registry and output permissions
  B17-B22  Advisory enforcement and certification gates
  B23-B27  Excel legacy sheet preservation audit
  B28      No internal paths in output contexts
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.chdir(str(_CORE))

from bridge_api import app as _app

_TEST_SECRET = "pvr-phase-b-test-secret-32chars!!"
_UAT_BASE    = _CORE / "instance" / "manual_review_outputs" / "professional_valuation_full_uat_outputs"
_FIXTURE_DIR = _UAT_BASE / "fixtures"
_EXCEL_DIR   = _UAT_BASE / "excel_outputs"


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", _TEST_SECRET)
    monkeypatch.delenv("JWT_TTL_SECONDS", raising=False)


@pytest.fixture(scope="module")
def client():
    _app.config["TESTING"] = True
    with _app.test_client() as c:
        yield c


def _submit(client, payload: dict | None = None):
    default = {
        "client_name":       "اختبار UAT الكامل",
        "property_type":     "شقة سكنية",
        "valuation_purpose": "قيمة سوقية",
        "city":              "الرياض",
        "district":          "العليا",
        "input_mode":        "manual",
        "report_type":       "professional_report",
    }
    if payload:
        default.update(payload)
    resp = client.post(
        "/api/professional-valuation/requests",
        json=default,
        content_type="application/json",
    )
    assert resp.status_code == 201, (
        f"Submit failed {resp.status_code}: {resp.get_data(as_text=True)[:300]}"
    )
    return resp.get_json()


# ── B01-B06: Fixture loading ──────────────────────────────────────────────────

class TestFixtureLoading:
    """B01-B06: All fixture files load correctly and contain required fields."""

    REQUIRED_FIXTURES = [
        "zamalek_apartment_market_fixture",
        "nasr_city_rental_market_fixture",
        "padel_court_market_fixture",
        "obour_industrial_land_fixture",
        "cairo_hotel_market_fixture",
        "standards_ivsc_uspap_fixture",
    ]

    def _load(self, fixture_key: str) -> dict:
        f = _FIXTURE_DIR / f"{fixture_key}.json"
        assert f.exists(), f"Fixture file missing: {fixture_key}.json"
        return json.loads(f.read_text(encoding="utf-8"))

    def test_PVFUAT_B01_all_fixture_files_exist(self):
        """B01: All 6 required fixture files exist."""
        for key in self.REQUIRED_FIXTURES:
            f = _FIXTURE_DIR / f"{key}.json"
            assert f.exists(), f"Missing fixture: {key}.json"

    def test_PVFUAT_B02_fixtures_have_required_fields(self):
        """B02: Each fixture has source_label, source_type, source_date, data_is_fixture, advisory_only."""
        for key in self.REQUIRED_FIXTURES:
            data = self._load(key)
            for field in ("source_label", "source_type", "source_date", "data_is_fixture", "advisory_only"):
                assert field in data, f"Fixture {key} missing field: {field}"

    def test_PVFUAT_B03_fixtures_are_marked_advisory_only(self):
        """B03: All fixtures have advisory_only=True and data_is_fixture=True."""
        for key in self.REQUIRED_FIXTURES:
            data = self._load(key)
            assert data.get("advisory_only") is True, f"Fixture {key}: advisory_only must be True"
            assert data.get("data_is_fixture") is True, f"Fixture {key}: data_is_fixture must be True"

    def test_PVFUAT_B04_fixtures_not_live_data(self):
        """B04: Fixture source_type is 'controlled_uat_fixture', not live data."""
        for key in self.REQUIRED_FIXTURES:
            data = self._load(key)
            src_type = data.get("source_type", "")
            assert "live" not in src_type.lower(), f"Fixture {key}: source_type must not be live data"
            assert "api" not in src_type.lower(), f"Fixture {key}: source_type must not be live API"

    def test_PVFUAT_B05_zamalek_fixture_has_comparables(self):
        """B05: Zamalek apartment fixture has comparables list."""
        data = self._load("zamalek_apartment_market_fixture")
        assert "comparables" in data
        assert len(data["comparables"]) >= 2

    def test_PVFUAT_B06_standards_fixture_has_ivs_and_uspap(self):
        """B06: Standards fixture has both ivs_ivsc_context and uspap_context."""
        data = self._load("standards_ivsc_uspap_fixture")
        assert "ivs_ivsc_context" in data
        assert "uspap_context" in data
        assert data.get("final_compliance_claim") is False
        assert data.get("expert_review_required") is True


# ── B07-B12: Unified page context coverage ────────────────────────────────────

class TestUnifiedPageContextCoverage:
    """B07-B12: unified_professional_valuation_page_context covers all required sections."""

    def test_PVFUAT_B07_unified_context_in_response(self, client):
        """B07: POST response includes unified_professional_valuation_page_context."""
        body = _submit(client)
        assert "unified_professional_valuation_page_context" in body, (
            "unified_professional_valuation_page_context missing from POST response"
        )

    def test_PVFUAT_B08_unified_context_has_section2(self, client):
        """B08: Unified context includes section2_asset_context."""
        body   = _submit(client)
        ctx    = body.get("unified_professional_valuation_page_context", {})
        assert "section2_asset_context" in ctx, "Missing section2_asset_context"

    def test_PVFUAT_B09_unified_context_has_section3(self, client):
        """B09: Unified context includes section3_purpose_scope_context."""
        body = _submit(client)
        ctx  = body.get("unified_professional_valuation_page_context", {})
        assert "section3_purpose_scope_context" in ctx, "Missing section3_purpose_scope_context"

    def test_PVFUAT_B10_unified_context_has_section4(self, client):
        """B10: Unified context includes section4_standards_context."""
        body = _submit(client)
        ctx  = body.get("unified_professional_valuation_page_context", {})
        assert "section4_standards_context" in ctx, "Missing section4_standards_context"

    def test_PVFUAT_B11_unified_context_has_chat_and_upload(self, client):
        """B11: Unified context includes chat and upload sub-contexts."""
        body = _submit(client)
        ctx  = body.get("unified_professional_valuation_page_context", {})
        for key in ("chat_instruction_context", "property_docs_context",
                    "simulation_report_context", "review_report_context"):
            assert key in ctx, f"Missing key in unified context: {key}"

    def test_PVFUAT_B12_unified_context_is_advisory_only(self, client):
        """B12: Unified context has advisory_only=True and certification_gate_context."""
        body = _submit(client)
        ctx  = body.get("unified_professional_valuation_page_context", {})
        assert ctx.get("advisory_only") is True, "advisory_only must be True"
        assert "certification_gate_context" in ctx, "Missing certification_gate_context"


# ── B13-B16: Report registry and output permissions ──────────────────────────

class TestReportRegistryAndOutputPermissions:
    """B13-B16: Report registry contains required types; output permissions correct."""

    def test_PVFUAT_B13_traditional_report_accepted(self, client):
        """B13: traditional_report is accepted as valid report_type."""
        body = _submit(client, {"report_type": "traditional_report"})
        assert "request_id" in body

    def test_PVFUAT_B14_detailed_report_accepted(self, client):
        """B14: detailed_report is accepted as valid report_type."""
        body = _submit(client, {"report_type": "detailed_report"})
        assert "request_id" in body

    def test_PVFUAT_B15_professional_report_accepted(self, client):
        """B15: professional_report is accepted as valid report_type."""
        body = _submit(client, {"report_type": "professional_report"})
        assert "request_id" in body

    def test_PVFUAT_B16_chat_command_center_has_upload_registry(self, client):
        """B16: POST response contains chat_command_center_context with upload_purpose_registry."""
        body = _submit(client)
        ccc = body.get("chat_command_center_context", {})
        assert "upload_purpose_registry" in ccc, (
            "upload_purpose_registry missing from chat_command_center_context"
        )


# ── B17-B22: Advisory enforcement and certification gates ─────────────────────

class TestAdvisoryEnforcementAndCertificationGates:
    """B17-B22: Advisory flags set correctly; certified outputs gated."""

    def test_PVFUAT_B17_response_advisory_only_true(self, client):
        """B17: unified context advisory_only=True for uncertified requests."""
        body = _submit(client)
        ctx  = body.get("unified_professional_valuation_page_context", {})
        assert ctx.get("advisory_only") is True

    def test_PVFUAT_B18_certification_ready_false_by_default(self, client):
        """B18: New request has certification_ready=False."""
        body = _submit(client)
        ctx  = body.get("unified_professional_valuation_page_context", {})
        gate = ctx.get("certification_gate_context", {})
        assert gate.get("certification_ready") is False

    def test_PVFUAT_B19_final_outputs_not_allowed_when_uncertified(self, client):
        """B19: final_outputs_allowed=False when certification_ready=False."""
        body = _submit(client)
        ctx  = body.get("unified_professional_valuation_page_context", {})
        gate = ctx.get("certification_gate_context", {})
        assert gate.get("final_outputs_allowed") is False

    def test_PVFUAT_B20_chat_command_center_shows_output_permissions(self, client):
        """B20: chat_command_center_context shows output_permissions with advisory controls."""
        body = _submit(client)
        ccc  = body.get("chat_command_center_context", {})
        # admin_excel should not be visible to public user
        assert ccc.get("admin_excel_visible_to_current_user") is False, (
            "admin_excel_visible_to_current_user must be False for non-admin"
        )

    def test_PVFUAT_B21_simulation_not_real_training(self, client):
        """B21: simulation_report_context has not_real_training=True."""
        body = _submit(client)
        ctx  = body.get("unified_professional_valuation_page_context", {})
        sim  = ctx.get("simulation_report_context", {})
        assert sim.get("not_real_training") is True, "not_real_training must be True for simulation"

    def test_PVFUAT_B22_review_report_advisory_only(self, client):
        """B22: review_report_context has advisory_review_only=True."""
        body = _submit(client)
        ctx  = body.get("unified_professional_valuation_page_context", {})
        rev  = ctx.get("review_report_context", {})
        assert rev.get("advisory_review_only") is True, "advisory_review_only must be True for review report"


# ── B23-B27: Excel legacy sheet preservation audit ────────────────────────────

class TestExcelLegacySheetPreservationAudit:
    """B23-B27: UAT workbooks preserve all 44 legacy sheets."""

    @pytest.fixture(scope="class")
    def workbook_audits(self):
        """Build UAT workbooks and return audits."""
        from professional_valuation_uat_workbook import build_all_uat_workbooks
        return build_all_uat_workbooks()

    def test_PVFUAT_B23_deleted_legacy_sheets_is_empty(self, workbook_audits):
        """B23: deleted_legacy_sheets = [] for all UAT workbooks."""
        for audit in workbook_audits:
            assert audit["deleted_legacy_sheets"] == [], (
                f"Scenario {audit['scenario_key']}: deleted_legacy_sheets must be []"
            )

    def test_PVFUAT_B24_generated_sheet_count_gte_44(self, workbook_audits):
        """B24: Generated workbook sheet count >= 44 (legacy count)."""
        for audit in workbook_audits:
            assert audit["generated_sheet_count_after"] >= 44, (
                f"Scenario {audit['scenario_key']}: "
                f"sheet count {audit['generated_sheet_count_after']} < 44 legacy sheets"
            )

    def test_PVFUAT_B25_legacy_sheet_map_created(self, workbook_audits):
        """B25: Legacy sheet map sheet created in all UAT workbooks."""
        for audit in workbook_audits:
            assert audit["legacy_sheet_map_created"] is True, (
                f"Scenario {audit['scenario_key']}: legacy_sheet_map_created must be True"
            )

    def test_PVFUAT_B26_preservation_pass_true(self, workbook_audits):
        """B26: preservation_pass=True for all UAT workbooks."""
        for audit in workbook_audits:
            assert audit["preservation_pass"] is True, (
                f"Scenario {audit['scenario_key']}: preservation_pass must be True"
            )

    def test_PVFUAT_B27_workbook_files_exist(self, workbook_audits):
        """B27: All 4 UAT workbook files were created successfully."""
        assert len(workbook_audits) == 4, "Expected 4 UAT workbook scenarios"
        for audit in workbook_audits:
            xlsx_name = audit["output_path"]
            f = _EXCEL_DIR / xlsx_name
            assert f.exists(), f"Workbook file missing: {xlsx_name}"
            assert f.stat().st_size > 5000, f"Workbook {xlsx_name} too small (may be corrupt)"


# ── B28: No internal paths in output contexts ─────────────────────────────────

class TestNoInternalPathsInOutputContexts:
    """B28: No internal file paths exposed in API responses."""

    def test_PVFUAT_B28_no_internal_paths_in_unified_context(self, client):
        """B28: unified_professional_valuation_page_context contains no internal paths."""
        body     = _submit(client)
        body_str = json.dumps(body)
        forbidden_patterns = [
            "C:\\", "c:\\", "/home/", "/root/", "/var/",
            "core_engine\\instance", "core_engine/instance",
            "internal_file_path",
        ]
        for pat in forbidden_patterns:
            assert pat not in body_str, (
                f"Internal path pattern '{pat}' found in API response"
            )
