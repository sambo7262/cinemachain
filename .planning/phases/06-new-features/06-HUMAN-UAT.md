---
status: partial
phase: 06-new-features
source: [06-VERIFICATION.md]
started: 2026-03-22T00:00:00Z
updated: 2026-03-22T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Now Playing Tile Stats (ITEM-9)

**Test:** Navigate to an active game session. Look at the Now Playing tile (the section showing the current movie being watched). Do MPAA rating, runtime, and TMDB vote average appear below the movie title?

expected: Three stats appear inline — MPAA badge (e.g., "R"), runtime (e.g., "2h 19m"), TMDB rating with star icon (e.g., "8.4"). All styled as small muted text.
result: [pending]

**Why manual:** Stats are sourced from `allEligibleMovies.find(m => m.tmdb_id === session.current_movie_tmdb_id)`. If the current movie isn't in the eligible movies list at render time, the stats return null silently. Cannot verify without a live session.

**If stats are missing:** Fix is to fetch current movie metadata separately (dedicated API call on session load) rather than relying on the eligible movies list.

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
