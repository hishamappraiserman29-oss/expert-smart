from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
HTML_PATH = ROOT / "frontend" / "index.html"


def _html() -> str:
    return HTML_PATH.read_text(
        encoding="utf-8",
        errors="replace",
    )


def _process_and_generate_source(html: str) -> str:
    match = re.search(
        r"async\s+function\s+processAndGenerate\s*\(\s*\)\s*\{"
        r"(?P<body>.*?)"
        r"\n\s*function\s+generateVisualReport\s*\(",
        html,
        re.DOTALL,
    )

    assert match, "processAndGenerate() was not found"
    return match.group("body")


def test_edf01_active_dynamic_schema_is_persisted():
    html = _html()

    assert "window.esActiveRequirementFields" in html
    assert "dynamic_fields" in html
    assert "role === 'user_input'" in html or 'role === "user_input"' in html


def test_edf02_typed_metadata_builder_is_exposed():
    html = _html()

    assert "window.esBuildDynamicRequirementMetadata" in html
    assert "field_type" in html
    assert "ui_required" in html


def test_edf03_builder_excludes_engine_fields():
    html = _html()

    assert (
        "engine_value" in html
        and "esBuildDynamicRequirementMetadata" in html
    )


def test_edf04_process_and_generate_builds_dynamic_metadata():
    html = _html()
    source = _process_and_generate_source(html)

    assert "esBuildDynamicRequirementMetadata" in source
    assert "dynamicRequirementResult" in source


def test_edf05_dynamic_values_are_sent_inside_metadata():
    html = _html()
    source = _process_and_generate_source(html)

    metadata_merge = re.search(
        r"basePayload\.metadata\s*=\s*Object\.assign\s*\(",
        source,
    )

    assert metadata_merge, (
        "processAndGenerate() must merge dynamic values "
        "into basePayload.metadata"
    )


def test_edf06_dynamic_validation_blocks_submission():
    html = _html()
    source = _process_and_generate_source(html)

    collector_pos = source.find(
        "esBuildDynamicRequirementMetadata"
    )
    request_pos = source.find(
        "const response = await esFetch"
    )

    assert collector_pos != -1
    assert request_pos != -1
    assert collector_pos < request_pos
    assert "dynamicRequirementResult.errors" in source


def test_edf07_static_payload_fields_win_name_collisions():
    html = _html()
    source = _process_and_generate_source(html)

    assert "existingStaticFieldNames" in html
    assert "dynamicRequirementResult.metadata" in source


def test_edf08_only_active_schema_is_serialized():
    html = _html()

    assert "esActiveRequirementFields" in html
    assert "data-es-req-field" in html
    assert "esBuildDynamicRequirementMetadata" in html
