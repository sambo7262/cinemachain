---
plan: 07
phase: 19-v2-bug-fixes-polish
status: complete
---

# 19-07 Summary — GAP-01/GAP-02: Mark-as-Watched Panel + Now Playing

## What was done
- GAP-01: Reworked both state panel blocks in GameSession.tsx to use a vertical flex-col layout — movie title as a prominent heading, instructional text below, full-width Mark as Watched button at bottom. Removed Clock icon and inline cramming.
- GAP-02: Now Playing section conditionally hides instructional text when isWatched is true, removing the stale radar text. The movie metadata row (including RatingsBadge) rendered just above already shows when a currentMovie is found, so the watched state now cleanly shows that metadata without the redundant instructional paragraph.

## Changes
- `frontend/src/pages/GameSession.tsx`: Both state panel blocks use flex-col layout; Now Playing conditionally hides instructional text when watched

## Acceptance criteria met
- text-lg font-bold text-foreground appears in both state panel blocks
- flex flex-col gap-3 used in the state panel area
- Old flex items-center justify-between layout removed from state panels
- isWatched conditional added in Now Playing section
