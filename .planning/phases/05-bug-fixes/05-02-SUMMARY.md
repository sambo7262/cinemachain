---
phase: 05-bug-fixes
plan: 02
subsystem: api
tags: [fastapi, tmdb, background-tasks, sqlalchemy, game]

# Dependency graph
requires:
  - phase: 05-bug-fixes-01
    provides: BUG-3/BUG-4/ENH-1 wave-0 test stubs in test_game.py
provides:
  - BUG-3 eligibility scope confirmed correct with invariant comments
  - BUG-4 canonical TMDB actor name stored in CSV import via tuple return
  - ENH-1 _prefetch_actor_credits_background background task on pick_actor
affects: [05-bug-fixes-03, 05-bug-fixes-04, 05-bug-fixes-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_prefetch_actor_credits_background mirrors _prefetch_credits_background pattern (background session, errors suppressed)"
    - "_resolve_actor_tmdb_id returns (tmdb_id, canonical_name) tuple — canonical name from TMDB search results stored in steps_data"
    - "ELIGIBILITY SCOPE INVARIANT comment pattern for documenting query scope guarantees"

key-files:
  created: []
  modified:
    - backend/app/routers/game.py

key-decisions:
  - "BUG-3 queries are correct as written — symptom was a data integrity issue (stale Credit rows), not query logic; scope invariant comments added for future reference"
  - "NAS DB diagnostic for stale Chalamet/The Menu Credit rows could not run from dev machine (SSH alias 'nas' not resolvable); diagnostic command documented in plan for manual execution"
  - "_resolve_actor_tmdb_id changed to return tuple[int | None, str | None] — canonical_name from TMDB search results used in steps_data with fallback to raw CSV actorName"
  - "pick_actor gains Request + BackgroundTasks params — tmdb_client fetched from request.app.state after db.commit() before re-fetch"

patterns-established:
  - "Background pre-fetch pattern: wrap _ensure_*_in_db in _prefetch_*_background with try/except pass and _bg_session_factory"
  - "Canonical name pattern: TMDB API returns verified spellings — always store canonical over raw user input"

requirements-completed: [BUG-3, BUG-4, ENH-1]

# Metrics
duration: 5min
completed: 2026-03-22
---

# Phase 5 Plan 02: BUG-3/BUG-4/ENH-1 Backend Fixes Summary

**Eligibility query scope confirmed correct; CSV import now stores TMDB canonical actor names via tuple return; pick_actor enqueues actor filmography pre-cache background task after commit**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-22T03:56:18Z
- **Completed:** 2026-03-22T03:58:00Z
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments
- BUG-3: Confirmed both `get_eligible_actors` and `get_eligible_movies` combined-view queries are correctly scoped to `current_movie_tmdb_id`; added ELIGIBILITY SCOPE INVARIANT comment blocks documenting the guarantee
- BUG-4: Changed `_resolve_actor_tmdb_id` to return `tuple[int | None, str | None]` (tmdb_id, canonical_name); `import_csv_session` now stores `canonical_name or row.actorName` in steps_data
- ENH-1: Added `_prefetch_actor_credits_background` function and wired it into `pick_actor` via `background_tasks.add_task` after `db.commit()` to pre-warm eligible movies data

## Task Commits

Each task was committed atomically:

1. **Task 1: BUG-3 — Verify eligibility query scope and diagnose/remediate stale Credit rows** - `5251efb` (fix)
2. **Task 2: BUG-4 — Fix CSV import to store canonical TMDB actor name** - `e2b0a10` (fix)
3. **Task 3: ENH-1 — Add actor pre-cache background task to pick_actor** - `c0c8eee` (feat)

## Files Created/Modified
- `backend/app/routers/game.py` - BUG-3 scope comments, BUG-4 canonical name tuple, ENH-1 background task function + pick_actor wiring

## Decisions Made
- BUG-3 queries were already correct — no query changes needed, only comments added. Symptom (Chalamet appearing after The Menu) was a data integrity issue (stale Credit rows in NAS DB)
- NAS DB diagnostic command was documented but could not be executed from dev machine (SSH alias 'nas' not resolvable); user must run manually: `ssh nas "docker exec cinemachain-db psql -U app -d cinemachain -c \"SELECT ... FROM credits WHERE m.tmdb_id = 508947 AND a.name ILIKE '%chalamet%'\""`
- `pick_actor` signature updated to add `Request` and `BackgroundTasks` — both were already imported at top of game.py, no new imports needed

## Deviations from Plan

None - plan executed exactly as written. The NAS DB diagnostic was attempted but blocked by SSH connectivity (not an unplanned deviation — the plan noted this as an operational step requiring SSH access).

## Issues Encountered
- NAS SSH alias `nas` not resolvable from dev machine. The diagnostic command is documented in 05-02-PLAN.md for manual execution. All three code changes (BUG-3 comments, BUG-4 tuple, ENH-1 background task) were completed successfully without NAS access.

## User Setup Required
None — no external service configuration required.

**Manual action needed:** Run the NAS DB diagnostic to check for stale Credit rows linking Timothee Chalamet (or similar actors) to The Menu (TMDB ID 508947). See step 4 in Task 1 of 05-02-PLAN.md for the exact SQL commands.

## Next Phase Readiness
- All three backend fixes deployed; ready for wave-3 NAS deployment and verification
- BUG-3/BUG-4/ENH-1 test stubs (from 05-01) will pass in Docker with asyncpg

---
*Phase: 05-bug-fixes*
*Completed: 2026-03-22*
