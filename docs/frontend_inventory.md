# Frontend Inventory — Phase 21

Generated: Phase 21 Step 0 (documentation-first, non-destructive).
Branch: `feature/requirements-checklist-ui` (HEAD `bf52497`).

> **Governance rule**: No file may be moved or deleted without Gate B approval.
> Moving ANY file changes its URL (served via `serve_static /<path:path>`) and may break tests or JS references.

---

## 1. Static-serving mechanism

`bridge_api.py:382-383` sets `static_folder=_FRONTEND_DIR`.

Three named routes serve frontend content:

| Route | Handler | File(s) | Line |
|---|---|---|---|
| `GET /` | `serve_index()` | `index.html` (primary) → `sovereign_brain.html` (fallback) | 674 |
| `GET /agent` | `agent_chat_ui()` | `agent_chat.html` | 9345 |
| `GET /<path:path>` | `serve_static()` | Any file in `frontend/` by name | 683 |

**Implication**: Every file in `frontend/` is reachable at `/<filename>`. Moving a file to a subdirectory changes its URL (e.g., `/sovereign.html` → `/_legacy/sovereign.html`) and would break any JS `fetch()` or `href` that references the old path.

---

## 2. Active / Served Files — DO NOT MOVE

| File | Size (bytes) | Served at | Referenced by | Endpoints called | Action |
|---|---|---|---|---|---|
| `index.html` | 3,222,602 | `/` (primary) | `bridge_api.py:677` | `/api/valuation`, `/api/valuation/requirements`, `/api/valuation/composite`, `/api/price-index`, `/api/radar/*`, `/api/mass-appraisal/*`, `/api/reports`, `/api/auth/verify`, `/api/ingest`, `/api/upload`, `/api/fraud/detect`, `/api/geo/risk`, `/api/demographic/flow`, `/api/image/geo-analyze` | **KEEP — primary UI** |
| `sovereign_brain.html` | 196,921 | `/` (fallback if index.html absent) | `bridge_api.py:677` | `/api/advisor`, `/api/advisor/health`, `/api/ingest`, `/api/fraud/detect`, `/api/demographic/flow`, `/api/image/analyze`, `/api/image/geo-analyze`, `/api/radar/*`, `/api/price/intelligence`, `/api/price/trend`, `/api/library`, `/api/library/add`, `/api/library/scan`, `/api/tune/*`, `/api/iaao`, `/api/training/register` | **KEEP — active fallback** |
| `agent_chat.html` | 5,089 | `/agent` (named route) | `bridge_api.py:9347` | `/api/agent/chat` | **KEEP — named route in bridge_api.py** |
| `composite_valuation.html` | 35,895 | `/composite_valuation.html` | `tests/e2e/test_composite_form_smoke.py:20,258` | `/api/valuation/composite`, `/api/valuation/composite/schema` | **KEEP — E2E test targets this exact URL** |
| `image_d86c0c.jpg` | 520,021 | `/image_d86c0c.jpg` | `index.html:1183` (`src="image_d86c0c.jpg"`) | — | **KEEP — referenced by active index.html** |

---

## 3. Legacy Frontend Files — Candidate for `frontend/_legacy/`

These files are NOT served at `/` and have no named routes. They are reachable at `/<filename>` via the catch-all, but nothing in the active UI links to them. Moving them to `frontend/_legacy/` would change their URL from `/<file>` to `/_legacy/<file>` — safe only if confirmed that no external bookmarks or active links point to them.

| File | Size (bytes) | Endpoints called | Phase 20 Status | Notes | Safe to move? |
|---|---|---|---|---|---|
| `sovereign.html` | 91,195 | `/api/market-sweep`✴, `/api/bank-audit`✴, `/api/fund-valuation`✴, `/api/tax-pilot`✴, `/api/master-report`✴, `/api/report/generate`✴, `/api/valuation`, `/api/ingest`, `/api/price-map`, `/api/upload`, `/api/fraud/detect`, `/api/demographic/flow` | Stubs added (Phase 20) | Legacy sovereign UI v1; not served at `/` | **YES — after Gate B approval** |
| `sovereign_v2.html` | 79,208 | `/api/session/update`✴ | Stub added (Phase 20) | Sovereign v2 — not served at `/` | **YES — after Gate B approval** |
| `valuation.html` | 74,836 | `/api/valuation`, `/api/generate-report`❌, `/api/investment-report`❌ | `/api/generate-report` and `/api/investment-report` still missing | Early standalone valuation UI + Gemini; two endpoints absent | **YES — after Gate B approval** (Phase 21 follow-up: add stubs for the two missing endpoints) |

✴ = Phase 20 501 stub added  
❌ = Endpoint still absent; no stub added (Phase 21 item)

---

## 4. Preview / Design Files — Candidate for `frontend/_archive/`

Static HTML mockups and design previews. No active API calls. Not served by any named route. Reachable only via catch-all `/<filename>`.

| File | Size (bytes) | References | Notes | Safe to archive? |
|---|---|---|---|---|
| `badge_preview.html` | 1,822 | `styles.css` | Badge design preview — static | **YES — after Gate B approval** |
| `business_valuation_preview.html` | 3,931 | None | Business valuation wireframe | **YES — after Gate B approval** |
| `expert_dashboard_preview.html` | 10,156 | `styles.css` | Dashboard design preview | **YES — after Gate B approval** |
| `financing_request_preview.html` | 6,732 | None | Financing wireframe | **YES — after Gate B approval** |
| `home_pillars_preview.html` | 5,435 | None | Home pillars mockup | **YES — after Gate B approval** |
| `sovereign_ui_phase1.html` | 66,357 | None | UI design phase 1 mockup; no API calls | **YES — after Gate B approval** |
| `sovereign_ui_phase2.html` | 93,885 | None | UI design phase 2 mockup; no API calls | **YES — after Gate B approval** |

> **Note on `styles.css`**: If `badge_preview.html` and `expert_dashboard_preview.html` are moved to `_archive/`, `styles.css` should move with them (it is only referenced by those two files). Moving `styles.css` alone without moving the preview files that depend on it would leave broken `href="styles.css"` references.

---

## 5. Dev / Test Tooling — Keep in Place

| File | Size (bytes) | References | Notes | Action |
|---|---|---|---|---|
| `test_pipeline.html` | 907 | `data-engine/*.js` | Data pipeline test harness; no API calls; only references local JS in `data-engine/` | **KEEP — dev tooling** |
| `frontend/data-engine/ai-valuation.js` | 4,385 | `test_pipeline.html` | AI valuation engine | **KEEP** |
| `frontend/data-engine/data-cleaner.js` | 4,168 | `test_pipeline.html` | Data cleaner | **KEEP** |
| `frontend/data-engine/duplicate-detector.js` | 1,395 | `test_pipeline.html` | Duplicate detector | **KEEP** |
| `frontend/data-engine/market-db.js` | 1,341 | `test_pipeline.html` | Market DB | **KEEP** |
| `frontend/data-engine/scheduler.js` | 2,722 | `test_pipeline.html` | Scheduler | **KEEP** |
| `frontend/data-engine/scraper.js` | 2,901 | `test_pipeline.html` | Scraper | **KEEP** |

---

## 6. Standalone JS / CSS Files — Needs Phase Decision

| File | Size (bytes) | Endpoints | Referenced by HTML? | Phase | Status | Action |
|---|---|---|---|---|---|---|
| `localization.js` | 2,709 | `/api/language/strings`, `/api/language/set/` | **NO** — not `<script>`-tagged in any active HTML | Phase 23 | Documented in `PHASE_23_CLOSURE.md`, `R3_REVIEW_LOG.md:253`, `PROD_READINESS_CHECKLIST.md` | **HOLD — Phase 23 i18n file; do not delete. Inclusion in index.html is a Phase 23 deliverable.** |
| `style_rtl.css` | 1,081 | None | **NO** — not `<link>`-tagged in any active HTML | Phase 23 | Documented in `PHASE_23_CLOSURE.md` | **HOLD — Phase 23 RTL layout CSS; do not delete. Inclusion in index.html is a Phase 23 deliverable.** |
| `script.js` | 71,756 | `/api/tags` | **NO** — not referenced by any HTML file in `frontend/` | Unknown | No reference found in any HTML, docs, or tests | **ORPHAN — Investigate `/api/tags` endpoint; if confirmed orphan after research, safe to move to `_archive/` with Gate B approval.** |
| `styles.css` | 40,002 | None | `badge_preview.html`, `expert_dashboard_preview.html` only | — | Not referenced by `index.html` or any served page | **ARCHIVE-CANDIDATE — Move together with preview files that depend on it.** |

---

## 7. Backup Snapshots — DO NOT DELETE, DO NOT MOVE

25 snapshot files that capture index.html state at various recovery/phase checkpoints. These are historical records — they must not be deleted, renamed, or moved.

| Pattern | Count | Must NOT delete |
|---|---|---|
| `index.before-*.html` | 24 | All 24 files |
| `index.broken.phase311.rollback-snapshot.html` | 1 | This file |

<details>
<summary>Full list (24 × index.before-* + 1 rollback)</summary>

```
index.before-cumulative-phase310-recovery.html      (160,317 bytes)
index.before-cumulative-pre311-recovery.html        (156,493 bytes)
index.before-ma-display-fix.html                    (218,425 bytes)
index.before-ma-restore.html                        (143,856 bytes)
index.before-phase311-prompt1-workspace-shell.html  (251,539 bytes)
index.before-phase311-prompt2-summary-cards.html    (253,489 bytes)
index.before-phase311-prompt3-action-bar.html       (258,384 bytes)
index.before-phase311-prompt4-tabs.html             (261,406 bytes)
index.before-phase311-prompt4a-tab-nav.html         (265,095 bytes)
index.before-phase311-prompt4b-tab-panels.html      (265,095 bytes)
index.before-phase311-prompt5-executive-summary.html(266,856 bytes)
index.before-phase311-prompt6-browser-polish.html   (276,556 bytes)
index.before-phase312-excel-wizard-recovery.html    (302,151 bytes)
index.before-phase312-prompt3-import-wizard.html    (278,719 bytes)
index.before-phase312-prompt4a-validation-panel.html(292,569 bytes)
index.before-phase312-prompt4b-fill-safety.html     (301,018 bytes)
index.before-phase312-prompt5b-model-cycle-fill.html(303,461 bytes)
index.before-phase313-prompt2-ux-text-polish.html   (304,777 bytes)
index.before-phase313-prompt2b-remove-duplicate-buttons.html (305,505 bytes)
index.before-phase313-prompt4-hardcoded-url-cleanup.html (306,718 bytes)
index.before-phase314-prompt4b-xlsx-export-enhancement.html (307,156 bytes)
index.before-pre311-asset-deep-recovery.html        (218,425 bytes)
index.before-pre311-delta-asset-recovery.html       (204,389 bytes)
index.before-pre311-delta-purpose-recovery.html     (208,016 bytes)
index.broken.phase311.rollback-snapshot.html        (156,392 bytes)  ← rollback snapshot
```

</details>

---

## 8. Summary — File Count

| Category | Count | Recommended Action |
|---|---|---|
| Active / served (DO NOT MOVE) | 5 | Keep in `frontend/` root |
| Legacy frontend | 3 | Move to `frontend/_legacy/` after Gate B |
| Preview / design | 7 | Move to `frontend/_archive/` after Gate B |
| Dev / test tooling | 7 | Keep in place (1 HTML + 6 data-engine/*.js) |
| Standalone JS/CSS — Hold (Phase 23) | 2 | Keep until Phase 23 wires them |
| Standalone JS/CSS — Orphan/archive candidate | 2 | Investigate then archive with Gate B |
| Backup snapshots (DO NOT DELETE) | 25 | Keep as-is |
| **Total** | **51** | |

---

## 9. Phase 21 — Open Items

These items require decisions or further work before Gate B can be approved:

1. **`/api/generate-report` missing** (called by `valuation.html:1619`) — Phase 21 to add stub.
2. **`/api/investment-report` missing** (called by `valuation.html:1644`) — Phase 21 to add stub.
3. **`script.js` orphan investigation** — check git history and `/api/tags` endpoint to confirm true orphan before archiving.
4. **Phase 23 completion check** — `localization.js` and `style_rtl.css` are documented deliverables of Phase 23. Confirm Phase 23 closure status before deciding their fate.
5. **Gate B approval required** before any files are moved to `_legacy/` or `_archive/` directories.
6. **Test suite baseline** (BEFORE any moves): 6,474 tests collected; all must pass after any structural change.

---

## 10. Cross-references

- `docs/LEGACY_COMPATIBILITY.md` — Phase 20 legacy endpoint audit
- `core_engine/PHASE_21_CLOSURE.md` — pre-existing closure doc for `/agent` → `agent_chat.html`
- `core_engine/PHASE_23_CLOSURE.md` — Phase 23 i18n/RTL deliverables (localization.js, style_rtl.css)
- `core_engine/tests/e2e/test_composite_form_smoke.py` — E2E test for composite_valuation.html
- `bridge_api.py:674-690` — frontend file serving logic
