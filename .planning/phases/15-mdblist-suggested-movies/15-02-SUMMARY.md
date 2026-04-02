---
plan: 15-02
phase: 15-mdblist-suggested-movies
status: complete
subsystem: backend/suggestions
tags: [tmdb, recommendations, background-tasks, caching]
dependency_graph:
  requires: [15-01]
  provides: [suggestions-service, fetch-and-cache, bg-task-wiring]
  affects: [backend/app/routers/game.py]
tech_stack:
  added: []
  patterns: [fetch-and-cache, frequency-ranking, background-task-pattern]
key_files:
  created:
    - backend/app/services/suggestions.py
    - backend/tests/test_suggestions.py
  modified:
    - backend/app/services/tmdb.py
    - backend/app/routers/game.py
decisions:
  - "Cache writes empty list [] (not None) on zero-result TMDB response to prevent re-fetching"
  - "get_session_suggestions excludes seed movie IDs from ranked results"
  - "_update_session_suggestions reads api_key and seed_count internally via settings_service"
metrics:
  duration: ~10min
  completed: 2026-04-01
  tasks_completed: 2
  files_created: 2
  files_modified: 2
---

# Phase 15 Plan 02: Suggestions Service Summary

TMDB recommendations service with fetch-and-cache, frequency-ranked aggregation, and background task wiring.

## Summary
- Added `TMDBClient.fetch_recommendations` to `backend/app/services/tmdb.py`
- Created `backend/app/services/suggestions.py` with `fetch_and_cache_recommendations`, `get_session_suggestions`, `_update_session_suggestions`
- Created `backend/tests/test_suggestions.py` with 6 passing unit tests
- Wired `_update_session_suggestions` into `mark_current_watched` in `game.py`

## Verification

```
$ python3 -c "from app.services.suggestions import fetch_and_cache_recommendations, get_session_suggestions, _update_session_suggestions; from app.services.tmdb import TMDBClient; assert hasattr(TMDBClient, 'fetch_recommendations'); print('imports OK')"
imports OK

$ python3 -c "import ast, pathlib; src = pathlib.Path('app/routers/game.py').read_text(); assert '_update_session_suggestions' in src; print('wired OK')"
wired OK

$ python3 -m pytest tests/test_suggestions.py -x -q
......
6 passed in 0.58s
```

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED
- `backend/app/services/suggestions.py` — FOUND
- `backend/tests/test_suggestions.py` — FOUND
- `backend/app/services/tmdb.py` contains `fetch_recommendations` — FOUND
- `backend/app/routers/game.py` contains `_update_session_suggestions` — FOUND
- Commit `2c1adb4` — FOUND
