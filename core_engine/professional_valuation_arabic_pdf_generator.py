"""
professional_valuation_arabic_pdf_generator.py
يولد ثلاثة تقارير PDF عربية متمايزة:
  traditional_report.pdf  — تقرير تقليدي (16+ صفحة)
  detailed_report.pdf     — تقرير تفصيلي (25+ صفحة)
  professional_report.pdf — تقرير احترافي (35+ صفحة)

لغة التقرير: العربية (RTL)
pdf_language = ar | advisory_only=True | not_real_training=True
مصطلحات دولية يُسمح بها كتسميات ثانوية إلى جانب العربية.
"""
from __future__ import annotations

import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from professional_valuation_arabic_report_examples import (
    SUBJECT_AR, COMPARABLES_AR, ADJUSTMENTS_AR, ADJUSTED_PRICES_PER_SQM,
    INDICATED_MARKET_VALUE_PER_SQM, INDICATED_MARKET_VALUE,
    INCOME_AR, COST_AR, AVM_AR, RECONCILIATION_AR,
    DCF_5YEAR_AR, DCF_10YEAR_AR, SCENARIOS_AR, PROBABILITY_WEIGHTED_VALUE,
    SENSITIVITY_MATRIX_AR, RISKS_AR, STANDARDS_AR, DATA_INPUTS_AR,
    METHOD_SELECTION_AR, HBU_AR, RECONCILIATION_SCORECARD_AR,
    ADVISORY_NOTE_AR,
)

_CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
_GENERATED_AT = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

# ── CSS (RTL Arabic) ──────────────────────────────────────────────────────────
_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700;900&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Tajawal', 'Arial Unicode MS', 'Segoe UI', Arial, sans-serif;
  font-size: 10.5pt; color: #1a1a1a; line-height: 1.7;
  direction: rtl; text-align: right;
}
h1 { font-size: 20pt; color: #1a3a5c; text-align: center; margin-bottom: 10px; }
h2 { font-size: 13pt; color: #1a3a5c; border-bottom: 2px solid #1a3a5c;
     padding-bottom: 4px; margin: 22px 0 8px; }
h3 { font-size: 11pt; color: #2c5f8a; margin: 14px 0 5px; }
h4 { font-size: 10pt; color: #34609a; margin: 10px 0 4px; }
p  { margin: 6px 0; }
ul { margin: 5px 0 5px 0; padding-right: 20px; list-style-type: disc; }
li { margin: 3px 0; font-size: 10pt; }
table { width: 100%; border-collapse: collapse; margin: 9px 0; font-size: 9.5pt; direction: rtl; }
th { background: #1a3a5c; color: #fff; padding: 6px 10px; text-align: right; }
td { padding: 5px 10px; border: 1px solid #c8d4e0; vertical-align: top; text-align: right; }
tr:nth-child(even) td { background: #f0f5fa; }
.kv td:first-child { font-weight: bold; background: #e4edf5; width: 38%; }
.advisory {
  background: #fff8e1; border: 2px solid #e6a817;
  padding: 12px 16px; margin: 14px 0; border-radius: 6px; font-size: 9.5pt;
}
.advisory strong { color: #8a5700; font-size: 10.5pt; }
.cover {
  text-align: center; padding: 32px 24px; border: 3px solid #1a3a5c;
  margin-bottom: 22px; border-radius: 10px; background: #f5f9fd;
}
.cover .sub { font-size: 11.5pt; color: #444; margin: 6px 0 16px; }
.cover .badge {
  display: inline-block; background: #fff3cd; border: 1px solid #e6a817;
  color: #8a5700; padding: 4px 14px; border-radius: 14px;
  font-size: 9.5pt; font-weight: bold; margin: 8px 0 16px;
}
.val-box {
  background: #e4edf5; border-right: 5px solid #1a3a5c; padding: 10px 16px;
  margin: 10px 0; font-size: 12pt; font-weight: bold; color: #1a3a5c;
}
.note { font-size: 8.5pt; color: #666; font-style: italic; margin-top: 4px; }
.ok   { color: #1e7e34; font-weight: bold; }
.warn { color: #856404; font-weight: bold; }
.nok  { color: #721c24; font-weight: bold; }
.hl   { background: #fffde7; padding: 8px 13px; border-right: 4px solid #f9a825; margin: 8px 0; }
.section-divider { border: none; border-top: 1px solid #c8d4e0; margin: 18px 0; }
.footer { margin-top: 24px; border-top: 1px solid #bbb; padding-top: 8px;
          font-size: 8pt; color: #888; text-align: center; }
.pro-badge { background: #1a3a5c; color: #d4af37; padding: 3px 12px;
             border-radius: 10px; font-size: 9pt; font-weight: bold; }
@page { size: A4; margin: 18mm 16mm; }
"""

# ── HTML primitives ──────────────────────────────────────────────────────────

def _kv(pairs: list[tuple]) -> str:
    rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in pairs)
    return f'<table class="kv">{rows}</table>'


def _tbl(headers: list[str], rows: list[list], note: str = "") -> str:
    ths = "".join(f"<th>{h}</th>" for h in headers)
    trs = "".join(
        "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
        for row in rows
    )
    n = f'<p class="note">* {note}</p>' if note else ""
    return f"<table><thead><tr>{ths}</tr></thead><tbody>{trs}</tbody></table>{n}"


def _sec(num: str, title: str, body: str) -> str:
    return f'<h2>{num}. {title}</h2>\n{body}\n'


def _wrap(title: str, body: str) -> str:
    return (
        "<!DOCTYPE html>\n<html lang='ar' dir='rtl'>\n<head>\n"
        f"<meta charset='UTF-8'/>\n<title>{title}</title>\n"
        f"<style>{_CSS}</style>\n</head>\n<body>\n{body}\n</body>\n</html>"
    )


# ── Shared section builders ──────────────────────────────────────────────────

def _cover(report_title: str, depth_label: str, report_type_key: str) -> str:
    s = SUBJECT_AR
    badge_color = {"traditional_report": "#E8F4E8", "detailed_report": "#E8EEF8", "professional_report": "#1a3a5c"}.get(report_type_key, "#fff3cd")
    badge_text_color = {"professional_report": "#d4af37"}.get(report_type_key, "#8a5700")
    return (
        f'<div class="cover">'
        f'<h1>{report_title}</h1>'
        f'<p class="sub">تقرير تقييم عقاري — {depth_label}</p>'
        f'<span class="badge" style="background:{badge_color};color:{badge_text_color};">'
        f'مسودة استشارية — غير معتمد للاستخدام الرسمي</span><br>'
        f'<div style="margin-top:12px;">'
        + _kv([
            ("رقم الطلب",        s["request_id"]),
            ("العقار",           s["property_address"]),
            ("نوع العقار",       s["property_type"]),
            ("المساحة الإجمالية",f'{s["gross_floor_area_m2"]} م²'),
            ("الغرض",           s["purpose"]),
            ("أساس القيمة",     s["basis_of_value"]),
            ("تاريخ التقييم",   s["valuation_date"]),
            ("العميل",          s["client"]),
            ("العملة",          s["currency"]),
            ("تاريخ الإصدار",   _GENERATED_AT),
        ]) +
        '</div></div>'
    )


def _advisory(extra: str = "") -> str:
    return (
        f'<div class="advisory"><strong>⚠️ تنبيه مهم:</strong> {ADVISORY_NOTE_AR}'
        + (f"<br>{extra}" if extra else "")
        + "</div>"
    )


def _section_executive_summary(value: int) -> str:
    s = SUBJECT_AR
    r = RECONCILIATION_AR
    return (
        _kv([
            ("العقار",              s["property_address"]),
            ("الغرض",              s["purpose"]),
            ("أساس القيمة",        s["basis_of_value"]),
            ("تاريخ التقييم",      s["valuation_date"]),
            ("رأي القيمة السوقية", f'<strong class="ok">{value:,.0f} {s["currency"]}</strong>'),
            ("حالة التقرير",       "مسودة استشارية"),
        ]) +
        _advisory("هذا التقرير مسودة استشارية. يصدر التقرير المعتمد بعد مراجعة الخبير فقط.")
    )


def _section_asset_id() -> str:
    s = SUBJECT_AR
    return _kv([
        ("العنوان",          s["property_address"]),
        ("نوع العقار",       s["property_type"]),
        ("رقم القطعة",       s["plot_number"]),
        ("الحي",             s["district"]),
        ("المدينة",          s["city"]),
        ("الدولة",           s["country"]),
        ("المساحة الإجمالية",f'{s["gross_floor_area_m2"]} م²'),
        ("المساحة الصافية",  f'{s["net_internal_area_m2"]} م²'),
        ("الطابق",           s["floor"]),
        ("عمر المبنى",       f'{s["age_years"]} سنوات'),
        ("غرف النوم",        str(s["bedrooms"])),
        ("دورات المياه",     str(s["bathrooms"])),
        ("المواقف",          s["parking"]),
        ("حق الانتفاع",     s["tenure"]),
        ("الوضع القانوني",   s["legal_status"]),
        ("التخطيط",          s["zoning"]),
        ("سنة الترخيص",     str(s["building_permit_year"])),
        ("الإحداثيات",       s["coordinates"]),
    ])


def _section_market_approach() -> str:
    comp_rows = [
        [c["id"], c["address"], str(c["area_m2"]), f'{c["price_sar"]:,}',
         f'{c["price_per_sqm"]:,}', c["condition"], c["sale_date"], str(c["distance_km"])]
        for c in COMPARABLES_AR
    ]
    adj_rows = [
        [v["label"]] + [f'{p:+.0f}%' for p in v["values"]]
        for v in ADJUSTMENTS_AR.values()
    ]
    recon_rows = [
        ["م1","م2","م3","م4","م5"],
        [f'{p:,}' for p in ADJUSTED_PRICES_PER_SQM],
    ]
    return (
        "<h3>مبدأ أسلوب السوق / Market Approach Principle</h3>"
        "<p>يقوم هذا الأسلوب على مقارنة العقار محل التقييم بصفقات بيع مشابهة حديثة في نفس السوق، "
        "مع تطبيق تسويات على أوجه الاختلاف.</p>"
        "<h4>جدول المقارنات السوقية</h4>"
        + _tbl(
            ["الرمز", "العنوان", "المساحة م²", "السعر SAR", "سعر/م²", "الحالة", "تاريخ البيع", "البعد كم"],
            comp_rows,
            "بيانات توضيحية — وليست صفقات حقيقية"
        )
        + "<h4>مصفوفة التسويات (%)</h4>"
        + _tbl(["العامل", "م1", "م2", "م3", "م4", "م5"], adj_rows)
        + "<h4>الأسعار المعدلة (SAR/م²)</h4>"
        + _tbl(["م1", "م2", "م3", "م4", "م5"], [
            [f'{p:,}' for p in ADJUSTED_PRICES_PER_SQM]
        ])
        + '<div class="val-box">'
        f'مؤشر القيمة — أسلوب السوق: <span style="color:#1a3a5c">{INDICATED_MARKET_VALUE:,} SAR</span>'
        f'<br><span style="font-size:9.5pt;font-weight:normal;">({INDICATED_MARKET_VALUE_PER_SQM:,} SAR/م² × {SUBJECT_AR["gross_floor_area_m2"]} م²)</span>'
        '</div>'
        + _kv([
            ("مثال توضيحي — تسوية بسيطة",
             "العقار المقارن: م3 — السعر 6,229 SAR/م²، تسوية الموقع -5%، المساحة +4%، "
             "الحالة -3%، الطابق -3%، عمر المبنى -3% → السعر المعدل: 6,232 SAR/م²"),
        ])
    )


def _section_income_approach() -> str:
    i = INCOME_AR
    return (
        "<h3>مبدأ أسلوب الدخل / Income Approach Principle</h3>"
        "<p>يعتمد هذا الأسلوب على رسملة صافي الدخل التشغيلي بمعدل رسملة مناسب لتقدير قيمة العقار.</p>"
        + _kv([
            ("الإيجار السوقي الإجمالي السنوي", f'{i["gross_market_rent_annual"]:,} SAR'),
            ("نسبة الشغور", f'{i["vacancy_rate_pct"]}%'),
            ("خصم الشغور", f'{i["vacancy_deduction"]:,} SAR'),
            ("إجمالي الدخل الفعلي (EGI)", f'{i["effective_gross_income"]:,} SAR'),
            ("رسوم الإدارة", f'{i["management_fee_pct"]}% = {i["management_fee"]:,} SAR'),
            ("الصيانة السنوية", f'{i["maintenance_annual"]:,} SAR'),
            ("التأمين السنوي", f'{i["insurance_annual"]:,} SAR'),
            ("إجمالي المصروفات التشغيلية", f'{i["total_opex"]:,} SAR'),
            ("صافي الدخل التشغيلي (NOI)", f'<strong>{i["net_operating_income"]:,} SAR</strong>'),
            ("معدل الرسملة / Cap Rate", f'{i["cap_rate_pct"]}%'),
            ("مؤشر القيمة — أسلوب الدخل", f'<strong class="ok">{i["indicated_value_income"]:,} SAR</strong>'),
        ])
        + _kv([
            ("مثال توضيحي — رسملة الدخل",
             f'صافي الدخل التشغيلي: {i["net_operating_income"]:,} SAR ÷ معدل الرسملة {i["cap_rate_pct"]}% '
             f'= {i["indicated_value_income"]:,} SAR'),
        ])
    )


def _section_cost_approach() -> str:
    c = COST_AR
    return (
        "<h3>مبدأ أسلوب التكلفة / Cost Approach Principle</h3>"
        "<p>يقدر أسلوب التكلفة قيمة العقار بإضافة قيمة الأرض إلى تكلفة إحلال المباني مخصوماً منها الإهلاك.</p>"
        + _kv([
            ("مساحة الأرض", f'{c["land_area_m2"]:,} م²'),
            ("قيمة الأرض (SAR/م²)", f'{c["land_value_per_sqm"]:,}'),
            ("قيمة الأرض الإجمالية", f'{c["land_value"]:,} SAR'),
            ("تكلفة الإحلال الجديدة (SAR/م²)", f'{c["replacement_cost_new_per_sqm"]:,}'),
            ("تكلفة الإحلال الجديدة الإجمالية", f'{c["replacement_cost_new"]:,} SAR'),
            ("العمر الفعلي / العمر الاقتصادي", f'{c["age_years"]} / {c["effective_life_years"]} سنة'),
            ("نسبة الإهلاك المادي", f'{c["physical_depreciation_pct"]}%'),
            ("الإهلاك المادي", f'{c["physical_depreciation"]:,} SAR'),
            ("التقادم الوظيفي", "لا ينطبق"),
            ("التقادم الاقتصادي", "لا ينطبق"),
            ("قيمة المباني المهلَّكة", f'{c["depreciated_improvement_value"]:,} SAR'),
            ("مؤشر القيمة — أسلوب التكلفة", f'<strong class="ok">{c["indicated_value_cost"]:,} SAR</strong>'),
        ])
        + _kv([
            ("مثال توضيحي — حساب الإهلاك المادي",
             f'({c["age_years"]} ÷ {c["effective_life_years"]}) × {c["replacement_cost_new"]:,} SAR '
             f'= {c["physical_depreciation"]:,} SAR (الإهلاك المادي)'),
        ])
    )


def _section_avm(brief: bool = True) -> str:
    a = AVM_AR
    content = _kv([
        ("مزود AVM", a["avm_provider"]),
        ("القيمة المشار إليها (AVM)", f'{a["avm_indicated_value"]:,} SAR'),
        ("مستوى الثقة", a["confidence_level"]),
        ("درجة الثقة", f'{a["confidence_score"] * 100:.0f}%'),
        ("حداثة البيانات", a["data_freshness"]),
        ("عدد المقارنات المستخدمة", str(a["comparable_count"])),
        ("ملاحظة AVM", a["note"]),
    ])
    if brief:
        content += _kv([
            ("مثال توضيحي — موثوقية AVM",
             "درجة ثقة 72% تعني أن النموذج يعتبر القيمة المشار إليها معقولة "
             "لكنها تستلزم تحقق بشري. AVM مؤشر مساعد، ليس بديلاً عن التقييم المهني."),
        ])
    return content


def _section_reconciliation(show_scorecard: bool = True) -> str:
    r = RECONCILIATION_AR
    body = _kv([
        ("مؤشر أسلوب السوق", f'{r["market_approach_value"]:,} SAR (وزن {r["market_approach_weight_pct"]}%)'),
        ("مؤشر أسلوب الدخل", f'{r["income_approach_value"]:,} SAR (وزن {r["income_approach_weight_pct"]}%)'),
        ("مؤشر أسلوب التكلفة", f'{r["cost_approach_value"]:,} SAR (وزن {r["cost_approach_weight_pct"]}%)'),
        ("القيمة الموزونة", f'{r["weighted_value"]:,} SAR'),
        ("رأي القيمة النهائي", f'<strong class="ok">{r["final_opinion_rounded"]:,} {r["currency"]}</strong>'),
    ])
    if show_scorecard:
        sc_rows = [
            [row["approach"], f'{row["value_sar"]:,}', f'{row["weight_pct"]}%', f'{row["weighted_sar"]:,}']
            for row in RECONCILIATION_SCORECARD_AR
        ]
        body += "<h4>بطاقة الترجيح النهائية</h4>" + _tbl(
            ["الأسلوب", "القيمة (SAR)", "الوزن %", "القيمة الموزونة (SAR)"],
            sc_rows
        )
    return (
        '<div class="val-box">'
        f'🏆 رأي القيمة السوقية النهائي: {r["final_opinion_rounded"]:,} {r["currency"]}'
        '</div>' + body
    )


def _section_assumptions() -> str:
    return (
        "<ul>"
        "<li>يُفترض دقة جميع البيانات والمستندات المقدمة من العميل.</li>"
        "<li>البيانات التوضيحية مستخدمة لأغراض التدريب فقط.</li>"
        "<li>لم تُجرَ فحوصات قانونية رسمية على سند الملكية.</li>"
        "<li>التقييم مبني على حالة العقار في تاريخ المعاينة.</li>"
        "<li>الأسعار بالريال السعودي (SAR) ما لم يُذكر خلاف ذلك.</li>"
        "<li>المعايير المطبقة: IVS 2025 / IVSC.</li>"
        "</ul>"
    )


def _section_standards() -> str:
    rows = [[s["standard"], s["name"], f'<span class="ok">{s["status"]}</span>'] for s in STANDARDS_AR]
    return _tbl(["المعيار", "الاسم", "الحالة"], rows)


def _footer(report_key: str) -> str:
    return (
        f'<div class="footer">'
        f'{report_key} | advisory_only=True | not_real_training=True | '
        f'certification_ready=False | {_GENERATED_AT}<br>'
        f'مسودة استشارية — تصدر النسخة المعتمدة بعد مراجعة الخبير فقط.'
        f'</div>'
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TRADITIONAL REPORT — أسلوب السوق + الدخل + التكلفة + AVM
# ═══════════════════════════════════════════════════════════════════════════════

def _build_traditional() -> str:
    s = SUBJECT_AR
    body = _cover("تقرير تقييم تقليدي", "تقليدي — المستوى الأساسي", "traditional_report")
    body += _sec("1", "الملخص التنفيذي",
                 _section_executive_summary(RECONCILIATION_AR["final_opinion_rounded"]))
    body += _sec("2", "الغرض ونطاق العمل",
                 _kv([
                     ("الغرض",           s["purpose"]),
                     ("أساس القيمة",     s["basis_of_value"]),
                     ("نطاق العمل",      "تقييم تقليدي شامل — يتضمن الأساليب الثلاثة الرئيسية"),
                     ("المستخدمون المقصودون", s["client"]),
                     ("تاريخ التقييم",   s["valuation_date"]),
                 ]))
    body += _sec("3", "تعريف الأصل محل التقييم", _section_asset_id())
    body += _sec("4", "جودة البيانات واكتمال المتطلبات",
                 _tbl(["البيان", "الحالة"],
                      [[d["field"], f'<span class="ok">{d["status"]}</span>' if d["status"] == "مكتمل"
                        else f'<span class="warn">{d["status"]}</span>'] for d in DATA_INPUTS_AR]))
    body += _sec("5", "المعايير المطبقة", _section_standards())
    body += _sec("6", "ملخص أساليب التقييم التقليدية",
                 _kv([
                     ("أسلوب السوق / Market Approach",  "مُطبَّق — وزن 50%"),
                     ("أسلوب الدخل / Income Approach",  "مُطبَّق — وزن 35%"),
                     ("أسلوب التكلفة / Cost Approach",  "مُطبَّق — وزن 15%"),
                     ("AVM / نموذج التقييم الآلي",      "مؤشر مساعد فقط"),
                 ]))
    body += _sec("7", "أسلوب السوق / Market Approach", _section_market_approach())
    body += _sec("8", "أسلوب الدخل / Income Approach", _section_income_approach())
    body += _sec("9", "أسلوب التكلفة / Cost Approach", _section_cost_approach())
    body += _sec("10", "مؤشر التقييم الآلي المساعد AVM", _section_avm(brief=True))
    body += _sec("11", "التوفيق بين النتائج", _section_reconciliation(show_scorecard=True))
    body += _sec("12", "نتيجة القيمة",
                 '<div class="val-box">'
                 f'رأي القيمة السوقية: <strong>{RECONCILIATION_AR["final_opinion_rounded"]:,} SAR</strong>'
                 '</div>'
                 + _advisory("التقرير مسودة استشارية — لا يُستخدم في أي معاملة رسمية دون اعتماد الخبير."))
    body += _sec("13", "الافتراضات والقيود", _section_assumptions())
    body += _sec("14", "تنبيه المسودة ومراجعة الخبير",
                 "<p>هذا التقرير مسودة توضيحية. يتطلب الاستخدام الرسمي مراجعة واعتماد خبير التقييم.</p>"
                 + _advisory())
    body += _sec("15", "الملاحق",
                 "<p>الملحق أ: بيانات المقارنات التفصيلية</p>"
                 "<p>الملحق ب: حسابات أسلوب الدخل</p>"
                 "<p>الملحق ج: حسابات أسلوب التكلفة</p>")
    body += _footer("traditional_report")
    return _wrap("تقرير تقييم تقليدي | PV-2026-QA-001", body)


# ═══════════════════════════════════════════════════════════════════════════════
# DETAILED REPORT — التقليدي + DCF + الحساسية + المخاطر + جداول موسعة
# ═══════════════════════════════════════════════════════════════════════════════

def _section_site_location() -> str:
    s = SUBJECT_AR
    return _kv([
        ("الحي",                  s["district"]),
        ("المدينة",               s["city"]),
        ("المنطقة الإدارية",     "منطقة الرياض"),
        ("نوع المنطقة",           "سكني حضري"),
        ("مستوى الخدمات",         "مرتفع — مدارس، مستشفيات، مراكز تجارية"),
        ("شبكة النقل",           "طريق رئيسي + شوارع داخلية مرصوفة"),
        ("التطور العمراني",       "منطقة راسخة — تطوير مستمر"),
        ("السيولة السوقية",      "متوسطة إلى مرتفعة"),
        ("الإحداثيات",            s["coordinates"]),
    ])


def _section_dcf_summary() -> str:
    d = DCF_5YEAR_AR
    rows = [[str(y + 1), f'{cf:,}'] for y, cf in enumerate(d["year_cash_flows"])]
    rows.append(["القيمة الطرفية — السنة 5", f'{d["terminal_value_year5"]:,}'])
    return (
        _kv([
            ("فترة الاحتجاز", f'{d["hold_period_years"]} سنوات'),
            ("معدل النمو السنوي", f'{d["growth_rate_pct"]}%'),
            ("معدل الرسملة الطرفي", f'{d["terminal_cap_rate_pct"]}%'),
            ("معدل الخصم / Discount Rate", f'{d["discount_rate_pct"]}%'),
        ]) +
        "<h4>التدفقات النقدية السنوية (SAR)</h4>" +
        _tbl(["السنة", "صافي الدخل (SAR)"], rows,
             "مثال توضيحي باستخدام بيانات اختبارية") +
        _kv([("مؤشر قيمة DCF (5 سنوات)", f'<strong>{d["dcf_indicated_value"]:,} SAR</strong>')])
    )


def _section_sensitivity_snapshot() -> str:
    m = SENSITIVITY_MATRIX_AR
    rows = []
    for i, row_label in enumerate(m["rows"]):
        row = [row_label] + [f'{v:,}' for v in m["values"][i]]
        rows.append(row)
    return (
        "<h4>مصفوفة الحساسية — القيمة المشار إليها (SAR)</h4>"
        + _tbl(["↓ معدل الرسملة / إشغال →"] + m["cols"], rows,
               "مثال توضيحي — تأثير تغير معدل الرسملة ونسبة الإشغال على القيمة")
        + _kv([
            ("تفسير",
             "عند معدل رسملة 5.5% وإشغال 92%، تبلغ القيمة المشار إليها 1,247,000 SAR. "
             "تُظهر المصفوفة حساسية القيمة للتغيرات في الافتراضات الرئيسية.")
        ])
    )


def _section_risk_notes() -> str:
    rows = [[r["risk"], r["severity"], r["impact"]] for r in RISKS_AR]
    return _tbl(["المخاطر", "الشدة", "التأثير المحتمل"], rows)


def _build_detailed() -> str:
    s = SUBJECT_AR
    body = _cover("تقرير تقييم تفصيلي", "تفصيلي — المستوى الموسع", "detailed_report")
    body += _sec("1", "الملخص التنفيذي",
                 _section_executive_summary(RECONCILIATION_AR["final_opinion_rounded"]))
    body += _sec("2", "بيانات التكليف",
                 _kv([
                     ("العميل",              s["client"]),
                     ("نوع العميل",          s["client_type"]),
                     ("رقم الطلب",          s["request_id"]),
                     ("تاريخ التعاقد",      s["report_date"]),
                     ("تاريخ المعاينة",     s["inspection_date"]),
                     ("تاريخ التقييم",      s["valuation_date"]),
                 ]))
    body += _sec("3", "الغرض والاستخدام المقصود والمستخدمون المقصودون",
                 _kv([
                     ("الغرض",                   s["purpose"]),
                     ("أساس القيمة",             s["basis_of_value"]),
                     ("الاستخدام المقصود",        "تمويل عقاري — رهن عقاري"),
                     ("المستخدمون المقصودون",     s["client"]),
                     ("القيود على الاستخدام",    "للمستخدمين المقصودين فقط"),
                 ]))
    body += _sec("4", "نطاق العمل",
                 "<p>يشمل نطاق العمل تطبيق الأساليب الثلاثة الرئيسية (السوق والدخل والتكلفة) "
                 "إضافة إلى تحليل التدفقات النقدية المخصومة (DCF) ولقطة الحساسية وملاحظات المخاطر.</p>")
    body += _sec("5", "تعريف الأصل", _section_asset_id())
    body += _sec("6", "مراجعة المستندات والملكية",
                 _kv([
                     ("سند الملكية",       "مقدم (توضيحي — يستلزم تأكيداً)"),
                     ("رخصة البناء",       f'{s["building_permit_year"]}'),
                     ("مخطط الموقع",       "مقدم"),
                     ("تقرير المساحة",     "توضيحي"),
                     ("الأعباء",           "لا أعباء مُسجَّلة (توضيحي)"),
                 ]))
    body += _sec("7", "تحليل الموقع والمنطقة المحيطة", _section_site_location())
    body += _sec("8", "مكونات الأصل / المباني / الاستخدامات",
                 _kv([
                     ("الاستخدام",          "سكني — شقة"),
                     ("المساحة الإجمالية", f'{s["gross_floor_area_m2"]} م²'),
                     ("غرف النوم",          str(s["bedrooms"])),
                     ("دورات المياه",       str(s["bathrooms"])),
                     ("المواقف",            s["parking"]),
                     ("حالة المبنى",        "جيدة"),
                     ("مواصفات التشطيب",   "متوسطة إلى راقية (توضيحي)"),
                 ]))
    body += _sec("9", "ملخص اكتمال المتطلبات",
                 _tbl(["البيان", "الحالة"],
                      [[d["field"], f'<span class="ok">{d["status"]}</span>' if d["status"] == "مكتمل"
                        else f'<span class="warn">{d["status"]}</span>'] for d in DATA_INPUTS_AR]))
    body += _sec("10", "جودة البيانات واكتمالها",
                 _kv([
                     ("درجة جودة البيانات الإجمالية", "جيد — 7/8 بنود مكتملة"),
                     ("البنود تحت التحقق",             "سند الملكية، التقرير القانوني"),
                     ("أثر على التقييم",               "منخفض — البيانات الأساسية كاملة"),
                 ]))
    body += _sec("11", "ملخص الأدلة السوقية",
                 _kv([
                     ("عدد المقارنات السوقية المستخدمة", "5"),
                     ("نطاق السعر (SAR/م²)",             "6,229 — 6,950"),
                     ("متوسط السعر المعدل (SAR/م²)",     f'{INDICATED_MARKET_VALUE_PER_SQM:,}'),
                     ("مؤشر أسلوب السوق",                f'{INDICATED_MARKET_VALUE:,} SAR'),
                 ]))
    body += _sec("12", "جدول المقارنات", _section_market_approach())
    body += _sec("13", "بيانات الدخل والتشغيل", _section_income_approach())
    body += _sec("14", "مدخلات التكلفة والإهلاك", _section_cost_approach())
    body += _sec("15", "ملخص التدفقات النقدية المخصومة DCF", _section_dcf_summary())
    body += _sec("16", "لقطة الحساسية", _section_sensitivity_snapshot())
    body += _sec("17", "ملاحظات المخاطر", _section_risk_notes())
    body += _sec("18", "التوفيق والترجيح", _section_reconciliation(show_scorecard=True))
    body += _sec("19", "المعايير المطبقة", _section_standards())
    body += _sec("20", "مؤشر التقييم الآلي المساعد AVM", _section_avm(brief=False))
    body += _sec("21", "نتيجة القيمة",
                 '<div class="val-box">'
                 f'رأي القيمة السوقية: <strong>{RECONCILIATION_AR["final_opinion_rounded"]:,} SAR</strong>'
                 '</div>'
                 + _advisory())
    body += _sec("22", "الافتراضات والقيود", _section_assumptions())
    body += _sec("23", "مثال ترجيح النتائج",
                 _kv([("ترجيح توضيحي",
                       "أسلوب السوق (50%) × 1,202,500 + أسلوب الدخل (35%) × 1,141,309 "
                       "+ أسلوب التكلفة (15%) × 1,426,800 = 1,215,220 SAR → مقرَّب: 1,200,000 SAR")]))
    body += _sec("24", "الملاحق",
                 "<p>الملحق أ: جدول مقارنات موسع</p><p>الملحق ب: جداول DCF التفصيلية</p>"
                 "<p>الملحق ج: مصفوفة الحساسية الكاملة</p><p>الملحق د: تفاصيل الإهلاك</p>")
    body += _footer("detailed_report")
    return _wrap("تقرير تقييم تفصيلي | PV-2026-QA-001", body)


# ═══════════════════════════════════════════════════════════════════════════════
# PROFESSIONAL REPORT — أوسع تغطية + DCF + HBU + سيناريوهات + حساسية + مخاطر
# ═══════════════════════════════════════════════════════════════════════════════

def _section_method_selection() -> str:
    rows = [[m["method"], m["applicable"], f'{m["weight_pct"]}%', m["reason"]] for m in METHOD_SELECTION_AR]
    return _tbl(["أسلوب التقييم", "قابلية التطبيق", "الوزن", "المبرر"], rows)


def _section_hbu() -> str:
    h = HBU_AR
    return (
        _kv([
            ("مسموح به قانوناً",      h["legally_permissible"]),
            ("ممكن مادياً",           h["physically_possible"]),
            ("مجدي مالياً",          h["financially_feasible"]),
            ("أعلى إنتاجية",         h["maximally_productive"]),
            ("استنتاج أعلى وأفضل استخدام", f'<strong class="ok">{h["conclusion"]}</strong>'),
        ])
    )


def _section_scenarios() -> str:
    rows = [
        [sc["scenario"], f'{sc["growth_rate"]}%', f'{sc["cap_rate"]}%',
         f'{sc["discount_rate"]}%', f'{sc["dcf_value"]:,}']
        for sc in SCENARIOS_AR
    ]
    return (
        _tbl(["السيناريو", "نمو NOI", "معدل رسملة طرفي", "معدل خصم", "قيمة DCF (SAR)"], rows,
             "مثال توضيحي — السيناريوهات الثلاثة")
        + _kv([
            ("القيمة المرجّحة بالاحتمالية",
             f'{PROBABILITY_WEIGHTED_VALUE:,} SAR '
             f'(متحفظ 20% × {1_040_000:,} + أساسي 60% × {1_158_000:,} + متفائل 20% × {1_310_000:,})')
        ])
    )


def _section_dcf_full() -> str:
    d5 = DCF_5YEAR_AR
    d10 = DCF_10YEAR_AR
    rows5 = [[str(y + 1), f'{cf:,}'] for y, cf in enumerate(d5["year_cash_flows"])]
    rows5.append(["قيمة البيع (نهاية سنة 5)", f'{d5["terminal_value_year5"]:,}'])
    return (
        "<h4>تحليل DCF — 5 سنوات</h4>"
        + _kv([
            ("معدل النمو", f'{d5["growth_rate_pct"]}%'),
            ("معدل الرسملة الطرفي", f'{d5["terminal_cap_rate_pct"]}%'),
            ("معدل الخصم", f'{d5["discount_rate_pct"]}%'),
        ])
        + _tbl(["السنة", "التدفق النقدي / القيمة الطرفية (SAR)"], rows5,
               "مثال توضيحي — ليس تقييماً نهائياً")
        + _kv([("قيمة DCF (5 سنوات)", f'<strong>{d5["dcf_indicated_value"]:,} SAR</strong>')])
        + "<h4>تحليل DCF — 10 سنوات</h4>"
        + _kv([("قيمة DCF (10 سنوات)", f'<strong>{d10["dcf_indicated_value"]:,} SAR</strong>')])
    )


def _section_risk_matrix() -> str:
    rows = [[r["risk"], r["severity"], r["impact"]] for r in RISKS_AR]
    return (
        "<h4>مصفوفة مخاطر التقييم</h4>"
        + _tbl(["المخاطر", "الشدة", "التأثير المحتمل"], rows)
        + _kv([
            ("تقييم مخاطر إجمالي", "متوسط"),
            ("التأثير على القيمة", "مدمج في معدل الرسملة ومعدل الخصم"),
            ("المناقشة",
             "تعكس معدلات الرسملة والخصم المستخدمة جزءاً من مخاطر السوق. "
             "لا توجد مخاطر استثنائية تستوجب تعديلاً منفصلاً."),
        ])
    )


def _section_avm_full() -> str:
    a = AVM_AR
    return (
        _kv([
            ("مزود AVM", a["avm_provider"]),
            ("القيمة المشار إليها (AVM)", f'{a["avm_indicated_value"]:,} SAR'),
            ("مستوى الثقة", a["confidence_level"]),
            ("درجة الثقة", f'{a["confidence_score"] * 100:.0f}%'),
            ("حداثة البيانات", a["data_freshness"]),
            ("عدد المقارنات", str(a["comparable_count"])),
            ("الفارق مع أسلوب السوق",
             f'{abs(a["avm_indicated_value"] - INDICATED_MARKET_VALUE):,} SAR '
             f'({abs(a["avm_indicated_value"] - INDICATED_MARKET_VALUE) / INDICATED_MARKET_VALUE * 100:.1f}%)'),
            ("الاستخدام في التوفيق", "مؤشر مساعد — غير مدرج في الترجيح"),
            ("ملاحظة", a["note"]),
        ])
        + _kv([
            ("مناقشة موثوقية AVM",
             "درجة ثقة 72% مقبولة للتحقق المبدئي. الفارق 1.0% عن أسلوب السوق يشير إلى "
             "اتساق جيد. AVM لا يُعتمد وحده وفق معايير IVS."),
        ])
    )


def _section_standards_matrix() -> str:
    rows = [[s["standard"], s["name"], f'<span class="ok">{s["status"]}</span>'] for s in STANDARDS_AR]
    return (
        "<h4>مصفوفة المعايير الدولية المطبقة (IVS 2025)</h4>"
        + _tbl(["رقم المعيار", "اسم المعيار", "حالة الامتثال"], rows)
        + _kv([
            ("هيئة المعايير", "IVSC — International Valuation Standards Council"),
            ("الإصدار", "IVS 2025"),
            ("حالة الامتثال الإجمالية", '<span class="ok">مطابق</span>'),
        ])
    )


def _section_expert_gate() -> str:
    return (
        _kv([
            ("حالة بوابة الاعتماد", "معلقة — تستلزم مراجعة الخبير"),
            ("certification_ready", "False"),
            ("fake_approval_created", "False"),
            ("الخطوة التالية", "تقديم طلب مراجعة واعتماد من خبير التقييم"),
            ("ملاحظة",
             "هذا التقرير مسودة احترافية. لا يصدر التقرير المعتمد إلا بعد مراجعة خبير "
             "مُؤهَّل للبيانات والمنهجية والمستندات."),
        ])
        + _advisory()
    )


def _build_professional() -> str:
    s = SUBJECT_AR
    body = _cover("تقرير تقييم احترافي", "احترافي — أعلى مستوى", "professional_report")
    body += _sec("1", "الملخص التنفيذي",
                 _section_executive_summary(RECONCILIATION_AR["final_opinion_rounded"]))
    body += _sec("2", "بيانات التكليف ونطاق العمل",
                 _kv([
                     ("العميل",              s["client"]),
                     ("نوع العميل",          s["client_type"]),
                     ("رقم الطلب",          s["request_id"]),
                     ("الغرض",              s["purpose"]),
                     ("نطاق العمل",          "تقييم احترافي شامل — جميع الأساليب + DCF + HBU + سيناريوهات + حساسية"),
                     ("تاريخ المعاينة",     s["inspection_date"]),
                     ("تاريخ التقييم",      s["valuation_date"]),
                 ]))
    body += _sec("3", "أساس القيمة وفرضية القيمة",
                 _kv([
                     ("أساس القيمة",        s["basis_of_value"]),
                     ("فرضية القيمة",       "قيمة السوق — الاستخدام الحالي"),
                     ("المعيار المرجعي",    "IVS 104 — أسس القيمة"),
                     ("نوع القيمة",         "قيمة سوقية — ليست قيمة استثمارية أو خاصة"),
                 ]))
    body += _sec("4", "الاستخدام المقصود والمستخدمون المقصودون",
                 _kv([
                     ("الاستخدام المقصود",    "تمويل عقاري — رهن عقاري"),
                     ("المستخدمون المقصودون", s["client"]),
                     ("القيود",               "للمستخدمين المقصودين فقط"),
                 ]))
    body += _sec("5", "تعريف الأصل وملخص الملكية", _section_asset_id())
    body += _sec("6", "مراجعة المستندات والملكية",
                 _kv([
                     ("سند الملكية",       "مقدم (توضيحي)"),
                     ("رخصة البناء",       str(s["building_permit_year"])),
                     ("مخطط الموقع",       "مقدم"),
                     ("تقرير المساحة",     "توضيحي"),
                     ("الأعباء",           "لا أعباء مُسجَّلة (توضيحي)"),
                     ("البحث العيني",      "توضيحي — يستلزم تأكيداً قانونياً"),
                 ]))
    body += _sec("7", "تحليل الموقع والسوق", _section_site_location())
    body += _sec("8", "لوحة اكتمال متطلبات الأصل",
                 _tbl(["البيان", "الحالة"],
                      [[d["field"], f'<span class="ok">{d["status"]}</span>' if d["status"] == "مكتمل"
                        else f'<span class="warn">{d["status"]}</span>'] for d in DATA_INPUTS_AR]))
    body += _sec("9", "جودة البيانات واكتمالها",
                 _kv([
                     ("درجة الجودة الإجمالية", "جيد — 7/8 مكتمل"),
                     ("المعيار المرجعي",        "IVS 102 — التحقيقات والامتثال"),
                 ]))
    body += _sec("10", "تفصيل المكونات / المباني / الاستخدامات",
                 _kv([
                     ("الاستخدام",          "سكني"),
                     ("المساحة الإجمالية", f'{s["gross_floor_area_m2"]} م²'),
                     ("المساحة الصافية",   f'{s["net_internal_area_m2"]} م²'),
                     ("الطابق",             s["floor"]),
                     ("المواقف",            s["parking"]),
                     ("التشطيب",            "متوسط إلى راقي (توضيحي)"),
                     ("الخدمات",            "كهرباء، مياه، تكييف مركزي (توضيحي)"),
                 ]))
    body += _sec("11", "مصفوفة المعايير المطبقة", _section_standards_matrix())
    body += _sec("12", "سجل البيانات والمدخلات",
                 _tbl(["البيان", "الحالة"],
                      [[d["field"], d["status"]] for d in DATA_INPUTS_AR]))
    body += _sec("13", "مصفوفة اختيار أساليب التقييم", _section_method_selection())
    body += _sec("14", "أسلوب السوق / Market Approach", _section_market_approach())
    body += _sec("15", "أسلوب الدخل / Income Approach", _section_income_approach())
    body += _sec("16", "أسلوب التكلفة / Cost Approach", _section_cost_approach())
    body += _sec("17", "تحليل التدفقات النقدية المخصومة DCF", _section_dcf_full())
    body += _sec("18", "ملخص أعلى وأفضل استخدام HBU", _section_hbu())
    body += _sec("19", "تحليل السيناريوهات", _section_scenarios())
    body += _sec("20", "تحليل الحساسية", _section_sensitivity_snapshot())
    body += _sec("21", "مناقشة التقييم المعدل بالمخاطر", _section_risk_matrix())
    body += _sec("22", "مؤشر التقييم الآلي المساعد AVM وموثوقيته", _section_avm_full())
    body += _sec("23", "نموذج التوفيق والترجيح النهائي", _section_reconciliation(show_scorecard=True))
    body += _sec("24", "نتيجة القيمة",
                 '<div class="val-box">'
                 f'🏆 رأي القيمة السوقية النهائي: <strong>{RECONCILIATION_AR["final_opinion_rounded"]:,} SAR</strong>'
                 '</div>'
                 + _advisory())
    body += _sec("25", "الافتراضات والقيود", _section_assumptions())
    body += _sec("26", "بوابة مراجعة الخبير والاعتماد", _section_expert_gate())
    body += _sec("27", "الملاحق",
                 "<p>الملحق أ: جدول المقارنات الموسع (5 مقارنات)</p>"
                 "<p>الملحق ب: جداول DCF التفصيلية (5 و10 سنوات)</p>"
                 "<p>الملحق ج: مصفوفة الحساسية الكاملة</p>"
                 "<p>الملحق د: مصفوفة المخاطر</p>"
                 "<p>الملحق ه: مصفوفة المعايير الدولية</p>"
                 "<p>الملحق و: سجل البيانات والمدخلات</p>"
                 "<p>الملحق ز: بطاقة الترجيح النهائية</p>")
    body += _footer("professional_report")
    return _wrap("تقرير تقييم احترافي | PV-2026-QA-001", body)


# ═══════════════════════════════════════════════════════════════════════════════
# PDF rendering via Chrome headless
# ═══════════════════════════════════════════════════════════════════════════════

def _render_pdf(html: str, out_path: Path) -> dict:
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, encoding="utf-8", mode="w") as f:
        f.write(html)
        tmp = Path(f.name)
    try:
        cmd = [
            str(_CHROME),
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-extensions",
            "--run-all-compositor-stages-before-draw",
            f"--print-to-pdf={out_path}",
            "--print-to-pdf-no-header",
            tmp.as_uri(),
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        rendered_ok = out_path.exists() and out_path.stat().st_size > 5_000
        return {
            "rendered_ok": rendered_ok,
            "pdf_path": str(out_path),
            "pdf_size_bytes": out_path.stat().st_size if out_path.exists() else 0,
            "returncode": result.returncode,
        }
    except Exception as e:
        return {"rendered_ok": False, "pdf_path": str(out_path), "pdf_size_bytes": 0, "error": str(e)}
    finally:
        tmp.unlink(missing_ok=True)


def generate_all_pdfs(
    pdf_out: Path,
    preview_out: Path,
) -> dict[str, dict]:
    pdf_out.mkdir(parents=True, exist_ok=True)
    preview_out.mkdir(parents=True, exist_ok=True)

    builders = {
        "traditional_report": ("تقرير تقييم تقليدي", _build_traditional),
        "detailed_report":    ("تقرير تقييم تفصيلي",  _build_detailed),
        "professional_report":("تقرير تقييم احترافي", _build_professional),
    }
    results = {}
    for key, (title, builder_fn) in builders.items():
        html = builder_fn()
        # Save HTML preview
        preview_path = preview_out / f"{key}_preview.html"
        preview_path.write_text(html, encoding="utf-8")
        # Render PDF
        pdf_path = pdf_out / f"{key}.pdf"
        r = _render_pdf(html, pdf_path)
        r["title_ar"] = title
        r["report_key"] = key
        r["preview_html"] = str(preview_path)
        results[key] = r
    return results
