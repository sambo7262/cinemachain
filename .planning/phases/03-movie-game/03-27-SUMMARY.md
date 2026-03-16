---
phase: 03-movie-game
plan: 27
subsystem: infra
tags: [docker, deployment, nas, game-loop, verification]

# Dependency graph
requires:
  - phase: 03-movie-game
    provides: "03-26 request_movie current_movie_watched reset fix"
provides:
  - "Docker images rebuilt and pushed with 03-26 fix"
  - "Live NAS deploy confirmed — Steps 1-5 of game loop verified"
  - "GAME-04 eligible-actors logic defect identified and documented for 03-28"
affects: [03-28-gap-closure]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Docker --no-cache rebuild + push + compose pull pattern for NAS gap-closure deploy"

key-files:
  created: []
  modified:
    - "Makefile — rebuild target used to push updated images"

key-decisions:
  - "03-27 PARTIAL PASS: Steps 1-5 verified on live NAS (deploy, fresh session, first movie flow, actor pick, 2nd movie Mark as Watched button present and functional); Step 6 fails"
  - "GAME-04 defect root cause: get_eligible_actors computes intersection of cast across all chain movies rather than (cast of current movie) MINUS (picked actor ids); fix required in backend/app/routers/game.py for 03-28"
  - "03-26 fix (current_movie_watched=False reset) confirmed working — 2nd movie Mark as Watched button now visible and functional"

patterns-established: []

requirements-completed: []  # GAME-04 not fully closed — partial pass; 03-28 required

# Metrics
duration: ~20min
completed: 2026-03-15
---

# Phase 3 Plan 27: Docker Rebuild + NAS Deploy + Full Game Loop Verification Summary

**03-26 fix deployed to live NAS and confirmed working for Steps 1-5; GAME-04 eligible-actors intersection bug blocks Step 6, documented for 03-28 gap-closure**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-03-15T00:10:00Z
- **Completed:** 2026-03-15
- **Tasks:** 1 of 2 fully complete (Task 2 partial — checkpoint outcome)
- **Files modified:** 0 (infra/deploy only)

## Accomplishments

- Rebuilt Docker images with --no-cache (make rebuild) and pushed both backend and frontend to Docker Hub
- Deployed updated images to NAS via docker compose pull && docker compose up -d; containers started clean
- Confirmed 03-26 fix is live: 2nd movie Mark as Watched button is present and functional (the blocking defect from 03-25 is now resolved)
- Full game loop Steps 1-5 verified passing on live hardware using Free Guy → Ryan Reynolds → Deadpool and Wolverine test sequence
- Identified and documented precise root cause of GAME-04 eligible-actors logic defect for 03-28 fix

## Task Commits

Each task was committed atomically:

1. **Task 1: Rebuild and push Docker images** - `bd4a164` (chore)
2. **Task 2: NAS deploy + full game loop verify** - checkpoint/human-verify — partial pass, no code commit

## Files Created/Modified

None — this was a deploy and verification plan. No source files were modified.

## Decisions Made

- 03-26 fix confirmed working in production: request_movie now resets current_movie_watched=False, enabling the Session Home Page to show Mark as Watched for the 2nd movie
- GAME-04 root cause confirmed: get_eligible_actors is computing the intersection of cast members across ALL movies in the chain, rather than (cast of current_movie_tmdb_id) MINUS (actors already picked in this session). This means after picking Ryan Reynolds for step 2, the eligible actors for step 3 show only actors appearing in both Free Guy AND Deadpool and Wolverine — an incorrect intersection rather than the correct subtraction
- Fix spec for 03-28: in backend/app/routers/game.py, get_eligible_actors must (1) get all credits for current_movie_tmdb_id, (2) build picked_actor_ids = {step.actor_tmdb_id for step in session.steps if step.actor_tmdb_id is not None}, (3) return actors from (1) NOT IN (2) — no intersection with previous movies' casts

## Deviations from Plan

None — verification outcome (partial pass) is the expected documented result. No code changes were made in this plan.

## Issues Encountered

**GAME-04 eligible-actors intersection defect discovered during Step 6 verification.**

Test sequence: Free Guy → pick Ryan Reynolds → Deadpool and Wolverine → Continue the chain.

- Expected: Eligible Actors tab shows all cast of Deadpool and Wolverine EXCEPT Ryan Reynolds
- Actual: Eligible Actors tab showed only actors appearing in BOTH Free Guy AND Deadpool and Wolverine (cast intersection across all chain movies)
- Root cause: get_eligible_actors backend query incorrectly computes intersection of cast members across all movies in the chain rather than filtering only by already-picked actor IDs
- Resolution: Deferred to 03-28 gap-closure plan. Fix is well-understood; no architectural change required.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 03-26 fix is live and confirmed: game loop Steps 1-5 pass on NAS
- 03-28 must fix GAME-04 eligible-actors query in backend/app/routers/game.py before Phase 3 can close
- Fix is narrow and well-scoped: change intersection query to subtraction of picked_actor_ids from current movie's cast
- After 03-28 fix + deploy + re-verify Step 6, Phase 3 can be declared complete and Phase 4 (Query Mode) can begin

---
*Phase: 03-movie-game*
*Completed: 2026-03-15*
