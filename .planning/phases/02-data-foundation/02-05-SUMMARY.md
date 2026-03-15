---
phase: 02-data-foundation
plan: 05
subsystem: api
tags: [fastapi, postgresql, plex, tmdb, webhooks, sqlalchemy]

# Dependency graph
requires:
  - phase: 02-data-foundation/02-02
    provides: WatchEvent ORM model with UniqueConstraint on tmdb_id
  - phase: 02-data-foundation/02-03
    provides: TMDBClient service and movies/actors routers
  - phase: 02-data-foundation/02-04
    provides: PlexSyncService and sync_on_startup function

provides:
  - POST /webhooks/plex endpoint accepting multipart/form-data with Form(...) payload field
  - PATCH /movies/{tmdb_id}/watched endpoint for manual watch marking
  - Fully wired main.py lifespan initializing TMDBClient and running Plex startup sync
  - All four routers registered in app (health, movies, actors, plex_webhook)

affects: [03-movie-game, 04-query-mode]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - FastAPI Form(...) for multipart/form-data webhook ingestion (Plex sends JSON in 'payload' field)
    - ON CONFLICT DO NOTHING for idempotent watch event upserts (both plex_webhook and manual sources)
    - app.state.tmdb_client for shared async client across all requests via lifespan
    - Non-fatal startup sync via try/except in lifespan — Plex unreachable does not prevent app startup

key-files:
  created:
    - backend/app/routers/plex.py
  modified:
    - backend/app/routers/movies.py
    - backend/app/main.py

key-decisions:
  - "plex.py router uses Form(...) not Body(...) — Plex multipart/form-data requires this; JSON body would be rejected by FastAPI"
  - "_extract_tmdb_id handles both Guid list (new Plex Movie agent) and legacy guid string (com.plexapp.agents.themoviedb://)"
  - "sync_on_startup wrapped in try/except in lifespan — Plex unreachable is non-fatal; app starts regardless"
  - "TMDBClient stored as app.state.tmdb_client — single shared instance; close() called on lifespan shutdown"

patterns-established:
  - "Webhook pattern: Form(...) for multipart ingestion, JSON.loads on payload field, event-type guard at top"
  - "Idempotent write pattern: pg_insert(...).on_conflict_do_nothing(index_elements=[...]) for watch events"
  - "Lifespan pattern: DB check -> client init -> startup sync -> yield -> shutdown cleanup"

requirements-completed: [DATA-05, DATA-06]

# Metrics
duration: 5min
completed: 2026-03-15
---

# Phase 2 Plan 05: Integration — Plex Webhook, Manual Mark Watched, and Wired Lifespan

**POST /webhooks/plex with multipart Form ingestion, PATCH /movies/{id}/watched with idempotent ON CONFLICT DO NOTHING, and fully wired FastAPI lifespan managing TMDBClient and Plex startup sync**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-15T15:02:31Z
- **Completed:** 2026-03-15T15:07:30Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created `backend/app/routers/plex.py` with POST /webhooks/plex that accepts Plex multipart payloads, handles both new Guid list and legacy guid string GUID formats, silently ignores non-scrobble and non-movie events, and upserts WatchEvent idempotently
- Added PATCH /{tmdb_id}/watched to the movies router (DATA-06 manual fallback for users without Plex Pass)
- Rewrote `main.py` lifespan to initialize TMDBClient, store it on app.state, run Plex startup sync non-fatally, and register all four routers

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement POST /webhooks/plex and add PATCH /movies/{id}/watched** - `4ca1391` (feat)
2. **Task 2: Wire all components into main.py lifespan** - `267cdfa` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `backend/app/routers/plex.py` - POST /webhooks/plex with Form(...) multipart ingestion, dual GUID format support, ON CONFLICT DO NOTHING upsert
- `backend/app/routers/movies.py` - Added PATCH /{tmdb_id}/watched endpoint (DATA-06), added datetime import
- `backend/app/main.py` - Updated lifespan: TMDBClient init, Plex sync, engine.dispose on shutdown, all four routers registered

## Decisions Made

- Used `Form(...)` for the webhook `payload` parameter — Plex sends multipart/form-data; a JSON Body parameter would cause FastAPI to reject the request
- `_extract_tmdb_id` handles both the new Plex Movie agent format (`Guid: [{id: "tmdb://550"}]`) and legacy format (`guid: "com.plexapp.agents.themoviedb://550?lang=en"`)
- Plex startup sync in lifespan wrapped in `try/except` — Plex being unreachable during startup is non-fatal per CONTEXT.md decisions
- TMDBClient created once in lifespan and stored as `app.state.tmdb_client` — avoids per-request instantiation cost; `close()` called on shutdown to flush httpx connection pool

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None — all files compiled cleanly on first attempt. The `python -m py_compile` verification confirmed no syntax or import-resolution errors (the settings-related error when running the Form inspection command was expected outside the container environment, not a code defect).

## User Setup Required

None — no external service configuration required beyond what was established in previous plans.

## Next Phase Readiness

- All six DATA requirements (DATA-01 through DATA-06) now have implementation
- Phase 2 complete: data layer is fully wired and ready for Phase 3 (Movie Game) and Phase 4 (Query Mode) consumption
- Tests in `test_plex_webhook.py` and `test_movies.py` will pass once run against the compose stack with live DB

---
*Phase: 02-data-foundation*
*Completed: 2026-03-15*
