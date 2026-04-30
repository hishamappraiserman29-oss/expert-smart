# Skill: Market Intelligence Processing

## Purpose
Ensure that data processed from the `Market_Intelligence` sheet is realistic, cleaned, and applicable to local valuation standards by accounting for the negotiation margin.

## Context
- **Target Data**: Any real estate market intelligence data, comparable sales, or asking prices.
- **Process**: Data Cleaning and Verification.

## Execution Rules
1. **Outlier Filtering**: Before using any dataset for market comparison, scan and filter out significant outliers (e.g., suspiciously low prices or extreme luxury premiums not representative of the subject property).
2. **Negotiation Factor (معامل التفاوض)**: When reading *asking prices* (أسعار العرض), ALWAYS apply a negotiation discount factor (typically between 5% to 15%, or specific to the regional trend) to estimate the actual transaction value.
   - Example: `Transaction Value = Asking Price * 0.90`
3. **Transparency**: When generating outputs or reports based on this data, explicitly state that a negotiation factor was applied to asking prices to reflect realistic fair market value.
