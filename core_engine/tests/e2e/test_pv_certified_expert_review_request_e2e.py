"""
E2E tests — PV Certified Expert Review Request
Tests: PVCERTE2E01–PVCERTE2E26
advisory_only=True | not_real_training=True | certification_ready=False

Static tests (01-17): HTML parse + audit JSON checks — no live server needed.
Live tests (18-26):   Playwright + live server — decorated @_LIVE @_SKIP_NO_PW.

Run static:
  python -m pytest core_engine/tests/e2e/test_pv_certified_expert_review_request_e2e.py -q -m "not live_server"

Run live (after: pip install playwright && playwright install):
  python -m pytest core_engine/tests/e2e/test_pv_certified_expert_review_request_e2e.py -q -m live_server
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_CORE))

_QA       = _CORE / "instance" / "manual_review_outputs" / "professional_valuation_certified_expert_review_request"
_FRONTEND = _CORE.parent / "frontend" / "index.html"
_BASE_URL = "http://127.0.0.1:5000"

# ── Playwright import with graceful fallback ──────────────────────────────────
try:
    from playwright.sync_api import Page, expect
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Page = object  # type: ignore[misc]

_LIVE     = pytest.mark.live_server
_SKIP_NO_PW = pytest.mark.skipif(
    not PLAYWRIGHT_AVAILABLE,
    reason="playwright not installed — run: pip install playwright && playwright install",
)


# ── helpers ──────────────────────────────────────────────────────────────────

def _html() -> str:
    assert _FRONTEND.exists(), "frontend/index.html not found"
    return _FRONTEND.read_text(encoding="utf-8")


def _load_audit(name: str) -> dict:
    p = _QA / name
    assert p.exists(), f"Audit file missing: {p}"
    return json.loads(p.read_text(encoding="utf-8"))


def _pv_section(html: str) -> str:
    """Return the HTML slice for the PV certified expert review section."""
    start = html.find('data-testid="pro-val-expert-review-request-section"')
    assert start != -1, "pro-val-expert-review-request-section not found"
    end = html.find('<!-- /pro-val-expert-review-request-section -->', start)
    return html[start: end + 50 if end != -1 else start + 10000]


# ═══════════════════════════════════════════════════════════════════════════════
# STATIC TESTS (HTML + JSON — no live server)
# ═══════════════════════════════════════════════════════════════════════════════

def test_PVCERTE2E01_frontend_file_exists():
    """PVCERTE2E01: frontend/index.html exists."""
    assert _FRONTEND.exists()


def test_PVCERTE2E02_pv_expert_review_section_present():
    """PVCERTE2E02: pro-val-expert-review-request-section present in HTML."""
    assert 'data-testid="pro-val-expert-review-request-section"' in _html()


def test_PVCERTE2E03_title_present():
    """PVCERTE2E03: title 'هل تحتاج تقرير تقييم معتمد؟' present in section."""
    section = _pv_section(_html())
    assert "هل تحتاج تقرير تقييم معتمد؟" in section


def test_PVCERTE2E04_description_present():
    """PVCERTE2E04: description text 'يمكنك تحويل المسودة المبدئية' present."""
    section = _pv_section(_html())
    assert "يمكنك تحويل المسودة المبدئية" in section


def test_PVCERTE2E05_request_checkbox_label_present():
    """PVCERTE2E05: checkbox label 'طلب مراجعة واعتماد من خبير التقييم' present."""
    section = _pv_section(_html())
    assert "طلب مراجعة واعتماد من خبير التقييم" in section


def test_PVCERTE2E06_checkbox_toggle_present():
    """PVCERTE2E06: pv-cert-request-toggle checkbox present."""
    section = _pv_section(_html())
    assert 'id="pv-cert-request-toggle"' in section


def test_PVCERTE2E07_delivery_method_field_present():
    """PVCERTE2E07: delivery method select (pv-cert-delivery) present."""
    section = _pv_section(_html())
    assert 'id="pv-cert-delivery"' in section


def test_PVCERTE2E08_delivery_placeholder_present():
    """PVCERTE2E08: delivery method placeholder '- اختر طريقة الاستلام -' present."""
    section = _pv_section(_html())
    assert "- اختر طريقة الاستلام -" in section


def test_PVCERTE2E09_delivery_options_present():
    """PVCERTE2E09: واتساب and البريد الإلكتروني options present."""
    section = _pv_section(_html())
    assert "واتساب" in section
    assert "البريد الإلكتروني" in section


def test_PVCERTE2E10_form_title_present():
    """PVCERTE2E10: form title 'طلب مراجعة واعتماد التقرير من خبير التقييم' present."""
    section = _pv_section(_html())
    assert "طلب مراجعة واعتماد التقرير من خبير التقييم" in section


def test_PVCERTE2E11_excel_internal_notice_present():
    """PVCERTE2E11: Excel internal-only notice present in section."""
    section = _pv_section(_html())
    assert "ملفات Excel التفصيلية تظل داخلية للخبير أو الإدارة فقط ولا تُرسل للمستخدم" in section


def test_PVCERTE2E12_phone_field_present():
    """PVCERTE2E12: phone/WhatsApp field (pv-cert-phone) present."""
    section = _pv_section(_html())
    assert 'id="pv-cert-phone"' in section
    assert "رقم الهاتف / واتساب" in section


def test_PVCERTE2E13_name_field_present():
    """PVCERTE2E13: full name field (pv-cert-name) and label present."""
    section = _pv_section(_html())
    assert 'id="pv-cert-name"' in section
    assert "الاسم بالكامل" in section


def test_PVCERTE2E14_report_type_field_present():
    """PVCERTE2E14: report type select (pv-cert-report-type) present."""
    section = _pv_section(_html())
    assert 'id="pv-cert-report-type"' in section
    assert "نوع التقرير المطلوب" in section


def test_PVCERTE2E15_report_type_has_seven_options():
    """PVCERTE2E15: report type dropdown has 7 professional options."""
    section = _pv_section(_html())
    expected = [
        "تقرير تقليدي",
        "تقرير تفصيلي",
        "تقرير احترافي",
        "تقرير مراجعة",
        "تقرير محاكاة",
        "تقرير أعلى وأفضل استخدام",
        "تقرير امتثال المعايير",
    ]
    for opt in expected:
        assert opt in section, f"Report type option missing: {opt}"


def test_PVCERTE2E16_no_internal_paths_in_section():
    """PVCERTE2E16: no internal filesystem paths in the PV section."""
    section = _pv_section(_html())
    for pat in ("C:\\Users", "C:/Users", "/home/", "expert_smart1", "core_engine/instance"):
        assert pat not in section, f"Internal path leaked: {pat}"


def test_PVCERTE2E17_audit_index_file_passes():
    """PVCERTE2E17: 00_certified_expert_review_request_index.json result=PASS."""
    data = _load_audit("00_certified_expert_review_request_index.json")
    assert data.get("result") == "PASS"
    assert data.get("matched_ordinary_valuation_page") is True
    assert data.get("fake_approval_created") is False
    assert data.get("certification_ready") is False


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT JSON STATIC CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

def test_PVCERTE2E18_style_match_audit_passes():
    """PVCERTE2E18: 01_ordinary_valuation_style_match_audit result=PASS."""
    data = _load_audit("01_ordinary_valuation_style_match_audit.json")
    assert data.get("result") == "PASS"
    assert data.get("matched_ordinary_valuation_page_style") is True


def test_PVCERTE2E19_text_visibility_audit_passes():
    """PVCERTE2E19: 02_required_text_visibility_audit all visible flags = True."""
    data = _load_audit("02_required_text_visibility_audit.json")
    assert data.get("result") == "PASS"
    assert data.get("visible_title_هل_تحتاج_تقرير_تقييم_معتمد") is True
    assert data.get("visible_request_label_طلب_مراجعة_واعتماد_من_خبير_التقييم") is True
    assert data.get("visible_excel_internal_only_notice") is True
    assert data.get("visible_no_immediate_certification_notice") is True


def test_PVCERTE2E20_delivery_validation_audit_passes():
    """PVCERTE2E20: 03_delivery_method_validation_audit result=PASS."""
    data = _load_audit("03_delivery_method_validation_audit.json")
    assert data.get("result") == "PASS"
    assert data["email_validation"]["result"] == "PASS"
    assert data["whatsapp_validation"]["result"] == "PASS"
    assert data.get("full_name_always_required") is True
    assert data.get("report_type_optional") is True


def test_PVCERTE2E21_certification_gate_audit_passes():
    """PVCERTE2E21: 04_certification_gate_preservation_audit result=PASS."""
    data = _load_audit("04_certification_gate_preservation_audit.json")
    assert data.get("result") == "PASS"
    assert data.get("certification_ready_changed_automatically") is False
    assert data.get("certified_pdf_generated_immediately") is False
    assert data["context_fields_verified"]["certification_ready_changed"] is False
    assert data["context_fields_verified"]["fake_approval_created"] is False


def test_PVCERTE2E22_excel_internal_only_audit_passes():
    """PVCERTE2E22: 05_admin_excel_internal_only_audit result=PASS."""
    data = _load_audit("05_admin_excel_internal_only_audit.json")
    assert data.get("result") == "PASS"
    assert data.get("admin_excel_internal_only") is True
    assert data.get("admin_excel_sent_to_user") is False


def test_PVCERTE2E23_no_fake_approval_audit_passes():
    """PVCERTE2E23: 06_no_fake_approval_audit result=PASS."""
    data = _load_audit("06_no_fake_approval_audit.json")
    assert data.get("result") == "PASS"
    assert data.get("fake_approval_created") is False
    assert data.get("fake_signature_created") is False
    assert data.get("fake_stamp_created") is False


def test_PVCERTE2E24_no_internal_paths_audit_passes():
    """PVCERTE2E24: 07_no_internal_paths_audit result=PASS."""
    data = _load_audit("07_no_internal_paths_audit.json")
    assert data.get("result") == "PASS"
    assert data.get("internal_paths_in_dom") is False
    assert data.get("no_filesystem_paths_exposed") is True


# ═══════════════════════════════════════════════════════════════════════════════
# LIVE SERVER + PLAYWRIGHT TESTS (skipped if playwright not installed)
# ═══════════════════════════════════════════════════════════════════════════════

@_LIVE
@_SKIP_NO_PW
def test_PVCERTE2E25_page_opens(page: Page):
    """PVCERTE2E25: Professional Valuation page opens without JS errors."""
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{_BASE_URL}/", timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=20_000)
    assert len(errors) == 0 or all("favicon" in e.lower() for e in errors)


@_LIVE
@_SKIP_NO_PW
def test_PVCERTE2E26_certified_section_visible(page: Page):
    """PVCERTE2E26: certified expert review section is visible on the page."""
    page.goto(f"{_BASE_URL}/", timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=20_000)
    section = page.locator('[data-testid="pro-val-expert-review-request-section"]')
    expect(section).to_be_visible(timeout=10_000)
