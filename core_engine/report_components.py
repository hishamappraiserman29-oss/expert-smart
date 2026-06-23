"""
report_components.py — Shared HTML/PDF report generation utilities.

Provides reusable helpers for building Arabic valuation report HTML.
All user-provided values must be passed through html_escape() before
insertion into any template or HTML fragment.

Public API
----------
build_report_base_html(title, body_html, options=None) -> str
render_dashboard_kpi_cards(cards) -> str
render_method_snapshot(methods) -> str
render_watermark(text) -> str
render_disclaimer(report_type) -> str
render_footer_proof_marker() -> str
render_section(title, content, header_style="") -> str
html_escape(value) -> str
get_report_disclaimer(report_kind) -> str
build_professional_valuation_skeleton_html(context) -> str
build_mass_appraisal_dashboard_skeleton_html(context) -> str
"""
from __future__ import annotations

import html
from typing import Any

# ── Watermark text constants ──────────────────────────────────────────────────

WATERMARK_SIMPLE   = "تقرير تقييم آلي مبسط - غير معتمد رسميًا"
WATERMARK_RECEIPT  = "إيصال طلب مراجعة - غير معتمد رسميًا"
WATERMARK_SKELETON = "مسودة تقرير - غير معتمد رسميًا"

# ── Disclaimer text registry ──────────────────────────────────────────────────

_DISCLAIMERS: dict[str, str] = {
    "simple_valuation": (
        "هذا التقرير آلي استرشادي ولا يُعد تقرير تقييم رسمي أو معتمد. "
        "لا يُستخدم أمام البنوك أو المحاكم أو الجهات الرسمية قبل مراجعة "
        "واعتماد خبير التقييم."
    ),
    "expert_request": (
        "هذا المستند يثبت تسجيل طلب مراجعة فقط، ولا يمثل تقرير تقييم معتمدًا. "
        "يتم إصدار النسخة المعتمدة فقط بعد مراجعة الخبير للبيانات والمستندات "
        "والمنهجية."
    ),
    "professional_skeleton": (
        "هذه مسودة هيكل تقرير غير معتمد. لا يتم إصدار تقرير نهائي أو معتمد "
        "إلا بعد اكتمال البيانات ومراجعة الخبير."
    ),
    "mass_appraisal_skeleton": (
        "هذه مسودة هيكل تقرير غير معتمد. لا يتم إصدار تقرير نهائي أو معتمد "
        "إلا بعد اكتمال البيانات ومراجعة الخبير."
    ),
}


def get_report_disclaimer(report_kind: str) -> str:
    """Return the standard disclaimer text for the given report kind.

    Falls back to the professional/skeleton disclaimer for unknown kinds.
    """
    return _DISCLAIMERS.get(report_kind, _DISCLAIMERS["professional_skeleton"])


# ── HTML escape helper ────────────────────────────────────────────────────────

def html_escape(value: Any) -> str:
    """Escape a user-provided value for safe insertion into HTML."""
    return html.escape(str(value) if value is not None else "")


# ── Shared base CSS ───────────────────────────────────────────────────────────

_BASE_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  direction: rtl;
  text-align: right;
  font-family: "Cairo", "Noto Naskh Arabic", "Amiri", "Tahoma",
               "Arial Unicode MS", "Arial", sans-serif;
  font-size: 9.5pt;
  color: #1a1a2e;
  line-height: 1.65;
  background: #ffffff;
}
.page-footer {
  position: fixed;
  bottom: 5mm;
  left: 10mm;
  right: 10mm;
  text-align: center;
  font-size: 7pt;
  color: #bbb;
  border-top: 1px solid #e8e8e8;
  padding-top: 2px;
  z-index: 0;
}
.watermark {
  position: fixed;
  top: 48%;
  left: 50%;
  transform: translate(-50%, -50%) rotate(-28deg);
  font-size: 28px;
  font-weight: 700;
  color: rgba(80, 80, 80, 0.07);
  z-index: 0;
  white-space: nowrap;
  pointer-events: none;
}
.content { position: relative; z-index: 1; }
.hero {
  background: #1f4e78;
  color: #fff;
  padding: 12px 18px 10px;
  margin-bottom: 10px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
.hero-left { flex: 1; }
.hero-right {
  text-align: left;
  font-size: 7.5pt;
  color: #b8d4f0;
  min-width: 150px;
}
.hero-right span { display: block; margin-bottom: 2px; }
.hero-company {
  font-size: 7.5pt;
  font-weight: 700;
  color: #d4af37;
  letter-spacing: 1px;
  margin-bottom: 3px;
}
.hero-title {
  font-size: 14pt;
  font-weight: 700;
  color: #fff;
  margin-bottom: 2px;
}
.hero-sub { font-size: 7.5pt; color: #c0d8f0; margin-bottom: 6px; }
.hero-badge {
  display: inline-block;
  background: #d4af37;
  color: #1a1a2e;
  font-weight: 700;
  font-size: 7.5pt;
  padding: 2px 12px;
  border-radius: 12px;
}
.sec-hdr {
  background: #1f4e78;
  color: #fff;
  font-weight: 700;
  font-size: 9.5pt;
  padding: 4px 12px;
  border-radius: 3px;
  margin-bottom: 7px;
}
.sec-block { margin-bottom: 9px; }
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 7px;
  margin-bottom: 10px;
}
.kpi-card {
  border: 1px solid #d0dff0;
  border-top: 3px solid #1f4e78;
  border-radius: 4px;
  padding: 7px 10px;
  background: #f8faff;
  text-align: center;
}
.kpi-card.warn  { border-top-color: #b43200; background: #fff8f5; border-color: #f0c8b0; }
.kpi-card.green { border-top-color: #1a7a4a; background: #f0fff6; border-color: #90d8b0; }
.kpi-card.gold  { border-top-color: #c8960a; background: #fffdf0; border-color: #e8d070; }
.kpi-card.span2 { grid-column: span 2; }
.kpi-lbl { font-size: 7pt; color: #667; font-weight: 700; margin-bottom: 3px; }
.kpi-val { font-size: 10.5pt; font-weight: 700; color: #1f4e78; }
.kpi-val.warn  { color: #b43200; font-size: 8.5pt; }
.kpi-val.green { color: #1a7a4a; }
.kpi-val.gold  { color: #7a5800; font-size: 9pt; }
.kpi-val.sm    { font-size: 9pt; }
.method-tbl { width: 100%; border-collapse: collapse; font-size: 8pt; }
.method-tbl th {
  background: #dce8f5; color: #1f4e78; font-weight: 700;
  padding: 4px 7px; border: 1px solid #c0d4e8; text-align: center;
}
.method-tbl td {
  padding: 3px 7px; border: 1px solid #e8eaf0;
  vertical-align: top; color: #333;
}
.method-tbl tr:nth-child(even) td { background: #fafcff; }
.m-name  { font-weight: 700; color: #1f4e78; }
.s-ok    { color: #1a7a4a; font-weight: 700; }
.s-no    { color: #b43200; font-weight: 700; }
.s-pnd   { color: #7a5500; font-weight: 700; }
.snap { width: 100%; border-collapse: collapse; }
.snap td {
  padding: 2.5px 7px; border-bottom: 1px solid #f0f0f0;
  font-size: 9pt; vertical-align: top;
}
.snap tr:last-child td { border-bottom: none; }
.snap .lbl { font-weight: 700; color: #557; width: 35%; background: #fafbfd; }
.snap .val { color: #222; }
.concl-box {
  background: #f0f7ff;
  border: 1px solid #b8d0ea;
  border-right: 4px solid #1f4e78;
  border-radius: 4px;
  padding: 9px 13px;
}
.concl-main { font-size: 12pt; font-weight: 700; color: #1f4e78; margin-bottom: 4px; }
.concl-range { font-size: 8.5pt; color: #555; margin-top: 2px; }
.gap-box {
  background: #fff5f5;
  border: 1px solid #eec8b8;
  border-right: 4px solid #b43200;
  border-radius: 4px;
  padding: 9px 13px;
  color: #782828;
  font-size: 9.5pt;
}
.conf-strip {
  background: #fffbf0;
  border: 1px solid #ead8a0;
  border-radius: 3px;
  padding: 4px 12px;
  font-size: 8pt;
  color: #7a5500;
  margin-bottom: 8px;
}
.cta {
  background: #1f4e78;
  color: #fff;
  padding: 9px 14px;
  border-radius: 4px;
  font-size: 9.5pt;
  line-height: 1.7;
  margin-bottom: 9px;
}
.cta-ttl { font-weight: 700; color: #d4af37; font-size: 10pt; margin-bottom: 3px; }
.bul { list-style: none; padding: 0; }
.bul li { font-size: 9pt; color: #444; padding: 1.5px 0; }
.bul li::before { content: "- "; color: #888; }
.bul.doc li::before { color: #1f4e78; }
.notice { font-size: 7.5pt; color: #999; margin-top: 3px; }
.disc-pg { page-break-before: always; padding-top: 12mm; }
.disc-ttl {
  font-size: 12pt; font-weight: 700; color: #782828;
  border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-bottom: 10px;
}
.disc-body { font-size: 9.5pt; color: #782828; line-height: 1.9; }
.skel-ph {
  background: #f5f5f5;
  border: 1px dashed #ccc;
  border-radius: 3px;
  padding: 6px 12px;
  font-size: 8.5pt;
  color: #888;
  margin: 4px 0;
}
.status-badge {
  display: inline-block;
  background: #fff8e6;
  border: 1px solid #e0c060;
  border-radius: 8px;
  padding: 2px 10px;
  font-size: 7.5pt;
  color: #7a5800;
  font-weight: 700;
}
.checklist { list-style: none; padding: 0; margin: 0; }
.checklist li {
  font-size: 8.5pt;
  color: #333;
  padding: 2px 0;
  border-bottom: 1px solid #f0f0f0;
}
.checklist li::before { content: "[ ] "; color: #aaa; }
"""


# ── Core HTML building blocks ────────────────────────────────────────────────

def render_watermark(text: str) -> str:
    """Return HTML for a CSS diagonal watermark."""
    return f'<div class="watermark">{html_escape(text)}</div>'


def render_footer_proof_marker() -> str:
    """Return the fixed footer proof marker div."""
    return (
        '<div class="page-footer">'
        'تم إنشاء هذا المستند بواسطة محرك HTML/PDF'
        '</div>'
    )


def render_section(title: str, content: str, header_style: str = "") -> str:
    """Wrap content in a section block with a coloured blue header."""
    style_attr = f' style="{html_escape(header_style)}"' if header_style else ""
    return (
        f'<div class="sec-block">'
        f'<div class="sec-hdr"{style_attr}>{html_escape(title)}</div>'
        f'{content}'
        f'</div>'
    )


def render_dashboard_kpi_cards(cards: list[dict]) -> str:
    """Return HTML for a row of dashboard KPI cards.

    Each card dict may contain:
      label   (str) — card label
      value   (str) — card value
      variant (str) — CSS modifier: 'warn', 'green', 'gold', or empty
      span2   (bool) — whether the card spans 2 columns
    """
    parts = ['<div class="kpi-grid">']
    for card in cards:
        label   = html_escape(card.get("label", ""))
        value   = html_escape(card.get("value", ""))
        variant = card.get("variant", "")
        span2   = card.get("span2", False)
        classes = "kpi-card"
        if variant:
            classes += f" {html_escape(variant)}"
        if span2:
            classes += " span2"
        parts.append(
            f'<div class="{classes}">'
            f'<div class="kpi-lbl">{label}</div>'
            f'<div class="kpi-val">{value}</div>'
            f'</div>'
        )
    parts.append('</div>')
    return "\n".join(parts)


def render_method_snapshot(methods: list[dict]) -> str:
    """Return HTML for the valuation method snapshot table.

    Each method dict:
      name         (str)
      status       (str)
      status_class (str) — 's-ok', 's-no', or 's-pnd'
      inputs       (str)
      value        (str)
      notes        (str)
    """
    rows = []
    for m in methods:
        name       = html_escape(m.get("name", ""))
        status     = html_escape(m.get("status", ""))
        status_cls = html_escape(m.get("status_class", "s-pnd"))
        inputs_txt = html_escape(m.get("inputs", ""))
        value_txt  = html_escape(m.get("value", ""))
        notes_txt  = html_escape(m.get("notes", ""))
        rows.append(
            f"<tr>"
            f'<td class="m-name">{name}</td>'
            f'<td><span class="{status_cls}">{status}</span></td>'
            f"<td>{inputs_txt}</td>"
            f"<td>{value_txt}</td>"
            f"<td>{notes_txt}</td>"
            f"</tr>"
        )
    header = (
        "<thead><tr>"
        "<th style='width:18%'>الطريقة</th>"
        "<th style='width:12%'>الحالة</th>"
        "<th style='width:26%'>المدخلات المطلوبة</th>"
        "<th style='width:22%'>القيمة</th>"
        "<th style='width:22%'>ملاحظات</th>"
        "</tr></thead>"
    )
    return (
        f'<table class="method-tbl">'
        f"{header}"
        f"<tbody>{''.join(rows)}</tbody>"
        f"</table>"
    )


def render_disclaimer(report_type: str) -> str:
    """Return the disclaimer block HTML for the given report type."""
    text = get_report_disclaimer(report_type)
    return render_section(
        "إخلاء المسؤولية",
        (
            f'<div style="font-size:9pt;color:#782828;line-height:1.75;padding:4px 0;">'
            f'{html_escape(text)}'
            f'</div>'
        ),
        header_style="background:#782828;",
    )


def build_report_base_html(
    title: str,
    body_html: str,
    options: dict | None = None,
) -> str:
    """Build a complete RTL Arabic HTML document.

    options:
      watermark_text (str)  — override watermark text
      extra_css      (str)  — additional CSS to inject after base styles
      font_css       (str)  — @font-face block from cairo_font_css()
    """
    opts          = options or {}
    watermark_txt = opts.get("watermark_text", WATERMARK_SIMPLE)
    extra_css     = opts.get("extra_css", "")
    font_css      = opts.get("font_css", "")
    safe_title    = html_escape(title)

    return (
        '<!DOCTYPE html>'
        '<html lang="ar" dir="rtl">'
        '<head>'
        '<meta charset="utf-8">'
        f'<title>{safe_title}</title>'
        f'<style>{font_css}{_BASE_CSS}{extra_css}</style>'
        '</head>'
        '<body>'
        f'{render_watermark(watermark_txt)}'
        f'{render_footer_proof_marker()}'
        f'<div class="content">{body_html}</div>'
        '</body>'
        '</html>'
    )


# ── Professional valuation skeleton ──────────────────────────────────────────

def build_professional_valuation_skeleton_html(context: dict) -> str:
    """Build the professional valuation report skeleton HTML.

    This is a structural skeleton only — no real valuation data.
    context is reserved for future use; pass {} for now.

    Sections:
      1  Hero header
      2  Dashboard KPI cards
      3  Asset definition
      4  Purpose router summary
      5  Integration matrix summary
      6  Professional requirements checklist
      7  Valuation approaches (sales, income, cost, specialized)
      8  Human approval status
      9  Report disclosure
      10 Output contract summary
      11 Disclaimer
      Watermark + footer
    """
    _ph = '<div class="skel-ph">— (مكان البيانات) —</div>'

    # 1. Hero
    hero = (
        '<div class="hero">'
        '<div class="hero-left">'
        '<div class="hero-company">ALHADY FOR REAL PROPERTY</div>'
        '<div class="hero-title">تقرير تقييم عقاري مهني</div>'
        '<div class="hero-sub">مسودة هيكل تقرير - غير معتمد رسميًا</div>'
        '<div class="hero-badge">مسودة — هيكل فقط</div>'
        '</div>'
        '<div class="hero-right">'
        '<span>تاريخ التقرير: — (مكان البيانات) —</span>'
        '<span>تاريخ التقييم: — (مكان البيانات) —</span>'
        '<span>رقم الطلب: — (مكان البيانات) —</span>'
        '</div>'
        '</div>'
    )

    # 2. KPI cards
    kpi_cards = render_dashboard_kpi_cards([
        {"label": "نوع الأصل",    "value": "— (مكان البيانات) —"},
        {"label": "الغرض",        "value": "— (مكان البيانات) —", "variant": "gold"},
        {"label": "المساحة",      "value": "— (مكان البيانات) —"},
        {"label": "العميل",       "value": "— (مكان البيانات) —"},
        {"label": "تاريخ التقييم","value": "— (مكان البيانات) —"},
        {"label": "حالة التقرير", "value": "مسودة هيكل — لم يُعتمد بعد", "variant": "warn"},
    ])

    # 3. Asset definition
    asset_def = render_section(
        "تعريف الأصل",
        '<table class="snap">'
        '<tr><td class="lbl">نوع الأصل:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '<tr><td class="lbl">العنوان:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '<tr><td class="lbl">حدود الأصل:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '<tr><td class="lbl">المرافق والخدمات:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '<tr><td class="lbl">حقوق الملكية:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '</table>',
    )

    # 4. Purpose router summary
    purpose_router = render_section(
        "ملخص الغرض من التقييم",
        '<table class="snap">'
        '<tr><td class="lbl">الغرض الأساسي:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '<tr><td class="lbl">القيمة المطلوبة:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '<tr><td class="lbl">نوع القيمة:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '<tr><td class="lbl">تاريخ التقييم الفعلي:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '</table>',
    )

    # 5. Integration matrix
    integration = render_section(
        "مصفوفة التكامل المهني",
        '<table class="snap">'
        '<tr><td class="lbl">المعيار المطبق:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '<tr><td class="lbl">متطلبات Basel III/IV:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '<tr><td class="lbl">متطلبات IVSC:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '<tr><td class="lbl">الجهة الطالبة:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '</table>',
    )

    # 6. Professional requirements checklist
    checklist = render_section(
        "قائمة الاشتراطات المهنية",
        '<ul class="checklist">'
        '<li>الاطلاع الميداني على العقار</li>'
        '<li>التحقق من سند الملكية والرسومات</li>'
        '<li>جمع بيانات السوق والمقارنات المعتمدة</li>'
        '<li>التحقق من حالة الترخيص والخدمات</li>'
        '<li>مراجعة عقود الإيجار إن وجدت</li>'
        '<li>التحقق من بيانات التكلفة والإهلاك</li>'
        '<li>اعتماد الخبير على المنهجية المستخدمة</li>'
        '</ul>',
    )

    # 7. Valuation approaches table
    methods = render_method_snapshot([
        {
            "name":         "مقارنة البيوع",
            "status":       "مكان البيانات",
            "status_class": "s-pnd",
            "inputs":       "مقارنات سوقية، سعر متر، تاريخ بيع",
            "value":        "— (مكان البيانات) —",
            "notes":        "لا يُعتمد دون مراجعة الخبير",
        },
        {
            "name":         "رسملة الدخل",
            "status":       "مكان البيانات",
            "status_class": "s-pnd",
            "inputs":       "إيجار، شواغر، معدل رسملة",
            "value":        "— (مكان البيانات) —",
            "notes":        "عند توافر دخل قابل للتحقق",
        },
        {
            "name":         "طريقة التكلفة",
            "status":       "مكان البيانات",
            "status_class": "s-pnd",
            "inputs":       "تكلفة إنشاء، إهلاك، نصيب أرض",
            "value":        "— (مكان البيانات) —",
            "notes":        "اختبار داعم للطرق الأخرى",
        },
        {
            "name":         "الطريقة المتخصصة",
            "status":       "ينطبق / لا ينطبق",
            "status_class": "s-pnd",
            "inputs":       "— حسب طبيعة الأصل —",
            "value":        "— (مكان البيانات) —",
            "notes":        "عند الانطباق فقط",
        },
    ])
    approaches = render_section("طرق التقييم المطبقة", methods)

    # 8. Human approval status
    approval = render_section(
        "حالة اعتماد الخبير",
        '<div class="conf-strip">'
        '<strong>حالة المراجعة:</strong> '
        '<span class="status-badge">قيد المراجعة — لم يُعتمد بعد</span>'
        '&nbsp;&nbsp;'
        '<strong>اسم الخبير:</strong> — (يُحدد بعد المراجعة) —'
        '</div>',
    )

    # 9. Report disclosure
    disclosure = render_section(
        "إفصاح التقرير",
        '<table class="snap">'
        '<tr><td class="lbl">نوع التقرير:</td><td class="val">هيكل مسودة — غير معتمد</td></tr>'
        '<tr><td class="lbl">نطاق المسؤولية:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '<tr><td class="lbl">الاستثناءات:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '<tr><td class="lbl">الافتراضات الجوهرية:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '</table>',
    )

    # 10. Output contract summary
    output_contract = render_section(
        "ملخص عقد المخرجات",
        '<table class="snap">'
        '<tr><td class="lbl">القيمة السوقية النهائية:</td><td class="val">— (تُحدد بعد اعتماد الخبير) —</td></tr>'
        '<tr><td class="lbl">النطاق السعري ±10%:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '<tr><td class="lbl">الأوزان النهائية:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '<tr><td class="lbl">توقيع الخبير:</td><td class="val">— (مكان التوقيع) —</td></tr>'
        '</table>',
    )

    # 11. Disclaimer
    disclaimer = render_disclaimer("professional_skeleton")

    # Detailed disclaimer page 2
    disc2 = (
        '<div class="disc-pg">'
        '<div class="disc-ttl">إخلاء المسؤولية التفصيلي</div>'
        '<div class="disc-body">'
        'هذا المستند هيكل مسودة تقرير تقييم مهني غير معتمد. '
        'لا يُستخدم لأي غرض رسمي أو قانوني أو تمويلي قبل اكتمال البيانات '
        'ومراجعة واعتماد خبير التقييم المختص.<br><br>'
        'لا تعكس الأرقام والمعطيات الواردة في هذا الهيكل قيمة سوقية معتمدة. '
        'الطرق المعروضة هي إطار منهجي مقترح فقط.'
        '</div>'
        '</div>'
    )

    body = (
        hero + kpi_cards + asset_def + purpose_router
        + integration + checklist + approaches + approval
        + disclosure + output_contract + disclaimer + disc2
    )

    return build_report_base_html(
        "هيكل تقرير التقييم المهني",
        body,
        {"watermark_text": WATERMARK_SKELETON},
    )


# ── Mass appraisal skeleton ───────────────────────────────────────────────────

def build_mass_appraisal_dashboard_skeleton_html(context: dict) -> str:
    """Build the mass appraisal portfolio dashboard skeleton HTML.

    This is a structural skeleton only — no real portfolio data.
    context is reserved for future use; pass {} for now.

    Sections:
      1  Hero header
      2  Portfolio summary dashboard (4 KPI cards)
      3  Data ingestion status
      4  Model governance status
      5  Ratio study placeholder
      6  Sales evidence placeholder
      7  Method weighting placeholder
      8  Draft warning
      9  Expert approval CTA
      10 Disclaimer
      Watermark + footer
    """
    # 1. Hero
    hero = (
        '<div class="hero">'
        '<div class="hero-left">'
        '<div class="hero-company">ALHADY FOR REAL PROPERTY</div>'
        '<div class="hero-title">لوحة التقييم الجماعي للمحفظة</div>'
        '<div class="hero-sub">مسودة هيكل لوحة تقييم جماعي - غير معتمد رسميًا</div>'
        '<div class="hero-badge">مسودة — هيكل فقط</div>'
        '</div>'
        '<div class="hero-right">'
        '<span>تاريخ اللوحة: — (مكان البيانات) —</span>'
        '<span>رقم المحفظة: — (مكان البيانات) —</span>'
        '<span>الجهة: — (مكان البيانات) —</span>'
        '</div>'
        '</div>'
    )

    # 2. Portfolio KPI cards
    kpi_cards = render_dashboard_kpi_cards([
        {"label": "عدد الأصول",                   "value": "— (مكان البيانات) —"},
        {"label": "إجمالي القيمة المبدئية",        "value": "— (مكان البيانات) —", "variant": "green"},
        {"label": "متوسط سعر المتر",               "value": "— (مكان البيانات) —", "variant": "gold"},
        {"label": "مؤشر COD (جودة النموذج)",       "value": "— (مكان البيانات) —", "variant": "warn"},
        {"label": "حالة الاستيعاب",                "value": "— (مكان البيانات) —"},
        {"label": "حالة حوكمة النموذج",             "value": "قيد المراجعة — لم يُعتمد", "variant": "warn"},
    ])

    # 3. Data ingestion status
    ingestion = render_section(
        "حالة استيعاب البيانات",
        '<table class="snap">'
        '<tr><td class="lbl">إجمالي الأصول المستوردة:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '<tr><td class="lbl">الأصول الصالحة للتقييم:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '<tr><td class="lbl">الأصول ذات بيانات ناقصة:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '<tr><td class="lbl">تاريخ آخر استيراد:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '<tr><td class="lbl">مصدر البيانات:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '</table>',
    )

    # 4. Model governance status
    governance = render_section(
        "حالة حوكمة النموذج",
        '<div class="conf-strip">'
        '<strong>مرحلة النموذج:</strong> '
        '<span class="status-badge">قيد المعايرة — لم يُعتمد</span>'
        '</div>'
        '<table class="snap" style="margin-top:5px;">'
        '<tr><td class="lbl">خوارزمية التقدير:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '<tr><td class="lbl">تاريخ آخر معايرة:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '<tr><td class="lbl">عدد الشواهد البيعية:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '<tr><td class="lbl">فترة التدريب:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '</table>',
    )

    # 5. Ratio study placeholder
    ratio_study = render_section(
        "دراسة النسبة (Ratio Study)",
        '<table class="snap">'
        '<tr><td class="lbl">متوسط نسبة التقييم (Median Ratio):</td><td class="val">— (مكان البيانات) —</td></tr>'
        '<tr><td class="lbl">معامل التباين (COD):</td><td class="val">— (مكان البيانات) —</td></tr>'
        '<tr><td class="lbl">نسبة السعر للتقييم (PRD):</td><td class="val">— (مكان البيانات) —</td></tr>'
        '<tr><td class="lbl">عدد مقارنات الاختبار:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '<tr><td class="lbl">تقييم الجودة:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '</table>',
    )

    # 6. Sales evidence placeholder
    sales_evidence = render_section(
        "الشواهد البيعية",
        '<div class="skel-ph">'
        '— جدول الشواهد البيعية المستخدمة في معايرة النموذج — (مكان البيانات) —'
        '</div>'
        '<table class="snap" style="margin-top:5px;">'
        '<tr><td class="lbl">إجمالي الصفقات المُحللة:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '<tr><td class="lbl">نطاق الفترة الزمنية:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '<tr><td class="lbl">المناطق الجغرافية:</td><td class="val">— (مكان البيانات) —</td></tr>'
        '</table>',
    )

    # 7. Method weighting placeholder
    method_weights = render_section(
        "أوزان طرق التقييم الجماعي",
        '<table class="method-tbl">'
        '<thead><tr>'
        '<th>الطريقة</th><th>الوزن</th><th>الحالة</th><th>ملاحظات</th>'
        '</tr></thead>'
        '<tbody>'
        '<tr><td class="m-name">نموذج التقييم الجماعي</td>'
        '<td class="s-pnd">— (مكان البيانات) —</td>'
        '<td class="s-pnd">قيد المراجعة</td>'
        '<td>الطريقة الأساسية للتقييم الجماعي</td></tr>'
        '<tr><td class="m-name">طريقة مقارنة البيوع</td>'
        '<td class="s-pnd">— (مكان البيانات) —</td>'
        '<td class="s-pnd">قيد المراجعة</td>'
        '<td>للتحقق وضبط النموذج</td></tr>'
        '<tr><td class="m-name">التوفيق النهائي</td>'
        '<td class="s-pnd">— (مكان البيانات) —</td>'
        '<td class="s-pnd">بانتظار اعتماد الخبير</td>'
        '<td>الأوزان قابلة للتعديل</td></tr>'
        '</tbody>'
        '</table>',
    )

    # 8. Draft warning strip
    draft_warn = (
        '<div class="conf-strip" style="margin-bottom:8px;">'
        '<strong>تحذير:</strong> هذه لوحة مسودة غير معتمدة. '
        'القيم والنتائج الواردة هي تقديرات أولية تحتاج إلى مراجعة وتحقق ميداني '
        'قبل أي استخدام رسمي أو تقنيني.'
        '</div>'
    )

    # 9. Expert approval CTA
    cta = (
        '<div class="cta">'
        '<div class="cta-ttl">الخطوة التالية — اعتماد الخبير</div>'
        'لتحويل هذه المسودة إلى تقرير تقييم جماعي معتمد، يجب مراجعة البيانات '
        'والمنهجية ودراسة النسبة بواسطة خبير التقييم المختص، ثم إصدار النسخة '
        'المعتمدة بعد القبول.'
        '</div>'
    )

    # 10. Disclaimer
    disclaimer = render_disclaimer("mass_appraisal_skeleton")

    # Detailed disclaimer page 2
    disc2 = (
        '<div class="disc-pg">'
        '<div class="disc-ttl">إخلاء المسؤولية التفصيلي</div>'
        '<div class="disc-body">'
        'هذه لوحة هيكل تقييم جماعي مسودة غير معتمدة. لا تُستخدم '
        'لأي غرض ضريبي أو رسمي أو تمويلي قبل اكتمال البيانات ودراسة النسبة '
        'ومراجعة واعتماد خبير التقييم الجماعي المختص.<br><br>'
        'لا تعتمد هذه اللوحة على بيانات سوق حية أو خوارزميات مدرَّبة على '
        'بيانات حقيقية. النموذج يحتاج إلى معايرة ميدانية شاملة.'
        '</div>'
        '</div>'
    )

    body = (
        hero + kpi_cards + ingestion + governance
        + ratio_study + sales_evidence + method_weights
        + draft_warn + cta + disclaimer + disc2
    )

    return build_report_base_html(
        "لوحة التقييم الجماعي للمحفظة",
        body,
        {"watermark_text": WATERMARK_SKELETON},
    )
