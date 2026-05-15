"""
best_practices.py — Best Practices & Regulatory Tracker (Phase 35)

Industry guidelines, regulatory updates, and compliance deadline tracking.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BestPractice:
    practice_id: str
    title: str
    description: str
    category: str
    problem_addressed: str
    solution: str
    benefits: List[str] = field(default_factory=list)
    implementation_steps: List[str] = field(default_factory=list)
    tools_required: List[str] = field(default_factory=list)
    author: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    endorsed_by: List[str] = field(default_factory=list)
    adoption_rate: float = 0.0
    usefulness_score: float = 0.0
    examples: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "practice_id": self.practice_id,
            "title": self.title,
            "category": self.category,
            "description": self.description,
            "adoption_rate": round(self.adoption_rate, 4),
            "usefulness_score": round(self.usefulness_score, 4),
            "endorsed_by": self.endorsed_by,
            "implementation_steps": self.implementation_steps,
        }


@dataclass
class RegulatoryUpdate:
    update_id: str
    title: str
    description: str
    source: str
    effective_date: datetime
    announced_date: datetime
    impact_level: str
    affected_entities: List[str] = field(default_factory=list)
    required_actions: List[str] = field(default_factory=list)
    compliance_deadline: datetime = field(default_factory=datetime.utcnow)
    full_text: str = ""
    related_links: List[str] = field(default_factory=list)
    is_active: bool = True
    acknowledged_by: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "update_id": self.update_id,
            "title": self.title,
            "source": self.source,
            "effective_date": self.effective_date.isoformat(),
            "impact_level": self.impact_level,
            "affected_entities": self.affected_entities,
            "compliance_deadline": self.compliance_deadline.isoformat(),
            "required_actions": self.required_actions,
            "is_active": self.is_active,
        }


class BestPracticesLibrary:
    """Library of best practices and regulatory updates."""

    def __init__(self) -> None:
        self.practices: Dict[str, BestPractice] = {}
        self.updates: Dict[str, RegulatoryUpdate] = {}
        self._by_category: Dict[str, List[str]] = {}
        self._by_source: Dict[str, List[str]] = {}
        self._lock = threading.Lock()
        logger.info("Best Practices Library initialized")

    def add_best_practice(
        self,
        practice_id: str,
        title: str,
        description: str,
        category: str,
        problem_addressed: str,
        solution: str,
        benefits: Optional[List[str]] = None,
        implementation_steps: Optional[List[str]] = None,
        endorsed_by: Optional[List[str]] = None,
        adoption_rate: float = 0.0,
    ) -> BestPractice:
        practice = BestPractice(
            practice_id=practice_id,
            title=title,
            description=description,
            category=category,
            problem_addressed=problem_addressed,
            solution=solution,
            benefits=benefits or [],
            implementation_steps=implementation_steps or [],
            endorsed_by=endorsed_by or [],
            adoption_rate=adoption_rate,
        )
        with self._lock:
            self.practices[practice_id] = practice
            self._by_category.setdefault(category, []).append(practice_id)
        logger.info("Best practice added: %s", title)
        return practice

    def add_regulatory_update(
        self,
        update_id: str,
        title: str,
        description: str,
        source: str,
        effective_date: datetime,
        impact_level: str,
        compliance_deadline: datetime,
        affected_entities: Optional[List[str]] = None,
        required_actions: Optional[List[str]] = None,
    ) -> RegulatoryUpdate:
        update = RegulatoryUpdate(
            update_id=update_id,
            title=title,
            description=description,
            source=source,
            effective_date=effective_date,
            announced_date=datetime.utcnow(),
            impact_level=impact_level,
            compliance_deadline=compliance_deadline,
            affected_entities=affected_entities or [],
            required_actions=required_actions or [],
        )
        with self._lock:
            self.updates[update_id] = update
            self._by_source.setdefault(source, []).append(update_id)
        logger.info("Regulatory update added: %s", title)
        return update

    def get_active_updates(self, source: Optional[str] = None) -> List[RegulatoryUpdate]:
        with self._lock:
            updates = [u for u in self.updates.values() if u.is_active]
        if source:
            updates = [u for u in updates if u.source == source]
        updates.sort(key=lambda x: x.effective_date, reverse=True)
        return updates

    def get_practices_by_category(self, category: str) -> List[BestPractice]:
        with self._lock:
            ids = self._by_category.get(category, [])
            return [self.practices[pid] for pid in ids if pid in self.practices]

    def get_upcoming_compliance_deadlines(self, days_ahead: int = 90) -> List[RegulatoryUpdate]:
        now = datetime.utcnow()
        cutoff = now + timedelta(days=days_ahead)
        with self._lock:
            updates = [
                u for u in self.updates.values()
                if u.is_active and now <= u.compliance_deadline <= cutoff
            ]
        updates.sort(key=lambda x: x.compliance_deadline)
        return updates

    def acknowledge_update(self, update_id: str, entity: str) -> bool:
        with self._lock:
            update = self.updates.get(update_id)
        if update is None:
            return False
        if entity not in update.acknowledged_by:
            update.acknowledged_by.append(entity)
        return True

    def deactivate_update(self, update_id: str) -> bool:
        with self._lock:
            update = self.updates.get(update_id)
        if update is None:
            return False
        update.is_active = False
        return True

    def get_practices_statistics(self) -> Dict[str, Any]:
        with self._lock:
            cats = {c: len(ids) for c, ids in self._by_category.items()}
        return {
            "total_practices": len(self.practices),
            "by_category": cats,
            "total_updates": len(self.updates),
            "active_updates": sum(1 for u in self.updates.values() if u.is_active),
        }

    def count_practices(self) -> int:
        with self._lock:
            return len(self.practices)

    def count_updates(self) -> int:
        with self._lock:
            return len(self.updates)


best_practices = BestPracticesLibrary()
