"""
paginator.py — PH.4 Generic List Paginator

Provides consistent pagination for any list-based API endpoint or
in-memory dataset.  No database dependency — pass in a Python list,
get back a PageResult.

Classes:
    PageRequest  — validated pagination / sort parameters
    PageResult   — one page of results with navigation metadata
    Paginator    — stateless helper that produces PageResults
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Union


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_PAGE_SIZE = 20
_MAX_PAGE_SIZE = 200
_MIN_PAGE_SIZE = 1


# ---------------------------------------------------------------------------
# PageRequest
# ---------------------------------------------------------------------------

@dataclass
class PageRequest:
    """
    Validated request parameters for a paginated query.

    Attributes
    ----------
    page       : 1-based page index (clamped to >= 1)
    page_size  : items per page (clamped to [1, MAX_PAGE_SIZE])
    sort_by    : field name to sort on (None = preserve original order)
    sort_dir   : "asc" or "desc" (default "asc")
    """

    page: int = 1
    page_size: int = _DEFAULT_PAGE_SIZE
    sort_by: Optional[str] = None
    sort_dir: str = "asc"

    def __post_init__(self) -> None:
        self.page = max(1, int(self.page))
        self.page_size = max(_MIN_PAGE_SIZE, min(_MAX_PAGE_SIZE, int(self.page_size)))
        self.sort_dir = "desc" if str(self.sort_dir).lower() == "desc" else "asc"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PageRequest":
        """Build a PageRequest from a raw dict (e.g. request.args / JSON body)."""
        return cls(
            page=int(data.get("page", 1)),
            page_size=int(data.get("page_size", data.get("per_page", _DEFAULT_PAGE_SIZE))),
            sort_by=data.get("sort_by") or data.get("sort"),
            sort_dir=str(data.get("sort_dir", data.get("order", "asc"))),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page": self.page,
            "page_size": self.page_size,
            "sort_by": self.sort_by,
            "sort_dir": self.sort_dir,
        }


# ---------------------------------------------------------------------------
# PageResult
# ---------------------------------------------------------------------------

@dataclass
class PageResult:
    """
    One page of results with complete navigation metadata.

    Attributes
    ----------
    items        : the slice of records for this page
    total        : total number of records across all pages
    page         : current 1-based page index
    page_size    : requested items per page (may differ from len(items) on last page)
    total_pages  : total number of pages
    has_next     : True if there is a next page
    has_prev     : True if there is a previous page
    """

    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": self.items,
            "pagination": {
                "total": self.total,
                "page": self.page,
                "page_size": self.page_size,
                "total_pages": self.total_pages,
                "has_next": self.has_next,
                "has_prev": self.has_prev,
            },
        }


# ---------------------------------------------------------------------------
# Paginator
# ---------------------------------------------------------------------------

class Paginator:
    """
    Stateless helper that slices a list according to a PageRequest.

    Usage
    -----
    result = Paginator.paginate(items=my_list, request=req)
    # or with defaults:
    result = Paginator.paginate(items=my_list, page=2, page_size=10)
    """

    # -- Main entry point -----------------------------------------------------

    @staticmethod
    def paginate(
        items: Sequence[Any],
        request: Optional[PageRequest] = None,
        *,
        page: int = 1,
        page_size: int = _DEFAULT_PAGE_SIZE,
        sort_by: Optional[str] = None,
        sort_dir: str = "asc",
    ) -> PageResult:
        """
        Return a PageResult for *items* according to the given pagination
        parameters.  You may pass a PageRequest object OR keyword arguments;
        the PageRequest takes precedence.

        Sorting is applied before slicing.  If *sort_by* names a key that
        does not exist in some items, those items sort last.
        """
        if request is None:
            request = PageRequest(
                page=page, page_size=page_size,
                sort_by=sort_by, sort_dir=sort_dir,
            )

        # Sort (optional)
        working: List[Any] = list(items)
        if request.sort_by:
            reverse = request.sort_dir == "desc"
            working = Paginator._sort(working, request.sort_by, reverse)

        total = len(working)
        total_pages = max(1, math.ceil(total / request.page_size)) if total > 0 else 1

        # Clamp page to valid range
        clamped_page = max(1, min(request.page, total_pages))

        start = (clamped_page - 1) * request.page_size
        end = start + request.page_size
        page_items = working[start:end]

        return PageResult(
            items=page_items,
            total=total,
            page=clamped_page,
            page_size=request.page_size,
            total_pages=total_pages,
            has_next=clamped_page < total_pages,
            has_prev=clamped_page > 1,
        )

    @staticmethod
    def from_dict(
        items: Sequence[Any],
        params: Dict[str, Any],
    ) -> PageResult:
        """Convenience: build from a raw parameter dict and paginate."""
        req = PageRequest.from_dict(params)
        return Paginator.paginate(items, request=req)

    # -- Sorting helper -------------------------------------------------------

    @staticmethod
    def _sort(items: List[Any], sort_by: str, reverse: bool) -> List[Any]:
        """
        Sort *items* by *sort_by*.

        Works for:
          - list of dicts  → item[sort_by]
          - list of objects → getattr(item, sort_by)
        Items missing the key sort last.
        """
        _SENTINEL = object()

        def key_fn(item: Any) -> Any:
            if isinstance(item, dict):
                val = item.get(sort_by, _SENTINEL)
            else:
                val = getattr(item, sort_by, _SENTINEL)
            return (val is _SENTINEL, val if val is not _SENTINEL else "")

        try:
            return sorted(items, key=key_fn, reverse=reverse)
        except TypeError:
            # Mixed types — fall back to str comparison
            def safe_key(item: Any) -> Any:
                if isinstance(item, dict):
                    val = item.get(sort_by, "")
                else:
                    val = getattr(item, sort_by, "")
                return (val is None, str(val) if val is not None else "")

            return sorted(items, key=safe_key, reverse=reverse)
