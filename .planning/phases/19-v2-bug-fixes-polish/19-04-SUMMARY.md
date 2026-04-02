---
phase: 19-v2-bug-fixes-polish
plan: 04
subsystem: api, ui
tags: [fastapi, react, typescript, game-session, delete-step]

# Dependency graph
requires:
  - phase: 19-03
    provides: GameSession filter/NR toggle/sort defaults

provides:
  - Atomic two-step delete_last_step (D-25): removes movie step + preceding actor step atomically
  - Session settings dropdown reordered per D-24

affects: [game-session, session-management]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Atomic two-step revert: check last_step.actor_tmdb_id is None + prev step is actor step before deciding delete scope"

key-files:
  created: []
  modified:
    - backend/app/routers/game.py
    - frontend/src/pages/GameSession.tsx

key-decisions:
  - "D-25: delete_last_step atomically removes movie step + preceding actor step; reverts current_movie_tmdb_id to steps[-3]; requires len(steps)>=3 guard; actor-only last steps fall through to single-step delete"
  - "D-24: session settings menu order is Export CSV, Edit Session Name, Delete Last Step, Archive Session"

patterns-established:
  - "Atomic two-step revert: check last_step.actor_tmdb_id is None and prev_step.actor_tmdb_id is not None before deleting two steps"

requirements-completed: [v2BUG-01]

# Metrics
duration: 8min
completed: 2026-04-02
---

# Phase 19 Plan 04: Atomic Delete Last Step and Menu Reorder Summary

**Atomic two-step delete_last_step that removes both the movie step and preceding actor step, reverting to the movie the actor was picked from; session settings dropdown reordered per D-24**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-02T18:20:00Z
- **Completed:** 2026-04-02T18:28:00Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- D-25: delete_last_step now atomically deletes both the movie step and the preceding actor step when the last step is a movie step with an actor step immediately before it
- Session reverts to `steps[-3].movie_tmdb_id` after two-step delete, correctly restoring the player to the movie from which the actor was chosen
- Edge cases handled: actor-only last step (no movie picked yet) falls through to single-step delete; short chains (len<3) also fall through to single-step delete
- D-24: Session settings dropdown reordered to Export CSV, Edit Session Name, Delete Last Step, Archive Session

## Task Commits

Each task was committed atomically:

1. **Task 1: Atomic two-step delete_last_step and menu reorder** - `1f9ab63` (feat)

## Files Created/Modified
- `backend/app/routers/game.py` - delete_last_step: atomic two-step delete logic with D-25 conditions
- `frontend/src/pages/GameSession.tsx` - session settings dropdown reordered per D-24

## Decisions Made
- D-25: Conditions for two-step delete are `last_step.actor_tmdb_id is None` (movie step) AND `prev_step.actor_tmdb_id is not None` (actor step) AND `len(steps) >= 3`. All three must be true.
- D-24: New menu order is Export CSV, Edit Session Name, Delete Last Step, Archive Session — Edit Session Name promoted above destructive Delete Last Step action.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `python` command not found on host (macOS uses `python3`); `python3 -m py_compile` confirmed syntax OK. Docker container runs Python 3.12 where the code actually executes.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plans 19-05 and 19-06 can proceed; no blockers introduced.

---
*Phase: 19-v2-bug-fixes-polish*
*Completed: 2026-04-02*
