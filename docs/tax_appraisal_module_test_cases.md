# حالات الاختبار — وحدة التقييم الضريبي العقاري
**الإصدار:** Phase 2.8 — التوثيق النهائي  
**التاريخ:** 2026-05-02  
**الجمهور المستهدف:** فريق QA والمطوّرون  

---

## 1. اختبارات الـ API

### A — التقييم الضريبي السكني الافتراضي

**الهدف:** التحقق من صحة الحسابات الأساسية وعقد الاستجابة الكامل لعقار سكني بالقيم الافتراضية.

**المدخل:**
```json
{
  "location": "التجمع الخامس",
  "property_type": "شقة سكنية",
  "area": 200,
  "valuation_purpose": "tax_assessment",
  "property_class": "residential",
  "annual_rental_pct": 0.03,
  "tax_rate": 0.10,
  "exemption_threshold": 24000
}
```

**المتوقع:**
```
status = "success"
tax_assessment ≠ null
tax_assessment.annual_tax > 0                     إذا كانت القيمة السوقية > 240,000 ج.م
tax_assessment.tax_due == tax_assessment.annual_tax
tax_assessment.taxable_value == tax_assessment.taxable_amount
tax_assessment.effective_tax_rate > 0
tax_assessment.policy_profile == "residential"
tax_assessment.tax_appeal_package ≠ null
tax_assessment.tax_appeal_package.evidence_checklist.length == 6
tax_assessment.manual_overrides == {}             لا تجاوزات
```

**الأوامر:**
```powershell
$body = '{"location":"التجمع الخامس","property_type":"شقة سكنية","area":200,"valuation_purpose":"tax_assessment","property_class":"residential","annual_rental_pct":0.03,"tax_rate":0.10,"exemption_threshold":24000}'
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/valuation" -Method Post -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 8
```

```bash
curl -s -X POST http://127.0.0.1:5000/api/valuation \
  -H "Content-Type: application/json" \
  -d '{"location":"التجمع الخامس","property_type":"شقة سكنية","area":200,"valuation_purpose":"tax_assessment","property_class":"residential"}' \
  | python -m json.tool
```

---

### B — تجاوز يدوي (Manual Override)

**الهدف:** التحقق من أن القيم المخصصة تُطبَّق فعلياً وتُسجَّل في `manual_overrides`.

**المدخل:**
```json
{
  "location": "المعادي",
  "property_type": "شقة سكنية",
  "area": 150,
  "valuation_purpose": "tax_assessment",
  "property_class": "residential",
  "annual_rental_pct": 0.05,
  "tax_rate": 0.07,
  "exemption_threshold": 30000,
  "legal_basis": "قرار وزاري رقم 42/2024"
}
```

**المتوقع:**
```
tax_assessment.annual_rental_pct == 0.05          القيمة المُدخَلة لا الافتراضية 0.03
tax_assessment.tax_rate == 0.07                    القيمة المُدخَلة لا الافتراضية 0.10
tax_assessment.exemption_threshold == 30000        القيمة المُدخَلة لا الافتراضية 24000
tax_assessment.legal_basis == "قرار وزاري رقم 42/2024"
tax_assessment.manual_overrides.annual_rental_pct.policy == 0.03
tax_assessment.manual_overrides.annual_rental_pct.used == 0.05
tax_assessment.manual_overrides.tax_rate.policy == 0.10
tax_assessment.manual_overrides.tax_rate.used == 0.07
tax_assessment.tax_appeal_package.appeal_strength ∈ ["medium", "high"]
    بسبب MANUAL_ASSUMPTIONS_USED
```

---

### C — السياسة التجارية (Commercial Policy)

**الهدف:** التحقق من تطبيق ملف السياسة التجاري مع الاختلافات عن السكني.

**المدخل:**
```json
{
  "location": "وسط البلد",
  "property_type": "محل تجاري",
  "area": 80,
  "valuation_purpose": "tax_assessment",
  "property_class": "commercial"
}
```

**المتوقع:**
```
tax_assessment.annual_rental_pct == 0.08          السياسة التجارية
tax_assessment.tax_rate == 0.10
tax_assessment.exemption_threshold == 0.0          لا إعفاء للتجاري
tax_assessment.taxable_value == tax_assessment.assessed_rental_value
tax_assessment.policy_profile == "commercial"
tax_assessment.policy_notes يحتوي على "تجاري"
```

---

### D — السياسة الزراعية (Agricultural Policy)

**الهدف:** التحقق من السعر المنخفض (5%) والإعفاء المرتفع (48,000) للزراعي.

**المدخل:**
```json
{
  "location": "الفيوم",
  "property_type": "أرض زراعية",
  "area": 5000,
  "valuation_purpose": "tax_assessment",
  "property_class": "agricultural"
}
```

**المتوقع:**
```
tax_assessment.annual_rental_pct == 0.02
tax_assessment.tax_rate == 0.05
tax_assessment.exemption_threshold == 48000.0
tax_assessment.policy_profile == "agricultural"
```

---

### E — إعفاء مرتفع / ضريبة صفر (High Exemption / Zero Tax)

**الهدف:** التحقق من أن الضريبة تساوي الصفر عندما يغطي الإعفاء الوعاء الضريبي بالكامل.

**المدخل:**
```json
{
  "location": "الفيوم",
  "property_type": "أرض زراعية",
  "area": 100,
  "valuation_purpose": "tax_assessment",
  "property_class": "agricultural",
  "exemption_threshold": 999999
}
```

**المتوقع:**
```
tax_assessment.taxable_value == 0.0
tax_assessment.taxable_amount == 0.0
tax_assessment.annual_tax == 0.0
tax_assessment.tax_due == 0.0
tax_assessment.effective_tax_rate == 0.0
tax_assessment.appeal_narrative يذكر "الإعفاء" أو "صفر"
tax_assessment.tax_appeal_package.appeal_reasons يحتوي على إشارة EXEMPTION_ELIMINATES_TAX
```

---

### F — سيناريوهات الضريبة (Tax Scenarios) — غير مُنفَّذة

**الحالة:** `tax_scenarios` و`tax_sensitivity_summary` **غير موجودَين** في الاستجابة الحالية.

**المتوقع الحالي (Phase 2.8):**
```
tax_assessment.tax_scenarios == null أو غائب
tax_assessment.tax_sensitivity_summary == null أو غائب
```

**ملاحظة:** هذه الميزة مخططة لـ Phase 3. لا تختبر وجودها في هذا الإصدار.

---

### G — حزمة الاعتراض (Tax Appeal Package)

**الهدف:** التحقق من اكتمال حزمة الاعتراض وصحة بنيتها.

**المدخل:** أي طلب `tax_assessment` صالح.

**المتوقع:**
```
tax_assessment.tax_appeal_package ≠ null
tax_assessment.tax_appeal_package.appeal_strength ∈ ["low", "medium", "high"]
tax_assessment.tax_appeal_package.appeal_reasons instanceof Array
tax_assessment.tax_appeal_package.evidence_checklist instanceof Array
tax_assessment.tax_appeal_package.evidence_checklist.length == 6
tax_assessment.tax_appeal_package.evidence_checklist[*].item ≠ null
tax_assessment.tax_appeal_package.evidence_checklist[*].required instanceof Boolean
tax_assessment.tax_appeal_package.operator_recommendation ≠ ""
tax_assessment.tax_appeal_package.appeal_summary ≠ ""
tax_assessment.tax_appeal_package.formal_appeal_narrative ≠ ""
tax_assessment.tax_appeal_package.disclaimer ≠ ""
```

---

### H — Fallback للقيم غير الصالحة

**الهدف:** التحقق من أن الـ API لا يتوقف (لا 500) عند إدخال قيم غير منطقية.

**المدخل — اختبار H1: `tax_rate` خارج النطاق:**
```json
{
  "location": "القاهرة",
  "property_type": "شقة",
  "area": 100,
  "valuation_purpose": "tax_assessment",
  "tax_rate": 2.0
}
```
**المتوقع:** `status == "success"` (لا crash) — `tax_rate = 2.0` تُطبَّق كما هي — تُسجَّل في `manual_overrides`

**المدخل — اختبار H2: `annual_rental_pct` سالبة:**
```json
{
  "location": "القاهرة",
  "property_type": "شقة",
  "area": 100,
  "valuation_purpose": "tax_assessment",
  "annual_rental_pct": -1
}
```
**المتوقع:** `status == "success"` (لا crash) — النظام يستخدم الافتراضي 0.03 من ملف السياسة

**المدخل — اختبار H3: `property_class` غير معروفة:**
```json
{
  "location": "القاهرة",
  "property_type": "شقة",
  "area": 100,
  "valuation_purpose": "tax_assessment",
  "property_class": "unknown_type"
}
```
**المتوقع:** `policy_profile == "residential"` (fallback) — `GENERIC_POLICY_PROFILE` في `appeal_reasons`

---

### I — الثوابت الرياضية (Numeric Invariants Verification)

```powershell
$r = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/valuation" -Method Post -ContentType "application/json" -Body '{"location":"التجمع الخامس","property_type":"شقة","area":200,"valuation_purpose":"tax_assessment","property_class":"residential"}'
$ta = $r.tax_assessment

# Invariant 1
if ([math]::Abs($ta.tax_due - $ta.annual_tax) -gt 0.01) { Write-Host "FAIL: tax_due != annual_tax" } else { Write-Host "PASS: tax_due == annual_tax" }

# Invariant 2
if ([math]::Abs($ta.taxable_value - $ta.taxable_amount) -gt 0.01) { Write-Host "FAIL: taxable_value != taxable_amount" } else { Write-Host "PASS: taxable_value == taxable_amount" }

# Invariant 3
if ($ta.taxable_value -lt 0) { Write-Host "FAIL: taxable_value negative" } else { Write-Host "PASS: taxable_value >= 0" }

# Invariant 4
if ($ta.annual_tax -lt 0) { Write-Host "FAIL: annual_tax negative" } else { Write-Host "PASS: annual_tax >= 0" }

# Invariant 5
$expected_cf = [math]::Round($ta.governorate_factor * $ta.construction_factor * $ta.location_factor, 4)
if ([math]::Abs($ta.composite_factor - $expected_cf) -gt 0.0001) { Write-Host "FAIL: composite_factor mismatch" } else { Write-Host "PASS: composite_factor correct" }
```

---

## 2. اختبارات الواجهة الأمامية (Frontend Tests)

### F1 — ظهور لوحة الضريبة

| الإجراء | المتوقع |
|---------|--------|
| اختر غرض التقييم "الضريبة العقارية" | تظهر لوحة حقول الضريبة |
| اختر غرضاً آخر (مثل fair_market_value) | تختفي لوحة الضريبة |

### F2 — الملء التلقائي من فئة العقار

| اختر `property_class` | `annual_rental_pct` | `tax_rate` | `exemption_threshold` |
|-----------------------|---------------------|------------|----------------------|
| residential | 0.03 | 0.10 | 24000 |
| commercial | 0.08 | 0.10 | 0 |
| industrial | 0.06 | 0.10 | 0 |
| agricultural | 0.02 | 0.05 | 48000 |
| administrative | 0.08 | 0.10 | 0 |

**التحقق:** افتح DevTools ← Elements ← تحقق من قيمة الحقول مباشرة بعد التغيير.

### F3 — صحة الـ Payload المُرسَل

بعد الضغط على "تقييم":  
افتح DevTools ← Network ← `/api/valuation` ← Request Payload.

**يجب أن يحتوي على:**
```json
{
  "valuation_purpose": "tax_assessment",
  "property_class": "...",
  "annual_rental_pct": ...,
  "tax_rate": ...,
  "exemption_threshold": ...,
  "governorate_factor": ...,
  "construction_factor": ...,
  "location_factor": ...
}
```

**يجب ألا يحتوي على:** أي نداء لـ `/api/mass-appraisal/*`

### F4 — عرض النتائج (Result Modal)

| القسم | المتوقع |
|-------|--------|
| جدول الضريبة الأساسي | يعرض `annual_tax`، `taxable_amount`، `effective_tax_rate` |
| ملف السياسة | يعرض فئة العقار ووصف السياسة |
| حزمة الاعتراض | يعرض شارة قوة الاعتراض بالألوان (أخضر/برتقالي/أحمر) |
| قائمة المستندات | يعرض 6 عناصر في جدول |
| السرد الرسمي | نص مقروء |
| إخلاء المسؤولية | مربع بحدود حمراء |

### F5 — عدم وجود أخطاء JavaScript

افتح DevTools ← Console.  
تحقق من: **لا توجد أخطاء** بعد تحميل الصفحة وتنفيذ تقييم ضريبي.

### F6 — حقول معاملات التقدير لا تتغير تلقائياً

تأكد أن تغيير `property_class` **لا يُغيّر** قيم:
- `#tax-gov-factor`
- `#tax-con-factor`
- `#tax-loc-factor`
- `#tax-assessment-ratio`

---

## 3. اختبارات تقرير Word

### W1 — الحقول الديناميكية

| الحقل | الاختبار |
|-------|---------|
| `annual_rental_pct` | أرسل 0.05 — تحقق أن التقرير يظهر 5% لا 3% |
| `tax_rate` | أرسل 0.07 — تحقق أن التقرير يظهر 7% |
| `exemption_threshold` | أرسل 30000 — تحقق أن التقرير يظهر 30,000 ج.م |
| `legal_basis` | أرسل نصاً مخصصاً — تحقق أنه يظهر في السند القانوني |

### W2 — أقسام Phase 2.4 و2.6

| القسم | يجب أن يوجد |
|-------|------------|
| "ملف السياسة الضريبية" | ✔ |
| فئة العقار (الفئة الصحيحة) | ✔ |
| وصف السياسة (policy_notes) | ✔ |
| تجاوزات يدوية (إن وجدت) | ✔ |
| "حزمة الاعتراض الضريبي (استشارية)" | ✔ |
| قوة الاعتراض (بالعربية) | ✔ |
| قائمة المستندات المطلوبة | ✔ |
| السرد الرسمي | ✔ |
| إخلاء المسؤولية | ✔ |

### W3 — التحقق من Fix A (Phase 2.7)

أرسل طلب `tax_assessment` مع تجاوز يدوي.  
افتح تقرير Word.  
**تحقق أن:** قسم "حزمة الاعتراض الضريبي" **ليس فارغاً** (كان فارغاً قبل Phase 2.7).  
**الإشارة:** وجود `appeal_strength` وأسباب الاعتراض في التقرير.

### W4 — ملاحظات التدقيق (audit_notes)

| الحالة | المتوقع في التقرير |
|--------|------------------|
| لم يُرسل `annual_rental_pct` | "تم استخدام نسبة إيجارية افتراضية قدرها 3%." |
| لم يُرسل `tax_rate` | "تم استخدام سعر ضريبة افتراضي قدره 10%." |
| أُرسلت القيم المخصصة | ملاحظة التقدير المخصص |

---

## 4. اختبارات Excel

### X1 — التقييم الجماعي — ورقة Tax Assessment

```powershell
# 1. نفّذ batch run مع صفوف tax_assessment
$batchBody = '{"rows":[
  {"row_id":"T-001","location":"التجمع الخامس","property_type":"شقة","area":200,"valuation_purpose":"tax_assessment","property_class":"residential"},
  {"row_id":"T-002","location":"وسط البلد","property_type":"محل","area":60,"valuation_purpose":"tax_assessment","property_class":"commercial"},
  {"row_id":"F-001","location":"مدينة نصر","property_type":"شقة","area":150,"valuation_purpose":"fair_market_value"}
]}'
$runResult = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/mass-appraisal/run" -Method Post -ContentType "application/json" -Body $batchBody

# 2. صدّر XLSX
$exportBody = $runResult | ConvertTo-Json -Depth 10
Invoke-WebRequest -Uri "http://127.0.0.1:5000/api/mass-appraisal/export-xlsx" -Method Post -ContentType "application/json" -Body $exportBody -OutFile "tax_test.xlsx"
```

**تحقق في Excel:**
- [ ] ورقة "Tax Assessment" موجودة
- [ ] 21 عموداً بالأسماء الصحيحة
- [ ] صفان فقط (T-001 و T-002) — F-001 ليس ضريبياً لا يظهر هنا
- [ ] عمود `policy_profile` يحتوي `"residential"` و`"commercial"` صحيح لكل صف
- [ ] عمود `appeal_strength` غير فارغ
- [ ] النصوص العربية تُقرأ بشكل صحيح في Excel

### X2 — عدم ظهور ورقة Tax Assessment لغرض غير ضريبي

```powershell
$fmvBatch = '{"rows":[{"row_id":"F-001","location":"مدينة نصر","property_type":"شقة","area":150,"valuation_purpose":"fair_market_value"}]}'
$result = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/mass-appraisal/run" -Method Post -ContentType "application/json" -Body $fmvBatch
# صدّر XLSX — لا يجب أن تحتوي على بيانات في ورقة Tax Assessment
```

### X3 — تقرير Excel للعقار الفردي (Phase 2.1B — قيد معروف)

```
الحالة: تقرير xlsm للعقار الفردي لا يحتوي على ورقة ضريبية ديناميكية.
المتوقع الحالي: التقرير يُحمَّل بدون خطأ لكن بدون ورقة Tax Assessment مخصصة.
هذا سلوك متوقع — Phase 2.1B لم تُنفَّذ.
```

---

## 5. اختبار التراجع للتقييم الجماعي (Mass Appraisal Regression)

### M1 — صف ضريبي في الـ Batch

```powershell
$body = '{"rows":[{"row_id":"T-001","location":"التجمع الخامس","property_type":"شقة","area":200,"valuation_purpose":"tax_assessment","property_class":"residential"}]}'
$r = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/mass-appraisal/run" -Method Post -ContentType "application/json" -Body $body
$row = $r.rows[0]
```

**المتوقع:**
```
$row.status == "success"
$row.tax_assessment ≠ null
$row.tax_assessment.annual_tax > 0
$row.tax_assessment.tax_appeal_package ≠ null
```

### M2 — صفوف HBU/REIT/EIA في نفس الـ Batch تبقى Skipped

```powershell
$mixed = '{"rows":[
  {"row_id":"T-001","valuation_purpose":"tax_assessment","location":"القاهرة","property_type":"شقة","area":100},
  {"row_id":"H-001","valuation_purpose":"hbu_analysis","location":"القاهرة","property_type":"أرض","area":500},
  {"row_id":"R-001","valuation_purpose":"reit_valuation","location":"القاهرة","property_type":"برج","area":5000}
]}'
$r = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/mass-appraisal/run" -Method Post -ContentType "application/json" -Body $mixed
```

**المتوقع:**
```
$r.rows | Where status == "success" | row_id == "T-001"
$r.rows | Where status == "skipped" | row_id ∈ ["H-001", "R-001"]
$r.summary.skipped_rows == 2
```

### M3 — اختبار معاينة (Preview) لا تحسب ضريبة

```powershell
$prevBody = '{"rows":[{"row_id":"T-001","location":"التجمع الخامس","property_type":"شقة","area":200,"valuation_purpose":"tax_assessment"}]}'
$prev = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/mass-appraisal/preview" -Method Post -ContentType "application/json" -Body $prevBody
```

**المتوقع:**
```
$prev.status == "success"
$prev.rows[0].valid == true
لا يوجد tax_assessment في نتيجة preview (preview لا تُنفّذ الحساب)
```

---

## 6. اختبارات التراجع للأغراض غير الضريبية (Non-Tax Regression)

### N1 — القيمة السوقية العادلة (Fair Market Value)

```powershell
$fmv = '{"location":"التجمع الخامس","property_type":"شقة","area":200,"valuation_purpose":"fair_market_value"}'
$r = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/valuation" -Method Post -ContentType "application/json" -Body $fmv
```
**المتوقع:** `$r.status == "success"` — `$r.tax_assessment` غائب أو null

### N2 — نموذج AVM

```powershell
$avm = '{"location":"التجمع الخامس","property_type":"شقة","area":200,"valuation_purpose":"fair_market_value","price_per_meter":25000}'
$r = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/valuation" -Method Post -ContentType "application/json" -Body $avm
```
**المتوقع:** `$r.avm` موجود — `$r.avm.applied` boolean

### N3 — الصحة العامة (Health Check)

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/advisor/health" -Method Get
```
**المتوقع:** `{"status": "ok"}`

### N4 — الاختبارات الكاملة للأغراض الأخرى

| الغرض | نقطة النهاية | المتوقع |
|-------|-------------|--------|
| `fair_market_value` | `/api/valuation` | `status: success`، لا `tax_assessment` |
| `investment_value` | `/api/valuation` | `status: success` |
| `usufruct` | `/api/valuation` | `usufruct.pv_factor` موجود |
| `uncertainty_valuation` | `/api/valuation` | `uncertainty_range.spread_pct` موجود |
| `hbu_analysis` | `/api/valuation` | HBU block موجود (لا يُهمَل في العقار الفردي) |
| `reit_valuation` | `/api/valuation` | REIT block موجود |
| `eia_assessment` | `/api/valuation` | EIA block موجود |
| أصول متخصصة | `/api/valuation` | `specialized_asset` block موجود |

---

## 7. أوامر التحقق والصيانة

### 7A — التحقق من صحة بناء الكود

```powershell
# Syntax check
python -m py_compile core_engine/bridge_api.py
python -m py_compile core_engine/purpose_detail_sections.py
python -m py_compile core_engine/mass_appraisal.py
python -m py_compile core_engine/mass_appraisal_excel.py

# AST check (أدق وأكثر شمولاً)
python -c "import ast, pathlib; ast.parse(pathlib.Path('core_engine/bridge_api.py').read_text(encoding='utf-8')); print('AST OK bridge_api')"
python -c "import ast, pathlib; ast.parse(pathlib.Path('core_engine/purpose_detail_sections.py').read_text(encoding='utf-8')); print('AST OK purpose_detail_sections')"
python -c "import ast, pathlib; ast.parse(pathlib.Path('core_engine/mass_appraisal_excel.py').read_text(encoding='utf-8')); print('AST OK mass_appraisal_excel')"
```

### 7B — بناء Docker

```powershell
docker compose -f deploy/docker-compose.yml up -d --build flask
docker compose -f deploy/docker-compose.yml logs flask --tail=50
```

### 7C — أوامر curl للاختبار السريع

```bash
# Health
curl -s http://127.0.0.1:5000/api/advisor/health

# Residential tax assessment
curl -s -X POST http://127.0.0.1:5000/api/valuation \
  -H "Content-Type: application/json" \
  -d '{"location":"التجمع الخامس","property_type":"شقة سكنية","area":200,"valuation_purpose":"tax_assessment","property_class":"residential"}' \
  | python -m json.tool

# Agricultural
curl -s -X POST http://127.0.0.1:5000/api/valuation \
  -H "Content-Type: application/json" \
  -d '{"location":"الفيوم","property_type":"أرض زراعية","area":5000,"valuation_purpose":"tax_assessment","property_class":"agricultural"}' \
  | python -m json.tool

# Commercial + extract appeal_strength only
curl -s -X POST http://127.0.0.1:5000/api/valuation \
  -H "Content-Type: application/json" \
  -d '{"location":"وسط البلد","property_type":"محل تجاري","area":80,"valuation_purpose":"tax_assessment","property_class":"commercial"}' \
  | python -c "import sys,json; r=json.load(sys.stdin); print('appeal_strength:', r.get('tax_assessment',{}).get('tax_appeal_package',{}).get('appeal_strength','N/A'))"

# Mass appraisal preview
curl -s -X POST http://127.0.0.1:5000/api/mass-appraisal/preview \
  -H "Content-Type: application/json" \
  -d '{"rows":[{"row_id":"T-001","location":"القاهرة","property_type":"شقة","area":150,"valuation_purpose":"tax_assessment"}]}' \
  | python -m json.tool
```

---

## 8. مصفوفة تغطية الاختبارات

| المنطقة | المُختبَر | الأولوية |
|---------|----------|---------|
| `_compute_tax_assessment_block` | الثوابت الرياضية، 5 ملفات سياسة، المخرجات الكاملة | عالية |
| `_resolve_tax_policy_profile` | 5 فئات، fallback سكني للغير معروف | عالية |
| `_build_tax_appeal_package` | 7 حقول، evidence_checklist بـ 6 عناصر، إشارات الاعتراض | عالية |
| تقرير Word | Phase 2.4 و2.6 sections، Fix A (اعتراض غير فارغ) | عالية |
| ورقة Excel الجماعية | 21 عموداً، عزل صفوف ضريبية | متوسطة |
| الواجهة — ملء تلقائي | 5 فئات × 3 حقول | عالية |
| الواجهة — عرض الاعتراض | شارة + جدول + سرد + إخلاء | متوسطة |
| تراجع non-tax | FMV، AVM، HBU، REIT، EIA، usufruct | عالية |
| تراجع batch | تقييم جماعي + HBU/REIT يبقيان skipped | عالية |
| غير مُنفَّذ (Phase 2.5) | `tax_scenarios` غائب — لا تختبر وجوده | N/A |
| غير مُنفَّذ (Phase 2.1B) | ورقة Excel فردية غير ديناميكية | N/A |
