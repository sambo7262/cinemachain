---
phase: 06-new-features
plan: "00"
subsystem: testing
tags: [tdd, wave-0, stubs, backend, frontend]
dependency_graph:
  requires: []
  provides: [wave-0-test-stubs]
  affects: [06-01, 06-02, 06-03]
tech_stack:
  added: []
  patterns: [pytest.mark.asyncio + client fixture, vitest + render + vi.mock]
key_files:
  created:
    - frontend/src/components/__tests__/ChainHistory.test.tsx
    - frontend/src/pages/__tests__/GameLobby.test.tsx
  modified:
    - backend/tests/test_game.py
    - backend/tests/test_settings.py
decisions:
  - "Used actual GameSessionStepDTO field names (poster_path, profile_path) in ChainHistory stubs instead of plan's placeholder names (actor_thumbnail, movie_thumbnail) to match the live type"
  - "Renamed test_request_movie_skip_radarr to test_request_movie_skip_radarr_field to avoid collision with existing test_request_movie_skip_radarr function in test_game.py"
metrics:
  duration_seconds: 137
  completed_date: "2026-03-22"
  tasks_completed: 2
  files_changed: 4
---

# Phase 6 Plan 00: Wave 0 Test Stubs Summary

Wave 0 RED-phase test stubs created for all new Phase 6 features — 5 backend stubs and 7 frontend stubs defining expected behavior before implementation begins.

## Tasks Completed

### Task 1: Backend test stubs
- Appended 4 async stubs to `backend/tests/test_game.py` after all existing tests
- Appended 1 async stub to `backend/tests/test_settings.py` after existing tests
- All use the `@pytest.mark.asyncio` + `client` fixture pattern from conftest.py
- Commit: 0a8a460

### Task 2: Frontend test stubs
- Created `frontend/src/components/__tests__/ChainHistory.test.tsx` with 3 search filter tests (Item 4)
- Created `frontend/src/pages/__tests__/GameLobby.test.tsx` with 4 session card stats tests (Item 8)
- Uses vitest + @testing-library/react + vi.mock pattern matching existing test files
- Commit: 401871a

## Stubs Created

| Stub | File | Feature | Fails Until |
|------|------|---------|-------------|
| test_csv_actor_name_resolved | test_game.py | ITEM-1: actor name resolution in CSV import | Plan 02 Task 2 |
| test_eligible_movie_overview_field | test_game.py | ITEM-2: overview field in EligibleMovieResponse | Plans 01/02 |
| test_request_movie_skip_radarr_field | test_game.py | ITEM-2: skip_radarr param on request-movie | Plan 02 Task 1 |
| test_rename_session | test_game.py | ITEM-3: PATCH /sessions/{id}/name endpoint | Plan 02 Task 1 |
| test_db_overrides_env | test_settings.py | ITEM-6: DB settings override .env | Plan 01 |
| ChainHistory search tests (3) | ChainHistory.test.tsx | ITEM-4: search filter in chain history | Plan 03 Task 2 |
| GameLobby card stats tests (4) | GameLobby.test.tsx | ITEM-8: session card stats display | Plan 03 Task 1 |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Adjusted ChainHistory stub prop shape to match actual type**
- **Found during:** Task 2
- **Issue:** Plan specified `actor_thumbnail` and `movie_thumbnail` as step props; actual `GameSessionStepDTO` uses `poster_path` and `profile_path`
- **Fix:** Used correct field names from api.ts type definition
- **Files modified:** frontend/src/components/__tests__/ChainHistory.test.tsx

**2. [Rule 1 - Bug] Renamed test_request_movie_skip_radarr stub to avoid name collision**
- **Found during:** Task 1
- **Issue:** An existing `test_request_movie_skip_radarr` test at line ~376 tests the "already in Radarr" skip behavior; the plan stub tests the `skip_radarr` request field
- **Fix:** Named the new stub `test_request_movie_skip_radarr_field` to distinguish the two behaviors
- **Files modified:** backend/tests/test_game.py

## Self-Check: PASSED

All created/modified files confirmed present. All task commits verified in git history.
