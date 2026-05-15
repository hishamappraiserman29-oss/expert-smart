"""
marketplace.py — Integration marketplace: browse, review, and install plugins.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ListingStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


@dataclass
class MarketplaceListing:
    listing_id: str
    plugin_id: str
    name: str
    description: str
    category: str
    icon_url: str = ""
    screenshots: List[str] = field(default_factory=list)
    price: float = 0.0
    status: ListingStatus = ListingStatus.DRAFT
    author: str = ""
    author_url: str = ""
    version: str = "1.0.0"
    ratings: float = 0.0
    download_count: int = 0
    review_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        return {
            "listing_id": self.listing_id,
            "plugin_id": self.plugin_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "icon_url": self.icon_url,
            "screenshots": self.screenshots,
            "price": self.price,
            "status": self.status.value,
            "author": self.author,
            "author_url": self.author_url,
            "version": self.version,
            "ratings": self.ratings,
            "download_count": self.download_count,
            "review_count": self.review_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class PluginReview:
    review_id: str
    listing_id: str
    tenant_id: str
    rating: int
    title: str
    comment: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    helpful_count: int = 0

    def to_dict(self) -> Dict:
        return {
            "review_id": self.review_id,
            "listing_id": self.listing_id,
            "rating": self.rating,
            "title": self.title,
            "comment": self.comment,
            "helpful_count": self.helpful_count,
            "created_at": self.created_at.isoformat(),
        }


class Marketplace:
    """Browse, review, and track plugin installations."""

    def __init__(self) -> None:
        self.listings: Dict[str, MarketplaceListing] = {}
        self.reviews: Dict[str, PluginReview] = {}
        self.installations: Dict[str, List[str]] = {}

    # ------------------------------------------------------------------
    # Listings
    # ------------------------------------------------------------------

    def publish_listing(
        self,
        plugin_id: str,
        name: str,
        description: str,
        category: str,
        price: float = 0.0,
        author: str = "",
        icon_url: str = "",
        version: str = "1.0.0",
    ) -> MarketplaceListing:
        listing_id = str(uuid.uuid4())
        listing = MarketplaceListing(
            listing_id=listing_id,
            plugin_id=plugin_id,
            name=name,
            description=description,
            category=category,
            icon_url=icon_url,
            price=price,
            author=author,
            version=version,
            status=ListingStatus.PUBLISHED,
        )
        self.listings[listing_id] = listing
        logger.info("Published to marketplace: %s (%s)", name, listing_id)
        return listing

    def unpublish_listing(self, listing_id: str) -> bool:
        listing = self.listings.get(listing_id)
        if listing is None:
            return False
        listing.status = ListingStatus.ARCHIVED
        return True

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def search_plugins(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        sort_by: str = "rating",
    ) -> List[MarketplaceListing]:
        results = [
            lst for lst in self.listings.values()
            if lst.status == ListingStatus.PUBLISHED
        ]

        if query:
            q = query.lower()
            results = [
                r for r in results
                if q in r.name.lower() or q in r.description.lower()
            ]

        if category:
            results = [r for r in results if r.category == category]

        if sort_by == "rating":
            results.sort(key=lambda x: x.ratings, reverse=True)
        elif sort_by == "downloads":
            results.sort(key=lambda x: x.download_count, reverse=True)
        elif sort_by == "newest":
            results.sort(key=lambda x: x.created_at, reverse=True)
        elif sort_by == "price":
            results.sort(key=lambda x: x.price)

        return results

    def get_trending_plugins(self, limit: int = 10) -> List[MarketplaceListing]:
        published = [
            lst for lst in self.listings.values()
            if lst.status == ListingStatus.PUBLISHED
        ]
        published.sort(
            key=lambda x: x.download_count + (x.ratings * 100),
            reverse=True,
        )
        return published[:limit]

    def get_category_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for lst in self.listings.values():
            if lst.status == ListingStatus.PUBLISHED:
                counts[lst.category] = counts.get(lst.category, 0) + 1
        return counts

    # ------------------------------------------------------------------
    # Reviews
    # ------------------------------------------------------------------

    def add_review(
        self,
        listing_id: str,
        tenant_id: str,
        rating: int,
        title: str,
        comment: str,
    ) -> Optional[PluginReview]:
        if listing_id not in self.listings:
            return None
        if not (1 <= rating <= 5):
            return None

        review = PluginReview(
            review_id=str(uuid.uuid4()),
            listing_id=listing_id,
            tenant_id=tenant_id,
            rating=rating,
            title=title,
            comment=comment,
        )
        self.reviews[review.review_id] = review

        # Recompute aggregate rating
        all_r = [r for r in self.reviews.values() if r.listing_id == listing_id]
        listing = self.listings[listing_id]
        listing.ratings = sum(r.rating for r in all_r) / len(all_r)
        listing.review_count = len(all_r)
        listing.updated_at = datetime.utcnow()

        logger.info("Review added for %s: %d stars", listing_id, rating)
        return review

    def get_reviews(self, listing_id: str) -> List[PluginReview]:
        return [r for r in self.reviews.values() if r.listing_id == listing_id]

    # ------------------------------------------------------------------
    # Installations
    # ------------------------------------------------------------------

    def record_installation(self, tenant_id: str, plugin_id: str) -> None:
        self.installations.setdefault(tenant_id, [])
        if plugin_id not in self.installations[tenant_id]:
            self.installations[tenant_id].append(plugin_id)

        for listing in self.listings.values():
            if listing.plugin_id == plugin_id:
                listing.download_count += 1
                logger.info("Download count for %s: %d", listing.name, listing.download_count)


marketplace = Marketplace()
