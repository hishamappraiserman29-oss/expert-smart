# Skill: Sovereign Validation & V26 Excel Styling

## Purpose
Embeds the precise `Black & Gold (v26)` aesthetics into all Excel macro reports (`.xlsm`) and internal Matplotlib traces without disrupting backend integrity and core processing logic.

## Context
Target integration points: `bridge_api.py` and `market_intelligence.py`

## Execution Rules
1. **Excel Export Hook**: 
   - Never override inline formatting inside `bridge_api.py` generating loops iteratively.
   - Simply pass the `wb` (OpenPyXL Workbook) through `apply_sovereign_dark_theme(wb)` from `excel_dark_theme.py` strictly before `wb.save()`.
2. **Print Constraints Protection**: 
   - Always ensure `ws.page_setup.blackAndWhite = True` to trick Excel into dropping `1A1A1A` background carbon fill upon physical print, converting them back to raw white pages (Ink Preservation Sovereign Standard).
3. **Matplotlib Alignments**: 
   - Use `fig.patch.set_facecolor("#030712")` (Midnight dark).
   - Use `ax1.plot(..., color="#D4AF37", marker='o', markersize=8, markerfacecolor="#EBB63C")` to fulfill the "Glowing Gold Marker" requested for Market Trends traces.
4. **Validation Stamp I1 Code**:
   - `✅`: MUST map to `#10B981`.
   - `❌`: MUST map to `#EF4444`. 
   These must be injected conditionally during validation routing.
