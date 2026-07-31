"""
Backend tests for Report Review V2.1 enhancements.
15 tests — E01 through E15.
Run: python -m pytest tests/test_pv_report_review_v21_enhancements.py -q
"""
from __future__ import annotations
import json
import pathlib
import pytest

_ROOT = pathlib.Path(__file__).parent.parent
_V2   = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_report_review_v2"
_AUD  = _V2 / "report_review_audits"
_PDF  = _V2 / "pdf_outputs"


def _aud(name: str) -> dict:
    p = _AUD / name
    assert p.exists(), f"Audit missing: {name}"
    return json.loads(p.read_text(encoding="utf-8"))


# ── E01: external market research audit exists ───────────────────────────────
def test_E01_external_market_research_audit_exists():
    audit = _aud("review_v21_external_market_research_audit.json")
    assert audit.get("external_market_research_attempted") is True
    assert "browser_access_status" in audit


# ── E02: extraction bottleneck audit exists ───────────────────────────────────
def test_E02_extraction_bottleneck_audit_exists():
    audit = _aud("review_v21_extraction_bottleneck_audit.json")
    assert audit.get("extraction_pipeline_improved") is True
    assert "ocr_status" in audit
    assert "table_extraction_status" in audit


# ── E03: critical scoring audit exists ───────────────────────────────────────
def test_E03_critical_scoring_audit_exists():
    audit = _aud("review_v21_critical_scoring_audit.json")
    assert audit.get("critical_weighting_enabled") is True
    assert audit.get("score_caps_enabled") is True


# ── E04: HBU gap suggestions audit exists ────────────────────────────────────
def test_E04_hbu_gap_suggestions_audit_exists():
    audit = _aud("review_v21_hbu_gap_suggestions_audit.json")
    assert audit.get("hbu_gap_analysis_enabled") is True
    assert audit.get("four_hbu_tests_checked") is True


# ── E05: uncertainty range suggestion audit exists ───────────────────────────
def test_E05_uncertainty_range_suggestion_audit_exists():
    audit = _aud("review_v21_uncertainty_range_suggestion_audit.json")
    assert audit.get("uncertainty_range_detection_enabled") is True
    assert audit.get("advisory_uncertainty_suggestion_enabled") is True


# ── E06: extraction blockers create human review flags ───────────────────────
def test_E06_extraction_blockers_create_human_review_flags():
    audit = _aud("review_v21_extraction_bottleneck_audit.json")
    assert audit.get("human_review_flags_created") is True, (
        "Extraction blockers must create human review flags"
    )
    assert audit.get("blocked_extraction_disclosed") is True


# ── E07: critical flaw caps score ────────────────────────────────────────────
def test_E07_critical_flaw_caps_score():
    audit = _aud("review_v21_critical_scoring_audit.json")
    assert audit.get("critical_flaws_cap_score") is True
    before = audit.get("score_before_caps", 0)
    after  = audit.get("score_after_caps", 0)
    assert after <= before, f"Score after caps ({after}) must be <= before ({before})"
    assert after < 60, f"Score with critical flaws must be < 60, got {after}"


# ── E08: income approach critical flaw affects status ────────────────────────
def test_E08_income_approach_critical_flaw_handled():
    audit = _aud("review_v21_critical_scoring_audit.json")
    assert audit.get("income_approach_critical_flaw_handled") is True


# ── E09: missing HBU creates targeted action items ───────────────────────────
def test_E09_missing_hbu_creates_action_items():
    audit = _aud("review_v21_hbu_gap_suggestions_audit.json")
    assert audit.get("hbu_action_items_generated") is True
    items = audit.get("hbu_action_items", [])
    assert len(items) >= 1, "At least 1 HBU action item expected"
    missing = audit.get("missing_hbu_components", [])
    assert len(missing) >= 1, "Missing HBU components must be identified"


# ── E10: uncertainty range advisory suggestion when data available ────────────
def test_E10_uncertainty_range_suggestion_when_data_available():
    audit = _aud("review_v21_uncertainty_range_suggestion_audit.json")
    assert audit.get("suggestion_needed") is True
    if audit.get("enough_data_to_suggest"):
        assert audit.get("suggested_margin_percent") is not None, (
            "Suggested margin percent must be set when data is available"
        )
    assert audit.get("statistical_confidence_claimed") is False, (
        "Must not falsely claim statistical confidence"
    )


# ── E11: V2 PDF includes value comparison and external research status ────────
def test_E11_pdf_includes_value_comparison_and_research_status():
    html = _PDF / "report_review_output_v2.html"
    if not html.exists():
        pytest.skip("HTML not generated")
    content = html.read_text(encoding="utf-8", errors="ignore")
    assert "مقارنة القيمة" in content, "Value comparison section missing from PDF"
    has_market = "البحث السوقي" in content or "market_research" in content.lower()
    has_blocked = "محجوب" in content or "BLOCKED" in content
    assert has_market or has_blocked, "External research status not referenced in PDF"


# ── E12: PDF does not falsely claim statistical confidence ───────────────────
def test_E12_pdf_no_false_statistical_confidence():
    html = _PDF / "report_review_output_v2.html"
    if not html.exists():
        pytest.skip("HTML not generated")
    content = html.read_text(encoding="utf-8", errors="ignore")
    assert "statistical_confidence_claimed=False" in content or \
           "استرشادي فقط" in content, (
        "PDF must clearly state advisory / non-statistical nature of suggestions"
    )


# ── E13: PDF does not include fake signature ──────────────────────────────────
def test_E13_pdf_no_fake_signature():
    html = _PDF / "report_review_output_v2.html"
    if not html.exists():
        pytest.skip("HTML not generated")
    content = html.read_text(encoding="utf-8", errors="ignore").lower()
    for bad in ["fake_reviewer_signature\n", "mock_signature", "placeholder_signature"]:
        assert bad not in content, f"Forbidden: '{bad}' found in V2 PDF HTML"


# ── E14: V2.1 UI panels audit exists ─────────────────────────────────────────
def test_E14_v21_ui_panels_audit_exists():
    audit = _aud("review_v21_ui_panels_audit.json")
    assert audit.get("extraction_quality_panel_visible") is True
    assert audit.get("external_market_research_panel_visible") is True
    assert audit.get("hbu_gap_suggestions_panel_visible") is True
    assert audit.get("uncertainty_range_suggestion_panel_visible") is True


# ── E15: no internal paths in any V2.1 audit ──────────────────────────────────
def test_E15_no_internal_paths_in_v21_audits():
    audit_files = [
        "review_v21_external_market_research_audit.json",
        "review_v21_extraction_bottleneck_audit.json",
        "review_v21_critical_scoring_audit.json",
        "review_v21_hbu_gap_suggestions_audit.json",
        "review_v21_uncertainty_range_suggestion_audit.json",
        "review_v21_ui_panels_audit.json",
    ]
    for fname in audit_files:
        p = _AUD / fname
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        assert r"C:\Users" not in text, f"Internal path in {fname}"
        assert "C:/Users/Lenovo" not in text, f"Internal path in {fname}"
