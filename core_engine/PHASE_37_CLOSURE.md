# Phase 37 Closure — Comparable Search Enhancement

## Status: COMPLETE

**Date:** 2026-05-09
**Tests:** 34/34 pass (A01–C10)
**Full suite:** 1015 passed, 3 pre-existing failures (Phase 15 e2e, unrelated)

---

## Modules Delivered

| File | Class | Purpose |
|------|-------|---------|
| `search/comparable_search.py` | `ComparableSearchEngine` | Multi-criteria search: type/area/price/condition/age/features filters, midpoint-based similarity scoring, distance check, sale-date window, sort/limit/rank |
| `search/similarity_matcher.py` | `SmartMatcher` | 4 strategies (exact/weighted/ML/hybrid), per-attribute scoring, A+→F grading |
| `search/adjustment_factors.py` | `AdjustmentFactorEngine` | 7 adjustment categories; time/condition/location factory methods; cumulative apply |
| `search/__init__.py` | — | Package exports |

## Key Design Decisions

- **Midpoint similarity** — area and price similarity uses range midpoint as target (not max), ensuring properties at the centre of the search range score highest.
- **Distance fallback** — same location = 0 km, different location = 5 km default; default `distance_km=5.0` so cross-location comparables pass unless a tighter radius is requested.
- **Adjustments** — applied cumulatively as percentage of original price (not compounded); confidence = mean reliability of applied adjustments.

## API Endpoints Added to bridge_api.py

- `GET  /api/search/info`
- `POST /api/search/properties/register`
- `POST /api/search/comparables`
- `POST /api/search/match`

All endpoints use `_SEARCH_OK` guard (503 if module fails to load) and plain `jsonify()`.

## Notes

- No regressions in Phases 1–36.
- Total Flask routes: ~163 (was 159).
