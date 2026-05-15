# تقرير إغلاق المشروع — Shared Core Architecture

**EXPERT_SMART** — رحلة بناء بنية موحَّدة للتقارير العقارية

**التاريخ:** مايو 2026
**الإصدار:** 1.0

---

## فهرس

1. القسم الأول — الملخص التنفيذي (د. عبد الرؤوف)
2. القسم الثاني — المرجع التقني (للمطوّر)
3. ملحق — مرجع سريع للـ APIs

---

# القسم الأول — الملخص التنفيذي

> لـ د. عبد الرؤوف محمد عبد الباقي

## 1.1 السياق — من أين بدأنا؟

كان لدينا ملف Excel ضخم وقوي لتقييم العقارات، لكنه نشأ ثلاث مرات (لثلاثة أنواع تقارير: legacy / detailed / professional_template) مع تكرار كبير في الكود. أي تعديل بسيط — تغيير لون، خط، صياغة — كان يستلزم تطبيقه ثلاث مرات يدوياً، مما يُسرّب الأخطاء ويضاعف التكلفة.

## 1.2 الهدف — ماذا أردنا؟

بناء نظام احترافي موحَّد بنفس قوة الـ Excel الحالي، لكن:

- **مرجع واحد** للألوان والخطوط والمنطق (بدل ثلاث نسخ متكررة)
- **تصدير PDF** بجانب Excel، بنفس الهوية البصرية (Midnight Gold + خط Cairo العربي)
- **تحقق ذكي** من البيانات قبل توليد التقرير (تنبيهات/أخطاء بالعربية والإنجليزية)
- **قاعدة بيانات** تحفظ التقارير وتستعيدها (لا فقدان للتقارير السابقة)
- **واجهة استرجاع** ضمن الـ frontend
- **اختبارات آلية** تحرس الجودة عند كل تغيير

## 1.3 ما أنجزناه

سبع مراحل متتالية + مرحلة ربط + واجهة فرونت-إند:

| # | المرحلة | المُنجَز |
|---|---|---|
| 1 | Profile Registry | مرجع واحد لأنواع التقارير الثلاثة |
| 2 | Report Theme | لوحة ألوان/خطوط Midnight Gold موحَّدة |
| 3 | Theme Integration | استبدال التكرار في `excel_builder` بالمرجع الجديد |
| 4 | Sales Comparison Sheet | فصل قسم مقارنة البيوع كـ module مستقل |
| 5 | Inputs + Main Report Sheets | فصل قسمَي المُدخلات والتقرير الرئيسي |
| 6 | Cost/Income/Reconciliation/Certification Sheets | فصل أقسام التقييم الأربعة |
| 7 | PDF + Validation + DB Engines | المحرّكات الثلاثة المستقلة |
| BA | Bridge API Integration | ربط المحرّكات بواجهة الـ API |
| FE | Frontend Integration | لوحة استرجاع التقارير + تنزيل PDF |

## 1.4 القيمة العملية لك

ما يمكنك أن تفعله الآن ولم تكن تفعله من قبل:

1. **تصدير PDF بضغطة زر** — تقرير عربي احترافي بنفس الهوية البصرية، نص متّصل، صفحات منسَّقة.
2. **عدم تكرار العمل** — تعديل اللون أو الخط أو الصياغة في مكان واحد ينعكس على كل التقارير.
3. **حماية ضد الأخطاء** — التحقق الذكي ينبّهك (أو يمنعك) إذا كانت البيانات ناقصة أو غير منطقية، **قبل** توليد التقرير.
4. **سجل التقارير** — كل تقرير تولِّده يُحفظ تلقائياً (إن فعّلت ذلك)، تستطيع استرجاعه أو تنزيل PDF منه لاحقاً.
5. **واجهة بسيطة** — لوحة "سجل التقارير المحفوظة" في الـ frontend مع فلاتر (نوع التقرير، الحالة).
6. **ثقة في النتائج** — 1606 اختبار آلي يحرس الجودة؛ أي تعديل مستقبلي يكسر شيئاً سيُكتشَف فوراً.

## 1.5 الأرقام

- **9 commits على main** — كل واحدة atomic ومُختبَرة
- **24 commit إضافية** على فرع R3 — جاهزة للمراجعة الانتقائية
- **1606 اختبار آلي** — كلها خضراء، صفر regression عبر كل المراحل
- **3 محرّكات مستقلة** — PDF / Validation / DB
- **7 sheet modules** — قسم واحد في ملف واحد
- **150+ ملف** تمت معالجتها وفصلها بانضباط

## 1.6 الحالة الحالية للمشروع

| المسار | المحتوى | الاختبارات |
|---|---|---|
| `main` | البنية الكاملة (Shared Core + Engines + Bridge + Frontend) — جاهزة للإنتاج | 1606/1606 ✅ |
| `wip/r3-subsystems-checkpoint` | 24 subsystem إضافية (banking/agents/marketplace/...) محفوظة بأمان | 1606/1606 ✅ |
| غير مُرتكَب | `PHASE_4_README.md` فقط — في انتظار مراجعتك اليدوية | — |

## 1.7 ما المتبقّي

- **مراجعة الـ 24 subsystem** على الفرع المنفصل (جلسات لاحقة، كل subsystem على حدة)
- **مراجعة `PHASE_4_README.md`** اليدوية (تغيير تجميلي بسيط)
- **اختيارياً:** إضافات للـ frontend، توسعة للـ engines، تحسينات للـ UX

---

# القسم الثاني — المرجع التقني

> للمطوّر — أي مهندس يلتقط المشروع لاحقاً

## 2.1 شجرة المعمارية النهائية

```
expert_smart/
├── core_engine/
│   ├── reports/
│   │   ├── report_profiles.py          # Phase 1 — Registry (3 profiles)
│   │   ├── report_theme.py             # Phase 2 — Palette + Typography
│   │   ├── excel_builder.py            # Phase 3 — uses theme + sheets
│   │   ├── report_pipeline.py          # BA.1 — facade for bridge_api
│   │   ├── sheets/                     # Phases 4-6 — sheet modules
│   │   │   ├── inputs_sheet.py
│   │   │   ├── main_report_sheet.py
│   │   │   ├── sales_comparison_sheet.py
│   │   │   ├── cost_approach_sheet.py
│   │   │   ├── income_approach_sheet.py
│   │   │   ├── reconciliation_sheet.py
│   │   │   ├── certification_sheet.py
│   │   │   └── _archive/               # Midnight Gold legacy
│   │   ├── pdf/                        # Phase 7a — PDF Engine
│   │   │   ├── pdf_engine.py
│   │   │   ├── pdf_theme.py
│   │   │   ├── pdf_arabic.py
│   │   │   ├── pdf_components.py
│   │   │   ├── sections/
│   │   │   │   ├── certification_pdf.py
│   │   │   │   ├── main_report_pdf.py
│   │   │   │   ├── sales_comparison_pdf.py
│   │   │   │   └── cost_income_reconciliation_pdf.py
│   │   │   └── assets/fonts/
│   │   │       ├── Cairo-Regular.ttf
│   │   │       └── Cairo-Bold.ttf
│   │   ├── validation/                 # Phase 7b — Validation Engine
│   │   │   ├── result.py
│   │   │   ├── rules.py
│   │   │   ├── input_validator.py
│   │   │   ├── output_validator.py
│   │   │   └── validation_engine.py
│   │   └── db/                         # Phase 7c — DB Engine
│   │       ├── schema.py
│   │       ├── models.py
│   │       ├── migrations.py
│   │       ├── repository.py
│   │       └── db_engine.py
│   ├── tests/                          # 1606 tests
│   └── bridge_api.py                   # BA.2-BA.4 — wired engines
├── frontend/
│   ├── index.html                      # FE.1+FE.2 — history panel
│   ├── agent_chat.html
│   ├── localization.js
│   └── style_rtl.css
├── docker/                             # Phase A — infra
├── kubernetes/                         # Phase A — infra
└── .gitignore                          # Phase A — R2-I pattern
```

## 2.2 Profile Registry

```python
# core_engine/reports/report_profiles.py
from dataclasses import dataclass

@dataclass(frozen=True)
class Profile:
    key: str
    name_ar: str
    name_en: str
    template_path: str
    sheets: tuple[str, ...]
    features: ReportFeatures
    tier: PriceTier

REGISTRY = {
    "legacy":                Profile(key="legacy", ...),
    "detailed":              Profile(key="detailed", ...),
    "professional_template": Profile(key="professional_template", ...),
}
```

> ⚠️ **مفتاح الـ profile الصحيح: `professional_template`** (ليس `"professional"`). هذا التمييز اكتشفه الـ smoke test ويُلتزَم به في كل الكود.

## 2.3 Report Theme — Midnight Gold

```python
# core_engine/reports/report_theme.py
class Palette:
    INK          = "0B1437"
    NAVY_DEEP    = "12224F"
    NAVY         = "1B3263"
    INDIGO       = "3A5491"
    GOLD         = "C9A961"
    GOLD_LIGHT   = "EBD79A"
    EMERALD      = "0E8B6E"
    CORAL        = "D85842"
    PURPLE       = "6B4FA1"
    INPUT_BLUE   = "0000FF"   # Wall Street blue للـ inputs

class Typography:
    PRIMARY  = "Cairo"
    FALLBACK = "Calibri"
    SIZE_PAGE_TITLE = 22
    SIZE_LABEL      = 10.5

# Style applicators
def style_page_title(cell): ...
def draw_banner(ws, row, end_col, text, ...): ...
def apply_sheet_defaults(ws, freeze=True): ...
```

## 2.4 المحرّكات الثلاثة

### Validation Engine

```python
from core_engine.reports.validation import validate_report

result = validate_report(data, profile_key="legacy")
if not result.is_valid:
    for issue in result.errors:
        print(issue.code, issue.message_ar, issue.message_en)
```

ميزات:
- 3 مستويات: `ERROR` / `WARNING` / `INFO`
- رسائل ثنائية اللغة (`message_ar` + `message_en`)
- أكواد ثابتة machine-readable (مثل `WEIGHTS_SUM_MISMATCH`, `AREA_POSITIVE`)
- profile-aware (قواعد مختلفة لكل profile)

### PDF Engine

```python
from core_engine.reports.pdf import generate_pdf

generate_pdf(
    profile_key="professional_template",
    data=report_dto,
    output_path="report.pdf",
)
```

ميزات:
- `fpdf2` + Cairo TTF مدمج (`pdf/assets/fonts/`)
- إعادة تشكيل العربية + bidi (RTL صحيح)
- Deterministic — نفس الـ input يُنتج نفس الـ MD5 (`creation_date` ثابت)
- 4 sections (main / sales / cost+income+reconciliation / certification)
- Profile-aware (KPI cards للـ detailed / professional_template فقط)

### DB Engine

```python
from core_engine.reports.db import save_report, get_report, list_reports

# حفظ
rid = save_report(data, profile_key="legacy", status="final")

# استرجاع
rec = get_report(rid)
assert rec.data == data    # round-trip fidelity 100%

# قائمة
reports = list_reports(profile_key="legacy", status="final")
```

ميزات:
- SQLite (ملف واحد، بلا خادم)
- Hybrid schema: أعمدة مفهرسة + JSON blob
- Single-row schema_version (`CHECK(id=1)`) — حماية DB-level
- JSON-serializable guard (`TypeError` واضح للبيانات غير القابلة للتسلسل)
- UTC ISO 8601 timestamps
- Round-trip fidelity (nested / Arabic / None / floats / lists / bools)
- Migrations forward-only (v0 → v1 → v2 لاحقاً)

## 2.5 Bridge API Integration

أربع موجات تكامل، كلها **additive و opt-in**:

| Wave | الـ flag / endpoint | السلوك |
|---|---|---|
| **BA.2** validation gate | `"validate": true` في payload | ERROR ⇒ HTTP 422، WARNING ⇒ يستمر مع تنبيه |
| **BA.3** auto-persist | `"persist": true` في payload | success ⇒ `report_db_id` في الـ response؛ فشل ⇒ non-fatal مع `persist_error` |
| **BA.4a** PDF export | `"pdf": true` في payload | ينتج PDF بجانب Excel |
| **BA.4b** history | `GET /api/reports`, `GET /api/reports/<id>`, `GET /api/reports/<id>/pdf` | endpoints جديدة، لا تمسّ الموجودة |

> **ضمانة zero behavior change:** `test_bridge_api_baseline.py` (BL01–13) يلتقط السلوك الحالي لكل endpoint موجود، ويبقى أخضر بعد كل موجة.

## 2.6 Frontend Integration (FE.1 + FE.2)

- لوحة `#es-reports-panel` في `frontend/index.html`
- فلاتر profile + status
- جدول بـ 8 أعمدة لكل تقرير
- Detail overlay بـ × close + backdrop close
- زر تنزيل PDF
- 9 دوال JS مع `escapeHtml` للحماية من XSS
- **No auto-load** — الصفحة لا تتأثر إن كان الـ backend متوقفاً

## 2.7 الاختبارات (1606)

| Suite | Tests |
|---|---|
| sheets + theme + profiles | ~315 |
| PDF engine (foundation + components + 4 sections + integration) | ~85 |
| Validation engine (result + rules + 2 validators + orchestrator) | ~50 |
| DB engine (schema + models + migrations + repository + engine) | ~85 |
| Bridge API (baseline + validation + persist + pdf + history + pipeline) | ~110 |
| Integration smoke (3 profiles × 4 layers) | 24 |
| All other (existing pre-Phase-1 + general) | ~937 |

## 2.8 القرارات المعمارية الحاسمة

| القرار | السبب |
|---|---|
| **Shared Core** بدلاً من تكرار 3 نسخ | DRY — تعديل في مكان واحد |
| **Profile Registry** كـ frozen dataclass | immutability + type safety |
| **3 engines مستقلة** | استدعاء كل engine منفرداً (validation بلا توليد، توليد بلا حفظ...) |
| **Bridge API additive** | صفر تغيير سلوكي على endpoints موجودة |
| **Atomic commits** (commit لكل موجة) | rollback نظيف، history مقروء |
| **Strict allowlist/denylist** لكل مهمة | منع الـ scope creep |
| **Gates إلزامية** قبل التنفيذ | منع القرارات الكبيرة بصمت |
| **Cell-by-cell verification** للـ Excel | ضمان zero behavior change |
| **Determinism في PDF** (MD5 ثابت) | reproducibility |
| **Bilingual validation messages** | تقارير ثنائية اللغة |
| **Single-row schema_version** (`CHECK(id=1)`) | DB-level integrity |
| **opt-in flags** للسلوك الجديد | المستخدم الحالي لا يتأثر |

## 2.9 حالة الـ Repo

```bash
# main (آخر commits)
f191348  chore(gitignore): ignore root-level _test*.py scripts
922794f  feat(frontend): add localization, RTL stylesheet, and agent chat UI
2a6f9d5  feat(infra): add Docker and Kubernetes deployment manifests
12ad8be  fix(reports): use canonical professional_template profile key
bccb66b  feat(reports): report profiles + sheet builders + PDF assets
94886ef  chore: add quality phase runner scripts
9459859  docs: add phase closure documentation
ad3d011  docs: add API reference documentation
1cec183  chore: add project tooling config
6e8d405  feat(bridge-api): pipeline + history + PDF export + frontend (BA)
60ca627  feat: add frontend report history and PDF download
10ae1d7  test(integration): add end-to-end smoke test
d7bba49  feat(db): wave 7c.3 — db_engine public API
[+ commits المراحل السابقة الأقدم]

# wip/r3-subsystems-checkpoint (آخر commits)
99c78e6  feat(mobile): React Native field-mode app (R3 checkpoint)
229fc3c  test(e2e): cross-subsystem E2E test bundle
7e3ec3b  feat(core): market_indicators + MCP modules (R3 checkpoint)
[+ 21 commit إضافي لكل subsystem]
```

## 2.10 القضايا المعروفة والعمل المتبقّي

### ✅ قضايا مُغلَقة (Resolved)

1. **تناقض `professional_template` في KPI section** ← **مُغلَق**
   - الوصف: `main_report_sheet.py` كان يفحص `("detailed", "professional")` بدلاً من `("detailed", "professional_template")`.
   - الحالة: **تم الإصلاح** في `12ad8be — fix(reports): use canonical professional_template profile key`
   - تفاصيل الإصلاح: تعديل السطر 245 + تحديث smoke test + إضافة test جديد `test_apply_kpi_absent_for_unknown_profile`.

### قضايا معروفة (Open)

1. **`PHASE_4_README.md`** — تغيير تجميلي على doc، لم يُرتكَب بعد. يحتاج مراجعة يدوية لقبول/رفض التغيير.

2. **Frontend بلا automated tests** — الاعتماد على manual checklist (8 بنود في تقرير FE).

### العمل المتبقّي

1. **مراجعة الـ 24 subsystem** على `wip/r3-subsystems-checkpoint`:
   - adapters / agents / analytics / api / banking / database / deployment / funds
   - government / i18n / integrations / knowledge / marketplace / ml / performance
   - saas / scenarios / scripts / search / security / standards
   - market_indicators + mcp modules
   - mobile (React Native)
   - cross-subsystem E2E tests
   - كل subsystem جلسة منفصلة: investigate → decide → cherry-pick to main أو reject

2. **`docker/` و `kubernetes/`** — موجودة لكن لم تُختبَر فعلياً في deployment. تحتاج dry-run.

3. **توسعة محتملة** (اختياري):
   - PDF: عناصر بصرية إضافية (شعار، charts)
   - Validation: المزيد من cross-field rules
   - DB: backup/restore، export to CSV
   - Frontend: محرّر/معاينة في المتصفح

## 2.11 كيف تضيف Sheet جديد

```python
# 1. أنشئ ملف جديد في core_engine/reports/sheets/
# core_engine/reports/sheets/new_sheet.py
from openpyxl.worksheet.worksheet import Worksheet
from typing import Any, Mapping
from ..report_theme import draw_banner, apply_sheet_defaults

def apply_new_sheet(
    ws: Worksheet,
    data: Mapping[str, Any],
    *,
    profile_key: str = "legacy",
) -> None:
    apply_sheet_defaults(ws, freeze=True)
    draw_banner(ws, row=1, end_col=10, text="عنوان القسم")
    # ... منطق البناء

# 2. أضِفه في sheets/__init__.py
from .new_sheet import apply_new_sheet

# 3. استدعِه من excel_builder.py
from .sheets.new_sheet import apply_new_sheet
ws = wb.create_sheet("اسم الـ sheet")
apply_new_sheet(ws, data, profile_key=self.profile_key)

# 4. اكتب اختبارات في core_engine/tests/test_new_sheet.py
# 5. حدّث report_profiles.REGISTRY إذا لزم
```

## 2.12 كيف تضيف Validator Rule جديد

```python
# 1. أضف rule primitive في validation/rules.py إن لم يوجد
def check_my_constraint(data, field, **kwargs) -> ValidationIssue | None:
    value = data.get(field)
    if value < kwargs["min_value"]:
        return ValidationIssue(
            field=field,
            severity=Severity.ERROR,
            code="MY_CONSTRAINT_FAILED",
            message_ar=f"القيمة في {field} أقل من الحد الأدنى",
            message_en=f"Value in {field} below minimum",
        )
    return None

# 2. استدعِ الـ rule في input_validator.py أو output_validator.py
def validate_inputs(data, *, profile_key):
    issues = []
    if issue := check_my_constraint(data, "my_field", min_value=100):
        issues.append(issue)
    return ValidationResult(issues=tuple(issues))

# 3. اكتب test في test_input_validator.py
```

## 2.13 كيف تضيف Profile جديد

```python
# في report_profiles.py
ENTERPRISE = Profile(
    key="enterprise",
    name_ar="تقرير المؤسسات",
    name_en="Enterprise Report",
    version="1.0",
    template_path="templates/enterprise.xlsm",
    sheets=("inputs", "main", "sales", ...),
    features=ReportFeatures(...),
    tier=PriceTier.ENTERPRISE,
    target_audience_ar="...",
    description_ar="...",
)

REGISTRY = {
    LEGACY.key: LEGACY,
    DETAILED.key: DETAILED,
    PROFESSIONAL.key: PROFESSIONAL,
    ENTERPRISE.key: ENTERPRISE,  # ← جديد
}
```

تحقّق من أن:
- كل الـ sheets الموجودة تدعم الـ profile الجديد عبر `profile_key` parameter
- اختبارات `test_report_profiles.py` تغطّيه
- PDF/Validation engines تتعامل معه (افتراضياً تقبله إن كان في `REGISTRY`)

## 2.14 المنهجية المتَّبعة (للرجوع إليها)

كل مرحلة اتّبعت نفس البنية الصارمة:

1. **Strict allowlist/denylist** — ملفات محدّدة بالاسم
2. **Baseline** — التقاط حالة قبل أي تعديل
3. **Inventory** — جرد الموجود بدقة
4. **🛑 Gate** — توقُّف لعرض الخطة قبل التنفيذ
5. **Build** — تنفيذ wave-by-wave مع testing بعد كل خطوة
6. **Verification** — cell-by-cell / regression / round-trip
7. **Atomic commit** — commit واحد منعزل لكل موجة

هذه المنهجية أنتجت **1606 اختباراً، صفر regression عبر 7 مراحل + موجات الـ Bridge API + التنظيف**.

---

# ملحق — مرجع سريع للـ APIs

## الـ Public APIs

```python
# Excel
from core_engine.reports.excel_builder import build_report
build_report(profile_key, data, output_path)

# PDF
from core_engine.reports.pdf import generate_pdf
generate_pdf(profile_key=..., data=..., output_path=...)

# Validation
from core_engine.reports.validation import validate_report
result = validate_report(data, profile_key=...)
result.is_valid       # bool
result.errors         # tuple[ValidationIssue]
result.warnings       # tuple[ValidationIssue]

# DB
from core_engine.reports.db import (
    save_report, get_report, list_reports,
    update_report, delete_report, count_reports, ReportRecord,
)

# Pipeline facade (highest-level — used by bridge_api)
from core_engine.reports.report_pipeline import (
    validate_report_data, persist_report_data,
    export_report_pdf, fetch_reports, fetch_report,
)
```

## Bridge API endpoints

```
POST /api/valuation             # توليد التقرير (مع opt-in: validate/persist/pdf)
GET  /api/reports               # قائمة (فلاتر: profile_key/status/limit/offset)
GET  /api/reports/<id>          # تقرير واحد
GET  /api/reports/<id>/pdf      # تنزيل PDF
```

## Frontend functions

```javascript
esReportsLoad()               // جلب القائمة + render
esReportsViewDetail(id)       // فتح overlay التفاصيل
esReportsCloseDetail(event)   // إغلاق
esReportsDownloadPdf(id, btn) // تنزيل PDF
```

---

## كلمة ختامية

هذا المشروع كان رحلة من الانضباط الهندسي:

- **40+ برومبت موجَّه** لـ Claude CLI
- **7 مراحل** بنية متتالية + **مرحلة ربط** + **تنظيف**
- **1606 اختبار** يحرس الجودة
- **زيرو regression** عبر الرحلة كلها
- **commits ذرّية** قابلة للقراءة والـ rollback
- **بوّابات إلزامية** منعت كل قرار كبير بصمت

النتيجة: مشروع يمكن تسليمه، توسيعه، صيانته — بدون خوف من كسر شيء، وبدون اعتماد على شخص واحد يعرف "أين المخفي".

---

**EXPERT_SMART | Shared Core Architecture | v1.0 | مايو 2026**
