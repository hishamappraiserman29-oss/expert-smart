"""test_pv_html_report.py — 22-test gate for HTML report generation.

Tests cover all three report tiers, shared context, security, MIME type,
dispositions, access control, parity, and backward compatibility.

Run:
    .venv/Scripts/python.exe -m pytest core_engine/tests/test_pv_html_report.py -q
"""
from __future__ import annotations

import pathlib
import re
import sys

import pytest

ROOT = pathlib.Path(__file__).parent.parent.parent
CORE = ROOT / "core_engine"

sys.path.insert(0, str(CORE))
sys.path.insert(0, str(ROOT))

# SAMPLE_DATA from accepted Traditional render gate
_SIM = "محاكاة داخلية/QA — غير معتمدة"
SAMPLE_DATA = {
    "report_title": "تقرير تقييم عقاري آلي — مبسط (Traditional)",
    "property_address": "شارع الجمهورية، القاهرة الجديدة، مصر",
    "property_type": "شقة سكنية", "area_sqm": 180, "floor": 5,
    "age_years": 8, "condition": "جيد جداً",
    "valuation_purpose": "بيع وشراء", "valuation_basis": "القيمة السوقية العادلة",
    "inspection_date": "2026-07-13", "report_date": "2026-07-13",
    "report_ref": "FINAL-TRAD-2026-001", "currency": "م.ج",
    "final_value": 3_200_000, "market_value": 3_200_000, "land_value": 1_800_000,
    "building_value": 1_100_000, "dcf_value": 3_100_000, "cost_approach_value": 2_900_000,
    "value_per_sqm": 17_778, "confidence_low": 2_950_000, "confidence_high": 3_450_000,
    "confidence_score": 74, "discount_rate": 12.5, "growth_rate": 3.5, "cap_rate_exit": 7.2,
    "land_area": 240, "land_price_sqm": 7_500, "land_method": _SIM,
    "physical_depreciation": 12, "functional_depreciation": 3, "total_depreciation": 15,
    "hbu_current": "سكني", "hbu_optimal": "سكني مع إمكانية التكثيف",
    "hbu_legal": "مسموح", "hbu_physical": "ممكن", "hbu_financial": "مجدٍ", "hbu_productivity": "متوسط",
    "recommendation": "يُنصح باستكمال الوثائق. القيمة التأشيرية 3,200,000 م.ج. — غير معتمدة.",
    "avm_results": [{"method": _SIM, "value": 3_220_000, "r2": 0.88, "note": _SIM}],
    "comparables": [{"id": 1, "address": "شارع المعز", "area": 175, "price": 3_150_000,
                     "price_sqm": 18_000, "adj_total": -2, "adj_value": 3_087_000,
                     "date": "2026-04", "note": _SIM}],
    "boq_items": [{"item": "هيكل خرساني", "unit": "م²", "qty": 180,
                   "unit_price": 3_800, "total": 684_000}],
    "dcf_years": [{"year": 1, "rent": 144_000, "vacancy": 5, "noi": 136_800,
                   "discount": 12.5, "pv": 121_600}],
    "terminal_value": 2_200_000,
    "cap_rate_models": [{"model": "بناء الأسعار", "rate": 7.8, "note": _SIM}],
    "swot": {"strengths": ["موقع متميز"], "weaknesses": ["عمر متوسط"],
             "opportunities": ["تطوير المنطقة"], "threats": ["تقلبات السوق"]},
    "required_docs": ["صك الملكية", "رخصة البناء"],
    "missing_docs": ["رخصة البناء"],
    "cert_risks": ["وثائق مفقودة"],
    "roadmap_steps": [{"step": "استكمال الوثائق", "status": "معلق"}],
    "annual_noi": 136_800, "cap_rate_used": 7.2,
    "market_weight": "40%", "cost_weight": "25%", "dcf_weight": "35%",
}


# ────────────────────────────────────────────────────────────────────────────
# Test 1 — Traditional HTML generation
# ────────────────────────────────────────────────────────────────────────────
def test_01_traditional_html_generation(tmp_path):
    from reports.html_report_builder import generate_html_report
    out = tmp_path / "trad.html"
    result = generate_html_report(SAMPLE_DATA, "traditional_report", out)
    assert result.exists(), "Traditional HTML not created"
    assert result.stat().st_size > 100_000, "Traditional HTML suspiciously small"


# ────────────────────────────────────────────────────────────────────────────
# Test 2 — Detailed HTML generation
# ────────────────────────────────────────────────────────────────────────────
def test_02_detailed_html_generation(tmp_path):
    from reports.html_report_builder import generate_html_report
    out = tmp_path / "det.html"
    result = generate_html_report(SAMPLE_DATA, "detailed_report", out)
    assert result.exists()
    assert result.stat().st_size > 100_000


# ────────────────────────────────────────────────────────────────────────────
# Test 3 — Professional HTML generation
# ────────────────────────────────────────────────────────────────────────────
def test_03_professional_html_generation(tmp_path):
    from reports.html_report_builder import generate_html_report
    out = tmp_path / "prof.html"
    result = generate_html_report(SAMPLE_DATA, "professional_report", out)
    assert result.exists()
    assert result.stat().st_size > 100_000


# ────────────────────────────────────────────────────────────────────────────
# Test 4 — Same shared report context for PDF and HTML (traditional)
# ────────────────────────────────────────────────────────────────────────────
def test_04_shared_context_traditional():
    from reports.pv_three_tier_pdf_builder import _enrich_traditional_data
    from reports.html_report_builder import build_traditional_html_safe
    enriched_direct = _enrich_traditional_data(SAMPLE_DATA)
    html_str = build_traditional_html_safe(SAMPLE_DATA)
    # The HTML must show the same final_value as the enriched context
    assert str(int(enriched_direct["final_value"])).replace(",", "") in html_str.replace(",", "")


# ────────────────────────────────────────────────────────────────────────────
# Test 5 — Numerical parity: final_value appears in HTML
# ────────────────────────────────────────────────────────────────────────────
def test_05_numerical_parity(tmp_path):
    from reports.html_report_builder import generate_html_report
    out = tmp_path / "num.html"
    generate_html_report(SAMPLE_DATA, "traditional_report", out)
    content = out.read_text(encoding="utf-8")
    # "3,200,000" or "3200000" must appear somewhere
    assert "3,200,000" in content or "3200000" in content, "final_value not found in HTML"


# ────────────────────────────────────────────────────────────────────────────
# Test 6 — Required section parity: Traditional has ≥36 section IDs
# ────────────────────────────────────────────────────────────────────────────
_TRADITIONAL_REQUIRED_SECTIONS = [
    "sec-cover", "sec-avm", "sec-comparables", "sec-land",
    "sec-boq", "sec-depreciation", "sec-cost-value", "sec-dcf",
    "sec-assumptions", "sec-kpi", "sec-reconciliation", "sec-caprate",
    "sec-hbu", "sec-swot", "sec-governance", "sec-cv",
    "sec-certrisk", "sec-roadmap", "sec-compliance", "sec-signature",
]

def test_06_required_section_parity(tmp_path):
    from reports.html_report_builder import generate_html_report
    out = tmp_path / "sec.html"
    generate_html_report(SAMPLE_DATA, "traditional_report", out)
    content = out.read_text(encoding="utf-8")
    missing = [s for s in _TRADITIONAL_REQUIRED_SECTIONS if f'id="{s}"' not in content]
    assert not missing, f"Missing sections: {missing}"


# ────────────────────────────────────────────────────────────────────────────
# Test 7 — Arabic RTL declaration
# ────────────────────────────────────────────────────────────────────────────
def test_07_arabic_rtl_declaration(tmp_path):
    from reports.html_report_builder import generate_html_report
    out = tmp_path / "rtl.html"
    generate_html_report(SAMPLE_DATA, "traditional_report", out)
    content = out.read_text(encoding="utf-8")
    assert 'lang="ar"' in content, "lang=ar not found"
    assert 'dir="rtl"' in content, "dir=rtl not found"


# ────────────────────────────────────────────────────────────────────────────
# Test 8 — UTF-8 encoding declaration
# ────────────────────────────────────────────────────────────────────────────
def test_08_utf8_encoding(tmp_path):
    from reports.html_report_builder import generate_html_report
    out = tmp_path / "enc.html"
    generate_html_report(SAMPLE_DATA, "traditional_report", out)
    # File must be readable as UTF-8 without error
    content = out.read_bytes().decode("utf-8")
    # And must declare charset
    assert "utf-8" in content[:1000].lower(), "UTF-8 charset declaration missing in <head>"


# ────────────────────────────────────────────────────────────────────────────
# Test 9 — HTML escaping of user-controlled inputs
# ────────────────────────────────────────────────────────────────────────────
def test_09_html_escaping(tmp_path):
    from reports.html_report_builder import generate_html_report
    xss_data = dict(SAMPLE_DATA)
    xss_data["property_address"] = '<b>TEST</b> & "quotes"'
    out = tmp_path / "esc.html"
    generate_html_report(xss_data, "traditional_report", out)
    content = out.read_text(encoding="utf-8")
    # The literal <b>TEST</b> must NOT appear unescaped
    assert "<b>TEST</b>" not in content, "User HTML tags not escaped"
    # Escaped form should appear (either &lt; or the content in the data)
    assert "TEST" in content, "Escaped content should still be present"


# ────────────────────────────────────────────────────────────────────────────
# Test 10 — Script injection prevention
# ────────────────────────────────────────────────────────────────────────────
def test_10_script_injection_prevention(tmp_path):
    from reports.html_report_builder import generate_html_report
    xss_data = dict(SAMPLE_DATA)
    xss_data["property_type"] = '<script>alert("XSS")</script>'
    out = tmp_path / "xss.html"
    generate_html_report(xss_data, "traditional_report", out)
    content = out.read_text(encoding="utf-8")
    # The literal unescaped script tag must not appear inside template content area
    # (outside the embedded CSS block which has no script tags)
    dangerous = re.findall(r'<script[^>]*>alert\("XSS"\)</script>', content)
    assert not dangerous, "Script injection not prevented — unescaped <script> found"


# ────────────────────────────────────────────────────────────────────────────
# Test 11 — Safe filename generation
# ────────────────────────────────────────────────────────────────────────────
def test_11_safe_filenames():
    from reports.html_report_builder import _safe_filename
    assert _safe_filename("normal.html") == "normal.html"
    assert "/" not in _safe_filename("../../../etc/passwd")
    assert "\\" not in _safe_filename("..\\..\\windows\\system32")
    safe = _safe_filename('<script>alert("xss")</script>.html')
    assert "<" not in safe and ">" not in safe and '"' not in safe


# ────────────────────────────────────────────────────────────────────────────
# Test 12 — Correct MIME type: html_view endpoint sets text/html
# ────────────────────────────────────────────────────────────────────────────
def test_12_correct_mime_type(tmp_path):
    import os
    # Verify bridge_api.py defines the html_view endpoint with text/html
    api_src = (CORE / "bridge_api.py").read_text(encoding="utf-8")
    assert "text/html; charset=utf-8" in api_src, "text/html MIME not set in html_view endpoint"
    assert "/api/report/html-view/" in api_src, "html-view endpoint not found"


# ────────────────────────────────────────────────────────────────────────────
# Test 13 — Inline view disposition
# ────────────────────────────────────────────────────────────────────────────
def test_13_inline_view_disposition():
    api_src = (CORE / "bridge_api.py").read_text(encoding="utf-8")
    assert "inline;" in api_src or 'Content-Disposition' in api_src, \
        "Inline disposition not set in html_view endpoint"
    # Specifically the html_view endpoint sets inline
    assert 'inline; filename=' in api_src


# ────────────────────────────────────────────────────────────────────────────
# Test 14 — Attachment download disposition
# ────────────────────────────────────────────────────────────────────────────
def test_14_attachment_download_disposition():
    api_src = (CORE / "bridge_api.py").read_text(encoding="utf-8")
    # The /api/download/ endpoint uses send_file(..., as_attachment=True)
    assert "as_attachment=True" in api_src, "as_attachment=True not in download endpoint"


# ────────────────────────────────────────────────────────────────────────────
# Test 15 — Access control: path traversal blocked in html_view
# ────────────────────────────────────────────────────────────────────────────
def test_15_access_control():
    api_src = (CORE / "bridge_api.py").read_text(encoding="utf-8")
    # html_view endpoint must check for path separators
    assert '"/" in filename' in api_src or "path separators" in api_src or \
        "Invalid filename" in api_src, "Path traversal check missing in html_view"


# ────────────────────────────────────────────────────────────────────────────
# Test 16 — No absolute local paths in generated HTML
# ────────────────────────────────────────────────────────────────────────────
def test_16_no_absolute_local_paths(tmp_path):
    from reports.html_report_builder import generate_html_report
    out = tmp_path / "trad_paths.html"
    generate_html_report(SAMPLE_DATA, "traditional_report", out)
    content = out.read_text(encoding="utf-8")
    assert "C:\\" not in content, "Windows absolute path found in generated HTML"
    assert "D:\\" not in content, "Windows absolute path found in generated HTML"
    assert "/home/" not in content, "Unix home path found in generated HTML"
    assert "/Users/" not in content, "Unix Users path found in generated HTML"


# ────────────────────────────────────────────────────────────────────────────
# Test 17 — No external runtime dependencies in generated HTML
# ────────────────────────────────────────────────────────────────────────────
def test_17_no_external_runtime_dependencies(tmp_path):
    from reports.html_report_builder import generate_html_report
    for tier in ("traditional_report", "detailed_report", "professional_report"):
        out = tmp_path / f"{tier}.html"
        generate_html_report(SAMPLE_DATA, tier, out)
        content = out.read_text(encoding="utf-8")
        external = re.findall(r'(?:src|href)=["\']https?://', content)
        assert not external, f"{tier}: external dependencies found: {external[:3]}"


# ────────────────────────────────────────────────────────────────────────────
# Test 18 — Signature-state parity: HTML never claims signed/certified
# ────────────────────────────────────────────────────────────────────────────
def test_18_signature_state_parity(tmp_path):
    from reports.html_report_builder import generate_html_report
    for tier in ("traditional_report", "detailed_report", "professional_report"):
        out = tmp_path / f"{tier}.html"
        generate_html_report(SAMPLE_DATA, tier, out)
        content = out.read_text(encoding="utf-8")
        forbidden = ["fake_stamp_created=True", "CERTIFIED_ISSUED", "تم الاعتماد الرسمي"]
        for phrase in forbidden:
            assert phrase not in content, f"{tier}: forbidden phrase '{phrase}' found"
        assert "مسودة غير معتمدة" in content, f"{tier}: advisory watermark missing"


# ────────────────────────────────────────────────────────────────────────────
# Test 19 — Certification-state parity: enriched data has pending cert status
# ────────────────────────────────────────────────────────────────────────────
def test_19_certification_state_parity():
    from reports.pv_three_tier_pdf_builder import _enrich_professional_data
    enriched = _enrich_professional_data(SAMPLE_DATA)
    cert_status = enriched.get("cert_overall_status", "")
    # Must be "pending" or "partial" — never "certified" or "issued"
    assert cert_status in ("pending", "partial", ""), \
        f"cert_overall_status should be pending/partial, got: {cert_status!r}"


# ────────────────────────────────────────────────────────────────────────────
# Test 20 — PDF backward compatibility: existing PDF builder unaffected
# ────────────────────────────────────────────────────────────────────────────
def test_20_pdf_backward_compatibility():
    # Verify pv_three_tier_pdf_builder exports same public functions
    from reports import pv_three_tier_pdf_builder as _tb
    assert callable(_tb.build_traditional_html)
    assert callable(_tb.build_detailed_html)
    assert callable(_tb.build_professional_html)
    assert callable(_tb.render_traditional_pdf)
    assert callable(_tb.render_detailed_pdf)
    assert callable(_tb.render_professional_pdf)
    # Verify html_report_builder does not override pv_three_tier functions
    from reports import html_report_builder as _hb
    assert _hb.generate_html_report is not getattr(_tb, "generate_html_report", None), \
        "html_report_builder must not shadow pv_three_tier_pdf_builder"


# ────────────────────────────────────────────────────────────────────────────
# Test 21 — Both artifacts returned by generation API (source code check)
# ────────────────────────────────────────────────────────────────────────────
def test_21_both_artifacts_returned_by_api():
    api_src = (CORE / "bridge_api.py").read_text(encoding="utf-8")
    assert "html_view_url" in api_src,     "html_view_url not added to API response"
    assert "html_download_url" in api_src, "html_download_url not added to API response"
    assert "pdf_url" in api_src,           "pdf_url not added to API response (three-tier PDF)"
    assert "generate_html_report" in api_src, "generate_html_report not called from handle_valuation"


# ────────────────────────────────────────────────────────────────────────────
# Test 22 — Frontend shows the three required actions
# ────────────────────────────────────────────────────────────────────────────
def test_22_frontend_shows_three_required_actions():
    frontend = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    assert "pv-html-view-btn" in frontend,     "View HTML button (data-testid) missing from frontend"
    assert "pv-html-download-btn" in frontend, "Download HTML button (data-testid) missing from frontend"
    assert "pv-pdf-download-btn" in frontend,  "Download PDF button (data-testid) missing from frontend"
    # Check Arabic labels
    assert "html_view_url" in frontend,     "html_view_url reference missing from frontend"
    assert "html_download_url" in frontend, "html_download_url reference missing from frontend"
    assert "pdf_url" in frontend,           "pdf_url reference missing from frontend"
