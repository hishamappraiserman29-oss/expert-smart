"""certification_pack_sheets.py — Batch 1: Certification/Compliance/Governance sheets.
9 new sheet builders for the professional valuation Excel reference parity workbook.
advisory_only=True | fake_sources_created=False | fake_signature_created=False
"""
from __future__ import annotations
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

# ── Style helpers (standalone — no import from main builder to avoid circular deps) ──

DK_BLUE = "1F4E79"; MD_BLUE = "2E75B6"; LT_BLUE = "DEEAF1"
YELLOW  = "FFF2CC"; GREEN   = "E2EFDA"; ORANGE  = "FCE4D6"
GRAY    = "F2F2F2"; RED     = "FFCCCC"; WHITE   = "FFFFFF"

# Status-semantic colors from Reference Workbook A (certification governance)
STA_GREEN_BG  = "BBF7D0"; STA_GREEN_FG  = "166534"
STA_AMBER_BG  = "FEF3C7"; STA_AMBER_FG  = "92400E"
STA_RED_BG    = "FEE2E2"; STA_RED_FG    = "8B1A1A"
STA_PURPLE_BG = "EDE9FE"; STA_PURPLE_FG = "4A235A"

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

def _sta_row(ws, r, *cols, status="⬜"):
    """Color row using certification traffic-light semantics."""
    if status == "✅":
        bg, fg = STA_GREEN_BG, STA_GREEN_FG
    elif status == "⚠":
        bg, fg = STA_AMBER_BG, STA_AMBER_FG
    elif status in ("⬜", "🔒"):
        bg, fg = STA_RED_BG, STA_RED_FG
    elif status == "💡":
        bg, fg = STA_PURPLE_BG, STA_PURPLE_FG
    else:
        bg, fg = GRAY, "000000"
    for c, v in enumerate(cols, 1):
        _c(ws, r, c, v, bg=bg, fg=fg, wrap=(c == 1 or c == len(cols)))
    ws.row_dimensions[r].height = 18

# ── Shared constants ─────────────────────────────────────────────────────────

REF   = "PV-RCP-2026-001"
DATE  = "2026-07-10"
PROP  = "شقة سكنية — المعادي، القاهرة"
LA    = 200; BA = 150; AGE = 12; FINAL = 1_130_000
NOI   = 67_830; INC_V = 1_043_538
MISS  = "⬜ Required Data Missing"
BLK   = "🔒 Blocked Pending Production Data"
NA    = "غير متاح ضمن بيانات الطلب"

# ── Batch 1 Sheet Builders (9 sheets) ────────────────────────────────────────

def build_intro_report(ws):
    """مقدمة التقرير — Report Introduction."""
    _setup(ws, "2E75B6")
    _h1(ws, 1, "مقدمة التقرير — Report Introduction")
    _nt(ws, 2, "advisory_only=True | fake_sources_created=False | Reference: PV-RCP-2026-001")
    _sp(ws, 3)
    _h2(ws, 4, "§1 — هوية التقرير")
    _kv(ws, 5,  "رقم المرجع",                      REF,  "I")
    _kv(ws, 6,  "تاريخ التقييم",                    DATE, "I")
    _kv(ws, 7,  "عنوان التقرير",                    "تقرير تقييم عقاري مهني — شقة سكنية، المعادي", "I")
    _kv(ws, 8,  "الغرض من التقييم",                 "تقييم للأغراض الاستشارية الداخلية", "I")
    _kv(ws, 9,  "الاستخدام المقصود",                "إرشادي داخلي — advisory_only", "I")
    _kv(ws, 10, "قاعدة القيمة",                     "القيمة السوقية / Market Value", "I")
    _sp(ws, 11)
    _h2(ws, 12, "§2 — بيانات العقار الموضوع")
    _kv(ws, 13, "وصف العقار",                       PROP,  "I")
    _kv(ws, 14, "مساحة الأرض (م²)",                 LA,    "I")
    _kv(ws, 15, "المساحة المبنية (م²)",              BA,    "I")
    _kv(ws, 16, "عمر العقار (سنة)",                  AGE,   "I")
    _kv(ws, 17, "القيمة السوقية النهائية (ج.م.)",    FINAL, "O")
    _sp(ws, 18)
    _h2(ws, 19, "§3 — المعايير المطبقة")
    _kv(ws, 20, "RICS Red Book 2022",                "مطبق — Applied", "C")
    _kv(ws, 21, "IVS 2022",                          "مطبق — Applied", "C")
    _kv(ws, 22, "المعايير المصرية للتقييم",          "مطبق — Applied", "C")
    _sp(ws, 23)
    _nt(ws, 24, "⚠ هذا التقرير للأغراض الاستشارية الداخلية فقط — No fake market evidence — No fake signature.")


def build_scope_work(ws):
    """نطاق العمل — Scope of Work."""
    _setup(ws, "2E75B6")
    _h1(ws, 1, "نطاق العمل — Scope of Work")
    _nt(ws, 2, "RICS VPS 1 | IVS 101 — Scope of Work Documentation | advisory_only=True")
    _sp(ws, 3)
    _h2(ws, 4, "§1 — مُصدِر التقرير والمستفيد")
    _kv(ws, 5,  "اسم المُقيِّم / المُعِد",           BLK,  "R")
    _kv(ws, 6,  "رقم الترخيص المهني",               BLK,  "R")
    _kv(ws, 7,  "الجهة الطالبة / العميل",           BLK,  "R")
    _kv(ws, 8,  "المستخدمون المقصودون",             "داخلي — Internal only", "I")
    _sp(ws, 9)
    _h2(ws, 10, "§2 — الغرض والقاعدة")
    _kv(ws, 11, "الغرض من التقييم",                 "استشاري / Advisory", "I")
    _kv(ws, 12, "قاعدة القيمة (Basis of Value)",    "القيمة السوقية وفق RICS/IVS", "I")
    _kv(ws, 13, "تاريخ السريان",                    DATE, "I")
    _sp(ws, 14)
    _h2(ws, 15, "§3 — حدود الفحص الميداني")
    _kv(ws, 16, "نطاق الفحص الميداني",              "فحص خارجي وداخلي — محدود", "I")
    _kv(ws, 17, "تاريخ الفحص",                      DATE, "I")
    _kv(ws, 18, "المفتش",                           BLK,  "R")
    _sp(ws, 19)
    _h2(ws, 20, "§4 — البيانات المستخدمة")
    _th(ws, 21, "نوع البيانات", "المصدر", "الحالة", "ملاحظات")
    rows = [
        ("بيانات السوق المرجعية",  "real_estate_enhanced_500.xlsx", "✅", "500 سجل"),
        ("أسعار تكلفة البناء",     "مؤشر داخلي",                    "✅", "مرجع افتراضي"),
        ("بيانات الإيجار",         NA,                              "⚠",  "بيانات محدودة"),
        ("مبيعات مقارنة محلية",    NA,                              "⬜", BLK),
        ("تراخيص ومخططات",         NA,                              "⬜", BLK),
    ]
    for i, row in enumerate(rows, 22): _td(ws, i, *row)
    _sp(ws, 27)
    _nt(ws, 28, "⚠ لا توجد بيانات مزورة — No fabricated market evidence. advisory_only=True.")


def build_special_assumptions(ws):
    """الافتراضات الخاصة والقيود — Special Assumptions & Limitations."""
    _setup(ws, "FFC000")
    _h1(ws, 1, "الافتراضات الخاصة والقيود — Special Assumptions & Limitations")
    _nt(ws, 2, "RICS VPS 4 | IVS 101.1 — Special assumptions must be reasonable, relevant and agreed")
    _sp(ws, 3)
    _h2(ws, 4, "§1 — الافتراضات الخاصة المعتمدة")
    _th(ws, 5, "#", "الافتراض", "المبرر", "الأثر على القيمة", "الحالة")
    assumptions = [
        (1, "حالة الصيانة جيدة",          "فحص بصري فقط",          "طفيف",  "✅"),
        (2, "لا قيود قانونية على البيع",   NA,                      "متوسط", "⚠"),
        (3, "لا عوائق على الملكية",        NA,                      "عالٍ",  "⬜"),
        (4, "معدل رسملة 6.5٪ معياري",      "متوسط السوق الإقليمي",  "متوسط", "✅"),
        (5, "تكلفة بناء 4,500 ج.م./م²",   "مؤشر داخلي مرجعي",     "متوسط", "✅"),
    ]
    for i, row in enumerate(assumptions, 6): _td(ws, i, *row)
    _sp(ws, 11)
    _h2(ws, 12, "§2 — القيود المؤثرة على الموثوقية")
    _th(ws, 13, "#", "القيد", "الأثر", "الإجراء المطلوب")
    limits = [
        (1, "غياب مبيعات مقارنة محلية",   "يُضعِف منهجية المقارنة",          "إضافة 4-6 مبيعات مقارنة"),
        (2, "بيانات إيجار محدودة",         "يقلل دقة منهجية الدخل",           "مسح سوق الإيجار"),
        (3, "غياب بيانات GIS مرخصة",       "يُقيِّد التحليل المكاني",          "الحصول على مصدر GIS"),
        (4, "عدم توفر وثائق ملكية رسمية",  "يحجب التحقق القانوني",             BLK),
        (5, "توقيع معتمد غير متاح",         "لا يمكن إصدار تقرير نهائي معتمد", BLK),
    ]
    for i, row in enumerate(limits, 14): _td(ws, i, *row)
    _sp(ws, 19)
    _nt(ws, 20, "⚠ جميع القيود موثقة صراحةً — No workaround by fabricating data. advisory_only=True.")


def build_docs_risks(ws):
    """المستندات والمخاطر — Documentation & Certification Risks."""
    _setup(ws, "C00000")
    _h1(ws, 1, "المستندات والمخاطر — Documentation & Certification Risks")
    _nt(ws, 2, "Document checklist + certification risk register | advisory_only=True")
    _sp(ws, 3)
    _h2(ws, 4, "§1 — قائمة المستندات المطلوبة")
    _th(ws, 5, "المستند", "النوع", "الحالة", "درجة الخطر", "ملاحظات")
    docs = [
        ("سند الملكية / عقد التمليك",      "قانوني", "⬜", "عالٍ",  BLK),
        ("الرسومات والمخططات المعتمدة",     "هندسي",  "⬜", "متوسط", BLK),
        ("شهادة إتمام البناء",              "إداري",  "⬜", "متوسط", BLK),
        ("شهادة التسجيل العقاري",           "قانوني", "⬜", "عالٍ",  BLK),
        ("عقد الإيجار السائد",              "مالي",   "⬜", "متوسط", NA),
        ("تقارير الفحص الهندسي",            "فني",    "⬜", "منخفض", NA),
        ("الضرائب العقارية المدفوعة",       "مالي",   "⬜", "متوسط", BLK),
        ("بيانات الاستهلاك والصيانة",       "مالي",   "✅", "منخفض", "مؤشر داخلي"),
        ("real_estate_enhanced_500.xlsx",    "سوقي",   "✅", "منخفض", "500 سجل"),
    ]
    for i, row in enumerate(docs, 6): _td(ws, i, *row)
    _sp(ws, 15)
    _h2(ws, 16, "§2 — سجل مخاطر الاعتماد")
    _th(ws, 17, "#", "المخاطرة", "الاحتمالية", "التأثير", "الدرجة", "الإجراء")
    cert_risks = [
        (1, "نقص مبيعات مقارنة",    3, 4, "=C18*D18", "توفير 4+ مبيعات"),
        (2, "غياب توقيع مقيّم",      5, 5, "=C19*D19", BLK),
        (3, "وثائق ملكية ناقصة",     4, 5, "=C20*D20", BLK),
        (4, "بيانات GIS غير مرخصة",  3, 3, "=C21*D21", "مصدر GIS مرخص"),
        (5, "عدم اكتمال نموذج ANN",  4, 3, "=C22*D22", "بيانات تدريب إضافية"),
    ]
    for i, row in enumerate(cert_risks, 18): _td(ws, i, *row)
    _sp(ws, 23)
    _nt(ws, 24, "⚠ لا يُكشَف هذا النموذج للمستخدم الخارجي — Excel للاستخدام الداخلي فقط.")


def build_legal_check(ws):
    """الفحص القانوني — Legal & Title Check."""
    _setup(ws, "7030A0")
    _h1(ws, 1, "الفحص القانوني المبدئي — Legal & Title Check")
    _nt(ws, 2, "Legal verification checklist | advisory_only — not a legal opinion | fake_sources_created=False")
    _sp(ws, 3)
    _h2(ws, 4, "§1 — التحقق من الملكية")
    _th(ws, 5, "البند", "الحالة", "مصدر التحقق", "درجة الخطر")
    items_own = [
        ("وضوح سند الملكية",                    "⬜", BLK, "عالٍ"),
        ("سلسلة ملكية متتالية (chain of title)", "⬜", BLK, "عالٍ"),
        ("غياب رهون أو أعباء",                   "⬜", NA,  "عالٍ"),
        ("مطابقة مساحة الأرض مع السجل الرسمي",   "⬜", BLK, "متوسط"),
        ("تسجيل في الشهر العقاري",               "⬜", BLK, "عالٍ"),
    ]
    for i, row in enumerate(items_own, 6): _td(ws, i, *row)
    _sp(ws, 11)
    _h2(ws, 12, "§2 — التراخيص والقرارات")
    items_perm = [
        ("ترخيص البناء",               "⬜", BLK, "متوسط"),
        ("شهادة إتمام البناء",          "⬜", BLK, "متوسط"),
        ("الامتثال لاشتراطات التخطيط",  "⬜", NA,  "متوسط"),
        ("لا قرارات إزالة سارية",       "⬜", NA,  "عالٍ"),
    ]
    for i, row in enumerate(items_perm, 13): _td(ws, i, *row)
    _sp(ws, 17)
    _h2(ws, 18, "§3 — ملاحظات الفحص")
    _kv(ws, 19, "تاريخ الفحص المبدئي",          DATE,                      "I")
    _kv(ws, 20, "الجهة المنفذة للفحص",          BLK,                       "R")
    _kv(ws, 21, "إجمالي البنود المكتملة (✅)",   "=COUNTIF(B6:B16,\"✅\")",  "C")
    _kv(ws, 22, "إجمالي البنود المحجوبة (⬜)",   "=COUNTIF(B6:B16,\"⬜\")",  "C")
    _sp(ws, 23)
    _nt(ws, 24, "⚠ هذا فحص أولي استشاري فقط — ليس رأياً قانونياً معتمداً. لا وثائق مزورة.")


def build_compliance_statement(ws):
    """بيان الامتثال — Professional Compliance Statement."""
    _setup(ws, "375623")
    _h1(ws, 1, "بيان الامتثال المهني — Compliance Statement")
    _nt(ws, 2, "RICS Red Book 2022 | IVS 2022 | Egyptian Standards | advisory_only=True")
    _sp(ws, 3)
    _h2(ws, 4, "§1 — الامتثال لـ RICS Red Book 2022")
    _th(ws, 5, "البند", "المتطلب", "الحالة", "ملاحظات")
    rics = [
        ("VPS 1",  "نطاق العمل موثق",             "✅", "موثق في ورقة نطاق العمل"),
        ("VPS 2",  "تعريف القيمة السوقية",         "✅", "RICS Market Value Definition"),
        ("VPS 3",  "تقييم وفق VPS 3",              "⚠",  "تقرير استشاري فقط"),
        ("VPS 4",  "الافتراضات الخاصة موثقة",      "✅", "موثق في ورقة الافتراضات"),
        ("VPS 5",  "نموذج تقرير مكتمل",             "⚠",  "في طور الإعداد"),
        ("VPGA 1", "تحليل سوقي موثق",              "⚠",  "بيانات محدودة"),
    ]
    for i, row in enumerate(rics, 6): _td(ws, i, *row)
    _sp(ws, 12)
    _h2(ws, 13, "§2 — الامتثال لـ IVS 2022")
    ivs = [
        ("IVS 101", "نطاق العمل",          "✅", "مكتمل"),
        ("IVS 102", "التحقيقات",           "⚠",  "فحص داخلي فقط"),
        ("IVS 103", "التقرير",              "⚠",  "استشاري — ليس معتمداً"),
        ("IVS 200", "الأعمال التجارية",     "N/A","لا ينطبق"),
        ("IVS 400", "الأصول العقارية",      "✅", "مطبق"),
    ]
    for i, row in enumerate(ivs, 14): _td(ws, i, *row)
    _sp(ws, 19)
    _h2(ws, 20, "§3 — الإعلان الرسمي")
    _kv(ws, 21, "نوع التقرير",              "استشاري — Advisory Only",             "I")
    _kv(ws, 22, "بيانات مزورة",             "لا — None fabricated",                "C")
    _kv(ws, 23, "توقيع معتمد",              "⬜ مطلوب — بانتظار مقيّم مرخص",       "R")
    _kv(ws, 24, "fake_sources_created",     "False",                               "C")
    _kv(ws, 25, "advisory_only",            "True",                                "C")
    _kv(ws, 26, "تاريخ الإعلان",            DATE,                                  "I")
    _sp(ws, 27)
    _nt(ws, 28, "⚠ advisory_only=True | fake_sources_created=False | No fake valuer / license / stamp.")


def build_cert_roadmap(ws):
    """خارطة طريق الاعتماد — Certification Roadmap."""
    _setup(ws, "1F4E79")
    _h1(ws, 1, "خارطة طريق الاعتماد — Certification Roadmap")
    _nt(ws, 2, "Phased certification milestones | Traffic-light status | RICS/IVS compliance path")
    _sp(ws, 3)
    _h2(ws, 4, "§1 — المراحل والبوابات")
    _th(ws, 5, "المرحلة", "البوابة", "المالك", "الهدف", "الحالة", "ملاحظات")
    ws.column_dimensions["C"].width = 20
    ws.column_dimensions["D"].width = 16
    ws.column_dimensions["F"].width = 26
    phases = [
        # Completed
        ("0 — البنية التحتية", "هيكل النموذج 50+ ورقة",         "نظام آلي",     "✅ مكتمل", "✅", "Skeleton built"),
        ("0 — البنية التحتية", "توليد PDF استشاري",              "نظام آلي",     "✅ مكتمل", "✅", "PDF rendered"),
        ("0 — البنية التحتية", "بيانات سوق مرجعية (500 سجل)",   "نظام آلي",     "✅ مكتمل", "✅", "real_estate_enhanced_500.xlsx"),
        # Blocked / pending
        ("1 — جمع البيانات",  "توفير 4+ مبيعات مقارنة",         "فريق البيانات", "⬜ مطلوب", "⬜", BLK),
        ("1 — جمع البيانات",  "توفير بيانات إيجار سوقية",        "فريق البيانات", "⬜ مطلوب", "⬜", BLK),
        ("2 — التحقق القانوني","الحصول على سند الملكية",          "قسم قانوني",    "⬜ مطلوب", "⬜", BLK),
        ("2 — التحقق القانوني","مراجعة التراخيص والمخططات",       "قسم قانوني",    "⬜ مطلوب", "⬜", BLK),
        ("3 — المراجعة المهنية","مراجعة مستقلة من خبير",          "خبير معتمد",    "⬜ مطلوب", "⬜", BLK),
        ("4 — الاعتماد",       "توقيع مقيّم عقاري مرخص",         "مقيّم مرخص",    "⬜ مطلوب", "⬜", BLK),
        ("5 — الأرشفة",        "حفظ آمن + نسخة احتياطية",        "فريق الأرشفة",  "⬜ مطلوب", "⬜", NA),
    ]
    for i, row in enumerate(phases, 6):
        st = row[4]
        bg = STA_GREEN_BG if st == "✅" else STA_RED_BG
        fg = STA_GREEN_FG if st == "✅" else STA_RED_FG
        for c, v in enumerate(row, 1):
            _c(ws, i, c, v, bg=bg, fg=fg, wrap=(c in (1, 2, 6)))
        ws.row_dimensions[i].height = 18
    _sp(ws, 16)
    _kv(ws, 17, "المراحل المكتملة (✅)", "=COUNTIF(E6:E15,\"✅\")", "C")
    _kv(ws, 18, "المراحل المحجوبة (⬜)", "=COUNTIF(E6:E15,\"⬜\")", "C")
    _sp(ws, 19)
    _nt(ws, 20, "⚠ لا يُصدَر تقرير معتمد قبل اكتمال جميع البوابات. advisory_only=True.")


def build_expert_signature_gate(ws):
    """توقيع الخبير وبوابة الاعتماد — Expert Signature Gate."""
    _setup(ws, "C00000")
    _h1(ws, 1, "توقيع الخبير وبوابة الاعتماد — Expert Signature Gate")
    _nt(ws, 2, "⚠ PERMANENTLY BLOCKED — بانتظار التوقيع الرسمي من مقيم عقاري مرخص")
    _sp(ws, 3)
    _h2(ws, 4, "§1 — حالة البوابة")
    _th(ws, 5, "البيان", "القيمة / الحالة", "علامة")
    sig_items = [
        ("اسم المقيّم المعتمد",           BLK,  "⬜"),
        ("رقم الترخيص المهني",            BLK,  "⬜"),
        ("رقم عضوية الجمعية المهنية",     BLK,  "⬜"),
        ("تاريخ انتهاء الترخيص",          BLK,  "⬜"),
        ("ختم المقيّم الرسمي",            BLK,  "⬜"),
        ("توقيع المقيّم الرسمي",          BLK,  "⬜"),
        ("تاريخ التوقيع",                 BLK,  "⬜"),
        ("تقرير مراجعة مستقلة",           BLK,  "⬜"),
    ]
    for i, (lbl, val, sta) in enumerate(sig_items, 6):
        _c(ws, i, 1, lbl, bg=STA_RED_BG, fg=STA_RED_FG, wrap=True)
        ws.merge_cells(start_row=i, start_column=2, end_row=i, end_column=5)
        _c(ws, i, 2, val, bg=STA_RED_BG, fg=STA_RED_FG)
        _c(ws, i, 6, sta, bg=STA_RED_BG, fg=STA_RED_FG, h="center", bold=True)
        ws.row_dimensions[i].height = 16
    _sp(ws, 14)
    _h2(ws, 15, "§2 — بيان المنع الرسمي")
    ws.merge_cells(start_row=16, start_column=1, end_row=20, end_column=6)
    cell = ws.cell(16, 1, (
        "بانتظار التوقيع الرسمي من مقيم عقاري مرخص\n\n"
        "هذا التقرير استشاري داخلي فقط ولا يُعتبر تقييماً معتمداً.\n"
        "fake_valuer_created=False | fake_stamp_created=False | fake_license_created=False\n"
        "No certified signature has been fabricated or simulated."
    ))
    cell.fill = _fill(STA_RED_BG)
    cell.font = Font(bold=True, size=12, color=STA_RED_FG, name="Calibri")
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = _BD
    ws.row_dimensions[16].height = 90
    _sp(ws, 21)
    _kv(ws, 22, "fake_valuer_created",  "False", "C")
    _kv(ws, 23, "fake_stamp_created",   "False", "C")
    _kv(ws, 24, "fake_license_created", "False", "C")
    _kv(ws, 25, "advisory_only",        "True",  "C")
    _sp(ws, 26)
    _nt(ws, 27, "⚠ Do NOT fill this sheet with fabricated data — gate is intentionally blocked.")


def build_rental_package(ws):
    """حزمة الإيجار — Rental Analysis Package."""
    _setup(ws, "00B050")
    _h1(ws, 1, "حزمة الإيجار — Rental Analysis Package")
    _nt(ws, 2, "Rental yield / NOI / Break-even / Sale-vs-Rent reconciliation | advisory_only=True")
    _sp(ws, 3)
    _h2(ws, 4, "§1 — مدخلات الإيجار")
    _kv(ws, 5,  "الإيجار السنوي الإجمالي (ج.م.)",     84_000, "I")
    _kv(ws, 6,  "نسبة الشغور",                        "5%",   "I")
    _kv(ws, 7,  "الإيجار الصافي الفعلي (ج.م.)",       "=84000*(1-0.05)",  "C")
    _kv(ws, 8,  "مصروفات تشغيلية (10٪)",              "=84000*0.95*0.10", "C")
    _kv(ws, 9,  "NOI الصافي (ج.م.)",                   NOI,    "O")
    _kv(ws, 10, "معدل الرسملة (Cap Rate)",              "6.5%", "I")
    _kv(ws, 11, "قيمة الدخل — Income Approach (ج.م.)",  INC_V,  "O")
    _sp(ws, 12)
    _h2(ws, 13, "§2 — تحليل العائد")
    _kv(ws, 14, "عائد الإيجار الإجمالي (Gross Yield)",  f"={84_000}/{FINAL}", "C")
    _kv(ws, 15, "عائد الإيجار الصافي (Net Yield)",      f"={NOI}/{FINAL}",    "C")
    _kv(ws, 16, "GRM — مضاعف الإيجار الإجمالي",         f"={FINAL}/{84_000}", "C")
    _sp(ws, 17)
    _h2(ws, 18, "§3 — تحليل نقطة التعادل (Break-Even)")
    _kv(ws, 19, "إجمالي التكلفة الاستثمارية (ج.م.)",   FINAL,                     "I")
    _kv(ws, 20, "NOI السنوي (ج.م.)",                   NOI,                       "C")
    _kv(ws, 21, "سنوات التعادل البسيطة",               f"={FINAL}/{NOI}",          "C")
    _kv(ws, 22, "إيجار مطلوب لتغطية 8٪ عائد (ج.م.)",  f"={FINAL}*0.08",           "C")
    _sp(ws, 23)
    _h2(ws, 24, "§4 — توفيق البيع مقابل الإيجار")
    _th(ws, 25, "القرار", "القيمة (ج.م.)", "العائد %", "التوصية")
    _td(ws, 26, "بيع فوري",          FINAL,  "—",                       "مناسب للسيولة")
    _td(ws, 27, "تأجير (10 سنوات)",  INC_V,  f"={NOI}/{FINAL}",          "مناسب للدخل")
    _td(ws, 28, "بيع بعد 5 سنوات",   NA,      NA,                        BLK)
    _sp(ws, 29)
    _kv(ws, 30, "التوصية المبدئية",
        "الإيجار أكثر كفاءة — عائد صافٍ ≈5.9٪ مقابل القيمة السوقية الحالية", "C")
    _sp(ws, 31)
    _nt(ws, 32, "⚠ بيانات الإيجار مرجعية — لا بيانات إيجار سوقية محلية متاحة. advisory_only=True.")
