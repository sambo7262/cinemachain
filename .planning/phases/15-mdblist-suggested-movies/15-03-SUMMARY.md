---
plan: 15-03
phase: 15-mdblist-suggested-movies
status: complete
subsystem: backend/game-router
tags: [suggestions, tmdb, eligible-pool, game-session]
dependency_graph:
  requires: [15-01, 15-02]
  provides: [GET /game/sessions/{session_id}/suggestions]
  affects: [backend/app/routers/game.py]
tech_stack:
  added: []
  patterns: [eligible-pool-intersection, settings-guard, tmdb-client-lifecycle]
key_files:
  modified:
    - backend/app/routers/game.py
decisions:
  - "settings_service imported in game.py for the first time — provides access to tmdb_api_key and tmdb_suggestions_seed_count guards without changing existing router patterns"
  - "Eligible pool built inline with 4 targeted SQL queries rather than reusing get_eligible_movies DTO to avoid full response construction overhead"
metrics:
  duration: ~10 minutes
  completed: 2026-04-01
  tasks_completed: 1
  files_modified: 1
---

# Phase 15 Plan 03: Add GET /sessions/{id}/suggestions Endpoint Summary

Added `GET /game/sessions/{session_id}/suggestions` endpoint to game router — returns TMDB-recommended movie IDs (ranked by watch frequency) intersected with the session's current eligible movie pool.

## Summary

- Added `SuggestionsResponse` Pydantic model to `game.py` response schemas section
- Added `GET /sessions/{session_id}/suggestions` endpoint with eligible pool intersection logic
- Eligible pool built via 4-step SQL query: used actors → chain movies → eligible actors → eligible movies
- Guards return empty list (never 500) when `tmdb_api_key` unset or `tmdb_suggestions_seed_count` = 0
- Returns 404 only when session does not exist
- Added `settings_service` import and added `get_session_suggestions` to existing suggestions import

## Verification

Python 3.12 is only available inside Docker (Dockerfile: `FROM python:3.12-slim`); local system has Python 3.9 which cannot evaluate `|` union type annotations. Syntax compilation check passed:

```
python3 -m py_compile backend/app/routers/game.py
# → syntax OK (exit 0)
```

Static verification of changes:
- `from app.services import settings_service` — present at line 23
- `from app.services.suggestions import _update_session_suggestions, get_session_suggestions` — present at line 24
- `class SuggestionsResponse(BaseModel)` — present at lines 68-69
- `@router.get("/sessions/{session_id}/suggestions", response_model=SuggestionsResponse)` — present at line 1298
- `async def get_session_suggestions_endpoint(` — present at line 1299
- Existing `_update_session_suggestions` usage at line 1277 — intact, not broken

## Deviations from Plan

**1. [Rule 2 - Missing Import] Added settings_service import**
- Found during: Task 1
- Issue: `settings_service` was not imported in `game.py` (plan context showed it already present but it was not)
- Fix: Added `from app.services import settings_service` above the suggestions import
- Files modified: `backend/app/routers/game.py`
- Commit: 53a9390

All other planned imports (`Actor`, `Credit`, `GameSession`, `GameSessionStep`, `Movie`, `select`, `sa`, `TMDBClient`) were already present. No other deviations.

## Self-Check: PASSED

- `backend/app/routers/game.py` — modified and committed at 53a9390
- Commit 53a9390 exists in git log
