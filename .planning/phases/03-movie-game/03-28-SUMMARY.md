---
phase: 03-movie-game
plan: 28
subsystem: api
tags: [fastapi, tmdb, background-tasks, game, eligible-actors]

# Dependency graph
requires:
  - phase: 03-27
    provides: GAME-04 defect documented — get_eligible_actors intersection root cause identified
provides:
  - Fixed get_eligible_actors with request: Request parameter and on-demand fallback
  - BackgroundTasks pre-fetch wired into request_movie for new movie cast population
  - _prefetch_credits_background called from both create_session and request_movie
affects: [03-29, Phase 3 verification, full game loop Step 6]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "on-demand TMDB fallback: if DB query returns empty, synchronously fetch credits then re-run query"
    - "BackgroundTasks pre-fetch pattern: fire _prefetch_credits_background after db.commit() for every new movie"

key-files:
  created: []
  modified:
    - backend/app/routers/game.py

key-decisions:
  - "03-28: get_eligible_actors on-demand fallback fetches /movie/{id}/credits directly (top 20 cast), calls _ensure_actor_credits_in_db per actor, then re-runs original SQL stmt — identical to combined-view pattern in get_eligible_movies"
  - "03-28: request_movie now fires background credits pre-fetch for the newly selected movie after db.commit() — mirrors create_session line 318 pattern exactly; closes the window where eligible-actors DB query runs before background task completes"

patterns-established:
  - "Pre-fetch + on-demand fallback: background task races ahead; on-demand in eligible-actors catches the race condition"

requirements-completed: [GAME-04]

# Metrics
duration: 5min
completed: 2026-03-16
---

# Phase 3 Plan 28: GAME-04 Eligible-Actors Bug Fix Summary

**Fixed eligible-actors intersection bug: request_movie now pre-fetches new movie cast via BackgroundTasks; get_eligible_actors falls back to on-demand TMDB fetch when DB returns empty cast**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-16T02:42:30Z
- **Completed:** 2026-03-16T02:47:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Added `background_tasks: BackgroundTasks` to `request_movie` signature and fired `_prefetch_credits_background` after `db.commit()` — ensures new movie's cast is populated in DB before user opens Eligible Actors tab
- Added `request: Request` to `get_eligible_actors` signature enabling TMDB client access
- Added on-demand fallback in `get_eligible_actors`: when DB returns empty actors list, synchronously fetches `/movie/{id}/credits` from TMDB, calls `_ensure_actor_credits_in_db` for each cast member, then re-runs the SQL query
- Both call sites of `_prefetch_credits_background` now exist: `create_session` (line 318) and `request_movie` (line 832)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix request_movie + get_eligible_actors for GAME-04** - `2d0381c` (fix)

## Files Created/Modified
- `backend/app/routers/game.py` - Added BackgroundTasks to request_movie, request: Request to get_eligible_actors, on-demand fallback block when actors list is empty

## Decisions Made
- On-demand fallback fetches top 20 cast members (matching `_prefetch_credits_background` limit) to stay consistent with pre-fetch behavior
- Exception in fallback is swallowed gracefully — endpoint returns empty list rather than 500 if TMDB is unavailable
- Re-runs the original `stmt` variable after populating credits (avoids code duplication, picks up same filters: current_movie_tmdb_id and not_in picked_ids)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - `python3` used instead of `python` (command not found on macOS), syntax check passed.

## User Setup Required

None - no external service configuration required.

Docker rebuild and NAS deploy required before live verification:
- `make rebuild` or manual `docker build` + push
- Deploy to NAS
- Verify Step 6 of full game loop (Free Guy → Ryan Reynolds → Eligible Actors tab shows Deadpool and Wolverine cast)

## Next Phase Readiness
- GAME-04 fix is in game.py; requires Docker rebuild + NAS deploy + live re-verification (03-29 gap-closure)
- No other files modified; fix is surgical and isolated

---
*Phase: 03-movie-game*
*Completed: 2026-03-16*
