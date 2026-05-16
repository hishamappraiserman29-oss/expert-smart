# Performance Baseline — v1.0.0

**Captured:** 2026-05-16 10:46:50 UTC
**Iterations:** 5
**Profile:** `professional_template`
**Platform:** `Windows-11-10.0.26100-SP0`
**Python:** `3.13.13`

## Numbers

| Scenario | n | min (s) | median (s) | mean (s) | max (s) | peak mem (MB) median |
|---|---|---|---|---|---|---|
| validate_report | 5 | 0.0003 | 0.0003 | 0.0003 | 0.0003 | 0.0 |
| generate_pdf | 5 | 2.365 | 2.4422 | 2.6058 | 3.295 | 8.42 |
| save_report | 5 | 0.0052 | 0.0057 | 0.0098 | 0.0268 | 0.01 |
| get_report | 5 | 0.0013 | 0.0019 | 0.0018 | 0.0023 | 0.02 |
| full pipeline (validate+pdf+save) | 5 | 2.3261 | 2.3632 | 2.3654 | 2.4369 | 8.41 |

## Regression Policy

Any commit whose **median time exceeds 2× the median** above for any scenario
should trigger investigation before merging.
Re-run this script after the change and compare.

## How to re-run

```bash
python tools/perf_baseline.py --iterations 5 --profile professional_template
```

Overwrite this file only when deliberately updating the baseline (e.g. after
a performance improvement or a major engine refactor). Commit the updated file
alongside the change so the history is traceable.