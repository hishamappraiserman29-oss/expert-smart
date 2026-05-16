# Production Readiness Checklist — EXPERT_SMART

Run this checklist **before** any production deployment. Each item is binary (✅ ready / ❌ blocker).

**Last reviewed:** [TBD]
**Reviewer:** [name]
**Target environment:** [staging / production]

---

## 1. Security 🔒

- [ ] Authentication on `/api/reports*` + `/api/valuation` (Followup #7)
- [ ] Authorization — `owner_user_id` filter enforced per tenant
- [ ] Rate limiting (per-user, per-IP)
- [ ] HTTPS only (TLS at ingress — no plain HTTP in production)
- [ ] Secrets in env vars (no hardcoded keys — `GOVERNMENT_SIGNATURE_SECRET` etc.)
- [ ] CORS — only known origins whitelisted
- [ ] Security headers (HSTS / X-Content-Type-Options / Referrer-Policy / X-Frame-Options)
- [ ] `pip-audit` / `safety check` clean on pinned dependencies
- [ ] `gitleaks` scan — no leaked secrets in git history
- [ ] Audit log populated for all sensitive endpoints

## 2. Reliability 🛡️

- [ ] All 669+ tests pass in CI (not just locally)
- [ ] Smoke test passes in staging-like environment
- [ ] Error responses for 4xx / 5xx contain no stack traces or internal paths
- [ ] Graceful shutdown (SIGTERM handled — in-flight requests complete)
- [ ] Health endpoint (`/api/advisor/health`) returns 200 when ready
- [ ] Readiness probe distinct from liveness probe in k8s manifests
- [ ] Container restart policy = `always` / `on-failure`

## 3. Observability 📊

- [ ] Structured logging (JSON, not plain text)
- [ ] Correlation IDs propagated through request lifecycle
- [ ] Error tracking (Sentry or equivalent) configured
- [ ] Metrics — request count, latency p50/p95/p99, error rate
- [ ] Performance baseline captured (Followup #12)
- [ ] Regression alerts set (p95 > 2× baseline triggers alert)
- [ ] Disk usage alerts for `reports.db` (SQLite grows unbounded without retention)

## 4. Data 💾

- [ ] DB backup scheduled (cron) — `reports.db` daily minimum
- [ ] Backup retention ≥ 30 days
- [ ] Restore drill verified (can restore from backup and pass smoke test)
- [ ] JSON export procedure documented
- [ ] Data retention policy documented and enforced
- [ ] PII / sensitive fields identified (appraiser name, property address, valuations)
- [ ] No personal data emitted in application logs

## 5. Deployment 🚀

- [ ] Docker image builds reproducibly (pinned dep versions in `requirements.txt`)
- [ ] k8s manifests reviewed (resource `limits`, liveness/readiness probes, replica count)
- [ ] Rollback procedure documented and tested (previous image tag available)
- [ ] Zero-downtime deploy strategy (rolling update, not recreate)
- [ ] DB migrations are forward-only and idempotent
- [ ] Feature flags in place for any risky runtime changes
- [ ] Staging environment mirrors production config (env vars, secrets, volumes)

## 6. Documentation 📖

- [ ] `README.md` links to architecture, API reference, and handoff docs
- [ ] `CHANGELOG.md` reflects the deployed version
- [ ] `docs/EXPERT_SMART_CLOSURE_REPORT.md` current
- [ ] `docs/api/openapi.yaml` matches all deployed endpoints
- [ ] `docs/CI_ACTIVATION_NOTES.md` — CI secrets and activation steps complete
- [ ] `docs/adr/` directory exists for Architectural Decision Records
- [ ] On-call runbook exists and is linked from README

## 7. Frontend 🖥️

- [ ] Manual smoke test checklist executed (history panel, PDF download, filters)
- [ ] Playwright / E2E smoke test passes (Followup #11)
- [ ] No browser console errors on production page load
- [ ] Page degrades gracefully when backend returns 500 (no-auto-load policy active)
- [ ] Cross-browser tested (Chrome / Firefox / Safari)
- [ ] Arabic RTL layout renders correctly (Cairo font, `style_rtl.css` loaded)

## 8. Operational 🛠️

- [ ] On-call rotation assigned with escalation path
- [ ] Runbook covers top 5 failure modes:
  1. DB lock / disk full (`reports.db` or `market_radar.db`)
  2. PDF generation OOM (large report, Arabic reshaping)
  3. Auth provider down (once auth is implemented)
  4. Rate-limit storms from a single tenant
  5. Frontend cannot reach backend (CORS, firewall, API down)
- [ ] Communication plan for outages (who notifies whom, within what SLA)
- [ ] SLA / SLO defined (uptime target, response time target)

## 9. Legal / Compliance ⚖️

- [ ] `LICENSE` file present in repo
- [ ] Third-party licenses audited (Cairo OFL-1.1, fpdf2 LGPL, openpyxl MIT, ...)
- [ ] Privacy policy referenced or linked from UI
- [ ] Terms of service in place if applicable
- [ ] IVS / USPAP / Egyptian EGVS appraiser compliance reviewed by domain expert (د. عبد الرؤوف)

## 10. Sign-off

- [ ] Tech lead sign-off
- [ ] Security review sign-off
- [ ] Domain expert sign-off on valuation accuracy
- [ ] Operations sign-off on deployment and monitoring setup
- [ ] Date of go-live: _____________
- [ ] Rollback decision-maker: _____________

---

## Quick Status Summary

| Section | Items | Score | Blockers |
|---|---|---|---|
| 1. Security | 10 | __/10 | __ |
| 2. Reliability | 7 | __/7 | __ |
| 3. Observability | 7 | __/7 | __ |
| 4. Data | 7 | __/7 | __ |
| 5. Deployment | 7 | __/7 | __ |
| 6. Documentation | 7 | __/7 | __ |
| 7. Frontend | 6 | __/6 | __ |
| 8. Operational | 4 | __/4 | __ |
| 9. Legal | 5 | __/5 | __ |
| 10. Sign-off | 6 | __/6 | __ |
| **TOTAL** | **66** | **__/66** | __ |

**Minimum threshold for production: 60+/66 with zero critical blockers.**
Sections 1 (Security), 2 (Reliability), and 4 (Data) must each be ≥ 80%.

---

## Notes

- This checklist is **living**. Add items as you learn from incidents or audits.
- Items marked ❌ should generate follow-up tasks with an owner and deadline.
- Re-run the checklist for any significant environment change (new region,
  k8s upgrade, major dependency bump, auth system change).
- Current known open items (as of 2026-05-16):
  - Section 1: No authentication on report endpoints yet (Followup #7)
  - Section 7: No automated E2E tests yet (Followup #11)
  - Section 3: No performance baseline yet (Followup #12)
