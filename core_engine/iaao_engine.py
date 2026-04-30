# -*- coding: utf-8 -*-
"""
iaao_engine.py — IAAO Mass Appraisal Standards Engine
Expert_Smart v37 | Tax Pathway Intelligence
=======================================================
Standards Reference: IAAO Standard on Ratio Studies (2013)
Metrics:
  ASR  — Assessment-to-Sales Ratio (Median)       target: 0.95 – 1.05
  COD  — Coefficient of Dispersion                 target: < 15% residential
  PRD  — Price-Related Differential                target: 0.98 – 1.03
  PRB  — Price-Related Bias (regression-based)     target: |PRB| ≤ 0.05
"""

import math
import statistics
from typing import List, Dict, Optional, Tuple

# ── Traffic-light thresholds ─────────────────────────────────────────────────
_SECTOR_COD_MAX = {
    "residential":  15.0,
    "commercial":   20.0,
    "agricultural": 25.0,
    "industrial":   20.0,
    "hospitality":  20.0,
    "retail":       20.0,
    "healthcare":   20.0,
    "educational":  20.0,
}

# ── Emoji & colour tokens for HTML / Excel output ────────────────────────────
_LIGHT_META = {
    "green":  {"emoji": "🟢", "hex": "#16a34a", "bg": "#dcfce7", "ar": "مطابق"},
    "yellow": {"emoji": "🟡", "hex": "#ca8a04", "bg": "#fef9c3", "ar": "تحذير"},
    "red":    {"emoji": "🔴", "hex": "#dc2626", "bg": "#fee2e2", "ar": "خطر"},
    "grey":   {"emoji": "⚪", "hex": "#6b7280", "bg": "#f3f4f6", "ar": "غير كافٍ"},
}


# ══════════════════════════════════════════════════════════════════════════════
#  Primitive calculators
# ══════════════════════════════════════════════════════════════════════════════

def compute_ratios(
    assessed_values: List[float],
    sale_prices:     List[float],
) -> List[float]:
    """
    نسبة التقييم إلى البيع لكل عقار.
    يُستبعد أي سعر بيع صفري أو سالب.
    """
    if len(assessed_values) != len(sale_prices):
        raise ValueError("يجب أن تكون القيم المقدَّرة وأسعار البيع بنفس الطول")
    return [av / sp for av, sp in zip(assessed_values, sale_prices) if sp > 0]


def compute_asr(ratios: List[float]) -> Dict:
    """
    ASR — النسبة الوسيطة للتقييم إلى البيع.
    معيار IAAO: 0.95 ≤ ASR ≤ 1.05
    """
    if len(ratios) < 2:
        return _insufficient("asr")
    median_r = statistics.median(ratios)
    mean_r   = statistics.mean(ratios)
    if 0.95 <= median_r <= 1.05:
        light = "green"; lbl = f"مقبول — ASR = {median_r:.3f} ضمن النطاق (0.95–1.05)"
    elif 0.90 <= median_r < 0.95 or 1.05 < median_r <= 1.10:
        light = "yellow"; lbl = f"تحذير — ASR = {median_r:.3f} خارج النطاق قليلاً"
    else:
        light = "red"; lbl = f"خطر — ASR = {median_r:.3f} تحيّز كبير في التقييم"
    return {
        "metric": "ASR", "value": round(median_r, 4), "mean": round(mean_r, 4),
        "count": len(ratios),
        "benchmark": "0.95 – 1.05",
        **_light(light, lbl),
    }


def compute_cod(ratios: List[float], sector: str = "residential") -> Dict:
    """
    COD — معامل التشتت.
    يقيس العدالة الأفقية (horizontal equity).
    معيار IAAO: COD < 15% للسكني، < 20% لغيره.
    """
    if len(ratios) < 3:
        return _insufficient("cod")
    median_r     = statistics.median(ratios)
    avg_abs_dev  = statistics.mean([abs(r - median_r) for r in ratios])
    cod          = (avg_abs_dev / median_r) * 100 if median_r else 0
    cod_max      = _SECTOR_COD_MAX.get(sector, 20.0)
    excellent    = cod_max * 0.67  # < 10% for residential

    if cod < excellent:
        light = "green";  lbl = f"ممتاز — COD = {cod:.1f}%"
    elif cod <= cod_max:
        light = "green";  lbl = f"مقبول — COD = {cod:.1f}% (الحد {cod_max:.0f}%)"
    elif cod <= cod_max * 1.33:
        light = "yellow"; lbl = f"تحذير — COD = {cod:.1f}% يتجاوز {cod_max:.0f}%"
    else:
        light = "red";    lbl = f"خطر — COD = {cod:.1f}% يتجاوز {cod_max*1.33:.0f}%"

    return {
        "metric": "COD", "value": round(cod, 2), "unit": "%",
        "median_ratio": round(median_r, 4),
        "avg_abs_deviation": round(avg_abs_dev, 4),
        "count": len(ratios),
        "benchmark": f"< {cod_max:.0f}%",
        **_light(light, lbl),
    }


def compute_prd(ratios: List[float], sale_prices: List[float]) -> Dict:
    """
    PRD — مؤشر التفاوت المرتبط بالسعر.
    يكشف عن عدم العدالة الرأسية (vertical inequity).
    معيار IAAO: 0.98 ≤ PRD ≤ 1.03
    """
    if len(ratios) < 3 or len(sale_prices) != len(ratios):
        return _insufficient("prd")
    mean_r    = statistics.mean(ratios)
    total_sp  = sum(sale_prices)
    if total_sp == 0:
        return _insufficient("prd")
    weighted_r = sum(r * sp for r, sp in zip(ratios, sale_prices)) / total_sp
    if weighted_r == 0:
        return _insufficient("prd")
    prd = mean_r / weighted_r
    if 0.98 <= prd <= 1.03:
        light = "green";  lbl = f"PRD = {prd:.3f} — لا تحيّز رأسي"
    elif 0.95 <= prd < 0.98:
        light = "yellow"; lbl = f"PRD = {prd:.3f} — تحذير: تحيّز إيجابي طفيف"
    elif 1.03 < prd <= 1.06:
        light = "yellow"; lbl = f"PRD = {prd:.3f} — تحذير: تحيّز سلبي طفيف"
    else:
        light = "red";    lbl = f"PRD = {prd:.3f} — خطر: تحيّز رأسي واضح"
    direction = "regressive" if prd > 1.03 else "progressive" if prd < 0.98 else "neutral"
    return {
        "metric": "PRD", "value": round(prd, 4),
        "mean_ratio": round(mean_r, 4), "weighted_ratio": round(weighted_r, 4),
        "direction": direction,
        "count": len(ratios),
        "benchmark": "0.98 – 1.03",
        **_light(light, lbl),
    }


def compute_prb(ratios: List[float], sale_prices: List[float]) -> Dict:
    """
    PRB — التحيّز المرتبط بالسعر (اختبار انحدار).
    المعيار الحديث لعدم العدالة الرأسية (IAAO 2013).
    |PRB| ≤ 0.05 مقبول.
    """
    if len(ratios) < 5 or len(sale_prices) != len(ratios):
        return _insufficient("prb")
    ln_prices = [math.log(sp) if sp > 0 else 0.0 for sp in sale_prices]
    mean_x = statistics.mean(ln_prices)
    mean_y = statistics.mean(ratios)
    ss_xy  = sum((x - mean_x) * (y - mean_y) for x, y in zip(ln_prices, ratios))
    ss_xx  = sum((x - mean_x) ** 2 for x in ln_prices)
    if ss_xx == 0:
        return _insufficient("prb")
    b = ss_xy / ss_xx  # slope = PRB
    if abs(b) <= 0.05:
        light = "green";  lbl = f"PRB = {b:.4f} — لا تحيّز رأسي"
    elif abs(b) <= 0.10:
        light = "yellow"; lbl = f"PRB = {b:.4f} — تحيّز بسيط"
    else:
        light = "red";    lbl = f"PRB = {b:.4f} — تحيّز رأسي واضح"
    return {
        "metric": "PRB", "value": round(b, 4),
        "count": len(ratios),
        "benchmark": "|PRB| ≤ 0.05",
        **_light(light, lbl),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Full IAAO Report
# ══════════════════════════════════════════════════════════════════════════════

def full_iaao_report(
    assessed_values: List[float],
    sale_prices:     List[float],
    location:        str = "",
    sector:          str = "residential",
    period:          str = "",
) -> Dict:
    """
    تقرير IAAO كامل: ASR + COD + PRD + PRB + إشارات + توصيات
    """
    if len(assessed_values) < 3 or len(sale_prices) < 3:
        return {
            "status": "insufficient_data",
            "message": f"يلزم 3 مقارنات على الأقل (وُجد {len(assessed_values)})",
        }

    ratios = compute_ratios(assessed_values, sale_prices)
    asr    = compute_asr(ratios)
    cod    = compute_cod(ratios, sector)
    prd    = compute_prd(ratios, sale_prices)
    prb    = compute_prb(ratios, sale_prices)

    lights = [asr["traffic_light"], cod["traffic_light"], prd["traffic_light"]]
    if all(l == "green" for l in lights):
        overall = "green";  overall_ar = "✅ مستوفٍ لمعايير IAAO بالكامل"
    elif "red" in lights:
        overall = "red";    overall_ar = "❌ انتهاك جوهري — مراجعة فورية مطلوبة"
    else:
        overall = "yellow"; overall_ar = "⚠️ مطابقة جزئية — يُوصى بالمراجعة الدورية"

    recs = _build_recommendations(asr, cod, prd, prb)

    return {
        "status": "success",
        "overall_light":     overall,
        "overall_ar":        overall_ar,
        "overall_meta":      _LIGHT_META[overall],
        "metrics":           {"asr": asr, "cod": cod, "prd": prd, "prb": prb},
        "count":             len(ratios),
        "location":          location,
        "sector":            sector,
        "period":            period,
        "sector_cod_max":    _SECTOR_COD_MAX.get(sector, 20.0),
        "recommendations":   recs,
        "standard":          "IAAO Standard on Ratio Studies (2013 Edition)",
        "generated_at":      _now(),
    }


def iaao_from_comparables(
    comparables:   List[Dict],
    assessed_ppm:  float,
    sector:        str = "residential",
    location:      str = "",
) -> Dict:
    """
    حساب IAAO مباشرة من قائمة مقارنات.
    كل مقارنة: {"price": float, "area": float, ...}
    assessed_ppm: القيمة المُقدَّرة للمتر المربع من نظام التقييم.
    """
    if not comparables or assessed_ppm <= 0:
        return {"status": "insufficient_data",
                "message": "يلزم توفير مقارنات وقيمة متر مُقدَّرة"}
    sale_ppms, assessed_ppms = [], []
    for c in comparables:
        try:
            price = float(c.get("price") or c.get("total_price") or 0)
            area  = float(c.get("area")  or c.get("area_sqm")    or 1)
            if price > 0 and area > 0:
                sale_ppms.append(price / area)
                assessed_ppms.append(assessed_ppm)
        except (TypeError, ValueError, ZeroDivisionError):
            continue
    if len(sale_ppms) < 3:
        return {"status": "insufficient_data",
                "message": f"مقارنات صالحة: {len(sale_ppms)} (الحد الأدنى 3)"}
    return full_iaao_report(assessed_ppms, sale_ppms, location=location, sector=sector)


# ══════════════════════════════════════════════════════════════════════════════
#  Excel-ready row builder  (for bridge_api.py)
# ══════════════════════════════════════════════════════════════════════════════

def iaao_excel_rows(report: Dict) -> List[Tuple]:
    """
    يُعيد قائمة صفوف جاهزة للكتابة في إكسيل:
    [(label_ar, value, benchmark, status_ar, emoji), ...]
    """
    if report.get("status") != "success":
        return [("بيانات غير كافية لتطبيق معايير IAAO", "—", "—", "—", "⚪")]
    m = report["metrics"]
    rows = []
    for key in ("asr", "cod", "prd", "prb"):
        metric = m[key]
        val    = metric.get("value", "—")
        unit   = "%" if metric.get("unit") == "%" else ""
        rows.append((
            metric.get("metric", key.upper()),
            f"{val}{unit}" if isinstance(val, (int, float)) else str(val),
            metric.get("benchmark", "—"),
            metric.get("label", "—"),
            _LIGHT_META.get(metric.get("traffic_light", "grey"), {}).get("emoji", "⚪"),
        ))
    rows.append(("الحكم الإجمالي", "—", "—",
                 report.get("overall_ar", "—"),
                 _LIGHT_META.get(report["overall_light"], {}).get("emoji", "⚪")))
    return rows


# ══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _light(light: str, label: str) -> Dict:
    meta = _LIGHT_META.get(light, _LIGHT_META["grey"])
    return {
        "traffic_light": light,
        "traffic_emoji": meta["emoji"],
        "traffic_hex":   meta["hex"],
        "traffic_bg":    meta["bg"],
        "label":         label,
        "status":        "ok" if light == "green" else "warning" if light == "yellow" else "critical",
    }


def _insufficient(metric: str) -> Dict:
    return {
        "metric": metric.upper(),
        "value": 0,
        "count": 0,
        "benchmark": "—",
        **_light("grey", "بيانات غير كافية"),
    }


def _build_recommendations(asr: Dict, cod: Dict, prd: Dict, prb: Dict) -> List[str]:
    recs = []
    asr_v = asr.get("value", 1.0)
    cod_v = cod.get("value", 0)
    prd_v = prd.get("value", 1.0)
    prb_v = abs(prb.get("value", 0))

    if cod_v > 20:
        recs.append("مراجعة بيانات المقارنات لتقليل التشتت في نسب التقييم (COD مرتفع جداً)")
    elif cod_v > 15:
        recs.append("تحسين الاتساق في نسب التقييم (COD = {:.1f}% يتجاوز 15%)".format(cod_v))

    if prd_v > 1.03:
        recs.append("الأصول الأرخص مُقيَّمة أعلى نسبياً — مراجعة منهجية التقييم للعدالة الرأسية (تحيّز تراجعي)")
    elif prd_v < 0.98:
        recs.append("الأصول الأغلى مُقيَّمة أعلى نسبياً — تحيّز تصاعدي يستدعي المراجعة")

    if prb_v > 0.10:
        recs.append(f"PRB = {prb.get('value',0):.4f} — تحيّز رأسي كبير؛ مراجعة مصفوفة التعديلات مطلوبة")

    if asr_v < 0.90:
        recs.append("القيم المُقدَّرة منخفضة بشكل عام — يُوصى بإعادة المعايرة الشاملة")
    elif asr_v > 1.10:
        recs.append("القيم المُقدَّرة مرتفعة — خطر الطعون القانونية؛ مراجعة مستوى التقييم مطلوبة")

    if not recs:
        recs.append("النظام مُعايَر بشكل جيد — لا توصيات تصحيحية فورية")
    return recs


def _now() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
