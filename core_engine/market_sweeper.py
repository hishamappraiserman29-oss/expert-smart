import os
import re
import sys
import json
import random
import threading
import traceback
from datetime import datetime
from typing import List, Dict, Any, Optional

# محاولة استيراد مدير البيانات الميدانية
try:
    from field_data_manager import add_field_record
except ImportError:
    # دالة بديلة في حال عدم وجود الملف حالياً للtesting
    def add_field_record(**kwargs):
        return True

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUTS_DIR = os.path.join(_BASE_DIR, "outputs")
LOGS_DIR = os.path.join(OUTPUTS_DIR, "logs")
RUN_SUMMARY_DIR = os.path.join(LOGS_DIR, "market_sweep_runs")

def ensure_dirs():
    os.makedirs(LOGS_DIR, exist_ok=True)
    os.makedirs(RUN_SUMMARY_DIR, exist_ok=True)

def now_iso() -> str:
    return datetime.now().isoformat()

def now_human() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def append_log(entry: Dict[str, Any]):
    ensure_dirs()
    log_path = os.path.join(LOGS_DIR, "market_sweep.log")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def save_run_summary(entry: Dict[str, Any]) -> str:
    ensure_dirs()
    filename = f"market_sweep_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path = os.path.join(RUN_SUMMARY_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entry, f, ensure_ascii=False, indent=2)
    return path

def build_success_entry(scanned_count, added_count, duplicate_count, sources, ingestion_mode="mock_generator"):
    return {
        "timestamp": now_iso(),
        "status": "success",
        "scanned_count": scanned_count,
        "records_added": added_count,
        "duplicate_count": duplicate_count,
        "source_summary": sorted(list(set(sources))),
        "source_count": len(set(sources)),
        "ingestion_mode": ingestion_mode,
        "market": "mixed",
        "notes": "Market sweep completed successfully."
    }

def build_failure_entry(error_message, ingestion_mode="mock_generator"):
    return {
        "timestamp": now_iso(),
        "status": "failed",
        "error": error_message,
        "ingestion_mode": ingestion_mode,
        "notes": "Market sweep failed."
    }

def generate_mock_market_records() -> List[Dict[str, Any]]:
    portals = [
        {"name": "aqarmap.com", "country": "Egypt", "language": "ar"},
        {"name": "propertyfinder.eg", "country": "Egypt", "language": "ar_en"},
        {"name": "olx.com.eg", "country": "Egypt", "language": "ar"},
        {"name": "aqar.sa", "country": "Saudi Arabia", "language": "ar"},
    ]

    base_samples = [
        {"location": "التجمع الخامس", "property_type": "apartment", "floor": 3, "year_built": 2019},
        {":location": "المعادي", "property_type": "apartment", "floor": 2, "year_built": 2015},
        {"location": "مدينة نصر", "property_type": "apartment", "floor": 5, "year_built": 2008},
        {"location": "الشيخ زايد", "property_type": "villa", "floor": 1, "year_built": 2020},
        {"location": "حي النرجس", "property_type": "villa", "floor": 0, "year_built": 2022},
    ]

    fresh_records = []
    num_to_generate = random.randint(5, 10)

    for _ in range(num_to_generate):
        sample = random.choice(base_samples).copy()
        portal = random.choice(portals)
        base_area = random.randint(100, 400)
        base_price_pm2 = random.randint(15000, 35000)

        sample.update({
            "area_m2": float(base_area),
            "price": float(base_area * base_price_pm2),
            "source": "portal_listing",
            "source_name": portal["name"],
            "country": portal["country"],
            "language": portal["language"],
            "confidence": round(random.uniform(0.65, 0.92), 2),
            "ingestion_mode": "mock_generator"
        })
        fresh_records.append(sample)
    return fresh_records

def perform_market_sweep():
    ensure_dirs()
    print(f"[{now_human()}] Starting Market Sweep...")
    try:
        fresh_records = generate_mock_market_records()
        scanned_count = len(fresh_records)
        added_count, duplicate_count = 0, 0
        used_sources = []

        for record in fresh_records:
            used_sources.append(record.get("source_name", "unknown"))
            try:
                # نفترض أن add_field_record ترجع True إذا أضافت فعلياً
                if add_field_record(added_by="market_sweep_bot", check_duplicates=True, **record):
                    added_count += 1
                else:
                    duplicate_count += 1
            except Exception as e:
                append_log({"status": "record_failed", "error": str(e)})

        success_entry = build_success_entry(scanned_count, added_count, duplicate_count, used_sources)
        append_log(success_entry)
        save_run_summary(success_entry)
        print(f"[{now_human()}] Sweep Complete | Scanned: {scanned_count} | Added: {added_count}")
    except Exception as e:
        print(f"[{now_human()}] Sweep Failed: {e}")
        append_log(build_failure_entry(str(e)))

# ── Field Price Estimation via LLM ────────────────────────────────────────────

_INPUTS_DIR = os.path.join(_BASE_DIR, "..", "inputs")

def _is_inputs_empty() -> bool:
    try:
        if not os.path.isdir(_INPUTS_DIR): return True
        return len([f for f in os.listdir(_INPUTS_DIR) if not f.startswith(".")]) == 0
    except: return True

def _trigger_sweep_background():
    threading.Thread(target=perform_market_sweep, daemon=True).start()

def estimate_price_via_llm(location: str, property_type: str = "apartment") -> Optional[float]:
    if _is_inputs_empty():
        _trigger_sweep_background()

    import requests
    model = "llama3" # Default
    
    # محاولة اختيار أفضل موديل متاح في Ollama
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        available = [m["name"] for m in r.json().get("models", [])]
        for pref in ["qwen2.5:7b", "llama3", "mistral"]:
            if any(pref in m for m in available):
                model = next(m for m in available if pref in m)
                break
    except: pass

    prop_ar = {"apartment": "شقة سكنية", "villa": "فيلا", "land": "أرض"}.get(property_type, "عقار")
    
    prompt = (
        f"أنت خبير عقاري. ما هو متوسط سعر متر الـ {prop_ar} الحالي في منطقة {location}؟ "
        f"أجب برقم واحد فقط بالجنيه المصري أو الريال السعودي بدون أي شرح."
    )

    try:
        resp = requests.post("http://localhost:11434/api/chat", json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.1}
        }, timeout=30)
        text = resp.json().get("message", {}).get("content", "")
        
        # تنظيف النص واستخراج الرقم
        text_clean = text.replace(",", "").translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
        matches = re.findall(r"\d[\d.]*", text_clean)
        for tok in matches:
            val = float(tok)
            if 2000 <= val <= 200000:
                print(f"[MarketSweeper] LLM Estimated: {val:,.0f} for {location}")
                return val
    except Exception as e:
        print(f"[MarketSweeper] Error: {e}")
    
    return None

if __name__ == "__main__":
    perform_market_sweep()