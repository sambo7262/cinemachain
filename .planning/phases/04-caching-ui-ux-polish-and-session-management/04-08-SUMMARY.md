---
phase: 04-caching-ui-ux-polish-and-session-management
plan: "08"
subsystem: backend
tags: [caching, tmdb, nightly-job, actor, performance]

# Dependency graph
requires:
  - phase: 04-07
    provides: Prior Phase 04 backend changes complete

provides:
  - Actor short-circuit in _ensure_actor_credits_in_db — skips TMDB if credits already in DB
  - Nightly actor pre-fetch (top-1500 popular actors) added to nightly_cache_job
  - Nightly movie stub backfill for blank title/genre rows added to nightly_cache_job

affects: [CACHE-01, CACHE-02]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Short-circuit DB check before TMDB API call to eliminate redundant fetches"
    - "Paginated /person/popular endpoint (75 pages x 20) for actor pre-warming"

key-files:
  created: []
  modified:
    - backend/app/routers/game.py
    - backend/app/services/cache.py

key-decisions:
  - "Short-circuit applied before any TMDB call in _ensure_actor_credits_in_db"
  - "Nightly pre-fetch warms top-1500 actors so mainstream actors are pre-loaded before user interaction"
  - "Movie stub backfill enriches rows with blank title or null genres via _ensure_movie_details_in_db"

patterns-established: []

requirements-completed: [CACHE-01, CACHE-02]

# Metrics
duration: autonomous
completed: 2026-03-18
---

# Phase 04 Plan 08: Cache Optimization Summary

**Actor short-circuit, nightly actor pre-fetch (top-1500), and movie stub backfill implemented to eliminate on-demand TMDB latency during gameplay**

## Accomplishments

- Short-circuited `_ensure_actor_credits_in_db` to skip TMDB when credits already in DB
- Added top-1500 popular actors nightly pre-fetch pass to `nightly_cache_job`
- Added nightly movie stub backfill for blank-title/null-genre rows

## Deviations from Plan

None.

## Issues Encountered

None.

---
*Phase: 04-caching-ui-ux-polish-and-session-management*
*Completed: 2026-03-18*
