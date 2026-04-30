"""
knowledge_vault.py — Expert_Smart Memory Vault
Session-persistent valuation history for RAG-style context injection.

Each valuation result is stored in a ring-buffer (in-memory) and
appended to a JSONL file for cross-session recall.
Expert tone samples (from uploaded reports) are used to personalize
the AI system prompt in /api/chat.
"""

import json
import os
import time
from collections import deque
from typing import Optional, List

# ── Storage ────────────────────────────────────────────────────────────────────

_VAULT: deque = deque(maxlen=500)   # last 500 valuation records
_TONE_SAMPLES: list = []            # expert writing samples (for style learning)

_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs", "vault")
os.makedirs(_OUTPUT_DIR, exist_ok=True)
_VAULT_FILE = os.path.join(_OUTPUT_DIR, "valuation_history.jsonl")

# ── Core Operations ────────────────────────────────────────────────────────────

def store_record(record: dict) -> None:
    """
    Store a valuation record to the in-memory ring buffer and JSONL file.
    Fields: location, property_type, area, reconciled_value, gis, purpose, ts
    """
    entry = dict(record)
    entry.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%S"))
    _VAULT.appendleft(entry)
    try:
        with open(_VAULT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def search_context(location: str = "", property_type: str = "", n: int = 3) -> List[dict]:
    """
    Find the N most relevant past valuations for context injection.
    Uses simple keyword matching (no embeddings required).
    Scored: +2 for location match, +1 for property_type match.
    """
    results = []
    loc = (location or "").strip()
    for rec in _VAULT:
        score = 0
        if loc and loc in rec.get("location", ""):
            score += 2
        if property_type and property_type in rec.get("property_type", ""):
            score += 1
        if score > 0:
            results.append((score, rec))
    results.sort(reverse=True, key=lambda x: x[0])
    return [r for _, r in results[:n]]


def build_context_note(location: str = "", property_type: str = "") -> Optional[str]:
    """
    Build a human-readable Arabic context note for injecting into chat responses.
    Returns None if no relevant history found.
    """
    matches = search_context(location, property_type)
    if not matches:
        return None
    values = [m.get("reconciled_value", 0) for m in matches if m.get("reconciled_value")]
    if not values:
        return None
    avg_value = sum(values) / len(values)
    loc_label = location or "منطقة مماثلة"
    return (
        f"📚 بناءً على {len(matches)} تقييم سابق في {loc_label} — "
        f"متوسط القيمة السوقية المسجّلة = {avg_value:,.0f} ج.م. "
        f"استخدم هذا السياق لمقارنة النتيجة الحالية."
    )


def build_context_note_for_prompt(location: str = "", property_type: str = "") -> Optional[str]:
    """
    English/Arabic combined context note suitable for LLM system prompts.
    """
    matches = search_context(location, property_type)
    if not matches:
        return None
    values = [m.get("reconciled_value", 0) for m in matches if m.get("reconciled_value")]
    if not values:
        return None
    avg = sum(values) / len(values)
    loc_label = location or "comparable area"
    return (
        f"Memory Vault context: {len(matches)} previous valuation(s) in {loc_label} "
        f"show an average market value of {avg:,.0f} EGP. "
        f"Reference this when analysing the current property."
    )


# ── Expert Tone Learning ───────────────────────────────────────────────────────

def store_tone_sample(text: str) -> None:
    """Store an expert report text sample for style learning."""
    if text and len(text) > 150:
        _TONE_SAMPLES.append(text[:3000])


def get_tone_context() -> str:
    """
    Return a system-prompt snippet reflecting learned expert tone.
    Empty string if no samples stored yet.
    """
    if not _TONE_SAMPLES:
        return ""
    return (
        f"Tone calibration: {len(_TONE_SAMPLES)} expert report(s) analysed. "
        f"Maintain a formal, academic, Egyptian-Arabic professional register "
        f"matching the uploaded reports' vocabulary and structure."
    )


# ── Utility ────────────────────────────────────────────────────────────────────

def get_vault_stats() -> dict:
    return {
        "total_records": len(_VAULT),
        "tone_samples":  len(_TONE_SAMPLES),
        "vault_file":    _VAULT_FILE,
    }


def get_recent(n: int = 5) -> list:
    return list(_VAULT)[:n]


# ── Startup: reload persisted history ─────────────────────────────────────────

def _load_history() -> None:
    if not os.path.exists(_VAULT_FILE):
        return
    try:
        with open(_VAULT_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    _VAULT.append(json.loads(line))
    except Exception:
        pass


_load_history()
