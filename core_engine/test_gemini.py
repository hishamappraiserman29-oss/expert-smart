# test_gemini.py
import os
import sys
import google.generativeai as genai
from dotenv import load_dotenv

# تحميل متغيرات البيئة
load_dotenv()

print("=" * 60)
print("🔍 اختبار الاتصال بـ Google Gemini API")
print("=" * 60)

# 1. التحقق من وجود المفتاح
api_key = os.getenv("GEMINI_API_KEY")
print(f"\n📌 الخطوة 1: التحقق من مفتاح API")
print(f"   - ملف .env موجود: {'✅' if os.path.exists('.env') else '❌'}")
print(f"   - المفتاح موجود: {'✅' if api_key else '❌'}")

if not api_key:
    print("\n❌ لم يتم العثور على مفتاح API!")
    print("\n📝 كيفية الحصول على مفتاح API:")
    print("   1. اذهب إلى https://aistudio.google.com/")
    print("   2. سجل الدخول بحساب Google")
    print("   3. اضغط على 'Get API Key'")
    print("   4. أنشئ مفتاح جديد")
    print("   5. أضفه في ملف .env بهذا الشكل:")
    print("      GEMINI_API_KEY=المفتاح_الخاص_بك")
    sys.exit(1)

# 2. تكوين الاتصال
print(f"\n📌 الخطوة 2: تكوين الاتصال بـ Gemini")
try:
    genai.configure(api_key=api_key)
    print("   ✅ تم التكوين بنجاح")
except Exception as e:
    print(f"   ❌ فشل التكوين: {e}")
    sys.exit(1)

# 3. جلب قائمة النماذج المتاحة
print(f"\n📌 الخطوة 3: جلب قائمة النماذج المتاحة")
try:
    models = list(genai.list_models())
    print(f"   ✅ تم العثور على {len(models)} نموذج")
    
    print("\n   النماذج التي تدعم generateContent:")
    for m in models:
        if 'generateContent' in m.supported_generation_methods:
            print(f"   • {m.name}")
except Exception as e:
    print(f"   ❌ فشل في جلب النماذج: {e}")

# 4. محاولة الاتصال بنماذج مختلفة
print(f"\n📌 الخطوة 4: اختبار النماذج المختلفة")

models_to_test = [
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-pro",
    "models/gemini-1.5-flash",
    "models/gemini-pro"
]

success = False
for model_name in models_to_test:
    print(f"\n   🔄 محاولة: {model_name}")
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("قل 'مرحباً' باللغة العربية")
        
        # استخراج النص من الاستجابة
        if hasattr(response, 'text'):
            result = response.text
        else:
            result = str(response)
            
        print(f"   ✅ نجح! الرد: {result[:50]}...")
        success = True
        break
    except Exception as e:
        print(f"   ❌ فشل: {str(e)[:100]}")

# 5. اختبار رفع ملف (اختياري)
if success:
    print(f"\n📌 الخطوة 5: اختبار رفع ملف (اختياري)")
    test_file = "test.txt"
    try:
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("هذا ملف اختبار")
        
        uploaded = genai.upload_file(test_file)
        print(f"   ✅ تم رفع الملف بنجاح: {uploaded.name}")
        os.remove(test_file)
    except Exception as e:
        print(f"   ⚠️ رفع الملف غير متاح: {e}")

print("\n" + "=" * 60)
if success:
    print("✅✅✅ الاتصال بـ Gemini يعمل بنجاح! ✅✅✅")
else:
    print("❌❌❌ فشل الاتصال بـ Gemini ❌❌❌")
    print("\n🔧 الحلول المقترحة:")
    print("1. تأكد من صحة مفتاح API")
    print("2. تأكد من تفعيل الفوترة في Google Cloud")
    print("3. جرب استخدام VPN إذا كنت في منطقة محظورة")
    print("4. انتظر بضع دقائق وحاول مجدداً")
print("=" * 60)