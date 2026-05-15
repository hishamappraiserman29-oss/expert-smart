"""
mcp_setup.py — Claude Desktop MCP Configuration Generator (Phase 16.1)

Generates the claude_desktop_config.json required to register Expert Smart
as an MCP server in Claude Desktop.

Usage (from the project root):
    python core_engine/mcp_setup.py             # print config to stdout
    python core_engine/mcp_setup.py --install   # write to %APPDATA%/Claude/
    python core_engine/mcp_setup.py --verify    # check prerequisites only

Claude Desktop config location (Windows):
    %APPDATA%\\Claude\\claude_desktop_config.json
    → C:\\Users\\<user>\\AppData\\Roaming\\Claude\\claude_desktop_config.json

Once installed, restart Claude Desktop and the 10 Expert Smart tools will
appear in the MCP tools panel.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List


# ── Paths ─────────────────────────────────────────────────────────────────────

_THIS_FILE   = Path(__file__).resolve()
_CORE_DIR    = _THIS_FILE.parent                           # core_engine/
_BRIDGE_FILE = _CORE_DIR / "mcp_bridge.py"
_PYTHON_EXE  = sys.executable

_APPDATA         = os.environ.get("APPDATA", "")
_CLAUDE_DIR      = Path(_APPDATA) / "Claude" if _APPDATA else None
_CLAUDE_CFG_PATH = _CLAUDE_DIR / "claude_desktop_config.json" if _CLAUDE_DIR else None

_SERVER_NAME = "expert_smart"


# ── Config builder ────────────────────────────────────────────────────────────

class MCPSetup:
    """Generate, verify, and install the Claude Desktop MCP configuration."""

    def __init__(
        self,
        python_exe:  str  = _PYTHON_EXE,
        bridge_file: Path = _BRIDGE_FILE,
        core_dir:    Path = _CORE_DIR,
    ) -> None:
        self.python_exe  = str(python_exe)
        self.bridge_file = Path(bridge_file)
        self.core_dir    = Path(core_dir)

    # ── Config generation ─────────────────────────────────────────────────────

    def generate_config(self) -> Dict:
        """
        Return the full claude_desktop_config.json dict.

        If an existing config already has mcpServers entries they are preserved;
        the expert_smart server is added or updated.
        """
        return {
            "mcpServers": {
                _SERVER_NAME: {
                    "command": self.python_exe,
                    "args":    [str(self.bridge_file)],
                    "env": {
                        "PYTHONPATH": str(self.core_dir),
                    },
                }
            }
        }

    def merge_into_existing(self, existing: Dict) -> Dict:
        """
        Merge the expert_smart server entry into an existing config dict,
        preserving all other mcpServers entries.
        """
        merged = dict(existing)
        servers = dict(merged.get("mcpServers", {}))
        servers[_SERVER_NAME] = self.generate_config()["mcpServers"][_SERVER_NAME]
        merged["mcpServers"] = servers
        return merged

    # ── Verification ──────────────────────────────────────────────────────────

    def check_prerequisites(self) -> List[Dict]:
        """
        Run prerequisite checks.  Returns a list of check result dicts:
            {"name": str, "ok": bool, "detail": str}
        """
        checks = []

        # 1. Python executable exists
        checks.append({
            "name":   "Python executable",
            "ok":     Path(self.python_exe).exists(),
            "detail": self.python_exe,
        })

        # 2. mcp_bridge.py exists
        checks.append({
            "name":   "mcp_bridge.py",
            "ok":     self.bridge_file.exists(),
            "detail": str(self.bridge_file),
        })

        # 3. fastmcp importable
        try:
            result = subprocess.run(
                [self.python_exe, "-c", "import fastmcp; print(fastmcp.__version__)"],
                capture_output=True, text=True, timeout=10,
            )
            ok      = result.returncode == 0
            version = result.stdout.strip() if ok else result.stderr.strip()[:80]
        except Exception as exc:
            ok, version = False, str(exc)
        checks.append({"name": "fastmcp installed", "ok": ok, "detail": version})

        # 4. httpx importable
        try:
            result = subprocess.run(
                [self.python_exe, "-c", "import httpx; print(httpx.__version__)"],
                capture_output=True, text=True, timeout=10,
            )
            ok      = result.returncode == 0
            version = result.stdout.strip() if ok else result.stderr.strip()[:80]
        except Exception as exc:
            ok, version = False, str(exc)
        checks.append({"name": "httpx installed", "ok": ok, "detail": version})

        # 5. Claude Desktop config directory reachable
        if _CLAUDE_DIR:
            checks.append({
                "name":   "Claude Desktop config dir",
                "ok":     _CLAUDE_DIR.exists(),
                "detail": str(_CLAUDE_DIR),
            })
        else:
            checks.append({
                "name":   "Claude Desktop config dir",
                "ok":     False,
                "detail": "APPDATA env var not set",
            })

        return checks

    # ── Install ───────────────────────────────────────────────────────────────

    def install(self, target_path: Path = _CLAUDE_CFG_PATH) -> Dict:
        """
        Write (or update) claude_desktop_config.json at target_path.
        If the file already exists, its mcpServers entries are preserved.

        Returns {"ok": bool, "path": str, "action": "created"|"updated"|"error", "error": str|None}
        """
        if target_path is None:
            return {"ok": False, "path": None, "action": "error",
                    "error": "APPDATA not set — cannot determine config path"}
        try:
            target_path = Path(target_path)
            target_path.parent.mkdir(parents=True, exist_ok=True)

            if target_path.exists():
                existing = json.loads(target_path.read_text(encoding="utf-8"))
                config   = self.merge_into_existing(existing)
                action   = "updated"
            else:
                config = self.generate_config()
                action = "created"

            target_path.write_text(
                json.dumps(config, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            return {"ok": True, "path": str(target_path), "action": action, "error": None}
        except Exception as exc:
            return {"ok": False, "path": str(target_path), "action": "error",
                    "error": str(exc)}

    def print_config(self) -> None:
        """Print the generated config to stdout (for manual copy-paste)."""
        cfg = self.generate_config()
        print(json.dumps(cfg, indent=2, ensure_ascii=False))

    def print_prerequisites(self) -> bool:
        """Print prerequisite check results.  Returns True if all pass."""
        checks  = self.check_prerequisites()
        all_ok  = all(c["ok"] for c in checks)
        print("Prerequisite checks:")
        for c in checks:
            mark = "OK  " if c["ok"] else "FAIL"
            print(f"  [{mark}] {c['name']}: {c['detail']}")
        return all_ok


# ── CLI entry point ───────────────────────────────────────────────────────────

def _main() -> None:
    args    = sys.argv[1:]
    setup   = MCPSetup()

    if "--verify" in args:
        ok = setup.print_prerequisites()
        sys.exit(0 if ok else 1)

    elif "--install" in args:
        print("Prerequisite check:")
        ok = setup.print_prerequisites()
        if not ok:
            print("\nAborted — fix the issues above before installing.")
            sys.exit(1)

        result = setup.install()
        if result["ok"]:
            print(f"\nConfig {result['action']}: {result['path']}")
            print("\nNext steps:")
            print("  1. Restart Claude Desktop")
            print(f"  2. Look for '{_SERVER_NAME}' in the MCP tools panel")
            print("  3. Start Expert Smart: python core_engine/bridge_api.py")
            print("  4. Ask Claude to call health_check()")
        else:
            print(f"\nInstall failed: {result['error']}")
            sys.exit(1)

    else:
        # Default: print config for manual copy-paste
        print("# Generated claude_desktop_config.json")
        print(f"# Copy to: {_CLAUDE_CFG_PATH}")
        print()
        setup.print_config()


if __name__ == "__main__":
    _main()
