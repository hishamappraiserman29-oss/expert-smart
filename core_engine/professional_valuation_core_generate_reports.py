"""
professional_valuation_core_generate_reports.py
Orchestrates PDF + Excel + QA audit generation for the three core reports.
Run from within core_engine/ directory.
advisory_only=True | not_real_training=True
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from professional_valuation_core_pdf_generator import generate_all_pdfs
from professional_valuation_core_excel_generator import generate_all_excel
from professional_valuation_core_report_audits import run_all_audits
from professional_valuation_core_report_examples import RECONCILIATION

_HERE = Path(__file__).parent
_QA_ROOT = _HERE / "instance" / "manual_review_outputs" / \
           "professional_valuation_final_core_workflow_and_report_qa"


def main() -> None:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"[generator] Starting — {generated_at}")

    # 1. Generate PDFs
    pdf_results = generate_all_pdfs(
        _QA_ROOT / "pdf_outputs",
        _QA_ROOT / "pdf_visual_previews",
    )
    for k, v in pdf_results.items():
        status = "OK" if v["rendered_ok"] else "FAILED"
        print(f"  [PDF {status}] {k}: {v['pdf_size_bytes']:,} bytes")

    # 2. Generate Excel
    excel_results = generate_all_excel(_QA_ROOT / "excel_outputs")
    for k, v in excel_results.items():
        print(f"  [XLS {v['status']}] {k}: {v.get('size_bytes', 0):,} bytes")

    # 3. Generate all QA audit files
    run_all_audits(_QA_ROOT, pdf_results, excel_results)
    print("  [audits] All QA JSON files written")

    # 4. Write test logs
    (_QA_ROOT / "test_logs").mkdir(exist_ok=True)
    (_QA_ROOT / "test_logs" / "backend_test_results.json").write_text(
        json.dumps({
            "note": "Run: python -m pytest core_engine/tests/test_pv_final_core_workflow_and_report_qa.py -q",
            "status": "pending_run",
            "generated_at": generated_at,
        }, indent=2), encoding="utf-8"
    )
    (_QA_ROOT / "test_logs" / "e2e_test_results.json").write_text(
        json.dumps({
            "note": "Run: python -m pytest core_engine/tests/e2e/test_pv_final_core_workflow_and_report_qa_e2e.py -q",
            "status": "pending_run",
            "generated_at": generated_at,
        }, indent=2), encoding="utf-8"
    )

    # 5. Summary
    all_pdfs_ok   = all(v["rendered_ok"] for v in pdf_results.values())
    all_excels_ok = all(v["status"] == "OK" for v in excel_results.values())
    print(f"\n[generator] PDFs: {'ALL OK' if all_pdfs_ok else 'SOME FAILED'}")
    print(f"[generator] Excel: {'ALL OK' if all_excels_ok else 'SOME FAILED'}")
    print(f"[generator] QA Root: {_QA_ROOT}")
    print("[generator] Done.")


if __name__ == "__main__":
    main()
