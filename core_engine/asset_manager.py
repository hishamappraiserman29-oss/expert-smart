# -*- coding: utf-8 -*-
"""
asset_manager.py — إدارة الأصول الذكية (Smart Asset Management)
Expert_Smart Sovereign Edition

نواة خدمة SaaS لمراقبة الثروة العقارية:
  - تسجيل تقييم العقار وحفظه في قاعدة بيانات SQLite
  - تحديث القيمة دورياً بناءً على التضخم أو price_intelligence
  - تتبع تاريخ القيمة (Value History) لكل عقار
  - حساب أداء المحفظة (Portfolio Performance)
  - توليد تقرير مصغّر للـ Dashboard
"""

from __future__ import annotations
import os
import json
import sqlite3
import threading
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

# ── قاعدة البيانات ──────────────────────────────────────────────────────────
_DB_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(_DB_DIR, exist_ok=True)
_DB_PATH = os.path.join(_DB_DIR, "asset_portfolio.db")

_LOCAL = threading.local()   # thread-safe connections

# ── معدلات التضخم الافتراضية (سنوية) ─────────────────────────────────────
_INFLATION_RATES = {
    "egypt":    0.20,    # 20% سنوياً
    "ksa":      0.04,    # 4%
    "uae":      0.04,
    "default":  0.10,
}


def _get_conn() -> sqlite3.Connection:
    if not getattr(_LOCAL, "conn", None):
        conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        _LOCAL.conn = conn
        _init_schema(conn)
    return _LOCAL.conn


def _init_schema(conn: sqlite3.Connection):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS assets (
        id              TEXT PRIMARY KEY,
        name            TEXT NOT NULL,
        location        TEXT,
        property_type   TEXT,
        area_m2         REAL,
        market          TEXT DEFAULT 'egypt',
        base_value      REAL,
        current_value   REAL,
        currency        TEXT DEFAULT 'EGP',
        owner_ref       TEXT,
        notes           TEXT,
        created_at      TEXT,
        updated_at      TEXT,
        metadata        TEXT
    );

    CREATE TABLE IF NOT EXISTS value_history (
        id              TEXT PRIMARY KEY,
        asset_id        TEXT NOT NULL,
        value           REAL,
        ppm             REAL,
        method          TEXT,
        source          TEXT,
        inflation_rate  REAL,
        recorded_at     TEXT,
        notes           TEXT,
        FOREIGN KEY (asset_id) REFERENCES assets(id)
    );
    """)
    conn.commit()


def _now() -> str:
    return datetime.utcnow().isoformat()


def _row_to_dict(row) -> Dict:
    if row is None:
        return {}
    d = dict(row)
    if d.get("metadata"):
        try:
            d["metadata"] = json.loads(d["metadata"])
        except Exception:
            pass
    return d


# ═══════════════════════════════════════════════════════════════════════════
# CRUD للأصول
# ═══════════════════════════════════════════════════════════════════════════

def register_asset(
    name: str,
    location: str,
    property_type: str,
    area_m2: float,
    base_value: float,
    market: str = "egypt",
    currency: str = "EGP",
    owner_ref: str = "",
    notes: str = "",
    metadata: Optional[Dict] = None,
) -> Dict[str, Any]:
    """يُسجّل عقاراً جديداً في المحفظة."""
    conn = _get_conn()
    asset_id = str(uuid.uuid4())
    ts = _now()
    conn.execute(
        """INSERT INTO assets
           (id, name, location, property_type, area_m2, market,
            base_value, current_value, currency, owner_ref, notes,
            created_at, updated_at, metadata)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (asset_id, name, location, property_type, area_m2, market,
         base_value, base_value, currency, owner_ref, notes,
         ts, ts, json.dumps(metadata or {}))
    )
    # تسجيل القيمة الأولى في السجل التاريخي
    conn.execute(
        """INSERT INTO value_history
           (id, asset_id, value, ppm, method, source, inflation_rate, recorded_at, notes)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (str(uuid.uuid4()), asset_id, base_value,
         round(base_value / area_m2, 2) if area_m2 > 0 else 0,
         "تقييم أولي", "manual", 0.0, ts, "قيمة التسجيل الأولي")
    )
    conn.commit()
    return {"status": "success", "asset_id": asset_id, "message": f"تم تسجيل العقار: {name}"}


def get_asset(asset_id: str) -> Dict[str, Any]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM assets WHERE id=?", (asset_id,)).fetchone()
    if not row:
        return {"status": "error", "message": "العقار غير موجود"}
    asset = _row_to_dict(row)
    history = _get_history(asset_id)
    asset["value_history"] = history
    return asset


def list_assets(market: Optional[str] = None, limit: int = 50) -> List[Dict]:
    conn = _get_conn()
    if market:
        rows = conn.execute(
            "SELECT * FROM assets WHERE market=? ORDER BY updated_at DESC LIMIT ?",
            (market, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM assets ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def _get_history(asset_id: str) -> List[Dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM value_history WHERE asset_id=? ORDER BY recorded_at ASC",
        (asset_id,)
    ).fetchall()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════════════
# تحديث القيمة
# ═══════════════════════════════════════════════════════════════════════════

def update_asset_value(
    asset_id: str,
    new_value: Optional[float] = None,
    method: str = "تحديث يدوي",
    source: str = "manual",
    apply_inflation: bool = False,
    notes: str = "",
) -> Dict[str, Any]:
    """
    يُحدّث قيمة العقار.
    إذا apply_inflation=True ولم يُعطَ new_value يُطبّق معدل التضخم تلقائياً.
    """
    conn = _get_conn()
    row = conn.execute("SELECT * FROM assets WHERE id=?", (asset_id,)).fetchone()
    if not row:
        return {"status": "error", "message": "العقار غير موجود"}
    asset = _row_to_dict(row)

    current = float(asset["current_value"])
    market  = asset.get("market", "egypt")
    area    = float(asset.get("area_m2", 1) or 1)
    infl    = _INFLATION_RATES.get(market, _INFLATION_RATES["default"])

    if new_value:
        updated_value  = float(new_value)
        inflation_rate = round((updated_value - current) / current, 4) if current else 0
    elif apply_inflation:
        updated_value  = round(current * (1 + infl), 2)
        inflation_rate = infl
        method = f"تحديث تضخم سنوي ({infl*100:.1f}%)"
    else:
        return {"status": "error", "message": "يجب تحديد قيمة أو تفعيل apply_inflation"}

    ts = _now()
    conn.execute(
        "UPDATE assets SET current_value=?, updated_at=? WHERE id=?",
        (updated_value, ts, asset_id)
    )
    conn.execute(
        """INSERT INTO value_history
           (id, asset_id, value, ppm, method, source, inflation_rate, recorded_at, notes)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (str(uuid.uuid4()), asset_id, updated_value,
         round(updated_value / area, 2),
         method, source, inflation_rate, ts, notes)
    )
    conn.commit()

    gain     = updated_value - float(asset["base_value"])
    gain_pct = (gain / float(asset["base_value"]) * 100) if asset["base_value"] else 0

    return {
        "status":        "success",
        "asset_id":      asset_id,
        "previous_value": current,
        "new_value":     updated_value,
        "gain_egp":      round(gain, 2),
        "gain_pct":      round(gain_pct, 2),
        "inflation_rate": inflation_rate,
        "updated_at":    ts,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Dashboard المحفظة
# ═══════════════════════════════════════════════════════════════════════════

def portfolio_dashboard(market: Optional[str] = None) -> Dict[str, Any]:
    """يُولّد تقريراً مُلخَّصاً لمحفظة العقارات."""
    assets = list_assets(market=market, limit=200)
    if not assets:
        return {"status": "empty", "message": "لا توجد أصول مُسجَّلة بعد"}

    total_base    = sum(float(a.get("base_value", 0) or 0)    for a in assets)
    total_current = sum(float(a.get("current_value", 0) or 0) for a in assets)
    total_area    = sum(float(a.get("area_m2", 0) or 0)       for a in assets)
    total_gain    = total_current - total_base
    gain_pct      = (total_gain / total_base * 100) if total_base else 0

    # توزيع حسب نوع العقار
    by_type: Dict[str, int] = {}
    for a in assets:
        pt = a.get("property_type", "أخرى") or "أخرى"
        by_type[pt] = by_type.get(pt, 0) + 1

    # أعلى 5 عقارات أداءً
    def _gain(a):
        b = float(a.get("base_value", 1) or 1)
        c = float(a.get("current_value", 0) or 0)
        return (c - b) / b if b else 0

    top5 = sorted(assets, key=_gain, reverse=True)[:5]
    top5_summary = [
        {
            "name":       a.get("name"),
            "location":   a.get("location"),
            "gain_pct":   round(_gain(a) * 100, 1),
            "current_val": a.get("current_value"),
        }
        for a in top5
    ]

    return {
        "status":          "success",
        "total_assets":    len(assets),
        "total_base_value":    round(total_base, 2),
        "total_current_value": round(total_current, 2),
        "total_gain":      round(total_gain, 2),
        "gain_pct":        round(gain_pct, 2),
        "total_area_m2":   round(total_area, 2),
        "avg_ppm":         round(total_current / total_area, 2) if total_area else 0,
        "by_type":         by_type,
        "top_performers":  top5_summary,
        "generated_at":    _now(),
        "currency":        assets[0].get("currency", "EGP") if assets else "EGP",
    }


def delete_asset(asset_id: str) -> Dict[str, Any]:
    conn = _get_conn()
    conn.execute("DELETE FROM value_history WHERE asset_id=?", (asset_id,))
    conn.execute("DELETE FROM assets WHERE id=?", (asset_id,))
    conn.commit()
    return {"status": "success", "message": "تم حذف العقار وسجله التاريخي"}
