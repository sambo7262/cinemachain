---
phase: 14-mdblist-watched-sync
plan: "02"
subsystem: backend/mdblist-sync
tags: [mdblist, watched-sync, settings, background-task]
dependency_graph:
  requires: []
  provides: [_SyncState, _run_watched_sync, /watched-sync/start, /watched-sync/status, mdblist_list_id-settings-field]
  affects: [backend/app/routers/mdblist.py, backend/app/routers/settings.py]
tech_stack:
  added: []
  patterns: [background-task-with-state, per-item-db-commit, quota-guard]
key_files:
  modified:
    - backend/app/routers/mdblist.py
    - backend/app/routers/settings.py
    - backend/tests/test_mdblist.py
    - backend/tests/test_settings.py
decisions:
  - "_SyncState is a separate dataclass from _BackfillState — independent running/progress tracking"
  - "mdblist_list_id stored as plaintext (not encrypted) — list IDs are not sensitive credentials"
  - "_run_watched_sync resolves imdb_id from Movie table before push; falls back to tmdb_id"
metrics:
  duration: "~10 minutes"
  completed: "2026-04-01"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 4
---

# Phase 14 Plan 02: Bulk Watched Sync Endpoints and mdblist_list_id Settings Field Summary

## One-liner

Bulk watched sync infrastructure: _SyncState dataclass, _run_watched_sync background task with quota guard and per-item commit, POST /watched-sync/start and GET /watched-sync/status endpoints mirroring the backfill pattern, plus mdblist_list_id added to SettingsResponse and SettingsUpdateRequest.

## What Was Built

### _SyncState and _sync_state (mdblist.py)

Added a `_SyncState` dataclass with fields `running`, `synced`, `total`, `calls_used_today`, and `daily_limit` (10,000). An instance `_sync_state = _SyncState()` was placed immediately after the existing `_state = _BackfillState()` line, keeping the two states clearly separated.

### _run_watched_sync (mdblist.py)

Background task that:
- Opens a `_bg_session_factory` session and reads `mdblist_api_key` and `mdblist_list_id` from settings (aborts if either missing)
- Queries `WatchEvent WHERE mdblist_synced_at IS NULL` for the full unsynced set
- For each event: resolves `imdb_id` from `Movie` table (falls back to `tmdb_id` when not found), POSTs to `https://mdblist.com/api/lists/{list_id}/items/add`
- On 200: sets `we.mdblist_synced_at = datetime.utcnow()`, calls `_increment_quota(db)`, commits
- On 429: sleeps 60 seconds and continues
- On other errors: logs warning and continues
- Respects daily quota guard (`calls_used_today >= daily_limit`)
- Paces at `asyncio.sleep(1.0)` per item
- Sets `_sync_state.running = False` in `finally` block

### POST /mdblist/watched-sync/start

- Returns 409 if sync already running
- Loads current quota from DB (resets counter if date changed)
- Counts unsynced events with `func.count(WatchEvent.id) WHERE mdblist_synced_at IS NULL`
- Enqueues `_run_watched_sync` as background task
- Returns `{"started": True, "total": total}`

### GET /mdblist/watched-sync/status

- Returns `running`, `synced`, `total`, `calls_used_today`, `daily_limit`
- When not running: reads actual quota from DB (same pattern as `backfill_status`)
- Falls back to in-memory value if DB unavailable

### Settings DTOs (settings.py)

Added `mdblist_list_id: str | None = None` as the last field in both `SettingsResponse` and `SettingsUpdateRequest` (after `mdblist_api_key`). The field is not encrypted since list IDs are not sensitive.

### Test Stubs

Appended 2 stubs to `test_mdblist.py` and 1 stub to `test_settings.py`, all using `pytest.skip("requires asyncpg — runs in Docker")`.

## Commits

| Hash | Message |
|------|---------|
| 11af66d | feat(14): bulk watched sync endpoints and mdblist_list_id settings field |

## Deviations from Plan

None — plan executed exactly as written. The `mdblist.py` file had already been extended by the parallel plan 01 run (adding `_push_watch_to_mdblist` and `WatchEvent` import), which was expected per the plan note.

## Known Stubs

None. All stub test functions immediately `pytest.skip()` — they contain no data wiring and are placeholder tests only, which is the intended pattern for Docker-only tests.

## Self-Check: PASSED

- `backend/app/routers/mdblist.py` — exists and contains `_SyncState`, `_run_watched_sync`, `watched-sync/start`, `watched-sync/status`
- `backend/app/routers/settings.py` — exists and contains `mdblist_list_id` (2 occurrences)
- `backend/tests/test_mdblist.py` — exists and contains `test_bulk_sync_queries_unsynced`, `test_watched_sync_status_endpoint`
- `backend/tests/test_settings.py` — exists and contains `test_settings_accepts_mdblist_list_id`
- Commit `11af66d` — verified present in git log
