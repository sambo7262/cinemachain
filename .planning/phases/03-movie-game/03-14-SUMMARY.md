---
phase: 03-movie-game
plan: "14"
subsystem: ui
tags: [react, tanstack-query, game-session, cache, frontend]

# Dependency graph
requires:
  - phase: 03-movie-game
    provides: GameLobby and GameSession components built in prior plans
provides:
  - Synchronous setQueryData cache clear in GameLobby endMutation — banner disappears on same render cycle
  - eligibleMovies query enabled on session load (not gated by activeTab) — combined view available immediately
affects:
  - GAME-01 session lifecycle
  - GAME-03 eligible movies display

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "setQueryData(null) + invalidateQueries for optimistic cache clear on mutation success"
    - "eligibleMovies query enabled on !!sid && !!session — not gated by UI tab state"

key-files:
  created: []
  modified:
    - frontend/src/pages/GameLobby.tsx
    - frontend/src/pages/GameSession.tsx

key-decisions:
  - "setQueryData(['activeSession'], null) used over refetchQueries in endMutation.onSuccess — guarantees synchronous banner clear on same React render cycle, eliminates staleTime race on NAS hardware"
  - "activeSession staleTime reduced from 10_000 to 0 — ensures subsequent refetch after invalidation returns fresh server state immediately"
  - "eligibleMovies enabled condition changed from activeTab gate to !!session — combined view (actor_id undefined) fetched on mount so Eligible Movies tab is pre-populated"

patterns-established:
  - "Optimistic UI with setQueryData: write null synchronously, then invalidate for background refresh"

requirements-completed:
  - GAME-01
  - GAME-03
  - GAME-04
  - GAME-07

# Metrics
duration: 8min
completed: 2026-03-15
---

# Phase 3 Plan 14: Session Lifecycle + Eligible Movies Gap Closure Summary

**Synchronous setQueryData clears lobby session banner on click; eligibleMovies query enabled on mount so combined view populates without actor selection**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-15T23:14:10Z
- **Completed:** 2026-03-15T23:22:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- End Session button in lobby now clears the session banner synchronously on the same render cycle — no page reload required and no async timing race
- activeSession staleTime set to 0 so the background invalidation after setQueryData always fetches fresh state
- Eligible Movies combined view (all actors' movies) fetched on session load regardless of which tab is visible
- Empty-state message updated to guide actor selection; "Clear actor filter" renamed to "Show all eligible movies" for clarity

## Task Commits

1. **Task 1: Fix end-session banner clear with synchronous setQueryData** - `6e6f7db` (fix)
2. **Task 2: Fix Eligible Movies combined view on mount + update UX copy** - `b9d0665` (fix)

## Files Created/Modified

- `/Users/Oreo/Projects/frontend/src/pages/GameLobby.tsx` — endMutation.onSuccess replaced with setQueryData(null)+invalidateQueries; staleTime reduced to 0
- `/Users/Oreo/Projects/frontend/src/pages/GameSession.tsx` — eligibleMovies enabled condition changed from activeTab gate to !!session; empty-state message updated; button copy updated

## Decisions Made

- Used `queryClient.setQueryData(["activeSession"], null)` over `refetchQueries` in endMutation.onSuccess. The prior `async onSuccess + refetchQueries` pattern was subject to a timing race: React could re-render with stale `activeSession` (still truthy) before the network refetch resolved, leaving the banner visible. Writing null synchronously is guaranteed to trigger a re-render with a falsy value on the same cycle.
- `staleTime: 0` on the activeSession query ensures the subsequent `invalidateQueries` triggers an actual network request rather than serving a still-fresh cached value.
- Eligible movies query enabled on `!!sid && !!session` — the backend already handles `actor_id: undefined` by returning a combined view across all eligible actors, so no actor selection is needed to show content.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — both builds passed on first attempt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Both defects from the 03-13 partial pass addressed
- GAME-01 session lifecycle: end-session banner clear is now synchronous and deterministic
- GAME-03/GAME-04/GAME-07 eligible movies: combined view available on mount
- Phase 3 is ready for final re-verification (deploy + manual smoke test)
- Phase 4 (Query Mode) unblocked once Phase 3 verification passes

---
*Phase: 03-movie-game*
*Completed: 2026-03-15*
