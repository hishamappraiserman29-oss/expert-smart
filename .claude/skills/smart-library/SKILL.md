# Skill: Smart Live Library (Scraper & Deduplication)

## Purpose
Periodic intelligent scanning of specialized global and regional real estate exchanges to keep the system training data state-of-the-art without manual intervention or data bloating.

## Context
- **Target File**: `core_engine/smart_library_scraper.py`
- **Execution**: Can be triggered by CRON (batch job).

## Execution Rules
1. **Selective Global Scraper (المسح الدوري الذكي)**: Only target high-authority valuation domains (Arabic and Global exchanges). Scan for newly published IVS/USPAP reports.
2. **Smart Deduplication (فلترة التكرار)**: Compare document contents (using semantic hashing or exact text deduplication). If a report is substantially identical to an existing one in the vector DB, discard the duplicate immediately to preserve storage and processing efficiency. Keep only the most advanced version.
3. **Automatic Binding (الربط الأوتوماتيكي)**: When a user selects a scraped report from the UI's Smart Library, automatically link it by setting the task intention `#ai-task` to "تدريب النموذج لعمل محاكاة على تقرير قديم". Do not prompt for this; make it seamless.
