# Archival Refs — A6 Unification Phase 0

## Source Aliases

| Alias | Description |
|-------|-------------|
| `canonical_source` | GitHub remote (`origin`) — authoritative production history |
| `legacy_primary` | Primary legacy Git repository (local only, never shared as a path here) |
| `canonical_worktree` | Git linked worktree tracking `main` (pre-existing, read-only) |
| `unified_target` | This repository (`ExpertSmart_Unified`) |
| `external_legacy_bundle` | External Git bundle archive — stored outside this repository |

---

## External Legacy Bundle

| Field | Value |
|-------|-------|
| Bundle alias | `external_legacy_bundle` |
| Bundle filename | `ExpertSmart_Legacy_Archive.bundle` |
| Bundle SHA-256 | `395EBA59AA7F82C7E395FBA1FFD14200CB7537C7F2A57718816AD8C0430E8F3B` |
| Stash bundle | Not created (stash included in main bundle) |
| Bundle verify result | `VERIFIED` — bundle records complete history |
| Location | External — NOT inside this repository, NOT pushed to any remote |
| Creation date | 2026-08-02 |

**The bundle file must NOT be:**
- Copied into this repository
- Added to `.gitignore` or any tracked index
- Pushed to any remote
- Deleted without independent future approval

---

## Bundle Contents — 22 Refs

| Ref | HEAD Commit | Classification |
|-----|------------|----------------|
| `refs/heads/backup-before-mass-appraisal-template-export` | `b80f0c9d` | Already Represented — 0 unique commits vs main |
| `refs/heads/backup-before-mass-template-profiles` | `83a15f06` | Already Represented — 0 unique commits vs main |
| `refs/heads/backup/ci-before-fix-20260731` | `fc923d2b` | Already Represented — 0 unique commits vs main |
| `refs/heads/backup/pr3-baseline-2026-08-01` | `1af87c65` | Already Represented — verified post-merge CI snapshot |
| `refs/heads/feature/composite-frontend-wave5` | `effa7b9f` | Pending Analysis |
| `refs/heads/feature/mass-valuation-import-ui` | `6d2ee18e` | Merged — PR #6 squash-merged to main |
| `refs/heads/feature/r3-1-database-security-review` | `73c507b8` | Partially Unique — database subsystem + closure report |
| `refs/heads/feature/r3-1-security-only` | `9a1584a2` | Partially Unique — security subsystem + rename |
| `refs/heads/feature/r3-2-government-banking-funds-review` | `ae4884dc` | Pending Analysis |
| `refs/heads/feature/reports-initiative` | `43dffaf9` | Unique Migration Candidate — Semantic Review Required |
| `refs/heads/feature/requirements-checklist-ui` | `b34a5711` | Active development branch (legacy primary HEAD) |
| `refs/heads/main` | `5e83c8d0` | Canonical — matches origin/main |
| `refs/heads/site-practical-improvements` | `bc8e2f53` | Pending Analysis |
| `refs/heads/wip/r3-subsystems-checkpoint` | `99c78e63` | Scope-Frozen — 24 commits, 222 files, 53,856 insertions |
| `refs/tags/v1.0.0` | `e84b5fe0` | Release tag — preserved |
| `refs/tags/v1.0.1` | `c42bf49c` | Release tag — preserved |
| `refs/tags/v1.1.0` | `944addd0` | Release tag — preserved |
| `refs/tags/v1.1.1` | `dc91a103` | Release tag — preserved |
| `refs/tags/v1.1.2` | `c32e59a1` | Release tag — preserved |
| `refs/tags/v3.13-stable` | `880b8147` | Release tag — preserved |
| `refs/tags/v3.14-pilot-ready` | `2a4dd346` | Release tag — preserved |
| `refs/stash` | `1bb32948` | `batch1-density-pre-padding-notes-20260714T003046` — 25,174 insertions, 19 files |

---

## Stash Record

| Field | Value |
|-------|-------|
| Stash label | `batch1-density-pre-padding-notes-20260714T003046` |
| Stash commit SHA | `1bb32948348716159032139d8b6d26e8f32185a7` |
| Stash third-parent (untracked tree) | `250ed7d120f25218e4cf51c58cbe5a3f01fff1ba` |
| Insertions | +25,174 lines across 19 files |
| Secret scan result | No real secrets found in stash HEAD or untracked tree |
| Preservation status | `PRESERVED_IN_EXTERNAL_BUNDLE` |
| Migration status | `PENDING_WAVE_5_GATE` — must not be applied until stash analysis approved |

---

## Previously Unrecorded Branches (discovered in bundle)

Three branches were discovered in the bundle that were not in the prior branch analysis:
- `feature/composite-frontend-wave5` — pending unique-commit analysis
- `feature/r3-2-government-banking-funds-review` — pending unique-commit analysis
- `site-practical-improvements` — pending unique-commit analysis

These must be analyzed before any migration wave that could overlap with their content.

---

## Secret Scan Summary

| Scan | Result | Confidence |
|------|--------|-----------|
| `OFFICIAL_HISTORY_SCAN` | No real secrets — single false positive in `test_ph3_security.py` (security test fixtures) | `PARTIALLY_VERIFIED` (pattern scan only) |
| `LEGACY_WORKTREE_SCAN` | `ph3_security_report.json` contains key preview — file is UNTRACKED, protected by `ph*_report.json` gitignore rule, never committed | `LEGACY_ARCHIVE_CONTAINS_SENSITIVE_HISTORY` |
| `LEGACY_REFS_SCAN` | 16 refs scanned — all matches in `test_ph3_security.py` (false positive) | `PARTIALLY_VERIFIED` |
| `LEGACY_STASH_SCAN` | No real matches in stash HEAD or untracked tree | `PARTIALLY_VERIFIED` |
| `BUNDLE_INTEGRITY_CHECK` | `VERIFIED` — `git bundle verify` passed | `VERIFIED` |

**Overall scan confidence: `PARTIALLY_VERIFIED`** — pattern-based scan only. Full content-based scan with `gitleaks` or `trufflehog` is recommended before any push to a shared environment.

The finding in `LEGACY_WORKTREE_SCAN` (`ph3_security_report.json`) does NOT block migration because:
1. The file is UNTRACKED and protected by the existing `.gitignore` rule (`ph*_report.json`)
2. The referenced `service_account.json` no longer exists in the working tree
3. Neither file was ever committed to any Git repository
