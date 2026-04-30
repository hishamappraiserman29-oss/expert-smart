# -*- coding: utf-8 -*-
"""
market_radar.py — Expert_Smart v37 Market Pulse Engine
=======================================================
محرك رادار السوق العقاري الآلي — يرصد لحظة بلحظة

Components:
  ArabicREParser    — Arabic real-estate text → structured record
  WebRadar          — Aqarmap / Bayut / OLX Egypt scraper (Playwright)
  WhatsAppRadar     — WhatsApp Web group monitor (Playwright)
  MarketDatabase    — SQLite persistent store
  RadarEngine       — Background daemon orchestrator
  RadarAPI          — Clean interface for bridge_api.py

Usage (in bridge_api.py):
  from market_radar import radar_api
  radar_api.start()
  status = radar_api.status()
  records = radar_api.get_records(limit=100)
"""

import re
import json
import math
import uuid
import time
import sqlite3
import threading
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# ── Database path ─────────────────────────────────────────────────────────────
_DB_PATH = Path(__file__).parent / "market_radar.db"

# ── Source identifiers ────────────────────────────────────────────────────────
SRC_WHATSAPP = "whatsapp"
SRC_AQARMAP  = "aqarmap"
SRC_BAYUT    = "bayut"
SRC_OLX      = "olx"
SRC_MANUAL   = "manual"
# Saudi Arabia sources
SRC_AQAR_SA  = "aqar_sa"      # sa.aqar.fm
SRC_EJAR     = "ejar"         # ejar.sa (إيجار)
SRC_MOJ_KSA  = "moj_ksa"     # وزارة العدل — مؤشرات عقارية
SRC_REGA     = "rega"         # الهيئة العامة للعقار


# ══════════════════════════════════════════════════════════════════════════════
#  Arabic Real-Estate Text Parser
# ══════════════════════════════════════════════════════════════════════════════

class ArabicREParser:
    """
    يحوّل رسائل عقارية غير منظَّمة (عربية/مختلطة) إلى سجلات منظَّمة.

    مثال:
      Input:  "شقة لقطة تانى نمرة 120م بـ 3 مليون في التجمع"
      Output: {"asset_type":"شقة","area":120,"price":3_000_000,
               "ppm":25_000,"location":"التجمع","source_text":"..."}
    """

    # ── Asset-type keywords ──────────────────────────────────────────────────
    _ASSET_MAP = {
        "شقة":          "شقة",    "شقه":        "شقة",    "دور":       "دور",
        "فيلا":         "فيلا",   "فلة":         "فيلا",   "تاون هاوس":"تاون هاوس",
        "دوبلكس":       "دوبلكس", "بنتهاوس":    "بنتهاوس","روف":       "روف",
        "محل":          "محل",    "مكتب":        "مكتب",   "عيادة":     "عيادة",
        "أرض":          "أرض",    "ارض":         "أرض",    "قطعة أرض": "أرض",
        "مستودع":       "مستودع", "مخزن":        "مخزن",   "مصنع":      "مصنع",
        "فندق":         "فندق",   "شاليه":       "شاليه",  "استوديو":   "استوديو",
        "مدرسة":        "مدرسة",  "مستشفى":      "مستشفى", "عمارة":     "عمارة",
    }

    # ── Price multipliers ────────────────────────────────────────────────────
    _MULTIPLIERS = {
        "مليار": 1_000_000_000,
        "مليون": 1_000_000,
        "ألف":   1_000,
        "الف":   1_000,
    }

    # ── Egyptian/Saudi location hints ────────────────────────────────────────
    _LOCATION_HINTS = [
        "التجمع", "مدينة نصر", "المهندسين", "الزمالك", "العجوزة", "الدقي",
        "الشيخ زايد", "أكتوبر", "6 أكتوبر", "العبور", "القاهرة الجديدة",
        "بدر", "المقطم", "حلوان", "المعادي", "المنيل", "إمبابة",
        "رأس الحكمة", "العلمين", "مرسى مطروح", "الإسكندرية", "الغردقة",
        "أسوان", "الأقصر", "أسيوط", "المنيا", "بني سويف", "الفيوم",
        "دمياط", "المنصورة", "طنطا", "الزقازيق", "الإسماعيلية", "بورسعيد",
        "السويس", "شرم الشيخ", "الغردقة", "رأس غارب",
        "العاصمة الإدارية", "المنتزه", "الجليم", "سيدي جابر",
        # Saudi Arabia — المناطق والأحياء
        "الرياض", "جدة", "مكة", "المدينة المنورة", "الدمام", "الخبر",
        "أبها", "تبوك", "حائل", "نجران", "جازان", "القصيم", "عرعر",
        "الجبيل", "ينبع", "الطائف", "خميس مشيط", "بريدة", "عنيزة",
        # Riyadh districts (أحياء الرياض)
        "النرجس", "العارض", "الملقا", "حي الملك فهد", "الربوة",
        "العليا", "الروضة", "الورود", "المروج", "الغدير",
        "الوادي", "الصحافة", "الياسمين", "الرمال", "النسيم",
        # Jeddah districts (أحياء جدة)
        "السلامة", "الزهراء", "الروضة", "أبحر", "الشاطئ",
        "الواجهة البحرية", "حي الحمراء", "الاندلس", "الفيصلية",
    ]

    # ── Transaction type ─────────────────────────────────────────────────────
    _TRANSACTION_TYPES = {
        "للبيع": "sale", "بيع": "sale", "تمليك": "sale",
        "للإيجار": "rent", "ايجار": "rent", "إيجار": "rent",
        "للإيجار السنوي": "rent", "شهري": "rent_monthly",
    }

    def parse(self, text: str) -> Optional[Dict]:
        """يحوّل نص حر → سجل عقاري. يُعيد None إذا لم يجد بيانات كافية."""
        if not text or len(text.strip()) < 10:
            return None
        text = text.strip()

        asset_type   = self._extract_asset_type(text)
        price        = self._extract_price(text)
        area         = self._extract_area(text)
        location     = self._extract_location(text)
        tx_type      = self._extract_tx_type(text)
        rooms        = self._extract_rooms(text)
        floor_info   = self._extract_floor(text)

        # Require at minimum a price or an area
        if price is None and area is None:
            return None

        ppm = round(price / area, 1) if price and area and area > 0 else None

        return {
            "id":           str(uuid.uuid4()),
            "asset_type":   asset_type or "غير محدد",
            "price":        price,
            "area":         area,
            "ppm":          ppm,
            "location":     location or "غير محدد",
            "tx_type":      tx_type,
            "rooms":        rooms,
            "floor":        floor_info,
            "source_text":  text[:500],
            "confidence":   self._confidence(price, area, location, asset_type),
            "parsed_at":    datetime.now().isoformat(),
        }

    # ── Private extractors ───────────────────────────────────────────────────

    def _extract_asset_type(self, text: str) -> Optional[str]:
        for kw, normalized in self._ASSET_MAP.items():
            if kw in text:
                return normalized
        return None

    def _extract_price(self, text: str) -> Optional[float]:
        # Pattern: رقم + وحدة (مليون / ألف / مليار)
        # e.g. "3 مليون", "٣.٥ مليون", "350 ألف", "2.5M"
        text_norm = self._normalize_arabic_nums(text)

        for unit_ar, mult in self._MULTIPLIERS.items():
            pat = rf"(\d+(?:[.,]\d+)?)\s*{unit_ar}"
            m = re.search(pat, text_norm)
            if m:
                try:
                    val = float(m.group(1).replace(",", "."))
                    return val * mult
                except ValueError:
                    continue

        # Plain number (likely total EGP) — only if ≥ 5 digits
        m = re.search(r"(\d{5,})", text_norm.replace(",", "").replace("،", ""))
        if m:
            try:
                val = float(m.group(1))
                if 50_000 <= val <= 500_000_000:
                    return val
            except ValueError:
                pass
        return None

    def _extract_area(self, text: str) -> Optional[float]:
        text_norm = self._normalize_arabic_nums(text)
        # Patterns: "120 م", "120م²", "120 متر", "120 sqm"
        patterns = [
            r"(\d+(?:[.,]\d+)?)\s*م(?:²|2|تر)?(?:\s|$|[^ا-ي])",
            r"(\d+(?:[.,]\d+)?)\s*متر",
            r"(\d+(?:[.,]\d+)?)\s*sqm",
            r"(\d+(?:[.,]\d+)?)\s*m²",
        ]
        for pat in patterns:
            m = re.search(pat, text_norm, re.IGNORECASE)
            if m:
                try:
                    val = float(m.group(1).replace(",", "."))
                    if 10 <= val <= 50_000:
                        return val
                except ValueError:
                    continue
        return None

    def _extract_location(self, text: str) -> Optional[str]:
        for loc in self._LOCATION_HINTS:
            if loc in text:
                return loc
        # Fallback: look for "في <name>" pattern
        m = re.search(r"في\s+([\u0600-\u06FF\s]{3,20})", text)
        if m:
            candidate = m.group(1).strip()
            if 3 < len(candidate) < 25:
                return candidate
        return None

    def _extract_tx_type(self, text: str) -> str:
        for kw, tx in self._TRANSACTION_TYPES.items():
            if kw in text:
                return tx
        return "sale"  # default assumption

    def _extract_rooms(self, text: str) -> Optional[int]:
        text_norm = self._normalize_arabic_nums(text)
        m = re.search(r"(\d)\s*(?:غرف|أوضة|أوض|غرفة)", text_norm)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
        return None

    def _extract_floor(self, text: str) -> Optional[str]:
        text_norm = self._normalize_arabic_nums(text)
        m = re.search(r"(?:الدور|طابق|دور)\s*(?:ال)?(\d+|أرضي|أول|ثاني|ثالث|رابع|خامس)", text_norm)
        if m:
            return m.group(1)
        return None

    @staticmethod
    def _normalize_arabic_nums(text: str) -> str:
        """يُحوِّل الأرقام العربية/الفارسية إلى ASCII"""
        ar_digits = "٠١٢٣٤٥٦٧٨٩"
        fa_digits = "۰۱۲۳۴۵۶۷۸۹"
        for i, (ar, fa) in enumerate(zip(ar_digits, fa_digits)):
            text = text.replace(ar, str(i)).replace(fa, str(i))
        return text

    def _confidence(self, price, area, location, asset_type) -> float:
        score = 0.0
        if price:    score += 0.35
        if area:     score += 0.30
        if location: score += 0.20
        if asset_type and asset_type != "غير محدد": score += 0.15
        return round(score, 2)


# ══════════════════════════════════════════════════════════════════════════════
#  SQLite Market Database
# ══════════════════════════════════════════════════════════════════════════════

class MarketDatabase:
    """
    تخزين سجلات السوق في SQLite.
    Thread-safe من خلال threading.local للاتصالات.
    """
    _local = threading.local()

    def __init__(self, db_path: Path = _DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        if not getattr(self._local, "conn", None):
            self._local.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS market_records (
                id          TEXT PRIMARY KEY,
                asset_type  TEXT,
                price       REAL,
                area        REAL,
                ppm         REAL,
                location    TEXT,
                tx_type     TEXT DEFAULT 'sale',
                rooms       INTEGER,
                floor       TEXT,
                source      TEXT,
                source_text TEXT,
                confidence  REAL DEFAULT 0.0,
                parsed_at   TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_location ON market_records(location)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_asset   ON market_records(asset_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_created ON market_records(created_at)")
        conn.commit()
        conn.close()

    def insert(self, record: Dict, source: str = SRC_MANUAL) -> bool:
        try:
            self._conn().execute("""
                INSERT OR IGNORE INTO market_records
                  (id, asset_type, price, area, ppm, location, tx_type,
                   rooms, floor, source, source_text, confidence, parsed_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                record.get("id", str(uuid.uuid4())),
                record.get("asset_type"),
                record.get("price"),
                record.get("area"),
                record.get("ppm"),
                record.get("location"),
                record.get("tx_type", "sale"),
                record.get("rooms"),
                record.get("floor"),
                source,
                record.get("source_text", "")[:1000],
                record.get("confidence", 0),
                record.get("parsed_at", datetime.now().isoformat()),
            ))
            self._conn().commit()
            return True
        except Exception:
            return False

    def query(
        self,
        location:   Optional[str] = None,
        asset_type: Optional[str] = None,
        source:     Optional[str] = None,
        min_conf:   float = 0.3,
        hours_back: Optional[int] = None,
        limit:      int   = 200,
        offset:     int   = 0,
    ) -> List[Dict]:
        conditions, params = ["confidence >= ?"], [min_conf]
        if location:
            conditions.append("location LIKE ?"); params.append(f"%{location}%")
        if asset_type:
            conditions.append("asset_type = ?"); params.append(asset_type)
        if source:
            conditions.append("source = ?"); params.append(source)
        if hours_back:
            cutoff = (datetime.now() - timedelta(hours=hours_back)).isoformat()
            conditions.append("created_at >= ?"); params.append(cutoff)
        where = " AND ".join(conditions)
        params += [limit, offset]
        cur = self._conn().execute(
            f"SELECT * FROM market_records WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params
        )
        return [dict(row) for row in cur.fetchall()]

    def stats(self) -> Dict:
        cur = self._conn().execute("""
            SELECT
                COUNT(*) as total,
                COUNT(DISTINCT location) as locations,
                COUNT(DISTINCT asset_type) as asset_types,
                AVG(ppm) as avg_ppm,
                MIN(created_at) as oldest,
                MAX(created_at) as newest,
                COUNT(CASE WHEN source='whatsapp' THEN 1 END) as from_whatsapp,
                COUNT(CASE WHEN source IN ('aqarmap','bayut','olx') THEN 1 END) as from_web
            FROM market_records WHERE confidence >= 0.3
        """)
        row = dict(cur.fetchone())
        row["avg_ppm"] = round(row["avg_ppm"] or 0, 1)
        return row

    def ppm_by_location(self, location: str = "", asset_type: str = "شقة") -> List[Dict]:
        """متوسط PPM مُجمَّع حسب الموقع لخريطة الأسعار (heatmap)"""
        cond = "confidence >= 0.3 AND ppm IS NOT NULL AND ppm > 0"
        params = []
        if location:
            cond += " AND location LIKE ?"; params.append(f"%{location}%")
        if asset_type:
            cond += " AND asset_type = ?"; params.append(asset_type)
        cur = self._conn().execute(f"""
            SELECT location,
                   AVG(ppm) as avg_ppm,
                   MIN(ppm) as min_ppm,
                   MAX(ppm) as max_ppm,
                   COUNT(*) as count
            FROM market_records WHERE {cond}
            GROUP BY location HAVING count >= 2
            ORDER BY avg_ppm DESC
        """, params)
        return [dict(row) for row in cur.fetchall()]

    def delete_old(self, days: int = 90) -> int:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        cur = self._conn().execute("DELETE FROM market_records WHERE created_at < ?", (cutoff,))
        self._conn().commit()
        return cur.rowcount


# ══════════════════════════════════════════════════════════════════════════════
#  Web Radar — Playwright-based scrapers
# ══════════════════════════════════════════════════════════════════════════════

class WebRadar:
    """
    يرصد مواقع العقارات المصرية والخليجية بشكل دوري.
    يعمل بـ Playwright (async → sync wrapper).
    """

    SOURCES = {
        # ─── Egypt ──────────────────────────────────────────────────────────
        SRC_AQARMAP: {
            "url": "https://aqarmap.com.eg/ar/for-sale/",
            "card_selector":  ".listing-card",
            "price_selector": ".listing-price",
            "area_selector":  ".listing-area",
            "loc_selector":   ".listing-location",
            "type_selector":  ".listing-type",
            "market": "egypt",
        },
        SRC_BAYUT: {
            "url": "https://www.bayut.eg/buy/",
            "card_selector":  "[data-testid='property-card']",
            "price_selector": "[data-testid='price']",
            "area_selector":  "[aria-label='Area']",
            "loc_selector":   "[aria-label='Location Breadcrumb']",
            "type_selector":  "[data-testid='property-type']",
            "market": "egypt",
        },
        SRC_OLX: {
            "url": "https://www.olx.com.eg/en/real-estate/",
            "card_selector":  ".EIR5N",
            "price_selector": ".evh5a3",
            "area_selector":  None,
            "loc_selector":   "._57kEY",
            "type_selector":  None,
            "market": "egypt",
        },
        # ─── Saudi Arabia ────────────────────────────────────────────────────
        SRC_AQAR_SA: {
            "url": "https://sa.aqar.fm/%D8%B4%D9%82%D9%82/for-sale",
            "card_selector":  ".item-card, [class*='ItemCard']",
            "price_selector": ".item-price, [class*='Price']",
            "area_selector":  "[class*='area'], [class*='Area']",
            "loc_selector":   "[class*='location'], [class*='Location']",
            "type_selector":  "[class*='type']",
            "market": "ksa",
        },
        SRC_EJAR: {
            "url": "https://www.ejar.sa/en/search?type=sale&propertyType=apartment",
            "card_selector":  ".property-card, [class*='PropertyCard']",
            "price_selector": "[class*='price'], [class*='Price']",
            "area_selector":  "[class*='area'], [class*='Area']",
            "loc_selector":   "[class*='location'], [class*='Location']",
            "type_selector":  None,
            "market": "ksa",
        },
        SRC_MOJ_KSA: {
            "url": "https://www.moj.gov.sa/ar/RealEstate/Pages/RealEstateIndicators.aspx",
            "card_selector":  "tr, .indicator-row",
            "price_selector": "td:nth-child(4), .price-col",
            "area_selector":  "td:nth-child(3), .area-col",
            "loc_selector":   "td:nth-child(2), .loc-col",
            "type_selector":  "td:nth-child(1)",
            "market": "ksa",
        },
        SRC_REGA: {
            "url": "https://www.rega.gov.sa/ar/real-estate-market",
            "card_selector":  ".market-item, .stat-card",
            "price_selector": ".price-value, .stat-value",
            "area_selector":  None,
            "loc_selector":   ".location-name, .region-name",
            "type_selector":  None,
            "market": "ksa",
        },
    }

    def __init__(self, db: MarketDatabase, parser: ArabicREParser):
        self.db     = db
        self.parser = parser
        self._total = 0

    def scrape_all(self, max_per_source: int = 50) -> Dict:
        """يجري scraping لكل مصدر ويُعيد ملخص."""
        results = {}
        for src_name in self.SOURCES:
            try:
                count = self._scrape_source(src_name, max_per_source)
                results[src_name] = {"status": "ok", "inserted": count}
                self._total += count
            except Exception as e:
                results[src_name] = {"status": "error", "message": str(e)[:120]}
        return results

    def _scrape_source(self, src_name: str, max_items: int) -> int:
        """يحاول الـ scraping ويُعيد عدد السجلات المُدرجة."""
        cfg = self.SOURCES[src_name]
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError("Playwright غير مثبَّت — pip install playwright && playwright install chromium")

        inserted = 0
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            ctx     = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                locale="ar-EG",
            )
            page = ctx.new_page()
            try:
                page.goto(cfg["url"], timeout=30_000, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
                cards = page.query_selector_all(cfg["card_selector"])[:max_items]
                for card in cards:
                    raw = self._extract_card_text(card, cfg)
                    rec = self.parser.parse(raw)
                    if rec and rec["confidence"] >= 0.3:
                        if self.db.insert(rec, source=src_name):
                            inserted += 1
            except Exception:
                pass
            finally:
                ctx.close()
                browser.close()
        return inserted

    @staticmethod
    def _extract_card_text(card, cfg: Dict) -> str:
        parts = []
        for key in ("type_selector", "loc_selector", "area_selector", "price_selector"):
            sel = cfg.get(key)
            if sel:
                try:
                    el = card.query_selector(sel)
                    if el:
                        parts.append(el.inner_text().strip())
                except Exception:
                    pass
        if not parts:
            parts.append(card.inner_text()[:300])
        return " ".join(parts)


# ══════════════════════════════════════════════════════════════════════════════
#  WhatsApp Radar — WhatsApp Web group monitor
# ══════════════════════════════════════════════════════════════════════════════

class WhatsAppRadar:
    """
    يراقب مجموعات واتساب عبر واتساب Web.
    يتطلب:
      1. مسح QR أول مرة (يُحفظ الـ session لاحقاً)
      2. اسم المجموعة المُستهدفة
    """

    _SESSION_DIR = Path(__file__).parent / ".whatsapp_session"

    def __init__(self, db: MarketDatabase, parser: ArabicREParser):
        self.db         = db
        self.parser     = parser
        self._groups:   List[str] = []
        self._inserted  = 0
        self._status    = "idle"
        self._qr_needed = False

    def set_target_groups(self, group_names: List[str]):
        self._groups = group_names

    def scan_once(self, group_name: str, max_messages: int = 100) -> Dict:
        """
        يسجل الدخول إلى واتساب Web، يفتح مجموعة،
        يقرأ آخر max_messages رسالة، ويُحلِّل العقارية منها.
        يُعيد: {"inserted": N, "parsed": M, "status": "..."}
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return {"status": "error", "message": "Playwright غير مثبَّت"}

        self._SESSION_DIR.mkdir(exist_ok=True)
        self._status = "connecting"
        inserted = parsed = 0

        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                str(self._SESSION_DIR),
                headless=False,       # WhatsApp Web يرفض headless=True أحياناً
                args=["--no-sandbox"],
            )
            page = browser.pages[0] if browser.pages else browser.new_page()
            try:
                page.goto("https://web.whatsapp.com", timeout=60_000)
                # انتظر تحميل الشاشة الرئيسية أو مربع QR
                qr_sel   = "canvas[aria-label='Scan me!']"
                main_sel = "#app .app-wrapper-web"

                try:
                    page.wait_for_selector(f"{qr_sel}, {main_sel}", timeout=30_000)
                except Exception:
                    return {"status": "timeout", "message": "انتهت المهلة — لم يُحمَّل واتساب Web"}

                if page.is_visible(qr_sel):
                    self._qr_needed = True
                    self._status = "qr_required"
                    return {"status": "qr_required",
                            "message": "افتح واتساب على هاتفك وامسح رمز QR ثم أعِد المحاولة"}

                self._qr_needed = False
                self._status = "scanning"

                # ابحث عن المجموعة
                page.click("[data-testid='search']", timeout=5_000)
                page.fill("[data-testid='search']", group_name, timeout=5_000)
                page.wait_for_timeout(1500)
                try:
                    page.click(f"[title='{group_name}']", timeout=5_000)
                except Exception:
                    # اضغط على أول نتيجة
                    try:
                        page.click("[data-testid='cell-frame-container']", timeout=3_000)
                    except Exception:
                        return {"status": "group_not_found",
                                "message": f"لم يتم العثور على المجموعة: {group_name}"}

                page.wait_for_timeout(2000)
                msgs = page.query_selector_all("[data-testid='msg-container']")[-max_messages:]
                for msg_el in msgs:
                    try:
                        txt = msg_el.inner_text(timeout=1000).strip()
                        if len(txt) > 15:
                            rec = self.parser.parse(txt)
                            if rec and rec["confidence"] >= 0.35:
                                parsed += 1
                                if self.db.insert(rec, source=SRC_WHATSAPP):
                                    inserted += 1
                    except Exception:
                        continue
            except Exception as e:
                return {"status": "error", "message": str(e)[:200]}
            finally:
                browser.close()

        self._inserted += inserted
        self._status = "idle"
        return {"status": "ok", "inserted": inserted, "parsed": parsed,
                "group": group_name}


# ══════════════════════════════════════════════════════════════════════════════
#  Radar Engine — Background Daemon
# ══════════════════════════════════════════════════════════════════════════════

class RadarEngine:
    """
    المحرك الرئيسي — يُدير دورات المراقبة في خيط خلفي.
    """

    def __init__(self):
        self._db          = MarketDatabase()
        self._parser      = ArabicREParser()
        self._web         = WebRadar(self._db, self._parser)
        self._wa          = WhatsAppRadar(self._db, self._parser)
        self._thread:     Optional[threading.Thread] = None
        self._stop_event  = threading.Event()
        self._running     = False
        self._cycle       = 0
        self._last_run    = None
        self._errors:     List[str] = []
        self._log:        List[str] = []
        self._interval_s  = 1800   # 30 minutes default
        self._modes       = {"web": True, "whatsapp": False}
        self._wa_groups:  List[str] = []

    # ── Public control API ───────────────────────────────────────────────────

    def start(
        self,
        interval_seconds: int = 1800,
        enable_web:       bool = True,
        enable_whatsapp:  bool = False,
        wa_groups:        Optional[List[str]] = None,
    ):
        if self._running:
            return {"status": "already_running", "cycle": self._cycle}
        self._interval_s  = max(300, interval_seconds)
        self._modes       = {"web": enable_web, "whatsapp": enable_whatsapp}
        self._wa_groups   = wa_groups or []
        self._stop_event.clear()
        self._running     = True
        self._thread      = threading.Thread(
            target=self._loop, daemon=True, name="radar-engine"
        )
        self._thread.start()
        self._log_msg("🚀 رادار السوق بدأ")
        return {"status": "started", "modes": self._modes, "interval_s": self._interval_s}

    def stop(self):
        self._stop_event.set()
        self._running = False
        self._log_msg("🛑 رادار السوق أوقف")
        return {"status": "stopped", "cycles_completed": self._cycle}

    def status(self) -> Dict:
        stats = self._db.stats()
        return {
            "running":        self._running,
            "cycle":          self._cycle,
            "last_run":       self._last_run,
            "interval_s":     self._interval_s,
            "modes":          self._modes,
            "wa_qr_needed":   self._wa._qr_needed,
            "wa_status":      self._wa._status,
            "db_stats":       stats,
            "recent_log":     self._log[-20:],
            "recent_errors":  self._errors[-5:],
        }

    def parse_text(self, text: str) -> Optional[Dict]:
        """يُحلِّل نصاً فردياً ويُخزِّنه."""
        rec = self._parser.parse(text)
        if rec:
            self.insert_manual(rec)
        return rec

    def insert_manual(self, record: Dict) -> bool:
        return self._db.insert(record, source=SRC_MANUAL)

    def get_records(self, **kwargs) -> List[Dict]:
        return self._db.query(**kwargs)

    def get_heatmap_data(self, asset_type: str = "شقة") -> List[Dict]:
        return self._db.ppm_by_location(asset_type=asset_type)

    def get_stats(self) -> Dict:
        return self._db.stats()

    # ── Main loop ────────────────────────────────────────────────────────────

    def _loop(self):
        while not self._stop_event.is_set():
            try:
                self._run_cycle()
            except Exception as e:
                self._errors.append(f"[{_ts()}] {e}")
            finally:
                self._last_run = datetime.now().isoformat()
                self._cycle   += 1
            self._stop_event.wait(timeout=self._interval_s)

    def _run_cycle(self):
        self._log_msg(f"⟳ دورة #{self._cycle + 1} — بدأت")
        if self._modes.get("web"):
            try:
                results = self._web.scrape_all(max_per_source=30)
                total = sum(v.get("inserted", 0) for v in results.values() if isinstance(v, dict))
                self._log_msg(f"🌐 مواقع الويب: {total} سجل جديد")
            except Exception as e:
                self._errors.append(f"[web] {str(e)[:120]}")

        if self._modes.get("whatsapp") and self._wa_groups:
            for grp in self._wa_groups:
                try:
                    res = self._wa.scan_once(grp, max_messages=80)
                    self._log_msg(f"💬 {grp}: {res.get('inserted',0)} سجل")
                except Exception as e:
                    self._errors.append(f"[wa:{grp}] {str(e)[:120]}")

        self._log_msg(f"✅ دورة #{self._cycle + 1} اكتملت")

    def _log_msg(self, msg: str):
        entry = f"[{_ts()}] {msg}"
        self._log.append(entry)
        if len(self._log) > 200:
            self._log = self._log[-100:]
        print(f"  [Radar] {entry}")


def _ts():
    return time.strftime("%H:%M:%S")


# ══════════════════════════════════════════════════════════════════════════════
#  Singleton API — imported by bridge_api.py
# ══════════════════════════════════════════════════════════════════════════════

radar_api = RadarEngine()
"""
استخدم هذا المُصدَّر الوحيد في bridge_api.py:
  from market_radar import radar_api
"""
