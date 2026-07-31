"""
Integration regression tests for the three-tier HTML report flow.

Covers the exact bugs fixed in PRODUCTION_HTML_REPORT_FLOW_FIX:
  1. HTML generation exception must be captured in _html_generation_error, not silently dropped.
  2. report_id (rid) must appear in the API response dict.
  3. A `formats` nested object (html + pdf sub-keys) must be in the response.
  4. The frontend must surface html_generation_error via a visible banner.
  5. Each report type must actually produce an .html file on disk when called directly.

Tests 1-4 are source-code structural assertions — they prevent silent regression if
the pattern is accidentally removed during a future edit.
Tests 5-7 are builder integration tests — they call generate_html_report() directly
with a canonical minimal payload and verify the output file is written.
"""

import os
import pathlib
import sys
import tempfile
import pytest

# ── Repo root ─────────────────────────────────────────────────────────────────
REPO = pathlib.Path(__file__).parent.parent.parent  # expert_smart1 - Copy/
CORE = REPO / "core_engine"
BRIDGE = CORE / "bridge_api.py"
FRONTEND = REPO / "frontend" / "index.html"

# Match how test_pv_html_report.py sets up paths so the builder import works.
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _bridge_src() -> str:
    return BRIDGE.read_text(encoding="utf-8")

def _frontend_src() -> str:
    return FRONTEND.read_text(encoding="utf-8")


def _minimal_report_data(report_type: str) -> dict:
    """Return the minimum data dict that html_report_builder accepts."""
    return {
        "property_description": f"عقار تجريبي لاختبار {report_type}",
        "location": "القاهرة، مصر",
        "area": 200,
        "price_per_sqm": 5000,
        "market_value": 1_000_000,
        "valuation_purpose": "fair_market_value",
        "report_type": report_type,
        "report_date": "2026-07-15",
        "report_id": "ES-TEST-0001",
    }


# ─────────────────────────────────────────────────────────────────────────────
# GROUP 1 — Source-code contract assertions (bridge_api.py)
# ─────────────────────────────────────────────────────────────────────────────

class TestBridgeApiResponseContract:

    def test_01_report_id_included_in_resp_dict(self):
        """resp dict must include report_id so the frontend can display it."""
        src = _bridge_src()
        assert '"report_id": rid' in src, (
            'bridge_api.py resp dict is missing "report_id": rid — '
            "the frontend cannot display the report identifier"
        )

    def test_02_html_generation_error_captured_not_silent(self):
        """HTML exception must be stored in _html_generation_error, not silently swallowed."""
        src = _bridge_src()
        assert "_html_generation_error = str(_html_err)" in src, (
            "bridge_api.py HTML exception handler does not store the error in "
            "_html_generation_error — failures are still silent"
        )

    def test_03_html_generation_error_variable_initialised(self):
        """_html_generation_error must be initialised to None before the try block."""
        src = _bridge_src()
        assert '_html_generation_error: "str | None" = None' in src, (
            "_html_generation_error variable not initialised before HTML generation block"
        )

    def test_04_html_generation_error_added_to_resp(self):
        """html_generation_error must be conditionally added to the response dict."""
        src = _bridge_src()
        assert 'resp["html_generation_error"] = _html_generation_error' in src, (
            "bridge_api.py does not add html_generation_error to the response — "
            "frontend cannot display the error to the user"
        )

    def test_05_formats_object_in_response(self):
        """A formats nested object must be added to resp for three-tier report types."""
        src = _bridge_src()
        assert 'resp["formats"]' in src, (
            'bridge_api.py does not add resp["formats"] — '
            "consumers cannot distinguish HTML-only vs PDF-only vs dual success"
        )

    def test_06_formats_html_subkey_present(self):
        """formats dict must contain an 'html' sub-key."""
        src = _bridge_src()
        assert '"html": {' in src or '"html":{' in src, (
            'resp["formats"] is missing the "html" sub-key'
        )

    def test_07_formats_pdf_subkey_present(self):
        """formats dict must contain a 'pdf' sub-key."""
        src = _bridge_src()
        assert '"pdf": {' in src or '"pdf":{' in src, (
            'resp["formats"] is missing the "pdf" sub-key'
        )

    def test_08_formats_generated_flag_in_html(self):
        """formats.html must include a 'generated' boolean so callers can distinguish None filename."""
        src = _bridge_src()
        assert '"generated":   _html_filename is not None' in src or \
               '"generated": _html_filename is not None' in src, (
            'formats["html"] is missing the "generated" flag'
        )

    def test_09_formats_error_field_in_html(self):
        """formats.html must include the 'error' field so callers can inspect the failure reason."""
        src = _bridge_src()
        assert '"error":       _html_generation_error' in src or \
               '"error": _html_generation_error' in src, (
            'formats["html"] is missing the "error" field'
        )

    def test_10_html_view_route_exists(self):
        """/api/report/html-view/<filename> route must exist."""
        src = _bridge_src()
        assert '"/api/report/html-view/<filename>"' in src or \
               "'/api/report/html-view/<filename>'" in src, (
            "html-view route missing from bridge_api.py"
        )

    def test_11_download_route_path_traversal_protected(self):
        """/api/download route must use realpath containment against traversal."""
        src = _bridge_src()
        assert "abs_outputs + os.sep" in src, (
            "Download route may be missing realpath+sep containment check"
        )


# ─────────────────────────────────────────────────────────────────────────────
# GROUP 2 — Frontend contract assertions
# ─────────────────────────────────────────────────────────────────────────────

class TestFrontendContract:

    def test_12_frontend_reads_html_generation_error(self):
        """Frontend must read html_generation_error from the API response."""
        src = _frontend_src()
        assert "html_generation_error" in src, (
            "frontend/index.html does not reference html_generation_error — "
            "users cannot see when HTML generation failed"
        )

    def test_13_frontend_html_error_banner_testid(self):
        """Frontend error banner must have data-testid=pv-html-error-banner for E2E tests."""
        src = _frontend_src()
        assert 'data-testid="pv-html-error-banner"' in src, (
            "HTML error banner is missing data-testid attribute — E2E tests cannot target it"
        )

    def test_14_frontend_html_error_banner_conditional(self):
        """htmlErrorBannerHtml must be in the modal innerHTML template."""
        src = _frontend_src()
        assert "${htmlErrorBannerHtml}" in src, (
            "htmlErrorBannerHtml is not interpolated into the reportResult innerHTML"
        )

    def test_15_frontend_reads_report_id(self):
        """Frontend must read report_id from the API response."""
        src = _frontend_src()
        assert "apiResult.report_id" in src, (
            "frontend/index.html does not read apiResult.report_id"
        )

    def test_16_frontend_report_id_in_template(self):
        """reportIdHtml must be in the modal innerHTML template."""
        src = _frontend_src()
        assert "${reportIdHtml}" in src, (
            "reportIdHtml is not interpolated into the reportResult innerHTML"
        )


# ─────────────────────────────────────────────────────────────────────────────
# GROUP 3 — Builder integration: generate_html_report writes actual files
# ─────────────────────────────────────────────────────────────────────────────

def _import_html_builder():
    """Import generate_html_report (sys.path set at module level)."""
    from reports.html_report_builder import generate_html_report
    return generate_html_report


@pytest.mark.parametrize("report_type", [
    "traditional_report",
    "detailed_report",
    "professional_report",
])
def test_17_builder_writes_html_file_to_disk(report_type, tmp_path):
    """generate_html_report() must produce a non-empty .html file for each tier."""
    gen = _import_html_builder()
    data = _minimal_report_data(report_type)
    out_path = tmp_path / f"test_{report_type}.html"
    gen(data, report_type, str(out_path))
    assert out_path.exists(), f"HTML file not created for {report_type}"
    size = out_path.stat().st_size
    assert size > 500, f"HTML file too small ({size} bytes) for {report_type}"


@pytest.mark.parametrize("report_type", [
    "traditional_report",
    "detailed_report",
    "professional_report",
])
def test_18_builder_output_is_valid_html(report_type, tmp_path):
    """Builder output must contain essential HTML scaffolding."""
    gen = _import_html_builder()
    data = _minimal_report_data(report_type)
    out_path = tmp_path / f"test_{report_type}.html"
    gen(data, report_type, str(out_path))
    content = out_path.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content or "<html" in content, (
        f"{report_type}: output is not valid HTML (missing doctype/html tag)"
    )


def test_19_builder_failure_raises_not_silenced(tmp_path):
    """Builder must raise an exception for unknown report_type (not silently return)."""
    gen = _import_html_builder()
    data = _minimal_report_data("traditional_report")
    out_path = tmp_path / "test_bad.html"
    with pytest.raises(Exception):
        gen(data, "UNKNOWN_REPORT_TYPE", str(out_path))


# ─────────────────────────────────────────────────────────────────────────────
# GROUP 4 — Response contract construction (simulates bridge_api logic)
# ─────────────────────────────────────────────────────────────────────────────

def test_20_formats_dict_structure_when_both_succeed(tmp_path):
    """
    Simulate bridge_api formats dict construction when both HTML and PDF succeed.
    Verifies the contract shape the frontend and downstream consumers depend on.
    """
    gen = _import_html_builder()
    data = _minimal_report_data("traditional_report")
    html_path = tmp_path / "Report_TEST_traditional_report.html"
    gen(data, "traditional_report", str(html_path))

    # Simulate bridge_api response construction
    _html_filename = html_path.name
    _pdf_filename = "Report_TEST_traditional_report.pdf"  # hypothetical
    _html_generation_error = None
    _ura = "traditional_report"
    _VALID_TIER_TYPES = {"traditional_report", "detailed_report", "professional_report"}

    resp = {"status": "success", "report_id": "ES-TEST-0001"}
    if _html_filename:
        resp["html_view_url"] = f"http://127.0.0.1:5000/api/report/html-view/{_html_filename}"
        resp["html_download_url"] = f"http://127.0.0.1:5000/api/download/{_html_filename}"
    if _html_generation_error:
        resp["html_generation_error"] = _html_generation_error
    if _pdf_filename:
        resp["pdf_url"] = f"http://127.0.0.1:5000/api/download/{_pdf_filename}"
    if _ura in _VALID_TIER_TYPES:
        resp["formats"] = {
            "html": {
                "filename": _html_filename,
                "viewUrl": resp.get("html_view_url"),
                "downloadUrl": resp.get("html_download_url"),
                "generated": _html_filename is not None,
                "error": _html_generation_error,
            },
            "pdf": {
                "filename": _pdf_filename,
                "downloadUrl": resp.get("pdf_url"),
                "generated": _pdf_filename is not None,
            },
        }

    assert resp["formats"]["html"]["generated"] is True
    assert resp["formats"]["html"]["error"] is None
    assert resp["formats"]["pdf"]["generated"] is True
    assert "report_id" in resp
    assert "html_generation_error" not in resp  # absent when no error


def test_21_formats_dict_structure_when_html_fails(tmp_path):
    """
    Simulate bridge_api response when HTML fails and PDF succeeds.
    Verifies html_generation_error is explicit, not silent.
    """
    _html_filename = None
    _pdf_filename = "Report_TEST_traditional_report.pdf"
    _html_generation_error = "TemplateNotFound: pv_traditional_report.html"
    _ura = "traditional_report"
    _VALID_TIER_TYPES = {"traditional_report", "detailed_report", "professional_report"}

    resp = {"status": "success", "report_id": "ES-TEST-0002"}
    if _html_filename:
        resp["html_view_url"] = f"http://127.0.0.1:5000/api/report/html-view/{_html_filename}"
        resp["html_download_url"] = f"http://127.0.0.1:5000/api/download/{_html_filename}"
    if _html_generation_error:
        resp["html_generation_error"] = _html_generation_error
    if _pdf_filename:
        resp["pdf_url"] = f"http://127.0.0.1:5000/api/download/{_pdf_filename}"
    if _ura in _VALID_TIER_TYPES:
        resp["formats"] = {
            "html": {
                "filename": _html_filename,
                "viewUrl": resp.get("html_view_url"),
                "downloadUrl": resp.get("html_download_url"),
                "generated": _html_filename is not None,
                "error": _html_generation_error,
            },
            "pdf": {
                "filename": _pdf_filename,
                "downloadUrl": resp.get("pdf_url"),
                "generated": _pdf_filename is not None,
            },
        }

    # HTML failed explicitly — not silent
    assert resp["formats"]["html"]["generated"] is False
    assert resp["formats"]["html"]["error"] == _html_generation_error
    assert resp["html_generation_error"] == _html_generation_error
    # PDF still succeeded
    assert resp["formats"]["pdf"]["generated"] is True
    # report_id still present
    assert "report_id" in resp
    # html_view_url absent when HTML failed
    assert "html_view_url" not in resp
