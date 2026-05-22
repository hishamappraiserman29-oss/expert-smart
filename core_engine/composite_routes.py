"""
Composite valuation endpoint — Wave 4 of the Composite Property
Architecture. Wires CompositeValidator → CompositeEngine →
PurposeComplianceAdapter into one stateless request path.

Stateless: NO database, NO persistence.

Registration: call register(app, require_auth) once from bridge_api.py.
require_auth is passed explicitly to avoid a circular import (it is
defined inside bridge_api.py itself).
"""
from __future__ import annotations

import dataclasses
import enum
from typing import Any

from flask import jsonify, request

from valuation_engines.composite_engine import ASSET_TYPES, CompositeEngine, CompositeEngineError
from valuation_engines.composite_aggregator import aggregate as _aggregate, CompositeAggregatorError
from valuation_engines.composite_reporter import build_reporting_blocks as _build_reporting
from adapters.purpose_adapter import PURPOSE_RULES, PurposeComplianceAdapter, PurposeAdapterError
from validation.composite_rules import CompositeValidator

COMPOSITE_API_VERSION = 1

_engine    = CompositeEngine()
_adapter   = PurposeComplianceAdapter()
_validator = CompositeValidator()


def _jsonify_obj(obj: Any) -> Any:
    """JSON-safe recursive conversion.

    Serializes the frozen Wave 1-3 dataclasses here — those classes have
    no to_dict and are NOT modified.
    """
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _jsonify_obj(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, enum.Enum):
        return obj.value
    if isinstance(obj, (list, tuple)):
        return [_jsonify_obj(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _jsonify_obj(v) for k, v in obj.items()}
    return obj


def _type_name(typ: type) -> str:
    """Serialize a Python type object to a stable string name."""
    return getattr(typ, "__name__", str(typ))


def _build_schema_payload() -> dict:
    """Build the composite schema from the single-source-of-truth catalogs.

    Does NOT redeclare ASSET_TYPES or PURPOSE_RULES.
    """
    asset_types = [
        {
            "name": type_name,
            "attributes": [
                {"name": attr, "type": _type_name(typ)}
                for attr, typ in attr_spec.items()
            ],
        }
        for type_name, attr_spec in ASSET_TYPES.items()
    ]
    purposes = [
        {
            "name": name,
            "multiplier": float(rule["multiplier"]),
            "deep": bool(rule.get("deep", False)),
        }
        for name, rule in PURPOSE_RULES.items()
    ]
    return {
        "composite_api_version": COMPOSITE_API_VERSION,
        "asset_types": asset_types,
        "purposes": purposes,
    }


def register(app, require_auth) -> None:
    """Register composite routes on *app*.

    Routes registered:
      POST /api/valuation/composite        — Wave 4 value endpoint
      GET  /api/valuation/composite/schema — Wave 5a schema endpoint

    Called once from bridge_api.py with its own require_auth.
    """

    @app.route("/api/valuation/composite", methods=["POST"])
    @require_auth
    def composite_value():
        # ── 1. Parse JSON body ────────────────────────────────────────
        data = request.get_json(force=True, silent=True)
        if data is None:
            return jsonify({
                "status": "error",
                "message": "Request body must be valid JSON",
            }), 400

        if "components" not in data:
            return jsonify({
                "status": "error",
                "message": "Missing required field: 'components'",
            }), 400
        if "purposes" not in data:
            return jsonify({
                "status": "error",
                "message": "Missing required field: 'purposes'",
            }), 400

        components = data["components"]
        purposes_raw = data["purposes"]

        if not isinstance(components, list):
            return jsonify({
                "status": "error",
                "message": "'components' must be a list",
            }), 400

        # ── 2. Purpose broadcast: one string → same for all ───────────
        if isinstance(purposes_raw, str):
            purposes = [purposes_raw] * len(components)
        elif isinstance(purposes_raw, list):
            purposes = purposes_raw
        else:
            return jsonify({
                "status": "error",
                "message": "'purposes' must be a string or a list of strings",
            }), 400

        # ── 3. Length guard ───────────────────────────────────────────
        if len(components) != len(purposes):
            return jsonify({
                "status": "error",
                "message": (
                    f"'purposes' length ({len(purposes)}) must match "
                    f"'components' length ({len(components)})"
                ),
            }), 422

        # ── 4. Wave 3: validate ───────────────────────────────────────
        try:
            report = _validator.validate(components, purposes)
        except Exception as exc:
            return jsonify({
                "status": "error",
                "message": f"Validation call failed: {exc}",
            }), 400

        validation_payload = {
            "is_blocking": report.is_blocking,
            "blocking_count": report.blocking_count,
            "advisory_count": report.advisory_count,
            "issues": [
                {
                    "severity": issue.severity.value.lower(),
                    "code": issue.code,
                    "component_index": issue.component_index,
                    "field": issue.field,
                    "message": issue.message,
                }
                for issue in report.issues
            ],
        }

        if report.is_blocking:
            return jsonify({
                "composite_api_version": COMPOSITE_API_VERSION,
                "status": "rejected",
                "validation": validation_payload,
            }), 422

        # ── 5. Wave 1: compute baselines ─────────────────────────────
        try:
            valuations = _engine.value_all(components)
        except CompositeEngineError as exc:
            return jsonify({
                "status": "error",
                "code": "POST_VALIDATION_ENGINE_ERROR",
                "message": str(exc),
            }), 422

        # ── 6. Wave 2: apply purposes ─────────────────────────────────
        try:
            adjusted = _adapter.adapt_all(valuations, purposes)
        except PurposeAdapterError as exc:
            return jsonify({
                "status": "error",
                "code": "POST_VALIDATION_ENGINE_ERROR",
                "message": str(exc),
            }), 422

        # ── 7. Read optional synergy (Wave 7A) ───────────────────────
        synergy_pct = data.get("synergy_adjustment_percent", 0.0)
        if isinstance(synergy_pct, bool) or not isinstance(synergy_pct, (int, float)):
            return jsonify({
                "status": "error",
                "message": "'synergy_adjustment_percent' must be a number",
            }), 422

        # ── 8. Aggregate (Wave 7A) ────────────────────────────────────
        try:
            agg = _aggregate(adjusted, synergy_adjustment_percent=synergy_pct)
        except CompositeAggregatorError as exc:
            return jsonify({
                "status": "error",
                "message": str(exc),
            }), 422

        # ── 9. Reporting blocks (Wave 7B) ─────────────────────────────
        reporting = _build_reporting(adjusted)

        return jsonify({
            "composite_api_version": COMPOSITE_API_VERSION,
            "status": "ok",
            "validation": validation_payload,
            "components": [_jsonify_obj(a) for a in adjusted],
            "summary": {
                "component_count": len(adjusted),
                "total_baseline_value": agg.total_baseline,
                "total_adjusted_value": agg.total_adjusted_before_synergy,
                "note": (
                    "totals are a NAIVE sum — synergy / portfolio aggregation "
                    "is applied in Wave 7, not here."
                ),
            },
            "aggregation": {
                "total_baseline": agg.total_baseline,
                "total_adjusted_before_synergy": agg.total_adjusted_before_synergy,
                "synergy_adjustment_percent": agg.synergy_adjustment_percent,
                "synergy_adjustment_amount": agg.synergy_adjustment_amount,
                "total_adjusted_after_synergy": agg.total_adjusted_after_synergy,
            },
            "uspap_reporting": reporting["uspap_reporting"],
            "iaao_reporting": reporting["iaao_reporting"],
        }), 200

    # ── Wave 5a — schema endpoint ─────────────────────────────────────

    @app.route("/api/valuation/composite/schema", methods=["GET"])
    @require_auth
    def composite_schema():
        return jsonify(_build_schema_payload()), 200
