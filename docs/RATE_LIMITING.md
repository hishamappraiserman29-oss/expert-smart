# Rate Limiting

Per-user rate limiting on protected endpoints (added in auth wave S4).

## Limits

| Endpoint | Limit | Reason |
|---|---|---|
| `GET /api/reports` | 30/min | List pagination — medium cost |
| `GET /api/reports/<id>` | 60/min | Lightweight retrieval |
| `GET /api/reports/<id>/pdf` | 10/min | PDF generation ~2.4s + 8MB output |
| `POST /api/valuation` | — | Not limited in S4 (S4.1 may add) |

## Key Function

Requests are keyed by `g.user_id` (set by the JWT middleware from S2).
Different users get fully independent counters. Unauthenticated requests
(blocked at `@require_auth` before reaching the limiter) would fall back to
IP-based keying, but in practice never reach the counter.

## Storage

In-memory by default (single-process, resets on restart). For multi-process
or multi-instance deployments, switch to Redis:

```python
# bridge_api.py
limiter = Limiter(
    key_func=_rate_limit_key,
    app=app,
    storage_uri="redis://localhost:6379",
    ...
)
```

Requires the `redis` package and a running Redis server.

## 429 Response

```json
{
  "status": "rate_limited",
  "message": "Too many requests. Please try again later.",
  "limit": "30 per 1 minute"
}
```

Headers on every response (success and 429):

| Header | Value |
|---|---|
| `X-RateLimit-Limit` | configured limit (e.g. `30`) |
| `X-RateLimit-Remaining` | remaining requests in window |
| `X-RateLimit-Reset` | window reset timestamp |
| `Retry-After` | seconds until counter resets |

## Disabling for Tests

Tests run with `RATE_LIMIT_ENABLED=false` by default (set in
`core_engine/tests/conftest.py`). The `_rate_limit_disabled()` callable is
evaluated per-request via `exempt_when=`, so monkeypatching the env var works
correctly regardless of when `bridge_api` was imported.

Tests that verify 429 behaviour opt in via fixture:

```python
@pytest.fixture
def rate_limited_client(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    from bridge_api import app, limiter
    limiter.reset()          # clear counters between tests
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c
```

## Production Checklist

- [ ] `RATE_LIMIT_ENABLED=true` in production environment variables
- [ ] Storage: Redis for multi-instance (in-memory is fine for single process)
- [ ] Monitor: alert if 429 rate spikes (indicates abuse or misconfigured client)
- [ ] Tune limits based on real usage patterns after first month in production
