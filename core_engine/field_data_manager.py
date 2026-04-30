from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

# ─── Storage ──────────────────────────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FIELD_DB_PATH = os.path.join(_BASE_DIR, "outputs", "field_data.jsonl")

# Source priority scores
SOURCE_PRIORITY = {
    "field_actual": 10,
    "notary_public": 9,
    "broker_oral": 8,
    "site_visit": 7,
    "portal_listing": 4,
    "avm_model": 2,
}


def _ensure_db():
    os.makedirs(os.path.dirname(FIELD_DB_PATH), exist_ok=True)
    if not os.path.exists(FIELD_DB_PATH):
        with open(FIELD_DB_PATH, "w", encoding="utf-8"):
            pass


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def build_record_signature(location: str, area_m2: float, price: float, property_type: str = "") -> str:
    """
    Creates a normalized signature for deduplication.
    """
    norm_loc = (location or "").strip().lower()
    norm_type = (property_type or "").strip().lower()
    norm_area = round(_safe_float(area_m2), 1)
    norm_price = round(_safe_float(price), 1)
    return f"{norm_loc}|{norm_type}|{norm_area}|{norm_price}"


def load_all_records() -> List[Dict]:
    _ensure_db()
    records: List[Dict] = []

    with open(FIELD_DB_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return records


def is_duplicate_record(location: str, area_m2: float, price: float, property_type: str = "") -> bool:
    """
    Stronger deduplication than simple equality checks.
    """
    target_sig = build_record_signature(location, area_m2, price, property_type)

    for rec in load_all_records():
        rec_sig = build_record_signature(
            rec.get("location", ""),
            rec.get("area_m2", 0),
            rec.get("price", 0),
            rec.get("property_type", ""),
        )
        if rec_sig == target_sig:
            return True

    return False


def add_field_record(
    location: str,
    area_m2: float,
    price: float,
    source: str = "broker_oral",
    source_name: str = "",
    property_type: str = "apartment",
    floor: int = 1,
    year_built: int = 2010,
    condition: str = "good",
    transaction_date: str = "",
    notes: str = "",
    coords: Optional[Dict] = None,
    added_by: str = "system",
    check_duplicates: bool = False,
    confidence: Optional[float] = None,
    country: str = "",
    language: str = "",
    ingestion_mode: str = "",
    **kwargs,
) -> Optional[Dict]:
    """
    Add a field data record.
    Returns:
      - record dict if inserted
      - None if skipped بسبب duplicate
    """
    _ensure_db()

    if source not in SOURCE_PRIORITY:
        source = "broker_oral"

    location = (location or "").strip()
    property_type = (property_type or "apartment").strip().lower()

    area_m2 = _safe_float(area_m2)
    price = _safe_float(price)

    if check_duplicates and is_duplicate_record(location, area_m2, price, property_type):
        return None

    price_pm2 = round(price / max(area_m2, 1), 0)

    record = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "transaction_date": transaction_date or datetime.now().strftime("%Y-%m-%d"),
        "location": location,
        "property_type": property_type,
        "area_m2": area_m2,
        "price": price,
        "price_pm2": price_pm2,
        "floor": _safe_int(floor, 1),
        "year_built": _safe_int(year_built, 2010),
        "condition": condition or "good",
        "source": source,
        "source_name": source_name or "",
        "priority": SOURCE_PRIORITY[source],
        "notes": notes or "",
        "coords": coords or {},
        "added_by": added_by,
        "verified": source in ("field_actual", "notary_public"),
        "confidence": confidence if confidence is not None else "",
        "country": country or "",
        "language": language or "",
        "ingestion_mode": ingestion_mode or "",
    }

    # Merge additional metadata
    record.update(kwargs)

    with open(FIELD_DB_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    _push_to_qdrant(record)
    return record


def _push_to_qdrant(record: Dict):
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import PointStruct

        _VECTOR_DB = os.path.join(_BASE_DIR, "..", "expert_smart_system", "vector_db")
        client = QdrantClient(path=_VECTOR_DB)

        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer("intfloat/multilingual-e5-large")
            text = f"query: عقار في {record['location']} مساحة {record['area_m2']} م²"
            vec = model.encode(text).tolist()
        except Exception:
            vec = [0.0] * 1024

        client.upsert(
            collection_name="egypt_estate",
            points=[
                PointStruct(
                    id=abs(hash(record["id"])) % (2**63),
                    vector=vec,
                    payload={
                        "loc": record["location"],
                        "pr": record["price"],
                        "ar": record["area_m2"],
                        "source": record["source"],
                        "priority": record["priority"],
                        "field_data": True,
                    },
                )
            ],
        )
    except Exception:
        pass


def query_field_data(
    location: str = "",
    property_type: str = "",
    min_area: float = 0,
    max_area: float = 1e9,
    source: str = "",
    verified_only: bool = False,
    top_k: int = 10,
) -> List[Dict]:
    records = load_all_records()
    filtered: List[Dict] = []

    for r in records:
        if location and location.lower() not in str(r.get("location", "")).lower():
            continue
        if property_type and r.get("property_type") != property_type:
            continue
        if not (min_area <= _safe_float(r.get("area_m2", 0)) <= max_area):
            continue
        if source and r.get("source") != source:
            continue
        if verified_only and not r.get("verified", False):
            continue
        filtered.append(r)

    filtered.sort(key=lambda r: (r.get("priority", 0), r.get("timestamp", "")), reverse=True)
    return filtered[:top_k]


def get_priority_comps(
    location: str,
    area_m2: float,
    rag_comps: Optional[List[Dict]] = None,
    top_k: int = 5,
) -> Dict:
    field = query_field_data(location=location, min_area=area_m2 * 0.5, max_area=area_m2 * 2.0)

    all_comps = []

    for r in field:
        all_comps.append({
            "loc": r["location"],
            "price_pm2": r["price_pm2"],
            "area": r["area_m2"],
            "source": r["source"],
            "source_name": r.get("source_name", ""),
            "priority": r["priority"],
            "verified": r["verified"],
            "date": r.get("transaction_date", ""),
            "notes": r.get("notes", ""),
        })

    for c in (rag_comps or []):
        all_comps.append({
            "loc": c.get("loc", location),
            "price_pm2": c.get("price_per_m2", 0),
            "area": c.get("ar", area_m2),
            "source": "portal_listing",
            "source_name": c.get("source_name", ""),
            "priority": SOURCE_PRIORITY["portal_listing"],
            "verified": False,
            "date": c.get("date", ""),
            "notes": c.get("notes", ""),
        })

    all_comps.sort(key=lambda c: c["priority"], reverse=True)
    top_comps = all_comps[:top_k]

    if top_comps:
        total_w = sum(c["priority"] for c in top_comps)
        w_ppm = sum(c["price_pm2"] * c["priority"] for c in top_comps) / total_w if total_w else 0
    else:
        w_ppm = 0

    hierarchy = {
        "field": sum(1 for c in top_comps if c["priority"] >= 7),
        "portal": sum(1 for c in top_comps if c["priority"] == 4),
        "avm": sum(1 for c in top_comps if c["priority"] <= 2),
    }

    has_field = hierarchy["field"] > 0
    source_note = (
        f"البيانات الميدانية الحقيقية تتصدر التحليل ({hierarchy['field']} مصدر ميداني)"
        if has_field
        else f"يعتمد التحليل على بيانات المنصات ({hierarchy['portal']} مقارنة)"
    )

    return {
        "comps": top_comps,
        "hierarchy_used": hierarchy,
        "weighted_ppm": round(w_ppm, 0),
        "source_note": source_note,
        "field_priority": has_field,
    }


def export_field_data_xlsx(output_dir: str = "") -> str:
    try:
        import xlsxwriter
    except ImportError:
        return ""

    records = load_all_records()
    if not records:
        return ""

    if not output_dir:
        output_dir = os.path.join(_BASE_DIR, "outputs", "reports")
    os.makedirs(output_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"field_data_{ts}.xlsx")

    wb = xlsxwriter.Workbook(path)
    ws = wb.add_worksheet("Field Data")
    ws.right_to_left()

    fH = wb.add_format({"bold": True, "bg_color": "#1F4E78", "font_color": "white", "border": 1, "align": "center"})
    fN = wb.add_format({"num_format": "#,##0", "border": 1, "align": "center"})
    fT = wb.add_format({"border": 1, "align": "right"})
    fV = wb.add_format({"border": 1, "bg_color": "#E2EFDA", "align": "center"})

    cols = [
        "id", "transaction_date", "location", "property_type", "area_m2",
        "price", "price_pm2", "floor", "source", "source_name", "verified",
        "confidence", "country", "language", "ingestion_mode", "notes"
    ]

    for c, col in enumerate(cols):
        ws.write(0, c, col, fH)

    for r, rec in enumerate(records, 1):
        for c, col in enumerate(cols):
            val = rec.get(col, "")
            if isinstance(val, bool):
                ws.write(r, c, "✅" if val else "❌", fV)
            elif isinstance(val, (int, float)) and col in ("price", "price_pm2", "area_m2", "confidence"):
                ws.write(r, c, val, fN)
            else:
                ws.write(r, c, str(val), fT)

    wb.close()
    return path


if __name__ == "__main__":
    add_field_record(
        "المعادي",
        150,
        4_500_000,
        "broker_oral",
        source_name="محمد عبدالله — سمسار",
        notes="صفقة فعلية مغلقة Q1-2026",
        check_duplicates=True,
    )

    add_field_record(
        "المعادي",
        140,
        4_200_000,
        "field_actual",
        source_name="عقد موثق — شهر عقاري",
        transaction_date="2026-02-15",
        check_duplicates=True,
    )

    comps = get_priority_comps("المعادي", 150)
    print(f"Comps returned: {len(comps['comps'])}")
    print(f"Weighted PPM: {comps['weighted_ppm']:,.0f}")
    print(f"Source note: {comps['source_note']}")
    print(f"Field priority: {comps['field_priority']}")

    xl = export_field_data_xlsx()
    print(f"Excel export: {xl}")