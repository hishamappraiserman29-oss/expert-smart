"""Sanity test: perf_baseline.py runs end-to-end and produces a valid markdown file."""
import subprocess
import sys
from pathlib import Path

# Project root is two levels above this file (core_engine/tests/ → core_engine/ → root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPT = _PROJECT_ROOT / "tools" / "perf_baseline.py"


def test_script_runs(tmp_path):
    out = tmp_path / "baseline.md"
    result = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--iterations", "2",
            "--out", str(out),
            "--profile", "professional_template",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(_PROJECT_ROOT),
    )
    assert result.returncode == 0, f"Script failed:\n{result.stderr}"
    assert out.exists(), "Output file was not created"

    content = out.read_text(encoding="utf-8")
    assert "Performance Baseline" in content
    for label in [
        "validate_report",
        "generate_pdf",
        "save_report",
        "get_report",
        "full pipeline",
    ]:
        assert label in content, f"Missing scenario in output: {label}"
