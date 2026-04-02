---
plan: 09-02
status: complete
---

## Summary

Updated App.tsx route table and created SearchPlaceholder.tsx.

## Changes
- Created `frontend/src/pages/SearchPlaceholder.tsx` — dark card, "Search" heading, "Coming soon."
- App.tsx: `path="/"` → `path="/game"` (GameLobby)
- App.tsx: removed `/archived` route and `ArchivedSessions` import
- App.tsx: added `/search` → `SearchPlaceholder`
- App.tsx: catch-all Navigate target changed from `"/"` to `"/game"`

## Verification
- `npx tsc --noEmit` passes
- `path="/game"`, `path="/search"`, `Navigate to="/game"` confirmed
- No `path="/"`, `path="/archived"`, or `ArchivedSessions` import in App.tsx
