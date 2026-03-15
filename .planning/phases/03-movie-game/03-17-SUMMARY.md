---
phase: 03-movie-game
plan: 17
subsystem: ui, api
tags: [fastapi, react, typescript, tmdb, radarr, game-session]

# Dependency graph
requires:
  - phase: 03-movie-game
    provides: "game.py eligible-movies endpoint, GameSession.tsx session UI, _ensure_actor_credits_in_db helper"
provides:
  - "combined-view eligible-movies calls _ensure_actor_credits_in_db for each eligible actor before querying filmographies"
  - "isStartingMovie derived state: watch-first guidance instead of actor-pick prompt at session start"
  - "Radarr result surfaced to user as dismissible inline notification after movie selection"
  - "REQUIREMENTS.md traceability table reflects accurate partial-pass status"
affects: ["03-18", "phase-3-closure", "game-session-verification"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "combined-view credits pre-fetch: loop _ensure_actor_credits_in_db over eligible_actor_tmdb_ids before film_stmt query"
    - "requestResult capture: api.requestMovie returns { status } body, conditional radarrStatus notification in UI"
    - "isStartingMovie derived state: steps.length === 1 && lastStep.actor_tmdb_id === null"

key-files:
  created: []
  modified:
    - backend/app/routers/game.py
    - frontend/src/pages/GameSession.tsx
    - .planning/REQUIREMENTS.md

key-decisions:
  - "Combined-view branch now mirrors actor-scoped branch: tmdb declared in else block, loop calls _ensure_actor_credits_in_db for each eligible actor before filmography query"
  - "isStartingMovie: session.steps.length === 1 && lastStep.actor_tmdb_id === null — distinguishes session-start watch state from mid-chain actor-pick state"
  - "Confirm dialog wording changed to neutral 'Select X as your next movie?' — does not unconditionally promise Radarr add"
  - "radarrStatus state holds conditional feedback string: 'Added to Radarr queue.' or 'Already in your library — waiting for watched event.' based on requestResult.status"
  - "REQUIREMENTS.md traceability downgraded: GAME-01, GAME-03, GAME-08 Incomplete; GAME-04 through GAME-07 blocked pending GAME-01 live verification"

patterns-established:
  - "Pattern: Both actor-scoped and combined-view branches of get_eligible_movies now call _ensure_actor_credits_in_db before querying filmographies"

requirements-completed: [GAME-01, GAME-03, GAME-08]

# Metrics
duration: 3min
completed: 2026-03-15
---

# Phase 3 Plan 17: Gap-Closure Defects (Session State, Credits, Radarr) Summary

**Combined-view credits pre-fetch added to backend, watch-first session start guidance and conditional Radarr result notification added to frontend, REQUIREMENTS.md traceability corrected to partial-pass**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-15T21:22:05Z
- **Completed:** 2026-03-15T21:24:38Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Backend `get_eligible_movies` combined-view branch now calls `_ensure_actor_credits_in_db` for each eligible actor before querying their filmographies — fixes GAME-03 empty combined view on session mount
- Frontend session start state shows "Watch [Movie], then come back and pick an actor" via `isStartingMovie` derived state — fixes GAME-01 incorrect actor-pick prompt at session start
- Frontend captures `requestResult` from `api.requestMovie` and displays dismissible inline notification: "Added to Radarr queue." or "Already in your library — waiting for watched event." — fixes GAME-08 Radarr result not surfaced
- REQUIREMENTS.md traceability table updated to accurately reflect GAME-01, GAME-03, GAME-08 as Incomplete and GAME-04 through GAME-07 as blocked pending live verification

## Task Commits

Each task was committed atomically:

1. **Task 1: Backend — ensure cast credits before combined-view eligible-movies query** - `cfa7f9f` (feat)
2. **Task 2: Frontend — fix isStartingMovie state, empty-state message, and Radarr result notification** - `6c7aac5` (feat)
3. **Task 3: Update REQUIREMENTS.md traceability table to reflect partial status** - `171160b` (docs)

## Files Created/Modified

- `backend/app/routers/game.py` - Added `tmdb` declaration and `_ensure_actor_credits_in_db` loop in combined-view else branch before `if eligible_actor_tmdb_ids:`
- `frontend/src/pages/GameSession.tsx` - Added `isStartingMovie` derived state, updated state panel JSX, updated empty-state message, added `radarrStatus` state + notification, updated `handleMovieConfirm` confirm dialog wording and requestResult capture
- `.planning/REQUIREMENTS.md` - Downgraded GAME-01/03/04/05/06/07/08 checkboxes and traceability table entries; updated Last updated line

## Decisions Made

- Combined-view branch needed its own `tmdb: TMDBClient = request.app.state.tmdb_client` declaration — it was only declared inside the `if actor_id is not None:` block, so the `else:` block required a separate declaration
- `isStartingMovie` uses `session.steps.length === 1 && lastStep?.actor_tmdb_id === null` — precisely targets the session-start state; `isMovieSelected` already guards `steps.length > 1` so no overlap
- `api.requestMovie` in `api.ts` already typed as `apiFetch<{ status: string }>` — returns parsed JSON body; no changes to `api.ts` were needed
- Confirm dialog changed to "Select X as your next movie?" — neutral; the subsequent inline notification conveys the actual Radarr outcome

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- Local `python -c "import app.routers.game"` fails (missing `asyncpg` module outside container) — used `python3 -m py_compile` for syntax-only check; confirmed valid Python syntax

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Backend combined-view fix is live; 03-17 changes ready for live NAS verification
- Frontend session start guidance, empty-state, and Radarr notification changes ready for verification
- 03-18 should perform live end-to-end game flow verification: create session from movie search, verify watch-first guidance, pick actor, verify eligible movies populate, select movie, verify Radarr notification, verify session advance

---
*Phase: 03-movie-game*
*Completed: 2026-03-15*
