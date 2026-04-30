# test_valuation.py
import json

def calculate_dcf(data: dict) -> dict:
    """
    Calculates the Discounted Cash Flow (DCF) valuation.
    """
    try:
        print("\n" + "="*50)
        print("بدء عملية التقييم بطريقة DCF")
        print("="*50)
        
        # استخراج البيانات
        imp = data.get("valuation_data", {}).get("income_dcf_data", {})
        print(f"\n📊 البيانات المستخرجة:")
        print(f"   - NOI السنوي: {imp.get('noi_annual')}")
        print(f"   - معدل الخصم: {imp.get('discount_rate_percent')}%")
        print(f"   - معدل النمو: {imp.get('growth_rate_percent')}%")
        print(f"   - معدل الخروج: {imp.get('exit_yield_percent')}%")
        print(f"   - عدد السنوات: {imp.get('projection_years')}")
        
        # تحويل إلى أرقام
        noi = float(imp.get("noi_annual", 0))
        discount_rate = float(imp.get("discount_rate_percent", 12)) / 100
        growth_rate = float(imp.get("growth_rate_percent", 3)) / 100
        exit_yield = float(imp.get("exit_yield_percent", 8)) / 100
        years = int(imp.get("projection_years", 5))

        print(f"\n🔢 القيم المحولة:")
        print(f"   - NOI: {noi:,.2f}")
        print(f"   - معدل الخصم: {discount_rate:.2%}")
        print(f"   - معدل النمو: {growth_rate:.2%}")
        print(f"   - معدل الخروج: {exit_yield:.2%}")
        print(f"   - السنوات: {years}")

        total_npv = 0.0
        running_noi = noi

        print(f"\n📈 تفاصيل التدفقات النقدية لكل سنة:")
        print("-" * 40)

        # DCF Loop
        for t in range(1, years + 1):
            running_noi *= (1 + growth_rate)
            cash_flow_present_value = running_noi / ((1 + discount_rate) ** t)
            total_npv += cash_flow_present_value
            
            print(f"   السنة {t}:")
            print(f"      NOI: {running_noi:,.2f}")
            print(f"      القيمة الحالية: {cash_flow_present_value:,.2f}")

        # Terminal Value
        terminal_cash_flow = running_noi * (1 + growth_rate)
        terminal_value = terminal_cash_flow / exit_yield
        discounted_terminal_value = terminal_value / ((1 + discount_rate) ** years)

        final_dcf = total_npv + discounted_terminal_value

        print(f"\n📊 النتائج النهائية:")
        print("-" * 40)
        print(f"   مجموع NPV: {total_npv:,.2f}")
        print(f"   قيمة التصفية: {terminal_value:,.2f}")
        print(f"   القيمة المخصومة للتصفية: {discounted_terminal_value:,.2f}")
        print(f"   ✨ القيمة النهائية DCF: {final_dcf:,.2f}")

        return {
            "calculated_dcf_final": round(final_dcf, 2),
            "terminal_value": round(terminal_value, 2),
            "discounted_terminal_value": round(discounted_terminal_value, 2),
            "npv_cash_flows": round(total_npv, 2),
            "calculation_status": "Validated by Python Engine",
            "input_parameters": {
                "noi_annual": noi,
                "discount_rate_percent": discount_rate * 100,
                "growth_rate_percent": growth_rate * 100,
                "exit_yield_percent": exit_yield * 100,
                "projection_years": years
            }
        }

    except Exception as e:
        print(f"\n❌ خطأ في الحساب: {str(e)}")
        return {
            "calculated_dcf_final": 0,
            "calculation_status": f"Error: {str(e)}"
        }

# ============ برنامج التجربة ============
if __name__ == "__main__":
    print("🚀 بدء تشغيل اختبار نظام التقييم العقاري")
    
    # البيانات الصحيحة
    property_data_correct = {
        "valuation_data": {
            "income_dcf_data": {
                "noi_annual": 500000,
                "discount_rate_percent": 10,
                "growth_rate_percent": 2,
                "exit_yield_percent": 8,
                "projection_years": 5
            }
        }
    }
    
    # استدعاء الدالة
    result = calculate_dcf(property_data_correct)
    
    print("\n" + "="*50)
    print("✅ النتيجة النهائية:")
    print("="*50)
    print(json.dumps(result, indent=4, ensure_ascii=False))
    
    # تجربة مع بيانات خاطئة
    print("\n" + "="*50)
    print("تجربة مع بيانات خاطئة:")
    print("="*50)
    wrong_data = {"wrong_key": "wrong_value"}
    wrong_result = calculate_dcf(wrong_data)
    print(json.dumps(wrong_result, indent=4, ensure_ascii=False))