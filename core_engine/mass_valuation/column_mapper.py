"""
column_mapper.py — D-02: maps import source columns to canonical field names.
Loads contract/column_mapping.json at import time; no external dependencies.
No statistical imputation — missing fields remain absent and are documented.
"""
from __future__ import annotations

import json
import pathlib
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

_CONTRACT_PATH = (
    pathlib.Path(__file__).parent / "contract" / "column_mapping.json"
)


def _load_contract() -> Dict[str, Any]:
    with _CONTRACT_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


_CONTRACT = _load_contract()
_CANONICAL_TO_DEF: Dict[str, Any] = _CONTRACT["canonical_to_aliases"]

# Reverse lookup: alias_lower → canonical_field
# Each canonical name is an implicit alias for itself (e.g. "land_area_m2" → "land_area_m2").
_ALIAS_TO_CANONICAL: Dict[str, str] = {}
for _canonical, _defn in _CANONICAL_TO_DEF.items():
    _ALIAS_TO_CANONICAL[_canonical.lower()] = _canonical  # self-alias
    for _alias in _defn.get("aliases", []):
        _ALIAS_TO_CANONICAL[_alias.lower()] = _canonical


class MappingResult:
    __slots__ = ("canonical", "unmapped_keys", "warnings")

    def __init__(
        self,
        canonical: Dict[str, Any],
        unmapped_keys: List[str],
        warnings: List[str],
    ) -> None:
        self.canonical = canonical
        self.unmapped_keys = unmapped_keys
        self.warnings = warnings


# ---------------------------------------------------------------------------
# Transform helpers
# ---------------------------------------------------------------------------

def _sanitise_control_chars(text: str) -> str:
    return "".join(
        ch for ch in text
        if not unicodedata.category(ch).startswith("C")
    )


def _to_float(value: Any) -> Optional[float]:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _apply_transform(
    canonical: str,
    defn: Dict[str, Any],
    raw: Any,
) -> Tuple[Any, Optional[str]]:
    """Return (transformed_value, optional_warning)."""
    transform = defn.get("transform", "")
    value_map: Optional[Dict[str, str]] = defn.get("value_map")
    value = raw

    if "strip_whitespace" in transform and value is not None:
        value = str(value).strip()

    if "sanitise_control_chars" in transform and isinstance(value, str):
        value = _sanitise_control_chars(value)

    if "to_string" in transform and value is not None:
        value = str(value).strip()

    if "to_float" in transform:
        value = _to_float(value)

    if "to_int" in transform and value is not None:
        try:
            value = int(float(value))
        except (TypeError, ValueError):
            value = None

    # lowercase before value_map so map keys can be lowercase
    if "lowercase" in transform and not "title_case" in transform:
        if isinstance(value, str):
            value = value.lower()

    if "title_case" in transform and isinstance(value, str):
        value = value.title()

    if value_map is not None and isinstance(value, str):
        mapped = value_map.get(value) or value_map.get(value.lower())
        if mapped is not None:
            value = mapped
        elif "unrecognised" in defn.get("notes", "").lower():
            value = "unknown"

    return value, None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def map_record(
    record: Dict[str, Any],
    source: str = "csv",
) -> MappingResult:
    """
    Map a single source record to canonical field names.

    Keys not found in any alias are collected in unmapped_keys.
    No statistical imputation is performed — missing fields remain absent.
    """
    canonical: Dict[str, Any] = {}
    unmapped_keys: List[str] = []
    warnings: List[str] = []

    for source_key, raw_value in record.items():
        lookup = source_key.lower().strip()
        canon = _ALIAS_TO_CANONICAL.get(lookup)

        if canon is None:
            unmapped_keys.append(source_key)
            continue

        defn = _CANONICAL_TO_DEF[canon]
        transformed, warn = _apply_transform(canon, defn, raw_value)
        if warn:
            warnings.append(warn)

        # coordinates.latitude / coordinates.longitude → nested dict
        if canon.startswith("coordinates."):
            sub = canon.split(".", 1)[1]
            coord = canonical.setdefault("coordinates", {})
            coord[sub] = transformed
        else:
            canonical[canon] = transformed

    return MappingResult(
        canonical=canonical,
        unmapped_keys=unmapped_keys,
        warnings=warnings,
    )


def resolve_canonical_name(source_key: str) -> Optional[str]:
    """Return the canonical field name for a source alias, or None."""
    return _ALIAS_TO_CANONICAL.get(source_key.lower().strip())


def canonical_fields() -> List[str]:
    """Return the list of all canonical field names defined in the contract."""
    return list(_CANONICAL_TO_DEF.keys())
