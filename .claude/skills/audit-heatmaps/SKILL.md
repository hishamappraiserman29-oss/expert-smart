# Skill: Geographic Intelligence & IAAO Audit Constraints

## Purpose
Enforces rigid tax auditing capabilities according to international real estate appraisal organizations and guarantees robust, un-trackable mapping endpoints.

## Context
Target integration points: `core_engine/spatial_audit_engine.py` and Excel formatting rules.

## Execution Rules
1. **Tax Audit Compliance (المسار الضريبي)**: Always invoke `calculate_iaao_metrics` when encountering tax properties. Validate Uniformity (`COD`), Central Tendencies (`ASR`), and Price Differentials (`PRD`). The `Traffic Light String (Green, Yellow, Red)` MUST be passed to the Excel Dashboard.
2. **Sovereign Heatmaps (GIS Logic)**: Under absolute Zero-Trust conditions, do NOT rely on external Javascript interactive maps like Google Maps APIs or Mapbox if you are printing the report. Render maps *server-side* natively via OpenStreetMap (`staticmap`) showcasing Price Zones around the main property coordinate.
3. **Structural Simplification (تبسيط الهيكل)**: The `Land Adjustments Matrix` (مصفوفة تعديلات الأرض) is strictly FORBIDDEN from having its own independent Excel sheet tab. All land modifiers, shape geometry adjustments, and location corner multipliers must be nested exclusively within the `Cost Approach` (طريقة التكلفة) computational sheet rows.
