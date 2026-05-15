"""
populate_knowledge_base.py — Task 22.4
Loads all seed entries into a KnowledgeBase instance and exports to JSON.
Run from the core_engine directory:
    python scripts/populate_knowledge_base.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from knowledge.knowledge_base import KnowledgeBase
from knowledge.seed_data import get_seed_entries

OUTPUT_FILE = str(Path(__file__).resolve().parent.parent / "knowledge" / "knowledge_base_export.json")


def main() -> None:
    print("[populate] Initialising KnowledgeBase ...")
    kb = KnowledgeBase()

    entries = get_seed_entries()
    print(f"[populate] Loading {len(entries)} seed entries (auto_embed=False) ...")

    ok = 0
    for entry in entries:
        if kb.add_entry(entry, auto_embed=False):
            ok += 1
        else:
            print(f"[populate] WARNING: failed to add entry {entry.id}")

    print(f"[populate] Loaded {ok}/{len(entries)} entries successfully.")

    stats = kb.get_statistics()
    print(f"[populate] Statistics:")
    print(f"  total_entries : {stats['total_entries']}")
    print(f"  by_category   : {stats['by_category']}")
    print(f"  by_language   : {stats['by_language']}")

    kb.export(OUTPUT_FILE)
    print(f"[populate] Exported to {OUTPUT_FILE}")
    print("[populate] Done.")


if __name__ == "__main__":
    main()
