"""
avm_dispatcher.py
==================
AVM (Automated Valuation Model) dispatcher — wires regression-based price
estimation into specific valuation purposes WITHOUT touching the rest of
the engine.

Eligible purposes (configurable):
    - fair_market_value         (Market Value — primary AVM use case)
    - bank_financing            (Basel III LTV — needs robust statistical anchor)
    - tax_assessment            (Mass Appraisal — IAAO best practice)
    - acquisition               (M&A — investment-driven, AVM as sanity check)

Other purposes are intentionally NOT eligible — their methodologies (forced
liquidation, insurance reinstatement, usufruct PV, REIT NAV, HBU NPV, EIA ERF)
do not benefit from AVM and must remain untouched.

Public API:
    is_avm_eligible(purpose)            -> bool
    compute_avm_estimate(payload, records=None) -> dict
    dispatch_avm(payload, records=None) -> dict
        Returns enrichment dict to merge into the response. Pure side-effect:
        if `payload["price_per_meter"]` is missing or zero AND data is sufficient,
        the AVM-derived ppm is injected into the payload (in-place) so the
        downstream `advanced_valuation` flow uses it transparently.

Confidence policy:
    - n_records >= 30 and time_span >= 6 months → "high"   (1.00 weight)
    - n_records >= 10 and time_span >= 3 months → "medium" (0.50 weight)
    - else                                       → "low"   (0.0 — AVM disabled)
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional


# ── Eligibility configuration (additive — does NOT modify _PURPOSE_PROFILES) ─
_AVM_ELIGIBLE_PURPOSES = {
    "fair_market_value",
    "bank_financing",
    "tax_assessment",
    "acquisition",
}

# ── Statistical thresholds ──────────────────────────────────────────────────
_MIN_N_RECORDS_FOR_AVM   = 10        # below this → AVM disabled
_MIN_TIME_SPAN_MONTHS    = 3
_HIGH_CONF_N             = 30
_HIGH_CONF_MONTHS        = 6


def is_avm_eligible(purpose: str) -> bool:
    """Check if a purpose is eligible for AVM-driven valuation."""
    return (purpose or "").strip() in _AVM_ELIGIBLE_PURPOSES


def list_avm_eligible_purposes() -> List[str]:
    return sorted(_AVM_ELIGIBLE_PURPOSES)


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v) if v not in (None, "") else default
    except Exception:
        return default


def _filter_records_for_location(records: List[Dict[str, Any]],
                                  location: str,
                                  property_type: Optional[str] = None
                                  ) -> List[Dict[str, Any]]:
    """
    Region-matching strategy:
      1. Exact substring match on the location string.
      2. If property_type is supplied, also filter on it.
      3. Returns whatever survives filtering — no fallback to global pool.
    """
    if not location:
        return []
    loc_norm = str(location).strip()
    out = []
    for r in records:
        rl = str(r.get("location", "")).strip()
        if not rl or loc_norm not in rl and rl not in loc_norm:
            continue
        if property_type:
            rt = str(r.get("property_type", "")).strip()
            if rt and property_type not in rt and rt not in property_type:
                # Loose match — allow if either substring matches the other
                continue
        out.append(r)
    return out


def _load_records_safely() -> List[Dict[str, Any]]:
    """Load market_feed.json without raising. Returns [] on any error."""
    try:
        try:
            from bridge_api import _load_feed as _lf  # type: ignore
        except Exception:
            from core_engine.bridge_api import _load_feed as _lf  # type: ignore
        return _lf() or []
    except Exception:
        # Direct fallback — read JSON file
        import json, os
        for candidate in (
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "market_feed.json"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core_engine", "data", "market_feed.json"),
        ):
            if os.path.exists(candidate):
                try:
                    with open(candidate, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass
        return []


# ════════════════════════════════════════════════════════════════════════════
#  CORE
# ════════════════════════════════════════════════════════════════════════════

def compute_avm_estimate(payload: Dict[str, Any],
                          records: Optional[List[Dict[str, Any]]] = None
                          ) -> Dict[str, Any]:
    """
    Computes the AVM-derived price-per-meter for the given location +
    property type, using time-weighted least-squares on market_feed records.

    Returns a dict (never raises). Always includes:
        eligible       : bool
        confidence     : "high" | "medium" | "low" | "none"
        avm_ppm        : float (0 if not enough data)
        avm_index      : float (100-base index value at current period)
        avm_yoy_pct    : float
        avm_growth_per_month_pct : float
        n_records      : int (matched within region)
        time_span_months : int
        weight_uplift  : float in [0, 1] — recommended bonus weight for AVM
        method         : description string
        source         : "price_index_engine._avm_index"
    """
    purpose       = str(payload.get("valuation_purpose") or "").strip()
    location      = str(payload.get("location") or "").strip()
    property_type = str(payload.get("property_type") or "").strip()

    base_ret = {
        "eligible":                 is_avm_eligible(purpose),
        "confidence":               "none",
        "avm_ppm":                  0.0,
        "avm_index":                100.0,
        "avm_yoy_pct":              0.0,
        "avm_growth_per_month_pct": 0.0,
        "n_records":                0,
        "time_span_months":         0,
        "weight_uplift":            0.0,
        "method":                   "Time-weighted Least-Squares Regression on price-per-meter",
        "source":                   "price_index_engine._avm_index",
        "notes":                    "",
    }

    if not is_avm_eligible(purpose):
        base_ret["notes"] = f"الغرض '{purpose}' ليس ضمن قائمة الأغراض المؤهلة للـ AVM."
        return base_ret

    if records is None:
        records = _load_records_safely()

    matched = _filter_records_for_location(records, location, property_type)
    base_ret["n_records"] = len(matched)

    if len(matched) < _MIN_N_RECORDS_FOR_AVM:
        base_ret["notes"] = (
            f"بيانات غير كافية: {len(matched)} سجل فقط، الحد الأدنى {_MIN_N_RECORDS_FOR_AVM}. "
            f"AVM غير مفعَّل — تُستخدم منهجية التقييم التقليدية."
        )
        return base_ret

    # Compute time span
    months_seen = set()
    for r in matched:
        try:
            ts = r.get("timestamp")
            if ts:
                dt = datetime.fromisoformat(str(ts).replace("Z", "")[:19])
                months_seen.add(dt.strftime("%Y-%m"))
        except Exception:
            pass
    time_span = len(months_seen)
    base_ret["time_span_months"] = time_span

    if time_span < _MIN_TIME_SPAN_MONTHS:
        base_ret["notes"] = (
            f"النطاق الزمني للبيانات قصير: {time_span} شهر. "
            f"AVM يحتاج ≥ {_MIN_TIME_SPAN_MONTHS} أشهر لاحتساب اتجاه موثوق."
        )
        return base_ret

    # Run AVM via price_index_engine — single-region wrapper
    try:
        try:
            from price_index_engine import compute_price_index
        except Exception:
            from core_engine.price_index_engine import compute_price_index  # type: ignore

        # We don't filter by property_type here — let the engine see the full
        # regional context; we already filtered records by location above.
        idx_res = compute_price_index(matched)
    except Exception as e:
        base_ret["notes"] = f"تعذر تشغيل price_index_engine: {e}"
        return base_ret

    if idx_res.get("status") != "success" or not idx_res.get("regions"):
        base_ret["notes"] = "محرك المؤشر لم يُرجع نتائج صالحة لهذه المنطقة."
        return base_ret

    # Pick the region with the most records (best statistical anchor)
    region_block = max(idx_res["regions"], key=lambda r: r["n_records"])
    avm_ppm = float(region_block.get("current_ppm") or 0)

    # Confidence determination
    n = base_ret["n_records"]
    if n >= _HIGH_CONF_N and time_span >= _HIGH_CONF_MONTHS:
        confidence    = "high"
        weight_uplift = 1.00
    elif n >= _MIN_N_RECORDS_FOR_AVM and time_span >= _MIN_TIME_SPAN_MONTHS:
        confidence    = "medium"
        weight_uplift = 0.50
    else:
        confidence    = "low"
        weight_uplift = 0.20

    base_ret.update({
        "confidence":               confidence,
        "avm_ppm":                  round(avm_ppm, 2),
        "avm_index":                region_block.get("avm_index", 100.0),
        "avm_yoy_pct":              region_block.get("avm_yoy_pct", 0.0),
        "avm_growth_per_month_pct": region_block.get("avm_growth_per_month_pct", 0.0),
        "weight_uplift":            weight_uplift,
        "matched_region":           region_block.get("region"),
        "current_period":           region_block.get("current_period"),
        "base_period":              region_block.get("base_period"),
        "notes":                    (
            f"AVM مفعَّل — confidence={confidence}، "
            f"بناءً على {n} معاملة عبر {time_span} شهر."
        ),
    })
    return base_ret


# ════════════════════════════════════════════════════════════════════════════
#  DISPATCH — entry point for /api/valuation integration
# ════════════════════════════════════════════════════════════════════════════

def dispatch_avm(payload: Dict[str, Any],
                  records: Optional[List[Dict[str, Any]]] = None
                  ) -> Dict[str, Any]:
    """
    Side-effecting dispatcher used by /api/valuation BEFORE advanced_valuation.

    Behavior (additive only — never blocks the standard flow):
      1. If purpose is not in the eligible set → returns minimal result, no side effects.
      2. If user already supplied price_per_meter → AVM is computed for *informational*
         purposes only; user value is NEVER overwritten.
      3. If user did NOT supply price_per_meter AND AVM confidence ≥ medium,
         `payload["price_per_meter"]` is set IN-PLACE so downstream advanced_valuation
         consumes it transparently. A meta flag `avm_injected_ppm=True` is added.
      4. Returns the AVM result dict + a "verdict" string for inclusion in API response.
    """
    purpose = str(payload.get("valuation_purpose") or "").strip()

    # Quick reject: not eligible — don't even compute, save cycles
    if not is_avm_eligible(purpose):
        return {
            "applied":        False,
            "eligible":       False,
            "purpose":        purpose,
            "reason":         f"الغرض '{purpose}' غير مؤهل للـ AVM (الأغراض المؤهلة: {sorted(_AVM_ELIGIBLE_PURPOSES)}).",
            "avm_ppm":        0.0,
            "user_ppm_kept":  True,
        }

    avm = compute_avm_estimate(payload, records=records)

    user_ppm = _safe_float(payload.get("price_per_meter"))
    decision = {
        "applied":        False,
        "eligible":       True,
        "purpose":        purpose,
        "user_ppm":       user_ppm,
        "avm":            avm,
        "user_ppm_kept":  True,
    }

    # Decide whether to inject the AVM ppm into the payload
    if avm["confidence"] in ("high", "medium") and avm["avm_ppm"] > 0 and user_ppm <= 0:
        payload["price_per_meter"] = avm["avm_ppm"]
        payload["avm_injected_ppm"] = True
        payload["avm_meta"] = avm
        decision["applied"] = True
        decision["user_ppm_kept"] = False
        decision["verdict"] = (
            f"تم اعتماد سعر المتر من AVM = {avm['avm_ppm']:,.0f} ج.م "
            f"(confidence={avm['confidence']}, n={avm['n_records']} معاملة)."
        )
    elif avm["confidence"] in ("high", "medium") and user_ppm > 0:
        # User-supplied — AVM serves as sanity check / cross-validation
        payload["avm_meta"] = avm
        spread_pct = ((user_ppm - avm["avm_ppm"]) / avm["avm_ppm"] * 100.0
                      if avm["avm_ppm"] > 0 else 0.0)
        decision["spread_pct"] = round(spread_pct, 2)
        if abs(spread_pct) > 15:
            decision["verdict"] = (
                f"تنبيه: سعر المتر المُدخَل ({user_ppm:,.0f}) ينحرف "
                f"{spread_pct:+.1f}% عن AVM ({avm['avm_ppm']:,.0f}). راجع المصدر."
            )
        else:
            decision["verdict"] = (
                f"AVM يُقارب المُدخَل (انحراف {spread_pct:+.1f}%) — التقييم متسق."
            )
    else:
        decision["verdict"] = (
            f"AVM لم يُفعَّل: {avm.get('notes', 'بيانات غير كافية')}. "
            f"التقييم يستخدم المنهجية التقليدية الكاملة."
        )

    return decision
