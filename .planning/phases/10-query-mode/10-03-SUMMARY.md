---
phase: 10-query-mode
plan: "03"
subsystem: frontend
tags: [wave-2, search, query-mode, react, tanstack-query, sort, filter, genre-chips]
dependency_graph:
  requires: [10-02]
  provides: [search-page-ui, genre-browse, title-search, person-search, movie-splash-dialog]
  affects:
    - frontend/src/pages/SearchPage.tsx
    - frontend/src/lib/api.ts
    - frontend/src/App.tsx
tech_stack:
  added: []
  patterns:
    - null-stable-two-pass-sort
    - debounced-prefix-aware-search
    - unified-results-pipeline
    - genre-chip-landing-state
key_files:
  created:
    - frontend/src/pages/SearchPage.tsx
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/App.tsx
  deleted:
    - frontend/src/pages/SearchPlaceholder.tsx
decisions:
  - "Renamed legacy api.searchMovies -> api.searchMoviesLegacy to avoid collision; new searchMovies hits /search/movies and returns EligibleMovieDTO[] (Phase 10 endpoint)"
  - "MovieFilterSidebar is a named export (not default) with genres/filters/onChange props; plan had incorrect import — fixed to match actual component interface"
  - "Derived availableGenres from rawResults via useMemo so sidebar genre list reflects what is actually loaded"
  - "Dropped redundant max-w-screen-xl on inner div; App.tsx already constrains layout width to max-w-[1400px]"
metrics:
  duration_minutes: 18
  completed_date: "2026-03-31T19:26:00Z"
  tasks_completed: 2
  files_changed: 4
---

# Phase 10 Plan 03: SearchPage Frontend Summary

Full Query Mode frontend — genre chips landing state, prefix-aware search with 300ms debounce, sortable results table (null-stable two-pass sort ported from GameSession), MovieFilterSidebar, Unwatched Only toggle, and movie splash dialog with Radarr/Watch Online actions.

## What Was Built

### frontend/src/pages/SearchPage.tsx (new — 632 lines)

Replaces the Wave 0 null stub with the full Query Mode page.

**Genre chips landing state:** 14 genre buttons rendered when search is empty and no genre is selected. Clicking a chip fires `getPopularByGenre` immediately (no debounce), displays results table, and shows the active genre chip above the table (acts as a clear button).

**Prefix-aware search input:** `parseSearchMode` parses `a:` / `d:` prefix as person search (hits `/search/actors`), `m:` or no prefix as title search (hits `/search/movies`). 300ms debounce applied. Inline clear button (lucide X) when input is non-empty. Syntax hint always visible below input.

**Unified results pipeline:**
1. Three `useQuery` calls (title, person, genre) with correct `enabled` guards
2. `rawResults` useMemo selects the active source
3. Filter chain: watched toggle → genre filter → MPAA filter → runtime range
4. Null-stable two-pass sort (exact port from GameSession.tsx) — nulls always sort last regardless of direction
5. Pagination (20 per page); page resets on any filter/sort/query change

**MovieFilterSidebar:** Integrated with `availableGenres` derived from loaded results, `filters` state, and `onChange={setFilters}`. Hidden below lg breakpoint (sidebar is desktop-only in this implementation matching the plan spec).

**Unwatched Only toggle:** Two buttons ("All" / "Unwatched Only") using `aria-pressed`. Watched movies show a green "Watched" badge in the title column.

**Movie splash dialog:** Reuses `max-w-2xl` Dialog structure from GameSession. Poster (w185), metadata badges (TMDB rating, RT%, MPAA, runtime, year), overview, TMDB external link. "Download via Radarr" calls `api.requestMovieStandalone` with label state machine (Requesting... / Added to Radarr / Already in Radarr). "Watch Online" calls `api.markWatchedOnline`. Error message shown inline for failures.

### frontend/src/lib/api.ts (modified)

- Added `RadarrRequestResult` interface: `{ status: "queued" | "already_in_radarr" | "not_found_in_radarr" | "error" }`
- Added 5 new Query Mode functions: `searchMovies`, `searchActors`, `getPopularByGenre`, `requestMovieStandalone`, `markWatchedOnline`
- Renamed old `searchMovies` (hits `/movies/search`, returns `MovieSearchResultDTO[]`) to `searchMoviesLegacy` to avoid collision

### frontend/src/App.tsx (modified)

Updated import from `SearchPlaceholder` to `SearchPage`. Route unchanged (`/search` → `<SearchPage />`).

### frontend/src/pages/SearchPlaceholder.tsx (deleted)

Removed — replaced by SearchPage.

## Verification Results

```
TypeScript: clean (no errors)

npm test -- --run SearchPage:
  Test Files: 1 passed
  Tests:      5 passed
  Duration:   2.52s
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Renamed legacy `api.searchMovies` to `api.searchMoviesLegacy`**
- **Found during:** Task 1
- **Issue:** `api.ts` already had `searchMovies` pointing to `/movies/search` returning `MovieSearchResultDTO[]`. The new Phase 10 `searchMovies` hits `/search/movies` and returns `EligibleMovieDTO[]`. Direct replacement would break `GameLobby.tsx` which depends on the old function and type.
- **Fix:** Renamed old function to `searchMoviesLegacy`, updated `GameLobby.tsx` to call `api.searchMoviesLegacy`. Added new `searchMovies` with Phase 10 semantics.
- **Files modified:** `frontend/src/lib/api.ts`, `frontend/src/pages/GameLobby.tsx`
- **Commit:** 16c95ca

**2. [Rule 1 - Bug] Fixed `MovieFilterSidebar` import and props**
- **Found during:** Task 2 pre-check
- **Issue:** Plan specified `import MovieFilterSidebar, { FilterState, DEFAULT_FILTER_STATE }` (default import) and props `filters` + `onFiltersChange`. Actual component is a named export with props `genres`, `filters`, `onChange`.
- **Fix:** Used named import `{ MovieFilterSidebar, FilterState, DEFAULT_FILTER_STATE }`. Passed `genres={availableGenres}` (derived from results) and `onChange={setFilters}`.
- **Files modified:** `frontend/src/pages/SearchPage.tsx`
- **Commit:** fa931e5

## Known Stubs

None — all UI functionality is wired. Radarr/Watch Online buttons are fully implemented (not stubs); Wave 3 (plan 10-04) will add confirmation states if needed per that plan's scope.

## Self-Check: PASSED

- `frontend/src/pages/SearchPage.tsx` — exists, 632 lines
- `frontend/src/lib/api.ts` — contains `searchMovies`, `searchActors`, `getPopularByGenre`, `requestMovieStandalone`, `markWatchedOnline`, `RadarrRequestResult`
- `frontend/src/pages/SearchPlaceholder.tsx` — deleted
- `frontend/src/App.tsx` — imports SearchPage, route `/search` points to `<SearchPage />`
- Commit 16c95ca — feat(10-03): add 5 Query Mode API functions
- Commit fa931e5 — feat(10-03): implement SearchPage
- `npm test -- --run SearchPage`: 5/5 passed
- `npx tsc --noEmit`: clean
