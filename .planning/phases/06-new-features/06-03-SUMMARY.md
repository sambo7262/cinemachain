---
phase: 06-new-features
plan: "03"
subsystem: frontend
tags: [ui, session-stats, tmdb-links, search, chain-history]
dependency_graph:
  requires: []
  provides: [session-card-stats, now-playing-stats, chain-history-search, tmdb-external-links]
  affects: [GameLobby, GameSession, ChainHistory, EligibleMovieDTO]
tech_stack:
  added: []
  patterns: [lucide-react icons, inline IIFE for conditional stat rendering, real-time client-side filtering]
key_files:
  created: []
  modified:
    - frontend/src/pages/GameLobby.tsx
    - frontend/src/pages/GameSession.tsx
    - frontend/src/components/ChainHistory.tsx
    - frontend/src/lib/api.ts
decisions:
  - "D-11: Archive button removed from session cards — moved to session settings menu (Plan 06-06)"
  - "Now Playing stats use allEligibleMovies lookup by current_movie_tmdb_id — no new data fetching needed"
  - "Chain history search filters both movie and actor name client-side without backend changes"
metrics:
  duration: "~15 minutes"
  completed: "2026-03-22"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 4
---

# Phase 06 Plan 03: Frontend Info Density Features Summary

Four frontend-only features adding information density and discoverability across the app: session card stats, Now Playing tile stats, chain history search, and TMDB external links.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Session card stats + Now Playing tile stats | 9711e28 | GameLobby.tsx, GameSession.tsx |
| 2 | Chain history search + TMDB external links | 1a58997 | ChainHistory.tsx, GameSession.tsx, api.ts |

## What Was Built

**Item 8 — Session Card Stats (GameLobby.tsx):**
- Replaced deprecated "steps" stat with `watched_count watched · Xh Ym total · Started Month D, YYYY`
- Added `formatRuntime(minutes)` and `formatDate(isoString)` helper functions
- Removed archive button from session cards (D-11 — moves to session settings menu in Plan 06-06)
- Removed `archiveMutation` which only served the now-removed archive button

**Item 9 — Now Playing Tile Stats (GameSession.tsx):**
- Added MPAA badge, runtime text, and TMDB vote_average with Star icon below the current movie title
- Uses `allEligibleMovies.find(m => m.tmdb_id === session.current_movie_tmdb_id)` to source movie details
- Gracefully renders nothing if the current movie isn't in the eligible movies list
- Imported `Star` and `ExternalLink` from lucide-react

**Item 4 — Chain History Search (ChainHistory.tsx):**
- Added `useState` for `searchQuery`
- Search input with Search icon above the table, full width
- Real-time filtering: hides rows where neither movie title nor actor name matches the query
- Empty state: "No chain steps match '{query}'." shown when filteredSteps is empty with an active query

**Item 5 — TMDB External Links:**
- ChainHistory: ExternalLink icon after each movie title linking to `themoviedb.org/movie/{id}`
- ChainHistory: ExternalLink icon after each actor name (when `actor_tmdb_id` exists) linking to `themoviedb.org/person/{id}`
- GameSession eligible movies table: ExternalLink icon after each movie title
- All links: `target="_blank"`, `rel="noopener noreferrer"`, `e.stopPropagation()` on click
- No TMDB links on Eligible Actors grid (D-20)

**api.ts:**
- Added `overview: string | null` to `EligibleMovieDTO` for Plan 04 movie selection splash

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

All created/modified files verified present. Both task commits (9711e28, 1a58997) confirmed in git log.
