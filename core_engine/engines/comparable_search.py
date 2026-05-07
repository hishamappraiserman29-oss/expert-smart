import json
import math
from pathlib import Path
from datetime import datetime, date
from typing import Optional
from .base import ValidationIssue


class ComparableSearchEngine:
    """
    Load market_feed.json once and expose a filter-based search API.

    Real data notes (as of Phase 4):
    - JSON is a flat array, not {"comparables": [...]}
    - Fields: area, price, price_per_meter, timestamp, location (string), year_built, credibility
    - No lat/lng in current data — distance filter is skipped per comparable when coordinates absent
    - property_type values are Arabic strings (e.g., "شقة سكنية", "فيلا", "تجاري")
    """

    def __init__(self, market_feed_path: str = "core_engine/data/market_feed.json"):
        self.comparables: list[dict] = []
        try:
            path = Path(market_feed_path)
            with path.open(encoding="utf-8") as f:
                raw = json.load(f)
        except FileNotFoundError:
            print(f"[ComparableSearchEngine] Warning: {market_feed_path} not found")
            return
        except json.JSONDecodeError as e:
            print(f"[ComparableSearchEngine] Warning: JSON parse error — {e}")
            return

        # Support both flat array and {"comparables": [...]} wrapper
        if isinstance(raw, list):
            records = raw
        elif isinstance(raw, dict):
            records = raw.get("comparables", [])
        else:
            records = []

        # Drop any soft-deleted records
        self.comparables = [r for r in records if not r.get("deleted", False)]

    # ──────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────

    def search(self, filters: dict) -> list[dict]:
        """
        Filter comparables by the given criteria and return enriched dicts.

        Required filter:
            latitude, longitude  — location of subject property

        Optional filters:
            property_type       str   exact match (case-insensitive)
            radius_meters       float default 5000
            area_sqm_min        float
            area_sqm_max        float
            max_age_months      int   based on timestamp
            finishing_levels    list  multi-select on finishing_level field
            location_text       str   substring match on location string

        Computed fields added to each result:
            distance_meters  — 0.0 when comparable has no coordinates
            price_per_sqm    — price / area
            area_sqm         — alias for area (for downstream engines)
            price_egp        — alias for price (for downstream engines)
        """
        lat = filters.get("latitude")
        lng = filters.get("longitude")

        # Location coordinates are required to anchor the search
        if lat is None or lng is None:
            return []

        radius = filters.get("radius_meters", 5000)
        if radius < 0:
            radius = 5000

        property_type    = filters.get("property_type")
        area_min         = filters.get("area_sqm_min")
        area_max         = filters.get("area_sqm_max")
        max_age_months   = filters.get("max_age_months")
        finishing_levels = filters.get("finishing_levels")
        location_text    = filters.get("location_text")

        # Swap silently if caller passed them reversed
        if area_min is not None and area_max is not None and area_min > area_max:
            area_min, area_max = area_max, area_min

        results = []
        for comp in self.comparables:

            # ── property_type ──────────────────────────────────────────
            if property_type is not None:
                if comp.get("property_type", "").lower() != property_type.lower():
                    continue

            # ── area ───────────────────────────────────────────────────
            comp_area = comp.get("area") or comp.get("area_sqm") or 0
            if area_min is not None and comp_area < area_min:
                continue
            if area_max is not None and comp_area > area_max:
                continue

            # ── location text substring match ──────────────────────────
            if location_text:
                if location_text.lower() not in str(comp.get("location", "")).lower():
                    continue

            # ── distance ───────────────────────────────────────────────
            # Current market_feed has string locations; compute only when lat/lng are present
            comp_loc = comp.get("location", {})
            if isinstance(comp_loc, dict):
                comp_lat = comp_loc.get("lat")
                comp_lng = comp_loc.get("lng")
            else:
                comp_lat, comp_lng = None, None

            if comp_lat is not None and comp_lng is not None:
                dist = self._distance_meters(lat, lng, comp_lat, comp_lng)
                if dist > radius:
                    continue
            else:
                # No coordinates in this comparable — distance filter not applicable
                dist = 0.0

            # ── age ────────────────────────────────────────────────────
            if max_age_months is not None:
                ts = comp.get("timestamp") or comp.get("transaction_date")
                days_ago = self._days_since(ts) if ts else None
                if days_ago is None or days_ago > max_age_months * 30:
                    continue

            # ── finishing_level ────────────────────────────────────────
            if finishing_levels:
                if comp.get("finishing_level", "") not in finishing_levels:
                    continue

            # ── Enrich ────────────────────────────────────────────────
            price = comp.get("price") or comp.get("price_egp") or 0
            area  = comp_area if comp_area > 0 else 1  # guard div-by-zero

            enriched = dict(comp)
            enriched["distance_meters"] = dist
            enriched["price_per_sqm"]   = round(price / area, 2)
            # Normalised aliases for downstream engines (Task 4.2+)
            enriched.setdefault("area_sqm",  area)
            enriched.setdefault("price_egp", price)
            results.append(enriched)

        return results

    # ──────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────

    def _distance_meters(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Approximate distance (metres) between two lat/lng points."""
        dlat_m = (lat2 - lat1) * 111000
        dlng_m = (lng2 - lng1) * 111000 * math.cos(math.radians(lat1))
        return math.sqrt(dlat_m ** 2 + dlng_m ** 2)

    def _days_since(self, transaction_date_str: str) -> Optional[int]:
        """
        Parse a date string and return elapsed days.
        Supports: ISO timestamps, YYYY-MM-DD, YYYY-MM.
        Returns None on parse failure (caller skips the comparable).
        """
        today = date.today()
        # Try formats from most to least specific
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
            "%Y-%m",
        ):
            try:
                s = transaction_date_str[:7] if fmt == "%Y-%m" else transaction_date_str
                parsed = datetime.strptime(s, fmt).date()
                return (today - parsed).days
            except ValueError:
                continue
        return None

    def _clamp(self, value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
        """Clamp value to [min_val, max_val]."""
        return max(min_val, min(max_val, value))

    # ──────────────────────────────────────────────────────────────────
    # Similarity scoring
    # ──────────────────────────────────────────────────────────────────

    def similarity_score(
        self,
        subject: dict,
        comparable: dict,
        search_radius_meters: float = 5000,
        area_tolerance_pct: float = 30,
        max_age_months: int = 24,
    ) -> dict:
        """
        Score ONE comparable against a subject property.

        Returns:
            {
                "similarity_score": float,   # 0-100 weighted total
                "breakdown": {               # 0-100 per factor
                    "distance":  float,
                    "area":      float,
                    "compound":  float,
                    "age":       float,
                    "finishing": float,
                    "recency":   float,
                }
            }

        Weights: distance 40%, area 20%, compound 15%, age 10%, finishing 10%, recency 5%.
        """
        # ── 1. Distance (40%) ────────────────────────────────────────
        dist = comparable.get("distance_meters", 0.0)
        radius = search_radius_meters if search_radius_meters > 0 else 5000
        distance_score = self._clamp(1.0 - dist / radius) * 100

        # ── 2. Area (20%) ────────────────────────────────────────────
        subject_area = subject.get("area_sqm") or 0
        comp_area    = comparable.get("area_sqm") or comparable.get("area") or 0
        if subject_area > 0 and comp_area > 0:
            area_pct_diff = abs(comp_area - subject_area) / subject_area * 100
            area_score = self._clamp(1.0 - area_pct_diff / area_tolerance_pct) * 100
        else:
            area_score = 0.0

        # ── 3. Compound match (15%) ───────────────────────────────────
        subject_compound = subject.get("compound_id")
        comp_compound    = comparable.get("compound_id")
        if subject_compound and comp_compound and subject_compound == comp_compound:
            compound_score = 100.0
        else:
            compound_score = 0.0

        # ── 4. Age similarity (10%) ───────────────────────────────────
        # Accept age_years directly or derive from year_built
        current_year = date.today().year
        subject_age = subject.get("age_years")
        if subject_age is None and subject.get("year_built"):
            subject_age = current_year - int(subject["year_built"])

        comp_age = comparable.get("age_years")
        if comp_age is None and comparable.get("year_built") and int(comparable.get("year_built", 0)) > 0:
            comp_age = current_year - int(comparable["year_built"])

        AGE_HORIZON = 30  # years beyond which age gap no longer matters
        if subject_age is not None and comp_age is not None:
            age_diff  = abs(subject_age - comp_age)
            age_score = self._clamp(1.0 - age_diff / AGE_HORIZON) * 100
        else:
            age_score = 50.0  # neutral — not penalised when data is absent

        # ── 5. Finishing level match (10%) ────────────────────────────
        subject_finish = subject.get("finishing_level")
        comp_finish    = comparable.get("finishing_level")
        if subject_finish and comp_finish and subject_finish == comp_finish:
            finishing_score = 100.0
        else:
            finishing_score = 0.0

        # ── 6. Recency (5%) ──────────────────────────────────────────
        ts = comparable.get("timestamp") or comparable.get("transaction_date")
        horizon_days = max_age_months * 30
        if ts:
            days_ago = self._days_since(ts)
            if days_ago is not None and horizon_days > 0:
                recency_score = self._clamp(1.0 - days_ago / horizon_days) * 100
            else:
                recency_score = 0.0
        else:
            recency_score = 0.0

        # ── Weighted total ────────────────────────────────────────────
        total = (
            0.40 * distance_score +
            0.20 * area_score     +
            0.15 * compound_score +
            0.10 * age_score      +
            0.10 * finishing_score +
            0.05 * recency_score
        )

        return {
            "similarity_score": round(total, 1),
            "breakdown": {
                "distance":  round(distance_score,  1),
                "area":      round(area_score,       1),
                "compound":  round(compound_score,   1),
                "age":       round(age_score,        1),
                "finishing": round(finishing_score,  1),
                "recency":   round(recency_score,    1),
            },
        }

    def search_and_rank(
        self,
        subject: dict,
        filters: dict,
        limit: int = 20,
    ) -> list[dict]:
        """
        Filter comparables, score each against subject, and return the top-N ranked list.

        Merges similarity_score + breakdown into each result dict.
        Results are sorted descending by similarity_score.
        """
        radius = filters.get("radius_meters", 5000)
        area_tol = filters.get("area_tolerance_pct", 30)
        max_age  = filters.get("max_age_months", 24)

        candidates = self.search(filters)

        for result in candidates:
            scored = self.similarity_score(
                subject,
                result,
                search_radius_meters=radius,
                area_tolerance_pct=area_tol,
                max_age_months=max_age,
            )
            result["similarity_score"]  = scored["similarity_score"]
            result["score_breakdown"]   = scored["breakdown"]

        candidates.sort(key=lambda r: r["similarity_score"], reverse=True)
        return candidates[:limit]
