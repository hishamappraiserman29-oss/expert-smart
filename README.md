# EXPERT_SMART

Egyptian real estate valuation system — PropTech platform for valuation reports,
Central Bank auditing (Basel III/IV), and tax mass appraisal.

## Release Status

**Latest:** `v1.1.0` — Conditional Release (2026-05-19)  
CI: ✅ passing · E2E: ✅ passing · Tests: 1858/1858 · Dry-run: GO  
See [`docs/FINAL_RELEASE_HANDOFF_v1.1.0.md`](docs/FINAL_RELEASE_HANDOFF_v1.1.0.md) and [`CHANGELOG.md`](CHANGELOG.md).

> **Note:** This is a CONDITIONAL release. Full Production GO is pending PH.3 Google service
> account key rotation (waiver: [`docs/PH3_KEY_ROTATION_WAIVER.md`](docs/PH3_KEY_ROTATION_WAIVER.md)).

## 📐 Architecture

This project follows a **Shared Core Architecture** with three isolated engines
(PDF / Validation / Database) wired into a single Bridge API.

For full architectural details, design decisions, and how to extend the system, see:

- [`docs/EXPERT_SMART_CLOSURE_REPORT.md`](docs/EXPERT_SMART_CLOSURE_REPORT.md) — Complete architecture reference (Arabic + English)

**Quick reference:**
- 7 phases of refactoring (Profiles → Theme → Sheets → 3 Engines)
- 1858 automated tests, zero regression policy
- Bridge API integration with opt-in validation / persistence / PDF / history
- Frontend history panel with PDF download

## Testing

```bash
python -m pytest core_engine/tests/ -v
```

## License

[Specify license]
