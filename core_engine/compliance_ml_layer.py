"""
Compliance ML Layer — Governed ML for Standards Compliance clause suggestions.
Separate from AVM models in core_engine/ml/.
Draft suggestions only. Trains exclusively on human-approved auditor decisions.
No automatic compliance decision. No automatic block/approve.
"""
from __future__ import annotations

import datetime
import json
import pathlib
import pickle
from typing import Any

# ── Storage (separate from core_engine/ml/ AVM registry) ─────────────────────
_ROOT = pathlib.Path(__file__).parent
_ML_DIR = _ROOT / "outputs" / "compliance_ml"
_FEEDBACK_LOG = _ML_DIR / "feedback_log.jsonl"
_MODELS_DIR = _ML_DIR / "models"
_MODEL_CARD_PATH = _ML_DIR / "model_card.json"

# ── Governance constants ───────────────────────────────────────────────────────
MIN_APPROVED_FOR_TRAINING: int = 10
VALIDATION_ACCURACY_THRESHOLD: float = 0.65
ML_LAYER_VERSION: str = "1.0.0"

# ── Feature engineering (compliance-specific, not AVM) ────────────────────────
FEATURE_NAMES: list[str] = [
    "standard_encoded",
    "severity_encoded",
    "materiality",
    "evidence_count",
    "has_findings",
    "blocks_issuance",
]

_STANDARD_MAP: dict[str, float] = {
    "IVS": 0.0, "RICS": 1.0, "USPAP": 2.0,
    "Basel": 3.0, "Taqyeem": 4.0, "AML": 5.0,
}
_SEVERITY_MAP: dict[str, float] = {
    "critical": 4.0, "high": 3.0, "medium": 2.0,
    "low": 1.0, "informational": 0.0, "not_applicable": -1.0,
}
_STATUS_AR: dict[str, str] = {
    "compliant": "متوافق",
    "partially_compliant": "متوافق جزئياً",
    "non_compliant": "غير متوافق",
    "not_applicable": "غير منطبق",
    "insufficient_evidence": "أدلة غير كافية",
    "not_assessed": "لم يُقيَّم",
}


def _ensure_dirs() -> None:
    _ML_DIR.mkdir(parents=True, exist_ok=True)
    _MODELS_DIR.mkdir(parents=True, exist_ok=True)


def encode_clause_features(clause: dict[str, Any]) -> list[float]:
    """Encode a clause dict into a numeric feature vector for ML suggestion."""
    std = clause.get("standard", "")
    std_code = next((v for k, v in _STANDARD_MAP.items() if k in std), -1.0)
    sev_code = _SEVERITY_MAP.get(clause.get("severity", ""), 0.0)
    materiality = 1.0 if clause.get("materiality") == "material" else 0.0
    evidence_count = float(len(clause.get("evidence_refs", [])))
    has_findings = 1.0 if clause.get("findings") else 0.0
    blocks = 1.0 if clause.get("blocks_issuance") else 0.0
    return [std_code, sev_code, materiality, evidence_count, has_findings, blocks]


class ComplianceMLLayer:
    """
    Governed ML suggestion layer for compliance clause status.

    Governance principles (hard-coded, non-overridable):
    - ml_suggestion_only=True: every output is a Draft suggestion, never a decision
    - ml_trained_on_approved_only=True: model trains only on human-approved records
    - ml_auto_decision=False: no automatic compliance block or approval
    - human_in_the_loop=True: auditor must review every suggestion
    - advisory_only=True: labeled with full advisory disclaimer
    """

    advisory_disclaimer: str = (
        "اقتراح تعلّم آلي — استرشادي — لا يُعتمد إلا بمراجعة مدقّق بشري معتمَد"
    )
    ml_suggestion_only: bool = True
    ml_trained_on_approved_only: bool = True
    ml_auto_decision: bool = False
    human_in_the_loop: bool = True
    advisory_only: bool = True

    def __init__(self) -> None:
        _ensure_dirs()
        self._model: Any = None
        self._model_version: int = 0
        self._model_path: pathlib.Path | None = None
        self._card: dict[str, Any] = self._load_card()
        self._try_load_active_model()

    # ── Model card ─────────────────────────────────────────────────────────────

    def _load_card(self) -> dict[str, Any]:
        if _MODEL_CARD_PATH.exists():
            try:
                return json.loads(_MODEL_CARD_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "layer_version": ML_LAYER_VERSION,
            "current_model_version": 0,
            "active_model_path": None,
            "training_history": [],
            "source_constraint": "human_approved_auditor_decisions_only",
            "ml_suggestion_only": True,
            "ml_trained_on_approved_only": True,
            "ml_auto_decision": False,
            "feature_names": FEATURE_NAMES,
            "min_approved_for_training": MIN_APPROVED_FOR_TRAINING,
            "validation_accuracy_threshold": VALIDATION_ACCURACY_THRESHOLD,
        }

    def _save_card(self) -> None:
        _MODEL_CARD_PATH.write_text(
            json.dumps(self._card, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ── Active model loading ───────────────────────────────────────────────────

    def _try_load_active_model(self) -> None:
        path_str = self._card.get("active_model_path")
        if not path_str:
            return
        p = pathlib.Path(path_str)
        if not p.exists():
            return
        try:
            with open(p, "rb") as fh:
                self._model = pickle.load(fh)
            self._model_path = p
            self._model_version = self._card.get("current_model_version", 0)
        except Exception:
            self._model = None

    # ── Feedback recording ─────────────────────────────────────────────────────

    def record_feedback(
        self,
        clause_id: str,
        ml_suggestion: str,
        human_decision: str,
        human_reason: str,
        auditor_id: str,
        clause_features: dict[str, Any],
    ) -> None:
        """
        Record an auditor's confirmed decision on a ML suggestion.
        Only records with human_approved=True are ever used for model training.
        """
        record = {
            "recorded_at": datetime.datetime.now().isoformat(),
            "clause_id": clause_id,
            "ml_suggestion_draft": ml_suggestion,
            "human_decision": human_decision,
            "human_reason": human_reason,
            "auditor_id": auditor_id,
            "human_approved": True,
            "features": encode_clause_features(clause_features),
            "label": human_decision,
            "source_constraint": "human_approved_auditor_decision",
        }
        with open(_FEEDBACK_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _load_approved_records(self) -> list[dict[str, Any]]:
        """Load ONLY records where human_approved=True. Never uses Draft data."""
        if not _FEEDBACK_LOG.exists():
            return []
        records: list[dict[str, Any]] = []
        for line in _FEEDBACK_LOG.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                if r.get("human_approved") is True:
                    records.append(r)
            except Exception:
                continue
        return records

    # ── Suggestion ─────────────────────────────────────────────────────────────

    def suggest(self, clause: dict[str, Any]) -> dict[str, Any]:
        """
        Return a Draft suggestion for a clause status.
        Returns 'not_ready' message if insufficient approved data or no model.
        NEVER makes an automatic compliance decision.
        """
        records = self._load_approved_records()
        n_approved = len(records)

        if n_approved < MIN_APPROVED_FOR_TRAINING or self._model is None:
            return {
                "status": "not_ready",
                "message": "النموذج غير جاهز — بيانات معتمدة غير كافية لتوليد اقتراح",
                "approved_records": n_approved,
                "min_required": MIN_APPROVED_FOR_TRAINING,
                "suggestion_draft": None,
                "confidence": 0.0,
                "model_version": self._model_version,
                "advisory": self.advisory_disclaimer,
                "ml_auto_decision": False,
            }

        features = encode_clause_features(clause)
        try:
            import numpy as np  # type: ignore
            X = np.array([features])
            proba = self._model.predict_proba(X)[0]
            classes = list(self._model.classes_)
            best_idx = int(proba.argmax())
            suggestion = classes[best_idx]
            confidence = float(proba[best_idx])
            top_features = sorted(
                zip(FEATURE_NAMES, features), key=lambda x: abs(x[1]), reverse=True
            )[:3]
        except Exception as exc:
            return {
                "status": "error",
                "message": f"خطأ أثناء الاقتراح: {exc}",
                "suggestion_draft": None,
                "confidence": 0.0,
                "advisory": self.advisory_disclaimer,
                "ml_auto_decision": False,
            }

        return {
            "status": "draft",
            "suggestion_draft": suggestion,
            "suggestion_ar": _STATUS_AR.get(suggestion, suggestion),
            "confidence": round(confidence, 3),
            "top_features": [{"feature": f, "value": round(v, 3)} for f, v in top_features],
            "model_version": self._model_version,
            "approved_records": n_approved,
            "advisory": self.advisory_disclaimer,
            "ml_auto_decision": False,
            "ml_suggestion_only": True,
        }

    # ── Training (approved records only) ──────────────────────────────────────

    def train_on_approved(self) -> dict[str, Any]:
        """
        Train a new model version using ONLY human-approved auditor decisions.
        Draft/web/unverified data is never used.
        """
        records = self._load_approved_records()
        n = len(records)
        if n < MIN_APPROVED_FOR_TRAINING:
            return {
                "ok": False,
                "reason": f"بيانات معتمدة غير كافية: {n} < {MIN_APPROVED_FOR_TRAINING}",
                "approved_records": n,
            }

        try:
            import numpy as np  # type: ignore
            from sklearn.linear_model import LogisticRegression  # type: ignore
            from sklearn.model_selection import train_test_split  # type: ignore
            from sklearn.metrics import accuracy_score  # type: ignore
        except ImportError as exc:
            return {"ok": False, "reason": f"sklearn غير متاح: {exc}"}

        X = np.array([r["features"] for r in records])
        y = np.array([r["label"] for r in records])

        try:
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=0.20, random_state=42, stratify=y
            )
        except ValueError:
            X_train, X_val, y_train, y_val = X, X, y, y

        model = LogisticRegression(max_iter=500, random_state=42)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_val)
        acc = float(accuracy_score(y_val, y_pred))

        new_version = self._model_version + 1
        model_path = _MODELS_DIR / f"compliance_suggestion_v{new_version}.pkl"
        with open(model_path, "wb") as fh:
            pickle.dump(model, fh)

        batch_record = {
            "version": new_version,
            "trained_at": datetime.datetime.now().isoformat(),
            "record_count": n,
            "train_count": len(X_train),
            "val_count": len(X_val),
            "validation_accuracy": round(acc, 4),
            "threshold": VALIDATION_ACCURACY_THRESHOLD,
            "threshold_passed": acc >= VALIDATION_ACCURACY_THRESHOLD,
            "source": "human_approved_auditor_decisions_only",
            "model_path": str(model_path),
            "feature_names": FEATURE_NAMES,
            "algorithm": "LogisticRegression",
            "not_trained_on_draft_or_web": True,
        }
        self._card.setdefault("training_history", []).append(batch_record)
        self._save_card()

        return {
            "ok": True,
            "new_version": new_version,
            "validation_accuracy": round(acc, 4),
            "threshold_passed": acc >= VALIDATION_ACCURACY_THRESHOLD,
            "model_path": str(model_path),
            "approved_records": n,
            "note": (
                "للترقية إلى مقترِح افتراضي: استدعِ promote(version, your_approval=True) "
                "بعد مراجعة النتائج وموافقتك الصريحة"
            ),
        }

    # ── Promotion + rollback ───────────────────────────────────────────────────

    def promote(self, version: int, your_approval: bool = False) -> dict[str, Any]:
        """
        Promote a trained model version to active suggester.
        Requires your_approval=True AND validation accuracy above threshold.
        """
        if not your_approval:
            return {
                "ok": False,
                "reason": "الترقية تتطلب your_approval=True — موافقة صريحة مطلوبة",
            }
        model_path = _MODELS_DIR / f"compliance_suggestion_v{version}.pkl"
        if not model_path.exists():
            return {"ok": False, "reason": f"إصدار {version} غير موجود على القرص"}

        history = self._card.get("training_history", [])
        record = next((r for r in history if r.get("version") == version), None)
        if record and not record.get("threshold_passed", False):
            return {
                "ok": False,
                "reason": (
                    f"الإصدار {version} لم يتجاوز عتبة التحقق "
                    f"({VALIDATION_ACCURACY_THRESHOLD})"
                ),
                "validation_accuracy": record.get("validation_accuracy"),
            }

        prev_version = self._model_version
        with open(model_path, "rb") as fh:
            self._model = pickle.load(fh)
        self._model_version = version
        self._model_path = model_path
        self._card["current_model_version"] = version
        self._card["active_model_path"] = str(model_path)
        self._save_card()

        return {
            "ok": True,
            "promoted_version": version,
            "previous_version": prev_version,
            "rollback_command": f"layer.rollback({prev_version}, your_approval=True)",
        }

    def rollback(self, version: int, your_approval: bool = False) -> dict[str, Any]:
        """Roll back to a previous model version. Requires explicit approval."""
        return self.promote(version, your_approval=your_approval)

    # ── Improvement curve ──────────────────────────────────────────────────────

    def get_improvement_curve(self) -> list[dict[str, Any]]:
        """Return per-version accuracy data for the improvement curve chart."""
        return [
            {
                "version": r["version"],
                "trained_at": r["trained_at"],
                "validation_accuracy": r.get("validation_accuracy", 0.0),
                "record_count": r.get("record_count", 0),
                "threshold_passed": r.get("threshold_passed", False),
            }
            for r in self._card.get("training_history", [])
        ]

    # ── Model card export ──────────────────────────────────────────────────────

    def get_model_card(self) -> dict[str, Any]:
        return {
            **self._card,
            "current_model_version": self._model_version,
            "active_model_loaded": self._model is not None,
            "approved_records_available": len(self._load_approved_records()),
            "min_approved_for_training": MIN_APPROVED_FOR_TRAINING,
            "validation_accuracy_threshold": VALIDATION_ACCURACY_THRESHOLD,
            "feature_names": FEATURE_NAMES,
            "governance": {
                "ml_suggestion_only": True,
                "ml_trained_on_approved_only": True,
                "ml_auto_decision": False,
                "human_in_the_loop": True,
                "advisory_only": True,
                "not_trained_on_draft_or_web": True,
            },
        }
