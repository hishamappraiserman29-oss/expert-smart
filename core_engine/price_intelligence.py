# -*- coding: utf-8 -*-
"""
price_intelligence.py — Expert_Smart Sovereign Price Intelligence Engine
=========================================================================
بروتوكول الرصد اللحظي للأسعار العقارية — مصر والسعودية

المصادر الرئيسية:
  مصر:      aqarmap.com.eg | olx.com.eg | بيانات هيئة المجتمعات العمرانية
  السعودية: ejar.sa | aqar.sa | moj.gov.sa | rega.gov.sa

المخرجات:
  ① سعر الطلب + سعر التنفيذ + معامل التفاوض (5-10%)
  ② تحليل اتجاه السوق (فائدة + مواد بناء + صرف)
  ③ تقرير تحليلي بأسلوب خبير فئة A
  ④ جدول مقارنة جاهز للإكسيل
"""

from __future__ import annotations

import re
import json
import math
import time
import hashlib
import threading
import traceback
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

# ── Optional heavy imports (graceful degradation) ────────────────────────────
try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False

try:
    from bs4 import BeautifulSoup
    _BS4_OK = True
except ImportError:
    _BS4_OK = False


# ══════════════════════════════════════════════════════════════════════════════
#  Constants & Source Registry
# ══════════════════════════════════════════════════════════════════════════════

MARKET_EG  = "egypt"
MARKET_KSA = "ksa"

# Negotiation coefficient range (asking → execution)
NEG_LOW  = 0.05   # 5%
NEG_HIGH = 0.10   # 10%
NEG_MID  = 0.075  # 7.5% typical

# Price-per-metre benchmarks (EGP/SAR) — updated quarterly, used as sanity guards
_PPM_GUARD: Dict[str, Tuple[float, float]] = {
    "التجمع الخامس":    (25_000,  75_000),
    "القاهرة الجديدة":  (22_000,  70_000),
    "الشيخ زايد":       (18_000,  55_000),
    "العاصمة الإدارية": (30_000, 120_000),
    "النرجس":           (15_000,  45_000),
    "مدينة نصر":        (18_000,  55_000),
    "الرياض":           (2_000,   12_000),
    "جدة":              (1_800,   10_000),
    "الدمام":           (1_200,    8_000),
}

# Macro-economic trend keywords (Arabic + English) for news scraping
_TREND_QUERIES = {
    "interest":  ["سعر الفائدة مصر", "CBE interest rate", "سعر الفائدة السعودية", "SAMA rate"],
    "materials": ["أسعار الحديد مصر", "أسعار الأسمنت", "iron cement price egypt",
                  "أسعار مواد البناء"],
    "fx":        ["سعر الدولار مصر", "USD EGP exchange rate", "سعر الريال",
                  "سعر صرف الجنيه"],
    "realestate":["أسعار العقارات 2025", "real estate egypt 2025",
                  "أسعار الشقق مصر", "سوق العقارات السعودي"],
}

# Source configurations
@dataclass
class SourceCfg:
    name:       str
    market:     str
    base_url:   str
    search_tpl: str          # format with location + asset_type
    card_sel:   str
    price_sel:  str
    area_sel:   str
    loc_sel:    str
    currency:   str
    uses_js:    bool = False  # True = requires Playwright


_SOURCES: List[SourceCfg] = [
    # ─── Egypt ──────────────────────────────────────────────────────────────
    SourceCfg(
        name="aqarmap",  market=MARKET_EG,
        base_url="https://aqarmap.com.eg",
        search_tpl="https://aqarmap.com.eg/ar/for-sale/cairo/{location}/",
        card_sel=".listing-card",
        price_sel=".listing-price strong, .price",
        area_sel=".listing-area, [data-feature='area']",
        loc_sel=".listing-location, .location",
        currency="EGP",
    ),
    SourceCfg(
        name="olx_eg",  market=MARKET_EG,
        base_url="https://www.olx.com.eg",
        search_tpl="https://www.olx.com.eg/ar/ads/q-{location}-عقار/",
        card_sel="li[data-aut-id='itemBox']",
        price_sel="[data-aut-id='itemPrice']",
        area_sel="[data-aut-id='item-details-area']",
        loc_sel="[data-aut-id='item-location']",
        currency="EGP",
    ),
    # ─── Saudi Arabia ────────────────────────────────────────────────────────
    SourceCfg(
        name="aqar_sa",  market=MARKET_KSA,
        base_url="https://sa.aqar.fm",
        search_tpl="https://sa.aqar.fm/%D8%B4%D9%82%D9%82/{location}/buy",
        card_sel=".item-card, [data-type='property']",
        price_sel=".item-price, .price-value",
        area_sel=".item-area, [data-feature='area']",
        loc_sel=".item-location, .location-name",
        currency="SAR",
        uses_js=True,
    ),
    SourceCfg(
        name="ejar",  market=MARKET_KSA,
        base_url="https://www.ejar.sa",
        search_tpl="https://www.ejar.sa/en/search?city={location}&type=sale",
        card_sel=".property-card",
        price_sel=".property-price",
        area_sel=".property-area",
        loc_sel=".property-location",
        currency="SAR",
        uses_js=True,
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
#  Data Models
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class PriceRecord:
    source:          str
    market:          str
    location:        str
    asset_type:      str
    area_m2:         Optional[float]
    asking_price:    Optional[float]
    execution_price: Optional[float]   # asking × (1 - negotiation_coeff)
    ppm_asking:      Optional[float]
    ppm_execution:   Optional[float]
    currency:        str
    negotiation_pct: float
    url:             str
    scraped_at:      str
    raw_text:        str = ""
    confidence:      float = 0.5

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class TrendSignal:
    category:   str           # interest | materials | fx | realestate
    headline:   str
    impact:     str           # positive | negative | neutral
    impact_pct: Optional[float]
    source:     str
    date:       str


@dataclass
class MarketIntelligenceReport:
    query_location:  str
    query_market:    str
    query_asset:     str
    generated_at:    str
    records:         List[PriceRecord]
    trends:          List[TrendSignal]
    summary:         Dict          # avg PPM, min/max, count, etc.
    analysis_text:   str           # A-class expert narrative (Arabic)
    excel_table:     List[Dict]    # ready for openpyxl injection
    data_sources:    List[str]


# ══════════════════════════════════════════════════════════════════════════════
#  HTTP Session (shared, with retries)
# ══════════════════════════════════════════════════════════════════════════════

def _make_session() -> Optional[Any]:
    if not _REQUESTS_OK:
        return None
    sess = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5,
                  status_forcelist=[429, 500, 502, 503, 504])
    sess.mount("https://", HTTPAdapter(max_retries=retry))
    sess.mount("http://",  HTTPAdapter(max_retries=retry))
    sess.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ar,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    return sess


# ══════════════════════════════════════════════════════════════════════════════
#  Arabic Number / Price Normaliser
# ══════════════════════════════════════════════════════════════════════════════

_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_MULT = {"مليار": 1_000_000_000, "مليون": 1_000_000, "ألف": 1_000, "الف": 1_000, "k": 1_000}


def _norm_num(text: str) -> str:
    return text.translate(_AR_DIGITS).replace("،", ",").replace("٫", ".")


def _parse_price(raw: str) -> Optional[float]:
    """يحوّل نصاً خاماً إلى قيمة رقمية (EGP/SAR)."""
    if not raw:
        return None
    t = _norm_num(raw.strip())
    for unit, mult in _MULT.items():
        m = re.search(rf"(\d+(?:[.,]\d+)?)\s*{unit}", t, re.I)
        if m:
            try:
                return float(m.group(1).replace(",", ".")) * mult
            except ValueError:
                pass
    # Plain number with optional commas
    m = re.search(r"(\d[\d,\.]+)", t)
    if m:
        try:
            v = float(m.group(1).replace(",", ""))
            if 50_000 <= v <= 500_000_000:
                return v
        except ValueError:
            pass
    return None


def _parse_area(raw: str) -> Optional[float]:
    t = _norm_num(raw.strip())
    for pat in [r"(\d+(?:[.,]\d+)?)\s*م", r"(\d+(?:[.,]\d+)?)\s*متر",
                r"(\d+(?:[.,]\d+)?)\s*sqm", r"(\d+(?:[.,]\d+)?)\s*m²"]:
        m = re.search(pat, t)
        if m:
            try:
                v = float(m.group(1).replace(",", "."))
                if 15 <= v <= 50_000:
                    return v
            except ValueError:
                pass
    return None


# ══════════════════════════════════════════════════════════════════════════════
#  Web Scraper (requests + BeautifulSoup)
# ══════════════════════════════════════════════════════════════════════════════

class PriceScraper:
    """يسحب إعلانات الأسعار من المصادر المحددة."""

    def __init__(self, session: Optional[Any] = None):
        self._sess = session or _make_session()

    def scrape_source(
        self,
        cfg: SourceCfg,
        location: str,
        asset_type: str = "شقة",
        max_items: int = 20,
    ) -> List[PriceRecord]:
        if not _REQUESTS_OK or not _BS4_OK:
            return []
        if cfg.uses_js:
            return self._scrape_with_playwright(cfg, location, asset_type, max_items)
        return self._scrape_with_requests(cfg, location, asset_type, max_items)

    # ── requests path ────────────────────────────────────────────────────────

    def _scrape_with_requests(
        self, cfg: SourceCfg, location: str, asset_type: str, max_items: int
    ) -> List[PriceRecord]:
        url = cfg.search_tpl.format(
            location=requests.utils.quote(location, safe="") if _REQUESTS_OK else location
        )
        records: List[PriceRecord] = []
        try:
            resp = self._sess.get(url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select(cfg.card_sel)[:max_items]
            for card in cards:
                rec = self._parse_card(card, cfg, location, asset_type, url)
                if rec:
                    records.append(rec)
        except Exception as exc:
            print(f"  [PriceScraper:{cfg.name}] {exc}")
        return records

    # ── Playwright path (JS-heavy sites) ────────────────────────────────────

    def _scrape_with_playwright(
        self, cfg: SourceCfg, location: str, asset_type: str, max_items: int
    ) -> List[PriceRecord]:
        records: List[PriceRecord] = []
        try:
            from playwright.sync_api import sync_playwright
            url = cfg.search_tpl.format(location=location)
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
                ctx  = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
                    ),
                    locale="ar",
                )
                page = ctx.new_page()
                page.goto(url, timeout=30_000, wait_until="domcontentloaded")
                page.wait_for_timeout(2500)
                html = page.content()
                browser.close()

            soup  = BeautifulSoup(html, "html.parser")
            cards = soup.select(cfg.card_sel)[:max_items]
            for card in cards:
                rec = self._parse_card(card, cfg, location, asset_type, url)
                if rec:
                    records.append(rec)
        except Exception as exc:
            print(f"  [PriceScraper:{cfg.name}/pw] {exc}")
        return records

    # ── Card parser ──────────────────────────────────────────────────────────

    def _parse_card(
        self, card: Any, cfg: SourceCfg, location: str, asset_type: str, page_url: str
    ) -> Optional[PriceRecord]:
        try:
            price_el = card.select_one(cfg.price_sel)
            area_el  = card.select_one(cfg.area_sel)  if cfg.area_sel  else None
            loc_el   = card.select_one(cfg.loc_sel)   if cfg.loc_sel   else None

            raw_price = price_el.get_text(" ", strip=True) if price_el else ""
            raw_area  = area_el.get_text(" ",  strip=True) if area_el  else ""
            raw_loc   = loc_el.get_text(" ",   strip=True) if loc_el   else location

            asking = _parse_price(raw_price)
            area   = _parse_area(raw_area)

            if not asking:
                return None

            neg_coeff = _negotiate_coeff(asking, cfg.market, location)
            execution = round(asking * (1 - neg_coeff), 0)
            ppm_ask   = round(asking   / area, 1) if area else None
            ppm_exec  = round(execution / area, 1) if area else None

            # Sanity check: discard records wildly outside guard range
            guard = _PPM_GUARD.get(location)
            if guard and ppm_ask:
                lo, hi = guard
                # allow 2× tolerance for data diversity
                if not (lo * 0.5 <= ppm_ask <= hi * 2.0):
                    return None

            link = ""
            a_tag = card.find("a", href=True)
            if a_tag:
                link = cfg.base_url + a_tag["href"] if a_tag["href"].startswith("/") else a_tag["href"]

            return PriceRecord(
                source=cfg.name,
                market=cfg.market,
                location=raw_loc.strip() or location,
                asset_type=asset_type,
                area_m2=area,
                asking_price=asking,
                execution_price=execution,
                ppm_asking=ppm_ask,
                ppm_execution=ppm_exec,
                currency=cfg.currency,
                negotiation_pct=round(neg_coeff * 100, 1),
                url=link or page_url,
                scraped_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
                raw_text=(price_el.get_text() if price_el else "") + " | " + raw_area,
                confidence=_record_confidence(asking, area, raw_loc),
            )
        except Exception:
            return None


# ══════════════════════════════════════════════════════════════════════════════
#  Negotiation Coefficient Calculator
# ══════════════════════════════════════════════════════════════════════════════

def _negotiate_coeff(asking: float, market: str, location: str) -> float:
    """
    يحسب معامل التفاوض بناءً على:
      - حجم الصفقة (صفقات كبيرة = هامش أكبر)
      - السوق (مصر vs السعودية)
      - المنطقة (مناطق ساخنة = هامش أضيق)
    """
    base = NEG_MID

    # Larger transactions → slightly higher negotiation room
    if asking > 5_000_000:
        base += 0.01
    elif asking < 500_000:
        base -= 0.01

    # KSA market historically has tighter margins
    if market == MARKET_KSA:
        base -= 0.015

    # Hot zones have tighter margins
    hot_zones = {"العاصمة الإدارية", "رأس الحكمة", "التجمع الخامس", "الرياض"}
    if any(z in location for z in hot_zones):
        base -= 0.01

    return max(NEG_LOW, min(NEG_HIGH, base))


def _record_confidence(price: float, area: Optional[float], loc: str) -> float:
    score = 0.5
    if price and price > 0:            score += 0.2
    if area and area > 0:              score += 0.2
    if loc and len(loc) > 3:           score += 0.1
    return round(min(score, 1.0), 2)


# ══════════════════════════════════════════════════════════════════════════════
#  Trend Analyser (DuckDuckGo Lite news scraping — no API key needed)
# ══════════════════════════════════════════════════════════════════════════════

class TrendAnalyser:
    """يرصد آخر الأخبار الاقتصادية المؤثرة على العقار."""

    _DDG_LITE = "https://lite.duckduckgo.com/lite/"

    def __init__(self, session: Optional[Any] = None):
        self._sess = session or _make_session()

    def fetch_trends(self, market: str, location: str) -> List[TrendSignal]:
        if not _REQUESTS_OK or not _BS4_OK:
            return []
        signals: List[TrendSignal] = []
        mkt_queries = {
            MARKET_EG:  ["سعر الفائدة مصر", "أسعار مواد البناء مصر",
                         "سعر الدولار مصر", f"أسعار العقارات {location}"],
            MARKET_KSA: ["سعر الفائدة السعودية", "أسعار مواد البناء السعودية",
                         "سعر الريال الدولار", f"أسعار العقارات {location} السعودية"],
        }
        queries = mkt_queries.get(market, mkt_queries[MARKET_EG])
        categories = ["interest", "materials", "fx", "realestate"]

        for q, cat in zip(queries, categories):
            try:
                sigs = self._search_ddg(q, cat)
                signals.extend(sigs[:2])
                time.sleep(0.4)
            except Exception as exc:
                print(f"  [TrendAnalyser] {cat}: {exc}")

        return signals

    def _search_ddg(self, query: str, category: str) -> List[TrendSignal]:
        signals = []
        try:
            resp = self._sess.post(
                self._DDG_LITE,
                data={"q": query, "kl": "ar-eg"},
                timeout=12,
            )
            soup = BeautifulSoup(resp.text, "html.parser")
            # DuckDuckGo Lite result links are in <a class="result-link">
            for link_el in soup.select("a.result-link, td.result-snippet")[:3]:
                headline = link_el.get_text(" ", strip=True)[:160]
                if not headline:
                    continue
                impact, pct = _classify_impact(headline, category)
                signals.append(TrendSignal(
                    category=category,
                    headline=headline,
                    impact=impact,
                    impact_pct=pct,
                    source="DuckDuckGo News",
                    date=datetime.now().strftime("%Y-%m-%d"),
                ))
        except Exception:
            pass
        return signals


def _classify_impact(headline: str, category: str) -> Tuple[str, Optional[float]]:
    """يُصنِّف الأثر (إيجابي/سلبي/محايد) ونسبة التأثير التقريبية على PPM."""
    h = headline.lower()

    # Keywords that signal price pressure
    pos_keywords = ["ارتفاع", "زيادة", "نمو", "تحسن", "increase", "rise", "growth", "surge"]
    neg_keywords = ["انخفاض", "تراجع", "هبوط", "انكماش", "decrease", "fall", "drop", "decline"]

    pos = any(k in h for k in pos_keywords)
    neg = any(k in h for k in neg_keywords)

    # Impact on real estate PPM depends on category
    if category == "interest":
        # Higher interest → NEGATIVE for real estate (higher financing cost)
        if pos:   return "negative", -3.0
        if neg:   return "positive",  2.0
    elif category == "materials":
        # Higher materials cost → POSITIVE for valuations (replacement cost ↑)
        if pos:   return "positive",  2.5
        if neg:   return "neutral",  None
    elif category == "fx":
        # Weaker local currency → higher construction cost → POSITIVE for PPM
        if pos and "دولار" in h: return "positive", 3.0
        if neg:   return "neutral",  None
    elif category == "realestate":
        if pos:   return "positive",  5.0
        if neg:   return "negative", -4.0

    return "neutral", None


# ══════════════════════════════════════════════════════════════════════════════
#  Summary & Analytics Generator
# ══════════════════════════════════════════════════════════════════════════════

def _build_summary(records: List[PriceRecord]) -> Dict:
    """يبني ملخصاً إحصائياً من سجلات الأسعار."""
    if not records:
        return {"count": 0}

    ppms   = [r.ppm_asking    for r in records if r.ppm_asking]
    prices = [r.asking_price  for r in records if r.asking_price]
    execs  = [r.execution_price for r in records if r.execution_price]

    def _safe_avg(lst): return round(sum(lst) / len(lst), 0) if lst else None
    def _safe_med(lst):
        s = sorted(lst)
        n = len(s)
        return round((s[n//2 - 1] + s[n//2]) / 2 if n % 2 == 0 else s[n//2], 0) if s else None

    currency = records[0].currency if records else "EGP"
    return {
        "count":              len(records),
        "currency":           currency,
        "avg_ppm_asking":     _safe_avg(ppms),
        "median_ppm_asking":  _safe_med(ppms),
        "min_ppm":            round(min(ppms), 0)   if ppms else None,
        "max_ppm":            round(max(ppms), 0)   if ppms else None,
        "avg_asking_price":   _safe_avg(prices),
        "avg_execution_price":_safe_avg(execs),
        "avg_neg_pct":        round(sum(r.negotiation_pct for r in records) / len(records), 1),
        "sources":            list({r.source for r in records}),
        "locations":          list({r.location for r in records})[:8],
        "as_of":              datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def _build_analysis_text(
    location: str,
    market: str,
    asset_type: str,
    summary: Dict,
    trends: List[TrendSignal],
    records: List[PriceRecord],
) -> str:
    """
    يولِّد تقريراً تحليلياً بأسلوب خبير فئة A (Big-4 FRICS)، باللغة العربية.
    """
    if not summary.get("count"):
        return f"لم يتم العثور على بيانات كافية لمنطقة '{location}' في الوقت الحالي."

    ts          = datetime.now().strftime("%d/%m/%Y %H:%M")
    avg_ppm     = summary.get("avg_ppm_asking")
    med_ppm     = summary.get("median_ppm_asking")
    min_ppm     = summary.get("min_ppm")
    max_ppm     = summary.get("max_ppm")
    avg_ask     = summary.get("avg_asking_price")
    avg_exec    = summary.get("avg_execution_price")
    neg_pct     = summary.get("avg_neg_pct", NEG_MID * 100)
    count       = summary.get("count", 0)
    currency    = summary.get("currency", "EGP")
    srcs        = "، ".join(summary.get("sources", []))

    market_lbl  = "جمهورية مصر العربية" if market == MARKET_EG \
                  else "المملكة العربية السعودية"

    # Trend narrative
    trend_lines = []
    for t in trends[:4]:
        arrow = "↑" if t.impact == "positive" else ("↓" if t.impact == "negative" else "→")
        pct_s = f" ({'+' if t.impact=='positive' else ''}{t.impact_pct:.1f}%)" \
                if t.impact_pct else ""
        trend_lines.append(f"  • {arrow} {t.headline[:120]}{pct_s}")
    trend_block = "\n".join(trend_lines) if trend_lines else "  • لا توجد إشارات اقتصادية جديدة في الوقت الحالي."

    # Location sub-market comparison
    loc_comp = ""
    by_loc: Dict[str, List[float]] = {}
    for r in records:
        if r.ppm_asking:
            by_loc.setdefault(r.location, []).append(r.ppm_asking)
    if by_loc:
        loc_rows = sorted(
            [(loc, round(sum(ppms)/len(ppms), 0)) for loc, ppms in by_loc.items()],
            key=lambda x: -x[1]
        )
        loc_comp = "\nمتوسط سعر المتر حسب الموقع الفرعي:\n"
        loc_comp += "\n".join(f"  • {loc}: {ppm:,.0f} {currency}/م²" for loc, ppm in loc_rows[:5])

    text = f"""══════════════════════════════════════════════════════
تقرير الرصد الآني للسوق — إعداد محرك الذكاء السعيادي
Expert_Smart | Sovereign Price Intelligence Engine
══════════════════════════════════════════════════════
المنطقة:       {location}
نوع الأصل:    {asset_type}
السوق:         {market_lbl}
تاريخ التقرير: {ts}
المصادر:       {srcs}
حجم العينة:   {count} إعلاناً
══════════════════════════════════════════════════════

① مؤشرات الأسعار الحالية
─────────────────────────
  • متوسط سعر الطلب (PPM):   {avg_ppm:>10,.0f} {currency}/م²
  • الوسيط (PPM):             {med_ppm:>10,.0f} {currency}/م²
  • نطاق السوق:               {min_ppm:,.0f} — {max_ppm:,.0f} {currency}/م²
  • متوسط سعر الوحدة (طلب):  {avg_ask:>12,.0f} {currency}
  • سعر التنفيذ المتوقع:      {avg_exec:>12,.0f} {currency}
  • معامل التفاوض التقريبي:   {neg_pct:.1f}%  (هامش {NEG_LOW*100:.0f}–{NEG_HIGH*100:.0f}%)
{loc_comp}

② الإشارات الاقتصادية المؤثرة على التقييم
──────────────────────────────────────────
{trend_block}

③ التقييم التحليلي (خبير فئة A — FRICS/IVS)
─────────────────────────────────────────────
بناءً على العينة المرصودة ({count} إعلاناً) من منطقة {location}، يُلاحظ أن
متوسط سعر المتر المربع يتراوح بين {min_ppm:,.0f} و{max_ppm:,.0f} {currency}/م²
بمتوسط مرجَّح يبلغ {avg_ppm:,.0f} {currency}/م².

تحليل التقارب: الفارق بين سعر الطلب وسعر التنفيذ يبلغ تقريباً {neg_pct:.1f}%،
وهو ما يُترجم إلى هامش تفاوضي حقيقي يتراوح بين
{avg_ask*(1-NEG_HIGH):,.0f} و{avg_ask*(1-NEG_LOW):,.0f} {currency} لمتوسط الوحدة.

الاتجاه قصير الأمد: استناداً إلى الإشارات الاقتصادية الواردة أعلاه، يُرجَّح
{'استمرار الضغط الصعودي على الأسعار' if any(t.impact=='positive' for t in trends) else 'استقرار الأسعار مع ميل للانخفاض الطفيف'}
خلال الأشهر الثلاثة القادمة، مع الأخذ بعين الاعتبار تأثير سياسات أسعار الفائدة
وتقلبات أسعار مواد البناء.

إخلاء مسؤولية: هذا تقرير رصد آلي استرشادي لا يُغني عن تقرير تقييم رسمي وفق
معايير IVS/RICS وتشريعات السوق المحلي.
══════════════════════════════════════════════════════"""

    return text


# ══════════════════════════════════════════════════════════════════════════════
#  Excel Table Formatter
# ══════════════════════════════════════════════════════════════════════════════

def build_excel_table(records: List[PriceRecord], summary: Dict) -> List[Dict]:
    """
    يُحوِّل سجلات الأسعار إلى قائمة من القواميس
    جاهزة للحقن في شيت الإكسيل عبر openpyxl.

    الأعمدة (16 عموداً):
      # | الموقع | نوع الأصل | المساحة | سعر الطلب | سعر التنفيذ |
      سعر المتر (طلب) | سعر المتر (تنفيذ) | معامل التفاوض% |
      العملة | المصدر | تاريخ الرصد | الرابط | الثقة |
      متوسط PPM (المنطقة) | ملاحظات
    """
    avg_ppm = summary.get("avg_ppm_asking", 0) or 0
    rows = []
    for i, r in enumerate(records, 1):
        delta_pct = None
        if r.ppm_asking and avg_ppm:
            delta_pct = round((r.ppm_asking - avg_ppm) / avg_ppm * 100, 1)

        rows.append({
            "#":                      i,
            "الموقع":                 r.location,
            "نوع الأصل":              r.asset_type,
            "المساحة (م²)":           r.area_m2,
            "سعر الطلب":              r.asking_price,
            "سعر التنفيذ المتوقع":    r.execution_price,
            "سعر المتر — طلب":        r.ppm_asking,
            "سعر المتر — تنفيذ":      r.ppm_execution,
            "معامل التفاوض %":        r.negotiation_pct,
            "العملة":                 r.currency,
            "المصدر":                 r.source,
            "تاريخ الرصد":            r.scraped_at,
            "الرابط":                 r.url,
            "نسبة الثقة":             r.confidence,
            "انحراف عن المتوسط %":    delta_pct,
            "ملاحظات":                "",
        })

    # Add summary footer row
    if records:
        rows.append({
            "#":                      "المتوسط",
            "الموقع":                 summary.get("locations", [""])[0],
            "نوع الأصل":              records[0].asset_type if records else "",
            "المساحة (م²)":           None,
            "سعر الطلب":              summary.get("avg_asking_price"),
            "سعر التنفيذ المتوقع":    summary.get("avg_execution_price"),
            "سعر المتر — طلب":        summary.get("avg_ppm_asking"),
            "سعر المتر — تنفيذ":      None,
            "معامل التفاوض %":        summary.get("avg_neg_pct"),
            "العملة":                 summary.get("currency", "EGP"),
            "المصدر":                 "متعددة",
            "تاريخ الرصد":            summary.get("as_of"),
            "الرابط":                 "",
            "نسبة الثقة":             None,
            "انحراف عن المتوسط %":    0.0,
            "ملاحظات":                f"عينة: {summary.get('count',0)} إعلان",
        })

    return rows


# ══════════════════════════════════════════════════════════════════════════════
#  TTL Cache (thread-safe)
# ══════════════════════════════════════════════════════════════════════════════

class _TTLCache:
    def __init__(self, ttl_seconds: int = 1800):
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._lock  = threading.Lock()
        self._ttl   = ttl_seconds

    def _key(self, **kwargs) -> str:
        return hashlib.md5(json.dumps(kwargs, sort_keys=True, ensure_ascii=False)
                           .encode()).hexdigest()[:16]

    def get(self, **kwargs) -> Optional[Any]:
        k = self._key(**kwargs)
        with self._lock:
            if k in self._store:
                ts, val = self._store[k]
                if time.time() - ts < self._ttl:
                    return val
                del self._store[k]
        return None

    def set(self, value: Any, **kwargs):
        k = self._key(**kwargs)
        with self._lock:
            self._store[k] = (time.time(), value)

    def clear(self):
        with self._lock:
            self._store.clear()


# ══════════════════════════════════════════════════════════════════════════════
#  Main Intelligence Engine (public API)
# ══════════════════════════════════════════════════════════════════════════════

class PriceIntelligenceEngine:
    """
    المحرك الرئيسي لبروتوكول الرصد اللحظي للأسعار.
    يُنسِّق بين: Scraper → TrendAnalyser → Summary → ExcelTable → AnalysisText
    """

    def __init__(self):
        self._sess    = _make_session()
        self._scraper = PriceScraper(self._sess)
        self._trends  = TrendAnalyser(self._sess)
        self._cache   = _TTLCache(ttl_seconds=1800)   # 30-min cache

    def search(
        self,
        location:   str,
        market:     str = MARKET_EG,
        asset_type: str = "شقة",
        max_items:  int = 20,
        force:      bool = False,
    ) -> MarketIntelligenceReport:
        """
        البحث الكامل: جمع أسعار + تحليل اتجاه + تقرير.

        Args:
            location:   المنطقة / الحي (مثل: التجمع الخامس)
            market:     MARKET_EG أو MARKET_KSA
            asset_type: نوع الأصل (شقة، فيلا، أرض ...)
            max_items:  أقصى عدد سجلات من كل مصدر
            force:      تجاهل الكاش وإعادة الجلب
        """
        if not force:
            cached = self._cache.get(
                location=location, market=market, asset_type=asset_type
            )
            if cached:
                return cached

        # 1. Scrape all matching sources
        records: List[PriceRecord] = []
        for cfg in _SOURCES:
            if cfg.market != market:
                continue
            try:
                recs = self._scraper.scrape_source(cfg, location, asset_type, max_items)
                records.extend(recs)
                print(f"  [PI:{cfg.name}] {len(recs)} سجل من {location}")
            except Exception as exc:
                print(f"  [PI:{cfg.name}] خطأ: {exc}")

        # Sort by confidence descending
        records.sort(key=lambda r: r.confidence, reverse=True)

        # 2. Fetch trend signals
        trends = self._trends.fetch_trends(market, location)

        # 3. Build summary
        summary = _build_summary(records)

        # 4. Generate analysis text
        analysis = _build_analysis_text(
            location, market, asset_type, summary, trends, records
        )

        # 5. Build Excel table
        excel_rows = build_excel_table(records, summary)

        report = MarketIntelligenceReport(
            query_location=location,
            query_market=market,
            query_asset=asset_type,
            generated_at=datetime.now().isoformat(),
            records=records,
            trends=trends,
            summary=summary,
            analysis_text=analysis,
            excel_table=excel_rows,
            data_sources=[cfg.name for cfg in _SOURCES if cfg.market == market],
        )

        self._cache.set(report, location=location, market=market, asset_type=asset_type)
        return report

    def search_dict(self, **kwargs) -> Dict:
        """نسخة dict من search() لسهولة الإرسال عبر JSON."""
        r = self.search(**kwargs)
        return {
            "status":         "success",
            "query_location": r.query_location,
            "query_market":   r.query_market,
            "query_asset":    r.query_asset,
            "generated_at":   r.generated_at,
            "summary":        r.summary,
            "analysis_text":  r.analysis_text,
            "excel_table":    r.excel_table,
            "records":        [rec.to_dict() for rec in r.records],
            "trends": [
                {
                    "category":   t.category,
                    "headline":   t.headline,
                    "impact":     t.impact,
                    "impact_pct": t.impact_pct,
                    "source":     t.source,
                    "date":       t.date,
                }
                for t in r.trends
            ],
            "data_sources":   r.data_sources,
        }

    def quick_trend(self, market: str = MARKET_EG, location: str = "") -> List[Dict]:
        """جلب إشارات الاتجاه فقط (أسرع — بدون scraping الأسعار)."""
        signals = self._trends.fetch_trends(market, location)
        return [
            {
                "category":   s.category,
                "headline":   s.headline,
                "impact":     s.impact,
                "impact_pct": s.impact_pct,
                "source":     s.source,
                "date":       s.date,
            }
            for s in signals
        ]

    def clear_cache(self):
        self._cache.clear()
        return {"status": "cache_cleared"}


# ── Singleton ────────────────────────────────────────────────────────────────
price_intel = PriceIntelligenceEngine()
"""
استخدم هذا المُصدَّر الوحيد في bridge_api.py:
  from price_intelligence import price_intel
"""
