---
phase: 04-caching-ui-ux-polish-and-session-management
plan: "09"
subsystem: backend
tags: [bug-fixes, eligible-movies, suggestions, blank-titles]

# Dependency graph
requires:
  - phase: 04-08
    provides: Actor short-circuit and nightly pre-fetch in place

provides:
  - Blank-title short-circuit fix — TMDB not skipped for title="" actor stubs
  - Eligible movies now excludes all session step movies directly (not just WatchEvents)
  - Suggestions fallback to genre-affinity from full DB when <5 game-mechanic results

affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Refined short-circuit: check credits count AND title non-empty before skipping TMDB"

key-files:
  created: []
  modified:
    - backend/app/routers/game.py

key-decisions:
  - "Short-circuit condition tightened to not skip TMDB when actor stubs have blank titles"
  - "Eligible movies query excludes session steps directly for correct chain enforcement"
  - "Suggestions fallback broadens to full DB genre-affinity pool when game-mechanic pool is thin"

patterns-established: []

requirements-completed: []

# Metrics
duration: autonomous
completed: 2026-03-18
---

# Phase 04 Plan 09: Bug Fixes Summary

**Three targeted backend fixes: blank-title short-circuit correction, direct session-step exclusion in eligible movies, and suggestions fallback to full-DB genre-affinity**

## Accomplishments

- Fixed blank-title actor stub issue — short-circuit now only skips TMDB if actor has credits AND non-empty titles
- Eligible movies excludes all session step movies directly (not just via WatchEvents)
- Suggestions fallback added: when game-mechanic results < 5, broadens to full-DB genre-affinity pool

## Deviations from Plan

None.

## Issues Encountered

None.

---
*Phase: 04-caching-ui-ux-polish-and-session-management*
*Completed: 2026-03-18*
