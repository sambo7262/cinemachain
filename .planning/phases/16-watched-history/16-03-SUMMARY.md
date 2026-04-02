---
phase: 16-watched-history
plan: "03"
subsystem: frontend
tags: [watch-history, page, navigation, ui]
dependency_graph:
  requires: [16-01, 16-02]
  provides: [WatchHistoryPage, /watched route, Watch History nav link]
  affects: [frontend/src/App.tsx, frontend/src/components/NavBar.tsx, frontend/src/lib/api.ts]
tech_stack:
  added: []
  patterns: [useQuery, useMutation, debounced search, shadcn Select/Dialog/Input/Button]
key_files:
  created:
    - frontend/src/pages/WatchHistoryPage.tsx
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/components/NavBar.tsx
    - frontend/src/App.tsx
decisions:
  - "Renamed saveMovie/unsaveMovie to saveMovieGlobal/unsaveMovieGlobal in api.ts to avoid naming conflict with existing session-scoped save functions"
  - "Used RatingsBadge variant='tile' for tile view and variant='splash' for dialog — matching existing SearchPage patterns"
metrics:
  duration_minutes: 20
  completed_date: "2026-04-02T04:18:33Z"
  tasks_completed: 2
  files_changed: 4
---

# Phase 16 Plan 03: Watch History Frontend Summary

Watch History frontend page — list/tile toggle, debounced search, sort dropdown, pagination, splash dialog with personal rating input and global save toggle — wired into NavBar and App.tsx routes.

## Objective

Build the primary user-visible deliverable for Phase 16: a first-party watched history view at `/watched`.

## Tasks Completed

### Task 1: Add api.ts types and functions for Watch History

Added `WatchedMovieDTO` and `WatchedMoviesResponse` interfaces after `RadarrRequestResult`. Added four new api functions to the `api` object:
- `getWatchedHistory(params?)` — fetches `GET /movies/watched` with sort/search/page params
- `setMovieRating(tmdbId, rating)` — calls `PATCH /movies/{id}/rating`
- `saveMovieGlobal(tmdbId)` — calls `POST /movies/{id}/save`
- `unsaveMovieGlobal(tmdbId)` — calls `DELETE /movies/{id}/save`

**Commit:** `30f7220`

### Task 2: Build WatchHistoryPage.tsx + wire NavBar + App.tsx

Created `frontend/src/pages/WatchHistoryPage.tsx` (~290 lines) with:
- List view: table with poster, title, year, runtime, genres, ratings (RatingsBadge card), watched date, personal rating columns
- Tile view: 3-column grid with poster (aspect-ratio 2/3), title, year, RatingsBadge tile, watched date, personal rating badge
- Toolbar: debounced search input (300ms), sort Select (11 options), list/tile toggle buttons
- Pagination: Previous/Next with page counter, correct disabled states
- Splash dialog: overview, all ratings (RatingsBadge splash), personal rating badge, watched date, runtime/MPAA; personal rating input (1-10) with Save Rating button; global Save/star toggle button

Updated `NavBar.tsx`: added `isWatchHistoryActive` const; inserted Watch History link between Search and Settings icon.

Updated `App.tsx`: imported WatchHistoryPage; added `<Route path="/watched" element={<WatchHistoryPage />} />` before catch-all.

**Commit:** `84b98ab`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Naming conflict with existing saveMovie/unsaveMovie**
- **Found during:** Task 1
- **Issue:** The `api` object already had `saveMovie(sessionId, tmdbId)` and `unsaveMovie(sessionId, tmdbId)` for session-scoped saves. Adding same-named functions for global saves would silently shadow/override them.
- **Fix:** Named the new functions `saveMovieGlobal` and `unsaveMovieGlobal`; updated all references in WatchHistoryPage accordingly.
- **Files modified:** `frontend/src/lib/api.ts`, `frontend/src/pages/WatchHistoryPage.tsx`
- **Commit:** Included in 30f7220 and 84b98ab

**2. [Rule 1 - Bug] RatingsBadge prop name**
- **Found during:** Task 2
- **Issue:** Plan specified `<RatingsBadge movie={movie} />` but the actual component API is `ratings` not `movie`.
- **Fix:** Used correct `ratings={m}` prop throughout WatchHistoryPage.
- **Files modified:** `frontend/src/pages/WatchHistoryPage.tsx`
- **Commit:** 84b98ab

## Verification Results

- TypeScript: no errors (`npx tsc --noEmit`)
- Build: succeeds (`npm run build` — 499KB JS bundle, 5.97s)
- WatchHistoryPage.tsx: 290+ lines, exports `default function WatchHistoryPage`
- NavBar: "Watch History" link present between Search and Settings icon
- App.tsx: `/watched` route present pointing to `<WatchHistoryPage />`

## Known Stubs

None — all data fetching is wired to real backend endpoints from Plan 16-02.

## Self-Check: PASSED

- `frontend/src/pages/WatchHistoryPage.tsx` — FOUND
- `frontend/src/lib/api.ts` WatchedMovieDTO, WatchedMoviesResponse — FOUND
- `frontend/src/components/NavBar.tsx` Watch History link — FOUND
- `frontend/src/App.tsx` /watched route — FOUND
- Commit 30f7220 — FOUND
- Commit 84b98ab — FOUND
