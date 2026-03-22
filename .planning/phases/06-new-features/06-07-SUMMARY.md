---
phase: 06-new-features
plan: 07
subsystem: ui
tags: [rotten-tomatoes, mdblist, decision-gate, verification, testing-library]

# Dependency graph
requires:
  - phase: 06-new-features
    provides: all Phase 6 features (Items 1-9 except RT ratings)
provides:
  - Decision: MDBList API selected for RT ratings (Item 7) — future implementation backlog
  - Frontend build verified clean (1907 modules, 439KB bundle)
  - Backend syntax verified clean
affects: [future-rt-ratings-implementation]

# Tech tracking
tech-stack:
  added:
    - "@testing-library/user-event ^14.6.1 (missing devDependency added)"
  patterns:
    - "tsconfig.app.json types field for @testing-library/jest-dom — required for toBeInTheDocument matchers to type-check"

key-files:
  created: []
  modified:
    - frontend/package.json
    - frontend/package-lock.json
    - frontend/tsconfig.app.json
    - frontend/src/pages/GameLobby.tsx

key-decisions:
  - "Item 7 RT ratings: MDBList API selected — accepts TMDB ID natively, returns both Tomatometer + Audience Score, 1000 free req/day with DB caching. Implementation deferred to post-Phase-6 backlog."

patterns-established: []

requirements-completed: [ITEM-7]

# Metrics
duration: 2min
completed: 2026-03-22
---

# Phase 06 Plan 07: RT Decision Gate + Build Verification Summary

**MDBList API selected for Rotten Tomatoes integration (TMDB-native, dual scores), frontend build clean at 439KB after fixing 3 pre-existing TypeScript errors**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-22T14:42:54Z
- **Completed:** 2026-03-22T14:44:54Z
- **Tasks:** 2 (1 decision checkpoint + 1 verification)
- **Files modified:** 4

## Accomplishments

- Decision gate resolved: MDBList API chosen for RT ratings (Item 7) — deferred to post-Phase-6 backlog
- Frontend builds cleanly: `tsc -b` + `vite build` succeed with zero errors (1907 modules, 439KB)
- Backend Python syntax verified clean across 5 core modules
- 3 pre-existing build blockers auto-fixed: missing `@testing-library/user-event`, missing jest-dom types, unused `formatSessionAge` function

## Task Commits

1. **Task 1-2: Decision recording + build verification** - `0e95d19` (fix)

**Plan metadata:** (recorded below with state update)

## Files Created/Modified

- `frontend/package.json` — added @testing-library/user-event ^14.6.1 to devDependencies
- `frontend/package-lock.json` — updated lockfile
- `frontend/tsconfig.app.json` — added `"types": ["@testing-library/jest-dom"]` for toBeInTheDocument type support
- `frontend/src/pages/GameLobby.tsx` — removed unused `formatSessionAge` function (duplicate of SessionCounters.tsx version)

## Decisions Made

**RT Ratings — MDBList API (implement-mdblist):**
- MDBList accepts TMDB ID directly (no IMDB ID mapping needed)
- Returns both Tomatometer + Audience Score in a single call
- 1,000 free requests/day — sufficient with DB caching (`rt_score`, `rt_audience_score` columns)
- Scores can be days-to-weeks stale (acceptable for home use)
- Implementation: add columns to Movie model, fetch on-demand, cache in DB, display in eligible movies table and movie splash
- Status: **backlog** — not implemented in Phase 6

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Missing @testing-library/user-event dependency**
- **Found during:** Task 2 (frontend build verification)
- **Issue:** ChainHistory.test.tsx imports `@testing-library/user-event` but it was not in package.json — caused TS2307 build failure
- **Fix:** `npm install --save-dev @testing-library/user-event`
- **Files modified:** frontend/package.json, frontend/package-lock.json
- **Verification:** TS error TS2307 gone, build passes
- **Committed in:** 0e95d19

**2. [Rule 1 - Bug] Missing @testing-library/jest-dom types in tsconfig**
- **Found during:** Task 2 (frontend build verification)
- **Issue:** `toBeInTheDocument()` matcher not recognized by TypeScript (TS2339) — jest-dom was installed but types not included in tsconfig.app.json
- **Fix:** Added `"types": ["@testing-library/jest-dom"]` to tsconfig.app.json compilerOptions
- **Files modified:** frontend/tsconfig.app.json
- **Verification:** TS error TS2339 gone across all test files, build passes
- **Committed in:** 0e95d19

**3. [Rule 1 - Bug] Unused formatSessionAge function in GameLobby.tsx**
- **Found during:** Task 2 (frontend build verification)
- **Issue:** `formatSessionAge` declared in GameLobby.tsx but never used there — same function exists in SessionCounters.tsx where it's actually used. Caused TS6133 with noUnusedLocals enabled.
- **Fix:** Removed the duplicate dead function from GameLobby.tsx
- **Files modified:** frontend/src/pages/GameLobby.tsx
- **Verification:** TS6133 gone, build passes
- **Committed in:** 0e95d19

---

**Total deviations:** 3 auto-fixed (1 blocking dependency, 2 bugs)
**Impact on plan:** All three fixes were pre-existing issues that blocked the build verification. Required for correctness. No scope creep.

## Issues Encountered

- `python` command not found on macOS — used `python3` instead. Backend syntax check passed cleanly.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- All Phase 6 features verified at build level (frontend + backend compile clean)
- RT ratings (Item 7) decision recorded: MDBList API, implementation deferred to backlog
- Visual verification (Test 1-8 in plan) remains for human — done at checkpoint
- Ready for Phase 6 final wrap-up or production deployment

---
*Phase: 06-new-features*
*Completed: 2026-03-22*
