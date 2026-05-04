# المرجع التقني — التقييم الجماعي المتقدم (Phase 3)
**الإصدار:** Phase 3.10 — Release Stabilization  
**التاريخ:** 2026-05-02  
**الجمهور المستهدف:** المطوّر / المسؤول عن الصيانة  

---

## 1. خريطة المعمارية (Architecture Map)

### 1.1 الملفات والمسؤوليات

| الملف | الوظيفة | الحالة |
|-------|---------|--------|
| `core_engine/mass_appraisal.py` | محرك الدُّفعات: `validate_rows()`, `run_batch()`, تسجيل الجودة، الشذوذات، ملخص المحفظة | ✅ مُنفَّذ (Phase 1 + 3.1) |
| `core_engine/mass_appraisal_excel.py` | بناء XLSX متعدد الأوراق: 17+ ورقة بما يشمل Ratio Study، Calibration، Governance، Model Cycle | ✅ مُنفَّذ |
| `core_engine/sales_verification.py` | `verify_sales_records()`: تصنيف صفقات البيع (usable/excluded/needs_review) | ✅ مُنفَّذ (Phase 3.2) |
| `core_engine/sales_time_adjustment.py` | تعديل أسعار البيع زمنياً وفق معدل النمو الشهري | ✅ مُنفَّذ (Phase 3.4) |
| `core_engine/sales_adjustments.py` | `apply_sales_adjustments()`: 6 عوامل تعديل مضاعفة → `final_adjusted_sale_price` | ✅ مُنفَّذ (Phase 3.5) |
| `core_engine/ratio_studies.py` | `run_ratio_study()`: حساب Median Ratio، COD، PRD، تجميعات المنطقة/الفئة | ✅ مُنفَّذ (Phase 3.3) |
| `core_engine/model_calibration.py` | `preview_calibration()`: معاينة suggested_factor وتوصية المعايرة | ✅ مُنفَّذ (Phase 3.6) |
| `core_engine/calibration_sandbox.py` | `apply_calibration_sandbox()`: تطبيق عوامل المعايرة في بيئة نسخة فقط | ✅ مُنفَّذ (Phase 3.7) |
| `core_engine/bridge_api.py` | نقاط نهاية Flask لجميع مراحل Phase 3 (9 نقاط نهاية) | ✅ مُنفَّذ |
| `frontend/index.html` | واجهة ويب كاملة بـ JS خالص: تشغيل الدُّفعات، المراجعة، المبيعات، Ratio Study، Calibration، Governance، Model Cycle | ✅ مُنفَّذ |

### 1.2 مخطط تدفق البيانات

```
[المستخدم: textarea JSON]
        │
        ▼
[frontend/index.html]
  _massCall() → POST /api/mass-appraisal/run
        │
        ▼
[bridge_api.py: handle_mass_appraisal_run()]
        │
        ▼
[mass_appraisal.py: run_batch()]
  ├── advanced_valuation() لكل صف
  ├── _score_row_quality()
  ├── _compute_portfolio_stats()
  └── _tag_outliers()
        │
        ▼
[النتيجة → frontend]
  ├── renderMassResult()
  ├── ensureMassGovernanceMetadata()
  └── ensureMassModelCycleMetadata()

[المبيعات — خط منفصل]
sales/verify → sales/time-adjust → sales/adjust
        │
        ▼
ratio-study/run
        │
        ▼
calibration/preview → calibration/sandbox
```

---

## 2. مرجع نقاط النهاية (Endpoint Reference)

### POST `/api/mass-appraisal/preview`
**الغرض:** التحقق من صحة صفوف الإدخال دون حساب القيم.  
**الاعتماديات:** `mass_appraisal.validate_rows()`

**طلب:**
```json
{"rows": [...], "options": {}}
```

**استجابة ناجحة:**
```json
{
  "status": "success",
  "summary": {"total_rows": 3, "valid_rows": 2, "invalid_rows": 1, "warning_rows": 0},
  "rows": [{"row_id": "R-001", "valid": true, "errors": [], "warnings": []}]
}
```

**أخطاء:** `400 MISSING_ROWS`، `400 INVALID_ROWS_FORMAT`، `400 TOO_MANY_ROWS`

---

### POST `/api/mass-appraisal/run`
**الغرض:** تشغيل دفعة التقييم الجماعي كاملةً.  
**الاعتماديات:** `mass_appraisal.run_batch()` → `advanced_valuation()` لكل صف

**طلب:**
```json
{"rows": [...], "options": {}}
```

**استجابة ناجحة:**
```json
{
  "status": "success",
  "summary": {
    "total_rows": 3, "successful_rows": 2, "failed_rows": 0, "skipped_rows": 1,
    "total_market_value": 7400000, "average_market_value": 3700000,
    "median_market_value": 3700000,
    "zone_summary": {"Z-NC-01": {...}},
    "property_class_summary": {"residential": {...}}
  },
  "rows": [{"row_id": "R-001", "status": "success", "market_value": 3700000, ...}]
}
```

**أخطاء:** `400 MISSING_ROWS`، `500` عند خطأ داخلي

---

### POST `/api/mass-appraisal/export-xlsx`
**الغرض:** توليد ملف XLSX احترافي وإرجاعه كـ binary stream.  
**الاعتماديات:** `mass_appraisal_excel.build_mass_appraisal_workbook()`

**طلب:**
```json
{
  "result": {...},
  "reviewed_summary": {...},
  "audit": {...},
  "ratio_study": {...},
  "governance": {...},
  "model_cycle": {...}
}
```

**استجابة:** `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`  
**أخطاء:** `400 MISSING_RUN_RESULT`

---

### POST `/api/mass-appraisal/sales/verify`
**الغرض:** التحقق من صلاحية سجلات البيع وتصنيفها.  
**الاعتماديات:** `sales_verification.verify_sales_records()`

**طلب:**
```json
{
  "records": [...],
  "options": {"include_needs_review_in_usable": false}
}
```

**استجابة ناجحة:**
```json
{
  "status": "success",
  "verification_summary": {"total_records": 10, "usable_count": 7, "excluded_count": 2, "needs_review_count": 1},
  "records": [{"sale_id": "S-001", "verification_status": "usable", ...}]
}
```

**أخطاء:** `400 MISSING_RECORDS`، `400 TOO_MANY_RECORDS` (> 1000)

---

### POST `/api/mass-appraisal/sales/time-adjust`
**الغرض:** ضبط أسعار البيع زمنياً حسب معدل النمو الشهري.  
**الاعتماديات:** `sales_time_adjustment` (وحدة مستقلة)

**طلب:**
```json
{
  "records": [...],
  "valuation_date": "2026-05-02",
  "monthly_growth_rate": 0.005
}
```

**استجابة ناجحة:**
```json
{
  "status": "success",
  "summary": {"total_records": 5, "adjusted_records": 5, "average_factor": 1.030},
  "records": [{"sale_id": "S-001", "time_adjustment_factor": 1.030, "adjusted_sale_price": 3605000, ...}]
}
```

---

### POST `/api/mass-appraisal/sales/adjust`
**الغرض:** تطبيق عوامل التعديل البيعي الستة → `final_adjusted_sale_price`.  
**الاعتماديات:** `sales_adjustments.apply_sales_adjustments()`

**طلب:**
```json
{
  "sale_records": [...],
  "adjustment_profile": {
    "location_factor": 1.02, "size_factor": 0.98,
    "condition_factor": 1.0, "quality_factor": 1.0,
    "financing_factor": 1.0, "property_rights_factor": 1.0
  },
  "options": {"round_to": 1000}
}
```

**استجابة ناجحة:**
```json
{
  "status": "success",
  "summary": {"total_records": 5, "adjusted_records": 4, "average_final_adjustment_factor": 0.9996},
  "records": [{"sale_id": "S-001", "final_adjustment_factor": 0.9996, "final_adjusted_sale_price": 3604000, ...}]
}
```

---

### POST `/api/mass-appraisal/ratio-study/run`
**الغرض:** حساب مؤشرات Ratio Study وفق معايير IAAO.  
**الاعتماديات:** `ratio_studies.run_ratio_study()`

**طلب:**
```json
{
  "subject_rows": [...],
  "sale_records": [...],
  "options": {"min_sample_size": 3}
}
```

**استجابة ناجحة:**
```json
{
  "status": "success",
  "summary": {"matched_pair_count": 8, "portfolio_median_ratio": 1.05, "portfolio_cod": 9.2, "portfolio_prd": 1.01},
  "portfolio_metrics": {"median_ratio": 1.05, "cod": 9.2, "prd": 1.01, ...},
  "zone_metrics": {"Z-NC-01": {...}},
  "property_class_metrics": {"residential": {...}},
  "matched_pairs": [...]
}
```

---

### POST `/api/mass-appraisal/calibration/preview`
**الغرض:** توليد معاينة المعايرة — مقترحات `suggested_factor` بدون تطبيق.  
**الاعتماديات:** `model_calibration.preview_calibration()`

**طلب:**
```json
{
  "subject_rows": [...],
  "sale_records": [...],
  "ratio_study": null,
  "options": {"target_median_ratio": 1.0, "min_sample_size": 3}
}
```

**استجابة ناجحة:**
```json
{
  "status": "success",
  "calibration_note": "هذه النتائج معايرة مبدئية للمراجعة فقط...",
  "portfolio_calibration": {
    "sample_size": 8, "median_ratio": 1.05, "suggested_factor": 0.952,
    "recommendation": "minor_adjustment", "warnings": []
  },
  "zone_calibration": {"Z-NC-01": {...}},
  "property_class_calibration": {"residential": {...}},
  "zone_property_class_calibration": {"z-nc-01|residential": {...}}
}
```

---

### POST `/api/mass-appraisal/calibration/sandbox`
**الغرض:** تطبيق عوامل المعايرة على نسخة من النتائج — **`market_value` الأصلي لا يُعدَّل أبداً**.  
**الاعتماديات:** `calibration_sandbox.apply_calibration_sandbox()`

**طلب:**
```json
{
  "subject_rows": [...],
  "calibration_preview": {...},
  "options": {
    "factor_priority": ["zone_property_class", "zone", "property_class", "portfolio"],
    "min_factor": 0.75,
    "max_factor": 1.35,
    "round_to": 1000,
    "apply_to_status": ["success"]
  }
}
```

**استجابة ناجحة:**
```json
{
  "status": "success",
  "summary": {
    "calibrated_rows": 6, "unchanged_rows": 2,
    "original_total_market_value": 22000000,
    "sandbox_total_market_value": 20944000,
    "total_value_delta": -1056000
  },
  "rows": [{"row_id": "R-001", "original_market_value": 3700000, "sandbox_calibrated_value": 3422000, ...}]
}
```

**أخطاء:** `400 MISSING_SUBJECT_ROWS`، `400 MISSING_CALIBRATION_PREVIEW`، `400 INVALID_CALIBRATION_PREVIEW`

---

## 3. عقود البيانات (Data Contracts)

### A. صف العقار (Subject Row)

```python
{
  "row_id":           str,   # required — معرّف فريد
  "location":         str,   # required — موقع العقار
  "property_type":    str,   # required — نوع العقار
  "area":             float, # required — المساحة بالم²
  "valuation_purpose":str,   # required — الغرض: fair_market_value | tax_assessment | usufruct | uncertainty_valuation
  "zone_id":          str,   # optional — رمز المنطقة (Phase 3.1)
  "neighborhood":     str,   # optional — الحي
  "submarket":        str,   # optional — السوق الفرعي
  "property_class":   str,   # optional — فئة العقار
}
```

### B. سجل البيع (Sale Record)

```python
{
  "sale_id":    str,   # required — معرّف فريد
  "sale_price": float, # required — سعر البيع
  "sale_date":  str,   # required — تاريخ البيع (YYYY-MM-DD)
  "area":       float, # required — المساحة
  "location":   str,   # optional
  "property_type": str, # optional
  "zone_id":    str,   # optional
  "property_class": str, # optional
  "verification_status": str, # مُضاف بعد verify
  "usability_status":    str, # مُضاف بعد verify
}
```

### C. مخرج تعديل الوقت

```python
{
  "sale_id":                str,
  "time_adjustment_factor": float,  # (1 + r)^m
  "months_to_valuation_date": float,
  "adjusted_sale_price":    float,  # sale_price × factor
  "adjustment_applied":     bool,
  "adjustment_warnings":    list[str],
}
```

### D. مخرج عوامل التعديل البيعي

```python
{
  "sale_id":                  str,
  "final_adjustment_factor":  float,  # حاصل ضرب العوامل الستة
  "final_adjusted_sale_price":float,  # base × final_adjustment_factor
  "adjustment_applied":       bool,
  "adjustment_method":        str,    # وصف العوامل غير المحايدة
  "adjustment_warnings":      list[str],
}
```

### E. مخرج دراسة النسب

```python
{
  "portfolio_metrics": {
    "sample_size": int,
    "median_ratio": float,
    "mean_ratio": float,
    "weighted_mean_ratio": float,
    "cod": float,
    "prd": float,
    "matched_pairs_count": int,
  },
  "zone_metrics":           dict[zone_id, metrics],
  "property_class_metrics": dict[class, metrics],
  "matched_pairs":          list[dict],  # الأزواج المتطابقة
}
```

### F. مخرج معاينة المعايرة

```python
{
  "portfolio_calibration": {
    "sample_size": int,
    "median_ratio": float,
    "suggested_factor": float,  # target / median_ratio
    "recommendation": str,       # no_action | minor_adjustment | moderate_adjustment | major_review
    "warnings": list[str],
  },
  "zone_calibration":                dict,
  "property_class_calibration":      dict,
  "zone_property_class_calibration": dict,
}
```

### G. مخرج Calibration Sandbox (لكل صف)

```python
{
  "original_market_value":       float,  # غير مُعدَّل
  "sandbox_calibrated_value":    float,  # نسخة افتراضية فقط
  "calibration_factor_applied":  float,
  "calibration_factor_source":   str,    # zone_property_class | zone | property_class | portfolio | none
  "sandbox_value_delta":         float,
  "sandbox_value_delta_pct":     float,
  "sandbox_value_per_m2":        float,
  "calibration_sandbox_warnings":list[str],
}
```

### H. بيانات الحوكمة (Governance Metadata)

```python
{
  "governance_id":      str,   # GOV-YYYYMMDD-HHMMSS-XXXX
  "status":             str,   # draft | under_review | approved | rejected | superseded
  "reviewer_name":      str,
  "reviewer_role":      str,
  "decision_note":      str,
  "approved_outputs":   list[str],
  "governance_history": list[{"timestamp", "from_status", "to_status", "actor", "note"}],
  "created_at":         str,   # ISO timestamp
  "last_updated":       str,
  "approval_timestamp": str | None,
}
```

### I. بيانات إصدار النموذج (Model Cycle Metadata)

```python
{
  "cycle_id":              str,   # CYCLE-YYYY-REGION
  "cycle_name":            str,
  "revaluation_year":      int,
  "valuation_date":        str,   # YYYY-MM-DD
  "effective_date":        str,
  "model_version":         str,   # MA-MODEL-vX.Y
  "model_family":          str,   # baseline_batch_valuation
  "model_status":          str,   # draft | under_review | approved | retired | superseded
  "calibration_reference": str,
  "ratio_study_reference": str,
  "notes":                 str,
  "created_at":            str,
  "last_updated":          str,
}
```

---

## 4. مرجع الصيغ الرياضية (Formula Reference)

```
# سعر البيع لكل متر مربع
sale_price_per_m2 = sale_price / area

# عامل تعديل الوقت
time_adjustment_factor = (1 + monthly_growth_rate) ^ months_diff
  حيث months_diff = شهور من sale_date إلى valuation_date

# السعر المعدَّل زمنياً
adjusted_sale_price = sale_price × time_adjustment_factor

# عامل التعديل البيعي الإجمالي (حاصل ضرب العوامل الستة)
final_adjustment_factor =
  location_factor × size_factor × condition_factor
  × quality_factor × financing_factor × property_rights_factor

# السعر المعدَّل نهائياً
final_adjusted_sale_price =
  base_sale_price_for_adjustment × final_adjustment_factor
  حيث base = final_adjusted_sale_price إن وُجد، ثم adjusted_sale_price، ثم sale_price

# نسبة التقييم لكل زوج
ratio = appraised_value / sale_price_used
  حيث sale_price_used:
    1. final_adjusted_sale_price إن كان موجباً
    2. adjusted_sale_price إن كان موجباً
    3. sale_price

# وسيط النسب
median_ratio = median(all ratios)

# المتوسط الحسابي
mean_ratio = mean(all ratios)

# المتوسط المرجَّح
weighted_mean_ratio = Σ(appraised_value) / Σ(sale_price_used)

# معامل التشتت COD
COD = mean(|ratio_i - median_ratio|) / median_ratio × 100

# نسبة انحياز السعر PRD
PRD = mean_ratio / weighted_mean_ratio

# عامل المعايرة المقترح
suggested_factor = target_median_ratio / median_ratio
  الافتراضي: target_median_ratio = 1.0

# القيمة المعايَرة الافتراضية (Sandbox فقط — لا تُعدَّل market_value)
sandbox_calibrated_value = market_value × calibration_factor_applied
  ثم تُقرَّب إلى أقرب round_to (افتراضي 1000)
```

---

## 5. قواعد التوافق العكسي (Backward Compatibility Rules)

| القاعدة | التفاصيل |
|---------|---------|
| `/api/valuation` محمي | نقطة النهاية هذه لا تُلمس من أي مرحلة من Phase 3 |
| `advanced_valuation()` محمي | الدالة الجوهرية غير قابلة للتعديل من Phase 3 |
| صفوف Phase 1 بدون حقول منطقة | تعمل بشكل طبيعي؛ تُستبعد من تحليلات zone/property_class فقط |
| وحدات المبيعات إضافية | sales_verification/time_adjustment/adjustments لا تُعدّل mass_appraisal.py |
| Calibration Sandbox آمن | `apply_calibration_sandbox()` يبدأ بـ `out = dict(row)` ولا يُعدّل القاموس الأصلي أبداً |
| الحوكمة وبيانات النموذج | تُخزَّن فقط في `window.latestMassAppraisalRunResult.{governance,model_cycle}` — جلسة مؤقتة |
| `build_mass_appraisal_workbook()` | جميع المعاملات الجديدة اختيارية بقيمة `None`؛ المستدعون القدامى غير متأثرين |
| المعاملات الاختيارية في bridge_api | `ratio_study`, `governance`, `model_cycle` تُستخرج فقط إذا أرسلها العميل |

---

## 6. ملاحظات الصيانة

### تعديل Ratio Study

إضافة منطق مطابقة جديد: عدّل `_match_pair()` في `ratio_studies.py` (السطور ~120–180).  
لا تعدّل أولوية `sale_price_used` (3 طبقات) — قاعدة أساسية تؤثر على المعايرة.

### إضافة ورقة XLSX جديدة

1. أضف دالة `_sheet_xxx(wb, data)` في `mass_appraisal_excel.py`.
2. أضف معاملاً اختيارياً في `build_mass_appraisal_workbook()`.
3. أضف استخراج القيمة في `handle_mass_appraisal_export_xlsx()` بـ `bridge_api.py`.
4. أضف القيمة في `body JSON.stringify({...})` بـ `downloadMassAppraisalXlsx()`.

### إضافة نقطة نهاية Phase 3 جديدة

1. أنشئ الوحدة/الدالة المنطقية مستقلةً في `core_engine/`.
2. أضف `@app.route()` في `bridge_api.py` قبل `# ── Phase X.Y`.
3. استخدم نمط الاستيراد المزدوج: `try: from core_engine.X import Y except: from X import Y`.
4. شغّل: `python -c "import ast, pathlib; ast.parse(...)"`.
5. أضف قسم UI في `frontend/index.html`.

---

*للتشغيل التجريبي: راجع `docs/mass_appraisal_phase3_test_matrix.md`*  
*لدليل المستخدم: راجع `docs/mass_appraisal_phase3_user_guide.md`*
