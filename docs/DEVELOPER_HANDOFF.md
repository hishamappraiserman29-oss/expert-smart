# Developer Handoff — EXPERT_SMART

> **Audience:** A developer picking up the project for the first time.
> **Expected time-to-productivity:** ~1 day.
> **Companion docs:** [`EXPERT_SMART_CLOSURE_REPORT.md`](EXPERT_SMART_CLOSURE_REPORT.md) (the "what") + this doc (the "how").

---

## 1. Mental Model

EXPERT_SMART is an Egyptian real estate valuation system. A user fills a form, the
system generates an **Excel** valuation report (always) and optionally a **PDF**, runs
**validation** to catch bad data, **persists** the report in a local SQLite DB, and
exposes a **history panel** in the frontend.

The codebase follows **Shared Core Architecture**:

```
                bridge_api.py  (Flask HTTP layer, ~11,600 lines)
                      |
            report_pipeline.py  (thin facade)
                      |
   +------------------+------------------+
   |                  |                  |
validation/        pdf/ + excel/        db/
```

All three engines share `report_profiles.py` (the 3 profiles) + `report_theme.py`
(Midnight Gold design system: Navy + Gold palette, Cairo typography).

---

## 2. First-Day Setup

```bash
git clone <repo-url> expert_smart && cd expert_smart
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r core_engine/requirements.txt
python -m pytest core_engine/tests/ -q | tail -3
# Expected: all tests passed

# Start the server
python core_engine/bridge_api.py
# Visit http://127.0.0.1:5000
```

If anything fails — stop, read the error, verify Python >= 3.10, resolve before
going further. Do not add workarounds.

---

## 3. Repository Tour (in this order)

| # | Path | Learn |
|---|---|---|
| 1 | `docs/EXPERT_SMART_CLOSURE_REPORT.md` | The big picture + resolved issues |
| 2 | `docs/api/openapi.yaml` | The 4 core HTTP endpoints |
| 3 | `core_engine/reports/report_profiles.py` | The 3 profiles + REGISTRY |
| 4 | `core_engine/reports/report_theme.py` | Colors / fonts / style helpers |
| 5 | `core_engine/reports/sheets/main_report_sheet.py` | A representative sheet module |
| 6 | `core_engine/reports/pdf/pdf_engine.py` | PDF entry point |
| 7 | `core_engine/reports/validation/validation_engine.py` | Validation entry |
| 8 | `core_engine/reports/db/db_engine.py` | DB public API |
| 9 | `core_engine/reports/report_pipeline.py` | How bridge_api wires it all |
| 10 | `core_engine/bridge_api.py` — `/api/valuation` + `/api/reports` | Full request flow |
| 11 | `frontend/index.html` — `es-reports-panel` section | Frontend history panel |

---

## 4. Common Tasks (Cheatsheet)

### Add a new sheet

1. Create `core_engine/reports/sheets/new_sheet.py` with
   `apply_new_sheet(ws, data, *, profile_key="legacy")`.
2. Export from `core_engine/reports/sheets/__init__.py`.
3. Call from `core_engine/reports/excel_builder.py`.
4. Write tests in `core_engine/tests/test_new_sheet.py`.

### Add a validation rule

Reuse primitives in `core_engine/reports/validation/rules.py`.
Add to the appropriate rule set in `validation_engine.py`.
Rules return `ValidationIssue` with `severity`, `code`, `message_ar`, `message_en`.

### Add a new report profile

Add a frozen dataclass to `REGISTRY` in `report_profiles.py`.
Profile key **must be `snake_case`**; premium variants conventionally end in `_template`.
The key `professional` is reserved — use `professional_template` (canonical).

### Add a new API endpoint

1. Study the existing `/api/reports` route for the Flask pattern.
2. Guard risky imports with `try/except ImportError` (see bridge_api.py lines 56-89).
3. Add the endpoint behind an opt-in flag if it changes existing behaviour.
4. Write tests in `core_engine/tests/test_bridge_api_<feature>.py`.
5. Update `docs/api/openapi.yaml`.

### Add a DB migration

1. Bump `SCHEMA_VERSION` in `core_engine/reports/db/schema.py`.
2. Add `_migrate_to_vN(conn)` in `migrations.py` — **forward-only**.
3. Test idempotency (run twice = identical result).
4. Register: `_MIGRATIONS[N] = _migrate_to_vN`.

---

## 5. Conventions We Don't Skip

| # | Convention | Why |
|---|---|---|
| 1 | Atomic commits — one logical change per commit | Selective rollback, readable history |
| 2 | Tests green before merge | Zero-regression policy |
| 3 | `git diff --cached --stat` before every commit | Catch unintended staged files |
| 4 | Profile key = `professional_template`, never `professional` | Canonical key; wrong key = `PROFILE_UNKNOWN` ERROR |
| 5 | All Arabic text via `prepare_text()` in PDF engine | Correct RTL bidi shaping |
| 6 | DB tests use `tmp_path` fixture only | Never write to the default `reports.db` in tests |
| 7 | Move legacy code to `_archive/` rather than deleting | Cheap recovery insurance |
| 8 | Bilingual validation messages always | `message_ar` + `message_en` on every `ValidationIssue` |
| 9 | No hardcoded secrets | Use env vars; `DigitalSignatureManager` requires `GOVERNMENT_SIGNATURE_SECRET` |

---

## 6. Branches

| Branch | Purpose | Rules |
|---|---|---|
| `main` | Production-ready, tagged `v1.0.0` | Gate on tests + review |
| `wip/r3-subsystems-checkpoint` | 24 subsystems pending review | **Frozen — read-only, never push, never delete** |
| `feature/r3-*` | Per-subsystem review branches | Branch from main; merge after Gate report |
| `feature/<name>` | Your feature work | Branch from main; merge via PR |

---

## 7. Things You Will Be Tempted To Do (Don't)

- **"Let me refactor while I'm here"** — file a separate task with its own Gate.
- **"This test is flaky, I'll skip it"** — fix the flake or halt until understood.
- **"I'll fix the broken test in the next commit"** — commits must be atomic + green.
- **"Frontend has no automated tests so anything goes"** — run the manual checklist or add Playwright.
- **"I'll use `or True` to bypass validation for now"** — use an opt-in flag; never inline.
- **"I'll just `git push --force`"** — blocked. Ask the lead.

---

## 8. Key Numbers (v1.0.0 Baseline)

From `docs/PERF_BASELINE_v1.0.0.md` — Windows 11 / Python 3.13:

| Scenario | Median (s) | Peak mem (MB) |
|---|---|---|
| `validate_report` | 0.0003 | ~0 |
| `generate_pdf` | 2.44 | 8.4 |
| `save_report` | 0.0057 | ~0 |
| `get_report` | 0.0019 | ~0 |
| full pipeline | 2.36 | 8.4 |

Regression threshold: **2× median** triggers investigation.
PDF is the bottleneck — Arabic shaping is the primary cost.

---

## 9. Where to Find Things

| Question | Where to look |
|---|---|
| Why does this endpoint exist? | `git log -S "route_name" --oneline` |
| What changed in v1.0.0? | `CHANGELOG.md` |
| Is this endpoint documented? | `docs/api/openapi.yaml` |
| Why is security guarded like this? | `docs/SECURITY_PLAN_REPORTS_API.md` |
| Is this production-ready? | `docs/PROD_READINESS_CHECKLIST.md` |
| What subsystems are still WIP? | `docs/R3_REVIEW_LOG.md` |
| How fast should this be? | `docs/PERF_BASELINE_v1.0.0.md` |

---

## 10. Ready Checklist

You are ready when you can:

- [ ] Run the full test suite locally and get all green
- [ ] Start the server and open the frontend
- [ ] Identify which file handles each engine (validation / pdf / db)
- [ ] Add a one-line change to a sheet module, write a test, see it pass
- [ ] Explain "Shared Core Architecture" to a colleague in 2 minutes

Welcome aboard.
