"""
E2E conftest — boots bridge_api on port 5000 for the test session.

Port 5000 is hardcoded in bridge_api.py (waitress / Flask fallback).
The fixture detects whether the server is already listening (developer
already running the app) and reuses it rather than starting a second one.
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
_PORT = 5000
_BASE_URL = f"http://{_HOST}:{_PORT}"
_HEALTH = f"{_BASE_URL}/api/advisor/health"


def _is_listening() -> bool:
    """Return True if something is already accepting connections on port 5000."""
    try:
        with socket.create_connection((_HOST, _PORT), timeout=1):
            return True
    except OSError:
        return False


def _wait_ready(timeout: float = 20.0) -> bool:
    """Poll the health endpoint until it responds 200 or timeout expires."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(_HEALTH, timeout=2) as r:
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

    Strategy:
    1. If port 5000 is already listening, reuse it (dev server running).
    2. Otherwise, start bridge_api.py as a subprocess and wait up to 20s.
    3. Terminate only if WE started it.
    """
    proc = None

    if _is_listening():
        # Server already up — reuse; do not kill at teardown.
        yield _BASE_URL
        return

    # Start the server ourselves.
    proc = subprocess.Popen(
        [sys.executable, str(_BRIDGE)],
        cwd=str(_PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    if not _wait_ready(timeout=20.0):
        proc.terminate()
        proc.wait(timeout=5)
        pytest.fail(
            f"bridge_api.py did not become ready within 20 s. "
            f"Check that port {_PORT} is free and the server starts correctly."
        )

    yield _BASE_URL

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


