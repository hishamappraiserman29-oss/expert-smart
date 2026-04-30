# Expert_Smart — Orchestration Design Notes

Free-form design notes that supplement `integration-plan.md` and
`tool-registry-draft.json`. These are decisions, caveats, and open
questions — captured so they don't have to be re-discovered later.

This file is **planning only**. It does not commit the project to anything.

Snapshot date: April 26, 2026.

## What stays outside orchestration for now

The following items are explicitly out of scope and should remain that way
until a deliberate, document-backed decision moves them in:

- **The 5 Python engines under `core_engine/`** (`hbu_analysis_engine`,
  `reit_nav_engine`, `eia_engine`, `bank_audit_engine`,
  `fund_valuation_engine`). Even though they expose clean
  `run_X(payload)` signatures, exposing them via direct Python import
  would couple the orchestration runtime to the unstable
  `bridge_api.py`-adjacent codebase. **Always go through HTTP.**
- **`core_engine/bridge_api.py` itself.** Treated as immutable in this
  phase. The two truncation incidents (Tasks #13 and #33) are sufficient
  reason to keep all change pressure off this file.
- **The ~44 non-public Flask routes** (admin, profile, file-download,
  market-feed write endpoints, CORS preflights, …). Out of scope until
  each is individually validated against `TESTED_BASELINES.md`. Not bulk
  promotable.
- **The frontend.** `frontend/index.html` is a static UI served by the
  same Flask app. An orchestration agent should never render or interact
  with the UI — it should call the same backend the UI calls.
- **The deploy stack (`deploy/`).** Not yet validated end-to-end on any
  cloud (DEFERRED_ITEMS.md → D6). Orchestration should not assume the
  containerized topology works until D6 is closed.

## Why `/api/image/geo-analyze` stays excluded

`DEFERRED_ITEMS.md → D2` documents that the frontend expects a 14-field
response shape (`gps_coordinates`, `soil_type`, `flood_risk`, `seismic_risk`,
`heat_risk`, `geotechnical_summary`, `estimated_area_sqm`, `buildability`,
`risk_score`, `geotechnical_risk_level`, `confidence`, `location_guess`,
`coordinates_note`, `recommendations`) but the underlying engine
(`geo_risk_engine.analyze_geo_risk`) returns only 10 fields with a
different shape. Only 5 of 14 fields can be mapped with high confidence;
the remaining 9 have no traceable contract in either the frontend or
backend code.

Implications for orchestration:

- An LLM-driven agent reasoning over a partial / inferred contract will
  produce subtly wrong results for `risk_score`, `confidence`, and four
  other unmapped fields. The user-visible numbers would look plausible
  but be unanchored — exactly the AVM-before-densification failure mode
  in microcosm.
- Inventing the missing fields ("hallucinated contract") is the worst
  possible failure: it scales with agent autonomy.
- Therefore: **do not wrap, do not even document for orchestration**,
  until either (a) the original transformer code is recovered from a backup
  / older commit, or (b) a stakeholder decision freezes the contract for
  the 9 unmapped fields.

The endpoint stays out of `tool-registry-draft.json` for that reason. It
is listed only in the `excluded_endpoints` block, which is a refusal note,
not a forward commitment.

## Why write-heavy endpoints need read-only / dry-run handling first

The endpoints `valuation`, `eia_assess`, and `image_analyze` always or
nearly always write to `outputs/`:

| endpoint | writes per successful call |
|---|---|
| `valuation` | 1× `.xlsm` + 1× `.docx` (uniquely-named) |
| `eia_assess` | 1× `.docx` + 1× `.xlsx` (uniquely-named) |
| `image_analyze` | 1× saved upload (uniquely-named) |

In an autonomous orchestration setting (e.g., an agent that explores
options by calling tools repeatedly), the disk impact compounds quickly.
Worst-case rough math: a 5-step plan that retries 3× per step calls each
side-effecting tool ~15 times. Across the 3 endpoints, that's up to 45
new files per "thought trace", each tens to hundreds of KB. Over a single
shift this fills storage on a small VM (e.g., the Render `starter` plan
disk, the Fly.io `performance-4x` ephemeral storage, or any laptop-class
deploy).

There is no current mechanism in `bridge_api.py` to:

- skip the file generation (no `dry_run` parameter);
- batch / dedupe identical results (each call gets a fresh report ID);
- expire generated artifacts (no TTL, no rotation, no quota check);
- reject calls when `outputs/` exceeds a size threshold.

Phase 3 of `integration-plan.md` is therefore gated on a server-side
`dry_run` flag and an `outputs/` retention policy — both small,
documented, additive backend changes that have **not yet been requested
or approved**. Until they exist, autonomous orchestration over these
three tools is a hazard, not a feature.

A safe interim option (not now, but worth noting): an orchestration
wrapper could be allowed to call `valuation` and `eia_assess` only when a
human operator has explicitly approved the call, and the wrapper would
delete the generated files after capturing the JSON portion of the
response. That partially shifts the problem from "disk fills up" to
"correctness of cleanup", which is also non-trivial.

## Risks around `outputs/` and report generation

- **No retention policy.** Generated `.docx` / `.xlsx` / `.xlsm` files
  accumulate indefinitely. Manual cleanup is the only mechanism today.
- **No quota / size check.** A misbehaving caller (or, worse, an agent in
  a loop) can fill the volume without any backpressure. The Flask app
  will not start failing requests until the underlying disk is full.
- **No deduplication.** Identical inputs produce different report IDs
  each call, so the same report is regenerated on every retry.
- **Report-ID format is timestamp-based.** Two calls within the same
  millisecond *should* still get distinct IDs, but this has not been
  stress-tested.
- **No content-addressing.** Even if dedup were added later, the current
  filename scheme (`Report_ES-<id>.xlsm`) does not lend itself to a hash
  / digest model without a server-side change.

The orchestration plan treats all of the above as known and unfixed. They
are listed here so a future operator does not assume the problem has
already been solved by the act of "wrapping the endpoint".

## `bridge_api.py` fragility

Two truncation incidents on this file (recovered in Tasks #13 and #33)
established that wide replacements or large-section rewrites against a
~6,700-line file are unsafe in this environment. The orchestration plan
inherits this constraint:

- No Phase will require a wide change to `bridge_api.py`.
- Any small additive change (e.g., a `dry_run` flag) is allowed as a
  separate, single-purpose, manually-validated edit, with the standard
  `python -c "import ast, pathlib; ast.parse(...)"` post-check.
- Refactors to make `bridge_api.py` "more orchestration-friendly" are
  explicitly out of scope.

## `vector_db/.lock` state

At the time of writing, `expert_smart_system/vector_db/.lock` cannot be
read from the build sandbox (returns `Input/output error`), suggesting an
active or stale lock held by Qdrant on the Windows host. The user has
chosen Option C from the previous turn — remove `.lock` only after
confirming the Flask server is fully stopped — but the action is
pending operator execution on the Windows side.

Implications for orchestration:

- `advisor_health` will continue to return `rag_ready=true` even when the
  collection is locked or empty. The signal is not strong enough to gate
  an orchestration call on it.
- Any wrapper for `advisor_health` should treat it as a "is the Flask
  app reachable" probe, not a "is the RAG corpus searchable" probe.
- Until the lock state is resolved and a deliberate restart has happened,
  Phase 1 should not begin.

## Choice of orchestration framework — postponed

`integration-plan.md` deliberately leaves the framework choice open. Some
notes that should inform the eventual decision:

- **MCP** would let other Anthropic-aware tools (Claude desktop, IDE
  plugins) call the wrapped tools without project-specific glue. Pro: low
  per-client integration cost. Con: requires running an MCP server
  process; another moving part to deploy and version.
- **LangGraph** would give explicit, testable state machines for
  multi-step plans. Pro: good fit for a chained workflow like
  `valuation → reit_nav → eia_assess` for the same property. Con: ties
  the orchestration layer to a specific Python ecosystem and version.
- **Custom thin client** (just a Python module that calls the HTTP
  endpoints directly, exposed to whatever agent is in use) is the
  smallest possible Phase 1 implementation. It buys the "HTTP-only"
  rule cheaply and defers the framework decision.

The plan assumes the third option will be the actual Phase 1
implementation — until proven otherwise.

## Open questions to resolve before Phase 1

- Where does the orchestration layer run (separate container? sidecar?
  separate VM? operator's laptop)? Affects networking, auth, secrets.
- What is the auth model? The current Flask app trusts localhost. If the
  orchestration layer runs elsewhere, an API key or VPN is required.
- Who owns the wrapper code and where does it live? In this repo under
  `agent_layer/`, or in a separate repo? Prefer separate to keep
  `bridge_api.py` change pressure low.
- What's the failure mode when `bridge_api.py` is down? The orchestration
  layer should fail closed (refuse the action) rather than guess.

These are documented here so they can be answered when (and only when)
Phase 1 is on the table.
