# Skill: Dual Comparison & Trends Modeling

## Purpose
Govern how the system compares historical reports against current input data accurately, producing annual growth rates and business insights strictly without exceeding maximum report lengths (merges into main dashboard).

## Context
- **Dependencies**: `smart_library_scraper.py` (uses deduplication hash).
- **Target File**: `core_engine/dual_comparison.py`

## Execution Rules
1. **Time-Series Constraint**: Ensure no exact duplicates are compared using `content_hash`. Delete any corrupted matched data beforehand.
2. **Dashboard Native Reports**: Never generate external comparison pages (to respect the strictly enforced 20-page limit). Inject the comparison outcome into the `[اتجاهات السوق - Market Trends]` dashboard pane.
3. **M&A DCF Feeding**: If the evaluation loop detects `purpose == 'ma'`, immediately forward the parsed `Annual Growth Rate (e.g. 12%)` to the core `DCF (Discounted Cash Flow)` calculation to refine investment synergies.
4. **Reshaper Compliance**: Validate that text meant for the AI Insights chart uses `arabic_reshaper` + `bidi` before drawing lines in `matplotlib`.
