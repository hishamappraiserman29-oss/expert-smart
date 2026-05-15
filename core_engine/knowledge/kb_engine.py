"""
kb_engine.py — Knowledge Base Engine (Phase 35)

Comprehensive content management and retrieval system.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ContentType(str, Enum):
    ARTICLE = "article"
    GUIDE = "guide"
    CASE_STUDY = "case_study"
    STANDARD = "standard"
    TEMPLATE = "template"
    TOOL = "tool"
    FAQ = "faq"
    GLOSSARY = "glossary"
    REGULATION = "regulation"
    BEST_PRACTICE = "best_practice"


class ContentLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    PROFESSIONAL = "professional"


class ContentStatus(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"


@dataclass
class KnowledgeContent:
    content_id: str
    title: str
    content_type: ContentType
    description: str
    body: str
    author: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None
    status: ContentStatus = ContentStatus.DRAFT
    expertise_level: ContentLevel = ContentLevel.INTERMEDIATE
    category: str = ""
    tags: List[str] = field(default_factory=list)
    related_standards: List[str] = field(default_factory=list)
    views: int = 0
    helpful_votes: int = 0
    unhelpful_votes: int = 0
    comments_count: int = 0
    keywords: List[str] = field(default_factory=list)
    language: str = "ar"
    version: str = "1.0"
    approval_status: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content_id": self.content_id,
            "title": self.title,
            "content_type": self.content_type.value,
            "description": self.description,
            "status": self.status.value,
            "expertise_level": self.expertise_level.value,
            "category": self.category,
            "tags": self.tags,
            "views": self.views,
            "helpful_votes": self.helpful_votes,
            "language": self.language,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class KnowledgeBaseEngine:
    """Central knowledge base management."""

    def __init__(self) -> None:
        self._contents: Dict[str, KnowledgeContent] = {}
        self._by_category: Dict[str, List[str]] = {}
        self._by_tag: Dict[str, List[str]] = {}
        self._by_type: Dict[str, List[str]] = {}
        self._lock = threading.Lock()
        logger.info("Knowledge Base Engine initialized")

    def create_content(
        self,
        content_id: str,
        title: str,
        content_type: ContentType,
        description: str,
        body: str,
        author: str,
        category: str = "",
        tags: Optional[List[str]] = None,
        expertise_level: ContentLevel = ContentLevel.INTERMEDIATE,
        language: str = "ar",
    ) -> KnowledgeContent:
        if tags is None:
            tags = []

        content = KnowledgeContent(
            content_id=content_id,
            title=title,
            content_type=content_type,
            description=description,
            body=body,
            author=author,
            category=category,
            tags=tags,
            expertise_level=expertise_level,
            language=language,
        )

        with self._lock:
            self._contents[content_id] = content
            if category:
                self._by_category.setdefault(category, []).append(content_id)
            for tag in tags:
                self._by_tag.setdefault(tag, []).append(content_id)
            self._by_type.setdefault(content_type.value, []).append(content_id)

        logger.info("Content created: %s", title)
        return content

    def publish_content(self, content_id: str, approval: bool = True) -> bool:
        with self._lock:
            content = self._contents.get(content_id)
        if content is None:
            return False
        content.status = ContentStatus.PUBLISHED
        content.published_at = datetime.utcnow()
        content.approval_status = approval
        logger.info("Content published: %s", content.title)
        return True

    def archive_content(self, content_id: str) -> bool:
        with self._lock:
            content = self._contents.get(content_id)
        if content is None:
            return False
        content.status = ContentStatus.ARCHIVED
        return True

    def search_content(
        self,
        query: str,
        content_type: Optional[ContentType] = None,
        category: Optional[str] = None,
        expertise_level: Optional[ContentLevel] = None,
        limit: int = 10,
    ) -> List[KnowledgeContent]:
        query_lower = query.lower()
        results: List[KnowledgeContent] = []

        with self._lock:
            items = list(self._contents.values())

        for content in items:
            if content.status != ContentStatus.PUBLISHED:
                continue
            if content_type and content.content_type != content_type:
                continue
            if category and content.category != category:
                continue
            if expertise_level and content.expertise_level != expertise_level:
                continue
            if (
                query_lower in content.title.lower()
                or query_lower in content.description.lower()
                or any(query_lower in tag.lower() for tag in content.tags)
            ):
                results.append(content)

        results.sort(key=lambda x: x.views + x.helpful_votes * 5, reverse=True)
        return results[:limit]

    def get_content(self, content_id: str) -> Optional[KnowledgeContent]:
        with self._lock:
            return self._contents.get(content_id)

    def get_by_category(self, category: str, limit: int = 20) -> List[KnowledgeContent]:
        with self._lock:
            ids = list(self._by_category.get(category, []))
            items = [self._contents[cid] for cid in ids if cid in self._contents]
        return [c for c in items if c.status == ContentStatus.PUBLISHED][:limit]

    def get_by_type(self, content_type: ContentType, limit: int = 20) -> List[KnowledgeContent]:
        with self._lock:
            ids = list(self._by_type.get(content_type.value, []))
            items = [self._contents[cid] for cid in ids if cid in self._contents]
        return [c for c in items if c.status == ContentStatus.PUBLISHED][:limit]

    def add_view(self, content_id: str) -> None:
        with self._lock:
            content = self._contents.get(content_id)
        if content:
            content.views += 1

    def vote_helpful(self, content_id: str, helpful: bool = True) -> None:
        with self._lock:
            content = self._contents.get(content_id)
        if content:
            if helpful:
                content.helpful_votes += 1
            else:
                content.unhelpful_votes += 1

    def get_statistics(self) -> Dict[str, Any]:
        with self._lock:
            contents = list(self._contents.values())
            by_type = {t: len(ids) for t, ids in self._by_type.items()}
            by_cat = {c: len(ids) for c, ids in self._by_category.items()}

        published = sum(1 for c in contents if c.status == ContentStatus.PUBLISHED)
        total_views = sum(c.views for c in contents)
        total_votes = sum(c.helpful_votes + c.unhelpful_votes for c in contents)
        return {
            "total_content": len(contents),
            "published_content": published,
            "draft_content": sum(1 for c in contents if c.status == ContentStatus.DRAFT),
            "total_views": total_views,
            "total_votes": total_votes,
            "by_type": by_type,
            "by_category": by_cat,
        }

    def count(self) -> int:
        with self._lock:
            return len(self._contents)


kb_engine = KnowledgeBaseEngine()
