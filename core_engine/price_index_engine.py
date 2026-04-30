"""
price_index_engine.py
======================
Real-Estate Price Index engine — مؤشر معدلات الزيادة في أسعار العقارات.

Implements four standard methodologies side-by-side, then reconciles them
into a single Composite Index per (region × property_type × month).

Methodologies:
    1. CMA  — Comparative Market Analysis (median of comparable transactions
              within same region + neighbouring locations).
    2. AVM  — Automated Valuation Model: time-weighted least-squares
              regression of price-per-meter on time, per stratum.
    3. RPPI — Real Estate Price Index (official). Accepts injected government
              series or, when absent, falls back to a volume-weighted hedonic
              index using the available transactions.
    4. Stratification — segments the market into homogeneous strata
              (area-size buckets × property type) and computes a per-stratum
              Laspeyres-style index. Aggregated to a stratified composite.

Public API:
    compute_price_index(records, *, base_period=None, region_filter=None,
                        property_type_filter=None, official_rppi=None) -> dict

Output JSON shape (suitable for direct UI consumption):
{
  "as_of":            "2026-04-25",
  "base_period":      "2025-01",
  "region_filter":    null,
  "property_type":    null,
  "regions": [
    {
      "region": "القاهرة الجديدة",
      "n_records": 132,
      "current_ppm": 28500.0,
      "cma_index": 112.4,           # Index where 100 = base period
      "cma_yoy_pct": 12.4,
      "cma_mom_pct": 0.8,
      "avm_index": 113.1,
      "avm_yoy_pct": 13.1,
      "avm_growth_per_month_pct": 1.1,
      "rppi_index": 110.0,
      "rppi_yoy_pct": 10.0,
      "strat_index": 111.7,
      "strat_yoy_pct": 11.7,
      "composite_index": 111.8,     # Average of available methodologies
      "composite_yoy_pct": 11.8,
      "alert": "ارتفاع طبيعي" | "قفزة سعرية" | "هبوط ملحوظ",
      "strata": [ {bucket, n, ppm_avg, mom_pct, yoy_pct}, ... ]
    },
    ...
  ],
  "summary": {
    "n_regions": 8, "avg_yoy_pct": 11.2, "highest_region": "...",
    "lowest_region": "...", "alert_count": 1
  },
  "methodology_notes": "..."
}
"""

from __future__ import annotations
import math
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


# ════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════════════════

def _parse_dt(ts: Any) -> Optional[datetime]:
    if isinstance(ts, datetime):
        return ts
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", ""))
    except Exception:
        try:
            return datetime.strptime(str(ts)[:10], "%Y-%m-%d")
        except Exception:
            return None


def _month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def _months_between(a: str, b: str) -> int:
    """How many months from a to b (both 'YYYY-MM')."""
    ya, ma = int(a[:4]), int(a[5:7])
    yb, mb = int(b[:4]), int(b[5:7])
    return (yb - ya) * 12 + (mb - ma)


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v) if v not in (None, "") else default
    except Exception:
        return default


def _median(values: List[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def _weighted_mean(pairs: List[Tuple[float, float]]) -> float:
    """pairs of (value, weight)."""
    total_w = sum(w for _, w in pairs if w > 0)
    if total_w <= 0:
        return 0.0
    return sum(v * w for v, w in pairs) / total_w


def _area_bucket(area: float) -> str:
    """Stratification bucket by floor area in m²."""
    if area <= 0:        return "غير محدد"
    if area < 80:        return "صغيرة (< 80م²)"
    if area < 150:       return "متوسطة (80–150م²)"
    if area < 250:       return "كبيرة (150–250م²)"
    if area < 500:       return "فاخرة (250–500م²)"
    return "مميزة (> 500م²)"


def _region_norm(s: Any) -> str:
    """Normalize region label (strip extra whitespace, fix garbage chars)."""
    s = str(s or "").strip()
    if not s or s == "??????? ???????" or all(c == "?" for c in s.replace(" ", "")):
        return "غير محدد"
    return s


# ════════════════════════════════════════════════════════════════════════════
#  CORE COMPUTATION
# ════════════════════════════════════════════════════════════════════════════

def _classify_alert(yoy_pct: float, mom_pct: float) -> str:
    if mom_pct >= 8.0 or yoy_pct >= 30.0:
        return "قفزة سعرية"
    if mom_pct <= -5.0 or yoy_pct <= -10.0:
        return "هبوط ملحوظ"
    if yoy_pct >= 15.0:
        return "نمو قوي"
    if yoy_pct <= 0:
        return "ركود"
    return "ارتفاع طبيعي"


def _cma_index(records: List[Dict[str, Any]], base_month: str,
               current_month: str) -> Tuple[float, float, float]:
    """
    Comparative Market Analysis.
    Index value for current period vs base, plus YoY & MoM percent changes.
    Uses median price-per-meter to be robust to outliers.
    """
    by_month: Dict[str, List[float]] = defaultdict(list)
    for r in records:
        m = r["_month_key"]
        ppm = r["_ppm"]
        if ppm > 0:
            by_month[m].append(ppm)

    base_ppm = _median(by_month.get(base_month, []))
    cur_ppm  = _median(by_month.get(current_month, []))
    if base_ppm <= 0:
        # fall back to earliest non-empty month
        for m in sorted(by_month.keys()):
            if by_month[m]:
                base_ppm = _median(by_month[m])
                break
    if cur_ppm <= 0 and by_month:
        latest_m = max(by_month.keys())
        cur_ppm = _median(by_month[latest_m])

    cma_index = (cur_ppm / base_ppm * 100.0) if base_ppm > 0 else 100.0

    # YoY: compare current to same month previous year
    try:
        cy, cm = int(current_month[:4]), int(current_month[5:7])
        prev_year_key = f"{cy - 1}-{cm:02d}"
        prev_year_ppm = _median(by_month.get(prev_year_key, []))
    except Exception:
        prev_year_ppm = 0.0

    yoy_pct = ((cur_ppm - prev_year_ppm) / prev_year_ppm * 100.0
               if prev_year_ppm > 0 else
               ((cma_index - 100.0)))

    # MoM: previous calendar month
    try:
        cy, cm = int(current_month[:4]), int(current_month[5:7])
        if cm == 1:
            prev_m_key = f"{cy - 1}-12"
        else:
            prev_m_key = f"{cy}-{cm - 1:02d}"
        prev_m_ppm = _median(by_month.get(prev_m_key, []))
    except Exception:
        prev_m_ppm = 0.0

    mom_pct = ((cur_ppm - prev_m_ppm) / prev_m_ppm * 100.0
               if prev_m_ppm > 0 else 0.0)

    return cma_index, yoy_pct, mom_pct


def _avm_index(records: List[Dict[str, Any]], base_month: str,
               current_month: str) -> Tuple[float, float, float]:
    """
    AVM — Time-weighted least-squares regression of ppm on time (months from base).
    Returns (index, yoy_pct, growth_per_month_pct).
    """
    if len(records) < 2:
        return 100.0, 0.0, 0.0

    # x = months since base, y = ppm
    pts: List[Tuple[float, float, float]] = []  # (x, y, weight)
    for r in records:
        if r["_ppm"] <= 0 or not r["_month_key"]:
            continue
        x = float(_months_between(base_month, r["_month_key"]))
        # Time weight: more recent transactions weighted higher
        cred = float(r.get("credibility", 0.7))
        pts.append((x, r["_ppm"], cred))

    if len(pts) < 2:
        return 100.0, 0.0, 0.0

    sw  = sum(w for _, _, w in pts)
    sx  = sum(x * w for x, _, w in pts) / sw
    sy  = sum(y * w for _, y, w in pts) / sw
    sxx = sum((x - sx) ** 2 * w for x, _, w in pts) / sw
    sxy = sum((x - sx) * (y - sy) * w for x, y, w in pts) / sw

    if sxx <= 0:
        return 100.0, 0.0, 0.0

    slope = sxy / sxx          # ppm per month
    intercept = sy - slope * sx

    # Predicted base ppm at month 0 = intercept
    # Predicted current ppm at month_x = intercept + slope * month_x
    cur_x  = float(_months_between(base_month, current_month))
    base_ppm_pred = intercept
    cur_ppm_pred  = intercept + slope * cur_x

    if base_ppm_pred <= 0:
        return 100.0, 0.0, 0.0

    avm_index = (cur_ppm_pred / base_ppm_pred) * 100.0
    growth_per_month_pct = (slope / base_ppm_pred) * 100.0
    yoy_pct = growth_per_month_pct * 12.0
    return avm_index, yoy_pct, growth_per_month_pct


def _rppi_index(records: List[Dict[str, Any]], base_month: str,
                current_month: str,
                official_series: Optional[Dict[str, float]] = None
                ) -> Tuple[float, float, str]:
    """
    Real-estate Price Property Index.

    If official_series ({'YYYY-MM': index_value}) is provided, use it directly.
    Otherwise compute a volume-weighted (Paasche-like) index from records.
    """
    if official_series:
        base_v = official_series.get(base_month)
        cur_v  = official_series.get(current_month)
        if base_v and cur_v and base_v > 0:
            idx = (cur_v / base_v) * 100.0
            yoy_pct = idx - 100.0
            return idx, yoy_pct, "official_government_series"

    # Volume-weighted internal RPPI (Paasche-like with current-period weights)
    by_month_v: Dict[str, List[Tuple[float, float]]] = defaultdict(list)  # ppm × area
    for r in records:
        if r["_ppm"] > 0 and r["_area"] > 0:
            by_month_v[r["_month_key"]].append((r["_ppm"], r["_area"]))

    def _vwm(month: str) -> float:
        return _weighted_mean(by_month_v.get(month, []))

    base_v = _vwm(base_month)
    cur_v  = _vwm(current_month)
    if base_v <= 0 and by_month_v:
        base_v = _vwm(min(by_month_v.keys()))
    if cur_v <= 0 and by_month_v:
        cur_v = _vwm(max(by_month_v.keys()))

    if base_v <= 0:
        return 100.0, 0.0, "internal_volume_weighted"

    idx = (cur_v / base_v) * 100.0
    yoy_pct = idx - 100.0
    return idx, yoy_pct, "internal_volume_weighted"


def _stratification_index(records: List[Dict[str, Any]], base_month: str,
                           current_month: str
                           ) -> Tuple[float, float, List[Dict[str, Any]]]:
    """
    Stratification: split by (property_type, area_bucket), compute per-stratum
    median price index, aggregate as a Laspeyres index using base-period
    transaction counts as weights.
    """
    strata_buckets: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for r in records:
        key = (str(r.get("property_type", "—") or "—"), _area_bucket(r["_area"]))
        strata_buckets[key].append(r)

    stratum_results: List[Dict[str, Any]] = []
    weighted_sum = 0.0
    total_weight = 0.0

    for (ptype, bucket), recs in strata_buckets.items():
        by_month = defaultdict(list)
        for r in recs:
            if r["_ppm"] > 0:
                by_month[r["_month_key"]].append(r["_ppm"])
        base_ppm = _median(by_month.get(base_month, []))
        cur_ppm  = _median(by_month.get(current_month, []))
        if base_ppm <= 0 and by_month:
            base_ppm = _median(by_month[min(by_month.keys())])
        if cur_ppm <= 0 and by_month:
            cur_ppm = _median(by_month[max(by_month.keys())])
        if base_ppm <= 0:
            continue

        ratio = cur_ppm / base_ppm
        n_base = len(by_month.get(base_month, [])) or 1
        weight = float(n_base)

        # MoM for stratum
        cy, cm = int(current_month[:4]), int(current_month[5:7])
        prev_m = f"{cy-1}-12" if cm == 1 else f"{cy}-{cm-1:02d}"
        prev_ppm = _median(by_month.get(prev_m, []))
        mom_pct = ((cur_ppm - prev_ppm) / prev_ppm * 100.0) if prev_ppm > 0 else 0.0

        stratum_results.append({
            "property_type":  ptype,
            "area_bucket":    bucket,
            "n_records":      len(recs),
            "base_ppm":       round(base_ppm, 2),
            "current_ppm":    round(cur_ppm, 2),
            "ratio":          round(ratio, 4),
            "yoy_pct":        round((ratio - 1) * 100.0, 2),
            "mom_pct":        round(mom_pct, 2),
        })

        weighted_sum += ratio * weight
        total_weight += weight

    if total_weight <= 0:
        return 100.0, 0.0, []

    composite_ratio = weighted_sum / total_weight
    return composite_ratio * 100.0, (composite_ratio - 1) * 100.0, stratum_results


# ════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ════════════════════════════════════════════════════════════════════════════

def compute_price_index(records: List[Dict[str, Any]], *,
                        base_period: Optional[str] = None,
                        region_filter: Optional[str] = None,
                        property_type_filter: Optional[str] = None,
                        official_rppi: Optional[Dict[str, Dict[str, float]]] = None
                        ) -> Dict[str, Any]:
    """
    Compute the multi-method price index from market_feed records.

    records :  list of dicts with keys timestamp, location, property_type,
               area, price, price_per_meter, credibility, ...
    base_period : 'YYYY-MM' to use as index base. Default = earliest month
                  found in data minus 0 (i.e. earliest itself).
    region_filter / property_type_filter : optional substring filters.
    official_rppi : optional {region: {'YYYY-MM': index_value}} for RPPI.

    Returns a JSON-serializable dict.
    """
    # ── Pre-process: enrich records with month_key + numeric fields ──────────
    enriched: List[Dict[str, Any]] = []
    for r in records:
        dt = _parse_dt(r.get("timestamp"))
        if dt is None:
            continue
        ppm = _safe_float(r.get("price_per_meter"))
        if ppm <= 0:
            area = _safe_float(r.get("area"))
            price = _safe_float(r.get("price"))
            if area > 0 and price > 0:
                ppm = price / area
        if ppm <= 0:
            continue
        enriched.append({
            **r,
            "_dt":           dt,
            "_month_key":    _month_key(dt),
            "_ppm":          ppm,
            "_area":         _safe_float(r.get("area")),
            "_region_norm":  _region_norm(r.get("location")),
        })

    if not enriched:
        return {
            "status":     "empty",
            "as_of":      datetime.now().strftime("%Y-%m-%d"),
            "regions":    [],
            "summary":    {"n_regions": 0, "n_records": 0},
            "methodology_notes": "لا توجد بيانات في market_feed لاحتساب المؤشر.",
        }

    # Apply filters
    if region_filter:
        enriched = [r for r in enriched if region_filter in r["_region_norm"]]
    if property_type_filter:
        enriched = [r for r in enriched
                    if property_type_filter in str(r.get("property_type", ""))]

    if not enriched:
        return {
            "status":  "empty",
            "as_of":   datetime.now().strftime("%Y-%m-%d"),
            "regions": [],
            "summary": {"n_regions": 0, "n_records": 0},
            "methodology_notes": "لا توجد بيانات تطابق الفلاتر المحددة.",
        }

    # Determine base / current month
    months = sorted({r["_month_key"] for r in enriched})
    base_month = base_period or months[0]
    current_month = months[-1]

    # ── Group by region ──────────────────────────────────────────────────────
    by_region: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in enriched:
        by_region[r["_region_norm"]].append(r)

    region_results: List[Dict[str, Any]] = []
    for region, recs in sorted(by_region.items()):
        if len(recs) < 1:
            continue

        # Current-period PPM (latest month median)
        cur_month_recs = [r for r in recs if r["_month_key"] == current_month]
        cur_ppm = _median([r["_ppm"] for r in cur_month_recs]) if cur_month_recs else \
                  _median([r["_ppm"] for r in recs])

        # 1) CMA
        cma_idx, cma_yoy, cma_mom = _cma_index(recs, base_month, current_month)
        # 2) AVM
        avm_idx, avm_yoy, avm_mpm = _avm_index(recs, base_month, current_month)
        # 3) RPPI
        official = (official_rppi or {}).get(region)
        rppi_idx, rppi_yoy, rppi_source = _rppi_index(recs, base_month, current_month,
                                                       official_series=official)
        # 4) Stratification
        strat_idx, strat_yoy, strata = _stratification_index(recs, base_month, current_month)

        # Composite — average of available methodologies
        composite_idx_vals = [v for v in (cma_idx, avm_idx, rppi_idx, strat_idx) if v > 0]
        composite_idx = sum(composite_idx_vals) / len(composite_idx_vals) if composite_idx_vals else 100.0
        composite_yoy_vals = [v for v in (cma_yoy, avm_yoy, rppi_yoy, strat_yoy) if not math.isnan(v)]
        composite_yoy = sum(composite_yoy_vals) / len(composite_yoy_vals) if composite_yoy_vals else 0.0

        alert = _classify_alert(composite_yoy, cma_mom)

        region_results.append({
            "region":            region,
            "n_records":         len(recs),
            "current_ppm":       round(cur_ppm, 2),
            "current_period":    current_month,
            "base_period":       base_month,
            "cma_index":         round(cma_idx, 2),
            "cma_yoy_pct":       round(cma_yoy, 2),
            "cma_mom_pct":       round(cma_mom, 2),
            "avm_index":         round(avm_idx, 2),
            "avm_yoy_pct":       round(avm_yoy, 2),
            "avm_growth_per_month_pct": round(avm_mpm, 3),
            "rppi_index":        round(rppi_idx, 2),
            "rppi_yoy_pct":      round(rppi_yoy, 2),
            "rppi_source":       rppi_source,
            "strat_index":       round(strat_idx, 2),
            "strat_yoy_pct":     round(strat_yoy, 2),
            "composite_index":   round(composite_idx, 2),
            "composite_yoy_pct": round(composite_yoy, 2),
            "alert":             alert,
            "strata":            strata,
        })

    # Sort by composite YoY desc (highest growth first)
    region_results.sort(key=lambda x: x["composite_yoy_pct"], reverse=True)

    # ── Summary block ────────────────────────────────────────────────────────
    yoy_values = [r["composite_yoy_pct"] for r in region_results]
    summary = {
        "n_regions":         len(region_results),
        "n_records":         sum(r["n_records"] for r in region_results),
        "avg_yoy_pct":       round(sum(yoy_values) / len(yoy_values), 2) if yoy_values else 0.0,
        "highest_region":    region_results[0]["region"] if region_results else None,
        "highest_yoy_pct":   region_results[0]["composite_yoy_pct"] if region_results else 0.0,
        "lowest_region":     region_results[-1]["region"] if region_results else None,
        "lowest_yoy_pct":    region_results[-1]["composite_yoy_pct"] if region_results else 0.0,
        "alert_count":       sum(1 for r in region_results
                                  if r["alert"] in ("قفزة سعرية", "هبوط ملحوظ")),
    }

    return {
        "status":               "success",
        "as_of":                datetime.now().strftime("%Y-%m-%d"),
        "base_period":          base_month,
        "current_period":       current_month,
        "region_filter":        region_filter,
        "property_type_filter": property_type_filter,
        "regions":              region_results,
        "summary":              summary,
        "methodology_notes": (
            "1) CMA يستخدم متوسط (median) سعر المتر من المعاملات المقارنة. "
            "2) AVM يطبق انحدار least-squares موزون بالمصداقية على ppm × زمن. "
            "3) RPPI يفضل السلسلة الحكومية الرسمية إذا توفرت، وإلا يحسب مؤشراً "
            "موزوناً بالمساحة (Paasche-like). "
            "4) Stratification يقسم السوق حسب (نوع الأصل × نطاق المساحة) "
            "ويحسب مؤشر Laspeyres مرجحاً. "
            "Composite Index = متوسط المنهجيات الأربع."
        ),
    }
