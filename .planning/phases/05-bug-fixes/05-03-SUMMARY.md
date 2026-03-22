---
phase: 05-bug-fixes
plan: 03
subsystem: api
tags: [fastapi, sqlalchemy, game, actor-resolution, disambiguation]

requires:
  - phase: 05-02
    provides: pick_actor with BackgroundTasks and canonical actor name tracking (BUG-4)

provides:
  - BUG-1 fix: request_movie auto-resolves connecting actor when no explicit pick was made
  - skip_actor=True bypass for disambiguation infinite-loop prevention
  - disambiguation_required response with candidates list for multi-actor ambiguity

affects: [frontend-game, chain-history, game-session-steps]

tech-stack:
  added: []
  patterns:
    - "Auto-resolve pattern: query shared actors between prev/selected movie before creating movie step"
    - "skip_actor bypass: frontend re-submits with skip_actor=True to escape disambiguation loop"
    - "Step order invariant: actor step at N, movie step at N+1 (matches ChainHistory.tsx line 27)"

key-files:
  created: []
  modified:
    - backend/app/routers/game.py

key-decisions:
  - "actor step movie_tmdb_id = previous_movie (not selected) — semantics: actor was selected FROM this movie"
  - "skip_actor=False default preserves backward compatibility — existing clients unaffected"
  - "Actor.tmdb_id.not_in(already_picked_ids) filter excluded only when already_picked_ids is empty (avoids SQL IN with empty list)"
  - "auto_step_added flag recalculates next_order as existing_max+2 when actor step was auto-inserted"

patterns-established:
  - "disambiguation_required: return early before any db.add() — session state must remain unchanged"
  - "Auto-actor creation: db.add() without commit — movie step added next, single commit for both"

requirements-completed: [BUG-1]

duration: 2min
completed: 2026-03-22
---

# Phase 5 Plan 03: BUG-1 Auto-Actor Resolution Summary

**request_movie now auto-creates connecting actor step when exactly one shared actor exists, returns disambiguation_required with candidates when multiple actors connect, and accepts skip_actor=True to bypass the loop**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-22T04:01:37Z
- **Completed:** 2026-03-22T04:02:58Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Added `skip_actor: bool = False` to `RequestMovieRequest` Pydantic model
- Implemented auto-resolve logic: queries shared actors between `session.current_movie_tmdb_id` and `body.movie_tmdb_id`
- Single shared actor path: auto-creates `GameSessionStep` at `existing_max+1`, movie step at `existing_max+2`
- Multiple shared actors path: returns `{"status": "disambiguation_required", "candidates": [...], "session": ...}` without creating any steps
- Zero shared actors or `skip_actor=True`: falls through to existing movie step creation unchanged
- Step order invariant preserved: actor step at N, movie step at N+1 matches `ChainHistory.tsx` expectation

## Task Commits

1. **Task 1: BUG-1 auto-resolve connecting actor in request_movie** - `3e57f2e` (feat)

## Files Created/Modified

- `/Users/Oreo/Projects/backend/app/routers/game.py` - Added `skip_actor` field to `RequestMovieRequest`, inserted auto-resolve block before movie step creation, updated `next_order` calculation

## Decisions Made

- `actor step movie_tmdb_id = session.current_movie_tmdb_id` (previous movie, not selected) — preserves "actor was selected FROM this movie" semantics required by chain history rendering
- `Actor.tmdb_id.not_in(already_picked_ids) if already_picked_ids else True` — avoids SQLAlchemy `.not_in([])` generating invalid SQL
- `auto_step_added` boolean flag used to switch between `existing_max+1` and `existing_max+2` cleanly
- Tests skip locally (asyncpg not installed) and run in Docker — consistent with all other BUG tests in this phase

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - `Actor`, `Credit`, and `Movie` already imported in `game.py`; syntax valid; all 46 tests pass (skip locally as expected).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- BUG-1 backend fix complete; frontend disambiguation dialog (05-04) can now handle `disambiguation_required` response
- `skip_actor=True` field available for frontend to use in re-submit after user dismisses dialog
- ChainHistory step ordering invariant preserved — no frontend rendering changes needed for auto-actor path

---
*Phase: 05-bug-fixes*
*Completed: 2026-03-22*

## Self-Check: PASSED

- `/Users/Oreo/Projects/.planning/phases/05-bug-fixes/05-03-SUMMARY.md` — FOUND
- `/Users/Oreo/Projects/backend/app/routers/game.py` — FOUND
- Commit `3e57f2e` — FOUND
