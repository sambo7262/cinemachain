---
phase: 19-v2-bug-fixes-polish
plan: 03
subsystem: ui
tags: [react, typescript, fastapi, GameSession, SearchPage, WatchHistoryPage, eligible-movies, filters, sort]

# Dependency graph
requires:
  - phase: 19-v2-bug-fixes-polish
    provides: plan 02 mobile UI fixes already applied
provides:
  - GameSession filter/search reset on step advance (D-16)
  - Cross-page search and filter via needsAllResults=9999 pattern (D-17)
  - NR filter toggle on eligible movies with backend exclude_nr param (D-18)
  - All sort selectors default to DESC across GameSession, SearchPage (D-21)
affects: [GameSession, SearchPage, WatchHistoryPage, game.py eligible movies endpoint]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "needsAllResults pattern: fetch all 9999 items when search, sidebar filters, or mark filters active"
    - "exclude_nr backend param: filters by mpaa_rating == NR only, NULL MPAA passes through"

key-files:
  created: []
  modified:
    - frontend/src/pages/GameSession.tsx
    - frontend/src/pages/SearchPage.tsx
    - backend/app/routers/game.py
    - frontend/src/lib/api.ts

key-decisions:
  - "needsAllResults extends filteringByMark to also include debouncedSearch and hasActiveFilters — fetches all 9999 movies for any active filter/search state"
  - "exclude_nr filters only mpaa_rating == NR; movies with mpaa_rating = NULL (missing) pass through per D-18 constraint"
  - "Sort default to desc unconditionally on new column selection; same-column click still toggles direction"

patterns-established:
  - "Cross-page filter pattern: set effectivePageSize=9999 when any filter/search is active, not just mark filters"

requirements-completed: [v2BUG-01]

# Metrics
duration: 15min
completed: 2026-04-02
---

# Phase 19 Plan 03: GameSession Filter/Search Bugs + NR Filter + Sort Defaults Summary

**GameSession filter/search reset on step advance, cross-page filter via 9999-fetch, NR toggle (exclude_nr backend param), and all sort selectors defaulting DESC**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-02T18:10:00Z
- **Completed:** 2026-04-02T18:25:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Reset all filters, search, sort, page, and selected actor when the session advances to a new movie (D-16)
- Extended the existing `filteringByMark` pattern to `needsAllResults` — now fetches all 9999 movies whenever search text, sidebar filters (genre/MPAA/runtime), or mark filters are active (D-17)
- Added `exclude_nr` query param to `get_eligible_movies` in game.py; frontend toggle button "Hide NR" in GameSession (D-18)
- GameSession and SearchPage sort column selectors now always default to DESC when a new column is selected; same-column click still toggles (D-21)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix filter/search reset on step advance and cross-page search** - `ac5feb3` (feat)
2. **Task 2: NR filter toggle and sort defaults to DESC** - `c6e3b0e` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `frontend/src/pages/GameSession.tsx` - Step-advance reset, needsAllResults pattern, excludeNR state + Hide NR button, sort default DESC
- `frontend/src/pages/SearchPage.tsx` - handleSortClick new column defaults to desc
- `backend/app/routers/game.py` - exclude_nr param and NR filter logic on eligible movies
- `frontend/src/lib/api.ts` - exclude_nr param in getEligibleMovies

## Decisions Made

- `needsAllResults` extends the existing `filteringByMark` flag: search and sidebar filters now also trigger full 9999-item fetch so client-side filtering works across all pages
- `exclude_nr` only excludes `mpaa_rating == "NR"` — movies with NULL/missing MPAA pass through as required by D-18
- Sort onValueChange always calls `setSortDir("desc")` unconditionally — no special case for "rating" column

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Local Python 3.9 import check fails for game.py due to pre-existing `str | None` type union syntax incompatibility (Python 3.10+ syntax). This is a pre-existing dev machine issue unrelated to this plan's changes. The backend runs in Docker with Python 3.11+. TypeScript compilation passed cleanly.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All D-16, D-17, D-18, D-21 bugs resolved
- GameSession eligible movies now filter/search across all pages regardless of pagination
- NR filter toggle wired end-to-end (backend + frontend)
- Sort defaults consistent (DESC) across GameSession and SearchPage
- Ready for plan 19-04

## Self-Check: PASSED

- SUMMARY.md: FOUND
- Commit ac5feb3: FOUND
- Commit c6e3b0e: FOUND

---
*Phase: 19-v2-bug-fixes-polish*
*Completed: 2026-04-02*
