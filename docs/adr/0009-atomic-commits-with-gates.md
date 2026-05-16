# ADR-0009: Atomic Commits with Mandatory Gates

- **Status:** Accepted
- **Date:** 2026-04-10

## Context

The project was developed incrementally across many phases. Early in the development,
several large commits bundled unrelated changes — a visual fix, a logic change, and a
new endpoint — into a single commit. When a regression was discovered days later,
identifying which change caused it required bisecting through a large diff.

Additionally, the codebase has several load-bearing invariants (profile key spelling,
backward-compatible API shape, engine isolation) that are easy to violate accidentally
during a multi-file change. A single "catch-all" commit at the end of a phase provided
no checkpoint for verifying those invariants.

## Options Considered

### Option A — Phase-level commits
One commit per development phase, however large. Simpler history, fewer commit
messages to write.

- Cons: Rollback granularity is the entire phase. Bisect is expensive. Reviewing a
  phase-level diff is cognitively expensive. Invariant violations are only caught at
  phase completion, not mid-phase.

### Option B — Atomic commits with mandatory gates (chosen)
Each commit contains exactly one logical change (one wave, one fix, one subsystem).
Before committing:
1. `git diff --cached --stat` is mandatory — any unintended staged file triggers unstage.
2. Tests must be green (run `pytest` locally before staging).
3. For risky changes (merge to main, subsystem import), a Gate report is produced
   and the human approves before proceeding.

### Option C — Feature flags + trunk-based development
All work on `main`, gated by runtime flags. No feature branches.
- Cons: Requires a feature-flag system. Incomplete work on `main` affects all
  environments. Higher complexity for a small team.

## Decision

Adopt Option B. The process is:

1. One logical change → one commit.
2. `git diff --cached --stat` before every commit (mandatory, not optional).
3. Tests green before staging.
4. Gate reports for: subsystem merges, bridge_api integration waves, any push to `main`.
5. Commits that change more than their stated scope are rolled back and split.

This process was enforced throughout the R3 subsystem reviews (ADR-0010), where each
of 24 subsystems was cherry-picked into an isolated feature branch, reviewed, and
merged (or deferred) independently.

## Consequences

**Positive:**
- `git bisect` finds regressions in minutes instead of hours.
- Rollback targets a specific logical change, not a large phase.
- Gate reports create an explicit human checkpoint before irreversible changes.
- The history is a readable narrative: each commit message describes a complete,
  working increment.
- Unintended staged files are caught before they enter the history.

**Negative / Tradeoffs:**
- More commits means more commit messages to write — higher per-commit discipline overhead.
- Gates add latency: a human must read the report and explicitly approve.
- The `git diff --cached --stat` step is procedural — it relies on the developer
  not skipping it. Automation (pre-commit hooks) would be more reliable.
- Atomic commits require planning before starting a change, not just after finishing.
