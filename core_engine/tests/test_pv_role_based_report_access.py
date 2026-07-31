"""
Role-based report access tests.

Covers the role-separation requirements added in USER_ADMIN_REPORT_FORMATS_VISUAL_REVIEW:

  1. Normal users receive PDF and HTML URLs in the valuation response.
  2. Normal users do not receive excel_url in the valuation response.
  3. Administrators receive excel_url in the valuation response.
  4. The /api/download endpoint returns 403 for xlsx/xlsm requests from non-admin users.
  5. The /api/download endpoint returns 403 for xlsm requests from non-admin users.
  6. The backend response includes formats.excel only for administrators.
  7. The backend response includes formats.html and formats.pdf for all users.
  8. The frontend section description mentions PDF and HTML.
  9. The frontend section description mentions administrator-only Excel.
 10. The Internal Excel Card is hidden by default (display:none) for role-based JS init.
 11. The pv-core-report-admin-helper element is hidden by default.
 12. The pvInitCoreReportIssuanceSection function exists in the frontend.
 13. The download endpoint admin-gate checks both .xlsx and .xlsm extensions.
 14. The Excel download button uses data-testid="pv-excel-download-btn".
 15. The HTML view button uses data-testid="pv-html-view-btn".
 16. The HTML download button uses data-testid="pv-html-download-btn".
 17. The PDF download button uses data-testid="pv-pdf-download-btn".
 18. No local path is exposed via the download response.
 19. The frontend excelBtnHtml checks _isAdmin before rendering.
 20. The pvGenerateCoreReportBundle function references pv-bundle-html-status.
"""

import pathlib
import sys
import pytest

REPO = pathlib.Path(__file__).parent.parent.parent
CORE = REPO / "core_engine"
BRIDGE = CORE / "bridge_api.py"
FRONTEND = REPO / "frontend" / "index.html"
ADMIN_MOD = CORE / "admin.py"

if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def _bridge_src() -> str:
    return BRIDGE.read_text(encoding="utf-8")


def _frontend_src() -> str:
    return FRONTEND.read_text(encoding="utf-8")


def _admin_src() -> str:
    return ADMIN_MOD.read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# GROUP 1 — Backend source-code contract assertions
# ─────────────────────────────────────────────────────────────────────────────

class TestBackendRoleContract:

    def test_01_excel_url_not_in_initial_resp_dict(self):
        """excel_url must not appear unconditionally in the initial resp dict."""
        src = _bridge_src()
        # The old pattern was: "excel_url": f"...{name}" unconditionally in resp = {
        # After the fix, excel_url must be gated behind _is_admin check
        assert '"excel_url": f"http://127.0.0.1:5000/api/download/{name}"' not in src, (
            "bridge_api.py still exposes excel_url unconditionally in the initial resp dict — "
            "normal users would receive the Excel workbook URL"
        )

    def test_02_excel_url_gated_by_is_admin(self):
        """excel_url must only be added to resp when _is_admin(g.user_id) is True."""
        src = _bridge_src()
        assert '_is_admin(g.user_id)' in src and 'resp["excel_url"]' in src, (
            "bridge_api.py does not gate resp[\"excel_url\"] behind _is_admin check"
        )

    def test_03_admin_check_precedes_excel_url_assignment(self):
        """The _is_admin check must appear before the resp["excel_url"] assignment."""
        import re as _re
        src = _bridge_src()
        # Allow for 'and name is not None' or other extra conditions on the guard
        pattern = r'if _is_admin\(g\.user_id\)[^:]*:\s+resp\["excel_url"\]'
        assert _re.search(pattern, src), (
            "The gated resp[\"excel_url\"] assignment pattern not found in bridge_api.py"
        )

    def test_04_formats_excel_gated_by_is_admin(self):
        """formats.excel must only appear in the response for admin users."""
        src = _bridge_src()
        assert 'resp["formats"]["excel"]' in src, (
            "bridge_api.py does not include formats.excel in the response"
        )
        # Verify it is inside an is_admin block
        formats_excel_pos = src.find('resp["formats"]["excel"]')
        preceding_block   = src[max(0, formats_excel_pos - 200):formats_excel_pos]
        assert '_is_admin' in preceding_block, (
            "formats.excel is not guarded by an _is_admin check"
        )

    def test_05_download_endpoint_has_admin_gate_for_xlsx(self):
        """The /api/download endpoint must reject xlsx files from non-admin users."""
        src = _bridge_src()
        assert 'safe_name.endswith(".xlsx")' in src and 'safe_name.endswith(".xlsm")' in src, (
            "bridge_api.py /api/download does not check for xlsx/xlsm extensions"
        )

    def test_06_download_endpoint_returns_403_for_unauthorized_excel(self):
        """The download endpoint must return HTTP 403 for unauthorized Excel downloads."""
        src = _bridge_src()
        assert '"Excel workbook downloads require administrator access"' in src, (
            "bridge_api.py download endpoint does not include the 403 Excel denial message"
        )

    def test_07_download_endpoint_admin_gate_before_file_serve(self):
        """The admin gate must appear before send_file in the download route."""
        src = _bridge_src()
        gate_pos   = src.find('"Excel workbook downloads require administrator access"')
        serve_pos  = src.find('return send_file(filepath, as_attachment=True)')
        assert gate_pos != -1 and serve_pos != -1 and gate_pos < serve_pos, (
            "The 403 Excel admin gate does not appear before send_file in bridge_api.py"
        )

    def test_08_formats_html_always_present_in_response(self):
        """formats.html must be in the response for all authenticated users."""
        src = _bridge_src()
        assert '"html": {' in src and '"viewUrl":' in src and '"downloadUrl":' in src, (
            "bridge_api.py formats.html is missing required keys"
        )

    def test_09_formats_pdf_always_present_in_response(self):
        """formats.pdf must be in the response for all authenticated users."""
        src = _bridge_src()
        assert '"pdf": {' in src and '"generated":   _pdf_filename is not None' in src, (
            "bridge_api.py formats.pdf missing generated key"
        )

    def test_10_admin_module_is_admin_fn_exists(self):
        """admin.py must define is_admin() and require_admin()."""
        src = _admin_src()
        assert 'def is_admin(' in src, "admin.py missing is_admin function"
        assert 'def require_admin(' in src, "admin.py missing require_admin function"

    def test_11_require_admin_returns_403_for_authenticated_non_admin(self):
        """require_admin must return 403 (not 401) for authenticated non-admin users."""
        src = _admin_src()
        assert '403' in src and '"Admin access required"' in src, (
            "admin.py require_admin decorator does not return 403 for non-admin users"
        )

    def test_12_no_local_path_in_download_response(self):
        """The download 403 response must not expose local filesystem paths."""
        src = _bridge_src()
        gate_text = '"Excel workbook downloads require administrator access"'
        pos = src.find(gate_text)
        assert pos != -1
        surrounding = src[max(0, pos - 50):pos + len(gate_text) + 50]
        assert 'C:\\\\' not in surrounding and '/home/' not in surrounding, (
            "Excel download 403 message contains a local filesystem path"
        )

    def test_13_formats_excel_includes_sheet_count(self):
        """formats.excel must include a sheetCount field derived from the actual workbook."""
        import re as _re
        src = _bridge_src()
        # sheetCount must be present and must NOT be the hardcoded integer 55
        assert '"sheetCount":' in src, (
            "bridge_api.py formats.excel does not include a sheetCount field"
        )
        assert '"sheetCount":  55' not in src and '"sheetCount": 55' not in src, (
            "bridge_api.py formats.excel sheetCount is hardcoded as 55 — "
            "must be derived from the actual workbook sheet count"
        )


# ─────────────────────────────────────────────────────────────────────────────
# GROUP 2 — Frontend source-code contract assertions
# ─────────────────────────────────────────────────────────────────────────────

class TestFrontendRoleContract:

    def test_14_helper_text_mentions_pdf(self):
        """The section helper text must explicitly mention PDF."""
        src = _frontend_src()
        assert 'pv-core-report-helper-text' in src
        # Find the helper text div and check it mentions PDF
        idx = src.find('pv-core-report-helper-text')
        snippet = src[idx:idx + 400]
        assert 'PDF' in snippet, (
            "pv-core-report-helper-text does not mention PDF"
        )

    def test_15_helper_text_mentions_html(self):
        """The section helper text must explicitly mention HTML."""
        src = _frontend_src()
        idx = src.find('pv-core-report-helper-text')
        snippet = src[idx:idx + 400]
        assert 'HTML' in snippet, (
            "pv-core-report-helper-text does not mention HTML"
        )

    def test_16_admin_helper_text_mentions_excel(self):
        """The admin-only helper text must mention Excel."""
        src = _frontend_src()
        assert 'pv-core-report-admin-helper' in src
        idx = src.find('pv-core-report-admin-helper')
        snippet = src[idx:idx + 400]
        assert 'Excel' in snippet, (
            "pv-core-report-admin-helper text does not mention Excel"
        )

    def test_17_admin_helper_text_mentions_admin_only(self):
        """The admin helper text must make clear it is for admins only."""
        src = _frontend_src()
        idx = src.find('pv-core-report-admin-helper')
        snippet = src[idx:idx + 400]
        assert 'للمسؤولين' in snippet or 'admin' in snippet.lower(), (
            "pv-core-report-admin-helper text does not indicate admin-only access"
        )

    def test_18_internal_excel_card_starts_hidden(self):
        """The Internal Excel Card must start with display:none for role-based JS init."""
        src = _frontend_src()
        idx = src.find('pv-core-internal-excel-card')
        # Find the containing div's style
        start = src.rfind('<div', 0, idx)
        end = src.find('>', start)
        tag = src[start:end + 1]
        assert 'display:none' in tag, (
            "pv-core-internal-excel-card div does not start with display:none — "
            "it would be visible to non-admin users before JS init runs"
        )

    def test_19_admin_helper_starts_hidden(self):
        """The pv-core-report-admin-helper element must start with display:none."""
        src = _frontend_src()
        idx = src.find('id="pv-core-report-admin-helper"')
        start = src.rfind('<div', 0, idx)
        end = src.find('>', start)
        tag = src[start:end + 1]
        assert 'display:none' in tag, (
            "pv-core-report-admin-helper div does not start with display:none"
        )

    def test_20_pvinit_core_report_issuance_section_exists(self):
        """pvInitCoreReportIssuanceSection function must be defined in the frontend."""
        src = _frontend_src()
        assert 'function pvInitCoreReportIssuanceSection()' in src, (
            "pvInitCoreReportIssuanceSection function not found in frontend/index.html"
        )

    def test_21_pvinit_called_from_command_center(self):
        """pvInitCoreReportIssuanceSection must be called from pvInitChatCommandCenter."""
        src = _frontend_src()
        idx = src.find('function pvInitChatCommandCenter()')
        assert idx != -1
        body = src[idx:idx + 400]
        assert 'pvInitCoreReportIssuanceSection()' in body, (
            "pvInitChatCommandCenter does not call pvInitCoreReportIssuanceSection()"
        )

    def test_22_excel_btn_checks_is_admin(self):
        """The excelBtnHtml rendering must check _isAdmin before displaying the button."""
        src = _frontend_src()
        idx = src.find('excelBtnHtml')
        # Find the excelBtnHtml assignment (not usage)
        assign_idx = src.find('const excelBtnHtml =')
        assert assign_idx != -1
        snippet = src[assign_idx:assign_idx + 200]
        assert '_isAdmin' in snippet, (
            "excelBtnHtml is rendered without checking _isAdmin — "
            "non-admin users could see the Excel download button"
        )

    def test_23_html_view_btn_has_testid(self):
        """The HTML view button must have data-testid='pv-html-view-btn'."""
        src = _frontend_src()
        assert 'data-testid="pv-html-view-btn"' in src, (
            "pv-html-view-btn testid not found — frontend tests cannot target the HTML view button"
        )

    def test_24_html_download_btn_has_testid(self):
        """The HTML download button must have data-testid='pv-html-download-btn'."""
        src = _frontend_src()
        assert 'data-testid="pv-html-download-btn"' in src, (
            "pv-html-download-btn testid not found"
        )

    def test_25_pdf_download_btn_has_testid(self):
        """The PDF download button must have data-testid='pv-pdf-download-btn'."""
        src = _frontend_src()
        assert 'data-testid="pv-pdf-download-btn"' in src, (
            "pv-pdf-download-btn testid not found"
        )

    def test_26_excel_download_btn_has_testid(self):
        """The Excel download button must have data-testid='pv-excel-download-btn'."""
        src = _frontend_src()
        assert 'data-testid="pv-excel-download-btn"' in src, (
            "pv-excel-download-btn testid not found"
        )

    def test_27_bundle_status_has_html_status_div(self):
        """The bundle status area must include a pv-bundle-html-status div."""
        src = _frontend_src()
        assert 'pv-bundle-html-status' in src, (
            "pv-bundle-html-status div missing from pv-core-bundle-status area"
        )

    def test_28_generate_report_bundle_references_html_status(self):
        """pvGenerateCoreReportBundle must reference pv-bundle-html-status."""
        src = _frontend_src()
        idx = src.find('function pvGenerateCoreReportBundle(reportType)')
        assert idx != -1
        body = src[idx:idx + 1500]
        assert 'pv-bundle-html-status' in body, (
            "pvGenerateCoreReportBundle does not update pv-bundle-html-status"
        )

    def test_29_bundle_excel_status_admin_only(self):
        """pvGenerateCoreReportBundle must only populate Excel status for admins."""
        src = _frontend_src()
        idx = src.find('function pvGenerateCoreReportBundle(reportType)')
        body = src[idx:idx + 1800]
        assert 'isAdmin' in body, (
            "pvGenerateCoreReportBundle does not check isAdmin before showing Excel status"
        )

    def test_30_html_view_uses_noopener_noreferrer(self):
        """HTML view link must use rel='noopener noreferrer' for security."""
        src = _frontend_src()
        assert 'rel="noopener noreferrer"' in src, (
            "HTML view link missing rel=noopener noreferrer security attribute"
        )

    def test_31_page_badge_detailed_is_18(self):
        """The detailed report page badge must show 18 صفحة (verified count)."""
        src = _frontend_src()
        idx = src.find('pv-core-badge-detailed-pages')
        snippet = src[idx:idx + 400]
        assert '18 صفحة' in snippet, (
            "pv-core-badge-detailed-pages does not show 18 صفحة — badge is inaccurate"
        )

    def test_32_page_badge_professional_is_28(self):
        """The professional report page badge must show 28 صفحة (verified count)."""
        src = _frontend_src()
        idx = src.find('pv-core-badge-professional-pages')
        snippet = src[idx:idx + 400]
        assert '28 صفحة' in snippet, (
            "pv-core-badge-professional-pages does not show 28 صفحة — badge is inaccurate"
        )
