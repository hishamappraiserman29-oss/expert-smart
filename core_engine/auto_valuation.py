import os
import json
from datetime import datetime

def format_currency(value):
    """تنسيق الرقم مع إضافة فواصل الآلاف"""
    return "{:,.0f}".format(value)

def arabic_number_to_words(number):
    """
    دالة مبسطة لتحويل بعض الأرقام الشائعة إلى كلمات 
    (لأغراض العرض التوضيحي، يمكن توسيعها لاحقاً لتدعم كافة الأرقام)
    """
    mapping = {
        1000000: "مليون",
        2000000: "مليونا",
        3000000: "ثلاثة ملايين",
        4000000: "أربعة ملايين",
        5000000: "خمسة ملايين",
        6000000: "ستة ملايين",
        7000000: "سبعة ملايين",
        8000000: "ثمانية ملايين",
        9000000: "تسعة ملايين",
        10000000: "عشرة ملايين"
    }
    return mapping.get(number, str(number))

def generate_valuation_record(
    area=400, 
    price_per_sqm=10000, 
    property_type="فيلا سكنية", 
    location="الرياض", 
    specs="تشطيب فاخر وموقع استراتيجي",
    region="SA"
):
    """
    تقوم هذه الدالة بإنشاء تقرير تقييم مبسط وتنسيقه ليتم استخدامه كملف تدريب (JSONL) أو كتقرير نهائي.
    """
    # 1. إعداد المتغيرات حسب المنطقة
    if region == "SA":
        currency_name = "ريال سعودي"
        standard = "للبيانات والمعايير المعتمدة من الهيئة السعودية للمقيمين المعتمدين (تقييم)"
    else:
        currency_name = "جنيه مصري"
        standard = "للمعايير المصرية للتقييم العقاري"
        
    # 2. الحسابات
    total_value = area * price_per_sqm
    
    # 3. صياغة التقرير (المخرجات)
    output_text = (
        f"يُقدر سعر المتر للـ {property_type} المماثلة في منطقة {location} بـ {format_currency(price_per_sqm)} {currency_name}، "
        f"وبناءً عليه فإن القيمة السوقية الإجمالية التقديرية تبلغ {format_currency(total_value)} {currency_name} "
    )
    
    # محاولة إضافة نص الرقم بالحروف إذا كان متوفراً
    word_num = arabic_number_to_words(total_value)
    if word_num != str(total_value):
        output_text += f"({word_num} {currency_name})، "
    else:
        output_text += "، "
        
    output_text += f"وهو ما تدعمه المواصفات: {specs}، وفقاً {standard}."

    # 4. تجهيز هيكل البيانات (للتوافق مع نموذج التدريب)
    record = {
        "instruction": "قم بتقييم هذا العرض بناءً على المواصفات الفنية المرفقة.",
        "input": f"{property_type} - {location} - {area}م - {specs}.",
        "output": output_text,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "region": region,
            "calculated_total": total_value
        }
    }
    
    return record

def save_to_jsonl(record, output_dir="../shared_data", filename="generated_valuations.jsonl"):
    """
    حفظ السجل في ملف JSONL
    """
    # تجهيز المسار
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, filename)
    
    # الكتابة للملف (إضافة)
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        
    print(f"✅ تم حفظ التقييم بنجاح في: {file_path}")
    return file_path

if __name__ == "__main__":
    # تجربة الدالة بناءً على طلب المستخدم (فيلا 400 متر)
    print("... جاري حساب وتوليد تقييم للفيلا ...\n")
    
    # استدعاء الدالة
    valuation_record = generate_valuation_record(
        area=400,
        price_per_sqm=10000,
        property_type="فيلا سكنية",
        location="الرياض",
        specs="تشطيب فاخر وموقع استراتيجي",
        region="SA"
    )
    
    # طباعة النتيجة
    print("المدخلات (Input):")
    print(valuation_record["input"])
    print("-" * 40)
    print("التحليل والتقييم (Output):")
    print(valuation_record["output"])
    print("-" * 40)
    
    # حفظ النتيجة في ملف
    # تحديد مسار shared_data بشكل ديناميكي بحيث يرجع خطوة للخلف من مجلد core_engine
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    shared_data_dir = os.path.join(base_dir, "shared_data")
    
    save_to_jsonl(valuation_record, output_dir=shared_data_dir)
