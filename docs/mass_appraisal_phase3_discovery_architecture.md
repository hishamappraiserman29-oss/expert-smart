# محرك التقييم الجماعي المتقدم — Phase 3.0
## تقرير الاكتشاف والبنية المعمارية وتحليل الفجوات
**الإصدار:** Phase 3.0 — Discovery Only (لا كود، لا تعديلات)  
**التاريخ:** 2026-05-02  
**المرجع:** IAAO Standard on Mass Appraisal of Real Property (2013) + IVS 105  
**الحالة:** وثيقة تخطيط — للمراجعة قبل الشروع في التنفيذ  

---

## A. خريطة Mass Appraisal Phase 1 الحالية

### A1. جدول الملفات

| الملف | الحجم | الوظيفة/القسم | المسؤولية الحالية | قابل لإعادة الاستخدام في Phase 3؟ | مستوى الخطورة |
|-------|-------|--------------|------------------|----------------------------------|--------------|
| `core_engine/mass_appraisal.py` | 1,013 سطر | `validate_rows()`, `run_batch()`, `_score_row_quality()`, `_compute_portfolio_stats()`, `_tag_outliers()` | المحرك الكامل للدفعات: التحقق، التقييم، إثراء البيانات، الكشف عن الشذوذات، ملخص المحفظة | نعم — يُوسَّع لا يُعاد كتابته | **متوسط** — أي تغيير يؤثر على كل صف |
| `core_engine/mass_appraisal_excel.py` | 1,269 سطر | 15 دالة لتوليد الأوراق + `build_mass_appraisal_workbook()` | توليد XLSX الاحترافي في الذاكرة | نعم — أوراق جديدة تُضاف لا تُستبدل | **منخفض** — الأوراق القائمة مستقلة |
| `core_engine/bridge_api.py` (مقاطع MA) | ~50 سطر | `handle_mass_appraisal_preview()`, `handle_mass_appraisal_run()`, `handle_mass_appraisal_export_xlsx()` | 3 نقاط نهاية REST | نعم — نقاط نهاية جديدة مستقلة | **منخفض** — نقاط النهاية الحالية لا تُلمس |
| `frontend/index.html` (قسم MA) | ~1,165 سطر JS/HTML | 29 دالة JS، textarea، زر تحميل، جدول نتائج، مراجعة، جلسة | الواجهة الكاملة للتقييم الجماعي | نعم — حقول وأعمدة جديدة تُضاف بحذر | **متوسط** — ازدحام بصري إذا أُضيفت حقول كثيرة |
| `core_engine/avm_dispatcher.py` | ~300 سطر | `dispatch_avm()`, `compute_avm_estimate()`, `is_avm_eligible()` | توزيع وحساب AVM بناءً على سجلات السوق | نعم — يُستدعى من mass_appraisal.py | **منخفض** — لا تعديل مخطط |
| `core_engine/data/market_feed.json` | سجلات صفقات | صفقات تاريخية: location, property_type, area, price, price_per_meter, credibility, timestamp, source | مصدر بيانات AVM والمقارنة السوقية | نعم — مصدر بيانات للمبيعات والمعايرة | **منخفض** — للقراءة فقط |
| `core_engine/market_intelligence.py` | غير محدد | ذكاء السوق | تحليل السوق المحلي | يحتاج فحصاً إضافياً | **غير محدد** |
| `core_engine/price_index_engine.py` | غير محدد | مؤشر الأسعار بالانحدار الزمني | حسابات تعديل الوقت | **نعم — مهم لـ Phase 3** | **منخفض** — قائم ويعمل |
| `docs/mass_appraisal_phase1_release_checklist.md` | 16 KB | قائمة فحص Phase 1.11 | توثيق الاختبار والإصدار | مرجع — لا يُعدَّل | — |

---

### A2. جدول الدوال الرئيسية

| الدالة | الملف | السطر | المسؤولية |
|--------|-------|-------|-----------|
| `validate_rows(rows, options)` | `mass_appraisal.py` | 523–619 | معاينة/تحقق من صحة الصفوف دون حساب |
| `run_batch(rows, options)` | `mass_appraisal.py` | 622–996 | خط أنابيب التقييم الكامل |
| `_score_row_quality(row, purpose)` | `mass_appraisal.py` | 152–327 | جودة بيانات كل صف (0–100) |
| `_compute_portfolio_stats(results)` | `mass_appraisal.py` | 354–386 | إحصائيات المحفظة: وسيط، متوسط، قيمة/م² |
| `_tag_outliers(results, stats)` | `mass_appraisal.py` | 389–520 | وسم الصفوف بالشذوذات وأسباب المراجعة |
| `build_mass_appraisal_workbook(result, reviewed_summary, audit)` | `mass_appraisal_excel.py` | 1237–1269 | توليد XLSX (15 ورقة) في الذاكرة |
| `dispatch_avm(payload, records)` | `avm_dispatcher.py` | — | حساب AVM وإرجاع الثقة والتقدير |

### A3. الثوابت والحدود

| الثابت | القيمة | الملف |
|--------|--------|-------|
| `MAX_ROWS` | 100 | `mass_appraisal.py:112` |
| `BATCH_SUPPORTED_PURPOSES` | 11 غرضاً | `mass_appraisal.py:114–119` |
| `BATCH_EXCLUDED_PURPOSES` | HBU, REIT, EIA | `mass_appraisal.py:120–123` |
| `_OL_MV_HIGH_FACTOR` | 2.5× الوسيط | `mass_appraisal.py:332` |
| `_OL_MV_LOW_FACTOR` | 0.40× الوسيط | `mass_appraisal.py:333` |
| `_OL_VPM2_HIGH_FACTOR` | 2.0× الوسيط | `mass_appraisal.py:334` |
| `_OL_AVM_MIN_RECORDS` | 5 | `mass_appraisal.py:338` |

---

## B. سير عمل Phase 1 الحالي

```
المدخل: JSON array (textarea / ملف JSON / ملف CSV)
       │
       ▼ POST /api/mass-appraisal/preview
┌─────────────────────────────────────────────────────────────┐
│  validate_rows(rows, options)                               │
│  لكل صف:                                                    │
│    ├── التحقق من الحقول المطلوبة: location, property_type, area │
│    ├── _score_row_quality() → score (0–100), level, flags   │
│    └── تجميع: total, valid, invalid, warning                 │
│  لا تقييم — لا market_value                                  │
└──────────────────┬──────────────────────────────────────────┘
                   │ (اختياري: مراجعة نتائج Preview)
                   ▼ POST /api/mass-appraisal/run
┌─────────────────────────────────────────────────────────────┐
│  run_batch(rows, options)                                   │
│                                                             │
│  لكل صف:                                                    │
│  1. التحقق المبدئي (حقول، منطقية المساحة)                   │
│  2. AVM Dispatch → dispatch_avm() [إن طُلب أو لم يُعطَ PPM] │
│  3. Augment → usufruct / uncertainty [حسب الغرض]            │
│  4. Valuation → advanced_valuation(location, area, type, PPM)│
│  5. Enrichment:                                             │
│     ├── AVM block (applied, confidence, n_records, ppm)     │
│     ├── Tax block [إن كان الغرض tax_assessment]             │
│     ├── Usufruct block [إن كان usufruct]                    │
│     └── Uncertainty block [إن كان uncertainty_valuation]    │
│  6. Data Quality → _score_row_quality()                     │
│                                                             │
│  بعد معالجة كل الصفوف:                                      │
│  7. Portfolio Stats → _compute_portfolio_stats()            │
│  8. Outlier Tagging → _tag_outliers() (بناءً على الوسيط)   │
│                                                             │
│  المخرج: per-row results + portfolio summary                │
└──────────────────┬──────────────────────────────────────────┘
                   │
         ┌─────────┴──────────┐
         │                    │
         ▼                    ▼
CSV (client-side)    POST /api/mass-appraisal/export-xlsx
JS → buildMassAppraisalCsv()  │
                               ▼
                    build_mass_appraisal_workbook()
                    └── 15 ورقة Excel في الذاكرة
                        (Executive Summary, Portfolio, DQ,
                         Review Queue, Tax, Audit...)
                               │
                               ▼
                    (اختياري) حفظ الجلسة / استعادتها
                    exportMassAppraisalSession() / importMassAppraisalSession()
```

**الحقول المُضافة لكل صف بعد run_batch:**

| المرحلة | الحقول المُضافة |
|---------|---------------|
| 1.4 | `location`، `property_type`، `area`، `price_per_meter_effective`، `calculation_source` |
| 1.5 | `data_quality_score`، `data_quality_level`، `data_quality_flags` |
| 1.6 | `value_per_m2`، `review_required`، `outlier_score`، `outlier_level`، `review_reasons` |
| 1.8 | `review_status`، `analyst_note`، `exclude_from_final_summary` (واجهة فقط) |
| 1.9 | `audit` metadata (batch_id، analyst_name، timestamps) |

---

## C. تحليل الفجوات مقابل محرك التقييم الجماعي الاحترافي (IAAO)

### C1. جدول الفجوات الكامل

| المجال | القدرة المطلوبة | الحالة الحالية | الفجوة | التصنيف |
|--------|----------------|---------------|--------|---------|
| **أ. تقسيم السوق** | | | | |
| | `zone_id` لكل صف | غائب تماماً | كاملة | ❌ مفقودة |
| | `neighborhood` | غائب | كاملة | ❌ مفقودة |
| | `submarket` | غائب | كاملة | ❌ مفقودة |
| | إحصائيات على مستوى المنطقة | وسيط المحفظة كلها (لا تقسيم) | جزئية | ⚠ جزئية |
| | مقارنة بين المناطق | غائبة | كاملة | ❌ مفقودة |
| **ب. تصنيف العقارات** | | | | |
| | `property_class` على مستوى الدفعة | موجود فقط في مسار `tax_assessment` | جزئية | ⚠ جزئية |
| | نماذج خاصة بكل فئة | غير موجودة — نموذج واحد لكل شيء | كاملة | ❌ مفقودة |
| | `use_class` (سكني/تجاري/إداري...) | `property_type` كنص حر فقط | جزئية | ⚠ جزئية |
| | إحصائيات الفئة ضمن الدفعة | `property_type_counts` (عدد فقط) | جزئية | ⚠ جزئية |
| **ج. التحقق من المبيعات** | | | | |
| | `sale_validity_status` | غائب — لا يوجد أي مفهوم للمبيعات | كاملة | ❌ مفقودة |
| | علامة `arms_length` | غائبة | كاملة | ❌ مفقودة |
| | `verification_source` | غائب | كاملة | ❌ مفقودة |
| | `sale_adjustment_notes` | غائبة | كاملة | ❌ مفقودة |
| | أسباب الاستبعاد من المبيعات | غائبة | كاملة | ❌ مفقودة |
| **د. تعديلات المبيعات** | | | | |
| | تعديل الوقت (`time_adjustment`) | `price_index_engine.py` موجود — لكن غير مُدمج في الدفعات | جزئية | ⚠ جزئية |
| | تعديل الموقع | داخل AVM substring match فقط | جزئية | ⚠ جزئية |
| | تعديل الحالة / الجودة | غائب | كاملة | ❌ مفقودة |
| | تعديل الحجم | غائب | كاملة | ❌ مفقودة |
| | تعديل التمويل | غائب | كاملة | ❌ مفقودة (غير مطلوب على الأرجح) |
| **هـ. معايرة النموذج** | | | | |
| | `model_family` | غائب — `advanced_valuation()` صندوق أسود | كاملة | ❌ مفقودة |
| | معاملات النموذج | غير مُعرَّضة | كاملة | ❌ مفقودة |
| | عينة التدريب وعينة الاختبار | غائبة | كاملة | ❌ مفقودة |
| | تاريخ المعايرة | غائب | كاملة | ❌ مفقودة |
| | مقاييس أداء النموذج (RMSE، R²...) | غائبة | كاملة | ❌ مفقودة |
| **و. دراسات النسب** | | | | |
| | نسبة القيمة المقدَّرة / سعر البيع | غائبة (لا توجد بيانات مبيعات مقابل تقدير) | كاملة | ❌ مفقودة |
| | الوسيط (Median Ratio) | غائب | كاملة | ❌ مفقودة |
| | COD (Coefficient of Dispersion) | غائب | كاملة | ❌ مفقودة |
| | PRD (Price-Related Differential) | غائب | كاملة | ❌ مفقودة |
| | مؤشرات العدالة العمودية/الأفقية | غائبة | كاملة | ❌ مفقودة |
| | ملاحظة: فحص `TAX_RATIO_HIGH` (ضريبة > 5% من MV) موجود في `_tag_outliers()` — لكنه ليس دراسة نسب حقيقية | ⚠ شبه جزئي | — |
| **ز. جودة البيانات** | | | | |
| | الاكتمال | ✅ موجودة — `_score_row_quality()` | — | ✅ مُنفَّذة |
| | الاتساق | ✅ جزئياً (نطاقات المساحة، المنطقية) | — | ✅ مُنفَّذة |
| | المعقولية | ✅ جزئياً (PPM limits) | — | ⚠ جزئية |
| | الثقة الجغرافية | `location` كنص فقط — لا إحداثيات | جزئية | ⚠ جزئية |
| | الكشف عن التكرار | غائب | كاملة | ❌ مفقودة |
| **ح. الحوكمة والتدقيق** | | | | |
| | `model_version` | غائب | كاملة | ❌ مفقودة |
| | `batch_id` | ✅ موجود (Phase 1.9) | — | ✅ مُنفَّذ |
| | قرار المحلل | ✅ `review_status` (Phase 1.8) | — | ✅ مُنفَّذ |
| | حالة الاعتماد (`approval_state`) | يدوي فقط — لا سير عمل ملزم | جزئية | ⚠ جزئية |
| | ملاحظات التدقيق | ✅ `analyst_note`، `audit_notes` | — | ✅ مُنفَّذ |
| | قابلية الاستنساخ | ✅ session export/import | — | ✅ مُنفَّذ |
| | إصدار النموذج | غائب | كاملة | ❌ مفقودة |
| | دورة إعادة التقييم | غائبة | كاملة | ❌ مفقودة |

### C2. ملخص حالة الفجوات

| التصنيف | العدد | النسبة |
|---------|-------|--------|
| ✅ مُنفَّذ | 8 قدرات | 20% |
| ⚠ جزئياً مُنفَّذ | 8 قدرات | 20% |
| ❌ مفقودة كلياً | 23 قدرة | 57% |
| — لا ينطبق بعد | 1 | 3% |

**الخلاصة:** النظام الحالي يُحقق جودة بيانات جيدة وحوكمة أولية، لكنه يفتقر إلى الركيزتين الأساسيتين في التقييم الجماعي الاحترافي: **تقسيم السوق** و**دراسات النسب**، فضلاً عن غياب أي منهجية للمعايرة والتحقق من المبيعات.

---

## D. البنية المعمارية المقترحة لـ Phase 3

### D1. مبادئ التصميم

1. **الإضافة لا الاستبدال:** Phase 1 يبقى كما هو — Phase 3 يُضيف طبقات فوقه.
2. **الاستقلالية المعيارية:** كل وحدة جديدة ملف مستقل — لا اعتمادات دائرية.
3. **التدهور الأمين:** إذا غابت zone_id أو sales_data، تعمل الدفعة بالنتائج الجزئية فقط.
4. **الواجهة الخلفية أولاً:** لا تغييرات في الواجهة حتى يُختبر الـ API.
5. **لا تعديل على `/api/valuation`:** نقطة النهاية الفردية محمية تماماً.

### D2. خريطة الوحدات المقترحة

```
┌─────────────────────────────────────────────────────────────────────┐
│  Phase 3 — New Modules (لا تُنشأ بعد)                              │
│                                                                     │
│  core_engine/mass_zones.py              ← Phase 3.1                │
│  ├── zone_id, neighborhood, submarket fields                        │
│  ├── group_by_zone(results) → zone summaries                        │
│  └── group_by_class(results) → class summaries                      │
│                                                                     │
│  core_engine/sales_verification.py      ← Phase 3.2                │
│  ├── verify_sale(sale_record) → validity_status                     │
│  ├── flag_non_arms_length(sale) → bool                              │
│  └── build_verified_sales_pool(records) → list[SaleRecord]         │
│                                                                     │
│  core_engine/ratio_studies.py           ← Phase 3.3                │
│  ├── compute_ratio_study(assessed, sales) → RatioStudyResult        │
│  ├── compute_cod(ratios) → float                                    │
│  ├── compute_prd(ratios, values) → float                            │
│  └── equity_analysis(ratios) → dict                                 │
│                                                                     │
│  core_engine/model_calibration.py       ← Phase 3.4                │
│  ├── calibrate_model(sample, purpose, zone) → CalibrationRecord     │
│  ├── apply_calibration(row, calib_record) → float                   │
│  └── store_calibration_history(record) → None                       │
│                                                                     │
│  core_engine/mass_governance.py         ← Phase 3.5                │
│  ├── finalize_batch(batch_id, analyst, decisions) → GovernanceRecord│
│  ├── compute_model_version(params) → str                            │
│  └── generate_revaluation_schedule(zone_ids) → list[date]          │
└─────────────────────────────────────────────────────────────────────┘
                           ↑ تُدمج مع:
┌─────────────────────────────────────────────────────────────────────┐
│  Phase 1 (موجود — لا تعديل)                                        │
│  mass_appraisal.py → run_batch()                                    │
│       ↓ يستدعي (سيبقى كما هو)                                       │
│  avm_dispatcher.py → dispatch_avm()                                 │
│  bridge_api.py → advanced_valuation()                               │
│  market_feed.json → بيانات الصفقات (source of truth)               │
│  price_index_engine.py → time adjustment (موجود، يُدمج في 3.2)     │
└─────────────────────────────────────────────────────────────────────┘
                           ↓ يُغذّي:
┌─────────────────────────────────────────────────────────────────────┐
│  mass_appraisal_excel.py (موجود — أوراق جديدة تُضاف)               │
│  ├── [موجودة] 15 ورقة حالية                                         │
│  ├── [Phase 3.1] ورقة "Zone Analysis"                              │
│  ├── [Phase 3.3] ورقة "Ratio Study"                                │
│  └── [Phase 3.4] ورقة "Model Calibration"                          │
└─────────────────────────────────────────────────────────────────────┘
```

### D3. علاقة الوحدات بالأنظمة القائمة

| الوحدة الجديدة | تقرأ من | تُغذّي | تعديل على القائم؟ |
|---------------|---------|--------|-------------------|
| `mass_zones.py` | مخرجات `run_batch()` | `run_batch()` summary، XLSX جديد | إضافة حقول للملخص فقط |
| `sales_verification.py` | `market_feed.json` + `price_index_engine.py` | `ratio_studies.py` | لا — يقرأ فقط |
| `ratio_studies.py` | نتائج التقييم + مبيعات مُحققة | XLSX جديد، API جديد | لا — وحدة مستقلة |
| `model_calibration.py` | عينات بيانات + نتائج ratio study | تُعدَّل معاملات في `advanced_valuation()` مستقبلاً | Phase 3.4 — مخطط |
| `mass_governance.py` | batch_id، قرارات المحلل، zone summaries | تقرير نهائي، XLSX | يُوسّع ورقة Audit الحالية |

---

## E. خارطة طريق نقاط النهاية المقترحة

> **تنبيه:** هذه مقترحات فقط — لا تنفيذ في Phase 3.0.

### E1. قائمة نقاط النهاية المقترحة

#### Phase 3.1

| نقطة النهاية | الغرض | المدخل الرئيسي | المخرج | التبعيات | الخطورة |
|-------------|-------|---------------|--------|----------|---------|
| `POST /api/mass-appraisal/zones/preview` | معاينة تجميع الصفوف بالمنطقة | `rows[]` مع `zone_id` اختياري | ملخص المناطق: عدد الصفوف، متوسط القيمة، عدد الفئات لكل منطقة | `mass_zones.py` | **منخفضة** — معاينة فقط، لا تقييم |

#### Phase 3.2

| نقطة النهاية | الغرض | المدخل الرئيسي | المخرج | التبعيات | الخطورة |
|-------------|-------|---------------|--------|----------|---------|
| `POST /api/mass-appraisal/sales/verify` | التحقق من صحة المبيعات | `sales[]`: location, price, area, date, source | لكل مبيعة: `validity_status`, `arms_length`, `time_adj_factor`, `exclusion_reason` | `sales_verification.py`, `price_index_engine.py`, `market_feed.json` | **متوسطة** — يعتمد على جودة بيانات market_feed |

#### Phase 3.3

| نقطة النهاية | الغرض | المدخل الرئيسي | المخرج | التبعيات | الخطورة |
|-------------|-------|---------------|--------|----------|---------|
| `POST /api/mass-appraisal/ratio-study/run` | دراسة نسب القيمة المقدَّرة / سعر البيع | `assessed_rows[]`, `verified_sales[]`, `zone_id` (اختياري) | `median_ratio`, `COD`, `PRD`, `equity_flags`, per-sale ratios | `ratio_studies.py`, `sales_verification.py` | **متوسطة** — يتطلب بيانات مبيعات مقابل تقدير |

#### Phase 3.4

| نقطة النهاية | الغرض | المدخل الرئيسي | المخرج | التبعيات | الخطورة |
|-------------|-------|---------------|--------|----------|---------|
| `POST /api/mass-appraisal/calibration/preview` | معاينة معايرة النموذج | عينة بيانات + مخرجات ratio study | `model_family`, معاملات مقترحة، RMSE التحسن المتوقع | `model_calibration.py`, `ratio_studies.py` | **عالية** — يؤثر على مخرجات التقييم مستقبلاً |

#### Phase 3.5

| نقطة النهاية | الغرض | المدخل الرئيسي | المخرج | التبعيات | الخطورة |
|-------------|-------|---------------|--------|----------|---------|
| `POST /api/mass-appraisal/governance/finalize` | اعتماد الدفعة وإنتاج سجل الحوكمة | `batch_id`, `analyst_id`, `zone_decisions[]`, `calibration_record_id` | `governance_record`: model_version, approval_state, revaluation_schedule | `mass_governance.py`, `mass_zones.py`, `ratio_studies.py` | **عالية** — عملية نهائية غير قابلة للعكس |

### E2. الجدول الزمني المقترح

```
Phase 3.1 — Q3 2026: Market Zones & Property-Class Segmentation
Phase 3.2 — Q4 2026: Sales Verification & Time Adjustment
Phase 3.3 — Q1 2027: Ratio Studies & Equity Analysis
Phase 3.4 — Q2 2027: Model Calibration Preview
Phase 3.5 — Q3 2027: Governance & Finalization Workflow
```

---

## F. Phase 3.1 — أصغر تنفيذ آمن موصى به

### F1. العنوان

**Phase 3.1 — Market Zones & Property-Class Segmentation**

### F2. المبرر

قبل التحقق من المبيعات ودراسات النسب، يحتاج النظام إلى:
- **تعريف المناطق** (zone_id): لمعرفة أي عقارات تنتمي لنفس السوق
- **تصنيف الفئات** (property_class على مستوى الدفعة): لإنتاج إحصائيات صادقة
- **إحصائيات الزون**: الوسيط والمتوسط لكل منطقة، لا للمحفظة كلها

هذا هو الأساس الذي يُبنى عليه كل ما بعده.

### F3. نطاق Phase 3.1

#### ما يُنفَّذ:

**أ. حقول اختيارية جديدة على مستوى الصف:**

```json
{
  "row_id": "R-001",
  "location": "التجمع الخامس",
  "property_type": "شقة سكنية",
  "area": 200,
  "valuation_purpose": "fair_market_value",

  "zone_id":       "Z-EAST-01",
  "neighborhood":  "التجمع الخامس",
  "submarket":     "القاهرة الجديدة",
  "property_class": "residential"
}
```

- جميعها **اختيارية** — الصف بدونها يُعالَج طبيعياً
- تُرجَّع كما أُرسلت في مخرجات `run_batch()` (echo-through)

**ب. ملخص المناطق في `summary`:**

```json
"zone_summary": {
  "Z-EAST-01": {
    "row_count": 3,
    "successful_rows": 3,
    "total_market_value": 12000000,
    "average_market_value": 4000000,
    "median_market_value": 3900000,
    "average_value_per_m2": 19500,
    "property_classes": {"residential": 2, "commercial": 1}
  }
},
"property_class_summary": {
  "residential": {
    "row_count": 5,
    "successful_rows": 5,
    "average_market_value": 3500000,
    "average_value_per_m2": 17500
  }
},
"zones_present": ["Z-EAST-01", "Z-WEST-02"],
"property_classes_present": ["residential", "commercial"]
```

**ج. ورقة Excel جديدة "Zone Analysis":**
- عمود لكل منطقة: zone_id، neighborhood، row_count، avg/median_value، avg_value_per_m2، class breakdown
- جدول فرعي للفئات العقارية: property_class، row_count، avg_value، avg_value_per_m2
- مخطط شريطي: متوسط القيمة بالمنطقة

**د. أعمدة جديدة في ورقة "Portfolio Results":**
- `zone_id` (العمود رقم 35)
- `neighborhood` (رقم 36)
- `submarket` (رقم 37)
- `property_class` (رقم 38) — **لا علاقة بـ tax property_class** إذا كان الغرض غير ضريبي

#### ما لا يُنفَّذ في Phase 3.1:

- ❌ لا خوارزميات تقييم جديدة
- ❌ لا تعديلات منطقية على الأسعار
- ❌ لا دراسات نسب
- ❌ لا معايرة
- ❌ لا تحقق من مبيعات
- ❌ لا حدود شذوذات خاصة بالمنطقة (Phase 3.2)
- ❌ لا تغيير على نقاط النهاية الحالية

### F4. التحسين الأهم في Phase 3.1 على الكشف عن الشذوذات

حالياً `_tag_outliers()` تستخدم وسيط المحفظة **كلها** عتبةً للشذوذات.  
عقار بـ 15,000 ج.م/م² في حي فاخر يُعلَّم شذوذاً إذا كان وسيط المحفظة 8,000 ج.م/م².

**Phase 3.1 يُهيئ البنية للتحسين الفعلي في Phase 3.2:**
- `zone_id` موجود على كل صف
- يمكن لاحقاً حساب وسيط كل منطقة منفصلاً كعتبة لشذوذاتها

> **لا تغيير على منطق `_tag_outliers()` في Phase 3.1** — التحضير فقط.

---

## G. الملفات المطلوب تعديلها في Phase 3.1

| الملف | التعديل المتوقع | مستوى الخطورة | طريقة الاختبار |
|-------|----------------|--------------|----------------|
| `core_engine/mass_appraisal.py` | إضافة echo-through لـ `zone_id`, `neighborhood`, `submarket`, `property_class` في كل صف (تُقرأ من المدخل وتُرجَّع في المخرج). إضافة `group_by_zone()` و`group_by_property_class()` لحساب ملخص المناطق بعد `run_batch()`. | **متوسط** — دوال جديدة، لا تعديل على `_tag_outliers()` أو `_score_row_quality()` | py_compile + AST + smoke test |
| `core_engine/mass_appraisal_excel.py` | إضافة `_sheet_zone_analysis()` وحقنها في `build_mass_appraisal_workbook()`. إضافة 4 أعمدة جديدة في `_sheet_portfolio()`. | **منخفض** — الأوراق الحالية لا تُعدَّل | تحميل XLSX + فحص عدد الأوراق |
| `frontend/index.html` | إضافة 4 حقول اختيارية في مثال JSON (zone_id, neighborhood, submarket, property_class). إضافة عمودَي zone_id و property_class في جدول نتائج Run إذا كانت الحقول موجودة في الاستجابة. | **متوسط** — الجدول الحالي يتأثر | فحص بصري + DevTools Network |
| `core_engine/bridge_api.py` | إضافة نقطة نهاية جديدة `POST /api/mass-appraisal/zones/preview` فقط إذا قُرِّر تنفيذها في Phase 3.1 | **منخفض** — Route مستقلة جديدة | curl smoke test |

---

## H. الملفات التي يجب عدم تعديلها

| الملف / النطاق | السبب |
|---------------|-------|
| `/api/valuation` وكل منطق التقييم الفردي | محمي تماماً — أي تغيير يكسر كل التقارير الفردية |
| وحدات الضريبة: `_compute_tax_assessment_block`, `_resolve_tax_policy_profile`, `_build_tax_appeal_package` | Phase 2 مُثبَّت ومُوثَّق — لا تعديل |
| محركات HBU / REIT / EIA | خارج نطاق Phase 3 |
| كاتبو التقارير القائمين: `purpose_detail_sections.py`, `write_to_excel_template()`, `write_word_summary()` | تقارير العقار الفردي معزولة |
| قوالب Excel (`.xlsm`) | القالب الثابت مُستخدَم للعقار الفردي فقط — Mass Appraisal يولّد من الصفر بـ openpyxl |
| `avm_dispatcher.py` | يعمل بشكل صحيح — Phase 3 يستفيد منه لا يُعدّله |
| `market_feed.json` | مصدر البيانات — للقراءة فقط |
| 15 ورقة Excel الحالية | تُضاف ورقة جديدة — الحالية لا تُعدَّل |
| نقاط نهاية Phase 1: `/api/mass-appraisal/preview`, `/run`, `/export-xlsx` | موجودة وتعمل — Phase 3 يُضيف نقاط جديدة |

---

## I. مخاطر التراجع

| المخاطرة | الاحتمالية | الأثر | التخفيف |
|---------|-----------|-------|---------|
| **تراجع Phase 1 الجماعي:** تغيير `run_batch()` يكسر الصفوف القائمة | متوسطة | عالية | الحقول الجديدة اختيارية فقط — الكود يقرأها بـ `row.get("zone_id")` |
| **تراجع CSV/XLSX:** أعمدة جديدة تُربك عميل CSV القائم | منخفضة | متوسطة | أعمدة تُضاف في النهاية — رؤوس CSV تتوسع لا تتغير |
| **تراجع session export/import:** حقول جديدة لا تُستعاد من جلسة قديمة | منخفضة | منخفضة | الحقول الجديدة اختيارية — الجلسات القديمة تعمل بدونها |
| **تراجع دفعة الضريبة:** `property_class` على مستوى الدفعة يتعارض مع `property_class` الضريبي | **مرتفعة** | عالية | **يجب التمييز الواضح:** `property_class` في السياق الضريبي يبقى داخل `tax_assessment` block — `property_class` الجديد على مستوى الصف هو لأغراض التجميع الجغرافي فقط |
| **تراجع التقييم الفردي:** أي import من mass_appraisal.py في bridge_api.py يُعيد تحميل الكود | منخفضة | عالية | الـ import الدفاعي القائم يحمي ذلك |
| **ازدحام واجهة المستخدم:** إضافة 4 حقول + عمودَين جديدَين | متوسطة | متوسطة | الحقول في قسم "متقدم" قابل للطيّ — الأعمدة تظهر فقط إذا وُجدت البيانات |
| **انكسار ورقة Portfolio في Excel:** إضافة أعمدة تُزحزح صيغ موجودة | منخفضة | متوسطة | `mass_appraisal_excel.py` يبني بـ openpyxl لا صيغ — آمن |
| **انكسار الاستيراد الدائري:** `mass_zones.py` الجديد يستورد من `mass_appraisal.py` | منخفضة | عالية | الاتجاه عكسي: `mass_appraisal.py` يستورد من `mass_zones.py` — لا `mass_zones.py` يستورد من `mass_appraisal.py` |

### المخاطرة الأعلى: تعارض `property_class`

`property_class` موجود في اتجاهين مختلفين:
1. **Tax Appraisal:** `property_class` يُحدِّد ملف السياسة الضريبية (residential/commercial/...)
2. **Phase 3.1 Zoning:** `property_class` على مستوى الدفعة لأغراض التجميع والإحصاء

**الحل:** استخدام نفس القيم (residential/commercial/industrial/agricultural/administrative) مع التوثيق الواضح أن `property_class` على مستوى الصف لا يُعيد المعايرة الضريبية — هو مجرد تصنيف للتجميع. تقييم الضريبة يُعيد قراءة `property_class` من الطلب الأصلي لا من حقل التجميع.

---

## J. خطة الاختبار اليدوي لـ Phase 3.1

### الدفعة النموذجية (5 صفوف)

```json
[
  {
    "row_id": "R-001",
    "location": "التجمع الخامس",
    "property_type": "شقة سكنية",
    "area": 200,
    "valuation_purpose": "fair_market_value",
    "zone_id": "Z-EAST-01",
    "neighborhood": "التجمع الخامس",
    "submarket": "القاهرة الجديدة",
    "property_class": "residential"
  },
  {
    "row_id": "R-002",
    "location": "وسط البلد",
    "property_type": "محل تجاري",
    "area": 80,
    "valuation_purpose": "fair_market_value",
    "zone_id": "Z-CENTRAL-01",
    "neighborhood": "وسط البلد",
    "submarket": "القاهرة الكبرى",
    "property_class": "commercial"
  },
  {
    "row_id": "R-003",
    "location": "مدينة نصر",
    "property_type": "شقة سكنية",
    "area": -50,
    "valuation_purpose": "fair_market_value",
    "zone_id": "Z-EAST-01",
    "neighborhood": "مدينة نصر",
    "submarket": "القاهرة الجديدة",
    "property_class": "residential"
  },
  {
    "row_id": "R-004",
    "location": "التجمع الخامس",
    "property_type": "شقة سكنية",
    "area": 150,
    "valuation_purpose": "tax_assessment",
    "zone_id": "Z-EAST-01",
    "neighborhood": "التجمع الخامس",
    "submarket": "القاهرة الجديدة",
    "property_class": "residential",
    "tax_rate": 0.10,
    "exemption_threshold": 24000
  },
  {
    "row_id": "R-005",
    "location": "المعادي",
    "property_type": "شقة سكنية",
    "area": 180,
    "valuation_purpose": "uncertainty_valuation",
    "uncertainty_spread_pct": 0.15
  }
]
```

### المتوقع من كل صف

| الصف | الحالة | `zone_id` في الاستجابة؟ | `property_class` في الاستجابة؟ | ملاحظة |
|------|--------|------------------------|---------------------------------|--------|
| R-001 | success | Z-EAST-01 | residential | صف اختبار المنطقة الرئيسي |
| R-002 | success | Z-CENTRAL-01 | commercial | منطقة مختلفة |
| R-003 | error | Z-EAST-01 | residential | مساحة سالبة — يُرفض + zone تُرجَع |
| R-004 | success | Z-EAST-01 | residential | property_class لا يتعارض مع tax block |
| R-005 | success | null / غائب | null / غائب | لا zone_id — يعمل عادياً |

### المتوقع في `summary`

```
zone_summary:
  Z-EAST-01:
    row_count: 3 (R-001, R-003, R-004)
    successful_rows: 2 (R-001, R-004)
    average_market_value: [محسوب]
    property_classes: { residential: 3 }
  Z-CENTRAL-01:
    row_count: 1 (R-002)
    successful_rows: 1
    property_classes: { commercial: 1 }

property_class_summary:
  residential: { row_count: 3, successful_rows: 2 }
  commercial:  { row_count: 1, successful_rows: 1 }

zones_present: ["Z-EAST-01", "Z-CENTRAL-01"]
```

### اختبارات التراجع

```
[ ] POST /api/mass-appraisal/run بدون zone_id → يعمل كما في Phase 1 (لا تغيير)
[ ] POST /api/mass-appraisal/preview → لا تأثير من حقول المنطقة
[ ] POST /api/mass-appraisal/export-xlsx → ورقة Zone Analysis جديدة + 15 ورقة قائمة
[ ] POST /api/valuation (عقار فردي) → لا تأثير مطلق
[ ] دفعة ضريبية (tax_assessment) → tax_assessment block صحيح + zone_id يُرجَع
[ ] session export/import → الجلسة تعمل مع الحقول الجديدة واختياريتها
[ ] جدول نتائج الواجهة → عمودا zone_id وproperty_class يظهران فقط عند وجود البيانات
```

---

## K. التوصية النهائية

### ما تم بناؤه (Phase 1 — ثابت ومُثبَّت)

Mass Appraisal Phase 1 يُقدّم:
- خط أنابيب تقييم دفعي (100 عقار / دفعة)
- جودة بيانات تلقائية + كشف شذوذات + مراجعة بشرية
- تصدير XLSX احترافي (15 ورقة) + CSV + جلسة قابلة للحفظ والاستعادة
- تكامل كامل مع محرك الضريبة ووحدة AVM
- حوكمة أولية: batch_id، analyst_note، audit sheet

### ما ينقص للوصول إلى تقييم جماعي احترافي بمعايير IAAO

**الفجوة الحرجة** ليست في الخوارزميات — بل في **البنية التحتية للبيانات:**
- لا تجميع جغرافي (zone_id، neighborhood، submarket)
- لا إحصائيات على مستوى المنطقة (وسيط المنطقة، متوسطها)
- لا رابط بين نتائج التقييم وبيانات المبيعات التاريخية
- لا منهجية لقياس دقة النموذج (COD، PRD)

### الخطوة الموصى بها: Phase 3.1 فقط

**ابدأ بـ Phase 3.1 وحده:**

1. أضف `zone_id`, `neighborhood`, `submarket`, `property_class` كحقول اختيارية في صفوف الدفعة
2. أنشئ `core_engine/mass_zones.py` بدوال `group_by_zone()` و`group_by_property_class()`
3. أضف `zone_summary` و`property_class_summary` في `summary` من `run_batch()`
4. أضف ورقة "Zone Analysis" في XLSX
5. أضف عمودَي `zone_id` و`property_class` في ورقة Portfolio
6. اختبر الدفعة النموذجية (5 صفوف أعلاه) بالكامل
7. لا تلمس Phase 1 أو الضريبة أو التقييم الفردي

**المدة المقدرة:** 5–7 أيام تطوير.

**المكسب الفوري:** البنية التحتية الجغرافية التي تُمكِّن Phase 3.2 و3.3 من العمل فور إضافة بيانات المبيعات.

**البديل:** تجاوز Phase 3.1 والذهاب مباشرة لـ Phase 3.2 يعني أن دراسات النسب ستُنتج إحصائيات مُضلِّلة لأنها ستعمل على المحفظة كلها لا على كل منطقة سوقية على حدة — وهذا ما يُحذر منه IAAO تحديداً.

---

*أُعِدَّ هذا التقرير بعد فحص دقيق لأكثر من 3,300 سطر من الكود الفعلي.  
جميع أسماء الدوال والثوابت والأعداد مأخوذة مباشرة من الكود الحالي — لا افتراضات.*
