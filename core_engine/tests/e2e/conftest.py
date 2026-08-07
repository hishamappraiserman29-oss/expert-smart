"""
E2E conftest — boots bridge_api on a fresh unused port for the test session.

Strategy:
1. If E2E_BASE_URL is set in the environment, use it directly — never reuse port 5000
   silently. The CI workflow sets E2E_BASE_URL after starting a fresh server.
2. Otherwise, find an unused port (never port 5000), start bridge_api.py on it,
   wait up to 20 s for it to be healthy, and terminate it on teardown.
3. If the server does not become healthy within the timeout, fail immediately —
   do not silently reuse any existing server.

STALE_SERVER_REUSE_POSSIBLE = False
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_BRIDGE = _PROJECT_ROOT / "core_engine" / "bridge_api.py"
_HOST = "127.0.0.1"


def _find_free_port(start: int = 15900, avoid: int = 5000) -> int:
    """Find a free TCP port, skipping avoid (default 5000)."""
    for port in range(start, start + 200):
        if port == avoid:
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((_HOST, port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port found in range {start}..{start + 200}")


def _wait_ready(base_url: str, timeout: float = 20.0) -> bool:
    """Poll the health endpoint until it responds 200 or timeout expires."""
    health = f"{base_url}/api/advisor/health"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(health, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.4)
    return False


@pytest.fixture(scope="session")
def live_server():
    """
    Yields the base URL of the running bridge_api server.

    Priority:
    1. E2E_BASE_URL environment variable (CI sets this to a pre-started fresh server).
    2. Start a fresh server on a newly allocated port (never reuse port 5000).

    If E2E_BASE_URL is set but not reachable, the test session fails immediately —
    stale port 5000 reuse is NEVER a fallback.
    """
    proc = None
    base_url = os.environ.get("E2E_BASE_URL", "").strip()

    if base_url:
        # CI-supplied URL — verify it is reachable before proceeding
        if not _wait_ready(base_url, timeout=10.0):
            pytest.fail(
                f"E2E_BASE_URL={base_url!r} was set but server is not healthy. "
                "Check that the CI workflow started the server before running tests."
            )
        yield base_url
        return

    # Local run — allocate a fresh port (not 5000) and start a subprocess
    port = _find_free_port()
    base_url = f"http://{_HOST}:{port}"

    env = {
        **os.environ,
        "PORT": str(port),
        "AVM_ARTIFACT_ROOT": str(Path(os.environ.get("TEMP", "/tmp")) / "expert_smart_avm_e2e"),
    }

    # Capture server stderr for diagnostics on failure
    server_log = Path(os.environ.get("TEMP", "/tmp")) / "bridge_api_e2e_server.log"
    log_fh = open(str(server_log), "w")

    proc = subprocess.Popen(
        [sys.executable, str(_BRIDGE)],
        cwd=str(_PROJECT_ROOT),
        env=env,
        stdout=log_fh,
        stderr=log_fh,
    )

    if not _wait_ready(base_url, timeout=25.0):
        log_fh.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        try:
            print(f"\n--- bridge_api server log ({server_log}) ---")
            print(server_log.read_text(encoding="utf-8", errors="replace")[-2000:])
        except Exception:
            pass
        pytest.fail(
            f"bridge_api.py on port {port} did not become ready within 25 s. "
            "Check the server log above."
        )

    yield base_url

    log_fh.close()
    proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 800},
    }
