"""
comparable_search.py — Advanced Comparable Search Engine (Phase 37)

Multi-criteria comparable property search with similarity scoring.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SearchType(str, Enum):
    EXACT = "exact"
    SIMILAR = "similar"
    RANGE = "range"
    FUZZY = "fuzzy"


class PropertyAttribute(str, Enum):
    LOCATION = "location"
    AREA = "area_sqm"
    PRICE = "price"
    TYPE = "property_type"
    AGE = "age_years"
    CONDITION = "condition"
    BEDROOMS = "bedrooms"
    BATHROOMS = "bathrooms"
    PARKING = "parking"
    FEATURES = "features"


@dataclass
class SearchCriteria:
    property_type: str
    location: str
    area_sqm_min: float
    area_sqm_max: float
    price_min: float
    price_max: float

    distance_km: float = 5.0
    sale_date_months_back: int = 12

    age_min: Optional[int] = None
    age_max: Optional[int] = None
    condition: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    parking_spaces: Optional[int] = None

    min_similarity_score: float = 0.7
    max_results: int = 10
    sort_by: str = "similarity"

    exclude_property_ids: List[str] = field(default_factory=list)
    required_features: List[str] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "property_type": self.property_type,
            "location": self.location,
            "area_sqm": f"{self.area_sqm_min}-{self.area_sqm_max}",
            "price": f"{self.price_min}-{self.price_max}",
            "distance_km": self.distance_km,
            "sale_date_months": self.sale_date_months_back,
        }


@dataclass
class ComparableResult:
    property_id: str
    property_data: Dict[str, Any]

    similarity_score: float
    match_percentage: float
    distance_km: float
    price_per_sqm: float
    days_since_sale: int

    score_breakdown: Dict[str, float] = field(default_factory=dict)

    is_adjusted: bool = False
    adjustment_factors: Dict[str, float] = field(default_factory=dict)
    adjusted_price: Optional[float] = None

    rank: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "property_id": self.property_id,
            "similarity_score": round(self.similarity_score, 2),
            "match_percentage": round(self.match_percentage, 2),
            "distance_km": round(self.distance_km, 2),
            "price": self.property_data.get("price", 0),
            "price_per_sqm": round(self.price_per_sqm, 2),
            "days_since_sale": self.days_since_sale,
            "rank": self.rank,
            "adjusted_price": self.adjusted_price,
            "score_breakdown": {k: round(v, 2) for k, v in self.score_breakdown.items()},
        }


class ComparableSearchEngine:
    """Advanced comparable search engine with multi-criteria filtering."""

    def __init__(self) -> None:
        self.properties: Dict[str, Dict[str, Any]] = {}
        self.recent_searches: Dict[str, List[SearchCriteria]] = {}
        self._lock = threading.Lock()
        logger.info("Comparable Search Engine initialized")

    def register_property(self, property_id: str, property_data: Dict[str, Any]) -> bool:
        with self._lock:
            self.properties[property_id] = property_data
        logger.info("Property registered: %s", property_id)
        return True

    def search_comparables(
        self,
        criteria: SearchCriteria,
        user_id: Optional[str] = None,
    ) -> List[ComparableResult]:
        logger.info("Searching comparables: %s in %s", criteria.property_type, criteria.location)

        with self._lock:
            snapshot = dict(self.properties)

        results: List[ComparableResult] = []

        candidates = self._filter_properties(criteria, snapshot)

        now = datetime.utcnow()
        threshold = criteria.min_similarity_score * 100

        for property_id, property_data in candidates.items():
            if property_id in criteria.exclude_property_ids:
                continue

            similarity_score, score_breakdown = self._calculate_similarity(criteria, property_data)

            if similarity_score < threshold:
                continue

            distance_km = self._calculate_distance(
                criteria.location, property_data.get("location", "")
            )
            if distance_km > criteria.distance_km:
                continue

            sale_date = property_data.get("sale_date")
            if isinstance(sale_date, datetime):
                days_since = (now - sale_date).days
            else:
                days_since = 0

            if days_since > criteria.sale_date_months_back * 30:
                continue

            price = property_data.get("price", 0)
            area = property_data.get("area_sqm", 1)
            price_per_sqm = price / area if area > 0 else 0

            result = ComparableResult(
                property_id=property_id,
                property_data=property_data,
                similarity_score=similarity_score,
                match_percentage=similarity_score,
                distance_km=distance_km,
                price_per_sqm=price_per_sqm,
                days_since_sale=days_since,
                score_breakdown=score_breakdown,
            )
            results.append(result)

        results = self._sort_results(results, criteria.sort_by)
        results = results[: criteria.max_results]

        for i, result in enumerate(results, 1):
            result.rank = i

        if user_id:
            with self._lock:
                self.recent_searches.setdefault(user_id, []).append(criteria)

        logger.info("Found %d comparables", len(results))
        return results

    # ── internals ──────────────────────────────────────────────────────────────

    def _filter_properties(
        self, criteria: SearchCriteria, snapshot: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        filtered: Dict[str, Dict[str, Any]] = {}
        for pid, data in snapshot.items():
            if data.get("property_type", "").lower() != criteria.property_type.lower():
                continue
            area = data.get("area_sqm", 0)
            if not (criteria.area_sqm_min <= area <= criteria.area_sqm_max):
                continue
            price = data.get("price", 0)
            if not (criteria.price_min <= price <= criteria.price_max):
                continue
            if criteria.condition and data.get("condition", "").lower() != criteria.condition.lower():
                continue
            if criteria.age_min is not None and data.get("age_years", 0) < criteria.age_min:
                continue
            if criteria.age_max is not None and data.get("age_years", 0) > criteria.age_max:
                continue
            if criteria.required_features:
                prop_features = data.get("features", [])
                if not all(f in prop_features for f in criteria.required_features):
                    continue
            filtered[pid] = data
        return filtered

    def _calculate_similarity(
        self, criteria: SearchCriteria, property_data: Dict[str, Any]
    ) -> Tuple[float, Dict[str, float]]:
        scores: Dict[str, float] = {}
        weights: Dict[str, float] = {}

        # Area similarity (midpoint-based, 20% weight)
        area_mid = (criteria.area_sqm_min + criteria.area_sqm_max) / 2
        area_half = (criteria.area_sqm_max - criteria.area_sqm_min) / 2
        area_diff = abs(area_mid - property_data.get("area_sqm", 0))
        scores["area"] = max(0.0, 100.0 - (area_diff / area_half * 100.0)) if area_half > 0 else 100.0
        weights["area"] = 0.20

        # Price similarity (midpoint-based, 20% weight)
        price_mid = (criteria.price_min + criteria.price_max) / 2
        price_half = (criteria.price_max - criteria.price_min) / 2
        price_diff = abs(price_mid - property_data.get("price", 0))
        scores["price"] = max(0.0, 100.0 - (price_diff / price_half * 100.0)) if price_half > 0 else 100.0
        weights["price"] = 0.20

        # Location similarity (25% weight)
        location_same = criteria.location.lower() == property_data.get("location", "").lower()
        scores["location"] = 100.0 if location_same else 50.0
        weights["location"] = 0.25

        # Condition similarity (15% weight)
        if criteria.condition:
            cond_same = criteria.condition.lower() == property_data.get("condition", "").lower()
            scores["condition"] = 100.0 if cond_same else 70.0
        else:
            scores["condition"] = 80.0
        weights["condition"] = 0.15

        # Features similarity (20% weight)
        if criteria.required_features:
            prop_features = property_data.get("features", [])
            matching = sum(1 for f in criteria.required_features if f in prop_features)
            scores["features"] = matching / len(criteria.required_features) * 100.0
        else:
            scores["features"] = 80.0
        weights["features"] = 0.20

        total_weight = sum(weights.values())
        weighted_score = sum(scores[k] * weights[k] for k in scores) / total_weight
        return weighted_score, scores

    def _calculate_distance(self, location1: str, location2: str) -> float:
        if location1.lower() == location2.lower():
            return 0.0
        return 5.0

    def _sort_results(self, results: List[ComparableResult], sort_by: str) -> List[ComparableResult]:
        if sort_by == "similarity":
            results.sort(key=lambda x: x.similarity_score, reverse=True)
        elif sort_by == "price":
            results.sort(key=lambda x: x.property_data.get("price", 0))
        elif sort_by == "date":
            results.sort(key=lambda x: x.days_since_sale)
        elif sort_by == "distance":
            results.sort(key=lambda x: x.distance_km)
        return results

    def get_search_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            if user_id and user_id in self.recent_searches:
                searches = self.recent_searches[user_id]
                now = datetime.utcnow()
                return {
                    "total_searches": len(searches),
                    "recent_searches": sum(
                        1 for s in searches if (now - s.created_at).days <= 7
                    ),
                    "last_search": searches[-1].created_at.isoformat() if searches else None,
                }
            return {
                "total_properties": len(self.properties),
                "indexed_properties": len(self.properties),
            }

    def count(self) -> int:
        with self._lock:
            return len(self.properties)


comparable_search = ComparableSearchEngine()
