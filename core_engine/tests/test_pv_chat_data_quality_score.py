# test_pv_chat_data_quality_score.py
# Backend unit tests for Chat Data Quality Score
# advisory_only=True | not_real_training=True | no_commit=True
#
# T01–T09: Pure Python tests — no live server needed.

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core_engine.professional_valuation_chat_intent_guard_context import (
    classify_chat_message_intent,
    extract_minimum_requirement_coverage,
    calculate_chat_data_quality_score,
    is_message_valuation_relevant,
    CHAT_DATA_QUALITY_CONTEXT,
)


# ── T01: Irrelevant message is blocked and not scored ────────────────────────
def test_T01_irrelevant_message_not_scored():
    msg = "أنا كنت في النادي وشاهدت مباراة كورة"
    result = classify_chat_message_intent(msg)
    assert result["category"] == "irrelevant_general_chat"
    # irrelevant messages must not be scored — calling extract on blocked message
    # should return mostly empty coverage (no meaningful valuation data)
    coverage = extract_minimum_requirement_coverage(msg)
    score_result = calculate_chat_data_quality_score(coverage)
    # Score should be very weak since no valuation content
    assert score_result["score"] <= 24, f"Expected very_weak, got score={score_result['score']}"
    assert score_result["level"] == "very_weak"
    assert not is_message_valuation_relevant(msg)


# ── T02: Minimal message gets weak score ─────────────────────────────────────
def test_T02_minimal_message_gets_weak_score():
    # Only mentions asset type — no location, area, purpose etc.
    msg = "عقار تجاري"
    coverage = extract_minimum_requirement_coverage(msg)
    score_result = calculate_chat_data_quality_score(coverage)
    # Should have asset_type but little else — weak or very_weak
    assert score_result["level"] in ("very_weak", "weak"), (
        f"Expected weak/very_weak, got {score_result['level']} (score={score_result['score']})"
    )
    assert score_result["score"] <= 49


# ── T03: Comprehensive message gets good/strong score ────────────────────────
def test_T03_comprehensive_message_gets_good_score():
    msg = (
        "العقار فندق سكني تجاري على مساحة 5000 متر في منطقة الرياض، "
        "يحتاج تقرير احترافي لأغراض الرهن التمويلي. "
        "حالة المبنى جيدة، الاستخدام الحالي مؤجر بالكامل. "
        "سند الملكية صك رسمي مسجل. "
        "معايير التقييم IVS ايفاس."
    )
    coverage = extract_minimum_requirement_coverage(msg)
    score_result = calculate_chat_data_quality_score(coverage)
    # Should have multiple fields covered — good or strong
    assert score_result["level"] in ("good", "strong", "acceptable"), (
        f"Expected good/strong/acceptable, got {score_result['level']} (score={score_result['score']})"
    )
    assert score_result["score"] >= 50


# ── T04: Missing minimum requirements are listed ─────────────────────────────
def test_T04_missing_minimum_requirements_listed():
    # Only asset type and location — missing most other fields
    msg = "شقة سكنية في حي النرجس بالرياض"
    coverage = extract_minimum_requirement_coverage(msg)
    score_result = calculate_chat_data_quality_score(coverage)
    assert len(score_result["missing"]) > 0, "Expected missing requirements"
    # Should be missing at least area, purpose, condition, use, report type, standards
    missing_labels = score_result["missing"]
    assert len(missing_labels) >= 4, f"Expected >=4 missing, got {len(missing_labels)}: {missing_labels}"


# ── T05: Optional fields alone do not create strong score ────────────────────
def test_T05_optional_fields_alone_not_strong():
    # Message has optional fields (income, comparables, date) but not minimum required
    msg = "الإيجار الشهري ألف ريال والإشغال 90% وسعر السوق مرتفع، تاريخ 2026"
    coverage = extract_minimum_requirement_coverage(msg)
    score_result = calculate_chat_data_quality_score(coverage)
    # Optional fields only — minimum required mostly missing — cannot be strong
    assert score_result["level"] not in ("strong",), (
        f"Optional-only message should not be strong, got {score_result['level']}"
    )
    assert score_result["score"] <= 69


# ── T06: Weak score should block final value conclusion ──────────────────────
def test_T06_weak_score_blocks_final_conclusion():
    assert CHAT_DATA_QUALITY_CONTEXT["weak_data_blocks_final_conclusion"] is True
    # A weak score means readiness is not_ready or partial
    msg = "عقار بس"
    coverage = extract_minimum_requirement_coverage(msg)
    score_result = calculate_chat_data_quality_score(coverage)
    assert score_result["readiness"] in ("not_ready", "partial")


# ── T07: PDF/Excel context includes data quality summary ─────────────────────
def test_T07_pdf_excel_context_includes_data_quality_summary():
    assert CHAT_DATA_QUALITY_CONTEXT["pdf_excel_include_data_quality_summary"] is True


# ── T08: Raw unrelated chat not used in scoring ──────────────────────────────
def test_T08_raw_unrelated_chat_not_used():
    assert CHAT_DATA_QUALITY_CONTEXT["irrelevant_messages_not_scored"] is True
    assert CHAT_DATA_QUALITY_CONTEXT["valuation_relevant_messages_scored"] is True


# ── T09: Expert review remains required ─────────────────────────────────────
def test_T09_expert_review_required():
    assert CHAT_DATA_QUALITY_CONTEXT["expert_review_required"] is True
    # Even for a strong score, expert review must be flagged
    msg = (
        "فندق على مساحة 5000 متر في الرياض، تقرير احترافي لأغراض الرهن، "
        "حالة ممتاز، مؤجر بالكامل، سند ملكية صك، معايير IVS."
    )
    coverage = extract_minimum_requirement_coverage(msg)
    score_result = calculate_chat_data_quality_score(coverage)
    assert score_result["expert_review_required"] is True
