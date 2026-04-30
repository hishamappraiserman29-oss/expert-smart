# -*- coding: utf-8 -*-
"""
report_tuner.py — محرك المحاكاة والتدريب (Context-Tuning Engine)
================================================================
يُحاكي عملية Fine-Tuning عبر:
  1. استخراج البصمة الأسلوبية (Style Fingerprint) من وثيقة مرجعية
  2. حفظ ملف الأسلوب محلياً للاستخدام المتكرر
  3. حقن الأسلوب في موجّهات AI (Ollama / Gemini) لضمان تطابق المخرجات
  4. إدارة مكتبة الأساليب المحفوظة
"""

import os, sys, json, re, time, hashlib, textwrap
from typing import Dict, Any, List, Optional
from datetime import datetime

_BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
_STYLES_DIR = os.path.join(_BASE_DIR, "data", "style_profiles")
os.makedirs(_STYLES_DIR, exist_ok=True)

# ══════════════════════════════════════════════════════════════════════════════
# هياكل بيانات البصمة الأسلوبية
# ══════════════════════════════════════════════════════════════════════════════
_EMPTY_PROFILE: Dict[str, Any] = {
    "id":               "",
    "name":             "",
    "source_file":      "",
    "created_at":       "",
    "doc_type":         "",          # valuation_report | audit_report | tax_report | standard
    "language":         "ar",        # ar | en | mixed
    "formality":        "formal",    # formal | semi-formal | technical
    "terminology": {
        "sector_terms":   [],        # مصطلحات القطاع المستخدمة
        "valuation_methods": [],     # الأساليب التقييمية المُشار إليها
        "standards_refs":  [],       # معايير مذكورة (IVS / RICS / TAQEEM / EFSA…)
        "currency_format": "EGP",    # عملة التقرير
        "unit_format":    "م²",
    },
    "structure": {
        "section_headers":  [],      # عناوين الأقسام المكتشفة
        "uses_tables":      True,
        "uses_bullet_lists": False,
        "number_format":   "#,##0",  # نمط الأرقام
        "conclusion_style": "",      # كيف تُكتب الخلاصة
    },
    "tone": {
        "opening_phrase":  "",       # الجملة الافتتاحية النموذجية
        "closing_phrase":  "",       # الجملة الختامية النموذجية
        "hedging_level":   "medium", # low / medium / high (مستوى التحفظ)
        "person":         "third",   # first / third (ضمير الكتابة)
    },
    "prompt_injection":  "",         # النص الجاهز للحقن في AI
    "sample_sentences":  [],         # 5 جمل نموذجية مُستخرجة
    "word_count":        0,
    "confidence":        0.0,
}

# ══════════════════════════════════════════════════════════════════════════════
# 1. استخراج البصمة الأسلوبية من النص
# ══════════════════════════════════════════════════════════════════════════════
def analyze_style(text: str, doc_name: str = "") -> Dict[str, Any]:
    """
    يُحلّل نص وثيقة ويستخرج بصمتها الأسلوبية.
    يستخدم Ollama أولاً ثم التحليل القاعدي كاحتياط.
    """
    profile = dict(_EMPTY_PROFILE)
    profile["id"]          = hashlib.md5(text[:2000].encode()).hexdigest()[:12]
    profile["name"]        = doc_name or f"نمط-{profile['id']}"
    profile["source_file"] = doc_name
    profile["created_at"]  = datetime.now().strftime("%Y-%m-%d %H:%M")
    profile["word_count"]  = len(text.split())

    # ── التحليل القاعدي (دائماً يعمل) ─────────────────────────────────────
    _basic_analysis(text, profile)

    # ── التحليل بالذكاء الاصطناعي (يُحسّن التحليل القاعدي) ────────────────
    try:
        _ai_analysis(text, profile)
        profile["confidence"] = 0.85
    except Exception as e:
        print(f"  [tuner] AI analysis skipped: {e}")
        profile["confidence"] = 0.55

    # ── بناء نص الحقن النهائي ─────────────────────────────────────────────
    profile["prompt_injection"] = _build_injection(profile)

    return profile


def _basic_analysis(text: str, profile: Dict[str, Any]) -> None:
    """تحليل قاعدي خالٍ من AI — يعمل دائماً"""
    lines = text.split("\n")

    # اكتشاف اللغة
    ar_chars = len(re.findall(r'[\u0600-\u06FF]', text))
    en_chars = len(re.findall(r'[a-zA-Z]', text))
    if ar_chars > en_chars * 2:
        profile["language"] = "ar"
    elif en_chars > ar_chars * 2:
        profile["language"] = "en"
    else:
        profile["language"] = "mixed"

    # عناوين الأقسام (أسطر قصيرة تبدأ برقم أو رمز)
    headers = []
    for ln in lines:
        ln = ln.strip()
        if len(ln) < 80 and len(ln) > 5:
            if re.match(r'^(\d+[\.\-]|\*|•|–|#|أولاً|ثانياً|ثالثاً|رابعاً|المادة|البند|الفصل|القسم)', ln):
                headers.append(ln[:60])
    profile["structure"]["section_headers"] = headers[:20]
    profile["structure"]["uses_tables"] = bool(re.search(r'\||\t{2,}|─{3,}', text))
    profile["structure"]["uses_bullet_lists"] = bool(re.search(r'^[•\-\*] ', text, re.MULTILINE))

    # نمط الأرقام
    if re.search(r'\d{1,3}(?:,\d{3})+', text):
        profile["terminology"]["number_format"] = "#,##0"
    elif re.search(r'\d{1,3}(?:\.\d{3})+', text):
        profile["terminology"]["number_format"] = "#.##0"

    # العملة
    if re.search(r'EGP|ج\.م|جنيه', text, re.IGNORECASE):
        profile["terminology"]["currency_format"] = "EGP"
    elif re.search(r'SAR|ريال|ر\.س', text, re.IGNORECASE):
        profile["terminology"]["currency_format"] = "SAR"
    elif re.search(r'USD|\$|دولار', text, re.IGNORECASE):
        profile["terminology"]["currency_format"] = "USD"

    # المعايير المُشار إليها
    standards = []
    for std in ["IVS", "RICS", "TAQEEM", "EFSA", "FRA", "SAMA", "IAAO", "Basel"]:
        if std in text:
            standards.append(std)
    profile["terminology"]["standards_refs"] = standards

    # الأساليب التقييمية
    methods = []
    _method_kw = [
        ("طريقة السوق", ["مقارنات","سوق","comparative"]),
        ("طريقة التكلفة", ["تكلفة","cost approach","إعادة الإنشاء"]),
        ("طريقة الدخل", ["رسملة","دخل","income","NOI","cap rate"]),
        ("DCF", ["DCF","تدفقات نقدية","discounted cash flow"]),
        ("IRR", ["IRR","معدل العائد الداخلي"]),
    ]
    for method_name, keywords in _method_kw:
        if any(kw.lower() in text.lower() for kw in keywords):
            methods.append(method_name)
    profile["terminology"]["valuation_methods"] = methods

    # الجمل النموذجية (أطول جملة في كل فقرة)
    sentences = re.split(r'[.،؛\n]', text)
    long_sents = sorted([s.strip() for s in sentences if 30 < len(s.strip()) < 200],
                         key=len, reverse=True)
    profile["sample_sentences"] = long_sents[:5]

    # العبارة الافتتاحية
    first_para = next((ln.strip() for ln in lines if len(ln.strip()) > 40), "")
    profile["tone"]["opening_phrase"] = first_para[:150]

    # العبارة الختامية
    last_paras = [ln.strip() for ln in reversed(lines) if len(ln.strip()) > 30]
    profile["tone"]["closing_phrase"] = last_paras[0][:150] if last_paras else ""

    # ضمير الكتابة
    if re.search(r'\bنرى\b|\bنُقدّر\b|\bنوصي\b', text):
        profile["tone"]["person"] = "first_plural"
    elif re.search(r'\bيرى المُقيّم\b|\bقدّر الخبير\b|\bأفاد المثمن\b', text):
        profile["tone"]["person"] = "third"
    else:
        profile["tone"]["person"] = "first_plural"

    # نوع الوثيقة
    if re.search(r'تقرير تقييم|valuation report|تقييم عقاري', text, re.IGNORECASE):
        profile["doc_type"] = "valuation_report"
    elif re.search(r'تدقيق|مراجعة|audit', text, re.IGNORECASE):
        profile["doc_type"] = "audit_report"
    elif re.search(r'ضريبي|ضريبة|mass appraisal', text, re.IGNORECASE):
        profile["doc_type"] = "tax_report"
    elif re.search(r'معيار|standard|IVS|RICS', text, re.IGNORECASE):
        profile["doc_type"] = "standard"
    else:
        profile["doc_type"] = "general"


def _ai_analysis(text: str, profile: Dict[str, Any]) -> None:
    """تحليل عميق بمساعدة Ollama qwen2.5:7b"""
    # نأخذ مقتطفاً (أول 3000 حرف + آخر 1000 حرف) لتوفير التوكنات
    snippet = text[:3000] + "\n...\n" + text[-1000:] if len(text) > 4000 else text

    prompt = f"""أنت محلل خبير للأساليب الكتابية في التقارير العقارية والمالية.

حلّل المقتطف التالي واستخرج:
1. مستوى الرسمية (رسمي جداً / شبه رسمي / تقني)
2. أبرز 5 مصطلحات متخصصة
3. نمط الخاتمة والتوصية
4. مستوى التحفظ والتحوّط (منخفض / متوسط / مرتفع)
5. جملة تلخيصية واحدة لأسلوب الكاتب

أجب بـ JSON فقط بهذا الشكل:
{{
  "formality": "formal",
  "key_terms": ["مصطلح1","مصطلح2","مصطلح3","مصطلح4","مصطلح5"],
  "conclusion_style": "وصف مختصر لأسلوب الخاتمة",
  "hedging_level": "medium",
  "style_summary": "جملة واحدة تصف الأسلوب"
}}

المقتطف:
{snippet[:2500]}"""

    result = _call_ollama(prompt)
    if result:
        try:
            # استخراج JSON من الرد
            json_match = re.search(r'\{[\s\S]+\}', result)
            if json_match:
                parsed = json.loads(json_match.group())
                profile["formality"]  = parsed.get("formality", "formal")
                profile["terminology"]["sector_terms"] = parsed.get("key_terms", [])
                profile["structure"]["conclusion_style"] = parsed.get("conclusion_style", "")
                profile["tone"]["hedging_level"] = parsed.get("hedging_level", "medium")
                # نضيف ملخص الأسلوب إلى الحقن
                profile["_style_summary"] = parsed.get("style_summary", "")
        except (json.JSONDecodeError, KeyError):
            pass


def _call_ollama(prompt: str) -> str:
    """يستدعي Ollama qwen2.5:7b ويُعيد الرد"""
    try:
        import urllib.request, json as _json
        data = _json.dumps({
            "model":  "qwen2.5:7b",
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 512}
        }).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            return _json.loads(r.read())["response"]
    except Exception as e:
        raise RuntimeError(f"Ollama unavailable: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# 2. بناء نص الحقن للـ AI
# ══════════════════════════════════════════════════════════════════════════════
def _build_injection(profile: Dict[str, Any]) -> str:
    """يبني نص الحقن الجاهز للإدراج في system prompt أي نموذج AI"""
    lang_map  = {"ar": "العربية الفصحى", "en": "English", "mixed": "لغة ثنائية"}
    form_map  = {"formal": "رسمية عالية", "semi-formal": "شبه رسمية", "technical": "تقنية متخصصة"}
    hedge_map = {"low": "حازم وقاطع", "medium": "متوازن مع تحفظ مناسب", "high": "محتاط ومتحفظ بشكل واضح"}

    methods   = "، ".join(profile["terminology"]["valuation_methods"]) or "المناهج الثلاثة"
    standards = "، ".join(profile["terminology"]["standards_refs"])    or "المعايير الدولية"
    terms     = "، ".join(profile["terminology"]["sector_terms"][:5])  or "مصطلحات التقييم"
    headers   = "\n    • " + "\n    • ".join(profile["structure"]["section_headers"][:6]) if profile["structure"]["section_headers"] else ""
    samples   = "\n    ─ " + "\n    ─ ".join(profile["sample_sentences"][:3]) if profile["sample_sentences"] else ""

    style_note = profile.get("_style_summary", "")
    opening    = profile["tone"]["opening_phrase"][:120]
    closing    = profile["tone"]["closing_phrase"][:120]

    injection = f"""══ تعليمات المحاكاة الأسلوبية (Context-Tuning) ══
أنت مُقيّم عقاري خبير يكتب بالأسلوب المحدد أدناه. التزم بهذا الأسلوب الاحترافي في كامل ردّك.

📄 الوثيقة المرجعية: "{profile['name']}"
📝 نوع الوثيقة: {profile['doc_type']}
🌐 لغة الكتابة: {lang_map.get(profile['language'], 'العربية')}
🎯 مستوى الرسمية: {form_map.get(profile['formality'], 'رسمية')}
⚖ أسلوب التحفظ: {hedge_map.get(profile['tone']['hedging_level'], 'متوازن')}
💰 العملة: {profile['terminology']['currency_format']} | وحدة المساحة: {profile['terminology']['unit_format']}

📌 الأساليب التقييمية المستخدمة في المرجع: {methods}
📋 المعايير المُشار إليها: {standards}
🔑 المصطلحات المفتاحية: {terms}
{'📑 هيكل الأقسام:' + headers if headers else ''}
{'✍ عينة من أسلوب الكتابة:' + samples if samples else ''}
{('💡 ملخص الأسلوب: ' + style_note) if style_note else ''}

🖊 افتتح تقريرك بما يشابه: "{opening}"
🔚 اختتم بما يشابه: "{closing}"

⚠ التزم بـ:
- نفس بنية الجمل ومستوى التفصيل
- نفس أسلوب عرض الأرقام ({profile['structure']['number_format']})
- {'استخدام الجداول كما في المرجع' if profile['structure']['uses_tables'] else 'تجنب الجداول إذا لم تكن ضرورية'}
- التحدث {'بضمير المتكلم الجمع (نرى، نُقدّر)' if 'plural' in profile['tone']['person'] else 'بصيغة الغائب (يرى المُقيّم، قدّر الخبير)'}
══════════════════════════════════════════════
"""
    return injection.strip()


# ══════════════════════════════════════════════════════════════════════════════
# 3. حفظ واسترجاع ملفات الأسلوب
# ══════════════════════════════════════════════════════════════════════════════
def save_style_profile(profile: Dict[str, Any]) -> str:
    """يحفظ ملف الأسلوب ويُعيد مسار الملف"""
    safe_name = re.sub(r'[^\w\-_]', '_', profile["name"])[:40]
    filename  = f"{profile['id']}_{safe_name}.json"
    path      = os.path.join(_STYLES_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
    print(f"  [tuner] Style saved: {filename}")
    return path


def load_style_profile(profile_id: str) -> Optional[Dict[str, Any]]:
    """يحمّل ملف أسلوب بالـ ID"""
    for fname in os.listdir(_STYLES_DIR):
        if fname.startswith(profile_id) and fname.endswith(".json"):
            with open(os.path.join(_STYLES_DIR, fname), encoding="utf-8") as f:
                return json.load(f)
    return None


def list_style_profiles() -> List[Dict[str, Any]]:
    """يُعيد قائمة بكل ملفات الأسلوب المحفوظة"""
    profiles = []
    for fname in sorted(os.listdir(_STYLES_DIR)):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(_STYLES_DIR, fname), encoding="utf-8") as f:
                    p = json.load(f)
                    profiles.append({
                        "id":          p.get("id", ""),
                        "name":        p.get("name", ""),
                        "source_file": p.get("source_file", ""),
                        "created_at":  p.get("created_at", ""),
                        "doc_type":    p.get("doc_type", ""),
                        "language":    p.get("language", "ar"),
                        "methods":     p["terminology"].get("valuation_methods", []),
                        "standards":   p["terminology"].get("standards_refs", []),
                        "confidence":  p.get("confidence", 0),
                        "word_count":  p.get("word_count", 0),
                    })
            except Exception:
                pass
    return profiles


def delete_style_profile(profile_id: str) -> bool:
    """يحذف ملف أسلوب"""
    for fname in os.listdir(_STYLES_DIR):
        if fname.startswith(profile_id) and fname.endswith(".json"):
            os.unlink(os.path.join(_STYLES_DIR, fname))
            return True
    return False


# ══════════════════════════════════════════════════════════════════════════════
# 4. حقن الأسلوب في موجّه AI
# ══════════════════════════════════════════════════════════════════════════════
def apply_style_to_prompt(base_prompt: str, profile_id: str) -> str:
    """
    يُضيف البصمة الأسلوبية إلى أي موجّه AI.
    يُعيد الموجّه المُعزَّز أو الأصلي إذا لم يُوجد الملف.
    """
    profile = load_style_profile(profile_id)
    if not profile:
        return base_prompt
    injection = profile.get("prompt_injection", "")
    if not injection:
        injection = _build_injection(profile)
    return f"{injection}\n\n{base_prompt}"


def get_style_system_prompt(profile_id: str) -> str:
    """
    يُعيد system-prompt جاهزاً للحقن في Gemini / Ollama / Claude.
    يُستخدم عند إنشاء التقارير المحاكية.
    """
    profile = load_style_profile(profile_id)
    if not profile:
        return ""
    return profile.get("prompt_injection", _build_injection(profile))
