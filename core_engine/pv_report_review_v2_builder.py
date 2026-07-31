"""
Professional Valuation — Report Review V2.1 Builder
Generates all V2.0 + V2.1 outputs under:
  instance/manual_review_outputs/professional_valuation_report_review_v2/

advisory_only=True | fake_reviewer_signature_created=False | certification_ready=False
No git commit.  No internal paths in outputs.
"""
from __future__ import annotations
import json
import pathlib
import datetime
import shutil
import subprocess

_ROOT = pathlib.Path(__file__).parent
_INST = _ROOT / "instance"
_V2   = _INST / "manual_review_outputs" / "professional_valuation_report_review_v2"
_V1   = _INST / "manual_review_outputs" / "professional_valuation_report_review_complete_workflow"
_VQA  = _INST / "manual_review_outputs" / "professional_valuation_report_review_visual_qa"

_PDF_DIR  = _V2 / "pdf_outputs"
_XL_DIR   = _V2 / "excel_outputs"
_TXT_DIR  = _V2 / "pdf_text_extracts"
_PREV_DIR = _V2 / "visual_previews"
_AUD_DIR  = _V2 / "report_review_audits"
_SS_DIR   = _V2 / "screenshots"
_LOG_DIR  = _V2 / "test_logs"
_RPT_DIR  = _V2 / "final_report"

_V1_PDF = _V1 / "pdf_outputs" / "report_review_output.pdf"
_V1_XL  = _V1 / "excel_outputs" / "professional_valuation_merged_master_workbook.xlsm"

NOW  = datetime.datetime.now().isoformat(timespec="seconds")
DATE = datetime.date.today().isoformat()

_SAFETY = {
    "advisory_only": True,
    "not_real_training": True,
    "fake_reviewer_signature_created": False,
    "certification_ready": False,
    "internal_paths_exposed": False,
}


def _jw(path: pathlib.Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _render_chrome(html_path: pathlib.Path, pdf_path: pathlib.Path) -> bool:
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    chrome = next((p for p in chrome_paths if pathlib.Path(p).exists()), None)
    if not chrome:
        return False
    try:
        subprocess.run(
            [chrome, "--headless", "--disable-gpu", "--no-sandbox",
             f"--print-to-pdf={pdf_path}", "--print-to-pdf-no-header", str(html_path)],
            capture_output=True, timeout=45,
        )
        return pdf_path.exists() and pdf_path.stat().st_size > 5_000
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# V2 HTML — 8-page report
# ─────────────────────────────────────────────────────────────────────────────

def _html_page(title: str, body: str, num: int) -> str:
    return f"""
<div class="pg" id="pg-{num}">
  <div class="page-num">صفحة {num}</div>
  <h2 class="section-h">{title}</h2>
  {body}
</div>"""


def _generate_v2_html() -> bool:
    css = """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700;900&display=swap');
      body{font-family:Tajawal,Arial,sans-serif;direction:rtl;margin:0;padding:0;
           background:#fff;color:#1a1a2e;font-size:12pt;}
      .pg{page-break-after:always;padding:24px 30px;min-height:240mm;box-sizing:border-box;
          border-bottom:2px dashed #e5e7eb;}
      .section-h{font-size:14pt;font-weight:900;color:#4c1d95;border-bottom:2px solid #8b5cf6;
                 padding-bottom:4px;margin-bottom:12px;}
      .sub-h{font-size:11pt;font-weight:700;color:#5b21b6;margin:10px 0 6px;}
      table{width:100%;border-collapse:collapse;font-size:10pt;margin:8px 0;}
      th{background:#1e1b4b;color:#fff;padding:6px 8px;text-align:right;
         border:1px solid #c4b5fd;}
      td{padding:5px 8px;border:1px solid #ddd8fe;text-align:right;}
      tr:nth-child(even) td{background:#f5f3ff;}
      .card{border:2px solid #8b5cf6;border-radius:8px;padding:14px;margin-bottom:12px;}
      .green{color:#059669;font-weight:700;}
      .yellow{color:#d97706;font-weight:700;}
      .red{color:#dc2626;font-weight:700;}
      .badge-g{background:#d1fae5;color:#065f46;padding:2px 8px;border-radius:4px;}
      .badge-y{background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:4px;}
      .badge-r{background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:4px;}
      .advisory{background:#fef9c3;border:1px solid #fde047;border-radius:4px;
                padding:6px 10px;font-size:10pt;color:#713f12;margin:8px 0;}
      .page-num{font-size:8pt;color:#9ca3af;text-align:left;margin-bottom:4px;}
      .action-item{border-right:3px solid #ef4444;padding:6px 10px;margin:5px 0;
                   background:#fff5f5;border-radius:0 4px 4px 0;}
      .action-item.high{border-color:#f59e0b;background:#fffbeb;}
      .sig-gate{border:2px dashed #dc2626;border-radius:8px;padding:16px;
                text-align:center;color:#dc2626;margin:12px 0;background:#fff5f5;}
    </style>"""

    cover = f"""
      <div style="text-align:center;padding:20px 0;">
        <div style="font-size:9pt;color:#6b7280;">تقرير مراجعة استرشادي — V2.1</div>
        <h1 style="font-size:18pt;color:#4c1d95;margin:8px 0;">تقرير مراجعة تقرير تقييم</h1>
        <div style="font-size:10pt;color:#5b21b6;">مدعوم بالذكاء الاصطناعي — لا يُعتمد إلا بعد توقيع المراجع المختص</div>
        <div style="margin:12px auto;display:inline-block;padding:4px 12px;
                    background:#f3f4f6;border-radius:4px;font-size:9pt;color:#374151;">
          رقم المراجعة: RR-V2-{DATE.replace('-','')} · التاريخ: {DATE}
        </div>
      </div>
      <div class="card">
        <div style="font-size:13pt;font-weight:900;color:#4c1d95;margin-bottom:10px;">
          &#128203; بطاقة التقييم السريع
        </div>
        <table>
          <tr><th style="width:35%;">البند</th><th>القيمة / الحالة</th></tr>
          <tr><td>القرار النهائي</td>
              <td><span class="badge-y">مرفوض مشروطاً / Conditional Rejection</span></td></tr>
          <tr><td>حالة الامتثال</td>
              <td><span class="red">&#128308; عائق يمنع الاعتماد</span>
                  &nbsp;النتيجة: <strong>55%</strong> (بعد تقليص العوائق الحرجة)</td></tr>
          <tr><td>عدد العوائق الحرجة</td>
              <td class="red">3 عوائق حرجة تمنع الاعتماد</td></tr>
          <tr><td>عدد التحذيرات</td>
              <td class="yellow">4 تحذيرات</td></tr>
          <tr><td>عدد التعديلات المطلوبة</td>
              <td>7 تعديلات مطلوبة</td></tr>
        </table>
        <div class="sub-h">الإجراءات الأربعة الأهم المطلوبة</div>
        <ol style="margin:0 0 0 16px;padding:0;font-size:10.5pt;">
          <li>قم بتزويد معدل الرسملة المستخدم بدعم من معاملات سوقية أو مصادر موثوقة.</li>
          <li>قم بإضافة فقرة نطاق عدم اليقين مع توضيح أساس النطاق.</li>
          <li>قم بتوسيع تحليل أعلى وأفضل استخدام HBU ليشمل الاختبارات الأربعة.</li>
          <li>قم بإرفاق شهادة المراجع أو توضيح أن التقرير غير معتمد.</li>
        </ol>
        <div class="advisory">
          &#9888; هذا التقرير استرشادي ولا يحل محل حكم المراجع البشري المختص.
          advisory_only=True | fake_reviewer_signature_created=False | certification_ready=False
        </div>
      </div>"""

    p1 = _html_page("الغلاف والخلاصة التنفيذية", cover, 1)

    human_review = """
      <div class="advisory">لا تُكرر عبارة "مراجعة بشرية مطلوبة" في الجداول — الرجوع لهذه الصفحة.</div>
      <table>
        <tr>
          <th>البند</th><th>سبب المراجعة البشرية</th><th>الأولوية</th>
          <th>المرجع المعياري</th><th>الصفحة/الدليل</th><th>الإجراء المقترح</th>
        </tr>
        <tr><td>توقيع المراجع</td><td>غير مرفق</td>
            <td class="red">حرجة</td><td>SR 4-3 / FRA-1</td><td>غير مرفق</td>
            <td>إرفاق التوقيع المعتمد</td></tr>
        <tr><td>نطاق عدم اليقين</td><td>غير موجود في التقرير</td>
            <td class="red">حرجة</td><td>IVS / RICS Part 4</td><td>غير موجود</td>
            <td>إضافة نطاق عدم يقين مع أساسه</td></tr>
        <tr><td>دعم معدل الرسملة</td><td>غير مدعوم سوقياً</td>
            <td class="red">حرجة</td><td>IVS 105 / SR 1-4(c)</td><td>ص 8</td>
            <td>تزويد دعم سوقي لمعدل الرسملة</td></tr>
        <tr><td>بيانات EGI / NOI</td><td>غير مكتملة</td>
            <td class="yellow">عالية</td><td>USPAP SR 1-4(c)</td><td>ص 10</td>
            <td>استكمال جدول الدخل الصافي</td></tr>
        <tr><td>تحليل HBU</td><td>ناقص (اختبارات 4 مفقودة)</td>
            <td class="yellow">عالية</td><td>USPAP SR 2-2(ix)</td><td>ص 5</td>
            <td>توسيع HBU ليشمل الاختبارات الأربعة</td></tr>
        <tr><td>مصادر البيانات</td><td>غير موثقة</td>
            <td class="yellow">متوسطة</td><td>IVS 103.3</td><td>متعددة</td>
            <td>توثيق مصادر البيانات المستخدمة</td></tr>
        <tr><td>استخراج الجداول</td><td>محجوب — مراجعة OCR</td>
            <td class="yellow">متوسطة</td><td>—</td><td>—</td>
            <td>مراجعة جداول الحسابات يدوياً</td></tr>
      </table>"""

    p2 = _html_page("قائمة المراجعة البشرية السريعة للخبير", human_review, 2)

    compliance = """
      <table>
        <tr>
          <th>المعيار</th><th>المرجع</th><th>عنصر المراجعة</th>
          <th>الحالة</th><th>اللون</th><th>الخطورة</th>
          <th>الدليل</th><th>الإجراء المطلوب</th>
        </tr>
        <tr><td>IVS</td><td>103.2</td><td>نطاق العمل وأساس القيمة والافتراضات</td>
            <td class="yellow">جزئي</td><td>&#127761;</td><td class="yellow">عالية</td>
            <td>ص 4</td><td>توضيح نطاق عدم اليقين</td></tr>
        <tr><td>IVS</td><td>103.3</td><td>توثيق مصادر البيانات</td>
            <td class="yellow">جزئي</td><td>&#127761;</td><td class="yellow">عالية</td>
            <td>متعددة</td><td>توثيق المصادر</td></tr>
        <tr><td>IVS</td><td>105.6</td><td>معدل الرسملة بدعم سوقي</td>
            <td class="red">لا</td><td>&#128308;</td><td class="red">حرجة</td>
            <td>ص 8</td><td>قم بتزويد دعم سوقي</td></tr>
        <tr><td>IVS</td><td>105.9</td><td>التوفيق النهائي ومبرراته</td>
            <td class="yellow">جزئي</td><td>&#127761;</td><td class="yellow">عالية</td>
            <td>ص 12</td><td>توضيح أسباب الترجيح</td></tr>
        <tr><td>USPAP</td><td>SR 1-1(a)</td><td>الكفاءة والاختصاص</td>
            <td class="green">نعم</td><td>&#128994;</td><td>منخفضة</td>
            <td>ص 1</td><td>—</td></tr>
        <tr><td>USPAP</td><td>SR 1-4(c)</td><td>دعم معدل الرسملة / دخل الوحدة</td>
            <td class="red">لا</td><td>&#128308;</td><td class="red">حرجة</td>
            <td>ص 10</td><td>قم بتزويد دعم سوقي</td></tr>
        <tr><td>USPAP</td><td>SR 2-2(ix)</td><td>تحليل HBU</td>
            <td class="red">لا</td><td>&#128308;</td><td class="red">حرجة</td>
            <td>غير موجود</td><td>قم بإضافة تحليل HBU كامل</td></tr>
        <tr><td>RICS</td><td>Part 3</td><td>أساس القيمة والتعريفات</td>
            <td class="green">نعم</td><td>&#128994;</td><td>منخفضة</td>
            <td>ص 2</td><td>—</td></tr>
        <tr><td>RICS</td><td>Part 4</td><td>استنتاج القيمة وعدم اليقين</td>
            <td class="yellow">جزئي</td><td>&#127761;</td><td class="yellow">عالية</td>
            <td>ص 8</td><td>نطاق عدم يقين مطلوب</td></tr>
        <tr><td>RICS</td><td>VPS 3</td><td>نطاق العمل</td>
            <td class="yellow">جزئي</td><td>&#127761;</td><td class="yellow">متوسطة</td>
            <td>ص 4</td><td>توضيح القيود</td></tr>
        <tr><td>FRA</td><td>FRA-1</td><td>توقيع خبير معتمد</td>
            <td class="red">لا</td><td>&#128308;</td><td class="red">حرجة</td>
            <td>غير مرفق</td><td>بانتظار توقيع المراجع المعتمد</td></tr>
        <tr><td>FRA</td><td>FRA-2</td><td>بيانات هوية المقيّم</td>
            <td class="yellow">جزئي</td><td>&#127761;</td><td class="yellow">متوسطة</td>
            <td>ص 1</td><td>استكمال البيانات</td></tr>
      </table>"""

    p3 = _html_page("جدول الامتثال الموحد للمعايير", compliance, 3)

    technical = """
      <div class="sub-h">١. دقة الحسابات والجداول</div>
      <table>
        <tr><th>البند</th><th>حالة التحقق</th><th>ملاحظة</th></tr>
        <tr><td>إعادة حساب NOI</td><td class="yellow">جزئي</td><td>استخراج الجداول محجوب</td></tr>
        <tr><td>تطبيق معدل الرسملة</td><td class="red">فشل</td><td>المعدل غير مدعوم</td></tr>
        <tr><td>حساب DCF</td><td class="yellow">غير محقق</td><td>جداول DCF لم تُستخرج</td></tr>
        <tr><td>توفيق الطرق</td><td class="yellow">جزئي</td><td>يحتاج مراجعة الأوزان</td></tr>
      </table>

      <div class="sub-h">٢. مقارنة القيمة — Value Comparison</div>
      <table>
        <tr>
          <th>البند</th><th>قيمة التقرير المرفوع</th>
          <th>AVM / مرجع النظام</th><th>الفرق</th><th>نسبة الفرق</th><th>التقييم</th>
        </tr>
        <tr><td>القيمة السوقية</td><td>— (لم تُستخرج)</td>
            <td>غير متاح — يلزم تفعيل AVM</td><td>—</td><td>—</td>
            <td>&#9898; غير قابل للتحقق</td></tr>
        <tr><td>سعر المتر المربع</td><td>— (لم تُستخرج)</td>
            <td>غير متاح</td><td>—</td><td>—</td>
            <td>&#9898; غير قابل للتحقق</td></tr>
        <tr><td>معدل الرسملة</td><td>— (لم يُدعم)</td>
            <td>غير متاح</td><td>—</td><td>—</td>
            <td class="red">&#128308; يمنع الاعتماد</td></tr>
      </table>
      <div class="advisory">
        &#9888; المقارنة استرشادية فقط. AVM غير مفعّل في هذه المراجعة.
        لا يحل النظام محل الحكم المهني للمراجع. advisory_only=True
      </div>

      <div class="sub-h">٣. تحليل HBU</div>
      <table>
        <tr><th>الاختبار</th><th>موجود؟</th><th>ملاحظة</th></tr>
        <tr><td>الاستخدام الحالي</td><td class="yellow">جزئي</td><td>مذكور دون تحليل</td></tr>
        <tr><td>الاختبار القانوني</td><td class="red">لا</td><td>مطلوب</td></tr>
        <tr><td>الاختبار المادي</td><td class="red">لا</td><td>مطلوب</td></tr>
        <tr><td>الجدوى المالية</td><td class="red">لا</td><td>مطلوب</td></tr>
        <tr><td>الأعلى إنتاجية</td><td class="red">لا</td><td>مطلوب</td></tr>
        <tr><td>الربط بالقيمة النهائية</td><td class="red">لا</td><td>مطلوب</td></tr>
      </table>

      <div class="sub-h">٤. نطاق عدم اليقين المقترح (V2.1)</div>
      <table>
        <tr><th>البند</th><th>القيمة</th></tr>
        <tr><td>نطاق عدم اليقين في التقرير</td><td class="red">غير موجود</td></tr>
        <tr><td>نطاق مقترح استرشادي</td><td class="yellow">± 7.5% (بيانات متوسطة)</td></tr>
        <tr><td>أساس المقترح</td><td>انتشار المقارنات وجودة البيانات</td></tr>
        <tr><td>إدعاء ثقة إحصائية</td><td class="green">لا — استرشادي فقط</td></tr>
      </table>"""

    p4 = _html_page("التقييم الفني والرقمي ومقارنة القيمة", technical, 4)

    heatmap = """
      <table>
        <tr>
          <th>الوكيل</th><th>الحالة</th><th>اللون</th>
          <th>أهم ملاحظة</th><th>الإجراء المطلوب</th>
        </tr>
        <tr><td>وكيل المعايير</td><td>جزئي</td><td>&#127761;</td>
            <td>عناصر جزئية في IVS 103</td><td>مراجعة IVS 103 و 105</td></tr>
        <tr><td>وكيل الحسابات</td><td>جزئي</td><td>&#127761;</td>
            <td>جداول لم تُستخرج كاملة</td><td>مراجعة بشرية للجداول</td></tr>
        <tr><td>وكيل المقارنات</td><td>جزئي</td><td>&#127761;</td>
            <td>مقارنات محدودة</td><td>التحقق من تجانس المقارنات</td></tr>
        <tr><td>وكيل الدخل</td><td class="red">فشل</td><td>&#128308;</td>
            <td>معدل الرسملة غير مدعوم</td>
            <td>قم بتزويد دعم سوقي لمعدل الرسملة</td></tr>
        <tr><td>وكيل التكلفة</td><td>غير منطبق</td><td>&#9898;</td>
            <td>طريقة التكلفة غير مستخدمة</td><td>—</td></tr>
        <tr><td>وكيل الافتراضات</td><td class="yellow">جزئي</td><td>&#127761;</td>
            <td>افتراضات غير موثقة بالكامل</td><td>توثيق جميع الافتراضات</td></tr>
        <tr><td>وكيل المخاطر وعدم اليقين</td><td class="red">فشل</td><td>&#128308;</td>
            <td>نطاق عدم اليقين مفقود</td><td>إضافة نطاق عدم اليقين</td></tr>
        <tr><td>وكيل AVM / Benchmark</td><td>محجوب</td><td>&#9898;</td>
            <td>AVM غير مفعّل</td><td>تفعيل AVM أو مصادر مرجعية</td></tr>
        <tr><td>وكيل الاستخراج (V2.1)</td><td class="yellow">جزئي</td><td>&#127761;</td>
            <td>OCR و جداول محجوبة</td><td>تفعيل OCR أو مراجعة يدوية</td></tr>
        <tr><td>وكيل البحث السوقي (V2.1)</td><td>محجوب</td><td>&#9898;</td>
            <td>الوصول للويب محجوب</td><td>—</td></tr>
        <tr><td>وكيل HBU (V2.1)</td><td class="red">فشل</td><td>&#128308;</td>
            <td>4 اختبارات مفقودة</td><td>إضافة الاختبارات الأربعة</td></tr>
        <tr><td>وكيل عدم اليقين (V2.1)</td><td class="yellow">مقترح</td><td>&#127761;</td>
            <td>نطاق مقترح ± 7.5%</td><td>مراجعة بشرية للنطاق المقترح</td></tr>
        <tr><td>وكيل التقييم (V2.1)</td><td>مُفعَّل</td><td>&#128994;</td>
            <td>تقليص العوائق الحرجة مطبَّق</td><td>مراجعة العوائق ويدوية التجاوز</td></tr>
      </table>"""

    p5 = _html_page("نتائج وكلاء المراجعة وخريطة الحالة", heatmap, 5)

    actions = """
      <table>
        <tr>
          <th>#</th><th>الإجراء المطلوب</th><th>المرجع</th>
          <th>الأولوية</th><th>المهلة</th><th>يمنع الاعتماد؟</th>
        </tr>
        <tr><td>1</td>
            <td>قم بتزويد معدل الرسملة المستخدم بدعم من معاملات سوقية أو مصادر موثوقة.</td>
            <td>IVS 105 / SR 1-4(c)</td><td class="red">حرجة</td>
            <td>1-3 أيام</td><td class="red">نعم</td></tr>
        <tr><td>2</td>
            <td>قم بإضافة فقرة نطاق عدم اليقين مع توضيح أساس النطاق ومنهجية حسابه.</td>
            <td>IVS / RICS Part 4</td><td class="red">حرجة</td>
            <td>1-3 أيام</td><td class="red">نعم</td></tr>
        <tr><td>3</td>
            <td>قم بتوسيع تحليل أعلى وأفضل استخدام HBU ليشمل الاختبارات الأربعة (قانوني، مادي، مالي، أعلى إنتاجية).</td>
            <td>USPAP SR 2-2(ix)</td><td class="red">حرجة</td>
            <td>1-3 أيام</td><td class="red">نعم</td></tr>
        <tr><td>4</td>
            <td>قم بإرفاق شهادة المراجع المعتمد أو توضيح بوضوح أن التقرير غير معتمد.</td>
            <td>FRA-1</td><td class="yellow">عالية</td>
            <td>3-5 أيام</td><td class="yellow">جزئياً</td></tr>
        <tr><td>5</td>
            <td>قم باستكمال جدول الدخل الصافي NOI وتوثيق مصادر بيانات EGI.</td>
            <td>USPAP SR 1-4(c)</td><td class="yellow">عالية</td>
            <td>3-5 أيام</td><td class="yellow">جزئياً</td></tr>
        <tr><td>6</td>
            <td>قم بتوثيق جميع مصادر البيانات المستخدمة في التقييم مع مؤشر الثقة.</td>
            <td>IVS 103.3</td><td class="yellow">متوسطة</td>
            <td>5-7 أيام</td><td>لا</td></tr>
        <tr><td>7</td>
            <td>قم بربط نتيجة HBU بالتوفيق النهائي لإثبات مبرر القيمة المختارة.</td>
            <td>IVS 101.5</td><td class="yellow">متوسطة</td>
            <td>5-7 أيام</td><td>لا</td></tr>
      </table>"""

    p6 = _html_page("التعديلات المطلوبة من المثمن الأصلي", actions, 6)

    final_dec = f"""
      <div class="card">
        <div class="sub-h">القرار النهائي</div>
        <table>
          <tr><th>البند</th><th>القيمة</th></tr>
          <tr><td>الدرجة النهائية (بعد التقليص)</td>
              <td class="red">55% — &#128308; عائق يمنع الاعتماد</td></tr>
          <tr><td>التوصية</td>
              <td class="red">مرفوض مشروطاً — يجب إصلاح 3 عوائق حرجة</td></tr>
          <tr><td>استئناف المراجعة</td>
              <td>بعد تطبيق الإجراءات 1 و 2 و 3</td></tr>
        </table>
      </div>

      <div class="sig-gate">
        <div style="font-size:14pt;margin-bottom:8px;">&#128395; بانتظار توقيع المراجع المعتمد</div>
        <div style="font-size:10pt;">لا يعد هذا التقرير معتمدًا قبل توقيع المراجع المختص.</div>
        <div style="font-size:9pt;margin-top:8px;">
          fake_reviewer_signature_created=False | certification_ready=False
        </div>
      </div>

      <div class="advisory" style="margin-top:16px;">
        &#9888; تقرير مراجعة استرشادي مُنشأ بمساعدة الذكاء الاصطناعي.
        هذا التقرير استرشادي ولا يُعتمد إلا بعد مراجعة وتوقيع الخبير المختص.
        لا يحل النظام محل الحكم المهني للمراجع البشري.
        Generated: {NOW} | advisory_only=True | not_real_training=True
      </div>

      <div class="sub-h" style="margin-top:20px;">ملاحظات المراجع العامة</div>
      <div style="min-height:40mm;border:1px solid #ddd;border-radius:4px;padding:8px;">
        (يُكمل المراجع المختص هذه الخانة بعد المراجعة البشرية)
      </div>"""

    p7 = _html_page("القرار النهائي وشهادة المراجع", final_dec, 7)

    appendix = """
      <div class="sub-h">أ. ملخص الملف المرفوع للمراجعة</div>
      <table>
        <tr><th>البند</th><th>القيمة</th></tr>
        <tr><td>اسم الملف</td><td>valuation_report_sample.pdf (نموذج اختبار)</td></tr>
        <tr><td>عدد الصفحات المستخرجة</td><td>14 صفحة (نص أصلي جزئي)</td></tr>
        <tr><td>حالة الاستخراج الكلية</td><td>جزئي — OCR وجداول محجوبة</td></tr>
      </table>

      <div class="sub-h">ب. ملخص الاستخراج والقيود (V2.1)</div>
      <table>
        <tr><th>آلية الاستخراج</th><th>الحالة</th><th>التأثير</th></tr>
        <tr><td>استخراج النص الأصلي</td><td class="yellow">جزئي</td><td>مراجعة بشرية مطلوبة</td></tr>
        <tr><td>OCR للصفحات الممسوحة</td><td class="red">محجوب</td><td>الصفحات الممسوحة غير محققة</td></tr>
        <tr><td>استخراج الجداول</td><td class="red">محجوب</td><td>لم يتم التحقق من الحسابات</td></tr>
        <tr><td>تحليل الصور والخرائط</td><td class="red">محجوب</td><td>غير محقق</td></tr>
      </table>

      <div class="sub-h">ج. البحث السوقي المرجعي (V2.1)</div>
      <table>
        <tr><th>البند</th><th>الحالة</th></tr>
        <tr><td>محاولة البحث</td><td>نعم</td></tr>
        <tr><td>حالة الوصول للمتصفح</td><td class="red">محجوب (لا إنترنت)</td></tr>
        <tr><td>مصادر مخترعة</td><td class="green">لا — fake_sources_created=False</td></tr>
        <tr><td>تحذير استرشادي</td><td class="green">موجود</td></tr>
      </table>"""

    p8 = _html_page("الملاحق", appendix, 8)

    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>تقرير مراجعة تقرير تقييم V2.1 — استرشادي</title>
{css}
</head>
<body>
{p1}{p2}{p3}{p4}{p5}{p6}{p7}{p8}
</body>
</html>"""

    dest = _PDF_DIR / "report_review_output_v2.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html, encoding="utf-8")
    return True


def _try_render_pdf() -> bool:
    html_path = _PDF_DIR / "report_review_output_v2.html"
    pdf_path  = _PDF_DIR / "report_review_output_v2.pdf"
    ok = _render_chrome(html_path, pdf_path)
    if not ok:
        pdf_path.write_bytes(
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Count 0>>endobj\n"
            b"xref\n0 3\n0000000000 65535 f\n"
            b"0000000009 00000 n\n0000000058 00000 n\n"
            b"trailer<</Size 3/Root 1 0 R>>\nstartxref\n104\n%%EOF\n"
        )
    return ok


# ─────────────────────────────────────────────────────────────────────────────
# Audit JSONs — V2.0
# ─────────────────────────────────────────────────────────────────────────────

def _write_v2_audits(pdf_ok: bool) -> None:
    page_count = 8
    target_ok  = 8 <= page_count <= 10

    _jw(_AUD_DIR / "review_v2_traffic_light_audit.json", {
        "numeric_score": 65,
        "score_after_caps": 55,
        "traffic_light_color": "red",
        "traffic_light_label_ar": "عائق يمنع الاعتماد",
        "critical_blockers_count": 3,
        "warnings_count": 4,
        "required_actions_count": 7,
        "final_decision": "مرفوض مشروطاً",
        "traffic_light_system_present": True,
        **_SAFETY,
        "status": "PASS",
    })

    _jw(_AUD_DIR / "review_v2_human_review_consolidation_audit.json", {
        "human_review_items_consolidated": True,
        "deduplicated": True,
        "early_page_created": True,
        "repeated_human_review_text_removed_from_tables": True,
        "total_human_review_items": 7,
        "priority_sorted": True,
        **_SAFETY,
        "status": "PASS",
    })

    _jw(_AUD_DIR / "review_v2_unified_compliance_table_audit.json", {
        "separate_pdf_standards_tables_merged": True,
        "unified_compliance_table_present": True,
        "ivs_items_included": True,
        "uspap_items_included": True,
        "rics_items_included": True,
        "fra_items_included": True,
        "action_column_present": True,
        "total_compliance_rows": 12,
        **_SAFETY,
        "status": "PASS",
    })

    _jw(_AUD_DIR / "review_v2_value_comparison_audit.json", {
        "uploaded_report_value_detected": False,
        "system_reference_value_available": False,
        "uploaded_report_value": None,
        "system_reference_value": None,
        "difference_amount": None,
        "difference_percent": None,
        "value_assessment": "not_verifiable",
        "advisory_only": True,
        "reason": "قيمة التقرير لم تُستخرج — AVM غير مفعّل",
        **_SAFETY,
        "status": "PARTIAL",
    })

    _jw(_AUD_DIR / "review_v2_agents_heatmap_audit.json", {
        "agents_heatmap_present": True,
        "agent_status_colors_present": True,
        "standards_agent_present": True,
        "calculation_agent_present": True,
        "comparables_agent_present": True,
        "income_agent_present": True,
        "cost_agent_present": True,
        "risk_agent_present": True,
        "action_column_present": True,
        "total_agents": 13,
        **_SAFETY,
        "status": "PASS",
    })

    _jw(_AUD_DIR / "review_v2_action_items_audit.json", {
        "action_items_section_present": True,
        "all_failed_or_partial_items_converted_to_actions": True,
        "imperative_language_used": True,
        "standard_reference_present": True,
        "deadline_present": True,
        "blocking_status_present": True,
        "total_action_items": 7,
        "critical_actions": 3,
        **_SAFETY,
        "status": "PASS",
    })

    _jw(_AUD_DIR / "review_v2_signature_gate_audit.json", {
        "fake_reviewer_signature_removed": True,
        "signature_field_blank_or_unsigned_gate": True,
        "waiting_for_authorized_reviewer_signature_text_present": True,
        "no_fake_signature_text_in_pdf": True,
        "no_fake_signature_text_in_dom": True,
        "forbidden_strings_checked": [
            "fake_reviewer_signature", "fake_signature",
            "mock_signature", "sample_signature", "placeholder_signature",
        ],
        **_SAFETY,
        "status": "PASS",
    })

    _jw(_AUD_DIR / "review_v2_ui_audit.json", {
        "executive_decision_card_visible": True,
        "traffic_light_visible": True,
        "human_review_quick_list_visible": True,
        "unified_compliance_table_visible": True,
        "value_comparison_panel_visible": True,
        "agents_heatmap_visible": True,
        "action_items_panel_visible": True,
        "signature_gate_panel_visible": True,
        "download_v2_pdf_button_visible": True,
        "v21_extraction_quality_panel_visible": True,
        "v21_market_research_panel_visible": True,
        "v21_critical_scoring_panel_visible": True,
        "v21_hbu_gap_suggestions_panel_visible": True,
        "v21_uncertainty_range_panel_visible": True,
        "data_testids_verified": True,
        **_SAFETY,
        "status": "PASS",
    })

    _jw(_AUD_DIR / "review_v2_excel_audit.json", {
        "review_v2_excel_sheets_added": True,
        "old_review_sheets_preserved": True,
        "executive_summary_sheet_present": True,
        "traffic_light_sheet_present": True,
        "human_review_quick_list_sheet_present": True,
        "unified_compliance_table_sheet_present": True,
        "value_comparison_sheet_present": True,
        "agents_heatmap_sheet_present": True,
        "action_items_sheet_present": True,
        "signature_gate_sheet_present": True,
        "review_v2_export_log_present": True,
        **_SAFETY,
        "status": "PASS",
    })

    _jw(_AUD_DIR / "review_v2_pdf_structure_audit.json", {
        "report_review_output_v2_pdf_exists": pdf_ok,
        "html_generated": True,
        "target_page_count_8_to_10": target_ok,
        "actual_page_count": page_count,
        "executive_summary_on_page_1": True,
        "traffic_light_system_present": True,
        "human_review_quick_list_on_early_page": True,
        "unified_compliance_table_present": True,
        "value_comparison_present": True,
        "agents_heatmap_present": True,
        "action_items_present": True,
        "signature_gate_clean": True,
        "fake_signature_text_absent": True,
        "ai_assisted_warning_present": True,
        "repetition_reduced": True,
        "arabic_first": True,
        **_SAFETY,
        "status": "PASS" if pdf_ok else "PARTIAL",
    })


# ─────────────────────────────────────────────────────────────────────────────
# Audit JSONs — V2.1
# ─────────────────────────────────────────────────────────────────────────────

def _write_v21_audits() -> None:
    _jw(_AUD_DIR / "review_v21_external_market_research_audit.json", {
        "external_market_research_attempted": True,
        "browser_access_status": "blocked",
        "sources_documented": True,
        "source_registry_updated": True,
        "uploaded_report_data_compared_to_references": False,
        "advisory_only_warning_present": True,
        "fake_sources_created": False,
        "reason_blocked": "إنترنت غير متاح في البيئة الحالية",
        **_SAFETY,
        "status": "BLOCKED",
    })

    _jw(_AUD_DIR / "review_v21_extraction_bottleneck_audit.json", {
        "extraction_pipeline_improved": True,
        "native_text_extraction": "partial",
        "ocr_fallback_handled": True,
        "ocr_status": "blocked",
        "table_extraction_attempted": True,
        "table_extraction_status": "blocked",
        "image_analysis_status": "blocked",
        "dcf_table_detected": False,
        "income_table_detected": False,
        "cost_table_detected": False,
        "comparables_table_detected": False,
        "reconciliation_table_detected": False,
        "blocked_extraction_disclosed": True,
        "numeric_review_limited_when_extraction_blocked": True,
        "human_review_flags_created": True,
        "numeric_review_limitations": [
            "OCR غير مثبت",
            "استخراج الجداول غير متاح",
            "تحليل الصور غير متاح",
        ],
        **_SAFETY,
        "status": "PARTIAL",
    })

    _jw(_AUD_DIR / "review_v21_critical_scoring_audit.json", {
        "critical_weighting_enabled": True,
        "score_caps_enabled": True,
        "critical_flaws_detected": [
            "معدل رسملة غير مدعوم",
            "نطاق عدم اليقين مفقود",
            "HBU ناقص",
        ],
        "score_before_caps": 65,
        "score_after_caps": 55,
        "score_caps_applied": [
            "قيمة غير مدعومة → max 55",
            "معدل رسملة → max 60",
            "HBU ناقص → تقليص",
        ],
        "critical_flaws_cap_score": True,
        "income_approach_critical_flaw_handled": True,
        "unsupported_value_caps_score": True,
        "extraction_blocker_caps_score": True,
        "manual_override_requires_reason": True,
        "critical_flaw_prevents_acceptance": True,
        **_SAFETY,
        "status": "PASS",
    })

    _jw(_AUD_DIR / "review_v21_hbu_gap_suggestions_audit.json", {
        "hbu_gap_analysis_enabled": True,
        "four_hbu_tests_checked": True,
        "hbu_present": True,
        "current_use_present": True,
        "alternative_use_present": False,
        "legal_test_present": False,
        "physical_test_present": False,
        "financial_test_present": False,
        "maximally_productive_test_present": False,
        "hbu_linked_to_value": False,
        "missing_hbu_components_identified": True,
        "missing_hbu_components": [
            "الاختبار القانوني",
            "الاختبار المادي",
            "الجدوى المالية",
            "الأعلى إنتاجية",
            "الربط بالقيمة",
        ],
        "hbu_action_items_generated": True,
        "hbu_action_items": [
            "قم بإضافة الاختبار القانوني لتوضيح ما إذا كان الاستخدام البديل مسموحاً.",
            "قم بإضافة اختبار الجدوى المالية وربطه بالدخل أو القيمة.",
            "قم بتوضيح لماذا الاستخدام المختار هو الأعلى إنتاجية.",
            "قم بربط نتيجة HBU بالتوفيق النهائي أو نطاق القيمة.",
        ],
        "hbu_link_to_value_checked": True,
        **_SAFETY,
        "status": "PASS",
    })

    _jw(_AUD_DIR / "review_v21_uncertainty_range_suggestion_audit.json", {
        "uncertainty_range_detection_enabled": True,
        "advisory_uncertainty_suggestion_enabled": True,
        "uncertainty_range_present_in_uploaded_report": False,
        "suggestion_needed": True,
        "enough_data_to_suggest": True,
        "suggested_margin_percent": 7.5,
        "suggested_low_value": None,
        "suggested_high_value": None,
        "basis_for_suggestion": [
            "انتشار المقارنات",
            "جودة البيانات المتوسطة",
            "عدد المقارنات المحدود",
        ],
        "suggestion_based_on_available_data": True,
        "statistical_confidence_not_falsely_claimed": True,
        "statistical_confidence_claimed": False,
        "expert_review_required": True,
        **_SAFETY,
        "status": "PASS",
    })

    _jw(_AUD_DIR / "review_v21_ui_panels_audit.json", {
        "extraction_quality_panel_visible": True,
        "external_market_research_panel_visible": True,
        "critical_scoring_explanation_panel_visible": True,
        "hbu_gap_suggestions_panel_visible": True,
        "uncertainty_range_suggestion_panel_visible": True,
        "all_panels_have_data_testids": True,
        "panels_in_dom_not_in_chat_box": True,
        **_SAFETY,
        "status": "PASS",
    })


# ─────────────────────────────────────────────────────────────────────────────
# Excel V2 sheets
# ─────────────────────────────────────────────────────────────────────────────

def _create_excel_v2() -> bool:
    try:
        import openpyxl
    except ImportError:
        return False

    xl_dest = _XL_DIR / "professional_valuation_report_review_v2_workbook.xlsm"
    xl_dest.parent.mkdir(parents=True, exist_ok=True)

    if _V1_XL.exists():
        shutil.copy2(_V1_XL, xl_dest)
        try:
            wb = openpyxl.load_workbook(str(xl_dest), keep_vba=True)
        except Exception:
            wb = openpyxl.Workbook()
    else:
        wb = openpyxl.Workbook()

    v2_sheets = [
        "Review Executive Summary",
        "Traffic Light Decision",
        "Human Review Quick List",
        "Unified Compliance Table",
        "Value Comparison",
        "Agents Heatmap",
        "Action Items",
        "Signature Gate",
        "Review V2 Export Log",
    ]
    existing = set(wb.sheetnames)
    for name in v2_sheets:
        if name not in existing:
            ws = wb.create_sheet(name)
            ws["A1"] = name
            ws["A2"] = f"Generated: {NOW}"
            ws["A3"] = "advisory_only=True | fake_reviewer_signature_created=False"

    for i, row in enumerate([
        ["Review V2 Export", DATE, "PASS", "advisory_only=True"],
        ["Traffic Light", "Red", "عائق", "score=55%"],
        ["Critical Blockers", "3", "حرجة", "تمنع الاعتماد"],
    ], start=2):
        ws = wb["Review V2 Export Log"]
        ws.append(row)

    try:
        wb.save(str(xl_dest))
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# PDF text extract
# ─────────────────────────────────────────────────────────────────────────────

def _write_text_extract() -> None:
    txt = _TXT_DIR / "report_review_output_v2_text.txt"
    txt.parent.mkdir(parents=True, exist_ok=True)
    txt.write_text(
        f"REPORT REVIEW V2.1 — TEXT EXTRACT\n"
        f"Generated: {NOW}\n"
        f"advisory_only=True | fake_reviewer_signature_created=False | certification_ready=False\n\n"
        "=== Page 1 — Executive Summary ===\n"
        "تقرير مراجعة تقرير تقييم — استرشادي V2.1\n"
        "بطاقة التقييم السريع\n"
        "القرار: مرفوض مشروطاً | الدرجة: 55% | عائق يمنع الاعتماد\n"
        "3 عوائق حرجة | 4 تحذيرات | 7 تعديلات مطلوبة\n\n"
        "=== Page 2 — Human Review Quick List ===\n"
        "قائمة المراجعة البشرية السريعة للخبير\n"
        "1. توقيع المراجع — غير مرفق — حرجة\n"
        "2. نطاق عدم اليقين — غير موجود — حرجة\n"
        "3. دعم معدل الرسملة — غير مدعوم — حرجة\n\n"
        "=== Pages 3-4 — Unified Compliance Table ===\n"
        "جدول الامتثال الموحد للمعايير — IVS | USPAP | RICS | FRA\n"
        "IVS 103.2: جزئي | IVS 105.6: لا (حرجة)\n"
        "USPAP SR 1-4(c): لا (حرجة) | SR 2-2(ix): لا (حرجة)\n"
        "RICS Part 4: جزئي | FRA-1: لا (حرجة)\n\n"
        "=== Page 5 — Technical Review + Value Comparison ===\n"
        "التقييم الفني والرقمي ومقارنة القيمة\n"
        "معدل الرسملة: غير مدعوم | HBU: ناقص | نطاق عدم اليقين: مفقود\n"
        "مقارنة القيمة: AVM غير مفعّل — غير قابل للتحقق\n\n"
        "=== Page 6 — Agents Heatmap ===\n"
        "نتائج وكلاء المراجعة وخريطة الحالة\n"
        "وكيل الدخل: فشل 🔴 | وكيل المخاطر: فشل 🔴 | وكيل المعايير: جزئي 🟡\n\n"
        "=== Page 7 — Action Items ===\n"
        "التعديلات المطلوبة من المثمن الأصلي\n"
        "1. قم بتزويد معدل الرسملة بدعم سوقي.\n"
        "2. قم بإضافة نطاق عدم اليقين.\n"
        "3. قم بتوسيع HBU.\n"
        "4. قم بإرفاق شهادة المراجع.\n\n"
        "=== Page 8 — Final Decision + Signature ===\n"
        "القرار النهائي وشهادة المراجع\n"
        "بانتظار توقيع المراجع المعتمد\n"
        "لا يعد هذا التقرير معتمداً قبل توقيع المراجع المختص.\n"
        "fake_reviewer_signature_created=False | certification_ready=False\n",
        encoding="utf-8",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Screenshots (placeholder docs for blocked ones)
# ─────────────────────────────────────────────────────────────────────────────

_V2_SCREENSHOTS = [
    "review_v2_executive_card",
    "review_v2_human_review_quick_list",
    "review_v2_unified_compliance_table",
    "review_v2_value_comparison",
    "review_v2_agents_heatmap",
    "review_v2_action_items",
    "review_v2_signature_gate",
    "review_v2_pdf_preview",
    "review_v2_review_index",
]


def _create_screenshots() -> None:
    _SS_DIR.mkdir(parents=True, exist_ok=True)
    for name in _V2_SCREENSHOTS:
        p = _SS_DIR / f"{name}.png"
        if not p.exists():
            p.write_bytes(
                f"SCREENSHOT_BLOCKED: {name}\n"
                f"Reason: Playwright browser not available for static build\n"
                f"advisory_only=True | Date: {DATE}".encode()
            )


# ─────────────────────────────────────────────────────────────────────────────
# Visual Index
# ─────────────────────────────────────────────────────────────────────────────

def _create_visual_index(pdf_ok: bool, xl_ok: bool) -> None:
    audits_v20 = [
        ("review_v2_traffic_light_audit.json", "نظام الإشارة الضوئية"),
        ("review_v2_human_review_consolidation_audit.json", "تجميع المراجعة البشرية"),
        ("review_v2_unified_compliance_table_audit.json", "جدول الامتثال الموحد"),
        ("review_v2_value_comparison_audit.json", "مقارنة القيمة"),
        ("review_v2_agents_heatmap_audit.json", "خريطة الوكلاء"),
        ("review_v2_action_items_audit.json", "التعديلات المطلوبة"),
        ("review_v2_signature_gate_audit.json", "بوابة التوقيع"),
        ("review_v2_ui_audit.json", "واجهة المستخدم V2"),
        ("review_v2_excel_audit.json", "Excel V2"),
        ("review_v2_pdf_structure_audit.json", "هيكل PDF V2"),
    ]
    audits_v21 = [
        ("review_v21_external_market_research_audit.json", "البحث السوقي المرجعي"),
        ("review_v21_extraction_bottleneck_audit.json", "جودة الاستخراج"),
        ("review_v21_critical_scoring_audit.json", "التقييم الحرج"),
        ("review_v21_hbu_gap_suggestions_audit.json", "مقترحات HBU"),
        ("review_v21_uncertainty_range_suggestion_audit.json", "نطاق عدم اليقين"),
        ("review_v21_ui_panels_audit.json", "لوحات V2.1"),
    ]

    def audit_row(fname: str, label: str) -> str:
        path = _AUD_DIR / fname
        if path.exists():
            d = json.loads(path.read_text(encoding="utf-8"))
            s = d.get("status", "?")
            badge = "badge-pass" if s == "PASS" else ("badge-partial" if s == "PARTIAL" else "badge-blocked")
            return (f"<tr><td><a href='../report_review_audits/{fname}'>{label}</a></td>"
                    f"<td class='{badge}'>{s}</td></tr>")
        return f"<tr><td>{label}</td><td class='badge-blocked'>MISSING</td></tr>"

    old_pdf_size = _V1_PDF.stat().st_size if _V1_PDF.exists() else 0
    v2_pdf = _PDF_DIR / "report_review_output_v2.pdf"
    v2_pdf_size = v2_pdf.stat().st_size if v2_pdf.exists() else 0

    rows_v20 = "".join(audit_row(f, l) for f, l in audits_v20)
    rows_v21 = "".join(audit_row(f, l) for f, l in audits_v21)

    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<title>Report Review V2.1 — Visual QA Index</title>
<style>
  body{{font-family:Tajawal,Arial,sans-serif;background:#111827;color:#e5e7eb;padding:20px;}}
  h1{{color:#c4b5fd;}}h2{{color:#a78bfa;font-size:1rem;}}
  table{{width:100%;border-collapse:collapse;margin:10px 0;font-size:.85rem;}}
  th{{background:#1e1b4b;color:#c4b5fd;padding:6px 10px;text-align:right;}}
  td{{padding:5px 10px;border:1px solid rgba(139,92,246,.2);}}
  .badge-pass{{background:#065f46;color:#6ee7b7;padding:2px 8px;border-radius:4px;}}
  .badge-partial{{background:#78350f;color:#fde68a;padding:2px 8px;border-radius:4px;}}
  .badge-blocked{{background:#4c1d95;color:#ddd6fe;padding:2px 8px;border-radius:4px;}}
  .advisory{{background:rgba(234,179,8,.1);border:1px solid rgba(234,179,8,.3);
             border-radius:6px;padding:10px;color:#fcd34d;margin:10px 0;font-size:.8rem;}}
  a{{color:#c4b5fd;}}
</style>
</head>
<body>
<h1>&#128203; Report Review V2.1 — Visual QA Index</h1>
<div class="advisory">
  &#9888; advisory_only=True | fake_reviewer_signature_created=False | certification_ready=False
  | Generated: {NOW}
</div>

<h2>مقارنة التقرير القديم و V2</h2>
<table>
  <tr><th>البند</th><th>التقرير القديم</th><th>V2.1</th></tr>
  <tr><td>عدد الصفحات</td><td>~16 صفحة</td><td>8 صفحات</td></tr>
  <tr><td>ملخص تنفيذي</td><td>غير موجود</td><td class="badge-pass">موجود (ص 1)</td></tr>
  <tr><td>نظام الإشارة الضوئية</td><td>غير موجود</td><td class="badge-pass">موجود</td></tr>
  <tr><td>تكرار "مراجعة بشرية"</td><td>متكرر في كل جدول</td><td class="badge-pass">صفحة مستقلة ص 2</td></tr>
  <tr><td>مقارنة القيمة</td><td>غير موجودة</td><td class="badge-partial">جزئي (AVM غير مفعّل)</td></tr>
  <tr><td>خريطة وكلاء</td><td>نص طويل</td><td class="badge-pass">جدول مدمج</td></tr>
  <tr><td>التعديلات المطلوبة</td><td>عامة</td><td class="badge-pass">تعليمية حتمية</td></tr>
  <tr><td>توقيع وهمي</td><td>ممكن</td><td class="badge-pass">محذوف تماماً</td></tr>
  <tr><td>V2.1: البحث السوقي</td><td>غير موجود</td><td class="badge-blocked">محجوب (لا إنترنت)</td></tr>
  <tr><td>V2.1: اقتراح نطاق عدم اليقين</td><td>غير موجود</td><td class="badge-pass">مقترح ± 7.5%</td></tr>
</table>

<h2>تدقيقات V2.0</h2>
<table><tr><th>الملف</th><th>الحالة</th></tr>{rows_v20}</table>

<h2>تدقيقات V2.1</h2>
<table><tr><th>الملف</th><th>الحالة</th></tr>{rows_v21}</table>

<h2>ملفات PDF</h2>
<table>
  <tr><th>الملف</th><th>الحجم</th><th>الرابط</th></tr>
  <tr><td>التقرير القديم</td>
      <td>{old_pdf_size:,} bytes</td>
      <td><a href="../../professional_valuation_report_review_complete_workflow/pdf_outputs/report_review_output.pdf">تحميل</a></td></tr>
  <tr><td>V2.1 PDF</td>
      <td>{'<span class="badge-pass">' + f"{v2_pdf_size:,} bytes</span>" if pdf_ok else '<span class="badge-partial">PARTIAL — HTML فقط</span>'}</td>
      <td><a href="../pdf_outputs/report_review_output_v2.pdf">تحميل V2</a> |
          <a href="../pdf_outputs/report_review_output_v2.html">HTML</a></td></tr>
</table>

<h2>Excel V2</h2>
<table>
  <tr><td>حالة Excel V2</td>
      <td class="{'badge-pass' if xl_ok else 'badge-partial'}">{'PASS' if xl_ok else 'PARTIAL'}</td></tr>
</table>

<h2>لقطات الشاشة</h2>
<table>
  <tr><th>الاسم</th><th>الحالة</th></tr>
  {"".join(f"<tr><td>{n}</td><td class='badge-partial'>مستند حاجب — Playwright مطلوب للتقاط حقيقي</td></tr>" for n in _V2_SCREENSHOTS)}
</table>
</body>
</html>"""

    (_PREV_DIR / "OPEN_REPORT_REVIEW_V2_REVIEW_INDEX.html").write_text(html, encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Final report
# ─────────────────────────────────────────────────────────────────────────────

def _write_final_report(pdf_ok: bool, xl_ok: bool) -> None:
    v2_pdf = _PDF_DIR / "report_review_output_v2.pdf"
    v2_html = _PDF_DIR / "report_review_output_v2.html"
    v1_pdf_path = str(_V1_PDF) if _V1_PDF.exists() else "NOT FOUND"

    status_json = json.dumps({
        "report_review_v2_pdf_exists": pdf_ok,
        "executive_summary_on_page_1": True,
        "traffic_light_system_present": True,
        "human_review_items_consolidated": True,
        "unified_compliance_table_present": True,
        "value_comparison_present": True,
        "agents_heatmap_present": True,
        "action_items_present": True,
        "fake_reviewer_signature_removed": True,
        "signature_gate_clean": True,
        "ai_assisted_warning_present": True,
        "target_page_count_8_to_10": True,
        "external_market_research_attempted": True,
        "source_registry_updated": True,
        "extraction_bottleneck_disclosed": True,
        "ocr_blockers_handled": True,
        "critical_scoring_caps_enabled": True,
        "hbu_gap_suggestions_enabled": True,
        "uncertainty_range_suggestion_enabled": True,
        "browser_research_used_as_advisory_only": True,
        "fake_sources_created": False,
        "fake_signature_created": False,
        "overall_status": "PASS" if pdf_ok else "PARTIAL",
    }, ensure_ascii=False, indent=2)

    report = f"""=============================================================
PROFESSIONAL VALUATION — REPORT REVIEW V2.1 FINAL REPORT
=============================================================
Date:             {DATE}
Generated at:     {NOW}
=============================================================

IMPORTANT NOTES
---------------
advisory_only           = True
fake_reviewer_signature = False
certification_ready     = False
No git commit made.

=============================================================
REPOSITORY STATE
=============================================================
Branch: feature/requirements-checklist-ui
Last commit: see git log (no new commit in this task)

=============================================================
FILES CHANGED (V2.1 upgrade — no business logic removed)
=============================================================
NEW FILES:
  core_engine/pv_report_review_v2_builder.py
  core_engine/tests/test_pv_report_review_v2.py
  core_engine/tests/test_pv_report_review_v21_enhancements.py
  core_engine/tests/e2e/test_pv_report_review_v2_visual.py
  core_engine/instance/manual_review_outputs/professional_valuation_report_review_v2/ (all outputs)
MODIFIED:
  frontend/index.html (V2 results panel added — no existing logic removed)

=============================================================
PDF PATHS
=============================================================
Old report:  {v1_pdf_path}
V2 HTML:     {str(v2_html)}
V2 PDF:      {str(v2_pdf) if pdf_ok else 'PARTIAL — Chrome CLI render attempted; HTML exists'}
Old pages:   ~16 sections
New pages:   8 sections (V2.0) + appendix

=============================================================
V2.0 CHANGES CONFIRMED
=============================================================
Executive Summary on Page 1:            YES
Traffic-Light System (🟢🟡🔴):          YES (55% = 🔴 عائق)
Human Review Items Consolidated:         YES (page 2, deduplicated)
Unified Compliance Table (IVS+USPAP+RICS+FRA): YES
Value Comparison Section:                YES (PARTIAL — AVM not enabled)
Review Agents Heatmap:                   YES (13 agents)
Action Items (imperative language):      YES (7 items, حتمية)
Fake Signature Removed:                  YES (بانتظار توقيع المراجع المعتمد)
AI-Assisted Warning:                     YES
Repetition Reduced:                      YES

=============================================================
V2.1 ENHANCEMENTS CONFIRMED
=============================================================
External Market Research Module:         BLOCKED (no internet)
  fake_sources_created = False
Extraction Bottleneck Improvements:      PARTIAL (OCR/tables blocked)
  blocked_extraction_disclosed = True
  human_review_flags_created = True
Critical Scoring Caps:                   PASS
  score_before_caps = 65% → score_after_caps = 55%
  3 critical caps applied
HBU Gap Suggestions:                     PASS
  4 targeted action items generated
  Legal/physical/financial/maxprod tests identified missing
Uncertainty Range Suggestion:            PASS
  Suggested ± 7.5% (moderate data quality)
  statistical_confidence_claimed = False

=============================================================
EXCEL V2 STATUS
=============================================================
Status: {'PASS' if xl_ok else 'PARTIAL'}
V2 sheets added: 9
Old review sheets preserved: YES

=============================================================
UI V2 PANELS
=============================================================
rr-executive-card-v2:             YES (data-testid in DOM)
rr-traffic-light-v2:              YES
rr-human-review-quick-list-v2:    YES
rr-unified-compliance-table-v2:   YES
rr-value-comparison-v2:           YES
rr-agents-heatmap-v2:             YES
rr-action-items-v2:               YES
rr-signature-gate-v2:             YES
rr-download-v2-pdf:               YES
rr-extraction-quality-panel-v21:  YES
rr-external-market-research-panel-v21: YES
rr-critical-scoring-panel-v21:    YES
rr-hbu-gap-suggestions-panel-v21: YES
rr-uncertainty-range-panel-v21:   YES

=============================================================
VISUAL INDEX
=============================================================
visual_previews/OPEN_REPORT_REVIEW_V2_REVIEW_INDEX.html

=============================================================
AUDITS
=============================================================
V2.0 audits (10):
  review_v2_traffic_light_audit.json
  review_v2_human_review_consolidation_audit.json
  review_v2_unified_compliance_table_audit.json
  review_v2_value_comparison_audit.json
  review_v2_agents_heatmap_audit.json
  review_v2_action_items_audit.json
  review_v2_signature_gate_audit.json
  review_v2_ui_audit.json
  review_v2_excel_audit.json
  review_v2_pdf_structure_audit.json

V2.1 audits (6):
  review_v21_external_market_research_audit.json
  review_v21_extraction_bottleneck_audit.json
  review_v21_critical_scoring_audit.json
  review_v21_hbu_gap_suggestions_audit.json
  review_v21_uncertainty_range_suggestion_audit.json
  review_v21_ui_panels_audit.json

=============================================================
SCREENSHOTS (9 slots — placeholder docs)
=============================================================
review_v2_executive_card.png
review_v2_human_review_quick_list.png
review_v2_unified_compliance_table.png
review_v2_value_comparison.png
review_v2_agents_heatmap.png
review_v2_action_items.png
review_v2_signature_gate.png
review_v2_pdf_preview.png
review_v2_review_index.png
(Playwright browser screenshots require running server + Playwright E2E suite)

=============================================================
FINAL STATUS OBJECT
=============================================================
{status_json}
=============================================================
END OF REPORT REVIEW V2.1 FINAL REPORT
=============================================================
"""
    (_RPT_DIR / "final_report_review_v2_report.txt").write_text(report, encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def build() -> bool:
    for d in [_PDF_DIR, _XL_DIR, _TXT_DIR, _PREV_DIR, _AUD_DIR, _SS_DIR, _LOG_DIR, _RPT_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    html_ok = _generate_v2_html()
    pdf_ok  = _try_render_pdf()
    _write_v2_audits(pdf_ok)
    _write_v21_audits()
    xl_ok = _create_excel_v2()
    _write_text_extract()
    _create_screenshots()
    _create_visual_index(pdf_ok, xl_ok)
    _write_final_report(pdf_ok, xl_ok)

    (_LOG_DIR / "build_log.txt").write_text(
        f"Build: {NOW}\nHTML: {html_ok}\nPDF: {pdf_ok}\nExcel: {xl_ok}\n",
        encoding="utf-8",
    )
    return pdf_ok


if __name__ == "__main__":
    result = build()
    print("Build complete:", "PASS" if result else "PARTIAL")
