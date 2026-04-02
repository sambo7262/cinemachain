---
plan: 09-01
status: complete
---

## Summary

Rewrote NavBar.tsx with three permanent items: Game Mode (/game), Search (/search), Settings icon (/settings).

## Changes
- Replaced `isSessionsActive` / `isArchivedActive` with `isGameModeActive` / `isSearchActive`
- Logo `to` updated from `/` to `/game`
- "Sessions" → "Game Mode" (to `/game`); "Archived" → "Search" (to `/search`)
- Settings icon treatment unchanged

## Verification
- `npx tsc --noEmit` passes
- `isGameModeActive`, `isSearchActive` present; `isArchivedActive` absent
- No `to="/"` or `to="/archived"` in file
