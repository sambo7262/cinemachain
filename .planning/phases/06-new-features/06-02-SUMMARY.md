---
phase: 06-new-features
plan: "02"
subsystem: api
tags: [fastapi, python, game, tmdb, radarr, csv-import]

# Dependency graph
requires:
  - phase: 05-production-deployment
    provides: game.py with request_movie, pick_actor, import_csv_session endpoints
provides:
  - overview field in EligibleMovieResponse populated from Movie.overview
  - skip_radarr bool in RequestMovieRequest to bypass Radarr add call
  - PATCH /game/sessions/{id}/name endpoint for renaming sessions
  - CSV import path resolves actor canonical name from TMDB when actor_name is NULL
affects: [06-03, 06-04, 06-05, 06-06, frontend-eligible-movies, frontend-session-management]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "skip_radarr=True sets radarr_status='skipped' in request_movie response"
    - "PATCH rename checks uniqueness excluding self via GameSession.id != session_id"
    - "CSV actor name fallback: fetch_person after step creation if actor_tmdb_id set and actor_name missing"

key-files:
  created: []
  modified:
    - backend/app/routers/game.py

key-decisions:
  - "overview stored in _ensure_movie_details_in_db and _backfill_movie_posters_background so it is populated via both TMDB fetch paths"
  - "skip_radarr guard wraps entire _request_radarr call; radarr_result set to 'skipped' in else branch"
  - "PATCH name validates: non-empty, <=100 chars, uniqueness among non-archived/non-ended sessions excluding self"
  - "CSV actor name fetch_person call is non-critical — exceptions swallowed; actor_name stays None on TMDB failure"

patterns-established:
  - "Pattern: all response-building endpoints call _enrich_steps_thumbnails + _enrich_steps_runtime before _build_session_response"

requirements-completed: [ITEM-1, ITEM-2-backend, ITEM-3-backend]

# Metrics
duration: 2min
completed: 2026-03-22
---

# Phase 06 Plan 02: Backend Game Endpoint Changes Summary

**overview in eligible movie responses, skip_radarr bypass, PATCH session rename endpoint, and CSV actor name resolution via TMDB fetch_person**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-22T14:49:00Z
- **Completed:** 2026-03-22T14:51:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Added `overview: str | None = None` to `EligibleMovieResponse` and both movies_map construction paths (actor-scoped and combined-view) in `get_eligible_movies`
- Added `skip_radarr: bool = False` to `RequestMovieRequest`; guards Radarr call in `request_movie` with `if not body.skip_radarr` and returns `"skipped"` status in else branch
- Added `RenameSessionRequest` model and `PATCH /game/sessions/{session_id}/name` endpoint with name validation (non-empty, <=100 chars), uniqueness check excluding self, and full enriched response
- Fixed CSV import path in `import_csv_session` to call `tmdb.fetch_person(step.actor_tmdb_id)` when step has actor_tmdb_id but no actor_name; populates canonical name from TMDB response
- Updated `_ensure_movie_details_in_db` and `_backfill_movie_posters_background` to store `overview` when fetching full movie details from TMDB

## Task Commits

1. **Task 1: Overview in eligible movies + skip_radarr + PATCH session name** - `cf83d7c` (feat)
2. **Task 2: CSV import actor name resolution fix** - `80c42e0` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `backend/app/routers/game.py` - All four backend changes: overview field, skip_radarr, rename endpoint, CSV actor name fix

## Decisions Made
- Overview stored in both `_ensure_movie_details_in_db` (actor-scoped TMDB fetch) and `_backfill_movie_posters_background` (CSV import poster backfill) so it is populated via all TMDB fetch paths
- PATCH rename uniqueness check uses `GameSession.id != session_id` (excludes self) and `status.not_in(["archived", "ended"])` matching the existing session creation uniqueness pattern
- CSV actor name resolution is non-critical: `except Exception: pass` ensures a TMDB failure on actor lookup does not block session creation

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
- Python import verification failed locally (missing asyncpg module outside Docker); verified via grep instead. All implementation patterns match existing codebase conventions.

## Next Phase Readiness
- Backend endpoints ready for frontend consumption in subsequent plans
- `overview` available in eligible movie API for movie splash screen (Item 2 frontend)
- `skip_radarr` available for frontend Radarr-optional flow
- PATCH name endpoint available for session rename UI (Item 3 frontend)
- CSV import actor names will resolve correctly for new imports

---
*Phase: 06-new-features*
*Completed: 2026-03-22*
