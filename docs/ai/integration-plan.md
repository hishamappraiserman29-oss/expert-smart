# Expert_Smart — AI Integration Plan

Lightweight, future-safe plan for how an external AI orchestration layer
should eventually interact with this project.

This document is **planning only**. It does not create any runtime artifact,
and it does not commit the project to any specific framework (LangGraph,
MCP, custom, or otherwise).

Snapshot date: April 26, 2026.

## Intent

The Expert_Smart core (Flask + 51 routes + 5 standalone engines) was built
without an orchestration layer in mind. It works correctly as a request /
response service on top of `core_engine/bridge_api.py`. Any future AI agent
that *uses* this project must treat the existing surface as immutable until
proven otherwise.

This plan defines:

- **how** an orchestration layer should call into the project (the integration model);
- **what** it is allowed to call now vs. later (the rollout order);
- **what** remains explicitly postponed.

## Integration model — HTTP-only

The single hard rule for any future orchestration layer:

> **Talk to the Flask server over HTTP. Never import from `core_engine.bridge_api` directly.**

Rationale:

- `core_engine/bridge_api.py` is ~6,726 lines and has been truncated twice
  in earlier sessions (Tasks #13 and #33). Importing from it embeds an
  unstable boundary into the orchestration layer, so a future truncation
  would crash the agent and the server simultaneously.
- HTTP gives a single, well-defined contract per endpoint that survives
  internal refactors.
- HTTP allows the orchestration layer to run in a separate container,
  process, or even host — useful for the deploy story (`deploy/`) and for
  isolating failures.

**Concrete consequence:** the orchestration layer should be a separate
package. It should not live under `core_engine/`. It should not be
referenced from `bridge_api.py`. It should not share a Python interpreter
with the Flask app in production.

## Read-only-first principle

A future orchestration layer must be brought online in stages, where each
stage adds a strictly larger blast radius than the previous one. Earlier
stages must remain operational and stable for at least one full validation
cycle before the next is enabled.

The grouping of endpoints follows `docs/TOOL_MANIFEST.md`:

- **Read-only** (no `outputs/` writes, fully idempotent):
  `advisor_health`, `price_index`.
- **Idempotent compute** (no `outputs/` writes by default, but optional
  report export): `hbu_analyze`, `reit_nav`.
- **Side-effecting compute** (always writes to `outputs/` on success):
  `eia_assess`, `valuation`.
- **Upload + storage** (saves an uploaded artifact, partial GPS contract):
  `image_analyze`.

The orchestration layer must default to the lowest-impact tier and require
an explicit feature-flag (or a deliberate operator action) to enable each
higher tier.

## Safe rollout order

### Phase 0 — Inventory only (where we are today)

- `docs/TOOL_MANIFEST.md` exists.
- `docs/ai/tool-registry-draft.json` exists (this PR), in **draft** form.
- No orchestration runtime exists.
- No tool is wrapped or callable from any agent.

This is the safe state. Staying in Phase 0 indefinitely is acceptable.

### Phase 1 — Read-only HTTP wrappers (smallest blast radius)

- Build a separate package (e.g., `agent_layer/` or external repo) that
  wraps **only** `advisor_health` and `price_index`.
- The wrapper makes HTTP calls to the running Flask server and returns the
  parsed response unchanged.
- No agent reasoning, no chains, no tools-of-tools yet — just a callable
  Python function for each endpoint.
- Validate via `docs/TESTED_BASELINES.md`: the wrapper output should match
  baseline values within ±5% for `price_index` and exactly for
  `advisor_health`.

Phase 1 entry criteria:

- `bridge_api.py` has not been truncated for at least one stabilization cycle.
- `vector_db/.lock` state is resolved (currently in flight).
- `deploy/` Docker build has been run end-to-end at least once locally.

### Phase 2 — Idempotent compute wrappers (medium blast radius)

- Add wrappers for `hbu_analyze` and `reit_nav` (idempotent; no `outputs/`
  writes by default).
- Wrappers must explicitly **omit** any optional `export_excel`-style flag
  in their default mode — file generation must require an explicit
  parameter on the wrapper call, not be implicit.
- Validate that running the wrapper 100× with the same payload produces
  byte-identical responses (within rounding) and zero new files in `outputs/`.

Phase 2 entry criteria:

- Phase 1 has been live and stable for at least one validation cycle.
- A documented `outputs/` cleanup or quota policy exists (it does not today).

### Phase 3 — Side-effecting wrappers (largest blast radius)

- Add wrappers for `eia_assess` and `valuation`.
- Each wrapper must support a `dry_run` flag that, when true, executes the
  computation but **suppresses** writing the `.docx` / `.xlsx` / `.xlsm`
  artifacts. (This will require a small server-side change at that time —
  not now.)
- Add a wrapper for `image_analyze` only after `DEFERRED_ITEMS.md → D1`
  (GPS extraction verification) is closed.

Phase 3 entry criteria:

- Phase 2 has been live and stable for at least one validation cycle.
- Server-side `dry_run` support is implemented and documented.
- `outputs/` retention policy is enforced (TTL, size cap, or rotation).
- `image_analyze` only: D1 closed.

## What remains postponed (do not start in this phase)

- Any agentic orchestration framework (LangGraph, MCP server, AutoGen, …).
- Any tool-of-tools / multi-step reasoning chain.
- Any wrapper for `/api/image/geo-analyze` (D2 — see orchestration-notes.md).
- Any wrapper for the ~44 other Flask routes not listed in `TOOL_MANIFEST.md`
  (admin, profile, file-download, market-feed write endpoints, etc.).
- Any change to the existing endpoint contracts (request shape, response
  shape, status codes) for the sake of orchestration convenience. The core
  is treated as immutable.
- Any direct Python import from `core_engine/`.

## Validation approach

Each rollout phase must include:

1. **Contract test** — the wrapper's input/output matches the row in
   `docs/TOOL_MANIFEST.md` for that endpoint, and the response top-level
   keys match those documented in `docs/API_REFERENCE.md`.
2. **Baseline test** — for endpoints with rows in `docs/TESTED_BASELINES.md`,
   the wrapper reproduces those baseline values (within the documented
   acceptance window).
3. **Idempotency test** — only for endpoints marked `idempotent: yes`. Run
   100× with identical payload, assert response equality (modulo response
   IDs / timestamps).
4. **No-side-effect test** — only for read-only and default-mode idempotent
   wrappers. Snapshot `outputs/` before and after a run; assert zero new files.

A phase is considered "stable" only after all four tests pass on two
independent runs separated by at least one server restart.

## Out-of-scope clarifications

This plan does not specify:

- which orchestration framework to use (deferred until Phase 1 entry);
- which auth / API-key model the orchestration layer should use (assume
  the current Flask trust boundary holds: localhost or VPN; production
  hardening is a separate exercise);
- where the orchestration layer is hosted (could be local CLI, sidecar
  container, separate VM, or external SaaS).

These choices should be made at Phase 1 entry, not now.
