"""
professional_valuation_pdf_modern_methods_upgrade.py
تقارير PDF عربية مُحسَّنة — تعكس الأساليب الحديثة الموجودة في ملفات Excel القديمة

التقليدي: 16 قسماً | التفصيلي: 28 قسماً | الاحترافي: 31 قسماً

pdf_language=ar | arabic_primary=True | advisory_only=True | not_real_training=True
"""
from __future__ import annotations

import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

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

# ── CSS (RTL Arabic — نفس الأسلوب مع تحسينات بصرية) ────────────────────────────
_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700;900&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Tajawal', 'Arial Unicode MS', 'Segoe UI', Arial, sans-serif;
  font-size: 10.5pt; color: #1a1a1a; line-height: 1.75;
  direction: rtl; text-align: right;
}
h1 { font-size: 20pt; color: #1a3a5c; text-align: center; margin-bottom: 10px; }
h2 { font-size: 13pt; color: #1a3a5c; border-bottom: 2px solid #1a3a5c;
     padding-bottom: 4px; margin: 24px 0 8px; }
h3 { font-size: 11pt; color: #2c5f8a; margin: 16px 0 5px; border-right: 3px solid #2c5f8a;
     padding-right: 8px; }
h4 { font-size: 10pt; color: #34609a; margin: 12px 0 4px; }
p  { margin: 7px 0; }
ul { margin: 6px 0; padding-right: 22px; list-style-type: disc; }
li { margin: 4px 0; font-size: 10pt; }
table { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 9.5pt; direction: rtl; }
th { background: #1a3a5c; color: #fff; padding: 7px 10px; text-align: right; }
td { padding: 6px 10px; border: 1px solid #c8d4e0; vertical-align: top; text-align: right; }
tr:nth-child(even) td { background: #f0f5fa; }
.kv td:first-child { font-weight: bold; background: #e4edf5; width: 38%; }
.advisory {
  background: #fff8e1; border: 2px solid #e6a817;
  padding: 12px 16px; margin: 14px 0; border-radius: 6px; font-size: 9.5pt;
}
.advisory strong { color: #8a5700; font-size: 10.5pt; }
.cover {
  text-align: center; padding: 36px 24px; border: 3px solid #1a3a5c;
  margin-bottom: 24px; border-radius: 10px; background: #f5f9fd;
}
.cover .sub { font-size: 11.5pt; color: #444; margin: 6px 0 16px; }
.cover .badge {
  display: inline-block; background: #fff3cd; border: 1px solid #e6a817;
  color: #8a5700; padding: 4px 14px; border-radius: 14px;
  font-size: 9.5pt; font-weight: bold; margin: 8px 0 16px;
}
.val-box {
  background: #e4edf5; border-right: 5px solid #1a3a5c; padding: 12px 16px;
  margin: 12px 0; font-size: 12pt; font-weight: bold; color: #1a3a5c;
}
.note { font-size: 8.5pt; color: #666; font-style: italic; margin-top: 4px; }
.ok   { color: #1e7e34; font-weight: bold; }
.warn { color: #856404; font-weight: bold; }
.nok  { color: #721c24; font-weight: bold; }
.hl   { background: #fffde7; padding: 9px 14px; border-right: 4px solid #f9a825; margin: 9px 0; border-radius:4px; }
.section-divider { border: none; border-top: 1px solid #c8d4e0; margin: 20px 0; }
.footer { margin-top: 28px; border-top: 1px solid #bbb; padding-top: 8px;
          font-size: 8pt; color: #888; text-align: center; }
.pro-badge { background: #1a3a5c; color: #d4af37; padding: 3px 12px;
             border-radius: 10px; font-size: 9pt; font-weight: bold; }
.dashboard-box {
  border: 2px solid #1a3a5c; border-radius: 8px; padding: 14px 18px;
  margin: 12px 0; background: #f8fbff;
}
.dashboard-box h3 { border: none; padding: 0; color: #1a3a5c; }
.method-card {
  display: inline-block; background: #1a3a5c; color: #fff;
  padding: 6px 14px; border-radius: 20px; font-size: 9pt;
  margin: 4px; font-weight: bold;
}
.method-card.partial { background: #2c5f8a; }
.method-card.na { background: #888; }
.risk-high { color: #721c24; font-weight: bold; }
.risk-med  { color: #856404; font-weight: bold; }
.risk-low  { color: #1e7e34; font-weight: bold; }
@page { size: A4; margin: 18mm 16mm; }
"""

# ── HTML primitives ───────────────────────────────────────────────────────────

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


def _example_label(text: str = "") -> str:
    base = "مثال توضيحي باستخدام بيانات اختبارية، وليس نتيجة تقييم نهائية."
    return f'<p class="note">⚠️ {base} {text}</p>'


# ── Shared blocks ─────────────────────────────────────────────────────────────

def _cover(report_title: str, depth_label: str, report_type_key: str) -> str:
    s = SUBJECT_AR
    bc = {"professional_report": "#1a3a5c"}.get(report_type_key, "#E8EEF8")
    tc = {"professional_report": "#d4af37"}.get(report_type_key, "#1a3a5c")
    return (
        f'<div class="cover">'
        f'<h1>{report_title}</h1>'
        f'<p class="sub">تقرير تقييم عقاري — {depth_label}</p>'
        f'<span class="badge" style="background:{bc};color:{tc};">'
        f'مسودة استشارية — غير معتمد للاستخدام الرسمي</span><br>'
        f'<div style="margin-top:14px;">'
        + _kv([
            ("رقم الطلب",        s["request_id"]),
            ("العقار",           s["property_address"]),
            ("نوع العقار",       s["property_type"]),
            ("المساحة الإجمالية",f'{s["gross_floor_area_m2"]} م²'),
            ("الغرض",           s["purpose"]),
            ("أساس القيمة",     s["basis_of_value"]),
            ("تاريخ التقييم",   s["valuation_date"]),
            ("تاريخ المعاينة",  s["inspection_date"]),
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


def _section_executive_summary(value: int, extra_rows: list[tuple] | None = None) -> str:
    s = SUBJECT_AR
    base_rows = [
        ("العقار",              s["property_address"]),
        ("الغرض",              s["purpose"]),
        ("أساس القيمة",        s["basis_of_value"]),
        ("تاريخ التقييم",      s["valuation_date"]),
        ("رأي القيمة السوقية", f'<strong class="ok">{value:,.0f} {s["currency"]}</strong>'),
        ("حالة التقرير",       "مسودة استشارية"),
    ]
    if extra_rows:
        base_rows += extra_rows
    return (
        _kv(base_rows) +
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


def _section_site_location() -> str:
    s = SUBJECT_AR
    return (
        _kv([
            ("الحي",                  s["district"]),
            ("المدينة",               s["city"]),
            ("المنطقة الإدارية",     "منطقة الرياض"),
            ("نوع المنطقة",           "سكني حضري — R-2"),
            ("مستوى الخدمات",         "مرتفع — مدارس، مستشفيات، مراكز تجارية"),
            ("شبكة النقل",           "طريق رئيسي + شوارع داخلية مرصوفة"),
            ("التطور العمراني",       "منطقة راسخة — تطوير مستمر"),
            ("السيولة السوقية",      "متوسطة إلى مرتفعة"),
            ("الإحداثيات",            s["coordinates"]),
        ])
        + "<h4>ملاحظات السوق والمنطقة المحيطة</h4>"
        + "<ul>"
        "<li>المنطقة تشهد طلباً متصاعداً على الوحدات السكنية.</li>"
        "<li>يتراوح متوسط سعر البيع المتري بين 6,200 — 7,000 SAR/م².</li>"
        "<li>معدلات الإشغال الإيجاري تتراوح بين 85% — 95%.</li>"
        "<li>البنية التحتية مكتملة — لا مخاطر هيكلية واضحة.</li>"
        "</ul>"
    )


def _section_standards() -> str:
    rows = [[s["standard"], s["name"], f'<span class="ok">{s["status"]}</span>'] for s in STANDARDS_AR]
    return _tbl(["المعيار", "الاسم", "الحالة"], rows)


def _section_assumptions() -> str:
    return (
        "<ul>"
        "<li>يُفترض دقة جميع البيانات والمستندات المقدمة من العميل.</li>"
        "<li>البيانات التوضيحية مستخدمة لأغراض التدريب فقط — وليست بيانات صفقات حقيقية.</li>"
        "<li>لم تُجرَ فحوصات قانونية رسمية على سند الملكية.</li>"
        "<li>التقييم مبني على حالة العقار في تاريخ المعاينة.</li>"
        "<li>الأسعار بالريال السعودي (SAR) ما لم يُذكر خلاف ذلك.</li>"
        "<li>المعايير المطبقة: IVS 2025 / IVSC.</li>"
        "<li>لا توجد ظروف استثنائية أو أعباء خفية على الأصل (افتراض توضيحي).</li>"
        "</ul>"
    )


def _section_market_approach(extended: bool = False) -> str:
    comp_rows = [
        [c["id"], c["address"], str(c["area_m2"]), f'{c["price_sar"]:,}',
         f'{c["price_per_sqm"]:,}', c["condition"], c["sale_date"], str(c["distance_km"])]
        for c in COMPARABLES_AR
    ]
    adj_rows = [
        [v["label"]] + [f'{p:+.0f}%' for p in v["values"]]
        for v in ADJUSTMENTS_AR.values()
    ]
    total_adj = [
        [f'{sum(list(ADJUSTMENTS_AR.values())[j]["values"][i] for j in range(len(ADJUSTMENTS_AR))):+.0f}%'
         for i in range(5)]
    ]
    out = (
        "<h3>مبدأ أسلوب السوق / Market Approach</h3>"
        "<p>يقوم هذا الأسلوب على مقارنة العقار محل التقييم بصفقات بيع مشابهة حديثة في نفس السوق، "
        "مع تطبيق تسويات كمية ونوعية على أوجه الاختلاف بين كل مقارنة والعقار محل التقييم.</p>"
        "<h4>جدول المقارنات السوقية — 5 مقارنات</h4>"
        + _tbl(
            ["الرمز", "العنوان", "المساحة م²", "السعر SAR", "سعر/م²", "الحالة", "تاريخ البيع", "البعد كم"],
            comp_rows,
            "بيانات توضيحية — وليست صفقات حقيقية"
        )
    )
    if extended:
        out += (
            "<h4>مصفوفة التسويات — التفصيل الكمي (%)</h4>"
            + _tbl(["عامل التسوية", "م1", "م2", "م3", "م4", "م5"], adj_rows)
            + "<h4>مجموع التسويات الصافية</h4>"
            + _tbl(["م1", "م2", "م3", "م4", "م5"], total_adj)
        )
    out += (
        "<h4>الأسعار المعدلة (SAR/م²)</h4>"
        + _tbl(["م1", "م2", "م3", "م4", "م5"], [
            [f'{p:,}' for p in ADJUSTED_PRICES_PER_SQM]
        ])
        + '<div class="val-box">'
        f'مؤشر القيمة — أسلوب السوق: {INDICATED_MARKET_VALUE:,} SAR'
        f'<br><span style="font-size:9.5pt;font-weight:normal;">({INDICATED_MARKET_VALUE_PER_SQM:,} SAR/م² × {SUBJECT_AR["gross_floor_area_m2"]} م²)</span>'
        '</div>'
        + _kv([
            ("مثال توضيحي — تسوية تفصيلية",
             "م3 — السعر الأصلي 6,229 SAR/م² → "
             "موقع -5% = -311، مساحة +4% = +249، حالة -3% = -187، "
             "طابق -3% = -187، مواقف +4% = +249، عمر -3% = -187 → "
             "سعر معدل: 6,232 SAR/م²"),
        ])
        + _example_label()
    )
    return out


def _section_income_approach(extended: bool = False) -> str:
    i = INCOME_AR
    out = (
        "<h3>مبدأ أسلوب الدخل / Income Approach</h3>"
        "<p>يعتمد هذا الأسلوب على رسملة صافي الدخل التشغيلي بمعدل رسملة مناسب، "
        "مستنتج من السوق، لتقدير قيمة العقار المُدر للدخل.</p>"
        + _kv([
            ("الإيجار السوقي الإجمالي السنوي", f'{i["gross_market_rent_annual"]:,} SAR'),
            ("نسبة الشغور / Vacancy Rate",     f'{i["vacancy_rate_pct"]}%'),
            ("خصم الشغور",                     f'({i["vacancy_deduction"]:,}) SAR'),
            ("إجمالي الدخل الفعلي (EGI)",       f'{i["effective_gross_income"]:,} SAR'),
        ])
    )
    if extended:
        out += _kv([
            ("رسوم الإدارة والتحصيل",    f'{i["management_fee_pct"]}% = ({i["management_fee"]:,}) SAR'),
            ("الصيانة السنوية",          f'({i["maintenance_annual"]:,}) SAR'),
            ("التأمين السنوي",           f'({i["insurance_annual"]:,}) SAR'),
            ("إجمالي المصروفات التشغيلية", f'({i["total_opex"]:,}) SAR'),
            ("صافي الدخل التشغيلي (NOI)",  f'<strong>{i["net_operating_income"]:,} SAR</strong>'),
            ("معدل الرسملة / Cap Rate",    f'{i["cap_rate_pct"]}%'),
            ("مؤشر القيمة — أسلوب الدخل", f'<strong class="ok">{i["indicated_value_income"]:,} SAR</strong>'),
        ])
    else:
        out += _kv([
            ("صافي الدخل التشغيلي (NOI)",  f'<strong>{i["net_operating_income"]:,} SAR</strong>'),
            ("معدل الرسملة / Cap Rate",    f'{i["cap_rate_pct"]}%'),
            ("مؤشر القيمة — أسلوب الدخل", f'<strong class="ok">{i["indicated_value_income"]:,} SAR</strong>'),
        ])
    out += (
        _kv([("مثال توضيحي — حساب NOI ورسملة الدخل",
              f'EGI: {i["effective_gross_income"]:,} SAR - مصاريف: {i["total_opex"]:,} SAR '
              f'= NOI: {i["net_operating_income"]:,} SAR ÷ Cap Rate {i["cap_rate_pct"]}% '
              f'= {i["indicated_value_income"]:,} SAR')])
        + _example_label()
    )
    return out


def _section_direct_capitalization() -> str:
    i = INCOME_AR
    return (
        "<h3>الرسملة المباشرة / Direct Capitalization</h3>"
        "<p>تُعد الرسملة المباشرة (شيت 'رأسمالة الدخل' في ملف Excel القديم) من أبسط تطبيقات "
        "أسلوب الدخل: تقسيم NOI على معدل رسملة للحصول على القيمة مباشرةً دون تحليل "
        "تدفق نقدي متعدد السنوات.</p>"
        + _kv([
            ("صافي الدخل التشغيلي (NOI)",       f'{i["net_operating_income"]:,} SAR'),
            ("معدل الرسملة المستنتج / All-Risks Yield", f'{i["cap_rate_pct"]}%'),
            ("قيمة الأصل = NOI ÷ Cap Rate",     f'{i["indicated_value_income"]:,} SAR'),
            ("المصدر المرجعي",                  "شيت 'رأسمالة الدخل' — Report_ES_GRAND_FINAL_v4.xlsm"),
        ])
        + "<h4>جدول حساسية معدل الرسملة (الرسملة المباشرة)</h4>"
        + _tbl(
            ["معدل الرسملة", "القيمة المشار إليها (SAR)"],
            [
                ["4.5%", f'{int(i["net_operating_income"]/0.045):,}'],
                ["5.0%", f'{int(i["net_operating_income"]/0.050):,}'],
                ["5.5%", f'{i["indicated_value_income"]:,}'],
                ["6.0%", f'{int(i["net_operating_income"]/0.060):,}'],
                ["6.5%", f'{int(i["net_operating_income"]/0.065):,}'],
            ],
            "مثال توضيحي — تأثير معدل الرسملة على القيمة"
        )
        + _example_label()
    )


def _section_cost_approach(extended: bool = False) -> str:
    c = COST_AR
    out = (
        "<h3>مبدأ أسلوب التكلفة / Cost Approach</h3>"
        "<p>يقدر أسلوب التكلفة (المستوحى من شيتات RCNLD وReproduction Cost في ملف Excel القديم) "
        "قيمة العقار بإضافة قيمة الأرض إلى تكلفة إحلال المباني مخصوماً منها الإهلاك المتراكم.</p>"
        + _kv([
            ("مساحة الأرض",                     f'{c["land_area_m2"]:,} م²'),
            ("قيمة الأرض (SAR/م²)",             f'{c["land_value_per_sqm"]:,}'),
            ("قيمة الأرض الإجمالية",             f'{c["land_value"]:,} SAR'),
            ("تكلفة الإحلال الجديدة (SAR/م²)",   f'{c["replacement_cost_new_per_sqm"]:,}'),
            ("تكلفة الإحلال الجديدة الإجمالية",  f'{c["replacement_cost_new"]:,} SAR'),
            ("العمر الفعلي / العمر الاقتصادي",   f'{c["age_years"]} / {c["effective_life_years"]} سنة'),
            ("نسبة الإهلاك المادي",              f'{c["physical_depreciation_pct"]}%'),
            ("الإهلاك المادي المتراكم",           f'({c["physical_depreciation"]:,}) SAR'),
        ])
    )
    if extended:
        out += _kv([
            ("التقادم الوظيفي / Functional Obsolescence",  "لا ينطبق — تصميم حديث"),
            ("التقادم الاقتصادي / Economic Obsolescence",  "لا ينطبق — منطقة مستقرة"),
            ("قيمة المباني المهلَّكة",              f'{c["depreciated_improvement_value"]:,} SAR'),
            ("قيمة الأرض + المباني المهلَّكة",     f'{c["indicated_value_cost"]:,} SAR'),
            ("مؤشر القيمة — أسلوب التكلفة",       f'<strong class="ok">{c["indicated_value_cost"]:,} SAR</strong>'),
            ("المصدر المرجعي",                    "شيت RCNLD + شيت Reproduction Cost — Excel القديم"),
        ])
    else:
        out += _kv([
            ("قيمة المباني المهلَّكة",   f'{c["depreciated_improvement_value"]:,} SAR'),
            ("مؤشر القيمة — أسلوب التكلفة", f'<strong class="ok">{c["indicated_value_cost"]:,} SAR</strong>'),
        ])
    out += (
        _kv([("مثال توضيحي — حساب الإهلاك المادي",
              f'({c["age_years"]} سنة ÷ {c["effective_life_years"]} سنة) × {c["replacement_cost_new"]:,} SAR '
              f'= {c["physical_depreciation"]:,} SAR (نسبة الإهلاك = {c["physical_depreciation_pct"]}%)')])
        + _example_label()
    )
    return out


def _section_dcf_summary() -> str:
    d = DCF_5YEAR_AR
    rows = [[str(y + 1), f'{cf:,}'] for y, cf in enumerate(d["year_cash_flows"])]
    rows.append(["القيمة الطرفية — السنة 5 / Terminal Value",
                 f'{d["terminal_value_year5"]:,}'])
    return (
        "<h3>ملخص DCF — 5 سنوات / DCF Summary</h3>"
        "<p>التدفقات النقدية المخصومة (مستوحاة من شيت 'DCF — التدفقات النقدية' في Excel القديم). "
        "تُقدّر قيمة الأصل بخصم التدفقات النقدية المستقبلية المتوقعة بمعدل خصم معكوس لمخاطر السوق.</p>"
        + _kv([
            ("فترة الاحتجاز / Hold Period",      f'{d["hold_period_years"]} سنوات'),
            ("معدل النمو السنوي / Growth Rate",   f'{d["growth_rate_pct"]}%'),
            ("معدل الرسملة الطرفي / Exit Cap",    f'{d["terminal_cap_rate_pct"]}%'),
            ("معدل الخصم / Discount Rate",        f'{d["discount_rate_pct"]}%'),
        ])
        + "<h4>التدفقات النقدية السنوية — NOI المتوقع (SAR)</h4>"
        + _tbl(["السنة", "صافي الدخل التشغيلي (SAR)"], rows,
               "مثال توضيحي باستخدام بيانات اختبارية")
        + _kv([
            ("مؤشر قيمة DCF (5 سنوات)",
             f'<strong>{d["dcf_indicated_value"]:,} SAR</strong>'),
            ("صيغة القيمة الطرفية",
             f'NOI السنة 5 ({d["year_cash_flows"][-1]:,}) ÷ معدل رسملة طرفي ({d["terminal_cap_rate_pct"]}%) '
             f'= {d["terminal_value_year5"]:,} SAR'),
        ])
        + _example_label()
    )


def _section_dcf_full() -> str:
    d5 = DCF_5YEAR_AR
    d10 = DCF_10YEAR_AR
    rows5 = [[str(y + 1), f'{cf:,}'] for y, cf in enumerate(d5["year_cash_flows"])]
    rows5.append(["القيمة الطرفية — نهاية سنة 5",
                  f'{d5["terminal_value_year5"]:,}'])
    rows10_noi = [int(d5["initial_noi"] * (1 + d10["growth_rate_pct"] / 100) ** y)
                  for y in range(10)]
    rows10 = [[str(y + 1), f'{noi:,}'] for y, noi in enumerate(rows10_noi)]
    rows10.append(["القيمة الطرفية — نهاية سنة 10",
                   f'{int(rows10_noi[-1] / (d10["terminal_cap_rate_pct"] / 100)):,}'])
    return (
        "<h3>تحليل التدفقات النقدية المخصومة DCF — 5 و10 سنوات</h3>"
        "<p>تحليل DCF الكامل مستوحى من شيت 'DCF — التدفقات النقدية' وشيت 'DCF + Options' "
        "الموجودَين في ملف Report_ES_GRAND_FINAL_v4.xlsm.</p>"
        "<h4>تحليل DCF — 5 سنوات</h4>"
        + _kv([
            ("معدل النمو", f'{d5["growth_rate_pct"]}%'),
            ("معدل الرسملة الطرفي", f'{d5["terminal_cap_rate_pct"]}%'),
            ("معدل الخصم", f'{d5["discount_rate_pct"]}%'),
        ])
        + _tbl(["السنة", "التدفق النقدي / القيمة الطرفية (SAR)"], rows5,
               "مثال توضيحي")
        + _kv([("قيمة DCF (5 سنوات)", f'<strong>{d5["dcf_indicated_value"]:,} SAR</strong>')])
        + "<h4>تحليل DCF — 10 سنوات</h4>"
        + _kv([
            ("معدل النمو", f'{d10["growth_rate_pct"]}%'),
            ("معدل الخصم", f'{d10["discount_rate_pct"]}%'),
        ])
        + _tbl(["السنة", "التدفق النقدي (SAR)"], rows10,
               "مثال توضيحي — ليس تقييماً نهائياً")
        + _kv([
            ("قيمة DCF (10 سنوات)", f'<strong>{d10["dcf_indicated_value"]:,} SAR</strong>'),
            ("القيمة النهائية Terminal Value (نهاية سنة 10)",
             f'{int(rows10_noi[-1] / (d10["terminal_cap_rate_pct"] / 100)):,} SAR '
             f'(NOI₁₀ ÷ معدل رسملة طرفي {d10["terminal_cap_rate_pct"]}%)'),
            ("مقارنة DCF 5 سنوات مع 10 سنوات",
             f'5Y: {d5["dcf_indicated_value"]:,} SAR — 10Y: {d10["dcf_indicated_value"]:,} SAR — '
             f'الفارق: {abs(d5["dcf_indicated_value"] - d10["dcf_indicated_value"]):,} SAR'),
        ])
        + _example_label("بيانات DCF توضيحية لأغراض التدريب.")
    )


def _section_residual_method() -> str:
    return (
        "<h3>طريقة المتبقي / Residual Method — التطوير العقاري</h3>"
        "<p>تُستخدم طريقة المتبقي (Residual Land Value) لتقدير قيمة الأرض عندما يكون "
        "الاستخدام المتوقع للأصل التطوير العقاري أو التحويل. استناداً إلى شيتات التطوير "
        "في ملف Excel القديم (إن وُجدت).</p>"
        + _kv([
            ("قابلية التطبيق",
             "منخفضة — الأصل شقة سكنية قائمة وليس أرضاً للتطوير"),
            ("حالة الأصل",       "مبنى قائم — لا يستدعي تحليل متبقي أرضي"),
            ("الاستنتاج",
             "طريقة المتبقي غير منطبقة على هذا الأصل. "
             "إذا كان الغرض تقدير قيمة أرض خام للتطوير فيُطبَّق هذا الأسلوب."),
            ("المصدر المرجعي",
             "تحليل HBU — شيت 'أفضل وأعلى استخدام — HABU'"),
        ])
        + '<div class="hl">'
        '<p><strong>صيغة طريقة المتبقي (للتوضيح):</strong></p>'
        '<p>قيمة التطوير المكتمل GDV − تكاليف التطوير − ربح المطور − تمويل = قيمة الأرض المتبقية</p>'
        '</div>'
        + _example_label("لا ينطبق هذا الأسلوب على العقار محل التقييم.")
    )


def _section_hbu() -> str:
    h = HBU_AR
    return (
        "<h3>أعلى وأفضل استخدام / HBU Analysis</h3>"
        "<p>تحليل أعلى وأفضل استخدام مستوحى من شيت 'أفضل وأعلى استخدام — HABU' "
        "في ملف Report_ES_GRAND_FINAL_v4.xlsm. يُحدد الاستخدام الذي يعظم قيمة الأصل.</p>"
        + _kv([
            ("مسموح به قانوناً",                h["legally_permissible"]),
            ("ممكن مادياً",                    h["physically_possible"]),
            ("مجدي مالياً",                    h["financially_feasible"]),
            ("أعلى إنتاجية / Maximally Productive", h["maximally_productive"]),
            ("استنتاج أعلى وأفضل استخدام",
             f'<strong class="ok">{h["conclusion"]}</strong>'),
            ("المرجع في Excel",                "شيت أفضل وأعلى استخدام — HABU"),
        ])
        + _tbl(["المعيار", "التقييم", "الملاحظة"],
               [
                   ["الاستخدام القانوني",  "✅ مسموح", "R-2 سكني"],
                   ["الاستخدام المادي",    "✅ ممكن",   "مبنى قائم صالح للسكن"],
                   ["الجدوى المالية",      "✅ مجدي",   "NOI إيجابي"],
                   ["أعلى إنتاجية",       "✅ محقق",   "الاستخدام السكني يعظم القيمة"],
               ])
        + _example_label()
    )


def _section_sensitivity_snapshot() -> str:
    m = SENSITIVITY_MATRIX_AR
    rows = []
    for i, row_label in enumerate(m["rows"]):
        row = [row_label] + [f'{v:,}' for v in m["values"][i]]
        rows.append(row)
    return (
        "<h3>لقطة تحليل الحساسية / Sensitivity Analysis</h3>"
        "<p>مستوحى من شيت '📊 تحليل الحساسية' في ملف Excel القديم.</p>"
        "<h4>مصفوفة الحساسية — القيمة المشار إليها (SAR)</h4>"
        + _tbl(["↓ معدل الرسملة / الإشغال →"] + m["cols"], rows,
               "تأثير تغير معدل الرسملة ونسبة الإشغال على القيمة")
        + _kv([
            ("تفسير النتائج",
             "عند معدل رسملة 5.5% وإشغال 92%، تبلغ القيمة المشار إليها 1,247,000 SAR. "
             "تُظهر المصفوفة حساسية القيمة للتغيرات في الافتراضات الرئيسية."),
            ("المرجع في Excel", "شيت 📊 تحليل الحساسية — Report_ES_GRAND_FINAL_v4.xlsm"),
        ])
        + _example_label()
    )


def _section_sensitivity_full() -> str:
    m = SENSITIVITY_MATRIX_AR
    rows = []
    for i, row_label in enumerate(m["rows"]):
        row = [row_label] + [f'{v:,}' for v in m["values"][i]]
        rows.append(row)
    # Second sensitivity: discount rate vs growth rate
    dr_rows = []
    for dr in [7.5, 8.0, 8.5, 9.0, 9.5]:
        dcf_vals = []
        for gr in [1.5, 2.0, 3.0, 4.0, 4.5]:
            base = DCF_5YEAR_AR["dcf_indicated_value"]
            adj = int(base * (1 + (3.0 - gr) * 0.02) * (1 + (8.5 - dr) * 0.03))
            dcf_vals.append(f'{adj:,}')
        dr_rows.append([f'معدل خصم {dr}%'] + dcf_vals)
    return (
        "<h3>تحليل الحساسية الكامل / Full Sensitivity Analysis</h3>"
        "<p>مستوحى من شيت '📊 تحليل الحساسية' في Report_ES_GRAND_FINAL_v4.xlsm. "
        "يختبر تأثير تغير الافتراضات الرئيسية على القيمة المشار إليها.</p>"
        "<h4>مصفوفة 1: تأثير معدل الرسملة × نسبة الإشغال</h4>"
        + _tbl(["↓ معدل الرسملة / الإشغال →"] + m["cols"], rows,
               "القيمة المشار إليها (SAR)")
        + "<h4>مصفوفة 2: تأثير معدل الخصم × معدل النمو على قيمة DCF</h4>"
        + _tbl(
            ["↓ معدل الخصم / نمو NOI →", "نمو 1.5%", "نمو 2.0%", "نمو 3.0%", "نمو 4.0%", "نمو 4.5%"],
            dr_rows,
            "مثال توضيحي — القيمة المشار إليها DCF (SAR)"
        )
        + _kv([
            ("تفسير عام",
             "أعلى قيمة محتملة (إشغال 100% + رسملة 5%) تصل إلى 1,488,000 SAR. "
             "أدنى قيمة (إشغال 88% + رسملة 6.5%) تبلغ 1,015,000 SAR. "
             "نطاق الحساسية: ±25% حول القيمة المركزية 1,200,000 SAR."),
            ("المرجع في Excel", "شيت 📊 تحليل الحساسية — Report_ES_GRAND_FINAL_v4.xlsm"),
        ])
        + _example_label()
    )


def _section_risk_notes() -> str:
    rows = [[r["risk"], r["severity"], r["impact"]] for r in RISKS_AR]
    return (
        "<h3>ملاحظات المخاطر / Risk Notes</h3>"
        "<p>مستوحى من شيت '📈 RISK_HEATMAP' و'🎯 مصفوفة SWOT' في Excel القديم.</p>"
        + _tbl(["المخاطر", "الشدة", "التأثير المحتمل"], rows)
        + _example_label()
    )


def _section_risk_matrix() -> str:
    prob_impact = [
        ["مخاطر السوق",   "متوسطة", "2 — متوسط",  "2 — متوسط",  "4 — متوسط", "معدل الخصم"],
        ["مخاطر الشغور",  "منخفضة", "2 — متوسط",  "1 — منخفض",  "2 — منخفض", "NOI"],
        ["مخاطر السيولة", "متوسطة", "1 — منخفض",  "2 — متوسط",  "2 — منخفض", "التسعير"],
        ["مخاطر تنظيمية", "منخفضة", "1 — منخفض",  "1 — منخفض",  "1 — منخفض", "التخطيط"],
        ["مخاطر البناء",  "منخفضة", "2 — متوسط",  "1 — منخفض",  "2 — منخفض", "تكلفة الإحلال"],
    ]
    return (
        "<h3>مصفوفة المخاطر / Risk Matrix</h3>"
        "<p>مستوحى من شيتات '📈 RISK_HEATMAP' و'🎯 مصفوفة SWOT' و'🎯 Expected Utility' "
        "في ملف Report_ES_GRAND_FINAL_v4.xlsm.</p>"
        + _tbl(
            ["نوع المخاطرة", "مستوى الشدة", "الاحتمالية (1-3)", "التأثير (1-3)",
             "الدرجة الإجمالية", "المتغير المتأثر"],
            prob_impact,
            "مثال توضيحي — المخاطر وتقديراتها"
        )
        + _kv([
            ("تقييم المخاطر الإجمالي",  "متوسط — 2.2/5"),
            ("التأثير على القيمة",       "مدمج في معدل الرسملة ومعدل الخصم"),
            ("مناقشة المخاطر المعدَّلة",
             "معدل الرسملة 5.5% يتضمن علاوة مخاطر ~1.5% فوق العائد الخالي من المخاطر. "
             "لا توجد مخاطر استثنائية تستوجب تعديلاً منفصلاً على القيمة."),
            ("المرجع في Excel",          "شيت 📈 RISK_HEATMAP + مصفوفة SWOT"),
        ])
        + _example_label()
    )


def _section_scenarios() -> str:
    rows = [
        [sc["scenario"], f'{sc["growth_rate"]}%', f'{sc["cap_rate"]}%',
         f'{sc["discount_rate"]}%', f'{sc["dcf_value"]:,}']
        for sc in SCENARIOS_AR
    ]
    return (
        "<h3>تحليل السيناريوهات / Scenario Analysis</h3>"
        "<p>مستوحى من شيت '💰 DCF + Options' و'🎲 Monte Carlo' في ملف Excel القديم. "
        "يختبر ثلاثة سيناريوهات — متحفظ / أساسي / متفائل.</p>"
        + _tbl(
            ["السيناريو", "نمو NOI سنوياً", "معدل رسملة طرفي", "معدل خصم", "قيمة DCF (SAR)"],
            rows,
            "مثال توضيحي — السيناريوهات الثلاثة"
        )
        + _kv([
            ("القيمة المرجّحة بالاحتمالية / Probability-Weighted Value",
             f'{PROBABILITY_WEIGHTED_VALUE:,} SAR '
             f'(متحفظ 20% × 1,040,000 + أساسي 60% × 1,158,000 + متفائل 20% × 1,310,000)'),
            ("الاحتمالية المُعيَّنة لكل سيناريو",
             "متحفظ: 20% | أساسي: 60% | متفائل: 20%"),
            ("المقارنة مع رأي القيمة",
             f'القيمة المرجّحة {PROBABILITY_WEIGHTED_VALUE:,} SAR مقابل رأي القيمة '
             f'{RECONCILIATION_AR["final_opinion_rounded"]:,} SAR '
             f'(فارق: {abs(PROBABILITY_WEIGHTED_VALUE - RECONCILIATION_AR["final_opinion_rounded"]):,} SAR)'),
            ("المرجع في Excel", "شيت 💰 DCF + Options + 🎲 Monte Carlo"),
        ])
        + _example_label()
    )


def _section_avm(full: bool = False) -> str:
    a = AVM_AR
    content = _kv([
        ("مزود AVM",                         a["avm_provider"]),
        ("القيمة المشار إليها (AVM)",         f'{a["avm_indicated_value"]:,} SAR'),
        ("مستوى الثقة",                       a["confidence_level"]),
        ("درجة الثقة",                        f'{a["confidence_score"] * 100:.0f}%'),
        ("حداثة البيانات",                    a["data_freshness"]),
        ("عدد المقارنات المستخدمة في النموذج", str(a["comparable_count"])),
        ("ملاحظة AVM",                        a["note"]),
    ])
    if full:
        content += _kv([
            ("الفارق مع أسلوب السوق",
             f'{abs(a["avm_indicated_value"] - INDICATED_MARKET_VALUE):,} SAR '
             f'({abs(a["avm_indicated_value"] - INDICATED_MARKET_VALUE) / INDICATED_MARKET_VALUE * 100:.1f}%)'),
            ("الاستخدام في نموذج التوفيق",   "مؤشر مساعد — غير مدرج في الترجيح الرئيسي"),
            ("مناقشة موثوقية AVM",
             "درجة ثقة 72% تعني أن النموذج يعتبر القيمة معقولة، لكنها تستلزم تحققاً بشرياً. "
             "وفق معايير IVS، لا يُعتمد AVM وحده في تقارير التقييم الرسمية. "
             "الفارق 1.0% عن أسلوب السوق يشير إلى اتساق جيد بين المؤشرين."),
        ])
    return content


def _section_reconciliation(detailed: bool = True) -> str:
    r = RECONCILIATION_AR
    body = _kv([
        ("مؤشر أسلوب السوق",   f'{r["market_approach_value"]:,} SAR (وزن {r["market_approach_weight_pct"]}%)'),
        ("مؤشر أسلوب الدخل",   f'{r["income_approach_value"]:,} SAR (وزن {r["income_approach_weight_pct"]}%)'),
        ("مؤشر أسلوب التكلفة", f'{r["cost_approach_value"]:,} SAR (وزن {r["cost_approach_weight_pct"]}%)'),
        ("القيمة الموزونة",     f'{r["weighted_value"]:,} SAR'),
        ("رأي القيمة النهائي",  f'<strong class="ok">{r["final_opinion_rounded"]:,} {r["currency"]}</strong>'),
    ])
    if detailed:
        sc_rows = [
            [row["approach"], f'{row["value_sar"]:,}', f'{row["weight_pct"]}%', f'{row["weighted_sar"]:,}']
            for row in RECONCILIATION_SCORECARD_AR
        ]
        body += "<h4>بطاقة الترجيح النهائية / Final Reconciliation Scorecard</h4>" + _tbl(
            ["الأسلوب", "القيمة (SAR)", "الوزن %", "القيمة الموزونة (SAR)"],
            sc_rows
        )
        body += _kv([
            ("مثال توضيحي — الترجيح",
             f'أسلوب السوق (50%) × {r["market_approach_value"]:,} = {int(r["market_approach_value"]*0.5):,} + '
             f'أسلوب الدخل (35%) × {r["income_approach_value"]:,} = {int(r["income_approach_value"]*0.35):,} + '
             f'أسلوب التكلفة (15%) × {r["cost_approach_value"]:,} = {int(r["cost_approach_value"]*0.15):,} '
             f'= {r["weighted_value"]:,} SAR → مقرَّب: {r["final_opinion_rounded"]:,} SAR'),
            ("مبرر الأوزان",
             "أسلوب السوق يحظى بأعلى وزن لكفاية بيانات السوق. "
             "أسلوب الدخل يحظى بوزن متوسط لكون العقار مدراً للدخل. "
             "أسلوب التكلفة للتحقق فقط — وزن منخفض."),
            ("المرجع في Excel", "شيت 'توفيق النتائج' — Report_ES_GRAND_FINAL_v4.xlsm"),
        ])
        body += _example_label()
    return (
        '<div class="val-box">'
        f'🏆 رأي القيمة السوقية النهائي: {r["final_opinion_rounded"]:,} {r["currency"]}'
        '</div>' + body
    )


def _section_method_selection() -> str:
    rows = [[m["method"], m["applicable"], f'{m["weight_pct"]}%', m["reason"]] for m in METHOD_SELECTION_AR]
    return (
        "<h3>مصفوفة اختيار أساليب التقييم / Method Selection Matrix</h3>"
        "<p>مستوحاة من منهجية شيت 'الافتراضات والمدخلات' وشيت 'توفيق النتائج' في Excel القديم.</p>"
        + _tbl(["أسلوب التقييم", "قابلية التطبيق", "الوزن في التوفيق", "المبرر"], rows)
        + _example_label()
    )


def _section_standards_matrix() -> str:
    rows = [[s["standard"], s["name"], f'<span class="ok">{s["status"]}</span>'] for s in STANDARDS_AR]
    return (
        "<h3>مصفوفة المعايير المطبقة / Standards Compliance Matrix</h3>"
        + _tbl(["رقم المعيار", "اسم المعيار", "حالة الامتثال"], rows)
        + _kv([
            ("هيئة المعايير",         "IVSC — International Valuation Standards Council"),
            ("الإصدار المُطبَّق",      "IVS 2025"),
            ("حالة الامتثال الإجمالية", '<span class="ok">مطابق</span>'),
        ])
    )


def _section_expert_gate() -> str:
    return (
        _kv([
            ("حالة بوابة الاعتماد",   "معلقة — تستلزم مراجعة الخبير"),
            ("certification_ready",   "False"),
            ("fake_approval_created", "False"),
            ("الخطوة التالية",
             "تقديم طلب مراجعة واعتماد من خبير تقييم مُؤهَّل"),
            ("ملاحظة",
             "هذا التقرير مسودة احترافية. لا يصدر التقرير المعتمد إلا بعد مراجعة خبير "
             "مُؤهَّل للبيانات والمنهجية والمستندات — advisory_only=True."),
        ])
        + _advisory()
    )


def _section_dashboard() -> str:
    r = RECONCILIATION_AR
    d5 = DCF_5YEAR_AR
    return (
        '<div class="dashboard-box">'
        '<h3>لوحة ملخص — Dashboard مستوحاة من Excel القديم</h3>'
        "<p>مستوحاة من شيت '🌟 الخريطة الذهنية للنتائج' و'🧠 الخريطة الذهنية للمنهجية' "
        "في Report_ES_GRAND_FINAL_v4.xlsm.</p>"
        + _tbl(
            ["المؤشر", "القيمة (SAR)", "الملاحظة"],
            [
                ["أسلوب السوق",  f'{r["market_approach_value"]:,}', f'وزن {r["market_approach_weight_pct"]}%'],
                ["أسلوب الدخل", f'{r["income_approach_value"]:,}',  f'وزن {r["income_approach_weight_pct"]}%'],
                ["أسلوب التكلفة",f'{r["cost_approach_value"]:,}',   f'وزن {r["cost_approach_weight_pct"]}%'],
                ["DCF (5 سنوات)",f'{d5["dcf_indicated_value"]:,}',   "مؤشر مساعد"],
                ["AVM",          f'{AVM_AR["avm_indicated_value"]:,}', "مؤشر مساعد"],
                ["القيمة الموزونة", f'{r["weighted_value"]:,}',    ""],
                ["<strong>رأي القيمة النهائي</strong>",
                 f'<strong class="ok">{r["final_opinion_rounded"]:,}</strong>', "مُقرَّب"],
            ]
        )
        + "<h4>بطاقة الأساليب المُطبَّقة</h4>"
        + "".join([
            f'<span class="method-card">✅ أسلوب السوق</span>',
            f'<span class="method-card">✅ أسلوب الدخل</span>',
            f'<span class="method-card">✅ أسلوب التكلفة</span>',
            f'<span class="method-card">✅ الرسملة المباشرة</span>',
            f'<span class="method-card">✅ DCF</span>',
            f'<span class="method-card partial">⚡ HBU</span>',
            f'<span class="method-card partial">⚡ السيناريوهات</span>',
            f'<span class="method-card partial">⚡ الحساسية</span>',
            f'<span class="method-card partial">⚡ المخاطر</span>',
            f'<span class="method-card na">➖ المتبقي (لا ينطبق)</span>',
        ])
        + _example_label()
        + "</div>"
    )


def _footer(report_key: str) -> str:
    return (
        f'<div class="footer">'
        f'{report_key} | arabic_primary=True | advisory_only=True | not_real_training=True | '
        f'certification_ready=False | {_GENERATED_AT}<br>'
        f'مسودة استشارية — تصدر النسخة المعتمدة بعد مراجعة الخبير فقط. '
        f'modern_methods_upgrade=True'
        f'</div>'
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TRADITIONAL REPORT — 16 أقسام
# ═══════════════════════════════════════════════════════════════════════════════

def _build_traditional() -> str:
    s = SUBJECT_AR
    body = _cover("تقرير تقييم تقليدي", "تقليدي — المستوى الأساسي", "traditional_report")
    body += _sec("1", "الملخص التنفيذي",
                 _section_executive_summary(RECONCILIATION_AR["final_opinion_rounded"]))
    body += _sec("2", "الغرض ونطاق العمل",
                 _kv([
                     ("الغرض",                   s["purpose"]),
                     ("أساس القيمة",             s["basis_of_value"]),
                     ("نطاق العمل",              "تقييم تقليدي — الأساليب الثلاثة الرئيسية"),
                     ("المستخدمون المقصودون",     s["client"]),
                     ("تاريخ التقييم",           s["valuation_date"]),
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
    body += _sec("7", "أسلوب السوق / Market Approach",
                 _section_market_approach(extended=False))
    body += _sec("8", "أسلوب الدخل / Income Approach",
                 _section_income_approach(extended=False))
    body += _sec("9", "أسلوب التكلفة / Cost Approach",
                 _section_cost_approach(extended=False))
    body += _sec("10", "مؤشر التقييم الآلي المساعد AVM",
                 _section_avm(full=False))
    body += _sec("11", "التوفيق بين النتائج",
                 _section_reconciliation(detailed=True))
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
# DETAILED REPORT — 28 أقسام (مُحسَّن)
# ═══════════════════════════════════════════════════════════════════════════════

def _build_detailed() -> str:
    s = SUBJECT_AR
    body = _cover("تقرير تقييم تفصيلي", "تفصيلي — المستوى الموسع", "detailed_report")
    body += _sec("1", "الملخص التنفيذي",
                 _section_executive_summary(RECONCILIATION_AR["final_opinion_rounded"], [
                     ("الأساليب المطبقة", "السوق + الدخل + التكلفة + الرسملة المباشرة + DCF + حساسية + مخاطر"),
                     ("عدد الأقسام",      "28 قسماً"),
                 ]))
    body += _sec("2", "بيانات التكليف",
                 _kv([
                     ("العميل",          s["client"]),
                     ("نوع العميل",      s["client_type"]),
                     ("رقم الطلب",       s["request_id"]),
                     ("تاريخ التعاقد",   s["report_date"]),
                     ("تاريخ المعاينة",  s["inspection_date"]),
                     ("تاريخ التقييم",   s["valuation_date"]),
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
                 "إضافة إلى الرسملة المباشرة وتحليل التدفقات النقدية المخصومة (DCF) "
                 "ولقطة الحساسية وملاحظات المخاطر وملخص HBU وتحليل طريقة المتبقي.</p>"
                 "<p>المرجع الأساسي لمنهجية التقييم: Report_ES_GRAND_FINAL_v4.xlsm</p>")
    body += _sec("5", "تعريف الأصل", _section_asset_id())
    body += _sec("6", "مراجعة المستندات والملكية",
                 _kv([
                     ("سند الملكية",   "مقدم (توضيحي — يستلزم تأكيداً قانونياً)"),
                     ("رخصة البناء",   f'{s["building_permit_year"]}'),
                     ("مخطط الموقع",   "مقدم"),
                     ("تقرير المساحة", "توضيحي"),
                     ("الأعباء",       "لا أعباء مُسجَّلة (توضيحي)"),
                 ]))
    body += _sec("7", "تحليل الموقع والمنطقة المحيطة", _section_site_location())
    body += _sec("8", "مكونات الأصل / المباني / الاستخدامات",
                 _kv([
                     ("الاستخدام",         "سكني — شقة"),
                     ("المساحة الإجمالية", f'{s["gross_floor_area_m2"]} م²'),
                     ("المساحة الصافية",   f'{s["net_internal_area_m2"]} م²'),
                     ("الطابق",             s["floor"]),
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
                     ("درجة جودة البيانات الإجمالية", "جيد — 7/8 بنود مكتملة (87.5%)"),
                     ("البنود تحت التحقق",             "سند الملكية، التقرير القانوني"),
                     ("أثر على التقييم",               "منخفض — البيانات الأساسية كاملة"),
                     ("معيار الجودة المرجعي",          "IVS 102 — التحقيقات والامتثال"),
                 ]))
    body += _sec("11", "ملخص الأدلة السوقية",
                 _kv([
                     ("عدد المقارنات السوقية المستخدمة", "5"),
                     ("نطاق السعر الأصلي (SAR/م²)",     "6,229 — 6,950"),
                     ("نطاق السعر المعدل (SAR/م²)",     f'{min(ADJUSTED_PRICES_PER_SQM):,} — {max(ADJUSTED_PRICES_PER_SQM):,}'),
                     ("متوسط السعر المعدل (SAR/م²)",     f'{INDICATED_MARKET_VALUE_PER_SQM:,}'),
                     ("مؤشر أسلوب السوق",                f'{INDICATED_MARKET_VALUE:,} SAR'),
                     ("زمن الصفقات",                    "مارس — يونيو 2026"),
                 ]))
    body += _sec("12", "جدول المقارنات السوقية / Market Evidence Table",
                 _section_market_approach(extended=False))
    body += _sec("13", "مصفوفة التسويات / Adjustment Matrix",
                 "<p>يُطبَّق نظام التسوية الكمية على أوجه الاختلاف الرئيسية بين المقارنات والعقار.</p>"
                 + _tbl(
                     ["عامل التسوية", "م1", "م2", "م3", "م4", "م5"],
                     [[v["label"]] + [f'{p:+.0f}%' for p in v["values"]]
                      for v in ADJUSTMENTS_AR.values()],
                     "مثال توضيحي — النسب التقريبية"
                 )
                 + _example_label())
    body += _sec("14", "حسابات أسلوب الدخل والتشغيل / Income Approach Calculations",
                 _section_income_approach(extended=True))
    body += _sec("15", "الرسملة المباشرة / Direct Capitalization",
                 _section_direct_capitalization())
    body += _sec("16", "حسابات أسلوب التكلفة والإهلاك / Cost Approach Calculations",
                 _section_cost_approach(extended=True))
    body += _sec("17", "ملخص التدفقات النقدية المخصومة DCF / DCF Summary",
                 _section_dcf_summary())
    body += _sec("18", "لقطة تحليل الحساسية / Sensitivity Snapshot",
                 _section_sensitivity_snapshot())
    body += _sec("19", "ملخص المخاطر / Risk Summary",
                 _section_risk_notes())
    body += _sec("20", "ملخص أعلى وأفضل استخدام HBU / HBU Summary",
                 _section_hbu())
    body += _sec("21", "ملخص طريقة المتبقي / Residual Method",
                 _section_residual_method())
    body += _sec("22", "التوفيق والترجيح / Reconciliation",
                 _section_reconciliation(detailed=True))
    body += _sec("23", "مؤشر التقييم الآلي المساعد AVM",
                 _section_avm(full=False))
    body += _sec("24", "المعايير المطبقة", _section_standards())
    body += _sec("25", "نتيجة القيمة",
                 '<div class="val-box">'
                 f'رأي القيمة السوقية: <strong>{RECONCILIATION_AR["final_opinion_rounded"]:,} SAR</strong>'
                 '</div>'
                 + _advisory())
    body += _sec("26", "الافتراضات والقيود", _section_assumptions())
    body += _sec("27", "تنبيه المسودة ومراجعة الخبير",
                 "<p>هذا التقرير مسودة تفصيلية. يتطلب الاستخدام الرسمي مراجعة واعتماد خبير التقييم.</p>"
                 + _advisory())
    body += _sec("28", "الملاحق",
                 "<p>الملحق أ: جدول مقارنات سوقية موسع (5 مقارنات مع تفاصيل التسويات)</p>"
                 "<p>الملحق ب: جداول DCF (5 سنوات)</p>"
                 "<p>الملحق ج: مصفوفة الحساسية الكاملة</p>"
                 "<p>الملحق د: تفاصيل الإهلاك المادي والوظيفي</p>"
                 "<p>الملحق ه: بيانات الدخل التفصيلية</p>"
                 "<p>الملحق و: بطاقة الترجيح النهائية</p>"
                 "<p>الملحق ز: مصفوفة SWOT وتحليل المخاطر</p>")
    body += _footer("detailed_report")
    return _wrap("تقرير تقييم تفصيلي | PV-2026-QA-001", body)


# ═══════════════════════════════════════════════════════════════════════════════
# PROFESSIONAL REPORT — 31 أقسام (أعلى مستوى)
# ═══════════════════════════════════════════════════════════════════════════════

def _build_professional() -> str:
    s = SUBJECT_AR
    body = _cover("تقرير تقييم احترافي", "احترافي — أعلى مستوى", "professional_report")
    body += _sec("1", "الملخص التنفيذي",
                 _section_executive_summary(RECONCILIATION_AR["final_opinion_rounded"], [
                     ("الأساليب المطبقة",
                      "السوق + الدخل + التكلفة + الرسملة المباشرة + DCF (5 و10 سنوات) + "
                      "HBU + سيناريوهات + حساسية + مخاطر + AVM + توفيق"),
                     ("عدد الأقسام",      "31 قسماً"),
                     ("مرجع Excel القديم", "Report_ES_GRAND_FINAL_v4.xlsm"),
                 ]))
    body += _sec("2", "بيانات التكليف ونطاق العمل",
                 _kv([
                     ("العميل",          s["client"]),
                     ("نوع العميل",      s["client_type"]),
                     ("رقم الطلب",       s["request_id"]),
                     ("الغرض",           s["purpose"]),
                     ("نطاق العمل",      "تقييم احترافي شامل — جميع الأساليب + DCF + HBU + "
                                         "سيناريوهات + حساسية + مخاطر + AVM"),
                     ("تاريخ المعاينة",  s["inspection_date"]),
                     ("تاريخ التقييم",   s["valuation_date"]),
                     ("إصدار المعايير",  "IVS 2025 / IVSC"),
                 ]))
    body += _sec("3", "أساس القيمة وفرضية القيمة",
                 _kv([
                     ("أساس القيمة",      s["basis_of_value"]),
                     ("فرضية القيمة",     "قيمة السوق — الاستخدام الحالي"),
                     ("المعيار المرجعي",  "IVS 104 — أسس القيمة"),
                     ("نوع القيمة",       "قيمة سوقية — ليست قيمة استثمارية أو خاصة"),
                     ("افتراضات التعامل", "بائع ومشترٍ راشدان في سوق مفتوحة"),
                 ]))
    body += _sec("4", "الاستخدام المقصود والمستخدمون المقصودون",
                 _kv([
                     ("الاستخدام المقصود",    "تمويل عقاري — رهن عقاري"),
                     ("المستخدمون المقصودون", s["client"]),
                     ("القيود",               "للمستخدمين المقصودين فقط — لا يُكشَف لأطراف أخرى"),
                 ]))
    body += _sec("5", "تعريف الأصل وملخص الملكية", _section_asset_id())
    body += _sec("6", "مراجعة المستندات والملكية",
                 _kv([
                     ("سند الملكية",   "مقدم (توضيحي — يستلزم تأكيداً قانونياً)"),
                     ("رخصة البناء",   str(s["building_permit_year"])),
                     ("مخطط الموقع",   "مقدم"),
                     ("تقرير المساحة", "توضيحي"),
                     ("الأعباء",       "لا أعباء مُسجَّلة (توضيحي)"),
                     ("البحث العيني",  "توضيحي — يستلزم تأكيداً قانونياً"),
                 ]))
    body += _sec("7", "تحليل الموقع والسوق", _section_site_location())
    body += _sec("8", "لوحة اكتمال متطلبات الأصل",
                 _tbl(["البيان", "الحالة"],
                      [[d["field"], f'<span class="ok">{d["status"]}</span>' if d["status"] == "مكتمل"
                        else f'<span class="warn">{d["status"]}</span>'] for d in DATA_INPUTS_AR]))
    body += _sec("9", "جودة البيانات واكتمالها",
                 _kv([
                     ("درجة الجودة الإجمالية", "جيد — 7/8 مكتمل (87.5%)"),
                     ("المعيار المرجعي",        "IVS 102 — التحقيقات والامتثال"),
                     ("أثر على الموثوقية",      "منخفض — البيانات الأساسية كاملة"),
                 ]))
    body += _sec("10", "تفصيل المكونات / المباني / الاستخدامات",
                 _kv([
                     ("الاستخدام",         "سكني — شقة"),
                     ("المساحة الإجمالية", f'{s["gross_floor_area_m2"]} م²'),
                     ("المساحة الصافية",   f'{s["net_internal_area_m2"]} م²'),
                     ("الطابق",             s["floor"]),
                     ("المواقف",            s["parking"]),
                     ("التشطيب",            "متوسط إلى راقي (توضيحي)"),
                     ("الخدمات",            "كهرباء، مياه، تكييف مركزي (توضيحي)"),
                 ]))
    body += _sec("11", "مصفوفة المعايير المطبقة", _section_standards_matrix())
    body += _sec("12", "سجل البيانات والمدخلات / Data & Inputs Register",
                 _tbl(["البيان", "الحالة", "الملاحظة"],
                      [[d["field"], d["status"],
                        "مرجعي" if d["status"] == "مكتمل" else "يستلزم مراجعة"]
                       for d in DATA_INPUTS_AR]))
    body += _sec("13", "مصفوفة اختيار أساليب التقييم", _section_method_selection())
    body += _sec("14", "أسلوب السوق / Market Approach",
                 _section_market_approach(extended=True))
    body += _sec("15", "أسلوب الدخل / Income Approach",
                 _section_income_approach(extended=True))
    body += _sec("16", "أسلوب التكلفة / Cost Approach",
                 _section_cost_approach(extended=True))
    body += _sec("17", "الرسملة المباشرة / Direct Capitalization",
                 _section_direct_capitalization())
    body += _sec("18", "تحليل التدفقات النقدية المخصومة DCF — 5 و10 سنوات",
                 _section_dcf_full())
    body += _sec("19", "طريقة المتبقي / Residual Method",
                 _section_residual_method())
    body += _sec("20", "ملخص أعلى وأفضل استخدام HBU / HBU Analysis",
                 _section_hbu())
    body += _sec("21", "تحليل السيناريوهات / Scenario Analysis",
                 _section_scenarios())
    body += _sec("22", "تحليل الحساسية الكامل / Full Sensitivity Analysis",
                 _section_sensitivity_full())
    body += _sec("23", "مناقشة التقييم المعدل بالمخاطر / Risk-Adjusted Valuation",
                 _section_risk_matrix())
    body += _sec("24", "مؤشر التقييم الآلي المساعد AVM وموثوقيته",
                 _section_avm(full=True))
    body += _sec("25", "نموذج التوفيق والترجيح النهائي / Final Reconciliation",
                 _section_reconciliation(detailed=True))
    body += _sec("26", "لوحة ملخص النتائج / Dashboard — مستوحاة من Excel",
                 _section_dashboard())
    body += _sec("27", "نتيجة القيمة أو موانع إصدار النتيجة",
                 '<div class="val-box">'
                 f'🏆 رأي القيمة السوقية النهائي: <strong>{RECONCILIATION_AR["final_opinion_rounded"]:,} SAR</strong>'
                 '</div>'
                 + _advisory())
    body += _sec("28", "الافتراضات والقيود", _section_assumptions())
    body += _sec("29", "بوابة مراجعة الخبير والاعتماد / Expert Gate",
                 _section_expert_gate())
    body += _sec("30", "مقارنة الأساليب مع Excel القديم",
                 _kv([
                     ("مرجع Excel الأساسي",   "Report_ES_GRAND_FINAL_v4.xlsm"),
                     ("أسلوب السوق",          "شيت 'مقارنات البيوع' + 'المقارنات الإيجارية'"),
                     ("أسلوب الدخل",          "شيت 'الافتراضات والمدخلات' + 'رأسمالة الدخل'"),
                     ("أسلوب التكلفة",        "شيت 'طريقة التكلفة' + RCNLD + Reproduction Cost"),
                     ("DCF",                  "شيت 'DCF — التدفقات النقدية' + 'DCF + Options'"),
                     ("HBU",                  "شيت 'أفضل وأعلى استخدام — HABU'"),
                     ("السيناريوهات",         "شيت 'DCF + Options' + 'Monte Carlo'"),
                     ("تحليل الحساسية",       "شيت '📊 تحليل الحساسية'"),
                     ("تحليل المخاطر",        "شيت '📈 RISK_HEATMAP' + 'مصفوفة SWOT'"),
                     ("التوفيق والترجيح",     "شيت 'توفيق النتائج'"),
                 ]))
    body += _sec("31", "الملاحق",
                 "<p>الملحق أ: جدول المقارنات الموسع (5 مقارنات مع تفاصيل التسويات)</p>"
                 "<p>الملحق ب: جداول DCF التفصيلية (5 و10 سنوات)</p>"
                 "<p>الملحق ج: مصفوفة الحساسية الكاملة (مزدوجة)</p>"
                 "<p>الملحق د: مصفوفة المخاطر التفصيلية</p>"
                 "<p>الملحق ه: مصفوفة المعايير الدولية (IVS 2025)</p>"
                 "<p>الملحق و: سجل البيانات والمدخلات الكامل</p>"
                 "<p>الملحق ز: بطاقة الترجيح النهائية</p>"
                 "<p>الملحق ح: تحليل السيناريوهات الثلاثة</p>"
                 "<p>الملحق ط: ملخص أعلى وأفضل استخدام HBU</p>"
                 "<p>الملحق ي: لوحة ملخص النتائج (Dashboard)</p>")
    body += _footer("professional_report")
    return _wrap("تقرير تقييم احترافي | PV-2026-QA-001", body)


# ═══════════════════════════════════════════════════════════════════════════════
# PDF Rendering
# ═══════════════════════════════════════════════════════════════════════════════

def _render_pdf(html: str, out_path: Path) -> dict:
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, encoding="utf-8", mode="w") as f:
        f.write(html)
        tmp = Path(f.name)
    try:
        cmd = [
            str(_CHROME), "--headless=new", "--disable-gpu", "--no-sandbox",
            "--disable-extensions", "--run-all-compositor-stages-before-draw",
            f"--print-to-pdf={out_path}", "--print-to-pdf-no-header",
            tmp.as_uri(),
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=90)
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


def generate_all_pdfs(pdf_out: Path, preview_out: Path) -> dict[str, dict]:
    pdf_out.mkdir(parents=True, exist_ok=True)
    preview_out.mkdir(parents=True, exist_ok=True)
    builders = {
        "traditional_report":  ("تقرير تقييم تقليدي",  _build_traditional),
        "detailed_report":     ("تقرير تقييم تفصيلي",   _build_detailed),
        "professional_report": ("تقرير تقييم احترافي",  _build_professional),
    }
    results = {}
    for key, (title, fn) in builders.items():
        html = fn()
        prev = preview_out / f"{key}_preview.html"
        prev.write_text(html, encoding="utf-8")
        pdf_path = pdf_out / f"{key}.pdf"
        r = _render_pdf(html, pdf_path)
        r["title_ar"] = title
        r["report_key"] = key
        r["preview_html"] = str(prev)
        results[key] = r
    return results
