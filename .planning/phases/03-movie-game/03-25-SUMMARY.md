---
phase: 03-movie-game
plan: 25
subsystem: infra
tags: [docker, game-loop, verification, gap-closure]

# Dependency graph
requires:
  - phase: 03-24
    provides: view state refactor (view:'home'|'tabs'), NavBar active-session routing
provides:
  - Steps 2-5 of full game loop verified on live NAS (session home page, NavBar, Mark as Watched, Continue the chain / Back)
  - Root cause identified for Step 6 failure: request_movie does not reset current_movie_watched=False
  - Precise fix path documented for 03-26 (game.py request_movie endpoint)
affects: [03-26]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Docker --no-cache rebuild via Makefile rebuild target; both images pushed atomically"

key-files:
  created: []
  modified:
    - Makefile

key-decisions:
  - "03-25 is a PARTIAL PASS — Steps 2-5 pass, Step 6 fails; 03-26 required to close the game loop"
  - "Root cause of Step 6 failure: request_movie endpoint (game.py) advances current_movie_tmdb_id but does NOT reset current_movie_watched=False; flag remains True from first movie; home page condition (active + !current_movie_watched) is never met for 2nd movie"
  - "Fix path for 03-26: set current_movie_watched=False in request_movie immediately after updating current_movie_tmdb_id and creating new GameSessionStep"
  - "UI refinements deferred to a later iteration after core user journey is solidified — captured in deferred-items.md"

patterns-established: []

requirements-completed: []

# Metrics
duration: ~45min
completed: 2026-03-15
---

# Phase 3 Plan 25: Docker Rebuild + Full Game Loop Verification Summary

**Docker images rebuilt and pushed; Steps 2-5 of the full game loop pass on live NAS; Step 6 (2nd movie Mark as Watched) blocked by request_movie not resetting current_movie_watched=False — fix path documented for 03-26.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-03-15 (session start)
- **Completed:** 2026-03-15
- **Tasks:** 1 complete, 1 partial (checkpoint — human verification)
- **Files modified:** 1 (Makefile — no-cache rebuild target used)

## Accomplishments

- Both Docker images (backend + frontend) rebuilt with `--no-cache` and pushed to Docker Hub with 03-24 frontend changes
- NAS containers updated via `docker compose pull && docker compose up -d`
- Steps 2-5 confirmed passing on live NAS:
  - Session Home Page is default landing on `/game/{id}` (Gap 1 closed)
  - NavBar Sessions routes directly to active session home page (Gap 3 closed)
  - Mark as Watched button functional on Session Home Page for active+unwatched session
  - Continue the chain opens Tab View; Back button returns to Session Home Page (Gap 2 closed)
- Root cause identified for Step 6 (full game loop) failure — precise fix documented for 03-26

## Task Commits

Each task was committed atomically:

1. **Task 1: Docker rebuild and push** - `1b9dfac` (chore)
2. **Task 2: NAS deploy + full game loop verification** — No commit (checkpoint — partial pass; documentation only)

**Plan metadata:** (this SUMMARY + STATE update commit — see below)

## Files Created/Modified

- `Makefile` — Used existing `rebuild` target for `--no-cache` Docker build and push of both images

## Decisions Made

- 03-25 recorded as **PARTIAL PASS** — Steps 2-5 verified; Step 6 blocked
- No code changes attempted in this plan — fix deferred to 03-26 per `<resume_instructions>`
- UI refinements (cosmetic/UX improvements) deferred to a later iteration; captured in `deferred-items.md`

## Deviations from Plan

None — plan executed exactly as written. The partial pass outcome was discovered through normal human verification; no auto-fixes were required or applied.

## Verification Results

| Step | Description | Result |
|------|-------------|--------|
| 1 | Deploy to NAS | PASS |
| 2 | Session Home Page is default landing | PASS |
| 3 | NavBar Sessions routes to active session home page | PASS |
| 4 | Mark as Watched on Session Home Page | PASS |
| 5 | Continue the chain → Tab View with Back button | PASS |
| 6 | Full game loop — 2nd movie Mark as Watched visible | FAIL |

## Root Cause Analysis (Step 6 Failure)

**Symptom:** After selecting the 2nd movie and being returned to the Session Home Page, the "Mark as Watched" button is absent. The game loop cannot advance past the 2nd movie.

**Cause:** The `request_movie` backend endpoint (backend/app/routers/game.py) advances `current_movie_tmdb_id` to the new movie and creates a new `GameSessionStep`, but does NOT reset `current_movie_watched = False`.

**State after first movie flow:**
1. First movie played → user clicks "Mark as Watched" → `current_movie_watched` set to `True`, status → `awaiting_continue`
2. User clicks "Continue the chain" → `continue-chain` endpoint sets `status = active` but does NOT touch `current_movie_watched` (correct — `current_movie_watched=True` is preserved intentionally here)
3. User picks actor, then picks movie → `request_movie` advances to new movie but leaves `current_movie_watched = True`

**Session Home Page condition for "Mark as Watched" button:**
```
status === 'active' && current_movie_watched === false
```
With `current_movie_watched` stuck at `True`, this condition is never met for the 2nd movie.

**Fix for 03-26:**
In `backend/app/routers/game.py`, in the `request_movie` endpoint, immediately after updating `current_movie_tmdb_id` and creating the new `GameSessionStep`, add:
```python
session.current_movie_watched = False
```

## Issues Encountered

- Step 6 blocked by backend state bug (root cause identified — see above). No unexpected environment or infrastructure issues.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

**03-26 is required before Phase 3 can close:**
- Fix `request_movie` to reset `current_movie_watched = False` when advancing to new movie
- Rebuild Docker images and deploy to NAS
- Verify full game loop end-to-end including GAME-04 (actor dedup on 2nd step)

**Deferred (post core-loop stabilisation):**
- UI refinements captured in `deferred-items.md`

---
*Phase: 03-movie-game*
*Completed: 2026-03-15*
