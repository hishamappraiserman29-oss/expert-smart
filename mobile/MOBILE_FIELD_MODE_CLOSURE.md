# Mobile / Field Mode Closure

## Status: COMPLETE

## Deliverables

| Task | File | Description |
|------|------|-------------|
| 1 | `mobile/app/OfflineStorage.ts` | SQLite wrapper: valuations + sync_queue tables, CRUD, stats |
| 2 | `mobile/app/SyncEngine.ts` | Conflict detection & resolution (completeness scoring) |
| 3 | `mobile/app/FieldTools.ts` | Camera (photo/gallery), GPS (watch/one-shot), Voice notes |
| 4 | `mobile/api/FieldApiClient.ts` | Axios client with offline fallback + auto-sync on reconnect |
| 5 | `mobile/app/FieldValuation.tsx` | React Native screen: form, photos, voice, sync status, stats |
| Mocks | `mobile/__mocks__/` | Full mock suite for SQLite, Geolocation, NetInfo, Voice, Camera, Axios, UUID |
| Tests | `mobile/tests/FieldMode.test.ts` | **44/44 tests pass** |

## Test Results

```
44 passed in 3.2s
OfflineStorage  A01–A14  14/14
SyncEngine      B01–B08   8/8
FieldTools      C01–C08   8/8
FieldApiClient  D01–D08   8/8
Integration     E01–E06   6/6
```

## Architecture

```
Field Appraiser
     │
     ▼
FieldValuation.tsx  ──── UI layer (React Native)
     │
     ├── OfflineStorage.ts  ─── SQLite (valuations + sync_queue)
     ├── FieldTools.ts      ─── Camera / GPS / Voice
     ├── SyncEngine.ts      ─── Conflict resolution
     └── FieldApiClient.ts  ─── Online/offline API gateway
                                    │
                          online    │    offline
                         ──────────┤────────────
                        API call   │  local save
                                   ▼
                            Expert Smart API
                            /api/valuation/*
```

## Key Design Decisions

- **Offline-first**: `OfflineStorage.saveValuation` always writes locally first; sync is asynchronous
- **Sync queue**: Every write adds a `(create/update/delete, table, data)` entry; `SyncEngine.startSync` drains the queue when online
- **Conflict resolution**: Compare `updatedAt` timestamps; use `calculateCompleteness` (6-field score) to pick winner when equal
- **Auto-sync**: `FieldApiClient.setupNetworkMonitoring` detects transition from offline → online and triggers `syncEngine.startSync`
- **Completeness scoring**: `∑ filled_fields / 6` — fields: location, areaSqm, propertyType, comparables, primaryValue, methodology
- **Windows-safe regex**: `/is` flag (ES2018 dotAll) replaced with `[\s\S]+?` for TypeScript target compatibility
- **`retries` default**: Explicitly included in INSERT with value `0` (not relying on DB DEFAULT)
- **GPS metadata on photos**: `takePhoto` calls `getCurrentLocation` and attaches coordinates to each Photo object

## Native Dependencies (mocked for tests)

| Package | Mock | Behavior |
|---------|------|----------|
| `react-native-sqlite-storage` | In-memory table store | Full CREATE/INSERT/UPDATE/SELECT/COUNT |
| `@react-native-community/geolocation` | Returns Cairo coords (30.04, 31.23) | Configurable error path |
| `@react-native-community/netinfo` | Starts online | `_setOnline()` test helper |
| `@react-native-voice/voice` | Returns transcription string | start/stop/destroy |
| `react-native-image-picker` | `jest.fn()` | Configurable response per test |
| `axios` | Mock instance | Per-call `mockResolvedValueOnce` |
| `uuid` | Sequential `mock-uuid-N` | Deterministic IDs |
