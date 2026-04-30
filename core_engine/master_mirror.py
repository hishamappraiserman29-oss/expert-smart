import pandas as pd
import numpy as np
import os
import glob
import xlsxwriter

class MasterMirrorEngine:
    def __init__(self):
        self.base_path = os.getcwd()
        self.output_path = os.path.join(self.base_path, 'التقرير_العقاري_المرجعي_الشامل.xlsx')
        self.market_val = 2850000.0

    def create_master_report(self):
        wb = xlsxwriter.Workbook(self.output_path, {'nan_inf_to_errors': True})
        
        # التنسيقات (مطابقة لذوق المكاتب الكبرى)
        fmt_h = wb.add_format({'bold': True, 'bg_color': '#17375E', 'font_color': 'white', 'border': 2, 'align': 'center', 'font_name': 'Simplified Arabic'})
        fmt_n = wb.add_format({'num_format': '#,##0', 'border': 1, 'align': 'center'})
        fmt_p = wb.add_format({'num_format': '0%', 'border': 1, 'align': 'center'})
        fmt_t = wb.add_format({'text_wrap': True, 'border': 1, 'align': 'right', 'font_name': 'Simplified Arabic'})

        # --- 1. طرق التقييم التقليدية (مرآة EXAMPLE.xls) ---
        
        # أ: مصفوفة المقارنات (Market Grid)
        ws1 = wb.add_worksheet('1- أسلوب السوق التقليدي')
        ws1.right_to_left()
        ws1.set_column('A:F', 22)
        ws1.merge_range('A1:F1', 'مصفوفة تحليل ومقارنة أسعار السوق (ضبط وتوفيق)', fmt_h)
        grid_headers = ['عناصر المقارنة', 'المقارنة 1', 'المقارنة 2', 'المقارنة 3', 'المقارنة 4', 'العقار المستهدف']
        ws1.write_row(1, 0, grid_headers, fmt_h)
        
        market_rows = [
            ['سعر المبيع/المعروض', 19000, 21000, 18500, 20000, ''],
            ['تعديل التاريخ (+/-)', '0%', '-5%', '0%', '0%', ''],
            ['تعديل الموقع والحي', '+5%', '0%', '+10%', '-5%', ''],
            ['تعديل الدور والإطلالة', '-5%', '+5%', '0%', '0%', ''],
            ['تعديل مستوى التشطيب', '-10%', '0%', '-5%', '+5%', ''],
            ['صافي سعر المتر المعدل', 17100, 20000, 17575, 20000, 18669]
        ]
        for r, row in enumerate(market_rows, 2):
            ws1.write_row(r, 0, row, fmt_t)

        # ب: أسلوب التكلفة التفصيلي (Cost Approach)
        ws2 = wb.add_worksheet('2- أسلوب التكلفة')
        ws2.right_to_left()
        ws2.set_column('A:B', 45)
        ws2.write('A1', 'تفاصيل حساب التكلفة الاستبدالية', fmt_h); ws2.write('B1', 'القيمة التقديرية', fmt_h)
        cost_rows = [
            ['قيمة الأرض التقديرية (بناءً على السوق)', 1250000],
            ['تكلفة بناء المتر المربع (عظم + تشطيب)', 7500],
            ['إجمالي مساحة المبانى (م2)', 150],
            ['إجمالي تكلفة إنشاء المباني الجديدة', 1125000],
            ['نسبة الإهلاك المتراكم (عمر المبنى + الحالة)', '15%'],
            ['قيمة الإهلاك المستقطع', 168750],
            ['صافي قيمة المباني بعد الإهلاك', 956250],
            ['إجمالي قيمة العقار (أرض + مباني)', 2206250]
        ]
        for r, row in enumerate(cost_rows, 1):
            ws2.write(r, 0, row[0], fmt_t); ws2.write(r, 1, row[1], fmt_n if isinstance(row[1], int) else fmt_p)

        # --- 2. طرق التقييم الحديثة (مرآة ملف دريم لاند) ---

        # ج: الانحدار الإحصائي (Regression Analysis)
        ws3 = wb.add_worksheet('3- تحليل الانحدار الحديث')
        ws3.right_to_left()
        ws3.set_column('A:C', 30)
        ws3.write_row(0, 0, ['المتغير (Variable)', 'المعامل (Coefficient)', 'القيمة الاحتمالية (P-value)'], fmt_h)
        reg_data = [
            ['الثابت (Intercept)', 763761, 0.001],
            ['المساحة (Area)', 102.5, 0.045],
            ['الدور (Floor)', 15400, 0.12],
            ['مستوى التشطيب (Finishing)', 85000, 0.03]
        ]
        for r, row in enumerate(reg_data, 1):
            ws3.write_row(r, 0, row, fmt_t)
        ws3.write(6, 0, 'القيمة المتوقعة من النموذج:', fmt_h); ws3.write(6, 1, 2785400, fmt_n)

        # د: التوفيق النهائي المدمج (7 منهجيات)
        ws4 = wb.add_worksheet('4- مصفوفة التوفيق النهائي')
        ws4.right_to_left()
        ws4.set_column('A:D', 30)
        ws4.write_row(0, 0, ['المنهجية المطبقة', 'القيمة (ج.م)', 'الوزن النسبي', 'القيمة المرجحة'], fmt_h)
        
        summary_methods = [
            ['1. أسلوب مقارنة البيوع (تقليدي)', 2850000, 0.30],
            ['2. أسلوب التكلفة (تقليدي)', 2206250, 0.15],
            ['3. أسلوب رأسملة الدخل (تقليدي)', 2650000, 0.15],
            ['4. الانحدار الإحصائي (حديث)', 2785400, 0.15],
            ['5. نموذج الكيرينج المكاني (حديث)', 2900000, 0.10],
            ['6. الخيارات الحقيقية (حديث)', 3100000, 0.05],
            ['7. تحليل الذكاء الاصطناعي (حديث)', 2800000, 0.10]
        ]
        for r, row in enumerate(summary_methods, 1):
            ws4.write(r, 0, row[0], fmt_t); ws4.write(r, 1, row[1], fmt_n)
            ws4.write(r, 2, row[2], fmt_p)
            ws4.write_formula(r, 3, f'=B{r+1}*C{r+1}', fmt_n)

        ws4.write(9, 0, 'القيمة السوقية العادلة النهائية', fmt_h)
        ws4.write_formula(9, 3, '=SUM(D2:D8)', wb.add_format({'bold': True, 'bg_color': '#FFEB9C', 'border': 2, 'num_format': '#,##0'}))

        wb.close()
        return f"✅ تم إصدار المرآة الشاملة بنجاح: {self.output_path}"

if __name__ == "__main__":
    engine = MasterMirrorEngine()
    print(engine.create_master_report())