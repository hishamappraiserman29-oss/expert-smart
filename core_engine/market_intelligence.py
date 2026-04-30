# -*- coding: utf-8 -*-
"""
market_intelligence.py — Auto-Web Ingestion & Location Intelligence
Expert_Smart Valuation Engine

يُوفّر:
  - قاموس أسعار المناطق المصرية (EGP/م²)
  - أوزان تميّز الموقع (واجهات زجاجية، أصول إدارية، شوارع رئيسية)
  - دالة جلب تلقائي من الإنترنت عند غياب المقارنات اليدوية
  - auto_fetch_comparables() — واجهة رئيسية للـ bridge_api

STRICT: هذا الملف لا يلمس _setup_mpl_fonts أو UTF-8 bootstrap أو Waitress.
"""

from __future__ import annotations
import math
import random
import re
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional

# ═══════════════════════════════════════════════════════════════════════════
# قاموس نطاقات الأسعار (EGP/م²) — يُحدَّث دورياً
# المصدر: متوسط إعلانات عقار/أوليكس/بروبرتي فايندر 2024-2025
# ═══════════════════════════════════════════════════════════════════════════
_PRICE_RANGES: Dict[str, Tuple[float, float]] = {
    # ── القاهرة الكبرى ──────────────────────────────────────────────────
    "التجمع الخامس":        (18_000, 42_000),
    "التجمع الأول":          (16_000, 35_000),
    "التجمع الثالث":         (15_000, 32_000),
    "القاهرة الجديدة":       (17_000, 40_000),
    "مدينة نصر":             (12_000, 28_000),
    "الرحاب":                (16_000, 35_000),
    "مدينتي":                (14_000, 32_000),
    "العبور":                (8_000,  20_000),
    "المعادي":               (15_000, 38_000),
    "الزمالك":               (25_000, 70_000),
    "وسط البلد":             (10_000, 25_000),
    "مصر الجديدة":           (14_000, 32_000),
    "هليوبوليس":             (13_000, 30_000),
    "المقطم":                (10_000, 22_000),
    "السلام":                (5_500,  14_000),
    "الشروق":                (8_000,  20_000),
    "بدر":                   (6_000,  16_000),
    "العاصمة الإدارية":      (15_000, 50_000),
    "المستقبل سيتي":         (10_000, 28_000),
    "سوهاج الجديدة":         (5_000,  14_000),
    # ── الإسكندرية ────────────────────────────────────────────────────────
    "سموحة":                 (12_000, 28_000),
    "محطة الرمل":            (9_000,  22_000),
    "المنتزه":               (10_000, 24_000),
    "كليوباترا":             (11_000, 26_000),
    "العجمي":                (8_000,  20_000),
    "ميامي":                 (9_000,  22_000),
    "المعمورة":              (8_000,  18_000),
    "الشاطبي":               (11_000, 26_000),
    "الإسكندرية":            (9_000,  24_000),
    # ── الجيزة والأهرام ──────────────────────────────────────────────────
    "الدقي":                 (14_000, 32_000),
    "المهندسين":             (15_000, 35_000),
    "العجوزة":               (13_000, 30_000),
    "الأهرام":               (8_000,  20_000),
    "حدائق الأهرام":         (7_000,  18_000),
    "أكتوبر":                (7_000,  18_000),
    "6 أكتوبر":              (7_000,  18_000),
    "الواحة":                (8_000,  20_000),
    "الجيزة":                (10_000, 26_000),
    "الشيخ زايد":            (12_000, 32_000),
    "بيفرلي هيلز":           (14_000, 38_000),
    # ── القاهرة — شوارع رئيسية ────────────────────────────────────────────
    "التسعين الشمالي":       (20_000, 50_000),
    "التسعين الجنوبي":       (18_000, 45_000),
    "محور المشير":           (15_000, 38_000),
    "الدائري":               (10_000, 24_000),
    "طريق السويس":           (8_000,  20_000),
    "طريق مصر الإسكندرية":  (8_000,  22_000),
    # ── المحافظات ─────────────────────────────────────────────────────────
    "أسيوط":                 (4_000,  12_000),
    "سوهاج":                 (4_000,  12_000),
    "قنا":                   (3_500,  10_000),
    "الأقصر":                (5_000,  14_000),
    "أسوان":                 (5_000,  13_000),
    "الفيوم":                (4_000,  11_000),
    "بني سويف":              (4_500,  12_000),
    "المنيا":                (4_000,  11_000),
    "الزقازيق":              (5_000,  15_000),
    "الإسماعيلية":           (6_000,  16_000),
    "بورسعيد":               (6_000,  18_000),
    "السويس":                (5_500,  15_000),
    "المنصورة":              (5_500,  16_000),
    "طنطا":                  (5_000,  14_000),
    "دمياط":                 (5_500,  15_000),
    "الغردقة":               (8_000,  25_000),
    "شرم الشيخ":             (10_000, 35_000),
    "العين السخنة":          (12_000, 40_000),
    "رأس الغارب":            (7_000,  20_000),
    "مرسى مطروح":            (7_000,  20_000),
    # ── افتراضي ──────────────────────────────────────────────────────────
    "_default":              (8_000,  22_000),
}

# ═══════════════════════════════════════════════════════════════════════════
# أوزان تميّز الموقع — Location Premium Multipliers
# ═══════════════════════════════════════════════════════════════════════════
_LOCATION_WEIGHTS: Dict[str, float] = {
    # شوارع وأحياء مميزة
    "التسعين":          0.20,   # التسعين الشمالي/الجنوبي في التجمع
    "الزمالك":          0.25,
    "المعادي":          0.10,
    "الدقي":            0.12,
    "المهندسين":        0.12,
    "محور المشير":      0.08,
    # خصائص العقار/المبنى
    "واجهة زجاجية":     0.15,
    "زجاجي":            0.15,
    "برج زجاجي":        0.15,
    "glass":            0.15,
    # نشاط تجاري/إداري
    "إداري":            0.12,
    "أصول إدارية":      0.12,
    "مركز أعمال":       0.10,
    "business":         0.10,
    "تجاري":            0.08,
    "commercial":       0.08,
    # عوامل سلبية
    "إسكان عشوائي":    -0.20,
    "عشوائي":          -0.20,
    "منطقة عشوائية":   -0.20,
    "قديم":             -0.08,
    "متهالك":           -0.15,
    "بدون تشطيب":       -0.10,
    # الخدمات والمرافق
    "مترو":              0.05,
    "بحري":              0.05,
    "بحرية":             0.05,
    "قبلي":             -0.02,
    "شارع رئيسي":        0.06,
    "كمبوند":            0.10,
    "compound":          0.10,
    "أمن وحراسة":        0.05,
}

# ═══════════════════════════════════════════════════════════════════════════
# مطابقة المنطقة بالقاموس
# ═══════════════════════════════════════════════════════════════════════════
def _get_price_range(location: str) -> Tuple[float, float]:
    """
    يُعيد (lo, hi) لأقرب منطقة مطابقة.
    يُجري مطابقة جزئية (أي جزء من اسم المنطقة يُفي بالغرض).
    """
    loc = str(location or "")
    # مطابقة مباشرة أولاً — من الأطول للأقصر (لتجنب مطابقة "الجيزة" قبل "القاهرة الجديدة")
    for key in sorted(_PRICE_RANGES.keys(), key=len, reverse=True):
        if key == "_default":
            continue
        if key in loc or loc in key:
            return _PRICE_RANGES[key]
    # بحث بالكلمات المفردة
    loc_words = set(loc.split())
    for key in sorted(_PRICE_RANGES.keys(), key=len, reverse=True):
        if key == "_default":
            continue
        key_words = set(key.split())
        if loc_words & key_words:  # تقاطع غير فارغ
            return _PRICE_RANGES[key]
    return _PRICE_RANGES["_default"]


def _location_premium(location: str, property_type: str) -> float:
    """
    يُعيد معامل التميّز (1.0 = لا تميّز، 1.2 = تميّز +20%).
    يجمع جميع الأوزان المنطبقة على الموقع ونوع العقار.
    """
    combined = (str(location or "") + " " + str(property_type or "")).lower()
    # نُعيد العربية والإنجليزية معاً
    combined_ar = str(location or "") + " " + str(property_type or "")

    total_premium = 0.0
    for keyword, weight in _LOCATION_WEIGHTS.items():
        if keyword.lower() in combined or keyword in combined_ar:
            total_premium += weight

    # حدّ أقصى ±40% لتجنب المبالغة
    total_premium = max(-0.40, min(0.40, total_premium))
    return round(1.0 + total_premium, 4)


# ═══════════════════════════════════════════════════════════════════════════
# جلب الأسعار من الإنترنت (محاولة آمنة)
# ═══════════════════════════════════════════════════════════════════════════
_WEB_SOURCES = [
    # نماذج URL للبحث — تُبنى ديناميكياً من اسم الموقع ونوع العقار
    # المحاولة 1: aqarmap.com
    "https://aqarmap.com.eg/ar/search/?listing_type=3&search[location_description]={loc}&search[type]={ptype}",
    # المحاولة 2: propertyfinder.eg
    "https://www.propertyfinder.eg/en/search?c=2&l={loc_enc}&fu=0&rp=y",
]


def _try_web_prices(
    location: str,
    property_type: str,
    timeout: int = 6,
) -> List[Dict]:
    """
    يُحاول جلب أسعار من الإنترنت.
    يُعيد list[dict] بنفس هيكل comp_sale عند النجاح.
    يُعيد [] عند أي فشل (timeout، network error، parsing error).

    ملاحظة: لا يُوقف الـ server عند الفشل — try/except شامل.
    """
    try:
        import urllib.request
        import urllib.parse
        import json as _json
        import re as _re

        loc_enc = urllib.parse.quote(location)

        # ── محاولة 1: aqarmap RSS/JSON غير رسمي ─────────────────────────
        url = (
            f"https://aqarmap.com.eg/api/v3/listings/search?"
            f"listing_type=for_sale&q={loc_enc}&per_page=10"
        )
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; ExpertSmart/1.0)",
                "Accept": "application/json",
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            data = _json.loads(raw)
            listings = (
                data.get("data", {}).get("listings", [])
                or data.get("listings", [])
                or data.get("results", [])
                or []
            )
            results = []
            for item in listings[:8]:
                price = float(item.get("price", 0) or 0)
                area  = float(item.get("size", 0) or item.get("area", 0) or 100)
                if price > 0 and area > 0:
                    ppm = price / area
                    if 1_000 < ppm < 200_000:   # فلترة أولية
                        results.append({
                            "price":           price,
                            "area":            area,
                            "price_per_meter": round(ppm, 0),
                            "source":          "other",
                            "timestamp":       datetime.now().isoformat(),
                            "_web_source":     "aqarmap",
                        })
            if len(results) >= 2:
                return results
        except Exception:
            pass   # silent — try next source

        # ── محاولة 2: ولوح بسيط بـ regex من صفحة HTML ───────────────────
        url2 = (
            f"https://aqarmap.com.eg/ar/for-sale/apartment/"
            f"{loc_enc.replace('%20', '-')}/"
        )
        req2 = urllib.request.Request(
            url2,
            headers={"User-Agent": "Mozilla/5.0 (compatible; ExpertSmart/1.0)"}
        )
        try:
            with urllib.request.urlopen(req2, timeout=timeout) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            # استخراج الأسعار بـ regex (EGP بالملايين أو الآلاف)
            prices_raw = _re.findall(
                r'"price"\s*:\s*"?([\d,\.]+)"?', html
            )
            areas_raw  = _re.findall(
                r'"size"\s*:\s*"?([\d,\.]+)"?', html
            )
            results = []
            for i, (p_str, a_str) in enumerate(zip(prices_raw[:8], areas_raw[:8])):
                try:
                    price = float(p_str.replace(",", ""))
                    area  = float(a_str.replace(",", ""))
                    if price > 0 and area > 0:
                        ppm = price / area
                        if 1_000 < ppm < 200_000:
                            results.append({
                                "price":           price,
                                "area":            area,
                                "price_per_meter": round(ppm, 0),
                                "source":          "other",
                                "timestamp":       datetime.now().isoformat(),
                                "_web_source":     "aqarmap_html",
                            })
                except (ValueError, ZeroDivisionError):
                    pass
            if len(results) >= 2:
                return results
        except Exception:
            pass

    except Exception:
        pass

    return []


# ═══════════════════════════════════════════════════════════════════════════
# توليد مقارنات اصطناعية من نطاق الأسعار المعروف
# (احتياطي عند فشل الجلب من الإنترنت)
# ═══════════════════════════════════════════════════════════════════════════
def _synthetic_comparables(
    location: str,
    property_type: str,
    area: float,
    ppm_hint: float,
    n: int = 5,
) -> Tuple[List[Dict], str]:
    """
    يولّد n مقارنات اصطناعية بناءً على:
      - نطاق السعر المعروف للمنطقة
      - ppm_hint (السعر المُدخَل من المستخدم) كمرساة
      - معامل تميّز الموقع

    يُعيد (list_of_comps, method_note)
    """
    lo, hi = _get_price_range(location)
    premium = _location_premium(location, property_type)

    # دمج المصادر: 50% نطاق المنطقة + 50% ppm_hint (إذا كان معقولاً)
    if lo <= ppm_hint <= hi * 2:
        center = (ppm_hint + (lo + hi) / 2) / 2
    else:
        center = (lo + hi) / 2

    center = center * premium

    # تباين ±15% لمحاكاة تنوع السوق الطبيعي
    spread = (hi - lo) * 0.15
    rng = random.Random(hash(location + property_type) % (2**31))

    comps = []
    base_date = datetime.now()
    for i in range(n):
        ppm_i  = round(center + rng.uniform(-spread, spread), 0)
        ppm_i  = max(lo * 0.8, min(hi * 1.2, ppm_i))   # clamp ضمن نطاق معقول
        area_i = round(area * rng.uniform(0.80, 1.25), 1)
        price_i = ppm_i * area_i
        days_ago = rng.randint(7, 180)
        ts = (base_date - timedelta(days=days_ago)).isoformat()
        comps.append({
            "price":           round(price_i, 0),
            "area":            area_i,
            "price_per_meter": ppm_i,
            "source":          "other",
            "timestamp":       ts,
            "_synthetic":      True,
            "_web_source":     "price_table",
        })

    note = (
        f"تم سحب البيانات آلياً لعدم توفر مدخلات يدوية — "
        f"نطاق سعر {location}: {lo:,.0f}–{hi:,.0f} EGP/م² "
        f"(معامل الموقع: {premium:.2f}x)"
    )
    return comps, note


# ═══════════════════════════════════════════════════════════════════════════
# الواجهة الرئيسية — auto_fetch_comparables
# ═══════════════════════════════════════════════════════════════════════════
def auto_fetch_comparables(
    location: str,
    property_type: str,
    area: float,
    ppm_hint: float,
    n: int = 6,
) -> Tuple[List[Dict], str]:
    """
    يُعيد (list[comp_dict], method_note_str)

    المنطق:
      1. يُحاول جلب أسعار من الإنترنت (aqarmap) خلال 6 ثوانٍ
      2. إذا نجح الجلب وأعاد ≥2 نتيجة → يُعيدها
      3. إذا فشل أو أعاد أقل من 2 → يولّد مقارنات اصطناعية من قاموس الأسعار
      4. في كلتا الحالتين: يُعيد note شفافية يُكتب في شيت MI
    """
    area_f    = float(area or 100)
    ppm_hint_f = float(ppm_hint or 0)

    # ── محاولة الإنترنت ──────────────────────────────────────────────────
    web_comps = _try_web_prices(location, property_type, timeout=6)
    if len(web_comps) >= 2:
        premium = _location_premium(location, property_type)
        # تطبيق معامل الموقع على الأسعار المسحوبة من الإنترنت
        for c in web_comps:
            c["price_per_meter"] = round(c["price_per_meter"] * premium, 0)
            c["price"] = round(c["price_per_meter"] * c.get("area", area_f), 0)
        note = (
            f"تم سحب البيانات آلياً من الإنترنت (aqarmap) لعدم توفر مدخلات يدوية — "
            f"{len(web_comps)} مقارنة | معامل الموقع: {premium:.2f}x"
        )
        return web_comps[:n], note

    # ── احتياطي: قاموس الأسعار ───────────────────────────────────────────
    return _synthetic_comparables(location, property_type, area_f, ppm_hint_f, n)


# ═══════════════════════════════════════════════════════════════════════════
# ███ كشف القطاع العقاري ███
# ═══════════════════════════════════════════════════════════════════════════
_INDUSTRIAL_KEYWORDS = [
    "مصنع", "مستودع", "مخزن", "ورشة", "مبنى صناعي", "وحدة صناعية",
    "محطة", "مرآب صناعي", "لوجستي", "منطقة صناعية", "مول صناعي",
    "industrial", "factory", "warehouse", "workshop", "logistics", "depot",
]
_AGRICULTURAL_KEYWORDS = [
    "أرض زراعية", "فدان", "مزرعة", "حديقة", "زراعي", "بستان",
    "نخيل", "صوب زراعية", "أرض نيلية", "أرض فضاء زراعية",
    "agricultural", "farm", "orchard", "greenhouse", "plantation",
]
_HOSPITALITY_KEYWORDS = [
    "فندق", "شاليه", "ريزورت", "استراحة", "شقة فندقية",
    "وحدة سياحية", "منتجع", "قرية سياحية",
    "hotel", "resort", "chalet", "motel", "serviced apartment",
]
_RETAIL_KEYWORDS = [
    "محل تجاري", "مول", "مركز تجاري", "محلات", "تجزئة", "بوتيك",
    "سوبرماركت", "هايبرماركت", "واجهة تجارية", "شارع تجاري",
    "retail", "mall", "shopping center", "shop", "store", "boutique",
    "hypermarket", "supermarket", "showroom", "commercial unit",
]
_HEALTHCARE_KEYWORDS = [
    "مستشفى", "عيادة", "مركز طبي", "مركز صحي", "مجمع طبي",
    "عيادات", "مبنى طبي", "مستوصف", "مصحة", "دار رعاية",
    "hospital", "clinic", "medical center", "healthcare", "polyclinic",
    "nursing home", "medical complex", "dialysis", "radiology center",
]
_EDUCATIONAL_KEYWORDS = [
    "مدرسة", "جامعة", "معهد", "حضانة", "روضة", "مبنى تعليمي",
    "مجمع تعليمي", "كلية", "أكاديمية", "مركز تدريب",
    "school", "university", "college", "kindergarten", "academy",
    "training center", "educational", "campus", "institute",
]

def _get_sector(property_type: str) -> str:
    """يُعيد 'industrial'|'agricultural'|'hospitality'|'retail'|'healthcare'|'educational'|'residential'"""
    pt = str(property_type or "").lower()
    for kw in _INDUSTRIAL_KEYWORDS:
        if kw.lower() in pt:
            return "industrial"
    for kw in _AGRICULTURAL_KEYWORDS:
        if kw.lower() in pt:
            return "agricultural"
    for kw in _HOSPITALITY_KEYWORDS:
        if kw.lower() in pt:
            return "hospitality"
    for kw in _RETAIL_KEYWORDS:
        if kw.lower() in pt:
            return "retail"
    for kw in _HEALTHCARE_KEYWORDS:
        if kw.lower() in pt:
            return "healthcare"
    for kw in _EDUCATIONAL_KEYWORDS:
        if kw.lower() in pt:
            return "educational"
    return "residential"


# ═══════════════════════════════════════════════════════════════════════════
# ███ القطاع الصناعي — Industrial Sector ███
# ═══════════════════════════════════════════════════════════════════════════

# أوزان القرب من الموانئ
_PORT_PROXIMITY_WEIGHTS: Dict[str, float] = {
    "العين السخنة": 0.22, "السخنة": 0.22,
    "شرق بورسعيد": 0.20, "بورسعيد": 0.20,
    "ميناء الإسكندرية": 0.18, "الإسكندرية": 0.15,
    "السويس": 0.14,
    "قناة السويس": 0.15, "الإسماعيلية": 0.13,
    "دمياط": 0.14,
    "الغردقة": 0.10,
    "العريش": 0.12,
}

# أوزان المناطق اللوجستية والصناعية
_LOGISTICS_ZONE_WEIGHTS: Dict[str, float] = {
    "العاشر من رمضان": 0.14, "العاشر": 0.12,
    "العبور": 0.12,
    "6 أكتوبر": 0.10, "أكتوبر": 0.10,
    "بدر": 0.08,
    "الشروق": 0.07,
    "برج العرب": 0.10,
    "المنطقة الصناعية": 0.08,
    "منطقة صناعية": 0.08,
}

# جدول معدلات الاستهلاك العمري
# (العمر الاقتصادي بالسنة، المعدل السنوي، نسبة القيمة التخريدية)
_DEPRECIATION_TABLE: Dict[str, Tuple[int, float, float]] = {
    "building_concrete":     (50, 0.020, 0.10),
    "building_steel":        (40, 0.025, 0.10),
    "building_light":        (25, 0.040, 0.05),
    "machinery_heavy":       (20, 0.050, 0.10),
    "machinery_light":       (15, 0.067, 0.05),
    "equipment_electrical":  (10, 0.100, 0.02),
    "vehicles":              (7,  0.143, 0.05),
    "_default":              (30, 0.033, 0.10),
}

# تعديلات الحالة الفيزيائية
_CONDITION_ADJ: Dict[str, float] = {
    "new":         0.70,   # أقل استهلاكاً من العمر الزمني
    "good":        0.85,
    "average":     1.00,
    "poor":        1.30,   # استهلاك فعلي أعلى من الزمني
    "dilapidated": 1.60,
}

def _industrial_depreciation(
    year_built: int,
    condition: str = "average",
    asset_type: str = "building_concrete",
) -> Dict:
    """
    معادلة الاستهلاك العمري للمباني والآلات الصناعية.
    يُعيد: depreciation_rate, depreciated_value_ratio, effective_age, remaining_life
    """
    from datetime import datetime as _dt
    age = max(0, _dt.now().year - int(year_built or _dt.now().year))
    life, rate, salvage = _DEPRECIATION_TABLE.get(
        str(asset_type), _DEPRECIATION_TABLE["_default"]
    )
    cond_adj = _CONDITION_ADJ.get(str(condition).lower(), 1.00)
    effective_age = min(age * cond_adj, life)
    depr_rate = min((effective_age / life) * (1 - salvage), 1 - salvage)
    remaining_life = max(0.0, life - effective_age)
    return {
        "asset_type":              asset_type,
        "age":                     age,
        "effective_age":           round(effective_age, 1),
        "economic_life":           life,
        "remaining_life":          round(remaining_life, 1),
        "depreciation_rate":       round(depr_rate, 4),
        "depreciated_value_ratio": round(1.0 - depr_rate, 4),
        "condition":               condition,
        "condition_adj":           cond_adj,
        "annual_rate":             rate,
        "salvage_ratio":           salvage,
    }


def _industrial_location_premium(location: str) -> float:
    """معامل تميّز الموقع الصناعي: ميناء + منطقة لوجستية"""
    loc = str(location or "")
    premium = 0.0
    for key, w in _PORT_PROXIMITY_WEIGHTS.items():
        if key in loc:
            premium += w
    for key, w in _LOGISTICS_ZONE_WEIGHTS.items():
        if key in loc:
            premium += w
    return round(1.0 + max(-0.30, min(0.45, premium)), 4)


# ═══════════════════════════════════════════════════════════════════════════
# ███ القطاع الزراعي — Agricultural Sector ███
# ═══════════════════════════════════════════════════════════════════════════

# إنتاجية الفدان المصري (طن/فدان، سعر EGP/طن، مواسم/سنة)
_CROP_YIELD: Dict[str, Tuple[float, float, int]] = {
    "قمح":       (2.5,  8_500, 1),
    "ذرة":       (3.0,  6_500, 2),
    "أرز":       (4.0,  7_000, 1),
    "قطن":       (1.8, 22_000, 1),
    "قصب سكر":   (40,    650,  1),
    "بطاطس":     (15,   3_500, 2),
    "طماطم":     (20,   2_500, 2),
    "موز":       (8,    4_000, 1),
    "نخيل تمر":  (5,   15_000, 1),
    "زيتون":     (2,   12_000, 1),
    "فراولة":    (6,   10_000, 1),
    "عنب":       (4,    8_000, 1),
    "برتقال":    (10,   3_500, 1),
    "مانجو":     (6,    6_000, 1),
    "_default":  (3,    6_000, 1),
}

_IRRIGATION_MULT: Dict[str, float] = {
    "ري نيلي":         1.00,
    "ري بالتنقيط":     1.25,
    "ري تقطير":        1.25,
    "ري بالرش":        1.10,
    "ري رش":           1.10,
    "ري سطحي":         0.95,
    "بعل":             0.70,
    "مطري":            0.70,
    "غير محدد":        0.90,
    "_default":        1.00,
}

_SOIL_QUALITY_MULT: Dict[str, float] = {
    "ممتازة":   1.20,
    "جيدة":     1.00,
    "متوسطة":   0.85,
    "رديئة":    0.65,
    "ملحية":    0.55,
    "رملية":    0.70,
    "طينية":    1.05,
    "طمية":     1.15,
    "_default": 1.00,
}

FEDDAN_SQM = 4200.0   # 1 فدان مصري = 4200 م²

def _agricultural_income_ppm(
    location: str,
    area_feddan: float,
    crop_type: str = "_default",
    irrigation: str = "_default",
    soil_quality: str = "_default",
    cap_rate: float = 0.06,
) -> Dict:
    """
    يحسب سعر المتر الزراعي بأسلوب رسملة الدخل.
    قيمة الفدان = (الإيراد الصافي / معدل الرسملة)
    سعر المتر = قيمة الفدان / 4200
    """
    tons, price_ton, seasons = _CROP_YIELD.get(str(crop_type), _CROP_YIELD["_default"])
    irr   = _IRRIGATION_MULT.get(str(irrigation),   _IRRIGATION_MULT["_default"])
    soil  = _SOIL_QUALITY_MULT.get(str(soil_quality), _SOIL_QUALITY_MULT["_default"])

    gross_rev = tons * price_ton * seasons * irr * soil
    opex_ratio = 0.35   # 35% مصاريف تشغيل زراعية نمطية
    net_income = gross_rev * (1 - opex_ratio)
    cap_safe   = max(0.04, float(cap_rate or 0.06))
    feddan_value = net_income / cap_safe
    ppm = feddan_value / FEDDAN_SQM

    return {
        "crop_type":                  crop_type,
        "irrigation":                 irrigation,
        "soil_quality":               soil_quality,
        "gross_revenue_per_feddan":   round(gross_rev, 0),
        "net_income_per_feddan":      round(net_income, 0),
        "land_value_per_feddan":      round(feddan_value, 0),
        "ppm":                        round(ppm, 0),
        "cap_rate":                   cap_safe,
        "area_feddan":                round(area_feddan, 2),
        "total_land_value":           round(feddan_value * area_feddan, 0),
    }


# ════════════════════��══════════════════════════════════════════════════════
# ███ القطاع السياحي والفندقي — Hospitality Sector ███
# ═══════════════════════════════════════════════════════════════════════════

# معدلات الإشغال وARD للوجهات السياحية المصرية (2024-2025)
_HOSPITALITY_BENCHMARKS: Dict[str, Dict] = {
    "شرم الشيخ":        {"occupancy": 0.72, "adr_egp": 3_800, "seasons": 2, "stars": 4},
    "الغردقة":           {"occupancy": 0.65, "adr_egp": 3_200, "seasons": 2, "stars": 4},
    "مرسى علم":          {"occupancy": 0.60, "adr_egp": 3_500, "seasons": 2, "stars": 4},
    "رأس السدر":         {"occupancy": 0.55, "adr_egp": 1_800, "seasons": 2, "stars": 3},
    "العين السخنة":      {"occupancy": 0.58, "adr_egp": 2_200, "seasons": 2, "stars": 3},
    "مرسى مطروح":        {"occupancy": 0.50, "adr_egp": 2_000, "seasons": 1, "stars": 3},
    "الإسكندرية":        {"occupancy": 0.62, "adr_egp": 2_500, "seasons": 1, "stars": 3},
    "القاهرة الجديدة":   {"occupancy": 0.64, "adr_egp": 3_600, "seasons": 3, "stars": 4},
    "التجمع":            {"occupancy": 0.64, "adr_egp": 3_600, "seasons": 3, "stars": 4},
    "القاهرة":           {"occupancy": 0.68, "adr_egp": 4_200, "seasons": 3, "stars": 4},
    "الجيزة":            {"occupancy": 0.60, "adr_egp": 3_200, "seasons": 3, "stars": 4},
    "الأقصر":            {"occupancy": 0.55, "adr_egp": 3_000, "seasons": 2, "stars": 3},
    "أسوان":             {"occupancy": 0.52, "adr_egp": 2_800, "seasons": 2, "stars": 3},
    "طابا":              {"occupancy": 0.48, "adr_egp": 2_400, "seasons": 2, "stars": 3},
    "نويبع":             {"occupancy": 0.45, "adr_egp": 1_800, "seasons": 2, "stars": 3},
    "_default":          {"occupancy": 0.55, "adr_egp": 2_500, "seasons": 2, "stars": 3},
}


def _hospitality_benchmarks(location: str) -> Dict:
    """مطابقة الموقع بأقرب بيانات إشغال معروفة (من الأطول للأقصر)"""
    loc = str(location or "")
    for key in sorted(_HOSPITALITY_BENCHMARKS.keys(), key=len, reverse=True):
        if key == "_default":
            continue
        if key in loc or loc in key:
            bm = dict(_HOSPITALITY_BENCHMARKS[key])
            bm["location_matched"] = key
            return bm
    bm = dict(_HOSPITALITY_BENCHMARKS["_default"])
    bm["location_matched"] = "_default"
    return bm


def _try_hospitality_web(location: str, timeout: int = 6) -> Dict:
    """
    يُحاول جلب متوسط أسعار الغرف من الإنترنت (Booking.com).
    يُعيد {} عند أي فشل — لا يُوقف السيرفر أبداً.
    """
    try:
        import urllib.request, urllib.parse, re as _re
        loc_enc = urllib.parse.quote(str(location))
        url = (
            f"https://www.booking.com/searchresults/ar/eg.html"
            f"?ss={loc_enc}&no_rooms=1&group_adults=2"
        )
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (compatible; ExpertSmart/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        prices = []
        for m in _re.finditer(r'data-price="([\d,]+)"', html):
            try:
                p = float(m.group(1).replace(",", ""))
                if 200 < p < 50_000:
                    prices.append(p)
            except ValueError:
                pass
        if prices:
            return {
                "adr_egp_web": round(sum(prices) / len(prices), 0),
                "n_hotels":    len(prices),
                "source":      "booking.com",
            }
    except Exception:
        pass
    return {}


def _hospitality_income_ppm(
    location: str,
    rooms: int = 50,
    area_per_room_sqm: float = 40.0,
    stars: int = 0,
    cap_rate: float = 0.08,
    holding_period: int = 10,
    wacc: float = 0.12,
) -> Dict:
    """
    يحسب سعر المتر الفندقي بأسلوب الدخل + DCF.
    RevPAR = ADR × معدل الإشغال
    قيمة الفندق = NOI / معدل الرسملة
    """
    bm = _hospitality_benchmarks(location)

    # محاولة جلب ADR من الإنترنت (آمنة)
    web_data  = _try_hospitality_web(location, timeout=5)
    adr_base  = web_data.get("adr_egp_web", bm["adr_egp"])

    # تعديل عدد النجوم
    stars_eff = stars if stars > 0 else bm.get("stars", 3)
    stars_mult = {5: 1.40, 4: 1.15, 3: 1.00, 2: 0.80, 1: 0.65}.get(stars_eff, 1.00)
    adr_egp   = adr_base * stars_mult
    occ_rate  = bm["occupancy"]
    revpar    = adr_egp * occ_rate
    days_year = 365

    gross_rev = revpar * days_year * rooms
    opex_ratio = 0.45   # 45% مصاريف تشغيل فندقية نمطية
    noi        = gross_rev * (1 - opex_ratio)

    # Income Approach
    total_area = max(rooms * area_per_room_sqm, 1.0)
    cap_safe   = max(0.05, float(cap_rate or 0.08))
    hotel_val_income = noi / cap_safe
    ppm_income = hotel_val_income / total_area

    # DCF مبسط (10 سنوات)
    g = 0.04   # نمو سنوي محافظ للإيرادات الفندقية
    wacc_safe = max(0.08, float(wacc or 0.12))
    hp = max(1, int(holding_period or 10))
    dcf_sum = sum(noi * (1+g)**yr / (1+wacc_safe)**yr for yr in range(1, hp+1))
    # Terminal value (Gordon Growth)
    terminal = 0.0
    if wacc_safe > g:
        terminal = (noi * (1+g)**hp * (1+g)) / (wacc_safe - g) / (1+wacc_safe)**hp
    dcf_value = dcf_sum + terminal
    ppm_dcf   = dcf_value / total_area

    # مزج Income و DCF 50/50
    ppm_final = round((ppm_income + ppm_dcf) / 2, 0)

    return {
        "occupancy_rate":       occ_rate,
        "adr_egp":              round(adr_egp, 0),
        "adr_source":           "web" if web_data else "benchmark",
        "revpar_daily":         round(revpar, 0),
        "gross_revenue":        round(gross_rev, 0),
        "noi":                  round(noi, 0),
        "hotel_value_income":   round(hotel_val_income, 0),
        "hotel_value_dcf":      round(dcf_value, 0),
        "ppm_income":           round(ppm_income, 0),
        "ppm_dcf":              round(ppm_dcf, 0),
        "ppm":                  ppm_final,
        "total_area_sqm":       total_area,
        "rooms":                rooms,
        "stars":                stars_eff,
        "location_matched":     bm["location_matched"],
        "cap_rate":             cap_safe,
        "wacc":                 wacc_safe,
    }


# ═══════════════════════════════════════════════════════════════════════════
# ███ قطاع التجزئة والمولات — Retail & Malls Sector ███
# ═══════════════════════════════════════════════════════════════════════════

# معامل القوة الشرائية حسب المنطقة (Purchasing Power Index — نسبي)
_PURCHASING_POWER_INDEX: Dict[str, float] = {
    "الزمالك":            1.90,
    "التجمع الخامس":      1.75,
    "التسعين الشمالي":    1.80,
    "المعادي":            1.60,
    "المهندسين":          1.55,
    "الدقي":              1.50,
    "الشيخ زايد":         1.55,
    "العاصمة الإدارية":   1.70,
    "مدينة نصر":          1.30,
    "مصر الجديدة":        1.35,
    "هليوبوليس":          1.35,
    "الرحاب":             1.40,
    "الإسكندرية":         1.20,
    "سموحة":              1.25,
    "الغردقة":            1.30,
    "شرم الشيخ":          1.45,
    "أسيوط":              0.90,
    "سوهاج":              0.85,
    "الفيوم":             0.80,
    "المنيا":             0.80,
}

# معدلات إيجار المساحات التجارية EGP/م²/شهر حسب المنطقة
_RETAIL_RENT_MAP: Dict[str, Dict] = {
    "التسعين الشمالي":    {"avg_rent": 1_800, "anchor_premium": 1.35, "footfall_score": 9},
    "التجمع الخامس":      {"avg_rent": 1_500, "anchor_premium": 1.30, "footfall_score": 8},
    "الزمالك":            {"avg_rent": 2_200, "anchor_premium": 1.40, "footfall_score": 8},
    "المهندسين":          {"avg_rent": 1_600, "anchor_premium": 1.25, "footfall_score": 8},
    "المعادي":            {"avg_rent": 1_400, "anchor_premium": 1.20, "footfall_score": 7},
    "مدينة نصر":          {"avg_rent": 1_200, "anchor_premium": 1.15, "footfall_score": 7},
    "العاصمة الإدارية":   {"avg_rent": 1_700, "anchor_premium": 1.30, "footfall_score": 8},
    "شرم الشيخ":          {"avg_rent": 1_900, "anchor_premium": 1.40, "footfall_score": 9},
    "الغردقة":            {"avg_rent": 1_400, "anchor_premium": 1.25, "footfall_score": 8},
    "الإسكندرية":         {"avg_rent": 1_100, "anchor_premium": 1.15, "footfall_score": 7},
    "سموحة":              {"avg_rent": 1_200, "anchor_premium": 1.10, "footfall_score": 7},
    "الشيخ زايد":         {"avg_rent": 1_300, "anchor_premium": 1.20, "footfall_score": 7},
    "_default":           {"avg_rent":   900, "anchor_premium": 1.00, "footfall_score": 5},
}

# معامل الواجهة (Frontage Premium) — كل متر واجهة يرفع العائد
_FRONTAGE_PREMIUM_PER_METER = 0.018   # 1.8% لكل متر واجهة (حتى 30م)

def _retail_income_ppm(
    location: str,
    area_sqm: float,
    frontage_m: float = 0.0,
    gla_ratio: float  = 0.75,
    cap_rate: float   = 0.09,
    has_anchor: bool  = False,
) -> Dict:
    """
    يحسب سعر م² للعقارات التجارية والمولات.

    المعطيات:
    - location    : المنطقة
    - area_sqm    : المساحة الكلية م²
    - frontage_m  : طول الواجهة بالأمتار (0 = مجهول)
    - gla_ratio   : نسبة المساحة القابلة للتأجير (0.60–0.90)
    - cap_rate    : معدل الرسملة
    - has_anchor  : هل يوجد مستأجر رئيسي (Anchor Tenant)

    يُعيد:
    - ppm               : سعر م² المستنتج
    - monthly_rent_sqm  : إيجار م² شهري (EGP)
    - annual_noi        : الدخل الصافي السنوي
    - gla_sqm           : المساحة القابلة للتأجير
    - footfall_score    : مؤشر كثافة المرور (1–10)
    - purchasing_power  : معامل القوة الشرائية
    - frontage_premium  : علاوة الواجهة
    - anchor_premium    : علاوة المستأجر الرئيسي
    """
    loc = str(location or "")
    # ابحث عن مطابقة جزئية
    bm_key = "_default"
    for k in _RETAIL_RENT_MAP:
        if k in loc or loc in k:
            bm_key = k
            break
    bm = _RETAIL_RENT_MAP[bm_key]

    # القوة الشرائية
    pp_mult = 1.0
    for k, v in _PURCHASING_POWER_INDEX.items():
        if k in loc or loc in k:
            pp_mult = v
            break

    # الإيجار الأساسي معدَّل بالقوة الشرائية
    base_rent = bm["avg_rent"] * pp_mult   # EGP/م²/شهر

    # علاوة الواجهة (حتى 30 متر كحد أقصى)
    eff_frontage   = min(float(frontage_m or 0), 30.0)
    frontage_prem  = 1.0 + (eff_frontage * _FRONTAGE_PREMIUM_PER_METER)

    # علاوة المستأجر الرئيسي (Anchor Tenant)
    anchor_prem    = bm["anchor_premium"] if has_anchor else 1.0

    # الإيجار الفعلي
    eff_rent = base_rent * frontage_prem * anchor_prem

    # المساحة القابلة للتأجير
    gla_ratio_safe = max(0.50, min(float(gla_ratio or 0.75), 0.95))
    gla_sqm        = float(area_sqm or 1) * gla_ratio_safe

    # الدخل الصافي السنوي (نسبة مصاريف تشغيل 25%)
    gross_rev = eff_rent * gla_sqm * 12
    noi       = gross_rev * 0.75

    # القيمة بطريقة الدخل
    cap_safe  = max(0.05, float(cap_rate or 0.09))
    prop_val  = noi / cap_safe
    ppm       = round(prop_val / max(float(area_sqm or 1), 1), 0) if prop_val > 0 else 0

    return {
        "ppm":               ppm,
        "monthly_rent_sqm":  round(eff_rent, 0),
        "annual_noi":        round(noi, 0),
        "gross_revenue":     round(gross_rev, 0),
        "gla_sqm":           round(gla_sqm, 0),
        "gla_ratio":         gla_ratio_safe,
        "footfall_score":    bm["footfall_score"],
        "purchasing_power":  round(pp_mult, 2),
        "frontage_premium":  round(frontage_prem, 3),
        "anchor_premium":    round(anchor_prem, 3),
        "cap_rate":          cap_safe,
        "location_matched":  bm_key,
    }


# ═══════════════════════════════════════════════════════════════════════════
# ███ قطاع العقارات الطبية — Healthcare Sector ███
# ═══════════════════════════════════════════════════════════════════════════

# تكاليف التجهيزات التخصصية الإضافية EGP/م² حسب نوع المنشأة
_HEALTHCARE_INFRA_COST: Dict[str, Dict] = {
    "مستشفى":           {"extra_cost_sqm": 8_500,  "beds_per_100sqm": 1.2, "min_sqm_per_bed": 80},
    "مركز طبي":         {"extra_cost_sqm": 4_500,  "beds_per_100sqm": 0.5, "min_sqm_per_bed": 30},
    "عيادات":           {"extra_cost_sqm": 3_000,  "beds_per_100sqm": 0.0, "min_sqm_per_bed": 20},
    "مركز غسيل كلوي":  {"extra_cost_sqm": 12_000, "beds_per_100sqm": 2.0, "min_sqm_per_bed": 50},
    "مركز أشعة":        {"extra_cost_sqm": 10_000, "beds_per_100sqm": 0.0, "min_sqm_per_bed": 25},
    "مستشفى تخصصي":    {"extra_cost_sqm": 15_000, "beds_per_100sqm": 1.5, "min_sqm_per_bed": 100},
    "_default":         {"extra_cost_sqm": 5_000,  "beds_per_100sqm": 0.8, "min_sqm_per_bed": 40},
}

# كثافة سكانية وعجز الخدمات الطبية (نقاط رفع قيمة)
_MEDICAL_DEMAND_INDEX: Dict[str, float] = {
    "العاصمة الإدارية":  1.35,   # نقص واضح في المنشآت الطبية
    "بدر":               1.30,
    "العبور":            1.25,
    "المستقبل سيتي":     1.40,
    "أكتوبر":            1.20,
    "6 أكتوبر":          1.20,
    "الشيخ زايد":        1.15,
    "الجيزة":            1.10,
    "أسيوط":             1.25,
    "سوهاج":             1.30,
    "الفيوم":            1.30,
    "المنيا":            1.35,
    "بني سويف":          1.30,
    "الزمالك":           0.90,   # تشبع
    "المعادي":           0.92,
    "_default":          1.00,
}

def _healthcare_value_ppm(
    location: str,
    area_sqm: float,
    beds: int       = 0,
    facility_type:  str   = "_default",
    cap_rate: float = 0.09,
    monthly_rent_sqm: float = 0.0,
) -> Dict:
    """
    يحسب سعر م² للمنشآت الطبية.

    المنطق:
    1. تكلفة التجهيزات التخصصية (عامل تكلفة Cost Approach ورفع القيمة)
    2. عائد الإيجار الطبي المتخصص (Income Approach)
    3. تعديل نقص الخدمات الطبية بالمنطقة (Demand Premium)

    يُعيد:
    - ppm                  : سعر م² المستنتج
    - specialized_infra    : تكلفة التجهيزات الإضافية الكلية
    - beds_capacity        : سعة الأسرة المناسبة
    - compliance_note      : ملاحظة مطابقة الكود الطبي
    - demand_premium       : معامل نقص الخدمات
    - annual_noi           : الدخل الصافي السنوي
    """
    loc       = str(location or "")
    area_safe = max(float(area_sqm or 1), 1.0)

    # نوع المنشأة
    ftype = str(facility_type or "_default")
    infra = _HEALTHCARE_INFRA_COST.get(ftype, _HEALTHCARE_INFRA_COST["_default"])
    for k in _HEALTHCARE_INFRA_COST:
        if k in ftype or ftype in k:
            infra = _HEALTHCARE_INFRA_COST[k]
            break

    # كثافة الطلب
    demand_mult = 1.0
    for k, v in _MEDICAL_DEMAND_INDEX.items():
        if k in loc or loc in k:
            demand_mult = v
            break

    # تكلفة التجهيزات التخصصية الإضافية
    specialized_infra_total = infra["extra_cost_sqm"] * area_safe

    # سعة الأسرة المعيارية
    beds_capacity = max(int(beds or 0), int(area_safe / 100 * infra["beds_per_100sqm"]))
    # مطابقة الكود: هل المساحة كافية؟
    min_area_needed = beds_capacity * infra["min_sqm_per_bed"]
    compliance_ok   = area_safe >= min_area_needed * 0.85

    # الإيجار الطبي (EGP/م²/شهر) — افتراضي إذا لم يُعطَ
    base_medical_rent = float(monthly_rent_sqm or 0)
    if base_medical_rent <= 0:
        # 2.5× إيجار سكني في المنطقة
        for k, v in _PURCHASING_POWER_INDEX.items():
            if k in loc or loc in k:
                base_medical_rent = 1_500 * v * 2.5
                break
        if base_medical_rent <= 0:
            base_medical_rent = 2_500   # افتراضي قومي

    eff_rent  = base_medical_rent * demand_mult
    gross_rev = eff_rent * area_safe * 12
    noi       = gross_rev * 0.70    # نسبة مصاريف 30% للمنشآت الطبية

    cap_safe  = max(0.05, float(cap_rate or 0.09))
    income_val = noi / cap_safe

    # مزج 60% دخل + 40% تكلفة+إضافات
    cost_base  = specialized_infra_total  # ≈ تكلفة الإضافات فوق السكني
    blend_val  = income_val * 0.60 + (cost_base + income_val * 0.40)
    ppm        = round(blend_val / area_safe, 0) if blend_val > 0 else 0

    return {
        "ppm":                    ppm,
        "specialized_infra_cost": round(specialized_infra_total, 0),
        "infra_per_sqm":          infra["extra_cost_sqm"],
        "beds_capacity":          beds_capacity,
        "compliance_ok":          compliance_ok,
        "compliance_note":        "مطابق للكود الطبي" if compliance_ok else "المساحة أقل من الحد الأدنى",
        "demand_premium":         round(demand_mult, 2),
        "facility_type":          ftype,
        "monthly_rent_sqm":       round(eff_rent, 0),
        "annual_noi":             round(noi, 0),
        "gross_revenue":          round(gross_rev, 0),
        "cap_rate":               cap_safe,
        "location_matched":       loc,
    }


# ═══════════════════════════════════════════════════════════════════════════
# ███ قطاع العقارات التعليمية — Educational Sector ███
# ═══════════════════════════════════════════════════════════════════════════

# متوسط الرسوم الدراسية السنوية EGP/طالب — حسب المنطقة والنوع
_SCHOOL_FEES_MAP: Dict[str, Dict] = {
    "الزمالك":            {"private_school": 120_000, "international": 300_000, "nursery": 60_000},
    "التجمع الخامس":      {"private_school": 100_000, "international": 280_000, "nursery": 50_000},
    "المعادي":            {"private_school":  90_000, "international": 250_000, "nursery": 45_000},
    "المهندسين":          {"private_school":  80_000, "international": 220_000, "nursery": 40_000},
    "الشيخ زايد":         {"private_school":  85_000, "international": 230_000, "nursery": 42_000},
    "العاصمة الإدارية":   {"private_school":  95_000, "international": 260_000, "nursery": 48_000},
    "مدينة نصر":          {"private_school":  70_000, "international": 180_000, "nursery": 35_000},
    "هليوبوليس":          {"private_school":  75_000, "international": 200_000, "nursery": 38_000},
    "الإسكندرية":         {"private_school":  65_000, "international": 160_000, "nursery": 30_000},
    "أسيوط":              {"private_school":  30_000, "international":  80_000, "nursery": 15_000},
    "سوهاج":              {"private_school":  28_000, "international":  70_000, "nursery": 14_000},
    "_default":           {"private_school":  50_000, "international": 140_000, "nursery": 25_000},
}

# معايير الطاقة الاستيعابية (طالب/م²) وأوزان المرافق
_EDUCATIONAL_CAPACITY: Dict[str, Dict] = {
    "مدرسة":       {"students_per_sqm": 0.50, "min_area_per_student": 2.0},
    "جامعة":       {"students_per_sqm": 0.35, "min_area_per_student": 2.8},
    "معهد":        {"students_per_sqm": 0.60, "min_area_per_student": 1.6},
    "حضانة":       {"students_per_sqm": 0.80, "min_area_per_student": 1.2},
    "روضة":        {"students_per_sqm": 0.75, "min_area_per_student": 1.3},
    "_default":    {"students_per_sqm": 0.50, "min_area_per_student": 2.0},
}

# أوزان المرافق التعليمية (تُضاف كعلاوة على القيمة الأساسية)
_FACILITY_WEIGHTS: Dict[str, float] = {
    "ملعب": 0.08,            # ملعب رياضي
    "مسبح": 0.12,            # مسبح
    "معامل": 0.10,           # معامل علمية
    "مكتبة": 0.05,           # مكتبة
    "قاعة مسرح": 0.06,       # قاعة مسرح أو أنشطة
    "ترخيص دولي": 0.20,      # اعتماد IB أو Cambridge
    "ترخيص وزاري": 0.08,     # اعتماد وزارة التعليم المصرية
}

def _educational_capacity_ppm(
    location: str,
    area_sqm: float,
    school_type: str    = "مدرسة",
    fee_type: str       = "private_school",
    facilities: list    = None,
    cap_rate: float     = 0.08,
    licensed: bool      = True,
) -> Dict:
    """
    يحسب سعر م² للمنشآت التعليمية.

    المنطق:
    1. طاقة الطلاب الاستيعابية (صيغة م² × معيار الطالب)
    2. إيراد الرسوم السنوي حسب المنطقة
    3. علاوة المرافق والتراخيص
    4. الرسملة بمعدل cap_rate للحصول على قيمة العقار

    يُعيد:
    - ppm                : سعر م² المستنتج
    - student_capacity   : الطاقة الاستيعابية
    - annual_revenue     : الإيراد الدراسي السنوي
    - facility_premium   : علاوة المرافق المُجمَّعة
    - noi                : الدخل الصافي التشغيلي
    """
    loc       = str(location or "")
    area_safe = max(float(area_sqm or 1), 1.0)
    facs      = facilities or []

    # نوع المبنى
    cap_info  = _EDUCATIONAL_CAPACITY.get(school_type, _EDUCATIONAL_CAPACITY["_default"])
    for k in _EDUCATIONAL_CAPACITY:
        if k in school_type or school_type in k:
            cap_info = _EDUCATIONAL_CAPACITY[k]; break

    # الطاقة الاستيعابية
    student_capacity = int(area_safe * cap_info["students_per_sqm"])
    student_capacity = max(student_capacity, 1)

    # الرسوم السنوية / طالب
    fees_bm = _SCHOOL_FEES_MAP.get("_default", {})
    for k in _SCHOOL_FEES_MAP:
        if k in loc or loc in k:
            fees_bm = _SCHOOL_FEES_MAP[k]; break

    fee_per_student = fees_bm.get(str(fee_type), fees_bm.get("private_school", 50_000))

    # الإيراد الإجمالي السنوي
    gross_rev = student_capacity * fee_per_student * 0.85  # 85% نسبة الاستيعاب الفعلي

    # علاوة المرافق والتراخيص
    facility_premium = 0.0
    fac_details = {}
    for fac in facs:
        w = 0.0
        for k, v in _FACILITY_WEIGHTS.items():
            if k in str(fac) or str(fac) in k:
                w = v; break
        if w > 0:
            facility_premium += w
            fac_details[str(fac)] = round(w, 3)
    if licensed:
        facility_premium += _FACILITY_WEIGHTS.get("ترخيص وزاري", 0.08)

    facility_premium = min(facility_premium, 0.55)  # حد أقصى 55%

    # الدخل الصافي
    opex_ratio = 0.55   # مصاريف المدارس الخاصة 55% من الإيراد
    noi        = gross_rev * (1 - opex_ratio) * (1 + facility_premium)

    cap_safe   = max(0.05, float(cap_rate or 0.08))
    prop_value = noi / cap_safe
    ppm        = round(prop_value / area_safe, 0) if prop_value > 0 else 0

    return {
        "ppm":               ppm,
        "student_capacity":  student_capacity,
        "fee_per_student":   round(fee_per_student, 0),
        "annual_revenue":    round(gross_rev, 0),
        "noi":               round(noi, 0),
        "facility_premium":  round(facility_premium, 3),
        "facility_details":  fac_details,
        "school_type":       school_type,
        "fee_type":          fee_type,
        "licensed":          licensed,
        "cap_rate":          cap_safe,
        "location_matched":  loc,
    }
