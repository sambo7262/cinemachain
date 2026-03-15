---
phase: 02-data-foundation
plan: 04
subsystem: database
tags: [plex, plexapi, asyncio, sqlalchemy, postgresql, watch-events, startup-sync]

# Dependency graph
requires:
  - phase: 02-02
    provides: WatchEvent ORM model with UniqueConstraint on tmdb_id, AsyncSessionLocal session factory
provides:
  - PlexSyncService in backend/app/services/plex.py
  - _sync_plex_watched synchronous function for run_in_executor wrapping
  - _upsert_watch_events async bulk upsert with ON CONFLICT DO NOTHING
  - sync_on_startup async coroutine ready for main.py lifespan hook
affects:
  - 02-05 (main.py lifespan wiring)
  - 03-movie-game (watched state available via watch_events)

# Tech tracking
tech-stack:
  added: [plexapi==4.18.0 (already in requirements.txt)]
  patterns:
    - run_in_executor pattern for synchronous third-party SDK calls in async context
    - pg_insert().on_conflict_do_nothing() for idempotent upserts without ORM session
    - Deferred import inside sync function to avoid import-time side effects

key-files:
  created:
    - backend/app/services/plex.py
  modified: []

key-decisions:
  - "PlexAPI import deferred inside _sync_plex_watched body to avoid import-time errors when plexapi is absent or unavailable"
  - "movie_id is None in startup-sync upserts — Plex-watched movies may not yet exist in the movies table; nullable FK is the correct model"
  - "sync_on_startup swallows all exceptions with logger.warning — Plex unavailable must never crash app startup"

patterns-established:
  - "run_in_executor wrapping: any synchronous SDK call placed in a named sync function, then awaited via loop.run_in_executor(None, fn, *args)"
  - "Idempotent upsert: pg_insert(Model).values(...).on_conflict_do_nothing(index_elements=[...]) — preferred over merge/upsert for bulk startup syncs"

requirements-completed: [DATA-04]

# Metrics
duration: 6min
completed: 2026-03-15
---

# Phase 2 Plan 04: Plex Startup Library Sync Summary

**PlexSyncService in plex.py: synchronous PlexAPI fetch wrapped in run_in_executor, bulk-upserts watched movies to watch_events via ON CONFLICT DO NOTHING, non-fatal if Plex unreachable**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-03-15T14:56:51Z
- **Completed:** 2026-03-15T15:03:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Implemented `_sync_plex_watched` as a synchronous function that iterates all Plex Movies library entries, filters watched movies with tmdb:// GUIDs, and returns a list of dicts
- Implemented `_upsert_watch_events` as an async bulk upsert using `pg_insert(...).on_conflict_do_nothing(index_elements=["tmdb_id"])` with `source="plex_sync"`
- Implemented `sync_on_startup` as an async coroutine using `loop.run_in_executor` to avoid blocking the event loop, with full exception swallowing (non-fatal startup)

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement PlexSyncService** - `b554117` (feat)

## Files Created/Modified

- `backend/app/services/plex.py` - PlexSyncService with _sync_plex_watched (sync), _upsert_watch_events (async), sync_on_startup (async)

## Decisions Made

- Deferred `from plexapi.server import PlexServer` to inside `_sync_plex_watched` body so that missing plexapi at import time does not break the module load
- `movie_id=None` in all upsert rows — Plex-watched movies may not yet have been fetched from TMDB; the nullable FK allows storing the watch event immediately
- `sync_on_startup` catches all exceptions (not just `plexapi` exceptions) to ensure no startup crash regardless of network state or config errors

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- System Python 3.9.6 lacks the project's dependencies (sqlalchemy etc.) which are Docker container-only. Used AST inspection to verify sync/async boundaries without requiring the full dependency stack. Module syntax compiles clean via `py_compile`.

## User Setup Required

None - no external service configuration required. Plex credentials already in settings.py (`plex_url`, `plex_token`).

## Next Phase Readiness

- `backend/app/services/plex.py` exports `sync_on_startup` ready for Plan 02-05 (main.py lifespan wiring)
- No blockers for 02-05

## Self-Check: PASSED

All created files exist and task commit b554117 is present in git history.

---
*Phase: 02-data-foundation*
*Completed: 2026-03-15*
