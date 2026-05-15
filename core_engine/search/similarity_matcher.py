"""
similarity_matcher.py — Smart Similarity Matcher (Phase 37)

AI-powered property matching with multiple strategies and graded scoring.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MatchingStrategy(str, Enum):
    EXACT = "exact"
    WEIGHTED = "weighted"
    MACHINE_LEARNING = "ml"
    HYBRID = "hybrid"


@dataclass
class MatchingProfile:
    property_id: str
    attributes: Dict[str, float]
    attribute_weights: Dict[str, float]
    flexible_attributes: Dict[str, Tuple[float, float]]
    fixed_attributes: List[str] = field(default_factory=list)
    preference_location: Optional[str] = None
    max_distance_km: float = 5.0
    matching_strategy: MatchingStrategy = MatchingStrategy.WEIGHTED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "property_id": self.property_id,
            "strategy": self.matching_strategy.value,
            "attributes": len(self.attributes),
            "fixed_attributes": self.fixed_attributes,
        }


@dataclass
class MatchScore:
    subject_id: str
    comparable_id: str
    overall_score: float
    component_scores: Dict[str, float]
    match_explanation: str
    match_grade: str = "F"
    is_match: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "comparable_id": self.comparable_id,
            "overall_score": round(self.overall_score, 2),
            "match_grade": self.match_grade,
            "is_match": self.is_match,
            "explanation": self.match_explanation,
            "component_scores": {k: round(v, 2) for k, v in self.component_scores.items()},
        }


class SmartMatcher:
    """Intelligent property matcher with four strategies."""

    _STRING_ATTRS = {"property_type", "condition", "location"}

    def __init__(self) -> None:
        self.default_weights: Dict[str, float] = {
            "area_sqm": 0.20,
            "price": 0.20,
            "location": 0.25,
            "age_years": 0.10,
            "condition": 0.15,
            "bedrooms": 0.05,
            "bathrooms": 0.05,
        }
        logger.info("Smart Matcher initialized")

    def match_properties(
        self,
        subject: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        strategy: MatchingStrategy = MatchingStrategy.WEIGHTED,
    ) -> List[MatchScore]:
        dispatcher = {
            MatchingStrategy.EXACT: self._match_exact,
            MatchingStrategy.WEIGHTED: self._match_weighted,
            MatchingStrategy.MACHINE_LEARNING: self._match_ml,
            MatchingStrategy.HYBRID: self._match_hybrid,
        }
        fn = dispatcher[strategy]
        matches = [fn(subject, c) for c in candidates]
        matches.sort(key=lambda x: x.overall_score, reverse=True)
        return matches

    # ── strategies ─────────────────────────────────────────────────────────────

    def _match_exact(self, subject: Dict[str, Any], candidate: Dict[str, Any]) -> MatchScore:
        attrs = ["property_type", "location", "condition"]
        matched = sum(
            1 for a in attrs if subject.get(a) == candidate.get(a)
        )
        component_scores = {
            a: (100.0 if subject.get(a) == candidate.get(a) else 0.0) for a in attrs
        }
        overall = matched / len(attrs) * 100
        return MatchScore(
            subject_id=subject.get("property_id", "unknown"),
            comparable_id=candidate.get("property_id", "unknown"),
            overall_score=overall,
            component_scores=component_scores,
            match_explanation="Exact match on key attributes" if overall > 75 else "Partial match",
            match_grade=self._score_to_grade(overall),
            is_match=overall > 75,
        )

    def _match_weighted(self, subject: Dict[str, Any], candidate: Dict[str, Any]) -> MatchScore:
        component_scores: Dict[str, float] = {}
        total_weight = 0.0
        weighted_sum = 0.0

        for attr, weight in self.default_weights.items():
            if attr in subject and attr in candidate:
                score = self._calculate_attribute_similarity(attr, subject[attr], candidate[attr])
                component_scores[attr] = score
                weighted_sum += score * weight
                total_weight += weight

        overall = weighted_sum / total_weight if total_weight > 0 else 0.0
        return MatchScore(
            subject_id=subject.get("property_id", "unknown"),
            comparable_id=candidate.get("property_id", "unknown"),
            overall_score=overall,
            component_scores=component_scores,
            match_explanation=self._generate_explanation(overall, component_scores),
            match_grade=self._score_to_grade(overall),
            is_match=overall > 70,
        )

    def _match_ml(self, subject: Dict[str, Any], candidate: Dict[str, Any]) -> MatchScore:
        # Production: replace with trained model; uses weighted as baseline.
        return self._match_weighted(subject, candidate)

    def _match_hybrid(self, subject: Dict[str, Any], candidate: Dict[str, Any]) -> MatchScore:
        exact = self._match_exact(subject, candidate)
        weighted = self._match_weighted(subject, candidate)
        combined = weighted.overall_score * 0.6 + exact.overall_score * 0.4
        merged = {**exact.component_scores, **weighted.component_scores}
        return MatchScore(
            subject_id=subject.get("property_id", "unknown"),
            comparable_id=candidate.get("property_id", "unknown"),
            overall_score=combined,
            component_scores=merged,
            match_explanation="Hybrid match using exact and weighted criteria",
            match_grade=self._score_to_grade(combined),
            is_match=combined > 70,
        )

    # ── helpers ────────────────────────────────────────────────────────────────

    def _calculate_attribute_similarity(self, attr: str, subject_val: Any, candidate_val: Any) -> float:
        if attr in self._STRING_ATTRS:
            return 100.0 if str(subject_val).lower() == str(candidate_val).lower() else 50.0

        # Numeric
        try:
            sv, cv = float(subject_val), float(candidate_val)
        except (TypeError, ValueError):
            return 50.0

        if sv == 0:
            return 100.0
        pct_diff = abs(sv - cv) / sv * 100
        if pct_diff <= 5:
            return 100.0
        if pct_diff <= 10:
            return 90.0
        if pct_diff <= 20:
            return 80.0
        if pct_diff <= 30:
            return 70.0
        return max(0.0, 100.0 - pct_diff)

    def _generate_explanation(self, overall_score: float, component_scores: Dict[str, float]) -> str:
        if overall_score > 90:
            return "Excellent match - very similar properties"
        if overall_score > 75:
            return "Good match - mostly similar properties"
        if overall_score > 60:
            return "Fair match - some similarities"
        if overall_score > 40:
            return "Weak match - limited similarities"
        return "Poor match - very different properties"

    def _score_to_grade(self, score: float) -> str:
        if score >= 95:
            return "A+"
        if score >= 90:
            return "A"
        if score >= 85:
            return "B+"
        if score >= 80:
            return "B"
        if score >= 75:
            return "B-"
        if score >= 70:
            return "C+"
        if score >= 60:
            return "C"
        return "F"


smart_matcher = SmartMatcher()
