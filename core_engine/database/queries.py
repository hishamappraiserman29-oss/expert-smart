"""
queries.py — ORM query builders for Phase 4 comparable search.

SearchComparable provides a fluent (method-chaining) API wrapping
SQLAlchemy queries against the comparables table.

Usage::

    results = (
        SearchComparable(session)
        .by_property_type('apartment')
        .by_governorate('Cairo')
        .by_area_range(100, 200)
        .limit(20)
        .execute()
    )
"""
from __future__ import annotations

import sys
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database.models import Comparable  # noqa: E402


# ── Geographic helper ────────────────────────────────────────────

def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in metres between two (lat, lon) points."""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * asin(sqrt(a)) * 6_371_000   # Earth radius in m


# ── Query builder ────────────────────────────────────────────────

class SearchComparable:
    """
    Fluent query builder for the ``comparables`` table.

    All filter methods return ``self`` so calls can be chained freely.
    Filters accumulate with AND logic.  Call ``execute()`` or
    ``to_dict_list()`` to materialise results.
    """

    def __init__(self, session: Session) -> None:
        self.session = session
        self.query = session.query(Comparable)

    # ── Filters ──────────────────────────────────────────────────

    def by_property_type(self, property_type: str) -> "SearchComparable":
        """Filter by property type (apartment, villa, office, …)."""
        self.query = self.query.filter(Comparable.property_type == property_type)
        return self

    def by_area_range(self, min_sqm: float, max_sqm: float) -> "SearchComparable":
        """Filter to properties whose area falls within [min_sqm, max_sqm]."""
        self.query = self.query.filter(
            and_(
                Comparable.area_sqm >= min_sqm,
                Comparable.area_sqm <= max_sqm,
            )
        )
        return self

    def by_price_range(self, min_egp: float, max_egp: float) -> "SearchComparable":
        """Filter to properties whose price falls within [min_egp, max_egp]."""
        self.query = self.query.filter(
            and_(
                Comparable.price_egp >= min_egp,
                Comparable.price_egp <= max_egp,
            )
        )
        return self

    def by_governorate(self, governorate: str) -> "SearchComparable":
        """Filter by governorate name (exact match)."""
        self.query = self.query.filter(Comparable.governorate == governorate)
        return self

    def by_location(
        self,
        latitude: float,
        longitude: float,
        radius_meters: float = 5_000,
    ) -> "SearchComparable":
        """
        Filter comparables within ``radius_meters`` of the given point.

        Applies the Haversine formula in Python after fetching candidate IDs,
        then replaces the internal query with an IN-filter on matched IDs.
        Records without coordinates are excluded from location results.
        """
        nearby_ids = [
            comp.id
            for comp in self.query.all()
            if comp.latitude is not None
            and comp.longitude is not None
            and _haversine_m(
                latitude, longitude,
                float(comp.latitude), float(comp.longitude),
            ) <= radius_meters
        ]
        self.query = self.session.query(Comparable).filter(
            Comparable.id.in_(nearby_ids)
        )
        return self

    def by_age_range(self, min_years: int, max_years: int) -> "SearchComparable":
        """Filter to properties whose age falls within [min_years, max_years]."""
        self.query = self.query.filter(
            and_(
                Comparable.age_years >= min_years,
                Comparable.age_years <= max_years,
            )
        )
        return self

    def by_quality_tier(self, quality_tier: str) -> "SearchComparable":
        """Filter by quality tier (luxury, standard, economy)."""
        self.query = self.query.filter(Comparable.quality_tier == quality_tier)
        return self

    def by_data_quality(self, min_score: float = 0.7) -> "SearchComparable":
        """Filter to records whose data_quality_score >= min_score."""
        self.query = self.query.filter(
            Comparable.data_quality_score >= min_score
        )
        return self

    # ── Pagination ────────────────────────────────────────────────

    def limit(self, count: int) -> "SearchComparable":
        """Cap the result set at ``count`` rows."""
        self.query = self.query.limit(count)
        return self

    # ── Terminal operations ────────────────────────────────────────

    def execute(self) -> List[Comparable]:
        """Materialise and return all matching Comparable rows."""
        return self.query.all()

    def count(self) -> int:
        """
        Return the number of matching rows.

        Note: if ``.limit()`` was applied before ``.count()``, SQLAlchemy
        wraps the limited query in a subquery, so the count reflects the
        limited set.  Call ``.count()`` *before* ``.limit()`` for a total
        count without pagination.
        """
        return self.query.count()

    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Execute the query and serialise each row to a plain dict."""
        return [
            {
                "id":                 str(c.id),
                "property_type":      c.property_type,
                "area_sqm":           c.area_sqm,
                "price_egp":          c.price_egp,
                "price_per_sqm":      c.price_per_sqm,
                "age_years":          c.age_years,
                "quality_tier":       c.quality_tier,
                "governorate":        c.governorate,
                "location":           c.location_description,
                "latitude":           c.latitude,
                "longitude":          c.longitude,
                "data_quality_score": c.data_quality_score,
            }
            for c in self.execute()
        ]
