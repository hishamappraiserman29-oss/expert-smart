"""
test_phase_14_e2e.py — Phase 14 Webhook Notifications (12 tests)

Tests:
  01  WebhookDelivery dataclass initial state and to_dict()
  02  dispatch_sync: single successful POST → status "delivered"
  03  dispatch_sync: two 500s then 200 → retry → status "delivered", attempt_count 3
  04  dispatch_sync: three 500s → status "failed", attempt_count 3
  05  dispatch_sync: unreachable URL → status "failed", non-empty last_error
  06  dispatch (async): returns immediately with status "pending"
  07  on_complete callback invoked on successful delivery
  08  on_complete callback invoked on failed delivery
  09  WebhookLog.record() persists and count() increments
  10  WebhookLog.count_by_status() reflects status breakdown
  11  WebhookLog.get_by_batch() returns only matching records, newest-first
  12  POST /api/valuation/batch with webhook_url returns normal batch response
"""
from __future__ import annotations

import http.server
import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

_CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_CORE))
os.environ.setdefault("JWT_SECRET", "test-secret-e2e-bundle")
os.chdir(str(_CORE))

from adapters.webhook_dispatcher import WebhookDelivery, WebhookDispatcher
from database.webhook_log import WebhookLog
import bridge_api as _bridge_api
from auth.tokens import generate_token as _gen_token
_AUTH_HDR = {"Authorization": f"Bearer {_gen_token('test-user-e2e')}"}


# ── Mock HTTP server ──────────────────────────────────────────────────────────

class _MockHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)
        self.server._bodies.append(body)
        n     = len(self.server._bodies)
        codes = self.server._codes
        code  = codes[n - 1] if n <= len(codes) else codes[-1]
        self.send_response(code)
        self.end_headers()

    def log_message(self, *args):
        pass  # silence


def _mock_server(codes=(200,)):
    srv = http.server.HTTPServer(("127.0.0.1", 0), _MockHandler)
    srv._codes  = list(codes)
    srv._bodies = []
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{port}"


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_01_delivery_dataclass_fields():
    d = WebhookDelivery(url="http://example.test", payload={"k": "v"}, batch_id="b1")
    assert d.status        == "pending"
    assert d.attempt_count == 0
    assert d.last_status   == 0
    assert d.last_error    == ""
    assert d.delivered_at  is None
    assert d.created_at                          # non-empty ISO timestamp
    info = d.to_dict()
    assert info["url"]      == "http://example.test"
    assert info["batch_id"] == "b1"
    assert info["status"]   == "pending"


def test_02_dispatch_sync_success():
    srv, url = _mock_server((200,))
    wd      = WebhookDispatcher(base_delay=0.01)
    payload = {"batch_id": "b-ok", "status": "completed"}
    d = wd.dispatch_sync(url, payload, batch_id="b-ok")
    assert d.status        == "delivered"
    assert d.last_status   == 200
    assert d.attempt_count == 1
    assert d.delivered_at  is not None
    body = json.loads(srv._bodies[0])
    assert body["batch_id"] == "b-ok"
    srv.shutdown()


def test_03_dispatch_sync_retry_then_success():
    srv, url = _mock_server((500, 500, 200))
    wd = WebhookDispatcher(base_delay=0.01, max_attempts=3)
    d  = wd.dispatch_sync(url, {"x": 1}, batch_id="retry-batch")
    assert d.status        == "delivered"
    assert d.attempt_count == 3
    assert len(srv._bodies) == 3
    srv.shutdown()


def test_04_dispatch_sync_all_fail():
    srv, url = _mock_server((500, 500, 500))
    wd = WebhookDispatcher(base_delay=0.01, max_attempts=3)
    d  = wd.dispatch_sync(url, {"x": 1})
    assert d.status        == "failed"
    assert d.attempt_count == 3
    assert d.last_status   == 500
    assert d.delivered_at  is None
    srv.shutdown()


def test_05_dispatch_sync_invalid_url():
    wd = WebhookDispatcher(base_delay=0.01, max_attempts=2)
    d  = wd.dispatch_sync("http://127.0.0.1:1", {"x": 1})
    assert d.status       == "failed"
    assert d.last_error               # non-empty error description
    assert d.delivered_at is None


def test_06_dispatch_async_returns_immediately():
    srv, url = _mock_server((200,))
    wd = WebhookDispatcher(base_delay=0.01)
    d  = wd.dispatch(url, {"k": "v"}, batch_id="async-test")
    # Returns before the daemon thread can possibly complete
    assert d.status == "pending"
    srv.shutdown()


def test_07_on_complete_called_on_success():
    srv, url = _mock_server((200,))
    results  = []
    wd = WebhookDispatcher(base_delay=0.01)
    wd.dispatch_sync(url, {"a": 1}, batch_id="cb-ok",
                     on_complete=lambda d: results.append(d.status))
    assert results == ["delivered"]
    srv.shutdown()


def test_08_on_complete_called_on_failure():
    srv, url = _mock_server((500, 500, 500))
    results  = []
    wd = WebhookDispatcher(base_delay=0.01, max_attempts=3)
    wd.dispatch_sync(url, {"a": 1}, batch_id="cb-fail",
                     on_complete=lambda d: results.append(d.status))
    assert results == ["failed"]
    srv.shutdown()


def test_09_webhook_log_record_and_count():
    db = tempfile.mktemp(suffix=".db")
    wl = WebhookLog(db_path=db)
    assert wl.count() == 0
    d1 = WebhookDelivery(url="http://a", payload={}, batch_id="b1",
                         status="delivered", attempt_count=1)
    d2 = WebhookDelivery(url="http://b", payload={}, batch_id="b2",
                         status="failed",    attempt_count=3)
    wl.record(d1)
    assert wl.count() == 1
    wl.record(d2)
    assert wl.count() == 2


def test_10_webhook_log_count_by_status():
    db = tempfile.mktemp(suffix=".db")
    wl = WebhookLog(db_path=db)
    for _ in range(3):
        d = WebhookDelivery(url="http://x", payload={}, status="delivered")
        wl.record(d)
    wl.record(WebhookDelivery(url="http://y", payload={}, status="failed"))
    assert wl.count_by_status("delivered") == 3
    assert wl.count_by_status("failed")    == 1
    assert wl.count_by_status("pending")   == 0


def test_11_webhook_log_get_by_batch():
    db = tempfile.mktemp(suffix=".db")
    wl = WebhookLog(db_path=db)
    for url in ["http://a", "http://b", "http://c"]:
        wl.record(WebhookDelivery(url=url, payload={},
                                  batch_id="target-batch", status="delivered"))
    wl.record(WebhookDelivery(url="http://other", payload={},
                              batch_id="other-batch", status="pending"))
    rows = wl.get_by_batch("target-batch")
    assert len(rows) == 3
    assert all(r["batch_id"] == "target-batch" for r in rows)
    # newest first (descending id)
    ids = [r["id"] for r in rows]
    assert ids == sorted(ids, reverse=True)
    # other batch is not included
    assert wl.get_by_batch("other-batch") == [
        r for r in wl.get_by_batch("other-batch")
    ]
    assert len(wl.get_by_batch("other-batch")) == 1


def test_12_api_batch_with_webhook_url():
    client = _bridge_api.app.test_client()
    srv, url = _mock_server((200,))
    payload = {
        "batch_name": "Webhook Integration Batch",
        "properties": [
            {
                "property_id":   "WH-P1",
                "property_type": "residential",
                "area_sqm":      120,
                "input_data":    {"valuation_value": 600_000},
            }
        ],
        "webhook_url": url,
    }
    t0   = time.time()
    resp = client.post(
        "/api/valuation/batch",
        data=json.dumps(payload),
        content_type="application/json",
        headers=_AUTH_HDR,
    )
    elapsed = time.time() - t0
    assert resp.status_code == 200
    body = json.loads(resp.data)
    assert body["status"]   == "success"
    assert body["batch_id"]
    assert body["summary"]["completed"] == 1
    # Response must be fast — webhook is async and must not block
    assert elapsed < 5.0, f"Response too slow: {elapsed:.2f}s"
    srv.shutdown()


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
