# دليل المستخدم — التقييم الجماعي المتقدم (Phase 3)
**الإصدار:** Phase 3.10 — Release Stabilization  
**التاريخ:** 2026-05-02  
**الجمهور المستهدف:** محلل التقييم / مشغّل منظومة التقييم الجماعي  
**المرجع:** IAAO Standard on Mass Appraisal (2013) · IVS 105  

---

## 1. نظرة عامة

يوفّر نظام Expert Smart منظومة تقييم جماعي متقدمة (Advanced Mass Appraisal) مكوّنة من عشر مراحل (Phase 3.0 – 3.10). تغطي هذه المنظومة دورة حياة التقييم كاملةً: من استيعاب العقارات المراد تقييمها، مروراً بالتحقق من بيانات المبيعات وضبط الوقت والعوامل البيعية ودراسة النسب والمعايرة، وصولاً إلى الحوكمة وإدارة إصدارات النموذج والتوثيق.

**ما يفعله النظام:**
- يُشغّل دفعات تقييم جماعي بالإسناد إلى محرك AVM ومحرك التقييم المتقدم.
- يُحلّل بيانات المبيعات ويتحقق منها ويضبطها زمنياً وعوامياً.
- يُنتج مؤشرات Ratio Study وفق معايير IAAO: Median Ratio، COD، PRD.
- يعرض معاينة المعايرة (Calibration Preview) دون تطبيقها تلقائياً.
- يُتيح اختبار سيناريوهات المعايرة في بيئة Sandbox دون المساس بالقيم الأصلية.
- يُسجّل قرارات الحوكمة ويُتيح ربطها بسير العمل التحليلي.
- يُدير بيانات إصدار النموذج ودورة إعادة التقييم لأغراض التتبع والمراجعة.

**ما لا يفعله النظام تلقائياً:**
- لا يُطبّق المعايرة تلقائياً على قيم التقييم.
- لا يُعدّل `market_value` لأي صف دون تدخل المحلل.
- لا يحفظ البيانات في قاعدة بيانات دائمة (الجلسة مؤقتة).
- لا يُصدر موافقات رسمية بموجب أي إطار تنظيمي.

---

## 2. سير العمل الكامل — من البداية إلى النهاية

### A. إعداد العقارات المراد تقييمها (Subject Properties)

**الحقول المطلوبة كحد أدنى:**

| الحقل | النوع | الوصف |
|-------|-------|-------|
| `row_id` | نص | معرّف فريد للصف |
| `location` | نص | موقع العقار |
| `property_type` | نص | نوع العقار (شقة سكنية، فيلا...) |
| `area` | رقم | المساحة بالمتر المربع |
| `valuation_purpose` | نص | الغرض: `fair_market_value`، `tax_assessment`، `usufruct`، `uncertainty_valuation` |

**الحقول الإضافية للتقسيم الجغرافي (Phase 3.1):**

| الحقل | الوصف |
|-------|-------|
| `zone_id` | رمز المنطقة السوقية (مثال: `Z-NC-01`) |
| `neighborhood` | الحي |
| `submarket` | السوق الفرعي |
| `property_class` | فئة العقار (مثال: `residential`, `commercial`) |

**ملاحظة:** الحقول الجغرافية اختيارية؛ يعمل النظام بدونها ويُسقطها من تحليل المناطق فقط.

---

### B. تشغيل التقييم الجماعي

1. **المعاينة (Preview):** اضغط **معاينة** للتحقق من صحة البيانات دون حساب القيم.
2. **التشغيل (Run):** اضغط **تشغيل** لحساب `market_value` لكل صف.
3. **مراجعة النتائج:** راجع كل صف وحالته (`success`/`error`/`skipped`).
4. **مراجعة الجودة والشذوذات:** تحقق من حقول `data_quality_level` و`outlier_level` و`review_required`.

بعد نجاح التشغيل تظهر تلقائياً لوحات Governance (Phase 3.8) وModel Cycle (Phase 3.9).

---

### C. إعداد بيانات المبيعات (Sales Evidence)

**الحقول الأساسية لكل صفقة بيع:**

| الحقل | النوع | الوصف |
|-------|-------|-------|
| `sale_id` | نص | معرّف فريد للصفقة |
| `sale_price` | رقم | سعر البيع (بالعملة المحلية) |
| `sale_date` | نص | تاريخ البيع (ISO: `YYYY-MM-DD`) |
| `area` | رقم | المساحة بالمتر المربع |
| `location` | نص | الموقع |
| `property_type` | نص | نوع العقار |

**الحقول الاختيارية للتطابق مع العقارات (Phase 3.1):**

```
zone_id, neighborhood, submarket, property_class
```

---

### D. التحقق من المبيعات (Sales Verification — Phase 3.2)

أرسل السجلات إلى `/api/mass-appraisal/sales/verify`.

يُصنّف النظام كل صفقة وفق:

| الحالة | المعنى |
|--------|--------|
| `usable` | صالحة للاستخدام في دراسة النسب |
| `excluded` | مستبعدة (بيع غير ذراع طول، ضغط بيعي...) |
| `needs_review` | تحتاج مراجعة محلل |

تحقق من `verification_summary` للاطلاع على: `total_records`، `usable_count`، `excluded_count`، `needs_review_count`.

---

### E. تعديل الوقت — Time Adjustment (Phase 3.4)

أرسل سجلات المبيعات مع تاريخ التقييم ومعدل النمو الشهري إلى `/api/mass-appraisal/sales/time-adjust`.

**الحقول الرئيسية:**

| الحقل | المعنى |
|-------|--------|
| `valuation_date` | تاريخ التقييم المرجعي |
| `monthly_growth_rate` | معدل النمو الشهري (مثال: `0.005` = 0.5%) |

**المخرجات لكل صفقة:**

| الحقل | المعنى |
|-------|--------|
| `time_adjustment_factor` | عامل الضبط الزمني |
| `months_to_valuation_date` | عدد الأشهر من تاريخ البيع إلى تاريخ التقييم |
| `adjusted_sale_price` | السعر بعد ضبط الوقت |

---

### F. عوامل التعديل البيعي — Sales Adjustment Factors (Phase 3.5)

أرسل السجلات إلى `/api/mass-appraisal/sales/adjust` مع ملف التعديلات (`adjustment_profile`).

**العوامل الستة المدعومة:**

| العامل | المفتاح |
|--------|--------|
| تعديل الموقع | `location_factor` |
| تعديل المساحة | `size_factor` |
| تعديل الحالة | `condition_factor` |
| تعديل الجودة | `quality_factor` |
| تعديل التمويل | `financing_factor` |
| تعديل حقوق الملكية | `property_rights_factor` |

- القيم الطبيعية: 1.0 (لا تعديل).
- حدود التحذير الفردية: خارج [0.70، 1.30].
- حدود التحذير المركّبة: خارج [0.60، 1.60].
- المخرج الرئيسي: `final_adjusted_sale_price = base_sale_price × final_adjustment_factor`.

---

### G. دراسة النسب — Ratio Study (Phase 3.3)

أرسل صفوف العقارات وسجلات المبيعات إلى `/api/mass-appraisal/ratio-study/run`.

**المخرجات الرئيسية:**

| المؤشر | المعنى |
|--------|--------|
| `median_ratio` | الوسيط الحسابي لنسب التقييم |
| `mean_ratio` | المتوسط الحسابي |
| `weighted_mean_ratio` | المتوسط المرجَّح بالمساحة/القيمة |
| `COD` | معامل التشتت — يقيس التجانس (IAAO: < 15% للسكني) |
| `PRD` | نسبة انحياز السعر (IAAO: قريب من 1.0) |
| `matched_pairs_count` | عدد الأزواج المتطابقة |

يُنتج النظام تحليلاً على مستوى: المحفظة الكاملة، المناطق (`zone_calibration`)، فئات العقارات (`property_class_calibration`).

---

### H. معاينة المعايرة — Calibration Preview (Phase 3.6)

أرسل إلى `/api/mass-appraisal/calibration/preview`.

**المخرجات:**

| الحقل | المعنى |
|-------|--------|
| `suggested_factor` | `target_median_ratio ÷ median_ratio` |
| `recommendation` | `no_action` / `minor_adjustment` / `moderate_adjustment` / `major_review` |
| `warnings` | تحذيرات عينة صغيرة أو انحراف عالٍ |

> **تحذير:** `suggested_factor` معلومة استرشادية فقط. لا يُطبّق النظام أي معايرة تلقائية.

---

### I. بيئة اختبار المعايرة — Calibration Sandbox (Phase 3.7)

أرسل نتائج التشغيل ومعاينة المعايرة إلى `/api/mass-appraisal/calibration/sandbox`.

**ضمانات الأمان:**
- `market_value` الأصلي لا يُعدَّل أبداً.
- يُضاف `original_market_value` للحفظ.
- `sandbox_calibrated_value` هو القيمة الافتراضية فقط.
- لا يؤثر على أي تشغيل مستقبلي.

**المخرجات:**

| الحقل | المعنى |
|-------|--------|
| `sandbox_calibrated_value` | القيمة المعايَرة الافتراضية |
| `calibration_factor_applied` | العامل المطبّق |
| `calibration_factor_source` | مصدر العامل: `zone_property_class` / `zone` / `property_class` / `portfolio` |
| `sandbox_value_delta` | الفرق المطلق عن القيمة الأصلية |
| `sandbox_value_delta_pct` | الفرق النسبي % |

**أولوية تطبيق العوامل:** `zone_property_class` → `zone` → `property_class` → `portfolio` → `none`.

---

### J. سير الحوكمة — Governance Approval Workflow (Phase 3.8)

بعد نجاح التشغيل تظهر لوحة الحوكمة تلقائياً. أدخل:

| الحقل | المعنى |
|-------|--------|
| `reviewer_name` | اسم المراجع |
| `reviewer_role` | الصفة الوظيفية |
| `status` | حالة القرار (انظر الجدول أدناه) |
| `decision_note` | ملاحظة القرار |
| المخرجات المعتمدة | اختر ما يُعتمد: المحفظة الخام / المراجَعة / معاينة المعايرة / Sandbox |

**حالات الحوكمة:**

| الحالة | المعنى |
|--------|--------|
| `draft` | مسودة (الافتراضي) |
| `under_review` | قيد المراجعة |
| `approved` | معتمد (يُثبَّت `approval_timestamp`) |
| `rejected` | مرفوض |
| `superseded` | تم استبداله بإصدار أحدث |

يُسجَّل كل تغيير حالة في `governance_history` مع الطابع الزمني والمسؤول والملاحظة.

---

### K. إصدار النموذج ودورة إعادة التقييم (Phase 3.9)

تظهر لوحة إصدار النموذج تلقائياً بعد نجاح التشغيل بالقيم الافتراضية. حدّثها حسب الدورة:

| الحقل | مثال |
|-------|------|
| `cycle_id` | `CYCLE-2026-NEWCAIRO` |
| `cycle_name` | `New Cairo Revaluation Cycle 2026` |
| `revaluation_year` | `2026` |
| `valuation_date` | `2026-05-02` |
| `effective_date` | `2026-07-01` |
| `model_version` | `MA-MODEL-v1.0` |
| `model_family` | `baseline_batch_valuation` |
| `model_status` | `draft` / `under_review` / `approved` / `retired` / `superseded` |
| `calibration_reference` | معرّف معاينة المعايرة إن وجد |
| `ratio_study_reference` | معرّف دراسة النسب إن وجد |

اضغط **حفظ بيانات دورة التقييم** لتحديث الجلسة.

---

### L. تصدير المخرجات

| التصدير | المحتوى |
|---------|---------|
| **CSV** | جميع صفوف التشغيل + ملخص المحفظة المراجَعة + بيانات الحوكمة (GOVERNANCE_FIELD) + بيانات دورة التقييم (MODEL_CYCLE_FIELD) + بيانات التدقيق (AUDIT_FIELD) |
| **XLSX** | مصنّف Excel احترافي متعدد الأوراق: ملخص تنفيذي، المحفظة، تحليلات المناطق والفئات، دراسة النسب، معاينة المعايرة، Sandbox، الحوكمة، إصدار النموذج |
| **JSON (جلسة)** | تصدير/استيراد الجلسة الكاملة بما يشمل النتائج وقرارات المراجعة وبيانات الحوكمة وبيانات النموذج |

---

## 3. أمثلة على المدخلات

### مثال: صف عقار مراد تقييمه

```json
{
  "row_id": "R-001",
  "location": "التجمع الخامس",
  "property_type": "شقة سكنية",
  "area": 200,
  "valuation_purpose": "fair_market_value",
  "zone_id": "Z-NC-01",
  "neighborhood": "القطامية",
  "submarket": "New Cairo",
  "property_class": "residential"
}
```

### مثال: سجل التحقق من المبيعات

```json
{
  "sale_id": "S-001",
  "sale_price": 3500000,
  "sale_date": "2025-11-15",
  "area": 190,
  "location": "التجمع الخامس",
  "property_type": "شقة سكنية",
  "zone_id": "Z-NC-01",
  "property_class": "residential"
}
```

### مثال: طلب تعديل الوقت

```json
{
  "records": [{"sale_id": "S-001", "sale_price": 3500000, "sale_date": "2025-11-15", "area": 190}],
  "valuation_date": "2026-05-02",
  "monthly_growth_rate": 0.005
}
```

### مثال: طلب عوامل التعديل البيعي

```json
{
  "sale_records": [{"sale_id": "S-001", "sale_price": 3500000, "area": 190}],
  "adjustment_profile": {
    "location_factor": 1.02,
    "size_factor": 0.98,
    "condition_factor": 1.0,
    "quality_factor": 1.0,
    "financing_factor": 1.0,
    "property_rights_factor": 1.0
  }
}
```

### مثال: طلب دراسة النسب

```json
{
  "subject_rows": [{"row_id": "R-001", "market_value": 3700000, "zone_id": "Z-NC-01", "property_class": "residential"}],
  "sale_records": [{"sale_id": "S-001", "final_adjusted_sale_price": 3550000, "zone_id": "Z-NC-01", "property_class": "residential"}]
}
```

### مثال: طلب معاينة المعايرة

```json
{
  "subject_rows": [...],
  "sale_records": [...],
  "options": {"target_median_ratio": 1.0, "min_sample_size": 3}
}
```

---

## 4. تفسير المخرجات

| الحقل | التفسير |
|-------|---------|
| `zone_summary` | إحصائيات المحفظة مجمَّعة حسب منطقة (`zone_id`): عدد الصفوف، إجمالي القيمة، المتوسط، الوسيط، قيمة/م² |
| `property_class_summary` | نفسه مجمَّعاً حسب فئة العقار |
| `verification_summary` | `total_records`، `usable_count`، `excluded_count`، `needs_review_count` |
| `adjusted_sale_price` | السعر بعد ضبط الوقت (Phase 3.4) |
| `final_adjusted_sale_price` | السعر بعد ضبط الوقت والعوامل البيعية (Phase 3.5) |
| `median_ratio` | وسيط نسب التقييم؛ الهدف قريب من 1.0 (= تقييم عادل في المتوسط) |
| `COD` | تشتت النسب — كلما انخفض كان النموذج أكثر تجانساً (IAAO: < 15% للسكني) |
| `PRD` | انحياز السعر — > 1.0 يشير إلى تقييم مرتفع للعقارات الرخيصة؛ < 1.0 عكسه (IAAO: 0.98–1.03) |
| `suggested_factor` | نسبة الضبط المقترحة = `target / median_ratio`؛ استرشادية فقط |
| `sandbox_calibrated_value` | القيمة الافتراضية بعد تطبيق `suggested_factor`؛ لا تُعدّل `market_value` الأصلي |
| `governance_status` | حالة قرار الحوكمة: `draft`/`under_review`/`approved`/`rejected`/`superseded` |
| `model_cycle` | بيانات دورة إعادة التقييم: `cycle_id`، `model_version`، `valuation_date`، `effective_date`، `model_status` |

---

## 5. القيود المعروفة (Known Limitations)

| القيد | الوصف |
|-------|-------|
| لا استمرارية في قاعدة البيانات | جميع البيانات جلسة مؤقتة؛ تُفقد عند إغلاق المتصفح ما لم تُصدَّر كجلسة JSON |
| لا معايرة تلقائية | `suggested_factor` معلومة استرشادية فقط؛ التطبيق يتطلب قرار محلل |
| لا إيداع تنظيمي رسمي | الحوكمة للتتبع الداخلي؛ لا تُعدّ موافقة رسمية بموجب أي إطار قانوني |
| لا تطابق جغرافي | التطابق بين العقارات والمبيعات يعتمد على `zone_id` و`property_class` والحقول النصية، لا الإحداثيات الجغرافية |
| لا تدريب نموذج آلي | النموذج ثابت؛ لا تعلم آلي أو إعادة تدريب تلقائية |
| تحذيرات العينة الصغيرة | إذا كانت عينة المبيعات أقل من `min_sample_size` (افتراضي 3)، تُصدر تحذيرات IAAO ويجب مراعاتها |
| مراجعة المحلل إلزامية | لا يُعتمد أي قرار دون مراجعة بشرية مؤهلة |
| حد أقصى للسجلات | 1,000 سجل بيع في الطلب الواحد |

---

*للاستفسارات التقنية: راجع `docs/mass_appraisal_phase3_technical_reference.md`*  
*لقائمة الاختبارات: راجع `docs/mass_appraisal_phase3_test_matrix.md`*
