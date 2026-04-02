---
phase: 16-watched-history
plan: "01"
subsystem: backend-cleanup
tags: [cleanup, mdblist, migration, alembic, deletion]
dependency_graph:
  requires: []
  provides: [clean-mdblist-no-sync, migration-0016-drop-mdblist-synced-at]
  affects: [backend/routers/mdblist, backend/routers/movies, backend/routers/game, backend/routers/settings, frontend/Settings, frontend/api]
tech_stack:
  added: []
  patterns: [alembic-batch-alter-table-sqlite]
key_files:
  created:
    - backend/alembic/versions/20260401_0016_drop_mdblist_synced_at.py
  modified:
    - backend/app/models/__init__.py
    - backend/app/routers/mdblist.py
    - backend/app/routers/movies.py
    - backend/app/routers/game.py
    - backend/app/routers/settings.py
    - backend/tests/test_mdblist.py
    - backend/tests/test_settings.py
    - frontend/src/lib/api.ts
    - frontend/src/pages/Settings.tsx
decisions:
  - "Used batch_alter_table for SQLite compatibility in migration 0016 (same pattern as all prior migrations)"
  - "Preserved BackgroundTasks in mark_current_watched — still needed for _update_session_suggestions (Phase 15)"
  - "Confirmed test_parse_all_rating_sources failure is pre-existing (imdb_rating scale mismatch, not introduced by this plan)"
metrics:
  duration: "~25 minutes"
  completed_date: "2026-04-01"
  tasks_completed: 3
  files_changed: 9
---

# Phase 16 Plan 01: MDBList Watched-Sync Removal Summary

Pure cleanup: deleted all Phase 14 MDBList watched-sync backend and frontend code, dropped the `mdblist_synced_at` column via Alembic migration 0016 (SQLite batch mode, revision chain 0015 → 0016).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Alembic migration 0016 + WatchEvent model update | fb0f259 | backend/alembic/versions/20260401_0016_drop_mdblist_synced_at.py, backend/app/models/__init__.py |
| 2 | Remove Phase 14 watched-sync code from backend + tests | 8d2858a | mdblist.py, movies.py, game.py, settings.py, test_mdblist.py, test_settings.py |
| 3 | Remove Phase 14 watched-sync code from frontend | 3e1c159 | frontend/src/lib/api.ts, frontend/src/pages/Settings.tsx |

## What Was Removed

**Backend — mdblist.py:**
- `_push_watch_to_mdblist` async function (fire-and-forget HTTP push)
- `_SyncState` dataclass + `_sync_state` instance
- `_run_watched_sync` async background function
- `POST /watched-sync/start` endpoint
- `GET /watched-sync/status` endpoint
- `WatchEvent` from the models import

**Backend — movies.py:**
- `BackgroundTasks` from FastAPI import
- `from app.routers.mdblist import _push_watch_to_mdblist` import
- `background_tasks: BackgroundTasks` parameter from `mark_movie_watched`
- imdb_id resolution query + `background_tasks.add_task(_push_watch_to_mdblist, ...)` block

**Backend — game.py:**
- `from app.routers.mdblist import _push_watch_to_mdblist` import
- imdb_id resolution query + `background_tasks.add_task(_push_watch_to_mdblist, ...)` block
- `BackgroundTasks` and `_update_session_suggestions` call PRESERVED (Phase 15 dependency)

**Backend — settings.py:**
- `mdblist_list_id: str | None = None` from `SettingsResponse`
- `mdblist_list_id: str | None = None` from `SettingsUpdateRequest`

**Tests:**
- 6 Phase 14 stubs from test_mdblist.py (MDBSYNC-01/02 skip stubs)
- `test_settings_accepts_mdblist_list_id` from test_settings.py

**Frontend — api.ts:**
- `mdblist_list_id: string | null` from `SettingsDTO`
- `WatchedSyncStatusDTO` interface
- `startWatchedSync` and `getWatchedSyncStatus` from `api.mdblist`

**Frontend — Settings.tsx:**
- `mdblist_list_id: ""` from `emptyForm`
- 4 sync state declarations: `syncRunning`, `syncStatus`, `syncDone`, `showSyncConfirm`
- `getWatchedSyncStatus()` call in mount useEffect
- `syncRunning` polling useEffect
- `handleSyncClick` and `handleSyncConfirm` handlers
- Entire "MDBList Watch Sync" `<Card>` block (82 lines)

**Database model:**
- `mdblist_synced_at: Mapped[Optional[datetime]]` removed from `WatchEvent`
- `rating` field preserved (used by Phase 16 personal ratings)

## Verification Results

- Migration 0016 exists with revision chain `0015 → 0016`, uses `batch_alter_table`
- `WatchEvent` model has no `mdblist_synced_at`; `rating` is present
- Zero occurrences of `_push_watch_to_mdblist`, `WatchedSyncStatusDTO`, `startWatchedSync`, `getWatchedSyncStatus`, `mdblist_list_id` in backend or frontend source
- `mdblist.py` router imports cleanly
- TypeScript: `npx tsc --noEmit` passes with zero errors
- pytest: 1 pre-existing failure (`test_parse_all_rating_sources` — imdb_rating scale mismatch, existed before this plan), 5 passed, 1 skipped

## Deviations from Plan

None — plan executed exactly as written, in the correct sequence (deleted watched-sync endpoint blocks before removing `WatchEvent` import as specified).

## Known Stubs

None — this is a deletion-only plan. No new code introduced.

## Self-Check: PASSED

- Migration file: FOUND `/Users/Oreo/Projects/CinemaChain/backend/alembic/versions/20260401_0016_drop_mdblist_synced_at.py`
- Commit fb0f259: FOUND
- Commit 8d2858a: FOUND
- Commit 3e1c159: FOUND
- TypeScript compile: PASSED
- No `_push_watch_to_mdblist` in source: CONFIRMED
