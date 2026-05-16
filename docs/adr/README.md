# Architecture Decision Records (ADRs)

Each record documents a single significant architectural decision: the context,
the options considered, the chosen path, and the consequences.

## Format

```
# ADR-NNNN: <Title>
- **Status:** Accepted | Superseded | Deprecated
- **Date:** YYYY-MM-DD
- **Context:** What problem are we facing?
- **Options:** What did we consider?
- **Decision:** What did we choose? Why?
- **Consequences:** What follows from this decision (good and bad)?
```

## Index

| # | Title | Status |
|---|---|---|
| [0001](0001-shared-core-architecture.md) | Adopt Shared Core Architecture | Accepted |
| [0002](0002-profile-registry-frozen-dataclass.md) | Profile Registry as frozen dataclass | Accepted |
| [0003](0003-midnight-gold-design-system.md) | Midnight Gold + Cairo as visual identity | Accepted |
| [0004](0004-three-isolated-engines.md) | Three isolated engines (PDF / Validation / DB) | Accepted |
| [0005](0005-bridge-api-additive-only.md) | Bridge API integration is additive + opt-in only | Accepted |
| [0006](0006-sqlite-hybrid-schema.md) | SQLite with hybrid schema (indexed cols + JSON blob) | Accepted |
| [0007](0007-fpdf2-with-bundled-cairo.md) | fpdf2 with bundled Cairo TTF | Accepted |
| [0008](0008-bilingual-validation-messages.md) | Bilingual validation messages with stable codes | Accepted |
| [0009](0009-atomic-commits-with-gates.md) | Atomic commits with mandatory gates | Accepted |
| [0010](0010-r3-safety-checkpoint-on-wip.md) | R3 subsystems on WIP branch for safe review | Accepted |
| [0011](0011-deterministic-pdf-output.md) | Deterministic PDF output (fixed creation date) | Accepted |
| [0012](0012-professional-template-canonical-key.md) | `professional_template` is the canonical profile key | Accepted |
