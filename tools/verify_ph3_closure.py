"""
tools/verify_ph3_closure.py

Collect PH.3 closure evidence files (screenshots, GCP exports) and produce
a SHA-256 hash manifest for the closure commit.

Does NOT touch Google Cloud directly — operator runs this AFTER completing
the external steps described in docs/PH3_CLOSURE_RUNBOOK.md.

Usage:
    python tools/verify_ph3_closure.py \\
        --evidence-dir path/to/screenshots/ \\
        --option A \\
        --out docs/PH3_CLOSURE_EVIDENCE.md

    # with optional notes
    python tools/verify_ph3_closure.py \\
        --evidence-dir path/to/screenshots/ \\
        --option C \\
        --notes "Service account disabled on 2026-05-20 by Hisham Elmahdy"
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

_OPTION_DESCRIPTIONS = {
    "A": "Key rotated — old key ID 39b698a4... deleted, new key stored in secret manager",
    "B": "Key/account confirmed never-used or already inactive — no new key needed",
    "C": "Service account disabled or deleted entirely — all keys revoked",
}

_SA_EMAIL = "appraiser-sync@gleaming-terra-487414-f4.iam.gserviceaccount.com"
_OLD_KEY_ID = "39b698a44b239fc7712314a035f7202e05718842"
_LOCAL_KEY_FILE = Path("core_engine/service_account.json")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def check_local_key_absent() -> tuple[bool, str]:
    """Return (absent, message) for the local service_account.json."""
    if _LOCAL_KEY_FILE.exists():
        return False, f"⚠️  LOCAL KEY FILE STILL EXISTS: {_LOCAL_KEY_FILE} — delete it after rotation"
    return True, f"✅  Local key file absent: {_LOCAL_KEY_FILE}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate PH.3 closure evidence manifest"
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        required=True,
        metavar="DIR",
        help="Directory containing closure evidence (screenshots, GCP exports)",
    )
    parser.add_argument(
        "--option",
        choices=["A", "B", "C"],
        required=True,
        help="Closure option executed (A=rotate, B=confirm-unused, C=disable)",
    )
    parser.add_argument(
        "--notes",
        default="",
        help="Optional free-text notes about the closure action",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("docs/PH3_CLOSURE_EVIDENCE.md"),
        help="Output manifest file (default: docs/PH3_CLOSURE_EVIDENCE.md)",
    )
    args = parser.parse_args()

    # Validate evidence directory
    if not args.evidence_dir.is_dir():
        print(
            f"ERROR: evidence directory not found: {args.evidence_dir}",
            file=sys.stderr,
        )
        return 1

    files = sorted(
        p for p in args.evidence_dir.rglob("*")
        if p.is_file() and not p.name.startswith(".")
    )
    if not files:
        print(
            f"ERROR: no evidence files found in {args.evidence_dir}",
            file=sys.stderr,
        )
        return 1

    # Check local key file
    key_absent, key_msg = check_local_key_absent()

    # Build manifest
    now = datetime.now(timezone.utc)
    lines: list[str] = [
        "# PH.3 Closure Evidence Manifest",
        "",
        f"**Closure date:** {now.date().isoformat()}",
        f"**Closure time (UTC):** {now.strftime('%H:%M')}",
        f"**Option chosen:** {args.option} — {_OPTION_DESCRIPTIONS[args.option]}",
        f"**Service account:** `{_SA_EMAIL}`",
        f"**Old key ID:** `{_OLD_KEY_ID}`",
        f"**Evidence files:** {len(files)}",
        "",
    ]

    if args.notes:
        lines += [
            "## Operator Notes",
            "",
            args.notes,
            "",
        ]

    lines += [
        "## Local Key File Status",
        "",
        key_msg,
        "",
        "## Evidence File Manifest (SHA-256)",
        "",
        "> Evidence files are stored OUTSIDE the git repository (sensitive screenshots).",
        "> Only this hash manifest is committed. Retrieve originals from secure storage",
        "> if audit is ever required.",
        "",
        "| File | Size (bytes) | SHA-256 (first 32 hex chars) |",
        "|---|---|---|",
    ]

    for f in files:
        rel = f.relative_to(args.evidence_dir)
        size = f.stat().st_size
        digest = sha256_file(f)
        lines.append(f"| `{rel}` | {size} | `{digest[:32]}...` |")

    lines += [
        "",
        "## Next Steps",
        "",
        "After running this script:",
        "",
        "1. Update `docs/PH3_KEY_ROTATION_WAIVER.md` — fill in the Closure Record table",
        "2. Update `docs/SECURITY_AUDIT_v1.md` — mark PH.3 as ✅ CLOSED",
        "3. Update `docs/FINAL_RELEASE_HANDOFF_v1.1.0.md` — P0 → ✅, gate verdict",
        "4. Commit: `docs/PH3_CLOSURE_EVIDENCE.md` + the three updated docs",
        "   Suggested message:",
        "   ```",
        f"   security(ph3): close GCP appraiser-sync service account key (Option {args.option})",
        "   ```",
        "",
        "---",
        "",
        f"*Generated by `tools/verify_ph3_closure.py` on {now.date().isoformat()}*",
    ]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✅  Manifest written: {args.out}")
    if not key_absent:
        print(key_msg, file=sys.stderr)
        return 1  # Warn operator — local key still present

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
