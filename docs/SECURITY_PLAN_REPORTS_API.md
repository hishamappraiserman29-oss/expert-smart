# Security Plan — Reports API Endpoints

> **Status:** Plan only — not yet implemented.
> **Scope:** `GET /api/reports`, `GET /api/reports/<id>`, `GET /api/reports/<id>/pdf`
> **Date:** مايو 2026 — v1.0

---

## 1. الوضع الحالي (Threat Surface)

### نتائج الفحص

**Authentication:**
لا يوجد أي بوابة auth على مستوى التطبيق. التعليق في الكود الحالي صريح:
```
# No application-level auth gate — infrastructure auth is assumed,
# consistent with the existing /api/valuation endpoint.
```

**Framework:**
Flask خالص (`Flask, jsonify, request, send_file, flask_cors`).
لا `Flask-Login`، لا `Flask-JWT-Extended`، لا أي auth decorator في الاستدعاءات الرئيسية.

**Rate Limiting:**
لا `flask-limiter` ولا أي throttle logic. الحد الوحيد الموجود هو pagination guard بسيط في `GET /api/reports`:
```python
limit = min(int(request.args.get("limit", 20)), 100)   # cap at 100 records
```
هذا ليس rate limiting — يمكن لأي طالب تكرار الطلب لا نهائياً.

**User Isolation:**
`schema.py` الحالي — جدول `reports`:
```sql
report_id, profile_key, status, appraiser_name,
market_value, created_at, updated_at, data_json
```
**لا يوجد عمود `owner_user_id` أو `tenant_id`.**
كل التقارير مرئية لكل من يصل للـ endpoint.

**Audit Logging:**
`database.audit_log` معرَّف في الكود (R3 WIP) لكن غير مفعَّل على `main` بعد.

**API Keys (R3 WIP):**
هناك endpoint معطَّل حالياً (`/api/hardening/api-keys/generate`) من subsystem `api.security_layer` على فرع R3. موجود في الكود لكن لا يُستدعى على `main`.

### التقييم

| المحور | الحالة | الملاحظة |
|---|---|---|
| ❌ Authentication | غائب | "infrastructure auth is assumed" |
| ❌ Authorization | غائب | لا owner check، لا role check |
| ❌ Rate Limiting | غائب | pagination cap فقط (100 records/request) |
| ❌ User Isolation | غائب | لا `owner_user_id` في الـ schema |
| ❌ Audit Logging | غائب (WIP) | موجود في R3، غير مفعَّل |
| ⚠️ Filename Sanitisation | موجود جزئياً | `safe_name` في PDF endpoint (`isalnum + "-_"`) |
| ⚠️ Pagination Cap | موجود جزئياً | `min(..., 100)` في list endpoint |

---

## 2. التهديدات المحتملة (Threat Model)

| # | التهديد | الأثر | الاحتمالية |
|---|---|---|---|
| T1 | **Unauthorized listing** — أي شخص يستدعي `GET /api/reports` | كشف جميع التقارير المحفوظة (بيانات عقارية حساسة) | High |
| T2 | **IDOR** — تخمين أو برمجة `report_id` والوصول لتقرير شخص آخر | تسرُّب بيانات (data leak) — `GET /api/reports/<id>` و `<id>/pdf` | High |
| T3 | **PDF mass scraping** — تنزيل آلاف الـ PDFs تلقائياً | سرقة بيانات + استنزاف bandwidth + CPU | Medium |
| T4 | **DoS عبر list flooding** — طلبات متكررة بـ `limit=100&offset=0` | server overload + قاعدة البيانات تحت ضغط | Medium |
| T5 | **Replay access** — وصول لتقرير "archived" بعد إلغاء الصلاحية | وصول لبيانات منتهي صلاحيتها | Low |
| T6 | **Information leakage عبر 403** | 403 يكشف وجود الـ ID — يُسهَّل التعداد (enumeration) | Low |
| T7 | **Path traversal في report_id** | حالياً محمي بالـ `safe_name` sanitisation، لكن يستحق التحقق | Low |

---

## 3. Authentication — الخيارات

### الوضع الحالي في bridge_api
Flask خالص بلا auth library. الـ `/api/valuation` نفسه لا يحوي auth gate.

### 3.1 Token-based — Bearer Token (موصى به)

```
Authorization: Bearer <token>
```

- **توليد:** عند login، token مُوقَّع يصلح N ساعة
- **تخزين:** JWT مُوقَّع (stateless) أو token hash في DB (revocable)
- **مكتبة:** `PyJWT` (خفيف، لا تبعيات إضافية كبيرة) أو `Flask-JWT-Extended`
- **الميزة:** يعمل مع frontend، mobile، API clients خارجية
- **التحقق:** decorator بسيط `@require_auth` يُطبَّق على الـ 3 endpoints

```python
# مثال توضيحي — للتوثيق فقط، لا ينفَّذ هنا
def require_auth(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").removeprefix("Bearer ")
        if not _validate_token(token):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated
```

### 3.2 Session Cookies + CSRF

- مناسب لـ frontend فقط (same-origin)
- أصعب للـ API الخارجي
- يتطلب `flask_wtf` أو `flask_login`

### 3.3 API Keys (B2B)

- للتكامل مع أنظمة خارجية (بنوك، شركات)
- الـ `api.security_layer` في R3 يوفر هذا جاهزاً (`/api/hardening/api-keys/generate`)
- **ليس بديلاً عن auth للمستخدم النهائي**

### القرار المقترح

**Bearer Token (PyJWT)** — لا يتعارض مع الـ R3 `api.security_layer` الذي يمكن دمجه لاحقاً.
لو اكتُشف أن الـ R3 `security_layer` يوفر bearer validation، يُفضَّل إعادة الاستخدام.

---

## 4. Authorization & Isolation

### 4.1 Field-level isolation — DB Schema

الـ schema الحالي لا يحوي `owner_user_id`. التغيير المطلوب في **مهمة منفصلة (S1)**:

```sql
-- migration v1 → v2
ALTER TABLE reports ADD COLUMN owner_user_id TEXT;
CREATE INDEX IF NOT EXISTS idx_reports_owner ON reports(owner_user_id);
```

- القيمة الافتراضية للتقارير القديمة: `NULL` أو `"system"` (تُقرَّر عند التنفيذ)
- `save_report()` في `db_engine.py` يأخذ `owner_user_id` إلزامياً لاحقاً
- migration forward-only فقط (v0→v1→v2 — لا rollback)

### 4.2 Endpoint-level checks

```
GET /api/reports
    → filter by g.current_user.id داخلياً
    → لا يقبل user_id من client في الـ query string

GET /api/reports/<id>
    → if record.owner_user_id != g.current_user.id → HTTP 404
    (ليس 403 — لتجنُّب information leakage / IDOR enumeration)

GET /api/reports/<id>/pdf
    → نفس owner check قبل توليد الـ PDF
```

### 4.3 Admin role (اختياري)

- flag `is_admin` على المستخدم يتخطّى الـ owner filter
- يرى جميع التقارير بصرف النظر عن `owner_user_id`

---

## 5. Rate Limiting

### 5.1 مكتبة مقترحة

`flask-limiter` — تدعم in-memory (dev) و Redis (production).

```python
# مثال توضيحي — للتوثيق فقط
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
limiter = Limiter(app, key_func=get_remote_address)
```

### 5.2 Per-endpoint limits

| Endpoint | الحد المقترح | السبب |
|---|---|---|
| `GET /api/reports` | 30 req/min | قراءة فهرس |
| `GET /api/reports/<id>` | 60 req/min | قراءة واحدة |
| `GET /api/reports/<id>/pdf` | 10 req/min | توليد PDF يستهلك CPU |
| `POST /api/valuation` | 5 req/min | أثقل عملية في النظام |

### 5.3 Response عند تجاوز

```
HTTP 429 Too Many Requests
Retry-After: 30
```

### 5.4 ملاحظة

**الـ pagination cap الموجود** (`min(..., 100)`) يبقى كما هو — دفاع مستقل عن rate limiting.

---

## 6. Audit Logging

كل وصول لأي من الـ 3 endpoints يُسجَّل:

| الحقل | المحتوى |
|---|---|
| `timestamp` | UTC ISO 8601 |
| `user_id` | من الـ token المُتحقَّق منه |
| `endpoint` | `list` / `detail` / `pdf` |
| `report_id` | إن انطبق (null للـ list) |
| `ip_address` | من `request.remote_addr` |
| `result` | `200` / `404` / `401` / `429` |

**تخزين:** جدول `report_access_log` مستقل في نفس SQLite.
**أرشفة:** بعد 90 يوماً (أو حسب سياسة retention المحلية).

الـ R3 `database.audit_log` (`_AuditLog`, `_AuditAction`, `_AuditEvent`) يوفر هذا جاهزاً — يُعاد استخدامه عند دمج R3.

---

## 7. PDF Download — اعتبارات إضافية

### موجود ✅
```python
safe_name = "".join(c if (c.isalnum() or c in "-_") else "_" for c in report_id)
# → Content-Disposition: attachment; filename="report_<safe_name>.pdf"
```

### مطلوب إضافته

- **`Content-Type: application/pdf`** — تأكيد صريح (موجود عبر `send_file`, يُتحقَّق)
- **`X-Content-Type-Options: nosniff`** — منع MIME sniffing
- **Owner check قبل التوليد** (انظر القسم 4.2) — لمنع IDOR
- **⚠️ Race condition:** لو `generate_pdf()` يكتب لملف مؤقت بـ report_id كاسم، طلبان متزامنان لـ ID مختلفَين لا يتداخلان. لكن لو الاسم ثابت (`temp.pdf`) — خطر تسرُّب. **يجب التحقق من `pdf_engine.py` عند التنفيذ.**

### اختياري — Signed URLs
لو احتُيج لمشاركة تقرير مع طرف خارجي (بنك، محكمة):
- توليد رابط مؤقت يصلح N دقيقة + token موقَّع في الـ URL
- بعد الانتهاء → 410 Gone

---

## 8. خطة التنفيذ المرحلية

| Phase | الوصف | المخاطرة | المتطلبات |
|---|---|---|---|
| **S1** | إضافة `owner_user_id` لـ DB schema — migration v1→v2 | متوسط | gate + tests |
| **S2** | Auth middleware (Bearer Token) في bridge_api + login endpoint | متوسط | S1 |
| **S3** | تطبيق owner isolation على الـ 3 endpoints | منخفض | S1 + S2 |
| **S4** | Rate limiting عبر `flask-limiter` | منخفض | مستقل |
| **S5** | Audit logging لكل وصول | منخفض | S1 + S2 |

**قاعدة:** كل phase مهمة منفصلة بـ Gate إلزامي — لا تُجمع phases.

---

## 9. ما لن تغطّيه هذه الخطة (Out of Scope)

| المحور | المسؤول |
|---|---|
| HTTPS / TLS | Infrastructure layer — nginx / k8s ingress |
| DDoS على مستوى الشبكة | CDN / WAF (Cloudflare, AWS Shield) |
| WAF rules (SQLi, XSS patterns) | Infrastructure / WAF layer |
| Penetration testing الفعلي | Security team — جلسة منفصلة |
| GDPR / data retention policy | القانوني + الإداري |

---

## 10. أسئلة معلَّقة للنقاش

| # | السؤال | الأثر على التنفيذ |
|---|---|---|
| Q1 | هل يوجد نظام مستخدمين حالياً (user table / identity provider)؟ | يُحدَّد S2 approach |
| Q2 | single-tenant (users فقط) أم multi-tenant (شركات + users)؟ | يُحدَّد S1 schema depth |
| Q3 | ما المدة الافتراضية لصلاحية الـ session token؟ | إعداد JWT expiry |
| Q4 | هل تقارير "archived" تحتاج صلاحية وصول مختلفة عن "draft"/"final"؟ | يُحدَّد S3 filter logic |
| Q5 | هل يحتاج النظام مشاركة تقارير خارجياً (بنك، محكمة)؟ | يُحدَّد حاجة Signed URLs |
| Q6 | هل يُعاد استخدام R3 `api.security_layer` أم نبني auth مستقلاً؟ | يُحدَّد مسار S2 |

---

**EXPERT_SMART | Security Plan — Reports API | Plan Only | مايو 2026**
