#!/usr/bin/env python3
"""
Final Release Reconciliation Orchestrator
Modes: --fresh, --resume, --validate-only
"""
import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(r"C:\Users\Lenovo\Desktop\expert_smart1 - Copy").resolve()
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"
DELIVERY = ROOT / "core_engine" / "instance" / "manual_review_outputs" / "FINAL_PROFESSIONAL_VALUATION_DELIVERY"
AUDITS = DELIVERY / "audits"
LOGS = DELIVERY / "test_logs"
CHECKPOINT = AUDITS / "final_reconciliation_checkpoint.json"

# Frozen delivery identity SHAs — CLASS A (verify immutable artifacts before copy, not render reproducibility)
# TRAD: Traditional render-gate PDF (professional_valuation_traditional_final_render_gate)
TRAD_SHA = "9f2fe498f49d91058d884952bdc387e26a9f6f1a5ad000710275fe0c2300f587"
# DET: Detailed density-upgrade source PDF (professional_valuation_detailed_density_upgrade)
DET_SHA  = "671f768be3c685512aa72318a26f0b1a65c3307869938ad5bd6ab41e34b68662"
# PRO: Professional PDF with canonical Saudi address (حي النخيل، شمال الرياض — no QA suffix)
PRO_SHA  = "702914b84711caa1d9422f943e083b5fe428aaba618e44cf1ec15c0a93449632"
TRAD_PAGES = 16
DET_PAGES  = 18
PRO_PAGES  = 28
TOTAL_PAGES = 62


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().lower()


def page_count(path: pathlib.Path) -> int:
    import fitz
    doc = fitz.open(str(path))
    n = len(doc)
    doc.close()
    return n


def run_pytest(test_path: str) -> dict:
    result = subprocess.run(
        [str(VENV_PY), "-m", "pytest", test_path, "-q"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT)
    )
    output = result.stdout + result.stderr
    passed = failed = skipped = 0
    for line in output.splitlines():
        if "passed" in line:
            import re
            m = re.search(r"(\d+) passed", line)
            if m: passed = int(m.group(1))
            m = re.search(r"(\d+) failed", line)
            if m: failed = int(m.group(1))
            m = re.search(r"(\d+) skipped", line)
            if m: skipped = int(m.group(1))
    return {"passed": passed, "failed": failed, "skipped": skipped, "output": output, "rc": result.returncode}


def validate_manifest() -> dict:
    manifest = DELIVERY / "final_report" / "CONTROLLED_STAGING_MANIFEST.txt"
    lines = manifest.read_text(encoding="utf-8").splitlines()
    paths = [l.strip() for l in lines if l.strip()]
    missing = [p for p in paths if not (ROOT / p).exists()]
    seen = set()
    dupes = [p for p in paths if p in seen or seen.add(p)]
    return {
        "total_paths": len(paths),
        "missing": missing,
        "duplicates": dupes,
        "result": "PASS" if not missing and not dupes else "FAIL"
    }


def validate_only():
    print("=== VALIDATE-ONLY MODE ===")

    # Check PDFs
    actual = DELIVERY / "actual_files"
    for name, path_name, exp_sha, exp_pages in [
        ("Traditional", "02_FINAL_TRADITIONAL_REPORT.pdf", TRAD_SHA, TRAD_PAGES),
        ("Detailed",    "03_FINAL_DETAILED_REPORT.pdf",    DET_SHA,  DET_PAGES),
        ("Professional","04_FINAL_PROFESSIONAL_REPORT.pdf", PRO_SHA, PRO_PAGES),
    ]:
        p = actual / path_name
        s = sha256(p)
        pg = page_count(p)
        ok = s == exp_sha and pg == exp_pages
        print(f"  {name}: pages={pg}/{exp_pages} sha_match={s==exp_sha} -> {'PASS' if ok else 'FAIL'}")

    # Manifest
    mv = validate_manifest()
    print(f"  Manifest: {mv['total_paths']} paths, {len(mv['missing'])} missing -> {mv['result']}")

    # Checkpoint
    if CHECKPOINT.exists():
        cp = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
        print(f"  Checkpoint: {cp['final_state']['final_decision']}")
    else:
        print("  Checkpoint: MISSING")


def resume_or_fresh(mode: str):
    log_path = LOGS / "final_release_reconciliation.log"
    LOGS.mkdir(parents=True, exist_ok=True)

    log_lines = []
    def log(msg: str):
        print(msg)
        log_lines.append(msg)

    log(f"=== Final Release Reconciliation — mode={mode} ===")

    # Load checkpoint if resuming
    cp = {}
    if mode == "resume" and CHECKPOINT.exists():
        cp = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
        log(f"Loaded checkpoint: {len(cp.get('steps_completed', {}))} steps recorded")

    def step_done(name: str) -> bool:
        if mode == "fresh":
            return False
        s = cp.get("steps_completed", {}).get(name, {})
        return s.get("status") == "DONE"

    results = {}

    # Step 1: Verify Detailed PDF
    if not step_done("step_1_freeze_detailed_artifact"):
        log("[STEP 1] Verifying Detailed PDF...")
        src = (ROOT / "core_engine/instance/manual_review_outputs"
               "/professional_valuation_detailed_density_upgrade/actual_file/FINAL_DETAILED_REPORT.pdf")
        s = sha256(src)
        pg = page_count(src)
        results["step1"] = {"sha": s, "pages": pg, "sha_ok": s == DET_SHA, "pages_ok": pg == DET_PAGES}
        log(f"  SHA={'MATCH' if s==DET_SHA else 'MISMATCH'} pages={pg}/18")
        if s != DET_SHA or pg != DET_PAGES:
            log("  FAIL — Detailed PDF does not match expected")
            sys.exit(1)
    else:
        log("[STEP 1] SKIP (checkpoint valid)")
        results["step1"] = cp["steps_completed"]["step_1_freeze_detailed_artifact"]

    # Step 2-3: Run Detailed suite
    if not step_done("step_3_detailed_acceptance_suite"):
        log("[STEP 3] Running Detailed acceptance suite...")
        r = run_pytest("core_engine/tests/test_pv_detailed_pdf_density_upgrade.py")
        results["step3"] = r
        log(f"  {r['passed']} passed, {r['failed']} failed, {r['skipped']} skipped")
        if r["failed"] or r["skipped"]:
            log("  FAIL — test failures remain")
            sys.exit(1)
    else:
        log("[STEP 3] SKIP (checkpoint valid)")

    # Step 4: All PDF regressions
    if not step_done("step_4_all_pdf_regressions"):
        log("[STEP 4] Running all PDF regressions...")
        r = run_pytest("core_engine/tests/test_pv_traditional_pdf_final_render.py "
                       "core_engine/tests/test_pv_detailed_pdf_density_upgrade.py "
                       "core_engine/tests/test_pv_professional_pdf_density_upgrade.py")
        results["step4"] = r
        log(f"  {r['passed']} passed, {r['failed']} failed, {r['skipped']} skipped")
        if r["failed"] or r["skipped"]:
            log("  FAIL — regression failures")
            sys.exit(1)
    else:
        log("[STEP 4] SKIP (checkpoint valid)")

    # Step 9: Consolidated tests
    if not step_done("step_9_consolidated_tests"):
        log("[STEP 9] Running consolidated delivery tests...")
        r = run_pytest("core_engine/tests/test_pv_final_consolidated_delivery.py")
        results["step9"] = r
        log(f"  {r['passed']} passed, {r['failed']} failed, {r['skipped']} skipped")
        if r["failed"] or r["skipped"]:
            log("  FAIL — consolidated test failures")
            sys.exit(1)
    else:
        log("[STEP 9] SKIP (checkpoint valid)")

    # Step 10: Validate manifest
    log("[STEP 10] Validating staging manifest...")
    mv = validate_manifest()
    results["step10"] = mv
    log(f"  {mv['total_paths']} paths, {len(mv['missing'])} missing -> {mv['result']}")
    if mv["result"] != "PASS":
        log("  FAIL — manifest validation failed")
        sys.exit(1)

    log("\n=== ALL STEPS COMPLETE ===")
    log(f"Traditional: {TRAD_PAGES} pages | Detailed: {DET_PAGES} pages | Professional: {PRO_PAGES} pages")
    log(f"Total PDF pages: {TOTAL_PAGES} | Manifest paths: {mv['total_paths']}")
    log("Final decision: STAGING_PREVIEW_APPROVED")

    log_path.write_text("\n".join(log_lines), encoding="utf-8")
    print(f"\nLog written: {log_path}")


def main():
    parser = argparse.ArgumentParser(description="Final Release Reconciliation Orchestrator")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--fresh", action="store_true")
    group.add_argument("--resume", action="store_true")
    group.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    if args.validate_only:
        validate_only()
    elif args.fresh:
        resume_or_fresh("fresh")
    else:
        resume_or_fresh("resume")


if __name__ == "__main__":
    main()
