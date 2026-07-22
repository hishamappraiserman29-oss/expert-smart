"""
Excel builder invocation authorization tests.

Covers the Step 2 fix from USER_ADMIN_REPORT_FORMATS_BLOCKER_CLOSURE:
Excel generation must occur only for administrator users.
Normal users must receive zero Excel builder calls and zero Excel files.

Tests: EBA-01 through EBA-30
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

_ORIG_CWD = os.getcwd()
try:
    os.chdir(str(_CORE))

    from bridge_api import app  # noqa: E402
    from auth.tokens import generate_token  # noqa: E402

finally:
    os.chdir(_ORIG_CWD)

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


# ── Helpers for physical-validation tests ─────────────────────────────────────

def _file_creating_mock(sheet_count: int):
    """Return a _build_55_sheet side_effect that writes a real xlsx to output_path.

    This ensures the post-generation physical validation in bridge_api can open
    the file.  Tests that need the validation to PASS use sheet_count=55;
    tests that need it to REJECT use a lower count.
    """
    import openpyxl as _opx_helper

    def _mock(ctx, output_path, *, request_id=None, **kwargs):
        wb = _opx_helper.Workbook()
        wb.remove(wb.active)
        for i in range(sheet_count):
            wb.create_sheet(title=f"Sheet{i + 1}")
        os.makedirs(os.path.dirname(str(output_path)), exist_ok=True)
        wb.save(str(output_path))
        wb.close()
        return {"success": True, "sheet_count": sheet_count, "errors": []}

    return _mock


@pytest.fixture()
def tmp_outputs(tmp_path, monkeypatch):
    """Redirect bridge_api.OUTPUTS to an isolated temp dir for this test."""
    monkeypatch.setattr("bridge_api.OUTPUTS", str(tmp_path))
    return tmp_path


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
        assert re.search(r"\bname\s+=\s+None", body), (
            "name not initialized to None — non-admin code paths would be broken"
        )

    def test_EBA02_admin_gate_wraps_excel_generation(self):
        """55-sheet builder must be invoked only inside the admin gate."""
        body = _handle_valuation_body(_bridge_src())
        idx_gate = body.find("        if _is_admin(g.user_id):")
        assert idx_gate != -1, "admin gate 'if _is_admin(g.user_id):' not found in handle_valuation"
        idx_builder = body.find("_build_55_sheet(")
        assert idx_builder != -1, "_build_55_sheet() call not found in handle_valuation"
        # Find the next statement at the same (8-space) indentation level after the gate
        next_same = re.search(r"\n        [^\s]", body[idx_gate + 1:])
        idx_end = (idx_gate + 1 + next_same.start()) if next_same else len(body)
        assert idx_gate < idx_builder < idx_end, (
            "_build_55_sheet is not inside 'if _is_admin(g.user_id):' block — "
            "Excel generation must be admin-only"
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
        """_build_55_sheet call must be at 16+ space indent (inside admin gate + try block)."""
        body = _handle_valuation_body(_bridge_src())
        # Match lines whose non-whitespace content contains _build_55_sheet(
        calls = re.findall(r"(?m)^( +)\S[^\n]*_build_55_sheet\(", body)
        assert calls, "_build_55_sheet not called in handle_valuation body"
        for indent in calls:
            assert len(indent) >= 16, (
                f"_build_55_sheet at {len(indent)}-space indent — "
                "expected ≥16 (inside admin gate and try block)"
            )

    def test_EBA05_build_iv_inside_admin_gate(self):
        """55-sheet builder call must only be reachable inside the admin gate."""
        body = _handle_valuation_body(_bridge_src())
        # Support both current (_build_55_sheet) and legacy (_build_iv) builder names
        if "_build_55_sheet(" in body:
            lines = [ln for ln in body.splitlines() if "_build_55_sheet(" in ln]
            for ln in lines:
                indent = len(ln) - len(ln.lstrip())
                assert indent >= 16, (
                    f"_build_55_sheet at {indent}-space indent — expected ≥16 "
                    "(inside admin gate and try block)"
                )
            return
        if "_build_iv(" not in body:
            pytest.skip("neither _build_55_sheet nor _build_iv in handle_valuation body")
        lines = [ln for ln in body.splitlines() if "_build_iv(" in ln]
        for ln in lines:
            indent = len(ln) - len(ln.lstrip())
            assert indent >= 20, (
                f"_build_iv at {indent}-space indent — expected ≥20 "
                "(inside admin gate + report_style + try blocks)"
            )

    def test_EBA06_excel_url_still_admin_gated_in_response(self):
        """excel_url assignment in resp must remain inside is_admin check."""
        src = _bridge_src()
        # Allow for additional conditions (e.g. 'and name is not None')
        pattern = r'if _is_admin\(g\.user_id\)[^:]*:\s+resp\["excel_url"\]'
        assert re.search(pattern, src), (
            "resp[\"excel_url\"] is not inside an is_admin check"
        )

    def test_EBA07_formats_excel_still_admin_gated(self):
        """formats.excel block in resp must remain inside is_admin check."""
        body = _handle_valuation_body(_bridge_src())
        # formats.excel may be set inside a nested if (e.g. 'if name is not None')
        # that itself sits inside the is_admin block.  Verify positional ordering.
        idx_admin = body.find("            if _is_admin(g.user_id):")
        assert idx_admin != -1, "_is_admin check not found in formats section"
        idx_formats = body.find('resp["formats"]["excel"]')
        assert idx_formats != -1, 'resp["formats"]["excel"] not found in handle_valuation'
        assert idx_admin < idx_formats, (
            'resp["formats"]["excel"] is not after the is_admin check — '
            "formats.excel must be admin-only"
        )


# ─────────────────────────────────────────────────────────────────────────────
# RUNTIME MOCK TESTS  (verify no Excel builder call for normal users)
# ─────────────────────────────────────────────────────────────────────────────

class TestExcelBuilderInvocation:
    """Runtime proof that Excel builder call count differs by role."""

    def test_EBA08_normal_user_excel_builder_call_count_zero(self, client):
        """Normal user: _build_55_sheet must not be called."""
        with patch("bridge_api._build_55_sheet") as mock_55, \
             patch("bridge_api.write_word_summary"), \
             patch("bridge_api.advanced_valuation", return_value=_ADV_STUB):
            resp = client.post("/api/valuation",
                               json=_MINIMAL,
                               headers=_normal_headers())
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            assert mock_55.call_count == 0, (
                f"_build_55_sheet called {mock_55.call_count} time(s) "
                "for a normal user — Excel generation must be admin-only"
            )

    def test_EBA09_admin_user_excel_builder_called(self, client, tmp_outputs):
        """Admin user: _build_55_sheet must be called at least once."""
        with patch("bridge_api._build_55_sheet",
                   side_effect=_file_creating_mock(55)) as mock_55, \
             patch("bridge_api.write_word_summary"), \
             patch("bridge_api.advanced_valuation", return_value=_ADV_STUB):
            resp = client.post("/api/valuation",
                               json=_MINIMAL,
                               headers=_admin_headers())
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            assert mock_55.call_count >= 1, (
                "_build_55_sheet was NOT called for an admin user — "
                "admin must receive 55-sheet Excel workbook generation"
            )

    def test_EBA10_normal_user_no_excel_url_in_response(self, client):
        """Normal user API response must not contain excel_url."""
        with patch("bridge_api._build_55_sheet") as mock_55, \
             patch("bridge_api.write_word_summary"), \
             patch("bridge_api.advanced_valuation", return_value=_ADV_STUB):
            resp = client.post("/api/valuation",
                               json=_MINIMAL,
                               headers=_normal_headers())
            data = resp.get_json()
            assert "excel_url" not in data, (
                f"excel_url present in normal-user response: {data.get('excel_url')}"
            )
            assert mock_55.call_count == 0, (
                "_build_55_sheet called for normal user — must be admin-only"
            )

    def test_EBA11_normal_user_no_formats_excel_in_response(self, client):
        """Normal user API response must not contain formats.excel."""
        with patch("bridge_api._build_55_sheet") as mock_55, \
             patch("bridge_api.write_word_summary"), \
             patch("bridge_api.advanced_valuation", return_value=_ADV_STUB):
            resp = client.post("/api/valuation",
                               json=_URA_PAYLOAD,
                               headers=_normal_headers())
            data = resp.get_json()
            formats = data.get("formats") or {}
            assert "excel" not in formats, (
                f"formats.excel present in normal-user response: {formats.get('excel')}"
            )
            assert mock_55.call_count == 0, (
                "_build_55_sheet called for normal user — must be admin-only"
            )

    def test_EBA12_admin_user_excel_url_in_response(self, client, tmp_outputs):
        """Admin user API response must contain excel_url when builder succeeds."""
        with patch("bridge_api._build_55_sheet",
                   side_effect=_file_creating_mock(55)), \
             patch("bridge_api.write_word_summary"), \
             patch("bridge_api.advanced_valuation", return_value=_ADV_STUB):
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


# ─────────────────────────────────────────────────────────────────────────────
# 55-SHEET INTEGRATION METADATA TESTS  (verify sheetCount is not hardcoded)
# ─────────────────────────────────────────────────────────────────────────────

class TestExcel55SheetMetadata:
    """Verify sheetCount is derived from the actual workbook, not hardcoded."""

    def test_EBA19_sheetCount_not_hardcoded_in_source(self):
        """sheetCount must not be the literal integer 55 in the source."""
        src = _bridge_src()
        assert '"sheetCount":  55' not in src and '"sheetCount": 55' not in src, (
            "sheetCount is hardcoded as 55 — must be derived from actual workbook sheet_count"
        )

    def test_EBA20_api_sheetCount_matches_physical_sheet_count(self, client, tmp_outputs):
        """API sheetCount must equal the physical workbook count (not builder result field)."""
        with patch("bridge_api._build_55_sheet",
                   side_effect=_file_creating_mock(55)), \
             patch("bridge_api.write_word_summary"), \
             patch("bridge_api.advanced_valuation", return_value=_ADV_STUB):
            resp = client.post("/api/valuation",
                               json=_URA_PAYLOAD,
                               headers=_admin_headers())
            data = resp.get_json()
            excel_meta = (data.get("formats") or {}).get("excel") or {}
            assert excel_meta.get("sheetCount") == 55, (
                f"Expected sheetCount=55 (from physical workbook), "
                f"got {excel_meta.get('sheetCount')}"
            )

    def test_EBA21_failed_builder_returns_generated_false(self, client):
        """When builder fails, formats.excel.generated must be False."""
        _mock_failure = {"success": False, "sheet_count": 0, "errors": ["template not found"]}
        with patch("bridge_api._build_55_sheet", return_value=_mock_failure), \
             patch("bridge_api.write_word_summary"), \
             patch("bridge_api.advanced_valuation", return_value=_ADV_STUB):
            resp = client.post("/api/valuation",
                               json=_URA_PAYLOAD,
                               headers=_admin_headers())
            data = resp.get_json()
            excel_meta = (data.get("formats") or {}).get("excel") or {}
            assert excel_meta.get("generated") is False, (
                f"generated should be False on builder failure, got {excel_meta.get('generated')}"
            )
            assert excel_meta.get("sheetCount") == 0, (
                f"sheetCount should be 0 on builder failure, got {excel_meta.get('sheetCount')}"
            )

    def test_EBA22_failed_builder_no_excel_url(self, client):
        """When builder fails, no excel_url is returned for admin."""
        _mock_failure = {"success": False, "sheet_count": 0, "errors": ["template missing"]}
        with patch("bridge_api._build_55_sheet", return_value=_mock_failure), \
             patch("bridge_api.write_word_summary"), \
             patch("bridge_api.advanced_valuation", return_value=_ADV_STUB):
            resp = client.post("/api/valuation",
                               json=_MINIMAL,
                               headers=_admin_headers())
            data = resp.get_json()
            assert "excel_url" not in data, (
                f"excel_url present despite builder failure: {data.get('excel_url')}"
            )

    def test_EBA23_physical_20sheet_workbook_is_rejected(self, client, tmp_outputs):
        """A physically 20-sheet workbook must be rejected (generated=False, no excel_url)."""
        with patch("bridge_api._build_55_sheet",
                   side_effect=_file_creating_mock(20)), \
             patch("bridge_api.write_word_summary"), \
             patch("bridge_api.advanced_valuation", return_value=_ADV_STUB):
            resp = client.post("/api/valuation",
                               json=_URA_PAYLOAD,
                               headers=_admin_headers())
            data = resp.get_json()
            excel_meta = (data.get("formats") or {}).get("excel") or {}
            assert excel_meta.get("generated") is False, (
                f"A 20-sheet workbook must be rejected; got generated={excel_meta.get('generated')}"
            )
            assert "excel_url" not in data, (
                "excel_url must be absent when physical sheet count ≠ 55"
            )
            assert excel_meta.get("sheetCount") != 55, (
                "sheetCount must NOT be 55 when the physical workbook has only 20 sheets"
            )


# ─────────────────────────────────────────────────────────────────────────────
# PHYSICAL VALIDATION TESTS  (post-generation validation rejects invalid workbooks)
# ─────────────────────────────────────────────────────────────────────────────

class TestPhysicalValidation:
    """Verify physical validation gate: reject < 55 sheets, clean up files."""

    def test_EBA24_physical_13sheet_workbook_is_rejected(self, client, tmp_outputs):
        """A physically 13-sheet workbook must be rejected (generated=False, no excel_url)."""
        with patch("bridge_api._build_55_sheet",
                   side_effect=_file_creating_mock(13)), \
             patch("bridge_api.write_word_summary"), \
             patch("bridge_api.advanced_valuation", return_value=_ADV_STUB):
            data = client.post("/api/valuation",
                               json=_URA_PAYLOAD,
                               headers=_admin_headers()).get_json()
            excel_meta = (data.get("formats") or {}).get("excel") or {}
            assert excel_meta.get("generated") is False, (
                "A 13-sheet workbook must be rejected by physical validation"
            )
            assert "excel_url" not in data, (
                "excel_url must be absent for a 13-sheet workbook"
            )
            assert excel_meta.get("sheetCount") != 13, (
                "A rejected workbook must not expose its invalid sheet count as 13"
            )

    def test_EBA25_invalid_workbook_file_removed_after_rejection(self, client, tmp_outputs):
        """After physical validation failure, the partial xlsx artifact must be deleted."""
        import glob as _glob
        with patch("bridge_api._build_55_sheet",
                   side_effect=_file_creating_mock(20)), \
             patch("bridge_api.write_word_summary"), \
             patch("bridge_api.advanced_valuation", return_value=_ADV_STUB):
            client.post("/api/valuation", json=_MINIMAL, headers=_admin_headers())
        # After the request, no .xlsx should remain in tmp_outputs (invalid file cleaned up)
        remaining = list(tmp_path_from(tmp_outputs, "*.xlsx"))
        assert remaining == [], (
            f"Invalid workbook was not cleaned up after physical validation failure: "
            f"{remaining}"
        )

    def test_EBA26_pdf_html_succeed_when_excel_physical_validation_fails(self, client, tmp_outputs):
        """PDF and HTML generation must succeed even when Excel physical validation fails."""
        with patch("bridge_api._build_55_sheet",
                   side_effect=_file_creating_mock(13)), \
             patch("bridge_api.write_word_summary"), \
             patch("bridge_api.advanced_valuation", return_value=_ADV_STUB):
            resp = client.post("/api/valuation",
                               json=_MINIMAL,
                               headers=_admin_headers())
        data = resp.get_json()
        assert resp.status_code == 200, (
            f"Response must be 200 even when Excel validation fails, got {resp.status_code}"
        )
        assert data.get("status") == "success", (
            "status must be 'success' even when Excel physical validation fails"
        )
        assert data.get("market_value", 0) > 0, (
            "market_value must be present even when Excel physical validation fails"
        )


def tmp_path_from(directory, pattern: str) -> list:
    """List files matching pattern in directory (helper for cleanup tests)."""
    import glob as _glob
    return _glob.glob(os.path.join(str(directory), pattern))


# ─────────────────────────────────────────────────────────────────────────────
# CONCURRENCY TESTS  (distinct filenames across simultaneous admin requests)
# ─────────────────────────────────────────────────────────────────────────────

class TestConcurrency:
    """Verify that two concurrent admin requests produce distinct output files."""

    def test_EBA27_two_admin_requests_produce_distinct_filenames(self, client, tmp_outputs):
        """Two admin requests must produce distinct Excel filenames (UUID-based)."""
        filenames = []

        def _capturing_mock(ctx, output_path, *, request_id=None, **kwargs):
            import openpyxl as _opx_c
            filenames.append(os.path.basename(str(output_path)))
            wb = _opx_c.Workbook()
            wb.remove(wb.active)
            for i in range(55):
                wb.create_sheet(title=f"Sheet{i + 1}")
            wb.save(str(output_path))
            wb.close()
            return {"success": True, "sheet_count": 55, "errors": []}

        with patch("bridge_api._build_55_sheet", side_effect=_capturing_mock), \
             patch("bridge_api.write_word_summary"), \
             patch("bridge_api.advanced_valuation", return_value=_ADV_STUB):
            resp1 = client.post("/api/valuation", json=_MINIMAL, headers=_admin_headers())
            resp2 = client.post("/api/valuation", json=_MINIMAL, headers=_admin_headers())

        assert resp1.status_code == 200 and resp2.status_code == 200
        assert len(filenames) == 2, f"Expected 2 builder calls, got {len(filenames)}"
        assert filenames[0] != filenames[1], (
            f"Two admin requests produced the same filename: {filenames[0]} — "
            "concurrent requests would overwrite each other"
        )

    def test_EBA28_each_response_points_to_own_workbook(self, client, tmp_outputs):
        """Each admin response excel_url must reference its own distinct workbook."""
        with patch("bridge_api._build_55_sheet",
                   side_effect=_file_creating_mock(55)), \
             patch("bridge_api.write_word_summary"), \
             patch("bridge_api.advanced_valuation", return_value=_ADV_STUB):
            data1 = client.post("/api/valuation", json=_MINIMAL,
                                headers=_admin_headers()).get_json()
            data2 = client.post("/api/valuation", json=_MINIMAL,
                                headers=_admin_headers()).get_json()

        url1 = data1.get("excel_url", "")
        url2 = data2.get("excel_url", "")
        assert url1 and url2, "Both admin responses must have excel_url"
        assert url1 != url2, (
            f"Both responses share the same excel_url: {url1} — "
            "each response must point to its own workbook"
        )


# ─────────────────────────────────────────────────────────────────────────────
# WORKBOOK CONTENT HYGIENE  (EBA29–EBA36)
# Saudi localization must eliminate all Egyptian geographic and QA content.
# Uses _egypt_infested_mock which creates Arabic-named sheets with Egyptian
# content, simulating a template-generated workbook before localization.
# ─────────────────────────────────────────────────────────────────────────────

# Arabic sheet names the localization touches
_SHEET_NAMES_55 = [
    "ملخص تنفيذى", "🧠 الخريطة الذهنية للمنهجية", "🌟 الخريطة الذهنية للنتائج",
    "الافتراضات والمدخلات", "التقرير", "مقارنات البيوع", "المقارنات الإيجارية",
    "طريقة التكلفة", "رأسمالة الدخل", "التحليل المكاني", "الانحدار المتعدد",
    "الخيارات الحقيقية", "توفيق النتائج", "محددات التقييم", "شهادة",
    "لوحة القيادة التنفيذية", "مصادر البيانات والمنهجية",
    "DCF — التدفقات النقدية", "ANN — الشبكات العصبية", "ARIMA — السلاسل الزمنية",
    "الإيجار مقابل الشراء", "أفضل وأعلى استخدام — HABU", "استخبارات السوق — MI",
    "📊 تحليل الحساسية", "🎯 مصفوفة SWOT", "📊 Hedonic Pricing",
    "📈 Gordon Growth", "🔁 Repeat Sales", "💰 DCF + Options", "🎲 Monte Carlo",
    "🏗️ RCNLD", "🏛️ Reproduction Cost", "🎯 Expected Utility",
    "💰 الاقتراض والكاش", "📈 CHOROPLETH", "📈 VORONOI", "📈 3D_SURFACE",
    "📈 SANKEY", "📈 GANTT", "📈 RISK_HEATMAP", "📈 COHORT",
    "📈 DECISION_TREE", "📈 TORNADO", "📈 RADAR_COMPARE",
    "بيان الامتثال", "توقيع واعتماد الخبير", "حوكمة مصادر البيانات",
    "قائمة المستندات ومخاطر الاعتماد", "حالة الاعتماد والتوصية",
    "نطاق العمل", "التوصية النهائية", "الإفصاحات المهنية",
    "نطاق الثقة وعدم اليقين", "حوكمة المعاملات", "القيمة بالحروف",
]
assert len(_SHEET_NAMES_55) == 55, f"Sheet list must be 55, got {len(_SHEET_NAMES_55)}"


def _egypt_infested_mock():
    """Return a _build_55_sheet side_effect that creates a workbook with 55
    Arabic-named sheets and Egyptian content injected into key cells.
    The Saudi localization pass in bridge_api.py must clean all of it."""
    import openpyxl as _opx_ei

    def _mock(ctx, output_path, *, request_id=None, **kwargs):
        wb = _opx_ei.Workbook()
        wb.remove(wb.active)
        for _sn in _SHEET_NAMES_55:
            wb.create_sheet(title=_sn)

        # Egyptian content to be removed by localization
        wb["الافتراضات والمدخلات"]["B57"] = "القاهرة"
        wb["الافتراضات والمدخلات"]["D48"] = "FRA Egypt"
        wb["الافتراضات والمدخلات"]["A147"] = "التضخم المصري السنوي"
        wb["التقرير"]["H8"] = "القاهرة"
        wb["التقرير"]["A16"] = "شقة سكنية تقع في القاهرة. يُعتبر الاستخدام الحالي الأمثل."
        wb["مقارنات البيوع"]["A47"] = "📊 بيانات نموذجية للمقارنات — Sample Comparable Sales"
        wb["المقارنات الإيجارية"]["B5"] = "القاهرة"
        wb["المقارنات الإيجارية"]["A37"] = "العائد يتراوح بين 4-7% في السوق المصري."
        wb["توفيق النتائج"]["A18"] = "شقة سكنية — القاهرة — توزيع الأوزان."
        wb["محددات التقييم"]["A32"] = "مشترٍ وبائع راغبان في السوق المصري."
        wb["شهادة"]["A26"] = "الشهادة تُثبت الالتزام مع جمعية المقيمين المصريين."
        wb["لوحة القيادة التنفيذية"]["A22"] = "📊  • التضخم المصري: 27.8% | EGP | 27.25%"
        wb["مصادر البيانات والمنهجية"]["A6"] = "عقار ماب (Aqar Map)"
        wb["مصادر البيانات والمنهجية"]["B6"] = "https://aqarmap.com.eg/ar/cairo"
        wb["مصادر البيانات والمنهجية"]["A14"] = "البنك المركزي المصري (CBE)"
        wb["مصادر البيانات والمنهجية"]["B14"] = "https://www.cbe.org.eg"
        wb["بيان الامتثال"]["D3"] = "المعيار المصري للتقييم — مبادئ HBU"
        wb["بيان الامتثال"]["D4"] = "المعيار المصري 410"
        wb["بيان الامتثال"]["D9"] = "FRA — متطلبات التقرير"
        wb["بيان الامتثال"]["B12"] = "IVS وUSPAP والمعايير المصرية للتقييم، الاعتماد."
        wb["القيمة بالحروف"]["A3"] = "الوحدة الحسابية: جنيه مصري (EGP)"
        wb["القيمة بالحروف"]["C5"] = "خمسة ملايين جنيهاً مصرياً وعشرون قرشاً"
        wb["القيمة بالحروف"]["B15"] = "القيمة/م² (EGP)"

        os.makedirs(os.path.dirname(str(output_path)), exist_ok=True)
        wb.save(str(output_path))
        wb.close()
        return {"success": True, "sheet_count": 55, "errors": []}

    return _mock


def _has_egypt_geographic_marker(cell_value) -> bool:
    """True if the cell contains an Egyptian geographic or institutional marker.

    False positives excluded: مصروفات/مصاريف/مصرف (expense / bank words).
    """
    import re as _re
    if cell_value is None:
        return False
    vs = str(cell_value)
    vl = vs.lower()

    if "القاهرة" in vs or "قاهرة" in vs:
        return True
    if _re.search(r"مصري[ةون]?|مصريين", vs):
        return True
    if ".com.eg" in vl or ".gov.eg" in vl or ".org.eg" in vl or "investinegypt" in vl:
        return True
    if "egypt" in vl:
        return True
    if "جنيه مصري" in vs or "جنيهاً مصرياً" in vs:
        return True
    if _re.search(r"\begp\b", vl):
        return True
    # مصر standalone: strip expense words first to avoid false positives
    cleaned = _re.sub(r"مصروفات?|مصرف", "", vs)
    if "مصر" in cleaned and not _re.search(r"مصري[ةون]?|مصريين", cleaned):
        # remaining مصر not in adjectival form — check it's geographic
        if _re.search(r"مصر(?!\w)", cleaned):
            return True
    return False


def _has_qa_marker(cell_value) -> bool:
    """True if the cell contains a QA/sample placeholder."""
    if cell_value is None:
        return False
    vs = str(cell_value).lower()
    return "sample comparable" in vs or "بيانات نموذجية للمقارنات" in str(cell_value)


def _scan_workbook_violations(wb_path) -> list:
    """Return list of (sheet, cell, value) tuples with Egypt/QA violations."""
    import openpyxl as _opx_scan
    violations = []
    wb = _opx_scan.load_workbook(str(wb_path), read_only=True, data_only=True)
    for sname in wb.sheetnames:
        ws = wb[sname]
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is None:
                    continue
                if _has_egypt_geographic_marker(cell.value):
                    violations.append((sname, cell.coordinate, str(cell.value)[:120]))
                elif _has_qa_marker(cell.value):
                    violations.append((sname, cell.coordinate, str(cell.value)[:120]))
    wb.close()
    return violations


class TestWorkbookContentHygiene:
    """EBA29–EBA36: After Saudi localization, the workbook must be free of
    Egyptian geographic markers, QA placeholders, and EGP currency labels."""

    def _make_admin_workbook(self, client, tmp_outputs):
        """Run one admin valuation, return (workbook_path, response_data)."""
        with patch("bridge_api._build_55_sheet",
                   side_effect=_egypt_infested_mock()), \
             patch("bridge_api.write_word_summary"), \
             patch("bridge_api.advanced_valuation", return_value=_ADV_STUB):
            resp = client.post(
                "/api/valuation",
                json={**_URA_PAYLOAD, "location": "الرياض — حي النخيل",
                      "property_type": "شقة سكنية", "currency": "SAR"},
                headers=_admin_headers(),
            )
        assert resp.status_code == 200, f"Valuation request failed: {resp.status_code}"
        data = resp.get_json()
        excel = data.get("formats", {}).get("excel", {})
        assert excel.get("generated"), (
            f"Builder should report generated=True; got: {excel}")
        filename = excel.get("filename")
        assert filename, "Response must include excel filename"
        return tmp_outputs / filename, data

    def test_EBA29_no_cairo_geographic_markers_after_localization(
            self, client, tmp_outputs):
        """Physical workbook must have zero Cairo geographic markers after localization."""
        wb_path, _ = self._make_admin_workbook(client, tmp_outputs)
        assert wb_path.exists(), f"Workbook file must be present at {wb_path}"
        violations = _scan_workbook_violations(wb_path)
        egypt_markers = [v for v in violations if _has_egypt_geographic_marker(v[2])]
        assert egypt_markers == [], (
            f"Cairo/Egyptian geographic markers found after localization:\n"
            + "\n".join(f"  {s}!{c}: {v}" for s, c, v in egypt_markers))

    def test_EBA30_no_sample_comparable_sales_after_localization(
            self, client, tmp_outputs):
        """Physical workbook must have zero 'Sample Comparable Sales' QA markers."""
        wb_path, _ = self._make_admin_workbook(client, tmp_outputs)
        violations = _scan_workbook_violations(wb_path)
        qa_markers = [v for v in violations if _has_qa_marker(v[2])]
        assert qa_markers == [], (
            f"QA/sample markers found after localization:\n"
            + "\n".join(f"  {s}!{c}: {v}" for s, c, v in qa_markers))

    def test_EBA31_currency_label_is_sar_not_egp(self, client, tmp_outputs):
        """القيمة بالحروف!A3 must show SAR, not EGP."""
        import openpyxl as _opx_cur
        wb_path, _ = self._make_admin_workbook(client, tmp_outputs)
        wb = _opx_cur.load_workbook(str(wb_path), read_only=True, data_only=True)
        a3 = None
        if "القيمة بالحروف" in wb.sheetnames:
            a3 = wb["القيمة بالحروف"]["A3"].value
        wb.close()
        assert a3 is not None, "القيمة بالحروف sheet / A3 must be present"
        assert "EGP" not in str(a3) and "جنيه مصري" not in str(a3), (
            f"A3 still contains Egyptian Pound: {a3!r}")
        assert "SAR" in str(a3) or "ريال سعودي" in str(a3), (
            f"A3 must mention SAR or ريال سعودي; got: {a3!r}")

    def test_EBA32_arabic_value_words_use_sar_not_egp(self, client, tmp_outputs):
        """القيمة بالحروف Arabic number words must say ريالاً سعودياً, not جنيهاً مصرياً."""
        import openpyxl as _opx_aw
        wb_path, _ = self._make_admin_workbook(client, tmp_outputs)
        wb = _opx_aw.load_workbook(str(wb_path), read_only=True, data_only=True)
        violations = []
        if "القيمة بالحروف" in wb.sheetnames:
            for _cel in ["C5", "A9"]:
                v = wb["القيمة بالحروف"][_cel].value
                if v and "جنيهاً مصرياً" in str(v):
                    violations.append(f"القيمة بالحروف!{_cel}: {v[:80]}")
        wb.close()
        assert violations == [], (
            "Arabic value cells still contain جنيهاً مصرياً:\n"
            + "\n".join(violations))

    def test_EBA33_data_sources_use_saudi_portals(self, client, tmp_outputs):
        """مصادر البيانات A6/A14 must reference Saudi portals, not Egyptian ones."""
        import openpyxl as _opx_ds
        wb_path, _ = self._make_admin_workbook(client, tmp_outputs)
        wb = _opx_ds.load_workbook(str(wb_path), read_only=True, data_only=True)
        a6 = a14 = b6 = b14 = None
        if "مصادر البيانات والمنهجية" in wb.sheetnames:
            ds = wb["مصادر البيانات والمنهجية"]
            a6  = str(ds["A6"].value or "")
            b6  = str(ds["B6"].value or "")
            a14 = str(ds["A14"].value or "")
            b14 = str(ds["B14"].value or "")
        wb.close()
        assert "aqarmap.com.eg" not in (b6 or "").lower(), (
            f"Egyptian portal URL still in B6: {b6!r}")
        assert "cbe.org.eg" not in (b14 or "").lower(), (
            f"Egyptian CBE URL still in B14: {b14!r}")
        assert "sama" in (a14 or "").lower() or "سعودي" in (a14 or ""), (
            f"A14 should reference SAMA; got: {a14!r}")

    def test_EBA34_compliance_sheet_uses_ivs_not_egyptian_standards(
            self, client, tmp_outputs):
        """بيان الامتثال D3–D8 must reference IVS, not Egyptian standards."""
        import openpyxl as _opx_cs
        wb_path, _ = self._make_admin_workbook(client, tmp_outputs)
        wb = _opx_cs.load_workbook(str(wb_path), read_only=True, data_only=True)
        violations = []
        if "بيان الامتثال" in wb.sheetnames:
            cs = wb["بيان الامتثال"]
            for row_n in range(3, 11):
                v = cs[f"D{row_n}"].value
                if v and ("المعيار المصري" in str(v) or "FRA Egypt" in str(v)):
                    violations.append(f"D{row_n}: {v}")
        wb.close()
        assert violations == [], (
            "Egyptian standards references remain in compliance column D:\n"
            + "\n".join(violations))

    def test_EBA35_report_sheet_location_is_from_request(self, client, tmp_outputs):
        """التقرير!H8 must contain the request location, not Cairo."""
        import openpyxl as _opx_loc
        wb_path, _ = self._make_admin_workbook(client, tmp_outputs)
        wb = _opx_loc.load_workbook(str(wb_path), read_only=True, data_only=True)
        h8 = None
        if "التقرير" in wb.sheetnames:
            h8 = wb["التقرير"]["H8"].value
        wb.close()
        assert h8 is not None, "التقرير!H8 must be present"
        assert "القاهرة" not in str(h8), (
            f"التقرير!H8 still shows Cairo: {h8!r}")
        assert "الرياض" in str(h8) or "حي النخيل" in str(h8), (
            f"التقرير!H8 should contain request location (Riyadh); got: {h8!r}")

    def test_EBA36_no_na_sentinel_in_visible_cells(self, client, tmp_outputs):
        """No cell should contain the _NA address sentinel."""
        import openpyxl as _opx_na
        wb_path, _ = self._make_admin_workbook(client, tmp_outputs)
        wb = _opx_na.load_workbook(str(wb_path), read_only=True, data_only=True)
        na_cells = []
        for sname in wb.sheetnames:
            for row in wb[sname].iter_rows():
                for cell in row:
                    if cell.value and "_NA" == str(cell.value).strip():
                        na_cells.append(f"{sname}!{cell.coordinate}")
        wb.close()
        assert na_cells == [], f"_NA sentinel found: {na_cells}"


# ─────────────────────────────────────────────────────────────────────────────
# LIFECYCLE TESTS  (EBA37–EBA40)
# Verify ONE_PER_REPORT_TIER semantics: one builder call per /api/valuation
# request regardless of PDF tier; distinct requests produce distinct workbooks.
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkbookLifecycle:
    """ONE_PER_REPORT_TIER: one workbook per /api/valuation request (distinct RIDs)."""

    def test_EBA37_single_admin_request_calls_builder_exactly_once(
            self, client, tmp_outputs):
        """One POST to /api/valuation must invoke the 55-sheet builder exactly once."""
        call_count = {"n": 0}

        def _counting_mock(ctx, output_path, *, request_id=None, **kwargs):
            call_count["n"] += 1
            return _file_creating_mock(55)(ctx, output_path, request_id=request_id)

        with patch("bridge_api._build_55_sheet", side_effect=_counting_mock), \
             patch("bridge_api.write_word_summary"), \
             patch("bridge_api.advanced_valuation", return_value=_ADV_STUB):
            resp = client.post("/api/valuation", json=_URA_PAYLOAD,
                               headers=_admin_headers())

        assert resp.status_code == 200
        assert call_count["n"] == 1, (
            f"Builder must be called exactly once per request; got {call_count['n']}")

    def test_EBA38_pdf_tier_does_not_affect_builder_call_count(
            self, client, tmp_outputs):
        """Different unified_report_action values each trigger exactly one builder call."""
        tiers = ["traditional_report", "detailed_report", "professional_report"]
        for tier in tiers:
            call_count = {"n": 0}

            def _counting(ctx, output_path, *, request_id=None, **kwargs):
                call_count["n"] += 1
                return _file_creating_mock(55)(ctx, output_path, request_id=request_id)

            payload = {**_MINIMAL, "unified_report_action": tier}
            with patch("bridge_api._build_55_sheet", side_effect=_counting), \
                 patch("bridge_api.write_word_summary"), \
                 patch("bridge_api.advanced_valuation", return_value=_ADV_STUB):
                resp = client.post("/api/valuation", json=payload,
                                   headers=_admin_headers())
            assert resp.status_code == 200, f"Request failed for tier {tier}"
            assert call_count["n"] == 1, (
                f"Tier {tier!r}: expected 1 builder call, got {call_count['n']}")

    def test_EBA39_normal_user_triggers_zero_builder_calls_any_tier(
            self, client, tmp_outputs):
        """Normal users must trigger zero builder calls regardless of unified_report_action."""
        tiers = ["traditional_report", "detailed_report", "professional_report"]
        for tier in tiers:
            call_count = {"n": 0}

            def _counting(ctx, output_path, *, request_id=None, **kwargs):
                call_count["n"] += 1
                return _file_creating_mock(55)(ctx, output_path, request_id=request_id)

            payload = {**_MINIMAL, "unified_report_action": tier}
            with patch("bridge_api._build_55_sheet", side_effect=_counting), \
                 patch("bridge_api.write_word_summary"), \
                 patch("bridge_api.advanced_valuation", return_value=_ADV_STUB):
                resp = client.post("/api/valuation", json=payload,
                                   headers=_normal_headers())
            assert resp.status_code == 200
            assert call_count["n"] == 0, (
                f"Normal user tier {tier!r}: expected 0 builder calls, got {call_count['n']}")

    def test_EBA40_workbook_filename_encodes_per_request_unique_id(
            self, client, tmp_outputs):
        """Every admin workbook filename must embed a unique request ID."""
        filenames = []

        def _cap(ctx, output_path, *, request_id=None, **kwargs):
            import re as _re2
            base = os.path.basename(str(output_path))
            filenames.append(base)
            # Verify filename structure: Report_{rid}_{ts}_admin.xlsx
            assert _re2.match(r"Report_.+_.+_admin\.xlsx", base), (
                f"Unexpected filename format: {base!r}")
            return _file_creating_mock(55)(ctx, output_path, request_id=request_id)

        with patch("bridge_api._build_55_sheet", side_effect=_cap), \
             patch("bridge_api.write_word_summary"), \
             patch("bridge_api.advanced_valuation", return_value=_ADV_STUB):
            for _ in range(3):
                client.post("/api/valuation", json=_MINIMAL, headers=_admin_headers())

        assert len(filenames) == 3, f"Expected 3 filenames, got {len(filenames)}"
        assert len(set(filenames)) == 3, (
            f"Duplicate filenames detected: {filenames}")
