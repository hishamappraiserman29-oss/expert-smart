"""Sanity tests for docs/api/openapi.yaml."""
import pathlib

import yaml

SPEC_PATH = pathlib.Path(__file__).resolve().parent.parent.parent / "docs" / "api" / "openapi.yaml"


def test_openapi_yaml_parses():
    yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))


def test_openapi_version_3():
    data = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    assert data["openapi"].startswith("3.")


def test_has_required_paths():
    data = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    required = [
        "/api/valuation",
        "/api/reports",
        "/api/reports/{report_id}",
        "/api/reports/{report_id}/pdf",
    ]
    for p in required:
        assert p in data["paths"], f"missing path: {p}"


def test_required_schemas_defined():
    data = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    schemas = data.get("components", {}).get("schemas", {})
    for name in [
        "ValuationRequest",
        "ValuationResponse",
        "ReportRecord",
        "ValidationIssue",
        "Error",
    ]:
        assert name in schemas, f"missing schema: {name}"
