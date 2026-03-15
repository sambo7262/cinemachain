---
phase: 03-movie-game
plan: "16"
subsystem: ui
tags: [react, typescript, game-session, verification, state-machine]

# Dependency graph
requires:
  - phase: 03-movie-game
    provides: Session lifecycle fixes (03-14) and NavBar + state machine UI (03-15)
provides:
  - Verification record for Phase 3 GAME requirements
  - Detailed root-cause analysis of session state machine flow defect
  - Specification of correct session flow for 03-17 planning
affects: [03-17]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified: []

key-decisions:
  - "Phase 3 not closed — GAME-01 (session start) and GAME-03 (eligible movies on mount) FAIL due to fundamental state machine flow mismatch; 03-17 required"
  - "Root cause: UI prompts actor selection immediately after movie search, but correct flow is: movie selection creates session → user watches → user picks actor → user picks next movie → THEN Radarr queried"
  - "Radarr query timing is also wrong: query should only fire when user picks the NEXT movie (step 5), and only if that movie is not already in Radarr — not at session creation"

patterns-established: []

requirements-completed: []

# Metrics
duration: 15min
completed: 2026-03-15
---

# Phase 3 Plan 16: Final Re-Verification Summary

**PARTIAL PASS — Items 1-2 pass (End Session clear works); Items 3-4 and 5-10 blocked by session state machine flow defect requiring 03-17**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-15T20:42:45Z
- **Completed:** 2026-03-15T20:57:00Z
- **Tasks:** 1 of 2 (Task 1 complete; Task 2 checkpoint — partial pass, defect found)
- **Files modified:** 0

## Accomplishments

- Frontend build confirmed clean: TypeScript + Vite build passes, 0 errors, 1886 modules transformed
- Production bundle confirmed to contain all 03-14 and 03-15 changes (`setQueryData`, `eligible-movies`, `Show all eligible movies`, `Start a new session`, `CinemaChain`, `Session paused`)
- Backend test suite: 20 passed / 3 skipped / 29 failed — all failures are DB connection errors (no live PostgreSQL in dev env); matches 03-13 baseline, no regressions
- GAME-01 end-session (Item 2): PASS — setQueryData fix confirmed working; banner clears immediately
- NavBar persistence (Item 1): PASS — NavBar with CinemaChain logo and Sessions link visible on all pages

## Verification Results

| Item | Check | Result |
|------|-------|--------|
| 1 | NavBar visible at `/` with CinemaChain logo and Sessions link | PASS |
| 2 | End Session — banner clears immediately without reload | PASS |
| 3 | Start a new session from lobby — no 409 error, navigates to `/game/{id}` | FAIL |
| 4 | Eligible Movies tab populates without actor selection | FAIL |
| 5-10 | Sort controls, watched toggle, actor dedup, state machine | BLOCKED |

## Failures — Root Cause Analysis

### Item 3: Start new session (GAME-01 partial)

**Expected:** User selects a movie from Watch History or Search → session is created with that movie as the starting point in the chain → UI reflects "movie selected, unwatched" state, showing all eligible actors from that movie's cast.

**Actual:** After typing "Cast Away" and selecting it, the UI immediately prompts "select an actor." This is the wrong state — at session start, no actor has been picked yet. The session state machine implementation conflates "session created with starting movie" with "actor selected, pick next movie."

### Item 4: Eligible Movies combined view on mount (GAME-03)

**Expected:** When the session is in "movie selected, unwatched" state (no actor picked yet), the Eligible Movies tab should show ALL movies from ALL cast members of the current movie — since all actors are still eligible.

**Actual:** The tab shows an empty state or requires actor selection first, because the current implementation gates the eligible-movies query on an actor being selected. At session start (starting movie, no actor chosen), `actor_id` is undefined and the combined view does not load correctly in this context.

## Correct Session State Machine Flow

The following is the verified correct flow (from live testing feedback):

1. **User searches for a movie** — no session exists yet (lobby state)
2. **User selects the movie** → session is CREATED with that movie as the first link in the chain. State becomes `movie_selected_unwatched`. No actor selection at this point. The starting movie is presumed already owned — Radarr is NOT queried.
3. **At this stage:** ALL actors from the current movie's cast are eligible (no actor has been excluded yet). ALL movies from ALL cast members are eligible and should be shown in the Eligible Movies tab.
4. **User watches the movie**, then picks an ACTOR from the current movie's cast (e.g., picks "Tom Hanks" from Cast Away). State advances.
5. **User picks the NEXT movie** from that actor's filmography. ONLY NOW does Radarr get queried — and the user should only receive a notification if the movie does NOT already exist in Radarr (no notification if already owned/queued).
6. State becomes `movie_selected_unwatched` for the new movie. Repeat from step 3.

**Key corrections needed in 03-17:**

1. **Session creation flow** — selecting a movie in the lobby should create a session and set the starting movie, NOT immediately prompt for actor selection. The "pick an actor" prompt appears only after the user has watched the current movie and is ready to chain forward.

2. **Eligible Movies on mount at session start** — when no actor has been selected yet (first step of a new session, or any `movie_selected_unwatched` state), the Eligible Movies tab must show the combined view: all movies from all cast members of the current movie. The combined-view query already exists (`actor_id` undefined) but may not be triggered correctly in this initial state.

3. **Radarr query timing** — Radarr should only be called when the user picks the NEXT movie (step 5 above), not at session creation. Additionally, the notification/confirmation should be conditional: only show if the movie is not already in Radarr.

## Task Commits

Task 1 (verification only, no files modified): no commit — verification output is this SUMMARY.

## Files Created/Modified

None — this plan is a verification-only checkpoint.

## Decisions Made

- Phase 3 cannot close until the session state machine flow is corrected in 03-17.
- The `setQueryData` end-session fix (03-14) is confirmed working — GAME-01 end-session sub-requirement passes.
- The NavBar (03-15) is confirmed working — persists on all pages.
- The session start + eligible movies defect is a flow/architecture issue, not a minor bug — the entire state machine advancement logic needs to be rethought in 03-17.

## Deviations from Plan

None — verification executed as written. Failures were discovered defects, not execution errors.

## Issues Encountered

The session state machine UI implemented in 03-15 encoded the wrong flow assumption: that a new session begins with "pick an actor" rather than "movie selected, watch it, then pick an actor." This misalignment was not visible during code review — it required live testing of the full user journey to surface.

## User Setup Required

None.

## Next Phase Readiness

- Phase 3 is NOT complete — 03-17 is required.
- 03-17 must address:
  1. Session creation flow: movie selection creates session in `movie_selected_unwatched` state with no actor prompt
  2. State machine UI: "pick an actor" guidance appears only after movie is watched (awaiting actor selection state)
  3. Eligible Movies on mount: combined view (all actors' movies) shows at session start before any actor is chosen
  4. Radarr query timing: fire Radarr call only when user picks the next movie (not at session creation); suppress notification if movie already exists in Radarr
- Phase 4 (Query Mode) remains blocked until Phase 3 closes.

---
*Phase: 03-movie-game*
*Completed: 2026-03-15*
