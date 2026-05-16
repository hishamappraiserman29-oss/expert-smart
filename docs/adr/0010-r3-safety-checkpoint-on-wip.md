# ADR-0010: R3 Subsystems on WIP Branch for Safe Review

- **Status:** Accepted
- **Date:** 2026-05-10

## Context

After v1.0.0 was stabilized (three engines + bridge API integration), 24 additional
subsystems existed in a pre-consolidation state: banking, government, funds, adapters,
agents, ML/AVM, analytics, marketplace, SaaS, security, and more.

These subsystems were built across dozens of earlier phases and contained varying
quality: some had full test suites, others had zero tests; some had clean stdlib-only
imports, others depended on packages not in `requirements.txt`; some introduced
naming collisions with existing main code.

Merging all 24 subsystems to `main` at once would have:
- Made it impossible to revert individual subsystems if a regression was discovered.
- Added untested code to the CI-protected main branch.
- Made it impossible to track which subsystem introduced a specific test failure.

## Options Considered

### Option A — Merge all subsystems to main at once
One large merge commit brings all 24 subsystems to `main`.

- Pros: Single operation. No branch management overhead.
- Cons: If any subsystem breaks `main`, the entire merge must be reverted or
  individual subsystems must be manually cherry-picked out — the inverse of the
  intended workflow. All 24 share blame for any subsequent failure.

### Option B — WIP safety checkpoint branch + per-subsystem cherry-pick (chosen)
All 24 subsystems are committed to `wip/r3-subsystems-checkpoint`, one commit per
subsystem. This branch is:
- **Frozen** — never pushed to by anyone; it is a read-only reference.
- **Never merged** directly — subsystems are cherry-picked to feature branches for
  review, then merged to `main` individually.

Each cherry-pick triggers a Gate report covering: files, dependencies, tests,
naming conflicts, security scan, recommendation (MERGE / DEFER / REJECT).

### Option C — One feature branch per subsystem from the start
24 parallel feature branches, each with its subsystem.

- Cons: 24 branches are unwieldy to manage. Coordinating base commits across them
  is complex when `main` evolves. The WIP checkpoint provides the same isolation with
  less branch management overhead.

## Decision

Adopt Option B. The WIP branch (`wip/r3-subsystems-checkpoint`) holds 24 one-commit
subsystem imports. The review workflow per R3 session:
1. Identify the target subsystems for the session.
2. `git cherry-pick <subsystem-commit>` to a fresh `feature/r3-N-*` branch.
3. Run the full Gate checklist (files, deps, tests, secrets scan, `py_compile`).
4. Human approves MERGE / DEFER / REJECT.
5. Pre-merge fixes applied. Merge to `main` via `--no-ff`.
6. Gate decisions logged in `docs/R3_REVIEW_LOG.md`.

## Consequences

**Positive:**
- Any subsystem can be individually deferred or rejected without affecting others.
- `main` remains green at all times — no untested code lands without a Gate.
- `docs/R3_REVIEW_LOG.md` provides a traceable record of every subsystem decision.
- The WIP branch survives as a reference even after all subsystems are merged.
- Rollback is surgical: revert the specific merge commit for a subsystem.

**Negative / Tradeoffs:**
- Cherry-picking one commit at a time is slower than a bulk merge.
- If the WIP branch commits have conflicts with post-v1.0.0 `main` changes, each
  cherry-pick may require manual resolution.
- The WIP branch must never be deleted — it is the source of truth for all
  not-yet-reviewed subsystems. Accidental deletion would require reconstruction from
  history.
- Gate reviews take time: each session covers 2–3 subsystems at most.
