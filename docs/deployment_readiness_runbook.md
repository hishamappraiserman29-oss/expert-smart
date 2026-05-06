# دليل تشغيل وتجهيز النشر — Expert Smart Mass Appraisal

> **الإصدار:** Phase 3.14 | **التاريخ:** 2026-05-06
> **النطاق:** تشغيل محلي / تجريبي (Controlled Local Pilot)

---

## 1. الهدف من الدليل

هذا الدليل يُغطي تشغيل منظومة Expert Smart Mass Appraisal خلال **مرحلة التجربة المحلية المضبوطة (Controlled Local Pilot)**. يهدف إلى تمكين المشغّل أو المهندس من:

- تشغيل النظام بالكامل عبر Docker
- التحقق من صحة الخدمات والمسارات
- فتح الواجهة وتشغيل سير العمل الكامل
- عرض السجلات (Logs) وتشخيص الأخطاء
- إجراء النسخ الاحتياطية والتراجع السريع

> **تنبيه:** هذا الإعداد مناسب للتجربة المحلية المضبوطة. **لا يُستخدم مباشرةً في بيئة إنتاج عامة على الإنترنت** قبل اتخاذ تدابير الأمان الإضافية الموضحة في القسم 14.

---

## 2. المتطلبات قبل التشغيل

### قائمة التحقق قبل البدء

```
□ Docker Desktop مثبَّت على الجهاز
□ Docker Desktop يعمل (أيقونة الحوت في شريط المهام)
□ مجلد المشروع موجود على الجهاز
□ PowerShell متاح
□ المنفذ 5000 غير مستخدم من تطبيق آخر
□ المتصفح متاح (Chrome / Edge / Firefox)
□ أحدث الإصدارات مسحوبة على الفرع الحالي
□ (اختياري) الوسم v3.13-stable موجود كنقطة رجوع
```

### أوامر التحقق الأولي

```powershell
# التحقق من حالة Git
git status --short
git log --oneline --decorate -5

# التحقق من Docker
docker version
docker ps
```

**المخرج المتوقع لـ `docker version`:** يجب أن يظهر رقم إصدار Client و Server بلا أخطاء.
**المخرج المتوقع لـ `docker ps`:** قائمة الحاويات الجارية (أو فارغة إن لم يُشغَّل بعد).

---

## 3. تشغيل النظام

```powershell
cd "C:\Users\Lenovo\Desktop\expert_smart1 - Copy"

docker compose -f deploy/docker-compose.yml up -d
```

> إن أردت إعادة بناء صورة Flask فقط بعد تعديل الكود:
> ```powershell
> docker build -f deploy/Dockerfile.flask -t expert-smart/flask:latest .
> docker stop expert-smart-flask
> docker rm expert-smart-flask
> docker compose -f deploy/docker-compose.yml up -d flask
> ```

### ما الذي يحدث عند التشغيل؟

| الخدمة | الوظيفة | المنفذ |
|---|---|---|
| `expert-smart-flask` | تطبيق الويب / API (Waitress) | 5000 |
| `expert-smart-qdrant` | قاعدة البيانات المتجهية (RAG) | 6333 / 6334 |
| `expert-smart-ollama` | نموذج اللغة المحلي (Llama 3 8B) | 11434 |

> **تحذير غير مؤثر:** قد يظهر التحذير التالي — يمكن تجاهله:
> ```
> the attribute `version` is obsolete, it will be ignored
> ```

---

## 4. التحقق من حالة الحاويات

```powershell
docker compose -f deploy/docker-compose.yml ps
docker ps
```

### الحاويات المتوقعة

| الاسم | الحالة الطبيعية |
|---|---|
| `expert-smart-flask` | `Up (healthy)` |
| `expert-smart-qdrant` | `Up (healthy)` |
| `expert-smart-ollama` | `Up (healthy)` |

### معنى كل حالة

| الحالة | المعنى |
|---|---|
| `Up (healthy)` | يعمل ويستجيب لفحص الصحة ✓ |
| `Up` | يعمل لكن فحص الصحة لم يكتمل بعد (انتظر 30-60 ثانية) |
| `Starting` | في طور البدء، انتظر |
| `Exited` | توقف — راجع الـ logs |
| `Restarting` | يعيد المحاولة — راجع الـ logs |

---

## 5. فحص الصحة (Health Check)

### curl (PowerShell / cmd)

```powershell
curl.exe -s http://127.0.0.1:5000/api/advisor/health
```

### PowerShell الأصيل

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/advisor/health" -Method Get
```

### المخرج المتوقع

```json
{
  "status": "ok",
  "rag_ready": true,
  "message": "المستشار الذكي جاهز"
}
```

> إن ظهر `"rag_ready": false`، انتظر 30 ثانية وأعد المحاولة — قد يكون Qdrant لا يزال في طور التهيئة.

---

## 6. فتح الواجهة

```
http://127.0.0.1:5000/
```

> **مهم:** لا تفتح `frontend/index.html` مباشرةً من المجلد (`file://`). هذا يمنع طلبات API بسبب سياسة CORS.

### إعادة التحميل الكاملة (بعد تحديث Flask)

```
Ctrl + Shift + R
```

### تحذيرات المتصفح المقبولة (غير مؤثرة)

```
□ favicon.ico 404 — لا يوجد أيقونة للموقع، غير مؤثر
□ Tracking prevention for CDN fonts — حماية خصوصية المتصفح، غير مؤثر
□ Mixed content warnings for external CDN (read-only) — غير مؤثر
```

### أخطاء المتصفح التي تستوجب التوقف

```
⛔ Failed to fetch — الخادم لا يرد، تحقق من الصحة
⛔ Uncaught TypeError — خطأ في JavaScript، افتح Console للتفاصيل
⛔ Cannot read properties of null — بيانات مفقودة في الاستجابة
⛔ JSON.parse error — استجابة غير صالحة من الخادم
⛔ NaN في قيمة حقل مالي — خلل في البيانات أو الحسابات
```

---

## 7. اختبار المسارات الأساسية (Route Smoke Tests)

### تحميل قالب Excel

```powershell
curl.exe -I http://127.0.0.1:5000/api/mass-appraisal/template-xlsx
```

**المتوقع:** `HTTP/1.1 200 OK` مع `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

### استيراد Excel (بدون ملف — اختبار الحماية)

```powershell
curl.exe -i -X POST http://127.0.0.1:5000/api/mass-appraisal/import-xlsx
```

**المتوقع:** `HTTP/1.1 400 BAD REQUEST` مع رسالة واضحة:
```json
{"status": "error", "message": "No file part. Upload an .xlsx file using multipart field 'file'."}
```

### معاينة التقييم الجماعي

```powershell
curl.exe -s -X POST http://127.0.0.1:5000/api/mass-appraisal/preview `
  -H "Content-Type: application/json" `
  -d '{\"rows\":[{\"id\":\"U-001\",\"location\":\"التجمع الخامس\",\"property_type\":\"شقة سكنية\",\"area\":150,\"zone_id\":\"Z-NC-01\",\"property_class\":\"A\"}]}'
```

**المتوقع:** `HTTP/1.1 200 OK` مع مصفوفة `units` تحتوي نتيجة.

---

## 8. اختبار سريع للواجهة

قبل التجربة الحقيقية، تحقق من كل نقطة:

```
□ التقييم المفرد (Single Valuation) يعطي نتيجة
□ تبويب "التقييم الجماعي" يظهر ويعمل
□ زر "تحميل القالب" يُنزِّل ملف .xlsx
□ معالج رفع Excel يقبل الملف ويُظهر بيانات المعاينة
□ لوحة التحقق من الصحة تظهر التحذيرات والأخطاء
□ زر "ملء العقارات" ينقل البيانات لحقول الإدخال
□ "معاينة جماعية" تُرجع نتائج لجميع الصفوف
□ "تشغيل جماعي" يُكمل بلا أخطاء
□ التحقق من صحة المبيعات (Sales Verification) يعمل
□ تحميل XLSX يشمل الأوراق الجديدة (Export_Metadata, Readiness, ...)
□ تصدير / استيراد الجلسة يعمل
```

---

## 9. عرض السجلات (Logs)

### عرض آخر 100 سطر

```powershell
docker compose -f deploy/docker-compose.yml logs flask --tail=100
```

### متابعة السجلات بشكل مباشر (Live)

```powershell
docker compose -f deploy/docker-compose.yml logs flask -f
```

اضغط `Ctrl + C` لإيقاف المتابعة.

### عرض سجلات خدمات أخرى

```powershell
docker compose -f deploy/docker-compose.yml logs qdrant --tail=50
docker compose -f deploy/docker-compose.yml logs ollama --tail=50
```

> **نصيحة:** اترك نافذة سجلات مفتوحة أثناء التجربة لمراقبة الأخطاء فور حدوثها.

---

## 10. إعادة تشغيل Flask فقط

### إعادة تشغيل بدون إعادة بناء (restart only)

```powershell
docker compose -f deploy/docker-compose.yml restart flask
```

### إعادة بناء وتشغيل (بعد تعديل الكود)

```powershell
docker compose -f deploy/docker-compose.yml up -d --build flask
```

> **تحذير — مشكلة TLS:** إن فشل الأمر أعلاه بخطأ TLS timeout أثناء سحب صورة Ollama، استخدم الحل البديل المباشر:

```powershell
# بناء صورة Flask مباشرةً (بدون سحب Ollama)
docker build -f deploy/Dockerfile.flask -t expert-smart/flask:latest .

# إيقاف الحاوية القديمة وإزالتها
docker stop expert-smart-flask
docker rm expert-smart-flask

# تشغيل الحاوية الجديدة (بدون --build)
docker compose -f deploy/docker-compose.yml up -d flask
```

> **مهم:** Waitress لا يُعيد تحميل الكود تلقائياً. أي تعديل على Python يستوجب إعادة بناء الصورة وتبديل الحاوية.

---

## 11. إيقاف النظام

### إيقاف مؤقت لجميع الخدمات

```powershell
docker compose -f deploy/docker-compose.yml stop
```

### إيقاف Flask فقط

```powershell
docker compose -f deploy/docker-compose.yml stop flask
```

### إيقاف وإزالة الحاويات (مع الحفاظ على البيانات)

```powershell
docker compose -f deploy/docker-compose.yml down
```

> **تحذير:** لا تستخدم `docker system prune` أو `docker compose down -v` إلا إن كنت تقصد حذف أوزان Llama 3 (~5 GB) والبيانات المتجهية. هذا لا يمكن التراجع عنه إلا بإعادة السحب.

---

## 12. مشاكل شائعة وحلولها

| المشكلة | السبب الغالب | الحل |
|---|---|---|
| `Unable to connect to remote server` | Flask لا يعمل | شغّل Docker Desktop ثم `compose up` |
| `dockerDesktopLinuxEngine pipe not found` | Docker Desktop متوقف | ابدأ Docker Desktop ثم انتظر دقيقة |
| `favicon.ico 404` في Console | لا توجد أيقونة | غير مؤثر، تجاهله |
| `Tracking prevention` في Console | حماية خصوصية المتصفح لـ CDN | غير مؤثر، تجاهله |
| `Failed to fetch` في الواجهة | الخادم لا يرد أو رابط API خاطئ | تحقق من health check وراجع حقل #api-url |
| `import-xlsx` يُرجع 400 بدون رسالة | لم يُرفع ملف | متوقع عند اختبار المسار — ارفع ملف xlsx حقيقي |
| رسالة "Invalid .xlsx" | الملف ليس xlsx حقيقي (magic bytes خاطئة) | استخدم ملف xlsx صادر من Excel أو القالب المُنزَّل |
| `File too large` — خطأ 413 | الملف أكبر من 10 MB | قلّل حجم البيانات أو اقسم الملف |
| `matched_count: 0` في دراسة النسبة | لا يوجد `subject_id` مشترك بين العقارات والمبيعات | تحقق من تطابق `subject_id` في ورقتي Properties و Sales |
| `rag_ready: false` | Qdrant في طور التهيئة | انتظر 30 ثانية وأعد المحاولة |
| الكود الجديد لا يظهر بعد "restart" | Waitress لا يُعيد التحميل تلقائياً | أعد بناء الصورة وبدّل الحاوية (القسم 10) |
| خطأ TLS timeout عند `--build flask` | Compose يحاول سحب صورة Ollama | استخدم الحل البديل المباشر (القسم 10) |

---

## 13. النسخ الاحتياطي والتراجع

### قبل أي تجربة مهمة

1. **تصدير الجلسة من الواجهة** — زر "تصدير الجلسة" يحفظ JSON يشمل: نتيجة التشغيل، حالة Governance، Model Cycle.
2. **تصدير XLSX** — بعد كل تشغيل ناجح.
3. **تسجيل hash الـ commit الحالي:**
   ```powershell
   git log --oneline --decorate -10
   git tag --list
   ```

### وسوم Git كنقاط رجوع

| الوسم | الحالة |
|---|---|
| `v3.13-stable` | آخر نقطة مستقرة قبل Phase 3.14 |
| `v3.14-pilot-ready` | **لم يُنشأ بعد** — ينتظر اجتياز التجربة |

### الرجوع إلى نقطة مستقرة

```powershell
# تحقق أولاً أن الـ working tree نظيف
git status --short

# الرجوع إلى وسم مستقر
git checkout v3.13-stable

# أو التراجع عن commit بعينه
git revert <commit-hash>

# العودة إلى main
git checkout main
```

> **تحذير:** لا تقفز إلى وسم قديم إن كان لديك تعديلات غير محفوظة (`git stash` أو `git commit` أولاً).

---

## 14. ملاحظات الأمان للتجربة المضبوطة

هذا الإعداد مناسب لبيئة محلية أو شبكة داخلية مضبوطة مع مستخدمين موثوقين.

**قبل أي نشر عام على الإنترنت، يجب:**

```
□ إضافة طبقة مصادقة وتحكم بالوصول (Authentication / Authorization)
□ قصر CORS على نطاق محدد بدلاً من origins: "*"
□ إخفاء منافذ Qdrant و Ollama عن الوصول الخارجي (إزالة ports من compose)
□ تفعيل HTTPS عبر nginx + TLS (deploy/nginx.conf و docker-compose.production.yml جاهزان)
□ حماية بيانات التقييم الحقيقية ووضع سياسة احتفاظ
□ تعريف صلاحيات المستخدمين (أدوار مختلفة: مُقيِّم، مراجع، مدير)
□ مراجعة تسجيل أحداث الاستيراد والتصدير في سجل تدقيق
```

> للنشر الإنتاجي، استخدم:
> ```powershell
> docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.production.yml up -d
> ```
> يُفعِّل هذا gunicorn + nginx + حدود الموارد.

---

## 15. قائمة التحقق التشغيلية للتجربة

### قبل التجربة

```
□ Docker Desktop يعمل
□ فحص الصحة يُرجع {"status":"ok","rag_ready":true}
□ المتصفح يفتح http://127.0.0.1:5000/ بلا أخطاء
□ ملف Excel القالب يُنزَّل ويُفتح بشكل صحيح
□ ملف Excel التجريبي الحقيقي جاهز ومُراجَع
□ تصدير جلسة فارغة تم اختباره
□ وسم الرجوع v3.13-stable معروف وموثَّق
□ نافذة logs مفتوحة للمراقبة
```

### أثناء التجربة

```
□ رفع ملف Excel الحقيقي
□ مراجعة التحذيرات والأخطاء في لوحة التحقق
□ تأكيد عدم وجود أخطاء blocking قبل المتابعة
□ تشغيل سير العمل الكامل (preview → run → verify → adjust → ratio study)
□ تصدير XLSX بعد كل تشغيل ناجح
□ تصدير الجلسة بعد كل مرحلة رئيسية
□ مراقبة الـ logs لأي tracebacks
```

### بعد التجربة

```
□ حفظ ملفات الإخراج (XLSX + JSON جلسة)
□ توثيق أي مشاكل أو انحرافات
□ لا تُنشئ وسم v3.14-pilot-ready إلا بعد مراجعة جميع المخرجات
□ إيقاف الخدمات إن لم تكن مطلوبة (docker compose stop)
```

---

## 16. متى تُنشئ وسم v3.14-pilot-ready؟

أنشئ هذا الوسم **فقط** بعد اكتمال الشروط التالية:

1. ✅ وثيقة Prompt 6A هذه مُلتزَمة في Git
2. ✅ وثيقة Prompt 6B (قائمة اختبار التجربة) مُلتزَمة
3. ✅ تجربة حقيقية بيانات حقيقية اجتازت قائمة التحقق بالكامل
4. ✅ لا أخطاء blocking في السجلات
5. ✅ مخرجات XLSX مراجَعة ومعتمدة

```powershell
# بعد اجتياز جميع الشروط فقط:
git tag -a v3.14-pilot-ready -m "Phase 3.14 pilot-ready: Mass Appraisal real data pilot baseline"

# لا ترفع الوسم حتى تتم المراجعة الكاملة
# git push origin v3.14-pilot-ready
```

---

*آخر تحديث: Phase 3.14 Prompt 6A — 2026-05-06*
