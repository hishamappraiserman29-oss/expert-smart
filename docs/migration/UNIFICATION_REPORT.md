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

---

## Phase Wave 1B — HBU Inputs Sourcing Bridge

**Date:** 2026-08-02
**Branch:** `migration/wave1b-hbu-inputs-bridge` (branched from `integration/unification` HEAD `56da9ddd`)
**Status:** COMPLETE — pending commit approval (`A6_AWAITING_WAVE_1B_COMMIT_APPROVAL`)

### Files Migrated

| File | source_sha256 | destination_sha256 | Notes |
|------|--------------|-------------------|-------|
| `core_engine/hbu_inputs_bridge.py` | `D7500BCA...` | `E60E7878...` | Governance fixes applied (see below) |
| `core_engine/tests/test_hbu_inputs_bridge.py` | `7734F896...` | `564F673F...` | Tests HB08–HB19 added; HB01–HB07 updated |

Source hashes match Wave 1B preflight report. Destination hashes differ due to approved focused fixes.

### Wave 1B Governance Controls

**Fix 1 — Enrichment opt-in (`enable_enrichment` parameter)**
Original code created `MarketEnrichmentLayer(use_mock=False)` unconditionally when no layer was supplied, potentially calling `ExistingLocalMarketFeedProvider` and `KnowledgeStoreProvider` without caller consent (violates Data Minimization).
The fix adds `enable_enrichment: bool = False`. Enrichment is now activated only when: `enrichment_layer` is provided, OR `use_mock_enrichment=True`, OR `enable_enrichment=True`. Without opt-in, all enrichment-dependent fields return `"enrichment_not_enabled"` in `unavailable`.

**Fix 2 — Geography guard (`_GEOGRAPHY_RESTRICTED_SOURCES` + `_enrichment_covers_geography`)**
`ExistingLocalMarketFeedProvider` uses `EgyptianPriceRangeDictionary` (Egyptian pricing) regardless of `country_code`. For `country_code="SA"`, these values were labeled `draft_pending_review` but were still elevated to `inputs` — misrepresenting geographically incompatible data as HBU inputs.
The fix adds `_GEOGRAPHY_RESTRICTED_SOURCES = {"EgyptianPriceRangeDictionary": {"EG", "EGP"}}` and `_enrichment_covers_geography()` which examines `data_source_log`. When a restricted source is detected for a non-matching geography, ALL enrichment values from that run go to `unavailable` with reason `"enrichment_geography_unsupported"`. Mock and knowledge-store sources are unrestricted.

**Fix 3 — Confidence from evidence only (no 65% heuristic)**
Original code fell back to `ma_conf = 65.0` when no IAAO ratio study was available, inventing a heuristic confidence value.
The fix removes this fallback entirely. When `ratio_study.n_sales == 0` or `cod` is absent, `confidence=None` is stored with `confidence_status="unavailable"` and `confidence_reason="ratio_study_missing"`. These fields propagate to the `provenance` table. Confidence from a real ratio study is still computed as `clamp(50, 95, 100 - COD)`.

**Fix 4 — Temporary artifact lifecycle (`TemporaryDirectory`)**
Original code used `tempfile.mkdtemp()` — the temp directory (and Excel artifact inside it) persisted after the function returned, accumulating on disk.
The fix uses `tempfile.TemporaryDirectory(prefix="hbu_ma_")` as a context manager. When `work_dir=None`, the directory is created, `run_mass_appraisal` runs, and the directory is deleted on exit (even if an exception occurs). When the caller supplies `work_dir`, the caller manages its lifecycle (documented in the function docstring).

**Fix 5 — base_market_ppm confirmed Neutral Sentinel (Path B)**
Investigation of `run_mass_appraisal` revealed that `_market_adjustment(base_ppm, unit, market_ppm)` accepts `market_ppm` but never uses it. Therefore `base_market_ppm=0` (the missing-key default) has no effect on any computed value. The docstring is updated to document this contract. Test HB10 verifies numerically that `base_market_ppm=0`, `None`, and `99999` all produce identical `avg_ppm`.

**Fix 6 — Exception propagation documented**
No exception handling was added around `run_mass_appraisal` or `layer.enrich()` calls. Both propagate as-is. Tests HB16 and HB17 confirm that exceptions do not produce fabricated fallback results. Future route wiring is responsible for converting these to appropriate API errors.

### Privacy Classification

`LOW_CONDITIONAL_PRIVACY_RISK`:
- No PII fields in the documented schema (`case_id` and comparable IDs are caller-controlled identifiers — their sensitivity depends on the caller).
- `ExistingLocalMarketFeedProvider` uses local static data (no external transfer).
- `KnowledgeStoreProvider` is a local Qdrant service — constitutes a service boundary even when not public internet.
- Geography and property metadata may be sent to a local provider when `enable_enrichment=True`.
- No raw identifiers are recorded in `source_name` or `reconciliation_note` (verified by HB19).
- After Fix 1 (opt-in), enrichment providers are never activated without explicit caller consent.

### base_market_ppm Contract (Path B — Neutral Sentinel)

`_market_adjustment(base_ppm, unit, market_ppm)` ignores its `market_ppm` parameter entirely.
Consequence: `base_market_ppm=0` (missing-key default) is equivalent to any other value — it has zero effect on `avg_ppm`, per-unit `final_ppm`, or `portfolio_summary`. This was verified by test HB10.
The default `float(case.get("base_market_ppm", 0) or 0)` is retained as a structural sentinel.

### Pre-Migration Decisions Resolved

1. **LEGACY_ONLY_RUNTIME_DEPENDENCIES = 0** — all imports (`mass_appraisal`, `enrichment.market_enrichment`) resolve in Unified.
2. **Enrichment interface compatibility** — Unified enrichment files confirmed compatible with bridge's call sites (`enrich`, `build_request`, `EnrichmentResult.to_dict()`, `.can_generate_final_report()`, `.suggested_values`, `.market_indicators`, `.data_source_log`).
3. **Egyptian geography data** — confirmed restricted source; geography guard prevents misuse.
4. **base_market_ppm** — confirmed Neutral Sentinel (Path B) by code inspection and test.
5. **Module wiring** — `hbu_inputs_bridge` remains library-only and unwired after migration. No endpoint created.

### Test Results

| Suite | Result |
|-------|--------|
| HB01–HB19 (focused wave tests) | **19/19 PASSED** |
| Wave 1A regression (FD01–FD12) | **12/12 PASSED** |
| CI requirements regression (275 tests) | **275/275 PASSED** |
| Import smoke (`hbu_inputs_bridge`) | **HBU_INPUTS_BRIDGE_IMPORT_OK** |
| Syntax check (both files) | **SYNTAX_OK** |
| Secret guard (Wave 1B files) | **PASSED — 0 real secrets** |
| `git diff --check` | **PASSED** |

---

## Pending Decisions Before Wave 1C / Wave 2

1. **Wave 1B commit approval** — `A6_AWAITING_WAVE_1B_COMMIT_APPROVAL`.
2. **Route wiring decisions** — both `enhance_hbu_financials` (Wave 1A) and `build_hbu_inputs` (Wave 1B) are library-only. Separate decisions required before either is called from `bridge_api.py`.
3. **`feature/reports-initiative` semantic review** — business policy review required before Wave 2.
4. **Full content-based secret scan** (gitleaks/trufflehog) — recommended before any push to shared environment.

---

## Phase Wave 1C — HBU Section Renderer

**Date:** 2026-08-02
**Branch:** `migration/wave1c-hbu-report-sections` (branched from `integration/unification` HEAD `4c45894d`)
**Status:** COMPLETE — pending commit approval (`A6_AWAITING_WAVE_1C_COMMIT_APPROVAL`)

### Classification

| Field | Value |
|-------|-------|
| Option | `OPTION_C — LIBRARY_PRESERVATION_ONLY` |
| Code quality | `PRODUCTION_HARDENED` |
| Runtime status | `INACTIVE_LIBRARY` |
| Wiring status | `LIBRARY_ONLY_UNWIRED` |
| Canonical renderer | `core_engine/reports/hbu_enhanced_report.py` |
| Source of truth changed | `False` |

### Files Migrated

| File | source_sha256 | destination_sha256 | Notes |
|------|--------------|-------------------|-------|
| `core_engine/hbu_report_sections.py` | `74AFFA22F3190A6F4EE51A087D0E7303826CBB59DCBD72FD5230B4B5FD9892E4` | `C05ACA9411807841E5D941492C15652B33A0FF5B8A052EE769BD02FF48BB22E5` | Governance fixes applied + scenario RLV label correction (see below) |
| `core_engine/tests/test_hbu_report_sections.py` | N/A (new file) | `4F4919AA3E153C340015E2864AAC9AD7296C43CA08ADF3D60C30A4073C5FC83C` | New test suite — 55 tests RS01–RS28+ (5 new RLV-label policy tests added) |

Source hash matches copy-integrity check (COPY_INTEGRITY_PASS). Destination hash differs due to approved focused fixes.

### Governance Fixes Applied

**Fix 1 — HTML injection guard (`_esc()` centralized helper)**
The original module contained ~32 sites where external data was interpolated into HTML f-strings without escaping — XSS risk across all section functions.
The fix adds `import html as _html` and `_esc(value)` using `html.escape("" if value is None else str(value), quote=True)`. All external data (site fields, planning fields, scenario values, synth_label, governance text, labels) passes through `_esc()` before HTML interpolation. `section_html` is a trusted callback and is not escaped. Formatter callbacks (`fmt_currency`, `pct`) are contractually plain-text-only — they are also wrapped in `_esc()` at all call sites. Final count: `UNSAFE_HTML_INTERPOLATIONS_AFTER_FIX = 0`.

**Fix 2 — Missing-value policy (physical dimensions)**
Physical dimensions (land_area, frontage, depth, road_width) originally treated any falsy value (including `0`) as unavailable and silently fabricated "محدود" for missing road_width.
The fix: None or `<= 0` → "غير متاح" for physical dimensions. No fabricated "محدود". Road_width missing → "غير متاح".

**Fix 3 — Missing-value policy (financial fields)**
Financial values (NPV, IRR, RLV, profit, cashflows) originally mixed `None` → "غير متاح" with `0` treated as falsy and silently shown as unavailable.
The fix: uses `isinstance(v, (int, float))` to distinguish numeric zero from None. `None` → "غير متاح"; `0` is a valid financial value and renders as zero.

**Fix 4 — Empty sensitivity grid → text message**
Empty `sensitivity_grid` originally rendered as `<table></table>` — invalid markup and confusing UI.
The fix replaces it with an Arabic paragraph: "بيانات الحساسية غير متاحة — يتطلّب معدل خصم وحساسية من تحليل العمق المالي (Wave 1A)".

**Fix 5 — Empty discount table → text message**
Same pattern — empty discount rows rendered as bare `<table>`. Replaced with text message.

**Fix 6 — Supply/demand fabrication removed**
Original code emitted unconditional positive market assertions ("الطلب في تنامٍ مستمر...") regardless of evidence.
The fix conditions assertions on `has_approved` / `has_draft` / no evidence. Three distinct outcome paths: approved evidence, draft evidence, no evidence available. No unconditional claims.

**Fix 7 — `fmt_sar` renamed `fmt_currency`**
Function renamed from `fmt_sar` to `fmt_currency` — no backward-compatibility alias needed (zero callers in Unified).

**Fix 8 — RTL / accessibility**
Added `dir="rtl"` on all content containers, `<bdi dir="ltr">` on numeric values, `scope="col"` on all `<th>` elements, `overflow-x:auto` wrappers on all tables, feasibility text labels alongside color indicators.

**Fix 9 — RLV labels carry NPV identity method ID (Wave 1A)**
Both Section C per-scenario RLV and Section D optimal RLV labels now carry `"هوية NPV (Wave 1A)"` method identifier, consistent with `hbu_financial_depth.enhance_hbu_financials` which computes `RLV = NPV + land_cost`. The GDV/TDC/developer-profit formula belongs exclusively to the canonical `hbu_enhanced_report.py`.

**Fix 10 — Governance constants and module docstring**
Added `_advisory_only = True`, `_certification_ready = False`, `_ADVISORY_DISCLAIMER` constant, and comprehensive module docstring classifying the file as `INACTIVE_LIBRARY / LIBRARY_ONLY_UNWIRED`.

### RLV Source Matrix

| Location | Source key | Verified producer | Label policy |
|----------|-----------|-------------------|--------------|
| Section C | `scenarios_evaluated[*].residual_land_value` | Not produced by the canonical engine; enrichment source unverified unless explicit metadata present | Neutral ("المنهج غير موثق") when value present but no `rlv_method_id`; NPV-identity label only when `sc["rlv_method_id"] == "NPV_IDENTITY_RLV"`; unavailable message when value absent |
| Section D | `financial_depth.residual_land_value` | `hbu_financial_depth.enhance_hbu_financials` (Wave 1A), formula `RLV = NPV + land_cost` | NPV-identity label always — producer is verified |
| Section D per m² | `financial_depth.rlv_per_m2` | `hbu_financial_depth.enhance_hbu_financials` (Wave 1A), formula `RLV / land_area` | NPV-identity-per-m² label always — producer is verified |

**Engine verification:** `hbu_analysis_engine._evaluate_scenario` does NOT produce `residual_land_value`. A value at `sc["residual_land_value"]` may arrive from Wave 1A or any other enrichment path; its producer is confirmed only when `sc["rlv_method_id"] == "NPV_IDENTITY_RLV"` is present. Section C unavailable message: "غير متاح — محرك HBU لا ينتج RLV على مستوى السيناريو، ويلزم إثراء مالي موثق."

### Correct Pipeline Order

```
build_hbu_inputs (Wave 1B) → run_hbu_analysis (engine) → enhance_hbu_financials (Wave 1A) → build_enhanced_sections (Wave 1C)
```

### What Is NOT Changed

- `core_engine/reports/hbu_enhanced_report.py` — canonical active HBU renderer: **unchanged**
- `core_engine/bridge_api.py` — no route added, no import added: **unchanged**
- `frontend/index.html` — no frontend changes: **unchanged**
- All Wave 1A and 1B files — unchanged by this wave

### Test Results

| Suite | Result |
|-------|--------|
| RS01–RS28+ (55 focused wave tests) | **55/55 PASSED (1.01s)** |
| Wave 1A regression (FD01–FD12) | **12/12 PASSED** |
| Wave 1B regression (HB01–HB19) | **19/19 PASSED** |
| CI requirements regression (275 tests) | **275/275 PASSED** |
| Import smoke (`hbu_report_sections`) | **HBU_REPORT_SECTIONS_IMPORT_OK** |
| Syntax check (both files) | **SYNTAX_OK** |
| Secret guard (Wave 1C files) | **PASSED — 0 real secrets** |
| `git diff --check` | **PASSED** |

### Pending Decisions After Wave 1C

1. **Route wiring decisions** — `build_enhanced_sections` (Wave 1C), `enhance_hbu_financials` (Wave 1A), and `build_hbu_inputs` (Wave 1B) are all library-only. Separate decisions required before any is called from `bridge_api.py`.
2. **Full content-based secret scan** (gitleaks/trufflehog) — recommended before any push to shared environment.

---

## Phase Wave 2 — Reports Initiative R2 Closure

**Date:** 2026-08-02
**Source commit:** `feature/reports-initiative` @ `43dffaf95e9c1048a31c965c13f3101c8e194827`
**Branch:** `migration/wave2-reports-initiative-r2-verification`
**Status:** COMPLETE — pending commit approval (`A6_AWAITING_WAVE_2_CLOSURE_COMMIT_APPROVAL`)
**Migration type:** `VERIFICATION_AND_DOCUMENTATION_ONLY` — no Production code migration

---

### Wave 2 Summary

Wave 2 is a closure wave. The business-policy preflight determined that all five files from commit `43dffaf` on `feature/reports-initiative` are already present in Unified — absorbed through a different migration path. No cherry-pick, no file copy, no Production code modification, and no fixture regeneration was performed.

The wave's only deliverable is a new contract-test file (`test_request_validation_property_types.py`) that formally documents the approved policy decisions and provides regression gates.

---

### Source Branch and Commit

| Field | Value |
|-------|-------|
| Branch | `feature/reports-initiative` |
| Commit SHA | `43dffaf95e9c1048a31c965c13f3101c8e194827` |
| Unique commits vs main | **1** — `43dffaf` only |
| Merge base (vs Unified main) | `0bd505653c50a31a05ce7b521fcfe82ab4d1c105` |
| Cherry-pick suppression | `43dffaf` did not appear in `--cherry-pick` output — its `request_validation.py` diff is patch-equivalent to a commit already in main's history |

---

### Pre-Absorption Matrix — All Five `43dffaf` Files

| File | Legacy blob SHA | Unified blob SHA | Equivalent | Migration action |
|------|----------------|-----------------|------------|-----------------|
| `core_engine/api/request_validation.py` | `83f42fe8` | `83f42fe8` | **YES** | NO_ACTION_PREABSORBED |
| `core_engine/tests/fixtures/baseline_land_detailed.json` | `7d768f34` | `7d768f34` | **YES** | NO_ACTION_PREABSORBED |
| `core_engine/tests/fixtures/baseline_land_legacy.json` | `4ac1686f` | `4ac1686f` | **YES** | NO_ACTION_PREABSORBED |
| `core_engine/tests/fixtures/report_land.json` | `618a38a8` | `618a38a8` | **YES** | NO_ACTION_PREABSORBED |
| `core_engine/tests/test_report_baseline.py` | `fe202646` | `5756220a` | **NO** | PREABSORBED_WITH_IMPROVEMENT |

`test_report_baseline.py` blob differs because Unified added +4 lines: a `try/finally` CWD-restore governance fix (`_ORIG_CWD = os.getcwd()` wrapper). BL08 and BL09 (the `43dffaf` additions) are fully present in the Unified version.

---

### Policy Decisions

| Policy | Decision | Evidence |
|--------|----------|----------|
| `INDUSTRIAL_POLICY` | **KEEP** | Phase 9.1 added `industrial` to `SUPPORTED_ASSET_TYPES` with 4 purposes, `_INDUSTRIAL` FieldSpec, active CI tests REQ19/REQ21, frontend tax-tab option, HBU scenarios, bridge_api branching |
| `LAND_RUNTIME_READINESS` | **READY** | `land` in `SUPPORTED_ASSET_TYPES`; `_LAND` FieldSpec; REQ07/REQ14 CI gates; `adapters/land.py`; bridge_api routes; report templates; i18n; mass valuation contracts; professional valuation |
| `43dffaf` industrial retirement | **NOT APPLIED** | Retirement was the original commit's intent but is superseded by Phase 9.1 expansion. Applying it would break REQ19, REQ21, frontend tax tab, HBU scenarios |
| `SCHEMA_DRIFT_PRESENT` | **YES** | 7 separate property-type lists across the codebase (see below); deferred to independent initiative |
| `FRONTEND_BACKEND_SCHEMA_MATCH` | **PARTIAL_MATCH** | Simple valuation tab submits Arabic string values; tax tab and professional tab submit English codes / subtypes |
| `WAVE_2_PRODUCTION_CODE_MIGRATION_REQUIRED` | **False** | All code changes already present in Unified |
| `MIGRATION_TECHNIQUE` | **VERIFICATION_AND_DOCUMENTATION_ONLY** | No cherry-pick; no copy; no modification to any Production file |

---

### Current `SUPPORTED_ASSET_TYPES` Registry

```python
SUPPORTED_ASSET_TYPES: frozenset[str] = frozenset({
    "residential",
    "commercial",
    "land",
    "industrial",   # Phase 9.1 — KEEP
    "hotel",        # Phase 9.1
})
```

Search schema `allowed_values` at runtime: `['commercial', 'hotel', 'industrial', 'land', 'residential']`

The registry has **5 members**, not 3 as `43dffaf` originally targeted.

---

### Fixture Inventory and Privacy Classification

| Fixture | SHA-256 | Classification |
|---------|---------|---------------|
| `report_land.json` | `EF2E7B7F…` | `SYNTHETIC_SAFE_FIXTURE` — Test Client / Test Appraiser / Cairo New Cairo (generic area) / frozen date 2026-01-01 / no real names, IDs, coordinates, or credentials |
| `baseline_land_legacy.json` | `B986E51A…` | `SYNTHETIC_SAFE_FIXTURE` — Excel golden snapshot; cost=0 (correct for vacant land); all values trace to explicit input |
| `baseline_land_detailed.json` | `AD3DA796…` | `SYNTHETIC_SAFE_FIXTURE` — same as above, detailed report style |

**No fabricated values in fixtures.** Cost weight is 0 (no cost approach for land). Income and comparable weights are explicitly provided. `hbu: "residential"` is a planning input, not an appraiser conclusion. No building fields appear for vacant land.

---

### Schema Drift — Seven Sources of Truth

| Source | Members | Notes |
|--------|---------|-------|
| `adapters/valuation_requirements.py` SUPPORTED_ASSET_TYPES | 5 (residential, commercial, land, industrial, hotel) | Authoritative registry |
| `api/request_validation.py` search schema | Delegates to above (sorted) | DRY — no drift here |
| `mass_valuation/contract/schema_validator.py` | residential, commercial, industrial, land, mixed_use, villa, apartment, ... | Additional sub-types; no hotel |
| `mass_valuation/contract/data_models.schema.json` | Same as above | No hotel |
| `security/input_validator.py` | residential, commercial, industrial, land, mixed_use, ... | No hotel |
| `adapters/commercial.py` | office, retail, mixed_use, industrial, warehouse | No land; sub-type list |
| `hbu_scenarios.py` SCENARIO_TYPES | residential, commercial, industrial, hotel, mixed_use | No land |

Schema drift resolution and Frontend normalization (`"أرض"` → `"land"`) are deferred to an independent initiative — out of scope for Wave 2.

---

### Baseline Tests — All Green

| Suite | Result |
|-------|--------|
| BL01–BL09 (report baseline) | **9/9 PASSED** |
| PT01–PT09 (new contract tests, 10 runs) | **10/10 PASSED** |
| Wave 1A regression (FD01–FD12) | **12/12 PASSED** |
| Wave 1B regression (HB01–HB19) | **19/19 PASSED** |
| Wave 1C regression (RS01–RS28+, 55 tests) | **55/55 PASSED** |
| CI requirements regression | **275/275 PASSED** |

---

### Property-Type Contract Test Details (PT01–PT09)

| Test | Assertion | Result |
|------|-----------|--------|
| PT01 — Registry delegation | `allowed_values == sorted(SUPPORTED_ASSET_TYPES)` — no hardcoded list | PASSED |
| PT02 — land accepted | `validate_request("search", {"property_type": "land"})` → `(True, [])` | PASSED |
| PT03 — industrial accepted | `validate_request("search", {"property_type": "industrial"})` → `(True, [])` | PASSED |
| PT04 — hotel accepted | `validate_request("search", {"property_type": "hotel"})` → `(True, [])` | PASSED |
| PT05a — residential accepted | `validate_request("search", {"property_type": "residential"})` → `(True, [])` | PASSED |
| PT05b — commercial accepted | `validate_request("search", {"property_type": "commercial"})` → `(True, [])` | PASSED |
| PT06 — unknown rejected | `"unknown_asset"` → error contains "must be one of" | PASSED |
| PT07 — missing rejected | empty payload → "Missing required field: property_type" | PASSED |
| PT08 — case sensitivity | `"Land"` rejected — no normalization; contract documented | PASSED |
| PT09 — no-industrial-retirement guard | `"industrial" in SUPPORTED_ASSET_TYPES` AND in search schema | PASSED |

---

### Golden Fixture Integrity After Tests

| Fixture | SHA-256 before | SHA-256 after | Unchanged |
|---------|---------------|--------------|-----------|
| `report_land.json` | `EF2E7B7F…` | `EF2E7B7F…` | **YES** |
| `baseline_land_legacy.json` | `B986E51A…` | `B986E51A…` | **YES** |
| `baseline_land_detailed.json` | `AD3DA796…` | `AD3DA796…` | **YES** |

`FIXTURE_HASHES_UNCHANGED = True`. `UPDATE_SNAPSHOTS` env var was absent throughout.

---

### Deferred Items

1. **Schema drift** — 7 separate property-type lists with differing membership require a dedicated unification initiative (not Wave 2).
2. **Frontend normalization** — simple-valuation tab submits Arabic string values (`"أرض"`) as form values; these are not validated against the search schema (different endpoint). Resolving the `PARTIAL_MATCH` is deferred.
3. **Route wiring** — `build_enhanced_sections` (Wave 1C), `enhance_hbu_financials` (Wave 1A), `build_hbu_inputs` (Wave 1B) remain library-only. Separate decisions required.
4. **Full content-based secret scan** (gitleaks/trufflehog) — recommended before any push.
5. **Stash analysis** (`PENDING_WAVE_5_GATE`) — must not be applied until gate opens.

---

### What Was NOT Done in This Wave

- No cherry-pick of `43dffaf`
- No file copy from Legacy
- No modification to `request_validation.py`
- No modification to `adapters/valuation_requirements.py`
- No fixture regeneration (`UPDATE_SNAPSHOTS` not set)
- No schema changes to mass_valuation contracts
- No frontend changes
- No route changes in `bridge_api.py`
- No push
- No direct commit to `integration/unification`

---

## Wave 3A — Standards Compliance Developer Tool Preservation

**Branch:** `migration/wave3a-standards-compliance-devtool`
**Decision:** `OPTION_D_DEVELOPER_TOOL_PRESERVATION`
**Date:** 2026-08-02

### Candidate Source Hashes (Legacy untracked working tree)

| File | SHA-256 |
|---|---|
| `standards_compliance_visual_qa_generator.py` | `33532171EEA4A2D3CD41DA9B97161247D3032C419EE8819CF35577CC9A35F4C1` |
| `pv_standards_compliance_endpoint.py` | `4EB14FA5BDA15D498C9D203B20208B641DCD40601964BB999F02F9A54668EAFB` |
| `test_pv_standards_compliance_deep_visual_qa.py` | `B5D0DCD3A9B077D1B1BA98365F99FE351092A77C8CC4E68F370B2AE3C85188F1` |

None of the three candidate files had git history in either repository.

### Contract Matrix

```
CONTRACT_MATRIX_COMPLETED       = True
ACTIVE_ENDPOINT_MIGRATION_APPROVED = False
```

All 18 contract dimensions were assessed (Sections A–W of the Wave 3 Preflight Report).
Two structural blockers were identified for the endpoint:

1. `CONCURRENCY_SAFETY = UNSAFE` — fixed module-level `CASE_ID` caused all concurrent
   calls to write the same filenames.
2. `TEST_QUALITY = NOT_CI_SAFE` — tests SC-D21 to SC-D40 required pre-generated
   artifacts and could not be added to the CI baseline without restructuring.

### Why the Endpoint Was Not Migrated

`bridge_api.py` in Unified already contains the v1 registration stub at lines 12701–12705,
currently silently skipped because the module is absent.  Simply copying
`pv_standards_compliance_endpoint.py` would activate six HTTP routes on the next server
restart without addressing the two blockers above.

```
ENDPOINT_STATUS    = BLOCKED_NOT_MIGRATED
ROUTE_ACTIVATION   = NONE
BRIDGE_API_CHANGE  = NONE
```

### What Was Migrated

**Generator only** — `core_engine/standards_compliance_visual_qa_generator.py` — with
the following hardening applied before copy:

| Property | Before | After |
|---|---|---|
| Runtime status | BROWSER_DEPENDENT_FILE_WRITER (unclassified) | CLI_ONLY_UNWIRED |
| Output path | Fixed module-level constant (project tree) | Caller-supplied `output_root` (required) |
| Concurrency | UNSAFE — shared CASE_ID filenames | SAFE_WITH_UNIQUE_WORKDIR per call |
| Run isolation | None | `<output_root>/<case_id>/<run_id>/` |
| Overwrite policy | Always overwrites | `FileExistsError` by default; opt-in `overwrite=True` |
| Path safety | None | `_sanitize_component()` regex + `relative_to()` containment check |
| Valuer name | A realistic-looking personal valuer identity and professional credential (removed) | `"مثمن تجريبي — بيانات QA اصطناعية"` (explicitly synthetic) |
| HTML escaping | None | `_esc()` applied at every string-insertion site |
| Browser lifecycle | No try/finally | `finally: page.close()` + `finally: browser.close()` |
| Partial cleanup | None | Failed run removes only its own created files |
| CLI interface | Bare `__main__` block | `argparse` with `--output-dir` (required), `--case-id`, `--run-id`, `--overwrite` |
| Governance flags | 6 flags | 8 flags — added `official_compliance_decision=False`, `synthetic_data=True` |
| Module docstring | Functional description only | DEVELOPER_TOOL classification docstring |

**New test file** — `core_engine/tests/test_standards_compliance_visual_qa_generator_unit.py`
— 28 tests (VT01–VT28), all CI-safe (no real browser, no network, no persistent project
artifacts).  No Legacy deep-visual test file copied.

### Classification

```
GENERATOR_STATUS            = DEVELOPER_TOOL_PRESERVATION
GENERATOR_RUNTIME_STATUS    = CLI_ONLY_UNWIRED
ENDPOINT_STATUS             = BLOCKED_NOT_MIGRATED
ROUTE_ACTIVATION            = NONE
PLAYWRIGHT_INTEGRATION_TESTS = DEFERRED_OPTIONAL
VISUAL_SCREENSHOT_APPROVAL  = MANUAL_DEVELOPER_WORKFLOW
```

### Endpoint Redesign Prerequisites (for Wave 3B, not yet approved)

Before the endpoint can be migrated:

1. Resolve `CONCURRENCY_SAFETY = UNSAFE` — parameterize output paths per request.
2. Restructure SC-D21 to SC-D40 as optional integration tests with explicit fixture
   generation; extract SC-D01 to SC-D20 as CI-safe unit tests.
3. Add SC02–SC05 route contract tests.
4. Sanitize `str(exc)` in 500 responses (error path exposes internal paths).
5. Fix `score_pct` initial assignment bug (line 99 of the Legacy endpoint).

### What Was NOT Done in Wave 3A

- `pv_standards_compliance_endpoint.py` — not copied
- `test_pv_standards_compliance_deep_visual_qa.py` — not copied (NOT_CI_SAFE)
- `bridge_api.py` — unchanged
- No HTTP routes activated
- No real browser executed during implementation
- No persistent artifacts generated under the repository tree
- No push
