"""
Compliance Inputs Bridge — READ-ONLY
Reads platform engine outputs to suggest initial clause status + provenance.
Falls back to documented "غير متاح" if an engine is unavailable.
All web references tagged Draft — never presented as official certification.
"""
from __future__ import annotations

import datetime
import sys
import pathlib
from typing import Any

_CORE = pathlib.Path(__file__).parent
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

BRIDGE_VERSION = "1.0.0"

# ── Mock QA payload (Riyadh / SAR — case QA-COMPLIANCE-VISUAL-001) ───────────

_QA_BANK_PAYLOAD: dict[str, Any] = {
    "property_type": "residential",
    "location": "الرياض",
    "area": 350,
    "current_market_value": 1_800_000,
    "original_valuation_value": 1_750_000,
    "original_valuation_date": "2023-01-15",
    "loan_amount": 1_260_000,
    "loan_type": "mortgage",
    "client_name": "عميل QA",
    "bank_name": "بنك QA",
}

_QA_FUND_PAYLOAD: dict[str, Any] = {
    "fund_name": "صندوق QA العقاري",
    "client_name": "عميل QA",
    "property_type": "residential",
    "location": "الرياض",
    "area": 350,
    "total_units": 1,
    "valuation_date": "2024-01-15",
    "market_value": 1_800_000,
    "annual_rent": 90_000,
    "vacancy_rate": 0.05,
    "operating_expenses": 18_000,
    "loan_amount": 1_260_000,
}

# ── Draft web references (structured — tagged Draft, not official certification) ──

DRAFT_WEB_REFS: list[dict[str, Any]] = [
    {
        "ref_id": "DWR-001",
        "standard": "IVS 2025",
        "clause": "IVS 101",
        "description": "Scope of Work — Effective 31 Jan 2025",
        "source_url": "https://www.ivsc.org/ivs/",
        "retrieved_at": "2026-07-01",
        "confidence": 0.80,
        "source_tier": "draft_web",
        "advisory_note": "Draft — مرجع شبكي — لا يُقدَّم كاعتماد رسمي",
    },
    {
        "ref_id": "DWR-002",
        "standard": "IVS 2025",
        "clause": "IVS 105",
        "description": "Valuation Approaches and Methods — IVS 2025",
        "source_url": "https://www.ivsc.org/ivs/",
        "retrieved_at": "2026-07-01",
        "confidence": 0.80,
        "source_tier": "draft_web",
        "advisory_note": "Draft — مرجع شبكي — لا يُقدَّم كاعتماد رسمي",
    },
    {
        "ref_id": "DWR-003",
        "standard": "Basel III/IV",
        "clause": "PCVC",
        "description": "Prudent Conservative Value Concept — BIS CRR Art. 229",
        "source_url": "https://www.bis.org/bcbs/",
        "retrieved_at": "2026-07-01",
        "confidence": 0.75,
        "source_tier": "draft_web",
        "advisory_note": "Draft — مرجع شبكي — لا يُقدَّم كاعتماد رسمي",
    },
    {
        "ref_id": "DWR-004",
        "standard": "Saudi Taqyeem",
        "clause": "SA-ACC",
        "description": "هيئة تقييم — نظام المقيّمين المعتمدين — اللائحة التنفيذية 1445هـ",
        "source_url": "https://taqyeem.org.sa/",
        "retrieved_at": "2026-07-01",
        "confidence": 0.85,
        "source_tier": "draft_web",
        "advisory_note": "Draft — مرجع شبكي — لا يُقدَّم كاعتماد رسمي",
    },
    {
        "ref_id": "DWR-005",
        "standard": "USPAP",
        "clause": "SR-1",
        "description": "USPAP 2024-2025 — Standard 1: Real Property Appraisal Development",
        "source_url": "https://www.appraisalfoundation.org/uspap",
        "retrieved_at": "2026-07-01",
        "confidence": 0.70,
        "source_tier": "draft_web",
        "advisory_note": "Draft — مرجع شبكي — لا يُقدَّم كاعتماد رسمي",
    },
    {
        "ref_id": "DWR-006",
        "standard": "RICS Red Book 2022",
        "clause": "VPS-6",
        "description": "Uncertainty in Valuations — RICS VPS 6.1",
        "source_url": "https://www.rics.org/red-book",
        "retrieved_at": "2026-07-01",
        "confidence": 0.85,
        "source_tier": "draft_web",
        "advisory_note": "Draft — مرجع شبكي — لا يُقدَّم كاعتماد رسمي",
    },
    {
        "ref_id": "DWR-007",
        "standard": "Saudi Mortgage Law",
        "clause": "SA-MORT",
        "description": "نظام التمويل العقاري — مؤسسة النقد العربي السعودي (ساما)",
        "source_url": "https://www.sama.gov.sa/",
        "retrieved_at": "2026-07-01",
        "confidence": 0.80,
        "source_tier": "draft_web",
        "advisory_note": "Draft — مرجع شبكي — لا يُقدَّم كاعتماد رسمي",
    },
    {
        "ref_id": "DWR-008",
        "standard": "AML/CFT",
        "clause": "AML-IND",
        "description": "FATF Recommendations — Valuer Independence and AML/CFT Obligations",
        "source_url": "https://www.fatf-gafi.org/",
        "retrieved_at": "2026-07-01",
        "confidence": 0.70,
        "source_tier": "draft_web",
        "advisory_note": "Draft — مرجع شبكي — لا يُقدَّم كاعتماد رسمي",
    },
    {
        "ref_id": "DWR-009",
        "standard": "IVS 2025",
        "clause": "IVS 102",
        "description": "Investigations and Compliance — IVS 2025",
        "source_url": "https://www.ivsc.org/ivs/",
        "retrieved_at": "2026-07-01",
        "confidence": 0.78,
        "source_tier": "draft_web",
        "advisory_note": "Draft — مرجع شبكي — لا يُقدَّم كاعتماد رسمي",
    },
    {
        "ref_id": "DWR-010",
        "standard": "Basel III/IV",
        "clause": "LTV",
        "description": "Loan-to-Value ratio limits — BCBS 457 / CRR2 Art. 124-126",
        "source_url": "https://www.bis.org/bcbs/publ/d457.htm",
        "retrieved_at": "2026-07-01",
        "confidence": 0.80,
        "source_tier": "draft_web",
        "advisory_note": "Draft — مرجع شبكي — لا يُقدَّم كاعتماد رسمي",
    },
]

# ── Clause → engine mapping ────────────────────────────────────────────────────

_BASEL_CLAUSE_IDS = {"BASEL-LTV", "BASEL-PCVC", "BASEL-REVTRIG", "BASEL-ORIGCAP"}
_IVS_METHOD_CLAUSE_IDS = {"IVS-105-METHODS", "IVS-200-MARKET", "IVS-400-PROP"}


class ComplianceInputsBridge:
    """
    READ-ONLY bridge to platform engines.
    Suggests clause status from engine outputs; documents provenance for each.
    Never modifies engine state.
    """

    def __init__(self, case_id: str = "QA-COMPLIANCE-VISUAL-001") -> None:
        self.case_id = case_id
        self._bank_result: dict[str, Any] | None = None
        self._fund_result: dict[str, Any] | None = None
        self._bank_error: str = ""
        self._fund_error: str = ""
        self._retrieved_at = datetime.datetime.now().isoformat()

    # ── Engine reads ──────────────────────────────────────────────────────────

    def load_bank_audit(self, payload: dict[str, Any] | None = None) -> None:
        """Read bank_audit_engine output. READ-ONLY — never writes engine state."""
        try:
            from bank_audit_engine import run_bank_audit  # type: ignore
            self._bank_result = run_bank_audit(payload or _QA_BANK_PAYLOAD)
        except Exception as exc:
            self._bank_error = f"bank_audit_engine غير متاح: {exc}"

    def load_fund_valuation(self, payload: dict[str, Any] | None = None) -> None:
        """Read fund_valuation_engine output. READ-ONLY — never writes engine state."""
        try:
            from fund_valuation_engine import run_fund_valuation  # type: ignore
            self._fund_result = run_fund_valuation(payload or _QA_FUND_PAYLOAD)
        except Exception as exc:
            self._fund_error = f"fund_valuation_engine غير متاح: {exc}"

    def load_all(self) -> None:
        """Load all available platform engine outputs."""
        self.load_bank_audit()
        self.load_fund_valuation()

    # ── Clause status hints ───────────────────────────────────────────────────

    def suggest_for_clause(self, clause_id: str) -> dict[str, Any]:
        """
        Return a suggested status for a clause based on available engine outputs.
        Falls back to 'not_assessed' with a documented reason — never fabricates.
        """
        if clause_id in _BASEL_CLAUSE_IDS:
            return self._suggest_basel(clause_id)
        if clause_id in _IVS_METHOD_CLAUSE_IDS:
            return self._suggest_ivs_methodology(clause_id)
        if "IVS-101" in clause_id or "IVS-102" in clause_id:
            return {
                "suggested_status": "partially_compliant",
                "source": "document_review",
                "confidence": 0.60,
                "tier": "document",
                "note": "مراجعة وثائق نطاق العمل — يستوجب تحقق مدقق بشري",
                "advisory": "استرشادي — مصدر: مراجعة وثيقة",
            }
        return {
            "suggested_status": "not_assessed",
            "source": "غير متاح — لا بيانات محرّك مرتبطة بهذا البند",
            "confidence": 0.0,
            "tier": "unavailable",
            "note": "يتطلب مراجعة يدوية من المدقق",
            "advisory": "استرشادي",
        }

    def _suggest_basel(self, clause_id: str) -> dict[str, Any]:
        if not self._bank_result:
            return {
                "suggested_status": "not_assessed",
                "source": self._bank_error or "bank_audit_engine: لم يُحمَّل",
                "confidence": 0.0,
                "tier": "unavailable",
                "note": "تعذّر قراءة مخرجات محرّك التدقيق البنكي",
                "advisory": "استرشادي",
            }
        r = self._bank_result
        if clause_id == "BASEL-LTV":
            breach = r.get("ltv_breach", False)
            return {
                "suggested_status": "non_compliant" if breach else "compliant",
                "source": "bank_audit_engine.run_bank_audit (READ-ONLY)",
                "confidence": 0.90,
                "tier": "platform_engine",
                "note": f"LTV={r.get('ltv_ratio_pct', '?')}% / عتبة={r.get('ltv_threshold_pct', '?')}%",
                "advisory": "استرشادي — مصدر: محرّك التدقيق البنكي",
            }
        if clause_id == "BASEL-PCVC":
            risk = str(r.get("risk_level", ""))
            status = "compliant" if risk in ("low", "medium") else "partially_compliant"
            return {
                "suggested_status": status,
                "source": "bank_audit_engine.run_bank_audit (READ-ONLY)",
                "confidence": 0.80,
                "tier": "platform_engine",
                "note": f"مستوى المخاطرة: {risk}",
                "advisory": "استرشادي — مصدر: محرّك التدقيق البنكي",
            }
        if clause_id == "BASEL-REVTRIG":
            req = r.get("revaluation_required", False)
            return {
                "suggested_status": "non_compliant" if req else "compliant",
                "source": "bank_audit_engine.run_bank_audit (READ-ONLY)",
                "confidence": 0.85,
                "tier": "platform_engine",
                "note": f"إعادة التقييم مطلوبة: {req}",
                "advisory": "استرشادي — مصدر: محرّك التدقيق البنكي",
            }
        if clause_id == "BASEL-ORIGCAP":
            return {
                "suggested_status": "compliant",
                "source": "bank_audit_engine.run_bank_audit (READ-ONLY)",
                "confidence": 0.70,
                "tier": "platform_engine",
                "note": "لم يُرصد تجاوز لسقف قيمة النشأة",
                "advisory": "استرشادي — مصدر: محرّك التدقيق البنكي",
            }
        return {
            "suggested_status": "not_assessed",
            "source": "غير متاح",
            "confidence": 0.0,
            "tier": "unavailable",
            "note": "",
            "advisory": "استرشادي",
        }

    def _suggest_ivs_methodology(self, clause_id: str) -> dict[str, Any]:
        if not self._fund_result:
            return {
                "suggested_status": "not_assessed",
                "source": self._fund_error or "fund_valuation_engine: لم يُحمَّل",
                "confidence": 0.0,
                "tier": "unavailable",
                "note": "تعذّر قراءة مخرجات محرّك التقييم",
                "advisory": "استرشادي",
            }
        r = self._fund_result
        ifrs_level = r.get("ifrs_level", 3)
        noi = r.get("noi", "?")
        status = "compliant" if ifrs_level <= 2 else "partially_compliant"
        return {
            "suggested_status": status,
            "source": "fund_valuation_engine.run_fund_valuation (READ-ONLY)",
            "confidence": 0.75,
            "tier": "platform_engine",
            "note": f"IFRS 13 المستوى={ifrs_level} · NOI={noi} SAR",
            "advisory": "استرشادي — مصدر: محرّك التقييم",
        }

    # ── Provenance table ──────────────────────────────────────────────────────

    def build_provenance_table(self, clause_ids: list[str]) -> list[dict[str, Any]]:
        """Build full provenance table for a list of clause IDs."""
        rows: list[dict[str, Any]] = []
        for cid in clause_ids:
            hint = self.suggest_for_clause(cid)
            rows.append({
                "clause_id": cid,
                "suggested_status": hint["suggested_status"],
                "source": hint["source"],
                "confidence": hint["confidence"],
                "tier": hint["tier"],
                "note": hint.get("note", ""),
                "retrieved_at": self._retrieved_at,
                "advisory": hint.get("advisory", "استرشادي"),
            })
        return rows

    def get_draft_web_refs(self, standard: str | None = None) -> list[dict[str, Any]]:
        """Return Draft web references, optionally filtered by standard name substring."""
        if standard:
            return [r for r in DRAFT_WEB_REFS if standard in r["standard"]]
        return DRAFT_WEB_REFS

    def summary(self) -> dict[str, Any]:
        return {
            "bridge_version": BRIDGE_VERSION,
            "case_id": self.case_id,
            "bank_audit_loaded": self._bank_result is not None,
            "bank_audit_error": self._bank_error,
            "fund_valuation_loaded": self._fund_result is not None,
            "fund_valuation_error": self._fund_error,
            "draft_web_refs_count": len(DRAFT_WEB_REFS),
            "advisory_only": True,
        }
