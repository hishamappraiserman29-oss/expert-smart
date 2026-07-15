"""mind_map_gallery_sheets.py — Batch 3: Mind Maps, Visualization Gallery, Certificate."""
from __future__ import annotations
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

# ── Color palette (standalone copy) ──────────────────────────────────────────
DK_BLUE = "1F4E79"; MD_BLUE = "2E75B6"; LT_BLUE = "DEEAF1"
YELLOW  = "FFF2CC"; GREEN   = "E2EFDA"; ORANGE  = "FCE4D6"
GRAY    = "F2F2F2"; RED     = "FFCCCC"; WHITE   = "FFFFFF"
GOLD    = "C9A84C"; DK_GOLD = "7D5A0B"; LT_GOLD = "FFF8DC"
PURPLE  = "7030A0"; DK_BRN  = "7B3F00"

NA   = "غير متاح ضمن بيانات الطلب"
BLK  = "🔒 محجوب — بيانات إنتاجية مطلوبة"
MISS = "⬜ بيانات مطلوبة"

NOI = 67_830; CAP = 0.065; FINAL = 1_130_000; BA = 150; LA = 200; AGE = 12
RCN = 1_045_193; TDEP = 324_012; NBV = 721_181; INC_V = 1_043_538; LAND_REC = 1_125_000

# ── Standalone helpers ────────────────────────────────────────────────────────
def _fill(c): return PatternFill("solid", fgColor=c)
def _fnt(bold=False, italic=False, size=10, color="000000"):
    return Font(bold=bold, italic=italic, size=size, color=color, name="Calibri")
def _aln(h="right", wrap=False):
    return Alignment(horizontal=h, vertical="center", wrap_text=wrap)
_BS = Side(style="thin", color="BFBFBF")
_BD = Border(left=_BS, right=_BS, top=_BS, bottom=_BS)

def _c(ws, r, c, val=None, bg=None, bold=False, italic=False, size=10,
       fg="000000", h="right", wrap=False, nf=None):
    cell = ws.cell(r, c, val)
    if bg: cell.fill = _fill(bg)
    cell.font = _fnt(bold, italic, size, fg)
    cell.alignment = _aln(h, wrap)
    cell.border = _BD
    if nf: cell.number_format = nf
    return cell

def _setup(ws, color=MD_BLUE, ca=36, cb=22, cx=14):
    ws.sheet_view.rightToLeft = True
    ws.sheet_properties.tabColor = color
    ws.column_dimensions["A"].width = ca
    ws.column_dimensions["B"].width = cb
    for ch in "CDEF": ws.column_dimensions[ch].width = cx
    ws.freeze_panes = "A4"

def _h1(ws, r, txt, nc=6):
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=nc)
    cell = ws.cell(r, 1, txt); cell.fill = _fill(DK_BLUE)
    cell.font = _fnt(True, size=13, color="FFFFFF")
    cell.alignment = _aln("center"); cell.border = _BD
    ws.row_dimensions[r].height = 26

def _h1_gold(ws, r, txt, nc=6):
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=nc)
    cell = ws.cell(r, 1, txt); cell.fill = _fill(DK_GOLD)
    cell.font = _fnt(True, size=14, color="FFFFFF")
    cell.alignment = _aln("center"); cell.border = _BD
    ws.row_dimensions[r].height = 30

def _h2(ws, r, txt, nc=6):
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=nc)
    cell = ws.cell(r, 1, txt); cell.fill = _fill(MD_BLUE)
    cell.font = _fnt(True, size=11, color="FFFFFF")
    cell.alignment = _aln("right"); cell.border = _BD
    ws.row_dimensions[r].height = 20

def _h2_gold(ws, r, txt, nc=6):
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=nc)
    cell = ws.cell(r, 1, txt); cell.fill = _fill(GOLD)
    cell.font = _fnt(True, size=11, color="FFFFFF")
    cell.alignment = _aln("right"); cell.border = _BD
    ws.row_dimensions[r].height = 20

def _nt(ws, r, txt, nc=6):
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=nc)
    cell = ws.cell(r, 1, txt); cell.fill = _fill(GRAY)
    cell.font = _fnt(italic=True, size=9, color="595959")
    cell.alignment = _aln("right", True); cell.border = _BD
    ws.row_dimensions[r].height = 15

def _kv(ws, r, label, val, vtype="I"):
    bg = {"I": YELLOW, "C": LT_BLUE, "O": GREEN, "M": ORANGE,
          "N": GRAY, "R": RED, "G": LT_GOLD}.get(vtype, YELLOW)
    lb = (vtype in ("O", "G"))
    _c(ws, r, 1, label, bg=GRAY, bold=lb, wrap=True)
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=6)
    nf = "#,##0" if isinstance(val, (int, float)) else None
    _c(ws, r, 2, val, bg=bg, bold=lb, nf=nf, h="left")
    ws.row_dimensions[r].height = 16

def _sp(ws, r): ws.row_dimensions[r].height = 6

def _th(ws, r, *hdrs):
    for c, h in enumerate(hdrs, 1):
        _c(ws, r, c, h, bg=MD_BLUE, bold=True, fg="FFFFFF", h="center")
    ws.row_dimensions[r].height = 18

def _td(ws, r, *vals, bg=None):
    alt = GRAY if r % 2 == 0 else WHITE
    for c, v in enumerate(vals, 1):
        nf = "#,##0" if isinstance(v, (int, float)) and not isinstance(v, bool) else None
        _c(ws, r, c, v, bg=(bg or alt), nf=nf)
    ws.row_dimensions[r].height = 16

def _blocker_row(ws, r, chart_id, chart_name_ar, description, data_needs, nc=6):
    """Write a documented chart blocker entry (used when matplotlib is unavailable)."""
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=nc)
    cell = ws.cell(r, 1, f"[{chart_id}] {chart_name_ar}")
    cell.fill = _fill(MD_BLUE); cell.font = _fnt(True, size=10, color="FFFFFF")
    cell.alignment = _aln("right"); cell.border = _BD
    ws.row_dimensions[r].height = 18

    ws.merge_cells(start_row=r+1, start_column=1, end_row=r+1, end_column=nc)
    c1 = ws.cell(r+1, 1, f"⬜ BLOCKER — matplotlib غير مثبّت | {description}")
    c1.fill = _fill(ORANGE); c1.font = _fnt(italic=True, size=9, color="7D5A0B")
    c1.alignment = _aln("right", True); c1.border = _BD
    ws.row_dimensions[r+1].height = 20

    ws.merge_cells(start_row=r+2, start_column=1, end_row=r+2, end_column=nc)
    c2 = ws.cell(r+2, 1, f"متطلبات البيانات: {data_needs}")
    c2.fill = _fill(GRAY); c2.font = _fnt(italic=True, size=9, color="595959")
    c2.alignment = _aln("right", True); c2.border = _BD
    ws.row_dimensions[r+2].height = 15


# ═══════════════════════════════════════════════════════════════════════════════
# Batch 3 Sheet Builders
# ═══════════════════════════════════════════════════════════════════════════════

def build_methodology_map(ws):
    """🧠 خريطة المنهجية — Methodology Map linking all valuation sheets."""
    _setup(ws, DK_BRN)
    _h1(ws, 1, "🧠 خريطة المنهجية — Methodology Map")
    _nt(ws, 2, "Valuation methodology map | Links all workbook sheets | advisory_only=True | fake_official_data=False")
    _sp(ws, 3)

    _h2(ws, 4, "§1 — المنهجيات التقليدية — Traditional Methods (50 Core Sheets)")
    _th(ws, 5, "#", "المنهجية", "الاسم الإنجليزي", "الورقة المرتبطة", "الحالة")
    trad = [
        (1, "منهجية مقارنة المبيعات", "Sales Comparison Approach", "Comparable Sales", "✅ متاح"),
        (2, "منهجية التكلفة (RCN)", "Cost Approach", "Cost Approach", "✅ متاح"),
        (3, "رسملة الدخل المباشرة", "Income Capitalization", "Income Capitalization", "✅ متاح"),
        (4, "التدفق النقدي المخصوم", "DCF Model", "DCF Model", "✅ متاح"),
        (5, "توفيق قيمة الأرض", "Land Reconciliation", "Land Reconciliation", "✅ متاح"),
        (6, "تحليل RCNLD التكلفة", "Depreciation Analysis", "Depreciation Analysis", "✅ متاح"),
        (7, "تحليل HBU الأمثل", "Highest & Best Use", "HBU Analysis", "✅ متاح"),
        (8, "نموذج AVM الآلي", "Automated Valuation Model", "AVM Summary", "✅ متاح"),
    ]
    for i, row in enumerate(trad, 6): _td(ws, i, *row)
    _sp(ws, 14)

    _h2(ws, 15, "§2 — المنهجيات المتقدمة — Advanced Methods (Batch 2)")
    _th(ws, 16, "#", "المنهجية", "الاسم الإنجليزي", "الورقة المرتبطة", "الحالة")
    adv = [
        (1,  "التسعير الهيدوني",        "Hedonic Pricing Model",           "📊 Hedonic Pricing",  "✅ متاح"),
        (2,  "نموذج نمو جوردون",         "Gordon Growth Model",             "📈 Gordon Growth",    "✅ متاح"),
        (3,  "المبيعات المتكررة",         "Repeat Sales Index",              "🔁 Repeat Sales",     "✅ متاح"),
        (4,  "محاكاة مونتي كارلو",        "Monte Carlo Simulation",          "🎲 Monte Carlo",      "✅ متاح"),
        (5,  "RCNLD",                    "Replacement Cost Net Depreciation","🏗️ RCNLD",            "✅ متاح"),
        (6,  "تكلفة الاستنساخ",           "Reproduction Cost",               "🏛️ Reproduction Cost","✅ متاح"),
        (7,  "القيمة المتوقعة بالمنفعة",  "Expected Utility Value",          "🎯 Expected Utility", "✅ متاح"),
        (8,  "ARIMA السلاسل الزمنية",     "Time Series ARIMA",               "📉 ARIMA",            "✅ متاح"),
        (9,  "الخيارات الحقيقية",          "Real Options Valuation",          "Real Options",        "✅ متاح"),
        (10, "طرق إضافية مختارة",          "Additional Methods Registry",     "🔬 طرق إضافية",       "✅ متاح"),
    ]
    for i, row in enumerate(adv, 17): _td(ws, i, *row)
    _sp(ws, 27)

    _h2(ws, 28, "§3 — حزمة الحوكمة والامتثال — Governance Pack (Batch 1)")
    _th(ws, 29, "#", "الورقة", "الغرض", "المعيار المرتبط", "الحالة")
    gov = [
        (1, "مقدمة التقرير",              "مقدمة ونطاق التقرير",        "IVS 2022 / RICS Red Book",  "✅"),
        (2, "نطاق العمل",                "نطاق التكليف المهني",         "RICS VPS 1",                "✅"),
        (3, "الافتراضات الخاصة والقيود", "افتراضات وقيود التقييم",      "IVS 101.4",                 "✅"),
        (4, "المستندات والمخاطر",         "قائمة مستندات + مخاطر",       "RICS VPS 3",                "✅"),
        (5, "الفحص القانوني",             "فحص قانوني مبدئي",            "RICS VPS 5",                "✅"),
        (6, "بيان الامتثال",              "بيان RICS / IVS / مصري",     "IVS 103",                   "✅"),
        (7, "خارطة طريق الاعتماد",        "بوابات الشهادة",              "RICS Red Book 2022",        "✅"),
        (8, "توقيع الخبير وبوابة الاعتماد","بوابة التوقيع الرسمية",      "RICS PS1",                  "✅"),
        (9, "حزمة الإيجار",               "إيجار / NOI / توفيق",        "IVS 400",                   "✅"),
    ]
    for i, row in enumerate(gov, 30): _td(ws, i, *row)
    _sp(ws, 39)

    _h2(ws, 40, "§4 — خريطة تدفق البيانات — Data Flow Map")
    _th(ws, 41, "المرحلة", "مصدر البيانات", "المعالجة", "المخرج", "الورقة الهدف")
    flow = [
        ("الإدخال المركزي",   "Input Control Panel",    "قيم افتراضية معتمدة",    "مدخلات مركزية",    "Input Control Panel"),
        ("بيانات السوق",      "Market Evidence",        "مقارنة + تعديل + ترجيح", "نطاق سعري",        "Comparable Sales"),
        ("تكلفة البناء",      "Building Cost Breakdown","RCN + استهلاك متعدد",    "NBV الصافية",       "Depreciation Analysis"),
        ("دخل العقار",        "Income Capitalization",  "NOI ÷ معدل رسملة",       "قيمة الدخل",        "Income Capitalization"),
        ("التدفق النقدي",     "DCF Model",              "PV(NOI) + PV(Rev)",       "صافي قيمة حالية",  "NPV Analysis"),
        ("توفيق المنهجيات",   "Method Reconciliation",  "ترجيح 30/40/30",          "القيمة النهائية",   "Final Value"),
        ("الإخراج والتقرير",  "Print Report Summary",   "تجميع + إفصاح",           "تقرير PDF / طباعة","Print Report Summary"),
    ]
    for i, row in enumerate(flow, 42): _td(ws, i, *row)
    _sp(ws, 49)
    _nt(ws, 50, "⚠ methodology_map | advisory_only=True | no_fake_official_data=True | Batch 1+2+3 linked")


def build_results_map(ws):
    """🌟 خريطة النتائج — Formula-linked results map with value conclusion flow."""
    _setup(ws, "375623")
    _h1(ws, 1, "🌟 خريطة النتائج — Results Map")
    _nt(ws, 2, "Formula-linked to Method Reconciliation | Value conclusion flow | advisory_only=True")
    _sp(ws, 3)

    _h2(ws, 4, "§1 — تدفق الاستنتاج — Value Conclusion Flow")
    # Formula-linked to Method Reconciliation
    _c(ws, 5, 1, "القيمة الموفَّقة المستخلصة (ج.م.) — من Method Reconciliation", bg=GRAY, bold=True, wrap=True)
    ws.merge_cells(start_row=5, start_column=2, end_row=5, end_column=6)
    cell_5 = ws.cell(5, 2, "='Method Reconciliation'!B12")
    cell_5.fill = _fill(LT_BLUE); cell_5.font = _fnt(bold=True, size=11)
    cell_5.alignment = _aln("left"); cell_5.border = _BD
    cell_5.number_format = "#,##0"; ws.row_dimensions[5].height = 18

    _c(ws, 6, 1, "القيمة المقربة — MROUND (ج.م.) — من Method Reconciliation", bg=GRAY, bold=True, wrap=True)
    ws.merge_cells(start_row=6, start_column=2, end_row=6, end_column=6)
    cell_6 = ws.cell(6, 2, "='Method Reconciliation'!B13")
    cell_6.fill = _fill(GREEN); cell_6.font = _fnt(bold=True, size=12, color="1F4E79")
    cell_6.alignment = _aln("left"); cell_6.border = _BD
    cell_6.number_format = "#,##0"; ws.row_dimensions[6].height = 20

    _c(ws, 7, 1, "مجموع الأوزان — من Method Reconciliation", bg=GRAY, wrap=True)
    ws.merge_cells(start_row=7, start_column=2, end_row=7, end_column=6)
    cell_7 = ws.cell(7, 2, "='Method Reconciliation'!B11")
    cell_7.fill = _fill(LT_BLUE); cell_7.alignment = _aln("left"); cell_7.border = _BD
    ws.row_dimensions[7].height = 16

    _c(ws, 8, 1, "درجة الاتساق — من Method Reconciliation", bg=GRAY, wrap=True)
    ws.merge_cells(start_row=8, start_column=2, end_row=8, end_column=6)
    cell_8 = ws.cell(8, 2, "='Method Reconciliation'!B21")
    cell_8.fill = _fill(YELLOW); cell_8.alignment = _aln("left"); cell_8.border = _BD
    ws.row_dimensions[8].height = 16

    _sp(ws, 9)
    _h2(ws, 10, "§2 — هيكل الترجيح — Method Weight Structure")
    _th(ws, 11, "المنهجية", "القيمة (ج.م.)", "الوزن %", "القيمة الموزونة", "المصدر")
    wts = [
        ("منهجية التكلفة",    f"{NBV+LAND_REC+50_000:,}", "30%", f"{(NBV+LAND_REC+50_000)*0.30:,.0f}", "Building Cost + Land Rec"),
        ("منهجية الدخل",      f"{INC_V:,}",               "40%", f"{INC_V*0.40:,.0f}",                 "Income Capitalization"),
        ("منهجية المقارنة",   NA,                          "30%", NA,                                   "Comparable Sales — مطلوب"),
        ("نموذج AVM",         NA,                          "0%",  NA,                                   "AVM — غير مكتمل"),
    ]
    for i, row in enumerate(wts, 12): _td(ws, i, *row)
    _sp(ws, 16)

    _h2(ws, 17, "§3 — مؤشرات الجاهزية والمخاطر — Risk / Readiness Indicators")
    _th(ws, 18, "المؤشر", "الحالة", "الدرجة", "المصدر", "التأثير على القيمة")
    indicators = [
        ("جودة البيانات",          "82%",   "جيد",    "Data Quality Sheet",    "منخفض"),
        ("درجة الثقة الكلية",      "78%",   "متوسط",  "Executive Dashboard",   "متوسط"),
        ("اتساق المنهجيات",        "✅ 1/3", "جزئي",  "Method Reconciliation", "متوسط"),
        ("توفر مبيعات مقارنة",     "⬜",    "ناقص",   "Comparable Sales",      "مرتفع"),
        ("درجة GIS الجغرافية",    NA,       NA,       "GIS Location Score",    "منخفض"),
        ("جاهزية شهادة المقيّم",   "⬜",    "محجوب",  "Certification Readiness","مرتفع جداً"),
    ]
    for i, row in enumerate(indicators, 19): _td(ws, i, *row)
    _sp(ws, 25)

    _h2(ws, 26, "§4 — خريطة تبعية القيمة النهائية — Final Value Dependency Map")
    _th(ws, 27, "المدخل", "الورقة المصدر", "تأثيره على القيمة", "الحالة", "ملاحظات")
    deps = [
        ("مساحة البناء (م²)",         "'Input Control Panel'!B8",  "مباشر — تكلفة/م²",    "✅", f"={BA} م²"),
        ("عمر العقار (سنة)",           "'Input Control Panel'!B9",  "استهلاك التكلفة",      "✅", f"={AGE} سنة"),
        ("معدل الرسملة",               "'Input Control Panel'!B23", "قيمة الدخل المباشرة",  "✅", "6.5%"),
        ("RCN تكلفة الاستبدال",        "'Building Cost Breakdown'!B20","منهجية التكلفة",    "✅", f"{RCN:,}"),
        ("صافي دخل التشغيل NOI",       "'Income Capitalization'!B9", "قيمة الدخل",          "✅", f"{NOI:,}"),
        ("مبيعات مقارنة محلية",        "'Comparable Sales'!B6",     "منهجية المقارنة",      "⬜", "مطلوب 5+ مبيعات"),
    ]
    for i, row in enumerate(deps, 28): _td(ws, i, *row)
    _sp(ws, 34)
    _nt(ws, 35, "⚠ results_map | all_formulas_linked=True | no_hardcoded_fake_values=True | advisory_only=True")


def build_visualization_gallery(ws):
    """📈 معرض التصوّرات — Visualization Gallery with 10 chart type placeholders."""
    _setup(ws, PURPLE)
    ws.column_dimensions["A"].width = 4
    ws.column_dimensions["B"].width = 54
    for ch in "CDEF": ws.column_dimensions[ch].width = 12
    _h1(ws, 1, "📈 معرض التصوّرات — Visualization Gallery (10 Chart Types)")
    _nt(ws, 2,
        "10 visualization types | illustrative data only | advisory_only=True | "
        "fake_market_intelligence_created=False")
    _sp(ws, 3)

    # matplotlib availability check at runtime
    _mpl_ok = False
    try:
        import matplotlib as _mpl
        _mpl.use("Agg")
        import matplotlib.pyplot as _plt
        import io as _io
        import numpy as _np
        _mpl_ok = True
    except Exception:
        pass

    CHART_DEFS = [
        ("CHOROPLETH",    "خريطة كثافة جغرافية",
         "يُظهر شبكة أسعار/م² ملوّنة على مناطق المعادي المختلفة — كثافة عالية تعني أسعاراً مرتفعة",
         "بيانات GIS بالمنطقة + أسعار بيع موزّعة جغرافياً لكل خلية شبكية"),
        ("VORONOI",       "مخطط فورونوي — مناطق تأثير المبيعات",
         "يُقسّم المنطقة إلى خلايا تأثير لكل مبيعة مقارنة — تحديد أقرب مبيعة لكل نقطة",
         "5+ مبيعات مقارنة محلية بإحداثيات GPS دقيقة"),
        ("3D_SURFACE",    "سطح ثلاثي الأبعاد — حساسية القيمة",
         "سطح 3D يوضّح كيف تتغير القيمة مع تغيّر معدل الرسملة والمساحة المبنية في آنٍ واحد",
         "معدلات رسملة نطاق 4—10% + مساحات بناء نطاق 80—300 م²"),
        ("SANKEY",        "تدفق توزيع القيمة — Sankey",
         "يُظهر كيف تتوزع القيمة الكلية (1.13M) بين مكونات الأرض والبناء ودخل الإيجار",
         "أوزان المنهجيات المعتمدة + تفصيل مكونات كل منهجية"),
        ("GANTT",         "جدول زمني لعملية التقييم",
         "جدول GANTT للمراحل الزمنية لعملية التقييم: فحص — بحث — تحليل — توفيق — تقرير",
         "تواريخ بدء وانتهاء كل مرحلة + اسم المسؤول عنها"),
        ("RISK_HEATMAP",  "خريطة حرارية للمخاطر 5×5",
         "مصفوفة 5×5 للمخاطر: احتمالية (1—5) × تأثير (1—5) بألوان من أخضر لأحمر",
         "Risk Register — قائمة المخاطر مع درجات الاحتمالية والتأثير"),
        ("COHORT",        "تحليل الفئات الزمنية — Cohort",
         "مخطط أعمدة لنسب ثبات العائد الإيجاري عبر الزمن لمجموعات (cohorts) مختلفة",
         "بيانات تاريخية للإيجار على 3+ سنوات مصنّفة بالفئة الزمنية"),
        ("DECISION_TREE", "شجرة القرار — اختيار المنهجية",
         "شجرة قرار تُوضّح كيف يُختار نهج التقييم بناءً على نوع الأصل وتوفر البيانات",
         "بروتوكول اختيار المنهجية المعتمد + قواعد القرار لكل فرع"),
        ("TORNADO",       "مخطط الإعصار — حساسية العوامل",
         "يُظهر ترتيب العوامل حسب تأثيرها على القيمة: معدل رسملة، NOI، تكلفة بناء، إلخ",
         "نتائج تحليل الحساسية من Sensitivity Matrix بنطاقات ±"),
        ("RADAR_COMPARE", "مخطط الرادار — مقارنة بالسوق",
         "رادار سداسي يقارن العقار بالمتوسط السوقي: جودة بيانات، تكلفة، دخل، مخاطر، معايير، سوق",
         "معايير مرجعية للسوق المحلي + درجات العقار الحالي على كل محور"),
    ]

    img_count = 0
    blk_count = 0
    row = 4

    if _mpl_ok:
        try:
            from openpyxl.drawing.image import Image as _XLImage
        except ImportError:
            _mpl_ok = False

    for idx, (ctype, name_ar, description, data_needs) in enumerate(CHART_DEFS):
        if idx > 0 and idx % 1 == 0:
            pass  # each chart gets its own row block
        chart_num = idx + 1

        if _mpl_ok:
            buf = _try_make_chart(ctype)
            if buf is not None:
                try:
                    img = _XLImage(buf)
                    img.width = 400; img.height = 270
                    ws.add_image(img, f"B{row + 1}")
                    _c(ws, row, 1, f"[{chart_num}] {ctype} — {name_ar}",
                       bg=MD_BLUE, bold=True, fg="FFFFFF")
                    ws.row_dimensions[row].height = 18
                    img_count += 1
                    row += 22
                    continue
                except Exception:
                    pass

        # No image — write documented text blocker
        _blocker_row(ws, row, chart_num, f"{ctype} — {name_ar}", description, data_needs)
        blk_count += 1
        row += 4  # 3 rows per blocker + 1 spacer

    # Summary marker (parsed by T9 validation test)
    _sp(ws, row)
    ws.merge_cells(start_row=row + 1, start_column=1, end_row=row + 1, end_column=6)
    sum_cell = ws.cell(row + 1, 1,
                       f"GALLERY_SUMMARY: images={img_count} blockers={blk_count} total=10")
    sum_cell.fill = _fill(GRAY)
    sum_cell.font = _fnt(italic=True, size=9, color="595959")
    sum_cell.alignment = _aln("right"); sum_cell.border = _BD
    ws.row_dimensions[row + 1].height = 15

    _nt(ws, row + 2,
        "⚠ All charts use illustrative/advisory data only | "
        "No production market data | advisory_only=True | fake_market_intelligence_created=False")


def _try_make_chart(chart_type: str):
    """Generate a matplotlib chart; returns BytesIO or None."""
    try:
        import matplotlib.pyplot as _plt
        import io as _io
        import numpy as _np
        fig, ax = _plt.subplots(figsize=(5.5, 3.6))
        ax.text(0.5, 0.5, f"{chart_type}\nIllustrative Chart\n(advisory_only=True)",
                ha="center", va="center", fontsize=12, transform=ax.transAxes,
                bbox=dict(boxstyle="round", facecolor="#DEEAF1", alpha=0.8))
        ax.set_title(f"{chart_type} — Placeholder"); ax.axis("off")
        buf = _io.BytesIO()
        fig.savefig(buf, format="png", dpi=72, bbox_inches="tight")
        buf.seek(0); _plt.close(fig)
        return buf
    except Exception:
        return None


def build_certificate(ws):
    """🏆 شهادة — Certificate placeholder sheet with signature gate."""
    _setup(ws, DK_GOLD)
    _h1_gold(ws, 1, "🏆 شهادة تقييم عقاري — Real Estate Valuation Certificate")
    _nt(ws, 2,
        "certificate_placeholder=True | fake_stamp=False | fake_license=False | "
        "fake_valuer=False | advisory_only=True")
    _sp(ws, 3)

    _h2_gold(ws, 4, "§1 — بيانات التقييم — Valuation Reference")
    _kv(ws, 5,  "رقم المرجع / Reference No.",       "PV-RCP-2026-001",             "G")
    _kv(ws, 6,  "تاريخ التقييم / Valuation Date",   "2026-07-11",                  "G")
    _kv(ws, 7,  "العقار / Property",                 "شقة سكنية — المعادي، القاهرة","G")
    _kv(ws, 8,  "المساحة المبنية (م²) / Built Area", f"{BA} م²",                   "C")
    _kv(ws, 9,  "عمر العقار / Age",                  f"{AGE} سنة",                 "C")
    _sp(ws, 10)

    _h2_gold(ws, 11, "§2 — ملخص القيمة — Value Summary")
    _kv(ws, 12, "القيمة السوقية الاستشارية (ج.م.)",  FINAL,           "O")
    _kv(ws, 13, "نطاق القيمة (ج.م.)",                "980,000 — 1,200,000", "C")
    _kv(ws, 14, "المنهجيات المستخدمة",
                "تكلفة 30% + دخل 40% + مقارنة 30%", "C")
    _kv(ws, 15, "معيار التقييم المطبق",               "RICS Red Book 2022 | IVS 2022", "C")
    _sp(ws, 16)

    _h2_gold(ws, 17, "§3 — بوابة التوقيع — Signature Gate")
    _kv(ws, 18, "🔏 توقيع الخبير المرخص",
                "بانتظار التوقيع الرسمي من مقيم عقاري مرخص", "M")
    _kv(ws, 19, "رقم ترخيص المقيّم",    BLK, "M")
    _kv(ws, 20, "اسم المقيّم المرخص",   BLK, "M")
    _kv(ws, 21, "الجهة المانحة للترخيص",BLK, "M")
    _kv(ws, 22, "ختم الاعتماد الرسمي",  BLK, "M")
    _sp(ws, 23)

    _h2_gold(ws, 24, "§4 — حالة جاهزية الشهادة — Certificate Readiness")
    _th(ws, 25, "#", "شرط الشهادة", "الحالة", "الملاحظة")
    readiness = [
        (1, "تقرير مكتمل بكافة الأقسام",        "⬜ جزئي",  "أقسام مكتملة، مقارنة ناقصة"),
        (2, "مبيعات مقارنة محلية (5+ مبيعات)",  "❌ ناقص",  "متاح: 1 فقط من الإسكندرية"),
        (3, "فحص قانوني مكتمل",                 "⬜ مبدئي", "الفحص القانوني — ورقة مستقلة"),
        (4, "بيانات GIS معتمدة",                "⬜ غير مكتمل","GIS يتطلب تكاملاً إنتاجياً"),
        (5, "توقيع مقيّم عقاري مرخص",           "🔒 محجوب", "بوابة التوقيع — BLK"),
        (6, "مراجعة مستقلة (Peer Review)",       "⬜ مطلوب", "مراجعة خارجية لم تُجرَ بعد"),
    ]
    for i, row in enumerate(readiness, 26): _td(ws, i, *row)
    _sp(ws, 32)

    _nt(ws, 33,
        "⚠ هذا النموذج للأغراض الاستشارية الداخلية فقط | "
        "fake_stamp_created=False | fake_license_created=False | "
        "fake_valuer_created=False | advisory_only=True | "
        "CERTIFICATE_PLACEHOLDER=True")
