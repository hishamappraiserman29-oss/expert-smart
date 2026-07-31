"""
quality_checker.py — D-03/D-04/D-05: enforces QR-001 → QR-016.
Loads contract/quality_rules.json at import time.

GOVERNANCE (preserved invariants):
  - Isolation Forest (QR-012): flag_for_review ONLY — auto_delete=False
  - Z-score (QR-013): flag_for_review ONLY — auto_delete=False
  - transaction_price: NEVER statistically imputed (D-04)
  - city / coordinates: NEVER statistically imputed (D-04)
"""
from __future__ import annotations

import datetime
import json
import pathlib
from typing import Any, Dict, List, Optional

_CONTRACT_PATH = (
    pathlib.Path(__file__).parent / "contract" / "quality_rules.json"
)


def _load_contract() -> Dict[str, Any]:
    with _CONTRACT_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


_CONTRACT = _load_contract()

_ACTION_SEVERITY: Dict[str, int] = {
    "pass":                   0,
    "warn":                   1,
    "normalise_and_continue": 1,
    "flag_out_of_window":     2,
    "flag_for_review":        3,
    "exclude":                4,
    "reject":                 5,
}

# Saudi Arabia bounding box (QR-008)
_SA_LAT_MIN, _SA_LAT_MAX = 16.3, 32.2
_SA_LON_MIN, _SA_LON_MAX = 34.5, 55.7

# Default max built/land floor ratios by property type (QR-010)
_MAX_FLOOR_RATIO: Dict[str, float] = {
    "residential": 4.0,
    "commercial":  10.0,
    "mixed_use":   10.0,
    "industrial":   3.0,
    "hotel":        15.0,
    "office":       10.0,
    "default":      10.0,
}

# Minimum plausible SAR price per property type (QR-014)
_MIN_PLAUSIBLE_SAR: Dict[str, float] = {
    "residential": 50_000.0,
    "commercial":  100_000.0,
    "land":        10_000.0,
    "default":      5_000.0,
}

_REQUIRED_FIELDS = [
    "property_id", "property_type", "transaction_date",
    "transaction_price", "land_area_m2",
]


class RuleViolation:
    __slots__ = ("rule_id", "name", "action", "fields_affected", "detail")

    def __init__(
        self,
        rule_id: str,
        name: str,
        action: str,
        fields_affected: List[str],
        detail: str = "",
    ) -> None:
        self.rule_id = rule_id
        self.name = name
        self.action = action
        self.fields_affected = fields_affected
        self.detail = detail

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id":         self.rule_id,
            "name":            self.name,
            "action":          self.action,
            "fields_affected": self.fields_affected,
            "detail":          self.detail,
        }


class QualityResult:
    """Result of checking a single record against all applicable quality rules."""

    def __init__(
        self,
        property_id: Optional[str],
        violations: List[RuleViolation],
    ) -> None:
        self.property_id = property_id
        self.violations = violations

    @property
    def action(self) -> str:
        """The most severe gate action triggered; 'pass' if no violations."""
        if not self.violations:
            return "pass"
        return max(
            (v.action for v in self.violations),
            key=lambda a: _ACTION_SEVERITY.get(a, 0),
        )

    @property
    def review_required(self) -> bool:
        return any(
            v.action in ("flag_for_review", "flag_out_of_window")
            for v in self.violations
        )

    @property
    def rejected(self) -> bool:
        return self.action == "reject"

    @property
    def quality_flags(self) -> List[str]:
        return [v.rule_id for v in self.violations]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "property_id":    self.property_id,
            "action":         self.action,
            "review_required": self.review_required,
            "rejected":       self.rejected,
            "quality_flags":  self.quality_flags,
            "violations":     [v.to_dict() for v in self.violations],
        }


# ---------------------------------------------------------------------------
# Individual rule implementations
# ---------------------------------------------------------------------------

def _qr001_missing_required(record: Dict[str, Any]) -> Optional[RuleViolation]:
    missing = [f for f in _REQUIRED_FIELDS if not record.get(f)]
    if not missing:
        return None
    return RuleViolation(
        "QR-001", "missing_required_field", "reject",
        missing,
        f"Missing required fields: {missing}",
    )


def _qr004_zero_or_negative_price(record: Dict[str, Any]) -> Optional[RuleViolation]:
    price = record.get("transaction_price")
    if price is None:
        return None  # covered by QR-001
    try:
        p = float(price)
    except (TypeError, ValueError):
        return RuleViolation(
            "QR-004", "zero_or_negative_price", "reject",
            ["transaction_price"],
            f"Non-numeric transaction_price: {price!r}",
        )
    if p <= 0 or p < 1000:
        return RuleViolation(
            "QR-004", "zero_or_negative_price", "reject",
            ["transaction_price"],
            f"transaction_price={p} is zero, negative, or below 1000 SAR",
        )
    return None


def _qr005_zero_or_negative_area(record: Dict[str, Any]) -> Optional[RuleViolation]:
    area = record.get("land_area_m2")
    if area is None:
        return None  # covered by QR-001
    try:
        a = float(area)
    except (TypeError, ValueError):
        return RuleViolation(
            "QR-005", "zero_or_negative_area", "reject",
            ["land_area_m2"],
            f"Non-numeric land_area_m2: {area!r}",
        )
    if a <= 0:
        return RuleViolation(
            "QR-005", "zero_or_negative_area", "reject",
            ["land_area_m2"],
            f"land_area_m2={a} must be > 0",
        )
    bua = record.get("built_up_area_m2")
    if bua is not None:
        try:
            b = float(bua)
            if b <= 0:
                return RuleViolation(
                    "QR-005", "zero_or_negative_area", "reject",
                    ["built_up_area_m2"],
                    f"built_up_area_m2={b} must be > 0",
                )
        except (TypeError, ValueError):
            pass
    return None


def _qr006_future_date(
    record: Dict[str, Any],
    today: datetime.date,
) -> Optional[RuleViolation]:
    raw = record.get("transaction_date")
    if not raw:
        return None
    try:
        td = datetime.date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None
    if td > today:
        return RuleViolation(
            "QR-006", "future_transaction_date", "reject",
            ["transaction_date"],
            f"transaction_date={td} is after today ({today})",
        )
    return None


def _qr007_outside_lookback(
    record: Dict[str, Any],
    today: datetime.date,
    lookback_months: int,
) -> Optional[RuleViolation]:
    raw = record.get("transaction_date")
    if not raw:
        return None
    try:
        td = datetime.date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None
    cutoff_year = today.year - (lookback_months // 12)
    cutoff_month = today.month - (lookback_months % 12)
    if cutoff_month <= 0:
        cutoff_year -= 1
        cutoff_month += 12
    cutoff = datetime.date(cutoff_year, cutoff_month, 1)
    if td < cutoff:
        return RuleViolation(
            "QR-007", "outside_lookback_window", "flag_out_of_window",
            ["transaction_date"],
            f"transaction_date={td} is before lookback cutoff {cutoff}",
        )
    return None


def _get_coords(record: Dict[str, Any]):
    """Return (lat, lon) from flat or nested coordinates; each may be None.
    Uses explicit None checks so that 0.0 is not treated as absent."""
    lat = record.get("latitude")
    if lat is None:
        lat = (record.get("coordinates") or {}).get("latitude")
    lon = record.get("longitude")
    if lon is None:
        lon = (record.get("coordinates") or {}).get("longitude")
    return lat, lon


def _qr008_coordinates_outside_sa(record: Dict[str, Any]) -> Optional[RuleViolation]:
    lat, lon = _get_coords(record)
    if lat is None and lon is None:
        return None
    try:
        lat_f, lon_f = float(lat), float(lon)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if (
        lat_f < _SA_LAT_MIN or lat_f > _SA_LAT_MAX
        or lon_f < _SA_LON_MIN or lon_f > _SA_LON_MAX
    ):
        return RuleViolation(
            "QR-008", "coordinates_outside_jurisdiction", "reject",
            ["coordinates"],
            f"lat={lat_f}, lon={lon_f} outside SA bounding box",
        )
    return None


def _qr009_partial_coordinates(record: Dict[str, Any]) -> Optional[RuleViolation]:
    lat, lon = _get_coords(record)
    if (lat is None) != (lon is None):
        return RuleViolation(
            "QR-009", "partial_coordinates", "reject",
            ["coordinates"],
            "Only one coordinate component provided; both required or both null",
        )
    return None


def _qr010_built_exceeds_land(record: Dict[str, Any]) -> Optional[RuleViolation]:
    bua = record.get("built_up_area_m2")
    land = record.get("land_area_m2")
    if bua is None or land is None:
        return None
    try:
        b, a = float(bua), float(land)
    except (TypeError, ValueError):
        return None
    if a <= 0:
        return None
    prop_type = str(record.get("property_type") or "default").lower()
    ratio = _MAX_FLOOR_RATIO.get(prop_type, _MAX_FLOOR_RATIO["default"])
    if b > a * ratio:
        return RuleViolation(
            "QR-010", "built_area_exceeds_land_area_beyond_threshold", "flag_for_review",
            ["built_up_area_m2", "land_area_m2", "property_type"],
            f"built_up_area_m2={b} > land_area_m2={a} × {ratio}",
        )
    return None


def _qr011_rentable_exceeds_built(record: Dict[str, Any]) -> Optional[RuleViolation]:
    rent = record.get("rentable_area_m2")
    bua = record.get("built_up_area_m2")
    if rent is None or bua is None:
        return None
    try:
        r, b = float(rent), float(bua)
    except (TypeError, ValueError):
        return None
    if r > b:
        return RuleViolation(
            "QR-011", "rentable_area_exceeds_built_area", "flag_for_review",
            ["rentable_area_m2", "built_up_area_m2"],
            f"rentable_area_m2={r} > built_up_area_m2={b}",
        )
    return None


def _qr012_isolation_forest_flag(
    record: Dict[str, Any],
    isolation_forest_score: Optional[float],
    contamination_threshold: float = 0.05,
) -> Optional[RuleViolation]:
    """
    D-05 GOVERNANCE: Isolation Forest = flag_for_review ONLY.
    auto_delete=False per anomaly_detection_governance in quality_rules.json.
    Score is injected by the caller — the checker never deletes records.
    """
    if isolation_forest_score is None:
        return None
    if isolation_forest_score < contamination_threshold:
        return RuleViolation(
            "QR-012", "price_per_sqm_outlier_isolation_forest", "flag_for_review",
            ["transaction_price", "land_area_m2", "property_type", "city"],
            f"Isolation Forest score={isolation_forest_score:.4f} < threshold={contamination_threshold}",
        )
    return None


def _qr013_zscore_flag(
    record: Dict[str, Any],
    z_score: Optional[float],
    threshold: float = 3.0,
) -> Optional[RuleViolation]:
    """
    D-05 GOVERNANCE: Z-score outlier = flag_for_review ONLY.
    auto_delete=False per anomaly_detection_governance in quality_rules.json.
    """
    if z_score is None:
        return None
    if abs(z_score) > threshold:
        return RuleViolation(
            "QR-013", "price_per_sqm_outlier_zscore", "flag_for_review",
            ["transaction_price", "land_area_m2"],
            f"Z-score={z_score:.4f} exceeds threshold={threshold}",
        )
    return None


def _qr014_currency_ambiguity(record: Dict[str, Any]) -> Optional[RuleViolation]:
    price = record.get("transaction_price")
    if price is None:
        return None
    try:
        p = float(price)
    except (TypeError, ValueError):
        return None
    if p <= 0:
        return None
    prop_type = str(record.get("property_type") or "default").lower()
    min_sar = _MIN_PLAUSIBLE_SAR.get(prop_type, _MIN_PLAUSIBLE_SAR["default"])
    if p < min_sar:
        return RuleViolation(
            "QR-014", "currency_unit_ambiguity", "flag_for_review",
            ["transaction_price"],
            f"transaction_price={p} < min_plausible_SAR={min_sar} for {prop_type!r}",
        )
    return None


def _qr015_location_both_missing(record: Dict[str, Any]) -> Optional[RuleViolation]:
    """
    D-04 GOVERNANCE: Location is NEVER statistically imputed.
    Flag when neither city nor coordinates are available.
    """
    city = record.get("city")
    lat, lon = _get_coords(record)
    if not city and (lat is None or lon is None):
        return RuleViolation(
            "QR-015", "location_fields_both_missing", "flag_for_review",
            ["city", "coordinates"],
            "Both city and coordinates are absent — location is never statistically imputed",
        )
    return None


def _qr016_non_arms_length(record: Dict[str, Any]) -> Optional[RuleViolation]:
    ev = str(record.get("evidence_type") or "").lower()
    if ev in ("manual_entry", "unknown", ""):
        if not record.get("source_documentation"):
            return RuleViolation(
                "QR-016", "non_arms_length_indicator", "flag_for_review",
                ["evidence_type"],
                f"evidence_type={ev!r} with no source_documentation",
            )
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_record(
    record: Dict[str, Any],
    today: Optional[datetime.date] = None,
    lookback_months: int = 36,
    isolation_forest_score: Optional[float] = None,
    z_score: Optional[float] = None,
) -> QualityResult:
    """
    Run all applicable per-record quality rules (QR-001 → QR-016).
    Anomaly scores for QR-012/QR-013 are optional; pass them if computed externally.
    Missing fields are documented — never imputed.
    """
    if today is None:
        today = datetime.date.today()

    pid = record.get("property_id")
    violations: List[RuleViolation] = []

    def _add(v: Optional[RuleViolation]) -> None:
        if v is not None:
            violations.append(v)

    _add(_qr001_missing_required(record))
    _add(_qr004_zero_or_negative_price(record))
    _add(_qr005_zero_or_negative_area(record))
    _add(_qr006_future_date(record, today))
    _add(_qr007_outside_lookback(record, today, lookback_months))
    _add(_qr008_coordinates_outside_sa(record))
    _add(_qr009_partial_coordinates(record))
    _add(_qr010_built_exceeds_land(record))
    _add(_qr011_rentable_exceeds_built(record))
    _add(_qr012_isolation_forest_flag(record, isolation_forest_score))
    _add(_qr013_zscore_flag(record, z_score))
    _add(_qr014_currency_ambiguity(record))
    _add(_qr015_location_both_missing(record))
    _add(_qr016_non_arms_length(record))

    return QualityResult(property_id=pid, violations=violations)


def check_batch(
    records: List[Dict[str, Any]],
    today: Optional[datetime.date] = None,
    lookback_months: int = 36,
) -> List[QualityResult]:
    """
    Run per-record checks plus QR-002 (duplicate property_id within batch).
    """
    if today is None:
        today = datetime.date.today()

    results = [
        check_record(r, today=today, lookback_months=lookback_months)
        for r in records
    ]

    # QR-002: count property_id occurrences in the batch
    pid_count: Dict[str, int] = {}
    for r in records:
        pid = str(r.get("property_id") or "")
        if pid:
            pid_count[pid] = pid_count.get(pid, 0) + 1

    for qr, r in zip(results, records):
        pid = str(r.get("property_id") or "")
        if pid and pid_count.get(pid, 0) > 1:
            qr.violations.append(
                RuleViolation(
                    "QR-002", "duplicate_property_id", "flag_for_review",
                    ["property_id"],
                    f"property_id={pid!r} appears {pid_count[pid]} times in batch",
                )
            )

    return results
