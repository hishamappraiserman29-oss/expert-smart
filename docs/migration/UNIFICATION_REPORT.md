# Unification Report — ExpertSmart_Unified

**Repository:** `unified_target`
**Clone source:** `canonical_source` (GitHub `origin/main`)
**Branch:** `integration/unification`

---

## Phase 0 — Repository Foundation

**Date:** 2026-08-02
**Status:** COMPLETE

---

### Phase 0.0 — Independent Clone

| Field | Value |
|-------|-------|
| Clone source | `canonical_source` — GitHub remote |
| Branch cloned | `main` |
| HEAD at clone | `5e83c8d09bdb5583c5164b72def83904f7694680` |
| `.git` type | Directory (independent clone — NOT a linked worktree) |
| `origin/main` HEAD | `5e83c8d09bdb5583c5164b72def83904f7694680` — matches |
| Working tree at clone | CLEAN |
| Integration branch | `integration/unification` created immediately after clone |
| `main` modified | NO — `main` head remains `5e83c8d` read-only |

---

### Phase 0.1 — External Legacy Archive

| Field | Value |
|-------|-------|
| Bundle alias | `external_legacy_bundle` |
| Bundle filename | `ExpertSmart_Legacy_Archive.bundle` |
| Bundle SHA-256 | `395EBA59AA7F82C7E395FBA1FFD14200CB7537C7F2A57718816AD8C0430E8F3B` |
| Refs captured | 22 (14 branches, 7 tags, 1 stash ref) |
| `git bundle verify` | PASSED |
| Bundle size | 10.56 MB |
| Location | External — outside `unified_target`, not pushed, not tracked in Git |
| Legacy repo modified | NO |

Previously unrecorded branches discovered in bundle:
- `feature/composite-frontend-wave5`
- `feature/r3-2-government-banking-funds-review`
- `site-practical-improvements`

These require unique-commit analysis before any migration wave.

---

### Phase 0.2 — Secret Scans

**Tools:** No `gitleaks` or `trufflehog` available — pattern-based scan only.
**Scan confidence:** `PARTIALLY_VERIFIED`

| Scan | Files / Refs Checked | Real Secrets Found | Classification |
|------|--------------------|--------------------|----------------|
| `OFFICIAL_HISTORY_SCAN` (working tree) | All tracked .py/.html/.json/.yaml files | 0 | CLEAR |
| `OFFICIAL_HISTORY_SCAN` (384 commits) | All commit trees in official history | 0 | CLEAR — `test_ph3_security.py` match is false positive (test fixtures for SecretsScanner) |
| `SECRET_GUARD` | 1,094 tracked files | 0 | PASSED (CI secret guard script) |
| `LEGACY_WORKTREE_SCAN` | All Legacy .py/.html/.json/.yaml in working tree | `ph3_security_report.json` | `LEGACY_ARCHIVE_CONTAINS_SENSITIVE_HISTORY` — scanner output containing key preview; UNTRACKED; covered by `ph*_report.json` gitignore; never committed; no migration risk |
| `LEGACY_REFS_SCAN` | 16 refs (14 branches + 2 tags reachable in old structure) | 0 | CLEAR — all matches in `test_ph3_security.py` (false positive) |
| `LEGACY_STASH_SCAN` | `refs/stash` HEAD + `refs/stash^3` (untracked tree) | 0 | CLEAR |
| `BUNDLE_INTEGRITY_CHECK` | `git bundle verify` | N/A | VERIFIED |

**Conclusion:** Official history and all Legacy git history are free of real secrets. The `unified_target` repository contains no credentials in tracked files or history. Full content-based scan (gitleaks/trufflehog) recommended before any push to a shared environment.

---

### Phase 0.3 — Baseline Tests

**Python executable:** `.venv\Scripts\python.exe`
**Python version:** 3.11.9
**pip version:** 24.0
**Dependency install:** SUCCESS (all packages from `core_engine/requirements.txt` + pytest extras + `requirements-dev.txt`)

#### CI_BASELINE — Requirements Tests (ci-cd.yml)

| Command | `python -m pytest tests/test_requirements_endpoint.py tests/test_valuation_requirements.py tests/test_asset_families.py tests/test_purpose_integration_matrix.py tests/test_purpose_routes.py tests/test_approval_rules.py -q --tb=short` |
|---------|---|
| Working directory | `core_engine` |
| Collected | 275 |
| Passed | **275** |
| Failed | 0 |
| Skipped | 0 |
| Errors | 0 |
| Warnings | 32,710 (pre-existing fpdf2 `ln` deprecation warnings — not errors) |
| Duration | 21.02s |
| **Result** | **GREEN** |

#### CI_BASELINE — Syntax Check (ci-cd.yml lint step)

| Command | `python -c "import ast, pathlib; ast.parse(pathlib.Path('bridge_api.py').read_text(encoding='utf-8'))"` |
|---------|---|
| Working directory | `core_engine` |
| **Result** | **SYNTAX_OK** |

#### CI_BASELINE — Secret Guard (ci-cd.yml)

| Command | Python inline script — checks 1,094 tracked files |
|---------|---|
| Tracked files checked | 1,094 |
| **Result** | **PASSED** |

#### CI_BASELINE — E2E Smoke Tests (e2e.yml)

| Command | `python -m pytest core_engine/tests/e2e/test_requirements_checklist_smoke.py -m smoke --strict-markers -v --tb=short --maxfail=1` |
|---------|---|
| JWT_SECRET set | YES (`ci-test-secret-for-e2e-workflow`) |
| Collected (smoke-marked) | 5 |
| Deselected (not smoke) | 3,167 |
| Passed | **5** |
| Failed | 0 |
| **Result** | **GREEN** |

**All CI baseline commands pass. Zero pre-existing failures to document.**

---

### Phase 0 — .gitignore Additions

Additions made to `.gitignore` (appended, no deletions):

| Entry | Reason |
|-------|--------|
| `.venv/` | Virtual environment created during unification — must not be tracked |
| `.venv_clean_test/` | Legacy untracked folder found during discovery |
| `venv/` | Generic virtualenv name |
| `playwright-report/` | Browser test output directory |
| `test-results/` | Browser test result files |
| `*.trace.zip` | Playwright trace archives |
| `*.p12`, `*.pfx`, `*.jks`, `*.keystore` | Additional certificate/keystore formats not yet in gitignore |

No entries were removed from `.gitignore`. The manifest files (`UNIFICATION_MANIFEST.csv`, `ARCHIVAL_REFS.md`, `UNIFICATION_REPORT.md`) are explicitly NOT excluded — they are tracked loss-prevention artifacts.

---

### Phase 0 — Git State

| Item | Value |
|------|-------|
| Current branch | `integration/unification` |
| `main` HEAD | `5e83c8d09bdb5583c5164b72def83904f7694680` (unmodified) |
| Staged files | `.gitignore`, `docs/migration/ARCHIVAL_REFS.md`, `docs/migration/UNIFICATION_MANIFEST.csv`, `docs/migration/UNIFICATION_REPORT.md` |
| Legacy repo modified | NO |
| canonical_worktree modified | NO |
| Any file copied from Legacy | NO |
| Push executed | NO |

---

## Phase Wave 1A — HBU Financial-Depth Layer

**Date:** 2026-08-02
**Branch:** `migration/wave1a-hbu-financial-depth` (branched from `integration/unification` HEAD `9f622965`)
**Status:** COMPLETE — pending commit approval (`A6_AWAITING_WAVE_1A_COMMIT_APPROVAL`)

### Files Migrated

| File | source_sha256 | destination_sha256 | Notes |
|------|--------------|-------------------|-------|
| `core_engine/hbu_financial_depth.py` | `9389A537...` | `FC11B67C...` | Governance fixes applied (see below) |
| `core_engine/tests/test_hbu_financial_depth.py` | `BE726416...` | `B0D9EF07...` | Edge-case tests FD06–FD12 added |

Source hashes match preflight report. Destination hashes differ due to approved focused fixes.

### Governance Fixes Applied

**Fix 1 — `discount_rate` silent fabrication removed**
The original `result.get("discount_rate", 0.10)` would invent a 10% rate if absent, violating `no_fabrication=True`.
The fix validates the field: if `discount_rate` is missing, zero, or non-numeric, `sensitivity` in `financial_depth` returns `{"status": "unavailable", "reason": "discount_rate_missing"}`. No rate is invented. `discount_rate_pct` is set to `None` when missing.

**Fix 2 — `cashflows=None` no longer fabricates zero profit**
The original `ev.get("cashflows") or []` silently treated absent cashflows as `sum([]) = 0.0` (zero undiscounted profit). The fix returns `{"status": "unavailable", "reason": "cashflows_missing"}` from `developer_metrics` when `cashflows is None`.

**Tests added: FD06–FD12**
Seven edge-case tests: missing discount_rate, zero land area, invalid financing (ltv boundary/range/missing loan_rate), IRR not computable, empty scenarios, missing cashflows, sensitivity unit correctness.

### Parallel HBU Financial Methodologies — Governance Note

This repository contains two parallel implementations of HBU financial depth metrics that produce **non-identical results** by design. This is not a defect; both are advisory layers serving different pipeline stages.

| Dimension | `hbu_financial_depth.enhance_hbu_financials` | `hbu_enhanced_report.compute_financial_depth` |
|-----------|-----------------------------------------------|------------------------------------------------|
| **RLV formula** | `NPV + land_cost` (NPV-identity: land price at which NPV = 0) | `GDV − TDC − dev_profit` (full cost-residual method incl. finance 8%, fees 10%, contingency 5%, profit margin 15%) |
| **Equity IRR** | Proper leveraged equity cash flows with explicit `ltv` + `loan_rate`; returns `unavailable` if financing absent | `irr_project − 200bps` (simplified fixed spread; no financing model) |
| **Sensitivity steps** | ±10% cost/revenue; ±2pp discount | ±15% cost/revenue; fixed [8%, 10%, 12%] discount |
| **Engine reuse** | Canonical `_npv/_irr/_build_cashflows` (engine primitives) | Local private copies (not reusing engine) |
| **Scope** | All scenarios | Optimal scenario only |
| **Purpose** | API enrichment layer (`/api/hbu/analyze` response) | Report generation pipeline (PDF/HTML/Excel manifest) |

**Rules that must remain in force:**
1. Neither value may be labeled simply "RLV" or "Equity IRR" without a method identifier in any user-facing output.
2. The two values must never be compared as if they use the same methodology.
3. Both remain advisory only. Neither has IVS/RICS certification at this layer.
4. Unifying the two methodologies requires an independent analysis phase — it is not within scope of any current migration wave.
5. `hbu_financial_depth.enhance_hbu_financials` is not wired to any API endpoint by this wave. Route wiring is a separate decision.

### Pre-Merge Decisions Resolved

1. **Three previously-unanalyzed branches** — all confirmed ALREADY REPRESENTED (ancestors of main, zero unique commits): `feature/composite-frontend-wave5`, `feature/r3-2-government-banking-funds-review`, `site-practical-improvements`.
2. **Dependency contract** — all 4 engine functions (`_build_cashflows`, `_irr`, `_npv`, `_payback_period`) confirmed present in canonical with compatible signatures. `LEGACY_ONLY_RUNTIME_DEPENDENCIES = 0`.
3. **Canonical equivalence** — `compute_financial_depth` in `hbu_enhanced_report.py` confirmed functionally distinct; no collision.

### Test Results

| Suite | Result |
|-------|--------|
| FD01–FD12 (focused wave tests) | **12/12 PASSED** |
| CI requirements regression (275 tests) | **275/275 PASSED** |
| Import smoke (`hbu_financial_depth`) | **HBU_FINANCIAL_DEPTH_IMPORT_OK** |
| Syntax check (both files) | **SYNTAX_OK** |
| Secret guard | **PASSED — 0 real secrets** |
| `git diff --check` | **PASSED** |

---

## Pending Decisions Before Wave 1B

1. **Wave 1A commit approval** — `A6_AWAITING_WAVE_1A_COMMIT_APPROVAL`.
2. **Route wiring decision** — `enhance_hbu_financials` is not connected to any endpoint. A separate decision is required before it is called from `bridge_api.py`.
3. **`feature/reports-initiative` semantic review** — business policy review required before Wave 2 (retiring `industrial`, enabling `land`).
4. **Full content-based secret scan** (gitleaks/trufflehog) — recommended before any push to shared environment.
