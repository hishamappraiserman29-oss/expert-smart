# ADR-0002: Profile Registry as Frozen Dataclass

- **Status:** Accepted
- **Date:** 2026-04-18

## Context

Once Shared Core Architecture (ADR-0001) was adopted, the three profiles needed a
single canonical description: which sections are enabled, which theme variant applies,
what the display name is, and whether the profile is a premium tier. Several
representations were possible.

An early prototype used a plain Python dict keyed by profile name. This worked but
had no type safety — callers could silently access non-existent keys, and the dict
could be mutated at runtime by any import that held a reference.

## Options Considered

### Option A — Plain dict
```python
REGISTRY = {
    "legacy": {"has_income": False, "has_pdf": False, ...},
}
```
- Pros: Simple, no imports needed.
- Cons: No IDE completion. Mutable — any module can add or remove keys at runtime.
  No documentation attached to fields.

### Option B — Frozen dataclass (chosen)
```python
@dataclass(frozen=True)
class ReportProfile:
    key: str
    display_name: str
    features: ReportFeatures
    ...
REGISTRY: dict[str, ReportProfile] = { ... }
```
- Pros: Immutable after construction. Full IDE type completion. Field docstrings.
  `features` is itself a frozen dataclass — nested immutability.
- Cons: Slightly more boilerplate than a dict.

### Option C — Enum
Use `Enum` where each member is a profile. Cleaner at call sites (`Profile.LEGACY`).
- Cons: Enums do not support rich attribute access on members without property
  gymnastics. Adding new profiles requires editing the enum body, which is less
  ergonomic than adding a REGISTRY entry.

## Decision

Adopt Option B. Both `ReportProfile` and `ReportFeatures` are `@dataclass(frozen=True)`.
The `REGISTRY` dict is module-level and populated at import time — effectively a
compile-time constant. Any attempt to mutate a profile at runtime raises `FrozenInstanceError`.

## Consequences

**Positive:**
- Impossible to accidentally mutate profile configuration mid-request.
- Full type safety: calling code gets IDE completion on `.features.has_income_approach`,
  not a dict key string.
- Easy to introspect: `list(REGISTRY.keys())` gives all valid profile keys.
- New profiles are one `ReportProfile(...)` call in the registry — zero structural change.

**Negative / Tradeoffs:**
- `frozen=True` means no post-init mutation, so any computed field must be derived
  at construction time.
- Adding a new field to `ReportFeatures` requires updating every existing profile
  instantiation — a global change, though easy with IDE refactor.
