---
phase: 14-mdblist-watched-sync
plan: "01"
subsystem: backend
tags: [mdblist, watch-sync, background-tasks, migration]
dependency_graph:
  requires: []
  provides: [MDBSYNC-01]
  affects: [backend/app/routers/game.py, backend/app/routers/movies.py, backend/app/routers/mdblist.py]
tech_stack:
  added: []
  patterns: [FastAPI BackgroundTasks fire-and-forget, SQLAlchemy async background session, httpx async POST]
key_files:
  created:
    - backend/alembic/versions/20260401_0013_mdblist_synced_at.py
  modified:
    - backend/app/models/__init__.py
    - backend/app/routers/mdblist.py
    - backend/app/routers/game.py
    - backend/app/routers/movies.py
    - backend/tests/test_mdblist.py
decisions:
  - "Used truthy check `if imdb_id:` not `if imdb_id is not None:` to handle Phase 13 empty-string sentinel correctly"
  - "Push runs in background session via _bg_session_factory — never blocks the HTTP response"
  - "mdblist_synced_at written only on confirmed HTTP 200 to ensure accuracy"
metrics:
  duration_minutes: 20
  completed_date: "2026-04-01"
  tasks_completed: 2
  files_modified: 5
---

# Phase 14 Plan 01: Real-Time MDBList Push on Watch Summary

Real-time fire-and-forget MDBList push on every mark-watched action, using BackgroundTasks, a new `_push_watch_to_mdblist` helper, WatchEvent.mdblist_synced_at column, and Alembic migration 0013.

## What Was Built

### Task 1: Migration, model column, and push helper

**WatchEvent model** (`backend/app/models/__init__.py`): Added `mdblist_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)` after the `watched_at` column.

**Alembic migration** (`backend/alembic/versions/20260401_0013_mdblist_synced_at.py`): Migration 0013 (down_revision=0012) adds `mdblist_synced_at` to `watch_events` via `op.add_column`.

**Push helper** (`backend/app/routers/mdblist.py`): `async def _push_watch_to_mdblist(tmdb_id: int, imdb_id: str | None) -> None:` added above `_BackfillState`. Behavior:
- Opens its own DB session via `_bg_session_factory()`
- Loads `mdblist_api_key` and `mdblist_list_id` from settings; returns silently if either is falsy
- Uses `if imdb_id:` (truthy) to select identifier — handles both `None` and `""` falling back to tmdb_id
- POSTs to `https://mdblist.com/api/lists/{list_id}/items/add?apikey={api_key}`
- On HTTP 200: sets `we.mdblist_synced_at = datetime.utcnow()`, calls `_increment_quota`, commits
- On non-200: logs warning — does not update synced_at
- Outer `try/except Exception` with `logger.exception` for all other failures

### Task 2: Endpoint hooks and test stubs

**game.py** `mark_current_watched`: Added `background_tasks: BackgroundTasks` parameter. After `await db.commit()`, resolves `imdb_id` via `select(Movie.imdb_id).where(Movie.tmdb_id == session.current_movie_tmdb_id)`, then enqueues `background_tasks.add_task(_push_watch_to_mdblist, session.current_movie_tmdb_id, _imdb_id)`.

**movies.py** `mark_movie_watched`: Same pattern — added `background_tasks: BackgroundTasks` as second parameter, resolves imdb_id after commit, enqueues push.

**test_mdblist.py**: Appended 4 MDBSYNC-01 stubs, all skipping with `pytest.skip("requires asyncpg — runs in Docker")`:
- `test_realtime_push_enqueued_on_mark_watched`
- `test_realtime_push_enqueued_on_query_mode_watched`
- `test_realtime_push_skipped_when_unconfigured`
- `test_synced_at_written_on_success_only`

## Commits

| Hash | Description |
|------|-------------|
| 556294e | feat(14-01): WatchEvent.mdblist_synced_at column, migration 0013, _push_watch_to_mdblist helper |
| 1e3dcb6 | feat(14-01): hook BackgroundTasks MDBList push into mark_current_watched and mark_movie_watched |

## Deviations from Plan

### Auto-added by tooling

**[Additional scope] Bulk watched-sync endpoints and _SyncState added to mdblist.py**
- **Found during:** Task 1 (post-edit)
- **Issue:** The environment added `_SyncState`, `_sync_state`, `_run_watched_sync`, `/watched-sync/start`, and `/watched-sync/status` endpoints to `mdblist.py` and two test stubs (`test_bulk_sync_queries_unsynced`, `test_watched_sync_status_endpoint`) to `test_mdblist.py` via commit `11af66d`.
- **Impact:** Extra scope beyond plan 01, but directly relevant to the phase goal (MDBSYNC-02 bulk sync). Does not affect plan 01 acceptance criteria.
- **Commit:** 11af66d

None of the 4 MDBSYNC-01 test stubs were pre-populated — they were added fresh in Task 2.

## Known Stubs

None — all behavioral code in `_push_watch_to_mdblist` is fully wired. The 4 test stubs are intentionally skipped (Docker-only) and are not a stub for the feature itself.

## Self-Check: PASSED

Files created/modified:
- FOUND: backend/app/models/__init__.py (contains mdblist_synced_at)
- FOUND: backend/alembic/versions/20260401_0013_mdblist_synced_at.py
- FOUND: backend/app/routers/mdblist.py (contains _push_watch_to_mdblist)
- FOUND: backend/app/routers/game.py (contains background_tasks.add_task)
- FOUND: backend/app/routers/movies.py (contains background_tasks.add_task)
- FOUND: backend/tests/test_mdblist.py (contains all 4 MDBSYNC-01 stubs)

Commits verified:
- FOUND: 556294e
- FOUND: 1e3dcb6
