---
phase: 03-movie-game
plan: 23
subsystem: infra
tags: [docker, nas, deploy, verification, game-loop]

# Dependency graph
requires:
  - phase: 03-movie-game/03-21
    provides: continue-chain endpoint, Plex webhook removal
  - phase: 03-movie-game/03-22
    provides: handleContinue fix, Radarr fallback, session home page, enlarged thumbnails
provides:
  - Docker images sambo7262/cinemachain-backend:latest and sambo7262/cinemachain-frontend:latest rebuilt with --no-cache and pushed to Docker Hub
  - NAS deployment of 03-21 and 03-22 changes
  - Partial verification: Plex webhook 404 confirmed, thumbnail sizing confirmed, state machine cycling root defect confirmed FIXED, Continue the chain populates Eligible Actors
  - Clarified UX architecture for session home page vs tab view (captured for 03-24)
affects: [03-24]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Docker --no-cache rebuild required on every NAS deploy to avoid stale layer caching"

key-files:
  created: []
  modified:
    - Makefile

key-decisions:
  - "03-23 PARTIAL PASS: root state machine defect (continue-chain cycling) is confirmed fixed; session home page UX architecture requires 03-24 gap-closure"
  - "Session home page (permanent hub) is architecturally distinct from Tab View (actor/movie selection) — two separate views, not one combined view"
  - "NavBar Sessions link must always land on Session Home Page, never Tab View"
  - "Tab View is entered only via Continue the chain button from home page, and has a Back button to return"
  - "After movie confirmed from Tab View, navigate back to Session Home Page"

patterns-established:
  - "Session Home Page is the permanent hub: shows current movie + previous movie, provides Mark as Watched and Continue the chain actions"
  - "Tab View is transient: reached via Continue the chain, exited via Back or after movie confirmation"

requirements-completed: []

# Metrics
duration: ~30min
completed: 2026-03-15
---

# Phase 3 Plan 23: Docker Rebuild + NAS Deploy + Verification Summary

**Root state machine cycling defect confirmed fixed; partial NAS verification pass with two UX gaps — session home page architecture clarified for 03-24**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-03-15
- **Completed:** 2026-03-15
- **Tasks:** 2 (Task 1 complete, Task 2 partial — checkpoint)
- **Files modified:** 1 (Makefile, during Task 1)

## Accomplishments

- Both Docker images rebuilt with `--no-cache` and pushed to Docker Hub (Task 1)
- NAS containers updated via `docker compose pull && docker compose up -d`
- Root defect confirmed fixed: state machine no longer cycles — "Continue the chain" stays in actor-selection mode and Eligible Actors populates correctly
- Plex webhook endpoint confirmed removed (returns 404)
- Thumbnail size confirmed visibly larger in Eligible Movies tab
- UX architecture for session home page clarified and documented for 03-24

## Verification Results

### PASSED

| Test | Requirement | Result |
|------|-------------|--------|
| Test 1: Plex webhook | NEW-01 | PASS — returns 404 as expected |
| Test 5: Thumbnail size | NEW-02 (partial) | PASS — thumbnails visibly larger (~48x72px) |
| Test 2: State machine cycling | GAME-01, GAME-02, GAME-03 (root defect) | PASS — Continue the chain no longer reverts to Mark as Watched; Eligible Actors populates after Continue the chain; Mark as Watched works; ROOT DEFECT FIXED |

### FAILED / BLOCKED

| Test | Requirement | Result |
|------|-------------|--------|
| Test 4: Session home page — Mark as Watched button | GAME-01, NEW-02 | FAIL — no Mark as Watched button present on session home page after it loads |
| Navigation: Tab View back to home page | UX | FAIL — no way to return to session home page from Eligible Actors/Movies tab view |
| NavBar Sessions nav | UX | FAIL — does not consistently land on session home page (hub) |
| Test 3: Actor dedup | GAME-04 | BLOCKED — full game loop required first |
| Sort controls | GAME-05 | BLOCKED — full game loop required first |
| Test 4 remainder (GAME-06/07) | GAME-06, GAME-07 | BLOCKED — full game loop required first |

### Blocked Tests

Tests 3 (actor dedup), sort/filter (GAME-05/06/07) are all blocked pending the full game loop UX working. They cannot be verified until the session home page and navigation issues are resolved.

## Clarified UX Architecture (captured for 03-24)

The user provided a definitive Option B — two distinct views:

**Session Home Page (permanent hub / default landing):**
- Shows current movie + previous movie in chain
- If `active` and `!watched`: "Mark as Watched" button
- If `awaiting_continue`: "Continue the chain" button → navigates to Tab View
- NavBar Sessions link → open session → always lands here

**Tab View (actor/movie selection):**
- Eligible Actors tab + Eligible Movies tab
- Reached only by clicking "Continue the chain" from home page
- Has "← Back" button to return to session home page
- After movie confirmed → navigate back to session home page

## Task Commits

1. **Task 1: Docker rebuild + push** - `3878cf0` (chore)
2. **Task 2: NAS deploy + human verify** — checkpoint; no code commit (partial pass documented)

## Files Created/Modified

- `Makefile` — rebuild target used for `--no-cache` image builds

## Decisions Made

- **PARTIAL PASS accepted:** Root defect (state machine cycling) is confirmed fixed, which is the most critical blocker from 03-20. Remaining failures are UX navigation issues, not backend correctness issues.
- **03-24 required:** Session home page UX architecture needs a dedicated gap-closure plan to implement the two-view model (home hub + tab view with Back button) and fix NavBar navigation.
- **No code fixes in this plan:** Per instructions, all remediation deferred to 03-24.

## Deviations from Plan

None — plan executed as written. Partial pass outcome documented. No code was changed.

## Issues Encountered

- Session home page lacked a "Mark as Watched" button after loading — the hub was rendered but the primary action was missing
- No navigation path from Tab View back to Session Home Page — once in tab view, user was stranded
- NavBar Sessions navigation did not reliably land on the session home page hub

All three are UX/routing issues in the frontend, deferred to 03-24.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **03-24 gap-closure plan required** to implement the two-view session UX architecture:
  1. Session Home Page: always renders current+previous movie; conditionally shows Mark as Watched (active+!watched) or Continue the chain (awaiting_continue)
  2. Tab View: add "← Back" button returning to home page
  3. After movie confirmation from Tab View: navigate to home page
  4. NavBar Sessions → open session always routes to home page
- Once 03-24 passes, Tests 3/4 (actor dedup, sort, GAME-04 through GAME-07) can be verified in the same session
- Backend is correct — all remaining work is frontend UX routing

---
*Phase: 03-movie-game*
*Completed: 2026-03-15*
