"""
DCF Engine — Discounted Cash Flow / Investment Analysis (IVS 105 / IFRS 13).

Computes Net Present Value (NPV) and Internal Rate of Return (IRR) for a
series of projected cash flows with an optional terminal value.

Formula:
    NPV = Σ(CF[t] / (1+r)^t  for t=0..n-1)  +  terminal_value / (1+r)^(n-1)

    where:
        CF[0]       = initial investment (typically negative)
        CF[1..n-1]  = periodic net cash flows
        terminal_value may be caller-supplied or derived as:
            terminal_value = CF[n-1] / terminal_cap_rate   (perpetuity)

IRR = r* such that NPV(r*) = 0
    Computed via bisection over [-0.99, 5.00] — pure stdlib, no scipy.
    Returns None if no real solution found in that range.

Safety:
    discount_rate ≤ -1  → error (division by zero in (1+r)^t)
    discount_rate = 0   → warning (no time-value discounting)
    terminal_cap_rate = 0 when used for TV derivation → error
"""

from decimal import Decimal
from typing import Optional

from .base import (
    EngineResult, AuditEntry, ValidationIssue, ValuationEngine,
)

_DISCOUNT_RATE_WARN_MIN: float = 0.05
_DISCOUNT_RATE_WARN_MAX: float = 0.30
_IRR_LO: float = -0.99
_IRR_HI: float = 5.00
_IRR_MAX_ITER: int = 200
_IRR_PRECISION: float = 1e-8   # rate precision (not EGP precision)


class DCFEngine(ValuationEngine):
    """
    Discounted Cash Flow (DCF) engine — Phase 16.3 v1.

    Inputs (dict keys):
        cash_flows           list[float]  required — index 0 = t=0 (initial outflow),
                                          index t = end-of-year t cash flow
        discount_rate        float        required (must be > -1)
        terminal_value       float        optional — caller-supplied reversion value
        terminal_cap_rate    float        optional — derive TV = CF[-1] / terminal_cap_rate
                                          used only when terminal_value not supplied
        projection_years     int          optional — informational; derived from
                                          len(cash_flows)-1 if not supplied

    Outputs (EngineResult):
        value      = NPV (Decimal, EGP)
        confidence = high | medium | low | insufficient
        metadata   = {npv, irr, terminal_value, terminal_value_source,
                      discount_rate, projection_years, cash_flows,
                      pv_of_cash_flows, pv_of_terminal_value}
    """

    name    = "dcf"
    version = "1.0.0"

    # ------------------------------------------------------------------
    # Abstract method implementations
    # ------------------------------------------------------------------

    def validate(self, inputs: dict) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        cfs = inputs.get("cash_flows")
        if not cfs:
            issues.append(ValidationIssue(
                severity="error",
                code="MISSING_CASH_FLOWS",
                message="cash_flows must be a non-empty list of numeric values",
            ))

        r = inputs.get("discount_rate")
        if r is None:
            issues.append(ValidationIssue(
                severity="error",
                code="MISSING_DISCOUNT_RATE",
                message="discount_rate is required",
            ))
        elif float(r) <= -1.0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_DISCOUNT_RATE",
                message=(
                    f"discount_rate must be > -1 to avoid zero denominator in "
                    f"(1+r)^t; got {r}"
                ),
            ))
        elif float(r) == 0.0:
            issues.append(ValidationIssue(
                severity="warning",
                code="ZERO_DISCOUNT_RATE",
                message=(
                    "discount_rate = 0 means no time-value discounting — "
                    "NPV equals the undiscounted sum of cash flows"
                ),
            ))
        elif not (_DISCOUNT_RATE_WARN_MIN <= float(r) <= _DISCOUNT_RATE_WARN_MAX):
            issues.append(ValidationIssue(
                severity="warning",
                code="UNUSUAL_DISCOUNT_RATE",
                message=(
                    f"discount_rate {float(r):.1%} is outside typical Egyptian "
                    f"market range {_DISCOUNT_RATE_WARN_MIN:.0%}–{_DISCOUNT_RATE_WARN_MAX:.0%}"
                ),
            ))

        tv    = inputs.get("terminal_value")
        t_cap = inputs.get("terminal_cap_rate")
        if tv is None and t_cap is None:
            issues.append(ValidationIssue(
                severity="warning",
                code="MISSING_TERMINAL_VALUE",
                message=(
                    "Neither terminal_value nor terminal_cap_rate supplied — "
                    "NPV will not include a reversion / terminal component"
                ),
            ))
        if t_cap is not None and float(t_cap) <= 0:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_TERMINAL_CAP_RATE",
                message=(
                    f"terminal_cap_rate must be > 0 to derive terminal_value; "
                    f"got {t_cap}"
                ),
            ))

        return issues

    def calculate(self, inputs: dict) -> EngineResult:
        """Project CFs → discount → NPV + IRR → EngineResult."""
        issues = self.validate(inputs)
        if any(i.severity == "error" for i in issues):
            return EngineResult(
                engine_name=self.name,
                value=None,
                confidence="insufficient",
                audit_trail=[],
                issues=issues,
                metadata={},
            )

        cfs   = [float(x) for x in inputs["cash_flows"]]
        r     = float(inputs["discount_rate"])
        n     = len(cfs)
        last_t = n - 1

        audit_trail: list[AuditEntry] = []

        # ── Step 1: Resolve terminal value ────────────────────────────
        tv_input = inputs.get("terminal_value")
        t_cap    = inputs.get("terminal_cap_rate")
        if tv_input is not None:
            tv        = float(tv_input)
            tv_source = "caller-supplied terminal_value"
        elif t_cap is not None:
            last_cf   = cfs[-1]
            tv        = last_cf / float(t_cap)
            tv_source = f"CF[-1] ({last_cf:,.0f}) / terminal_cap_rate ({float(t_cap):.2%})"
        else:
            tv        = 0.0
            tv_source = "zero (not supplied)"

        audit_trail.append(AuditEntry(
            step_name="Resolve terminal value",
            inputs={
                "terminal_value_override": tv_input,
                "terminal_cap_rate": t_cap,
                "last_cash_flow": cfs[-1],
            },
            outputs={"terminal_value": round(tv, 2), "source": tv_source},
            formula="TV = CF[-1] / terminal_cap_rate  (or caller override)",
            references=["IVS 105: Terminal Value", "EGVS_7.1: DCF Reversion"],
        ))

        # ── Step 2: Discount each cash flow ──────────────────────────
        factor  = 1.0 + r
        pv_cfs: list[float] = []
        for t, cf in enumerate(cfs):
            # (1+r)^0 = 1 for t=0; safe because r > -1 guarantees factor > 0
            pv = cf / (factor ** t) if t > 0 else cf
            pv_cfs.append(pv)

        pv_terminal = tv / (factor ** last_t) if last_t > 0 else tv

        audit_trail.append(AuditEntry(
            step_name="Discount periodic cash flows",
            inputs={
                "cash_flows": [round(c, 2) for c in cfs],
                "discount_rate": r,
                "n_periods": n,
            },
            outputs={
                "pv_cash_flows":     [round(p, 2) for p in pv_cfs],
                "pv_terminal_value": round(pv_terminal, 2),
            },
            formula="PV(CF[t]) = CF[t] / (1+r)^t",
            references=["EGVS_7.2: Present Value", "IVS 105: Discounting"],
        ))

        # ── Step 3: NPV ───────────────────────────────────────────────
        npv = sum(pv_cfs) + pv_terminal
        audit_trail.append(AuditEntry(
            step_name="Calculate Net Present Value (NPV)",
            inputs={
                "sum_pv_cash_flows": round(sum(pv_cfs), 2),
                "pv_terminal_value": round(pv_terminal, 2),
            },
            outputs={"npv": round(npv, 2)},
            formula="NPV = Σ PV(CF[t]) + PV(terminal_value)",
            references=["EGVS_7.3: NPV", "IVS 105: Net Present Value"],
        ))

        # ── Step 4: IRR (bisection — pure stdlib) ─────────────────────
        irr = self._compute_irr(cfs, tv, last_t)
        irr_note = "bisection converged" if irr is not None else "no real solution in [-99%, 500%]"
        audit_trail.append(AuditEntry(
            step_name="Compute Internal Rate of Return (IRR)",
            inputs={"cash_flows": [round(c, 2) for c in cfs], "terminal_value": round(tv, 2)},
            outputs={"irr": round(irr * 100, 4) if irr is not None else None, "note": irr_note},
            formula="IRR: solve NPV(r*)=0 via bisection over [-99%, 500%]",
            references=["EGVS_7.4: IRR", "IVS 105: Internal Rate of Return"],
        ))

        # ── Confidence ────────────────────────────────────────────────
        rate_ok = _DISCOUNT_RATE_WARN_MIN <= r <= _DISCOUNT_RATE_WARN_MAX
        has_tv  = tv != 0.0
        if r == 0.0:
            confidence = "low"
        elif not rate_ok:
            confidence = "low"
        elif not has_tv:
            confidence = "medium"
        else:
            confidence = "high"

        proj_years = inputs.get("projection_years") or last_t

        metadata: dict = {
            "npv":                   round(npv, 2),
            "irr":                   round(irr, 6) if irr is not None else None,
            "irr_pct":               round(irr * 100, 4) if irr is not None else None,
            "terminal_value":        round(tv, 2),
            "terminal_value_source": tv_source,
            "discount_rate":         r,
            "projection_years":      proj_years,
            "cash_flows":            [round(c, 2) for c in cfs],
            "pv_of_cash_flows":      [round(p, 2) for p in pv_cfs],
            "pv_of_terminal_value":  round(pv_terminal, 2),
        }

        return EngineResult(
            engine_name=self.name,
            value=Decimal(str(round(npv, 2))),
            confidence=confidence,
            audit_trail=audit_trail,
            issues=issues,
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _npv_at_rate(self, cfs: list[float], tv: float, last_t: int, r: float) -> float:
        """NPV function used for IRR bisection."""
        f = 1.0 + r
        result = sum(cf / (f ** t) if t > 0 else cf for t, cf in enumerate(cfs))
        result += tv / (f ** last_t) if last_t > 0 else tv
        return result

    def _compute_irr(
        self,
        cfs: list[float],
        tv: float,
        last_t: int,
    ) -> Optional[float]:
        """IRR via bisection over [_IRR_LO, _IRR_HI]. Returns None if no real solution."""
        lo, hi = _IRR_LO, _IRR_HI
        try:
            npv_lo = self._npv_at_rate(cfs, tv, last_t, lo)
            npv_hi = self._npv_at_rate(cfs, tv, last_t, hi)
        except (ZeroDivisionError, OverflowError):
            return None

        if npv_lo * npv_hi > 0:
            return None  # No sign change — no IRR in this range

        for _ in range(_IRR_MAX_ITER):
            mid = (lo + hi) / 2.0
            try:
                npv_mid = self._npv_at_rate(cfs, tv, last_t, mid)
            except (ZeroDivisionError, OverflowError):
                return None
            if abs(npv_mid) < _IRR_PRECISION or (hi - lo) < _IRR_PRECISION:
                return mid
            if npv_lo * npv_mid <= 0:
                hi = mid
            else:
                lo = mid
                npv_lo = npv_mid

        return (lo + hi) / 2.0
