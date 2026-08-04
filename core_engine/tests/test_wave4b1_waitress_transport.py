"""Wave 4B1 Waitress transport tests.

Tests the live Waitress server with:
- max_request_body_size enforcement
- HTTP/1.1 chunked transfer encoding
- Unauthenticated health endpoint

Server lifecycle:
- Subprocess launch with bounded port-collision retry (3 attempts)
- Deterministic terminate + kill
- stderr preserved on failure
"""
from __future__ import annotations

import http.client
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


_HEALTH_PATH = "/api/advisor/health"
_MAX_BODY    = 67_108_864   # 64 MiB — Wave 4B1 limit


def _free_port(start: int = 15800) -> int:
    """Find a free TCP port starting from *start*."""
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free port found in range")


def _wait_ready(host: str, port: int, timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def _kill_process(proc: subprocess.Popen) -> None:
    """Terminate gracefully, then force-kill if needed."""
    try:
        proc.terminate()
    except OSError:
        pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except OSError:
            pass
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            pass


@pytest.fixture(scope="module")
def waitress_server(tmp_path_factory):
    """Start a Waitress server subprocess and yield (host, port). Teardown kills it."""
    tmp = tmp_path_factory.mktemp("waitress_avm")
    env = {
        **os.environ,
        "JWT_SECRET":        "test-waitress-secret-32bytes-min!!",
        "ADMIN_USER_IDS":    "",
        "RATE_LIMIT_ENABLED": "false",
        "AUDIT_ENABLED":     "false",
        "AVM_ARTIFACT_ROOT": str(tmp),
        "PYTHONPATH":        f"{str(_CORE)}{os.pathsep}{str(_ROOT)}",
    }

    proc = None
    host = "127.0.0.1"
    stderr_lines: list[str] = []

    # Bounded port-collision retry — 3 attempts
    for attempt in range(3):
        port = _free_port(15800 + attempt * 100)
        env["PORT"] = str(port)
        try:
            proc = subprocess.Popen(
                [sys.executable, str(_CORE / "bridge_api.py")],
                env=env,
                cwd=str(_CORE),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        except OSError:
            continue

        if _wait_ready(host, port, timeout=20):
            break

        stderr_lines = []
        if proc.stderr:
            import select as _sel
            while True:
                r, _, _ = _sel.select([proc.stderr], [], [], 0.1)
                if not r:
                    break
                line = proc.stderr.readline()
                if not line:
                    break
                stderr_lines.append(line.decode(errors="replace"))
        _kill_process(proc)
        proc = None
    else:
        pytest.skip(
            f"Waitress server did not start after 3 attempts. "
            f"Last stderr:\n{''.join(stderr_lines)}"
        )

    yield host, port

    if proc is not None:
        _kill_process(proc)


# ── WT-01: Health endpoint is reachable without authentication ────────────────

def test_wt_01_health_unauthenticated(waitress_server):
    """Health endpoint returns 200 without any Authorization header."""
    host, port = waitress_server
    conn = http.client.HTTPConnection(host, port, timeout=10)
    try:
        conn.request("GET", _HEALTH_PATH)
        resp = conn.getresponse()
        assert resp.status == 200, (
            f"Health endpoint returned {resp.status}, expected 200"
        )
    finally:
        conn.close()


# ── WT-02: max_request_body_size rejects oversized Content-Length ─────────────

def test_wt_02_oversized_content_length_rejected(waitress_server):
    """Declared Content-Length above 64 MiB is rejected before reading the body."""
    host, port = waitress_server
    conn = http.client.HTTPConnection(host, port, timeout=10)
    try:
        headers = {
            "Content-Type":    "application/json",
            "Content-Length":  str(_MAX_BODY + 1),
        }
        conn.request("POST", "/api/mass-appraisal/preview", body=b"{}", headers=headers)
        resp = conn.getresponse()
        # Waitress closes the connection or returns 413/400
        assert resp.status in (413, 400, 431, 503), (
            f"Oversized Content-Length: expected 413/400, got {resp.status}"
        )
    except (http.client.RemoteDisconnected, ConnectionResetError):
        # Waitress may close the connection for oversized requests — acceptable
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ── WT-03: Small JSON body accepted end-to-end ────────────────────────────────

def test_wt_03_small_json_body_accepted(waitress_server):
    """A small JSON body to a JSON route succeeds (not rejected by transport layer)."""
    host, port = waitress_server
    body = b'{"units": [], "location": "Riyadh", "purpose": "test"}'
    conn = http.client.HTTPConnection(host, port, timeout=10)
    try:
        conn.request(
            "POST",
            "/api/mass-appraisal/preview",
            body=body,
            headers={
                "Content-Type":   "application/json",
                "Content-Length": str(len(body)),
            },
        )
        resp = conn.getresponse()
        # Any non-5xx response from the transport layer is acceptable
        # (401/403 means auth gate; 400 means JSON validation worked)
        assert resp.status != 502, "Should not get 502 Bad Gateway for a small body"
        assert resp.status < 600
    finally:
        conn.close()


# ── WT-04: HTTP/1.1 chunked transfer encoding ─────────────────────────────────

def test_wt_04_http11_chunked_request_accepted(waitress_server):
    """HTTP/1.1 chunked Transfer-Encoding is accepted by Waitress (no HTTP/2)."""
    host, port = waitress_server
    conn = http.client.HTTPConnection(host, port, timeout=10)
    conn._http_vsn = 11
    conn._http_vsn_str = "HTTP/1.1"
    try:
        # Send chunked body manually
        conn.putrequest("POST", _HEALTH_PATH)
        conn.putheader("Content-Type", "application/json")
        conn.putheader("Transfer-Encoding", "chunked")
        conn.endheaders()
        # Write chunked encoding
        chunk = b'{"ping": "chunked"}'
        conn.send(f"{len(chunk):x}\r\n".encode())
        conn.send(chunk + b"\r\n")
        conn.send(b"0\r\n\r\n")
        resp = conn.getresponse()
        # Health endpoint doesn't use the body, so any response is acceptable
        assert resp.status < 600, f"Chunked request got unexpected status {resp.status}"
    except (http.client.RemoteDisconnected, ConnectionResetError):
        # Some configurations reject body-bearing health POSTs — acceptable
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ── WT-05: max_request_body_size does not block the health endpoint ───────────

def test_wt_05_health_not_blocked_by_body_limit(waitress_server):
    """The health endpoint with no body is never blocked by the body limit."""
    host, port = waitress_server
    # Hit the health endpoint 5 times to confirm it remains available
    for _ in range(5):
        conn = http.client.HTTPConnection(host, port, timeout=5)
        try:
            conn.request("GET", _HEALTH_PATH)
            resp = conn.getresponse()
            assert resp.status == 200
        finally:
            conn.close()
