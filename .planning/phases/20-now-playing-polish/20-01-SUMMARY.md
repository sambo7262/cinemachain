---
phase: 020-now-playing-polish
plan: 01
subsystem: ui
tags: [react, fastapi, pydantic, typescript, tailwind, shadcn]

# Dependency graph
requires:
  - phase: 19-v2-bug-fixes-polish
    provides: RatingsBadge component, GameSession hub layout, session response shape
provides:
  - CurrentMovieDetail embedded in all single-session API responses
  - Now Playing hub with MPAA badge, year, runtime, full ratings row, expandable overview
  - PosterWall desktop visibility restored (bg-background removed from outer wrapper)
affects: [GameSession, api, game.py]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Backend embeds current_movie_detail in session response at query time (no frontend DB lookup)
    - ExpandableOverview local component with line-clamp-3 and controlled expand/collapse

key-files:
  created: []
  modified:
    - backend/app/routers/game.py
    - frontend/src/lib/api.ts
    - frontend/src/pages/GameSession.tsx

key-decisions:
  - "20-01: CurrentMovieDetail embedded via _resolve_current_movie_detail helper called at each single-session endpoint; list endpoints (GET /sessions, GET /sessions/archived) skip it"
  - "20-01: ExpandableOverview threshold is 150 chars (text.length > 150); text below that shows no expand button"
  - "20-01: bg-background removed from GameSession min-h-screen wrapper; sub-header retains its own bg-background so only the content area becomes transparent behind PosterWall"

patterns-established:
  - "Backend metadata embedding: resolve detail once per request in async endpoint, pass to sync _build_session_response as a parameter"

requirements-completed: [POLISH-01]

# Metrics
duration: 20min
completed: 2026-04-02
---

# Phase 20 Plan 01: Now Playing Polish Summary

**Backend embeds CurrentMovieDetail (year, runtime, MPAA, overview, 5 ratings) in session responses; Now Playing hub renders full metadata row, RatingsBadge card variant, and expandable overview from backend data instead of allEligibleMovies lookup**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-04-02T20:30:00Z
- **Completed:** 2026-04-02T20:52:22Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added `CurrentMovieDetail` Pydantic model with 9 metadata fields and embedded it in `GameSessionResponse`
- Added `_resolve_current_movie_detail` async helper and wired it into 9 single-session endpoints
- Replaced fragile `allEligibleMovies.find()` in Now Playing hub with `session.current_movie_detail` — metadata now visible pre-watch without fetching eligible movies
- Added metadata row (MPAA badge, year, runtime), `RatingsBadge variant="card"` with full ratings, and `ExpandableOverview` with 3-line clamp and Read more/Show less toggle
- Fixed PosterWall desktop visibility by removing `bg-background` from GameSession outer wrapper

## Task Commits

1. **Task 1: Backend — embed current_movie_detail in session response** - `c655605` (feat)
2. **Task 2: Frontend — render metadata, ratings, overview + fix PosterWall visibility** - `3261280` (feat)

## Files Created/Modified
- `backend/app/routers/game.py` - Added CurrentMovieDetail model, _resolve_current_movie_detail helper, wired into 9 call sites
- `frontend/src/lib/api.ts` - Added CurrentMovieDetail interface, added field to GameSessionDTO
- `frontend/src/pages/GameSession.tsx` - ExpandableOverview component, Now Playing hub metadata block, PosterWall bg fix

## Decisions Made
- `_resolve_current_movie_detail` is async (awaits db) and called per-request in async endpoint functions; passed as a parameter to the sync `_build_session_response` to maintain the existing pattern
- List endpoints (`GET /sessions`, `GET /sessions/archived`) do not call `_resolve_current_movie_detail` — those are grid views, not Now Playing renderers
- `ExpandableOverview` threshold is 150 chars — short overviews show full text with no toggle
- `bg-background` removed from outer GameSession wrapper only; the sub-header (`border-b border-border bg-background`) retains its own opaque background

## Deviations from Plan

None - plan executed exactly as written. The plan also mentioned updating `request_movie`, `pick_actor`, and `disambiguation_required` responses which were not explicitly listed in the plan's endpoint list but were found during implementation; these were updated as they are also single-session responses.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Now Playing hub is fully informative at all times regardless of watched state
- PosterWall visible on desktop viewports (sm+)
- TypeScript compiles cleanly
- Ready for Phase 20 Plan 02

---
*Phase: 020-now-playing-polish*
*Completed: 2026-04-02*

## Self-Check: PASSED
- SUMMARY.md exists at .planning/phases/020-now-playing-polish/20-01-SUMMARY.md
- Commit c655605 (Task 1) confirmed in git log
- Commit 3261280 (Task 2) confirmed in git log
