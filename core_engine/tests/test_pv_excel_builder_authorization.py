"""
Excel builder invocation authorization tests.

Covers the Step 2 fix from USER_ADMIN_REPORT_FORMATS_BLOCKER_CLOSURE:
Excel generation must occur only for administrator users.
Normal users must receive zero Excel builder calls and zero Excel files.

Tests: EBA-01 through EBA-18
"""
from __future__ import annotations

import os
import sys
import pathlib
import re
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(str(_CORE))

from bridge_api import app  # noqa: E402
from auth.tokens import generate_token  # noqa: E402

BRIDGE = _CORE / "bridge_api.py"

_NORMAL_USER = "eba-normal-user"
_ADMIN_USER  = "eba-admin-user"
_TEST_SECRET = "eba-test-secret-for-builder"

_ADV_STUB = {"market_value": 1_800_000.0, "confidence": "عالية"}

_MINIMAL = {
    "location":        "الرياض",
    "area":            200,
    "property_type":   "شقة",
    "price_per_meter": 9_000,
    "report_style":    "legacy",
}

_URA_PAYLOAD = {
    **_MINIMAL,
    "unified_report_action": "detailed_report",
}


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET",      _TEST_SECRET)
    monkeypatch.setenv("ADMIN_USER_IDS",  _ADMIN_USER)
    monkeypatch.delenv("JWT_TTL_SECONDS", raising=False)


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _normal_headers() -> dict:
    return {"Authorization": f"Bearer {generate_token(_NORMAL_USER)}",
            "Content-Type": "application/json"}


def _admin_headers() -> dict:
    return {"Authorization": f"Bearer {generate_token(_ADMIN_USER)}",
            "Content-Type": "application/json"}


def _bridge_src() -> str:
    return BRIDGE.read_text(encoding="utf-8")


def _handle_valuation_body(src: str) -> str:
    """Extract handle_valuation function body from bridge_api source."""
    start = src.find("def handle_valuation():")
    match = re.search(r"\n@app\.route", src[start:])
    end = (start + match.start()) if match else len(src)
    return src[start:end]


# ─────────────────────────────────────────────────────────────────────────────
# SOURCE-STRUCTURE TESTS  (verify the admin-gate fix was applied)
# ─────────────────────────────────────────────────────────────────────────────

class TestExcelBuilderStructure:
    """Source-level proof that Excel generation is inside the admin gate."""

    def test_EBA01_name_initialized_to_none(self):
        """name variable must be initialized to None before any role check."""
        body = _handle_valuation_body(_bridge_src())
        assert "name         = None" in body or "name = None" in body, (
            "name not initialized to None — non-admin code paths would be broken"
        )

    def test_EBA02_admin_gate_wraps_excel_generation(self):
        """if _is_admin block must immediately precede the report_style branch."""
        body = _handle_valuation_body(_bridge_src())
        gate = "        if _is_admin(g.user_id):\n            if report_style"
        assert gate in body, (
            "Excel generation is not inside 'if _is_admin(g.user_id):' block. "
            "Structural fix from Step 2 is not present."
        )

    def test_EBA03_write_to_excel_not_at_function_body_level(self):
        """write_to_excel_template must not appear at 8-space (function-body) indentation."""
        body = _handle_valuation_body(_bridge_src())
        # Line-anchored check: finds write_to_excel_template at exactly 8 spaces
        # (= unconditional in handle_valuation's try block, before any inner if)
        match = re.search(r"(?m)^\s{8}write_to_excel_template\(", body)
        assert match is None, (
            "write_to_excel_template found at function-body indentation (8 spaces) — "
            "it runs for ALL users, not admin-only."
        )

    def test_EBA04_excel_generation_indented_beyond_admin_gate(self):
        """write_to_excel_template calls must be at 16+ space indent (inside admin + style blocks)."""
        body = _handle_valuation_body(_bridge_src())
        calls = re.findall(r"(?m)^( +)write_to_excel_template\(", body)
        for indent in calls:
            assert len(indent) >= 16, (
                f"write_to_excel_template at {len(indent)}-space indent — "
                "expected ≥16 (inside admin gate and report_style block)"
            )

    def test_EBA05_build_iv_inside_admin_gate(self):
        """build_individual_valuation_report must only be reachable via admin gate."""
        body = _handle_valuation_body(_bridge_src())
        if "_build_iv(" not in body:
            pytest.skip("_build_iv not in handle_valuation body")
        # Line-anchored: captures leading whitespace for lines starting with _build_iv
        calls = re.findall(r"(?m)^( +)_build_iv\(", body)
        for indent in calls:
            assert len(indent) >= 20, (
                f"_build_iv at {len(indent)}-space indent — expected ≥20 "
                "(inside admin gate + report_style + try blocks)"
            )

    def test_EBA06_excel_url_still_admin_gated_in_response(self):
        """excel_url assignment in resp must remain inside is_admin check."""
        src = _bridge_src()
        pattern = r'if _is_admin\(g\.user_id\):\s+resp\["excel_url"\]'
        assert re.search(pattern, src), (
            "resp[\"excel_url\"] is not inside an is_admin check"
        )

    def test_EBA07_formats_excel_still_admin_gated(self):
        """formats.excel block in resp must remain inside is_admin check."""
        src = _bridge_src()
        pattern = r'if _is_admin\(g\.user_id\):\s+resp\["formats"\]\["excel"\]'
        assert re.search(pattern, src), (
            "resp[\"formats\"][\"excel\"] is not inside an is_admin check"
        )


# ─────────────────────────────────────────────────────────────────────────────
# RUNTIME MOCK TESTS  (verify no Excel builder call for normal users)
# ─────────────────────────────────────────────────────────────────────────────

class TestExcelBuilderInvocation:
    """Runtime proof that Excel builder call count differs by role."""

    def test_EBA08_normal_user_excel_builder_call_count_zero(self, client):
        """Normal user: write_to_excel_template must not be called."""
        with patch("bridge_api.write_to_excel_template") as mock_wte, \
             patch("bridge_api.write_word_summary"), \
             patch("bridge_api.advanced_valuation", return_value=_ADV_STUB), \
             patch("bridge_api._remove_legacy_advanced_sheets"):
            resp = client.post("/api/valuation",
                               json=_MINIMAL,
                               headers=_normal_headers())
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            assert mock_wte.call_count == 0, (
                f"write_to_excel_template called {mock_wte.call_count} time(s) "
                "for a normal user — Excel generation must be admin-only"
            )

    def test_EBA09_admin_user_excel_builder_called(self, client):
        """Admin user: write_to_excel_template must be called at least once."""
        with patch("bridge_api.write_to_excel_template") as mock_wte, \
             patch("bridge_api.write_word_summary"), \
             patch("bridge_api.advanced_valuation", return_value=_ADV_STUB), \
             patch("bridge_api._remove_legacy_advanced_sheets"):
            resp = client.post("/api/valuation",
                               json=_MINIMAL,
                               headers=_admin_headers())
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            assert mock_wte.call_count >= 1, (
                "write_to_excel_template was NOT called for an admin user — "
                "admin must receive Excel workbook generation"
            )

    def test_EBA10_normal_user_no_excel_url_in_response(self, client):
        """Normal user API response must not contain excel_url."""
        with patch("bridge_api.write_to_excel_template"), \
             patch("bridge_api.write_word_summary"), \
             patch("bridge_api.advanced_valuation", return_value=_ADV_STUB), \
             patch("bridge_api._remove_legacy_advanced_sheets"):
            resp = client.post("/api/valuation",
                               json=_MINIMAL,
                               headers=_normal_headers())
            data = resp.get_json()
            assert "excel_url" not in data, (
                f"excel_url present in normal-user response: {data.get('excel_url')}"
            )

    def test_EBA11_normal_user_no_formats_excel_in_response(self, client):
        """Normal user API response must not contain formats.excel."""
        with patch("bridge_api.write_to_excel_template"), \
             patch("bridge_api.write_word_summary"), \
             patch("bridge_api.advanced_valuation", return_value=_ADV_STUB), \
             patch("bridge_api._remove_legacy_advanced_sheets"):
            resp = client.post("/api/valuation",
                               json=_URA_PAYLOAD,
                               headers=_normal_headers())
            data = resp.get_json()
            formats = data.get("formats") or {}
            assert "excel" not in formats, (
                f"formats.excel present in normal-user response: {formats.get('excel')}"
            )

    def test_EBA12_admin_user_excel_url_in_response(self, client):
        """Admin user API response must contain excel_url."""
        with patch("bridge_api.write_to_excel_template"), \
             patch("bridge_api.write_word_summary"), \
             patch("bridge_api.advanced_valuation", return_value=_ADV_STUB), \
             patch("bridge_api._remove_legacy_advanced_sheets"):
            resp = client.post("/api/valuation",
                               json=_MINIMAL,
                               headers=_admin_headers())
            data = resp.get_json()
            assert "excel_url" in data, "excel_url missing from admin response"

    def test_EBA13_pdf_html_succeed_for_normal_user(self, client):
        """PDF and HTML generation must still succeed for a normal user."""
        with patch("bridge_api.write_to_excel_template"), \
             patch("bridge_api.write_word_summary"), \
             patch("bridge_api.advanced_valuation", return_value=_ADV_STUB), \
             patch("bridge_api._remove_legacy_advanced_sheets"), \
             patch("bridge_api._gen_html", create=True) as _mh, \
             patch("bridge_api._rtp",      create=True) as _mp:
            resp = client.post("/api/valuation",
                               json=_URA_PAYLOAD,
                               headers=_normal_headers())
            data = resp.get_json()
            assert resp.status_code == 200
            assert data.get("status") == "success"


# ─────────────────────────────────────────────────────────────────────────────
# DOWNLOAD ENDPOINT AUTHORIZATION TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestDownloadAuthorization:
    """Runtime proof that download endpoint enforces Excel access control."""

    def test_EBA14_normal_user_xlsx_download_403(self, client):
        """Normal user must receive HTTP 403 for .xlsx download."""
        resp = client.get("/api/download/Report_test.xlsx",
                          headers=_normal_headers())
        assert resp.status_code == 403

    def test_EBA15_normal_user_xlsm_download_403(self, client):
        """Normal user must receive HTTP 403 for .xlsm download."""
        resp = client.get("/api/download/Report_test.xlsm",
                          headers=_normal_headers())
        assert resp.status_code == 403

    def test_EBA16_403_response_no_local_path(self, client):
        """HTTP 403 response body must not expose a local filesystem path."""
        resp = client.get("/api/download/Report_test.xlsx",
                          headers=_normal_headers())
        body = resp.get_data(as_text=True)
        assert "C:\\" not in body, "Windows path in 403 response"
        assert "/home/" not in body, "Unix home path in 403 response"
        assert "core_engine" not in body, "core_engine path in 403 response"
        assert "OUTPUTS" not in body, "OUTPUTS variable name in 403 response"

    def test_EBA17_normal_user_path_traversal_rejected(self, client):
        """Path traversal via filename must be rejected (400/403/404, no 200)."""
        paths = [
            "..%2F..%2Fetc%2Fpasswd",
            "Report%5C..%5C..%5Cpasswd",
            "../../../etc/passwd",
        ]
        for p in paths:
            resp = client.get(f"/api/download/{p}",
                              headers=_normal_headers())
            assert resp.status_code in (400, 403, 404), (
                f"Path traversal '{p}' returned {resp.status_code} — expected 400/403/404"
            )

    def test_EBA18_admin_xlsx_not_blocked_at_gate(self, client):
        """Admin user must not receive 403 for .xlsx (may 404 for nonexistent file)."""
        resp = client.get("/api/download/NonExistent_admin_file.xlsx",
                          headers=_admin_headers())
        assert resp.status_code != 403, (
            f"Admin received 403 for xlsx download — authorization gate too aggressive. "
            f"Status: {resp.status_code}"
        )
