# -*- coding: utf-8 -*-
"""
geo_risk_engine.py — التحليل الجيوتقني والقانوني
Expert_Smart Sovereign Edition

طبقات المخاطر (Proof of Concept — Mock Data):
  1. خرائط التربة (Soil Type)         — انتفاخية / رملية / صخرية / طينية
  2. مخرات السيول (Flood Path)        — مرتفع / متوسط / منخفض / آمن
  3. المناطق الزلزالية (Seismic Zone) — عالي / متوسط / منخفض
  4. الوضع القانوني (Legal Status)     — رهن / حجز / نزاع / سليم

عند الاتصال بـ OpenStreetMap (Nominatim) يُستخرج خط الطول والعرض للبحث في الطبقات.
"""

from __future__ import annotations
import hashlib
import math
from typing import Dict, Any, List, Optional

# ═══════════════════════════════════════════════════════════════════════════
# Mock Layers — بيانات نموذجية (PoC) قابلة للاستبدال بـ GeoJSON حقيقي
# ═══════════════════════════════════════════════════════════════════════════

_SOIL_PROFILES: Dict[str, Dict[str, Any]] = {
    # القاهرة الجديدة / التجمع
    "التجمع":         {"type": "رملية متوسطة التحمل", "risk": "منخفض",   "bearing": "12–16 طن/م²", "note": ""},
    "القاهرة الجديدة":{"type": "رملية متوسطة التحمل", "risk": "منخفض",   "bearing": "12–16 طن/م²", "note": ""},
    "العاصمة الإدارية":{"type": "رملية جيرية صلبة",   "risk": "منخفض",   "bearing": "18–22 طن/م²", "note": ""},
    # مناطق النيل والدلتا
    "المعادي":        {"type": "طينية انتفاخية",       "risk": "متوسط",   "bearing": "6–10 طن/م²",  "note": "قد تتشقق الأساسات عند تشبع التربة"},
    "الزمالك":        {"type": "طينية انتفاخية",       "risk": "متوسط",   "bearing": "7–11 طن/م²",  "note": "جزيرة نيلية — تربة طمية رخوة في الطبقات العليا"},
    "الدقي":          {"type": "طينية انتفاخية",       "risk": "متوسط",   "bearing": "7–12 طن/م²",  "note": ""},
    "المهندسين":      {"type": "طينية انتفاخية",       "risk": "متوسط",   "bearing": "7–12 طن/م²",  "note": ""},
    # الصحراء
    "أكتوبر":         {"type": "رملية جافة",            "risk": "منخفض",   "bearing": "10–14 طن/م²", "note": ""},
    "6 أكتوبر":       {"type": "رملية جافة",            "risk": "منخفض",   "bearing": "10–14 طن/م²", "note": ""},
    "الشيخ زايد":     {"type": "رملية جافة متماسكة",    "risk": "منخفض",   "bearing": "12–16 طن/م²", "note": ""},
    # جنوب مصر والصعيد
    "الأقصر":         {"type": "صخرية جيرية صلبة",      "risk": "منخفض",   "bearing": "> 25 طن/م²",  "note": ""},
    "أسوان":          {"type": "صخرية جرانيتية",         "risk": "منخفض",   "bearing": "> 30 طن/م²",  "note": ""},
    # مناطق الخطر
    "العبور":         {"type": "طينية رملية متشبعة",    "risk": "متوسط-مرتفع", "bearing": "5–8 طن/م²", "note": "منطقة قريبة من مجرى قناة الإسماعيلية"},
    "السلام":         {"type": "ردم صناعي + طين",       "risk": "مرتفع",   "bearing": "4–7 طن/م²",   "note": "⚠️ مناطق ردم تاريخية — يُستوجب تحليل تربة مستقل"},
    "_default":       {"type": "مختلطة (غير محددة)",    "risk": "متوسط",   "bearing": "8–14 طن/م²",  "note": ""},
}

_FLOOD_ZONES: Dict[str, Dict[str, Any]] = {
    # مناطق الخطر الكبير
    "العبور":          {"risk": "مرتفع",  "path": "مخرة سيول رئيسية",  "return_period": "25 سنة"},
    "السلام":          {"risk": "مرتفع",  "path": "منطقة تجمع مياه",   "return_period": "10 سنة"},
    "طريق السويس":     {"risk": "مرتفع",  "path": "وادي جاف دوري",      "return_period": "15 سنة"},
    "حلوان":           {"risk": "متوسط",  "path": "صرف عمراني",         "return_period": "50 سنة"},
    # مناطق آمنة نسبياً
    "التجمع":          {"risk": "منخفض",  "path": "لا يوجد",            "return_period": "—"},
    "التجمع الخامس":   {"risk": "منخفض",  "path": "لا يوجد",            "return_period": "—"},
    "العاصمة الإدارية":{"risk": "منخفض",  "path": "لا يوجد — نظام صرف متكامل", "return_period": "—"},
    "الزمالك":         {"risk": "منخفض",  "path": "لا يوجد مباشر",     "return_period": "—"},
    "الشيخ زايد":      {"risk": "منخفض",  "path": "لا يوجد",            "return_period": "—"},
    # مناطق الساحل الشمالي
    "مرسى مطروح":      {"risk": "مرتفع",  "path": "شرافات وادي القصب",  "return_period": "5 سنوات"},
    "العلمين":         {"risk": "متوسط",  "path": "انجراف ساحلي",        "return_period": "20 سنة"},
    "_default":        {"risk": "منخفض",  "path": "غير مصنف",           "return_period": "—"},
}

_SEISMIC_ZONES: Dict[str, Dict[str, Any]] = {
    "السويس":          {"zone": "Z3 — مرتفع", "peak_g": "0.15g", "note": "قريب من منطقة التصدعات"},
    "شرم الشيخ":       {"zone": "Z3 — مرتفع", "peak_g": "0.15g", "note": "نشاط زلزالي دوري في البحر الأحمر"},
    "أسوان":           {"zone": "Z2 — متوسط", "peak_g": "0.10g", "note": "نشاط زلزالي تاريخي"},
    "الغردقة":         {"zone": "Z2 — متوسط", "peak_g": "0.10g", "note": ""},
    "_default":        {"zone": "Z1 — منخفض", "peak_g": "0.05g", "note": ""},
}

# معاملات المخاطر لرفع نسبة المخاطرة الإجمالية
_RISK_MULTIPLIERS = {
    "مرتفع":            0.15,    # +15% على معامل المخاطرة
    "متوسط-مرتفع":     0.10,
    "متوسط":            0.05,
    "منخفض":            0.0,
    "منخفض-متوسط":      0.02,
}


def _lookup(database: Dict, location: str) -> Dict:
    """بحث بالتطابق الجزئي في قاموس البيانات."""
    for key, val in database.items():
        if key != "_default" and key in location:
            return val
    return database.get("_default", {})


def _risk_score(soil_risk: str, flood_risk: str, seismic_zone: str) -> float:
    """يحسب معامل المخاطرة المُجمَّع [0.0 – 1.0]."""
    base = (
        _RISK_MULTIPLIERS.get(soil_risk, 0.05) +
        _RISK_MULTIPLIERS.get(flood_risk, 0.0) +
        _RISK_MULTIPLIERS.get(seismic_zone.split("—")[0].strip() if "—" in seismic_zone else seismic_zone, 0.0)
    )
    return min(round(base, 3), 1.0)


def _format_report_alert(soil: dict, flood: dict, seismic: dict, risk_factor: float, location: str) -> str:
    """يُولّد نص التحذير للتقرير."""
    lines = [
        f"══ تقرير المخاطر الجيوتقنية والبيئية — {location} ══",
        "",
        f"🌍 التربة: {soil.get('type','غير محدد')}",
        f"   قدرة التحمل: {soil.get('bearing','—')}  |  مستوى الخطر: {soil.get('risk','—')}",
    ]
    if soil.get("note"):
        lines.append(f"   ⚠️ {soil['note']}")

    lines += [
        "",
        f"🌊 مخاطر الفيضان والسيول: {flood.get('risk','—')}",
        f"   المسار: {flood.get('path','—')}  |  دورة التكرار: {flood.get('return_period','—')}",
        "",
        f"🏔️ المنطقة الزلزالية: {seismic.get('zone','—')}  |  ذروة التسارع: {seismic.get('peak_g','—')}",
    ]
    if seismic.get("note"):
        lines.append(f"   {seismic['note']}")

    lines += [
        "",
        f"📊 معامل المخاطرة الإجمالي: {risk_factor * 100:.1f}%",
    ]

    if risk_factor >= 0.20:
        lines.append("🔴 الحكم: مخاطر جيوتقنية مرتفعة — يُلزم الحصول على تقرير تربة معتمد قبل أي تمويل بنكي.")
    elif risk_factor >= 0.10:
        lines.append("🟡 الحكم: مخاطر معتدلة — يُنصح بمراجعة تقارير التربة وتفعيل بند الشروط الجيوتقنية في العقد.")
    else:
        lines.append("🟢 الحكم: مخاطر جيوتقنية منخفضة — العقار مناسب للتطوير دون قيود خاصة.")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# الدالة الرئيسية
# ═══════════════════════════════════════════════════════════════════════════

def analyze_geo_risk(
    location: str,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    property_type: str = "",
) -> Dict[str, Any]:
    """
    يُحلّل المخاطر الجيوتقنية والبيئية والقانونية للموقع.

    المُخرجات:
      soil         : dict  — نوع التربة وقدرة التحمل والمخاطر
      flood        : dict  — منطقة السيول ومسار المخرة
      seismic      : dict  — المنطقة الزلزالية
      risk_factor  : float — معامل المخاطرة [0.0 – 1.0]
      risk_pct     : str   "12.0%"
      alert_level  : str   "منخفض" | "متوسط" | "مرتفع"
      report_text  : str   — نص التحذير للتقرير
      mock         : True  — بيانات نموذجية (PoC)
    """
    soil    = _lookup(_SOIL_PROFILES, location)
    flood   = _lookup(_FLOOD_ZONES, location)
    seismic = _lookup(_SEISMIC_ZONES, location)

    seismic_risk_key = seismic.get("zone", "Z1 — منخفض").split("—")[0].strip()
    risk_factor = _risk_score(
        soil.get("risk", "منخفض"),
        flood.get("risk", "منخفض"),
        seismic_risk_key,
    )

    if risk_factor >= 0.20:
        alert_level = "مرتفع"
    elif risk_factor >= 0.10:
        alert_level = "متوسط"
    else:
        alert_level = "منخفض"

    report_text = _format_report_alert(soil, flood, seismic, risk_factor, location)

    return {
        "location":     location,
        "lat":          lat,
        "lng":          lng,
        "soil":         soil,
        "flood":        flood,
        "seismic":      seismic,
        "risk_factor":  risk_factor,
        "risk_pct":     f"{risk_factor * 100:.1f}%",
        "alert_level":  alert_level,
        "report_text":  report_text,
        "mock":         True,
        "note":         "بيانات نموذجية — يُنصح باستبدالها بطبقات GeoJSON رسمية عند الإتاحة",
    }
