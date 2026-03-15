---
phase: 03-movie-game
plan: "15"
subsystem: ui
tags: [react, typescript, tailwind, shadcn, lucide-react, vite]

# Dependency graph
requires:
  - phase: 03-movie-game
    provides: GameSession and GameLobby pages with session lifecycle fixes (03-14)
provides:
  - NavBar component with CinemaChain logo and Sessions link, rendered persistently on all pages
  - GameSession full state machine UI covering 7 states with inline guidance panel
  - Compact table layout for Eligible Actors and Eligible Movies (TV-optimized)
  - GameLobby "Start a new session" heading when no active session
affects: [03-16]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "NavBar as sticky layout component above Routes in App.tsx — persists across all pages"
    - "Session state derived from status + steps shape (isMovieSelected) — no new backend field needed"
    - "Compact table rows replace card stacks — reduces scroll on TV displays"

key-files:
  created:
    - frontend/src/components/NavBar.tsx
  modified:
    - frontend/src/App.tsx
    - frontend/src/pages/GameSession.tsx
    - frontend/src/pages/GameLobby.tsx

key-decisions:
  - "isMovieSelected derived client-side from lastStep.actor_tmdb_id === null && steps.length > 1 — avoids new backend field for movie_selected_unwatched sub-state"
  - "ActorCard and MovieCard components not deleted — replaced inline in GameSession only; files kept for potential reuse"
  - "State panel rendered as inline JSX in GameSession (not extracted component) per plan spec"

patterns-established:
  - "Sticky NavBar above Routes: all pages share persistent nav without per-page duplication"
  - "Session state panel: switch on status + derived booleans for context-appropriate guidance text"

requirements-completed: [GAME-01, GAME-04, GAME-05, GAME-06, GAME-07]

# Metrics
duration: 3min
completed: 2026-03-15
---

# Phase 3 Plan 15: NavBar + Session State Machine UI Summary

**Persistent NavBar, full 7-state session guidance panel, and compact TV-optimized table layout for actor/movie selection panels**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-15T20:37:54Z
- **Completed:** 2026-03-15T20:40:24Z
- **Tasks:** 2
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments

- Created NavBar.tsx with CinemaChain logo (links to /), Sessions nav link with active-state highlighting, sticky top with backdrop blur
- Wired NavBar into App.tsx layout wrapper so it renders persistently on every page
- Replaced GameSession's duplicate "CinemaChain" h1 with current movie title in header
- Added inline session state panel covering all 7 UI states: new_session, active (pick actor), movie_selected_unwatched (awaiting watch), awaiting_continue (continue button), paused (resume button)
- Replaced tall ActorCard stack with compact table (avatar, name, character column)
- Replaced tall MovieCard stack with compact table (poster thumbnail, title, via-actor, rating, year)
- Added "Start a new session" heading + subtitle above three-tab panel in GameLobby when no active session

## Task Commits

Each task was committed atomically:

1. **Task 1: NavBar component and App.tsx layout wiring** - `a7d67c4` (feat)
2. **Task 2: Session state machine UI + compact tables in GameSession and GameLobby** - `d057c2f` (feat)

## Files Created/Modified

- `frontend/src/components/NavBar.tsx` - New sticky nav with CinemaChain logo, Sessions link, active-state highlighting
- `frontend/src/App.tsx` - Imports and renders NavBar above Routes
- `frontend/src/pages/GameSession.tsx` - Header shows current movie title; inline state panel; compact actor/movie tables; removed ActorCard/MovieCard usage and old awaiting_continue banner
- `frontend/src/pages/GameLobby.tsx` - "Start a new session" heading wrapping three-tab panel

## Decisions Made

- `isMovieSelected` derived client-side: `status === "active" && lastStep.actor_tmdb_id === null && steps.length > 1`. No new backend field required — the existing step shape already carries this information.
- ActorCard.tsx and MovieCard.tsx files not deleted — only their usage in GameSession.tsx removed. Kept for potential future use.
- State panel implemented as inline JSX per plan spec (not extracted to a separate component file).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. All changes are frontend-only; rebuild and redeploy to pick up changes.

## Next Phase Readiness

- NavBar renders on all pages — GAME-05/GAME-06 navigation gap closed
- Session state machine UI complete — all 7 states have distinct purposeful UI
- Compact tables ready for TV use — reduced scroll on both actor and movie panels
- 03-16 can proceed with API verification (GAME-04 actor deduplication) and final re-verification pass

## Self-Check: PASSED

All created files confirmed present. Both task commits verified in git log.

---
*Phase: 03-movie-game*
*Completed: 2026-03-15*
