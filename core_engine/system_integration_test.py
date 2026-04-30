import os
import re
import sys
import datetime

# Ensure we can import from core_engine
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from valuation_logic import calculate_property_valuation
from report_generator import generate_professional_report

def run_integration_test():
    print("--- 🚀 بدء اختبار تكامل النظام (System Integration Test) ---")
    
    # 1. إثبات قراءة ملف معايير التقييم من التدريب
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    train_file = os.path.join(base_dir, "shared_data", "train_ready_fixed.jsonl")
    try:
        with open(train_file, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            print(f"✅ تم قراءة معايير التدريب بنجاح (عينة): {first_line[:50]}...")
    except Exception as e:
        print(f"⚠️ تحذير: لم يتم العثور على ملف التدريب: {e}")
        
    # 2. تحديد معطيات الاختبار واستخراجها
    test_query = "قيم فيلا مساحتها 450 متر في حي الملقا بالرياض"
    
    # استخراج المساحة والحي (محاكاة لاستخراج الذكاء الاصطناعي أو RegEx)
    area_sqm = 0
    match_area = re.search(r'(\d+)\s*(متر|m|sqm)', test_query.lower())
    if match_area:
        area_sqm = float(match_area.group(1))
        
    # استخراج الموقع (تبسيطاً بـ RegEx للبحث عن حي كذا)
    location = "غير محدد"
    match_loc = re.search(r'في (حي .*?\sبالرياض|حي .*?)', test_query)
    if match_loc:
        location = match_loc.group(1)

    print(f"✅ تم استخراج المساحة: {area_sqm} متر مربع")
    print(f"✅ تم استخراج الموقع: {location}")
    
    # افتراض سعر المتر لحي الملقا بالرياض
    price_per_meter = 15000 
    
    # 3. استخدام دالة دالة valuation_logic.py
    report_text = calculate_property_valuation(area_sqm, price_per_meter, region="SA")
    total_value = area_sqm * price_per_meter
    
    # 4. توليد تقرير Word وحفظه باستخدام report_generator.py
    case_data = {
        "region": "SA",
        "property_type": "فيلا سكنية",
        "area": area_sqm,
        "price_per_meter": price_per_meter,
        "total_value": total_value,
        "location": location
    }
    
    word_file_path = generate_professional_report(case_data)
    
    # 5. رسالة التأكيد النهائية للمستخدم
    print("\n" + "="*50)
    print("🎯 رسالة تأكيد النظام (System Validation Message)")
    print("="*50)
    print(f"المساحة المكتشفة: {area_sqm} متر مربع")
    print(f"السعر الإجمالي: {total_value:,.2f} ريال سعودي")
    print(f"مسار ملف الـ Word: {word_file_path}")
    print("="*50)
    
if __name__ == "__main__":
    run_integration_test()
