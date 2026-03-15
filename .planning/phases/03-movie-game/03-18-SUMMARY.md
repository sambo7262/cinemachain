---
phase: 03-movie-game
plan: 18
subsystem: infra, ui, api
tags: [docker, fastapi, react, tmdb, radarr, game-session, verification]

# Dependency graph
requires:
  - phase: 03-movie-game
    provides: "03-17 combined-view credits pre-fetch, isStartingMovie watch-first guidance, Radarr result notification"
provides:
  - "03-18 verification result: Test 1 (GAME-01 session start) PASS; Test 2 (GAME-03 combined view) FAIL; Tests 3-5 BLOCKED"
  - "Fresh Docker images built and pushed (sambo7262/cinemachain-*:latest, 2026-03-15)"
  - "Root cause identified: combined-view credits fetch is synchronous and times out for large casts"
  - "Flow redesign requirement: eligible actors/movies gated behind watched state; Radarr check fires at session start for starting movie"
  - "03-19 gap-closure plan required for: watched state gate, manual Mark as Watched, Radarr on session start, async credits pre-fetch, eligible movies pagination"
affects: ["03-19", "phase-3-closure", "game-session-verification"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Docker Hub push pattern: build locally with --no-cache, push to sambo7262/cinemachain-*:latest, NAS pulls on next compose pull"

key-files:
  created:
    - .planning/phases/03-movie-game/03-18-SUMMARY.md
  modified: []

key-decisions:
  - "GAME-01 session start guidance CONFIRMED WORKING: isStartingMovie derived state shows watch-first message correctly"
  - "GAME-03 combined-view eligible movies FAILS: synchronous TMDB credits fetch for all cast members times out on NAS hardware; never returns results"
  - "Flow redesign required: eligible actors/movies must be gated behind watched state (not shown until current movie marked watched)"
  - "Radarr check must fire at session START for the starting movie (not only on next-movie selection)"
  - "Manual Mark as Watched button required: user needs explicit in-UI action to advance watched state, separate from Plex webhook"
  - "Async/background credits pre-fetch on session creation: TMDB calls should fire asynchronously when session starts so data is ready when user opens Eligible Movies"
  - "Pagination required for eligible movies API: only fetch credits for first N actors on initial load, serve more on demand"

patterns-established:
  - "Pattern: Docker rebuild with --no-cache + push to Hub + NAS pull is the correct deploy cycle for NAS-targeted images"

requirements-completed: []

# Metrics
duration: 15min
completed: 2026-03-15
---

# Phase 3 Plan 18: Live NAS Verification (03-18) Summary

**GAME-01 session start guidance confirmed; GAME-03 combined-view times out on NAS; flow redesign and async pre-fetch required in 03-19**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-15T21:26:57Z
- **Completed:** 2026-03-15T21:42:00Z
- **Tasks:** 1 of 2 (Task 1 auto — Docker rebuild; Task 2 human verify — partial pass)
- **Files modified:** 0 (Docker build artifacts, no source changes)

## Accomplishments

- Docker images rebuilt from scratch (`--no-cache`) incorporating all 03-17 changes and pushed to Docker Hub
- Deployed to live NAS — all containers running
- Test 1 (GAME-01 session start): PASS — "Watch [Movie], then come back and pick an actor to begin the chain." displayed correctly at session start
- Root cause of GAME-03 failure identified: combined-view fetches TMDB credits for ALL cast members synchronously before returning any results; this reliably times out on NAS hardware for movies with large casts
- User-provided flow redesign captured and documented for 03-19

## Task Commits

Each task was committed atomically:

1. **Task 1: Rebuild and redeploy Docker images with 03-17 changes** - `2bdbcf7` (chore)
2. **Task 2: Human verify — five game-loop scenarios** — PARTIAL PASS — no code commit (verification outcome documented here)

## Files Created/Modified

- No source files created or modified in this plan
- Docker images `sambo7262/cinemachain-backend:latest` and `sambo7262/cinemachain-frontend:latest` rebuilt and pushed (2026-03-15 14:28 PDT)

## Verification Results

| Test | Requirement | Result | Notes |
|------|-------------|--------|-------|
| Test 1 — Session start guidance | GAME-01 | PASS | Watch-first message shown correctly |
| Test 2 — Combined eligible movies | GAME-03 | FAIL | "Loading eligible movies… credits are being fetched" spinner never resolves; synchronous cast credits fetch times out |
| Test 3 — Full move cycle + actor dedup | GAME-04 | BLOCKED | Could not reach this test due to Test 2 failure |
| Test 4 — Sort controls + watched toggle | GAME-05/06/07 | BLOCKED | Could not reach this test due to Test 2 failure |
| Test 5 — Radarr conditional notification | GAME-08 | BLOCKED | Could not reach this test due to Test 2 failure |

## Decisions Made

- GAME-01 session start guidance confirmed working — no further changes needed to `isStartingMovie` logic
- GAME-03 root cause: `_ensure_actor_credits_in_db` is called synchronously for every eligible actor in a single request; for movies with 20+ cast members this triggers 20+ sequential TMDB API calls before the first result is returned; this reliably exceeds NAS request timeout
- Flow redesign required (captured from live test feedback):
  1. Session begins → movie selected → **Radarr check fires for starting movie** (notify user if not in library)
  2. User watches the movie → uses **manual "Mark as Watched" button** in UI (or Plex webhook fires)
  3. **Only after movie is marked watched** do Eligible Actors and Eligible Movies tabs become active/visible
  4. User picks actor → picks next movie → Radarr check for next movie
  5. Repeat
- Async background credits pre-fetch: when a session is created, a background task should call `_ensure_actor_credits_in_db` for the starting movie's cast asynchronously so data is cached by the time the user opens Eligible Movies
- Pagination for eligible movies: only fetch credits for the first N actors on initial page load; return partial results immediately; load more on demand via pagination or infinite scroll

## Deviations from Plan

None — plan executed exactly as written. Partial pass outcome was the expected alternate path for this verification checkpoint.

## Issues Encountered

- `make rebuild` fails with `network synobridge declared as external, but could not be found` — this is expected on the local dev machine (synobridge only exists on NAS); images built and pushed to Docker Hub successfully; NAS deployment via `docker compose pull && docker compose up -d` on the NAS itself
- Backend image build: `python -c "import app.routers.game"` unavailable outside container (no asyncpg) — syntax-only verified via `python3 -m py_compile` in previous plans; image builds cleanly inside Docker

## User Setup Required

None — no new external service configuration required.

## Next Phase Readiness

03-18 is a PARTIAL PASS. Phase 3 remains open. A 03-19 gap-closure plan is required to address:

1. **Radarr check on session start** — fire Radarr check for the starting movie when session is created; surface notification if not in library
2. **Manual "Mark as Watched" button** — explicit in-UI action on the GameSession page so user can advance watched state without relying on Plex webhook
3. **Watched state gate on eligible actors/movies** — Eligible Actors and Eligible Movies tabs/content gated behind `session.current_movie_watched === true`; show locked state with message "Watch [Movie] to unlock the next step"
4. **Async/background credits pre-fetch on session creation** — when session is created, spawn background task to call `_ensure_actor_credits_in_db` for starting movie cast; data ready when user eventually opens Eligible Movies
5. **Pagination for eligible movies API** — `/game/{id}/eligible-movies` returns first N results immediately; subsequent pages fetched on demand; prevents synchronous timeout for large casts

---
*Phase: 03-movie-game*
*Completed: 2026-03-15*
