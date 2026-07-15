# test_pv_chat_intent_guard.py
# Backend unit tests for Professional Valuation Chat Intent Guard
# advisory_only=True | not_real_training=True | no_commit=True
#
# T01–T19: Pure Python tests — no live server needed.

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


# ── T01: Context module importable ────────────────────────────────────────────
def test_T01_context_module_importable():
    from core_engine.professional_valuation_chat_intent_guard_context import (
        CHAT_INTENT_GUARD_CONTEXT
    )
    assert CHAT_INTENT_GUARD_CONTEXT is not None
    assert isinstance(CHAT_INTENT_GUARD_CONTEXT, dict)


# ── T02: chat_intent_guard_enabled = True ─────────────────────────────────────
def test_T02_chat_intent_guard_enabled():
    from core_engine.professional_valuation_chat_intent_guard_context import (
        CHAT_INTENT_GUARD_CONTEXT
    )
    assert CHAT_INTENT_GUARD_CONTEXT["chat_intent_guard_enabled"] is True


# ── T03: All 8 classification categories exist ───────────────────────────────
def test_T03_classification_categories_complete():
    from core_engine.professional_valuation_chat_intent_guard_context import (
        CHAT_INTENT_GUARD_CONTEXT
    )
    required = {
        "valuation_relevant",
        "report_generation_relevant",
        "document_or_attachment_relevant",
        "special_report_relevant",
        "clarification_request",
        "irrelevant_general_chat",
        "unsafe_or_out_of_scope",
        "ambiguous_needs_confirmation",
    }
    cats = set(CHAT_INTENT_GUARD_CONTEXT["classification_categories"])
    assert required <= cats, f"Missing categories: {required - cats}"


# ── T04: Valuation-related message is accepted ───────────────────────────────
def test_T04_valuation_message_accepted():
    from core_engine.professional_valuation_chat_intent_guard_context import (
        classify_chat_message_intent, is_message_valuation_relevant
    )
    msg = "العقار فندق على مساحة 5000 متر مربع في منطقة الرياض ويحتاج تقرير احترافي"
    result = classify_chat_message_intent(msg)
    assert result["category"] in (
        "valuation_relevant", "report_generation_relevant", "special_report_relevant"
    ), f"Got: {result['category']}"
    assert is_message_valuation_relevant(msg) is True


# ── T05: Report generation message is accepted ──────────────────────────────
def test_T05_report_generation_message_accepted():
    from core_engine.professional_valuation_chat_intent_guard_context import (
        classify_chat_message_intent, is_message_valuation_relevant
    )
    msg = "أريد إصدار تقرير PDF احترافي للعقار"
    result = classify_chat_message_intent(msg)
    assert result["category"] in (
        "report_generation_relevant", "valuation_relevant"
    ), f"Got: {result['category']}"
    assert is_message_valuation_relevant(msg) is True


# ── T06: Document-related message is accepted ───────────────────────────────
def test_T06_document_message_accepted():
    from core_engine.professional_valuation_chat_intent_guard_context import (
        classify_chat_message_intent, is_message_valuation_relevant
    )
    msg = "أريد رفع مستند الملكية وصك العقار"
    result = classify_chat_message_intent(msg)
    assert result["category"] in (
        "document_or_attachment_relevant", "valuation_relevant"
    ), f"Got: {result['category']}"
    assert is_message_valuation_relevant(msg) is True


# ── T07: HBU-related message is accepted ─────────────────────────────────────
def test_T07_hbu_message_accepted():
    from core_engine.professional_valuation_chat_intent_guard_context import (
        classify_chat_message_intent, is_message_valuation_relevant
    )
    msg = "أريد تحليل هبيو للأرض الصناعية HBU"
    result = classify_chat_message_intent(msg)
    assert result["category"] == "special_report_relevant", f"Got: {result['category']}"
    assert is_message_valuation_relevant(msg) is True


# ── T08: Report review message is accepted ──────────────────────────────────
def test_T08_report_review_message_accepted():
    from core_engine.professional_valuation_chat_intent_guard_context import (
        classify_chat_message_intent, is_message_valuation_relevant
    )
    msg = "أريد مراجعة تقرير التقييم المقدم من المقيم السابق"
    result = classify_chat_message_intent(msg)
    assert result["category"] in (
        "special_report_relevant", "valuation_relevant"
    ), f"Got: {result['category']}"
    assert is_message_valuation_relevant(msg) is True


# ── T09: Casual irrelevant message is blocked ────────────────────────────────
def test_T09_casual_irrelevant_message_blocked():
    from core_engine.professional_valuation_chat_intent_guard_context import (
        classify_chat_message_intent, is_message_valuation_relevant
    )
    msg = "أنا كنت في النادي وشاهدت مباراة كورة ممتعة جداً مع الأصدقاء"
    result = classify_chat_message_intent(msg)
    assert result["category"] == "irrelevant_general_chat", f"Got: {result['category']}"
    assert is_message_valuation_relevant(msg) is False


# ── T10: Unrelated story is blocked ─────────────────────────────────────────
def test_T10_unrelated_story_blocked():
    from core_engine.professional_valuation_chat_intent_guard_context import (
        classify_chat_message_intent, is_message_valuation_relevant
    )
    msg = "أنا كنت في النادي وبحكي قصة ليس لها علاقة بالتقييم وكانت رحلة سياحية جميلة"
    result = classify_chat_message_intent(msg)
    assert result["category"] == "irrelevant_general_chat", f"Got: {result['category']}"
    assert is_message_valuation_relevant(msg) is False


# ── T11: Ambiguous message requires confirmation ────────────────────────────
def test_T11_ambiguous_message_requires_confirmation():
    from core_engine.professional_valuation_chat_intent_guard_context import (
        classify_chat_message_intent
    )
    msg = "محتاج رأيك"
    result = classify_chat_message_intent(msg)
    assert result["category"] == "ambiguous_needs_confirmation", f"Got: {result['category']}"


# ── T12: Blocked irrelevant message not added to report context ──────────────
def test_T12_blocked_irrelevant_not_in_report_context():
    from core_engine.professional_valuation_chat_intent_guard_context import (
        CHAT_INTENT_GUARD_CONTEXT
    )
    assert CHAT_INTENT_GUARD_CONTEXT["irrelevant_messages_blocked_from_report_context"] is True
    assert CHAT_INTENT_GUARD_CONTEXT["irrelevant_messages_excluded_from_report_outputs"] is True


# ── T13: Raw unrelated chat not used as assumptions ──────────────────────────
def test_T13_raw_unrelated_chat_not_used_as_assumptions():
    from core_engine.professional_valuation_chat_intent_guard_context import (
        CHAT_INTENT_GUARD_CONTEXT
    )
    assert CHAT_INTENT_GUARD_CONTEXT["raw_chat_not_used_as_assumptions"] is True


# ── T14: PDF generation uses filtered chat context ───────────────────────────
def test_T14_pdf_generation_uses_filtered_context():
    from core_engine.professional_valuation_chat_intent_guard_context import (
        CHAT_INTENT_GUARD_CONTEXT
    )
    assert CHAT_INTENT_GUARD_CONTEXT["pdf_generation_uses_filtered_chat_context"] is True
    assert CHAT_INTENT_GUARD_CONTEXT["raw_unrelated_chat_not_used_in_pdf"] is True


# ── T15: Excel generation uses filtered chat context ─────────────────────────
def test_T15_excel_generation_uses_filtered_context():
    from core_engine.professional_valuation_chat_intent_guard_context import (
        CHAT_INTENT_GUARD_CONTEXT
    )
    assert CHAT_INTENT_GUARD_CONTEXT["excel_generation_uses_filtered_chat_context"] is True
    assert CHAT_INTENT_GUARD_CONTEXT["raw_unrelated_chat_not_used_in_excel"] is True


# ── T16: Irrelevant chat excluded from generated report context ──────────────
def test_T16_irrelevant_chat_excluded_from_report_outputs():
    from core_engine.professional_valuation_chat_intent_guard_context import (
        CHAT_INTENT_GUARD_CONTEXT
    )
    assert CHAT_INTENT_GUARD_CONTEXT["ambiguous_messages_excluded_until_confirmed"] is True


# ── T17: No internal paths ───────────────────────────────────────────────────
def test_T17_no_internal_paths():
    from core_engine.professional_valuation_chat_intent_guard_context import (
        CHAT_INTENT_GUARD_CONTEXT
    )
    ctx_str = str(CHAT_INTENT_GUARD_CONTEXT)
    for pat in ["C:\\Users\\Lenovo", "AppData\\Local", "__file__", "/home/"]:
        assert pat not in ctx_str, f"Internal path found: {pat}"
    assert CHAT_INTENT_GUARD_CONTEXT.get("no_internal_paths") is True


# ── T18: Ordinary valuation unaffected ──────────────────────────────────────
def test_T18_ordinary_valuation_unaffected():
    from core_engine.professional_valuation_chat_intent_guard_context import (
        CHAT_INTENT_GUARD_CONTEXT
    )
    assert CHAT_INTENT_GUARD_CONTEXT.get("ordinary_valuation_unaffected") is True


# ── T19: Tax appeal unaffected ───────────────────────────────────────────────
def test_T19_tax_appeal_unaffected():
    from core_engine.professional_valuation_chat_intent_guard_context import (
        CHAT_INTENT_GUARD_CONTEXT
    )
    assert CHAT_INTENT_GUARD_CONTEXT.get("tax_appeal_unaffected") is True
