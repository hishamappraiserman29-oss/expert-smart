# Tax Appraisal Phase 2 — Release Checklist
**Version:** Phase 2.7 (QA Audit & Release Freeze)
**Date:** 2026-05-02
**Status:** RELEASE FREEZE

---

## A. Backend API Tests — `/api/valuation` (tax_assessment purpose)

### A1. Baseline Response Contract
- [ ] `POST /api/valuation` with `valuation_purpose:"tax_assessment"` returns `200`
- [ ] Response contains `tax_assessment` block at top level
- [ ] `tax_assessment.market_value` matches `market_value` in root response
- [ ] `tax_assessment.annual_tax` is non-negative
- [ ] `tax_assessment.taxable_amount >= 0` (never negative)
- [ ] `tax_assessment.legal_basis` is non-empty string

### A2. Phase 2.2 Enrichment Fields
- [ ] `assessed_value` present and equals `market_value * composite_factor`
- [ ] `assessment_ratio` present (default 1.0)
- [ ] `taxable_value` equals `taxable_amount` (invariant)
- [ ] `effective_tax_rate` equals `annual_tax / market_value` (within floating-point tolerance)
- [ ] `tax_due` equals `annual_tax` (invariant)
- [ ] `tax_sheet_summary` object present with `market_value`, `assessed_value`, `annual_rental_value`, `assessed_rental_value`, `exemption_amount`, `taxable_value`, `tax_rate`, `tax_due`

### A3. Phase 2.4 — Policy Profiles (one request per class)

#### residential (default)
- [ ] `property_class:"residential"` → `annual_rental_pct ≈ 0.03`, `tax_rate ≈ 0.10`, `exemption_threshold = 24000`
- [ ] `policy_profile` = `"residential"` in response
- [ ] `policy_notes` contains "24,000 ج.م"
- [ ] `note` field in `tax_assessment` is NOT the old hardcoded string — must be policy-aware

#### commercial
- [ ] `property_class:"commercial"` → `annual_rental_pct ≈ 0.08`, `exemption_threshold = 0`
- [ ] `policy_notes` references commercial units

#### industrial
- [ ] `property_class:"industrial"` → `annual_rental_pct ≈ 0.06`, `exemption_threshold = 0`

#### agricultural
- [ ] `property_class:"agricultural"` → `annual_rental_pct ≈ 0.02`, `tax_rate ≈ 0.05`, `exemption_threshold = 48000`
- [ ] `annual_tax` is lower than equivalent residential property (lower rate + higher exemption)

#### administrative
- [ ] `property_class:"administrative"` → `annual_rental_pct ≈ 0.08`, `exemption_threshold = 0`

### A4. Manual Overrides vs Policy Defaults
- [ ] Sending `annual_rental_pct:0.05` with `property_class:"residential"` → `manual_overrides` contains entry for `annual_rental_pct`
- [ ] `policy_defaults` shows the policy default value (`0.03`) separately from the used value (`0.05`)
- [ ] Policy-driven fields NOT overridden show empty/absent `manual_overrides` entry for that field

### A5. High Exemption (zero tax)
- [ ] `property_class:"residential"`, small `area` → `taxable_amount = 0`, `annual_tax = 0`
- [ ] `effective_tax_rate = 0` when `annual_tax = 0`
- [ ] `appeal_narrative` references zero-tax outcome

### A6. Phase 2.6 — Tax Appeal Package
- [ ] `tax_appeal_package` present in `tax_assessment` block for all 5 property classes
- [ ] `appeal_strength` is one of: `"low"`, `"medium"`, `"high"`
- [ ] `appeal_reasons` is a list; each entry has `code`, `severity`, `message`
- [ ] `evidence_checklist` has 6 items; each has `item`, `required` (bool), `purpose`
- [ ] `operator_recommendation` is non-empty string
- [ ] `appeal_summary` is non-empty string
- [ ] `formal_appeal_narrative` is non-empty string
- [ ] `disclaimer` is non-empty string
- [ ] `HIGH_EFFECTIVE_TAX_RATE` signal triggered when `effective_tax_rate > 0.01`
- [ ] `MANUAL_ASSUMPTIONS_USED` signal triggered when `manual_overrides` is non-empty
- [ ] `EXEMPTION_ELIMINATES_TAX` signal triggered when `taxable_value == 0` or `annual_tax == 0`
- [ ] `LEGAL_BASIS_REVIEW_REQUIRED` signal triggered when `legal_basis` is generic or empty
- [ ] `GENERIC_POLICY_PROFILE` signal triggered when `property_class` absent from payload

### A7. Error Cases
- [ ] Missing `location` → returns error or defaults gracefully (no 500)
- [ ] `area: -50` → handled without crash
- [ ] Non-numeric `annual_rental_pct` → falls back to policy default, no 500
- [ ] `tax_rate: 1.5` (> 1) → accepted as user override, manual_overrides recorded

### Smoke Test Commands
```powershell
# Residential — default profile
$body = '{"location":"التجمع الخامس","property_type":"شقة سكنية","area":200,"valuation_purpose":"tax_assessment","property_class":"residential"}'
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/valuation" -Method Post -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 6

# Agricultural — low rate + high exemption
$body2 = '{"location":"الفيوم","property_type":"أرض زراعية","area":5000,"valuation_purpose":"tax_assessment","property_class":"agricultural"}'
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/valuation" -Method Post -ContentType "application/json" -Body $body2 | ConvertTo-Json -Depth 6

# Manual override
$body3 = '{"location":"التجمع الخامس","property_type":"شقة سكنية","area":200,"valuation_purpose":"tax_assessment","property_class":"residential","annual_rental_pct":0.05}'
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/valuation" -Method Post -ContentType "application/json" -Body $body3 | ConvertTo-Json -Depth 6
```

---

## B. Frontend Tests — Tax Assessment Panel

### B1. Panel Visibility & Inputs
- [ ] Tax Assessment section visible when `valuation_purpose = "tax_assessment"` selected
- [ ] `property_class` select present with 5 options: residential, commercial, industrial, agricultural, administrative
- [ ] Selecting a class auto-fills `annual_rental_pct`, `tax_rate`, `exemption_threshold` immediately
- [ ] `governorate_factor`, `construction_factor`, `location_factor`, `assessment_ratio` are NOT auto-filled (property-specific)
- [ ] Manually typed values in auto-filled fields are preserved on subsequent run (not overwritten by select)

### B2. Payload Verification (DevTools Network)
- [ ] Request payload to `/api/valuation` includes `property_class` key
- [ ] Request does NOT call `/api/mass-appraisal/*` for single-property tax flow

### B3. Result Rendering
- [ ] Tax table renders after successful run
- [ ] Policy profile section visible: فئة العقار, وصف السياسة
- [ ] Manual overrides row visible when override was sent
- [ ] `tax_appeal_package` section renders: "حزمة الاعتراض الضريبي"
- [ ] Appeal strength pill colored: green (low), amber (medium), red (high)
- [ ] `appeal_reasons` list renders with severity codes
- [ ] Evidence checklist table renders (6 rows)
- [ ] `formal_appeal_narrative` text visible
- [ ] `disclaimer` rendered in red-border warning box

### B4. Auto-fill Accuracy
| Class | annual_rental_pct | tax_rate | exemption_threshold |
|-------|-------------------|----------|---------------------|
| residential | 0.03 | 0.10 | 24000 |
| commercial | 0.08 | 0.10 | 0 |
| industrial | 0.06 | 0.10 | 0 |
| agricultural | 0.02 | 0.05 | 48000 |
| administrative | 0.08 | 0.10 | 0 |

---

## C. Word Report Tests

### C1. Policy Profile Section (Phase 2.4)
- [ ] Word report for `tax_assessment` contains "ملف السياسة الضريبية" heading
- [ ] `فئة العقار` row shows correct property class (not always "residential")
- [ ] `وصف السياسة` row shows non-empty policy description
- [ ] Policy defaults table rendered when present
- [ ] Manual overrides disclosure rendered when `manual_overrides` is non-empty

### C2. Tax Appeal Package Section (Phase 2.6)
- [ ] Word report contains "حزمة الاعتراض الضريبي (استشارية)" heading
- [ ] `قوة الاعتراض` row present with Arabic label (منخفضة/متوسطة/مرتفعة)
- [ ] `ملخص الاعتراض` and `توصية المقيّم` rows present
- [ ] Appeal reasons rendered as key-value pairs (code → message)
- [ ] Evidence checklist section "قائمة المستندات المطلوبة" present with 6 rows
- [ ] `السرد الرسمي` block present
- [ ] `disclaimer` disclosure block present
- [ ] **Fix A verified**: appeal section is NOT empty (was broken before Phase 2.7)

### C3. Audit Notes Section (Phase 2.3)
- [ ] "ملاحظات التدقيق" disclosure present
- [ ] When `audit_notes` computed by backend (non-empty), the Word report uses computed notes (not hardcoded fallback)
- [ ] **Fix B verified**: `audit_notes` from nested `tax_assessment` sub-dict flows correctly into Word report

### C4. Note Field (Phase 2.7 Fix C)
- [ ] `note` field in API response is NOT the hardcoded residential string for non-residential classes
- [ ] Agricultural: note references `قانون 196/2008 — أراضي زراعية` and agricultural policy text
- [ ] Commercial: note references `قانون 196/2008 — وحدات تجارية`

---

## D. Excel Tests

### D1. Single-Property Excel (Phase 2.1B — NOT IMPLEMENTED)
> **Known Gap**: The per-property Excel report (`write_to_excel_template()`) uses a fixed `.xlsm` template and does not add a dynamic Tax Assessment sheet. This is a Phase 3 target.
- [ ] Excel report still downloads without error for `tax_assessment` purpose
- [ ] No crash or 500 error when `tax_assessment` data is present

### D2. Mass Appraisal XLSX — Tax Assessment Sheet
- [ ] Tax Assessment sheet present in mass XLSX when rows include `tax_assessment` purpose
- [ ] Sheet has 21 columns: row_id, market_value, annual_rental_value, tax_base, taxable_amount, tax_rate, annual_tax, governorate_factor, construction_factor, location_factor, exemption_threshold, legal_basis, assessed_value, exemption_amount, taxable_value, effective_tax_rate, tax_due, policy_profile, property_class, appeal_strength, operator_recommendation
- [ ] `policy_profile` and `property_class` columns populated correctly per row
- [ ] `appeal_strength` and `operator_recommendation` populated from `tax_appeal_package`
- [ ] Rows with non-tax purposes do not appear in Tax Assessment sheet (or appear with empty tax columns)

---

## E. Mass Appraisal Regression

- [ ] Mass appraisal batch with `valuation_purpose:"tax_assessment"` rows → each row has `tax_assessment` block
- [ ] `tax_assessment` block per row has all Phase 2.2/2.4/2.6 fields
- [ ] `tax_appeal_package` present in each row's `tax_assessment`
- [ ] `HBU`, `REIT`, `EIA` rows in same batch → `status:"skipped"` (not affected by tax changes)
- [ ] `fair_market_value` rows in same batch → no `tax_assessment` block injected
- [ ] Batch summary `successful_rows` count is correct
- [ ] Mass XLSX Tax Assessment sheet only contains rows where purpose is `tax_assessment`

### Smoke Test
```powershell
$batchBody = '{"rows":[{"row_id":"T-001","location":"التجمع الخامس","property_type":"شقة سكنية","area":200,"valuation_purpose":"tax_assessment","property_class":"residential"},{"row_id":"T-002","location":"الفيوم","property_type":"أرض زراعية","area":5000,"valuation_purpose":"tax_assessment","property_class":"agricultural"},{"row_id":"F-001","location":"مدينة نصر","property_type":"شقة سكنية","area":150,"valuation_purpose":"fair_market_value"}]}'
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/mass-appraisal/run" -Method Post -ContentType "application/json" -Body $batchBody | ConvertTo-Json -Depth 6
```

---

## F. Non-Tax Regression Tests

> These ensure Phase 2 changes did not break other valuation flows.

- [ ] `fair_market_value` → correct `market_value`, no `tax_assessment` block
- [ ] `investment_value` → correct result
- [ ] `usufruct` → `usufruct.pv_factor` present
- [ ] `uncertainty_valuation` → `uncertainty_range.spread_pct` present
- [ ] `hbu_analysis` → HBU block returned (NOT skipped in single-property mode)
- [ ] `reit_valuation` → REIT block returned
- [ ] `eia_assessment` → EIA block returned
- [ ] AVM: when `price_per_meter` provided near AVM data, `avm.applied` field present
- [ ] Word report for `fair_market_value` has no tax section injected
- [ ] Excel download still works for all non-tax purposes
- [ ] `/api/advisor/health` → `{status:"ok"}`

### Non-Tax Smoke Test
```powershell
$singleBody = '{"location":"التجمع الخامس","property_type":"شقة سكنية","area":200,"valuation_purpose":"fair_market_value"}'
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/valuation" -Method Post -ContentType "application/json" -Body $singleBody
```

---

## G. Known Limitations (Accepted for Phase 2)

| Limitation | Decision |
|------------|----------|
| Phase 2.1B: No dynamic Tax sheet in per-property `.xlsm` report | Accepted — template-based Excel; Phase 3 target |
| Phase 2.5: `tax_scenarios` and `tax_sensitivity_summary` not implemented | Accepted — not in Phase 2 scope; Phase 3 target |
| `tax_scenarios` absence: Signal 2 (`HIGH_TAX_SENSITIVITY`) in appeal package is a graceful no-op | Accepted — signal simply absent from `appeal_reasons` when Phase 2.5 data unavailable |
| Policy profiles are advisory defaults, not binding regulatory rates | By design — assessor must confirm current local tariff |
| Manual overrides not validated against legal maximums | Accepted — assessor responsibility |
| `tax_appeal_package` is advisory only; not a formal legal appeal document | By design — disclaimer rendered in all outputs |
| No per-class tax brackets (progressive rates) | Phase 3 target — current law uses flat 10% |
| No penalty/interest calculation for late tax | Out of scope for Phase 2 |
| Session JSON not encrypted | Acceptable for local dev; encrypt before production |

---

## H. Release Sign-Off

| Check | Result | Notes |
|-------|--------|-------|
| `py_compile core_engine/bridge_api.py` | ✅ PASS | |
| `py_compile core_engine/purpose_detail_sections.py` | ✅ PASS | |
| `py_compile core_engine/mass_appraisal_excel.py` | ✅ PASS | |
| AST check bridge_api.py | ✅ PASS | Phase 2.7 |
| AST check purpose_detail_sections.py | ✅ PASS | Phase 2.7 |
| Fix A: Word report sees tax_appeal_package | ✅ PASS | Phase 2.7 — pre-compute before report write |
| Fix B: audit_notes/policy_profile/manual_overrides via _tsub | ✅ PASS | Phase 2.7 |
| Fix C: `note` field is policy-aware | ✅ PASS | Phase 2.7 |
| Numeric invariants: tax_due == annual_tax | Pending manual verification | See Section A2 |
| Numeric invariants: taxable_value == taxable_amount | Pending manual verification | See Section A2 |
| All 5 policy profiles return correct defaults | Pending manual verification | See Section A3 |
| Word report appeal section non-empty | Pending manual verification | See Section C2 |
| Mass XLSX Tax Assessment sheet 21 columns | Pending manual verification | See Section D2 |
| Docker build | Pending manual run | |
| Manual end-to-end flow | Pending | See Sections B, C |

---

## I. Phase 3 Backlog (NOT in Phase 2 scope)

- Dynamic Tax Assessment sheet in per-property `.xlsm` Excel report (Phase 2.1B)
- `tax_scenarios` (rate sensitivity table) and `tax_sensitivity_summary` (Phase 2.5)
- Progressive tax brackets for future law changes
- Penalty and interest computation for late or deferred tax payment
- Regulatory submission export (ETA format)
- Multi-year tax projection table
- Comparison of assessed value vs. self-declared value
- Scheduled batch tax reassessment runs
- Integration with cadastral / land registry data for automatic area validation
