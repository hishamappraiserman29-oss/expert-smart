"""
install_plugin.py — CLI tool to install a plugin for a tenant.

Usage:
  python scripts/install_plugin.py --plugin <plugin_id> --tenant <tenant_id>
                                   [--config '{"key": "value"}']
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(levelname)s — %(message)s")
logger = logging.getLogger(__name__)


def install_plugin_cli(plugin_id: str, tenant_id: str, config: dict) -> dict:
    from plugins.plugin_system import plugin_system
    from plugins.plugin_registry import plugin_registry
    from marketplace.marketplace import marketplace

    meta = plugin_registry.get(plugin_id)
    if meta is None:
        logger.error("Plugin not found in registry: %s", plugin_id)
        return {"success": False, "error": "Plugin not in registry"}

    if plugin_id not in plugin_system.plugins:
        logger.error("Plugin not loaded in plugin system: %s", plugin_id)
        return {"success": False, "error": "Plugin not loaded"}

    instance = plugin_system.install_plugin(
        tenant_id=tenant_id,
        plugin_id=plugin_id,
        config=config,
    )
    if instance is None:
        return {"success": False, "error": "Installation failed"}

    marketplace.record_installation(tenant_id, plugin_id)

    logger.info("Plugin %s installed for tenant %s", meta.name, tenant_id)
    return {
        "success": True,
        "plugin": instance.to_dict(),
        "metadata": meta.to_dict(),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Install a plugin for a tenant")
    parser.add_argument("--plugin", required=True, help="Plugin ID")
    parser.add_argument("--tenant", required=True, help="Tenant ID")
    parser.add_argument("--config", default="{}", help="JSON configuration")
    args = parser.parse_args()

    cfg = json.loads(args.config)
    result = install_plugin_cli(args.plugin, args.tenant, cfg)
    if result["success"]:
        print(f"\nPlugin installed: {result['plugin']['name']}")
        print(f"Status         : {result['plugin']['status']}")
    else:
        print(f"\nInstallation failed: {result['error']}")
        sys.exit(1)
