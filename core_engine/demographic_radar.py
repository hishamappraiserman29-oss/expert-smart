# -*- coding: utf-8 -*-
"""
demographic_radar.py — رادار الهجرة العقارية وتحليل الزحف العمراني
Expert_Smart Sovereign Edition

يُحلّل:
  1. كثافة نقاط الاهتمام (POIs) المحيطة: مدارس / مستشفيات / مراكز تجارية / نقل
  2. اتجاه الطلب العمراني (نمو / تشبع / انكماش)
  3. توصية استباقية للمستثمر بالمناطق الصاعدة

مصدر البيانات: Nominatim/OSM + Mock POI Density Tables (PoC)
"""

from __future__ import annotations
import math
from typing import Dict, Any, List, Optional

# ═══════════════════════════════════════════════════════════════════════════
# جداول كثافة POI النموذجية (PoC)
# درجة الكثافة: 0-10  (10 = مشبع تماماً، 0 = فارغ)
# ═══════════════════════════════════════════════════════════════════════════

_POI_DENSITY: Dict[str, Dict[str, float]] = {
    # الحي → {نوع_POI: كثافة}
    "التجمع الخامس":    {"schools": 8.5, "hospitals": 6.0, "malls": 9.0, "transit": 4.0, "mosques": 8.0},
    "التجمع الأول":     {"schools": 7.0, "hospitals": 5.0, "malls": 7.5, "transit": 3.5, "mosques": 7.0},
    "القاهرة الجديدة":  {"schools": 8.0, "hospitals": 6.5, "malls": 8.5, "transit": 4.5, "mosques": 8.0},
    "العاصمة الإدارية": {"schools": 5.0, "hospitals": 4.0, "malls": 5.0, "transit": 6.0, "mosques": 4.0},
    "مدينة نصر":        {"schools": 9.5, "hospitals": 9.0, "malls": 9.5, "transit": 8.5, "mosques": 9.5},
    "الزمالك":          {"schools": 8.0, "hospitals": 8.5, "malls": 7.0, "transit": 7.0, "mosques": 7.5},
    "المعادي":          {"schools": 8.5, "hospitals": 7.5, "malls": 8.0, "transit": 7.0, "mosques": 8.0},
    "الشيخ زايد":       {"schools": 7.5, "hospitals": 6.0, "malls": 8.0, "transit": 5.0, "mosques": 7.5},
    "6 أكتوبر":         {"schools": 7.0, "hospitals": 6.5, "malls": 7.5, "transit": 5.5, "mosques": 8.0},
    "بدر":              {"schools": 4.0, "hospitals": 3.0, "malls": 3.5, "transit": 3.0, "mosques": 5.0},
    "الشروق":           {"schools": 5.5, "hospitals": 4.0, "malls": 4.5, "transit": 3.0, "mosques": 6.0},
    "العبور":           {"schools": 5.0, "hospitals": 4.5, "malls": 5.0, "transit": 4.0, "mosques": 6.0},
    "المستقبل سيتي":    {"schools": 3.5, "hospitals": 2.5, "malls": 3.0, "transit": 2.5, "mosques": 3.0},
    "سوهاج الجديدة":    {"schools": 3.0, "hospitals": 2.5, "malls": 2.0, "transit": 2.0, "mosques": 4.0},
    "الغردقة":          {"schools": 6.0, "hospitals": 5.0, "malls": 7.0, "transit": 4.0, "mosques": 6.0},
    "_default":         {"schools": 5.0, "hospitals": 4.5, "malls": 5.0, "transit": 4.0, "mosques": 5.0},
}

# عتبات التشبع
_SAT_HIGH   = 8.5   # تشبع مرتفع → انتقال الطلب
_SAT_MED    = 6.5   # متوسط
_GROWTH_LOW = 4.0   # مناطق في طور النمو

# ── خريطة الطلب المنتقل (من → إلى مع نسبة الانتقال) ──────────────────────
_DEMAND_FLOW: Dict[str, List[Dict[str, Any]]] = {
    "مدينة نصر":       [{"to": "التجمع الخامس", "pct": 25}, {"to": "القاهرة الجديدة", "pct": 15}],
    "التجمع الخامس":   [{"to": "العاصمة الإدارية", "pct": 20}, {"to": "المستقبل سيتي", "pct": 10}],
    "الزمالك":         [{"to": "المعادي", "pct": 15}, {"to": "الشيخ زايد", "pct": 20}],
    "6 أكتوبر":        [{"to": "الشيخ زايد", "pct": 20}, {"to": "المستقبل سيتي", "pct": 15}],
    "المعادي":         [{"to": "التجمع الأول", "pct": 18}, {"to": "الشروق", "pct": 10}],
    "_default":        [{"to": "مناطق التوسع الجديدة", "pct": 15}],
}

# ── مناطق الفرص الصاعدة (Rising Stars) ───────────────────────────────────
_RISING_STARS: List[Dict[str, Any]] = [
    {"name": "العاصمة الإدارية",  "score": 9.2, "driver": "قرار حكومي + مقرات وزارية", "horizon_yr": 3},
    {"name": "المستقبل سيتي",     "score": 7.8, "driver": "قرب جامعات + مشاريع تجارية", "horizon_yr": 4},
    {"name": "بدر",               "score": 7.1, "driver": "امتداد طبيعي للتجمع + مترو", "horizon_yr": 5},
    {"name": "الشروق",            "score": 6.8, "driver": "توسع خدمات + سعر أقل 40%",   "horizon_yr": 4},
    {"name": "سوهاج الجديدة",     "score": 6.5, "driver": "دعم حكومي + جامعات",         "horizon_yr": 6},
]


def _lookup_poi(location: str) -> Dict[str, float]:
    for key, val in _POI_DENSITY.items():
        if key != "_default" and key in location:
            return val
    return _POI_DENSITY["_default"]


def _saturation_level(poi: Dict[str, float]) -> str:
    avg = sum(poi.values()) / len(poi) if poi else 5.0
    if avg >= _SAT_HIGH:
        return "مشبع — تشبّع المنطقة بالخدمات"
    elif avg >= _SAT_MED:
        return "ناضج — خدمات جيدة ونمو ثابت"
    elif avg >= _GROWTH_LOW:
        return "في طور النمو — خدمات في تطور"
    else:
        return "ناشئ — فرصة مبكرة عالية المخاطر"


def _demand_outlook(location: str, poi: Dict[str, float]) -> Dict[str, Any]:
    avg = sum(poi.values()) / len(poi) if poi else 5.0
    if avg >= _SAT_HIGH:
        trend = "هابط — الطلب ينتقل للمناطق المجاورة"
        growth_pct = -5
    elif avg >= _SAT_MED:
        trend = "مستقر — نمو معتدل محافظ"
        growth_pct = 8
    else:
        trend = "صاعد — إمكانية نمو قوية"
        growth_pct = 18
    return {"trend": trend, "annual_growth_pct": growth_pct}


def _build_advisory(
    location: str,
    saturation: str,
    outlook: Dict,
    demand_flows: List[Dict],
    poi: Dict[str, float],
) -> str:
    schools_count   = int(poi.get("schools", 5) * 2.3)
    hospitals_count = int(poi.get("hospitals", 4) * 1.2)
    malls_count     = int(poi.get("malls", 5) * 0.8)

    lines = [
        f"══ رادار الهجرة العقارية — {location} ══",
        "",
        f"📊 وضع المنطقة: {saturation}",
        f"📈 اتجاه الطلب: {outlook['trend']}",
        f"   نمو سنوي متوقع: {outlook['annual_growth_pct']:+}%",
        "",
        f"🏫 مؤشرات البنية التحتية:",
        f"   • المدارس والتعليم:   {schools_count} منشأة تقريباً",
        f"   • المرافق الصحية:     {hospitals_count} منشأة تقريباً",
        f"   • مراكز التسوق:       {malls_count} منشأة تقريباً",
        "",
    ]

    if demand_flows:
        lines.append("🔄 اتجاهات انتقال الطلب:")
        for flow in demand_flows[:3]:
            lines.append(f"   → {flow['to']}  |  نسبة الانتقال: {flow['pct']}%")
        lines.append("")

    # توصية استباقية
    avg = sum(poi.values()) / len(poi)
    if avg >= _SAT_HIGH:
        lines += [
            "💡 التوصية الاستثمارية الاستباقية:",
            f"   الحي يتشبع حالياً (مؤشر {avg:.1f}/10) — الطلب يُهاجر شمالاً وشرقاً.",
            "   ► الإجراء المُقترح: تأخير الشراء الاستثماري الجديد أو التحول لعقارات مُدرّة دخل.",
            "   ► فرصة البديل: انظر مناطق النمو الصاعدة في القسم التالي.",
        ]
    elif avg >= _SAT_MED:
        lines += [
            "💡 التوصية الاستثمارية:",
            "   المنطقة في مرحلة النضج — عوائد مستقرة ومخاطر منخفضة.",
            "   ► مناسبة للمحافظ الدفاعية وعقارات الدخل الثابت.",
        ]
    else:
        lines += [
            "💡 التوصية الاستثمارية:",
            "   منطقة في طور النمو المبكر — فرصة رأسمالية عالية مع مخاطر متوسطة.",
            "   ► مناسبة للمستثمرين ذوي الأفق الزمني 3–6 سنوات.",
        ]

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# الدالة الرئيسية
# ═══════════════════════════════════════════════════════════════════════════

def analyze_demographic_flow(
    location: str,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    investment_horizon_yr: int = 5,
) -> Dict[str, Any]:
    """
    يُحلّل الزحف العمراني والهجرة الديموغرافية.

    المُخرجات:
      poi_density      : dict  كثافة نقاط الاهتمام
      saturation       : str   حالة التشبع
      demand_outlook   : dict  اتجاه الطلب + نمو سنوي
      demand_flows     : list  وجهات انتقال الطلب
      rising_stars     : list  المناطق الصاعدة المُقترحة
      advisory_text    : str   التوصية الاستباقية
      mock             : True
    """
    poi    = _lookup_poi(location)
    sat    = _saturation_level(poi)
    outlook = _demand_outlook(location, poi)

    # جلب بيانات انتقال الطلب
    flows: List[Dict] = []
    for key, val in _DEMAND_FLOW.items():
        if key != "_default" and key in location:
            flows = val
            break
    if not flows:
        flows = _DEMAND_FLOW["_default"]

    # فلترة النجوم الصاعدة حسب الأفق الاستثماري
    stars = [s for s in _RISING_STARS if s["horizon_yr"] <= investment_horizon_yr]

    advisory = _build_advisory(location, sat, outlook, flows, poi)

    return {
        "location":         location,
        "lat":              lat,
        "lng":              lng,
        "poi_density":      poi,
        "saturation":       sat,
        "demand_outlook":   outlook,
        "demand_flows":     flows,
        "rising_stars":     stars,
        "advisory_text":    advisory,
        "investment_horizon_yr": investment_horizon_yr,
        "mock":             True,
        "note":             "بيانات نموذجية — يمكن ربطها بـ OSM Overpass API أو Google Places للبيانات الحية",
    }
