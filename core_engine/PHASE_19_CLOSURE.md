# Phase 19 Closure — Supervised Autonomy

**Date:** 2026-05-08  
**Status:** COMPLETE  
**Tests:** 12/12

---

## What Was Built

### `core_engine/agents/supervised_agent.py`

Three components that wrap the `ValuationPipelineOrchestrator` with human-in-the-loop controls:

#### ExecutionMode (str Enum)
| Mode | Behaviour |
|------|-----------|
| `AUTONOMOUS` | All actions auto-approved, no callback invoked |
| `SUPERVISED` | Routine actions auto-approved; risky actions (delete, restore, run_pipeline) require callback |
| `MANUAL` | Every action requires callback approval |
| `READONLY` | Write / valuate / pipeline actions blocked outright |

#### ActionType (str Enum)
`SCAN · READ_FILE · WRITE_FILE · DELETE_FILE · VALUATE · BACKUP · RESTORE · RUN_PIPELINE`

#### BackupManager
- Stores snapshots in `<base_dir>/_backups/<uuid>/`
- Each backup contains a `backup.json` metadata file
- `workspace.json` is never included in a backup
- API: `create_backup / restore_backup / list_backups / delete_backup`

#### SupervisedAgent
- `_gate(action_type, workspace_id, details)` — evaluates action against current mode, invokes approval callback for gated actions, always appends an `ActionRecord`
- `run_pipeline(workspace_id, primary_purpose, auto_backup)` — gates → optional pre-pipeline backup → `ValuationPipelineOrchestrator.run()` → logs result
- `create_backup / restore_backup` — wrappers with gate + log

---

## Test Coverage

| # | Test | Result |
|---|------|--------|
| 01 | ExecutionMode enum values | PASS |
| 02 | ActionType enum + frozenset membership | PASS |
| 03 | ActionRecord dataclass + to_dict | PASS |
| 04 | BackupManager.create_backup copies files, writes metadata | PASS |
| 05 | BackupManager.list_backups filters by workspace_id | PASS |
| 06 | BackupManager.restore_backup restores file content | PASS |
| 07 | BackupManager.delete_backup removes dir, False on missing | PASS |
| 08 | AUTONOMOUS mode auto-approves run_pipeline | PASS |
| 09 | READONLY mode raises PermissionError on run_pipeline | PASS |
| 10 | SUPERVISED mode: non-risky auto-approved, risky calls callback | PASS |
| 11 | MANUAL mode: all actions gated through callback | PASS |
| 12 | auto_backup creates pre_pipeline snapshot; action log complete | PASS |

---

## Cumulative Platform State

| Phases | Focus | Tests |
|--------|-------|-------|
| 1–7 | Foundation → Land Adapter | ~302 |
| 8 | PostgreSQL migration | 55 |
| 9–10 | IVSC compliance + DCF income model | 43 |
| 11–12 | Portfolio + Batch valuation | 45 |
| 13–14 | SQLite batch store + webhook dispatcher | 22 |
| 15 | Enterprise RBAC + audit log | 34 |
| 16 | MCP bridge + Claude Desktop installer | 20 |
| 17 | Local workspace agent | 12 |
| 18 | Automated valuation pipeline | 12 |
| **19** | **Supervised autonomy** | **12** |
| **Total** | | **~557+** |

---

## Next: Phase 20 — Folder Watcher

Real-time file monitoring that auto-triggers the supervised pipeline when new property files land in a watched workspace directory.

Planned components:
- `FileWatcher` — wraps `watchdog` or polling fallback; emits `FileEvent` objects
- `WatcherManager` — per-workspace watcher registry
- Auto-trigger: new `.csv` / `.json` files → `SupervisedAgent.run_pipeline()`
