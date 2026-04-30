# Expert_Smart — API Reference

Practical reference for the 7 endpoints validated in the stabilization phase.

**Base URL (local dev):** `http://127.0.0.1:5000`
**Server:** Flask + Waitress on port 5000.
**Restart rule:** Waitress does NOT auto-reload. After any change to `core_engine/*.py`, stop the server (Ctrl+C) and re-run `python bridge_api.py` from `core_engine/`.

---

## 1. `GET /api/advisor/health`

**Purpose:** Health smoke test. Confirms the server is up and the RAG model has finished loading.

**Method:** GET
**Path:** `/api/advisor/health`
**Body:** none

### Key response fields
- `status` — `"ok"` when reachable.
- `rag_ready` — `true` when the embedding model finished its background load.
- `message` — Arabic string for UI display.

### Example
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/advisor/health" -Method Get
```

### Common failure cases
- `Unable to connect` → server not running.
- `404` → server is running but stale (route not registered) — restart.
- Timeout > 5s on first call → RAG warmup; wait and retry.

---

## 2. `GET /api/price-index`

**Purpose:** Real-estate price index across regions, computed via 4 methodologies (CMA / AVM / RPPI / Stratification) on data in `core_engine/data/market_feed.json`.

**Method:** GET (or POST with optional filters in body)
**Path:** `/api/price-index`
**Body:** none for full index. Optional filters via query string:
- `?region=<substring>` — filter regions whose name contains this string
- `?property_type=<substring>` — filter by property type
- `?base_period=YYYY-MM` — override base period

### Key response fields
- `status` — `"success"` or `"empty"`.
- `summary.n_records` — total records analyzed (≥ 250 after `bootstrap_price_data.py`).
- `summary.n_regions` — distinct regions found.
- `summary.avg_yoy_pct` — average composite YoY across regions.
- `summary.highest_region`, `summary.highest_yoy_pct` — top growth region.
- `summary.lowest_region`, `summary.lowest_yoy_pct` — slowest region.
- `regions[]` — per-region object with: `region, n_records, current_ppm, cma_yoy_pct, avm_yoy_pct, rppi_yoy_pct, strat_yoy_pct, composite_yoy_pct, alert`.
- `methodology_notes` — Arabic description of the 4 methodologies.

### Example
```powershell
$res = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/price-index" -Method Get
$res.summary
$res.regions | Select-Object -First 5 region, composite_yoy_pct, alert | Format-Table
```

### Common failure cases
- `status = "empty"` or `n_records = 0` → market_feed.json empty. Run `python bootstrap_price_data.py --count 250`.
- `regions = []` → filter applied with no matches.
- `avg_yoy_pct` outside reasonable range (>50% or <-10%) → corrupted records in feed.

---

## 3. `POST /api/valuation`

**Purpose:** Main property-valuation endpoint. Routes through:
- `advanced_valuation()` general path (3 approaches: market / cost / income).
- AVM dispatcher (when purpose is FMV / bank_financing / tax_assessment / acquisition AND data sufficient).
- Specialized asset valuator (when property_type matches أصول معنوية / ملكيات جزئية / استثمارات تحت الإنشاء / مناجم).
- Specialized purpose delegate (when valuation_purpose triggers HBU / REIT / EIA — see those endpoints).

**Method:** POST
**Path:** `/api/valuation`
**Content-Type:** `application/json`

### Minimum request payload
```json
{
  "location":          "التجمع الخامس",
  "area":              200,
  "property_type":     "شقة سكنية",
  "valuation_purpose": "fair_market_value",
  "description":       "شقة سكنية في التجمع الخامس...",
  "price_per_meter":   35000,        // optional — AVM fills if missing & eligible
  "date":              "25/04/2026"  // optional
}
```

### Supported `valuation_purpose` values (14)
`fair_market_value, acquisition, bank_financing, judicial_liquidation, insurance, investment_analysis, rental_arbitration, tax_assessment, financial_reporting, usufruct, uncertainty_valuation, highest_and_best_use, investment_funds, environmental_impact_assessment`

### Supported `property_type` values (14)
`شقة سكنية, عمارة سكنية, تجاري, أرض فضاء, مصنع, أرض زراعية, فندق, محل تجاري, مستشفى, مدرسة, أصول معنوية, ملكيات جزئية, مناجم, استثمارات تحت الإنشاء`

### Key response fields
- `status` — `"success"` or `"error"`.
- `market_value` — final reconciled value in EGP.
- `excel_url` — download link for the full Excel report (.xlsm or .xlsx).
- `purpose_report_url` — download link for the purpose-specific Word report.
- `valuation_purpose` — echo of input.
- `avm` — object with `applied, avm_ppm, confidence, spread_pct, verdict, n_records` (only present for AVM-eligible purposes).

### Example (PowerShell)
```powershell
$body = @{
    location          = "التجمع الخامس"
    area              = 200
    property_type     = "شقة سكنية"
    valuation_purpose = "fair_market_value"
    price_per_meter   = 35000
    description       = "شقة سكنية في التجمع الخامس بمساحة 200 متر"
    date              = "25/04/2026"
} | ConvertTo-Json

$res = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/valuation" `
                          -Method Post -ContentType "application/json" -Body $body
$res.market_value
$res.excel_url
$res.avm
```

### Common failure cases
- `status = "error"` with Arabic message → read `result.message`.
- `excel_url = $null` → Excel writer failed (template issue).
- `avm.applied = false` with reason "بيانات غير كافية" → market_feed has < 10 records matching this region+type.
- `500 Internal Server Error` → exception in pipeline; check server window for traceback.

---

## 4. `POST /api/hbu/analyze`

**Purpose:** Highest-and-Best-Use analysis. Applies 4 sequential tests (legal / physical / financial / maximally productive) and returns the optimal use among alternatives.

**Method:** POST
**Path:** `/api/hbu/analyze`
**Content-Type:** `application/json`

### Minimum request payload
```json
{
  "property": {
    "location":       "الشيخ زايد",
    "area":           5000,
    "current_zoning": "مختلط"
  },
  "discount_rate": 0.12,
  "alternative_uses": [
    {
      "use_name":                  "برج سكني",
      "is_legally_permissible":    true,
      "is_physically_possible":    true,
      "land_cost":                 25000000,
      "construction_cost":         60000000,
      "construction_period_years": 2,
      "holding_period_years":      8,
      "annual_revenue":            18000000,
      "annual_opex":               4000000,
      "exit_value":                110000000
    }
    // ...add at least one more alternative
  ]
}
```

### Key response fields
- `status` — `"success"` or `"error"`.
- `result.recommended_use` — winning Arabic name.
- `result.recommended_npv` — winning NPV in EGP.
- `result.recommendation_note` — Arabic explanation.
- `result.comparison_table[]` — per-alternative: `use_name, legally_permissible, physically_possible, financially_feasible, maximally_productive, npv, irr_pct, payback_years, verdict`.
- `result.scenarios_evaluated[]` — full per-scenario detail including `cashflows`.
- `result.standards_note` — IVS / USPAP reference.

### Example
```powershell
# (Body matches the JSON above, converted via ConvertTo-Json -Depth 5)
$res = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/hbu/analyze" `
                          -Method Post -ContentType "application/json" -Body $body
$res.result.recommended_use
$res.result.recommended_npv
$res.result.comparison_table | Format-Table use_name, npv, irr_pct, verdict
```

### Common failure cases
- `recommended_use = $null` → all scenarios failed at least one of tests 1–3 (legal/physical/financial).
- `npv = "NaN"` → invalid `discount_rate` (e.g. ≤ -1).
- `400` with "alternative_uses فارغة" → array missing or didn't serialize (raise `-Depth` in ConvertTo-Json).
- `irr_pct = $null` → cashflows monotonic; IRR not computable.

---

## 5. `POST /api/reit/nav`

**Purpose:** Portfolio-level NAV per Unit for a Real-Estate Investment Trust under IFRS 13 / IOSCO.

**Method:** POST
**Path:** `/api/reit/nav`
**Content-Type:** `application/json`

### Minimum request payload
```json
{
  "fund_name":             "صندوق اختبار",
  "units_outstanding":     100000,
  "cash_and_equiv":        5000000,
  "receivables":           1200000,
  "loans":                 35000000,
  "accrued_expenses":      800000,
  "distributions_payable": 2000000,
  "properties": [
    {
      "asset_name":    "برج التجاريين",
      "property_type": "تجاري",
      "location":      "القاهرة الجديدة",
      "fair_value":    50000000,
      "noi":           4000000,
      "cap_rate":      0.08,
      "area":          3500
    }
    // ...
  ]
}
```

Each property may use either `fair_value` (pre-supplied) OR a full set of operational inputs (`market_value, annual_rent, vacancy_rate, operating_expenses, area, property_type`) — in the latter case `run_fund_valuation` is called to derive FV.

### Key response fields
- `status` — `"success"`.
- `result.fund_name` — echo.
- `result.gross_asset_value` — GAV in EGP.
- `result.total_liabilities` — sum of all liability fields.
- `result.nav` — Net Asset Value (GAV − liabilities).
- `result.nav_per_unit` — NAV / units_outstanding.
- `result.weighted_cap_rate_pct` — portfolio-weighted cap rate.
- `result.ltv_pct` — loans / real-estate-FV.
- `result.gearing_ratio_pct` — total liabilities / GAV.
- `result.health_score`, `result.health_label` — 0–100 + Arabic label.
- `result.assets[]` — per-asset breakdown.
- `excel_url` — only present if `export_excel: true` in payload.

### Example
```powershell
$res = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/reit/nav" `
                          -Method Post -ContentType "application/json" -Body $body
$res.result.gross_asset_value
$res.result.nav
$res.result.nav_per_unit
```

### Common failure cases
- `400` with "units_outstanding يجب أن يكون موجباً" → 0 or missing.
- `nav` negative → liabilities > assets (mathematically valid).
- `excel_url` empty → didn't pass `export_excel: true`.

---

## 6. `POST /api/eia/assess`

**Purpose:** Environmental Impact Assessment with 10-section report. Computes Impact Matrix (Severity × Probability), classifies the project (A / B / C), derives Environmental Risk Factor (ERF), and links to investment value.

**Method:** POST
**Path:** `/api/eia/assess`
**Content-Type:** `application/json`

### Minimum request payload
```json
{
  "project": {
    "activity_type":   "مصنع كيماويات",
    "location":        "العاشر من رمضان",
    "gis_lat":         30.29,
    "gis_lon":         31.74,
    "area_m2":         25000
  },
  "site_analysis": {
    "distance_to_residential_m":    850,
    "distance_to_water_m":          320,
    "distance_to_infrastructure_m": 1100
  },
  "baseline":  { "air_quality": "متوسطة", "noise_level_db": 62 },
  "emissions": {
    "air_emissions_tons_yr":       180,
    "industrial_wastewater_m3_yr": 65000,
    "ordinary_waste_tons_yr":      220,
    "hazardous_waste_tons_yr":     85
  },
  "impact_matrix": [
    { "activity": "تشغيل المراجل",  "element": "الهواء", "severity": "high",   "duration": "long",  "probability": "high"   },
    { "activity": "صرف صناعي",       "element": "المياه", "severity": "high",   "duration": "long",  "probability": "medium" },
    { "activity": "النفايات الخطرة", "element": "الصحة",  "severity": "high",   "duration": "long",  "probability": "high"   }
  ],
  "iso_14001_compliant": true,
  "market_value":        250000000
}
```

`severity`, `duration`, `probability` accept `low/medium/high` or `منخفض/متوسط/عالي` or `1/2/3`.

### Key response fields
- `status` — `"success"`.
- `category` — `"A"` / `"B"` / `"C"`.
- `erf` — Environmental Risk Factor (1.00 / 0.95 / 0.85).
- `result.classification.category_label` — Arabic full label.
- `result.classification.composite_score` — final 1–9 score.
- `result.investment_linkage.market_value` — input echo.
- `result.investment_linkage.adjusted_market_value` — `market_value × erf`.
- `result.investment_linkage.value_at_risk` — `market_value − adjusted_market_value`.
- `result.impact_assessment.avg_impact_score`, `n_critical`.
- `word_url` — Word report download link.
- `excel_url` — Excel report download link.

### Example
```powershell
$res = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/eia/assess" `
                          -Method Post -ContentType "application/json" -Body $body
$res.category                                  # e.g. "C"
$res.erf                                       # e.g. 0.85
$res.result.investment_linkage.value_at_risk   # e.g. 37500000
$res.word_url
```

### Common failure cases
- `400` with "impact_matrix فارغة" → array missing.
- `category = "A"` despite high severities → check `_classify` thresholds in `eia_engine.py`.
- `word_url = $null` → python-docx unavailable.

---

## 7. `POST /api/image/analyze`

**Purpose:** Auto-tag a property image (Arabic categories) and extract GPS from EXIF.

**Method:** POST
**Path:** `/api/image/analyze`
**Content-Type:** `multipart/form-data`

### Request
- Field name: `file`
- Allowed extensions: `.jpg, .jpeg, .png, .gif, .webp, .bmp, .tiff, .tif, .jfif`

### Key response fields
- `status` — `"success"`.
- `tag` — Arabic tag from the catalog (واجهة / تشطيب داخلي / مطبخ / حمام / غرفة نوم / صالة / مسبح / حديقة / موقف سيارات / إطلالة / عداد مياه/كهرباء / هيكل إنشائي / أخرى).
- `report_order` — int 0–12 (display order).
- `has_gps` — boolean.
- `gps_lat`, `gps_lng` — present only when `has_gps == true` (decimal degrees).
- `saved_as` — saved filename.

### Example (PowerShell — needs version 6+ for `-Form`)
```powershell
$file = "C:\path\to\photo.jpg"
$form = @{ file = Get-Item $file }
$res = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/image/analyze" -Method Post -Form $form
$res.tag
$res.has_gps
```

### Example (curl, works on PowerShell 5.1)
```powershell
curl.exe -F "file=@C:\path\to\photo.jpg" http://127.0.0.1:5000/api/image/analyze
```

### Common failure cases
- `400` "لم يتم إرسال صورة" → field name not `file`, or PowerShell 5.1 `-Form` unsupported (use `curl.exe`).
- `415` "صيغة صورة غير مدعومة" → extension outside allowed set.
- `405 Method Not Allowed` → server is running with stale route map; restart `python bridge_api.py`.
- `has_gps = false` for a known GPS-tagged photo → uncertain (parser needs verification — see DEFERRED_ITEMS.md).

---

## Notes

- **AVM is wired only for 4 purposes:** `fair_market_value, bank_financing, tax_assessment, acquisition`. Other purposes route through general path or specialized delegates.
- **Specialized asset valuators (4):** `أصول معنوية → MPEEM`, `ملكيات جزئية → Pro-rata × DLOC × DLOM`, `استثمارات تحت الإنشاء → Cost-to-date + Risk`, `مناجم → DCF on reserves`.
- **Word/Excel reports** are saved under `core_engine/outputs/` and served via `/api/download/<filename>`.
- **Rate limit:** none in dev. Production deployment should add throttling.

Sources used while writing this document:
- `core_engine/bridge_api.py` (route declarations, lines 5328, 6611, 6472, 6527, 6568, 6474)
- `core_engine/eia_engine.py` (payload schema)
- `core_engine/hbu_analysis_engine.py` (4-test framework)
- `core_engine/reit_nav_engine.py` (NAV formulas)
- `core_engine/avm_dispatcher.py` (eligibility + thresholds)
- `core_engine/price_index_engine.py` (4 methodologies)
- Runtime tests executed during the stabilization phase (see TESTED_BASELINES.md).
