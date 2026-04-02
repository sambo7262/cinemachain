---
plan: 09-03
status: complete
---

## Summary

Merged archived sessions into GameLobby as an Archived tab.

## Changes
- ArchivedSessions.tsx: added `ArchivedSessionsTab` named export — identical logic to default export but no outer `min-h-screen` page wrapper and no heading
- GameLobby.tsx: imported `ArchivedSessionsTab`; wrapped existing grid/form content in outer `<Tabs defaultValue="active">` with Active and Archived tabs

## Verification
- `npx tsc --noEmit` passes
- `export function ArchivedSessionsTab` confirmed in ArchivedSessions.tsx
- No `min-h-screen` inside ArchivedSessionsTab
- GameLobby confirms `defaultValue="active"`, `value="archived"`, `ArchivedSessionsTab`
