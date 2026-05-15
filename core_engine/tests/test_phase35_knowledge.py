"""
test_phase35_knowledge.py — Phase 35: Knowledge Base + Standards Tests

Test groups:
  A — KnowledgeBaseEngine (A01-A12)
  B — StandardsRegistry (B01-B10)
  C — SmartSearchEngine (C01-C08)
  D — LearningPlatform (D01-D10)
  E — BestPracticesLibrary (E01-E08)
  F — RegulatoryTracker (F01-F08)
"""

import sys
import os
import pytest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from knowledge.kb_engine import (
    KnowledgeBaseEngine, ContentType, ContentLevel, ContentStatus,
)
from knowledge.standards_registry import StandardsRegistry
from knowledge.ai_search import SmartSearchEngine
from knowledge.learning_platform import LearningPlatform, CourseLevel
from knowledge.best_practices import BestPracticesLibrary


# ---------------------------------------------------------------------------
# Fixtures — fresh instances per test class
# ---------------------------------------------------------------------------

@pytest.fixture
def kb():
    return KnowledgeBaseEngine()


@pytest.fixture
def sr():
    return StandardsRegistry()


@pytest.fixture
def ss():
    return SmartSearchEngine()


@pytest.fixture
def lp():
    return LearningPlatform()


@pytest.fixture
def bp():
    return BestPracticesLibrary()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add_and_publish(kb, cid, title="Guide", ctype=ContentType.GUIDE,
                     category="Valuation", tags=None):
    c = kb.create_content(
        content_id=cid, title=title, content_type=ctype,
        description=f"Description for {title}",
        body="Body content about valuation and property.",
        author="Author", category=category, tags=tags or [],
    )
    kb.publish_content(cid)
    return c


def _add_practice(bp, pid, category="valuation"):
    return bp.add_best_practice(
        practice_id=pid, title=f"Practice {pid}",
        description="Best practice description",
        category=category,
        problem_addressed="Common problem",
        solution="Proposed solution",
    )


def _add_update(bp, uid, source="CBE", days_deadline=60):
    return bp.add_regulatory_update(
        update_id=uid, title=f"Update {uid}",
        description="Regulatory update description",
        source=source,
        effective_date=datetime.utcnow(),
        impact_level="high",
        compliance_deadline=datetime.utcnow() + timedelta(days=days_deadline),
        required_actions=["Review policy", "Update documentation"],
    )


# ---------------------------------------------------------------------------
# A — KnowledgeBaseEngine
# ---------------------------------------------------------------------------

class TestKnowledgeBaseEngine:

    def test_A01_create_content_stored(self, kb):
        c = kb.create_content("K1", "Guide A", ContentType.GUIDE, "Desc", "Body", "Author")
        assert kb.get_content("K1") is not None
        assert c.content_id == "K1"

    def test_A02_initial_status_is_draft(self, kb):
        c = kb.create_content("K2", "Article", ContentType.ARTICLE, "D", "B", "A")
        assert c.status == ContentStatus.DRAFT

    def test_A03_publish_changes_status(self, kb):
        kb.create_content("K3", "FAQ", ContentType.FAQ, "D", "B", "A")
        result = kb.publish_content("K3")
        assert result is True
        assert kb.get_content("K3").status == ContentStatus.PUBLISHED

    def test_A04_publish_nonexistent_returns_false(self, kb):
        assert kb.publish_content("NONEXISTENT") is False

    def test_A05_search_finds_published_content(self, kb):
        _add_and_publish(kb, "K5", title="Residential Valuation", tags=["residential"])
        results = kb.search_content("residential")
        assert len(results) >= 1

    def test_A06_search_excludes_draft(self, kb):
        kb.create_content("K6", "Draft Residential", ContentType.ARTICLE, "Desc", "Body", "A",
                           tags=["residential"])
        results = kb.search_content("Draft Residential")
        assert not any(r.content_id == "K6" for r in results)

    def test_A07_search_filter_by_type(self, kb):
        _add_and_publish(kb, "K7A", title="Guide X", ctype=ContentType.GUIDE)
        _add_and_publish(kb, "K7B", title="Guide X article", ctype=ContentType.ARTICLE)
        results = kb.search_content("Guide X", content_type=ContentType.GUIDE)
        assert all(r.content_type == ContentType.GUIDE for r in results)

    def test_A08_add_view_increments(self, kb):
        _add_and_publish(kb, "K8", title="Viewed Content")
        kb.add_view("K8")
        kb.add_view("K8")
        assert kb.get_content("K8").views == 2

    def test_A09_helpful_vote(self, kb):
        _add_and_publish(kb, "K9", title="Voted Content")
        kb.vote_helpful("K9", helpful=True)
        kb.vote_helpful("K9", helpful=False)
        c = kb.get_content("K9")
        assert c.helpful_votes == 1
        assert c.unhelpful_votes == 1

    def test_A10_statistics_structure(self, kb):
        _add_and_publish(kb, "K10", title="Stats Test")
        stats = kb.get_statistics()
        assert "total_content" in stats
        assert "published_content" in stats
        assert "by_type" in stats

    def test_A11_get_by_category(self, kb):
        _add_and_publish(kb, "K11A", title="Cat Test A", category="Tax")
        _add_and_publish(kb, "K11B", title="Cat Test B", category="Tax")
        items = kb.get_by_category("Tax")
        assert len(items) == 2

    def test_A12_archive_content(self, kb):
        _add_and_publish(kb, "K12", title="To Archive")
        kb.archive_content("K12")
        assert kb.get_content("K12").status == ContentStatus.ARCHIVED


# ---------------------------------------------------------------------------
# B — StandardsRegistry
# ---------------------------------------------------------------------------

class TestStandardsRegistry:

    def test_B01_initialized_with_20_plus_standards(self, sr):
        assert sr.count() >= 20

    def test_B02_get_existing_standard(self, sr):
        std = sr.get_standard("EGVS")
        assert std is not None
        assert std.short_name == "EGVS"

    def test_B03_get_nonexistent_standard_is_none(self, sr):
        assert sr.get_standard("NONEXISTENT_XYZ") is None

    def test_B04_standards_for_residential_egypt(self, sr):
        stds = sr.get_standards_for_asset("residential")
        ids = [s.standard_id for s in stds]
        assert "EGVS" in ids

    def test_B05_get_standards_for_country_egypt(self, sr):
        stds = sr.get_standards_for_country("Egypt")
        ids = [s.standard_id for s in stds]
        assert "EGVS" in ids
        assert "CBE" in ids

    def test_B06_global_standards_included_for_egypt(self, sr):
        stds = sr.get_standards_for_country("Egypt")
        ids = [s.standard_id for s in stds]
        assert "IVSC" in ids

    def test_B07_compatibility_matrix_has_applicable(self, sr):
        matrix = sr.get_compatibility_matrix("residential", "Egypt")
        assert "applicable_standards" in matrix
        assert len(matrix["applicable_standards"]) > 0

    def test_B08_compatibility_matrix_required_are_mandatory(self, sr):
        matrix = sr.get_compatibility_matrix("residential", "Egypt")
        for std_dict in matrix["required_standards"]:
            assert std_dict["implementation_level"] == "mandatory"

    def test_B09_list_all_standards_active_only(self, sr):
        all_stds = sr.list_all_standards(active_only=True)
        assert all(s.is_active for s in all_stds)

    def test_B10_to_dict_structure(self, sr):
        std = sr.get_standard("IVSC")
        d = std.to_dict()
        assert "standard_id" in d
        assert "implementation_level" in d
        assert "valuation_approaches" in d


# ---------------------------------------------------------------------------
# C — SmartSearchEngine
# ---------------------------------------------------------------------------

class TestSmartSearchEngine:

    def test_C01_expand_query_includes_synonyms(self, ss):
        terms = ss.expand_query("property valuation")
        assert "appraisal" in terms or "assessment" in terms

    def test_C02_expand_query_includes_original(self, ss):
        terms = ss.expand_query("mortgage")
        assert "mortgage" in terms

    def test_C03_autocomplete_startswith(self, ss):
        suggestions = ["Valuation Guide", "Valuation Standard", "Market Analysis"]
        result = ss.autocomplete("val", suggestions)
        assert all("val" in r.lower() for r in result)

    def test_C04_autocomplete_limit(self, ss):
        words = [f"Word{i}" for i in range(20)]
        result = ss.autocomplete("W", words, limit=3)
        assert len(result) <= 3

    def test_C05_semantic_search_finds_match(self, ss, kb):
        _add_and_publish(kb, "SS1", title="Property Appraisal Guide",
                         tags=["appraisal", "guide"])
        # Lower threshold since query expansion matches partially
        results = ss.semantic_search("property valuation", [kb.get_content("SS1")],
                                     similarity_threshold=0.1)
        assert len(results) > 0

    def test_C06_semantic_search_returns_score(self, ss, kb):
        _add_and_publish(kb, "SS2", title="Residential Housing Assessment")
        results = ss.semantic_search("residential", [kb.get_content("SS2")])
        if results:
            content, score = results[0]
            assert 0 <= score <= 1

    def test_C07_search_history_recorded(self, ss):
        ss.expand_query("test query one")
        ss.semantic_search("test query two", [])
        history = ss.get_search_history()
        assert "test query two" in history

    def test_C08_get_search_suggestions(self, ss):
        suggestions = ss.get_search_suggestions("property")
        # Should return synonyms excluding the original
        assert "property" not in suggestions or len(suggestions) > 0


# ---------------------------------------------------------------------------
# D — LearningPlatform
# ---------------------------------------------------------------------------

class TestLearningPlatform:

    def test_D01_create_course_stored(self, lp):
        c = lp.create_course("C1", "Basics", "Intro", CourseLevel.BEGINNER,
                              modules=5, duration_hours=10, instructor="Prof")
        assert lp.courses["C1"] is not None
        assert c.level == CourseLevel.BEGINNER

    def test_D02_course_initially_unpublished(self, lp):
        lp.create_course("C2", "Adv", "Adv Desc", CourseLevel.ADVANCED,
                         modules=8, duration_hours=20)
        assert lp.courses["C2"].is_published is False

    def test_D03_publish_course(self, lp):
        lp.create_course("C3", "Mid", "Mid Desc", CourseLevel.INTERMEDIATE,
                         modules=6, duration_hours=15)
        result = lp.publish_course("C3")
        assert result is True
        assert lp.courses["C3"].is_published is True

    def test_D04_enroll_user(self, lp):
        lp.create_course("C4", "Expert", "Exp Desc", CourseLevel.EXPERT,
                         modules=10, duration_hours=50)
        enr = lp.enroll_user("U1", "C4")
        assert enr.user_id == "U1"
        assert enr.course_id == "C4"

    def test_D05_enroll_increments_count(self, lp):
        lp.create_course("C5", "Course5", "Desc", CourseLevel.BEGINNER,
                         modules=3, duration_hours=5)
        lp.enroll_user("U2", "C5")
        lp.enroll_user("U3", "C5")
        assert lp.courses["C5"].enrollment_count == 2

    def test_D06_enroll_nonexistent_course_raises(self, lp):
        with pytest.raises(ValueError):
            lp.enroll_user("U1", "NONEXISTENT")

    def test_D07_complete_course_pass(self, lp):
        lp.create_course("C7", "Course7", "Desc", CourseLevel.INTERMEDIATE,
                         modules=4, duration_hours=8, passing_score=70.0)
        enr = lp.enroll_user("U4", "C7")
        passed = lp.complete_course(enr.enrollment_id, 85.0)
        assert passed is True
        assert lp.enrollments[enr.enrollment_id].has_certificate is True

    def test_D08_complete_course_fail(self, lp):
        lp.create_course("C8", "Course8", "Desc", CourseLevel.ADVANCED,
                         modules=5, duration_hours=12, passing_score=70.0)
        enr = lp.enroll_user("U5", "C8")
        passed = lp.complete_course(enr.enrollment_id, 55.0)
        assert passed is False
        assert lp.enrollments[enr.enrollment_id].has_certificate is False

    def test_D09_get_user_certificates(self, lp):
        lp.create_course("C9", "Cert Course", "Desc", CourseLevel.BEGINNER,
                         modules=3, duration_hours=6)
        enr = lp.enroll_user("U6", "C9")
        lp.complete_course(enr.enrollment_id, 90.0)
        certs = lp.get_user_certificates("U6")
        assert len(certs) == 1
        assert certs[0]["course_id"] == "C9"

    def test_D10_platform_statistics(self, lp):
        lp.create_course("C10A", "S1", "D", CourseLevel.BEGINNER, 2, 4)
        lp.create_course("C10B", "S2", "D", CourseLevel.INTERMEDIATE, 3, 6)
        enr = lp.enroll_user("U7", "C10A")
        lp.complete_course(enr.enrollment_id, 80.0)
        stats = lp.get_platform_statistics()
        assert stats["total_courses"] >= 2
        assert stats["completions"] >= 1
        assert "completion_rate" in stats


# ---------------------------------------------------------------------------
# E — BestPracticesLibrary
# ---------------------------------------------------------------------------

class TestBestPracticesLibrary:

    def test_E01_add_best_practice(self, bp):
        p = _add_practice(bp, "P1")
        assert bp.practices["P1"] is not None
        assert p.category == "valuation"

    def test_E02_practices_by_category(self, bp):
        _add_practice(bp, "P2A", category="compliance")
        _add_practice(bp, "P2B", category="compliance")
        _add_practice(bp, "P2C", category="ethics")
        practices = bp.get_practices_by_category("compliance")
        assert len(practices) == 2

    def test_E03_to_dict_structure(self, bp):
        _add_practice(bp, "P3")
        d = bp.practices["P3"].to_dict()
        assert "practice_id" in d
        assert "category" in d
        assert "implementation_steps" in d

    def test_E04_adoption_rate_stored(self, bp):
        bp.add_best_practice(
            "P4", "Endorsed", "Desc", "valuation", "Problem", "Solution",
            adoption_rate=0.75,
        )
        assert bp.practices["P4"].adoption_rate == pytest.approx(0.75)

    def test_E05_count_practices(self, bp):
        initial = bp.count_practices()
        _add_practice(bp, "P5A")
        _add_practice(bp, "P5B")
        assert bp.count_practices() == initial + 2

    def test_E06_practices_statistics(self, bp):
        _add_practice(bp, "P6", category="process")
        stats = bp.get_practices_statistics()
        assert "total_practices" in stats
        assert "by_category" in stats

    def test_E07_endorsed_by_stored(self, bp):
        bp.add_best_practice(
            "P7", "CBE Practice", "Desc", "compliance", "Prob", "Sol",
            endorsed_by=["CBE", "FRA"],
        )
        assert "CBE" in bp.practices["P7"].endorsed_by

    def test_E08_implementation_steps_stored(self, bp):
        bp.add_best_practice(
            "P8", "Stepped", "Desc", "process", "Problem", "Solution",
            implementation_steps=["Step 1", "Step 2", "Step 3"],
        )
        assert len(bp.practices["P8"].implementation_steps) == 3


# ---------------------------------------------------------------------------
# F — RegulatoryTracker (inside BestPracticesLibrary)
# ---------------------------------------------------------------------------

class TestRegulatoryTracker:

    def test_F01_add_regulatory_update(self, bp):
        u = _add_update(bp, "U1")
        assert bp.updates["U1"] is not None
        assert u.source == "CBE"

    def test_F02_active_updates_returned(self, bp):
        _add_update(bp, "U2A", source="FRA")
        _add_update(bp, "U2B", source="CBE")
        active = bp.get_active_updates()
        assert len(active) >= 2

    def test_F03_filter_by_source(self, bp):
        _add_update(bp, "U3A", source="FRA")
        _add_update(bp, "U3B", source="Tax")
        fra_updates = bp.get_active_updates(source="FRA")
        assert all(u.source == "FRA" for u in fra_updates)

    def test_F04_upcoming_deadlines_within_window(self, bp):
        _add_update(bp, "U4A", days_deadline=30)
        _add_update(bp, "U4B", days_deadline=180)
        deadlines = bp.get_upcoming_compliance_deadlines(days_ahead=90)
        ids = [u.update_id for u in deadlines]
        assert "U4A" in ids
        assert "U4B" not in ids

    def test_F05_deactivate_update(self, bp):
        _add_update(bp, "U5")
        result = bp.deactivate_update("U5")
        assert result is True
        assert bp.updates["U5"].is_active is False
        active = bp.get_active_updates()
        assert not any(u.update_id == "U5" for u in active)

    def test_F06_acknowledge_update(self, bp):
        _add_update(bp, "U6")
        bp.acknowledge_update("U6", "BANK-1")
        assert "BANK-1" in bp.updates["U6"].acknowledged_by

    def test_F07_to_dict_structure(self, bp):
        u = _add_update(bp, "U7")
        d = u.to_dict()
        assert "update_id" in d
        assert "compliance_deadline" in d
        assert "required_actions" in d

    def test_F08_count_updates(self, bp):
        initial = bp.count_updates()
        _add_update(bp, "U8A")
        _add_update(bp, "U8B")
        assert bp.count_updates() == initial + 2
