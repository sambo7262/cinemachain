---
plan: 09-04
status: complete
---

## Summary

Fixed both `navigate("/")` calls in GameSession.tsx to redirect to `/game`.

## Changes
- Line 363 (archiveMutation.onSuccess): `navigate("/")` → `navigate("/game")`
- Line 714 (End Session button): `api.archiveSession(sid).then(() => navigate("/"))` → `navigate("/game")`

## Verification
- `npx tsc --noEmit` passes
- `grep 'navigate("/")' GameSession.tsx` → 0 matches
- `grep 'navigate("/game")' GameSession.tsx` → 2 matches
