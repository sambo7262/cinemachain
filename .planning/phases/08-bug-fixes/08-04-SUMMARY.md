---
phase: 08-bug-fixes
plan: "04"
subsystem: api
tags: [fastapi, sqlalchemy, csv, game-session, bug-fix]

# Dependency graph
requires:
  - phase: 03-game-engine
    provides: game session routing and step model in backend/app/routers/game.py
provides:
  - CSV export handles step_order gaps via forward-scan instead of +1 assumption
  - Combined-view eligible movies self-heals when current movie has no credits in DB
  - Regression test for BUG-08 step_order gap scenario
affects: [csv-export, eligible-movies, game-session]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Forward-scan with next() instead of dict.get(key+1) for step lookup in sorted lists"
    - "Self-healing DB check pattern: detect missing data, trigger re-fetch, retry query in same request"

key-files:
  created: []
  modified:
    - backend/app/routers/game.py
    - backend/tests/test_game.py

key-decisions:
  - "Forward-scan using next() over sorted_steps is the robust solution for step_order gaps — no index math assumptions"
  - "Self-healing eligible-movies: check credits existence before returning empty, trigger re-fetch if zero credits found"
  - "hasattr(request.app.state, 'tmdb_client') guard prevents AttributeError in test environments without TMDB client"

patterns-established:
  - "Step lookup: always forward-scan by step_order comparison, never assume consecutive ordering"
  - "Self-healing DB data: detect -> log warning -> re-fetch -> retry, all in single request"

requirements-completed: [BUG-07, BUG-08]

# Metrics
duration: 10min
completed: 2026-03-31
---

# Phase 08 Plan 04: Session Bug Fixes Summary

**CSV export forward-scan fix for step_order gaps (BUG-08) and self-healing eligible-movies re-fetch for missing movie credits (BUG-07)**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-31T03:23:00Z
- **Completed:** 2026-03-31T03:33:00Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- Replaced fragile `step_by_order.get(step.step_order + 1)` with forward-scan in `export_session_csv` — CSV export no longer crashes when session steps have gaps from deleted steps
- Added self-healing to combined-view eligible movies: when no eligible actors found and current movie has zero credits in DB, triggers `_ensure_movie_cast_in_db` re-fetch and retries actor query in the same request
- Added regression test `test_csv_export_with_step_order_gap` covering the BUG-08 scenario

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix CSV export step_order gap** - `4ff55ec` (fix)
2. **Task 2: Self-heal combined-view eligible movies** - `d09abbd` (fix)
3. **Task 3: Regression test for BUG-08** - `9af7081` (test)

## Files Created/Modified
- `backend/app/routers/game.py` - Replaced step_by_order dict + step_order+1 lookup with forward-scan next(); added self-healing credits re-fetch block in combined-view eligible movies
- `backend/tests/test_game.py` - Appended regression test for BUG-08 step_order gap scenario

## Decisions Made
- Used `next()` with a generator expression for the forward-scan — idiomatic Python, returns `None` sentinel via default parameter
- Removed `step_by_order` dict entirely since it was only used in the now-replaced actor lookup
- Self-healing block guarded with `hasattr(request.app.state, "tmdb_client")` to prevent AttributeError in test environments
- Re-executing `actor_stmt` as `eligible_actor_rows2` (not reassigning `eligible_actor_rows`) to make the retry explicit and readable

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None - both fixes applied cleanly without complications.

## Known Stubs
None - no stubs or placeholders introduced in this plan.

## Next Phase Readiness
- BUG-07 and BUG-08 are resolved and regression-tested
- No blockers for subsequent plans

---
*Phase: 08-bug-fixes*
*Completed: 2026-03-31*
