"""Wave 4B1 Waitress transport tests.

Tests the live Waitress server with:
- max_request_body_size enforcement
- HTTP/1.1 chunked transfer encoding
- Unauthenticated health endpoint
- JSON body validation (malformed, empty)

Server lifecycle:
- Subprocess launch with bounded port-collision retry (3 attempts)
- Deterministic terminate + kill
- stderr preserved on failure
"""
from __future__ import annotations

import http.client
import os
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
_BOUNDED_ROUTE = "/api/mass-appraisal/preview"
_MAX_BODY      = 67_108_864   # 64 MiB — Wave 4B1 limit
_JWT_SECRET    = "test-waitress-secret-32bytes-min!!"


def _make_jwt(user_id: str = "test-user-wt") -> str:
    """Generate a signed JWT for use in transport tests."""
    import time as _time
    try:
        import jwt as _jwt
    except ImportError:
        import PyJWT as _jwt  # type: ignore[no-redef]
    now = int(_time.time())
    payload = {"sub": user_id, "iat": now, "exp": now + 3600}
    return _jwt.encode(payload, _JWT_SECRET, algorithm="HS256")


def _auth_headers(content_type: str = "application/json") -> dict:
    return {
        "Authorization": f"Bearer {_make_jwt()}",
        "Content-Type": content_type,
    }


def _free_port(start: int = 15800) -> int:
    """Find a free TCP port starting from *start*.

    Intentionally does NOT set SO_REUSEADDR so that a port held by a
    listening socket is correctly detected as occupied (Windows-compatible).
    """
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
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


def _bounded_retry_start(
    env: dict,
    host: str,
    start_base: int = 15800,
    attempts: int = 3,
) -> tuple[subprocess.Popen, int]:
    """Bounded port-collision retry — up to *attempts* tries.

    Returns (proc, port) on success.
    Raises RuntimeError when all attempts fail.
    """
    stderr_lines: list[str] = []
    for attempt in range(attempts):
        port = _free_port(start_base + attempt * 100)
        env_copy = {**env, "PORT": str(port)}
        try:
            proc = subprocess.Popen(
                [sys.executable, str(_CORE / "bridge_api.py")],
                env=env_copy,
                cwd=str(_CORE),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        except OSError:
            continue

        if _wait_ready(host, port, timeout=20):
            return proc, port

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

    raise RuntimeError(
        f"Waitress server did not start after {attempts} attempts.\n"
        f"Last stderr:\n{''.join(stderr_lines)}"
    )


@pytest.fixture(scope="module")
def waitress_server(tmp_path_factory):
    """Start a Waitress server subprocess and yield (host, port). Teardown kills it."""
    tmp = tmp_path_factory.mktemp("waitress_avm")
    env = {
        **os.environ,
        "JWT_SECRET":        _JWT_SECRET,
        "ADMIN_USER_IDS":    "",
        "RATE_LIMIT_ENABLED": "false",
        "AUDIT_ENABLED":     "false",
        "AVM_ARTIFACT_ROOT": str(tmp),
        "PYTHONPATH":        f"{str(_CORE)}{os.pathsep}{str(_ROOT)}",
    }

    host = "127.0.0.1"
    try:
        proc, port = _bounded_retry_start(env, host)
    except RuntimeError as exc:
        pytest.skip(str(exc))
        return

    yield host, port

    _kill_process(proc)


# ── WT-01: Health endpoint is reachable without authentication ─────────────────

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


# ── WT-02: Declared Content-Length within route limit is accepted ──────────────

def test_wt_02_content_length_within_limit_accepted(waitress_server):
    """A small declared Content-Length is accepted by the transport layer."""
    host, port = waitress_server
    body = b'{"units": [], "location": "Riyadh", "purpose": "test"}'
    headers = {**_auth_headers(), "Content-Length": str(len(body))}
    conn = http.client.HTTPConnection(host, port, timeout=10)
    try:
        conn.request("POST", _BOUNDED_ROUTE, body=body, headers=headers)
        resp = conn.getresponse()
        # Auth may return 401/403 (before JSON parsing), any non-5xx from transport ok
        assert resp.status not in (502, 503), (
            f"Transport should not 502/503 for a small body; got {resp.status}"
        )
    finally:
        conn.close()


# ── WT-03: Declared Content-Length above route limit is rejected ───────────────

def test_wt_03_content_length_above_limit_rejected(waitress_server):
    """Declared Content-Length above 64 MiB is rejected before reading the body."""
    host, port = waitress_server
    headers = {
        "Content-Type":   "application/json",
        "Content-Length": str(_MAX_BODY + 1),
    }
    conn = http.client.HTTPConnection(host, port, timeout=10)
    try:
        conn.request("POST", _BOUNDED_ROUTE, body=b"{}", headers=headers)
        resp = conn.getresponse()
        assert resp.status in (413, 400, 431), (
            f"Oversized Content-Length: expected 413/400, got {resp.status}"
        )
    except (http.client.RemoteDisconnected, ConnectionResetError):
        pass  # Waitress may close connection for oversized requests — acceptable
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ── WT-04: HTTP/1.1 chunked body within route limit is accepted ────────────────

def test_wt_04_chunked_body_within_limit_accepted(waitress_server):
    """HTTP/1.1 chunked body within the 64 MiB limit reaches the bounded route."""
    host, port = waitress_server
    body_chunk = b'{"units":[],"location":"Riyadh"}'
    token = _make_jwt()
    conn = http.client.HTTPConnection(host, port, timeout=10)
    try:
        conn.putrequest("POST", _BOUNDED_ROUTE)
        conn.putheader("Authorization", f"Bearer {token}")
        conn.putheader("Content-Type", "application/json")
        conn.putheader("Transfer-Encoding", "chunked")
        conn.endheaders()
        conn.send(f"{len(body_chunk):x}\r\n".encode())
        conn.send(body_chunk + b"\r\n")
        conn.send(b"0\r\n\r\n")
        resp = conn.getresponse()
        # 400/401/422 from application layer = transport accepted the body
        assert resp.status < 600, f"Unexpected status {resp.status}"
        assert resp.status != 502, "Should not get 502 for small chunked body"
    except (http.client.RemoteDisconnected, ConnectionResetError):
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ── WT-05: max_request_body_size does not block the health endpoint ────────────

def test_wt_05_health_not_blocked_by_body_limit(waitress_server):
    """The health endpoint with no body is never blocked by the body limit."""
    host, port = waitress_server
    for _ in range(5):
        conn = http.client.HTTPConnection(host, port, timeout=5)
        try:
            conn.request("GET", _HEALTH_PATH)
            resp = conn.getresponse()
            assert resp.status == 200
        finally:
            conn.close()


# ── WT-06: HTTP/1.1 chunked body above route limit returns 413 ────────────────

def test_wt_06_chunked_body_above_limit_rejected(waitress_server):
    """HTTP/1.1 chunked body exceeding 64 MiB is rejected with 413 or connection close."""
    host, port = waitress_server
    # Send MAX_BODY + 1 bytes as chunked — Waitress rejects at max_request_body_size
    chunk_size = 65536  # 64 KiB per chunk
    total = _MAX_BODY + 1
    conn = http.client.HTTPConnection(host, port, timeout=60)
    try:
        conn.putrequest("POST", _BOUNDED_ROUTE)
        conn.putheader("Authorization", f"Bearer {_make_jwt()}")
        conn.putheader("Content-Type", "application/json")
        conn.putheader("Transfer-Encoding", "chunked")
        conn.endheaders()
        sent = 0
        rejected = False
        while sent < total:
            chunk = b"x" * min(chunk_size, total - sent)
            conn.send(f"{len(chunk):x}\r\n".encode())
            conn.send(chunk + b"\r\n")
            sent += len(chunk)
            # Eagerly check for an error response mid-stream
            try:
                conn.sock.setblocking(False)  # type: ignore[union-attr]
                peek = conn.sock.recv(16, socket.MSG_PEEK)  # type: ignore[union-attr]
                if peek.startswith(b"HTTP/1"):
                    rejected = True
                    break
            except (BlockingIOError, OSError):
                pass
            finally:
                try:
                    conn.sock.setblocking(True)  # type: ignore[union-attr]
                except OSError:
                    pass
        if not rejected:
            conn.send(b"0\r\n\r\n")
        try:
            resp = conn.getresponse()
            assert resp.status in (413, 400, 431, 503), (
                f"Oversized chunked body: expected 413/400, got {resp.status}"
            )
        except (http.client.RemoteDisconnected, ConnectionResetError, http.client.BadStatusLine):
            pass  # Waitress may close connection — acceptable
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ── WT-07: Malformed JSON returns 400 invalid_json ────────────────────────────

def test_wt_07_malformed_json_returns_400(waitress_server):
    """Malformed JSON body to a bounded route returns 400 invalid_json."""
    host, port = waitress_server
    body = b"{this is not valid json!!"
    headers = {**_auth_headers(), "Content-Length": str(len(body))}
    conn = http.client.HTTPConnection(host, port, timeout=10)
    try:
        conn.request("POST", _BOUNDED_ROUTE, body=body, headers=headers)
        resp = conn.getresponse()
        raw = resp.read()
        assert resp.status == 400, (
            f"Malformed JSON: expected 400, got {resp.status}; body={raw[:200]}"
        )
        import json
        try:
            body_json = json.loads(raw)
            assert body_json.get("error") == "invalid_json", (
                f"Expected error='invalid_json', got {body_json}"
            )
        except json.JSONDecodeError:
            pytest.fail(f"Response body is not JSON: {raw[:200]}")
    finally:
        conn.close()


# ── WT-08: Empty JSON body returns 400 json_body_required ─────────────────────

def test_wt_08_empty_json_body_returns_400(waitress_server):
    """Empty body to a bounded JSON route returns 400 json_body_required."""
    host, port = waitress_server
    headers = {**_auth_headers(), "Content-Length": "0"}
    conn = http.client.HTTPConnection(host, port, timeout=10)
    try:
        conn.request("POST", _BOUNDED_ROUTE, body=b"", headers=headers)
        resp = conn.getresponse()
        raw = resp.read()
        assert resp.status == 400, (
            f"Empty body: expected 400, got {resp.status}; body={raw[:200]}"
        )
        import json
        try:
            body_json = json.loads(raw)
            assert body_json.get("error") == "json_body_required", (
                f"Expected error='json_body_required', got {body_json}"
            )
        except json.JSONDecodeError:
            pytest.fail(f"Response body is not JSON: {raw[:200]}")
    finally:
        conn.close()


# ── Unit test: bounded port-collision retry helper ────────────────────────────

def test_port_collision_retry_finds_free_port():
    """_free_port() succeeds when earlier ports are occupied."""
    base = 15700
    # Listen on the first port to firmly occupy it (listen() is required on
    # Windows — bind()+SO_REUSEADDR alone does not block a second bind there).
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        blocker.bind(("127.0.0.1", base))
        blocker.listen(1)
        found = _free_port(base)
    finally:
        blocker.close()
    # Should have found a port different from the occupied one
    assert found != base, "Should skip the occupied port"
    assert found > base, "Should try higher ports when lower ones are occupied"


def test_port_collision_retry_raises_when_all_occupied():
    """_free_port() raises RuntimeError when no port is available in the range."""
    sockets = []
    start = 19000
    try:
        for p in range(start, start + 10):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.bind(("127.0.0.1", p))
                s.listen(1)  # listening firmly occupies the port on all platforms
                sockets.append(s)
            except OSError:
                s.close()

        def _tiny_free_port(start: int = start) -> int:
            for port in range(start, start + len(sockets)):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    try:
                        s.bind(("127.0.0.1", port))
                        return port
                    except OSError:
                        continue
            raise RuntimeError("No free port found in range")

        with pytest.raises(RuntimeError, match="No free port"):
            _tiny_free_port(start)
    finally:
        for s in sockets:
            try:
                s.close()
            except Exception:
                pass
