import json
from decimal import Decimal
from pathlib import Path
from typing import Optional

from .base import (
    EngineResult, AuditEntry, ValidationIssue, ValuationEngine,
)

# Hardcoded defaults used when cost_tables.json is missing or corrupt
_DEFAULT_COST_TABLES: dict = {
    "Cairo":      {"economy": 8000,  "standard": 14000, "luxury": 25000},
    "Giza":       {"economy": 7500,  "standard": 13000, "luxury": 23000},
    "Alexandria": {"economy": 7000,  "standard": 12000, "luxury": 20000},
    "_default":   {"economy": 6500,  "standard": 11000, "luxury": 18000},
}

_VALID_QUALITIES = {"economy", "standard", "luxury"}


class CostEngine(ValuationEngine):
    """
    Cost Approach (Replacement Cost Method) engine — Phase 4 v1.

    Formula:
        Value = (Cost_Per_Sqm × Building_Area) × (1 − Depreciation%) + Land_Value
    """

    name    = "cost"
    version = "1.0.0"

    def __init__(self, cost_tables_path: str = "core_engine/engines/cost_tables.json"):
        self.cost_tables: dict = {}
        try:
            with Path(cost_tables_path).open(encoding="utf-8") as f:
                self.cost_tables = json.load(f)
        except FileNotFoundError:
            print(f"[CostEngine] Warning: {cost_tables_path} not found — using built-in defaults")
            self.cost_tables = dict(_DEFAULT_COST_TABLES)
        except json.JSONDecodeError as e:
            print(f"[CostEngine] Warning: JSON parse error — {e} — using built-in defaults")
            self.cost_tables = dict(_DEFAULT_COST_TABLES)

        # Straight-line economic life (years) per quality grade
        self.economic_life: dict[str, int] = {
            "economy":  40,
            "standard": 60,
            "luxury":   80,
        }

    # ──────────────────────────────────────────────────────────────────
    # Abstract method implementations
    # ──────────────────────────────────────────────────────────────────

    def validate(self, inputs: dict) -> list[ValidationIssue]:
        """Check inputs before calculation. Returns list of issues (empty = OK)."""
        issues: list[ValidationIssue] = []

        building_area = inputs.get("building_area_sqm", 0) or 0
        if building_area <= 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_BUILDING_AREA",
                message=f"building_area_sqm must be > 0; got {building_area}",
            ))

        age = inputs.get("building_age_years")
        if age is not None and age < 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_AGE",
                message=f"building_age_years must be >= 0; got {age}",
            ))

        quality = inputs.get("construction_quality", "")
        if quality not in _VALID_QUALITIES:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_QUALITY",
                message=f"construction_quality must be one of {sorted(_VALID_QUALITIES)}; got '{quality}'",
            ))

        land_value = inputs.get("land_value_egp", 0) or 0
        if land_value < 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_LAND_VALUE",
                message=f"land_value_egp must be >= 0; got {land_value}",
            ))

        # Warnings — only when no hard errors on quality/age so we can look them up
        if age is not None and age >= 0 and quality in _VALID_QUALITIES:
            econ_life = self.economic_life[quality]
            if age >= econ_life:
                issues.append(ValidationIssue(
                    severity="warning",
                    code="FULLY_DEPRECIATED",
                    message=(
                        f"Building age ({age} yrs) >= economic life ({econ_life} yrs); "
                        "fully depreciated — value is land only"
                    ),
                ))

        governorate = inputs.get("governorate", "_default")
        if governorate and governorate not in self.cost_tables:
            issues.append(ValidationIssue(
                severity="warning",
                code="UNKNOWN_GOVERNORATE",
                message=f"Governorate '{governorate}' not in cost tables; using default rates",
            ))

        return issues

    def calculate(self, inputs: dict) -> EngineResult:
        """Replacement Cost − Depreciation + Land Value → EngineResult."""
        issues = self.validate(inputs)
        errors = [i for i in issues if i.severity == "error"]

        if errors:
            return EngineResult(
                engine_name=self.name,
                value=None,
                confidence="insufficient",
                audit_trail=[],
                issues=issues,
                metadata={},
            )

        building_area = float(inputs["building_area_sqm"])
        age           = float(inputs.get("building_age_years", 0) or 0)
        quality       = inputs["construction_quality"]
        governorate   = inputs.get("governorate", "_default") or "_default"
        land_value    = float(inputs.get("land_value_egp", 0) or 0)
        custom_cost   = inputs.get("custom_cost_per_sqm")

        audit_trail: list[AuditEntry] = []

        # ── Step 1: Cost per sqm ──────────────────────────────────────
        cost_per_sqm = (
            float(custom_cost)
            if custom_cost is not None
            else self._get_cost_per_sqm(governorate, quality)
        )
        source_label = "custom override" if custom_cost is not None else f"{governorate}/{quality}"
        audit_trail.append(AuditEntry(
            step_name="Get cost per sqm from cost tables",
            inputs={"governorate": governorate, "quality": quality, "custom_override": custom_cost},
            outputs={"cost_per_sqm": cost_per_sqm, "source": source_label},
            formula="lookup cost_tables[governorate][quality]",
            references=["EGVS_4.1: Cost Approach", "Phase 4 Cost Engine v1.0"],
        ))

        # ── Step 2: Replacement Cost New (RCN) ───────────────────────
        rcn = cost_per_sqm * building_area
        audit_trail.append(AuditEntry(
            step_name="Calculate Replacement Cost New (RCN)",
            inputs={"cost_per_sqm": cost_per_sqm, "building_area_sqm": building_area},
            outputs={"rcn": round(rcn, 2)},
            formula="RCN = cost_per_sqm × building_area_sqm",
            references=["EGVS_4.2: Replacement Cost New"],
        ))

        # ── Step 3: Economic life ─────────────────────────────────────
        econ_life = self.economic_life[quality]
        audit_trail.append(AuditEntry(
            step_name="Get economic life by quality",
            inputs={"quality": quality},
            outputs={"economic_life_years": econ_life},
            formula="lookup economic_life[quality]",
            references=["EGVS_4.3: Economic Life Table"],
        ))

        # ── Step 4: Depreciation % ────────────────────────────────────
        depreciation_pct = min(age / econ_life, 1.0) if econ_life > 0 else 1.0
        audit_trail.append(AuditEntry(
            step_name="Calculate accumulated depreciation",
            inputs={"building_age_years": age, "economic_life_years": econ_life},
            outputs={"depreciation_pct": round(depreciation_pct * 100, 4)},
            formula="depreciation_pct = min(age / economic_life, 1.0)",
            references=["EGVS_4.4: Straight-Line Depreciation"],
        ))

        # ── Step 5: Depreciated building cost ────────────────────────
        depreciated_cost = rcn * (1.0 - depreciation_pct)
        audit_trail.append(AuditEntry(
            step_name="Calculate depreciated building cost",
            inputs={"rcn": round(rcn, 2), "depreciation_pct": round(depreciation_pct * 100, 4)},
            outputs={"depreciated_cost": round(depreciated_cost, 2)},
            formula="depreciated_cost = RCN × (1 − depreciation_pct)",
            references=["EGVS_4.5: Accrued Depreciation"],
        ))

        # ── Step 6: Add land value ─────────────────────────────────────
        total_value = depreciated_cost + land_value
        audit_trail.append(AuditEntry(
            step_name="Add land value",
            inputs={"depreciated_cost": round(depreciated_cost, 2), "land_value_egp": land_value},
            outputs={"total_value": round(total_value, 2)},
            formula="total_value = depreciated_cost + land_value_egp",
            references=["EGVS_4.6: Land + Building Reconciliation", "Phase 4 Cost Engine v1.0"],
        ))

        # ── Step 7: Confidence ────────────────────────────────────────
        if age >= econ_life:
            confidence = "low"       # fully depreciated → high uncertainty
        elif age >= econ_life * 0.8:
            confidence = "medium"    # aging building
        elif land_value == 0:
            confidence = "low"       # unknown land value
        else:
            confidence = "high"

        metadata = {
            "rcn":                  round(rcn, 2),
            "rcn_per_sqm":          cost_per_sqm,
            "depreciation_pct":     round(depreciation_pct * 100, 4),
            "depreciated_cost":     round(depreciated_cost, 2),
            "land_value":           land_value,
            "depreciation_years":   age,
            "economic_life_years":  econ_life,
        }

        return EngineResult(
            engine_name=self.name,
            value=Decimal(str(round(total_value, 2))),
            confidence=confidence,
            audit_trail=audit_trail,
            issues=issues,
            metadata=metadata,
        )

    # ──────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────

    def _get_cost_per_sqm(self, governorate: str, quality: str) -> float:
        """Return EGP/sqm from cost tables, falling back to _default."""
        table = self.cost_tables.get(governorate) or self.cost_tables.get("_default", {})
        return float(table.get(quality, self.cost_tables["_default"][quality]))
