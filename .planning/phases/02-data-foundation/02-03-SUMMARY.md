---
phase: 02-data-foundation
plan: "03"
subsystem: api
tags: [tmdb, httpx, fastapi, sqlalchemy, postgresql, async, caching]

# Dependency graph
requires:
  - phase: 02-02
    provides: ORM models (Movie, Actor, Credit, WatchEvent) with lazy="raise" relationships
  - phase: 02-01
    provides: Docker infrastructure and database connection (get_db, AsyncSession)
provides:
  - TMDBClient service with fetch_movie, fetch_actor_credits, fetch_person, close methods
  - GET /movies/{tmdb_id} endpoint with lazy-fetch-and-cache pattern
  - GET /actors/{tmdb_id}/filmography endpoint with lazy-fetch-and-cache pattern
affects: [02-04, 02-05, 03-movie-game, 04-query-mode]

# Tech tracking
tech-stack:
  added: [httpx.AsyncClient, asyncio.Semaphore]
  patterns: [lazy-fetch-cache, pg_insert ON CONFLICT DO NOTHING upserts, selectinload on lazy=raise relationships, app.state dependency injection]

key-files:
  created:
    - backend/app/services/__init__.py
    - backend/app/services/tmdb.py
    - backend/app/routers/movies.py
    - backend/app/routers/actors.py
  modified: []

key-decisions:
  - "fetch_person added to TMDBClient for testability — actors router uses it instead of accessing _client directly"
  - "Actor upsert uses pg_insert ON CONFLICT DO NOTHING (index_elements=[tmdb_id]) — safe for concurrent multi-movie fetches sharing actors"
  - "Credit upsert uses pg_insert ON CONFLICT DO NOTHING (index_elements=[movie_id, actor_id]) — idempotent re-entry"
  - "poster_path stored as raw relative path (/abc.jpg) — caller prepends image base URL at render time"
  - "genres stored as JSON string in DB; parsed to list in response — avoids separate genres table"
  - "Actor filmography fetch requires two TMDB calls: fetch_actor_credits for credits + fetch_person for actor metadata"

patterns-established:
  - "lazy-fetch-cache: check DB first, fetch TMDB on miss, upsert to DB, return from DB"
  - "selectinload chaining: selectinload(Actor.credits).selectinload(Credit.movie) for nested lazy=raise traversals"
  - "TMDBClient via app.state: request.app.state.tmdb_client — wired by main.py lifespan (Plan 02-05)"
  - "Semaphore cap: asyncio.Semaphore(10) in TMDBClient prevents concurrent TMDB request overflow"

requirements-completed: [DATA-01, DATA-02, DATA-03]

# Metrics
duration: 2min
completed: 2026-03-15
---

# Phase 2 Plan 03: TMDB Service and Lazy-Fetch Cache Routers Summary

**httpx-based TMDBClient with asyncio.Semaphore(10) rate cap, plus GET /movies and GET /actors filmography endpoints that lazy-fetch from TMDB on cache miss and serve PostgreSQL-cached data on repeat requests**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-15T14:56:48Z
- **Completed:** 2026-03-15T14:59:16Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- TMDBClient service with four methods: fetch_movie (with append_to_response=credits), fetch_actor_credits, fetch_person (for actor metadata), and close
- GET /movies/{tmdb_id}: checks DB cache, fetches TMDB on miss, upserts Movie + Actor + Credit rows via ON CONFLICT DO NOTHING, returns watched flag from WatchEvent
- GET /actors/{tmdb_id}/filmography: checks DB cache, fetches actor credits + person details on miss, returns filmography with per-movie watched flag via batch WatchEvent query

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement TMDBClient service** - `f96f5ca` (feat)
2. **Task 2: Implement movies and actors routers** - `6dfd65f` (feat)

## Files Created/Modified

- `backend/app/services/__init__.py` - Empty package marker for services module
- `backend/app/services/tmdb.py` - TMDBClient class: httpx.AsyncClient with base_url, api_key param, Semaphore(10), fetch_movie/fetch_actor_credits/fetch_person/close
- `backend/app/routers/movies.py` - GET /movies/{tmdb_id}: lazy-fetch-cache with TMDB field mapping, pg upserts, watched flag
- `backend/app/routers/actors.py` - GET /actors/{tmdb_id}/filmography: lazy-fetch-cache with selectinload chaining, batch watch state check

## Decisions Made

- Added `fetch_person` method to TMDBClient — the `/person/{id}/movie_credits` endpoint doesn't return actor name or profile_path, so a separate `/person/{id}` call is required. Adding it as a named method keeps the actors router testable without accessing `_client` directly.
- Actors router makes two TMDB calls on cache miss (fetch_actor_credits + fetch_person). This is acceptable for lazy-fetch strategy; actor data is then cached, so subsequent requests serve from DB.
- Movie stubs created during actor filmography fetch use `genres=None` — the `/person/{id}/movie_credits` endpoint returns genre_ids (integers), not genre names. Full genre names are resolved on demand when GET /movies/{id} is called.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added fetch_person method to TMDBClient**
- **Found during:** Task 2 (actors router implementation)
- **Issue:** Plan noted in the action block that `/person/{id}/movie_credits` doesn't include actor metadata and suggested adding `fetch_person` to TMDBClient for testability, but this was listed as a refactor note rather than a required method in Task 1
- **Fix:** Added `fetch_person(person_id: int) -> dict` to TMDBClient in Task 1 files; actors router uses it rather than accessing `_client` directly
- **Files modified:** backend/app/services/tmdb.py
- **Verification:** All three fetch methods present; actors.py imports cleanly
- **Committed in:** f96f5ca (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (missing critical method added proactively)
**Impact on plan:** Aligned with plan's own recommendation; no scope creep.

## Issues Encountered

None — both tasks executed cleanly. Compile verification passed for all files.

## User Setup Required

None — TMDBClient is wired to app.state by Plan 02-05 (main.py lifespan update). No new env vars required; `settings.tmdb_api_key` already exists.

## Next Phase Readiness

- TMDBClient and both routers are ready; they require Plan 02-05 to wire `tmdb_client` into `app.state` via lifespan before the test suite (test_tmdb.py) can pass end-to-end
- Test stubs in `backend/tests/test_tmdb.py` (DATA-01, DATA-02, DATA-03) will become green after Plan 02-05 completes the wiring

---
*Phase: 02-data-foundation*
*Completed: 2026-03-15*
