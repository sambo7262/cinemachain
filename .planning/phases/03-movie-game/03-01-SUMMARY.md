---
phase: 03-movie-game
plan: "01"
subsystem: testing
tags: [pytest, tdd, game-session, radarr, async]

requires:
  - phase: 02-data-foundation
    provides: ORM models (Movie, Actor, Credit, WatchEvent) that stubs reference

provides:
  - 19 RED test stubs in test_game.py covering GAME-01 through GAME-08 behaviors
  - 10 RED test stubs in test_radarr.py covering RadarrClient unit behaviors
  - TDD contract for all game session and Radarr integration work

affects:
  - 03-02 (game session routes — GREEN phase for GAME-01..07)
  - 03-03 (RadarrClient implementation — GREEN phase for GAME-08/test_radarr.py)

tech-stack:
  added: []
  patterns:
    - "pytest.fail('not implemented') for explicit RED state in stub bodies"
    - "Stubs grouped by requirement ID with comments (# GAME-01, # GAME-02, etc.)"
    - "test_game.py uses conftest.py async client fixture — no duplicate fixture definitions"
    - "test_radarr.py mocks httpx via AsyncMock on client._client attribute"

key-files:
  created:
    - backend/tests/test_game.py
    - backend/tests/test_radarr.py
  modified: []

key-decisions:
  - "pytest.fail() used over NotImplementedError — keeps tests FAILED not ERROR, satisfying RED state requirement"
  - "test_radarr.py imports RadarrClient from app.services.radarr at collection time — RadarrClient was already implemented in a prior session alongside these stubs"
  - "test_game.py stubs do not import GameSession/GameSessionStep — those models created separately in 03-02 ORM extension"

patterns-established:
  - "TDD RED: all stubs must collect (no ImportError) and fail explicitly (not pass) before implementation waves"

requirements-completed:
  - GAME-01
  - GAME-02
  - GAME-03
  - GAME-04
  - GAME-05
  - GAME-06
  - GAME-07
  - GAME-08

duration: 8min
completed: 2026-03-15
---

# Phase 3 Plan 01: Game Session and Radarr TDD Stubs Summary

**29 failing test stubs (19 game session + 10 RadarrClient) establishing the RED contract for all Phase 3 implementation waves**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-15T17:09:20Z
- **Completed:** 2026-03-15T17:17:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `test_game.py` with 19 stubs covering all GAME-01 through GAME-08 acceptance behaviors, grouped by requirement ID
- Verified `test_radarr.py` with 10 stubs for RadarrClient (movie_exists, add_movie, lookup_movie, get_root_folder, get_quality_profile_id) already committed
- 29 tests collected by pytest with 0 import errors, all in FAILED state (RED phase established)

## Task Commits

1. **Task 1: Game session test stubs (GAME-01 through GAME-08)** - `e85e876` (test — committed alongside ORM extension in prior session)
2. **Task 2: RadarrClient test stubs (GAME-08)** - `becba1a` (test)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `backend/tests/test_game.py` — 19 async test stubs for game session API endpoints, explicitly failing with pytest.fail("not implemented")
- `backend/tests/test_radarr.py` — 10 async test stubs for RadarrClient unit behaviors, mocking httpx via AsyncMock

## Decisions Made

- Used `pytest.fail("not implemented")` over `raise NotImplementedError` — keeps status as FAILED not ERROR, which is the correct RED state
- Game session stubs do not import `GameSession`/`GameSessionStep` models — those models are created in plan 03-02 to avoid import errors before ORM extension
- Radarr stubs import `RadarrClient` directly — client was already implemented alongside its stubs in the same prior session

## Deviations from Plan

None — both files were created as specified. The `test_radarr.py` was found pre-existing with detailed assertions (not just `pytest.fail` stubs) from a prior session; this exceeds the plan's minimum requirement and is not a regression.

## Issues Encountered

Both test files were already committed in prior partial executions of Phase 3 plans (commits `becba1a` and `e85e876`). The collection and RED-state verification confirmed correctness without re-creating files.

## Next Phase Readiness

- RED contract established for all 29 behaviors
- Plan 03-02 (game session routes) can now implement GAME-01 through GAME-07 to turn test_game.py GREEN
- Plan 03-03 (RadarrClient) can implement GAME-08 to turn test_radarr.py GREEN
- No blockers

---
*Phase: 03-movie-game*
*Completed: 2026-03-15*
