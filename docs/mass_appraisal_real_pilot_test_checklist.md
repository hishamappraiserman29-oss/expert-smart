# قائمة اختبار التشغيل التجريبي الحقيقي — Mass Appraisal Pilot

> **الإصدار:** Phase 3.14 | **التاريخ:** 2026-05-06
> **الغرض:** التحقق من جاهزية النظام قبل إنشاء وسم `v3.14-pilot-ready`

---

## 1. الهدف من الاختبار

هذه القائمة مخصصة للتحقق من سير العمل الكامل لنظام التقييم الجماعي باستخدام بيانات Excel حقيقية أو شبه حقيقية.

- لا تُعدِّل أي صيغة أو إعداد في النظام.
- يجب اجتيازها بالكامل **قبل** إنشاء وسم `v3.14-pilot-ready`.
- في حالة وجود blockers، لا يُنشأ الوسم حتى تُحلَّ.

---

## 2. معلومات الاختبار

## 2. معلومات الاختبار

| الحقل | القيمة |
|---|---|
| تاريخ الاختبار | 2026-05-05 |
| المختبر | م. هشام المهدي |
| اسم مجموعة البيانات | Mass Appraisal Pilot Dataset 01 |
| إصدار مجموعة البيانات | v1.0 |
| Git Commit | 4ad6e1c |
| Git Tag | v3.14-pilot-ready |
| المتصفح | Microsoft Edge |
| البيئة | Local Docker / http://127.0.0.1:5000 |
| عدد العقارات | |
| عدد المبيعات | |
| نتيجة الاختبار | Pending |
| ملاحظات عامة | أول اختبار تشغيل تجريبي ببيانات حقيقية أو شبه حقيقية |

## 3. قائمة تحقق بيئة ما قبل الاختبار

### ملاحظات عامة

- [x] Docker Desktop يعمل.
- [x] حاوية Flask تعمل وحالتها Healthy أو Running.
- [x] حاوية Qdrant تعمل إن كانت مطلوبة.
- [x] حاوية Ollama تعمل وحالتها Healthy إن كانت مطلوبة.
- [x] Health endpoint يُرجع `status: ok`.
- [x] الواجهة تفتح على `http://127.0.0.1:5000/`.
- [x] تم عمل Hard Refresh في المتصفح باستخدام `Ctrl + Shift + R`.
- [x] Console المتصفح لا يحتوي أخطاء Blocking.
- [x] تم تسجيل Git Commit الحالي في جدول معلومات الاختبار.
- [x] وسم الرجوع `v3.13-stable` معروف وموثق.

### أوامر التحقق

```powershell
git log --oneline --decorate -5

docker compose -f deploy/docker-compose.yml ps

curl.exe -s http://127.0.0.1:5000/api/advisor/health

### أوامر التحقق

```powershell
git log --oneline --decorate -5

docker compose -f deploy/docker-compose.yml ps

curl.exe -s http://127.0.0.1:5000/api/advisor/health

### أوامر التحقق

```powershell
git log --oneline --decorate -5
docker compose -f deploy/docker-compose.yml ps
curl.exe -s http://127.0.0.1:5000/api/advisor/health
```

**المخرج المتوقع للـ health:**
```json
{"status": "ok", "rag_ready": true}
```

---

## 4. قائمة تحقق ملف Excel التجريبي

### الهدف

التأكد أن ملف Excel المستخدم في التجربة صالح للرفع في قسم **استيراد بيانات من Excel**، وأنه لم يتم تغيير بنية القالب.

### قائمة التحقق

- [x] ملف Excel بصيغة `.xlsx`.
- [x] أسماء الشيتات لم يتم تغييرها.
- [x] أسماء الأعمدة لم يتم تغييرها.
- [x] شيت `Properties` يحتوي بيانات العقارات.
- [x] شيت `Sales` يحتوي بيانات المبيعات.
- [x] Upload succeeds.
- [x] errors_count = 0.

### نتيجة هذا الاختبار

| Metric | Value |
|---|---|
| properties_count | اكتب الرقم الظاهر |
| sales_count | اكتب الرقم الظاهر |
| errors_count | 0 |
| warnings_count | اكتب الرقم الظاهر |
---

## 5. قائمة تحقق جودة بيانات العقارات (Properties)

```
□ row_id موجود في كل صف
□ row_id قيم فريدة (لا تكرار)
□ location موجود في كل صف
□ property_type موجود في كل صف
□ area رقمية وأكبر من صفر
□ zone_id مُعبَّأ حيثما أمكن
□ property_class مُعبَّأ حيثما أمكن
□ condition مُعبَّأ حيثما يُفيد
□ valuation_purpose مُعبَّأ حيثما يُفيد
□ لا يوجد تباين في تهجئة المواقع (مثل: "الرياض" vs "رياض")
□ لا يوجد تباين في تهجئة أنواع العقارات
```

---

## 6. قائمة تحقق جودة بيانات المبيعات (Sales)

```
□ sale_id موجود في كل صف
□ sale_id قيم فريدة (لا تكرار)
□ location موجود في كل صف
□ property_type موجود في كل صف
□ area رقمية وأكبر من صفر
□ sale_price رقمية وأكبر من صفر
□ sale_date بصيغة YYYY-MM-DD
□ verified = TRUE للمبيعات الصالحة للدراسة
□ arms_length = TRUE للمبيعات الصالحة
□ buyer_seller_related = FALSE للمبيعات الصالحة
□ usable_for_ratio_study = TRUE فقط للمبيعات الموثوقة
□ zone_id مُعبَّأ حيثما أمكن
□ property_class مُعبَّأ حيثما أمكن
□ subject_id يطابق row_id في Properties حيثما أمكن
```

---

## 7. قائمة تحقق جاهزية المطابقة (Matching Readiness)

```
□ على الأقل 10–20 مبيعة تتطابق مع العقارات بـ zone_id/property_class
□ على الأقل 5–10 مبيعات تتطابق بـ subject_id (إن وُجدت)
□ لا توجد قيم location كبيرة موجودة في المبيعات فقط دون العقارات
□ لا توجد قيم property_type موجودة في المبيعات فقط دون العقارات
□ تحذيرات matching_readiness تمت مراجعتها وفهمها
□ تحذيرات normalization_readiness تمت مراجعتها وفهمها
```

---

## 8. اختبار رفع Excel والتحقق من الصحة

### الخطوات

1. افتح تبويب **التصدير والجلسة**.
2. انقر **رفع قالب Excel المعبأ**.
3. اختر ملف Excel التجريبي.
4. راجع لوحة التحقق من الصحة.

### معايير الاجتياز

```
□ الرفع نجح بلا خطأ
□ errors_count = 0 (لا أخطاء blocking)
□ warnings_count تمت مراجعته وفهمه
□ لوحة Import_Validation مقروءة ومفهومة
□ لا يظهر "Failed to fetch"
□ لا توجد أخطاء في Console
```

### تسجيل النتائج

| المقياس | القيمة |
|---|---|
| properties_count | |
| sales_count | |
| errors_count | |
| warnings_count | |
| matched_count | |
| unmatched_properties | |
| unmatched_sales | |

---

## 9. Properties Fill and Mass Appraisal Test

- [x] Properties fill works.
- [x] Preview works.
- [x] Run works.
- [x] Summary cards update.
- [x] Executive summary updates.
- [x] No "القائمة فارغة".
- [x] No JSON parse error.

### معايير الاجتياز

```
□ تعبئة العقارات تعمل
□ المعاينة (Preview) تعمل وتُرجع نتائج
□ التشغيل الجماعي (Run) يكتمل بلا خطأ
□ بطاقات الملخص تتحدث
□ Executive Summary يتحدث
□ لا تظهر رسالة "القائمة فارغة"
□ لا يظهر خطأ JSON parse
```

### تسجيل النتائج

| Metric | Value |
|---|---|
| n_units | 3 |
| total_portfolio_value | 29,479,500 ج.م |
| avg_ppm | 81,888 |
| method | avm |

---

## 10. Sales Verification Test

### حالة الاختبار

- [x] Sales fill works.
- [x] Sales Verification works.
- [x] No "يرجى إدخال بيانات المبيعات".
- [x] Usable/rejected sales counts are reasonable.

### تسجيل النتائج

| Metric | Value |
|---|---|
| total sales | 3 |
| usable sales | 3 |
| rejected sales | 0 |
| warnings | 0 |

### معايير الاجتياز

- [x] تعبئة المبيعات تعمل.
- [x] Sales Verification يعمل وتظهر النتائج.
- [x] لا تظهر رسالة "يرجى إدخال بيانات المبيعات".
- [x] أعداد المبيعات الصالحة والمرفوضة معقولة ومبررة.

---

## 11. Time Adjustment Test

### خطوات الاختبار

1. استخدم نتيجة التحقق من المبيعات `Sales Verification`.
2. أدخل تاريخ التقييم.
3. اضغط زر `ضبط الوقت`.

### حالة الاختبار

- [x] Time adjustment runs.
- [x] adjusted_sale_price appears.
- [x] time_adjustment_factor appears.
- [x] No empty list errors.
- [x] No console errors.

### تسجيل النتائج

| Metric | Value |
|---|---|
| valuation_date | 2026-05-03 |
| monthly_growth_rate | 0.0075 |
| adjusted records | 3 |
| sample adjusted_sale_price | 8,220,771.68 |
| sample months_to_valuation_date | 4 |
| notes | تم التعديل الزمني بنجاح على بيانات المبيعات. |

### معايير الاجتياز

- [x] التعديل الزمني يعمل بدون أخطاء.
- [x] تظهر قيمة `adjusted_sale_price`.
- [x] تظهر قيمة `time_adjustment_factor`.
- [x] لا تظهر رسالة `sale_records must be a non-empty list`.
---

## 12. Sales Adjustments Test

### خطوات الاختبار

1. استخدم نتيجة التعديل الزمني `Time Adjustment`.
2. أدخل عوامل التعديل البيعي.
3. اضغط زر `تطبيق عوامل التعديل`.

### حالة الاختبار

- [x] Sales adjustments run.
- [x] final_adjusted_price appears.
- [x] No empty list errors.
- [x] No console errors.

### تسجيل النتائج

| Metric | Value |
|---|---|
| adjusted records | 3 |
| sample final_adjusted_sale_price | 8,220,771.68 |
| final_adjustment_factor | 1 |
| adjustment_method | no_adjustment |
| notes | تم تطبيق عوامل التعديل بنجاح. لم يتم تغيير السعر لأن عوامل التعديل = 1.0. |

### معايير الاجتياز

- [x] تعديلات المبيعات تعمل بدون أخطاء.
- [x] تظهر قيمة `final_adjusted_sale_price`.
- [x] لا تظهر رسالة `sale_records must be a non-empty list`.
- [x] النتيجة منطقية؛ السعر النهائي يساوي السعر المعدل زمنيًا عند استخدام عوامل تعديل = 1.0.

---

## 13. Ratio Study Test

### خطوات الاختبار

1. افتح تبويب `دراسة النسب والمعايرة`.
2. استخدم آخر نتيجة تشغيل للتقييم الجماعي.
3. استخدم آخر نتيجة تعديلات المبيعات.
4. اضغط زر `إجراء دراسة النسب`.

### حالة الاختبار

- [x] matched_pair_count > 0.
- [x] Median Ratio appears.
- [x] COD appears.
- [x] PRD appears.
- [x] Metrics are not all zero unless justified.

### تسجيل النتائج

| Metric | Value |
|---|---|
| matched_pair_count | 3 |
| median_ratio | 1.4869 |
| COD | 24.07% |
| PRD | 1.0754 |
| matching method | subject_id / zone_id + property_class |

### معايير الاجتياز

- [x] دراسة النسب تعمل بدون أخطاء.
- [x] تم إنشاء أزواج مطابقة.
- [x] تظهر قيمة `Median Ratio`.
- [x] تظهر قيمة `COD`.
- [x] تظهر قيمة `PRD`.

---

## 14. Calibration Preview Test

### خطوات الاختبار

1. استخدم آخر نتيجة `Ratio Study`.
2. اضغط زر `معاينة المعايرة`.

### حالة الاختبار

- [x] calibration factor appears.
- [x] recommendation appears.
- [x] no missing ratio_study error.
- [x] factor is meaningful or justified.

### تسجيل النتائج

| Metric | Value |
|---|---|
| suggested_factor | 0.6725 |
| recommendation | major_review |
| matched pairs | 3 |
| median_ratio | 1.4869 |
| COD | 24.07% |
| source | ratio_study |

### معايير الاجتياز

- [x] معاينة المعايرة تعمل بدون أخطاء.
- [x] يظهر عامل المعايرة المقترح.
- [x] تظهر التوصية.
- [x] لا تظهر رسالة `missing ratio_study`.
- [x] النتيجة منطقية؛ `major_review` بسبب ارتفاع Median Ratio.

---

## 15. Calibration Sandbox Test

### خطوات الاختبار

1. استخدم نتيجة `Calibration Preview`.
2. أدخل عامل معايرة للاختبار داخل Sandbox.
3. اضغط زر `اختبار المعايرة (Sandbox)`.

### حالة الاختبار

- [x] Sandbox runs.
- [x] calibrated_rows > 0 when applicable.
- [x] original values are not modified.
- [x] no portfolio_calibration error.

### تسجيل النتائج

| Metric | Value |
|---|---|
| applied factor | 1.0500 |
| original total | 29,479,500 |
| sandbox total | 30,953,000 |
| calibrated rows | 3 |
| unchanged rows | 0 |
| total change | +5.00% |
| notes | تم اختبار عامل يدوي 1.05 للمراجعة فقط؛ لا يتم تطبيقه تلقائيًا على القيم الأصلية. |

### معايير الاجتياز

- [x] اختبار Sandbox يعمل بدون أخطاء.
- [x] تظهر قيم Sandbox.
- [x] عدد الصفوف المعايرة = 3.
- [x] القيم الأصلية لا يتم تعديلها تلقائيًا.
- [x] لا تظهر رسالة `portfolio_calibration`.

---

## 16. Governance Test

### خطوات الاختبار

1. افتح تبويب `التصدير والجلسة`.
2. اضغط زر `تعبئة بيانات الحوكمة`.
3. تأكد أن تبويب `الحوكمة ودورة النموذج` تم فتحه.
4. راجع بيانات الحوكمة.
5. اضغط زر `حفظ قرار الحوكمة`.

### حالة الاختبار

- [x] Reviewer filled.
- [x] Governance status filled.
- [x] Notes filled.
- [x] Save works.
- [x] Governance ID appears.

### تسجيل النتائج

| Metric | Value |
|---|---|
| governance_status | pending |
| reviewer | م هشام المهدى |
| notes | تم إنشاء القالب للاختبار |
| governance_id | GOV-20260506-6E1S |
| last_updated | 2026-05-06T17:14:09.742Z |

### معايير الاجتياز

- [x] تعبئة بيانات الحوكمة تعمل.
- [x] حالة الحوكمة تظهر.
- [x] اسم المراجع يظهر.
- [x] ملاحظات القرار تظهر.
- [x] حفظ قرار الحوكمة يعمل.
- [x] يظهر Governance ID بعد الحفظ.
```

---

## 17. Model Cycle Test

### خطوات الاختبار

1. افتح تبويب `التصدير والجلسة`.
2. اضغط زر `تعبئة بيانات دورة النموذج`.
3. تأكد أن تبويب `الحوكمة ودورة النموذج` تم فتحه.
4. راجع بيانات دورة النموذج.
5. اضغط زر `حفظ بيانات دورة التقييم`.

### حالة الاختبار

- [x] model-version-id filled.
- [x] model-status-select filled.
- [x] model-cycle-id filled.
- [x] start date filled correctly.
- [x] end date filled correctly.
- [x] Date year is correct, not 0026.
- [x] Save works.

### تسجيل النتائج

| Metric | Value |
|---|---|
| model_version | MA-MODEL-v1.0 |
| model_status | draft |
| cycle_id | CYCLE-2025-GENERAL |
| cycle_start_date | 2026-06-03 |
| cycle_end_date | 2026-05-06 |
| last_updated | 2026-05-06T17:18:29.969Z |
| notes | الحفظ نجح، والسنة ظهرت صحيحة. توجد ملاحظة منطقية: تاريخ البداية بعد تاريخ النهاية، ويجب تصحيحها في بيانات Excel قبل الاعتماد النهائي. |

### معايير الاجتياز

- [x] تعبئة بيانات دورة النموذج تعمل.
- [x] إصدار النموذج يظهر.
- [x] حالة النموذج تظهر.
- [x] معرّف الدورة يظهر.
- [x] الحفظ يعمل.
- [x] السنة تظهر بصيغة صحيحة وليست `0026`.
```

> **تنبيه:** تحقق من أن السنة في حقول التاريخ تظهر بأربعة أرقام صحيحة (مثلاً 2025 وليس 0025 أو 0026). هذا ناتج عن قراءة Excel للتواريخ برقمين أحياناً.

---

## 18. XLSX Export Test

### حالة الاختبار

- [x] زر تصدير Excel ظاهر.
- [x] تم تشغيل التقييم الجماعي قبل التصدير.
- [x] Workbook downloads.
- [x] Workbook opens.
- [x] Export_Metadata sheet exists.
- [x] Import_Validation sheet exists.
- [x] Readiness sheet exists.
- [x] Sales_Verification sheet exists.
- [x] Time_Adjustment sheet exists.
- [x] Sales_Adjustments sheet exists.

### نتيجة الاختبار

| البند | النتيجة |
|---|---|
| export-xlsx HTTP status | 200 |
| النتيجة | Pass |
| ملاحظات | تم إصلاح خطأ MergedCell، وملف Excel تم تحميله وفتحه بنجاح. |

### قرار

- [x] XLSX Export جاهز للاستخدام في الـ pilot.




```

---

## 19. Session Export / Import Test

### حالة الاختبار

- [x] Session exports.
- [x] Session imports.
- [x] State is restored.
- [x] This is clearly separate from Excel import.

### تسجيل النتائج

| Metric | Value |
|---|---|
| session_export | Pass |
| session_import | Pass |
| restored_state | نعم |
| notes | تم تصدير واستيراد الجلسة بنجاح، وتم استرجاع حالة العمل بعد تحديث الصفحة. |

### معايير الاجتياز

- [x] يتم تنزيل ملف الجلسة.
- [x] يتم استيراد ملف الجلسة بنجاح.
- [x] حالة العمل يتم استرجاعها.
- [x] لا يحدث خلط بين استيراد الجلسة ورفع Excel.
```

---

## 20. Final Browser Console Check

### المسموح

- [x] `favicon.ico 404` إن ظهر.
- [x] Browser tracking prevention warnings إن ظهرت.

### غير مسموح

- [x] لا يوجد `Failed to fetch`.
- [x] لا يوجد `Uncaught TypeError`.
- [x] لا يوجد `Cannot read properties of null`.
- [x] لا يوجد `JSON.parse error`.
- [x] لا يوجد `NaN` في الواجهة.
- [x] لا يوجد `[object Object]` في الواجهة.

### نتيجة الفحص

| البند | النتيجة |
|---|---|
| Console status | Pass |
| Blocking errors | None |
| Allowed warnings | `favicon.ico 404` و `Tracking Prevention` فقط |
| notes | لا توجد أخطاء blocking أثناء الاختبار النهائي. التحذيرات الظاهرة غير مؤثرة على التشغيل. |
```

---

## 21. Issue Log

### سجل المشكلات أثناء الاختبار

| # | Area | Severity | Description | Screenshot/Log | Owner | Status |
|---|---|---|---|---|---|---|
| 1 | XLSX Export | High | فشل تصدير Excel أول مرة بسبب خطأ backend: `MergedCell object has no attribute column_letter` داخل `Calibration Sandbox` sheet. | Flask logs / HTTP 500 | Dev | Resolved |
| 2 | Browser Console | Low | ظهور `favicon.ico 404`. لا يؤثر على التشغيل. | Console | Dev | Accepted |
| 3 | Browser Console | Low | ظهور `Tracking Prevention` بسبب المتصفح/CDN. لا يؤثر على التشغيل. | Console | Browser | Accepted |
| 4 | Model Cycle Data | Medium | تاريخ بداية الدورة ظهر بعد تاريخ نهاية الدورة في بيانات الاختبار. الحفظ نجح تقنيًا، لكن يجب تعديل بيانات Excel قبل الاعتماد النهائي. | UI | Data Owner | Open - Data Fix |

### تفاصيل الإصلاح

| Item | Value |
|---|---|
| Hotfix Commit | `1e1b686` |
| Commit Message | `fix: prevent merged-cell error in XLSX calibration sandbox export` |
| File Fixed | `core_engine/mass_appraisal_excel.py` |
| Result After Fix | XLSX export works and no HTTP 500 |
| Pilot Impact | تم حل المشكلة قبل قرار النجاح النهائي |

### ملخص حالة المشكلات

| Severity | Count | Status |
|---|---:|---|
| Blocker | 0 | None |
| High | 1 | Resolved |
| Medium | 1 | Open - Data Fix |
| Low | 2 | Accepted |

---

## 22. Pilot Pass/Fail Decision

### قائمة قرار النجاح

- [x] No blockers.
- [x] No high-severity unresolved issues.
- [x] Excel upload works.
- [x] Mass Appraisal run works.
- [x] Sales/Ratio/Calibration chain works.
- [x] XLSX export reviewed.
- [x] Session export/import works.
- [x] Logs reviewed.
- [x] Results accepted for technical pilot review.
- [ ] Model Cycle dates require data correction before final business approval.

### قرار الاختبار

| Field | Value |
|---|---|
| Pilot Result | Conditional Pass |
| Reviewer | م. هشام المهدي |
| Date | 2026-05-06 |
| Notes | الاختبار التشغيلي نجح وظيفيًا. تم رفع Excel بدون أخطاء، وتشغيل التقييم الجماعي، والتحقق من المبيعات، والتعديل الزمني، وتعديلات المبيعات، ودراسة النسب، والمعايرة، وSandbox، والحوكمة، والتصدير، واستيراد/تصدير الجلسة. توجد ملاحظة بيانات فقط: تاريخ بداية دورة النموذج بعد تاريخ النهاية، ويجب تصحيحها في ملف Excel قبل الاعتماد النهائي. |

### ملخص القرار

| Area | Result |
|---|---|
| Environment | Pass |
| Excel Upload | Pass |
| Mass Appraisal | Pass |
| Sales Verification | Pass |
| Time Adjustment | Pass |
| Sales Adjustments | Pass |
| Ratio Study | Pass |
| Calibration Preview | Pass |
| Calibration Sandbox | Pass |
| Governance | Pass |
| Model Cycle | Conditional Pass - data correction needed |
| XLSX Export | Pass after hotfix |
| Session Export/Import | Pass |
| Final Console | Pass |

### القرار النهائي

- [x] النظام جاهز لاستكمال Pilot Controlled Use.
- [x] لا توجد مشاكل كود مانعة بعد إصلاح XLSX Export.
- [x] يجب تصحيح تواريخ Model Cycle في بيانات Excel قبل اعتبار النتيجة Business-approved.
- [ ] لا يتم اعتبار الاختبار Final Pass إلا بعد تصحيح بيانات دورة النموذج أو اعتمادها كملاحظة مقبولة.

---

## 23. Next Action After Pilot

### القرار الحالي بعد الاختبار

| Field | Value |
|---|---|
| Pilot Result | Conditional Pass |
| Blocking Code Issues | None |
| Blocking Functional Issues | None |
| Main Note | توجد ملاحظة بيانات في Model Cycle: تاريخ بداية الدورة بعد تاريخ النهاية |
| Required Action Before Final Pass | تصحيح تواريخ دورة النموذج في ملف Excel أو اعتمادها كملاحظة بيانات غير مانعة |

### معنى Conditional Pass

الاختبار نجح وظيفيًا من ناحية النظام:

- [x] Excel upload يعمل.
- [x] Mass Appraisal يعمل.
- [x] Sales Verification يعمل.
- [x] Time Adjustment يعمل.
- [x] Sales Adjustments تعمل.
- [x] Ratio Study تعمل.
- [x] Calibration Preview يعمل.
- [x] Calibration Sandbox يعمل.
- [x] Governance يعمل.
- [x] XLSX Export يعمل بعد إصلاح الخطأ.
- [x] Session Export / Import يعمل.
- [x] لا توجد أخطاء Console مانعة.

لكن النتيجة ليست Final Pass بسبب ملاحظة بيانات:

- [ ] تاريخ بداية Model Cycle يجب أن يكون قبل تاريخ النهاية.

### الإجراء التالي

يوجد اختياران:

| Option | Action | Result |
|---|---|---|
| Option 1 | تصحيح تاريخ بداية ونهاية Model Cycle في Excel ثم إعادة اختبار Section 17 فقط | يمكن تحويل النتيجة إلى Pass |
| Option 2 | قبول الملاحظة لأنها بيانات اختبار فقط | تبقى النتيجة Conditional Pass |

### قرار Tag

| Item | Decision |
|---|---|
| Create v3.14-pilot-ready now | No |
| Reason | يوجد Hotfix بعد tag السابق، وملف checklist تم تعديله بنتائج الاختبار |
| Required before tag | Commit نتائج الاختبار ثم قرار المراجع |
| Current recommendation | Commit checklist first, then update tag بعد الاعتماد |

### أوامر حفظ نتائج الاختبار

نفذ الأوامر التالية بعد حفظ الملف:

| Step | Command |
|---|---|
| 1 | git status --short |
| 2 | git add docs/mass_appraisal_real_pilot_test_checklist.md |
| 3 | git commit -m "test: record real pilot checklist results" |
| 4 | git status --short |
| 5 | git log --oneline --decorate -5 |

### أوامر تحديث Tag بعد الاعتماد

لا تنفذ هذه الأوامر إلا بعد اعتماد النتيجة النهائية:

| Step | Command |
|---|---|
| 1 | git tag -f -a v3.14-pilot-ready -m "Phase 3.14 pilot-ready: Mass Appraisal real data pilot baseline" |
| 2 | git push origin main |
| 3 | git push origin -f v3.14-pilot-ready |

### القرار النهائي المقترح الآن

| Item | Decision |
|---|---|
| Continue controlled pilot use | Yes |
| Pilot result now | Conditional Pass |
| Required data fix | Correct Model Cycle date order |
| Required code fix | None |
| Public production release | Not yet |
| Reason production is not final | Authentication, CORS restriction, HTTPS, and access control still need production hardening |

- وثِّق جميع الـ Blockers في سجل المشاكل.
- لا تُنشئ الوسم.
- حدِّد المطلوب: إصلاح بيانات أم إصلاح في النظام.
- ابدأ دورة إصلاح جديدة وأعد الاختبار.

---

*آخر تحديث: Phase 3.14 Prompt 6B — 2026-05-06*
