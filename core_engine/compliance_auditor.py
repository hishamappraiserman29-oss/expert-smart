"""
compliance_auditor.py
=====================
IVS / USPAP Compliance Auditor + Expert DNA Cloner

Two capabilities:
  1. audit_report(text)          → Compliance Scorecard dict
  2. extract_expert_dna(text)    → Professional DNA dict (tone/structure/adjustments)

Usage:
    from compliance_auditor import audit_report, extract_expert_dna
    scorecard = audit_report(report_text)
    dna       = extract_expert_dna(report_text)
"""
from __future__ import annotations
import os
import re
import json
from datetime import datetime
from typing import Dict, List, Tuple


# ─── IVS / USPAP checklist definitions ───────────────────────────────────────

_IVS_CHECKLIST: List[Dict] = [
    # Mandatory IVS 104 (Bases of Value)
    {"code": "IVS-104-1",  "section": "أساس القيمة",
     "description": "تحديد أساس القيمة بوضوح (القيمة السوقية العادلة / التصفية / الإيجارية)",
     "keywords": ["القيمة السوقية", "fair market value", "أساس القيمة", "basis of value"],
     "weight": 8},
    # IVS 105 (Valuation Approaches)
    {"code": "IVS-105-1",  "section": "أساليب التقييم",
     "description": "استخدام أسلوب مقارنة السوق",
     "keywords": ["مقارنة السوق", "market approach", "sales comparison", "البيوع السابقة"],
     "weight": 10},
    {"code": "IVS-105-2",  "section": "أساليب التقييم",
     "description": "استخدام أسلوب التكلفة (DRC)",
     "keywords": ["التكلفة", "cost approach", "DRC", "التكلفة الاستبدالية", "إهلاك"],
     "weight": 8},
    {"code": "IVS-105-3",  "section": "أساليب التقييم",
     "description": "استخدام أسلوب الدخل / رأسمالة",
     "keywords": ["الدخل", "income approach", "رأسمالة", "NOI", "cap rate"],
     "weight": 8},
    {"code": "IVS-105-4",  "section": "التوفيق",
     "description": "توفيق النتائج بين الأساليب المستخدمة",
     "keywords": ["توفيق", "reconciliation", "الوزن النسبي", "weighted"],
     "weight": 10},
    # IVS 103 (Reporting)
    {"code": "IVS-103-1",  "section": "التقرير",
     "description": "ذكر هوية الخبير المعتمد وقيده المهني",
     "keywords": ["الخبير", "expert", "قيد", "معتمد", "certified", "خبير مقيم"],
     "weight": 7},
    {"code": "IVS-103-2",  "section": "التقرير",
     "description": "ذكر تاريخ ومدة صلاحية التقييم",
     "keywords": ["تاريخ التقييم", "valuation date", "صلاحية", "effective date"],
     "weight": 6},
    {"code": "IVS-103-3",  "section": "التقرير",
     "description": "وصف العقار موضوع التقييم",
     "keywords": ["موضوع التقييم", "subject property", "وصف", "وحدة"],
     "weight": 7},
    {"code": "IVS-103-4",  "section": "التقرير",
     "description": "ذكر الغرض من التقييم",
     "keywords": ["الغرض", "purpose", "هدف التقييم", "مقتضيات"],
     "weight": 6},
    # IVS 105 (HBU)
    {"code": "IVS-105-5",  "section": "أعلى وأفضل استخدام",
     "description": "تحليل أعلى وأفضل استخدام (HBU)",
     "keywords": ["HBU", "أعلى وأفضل", "highest and best", "أقصى استخدام"],
     "weight": 8},
    # Assumptions & Limiting Conditions
    {"code": "IVS-103-5",  "section": "المحددات",
     "description": "ذكر الافتراضات والمحددات",
     "keywords": ["افتراضات", "assumptions", "محددات", "limitations", "تحفظات"],
     "weight": 5},
    # Market Data & Sources
    {"code": "IVS-105-6",  "section": "مصادر البيانات",
     "description": "الإشارة إلى مصادر بيانات السوق",
     "keywords": ["مصادر", "sources", "بيانات السوق", "market data", "مقارنات"],
     "weight": 7},
    # Certification
    {"code": "IVS-103-6",  "section": "الشهادة",
     "description": "شهادة وتوقيع الخبير المعتمد",
     "keywords": ["شهادة", "certificate", "أُقر", "أشهد", "توقيع", "signature"],
     "weight": 5},
    # USPAP specifics (bonus points)
    {"code": "USPAP-SR1",  "section": "USPAP",
     "description": "الالتزام بمتطلبات تقرير USPAP Standard Rule 2",
     "keywords": ["USPAP", "appraisal report", "uniform standards", "قياسي"],
     "weight": 5},
]

_MAX_SCORE = sum(c["weight"] for c in _IVS_CHECKLIST)


def audit_report(report_text: str) -> Dict:
    """
    Audits a valuation report text against IVS/USPAP checklist.

    Returns:
    {
      "score": int (0-100),
      "grade": str,
      "passed": [...],
      "failed": [...],
      "recommendations": [...],
      "timestamp": str,
    }
    """
    text_lower = report_text.lower()

    passed   = []
    failed   = []
    earned   = 0

    for item in _IVS_CHECKLIST:
        found = any(kw.lower() in text_lower for kw in item["keywords"])
        entry = {
            "code":        item["code"],
            "section":     item["section"],
            "description": item["description"],
            "weight":      item["weight"],
        }
        if found:
            earned += item["weight"]
            passed.append(entry)
        else:
            failed.append(entry)

    score = round(earned / _MAX_SCORE * 100)

    if score >= 90:
        grade = "ممتاز (A+)"
    elif score >= 80:
        grade = "جيد جداً (A)"
    elif score >= 70:
        grade = "جيد (B)"
    elif score >= 60:
        grade = "مقبول (C)"
    else:
        grade = "يحتاج مراجعة (D)"

    recommendations = []
    for f in failed:
        recommendations.append(
            f"[{f['code']}] أضف قسم «{f['section']}»: {f['description']}"
        )

    return {
        "score":           score,
        "grade":           grade,
        "earned_points":   earned,
        "max_points":      _MAX_SCORE,
        "passed":          passed,
        "failed":          failed,
        "recommendations": recommendations,
        "timestamp":       datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


# ─── Expert DNA Extractor ─────────────────────────────────────────────────────

_TONE_PATTERNS = {
    "formal_arabic":    r"(وفق|يُعدّ|يتبين|بناءً على|وفقاً لـ|تمت الدراسة)",
    "quantitative":     r"(\d[\d,\.]+\s*(ج\.م|EGP|ريال|SAR|جنيه|مليون))",
    "legal_reference":  r"(قانون|لائحة|معيار|IVS|USPAP|TAQEEM|EFSA|المعايير الدولية)",
    "cautious":         r"(يُلاحظ|يُشار|مع مراعاة|شريطة|في حدود|تقديري)",
    "descriptive_adj":  r"(متميز|راقي|سوبر لوكس|فاخر|ممتاز|مناسب|جيد)",
}

_SECTION_PATTERNS = {
    "has_cover":         r"(تقرير تقييم|valuation report|خبير مقيم)",
    "has_hbu":           r"(أعلى وأفضل|HBU|highest.*best|أقصى استخدام)",
    "has_market_grid":   r"(جدول المقارنات|sales grid|مصفوفة|adjustment grid)",
    "has_cost_table":    r"(تكلفة الاستبدال|DRC|gross replacement|إهلاك.*جدول)",
    "has_income_table":  r"(صافي الدخل|NOI|cap rate|رأسمالة.*جدول)",
    "has_reconcile":     r"(توفيق|التوفيق النهائي|reconciliation|الوزن النسبي)",
    "has_cert":          r"(أُقر وأشهد|شهادة المقيم|I hereby certify|certification)",
    "has_assumptions":   r"(افتراضات|محددات|limiting conditions|تحفظات)",
}

_ADJUSTMENT_PATTERNS: List[Tuple[str, str]] = [
    (r"تعديل.*?([\+\-]\s*\d+\.?\d*\s*%)", "adjustment_pct"),
    (r"خصم.*?([\+\-]?\s*\d+\.?\d*\s*%)",  "discount_pct"),
    (r"معدل الرسملة.*?(\d+\.?\d*\s*%)",    "cap_rate"),
    (r"معدل الإهلاك.*?(\d+\.?\d*\s*%)",    "depr_rate"),
    (r"(WACC|معدل الخصم).*?(\d+\.?\d*\s*%)", "wacc"),
]


def extract_expert_dna(report_text: str) -> Dict:
    """
    Extracts the "Professional DNA" from an existing valuation report:
    tone patterns, section structure, adjustment magnitudes.

    Returns a dict that can be injected into new report generation prompts.
    """
    text = report_text

    # Tone analysis
    tone_scores: Dict[str, int] = {}
    for tone, pattern in _TONE_PATTERNS.items():
        hits = len(re.findall(pattern, text, re.IGNORECASE | re.UNICODE))
        tone_scores[tone] = hits

    dominant_tone = max(tone_scores, key=tone_scores.get) if tone_scores else "formal_arabic"

    # Section presence
    sections_found = {}
    for sec, pattern in _SECTION_PATTERNS.items():
        sections_found[sec] = bool(re.search(pattern, text, re.IGNORECASE | re.UNICODE))

    # Adjustment magnitudes
    adjustments_found: List[Dict] = []
    for pattern, kind in _ADJUSTMENT_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE | re.UNICODE):
            try:
                pct_str = m.group(1) if m.lastindex and m.lastindex >= 1 else ""
                pct_val = float(re.sub(r"[^0-9\.\-\+]", "", pct_str))
                adjustments_found.append({"type": kind, "value_pct": pct_val})
            except Exception:
                pass

    # Average adjustments per type
    adj_summary: Dict[str, float] = {}
    for a in adjustments_found:
        t = a["type"]
        adj_summary.setdefault(t, [])
        adj_summary[t].append(a["value_pct"])    # type: ignore[index]
    adj_avg = {t: round(sum(v) / len(v), 2) for t, v in adj_summary.items()}   # type: ignore

    # Writing style sample (first 300 chars of substantive text)
    style_sample = re.sub(r'\s+', ' ', text[:800]).strip()[:300]

    # GPT-enhanced DNA (only if key available)
    gpt_dna = ""
    try:
        import openai
        key = os.getenv("OPENAI_API_KEY", "")
        if key:
            client = openai.OpenAI(api_key=key)
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": (
                        "أنت محلل تقارير تقييم عقاري. استخلص من هذا المقطع:\n"
                        "1. أسلوب الكتابة المهني (جملتين)\n"
                        "2. طريقة التعامل مع التعديلات (جملة)\n"
                        "3. مستوى التحفظ في الصياغة (منخفض/متوسط/عالي)\n\n"
                        f"المقطع:\n{style_sample}\n\nرد موجز (3 أسطر)."
                    )
                }],
                max_tokens=150,
                temperature=0.3,
            )
            gpt_dna = resp.choices[0].message.content.strip()
    except Exception:
        pass

    return {
        "dominant_tone":    dominant_tone,
        "tone_scores":      tone_scores,
        "sections_found":   sections_found,
        "sections_coverage": round(sum(sections_found.values()) / len(sections_found) * 100),
        "adjustment_averages": adj_avg,
        "style_sample":     style_sample,
        "gpt_analysis":     gpt_dna,
        "timestamp":        datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


# ─── CLI quick test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    sample = """
    تقرير تقييم عقاري احترافي — معايير IVS الدولية
    الخبير المعتمد: هشام محمد المهدى — رقم القيد 29
    تاريخ التقييم: 2026/04/12 | الغرض: تحديد القيمة السوقية العادلة

    أولاً: أعلى وأفضل استخدام (HBU)
    بناءً على دراسة جدوى متكاملة يتبين أن الاستخدام السكني يحقق أعلى قيمة مضافة.

    ثانياً: أسلوب مقارنة البيوع السابقة
    مصفوفة مقارنات السوق: تعديل الموقع +5%، تعديل التشطيب -10%

    ثالثاً: أسلوب التكلفة الاستبدالية المستهلكة (DRC)
    تكلفة الإحلال: 5,500 EGP/م² | إهلاك 15%

    رابعاً: رأسمالة الدخل | NOI = 450,000 EGP | Cap Rate = 8%

    خامساً: التوفيق النهائي — الوزن النسبي بين الأساليب الثلاثة

    شهادة: أُقر وأشهد أن هذا التقرير أُعدّ وفق معايير IVS.
    الافتراضات والمحددات: البيانات مبنية على معاينة ميدانية.
    مصادر بيانات السوق: aqar.eg، propertyfinder.eg
    """
    sc = audit_report(sample)
    print(f"Score: {sc['score']}/100 — {sc['grade']}")
    print(f"Passed: {len(sc['passed'])} | Failed: {len(sc['failed'])}")
    print("\nRecommendations:")
    for r in sc["recommendations"]:
        print(f"  {r}")

    dna = extract_expert_dna(sample)
    print(f"\nExpert DNA — dominant tone: {dna['dominant_tone']}")
    print(f"Sections coverage: {dna['sections_coverage']}%")
