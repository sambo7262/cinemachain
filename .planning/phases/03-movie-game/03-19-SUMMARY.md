---
phase: 03-movie-game
plan: 19
subsystem: api
tags: [fastapi, sqlalchemy, alembic, postgresql, radarr, tmdb, background-tasks, pagination]

# Dependency graph
requires:
  - phase: 03-movie-game
    provides: game session ORM, eligible endpoints, _ensure_actor_credits_in_db, _request_radarr
provides:
  - current_movie_watched field on GameSession (ORM + migration 0003)
  - watched gate (HTTP 423) on eligible-actors and eligible-movies endpoints
  - POST /game/sessions/{id}/mark-current-watched manual mark-watched endpoint
  - Radarr check fired at session creation (radarr_status in response)
  - Async background credits pre-fetch via FastAPI BackgroundTasks on session start
  - Paginated eligible-movies response envelope {items, total, page, page_size, has_more}
affects: [frontend GameSession UI, verification 03-19, future phase 4]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - FastAPI BackgroundTasks for best-effort async post-response work with its own DB session factory
    - HTTP 423 Locked used as watched-gate status code on eligible endpoints
    - Background session factory (_bg_session_factory) created from engine for background tasks that outlive the request

key-files:
  created:
    - backend/alembic/versions/20260315_0003_watched_gate.py
  modified:
    - backend/app/models/__init__.py
    - backend/app/routers/game.py
    - backend/app/routers/plex.py

key-decisions:
  - "HTTP 423 Locked chosen for watched-gate — semantically correct (resource locked until precondition met) and distinct from 403/422"
  - "_prefetch_credits_background swallows all exceptions and uses _bg_session_factory — background tasks cannot share request-scoped DB sessions that are closed after response"
  - "Radarr check fires synchronously at create_session (result in response) vs. background pre-fetch fires asynchronously — user needs Radarr status immediately, credits are best-effort"
  - "current_movie_watched=False reset in resume_session — advancing to new movie clears the gate for the next iteration"
  - "plex.py _maybe_advance_session sets current_movie_watched=True alongside awaiting_continue — Plex scrobble is the authoritative watched signal"
  - "mark_current_watched duplicates _maybe_advance_session logic inline to avoid circular import (plex.py already imports GameSession)"

patterns-established:
  - "Background task with own DB session: async_sessionmaker(engine) at module level, create session inside task with async with"
  - "Watched gate pattern: check session.current_movie_watched after 404 check, raise HTTP 423 before any DB work"

requirements-completed: [GAME-01, GAME-03, GAME-04, GAME-05, GAME-06, GAME-07, GAME-08]

# Metrics
duration: 3min
completed: 2026-03-15
---

# Phase 3 Plan 19: Gap-Closure — Watched Gate, Async Pre-fetch, Pagination Summary

**Backend watched-state gate, manual mark-watched endpoint, Radarr-on-start, async credits pre-fetch, and eligible-movies pagination resolving NAS timeout root cause**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-15T21:56:58Z
- **Completed:** 2026-03-15T21:59:21Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Added `current_movie_watched` boolean field to `GameSession` ORM with Alembic migration 0003 (NOT NULL, server_default=false)
- Implemented watched gate (HTTP 423) on both eligible-actors and eligible-movies endpoints; Plex webhook and manual endpoint both set the flag
- Added `POST /game/sessions/{id}/mark-current-watched`: creates WatchEvent, sets session to awaiting_continue; added BackgroundTasks pre-fetch of starting movie cast credits at session creation; Radarr check now fires inline at session start with radarr_status in response; eligible-movies returns paginated envelope {items, total, page, page_size, has_more}

## Task Commits

Each task was committed atomically:

1. **Task 1: Add current_movie_watched to GameSession ORM and Alembic migration** - `cf7044c` (feat)
2. **Task 2: Redesign create_session, add mark-current-watched, enforce watched gate** - `76a131e` (feat)
3. **Task 3: Add pagination to get_eligible_movies endpoint** - `56b17eb` (feat)

## Files Created/Modified
- `backend/alembic/versions/20260315_0003_watched_gate.py` - Migration 0003 adding current_movie_watched column
- `backend/app/models/__init__.py` - current_movie_watched: Mapped[bool] field on GameSession
- `backend/app/routers/game.py` - All 5 gap-closure items: watched gate, mark-current-watched endpoint, BackgroundTasks pre-fetch, Radarr-on-start, pagination
- `backend/app/routers/plex.py` - _maybe_advance_session sets current_movie_watched=True alongside awaiting_continue

## Decisions Made
- HTTP 423 Locked for watched gate — semantically correct and distinct from 403/422
- Background pre-fetch uses `_bg_session_factory = async_sessionmaker(engine)` at module level; errors swallowed since it is best-effort
- Radarr check fires synchronously in create_session so result is available in the response immediately
- `current_movie_watched = False` reset in `resume_session` so each new movie iteration starts with gate closed
- `mark_current_watched` duplicates _maybe_advance_session logic inline to avoid circular import

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None — all changes are backend code. Docker image rebuild and `alembic upgrade head` required to apply migration 0003 in the running NAS environment.

## Next Phase Readiness
- Backend gap-closure complete; frontend needs: (1) Mark as Watched button in GameSession, (2) gate UI showing locked state until watched, (3) Radarr notification on session start for starting movie
- All GAME-01 through GAME-08 backend requirements now fully implemented
- Docker image rebuild + migration deployment required before 03-19 verification pass

---
*Phase: 03-movie-game*
*Completed: 2026-03-15*
