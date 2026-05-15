# Phase 20 Closure — Folder Watcher

**Date:** 2026-05-08  
**Status:** COMPLETE  
**Tests:** 12/12

---

## What Was Built

### `core_engine/agents/file_watcher.py`

#### WatchEventType (str Enum)
| Value | Meaning |
|-------|---------|
| `CREATED` | A new tracked file appeared |
| `MODIFIED` | An existing file's mtime changed |
| `DELETED` | A tracked file was removed |

#### FileEvent (dataclass)
Fields: `event_type · workspace_id · relative_path · absolute_path · detected_at`  
Method: `to_dict()`

#### FileWatcher
- Background polling thread (`daemon=True`); no external dependencies
- Poll interval configurable (default 1.0 s)
- Tracks only configured extensions (default `.csv .json .xlsx .xls`)
- Skips `workspace.json` and `backup.json` by default
- Snapshot diffing: compares `{rel_path → mtime}` maps between polls
- Callback exceptions are swallowed — watcher thread never dies from caller bugs
- API: `start() · stop() · is_running`

#### WatcherManager
- Registry: one workspace → one watcher at a time (new watch replaces old)
- API: `watch() · unwatch() · list_watched() · stop_all()`
- `make_pipeline_trigger(agent, workspace_id, ...)` — returns a callback that calls `agent.run_pipeline()` on every `CREATED` event; pipeline errors swallowed

---

## Integration Pattern

```python
from agents.file_watcher import WatcherManager
from agents.supervised_agent import SupervisedAgent, ExecutionMode

agent   = SupervisedAgent(wm, bridge, execution_mode=ExecutionMode.SUPERVISED,
                          approval_callback=my_approval_fn)
watcher = WatcherManager()

trigger = watcher.make_pipeline_trigger(agent, ws.workspace_id)
watcher.watch(ws.workspace_id, ws.root_path, trigger, poll_interval=2.0)

# Drop a CSV into the workspace → pipeline fires automatically
```

---

## Test Coverage

| # | Test | Result |
|---|------|--------|
| 01 | WatchEventType enum values | PASS |
| 02 | FileEvent dataclass + to_dict | PASS |
| 03 | FileWatcher start/stop is_running transitions | PASS |
| 04 | Detects CREATED when new file appears | PASS |
| 05 | Detects MODIFIED when file content changes | PASS |
| 06 | Detects DELETED when file is removed | PASS |
| 07 | Extension filter — .txt ignored, .csv tracked | PASS |
| 08 | Callback exception swallowed, watcher stays alive | PASS |
| 09 | WatcherManager.watch + list_watched | PASS |
| 10 | WatcherManager.unwatch; False for unknown | PASS |
| 11 | WatcherManager.stop_all | PASS |
| 12 | make_pipeline_trigger fires only on CREATED | PASS |

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
| 19 | Supervised autonomy | 12 |
| **20** | **Folder watcher** | **12** |
| **Total** | | **~569+** |

---

## Next: Phase 21 — Chat UI + Command Parser

Optional conversational interface: `CommandParser` (text → agent action) + lightweight web UI served from `bridge_api.py`.
