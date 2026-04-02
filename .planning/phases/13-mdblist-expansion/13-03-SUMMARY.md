---
phase: 13-mdblist-expansion
plan: "03"
subsystem: frontend
tags: [ratings, badges, imdb, ui-component, icons]
dependency_graph:
  requires: [mdblist-expanded-parser, movie-model-rating-columns, dto-rating-fields]
  provides: [ratings-badge-component, imdb-external-links]
  affects: [game-session-ui, search-page-ui, chain-history-ui]
tech_stack:
  added: ["@icons-pack/react-simple-icons@^13.13.0"]
  patterns: [variant-keyed-badge-strip, null-0-sentinel-hiding, conditional-imdb-tmdb-link]
key_files:
  created:
    - frontend/src/components/RatingsBadge.tsx
    - frontend/src/components/__tests__/RatingsBadge.test.tsx
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/pages/GameSession.tsx
    - frontend/src/pages/SearchPage.tsx
    - frontend/src/components/ChainHistory.tsx
    - frontend/package.json
decisions:
  - "RatingsBadge uses variant-keyed BADGE_DEFS array to filter which sources appear per context (card/splash/tile)"
  - "0-sentinel hidden same as null — no badge rendered when value === 0 matching backend sentinel-0 pattern"
  - "SearchPage results table: collapsed two columns (Rating + RT) into single Ratings column with RatingsBadge card variant"
  - "ChainHistory uses step.movie_imdb_id (optional field added to GameSessionStepDTO) with TMDB fallback — graceful degradation until backend serializes field"
  - "star vote_average removed from splash/card in GameSession — vote_average now rendered by RatingsBadge splash/card via TMDB icon badge"
metrics:
  duration_minutes: 22
  tasks_completed: 2
  files_created: 2
  files_modified: 5
  completed_date: "2026-04-01"
---

# Phase 13 Plan 03: RatingsBadge Component + Frontend Integration Summary

Replaced single `🍅 RT%` inline text across all movie displays with a flex-wrap RatingsBadge component showing multi-source ratings (IMDB, RT, Audience, Metacritic, MDB, TMDB, Letterboxd) keyed by context variant, and swapped all 4 TMDB external links to conditional IMDB links.

## What Was Built

### Task 1: Install icons, extend DTO, RatingsBadge component + tests

**Package install:**
- `@icons-pack/react-simple-icons@^13.13.0` — provides `SiImdb`, `SiLetterboxd`, `SiThemoviedatabase` SVG icons

**EligibleMovieDTO extension** (`frontend/src/lib/api.ts`):
- Added 6 new fields after `rt_score`: `rt_audience_score`, `imdb_id`, `imdb_rating`, `metacritic_score`, `letterboxd_score`, `mdb_avg_score`
- Added optional `movie_imdb_id` to `GameSessionStepDTO` for forward-compatible ChainHistory link swap

**RatingsBadge component** (`frontend/src/components/RatingsBadge.tsx`):
- `RatingsData` interface accepts all 7 optional/nullable rating fields
- `BadgeVariant`: `"card" | "splash" | "tile"`
- `VARIANT_KEYS` defines which keys appear per variant:
  - `card`: `[imdb_rating, rt_score, rt_audience_score, metacritic_score]`
  - `splash`: all 7 fields
  - `tile`: `[imdb_rating, rt_score]`
- `BADGE_DEFS` array with SVG icons (SiImdb, SiLetterboxd, SiThemoviedatabase) and styled text for RT/Audience/MC/MDB
- Null and 0-sentinel values both hidden — no badge rendered
- Output: `<div className="flex flex-wrap gap-1.5 items-center">` with inline-flex badges

**Tests** (`frontend/src/components/__tests__/RatingsBadge.test.tsx`):
- 6 tests using `@testing-library/react` render + screen with `.toBeTruthy()` / `.toBeFalsy()` (project pattern — no jest-dom setup)
- Tests: card 4-badge count, splash 7-badge count, tile 2-badge count, null hiding, 0-sentinel hiding, score formatting

### Task 2: Frontend integration — RT replacement + IMDB link swap

**GameSession.tsx** (3 RatingsBadge locations, 2 IMDB link swaps):
- Now Playing tile: `🍅 {rt_score}%` → `<RatingsBadge variant="tile" ratings={currentMovie} />`
- Eligible card Row 4: vote_average + rt_score display → `<RatingsBadge variant="card" ratings={movie} />`
- Splash dialog stats row: Star+vote_average badge + rt_score badge → `<RatingsBadge variant="splash" ratings={splashMovie} />`
- Eligible card link: TMDB → `imdb_id ? imdb.com/title/{id} : themoviedb.org/movie/{id}`
- Splash dialog link: TMDB → same conditional pattern with `splashMovie.imdb_id`

**SearchPage.tsx** (2 RatingsBadge locations, 1 IMDB link swap):
- Results table: collapsed "Rating" (vote_average) + "RT" (rt_score) columns into single "Ratings" column with `<RatingsBadge variant="card" ratings={movie} />`
- Splash dialog: vote_average Badge + rt_score Badge → `<RatingsBadge variant="splash" ratings={splashMovie} />`
- Splash link: TMDB → conditional IMDB/TMDB

**ChainHistory.tsx** (1 IMDB link swap):
- Movie title link: TMDB → `step.movie_imdb_id ? imdb.com/title/{id} : themoviedb.org/movie/{id}`
- Currently always falls back to TMDB (field not yet in backend serialization) — graceful degradation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Tests used toBeInTheDocument() but jest-dom is not configured**
- **Found during:** Task 1 test run
- **Issue:** Project vitest config has `setupFiles: []` — `@testing-library/jest-dom` matchers are not globally available. `toBeInTheDocument()` throws "Invalid Chai property".
- **Fix:** Rewrote RatingsBadge tests to use `.toBeTruthy()` / `.toBeFalsy()` matching the passing SessionCounters/PosterWall test pattern already in the project.
- **Files modified:** `frontend/src/components/__tests__/RatingsBadge.test.tsx`
- **Commit:** f98415a

**2. [Rule 1 - Bug] SearchPage table column count mismatch after RT cell removal**
- **Found during:** Task 2 — after removing both the vote_average cell and rt_score cell, the column count would not match the header row.
- **Fix:** Collapsed both the "Rating" and "RT" sort-able header `<th>` columns into a single non-sortable "Ratings" `<th>`, matching the single combined `<td>` in each data row.
- **Files modified:** `frontend/src/pages/SearchPage.tsx`
- **Commit:** c52c79d

## Known Stubs

None — all rating fields are wired from EligibleMovieDTO through RatingsBadge. ChainHistory IMDB link gracefully falls back to TMDB because `movie_imdb_id` is not yet serialized by the backend step endpoints. This is documented in CONTEXT.md as acceptable graceful degradation; the optional field is already added to `GameSessionStepDTO` for when the backend wires it.

## Self-Check: PASSED

Files created:
- /Users/Oreo/Projects/CinemaChain/frontend/src/components/RatingsBadge.tsx — FOUND
- /Users/Oreo/Projects/CinemaChain/frontend/src/components/__tests__/RatingsBadge.test.tsx — FOUND

Commits:
- f98415a — Task 1: install icons pkg, extend EligibleMovieDTO, create RatingsBadge component + tests — FOUND
- c52c79d — Task 2: replace RT displays with RatingsBadge + swap TMDB links to IMDB — FOUND
