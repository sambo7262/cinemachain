---
phase: 05-bug-fixes
plan: 01
subsystem: testing
tags: [pytest, asyncpg, tdd, backend, game]

# Dependency graph
requires:
  - phase: 04.3-bug-fixes-and-ux-refinements
    provides: asyncpg-skip test pattern established in test_game.py
provides:
  - Wave 0 RED-phase test stubs for BUG-1, BUG-3, BUG-4, ENH-1 in test_game.py
affects: [05-02, 05-03, 05-04, 05-05]

# Tech tracking
tech-stack:
  added: []
  patterns: [asyncpg-skip pattern for Docker-only tests, unittest.mock.patch inside asyncpg-skip block]

key-files:
  created: []
  modified:
    - backend/tests/test_game.py

key-decisions:
  - "BUG-1 stubs use request-movie without prior pick-actor to trigger auto-resolution or disambiguation path"
  - "BUG-3 stub seeds actor exclusive to previous movie and asserts it is absent from eligible-actors response"
  - "BUG-4 canonical name stub uses mock.patch at game module level to control _resolve_actor_tmdb_id return value"
  - "BUG-4 roundtrip stub exercises full export-then-reimport cycle with mocked TMDB resolvers"
  - "ENH-1 stub patches _prefetch_actor_credits_background and asserts call_count > 0 after pick-actor"

patterns-established:
  - "asyncpg-skip: skip locally when asyncpg absent, fail in Docker until fix is live"
  - "mock.patch inside asyncpg-skip try block for TMDB-dependent CSV import tests"

requirements-completed: [BUG-1, BUG-3, BUG-4, ENH-1]

# Metrics
duration: 10min
completed: 2026-03-22
---

# Phase 5 Plan 01: Wave 0 Test Stubs Summary

**Six asyncpg-skip RED-phase stubs for BUG-1 auto-actor/disambiguation, BUG-3 eligibility scoping, BUG-4 CSV canonical name + roundtrip, and ENH-1 actor precache appended to test_game.py**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-22T03:52:07Z
- **Completed:** 2026-03-22T04:02:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Appended 2 BUG-1 stubs: auto-actor single and multi-actor disambiguation detection
- Appended 4 stubs: BUG-3 (eligibility scoping), BUG-4 canonical name, BUG-4 roundtrip, ENH-1 precache
- All 6 stubs collected by pytest (46 total, 0 errors), skip locally (asyncpg absent)

## Task Commits

Each task was committed atomically:

1. **Task 1: Append BUG-1 test stubs** - `34d505c` (test)
2. **Task 2: Append BUG-3, BUG-4, ENH-1 test stubs** - `fffb908` (test)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `backend/tests/test_game.py` - Six new test functions appended (lines 1028–end)

## Decisions Made
- BUG-1 stubs call request-movie without a prior pick-actor call to trigger the auto-resolution code path (the bug fix path, not the normal game flow)
- BUG-4 canonical name test uses `unittest.mock.patch` at `app.routers.game._resolve_actor_tmdb_id` to return `(99001, "Canonical Name From TMDB")`, isolating the test from live TMDB calls
- BUG-4 roundtrip test exports from a pre-seeded session, parses the CSV, and re-imports via mocked resolvers — verifies no duplicates and no blank actor_name
- ENH-1 stub patches `_prefetch_actor_credits_background` at the module level and checks `call_count > 0` after pick-actor completes

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Wave 0 stubs are GREEN locally (skip). In Docker they will be RED until Wave 1 implements fixes.
- Plan 05-02 (Wave 1 backend fixes) can proceed immediately — stubs define the contract.

---
*Phase: 05-bug-fixes*
*Completed: 2026-03-22*
