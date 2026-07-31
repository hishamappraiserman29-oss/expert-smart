"""advanced_methods_sheets.py — Batch 2: Advanced Valuation Method sheets.
10 new sheet builders for the professional valuation Excel reference parity workbook.
advisory_only=True | fake_sources_created=False | fake_production_data_created=False
"""
from __future__ import annotations
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

# ── Style helpers (standalone — no import from main builder) ──────────────────
DK_BLUE = "1F4E79"; MD_BLUE = "2E75B6"; LT_BLUE = "DEEAF1"
YELLOW  = "FFF2CC"; GREEN   = "E2EFDA"; ORANGE  = "FCE4D6"
GRAY    = "F2F2F2"; RED     = "FFCCCC"; WHITE   = "FFFFFF"

NA   = "غير متاح ضمن بيانات الطلب"
BLK  = "🔒 محجوب — بيانات إنتاجية مطلوبة"
MISS = "⬜ بيانات مطلوبة"

NOI = 67_830; CAP = 0.065; FINAL = 1_130_000; BA = 150; LA = 200; AGE = 12
RCN = 1_045_193; TDEP = 324_012; NBV = 721_181; INC_V = 1_043_538
LAND_REC = 1_125_000

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
    cell = ws.cell(r, 1, txt)
    cell.fill = _fill(DK_BLUE); cell.font = _fnt(True, size=13, color="FFFFFF")
    cell.alignment = _aln("center"); cell.border = _BD
    ws.row_dimensions[r].height = 26

def _h2(ws, r, txt, nc=6):
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=nc)
    cell = ws.cell(r, 1, txt)
    cell.fill = _fill(MD_BLUE); cell.font = _fnt(True, size=11, color="FFFFFF")
    cell.alignment = _aln("right"); cell.border = _BD
    ws.row_dimensions[r].height = 20

def _nt(ws, r, txt, nc=6):
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=nc)
    cell = ws.cell(r, 1, txt)
    cell.fill = _fill(GRAY); cell.font = _fnt(italic=True, size=9, color="595959")
    cell.alignment = _aln("right", True); cell.border = _BD
    ws.row_dimensions[r].height = 15

def _kv(ws, r, label, val, vtype="I"):
    bg = {"I": YELLOW, "C": LT_BLUE, "O": GREEN, "M": ORANGE, "N": GRAY, "R": RED}.get(vtype, YELLOW)
    lb = (vtype == "O")
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


# ── 10 Builder Functions ──────────────────────────────────────────────────────

def build_hedonic_pricing(ws):
    _setup(ws, "4472C4")
    _h1(ws, 1, "Hedonic Pricing — نموذج التسعير الهيدوني")
    _nt(ws, 2, "Hedonic regression: Value = f(size, location, quality, age...) | Blocked: regression engine required")
    _sp(ws, 3); _h2(ws, 4, "§1 — المتغيرات والمحركات السعرية — Price Driver Variables")
    _th(ws, 5, "المتغير", "قيمة الموضوع", "المعامل β (مقدَّر)", "الأثر السعري (ج.م.)", "مصدر البيانات")
    _td(ws, 6,  "المساحة المبنية (م²)",        "='Input Control Panel'!B8", NA, NA, "Input Control Panel")
    _td(ws, 7,  "المنطقة الجغرافية",            "المعادي",                   NA, NA, "Location Data")
    _td(ws, 8,  "جودة التشطيب (1-5)",           4,                           NA, NA, "Property Data")
    _td(ws, 9,  "عمر العقار (سنة)",              "='Input Control Panel'!B9", NA, NA, "Input Control Panel")
    _td(ws, 10, "الطابق",                        NA,                          NA, NA, NA)
    _td(ws, 11, "قرب المواصلات (م)",             NA,                          NA, NA, "GIS Location Score")
    _td(ws, 12, "قرب المراكز التجارية (م)",      NA,                          NA, NA, "GIS Location Score")
    _td(ws, 13, "خط العرض / الطول",              "29.9553 / 31.2565",         NA, NA, "Location Data")
    _sp(ws, 14); _h2(ws, 15, "§2 — هيكل الصيغة — Formula Structure")
    _kv(ws, 16, "صيغة النموذج الهيدوني", "Value = β₀ + β₁·Size + β₂·Location + β₃·Quality + ... + ε", "C")
    _kv(ws, 17, "Intercept β₀",           NA, "M")
    _kv(ws, 18, "R² (معامل التحديد)",     NA, "M")
    _kv(ws, 19, "RMSE",                   NA, "M")
    _kv(ws, 20, "القيمة المتوقعة — هيدوني (ج.م.)", NA, "M")
    _kv(ws, 21, "NOI المرجعي (للمقارنة) (ج.م.)",  "='Income Capitalization'!B9", "C")
    _sp(ws, 22); _h2(ws, 23, "§3 — الافتراضات والقيود")
    _kv(ws, 24, "افتراض الخطية",     "العلاقة بين المتغيرات والسعر خطية — قابل للاختبار", "I")
    _kv(ws, 25, "حجم العينة المطلوب", "لا يقل عن 50 صفقة معتمدة في السوق المحلية", "I")
    _kv(ws, 26, "توفر البيانات",      "بيانات المبيعات المقارنة المحلية غير متوفرة حالياً", "R")
    _sp(ws, 27); _h2(ws, 28, "§4 — الحالة والمخرجات")
    _kv(ws, 29, "حالة النموذج",      BLK, "R")
    _kv(ws, 30, "الإجراء المطلوب",   "توفير 50+ مبيعة محلية مقارنة + تشغيل محرك الانحدار", "M")
    _nt(ws, 31, "⚠ advisory_only=True | fake_regression_created=False | بيانات انحدار حقيقية مطلوبة")


def build_gordon_growth(ws):
    _setup(ws, "375623")
    _h1(ws, 1, "Gordon Growth — نموذج نمو Gordon")
    _nt(ws, 2, "GGM: Value = NOI₁ / (Discount Rate − Growth Rate) | Income approach constant-growth variant")
    _sp(ws, 3); _h2(ws, 4, "§1 — المدخلات — Inputs")
    _kv(ws, 5, "NOI السنة الأولى (ج.م.)",       "='Income Capitalization'!B9",  "I")
    _kv(ws, 6, "معدل النمو السنوي الدائم g",     "='Input Control Panel'!B26",   "I")
    _kv(ws, 7, "معدل الرسملة — Cap Rate",        "='Input Control Panel'!B23",   "I")
    _kv(ws, 8, "معدل الخصم — r (المطلوب)",       "='Input Control Panel'!B24",   "I")
    _sp(ws, 9); _h2(ws, 10, "§2 — الحساب — Calculation")
    _kv(ws, 11, "التحقق: r > g (شرط صحة النموذج)", "=IF(B8>B6,\"✅ صحيح\",\"⚠ r ≤ g — النموذج غير صالح\")", "C")
    _kv(ws, 12, "معدل الرسملة المعدَّل (r − g)",    "=B8-B6",  "C")
    _kv(ws, 13, "قيمة GGM = NOI₁ / (r − g) (ج.م.)",
        "=IF(B8>B6,B5/(B8-B6),\"غير قابل للحساب — r ≤ g\")", "O")
    _kv(ws, 14, "مقارنة: Direct Cap (NOI/Cap Rate) (ج.م.)", f"={NOI}/{CAP}", "C")
    _sp(ws, 15); _h2(ws, 16, "§3 — تحليل الحساسية — Sensitivity")
    _th(ws, 17, "معدل النمو g", "r = 10%", "r = 12%", "r = 14%")
    for i, g in enumerate([0.01, 0.02, 0.03, 0.04, 0.05], 18):
        v = [round(NOI/(r-g)) if r > g else "غير صالح" for r in [0.10, 0.12, 0.14]]
        _td(ws, i, f"{g*100:.0f}%", v[0], v[1], v[2])
    _sp(ws, 23); _h2(ws, 24, "§4 — الافتراضات والقيود")
    _kv(ws, 25, "افتراض النمو الثابت",  "النمو الدائم ثابت — قد لا يعكس دورات السوق الحقيقية", "I")
    _kv(ws, 26, "صلاحية التطبيق",       "يصلح للعقارات ذات دخل مستقر وطويل الأمد فقط", "I")
    _kv(ws, 27, "حساسية عالية",         "فارق ±1٪ في (r−g) يغيّر القيمة بشكل جوهري", "M")
    _nt(ws, 28, "⚠ advisory_only=True | Input Control Panel هو مصدر البيانات المرجعية")


def build_repeat_sales(ws):
    _setup(ws, "00B050")
    _h1(ws, 1, "Repeat Sales — منهجية المبيعات المتكررة")
    _nt(ws, 2, "Case-Shiller style: ΔPrice from same property sold twice | Blocked: repeated transactions required")
    _sp(ws, 3); _h2(ws, 4, "§1 — هيكل البيانات المطلوب — Required Data Structure")
    _th(ws, 5, "#", "رقم العقار", "البيع الأول (ج.م.)", "تاريخ البيع الأول", "البيع الثاني (ج.م.)", "تاريخ البيع الثاني")
    for i in range(1, 6):
        _td(ws, i+5, i, NA, NA, NA, NA, NA)
    _sp(ws, 11); _h2(ws, 12, "§2 — حساب المؤشر — Index Calculation")
    _th(ws, 13, "#", "رقم العقار", "نسبة التغير %", "الفترة (شهر)", "معدل النمو السنوي")
    for i in range(1, 6):
        _td(ws, i+13, i, NA, NA, NA, NA)
    _sp(ws, 19); _h2(ws, 20, "§3 — نتائج المؤشر")
    _kv(ws, 21, "عدد العقارات المتاحة ببيعتين",
        "=COUNTA(C6:C10)-COUNTBLANK(C6:C10)", "C")
    _kv(ws, 22, "مؤشر السوق (نسبة التغير الكلية)",     NA, "M")
    _kv(ws, 23, "معدل نمو السوق السنوي المستخلص",        NA, "M")
    _kv(ws, 24, "تعديل القيمة المطبق على الموضوع (ج.م.)", NA, "M")
    _sp(ws, 25); _h2(ws, 26, "§4 — الافتراضات والقيود")
    _kv(ws, 27, "شرط التطابق",    "نفس العقار يُباع مرتين — نادر في السوق المحلي", "I")
    _kv(ws, 28, "تحيز الاختيار",  "قد يقتصر على عقارات ذات جودة معينة — selection bias", "I")
    _kv(ws, 29, "توفر البيانات",   "بيانات المبيعات المتكررة المحلية غير متوفرة حالياً", "R")
    _sp(ws, 30); _h2(ws, 31, "§5 — الحالة")
    _kv(ws, 32, "حالة النموذج",    BLK, "R")
    _kv(ws, 33, "الإجراء المطلوب", "توفير قاعدة بيانات مبيعات عقارات متكررة محلية", "M")
    _nt(ws, 34, "⚠ fake_repeat_sales_created=False | بيانات حقيقية من السوق مطلوبة")


def build_monte_carlo(ws):
    _setup(ws, "C00000")
    _h1(ws, 1, "Monte Carlo — محاكاة مونتي كارلو")
    _nt(ws, 2, "Structural framework: Low/Base/High inputs → simulated value range | No random fake production data")
    _sp(ws, 3); _h2(ws, 4, "§1 — جدول الافتراضات — Assumptions Table")
    _th(ws, 5, "المتغير", "منخفض", "أساسي", "مرتفع", "التوزيع", "المصدر")
    _td(ws, 6,  "NOI (ج.م.)",              round(NOI*0.85), NOI,  round(NOI*1.15), "طبيعي",  "Income Capitalization")
    _td(ws, 7,  "معدل الرسملة %",          5.5,             6.5,  8.0,             "ثلاثي",  "Input Control Panel")
    _td(ws, 8,  "معدل نمو NOI %",          0,               3,    5,               "ثلاثي",  "Input Control Panel")
    _td(ws, 9,  "معدل الشغور %",           3,               5,    10,              "موحد",   "Rent Comparables")
    _td(ws, 10, "تكلفة الصيانة السنوية %", 1,               2,    4,               "ثلاثي",  "Site Improvements")
    _td(ws, 11, "تغيّر سعر إعادة البيع %", -10,             5,    15,              "ثلاثي",  "Market Evidence")
    _sp(ws, 12); _h2(ws, 13, "§2 — نطاقات القيمة المحاكاة — Simulated Value Ranges")
    _th(ws, 14, "السيناريو", "الافتراض", "NOI (ج.م.)", "Cap Rate", "القيمة المحاكاة (ج.م.)")
    _td(ws, 15, "P10 — مئين عاشر",  "منخفض",   round(NOI*0.85), 0.08,  round(NOI*0.85/0.08))
    _td(ws, 16, "P25 — ربع أول",    "متشائم",  round(NOI*0.90), 0.075, round(NOI*0.90/0.075))
    _td(ws, 17, "P50 — وسيط",       "أساسي",   NOI,             0.065, round(NOI/0.065))
    _td(ws, 18, "P75 — ربع ثالث",   "متفائل",  round(NOI*1.08), 0.060, round(NOI*1.08/0.060))
    _td(ws, 19, "P90 — مئين تسعون", "مرتفع",   round(NOI*1.15), 0.055, round(NOI*1.15/0.055))
    _sp(ws, 20); _h2(ws, 21, "§3 — الإحصاءات التلخيصية — Summary Statistics")
    _kv(ws, 22, "متوسط القيم المحاكاة P50 (ج.م.)",      "=AVERAGE(E15:E19)", "C")
    _kv(ws, 23, "نطاق 80٪ الثقة P10—P90 (ج.م.)",
        f"{round(NOI*0.85/0.08):,} — {round(NOI*1.15/0.055):,}", "C")
    _kv(ws, 24, "الانحراف المعياري المحاكاة (ج.م.)",     NA, "M")
    _kv(ws, 25, "احتمالية القيمة ≥ 1,000,000 ج.م.",      NA, "M")
    _sp(ws, 26); _h2(ws, 27, "§4 — القيود")
    _kv(ws, 28, "طبيعة الهيكل",     "إطار بنيوي — لا محاكاة عشوائية فعلية في الملف", "I")
    _kv(ws, 29, "متطلب التشغيل",    "Python / @RISK / Crystal Ball لـ N=10,000 سيناريو", "M")
    _kv(ws, 30, "بيانات مزورة",     "لا — fake_production_data_created=False", "C")
    _nt(ws, 31, "⚠ هذا إطار بنيوي فقط | التوزيعات والمحاكاة الفعلية تتطلب محرك إحصائي خارجي")


def build_rcnld(ws):
    _setup(ws, "C00000")
    _h1(ws, 1, "RCNLD — تكلفة الاستبدال ناقص الاستهلاك")
    _nt(ws, 2, "RCNLD = RCN - Accumulated Depreciation (Physical + Functional + External) | Links to Cost sheets")
    _sp(ws, 3); _h2(ws, 4, "§1 — تكلفة الاستبدال الجديدة — RCN")
    _kv(ws, 5,  "RCN من Building Cost Breakdown (ج.م.)",  "='Building Cost Breakdown'!B20", "I")
    _kv(ws, 6,  "RCN للتحقق (مُحسَب مباشرة) (ج.م.)",     RCN, "C")
    _sp(ws, 7); _h2(ws, 8, "§2 — الاستهلاك المتراكم — Depreciation")
    _kv(ws, 9,  "الاستهلاك المادي (ج.م.)",       "='Depreciation Analysis'!B8",  "C")
    _kv(ws, 10, "الاستهلاك الوظيفي (ج.م.)",      "='Depreciation Analysis'!B12", "C")
    _kv(ws, 11, "الاستهلاك الخارجي (ج.م.)",      "='Depreciation Analysis'!B16", "C")
    _kv(ws, 12, "إجمالي الاستهلاك (ج.م.)",       "='Depreciation Analysis'!B19", "C")
    _kv(ws, 13, "نسبة الاستهلاك الكلي %",         f"={TDEP}/{RCN}", "C")
    _sp(ws, 14); _h2(ws, 15, "§3 — القيمة الدفترية RCNLD")
    _kv(ws, 16, "RCNLD = RCN − إجمالي الاستهلاك (ج.م.)", "=B5-B12", "O")
    _kv(ws, 17, "RCNLD للتحقق (ج.م.)",                     NBV, "C")
    _kv(ws, 18, "قيمة الأرض المضافة (ج.م.)",               "='Land Reconciliation'!B12", "C")
    _kv(ws, 19, "القيمة الكاملة (RCNLD + أرض + تحسينات) (ج.م.)", f"=B16+B18+{50_000}", "O")
    _kv(ws, 20, "للتحقق (ج.م.)",                            NBV + LAND_REC + 50_000, "C")
    _sp(ws, 21); _h2(ws, 22, "§4 — الافتراضات والقيود")
    _kv(ws, 23, "معيار التطبيق",     "RCNLD مناسب للعقارات الجديدة أو محدودة التداول في السوق", "I")
    _kv(ws, 24, "مصدر RCN",          "مؤشر داخلي — يُفضَّل مراجعة مقيّم تكاليف متخصص", "M")
    _kv(ws, 25, "الاستهلاك الوظيفي", "نسبة 5٪ افتراضية — يستلزم تفتيشاً ميدانياً", "M")
    _nt(ws, 26, "⚠ advisory_only=True | مرتبط بـ Building Cost Breakdown & Depreciation Analysis")


def build_reproduction_cost(ws):
    _setup(ws, "C00000")
    _h1(ws, 1, "Reproduction Cost — تكلفة الاستنساخ")
    _nt(ws, 2, "Reproduction Cost: exact replica at current prices vs Replacement Cost (modern equivalent)")
    _sp(ws, 3); _h2(ws, 4, "§1 — الفرق بين الاستنساخ والاستبدال")
    _th(ws, 5, "المفهوم", "التعريف", "الاستخدام", "الملاحظة")
    _td(ws, 6, "تكلفة الاستنساخ",
        "إعادة بناء نسخة طبق الأصل بالمواد والتصاميم الأصلية",
        "مباني تاريخية / إرث معماري", "عادةً أعلى من الاستبدال")
    _td(ws, 7, "تكلفة الاستبدال (RCN)",
        "بناء مبنى مماثل الفائدة بمواد ومعايير حديثة",
        "التقييم القياسي", "المستخدم في هذا الملف")
    _sp(ws, 8); _h2(ws, 9, "§2 — تكلفة الاستنساخ المقدرة")
    _kv(ws, 10, "تكلفة البناء التاريخية (ج.م./م²)",  NA, "M")
    _kv(ws, 11, "مؤشر تكلفة البناء الحالي",           NA, "M")
    _kv(ws, 12, "تكلفة الاستنساخ المحدَّثة (ج.م./م²)", NA, "M")
    _kv(ws, 13, "تكلفة الاستنساخ الكلية (ج.م.)",      NA, "M")
    _kv(ws, 14, "مقارنة: RCN الحالي (ج.م.)",          "='Building Cost Breakdown'!B20", "C")
    _sp(ws, 15); _h2(ws, 16, "§3 — الاستهلاك والقيمة الصافية")
    _kv(ws, 17, "استهلاك الاستنساخ %",         NA, "M")
    _kv(ws, 18, "استهلاك الاستنساخ (ج.م.)",    NA, "M")
    _kv(ws, 19, "صافي قيمة الاستنساخ (ج.م.)",  NA, "M")
    _sp(ws, 20); _h2(ws, 21, "§4 — الافتراضات والقيود")
    _kv(ws, 22, "تطبيق العقار الحالي",
        "شقة سكنية معيارية — الاستبدال (RCN) أنسب من الاستنساخ", "I")
    _kv(ws, 23, "متى يُستخدَم الاستنساخ",
        "مباني ذات قيمة تاريخية أو معمارية فريدة فقط", "I")
    _kv(ws, 24, "قيود البيانات",
        "تكاليف البناء التاريخية ومؤشرات التحديث غير متوفرة", "R")
    _sp(ws, 25); _h2(ws, 26, "§5 — الحالة")
    _kv(ws, 27, "حالة النموذج",       BLK, "R")
    _kv(ws, 28, "القيمة البديلة المعتمدة", "RCN = تكلفة الاستبدال — موثقة في Building Cost Breakdown", "C")
    _nt(ws, 29, "⚠ fake_reproduction_cost_created=False | RCN يُستخدَم بدلاً من الاستنساخ في الحالة الراهنة")


def build_expected_utility(ws):
    _setup(ws, "7030A0")
    _h1(ws, 1, "Expected Utility — القيمة المتوقعة بالمنفعة")
    _nt(ws, 2, "EV = Σ(P(scenario) × Value(scenario)) | Decision support under uncertainty")
    _sp(ws, 3); _h2(ws, 4, "§1 — السيناريوهات والاحتمالات — Scenarios & Probabilities")
    _th(ws, 5, "السيناريو", "الاحتمالية P", "القيمة (ج.م.)", "القيمة × P (ج.م.)", "الافتراض الرئيسي")
    v1 = round(NOI*0.85/0.08); v2 = round(NOI/0.065)
    v3 = round(NOI*1.10/0.060); v4 = round(NOI*1.20/0.055)
    _td(ws, 6, "متشائم — انكماش سوقي",   0.20, v1, f"=B6*C6",  "معدل رسملة 8٪ + انخفاض NOI 15٪")
    _td(ws, 7, "محايد — أساسي",           0.50, v2, f"=B7*C7",  "NOI مستقر + Cap Rate 6.5٪")
    _td(ws, 8, "متفائل — نمو معتدل",      0.25, v3, f"=B8*C8",  "نمو NOI 10٪ + Cap Rate 6٪")
    _td(ws, 9, "تفاؤل قوي — طفرة عقارية",0.05, v4, f"=B9*C9",  "نمو NOI 20٪ + Cap Rate 5.5٪")
    _sp(ws, 10)
    _kv(ws, 11, "إجمالي الاحتمالات (يجب = 1.0)",   "=SUM(B6:B9)",  "C")
    _kv(ws, 12, "القيمة المتوقعة — EV (ج.م.)",      "=SUM(D6:D9)",  "O")
    _kv(ws, 13, "EV للتحقق (ج.م.)",
        round(0.20*v1 + 0.50*v2 + 0.25*v3 + 0.05*v4), "C")
    _sp(ws, 14); _h2(ws, 15, "§2 — هيكل المنفعة — Utility Structure")
    _th(ws, 16, "مستوى المخاطر", "معامل المنفعة U", "القيمة المعدَّلة (ج.م.)", "التوصية")
    _td(ws, 17, "متحفظ (U=0.8)",  0.8, "=B12*0.8", "يُفضل الأصول منخفضة المخاطر")
    _td(ws, 18, "محايد (U=1.0)",  1.0, "=B12*1.0", "EV تتوافق مع قيمة السوق")
    _td(ws, 19, "مقبِل (U=1.2)",  1.2, "=B12*1.2", "يقبل مخاطر مقابل عائد أعلى")
    _sp(ws, 20); _h2(ws, 21, "§3 — دعم القرار — Decision Support")
    _kv(ws, 22, "قرار",
        f"=IF(B12>={FINAL},\"القيمة المتوقعة تدعم السعر الحالي\",\"القيمة المتوقعة < السعر الحالي\")", "C")
    _kv(ws, 23, "هامش الأمان (Safety Margin) (ج.م.)", f"=B12-{FINAL}", "C")
    _sp(ws, 24); _h2(ws, 25, "§4 — الافتراضات والقيود")
    _kv(ws, 26, "ذاتية الاحتمالات",      "الاحتمالات تعتمد على حكم خبير — يُفضَّل تحديثها بمؤشرات سوق", "I")
    _kv(ws, 27, "استقلالية السيناريوهات","السيناريوهات مستقلة — تبسيط منطقي", "I")
    _kv(ws, 28, "بيانات مزورة",           "لا — fake_market_data_created=False", "C")
    _nt(ws, 29, "⚠ advisory_only=True | القيمة المتوقعة أداة قرار داعمة وليست قيمة معتمدة رسمياً")


def build_arima(ws):
    _setup(ws, "404040")
    _h1(ws, 1, "ARIMA — نموذج السلاسل الزمنية")
    _nt(ws, 2, "ARIMA(p,d,q): AutoRegressive Integrated Moving Average | Blocked: historical price series required")
    _sp(ws, 3); _h2(ws, 4, "§1 — بنية النموذج — Model Structure")
    _th(ws, 5, "المكوّن", "الرمز", "المعنى", "القيمة الحالية", "ملاحظات")
    _td(ws, 6, "AutoRegressive",  "p", "عدد فترات الإبطاء", NA, "يُحدَّد بـ PACF")
    _td(ws, 7, "Integrated",      "d", "درجة الفروق",        NA, "لتحقيق الاستقرارية")
    _td(ws, 8, "Moving Average",  "q", "عدد خطأ الإبطاء",   NA, "يُحدَّد بـ ACF")
    _td(ws, 9, "Seasonality",     "s", "دورة موسمية (شهر)", 12,  "دورة سنوية")
    _sp(ws, 10); _h2(ws, 11, "§2 — بيانات السلاسل الزمنية المطلوبة — Required Time Series")
    _th(ws, 12, "السنة", "الربع", "متوسط سعر/م² (ج.م.)", "حجم الصفقات", "المصدر")
    for yr in range(2019, 2025):
        for q in [1, 2, 3, 4]:
            _td(ws, 13 + (yr-2019)*4 + (q-1), yr, f"Q{q}", NA, NA, NA)
    _sp(ws, 37); _h2(ws, 38, "§3 — مخرجات النموذج — Model Outputs")
    _kv(ws, 39, "نقاط البيانات المتاحة في جدول §2",    "=COUNTA(C13:C36)", "C")
    _kv(ws, 40, "ARIMA(p,d,q) المحدد",                  NA, "M")
    _kv(ws, 41, "AIC / BIC (جودة النموذج)",             NA, "M")
    _kv(ws, 42, "توقع السعر السنة القادمة (ج.م./م²)",   NA, "M")
    _kv(ws, 43, "نطاق الثقة 95٪ للتوقع",                NA, "M")
    _kv(ws, 44, "القيمة المتوقعة من ARIMA (ج.م.)",       NA, "M")
    _sp(ws, 45); _h2(ws, 46, "§4 — الافتراضات والقيود")
    _kv(ws, 47, "بيانات مطلوبة",    "24 نقطة بيانات على الأقل (ربع سنوية)", "M")
    _kv(ws, 48, "الاستقرارية",      "السلسلة يجب أن تكون Stationary — يُختبر بـ ADF Test", "I")
    _kv(ws, 49, "حدود التوقع",      "التوقعات تدهور في الدقة بعد 4-8 أرباع", "I")
    _kv(ws, 50, "متطلبات التشغيل",  "Python statsmodels / R forecast / EViews", "I")
    _kv(ws, 51, "حالة النموذج",      BLK, "R")
    _nt(ws, 52, "⚠ fake_time_series_created=False | بيانات تاريخية حقيقية من السوق مطلوبة لتشغيل ARIMA")


def build_real_options(ws):
    _setup(ws, "7030A0")
    _h1(ws, 1, "Real Options — خيارات حقيقية")
    _nt(ws, 2, "Real Options: option to delay, develop, expand, or abandon | Black-Scholes framework")
    _sp(ws, 3); _h2(ws, 4, "§1 — أنواع الخيارات الحقيقية — Option Types")
    _th(ws, 5, "نوع الخيار", "التعريف", "القيمة المضافة", "تطبيق العقار الحالي")
    _td(ws, 6, "خيار التأجيل (Delay)",  "تأجيل قرار التطوير أو البيع",    "تجنب سوق هابط",         "قابل للتطبيق — الاحتفاظ مقابل البيع")
    _td(ws, 7, "خيار التوسع (Expand)",  "توسعة أو إضافة وحدات",           "زيادة القيمة الإيجارية", "محدود — حصص البناء")
    _td(ws, 8, "خيار التطوير (Develop)","إعادة تطوير لاستخدام أعلى قيمة", "رفع الكثافة",             "يحتاج HBU إيجابي")
    _td(ws, 9, "خيار الخروج (Abandon)", "بيع قبل انتهاء الأفق الاستثماري","تحديد حد أدنى للخسارة",  "مرتبط بـ Sale vs Rent")
    _sp(ws, 10); _h2(ws, 11, "§2 — محفز القرار — Decision Trigger")
    _kv(ws, 12, "القيمة الحالية للأصل S (ج.م.)", FINAL, "I")
    _kv(ws, 13, "تكلفة التطوير / الخروج X (ج.م.)", NA, "M")
    _kv(ws, 14, "التقلب σ — Volatility",            NA, "M")
    _kv(ws, 15, "المعدل الخالي من المخاطر r",        "='Input Control Panel'!B24", "I")
    _kv(ws, 16, "الأفق الزمني T (سنوات)",            NA, "M")
    _sp(ws, 17); _h2(ws, 18, "§3 — القيمة الاتجاهية — Upside / Downside")
    _kv(ws, 19, "قيمة السوق الحالية (Intrinsic Value) (ج.م.)", FINAL, "C")
    _kv(ws, 20, "قيمة الخيار (Option Premium) (ج.م.)",          NA, "M")
    _kv(ws, 21, "القيمة الكلية (Intrinsic + Premium) (ج.م.)",   NA, "M")
    _kv(ws, 22, "قرار الاحتفاظ vs البيع",
        "=IF('Sale vs Rent'!B7>0.10,\"الاحتفاظ والتأجير أفضل\",\"البيع قد يكون أفضل\")", "C")
    _sp(ws, 23); _h2(ws, 24, "§4 — القيود")
    _kv(ws, 25, "قيد التقلب",       "σ يحتاج سلسلة زمنية من أسعار السوق — مرتبط بـ ARIMA", "M")
    _kv(ws, 26, "قيد Black-Scholes", "افتراض التوزيع اللوغاريتمي — قد لا ينطبق على السوق المصري", "I")
    _kv(ws, 27, "حالة النموذج",      BLK, "R")
    _nt(ws, 28, "⚠ advisory_only=True | قيمة الخيارات الحقيقية أداة استراتيجية — ليست قيمة سوقية رسمية")


def build_additional_methods(ws):
    _setup(ws, "595959")
    _h1(ws, 1, "طرق إضافية — Additional Valuation Methods")
    _nt(ws, 2, "Supplementary methods registry: applicability, data requirements, readiness status")
    _sp(ws, 3); _h2(ws, 4, "§1 — سجل الطرق الإضافية — Methods Registry")
    _th(ws, 5, "الطريقة", "التعريف", "قابلية التطبيق", "البيانات المطلوبة", "الجاهزية / المؤشر")
    _td(ws, 6,  "معامل السعر/الإيجار P/R",
        "نسبة سعر البيع إلى الإيجار الصافي السنوي",
        "قابل للتطبيق",
        "سعر البيع + NOI",
        f"P/R = {round(FINAL/NOI, 1):.1f}x")
    _td(ws, 7,  "معامل إجمالي الدخل GIM",
        "Value = GIM × Gross Rental Income",
        "قابل للتطبيق",
        "GIM السوقي + إيجار إجمالي",
        f"GIM = {round(FINAL/84_000, 1):.1f}x تقديري")
    _td(ws, 8,  "نسبة تغطية الدين DSCR",
        "NOI / خدمة الدين السنوية",
        "قابل للتطبيق",
        "NOI + خدمة دين",
        BLK)
    _td(ws, 9,  "معادلة التعادل Break-Even",
        "إيجار يغطي كل التكاليف",
        "قابل للتطبيق",
        "NOI + تكاليف ثابتة",
        f"B/E Yield = {round(NOI/FINAL*100, 2):.2f}٪")
    _td(ws, 10, "نموذج Graaskamp",
        "ربط قيمة العقار بالقدرة التمويلية للمشتري",
        "تطبيق جزئي",
        "بيانات التمويل + دخل المستثمر",
        BLK)
    _td(ws, 11, "تحليل المحفظة Portfolio",
        "تقييم في سياق محفظة عقارية",
        "تطبيق جزئي",
        "بيانات المحفظة الكاملة",
        BLK)
    _td(ws, 12, "مؤشر الاقتدار السكني",
        "مدى قدرة متوسط الدخل على الشراء",
        "بيانات ناقصة",
        "متوسط دخل الأسرة في المنطقة",
        NA)
    _td(ws, 13, "قيمة التصفية Liquidation",
        "قيمة البيع السريع مع خصم الإلحاح",
        "قابل للتطبيق",
        "قيمة السوق + نسبة خصم الإلحاح",
        f"Liq ≈ {round(FINAL*0.85):,} ج.م. (خصم 15٪)")
    _td(ws, 14, "قيمة التأمين Insurable",
        "تكلفة إعادة البناء للتأمين العقاري",
        "قابل للتطبيق",
        "RCN بدون قيمة الأرض",
        f"RCN = {RCN:,} ج.م.")
    _td(ws, 15, "قيمة الاستمرارية Going Concern",
        "قيمة العقار بما يشمل الأعمال الجارية",
        "لا ينطبق",
        "بيانات الأعمال التشغيلية",
        "شقة سكنية — لا تطبيق مباشر")
    _sp(ws, 16); _h2(ws, 17, "§2 — مؤشرات سريعة — Quick Indicators")
    _kv(ws, 18, "P/R Ratio (سعر / NOI)",               f"={FINAL}/{NOI}", "C")
    _kv(ws, 19, "GIM (معامل إجمالي الدخل)",             f"={FINAL}/84000", "C")
    _kv(ws, 20, "Gross Yield % (إيجار إجمالي / سعر)",   "=84000/{:d}".format(FINAL), "C")
    _kv(ws, 21, "Net Yield % (NOI / سعر)",               f"={NOI}/{FINAL}", "C")
    _kv(ws, 22, "قيمة التصفية التقديرية (ج.م.)",        round(FINAL*0.85), "C")
    _kv(ws, 23, "قيمة التأمين = RCN (ج.م.)",            "='Building Cost Breakdown'!B20", "C")
    _sp(ws, 24); _h2(ws, 25, "§3 — ملخص الجاهزية — Readiness Summary")
    _kv(ws, 26, "الطرق الجاهزة فوراً",   "P/R | GIM | Break-Even | Liquidation | Insurable Value", "C")
    _kv(ws, 27, "الطرق المحجوبة ببيانات", "DSCR | Graaskamp | Portfolio | Affordability | Going Concern", "M")
    _kv(ws, 28, "بيانات مزورة",           "لا — fake_methods_data_created=False", "C")
    _nt(ws, 29, "⚠ advisory_only=True | جميع الطرق الإضافية استشارية — ليست قيماً معتمدة رسمياً")
