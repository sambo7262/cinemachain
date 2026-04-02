---
phase: 08-bug-fixes
plan: "01"
subsystem: ui
tags: [react, typescript, python, fastapi, tmdb, missing-data-display]

# Dependency graph
requires:
  - phase: 04.1-bug-fixes-csv-hardening
    provides: RT scores and MPAA rating fields populated on Movie model
provides:
  - MPAA always-render NR fallback in table cell, splash dialog, and MovieCard
  - RT always-render em dash fallback in table cell and splash dialog
  - Overview always-render fallback text in splash dialog
  - _backfill_overview_pass in nightly_cache_job to fill NULL overview rows from TMDB
affects: [game-session, movie-card, nightly-cache]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - frontend/src/pages/GameSession.tsx
    - frontend/src/components/MovieCard.tsx
    - backend/app/services/cache.py

key-decisions:
  - "|| over ?? for MPAA fallback: || maps both null and empty string to 'NR'; ?? only handles null/undefined"
  - "Always-render badge pattern for RT and MPAA in splash dialog — removes conditional wrapper"
  - "_backfill_overview_pass modelled on _backfill_mpaa_pass; called after MPAA pass in nightly_cache_job"

patterns-established:
  - "Missing-data display: always render placeholder text/badge — never blank gap"
  - "|| 'NR' for MPAA, || 'No overview available.' for overview, ternary '—' for RT"

requirements-completed: [BUG-02, BUG-03, BUG-06]

# Metrics
duration: 12min
completed: 2026-03-30
---

# Phase 08 Plan 01: Missing-Data Display Fixes Summary

**MPAA NR fallback and RT em dash placeholders across table/splash/MovieCard, plus nightly overview backfill from TMDB**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-30T00:00:00Z
- **Completed:** 2026-03-30T00:12:00Z
- **Tasks:** 4
- **Files modified:** 3

## Accomplishments
- MPAA rating now shows "NR" instead of blank for null and empty-string values in table cell, splash dialog, and MovieCard badge
- RT score table cell now shows "—" em dash instead of blank when score is null/0
- Splash dialog RT and MPAA badges always render with explicit fallback values
- Splash dialog overview paragraph always renders — shows "No overview available." when overview is absent
- `_backfill_overview_pass` added to cache.py; nightly job now fills movies with NULL overview from TMDB

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix MPAA and RT display in GameSession.tsx movies table** - `6701322` (fix)
2. **Task 2: Fix splash dialog — MPAA NR fallback, RT em dash, overview fallback text** - `4c363b5` (fix)
3. **Task 3: Fix MovieCard MPAA badge to always render with NR fallback** - `a7a7393` (fix)
4. **Task 4: Add _backfill_overview_pass to cache.py and call it from nightly_cache_job** - `470a0db` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `frontend/src/pages/GameSession.tsx` - Table cell MPAA/RT display fixes; splash dialog always-render MPAA/RT/overview
- `frontend/src/components/MovieCard.tsx` - MPAA badge always renders with NR fallback
- `backend/app/services/cache.py` - Added `_backfill_overview_pass` function; called from `nightly_cache_job`

## Decisions Made
- Used `||` operator instead of `??` for MPAA fallback — `??` only guards null/undefined while `||` also catches empty string (the no-US-cert sentinel written by the backfill pass)
- Always-render badge pattern in splash dialog: removed `{condition && <Badge>}` wrappers; badge always present with ternary/or fallback value
- `_backfill_overview_pass` writes `overview=None` (not empty string) when TMDB returns empty, consistent with the IS NULL query filter

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `python` command not found on macOS — used `python3` for syntax check. No impact on deployed code.

## Next Phase Readiness
- BUG-02, BUG-03, BUG-06 display fixes are deployed to frontend
- Overview backfill will run on next nightly cache job cycle
- No blockers for subsequent bug-fix plans in phase 08

---
*Phase: 08-bug-fixes*
*Completed: 2026-03-30*
