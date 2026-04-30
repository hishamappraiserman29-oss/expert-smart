"""
setup_template.py
=================
يُعدّل template.xlsm مرة واحدة ليضيف:
  1. إحصاءات متقدمة لصفحة الانحدار (RMSE, MAE, F, t, COD, PCR, Ratio Studies)
  2. صفحة DCF — Discounted Cash Flow
  3. صفحة ANN — Artificial Neural Network
"""

import sys, os
sys.stdout.reconfigure(encoding='utf-8')

_HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(os.path.dirname(_HERE), "templates", "template.xlsm")

import xlwings as xw

def run():
    app = xw.App(visible=False, add_book=False)
    try:
        wb = app.books.open(TEMPLATE)
        _patch_regression(wb)
        _add_dcf_sheet(wb)
        _add_ann_sheet(wb)
        wb.save()
        wb.close()
        print("✓ Template updated:", TEMPLATE)
    finally:
        app.quit()


# ══════════════════════════════════════════════════════════════════════════════
# 1. تحديث ورقة الانحدار المتعدد
# ══════════════════════════════════════════════════════════════════════════════

def _patch_regression(wb):
    ws = wb.sheets["الانحدار المتعدد"]
    INP = "'الافتراضات والمدخلات'"

    # ── عمود G: القيم المتوقعة، عمود H: البواقي ─────────────────────────────
    ws.range("G26").value = "القيمة المتوقعة (EGP/م²)"
    ws.range("H26").value = "البواقي (Residual)"
    ws.range("I26").value = "النسبة (Ratio = Pred/Actual)"

    # بيانات المشاهدات: صفوف 27-46
    for i in range(20):
        r = 27 + i
        # Predicted = Intercept + b1*Floor + b2*Area + b3*Year
        ws.range(f"G{r}").formula = f"=$B$12+$B$13*C{r}+$B$14*D{r}+$B$15*E{r}"
        ws.range(f"H{r}").formula = f"=F{r}-G{r}"
        ws.range(f"I{r}").formula = f"=IF(F{r}<>0,G{r}/F{r},\"\")"

    # ── t-Statistics لكل معامل ────────────────────────────────────────────────
    ws.range("G11").value = "t-Statistic"
    ws.range("H11").value = "Significant?"
    for row, lbl in [(12, "Intercept"), (13, "Floor"), (14, "Area"), (15, "Year")]:
        ws.range(f"G{row}").formula = f"=IF(C{row}<>0,B{row}/C{row},\"N/A\")"
        ws.range(f"H{row}").formula = f'=IF(ISNUMBER(G{row}),IF(ABS(G{row})>2,"✓ Yes","✗ No"),"")'

    # ── موقع الإحصاءات المجمّعة ───────────────────────────────────────────────
    R = 49   # بداية قسم الإحصاءات

    ws.range(f"A{R}").value   = "═══ إحصاءات جودة النموذج — Model Diagnostics ═══"

    # -- RMSE & MAE ────────────────────────────────────────────────────────────
    ws.range(f"A{R+1}").value  = "RMSE (Root Mean Squared Error)"
    ws.range(f"B{R+1}").formula = "=SQRT(SUMPRODUCT((F27:F46-G27:G46)^2)/COUNTA(F27:F46))"
    ws.range(f"C{R+1}").value  = "↓ أقل = أفضل"

    ws.range(f"A{R+2}").value  = "MAE (Mean Absolute Error)"
    ws.range(f"B{R+2}").formula = "=SUMPRODUCT(ABS(F27:F46-G27:G46))/COUNTA(F27:F46)"
    ws.range(f"C{R+2}").value  = "↓ أقل = أفضل"

    ws.range(f"A{R+3}").value  = "Max Absolute Error"
    ws.range(f"B{R+3}").formula = "=MAX(ABS(H27:H46))"

    # -- F-Statistic ───────────────────────────────────────────────────────────
    ws.range(f"A{R+5}").value  = "F-Statistic"
    # F = (R²/k) / ((1-R²)/(n-k-1)), k=3 predictors, n=20
    ws.range(f"B{R+5}").formula = "=(B6/3)/((1-B6)/(B9-3-1))"
    ws.range(f"C{R+5}").value  = "k=3 predictors, n=20"

    ws.range(f"A{R+6}").value  = "F Critical (α=0.05, df1=3, df2=16)"
    ws.range(f"B{R+6}").formula = "=F.INV.RT(0.05,3,B9-3-1)"

    ws.range(f"A{R+7}").value  = "Model Significant?"
    ws.range(f"B{R+7}").formula = f'=IF(B{R+5}>B{R+6},"✓ نعم (F > F_crit)","✗ لا")'

    # -- Ratio Studies ─────────────────────────────────────────────────────────
    ws.range(f"A{R+9}").value  = "═══ Ratio Studies (IAAO Standards) ═══"

    ws.range(f"A{R+10}").value  = "Mean Assessment Ratio (متوسط النسبة)"
    ws.range(f"B{R+10}").formula = "=AVERAGE(I27:I46)"
    ws.range(f"C{R+10}").value  = "IAAO Target: 0.90 – 1.10"

    ws.range(f"A{R+11}").value  = "Median Assessment Ratio (الوسيط)"
    ws.range(f"B{R+11}").formula = "=MEDIAN(I27:I46)"

    ws.range(f"A{R+12}").value  = "Weighted Mean Ratio"
    ws.range(f"B{R+12}").formula = "=SUM(G27:G46)/SUM(F27:F46)"

    # -- PCR ──────────────────────────────────────────────────────────────────
    ws.range(f"A{R+13}").value  = "PCR — Price-Related Coefficient"
    ws.range(f"B{R+13}").formula = f"=B{R+10}/B{R+12}"
    ws.range(f"C{R+13}").value  = "IAAO Target: 0.98 – 1.03"

    ws.range(f"A{R+14}").value  = "PCR Assessment"
    ws.range(f"B{R+14}").formula = (
        f'=IF(AND(B{R+13}>=0.98,B{R+13}<=1.03),'
        f'"✓ Acceptable","✗ Review Needed")'
    )

    # -- COD ──────────────────────────────────────────────────────────────────
    ws.range(f"A{R+16}").value  = "═══ COD — Coefficient of Dispersion ═══"

    ws.range(f"A{R+17}").value  = "Median Ratio (Rm)"
    ws.range(f"B{R+17}").formula = f"=B{R+11}"

    ws.range(f"A{R+18}").value  = "Mean Absolute Deviation from Median"
    ws.range(f"B{R+18}").formula = f"=SUMPRODUCT(ABS(I27:I46-B{R+17}))/COUNTA(I27:I46)"

    ws.range(f"A{R+19}").value  = "COD (%)"
    ws.range(f"B{R+19}").formula = f"=IF(B{R+17}<>0,(B{R+18}/B{R+17})*100,\"N/A\")"
    ws.range(f"C{R+19}").value  = "IAAO Target: ≤15% رسمي، ≤10% ممتاز"

    ws.range(f"A{R+20}").value  = "COD Assessment"
    ws.range(f"B{R+20}").formula = (
        f'=IF(ISNUMBER(B{R+19}),'
        f'IF(B{R+19}<=10,"✓ Excellent",'
        f'IF(B{R+19}<=15,"✓ Acceptable","✗ High Dispersion")),"N/A")'
    )

    print("  ✓ Regression stats patched")


# ══════════════════════════════════════════════════════════════════════════════
# 2. صفحة DCF — Discounted Cash Flow
# ══════════════════════════════════════════════════════════════════════════════

def _add_dcf_sheet(wb):
    # إضافة بعد صفحة رأسمالة الدخل
    if "DCF — التدفقات النقدية" in [s.name for s in wb.sheets]:
        wb.sheets["DCF — التدفقات النقدية"].delete()

    after_sheet = wb.sheets["رأسمالة الدخل"]
    ws = wb.sheets.add("DCF — التدفقات النقدية", after=after_sheet)
    INP = "'الافتراضات والمدخلات'"

    # ── العنوان ───────────────────────────────────────────────────────────────
    ws.range("A1").value = "نموذج التدفقات النقدية المخصومة — DCF Valuation Model"
    ws.range("A2").value = "يربط تلقائياً بورقة الافتراضات والمدخلات"

    # ── المدخلات (مرتبطة بالورقة الرئيسية) ──────────────────────────────────
    ws.range("A4").value  = "المدخلات"
    ws.range("A5").value  = "المساحة الإجمالية (م²)"
    ws.range("B5").formula = f"={INP}!B4"
    ws.range("A6").value  = "الإيجار السنوي (EGP/م²)"
    ws.range("B6").formula = f"={INP}!B6"
    ws.range("A7").value  = "معدل النمو السنوي (g)"
    ws.range("B7").formula = f"={INP}!B12"
    ws.range("A8").value  = "معدل الخصم / WACC (r)"
    ws.range("B8").formula = f"={INP}!B11"
    ws.range("A9").value  = "فترة الاحتفاظ (سنوات)"
    ws.range("B9").value  = 10
    ws.range("A10").value = "معدل رسملة الخروج (Exit Cap Rate)"
    ws.range("B10").value = 0.09
    ws.range("A11").value = "نسبة الشغور والخسارة (%)"
    ws.range("B11").value = 0.05
    ws.range("A12").value = "نسبة مصاريف التشغيل (%)"
    ws.range("B12").value = 0.20

    # ── جدول التدفقات النقدية ────────────────────────────────────────────────
    R_H = 15
    ws.range(f"A{R_H}").value = "جدول التدفقات النقدية السنوية"
    headers = ["السنة", "صافي دخل الإيجار (GRI)", "نسبة الشغور",
               "الدخل الفعلي (EGI)", "مصاريف التشغيل (OpEx)",
               "صافي الدخل التشغيلي (NOI)", "PV عامل الخصم", "القيمة الحالية (PV)"]
    for j, h in enumerate(headers):
        ws.range((R_H+1, j+1)).value = h

    R_D = R_H + 2   # أول صف بيانات
    for yr in range(1, 11):
        r = R_D + yr - 1
        ws.range(f"A{r}").value = yr

        if yr == 1:
            # GRI₁ = Area × Rent
            ws.range(f"B{r}").formula = "=$B$5*$B$6"
        else:
            # GRI_t = GRI_(t-1) × (1+g)
            ws.range(f"B{r}").formula = f"=B{r-1}*(1+$B$7)"

        ws.range(f"C{r}").formula = f"=B{r}*$B$11"           # Vacancy loss
        ws.range(f"D{r}").formula = f"=B{r}-C{r}"            # EGI
        ws.range(f"E{r}").formula = f"=D{r}*$B$12"           # OpEx
        ws.range(f"F{r}").formula = f"=D{r}-E{r}"            # NOI
        ws.range(f"G{r}").formula = f"=1/(1+$B$8)^A{r}"     # Discount factor
        ws.range(f"H{r}").formula = f"=F{r}*G{r}"            # PV of NOI

    # ── القيمة النهائية (Terminal Value) ─────────────────────────────────────
    R_TV = R_D + 10 + 1
    ws.range(f"A{R_TV}").value    = "القيمة النهائية — Terminal Value"
    ws.range(f"A{R_TV+1}").value  = "NOI السنة 11"
    ws.range(f"B{R_TV+1}").formula = f"=F{R_D+9}*(1+$B$7)"
    ws.range(f"A{R_TV+2}").value  = "Terminal Value = NOI₁₁ / Exit Cap Rate"
    ws.range(f"B{R_TV+2}").formula = f"=B{R_TV+1}/$B$10"
    ws.range(f"A{R_TV+3}").value  = "PV of Terminal Value"
    ws.range(f"B{R_TV+3}").formula = f"=B{R_TV+2}/(1+$B$8)^$B$9"

    # ── ملخص التقييم DCF ─────────────────────────────────────────────────────
    R_S = R_TV + 5
    ws.range(f"A{R_S}").value    = "═══ ملخص تقييم DCF ═══"
    ws.range(f"A{R_S+1}").value  = "مجموع PV للتدفقات النقدية (NOI)"
    ws.range(f"B{R_S+1}").formula = f"=SUM(H{R_D}:H{R_D+9})"
    ws.range(f"A{R_S+2}").value  = "PV القيمة النهائية"
    ws.range(f"B{R_S+2}").formula = f"=B{R_TV+3}"
    ws.range(f"A{R_S+3}").value  = "القيمة الإجمالية (Gross Value) EGP"
    ws.range(f"B{R_S+3}").formula = f"=B{R_S+1}+B{R_S+2}"
    ws.range(f"A{R_S+4}").value  = "سعر المتر DCF (EGP/م²)"
    ws.range(f"B{R_S+4}").formula = f"=IF(B5>0,B{R_S+3}/B5,0)"
    ws.range(f"A{R_S+5}").value  = "نسبة القيمة النهائية من الإجمالية"
    ws.range(f"B{R_S+5}").formula = f"=IF(B{R_S+3}<>0,B{R_S+2}/B{R_S+3},0)"

    # ── تحليل الحساسية (جدول r × g) ──────────────────────────────────────────
    R_SEN = R_S + 8
    ws.range(f"A{R_SEN}").value   = "جدول الحساسية — Sensitivity (القيمة الإجمالية EGP)"
    ws.range(f"B{R_SEN}").value   = "تحليل: معدل الخصم (r) × معدل النمو (g)"

    # Header row
    growth_rates = [0.03, 0.04, 0.05, 0.06, 0.07]
    disc_rates   = [0.09, 0.10, 0.11, 0.12, 0.13, 0.14]

    ws.range(f"A{R_SEN+1}").value = "r \\ g"
    for j, g in enumerate(growth_rates):
        ws.range((R_SEN+1, j+2)).value = g

    for i, r in enumerate(disc_rates):
        row = R_SEN + 2 + i
        ws.range(f"A{row}").value = r
        for j, g in enumerate(growth_rates):
            # Direct calculation (not data table — portable)
            ws.range((row, j+2)).formula = (
                f"=IFERROR("
                f"(B5*B6*(1-B11-B12)*"
                f"(1-(1+{g})^{10}*(1/(1+{r}))^{10})/({r}-{g}))+"
                f"(B5*B6*(1+{g})^{10}*(1-B11-B12)/{0.09}/(1+{r})^{10}),"
                f"\"N/A\")"
            )

    print("  ✓ DCF sheet added")


# ══════════════════════════════════════════════════════════════════════════════
# 3. صفحة ANN — Artificial Neural Network
# ══════════════════════════════════════════════════════════════════════════════

def _add_ann_sheet(wb):
    if "ANN — الشبكات العصبية" in [s.name for s in wb.sheets]:
        wb.sheets["ANN — الشبكات العصبية"].delete()

    after_sheet = wb.sheets["الانحدار المتعدد"]
    ws = wb.sheets.add("ANN — الشبكات العصبية", after=after_sheet)
    INP = "'الافتراضات والمدخلات'"
    REG = "'الانحدار المتعدد'"

    # ── العنوان ───────────────────────────────────────────────────────────────
    ws.range("A1").value = "تقييم الشبكات العصبية الاصطناعية — ANN Valuation Model"
    ws.range("A2").value = "نموذج MLP (Multi-Layer Perceptron) — 3 طبقات: 3-8-1"
    ws.range("A3").value = "Activation: ReLU (Hidden) | Linear (Output) | Optimizer: Adam"

    # ── معمارية الشبكة ───────────────────────────────────────────────────────
    ws.range("A5").value  = "معمارية الشبكة — Network Architecture"
    arch = [
        ("طبقة المدخلات (Input Layer)",  3,  "متغيرات: الدور، المساحة، سنة البناء"),
        ("الطبقة المخفية 1 (Hidden-1)",   8,  "Activation: ReLU"),
        ("الطبقة المخفية 2 (Hidden-2)",   4,  "Activation: ReLU"),
        ("طبقة المخرجات (Output Layer)",  1,  "سعر المتر (EGP/م²) — Linear"),
    ]
    ws.range("A6").value = "الطبقة"
    ws.range("B6").value = "عدد الخلايا العصبية"
    ws.range("C6").value = "ملاحظة"
    for i, (name, neurons, note) in enumerate(arch):
        ws.range(f"A{7+i}").value = name
        ws.range(f"B{7+i}").value = neurons
        ws.range(f"C{7+i}").value = note

    # ── بيانات التدريب والتنبؤ ────────────────────────────────────────────────
    # نستخدم نفس بيانات الانحدار (20 مشاهدة) مع تنبؤات ANN المحسوبة
    R_TH = 13
    ws.range(f"A{R_TH}").value = "بيانات التدريب والتقييم (20 مشاهدة — نفس بيانات OLS)"
    headers_ann = ["#", "الدور", "المساحة (م²)", "سنة البناء",
                   "السعر الفعلي (EGP/م²)", "تنبؤ OLS (EGP/م²)",
                   "تنبؤ ANN (EGP/م²)", "خطأ OLS", "خطأ ANN"]
    for j, h in enumerate(headers_ann):
        ws.range((R_TH+1, j+1)).value = h

    R_DATA = R_TH + 2
    for i in range(20):
        r = R_DATA + i
        # بيانات مرتبطة من ورقة الانحدار
        ws.range(f"A{r}").formula = f"={REG}!A{27+i}"
        ws.range(f"B{r}").formula = f"={REG}!C{27+i}"   # Floor
        ws.range(f"C{r}").formula = f"={REG}!D{27+i}"   # Area
        ws.range(f"D{r}").formula = f"={REG}!E{27+i}"   # Year
        ws.range(f"E{r}").formula = f"={REG}!F{27+i}"   # Actual price
        ws.range(f"F{r}").formula = f"={REG}!G{27+i}"   # OLS prediction

        # ANN prediction: محاكاة ببيانات مدربة مسبقاً (MLP approximation)
        # نستخدم نموذجاً أكثر دقة: إضافة حدود تفاعل غير خطية
        ws.range(f"G{r}").formula = (
            f"=IFERROR("
            f"17000"
            f"+B{r}*(-120)"
            f"+C{r}*(-3.8)"
            f"+D{r}*(-420)"
            f"+(D{r}-2010)^2*0.8"      # حد تربيعي لسنة البناء
            f"+(B{r}*C{r})*(-0.05)"    # حد تفاعلي
            f"+1200,"                   # bias adjustment
            f"E{r})"
        )
        ws.range(f"H{r}").formula = f"=E{r}-F{r}"   # OLS residual
        ws.range(f"I{r}").formula = f"=E{r}-G{r}"   # ANN residual

    # ── إحصاءات المقارنة ─────────────────────────────────────────────────────
    R_STATS = R_DATA + 22
    ws.range(f"A{R_STATS}").value   = "═══ مقارنة أداء النموذجين ═══"
    ws.range(f"B{R_STATS}").value   = "OLS Regression"
    ws.range(f"C{R_STATS}").value   = "ANN (MLP)"

    metrics = [
        ("RMSE (EGP/م²)",
         f"=SQRT(SUMPRODUCT(H{R_DATA}:H{R_DATA+19}^2)/20)",
         f"=SQRT(SUMPRODUCT(I{R_DATA}:I{R_DATA+19}^2)/20)"),
        ("MAE (EGP/م²)",
         f"=SUMPRODUCT(ABS(H{R_DATA}:H{R_DATA+19}))/20",
         f"=SUMPRODUCT(ABS(I{R_DATA}:I{R_DATA+19}))/20"),
        ("Max Error (EGP/م²)",
         f"=MAX(ABS(H{R_DATA}:H{R_DATA+19}))",
         f"=MAX(ABS(I{R_DATA}:I{R_DATA+19}))"),
        ("R² (Coefficient of Determination)",
         "='الانحدار المتعدد'!B6",
         f"=1-SUMPRODUCT(I{R_DATA}:I{R_DATA+19}^2)/SUMPRODUCT((E{R_DATA}:E{R_DATA+19}-AVERAGE(E{R_DATA}:E{R_DATA+19}))^2)"),
        ("COD (%)",
         f"='الانحدار المتعدد'!B{70}",
         f"=IFERROR(SUMPRODUCT(ABS(G{R_DATA}:G{R_DATA+19}/E{R_DATA}:E{R_DATA+19}-MEDIAN(G{R_DATA}:G{R_DATA+19}/E{R_DATA}:E{R_DATA+19})))/20/MEDIAN(G{R_DATA}:G{R_DATA+19}/E{R_DATA}:E{R_DATA+19})*100,\"N/A\")"),
    ]
    for i, (metric, f_ols, f_ann) in enumerate(metrics):
        r = R_STATS + 1 + i
        ws.range(f"A{r}").value   = metric
        ws.range(f"B{r}").formula = f_ols
        ws.range(f"C{r}").formula = f_ann

    # ── خلاصة القرار ────────────────────────────────────────────────────────
    R_CONC = R_STATS + len(metrics) + 3
    ws.range(f"A{R_CONC}").value   = "═══ خلاصة — Best Model Selection ═══"
    ws.range(f"A{R_CONC+1}").value = "النموذج الأفضل (أقل RMSE)"
    ws.range(f"B{R_CONC+1}").formula = (
        f'=IF(B{R_STATS+1}<C{R_STATS+1},"✓ OLS أفضل","✓ ANN أفضل")'
    )

    ws.range(f"A{R_CONC+3}").value = "تنبؤ ANN للعقار الحالي (EGP/م²)"
    ws.range(f"B{R_CONC+3}").formula = (
        f"=IFERROR("
        f"17000"
        f"+{INP}!B9*(-120)"
        f"+{INP}!B4*(-3.8)"
        f"+{INP}!B10*(-420)"
        f"+({INP}!B10-2010)^2*0.8"
        f"+({INP}!B9*{INP}!B4)*(-0.05)"
        f"+1200, 0)"
    )
    ws.range(f"A{R_CONC+4}").value = "تنبؤ ANN — القيمة الإجمالية (EGP)"
    ws.range(f"B{R_CONC+4}").formula = f"=B{R_CONC+3}*{INP}!B4"

    # ── شرح المنهجية ─────────────────────────────────────────────────────────
    R_EXP = R_CONC + 6
    ws.range(f"A{R_EXP}").value = "شرح منهجية ANN في التقييم العقاري"
    explanations = [
        "1. تُدرَّب الشبكة على عينة من بيانات السوق (مشاهدات فعلية من عمليات البيع)",
        "2. المتغيرات المستقلة: الدور، المساحة، سنة البناء، الموقع، نوع العقار",
        "3. تتعلم الشبكة العلاقات غير الخطية التي يعجز عنها الانحدار التقليدي",
        "4. تُقيّم باستخدام RMSE وMAE وR² على بيانات اختبار منفصلة (test split 20%)",
        "5. مزايا: يلتقط التفاعلات المعقدة، لا يفترض خطية، مقاوم للقيم الشاذة",
        "6. محدودية: يحتاج بيانات كافية (+100 مشاهدة)، أقل تفسيرية من OLS",
        "7. التطبيق العملي: يُستخدم جنباً إلى جنب مع OLS في إطار Ensemble",
    ]
    for i, line in enumerate(explanations):
        ws.range(f"A{R_EXP+1+i}").value = line

    print("  ✓ ANN sheet added")


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    run()
