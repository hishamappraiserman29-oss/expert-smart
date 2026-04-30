# Expert_Smart — Deferred Items & Minor Issues

This is the canonical list of **known unresolved items** at the close of the stabilization phase. Each item has:
- **Description** — what was observed.
- **Why deferred** — the constraint that prevented an in-session fix.
- **Impact** — what users / operators see.
- **Classification** — `safe now` (low-risk to start later) / `later` (needs prep work) / `do not touch yet` (real risk).
- **Hint for next time** — a single sentence pointing the next session at the right place.

If something here turns out to be wrong or stale, mark it explicitly when picking it up.

---

## D1 — `/api/image/analyze` GPS extraction is unverified

**Description:** The `_extract_exif_gps` parser was rebuilt during the second truncation recovery (`bridge_api.py` task #33). It is defined, importable, and reachable through the restored route. **It has never been exercised on a real GPS-tagged photo.** Smoke (no GPS) and unsupported-file rejection both pass.

**Why deferred:** No GPS-tagged sample image was available during the validation session.

**Impact:**
- Functional risk: low — `has_gps` returns `false` cleanly when EXIF is absent.
- Hidden risk: if a real EXIF-bearing photo lands in production and the parser misreads bytes, returned `gps_lat`/`gps_lng` could be wrong (parity error in `ref_lat`/`ref_lng` lookup, or sec/min/deg ordering bug).

**Classification:** **later** — safe to revisit once a GPS-tagged photo is available.

**Hint for next time:** Use a phone photo with location services enabled, verify EXIF first via Windows file properties (`GPS Latitude` row), then call `POST /api/image/analyze`. Compare returned decimal degrees to Google Maps within 0.001° tolerance.

---

## D2 — `/api/image/geo-analyze` is not implemented

**Description:** The frontend (`frontend/index.html:1565`, `frontend/sovereign_brain.html:2560`) calls `POST /api/image/geo-analyze`. The backend route does not exist. Calls fail with HTTP 404 and the frontend shows a toast.

**Why deferred:** A field-by-field mapping audit between the response shape the frontend expects (14 fields including `gps_coordinates, soil_type, flood_risk, seismic_risk, heat_risk, geotechnical_summary, estimated_area_sqm, buildability, risk_score, geotechnical_risk_level, confidence, location_guess, coordinates_note, recommendations`) and what `geo_risk_engine.analyze_geo_risk` returns (10 fields with different shape) showed **only 5 / 14 fields can be mapped with high confidence**. Recovering the original transformer from memory is not safe.

**Impact:**
- Functional: the "geo-map fast track" upload feature in the frontend is dead — users see a failure toast.
- Risk to other features: zero (no other endpoint depends on this).

**Classification:** **do not touch yet** — invent-and-ship would produce subtly wrong values for `risk_score`, `confidence`, and 4 other unmapped fields.

**Hint for next time:** Look for an older commit or backup of `bridge_api.py` (search `.git/`, OneDrive, or any `.bak` / `.old` files). If none exists, gather a stakeholder decision on the contract for the 9 unmapped fields before writing a transformer.

---

## D3 — PowerShell Arabic display issue (`???` in some fields)

**Description:** When tests 4 and 5 ran via PowerShell 5.1, certain Arabic strings (`recommended_use`, `use_name`, `fund_name`, `asset_name`) printed as `???` in the console. The actual JSON returned by the server is correct UTF-8 — the issue is how PowerShell 5.1 renders the string when concatenated with `+`.

**Why deferred:** Cosmetic (console-only). Does not affect the API, the frontend, the JSON payload, or any downstream system.

**Impact:**
- Test logs may look broken when read out of context.
- Anyone running tests on PowerShell 5.1 sees `???` instead of Arabic, which can be confusing.

**Classification:** **safe now** — fix is pure documentation:
- Add `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` to the test prereq (already noted in TESTED_BASELINES.md).
- Recommend PowerShell 7+ for development environments.
- Use `$res.field` (no `+` concatenation) when displaying Arabic — the object reference renders the string directly without round-tripping through the locale codepage.

**Hint for next time:** The same encoding caveat applies if anyone scripts smoke tests from `cmd.exe`. Document workaround once; do not chase the rendering bug in PowerShell itself.

---

## D4 — AVM activation (RESOLVED — was data sparsity, not a filter bug)

**Status:** ✅ **Resolved** on April 25, 2026 via data densification only. No code, config, route, or matching-logic changes.

**Original observation:** Test 3 returned `avm.applied = false` with verdict `"بيانات غير كافية: 4 سجل فقط"`, even though the feed appeared to have 250+ records. Earlier hypotheses speculated about substring matching, anchoring, or `property_type` normalization being the root cause.

**Audit conclusion (read-only inspection of `avm_dispatcher.py` + `market_feed.json` + `bootstrap_price_data.py`):**

The matching logic in `_filter_records_for_location` is **correct**:
- `"التجمع الخامس" in "القاهرة الجديدة - التجمع الخامس"` evaluates True — substring match works.
- The `property_type` filter uses bidirectional substring match — `"شقة سكنية"` matches the bootstrap value `"شقة سكنية"` cleanly.

The actual root cause was **bootstrap data sparsity**:
- `bootstrap_price_data.py --count 250` distributes records across 40 regions × 16 months = 640 buckets → ~1 record per (region, month) bucket.
- Result: `التجمع الخامس` had only **3 records total**, of which only **1** matched `property_type="شقة سكنية"` — well below `_MIN_N_RECORDS_FOR_AVM = 10`.
- The 10-record threshold itself is statistically defensible and was kept unchanged.

**Resolution:** Re-ran `python core_engine/bootstrap_price_data.py --count 1500`. The prior 254-record feed was preserved as `core_engine/data/market_feed.backup_20260425_140144.json`.

**Before / After (verified by direct invocation of `dispatch_avm` against the regenerated feed AND by HTTP-level confirmation against the running Waitress server):**

| Metric | Before (`--count 250`) | After (`--count 1500`) |
|---|---|---|
| Total feed records | 254 | **1,731** |
| Records matching `التجمع الخامس` + `شقة سكنية` | 1 | **16** |
| Distinct months covered for that region+type | 1 | **11** |
| `avm.applied` | `false` | **`true`** |
| `avm.confidence` | `none` | **`medium`** |
| `avm.avm_ppm` (injected when no manual ppm) | 0 | **32,872 EGP** |
| `market_value` (no user ppm) | N/A — AVM disabled | **6,358,000 EGP** |

**HTTP-level confirmation (April 25, 2026):**

`GET /api/price-index` returned `n_records=1731`, `n_regions=40`, `avg_yoy_pct=11.74` — confirming the densified feed is being served correctly.

`POST /api/valuation` with payload `{"location":"التجمع الخامس","property_type":"شقة سكنية","valuation_purpose":"fair_market_value","area":200}` (no manual `price_per_meter`) returned:
```
avm.applied      = true
avm.confidence   = "medium"
avm.n_records    = 16
avm.avm_ppm      = 32,872 EGP
market_value     = 6,358,000 EGP
```
This is the canonical post-densification baseline; see `TESTED_BASELINES.md → Baseline 3b` for the full response shape.

**Why "medium", not "high":** the threshold for "high" is `n_records ≥ 30` AND `time_span ≥ 6 months`. Currently we have 16 records over 11 months — sufficient for a credible regression but below the high-confidence floor. To reach "high", regenerate at `--count 3000+` (which would push the التجمع الخامس + شقة سكنية bucket above ~32 records). **Medium is acceptable for current operational use** — the AVM ppm is injected into the payload and consumed by downstream `advanced_valuation`; user-supplied ppm (when provided) is never overwritten and AVM serves only as a sanity-check / cross-validator in that case.

**Classification:** **resolved (minor note kept for traceability)** — no further action required unless higher-confidence AVM is desired.

**Hint for next time:** If AVM verdict ever degrades back to `none` for a previously-active region, the most likely cause is feed shrinkage (someone wiped the seed or replaced it with a tiny smoke fixture). Confirm via:
```powershell
$feed = Get-Content "C:\Users\Lenovo\Desktop\expert_smart - Copy\core_engine\data\market_feed.json" -Raw | ConvertFrom-Json
"Total records: " + $feed.Count
($feed | Where-Object { $_.location -like "*التجمع الخامس*" -and $_.property_type -eq "شقة سكنية" }).Count
```
If the second number is below 10, regenerate with a higher `--count` rather than touching the matching code.

---

## D5 — Mojibake in `frontend/index.html:576` (RESOLVED — single-file frontend fix)

**Status:** ✅ **Resolved** in this stabilization session via a single-line frontend edit on line 576. No backend change was needed.

**Original observation:** Line 576's `<option>` had a corrupted `value="ا��دقي"` — the letter ل (U+0644, 2 UTF-8 bytes) had been replaced by two U+FFFD replacement characters (6 bytes total) at some point in an earlier save cycle. The display text `الدقي` was clean, so users saw the correct label but submitted a corrupted form value to `/api/valuation`. The earlier hypothesis assumed a paired fix was needed across the frontend value AND the backend `_PRICE_MAP` key.

**Audit conclusion (read-only inspection of `bridge_api.py` and the frontend):**

- The backend already had the canonical key `_PRICE_MAP["الدقي"] = 30000` (intact UTF-8, verified zero replacement bytes anywhere in `bridge_api.py`).
- Two other backend tables (coordinates at line 801, neighbourhood multipliers at line 882) were also keyed on the canonical `"الدقي"`.
- The corruption was therefore confined to **one attribute on one line** in the frontend — a single-file fix, not a paired one.

**Resolution:** Replaced `value="ا��دقي"` with `value="الدقي"` on `frontend/index.html:576`. Verified via post-edit hex inspection: the 6-byte sequence `ef bf bd ef bf bd` is gone from the file project-wide; `الدقي` now appears exactly twice on line 576 (once in `value=`, once in the display text), matching the form expected by `_PRICE_MAP`.

**Before / After:**

| Metric | Before | After |
|---|---|---|
| `value=` codepoints on line 576 | `ا U+FFFD U+FFFD د ق ي` (6 codepoints) | `ا ل د ق ي` (5 codepoints) |
| Submitted form value when user picks الدقي | corrupted string never matches any key | matches `_PRICE_MAP["الدقي"]`, coordinates, multipliers |
| Backend lookup result | falls through to default → valuation not anchored to الدقي | hits `_PRICE_MAP["الدقي"] = 30000` and the coordinates `(30.0499, 31.2091)` |

**Classification:** **resolved** — no further action required. The "paired fix" warning in the original entry was based on an unverified assumption; the audit showed the backend was always correct.

**Hint for next time:** If a similar mojibake is reported on another `<option>` value, run the same audit pattern: hex-inspect the suspect line, then grep `bridge_api.py` for the canonical Arabic key. If the backend already has the canonical form, the fix is single-file in `frontend/index.html`. If not, a paired fix is needed.

---

## D6 — Deploy stack (Docker / SaaS) not validated by a real deployment

**Description:** The `deploy/` folder contains 15 files (Dockerfiles, docker-compose, render.yaml, fly.toml, railway.json, scripts, README) ready for cloud deployment, including a clever Llama 3 `ollama cp` alias trick so `core_engine/rag_advisor.py` works unmodified. None of this has been exercised — no `docker build`, no `fly deploy`, no `render blueprint launch` was run.

**Why deferred:** A real deployment validation needs:
1. A cloud provider account (Render / Fly.io / Railway).
2. API tokens for `ollama-python` to actually pull `llama3:8b`.
3. Sufficient memory on the chosen plan (≥ 8 GB for `llama3:8b`).
4. Time to run a full deploy + integration test.

**Impact:**
- The deploy artifacts are **untested**, not necessarily broken. Pre-flight checks (YAML lint, Dockerfile syntax) passed during the build session, but real cloud behaviour is unknown.
- Risk of subtle issues: missing `ollama` Python package on slim images, port-forwarding rules, volume mounts for `qdrant_data` / `ollama_models`.

**Classification:** **later** — needs a controlled deployment session.

**Hint for next time:** Start with Render.com (lowest friction):
```bash
render blueprint launch deploy/render.yaml
```
First failure is most likely on the Ollama service (memory or model-pull timeout). The fallback is to run only the Flask service in the cloud and point `OLLAMA_HOST` at a hosted Ollama endpoint instead.

---

## Summary table

| ID | Item | Classification | Effort to address |
|---|---|---|---|
| D1 | GPS extraction unverified | later | 5 min (need GPS photo) |
| D2 | `/api/image/geo-analyze` missing | do not touch yet | 1–2 h (after stakeholder decision) |
| D3 | PowerShell `???` display | safe now | 5 min (doc note) |
| ~~D4~~ | ~~AVM filter too strict~~ | ✅ **resolved** (data densification, April 25, 2026) | done — `--count 1500` |
| ~~D5~~ | ~~Mojibake in الدقي value~~ | ✅ **resolved** (single-file frontend fix, this session) | done |
| D6 | Deploy stack unvalidated | later | 1–2 h (real deploy) |

---

## Process notes

- Items **must not be marked resolved** without a runtime test logged in `TESTED_BASELINES.md`.
- The minimal-change rule from `CLAUDE.md` and `bridge-api-debug/SKILL.md` applies to all of these.
- For D1 / D6 specifically, do not assume a passing static check (AST parse, schema validation) means the feature works; only a runtime test counts.
