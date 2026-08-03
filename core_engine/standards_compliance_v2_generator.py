"""
Standards Compliance Report v2 — Deep Visual QA Generator
Axes A–G + H hooks. 30 clauses: IVS 2025 · RICS · USPAP · Basel III/IV · Taqyeem · AML
Case: QA-COMPLIANCE-VISUAL-001 · Saudi Arabia / Riyadh / SAR
"""
from __future__ import annotations

import datetime
import json
import math
import pathlib
import sys
import tempfile
from typing import Any

_CORE = pathlib.Path(__file__).parent
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

# ── Constants ─────────────────────────────────────────────────────────────────
GENERATOR_VERSION = "2.0.0"
CASE_ID           = "QA-COMPLIANCE-VISUAL-001"
CURRENCY          = "SAR"
LOCATION          = "الرياض"
COUNTRY           = "المملكة العربية السعودية"
REPORT_DATE       = "2026-07-27"
VALUATION_DATE    = "2024-01-15"

USER_WATERMARK  = "استرشادي — غير معتمد"
ADMIN_WATERMARK = "للمراجعة الداخلية فقط"
SIG_GATE        = "لم يُوقَّع بعد"

advisory_only             = True
certification_ready       = False
fake_signature_created    = False
non_certified             = True
not_real_training         = True
ml_suggestion_only        = True
ml_trained_on_approved_only = True
ml_auto_decision          = False
synthetic_data            = True

_OUT  = _CORE / "outputs" / "visual_qa_standards_compliance_v2"
_ARTS = _OUT / "artifacts"
_SS   = _OUT / "screenshots"
_AUD  = _OUT / "audits"

_PDF_SCREENSHOT_CAP = 76  # max pages captured per PDF; keeps total entries ≤ _DELETE_MAX_ENTRIES (200)

_SEV_W  = {"critical": 4, "high": 3, "medium": 2, "low": 1, "informational": 0.5, "not_applicable": 0}
_MAT_W  = {"material": 1.0, "non_material": 0.5, "not_applicable": 0.0}
_COMP_S = {"compliant": 1.0, "partially_compliant": 0.5, "non_compliant": 0.0,
           "not_applicable": None, "insufficient_evidence": 0.3, "not_assessed": 0.3}

_STATUS_AR = {
    "compliant": "متوافق", "partially_compliant": "متوافق جزئياً",
    "non_compliant": "غير متوافق", "not_applicable": "غير منطبق",
    "insufficient_evidence": "أدلة غير كافية", "not_assessed": "لم يُقيَّم",
}
_STATUS_COLOR = {
    "compliant": "#22c55e", "partially_compliant": "#f59e0b",
    "non_compliant": "#ef4444", "not_applicable": "#94a3b8",
    "insufficient_evidence": "#f97316", "not_assessed": "#cbd5e1",
}

# ── Clause helper ─────────────────────────────────────────────────────────────
def _c(std: str, cid: str, ref: str, title: str, req: str, status: str,
       sev: str, evs: list[str], findings: str, remediation: str,
       blocks: bool, mat: str = "material", conf: float = 0.80,
       owner: str = "مدقق الامتثال", deadline: str = "2024-09-01",
       pri: str = "P2", wf: str = "open") -> dict[str, Any]:
    sw = _SEV_W.get(sev, 1)
    mw = _MAT_W.get(mat, 1.0)
    return {
        "standard": std, "clause_id": cid, "clause_ref": ref,
        "title": title, "requirement": req, "status": status,
        "severity": sev, "evidence_refs": evs, "findings": findings,
        "remediation": remediation, "blocks_issuance": blocks,
        "materiality": mat, "confidence": conf, "owner": owner,
        "deadline": deadline, "priority": pri, "workflow_status": wf,
        "severity_weight": sw, "materiality_weight": mw,
        "retest_criterion": "مراجعة المستند المُحدَّث بعد الإصلاح",
        "closure_condition": "توافق الحالة مع المتطلب المعياري عند إعادة الفحص",
    }

# ── Dimension A — 30 clauses ──────────────────────────────────────────────────
IVS = "IVS 2025 (IVSC)"
RICS = "RICS 2022 (Red Book)"
USPAP = "USPAP 2024-2025 (TAF)"
BASEL = "Basel III/IV (BIS/BCBS)"
TAQYEEM = "هيئة تقييم (KSA)"
AML = "AML/CFT (FATF/SAMA)"

CLAUSES: list[dict[str, Any]] = [
    # ── IVS 2025 (10 clauses) ─────────────────────────────────────────────────
    _c(IVS, "IVS-101-SCOPE", "IVS 101 §3", "نطاق العمل",
       "يجب توثيق نطاق العمل توثيقاً كاملاً: الغرض · الأساس · الافتراضات · تاريخ التقييم.",
       "partially_compliant", "medium", ["E-001", "E-002"],
       "وثيقة نطاق العمل تفتقر إلى توثيق الافتراضات الخاصة وتحديد الغرض الاستخدامي بوضوح.",
       "إعادة صياغة قسم نطاق العمل ليشمل جميع عناصر IVS 101 §3.1–3.8.", False),

    _c(IVS, "IVS-102-INV", "IVS 102 §2", "التحقيق والامتثال",
       "يجب إجراء التحقيقات الكافية وتوثيق الامتثال لمتطلبات IVS.",
       "compliant", "medium", ["E-003"],
       "لا إيجادات — التحقيقات كافية ومُوثَّقة.",
       "لا إجراء مطلوب.", False),

    _c(IVS, "IVS-103-RPT", "IVS 103 §3", "متطلبات التقرير",
       "يجب أن يحتوي التقرير على جميع العناصر الإلزامية بموجب IVS 103.",
       "partially_compliant", "high", ["E-004", "E-005"],
       "القسم الخاص بعدم اليقين وحساسية القيمة غائب من التقرير.",
       "إضافة قسم عدم اليقين والحساسية وفق IVS 103 §3(i).", False,
       conf=0.85, pri="P1", wf="open"),

    _c(IVS, "IVS-104-BASES", "IVS 104 §2", "أسس القيمة",
       "يجب تحديد أساس القيمة المستخدم وتعريفه بدقة (قيمة سوقية · قيمة عادلة · غيرها).",
       "compliant", "medium", ["E-002"],
       "لا إيجادات — القيمة السوقية مُعرَّفة وفق IVS 104.", "لا إجراء مطلوب.", False),

    _c(IVS, "IVS-105-METHODS", "IVS 105 §3", "مناهج وطرق التقييم",
       "يجب تطبيق مناهج التقييم الملائمة وتبرير الاختيار.",
       "compliant", "high", ["E-006", "E-007"],
       "لا إيجادات — تم استخدام منهج المقارنة ومنهج الدخل مع تبرير واضح.",
       "لا إجراء مطلوب.", False, conf=0.90),

    _c(IVS, "IVS-230-REAL", "IVS 230 §2", "حقوق الملكية العقارية",
       "يجب توثيق طبيعة الحق العيني وتأثيره على القيمة.",
       "compliant", "medium", ["E-001", "E-008"],
       "لا إيجادات — حق الملكية الحرة مُوثَّق.", "لا إجراء مطلوب.", False),

    _c(IVS, "IVS-500-FIN", "IVS 500", "الأدوات المالية",
       "تنطبق متطلبات IVS 500 على الأدوات المالية عند وجودها.",
       "not_applicable", "low", [],
       "غير منطبق — لا أدوات مالية في نطاق هذا التقييم.",
       "لا إجراء مطلوب.", False, mat="not_applicable"),

    _c(IVS, "IVS-103-DISC", "IVS 103 §3(h)", "الإفصاحات الإلزامية",
       "يجب الإفصاح عن القيود وعدم اليقين والمعلومات المادية التي قد تؤثر على المستخدم.",
       "partially_compliant", "medium", ["E-004"],
       "قيد انعدام بيانات المقارنة الحديثة لم يُفصَح عنه صراحةً.",
       "إضافة فقرة إفصاح صريحة عن قيود البيانات وفق IVS 103 §3(h).", False,
       pri="P2", wf="open"),

    _c(IVS, "IVS-104-MKT", "IVS 104 §30", "القيمة السوقية — التعريف",
       "يجب أن يتوافق تعريف القيمة السوقية مع صياغة IVS 104 §30.",
       "compliant", "medium", ["E-002"],
       "لا إيجادات — التعريف متوافق.", "لا إجراء مطلوب.", False),

    _c(IVS, "IVS-102-COMP", "IVS 102 §4", "الكفاءة المهنية",
       "يجب أن يمتلك المقيّم الكفاءة اللازمة أو الاستعانة بخبير متخصص.",
       "compliant", "low", ["E-009"],
       "لا إيجادات — الكفاءة مُثبَتة.", "لا إجراء مطلوب.", False, mat="non_material"),

    # ── RICS 2022 (6 clauses) ─────────────────────────────────────────────────
    _c(RICS, "VPS-1-TERMS", "VPS 1", "شروط التكليف",
       "يجب توثيق جميع شروط التكليف المُتفَّق عليها مع العميل كتابةً.",
       "compliant", "medium", ["E-001", "E-003"],
       "لا إيجادات — شروط التكليف مُوثَّقة.", "لا إجراء مطلوب.", False),

    _c(RICS, "VPS-2-INSP", "VPS 2", "المعاينات والتحقيقات",
       "يجب إجراء معاينة كافية وتوثيق ملاحظات المعاينة الميدانية.",
       "compliant", "medium", ["E-008", "E-010"],
       "لا إيجادات — المعاينة الميدانية مُنجَزة ومُوثَّقة.", "لا إجراء مطلوب.", False),

    _c(RICS, "VPS-3-RPT", "VPS 3", "تقرير التقييم",
       "يجب أن يستوفي التقرير متطلبات محتوى VPS 3 ويتضمن جميع العناصر الإلزامية.",
       "partially_compliant", "high", ["E-004", "E-005"],
       "التقرير يفتقر إلى تحليل السوق الكافي وتبرير طريقة التقييم المختارة.",
       "تعزيز قسم تحليل السوق وإضافة تبرير منهجي وفق VPS 3.1(f).", False,
       pri="P1", wf="open"),

    _c(RICS, "VPS-4-BASES", "VPS 4", "أسس القيمة RICS",
       "يجب استخدام الأساس المناسب للقيمة وتعريفه صراحةً وفق RICS VPS 4.",
       "compliant", "medium", ["E-002"],
       "لا إيجادات — القيمة السوقية مُستخدَمة ومُعرَّفة.", "لا إجراء مطلوب.", False),

    _c(RICS, "VPS-5-ASSUMPTIONS", "VPS 5", "الافتراضات الخاصة",
       "يجب الإفصاح عن جميع الافتراضات الخاصة والافتراضات المقيَّدة والحصول على موافقة العميل.",
       "non_compliant", "high", ["E-004"],
       "الافتراضات الخاصة المتعلقة بحالة العقار والتحسينات لم تُفصَح عنها ولم تُوافَق عليها.",
       "توثيق جميع الافتراضات الخاصة وإرسالها للعميل للموافقة الكتابية قبل إصدار التقرير النهائي.",
       True, pri="P1", wf="open"),

    _c(RICS, "VPS-6-UNCERTAINTY", "VPS 6", "عدم اليقين في التقييم",
       "يجب الإفصاح عن أي عدم يقين مادي في القيمة وتوثيق أسبابه ونطاق تأثيره.",
       "non_compliant", "critical", ["E-004", "E-005"],
       "غياب تام لتوثيق عدم اليقين رغم شُح بيانات المقارنة وعدم استقرار السوق.",
       "إضافة قسم عدم اليقين: أسبابه · مدى تأثيره · النطاق الاسترشادي للقيمة وفق VPS 6.1.",
       True, pri="P1", wf="open"),

    # ── USPAP (4 clauses) ─────────────────────────────────────────────────────
    _c(USPAP, "USPAP-SR1", "SR-1", "تطوير تقييم العقار",
       "يُطبَّق USPAP SR-1 كمرجع دولي مقارن لمنهجية تطوير التقييم.",
       "partially_compliant", "medium", ["E-006", "E-007"],
       "تحليل السوق غير كافٍ مقارنةً بمتطلبات SR-1(a)(i).",
       "استكمال تحليل السوق وتوثيق الإجراء الكافي كمرجع استرشادي.", False,
       mat="material", pri="P2", wf="open"),

    _c(USPAP, "USPAP-SR2", "SR-2", "الإبلاغ عن تقييم العقار",
       "تقرير التقييم يجب أن يحتوي على جميع عناصر SR-2 كمرجع مقارن.",
       "partially_compliant", "medium", ["E-004", "E-005"],
       "بعض عناصر الإبلاغ الإلزامية غائبة مقارنةً بمعيار SR-2.",
       "مراجعة قائمة متطلبات SR-2(a)–(k) وإضافة العناصر الغائبة.", False,
       pri="P2", wf="open"),

    _c(USPAP, "USPAP-ETH", "Ethics Rule", "قاعدة الأخلاقيات",
       "يجب أن يلتزم المقيّم بقاعدة الأخلاقيات المهنية وعدم التحيز.",
       "compliant", "low", ["E-009"],
       "لا إيجادات — إعلان الاستقلالية والأخلاقيات حاضر.", "لا إجراء مطلوب.", False, mat="non_material"),

    _c(USPAP, "USPAP-COMP", "Competency Rule", "قاعدة الكفاءة",
       "يجب أن يمتلك المقيّم الكفاءة الجغرافية والنوعية للموضوع.",
       "compliant", "low", ["E-009"],
       "لا إيجادات — خبرة المقيّم في السوق السعودية مُثبَتة.", "لا إجراء مطلوب.", False, mat="non_material"),

    # ── Basel III/IV (4 clauses) ───────────────────────────────────────────────
    _c(BASEL, "BASEL-LTV", "CRR Art. 124-126",
       "نسبة القرض إلى القيمة (LTV)",
       "يجب ألا تتجاوز قيمة الضمان المُستخدَمة في احتساب LTV القيمةَ السوقية المُقدَّرة وفق Basel.",
       "compliant", "high", ["E-006"],
       "لا إيجادات — نسبة LTV محسوبة بالقيمة السوقية الحالية (70%).",
       "لا إجراء مطلوب.", False, conf=0.88),

    _c(BASEL, "BASEL-PCVC", "BCBS §228-229",
       "مفهوم القيمة التحوّطية (PCVC)",
       "يجب التحقق من أن القيمة المُقدَّرة تتوافق مع مبدأ الحيطة والتحفظ لأغراض الائتمان.",
       "partially_compliant", "high", ["E-006", "E-007"],
       "لم يُجرَ تحليل الحساسية المطلوب لإثبات القيمة التحوّطية.",
       "إضافة تحليل حساسية +/-10% مع توثيق القيمة التحوّطية وفق BCBS §229.", False,
       pri="P1", wf="open"),

    _c(BASEL, "BASEL-REVTRIG", "BCBS §526",
       "محفّزات إعادة التقييم",
       "يجب تحديد محفّزات إعادة التقييم وتوثيق أي تغييرات جوهرية في قيمة الضمان.",
       "not_assessed", "medium", ["E-006"],
       "لم يُحدَّد بوضوح جدول إعادة التقييم الدوري ومحفّزاته.",
       "توثيق جدول إعادة التقييم الدوري (سنوي كحد أدنى) ومحفّزاته الرئيسية.", False,
       conf=0.60, pri="P2", wf="open"),

    _c(BASEL, "BASEL-ORIGCAP", "BCBS Art. 164",
       "سقف قيمة النشأة",
       "لا تتجاوز القيمة المُستخدَمة لاحتساب LTV قيمةَ التقييم عند النشأة للقروض القائمة.",
       "compliant", "medium", ["E-006"],
       "لا إيجادات — القيمة الحالية أقل من قيمة النشأة المُسجَّلة.",
       "لا إجراء مطلوب.", False),

    # ── Saudi Taqyeem (4 clauses) ─────────────────────────────────────────────
    _c(TAQYEEM, "SA-ACC", "لائحة المقيّمين 1445",
       "اعتماد المقيّم — هيئة تقييم",
       "يجب أن يكون المقيّم معتمداً من هيئة تقييم وأن يكون الاعتماد سارياً.",
       "compliant", "critical", ["E-009"],
       "لا إيجادات — الاعتماد ساري والرقم مُوثَّق.", "لا إجراء مطلوب.", False, conf=0.95),

    _c(TAQYEEM, "SA-MORT", "نظام التمويل العقاري",
       "الامتثال لنظام التمويل العقاري (ساما)",
       "يجب أن يتوافق تقييم الضمان مع متطلبات ساما لنظام التمويل العقاري.",
       "compliant", "high", ["E-006", "E-010"],
       "لا إيجادات — التقييم مُستوفٍ لمتطلبات ساما.", "لا إجراء مطلوب.", False, conf=0.90),

    _c(TAQYEEM, "SA-IVS", "قانون التقييم 1443",
       "IVS كمعيار قانوني",
       "IVS معيار قانوني في المملكة العربية السعودية بموجب قانون التقييم 1443هـ.",
       "compliant", "medium", ["E-002", "E-003"],
       "لا إيجادات — التقرير مبني على IVS.", "لا إجراء مطلوب.", False),

    _c(TAQYEEM, "SA-DECL", "لائحة الاستقلالية",
       "إعلان الاستقلالية",
       "يجب أن يُعلن المقيّم استقلاليته عن الأطراف ذات المصلحة وعدم وجود تعارض.",
       "compliant", "medium", ["E-009"],
       "لا إيجادات — إعلان الاستقلالية مُضمَّن في التقرير.", "لا إجراء مطلوب.", False),

    # ── AML/CFT (2 clauses) ───────────────────────────────────────────────────
    _c(AML, "AML-IND", "FATF R.22 / SAMA AML",
       "استقلالية المقيّم عن المموّل",
       "يجب أن يكون المقيّم مستقلاً عن الجهة الممولة وعدم وجود علاقة تعارض مصالح.",
       "compliant", "medium", ["E-009"],
       "لا إيجادات — الاستقلالية عن الجهة الممولة مُؤكَّدة.", "لا إجراء مطلوب.", False),

    _c(AML, "AML-CFT", "FATF R.22 / نظام مكافحة غسل الأموال",
       "العناية الواجبة AML/CFT",
       "يجب على المقيّم التحقق من مشروعية الغرض من التقييم وعدم استخدامه في غسل الأموال.",
       "compliant", "medium", ["E-009"],
       "لا إيجادات — إجراءات العناية الواجبة مُطبَّقة.", "لا إجراء مطلوب.", False),
]

# ── Evidence register ──────────────────────────────────────────────────────────
EVIDENCE: list[dict[str, Any]] = [
    {"id": "E-001", "type": "deed",          "title": "صك الملكية",                   "sufficiency": "sufficient",    "custody": "محفوظ لدى عميل التقييم"},
    {"id": "E-002", "type": "report",        "title": "تقرير التقييم — المسودة",       "sufficiency": "insufficient",  "custody": "محفوظ لدى المقيّم"},
    {"id": "E-003", "type": "engagement",    "title": "خطاب التكليف",                  "sufficiency": "sufficient",    "custody": "محفوظ لدى شركة التقييم"},
    {"id": "E-004", "type": "report",        "title": "تقرير التقييم — الإصدار النهائي","sufficiency": "insufficient", "custody": "محفوظ لدى المقيّم"},
    {"id": "E-005", "type": "market",        "title": "تحليل السوق المحلي",            "sufficiency": "insufficient",  "custody": "محفوظ لدى المقيّم"},
    {"id": "E-006", "type": "financial",     "title": "ملف القرض — بيانات LTV",       "sufficiency": "sufficient",    "custody": "محفوظ لدى البنك"},
    {"id": "E-007", "type": "comparables",   "title": "بيانات المبيعات المقارنة",      "sufficiency": "insufficient",  "custody": "محفوظ لدى المقيّم"},
    {"id": "E-008", "type": "inspection",    "title": "تقرير المعاينة الميدانية",      "sufficiency": "sufficient",    "custody": "محفوظ لدى المقيّم"},
    {"id": "E-009", "type": "accreditation", "title": "شهادة اعتماد هيئة تقييم",      "sufficiency": "sufficient",    "custody": "محفوظ لدى شركة التقييم"},
    {"id": "E-010", "type": "photos",        "title": "صور المعاينة الميدانية",        "sufficiency": "sufficient",    "custody": "محفوظ لدى المقيّم"},
]

# ── Temporal audit trail ───────────────────────────────────────────────────────
AUDIT_TRAIL: list[dict[str, Any]] = [
    {"event": "تكليف",   "date": "2024-01-01", "actor": "البنك الممول",    "note": "تكليف رسمي بإجراء تقييم ضمان القرض العقاري"},
    {"event": "معاينة",  "date": "2024-01-15", "actor": "المقيّم",         "note": "معاينة ميدانية للعقار وتوثيق الحالة والمساحة"},
    {"event": "تحليل",   "date": "2024-01-22", "actor": "المقيّم",         "note": "تحليل بيانات السوق المحلي وانتقاء المقارنات"},
    {"event": "تسليم",   "date": "2024-02-01", "actor": "المقيّم",         "note": "تسليم مسودة التقرير للعميل للمراجعة"},
    {"event": "مراجعة",  "date": "2024-02-15", "actor": "مدقق الامتثال",   "note": "بدء مراجعة الامتثال للمعايير التنظيمية"},
    {"event": "QA",      "date": "2024-03-01", "actor": "مدقق الجودة",      "note": "فحص جودة التقرير والمخرجات — حالة QA-COMPLIANCE-VISUAL-001"},
    {"event": "إشعار",   "date": "2024-03-10", "actor": "مدقق الامتثال",   "note": "إخطار المقيّم بالإيجادات المطلوب إصلاحها"},
]

# ── Workflow items ─────────────────────────────────────────────────────────────
WORKFLOW_ITEMS: list[dict[str, Any]] = [
    {"clause_id": "VPS-6-UNCERTAINTY", "owner": "المقيّم الرئيسي", "deadline": "2024-04-01", "priority": "P1",
     "status": "open", "retest": "مراجعة قسم عدم اليقين المُضاف", "closure": "قسم عدم اليقين مُستوفٍ لـ VPS 6.1"},
    {"clause_id": "VPS-5-ASSUMPTIONS", "owner": "المقيّم الرئيسي", "deadline": "2024-04-01", "priority": "P1",
     "status": "open", "retest": "التحقق من موافقة العميل الكتابية على الافتراضات", "closure": "موافقة موقّعة متاحة"},
    {"clause_id": "IVS-103-RPT",       "owner": "المقيّم الرئيسي", "deadline": "2024-04-15", "priority": "P1",
     "status": "open", "retest": "إعادة فحص قسم الإفصاح", "closure": "جميع عناصر IVS 103 §3 موجودة"},
    {"clause_id": "VPS-3-RPT",         "owner": "المقيّم الرئيسي", "deadline": "2024-04-15", "priority": "P1",
     "status": "open", "retest": "مراجعة قسم تحليل السوق", "closure": "تحليل سوق كامل وفق VPS 3.1(f)"},
    {"clause_id": "BASEL-PCVC",        "owner": "مدقق الائتمان",   "deadline": "2024-05-01", "priority": "P1",
     "status": "open", "retest": "مراجعة تحليل الحساسية المُرفَق", "closure": "تحليل حساسية موثّق ضمن التقرير"},
    {"clause_id": "IVS-103-DISC",      "owner": "المقيّم الرئيسي", "deadline": "2024-05-01", "priority": "P2",
     "status": "open", "retest": "فحص فقرة الإفصاح عن القيود", "closure": "إفصاح صريح عن قيود البيانات"},
    {"clause_id": "USPAP-SR1",         "owner": "مدقق الامتثال",   "deadline": "2024-05-15", "priority": "P2",
     "status": "open", "retest": "مراجعة تحليل السوق بالمرجع المقارن", "closure": "تحليل كافٍ بالمرجع SR-1"},
    {"clause_id": "BASEL-REVTRIG",     "owner": "مدقق الائتمان",   "deadline": "2024-06-01", "priority": "P2",
     "status": "open", "retest": "التحقق من وجود جدول إعادة التقييم", "closure": "جدول إعادة التقييم مُوثَّق"},
]

# ── Auditor opinion ────────────────────────────────────────────────────────────
AUDITOR_OPINION: dict[str, Any] = {
    "basis": (
        "بناءً على مراجعة تقرير التقييم الصادر بتاريخ 15 يناير 2024 وفق أُطر IVS 2025 وRICS Red Book 2022 "
        "وUSPAP وBasel III/IV ومتطلبات هيئة تقييم ومكافحة غسل الأموال، يرى مدقق الامتثال ما يلي:"
    ),
    "reservations": [
        "إيجاد حرج (VPS-6): غياب توثيق عدم اليقين رغم شُح المقارنات وعدم استقرار السوق.",
        "إيجاد عالٍ (VPS-5): عدم الإفصاح عن الافتراضات الخاصة للحصول على موافقة العميل.",
        "إيجاد عالٍ (IVS-103/VPS-3): نقص في قسم تحليل السوق والإفصاح الإلزامي.",
        "إيجاد عالٍ (BASEL-PCVC): غياب تحليل الحساسية المطلوب لإثبات القيمة التحوّطية.",
    ],
    "conditions": [
        "إضافة قسم عدم اليقين الكامل وفق VPS 6.1 قبل الاعتماد.",
        "توثيق الافتراضات الخاصة والحصول على موافقة العميل الكتابية.",
        "استكمال تحليل السوق وإضافة الإفصاحات الإلزامية.",
        "إرفاق تحليل حساسية +/-10% لإثبات القيمة التحوّطية.",
    ],
    "bank_credit_impact": "مشروط",
    "bank_credit_impact_en": "conditional",
    "bank_credit_rationale": (
        "التقرير غير مستوفٍ لمتطلبات VPS-5 وVPS-6 وBasel PCVC — لا يُقبَل كضمان ائتماني إلا بعد رفع "
        "إيجادات الحجب الثلاثة المذكورة أعلاه وإعادة مراجعة من مدقق امتثال معتمَد."
    ),
    "issuance_status": "مشروط — معلّق على رفع الإيجادات الحارجة",
    "advisory_note": "هذا الرأي استرشادي ولا يُعتمد إلا بتوقيع مدقق بشري معتمَد.",
}

# ── Score computation ──────────────────────────────────────────────────────────
def _compute_score_v2(clauses: list[dict[str, Any]]) -> dict[str, Any]:
    earned = 0.0
    maximum = 0.0
    std_earned: dict[str, float] = {}
    std_max: dict[str, float]    = {}
    blocking: list[str] = []
    critical: list[str] = []

    for cl in clauses:
        comp_s = _COMP_S.get(cl["status"])
        if comp_s is None:
            continue
        sw = cl.get("severity_weight", 1)
        mw = cl.get("materiality_weight", 1.0)
        weight = sw * mw
        earned  += comp_s * weight
        maximum += weight

        std = cl["standard"]
        std_earned.setdefault(std, 0.0)
        std_max.setdefault(std, 0.0)
        std_earned[std] += comp_s * weight
        std_max[std]    += weight

        if cl.get("blocks_issuance") and cl["status"] not in ("compliant", "not_applicable"):
            blocking.append(cl["clause_id"])
        if cl.get("severity") == "critical" and cl["status"] not in ("compliant", "not_applicable"):
            critical.append(cl["clause_id"])

    pct = round(earned / maximum * 100) if maximum > 0 else 0
    tl  = "green" if pct >= 80 else ("yellow" if pct >= 50 else "red")
    lbl_map = {"green": "متوافق", "yellow": "متوافق جزئياً", "red": "غير متوافق"}

    std_scores: dict[str, Any] = {}
    for std in std_earned:
        mx = std_max[std]
        ep = round(std_earned[std] / mx * 100) if mx > 0 else 0
        std_scores[std] = {"earned": round(std_earned[std], 2), "max": round(mx, 2), "pct": ep}

    app = sum(1 for cl in clauses if _COMP_S.get(cl["status"]) is not None)
    return {
        "applicable_clauses": app,
        "total_clauses": len(clauses),
        "raw_weighted_score": round(earned, 2),
        "max_weighted_score": round(maximum, 2),
        "percentage": pct,
        "traffic_light": tl,
        "label": lbl_map.get(tl, ""),
        "blocks_issuance": blocking,
        "critical_findings": critical,
        "standard_scores": std_scores,
    }

SCORE_V2: dict[str, Any] = _compute_score_v2(CLAUSES)

# ── CSS (shared base) ─────────────────────────────────────────────────────────
_CSS_BASE = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Tahoma,'Arial',sans-serif;direction:rtl;background:#f8fafc;color:#1e293b;font-size:14px;line-height:1.7}
.page{max-width:1100px;margin:0 auto;padding:24px}
h1{font-size:1.7rem;font-weight:700;color:#1e3a5f;margin-bottom:8px}
h2{font-size:1.25rem;font-weight:700;color:#1e3a5f;margin:28px 0 10px;border-bottom:2px solid #cbd5e1;padding-bottom:6px}
h3{font-size:1rem;font-weight:700;color:#334155;margin:16px 0 6px}
table{width:100%;border-collapse:collapse;margin-bottom:16px;font-size:13px}
th{background:#1e3a5f;color:#fff;padding:8px 10px;text-align:right}
td{padding:7px 10px;border-bottom:1px solid #e2e8f0;vertical-align:top}
tr:nth-child(even) td{background:#f1f5f9}
.badge{display:inline-block;padding:3px 10px;border-radius:12px;font-size:12px;font-weight:700;color:#fff}
.badge-compliant{background:#22c55e}
.badge-partial{background:#f59e0b}
.badge-noncompliant{background:#ef4444}
.badge-na{background:#94a3b8}
.badge-notassessed{background:#cbd5e1;color:#475569}
.score-box{display:flex;gap:16px;flex-wrap:wrap;margin:16px 0}
.score-card{background:#fff;border-radius:10px;padding:16px 24px;box-shadow:0 1px 4px rgba(0,0,0,.08);min-width:180px;text-align:center}
.score-num{font-size:2.2rem;font-weight:700;color:#1e3a5f}
.score-lbl{font-size:13px;color:#64748b;margin-top:4px}
.tl-green{color:#16a34a}
.tl-yellow{color:#d97706}
.tl-red{color:#dc2626}
.finding-block{background:#fff;border-right:4px solid #ef4444;border-radius:6px;padding:12px 16px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.finding-block.high{border-color:#f97316}
.finding-block.medium{border-color:#f59e0b}
.finding-block.low{border-color:#22c55e}
.watermark{position:fixed;bottom:40px;left:50%;transform:translateX(-50%);font-size:20px;color:rgba(200,50,50,.18);font-weight:700;pointer-events:none;z-index:9999;white-space:nowrap}
.sig-box{margin:24px 0;padding:16px;background:#fff3cd;border:2px dashed #f59e0b;border-radius:8px;text-align:center;font-size:1.1rem;font-weight:700;color:#92400e}
.admin-only-marker{border-right:4px solid #7c3aed;background:#faf5ff;border-radius:6px;padding:12px 16px;margin-bottom:10px}
.chart-wrap{margin:20px 0;text-align:center}
.provenance-tier-platform{color:#16a34a;font-weight:700}
.provenance-tier-document{color:#2563eb;font-weight:700}
.provenance-tier-draft_web{color:#d97706;font-weight:700}
.provenance-tier-unavailable{color:#94a3b8}
.ml-draft-tag{display:inline-block;background:#fef3c7;color:#92400e;border:1px solid #fbbf24;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;margin-right:6px}
.advisory_only{display:none}
section{margin-bottom:32px}
"""

# ── SVG charts ────────────────────────────────────────────────────────────────

def _svg_heatmap(clauses: list[dict[str, Any]]) -> str:
    """Compliance heatmap: rows = standard groups, cols = severity levels."""
    standards = [IVS, RICS, USPAP, BASEL, TAQYEEM, AML]
    std_short = {"IVS 2025 (IVSC)": "IVS 2025", "RICS 2022 (Red Book)": "RICS",
                 "USPAP 2024-2025 (TAF)": "USPAP", "Basel III/IV (BIS/BCBS)": "Basel",
                 "هيئة تقييم (KSA)": "Taqyeem", "AML/CFT (FATF/SAMA)": "AML"}
    sevs = ["critical", "high", "medium", "low"]
    sev_ar = {"critical": "حرج", "high": "عالٍ", "medium": "متوسط", "low": "منخفض"}

    cell_w, cell_h, lbl_w = 80, 36, 90
    cols = len(sevs)
    rows = len(standards)
    W = lbl_w + cols * cell_w + 20
    H = 40 + rows * cell_h + 20

    svg = [f'<svg width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg" style="font-family:Tahoma,Arial;direction:ltr">']
    svg.append(f'<text x="{W//2}" y="20" text-anchor="middle" font-size="13" font-weight="bold" fill="#1e3a5f">خريطة حرارية — الامتثال (معيار × خطورة)</text>')

    for ci, sev in enumerate(sevs):
        x = lbl_w + ci * cell_w + cell_w // 2
        svg.append(f'<text x="{x}" y="38" text-anchor="middle" font-size="11" fill="#475569">{sev_ar[sev]}</text>')

    for ri, std in enumerate(standards):
        y = 44 + ri * cell_h
        short = std_short.get(std, std[:8])
        svg.append(f'<text x="{lbl_w - 4}" y="{y + cell_h//2 + 4}" text-anchor="end" font-size="11" fill="#334155">{short}</text>')

        for ci, sev in enumerate(sevs):
            matching = [cl for cl in clauses if cl["standard"] == std and cl["severity"] == sev]
            if not matching:
                color = "#f1f5f9"
            else:
                statuses = [cl["status"] for cl in matching]
                if any(s == "non_compliant" for s in statuses):
                    color = "#fca5a5"
                elif any(s == "partially_compliant" for s in statuses):
                    color = "#fde68a"
                elif all(s in ("compliant",) for s in statuses):
                    color = "#bbf7d0"
                else:
                    color = "#e2e8f0"
            x = lbl_w + ci * cell_w
            cnt = len(matching)
            cnt_txt = str(cnt) if cnt else ""
            svg.append(f'<rect x="{x+2}" y="{y+2}" width="{cell_w-4}" height="{cell_h-4}" rx="4" fill="{color}" stroke="#cbd5e1" stroke-width="0.5"/>')
            if cnt_txt:
                svg.append(f'<text x="{x+cell_w//2}" y="{y+cell_h//2+4}" text-anchor="middle" font-size="12" fill="#1e293b">{cnt_txt}</text>')

    svg.append("</svg>")
    return "\n".join(svg)


def _svg_radar(std_scores: dict[str, Any]) -> str:
    """Radar chart showing compliance % by standard."""
    labels = {IVS: "IVS 2025", RICS: "RICS", USPAP: "USPAP",
              BASEL: "Basel", TAQYEEM: "Taqyeem", AML: "AML"}
    keys = list(labels.keys())
    n = len(keys)
    cx, cy, R = 200, 200, 140
    W, H = 420, 420

    def pt(i: int, r: float) -> tuple[float, float]:
        angle = math.pi / 2 - 2 * math.pi * i / n
        return cx + r * math.cos(angle), cy - r * math.sin(angle)

    svg = [f'<svg width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg" style="font-family:Tahoma,Arial">']
    svg.append(f'<text x="{W//2}" y="18" text-anchor="middle" font-size="13" font-weight="bold" fill="#1e3a5f">رادار الامتثال بالمعيار</text>')

    for level in [0.25, 0.5, 0.75, 1.0]:
        pts = [pt(i, R * level) for i in range(n)]
        poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        svg.append(f'<polygon points="{poly}" fill="none" stroke="#e2e8f0" stroke-width="1"/>')

    for i in range(n):
        x1, y1 = pt(i, 0)
        x2, y2 = pt(i, R)
        svg.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#e2e8f0" stroke-width="1"/>')

    data_pts = []
    for i, key in enumerate(keys):
        pct = std_scores.get(key, {}).get("pct", 0) / 100.0
        x, y = pt(i, R * pct)
        data_pts.append((x, y))
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in data_pts)
    svg.append(f'<polygon points="{poly}" fill="rgba(30,58,95,0.18)" stroke="#1e3a5f" stroke-width="2"/>')
    for x, y in data_pts:
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#1e3a5f"/>')

    for i, key in enumerate(keys):
        x, y = pt(i, R + 22)
        pct = std_scores.get(key, {}).get("pct", 0)
        lbl = labels.get(key, key[:6])
        anchor = "middle"
        svg.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="11" fill="#334155">{lbl} {pct}%</text>')

    svg.append("</svg>")
    return "\n".join(svg)


def _svg_rag_bar(clauses: list[dict[str, Any]]) -> str:
    """RAG distribution horizontal bar chart."""
    counts = {"compliant": 0, "partially_compliant": 0, "non_compliant": 0,
              "not_applicable": 0, "not_assessed": 0, "insufficient_evidence": 0}
    for cl in clauses:
        s = cl["status"]
        if s in counts:
            counts[s] += 1

    items = [
        ("متوافق",          counts["compliant"],             "#22c55e"),
        ("متوافق جزئياً",   counts["partially_compliant"],   "#f59e0b"),
        ("غير متوافق",      counts["non_compliant"],         "#ef4444"),
        ("غير منطبق",       counts["not_applicable"],        "#94a3b8"),
        ("لم يُقيَّم",      counts["not_assessed"],          "#cbd5e1"),
    ]
    total = len(clauses)
    W, bar_h, gap, lbl_w = 500, 32, 8, 120
    H = len(items) * (bar_h + gap) + 50

    svg = [f'<svg width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg" style="font-family:Tahoma,Arial;direction:rtl">']
    svg.append(f'<text x="{W//2}" y="18" text-anchor="middle" font-size="13" font-weight="bold" fill="#1e3a5f">توزيع RAG — {total} بنداً</text>')

    max_count = max(c for _, c, _ in items) or 1
    bar_area = W - lbl_w - 60

    for i, (lbl, cnt, color) in enumerate(items):
        y = 28 + i * (bar_h + gap)
        bar_w = int(bar_area * cnt / max_count) if cnt else 0
        svg.append(f'<text x="{lbl_w - 4}" y="{y + bar_h//2 + 4}" text-anchor="end" font-size="11" fill="#334155">{lbl}</text>')
        svg.append(f'<rect x="{lbl_w}" y="{y}" width="{bar_w}" height="{bar_h}" rx="4" fill="{color}"/>')
        if cnt:
            txt_x = lbl_w + bar_w + 6
            svg.append(f'<text x="{txt_x}" y="{y + bar_h//2 + 4}" font-size="12" fill="#1e293b">{cnt}</text>')

    svg.append("</svg>")
    return "\n".join(svg)


def _svg_trend(history: list[dict[str, Any]]) -> str:
    """Temporal trend line (score history). Seeds with current score if empty."""
    if not history:
        history = [{"date": REPORT_DATE, "pct": SCORE_V2["percentage"], "label": "القياس الحالي"}]

    W, H, pad_l, pad_r, pad_t, pad_b = 500, 200, 60, 30, 30, 40
    plot_w = W - pad_l - pad_r
    plot_h = H - pad_t - pad_b
    n = len(history)

    svg = [f'<svg width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg" style="font-family:Tahoma,Arial">']
    svg.append(f'<text x="{W//2}" y="18" text-anchor="middle" font-size="13" font-weight="bold" fill="#1e3a5f">الاتجاه الزمني — درجة الامتثال</text>')

    for level in [0, 25, 50, 75, 100]:
        y = pad_t + plot_h - int(plot_h * level / 100)
        svg.append(f'<line x1="{pad_l}" y1="{y}" x2="{pad_l + plot_w}" y2="{y}" stroke="#e2e8f0" stroke-width="1" stroke-dasharray="4,3"/>')
        svg.append(f'<text x="{pad_l - 6}" y="{y + 4}" text-anchor="end" font-size="10" fill="#94a3b8">{level}%</text>')

    if n == 1:
        x = pad_l + plot_w // 2
        pct = history[0]["pct"]
        y = pad_t + plot_h - int(plot_h * pct / 100)
        svg.append(f'<circle cx="{x}" cy="{y}" r="7" fill="#1e3a5f"/>')
        svg.append(f'<text x="{x}" y="{y - 12}" text-anchor="middle" font-size="12" fill="#1e3a5f">{pct}%</text>')
        svg.append(f'<text x="{x}" y="{H - 8}" text-anchor="middle" font-size="10" fill="#64748b">{history[0]["date"]}</text>')
    else:
        pts = []
        for j, item in enumerate(history):
            x = pad_l + int(plot_w * j / (n - 1))
            y = pad_t + plot_h - int(plot_h * item["pct"] / 100)
            pts.append((x, y, item))
        poly = " ".join(f"{x},{y}" for x, y, _ in pts)
        svg.append(f'<polyline points="{poly}" fill="none" stroke="#1e3a5f" stroke-width="2"/>')
        for x, y, item in pts:
            svg.append(f'<circle cx="{x}" cy="{y}" r="5" fill="#1e3a5f"/>')
            svg.append(f'<text x="{x}" y="{y - 10}" text-anchor="middle" font-size="11" fill="#1e3a5f">{item["pct"]}%</text>')
            svg.append(f'<text x="{x}" y="{H - 8}" text-anchor="middle" font-size="9" fill="#64748b">{item["date"]}</text>')

    svg.append("</svg>")
    return "\n".join(svg)


def _svg_ml_curve(curve: list[dict[str, Any]]) -> str:
    """ML improvement curve (validation accuracy per model version)."""
    if not curve:
        W, H = 400, 120
        svg = [f'<svg width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg" style="font-family:Tahoma,Arial">']
        svg.append(f'<text x="{W//2}" y="50" text-anchor="middle" font-size="13" fill="#94a3b8">منحنى تحسّن ML — لا بيانات بعد</text>')
        svg.append(f'<text x="{W//2}" y="74" text-anchor="middle" font-size="11" fill="#cbd5e1">النموذج غير جاهز — بيانات معتمدة غير كافية</text>')
        svg.append("</svg>")
        return "\n".join(svg)

    W, H = 500, 200
    pad_l, pad_r, pad_t, pad_b = 60, 30, 30, 40
    plot_w = W - pad_l - pad_r
    plot_h = H - pad_t - pad_b
    n = len(curve)
    thresh = 0.65

    svg = [f'<svg width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg" style="font-family:Tahoma,Arial">']
    svg.append(f'<text x="{W//2}" y="18" text-anchor="middle" font-size="13" font-weight="bold" fill="#1e3a5f">منحنى تحسّن ML — دقة التحقق لكل إصدار</text>')

    thresh_y = pad_t + plot_h - int(plot_h * thresh)
    svg.append(f'<line x1="{pad_l}" y1="{thresh_y}" x2="{pad_l+plot_w}" y2="{thresh_y}" stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="6,3"/>')
    svg.append(f'<text x="{pad_l+plot_w+4}" y="{thresh_y+4}" font-size="10" fill="#d97706">عتبة {int(thresh*100)}%</text>')

    pts = []
    for j, item in enumerate(curve):
        x = pad_l + int(plot_w * j / max(n - 1, 1))
        y = pad_t + plot_h - int(plot_h * item["validation_accuracy"])
        pts.append((x, y, item))

    if len(pts) > 1:
        poly = " ".join(f"{x},{y}" for x, y, _ in pts)
        svg.append(f'<polyline points="{poly}" fill="none" stroke="#7c3aed" stroke-width="2"/>')
    for x, y, item in pts:
        color = "#7c3aed" if item["threshold_passed"] else "#94a3b8"
        svg.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{color}"/>')
        acc_pct = int(item["validation_accuracy"] * 100)
        svg.append(f'<text x="{x}" y="{y - 10}" text-anchor="middle" font-size="11" fill="{color}">{acc_pct}%</text>')
        svg.append(f'<text x="{x}" y="{H - 8}" text-anchor="middle" font-size="9" fill="#64748b">v{item["version"]}</text>')

    svg.append("</svg>")
    return "\n".join(svg)


# ── Badge helper ───────────────────────────────────────────────────────────────
def _badge(status: str) -> str:
    cls_map = {
        "compliant": "badge-compliant", "partially_compliant": "badge-partial",
        "non_compliant": "badge-noncompliant", "not_applicable": "badge-na",
        "not_assessed": "badge-notassessed", "insufficient_evidence": "badge-notassessed",
    }
    css = cls_map.get(status, "badge-na")
    ar  = _STATUS_AR.get(status, status)
    return f'<span class="badge {css}">{ar}</span>'


def _clauses_table(clauses: list[dict[str, Any]]) -> str:
    rows = []
    for cl in clauses:
        wf_color = "#ef4444" if cl["workflow_status"] == "open" else (
            "#f59e0b" if cl["workflow_status"] == "in_progress" else "#22c55e")
        findings_html = cl["findings"] if cl["findings"] else "—"
        block_icon = "🔴" if cl.get("blocks_issuance") else ""
        rows.append(
            f'<tr><td><strong>{cl["clause_id"]}</strong><br>'
            f'<small style="color:#64748b">{cl["clause_ref"]}</small></td>'
            f'<td>{cl["title"]}</td>'
            f'<td>{_badge(cl["status"])} {block_icon}</td>'
            f'<td>{cl["severity"]}</td>'
            f'<td>{findings_html}</td>'
            f'<td style="color:{wf_color};font-size:12px">{cl["workflow_status"]}</td></tr>'
        )
    return (
        '<table><thead><tr><th>البند</th><th>العنوان</th><th>الحالة</th>'
        '<th>الخطورة</th><th>الإيجادات</th><th>سير العمل</th></tr></thead><tbody>'
        + "".join(rows) + "</tbody></table>"
    )


def _build_user_html(
    score: dict[str, Any],
    ml_suggestion: dict[str, Any] | None = None,
) -> str:
    pct     = score["percentage"]
    tl      = score["traffic_light"]
    tl_icon = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(tl, "⚪")
    label   = score["label"]
    blocking = score["blocks_issuance"]
    critical = score["critical_findings"]

    heatmap = _svg_heatmap(CLAUSES)
    radar   = _svg_radar(score.get("standard_scores", {}))
    rag     = _svg_rag_bar(CLAUSES)
    trend   = _svg_trend([])
    ml_curve = _svg_ml_curve([])

    # group clauses by standard
    def cls_section(std_name: str, std_key: str) -> str:
        group = [cl for cl in CLAUSES if cl["standard"] == std_key]
        return f"<h2>{std_name}</h2>" + _clauses_table(group)

    cond_rows = "".join(
        f"<li style='margin-bottom:6px'>{c}</li>"
        for c in AUDITOR_OPINION["conditions"]
    )
    reserv_rows = "".join(
        f"<li style='margin-bottom:6px'>{r}</li>"
        for r in AUDITOR_OPINION["reservations"]
    )
    blocking_li = "".join(f"<li>{b}</li>" for b in blocking) if blocking else "<li>لا يوجد</li>"
    critical_li = "".join(f"<li>{c}</li>" for c in critical) if critical else "<li>لا يوجد</li>"

    std_scores_rows = "".join(
        f'<tr><td>{k}</td><td>{v["pct"]}%</td>'
        f'<td><div style="height:14px;width:{v["pct"]*2}px;background:#1e3a5f;border-radius:4px"></div></td></tr>'
        for k, v in score.get("standard_scores", {}).items()
    )

    ml_block = ""
    if ml_suggestion:
        if ml_suggestion.get("status") == "draft":
            ml_block = (
                f'<div class="finding-block medium" style="border-color:#7c3aed">'
                f'<span class="ml-draft-tag">اقتراح ML — Draft</span>'
                f'<strong>اقتراح تعلّم آلي استرشادي:</strong> {ml_suggestion.get("suggestion_ar","")}'
                f' (ثقة: {int(ml_suggestion.get("confidence",0)*100)}%)<br>'
                f'<small style="color:#92400e">{ml_suggestion.get("advisory","")}</small></div>'
            )
        else:
            ml_block = (
                f'<div class="finding-block low" style="border-color:#94a3b8">'
                f'<span class="ml-draft-tag">اقتراح ML</span>'
                f'{ml_suggestion.get("message","النموذج غير جاهز — بيانات معتمدة غير كافية")}</div>'
            )

    return f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head><meta charset="UTF-8">
<title>تقرير الامتثال — {CASE_ID}</title>
<style>{_CSS_BASE}</style>
</head>
<body>
<div class="watermark">{USER_WATERMARK}</div>
<div class="page">
<h1>تقرير امتثال المعايير التنظيمية — الإصدار الثاني</h1>
<p style="color:#64748b;font-size:13px">الحالة: <strong>{CASE_ID}</strong> · التاريخ: {REPORT_DATE} · العملة: {CURRENCY} · الموقع: {LOCATION} · {COUNTRY}</p>
<p style="color:#92400e;font-size:12px;margin:4px 0"><em>استرشادي — غير معتمد — لا يُعتمد إلا بتوقيع مدقق بشري معتمَد · advisory_only=True</em></p>

<section>
<h2>الملخص التنفيذي</h2>
<div class="score-box">
  <div class="score-card"><div class="score-num tl-{tl}">{pct}%</div><div class="score-lbl">{tl_icon} {label}</div></div>
  <div class="score-card"><div class="score-num">{score["applicable_clauses"]}</div><div class="score-lbl">بنداً قابلاً للتقييم</div></div>
  <div class="score-card"><div class="score-num">{score["total_clauses"]}</div><div class="score-lbl">إجمالي البنود</div></div>
  <div class="score-card"><div class="score-num" style="color:#ef4444">{len(blocking)}</div><div class="score-lbl">تحجب الإصدار</div></div>
</div>
<table><thead><tr><th>المعيار</th><th>النسبة المرجّحة</th><th>شريط التقدّم</th></tr></thead><tbody>
{std_scores_rows}
</tbody></table>
<h3>بنود تحجب الإصدار</h3><ul>{blocking_li}</ul>
<h3>الإيجادات الحرجة</h3><ul>{critical_li}</ul>
</section>

<section>
{cls_section("IVS 2025 (IVSC) — معيار التقييم الدولي", IVS)}
</section>
<section>
{cls_section("RICS 2022 (Red Book) — المعيار الأحمر البريطاني", RICS)}
</section>
<section>
{cls_section("USPAP 2024-2025 — المعيار الأمريكي (مرجع مقارن)", USPAP)}
</section>
<section>
{cls_section("Basel III/IV — متطلبات الضمانات البنكية", BASEL)}
</section>
<section>
{cls_section("هيئة تقييم (KSA) — المتطلبات السعودية", TAQYEEM)}
</section>
<section>
{cls_section("AML/CFT — مكافحة غسل الأموال", AML)}
</section>

<section>
<h2>الرأي التدقيقي</h2>
<p>{AUDITOR_OPINION["basis"]}</p>
<h3>التحفّظات</h3><ul>{reserv_rows}</ul>
<h3>شروط رفع الحجب</h3><ol>{cond_rows}</ol>
<h3>أثر القرار البنكي</h3>
<p><strong>الحكم:</strong> {AUDITOR_OPINION["bank_credit_impact"]} (<em>{AUDITOR_OPINION["bank_credit_impact_en"]}</em>)</p>
<p>{AUDITOR_OPINION["bank_credit_rationale"]}</p>
<p style="font-size:12px;color:#92400e"><em>{AUDITOR_OPINION["advisory_note"]}</em></p>
</section>

<section>
<h2>الرسوم التحليلية</h2>
<div class="chart-wrap">{heatmap}</div>
<div class="chart-wrap">{radar}</div>
<div class="chart-wrap">{rag}</div>
<div class="chart-wrap">{trend}</div>
</section>

<section>
<h2>اقتراحات التعلّم الآلي (استرشادية — Draft)</h2>
<p style="font-size:12px;color:#92400e"><em>اقتراحات تعلّم آلي — استرشادية — لا تُعتمد إلا بمراجعة مدقّق بشري</em></p>
{ml_block if ml_block else '<p style="color:#94a3b8">النموذج غير جاهز — بيانات معتمدة غير كافية لعرض اقتراحات.</p>'}
<div class="chart-wrap">{ml_curve}</div>
</section>

<section>
<h2>الإصدار المشروط</h2>
<p><strong>حالة الإصدار:</strong> {AUDITOR_OPINION["issuance_status"]}</p>
<h3>شروط الرفع</h3><ol>{cond_rows}</ol>
</section>

<div class="sig-box">{SIG_GATE}</div>
<p style="text-align:center;font-size:11px;color:#94a3b8;margin-top:12px">
  {USER_WATERMARK} · advisory_only=True · certification_ready=False · fake_signature_created=False
  · ml_suggestion_only=True · ml_auto_decision=False · {GENERATOR_VERSION}
</p>
<p style="display:none" class="advisory_only">advisory_only</p>
</div>
</body></html>"""


def _build_admin_html(
    score: dict[str, Any],
    provenance: list[dict[str, Any]],
    ml_card: dict[str, Any],
    ml_curve_data: list[dict[str, Any]],
) -> str:
    user_html = _build_user_html(score)

    prov_rows = "".join(
        f'<tr><td>{r["clause_id"]}</td>'
        f'<td><span class="provenance-tier-{r["tier"]}">{r["tier"]}</span></td>'
        f'<td>{r["suggested_status"]}</td>'
        f'<td>{int(r["confidence"]*100)}%</td>'
        f'<td>{r["source"][:60]}</td>'
        f'<td style="font-size:11px">{r["note"][:50]}</td></tr>'
        for r in provenance
    )

    audit_rows = "".join(
        f'<tr><td>{e["date"]}</td><td>{e["event"]}</td><td>{e["actor"]}</td><td>{e["note"]}</td></tr>'
        for e in AUDIT_TRAIL
    )

    wf_rows = "".join(
        f'<tr><td>{w["clause_id"]}</td><td>{w["owner"]}</td><td>{w["deadline"]}</td>'
        f'<td>{w["priority"]}</td>'
        f'<td style="color:{"#ef4444" if w["status"]=="open" else "#22c55e"}">{w["status"]}</td>'
        f'<td style="font-size:12px">{w["closure"][:50]}</td></tr>'
        for w in WORKFLOW_ITEMS
    )

    ev_rows = "".join(
        f'<tr><td>{e["id"]}</td><td>{e["title"]}</td><td>{e["type"]}</td>'
        f'<td style="color:{"#22c55e" if e["sufficiency"]=="sufficient" else "#ef4444"}">{e["sufficiency"]}</td>'
        f'<td>{e["custody"]}</td></tr>'
        for e in EVIDENCE
    )

    from compliance_inputs_bridge import DRAFT_WEB_REFS  # type: ignore
    dwr_rows = "".join(
        f'<tr><td>{r["ref_id"]}</td><td>{r["standard"]}</td><td>{r["clause"]}</td>'
        f'<td><a href="#" style="color:#2563eb">{r["description"][:40]}...</a></td>'
        f'<td>{int(r["confidence"]*100)}%</td>'
        f'<td style="color:#d97706;font-size:11px">{r["advisory_note"][:30]}</td></tr>'
        for r in DRAFT_WEB_REFS
    )

    ml_card_html = (
        f'<table><tr><th>المفتاح</th><th>القيمة</th></tr>' +
        "".join(
            f'<tr><td>{k}</td><td>{json.dumps(v, ensure_ascii=False)[:80]}</td></tr>'
            for k, v in ml_card.items() if k not in ("training_history",)
        ) + "</table>"
    )

    ml_curve_svg = _svg_ml_curve(ml_curve_data)

    admin_extra = f"""
<div class="admin-only-marker">
<h2>جدول المصدرية (Provenance) — للمسؤولين فقط</h2>
<table><thead><tr><th>البند</th><th>طبقة المصدر</th><th>الحالة المقترحة</th><th>الثقة</th><th>المصدر</th><th>ملاحظة</th></tr></thead>
<tbody>{prov_rows}</tbody></table>

<h2>سجل التدقيق الزمني</h2>
<table><thead><tr><th>التاريخ</th><th>الحدث</th><th>الجهة</th><th>ملاحظات</th></tr></thead>
<tbody>{audit_rows}</tbody></table>

<h2>متابعة سير العمل (Workflow Tracker)</h2>
<table><thead><tr><th>البند</th><th>المالك</th><th>الموعد</th><th>الأولوية</th><th>الحالة</th><th>شرط الإغلاق</th></tr></thead>
<tbody>{wf_rows}</tbody></table>

<h2>سجل الأدلة وكفايتها</h2>
<table><thead><tr><th>المعرّف</th><th>العنوان</th><th>النوع</th><th>الكفاية</th><th>سلسلة العهدة</th></tr></thead>
<tbody>{ev_rows}</tbody></table>

<h2>سجل المراجع Draft (مراجع شبكية — لا تُقدَّم كاعتماد رسمي)</h2>
<table><thead><tr><th>المعرّف</th><th>المعيار</th><th>البند</th><th>الوصف</th><th>الثقة</th><th>تحذير</th></tr></thead>
<tbody>{dwr_rows}</tbody></table>

<h2>بطاقة نموذج ML — للمسؤولين فقط</h2>
{ml_card_html}
<div class="chart-wrap">{ml_curve_svg}</div>
<p style="color:#94a3b8;font-size:11px">ml_suggestion_only=True · ml_trained_on_approved_only=True · ml_auto_decision=False · بطاقة النموذج داخلية — لا تُكشَف للمستخدم</p>
</div>
"""

    return user_html.replace(
        "</div>\n</body></html>",
        f"{admin_extra}\n"
        f'<p style="text-align:center;font-size:11px;color:#94a3b8;margin-top:12px">'
        f'{ADMIN_WATERMARK} · للمراجعة الداخلية فقط · {GENERATOR_VERSION}</p>\n'
        f'</div>\n</body></html>'
    ).replace(
        f'<div class="watermark">{USER_WATERMARK}</div>',
        f'<div class="watermark">{ADMIN_WATERMARK}</div>'
    )


# ── Excel builder (30+ sheets) ────────────────────────────────────────────────

def _build_excel(
    score: dict[str, Any],
    provenance: list[dict[str, Any]],
    ml_card: dict[str, Any],
    ml_curve_data: list[dict[str, Any]],
    out_path: pathlib.Path,
) -> None:
    import openpyxl  # type: ignore
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side  # type: ignore
    from openpyxl.utils import get_column_letter  # type: ignore

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    hdr_font = Font(bold=True, color="FFFFFF", size=11)
    hdr_fill = PatternFill("solid", fgColor="1E3A5F")
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    right_align = Alignment(horizontal="right", vertical="center", wrap_text=True)

    def make_sheet(name: str) -> Any:
        ws = wb.create_sheet(title=name)
        ws.sheet_view.rightToLeft = True
        return ws

    def hdr_row(ws: Any, cols: list[str], row: int = 1) -> None:
        for ci, col in enumerate(cols, 1):
            cell = ws.cell(row=row, column=ci, value=col)
            cell.font = hdr_font
            cell.fill = hdr_fill
            cell.alignment = center

    def auto_width(ws: Any) -> None:
        for col in ws.columns:
            max_len = max((len(str(c.value or "")) for c in col), default=10)
            ws.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 4, 45)

    # ── Sheet 1: ملخص تنفيذي ────────────────────────────────────────────────
    ws = make_sheet("ملخص تنفيذي")
    ws.merge_cells("A1:D1")
    ws["A1"] = "تقرير امتثال المعايير التنظيمية v2"
    ws["A1"].font = Font(bold=True, size=14, color="1E3A5F")
    data = [
        ("الحالة", CASE_ID), ("التاريخ", REPORT_DATE), ("الموقع", LOCATION),
        ("العملة", CURRENCY), ("إجمالي البنود", score["total_clauses"]),
        ("البنود المطبَّقة", score["applicable_clauses"]),
        ("الدرجة المرجّحة الخام", score["raw_weighted_score"]),
        ("الحد الأقصى المرجّح", score["max_weighted_score"]),
        ("النسبة المئوية", f'{score["percentage"]}%'),
        ("إشارة المرور", score["traffic_light"]),
        ("التصنيف", score["label"]),
        ("بنود تحجب الإصدار", "; ".join(score["blocks_issuance"])),
        ("الإيجادات الحرجة", "; ".join(score["critical_findings"])),
        ("advisory_only", str(advisory_only)),
        ("certification_ready", str(certification_ready)),
        ("fake_signature_created", str(fake_signature_created)),
        ("ml_suggestion_only", str(ml_suggestion_only)),
        ("ml_auto_decision", str(ml_auto_decision)),
        ("إصدار المولّد", GENERATOR_VERSION),
    ]
    for ri, (k, v) in enumerate(data, 3):
        ws.cell(row=ri, column=1, value=k).font = Font(bold=True)
        ws.cell(row=ri, column=2, value=v)
    auto_width(ws)

    # ── Sheet 2: التسجيل المرجّح ─────────────────────────────────────────────
    ws = make_sheet("التسجيل المرجّح")
    hdr_row(ws, ["البند", "المعيار", "الخطورة", "وزن الخطورة", "الأهمية",
                 "وزن الأهمية", "الحالة", "درجة الامتثال", "الدرجة المرجّحة",
                 "تحجب الإصدار", "أهمية مادية"])
    for ri, cl in enumerate(CLAUSES, 2):
        comp_s = _COMP_S.get(cl["status"])
        sw = cl["severity_weight"]
        mw = cl["materiality_weight"]
        weighted = round(comp_s * sw * mw, 3) if comp_s is not None else "مستثنى"
        row_data = [
            cl["clause_id"], cl["standard"], cl["severity"], sw,
            cl["materiality"], mw, cl["status"],
            comp_s if comp_s is not None else "N/A", weighted,
            "نعم" if cl.get("blocks_issuance") else "لا",
            "مادي" if cl["materiality"] == "material" else "غير مادي",
        ]
        for ci, val in enumerate(row_data, 1):
            ws.cell(row=ri, column=ci, value=val)
    auto_width(ws)

    # ── Sheets 3-8: per-standard clause sheets ────────────────────────────────
    std_sheets = [
        ("بنود IVS 2025", IVS), ("بنود RICS 2022", RICS), ("بنود USPAP", USPAP),
        ("بنود Basel III-IV", BASEL), ("بنود هيئة تقييم", TAQYEEM), ("بنود AML", AML),
    ]
    hdr_cols = ["معرّف البند", "المرجع", "العنوان", "المتطلب", "الحالة",
                "الخطورة", "الإيجادات", "الإجراء التصحيحي", "تحجب", "المالك", "الموعد"]
    for sheet_name, std_key in std_sheets:
        ws = make_sheet(sheet_name)
        hdr_row(ws, hdr_cols)
        group = [cl for cl in CLAUSES if cl["standard"] == std_key]
        for ri, cl in enumerate(group, 2):
            for ci, val in enumerate([
                cl["clause_id"], cl["clause_ref"], cl["title"], cl["requirement"],
                cl["status"], cl["severity"], cl["findings"], cl["remediation"],
                "نعم" if cl.get("blocks_issuance") else "لا",
                cl["owner"], cl["deadline"],
            ], 1):
                ws.cell(row=ri, column=ci, value=val)
        auto_width(ws)

    # ── Sheet 9: سجل الأدلة ───────────────────────────────────────────────────
    ws = make_sheet("سجل الأدلة")
    hdr_row(ws, ["المعرّف", "العنوان", "النوع", "الكفاية", "سلسلة العهدة"])
    for ri, e in enumerate(EVIDENCE, 2):
        for ci, val in enumerate([e["id"], e["title"], e["type"], e["sufficiency"], e["custody"]], 1):
            ws.cell(row=ri, column=ci, value=val)
    auto_width(ws)

    # ── Sheet 10: سجل التدقيق الزمني ─────────────────────────────────────────
    ws = make_sheet("سجل التدقيق الزمني")
    hdr_row(ws, ["التاريخ", "الحدث", "الجهة", "ملاحظات"])
    for ri, e in enumerate(AUDIT_TRAIL, 2):
        for ci, val in enumerate([e["date"], e["event"], e["actor"], e["note"]], 1):
            ws.cell(row=ri, column=ci, value=val)
    auto_width(ws)

    # ── Sheet 11: Workflow Tracker ────────────────────────────────────────────
    ws = make_sheet("متابعة سير العمل")
    hdr_row(ws, ["البند", "المالك", "الموعد", "الأولوية", "الحالة", "معيار الإعادة", "شرط الإغلاق"])
    for ri, w in enumerate(WORKFLOW_ITEMS, 2):
        for ci, val in enumerate([
            w["clause_id"], w["owner"], w["deadline"], w["priority"],
            w["status"], w["retest"], w["closure"]
        ], 1):
            ws.cell(row=ri, column=ci, value=val)
    auto_width(ws)

    # ── Sheet 12: جدول المصدرية ───────────────────────────────────────────────
    ws = make_sheet("جدول المصدرية")
    hdr_row(ws, ["البند", "طبقة المصدر", "الحالة المقترحة", "الثقة", "المصدر", "الملاحظة", "الاسترشادية"])
    for ri, r in enumerate(provenance, 2):
        for ci, val in enumerate([
            r["clause_id"], r["tier"], r["suggested_status"],
            f'{int(r["confidence"]*100)}%', r["source"][:80],
            r.get("note", "")[:80], r.get("advisory", "")
        ], 1):
            ws.cell(row=ri, column=ci, value=val)
    auto_width(ws)

    # ── Sheet 13: الرأي التدقيقي ──────────────────────────────────────────────
    ws = make_sheet("الرأي التدقيقي")
    ws["A1"] = "الرأي التدقيقي وأثر القرار البنكي"
    ws["A1"].font = Font(bold=True, size=12)
    ws["A3"] = "الأساس"
    ws["B3"] = AUDITOR_OPINION["basis"]
    ws["A5"] = "حكم القرار البنكي"
    ws["B5"] = AUDITOR_OPINION["bank_credit_impact"]
    ws["A6"] = "التبرير"
    ws["B6"] = AUDITOR_OPINION["bank_credit_rationale"]
    ws["A8"] = "التحفّظات"
    for ri, r in enumerate(AUDITOR_OPINION["reservations"], 9):
        ws.cell(row=ri, column=2, value=r)
    ws["A15"] = "شروط الرفع"
    for ri, c in enumerate(AUDITOR_OPINION["conditions"], 16):
        ws.cell(row=ri, column=2, value=c)
    ws["A21"] = "حالة الإصدار"
    ws["B21"] = AUDITOR_OPINION["issuance_status"]
    ws["A23"] = "تحذير"
    ws["B23"] = AUDITOR_OPINION["advisory_note"]
    auto_width(ws)

    # ── Sheet 14: درجات المعايير ──────────────────────────────────────────────
    ws = make_sheet("درجات المعايير")
    hdr_row(ws, ["المعيار", "الدرجة المكتسبة", "الحد الأقصى", "النسبة المئوية", "شريط التقدّم"])
    for ri, (std, v) in enumerate(score.get("standard_scores", {}).items(), 2):
        bar = "█" * (v["pct"] // 10) + "░" * (10 - v["pct"] // 10)
        for ci, val in enumerate([std, v["earned"], v["max"], f'{v["pct"]}%', bar], 1):
            ws.cell(row=ri, column=ci, value=val)
    auto_width(ws)

    # ── Sheet 15: سجل المراجع Draft ───────────────────────────────────────────
    ws = make_sheet("سجل المراجع Draft")
    hdr_row(ws, ["المعرّف", "المعيار", "البند", "الوصف", "الرابط", "تاريخ الاسترداد", "الثقة", "تحذير"])
    try:
        from compliance_inputs_bridge import DRAFT_WEB_REFS  # type: ignore
        refs = DRAFT_WEB_REFS
    except Exception:
        refs = []
    for ri, r in enumerate(refs, 2):
        for ci, val in enumerate([
            r["ref_id"], r["standard"], r["clause"], r["description"],
            r["source_url"], r["retrieved_at"], f'{int(r["confidence"]*100)}%', r["advisory_note"]
        ], 1):
            ws.cell(row=ri, column=ci, value=val)
    auto_width(ws)

    # ── Sheet 16: بطاقة نموذج ML ─────────────────────────────────────────────
    ws = make_sheet("بطاقة نموذج ML")
    ws["A1"] = "بطاقة نموذج ML — داخلية — لا تُكشَف للمستخدم"
    ws["A1"].font = Font(bold=True, size=12, color="7C3AED")
    ws["A3"] = "ml_suggestion_only"
    ws["B3"] = str(ml_card.get("governance", {}).get("ml_suggestion_only", True))
    ws["A4"] = "ml_trained_on_approved_only"
    ws["B4"] = str(ml_card.get("governance", {}).get("ml_trained_on_approved_only", True))
    ws["A5"] = "ml_auto_decision"
    ws["B5"] = str(ml_card.get("governance", {}).get("ml_auto_decision", False))
    ws["A6"] = "الإصدار الحالي"
    ws["B6"] = ml_card.get("current_model_version", 0)
    ws["A7"] = "السجلات المعتمدة المتاحة"
    ws["B7"] = ml_card.get("approved_records_available", 0)
    ws["A8"] = "الحد الأدنى للتدريب"
    ws["B8"] = ml_card.get("min_approved_for_training", 10)
    ws["A9"] = "عتبة الترقية"
    ws["B9"] = str(ml_card.get("validation_accuracy_threshold", 0.65))
    ws["A10"] = "مصدر البيانات"
    ws["B10"] = ml_card.get("source_constraint", "human_approved_auditor_decisions_only")
    ws["A11"] = "السمات"
    ws["B11"] = str(ml_card.get("feature_names", []))
    ws["A13"] = "سجل التدريب"
    hdr_row(ws, ["الإصدار", "تاريخ التدريب", "عدد السجلات", "دقة التحقق", "تجاوز العتبة", "المصدر"], row=14)
    for ri, r in enumerate(ml_card.get("training_history", []), 15):
        for ci, val in enumerate([
            r.get("version"), r.get("trained_at"), r.get("record_count"),
            r.get("validation_accuracy"), r.get("threshold_passed"),
            r.get("source", "")[:40]
        ], 1):
            ws.cell(row=ri, column=ci, value=val)
    auto_width(ws)

    # ── Sheet 17: منحنى تحسّن ML ─────────────────────────────────────────────
    ws = make_sheet("منحنى تحسّن ML")
    hdr_row(ws, ["الإصدار", "تاريخ التدريب", "دقة التحقق", "عدد السجلات", "تجاوز العتبة"])
    for ri, item in enumerate(ml_curve_data, 2):
        for ci, val in enumerate([
            item.get("version"), item.get("trained_at"),
            item.get("validation_accuracy"), item.get("record_count"),
            item.get("threshold_passed")
        ], 1):
            ws.cell(row=ri, column=ci, value=val)
    if not ml_curve_data:
        ws["A2"] = "لا بيانات بعد — النموذج يحتاج إلى سجلات معتمدة كافية"
    auto_width(ws)

    # ── Sheets 18-30: coverage completeness ───────────────────────────────────
    extra_sheets = [
        ("الأهمية النسبية", [
            ["البند", "الأهمية", "الوزن", "التأثير"],
            *[[cl["clause_id"], cl["materiality"], cl["materiality_weight"],
               "مادي" if cl["materiality"]=="material" else "غير مادي"] for cl in CLAUSES]
        ]),
        ("مصفوفة الأدلة", [
            ["البند"] + [e["id"] for e in EVIDENCE],
            *[[cl["clause_id"]] + [("✓" if e["id"] in cl.get("evidence_refs", []) else "") for e in EVIDENCE]
              for cl in CLAUSES]
        ]),
        ("خريطة حرارية — بيانات", [
            ["المعيار", "الخطورة", "الحالة السائدة", "عدد البنود"],
            *[[cl["standard"], cl["severity"], cl["status"], 1] for cl in CLAUSES]
        ]),
        ("توزيع RAG — بيانات", [
            ["الحالة", "العدد"],
            *[[s, sum(1 for cl in CLAUSES if cl["status"]==s)]
              for s in ["compliant","partially_compliant","non_compliant","not_applicable","not_assessed"]]
        ]),
        ("الاتجاه الزمني — بيانات", [
            ["التاريخ", "الدرجة", "ملاحظة"],
            [REPORT_DATE, score["percentage"], "القياس الأساسي — QA v2"]
        ]),
        ("الإصدار المشروط", [
            ["الشرط", "البند المرتبط", "الأولوية"],
            *[[c, w["clause_id"], w["priority"]] for c, w in zip(AUDITOR_OPINION["conditions"], WORKFLOW_ITEMS[:4])]
        ]),
        ("كفاية الأدلة", [
            ["المعرّف", "العنوان", "الكفاية", "العهدة"],
            *[[e["id"], e["title"], e["sufficiency"], e["custody"]] for e in EVIDENCE]
        ]),
        ("مؤشرات الجودة", [
            ["المؤشر", "القيمة"],
            ["الدرجة الكلية المرجّحة", score["percentage"]],
            ["بنود تحجب الإصدار", len(score["blocks_issuance"])],
            ["إيجادات حرجة", len(score["critical_findings"])],
            ["أدلة كافية", sum(1 for e in EVIDENCE if e["sufficiency"]=="sufficient")],
            ["أدلة ناقصة", sum(1 for e in EVIDENCE if e["sufficiency"]=="insufficient")],
            ["نسبة الاستيفاء", f'{round(sum(1 for cl in CLAUSES if cl["status"]=="compliant")/len(CLAUSES)*100)}%'],
        ]),
        ("حوكمة الإطار", [
            ["العلَم", "القيمة"],
            ["advisory_only", str(advisory_only)],
            ["certification_ready", str(certification_ready)],
            ["fake_signature_created", str(fake_signature_created)],
            ["non_certified", str(non_certified)],
            ["ml_suggestion_only", str(ml_suggestion_only)],
            ["ml_trained_on_approved_only", str(ml_trained_on_approved_only)],
            ["ml_auto_decision", str(ml_auto_decision)],
            ["not_real_training", str(not_real_training)],
            ["إصدار المولّد", GENERATOR_VERSION],
        ]),
        ("جسر الحالة — ملخص", [
            ["البند", "الحالة الفعلية", "المصدر", "طبقة المصدر", "الثقة"],
            *[[r["clause_id"], r["suggested_status"], r["source"][:60], r["tier"], f'{int(r["confidence"]*100)}%']
              for r in provenance]
        ]),
        ("المراجع التنظيمية", [
            ["المعيار", "رقم البند", "المتطلب"],
            *[[cl["standard"], cl["clause_ref"], cl["requirement"][:80]] for cl in CLAUSES]
        ]),
        ("ملخص الإجراءات التصحيحية", [
            ["البند", "الخطورة", "الإجراء التصحيحي", "الأولوية", "الموعد"],
            *[[cl["clause_id"], cl["severity"], cl["remediation"][:60], cl["priority"], cl["deadline"]]
              for cl in CLAUSES if cl["status"] not in ("compliant", "not_applicable")]
        ]),
        ("ملاحظات المدقق", [
            ["رقم", "الملاحظة", "المرجع", "التاريخ"],
            ["1", "تقرير الامتثال v2 — استرشادي غير معتمد.", "SCORE_V2", "2026-07-27"],
            ["2", f"الدرجة الكلية: {score['percentage']}% ({score['traffic_light']})", "SCORE_V2", "2026-07-27"],
            ["3", f"البنود الحاجبة: {', '.join(score['blocks_issuance'])}", "SCORE_V2", "2026-07-27"],
            ["4", "الطبقة ML غير جاهزة — تحتاج ≥10 سجلات بشرية معتمدة.", "ComplianceMLLayer", "2026-07-27"],
            ["5", "جميع الاقتراحات استرشادية — لا قرار تلقائي.", "حوكمة", "2026-07-27"],
        ]),
    ]

    for sheet_name, data in extra_sheets:
        ws = make_sheet(sheet_name)
        if data and isinstance(data[0], list):
            hdr_row(ws, data[0])
            for ri, row_data in enumerate(data[1:], 2):
                for ci, val in enumerate(row_data, 1):
                    ws.cell(row=ri, column=ci, value=val)
        auto_width(ws)

    wb.save(str(out_path))


# ── PDF generation ────────────────────────────────────────────────────────────

def _generate_pdf(html_content: str, out_path: pathlib.Path) -> int:
    """Render HTML to PDF using Playwright. Returns page count."""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        raise RuntimeError("Playwright غير متاح — pip install playwright && playwright install chromium")

    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", encoding="utf-8", delete=False) as tmp:
        tmp.write(html_content)
        tmp_path = tmp.name

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(f"file:///{tmp_path.replace(chr(92), '/')}", wait_until="networkidle")
            page.pdf(
                path=str(out_path),
                format="A4",
                print_background=True,
                margin={"top": "15mm", "bottom": "15mm", "left": "12mm", "right": "12mm"},
            )
            page_count = page.evaluate("() => document.querySelectorAll('.page').length") or 1
            browser.close()
    finally:
        pathlib.Path(tmp_path).unlink(missing_ok=True)

    try:
        import fitz  # type: ignore
        doc = fitz.open(str(out_path))
        page_count = len(doc)
        doc.close()
    except Exception:
        pass

    return page_count


def _take_screenshots(html_content: str, ss_dir: pathlib.Path, label: str) -> list[str]:
    """Take section screenshots from HTML using Playwright."""
    shots: list[str] = []
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        return shots

    ss_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", encoding="utf-8", delete=False) as tmp:
        tmp.write(html_content)
        tmp_path = tmp.name

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1200, "height": 900})
            page.goto(f"file:///{tmp_path.replace(chr(92), '/')}", wait_until="networkidle")
            sections = page.query_selector_all("section, h2, .admin-only-marker")
            for i, sec in enumerate(sections[:15]):
                try:
                    path = str(ss_dir / f"{label}_section_{i+1:02d}.png")
                    sec.screenshot(path=path)
                    shots.append(path)
                except Exception:
                    pass
            full_path = str(ss_dir / f"{label}_full.png")
            page.screenshot(path=full_path, full_page=True)
            shots.append(full_path)
            browser.close()
    except Exception:
        pass
    finally:
        pathlib.Path(tmp_path).unlink(missing_ok=True)

    return shots


def _pdf_screenshots(pdf_path: pathlib.Path, ss_dir: pathlib.Path, label: str) -> list[str]:
    shots: list[str] = []
    try:
        import fitz  # type: ignore
        ss_dir.mkdir(parents=True, exist_ok=True)
        doc = fitz.open(str(pdf_path))
        for i, pg in enumerate(doc):
            if i >= _PDF_SCREENSHOT_CAP:
                break
            mat = fitz.Matrix(1.8, 1.8)
            pix = pg.get_pixmap(matrix=mat)
            path = str(ss_dir / f"{label}_page_{i+1:02d}.png")
            pix.save(path)
            shots.append(path)
        doc.close()
    except Exception:
        pass
    return shots


# ── Cross-format consistency check ───────────────────────────────────────────

def _cross_format_check_v2(
    user_html: str, admin_html: str,
    user_pdf: pathlib.Path, admin_pdf: pathlib.Path,
    excel: pathlib.Path,
) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    checks["case_id_user"]    = CASE_ID in user_html
    checks["case_id_admin"]   = CASE_ID in admin_html
    checks["sar_in_user"]     = CURRENCY in user_html
    checks["no_egp_in_user"]  = "EGP" not in user_html
    checks["user_wm_correct"] = USER_WATERMARK in user_html and ADMIN_WATERMARK not in user_html
    checks["admin_wm"]        = ADMIN_WATERMARK in admin_html
    checks["sig_gate_user"]   = SIG_GATE in user_html
    checks["sig_gate_admin"]  = SIG_GATE in admin_html
    checks["advisory_flag"]   = "advisory_only" in user_html and "advisory_only" in admin_html
    checks["ml_draft_tag_user"]  = "ml-draft-tag" in user_html or "اقتراح ML" in user_html
    checks["no_admin_element_in_user"] = 'class="admin-only-marker"' not in user_html
    checks["admin_marker_in_admin"]    = 'class="admin-only-marker"' in admin_html
    checks["user_pdf_exists"]  = user_pdf.exists() and user_pdf.stat().st_size > 1000
    checks["admin_pdf_exists"] = admin_pdf.exists() and admin_pdf.stat().st_size > 1000
    checks["excel_exists"]     = excel.exists() and excel.stat().st_size > 1000
    checks["no_file_paths_user"]  = "file:///" not in user_html and "C:\\" not in user_html
    checks["no_file_paths_admin"] = "file:///" not in admin_html

    mismatches = [k for k, v in checks.items() if not v]
    return {"pass": len(mismatches) == 0, "checks": checks, "mismatches": mismatches}


# ── Main runner ───────────────────────────────────────────────────────────────

def run_standards_compliance_v2_visual_qa(
    *,
    output_root: "str | pathlib.Path",
    run_id: str,
    case_id: str = CASE_ID,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Generate all 5 artifacts + screenshots + audit JSONs into a per-run directory.

    Args:
        output_root: Parent directory under which the run directory is created.
        run_id:      UUID4-hex string identifying this run (server-supplied).
        case_id:     Compliance case identifier (default CASE_ID).
        overwrite:   If False (default), abort if the run directory already exists.

    Returns:
        Summary dict with score / format-check / metadata fields.
        No path-bearing fields are included in the return value.
    """
    run_dir = pathlib.Path(output_root) / run_id
    arts    = run_dir / "artifacts"
    ss      = run_dir / "screenshots"
    aud     = run_dir / "audits"

    if run_dir.exists() and not overwrite:
        raise FileExistsError(f"Run directory already exists: {run_dir}")

    for d in [arts, ss / "user_html", ss / "admin_html",
              ss / "user_pdf", ss / "admin_pdf", aud]:
        d.mkdir(parents=True, exist_ok=True)

    # Bridge (READ-ONLY)
    try:
        from compliance_inputs_bridge import ComplianceInputsBridge  # type: ignore
        bridge = ComplianceInputsBridge()
        bridge.load_all()
        provenance = bridge.build_provenance_table([cl["clause_id"] for cl in CLAUSES])
        bridge_summary = bridge.summary()
    except Exception as exc:
        provenance = []
        bridge_summary = {"error": str(exc)}

    # ML layer
    try:
        from compliance_ml_layer import ComplianceMLLayer  # type: ignore
        ml = ComplianceMLLayer()
        ml_card = ml.get_model_card()
        ml_curve_data = ml.get_improvement_curve()
        ml_suggestion = ml.suggest(CLAUSES[0])
    except Exception as exc:
        ml_card = {"error": str(exc), "governance": {
            "ml_suggestion_only": True, "ml_auto_decision": False}}
        ml_curve_data = []
        ml_suggestion = {"status": "not_ready",
                         "message": "ML layer unavailable", "confidence": 0.0}

    score = SCORE_V2

    # Build HTML
    user_html  = _build_user_html(score, ml_suggestion)
    admin_html = _build_admin_html(score, provenance, ml_card, ml_curve_data)

    user_html_path  = arts / f"compliance_v2_{case_id}_user.html"
    admin_html_path = arts / f"compliance_v2_{case_id}_admin.html"
    user_html_path.write_text(user_html, encoding="utf-8")
    admin_html_path.write_text(admin_html, encoding="utf-8")

    # Generate PDFs
    user_pdf_path  = arts / f"compliance_v2_{case_id}_user.pdf"
    admin_pdf_path = arts / f"compliance_v2_{case_id}_admin.pdf"
    user_pages  = _generate_pdf(user_html, user_pdf_path)
    admin_pages = _generate_pdf(admin_html, admin_pdf_path)

    # Screenshots
    user_html_shots  = _take_screenshots(user_html,  ss / "user_html",  "user")
    admin_html_shots = _take_screenshots(admin_html, ss / "admin_html", "admin")
    try:
        from standards_compliance_v2_generator import _pdf_screenshots  # type: ignore
        user_pdf_shots  = _pdf_screenshots(user_pdf_path,  ss / "user_pdf",  "user_pdf")
        admin_pdf_shots = _pdf_screenshots(admin_pdf_path, ss / "admin_pdf", "admin_pdf")
    except Exception:
        user_pdf_shots  = []
        admin_pdf_shots = []

    # Excel
    excel_path = arts / f"compliance_v2_{case_id}_admin.xlsx"
    _build_excel(score, provenance, ml_card, ml_curve_data, excel_path)
    import openpyxl as _oxl  # type: ignore
    _wb = _oxl.load_workbook(str(excel_path))
    sheet_count = len(_wb.sheetnames)
    _wb.close()

    # Cross-format check
    cross = _cross_format_check_v2(
        user_html, admin_html, user_pdf_path, admin_pdf_path, excel_path
    )

    # Governance object (7 keys including synthetic_data)
    governance_obj = {
        "advisory_only":              advisory_only,
        "certification_ready":        certification_ready,
        "fake_signature_created":     fake_signature_created,
        "ml_suggestion_only":         ml_suggestion_only,
        "ml_trained_on_approved_only": ml_trained_on_approved_only,
        "ml_auto_decision":           ml_auto_decision,
        "synthetic_data":             synthetic_data,
    }

    # Audit JSONs
    report = {
        "generator_version": GENERATOR_VERSION,
        "case_id":           case_id,
        "generated_at":      datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "score":             score,
        "user_html":         {"size": user_html_path.stat().st_size},
        "admin_html":        {"size": admin_html_path.stat().st_size},
        "user_pdf":          {
            "pages":                user_pages,
            "screenshots_captured": min(user_pages, _PDF_SCREENSHOT_CAP),
            "screenshots_truncated": user_pages > _PDF_SCREENSHOT_CAP,
        },
        "admin_pdf":         {
            "pages":                admin_pages,
            "screenshots_captured": min(admin_pages, _PDF_SCREENSHOT_CAP),
            "screenshots_truncated": admin_pages > _PDF_SCREENSHOT_CAP,
        },
        "excel":             {"sheet_count": sheet_count},
        "cross_format":      cross,
        "bridge_summary":    bridge_summary,
        "ml_card_summary":   {k: v for k, v in ml_card.items() if k != "training_history"},
        "screenshots": {
            "user_html":  len(user_html_shots),
            "admin_html": len(admin_html_shots),
            "user_pdf":   len(user_pdf_shots),
            "admin_pdf":  len(admin_pdf_shots),
            "pdf_screenshot_cap": _PDF_SCREENSHOT_CAP,
        },
        "governance": governance_obj,
    }
    (aud / "compliance_v2_visual_qa_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (aud / "compliance_v2_cross_format.json").write_text(
        json.dumps(cross, ensure_ascii=False, indent=2), encoding="utf-8")
    (aud / "compliance_v2_content_audit.json").write_text(
        json.dumps({
            "clauses_count":       len(CLAUSES),
            "evidence_count":      len(EVIDENCE),
            "audit_trail_events":  len(AUDIT_TRAIL),
            "workflow_items":      len(WORKFLOW_ITEMS),
            "provenance_rows":     len(provenance),
            "draft_web_refs":      bridge_summary.get("draft_web_refs_count", 0),
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "overall_pass":      cross["pass"],
        "score_pct":         score["percentage"],
        "traffic_light":     score["traffic_light"],
        "user_pdf_pages":    user_pages,
        "admin_pdf_pages":   admin_pages,
        "excel_sheets":      sheet_count,
        "cross_format_pass": cross["pass"],
        "mismatches":        cross["mismatches"],
        "ml_ready":          ml_card.get("current_model_version", 0) > 0,
    }


if __name__ == "__main__":
    import uuid as _uuid
    _run_id = _uuid.uuid4().hex
    with tempfile.TemporaryDirectory() as _tmp:
        result = run_standards_compliance_v2_visual_qa(
            output_root=_tmp,
            run_id=_run_id,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))

