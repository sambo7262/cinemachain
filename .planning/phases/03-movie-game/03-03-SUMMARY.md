---
phase: 03-movie-game
plan: "03"
subsystem: api
tags: [radarr, httpx, async, tdd, python]

# Dependency graph
requires:
  - phase: 03-01
    provides: Game session scaffolding and project structure this service will be wired into
provides:
  - RadarrClient async httpx wrapper for Radarr API v3 with movie_exists, lookup_movie, add_movie, get_root_folder, get_quality_profile_id
affects:
  - game-session request-movie endpoint (03-04+) that calls RadarrClient to queue downloads

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "RadarrClient mirrors TMDBClient pattern: AsyncClient in constructor, X-Api-Key header auth, timeout=15.0"
    - "Python-side tmdbId filtering in movie_exists to handle Radarr bug #6086"
    - "HTTP 400 from POST /api/v3/movie treated as success sentinel {status: already_exists}"
    - "from __future__ import annotations for Python 3.9 union type hint compatibility"
    - "httpx.Response with explicit request= and content= for testable raise_for_status() in unit tests"

key-files:
  created:
    - backend/app/services/radarr.py
    - backend/tests/test_radarr.py
  modified: []

key-decisions:
  - "RadarrClient uses X-Api-Key header (not query param) — Radarr API v3 auth convention"
  - "movie_exists filters Python-side (not trusts server response) to handle Radarr bug #6086 where older installs return all movies for any tmdbId query"
  - "add_movie treats 400 as success not error — Radarr returns 400 on duplicate, not 409"
  - "from __future__ import annotations required for Python 3.9 dict | None union type syntax"
  - "httpx.Response needs explicit request= attribute for raise_for_status() to work in unit tests"

patterns-established:
  - "Radarr API v3 auth: X-Api-Key header (not query param like TMDB)"
  - "Async httpx client: base_url + headers in constructor, close() delegates to aclose()"
  - "TDD unit tests mock _client directly via AsyncMock, not via httpx.MockTransport"

requirements-completed: [GAME-08]

# Metrics
duration: 8min
completed: 2026-03-15
---

# Phase 3 Plan 03: RadarrClient Implementation Summary

**Async httpx RadarrClient with Python-side tmdbId filtering (Radarr bug #6086 fix) and 400-as-success add_movie semantics — 10 tests GREEN**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-15T17:22:45Z
- **Completed:** 2026-03-15T17:30:00Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments

- RadarrClient with all 6 methods: movie_exists, lookup_movie, add_movie, get_root_folder, get_quality_profile_id, close
- Python-side tmdbId filtering in movie_exists guards against Radarr bug #6086
- add_movie returns {"status": "already_exists"} on HTTP 400 — never raises
- 10 unit tests pass GREEN (plan specified 9 minimum)

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **RED — Failing tests** - `becba1a` (test)
2. **GREEN — RadarrClient implementation** - `85edcc7` (feat)

## Files Created/Modified

- `backend/app/services/radarr.py` - RadarrClient async httpx wrapper for Radarr API v3
- `backend/tests/test_radarr.py` - 10 unit tests covering all methods and edge cases

## Decisions Made

- Used `from __future__ import annotations` to support Python 3.9 `dict | None` union syntax (discovered during GREEN run — Python 3.9 doesn't support X | Y at class definition time)
- Tests mock `client._client` directly with `AsyncMock` rather than using `httpx.MockTransport` — simpler and matches plan guidance
- `httpx.Response` requires explicit `request=` and `content=` arguments for `raise_for_status()` to work correctly in unit tests

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Python 3.9 union type hint syntax unsupported**
- **Found during:** Task 1 (GREEN phase — first test run after creating radarr.py)
- **Issue:** `dict | None` return type annotation causes `TypeError` at class body parse time in Python 3.9; only supported in 3.10+
- **Fix:** Added `from __future__ import annotations` to radarr.py (defers annotation evaluation)
- **Files modified:** backend/app/services/radarr.py
- **Verification:** `python3 -c "from app.services.radarr import RadarrClient; print('ok')"` succeeds
- **Committed in:** 85edcc7 (feat commit)

**2. [Rule 1 - Bug] httpx.Response helper missing request attribute**
- **Found during:** Task 1 (GREEN phase — first test run)
- **Issue:** `httpx.Response(status_code=200, json=...)` does not set `_request`, causing `raise_for_status()` to throw `RuntimeError: Cannot call raise_for_status as the request instance has not been set`
- **Fix:** Updated `_make_response` helper in test_radarr.py to pass `request=_DUMMY_REQUEST`, `content=json.dumps(body).encode()`, and `headers={"content-type": "application/json"}`
- **Files modified:** backend/tests/test_radarr.py
- **Verification:** All 10 tests pass GREEN
- **Committed in:** 85edcc7 (feat commit — test helper fix included)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bugs found during GREEN implementation run)
**Impact on plan:** Both fixes essential for tests to run. No scope creep.

## Issues Encountered

- pytest-asyncio not installed in system Python 3.9 — installed from requirements.txt during execution (Rule 3 auto-fix)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- RadarrClient importable from `app.services.radarr` — ready to wire into game session endpoint
- Constructor signature `(base_url: str, api_key: str)` matches `settings.radarr_url` / `settings.radarr_api_key`
- No blockers

---
*Phase: 03-movie-game*
*Completed: 2026-03-15*
