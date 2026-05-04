# المرجع التقني — وحدة التقييم الضريبي العقاري
**الإصدار:** Phase 2.8 — التوثيق النهائي  
**التاريخ:** 2026-05-02  
**الجمهور المستهدف:** المطوّرون وفريق الصيانة  

---

## 1. خريطة البنية المعمارية (Architecture Map)

```
┌──────────────────────────────────────────────────────────────────┐
│  frontend/index.html                                             │
│  ├── collectTaxAssessmentPayload()   ← يجمع الحقول الضريبية     │
│  ├── applyTaxPolicyDefaults(cls)     ← يملأ الحقول من فئة العقار │
│  ├── TAX_POLICY_DEFAULTS {}          ← مرآة JS لـ _TAX_POLICY_PROFILES │
│  └── generateVisualReport() / tax block renderer                 │
│       └── tax_appeal_package IIFE renderer                       │
└──────────────────────────────────────────────────────────────────┘
                           │ POST /api/valuation
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  core_engine/bridge_api.py                                       │
│  ├── handle_valuation()              ← route handler             │
│  │    ├── _pre_tax_block = _compute_tax_assessment_block(...)    │
│  │    ├── full["tax_assessment"] = _pre_tax_block  (Fix A)       │
│  │    └── resp["tax_assessment"] = tax_block                     │
│  │                                                               │
│  ├── _TAX_POLICY_PROFILES {}         ← 5 فئات عقارية            │
│  ├── _resolve_tax_policy_profile(payload) → dict                 │
│  ├── _build_tax_appeal_package(tax, payload) → dict              │
│  └── _compute_tax_assessment_block(payload, market_value) → dict │
└──────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  core_engine/purpose_detail_sections.py                          │
│  └── add_tax_assessment_section(doc, p)                          │
│       ├── جدول الحسابات الأساسية                                 │
│       ├── المؤشرات الموسعة (Phase 2.2)                           │
│       ├── audit_notes (Phase 2.3)                                │
│       ├── policy profile (Phase 2.4)   _tsub fallback (Fix B)   │
│       └── tax_appeal_package (Phase 2.6)  _tsub fallback (Fix B) │
└──────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  core_engine/mass_appraisal.py                                   │
│  ├── BATCH_SUPPORTED_PURPOSES includes "tax_assessment"          │
│  └── calls _compute_tax_assessment_block(payload, mv) per row    │
│                                                                   │
│  core_engine/mass_appraisal_excel.py                             │
│  └── _sheet_tax_assessment(wb, rows_data)                        │
│       └── 21 columns incl. appeal_strength, operator_recommendation │
└──────────────────────────────────────────────────────────────────┘
```

### ملف الواجهة: `frontend/index.html`

| العنصر | الموقع التقريبي | الدور |
|--------|-----------------|-------|
| `#tax-property-class` (select) | ~line 1039 | اختيار فئة العقار |
| `TAX_POLICY_DEFAULTS` | ~line 3338 | مرآة JS لـ `_TAX_POLICY_PROFILES` |
| `applyTaxPolicyDefaults(cls)` | ~line 3345 | يملأ `tax-rental-pct`، `tax-rate`، `exemption_threshold` |
| `collectTaxAssessmentPayload()` | ~line 3354 | يجمع 7 حقول ضريبية في كائن |
| Tax block renderer | ~line 2845–2898 | يعرض `tax_appeal_package` بالكامل |

**الحقول التي تُملأ تلقائياً من `applyTaxPolicyDefaults()`:**
- `#tax-rental-pct` ← `annual_rental_pct`
- `#tax-rate` ← `tax_rate`
- `#tax-exemption` ← `exemption_threshold`

**الحقول التي لا تُملأ تلقائياً (خاصة بالعقار):**
- `#tax-gov-factor` ← `governorate_factor`
- `#tax-con-factor` ← `construction_factor`
- `#tax-loc-factor` ← `location_factor`
- `#tax-assessment-ratio` ← `assessment_ratio`

---

## 2. عقد طلب الـ API (Request Payload Contract)

### `POST /api/valuation`

```json
{
  "location": "التجمع الخامس",
  "property_type": "شقة سكنية",
  "area": 200,
  "price_per_meter": 25000,
  "valuation_purpose": "tax_assessment",

  "property_class": "residential",

  "governorate_factor": 1.00,
  "construction_factor": 1.00,
  "location_factor": 1.00,
  "assessment_ratio": 1.00,

  "annual_rental_pct": 0.03,
  "tax_rate": 0.10,
  "exemption_threshold": 24000,
  "legal_basis": "قانون 196/2008"
}
```

**ملاحظات العقد:**
- `valuation_purpose` **مطلوب** — يجب أن يكون `"tax_assessment"` لتفعيل الحسابات الضريبية
- `property_class` **اختياري** — الافتراضي `"residential"` إذا غاب أو كان غير معروف
- جميع الحقول الضريبية (`annual_rental_pct`، `tax_rate`، إلخ) **اختيارية** — تُستكمل من ملف السياسة عند غيابها
- عند إرسال قيمة تختلف عن الافتراضي، يُسجَّل التجاوز في `manual_overrides`

---

## 3. عقد الاستجابة (Response Contract)

### `response.tax_assessment`

الاستجابة الكاملة تُعيد `tax_assessment` ككائن متداخل ضمن `resp`.

```json
{
  "status": "success",
  "market_value": 5000000.00,
  "valuation_purpose": "tax_assessment",
  "excel_url": "http://127.0.0.1:5000/api/download/Report_ES-...",
  "purpose_report_url": "http://127.0.0.1:5000/api/download/PurposeReport_...",

  "tax_assessment": {

    "market_value": 5000000.00,
    "annual_rental_pct": 0.03,
    "annual_rental_value": 150000.00,
    "governorate_factor": 1.00,
    "construction_factor": 1.00,
    "location_factor": 1.00,
    "composite_factor": 1.0000,
    "tax_base": 150000.00,
    "exemption_threshold": 24000.00,
    "taxable_amount": 126000.00,
    "tax_rate": 0.10,
    "annual_tax": 12600.00,
    "legal_basis": "قانون 196/2008",
    "note": "ضريبة عقارية وفق قانون 196/2008 — وحدات سكنية — إعفاء 24,000 ج.م — نسبة إيجار 3%.",

    "assessed_value": 5000000.00,
    "assessment_ratio": 1.0,
    "assessed_rental_value": 150000.00,
    "exemption_amount": 24000.00,
    "taxable_value": 126000.00,
    "effective_tax_rate": 0.00252,
    "tax_due": 12600.00,
    "tax_sheet_summary": {
      "market_value": 5000000.00,
      "assessed_value": 5000000.00,
      "annual_rental_value": 150000.00,
      "assessed_rental_value": 150000.00,
      "exemption_amount": 24000.00,
      "taxable_value": 126000.00,
      "tax_rate": 0.10,
      "tax_due": 12600.00
    },
    "appeal_narrative": "...",
    "audit_notes": ["...", "..."],

    "policy_profile": "residential",
    "property_class": "residential",
    "policy_defaults": {
      "annual_rental_pct_default": 0.03,
      "tax_rate_default": 0.10,
      "exemption_threshold_default": 24000.0,
      "legal_basis_default": "قانون 196/2008",
      "policy_notes": "وحدات سكنية — إعفاء 24,000 ج.م — نسبة إيجار 3%."
    },
    "policy_notes": "وحدات سكنية — إعفاء 24,000 ج.م — نسبة إيجار 3%.",
    "manual_overrides": {},

    "tax_appeal_package": {
      "appeal_strength": "low",
      "appeal_reasons": [],
      "evidence_checklist": [
        { "item": "...", "required": true, "purpose": "..." },
        ...
      ],
      "operator_recommendation": "...",
      "appeal_summary": "...",
      "formal_appeal_narrative": "...",
      "disclaimer": "..."
    }
  }
}
```

### حقول غائبة (Not Implemented)

| الحقل | الحالة | الملاحظة |
|-------|--------|----------|
| `tax_scenarios` | غائب | Phase 2.5 — لم يُنفَّذ |
| `tax_sensitivity_summary` | غائب | يُقرأ كـ no-op في `_build_tax_appeal_package` لكن لا يُحسب |

---

## 4. معادلات الحساب (Calculation Formulas)

```
annual_rental_value  = market_value × annual_rental_pct

composite_factor     = governorate_factor × construction_factor × location_factor

assessed_value       = market_value × composite_factor

assessed_rental_value = annual_rental_value × composite_factor
                      ≡ tax_base   (للتوافق مع الإصدارات السابقة)

exemption_amount     = min(exemption_threshold, assessed_rental_value)

taxable_value        = max(assessed_rental_value − exemption_amount, 0)
                     ≡ taxable_amount   (للتوافق مع الإصدارات السابقة)

annual_tax           = taxable_value × tax_rate

tax_due              = annual_tax   (محتفظ به للتوافق — لا تستخدمه لأي منطق إضافي)

effective_tax_rate   = annual_tax / market_value   (صفر إذا كان market_value = 0)
```

### الثوابت الرياضية (Invariants)

| الثابت | التعريف |
|--------|---------|
| `tax_due == annual_tax` | دائماً متساويان — `tax_due` للتوافق العكسي فقط |
| `taxable_value == taxable_amount` | دائماً متساويان — `taxable_amount` للتوافق العكسي فقط |
| `taxable_value >= 0` | لا يكون أبداً سالباً |
| `annual_tax >= 0` | لا يكون أبداً سالباً |
| `composite_factor = G × C × L` | دائماً حاصل ضرب المعاملات الثلاثة |

---

## 5. سلوك التحقق والـ Fallback

### منطق الـ Fallback في `_compute_tax_assessment_block()`

| الحقل | السلوك عند الإدخال غير الصالح |
|-------|-------------------------------|
| `tax_rate <= 0` أو `> 1` | يُستخدم ما أُرسل كما هو (المستخدم مسؤول)؛ يُسجَّل في `manual_overrides` إذا اختلف عن السياسة |
| `annual_rental_pct <= 0` أو غائب | يُستخدم الافتراضي من ملف السياسة (`policy_profile`) |
| `exemption_threshold < 0` | يعمل رياضياً (سيزيد الوعاء الخاضع)؛ لا يُرفض |
| `governorate_factor` / `construction_factor` / `location_factor` غائب | الافتراضي `1.00` |
| `assessment_ratio` غائب | الافتراضي `1.00` |
| `legal_basis` غائب أو فارغ | يُؤخذ من `_TAX_POLICY_PROFILES[property_class]["legal_basis_default"]` |
| `property_class` غائب أو غير معروف | يُعاد إلى `"residential"` |
| أي استثناء داخلي | `_compute_tax_assessment_block` يُعيد `{}` — لا يُوقف التقييم |

### منطق الـ Fallback في `add_tax_assessment_section()`

بسبب **Phase 2.7 Fix B**، تقرأ الدالة الحقول الموسعة من مستويين:
1. **أولاً:** `p.get("field")` — المستوى الأعلى في `full`
2. **ثانياً:** `_tsub.get("field")` — من `p.get("tax_assessment")` (الكائن المتداخل)

هذا يضمن أن تقارير Word ترى `tax_appeal_package` و`audit_notes` و`policy_profile` و`manual_overrides` بصرف النظر عن كيفية بناء `full`.

---

## 6. تكامل التقارير (Report Integration)

### تقرير Word — `purpose_detail_sections.py`

**نقطة الدخول:** `add_tax_assessment_section(doc, p)`  
**يُستدعى من:** `write_purpose_specific_report("tax_assessment", full, pr_path)`  
**المعامل `p`:** هو `full = {**payload, **res, "report_id": ..., "tax_assessment": _pre_tax_block}`

الأقسام المُولَّدة بالترتيب:
1. `_add_avm_section(doc, p)` — قسم AVM إذا كان مفعّلاً
2. جدول الحسابات الأساسية (8 سطور)
3. جدول المؤشرات المشتقة (7 سطور — Phase 2.2)
4. إفصاحات التدقيق + `audit_notes` (Phase 2.3)
5. ملف السياسة الضريبية (Phase 2.4)
6. حزمة الاعتراض الاستشارية (Phase 2.6)

### التقارير الجماعية — `mass_appraisal_excel.py`

**الدالة:** `_sheet_tax_assessment(wb, rows_data)`  
**تُستدعى:** ضمن تصدير `export-xlsx` للتقييم الجماعي  
**المدخل:** قائمة بيانات الصفوف — كل صف يحتوي على `row.get("tax_assessment")`

بيانات عمودي الاعتراض (العمودان 20 و21):
```python
tap = (tax.get("tax_appeal_package") or {})
vals = [
    ...
    tap.get("appeal_strength"),
    tap.get("operator_recommendation"),
]
```

### عقد ما قبل الحساب (Pre-compute — Phase 2.7 Fix A)

في `handle_valuation()` — الترتيب الضروري:

```python
# 1. احسب كتلة الضريبة قبل بناء full
_pre_tax_block = {}
if _vp == "tax_assessment":
    _pre_tax_block = _compute_tax_assessment_block(payload, res["market_value"]) or {}

# 2. ابنِ full مع حقن tax_assessment
full = {**payload, **res, "report_id": rid, ...}
if _pre_tax_block:
    full["tax_assessment"] = _pre_tax_block

# 3. اكتب التقارير (Word يرى الآن tax_appeal_package)
write_to_excel_template(full, path)
write_word_summary(full, ...)
write_purpose_specific_report("tax_assessment", full, pr_path)

# 4. أعد الاستجابة (أعِد استخدام _pre_tax_block لا تحسب مرتين)
if _vp == "tax_assessment":
    tax_block = _pre_tax_block or _compute_tax_assessment_block(...)
    resp["tax_assessment"] = tax_block
```

---

## 7. قواعد التوافق العكسي (Backward Compatibility Rules)

هذه القواعد **ملزمة** — لا يجوز تغييرها في أي مرحلة مستقبلية دون موافقة صريحة:

| القاعدة | التفاصيل |
|---------|---------|
| لا تحذف حقلاً قديماً | `tax_base`، `taxable_amount`، `tax_due` موجودة للتوافق — لا تحذفها |
| `tax_due == annual_tax` دائماً | أي منطق يعتمد على `tax_due` يحصل على نفس نتيجة `annual_tax` |
| `taxable_value == taxable_amount` دائماً | الحقلان متزامنان دائماً |
| `tax_assessment` يعمل في التقييم الجماعي | `mass_appraisal.py` يستدعي `_compute_tax_assessment_block` لكل صف |
| الأغراض الأخرى لا تتأثر | `fair_market_value` وغيره لا تحصل على `tax_assessment` في الاستجابة |
| لا تُدخل حقلاً جديداً داخل dict موجودة | أضف خارجها: `result["new_field"] = value` بعد بناء `result` |
| الـ API fallback لا يكسر الاستجابة | `_compute_tax_assessment_block` يُعيد `{}` عند أي استثناء — الاستجابة تُكمل |

---

## 8. نقاط التوسع المستقبلية (Developer Extension Points)

هذه نقاط آمنة لإضافات مستقبلية دون كسر ما هو قائم:

### 1. جداول تعريفة رسمية من قاعدة بيانات
```python
# بدلاً من _TAX_POLICY_PROFILES الثابتة
def _resolve_tax_policy_profile(payload: dict) -> dict:
    db_profile = fetch_from_db(payload.get("property_class"), payload.get("governorate"))
    return db_profile or _TAX_POLICY_PROFILES.get("residential")
```
أضف fallback على `_TAX_POLICY_PROFILES` لضمان التوافق مع البيئات بلا DB.

### 2. تصدير رسمي بتنسيق هيئة الضرائب (ETA)
أضف route جديدة `/api/tax/export-eta` تأخذ `tax_assessment` block وتنتج PDF رسمي.  
**لا تعدّل** `_compute_tax_assessment_block`.

### 3. بحث السياسة حسب المحافظة
```python
# في _resolve_tax_policy_profile():
governorate = payload.get("governorate") or payload.get("location", "").split()[0]
gov_override = _GOVERNORATE_TAX_OVERRIDES.get(governorate, {})
profile = {**_TAX_POLICY_PROFILES[pc], **gov_override}
```

### 4. معادلات ضريبية تصاعدية (Brackets)
أضف منطق الشرائح بعد `taxable_value`:
```python
# احسب taxable_value أولاً كما هو الآن
# ثم طبق الشرائح
annual_tax = _apply_tax_brackets(taxable_value, policy["tax_brackets"])
```
احتفظ بـ `tax_rate` في النتيجة للتوافق العكسي.

### 5. سيناريوهات الضريبة (Phase 2.5 — لم تُنفَّذ)
```python
def _compute_tax_scenarios(payload: dict, mv: float) -> dict:
    """Returns tax_scenarios and tax_sensitivity_summary."""
    cases = {
        "current_case":         _compute_tax_assessment_block(payload, mv),
        "policy_default_case":  _compute_tax_assessment_block({**payload, ...policy_defaults}, mv),
        "conservative_case":    _compute_tax_assessment_block({...conservative_inputs}, mv),
        "high_assessment_case": _compute_tax_assessment_block({...high_inputs}, mv),
    }
    return {"tax_scenarios": cases, "tax_sensitivity_summary": _summarize(cases)}
```
اُستدعِ بعد `_compute_tax_assessment_block` في `handle_valuation()` وأضف النتيجة إلى `resp`.

### 6. ورقة Excel للعقار الفردي (Phase 2.1B — لم تُنفَّذ)
```python
def write_tax_sheet_to_workbook(wb, tax_block: dict) -> None:
    """Adds a dynamic Tax Assessment sheet to an existing workbook."""
    ws = wb.create_sheet("Tax Assessment")
    # ... اكتب الحقول
```
استدعِها في `write_to_excel_template()` بعد تحميل القالب، مشروطةً بوجود `tax_assessment` في `full`.

### 7. حفظ نتائج الاعتراض (Persistence)
أضف endpoint `/api/tax/appeal/save` يحفظ `tax_appeal_package` في قاعدة البيانات مع `batch_id` ومعرف المقيّم.  
**لا تعدّل** `_build_tax_appeal_package` — ابقها pure function.

### 8. PDF ورقة الضريبة الرسمية
أنشئ قالب `reportlab` أو `weasyprint` منفصل:
```python
def generate_tax_pdf(tax_block: dict, output_path: str) -> str:
    """Generates an official-style tax assessment PDF."""
    ...
```
استدعِها كخطوة مستقلة في `handle_valuation()` بعد `write_purpose_specific_report`.
