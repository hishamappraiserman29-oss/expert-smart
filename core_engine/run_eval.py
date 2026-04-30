import sys
import os

sys.path.append(r'c:\Users\Lenovo\Desktop\expert_smart\core_engine')
from valuation_logic import advanced_valuation, get_estimated_price
from report_generator import generate_professional_report

location = 'حي الياسمين'
price_per_meter = get_estimated_price(location)

data = {
    'area': 500,
    'price_per_meter': price_per_meter,
    'location': f'{location}، الرياض',
    'property_type': 'فيلا سكنية',
    'building_age': 5,
    'building_cost_sqm': 3000, 
    'rent_per_sqm': 450,
    'cap_rate': 0.08,
    'comparables': [
        {'name': 'فيلا 1 (شارع 20م)', 'location': location, 'price_per_meter': price_per_meter + 500},
        {'name': 'فيلا 2 (نفس المربع)', 'location': location, 'price_per_meter': price_per_meter - 300},
        {'name': 'فيلا 3 (قريبة)', 'location': location, 'price_per_meter': price_per_meter}
    ]
}

ivs_result = advanced_valuation(data)
ivs_result['property_type'] = data['property_type']

# حفظ التقرير
file_path = generate_professional_report(ivs_result)

# طباعة النتائج
print("REPORT_GENERATED:", file_path)
print(f"MARKET_VAL: {ivs_result['market']['value']:,.2f}")
print(f"COST_VAL:   {ivs_result['cost']['value']:,.2f}")
print(f"INCOME_VAL: {ivs_result['income']['value']:,.2f}")
print(f"RECONCILED: {ivs_result['reconciled_value']:,.2f}")
