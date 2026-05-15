"""
test_phase_16_1_e2e.py — Phase 16.1 Claude Desktop MCP Config (10 tests)

Tests:
  01  MCPSetup instantiation — python_exe, bridge_file, core_dir set correctly
  02  generate_config() structure — mcpServers key, server name, command, args
  03  Config command points to the real Python executable
  04  Config args[0] is an existing mcp_bridge.py path
  05  Config env contains PYTHONPATH pointing to core_engine/
  06  merge_into_existing() preserves pre-existing mcpServers entries
  07  merge_into_existing() overwrites stale expert_smart entry
  08  install() creates config file + parent directory (temp target)
  09  install() updates existing config without clobbering other servers
  10  check_prerequisites() returns list of dicts with ok/name/detail keys
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

_CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_CORE))
os.chdir(str(_CORE))

from mcp_setup import MCPSetup, _BRIDGE_FILE, _CORE_DIR, _PYTHON_EXE, _SERVER_NAME


# ── Helpers ───────────────────────────────────────────────────────────────────

def _setup() -> MCPSetup:
    return MCPSetup()


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_01_instantiation_defaults():
    s = _setup()
    assert s.python_exe  == str(_PYTHON_EXE)
    assert s.bridge_file == _BRIDGE_FILE
    assert s.core_dir    == _CORE_DIR
    assert s.bridge_file.name == "mcp_bridge.py"


def test_02_generate_config_structure():
    cfg = _setup().generate_config()

    assert "mcpServers" in cfg
    servers = cfg["mcpServers"]
    assert _SERVER_NAME in servers, f"Expected '{_SERVER_NAME}' in mcpServers"

    entry = servers[_SERVER_NAME]
    assert "command" in entry
    assert "args"    in entry
    assert "env"     in entry
    assert isinstance(entry["args"], list)
    assert len(entry["args"]) == 1


def test_03_config_command_is_python():
    entry = _setup().generate_config()["mcpServers"][_SERVER_NAME]
    cmd   = entry["command"]
    # Must be a recognisable Python executable
    assert "python" in cmd.lower(), f"Expected python executable, got: {cmd}"
    assert Path(cmd).exists(), f"Python executable does not exist: {cmd}"


def test_04_config_args_point_to_bridge():
    entry       = _setup().generate_config()["mcpServers"][_SERVER_NAME]
    bridge_path = Path(entry["args"][0])
    assert bridge_path.name == "mcp_bridge.py", \
        f"Expected mcp_bridge.py in args, got: {bridge_path.name}"
    assert bridge_path.exists(), \
        f"mcp_bridge.py not found at: {bridge_path}"


def test_05_config_env_has_pythonpath():
    entry    = _setup().generate_config()["mcpServers"][_SERVER_NAME]
    env      = entry["env"]
    assert "PYTHONPATH" in env, "PYTHONPATH missing from env"
    pp_path  = Path(env["PYTHONPATH"])
    assert pp_path.exists(),           f"PYTHONPATH dir does not exist: {pp_path}"
    assert (pp_path / "mcp_bridge.py").exists(), \
        "PYTHONPATH does not contain mcp_bridge.py"


def test_06_merge_preserves_other_servers():
    existing = {
        "mcpServers": {
            "other_tool": {
                "command": "node",
                "args":    ["/path/to/other.js"],
            }
        }
    }
    merged = _setup().merge_into_existing(existing)
    assert "other_tool"  in merged["mcpServers"], "Pre-existing server was removed"
    assert _SERVER_NAME  in merged["mcpServers"], "expert_smart server missing"
    assert merged["mcpServers"]["other_tool"]["command"] == "node"


def test_07_merge_overwrites_stale_entry():
    old_entry = {"command": "old_python", "args": ["/old/path.py"], "env": {}}
    existing  = {"mcpServers": {_SERVER_NAME: old_entry}}
    merged    = _setup().merge_into_existing(existing)
    updated   = merged["mcpServers"][_SERVER_NAME]
    assert updated["command"] != "old_python", "Stale command was not updated"
    assert "mcp_bridge.py" in updated["args"][0], "Stale args were not updated"


def test_08_install_creates_file_and_dir():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "subdir" / "claude_desktop_config.json"
        assert not target.exists()

        result = _setup().install(target_path=target)
        assert result["ok"],  f"Install failed: {result.get('error')}"
        assert result["action"] == "created"
        assert target.exists()

        # File is valid JSON with correct structure
        content = json.loads(target.read_text(encoding="utf-8"))
        assert _SERVER_NAME in content["mcpServers"]


def test_09_install_updates_existing():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "claude_desktop_config.json"

        # Pre-populate with another server
        initial = {"mcpServers": {"third_party": {"command": "npx", "args": []}}}
        target.write_text(json.dumps(initial), encoding="utf-8")

        result = _setup().install(target_path=target)
        assert result["ok"]
        assert result["action"] == "updated"

        content = json.loads(target.read_text(encoding="utf-8"))
        # Both servers present
        assert "third_party" in content["mcpServers"], "Existing server was lost"
        assert _SERVER_NAME  in content["mcpServers"], "expert_smart not added"


def test_10_check_prerequisites_structure():
    checks = _setup().check_prerequisites()
    assert isinstance(checks, list)
    assert len(checks) >= 4   # python, bridge file, fastmcp, httpx (+ optional claude dir)

    for c in checks:
        assert "name"   in c, f"Missing 'name' in check: {c}"
        assert "ok"     in c, f"Missing 'ok' in check: {c}"
        assert "detail" in c, f"Missing 'detail' in check: {c}"
        assert isinstance(c["ok"], bool)

    # Core checks must pass on this machine
    names = {c["name"] for c in checks}
    assert "Python executable"  in names
    assert "mcp_bridge.py"      in names
    assert "fastmcp installed"  in names
    assert "httpx installed"    in names

    # All core infrastructure checks must be OK
    core = {c["name"]: c["ok"] for c in checks
            if c["name"] != "Claude Desktop config dir"}
    failing = [n for n, ok in core.items() if not ok]
    assert not failing, f"Core prerequisite checks failed: {failing}"


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for fn in tests:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
            passed += 1
        except Exception as exc:
            import traceback
            print(f"  FAIL  {fn.__name__}: {exc}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed}/{passed + failed} tests passed")
