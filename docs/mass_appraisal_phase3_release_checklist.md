# قائمة إصدار التقييم الجماعي المتقدم — Phase 3 Release Checklist
**الإصدار:** Phase 3.10 — Release Stabilization  
**التاريخ:** 2026-05-02  
**الحالة:** RELEASE FREEZE  
**المراجع:** م. هشام المهدي  

---

## A. بناء البيئة (Build)

- [ ] `docker compose -f deploy/docker-compose.yml up -d --build flask` ينتهي بدون أخطاء
- [ ] `Invoke-RestMethod http://127.0.0.1:5000/api/advisor/health` يُرجع استجابة صحيحة
- [ ] جميع فحوصات py_compile تمر (9 ملفات — انظر test_matrix.md §7)
- [ ] فحص AST لـ `bridge_api.py` يُرجع `AST OK`

---

## B. التقييم الجماعي الأساسي (Core Mass Appraisal)

- [ ] **معاينة:** `POST /api/mass-appraisal/preview` → HTTP 200 + `status: "success"`
- [ ] **تشغيل:** `POST /api/mass-appraisal/run` → HTTP 200 + `market_value` لكل صف نجاح
- [ ] ملخص `zone_summary` موجود عند وجود `zone_id`
- [ ] ملخص `property_class_summary` موجود عند وجود `property_class`
- [ ] `data_quality_level` و`outlier_level` مُحسوبان لكل صف
- [ ] صفوف بدون `zone_id` تعمل بشكل طبيعي

---

## C. التحقق من المبيعات (Sales Verification — Phase 3.2)

- [ ] `POST /api/mass-appraisal/sales/verify` → HTTP 200
- [ ] `verification_summary.usable_count` ≥ 0
- [ ] صفقات ذات `verification_status: "excluded"` تُستبعد من دراسة النسب
- [ ] حد 1000 سجل مُطبَّق

---

## D. تعديل الوقت (Time Adjustment — Phase 3.4)

- [ ] `POST /api/mass-appraisal/sales/time-adjust` → HTTP 200
- [ ] `adjusted_sale_price` محسوب صحيحاً
- [ ] `time_adjustment_factor = 1.0` لتاريخ البيع = تاريخ التقييم

---

## E. عوامل التعديل البيعي (Sales Adjustment — Phase 3.5)

- [ ] `POST /api/mass-appraisal/sales/adjust` → HTTP 200
- [ ] `final_adjusted_sale_price` محسوب صحيحاً
- [ ] جميع العوامل = 1.0 → لا تعديل
- [ ] تحذير عامل مركّب خارج [0.60، 1.60] صادر

---

## F. دراسة النسب (Ratio Study — Phase 3.3)

- [ ] `POST /api/mass-appraisal/ratio-study/run` → HTTP 200
- [ ] `median_ratio` محسوب
- [ ] `cod` و`prd` محسوبان
- [ ] `zone_metrics` موجود عند وجود بيانات منطقة
- [ ] تحذير عينة صغيرة صادر عند الحاجة
- [ ] أولوية `sale_price_used`: `final_adjusted` → `adjusted` → `raw` مُطبَّقة

---

## G. معاينة المعايرة (Calibration Preview — Phase 3.6)

- [ ] `POST /api/mass-appraisal/calibration/preview` → HTTP 200
- [ ] `suggested_factor` موجود في `portfolio_calibration`
- [ ] `recommendation` ∈ {`no_action`, `minor_adjustment`, `moderate_adjustment`, `major_review`}
- [ ] `calibration_note` العربية موجودة
- [ ] **لا تغيير تلقائي في أي `market_value`**

---

## H. بيئة اختبار المعايرة (Calibration Sandbox — Phase 3.7)

- [ ] `POST /api/mass-appraisal/calibration/sandbox` → HTTP 200
- [ ] `original_market_value` = `market_value` الأصلي
- [ ] `sandbox_calibrated_value` ≠ `original_market_value` عند عامل ≠ 1.0
- [ ] صفوف `status: "error"` لها `sandbox_calibrated_value: null`
- [ ] العامل مُقيَّد بين `min_factor=0.75` و`max_factor=1.35` افتراضياً
- [ ] **`market_value` الأصلي في `window.latestMassAppraisalRunResult` لم يتغير**

---

## I. الحوكمة (Governance — Phase 3.8)

- [ ] لوحة الحوكمة تظهر تلقائياً بعد نجاح التشغيل
- [ ] حفظ القرار يُحدِّث `governance_status` و`last_updated`
- [ ] الحالة `approved` تُثبِّت `approval_timestamp`
- [ ] الحالة غير `approved` تُزيل `approval_timestamp`
- [ ] `governance_history` يُضاف إدخال في كل حفظ
- [ ] `governance_id` مُولَّد بصيغة `GOV-YYYYMMDD-HHMMSS-XXXX`
- [ ] بيانات الحوكمة مُدرَجة في CSV (عمود `GOVERNANCE_FIELD`)
- [ ] بيانات الحوكمة مُدرَجة في XLSX (ورقة "Governance Approval")

---

## J. إصدار النموذج (Model Cycle — Phase 3.9)

- [ ] لوحة Model Cycle تظهر تلقائياً بعد نجاح التشغيل
- [ ] القيم الافتراضية مُعبَّأة: `CYCLE-YYYY-GENERAL`، `MA-MODEL-v1.0`، `draft`
- [ ] حفظ البيانات يُحدِّث `last_updated` ويُصدر تأكيداً
- [ ] `model_status` ∈ {`draft`, `under_review`, `approved`, `retired`, `superseded`}
- [ ] بيانات دورة التقييم مُدرَجة في CSV (عمود `MODEL_CYCLE_FIELD`)
- [ ] بيانات دورة التقييم مُدرَجة في XLSX (ورقة "Model & Revaluation Cycle")

---

## K. التصدير والاستيراد (Export / Import)

- [ ] CSV يُنزَّل ويُفتح في Excel بترميز UTF-8 (BOM موجود)
- [ ] CSV يشمل: أعمدة البيانات + ملخص المحفظة المراجَعة + GOVERNANCE_FIELD + MODEL_CYCLE_FIELD + AUDIT_FIELD
- [ ] XLSX يُنزَّل ويُفتح بدون أخطاء
- [ ] XLSX يشمل ورقة "Model & Revaluation Cycle" إذا كانت cycle_id موجودة
- [ ] XLSX يشمل ورقة "Governance Approval" إذا كانت governance_id موجودة
- [ ] تصدير الجلسة JSON يشمل `governance` و`model_cycle`
- [ ] استيراد الجلسة يُعيد بيانات الحوكمة وبيانات النموذج ويُعيد الرسم

---

## L. اختبارات الانحدار (Regression)

- [ ] `/api/valuation` لم يُعدَّل — يعمل بشكل طبيعي للتقييم الفردي
- [ ] Tax Appraisal يعمل بشكل طبيعي
- [ ] `advanced_valuation()` لم يُعدَّل
- [ ] AVM engine لم يُعدَّل
- [ ] لا معايرة تلقائية تُطبَّق على `market_value`
- [ ] الفتح من `file://` يُظهر البانر التحذيري الأحمر

---

## M. التوثيق (Documentation)

- [ ] `docs/mass_appraisal_phase3_user_guide.md` مكتمل ومراجَع
- [ ] `docs/mass_appraisal_phase3_technical_reference.md` مكتمل ومراجَع
- [ ] `docs/mass_appraisal_phase3_test_matrix.md` مكتمل ومراجَع
- [ ] `docs/mass_appraisal_phase3_release_checklist.md` هذا الملف — مكتمل
- [ ] `docs/mass_appraisal_phase3_handover_readme.md` مكتمل ومراجَع

---

## N. القيود المعروفة — مقبولة في هذا الإصدار

- [ ] **لا استمرارية في قاعدة البيانات** — الجلسة مؤقتة (مقبول)
- [ ] **لا معايرة تلقائية للإنتاج** — Sandbox فقط (مقبول)
- [ ] **لا إيداع تنظيمي رسمي** — الحوكمة للتتبع الداخلي (مقبول)
- [ ] **لا تطابق جغرافي بالإحداثيات** — التطابق نصي (مقبول)
- [ ] **لا تدريب نموذج آلي** — النموذج ثابت (مقبول)

---

## O. القرار النهائي

```
[ ] تمت مراجعة جميع البنود السابقة
[ ] القيود المعروفة مقبولة
[ ] مُستعد للانتقال إلى Phase 4 — Heritage / Historical Engine
```

**المراجع:** ____________________________  
**التاريخ:** ____________________________  
**التوقيع:** ____________________________  
