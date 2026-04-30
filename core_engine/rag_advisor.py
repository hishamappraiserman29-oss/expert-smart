# -*- coding: utf-8 -*-
"""
rag_advisor.py — المستشار العقاري الذكي (RAG Engine)
=====================================================
بنية RAG محلية تجمع:
  1. Qdrant vector search  (egypt_estate — 38 نقطة)
  2. market_feed.json       (بيانات السوق اللحظية)
  3. Macro Knowledge Base   (مؤشرات اقتصادية + مدن + أحداث)
  4. Web Search             (DuckDuckGo — بدون API key)
  5. Ollama qwen2.5:7b     (توليد النص — محلي، مجاني)
"""

import os, sys, json, re, time, math, urllib.request, urllib.parse
from typing import List, Dict, Any

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_BASE_DIR)
_VDB_PATH  = os.path.join(_ROOT_DIR, "expert_smart_system", "vector_db")
_FEED_FILE = os.path.join(_BASE_DIR, "data", "market_feed.json")

# ══════════════════════════════════════════════════════════════════════════════
# كاشات سينغلتون — يُحمَّلان مرة واحدة عند أول استدعاء
# ══════════════════════════════════════════════════════════════════════════════
_EMBED_MODEL = None   # SentenceTransformer
_QDRANT      = None   # QdrantClient

def _init_rag():
    """تهيئة كسولة للنموذج وقاعدة البيانات المتجهة"""
    global _EMBED_MODEL, _QDRANT
    if _EMBED_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            _EMBED_MODEL = SentenceTransformer("intfloat/multilingual-e5-large")
            print("  [RAG] SentenceTransformer loaded ✓")
        except Exception as e:
            print(f"  [RAG] SentenceTransformer failed: {e}")
    if _QDRANT is None:
        try:
            from qdrant_client import QdrantClient
            _QDRANT = QdrantClient(path=_VDB_PATH)
            print("  [RAG] Qdrant DB loaded ✓")
        except Exception as e:
            print(f"  [RAG] Qdrant failed: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# قاعدة المعرفة الكلية — Macro Knowledge Base
# بيانات محدَّثة لعام 2025 — يُحدَّث دورياً
# ══════════════════════════════════════════════════════════════════════════════
_MACRO_KB: Dict[str, Any] = {

    # ── مقارنة المدن الرئيسية ───────────────────────────────────────────────
    "cities": {
        "التجمع الخامس": {
            "avg_ppm": 42000, "trend": "مستقر-صاعد", "growth_1y": 18,
            "demand": "مرتفع", "risk": "منخفض",
            "notes": "الوجهة الأولى للطبقة المتوسطة العليا. نمو مدروس مع توسعات Phase2 و3.",
            "vs_market": "يتداول بعلاوة 25% على متوسط القاهرة الكبرى"
        },
        "العاصمة الإدارية": {
            "avg_ppm": 35000, "trend": "صاعد قوي", "growth_1y": 28,
            "demand": "متصاعد", "risk": "متوسط",
            "notes": "أعلى معدلات نمو 2024-2025. الطلب الحكومي والمؤسسي يدعم الأسعار.",
            "vs_market": "مرشح للوصول لمستوى التجمع خلال 3 سنوات"
        },
        "رأس الحكمة": {
            "avg_ppm": 12000, "trend": "انطلاق", "growth_1y": 45,
            "demand": "موسمي+دائم", "risk": "متوسط-مرتفع",
            "notes": "المشروع القومي الأضخم. استثمار إماراتي 35 مليار دولار. فرصة مبكرة عالية العائد.",
            "vs_market": "أسعار لا تزال في مرحلة الانطلاق — فجوة كبيرة مع الساحل الشمالي المجاور"
        },
        "مدينة بدر": {
            "avg_ppm": 8500, "trend": "صاعد", "growth_1y": 22,
            "demand": "متوسط", "risk": "منخفض",
            "notes": "تستفيد من قرب العاصمة الإدارية والكثافة الصناعية.",
            "vs_market": "أفضل قيمة لعقارات شرق القاهرة"
        },
        "الشيخ زايد": {
            "avg_ppm": 30000, "trend": "مستقر", "growth_1y": 12,
            "demand": "متوسط-مرتفع", "risk": "منخفض",
            "notes": "سوق ناضج. نمو معتدل. مناسب للاحتفاظ طويل الأمد.",
            "vs_market": "خصم 20% على التجمع — قيمة جيدة لمشتري نهاية الاستخدام"
        },
        "سيدي عبد الرحمن": {
            "avg_ppm": 25000, "trend": "صاعد موسمي", "growth_1y": 30,
            "demand": "موسمي عالٍ", "risk": "متوسط",
            "notes": "الساحل الشمالي يشهد طفرة. الطلب الموسمي يدعم إيرادات الإيجار.",
            "vs_market": "عائد إيجاري موسمي 8-12% — أعلى من متوسط القاهرة"
        },
        "الزمالك": {
            "avg_ppm": 35000, "trend": "مستقر", "growth_1y": 8,
            "demand": "متخصص", "risk": "منخفض",
            "notes": "سوق نادر. عرض محدود جداً. طلب سفارات ومؤسسات دولية.",
            "vs_market": "قيمة الندرة تحمي من تراجعات السوق"
        },
        "الغردقة": {
            "avg_ppm": 18000, "trend": "صاعد", "growth_1y": 25,
            "demand": "سياحي+دائم", "risk": "متوسط",
            "notes": "الطلب الأوروبي الشرقي (روس، ألمان، بولنديون) يدفع الأسعار.",
            "vs_market": "عائد إيجاري 7-10% مع إمكانية الاستخدام الشخصي"
        },
        "العاشر من رمضان": {
            "avg_ppm": 5500, "trend": "مستقر", "growth_1y": 15,
            "demand": "صناعي عالٍ", "risk": "منخفض",
            "notes": "قطب صناعي لوجستي. الطلب من المصانع والمستودعات قوي.",
            "vs_market": "أفضل عائد صناعي في محيط القاهرة الكبرى"
        },
    },

    # ── المؤشرات الاقتصادية الكلية (2025) ─────────────────────────────────
    "macro": {
        "inflation_egypt": {
            "rate": "27.8%", "direction": "تراجع",
            "impact_re": "ضغط تصاعدي على تكاليف البناء (+40% خلال 18 شهراً). العقار أصبح مخزناً للقيمة.",
            "advice": "الشراء الآن أفضل من الانتظار — التضخم يأكل قوة الجنيه"
        },
        "usd_egp": {
            "rate": "50.5", "direction": "استقرار نسبي",
            "impact_re": "تراجع الجنيه يرفع تكلفة الاستيراد والمعدات. الملاك يحوّلون إلى عقارات دولارية.",
            "advice": "العقارات السياحية والساحلية تستفيد من الطلب بالعملات الصعبة"
        },
        "cboe_rate": {
            "rate": "27.25%", "direction": "ثابت",
            "impact_re": "ارتفاع تكلفة التمويل يُخفف الطلب على القروض العقارية. يفضل المشترين النقديين.",
            "advice": "المشترون بالتمويل يُفضّلون تأجيل القرار. النقدي يتفاوض بقوة أكبر"
        },
        "oil_prices": {
            "rate": "$72/bbl", "direction": "مستقر-منخفض",
            "impact_re": "تأثير غير مباشر: تحويلات المصريين في الخليج تنخفض → تراجع طفيف في الطلب.",
            "advice": "مناطق الطلب الخليجي (الساحل الشمالي، التجمع) تشهد بعض الضغط"
        },
        "remittances": {
            "rate": "23 مليار دولار/سنة", "direction": "صاعد",
            "impact_re": "التحويلات تدعم الطلب العقاري بشكل مستمر. +15% 2024.",
            "advice": "المناطق المفضلة للمغتربين (التجمع، الشيخ زايد) تستفيد أكثر"
        },
    },

    # ── الأحداث الجيوسياسية وتأثيرها ──────────────────────────────────────
    "geopolitical": {
        "حرب غزة": {
            "direct_impact": "تراجع السياحة الإسرائيلية والخليجية في سيناء. ضغط على أسعار العقارات السياحية.",
            "indirect_impact": "تدفق استثمارات مصرية من الخارج كملاذ آمن. تعزيز العقار كأصل دفاعي.",
            "sector_winners": ["عقارات القاهرة الكبرى", "العاصمة الإدارية"],
            "sector_losers": ["منتجعات سيناء الشمالية", "السياحة شرم الشيخ"],
        },
        "أزمة البحر الأحمر": {
            "direct_impact": "تراجع إيرادات قناة السويس -50%. ضغط على الموازنة العامة.",
            "indirect_impact": "المستثمرون يتجنبون المناطق اللوجستية المرتبطة بالبحر الأحمر.",
            "sector_winners": ["مناطق صناعية داخلية", "عقارات القاهرة"],
            "sector_losers": ["بورسعيد", "السويس الصناعية"],
        },
        "تدفق الاستثمار الإماراتي": {
            "direct_impact": "رأس الحكمة: 35 مليار دولار. أضخم استثمار في تاريخ مصر.",
            "indirect_impact": "تعزيز ثقة المستثمرين الأجانب. ارتفاع أسعار الأراضي المجاورة +60%.",
            "sector_winners": ["رأس الحكمة", "الساحل الشمالي", "التجمع الخامس"],
            "sector_losers": [],
        },
        "التضخم العالمي": {
            "direct_impact": "ارتفاع أسعار مواد البناء الحديد (+45%)، الأسمنت (+35%)، الألومنيوم (+30%).",
            "indirect_impact": "ارتفاع تكاليف المشاريع الجديدة يدفع أسعار الوحدات للأعلى.",
            "sector_winners": ["ملاك العقارات القائمة", "مطوري العقارات"],
            "sector_losers": ["المشترون بالتقسيط", "مشاريع قيد التنفيذ"],
        },
    },

    # ── تحليل توقعات القطاعات 2025 ─────────────────────────────────────────
    "sector_outlook": {
        "residential": {
            "2025_forecast": "نمو 15-20%",
            "drivers": "التضخم + تحويلات الخارج + الطلب المحبوس",
            "risk": "ارتفاع تكاليف التمويل"
        },
        "industrial": {
            "2025_forecast": "نمو 20-25%",
            "drivers": "تحول سلاسل التوريد + استثمارات أجنبية مباشرة",
            "risk": "أزمة البحر الأحمر تؤثر على الصادرات"
        },
        "hospitality": {
            "2025_forecast": "نمو 25-35%",
            "drivers": "انخفاض الجنيه يجعل مصر وجهة رخيصة للسياح",
            "risk": "عدم الاستقرار الإقليمي"
        },
        "retail": {
            "2025_forecast": "نمو 12-18%",
            "drivers": "نمو التجارة الإلكترونية الفيزيائية + المولات العصرية",
            "risk": "ضغط القوة الشرائية بسبب التضخم"
        },
        "healthcare": {
            "2025_forecast": "نمو 18-22%",
            "drivers": "نقص المنشآت + تحولات ديموغرافية",
            "risk": "تعقيدات التراخيص والاشتراطات"
        },
        "educational": {
            "2025_forecast": "نمو 15-20%",
            "drivers": "الطلب على التعليم الخاص + التوسع السكاني",
            "risk": "مخاطر تنظيمية + منافسة التعليم الرقمي"
        },
        "agricultural": {
            "2025_forecast": "نمو 8-12%",
            "drivers": "الأمن الغذائي + سياسات الاستصلاح",
            "risk": "ندرة المياه + تغير المناخ"
        },
    },

    # ── توصيات استراتيجية للمسؤولين ────────────────────────────────────────
    "strategic_intel": {
        "buy_signals": [
            "العاصمة الإدارية — قبل التشغيل الكامل للوزارات",
            "رأس الحكمة — مرحلة الانطلاق الأولى",
            "الغردقة — الطلب الأوروبي الشرقي في ازدياد",
            "مدينة بدر — سعر منخفض مع نمو صناعي حاد",
        ],
        "hold_signals": [
            "التجمع الخامس — سوق ناضج، نمو معتدل مستدام",
            "الشيخ زايد — عمق سوقي + عائد إيجاري مستقر",
        ],
        "caution_signals": [
            "بورسعيد الصناعية — أزمة البحر الأحمر تؤثر",
            "سيناء السياحية — عدم استقرار إقليمي",
            "عقارات التمويل — أسعار الفائدة تثقل",
        ],
    }
}

# ══════════════════════════════════════════════════════════════════════════════
# Vector Search — Qdrant
# ══════════════════════════════════════════════════════════════════════════════
def _search_vectors(question: str, top_k: int = 5) -> List[Dict]:
    """يبحث في قاعدة البيانات المتجهة عن أقرب نتائج للسؤال"""
    _init_rag()
    if _EMBED_MODEL is None or _QDRANT is None:
        return []
    try:
        vec = _EMBED_MODEL.encode(f"query: {question}").tolist()
        try:
            resp = _QDRANT.query_points(
                collection_name="egypt_estate",
                query=vec, limit=top_k, with_payload=True
            )
            hits = resp.points
        except Exception:
            hits = _QDRANT.search(
                collection_name="egypt_estate",
                query_vector=vec, limit=top_k
            )
        return [
            {"loc": h.payload.get("loc",""), "pr": h.payload.get("pr",0),
             "ar": h.payload.get("ar",1), "source": "vector_db",
             "ppm": round(h.payload.get("pr",0)/max(h.payload.get("ar",1),1))}
            for h in hits
        ]
    except Exception as e:
        print(f"  [RAG] vector search error: {e}")
        return []

# ══════════════════════════════════════════════════════════════════════════════
# Market Feed Search
# ══════════════════════════════════════════════════════════════════════════════
def _search_feed(location: str = "", property_type: str = "",
                 n: int = 5) -> List[Dict]:
    """يبحث في market_feed.json عن سجلات مطابقة"""
    try:
        if not os.path.exists(_FEED_FILE):
            return []
        with open(_FEED_FILE, encoding="utf-8") as f:
            feed = json.load(f)
        results = []
        for rec in feed:
            loc_m  = not location or location in str(rec.get("location",""))
            type_m = not property_type or property_type in str(rec.get("property_type",""))
            if loc_m and type_m:
                results.append({
                    "loc": rec.get("location",""),
                    "pr": rec.get("price",0),
                    "ar": rec.get("area",1),
                    "ppm": rec.get("price_per_meter",0),
                    "source": f"market_feed:{rec.get('source','?')}"
                })
        return results[:n]
    except Exception as e:
        print(f"  [RAG] feed search error: {e}")
        return []

# ══════════════════════════════════════════════════════════════════════════════
# Web Search — DuckDuckGo (بدون API key)
# ══════════════════════════════════════════════════════════════════════════════
def _web_search(query: str, n: int = 3) -> List[Dict]:
    """بحث ويب عبر DuckDuckGo HTML scraping — fallback graceful"""
    try:
        url = "https://html.duckduckgo.com/html/"
        data = urllib.parse.urlencode({"q": query + " عقارات مصر 2025"}).encode()
        req = urllib.request.Request(
            url, data=data,
            headers={"User-Agent": "Mozilla/5.0 (compatible; ExpertSmartBot/1.0)",
                     "Content-Type": "application/x-www-form-urlencoded"}
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            html = r.read().decode("utf-8", errors="replace")

        # استخلاص المقتطفات النصية
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
        titles   = re.findall(r'class="result__title"[^>]*>.*?<a[^>]*>(.*?)</a>', html, re.DOTALL)

        results = []
        for i, (t, s) in enumerate(zip(titles[:n], snippets[:n])):
            clean_t = re.sub(r'<[^>]+>', '', t).strip()
            clean_s = re.sub(r'<[^>]+>', '', s).strip()
            if clean_s:
                results.append({"title": clean_t, "snippet": clean_s, "source": "web"})
        return results
    except Exception as e:
        print(f"  [RAG] web search skipped: {e}")
        return []

# ══════════════════════════════════════════════════════════════════════════════
# Macro KB Retrieval — البحث في قاعدة المعرفة الكلية
# ══════════════════════════════════════════════════════════════════════════════
def _search_macro(question: str) -> Dict:
    """يبحث في قاعدة المعرفة الكلية عن المعلومات ذات الصلة"""
    q = question.lower()
    results = {}

    # البحث في المدن
    for city, info in _MACRO_KB["cities"].items():
        if city in question or city.replace(" ", "") in q:
            results[f"city:{city}"] = info

    # البحث في المؤشرات الاقتصادية
    econ_keywords = {
        "تضخم": "inflation_egypt", "inflation": "inflation_egypt",
        "دولار": "usd_egp", "صرف": "usd_egp", "جنيه": "usd_egp",
        "فائدة": "cboe_rate", "بنك مركزي": "cboe_rate",
        "نفط": "oil_prices", "بترول": "oil_prices",
        "تحويلات": "remittances", "مغتربين": "remittances",
    }
    for kw, key in econ_keywords.items():
        if kw in q:
            results[f"macro:{key}"] = _MACRO_KB["macro"][key]
            break

    # البحث في الأحداث الجيوسياسية
    geo_keywords = {
        "غزة": "حرب غزة", "حرب": "حرب غزة",
        "بحر أحمر": "أزمة البحر الأحمر", "سويس": "أزمة البحر الأحمر",
        "إماراتي": "تدفق الاستثمار الإماراتي", "أبوظبي": "تدفق الاستثمار الإماراتي",
        "عالمي": "التضخم العالمي", "استيراد": "التضخم العالمي",
    }
    for kw, event in geo_keywords.items():
        if kw in q:
            results[f"geo:{event}"] = _MACRO_KB["geopolitical"][event]
            break

    # توقعات القطاعات
    sector_keywords = {
        "سكني": "residential", "شقة": "residential", "فيلا": "residential",
        "صناعي": "industrial", "مصنع": "industrial", "مستودع": "industrial",
        "فندقي": "hospitality", "فندق": "hospitality", "سياحي": "hospitality",
        "تجزئة": "retail", "محل": "retail", "مول": "retail",
        "طبي": "healthcare", "مستشفى": "healthcare", "صحي": "healthcare",
        "تعليمي": "educational", "مدرسة": "educational", "جامعة": "educational",
        "زراعي": "agricultural", "أرض": "agricultural",
    }
    for kw, sec in sector_keywords.items():
        if kw in q:
            results[f"outlook:{sec}"] = _MACRO_KB["sector_outlook"][sec]
            break

    # الإشارات الاستراتيجية دائماً مفيدة
    results["strategic"] = _MACRO_KB["strategic_intel"]
    return results

# ══════════════════════════════════════════════════════════════════════════════
# بناء الـ Prompt للـ LLM
# ══════════════════════════════════════════════════════════════════════════════
def _build_prompt(question: str, vector_docs: List[Dict],
                  macro_ctx: Dict, web_results: List[Dict]) -> str:
    """يبني prompt احترافي للـ LLM يدمج كل مصادر البيانات"""

    # بيانات السوق من Qdrant + feed
    market_lines = []
    for d in vector_docs[:6]:
        ppm = d.get("ppm", d.get("pr",0)//max(d.get("ar",1),1))
        market_lines.append(f"  • {d['loc']}: {ppm:,} EGP/م² (إجمالي: {d.get('pr',0):,} EGP، مساحة: {d.get('ar',0)} م²)")

    # السياق الكلي
    macro_lines = []
    for k, v in macro_ctx.items():
        if k.startswith("city:"):
            city = k[5:]
            macro_lines.append(
                f"  📍 {city}: متوسط السعر {v['avg_ppm']:,} EGP/م² | "
                f"النمو السنوي: {v['growth_1y']}% | الاتجاه: {v['trend']}\n"
                f"     {v['notes']}"
            )
        elif k.startswith("macro:"):
            macro_lines.append(
                f"  📊 {list(v.keys())[0] if isinstance(v,dict) else k}: "
                f"{v.get('rate','') if isinstance(v,dict) else ''} — "
                f"{v.get('impact_re','') if isinstance(v,dict) else str(v)}"
            )
        elif k.startswith("geo:"):
            macro_lines.append(
                f"  🌍 الحدث الجيوسياسي: {v.get('direct_impact','')}"
            )
        elif k.startswith("outlook:"):
            macro_lines.append(
                f"  📈 توقعات القطاع 2025: {v.get('2025_forecast','')} | "
                f"المحركات: {v.get('drivers','')}"
            )

    # نتائج الويب
    web_lines = [
        f"  🔍 [{r['title'][:50]}]: {r['snippet'][:120]}"
        for r in web_results[:2] if r.get("snippet")
    ]

    mkt_str  = "\n".join(market_lines)  if market_lines  else "  (لا توجد بيانات سوق مطابقة)"
    mac_str  = "\n".join(macro_lines)   if macro_lines   else "  (لا توجد بيانات كلية ذات صلة)"
    web_str  = "\n".join(web_lines)     if web_lines     else ""

    # الإشارات الاستراتيجية
    strat = macro_ctx.get("strategic", {})
    buy_sigs = " | ".join(strat.get("buy_signals",  [])[:3])
    cau_sigs = " | ".join(strat.get("caution_signals", [])[:2])

    prompt = f"""أنت خبير عقاري وطني متخصص في السوق المصري. لديك:
- خبرة 20 عاماً في التقييم العقاري والتحليل الاستثماري
- معرفة عميقة بالوضع الاقتصادي والجيوسياسي المصري والإقليمي
- اطلاع كامل على أحدث بيانات السوق لعام 2025

استخدم البيانات أدناه للإجابة بدقة واحترافية باللغة العربية الفصحى.

══ بيانات السوق العقاري ══
{mkt_str}

══ المؤشرات الاقتصادية والجيوسياسية ══
{mac_str}

{f'══ إشارات من الإنترنت ══{chr(10)}{web_str}{chr(10)}' if web_str else ''}

══ الإشارات الاستراتيجية الحالية ══
  ✅ فرص الشراء: {buy_sigs}
  ⚠ مناطق الحذر: {cau_sigs}

══ السؤال ══
{question}

══ المطلوب ══
قدم إجابة احترافية شاملة (200-400 كلمة) تشمل:
1. الإجابة المباشرة مع أرقام وبيانات محددة
2. التحليل السوقي الداعم
3. المخاطر والفرص
4. توصية عملية واضحة للمستثمر أو صانع القرار

الإجابة:"""

    return prompt

# ══════════════════════════════════════════════════════════════════════════════
# LLM Call — Ollama qwen2.5:7b
# ══════════════════════════════════════════════════════════════════════════════
def _ask_llm(prompt: str) -> str:
    """يستدعي qwen2.5:7b عبر Ollama للإجابة"""
    # محاولة Ollama أولاً
    try:
        import ollama
        resp = ollama.chat(
            model="qwen2.5:7b",
            messages=[
                {"role": "system",
                 "content": "أنت مستشار عقاري خبير في السوق المصري. أجب بالعربية الفصحى دائماً."},
                {"role": "user", "content": prompt}
            ],
            options={"temperature": 0.3, "num_predict": 600}
        )
        return resp["message"]["content"].strip()
    except Exception as e:
        print(f"  [RAG] Ollama error: {e}")

    # محاولة Anthropic API ثانياً
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if api_key:
        try:
            import anthropic
            c = anthropic.Anthropic(api_key=api_key)
            r = c.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=700,
                messages=[{"role": "user", "content": prompt}]
            )
            return r.content[0].text.strip()
        except Exception as e:
            print(f"  [RAG] Anthropic error: {e}")

    # Fallback — هيكل نصي من القاعدة المعرفية
    return _fallback_answer(prompt)

def _fallback_answer(prompt: str) -> str:
    """إجابة هيكلية عند غياب LLM — تستخلص من السياق"""
    # استخلاص الخطوط الرئيسية من الـ prompt
    lines = [l.strip() for l in prompt.split("\n")
             if l.strip().startswith(("•", "📍", "📊", "📈", "✅", "⚠"))]
    if lines:
        return (
            "**ملخص تحليلي (وضع احتياطي — بدون LLM):**\n\n"
            + "\n".join(lines[:8])
            + "\n\n*تفعيل Ollama أو مفتاح Anthropic API للحصول على تحليل أعمق.*"
        )
    return "⚠ تعذّر توليد إجابة — يُرجى التحقق من تشغيل Ollama أو تعيين ANTHROPIC_API_KEY."

# ══════════════════════════════════════════════════════════════════════════════
# الدالة الرئيسية — advisor_answer
# ══════════════════════════════════════════════════════════════════════════════
def advisor_answer(question: str, location: str = "", property_type: str = "",
                   use_web: bool = True) -> Dict[str, Any]:
    """
    دالة الدخول الرئيسية — تُشغّل الـ pipeline الكامل:
      1. Vector search (Qdrant)
      2. Market feed search
      3. Macro KB lookup
      4. Web search (اختياري)
      5. LLM synthesis (Ollama/Anthropic/Fallback)
    """
    t0 = time.time()

    # 1. بحث متجه
    vec_docs = _search_vectors(question, top_k=5)

    # 2. بيانات السوق المحلية
    feed_docs = _search_feed(location, property_type, n=4)
    all_docs  = vec_docs + [d for d in feed_docs if d not in vec_docs]

    # 3. قاعدة المعرفة الكلية
    macro_ctx = _search_macro(question)

    # 4. بحث ويب (محدود الوقت)
    web_res = _web_search(question) if use_web else []

    # 5. بناء الـ prompt والإجابة
    prompt  = _build_prompt(question, all_docs, macro_ctx, web_res)
    answer  = _ask_llm(prompt)
    elapsed = round(time.time() - t0, 1)

    # مصادر الإجابة
    sources = []
    if vec_docs:  sources.append(f"Qdrant vector DB ({len(vec_docs)} نتيجة)")
    if feed_docs: sources.append(f"Market Feed ({len(feed_docs)} سجل)")
    if web_res:   sources.append(f"بحث الإنترنت ({len(web_res)} نتيجة)")
    sources.append(f"قاعدة المعرفة الكلية ({len(macro_ctx)} عنصر)")

    # معلومات المدن المكتشفة
    cities_found = [k[5:] for k in macro_ctx if k.startswith("city:")]

    return {
        "answer":       answer,
        "sources":      sources,
        "cities_found": cities_found,
        "docs_used":    len(all_docs),
        "web_hits":     len(web_res),
        "elapsed_s":    elapsed,
        "confidence":   min(0.95, 0.50 + len(all_docs)*0.04 + (0.10 if web_res else 0)),
        "mode":         "RAG+Ollama" if answer and "وضع احتياطي" not in answer else "RAG+Fallback"
    }

# ══════════════════════════════════════════════════════════════════════════════
# Strategic Context for Excel Reports
# ══════════════════════════════════════════════════════════════════════════════
def get_strategic_context(sector: str, purpose: str, location: str) -> Dict[str, str]:
    """
    يُعيد نصاً استراتيجياً لقسم تقرير الإكسيل
    يُستدعى من write_to_excel_template()
    """
    loc = str(location or "").strip()
    sec = str(sector or "residential").lower()
    pur = str(purpose or "fair_market_value").lower()

    # مؤشرات الموقع
    city_data = None
    for city, info in _MACRO_KB["cities"].items():
        if city in loc or loc in city:
            city_data = (city, info)
            break

    # توقعات القطاع
    outlook = _MACRO_KB["sector_outlook"].get(sec, _MACRO_KB["sector_outlook"]["residential"])

    # نص الغرض الاستراتيجي
    purpose_notes = {
        "acquisition":          "يُنصح بمقارنة علاوة السيطرة مع IRR المحسوب في ورقة DCF قبل إغلاق الصفقة.",
        "bank_financing":       "القيمة التمويلية تعكس خصم 5% من السوق — تُستخدم كحد دنى للضمان البنكي.",
        "rental_arbitration":   "القيمة الإيجارية محسوبة وفق بيانات السوق الفعلية — لا التقديرية.",
        "insurance":            "القيمة التأمينية تعكس تكلفة إعادة الإنشاء الكاملة بأسعار 2025.",
        "investment_analysis":  "يُقارن IRR بمعدل الفائدة البنكي الحالي (27.25%) كمعيار الفرصة البديلة.",
        "judicial_liquidation": "القيمة التصفوية تشمل خصم 18% وتكاليف إجراءات قضائية مُقدَّرة 3%.",
        "fair_market_value":    "القيمة السوقية محسوبة وفق مناهج ثلاثة دولية مُوزَّنة.",
    }

    # بناء النص الاستراتيجي
    city_line = ""
    if city_data:
        c, ci = city_data
        city_line = (
            f"📍 {c}: متوسط السعر {ci['avg_ppm']:,} EGP/م² | "
            f"النمو السنوي {ci['growth_1y']}% | {ci['trend']}"
        )

    macro = _MACRO_KB["macro"]
    econ_lines = (
        f"• التضخم المصري: {macro['inflation_egypt']['rate']} | "
        f"سعر الدولار: {macro['usd_egp']['rate']} EGP | "
        f"سعر الفائدة: {macro['cboe_rate']['rate']}"
    )

    geo_summary = (
        "• الاستثمار الإماراتي يدعم ثقة السوق. "
        "أزمة البحر الأحمر تُخفض إيرادات السويس. "
        "التضخم العالمي يرفع تكاليف البناء."
    )

    sector_line = (
        f"• توقعات {sec} 2025: {outlook['2025_forecast']} | "
        f"المحركات: {outlook['drivers']}"
    )

    buy_sigs  = _MACRO_KB["strategic_intel"]["buy_signals"][:3]
    caut_sigs = _MACRO_KB["strategic_intel"]["caution_signals"][:2]

    return {
        "title":        "التحليل الاستراتيجي والجيوسياسي",
        "city_line":    city_line,
        "econ_line":    econ_lines,
        "geo_line":     geo_summary,
        "sector_line":  sector_line,
        "purpose_note": purpose_notes.get(pur, purpose_notes["fair_market_value"]),
        "buy_signals":  buy_sigs,    # list of strings
        "caution":      caut_sigs,   # list of strings
        "disclaimer":   "المؤشرات الاقتصادية مُستقاة من بيانات Q1-2025. تُحدَّث فصلياً.",
    }
