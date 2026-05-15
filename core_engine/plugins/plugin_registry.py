"""
plugin_registry.py — Central registry for plugin discovery.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .plugin_system import PluginMetadata, PluginType

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Discover, search, and categorise available plugins."""

    def __init__(self) -> None:
        self._registry: Dict[str, PluginMetadata] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, metadata: PluginMetadata) -> bool:
        if metadata.plugin_id in self._registry:
            logger.warning("Plugin already in registry: %s", metadata.plugin_id)
            return False
        self._registry[metadata.plugin_id] = metadata
        logger.info("Registry: added %s (%s)", metadata.name, metadata.plugin_id)
        return True

    def unregister(self, plugin_id: str) -> bool:
        if plugin_id not in self._registry:
            return False
        del self._registry[plugin_id]
        return True

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, plugin_id: str) -> Optional[PluginMetadata]:
        return self._registry.get(plugin_id)

    def list_all(self) -> List[PluginMetadata]:
        return list(self._registry.values())

    def search(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        plugin_type: Optional[PluginType] = None,
    ) -> List[PluginMetadata]:
        results = list(self._registry.values())

        if query:
            q = query.lower()
            results = [
                m for m in results
                if q in m.name.lower() or q in m.description.lower()
            ]

        if plugin_type:
            results = [m for m in results if m.plugin_type == plugin_type]

        return results

    def get_by_type(self, plugin_type: PluginType) -> List[PluginMetadata]:
        return [m for m in self._registry.values() if m.plugin_type == plugin_type]

    def list_categories(self) -> List[str]:
        return sorted({m.plugin_type.value for m in self._registry.values()})

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        all_plugins = list(self._registry.values())
        by_type: Dict[str, int] = {}
        for m in all_plugins:
            by_type[m.plugin_type.value] = by_type.get(m.plugin_type.value, 0) + 1
        return {
            "total": len(all_plugins),
            "by_type": by_type,
            "requires_credentials": sum(1 for m in all_plugins if m.requires_credentials),
        }


plugin_registry = PluginRegistry()
