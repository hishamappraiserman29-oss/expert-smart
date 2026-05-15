# EXPERT_SMART

Egyptian real estate valuation system — PropTech platform for valuation reports,
Central Bank auditing (Basel III/IV), and tax mass appraisal.

## 📐 Architecture

This project follows a **Shared Core Architecture** with three isolated engines
(PDF / Validation / Database) wired into a single Bridge API.

For full architectural details, design decisions, and how to extend the system, see:

- [`docs/EXPERT_SMART_CLOSURE_REPORT.md`](docs/EXPERT_SMART_CLOSURE_REPORT.md) — Complete architecture reference (Arabic + English)

**Quick reference:**
- 7 phases of refactoring (Profiles → Theme → Sheets → 3 Engines)
- 1606 automated tests, zero regression policy
- Bridge API integration with opt-in validation / persistence / PDF / history
- Frontend history panel with PDF download

## Testing

```bash
python -m pytest core_engine/tests/ -v
```

## License

[Specify license]
