# -*- coding: utf-8 -*-
"""
fraud_detector.py — المُحقق الرقمي للكشف عن الشذوذ والغش العقاري
Expert_Smart Sovereign Edition

الخوارزمية:
  1. Z-Score vs نطاق السوق المعروف (_PRICE_RANGES من market_intelligence)
  2. IQR Fence vs مدخلات المقارنات
  3. نسبة الثقة (Confidence Score) متدنية عند الشذوذ + رسالة تحذير للمقيم
"""

from __future__ import annotations
import math
import statistics as _st
from typing import Optional, Dict, Any, List

# ── استيراد قاموس أسعار السوق من market_intelligence ──────────────────────
try:
    from market_intelligence import _PRICE_RANGES as _MKT_RANGES
except ImportError:
    _MKT_RANGES: dict = {"_default": (8_000, 22_000)}

# ── عتبات الثقة ────────────────────────────────────────────────────────────
_Z_HIGH    = 2.5    # Z-Score فوق هذا الحد → شذوذ مرتفع
_Z_WARN    = 1.5    # Z-Score فوق هذا الحد → تحذير
_CONF_BASE = 1.0    # نسبة الثقة الكاملة (100%)

# ── أنواع التحذير ──────────────────────────────────────────────────────────
_FLAG_NONE     = "سليم"
_FLAG_WARN     = "تحذير — مراجعة مطلوبة"
_FLAG_CRITICAL = "🚨 شذوذ حرج — احتمال تلاعب أو بيع قسري"


def _lookup_market_range(location: str) -> tuple[float, float]:
    """يبحث عن نطاق السعر للموقع (تطابق جزئي)."""
    for key, rng in _MKT_RANGES.items():
        if key != "_default" and key in location:
            return rng
    return _MKT_RANGES.get("_default", (8_000, 22_000))


def _zscore_vs_range(ppm: float, low: float, high: float) -> float:
    """
    Z-Score بسيط: كم انحراف معياري يبعد السعر عن مركز النطاق.
    الانحراف المعياري المُقدَّر = (high - low) / 4  (نفترض نطاق 4σ).
    """
    mid = (low + high) / 2
    sigma = max((high - low) / 4, 1.0)
    return abs(ppm - mid) / sigma


def _zscore_vs_comps(ppm: float, comps_ppms: List[float]) -> float:
    """Z-Score للسعر مقارنة بمجموعة المقارنات المُدخلة."""
    if len(comps_ppms) < 2:
        return 0.0
    mean  = _st.mean(comps_ppms)
    sigma = _st.stdev(comps_ppms)
    if sigma == 0:
        return 0.0
    return abs(ppm - mean) / sigma


def _confidence_from_z(z: float) -> float:
    """تحويل Z-Score إلى نسبة ثقة [0, 1]."""
    if z <= 1.0:
        return 1.0
    if z >= _Z_HIGH:
        return max(0.0, 1.0 - (z - 1.0) * 0.25)
    # خطي بين 1.0 و 2.5
    return round(1.0 - ((z - 1.0) / (_Z_HIGH - 1.0)) * 0.55, 3)


def _build_warning_message(
    ppm: float,
    low: float,
    high: float,
    z_mkt: float,
    z_comp: float,
    direction: str,   # "منخفض" | "مرتفع"
    location: str,
) -> str:
    lines = [
        f"⚠️ تنبيه المُحقق الرقمي — سعر المتر ({ppm:,.0f} ج.م) {direction} بشكل لافت",
        f"   النطاق السوقي المتوقع لـ ({location}): {low:,.0f} — {high:,.0f} ج.م/م²",
        f"   انحراف Z-Score عن السوق: {z_mkt:.2f}σ  |  عن المقارنات: {z_comp:.2f}σ",
    ]
    if direction == "منخفض":
        lines += [
            "   ► الاحتمالات الأكثر شيوعاً:",
            "     • بيع قسري أو ضائقة مالية حادة للبائع",
            "     • عقد صوري (التلاعب في وثائق الملكية)",
            "     • عقار مُثقل بحجوزات أو رهون غير مُفصح عنها",
        ]
    else:
        lines += [
            "   ► الاحتمالات الأكثر شيوعاً:",
            "     • تضخيم القيمة للحصول على قرض مصرفي أعلى (Mortgage Fraud)",
            "     • غسيل أموال عبر معاملات عقارية فوق السوق",
            "     • بيانات مدخلة بالخطأ (خطأ في المساحة أو العملة)",
        ]
    lines.append("   ► التوصية: يرجى التحقق الميداني والحصول على 3 مقارنات إضافية مستقلة.")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# الدالة الرئيسية
# ═══════════════════════════════════════════════════════════════════════════

def detect_fraud(
    price_per_meter: float,
    location: str = "",
    property_type: str = "",
    comp_ppms: Optional[List[float]] = None,
    area_m2: float = 0.0,
    total_price: float = 0.0,
) -> Dict[str, Any]:
    """
    يُحلّل سعر المتر المُدخل ويكتشف الشذوذ.

    المُخرجات:
      confidence_score  : float [0.0 – 1.0]   (1.0 = سليم تماماً)
      confidence_pct    : str   "94%"
      flag              : str   سليم | تحذير | شذوذ حرج
      z_score_market    : float
      z_score_comps     : float
      market_low        : float
      market_high       : float
      direction         : str   "منخفض" | "مرتفع" | "طبيعي"
      warning_message   : str   (فارغ إذا لا يوجد شذوذ)
      recommendation    : str
      details           : dict
    """
    ppm = float(price_per_meter or 0)
    comps = [float(x) for x in (comp_ppms or []) if float(x) > 0]

    # ── 1. نطاق السوق ────────────────────────────────────────────────────
    low, high = _lookup_market_range(location)

    # ── 2. Z-Scores ──────────────────────────────────────────────────────
    z_mkt  = _zscore_vs_range(ppm, low, high) if ppm > 0 else 0.0
    z_comp = _zscore_vs_comps(ppm, comps)     if comps  else 0.0
    z_max  = max(z_mkt, z_comp)

    # ── 3. اتجاه الشذوذ ──────────────────────────────────────────────────
    mid = (low + high) / 2
    if ppm <= 0:
        direction = "غير محدد"
    elif ppm < mid:
        direction = "منخفض"
    else:
        direction = "مرتفع"

    # ── 4. نسبة الثقة ────────────────────────────────────────────────────
    conf = _confidence_from_z(z_max)

    # ── 5. تصنيف التحذير ─────────────────────────────────────────────────
    if z_max >= _Z_HIGH:
        flag = _FLAG_CRITICAL
    elif z_max >= _Z_WARN:
        flag = _FLAG_WARN
    else:
        flag = _FLAG_NONE

    # ── 6. رسالة التحذير ─────────────────────────────────────────────────
    warning = ""
    if flag != _FLAG_NONE and ppm > 0:
        warning = _build_warning_message(ppm, low, high, z_mkt, z_comp, direction, location)

    # ── 7. توصية مختصرة ──────────────────────────────────────────────────
    if conf >= 0.90:
        rec = "السعر ضمن النطاق السوقي الطبيعي — لا توجد مؤشرات شذوذ."
    elif conf >= 0.70:
        rec = "السعر يحتاج مراجعة — يُنصح بإضافة مقارنات إضافية لتأكيد القيمة."
    elif conf >= 0.50:
        rec = "⚠️ ابحث عن 3 مقارنات مستقلة وتحقق من سجلات الملكية قبل إصدار التقرير."
    else:
        rec = "🚨 أوقف إجراءات التقييم حتى يتم التحقق الميداني والقانوني من صحة البيانات."

    # ── 8. تفاصيل الحساب ─────────────────────────────────────────────────
    comp_stats: dict = {}
    if comps:
        comp_stats = {
            "mean":   round(_st.mean(comps), 0),
            "median": round(_st.median(comps), 0),
            "std":    round(_st.stdev(comps) if len(comps) > 1 else 0, 0),
            "count":  len(comps),
        }

    return {
        "confidence_score": round(conf, 3),
        "confidence_pct":   f"{conf * 100:.1f}%",
        "flag":             flag,
        "z_score_market":   round(z_mkt, 3),
        "z_score_comps":    round(z_comp, 3),
        "market_low":       low,
        "market_high":      high,
        "market_mid":       round(mid, 0),
        "direction":        direction,
        "warning_message":  warning,
        "recommendation":   rec,
        "details": {
            "input_ppm":    ppm,
            "location":     location,
            "property_type": property_type,
            "area_m2":      area_m2,
            "total_price":  total_price,
            "comp_stats":   comp_stats,
        },
    }
