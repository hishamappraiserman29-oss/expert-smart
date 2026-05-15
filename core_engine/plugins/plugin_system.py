"""
plugin_system.py — Plugin manager for Expert Smart integrations.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class PluginStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISABLED = "disabled"
    ERROR = "error"


class PluginType(str, Enum):
    INTEGRATION = "integration"
    EXTENSION = "extension"
    DATASOURCE = "datasource"
    EXPORT = "export"
    WEBHOOK = "webhook"


@dataclass
class PluginMetadata:
    name: str
    version: str
    plugin_type: PluginType
    description: str
    author: str
    author_email: str
    plugin_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    homepage: str = ""
    documentation: str = ""
    license: str = "MIT"
    requires_credentials: bool = False
    required_fields: List[str] = field(default_factory=list)
    api_version: str = "1.0"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        return {
            "plugin_id": self.plugin_id,
            "name": self.name,
            "version": self.version,
            "type": self.plugin_type.value,
            "description": self.description,
            "author": self.author,
            "author_email": self.author_email,
            "homepage": self.homepage,
            "documentation": self.documentation,
            "license": self.license,
            "requires_credentials": self.requires_credentials,
            "required_fields": self.required_fields,
            "api_version": self.api_version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class PluginInstance:
    plugin_id: str
    tenant_id: str
    name: str
    status: PluginStatus = PluginStatus.INACTIVE
    configuration: Dict[str, Any] = field(default_factory=dict)
    credentials: Dict[str, str] = field(default_factory=dict)
    installed_at: datetime = field(default_factory=datetime.utcnow)
    last_error: Optional[str] = None
    usage_stats: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "plugin_id": self.plugin_id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "status": self.status.value,
            "configuration": self.configuration,
            "has_credentials": bool(self.credentials),
            "installed_at": self.installed_at.isoformat(),
            "last_error": self.last_error,
            "usage_stats": self.usage_stats,
        }


class BasePlugin:
    """Base class every plugin must extend."""

    metadata: PluginMetadata

    def initialize(self, config: Dict[str, Any]) -> bool:
        raise NotImplementedError

    def validate_config(self, config: Dict[str, Any]) -> bool:
        for req in getattr(self.metadata, "required_fields", []):
            if req not in config:
                logger.error("Missing required config field: %s", req)
                return False
        return True

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    def on_install(self) -> bool:
        return True

    def on_uninstall(self) -> bool:
        return True

    def on_enable(self) -> bool:
        return True

    def on_disable(self) -> bool:
        return True

    def get_status(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.metadata.plugin_id,
            "name": self.metadata.name,
            "version": self.metadata.version,
            "status": "active",
        }


class PluginSystem:
    """Register, install, and execute plugins."""

    def __init__(self) -> None:
        self.plugins: Dict[str, BasePlugin] = {}
        self.instances: Dict[str, PluginInstance] = {}
        self.hooks: Dict[str, List[Callable]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_plugin(self, plugin: BasePlugin) -> bool:
        if not self._validate_plugin(plugin):
            return False
        pid = plugin.metadata.plugin_id
        if pid in self.plugins:
            logger.warning("Plugin already registered: %s", pid)
            return False
        self.plugins[pid] = plugin
        logger.info("Plugin registered: %s (%s)", plugin.metadata.name, pid)
        return True

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def install_plugin(
        self,
        tenant_id: str,
        plugin_id: str,
        config: Dict[str, Any],
        credentials: Optional[Dict[str, str]] = None,
    ) -> Optional[PluginInstance]:
        if plugin_id not in self.plugins:
            logger.error("Plugin not found: %s", plugin_id)
            return None

        plugin = self.plugins[plugin_id]

        if not plugin.validate_config(config):
            logger.error("Invalid configuration for %s", plugin_id)
            return None

        instance_id = f"{tenant_id}_{plugin_id}"
        instance = PluginInstance(
            plugin_id=plugin_id,
            tenant_id=tenant_id,
            name=plugin.metadata.name,
            configuration=config,
            credentials=credentials or {},
        )

        try:
            if not plugin.initialize(config):
                instance.status = PluginStatus.ERROR
                instance.last_error = "Initialization failed"
                return None

            if not plugin.on_install():
                instance.status = PluginStatus.ERROR
                instance.last_error = "Install hook failed"
                return None

            self.instances[instance_id] = instance
            instance.status = PluginStatus.ACTIVE
            logger.info("Plugin installed: %s for %s", plugin.metadata.name, tenant_id)
            return instance

        except Exception as exc:
            logger.error("Error installing plugin: %s", exc)
            instance.status = PluginStatus.ERROR
            instance.last_error = str(exc)
            return None

    def execute_plugin(
        self, tenant_id: str, plugin_id: str, *args: Any, **kwargs: Any
    ) -> Any:
        instance_id = f"{tenant_id}_{plugin_id}"
        if instance_id not in self.instances:
            logger.error("Plugin not installed: %s", plugin_id)
            return None

        instance = self.instances[instance_id]
        if instance.status != PluginStatus.ACTIVE:
            logger.error("Plugin not active: %s (status=%s)", plugin_id, instance.status)
            return None

        try:
            result = self.plugins[plugin_id].execute(*args, **kwargs)
            key = f"{plugin_id}_executions"
            instance.usage_stats[key] = instance.usage_stats.get(key, 0) + 1
            return result
        except Exception as exc:
            logger.error("Plugin execution error: %s", exc)
            instance.last_error = str(exc)
            instance.status = PluginStatus.ERROR
            return None

    def uninstall_plugin(self, tenant_id: str, plugin_id: str) -> bool:
        instance_id = f"{tenant_id}_{plugin_id}"
        if instance_id not in self.instances:
            return False
        try:
            plugin = self.plugins.get(plugin_id)
            if plugin:
                plugin.on_uninstall()
            del self.instances[instance_id]
            logger.info("Plugin uninstalled: %s", plugin_id)
            return True
        except Exception as exc:
            logger.error("Error uninstalling plugin: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_plugins(self) -> List[PluginMetadata]:
        return [p.metadata for p in self.plugins.values()]

    def list_installed_plugins(self, tenant_id: str) -> List[PluginInstance]:
        return [i for i in self.instances.values() if i.tenant_id == tenant_id]

    def get_plugin_status(self, tenant_id: str, plugin_id: str) -> Optional[Dict]:
        instance_id = f"{tenant_id}_{plugin_id}"
        if instance_id not in self.instances:
            return None
        instance = self.instances[instance_id]
        plugin = self.plugins[plugin_id]
        return {
            "instance": instance.to_dict(),
            "metadata": plugin.metadata.to_dict(),
            "status": plugin.get_status(),
        }

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------

    def register_hook(self, hook_name: str, callback: Callable) -> None:
        self.hooks.setdefault(hook_name, []).append(callback)

    def trigger_hook(self, hook_name: str, *args: Any, **kwargs: Any) -> List[Any]:
        results = []
        for cb in self.hooks.get(hook_name, []):
            try:
                results.append(cb(*args, **kwargs))
            except Exception as exc:
                logger.error("Hook error in %s: %s", hook_name, exc)
        return results

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_plugin(self, plugin: BasePlugin) -> bool:
        if not hasattr(plugin, "metadata"):
            logger.error("Plugin missing metadata attribute")
            return False
        if not isinstance(plugin.metadata, PluginMetadata):
            logger.error("Plugin metadata must be a PluginMetadata instance")
            return False
        for method in ("initialize", "execute", "on_install", "on_uninstall"):
            if not hasattr(plugin, method):
                logger.error("Plugin missing required method: %s", method)
                return False
        return True


plugin_system = PluginSystem()
