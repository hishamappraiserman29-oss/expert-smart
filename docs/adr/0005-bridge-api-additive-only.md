# ADR-0005: Bridge API Integration is Additive + Opt-In Only

- **Status:** Accepted
- **Date:** 2026-05-01

## Context

After building the three engines (Validation / PDF / DB), they had to be wired into
`bridge_api.py` — which was already serving live users with the existing valuation
endpoint (`POST /api/valuation`). Any behavior change to that endpoint would break
existing clients silently: they send the same payload and expect the same response
shape back.

The risk was compounded by the size of `bridge_api.py` (~11,600 lines). Wide
refactors in a file that large have a high probability of introducing unintended
side effects in unrelated routes.

## Options Considered

### Option A — Replace the existing flow
Rewrite `POST /api/valuation` to run through `report_pipeline.py` unconditionally.
Validation always runs. PDF always generates. Report always persists.

- Pros: Cleanest internal architecture. No opt-in flags cluttering the payload.
- Cons: Every existing client must handle: validation errors (new 422s), PDF paths
  in the response, DB IDs in the response. Breaking change without a migration plan.

### Option B — Additive opt-in flags (chosen)
Add boolean flags to the request payload: `validate`, `persist`, `pdf`.
When absent (or false), the existing behavior is byte-identical to pre-integration.
New behavior activates only when the client explicitly opts in.

Add read-only retrieval endpoints (`GET /api/reports`, `GET /api/reports/<id>`,
`GET /api/reports/<id>/pdf`) as purely additive new routes — existing clients are
unaffected.

### Option C — Separate versioned endpoints (`/api/v2/valuation`)
New behavior on `/api/v2/`, old behavior stays on `/api/v1/`.

- Pros: Clean separation; old and new clients coexist indefinitely.
- Cons: Requires every client to migrate explicitly. Doubles the maintenance surface
  for the valuation endpoint. No natural deprecation path.

## Decision

Adopt Option B for request-level features (validate / persist / pdf flags) and
Option C's spirit for retrieval (new `GET /api/reports*` endpoints rather than
overloading the POST).

A snapshot test (`test_bridge_api_baseline.py`) captures the pre-integration response
shape and is run after every integration wave. Any change to it is treated as a
regression and must be explicitly approved before merging.

## Consequences

**Positive:**
- Zero client breakage at v1.0.0 launch.
- Gradual adoption: clients enable features one at a time.
- Each flag is independently revertable (set to false = old behavior).
- The snapshot test is a hard guarantee, not a convention.

**Negative / Tradeoffs:**
- Three extra boolean keys in the request payload create minor friction for new
  integrators who expect a clean API.
- `bridge_api.py` grows in LOC rather than being refactored — technical debt accrues.
- The snapshot test is load-bearing; deleting it accidentally removes the only
  automated guarantee of backward compatibility.
- Error handling for `persist=true` is non-fatal by design (persist failure returns
  200 with `persist_error` field) — this is intentional but unintuitive.
