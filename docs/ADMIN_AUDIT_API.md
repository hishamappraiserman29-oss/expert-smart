# Admin Audit API

Read-only HTTP endpoint exposing the audit log to operators.

## Endpoint

```
GET /api/admin/audit
```

### Headers

```
Authorization: Bearer <jwt>
```

### Query Parameters

| Param | Type | Default | Description |
|---|---|---|---|
| `user_id` | string | — | Filter by audited user |
| `since` | ISO date | — | `created_at >= since` |
| `until` | ISO date | — | `created_at <= until` |
| `limit` | int | 100 | Max records (capped at 500) |
| `offset` | int | 0 | Pagination offset |

### Response (200)

```json
{
  "count": 42,
  "filters": {"user_id": "alice", "since": null, "until": null, "limit": 100, "offset": 0},
  "records": [
    {
      "id": 123,
      "user_id": "alice",
      "endpoint": "/api/reports",
      "method": "GET",
      "status": 200,
      "report_id": null,
      "ip": "127.0.0.1",
      "created_at": "2026-05-16T10:23:45+00:00"
    }
  ]
}
```

### Errors

| Code | When |
|---|---|
| 400 | Invalid `limit` or `offset` (non-integer) |
| 401 | Missing or invalid JWT token |
| 403 | Authenticated but not in admin set |
| 429 | Rate limit exceeded (30/min per user) |

## Admin Authentication

Currently identified by `ADMIN_USER_IDS` env var (comma-separated):

```bash
export ADMIN_USER_IDS=alice,operations@example.com
```

- If the env var is unset or empty, **no user is admin**.
- Restart the app after changing this env var.

## Meta-Audit

Access to `/api/admin/audit` is itself logged in the `report_access_log` table.
This provides accountability for who reviewed logs and when.

## Rate Limiting

30 requests/minute per admin user (S4 per-user rate limiting applies).

## Future Upgrade Path (S5.2 — optional)

Replace env-var admin identification with a JWT `role` claim:

1. Extend `generate_token(user_id, *, role="user")` to embed `role` in the payload
2. `is_admin()` reads `role == "admin"` from the decoded token
3. Provision admin tokens via a separate (manual or privileged) flow
4. Update `require_admin` to read the claim from `g` (set by `_attach_user_from_token`)

Until that lands, keep `ADMIN_USER_IDS` short and rotate it on team changes.

## Production Checklist

- [ ] `ADMIN_USER_IDS` set with minimum necessary list
- [ ] Restart procedure after admin list change documented
- [ ] Audit log retention policy in place (see `docs/AUDIT_LOG.md`)
- [ ] Alerts on unusual `/api/admin/audit` access patterns
