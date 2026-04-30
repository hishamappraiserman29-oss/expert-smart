# -*- coding: utf-8 -*-
"""
library_scanner.py — المكتبة المرجعية الذكية
============================================
يُنفّذ:
  1. مسح دوري لمصادر التقارير العقارية المفتوحة (CMA / FRA / RICS / IVSC)
  2. استخراج البيانات الوصفية (العنوان / التاريخ / القطاع / المصدر)
  3. فلترة التكرار عبر تشابه العنوان + بصمة المحتوى
  4. فهرسة محلية في library_index.json
  5. API للبحث والتصفية والتحميل
"""

import os, sys, re, json, time, hashlib, urllib.request, urllib.parse
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

_BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
_LIB_DIR     = os.path.join(_BASE_DIR, "data", "library")
_INDEX_FILE  = os.path.join(_LIB_DIR, "library_index.json")
os.makedirs(_LIB_DIR, exist_ok=True)

# ══════════════════════════════════════════════════════════════════════════════
# مصادر الفحص — قابلة للتوسعة
# ══════════════════════════════════════════════════════════════════════════════
_SOURCES: List[Dict[str, Any]] = [
    {
        "id":       "cma_sa",
        "name":     "هيئة السوق المالية السعودية (CMA)",
        "country":  "SA",
        "base_url": "https://cma.org.sa",
        "search_url": "https://cma.org.sa/ar/RulesRegulations/Regulations/Pages/default.aspx",
        "type":     "regulatory",
        "sectors":  ["residential", "commercial", "industrial"],
        "enabled":  True,
    },
    {
        "id":       "fra_eg",
        "name":     "الهيئة العامة للرقابة المالية (FRA)",
        "country":  "EG",
        "base_url": "https://fra.gov.eg",
        "search_url": "https://fra.gov.eg/fra-arabic/index.php/legislation",
        "type":     "regulatory",
        "sectors":  ["residential", "commercial"],
        "enabled":  True,
    },
    {
        "id":       "ivsc",
        "name":     "International Valuation Standards Council (IVSC)",
        "country":  "INT",
        "base_url": "https://www.ivsc.org",
        "search_url": "https://www.ivsc.org/standards/",
        "type":     "standards",
        "sectors":  ["all"],
        "enabled":  True,
    },
    {
        "id":       "rics",
        "name":     "RICS — Royal Institution of Chartered Surveyors",
        "country":  "INT",
        "base_url": "https://www.rics.org",
        "search_url": "https://www.rics.org/profession-standards/rics-standards-and-guidance/",
        "type":     "standards",
        "sectors":  ["all"],
        "enabled":  True,
    },
    {
        "id":       "realestate_eg",
        "name":     "الجهاز المركزي للتعبئة والإحصاء (CAPMAS)",
        "country":  "EG",
        "base_url": "https://www.capmas.gov.eg",
        "search_url": "https://www.capmas.gov.eg/Pages/StaticPages.aspx?page_id=5035",
        "type":     "statistics",
        "sectors":  ["residential", "agricultural"],
        "enabled":  True,
    },
    {
        "id":       "tadawul",
        "name":     "تداول — سوق الأسهم السعودية",
        "country":  "SA",
        "base_url": "https://www.tadawul.com.sa",
        "search_url": "https://www.tadawul.com.sa/wps/portal/tadawul/markets/real-estate",
        "type":     "market_data",
        "sectors":  ["residential", "commercial", "hospitality"],
        "enabled":  True,
    },
]

# ══════════════════════════════════════════════════════════════════════════════
# هيكل سجل المكتبة
# ══════════════════════════════════════════════════════════════════════════════
_EMPTY_RECORD: Dict[str, Any] = {
    "id":           "",        # MD5 hash من العنوان + المصدر
    "title":        "",
    "title_ar":     "",
    "source_id":    "",
    "source_name":  "",
    "country":      "",
    "doc_type":     "",        # valuation_report | standard | circular | statistics
    "sector":       "",        # residential | commercial | industrial | all
    "date":         "",
    "url":          "",
    "file_path":    "",        # مسار الملف المحمّل محلياً (فارغ إذا لم يُحمَّل)
    "summary":      "",        # ملخص قصير (يُستخرج أو يُولَّد)
    "pages":        0,
    "language":     "ar",
    "tags":         [],
    "style_id":     "",        # مرتبط بـ report_tuner profile إذا تم التحليل
    "added_at":     "",
    "content_hash": "",        # للكشف عن التكرار
    "is_manual":    False,     # رُفع يدوياً من المستخدم
    "quality_score": 0,        # 1-10 جودة الوثيقة
}

# ══════════════════════════════════════════════════════════════════════════════
# تحميل وحفظ الفهرس
# ══════════════════════════════════════════════════════════════════════════════
def _load_index() -> List[Dict[str, Any]]:
    if os.path.exists(_INDEX_FILE):
        try:
            with open(_INDEX_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_index(records: List[Dict[str, Any]]) -> None:
    with open(_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def _make_id(title: str, source_id: str) -> str:
    return hashlib.md5(f"{title}|{source_id}".encode()).hexdigest()[:12]


def _content_hash(text: str) -> str:
    return hashlib.sha1(text[:2000].encode(errors="replace")).hexdigest()[:16]


# ══════════════════════════════════════════════════════════════════════════════
# فلترة التكرار
# ══════════════════════════════════════════════════════════════════════════════
def _title_similarity(a: str, b: str) -> float:
    """تشابه بسيط بين عنوانين عبر مقارنة الكلمات المشتركة"""
    a_words = set(re.findall(r'\w+', a.lower()))
    b_words = set(re.findall(r'\w+', b.lower()))
    if not a_words or not b_words:
        return 0.0
    return len(a_words & b_words) / max(len(a_words), len(b_words))


def is_duplicate(record: Dict[str, Any], existing: List[Dict[str, Any]]) -> bool:
    """يُعيد True إذا كانت الوثيقة مكررة"""
    # 1. تطابق exact ID
    if any(r["id"] == record["id"] for r in existing):
        return True
    # 2. تطابق content hash
    if record.get("content_hash") and any(
        r.get("content_hash") == record["content_hash"] for r in existing
    ):
        return True
    # 3. تشابه العنوان ≥ 85%
    for r in existing:
        if _title_similarity(record["title"], r["title"]) >= 0.85:
            return True
    return False


# ══════════════════════════════════════════════════════════════════════════════
# جلب صفحة ويب بشكل آمن
# ══════════════════════════════════════════════════════════════════════════════
def _safe_fetch(url: str, timeout: int = 15) -> str:
    """يجلب صفحة HTML مع User-Agent مناسب"""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; ExpertSmartBot/1.0; "
                    "+https://expertsmart.ai/bot)"
                ),
                "Accept-Language": "ar,en;q=0.9",
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            charset = r.headers.get_content_charset() or "utf-8"
            return r.read().decode(charset, errors="replace")
    except Exception as e:
        print(f"  [scanner] fetch failed ({url[:60]}): {e}")
        return ""


def _extract_links(html: str, base_url: str, ext_filter: tuple = (".pdf",)) -> List[str]:
    """يستخرج روابط الـ PDF من صفحة HTML"""
    pattern = r'href=["\']([^"\']+)["\']'
    links = re.findall(pattern, html, re.IGNORECASE)
    result = []
    for lnk in links:
        if any(lnk.lower().endswith(ext) for ext in ext_filter):
            if lnk.startswith("http"):
                result.append(lnk)
            elif lnk.startswith("/"):
                domain = re.match(r'https?://[^/]+', base_url)
                if domain:
                    result.append(domain.group() + lnk)
    return list(dict.fromkeys(result))  # إزالة التكرار مع الحفاظ على الترتيب


def _extract_title_from_html(html: str) -> str:
    """يستخرج عنوان الصفحة"""
    m = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
    return re.sub(r'\s+', ' ', m.group(1)).strip() if m else ""


def _extract_title_from_url(url: str) -> str:
    """يستنتج عنواناً من اسم الملف في الـ URL"""
    name = os.path.basename(urllib.parse.urlparse(url).path)
    name = re.sub(r'\.\w+$', '', name)          # إزالة الامتداد
    name = re.sub(r'[_\-]+', ' ', name)         # تحويل _ و - إلى مسافات
    return name.strip() or url


# ══════════════════════════════════════════════════════════════════════════════
# دوال المسح لكل مصدر
# ══════════════════════════════════════════════════════════════════════════════
def _scan_source(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    """يمسح مصدراً واحداً ويُعيد قائمة بالسجلات المُكتشفة"""
    records = []
    html = _safe_fetch(source["search_url"])
    if not html:
        return records

    links = _extract_links(html, source["base_url"], (".pdf", ".PDF"))
    print(f"  [scanner] {source['name']}: {len(links)} PDF(s) found")

    for url in links[:15]:   # حد أقصى 15 وثيقة لكل مصدر في كل جلسة
        title  = _extract_title_from_url(url)
        rec_id = _make_id(title, source["id"])

        rec = dict(_EMPTY_RECORD)
        rec["id"]          = rec_id
        rec["title"]       = title
        rec["source_id"]   = source["id"]
        rec["source_name"] = source["name"]
        rec["country"]     = source["country"]
        rec["url"]         = url
        rec["doc_type"]    = _guess_doc_type(url, title)
        rec["sector"]      = _guess_sector(url, title)
        rec["language"]    = "ar" if source["country"] in ("EG", "SA") else "en"
        rec["added_at"]    = datetime.now().strftime("%Y-%m-%d")
        rec["quality_score"] = _estimate_quality(source, title)

        records.append(rec)

    return records


def _guess_doc_type(url: str, title: str) -> str:
    text = (url + " " + title).lower()
    if re.search(r'valuation|تقييم|apprais', text):
        return "valuation_report"
    if re.search(r'standard|معيار|rics|ivs|taqeem', text):
        return "standard"
    if re.search(r'circular|تعميم|نشرة', text):
        return "circular"
    if re.search(r'statistic|إحصاء|بيانات', text):
        return "statistics"
    return "general"


def _guess_sector(url: str, title: str) -> str:
    text = (url + " " + title).lower()
    if re.search(r'سكني|residential|villa|شقة|apartment', text):
        return "residential"
    if re.search(r'تجاري|commercial|retail|مول|mall', text):
        return "commercial"
    if re.search(r'صناعي|industrial|مصنع|مستودع', text):
        return "industrial"
    if re.search(r'فندق|hotel|hospitality|سياحي', text):
        return "hospitality"
    if re.search(r'زراعي|agricultural|أرض', text):
        return "agricultural"
    return "all"


def _estimate_quality(source: Dict[str, Any], title: str) -> int:
    """تقدير أولي لجودة الوثيقة 1-10"""
    score = 5
    # مصادر تنظيمية → أعلى ثقة
    if source["type"] in ("regulatory", "standards"):
        score += 2
    # وثائق بها كلمات جودة
    if re.search(r'معيار|نموذج|IVS|RICS|TAQEEM', title, re.IGNORECASE):
        score += 1
    if re.search(r'تقييم|valuation|apprais', title, re.IGNORECASE):
        score += 1
    return min(10, score)


# ══════════════════════════════════════════════════════════════════════════════
# إضافة وثيقة يدوية (رفع المستخدم)
# ══════════════════════════════════════════════════════════════════════════════
def add_manual_document(
    title: str,
    text: str,
    filename: str,
    sector: str = "all",
    doc_type: str = "valuation_report",
) -> Dict[str, Any]:
    """يُضيف وثيقة رُفعت يدوياً إلى المكتبة"""
    library = _load_index()

    rec = dict(_EMPTY_RECORD)
    rec["id"]           = _make_id(title, "manual_" + datetime.now().strftime("%Y%m%d%H%M%S"))
    rec["title"]        = title
    rec["source_id"]    = "manual"
    rec["source_name"]  = "رفع يدوي"
    rec["country"]      = "manual"
    rec["doc_type"]     = doc_type
    rec["sector"]       = sector
    rec["language"]     = "ar" if len(re.findall(r'[\u0600-\u06FF]', text)) > 50 else "en"
    rec["added_at"]     = datetime.now().strftime("%Y-%m-%d")
    rec["is_manual"]    = True
    rec["content_hash"] = _content_hash(text)
    rec["quality_score"] = 8   # الوثائق اليدوية تحظى بدرجة أعلى
    rec["summary"]      = text[:300].replace("\n", " ") + "..."

    # تحقق من التكرار
    if is_duplicate(rec, library):
        return {"status": "duplicate", "record": rec}

    # حفظ ملف النص محلياً
    safe_name = re.sub(r'[^\w\-_]', '_', title)[:40]
    txt_path  = os.path.join(_LIB_DIR, f"{rec['id']}_{safe_name}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)
    rec["file_path"] = txt_path

    library.append(rec)
    _save_index(library)
    print(f"  [library] Added manual: {title[:50]}")
    return {"status": "added", "record": rec}


# ══════════════════════════════════════════════════════════════════════════════
# المسح الدوري الكامل
# ══════════════════════════════════════════════════════════════════════════════
def scan_all_sources(max_per_source: int = 10) -> Dict[str, Any]:
    """
    يمسح كل المصادر المُفعَّلة ويُضيف الوثائق الجديدة إلى الفهرس.
    يُعيد إحصاء الإضافات والتكرارات.
    """
    library  = _load_index()
    added    = 0
    skipped  = 0
    errors   = 0

    for source in _SOURCES:
        if not source.get("enabled"):
            continue
        try:
            print(f"  [scanner] Scanning: {source['name']}...")
            new_records = _scan_source(source)
            for rec in new_records[:max_per_source]:
                if is_duplicate(rec, library):
                    skipped += 1
                else:
                    library.append(rec)
                    added += 1
        except Exception as e:
            print(f"  [scanner] Source {source['id']} error: {e}")
            errors += 1

    if added > 0:
        _save_index(library)
        print(f"  [scanner] ✓ Scan complete: +{added} new | {skipped} duplicates | {errors} errors")

    return {
        "added":    added,
        "skipped":  skipped,
        "errors":   errors,
        "total":    len(library),
        "scanned_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# البحث والتصفية
# ══════════════════════════════════════════════════════════════════════════════
def search_library(
    query:    str  = "",
    sector:   str  = "",
    doc_type: str  = "",
    country:  str  = "",
    language: str  = "",
    sort_by:  str  = "quality_score",   # quality_score | added_at | title
    limit:    int  = 30,
) -> List[Dict[str, Any]]:
    """يُعيد قائمة مُصفَّاة ومُرتَّبة من المكتبة"""
    library = _load_index()
    results = []

    query_lower = query.lower().strip()

    for rec in library:
        # تصفية
        if sector   and rec.get("sector")   not in (sector, "all"):
            continue
        if doc_type and rec.get("doc_type") != doc_type:
            continue
        if country  and rec.get("country")  != country:
            continue
        if language and rec.get("language") != language:
            continue

        # بحث نصي
        if query_lower:
            searchable = (
                rec.get("title", "") + " " +
                rec.get("summary", "") + " " +
                " ".join(rec.get("tags", []))
            ).lower()
            if query_lower not in searchable:
                continue

        results.append(rec)

    # ترتيب
    reverse_sort = sort_by in ("quality_score", "added_at")
    results.sort(key=lambda r: r.get(sort_by, ""), reverse=reverse_sort)

    return results[:limit]


def get_library_stats() -> Dict[str, Any]:
    """إحصاءات المكتبة"""
    library = _load_index()
    sectors  = {}
    countries = {}
    doc_types = {}
    for rec in library:
        sectors  [rec.get("sector",   "other")] = sectors.get(rec.get("sector","other"), 0) + 1
        countries[rec.get("country",  "other")] = countries.get(rec.get("country","other"), 0) + 1
        doc_types[rec.get("doc_type", "other")] = doc_types.get(rec.get("doc_type","other"), 0) + 1

    return {
        "total":      len(library),
        "manual":     sum(1 for r in library if r.get("is_manual")),
        "sectors":    sectors,
        "countries":  countries,
        "doc_types":  doc_types,
        "last_scan":  max((r.get("added_at","") for r in library), default="—"),
    }


def get_record(record_id: str) -> Optional[Dict[str, Any]]:
    """يُعيد سجلاً بالـ ID"""
    for rec in _load_index():
        if rec["id"] == record_id:
            return rec
    return None


def delete_record(record_id: str) -> bool:
    """يحذف سجلاً من الفهرس"""
    library = _load_index()
    before  = len(library)
    library = [r for r in library if r["id"] != record_id]
    if len(library) < before:
        _save_index(library)
        return True
    return False
