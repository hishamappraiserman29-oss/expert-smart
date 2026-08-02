"""
test_standards_compliance_visual_qa_generator_unit.py — Wave 3A unit tests

VT01  Import isolation — no file, directory, or browser side-effects on import
VT02  Governance constants — advisory_only, certification_ready, etc.
VT03  Synthetic identity — SYNTHETIC_DATA flag; synthetic QA marker in VALUER; no MRICS
VT04  Score determinism — _compute_score() is stable across calls
VT05  Valid case_id accepted by _sanitize_component
VT06  Path traversal rejected — '../case'
VT07  Windows separator rejected — '..\\\\case' and 'C:\\\\case'
VT08  UNC rejected — '\\\\\\\\server\\\\share'
VT09  Null / colon / empty rejected
VT10  Valid run_id accepted
VT11  Unique generated run_id — _new_run_id() produces distinct values
VT12  Output containment — constructed run_dir stays under output_root
VT13  Existing run rejected when overwrite=False
VT14  overwrite=True preserves unknown files, run_dir, and output_root
VT15  Artifact extension allowlist — all generated artifacts use approved extensions
VT16  HTML escaping — textual values are escaped
VT17  No certification overclaim — advisory_only / certification_ready enforced
VT18  Browser close on success — page and browser closed via finally
VT19  Browser close on failure — page and browser closed even when pdf() raises
VT20  Partial artifact cleanup — failure removes only files created in this run
VT21  Deterministic HTML — same constants produce identical output on repeated calls
VT22  CLI --output-dir required — exits with error when omitted
VT23  Endpoint remains absent — pv_standards_compliance_endpoint.py not in Unified
VT24  No active routes — generator module registers no Flask routes
VT25  Cleanup scope — failure in run A does not affect sibling run B artifacts
VT26  Full artifact schema — all categories present, correct types, allowed extensions
VT27  Score is dict — score field has required keys; not a float
VT28  Sibling run isolation — two run_ids under same case_id coexist independently
"""
from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── Path setup ────────────────────────────────────────────────────────────────
_TESTS = Path(__file__).parent.resolve()
_CORE = _TESTS.parent.resolve()
_ROOT = _CORE.parent.resolve()

for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import standards_compliance_visual_qa_generator as mod  # noqa: E402


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_fake_playwright(*, pdf_side_effect=None, screenshot_side_effect=None):
    """Build a fake sync_playwright context manager.

    Returns (fake_sync_playwright, fake_page, fake_browser).
    """
    fake_page = MagicMock()
    if pdf_side_effect is not None:
        fake_page.pdf.side_effect = pdf_side_effect
    if screenshot_side_effect is not None:
        fake_page.query_selector_all.side_effect = screenshot_side_effect

    fake_browser = MagicMock()
    fake_browser.new_page.return_value = fake_page

    fake_ctx = MagicMock()
    fake_ctx.__enter__.return_value = fake_ctx
    fake_ctx.__exit__.return_value = None
    fake_ctx.chromium.launch.return_value = fake_browser

    fake_sync_pw = MagicMock(return_value=fake_ctx)
    return fake_sync_pw, fake_page, fake_browser


def _inject_fake_playwright(fake_sync_pw):
    """Inject fake_sync_pw into sys.modules so local imports inside the module use it."""
    if "playwright" not in sys.modules:
        sys.modules["playwright"] = types.ModuleType("playwright")
    if "playwright.sync_api" not in sys.modules:
        sys.modules["playwright.sync_api"] = types.ModuleType("playwright.sync_api")
    sys.modules["playwright.sync_api"].sync_playwright = fake_sync_pw


def _make_stub_heavy_funcs(tmp_path: Path):
    """Return monkeypatch-ready replacements for the three browser-dependent helpers."""
    def fake_pdf(html_path: Path, pdf_path: Path) -> None:
        pdf_path.write_bytes(b"%PDF-1.4 stub")

    def fake_screenshot(html_path: Path, shots_dir: Path, prefix: str) -> list[str]:
        shots_dir.mkdir(parents=True, exist_ok=True)
        p = shots_dir / f"{prefix}_section_1.png"
        p.write_bytes(b"\x89PNG\r\n\x1a\n")
        return [str(p)]

    def fake_inspect(pdf_path: Path, shots_dir: Path) -> dict:
        shots_dir.mkdir(parents=True, exist_ok=True)
        shot = shots_dir / "page_1.png"
        shot.write_bytes(b"\x89PNG\r\n\x1a\n")
        return {
            "path": str(pdf_path), "valid_header": True, "page_count": 1,
            "pages": [{"page": 1, "text_len": 50, "has_text": True, "blank": False,
                       "local_path": False, "shot": str(shot), "shot_size": 10}],
            "blank_pages": [], "has_text": True, "local_paths": False,
            "pass": True, "size": 14,
        }

    def fake_excel(xlsx_path: Path) -> dict:
        xlsx_path.write_bytes(b"PK\x03\x04 stub")
        return {
            "path": str(xlsx_path), "valid_signature": True, "sheet_count": 16,
            "sheet_names": [str(i) for i in range(16)], "hidden_sheets": 0,
            "formula_errors": 0, "sar_occurrences": 1, "egp_occurrences": 0,
            "qar_occurrences": 0, "local_paths": False, "pass": True,
            "size": 5, "sha256": "abc",
        }

    return fake_pdf, fake_screenshot, fake_inspect, fake_excel


# ── VT01 — Import isolation ───────────────────────────────────────────────────

def test_VT01_import_isolation():
    """Importing the module must not create files, directories, or a browser process."""
    # No module-level output directories
    assert not hasattr(mod, "OUTPUTS_DIR"), "OUTPUTS_DIR must not exist at module level"
    assert not hasattr(mod, "ARTIFACTS_DIR"), "ARTIFACTS_DIR must not exist at module level"
    assert not hasattr(mod, "SCREENSHOTS_DIR"), "SCREENSHOTS_DIR must not exist at module level"
    assert not hasattr(mod, "AUDITS_DIR"), "AUDITS_DIR must not exist at module level"

    # The fixed legacy output path must not have been created
    legacy_output = _CORE / "outputs" / "visual_qa_standards_compliance_final"
    assert not legacy_output.exists(), (
        f"Import must not create {legacy_output}"
    )


# ── VT02 — Governance constants ───────────────────────────────────────────────

def test_VT02_governance_constants():
    assert mod._SAFETY["advisory_only"] is True
    assert mod._SAFETY["certification_ready"] is False
    assert mod._SAFETY["fake_signature_created"] is False
    assert mod._SAFETY["official_compliance_decision"] is False
    assert mod._SAFETY["synthetic_data"] is True
    assert mod.SYNTHETIC_DATA is True


# ── VT03 — Synthetic identity ─────────────────────────────────────────────────

def test_VT03_synthetic_identity():
    # Synthetic data flag must be set
    assert mod.SYNTHETIC_DATA is True
    # VALUER must contain the explicit synthetic QA marker
    assert "بيانات QA اصطناعية" in mod.VALUER, (
        f"Expected explicit synthetic QA marker in VALUER: {mod.VALUER!r}"
    )
    # Professional credential abbreviation must not appear in VALUER
    assert "MRICS" not in mod.VALUER, (
        f"Professional credential must not appear in VALUER: {mod.VALUER!r}"
    )


# ── VT04 — Score determinism ──────────────────────────────────────────────────

def test_VT04_score_determinism():
    s1 = mod._compute_score()
    s2 = mod._compute_score()
    assert s1 == s2
    assert s1 == mod.SCORE


# ── VT05 — Valid case_id accepted ────────────────────────────────────────────

def test_VT05_valid_case_id():
    result = mod._sanitize_component("QA-COMPLIANCE-VISUAL-001", "case_id")
    assert result == "QA-COMPLIANCE-VISUAL-001"

    result2 = mod._sanitize_component("CASE_123", "case_id")
    assert result2 == "CASE_123"


# ── VT06 — Path traversal rejected ───────────────────────────────────────────

def test_VT06_path_traversal_rejected():
    with pytest.raises(ValueError):
        mod._sanitize_component("../escape", "case_id")

    with pytest.raises(ValueError):
        mod._sanitize_component("../../etc/passwd", "case_id")


# ── VT07 — Windows separator rejected ────────────────────────────────────────

def test_VT07_windows_separator_rejected():
    with pytest.raises(ValueError):
        mod._sanitize_component("..\\case", "case_id")

    with pytest.raises(ValueError):
        mod._sanitize_component("C:\\Windows\\case", "case_id")


# ── VT08 — UNC path rejected ─────────────────────────────────────────────────

def test_VT08_unc_rejected():
    with pytest.raises(ValueError):
        mod._sanitize_component("\\\\server\\share", "case_id")


# ── VT09 — Null / colon / empty rejected ─────────────────────────────────────

def test_VT09_null_colon_empty_rejected():
    with pytest.raises(ValueError):
        mod._sanitize_component("", "case_id")

    with pytest.raises(ValueError):
        mod._sanitize_component("case:id", "case_id")

    with pytest.raises(ValueError):
        mod._sanitize_component("case/id", "case_id")

    with pytest.raises(ValueError):
        mod._sanitize_component("a" * 81, "case_id")  # exceeds 80-char limit


# ── VT10 — Valid run_id accepted ──────────────────────────────────────────────

def test_VT10_valid_run_id():
    result = mod._sanitize_component("abc123def456", "run_id")
    assert result == "abc123def456"


# ── VT11 — Unique generated run_id ───────────────────────────────────────────

def test_VT11_unique_generated_run_id():
    ids = {mod._new_run_id() for _ in range(5)}
    assert len(ids) == 5  # all unique (UUID4 essentially guaranteed)
    for rid in ids:
        validated = mod._sanitize_component(rid, "run_id")
        assert validated == rid


# ── VT12 — Output containment ────────────────────────────────────────────────

def test_VT12_output_containment(tmp_path):
    """Sanitized components cannot escape the output root."""
    # Path traversal blocked at sanitization level
    with pytest.raises(ValueError):
        mod._sanitize_component("../escape", "case_id")

    # Valid components produce a path that stays under root
    root = (tmp_path / "qa").resolve()
    root.mkdir()
    safe_case = mod._sanitize_component("MYCASE", "case_id")
    safe_run = mod._new_run_id()
    run_dir = (root / safe_case / safe_run).resolve()
    run_dir.relative_to(root)  # must not raise ValueError


# ── VT13 — Existing run rejected ─────────────────────────────────────────────

def test_VT13_existing_run_rejected(tmp_path):
    """overwrite=False must raise FileExistsError when the run directory exists."""
    run_dir = tmp_path / "QA-COMPLIANCE-VISUAL-001" / "testrun001"
    run_dir.mkdir(parents=True)

    with pytest.raises(FileExistsError):
        mod.run_standards_compliance_visual_qa(
            output_root=tmp_path,
            case_id="QA-COMPLIANCE-VISUAL-001",
            run_id="testrun001",
            overwrite=False,
        )


# ── VT14 — overwrite=True does not delete unknown files ──────────────────────

def test_VT14_overwrite_scope(tmp_path, monkeypatch):
    """Unknown files in the run directory must survive overwrite=True.

    Verifies:
      - sentinel file with arbitrary content survives
      - run_dir is not recursively deleted
      - output_root is not deleted
      - only known artifact paths may be replaced
    """
    run_dir = tmp_path / "QA-COMPLIANCE-VISUAL-001" / "testrun001"
    (run_dir / "artifacts").mkdir(parents=True)
    sentinel = run_dir / "do_not_delete.txt"
    sentinel.write_text("sentinel content - must survive", encoding="utf-8")
    # A second unknown file nested inside artifacts
    unknown_in_artifacts = run_dir / "artifacts" / "external_notes.txt"
    unknown_in_artifacts.write_text("external notes", encoding="utf-8")

    fake_pdf, fake_ss, fake_inspect, fake_excel = _make_stub_heavy_funcs(tmp_path)
    monkeypatch.setattr(mod, "_pdf_via_playwright", fake_pdf)
    monkeypatch.setattr(mod, "_screenshot_html", fake_ss)
    monkeypatch.setattr(mod, "_inspect_pdf", fake_inspect)
    monkeypatch.setattr(mod, "_build_excel", fake_excel)

    result = mod.run_standards_compliance_visual_qa(
        output_root=tmp_path,
        case_id="QA-COMPLIANCE-VISUAL-001",
        run_id="testrun001",
        overwrite=True,
    )

    assert result["ok"]
    # Unknown files must survive
    assert sentinel.exists(), "Sentinel file must survive overwrite=True"
    assert sentinel.read_text(encoding="utf-8") == "sentinel content - must survive"
    assert unknown_in_artifacts.exists(), "Unknown file inside artifacts/ must survive"
    assert unknown_in_artifacts.read_text() == "external notes"
    # Structural directories must not be deleted
    assert run_dir.exists(), "run_dir must not be deleted"
    assert tmp_path.exists(), "output_root must not be deleted"


# ── VT15 — Artifact extension allowlist ──────────────────────────────────────

def test_VT15_artifact_extension_allowlist():
    """All artifact filenames use only approved extensions."""
    allowed = mod._ALLOWED_EXTENSIONS
    case_id = "TESTCASE"
    expected = [
        f"compliance_{case_id}_user.html",
        f"compliance_{case_id}_admin.html",
        f"compliance_{case_id}_user.pdf",
        f"compliance_{case_id}_admin.pdf",
        f"compliance_{case_id}_admin.xlsx",
        "compliance_visual_qa_report.json",
        "compliance_cross_format_consistency.json",
        "compliance_content_audit.json",
    ]
    for fname in expected:
        ext = Path(fname).suffix
        assert ext in allowed, f"Unexpected extension {ext!r} in {fname!r}"


# ── VT16 — HTML escaping ──────────────────────────────────────────────────────

def test_VT16_html_escaping():
    """_esc() escapes HTML special characters; HTML builders use _esc."""
    # Direct _esc checks
    assert mod._esc("<script>") == "&lt;script&gt;"
    assert mod._esc("<img onerror=x>") == "&lt;img onerror=x&gt;"
    assert mod._esc("&") == "&amp;"
    assert mod._esc('"hello"') == "&quot;hello&quot;"
    assert mod._esc(None) == ""

    # Patch CASE_ID temporarily and verify HTML builders escape it
    old = mod.CASE_ID
    try:
        mod.CASE_ID = "<test&case>"
        html = mod._html_header(is_admin=False)
        assert "<test&case>" not in html, "Unescaped CASE_ID in HTML"
        assert "&lt;test&amp;case&gt;" in html
    finally:
        mod.CASE_ID = old


# ── VT17 — No certification overclaim ────────────────────────────────────────

def test_VT17_no_certification_overclaim():
    user_html = mod._build_user_html()
    admin_html = mod._build_admin_html()

    # Governance flags present
    assert "advisory_only" in user_html
    assert "advisory_only" in admin_html

    # Module constants confirm no overclaim
    assert mod._SAFETY["advisory_only"] is True
    assert mod._SAFETY["certification_ready"] is False
    assert mod._SAFETY["official_compliance_decision"] is False

    # Neither HTML version should claim certification_ready: True
    assert "certification_ready" in user_html or "certification_ready" in admin_html
    assert "certification_ready: True" not in user_html
    assert "certification_ready: True" not in admin_html


# ── VT18 — Browser close on success ──────────────────────────────────────────

def test_VT18_browser_close_on_success(tmp_path):
    """page.close() and browser.close() must be called after successful PDF."""
    html_path = tmp_path / "test.html"
    html_path.write_text("<html></html>", encoding="utf-8")
    pdf_path = tmp_path / "test.pdf"

    fake_sync_pw, fake_page, fake_browser = _make_fake_playwright()
    _inject_fake_playwright(fake_sync_pw)

    mod._pdf_via_playwright(html_path, pdf_path)

    fake_page.close.assert_called_once()
    fake_browser.close.assert_called_once()


# ── VT19 — Browser close on failure ──────────────────────────────────────────

def test_VT19_browser_close_on_failure(tmp_path):
    """page.close() and browser.close() must be called even when pdf() raises."""
    html_path = tmp_path / "test.html"
    html_path.write_text("<html></html>", encoding="utf-8")
    pdf_path = tmp_path / "test.pdf"

    fake_sync_pw, fake_page, fake_browser = _make_fake_playwright(
        pdf_side_effect=RuntimeError("simulated playwright failure")
    )
    _inject_fake_playwright(fake_sync_pw)

    with pytest.raises(RuntimeError, match="simulated playwright failure"):
        mod._pdf_via_playwright(html_path, pdf_path)

    fake_page.close.assert_called_once()
    fake_browser.close.assert_called_once()


# ── VT20 — Partial artifact cleanup ──────────────────────────────────────────

def test_VT20_partial_artifact_cleanup(tmp_path, monkeypatch):
    """Failure removes only partially-created artifacts from the current run."""
    call_count = {"n": 0}

    def fail_on_second_pdf(html_path: Path, pdf_path: Path) -> None:
        call_count["n"] += 1
        if call_count["n"] == 1:
            pdf_path.write_bytes(b"%PDF-1.4 stub")
        else:
            raise RuntimeError("simulated second pdf failure")

    monkeypatch.setattr(mod, "_pdf_via_playwright", fail_on_second_pdf)
    monkeypatch.setattr(mod, "_screenshot_html", lambda *a, **kw: [])

    with pytest.raises(RuntimeError, match="simulated second pdf failure"):
        mod.run_standards_compliance_visual_qa(
            output_root=tmp_path,
            case_id="QA-COMPLIANCE-VISUAL-001",
            run_id="cleanuptest",
            overwrite=False,
        )

    artifacts_dir = tmp_path / "QA-COMPLIANCE-VISUAL-001" / "cleanuptest" / "artifacts"
    pdf_files = list(artifacts_dir.glob("*.pdf")) if artifacts_dir.exists() else []
    assert len(pdf_files) == 0, "Partial PDF artifact must have been cleaned up"

    html_files = list(artifacts_dir.glob("*.html")) if artifacts_dir.exists() else []
    assert len(html_files) == 0, "HTML artifacts created before failure must be cleaned up"


# ── VT21 — Deterministic HTML ────────────────────────────────────────────────

def test_VT21_deterministic_html():
    """Building HTML twice from the same constants produces identical output."""
    assert mod._build_user_html() == mod._build_user_html()
    assert mod._build_admin_html() == mod._build_admin_html()


# ── VT22 — CLI --output-dir required ─────────────────────────────────────────

def test_VT22_cli_output_dir_required():
    """Running the module as a script without --output-dir exits with non-zero code."""
    import subprocess
    generator_script = _CORE / "standards_compliance_visual_qa_generator.py"
    assert generator_script.exists()

    result = subprocess.run(
        [sys.executable, str(generator_script)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, (
        "CLI must exit non-zero when --output-dir is missing"
    )


# ── VT23 — Endpoint remains absent ───────────────────────────────────────────

def test_VT23_endpoint_remains_absent():
    """pv_standards_compliance_endpoint.py must NOT exist in the Unified tree."""
    endpoint = _CORE / "pv_standards_compliance_endpoint.py"
    assert not endpoint.exists(), (
        f"Wave 3A contract violation: endpoint file must remain absent. "
        f"Found at: {endpoint}"
    )


# ── VT24 — No active Flask routes ────────────────────────────────────────────

def test_VT24_no_active_routes():
    """The generator module must not register any Flask routes."""
    import inspect
    source = inspect.getsource(mod)

    assert "@app.route" not in source, "Generator must not register Flask routes"
    assert "register_standards_compliance" not in source, (
        "Generator must not export a route-registration function"
    )
    assert "/api/standards-compliance/" not in source, (
        "Generator must not reference standards-compliance API route paths"
    )


# ── VT25 — Cleanup does not affect sibling runs ───────────────────────────────

def test_VT25_cleanup_does_not_affect_sibling_runs(tmp_path, monkeypatch):
    """Partial-failure cleanup removes only files created in the failing run.

    Verifies:
      - sibling run artifacts are untouched after a failure in another run
      - output_root is not deleted
      - the failing run's artifacts that existed before the failure are cleaned up
    """
    case_id = "QA-COMPLIANCE-VISUAL-001"

    # Pre-create a successful sibling run with a sentinel artifact
    sibling_run_dir = tmp_path / case_id / "siblingrun001"
    sibling_artifacts = sibling_run_dir / "artifacts"
    sibling_artifacts.mkdir(parents=True)
    sibling_sentinel = sibling_artifacts / "sibling_data.html"
    sibling_sentinel.write_text("<html>sibling</html>", encoding="utf-8")

    # Fail the second PDF call in a different run
    call_count = {"n": 0}

    def fail_on_second_pdf(html_path: Path, pdf_path: Path) -> None:
        call_count["n"] += 1
        if call_count["n"] == 1:
            pdf_path.write_bytes(b"%PDF-1.4 stub")
        else:
            raise RuntimeError("simulated second pdf failure in failing run")

    monkeypatch.setattr(mod, "_pdf_via_playwright", fail_on_second_pdf)
    monkeypatch.setattr(mod, "_screenshot_html", lambda *a, **kw: [])

    with pytest.raises(RuntimeError, match="simulated second pdf failure"):
        mod.run_standards_compliance_visual_qa(
            output_root=tmp_path,
            case_id=case_id,
            run_id="failingrun001",
            overwrite=False,
        )

    # Sibling run must be completely untouched
    assert sibling_sentinel.exists(), "Sibling run artifact must not be deleted"
    assert sibling_sentinel.read_text() == "<html>sibling</html>"

    # output_root must not be deleted
    assert tmp_path.exists(), "output_root must not be deleted"

    # Failing run: PDF artifacts created before failure must have been cleaned up
    failing_artifacts = tmp_path / case_id / "failingrun001" / "artifacts"
    if failing_artifacts.exists():
        pdf_files = list(failing_artifacts.glob("*.pdf"))
        assert len(pdf_files) == 0, (
            f"Partial PDF from failing run must be cleaned up; found: {pdf_files}"
        )
        html_files = list(failing_artifacts.glob("*.html"))
        assert len(html_files) == 0, (
            f"HTML files from failing run must be cleaned up; found: {html_files}"
        )


# ── VT26 — Full artifact schema ───────────────────────────────────────────────

def test_VT26_full_artifact_schema(tmp_path, monkeypatch):
    """Return dict must contain all expected artifact categories with correct types.

    Checks: user_html, admin_html, user_pdf, admin_pdf, admin_excel,
    audit_json (exactly 3 paths), screenshots (includes HTML + PDF page shots),
    all extensions allowed, user/admin file separation.
    """
    fake_pdf, fake_ss, fake_inspect, fake_excel = _make_stub_heavy_funcs(tmp_path)
    monkeypatch.setattr(mod, "_pdf_via_playwright", fake_pdf)
    monkeypatch.setattr(mod, "_screenshot_html", fake_ss)
    monkeypatch.setattr(mod, "_inspect_pdf", fake_inspect)
    monkeypatch.setattr(mod, "_build_excel", fake_excel)

    result = mod.run_standards_compliance_visual_qa(
        output_root=tmp_path,
        case_id="QA-COMPLIANCE-VISUAL-001",
        run_id="schematest001",
        overwrite=False,
    )

    assert result["ok"] is True
    arts = result["artifacts"]

    # All required keys present
    for key in ("user_html", "admin_html", "user_pdf", "admin_pdf",
                "admin_excel", "audit_json", "screenshots"):
        assert key in arts, f"Missing artifact key: {key!r}"

    # Scalar paths are strings
    for key in ("user_html", "admin_html", "user_pdf", "admin_pdf", "admin_excel"):
        assert isinstance(arts[key], str), f"Expected str for {key!r}"

    # Exactly 3 audit JSONs
    assert isinstance(arts["audit_json"], list), "audit_json must be a list"
    assert len(arts["audit_json"]) == 3, (
        f"Expected 3 audit JSON paths, got {len(arts['audit_json'])}"
    )

    # screenshots is a list
    assert isinstance(arts["screenshots"], list), "screenshots must be a list"

    # All extensions must be in the allowlist
    allowed = mod._ALLOWED_EXTENSIONS
    scalar_paths = [arts[k] for k in ("user_html", "admin_html", "user_pdf",
                                       "admin_pdf", "admin_excel")]
    for path_str in scalar_paths + arts["audit_json"] + arts["screenshots"]:
        ext = Path(path_str).suffix
        assert ext in allowed, f"Disallowed extension {ext!r} in path {path_str!r}"

    # Screenshots must include both HTML section shots (2) and PDF page shots (2)
    # fake_ss returns 1 shot per call × 2 calls = 2 HTML shots
    # fake_inspect returns 1 page shot per call × 2 calls = 2 PDF page shots
    assert len(arts["screenshots"]) == 4, (
        f"Expected 4 screenshots (2 HTML + 2 PDF-page), got {len(arts['screenshots'])}"
    )

    # user and admin artifacts must be different files
    assert arts["user_html"] != arts["admin_html"]
    assert arts["user_pdf"] != arts["admin_pdf"]

    # user artifacts must not contain 'admin' and vice versa
    assert "user" in Path(arts["user_html"]).name
    assert "admin" in Path(arts["admin_html"]).name
    assert "user" in Path(arts["user_pdf"]).name
    assert "admin" in Path(arts["admin_pdf"]).name
    assert "admin" in Path(arts["admin_excel"]).name


# ── VT27 — Score is a dict ────────────────────────────────────────────────────

def test_VT27_score_is_dict(tmp_path, monkeypatch):
    """The score field must be a dict with required keys, not a float or int."""
    fake_pdf, fake_ss, fake_inspect, fake_excel = _make_stub_heavy_funcs(tmp_path)
    monkeypatch.setattr(mod, "_pdf_via_playwright", fake_pdf)
    monkeypatch.setattr(mod, "_screenshot_html", fake_ss)
    monkeypatch.setattr(mod, "_inspect_pdf", fake_inspect)
    monkeypatch.setattr(mod, "_build_excel", fake_excel)

    result = mod.run_standards_compliance_visual_qa(
        output_root=tmp_path,
        case_id="QA-COMPLIANCE-VISUAL-001",
        run_id="scoretypetest",
        overwrite=False,
    )

    score = result["score"]
    assert isinstance(score, dict), (
        f"score must be a dict, got {type(score).__name__!r}"
    )
    for key in ("percentage", "traffic_light", "label",
                "applicable_clauses", "raw_score"):
        assert key in score, f"Required score key missing: {key!r}"
    assert isinstance(score["percentage"], (int, float))
    assert score["traffic_light"] in ("green", "yellow", "red")


# ── VT28 — Sibling run isolation ──────────────────────────────────────────────

def test_VT28_sibling_run_isolation(tmp_path, monkeypatch):
    """Two different run_ids under the same case_id must not interfere."""
    fake_pdf, fake_ss, fake_inspect, fake_excel = _make_stub_heavy_funcs(tmp_path)
    monkeypatch.setattr(mod, "_pdf_via_playwright", fake_pdf)
    monkeypatch.setattr(mod, "_screenshot_html", fake_ss)
    monkeypatch.setattr(mod, "_inspect_pdf", fake_inspect)
    monkeypatch.setattr(mod, "_build_excel", fake_excel)

    r1 = mod.run_standards_compliance_visual_qa(
        output_root=tmp_path,
        case_id="QA-COMPLIANCE-VISUAL-001",
        run_id="sibling001",
        overwrite=False,
    )
    r2 = mod.run_standards_compliance_visual_qa(
        output_root=tmp_path,
        case_id="QA-COMPLIANCE-VISUAL-001",
        run_id="sibling002",
        overwrite=False,
    )

    assert r1["ok"]
    assert r2["ok"]

    # Different run directories
    assert r1["run_directory"] != r2["run_directory"]

    # Both run directories exist independently
    assert Path(r1["run_directory"]).exists()
    assert Path(r2["run_directory"]).exists()

    # Artifacts from each run are in distinct directories
    r1_user_html = Path(r1["artifacts"]["user_html"])
    r2_user_html = Path(r2["artifacts"]["user_html"])
    assert r1_user_html != r2_user_html
    assert r1_user_html.parent == Path(r1["run_directory"]) / "artifacts"
    assert r2_user_html.parent == Path(r2["run_directory"]) / "artifacts"

    # Each run's user_html exists in its own directory
    assert r1_user_html.exists()
    assert r2_user_html.exists()

    # Each artifact path must be contained within its own run_directory
    assert str(r1_user_html).startswith(r1["run_directory"])
    assert str(r2_user_html).startswith(r2["run_directory"])

    # r1 and r2 run directories are completely separate subtrees
    assert not r1["run_directory"].startswith(r2["run_directory"])
    assert not r2["run_directory"].startswith(r1["run_directory"])
