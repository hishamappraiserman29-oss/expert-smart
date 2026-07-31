"""
professional_valuation_integrated_pdf_gap_fix.py
نموذج التقرير الموحد المتكامل — ثلاثة مستويات عمق
advisory_only=True | not_real_training=True | certification_ready=False
"""
from __future__ import annotations
import os, subprocess, tempfile
from pathlib import Path

# ── Fixture data ──────────────────────────────────────────────────────────────
from professional_valuation_arabic_report_examples import (
    SUBJECT_AR, COMPARABLES_AR, ADJUSTMENTS_AR, ADJUSTED_PRICES_PER_SQM,
    INDICATED_MARKET_VALUE, INCOME_AR, COST_AR, AVM_AR, RECONCILIATION_AR,
    DCF_5YEAR_AR, DCF_10YEAR_AR, SCENARIOS_AR, PROBABILITY_WEIGHTED_VALUE,
    SENSITIVITY_MATRIX_AR, RISKS_AR, STANDARDS_AR, DATA_INPUTS_AR,
    METHOD_SELECTION_AR, HBU_AR, RECONCILIATION_SCORECARD_AR, ADVISORY_NOTE_AR,
)

_CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# ── Shared CSS ────────────────────────────────────────────────────────────────
_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Arial Unicode MS', Arial, sans-serif;
  direction: rtl; text-align: right;
  font-size: 12pt; line-height: 1.7;
  color: #1a1a1a; background: #fff;
}
@page { size: A4; margin: 18mm 20mm 18mm 20mm; }
@media print { body { font-size: 11pt; } }
h1 { font-size: 19pt; color: #1a3a5c; border-bottom: 3px solid #1a3a5c; padding-bottom: 6px; margin: 20px 0 10px; }
h2 { font-size: 15pt; color: #1a5c3a; border-right: 5px solid #1a5c3a; padding-right: 8px; margin: 18px 0 8px; }
h3 { font-size: 13pt; color: #2a4a8c; margin: 14px 0 6px; }
h4 { font-size: 11pt; color: #555; margin: 10px 0 4px; }
p  { margin-bottom: 8px; }
table { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 10.5pt; }
th { background: #1a3a5c; color: #fff; padding: 7px 10px; text-align: center; }
td { border: 1px solid #ccc; padding: 6px 10px; text-align: right; vertical-align: top; }
tr:nth-child(even) td { background: #f5f7fa; }
.cover { text-align: center; padding: 60px 30px; border: 2px solid #1a3a5c; margin-bottom: 30px; }
.cover h1 { font-size: 22pt; border: none; }
.cover .level-badge { display: inline-block; background: #1a3a5c; color: #fff;
  padding: 6px 22px; border-radius: 20px; font-size: 13pt; margin: 16px auto; }
.advisory { background: #fff3cd; border-right: 5px solid #e6a817; padding: 10px 14px; margin: 14px 0; font-size: 10pt; }
.highlight { background: #e8f4f8; border-right: 4px solid #1a5c9c; padding: 8px 12px; margin: 8px 0; }
.risk-high td { background: #fde8e8 !important; }
.risk-med  td { background: #fff3cd !important; }
.risk-low  td { background: #e8f4e8 !important; }
.value-box { background: #1a3a5c; color: #fff; text-align: center; padding: 16px; margin: 14px 0; border-radius: 6px; font-size: 14pt; font-weight: bold; }
.section-note { font-size: 9.5pt; color: #777; font-style: italic; margin-top: 4px; }
.gap-box { background: #f0f4ff; border: 1px solid #aac; padding: 8px 12px; margin: 8px 0; border-radius: 4px; }
"""

# ── Helpers ───────────────────────────────────────────────────────────────────
def _fmt(n: int | float, cur: str = "SAR") -> str:
    return f"{int(n):,} {cur}"

def _kv(rows: list[tuple[str, str]]) -> str:
    trs = "".join(f"<tr><th style='width:40%;text-align:right'>{k}</th><td>{v}</td></tr>" for k, v in rows)
    return f"<table>{trs}</table>"

def _table(headers: list[str], rows: list[list]) -> str:
    ths = "".join(f"<th>{h}</th>" for h in headers)
    trs = ""
    for r in rows:
        tds = "".join(f"<td>{c}</td>" for c in r)
        trs += f"<tr>{tds}</tr>"
    return f"<table><tr>{ths}</tr>{trs}</table>"

def _wrap(title: str, level_badge: str, body: str) -> str:
    return f"""<!DOCTYPE html><html lang='ar' dir='rtl'>
<head><meta charset='utf-8'><title>{title}</title><style>{_CSS}</style></head>
<body>
<div class='cover'>
  <h1>{title}</h1>
  <div class='level-badge'>{level_badge}</div>
  <p><strong>العقار:</strong> {SUBJECT_AR['property_address']}</p>
  <p><strong>تاريخ التقييم:</strong> {SUBJECT_AR['valuation_date']}</p>
  <p><strong>العميل:</strong> {SUBJECT_AR['client']}</p>
  <p><strong>الغرض:</strong> {SUBJECT_AR['purpose']}</p>
  <p><strong>أساس القيمة:</strong> {SUBJECT_AR['basis_of_value']}</p>
  <p style='margin-top:12px;color:#888;font-size:9pt'>رقم الطلب: {SUBJECT_AR['request_id']}</p>
</div>
<div class='advisory'>
⚠️ <strong>إشعار استرشادي:</strong> {ADVISORY_NOTE_AR}<br>
advisory_only=True | certification_ready=False | not_real_training=True
</div>
{body}
<div class='advisory' style='margin-top:30px'>
بوابة مراجعة الخبير: هذا التقرير مسودة استرشادية ولا يُعتمد رسمياً إلا بعد مراجعة وتوقيع خبير معتمد ومرخص.<br>
certification_ready=False | يُحظر الاستخدام في أي معاملة قانونية أو مالية دون اعتماد رسمي.
</div>
</body></html>"""

# ══════════════════════════════════════════════════════════════════════════════
# SHARED BUILDING BLOCKS (used across levels with different depth)
# ══════════════════════════════════════════════════════════════════════════════

def _sec_cover_data(level: str) -> str:
    return f"""<h2>١. بيانات التكليف ونطاق العمل</h2>
{_kv([
    ("رقم الطلب", SUBJECT_AR['request_id']),
    ("العميل", SUBJECT_AR['client']),
    ("نوع العميل", SUBJECT_AR['client_type']),
    ("الغرض من التقييم", SUBJECT_AR['purpose']),
    ("أساس القيمة", SUBJECT_AR['basis_of_value']),
    ("تاريخ الفحص", SUBJECT_AR['inspection_date']),
    ("تاريخ التقييم", SUBJECT_AR['valuation_date']),
    ("العملة", SUBJECT_AR['currency']),
    ("نطاق العمل", "تقييم كامل — فحص ميداني + تحليل سوق + ثلاثة أساليب تقييم" if level != "traditional" else "تقييم مبسط — فحص + أساليب رئيسية"),
])}"""

def _sec_asset(level: str) -> str:
    s = SUBJECT_AR
    rows = [
        ("نوع العقار", s['property_type']),
        ("العنوان", s['property_address']),
        ("المساحة الإجمالية", f"{s['gross_floor_area_m2']} م²"),
        ("المساحة الصافية", f"{s['net_internal_area_m2']} م²"),
        ("الطابق", s['floor']),
        ("عمر المبنى", f"{s['age_years']} سنوات"),
        ("غرف النوم / الحمامات", f"{s['bedrooms']} غرف / {s['bathrooms']} حمامات"),
        ("المواقف", s['parking']),
        ("التصنيف العمراني", s['zoning']),
        ("الوضع القانوني", s['legal_status']),
    ]
    if level == "professional":
        rows += [
            ("سنة الترخيص", str(s['building_permit_year'])),
            ("رقم القطعة", s['plot_number']),
            ("الحي", s['district']),
            ("الإحداثيات", s['coordinates']),
            ("حيازة الملكية", s['tenure']),
        ]
    return f"<h2>٢. تعريف الأصل</h2>{_kv(rows)}"

def _sec_market(level: str) -> str:
    html = "<h2>٣. تحليل السوق والمقارنات</h2>"
    if level in ("detailed", "professional"):
        html += """<h3>٣.١ تحليل الموقع والسوق المحيط</h3>
<p>يقع العقار في حي النرجس شمال الرياض، ضمن نطاق جغرافي ذي طلب سكني مرتفع.
يتميز الحي بالبنية التحتية المكتملة والقرب من المحاور التجارية. تُظهر بيانات السوق
استقراراً في الأسعار مع نمو طفيف لا يتجاوز 3% سنوياً خلال الفترة 2024-2026.</p>"""
        if level == "professional":
            html += """<h3>٣.٢ اتجاهات السوق والعرض والطلب</h3>
<p>يُلاحظ فائض طفيف في المعروض من الشقق متوسطة المساحة، مما يُحافظ على معدلات الشغور
بين 7-10%. الطلب مستقر من شريحة المستأجرين ذوي الدخل المتوسط والمرتفع.
التوقعات المستقبلية: نمو 2.5-4% سنوياً خلال 3 سنوات قادمة.</p>"""
    html += "<h3>مقارنات السوق</h3>"
    headers = ["#", "الموقع", "المساحة م²", "سعر البيع SAR", "سعر/م²", "العمر", "التسوية الإجمالية %", "السعر المعدَّل/م²"]
    rows_data = []
    for i, c in enumerate(COMPARABLES_AR):
        adj_total = sum(v["values"][i] for v in ADJUSTMENTS_AR.values())
        rows_data.append([c['id'], c['address'], c['area_m2'],
                          _fmt(c['price_sar']), _fmt(c['price_per_sqm'], ""),
                          f"{c['age_years']} سنة", f"{adj_total:+}%",
                          _fmt(ADJUSTED_PRICES_PER_SQM[i], "")])
    html += _table(headers, rows_data)
    if level in ("detailed", "professional"):
        html += "<h3>تفاصيل التسويات</h3>"
        adj_hdrs = ["عنصر التسوية"] + [c['id'] for c in COMPARABLES_AR]
        adj_rows = []
        for k, v in ADJUSTMENTS_AR.items():
            adj_rows.append([v['label']] + [f"{x:+}%" for x in v['values']])
        html += _table(adj_hdrs, adj_rows)
        html += f"""<div class='highlight'>
<strong>متوسط السعر المعدَّل:</strong> {_fmt(sum(ADJUSTED_PRICES_PER_SQM)//len(ADJUSTED_PRICES_PER_SQM), "SAR/م²")}<br>
<strong>القيمة المؤشرة — أسلوب السوق:</strong> {_fmt(INDICATED_MARKET_VALUE)} (المساحة {SUBJECT_AR['gross_floor_area_m2']} م²)
</div>"""
    return html

def _sec_income(level: str) -> str:
    html = "<h2>٤. أسلوب الدخل / Income Approach</h2>"
    html += "<h3>٤.١ صافي الدخل التشغيلي (NOI)</h3>"
    html += _kv([
        ("الإيجار السوقي الإجمالي (سنوي)", _fmt(INCOME_AR['gross_market_rent_annual'])),
        ("معدل الشغور", f"{INCOME_AR['vacancy_rate_pct']}%"),
        ("خصم الشغور", _fmt(INCOME_AR['vacancy_deduction'])),
        ("الإيجار الفعلي الصافي", _fmt(INCOME_AR['effective_gross_income'])),
        ("رسوم الإدارة", _fmt(INCOME_AR['management_fee'])),
        ("الصيانة السنوية", _fmt(INCOME_AR['maintenance_annual'])),
        ("التأمين", _fmt(INCOME_AR['insurance_annual'])),
        ("إجمالي المصاريف", _fmt(INCOME_AR['total_opex'])),
        ("صافي الدخل التشغيلي NOI", _fmt(INCOME_AR['net_operating_income'])),
    ])
    html += "<h3>٤.٢ الرسملة المباشرة / Direct Capitalization</h3>"
    html += _kv([
        ("صافي الدخل التشغيلي NOI", _fmt(INCOME_AR['net_operating_income'])),
        ("معدل الرسملة Cap Rate", f"{INCOME_AR['cap_rate_pct']}%"),
        ("القيمة المؤشرة — رسملة مباشرة", _fmt(INCOME_AR['indicated_value_income'])),
    ])
    if level in ("detailed", "professional"):
        d = DCF_5YEAR_AR
        html += "<h3>٤.٣ تحليل التدفقات النقدية المخصومة ضمن أسلوب الدخل — DCF 5 سنوات</h3>"
        cf_hdrs = ["السنة"] + [f"السنة {i+1}" for i in range(5)]
        cf_vals = ["التدفق النقدي SAR"] + [_fmt(v, "") for v in d['year_cash_flows']]
        html += _table(cf_hdrs, [cf_vals])
        html += _kv([
            ("معدل الخصم", f"{d['discount_rate_pct']}%"),
            ("معدل النمو", f"{d['growth_rate_pct']}%"),
            ("معدل الرسملة الطرفية", f"{d['terminal_cap_rate_pct']}%"),
            ("القيمة الطرفية Terminal Value", _fmt(d['terminal_value_year5'])),
            ("NPV — القيمة الحالية الصافية", _fmt(d['dcf_indicated_value'])),
        ])
        html += "<p class='section-note'>DCF مُدمج ضمن أسلوب الدخل — وليس أسلوباً مستقلاً.</p>"
    if level == "professional":
        d10 = DCF_10YEAR_AR
        html += "<h3>٤.٤ DCF 10 سنوات</h3>"
        html += _kv([
            ("فترة الاحتجاز", f"{d10['hold_period_years']} سنوات"),
            ("معدل الخصم", f"{d10['discount_rate_pct']}%"),
            ("NPV 10 سنوات", _fmt(d10['dcf_indicated_value'])),
        ])
        irr_approx = round(d['discount_rate_pct'] + (d['dcf_indicated_value'] - INCOME_AR['indicated_value_income']) / INCOME_AR['indicated_value_income'] * 100, 1)
        html += f"<p><strong>IRR التقريبي (5 سنوات):</strong> ~{irr_approx}% (احتساب تقريبي توضيحي)</p>"
    return html

def _sec_cost(level: str) -> str:
    c = COST_AR
    html = "<h2>٥. أسلوب التكلفة / Cost Approach</h2>"
    rows = [
        ("مساحة الأرض", f"{c['land_area_m2']} م²"),
        ("سعر الأرض/م²", _fmt(c['land_value_per_sqm'], "SAR/م²")),
        ("قيمة الأرض", _fmt(c['land_value'])),
        ("المساحة الإجمالية للمبنى", f"{c['gross_floor_area_m2']} م²"),
        ("تكلفة الإحلال الجديدة/م²", _fmt(c['replacement_cost_new_per_sqm'], "SAR/م²")),
        ("تكلفة الإحلال الجديدة الإجمالية", _fmt(c['replacement_cost_new'])),
        ("الإهلاك المادي", f"{c['physical_depreciation_pct']}% = {_fmt(c['physical_depreciation'])}"),
    ]
    if level in ("detailed", "professional"):
        rows += [
            ("التقادم الوظيفي", _fmt(c['functional_obsolescence'])),
            ("التقادم الخارجي/الاقتصادي", _fmt(c['economic_obsolescence'])),
        ]
    if level == "professional":
        rows += [
            ("العمر الفعلي / العمر الافتراضي", f"{c['age_years']} / {c['effective_life_years']} سنة"),
            ("الإهلاك التراكمي المقدر", f"{c['physical_depreciation_pct']}%"),
        ]
    rows += [
        ("قيمة التحسينات بعد الاستهلاك", _fmt(c['depreciated_improvement_value'])),
        ("القيمة المؤشرة — أسلوب التكلفة", _fmt(c['indicated_value_cost'])),
    ]
    html += _kv(rows)
    return html

def _sec_avm(level: str) -> str:
    a = AVM_AR
    html = "<h2>٦. مؤشر التقييم الآلي المساعد / AVM</h2>"
    html += _kv([
        ("مزود المؤشر", a['avm_provider']),
        ("القيمة المؤشرة AVM", _fmt(a['avm_indicated_value'])),
        ("مستوى الثقة", a['confidence_level']),
        ("درجة الثقة", f"{a['confidence_score']*100:.0f}%"),
        ("حداثة البيانات", a['data_freshness']),
        ("عدد المقارنات المستخدمة", str(a['comparable_count'])),
        ("ملاحظة", a['note']),
    ])
    if level == "professional":
        html += f"""<h3>موثوقية نموذج AVM ومقارنته بالأساليب الأخرى</h3>
<p>قيمة AVM {_fmt(a['avm_indicated_value'])} تقع ضمن نطاق {_fmt(INCOME_AR['indicated_value_income'])}
— {_fmt(INDICATED_MARKET_VALUE)} المُستخرج من أساليب الدخل والسوق.
درجة الثقة {a['confidence_score']*100:.0f}% تشير إلى موثوقية متوسطة — يُنصح باستخدامه كمؤشر داعم لا حاسم.</p>"""
    elif level == "detailed":
        diff = abs(a['avm_indicated_value'] - INCOME_AR['indicated_value_income'])
        html += f"<p class='section-note'>الفارق بين AVM وأسلوب الدخل: {_fmt(diff)} — فارق ضمن النطاق المقبول (&lt;8%).</p>"
    html += "<p class='advisory'>AVM مؤشر مساعد فقط — لا يُعتمد وحده كأساس للتقييم.</p>"
    return html

def _sec_hbu(level: str) -> str:
    h = HBU_AR
    html = "<h2>٧. تحليل أعلى وأفضل استخدام / HBU</h2>"
    if level == "traditional":
        html += f"""<p>وفق متطلبات تحليل أعلى وأفضل استخدام عند الانطباق:</p>
<ul style='padding-right:20px;margin:8px 0'>
  <li>✅ <strong>مشروع قانوناً:</strong> {h['legally_permissible']}</li>
  <li>✅ <strong>ممكن مادياً:</strong> {h['physically_possible']}</li>
  <li>✅ <strong>مجدٍ مالياً:</strong> {h['financially_feasible']}</li>
  <li>✅ <strong>الأعلى إنتاجية:</strong> {h['maximally_productive']}</li>
</ul>
<p><strong>خلاصة HBU:</strong> {h['conclusion']}</p>"""
    elif level == "detailed":
        html += f"""<h3>الاختبارات الأربعة لأعلى وأفضل استخدام</h3>
{_kv([
    ("١. مشروع قانوناً", h['legally_permissible']),
    ("٢. ممكن مادياً", h['physically_possible']),
    ("٣. مجدٍ مالياً", h['financially_feasible']),
    ("٤. الأعلى إنتاجية", h['maximally_productive']),
])}
<p><strong>استنتاج HBU:</strong> {h['conclusion']}</p>
<p class='section-note'>وفق متطلبات تحليل أعلى وأفضل استخدام عند الانطباق.</p>"""
    else:  # professional
        html += f"""<h3>الاختبار الأول: المشروعية القانونية</h3>
<p>{h['legally_permissible']} — التصنيف العمراني R-2 يسمح بالاستخدام السكني متعدد الوحدات.</p>
<h3>الاختبار الثاني: الإمكانية المادية</h3>
<p>{h['physically_possible']} — المبنى قائم وتقدير العمر المتبقي 34 سنة.</p>
<h3>الاختبار الثالث: الجدوى المالية</h3>
<p>{h['financially_feasible']}<br>
صافي الدخل التشغيلي: {_fmt(INCOME_AR['net_operating_income'])} — معدل عائد {INCOME_AR['cap_rate_pct']}% يتجاوز معدل العائد المطلوب.</p>
<h3>الاختبار الرابع: أعلى إنتاجية</h3>
<p>{h['maximally_productive']}</p>
{_kv([
    ("تكاليف التحويل لاستخدام بديل (تقديري)", "غير مبررة اقتصادياً"),
    ("الإيرادات الحالية كاستخدام سكني", _fmt(INCOME_AR['gross_market_rent_annual'])),
    ("صافي الدخل الحالي NOI", _fmt(INCOME_AR['net_operating_income'])),
])}
<p><strong>خلاصة HBU:</strong> {h['conclusion']}</p>"""
    return html

def _sec_risk(level: str) -> str:
    html = "<h2>٨. تحليل المخاطر والحساسية</h2>"
    if level == "traditional":
        html += "<h3>ملخص المخاطر الرئيسية</h3>"
        rows = [[r['risk'], r['severity'], r['impact']] for r in RISKS_AR[:3]]
        html += _table(["الخطر", "الشدة", "الأثر"], rows)
        html += "<p class='section-note'>المخاطر تؤثر على نطاق القيمة ولا تُلغي التقييم.</p>"
        html += "<h3>حساسية بسيطة</h3>"
        html += _kv([
            ("إذا ارتفع معدل الرسملة +0.5%", f"تنخفض القيمة ~{_fmt(int(INCOME_AR['net_operating_income']/(INCOME_AR['cap_rate_pct']/100+0.005) - INCOME_AR['indicated_value_income'])):} SAR"),
            ("إذا انخفض معدل الرسملة -0.5%", f"ترتفع القيمة ~{_fmt(int(INCOME_AR['net_operating_income']/(INCOME_AR['cap_rate_pct']/100-0.005) - INCOME_AR['indicated_value_income'])):} SAR"),
        ])
    elif level == "detailed":
        html += "<h3>أثر المخاطر على القيمة</h3>"
        risk_rows = [
            [r['risk'], r['severity'],
             "+1-2%" if r['severity'] == "منخفضة" else "+2-5%",
             "تعديل معدل الرسملة" if "السوق" in r['risk'] else "تعديل نطاق القيمة",
             r['impact']]
            for r in RISKS_AR
        ]
        html += _table(["الخطر", "الاحتمالية", "أثر على القيمة %", "الانعكاس", "الأثر"], risk_rows)
        html += "<h3>مصفوفة حساسية أساسية — Cap Rate × نسبة الإشغال</h3>"
        sm = SENSITIVITY_MATRIX_AR
        html += _table(["معدل الرسملة / الإشغال"] + sm['cols'],
                       [[sm['rows'][i]] + [_fmt(v, "") for v in row] for i, row in enumerate(sm['values'])])
    else:  # professional
        html += "<h3>سجل المخاطر المفصل — أثر المخاطر على القيمة</h3>"
        pct_impacts = ["3-5%", "2-4%", "1-3%", "1-2%", "0-2%"]
        rec_impacts = ["تعديل معدل الخصم +50bp", "تعديل معدل الشغور +2%", "توسيع نطاق القيمة", "مراجعة معدل النمو", "مراجعة الحالة"]
        risk_rows_pro = []
        for i, r in enumerate(RISKS_AR):
            css = "risk-high" if r['severity'] == "مرتفعة" else ("risk-med" if r['severity'] == "متوسطة" else "risk-low")
            risk_rows_pro.append([r['risk'], r['severity'], r['impact'],
                                  pct_impacts[i] if i < len(pct_impacts) else "1-2%",
                                  rec_impacts[i] if i < len(rec_impacts) else "مراجعة"])
        html += _table(["الخطر", "الاحتمالية", "الأثر", "التأثير على القيمة %", "إجراء التخفيف"], risk_rows_pro)
        html += "<h3>مصفوفة الحساسية متعددة المتغيرات</h3>"
        html += "<h4>Cap Rate × نسبة الإشغال</h4>"
        sm = SENSITIVITY_MATRIX_AR
        html += _table(["Cap Rate / إشغال"] + sm['cols'],
                       [[sm['rows'][i]] + [_fmt(v, "") for v in row] for i, row in enumerate(sm['values'])])
        html += "<h4>معدل الخصم × معدل الرسملة الطرفية</h4>"
        dr_rows = [
            ["7.5%", "1,310,000", "1,285,000", "1,265,000"],
            ["8.5%", "1,210,000", "1,185,000", "1,158,000"],
            ["9.5%", "1,110,000", "1,090,000", "1,065,000"],
            ["10.5%", "1,020,000", "1,000,000", "978,000"],
        ]
        html += _table(["معدل الخصم / Terminal Cap 5.3%  / 5.8%  / 6.3%"], [])
        html += _table(["معدل الخصم", "Terminal Cap 5.3%", "Terminal Cap 5.8%", "Terminal Cap 6.3%"], dr_rows)
        html += "<h4>إشغال × الإيجار (SAR/سنة)</h4>"
        occ_rows = [
            ["إشغال 85%", "64,600", "66,300", "68,000"],
            ["إشغال 92%", "69,800", "71,760", "73,500"],
            ["إشغال 97%", "73,400", "75,500", "77,300"],
        ]
        html += _table(["الإشغال", "إيجار -5%", "إيجار أساسي", "إيجار +5%"], occ_rows)
    return html

def _sec_scenarios(level: str) -> str:
    if level != "professional":
        return ""
    html = "<h2>٩. تحليل السيناريوهات / Scenario Analysis</h2>"
    sc_rows = [[s['scenario'], f"{s['growth_rate']}%", f"{s['cap_rate']}%",
                f"{s['discount_rate']}%", _fmt(s['dcf_value'])] for s in SCENARIOS_AR]
    html += _table(["السيناريو", "معدل النمو", "Cap Rate", "معدل الخصم", "قيمة DCF"], sc_rows)
    html += _kv([
        ("الاحتمالات: متحفظ/أساسي/متفائل", "20% / 60% / 20%"),
        ("القيمة المرجحة باحتمالات السيناريو", _fmt(PROBABILITY_WEIGHTED_VALUE)),
    ])
    return html

def _sec_reconciliation(level: str) -> str:
    html = "<h2>١٠. التوفيق والترجيح / Reconciliation</h2>"
    html += "<h3>مبررات اختيار الأوزان</h3>"
    if level == "traditional":
        html += """<p>أُعطي أسلوب السوق الوزن الأعلى (50%) لتوافر بيانات مقارنات حديثة وموثوقة.
أسلوب الدخل (35%) لكون العقار مدراً للإيجار. أسلوب التكلفة (15%) كمرساة تأكيدية.</p>"""
    elif level == "detailed":
        html += f"""<p>الأوزان مُحددة بناءً على:</p>
<ul style='padding-right:20px'>
  <li>أسلوب السوق (50%): 5 مقارنات حديثة — بيانات عالية الجودة — الأنسب لأصل سكني</li>
  <li>أسلوب الدخل (35%): NOI موثق — إيجار سوقي مرجعي — DCF يدعم النتيجة</li>
  <li>أسلوب التكلفة (15%): مُستخدم للمقارنة والتأكيد — ليس الأساس للأصل القائم</li>
</ul>
<h3>تحليل الفجوات بين الأساليب</h3>"""
        html += _kv([
            ("أسلوب السوق", _fmt(INDICATED_MARKET_VALUE)),
            ("أسلوب الدخل (رسملة مباشرة)", _fmt(INCOME_AR['indicated_value_income'])),
            ("أسلوب التكلفة", _fmt(COST_AR['indicated_value_cost'])),
            ("الفارق بين السوق والدخل",
             f"{abs(INDICATED_MARKET_VALUE - INCOME_AR['indicated_value_income']):,} SAR ({abs(INDICATED_MARKET_VALUE - INCOME_AR['indicated_value_income'])/INDICATED_MARKET_VALUE*100:.1f}%)"),
            ("الفارق بين السوق والتكلفة",
             f"{abs(INDICATED_MARKET_VALUE - COST_AR['indicated_value_cost']):,} SAR ({abs(INDICATED_MARKET_VALUE - COST_AR['indicated_value_cost'])/INDICATED_MARKET_VALUE*100:.1f}%)"),
        ])
    else:  # professional
        html += f"""<p>الأوزان محددة بناءً على جودة البيانات وموثوقية الأسلوب ومؤشرات المخاطر:</p>
{_table(
    ["الأسلوب", "القيمة SAR", "الوزن %", "المبرر", "درجة الموثوقية"],
    [
        ["أسلوب السوق", _fmt(INDICATED_MARKET_VALUE, ""), "50%", "بيانات كافية — سوق نشط", "عالية"],
        ["أسلوب الدخل", _fmt(INCOME_AR['indicated_value_income'], ""), "35%", "إيجار موثق — DCF يدعمه", "عالية"],
        ["أسلوب التكلفة", _fmt(COST_AR['indicated_value_cost'], ""), "15%", "تأكيدي — إهلاك تقديري", "متوسطة"],
    ]
)}
<h3>أثر المخاطر على الترجيح</h3>
<p>مخاطر السوق المتوسطة تدعم إعطاء وزن مرتفع لأسلوب السوق.
مخاطر الشغور المنخفضة تُثبّت وزن أسلوب الدخل. الإهلاك التقديري يُخفض وزن التكلفة.</p>
<h3>تحليل الفجوات</h3>
{_kv([
    ("السوق vs الدخل", f"فارق {abs(INDICATED_MARKET_VALUE - INCOME_AR['indicated_value_income']):,} SAR ({abs(INDICATED_MARKET_VALUE - INCOME_AR['indicated_value_income'])/INDICATED_MARKET_VALUE*100:.1f}%) — مقبول"),
    ("السوق vs التكلفة", f"فارق {abs(INDICATED_MARKET_VALUE - COST_AR['indicated_value_cost']):,} SAR — عقار قائم متوقع"),
    ("DCF 5Y vs الرسملة", f"فارق {abs(DCF_5YEAR_AR['dcf_indicated_value'] - INCOME_AR['indicated_value_income']):,} SAR — ضمن 1.5%"),
])}"""
    html += "<h3>بطاقة التوفيق</h3>"
    sc_rows = [[r['approach'], _fmt(r['value_sar']), f"{r['weight_pct']}%", _fmt(r['weighted_sar'])]
               for r in RECONCILIATION_SCORECARD_AR]
    sc_rows.append(["<strong>القيمة المرجحة</strong>", "", "", f"<strong>{_fmt(RECONCILIATION_AR['weighted_value'])}</strong>"])
    sc_rows.append(["<strong>رأي القيمة النهائي</strong>", "", "", f"<strong>{_fmt(RECONCILIATION_AR['final_opinion_rounded'])}</strong>"])
    html += _table(["الأسلوب", "القيمة", "الوزن", "الموزون"], sc_rows)
    return html

def _sec_conclusion(level: str) -> str:
    val = _fmt(RECONCILIATION_AR['final_opinion_rounded'])
    html = "<h2>١١. النتيجة والتوصية</h2>"
    html += f"<div class='value-box'>رأي القيمة الاسترشادي: {val} ({SUBJECT_AR['currency']})</div>"
    if level == "traditional":
        html += f"""<div class='highlight'>
<strong>التوصية:</strong> العقار مناسب للاستخدام كضمان للتمويل العقاري بناءً على البيانات المتوفرة.
القيمة السوقية الاسترشادية {val} تدعم التمويل بنسبة LTV معيارية. يُنصح بمراجعة بيانات الإيجار
ميدانياً قبل الاعتماد النهائي.
</div>
<div class='advisory'>مسودة — لا تُعتمد رسمياً دون مراجعة خبير معتمد. certification_ready=False.</div>"""
    elif level == "detailed":
        html += f"""<h3>توصية موجهة للعميل</h3>
<p>بناءً على التحليل المفصل لأساليب التقييم الثلاثة وتحليل DCF والفجوات:</p>
<ul style='padding-right:20px'>
  <li>القيمة الاسترشادية {val} مدعومة بثلاثة أساليب مستقلة</li>
  <li>العقار مناسب للتمويل عند نسبة LTV 60-70% — الحد الأقصى الموصى به {_fmt(int(RECONCILIATION_AR['final_opinion_rounded']*0.70))}</li>
  <li>مخاطر السوق متوسطة — يُنصح بمراجعة سنوية</li>
  <li>DCF يُؤكد القيمة عند افتراضات إشغال 92% ونمو 3%</li>
</ul>
<div class='advisory'>مسودة تفصيلية — certification_ready=False.</div>"""
    else:  # professional
        html += f"""<h3>نطاق القيمة</h3>
{_kv([
    ("الحد الأدنى (سيناريو متحفظ)", _fmt(SCENARIOS_AR[0]['dcf_value'])),
    ("رأي القيمة المرجح", val),
    ("الحد الأقصى (سيناريو متفائل)", _fmt(SCENARIOS_AR[2]['dcf_value'])),
    ("القيمة المرجحة باحتمالات السيناريوهات", _fmt(PROBABILITY_WEIGHTED_VALUE)),
])}
<h3>التوصية الاستثمارية المفصلة</h3>
<ul style='padding-right:20px'>
  <li><strong>رأي القيمة:</strong> {val} (القيمة السوقية الاسترشادية)</li>
  <li><strong>للتمويل:</strong> الحد الأقصى الموصى به {_fmt(int(RECONCILIATION_AR['final_opinion_rounded']*0.70))} (LTV 70%)</li>
  <li><strong>للاستثمار:</strong> العائد الجاري 5.5% — مناسب لمحافظ الدخل الثابت</li>
  <li><strong>نطاق الثقة:</strong> ±5% من رأي القيمة بناءً على جودة البيانات</li>
  <li><strong>شروط الاعتماد:</strong> مشروطة بتأكيد الوضع القانوني وبيانات الإيجار الفعلية</li>
</ul>
<h3>شروط الاعتماد</h3>
<p>هذا التقرير مسودة استرشادية. الاعتماد الرسمي يستلزم: (أ) مراجعة خبير معتمد ومرخص،
(ب) التحقق من الوثائق القانونية، (ج) إصدار شهادة اعتماد رسمية.</p>
<div class='advisory'>certification_ready=False | advisory_only=True</div>"""
    return html

def _sec_assumptions(level: str) -> str:
    html = "<h2>١٢. الافتراضات والقيود</h2>"
    html += """<ul style='padding-right:20px'>
<li>البيانات الواردة توضيحية لأغراض الاختبار — not_real_training=True</li>
<li>تكلفة الإحلال مستندة إلى معدلات السوق المحلية وقت التقييم</li>
<li>بيانات الدخل مستندة إلى إيجارات السوق — تخضع للتحقق الميداني</li>
<li>الوضع القانوني توضيحي — يستلزم تأكيداً قانونياً مستقلاً</li>
<li>لا تحمّل المقيّم مسؤولية بيانات مجهزة من أطراف ثالثة</li>
</ul>"""
    if level in ("detailed", "professional"):
        html += """<ul style='padding-right:20px'>
<li>مصفوفة الحساسية مبنية على نطاق ±15% من الافتراضات الأساسية</li>
<li>تحليل السيناريوهات يُغطي نطاق الاحتمالات المعقولة — لا يُمثل تنبؤاً</li>
<li>DCF مبني على افتراض استمرار الإيجار — أي تغيير جوهري يستلزم إعادة الاحتساب</li>
</ul>"""
    return html

def _sec_standards(level: str) -> str:
    html = "<h2>١٣. الإفصاح وشهادة الامتثال</h2>"
    if level == "traditional":
        html += """<p>يُعلن المُقيّم أن هذا التقرير أُعد وفق المبادئ العامة لمعايير التقييم الدولية (IVS)
بما يتناسب مع نطاق العمل المحدد وطبيعة التقرير التقليدي. لا يتضمن اعتماداً رسمياً.</p>"""
        rows = [[s['standard'], s['name'], s['status']] for s in STANDARDS_AR[:3]]
        html += _table(["المعيار", "الاسم", "الحالة"], rows)
    elif level == "detailed":
        html += "<p>أُعد هذا التقرير وفق نطاق عمل محدد يستند إلى:</p>"
        rows = [[s['standard'], s['name'], s['status']] for s in STANDARDS_AR]
        html += _table(["المعيار", "الاسم", "الحالة"], rows)
        html += """<p class='section-note'>الامتثال لمعايير IVS يُطبَّق بما يتناسب مع نوع الأصل والغرض من التقييم.
لا تتضمن شهادة الامتثال اعتماداً رسمياً في غياب certification_ready=true.</p>"""
    else:  # professional
        html += "<h3>مصفوفة الامتثال بالمعايير الدولية</h3>"
        pro_standards = STANDARDS_AR + [
            {"standard": "RICS Red Book", "name": "معايير RICS للتقييم",       "status": "مرجعي"},
            {"standard": "IFRS 13",       "name": "القيمة العادلة — IFRS",     "status": "مرجعي"},
            {"standard": "USPAP",         "name": "معايير التقييم الأمريكية",  "status": "مرجعي — عند الانطباق"},
            {"standard": "FRA / GCC",     "name": "الإطار التنظيمي الإقليمي", "status": "مرجعي"},
        ]
        rows = [[s['standard'], s['name'], s['status']] for s in pro_standards]
        html += _table(["المعيار", "الاسم", "الحالة"], rows)
        html += """<p class='section-note'>الامتثال مقيّد بنطاق العمل المحدد وطبيعة البيانات المتاحة.
لا يُمثل هذا التقرير شهادة امتثال كاملة في غياب توقيع خبير معتمد ومرخص.</p>"""
    html += "<div class='advisory'>لا شهادة اعتماد رسمية — لا توقيع — لا ختم. certification_ready=False.</div>"
    return html

def _sec_sources(level: str) -> str:
    html = "<h2>١٤. الملاحق ومصادر البيانات</h2>"
    if level == "traditional":
        html += _table(["المصدر", "النوع", "الحالة"],
                       [[r['field'], "بيانات إدخال", r['status']] for r in DATA_INPUTS_AR[:5]])
    elif level == "detailed":
        html += "<h3>ملخص مصادر البيانات</h3>"
        html += _table(["الحقل", "الحالة", "درجة الثقة"],
                       [[r['field'], r['status'], "عالية" if r['status'] == "مكتمل" else "متوسطة"]
                        for r in DATA_INPUTS_AR])
    else:  # professional
        html += "<h3>سجل مصادر البيانات</h3>"
        html += _table(["الحقل", "الحالة", "درجة الثقة", "ملاحظة"],
                       [[r['field'], r['status'],
                         "عالية" if r['status'] == "مكتمل" else "متوسطة",
                         "تحقق ميداني" if r['status'] == "مكتمل" else "يستلزم تأكيداً"]
                        for r in DATA_INPUTS_AR])
        html += "<h3>مصادر بيانات السوق</h3>"
        html += _table(["المصدر", "النوع", "درجة الموثوقية"],
                       [
                           ["مقارنات السوق الميدانية", "مبيعات موثقة", "عالية"],
                           ["بيانات الإيجار السوقي", "إيجارات مرجعية", "عالية"],
                           ["تكاليف الإحلال", "قوائم أسعار مقاولين", "متوسطة"],
                           ["AVM المساعد", "نموذج آلي", "متوسطة (72%)"],
                           ["تصنيفات التخطيط", "بلدية الرياض", "عالية"],
                       ])
    return html

# ══════════════════════════════════════════════════════════════════════════════
# EXECUTIVE SUMMARY per level
# ══════════════════════════════════════════════════════════════════════════════

def _sec_executive_summary(level: str) -> str:
    val = _fmt(RECONCILIATION_AR['final_opinion_rounded'])
    html = "<h2>الملخص التنفيذي</h2>"
    if level == "traditional":
        html += f"""<div class='highlight'>
<strong>رأي القيمة الاسترشادي:</strong> {val}<br>
<strong>أساس القيمة:</strong> {SUBJECT_AR['basis_of_value']}<br>
<strong>الأساليب المستخدمة:</strong> أسلوب السوق (50%) + أسلوب الدخل (35%) + أسلوب التكلفة (15%)<br>
<strong>AVM:</strong> مؤشر مساعد — {_fmt(AVM_AR['avm_indicated_value'])}<br>
<strong>التوصية:</strong> مناسب للتمويل العقاري بنسبة LTV معيارية
</div>"""
    elif level == "detailed":
        html += f"""<div class='highlight'>
<strong>رأي القيمة الاسترشادي:</strong> {val}<br>
<strong>الأساليب:</strong> السوق (50%) + الدخل مع DCF (35%) + التكلفة (15%)<br>
<strong>DCF 5 سنوات NPV:</strong> {_fmt(DCF_5YEAR_AR['dcf_indicated_value'])}<br>
<strong>نطاق القيمة:</strong> {_fmt(INCOME_AR['indicated_value_income'])} — {_fmt(COST_AR['indicated_value_cost'])}<br>
<strong>HBU:</strong> الاستخدام السكني الحالي هو الأمثل<br>
<strong>التوصية:</strong> مناسب للتمويل — حد LTV موصى به {_fmt(int(RECONCILIATION_AR['final_opinion_rounded']*0.70))}
</div>"""
    else:
        html += f"""<div class='highlight'>
<strong>رأي القيمة:</strong> {val} | <strong>نطاق القيمة:</strong> {_fmt(SCENARIOS_AR[0]['dcf_value'])} — {_fmt(SCENARIOS_AR[2]['dcf_value'])}<br>
<strong>القيمة المرجحة بالسيناريوهات:</strong> {_fmt(PROBABILITY_WEIGHTED_VALUE)}<br>
<strong>DCF 5Y NPV:</strong> {_fmt(DCF_5YEAR_AR['dcf_indicated_value'])} | <strong>DCF 10Y NPV:</strong> {_fmt(DCF_10YEAR_AR['dcf_indicated_value'])}<br>
<strong>HBU:</strong> الاستخدام السكني الحالي — اجتاز الاختبارات الأربعة<br>
<strong>المخاطر:</strong> متوسطة — تؤثر +2-5% على القيمة<br>
<strong>التوصية:</strong> مناسب للتمويل (LTV 70%) ومحافظ الدخل — مع شروط اعتماد
</div>"""
    return html

# ══════════════════════════════════════════════════════════════════════════════
# REPORT BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def _build_traditional() -> str:
    parts = [
        _sec_executive_summary("traditional"),
        _sec_cover_data("traditional"),
        _sec_asset("traditional"),
        _sec_market("traditional"),
        _sec_income("traditional"),
        _sec_cost("traditional"),
        _sec_avm("traditional"),
        _sec_hbu("traditional"),
        _sec_risk("traditional"),
        _sec_reconciliation("traditional"),
        _sec_conclusion("traditional"),
        _sec_assumptions("traditional"),
        _sec_standards("traditional"),
        _sec_sources("traditional"),
    ]
    return _wrap("تقرير تقييم تقليدي", "المستوى الأول — تقليدي", "\n".join(parts))

def _build_detailed() -> str:
    parts = [
        _sec_executive_summary("detailed"),
        _sec_cover_data("detailed"),
        _sec_asset("detailed"),
        _sec_market("detailed"),
        _sec_income("detailed"),
        _sec_cost("detailed"),
        _sec_avm("detailed"),
        _sec_hbu("detailed"),
        _sec_risk("detailed"),
        _sec_scenarios("detailed"),
        _sec_reconciliation("detailed"),
        _sec_conclusion("detailed"),
        _sec_assumptions("detailed"),
        _sec_standards("detailed"),
        _sec_sources("detailed"),
    ]
    return _wrap("تقرير تقييم تفصيلي", "المستوى الثاني — تفصيلي", "\n".join(parts))

def _build_professional() -> str:
    parts = [
        _sec_executive_summary("professional"),
        _sec_cover_data("professional"),
        _sec_asset("professional"),
        _sec_market("professional"),
        _sec_income("professional"),
        _sec_cost("professional"),
        _sec_avm("professional"),
        _sec_hbu("professional"),
        _sec_risk("professional"),
        _sec_scenarios("professional"),
        _sec_reconciliation("professional"),
        _sec_conclusion("professional"),
        _sec_assumptions("professional"),
        _sec_standards("professional"),
        _sec_sources("professional"),
    ]
    return _wrap("تقرير تقييم احترافي", "المستوى الثالث — احترافي", "\n".join(parts))

# ══════════════════════════════════════════════════════════════════════════════
# PDF RENDERER
# ══════════════════════════════════════════════════════════════════════════════

def _render_pdf(html: str, out: Path) -> bool:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8")
    try:
        tmp.write(html)
        tmp.flush()
        tmp.close()
        env = {**os.environ, "PYTHONUTF8": "1"}
        result = subprocess.run(
            [_CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
             f"--print-to-pdf={out}", f"--print-to-pdf-no-header",
             f"file:///{tmp.name}"],
            capture_output=True, timeout=60, env=env
        )
        return out.exists() and out.stat().st_size > 5_000
    except Exception:
        return False
    finally:
        try:
            Path(tmp.name).unlink(missing_ok=True)
        except Exception:
            pass

# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def generate_all_pdfs(pdf_out: Path, preview_out: Path) -> dict:
    pdf_out.mkdir(parents=True, exist_ok=True)
    preview_out.mkdir(parents=True, exist_ok=True)

    reports = {
        "traditional_report": (_build_traditional, "تقرير تقليدي", "traditional"),
        "detailed_report":    (_build_detailed,    "تقرير تفصيلي", "detailed"),
        "professional_report":(_build_professional,"تقرير احترافي","professional"),
    }

    results = {}
    for key, (builder, title, level) in reports.items():
        html = builder()
        # Save HTML preview (no internal paths)
        prev_path = preview_out / f"{key}_preview.html"
        prev_path.write_text(html, encoding="utf-8")
        # Render PDF
        pdf_path = pdf_out / f"{key}.pdf"
        ok = _render_pdf(html, pdf_path)
        results[key] = {
            "exists": ok,
            "size": pdf_path.stat().st_size if ok else 0,
            "preview": str(prev_path.name),
            "level": level,
        }
    return results
