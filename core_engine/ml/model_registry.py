"""
model_registry.py — Versioned model storage and retrieval.
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib

logger = logging.getLogger(__name__)


@dataclass
class ModelMetadata:
    model_id: str
    algorithm: str
    version: str
    trained_at: str
    metrics: Dict[str, Any]
    feature_count: int
    record_count: int
    model_path: str
    is_active: bool = False
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


class ModelRegistry:
    """Persist, retrieve, and activate versioned AVM models."""

    def __init__(self, registry_dir: str = "models/registry") -> None:
        self._dir = Path(registry_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._dir / "index.json"
        self._index: Dict[str, ModelMetadata] = {}
        self._lock = threading.Lock()
        self._load_index()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        model: Any,
        algorithm: str,
        metrics: Dict[str, Any],
        feature_count: int,
        record_count: int,
        version: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> ModelMetadata:
        """Save *model* to disk and register its metadata."""
        import uuid

        model_id = str(uuid.uuid4())[:8]
        ver = version or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        model_file = self._dir / f"{algorithm}_{ver}_{model_id}.pkl"

        joblib.dump(model, model_file)

        meta = ModelMetadata(
            model_id=model_id,
            algorithm=algorithm,
            version=ver,
            trained_at=datetime.utcnow().isoformat(),
            metrics=metrics,
            feature_count=feature_count,
            record_count=record_count,
            model_path=str(model_file),
            tags=tags or [],
        )

        with self._lock:
            self._index[model_id] = meta
            self._save_index()

        logger.info("Registered model %s (%s v%s)", model_id, algorithm, ver)
        return meta

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, model_id: str) -> Optional[ModelMetadata]:
        return self._index.get(model_id)

    def list_models(self, algorithm: Optional[str] = None) -> List[ModelMetadata]:
        models = list(self._index.values())
        if algorithm:
            models = [m for m in models if m.algorithm == algorithm]
        return sorted(models, key=lambda m: m.trained_at, reverse=True)

    def load_model(self, model_id: str) -> Optional[Any]:
        meta = self.get(model_id)
        if meta is None:
            logger.error("Model %s not found", model_id)
            return None
        try:
            return joblib.load(meta.model_path)
        except Exception as exc:
            logger.error("Error loading model %s: %s", model_id, exc)
            return None

    def get_active_model(self) -> Optional[ModelMetadata]:
        for meta in self._index.values():
            if meta.is_active:
                return meta
        return None

    def activate(self, model_id: str) -> bool:
        """Mark *model_id* as active and deactivate all others."""
        with self._lock:
            if model_id not in self._index:
                return False
            for meta in self._index.values():
                meta.is_active = False
            self._index[model_id].is_active = True
            self._save_index()
        logger.info("Activated model %s", model_id)
        return True

    def delete(self, model_id: str) -> bool:
        with self._lock:
            meta = self._index.pop(model_id, None)
            if meta is None:
                return False
            try:
                Path(meta.model_path).unlink(missing_ok=True)
            except Exception:
                pass
            self._save_index()
        return True

    def get_stats(self) -> Dict[str, Any]:
        models = list(self._index.values())
        return {
            "total_models": len(models),
            "active_model": next((m.model_id for m in models if m.is_active), None),
            "algorithms": list({m.algorithm for m in models}),
        }

    # ------------------------------------------------------------------
    # Index persistence
    # ------------------------------------------------------------------

    def _load_index(self) -> None:
        if self._index_path.exists():
            try:
                raw = json.loads(self._index_path.read_text(encoding="utf-8"))
                self._index = {k: ModelMetadata(**v) for k, v in raw.items()}
            except Exception as exc:
                logger.warning("Could not load registry index: %s", exc)
                self._index = {}

    def _save_index(self) -> None:
        data = {k: v.to_dict() for k, v in self._index.items()}
        self._index_path.write_text(
            json.dumps(data, indent=2, default=str), encoding="utf-8"
        )
