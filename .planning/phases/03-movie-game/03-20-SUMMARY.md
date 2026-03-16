---
phase: 03-movie-game
plan: 20
subsystem: ui
tags: [react, typescript, vite, docker, game-session, pagination, radarr]

# Dependency graph
requires:
  - phase: 03-movie-game
    plan: 19
    provides: "Backend watched gate (HTTP 423), mark-current-watched endpoint, Radarr-on-start, async credits pre-fetch, eligible-movies pagination"
provides:
  - "frontend/src/lib/api.ts updated with PaginatedMoviesDTO, markCurrentWatched, GameSessionDTO.current_movie_watched"
  - "GameSession.tsx: watched gate on Eligible Actors/Movies tabs, Mark as Watched button, radarr_status from location.state, Load More pagination"
  - "GameLobby.tsx: passes radarr_status in router state on session creation"
affects: [03-21-gap-closure]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "location.state used to pass radarr_status from create-session response into GameSession on mount"
    - "isWatched derived from session.current_movie_watched — single boolean gates both eligible tabs"
    - "PaginatedMoviesDTO envelope — eligible-movies now returns items/total/page/page_size/has_more"

key-files:
  created: []
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/pages/GameSession.tsx
    - frontend/src/pages/GameLobby.tsx

key-decisions:
  - "Partial pass: 2 of 5 test scenarios passed; 03-21 gap plan required to resolve remaining failures"
  - "Remove Plex webhook integration entirely — all movies will be marked watched manually via Mark as Watched button (new requirement from user)"
  - "After selecting next movie and confirming, user should be taken to a session home page showing current and previous movie in chain (new UX requirement)"
  - "Eligible Actors tab failure is complete (no data ever populated) — root cause unknown; must be diagnosed in 03-21"
  - "State machine cycling defect found: clicking Continue the chain reverts UI back to Mark as Watched state instead of remaining in actor-selection mode"
  - "Radarr notification (GAME-08) not surfacing in UI — frontend not reading radarr_status from location.state correctly"

patterns-established:
  - "location.state pattern for passing create-session response fields into downstream pages"

requirements-completed: []

# Metrics
duration: partial
completed: 2026-03-15
---

# Phase 3 Plan 20: Frontend Watched Gate + Mark as Watched + Pagination Summary

**Partial pass: frontend watched gate, Mark as Watched button, and pagination wired; Radarr notification, Eligible Actors data, state machine sequencing, and sort/thumbnail remain broken — 03-21 gap-closure required**

## Performance

- **Duration:** Multiple sessions across 03-20 execution
- **Started:** 2026-03-15
- **Completed:** 2026-03-15 (partial — verification failed)
- **Tasks:** 2 of 3 (checkpoint task reached, partial pass received)
- **Files modified:** 3

## Accomplishments

- Updated `api.ts` with `PaginatedMoviesDTO`, `markCurrentWatched`, and `GameSessionDTO.current_movie_watched` / `radarr_status` fields
- Updated `GameSession.tsx` with watched gate on both eligible tabs, `isWatched` derivation, `markWatchedMutation`, `moviesPage` pagination state, Load More button, and `radarrStatus` initialized from `location.state`
- Updated `GameLobby.tsx` to pass `radarr_status` in React Router state on session creation for all three start-session paths
- Test 5 (pagination — Load More) passed on NAS hardware
- Mark as Watched button fires correctly and triggers Eligible Movies tab to open
- Docker images built and deployed in prior plan (03-19 rebuild); no rebuild needed for 03-20

## Task Commits

1. **Task 1: Update api.ts — new types, markCurrentWatched, paginated eligible movies** — `77dccc0` (feat)
2. **Task 2: Update GameSession.tsx — watched gate, Mark as Watched button, Radarr start notification, pagination** — `cd440b2` (feat)
3. **Task 3: Docker rebuild + human verify** — CHECKPOINT (partial pass received — no code commit)

## Files Created/Modified

- `frontend/src/lib/api.ts` — Added `PaginatedMoviesDTO`, `markCurrentWatched`, updated `GameSessionDTO` with `current_movie_watched` and `radarr_status`, updated `getEligibleMovies` to return paginated envelope
- `frontend/src/pages/GameSession.tsx` — Watched gate on Eligible Actors/Movies tabs, Mark as Watched button in both `isStartingMovie` and `isMovieSelected` branches, `radarrStatus` initialized from `location.state`, `moviesPage` pagination, Load More button
- `frontend/src/pages/GameLobby.tsx` — Passes `radarr_status` in router state when navigating to session page from all create-session paths

## Decisions Made

- Partial pass accepted; 03-21 gap plan to be written by orchestrator
- Two new user requirements captured for 03-21 scope:
  1. Remove Plex webhook integration entirely — all watched events will be manual via Mark as Watched button
  2. After movie selection confirmation, navigate to a "session home page" showing current movie and previous movie in the chain

## Deviations from Plan

None — plan executed as written. Failures are verification failures (bugs in the implementation), not deviations from the plan spec.

---

**Total deviations:** 0
**Impact on plan:** No scope creep. Verification partial pass.

## Verification Results (NAS Hardware — 2026-03-15)

### PASSED

| Test | Requirement | Result |
|------|-------------|--------|
| Test 5: Pagination | GAME-03 (partial) | PASS — Load More button visible and working |
| Mark as Watched button | GAME-01 (partial) | PASS — button fires correctly, Eligible Movies tab opens |

### FAILED

| # | Test | Requirement | Failure Description |
|---|------|-------------|---------------------|
| 1 | Radarr notification | GAME-08 | Movie added to Radarr queue via API but NO notification shown in UI. Frontend not surfacing `radarr_status` from `location.state`. |
| 2 | Eligible Actors tab | GAME-02, GAME-04 | Never populated data at any point during testing — complete failure. Root cause unknown. |
| 3 | State machine sequencing | GAME-01 | After Mark as Watched → Continue the chain → button reverted back to "Mark as Watched". State machine cycling incorrectly. Once Continue the chain is clicked, should stay in actor-selection mode. |
| 4 | Actor dedup | GAME-04 | Blocked by Eligible Actors failure — could not execute. |
| 5 | Sorting | GAME-05 | Not effective — not all results populated across tabs. |
| 6 | Thumbnail size | N/A | Eligible Movies thumbnails too small — need to be bigger. |

### Blocked Tests

- Tests 3 and 4 (GAME-04, GAME-05, GAME-06, GAME-07) blocked by Eligible Actors tab complete failure.

## New Requirements Captured (for 03-21)

1. **Remove Plex webhook integration entirely** — all movies will be marked watched manually via the Mark as Watched button. The Plex webhook receiver, `media.scrobble` handler, and `_maybe_advance_session` Plex path should be removed or disabled.

2. **Session home page after movie confirmation** — after a user selects a next movie and confirms, they should be taken to a dedicated "session home page" that shows:
   - What movie is currently next (the current movie in the chain)
   - What movie was previously in the chain
   - This is the homebase of the session UX

## Issues Encountered

- Radarr notification not surfacing: `location.state?.radarr_status` not being read correctly on mount — likely a GameLobby navigate call passing state in a form React Router does not retain, or GameSession not reading it before state clears.
- Eligible Actors tab complete failure: no data ever populates. Backend eligible-actors endpoint may be failing silently, or the frontend query may be disabled incorrectly (isWatched gate may not be evaluating to true when expected).
- State machine reversion: `awaiting_continue` status transitions may be cycling back to `active` with `current_movie_watched=false` on Continue the chain, causing the UI to show Mark as Watched again.

## Next Phase Readiness

Not ready to close Phase 3. A 03-21 gap-closure plan is required addressing:

1. Fix Radarr notification — ensure `radarr_status` is passed in router state and read in GameSession
2. Fix Eligible Actors tab — diagnose why no data populates (backend 423 gate still active? query disabled? API error swallowed?)
3. Fix state machine cycling — Continue the chain must leave user in actor-selection mode permanently
4. Implement session home page (new UX requirement)
5. Remove Plex webhook integration
6. Fix sorting (GAME-05)
7. Increase Eligible Movies thumbnail size
8. Retest GAME-04 actor dedup after Eligible Actors is fixed

---
*Phase: 03-movie-game*
*Completed: 2026-03-15 (partial pass)*
