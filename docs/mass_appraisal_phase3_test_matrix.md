# مصفوفة الاختبارات — التقييم الجماعي المتقدم (Phase 3)
**الإصدار:** Phase 3.10 — Release Stabilization  
**التاريخ:** 2026-05-02  
**الحالة:** RELEASE FREEZE  

---

## 1. اختبارات التجميع (Backend Compile Tests)

شغّل الأوامر التالية من جذر المشروع. يجب أن تمر **جميعها** بنجاح:

```powershell
# Python compile checks
python -m py_compile core_engine/mass_appraisal.py
python -m py_compile core_engine/mass_appraisal_excel.py
python -m py_compile core_engine/sales_verification.py
python -m py_compile core_engine/sales_time_adjustment.py
python -m py_compile core_engine/sales_adjustments.py
python -m py_compile core_engine/ratio_studies.py
python -m py_compile core_engine/model_calibration.py
python -m py_compile core_engine/calibration_sandbox.py
python -m py_compile core_engine/bridge_api.py
```

**النتيجة المتوقعة:** لا مخرجات (كود الخروج = 0).

---

## 2. فحص AST

```powershell
python -c "import ast, pathlib; ast.parse(pathlib.Path('core_engine/bridge_api.py').read_text(encoding='utf-8')); print('AST OK')"
```

**النتيجة المتوقعة:** `AST OK`

---

## 3. بناء Docker

```powershell
docker compose -f deploy/docker-compose.yml up -d --build flask
```

**النتيجة المتوقعة:** `Container ... Started` بدون أخطاء build.

**فحص الصحة بعد البناء:**
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/advisor/health" -Method Get
```

---

## 4. اختبارات نقاط النهاية (Endpoint Tests)

### 4.1 POST `/api/mass-appraisal/preview`

- [ ] HTTP 200 مع `{"status": "success"}`
- [ ] `summary.valid_rows` + `summary.invalid_rows` = `summary.total_rows`
- [ ] كل صف يحتوي على `valid`, `errors`, `warnings`
- [ ] HTTP 400 لجسم طلب فارغ
- [ ] HTTP 400 لصفوف غير مصفوفة

**حمولة الاختبار:**
```json
{"rows": [{"row_id": "T-001", "location": "التجمع الخامس", "property_type": "شقة سكنية", "area": 200, "valuation_purpose": "fair_market_value"}]}
```

---

### 4.2 POST `/api/mass-appraisal/run`

- [ ] HTTP 200 مع `{"status": "success"}`
- [ ] صفوف نجاح تحتوي: `market_value`, `currency`, `status: "success"`
- [ ] `summary.zone_summary` موجود إذا كانت هناك zone_id
- [ ] `summary.property_class_summary` موجود إذا كانت هناك property_class
- [ ] `data_quality_score` بين 0 و100
- [ ] `outlier_level` ∈ {`normal`, `moderate`, `high`, `extreme`}
- [ ] صفوف HBU/REIT/EIA تُرجع `status: "skipped"` مع `skip_reason`

---

### 4.3 POST `/api/mass-appraisal/export-xlsx`

- [ ] HTTP 200 مع Content-Type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- [ ] ملف XLSX صالح يُفتح في Excel
- [ ] ورقة "Executive Summary" موجودة
- [ ] ورقة "Portfolio" موجودة
- [ ] HTTP 400 `MISSING_RUN_RESULT` إذا أُرسل body فارغ

---

### 4.4 POST `/api/mass-appraisal/sales/verify`

- [ ] HTTP 200 مع `{"status": "success"}`
- [ ] `verification_summary` يحتوي: `usable_count`, `excluded_count`, `needs_review_count`
- [ ] كل سجل يحتوي على `verification_status` و`usability_status`
- [ ] HTTP 400 `MISSING_RECORDS` إذا لم تُرسَل records
- [ ] HTTP 400 `TOO_MANY_RECORDS` إذا تجاوزت 1000 سجل

---

### 4.5 POST `/api/mass-appraisal/sales/time-adjust`

- [ ] HTTP 200 مع `{"status": "success"}`
- [ ] كل سجل يحتوي على `time_adjustment_factor` و`adjusted_sale_price`
- [ ] `time_adjustment_factor > 1.0` إذا كان معدل النمو موجباً والتاريخ في المستقبل
- [ ] `time_adjustment_factor = 1.0` لصفقة بيع في تاريخ التقييم نفسه

---

### 4.6 POST `/api/mass-appraisal/sales/adjust`

- [ ] HTTP 200 مع `{"status": "success"}`
- [ ] كل سجل يحتوي على `final_adjustment_factor` و`final_adjusted_sale_price`
- [ ] جميع العوامل = 1.0 → `final_adjustment_factor = 1.0`
- [ ] تحذير `COMPOSITE_FACTOR_EXTREME` إذا كان الناتج المركّب خارج [0.60، 1.60]
- [ ] HTTP 400 `TOO_MANY_RECORDS` إذا تجاوزت 1000 سجل

---

### 4.7 POST `/api/mass-appraisal/ratio-study/run`

- [ ] HTTP 200 مع `{"status": "success"}`
- [ ] `portfolio_metrics` يحتوي: `median_ratio`, `cod`, `prd`
- [ ] `matched_pairs_count > 0` عند وجود عقارات ومبيعات متطابقة
- [ ] `zone_metrics` يُنتج مفاتيح `zone_id` عند توفرها
- [ ] تحذير عينة صغيرة عند أقل من `min_sample_size`

---

### 4.8 POST `/api/mass-appraisal/calibration/preview`

- [ ] HTTP 200 مع `{"status": "success"}`
- [ ] `portfolio_calibration.suggested_factor` ∈ (0، +∞)
- [ ] `recommendation` ∈ {`no_action`, `minor_adjustment`, `moderate_adjustment`, `major_review`}
- [ ] `calibration_note` الرسالة العربية موجودة
- [ ] HTTP 400 `MISSING_SUBJECT_ROWS` إذا لم تُرسَل صفوف

---

### 4.9 POST `/api/mass-appraisal/calibration/sandbox`

- [ ] HTTP 200 مع `{"status": "success"}`
- [ ] `original_market_value` = `market_value` الأصلي للصف (غير مُعدَّل)
- [ ] `sandbox_calibrated_value ≠ original_market_value` إذا كان العامل ≠ 1.0
- [ ] صفوف `status: "error"` تُعاد بـ `sandbox_calibrated_value: null`
- [ ] العامل المطبَّق يُقيَّد بين `min_factor` و`max_factor`
- [ ] HTTP 400 `MISSING_CALIBRATION_PREVIEW` إذا لم تُرسَل calibration_preview
- [ ] HTTP 400 `INVALID_CALIBRATION_PREVIEW` إذا غاب `portfolio_calibration` من الجسم

---

## 5. اختبارات الواجهة الأمامية (Frontend Tests)

**شرط:** افتح دائماً من `http://127.0.0.1:5000/` ليس من `file://`.

### 5.1 الوصول والتهيئة

- [ ] الواجهة تُحمَّل دون أخطاء console (F12)
- [ ] تحذير `file://` يظهر عند الفتح من الملف مباشرةً (البانر الأحمر)
- [ ] زر "تحميل مثال" يملأ textarea بصفوف صحيحة

### 5.2 تشغيل التقييم الجماعي

- [ ] زر "معاينة" يُظهر ملخص تحقق الصفوف
- [ ] زر "تشغيل" يُظهر جدول النتائج مع `market_value`
- [ ] ملخص zone_summary يظهر إذا كانت هناك zone_id
- [ ] لوحة الحوكمة (Phase 3.8) تظهر تلقائياً بعد نجاح التشغيل
- [ ] لوحة Model Cycle (Phase 3.9) تظهر تلقائياً بعد نجاح التشغيل

### 5.3 وحدة المبيعات

- [ ] قسم Sales Verification يفتح ويُرسل البيانات
- [ ] قسم Time Adjustment يُنتج `adjusted_sale_price`
- [ ] قسم Sales Adjustments يُنتج `final_adjusted_sale_price`
- [ ] زر "استخدام في دراسة النسب" ينقل السجلات المعدَّلة

### 5.4 Ratio Study و Calibration

- [ ] قسم Ratio Study يعمل ويُنتج Median Ratio، COD، PRD
- [ ] قسم Calibration Preview يعمل ويُنتج `suggested_factor` و`recommendation`
- [ ] قسم Calibration Sandbox يعمل ويُنتج `sandbox_calibrated_value`
- [ ] ألوان الشارات (badge) تتوافق مع مستوى التوصية

### 5.5 الحوكمة وبيانات النموذج

- [ ] تغيير حالة الحوكمة وحفظها يُحدِّث summary bar
- [ ] تغيير الحالة إلى `approved` يُثبِّت `approval_timestamp`
- [ ] تغيير الحالة من `approved` إلى غيرها يُزيل `approval_timestamp`
- [ ] سجل المراجعة `governance_history` يُضاف في كل حفظ
- [ ] حفظ بيانات Model Cycle يُحدِّث summary bar

### 5.6 التصدير والاستيراد

- [ ] تحميل CSV يشمل أعمدة `MODEL_CYCLE_FIELD` و`GOVERNANCE_FIELD` و`AUDIT_FIELD`
- [ ] تحميل XLSX ينتج ملفاً صالحاً
- [ ] تصدير الجلسة JSON يشمل `governance` و`model_cycle`
- [ ] استيراد الجلسة يُعيد عرض الحوكمة وبيانات النموذج

---

## 6. اختبارات الانحدار (Regression Tests)

### 6.1 صون /api/valuation

- [ ] `POST /api/valuation` يُرجع نتيجة تقييم صحيحة لعقار `fair_market_value`
- [ ] `POST /api/valuation` للـ Tax Appraisal يعمل بشكل طبيعي
- [ ] لا يوجد أي استدعاء لـ `/api/valuation` من أزرار Phase 3

### 6.2 صون Mass Appraisal Phase 1

- [ ] صفوف بدون `zone_id` تُقيَّم بنجاح
- [ ] صفوف بدون `property_class` تُقيَّم بنجاح
- [ ] `data_quality_score` لا يزال يُحسب للصفوف البسيطة
- [ ] `outlier_score` لا يزال يُحسب

### 6.3 عزل Calibration Sandbox

- [ ] بعد تشغيل Sandbox: `market_value` في `window.latestMassAppraisalRunResult.rows[i]` **لم يتغير**
- [ ] `original_market_value` في نتيجة Sandbox = `market_value` الأصلي

### 6.4 عدم التطبيق التلقائي

- [ ] عند تشغيل Calibration Preview فقط: لا يتغير أي `market_value`
- [ ] Calibration Sandbox نتائجه لا تؤثر على تشغيل جديد
- [ ] `saveMassGovernanceDecision()` لا يرسل أي طلب HTTP

---

## 7. نتائج py_compile المُسجَّلة (2026-05-02)

| الملف | النتيجة |
|-------|---------|
| `core_engine/mass_appraisal.py` | ✅ OK |
| `core_engine/mass_appraisal_excel.py` | ✅ OK |
| `core_engine/sales_verification.py` | ✅ OK |
| `core_engine/sales_time_adjustment.py` | ✅ OK |
| `core_engine/sales_adjustments.py` | ✅ OK |
| `core_engine/ratio_studies.py` | ✅ OK |
| `core_engine/model_calibration.py` | ✅ OK |
| `core_engine/calibration_sandbox.py` | ✅ OK |
| `core_engine/bridge_api.py` | ✅ OK (AST) |
