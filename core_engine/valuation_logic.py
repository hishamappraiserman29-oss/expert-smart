"""
valuation_logic.py
==================
المحرك الحسابي الشامل — IVS-compliant valuation engine.

يُنفّذ الرؤية الكاملة:
  1. RAG  — يجلب مقارنات حقيقية من Qdrant (بيانات السوق الفعلية)
  2. AI   — يستخدم GPT-4o لكتابة تحليل HBU واحترافي بالعربية
  3. IVS  — يحسب 3 أساليب تقييم معيارية (سوق / تكلفة / دخل)
  4. Reconciliation — يوفّق النتائج ويعيدها لـ bridge_api.py

المُخرجات متوافقة تماماً مع ما يتوقعه bridge_api.py
"""

import os
import sys
import json
import math

# ─── Paths ────────────────────────────────────────────────────────────────────
_CORE_DIR   = os.path.dirname(os.path.abspath(__file__))

# ─── تحميل متغيرات البيئة بـ python-dotenv إن وُجد ──────────────────────────
try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv(os.path.join(_CORE_DIR, ".env"), override=False)
except ImportError:
    pass
_ROOT_DIR   = os.path.join(_CORE_DIR, "..")
_RAG_DIR    = os.path.join(_ROOT_DIR, "expert_smart_system")
_VECTOR_DB  = os.path.join(_RAG_DIR,  "vector_db")

# إضافة مسار RAG لـ sys.path حتى يمكن استيراد query.py
sys.path.insert(0, _RAG_DIR)

# ─── Constants ────────────────────────────────────────────────────────────────
INTEREST_RATE    = 0.085   # سعر الفائدة السائد
ECONOMIC_LIFE    = 60      # العمر الاقتصادي للمبنى
LAND_RATIO       = 0.30    # نسبة الأرض من القيمة الكلية
BUILD_COST_PM2   = 5500    # تكلفة بناء المتر (EGP)

# ─── GIS: إحداثيات مناطق القاهرة الكبرى ──────────────────────────────────────
_AREA_COORDS = {
    "المعادي":          (29.961, 31.258),
    "الزمالك":          (30.059, 31.224),
    "المهندسين":        (30.055, 31.195),
    "مدينة نصر":        (30.074, 31.338),
    "التجمع الخامس":    (30.009, 31.500),
    "مصر الجديدة":      (30.087, 31.323),
    "دريم لاند":        (29.977, 31.049),
    "الشيخ زايد":       (30.010, 30.957),
    "6 أكتوبر":         (29.930, 30.936),
    "أكتوبر":           (29.930, 30.936),
    "الهرم":            (29.990, 31.130),
    "فيصل":             (29.980, 31.139),
    "الدقي":            (30.042, 31.211),
    "العجوزة":          (30.055, 31.215),
    "بولاق":            (30.060, 31.238),
    "القاهرة":          (30.044, 31.236),
}

# ─── GIS: قاعدة بيانات مكانية للمقارنات (من Dreamland — إحداثيات حقيقية) ──────
_SPATIAL_COMPS = [
    {"floor":1, "area":72,  "year":2016, "ppm":21956, "x":29.97791, "y":31.05436},
    {"floor":1, "area":71,  "year":2016, "ppm":22000, "x":29.97791, "y":31.05383},
    {"floor":2, "area":72,  "year":2016, "ppm":21885, "x":29.97766, "y":31.04647},
    {"floor":3, "area":92,  "year":2017, "ppm":21436, "x":29.97790, "y":31.04300},
    {"floor":4, "area":92,  "year":2017, "ppm":21368, "x":29.97790, "y":31.04200},
    {"floor":8, "area":297, "year":2000, "ppm":26208, "x":29.97760, "y":31.05800},
    {"floor":9, "area":417, "year":2000, "ppm":25773, "x":29.97750, "y":31.05600},
    {"floor":1, "area":372, "year":2000, "ppm":26855, "x":29.97800, "y":31.04700},
    {"floor":5, "area":331, "year":2000, "ppm":26925, "x":29.97810, "y":31.04750},
    {"floor":5, "area":67,  "year":2007, "ppm":23584, "x":29.97600, "y":31.05900},
    {"floor":1, "area":67,  "year":2007, "ppm":24303, "x":29.97620, "y":31.05700},
    {"floor":1, "area":67,  "year":2007, "ppm":24849, "x":29.97650, "y":31.05500},
    {"floor":4, "area":72,  "year":2016, "ppm":21749, "x":29.97791, "y":31.05436},
    {"floor":1, "area":70,  "year":2017, "ppm":21617, "x":29.97791, "y":31.04437},
    {"floor":5, "area":312, "year":2013, "ppm":17505, "x":29.97850, "y":31.04900},
    {"floor":1, "area":224, "year":2000, "ppm":27392, "x":29.97800, "y":31.04880},
    {"floor":7, "area":533, "year":2000, "ppm":25247, "x":29.97820, "y":31.04860},
    {"floor":1, "area":67,  "year":2009, "ppm":23273, "x":29.97650, "y":31.05480},
    {"floor":4, "area":67,  "year":2009, "ppm":23067, "x":29.97660, "y":31.05490},
    {"floor":1, "area":110, "year":2007, "ppm":24677, "x":29.97670, "y":31.05500},
]


def _get_target_coords(location: str) -> tuple:
    """يحوّل اسم المنطقة إلى إحداثيات جغرافية."""
    for area_name, coords in _AREA_COORDS.items():
        if area_name in location:
            return coords
    return (30.044, 31.236)   # مركز القاهرة كقيمة افتراضية


def _compute_gis(location: str) -> dict:
    """
    يحسب سعر المتر عبر IDW و Kriging بناءً على موقع العقار المستهدف.
    يعيد: {idw_ppm, kriging_ppm}
    """
    target = _get_target_coords(location)
    xs     = [c["x"] for c in _SPATIAL_COMPS]
    ys     = [c["y"] for c in _SPATIAL_COMPS]
    prices = [c["ppm"] for c in _SPATIAL_COMPS]

    # ── IDW ──────────────────────────────────────────────────────────────────
    try:
        from scipy.spatial.distance import euclidean
        dists = [euclidean(target, (x, y)) for x, y in zip(xs, ys)]
        min_d = min(dists)
        if min_d < 1e-10:
            idw_ppm = float(prices[dists.index(min_d)])
        else:
            weights = [1.0 / (d ** 2) for d in dists]
            w_sum   = sum(weights)
            idw_ppm = sum(w * p for w, p in zip(weights, prices)) / w_sum
    except Exception:
        idw_ppm = float(sum(prices) / len(prices))

    # ── Kriging ───────────────────────────────────────────────────────────────
    try:
        from pykrige.ok import OrdinaryKriging
        ok = OrdinaryKriging(
            xs, ys, prices,
            variogram_model="linear",
            verbose=False,
            enable_plotting=False,
        )
        krig_vals, _ = ok.execute("points", [target[0]], [target[1]])
        kriging_ppm  = float(krig_vals[0])
    except Exception:
        kriging_ppm = idw_ppm

    return {
        "idw_ppm":     round(idw_ppm, 0),
        "kriging_ppm": round(kriging_ppm, 0),
    }


def _compute_ols(area: float, floor_num: int, year_built: int) -> dict:
    """
    نموذج OLS على قاعدة _SPATIAL_COMPS:
      المتغيرات: floor, area, year_built → price_per_m²
    يعيد: {r_squared, coefficients, predicted_ppm}
    """
    try:
        import numpy as np
        import statsmodels.api as sm

        X = np.array([[c["floor"], c["area"], c["year"]] for c in _SPATIAL_COMPS])
        y = np.array([float(c["ppm"]) for c in _SPATIAL_COMPS])
        X_sm  = sm.add_constant(X)
        model = sm.OLS(y, X_sm).fit()

        x_new     = np.array([[1.0, float(floor_num), float(area), float(year_built)]])
        pred_ppm  = float(model.predict(x_new)[0])
        pred_ppm  = max(pred_ppm, 5000)   # حد أدنى معقول

        return {
            "r_squared":     round(float(model.rsquared), 3),
            "adj_r_squared": round(float(model.rsquared_adj), 3),
            "coefficients": {
                "const":      round(float(model.params[0]), 2),
                "floor":      round(float(model.params[1]), 2),
                "area":       round(float(model.params[2]), 2),
                "year_built": round(float(model.params[3]), 2),
            },
            "pvalues": {
                "const":      round(float(model.pvalues[0]), 4),
                "floor":      round(float(model.pvalues[1]), 4),
                "area":       round(float(model.pvalues[2]), 4),
                "year_built": round(float(model.pvalues[3]), 4),
            },
            "predicted_ppm": round(pred_ppm, 0),
            "n_obs":         len(_SPATIAL_COMPS),
        }
    except Exception:
        return {
            "r_squared":     0.0,
            "adj_r_squared": 0.0,
            "coefficients":  {},
            "pvalues":       {},
            "predicted_ppm": 0.0,
            "n_obs":         0,
        }

# ─── RAG: load embedding model + Qdrant (lazy, once) ─────────────────────────
_rag_model  = None
_rag_client = None

def _get_rag():
    """تحميل نموذج التضمين + Qdrant مرة واحدة فقط."""
    global _rag_model, _rag_client
    if _rag_model is None:
        try:
            print("\n[AI Brain] Loading Multilingual Embedding Model (small)... Please wait.")
            from sentence_transformers import SentenceTransformer
            from qdrant_client import QdrantClient
            _rag_model  = SentenceTransformer("intfloat/multilingual-e5-small")
            _rag_client = QdrantClient(path=_VECTOR_DB)
            print("[AI Brain] Model loaded successfully.")
        except Exception as e:
            print(f"[AI Brain] Error loading AI models: {e}")
            _rag_model  = None
            _rag_client = None
    return _rag_model, _rag_client


def _rag_search(location: str, top_k: int = 5):
    """
    يبحث في Qdrant عن العقارات الأقرب للموقع المُدخل.
    يُعيد قائمة بـ dicts: {loc, pr, ar, price_per_m2}
    يدعم qdrant-client >= 1.7 (query_points) و < 1.7 (search)
    """
    model, client = _get_rag()
    if model is None or client is None:
        return []
    try:
        print(f"[RAG] Searching for market comparables in: {location}...")
        query_text = f"query: شقة في {location}"
        vector     = model.encode(query_text).tolist()

        # qdrant-client >= 1.7 — query_points is the stable API
        # client.search() was removed in v1.12+; do NOT use it as fallback
        response = client.query_points(
            collection_name="egypt_estate",
            query=vector,
            limit=top_k,
            with_payload=True,
        )
        raw_hits = response.points

        results = []
        for h in raw_hits:
            p  = h.payload or {}
            ar = max(float(p.get("ar", 100)), 1)
            pr = float(p.get("pr", 0))
            results.append({
                "loc":          p.get("loc", location),
                "pr":           pr,
                "ar":           ar,
                "price_per_m2": round(pr / ar, 0),
            })
        print(f"[RAG] Found {len(results)} relevant market records.")
        return results
    except Exception as e:
        print(f"[RAG] Search failed or Qdrant unavailable: {e}")
        return []


# ─── AI: GPT-4o for HBU + narrative ──────────────────────────────────────────
def _load_openai_key() -> str:
    """يحاول تحميل مفتاح OpenAI من البيئة (python-dotenv يُحمَّل مسبقاً)."""
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        # fallback يدوي إن لم يُحمَّل dotenv
        env_path = os.path.join(_CORE_DIR, ".env")
        if os.path.exists(env_path):
            try:
                with open(env_path, encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if line.startswith("OPENAI_API_KEY="):
                            key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
            except Exception:
                pass
    return key


def _ai_hbu(property_type: str, location: str, area: float,
            building_age: int, market_comps: list) -> str:
    """
    يستخدم GPT-4o لكتابة تحليل HBU احترافي بالعربية.
    يُعيد نصاً من 3-4 جمل إذا نجح، وإلا يُعيد نصاً افتراضياً.
    """
    api_key = _load_openai_key()
    if not api_key:
        return _default_hbu(property_type, location)

    # ملخص المقارنات للسياق
    comps_summary = ""
    if market_comps:
        lines = [
            f"- {c['loc']}: {c['price_per_m2']:,.0f} EGP/م² (مساحة {c['ar']:.0f} م²)"
            for c in market_comps[:3]
        ]
        comps_summary = "\n".join(lines)

    prompt = (
        f"أنت خبير تقييم عقاري معتمد وفق معايير IVS. اكتب تحليل (أعلى وأفضل استخدام - HBU) "
        f"لعقار من النوع: {property_type}، في منطقة: {location}، "
        f"المساحة: {area} م²، عمر المبنى: {building_age} سنة.\n\n"
        f"بيانات السوق المحيط:\n{comps_summary}\n\n"
        f"اكتب تحليل HBU في 4 جمل فقط بالعربية الفصحى المهنية، مُحدداً: "
        f"(1) الاستخدام المادياً الممكن، (2) المسموح قانونياً، "
        f"(3) المجدي مالياً، (4) الأعلى إنتاجية. "
        f"لا تذكر أرقاماً مباشرة من البيانات."
    )

    try:
        print(f"[AI] Generating HBU for location={location!r}...")
        import openai
        client   = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.4,
        )
        print("[AI] HBU analysis generated successfully.")
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[AI] OpenAI Error: {e}")
        return _default_hbu(property_type, location)


def _default_hbu(property_type: str, location: str) -> str:
    return (
        f"بناءً على الفحص المتكامل للأبعاد الأربعة، يتبين أن الاستخدام الحالي "
        f"كـ{property_type} في {location} يُمثّل أعلى وأفضل استخدام للعقار؛ "
        f"إذ يتوافق مع التوجيهات التنظيمية للمنطقة ويحقق أعلى عائد استثماري "
        f"ضمن المعطيات القانونية والمادية المتاحة وفق معايير IVS 105."
    )


# ─── Valuation Methods ────────────────────────────────────────────────────────

def _market_approach(area: float, comps: list, input_ppm: float):
    """
    أسلوب مقارنة السوق — يستخدم مقارنات RAG الحقيقية إن وُجدت،
    وإلا يبني 3 مقارنات اصطناعية حول سعر الإدخال.
    """
    if not comps:
        # بديل إذا لم يجد RAG شيئاً
        comps = [
            {"loc": "نفس الحي",     "price_per_m2": input_ppm + 500},
            {"loc": "مربع مقارب",   "price_per_m2": input_ppm - 200},
            {"loc": "شارع مجاور",   "price_per_m2": input_ppm},
        ]

    adj_comps  = []
    total_adj  = 0
    for i, c in enumerate(comps):
        base = float(c.get("price_per_m2", input_ppm))
        adj  = base * 0.95       # خصم تفاوض 5%
        total_adj += adj
        adj_comps.append({
            "name":      c.get("loc", f"مقارن {i+1}"),
            "location":  c.get("loc", "غير محدد"),
            "base_price": base,
            "adj_price":  adj,
        })

    avg_ppm = total_adj / len(adj_comps) if adj_comps else input_ppm
    return avg_ppm * area, avg_ppm, adj_comps


def _cost_approach(area: float, price_per_m2: float, building_age: int):
    """أسلوب التكلفة الاستبدالية المستهلكة (DRC)"""
    land_ppm        = price_per_m2 * LAND_RATIO
    land_value      = land_ppm * area

    # تكلفة البناء بمكوناتها
    gross_build     = BUILD_COST_PM2 * area
    contractor      = gross_build * 0.15
    total_build     = gross_build + contractor

    # إهلاك خطي + وظيفي
    eff_age         = min(building_age, ECONOMIC_LIFE)
    physical_depr   = (eff_age / ECONOMIC_LIFE) * total_build
    functional_depr = total_build * 0.02
    total_depr      = physical_depr + functional_depr
    net_build       = total_build - total_depr

    total_value     = land_value + net_build
    return {
        "value":              total_value,
        "ppm":                total_value / area if area else 0,
        "land_value":         land_value,
        "gross_building_cost": total_build,
        "depreciation":       total_depr,
        "net_build":          net_build,
        "building_area":      area,
        "building_age":       building_age,
    }


def _income_approach(area: float, rent_per_sqm: float,
                     cap_rate: float, building_age: int, land_value: float):
    """أسلوب رأسمالة الدخل"""
    annual_gross    = area * rent_per_sqm
    vacancy_loss    = annual_gross * 0.10
    noi             = annual_gross - vacancy_loss

    remaining_life  = max(ECONOMIC_LIFE - building_age, 5)
    cap_recovery    = 1.0 / remaining_life
    effective_cap   = INTEREST_RATE + cap_recovery

    land_return     = land_value * INTEREST_RATE

    if noi > land_return:
        bldg_income = noi - land_return
        bldg_value  = bldg_income / effective_cap
        total_value = bldg_value + land_value
    else:
        # direct capitalisation عند إيجار منخفض
        total_value = noi / effective_cap if effective_cap > 0 else 0

    return {
        "value":        total_value,
        "ppm":          total_value / area if area else 0,
        "noi":          noi,
        "cap_rate":     cap_rate,
        "rent_per_sqm": rent_per_sqm,
    }


# ─── Backward-compat helpers (used by bridge_api.py directly) ─────────────────

def hbu_analysis():
    return _default_hbu("عقار سكني", "المنطقة")


def market_approach(area_sqm, comparables):
    val, _, comps = _market_approach(area_sqm, [], 10000)
    return val, comps


def cost_approach(land_area, land_price_sqm, building_area, building_cost_sqm, age_years):
    r = _cost_approach(building_area, land_price_sqm, age_years)
    return r["value"], r["gross_building_cost"], r["depreciation"]


def income_approach(building_area, rent_per_sqm, cap_rate):
    r = _income_approach(building_area, rent_per_sqm, cap_rate, 10, 0)
    return r["value"], r["noi"]


def calculate_property_valuation(area_sqm, price_per_meter, region="SA"):
    total_value = area_sqm * price_per_meter
    return f"تم حساب القيمة المبدئية: {total_value:,.0f}"


# أسعار مرجعية لأحياء الرياض (SAR/م²)
_RIYADH_PRICES = {
    "الملقا":   12000,
    "النرجس":   11000,
    "الياسمين": 10500,
    "العليا":   15000,
    "الورود":   9500,
    "الغدير":   8500,
}

def get_estimated_price(neighborhood: str) -> float:
    """
    يُعيد سعر المتر التقديري لحي سكني في الرياض (SAR/م²).
    يُستخدم من rag_pipeline.py.
    """
    for key, price in _RIYADH_PRICES.items():
        if key in neighborhood:
            return float(price)
    return 10000.0   # قيمة افتراضية


# ─── Valuation Purpose Profiles ──────────────────────────────────────────────
#
# Each profile defines:
#   weights        — reconciliation weights [market, cost, income, gis_idw, gis_krig, ols]
#   forced_discount — haircut applied to reconciled value after weighting
#   cap_rate_adj   — added to user cap_rate (higher risk → higher cap)
#   label_ar       — Arabic label for reports
#   label_en       — English label
#
_PURPOSE_PROFILES = {
    # Standard IVS Fair Market Value
    "fair_market": {
        "label_ar":       "القيمة السوقية العادلة",
        "label_en":       "Fair Market Value (IVS)",
        "weights":        [0.35, 0.20, 0.15, 0.12, 0.10, 0.08],
        "forced_discount": 0.00,
        "cap_rate_adj":   0.00,
    },
    # Forced-sale / liquidation — RICS VPS 4
    "liquidation": {
        "label_ar":       "قيمة التصفية / البيع القسري",
        "label_en":       "Liquidation / Forced Sale Value",
        "weights":        [0.50, 0.15, 0.15, 0.10, 0.05, 0.05],
        "forced_discount": 0.20,   # 20% forced-sale haircut
        "cap_rate_adj":   0.03,    # +3% risk premium
    },
    # Taxation / Assessment Value — conservative lower bound
    "taxation": {
        "label_ar":       "القيمة التقديرية للأغراض الضريبية",
        "label_en":       "Taxation / Assessment Value",
        "weights":        [0.20, 0.40, 0.25, 0.08, 0.05, 0.02],
        "forced_discount": 0.10,   # 10% conservative deduction
        "cap_rate_adj":   0.01,
    },
    # Usufruct / Right of Use — income-dominant
    "usufruct": {
        "label_ar":       "قيمة حق الانتفاع",
        "label_en":       "Usufruct / Right of Use Value",
        "weights":        [0.15, 0.10, 0.55, 0.10, 0.05, 0.05],
        "forced_discount": 0.00,
        "cap_rate_adj":   0.00,
    },
    # Banking / Mortgage Security — Basel III / CBE collateral framework
    "banking": {
        "label_ar":       "قيمة الضمان البنكي (Basel III)",
        "label_en":       "Banking / Mortgage Security Value (Basel III)",
        "weights":        [0.40, 0.25, 0.15, 0.10, 0.05, 0.05],
        "forced_discount": 0.15,   # 15% prudential haircut for collateral
        "cap_rate_adj":   0.02,    # +2% risk premium (CBE guidelines)
    },
    # REITs / IFRS 13 Fair Value for Investment Property
    "reits": {
        "label_ar":       "القيمة العادلة للصناديق العقارية (IFRS 13)",
        "label_en":       "REITs / Investment Property Fair Value (IFRS 13)",
        "weights":        [0.25, 0.10, 0.45, 0.10, 0.05, 0.05],
        "forced_discount": 0.00,
        "cap_rate_adj":  -0.01,    # -1% premium for institutional-grade assets
    },
}


# ─── Land Dual Path ──────────────────────────────────────────────────────────

def _land_sales_comparison(area: float, price_pm2: float, location: str) -> dict:
    """
    Sales Comparison Matrix for land — مصفوفة مقارنات الأرض.
    توليد 4 مقارنات أراضٍ بستة عوامل تعديل IVS-105.
    """
    base_land_ppm = price_pm2 * LAND_RATIO

    raw_comps = [
        {"name": f"أرض 1 — {location}",       "base_ppm": base_land_ppm * 1.05, "adj": {"time": -0.02, "location": 0.00, "area": +0.03, "frontage": 0.00, "legal": 0.00, "view": +0.02}},
        {"name": f"أرض 2 — مجاور مباشر",      "base_ppm": base_land_ppm * 0.97, "adj": {"time": -0.01, "location": +0.05, "area": -0.02, "frontage": +0.03, "legal": 0.00, "view": 0.00}},
        {"name": f"أرض 3 — حي مقارب",         "base_ppm": base_land_ppm * 1.10, "adj": {"time": -0.03, "location": -0.05, "area": +0.02, "frontage": -0.02, "legal": +0.02, "view": 0.00}},
        {"name": f"أرض 4 — المنطقة الموسّعة", "base_ppm": base_land_ppm * 0.93, "adj": {"time": 0.00, "location": +0.08, "area": +0.01, "frontage": 0.00, "legal": 0.00, "view": +0.03}},
    ]

    adj_factor_labels = {
        "time":     "التعديل الزمني",
        "location": "تعديل الموقع",
        "area":     "تعديل المساحة",
        "frontage": "تعديل الواجهة",
        "legal":    "تعديل الوضع القانوني",
        "view":     "تعديل الإطلالة",
    }

    grid = []
    total_adj_ppm = 0.0
    for w_idx, comp in enumerate(raw_comps):
        total_adj_factor = sum(comp["adj"].values())
        adjusted_ppm = comp["base_ppm"] * (1 + total_adj_factor)
        total_adj_ppm += adjusted_ppm
        grid.append({
            "name":             comp["name"],
            "base_ppm":         round(comp["base_ppm"], 0),
            "adjustments":      {adj_factor_labels[k]: f"{v*100:+.0f}%" for k, v in comp["adj"].items()},
            "total_adj_pct":    f"{total_adj_factor*100:+.1f}%",
            "adjusted_ppm":     round(adjusted_ppm, 0),
            "weight":           0.25,
        })

    avg_land_ppm = total_adj_ppm / len(grid)
    land_value_sc = avg_land_ppm * area

    return {
        "method":        "sales_comparison",
        "label_ar":      "أسلوب مصفوفة مقارنات الأرض",
        "grid":          grid,
        "avg_land_ppm":  round(avg_land_ppm, 0),
        "land_value":    round(land_value_sc, 0),
        "area":          area,
    }


def _land_residual(area: float, price_pm2: float) -> dict:
    """
    Residual Method — طريقة الباقي لتقدير قيمة الأرض.
    Land Value = GDV − Construction Cost − Developer Profit − Finance Costs
    """
    # GDV: القيمة البيعية الإجمالية عند التطوير
    gfa_ratio       = 2.0                          # نسبة البناء الإجمالية (FAR) = 2×مساحة الأرض
    saleable_area   = area * gfa_ratio * 0.85      # نسبة القابل للبيع 85%
    sales_price_pm2 = price_pm2 * 1.25             # سعر الوحدة المطورة أعلى بـ25%
    gdv             = saleable_area * sales_price_pm2

    # تكلفة البناء
    construction_cost = area * gfa_ratio * BUILD_COST_PM2
    contractor_margin = construction_cost * 0.12
    total_build_cost  = construction_cost + contractor_margin

    # تكاليف التطوير الناعمة
    professional_fees = gdv * 0.03
    marketing_costs   = gdv * 0.02

    # ربح المطور (20% من GDV)
    developer_profit  = gdv * 0.20

    # تكاليف التمويل (افتراض 18 شهر تطوير)
    finance_cost      = total_build_cost * INTEREST_RATE * 1.5

    # قيمة الأرض كباقي
    land_value_res = gdv - total_build_cost - professional_fees - marketing_costs - developer_profit - finance_cost

    return {
        "method":             "residual",
        "label_ar":           "طريقة الباقي (التطوير)",
        "gdv":                round(gdv, 0),
        "saleable_area_m2":   round(saleable_area, 0),
        "sales_price_pm2":    round(sales_price_pm2, 0),
        "total_build_cost":   round(total_build_cost, 0),
        "professional_fees":  round(professional_fees, 0),
        "marketing_costs":    round(marketing_costs, 0),
        "developer_profit":   round(developer_profit, 0),
        "developer_profit_pct": "20%",
        "finance_cost":       round(finance_cost, 0),
        "land_value":         round(max(land_value_res, 0), 0),
        "area":               area,
        "avg_land_ppm":       round(max(land_value_res, 0) / area, 0) if area else 0,
    }


def _land_dual_path(area: float, price_pm2: float, location: str,
                    sc_weight: float = 0.60, res_weight: float = 0.40) -> dict:
    """
    Dual Path Land Valuation — المسار المزدوج لتقدير قيمة الأرض.
    يوفّق بين: مصفوفة المقارنات السوقية (60%) + طريقة الباقي (40%).
    """
    sc  = _land_sales_comparison(area, price_pm2, location)
    res = _land_residual(area, price_pm2)

    reconciled_land_ppm   = sc["avg_land_ppm"] * sc_weight + res["avg_land_ppm"] * res_weight
    reconciled_land_value = reconciled_land_ppm * area

    return {
        "sales_comparison":       sc,
        "residual":               res,
        "sc_weight":              sc_weight,
        "residual_weight":        res_weight,
        "reconciled_land_ppm":    round(reconciled_land_ppm, 0),
        "reconciled_land_value":  round(reconciled_land_value, 0),
        "delta_pct":              round(abs(sc["avg_land_ppm"] - res["avg_land_ppm"]) / max(sc["avg_land_ppm"], 1) * 100, 1),
    }


# ─── Main entry: advanced_valuation ──────────────────────────────────────────

def advanced_valuation(data: dict) -> dict:
    """
    المحرك الحسابي الشامل — يستدعي RAG + AI + IVS methods.

    المدخلات (data dict):
      area              (float)  المساحة م²
      price_per_meter   (float)  سعر المتر السوقي المرجعي
      location          (str)    الموقع / المنطقة
      building_age      (int)    عمر المبنى بالسنوات
      rent_per_sqm      (float)  الإيجار السنوي EGP/م²
      cap_rate          (float)  معدل الرسملة (0.08 = 8%)
      property_type     (str)    نوع العقار (اختياري)
      valuation_purpose (str)    fair_market | liquidation | taxation | usufruct

    المخرجات: dict متوافق مع ما يتوقعه bridge_api.py
    """
    area          = float(data.get("area", 0))
    price_pm2     = float(data.get("price_per_meter", 10000))
    location      = data.get("location", "غير محدد")
    building_age  = int(data.get("building_age", 5))
    rent_per_sqm  = float(data.get("rent_per_sqm", 400))
    cap_rate      = float(data.get("cap_rate", 0.08))
    property_type = data.get("property_type", "شقة سكنية")
    floor_num     = int(data.get("floor", 1))
    year_built    = int(data.get("year_built", 2015))
    land_method   = data.get("land_method", "standard")   # 'dual_path' | 'standard'

    # ── Purpose profile ───────────────────────────────────────────────────────
    purpose_key = data.get("valuation_purpose", "fair_market")
    if purpose_key not in _PURPOSE_PROFILES:
        purpose_key = "fair_market"
    profile     = _PURPOSE_PROFILES[purpose_key]
    cap_rate    = cap_rate + profile["cap_rate_adj"]

    # ── Step 1: RAG — جلب مقارنات حقيقية من Qdrant ──────────────────────────
    print(f"[Valuation Engine] Processing: type={property_type!r} location={location!r}")
    rag_comps = _rag_search(location, top_k=5)

    # ── Step 2: IVS calculations ──────────────────────────────────────────────
    print("[Valuation Engine] Calculating IVS Methods (Market, Cost, Income)...")
    market_val, market_ppm, adj_comps = _market_approach(area, rag_comps, price_pm2)

    # ── Land Dual Path (optional) ────────────────────────────────────────────
    land_dual = None
    if land_method == "dual_path":
        land_dual = _land_dual_path(area, price_pm2, location)
        # استخدم قيمة الأرض الموفّقة في أسلوبَي التكلفة والدخل
        reconciled_land_value = land_dual["reconciled_land_value"]
        cost_res  = _cost_approach(area, price_pm2, building_age)
        # تجاوز قيمة الأرض الافتراضية بالقيمة الموفّقة من المسار المزدوج
        cost_res["land_value"]  = reconciled_land_value
        cost_res["value"]       = reconciled_land_value + cost_res["net_build"]
    else:
        cost_res = _cost_approach(area, price_pm2, building_age)

    cost_val  = cost_res["value"]

    income_res = _income_approach(area, rent_per_sqm, cap_rate,
                                   building_age, cost_res["land_value"])
    income_val = income_res["value"]

    # ── Step 2b: GIS — IDW + Kriging المكاني ─────────────────────────────────
    gis = _compute_gis(location)

    # ── Step 2c: OLS — انحدار متعدد ──────────────────────────────────────────
    ols = _compute_ols(area, floor_num, year_built)

    # ── Step 3: AI — تحليل HBU بـ GPT-4o ────────────────────────────────────
    hbu = _ai_hbu(property_type, location, area, building_age, rag_comps)

    print("[Valuation Engine] Reconciling results...")
    # ── Step 4: Reconciliation — purpose-weighted ────────────────────────────
    gis_avg_ppm = (gis["idw_ppm"] + gis["kriging_ppm"]) / 2.0
    gis_val     = gis_avg_ppm * area
    ols_val     = ols["predicted_ppm"] * area if ols["predicted_ppm"] > 0 else 0.0

    w = profile["weights"]  # [market, cost, income, gis_idw, gis_krig, ols]

    if gis_val > 0 and ols_val > 0:
        raw_reconciled = (
            market_val              * w[0] +
            cost_val                * w[1] +
            income_val              * w[2] +
            gis["idw_ppm"] * area   * w[3] +
            gis["kriging_ppm"] * area * w[4] +
            ols_val                 * w[5]
        )
    else:
        # 3-method fallback (redistribute proportionally)
        total_w = w[0] + w[1] + w[2]
        raw_reconciled = (
            market_val * (w[0] / total_w) +
            cost_val   * (w[1] / total_w) +
            income_val * (w[2] / total_w)
        )

    # Apply forced-sale discount (liquidation / taxation)
    discount         = profile["forced_discount"]
    reconciled_value = raw_reconciled * (1.0 - discount)

    # ── Step 5: تجميع المخرجات ───────────────────────────────────────────────
    return {
        "hbu_text":         hbu,
        "location":         location,
        "valuation_purpose":  purpose_key,
        "purpose_label_ar":  profile["label_ar"],
        "purpose_label_en":  profile["label_en"],
        "forced_discount":   discount,
        "raw_reconciled":    raw_reconciled,
        "market": {
            "value":       market_val,
            "ppm":         market_ppm,
            "comparables": adj_comps,
            "rag_used":    len(rag_comps) > 0,
        },
        "cost": {
            "value":               cost_val,
            "gross_building_cost": cost_res["gross_building_cost"],
            "depreciation":        cost_res["depreciation"],
            "building_area":       cost_res["building_area"],
            "building_age":        cost_res["building_age"],
        },
        "income": {
            "value":        income_val,
            "noi":          income_res["noi"],
            "cap_rate":     income_res["cap_rate"],
            "rent_per_sqm": income_res["rent_per_sqm"],
        },
        "gis": gis,
        "ols": ols,
        "land_dual":        land_dual,
        "land_method":      land_method,
        "reconciled_value": reconciled_value,
        "area":             area,
    }
