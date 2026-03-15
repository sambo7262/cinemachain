---
phase: 02-data-foundation
plan: 01
subsystem: testing
tags: [pytest, asyncio, tmdb, plex, fastapi, httpx]

# Dependency graph
requires: []
provides:
  - Wave 0 failing test stubs for DATA-01 through DATA-06
  - Behavioral contracts defined as named pytest functions for all six data requirements
  - Skip-safe test infrastructure that activates once app.main is implemented
affects:
  - 02-data-foundation (plans 02-03, 02-04, 02-05 must make these tests green)
  - 03-movie-game
  - 04-query-mode

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Wave 0 TDD pattern: define behavioral contracts as skip-safe failing tests before any implementation"
    - "conftest client fixture uses try/except ImportError with pytest.skip guard for pre-implementation safety"

key-files:
  created:
    - backend/tests/test_tmdb.py
    - backend/tests/test_plex_sync.py
    - backend/tests/test_plex_webhook.py
    - backend/tests/test_movies.py
  modified: []

key-decisions:
  - "DATA-05 webhook test uses data= (multipart/form-data) not json= — matches actual Plex payload format"
  - "Scrobble idempotency test verifies ON CONFLICT DO NOTHING behavior with double-fire scenario"
  - "DATA-03 cache test verifies via fetched_at timestamp stability, not mock call count"

patterns-established:
  - "Wave 0 test stubs: syntactically valid Python, skip gracefully until app.main exists, document exact behavioral contract in docstring"
  - "Plex webhook tests: always send multipart/form-data via data= param, never application/json"

requirements-completed: [DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06]

# Metrics
duration: 2min
completed: 2026-03-15
---

# Phase 2 Plan 01: Data Foundation Wave 0 Summary

**Four pytest stub files defining behavioral contracts for DATA-01 through DATA-06 using skip-safe asyncio test functions**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-15T14:49:49Z
- **Completed:** 2026-03-15T14:52:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Created test_tmdb.py with three stubs: DATA-01 (fetch_movie_details), DATA-02 (fetch_actor_credits), DATA-03 (movie_cached_on_repeat_request)
- Created test_plex_sync.py with one stub: DATA-04 (startup_sync_marks_watched)
- Created test_plex_webhook.py with three stubs: DATA-05 (scrobble_marks_watched, scrobble_is_idempotent, non_scrobble_event_ignored)
- Created test_movies.py with two stubs: DATA-06 (manual_mark_watched, manual_mark_watched_is_idempotent)
- All four files compile without errors via py_compile

## Task Commits

Each task was committed atomically:

1. **Task 1: Write test stubs for TMDB service and Plex sync (DATA-01 through DATA-04)** - `aec6f54` (test)
2. **Task 2: Write test stubs for Plex webhook and manual mark watched (DATA-05, DATA-06)** - `c688dcb` (test)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `backend/tests/test_tmdb.py` - Failing stubs for DATA-01 (movie details), DATA-02 (actor filmography), DATA-03 (DB cache hit on repeat)
- `backend/tests/test_plex_sync.py` - Failing stub for DATA-04 (startup Plex library sync writes watch_events)
- `backend/tests/test_plex_webhook.py` - Failing stubs for DATA-05 (scrobble marks watched, idempotency, non-scrobble ignored)
- `backend/tests/test_movies.py` - Failing stubs for DATA-06 (manual PATCH /movies/{id}/watched, idempotency)

## Decisions Made

- DATA-05 webhook tests use `data={"payload": ...}` (multipart/form-data) not `json=` — this matches the actual Plex webhook format and the FastAPI `Form(...)` requirement documented in CONTEXT.md
- DATA-03 cache verification uses `fetched_at` timestamp comparison rather than mock call counting, keeping the test black-box and decoupled from internal implementation
- Idempotency tests for both DATA-05 and DATA-06 explicitly exercise the ON CONFLICT DO NOTHING semantics that Wave 2 must implement

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

pytest itself was not on PATH in the local environment (missing httpx module would also prevent collection until Wave 1 installs dependencies). All four files were verified syntactically valid via `python3 -m py_compile`, which is the Wave 0 success criterion. Full pytest collection will succeed once Wave 1 creates app.main and the test environment has its dependencies installed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All six DATA requirement contracts are now defined as named, runnable test functions
- Plans 02-03 (TMDB routes), 02-04 (Plex sync), and 02-05 (webhook + manual mark) have concrete verify commands pointing at these stubs
- Existing conftest.py skip-guard pattern (`try: from app.main import app; except ImportError: pytest.skip(...)`) means all stubs fail gracefully until app.main exists

---
*Phase: 02-data-foundation*
*Completed: 2026-03-15*
